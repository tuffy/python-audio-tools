#include "flac.h"
#include "../pcmconv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

#ifndef STANDALONE
int
FlacDecoder_init(decoders_FlacDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    char* filename;
    int stream_offset = 0;

    self->filename = NULL;
    self->file = NULL;
    self->bitstream = NULL;

    self->seektable = array_o_new((ARRAY_COPY_FUNC)seekpoint_copy,
                                  free,
                                  NULL);

    self->subframe_data = array_ia_new();
    self->residuals = array_i_new();
    self->qlp_coeffs = array_i_new();
    self->framelist_data = array_i_new();
    self->audiotools_pcm = NULL;
    self->remaining_samples = 0;

    if (!PyArg_ParseTuple(args, "si|i",
                          &filename,
                          &(self->channel_mask),
                          &stream_offset))
        return -1;

    if (self->channel_mask < 0) {
        PyErr_SetString(PyExc_ValueError, "channel_mask must be >= 0");
        return -1;
    }
    if (stream_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "stream offset must be >= 0");
        return -1;
    }

    /*open the flac file*/
    self->file = fopen(filename, "rb");
    if (self->file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = br_open(self->file, BS_BIG_ENDIAN);
    }

    /*skip the given number of bytes, if any*/
    if (stream_offset != 0)
        fseek(self->file, stream_offset, SEEK_SET);

    self->filename = strdup(filename);

    /*read the STREAMINFO block, SEEKTABLE block
      and setup the total number of samples to read*/
    if (flacdec_read_metadata(self->bitstream,
                              &(self->streaminfo),
                              self->seektable)) {
        self->streaminfo.channels = 0;
        return -1;
    }

    self->remaining_samples = self->streaminfo.total_samples;

    /*initialize the output MD5 sum*/
    audiotools__MD5Init(&(self->md5));
    self->perform_validation = 1;
    self->stream_finalized = 0;

    /*setup a framelist generator function*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    /*place mark at beginning of stream in case seeking is needed*/
    self->bitstream->mark(self->bitstream);

    /*mark stream as not closed and ready for reading*/
    self->closed = 0;

    return 0;
}

PyObject*
FlacDecoder_close(decoders_FlacDecoder* self,
                  PyObject *args)
{
    /*mark stream as closed so more calls to read()
      generate ValueErrors*/
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

void
FlacDecoder_dealloc(decoders_FlacDecoder *self)
{

    self->subframe_data->del(self->subframe_data);
    self->residuals->del(self->residuals);
    self->qlp_coeffs->del(self->qlp_coeffs);
    self->framelist_data->del(self->framelist_data);
    Py_XDECREF(self->audiotools_pcm);

    if (self->filename != NULL)
        free(self->filename);

    if (self->bitstream != NULL) {
        /*clear out seek mark, if present*/
        if (self->bitstream->marks != NULL)
            self->bitstream->unmark(self->bitstream);

        self->bitstream->close(self->bitstream);
    }

    self->seektable->del(self->seektable);

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
FlacDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_FlacDecoder *self;

    self = (decoders_FlacDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
FlacDecoder_sample_rate(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->streaminfo.sample_rate);
}

static PyObject*
FlacDecoder_bits_per_sample(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->streaminfo.bits_per_sample);
}

static PyObject*
FlacDecoder_channels(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->streaminfo.channels);
}

static PyObject*
FlacDecoder_channel_mask(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->channel_mask);
}

