#include <Python.h>
#include <stdint.h>
#include "../array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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

    int total_pcm_frames;
    int remaining_pcm_frames;
    int bits_per_sample;
    int sample_rate;
    int full_scale;
    double a1;
    double a2;
    double delta1;
    double delta2;
    double theta1;
    double theta2;

    array_ia* buffer;
    PyObject* audiotools_pcm;
} decoders_Sine_Mono;

int
Sine_Mono_init(decoders_Sine_Mono* self, PyObject *args, PyObject *kwds);

void Sine_Mono_dealloc(decoders_Sine_Mono* self);

PyObject*
Sine_Mono_new(PyTypeObject *type, PyObject *args, PyObject *kwds);


static PyObject*
Sine_Mono_read(decoders_Sine_Mono* self, PyObject* args);

static PyObject*
Sine_Mono_close(decoders_Sine_Mono* self, PyObject* args);

static PyObject*
Sine_Mono_reset(decoders_Sine_Mono* self, PyObject* args);

static PyObject*
Sine_Mono_channels(decoders_Sine_Mono *self, void *closure);

static PyObject*
Sine_Mono_bits_per_sample(decoders_Sine_Mono *self, void *closure);

static PyObject*
Sine_Mono_sample_rate(decoders_Sine_Mono *self, void *closure);

static PyObject*
Sine_Mono_channel_mask(decoders_Sine_Mono *self, void *closure);

PyMethodDef Sine_Mono_methods[] = {
    {"read", (PyCFunction)Sine_Mono_read,
     METH_VARARGS, "Reads a frame of sine data"},
    {"close", (PyCFunction)Sine_Mono_close,
     METH_NOARGS, "Closes the stream"},
    {"reset", (PyCFunction)Sine_Mono_reset,
     METH_NOARGS, "Resets the stream to be read again"},
    {NULL}
};

