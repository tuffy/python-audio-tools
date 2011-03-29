#include "flac.h"
#include "../pcm.h"
#include "pcm.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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

    self->filename = NULL;
    self->file = NULL;
    self->bitstream = NULL;
    self->residuals = ia_blank();
    self->qlp_coeffs = ia_blank();
    self->remaining_samples = 0;

    if (!PyArg_ParseTuple(args, "si", &filename, &(self->channel_mask)))
        return -1;

    /*open the flac file*/
    self->file = fopen(filename, "rb");
    if (self->file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = bs_open(self->file, BS_BIG_ENDIAN);
    }

    self->filename = strdup(filename);

    /*read the STREAMINFO block and setup the total number of samples to read*/
    if (FlacDecoder_read_metadata(self) == ERROR) {
        self->streaminfo.channels = 0;
        return -1;
    }

    self->remaining_samples = self->streaminfo.total_samples;

    /*initialize the output MD5 sum*/
    audiotools__MD5Init(&(self->md5));
    self->stream_finalized = 0;

    /*add callbacks for CRC8 and CRC16 calculation*/
    bs_add_callback(self->bitstream, flac_crc8, &(self->crc8));
    bs_add_callback(self->bitstream, flac_crc16, &(self->crc16));

    /*setup a bunch of temporary buffers*/
    iaa_init(&(self->subframe_data),
             self->streaminfo.channels,
             self->streaminfo.maximum_block_size);
    ia_init(&(self->residuals), self->streaminfo.maximum_block_size);
    ia_init(&(self->qlp_coeffs), 1);

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
    iaa_free(&(self->subframe_data));
    ia_free(&(self->residuals));
    ia_free(&(self->qlp_coeffs));

    if (self->filename != NULL)
        free(self->filename);

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

status
FlacDecoder_read_metadata(decoders_FlacDecoder *self)
{
    unsigned int last_block;
    unsigned int block_type;
    unsigned int block_length;

    if (!setjmp(*bs_try(self->bitstream))) {
        if (self->bitstream->read(self->bitstream, 32) != 0x664C6143u) {
            PyErr_SetString(PyExc_ValueError, "not a FLAC file");
            goto error;
        }

        last_block = self->bitstream->read(self->bitstream, 1);
        block_type = self->bitstream->read(self->bitstream, 7);
        block_length = self->bitstream->read(self->bitstream, 24);

        if (block_type == 0) {
            self->streaminfo.minimum_block_size = self->bitstream->read(
                                        self->bitstream, 16);
            self->streaminfo.maximum_block_size = self->bitstream->read(
                                        self->bitstream, 16);
            self->streaminfo.minimum_frame_size = self->bitstream->read(
                                        self->bitstream, 24);
            self->streaminfo.maximum_frame_size = self->bitstream->read(
                                        self->bitstream, 24);
            self->streaminfo.sample_rate = self->bitstream->read(
                                        self->bitstream, 20);
            self->streaminfo.channels = self->bitstream->read(
                                        self->bitstream, 3) + 1;
            self->streaminfo.bits_per_sample = self->bitstream->read(
                                        self->bitstream, 5) + 1;
            self->streaminfo.total_samples = self->bitstream->read_64(
                                        self->bitstream, 36);
            if (fread(self->streaminfo.md5sum, sizeof(unsigned char),
                      16, self->file) != 16) {
                PyErr_SetString(PyExc_IOError, "unable to read md5sum");
                goto error;
            }
        } else {
            PyErr_SetString(PyExc_ValueError,
                            "STREAMINFO not first metadata block");
            goto error;
        }

        while (!last_block) {
            last_block = self->bitstream->read(self->bitstream, 1);
            block_type = self->bitstream->read(self->bitstream, 7);
            block_length = self->bitstream->read(self->bitstream, 24);
            if (fseek(self->file, block_length, SEEK_CUR) == -1) {
                PyErr_SetFromErrno(PyExc_ValueError);
                goto error;
            }
        }

        bs_etry(self->bitstream);
        return OK;
    } else {
        PyErr_SetString(PyExc_IOError,
                        "EOF while reading STREAMINFO block");
        goto error;
    }

 error:
    bs_etry(self->bitstream);
    return ERROR;
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
    PyObject *framelist;
    PyThreadState *thread_state;
    status error;

    iaa_reset(&(self->subframe_data));

    /*if all samples have been read, return an empty FrameList*/
    if (self->stream_finalized) {
        return ia_array_to_framelist(&(self->subframe_data),
                                     self->streaminfo.bits_per_sample);
    }

    if (self->remaining_samples < 1) {
        self->stream_finalized = 1;

        if (FlacDecoder_verify_okay(self))
            return ia_array_to_framelist(&(self->subframe_data),
                                         self->streaminfo.bits_per_sample);
        else {
            PyErr_SetString(PyExc_ValueError,
                            "MD5 mismatch at end of stream");
            return NULL;
        }
    }

    thread_state = PyEval_SaveThread();
    self->crc8 = self->crc16 = 0;

    if (!setjmp(*bs_try(self->bitstream))) {
        if ((error = FlacDecoder_read_frame_header(self,
                                                   &frame_header)) != OK) {
            PyEval_RestoreThread(thread_state);
            PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
            goto error;
        }

        for (channel = 0; channel < frame_header.channel_count; channel++)
            if ((error = FlacDecoder_read_subframe(
                        self,
                        MIN(frame_header.block_size,
                            self->remaining_samples),
                        FlacDecoder_subframe_bits_per_sample(&frame_header,
                                                             channel),
                        &(self->subframe_data.arrays[channel]))) != OK) {
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
                goto error;
            }

        /*handle difference channels, if any*/
        FlacDecoder_decorrelate_channels(&frame_header,
                                         &(self->subframe_data));

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
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "EOF reading frame");
        goto error;
    }

    bs_etry(self->bitstream);
    PyEval_RestoreThread(thread_state);

    framelist = ia_array_to_framelist(&(self->subframe_data),
                                      frame_header.bits_per_sample);

    /*update MD5 sum*/
    if (FlacDecoder_update_md5sum(self, framelist) == OK)
        /*return pcm.FrameList Python object*/
        return framelist;
    else {
        Py_DECREF(framelist);
        return NULL;
    }
 error:
    bs_etry(self->bitstream);
    return NULL;
}

