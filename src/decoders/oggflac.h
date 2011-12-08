#include <Python.h>
#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"
#include "ogg.h"
#define OGG_FLAC
#include "flac.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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

    FILE* ogg_file;
    OggReader* ogg_stream;
    BitstreamReader* packet;
    int channel_mask;

    struct flac_STREAMINFO streaminfo;

    uint32_t crc16;
    audiotools__MD5Context md5;

    /*temporary buffers we don't want to reallocate each time*/
    array_ia* subframe_data;
    array_i* residuals;
    array_i* qlp_coeffs;
    array_i* framelist_data;

    /*a framelist generator*/
    PyObject* audiotools_pcm;
} decoders_OggFlacDecoder;

static PyObject*
OggFlacDecoder_sample_rate(decoders_OggFlacDecoder *self, void *closure);

static PyObject*
OggFlacDecoder_bits_per_sample(decoders_OggFlacDecoder *self, void *closure);

static PyObject*
OggFlacDecoder_channels(decoders_OggFlacDecoder *self, void *closure);

static PyObject*
OggFlacDecoder_channel_mask(decoders_OggFlacDecoder *self, void *closure);

static PyObject*
OggFlacDecoder_read(decoders_OggFlacDecoder *self, PyObject *args);

static PyObject*
OggFlacDecoder_close(decoders_OggFlacDecoder *self, PyObject *args);

static PyObject*
OggFlacDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
OggFlacDecoder_dealloc(decoders_OggFlacDecoder *self);

int
OggFlacDecoder_init(decoders_OggFlacDecoder *self,
                    PyObject *args, PyObject *kwds);

PyGetSetDef OggFlacDecoder_getseters[] = {
    {"sample_rate", (getter)OggFlacDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)OggFlacDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels", (getter)OggFlacDecoder_channels, NULL, "channels", NULL},
    {"channel_mask", (getter)OggFlacDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef OggFlacDecoder_methods[] = {
    {"read", (PyCFunction)OggFlacDecoder_read, METH_VARARGS, ""},
    {"close", (PyCFunction)OggFlacDecoder_close, METH_NOARGS, ""},
    {NULL}
  };

PyTypeObject decoders_OggFlacDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.OggFlacDecoder",     /*tp_name*/
    sizeof(decoders_OggFlacDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)OggFlacDecoder_dealloc, /*tp_dealloc*/
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
    "OggFlacDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    OggFlacDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    OggFlacDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)OggFlacDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    OggFlacDecoder_new,            /* tp_new */
};

int
oggflac_read_streaminfo(BitstreamReader *bitstream,
                        struct flac_STREAMINFO *streaminfo,
                        uint16_t *header_packets);
int
OggFlacDecoder_update_md5sum(decoders_OggFlacDecoder *self,
                             PyObject *framelist);

int
OggFlacDecoder_verify_okay(decoders_OggFlacDecoder *self);
