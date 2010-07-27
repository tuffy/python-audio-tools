#include <Python.h>
#include "decoders.h"
#include "bitstream_r.h"

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
