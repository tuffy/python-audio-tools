#include <Python.h>

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

static PyObject* read_bits(PyObject* self, PyObject* args);
static PyObject* read_unary(PyObject* self, PyObject* args);

static PyMethodDef BitStreamMethods[] = {
    {"read_bits",  read_bits, METH_VARARGS,
     "Read bits from context and return bits, count and new context."},
    {"read_unary", read_unary, METH_VARARGS,
     "Read a unary value from context and return bits, count and new context."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC initbitstream(void) {
    (void) Py_InitModule("bitstream", BitStreamMethods);
}


static PyObject* read_bits(PyObject* self, PyObject* args) {
  int context;
  int total_bits;
  static unsigned int jumptable[0x900][8] =
#include "read_bits_table.c"
    ;

  if (!PyArg_ParseTuple(args, "ii", &context,&total_bits))
    return NULL;

  /*DANGER! - If context or total_bits are outside the array
    this will bomb horribly.  This function should only be called
    by high-level routines that know what they're doing.*/

  /*the context's low 8 bits are parts of a byte that have not been read
    its remaining high bits are the amount of bits in the byte not read

    the jumptable's result is an int encoded with 3 separate values
    its low 12 bits are the new context
    the next 8 bits are the returned value
    the high 8 bits are the amount of bits in the returned value*/
  return Py_BuildValue("i",jumptable[context][total_bits - 1]);
}

static PyObject* read_unary(PyObject* self, PyObject* args) {
  int context;
  int stop_bit;
  static unsigned int jumptable[0x900][2] =
#include "read_unary_table.c"
    ;

  if (!PyArg_ParseTuple(args, "ii", &context,&stop_bit))
    return NULL;

  /*DANGER! - If context or stop_bit are outside the array
    this will bomb horribly.  This function should only be called
    by high-level routines that know what they're doing.*/

  /*the context is the same as read_bits and the two are interchangeable

    the jumptable's result is an int encoded with 3 separate values
    the low 12 bits are the new context
    the middle 8 bits are the returned value
    the highest bit indicates whether we need to continune reading*/
  return Py_BuildValue("i",jumptable[context][stop_bit]);
}
