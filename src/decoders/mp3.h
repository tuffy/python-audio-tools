#include <Python.h>
#include <stdint.h>
#include <mpg123.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

typedef struct {
    PyObject_HEAD

    mpg123_handle *handle;

    int channels;
    long rate;
    int encoding;
    int closed;

    PyObject *audiotools_pcm;
} decoders_MP3Decoder;

static PyObject*
MP3Decoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds);

int
MP3Decoder_init(decoders_MP3Decoder *self,
                PyObject *args, PyObject *kwds);

void
MP3Decoders_dealloc(decoders_MP3Decoder *self);

static PyObject*
MP3Decoder_sample_rate(decoders_MP3Decoder *self, void *closure);

static PyObject*
MP3Decoder_bits_per_sample(decoders_MP3Decoder *self, void *closure);

static PyObject*
MP3Decoder_channels(decoders_MP3Decoder *self, void *closure);

static PyObject*
MP3Decoder_channel_mask(decoders_MP3Decoder *self, void *closure);

static PyObject*
MP3Decoder_read(decoders_MP3Decoder* self, PyObject *args);

static PyObject*
MP3Decoder_close(decoders_MP3Decoder* self, PyObject *args);

static PyObject*
MP3Decoder_enter(decoders_MP3Decoder* self, PyObject *args);

static PyObject*
MP3Decoder_exit(decoders_MP3Decoder* self, PyObject *args);

PyGetSetDef MP3Decoder_getseters[] = {
    {"sample_rate",
     (getter)MP3Decoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)MP3Decoder_bits_per_sample, NULL, "bits-per-sample", NULL},
    {"channels",
     (getter)MP3Decoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)MP3Decoder_channel_mask, NULL, "channel mask", NULL},
    {NULL}
};

PyMethodDef MP3Decoder_methods[] = {
    {"read", (PyCFunction)MP3Decoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"close", (PyCFunction)MP3Decoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)MP3Decoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)MP3Decoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_MP3DecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.MP3Decoder",   /* tp_name */
    sizeof(decoders_MP3Decoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)MP3Decoders_dealloc, /* tp_dealloc */
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
    Py_TPFLAGS_BASETYPE,       /* tp_flags */
    "MP3Decoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    MP3Decoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    MP3Decoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)MP3Decoder_init, /* tp_init */
    0,                         /* tp_alloc */
    MP3Decoder_new,            /* tp_new */
};
