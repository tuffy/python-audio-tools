#include "alac.h"

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

PyObject* encoders_encode_alac(PyObject *dummy,
			       PyObject *args, PyObject *keywds) {

  static char *kwlist[] = {"file",
			   "pcmreader",
			   "block_size",
			   NULL};

  PyObject *file_obj;
  PyObject *fileno_obj;
  int output_fd;
  Bitstream *stream = NULL;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;

  int block_size;

  /*extract a file object, PCMReader-compatible object and encoding options*/
  if (!PyArg_ParseTupleAndKeywords(args,keywds,"OOi",
				   kwlist,
				   &file_obj,
				   &pcmreader_obj,
				   &block_size))
    return NULL;

  /*check for negative block_size*/
  if (block_size <= 0) {
    PyErr_SetString(PyExc_ValueError,"block_size must be positive");
    return NULL;
  }

  /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
  if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
    return NULL;
  }

  /*determine if the PCMReader is compatible with ALAC*/
  if ((reader->bits_per_sample != 16) &&
      (reader->bits_per_sample != 24)) {
    PyErr_SetString(PyExc_ValueError,"bits per sample must be 16 or 24");
    goto error;
  }
  if (reader->channels > 2) {
    PyErr_SetString(PyExc_ValueError,"channels must be 1 or 2");
    goto error;
  }

  /*convert file object with .fileno() method to bitstream writer*/
  if ((fileno_obj = PyObject_CallMethod(file_obj,"fileno",NULL)) == NULL) {
    goto error;
  } else {
    if (((output_fd = PyInt_AsLong(fileno_obj)) == -1) && PyErr_Occurred()) {
      Py_DECREF(fileno_obj);
      goto error;
    } else
      Py_DECREF(fileno_obj);
  }

  /*write frames from pcm_reader until empty*/

  /*close and free allocated files/buffers*/

  /*return the accumulated log of output*/

  Py_INCREF(Py_None);
  return Py_None;

 error:
  pcmr_close(reader);
  bs_close(stream);
  return NULL;
}
