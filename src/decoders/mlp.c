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

    /*store initial position in stream/
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

    return 0;
}

void
MLPDecoder_dealloc(decoders_MLPDecoder *self)
{
    bs_close(self->bitstream);

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

static PyObject*
MLPDecoder_sample_rate(decoders_MLPDecoder *self, void *closure) {
    switch (self->major_sync.group1_sample_rate) {
    case 0x0:
        return Py_BuildValue("i", 48000);
    case 0x1:
        return Py_BuildValue("i", 96000);
    case 0x2:
        return Py_BuildValue("i", 192000);
    case 0x3:
        return Py_BuildValue("i", 394000);
    case 0x4:
        return Py_BuildValue("i", 768000);
    case 0x5:
        return Py_BuildValue("i", 1536000);
    case 0x6:
        return Py_BuildValue("i", 3072000);
    case 0x8:
        return Py_BuildValue("i", 44100);
    case 0x9:
        return Py_BuildValue("i", 88200);
    case 0xA:
        return Py_BuildValue("i", 176400);
    case 0xB:
        return Py_BuildValue("i", 352800);
    case 0xC:
        return Py_BuildValue("i", 705600);
    case 0xD:
        return Py_BuildValue("i", 1411200);
    case 0xE:
        return Py_BuildValue("i", 2822400);
    default:
        PyErr_SetString(PyExc_ValueError, "unsupported sample rate");
        return NULL;
    }

}

static PyObject*
MLPDecoder_bits_per_sample(decoders_MLPDecoder *self, void *closure) {
    switch (self->major_sync.group1_bits) {
    case 0:
        return Py_BuildValue("i", 16);
    case 1:
        return Py_BuildValue("i", 20);
    case 2:
        return Py_BuildValue("i", 24);
    default:
        PyErr_SetString(PyExc_ValueError, "unsupported bits-per-sample");
        return NULL;
    }
}

static PyObject*
MLPDecoder_channels(decoders_MLPDecoder *self, void *closure) {
    switch (self->major_sync.channel_assignment) {
    case 0x0:
        return Py_BuildValue("i", 1);
    case 0x1:
        return Py_BuildValue("i", 2);
    case 0x2:
    case 0x4:
    case 0x7:
        return Py_BuildValue("i", 3);
    case 0x3:
    case 0x5:
    case 0x8:
    case 0xA:
    case 0xD:
    case 0xF:
        return Py_BuildValue("i", 4);
    case 0x6:
    case 0x9:
    case 0xB:
    case 0xE:
    case 0x10:
    case 0x12:
    case 0x13:
        return Py_BuildValue("i", 5);
    case 0xC:
    case 0x11:
    case 0x14:
        return Py_BuildValue("i", 6);
    default:
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
    int total_frame_size = mlp_total_frame_size(self->bitstream);

    if (total_frame_size > 0) {
        self->bitstream->skip(self->bitstream, (total_frame_size - 4) * 8);
        return Py_BuildValue("i", total_frame_size);
    } else {
        Py_INCREF(Py_None);
        return Py_None;
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
