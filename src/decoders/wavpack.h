#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"
#include "../common/md5.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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
              IO_ERROR,
              SUB_BLOCK_NOT_FOUND,
              INVALID_BLOCK_ID,
              INVALID_RESERVED_BIT,
              EXCESSIVE_DECORRELATION_PASSES,
              INVALID_DECORRELATION_TERM,
              DECORRELATION_TERMS_MISSING,
              DECORRELATION_WEIGHTS_MISSING,
              DECORRELATION_SAMPLES_MISSING,
              ENTROPY_VARIABLES_MISSING,
              RESIDUALS_MISSING,
              EXTENDED_INTEGERS_MISSING,
              EXCESSIVE_DECORRELATION_WEIGHTS,
              INVALID_ENTROPY_VARIABLE_COUNT,
              BLOCK_DATA_CRC_MISMATCH} status;

typedef enum {WV_DECORR_TERMS      = 0x2,
              WV_DECORR_WEIGHTS    = 0x3,
              WV_DECORR_SAMPLES    = 0x4,
              WV_ENTROPY_VARIABLES = 0x5,
              WV_INT32_INFO        = 0x9,
              WV_BITSTREAM         = 0xA,
              WV_CHANNEL_INFO      = 0xD,
              WV_MD5               = 0x26} wv_metadata_function;

typedef struct {
#ifndef STANDALONE
    PyObject_HEAD

    PyObject* audiotools_pcm;
    PyObject* file;
#endif

    BitstreamReader* bitstream;
    BitstreamReader* block_data;
    BitstreamReader* sub_block_data;

    audiotools__MD5Context md5;
    int md5sum_checked;

    int sample_rate;
    int bits_per_sample;
    int channels;
    int channel_mask;
    unsigned total_pcm_frames;
    unsigned remaining_pcm_samples;
    int closed;

    /*reusable buffers*/
    aa_int* channels_data;
    a_int* decorrelation_terms;
    a_int* decorrelation_deltas;
    aa_int* decorrelation_weights;
    aaa_int* decorrelation_samples;
    aa_int* entropies;
    aa_int* residuals;
    aa_int* decorrelated;
    aa_int* correlated;
    aa_int* left_right;
    aa_int* un_shifted;
} decoders_WavPackDecoder;

#ifndef STANDALONE
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

static PyObject*
WavPackDecoder_close(decoders_WavPackDecoder* self, PyObject *args);

PyObject*
WavPackDecoder_read(decoders_WavPackDecoder* self, PyObject *args);

PyObject*
WavPackDecoder_seek(decoders_WavPackDecoder* self, PyObject *args);

PyMethodDef WavPackDecoder_methods[] = {
    {"read", (PyCFunction)WavPackDecoder_read,
     METH_VARARGS, "Returns a decoded frame"},
    {"seek", (PyCFunction)WavPackDecoder_seek,
     METH_VARARGS, "Tries to seek to the given PCM frames offset"},
    {"close", (PyCFunction)WavPackDecoder_close,
     METH_NOARGS, "Closes the stream"},
    {NULL}
};

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self);

static PyObject*
WavPackDecoder_new(PyTypeObject *type,
                   PyObject *args, PyObject *kwds);

PyObject*
wavpack_exception(status error);

PyTypeObject decoders_WavPackDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.WavPackDecoder", /*tp_name*/
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
    "WavPackDecoder objects",  /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    WavPackDecoder_methods,    /* tp_methods */
    0,                         /* tp_members */
    WavPackDecoder_getseters,  /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)WavPackDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    WavPackDecoder_new,        /* tp_new */
};

int
WavPackDecoder_update_md5sum(decoders_WavPackDecoder *self,
                             PyObject *framelist);
#else
int
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    char* filename);

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self);
#endif

const char*
wavpack_strerror(status error);

struct block_header {
    /*block ID                                    32 bits*/
    unsigned block_size;                        /*32 bits*/
    unsigned version;                           /*16 bits*/
    unsigned track_number;                      /* 8 bits*/
    unsigned index_number;                      /* 8 bits*/
    unsigned total_samples;                     /*32 bits*/
    unsigned block_index;                       /*32 bits*/
    unsigned block_samples;                     /*32 bits*/

    unsigned bits_per_sample;                   /* 2 bits*/
    unsigned mono_output;                       /* 1 bit */
    unsigned hybrid_mode;                       /* 1 bit */
    unsigned joint_stereo;                      /* 1 bit */
    unsigned cross_channel_decorrelation;       /* 1 bit */
    unsigned hybrid_noise_shaping;              /* 1 bit */
    unsigned floating_point_data;               /* 1 bit */
    unsigned extended_size_integers;            /* 1 bit */
    unsigned hybrid_parameters_control_bitrate; /* 1 bit */
    unsigned hybrid_noise_balanced;             /* 1 bit */
    unsigned initial_block;                     /* 1 bit */
    unsigned final_block;                       /* 1 bit */
    unsigned left_shift;                        /* 5 bits*/
    unsigned maximum_data_magnitude;            /* 5 bits*/
    unsigned sample_rate;                       /* 4 bits*/
    /*reserved                                     2 bits*/
    unsigned use_IIR;                           /* 1 bit */
    unsigned false_stereo;                      /* 1 bit */
    /*reserved                                     1 bit */

