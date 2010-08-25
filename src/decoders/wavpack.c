#include "wavpack.h"
#include "../pcm.h"
#include "pcm.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    PyObject *args, PyObject *kwds) {
    char* filename;
    struct wavpack_block_header block_header;

    self->filename = NULL;
    self->bitstream = NULL;
    self->file = NULL;

    /*setup a bunch of temporary buffers*/
    ia_init(&(self->decorr_terms), 8);
    ia_init(&(self->decorr_deltas), 8);
    ia_init(&(self->decorr_weights_A), 8);
    ia_init(&(self->decorr_weights_B), 8);
    iaa_init(&(self->decorr_samples_A), 16, 8);
    iaa_init(&(self->decorr_samples_B), 16, 8);
    ia_init(&(self->entropy_variables_A), 3);
    ia_init(&(self->entropy_variables_B), 3);
    ia_init(&(self->values), 128);

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    /*open the WavPack file*/
    self->file = fopen(filename, "rb");
    if (self->file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = bs_open(self->file, BS_LITTLE_ENDIAN);
    }

    self->filename = strdup(filename);

    /*read as many block headers as necessary
      to determine channel count and channel mask*/
    self->sample_rate = 0;
    self->bits_per_sample = 0;
    self->channels = 0;
    self->channel_mask = 0;
    self->remaining_samples = -1;

    do {
        if (WavPackDecoder_read_block_header(self->bitstream,
                                             &block_header) == ERROR)
            return -1;
        else {
            if (self->remaining_samples == -1)
                self->remaining_samples = block_header.total_samples;

            self->sample_rate = block_header.sample_rate;
            self->bits_per_sample = block_header.bits_per_sample;
            self->channels += (block_header.mono_output ? 1 : 2);
            fseek(self->file, block_header.block_size - 24, SEEK_CUR);
            /*FIXME - determining channel mask requires sub-block parsing*/
        }
    } while (block_header.final_block_in_sequence == 0);

    iaa_init(&(self->decoded_samples), self->channels, 44100);
    fseek(self->file, 0, SEEK_SET);

    return 0;
}

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self) {
    ia_free(&(self->decorr_terms));
    ia_free(&(self->decorr_deltas));
    ia_free(&(self->decorr_weights_A));
    ia_free(&(self->decorr_weights_B));
    iaa_free(&(self->decorr_samples_A));
    iaa_free(&(self->decorr_samples_B));
    ia_free(&(self->entropy_variables_A));
    ia_free(&(self->entropy_variables_B));
    ia_free(&(self->values));

    if (self->filename != NULL)
        free(self->filename);
    if (self->channels > 0)
        iaa_free(&(self->decoded_samples));

    bs_close(self->bitstream);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
WavPackDecoder_new(PyTypeObject *type,
                   PyObject *args, PyObject *kwds) {
    decoders_WavPackDecoder *self;

    self = (decoders_WavPackDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
WavPackDecoder_sample_rate(decoders_WavPackDecoder *self, void *closure) {
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
WavPackDecoder_bits_per_sample(decoders_WavPackDecoder *self, void *closure) {
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
WavPackDecoder_channels(decoders_WavPackDecoder *self, void *closure) {
    return Py_BuildValue("i", self->channels);
}

static PyObject*
WavPackDecoder_channel_mask(decoders_WavPackDecoder *self, void *closure) {
    return Py_BuildValue("i", self->channel_mask);
}

static PyObject*
WavPackDecoder_close(decoders_WavPackDecoder* self, PyObject *args) {
    self->remaining_samples = 0;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
WavPackDecoder_offset(decoders_WavPackDecoder *self, void *closure) {
    return Py_BuildValue("i", ftell(self->bitstream->file));
}

status
WavPackDecoder_read_block_header(Bitstream* bitstream,
                                 struct wavpack_block_header* header) {
    if (!setjmp(*bs_try(bitstream))) {
        /*read and verify block ID*/
        if (bitstream->read(bitstream, 32) != 0x6B707677) {
            PyErr_SetString(PyExc_ValueError, "invalid block ID");
            goto error;
        }

        header->block_size = bitstream->read(bitstream, 32);
        header->version = bitstream->read(bitstream, 16);
        header->track_number = bitstream->read(bitstream, 8);
        header->index_number = bitstream->read(bitstream, 8);
        header->total_samples = bitstream->read_signed(bitstream, 32);
        header->block_index = bitstream->read(bitstream, 32);
        header->block_samples = bitstream->read(bitstream, 32);

        switch (bitstream->read(bitstream, 2)) {
        case 0: header->bits_per_sample = 8; break;
        case 1: header->bits_per_sample = 16; break;
        case 2: header->bits_per_sample = 24; break;
        case 3: header->bits_per_sample = 32; break;
        default: break; /*can't happen since it's a 4-bit field*/
        }

        header->mono_output = bitstream->read(bitstream, 1);
        header->hybrid_mode = bitstream->read(bitstream, 1);
        header->joint_stereo = bitstream->read(bitstream, 1);
        header->cross_channel_decorrelation = bitstream->read(bitstream, 1);
        header->hybrid_noise_shaping = bitstream->read(bitstream, 1);
        header->floating_point_data = bitstream->read(bitstream, 1);
        header->extended_size_integers = bitstream->read(bitstream, 1);
        header->hybrid_parameters_control_bitrate = bitstream->read(bitstream,
                                                                    1);
        header->hybrid_noise_balanced = bitstream->read(bitstream, 1);
        header->initial_block_in_sequence = bitstream->read(bitstream, 1);
        header->final_block_in_sequence = bitstream->read(bitstream, 1);
        header->left_shift = bitstream->read(bitstream, 5);
        header->maximum_data_magnitude = bitstream->read(bitstream, 5);

        switch (bitstream->read(bitstream, 4)) {
        case 0x0: header->sample_rate =   6000; break;
        case 0x1: header->sample_rate =   8000; break;
        case 0x2: header->sample_rate =   9600; break;
        case 0x3: header->sample_rate =  11025; break;
        case 0x4: header->sample_rate =  12000; break;
        case 0x5: header->sample_rate =  16000; break;
        case 0x6: header->sample_rate =  22050; break;
        case 0x7: header->sample_rate =  24000; break;
        case 0x8: header->sample_rate =  32000; break;
        case 0x9: header->sample_rate =  44100; break;
        case 0xA: header->sample_rate =  48000; break;
        case 0xB: header->sample_rate =  64000; break;
        case 0xC: header->sample_rate =  88200; break;
        case 0xD: header->sample_rate =  96000; break;
        case 0xE: header->sample_rate = 192000; break;
        case 0xF: header->sample_rate =      0; break; /*reserved*/
        }

        bitstream->read(bitstream, 2);
        header->use_IIR = bitstream->read(bitstream, 1);
        header->false_stereo = bitstream->read(bitstream, 1);

        if (bitstream->read(bitstream, 1) != 0) {
            PyErr_SetString(PyExc_ValueError, "invalid reserved bit");
            goto error;
        }

        header->crc = bitstream->read(bitstream, 32);

        bs_etry(bitstream);
        return OK;
    } else {
        PyErr_SetString(PyExc_IOError, "I/O error reading block header");
        goto error;
    }
 error:
    bs_etry(bitstream);
    return ERROR;
}

void
WavPackDecoder_read_subblock_header(Bitstream* bitstream,
                                    struct wavpack_subblock_header* header) {
    header->metadata_function = bitstream->read(bitstream, 5);
    header->nondecoder_data = bitstream->read(bitstream, 1);
    header->actual_size_1_less = bitstream->read(bitstream, 1);
    header->large_block = bitstream->read(bitstream, 1);
    header->block_size = bitstream->read(bitstream,
                                         header->large_block ? 24 : 8);
}

status
WavPackDecoder_read_decorr_terms(Bitstream* bitstream,
                                 struct wavpack_subblock_header* header,
                                 struct i_array* decorr_terms,
                                 struct i_array* decorr_deltas) {
    int term_count = (header->block_size * 2) -
        (header->actual_size_1_less ? 1 : 0);
    int decorr_term;

    if (term_count > MAXIMUM_TERM_COUNT) {
        PyErr_SetString(PyExc_ValueError, "excessive term count");
        return ERROR;
    }

    ia_reset(decorr_terms);
    ia_reset(decorr_deltas);

    for (; term_count > 0; term_count--) {
        decorr_term = bitstream->read(bitstream, 5) - 5;
        switch (decorr_term) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
        case 6:
        case 7:
        case 8:
        case 17:
        case 18:
        case -1:
        case -2:
        case -3:
            /* valid terms */
            break;
        default:
            /* anything else is invalid*/
            PyErr_SetString(PyExc_ValueError, "invalid decorrelation term");
            return ERROR;
        }
        ia_append(decorr_terms, decorr_term);
        ia_append(decorr_deltas, bitstream->read(bitstream, 3));
    }

    if (header->actual_size_1_less)
        bitstream->read(bitstream, 8);

    ia_reverse(decorr_terms);
    ia_reverse(decorr_deltas);

    return OK;
}

int
WavPackDecoder_restore_weight(int weight) {
    if (weight > 0) {
        return (weight << 3) + (((weight << 3) + 64) >> 7);
    } else {
        return weight << 3;
    }
}

status
WavPackDecoder_read_decorr_weights(Bitstream* bitstream,
                                   struct wavpack_subblock_header* header,
                                   int block_channel_count,
                                   int term_count,
                                   struct i_array* weights_A,
                                   struct i_array* weights_B) {
    int weight_pairs = (((header->block_size * 2) -
                         (header->actual_size_1_less ? 1 : 0)) /
                        block_channel_count);

    ia_reset(weights_A);
    ia_reset(weights_B);

    for(; weight_pairs > 0; weight_pairs--, term_count--) {
        ia_append(weights_A,
                  WavPackDecoder_restore_weight(
                        bitstream->read_signed(bitstream, 8)));
        if (block_channel_count > 1)
            ia_append(weights_B,
                      WavPackDecoder_restore_weight(
                            bitstream->read_signed(bitstream, 8)));
        else
            ia_append(weights_B, 0);
    }

    if (header->actual_size_1_less)
        bitstream->read(bitstream, 8);

    for(; term_count > 0; term_count--) {
        ia_append(weights_A, 0);
        ia_append(weights_B, 0);
    }

    ia_reverse(weights_A);
    ia_reverse(weights_B);

    return OK;
}

static int wavpack_exp2(int log) {
    int value;
    static const uint8_t exp2_table[] = {
        0x00, 0x01, 0x01, 0x02, 0x03, 0x03, 0x04, 0x05,
        0x06, 0x06, 0x07, 0x08, 0x08, 0x09, 0x0a, 0x0b,
        0x0b, 0x0c, 0x0d, 0x0e, 0x0e, 0x0f, 0x10, 0x10,
        0x11, 0x12, 0x13, 0x13, 0x14, 0x15, 0x16, 0x16,
        0x17, 0x18, 0x19, 0x19, 0x1a, 0x1b, 0x1c, 0x1d,
        0x1d, 0x1e, 0x1f, 0x20, 0x20, 0x21, 0x22, 0x23,
        0x24, 0x24, 0x25, 0x26, 0x27, 0x28, 0x28, 0x29,
        0x2a, 0x2b, 0x2c, 0x2c, 0x2d, 0x2e, 0x2f, 0x30,
        0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x35, 0x36,
        0x37, 0x38, 0x39, 0x3a, 0x3a, 0x3b, 0x3c, 0x3d,
        0x3e, 0x3f, 0x40, 0x41, 0x41, 0x42, 0x43, 0x44,
        0x45, 0x46, 0x47, 0x48, 0x48, 0x49, 0x4a, 0x4b,
        0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51, 0x51, 0x52,
        0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a,
        0x5b, 0x5c, 0x5d, 0x5e, 0x5e, 0x5f, 0x60, 0x61,
        0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f, 0x70, 0x71,
        0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
        0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81,
        0x82, 0x83, 0x84, 0x85, 0x87, 0x88, 0x89, 0x8a,
        0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92,
        0x93, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b,
        0x9c, 0x9d, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4,
        0xa5, 0xa6, 0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad,
        0xaf, 0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb6, 0xb7,
        0xb8, 0xb9, 0xba, 0xbc, 0xbd, 0xbe, 0xbf, 0xc0,
        0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc8, 0xc9, 0xca,
        0xcb, 0xcd, 0xce, 0xcf, 0xd0, 0xd2, 0xd3, 0xd4,
        0xd6, 0xd7, 0xd8, 0xd9, 0xdb, 0xdc, 0xdd, 0xde,
        0xe0, 0xe1, 0xe2, 0xe4, 0xe5, 0xe6, 0xe8, 0xe9,
        0xea, 0xec, 0xed, 0xee, 0xf0, 0xf1, 0xf2, 0xf4,
        0xf5, 0xf6, 0xf8, 0xf9, 0xfa, 0xfc, 0xfd, 0xff};

    if (log < 0) {
        return -wavpack_exp2(-log);
    }

    value = exp2_table[log & 0xFF] | 0x100;
    log >>= 8;
    if (log <= 9) {
        return (value >> (9 - log));
    } else {
        return (value << (log - 9));
    }
}

static inline ia_data_t
ia_getdefault(struct i_array *data, ia_size_t index, ia_data_t default_) {
    if (index >= data->size)
        return default_;
    else
        return data->data[index];
}

status
WavPackDecoder_read_decorr_samples(Bitstream* bitstream,
                                   struct wavpack_subblock_header* header,
                                   int block_channel_count,
                                   struct i_array* decorr_terms,
                                   struct ia_array* samples_A,
                                   struct ia_array* samples_B) {
    int i;
    int j;
    int k;
    int term;
    struct i_array samples;
    struct i_array *term_samples_A;
    struct i_array *term_samples_B;

    /*first, grab and decode a pile of decorrelation samples
      from the sub-block*/
    ia_init(&samples, decorr_terms->size);

    if (!setjmp(*bs_try(bitstream))) {
        for (i = 0; i < header->block_size; i++) {
            ia_append(&samples,
                      wavpack_exp2(bitstream->read_signed(bitstream, 16)));
        }
        bs_etry(bitstream);
    } else {
        bs_etry(bitstream);
        PyErr_SetString(PyExc_IOError,
                        "I/O error reading decorrelation samples");
        goto error;
    }

    iaa_reset(samples_A);
    iaa_reset(samples_B);
    j = 0;

    if (block_channel_count > 1) {  /*2 channel block*/
        for (i = decorr_terms->size - 1; i >= 0; i--) {
            term = decorr_terms->data[i];
            term_samples_A = &(samples_A->arrays[i]);
            term_samples_B = &(samples_B->arrays[i]);

            if ((17 <= term) && (term <= 18)) {
                ia_append(term_samples_A,
                          ia_getdefault(&samples, j + 1, 0));
                ia_append(term_samples_A,
                          ia_getdefault(&samples, j, 0));
                ia_append(term_samples_B,
                          ia_getdefault(&samples, j + 3, 0));
                ia_append(term_samples_B,
                          ia_getdefault(&samples, j + 2, 0));
                j += 4;
            } else if ((1 <= term) && (term <= 8)) {
                for (k = 0; k < term; k++) {
                    ia_append(term_samples_A,
                              ia_getdefault(&samples, j, 0));
                    ia_append(term_samples_B,
                              ia_getdefault(&samples, j + 1, 0));
                    j += 2;
                }
            } else if ((-3 <= term) && (term <= -1)) {
                ia_append(term_samples_A,
                          ia_getdefault(&samples, j, 0));
                ia_append(term_samples_B,
                          ia_getdefault(&samples, j + 1, 0));
                j += 2;
            } else {
                PyErr_SetString(PyExc_ValueError,
                                "unsupported decorrelation term");
                goto error;
            }
        }
    } else {                        /*1 channel block*/
        for (i = decorr_terms->size - 1; i >= 0; i--) {
            term = decorr_terms->data[i];
            term_samples_A = &(samples_A->arrays[i]);

            if ((17 <= term) && (term <= 18)) {
                ia_append(term_samples_A,
                          ia_getdefault(&samples, j + 1, 0));
                ia_append(term_samples_A,
                          ia_getdefault(&samples, j, 0));
                j += 2;
            } else if ((1 <= term) && (term <= 8)) {
                for (k = 0; k < term; k++) {
                    ia_append(term_samples_A,
                              ia_getdefault(&samples, j, 0));
                    j++;
                }
                ia_reverse(term_samples_A);
            } else if ((-3 <= term) && (term <= -1)) {
                ia_append(term_samples_A,
                          ia_getdefault(&samples, j, 0));
                j++;
            } else {
                PyErr_SetString(PyExc_ValueError,
                                "unsupported decorrelation term");
                goto error;
            }
        }
    }

    ia_free(&samples);
    return OK;
 error:
    ia_free(&samples);
    return ERROR;
}


status
WavPackDecoder_read_entropy_variables(Bitstream* bitstream,
                                      int block_channel_count,
                                      struct i_array* variables_A,
                                      struct i_array* variables_B) {
    ia_reset(variables_A);
    ia_reset(variables_B);

    ia_append(variables_A,
              wavpack_exp2(bitstream->read_signed(bitstream, 16)));
    ia_append(variables_A,
              wavpack_exp2(bitstream->read_signed(bitstream, 16)));
    ia_append(variables_A,
              wavpack_exp2(bitstream->read_signed(bitstream, 16)));
    if (block_channel_count > 1) {
        ia_append(variables_B,
                  wavpack_exp2(bitstream->read_signed(bitstream, 16)));
        ia_append(variables_B,
                  wavpack_exp2(bitstream->read_signed(bitstream, 16)));
        ia_append(variables_B,
                  wavpack_exp2(bitstream->read_signed(bitstream, 16)));
    } else {
        ia_append(variables_B, 0);
        ia_append(variables_B, 0);
        ia_append(variables_B, 0);
    }

    return OK;
}

status
WavPackDecoder_read_int32_info(Bitstream* bitstream,
                               int8_t* sent_bits, int8_t* zeroes,
                               int8_t* ones, int8_t* dupes) {
    *sent_bits = bitstream->read(bitstream, 8);
    *zeroes = bitstream->read(bitstream, 8);
    *ones = bitstream->read(bitstream, 8);
    *dupes = bitstream->read(bitstream, 8);

    return OK;
}

status
WavPackDecoder_read_wv_bitstream(Bitstream* bitstream,
                                 struct wavpack_subblock_header* header,
                                 struct i_array* entropy_variables_A,
                                 struct i_array* entropy_variables_B,
                                 int block_channel_count,
                                 int block_samples,
                                 struct i_array* values) {
    int value_count = block_channel_count * block_samples;
    int channel = 0;
    int holding_one = 0;
    int holding_zero = 0;
    int zeroes = 0;
    struct i_array* entropy_variables[] = {entropy_variables_A,
                                           entropy_variables_B};
    int byte_block_size = header->block_size * 2;

    bs_add_callback(bitstream, wavpack_decrement_counter, &byte_block_size);
    ia_reset(values);

    if (!setjmp(*bs_try(bitstream))) {
        while (value_count > 0) {
            if ((!holding_zero) &&
                (!holding_one) &&
                (entropy_variables_A->data[0] < 2) &&
                (entropy_variables_B->data[0] < 2)) {
                /*possibly get a chunk of 0 samples*/
                zeroes = wavpack_get_zero_count(bitstream);
                if (zeroes > 0) {
                    entropy_variables_A->data[0] = 0;
                    entropy_variables_A->data[1] = 0;
                    entropy_variables_A->data[2] = 0;
                    entropy_variables_B->data[0] = 0;
                    entropy_variables_B->data[1] = 0;
                    entropy_variables_B->data[2] = 0;

                    for (; zeroes > 0; zeroes--) {
                        ia_append(values, 0);
                        value_count--;
                        channel = (channel + 1) % block_channel_count;
                    }
                }
            }

            if (value_count > 0) {
                ia_append(values,
                          wavpack_get_value(bitstream,
                                            entropy_variables[channel],
                                            &holding_one,
                                            &holding_zero));
                value_count--;
                channel = (channel + 1) % block_channel_count;
            }
        }

        bitstream->byte_align(bitstream);
        while (byte_block_size > 0)
            bitstream->read(bitstream, 8);
        bs_pop_callback(bitstream);
        bs_etry(bitstream);

        return OK;
    } else {
        PyErr_SetString(PyExc_IOError, "I/O error reading bitstream");
        bs_pop_callback(bitstream);
        bs_etry(bitstream);

        return ERROR;
    }
}

static inline int
LOG2(int value)
{
    int bits = -1;
    while (value) {
        bits++;
        value >>= 1;
    }
    return bits;
}

int wavpack_get_value(Bitstream* bitstream,
                      struct i_array* entropy_variables,
                      int* holding_one,
                      int* holding_zero) {
    int t;
    int t2;
    int base;
    int add;
    int p;
    int e;
    int result;
    ia_data_t *medians = entropy_variables->data;

    /*The first phase is to calculate "t"
      which determines how to use/adjust our "entropy_variables".*/
    if (*holding_zero) {
        t = 0;
        *holding_zero = 0;
    } else {
        t = bitstream->read_limited_unary(bitstream, 0, 34);
        if (t == 16) {
            /*an escape code for large residuals, it seems*/
            t2 = bitstream->read_limited_unary(bitstream, 0, 34);
            if (t2 < 2)
                t += t2;
            else
                t += bitstream->read(bitstream, t2 - 1) | (1 << (t2 - 1));
        }

        if (*holding_one) {
            *holding_one = t & 1;
            *holding_zero = !*holding_one;
            t = (t >> 1) + 1;
        } else {
            *holding_one = t & 1;
            *holding_zero = !*holding_one;
            t = (t >> 1);
        }
    }

    /*The second stage is to use our "entropy_variables"
      to calculate "base" and "add".*/
    switch (t) {
    case 0:
        base = 0;
        add = medians[0] >> 4;
        medians[0] -= ((medians[0] + 126) >> 7) * 2;
        break;
    case 1:
        base = (medians[0] >> 4) + 1;
        add = medians[1] >> 4;
        medians[0] += ((medians[0] + 128) >> 7) * 5;
        medians[1] -= ((medians[1] + 62) >> 6) * 2;
        break;
    case 2:
        base = ((medians[0] >> 4) + 1) + ((medians[1] >> 4) + 1);
        add = medians[2] >> 4;
        medians[0] += ((medians[0] + 128) >> 7) * 5;
        medians[1] += ((medians[1] + 64) >> 6) * 5;
        medians[2] -= ((medians[2] + 30) >> 5) * 2;
        break;
    default:
        base = ((medians[0] >> 4) + 1) + (((medians[1] >> 4) + 1) +
             (((medians[2] >> 4) + 1) * (t - 2)));
        add = medians[2] >> 4;
        medians[0] += ((medians[0] + 128) >> 7) * 5;
        medians[1] += ((medians[1] + 64) >> 6) * 5;
        medians[2] += ((medians[2] + 32) >> 5) * 5;
        break;
    }

    /*The third stage is to use "base" and "add" to calculate
      our final value.*/
    if (add < 1) {
        if (bitstream->read(bitstream, 1))
            return ~base; /*negative*/
        else
            return base;  /*positive*/
    } else {
        p = LOG2(add);
        e = (1 << (p + 1)) - add - 1;
        if (p > 0)
            result = bitstream->read(bitstream, p);
        else
            result = 0;

        if (result >= e)
            result = (result << 1) - e + bitstream->read(bitstream, 1);

        if (bitstream->read(bitstream, 1))
            return ~(base + result);  /*negative*/
        else
            return base + result;     /*positive*/
    }
}

int wavpack_get_zero_count(Bitstream* bitstream) {
    int t;
    t = bitstream->read_limited_unary(bitstream, 0, 34);
    if (t >= 2)
        t = bitstream->read(bitstream, t - 1) | (1 << (t - 1));
    return t;
}

void wavpack_decrement_counter(int byte, void* counter) {
    int* int_counter = (int*)counter;
    *int_counter -= 1;
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

static PyObject*
ia_array_to_list(struct ia_array *list)
{
    PyObject* toreturn;
    PyObject* item;
    ia_size_t i;

    if ((toreturn = PyList_New(0)) == NULL)
        return NULL;
    else {
        for (i = 0; i < list->size; i++) {
            item = i_array_to_list(&(list->arrays[i]));
            PyList_Append(toreturn, item);
            Py_DECREF(item);
        }
        return toreturn;
    }
}

PyObject*
WavPackDecoder_read(decoders_WavPackDecoder* self,
                    struct wavpack_block_header* block_header) {
    int channels_read;
    int final_block = 0;
    int current_channel = 0;
    iaa_reset(&(self->decoded_samples));

    if (self->remaining_samples < 1)
        return ia_array_to_framelist(&(self->decoded_samples),
                                     self->bits_per_sample);

    do {
        if (WavPackDecoder_decode_block(
                    self,
                    current_channel < self->channels ?
                    &(self->decoded_samples.arrays[current_channel]) :
                    NULL,
                    (current_channel + 1) < self->channels ?
                    &(self->decoded_samples.arrays[current_channel + 1]) :
                    NULL,
                    &channels_read,
                    &final_block) == OK) {
            current_channel += channels_read;
        } else
            goto error;
    } while (!final_block);

    self->remaining_samples -= self->decoded_samples.arrays[0].size;

    return ia_array_to_framelist(&(self->decoded_samples),
                                 self->bits_per_sample);
 error:
    return NULL;
}

/*as with Shorten, whose analyze_frame() returns the next command
  (possibly only part of a total collection of PCM frames),
  this returns a single block which may be only one of several
  needed to reconstruct a multichannel set of audio*/

static PyObject*
WavPackDecoder_analyze_frame(decoders_WavPackDecoder* self, PyObject *args) {
    struct wavpack_block_header block_header;
    long block_end;
    PyObject* subblocks;
    PyObject* subblock;
    long position;

    if (self->remaining_samples > 0) {
        position = ftell(self->bitstream->file);

        self->got_decorr_terms = 0;
        self->got_decorr_weights = 0;
        self->got_decorr_samples = 0;
        self->got_entropy_variables = 0;
        self->got_bitstream = 0;
        self->got_int32_info = 0;

        if (WavPackDecoder_read_block_header(self->bitstream,
                                             &block_header) == OK) {
            subblocks = PyList_New(0);
            block_end = ftell(self->bitstream->file) +
                block_header.block_size - 24 - 1;

            if (!setjmp(*bs_try(self->bitstream))) {
                while (ftell(self->bitstream->file) < block_end) {
                    subblock = WavPackDecoder_analyze_subblock(self,
                                                               &block_header);
                    if (subblock != NULL) {
                        PyList_Append(subblocks, subblock);
                        Py_DECREF(subblock);
                    } else {
                        Py_DECREF(subblocks);
                        bs_etry(self->bitstream);
                        return NULL;
                    }
                }
                bs_etry(self->bitstream);
            } else {
                Py_DECREF(subblocks);
                bs_etry(self->bitstream);
                PyErr_SetString(PyExc_IOError,
                                "I/O error reading sub-blocks");
                return NULL;
            }

            self->remaining_samples -= block_header.block_samples;
            return Py_BuildValue(
                    "{sl sI sI si si si sI sI "
                    "si si si si si si si si si si si si si si si "
                    "si si sI sN}",
                    "offset", position,
                    "block_size", block_header.block_size,
                    "version", block_header.version,
                    "track_number", block_header.track_number,
                    "index_number", block_header.index_number,
                    "total_samples", block_header.total_samples,
                    "block_index", block_header.block_index,
                    "block_samples", block_header.block_samples,

                    "bits_per_sample", block_header.bits_per_sample,
                    "mono_output", block_header.mono_output,
                    "hybrid_mode", block_header.hybrid_mode,
                    "joint_stereo", block_header.joint_stereo,
                    "cross_channel_decorrelation",
                    block_header.cross_channel_decorrelation,
                    "hybrid_noise_shaping",
                    block_header.hybrid_noise_shaping,
                    "floating_point_data",
                    block_header.floating_point_data,
                    "extended_size_integers",
                    block_header.extended_size_integers,
                    "hybrid_parameters_control_bitrate",
                    block_header.hybrid_parameters_control_bitrate,
                    "hybrid_noise_balanced",
                    block_header.hybrid_noise_balanced,
                    "initial_block_in_sequence",
                    block_header.initial_block_in_sequence,
                    "final_block_in_sequence",
                    block_header.final_block_in_sequence,
                    "left_shift", block_header.left_shift,
                    "maximum_data_magnitude",
                    block_header.maximum_data_magnitude,
                    "sample_rate", block_header.sample_rate,

                    "use_IIR", block_header.use_IIR,
                    "false_stereo", block_header.false_stereo,
                    "crc", block_header.crc,
                    "sub_blocks", subblocks);

        } else {
            return NULL;
        }
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

PyObject*
WavPackDecoder_analyze_subblock(decoders_WavPackDecoder* self,
                                struct wavpack_block_header* block_header) {
    Bitstream* bitstream = self->bitstream;
    struct wavpack_subblock_header header;
    unsigned char* subblock_data = NULL;
    size_t data_size;
    PyObject* subblock_data_obj = NULL;

    WavPackDecoder_read_subblock_header(bitstream, &header);

    switch (header.metadata_function | (header.nondecoder_data << 5)) {
    case WV_DECORR_TERMS:
        if (WavPackDecoder_read_decorr_terms(bitstream,
                                             &header,
                                             &(self->decorr_terms),
                                             &(self->decorr_deltas)) == OK) {
            subblock_data_obj = Py_BuildValue(
                                    "{sN sN}",
                                    "decorr_terms",
                                    i_array_to_list(&(self->decorr_terms)),
                                    "decorr_deltas",
                                    i_array_to_list(&(self->decorr_deltas)));
            self->got_decorr_terms = 1;
        } else
            return NULL;
        break;
    case WV_DECORR_WEIGHTS:
        if (!self->got_decorr_terms) {
            PyErr_SetString(PyExc_ValueError,
                            "decorrelation weights found before terms");
            return NULL;
        }
        if (WavPackDecoder_read_decorr_weights(
                                bitstream,
                                &header,
                                block_header->mono_output ? 1 : 2,
                                self->decorr_terms.size,
                                &(self->decorr_weights_A),
                                &(self->decorr_weights_B)) == OK) {
            subblock_data_obj = Py_BuildValue(
                                "{sN sN}",
                                "decorr_weights_A",
                                i_array_to_list(&(self->decorr_weights_A)),
                                "decorr_weights_B",
                                i_array_to_list(&(self->decorr_weights_B)));
            self->got_decorr_weights = 1;
        } else
            return NULL;
        break;
    case WV_DECORR_SAMPLES:
        if (!self->got_decorr_terms) {
            PyErr_SetString(PyExc_ValueError,
                            "decorrelation samples found before terms");
            return NULL;
        }
        if (WavPackDecoder_read_decorr_samples(
                                bitstream,
                                &header,
                                block_header->mono_output ? 1 : 2,
                                &(self->decorr_terms),
                                &(self->decorr_samples_A),
                                &(self->decorr_samples_B)) == OK) {
            subblock_data_obj = Py_BuildValue(
                                "{sN sN}",
                                "decorr_samples_A",
                                ia_array_to_list(&(self->decorr_samples_A)),
                                "decorr_samples_B",
                                ia_array_to_list(&(self->decorr_samples_B)));
            self->got_decorr_samples = 1;
        } else
            return NULL;
        break;
    case WV_ENTROPY_VARIABLES:
        if (WavPackDecoder_read_entropy_variables(
                                bitstream,
                                block_header->mono_output ? 1 : 2,
                                &(self->entropy_variables_A),
                                &(self->entropy_variables_B)) == OK) {
            subblock_data_obj = Py_BuildValue(
                                "{sN sN}",
                                "entropy_variables_A",
                                i_array_to_list(&(self->entropy_variables_A)),
                                "entropy_variables_B",
                                i_array_to_list(&(self->entropy_variables_B)));
            self->got_entropy_variables = 1;
        } else
            return NULL;
        break;
    case WV_INT32_INFO:
        if (WavPackDecoder_read_int32_info(bitstream,
                                           &(self->int32_info.sent_bits),
                                           &(self->int32_info.zeroes),
                                           &(self->int32_info.ones),
                                           &(self->int32_info.dupes)) == OK) {
            subblock_data_obj = Py_BuildValue("{si si si si}",
                                              "sent_bits",
                                              self->int32_info.sent_bits,
                                              "zeroes",
                                              self->int32_info.zeroes,
                                              "ones",
                                              self->int32_info.ones,
                                              "dupes",
                                              self->int32_info.dupes);
            self->got_int32_info = 1;
        } else
            return NULL;
        break;
    case WV_BITSTREAM:
        if (!self->got_entropy_variables) {
            PyErr_SetString(PyExc_ValueError,
                            "bitstream found before entropy variables");
            return NULL;
        }
        if (WavPackDecoder_read_wv_bitstream(
                                   bitstream,
                                   &header,
                                   &(self->entropy_variables_A),
                                   &(self->entropy_variables_B),
                                   block_header->mono_output ? 1 : 2,
                                   block_header->block_samples,
                                   &(self->values)) == OK) {
            subblock_data_obj = i_array_to_list(&(self->values));
            self->got_bitstream = 1;
        } else
            return NULL;
        break;
    default:
        /*return a binary string for unknown subblock types*/
        data_size = header.block_size * 2;
        subblock_data = malloc(data_size);
        if (fread(subblock_data,
                  sizeof(unsigned char),
                  data_size,
                  bitstream->file) != data_size) {
            PyErr_SetString(PyExc_IOError, "I/O error reading stream");
            free(subblock_data);
            return NULL;
        } else {
            subblock_data_obj = PyString_FromStringAndSize(
                        (char*)subblock_data,
                        data_size - (header.actual_size_1_less ? 1 : 0));
            free(subblock_data);
        }
        break;
    }


    return Py_BuildValue("{sI sI sI sI sI sN}",
                         "metadata_function", header.metadata_function,
                         "nondecoder_data", header.nondecoder_data,
                         "actual_size_1_less", header.actual_size_1_less,
                         "large_block", header.large_block,
                         "sub_block_size", header.block_size,
                         "sub_block_data", subblock_data_obj);
}

status
WavPackDecoder_decode_block(decoders_WavPackDecoder* self,
                            struct i_array* channel_A,
                            struct i_array* channel_B,
                            int* channel_count,
                            int* final_block) {
    Bitstream* bitstream = self->bitstream;
    struct wavpack_block_header block_header;
    int available_channels = 0;
    long block_end;
    ia_size_t i;
    struct i_array* channels[] = {channel_A, channel_B};

    self->got_decorr_terms = 0;
    self->got_decorr_weights = 0;
    self->got_decorr_samples = 0;
    self->got_entropy_variables = 0;
    self->got_bitstream = 0;
    self->got_int32_info = 0;

    if (channel_A != NULL) {
        ia_reset(channel_A);
        available_channels++;
    }
    if (channel_B != NULL) {
        ia_reset(channel_B);
        available_channels++;
    }

    if (WavPackDecoder_read_block_header(bitstream, &block_header) == OK) {
        *channel_count = block_header.mono_output ? 1 : 2;
        *final_block = block_header.final_block_in_sequence;
        if (*channel_count > available_channels) {
            PyErr_SetString(PyExc_ValueError,
                            "too many channels requested in block header");
            goto error;
        }

        /*First, read in all the sub-block data.
          These are like arguments to the decoding routine.*/
        block_end = ftell(bitstream->file) + block_header.block_size - 24 - 1;
        if (!setjmp(*bs_try(self->bitstream))) {
            while (ftell(self->bitstream->file) < block_end) {
                if (WavPackDecoder_decode_subblock(self,
                                                   &block_header) != OK) {
                    bs_etry(bitstream);
                    goto error;
                }
            }
            bs_etry(bitstream);
        } else {
            bs_etry(bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error reading sub-block");
            goto error;
        }

        if (!self->got_bitstream) {
            PyErr_SetString(PyExc_ValueError, "residual bitstream not found");
            goto error;
        }

        /*Place the bitstream contents in channel_A and channel_B.*/
        for (i = 0; i < self->values.size; i++) {
            ia_append(channels[i % available_channels],
                      self->values.data[i]);
        }

        /*If we have decorrelation passes, run them over
         channel_A and channel_B as many times as necessary.*/
        if (self->got_decorr_terms) {
            /*FIXME - sanity check all decorrelation pass inputs here*/

            for (i = 0; i < self->decorr_terms.size; i++) {
                wavpack_perform_decorrelation_pass(
                                channel_A,
                                channel_B,
                                self->decorr_terms.data[i],
                                self->decorr_deltas.data[i],
                                self->decorr_weights_A.data[i],
                                self->decorr_weights_B.data[i],
                                &(self->decorr_samples_A.arrays[i]),
                                &(self->decorr_samples_B.arrays[i]),
                                available_channels);
            }
        }

        /*Finally, undo joint stereo if necessary.*/
        if (block_header.joint_stereo) {
            wavpack_undo_joint_stereo(channel_A, channel_B);
        }

        return OK;
    } else
        goto error;

 error:
    return ERROR;
}

status
WavPackDecoder_decode_subblock(decoders_WavPackDecoder* self,
                               struct wavpack_block_header* block_header) {
    Bitstream* bitstream = self->bitstream;
    struct wavpack_subblock_header header;

    WavPackDecoder_read_subblock_header(bitstream, &header);
    switch (header.metadata_function | (header.nondecoder_data << 5)) {
    case WV_DECORR_TERMS:
        if (WavPackDecoder_read_decorr_terms(bitstream,
                                             &header,
                                             &(self->decorr_terms),
                                             &(self->decorr_deltas)) == OK) {
            self->got_decorr_terms = 1;
            break;
        } else
            return ERROR;
    case WV_DECORR_WEIGHTS:
        if (!self->got_decorr_terms) {
            PyErr_SetString(PyExc_ValueError,
                            "decorrelation weights found before terms");
            return ERROR;
        }
        if (WavPackDecoder_read_decorr_weights(
                                bitstream,
                                &header,
                                block_header->mono_output ? 1 : 2,
                                self->decorr_terms.size,
                                &(self->decorr_weights_A),
                                &(self->decorr_weights_B)) == OK) {
            self->got_decorr_weights = 1;
            break;
        } else
            return ERROR;
    case WV_DECORR_SAMPLES:
        if (!self->got_decorr_terms) {
            PyErr_SetString(PyExc_ValueError,
                            "decorrelation samples found before terms");
            return ERROR;
        }
        if (WavPackDecoder_read_decorr_samples(
                                bitstream,
                                &header,
                                block_header->mono_output ? 1 : 2,
                                &(self->decorr_terms),
                                &(self->decorr_samples_A),
                                &(self->decorr_samples_B)) == OK) {
            self->got_decorr_samples = 1;
            break;
        } else
            return ERROR;
    case WV_ENTROPY_VARIABLES:
        if (WavPackDecoder_read_entropy_variables(
                                bitstream,
                                block_header->mono_output ? 1 : 2,
                                &(self->entropy_variables_A),
                                &(self->entropy_variables_B)) == OK) {
            self->got_entropy_variables = 1;
            break;
        } else
            return ERROR;
    case WV_INT32_INFO:
        if (WavPackDecoder_read_int32_info(bitstream,
                                           &(self->int32_info.sent_bits),
                                           &(self->int32_info.zeroes),
                                           &(self->int32_info.ones),
                                           &(self->int32_info.dupes)) == OK) {
            self->got_int32_info = 1;
            break;
        } else
            return ERROR;
    case WV_BITSTREAM:
        if (!self->got_entropy_variables) {
            PyErr_SetString(PyExc_ValueError,
                            "bitstream found before entropy variables");
            return ERROR;
        }
        if (WavPackDecoder_read_wv_bitstream(
                                   bitstream,
                                   &header,
                                   &(self->entropy_variables_A),
                                   &(self->entropy_variables_B),
                                   block_header->mono_output ? 1 : 2,
                                   block_header->block_samples,
                                   &(self->values)) == OK) {
            self->got_bitstream = 1;
            break;
        } else
            return ERROR;
    default:
        /*unsupported sub-blocks are skipped*/
        fseek(bitstream->file, header.block_size * 2, SEEK_CUR);
        break;
    }

    return OK;
}

void wavpack_perform_decorrelation_pass(
                                    struct i_array* channel_A,
                                    struct i_array* channel_B,
                                    int decorrelation_term,
                                    int decorrelation_delta,
                                    int decorrelation_weight_A,
                                    int decorrelation_weight_B,
                                    struct i_array* decorrelation_samples_A,
                                    struct i_array* decorrelation_samples_B,
                                    int channel_count) {
    struct i_array output_A;
    struct i_array output_A_tail;
    struct i_array output_B;
    struct i_array output_B_tail;
    ia_data_t output_Ai;
    ia_data_t output_Bi;
    ia_data_t output_A_1;
    ia_data_t output_B_1;
    ia_data_t input_Ai;
    ia_data_t input_Bi;
    ia_size_t i;

    if (channel_count == 1) {
        wavpack_perform_decorrelation_pass_1ch(channel_A,
                                               decorrelation_term,
                                               decorrelation_delta,
                                               decorrelation_weight_A,
                                               decorrelation_samples_A);
    } else if (decorrelation_term >= 1) {
        wavpack_perform_decorrelation_pass_1ch(channel_A,
                                               decorrelation_term,
                                               decorrelation_delta,
                                               decorrelation_weight_A,
                                               decorrelation_samples_A);
        wavpack_perform_decorrelation_pass_1ch(channel_B,
                                               decorrelation_term,
                                               decorrelation_delta,
                                               decorrelation_weight_B,
                                               decorrelation_samples_B);
    } else {
        ia_init(&output_A, channel_A->size);
        ia_extend(&output_A, decorrelation_samples_A);

        ia_init(&output_B, channel_B->size);
        ia_extend(&output_B, decorrelation_samples_B);

        switch (decorrelation_term) {
        case -1:
            for (i = 0; i < channel_A->size; i++) {
                input_Ai = channel_A->data[i];
                input_Bi = channel_B->data[i];
                output_A_1 = ia_getitem(&(output_A), -1);
                output_B_1 = ia_getitem(&(output_B), -1);
                output_Ai = (((decorrelation_weight_A * output_B_1) +
                              512) >> 10) + input_Ai;
                ia_append(&output_A, output_Ai);
                if ((output_B_1 != 0) && (input_Ai != 0)) {
                    if ((output_B_1 ^ input_Ai) >= 0)
                        decorrelation_weight_A = MIN(
                                decorrelation_weight_A + decorrelation_delta,
                                WEIGHT_MAXIMUM);
                    else
                        decorrelation_weight_A = MAX(
                                decorrelation_weight_A - decorrelation_delta,
                                WEIGHT_MINIMUM);
                }
                ia_append(&output_B,
                          (((decorrelation_weight_B * output_Ai) +
                            512) >> 10) + input_Bi);
                if ((output_Ai != 0) && (input_Bi != 0)) {
                    if ((output_Ai ^ input_Bi) >= 0)
                        decorrelation_weight_B = MIN(
                                decorrelation_weight_B + decorrelation_delta,
                                WEIGHT_MAXIMUM);
                    else
                        decorrelation_weight_B = MAX(
                                decorrelation_weight_B - decorrelation_delta,
                                WEIGHT_MINIMUM);
                }
            }
            break;
        case -2:
            for (i = 0; i < channel_B->size; i++) {
                input_Bi = channel_B->data[i];
                input_Ai = channel_A->data[i];
                output_B_1 = ia_getitem(&(output_B), -1);
                output_A_1 = ia_getitem(&(output_A), -1);
                output_Bi = (((decorrelation_weight_B * output_A_1) +
                              512) >> 10) + input_Bi;
                ia_append(&output_B, output_Bi);
                if ((output_A_1 != 0) && (input_Bi != 0)) {
                    if ((output_A_1 ^ input_Bi) >= 0)
                        decorrelation_weight_B = MIN(
                                decorrelation_weight_B + decorrelation_delta,
                                WEIGHT_MAXIMUM);
                    else
                        decorrelation_weight_B = MAX(
                                decorrelation_weight_B - decorrelation_delta,
                                WEIGHT_MINIMUM);
                }
                ia_append(&output_A,
                          (((decorrelation_weight_A * output_Bi) +
                            512) >> 10) + input_Ai);
                if ((output_Bi != 0) && (input_Ai != 0)) {
                    if ((output_Bi ^ input_Ai) >= 0)
                        decorrelation_weight_A = MIN(
                                decorrelation_weight_A + decorrelation_delta,
                                WEIGHT_MAXIMUM);
                    else
                        decorrelation_weight_A = MAX(
                                decorrelation_weight_A - decorrelation_delta,
                                WEIGHT_MINIMUM);
                }
            }
            break;
        case -3:
            for (i = 0; i < channel_A->size; i++) {
                input_Bi = channel_B->data[i];
                input_Ai = channel_A->data[i];
                output_B_1 = ia_getitem(&(output_B), -1);
                output_A_1 = ia_getitem(&(output_A), -1);
                output_Ai = (((decorrelation_weight_A * output_B_1) +
                              512) >> 10) + input_Ai;
                output_Bi = (((decorrelation_weight_B * output_A_1) +
                              512) >> 10) + input_Bi;
                ia_append(&(output_A), output_Ai);
                ia_append(&(output_B), output_Bi);
                if ((output_B_1 != 0) && (input_Ai != 0)) {
                    if ((output_B_1 ^ input_Ai) >= 0)
                        decorrelation_weight_A = MIN(
                                decorrelation_weight_A + decorrelation_delta,
                                WEIGHT_MAXIMUM);
                    else
                        decorrelation_weight_A = MAX(
                                decorrelation_weight_A - decorrelation_delta,
                                WEIGHT_MINIMUM);
                }
                if ((output_A_1 != 0) && (input_Bi != 0)) {
                    if ((output_A_1 ^ input_Bi) >= 0)
                        decorrelation_weight_B = MIN(
                                decorrelation_weight_B + decorrelation_delta,
                                WEIGHT_MAXIMUM);
                    else
                        decorrelation_weight_B = MAX(
                                decorrelation_weight_B - decorrelation_delta,
                                WEIGHT_MINIMUM);
                }
            }
        }

        ia_tail(&output_A_tail, &output_A, channel_A->size);
        ia_tail(&output_B_tail, &output_B, channel_B->size);
        ia_copy(channel_A, &output_A_tail);
        ia_copy(channel_B, &output_B_tail);
        ia_free(&output_A);
        ia_free(&output_B);
    }
}

void wavpack_perform_decorrelation_pass_1ch(
                                    struct i_array* channel,
                                    int decorrelation_term,
                                    int decorrelation_delta,
                                    int decorrelation_weight,
                                    struct i_array* decorrelation_samples) {
    struct i_array output;
    struct i_array output_tail;
    int64_t temp;
    ia_data_t input_i;
    ia_size_t i;

    ia_init(&output, channel->size + decorrelation_samples->size);
    ia_extend(&output, decorrelation_samples);

    switch (decorrelation_term) {
    case 18:
        for (i = 0; i < channel->size; i++) {
            input_i = channel->data[i];
            temp = ((3 * ia_getitem(&output, -1)) -
                    ia_getitem(&output, -2)) >> 1;
            ia_append(&output, (((decorrelation_weight * temp) + 512) >> 10) +
                      input_i);
            if ((temp != 0) && (input_i != 0)) {
                if ((temp ^ input_i) >= 0)
                    decorrelation_weight += decorrelation_delta;
                else
                    decorrelation_weight -= decorrelation_delta;
            }
        }
        break;
    case 17:
        for (i = 0; i < channel->size; i++) {
            input_i = channel->data[i];
            temp = (2 * ia_getitem(&output, -1)) - ia_getitem(&output, -2);
            ia_append(&output, (((decorrelation_weight * temp) + 512) >> 10) +
                      input_i);
            if ((temp != 0) && (input_i != 0)) {
                if ((temp ^ input_i) >= 0)
                    decorrelation_weight += decorrelation_delta;
                else
                    decorrelation_weight -= decorrelation_delta;
            }
        }
        break;
    case 1:
    case 2:
    case 3:
    case 4:
    case 5:
    case 6:
    case 7:
    case 8:
        for (i = 0; i < channel->size; i++) {
            input_i = channel->data[i];
            temp = ia_getitem(&output, -decorrelation_term);
            ia_append(&output,
                      (((decorrelation_weight * temp) + 512) >> 10) +
                      input_i);
            if ((temp != 0) && (input_i != 0)) {
                if ((temp ^ input_i) >= 0)
                    decorrelation_weight += decorrelation_delta;
                else
                    decorrelation_weight -= decorrelation_delta;
            }
        }
        break;
    }

    ia_tail(&output_tail, &output, channel->size);
    ia_copy(channel, &output_tail);
    ia_free(&output);
}

void wavpack_undo_joint_stereo(struct i_array* channel_A,
                               struct i_array* channel_B) {
    ia_size_t i;
    ia_data_t mid;
    ia_data_t side;

    for (i = 0; i < channel_A->size; i++) {
        mid = channel_A->data[i];
        side = channel_B->data[i];
        side -= (mid >> 1);
        mid += side;
        channel_A->data[i] = mid;
        channel_B->data[i] = side;
    }
}

#include "pcm.c"
