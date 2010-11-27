#include "mlp.h"

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
MLPDecoder_init(decoders_MLPDecoder *self,
                PyObject *args, PyObject *kwds) {
    char *filename;
    fpos_t pos;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    /*open the MLP file*/
    self->file = fopen(filename, "rb");
    if (self->file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = bs_open(self->file, BS_BIG_ENDIAN);
    }

    /*store initial position in stream*/
    if (fgetpos(self->bitstream->file, &pos) == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    }

    /*skip initial frame size, if possible*/
    if (mlp_total_frame_size(self->bitstream) == -1) {
        PyErr_SetString(PyExc_IOError, "unable to read initial major sync");
        return -1;
    }

    /*attempt to read initial major sync*/
    switch (mlp_read_major_sync(self->bitstream, &(self->major_sync))) {
    case MLP_MAJOR_SYNC_OK:
        break;
    case MLP_MAJOR_SYNC_NOT_FOUND:
        PyErr_SetString(PyExc_ValueError, "invalid initial major sync");
        return -1;
    case MLP_MAJOR_SYNC_ERROR:
        PyErr_SetString(PyExc_IOError, "unable to read initial major sync");
        return -1;
    }

    /*restore initial stream position*/
    if (fsetpos(self->bitstream->file, &pos) == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    }

    mlp_init_frame(&(self->major_sync), &(self->frame));

    return 0;
}

