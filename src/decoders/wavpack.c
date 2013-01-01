#include "wavpack.h"
#include "../pcmconv.h"
#include <string.h>

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
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    PyObject *args, PyObject *kwds) {
    char* filename;
#else
int
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    char* filename) {
#endif
    struct block_header header;
    status error;

    self->filename = NULL;
    self->bitstream = NULL;
    self->file = NULL;

    audiotools__MD5Init(&(self->md5));
    self->md5sum_checked = 0;

    self->channels_data = array_ia_new();
    self->decorrelation_terms = array_i_new();
    self->decorrelation_deltas = array_i_new();
    self->decorrelation_weights = array_ia_new();
    self->decorrelation_samples = array_iaa_new();
    self->entropies = array_ia_new();
    self->residuals = array_ia_new();
    self->decorrelated = array_ia_new();
    self->correlated = array_ia_new();
    self->left_right = array_ia_new();
    self->un_shifted = array_ia_new();
    self->block_data = br_substream_new(BS_LITTLE_ENDIAN);
    self->sub_block_data = br_substream_new(BS_LITTLE_ENDIAN);

#ifndef STANDALONE
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    /*open the WavPack file*/
    self->file = fopen(filename, "rb");
    if (self->file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = br_open(self->file, BS_LITTLE_ENDIAN);
    }
#else
    if ((self->file = fopen(filename, "rb")) == NULL) {
        return -1;
    } else {
        self->bitstream = br_open(self->file, BS_LITTLE_ENDIAN);
    }
#endif

    self->filename = strdup(filename);

    self->sample_rate = 0;
    self->bits_per_sample = 0;
    self->channels = 0;
    self->channel_mask = 0;
    self->remaining_pcm_samples = 0;

    /*read initial block to populate
      sample_rate, bits_per_sample, channels, and channel_mask*/
    self->bitstream->mark(self->bitstream); /*beginning of stream*/
    if ((error = read_block_header(self->bitstream, &header)) != OK) {
#ifndef STANDALONE
        PyErr_SetString(wavpack_exception(error), wavpack_strerror(error));
#endif
        self->bitstream->unmark(self->bitstream);
        return -1;
    }

    if ((self->sample_rate = unencode_sample_rate(header.sample_rate)) == 0) {
        /*in the event of an odd sample rate,
          look for a sample rate sub block within the first block*/
        self->bitstream->mark(self->bitstream); /*after block header*/
        switch (error =
                read_sample_rate_sub_block(&header,
                                           self->bitstream,
                                           &(self->sample_rate))) {
        case OK:
            self->bitstream->rewind(self->bitstream);
            self->bitstream->unmark(self->bitstream); /*after block header*/
            break;
        case SUB_BLOCK_NOT_FOUND:
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "sample rate undefined");
#endif
            self->bitstream->unmark(self->bitstream); /*after block header*/
            self->bitstream->unmark(self->bitstream); /*beginning of stream*/
            return -1;
        default:
#ifndef STANDALONE
            PyErr_SetString(wavpack_exception(error), wavpack_strerror(error));
#endif
            self->bitstream->unmark(self->bitstream); /*after block header*/
            self->bitstream->unmark(self->bitstream); /*beginning of stream*/
            return -1;
        }
    }

    self->bits_per_sample = unencode_bits_per_sample(header.bits_per_sample);
    if (header.final_block) {
        if ((header.mono_output == 0) || (header.false_stereo == 1)) {
            self->channels = 2;
            self->channel_mask = 0x3;
        } else {
            self->channels = 1;
            self->channel_mask = 0x4;
        }
    } else {
        /*in the event of a stream with more than 2 channels,
          look for a channel count/channel mask sub block
          within the first block*/
        self->bitstream->mark(self->bitstream);
        switch (error =
                read_channel_count_sub_block(&header,
                                             self->bitstream,
                                             &(self->channels),
                                             &(self->channel_mask))) {
        case OK:
            self->bitstream->rewind(self->bitstream);
            self->bitstream->unmark(self->bitstream); /*after block header*/
            break;
        case SUB_BLOCK_NOT_FOUND:
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "channel count/mask undefined");
#endif
            self->bitstream->unmark(self->bitstream); /*after block header*/
            self->bitstream->unmark(self->bitstream); /*beginning of stream*/
            return -1;
        default:
#ifndef STANDALONE
            PyErr_SetString(wavpack_exception(error), wavpack_strerror(error));
#endif
            self->bitstream->unmark(self->bitstream); /*after block header*/
            self->bitstream->unmark(self->bitstream); /*beginning of stream*/
            return -1;
        }
    }

    self->remaining_pcm_samples = header.total_samples;

    self->bitstream->rewind(self->bitstream);
    self->bitstream->unmark(self->bitstream); /*beginning of stream*/

    /*mark stream as not closed and ready for reading*/
    self->closed = 0;

    return 0;
}

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self) {
    self->channels_data->del(self->channels_data);
    self->decorrelation_terms->del(self->decorrelation_terms);
    self->decorrelation_deltas->del(self->decorrelation_deltas);
    self->decorrelation_weights->del(self->decorrelation_weights);
    self->decorrelation_samples->del(self->decorrelation_samples);
    self->entropies->del(self->entropies);
    self->residuals->del(self->residuals);
    self->decorrelated->del(self->decorrelated);
    self->correlated->del(self->correlated);
    self->left_right->del(self->left_right);
    self->un_shifted->del(self->un_shifted);
    self->block_data->close(self->block_data);
    self->sub_block_data->close(self->sub_block_data);

#ifndef STANDALONE
    Py_XDECREF(self->audiotools_pcm);
#endif

    if (self->filename != NULL)
        free(self->filename);

    if (self->bitstream != NULL)
        self->bitstream->close(self->bitstream);

#ifndef STANDALONE
    self->ob_type->tp_free((PyObject*)self);
#endif
}

#ifndef STANDALONE
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
    /*mark stream as closed so more calls to read() generate ValueErrors*/
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject*
WavPackDecoder_read(decoders_WavPackDecoder* self, PyObject *args) {
    BitstreamReader* bs = self->bitstream;
    array_ia* channels_data = self->channels_data;
    status error;
    struct block_header block_header;
    BitstreamReader* block_data = self->block_data;
    PyThreadState *thread_state;
    PyObject* framelist;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    channels_data->reset(channels_data);

    if (self->remaining_pcm_samples > 0) {
        do {
            /*read block header*/
            if ((error = read_block_header(bs, &block_header)) != OK) {
                PyErr_SetString(wavpack_exception(error),
                                wavpack_strerror(error));
                return NULL;
            }

            /*FIXME - ensure block header is consistent
              with the starting block header*/

            br_substream_reset(block_data);

            /*read block data*/
            if (!setjmp(*br_try(bs))) {
                bs->substream_append(bs, block_data,
                                     block_header.block_size - 24);
                br_etry(bs);
            } else {
                br_etry(bs);
                PyErr_SetString(PyExc_IOError, "I/O error reading block data");
                return NULL;
            }

            /*decode block to 1 or 2 channels of PCM data*/
            thread_state = PyEval_SaveThread();
            if ((error = decode_block(self,
                                      &block_header,
                                      block_data,
                                      block_header.block_size - 24,
                                      channels_data)) != OK) {
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(wavpack_exception(error),
                                wavpack_strerror(error));
                return NULL;
            } else {
                PyEval_RestoreThread(thread_state);
            }
        } while (block_header.final_block == 0);

        /*deduct frame count from total remaining*/
        self->remaining_pcm_samples -= MIN(channels_data->_[0]->len,
                                           self->remaining_pcm_samples);

        /*convert all channels to single PCM framelist*/
        framelist = array_ia_to_FrameList(self->audiotools_pcm,
                                          channels_data,
                                          self->bits_per_sample);

        /*update stream's MD5 sum with framelist data*/
        if (!WavPackDecoder_update_md5sum(self, framelist)) {
            return framelist;
        } else {
            return NULL;
        }
    } else {
        if (!self->md5sum_checked) {
            struct sub_block md5_sub_block;
            unsigned char sub_block_md5sum[16];
            unsigned char stream_md5sum[16];

            md5_sub_block.data = self->sub_block_data;

            /*check for final MD5 block, which may not be present*/
            if ((read_block_header(bs, &block_header) == OK) &&
                (find_sub_block(&block_header,
                                bs,
                                6, 1, &md5_sub_block) == OK) &&
                (sub_block_data_size(&md5_sub_block) == 16)) {
                /*have valid MD5 block, so check it*/
                md5_sub_block.data->read_bytes(md5_sub_block.data,
                                               (uint8_t*)sub_block_md5sum,
                                               16);
                audiotools__MD5Final(stream_md5sum, &(self->md5));
                self->md5sum_checked = 1;

                if (memcmp(sub_block_md5sum, stream_md5sum, 16)) {
                    PyErr_SetString(PyExc_ValueError,
                                    "MD5 mismatch at end of stream");
                    return NULL;
                }
            }
        }

        return empty_FrameList(self->audiotools_pcm,
                               (unsigned int)self->channels,
                               (unsigned int)self->bits_per_sample);
    }
}

