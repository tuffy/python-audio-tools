#include "shn.h"
#include "../pcm.h"

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

int SHNDecoder_init(decoders_SHNDecoder *self,
		    PyObject *args, PyObject *kwds) {
  char* filename;
  FILE* fp;

  if (!PyArg_ParseTuple(args, "s", &filename))
    return -1;

  /*open the shn file*/
  if ((fp = fopen(filename,"rb")) == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return -1;
  } else {
    self->bitstream = bs_open(fp);
  }

  self->filename = strdup(filename);

  return 0;
}

PyObject *SHNDecoder_close(decoders_SHNDecoder* self,
			   PyObject *args) {
  Py_INCREF(Py_None);
  return Py_None;
}

void SHNDecoder_dealloc(decoders_SHNDecoder *self) {
  if (self->filename != NULL)
    free(self->filename);

  bs_close(self->bitstream);

  self->ob_type->tp_free((PyObject*)self);
}


PyObject *SHNDecoder_new(PyTypeObject *type,
			 PyObject *args, PyObject *kwds) {
  decoders_SHNDecoder *self;

  self = (decoders_SHNDecoder *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

PyObject *SHNDecoder_read(decoders_SHNDecoder* self,
			  PyObject *args) {
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *SHNDecoder_verbatim(decoders_SHNDecoder* self,
			      PyObject *args) {
  Py_INCREF(Py_None);
  return Py_None;
}
