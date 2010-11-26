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

typedef struct {
    PyObject_HEAD

    FILE* file;
    Bitstream* bitstream;
} decoders_MLPDecoder;

/*the MLPDecoder.sample_rate attribute getter*/
static PyObject*
MLPDecoder_sample_rate(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.bits_per_sample attribute getter*/
static PyObject*
MLPDecoder_bits_per_sample(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.channels attribute getter*/
static PyObject*
MLPDecoder_channels(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.channel_mask attribute getter*/
static PyObject*
MLPDecoder_channel_mask(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.read() method*/
static PyObject*
MLPDecoder_read(decoders_MLPDecoder* self, PyObject *args);

/*the MLPDecoder.analyze_frame() method*/
static PyObject*
MLPDecoder_analyze_frame(decoders_MLPDecoder* self, PyObject *args);

/*the MLPDecoder.close() method*/
static PyObject*
MLPDecoder_close(decoders_MLPDecoder* self, PyObject *args);

/*the MLPDecoder.__init__() method*/
int
MLPDecoder_init(decoders_MLPDecoder *self,
                PyObject *args, PyObject *kwds);

PyGetSetDef MLPDecoder_getseters[] = {
    {"sample_rate",
     (getter)MLPDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)MLPDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)MLPDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)MLPDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef MLPDecoder_methods[] = {
    {"read", (PyCFunction)MLPDecoder_read,
     METH_VARARGS,
     "Reads the given number of bytes from the MLP file, if possible"},
    {"analyze_frame", (PyCFunction)MLPDecoder_analyze_frame,
     METH_NOARGS, "Returns the analysis of the next frame"},
    {"close", (PyCFunction)MLPDecoder_close,
     METH_NOARGS, "Closes the MLP decoder stream"},
    {NULL}
};

void
MLPDecoder_dealloc(decoders_MLPDecoder *self);

static PyObject*
MLPDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds);

PyTypeObject decoders_MLPDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.MLPDecoder",    /*tp_name*/
    sizeof(decoders_MLPDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)MLPDecoder_dealloc, /*tp_dealloc*/
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
    "MLPDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    MLPDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    MLPDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)MLPDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    MLPDecoder_new,           /* tp_new */
};