PyObject*
wavpack_exception(status error)
{
    switch (error) {
    case IO_ERROR:
        return PyExc_IOError;
    case OK:
    case INVALID_BLOCK_ID:
    case INVALID_RESERVED_BIT:
    case EXCESSIVE_DECORRELATION_PASSES:
    case INVALID_DECORRELATION_TERM:
    case DECORRELATION_TERMS_MISSING:
    case DECORRELATION_WEIGHTS_MISSING:
    case DECORRELATION_SAMPLES_MISSING:
    case ENTROPY_VARIABLES_MISSING:
    case RESIDUALS_MISSING:
    case EXCESSIVE_DECORRELATION_WEIGHTS:
    case INVALID_ENTROPY_VARIABLE_COUNT:
    case BLOCK_DATA_CRC_MISMATCH:
    case EXTENDED_INTEGERS_MISSING:
    default:
        return PyExc_ValueError;
    }
}

int
WavPackDecoder_update_md5sum(decoders_WavPackDecoder *self,
                             PyObject *framelist)
{
    PyObject *string_obj;
    char *string_buffer;
    Py_ssize_t length;
    int sign = self->bits_per_sample >= 16;

    if ((string_obj =
         PyObject_CallMethod(framelist, "to_bytes","ii", 0, sign)) != NULL) {
        if (PyString_AsStringAndSize(string_obj,
                                     &string_buffer,
                                     &length) == 0) {
            audiotools__MD5Update(&(self->md5),
                                  (unsigned char *)string_buffer,
                                  length);
            Py_DECREF(string_obj);
            return 0;
        } else {
            Py_DECREF(string_obj);
            return 1;
        }
    } else {
        return 1;
    }
}
#endif

const char*
wavpack_strerror(status error)
{
    switch (error) {
    case OK:
        return "no error";
    case IO_ERROR:
        return "I/O error";
    case INVALID_BLOCK_ID:
        return "invalid block header ID";
    case INVALID_RESERVED_BIT:
        return "invalid reserved bit";
    case EXCESSIVE_DECORRELATION_PASSES:
        return "excessive decorrelation passes";
    case INVALID_DECORRELATION_TERM:
        return "invalid decorrelation term";
    case DECORRELATION_TERMS_MISSING:
        return "missing decorrelation terms sub block";
    case DECORRELATION_WEIGHTS_MISSING:
        return "missing decorrelation weights sub block";
    case DECORRELATION_SAMPLES_MISSING:
        return "missing decorrelation samples sub block";
    case ENTROPY_VARIABLES_MISSING:
        return "missing entropy variables sub block";
    case RESIDUALS_MISSING:
        return "missing bitstream sub block";
    case EXTENDED_INTEGERS_MISSING:
        return "missing extended integers sub block";
    case EXCESSIVE_DECORRELATION_WEIGHTS:
        return "excessive decorrelation weight values";
    case INVALID_ENTROPY_VARIABLE_COUNT:
        return "invalid entropy variable count";
    case BLOCK_DATA_CRC_MISMATCH:
        return "block data CRC mismatch";
    default:
        return "unspecified error";
    }
}

static status
read_block_header(BitstreamReader* bs, struct block_header* header)
{
    unsigned char block_id[4];
    unsigned reserved;

    if (!setjmp(*br_try(bs))) {
        bs->parse(bs,
                  "4b 32u 16u 8u 8u 32u 32u 32u"
                  "2u 1u 1u 1u 1u 1u 1u 1u "
                  "1u 1u 1u 1u 5u 5u 4u 2p 1u 1u 1u"
                  "32u",
                  block_id,
                  &(header->block_size),
                  &(header->version),
                  &(header->track_number),
                  &(header->index_number),
                  &(header->total_samples),
                  &(header->block_index),
                  &(header->block_samples),
                  &(header->bits_per_sample),
                  &(header->mono_output),
                  &(header->hybrid_mode),
                  &(header->joint_stereo),
                  &(header->cross_channel_decorrelation),
                  &(header->hybrid_noise_shaping),
                  &(header->floating_point_data),
                  &(header->extended_size_integers),
                  &(header->hybrid_parameters_control_bitrate),
                  &(header->hybrid_noise_balanced),
                  &(header->initial_block),
                  &(header->final_block),
                  &(header->left_shift),
                  &(header->maximum_data_magnitude),
                  &(header->sample_rate),
                  &(header->use_IIR),
                  &(header->false_stereo),
                  &reserved,
                  &(header->CRC));
        br_etry(bs);
        if (memcmp(block_id, "wvpk", 4))
            return INVALID_BLOCK_ID;
        else if (reserved)
            return INVALID_RESERVED_BIT;
        else
            return OK;
    } else {
        br_etry(bs);
        return IO_ERROR;
    }
}