PyObject*
FlacDecoder_analyze_frame(decoders_FlacDecoder* self, PyObject *args)
{
    struct flac_frame_header frame_header;
    int channel;
    int offset;
    PyObject *subframe;
    PyObject *subframes;
    status error;

    /*if all samples have been read, return None*/
    if (self->remaining_samples < 1) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    offset = bs_ftell(self->bitstream);

    self->crc8 = self->crc16 = 0;

    if (!setjmp(*bs_try(self->bitstream))) {
        if ((error = FlacDecoder_read_frame_header(self,
                                                   &frame_header)) != OK) {
            PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
            goto error;
        }

        subframes = PyList_New(0);
        for (channel = 0; channel < frame_header.channel_count; channel++) {
            subframe = FlacDecoder_analyze_subframe(
                        self,
                        frame_header.block_size,
                        FlacDecoder_subframe_bits_per_sample(&frame_header,
                                                             channel));
            if (subframe != NULL) {
                PyList_Append(subframes, subframe);
                Py_DECREF(subframe);
            } else
                goto error;
        }

        /*check CRC-16*/
        self->bitstream->byte_align(self->bitstream);
        self->bitstream->read(self->bitstream, 16);
        if (self->crc16 != 0) {
            PyErr_SetString(PyExc_ValueError, "invalid checksum in frame");
            goto error;
        }

        /*decrement remaining samples*/
        self->remaining_samples -= frame_header.block_size;
    } else {
        PyErr_SetString(PyExc_IOError, "EOF reading frame");
        goto error;
    }

    bs_etry(self->bitstream);

    /*return frame analysis*/
    return Py_BuildValue("{si si si si si sK sN si}",
                         "block_size", frame_header.block_size,
                         "sample_rate", frame_header.sample_rate,
                         "channel_assignment", frame_header.channel_assignment,
                         "channel_count", frame_header.channel_count,
                         "bits_per_sample", frame_header.bits_per_sample,
                         "frame_number", frame_header.frame_number,
                         "subframes", subframes,
                         "offset", offset);
 error:
    bs_etry(self->bitstream);
    return NULL;
}