void
MLPDecoder_dealloc(decoders_MLPDecoder *self)
{
    bs_close(self->bitstream);
    mlp_free_frame(&(self->frame));

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
MLPDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_MLPDecoder *self;

    self = (decoders_MLPDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int mlp_sample_rate(struct mlp_MajorSync* major_sync) {
    switch (major_sync->group1_sample_rate) {
    case 0x0:
        return 48000;
    case 0x1:
        return 96000;
    case 0x2:
        return 192000;
    case 0x3:
        return 394000;
    case 0x4:
        return 768000;
    case 0x5:
        return 1536000;
    case 0x6:
        return 3072000;
    case 0x8:
        return 44100;
    case 0x9:
        return 88200;
    case 0xA:
        return 176400;
    case 0xB:
        return 352800;
    case 0xC:
        return 705600;
    case 0xD:
        return 1411200;
    case 0xE:
        return 2822400;
    default:
        return -1;
    }
}

static PyObject*
MLPDecoder_sample_rate(decoders_MLPDecoder *self, void *closure) {
    int rate = mlp_sample_rate(&(self->major_sync));
    if (rate > 0) {
        return Py_BuildValue("i", rate);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported sample rate");
        return NULL;
    }

}

int mlp_bits_per_sample(struct mlp_MajorSync* major_sync) {
    switch (major_sync->group1_bits) {
    case 0:
        return 16;
    case 1:
        return 20;
    case 2:
        return 24;
    default:
        return -1;
    }
}

static PyObject*
MLPDecoder_bits_per_sample(decoders_MLPDecoder *self, void *closure) {
    int bits_per_sample = mlp_bits_per_sample(&(self->major_sync));
    if (bits_per_sample > 0) {
        return Py_BuildValue("i", bits_per_sample);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported bits-per-sample");
        return NULL;
    }
}

int mlp_channel_count(struct mlp_MajorSync* major_sync) {
    switch (major_sync->channel_assignment) {
    case 0x0:
        return 1;
    case 0x1:
        return 2;
    case 0x2:
    case 0x4:
    case 0x7:
        return 3;
    case 0x3:
    case 0x5:
    case 0x8:
    case 0xA:
    case 0xD:
    case 0xF:
        return 4;
    case 0x6:
    case 0x9:
    case 0xB:
    case 0xE:
    case 0x10:
    case 0x12:
    case 0x13:
        return 5;
    case 0xC:
    case 0x11:
    case 0x14:
        return 6;
    default:
        return -1;
    }
}

static PyObject*
MLPDecoder_channels(decoders_MLPDecoder *self, void *closure) {
    int channels = mlp_channel_count(&(self->major_sync));
    if (channels > 0) {
        return Py_BuildValue("i", channels);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported channel assignment");
        return NULL;
    }
}

static PyObject*
MLPDecoder_channel_mask(decoders_MLPDecoder *self, void *closure) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_read(decoders_MLPDecoder* self, PyObject *args) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_close(decoders_MLPDecoder* self, PyObject *args) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_analyze_frame(decoders_MLPDecoder* self, PyObject *args) {
    int frame_size = mlp_read_frame(self->bitstream,
                                    &(self->major_sync),
                                    &(self->frame));
    if (frame_size > 0) {
        return Py_BuildValue("i", self->frame.total_size);
    } else if (frame_size == 0) {
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        return NULL;
    }
}

int
mlp_total_frame_size(Bitstream* bitstream) {
    int total_size;

    if (!setjmp(*bs_try(bitstream))) {
        bitstream->skip(bitstream, 4);
        total_size = bitstream->read(bitstream, 12) * 2;
        bitstream->skip(bitstream, 16);
        bs_etry(bitstream);
        return total_size;
    } else {
        bs_etry(bitstream);
        return -1;
    }
}

mlp_major_sync_status
mlp_read_major_sync(Bitstream* bitstream, struct mlp_MajorSync* major_sync) {
    if (!setjmp(*bs_try(bitstream))) {
        if (bitstream->read(bitstream, 24) != 0xF8726F) {
            /*sync words not found*/
            bs_etry(bitstream);
            fseek(bitstream->file, -3, SEEK_CUR);
            return MLP_MAJOR_SYNC_NOT_FOUND;
        }
        if (bitstream->read(bitstream, 8) != 0xBB) {
            /*stream type not 0xBB*/
            bs_etry(bitstream);
            fseek(bitstream->file, -4, SEEK_CUR);
            return MLP_MAJOR_SYNC_NOT_FOUND;
        }

        major_sync->group1_bits = bitstream->read(bitstream, 4);
        major_sync->group2_bits = bitstream->read(bitstream, 4);
        major_sync->group1_sample_rate = bitstream->read(bitstream, 4);
        major_sync->group2_sample_rate = bitstream->read(bitstream, 4);
        bitstream->skip(bitstream, 11); /*unknown 1*/
        major_sync->channel_assignment = bitstream->read(bitstream, 5);
        bitstream->skip(bitstream, 48); /*unknown 2*/
        bitstream->skip(bitstream, 1);  /*is VBR*/
        bitstream->skip(bitstream, 15); /*peak bitrate*/
        major_sync->substream_count = bitstream->read(bitstream, 4);
        bitstream->skip(bitstream, 92); /*unknown 3*/

        bs_etry(bitstream);
        return MLP_MAJOR_SYNC_OK;
    } else {
        bs_etry(bitstream);
        return MLP_MAJOR_SYNC_ERROR;
    }
}

void
mlp_init_frame(struct mlp_MajorSync* major_sync,
               struct mlp_Frame* frame) {
    frame->substream_count = major_sync->substream_count;
    frame->channel_count = mlp_channel_count(major_sync);
    frame->sizes = malloc(sizeof(struct mlp_SubstreamSize) *
                          frame->substream_count);
    frame->substreams = malloc(sizeof(struct mlp_Substream) *
                               frame->substream_count);
}

void
mlp_free_frame(struct mlp_Frame* frame) {
    free(frame->sizes);
    free(frame->substreams);
}

int
mlp_read_frame(Bitstream* bitstream,
               struct mlp_MajorSync* major_sync,
               struct mlp_Frame* frame) {
    struct mlp_MajorSync frame_major_sync;
    int i;

    /*read the 32-bit total size value*/
    if ((frame->total_size = mlp_total_frame_size(bitstream)) == -1) {
        return 0;
    }

    /*read a major sync, if present*/
    if (mlp_read_major_sync(bitstream,
                            &frame_major_sync) == MLP_MAJOR_SYNC_ERROR) {
        PyErr_SetString(PyExc_IOError, "I/O error reading major sync");
        return -1;
    }

    /*read one SubstreamSize per substream*/
    for (i = 0; i < major_sync->substream_count; i++) {
        if (mlp_read_substream_size(bitstream, &(frame->sizes[i])) == ERROR)
            return -1;
    }

    /*read one Substream per substream*/
    for (i = 0; i < major_sync->substream_count; i++) {
        bitstream->skip(bitstream, frame->sizes[i].substream_size * 8);
        /*FIXME*/
    }

    return frame->total_size;
}

mlp_status
mlp_read_substream_size(Bitstream* bitstream,
                        struct mlp_SubstreamSize* size) {
    if (bitstream->read(bitstream, 1) == 1) {
        PyErr_SetString(PyExc_ValueError,
                        "extraword cannot be present in substream size");
        return ERROR;
    }
    size->nonrestart_substream = bitstream->read(bitstream, 1);
    size->checkdata_present = bitstream->read(bitstream, 1);
    bitstream->skip(bitstream, 1);
    size->substream_size = bitstream->read(bitstream, 12) * 2;

    return OK;
}
