#include "wavpack.h"
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
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    PyObject *args, PyObject *kwds) {
    char* filename;
    struct wavpack_block_header block_header;
    struct wavpack_subblock_header sub_block_header;
    uint32_t block_length;
    status error;

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
        if ((error = WavPackDecoder_read_block_header(self->bitstream,
                                                      &block_header)) != OK) {
            PyErr_SetString(PyExc_ValueError, wavpack_strerror(error));
            return -1;
        } else {
            if (!setjmp(*bs_try(self->bitstream))) {
                if (self->remaining_samples == -1)
                    self->remaining_samples = block_header.total_samples;

                self->sample_rate = block_header.sample_rate;
                self->bits_per_sample = block_header.bits_per_sample;
                self->channels += (block_header.mono_output ? 1 : 2);

                /*parse sub-blocks as necessary to find a channel mask*/
                block_length = block_header.block_size - 24;
                while (block_length > 0) {
                    WavPackDecoder_read_subblock_header(self->bitstream,
                                                        &sub_block_header);
                    block_length -= (sub_block_header.large_block ? 4 : 2);
                    if ((sub_block_header.metadata_function ==
                         WV_CHANNEL_INFO) &&
                        (sub_block_header.nondecoder_data == 0)) {
                        WavPackDecoder_read_channel_info(self->bitstream,
                                                         &sub_block_header,
                                                         &(self->channels),
                                                         &(self->channel_mask));
                        /*once we have a channel_info sub-block,
                          there's no need to walk through additional
                          block headers for the channel count*/
                        bs_etry(self->bitstream);
                        goto finished;
                    } else {
                        fseek(self->file,
                              sub_block_header.block_size * 2,
                              SEEK_CUR);
                    }
                    block_length -= sub_block_header.block_size * 2;
                }
                bs_etry(self->bitstream);
            } else {
                /*EOF error*/
                bs_etry(self->bitstream);
                PyErr_SetString(PyExc_IOError, "I/O error reading block");
                return -1;
            }
        }
    } while (block_header.final_block_in_sequence == 0);

 finished:
    iaa_init(&(self->decoded_samples), self->channels, 44100);
    fseek(self->file, 0, SEEK_SET);

    if (self->channel_mask == 0)
        switch (self->channels) {
        case 1:
            self->channel_mask = 0x4;
            break;
        case 2:
            self->channel_mask = 0x3;
            break;
        default:
            /*channel_mask == 0 (undefined)
              if we have multiple channels but no channel_info sub-block*/
            break;
        }

    /*initialize our output MD5 sum*/
    audiotools__MD5Init(&(self->md5));
    self->md5_checked = 0;

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

    self->bitstream->close(self->bitstream);

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
    return Py_BuildValue("i", bs_ftell(self->bitstream));
}

status
WavPackDecoder_read_block_header(Bitstream* bitstream,
                                 struct wavpack_block_header* header) {
    if (!setjmp(*bs_try(bitstream))) {
        /*read and verify block ID*/
        if (bitstream->read(bitstream, 32) != 0x6B707677) {
            bs_etry(bitstream);
            return ERR_INVALID_BLOCK_ID;
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
            bs_etry(bitstream);
            return ERR_INVALID_RESERVED_BIT;
        }

        header->crc = bitstream->read(bitstream, 32);

        bs_etry(bitstream);
        return OK;
    } else {
        bs_etry(bitstream);
        return ERR_BLOCK_HEADER_IO;
    }
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
        return ERR_EXCESSIVE_TERMS;
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
            return ERR_INVALID_TERM;
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

void
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
}

int
wavpack_exp2(int log) {
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
    status result = OK;

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
        result = ERR_DECORR_SAMPLES_IO;
        goto done;
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
                          ia_getdefault(&samples, j + 1, 0));
                ia_append(term_samples_B,
                          ia_getdefault(&samples, j, 0));
                j += 2;
            } else {
                result = ERR_UNSUPPORTED_DECORR_TERM;
                goto done;
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
            } else {
                result = ERR_UNSUPPORTED_DECORR_TERM;
                goto done;
            }
        }
    }

 done:
    ia_free(&samples);
    return result;
}


void
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
}

