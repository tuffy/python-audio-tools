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

int read_samples(PyObject *read,
		 long total_samples,
		 long bits_per_sample,
		 struct ia_array *samples) {
  uint32_t i;
  PyObject *args;
  PyObject *result;

  unsigned char *buffer;
  Py_ssize_t buffer_length;

  args = Py_BuildValue("(l)",
		       total_samples * bits_per_sample * samples->size / 8);
  result = PyEval_CallObject(read,args);
  Py_DECREF(args);
  if (result == NULL)
    return 0;
  if (PyString_AsStringAndSize(result,(char **)(&buffer),&buffer_length) == -1){
    Py_DECREF(result);
    return 0;
  }

  for (i = 0; i < samples->size; i++) {
    ia_reset(iaa_getitem(samples,i));
    switch (bits_per_sample) {
    case 8:
      ia_char_to_U8(iaa_getitem(samples,i),
		    buffer,(int)buffer_length,i,samples->size);
      break;
    case 16:
      ia_char_to_SL16(iaa_getitem(samples,i),
		      buffer,(int)buffer_length,i,samples->size);
      break;
    case 24:
      ia_char_to_SL24(iaa_getitem(samples,i),
		      buffer,(int)buffer_length,i,samples->size);
      break;
    default:
      PyErr_SetString(PyExc_ValueError,"unsupported bits per sample");
      Py_DECREF(result);
      return 0;
    }
  }

  Py_DECREF(result);
  return 1;
}

#include "encoders/flac.c"

#include "bitstream.c"
#include "array.c"

