#include <Python.h>
#include <stdint.h>
#include "../bitstream.h"
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

typedef struct {
    PyObject_HEAD

    char* filename;
    FILE* file;
    BitstreamReader* bitstream;

    unsigned int sample_rate;
    unsigned int channels;
    unsigned int bits_per_sample;

    unsigned int total_samples;

    /*a bunch of decoding fields pulled from the stream's 'alac' atom*/
    unsigned int max_samples_per_frame;
    unsigned int history_multiplier;
    unsigned int initial_history;
    unsigned int maximum_k;

    struct ia_array samples; /*a sample buffer for an entire group of frames*/
    struct ia_array subframe_samples; /*a sample buffer for subframe output*/
    struct ia_array wasted_bits_samples;  /*a buffer for wasted-bits samples*/
    struct ia_array residuals; /*a buffer for residual values*/
    struct alac_subframe_header *subframe_headers;

    int data_allocated; /*indicates the init method allocated
                          the preceding ia_array and subframe header structs*/
} decoders_ALACDecoder;

struct alac_frame_header {
    uint8_t has_size;
    uint8_t wasted_bits;
    uint8_t is_not_compressed;
    uint32_t output_samples;
};

struct alac_subframe_header {
    uint8_t prediction_type;
    uint8_t prediction_quantitization;
    uint8_t rice_modifier;
    struct i_array predictor_coef_table;
};

typedef enum {OK, ERROR} status;

/*the ALACDecoder.sample_rate attribute getter*/
static PyObject*
ALACDecoder_sample_rate(decoders_ALACDecoder *self, void *closure);

/*the ALACDecoder.bits_per_sample attribute getter*/
static PyObject*
ALACDecoder_bits_per_sample(decoders_ALACDecoder *self, void *closure);

/*the ALACDecoder.channels attribute getter*/
static PyObject*
ALACDecoder_channels(decoders_ALACDecoder *self, void *closure);

/*the ALACDecoder.channel_mask attribute getter*/
static PyObject*
ALACDecoder_channel_mask(decoders_ALACDecoder *self, void *closure);

/*the ALACDecoder.read() method*/
static PyObject*
ALACDecoder_read(decoders_ALACDecoder* self, PyObject *args);

/*the ALACDecoder.analyze_frame() method*/
static PyObject*
ALACDecoder_analyze_frame(decoders_ALACDecoder* self, PyObject *args);

/*the ALACDecoder.close() method*/
static PyObject*
ALACDecoder_close(decoders_ALACDecoder* self, PyObject *args);

/*the ALACDecoder.__init__() method*/
int
ALACDecoder_init(decoders_ALACDecoder *self,
                 PyObject *args, PyObject *kwds);

int
ALACDecoder_parse_decoding_parameters(decoders_ALACDecoder *self);

/*walks through the open QuickTime stream looking for the 'mdat' atom
  or returns ERROR if one cannot be found*/
status
ALACDecoder_seek_mdat(BitstreamReader* alac_stream);

/*reads "frame_header" from the current bitstream*/
void
ALACDecoder_read_frame_header(BitstreamReader *bs,
                              struct alac_frame_header *frame_header,
                              unsigned int max_samples_per_frame);

/*reads "subframe header" from the current bitstream*/
void
ALACDecoder_read_subframe_header(BitstreamReader *bs,
                                 struct alac_subframe_header *subframe_header);

/*reads a block of "wasted_bits" samples from the current bitstream*/
void
ALACDecoder_read_wasted_bits(BitstreamReader *bs,
                             struct ia_array *wasted_bits_samples,
                             int sample_count,
                             int channels,
                             int wasted_bits_size);

/*reads a block of residuals from the current bitstream*/
void
ALACDecoder_read_residuals(BitstreamReader *bs,
                           struct i_array *residuals,
                           unsigned int residual_count,
                           unsigned int sample_size,
                           unsigned int initial_history,
                           unsigned int history_multiplier,
                           unsigned int maximum_k);

/*reads an unsigned residual from the current bitstream*/
unsigned int
ALACDecoder_read_residual(BitstreamReader *bs,
                          unsigned int lsb_count,
                          unsigned int sample_size);

/*takes a set of residuals, coefficients and a predictor_quantitization value
  returns a set of decoded samples*/
void
ALACDecoder_decode_subframe(struct i_array *samples,
                            struct i_array *residuals,
                            struct i_array *coefficients,
                            int predictor_quantitization);

void
ALACDecoder_decorrelate_channels(struct ia_array *output,
                                 struct ia_array *input,
                                 int interlacing_shift,
                                 int interlacing_leftweight);


/*simple routines*/
void
ALACDecoder_print_frame_header(FILE *output,
                               struct alac_frame_header *frame_header);

void
ALACDecoder_print_subframe_header(FILE *output,
                                struct alac_subframe_header *subframe_header);

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
     METH_VARARGS,
     "Reads the given number of bytes from the ALAC file, if possible"},
    {"analyze_frame", (PyCFunction)ALACDecoder_analyze_frame,
     METH_NOARGS, "Reads a single frame of analysis"},
    {"close", (PyCFunction)ALACDecoder_close,
     METH_NOARGS, "Closes the ALAC decoder stream"},
    {NULL}
};

void
ALACDecoder_dealloc(decoders_ALACDecoder *self);

PyObject*
ALACDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

PyTypeObject decoders_ALACDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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

/*returns 0 if the given sub atom name is found in the parent
  and sets "sub_atom" to that atom data and "sub_atom_size" to its size
  (not including the 64 bit header)
  returns 1 if the sub atom is not found in the parent*/
int
find_atom(BitstreamReader* parent,
          BitstreamReader* sub_atom, uint32_t* sub_atom_size,
          const char* sub_atom_name);

/*returns 0 if the given sub atom path is found in the parent
  and sets "sub_atom" to that atom data and "sub_atom_size" to its size
  (not including the 64 bit header)
  returns 1 if the sub atom path is not found in the parent*/
int
find_sub_atom(BitstreamReader* parent,
              BitstreamReader* sub_atom, uint32_t* sub_atom_size,
              ...);

void
swap_readers(BitstreamReader** a, BitstreamReader** b);

/*returns 0 if the atom is read successfully,
  1 on an I/O error,
  2 if there's a parsing error*/
int
read_alac_atom(BitstreamReader* stsd_atom,
               unsigned int* max_samples_per_frame,
               unsigned int* bits_per_sample,
               unsigned int* history_multiplier,
               unsigned int* initial_history,
               unsigned int* maximum_k,
               unsigned int* channels,
               unsigned int* sample_rate);

/*returns 0 if the atom is read successfully,
  1 on an I/O error,
  2 if the version is unsupported*/
int
read_mdhd_atom(BitstreamReader* mdhd_atom,
               unsigned int* total_frames);
