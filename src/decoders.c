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

PyObject*
decoders_read_bits(PyObject *dummy, PyObject *args)
{
    int context;
    int bits;

    if (!PyArg_ParseTuple(args, "ii", &context, &bits))
        return NULL;

    return Py_BuildValue("i", read_bits_table[context][bits - 1]);
}

PyObject*
decoders_unread_bit(PyObject *dummy, PyObject *args)
{
    int context;
    int bit;

    if (!PyArg_ParseTuple(args, "ii", &context, &bit))
        return NULL;

    context = unread_bit_table[context][bit];
    if (context >> 12) {
        PyErr_SetString(PyExc_ValueError, "unable to unread bit");
        return NULL;
    } else {
        return Py_BuildValue("i", context);
    }
}

PyObject*
decoders_read_unary(PyObject *dummy, PyObject *args)
{
    int context;
    int stop_bit;

    if (!PyArg_ParseTuple(args, "ii", &context, &stop_bit))
        return NULL;

    return Py_BuildValue("i", read_unary_table[context][stop_bit]);
}

PyObject*
decoders_read_limited_unary(PyObject *dummy, PyObject *args)
{
    int context;
    int stop_bit;
    int maximum_bits;

    if (!PyArg_ParseTuple(args, "iii", &context, &stop_bit, &maximum_bits))
        return NULL;

    stop_bit *= 9;

    return Py_BuildValue("i",
                         read_limited_unary_table[context][stop_bit +
                                                           maximum_bits]);
}

static PyObject*
BitstreamReader_read(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_byte_align(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_unread(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_read_signed(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_unary(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_limited_unary(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_tell(decoders_BitstreamReader *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
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
    self->file_obj = NULL;

    if (!PyArg_ParseTuple(args, "O", &file_obj))
        return -1;

    if (!PyFile_CheckExact(file_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be an actual file object");
        return -1;
    }

    Py_INCREF(file_obj);
    self->file_obj = file_obj;
    /*FIXME - make this selectable in init*/
    self->bitstream = bs_open(PyFile_AsFile(self->file_obj),
                              BS_BIG_ENDIAN);

    return 0;
}

void
BitstreamReader_dealloc(decoders_BitstreamReader *self)
{
    if (self->file_obj != NULL) {
        self->bitstream->file = NULL;
        bs_close(self->bitstream);
        Py_DECREF(self->file_obj);
    }

    self->ob_type->tp_free((PyObject*)self);
}