status
FlacDecoder_read_frame_header(decoders_FlacDecoder *self,
                              struct flac_frame_header *header)
{
    Bitstream *bitstream = self->bitstream;
    uint32_t block_size_bits;
    uint32_t sample_rate_bits;

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
        header->bits_per_sample = self->streaminfo.bits_per_sample; break;
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
    case 0x0: header->block_size = self->streaminfo.maximum_block_size; break;
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
    case 0x0: header->sample_rate = self->streaminfo.sample_rate; break;
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
    if (self->crc8 != 0) {
        return ERR_INVALID_FRAME_CRC;
    }

    /*Once we've read everything,
      ensure the values are compatible with STREAMINFO.*/

    if (self->streaminfo.sample_rate != header->sample_rate) {
        return ERR_SAMPLE_RATE_MISMATCH;
    }
    if (self->streaminfo.channels != header->channel_count) {
        return ERR_CHANNEL_COUNT_MISMATCH;
    }
    if (self->streaminfo.bits_per_sample != header->bits_per_sample) {
        return ERR_BITS_PER_SAMPLE_MISMATCH;
    }
    if (header->block_size > self->streaminfo.maximum_block_size) {
        return ERR_MAXIMUM_BLOCK_SIZE_EXCEEDED;
    }

    return OK;
}

status
FlacDecoder_read_subframe(decoders_FlacDecoder *self,
                          uint32_t block_size,
                          uint8_t bits_per_sample,
                          struct i_array *samples)
{
    struct flac_subframe_header subframe_header;
    uint32_t i;
    status error = OK;

    if (FlacDecoder_read_subframe_header(self, &subframe_header) == ERROR)
        return ERROR;

    /*account for wasted bits-per-sample*/
    if (subframe_header.wasted_bits_per_sample > 0)
        bits_per_sample -= subframe_header.wasted_bits_per_sample;

