#include <Python.h>
#include "bitstream_r.h"
#include "decoders.h"

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

extern PyTypeObject decoders_FlacDecoderType;
extern PyTypeObject decoders_SHNDecoderType;
extern PyTypeObject decoders_ALACDecoderType;

extern const unsigned int read_bits_table[0x900][8];
extern const unsigned int read_unary_table[0x900][2];
extern const unsigned int read_limited_unary_table[0x900][18];
extern const unsigned int unread_bit_table[0x900][2];

PyMODINIT_FUNC
initdecoders(void)
{
    PyObject* m;

    decoders_BitstreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_BitstreamReaderType) < 0)
        return;

    decoders_FlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_FlacDecoderType) < 0)
        return;

    decoders_SHNDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_SHNDecoderType) < 0)
        return;

    decoders_ALACDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_ALACDecoderType) < 0)
        return;

    m = Py_InitModule3("decoders", module_methods,
                       "Low-level audio format decoders");

    Py_INCREF(&decoders_BitstreamReaderType);
    PyModule_AddObject(m, "BitstreamReader",
                       (PyObject *)&decoders_BitstreamReaderType);

    Py_INCREF(&decoders_FlacDecoderType);
    PyModule_AddObject(m, "FlacDecoder",
                       (PyObject *)&decoders_FlacDecoderType);

    Py_INCREF(&decoders_SHNDecoderType);
    PyModule_AddObject(m, "SHNDecoder",
                       (PyObject *)&decoders_SHNDecoderType);

    Py_INCREF(&decoders_ALACDecoderType);
    PyModule_AddObject(m, "ALACDecoder",
                       (PyObject *)&decoders_ALACDecoderType);

}

static PyObject*
BitstreamReader_read(decoders_BitstreamReader *self, PyObject *args) {
    unsigned int count;
    unsigned int result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*bs_try(self->bitstream))) {
        result = self->bitstream->read(self->bitstream, count);
        bs_etry(self->bitstream);
        return Py_BuildValue("I", result);
    } else {
        bs_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_read64(decoders_BitstreamReader *self, PyObject *args) {
    unsigned int count;
    uint64_t result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*bs_try(self->bitstream))) {
        result = self->bitstream->read_64(self->bitstream, count);
        bs_etry(self->bitstream);
        return Py_BuildValue("L", result);
    } else {
        bs_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_byte_align(decoders_BitstreamReader *self, PyObject *args) {
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_unread(decoders_BitstreamReader *self, PyObject *args) {
    int unread_bit;

    if (!PyArg_ParseTuple(args, "i", &unread_bit))
        return NULL;

    if ((unread_bit != 0) && (unread_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "unread bit must be 0 or 1");
        return NULL;
    }

    self->bitstream->unread(self->bitstream, unread_bit);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_read_signed(decoders_BitstreamReader *self, PyObject *args) {
    unsigned int count;
    int result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*bs_try(self->bitstream))) {
        result = self->bitstream->read_signed(self->bitstream, count);
        bs_etry(self->bitstream);
        return Py_BuildValue("i", result);
    } else {
        bs_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_unary(decoders_BitstreamReader *self, PyObject *args) {
    int stop_bit;
    int result;

    if (!PyArg_ParseTuple(args, "i", &stop_bit))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    if (!setjmp(*bs_try(self->bitstream))) {
        result = self->bitstream->read_unary(self->bitstream, stop_bit);
        bs_etry(self->bitstream);
        return Py_BuildValue("I", result);
    } else {
        bs_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_limited_unary(decoders_BitstreamReader *self, PyObject *args) {
    int stop_bit;
    int maximum_bits;
    int result;

    if (!PyArg_ParseTuple(args, "ii", &stop_bit, &maximum_bits))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }
    if (maximum_bits < 1) {
        PyErr_SetString(PyExc_ValueError,
                        "maximum bits must be greater than 0");
        return NULL;
    }

    if (!setjmp(*bs_try(self->bitstream))) {
        result = self->bitstream->read_limited_unary(self->bitstream,
                                                     stop_bit,
                                                     maximum_bits);
        bs_etry(self->bitstream);
        if (result >= 0)
            return Py_BuildValue("i", result);
        else {
            Py_INCREF(Py_None);
            return Py_None;
        }
    } else {
        bs_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }


}

static PyObject*
BitstreamReader_tell(decoders_BitstreamReader *self, PyObject *args) {
    return Py_BuildValue("i", bs_ftell(self->bitstream));
}

static PyObject*
BitstreamReader_close(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject*
BitstreamReader_new(PyTypeObject *type,
                    PyObject *args, PyObject *kwds)
{
    decoders_BitstreamReader *self;

    self = (decoders_BitstreamReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamReader_init(decoders_BitstreamReader *self,
                     PyObject *args)
{
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

    self->bitstream = bs_open(
                    PyFile_AsFile(self->file_obj),
                    little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    return 0;
}

void
BitstreamReader_dealloc(decoders_BitstreamReader *self)
{
    struct bs_callback* callback;
    PyObject* function;

    if (self->file_obj != NULL) {
        for (callback = self->bitstream->callback;
             callback != NULL;
             callback = callback->next) {
            function = (PyObject*)callback->data;
            Py_DECREF(function);
        }

        self->bitstream->file = NULL;
        bs_close(self->bitstream);
        Py_DECREF(self->file_obj);
    }

    self->ob_type->tp_free((PyObject*)self);
}