static status
decode_block(decoders_WavPackDecoder* decoder,
             const struct block_header* block_header,
             BitstreamReader* block_data,
             unsigned block_data_size,
             array_ia* channels)
{
    struct sub_block sub_block;
    int sub_block_size;
    status status = OK;

    int decorrelation_terms_read = 0;
    int decorrelation_weights_read = 0;
    int decorrelation_samples_read = 0;
    int entropy_variables_read = 0;
    int extended_integers_read = 0;
    int bitstream_read = 0;

    struct extended_integers extended_integers;

    array_i* decorrelation_terms = decoder->decorrelation_terms;
    array_i* decorrelation_deltas = decoder->decorrelation_deltas;
    array_ia* decorrelation_weights = decoder->decorrelation_weights;
    array_iaa* decorrelation_samples = decoder->decorrelation_samples;
    array_ia* entropies = decoder->entropies;
    array_ia* residuals = decoder->residuals;

    sub_block.data = decoder->sub_block_data;

    /*parse all decoding parameter sub blocks*/
    while (block_data_size > 0) {
        if ((sub_block_size = read_sub_block(block_data,
                                             &sub_block)) == -1) {
            return IO_ERROR;
        } else {
            block_data_size -= sub_block_size;
        }

        if (!sub_block.nondecoder_data) {
            switch (sub_block.metadata_function) {
            case 2:
                if ((status = read_decorrelation_terms(
                         &sub_block,
                         decorrelation_terms,
                         decorrelation_deltas)) != OK) {
                    return status;
                }
                decorrelation_terms_read = 1;
                break;
            case 3:
                if (!decorrelation_terms_read) {
                    return DECORRELATION_TERMS_MISSING;
                }
                if ((status = read_decorrelation_weights(
                         block_header,
                         &sub_block,
                         decorrelation_terms->len,
                         decorrelation_weights)) != OK) {
                    return status;
                }
                decorrelation_weights_read = 1;
                break;
            case 4:
                if (!decorrelation_terms_read) {
                    return DECORRELATION_TERMS_MISSING;
                }
                if ((status = read_decorrelation_samples(
                         block_header,
                         &sub_block,
                         decorrelation_terms,
                         decorrelation_samples)) != OK) {
                    return status;
                }
                decorrelation_samples_read = 1;
                break;
            case 5:
                if ((status = read_entropy_variables(
                         block_header,
                         &sub_block,
                         entropies)) != OK) {
                    return status;
                }
                entropy_variables_read = 1;
                break;
            case 9:
                if ((status = read_extended_integers(
                         &sub_block,
                         &extended_integers)) != OK) {
                    return status;
                }
                extended_integers_read = 1;
                break;
            case 10:
                if (!entropy_variables_read) {
                    return ENTROPY_VARIABLES_MISSING;
                }
                if ((status = read_bitstream(block_header,
                                             sub_block.data,
                                             entropies,
                                             residuals)) != OK) {
                    return status;
                }
                bitstream_read = 1;
                break;
            }
        }
    }

    /*ensure the required decoding parameters have been read*/
    if (decorrelation_terms_read) {
        if (!decorrelation_weights_read)
            return DECORRELATION_WEIGHTS_MISSING;
        if (!decorrelation_samples_read)
            return DECORRELATION_SAMPLES_MISSING;
    }
    if (!bitstream_read)
        return RESIDUALS_MISSING;

    if ((block_header->mono_output == 0) &&
        (block_header->false_stereo == 0)) {
        array_ia* decorrelated = decoder->decorrelated;
        array_ia* left_right = decoder->left_right;
        array_ia* un_shifted = decoder->un_shifted;

        /*perform decorrelation passes over residual data*/
        if (decorrelation_terms_read &&
            (decorrelation_terms->len > 0)) {
            decorrelate_channels(decorrelation_terms,
                                 decorrelation_deltas,
                                 decorrelation_weights,
                                 decorrelation_samples,
                                 residuals,
                                 decorrelated,
                                 decoder->correlated);
        } else {
            residuals->swap(residuals, decorrelated);
        }

        /*undo joint stereo*/
        if (block_header->joint_stereo) {
            undo_joint_stereo(decorrelated, left_right);
        } else {
            decorrelated->swap(decorrelated, left_right);
        }

        /*verify PCM data against block header's CRC*/
        if (calculate_crc(left_right) != block_header->CRC) {
            return BLOCK_DATA_CRC_MISMATCH;
        }

        /*undo extended integers*/
        if (block_header->extended_size_integers) {
            if (extended_integers_read) {
                undo_extended_integers(&extended_integers,
                                       left_right,
                                       un_shifted);
            } else {
                return EXTENDED_INTEGERS_MISSING;
            }
        } else {
            left_right->swap(left_right, un_shifted);
        }

        channels->extend(channels, un_shifted);
    } else {
        array_ia* decorrelated = decoder->decorrelated;
        array_ia* un_shifted = decoder->un_shifted;

        /*perform decorrelation passes over residual data*/
        if (decorrelation_terms_read &&
            (decorrelation_terms->len > 0)) {
            decorrelate_channels(decorrelation_terms,
                                 decorrelation_deltas,
                                 decorrelation_weights,
                                 decorrelation_samples,
                                 residuals,
                                 decorrelated,
                                 decoder->correlated);
        } else {
            residuals->swap(residuals, decorrelated);
        }

        /*verify PCM data against block header's CRC*/
        if (calculate_crc(decorrelated) != block_header->CRC) {
            return BLOCK_DATA_CRC_MISMATCH;
        }

        /*undo extended integers*/
        if (block_header->extended_size_integers) {
            if (extended_integers_read) {
                undo_extended_integers(&extended_integers,
                                       decorrelated,
                                       un_shifted);
            } else {
                return EXTENDED_INTEGERS_MISSING;
            }
        } else {
            decorrelated->swap(decorrelated, un_shifted);
        }

        /*undo false stereo*/
        if (block_header->false_stereo) {
            un_shifted->_[0]->copy(un_shifted->_[0],
                                   channels->append(channels));
            un_shifted->_[0]->copy(un_shifted->_[0],
                                   channels->append(channels));
        } else {
            channels->extend(channels, un_shifted);
        }
    }

    return OK;
}

static status
read_decorrelation_terms(const struct sub_block* sub_block,
                         array_i* terms,
                         array_i* deltas)
{
    BitstreamReader* sub_block_data = sub_block->data;
    unsigned passes;
    unsigned i;

    if (sub_block->actual_size_1_less == 0) {
        passes = sub_block->size * 2;
    } else {
        passes = sub_block->size * 2 - 1;
    }

    if (passes > 16)
        return EXCESSIVE_DECORRELATION_PASSES;

    terms->reset(terms);
    deltas->reset(deltas);

    for (i = 0; i < passes; i++) {
        terms->append(terms,
                      (int)(sub_block_data->read(sub_block_data, 5)) - 5);
        if (!(((-3 <= terms->_[i]) && (terms->_[i] <= -1)) ||
              ( (1 <= terms->_[i]) && (terms->_[i] <=  8)) ||
              ((17 <= terms->_[i]) && (terms->_[i] <= 18))))
            return INVALID_DECORRELATION_TERM;
        deltas->append(deltas, sub_block_data->read(sub_block_data, 3));
    }

    terms->reverse(terms);
    deltas->reverse(deltas);
    return OK;
}

static inline int
pop_decorrelation_weight(BitstreamReader *sub_block)
{
    const int value = sub_block->read_signed(sub_block, 8);
    if (value > 0) {
        return (value << 3) + (((value << 3) + (1 << 6)) >> 7);
    } else if (value == 0) {
        return 0;
    } else {
        return (value << 3);
    }
}

static status
read_decorrelation_weights(const struct block_header* block_header,
                           const struct sub_block* sub_block,
                           unsigned term_count,
                           array_ia* weights)
{
    unsigned i;
    unsigned weight_count;

    if (sub_block->actual_size_1_less == 0) {
        weight_count = sub_block->size * 2;
    } else {
        weight_count = sub_block->size * 2 - 1;
    }

    weights->reset(weights);

    if ((block_header->mono_output == 0) && (block_header->false_stereo == 0)) {
        /*two channels*/
        if ((weight_count / 2) > term_count) {
            return EXCESSIVE_DECORRELATION_WEIGHTS;
        }
        for (i = 0; i < weight_count / 2; i++) {
            array_i* weights_pass = weights->append(weights);
            weights_pass->append(weights_pass,
                                 pop_decorrelation_weight(sub_block->data));
            weights_pass->append(weights_pass,
                                 pop_decorrelation_weight(sub_block->data));
        }
        for (; i < term_count; i++) {
            array_i* weights_pass = weights->append(weights);
            weights_pass->mappend(weights_pass, 2, 0);
        }

        weights->reverse(weights);
        return OK;
    } else {
        /*one channel*/
        if (weight_count > term_count) {
            return EXCESSIVE_DECORRELATION_WEIGHTS;
        }

        for (i = 0; i < weight_count; i++) {
            array_i* weights_pass = weights->append(weights);
            weights_pass->append(weights_pass,
                                 pop_decorrelation_weight(sub_block->data));
        }
        for (; i < term_count; i++) {
            array_i* weights_pass = weights->append(weights);
            weights_pass->append(weights_pass, 0);
        }

        weights->reverse(weights);
        return OK;
    }
}

