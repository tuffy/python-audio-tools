#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include "../bitstream_r.h"
#include "../array.h"

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

#define MAX_MLP_CHANNELS 8
#define MAX_MLP_MATRICES 6
#define MAX_MLP_SUBSTREAMS 2

#define MLP_FRAMES_AT_A_TIME 1000

struct mlp_MajorSync {
    /* sync words (0xF8726F)     24 bits*/
    /* stream type (0xBB)         8 bits*/
    uint8_t group1_bits;        /*4 bits*/
    uint8_t group2_bits;        /*4 bits*/
    uint8_t group1_sample_rate; /*4 bits*/
    uint8_t group2_sample_rate; /*4 bits*/
    /* unknown                   11 bits*/
    uint8_t channel_assignment; /*5 bits*/
    /* unknown                   48 bits*/
    /* is VBR                     1 bit*/
    /* peak bitrate              15 bits*/
    uint8_t substream_count;   /* 4 bits*/
    /* unknown                   92 bits*/
};

struct mlp_SubstreamSize {
    /* extraword present            1 bit*/
    uint8_t nonrestart_substream; /*1 bit*/
    uint8_t checkdata_present;    /*1 bit*/
    /* skip                         1 bit*/
    uint16_t substream_size; /*    12 bits*/
};

struct mlp_RestartHeader {
    /* sync word (0x18F5)                           13 bits*/
    uint8_t noise_type;                            /*1 bit*/
    uint16_t output_timestamp;                    /*16 bits*/
    uint8_t min_channel;                           /*4 bits*/
    uint8_t max_channel;                           /*4 bits*/
    uint8_t max_matrix_channel;                    /*4 bits*/
    uint8_t noise_shift;                           /*4 bits*/
    uint32_t noise_gen_seed;                      /*23 bits*/
    /* unknown                                      19 bits*/
    uint8_t data_check_present;                    /*1 bit*/
    uint8_t lossless_check;                        /*8 bits*/
    /* unknown                                      16 bits*/
    uint8_t channel_assignments[MAX_MLP_CHANNELS]; /*6 bits each*/
    uint8_t checksum;                              /*8 bits*/
};

struct mlp_ParameterPresentFlags {
    uint8_t parameter_present_flags;  /*1 bit*/
    uint8_t huffman_offset;           /*1 bit*/
    uint8_t iir_filter_parameters;    /*1 bit*/
    uint8_t fir_filter_parameters;    /*1 bit*/
    uint8_t quant_step_sizes;         /*1 bit*/
    uint8_t output_shifts;            /*1 bit*/
    uint8_t matrix_parameters;        /*1 bit*/
    uint8_t block_size;               /*1 bit*/
};

struct mlp_Matrix {
    uint8_t out_channel;                    /*4 bits*/
    uint8_t fractional_bits;                /*4 bits*/
    uint8_t lsb_bypass;                     /*1 bit*/
    int32_t coefficients[MAX_MLP_CHANNELS]; /*each 'fractional_bits' + 2*/
    struct i_array bypassed_lsbs;           /*1 bit per PCM frame*/
};

struct mlp_MatrixParameters {
    uint8_t count;                 /*4 bits*/
    struct mlp_Matrix matrices[MAX_MLP_MATRICES];
};

struct mlp_FilterParameters {
    struct i_array coefficients;  /*1 per "order"*/
    uint32_t shift;               /*4 bits*/
    uint8_t has_state;            /*1 bit*/
    struct i_array state;         /*1 per "order", if "has_state"*/
};

struct mlp_ChannelParameters {
    struct mlp_FilterParameters fir_filter_parameters;
    struct mlp_FilterParameters iir_filter_parameters;
    int16_t huffman_offset;         /*15 bits*/
    /* int32_t signed_huffman_offset; */
    uint8_t codebook;                /*2 bits*/
    uint8_t huffman_lsbs;            /*5 bits*/
};

struct mlp_DecodingParameters {
    struct mlp_ParameterPresentFlags parameters_present_flags; /*8 bits*/
    uint16_t block_size;                              /*9 bits*/
    struct mlp_MatrixParameters matrix_parameters;
    int8_t output_shifts[MAX_MLP_CHANNELS];           /*4 bits each*/
    uint8_t quant_step_sizes[MAX_MLP_CHANNELS];       /*4 bits each*/

    /*1 per substream channel*/
    struct mlp_ChannelParameters channel_parameters[MAX_MLP_CHANNELS];
};