    switch (subframe_header.type) {
    case FLAC_SUBFRAME_CONSTANT:
        error = FlacDecoder_read_constant_subframe(self,
                                                   block_size,
                                                   bits_per_sample,
                                                   samples);
        break;
    case FLAC_SUBFRAME_VERBATIM:
        error = FlacDecoder_read_verbatim_subframe(self,
                                                   block_size,
                                                   bits_per_sample,
                                                   samples);
        break;
    case FLAC_SUBFRAME_FIXED:
        error = FlacDecoder_read_fixed_subframe(self,
                                                subframe_header.order,
                                                block_size,
                                                bits_per_sample,
                                                samples);
        break;
    case FLAC_SUBFRAME_LPC:
        error = FlacDecoder_read_lpc_subframe(self,
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
            ia_setitem(samples, i, ia_getitem(samples, i) <<
                       subframe_header.wasted_bits_per_sample);

    return OK;
}

status
FlacDecoder_read_subframe_header(decoders_FlacDecoder *self,
                                 struct flac_subframe_header *subframe_header)
{
    Bitstream *bitstream = self->bitstream;
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

int
FlacDecoder_subframe_bits_per_sample(struct flac_frame_header *frame_header,
                                     int channel_number) {
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

status
FlacDecoder_read_constant_subframe(decoders_FlacDecoder *self,
                                   uint32_t block_size,
                                   uint8_t bits_per_sample,
                                   struct i_array *samples)
{
    int32_t value = self->bitstream->read_signed(self->bitstream,
                                                 bits_per_sample);
    int32_t i;

    ia_reset(samples);

    for (i = 0; i < block_size; i++)
        ia_append(samples, value);

    return OK;
}

status
FlacDecoder_read_verbatim_subframe(decoders_FlacDecoder *self,
                                   uint32_t block_size,
                                   uint8_t bits_per_sample,
                                   struct i_array *samples)
{
    int32_t i;

    ia_reset(samples);
    for (i = 0; i < block_size; i++)
        ia_append(samples, self->bitstream->read_signed(self->bitstream,
                                                        bits_per_sample));

    return OK;
}

status
FlacDecoder_read_fixed_subframe(decoders_FlacDecoder *self,
                                uint8_t order,
                                uint32_t block_size,
                                uint8_t bits_per_sample,
                                struct i_array *samples)
{
    int32_t i;
    Bitstream *bitstream = self->bitstream;
    struct i_array *residuals = &(self->residuals);
    status error;

    ia_reset(residuals);
    ia_reset(samples);

    /*read "order" number of warm-up samples*/
    for (i = 0; i < order; i++) {
        ia_append(samples, bitstream->read_signed(bitstream, bits_per_sample));
    }

    /*read the residual*/
    if ((error = FlacDecoder_read_residual(self, order,
                                           block_size, residuals)) != OK)
        return error;

    /*calculate subframe samples from warm-up samples and residual*/
    switch (order) {
    case 0:
        for (i = 0; i < residuals->size; i++) {
            ia_append(samples,
                      ia_getitem(residuals, i));
        }
        break;
    case 1:
        for (i = 0; i < residuals->size; i++) {
            ia_append(samples,
                      ia_getitem(samples, -1) +
                      ia_getitem(residuals, i));
        }
        break;
    case 2:
        for (i = 0; i < residuals->size; i++) {
            ia_append(samples,
                      (2 * ia_getitem(samples, -1)) -
                      ia_getitem(samples, -2) +
                      ia_getitem(residuals, i));
        }
        break;
    case 3:
        for (i = 0; i < residuals->size; i++) {
            ia_append(samples,
                      (3 * ia_getitem(samples, -1)) -
                      (3 * ia_getitem(samples, -2)) +
                      ia_getitem(samples, -3) +
                      ia_getitem(residuals, i));
        }
        break;
    case 4:
        for (i = 0; i < residuals->size; i++) {
            ia_append(samples,
                      (4 * ia_getitem(samples, -1)) -
                      (6 * ia_getitem(samples, -2)) +
                      (4 * ia_getitem(samples, -3)) -
                      ia_getitem(samples, -4) +
                      ia_getitem(residuals, i));
        }
        break;
    default:
        return ERR_INVALID_FIXED_ORDER;
    }

    return OK;
}

status
FlacDecoder_read_lpc_subframe(decoders_FlacDecoder *self,
                              uint8_t order,
                              uint32_t block_size,
                              uint8_t bits_per_sample,
                              struct i_array *samples)
{
    int i, j;
    Bitstream *bitstream = self->bitstream;
    uint32_t qlp_precision;
    int32_t qlp_shift_needed;
    struct i_array tail;
    int64_t accumulator;

    struct i_array *qlp_coeffs = &(self->qlp_coeffs);
    struct i_array *residuals = &(self->residuals);
    status error;

    ia_reset(residuals);
    ia_reset(samples);
    ia_reset(qlp_coeffs);

    /*read order number of warm-up samples*/
    for (i = 0; i < order; i++) {
        ia_append(samples, bitstream->read_signed(bitstream, bits_per_sample));
    }

    /*read QLP precision*/
    qlp_precision = bitstream->read(bitstream, 4) + 1;

    /*read QLP shift needed*/
    qlp_shift_needed = bitstream->read_signed(bitstream, 5);

    /*read order number of QLP coefficients of size qlp_precision*/
    for (i = 0; i < order; i++) {
        ia_append(qlp_coeffs, bitstream->read_signed(bitstream,
                                                     qlp_precision));
    }
    ia_reverse(qlp_coeffs);

    /*read the residual*/
    if ((error = FlacDecoder_read_residual(self, order,
                                           block_size, residuals)) != OK)
        return error;

    /*calculate subframe samples from warm-up samples and residual*/
    for (i = 0; i < residuals->size; i++) {
        accumulator = 0;
        ia_tail(&tail, samples, order);
        for (j = 0; j < order; j++) {
            accumulator += (int64_t)ia_getitem(&tail, j) *
                (int64_t)ia_getitem(qlp_coeffs, j);
        }
        ia_append(samples,
                  (accumulator >> qlp_shift_needed) +
                  ia_getitem(residuals, i));
    }

    return OK;
}

status
FlacDecoder_read_residual(decoders_FlacDecoder *self,
                          uint8_t order,
                          uint32_t block_size,
                          struct i_array *residuals)
{
    Bitstream *bitstream = self->bitstream;
    uint32_t coding_method = bitstream->read(bitstream, 2);
    uint32_t partition_order = bitstream->read(bitstream, 4);
    int total_partitions = 1 << partition_order;
    int partition;
    uint32_t rice_parameter;
    uint32_t escape_code;
    uint32_t partition_samples;
    uint32_t sample;
    int32_t msb;
    int32_t lsb;
    int32_t value;
    ia_data_t *residuals_data;

    unsigned int (*read)(struct Bitstream_s* bs, unsigned int count);
    unsigned int (*read_unary)(struct Bitstream_s* bs, int stop_bit);

    read = bitstream->read;
    read_unary = bitstream->read_unary;

    ia_resize(residuals, block_size - order);
    residuals->size = block_size - order;
    residuals_data = residuals->data;
    sample = 0;

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
                    residuals_data[sample++] = -(value >> 1) - 1;
                } else {
                    residuals_data[sample++] = value >> 1;
                }
            }
        } else {
            for (;partition_samples; partition_samples--) {
                residuals_data[sample++] = bitstream->read_signed(bitstream,
                                                                  escape_code);
            }
        }
    }

