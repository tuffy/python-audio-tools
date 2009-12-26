#include <Python.h>
#include "decoders.h"
#include "bitstream_r.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2009  Brian Langenberger

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

PyMODINIT_FUNC initdecoders(void) {
    PyObject* m;

    decoders_FlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_FlacDecoderType) < 0)
      return;

    m = Py_InitModule3("decoders", module_methods,
                       "Low-level audio format decoders");

    Py_INCREF(&decoders_FlacDecoderType);
    PyModule_AddObject(m, "FlacDecoder",
		       (PyObject *)&decoders_FlacDecoderType);
}

PyObject *decoders_read_bits(PyObject *dummy, PyObject *args) {
  int context;
  int bits;

  if (!PyArg_ParseTuple(args,"ii",&context,&bits))
    return NULL;

  return Py_BuildValue("i",read_bits_table[context][bits - 1]);
}

PyObject *decoders_read_unary(PyObject *dummy, PyObject *args) {
  int context;
  int stop_bit;

  if (!PyArg_ParseTuple(args, "ii", &context,&stop_bit))
    return NULL;

  return Py_BuildValue("i",read_unary_table[context][stop_bit]);
}