typedef struct {
#ifndef STANDALONE
    PyObject_HEAD
#endif

    Bitstream* bitstream;

    int init_ok;
    int stream_closed;
    int64_t remaining_samples;

    uint64_t bytes_read;
    uint8_t parity;
    uint8_t crc;
    uint8_t final_crc;

    /*the stream's initial major sync*/
    struct mlp_MajorSync major_sync;

    /*the latest size for a given substream*/
    struct mlp_SubstreamSize* substream_sizes;

    /*the latest restart header for a given substream*/
    struct mlp_RestartHeader* restart_headers;

    /*the latest decoding parameters for a given substream*/
    struct mlp_DecodingParameters* decoding_parameters;

    /*raw, unfiltered residuals from a given block*/
    struct ia_array unfiltered_residuals;

    /*filtered data from a given block*/
    struct ia_array filtered_residuals;

    /*decoded and filtered samples for all substreams*/
    struct ia_array substream_samples;

    /*combined array of all substreams*/
    struct ia_array frame_samples;

    /*combined array of several frame_samples*/
    struct ia_array multi_frame_samples;
} decoders_MLPDecoder;

typedef enum {MLP_MAJOR_SYNC_OK,
              MLP_MAJOR_SYNC_NOT_FOUND,
              MLP_MAJOR_SYNC_INVALID,
              MLP_MAJOR_SYNC_ERROR} mlp_major_sync_status;

typedef enum {OK, ERROR} mlp_status;

/*called on each byte read from the stream
  and used to calculcate parity, checksums and frame sizes*/
void mlp_byte_callback(uint8_t byte, void* ptr);

int mlp_sample_rate(struct mlp_MajorSync* major_sync);

int mlp_bits_per_sample(struct mlp_MajorSync* major_sync);

int mlp_channel_count(struct mlp_MajorSync* major_sync);

int
mlp_channel_mask(struct mlp_MajorSync* major_sync);

#ifndef STANDALONE
/*the MLPDecoder.sample_rate attribute getter*/
static PyObject*
MLPDecoder_sample_rate(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.bits_per_sample attribute getter*/
static PyObject*
MLPDecoder_bits_per_sample(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.channels attribute getter*/
static PyObject*
MLPDecoder_channels(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.channel_mask attribute getter*/
static PyObject*
MLPDecoder_channel_mask(decoders_MLPDecoder *self, void *closure);

/*the MLPDecoder.read() method*/
static PyObject*
MLPDecoder_read(decoders_MLPDecoder* self, PyObject *args);

/*the MLPDecoder.analyze_frame() method*/
static PyObject*
MLPDecoder_analyze_frame(decoders_MLPDecoder* self, PyObject *args);

/*Reads a substream and returns a Python object of its values*/
PyObject*
mlp_analyze_substream(decoders_MLPDecoder* decoder,
                      int substream);

/*the MLPDecoder.close() method*/
static PyObject*
MLPDecoder_close(decoders_MLPDecoder* self, PyObject *args);

/*the MLPDecoder.__init__() method*/
int
MLPDecoder_init(decoders_MLPDecoder *self,
                PyObject *args, PyObject *kwds);

PyGetSetDef MLPDecoder_getseters[] = {
    {"sample_rate",
     (getter)MLPDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)MLPDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)MLPDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)MLPDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef MLPDecoder_methods[] = {
    {"read", (PyCFunction)MLPDecoder_read,
     METH_VARARGS,
     "Reads the given number of bytes from the MLP file, if possible"},
    {"analyze_frame", (PyCFunction)MLPDecoder_analyze_frame,
     METH_NOARGS, "Returns the analysis of the next frame"},
    {"close", (PyCFunction)MLPDecoder_close,
     METH_NOARGS, "Closes the MLP decoder stream"},
    {NULL}
};

void
MLPDecoder_dealloc(decoders_MLPDecoder *self);

static PyObject*
MLPDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds);

PyTypeObject decoders_MLPDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.MLPDecoder",    /*tp_name*/
    sizeof(decoders_MLPDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)MLPDecoder_dealloc, /*tp_dealloc*/
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
    "MLPDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    MLPDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    MLPDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)MLPDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    MLPDecoder_new,            /* tp_new */
};
#endif

/*Returns the total size of the next MLP frame
  or -1 if the end of the stream has been reached.*/
int
mlp_total_frame_size(Bitstream* bitstream);

/*Tries to read the next major sync from the bitstream.
  Returns MLP_MAJOR_SYNC_OK if successful,
  MLP_MAJOR_SYNC_NOT_FOUND if a major sync is not found,
  MLP_MAJOR_SYNC_ERROR if an error occurs when reading the bitstream.
  If a sync is not found, the stream is rewound to the starting position.*/