static status
read_decorrelation_samples(const struct block_header* block_header,
                           const struct sub_block* sub_block,
                           const array_i* terms,
                           array_iaa* samples)
{
    unsigned bytes_remaining;
    int p;
    int s;

    if (sub_block->actual_size_1_less) {
        bytes_remaining = sub_block->size * 2 - 1;
    } else {
        bytes_remaining = sub_block->size * 2;
    }

    samples->reset(samples);

    if ((block_header->mono_output == 0) && (block_header->false_stereo == 0)) {
        /*two channels*/
        for (p = terms->len - 1; p >= 0; p--) {
            array_ia* samples_p = samples->append(samples);

            /*samples for pass "p", channel "0"*/
            array_i* samples_p_0_s = samples_p->append(samples_p);
            /*samples for pass "p", channel "1"*/
            array_i* samples_p_1_s = samples_p->append(samples_p);

            if ((17 <= terms->_[p]) && (terms->_[p] <= 18)) {
                if (bytes_remaining >= 8) {
                    samples_p_0_s->append(samples_p_0_s,
                                          read_wv_exp2(sub_block->data));
                    samples_p_0_s->append(samples_p_0_s,
                                          read_wv_exp2(sub_block->data));

                    samples_p_1_s->append(samples_p_1_s,
                                          read_wv_exp2(sub_block->data));
                    samples_p_1_s->append(samples_p_1_s,
                                          read_wv_exp2(sub_block->data));
                    bytes_remaining -= 8;
                } else {
                    samples_p_0_s->mappend(samples_p_0_s, 2, 0);
                    samples_p_1_s->mappend(samples_p_1_s, 2, 0);
                    bytes_remaining = 0;
                }
            } else if ((1 <= terms->_[p]) && (terms->_[p] <= 8)) {
                if (bytes_remaining >= (terms->_[p] * 4)) {
                    for (s = 0; s < terms->_[p]; s++) {
                        samples_p_0_s->append(samples_p_0_s,
                                              read_wv_exp2(sub_block->data));

                        samples_p_1_s->append(samples_p_1_s,
                                              read_wv_exp2(sub_block->data));
                        bytes_remaining -= 4;
                    }
                } else {
                    for (s = 0; s < terms->_[p]; s++) {
                        samples_p_0_s->append(samples_p_0_s, 0);

                        samples_p_1_s->append(samples_p_1_s, 0);
                    }
                    bytes_remaining = 0;
                }
            } else if ((-3 <= terms->_[p]) && (terms->_[p] <= -1)) {
                if (bytes_remaining >= 4) {
                    samples_p_0_s->append(samples_p_0_s,
                                          read_wv_exp2(sub_block->data));

                    samples_p_1_s->append(samples_p_1_s,
                                          read_wv_exp2(sub_block->data));
                    bytes_remaining -= 4;
                } else {
                    samples_p_0_s->append(samples_p_0_s, 0);
                    samples_p_1_s->append(samples_p_1_s, 0);
                    bytes_remaining = 0;
                }
            } else {
                return INVALID_DECORRELATION_TERM;
            }
        }

        samples->reverse(samples);
    } else {
        /*one channel*/

        for (p = terms->len - 1; p >= 0 ; p--) {
            array_ia* samples_p = samples->append(samples);

            array_i* samples_p_0_s = samples_p->append(samples_p);

            if ((17 <= terms->_[p]) && (terms->_[p] <= 18)) {
                if (bytes_remaining >= 4) {
                    samples_p_0_s->append(samples_p_0_s,
                                          read_wv_exp2(sub_block->data));
                    samples_p_0_s->append(samples_p_0_s,
                                          read_wv_exp2(sub_block->data));
                    bytes_remaining -= 4;
                } else {
                    samples_p_0_s->mappend(samples_p_0_s, 2, 0);
                    bytes_remaining = 0;
                }
            } else if ((1 <= terms->_[p]) && (terms->_[p] <= 8)) {
                if (bytes_remaining >= (terms->_[p] * 2)) {
                    for (s = 0; s < terms->_[p]; s++) {
                        samples_p_0_s->append(samples_p_0_s,
                                              read_wv_exp2(sub_block->data));
                        bytes_remaining -= 2;
                    }
                } else {
                    for (s = 0; s < terms->_[p]; s++) {
                        samples_p_0_s->append(samples_p_0_s, 0);
                    }
                    bytes_remaining = 0;
                }
            } else {
                return INVALID_DECORRELATION_TERM;
            }
        }

        samples->reverse(samples);
    }

    return OK;
}

static status
read_entropy_variables(const struct block_header* block_header,
                       const struct sub_block* sub_block,
                       array_ia* entropies)
{
    array_i* entropies_0;
    array_i* entropies_1;

    if (sub_block->actual_size_1_less)
        return INVALID_ENTROPY_VARIABLE_COUNT;

    entropies->reset(entropies);
    entropies_0 = entropies->append(entropies);
    entropies_1 = entropies->append(entropies);

    if ((block_header->mono_output == 0) && (block_header->false_stereo == 0)) {
        if (sub_block->size != 6)
            return INVALID_ENTROPY_VARIABLE_COUNT;

        entropies_0->append(entropies_0, read_wv_exp2(sub_block->data));
        entropies_0->append(entropies_0, read_wv_exp2(sub_block->data));
        entropies_0->append(entropies_0, read_wv_exp2(sub_block->data));
        entropies_1->append(entropies_1, read_wv_exp2(sub_block->data));
        entropies_1->append(entropies_1, read_wv_exp2(sub_block->data));
        entropies_1->append(entropies_1, read_wv_exp2(sub_block->data));
    } else {
        if (sub_block->size != 3)
            return INVALID_ENTROPY_VARIABLE_COUNT;

        entropies_0->append(entropies_0, read_wv_exp2(sub_block->data));
        entropies_0->append(entropies_0, read_wv_exp2(sub_block->data));
        entropies_0->append(entropies_0, read_wv_exp2(sub_block->data));
        entropies_1->mappend(entropies_1, 3, 0);
    }

    return OK;
}

