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

struct tta_header {
    unsigned channels;
    unsigned bits_per_sample;
    unsigned sample_rate;
    unsigned total_pcm_frames;
};

#ifndef STANDALONE
typedef struct {
    PyObject_HEAD

    struct tta_header header;

    unsigned default_block_size;
    unsigned total_tta_frames;
    unsigned current_tta_frame;
    unsigned* seektable;

    int closed;

    BitstreamReader* bitstream;

    /*a framelist generator*/
    PyObject* audiotools_pcm;

    /*position of start of frames*/
    br_pos_t* frames_start;
} decoders_TTADecoder;

static PyObject*
TTADecoder_sample_rate(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_bits_per_sample(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_channels(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_channel_mask(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_read(decoders_TTADecoder *self, PyObject *args);

static PyObject*
TTADecoder_seek(decoders_TTADecoder *self, PyObject *args);

static PyObject*
TTADecoder_close(decoders_TTADecoder *self, PyObject *args);

static PyObject*
TTADecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
TTADecoder_dealloc(decoders_TTADecoder *self);

static PyObject*
TTADecoder_enter(decoders_TTADecoder* self, PyObject *args);

static PyObject*
TTADecoder_exit(decoders_TTADecoder* self, PyObject *args);

int
TTADecoder_init(decoders_TTADecoder *self, PyObject *args, PyObject *kwds);

PyGetSetDef TTADecoder_getseters[] = {
    {"sample_rate",
     (getter)TTADecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)TTADecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)TTADecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)TTADecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef TTADecoder_methods[] = {
    {"read", (PyCFunction)TTADecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"seek", (PyCFunction)TTADecoder_seek,
     METH_VARARGS, "seek(desired_pcm_offset) -> actual_pcm_offset"},
    {"close", (PyCFunction)TTADecoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)TTADecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)TTADecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_TTADecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.TTADecoder",     /*tp_name*/
    sizeof(decoders_TTADecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)TTADecoder_dealloc, /*tp_dealloc*/
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
    "TTADecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    TTADecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    TTADecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)TTADecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    TTADecoder_new,            /* tp_new */
  };
#endif
