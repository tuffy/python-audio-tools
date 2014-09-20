#include <Python.h>
#include <opus/opusfile.h>
#include "../array.h"
#include "../pcmconv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

    OggOpusFile *opus_file;

    int channel_count;
    int closed;
    aa_int *channels;
    PyObject *audiotools_pcm;
} decoders_OpusDecoder;

static PyObject*
OpusDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

int
OpusDecoder_init(decoders_OpusDecoder *self,
                 PyObject *args, PyObject *kwds);

void
OpusDecoders_dealloc(decoders_OpusDecoder *self);

static PyObject*
OpusDecoder_sample_rate(decoders_OpusDecoder *self, void *closure);

static PyObject*
OpusDecoder_bits_per_sample(decoders_OpusDecoder *self, void *closure);

static PyObject*
OpusDecoder_channels(decoders_OpusDecoder *self, void *closure);

static PyObject*
OpusDecoder_channel_mask(decoders_OpusDecoder *self, void *closure);

static PyObject*
OpusDecoder_read(decoders_OpusDecoder* self, PyObject *args);

static PyObject*
OpusDecoder_close(decoders_OpusDecoder* self, PyObject *args);

static PyObject*
OpusDecoder_enter(decoders_OpusDecoder* self, PyObject *args);

static PyObject*
OpusDecoder_exit(decoders_OpusDecoder* self, PyObject *args);

PyGetSetDef OpusDecoder_getseters[] = {
    {"sample_rate",
     (getter)OpusDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)OpusDecoder_bits_per_sample, NULL, "bits-per-sample", NULL},
    {"channels",
     (getter)OpusDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)OpusDecoder_channel_mask, NULL, "channel mask", NULL},
    {NULL}
};

PyMethodDef OpusDecoder_methods[] = {
    {"read", (PyCFunction)OpusDecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"close", (PyCFunction)OpusDecoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)OpusDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)OpusDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_OpusDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.OpusDecoder",   /* tp_name */
    sizeof(decoders_OpusDecoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)OpusDecoders_dealloc, /* tp_dealloc */
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
    "OpusDecoder objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    OpusDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    OpusDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)OpusDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    OpusDecoder_new,           /* tp_new */
};