    return OK;
}


void
FlacDecoder_decorrelate_channels(struct flac_frame_header *frame_header,
                                 struct ia_array *subframe_data) {
    int32_t i;
    int64_t mid;
    int32_t side;

    switch (frame_header->channel_assignment) {
    case 0x8:
        /*left-difference*/
        ia_sub(&(subframe_data->arrays[1]),
               &(subframe_data->arrays[0]), &(subframe_data->arrays[1]));
        break;
    case 0x9:
        /*difference-right*/
        ia_add(&(subframe_data->arrays[0]),
               &(subframe_data->arrays[0]), &(subframe_data->arrays[1]));
        break;
    case 0xA:
        /*mid-side*/
        for (i = 0; i < frame_header->block_size; i++) {
            mid = subframe_data->arrays[0].data[i];
            side = subframe_data->arrays[1].data[i];
            mid = (mid << 1) | (side & 1);
            subframe_data->arrays[0].data[i] = (mid + side) >> 1;
            subframe_data->arrays[1].data[i] = (mid - side) >> 1;
        }
        break;
    default:
        /*do nothing for independent channels*/
        break;
    }
}


static PyObject*
i_array_to_list(struct i_array *list)
{
    PyObject* toreturn;
    PyObject* item;
    ia_size_t i;

    if ((toreturn = PyList_New(0)) == NULL)
        return NULL;
    else {
        for (i = 0; i < list->size; i++) {
            item = PyInt_FromLong(list->data[i]);
            PyList_Append(toreturn, item);
            Py_DECREF(item);
        }
        return toreturn;
    }
}

PyObject*
FlacDecoder_analyze_subframe(decoders_FlacDecoder *self,
                             uint32_t block_size,
                             uint8_t bits_per_sample)
{
    struct flac_subframe_header subframe_header;
    PyObject* subframe = NULL;

    if (FlacDecoder_read_subframe_header(self, &subframe_header) == ERROR)
        return NULL;

    /*account for wasted bits-per-sample*/
    if (subframe_header.wasted_bits_per_sample > 0)
        bits_per_sample -= subframe_header.wasted_bits_per_sample;

    switch (subframe_header.type) {
    case FLAC_SUBFRAME_CONSTANT:
        subframe = FlacDecoder_analyze_constant_subframe(self, block_size,
                                                         bits_per_sample);
        break;
    case FLAC_SUBFRAME_VERBATIM:
        subframe = FlacDecoder_analyze_verbatim_subframe(self, block_size,
                                                         bits_per_sample);
        break;
    case FLAC_SUBFRAME_FIXED:
        subframe = FlacDecoder_analyze_fixed_subframe(self,
                                                      subframe_header.order,
                                                      block_size,
                                                      bits_per_sample);
        break;
    case FLAC_SUBFRAME_LPC:
        subframe = FlacDecoder_analyze_lpc_subframe(self,
                                                    subframe_header.order,
                                                    block_size,
                                                    bits_per_sample);
        break;
    }

    return Py_BuildValue("{si si si sN}",
                         "type", subframe_header.type,
                         "order", subframe_header.order,
                         "wasted_bps", subframe_header.wasted_bits_per_sample,
                         "data", subframe);
}

PyObject*
FlacDecoder_analyze_constant_subframe(decoders_FlacDecoder *self,
                                      uint32_t block_size,
                                      uint8_t bits_per_sample)
{
    return PyInt_FromLong(self->bitstream->read_signed(self->bitstream,
                                                       bits_per_sample));
}

PyObject*
FlacDecoder_analyze_verbatim_subframe(decoders_FlacDecoder *self,
                                      uint32_t block_size,
                                      uint8_t bits_per_sample)
{
    PyObject *toreturn;
    struct i_array samples;
    int32_t i;

    ia_init(&samples, block_size);
    for (i = 0; i < block_size; i++)
        ia_append(&samples,
                  self->bitstream->read_signed(self->bitstream,
                                               bits_per_sample));

    toreturn = i_array_to_list(&samples);
    ia_free(&samples);
    return toreturn;
}

