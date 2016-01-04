#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
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

struct STREAMINFO {
    unsigned minimum_block_size;
    unsigned maximum_block_size;
    unsigned minimum_frame_size;
    unsigned maximum_frame_size;
    unsigned sample_rate;
    unsigned channel_count;
    unsigned bits_per_sample;
    uint64_t total_samples;
    uint8_t MD5[16];
};

struct SEEKPOINT {
    uint64_t sample_number;
    uint64_t frame_offset;
    unsigned frame_samples;
};

struct SEEKTABLE {
    unsigned total_points;
    struct SEEKPOINT *seek_points;
};

#ifndef STANDALONE
typedef struct {
    PyObject_HEAD

    BitstreamReader* bitstream;
    struct STREAMINFO streaminfo;
    struct SEEKTABLE seektable;
    unsigned channel_mask;
    uint64_t remaining_samples;
    int closed;

    audiotools__MD5Context md5;
    int perform_validation;
    int stream_finalized;

    /*a framelist generator*/
    PyObject* audiotools_pcm;

    /*a mark for seeking purposes*/
    br_pos_t* beginning_of_frames;
} decoders_FlacDecoder;

static PyObject*
FlacDecoder_sample_rate(decoders_FlacDecoder *self, void *closure);

static PyObject*
FlacDecoder_bits_per_sample(decoders_FlacDecoder *self, void *closure);

static PyObject*
FlacDecoder_channels(decoders_FlacDecoder *self, void *closure);

static PyObject*
FlacDecoder_channel_mask(decoders_FlacDecoder *self, void *closure);

static PyObject*
FlacDecoder_read(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_frame_size(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_seek(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_close(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_enter(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_exit(decoders_FlacDecoder* self, PyObject *args);


PyGetSetDef FlacDecoder_getseters[] = {
    {"sample_rate",
     (getter)FlacDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)FlacDecoder_bits_per_sample, NULL, "bits-per-sample", NULL},
    {"channels",
     (getter)FlacDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)FlacDecoder_channel_mask, NULL, "channel mask", NULL},
    {NULL}
};

PyMethodDef FlacDecoder_methods[] = {
    {"read", (PyCFunction)FlacDecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"seek", (PyCFunction)FlacDecoder_seek,
     METH_VARARGS, "seek(desired_pcm_offset) -> actual_pcm_offset"},
    {"frame_size", (PyCFunction)FlacDecoder_frame_size,
     METH_NOARGS, "frame_size() -> (byte_length, pcm_frame_count)"},
    {"close", (PyCFunction)FlacDecoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)FlacDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)FlacDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

static PyObject*
FlacDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

int
FlacDecoder_init(decoders_FlacDecoder *self,
                 PyObject *args, PyObject *kwds);

void
FlacDecoder_dealloc(decoders_FlacDecoder *self);

PyTypeObject decoders_FlacDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.FlacDecoder",     /* tp_name */
    sizeof(decoders_FlacDecoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)FlacDecoder_dealloc, /* tp_dealloc */
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
    "FlacDecoder objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
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
