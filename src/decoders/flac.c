#include "flac.h"
#include "../pcmconv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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

int
FlacDecoder_init(decoders_FlacDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    char* filename;
    int stream_offset = 0;

    self->filename = NULL;
    self->file = NULL;
    self->bitstream = NULL;
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

    /*read the STREAMINFO block and setup the total number of samples to read*/
    if (flacdec_read_metadata(self->bitstream, &(self->streaminfo))) {
        self->streaminfo.channels = 0;
        return -1;
    }

    self->remaining_samples = self->streaminfo.total_samples;

    /*initialize the output MD5 sum*/
    audiotools__MD5Init(&(self->md5));
    self->stream_finalized = 0;

    /*add callback for CRC16 calculation*/
    br_add_callback(self->bitstream, flac_crc16, &(self->crc16));

    /*setup a framelist generator function*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

PyObject*
FlacDecoder_close(decoders_FlacDecoder* self,
                  PyObject *args)
{
    self->remaining_samples = 0;
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

    if (self->bitstream != NULL)
        self->bitstream->close(self->bitstream);

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

int
flacdec_read_metadata(BitstreamReader *bitstream,
                      struct flac_STREAMINFO *streaminfo)
{
    unsigned int last_block;
    unsigned int block_type;
    unsigned int block_length;

    if (!setjmp(*br_try(bitstream))) {
        if (bitstream->read(bitstream, 32) != 0x664C6143u) {
            PyErr_SetString(PyExc_ValueError, "not a FLAC file");
            br_etry(bitstream);
            return 1;
        }

        do {
            last_block = bitstream->read(bitstream, 1);
            block_type = bitstream->read(bitstream, 7);
            block_length = bitstream->read(bitstream, 24);

            if (block_type == 0) {
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
            } else {
                bitstream->skip(bitstream, block_length * 8);
            }
        } while (!last_block);

        br_etry(bitstream);
        return 0;
    } else {
        PyErr_SetString(PyExc_IOError,
                        "EOF while reading STREAMINFO block");
        br_etry(bitstream);
        return 1;
    }
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
    int channel;
    struct flac_frame_header frame_header;
    PyObject* framelist;
    PyThreadState *thread_state;
    flac_status error;

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
    self->crc16 = 0;

    if (!setjmp(*br_try(self->bitstream))) {
        /*read frame header*/
        if ((error = flacdec_read_frame_header(self->bitstream,
                                               &(self->streaminfo),
                                               &frame_header)) != OK) {
            PyEval_RestoreThread(thread_state);
            PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
            goto error;
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
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
                goto error;
            }

        /*handle difference channels, if any*/
        flacdec_decorrelate_channels(frame_header.channel_assignment,
                                     self->subframe_data,
                                     self->framelist_data);

        /*check CRC-16*/
        self->bitstream->byte_align(self->bitstream);
        self->bitstream->read(self->bitstream, 16);
        if (self->crc16 != 0) {
            PyEval_RestoreThread(thread_state);
            PyErr_SetString(PyExc_ValueError, "invalid checksum in frame");
            goto error;
        }

        /*decrement remaining samples*/
        self->remaining_samples -= frame_header.block_size;
    } else {
        /*handle I/O error during read*/
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "EOF reading frame");
        goto error;
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

 error:
    br_etry(self->bitstream);
    return NULL;
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
flacdec_read_frame_header(BitstreamReader *bitstream,
                          struct flac_STREAMINFO *streaminfo,
                          struct flac_frame_header *header)
{
    uint32_t block_size_bits;
    uint32_t sample_rate_bits;
    uint32_t crc8 = 0;

    br_add_callback(bitstream, flac_crc8, &crc8);

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
                      unsigned int block_size,
                      unsigned int bits_per_sample,
                      array_i* samples)
{
    struct flac_subframe_header subframe_header;
    uint32_t i;
    flac_status error = OK;

    if (flacdec_read_subframe_header(bitstream,
                                     &subframe_header) == ERROR)
        return ERROR;

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
    uint8_t subframe_type;

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
                               uint32_t block_size,
                               uint8_t bits_per_sample,
                               array_i* samples)
{
    int32_t value = bitstream->read_signed(bitstream, bits_per_sample);

    samples->reset(samples);
    samples->mappend(samples, block_size, value);

    return OK;
}

flac_status
flacdec_read_verbatim_subframe(BitstreamReader* bitstream,
                               uint32_t block_size,
                               uint8_t bits_per_sample,
                               array_i* samples)
{
    int32_t i;

    samples->reset(samples);
    samples->resize(samples, block_size);

    for (i = 0; i < block_size; i++)
        a_append(samples,
                 bitstream->read_signed(bitstream, bits_per_sample));

    return OK;
}

