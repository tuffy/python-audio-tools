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
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_bits_per_sample(decoders_MLPDecoder *self, void *closure) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_channels(decoders_MLPDecoder *self, void *closure) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
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
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