PyObject*
FlacDecoder_analyze_fixed_subframe(decoders_FlacDecoder *self,
                                   uint8_t order,
                                   uint32_t block_size,
                                   uint8_t bits_per_sample)
{
    struct i_array warm_up_samples;
    int32_t i;
    PyObject *warm_up_obj;
    PyObject *residual_obj;

    /*read "order" number of warm-up samples*/
    ia_init(&warm_up_samples, order);
    for (i = 0; i < order; i++) {
        ia_append(&warm_up_samples,
                  self->bitstream->read_signed(self->bitstream,
                                               bits_per_sample));
    }
    warm_up_obj = i_array_to_list(&warm_up_samples);
    ia_free(&warm_up_samples);

    /*read the residual*/
    residual_obj = FlacDecoder_analyze_residual(self, order, block_size);

    return Py_BuildValue("{sN sN}",
                         "warm_up", warm_up_obj,
                         "residual", residual_obj);
}

PyObject*
FlacDecoder_analyze_lpc_subframe(decoders_FlacDecoder *self,
                                 uint8_t order,
                                 uint32_t block_size,
                                 uint8_t bits_per_sample)
{
    int i;
    uint32_t qlp_precision;
    int32_t shift_needed;
    struct i_array warm_up_samples;
    struct i_array qlp_coefficients;
    PyObject *warm_up_obj;
    PyObject *coefficients_obj;
    PyObject *residual_obj;

    /*read order number of warm-up samples*/
    ia_init(&warm_up_samples, order);
    for (i = 0; i < order; i++) {
        ia_append(&warm_up_samples,
                  self->bitstream->read_signed(self->bitstream,
                                               bits_per_sample));
    }
    warm_up_obj = i_array_to_list(&warm_up_samples);
    ia_free(&warm_up_samples);

    /*read QLP precision*/
    qlp_precision = self->bitstream->read(self->bitstream, 4) + 1;

    /*read QLP shift needed*/
    shift_needed = self->bitstream->read_signed(self->bitstream, 5);

    /*read order number of QLP coefficients of size qlp_precision*/
    ia_init(&qlp_coefficients, order);
    for (i = 0; i < order; i++) {
        ia_append(&qlp_coefficients,
                  self->bitstream->read_signed(self->bitstream,
                                               qlp_precision));
    }
    coefficients_obj = i_array_to_list(&qlp_coefficients);

    /*read the residual*/
    residual_obj = FlacDecoder_analyze_residual(self, order, block_size);

    return Py_BuildValue("{si si sN sN sN}",
                         "qlp_precision", qlp_precision,
                         "qlp_shift_needed", shift_needed,
                         "warm_up", warm_up_obj,
                         "coefficients", coefficients_obj,
                         "residual", residual_obj);
}

PyObject*
FlacDecoder_analyze_residual(decoders_FlacDecoder *self,
                             uint8_t order,
                             uint32_t block_size)
{
    struct i_array residuals;
    PyObject *toreturn;
    status error;

    ia_init(&residuals, block_size);
    if ((error = FlacDecoder_read_residual(self, order,
                                           block_size, &residuals)) == OK) {
        toreturn = i_array_to_list(&residuals);
        ia_free(&residuals);
        return toreturn;
    } else {
        PyErr_SetString(PyExc_ValueError, FlacDecoder_strerror(error));
        return NULL;
    }
}

status
FlacDecoder_update_md5sum(decoders_FlacDecoder *self,
                          PyObject *framelist) {
    PyObject *string = PyObject_CallMethod(
                                framelist,
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
FlacDecoder_verify_okay(decoders_FlacDecoder *self) {
    unsigned char stream_md5sum[16];

    audiotools__MD5Final(stream_md5sum, &(self->md5));

    return (memcmp(stream_md5sum, self->streaminfo.md5sum, 16) == 0);
}

const char*
FlacDecoder_strerror(status error) {
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
read_utf8(Bitstream *stream)
{
    uint32_t total_bytes = stream->read_unary(stream, 0);
    uint32_t value = stream->read(stream, 7 - total_bytes);
    for (;total_bytes > 1; total_bytes--) {
        value = (value << 6) | (stream->read(stream, 8) & 0x3F);
    }

    return value;
}

#include "pcm.c"