PyGetSetDef Sine_Mono_getseters[] = {
    {"channels",
     (getter)Sine_Mono_channels, NULL, "channels", NULL},
    {"bits_per_sample",
     (getter)Sine_Mono_bits_per_sample, NULL, "bits_per_sample", NULL},
    {"sample_rate",
     (getter)Sine_Mono_sample_rate, NULL, "sample_rate", NULL},
    {"channel_mask",
     (getter)Sine_Mono_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyTypeObject decoders_Sine_Mono_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.Sine_Mono",      /*tp_name*/
    sizeof(decoders_Sine_Mono),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Sine_Mono_dealloc, /*tp_dealloc*/
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
    "Sine_Mono objects",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Sine_Mono_methods,         /* tp_methods */
    0,                         /* tp_members */
    Sine_Mono_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Sine_Mono_init,  /* tp_init */
    0,                         /* tp_alloc */
    Sine_Mono_new,             /* tp_new */
};


typedef struct {
    PyObject_HEAD

    int total_pcm_frames;
    int remaining_pcm_frames;
    int bits_per_sample;
    int sample_rate;
    int full_scale;
    double a1;
    double a2;
    double delta1;
    double delta2;
    double theta1;
    double theta2;
    double fmult;

    array_ia* buffer;
    PyObject* audiotools_pcm;
} decoders_Sine_Stereo;

int
Sine_Stereo_init(decoders_Sine_Stereo* self, PyObject *args, PyObject *kwds);

void Sine_Stereo_dealloc(decoders_Sine_Stereo* self);

PyObject*
Sine_Stereo_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static PyObject*
Sine_Stereo_read(decoders_Sine_Stereo* self, PyObject* args);

static PyObject*
Sine_Stereo_close(decoders_Sine_Stereo* self, PyObject* args);

static PyObject*
Sine_Stereo_reset(decoders_Sine_Stereo* self, PyObject* args);

static PyObject*
Sine_Stereo_channels(decoders_Sine_Stereo *self, void *closure);

static PyObject*
Sine_Stereo_bits_per_sample(decoders_Sine_Stereo *self, void *closure);

static PyObject*
Sine_Stereo_sample_rate(decoders_Sine_Stereo *self, void *closure);

static PyObject*
Sine_Stereo_channel_mask(decoders_Sine_Stereo *self, void *closure);

PyMethodDef Sine_Stereo_methods[] = {
    {"read", (PyCFunction)Sine_Stereo_read,
     METH_VARARGS, "Reads a frame of sine data"},
    {"close", (PyCFunction)Sine_Stereo_close,
     METH_NOARGS, "Closes the stream"},
    {"reset", (PyCFunction)Sine_Stereo_reset,
     METH_NOARGS, "Resets the stream to be read again"},
    {NULL}
};

PyGetSetDef Sine_Stereo_getseters[] = {
    {"channels",
     (getter)Sine_Stereo_channels, NULL, "channels", NULL},
    {"bits_per_sample",
     (getter)Sine_Stereo_bits_per_sample, NULL, "bits_per_sample", NULL},
    {"sample_rate",
     (getter)Sine_Stereo_sample_rate, NULL, "sample_rate", NULL},
    {"channel_mask",
     (getter)Sine_Stereo_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyTypeObject decoders_Sine_Stereo_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.Sine_Stereo",    /*tp_name*/
    sizeof(decoders_Sine_Stereo),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Sine_Stereo_dealloc, /*tp_dealloc*/
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
    "Sine_Stereo objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Sine_Stereo_methods,       /* tp_methods */
    0,                         /* tp_members */
    Sine_Stereo_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Sine_Stereo_init,/* tp_init */
    0,                         /* tp_alloc */
    Sine_Stereo_new,           /* tp_new */
};


typedef struct {
    PyObject_HEAD

    int total_pcm_frames;
    int remaining_pcm_frames;
    int bits_per_sample;
    int sample_rate;
    int i;

    int max_value;
    int count;

    array_ia* buffer;
    PyObject* audiotools_pcm;
} decoders_Sine_Simple;

int
Sine_Simple_init(decoders_Sine_Simple* self, PyObject *args, PyObject *kwds);

void Sine_Simple_dealloc(decoders_Sine_Simple* self);

PyObject*
Sine_Simple_new(PyTypeObject *type, PyObject *args, PyObject *kwds);


static PyObject*
Sine_Simple_read(decoders_Sine_Simple* self, PyObject* args);

static PyObject*
Sine_Simple_close(decoders_Sine_Simple* self, PyObject* args);

static PyObject*
Sine_Simple_reset(decoders_Sine_Simple* self, PyObject* args);

static PyObject*
Sine_Simple_channels(decoders_Sine_Simple *self, void *closure);

static PyObject*
Sine_Simple_bits_per_sample(decoders_Sine_Simple *self, void *closure);

static PyObject*
Sine_Simple_sample_rate(decoders_Sine_Simple *self, void *closure);

static PyObject*
Sine_Simple_channel_mask(decoders_Sine_Simple *self, void *closure);

PyMethodDef Sine_Simple_methods[] = {
    {"read", (PyCFunction)Sine_Simple_read,
     METH_VARARGS, "Reads a frame of sine data"},
    {"close", (PyCFunction)Sine_Simple_close,
     METH_NOARGS, "Closes the stream"},
    {"reset", (PyCFunction)Sine_Simple_reset,
     METH_NOARGS, "Resets the stream to be read again"},
    {NULL}
};

PyGetSetDef Sine_Simple_getseters[] = {
    {"channels",
     (getter)Sine_Simple_channels, NULL, "channels", NULL},
    {"bits_per_sample",
     (getter)Sine_Simple_bits_per_sample, NULL, "bits_per_sample", NULL},
    {"sample_rate",
     (getter)Sine_Simple_sample_rate, NULL, "sample_rate", NULL},
    {"channel_mask",
     (getter)Sine_Simple_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyTypeObject decoders_Sine_Simple_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.Sine_Simple",    /*tp_name*/
    sizeof(decoders_Sine_Simple),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Sine_Simple_dealloc, /*tp_dealloc*/
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
    "Sine_Simple objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Sine_Simple_methods,       /* tp_methods */
    0,                         /* tp_members */
    Sine_Simple_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Sine_Simple_init, /* tp_init */
    0,                         /* tp_alloc */
    Sine_Simple_new,           /* tp_new */
};