PyObject*
FlacDecoder_read(decoders_FlacDecoder* self, PyObject *args)
{
    uint16_t crc16 = 0;
    int channel;
    struct flac_frame_header frame_header;
    PyObject* framelist;
    PyThreadState *thread_state;
    flac_status error;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    self->subframe_data->reset(self->subframe_data);

    /*if all samples have been read, return an empty FrameList*/
    if (self->stream_finalized) {
        return empty_FrameList(self->audiotools_pcm,
                               self->streaminfo.channels,
                               self->streaminfo.bits_per_sample);
    }

    if (self->remaining_samples < 1) {
        self->stream_finalized = 1;

        if (FlacDecoder_verify_okay(self)) {
            return empty_FrameList(self->audiotools_pcm,
                                   self->streaminfo.channels,
                                   self->streaminfo.bits_per_sample);
        } else {
            PyErr_SetString(PyExc_ValueError,
                            "MD5 mismatch at end of stream");
            return NULL;
        }
    }

    thread_state = PyEval_SaveThread();

    if (!setjmp(*br_try(self->bitstream))) {
        /*add callback for CRC16 calculation*/
        br_add_callback(self->bitstream, (bs_callback_func)flac_crc16, &crc16);

        /*read frame header*/
        if ((error = flacdec_read_frame_header(self->bitstream,
                                               &(self->streaminfo),
                                               &frame_header)) != OK) {
            br_pop_callback(self->bitstream, NULL);
            PyEval_RestoreThread(thread_state);
            PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
            br_etry(self->bitstream);
            return NULL;
        }

        /*read 1 subframe per channel*/
        for (channel = 0; channel < frame_header.channel_count; channel++)
            if ((error =
                 flacdec_read_subframe(
                     self->bitstream,
                     self->qlp_coeffs,
                     self->residuals,
                     (unsigned int)MIN(frame_header.block_size,
                                       self->remaining_samples),
                     flacdec_subframe_bits_per_sample(&frame_header,
                                                      channel),
                     self->subframe_data->append(self->subframe_data))) != OK) {
                br_pop_callback(self->bitstream, NULL);
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
                br_etry(self->bitstream);
                return NULL;
            }

        /*handle difference channels, if any*/
        flacdec_decorrelate_channels(frame_header.channel_assignment,
                                     self->subframe_data,
                                     self->framelist_data);

        /*check CRC-16*/
        self->bitstream->byte_align(self->bitstream);
        self->bitstream->read(self->bitstream, 16);
        br_pop_callback(self->bitstream, NULL);
        if (crc16 != 0) {
            PyEval_RestoreThread(thread_state);
            PyErr_SetString(PyExc_ValueError, "invalid checksum in frame");
            br_etry(self->bitstream);
            return NULL;
        }

        /*decrement remaining samples*/
        self->remaining_samples -= frame_header.block_size;
    } else {
        /*handle I/O error during read*/
        br_pop_callback(self->bitstream, NULL);
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "EOF reading frame");
        br_etry(self->bitstream);
        return NULL;
    }

    br_etry(self->bitstream);
    PyEval_RestoreThread(thread_state);

    framelist = array_i_to_FrameList(self->audiotools_pcm,
                                     self->framelist_data,
                                     frame_header.channel_count,
                                     frame_header.bits_per_sample);
    if (framelist != NULL) {
        /*update MD5 sum*/
        if (FlacDecoder_update_md5sum(self, framelist) == OK)
            /*return pcm.FrameList Python object*/
            return framelist;
        else {
            Py_DECREF(framelist);
            return NULL;
        }
    } else {
        return NULL;
    }
}

static PyObject*
FlacDecoder_seek(decoders_FlacDecoder* self, PyObject *args)
{
    long long seeked_offset;

    const array_o* seektable = self->seektable;
    uint64_t pcm_frames_offset = 0;
    uint64_t byte_offset = 0;
    unsigned i;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot seek closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "L", &seeked_offset))
        return NULL;

    if (seeked_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "cannot seek to negative value");
        return NULL;
    }

    self->stream_finalized = 0;

    /*find latest seekpoint whose first sample is <= seeked_offset
      or 0 if there are no seekpoints in the seektable*/
    for (i = 0; i < seektable->len; i++) {
        struct flac_SEEKPOINT* seekpoint = seektable->_[i];
        if (seekpoint->sample_number <= seeked_offset) {
            pcm_frames_offset = seekpoint->sample_number;
            byte_offset = seekpoint->byte_offset;
        } else {
            break;
        }
    }

    /*position bitstream to indicated value in file*/
    self->bitstream->rewind(self->bitstream);
    while (byte_offset) {
        /*perform this in chunks in case seeked distance
          is longer than a "long" taken by fseek*/
        const uint64_t seek = MIN(byte_offset, LONG_MAX);
        fseek(self->file, (long)seek, SEEK_CUR);
        byte_offset -= seek;
    }

    /*reset stream's total remaining frames*/
    self->remaining_samples = (self->streaminfo.total_samples -
                               pcm_frames_offset);

    if (pcm_frames_offset == 0) {
        /*if pcm_frames_offset is 0, reset MD5 validation*/
        audiotools__MD5Init(&(self->md5));
        self->perform_validation = 1;
    } else {
        /*otherwise, disable MD5 validation altogether at end of stream*/
        self->perform_validation = 0;
    }

    /*return actual PCM frames position in file*/
    return Py_BuildValue("K", pcm_frames_offset);
}

static PyObject*
FlacDecoder_offsets(decoders_FlacDecoder* self, PyObject *args)
{
    int channel;
    struct flac_frame_header frame_header;
    flac_status error;
    PyObject* offsets = PyList_New(0);
    PyObject* offset_pair;
    uint32_t samples;
    long offset;
    PyThreadState *thread_state = PyEval_SaveThread();

    while (self->remaining_samples > 0) {
        self->subframe_data->reset(self->subframe_data);
        offset = br_ftell(self->bitstream);

        if (!setjmp(*br_try(self->bitstream))) {
            /*read frame header*/
            if ((error = flacdec_read_frame_header(self->bitstream,
                                                   &(self->streaminfo),
                                                   &frame_header)) != OK) {
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
                goto error;
            }

            samples = frame_header.block_size;

            /*read 1 subframe per channel*/
            for (channel = 0; channel < frame_header.channel_count; channel++)
                if ((error =
                     flacdec_read_subframe(
                         self->bitstream,
                         self->qlp_coeffs,
                         self->residuals,
                         (unsigned int)MIN(frame_header.block_size,
                                           self->remaining_samples),
                         flacdec_subframe_bits_per_sample(&frame_header,
                                                          channel),
                         self->subframe_data->append(self->subframe_data))) !=
                    OK) {
                    PyEval_RestoreThread(thread_state);
                    PyErr_SetString(PyExc_ValueError,
                                    FlacDecoder_strerror(error));
                    goto error;
                }

            /*read CRC-16*/
            self->bitstream->byte_align(self->bitstream);
            self->bitstream->read(self->bitstream, 16);

            /*decrement remaining samples*/
            self->remaining_samples -= frame_header.block_size;

            /*add offset pair to our list*/
            PyEval_RestoreThread(thread_state);
            offset_pair = Py_BuildValue("(i, I)", offset, samples);
            PyList_Append(offsets, offset_pair);
            Py_DECREF(offset_pair);
            thread_state = PyEval_SaveThread();
        } else {
            /*handle I/O error during read*/
            PyEval_RestoreThread(thread_state);
            PyErr_SetString(PyExc_IOError, "EOF reading frame");
            goto error;
        }

        br_etry(self->bitstream);
    }

    self->stream_finalized = 1;

    PyEval_RestoreThread(thread_state);
    return offsets;
error:
    Py_XDECREF(offsets);
    br_etry(self->bitstream);
    return NULL;
}

