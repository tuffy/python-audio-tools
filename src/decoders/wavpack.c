#include "wavpack.h"

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

    /*FIXME - check for EOF here*/
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

    fseek(self->file, 0, SEEK_SET);

    /*setup a bunch of temporary buffers*/

    return 0;
}

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self) {
    if (self->filename != NULL)
        free(self->filename);

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

status
WavPackDecoder_read_block_header(Bitstream* bitstream,
                                 struct wavpack_block_header* header) {
    /*read and verify block ID*/
    if (bitstream->read(bitstream, 32) != 0x6B707677) {
        PyErr_SetString(PyExc_ValueError, "invalid block ID");
        return ERROR;
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
    default: break; /*can't happen*/
    }

    header->mono_output = bitstream->read(bitstream, 1);
    header->hybrid_mode = bitstream->read(bitstream, 1);
    header->joint_stereo = bitstream->read(bitstream, 1);
    header->cross_channel_decorrelation = bitstream->read(bitstream, 1);
    header->hybrid_noise_shaping = bitstream->read(bitstream, 1);
    header->floating_point_data = bitstream->read(bitstream, 1);
    header->extended_size_integers = bitstream->read(bitstream, 1);
    header->hybrid_parameters_control_bitrate = bitstream->read(bitstream, 1);
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
    case 0x9: header->sample_rate =  41000; break;
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
        return ERROR;
    }

    header->crc = bitstream->read(bitstream, 32);

    return OK;
}

/*as with Shorten, whose analyze_frame() returns the next command
  (likely only part of a total collection of PCM frames),
  this returns a single block which may be only one of several
  needed to reconstruct a multichannel set of audio*/

static PyObject*
WavPackDecoder_analyze_frame(decoders_WavPackDecoder* self, PyObject *args) {
    struct wavpack_block_header block_header;

    if (self->remaining_samples > 0) {
        /*FIXME - check for EOFs here*/
        if (WavPackDecoder_read_block_header(self->bitstream,
                                             &block_header) == OK) {
            /*FIXME - parse sub-blocks here*/
            fseek(self->file, block_header.block_size - 24, SEEK_CUR);

            self->remaining_samples -= block_header.block_samples;
            return Py_BuildValue(
                    "{sI sI si si si sI sI "
                    "si si si si si si si si si si si si si si si "
                    "si si sI}",
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
                    "crc", block_header.crc);

        } else {
            return NULL;
        }
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}
