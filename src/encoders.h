#include <Python.h>
#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

PyObject *encoders_write_bits(PyObject *dummy, PyObject *args);
PyObject *encoders_write_unary(PyObject *dummy, PyObject *args);
PyObject *encoders_encode_flac(PyObject *dummy,
			       PyObject *args, PyObject *keywds);

PyMethodDef module_methods[] = {
  {"write_bits",(PyCFunction)encoders_write_bits,
   METH_VARARGS,""},
  {"write_unary",(PyCFunction)encoders_write_unary,
   METH_VARARGS,""},
  {"encode_flac",(PyCFunction)encoders_encode_flac,
   METH_VARARGS | METH_KEYWORDS,"Encode FLAC file from PCMReader"},
  {NULL}
};
