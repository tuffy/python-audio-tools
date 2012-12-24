#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include "../bitstream.h"
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

typedef enum {OK,
              IOERROR,
              CRCMISMATCH,
              INVALID_SIGNATURE,
              UNSUPPORTED_FORMAT} status;

struct tta_cache {
    array_i* k0;
    array_i* sum0;
    array_i* k1;
    array_i* sum1;
    array_ia* residual;
    array_ia* filtered;
    array_ia* predicted;
};

#ifndef STANDALONE
typedef struct {
    PyObject_HEAD

    struct {
        unsigned channels;
        unsigned bits_per_sample;
        unsigned sample_rate;
        unsigned total_pcm_frames;
    } header;

    unsigned total_tta_frames;
    unsigned current_tta_frame;
    unsigned block_size;
    unsigned* seektable;

    struct tta_cache cache;

    int closed;

    BitstreamReader* bitstream;
    BitstreamReader* frame;
    array_ia* framelist;

    /*a framelist generator*/
    PyObject* audiotools_pcm;
} decoders_TTADecoder;

static PyObject*
TTADecoder_sample_rate(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_bits_per_sample(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_channels(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_channel_mask(decoders_TTADecoder *self, void *closure);

static PyObject*
TTADecoder_read(decoders_TTADecoder *self, PyObject *args);

static PyObject*
TTADecoder_close(decoders_TTADecoder *self, PyObject *args);

static PyObject*
TTADecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
TTADecoder_dealloc(decoders_TTADecoder *self);

int
TTADecoder_init(decoders_TTADecoder *self, PyObject *args, PyObject *kwds);

PyGetSetDef TTADecoder_getseters[] = {
    {"sample_rate",
     (getter)TTADecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)TTADecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)TTADecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)TTADecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef TTADecoder_methods[] = {
    {"read",
    (PyCFunction)TTADecoder_read,
     METH_VARARGS,
     "Reads the given number of PCM frames from the TTA file, if possible"},
    {"close",
    (PyCFunction)TTADecoder_close,
     METH_NOARGS,
     "Closes the TTA decoder stream"},
    {NULL}
};

PyTypeObject decoders_TTADecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.TTADecoder",     /*tp_name*/
    sizeof(decoders_TTADecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)TTADecoder_dealloc, /*tp_dealloc*/
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
    "TTADecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    TTADecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    TTADecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)TTADecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    TTADecoder_new,            /* tp_new */
  };
#endif

static void
init_cache(struct tta_cache *cache);

static void
free_cache(struct tta_cache *cache);

static status
read_header(BitstreamReader* bitstream,
            unsigned* channels,
            unsigned* bits_per_sample,
            unsigned* sample_rate,
            unsigned* total_pcm_frames);

static status
read_seektable(BitstreamReader* bitstream,
               unsigned total_tta_frames,
               unsigned seektable[]);

static status
read_frame(BitstreamReader* frame,
           struct tta_cache* cache,
           unsigned block_size,
           unsigned channels,
           unsigned bits_per_sample,
           array_ia* framelist);

static void
hybrid_filter(array_i* residual,
              unsigned bits_per_sample,
              array_i* filtered);

static void
fixed_prediction(array_i* filtered,
                 unsigned bits_per_sample,
                 array_i* predicted);

static void
decorrelate_channels(array_ia* predicted,
                     array_ia* decorrelated);
