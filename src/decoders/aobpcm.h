#include <Python.h>
#include <stdint.h>

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

/*the default size of the buffer, in 2 PCM frame chunks*/
#define DEFAULT_BUFFER_SIZE 1028

const uint8_t AOB_BYTE_SWAP[2][6][36] = {
    { /*16 bps*/
        {1, 0, 3, 2},                                    /*1 ch*/
        {1, 0, 3, 2, 5, 4, 7, 6},                        /*2 ch*/
        {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10},          /*3 ch*/
        {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10,
         13, 12, 15, 14},                                /*4 ch*/
        {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10,
         13, 12, 15, 14, 17, 16, 19, 18},                /*5 ch*/
        {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10,
         13, 12, 15, 14, 17, 16, 19, 18, 21, 20, 23, 22} /*6 ch*/
    },
    { /*24 bps*/
        {  2,  1,  5,  4,  0,  3},  /*1 ch*/
        {  2,  1,  5,  4,  8,  7,
          11, 10,  0,  3,  6,  9},  /*2 ch*/
        {  8,  7, 17, 16,  6, 15,
           2,  1,  5,  4, 11, 10,
          14, 13,  0,  3,  9, 12},  /*3 ch*/
        {  8,  7, 11, 10, 20, 19,
          23, 22,  6,  9, 18, 21,
           2,  1,  5,  4, 14, 13,
          17, 16,  0,  3, 12, 15},  /*4 ch*/
        {  8,  7, 11, 10, 14, 13,
          23, 22, 26, 25, 29, 28,
           6,  9, 12, 21, 24, 27,
           2,  1,  5,  4, 17, 16,
          20, 19,  0,  3, 15, 18},  /*5 ch*/
        {  8,  7, 11, 10, 26, 25,
          29, 28,  6,  9, 24, 27,
           2,  1,  5,  4, 14, 13,
          17, 16, 20, 19, 23, 22,
          32, 31, 35, 34,  0,  3,
          12, 15, 18, 21, 30, 33}  /*6 ch*/
    }
};

typedef struct {
    PyObject_HEAD

    struct br_python_input* reader;
    int sample_rate;
    int channels;
    int channel_mask;
    int bits_per_sample;

    unsigned int chunk_size;  /*chunk size in bytes
                                each "chunk" is 2 PCM frames,
                                or (bits_per_sample / 8) * channels * 2
                              */
    uint8_t* buffer;
    unsigned int buffer_size; /*the total buffer size, in chunks*/
    uint8_t swap[36];         /*a lookup table for byte swapping output*/
} decoders_AOBPCMDecoder;

/*the AOBPCMDecoder.sample_rate attribute getter*/
static PyObject*
AOBPCMDecoder_sample_rate(decoders_AOBPCMDecoder *self, void *closure);

/*the AOBPCMDecoder.bits_per_sample attribute getter*/
static PyObject*
AOBPCMDecoder_bits_per_sample(decoders_AOBPCMDecoder *self, void *closure);

/*the AOBPCMDecoder.channels attribute getter*/
static PyObject*
AOBPCMDecoder_channels(decoders_AOBPCMDecoder *self, void *closure);

/*the AOBPCMDecoder.channel_mask attribute getter*/
static PyObject*
AOBPCMDecoder_channel_mask(decoders_AOBPCMDecoder *self, void *closure);

/*the AOBPCMDecoder.read() method*/
static PyObject*
AOBPCMDecoder_read(decoders_AOBPCMDecoder* self, PyObject *args);

static PyObject*
bytes_to_framelist(uint8_t *bytes,
                   int bytes_length,
                   int channels,
                   int bits_per_sample,
                   int is_big_endian,
                   int is_signed);

/*reads a single, 2 frame chunk into the given buffer
  returns 1 on success, 0 on EOF and -1 if a whole chunk cannot be read*/
int
aobpcm_read_chunk(uint8_t* buffer,
                  int chunk_size,
                  uint8_t* swap,
                  struct br_python_input* reader);

/*the MLPDecoder.close() method*/
static PyObject*
AOBPCMDecoder_close(decoders_AOBPCMDecoder* self, PyObject *args);

PyGetSetDef AOBPCMDecoder_getseters[] = {
    {"sample_rate",
     (getter)AOBPCMDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)AOBPCMDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)AOBPCMDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)AOBPCMDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef AOBPCMDecoder_methods[] = {
    {"read", (PyCFunction)AOBPCMDecoder_read,
     METH_VARARGS,
     "Reads the given number of bytes from the AOB PCM file, if possible"},
    {"close", (PyCFunction)AOBPCMDecoder_close,
     METH_NOARGS, "Closes the AOB PCM decoder stream"},
    {NULL}
};

/*the AOBPCMDecoder.__init__() method*/
int
AOBPCMDecoder_init(decoders_AOBPCMDecoder *self,
                   PyObject *args, PyObject *kwds);

void
AOBPCMDecoder_dealloc(decoders_AOBPCMDecoder *self);

static PyObject*
AOBPCMDecoder_new(PyTypeObject *type,
                  PyObject *args, PyObject *kwds);

PyTypeObject decoders_AOBPCMDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.AOBPCMDecoder",    /*tp_name*/
    sizeof(decoders_AOBPCMDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)AOBPCMDecoder_dealloc, /*tp_dealloc*/
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
    "AOBPCMDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    AOBPCMDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    AOBPCMDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)AOBPCMDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    AOBPCMDecoder_new,            /* tp_new */
};
