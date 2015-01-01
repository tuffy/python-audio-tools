#include <Python.h>
#include <stdint.h>
#include <vorbis/vorbisfile.h>
#include "../array.h"

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

typedef struct {
    PyObject_HEAD

    OggVorbis_File vorbisfile;
    int open_ok;  /*used to determine if vorbis_file is opened successfully*/

    int channel_count;
    long rate;
    int closed;

    aa_int* channels;
    PyObject* audiotools_pcm;
} decoders_VorbisDecoder;

static PyObject*
VorbisDecoder_sample_rate(decoders_VorbisDecoder *self, void *closure);

static PyObject*
VorbisDecoder_bits_per_sample(decoders_VorbisDecoder *self, void *closure);

static PyObject*
VorbisDecoder_channels(decoders_VorbisDecoder *self, void *closure);

static PyObject*
VorbisDecoder_channel_mask(decoders_VorbisDecoder *self, void *closure);

static PyObject*
VorbisDecoder_read(decoders_VorbisDecoder *self, PyObject *args);

static PyObject*
VorbisDecoder_close(decoders_VorbisDecoder *self, PyObject *args);

static PyObject*
VorbisDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
VorbisDecoder_dealloc(decoders_VorbisDecoder *self);

int
VorbisDecoder_init(decoders_VorbisDecoder *self, PyObject *args, PyObject *kwds);

static PyObject*
VorbisDecoder_enter(decoders_VorbisDecoder* self, PyObject *args);

static PyObject*
VorbisDecoder_exit(decoders_VorbisDecoder* self, PyObject *args);

PyGetSetDef VorbisDecoder_getseters[] = {
    {"sample_rate", (getter)VorbisDecoder_sample_rate,
     NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)VorbisDecoder_bits_per_sample,
     NULL, "bits-per-sample", NULL},
    {"channels", (getter)VorbisDecoder_channels, NULL,
     "channels", NULL},
    {"channel_mask", (getter)VorbisDecoder_channel_mask,
     NULL, "channel mask", NULL},
    {NULL}
};

PyMethodDef VorbisDecoder_methods[] = {
    {"read", (PyCFunction)VorbisDecoder_read, METH_VARARGS,
     "read(pcm_frame_count) -> FrameList"},
    {"close", (PyCFunction)VorbisDecoder_close, METH_NOARGS,
     "close() -> None"},
    {"__enter__", (PyCFunction)VorbisDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)VorbisDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_VorbisDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.VorbisDecoder",     /*tp_name*/
    sizeof(decoders_VorbisDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)VorbisDecoder_dealloc, /*tp_dealloc*/
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
    "VorbisDecoder objects",   /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    VorbisDecoder_methods,     /* tp_methods */
    0,                         /* tp_members */
    VorbisDecoder_getseters,   /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)VorbisDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    VorbisDecoder_new,         /* tp_new */
};
