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

struct flac_STREAMINFO {
    uint16_t minimum_block_size;  /*16  bits*/
    uint16_t maximum_block_size;  /*16  bits*/
    uint32_t minimum_frame_size;  /*24  bits*/
    uint32_t maximum_frame_size;  /*24  bits*/
    uint32_t sample_rate;         /*20  bits*/
    uint8_t channels;             /*3   bits*/
    uint8_t bits_per_sample;      /*5   bits*/
    uint64_t total_samples;       /*36  bits*/
    unsigned char md5sum[16];     /*128 bits*/
};

struct flac_frame_header {
    uint8_t blocking_strategy;
    uint32_t block_size;
    uint32_t sample_rate;
    uint8_t channel_assignment;
    uint8_t channel_count;
    uint8_t bits_per_sample;
    uint64_t frame_number;
};

typedef enum {FLAC_SUBFRAME_CONSTANT,
              FLAC_SUBFRAME_VERBATIM,
              FLAC_SUBFRAME_FIXED,
              FLAC_SUBFRAME_LPC} flac_subframe_type;

struct flac_subframe_header {
    flac_subframe_type type;
    uint8_t order;
    uint8_t wasted_bits_per_sample;
};

typedef enum {OK,ERROR} status;

typedef struct {
    PyObject_HEAD

    char* filename;
    FILE* file;
    Bitstream* bitstream;
    int channel_mask;

    struct flac_STREAMINFO streaminfo;
    uint64_t remaining_samples;

    uint32_t crc8;
    uint32_t crc16;

    /*temporary buffers we don't want to reallocate each time*/
    struct ia_array subframe_data;
    struct i_array residuals;
    struct i_array qlp_coeffs;
} decoders_FlacDecoder;

/*the FlacDecoder.sample_rate attribute getter*/
static PyObject*
FlacDecoder_sample_rate(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.bits_per_sample attribute getter*/
static PyObject*
FlacDecoder_bits_per_sample(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.channels attribute getter*/
static PyObject*
FlacDecoder_channels(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.channel_mask attribute getter*/
static PyObject*
FlacDecoder_channel_mask(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.read() method*/
static PyObject*
FLACDecoder_read(decoders_FlacDecoder* self, PyObject *args);

/*the FlacDecoder.analyze_frame() method*/
static PyObject*
FLACDecoder_analyze_frame(decoders_FlacDecoder* self, PyObject *args);

/*the FlacDecoder.close() method*/
static PyObject*
FLACDecoder_close(decoders_FlacDecoder* self, PyObject *args);

/*the FlacDecoder.__init__() method*/
int
FlacDecoder_init(decoders_FlacDecoder *self,
                 PyObject *args, PyObject *kwds);

PyGetSetDef FlacDecoder_getseters[] = {
    {"sample_rate",
     (getter)FlacDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)FlacDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)FlacDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)FlacDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef FlacDecoder_methods[] = {
    {"read", (PyCFunction)FLACDecoder_read,
     METH_VARARGS,
     "Reads the given number of bytes from the FLAC file, if possible"},
    {"analyze_frame", (PyCFunction)FLACDecoder_analyze_frame,
     METH_NOARGS, "Returns the analysis of the next frame"},
    {"close", (PyCFunction)FLACDecoder_close,
     METH_NOARGS, "Closes the FLAC decoder stream"},
    {NULL}
};

void
FlacDecoder_dealloc(decoders_FlacDecoder *self);

static PyObject*
FlacDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

/*all of the "status" returning functions
  return OK upon success and ERROR upon failure
  if ERROR is returned, a Python exception has been set
  which should bubble up to the original caller (probably FLACDecoder_read)*/

/*reads the STREAMINFO block and skips any other metadata blocks,
  placing our internal stream at the first FLAC frame*/
status
FlacDecoder_read_metadata(decoders_FlacDecoder *self);

/*reads a FLAC frame header from the sync code to the CRC-8
  and places the result in "header"*/
status
FlacDecoder_read_frame_header(decoders_FlacDecoder *self,
                              struct flac_frame_header *header);

/*reads a FLAC subframe header from the padding bit to the wasted bps (if any)
  and places the result in "subframe_header"*/
status
FlacDecoder_read_subframe_header(decoders_FlacDecoder *self,
                                 struct flac_subframe_header *subframe_header);

int
FlacDecoder_subframe_bits_per_sample(struct flac_frame_header *frame_header,
                                     int channel_number);

/*reads a FLAC subframe
  with "block_size" and "bits_per_sample" (determined from the frame header)
  and places the result in "samples"*/
status
FlacDecoder_read_subframe(decoders_FlacDecoder *self,
                          uint32_t block_size,
                          uint8_t bits_per_sample,
                          struct i_array *samples);

/*the following four functions are called by FlacDecoder_read_subframe
  depending on the subframe type in the subframe header
  all take the same arguments as FlacDecoder_read_subframe
  and, for fixed and lpc, an "order" argument - also from the subframe header*/
status
FlacDecoder_read_constant_subframe(decoders_FlacDecoder *self,
                                   uint32_t block_size,
                                   uint8_t bits_per_sample,
                                   struct i_array *samples);

status
FlacDecoder_read_verbatim_subframe(decoders_FlacDecoder *self,
                                   uint32_t block_size,
                                   uint8_t bits_per_sample,
                                   struct i_array *samples);

status
FlacDecoder_read_fixed_subframe(decoders_FlacDecoder *self,
                                uint8_t order,
                                uint32_t block_size,
                                uint8_t bits_per_sample,
                                struct i_array *samples);

status
FlacDecoder_read_lpc_subframe(decoders_FlacDecoder *self,
                              uint8_t order,
                              uint32_t block_size,
                              uint8_t bits_per_sample,
                              struct i_array *samples);

/*reads a chunk of residuals with the given "order" and "block_size"
  (determined from read_fixed_subframe or read_lpc_subframe)
  and places the result in "residuals"*/
status
FlacDecoder_read_residual(decoders_FlacDecoder *self,
                          uint8_t order,
                          uint32_t block_size,
                          struct i_array *residuals);


void
FlacDecoder_decorrelate_channels(struct flac_frame_header *frame_header,
                                 struct ia_array *subframe_data);

PyObject*
FlacDecoder_analyze_subframe(decoders_FlacDecoder *self,
                             uint32_t block_size,
                             uint8_t bits_per_sample);

PyObject*
FlacDecoder_analyze_constant_subframe(decoders_FlacDecoder *self,
                                      uint32_t block_size,
                                      uint8_t bits_per_sample);

PyObject*
FlacDecoder_analyze_verbatim_subframe(decoders_FlacDecoder *self,
                                      uint32_t block_size,
                                      uint8_t bits_per_sample);

PyObject*
FlacDecoder_analyze_fixed_subframe(decoders_FlacDecoder *self,
                                   uint8_t order,
                                   uint32_t block_size,
                                   uint8_t bits_per_sample);

PyObject*
FlacDecoder_analyze_lpc_subframe(decoders_FlacDecoder *self,
                                 uint8_t order,
                                 uint32_t block_size,
                                 uint8_t bits_per_sample);

PyObject*
FlacDecoder_analyze_residual(decoders_FlacDecoder *self,
                             uint8_t order,
                             uint32_t block_size);


#include "flac_crc.h"

uint32_t read_utf8(Bitstream *stream);

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