flac_status
FlacDecoder_update_md5sum(decoders_FlacDecoder *self,
                          PyObject *framelist)
{
    if (self->perform_validation) {
        PyObject *string = PyObject_CallMethod(framelist,
                                               "to_bytes","ii",
                                               0,
                                               1);
        char *string_buffer;
        Py_ssize_t length;

        if (string != NULL) {
            if (PyString_AsStringAndSize(string,
                                         &string_buffer,
                                         &length) == 0) {
                audiotools__MD5Update(&(self->md5),
                                      (unsigned char *)string_buffer,
                                      length);
                Py_DECREF(string);
                return OK;
            } else {
                Py_DECREF(string);
                return ERROR;
            }
        } else {
            return ERROR;
        }
    } else {
        return OK;
    }
}

int
FlacDecoder_verify_okay(decoders_FlacDecoder *self)
{
    if (self->perform_validation) {
        unsigned char stream_md5sum[16];
        const static unsigned char blank_md5sum[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                                       0, 0, 0, 0, 0, 0, 0, 0};

        audiotools__MD5Final(stream_md5sum, &(self->md5));

        return ((memcmp(self->streaminfo.md5sum, blank_md5sum, 16) == 0) ||
                (memcmp(stream_md5sum, self->streaminfo.md5sum, 16) == 0));
    } else {
        return 1;
    }
}

#endif

int
flacdec_read_metadata(BitstreamReader *bitstream,
                      struct flac_STREAMINFO *streaminfo,
                      array_o *seektable)
{
    if (!setjmp(*br_try(bitstream))) {
        unsigned last_block;

        if (bitstream->read(bitstream, 32) != 0x664C6143u) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "not a FLAC file");
#endif
            br_etry(bitstream);
            return 1;
        }

        do {
            last_block = bitstream->read(bitstream, 1);
            const unsigned block_type = bitstream->read(bitstream, 7);
            const unsigned block_length = bitstream->read(bitstream, 24);

            switch (block_type) {
            case 0:   /*STREAMINFO*/
                streaminfo->minimum_block_size =
                    bitstream->read(bitstream, 16);
                streaminfo->maximum_block_size =
                    bitstream->read(bitstream, 16);
                streaminfo->minimum_frame_size =
                    bitstream->read(bitstream, 24);
                streaminfo->maximum_frame_size =
                    bitstream->read(bitstream, 24);
                streaminfo->sample_rate =
                    bitstream->read(bitstream, 20);
                streaminfo->channels =
                    bitstream->read(bitstream, 3) + 1;
                streaminfo->bits_per_sample =
                    bitstream->read(bitstream, 5) + 1;
                streaminfo->total_samples =
                    bitstream->read_64(bitstream, 36);

                bitstream->read_bytes(bitstream, streaminfo->md5sum, 16);
                break;
            case 3: /*SEEKTABLE*/
                {
                    unsigned seekpoints = block_length / 18;
                    seektable->reset_for(seektable, seekpoints);

                    for (; seekpoints > 0; seekpoints--) {
                        struct flac_SEEKPOINT seekpoint;
                        seekpoint.sample_number =
                            bitstream->read_64(bitstream, 64);
                        seekpoint.byte_offset =
                            bitstream->read_64(bitstream, 64);
                        seekpoint.samples =
                            bitstream->read(bitstream, 16);
                        seektable->append(seektable, &seekpoint);
                    }
                }
                break;
            default:  /*all other blocks*/
                bitstream->skip(bitstream, block_length * 8);
                break;
            }
        } while (!last_block);

        br_etry(bitstream);
        return 0;
    } else {
#ifndef STANDALONE
        PyErr_SetString(PyExc_IOError, "EOF while reading metadata");
#endif
        br_etry(bitstream);
        return 1;
    }
}

flac_status
flacdec_read_frame_header(BitstreamReader *bitstream,
                          struct flac_STREAMINFO *streaminfo,
                          struct flac_frame_header *header)
{
    unsigned block_size_bits;
    unsigned sample_rate_bits;
    uint8_t crc8 = 0;