static int
read_wv_exp2(BitstreamReader* sub_block_data)
{
    const static int EXP2[] =
        {0x100, 0x101, 0x101, 0x102, 0x103, 0x103, 0x104, 0x105,
         0x106, 0x106, 0x107, 0x108, 0x108, 0x109, 0x10a, 0x10b,
         0x10b, 0x10c, 0x10d, 0x10e, 0x10e, 0x10f, 0x110, 0x110,
         0x111, 0x112, 0x113, 0x113, 0x114, 0x115, 0x116, 0x116,
         0x117, 0x118, 0x119, 0x119, 0x11a, 0x11b, 0x11c, 0x11d,
         0x11d, 0x11e, 0x11f, 0x120, 0x120, 0x121, 0x122, 0x123,
         0x124, 0x124, 0x125, 0x126, 0x127, 0x128, 0x128, 0x129,
         0x12a, 0x12b, 0x12c, 0x12c, 0x12d, 0x12e, 0x12f, 0x130,
         0x130, 0x131, 0x132, 0x133, 0x134, 0x135, 0x135, 0x136,
         0x137, 0x138, 0x139, 0x13a, 0x13a, 0x13b, 0x13c, 0x13d,
         0x13e, 0x13f, 0x140, 0x141, 0x141, 0x142, 0x143, 0x144,
         0x145, 0x146, 0x147, 0x148, 0x148, 0x149, 0x14a, 0x14b,
         0x14c, 0x14d, 0x14e, 0x14f, 0x150, 0x151, 0x151, 0x152,
         0x153, 0x154, 0x155, 0x156, 0x157, 0x158, 0x159, 0x15a,
         0x15b, 0x15c, 0x15d, 0x15e, 0x15e, 0x15f, 0x160, 0x161,
         0x162, 0x163, 0x164, 0x165, 0x166, 0x167, 0x168, 0x169,
         0x16a, 0x16b, 0x16c, 0x16d, 0x16e, 0x16f, 0x170, 0x171,
         0x172, 0x173, 0x174, 0x175, 0x176, 0x177, 0x178, 0x179,
         0x17a, 0x17b, 0x17c, 0x17d, 0x17e, 0x17f, 0x180, 0x181,
         0x182, 0x183, 0x184, 0x185, 0x187, 0x188, 0x189, 0x18a,
         0x18b, 0x18c, 0x18d, 0x18e, 0x18f, 0x190, 0x191, 0x192,
         0x193, 0x195, 0x196, 0x197, 0x198, 0x199, 0x19a, 0x19b,
         0x19c, 0x19d, 0x19f, 0x1a0, 0x1a1, 0x1a2, 0x1a3, 0x1a4,
         0x1a5, 0x1a6, 0x1a8, 0x1a9, 0x1aa, 0x1ab, 0x1ac, 0x1ad,
         0x1af, 0x1b0, 0x1b1, 0x1b2, 0x1b3, 0x1b4, 0x1b6, 0x1b7,
         0x1b8, 0x1b9, 0x1ba, 0x1bc, 0x1bd, 0x1be, 0x1bf, 0x1c0,
         0x1c2, 0x1c3, 0x1c4, 0x1c5, 0x1c6, 0x1c8, 0x1c9, 0x1ca,
         0x1cb, 0x1cd, 0x1ce, 0x1cf, 0x1d0, 0x1d2, 0x1d3, 0x1d4,
         0x1d6, 0x1d7, 0x1d8, 0x1d9, 0x1db, 0x1dc, 0x1dd, 0x1de,
         0x1e0, 0x1e1, 0x1e2, 0x1e4, 0x1e5, 0x1e6, 0x1e8, 0x1e9,
         0x1ea, 0x1ec, 0x1ed, 0x1ee, 0x1f0, 0x1f1, 0x1f2, 0x1f4,
         0x1f5, 0x1f6, 0x1f8, 0x1f9, 0x1fa, 0x1fc, 0x1fd, 0x1ff};
    int value = sub_block_data->read_signed(sub_block_data, 16);

    if ((-32768 <= value) && (value < -2304)) {
        return -(EXP2[-value & 0xFF] << ((-value >> 8) - 9));
    } else if ((-2304 <= value) && (value < 0)) {
        return -(EXP2[-value & 0xFF] >> (9 - (-value >> 8)));
    } else if ((0 <= value) && (value <= 2304)) {
        return EXP2[value & 0xFF] >> (9 - (value >> 8));
    } else if ((2304 < value) && (value <= 32767)) {
        return EXP2[value & 0xFF] << ((value >> 8) - 9);
    } else {
        /*shouldn't get here from a 16-bit value*/
        abort();
        return 0;
    }
}

#define UNDEFINED -1

static status
read_bitstream(const struct block_header* block_header,
               BitstreamReader* sub_block_data,
               array_ia* entropies,
               array_ia* residuals)
{
    unsigned channel_count;
    int u = UNDEFINED;
    unsigned i = 0;
    unsigned j;

    residuals->reset(residuals);

    if ((block_header->mono_output == 0) && (block_header->false_stereo == 0)) {
        channel_count = 2;
        residuals->append(residuals);
        residuals->append(residuals);
    } else {
        channel_count = 1;
        residuals->append(residuals);
    }

    if (!setjmp(*br_try(sub_block_data))) {
        const unsigned total_samples =
            channel_count * block_header->block_samples;

        while (i < total_samples) {
            if ((u == UNDEFINED) &&
                (entropies->_[0]->_[0] < 2) &&
                (entropies->_[1]->_[0] < 2)) {
                unsigned zeroes = read_egc(sub_block_data);

                if (zeroes > 0) {
                    /*ensure i doesn't exceed total samples*/
                    zeroes = MIN(zeroes, total_samples - i);

                    for (j = 0; j < zeroes; j++) {
                        array_i* channel = residuals->_[i % channel_count];
                        channel->append(channel, 0);
                        i++;
                    }
                    entropies->_[0]->_[0] = 0;
                    entropies->_[0]->_[1] = 0;
                    entropies->_[0]->_[2] = 0;
                    entropies->_[1]->_[0] = 0;
                    entropies->_[1]->_[1] = 0;
                    entropies->_[1]->_[2] = 0;
                }

                if (i < total_samples) {
                    const int residual =
                        read_residual(sub_block_data,
                                      &u,
                                      entropies->_[i % channel_count]);
                    array_i* channel = residuals->_[i % channel_count];
                    channel->append(channel, residual);
                    i++;
                }
            } else {
                const int residual =
                    read_residual(sub_block_data,
                                  &u,
                                  entropies->_[i % channel_count]);
                array_i* channel = residuals->_[i % channel_count];
                channel->append(channel, residual);
                i++;
            }
        }

        br_etry(sub_block_data);
        return OK;
    } else {
        br_etry(sub_block_data);
        return IO_ERROR;
    }
}

static unsigned
read_egc(BitstreamReader* bs)
{
    unsigned t = bs->read_unary(bs, 0);
    if (t > 1) {
        unsigned p = bs->read(bs, t - 1);
        return (1 << (t - 1)) + p;
    } else {
        return t;
    }
}

static inline unsigned
LOG2(unsigned value)
{
    unsigned bits = 0;
    assert(value > 0);
    while (value) {
        bits++;
        value >>= 1;
    }
    return bits - 1;
}