void
WavPackDecoder_read_int32_info(Bitstream* bitstream,
                               uint8_t* sent_bits, uint8_t* zeroes,
                               uint8_t* ones, uint8_t* dupes) {
    *sent_bits = bitstream->read(bitstream, 8);
    *zeroes = bitstream->read(bitstream, 8);
    *ones = bitstream->read(bitstream, 8);
    *dupes = bitstream->read(bitstream, 8);
}

void
WavPackDecoder_read_channel_info(Bitstream* bitstream,
                                 struct wavpack_subblock_header* header,
                                 int* channel_count,
                                 int* channel_mask) {
    *channel_count = bitstream->read(bitstream, 8);
    *channel_mask = bitstream->read(bitstream,
                                    8 * ((header->block_size * 2) - 1 -
                                         header->actual_size_1_less));
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
        bs_pop_callback(bitstream);
        bs_etry(bitstream);

        return ERR_BITSTREAM_IO;
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

void wavpack_decrement_counter(uint8_t byte, void* counter) {
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
WavPackDecoder_read(decoders_WavPackDecoder* self, PyObject *args) {
    int channels_read;
    int final_block = 0;
    int current_channel = 0;

    struct wavpack_block_header block_header;
    long block_end;
    Bitstream* bitstream = self->bitstream;

    PyObject* framelist;
    status error;

    iaa_reset(&(self->decoded_samples));

    if (self->remaining_samples < 1) {
        /*If we're at the end of the file,
          try to read one additional block to check for
          an MD5 sum.*/

        if (!(self->md5_checked) &&
            (WavPackDecoder_read_block_header(bitstream,
                                              &block_header) == OK)) {
            block_end = ftell(self->file) + block_header.block_size - 24 - 1;
            if (!setjmp(*bs_try(bitstream))) {
                while (ftell(self->file) < block_end) {
                    if ((error = WavPackDecoder_decode_subblock(
                                                self, &block_header)) != OK) {
                        bs_etry(bitstream);
                        PyErr_SetString(PyExc_ValueError,
                                        wavpack_strerror(error));
                        goto error;
                    }
                }
                bs_etry(bitstream);
                return ia_array_to_framelist(&(self->decoded_samples),
                                             self->bits_per_sample);
            } else {
                /*but once we find a block header during closing,
                  trigger an error if that block is truncated*/
                bs_etry(bitstream);
                PyErr_SetString(PyExc_IOError, "I/O error reading sub-block");
                goto error;
            }
        }

        /*there's no error if we can't find a trailing block*/
        return ia_array_to_framelist(&(self->decoded_samples),
                                     self->bits_per_sample);
    }

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

    framelist = ia_array_to_framelist(&(self->decoded_samples),
                                      self->bits_per_sample);

    if (WavPackDecoder_update_md5sum(self, framelist) == OK)
        return framelist;
    else {
        Py_DECREF(framelist);
        goto error;
    }
 error:
    return NULL;
}

status
WavPackDecoder_update_md5sum(decoders_WavPackDecoder *self,
                             PyObject *framelist) {
    PyObject *string = PyObject_CallMethod(framelist,
                                           "to_bytes","ii",
                                           0,
                                           self->bits_per_sample != 8);
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

uint32_t
wavpack_calculate_crc(struct i_array* channel_A,
                      struct i_array* channel_B,
                      int channel_count) {
    struct i_array* channels[] = {channel_A, channel_B};
    ia_size_t total_samples = (channel_count * channel_A->size);
    ia_size_t i;
    ia_data_t sample;
    uint32_t crc = 0xFFFFFFFF;

    for (i = 0; i < total_samples; i++) {
        sample = channels[i % channel_count]->data[i / channel_count];
        crc = ((3 * crc) + sample) & 0xFFFFFFFF;
    }

    return crc;
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
    status error;

    if (self->remaining_samples > 0) {
        position = bs_ftell(self->bitstream);

        self->got_decorr_terms = 0;
        self->got_decorr_weights = 0;
        self->got_decorr_samples = 0;
        self->got_entropy_variables = 0;
        self->got_bitstream = 0;
        self->got_int32_info = 0;

        if ((error = WavPackDecoder_read_block_header(self->bitstream,
                                                      &block_header)) == OK) {
            if (block_header.hybrid_mode) {
                /*FIXME - this should actually be implemented at some point*/
                PyErr_SetString(PyExc_ValueError,
                                "hybrid mode not yet supported");
                return NULL;
            }

            subblocks = PyList_New(0);
            block_end = bs_ftell(self->bitstream) +
                block_header.block_size - 24 - 1;

            if (!setjmp(*bs_try(self->bitstream))) {
                while (bs_ftell(self->bitstream) < block_end) {
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
            PyErr_SetString(PyExc_ValueError, wavpack_strerror(error));
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
    int channel_count;
    int channel_mask;
    status error;

    WavPackDecoder_read_subblock_header(bitstream, &header);

    switch (header.metadata_function | (header.nondecoder_data << 5)) {
    case WV_DECORR_TERMS:
        if ((error = WavPackDecoder_read_decorr_terms(
                                             bitstream,
                                             &header,
                                             &(self->decorr_terms),
                                             &(self->decorr_deltas))) != OK) {
            subblock_data_obj = Py_BuildValue(
                                    "{sN sN}",
                                    "decorr_terms",
                                    i_array_to_list(&(self->decorr_terms)),
                                    "decorr_deltas",
                                    i_array_to_list(&(self->decorr_deltas)));
            self->got_decorr_terms = 1;
        } else {
            PyErr_SetString(PyExc_ValueError, wavpack_strerror(error));
            return NULL;
        }
        break;
    case WV_DECORR_WEIGHTS:
        if (!self->got_decorr_terms) {
            PyErr_SetString(PyExc_ValueError,
                            "decorrelation weights found before terms");
            return NULL;
        }
        WavPackDecoder_read_decorr_weights(
                                   bitstream,
                                   &header,
                                   (block_header->mono_output ||
                                    block_header->false_stereo) ? 1 : 2,
                                   self->decorr_terms.size,
                                   &(self->decorr_weights_A),
                                   &(self->decorr_weights_B));
        subblock_data_obj = Py_BuildValue(
                                "{sN sN}",
                                "decorr_weights_A",
                                i_array_to_list(&(self->decorr_weights_A)),
                                "decorr_weights_B",
                                i_array_to_list(&(self->decorr_weights_B)));
        self->got_decorr_weights = 1;
        break;
    case WV_DECORR_SAMPLES:
        if (!self->got_decorr_terms) {
            PyErr_SetString(PyExc_ValueError,
                            "decorrelation samples found before terms");
            return NULL;
        }
        if ((error = WavPackDecoder_read_decorr_samples(
                                    bitstream,
                                    &header,
                                    (block_header->mono_output ||
                                    block_header->false_stereo) ? 1 : 2,
                                    &(self->decorr_terms),
                                    &(self->decorr_samples_A),
                                    &(self->decorr_samples_B))) == OK) {
            subblock_data_obj = Py_BuildValue(
                                "{sN sN}",
                                "decorr_samples_A",
                                ia_array_to_list(&(self->decorr_samples_A)),
                                "decorr_samples_B",
                                ia_array_to_list(&(self->decorr_samples_B)));
            self->got_decorr_samples = 1;
        } else {
            PyErr_SetString(PyExc_ValueError, wavpack_strerror(error));
            return NULL;
        }
        break;
    case WV_ENTROPY_VARIABLES:
        WavPackDecoder_read_entropy_variables(
                                    bitstream,
                                    (block_header->mono_output ||
                                     block_header->false_stereo) ? 1 : 2,
                                    &(self->entropy_variables_A),
                                    &(self->entropy_variables_B));
        subblock_data_obj = Py_BuildValue(
                                "{sN sN}",
                                "entropy_variables_A",
                                i_array_to_list(&(self->entropy_variables_A)),
                                "entropy_variables_B",
                                i_array_to_list(&(self->entropy_variables_B)));
            self->got_entropy_variables = 1;
        break;
    case WV_INT32_INFO:
        WavPackDecoder_read_int32_info(bitstream,
                                       &(self->int32_info.sent_bits),
                                       &(self->int32_info.zeroes),
                                       &(self->int32_info.ones),
                                       &(self->int32_info.dupes));
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
        break;
    case WV_CHANNEL_INFO:
        WavPackDecoder_read_channel_info(bitstream,
                                         &header,
                                         &channel_count,
                                         &channel_mask);
        subblock_data_obj = Py_BuildValue("{si si}",
                                          "channel_count",
                                          channel_count,
                                          "channel_mask",
                                          channel_mask);
        break;
    case WV_BITSTREAM:
        if (!self->got_entropy_variables) {
            PyErr_SetString(PyExc_ValueError,
                            "bitstream found before entropy variables");
            return NULL;
        }
        if ((error = WavPackDecoder_read_wv_bitstream(
                                    bitstream,
                                    &header,
                                    &(self->entropy_variables_A),
                                    &(self->entropy_variables_B),
                                    (block_header->mono_output ||
                                     block_header->false_stereo) ? 1 : 2,
                                    block_header->block_samples,
                                    &(self->values))) == OK) {
            subblock_data_obj = i_array_to_list(&(self->values));
            self->got_bitstream = 1;
        } else {
            PyErr_SetString(PyExc_IOError, wavpack_strerror(error));
            return NULL;
        }
        break;
    default:
        /*return a binary string for unknown subblock types*/
        data_size = header.block_size * 2;

        subblock_data = malloc(data_size);
        if (fread(subblock_data,
                  sizeof(unsigned char),
                  data_size,
                  bitstream->input.file) != data_size) {
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
    int block_channels = 0;  /*how many channels are actually in the block
                               which depends on the block header's
                               "is_mono" and "false_stereo" flags*/
    long block_end;
    ia_size_t i;
    struct i_array* channels[] = {channel_A, channel_B};
    PyThreadState *thread_state;
    status error;

    self->got_decorr_terms = 0;
    self->got_decorr_weights = 0;
    self->got_decorr_samples = 0;
    self->got_entropy_variables = 0;
    self->got_bitstream = 0;
    self->got_int32_info = 0;

    if (channel_A != NULL) {
        ia_reset(channel_A);
        block_channels++;
    }
    if (channel_B != NULL) {
        ia_reset(channel_B);
        block_channels++;
    }

    thread_state = PyEval_SaveThread();

    if ((error = WavPackDecoder_read_block_header(bitstream,
                                                  &block_header)) != OK) {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_ValueError, wavpack_strerror(error));
        return ERROR;
    }

    if (block_header.hybrid_mode) {
        /*FIXME - this should actually be implemented at some point*/
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_ValueError, "hybrid mode not yet supported");
        return ERROR;
    }

    *channel_count = block_header.mono_output ? 1 : 2;
    *final_block = block_header.final_block_in_sequence;
    if (*channel_count > block_channels) {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_ValueError,
                        "too many channels requested in block header");
        return ERROR;
    } else {
        block_channels = (block_header.mono_output ||
                          block_header.false_stereo) ? 1 : 2;
    }

    /*First, read in all the sub-block data.
      These are like arguments to the decoding routine.*/
    block_end = bs_ftell(bitstream) + block_header.block_size - 24 - 1;
    if (!setjmp(*bs_try(self->bitstream))) {
        while (bs_ftell(self->bitstream) < block_end) {
            if ((error = WavPackDecoder_decode_subblock(
                                               self, &block_header)) != OK) {
                bs_etry(bitstream);
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError, wavpack_strerror(error));
                return ERROR;
            }
        }
        bs_etry(bitstream);
    } else {
        bs_etry(bitstream);
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "I/O error reading sub-block");
        return ERROR;
    }

    if (!self->got_bitstream) {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_ValueError, "residual bitstream not found");
        return ERROR;
    }

    /*Place the bitstream contents in channel_A and channel_B.*/
    for (i = 0; i < self->values.size; i++) {
        ia_append(channels[i % block_channels],
                  self->values.data[i]);
    }

    /*If we have decorrelation passes, run them over
      channel_A and channel_B as many times as necessary.*/
    if (self->got_decorr_terms) {
        /*FIXME - sanity check all decorrelation pass inputs here*/

        for (i = 0; i < self->decorr_terms.size; i++) {
            wavpack_perform_decorrelation_pass(channel_A,
                                               channel_B,
                                               self->decorr_terms.data[i],
                                               self->decorr_deltas.data[i],
                                               self->decorr_weights_A.data[i],
                                               self->decorr_weights_B.data[i],
                                               &(self->decorr_samples_A.arrays[i]),
                                               &(self->decorr_samples_B.arrays[i]),
                                               block_channels);
        }
    }

    /*Undo joint stereo, if necessary.*/
    if (block_header.joint_stereo) {
        wavpack_undo_joint_stereo(channel_A, channel_B);
    }

    /*check CRC of data to return*/
    if (wavpack_calculate_crc(channel_A, channel_B, block_channels) !=
        block_header.crc) {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_ValueError, "CRC mismatch during decode");
        return ERROR;
    }

    /*Handle extended integers, if necessary.*/
    if (block_header.extended_size_integers) {
        wavpack_undo_extended_integers(channel_A, channel_B,
                                       block_channels,
                                       self->int32_info.sent_bits,
                                       self->int32_info.zeroes,
                                       self->int32_info.ones,
                                       self->int32_info.dupes);
    }

    /*Fix false stereo, if present*/
    if (block_header.false_stereo) {
        ia_copy(channel_B, channel_A);
    }

    PyEval_RestoreThread(thread_state);
    return OK;
}

status
WavPackDecoder_decode_subblock(decoders_WavPackDecoder* self,
                               struct wavpack_block_header* block_header) {
    Bitstream* bitstream = self->bitstream;
    struct wavpack_subblock_header header;
    uint8_t file_md5sum[16];
    uint8_t running_md5sum[16];
    status error;

    WavPackDecoder_read_subblock_header(bitstream, &header);
    switch (header.metadata_function | (header.nondecoder_data << 5)) {
    case WV_DECORR_TERMS:
        if ((error = WavPackDecoder_read_decorr_terms(
                                         bitstream,
                                         &header,
                                         &(self->decorr_terms),
                                         &(self->decorr_deltas))) == OK) {
            self->got_decorr_terms = 1;
            break;
        } else
            return error;
    case WV_DECORR_WEIGHTS:
        if (!self->got_decorr_terms)
            return ERR_PREMATURE_DECORR_WEIGHTS;

        WavPackDecoder_read_decorr_weights(
                                   bitstream,
                                   &header,
                                   (block_header->mono_output ||
                                    block_header->false_stereo) ? 1 : 2,
                                   self->decorr_terms.size,
                                   &(self->decorr_weights_A),
                                   &(self->decorr_weights_B));
        self->got_decorr_weights = 1;
        break;
    case WV_DECORR_SAMPLES:
        if (!self->got_decorr_terms)
            return ERR_PREMATURE_DECORR_SAMPLES;

        if ((error = WavPackDecoder_read_decorr_samples(
                                    bitstream,
                                    &header,
                                    (block_header->mono_output ||
                                     block_header->false_stereo) ? 1 : 2,
                                    &(self->decorr_terms),
                                    &(self->decorr_samples_A),
                                    &(self->decorr_samples_B))) == OK) {
            self->got_decorr_samples = 1;
            break;
        } else
            return error;
    case WV_ENTROPY_VARIABLES:
        WavPackDecoder_read_entropy_variables(
                                    bitstream,
                                    (block_header->mono_output ||
                                     block_header->false_stereo) ? 1 : 2,
                                    &(self->entropy_variables_A),
                                    &(self->entropy_variables_B));
        self->got_entropy_variables = 1;
        break;
    case WV_INT32_INFO:
        WavPackDecoder_read_int32_info(bitstream,
                                       &(self->int32_info.sent_bits),
                                       &(self->int32_info.zeroes),
                                       &(self->int32_info.ones),
                                       &(self->int32_info.dupes));
        self->got_int32_info = 1;
        break;
    case WV_BITSTREAM:
        if (!self->got_entropy_variables)
            return ERR_PREMATURE_BITSTREAM;

        if ((error = WavPackDecoder_read_wv_bitstream(
                                    bitstream,
                                    &header,
                                    &(self->entropy_variables_A),
                                    &(self->entropy_variables_B),
                                    (block_header->mono_output ||
                                     block_header->false_stereo) ? 1 : 2,
                                    block_header->block_samples,
                                    &(self->values))) == OK) {
            self->got_bitstream = 1;
            break;
        } else
            return error;
    case WV_MD5:
        if (fread(file_md5sum, 1, 16, bitstream->input.file) == 16) {
            audiotools__MD5Final(running_md5sum, &(self->md5));
            if (memcmp(file_md5sum, running_md5sum, 16) == 0) {
                return OK;
            } else {
                return ERR_MD5_MISMATCH;
            }
        } else {
            return ERR_MD5_IO;
        }
        break;
    default:
        /*unsupported sub-blocks are skipped*/
        fseek(bitstream->input.file, header.block_size * 2, SEEK_CUR);
        break;
    }

    return OK;
}

static inline int
apply_weight(int weight, int64_t sample) {
    return ((weight * sample) + 512) >> 10;
}

static inline int
update_weight(int64_t source, int result, int delta) {
    if ((source == 0) || (result == 0))
        return 0;
    else if ((source ^ result) >= 0)
        return delta;
    else
        return -delta;
}

void wavpack_perform_decorrelation_pass(
                                    struct i_array* channel_A,
                                    struct i_array* channel_B,
                                    int term,
                                    int delta,
                                    int weight_A,
                                    int weight_B,
                                    struct i_array* samples_A,
                                    struct i_array* samples_B,
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
                                               term,
                                               delta,
                                               weight_A,
                                               samples_A);
    } else if (term >= 1) {
        wavpack_perform_decorrelation_pass_1ch(channel_A,
                                               term,
                                               delta,
                                               weight_A,
                                               samples_A);
        wavpack_perform_decorrelation_pass_1ch(channel_B,
                                               term,
                                               delta,
                                               weight_B,
                                               samples_B);
    } else {
        ia_init(&output_A, channel_A->size);
        ia_extend(&output_A, samples_A);

        ia_init(&output_B, channel_B->size);
        ia_extend(&output_B, samples_B);

        switch (term) {
        case -1:
            for (i = 0; i < channel_A->size; i++) {
                input_Ai = channel_A->data[i];
                input_Bi = channel_B->data[i];
                output_A_1 = ia_getitem(&(output_A), -1);
                output_B_1 = ia_getitem(&(output_B), -1);

                /*apply weight*/
                output_Ai = apply_weight(weight_A, output_B_1) +
                    input_Ai;
                ia_append(&output_A, output_Ai);

                /*update weight*/
                weight_A = MAX(MIN(weight_A + update_weight(output_B_1,
                                                            input_Ai,
                                                            delta),
                                   WEIGHT_MAXIMUM), WEIGHT_MINIMUM);

                /*apply weight*/
                ia_append(&output_B,
                          apply_weight(weight_B, output_Ai) +
                          input_Bi);

                /*update weight*/
                weight_B = MAX(MIN(weight_B + update_weight(output_Ai,
                                                            input_Bi,
                                                            delta),
                                   WEIGHT_MAXIMUM), WEIGHT_MINIMUM);
            }
            break;
        case -2:
            for (i = 0; i < channel_B->size; i++) {
                input_Bi = channel_B->data[i];
                input_Ai = channel_A->data[i];
                output_B_1 = ia_getitem(&(output_B), -1);
                output_A_1 = ia_getitem(&(output_A), -1);

                /*apply weight*/
                output_Bi = apply_weight(weight_B, output_A_1) +
                    input_Bi;
                ia_append(&output_B, output_Bi);

                /*update weight*/
                weight_B = MAX(MIN(weight_B + update_weight(output_A_1,
                                                            input_Bi,
                                                            delta),
                                   WEIGHT_MAXIMUM), WEIGHT_MINIMUM);

                /*apply weight*/
                ia_append(&output_A,
                          apply_weight(weight_A, output_Bi) +
                          input_Ai);

                /*update weight*/
                weight_A = MAX(MIN(weight_A + update_weight(output_Bi,
                                                            input_Ai,
                                                            delta),
                                   WEIGHT_MAXIMUM), WEIGHT_MINIMUM);
            }
            break;
        case -3:
            for (i = 0; i < channel_A->size; i++) {
                input_Bi = channel_B->data[i];
                input_Ai = channel_A->data[i];
                output_B_1 = ia_getitem(&(output_B), -1);
                output_A_1 = ia_getitem(&(output_A), -1);

                /*apply weight*/
                output_Ai = apply_weight(weight_A,output_B_1) +
                    input_Ai;
                output_Bi = apply_weight(weight_B, output_A_1) +
                    input_Bi;
                ia_append(&(output_A), output_Ai);
                ia_append(&(output_B), output_Bi);

                /*update weight*/
                weight_A = MAX(MIN(weight_A + update_weight(output_B_1,
                                                            input_Ai,
                                                            delta),
                                   WEIGHT_MAXIMUM), WEIGHT_MINIMUM);
                weight_B = MAX(MIN(weight_B + update_weight(output_A_1,
                                                            input_Bi,
                                                            delta),
                                   WEIGHT_MAXIMUM), WEIGHT_MINIMUM);
            }
        }

        /*clean up temporary buffers*/
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
                                    int term,
                                    int delta,
                                    int weight,
                                    struct i_array* samples) {
    struct i_array output;
    struct i_array output_tail;
    int64_t temp;
    ia_data_t input_i;
    ia_size_t i;

    ia_init(&output, channel->size + samples->size);
    ia_extend(&output, samples);

    switch (term) {
    case 18:
        for (i = 0; i < channel->size; i++) {
            input_i = channel->data[i];
            temp = ((3 * ia_getitem(&output, -1)) -
                    ia_getitem(&output, -2)) >> 1;

            ia_append(&output, apply_weight(weight, temp) + input_i);
            weight += update_weight(temp, input_i, delta);
        }
        break;
    case 17:
        for (i = 0; i < channel->size; i++) {
            input_i = channel->data[i];
            temp = (2 * ia_getitem(&output, -1)) - ia_getitem(&output, -2);

            ia_append(&output, apply_weight(weight, temp) + input_i);
            weight += update_weight(temp, input_i, delta);
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
            temp = ia_getitem(&output, -term);

            ia_append(&output, apply_weight(weight, temp) + input_i);
            weight += update_weight(temp, input_i, delta);
        }
        break;
    }

    ia_tail(&output_tail, &output, channel->size);
    ia_copy(channel, &output_tail);
    ia_free(&output);
}

void wavpack_undo_extended_integers(struct i_array* channel_A,
                                    struct i_array* channel_B,
                                    int channel_count,
                                    uint8_t sent_bits, uint8_t zeroes,
                                    uint8_t ones, uint8_t dupes) {
    ia_size_t i;
    int32_t pad;

    if (zeroes) {
        /*pad the least-significant bits of each sample with 0*/
        for (i = 0; i < channel_A->size; i++) {
            channel_A->data[i] <<= zeroes;
        }
        if (channel_count == 2)
            for (i = 0; i < channel_B->size; i++)
                channel_B->data[i] <<= zeroes;

    } else if (ones) {
        /*pad the least-significant bits of each sample with 1*/
        pad = (1 << ones) - 1;
        for (i = 0; i < channel_A->size; i++)
            channel_A->data[i] = (channel_A->data[i] << ones) | pad;

        if (channel_count == 2)
            for (i = 0; i < channel_B->size; i++)
                channel_B->data[i] = (channel_B->data[i] << ones) | pad;

    } else if (dupes) {
        /*pad the least-significant bits of each sample
          with its own least-significant bit*/
        pad = (1 << dupes) - 1;
        for (i = 0; i < channel_A->size; i++) {
            if (channel_A->data[i] & 1)
                channel_A->data[i] = (channel_A->data[i] << dupes) | dupes;
            else
                channel_A->data[i] <<= dupes;
        }
        if (channel_count == 2)
            for (i = 0; i < channel_B->size; i++) {
                if (channel_B->data[i] & 1)
                    channel_B->data[i] = (channel_B->data[i] << dupes) | dupes;
                else
                    channel_B->data[i] <<= dupes;
            }
    }
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

const char* wavpack_strerror(status error) {
    switch (error) {
    case OK:
        return "No Error";
    case ERROR:
        return "Error";
    case ERR_BITSTREAM_IO:
        return "I/O error reading bitstream";
    case ERR_EXCESSIVE_TERMS:
        return "excessive term count";
    case ERR_INVALID_TERM:
        return "invalid decorrelation term";
    case ERR_DECORR_SAMPLES_IO:
        return "I/O error reading decorrelation samples";
    case ERR_UNSUPPORTED_DECORR_TERM:
        return "unsupported decorrelation term";
    case ERR_PREMATURE_DECORR_WEIGHTS:
        return "decorrelation weights found before terms";
    case ERR_PREMATURE_DECORR_SAMPLES:
        return "decorrelation samples found before terms";
    case ERR_PREMATURE_BITSTREAM:
        return "bitstream found before entropy variables";
    case ERR_MD5_MISMATCH:
        return "MD5 mismatch reading stream";
    case ERR_MD5_IO:
        return "I/O error reading MD5 sub-block data";
    case ERR_INVALID_BLOCK_ID:
        return "invalid block ID";
    case ERR_INVALID_RESERVED_BIT:
        return "invalid reserved bit";
    case ERR_BLOCK_HEADER_IO:
        return "I/O error reading block header";
    default:
        return "Unknown Error";
    }
}

#include "pcm.c"