    br_add_callback(bitstream, (bs_callback_func)flac_crc8, &crc8);

    /*read and verify sync code*/
    if (bitstream->read(bitstream, 14) != 0x3FFE) {
        return ERR_INVALID_SYNC_CODE;
    }

    /*read and verify reserved bit*/
    if (bitstream->read(bitstream, 1) != 0) {
        return ERR_INVALID_RESERVED_BIT;
    }

    header->blocking_strategy = bitstream->read(bitstream, 1);

    block_size_bits = bitstream->read(bitstream, 4);
    sample_rate_bits = bitstream->read(bitstream, 4);
    header->channel_assignment = bitstream->read(bitstream, 4);
    switch (header->channel_assignment) {
    case 0x8:
    case 0x9:
    case 0xA:
        header->channel_count = 2;
        break;
    default:
        header->channel_count = header->channel_assignment + 1;
        break;
    }

    switch (bitstream->read(bitstream, 3)) {
    case 0:
        header->bits_per_sample = streaminfo->bits_per_sample; break;
    case 1:
        header->bits_per_sample = 8; break;
    case 2:
        header->bits_per_sample = 12; break;
    case 4:
        header->bits_per_sample = 16; break;
    case 5:
        header->bits_per_sample = 20; break;
    case 6:
        header->bits_per_sample = 24; break;
    default:
        return ERR_INVALID_BITS_PER_SAMPLE;
    }
    bitstream->read(bitstream, 1); /*padding*/

    header->frame_number = read_utf8(bitstream);

    switch (block_size_bits) {
    case 0x0: header->block_size = streaminfo->maximum_block_size; break;
    case 0x1: header->block_size = 192; break;
    case 0x2: header->block_size = 576; break;
    case 0x3: header->block_size = 1152; break;
    case 0x4: header->block_size = 2304; break;
    case 0x5: header->block_size = 4608; break;
    case 0x6: header->block_size = bitstream->read(bitstream, 8) + 1; break;
    case 0x7: header->block_size = bitstream->read(bitstream, 16) + 1; break;
    case 0x8: header->block_size = 256; break;
    case 0x9: header->block_size = 512; break;
    case 0xA: header->block_size = 1024; break;
    case 0xB: header->block_size = 2048; break;
    case 0xC: header->block_size = 4096; break;
    case 0xD: header->block_size = 8192; break;
    case 0xE: header->block_size = 16384; break;
    case 0xF: header->block_size = 32768; break;
    }

    switch (sample_rate_bits) {
    case 0x0: header->sample_rate = streaminfo->sample_rate; break;
    case 0x1: header->sample_rate = 88200; break;
    case 0x2: header->sample_rate = 176400; break;
    case 0x3: header->sample_rate = 192000; break;
    case 0x4: header->sample_rate = 8000; break;
    case 0x5: header->sample_rate = 16000; break;
    case 0x6: header->sample_rate = 22050; break;
    case 0x7: header->sample_rate = 24000; break;
    case 0x8: header->sample_rate = 32000; break;
    case 0x9: header->sample_rate = 44100; break;
    case 0xA: header->sample_rate = 48000; break;
    case 0xB: header->sample_rate = 96000; break;
    case 0xC: header->sample_rate = bitstream->read(bitstream, 8) * 1000; break;
    case 0xD: header->sample_rate = bitstream->read(bitstream, 16); break;
    case 0xE: header->sample_rate = bitstream->read(bitstream, 16) * 10; break;
    case 0xF:
        return ERR_INVALID_SAMPLE_RATE;
    }

    /*check for valid CRC-8 value*/
    bitstream->read(bitstream, 8);
    br_pop_callback(bitstream, NULL);
    if (crc8 != 0)
        return ERR_INVALID_FRAME_CRC;

    /*Once we've read everything,
      ensure the values are compatible with STREAMINFO.*/

    if (streaminfo->sample_rate != header->sample_rate) {
        return ERR_SAMPLE_RATE_MISMATCH;
    }
    if (streaminfo->channels != header->channel_count) {
        return ERR_CHANNEL_COUNT_MISMATCH;
    }
    if (streaminfo->bits_per_sample != header->bits_per_sample) {
        return ERR_BITS_PER_SAMPLE_MISMATCH;
    }
    if (header->block_size > streaminfo->maximum_block_size) {
        return ERR_MAXIMUM_BLOCK_SIZE_EXCEEDED;
    }

    return OK;
}