flac_status
flacdec_read_fixed_subframe(BitstreamReader* bitstream,
                            array_i* residuals,
                            uint8_t order,
                            uint32_t block_size,
                            uint8_t bits_per_sample,
                            array_i* samples)
{
    unsigned i;
    flac_status error;
    int* s_data;
    int* r_data;

    residuals->reset(residuals);
    samples->reset(samples);

    /*ensure that samples->data won't be realloc'ated*/
    samples->resize(samples, block_size);
    s_data = samples->_;

    /*read "order" number of warm-up samples*/
    for (i = 0; i < order; i++) {
        a_append(samples,
                 bitstream->read_signed(bitstream, bits_per_sample));
    }

    /*read the residual block*/
    if ((error = flacdec_read_residual(bitstream, order,
                                       block_size, residuals)) != OK)
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
                          uint8_t order,
                          uint32_t block_size,
                          uint8_t bits_per_sample,
                          array_i* samples)
{
    unsigned i, j;
    uint32_t qlp_precision;
    int32_t qlp_shift_needed;

    int* s_data;
    int* r_data;
    int* qlp_data;
    int64_t accumulator;
    flac_status error;

    qlp_coeffs->reset(qlp_coeffs);
    residuals->reset(residuals);
    samples->reset(samples);
    samples->resize(samples, block_size);
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
        accumulator = 0;
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
                      uint8_t order,
                      uint32_t block_size,
                      array_i* residuals)
{
    uint32_t coding_method = bitstream->read(bitstream, 2);
    uint32_t partition_order = bitstream->read(bitstream, 4);
    int total_partitions = 1 << partition_order;
    int partition;
    uint32_t rice_parameter;
    uint32_t escape_code;
    uint32_t partition_samples;
    int32_t msb;
    int32_t lsb;
    int32_t value;

    unsigned int (*read)(struct BitstreamReader_s* bs, unsigned int count);
    unsigned int (*read_unary)(struct BitstreamReader_s* bs, int stop_bit);
    void (*append)(array_i* array, int value);

    read = bitstream->read;
    read_unary = bitstream->read_unary;
    append = residuals->append;

    residuals->reset(residuals);

    /*read 2^partition_order number of partitions*/
    for (partition = 0; partition < total_partitions; partition++) {
        /*each partition after the first contains
          block_size / (2 ^ partition_order) number of residual values*/
        if (partition == 0) {
            partition_samples = (block_size / (1 << partition_order)) - order;
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

        if (!escape_code) {
            for (;partition_samples; partition_samples--) {
                msb = read_unary(bitstream, 1);
                lsb = read(bitstream, rice_parameter);
                value = (msb << rice_parameter) | lsb;
                if (value & 1) {
                    append(residuals, -(value >> 1) - 1);
                } else {
                    append(residuals, value >> 1);
                }
            }
        } else {
            for (;partition_samples; partition_samples--) {
                append(residuals,
                       bitstream->read_signed(bitstream, escape_code));
            }
        }
    }

    return OK;
}


void
flacdec_decorrelate_channels(uint8_t channel_assignment,
                             array_ia* subframes,
                             array_i* framelist) {
    int* framelist_data;
    unsigned i,j;
    unsigned channel_count = subframes->len;
    unsigned block_size = subframes->_[0]->len;
    int64_t mid;
    int32_t side;

    framelist->reset(framelist);
    framelist->resize(framelist, channel_count * block_size);
    framelist_data = framelist->_;
    framelist->len = channel_count * block_size;

    switch (channel_assignment) {
    case 0x8:
        /*left-difference*/
        for (i = 0; i < block_size; i++) {
            framelist_data[i * 2] = subframes->_[0]->_[i];
            framelist_data[i * 2 + 1] = (subframes->_[0]->_[i] -
                                         subframes->_[1]->_[i]);
        }
        break;
    case 0x9:
        /*difference-right*/
        for (i = 0; i < block_size; i++) {
            framelist_data[i * 2] = (subframes->_[0]->_[i] +
                                     subframes->_[1]->_[i]);
            framelist_data[i * 2 + 1] = subframes->_[1]->_[i];
        }
        break;
    case 0xA:
        /*mid-side*/
        for (i = 0; i < block_size; i++) {
            mid = subframes->_[0]->_[i];
            side = subframes->_[1]->_[i];
            mid = (mid << 1) | (side & 1);
            framelist_data[i * 2] = (int)((mid + side) >> 1);
            framelist_data[i * 2 + 1] = (int)((mid - side) >> 1);
        }
        break;
    default:
        /*independent*/
        for (i = 0; i < block_size; i++) {
            for (j = 0; j < channel_count; j++) {
                framelist_data[i * channel_count + j] =
                    subframes->_[j]->_[i];
            }
        }
        break;
    }
}

flac_status
FlacDecoder_update_md5sum(decoders_FlacDecoder *self,
                          PyObject *framelist)
{
    PyObject *string = PyObject_CallMethod(framelist,
                                           "to_bytes","ii",
                                           0,
                                           1);
    char *string_buffer;
    Py_ssize_t length;

    if (string != NULL) {
        if (PyString_AsStringAndSize(string, &string_buffer, &length) == 0) {
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
}

int
FlacDecoder_verify_okay(decoders_FlacDecoder *self)
{
    unsigned char stream_md5sum[16];
    const static unsigned char blank_md5sum[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                                   0, 0, 0, 0, 0, 0, 0, 0};

    audiotools__MD5Final(stream_md5sum, &(self->md5));

    return ((memcmp(self->streaminfo.md5sum, blank_md5sum, 16) == 0) ||
            (memcmp(stream_md5sum, self->streaminfo.md5sum, 16) == 0));
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

uint32_t
read_utf8(BitstreamReader *stream)
{
    uint32_t total_bytes = stream->read_unary(stream, 0);
    uint32_t value = stream->read(stream, 7 - total_bytes);
    for (;total_bytes > 1; total_bytes--) {
        value = (value << 6) | (stream->read(stream, 8) & 0x3F);
    }

    return value;
}