static int
read_residual(BitstreamReader* bs,
              int* last_u,
              array_i* entropies)
{
    unsigned u;
    unsigned m;
    int base;
    int add;

    if (*last_u == UNDEFINED) {
        u = bs->read_unary(bs, 0);
        if (u == 16)
            u += read_egc(bs);
        *last_u = (int)u;
        m = u / 2;
    } else if (*last_u % 2) {
        u = bs->read_unary(bs, 0);
        if (u == 16)
            u += read_egc(bs);
        *last_u = (int)u;
        m = (u / 2) + 1;
    } else {
        *last_u = UNDEFINED;
        m = 0;
    }

    switch (m) {
    case 0:
        base = 0;
        add = entropies->_[0] >> 4;
        entropies->_[0] -= ((entropies->_[0] + 126) >> 7) * 2;
        break;
    case 1:
        base = (entropies->_[0] >> 4) + 1;
        add = entropies->_[1] >> 4;
        entropies->_[0] += ((entropies->_[0] + 128) >> 7) * 5;
        entropies->_[1] -= ((entropies->_[1] + 62) >> 6) * 2;
        break;
    case 2:
        base = ((entropies->_[0] >> 4) + 1) + ((entropies->_[1] >> 4) + 1);
        add = entropies->_[2] >> 4;
        entropies->_[0] += ((entropies->_[0] + 128) >> 7) * 5;
        entropies->_[1] += ((entropies->_[1] + 64) >> 6) * 5;
        entropies->_[2] -= ((entropies->_[2] + 30) >> 5) * 2;
        break;
    default:
        base = (((entropies->_[0] >> 4) + 1) +
                ((entropies->_[1] >> 4) + 1) +
                (((entropies->_[2] >> 4) + 1) * (m - 2)));
        add = entropies->_[2] >> 4;
        entropies->_[0] += ((entropies->_[0] + 128) >> 7) * 5;
        entropies->_[1] += ((entropies->_[1] + 64) >> 6) * 5;
        entropies->_[2] += ((entropies->_[2] + 32) >> 5) * 5;
        break;
    }

    if (add == 0) {
        u = base;
    } else {
        const unsigned p = LOG2(add);
        const int e = (1 << (p + 1)) - add - 1;
        const unsigned r = bs->read(bs, p);
        if (r >= e) {
            u = base + (r * 2) - e + bs->read(bs, 1);
        } else {
            u = base + r;
        }
    }

    if (bs->read(bs, 1)) {
        return -u - 1;
    } else {
        return u;
    }
}

static status
decorrelate_channels(const array_i* decorrelation_terms,
                     const array_i* decorrelation_deltas,
                     const array_ia* decorrelation_weights,
                     const array_iaa* decorrelation_samples,
                     const array_ia* residuals,
                     array_ia* decorrelated,
                     array_ia* correlated)
{
    status status;
    unsigned pass;

    correlated->reset(correlated);

    if (residuals->len == 1) {
        residuals->copy(residuals, decorrelated);
        correlated->append(correlated);

        for (pass = 0; pass < decorrelation_terms->len; pass++) {
            correlated->swap(correlated, decorrelated);

            if ((status = decorrelate_1ch_pass(
                              decorrelation_terms->_[pass],
                              decorrelation_deltas->_[pass],
                              decorrelation_weights->_[pass]->_[0],
                              decorrelation_samples->_[pass]->_[0],
                              correlated->_[0],
                              decorrelated->_[0])) != OK) {
                return status;
            }
        }

    } else if (residuals->len == 2) {
        residuals->copy(residuals, decorrelated);

        for (pass = 0; pass < decorrelation_terms->len; pass++) {
            correlated->swap(correlated, decorrelated);

            if ((status = decorrelate_2ch_pass(
                              decorrelation_terms->_[pass],
                              decorrelation_deltas->_[pass],
                              decorrelation_weights->_[pass]->_[0],
                              decorrelation_weights->_[pass]->_[1],
                              decorrelation_samples->_[pass]->_[0],
                              decorrelation_samples->_[pass]->_[1],
                              correlated,
                              decorrelated)) != OK) {
                return status;
            }
        }
    } else {
        fprintf(stderr, "channel count must be 1 or 2\n");
        abort();
    }

    return OK;
}

static inline int
apply_weight(int weight, int64_t sample)
{
    int64_t temp = (int64_t)weight * sample + (1 << 9);
    return (int)(temp >> 10);
}

static inline int
update_weight(int64_t source, int result, int delta)
{
    if ((source == 0) || (result == 0)) {
        return 0;
    } else if ((source ^ result) >= 0) {
        return delta;
    } else {
        return -delta;
    }
}

static status
decorrelate_1ch_pass(int decorrelation_term,
                     int decorrelation_delta,
                     int decorrelation_weight,
                     const array_i* decorrelation_samples,
                     const array_i* correlated,
                     array_i* decorrelated)
{
    unsigned i;

    decorrelated->reset(decorrelated);

    switch (decorrelation_term) {
    case 18:
        decorrelation_samples->copy(decorrelation_samples, decorrelated);
        decorrelated->reverse(decorrelated);
        decorrelated->resize_for(decorrelated, correlated->len);
        for (i = 0; i < correlated->len; i++) {
            const int64_t temp =
                (3 * decorrelated->_[i + 1] - decorrelated->_[i]) >> 1;
            a_append(decorrelated,
                     apply_weight(decorrelation_weight, temp) +
                     correlated->_[i]);
            decorrelation_weight += update_weight(temp,
                                                  correlated->_[i],
                                                  decorrelation_delta);
        }
        decorrelated->de_head(decorrelated, 2, decorrelated);
        return OK;
    case 17:
        decorrelation_samples->copy(decorrelation_samples, decorrelated);
        decorrelated->reverse(decorrelated);
        decorrelated->resize_for(decorrelated, correlated->len);
        for (i = 0; i < correlated->len; i++) {
            const int64_t temp =
                2 * decorrelated->_[i + 1] - decorrelated->_[i];
            a_append(decorrelated,
                     apply_weight(decorrelation_weight, temp) +
                     correlated->_[i]);
            decorrelation_weight += update_weight(temp,
                                                  correlated->_[i],
                                                  decorrelation_delta);
        }
        decorrelated->de_head(decorrelated, 2, decorrelated);
        return OK;
    case 8:
    case 7:
    case 6:
    case 5:
    case 4:
    case 3:
    case 2:
    case 1:
        decorrelation_samples->copy(decorrelation_samples, decorrelated);
        decorrelated->resize_for(decorrelated, correlated->len);
        for (i = 0; i < correlated->len; i++) {
            a_append(decorrelated,
                     apply_weight(decorrelation_weight,
                                  decorrelated->_[i]) + correlated->_[i]);
            decorrelation_weight += update_weight(decorrelated->_[i],
                                                  correlated->_[i],
                                                  decorrelation_delta);
        }
        decorrelated->de_head(decorrelated, decorrelation_term, decorrelated);
        return OK;
    default:
        return INVALID_DECORRELATION_TERM;
    }
}

