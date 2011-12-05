#include "wavpack.h"
#include "../pcmconv.h"

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
    struct block_header header;
    char* filename;
    status error;

    self->filename = NULL;
    self->bitstream = NULL;
    self->file = NULL;

    self->md5sum_checked = 0;
    self->channels_data = array_ia_new();
    self->block_data = br_substream_new(BS_LITTLE_ENDIAN);
    self->sub_block_data = br_substream_new(BS_LITTLE_ENDIAN);

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

    self->filename = strdup(filename);

    self->sample_rate = 0;
    self->bits_per_sample = 0;
    self->channels = 0;
    self->channel_mask = 0;
    self->remaining_pcm_samples = 0;

    /*read initial block to populate
      sample_rate, bits_per_sample, channels, and channel_mask*/
    self->bitstream->mark(self->bitstream);
    if ((error = wavpack_read_block_header(self->bitstream, &header)) != OK) {
        PyErr_SetString(wavpack_exception(error), wavpack_strerror(error));
        self->bitstream->unmark(self->bitstream);
        return -1;
    }

    if ((self->sample_rate = unencode_sample_rate(header.sample_rate)) == 0) {
        /*FIXME - look for sample rate sub block*/
    }

    self->bits_per_sample = unencode_bits_per_sample(header.bits_per_sample);
    if (header.final_block) {
        if ((header.mono_output == 0) && (header.false_stereo == 0)) {
            self->channels = 2;
            self->channel_mask = 0x3;
        } else {
            self->channels = 1;
            self->channel_mask = 0x4;
        }
    } else {
        /*FIXME - look for channel mask sub block*/
    }

    self->remaining_pcm_samples = header.total_samples;

    self->bitstream->rewind(self->bitstream);
    self->bitstream->unmark(self->bitstream);

    return 0;
}

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self) {
    self->channels_data->del(self->channels_data);
    self->block_data->close(self->block_data);
    self->sub_block_data->close(self->sub_block_data);

    Py_XDECREF(self->audiotools_pcm);

    if (self->filename != NULL)
        free(self->filename);

    if (self->bitstream != NULL)
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
    PyObject* framelist;

    channels_data->reset(channels_data);
    br_substream_reset(block_data);

    if (self->remaining_pcm_samples > 0) {
        do {
            /*read block header*/
            if ((error = wavpack_read_block_header(bs, &block_header)) != OK) {
                PyErr_SetString(wavpack_exception(error),
                                wavpack_strerror(error));
                return NULL;
            }

            /*FIXME - ensure block header is consistent
              with the starting block header*/

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
            if ((error = wavpack_decode_block(self,
                                              &block_header,
                                              block_data,
                                              block_header.block_size - 24,
                                              channels_data)) != OK) {
                PyErr_SetString(wavpack_exception(error),
                                wavpack_strerror(error));
                return NULL;
            }
        } while (block_header.final_block == 0);

        /*convert all channels to single PCM framelist*/
        framelist = array_ia_to_FrameList(self->audiotools_pcm,
                                          channels_data,
                                          self->bits_per_sample);

        /*FIXME - update stream's MD5 sum with framelist data*/

        /*deduct frame count from total remaining*/
        /*FIXME - check for 0 channels of output here*/
        if (channels_data->size != 0) {
            self->remaining_pcm_samples -= MIN(channels_data->data[0]->size,
                                               self->remaining_pcm_samples);
        } else {
            fprintf(stderr, "0 channel block found\n");
        }

        return framelist;
    } else {
        if (!self->md5sum_checked) {
            /*FIXME - check MD5 sum here*/
        }

        return empty_FrameList(self->audiotools_pcm,
                               (unsigned int)self->channels,
                               (unsigned int)self->bits_per_sample);
    }
}

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
    default:
        return "unspecified error";
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
    default:
        return PyExc_ValueError;
    }
}

status
wavpack_read_block_header(BitstreamReader* bs, struct block_header* header)
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

status
wavpack_decode_block(decoders_WavPackDecoder* decoder,
                     struct block_header* const block_header,
                     BitstreamReader* block_data,
                     unsigned block_data_size,
                     array_ia* channels)
{
    unsigned metadata_function;
    unsigned nondecoder_data;
    unsigned actual_size_1_less;
    unsigned large_sub_block;
    unsigned sub_block_size;
    BitstreamReader* sub_block_data = decoder->sub_block_data;

    if (!setjmp(*br_try(block_data))) {
        /*parse all decoding parameter sub blocks*/
        while (block_data_size > 0) {
            block_data->parse(block_data, "5u 1u 1u 1u",
                              &metadata_function,
                              &nondecoder_data,
                              &actual_size_1_less,
                              &large_sub_block);
            if (!large_sub_block) {
                sub_block_size = block_data->read(block_data, 8);
            } else {
                sub_block_size = block_data->read(block_data, 24);
            }

            br_reset_recorder(sub_block_data);

            if (!actual_size_1_less) {
                block_data->substream_append(block_data,
                                             sub_block_data,
                                             sub_block_size * 2);
            } else {
                block_data->substream_append(block_data,
                                             sub_block_data,
                                             sub_block_size * 2 - 1);
                block_data->skip(block_data, 1);
            }

            if (!nondecoder_data) {
                switch (metadata_function) {
                case 2:
                    /*FIXME*/
                    break;
                case 3:
                    /*FIXME*/
                    break;
                case 4:
                    /*FIXME*/
                    break;
                case 5:
                    /*FIXME*/
                    break;
                case 9:
                    /*FIXME*/
                    break;
                case 10:
                    /*FIXME*/
                    break;
                }
            }

            if (!large_sub_block) {
                sub_block_size -= (2 + 2 * sub_block_size);
            } else {
                sub_block_size -= (4 + 2 * sub_block_size);
            }
        }

        br_etry(block_data);

        /*convert decoding parameter sub blocks
          into 1 or 2 channels of PCM data*/
        /*FIXME*/

        return OK;
    } else {
        br_etry(block_data);
        return IO_ERROR;
    }
}

int
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

int
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
