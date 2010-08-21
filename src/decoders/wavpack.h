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

typedef enum {OK, ERROR} status;

typedef enum {WV_DECORR_TERMS      = 0x2,
              WV_DECORR_WEIGHTS    = 0x3,
              WV_DECORR_SAMPLES    = 0x4,
              WV_ENTROPY_VARIABLES = 0x5,
              WV_BITSTREAM         = 0xA} wv_metadata_function;

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

    /*a bunch of buffers to hold our sub-block data*/
    struct i_array decorr_terms;
    struct i_array decorr_deltas;
    struct i_array decorr_weights_A;
    struct i_array decorr_weights_B;
    struct ia_array decorr_samples_A;
    struct ia_array decorr_samples_B;
    struct i_array entropy_variables_A;
    struct i_array entropy_variables_B;
    struct i_array values;
    struct ia_array decoded_samples;

    /*boolean indicators as to whether certain sub-blocks have been found*/
    int got_decorr_terms;
    int got_decorr_weights;
    int got_decorr_samples;
    int got_entropy_variables;
    int got_bitstream;
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

#define MAXIMUM_TERM_COUNT 16

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

static PyObject*
WavPackDecoder_offset(decoders_WavPackDecoder *self, void *closure);

PyGetSetDef WavPackDecoder_getseters[] = {
    {"sample_rate",
     (getter)WavPackDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)WavPackDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)WavPackDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)WavPackDecoder_channel_mask, NULL, "channel_mask", NULL},
    {"offset",
     (getter)WavPackDecoder_offset, NULL, "offset", NULL},
    {NULL}
};

/*the WavPackDecoder.analyze_frame() method*/
static PyObject*
WavPackDecoder_analyze_frame(decoders_WavPackDecoder* self, PyObject *args);

/*the WavPackDecoder.close() method*/
static PyObject*
WavPackDecoder_close(decoders_WavPackDecoder* self, PyObject *args);

PyObject*
WavPackDecoder_read(decoders_WavPackDecoder* self,
                    struct wavpack_block_header* block_header);

PyObject*
WavPackDecoder_analyze_subblock(decoders_WavPackDecoder* self,
                                struct wavpack_block_header* block_header);

PyMethodDef WavPackDecoder_methods[] = {
    {"read", (PyCFunction)WavPackDecoder_read,
     METH_VARARGS, "Returns a decoded frame"},
    {"analyze_frame", (PyCFunction)WavPackDecoder_analyze_frame,
     METH_NOARGS, "Returns the analysis of the next frame"},
    {"close", (PyCFunction)WavPackDecoder_close,
     METH_NOARGS, "Closes the stream"},
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

/*Reads the interleaved decorrelation terms and decorrelation deltas
  from the bitstream to the given arrays.
  May return an error if any of the terms are invalid.*/
status
WavPackDecoder_read_decorr_terms(Bitstream* bitstream,
                                 struct wavpack_subblock_header* header,
                                 struct i_array* decorr_terms,
                                 struct i_array* decorr_deltas);

int
WavPackDecoder_restore_weight(int weight);

/*Reads the interleaved decorrelation weights
  from the bitstream to the given arrays.*/
status
WavPackDecoder_read_decorr_weights(Bitstream* bitstream,
                                   struct wavpack_subblock_header* header,
                                   int block_channel_count,
                                   int term_count,
                                   struct i_array *weights_A,
                                   struct i_array *weights_B);

status
WavPackDecoder_read_decorr_samples(Bitstream* bitstream,
                                   struct wavpack_subblock_header* header,
                                   int block_channel_count,
                                   struct i_array* decorr_terms,
                                   struct ia_array* samples_A,
                                   struct ia_array* samples_B);

status
WavPackDecoder_read_entropy_variables(Bitstream* bitstream,
                                      int block_channel_count,
                                      struct i_array* entropy_variables_A,
                                      struct i_array* entropy_variables_B);

/*Reads the WV_BITSTREAM sub-block and returns
  channel_count * samples number of values to the given array.*/
status
WavPackDecoder_read_wv_bitstream(Bitstream* bitstream,
                                 struct wavpack_subblock_header* header,
                                 struct i_array* entropy_variables_A,
                                 struct i_array* entropy_variables_B,
                                 int block_channel_count,
                                 int block_samples,
                                 struct i_array* values);

int wavpack_get_value(Bitstream* bitstream,
                      struct i_array* entropy_variables,
                      int* holding_one,
                      int* holding_zero);

int wavpack_get_zero_count(Bitstream* bitstream);

void wavpack_decrement_counter(int byte, void* counter);

/*Reads a single block from the bitstream
  and returns its final sample values to channel_A and (optionally) channel_B.
  "channel_count" indicates whether 1 or 2 channels were decoded.
  "final_block" indicates whether this is the final block to read
  before decoding channels into a final pcm.FrameList object.*/
status
WavPackDecoder_decode_block(decoders_WavPackDecoder* self,
                            struct i_array* channel_A,
                            struct i_array* channel_B,
                            int* channel_count,
                            int* final_block);

status
WavPackDecoder_decode_subblock(decoders_WavPackDecoder* self,
                               struct wavpack_block_header* block_header);

/*Performs a decorrelation pass over channel_A and (optionally) channel_B,
  altering their values in the process.
  If "channel_count" is 1, only channel_A and weight_A are used.
  Otherwise, channel_B is also used.*/
void wavpack_perform_decorrelation_pass(
                                    struct i_array* channel_A,
                                    struct i_array* channel_B,
                                    int decorrelation_term,
                                    int decorrelation_delta,
                                    int decorrelation_weight_A,
                                    int decorrelation_weight_B,
                                    struct i_array* decorrelation_samples_A,
                                    struct i_array* decorrelation_samples_B,
                                    int channel_count);

void wavpack_perform_decorrelation_pass_1ch(
                                    struct i_array* channel,
                                    int decorrelation_term,
                                    int decorrelation_delta,
                                    int decorrelation_weight,
                                    struct i_array* decorrelation_samples);

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