flac_status
flacdec_read_subframe(BitstreamReader* bitstream,
                      array_i* qlp_coeffs,
                      array_i* residuals,
                      unsigned block_size,
                      unsigned bits_per_sample,
                      array_i* samples)
{
    struct flac_subframe_header subframe_header;
    unsigned i;
    flac_status error = OK;

    if (flacdec_read_subframe_header(
            bitstream,
            &subframe_header) == ERR_INVALID_SUBFRAME_TYPE)
        return ERR_INVALID_SUBFRAME_TYPE;

    /*account for wasted bits-per-sample*/
    if (subframe_header.wasted_bits_per_sample > 0)
        bits_per_sample -= subframe_header.wasted_bits_per_sample;

    switch (subframe_header.type) {
    case FLAC_SUBFRAME_CONSTANT:
        error = flacdec_read_constant_subframe(bitstream,
                                               block_size,
                                               bits_per_sample,
                                               samples);
        break;
    case FLAC_SUBFRAME_VERBATIM:
        error = flacdec_read_verbatim_subframe(bitstream,
                                               block_size,
                                               bits_per_sample,
                                               samples);
        break;
    case FLAC_SUBFRAME_FIXED:
        error = flacdec_read_fixed_subframe(bitstream,
                                            residuals,
                                            subframe_header.order,
                                            block_size,
                                            bits_per_sample,
                                            samples);
        break;
    case FLAC_SUBFRAME_LPC:
        error = flacdec_read_lpc_subframe(bitstream,
                                          qlp_coeffs,
                                          residuals,
                                          subframe_header.order,
                                          block_size,
                                          bits_per_sample,
                                          samples);
        break;
    }

    if (error != OK)
        return error;

    /*reinsert wasted bits-per-sample, if necessary*/
    if (subframe_header.wasted_bits_per_sample > 0)
        for (i = 0; i < block_size; i++)
            samples->_[i] <<= subframe_header.wasted_bits_per_sample;

    return OK;
}

flac_status
flacdec_read_subframe_header(BitstreamReader *bitstream,
                             struct flac_subframe_header *subframe_header)
{
    unsigned subframe_type;

    bitstream->read(bitstream, 1);  /*padding*/
    subframe_type = bitstream->read(bitstream, 6);
    if (subframe_type == 0) {
        subframe_header->type = FLAC_SUBFRAME_CONSTANT;
        subframe_header->order = 0;
    } else if (subframe_type == 1) {
        subframe_header->type = FLAC_SUBFRAME_VERBATIM;
        subframe_header->order = 0;
    } else if ((subframe_type & 0x38) == 0x08) {
        subframe_header->type = FLAC_SUBFRAME_FIXED;
        subframe_header->order = subframe_type & 0x07;
    } else if ((subframe_type & 0x20) == 0x20) {
        subframe_header->type = FLAC_SUBFRAME_LPC;
        subframe_header->order = (subframe_type & 0x1F) + 1;
    } else {
        return ERR_INVALID_SUBFRAME_TYPE;
    }

    if (bitstream->read(bitstream, 1) == 0) {
        subframe_header->wasted_bits_per_sample = 0;
    } else {
        subframe_header->wasted_bits_per_sample = bitstream->read_unary(
                                                      bitstream, 1) + 1;
    }

    return OK;
}

unsigned int
flacdec_subframe_bits_per_sample(struct flac_frame_header *frame_header,
                                 unsigned int channel_number) {
    if (((frame_header->channel_assignment == 0x8) &&
         (channel_number == 1)) ||
        ((frame_header->channel_assignment == 0x9) &&
         (channel_number == 0)) ||
        ((frame_header->channel_assignment == 0xA) &&
         (channel_number == 1))) {
        return frame_header->bits_per_sample + 1;
    } else {
        return frame_header->bits_per_sample;
    }
}

flac_status
flacdec_read_constant_subframe(BitstreamReader* bitstream,
                               unsigned block_size,
                               unsigned bits_per_sample,
                               array_i* samples)
{
    const int value = bitstream->read_signed(bitstream, bits_per_sample);

    samples->mset(samples, block_size, value);

    return OK;
}

flac_status
flacdec_read_verbatim_subframe(BitstreamReader* bitstream,
                               unsigned block_size,
                               unsigned bits_per_sample,
                               array_i* samples)
{
    unsigned i;

    samples->reset_for(samples, block_size);

    for (i = 0; i < block_size; i++)
        a_append(samples,
                 bitstream->read_signed(bitstream, bits_per_sample));

    return OK;
}

flac_status
flacdec_read_fixed_subframe(BitstreamReader* bitstream,
                            array_i* residuals,
                            unsigned order,
                            unsigned block_size,
                            unsigned bits_per_sample,
                            array_i* samples)
{
    unsigned i;
    flac_status error;
    int* s_data;
    int* r_data;

    /*ensure that samples->data won't be realloc'ated*/
    samples->reset_for(samples, block_size);
    s_data = samples->_;

    /*read "order" number of warm-up samples*/
    for (i = 0; i < order; i++) {
        a_append(samples,
                 bitstream->read_signed(bitstream, bits_per_sample));
    }

    /*read the residual block*/
    if ((error = flacdec_read_residual(bitstream,
                                       order,
                                       block_size,
                                       residuals)) != OK)
        return error;
    else
        r_data = residuals->_;

    /*calculate subframe samples from warm-up samples and residual*/
    switch (order) {
    case 0:
        samples->extend(samples, residuals);
        break;
    case 1:
        for (i = 1; i < block_size; i++)
            a_append(samples, s_data[i - 1] + r_data[i - 1]);
        break;
    case 2:
        for (i = 2; i < block_size; i++)
            a_append(samples,
                     (2 * s_data[i - 1]) -
                     s_data[i - 2] +
                     r_data[i - 2]);
        break;
    case 3:
        for (i = 3; i < block_size; i++)
            a_append(samples,
                     (3 * s_data[i - 1]) -
                     (3 * s_data[i - 2]) +
                     s_data[i - 3] +
                     r_data[i - 3]);
        break;
    case 4:
        for (i = 4; i < block_size; i++)
            a_append(samples,
                     (4 * s_data[i - 1]) -
                     (6 * s_data[i - 2]) +
                     (4 * s_data[i - 3]) -
                     s_data[i - 4] +
                     r_data[i - 4]);

        break;
    default:
        return ERR_INVALID_FIXED_ORDER;
    }

    return OK;
}

