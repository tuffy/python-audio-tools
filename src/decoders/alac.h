#include <Python.h>
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

struct alac_parameters {
    unsigned block_size;
    unsigned history_multiplier;
    unsigned initial_history;
    unsigned maximum_K;
};

struct alac_seekpoint {
    unsigned pcm_frames;
    unsigned byte_size;
};

typedef struct {
    PyObject_HEAD

    BitstreamReader *bitstream;
    br_pos_t *mdat_start;

    unsigned total_pcm_frames;
    unsigned read_pcm_frames;

    struct alac_parameters params;

    unsigned bits_per_sample;
    unsigned channels;
    unsigned sample_rate;

    unsigned total_alac_frames;
    struct alac_seekpoint *seektable;

    int closed;

    /*a framelist generator*/
    PyObject *audiotools_pcm;
} decoders_ALACDecoder;


PyObject*
ALACDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
ALACDecoder_init(decoders_ALACDecoder *self,
                 PyObject *args, PyObject *kwds);

void
ALACDecoder_dealloc(decoders_ALACDecoder *self);

static PyObject*
ALACDecoder_sample_rate(decoders_ALACDecoder *self, void *closure);

static PyObject*
ALACDecoder_bits_per_sample(decoders_ALACDecoder *self, void *closure);

static PyObject*
ALACDecoder_channels(decoders_ALACDecoder *self, void *closure);

static PyObject*
ALACDecoder_channel_mask(decoders_ALACDecoder *self, void *closure);

static PyObject*
ALACDecoder_read(decoders_ALACDecoder* self, PyObject *args);

static PyObject*
ALACDecoder_seek(decoders_ALACDecoder* self, PyObject *args);

static PyObject*
ALACDecoder_close(decoders_ALACDecoder* self, PyObject *args);

static PyObject*
ALACDecoder_enter(decoders_ALACDecoder* self, PyObject *args);

static PyObject*
ALACDecoder_exit(decoders_ALACDecoder* self, PyObject *args);

PyGetSetDef ALACDecoder_getseters[] = {
    {"sample_rate",
     (getter)ALACDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)ALACDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)ALACDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)ALACDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef ALACDecoder_methods[] = {
    {"read", (PyCFunction)ALACDecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"seek", (PyCFunction)ALACDecoder_seek,
     METH_VARARGS, "seek(desired_pcm_offset) -> actual_pcm_offset"},
    {"close", (PyCFunction)ALACDecoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)ALACDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)ALACDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_ALACDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.ALACDecoder",    /*tp_name*/
    sizeof(decoders_ALACDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ALACDecoder_dealloc, /*tp_dealloc*/
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
    "ALACDecoder objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /*  tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ALACDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    ALACDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ALACDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    ALACDecoder_new,           /* tp_new */
};
