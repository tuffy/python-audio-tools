#include "shn.h"
#include "../pcmreader.h"

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

PyObject* encoders_encode_shn(PyObject *dummy,
			      PyObject *args, PyObject *keywds) {

  static char *kwlist[] = {"filename",
			   "pcmreader",
			   "block_size",
			   "verbatim_chunks",
			   NULL};
  char *filename;
  FILE *file;
  Bitstream *stream;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;
  int block_size;
  PyObject *verbatim_chunks;

  /*extract a filename, PCMReader-compatible object and encoding options*/
  if (!PyArg_ParseTupleAndKeywords(args,keywds,"sOiO",
				   kwlist,
				   &filename,
				   &pcmreader_obj,
				   &block_size,
				   &verbatim_chunks))
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

  /*determine if the PCMReader is compatible with Shorten*/
  if ((reader->bits_per_sample != 8) && (reader->bits_per_sample != 16)) {
    PyErr_SetString(PyExc_ValueError,"bits_per_sample must be 8 or 16");
    return NULL;
  }

  /*open the given filename for writing*/
  if ((file = fopen(filename,"wb")) == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return NULL;
  } else {
    stream = bs_open(file);
  }

  stream->write_bits(stream,32,0x616A6B67); /*the magic number 'ajkg'*/
  stream->write_bits(stream,8,2);           /*the version number 2*/


  pcmr_close(reader);
  bs_close(stream);
  Py_INCREF(Py_None);
  return Py_None;
}
