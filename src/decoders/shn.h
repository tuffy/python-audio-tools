#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

struct shn_header {
    unsigned file_type;
    unsigned channels;
    unsigned block_size;
    unsigned max_LPC;
    unsigned mean_count;
};

typedef struct {
    PyObject_HEAD

    int sample_rate;
    int channel_mask;

    BitstreamReader* bitstream;

    /*fixed fields from the Shorten header*/
    struct shn_header header;

    /*derives from header's file type*/
    unsigned bits_per_sample;

    /*fields which may change during decoding*/
    unsigned left_shift;

    /*an array of channel arrays, one per channel, each 3 entries long
      contains the wrapped samples from the previous Shorten "frame"*/
    int **wrapped_samples;

    /*a framelist generator*/
    PyObject* audiotools_pcm;

    /*a marker to indicate the stream has been explicitly closed*/
    int closed;

    /*a marker to indicate the end of the stream was reached*/
    int quitted;
} decoders_SHNDecoder;

PyObject*
SHNDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
SHNDecoder_init(decoders_SHNDecoder *self, PyObject *args, PyObject *kwds);

void SHNDecoder_dealloc(decoders_SHNDecoder *self);

static PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args);

static PyObject*
SHNDecoder_sample_rate(decoders_SHNDecoder *self, void *closure);

static PyObject*
SHNDecoder_bits_per_sample(decoders_SHNDecoder *self, void *closure);

static PyObject*
SHNDecoder_channels(decoders_SHNDecoder *self, void *closure);

static PyObject*
SHNDecoder_channel_mask(decoders_SHNDecoder *self, void *closure);

static PyObject*
SHNDecoder_read(decoders_SHNDecoder* self, PyObject *args);

static PyObject*
SHNDecoder_verbatims(decoders_SHNDecoder* self, PyObject *args);

static PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args);

static PyObject*
SHNDecoder_enter(decoders_SHNDecoder* self, PyObject *args);

static PyObject*
SHNDecoder_exit(decoders_SHNDecoder* self, PyObject *args);

PyGetSetDef SHNDecoder_getseters[] = {
    {"channels",
     (getter)SHNDecoder_channels, NULL, "channels", NULL},
    {"bits_per_sample",
     (getter)SHNDecoder_bits_per_sample, NULL, "bits-per-sample", NULL},
    {"sample_rate",
     (getter)SHNDecoder_sample_rate, NULL, "sample rate", NULL},
    {"channel_mask",
     (getter)SHNDecoder_channel_mask, NULL, "channel mask", NULL},
    {NULL}
};

PyMethodDef SHNDecoder_methods[] = {
    {"read", (PyCFunction)SHNDecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"close", (PyCFunction)SHNDecoder_close,
     METH_NOARGS, "close() -> None"},
    {"verbatims", (PyCFunction)SHNDecoder_verbatims,
     METH_NOARGS, "verbatims() -> [bytes, bytes, ...]"},
    {"__enter__", (PyCFunction)SHNDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)SHNDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_SHNDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.SHNDecoder",     /*tp_name*/
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
    "SHNDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    SHNDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    SHNDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)SHNDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    SHNDecoder_new,            /* tp_new */
};
