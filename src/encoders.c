#include <Python.h>
#include "encoders.h"

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

PyMODINIT_FUNC initencoders(void) {
  PyObject* m;

  m = Py_InitModule3("encoders", module_methods,
		     "Low-level audio format encoders");

}

PyObject *encoders_write_bits(PyObject *dummy, PyObject *args) {
  int context;
  int value;

  if (!PyArg_ParseTuple(args,"ii",&context,&value))
    return NULL;

  return Py_BuildValue("i",write_bits_table[context][value]);
}


PyObject *encoders_write_unary(PyObject *dummy, PyObject *args) {
  int context;
  int value;

  if (!PyArg_ParseTuple(args,"ii",&context,&value))
    return NULL;

  return Py_BuildValue("i",write_unary_table[context][value]);
}

int parse_pcmreader(PyObject *pcmreader,
		    PyObject **read,
		    PyObject **close,
		    long *sample_rate,
		    long *channels,
		    long *bits_per_sample) {
  PyObject *attr;

  if ((attr = PyObject_GetAttrString(pcmreader,"sample_rate")) == NULL)
    return 0;
  *sample_rate = PyInt_AsLong(attr);
  Py_DECREF(attr);
  if ((*sample_rate == -1) && (PyErr_Occurred()))
    return 0;

  if ((attr = PyObject_GetAttrString(pcmreader,"bits_per_sample")) == NULL)
    return 0;
  *bits_per_sample = PyInt_AsLong(attr);
  Py_DECREF(attr);
  if ((*bits_per_sample == -1) && (PyErr_Occurred()))
    return 0;

  if ((attr = PyObject_GetAttrString(pcmreader,"channels")) == NULL)
    return 0;
  *channels = PyInt_AsLong(attr);
  Py_DECREF(attr);
  if ((*channels == -1) && (PyErr_Occurred()))
    return 0;

  if ((*read = PyObject_GetAttrString(pcmreader,"read")) == NULL)
    return 0;
  if (!PyCallable_Check(*read)) {
    Py_DECREF(*read);
    PyErr_SetString(PyExc_TypeError,"read parameter must be callable");
    return 0;
  }
  if ((*close = PyObject_GetAttrString(pcmreader,"close")) == NULL)
    return 0;
  if (!PyCallable_Check(*close)) {
    Py_DECREF(*read);
    Py_DECREF(*close);
    PyErr_SetString(PyExc_TypeError,"close parameter must be callable");
    return 0;
  }

  return 1;
}

#include "encoders/flac.c"

#include "bitstream.c"