flac_status
flacdec_read_lpc_subframe(BitstreamReader* bitstream,
                          array_i* qlp_coeffs,
                          array_i* residuals,
                          unsigned order,
                          unsigned block_size,
                          unsigned bits_per_sample,
                          array_i* samples)
{
    unsigned i;
    unsigned qlp_precision;
    unsigned qlp_shift_needed;

    int* s_data;
    int* r_data;
    int* qlp_data;
    flac_status error;

    qlp_coeffs->reset(qlp_coeffs);
    samples->reset_for(samples, block_size);
    s_data = samples->_;

    /*read order number of warm-up samples*/
    for (i = 0; i < order; i++) {
        a_append(samples,
                 bitstream->read_signed(bitstream, bits_per_sample));
    }

    /*read QLP precision*/
    qlp_precision = bitstream->read(bitstream, 4) + 1;

    /*read QLP shift needed*/
    qlp_shift_needed = bitstream->read_signed(bitstream, 5);
    qlp_shift_needed = MAX(qlp_shift_needed, 0);

    /*read order number of QLP coefficients of size qlp_precision*/
    for (i = 0; i < order; i++) {
        qlp_coeffs->append(qlp_coeffs,
                           bitstream->read_signed(bitstream, qlp_precision));
    }

    qlp_data = qlp_coeffs->_;

    /*read the residual*/
    if ((error = flacdec_read_residual(bitstream, order,
                                       block_size, residuals)) != OK)
        return error;
    else
        r_data = residuals->_;

    /*calculate subframe samples from warm-up samples and residual*/
    for (i = order; i < block_size; i++) {
        int64_t accumulator = 0;
        unsigned j;
        for (j = 0; j < order; j++) {
            accumulator += (int64_t)qlp_data[j] * (int64_t)s_data[i - j - 1];
        }

        a_append(samples,
                 (int)(accumulator >> qlp_shift_needed) + r_data[i - order]);
    }

    return OK;
}

flac_status
flacdec_read_residual(BitstreamReader* bitstream,
                      unsigned order,
                      unsigned block_size,
                      array_i* residuals)
{
    const unsigned coding_method = bitstream->read(bitstream, 2);
    const unsigned partition_order = bitstream->read(bitstream, 4);
    const unsigned total_partitions = 1 << partition_order;
    unsigned partition;

    unsigned int (*read)(struct BitstreamReader_s* bs, unsigned int count);
    unsigned int (*read_unary)(struct BitstreamReader_s* bs, int stop_bit);

    read = bitstream->read;
    read_unary = bitstream->read_unary;

    residuals->reset(residuals);

    /*read 2^partition_order number of partitions*/
    for (partition = 0; partition < total_partitions; partition++) {
        int partition_samples;
        unsigned rice_parameter;
        unsigned escape_code;

        /*each partition after the first contains
          block_size / (2 ^ partition_order) number of residual values*/
        if (partition == 0) {
            partition_samples = (int)(block_size /
                                      (1 << partition_order)) - order;
            partition_samples = MAX(partition_samples, 0);
        } else {
            partition_samples = block_size / (1 << partition_order);
        }

        switch (coding_method) {
        case 0:
            rice_parameter = bitstream->read(bitstream, 4);
            if (rice_parameter == 0xF)
                escape_code = bitstream->read(bitstream, 5);
            else
                escape_code = 0;
            break;
        case 1:
            rice_parameter = bitstream->read(bitstream, 5);
            if (rice_parameter == 0x1F)
                escape_code = bitstream->read(bitstream, 5);
            else
                escape_code = 0;
            break;
        default:
            return ERR_INVALID_CODING_METHOD;
        }

        residuals->resize_for(residuals, partition_samples);
        if (!escape_code) {
            for (;partition_samples; partition_samples--) {
                const unsigned msb = read_unary(bitstream, 1);
                const unsigned lsb = read(bitstream, rice_parameter);
                const unsigned value = (msb << rice_parameter) | lsb;
                if (value & 1) {
                    a_append(residuals, -((int)value >> 1) - 1);
                } else {
                    a_append(residuals, (int)value >> 1);
                }
            }
        } else {
            for (;partition_samples; partition_samples--) {
                a_append(residuals,
                         bitstream->read_signed(bitstream, escape_code));
            }
        }
    }

    return OK;
}