static status
decorrelate_2ch_pass(int decorrelation_term,
                     int decorrelation_delta,
                     int weight_0,
                     int weight_1,
                     const array_i* samples_0,
                     const array_i* samples_1,
                     const array_ia* correlated,
                     array_ia* decorrelated)
{
    status status;

    if (((17 <= decorrelation_term) && (decorrelation_term <= 18)) ||
        ((1 <= decorrelation_term) && (decorrelation_term <= 8))) {
        decorrelated->reset(decorrelated);
        if ((status = decorrelate_1ch_pass(
                          decorrelation_term,
                          decorrelation_delta,
                          weight_0,
                          samples_0,
                          correlated->_[0],
                          decorrelated->append(decorrelated))) != OK)
            return status;
        if ((status = decorrelate_1ch_pass(
                          decorrelation_term,
                          decorrelation_delta,
                          weight_1,
                          samples_1,
                          correlated->_[1],
                          decorrelated->append(decorrelated))) != OK)
            return status;

        return OK;
    } else if ((-3 <= decorrelation_term) && (decorrelation_term <= -1)) {
        array_i* corr_0;
        array_i* corr_1;
        array_i* decorr_0;
        array_i* decorr_1;
        unsigned i;

        decorrelated->reset(decorrelated);
        corr_0 = correlated->_[0];
        corr_1 = correlated->_[1];
        decorr_0 = decorrelated->append(decorrelated);
        decorr_1 = decorrelated->append(decorrelated);
        decorr_0->extend(decorr_0, samples_1);
        decorr_1->extend(decorr_1, samples_0);
        decorr_0->resize_for(decorr_0, corr_0->len);
        decorr_1->resize_for(decorr_1, corr_1->len);

        switch (decorrelation_term) {
        case -1:
            for (i = 0; i < corr_0->len; i++) {
                a_append(decorr_0,
                         apply_weight(weight_0, decorr_1->_[i]) +
                         corr_0->_[i]);
                a_append(decorr_1,
                         apply_weight(weight_1, decorr_0->_[i + 1]) +
                         corr_1->_[i]);
                weight_0 += update_weight(decorr_1->_[i],
                                          corr_0->_[i],
                                          decorrelation_delta);
                weight_1 += update_weight(decorr_0->_[i + 1],
                                          corr_1->_[i],
                                          decorrelation_delta);
                weight_0 = MAX(MIN(weight_0, 1024), -1024);
                weight_1 = MAX(MIN(weight_1, 1024), -1024);
            }
            break;
        case -2:
            for (i = 0; i < corr_0->len; i++) {
                a_append(decorr_1,
                         apply_weight(weight_1, decorr_0->_[i]) +
                         corr_1->_[i]);
                a_append(decorr_0,
                         apply_weight(weight_0, decorr_1->_[i + 1]) +
                         corr_0->_[i]);
                weight_1 += update_weight(decorr_0->_[i],
                                          corr_1->_[i],
                                          decorrelation_delta);
                weight_0 += update_weight(decorr_1->_[i + 1],
                                          corr_0->_[i],
                                          decorrelation_delta);
                weight_1 = MAX(MIN(weight_1, 1024), -1024);
                weight_0 = MAX(MIN(weight_0, 1024), -1024);
            }
            break;
        case -3:
            for (i = 0; i < corr_0->len; i++) {
                a_append(decorr_0,
                         apply_weight(weight_0, decorr_1->_[i]) +
                         corr_0->_[i]);
                a_append(decorr_1,
                         apply_weight(weight_1, decorr_0->_[i]) +
                         corr_1->_[i]);
                weight_0 += update_weight(decorr_1->_[i],
                                          corr_0->_[i],
                                          decorrelation_delta);
                weight_1 += update_weight(decorr_0->_[i],
                                          corr_1->_[i],
                                          decorrelation_delta);
                weight_0 = MAX(MIN(weight_0, 1024), -1024);
                weight_1 = MAX(MIN(weight_1, 1024), -1024);
            }
            break;
        default:
            /*can't get here*/
            abort();
        }

        decorr_0->de_head(decorr_0, 1, decorr_0);
        decorr_1->de_head(decorr_1, 1, decorr_1);
        return OK;
    } else {
        return INVALID_DECORRELATION_TERM;
    }
}

static void
undo_joint_stereo(const array_ia* mid_side, array_ia* left_right)
{
    array_i* mid = mid_side->_[0];
    array_i* side = mid_side->_[1];
    array_i* left;
    array_i* right;
    unsigned i;

    left_right->reset(left_right);
    left = left_right->append(left_right);
    right = left_right->append(left_right);

    for (i = 0; i < mid->len; i++) {
        right->append(right, side->_[i] - (mid->_[i] >> 1));
        left->append(left, mid->_[i] + right->_[i]);
    }
}

static uint32_t
calculate_crc(const array_ia* channels)
{
    unsigned i;
    uint32_t crc = 0xFFFFFFFF;

    if (channels->len == 2) {
        for (i = 0; i < channels->_[0]->len; i++) {
            crc = (3 * crc) + channels->_[0]->_[i];
            crc = (3 * crc) + channels->_[1]->_[i];
        }
    } else {
        for (i = 0; i < channels->_[0]->len; i++) {
            crc = (3 * crc) + channels->_[0]->_[i];
        }
    }
    return crc;
}

static int
unencode_sample_rate(unsigned encoded_sample_rate)
{
    switch (encoded_sample_rate) {
    case 0:
        return 6000;
    case 1:
        return 8000;
    case 2:
        return 9600;
    case 3:
        return 11025;
    case 4:
        return 12000;
    case 5:
        return 16000;
    case 6:
        return 22050;
    case 7:
        return 24000;
    case 8:
        return 32000;
    case 9:
        return 44100;
    case 10:
        return 48000;
    case 11:
        return 64000;
    case 12:
        return 88200;
    case 13:
        return 96000;
    case 14:
        return 192000;
    default:
        return 0;
    }
}

static int
unencode_bits_per_sample(unsigned encoded_bits_per_sample)
{
    switch (encoded_bits_per_sample) {
    case 0:
        return 8;
    case 1:
        return 16;
    case 2:
        return 24;
    case 3:
        return 32;
    default:
        /*a 2 bit field, so we shouldn't get this far*/
        abort();
        return 0;
    }
}

static int
read_sub_block(BitstreamReader* bitstream,
               struct sub_block* sub_block) {
    if (!setjmp(*br_try(bitstream))) {
        bitstream->parse(bitstream, "5u 1u 1u 1u",
                         &(sub_block->metadata_function),
                         &(sub_block->nondecoder_data),
                         &(sub_block->actual_size_1_less),
                         &(sub_block->large_sub_block));

        if (!sub_block->large_sub_block) {
            sub_block->size = bitstream->read(bitstream, 8);
        } else {
            sub_block->size = bitstream->read(bitstream, 24);
        }

        br_substream_reset(sub_block->data);

        if (!sub_block->actual_size_1_less) {
            bitstream->substream_append(bitstream,
                                        sub_block->data,
                                        sub_block->size * 2);
        } else {
            bitstream->substream_append(bitstream,
                                        sub_block->data,
                                        sub_block->size * 2 - 1);
            bitstream->skip(bitstream, 8);
        }

        br_etry(bitstream);
        if (sub_block->large_sub_block) {
            return 4 + sub_block->size * 2;
        } else {
            return 2 + sub_block->size * 2;
        }
    } else {
        br_etry(bitstream);
        return -1;
    }
}

static unsigned
sub_block_data_size(const struct sub_block* sub_block)
{
    if (!sub_block->actual_size_1_less) {
        return sub_block->size * 2;
    } else {
        return sub_block->size * 2 - 1;
    }
}

static status
find_sub_block(const struct block_header* block_header,
               BitstreamReader* bitstream,
               unsigned metadata_function,
               unsigned nondecoder_data,
               struct sub_block* sub_block)
{
    unsigned sub_blocks_size = block_header->block_size - 24;
    int sub_block_size;
    BitstreamReader* sub_blocks = br_substream_new(BS_LITTLE_ENDIAN);

    if (!setjmp(*br_try(bitstream))) {
        bitstream->substream_append(bitstream, sub_blocks, sub_blocks_size);
        br_etry(bitstream);
    } else {
        br_etry(bitstream);
        sub_blocks->close(sub_blocks);
        return IO_ERROR;
    }

    while (sub_blocks_size > 0) {
        if ((sub_block_size = read_sub_block(sub_blocks,
                                             sub_block)) == -1) {
            sub_blocks->close(sub_blocks);
            return IO_ERROR;
        } else {
            sub_blocks_size -= sub_block_size;
        }

        if ((sub_block->metadata_function == metadata_function) &&
            (sub_block->nondecoder_data == nondecoder_data)) {
            sub_blocks->close(sub_blocks);
            return OK;
        }
    }

    sub_blocks->close(sub_blocks);
    return SUB_BLOCK_NOT_FOUND;
}

