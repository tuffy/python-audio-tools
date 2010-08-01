#include <Python.h>
#include "bitstream_w.h"
#include "encoders.h"

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

PyMODINIT_FUNC
initencoders(void)
{
    PyObject* m;

    encoders_BitstreamWriterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&encoders_BitstreamWriterType) < 0)
        return;

    m = Py_InitModule3("encoders", module_methods,
                       "Low-level audio format encoders");

    Py_INCREF(&encoders_BitstreamWriterType);
    PyModule_AddObject(m, "BitstreamWriter",
                       (PyObject *)&encoders_BitstreamWriterType);

}

int
BitstreamWriter_init(encoders_BitstreamWriter *self, PyObject *args) {
    PyObject *file_obj;
    int little_endian;

    self->file_obj = NULL;

    if (!PyArg_ParseTuple(args, "Oi", &file_obj, &little_endian))
        return -1;

    if (!PyFile_CheckExact(file_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be an actual file object");
        return -1;
    }

    Py_INCREF(file_obj);
    self->file_obj = file_obj;

    self->bitstream = bs_open(PyFile_AsFile(self->file_obj),
                        little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    return 0;
}

void
BitstreamWriter_dealloc(encoders_BitstreamWriter *self) {
    if (self->file_obj != NULL) {
        self->bitstream->file = NULL;
        bs_close(self->bitstream);
        Py_DECREF(self->file_obj);
    }

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
BitstreamWriter_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds) {
    encoders_BitstreamWriter *self;

    self = (encoders_BitstreamWriter *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
BitstreamWriter_write(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    self->bitstream->write_bits(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write_signed(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    self->bitstream->write_signed_bits(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write64(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    self->bitstream->write_bits64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_unary(encoders_BitstreamWriter *self, PyObject *args) {
    int stop_bit;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    self->bitstream->write_unary(self->bitstream, stop_bit, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_byte_align(encoders_BitstreamWriter *self, PyObject *args) {
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_set_endianness(encoders_BitstreamWriter *self,
                               PyObject *args) {
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    if ((little_endian != 0) && (little_endian != 1)) {
        PyErr_SetString(PyExc_ValueError,
                    "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }

    self->bitstream->set_endianness(
                    self->bitstream,
                    little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_close(encoders_BitstreamWriter *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}