void
flacdec_decorrelate_channels(unsigned channel_assignment,
                             const array_ia* subframes,
                             array_i* framelist) {
    unsigned i,j;
    const unsigned channel_count = subframes->len;
    const unsigned block_size = subframes->_[0]->len;
    int64_t mid;
    int32_t side;

    framelist->reset_for(framelist, channel_count * block_size);

    switch (channel_assignment) {
    case 0x8:
        /*left-difference*/
        assert(subframes->len == 2);
        assert(subframes->_[0]->len == subframes->_[1]->len);
        for (i = 0; i < block_size; i++) {
            a_append(framelist, subframes->_[0]->_[i]);
            a_append(framelist, (subframes->_[0]->_[i] -
                                 subframes->_[1]->_[i]));
        }
        break;
    case 0x9:
        /*difference-right*/
        assert(subframes->len == 2);
        assert(subframes->_[0]->len == subframes->_[1]->len);
        for (i = 0; i < block_size; i++) {
            a_append(framelist, (subframes->_[0]->_[i] +
                                 subframes->_[1]->_[i]));
            a_append(framelist, subframes->_[1]->_[i]);
        }
        break;
    case 0xA:
        /*mid-side*/
        assert(subframes->len == 2);
        assert(subframes->_[0]->len == subframes->_[1]->len);
        for (i = 0; i < block_size; i++) {
            mid = subframes->_[0]->_[i];
            side = subframes->_[1]->_[i];
            mid = (mid << 1) | (side & 1);
            a_append(framelist, (int)((mid + side) >> 1));
            a_append(framelist, (int)((mid - side) >> 1));
        }
        break;
    default:
        /*independent*/
#ifndef NDEBUG
        for (j = 0; j < channel_count; j++) {
            assert(subframes->_[0]->len == subframes->_[j]->len);
        }
#endif
        for (i = 0; i < block_size; i++) {
            for (j = 0; j < channel_count; j++) {
                a_append(framelist, subframes->_[j]->_[i]);
            }
        }
        break;
    }
}


const char*
FlacDecoder_strerror(flac_status error)
{
    switch (error) {
    case OK:
        return "No Error";
    case ERROR:
        return "Error";
    case ERR_INVALID_SYNC_CODE:
        return "invalid sync code";
    case ERR_INVALID_RESERVED_BIT:
        return "invalid reserved bit";
    case ERR_INVALID_BITS_PER_SAMPLE:
        return "invalid bits per sample";
    case ERR_INVALID_SAMPLE_RATE:
        return "invalid sample rate";
    case ERR_INVALID_FRAME_CRC:
        return "invalid checksum in frame header";
    case ERR_SAMPLE_RATE_MISMATCH:
        return "frame sample rate does not match STREAMINFO sample rate";
    case ERR_CHANNEL_COUNT_MISMATCH:
        return "frame channel count does not match STREAMINFO channel count";
    case ERR_BITS_PER_SAMPLE_MISMATCH:
        return "frame bits-per-sample does not match "
            "STREAMINFO bits per sample";
    case ERR_MAXIMUM_BLOCK_SIZE_EXCEEDED:
        return "frame block size exceeds STREAMINFO's maximum block size";
    case ERR_INVALID_CODING_METHOD:
        return "invalid residual partition coding method";
    case ERR_INVALID_FIXED_ORDER:
        return "invalid FIXED subframe order";
    case ERR_INVALID_SUBFRAME_TYPE:
        return "invalid subframe type";
    default:
        return "Unknown Error";
    }
}

unsigned
read_utf8(BitstreamReader *stream)
{
    unsigned total_bytes = stream->read_unary(stream, 0);
    unsigned value = stream->read(stream, 7 - total_bytes);
    for (;total_bytes > 1; total_bytes--) {
        value = (value << 6) | (stream->read(stream, 8) & 0x3F);
    }

    return value;
}

struct flac_SEEKPOINT*
seekpoint_copy(struct flac_SEEKPOINT* seekpoint)
{
    struct flac_SEEKPOINT* new_seekpoint =
        malloc(sizeof(struct flac_SEEKPOINT));

    new_seekpoint->sample_number = seekpoint->sample_number;
    new_seekpoint->byte_offset = seekpoint->byte_offset;
    new_seekpoint->samples = seekpoint->samples;

    return new_seekpoint;
}


#ifdef EXECUTABLE
#include <string.h>
#include <errno.h>

