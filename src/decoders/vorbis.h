#include <Python.h>
#include <stdint.h>
#include "ogg.h"

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

struct vorbis_identification_header {
    uint32_t vorbis_version;
    uint8_t channel_count;
    uint32_t sample_rate;
    uint32_t bitrate_maximum;
    uint32_t bitrate_nominal;
    uint32_t bitrate_minimum;
    uint16_t blocksize_0;
    uint16_t blocksize_1;
};

typedef struct {
    PyObject_HEAD

    FILE* ogg_file;
    OggReader* ogg_stream;
    Bitstream* packet;

    struct vorbis_identification_header identification;
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
VorbisDecoder_analyze_frame(decoders_VorbisDecoder *self, PyObject *args);

static PyObject*
VorbisDecoder_close(decoders_VorbisDecoder *self, PyObject *args);

static PyObject*
VorbisDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
VorbisDecoder_dealloc(decoders_VorbisDecoder *self);

int
VorbisDecoder_init(decoders_VorbisDecoder *self, PyObject *args, PyObject *kwds);

PyGetSetDef VorbisDecoder_getseters[] = {
    {"sample_rate", (getter)VorbisDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)VorbisDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels", (getter)VorbisDecoder_channels, NULL, "channels", NULL},
    {"channel_mask", (getter)VorbisDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef VorbisDecoder_methods[] = {
    {"read", (PyCFunction)VorbisDecoder_read, METH_VARARGS, ""},
    {"analyze_frame", (PyCFunction)VorbisDecoder_analyze_frame, METH_NOARGS, ""},
    {"close", (PyCFunction)VorbisDecoder_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject decoders_VorbisDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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

/*returns a non-negative packet type upon success
  or a negative value if the header fields aren't "vorbis"
  doesn't perform any EOF checking of its own*/
int
vorbis_read_common_header(Bitstream *packet);

/*reads packet data (including the common header) into "identification"
  performs EOF checking in case the packet is too small
  returns 1 upon success
  returns 0 upon failure and sets the appropriate Python exception*/
int
vorbis_read_identification_packet(
                        Bitstream *packet,
                        struct vorbis_identification_header *identification);
