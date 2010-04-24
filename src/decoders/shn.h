#include <Python.h>
#include <stdint.h>
#include "../bitstream_r.h"
#include "../array.h"

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

#define ENERGY_SIZE 3
#define VERBATIM_CHUNK_SIZE 5
#define VERBATIM_BYTE_SIZE 8
enum {FN_DIFF0     = 0,
      FN_DIFF1     = 1,
      FN_DIFF2     = 2,
      FN_DIFF3     = 3,
      FN_QUIT      = 4,
      FN_BLOCKSIZE = 5,
      FN_ZERO      = 8,
      FN_VERBATIM  = 9};

typedef struct {
  PyObject_HEAD

  char* filename;
  Bitstream* bitstream;

  unsigned int version;
  unsigned int file_type;
  unsigned int channels;
  unsigned int block_size;
  unsigned int maxnlpc;
  unsigned int nmean;
  unsigned int nskip;
  unsigned int wrap;

  int read_started;
  int read_finished;
} decoders_SHNDecoder;

/*the SHNDecoder.read() method*/
PyObject *SHNDecoder_read(decoders_SHNDecoder* self,
			  PyObject *args);

/*the SHNDecoder.verbatim() method*/
PyObject *SHNDecoder_verbatim(decoders_SHNDecoder* self,
			      PyObject *args);

/*the SHNDecoder.close() method*/
PyObject *SHNDecoder_close(decoders_SHNDecoder* self,
			    PyObject *args);

/*the SHNDecoder.__init__() method*/
int SHNDecoder_init(decoders_SHNDecoder *self,
		    PyObject *args, PyObject *kwds);


/*the SHNDecoder.version attribute getter*/
static PyObject *SHNDecoder_version(decoders_SHNDecoder *self,
				    void *closure);

/*the SHNDecoder.file_type attribute getter*/
static PyObject *SHNDecoder_file_type(decoders_SHNDecoder *self,
				      void *closure);

/*the SHNDecoder.channels attribute getter*/
static PyObject *SHNDecoder_channels(decoders_SHNDecoder *self,
				     void *closure);

/*the SHNDecoder.block_size attribute getter*/
static PyObject *SHNDecoder_block_size(decoders_SHNDecoder *self,
				       void *closure);

PyGetSetDef SHNDecoder_getseters[] = {
  {"version",
   (getter)SHNDecoder_version, NULL, "version", NULL},
  {"file_type",
   (getter)SHNDecoder_file_type, NULL, "file_type", NULL},
  {"channels",
   (getter)SHNDecoder_channels, NULL, "channels", NULL},
  {"block_size",
   (getter)SHNDecoder_block_size, NULL, "block_size", NULL},
  {NULL}
};

PyMethodDef SHNDecoder_methods[] = {
  {"read", (PyCFunction)SHNDecoder_read,
   METH_VARARGS,"Reads a frame of data from the SHN file"},
  {"verbatim", (PyCFunction)SHNDecoder_verbatim,
   METH_NOARGS,"Returns a list of verbatim chunks from the SHN file"},
  {"close", (PyCFunction)SHNDecoder_close,
   METH_NOARGS,"Closes the SHN decoder stream"},
  {NULL}
};

void SHNDecoder_dealloc(decoders_SHNDecoder *self);

PyObject *SHNDecoder_new(PyTypeObject *type,
			 PyObject *args, PyObject *kwds);


PyTypeObject decoders_SHNDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.SHNDecoder",    /*tp_name*/
    sizeof(decoders_SHNDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)SHNDecoder_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "SHNDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    SHNDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    SHNDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)SHNDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    SHNDecoder_new,           /* tp_new */
};

int SHNDecoder_read_header(decoders_SHNDecoder* self);

unsigned int shn_read_uvar(Bitstream* bs, unsigned int count);

int shn_read_var(Bitstream* bs, unsigned int count);

unsigned int shn_read_long(Bitstream* bs);