mlp_major_sync_status
mlp_read_major_sync(decoders_MLPDecoder* decoder,
                    struct mlp_MajorSync* major_sync);

/*Reads an entire MLP frame and combines its
  substream samples into a single block of channels/samples.
  Returns the frame's total size upon success,
  0 on EOF or -1 if an error occurs.*/
int
mlp_read_frame(decoders_MLPDecoder* decoder,
               struct ia_array* frame_samples);

/*Reads a 16-bit substream size value.*/
mlp_status
mlp_read_substream_size(Bitstream* bitstream,
                        struct mlp_SubstreamSize* size);

/*Reads a substream and its optional parity/checksum*/
mlp_status
mlp_read_substream(decoders_MLPDecoder* decoder,
                   int substream,
                   struct ia_array* samples);

unsigned int
mlp_substream_channel_count(decoders_MLPDecoder* decoder,
                            int substream);

/*Reads a block along with optional restart header and decoding parameters
  and performs FIR/IIR filtering on it before placing the results in
  "block_data".*/
mlp_status
mlp_read_block(decoders_MLPDecoder* decoder,
               int substream,
               struct ia_array* block_data,
               int* last_block);

/*Reads a block along with optional restart header and decoding parameters
  and places the result in "block_data".
  Unlike mlp_read_block, this does not perform FIR/IIR filtering on the
  results so that unfiltered residuals can be fed to analyze_substream*/
mlp_status
mlp_analyze_block(decoders_MLPDecoder* decoder,
                  int substream,
                  struct ia_array* block_data,
                  int* last_block);


mlp_status
mlp_read_restart_header(Bitstream* bs,
                        struct mlp_DecodingParameters* parameters,
                        struct mlp_RestartHeader* header);

mlp_status
mlp_read_decoding_parameters(Bitstream* bs,
                             int min_channel,
                             int max_channel,
                             int max_matrix_channel,
                             struct mlp_DecodingParameters* parameters);

mlp_status
mlp_read_channel_parameters(Bitstream* bs,
                            struct mlp_ParameterPresentFlags* flags,
                            uint8_t quant_step_size,
                            struct mlp_ChannelParameters* parameters);

mlp_status
mlp_read_matrix_parameters(Bitstream* bs,
                           int substream_channel_count,
                           struct mlp_MatrixParameters* parameters);

mlp_status
mlp_read_fir_filter_parameters(Bitstream* bs,
                               struct mlp_FilterParameters* fir);

mlp_status
mlp_read_iir_filter_parameters(Bitstream* bs,
                               struct mlp_FilterParameters* iir);

int32_t
mlp_calculate_signed_offset(uint8_t codebook,
                            uint8_t huffman_lsbs,
                            int16_t huffman_offset,
                            uint8_t quant_step_size);

mlp_status
mlp_read_residuals(Bitstream* bs,
                   struct mlp_DecodingParameters* parameters,
                   int min_channel,
                   int max_channel,
                   struct ia_array* residuals);

mlp_status
mlp_filter_channels(struct ia_array* unfiltered,
                    int min_channel,
                    int max_channel,
                    struct mlp_DecodingParameters* parameters,
                    struct ia_array* filtered);

mlp_status
mlp_filter_channel(struct i_array* unfiltered,
                   struct mlp_FilterParameters* fir_filter,
                   struct mlp_FilterParameters* iir_filter,
                   uint8_t quant_step_size,
                   struct i_array* filtered);


/*generates a pair of noise channels based on
  the number of PCM frames, noise seed and noise shift*/
void
mlp_noise_channels(unsigned int pcm_frames,
                   uint32_t* noise_gen_seed,
                   uint8_t noise_shift,
                   struct i_array* noise_channel1,
                   struct i_array* noise_channel2);


/*modifies the values of "channels" to be rematrixed
  for each matrix in the list of matrices*/
void
mlp_rematrix_channels(struct ia_array* channels,
                      int max_matrix_channel,
                      uint32_t* noise_gen_seed,
                      uint8_t noise_shift,
                      struct mlp_MatrixParameters* matrices,
                      uint8_t* quant_step_sizes);

/*modifies the values of "channels" to be rematrixed
  for a single set of matrix values*/
void
mlp_rematrix_channel(struct ia_array* channels,
                     int max_matrix_channel,
                     struct i_array* noise_channel1,
                     struct i_array* noise_channel2,
                     struct mlp_Matrix* matrix,
                     uint8_t* quant_step_sizes);