int main(int argc, char* argv[]) {
    FILE* file;
    BitstreamReader* reader;
    struct flac_STREAMINFO streaminfo;
    array_o* seektable;
    uint64_t remaining_frames;

    array_i* qlp_coeffs;
    array_i* residuals;
    array_ia* subframe_data;
    array_i* framelist_data;

    FrameList_int_to_char_converter converter;
    unsigned char *output_data;
    unsigned output_data_size;

    audiotools__MD5Context md5;
    unsigned char stream_md5sum[16];
    const static unsigned char blank_md5sum[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                                   0, 0, 0, 0, 0, 0, 0, 0};

    if (argc < 2) {
        fprintf(stderr, "*** Usage: %s <file.flac>\n", argv[0]);
        return 1;
    }

    /*open input file for reading*/
    if ((file = fopen(argv[1], "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", argv[1], strerror(errno));
        return 1;
    } else {
        /*open bitstream and setup temporary arrays/buffers*/
        reader = br_open(file, BS_BIG_ENDIAN);
        seektable = array_o_new((ARRAY_COPY_FUNC)seekpoint_copy,
                                free,
                                NULL);
        qlp_coeffs = array_i_new();
        residuals = array_i_new();
        subframe_data = array_ia_new();
        framelist_data = array_i_new();

        output_data = malloc(1);
        output_data_size = 1;
    }

    /*read initial metadata blocks*/
    if (flacdec_read_metadata(reader, &streaminfo, seektable)) {
        fprintf(stderr, "*** Error reading streaminfo\n");
        goto error;
    } else {
        remaining_frames = streaminfo.total_samples;
    }

    /*initialize the output MD5 sum*/
    audiotools__MD5Init(&md5);

    /*setup a framelist converter function*/
    converter = FrameList_get_int_to_char_converter(streaminfo.bits_per_sample,
                                                    0,
                                                    1);

    while (remaining_frames) {
        unsigned pcm_size;

        qlp_coeffs->reset(qlp_coeffs);
        residuals->reset(residuals);
        subframe_data->reset(subframe_data);
        framelist_data->reset(framelist_data);

        if (!setjmp(*br_try(reader))) {
            flac_status error;
            struct flac_frame_header frame_header;
            unsigned channel;
            uint16_t crc16 = 0;

            /*add callback for CRC16 calculation*/
            br_add_callback(reader, (bs_callback_func)flac_crc16, &crc16);

            /*read frame header*/
            if ((error = flacdec_read_frame_header(reader,
                                                   &streaminfo,
                                                   &frame_header)) != OK) {
                br_pop_callback(reader, NULL);
                br_etry(reader);
                fprintf(stderr, "*** Error: %s\n", FlacDecoder_strerror(error));
                goto error;
            }

            /*read 1 subframe per channels*/
            for (channel = 0; channel < frame_header.channel_count; channel++)
                if ((error =
                     flacdec_read_subframe(
                         reader,
                         qlp_coeffs,
                         residuals,
                         (unsigned)MIN(frame_header.block_size,
                                       remaining_frames),
                         flacdec_subframe_bits_per_sample(&frame_header,
                                                          channel),
                         subframe_data->append(subframe_data))) != OK) {
                    br_pop_callback(reader, NULL);
                    br_etry(reader);
                    fprintf(stderr, "*** Error: %s\n",
                            FlacDecoder_strerror(error));
                    goto error;
                }

            /*handle difference channels, if any*/
            flacdec_decorrelate_channels(frame_header.channel_assignment,
                                         subframe_data,
                                         framelist_data);

            /*check CRC-16*/
            reader->byte_align(reader);
            reader->read(reader, 16);
            br_pop_callback(reader, NULL);
            if (crc16 != 0) {
                br_etry(reader);
                fprintf(stderr, "*** Error: invalid checksum in frame\n");
                goto error;
            }

            /*decrement remaining frames*/
            remaining_frames -= frame_header.block_size;

            br_etry(reader);
        } else {
            /*handle I/O error during read*/
            br_pop_callback(reader, NULL);
            br_etry(reader);
            fprintf(stderr, "*** I/O Error reading frame\n");
            goto error;
        }

        /*convert framelist to string*/
        pcm_size = (streaminfo.bits_per_sample / 8) * framelist_data->len;
        if (pcm_size > output_data_size) {
            output_data_size = pcm_size;
            output_data = realloc(output_data, output_data_size);
        }
        FrameList_samples_to_char(output_data,
                                  framelist_data->_,
                                  converter,
                                  framelist_data->len,
                                  streaminfo.bits_per_sample);

        /*update MD5 sum*/
        audiotools__MD5Update(&md5, output_data, pcm_size);

        /*output framelist as string to stdout*/
        fwrite(output_data, sizeof(unsigned char), pcm_size, stdout);
    }

    /*verify MD5 sum*/
    audiotools__MD5Final(stream_md5sum, &md5);

    if (!((memcmp(streaminfo.md5sum, blank_md5sum, 16) == 0) ||
          (memcmp(stream_md5sum, streaminfo.md5sum, 16) == 0))) {
        fprintf(stderr, "*** MD5 mismatch at end of stream\n");
        goto error;
    }

    reader->close(reader);
    seektable->del(seektable);
    qlp_coeffs->del(qlp_coeffs);
    residuals->del(residuals);
    subframe_data->del(subframe_data);
    framelist_data->del(framelist_data);

    free(output_data);

    return 0;
error:
    reader->close(reader);
    seektable->del(seektable);
    qlp_coeffs->del(qlp_coeffs);
    residuals->del(residuals);
    subframe_data->del(subframe_data);
    framelist_data->del(framelist_data);

    free(output_data);

    return 1;
}
#endif
