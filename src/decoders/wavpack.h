#ifndef STANDALONE
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#endif
#include <stdint.h>
#include <wavpack/wavpack.h>
#include "../common/md5.h"

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

    PyObject* audiotools_pcm;

    WavpackContext* context;

    audiotools__MD5Context md5;
    int verifying_md5_sum;

    int closed;

} decoders_WavPackDecoder;

int
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    PyObject *args, PyObject *kwds);

static PyObject*
WavPackDecoder_sample_rate(decoders_WavPackDecoder *self, void *closure);

static PyObject*
WavPackDecoder_bits_per_sample(decoders_WavPackDecoder *self, void *closure);

static PyObject*
WavPackDecoder_channels(decoders_WavPackDecoder *self, void *closure);

static PyObject*
WavPackDecoder_channel_mask(decoders_WavPackDecoder *self, void *closure);

PyGetSetDef WavPackDecoder_getseters[] = {
    {"sample_rate",
     (getter)WavPackDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)WavPackDecoder_bits_per_sample, NULL, "bits-per-sample", NULL},
    {"channels",
     (getter)WavPackDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)WavPackDecoder_channel_mask, NULL, "channel mask", NULL},
    {NULL}
};

static PyObject*
WavPackDecoder_close(decoders_WavPackDecoder* self, PyObject *args);

PyObject*
WavPackDecoder_read(decoders_WavPackDecoder* self, PyObject *args);

PyObject*
WavPackDecoder_seek(decoders_WavPackDecoder* self, PyObject *args);

static PyObject*
WavPackDecoder_enter(decoders_WavPackDecoder* self, PyObject *args);

static PyObject*
WavPackDecoder_exit(decoders_WavPackDecoder* self, PyObject *args);

PyMethodDef WavPackDecoder_methods[] = {
    {"read", (PyCFunction)WavPackDecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"seek", (PyCFunction)WavPackDecoder_seek,
     METH_VARARGS, "seek(desired_pcm_offset) -> actual_pcm_offset"},
    {"close", (PyCFunction)WavPackDecoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)WavPackDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)WavPackDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self);

static PyObject*
WavPackDecoder_new(PyTypeObject *type,
                   PyObject *args, PyObject *kwds);

PyTypeObject decoders_WavPackDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.WavPackDecoder", /*tp_name*/
    sizeof(decoders_WavPackDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)WavPackDecoder_dealloc, /*tp_dealloc*/
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
    "WavPackDecoder objects",  /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    WavPackDecoder_methods,    /* tp_methods */
    0,                         /* tp_members */
    WavPackDecoder_getseters,  /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)WavPackDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    WavPackDecoder_new,        /* tp_new */
};