    uint32_t CRC;                               /*32 bits*/
};

struct sub_block {
    unsigned metadata_function;
    unsigned nondecoder_data;
    unsigned actual_size_1_less;
    unsigned large_sub_block;
    unsigned size;
    BitstreamReader* data;
};

struct extended_integers {
    unsigned sent_bits;
    unsigned zero_bits;
    unsigned one_bits;
    unsigned duplicate_bits;
};

static status
read_block_header(BitstreamReader* bs, struct block_header* header);

static int
unencode_sample_rate(unsigned encoded_sample_rate);

static int
unencode_bits_per_sample(unsigned encoded_bits_per_sample);

static status
decode_block(decoders_WavPackDecoder* decoder,
             const struct block_header* block_header,
             BitstreamReader* block_data,
             unsigned block_data_size,
             aa_int* channels);

/*returns a list of decorrelation terms and decorrelation deltas
  per decorrelation pass

  terms->_[pass]  , deltas->_[pass]*/
static status
read_decorrelation_terms(const struct sub_block* sub_block,
                         a_int* terms,
                         a_int* deltas);

/*returns a list of decorrelation weights per pass, per channel
  where channel count is determined from block header

 weights->_[pass]->_[channel]*/
static status
read_decorrelation_weights(const struct block_header* block_header,
                           const struct sub_block* sub_block,
                           unsigned term_count,
                           aa_int* weights);

/*returns a list of decorrelation samples list per pass, per channel

  samples->_[pass]->_[channel]->_[s]*/
static status
read_decorrelation_samples(const struct block_header* block_header,
                           const struct sub_block* sub_block,
                           const a_int* terms,
                           aaa_int* samples);

/*returns two lists of 3 entropy values, one per channel

 entropies->_[channel]->_[m]*/
static status
read_entropy_variables(const struct block_header* block_header,
                       const struct sub_block* sub_block,
                       aa_int* entropies);

/*returns a list of residuals per channel

 residuals->_[channel]->_[r]*/
static status
read_bitstream(const struct block_header* block_header,
               BitstreamReader* sub_block_data,
               aa_int* entropies,
               aa_int* residuals);

static unsigned
read_egc(BitstreamReader* bs);

static int
read_residual(BitstreamReader* bs,
              int* last_u,
              a_int* entropies);

static status
decorrelate_channels(const a_int* decorrelation_terms,
                     const a_int* decorrelation_deltas,
                     const aa_int* decorrelation_weights,
                     const aaa_int* decorrelation_samples,
                     const aa_int* residuals,
                     aa_int* decorrelated,
                     aa_int* correlated  /*a temporary buffer*/
                     );

static status
decorrelate_1ch_pass(int decorrelation_term,
                     int decorrelation_delta,
                     int decorrelation_weight,
                     const a_int* decorrelation_samples,
                     const a_int* correlated,
                     a_int* decorrelated);

static status
decorrelate_2ch_pass(int decorrelation_term,
                     int decorrelation_delta,
                     int weight_0,
                     int weight_1,
                     const a_int* samples_0,
                     const a_int* samples_1,
                     const aa_int* correlated,
                     aa_int* decorrelated);

static void
undo_joint_stereo(const aa_int* mid_side, aa_int* left_right);

static uint32_t
calculate_crc(const aa_int* channels);

static int
read_wv_exp2(BitstreamReader* sub_block_data);

/*read a sub block header and data to the given struct
  which *must* have a valid bitstream recorder ->data field

  returns the total sub block size on success
  returns -1 if an IO error occurs reading the sub block*/
static int
read_sub_block(BitstreamReader* bitstream,
               struct sub_block* sub_block);

static unsigned
sub_block_data_size(const struct sub_block* sub_block);

static status
find_sub_block(const struct block_header* block_header,
               BitstreamReader* bitstream,
               unsigned metadata_function,
               unsigned nondecoder_data,
               struct sub_block* sub_block);

static status
read_sample_rate_sub_block(const struct block_header* block_header,
                           BitstreamReader* bitstream,
                           int* sample_rate);

static status
read_channel_count_sub_block(const struct block_header* block_header,
                             BitstreamReader* bitstream,
                             int* channel_count,
                             int* channel_mask);

static status
read_extended_integers(const struct sub_block* sub_block,
                       struct extended_integers* extended_integers);

static void
undo_extended_integers(const struct extended_integers* params,
                       const aa_int* extended_integers,
                       aa_int* un_extended_integers);
