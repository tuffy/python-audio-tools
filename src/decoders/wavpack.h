#include <Python.h>
#include <stdint.h>
#include "../bitstream_r.h"

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

typedef enum {OK, ERROR} status;

typedef struct {
    PyObject_HEAD

    FILE* file;
    char* filename;
    Bitstream* bitstream;

    int sample_rate;
    int bits_per_sample;
    int channels;
    int channel_mask;
    int remaining_samples;
} decoders_WavPackDecoder;

struct wavpack_block_header {
    /*block ID                                   32 bits*/
    uint32_t block_size;                       /*32 bits*/
    uint16_t version;                          /*16 bits*/
    uint8_t track_number;                      /*8 bits*/
    uint8_t index_number;                      /*8 bits*/
    uint32_t total_samples;                    /*32 bits*/
    uint32_t block_index;                      /*32 bits*/
    uint32_t block_samples;                    /*32 bits*/

    uint8_t bits_per_sample;                   /*2 bits*/
    uint8_t mono_output;                       /*1 bit*/
    uint8_t hybrid_mode;                       /*1 bit*/
    uint8_t joint_stereo;                      /*1 bit*/
    uint8_t cross_channel_decorrelation;       /*1 bit*/
    uint8_t hybrid_noise_shaping;              /*1 bit*/
    uint8_t floating_point_data;               /*1 bit*/
    uint8_t extended_size_integers;            /*1 bit*/
    uint8_t hybrid_parameters_control_bitrate; /*1 bit*/
    uint8_t hybrid_noise_balanced;             /*1 bit*/
    uint8_t initial_block_in_sequence;         /*1 bit*/
    uint8_t final_block_in_sequence;           /*1 bit*/
    uint8_t left_shift;                        /*5 bits*/
    uint8_t maximum_data_magnitude;            /*5 bits*/
    uint32_t sample_rate;                      /*4 bits*/
    /*reserved                                   2 bits*/
    uint8_t use_IIR;                           /*1 bit*/
    uint8_t false_stereo;                      /*1 bit*/
    /*reserved                                   1 bit*/

    uint32_t crc;                              /*32 bits*/
};

struct wavpack_subblock_header {
    uint8_t metadata_function;                 /*5 bits*/
    uint8_t nondecoder_data;                   /*1 bit*/
    uint8_t actual_size_1_less;                /*1 bit*/
    uint8_t large_block;                       /*1 bit*/
    uint32_t block_size;                       /*8 bits/24 bits*/
};

/*the WavPackDecoder.__init__() method*/
int
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    PyObject *args, PyObject *kwds);

/*the WavPackDecoder.sample_rate attribute getter*/
static PyObject*
WavPackDecoder_sample_rate(decoders_WavPackDecoder *self, void *closure);

/*the WavPackDecoder.bits_per_sample attribute getter*/
static PyObject*
WavPackDecoder_bits_per_sample(decoders_WavPackDecoder *self, void *closure);

/*the WavPackDecoder.channels attribute getter*/
static PyObject*
WavPackDecoder_channels(decoders_WavPackDecoder *self, void *closure);

/*the WavPackDecoder.channel_mask attribute getter*/
static PyObject*
WavPackDecoder_channel_mask(decoders_WavPackDecoder *self, void *closure);

PyGetSetDef WavPackDecoder_getseters[] = {
    {"sample_rate",
     (getter)WavPackDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)WavPackDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)WavPackDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)WavPackDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

/*the WavPackDecoder.analyze_frame() method*/
static PyObject*
WavPackDecoder_analyze_frame(decoders_WavPackDecoder* self, PyObject *args);

PyObject*
WavPackDecoder_analyze_subblock(Bitstream* bitstream);

PyMethodDef WavPackDecoder_methods[] = {
    {"analyze_frame", (PyCFunction)WavPackDecoder_analyze_frame,
     METH_NOARGS, "Returns the analysis of the next frame"},
    {NULL}
};

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self);

static PyObject*
WavPackDecoder_new(PyTypeObject *type,
                   PyObject *args, PyObject *kwds);

status
WavPackDecoder_read_block_header(Bitstream* bitstream,
                                 struct wavpack_block_header* header);

void
WavPackDecoder_read_subblock_header(Bitstream* bitstream,
                                    struct wavpack_subblock_header* header);

PyTypeObject decoders_WavPackDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.WavPackDecoder",    /*tp_name*/
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
    "WavPackDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    WavPackDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    WavPackDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)WavPackDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    WavPackDecoder_new,           /* tp_new */
};