static status
read_sample_rate_sub_block(const struct block_header* block_header,
                           BitstreamReader* bitstream,
                           int* sample_rate)
{
    status status;
    struct sub_block sub_block;
    sub_block.data = br_substream_new(BS_LITTLE_ENDIAN);

    switch (status = find_sub_block(block_header,
                                    bitstream,
                                    7, 1,
                                    &sub_block)) {
    case OK:
        *sample_rate = (int)(sub_block.data->read(
                                 sub_block.data,
                                 sub_block_data_size(&sub_block) * 8));
        sub_block.data->close(sub_block.data);
        return OK;
    default:
        sub_block.data->close(sub_block.data);
        return status;
    }
}

static status
read_channel_count_sub_block(const struct block_header* block_header,
                             BitstreamReader* bitstream,
                             int* channel_count,
                             int* channel_mask)
{
    status status;
    struct sub_block sub_block;
    sub_block.data = br_substream_new(BS_LITTLE_ENDIAN);

    switch (status = find_sub_block(block_header,
                                    bitstream,
                                    13, 0,
                                    &sub_block)) {
    case OK:
        if (sub_block_data_size(&sub_block) >= 2) {
            *channel_count = sub_block.data->read(sub_block.data, 8);
            *channel_mask =
                sub_block.data->read(sub_block.data,
                                     (sub_block_data_size(&sub_block) - 1) * 8);
            sub_block.data->close(sub_block.data);
            return OK;
        } else {
            sub_block.data->close(sub_block.data);
            return IO_ERROR;
        }
    default:
        sub_block.data->close(sub_block.data);
        return status;
    }
}

static status
read_extended_integers(const struct sub_block* sub_block,
                       struct extended_integers* extended_integers)
{
    if (sub_block_data_size(sub_block) == 4) {
        sub_block->data->parse(sub_block->data, "8u 8u 8u 8u",
                               &(extended_integers->sent_bits),
                               &(extended_integers->zero_bits),
                               &(extended_integers->one_bits),
                               &(extended_integers->duplicate_bits));
        return OK;
    } else {
        return IO_ERROR;
    }
}

static void
undo_extended_integers(const struct extended_integers* params,
                       const array_ia* extended_integers,
                       array_ia* un_extended_integers)
{
    unsigned c;
    unsigned i;
    const array_i* extended;
    array_i* un_extended;

    un_extended_integers->reset(un_extended_integers);

    for (c = 0; c < extended_integers->len; c++) {
        extended = extended_integers->_[c];
        un_extended = un_extended_integers->append(un_extended_integers);
        if (params->zero_bits > 0) {
            for (i = 0; i < extended->len; i++)
                un_extended->append(un_extended,
                                    extended->_[i] << params->zero_bits);
        } else if (params->one_bits > 0) {
            for (i = 0; i < extended->len; i++)
                un_extended->append(un_extended,
                                    (extended->_[i] << params->one_bits) |
                                    ((1 << params->one_bits) - 1));
        } else if (params->duplicate_bits > 0) {
            for (i = 0; i < extended->len; i++) {
                int shifted = extended->_[i];
                if ((shifted % 2) == 0) {
                    un_extended->append(un_extended,
                                        shifted << params->duplicate_bits);
                } else {
                    un_extended->append(un_extended,
                                        (shifted << params->duplicate_bits) |
                                        ((1 << params->duplicate_bits) - 1));
                }
            }
        } else {
            extended->copy(extended, un_extended);
        }
    }
}

#ifdef STANDALONE
int main(int argc, char* argv[]) {
    decoders_WavPackDecoder decoder;
    unsigned bytes_per_sample;
    unsigned char *output_data;
    unsigned output_data_size;
    FrameList_int_to_char_converter converter;

    struct block_header block_header;
    struct sub_block md5_sub_block;
    unsigned char sub_block_md5sum[16];
    unsigned char stream_md5sum[16];

    if (argc < 2) {
        fprintf(stderr, "*** Usage: %s <file.wv>\n", argv[0]);
        return 1;
    }

    /*initialize reader object*/
    if (WavPackDecoder_init(&decoder, argv[1])) {
        fprintf(stderr, "*** Error initializing WavPack decoder\n");
        return 1;
    } else {
        bytes_per_sample = decoder.bits_per_sample / 8;
        output_data = malloc(1);
        output_data_size = 1;
        converter = FrameList_get_int_to_char_converter(
            decoder.bits_per_sample, 0, 1);
    }

    while (decoder.remaining_pcm_samples) {
        BitstreamReader* bs = decoder.bitstream;
        array_ia* channels_data = decoder.channels_data;
        status error;
        BitstreamReader* block_data = decoder.block_data;
        unsigned pcm_size;
        unsigned channel;
        unsigned frame;

        channels_data->reset(channels_data);

        do {
            /*read block header*/
            if ((error = read_block_header(bs, &block_header)) != OK) {
                fprintf(stderr, "*** Error: %s\n",
                        wavpack_strerror(error));
                goto error;
            }

            /*FIXME - ensure block header is consistent
              with the starting block header*/

            br_substream_reset(block_data);

            /*read block data*/
            if (!setjmp(*br_try(bs))) {
                bs->substream_append(bs, block_data,
                                     block_header.block_size - 24);
                br_etry(bs);
            } else {
                br_etry(bs);
                fprintf(stderr, "I/O error reading block data");
                goto error;
            }

            /*decode block to 1 or 2 channels of PCM data*/
            if ((error = decode_block(&decoder,
                                      &block_header,
                                      block_data,
                                      block_header.block_size - 24,
                                      channels_data)) != OK) {
                fprintf(stderr, "*** Error: %s\n",
                        wavpack_strerror(error));
                goto error;
            }
        } while (block_header.final_block == 0);

        /*deduct frame count from total remaining*/
        decoder.remaining_pcm_samples -= MIN(channels_data->_[0]->len,
                                             decoder.remaining_pcm_samples);

        /*convert all channels to single PCM string*/
        pcm_size = (bytes_per_sample *
                    channels_data->len *
                    channels_data->_[0]->len);
        if (pcm_size > output_data_size) {
            output_data_size = pcm_size;
            output_data = realloc(output_data, output_data_size);
        }
        for (channel = 0; channel < channels_data->len; channel++) {
            const array_i* channel_data = channels_data->_[channel];
            for (frame = 0; frame < channel_data->len; frame++) {
                converter(channel_data->_[frame],
                          output_data +
                          ((frame * channels_data->len) + channel) *
                          bytes_per_sample);
            }
        }

        /*update stream's MD5 sum with framelist data*/
        audiotools__MD5Update(&(decoder.md5), output_data, pcm_size);

        /*output PCM string to stdout*/
        fwrite(output_data, sizeof(unsigned char), pcm_size, stdout);
    }

    /*check for final MD5 sub block, if present*/
    md5_sub_block.data = decoder.sub_block_data;

    /*check for final MD5 block, which may not be present*/
    if ((read_block_header(decoder.bitstream, &block_header) == OK) &&
        (find_sub_block(&block_header,
                        decoder.bitstream,
                        6, 1, &md5_sub_block) == OK) &&
        (sub_block_data_size(&md5_sub_block) == 16)) {

        /*have valid MD5 block, so check it*/
        md5_sub_block.data->read_bytes(md5_sub_block.data,
                                       (uint8_t*)sub_block_md5sum,
                                       16);

        audiotools__MD5Final(stream_md5sum, &(decoder.md5));

        if (memcmp(sub_block_md5sum, stream_md5sum, 16)) {
            fprintf(stderr, "*** MD5 mismatch at end of stream\n");
            goto error;
        }
    }

    /*deallocate reader object*/
    WavPackDecoder_dealloc(&decoder);
    free(output_data);

    return 0;

error:
    /*deallocate reader object*/
    WavPackDecoder_dealloc(&decoder);
    free(output_data);

    return 1;
}
#endif
