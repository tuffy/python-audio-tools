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

  if (!SHNDecoder_read_header(self)) {
    PyErr_SetString(PyExc_ValueError,"not a SHN file");
    return -1;
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

static PyObject *SHNDecoder_version(decoders_SHNDecoder *self,
				    void *closure) {
  return Py_BuildValue("i",self->version);
}

static PyObject *SHNDecoder_file_type(decoders_SHNDecoder *self,
				      void *closure) {
  return Py_BuildValue("i",self->file_type);
}

static PyObject *SHNDecoder_channels(decoders_SHNDecoder *self,
				     void *closure) {
  return Py_BuildValue("i",self->channels);
}

static PyObject *SHNDecoder_block_size(decoders_SHNDecoder *self,
				       void *closure) {
  return Py_BuildValue("i",self->block_size);
}


PyObject *SHNDecoder_read(decoders_SHNDecoder* self,
			  PyObject *args) {
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *SHNDecoder_verbatim(decoders_SHNDecoder* self,
			      PyObject *args) {
  unsigned int cmd;

  /*rewind the stream and re-read the header*/
  fseek(self->bitstream->file,0,SEEK_SET);
  self->bitstream->state = 0;

  SHNDecoder_read_header(self);

  /*walk through the Shorten file,
    storing FN_VERBATIM instructions as strings*/

  cmd = shn_read_uvar(self->bitstream,2);

  printf("%u\n",cmd);

  Py_INCREF(Py_None);
  return Py_None;
}

int SHNDecoder_read_header(decoders_SHNDecoder* self) {
  Bitstream* bs = self->bitstream;

  if (read_bits(bs, 32) != 0x616A6B67)
    return 0;

  self->version = read_bits(bs,8);
  self->file_type = shn_read_long(bs);
  self->channels = shn_read_long(bs);
  self->block_size = shn_read_long(bs);
  self->maxnlpc = shn_read_long(bs);
  self->nmean = shn_read_long(bs);
  self->nskip = shn_read_long(bs);
  /*FIXME - perform writing if bytes skipped*/
  self->wrap = self->maxnlpc > 3 ? self->maxnlpc : 3;

  return 1;
}

unsigned int shn_read_uvar(Bitstream* bs, unsigned int count) {
  unsigned int high_bits = read_unary(bs,1);
  unsigned int low_bits = read_bits(bs,count);

  return (high_bits << count) | low_bits;
}

unsigned int shn_read_long(Bitstream* bs) {
  return shn_read_uvar(bs,shn_read_uvar(bs,2));
}
