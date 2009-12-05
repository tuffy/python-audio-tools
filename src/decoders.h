#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

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

#include "bitstream.h"

PyMethodDef module_methods[] = {
  {NULL}
};

struct flac_STREAMINFO {
  uint16_t minimum_block_size;
  uint16_t maximum_block_size;
  uint32_t minimum_frame_size;
  uint32_t maximum_frame_size;
  uint32_t sample_rate;
  uint8_t channels;
  uint8_t bits_per_sample;
  uint64_t total_samples;
  unsigned char md5sum[16];
};

typedef struct {
  PyObject_HEAD
  char* filename;

  FILE* file;
  Bitstream* bitstream;

  struct flac_STREAMINFO streaminfo;
} decoders_FlacDecoder;

static PyObject *FlacDecoder_sample_rate(decoders_FlacDecoder *self,
					 void *closure);
static PyObject *FlacDecoder_bits_per_sample(decoders_FlacDecoder *self,
					     void *closure);

static PyObject *FlacDecoder_channels(decoders_FlacDecoder *self,
				      void *closure);

int FlacDecoder_init(decoders_FlacDecoder *self,
		     PyObject *args, PyObject *kwds);

PyGetSetDef FlacDecoder_getseters[] = {
  {"sample_rate",
   (getter)FlacDecoder_sample_rate, NULL, "sample rate", NULL},
  {"bits_per_sample",
   (getter)FlacDecoder_bits_per_sample, NULL, "bits per sample", NULL},
  {"channels",
   (getter)FlacDecoder_channels, NULL, "channels", NULL},
  {NULL}
};

PyMethodDef FlacDecoder_methods[] = {
  {NULL}
};

void FlacDecoder_dealloc(decoders_FlacDecoder *self);

PyObject *FlacDecoder_new(PyTypeObject *type,
			  PyObject *args, PyObject *kwds);

int FlacDecoder_read_metadata(decoders_FlacDecoder *self);

#ifdef IS_PY3K

static PyTypeObject decoders_FlacDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.FlacDecoder",     /* tp_name */
    sizeof(decoders_FlacDecoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)FlacDecoders_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
        Py_TPFLAGS_BASETYPE,   /* tp_flags */
    "FlacDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    FlacDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    FlacDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FlacDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    FlacDecoder_new,       /* tp_new */
};

#else

PyTypeObject decoders_FlacDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.FlacDecoder",    /*tp_name*/
    sizeof(decoders_FlacDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FlacDecoder_dealloc, /*tp_dealloc*/
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
    "FlacDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    FlacDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    FlacDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FlacDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    FlacDecoder_new,           /* tp_new */
};

#endif

