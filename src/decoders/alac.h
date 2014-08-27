#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

#define MAX_CHANNELS 8

struct alac_subframe_header {
    unsigned prediction_type;
    unsigned qlp_shift_needed;
    unsigned rice_modifier;
    a_int* qlp_coeff;
};

struct alac_stts {
    unsigned frame_count;
    unsigned frame_duration;
};

struct alac_stsc {
    unsigned first_chunk;
    unsigned ALAC_frames_per_chunk;
    unsigned description_index;
};

struct alac_seektable {
    unsigned pcm_frames_offset;
    unsigned absolute_file_offset;
};

typedef struct {
#ifndef STANDALONE
    PyObject_HEAD
#endif

    char* filename;
    FILE* file;
    BitstreamReader* bitstream;

    unsigned int sample_rate;
    unsigned int channels;
    unsigned int bits_per_sample;

    int closed;
    unsigned int total_frames;
    unsigned int remaining_frames;

    /*a bunch of decoding fields pulled from the stream's 'alac' atom*/
    unsigned int max_samples_per_frame;
    unsigned int history_multiplier;
    unsigned int initial_history;
    unsigned int maximum_k;

    /*a compiled seektable from the three seektable atoms*/
    a_obj* seektable;

    aa_int* frameset_channels;
    aa_int* frame_channels;
    a_int* uncompressed_LSBs;
    a_int* residuals;
    struct alac_subframe_header subframe_headers[MAX_CHANNELS];

#ifndef STANDALONE
    /*a framelist generator*/
    PyObject* audiotools_pcm;
#endif
} decoders_ALACDecoder;

typedef enum {OK,
              IO_ERROR,
              INVALID_UNUSED_BITS,
              INVALID_ALAC_ATOM,
              INVALID_MDHD_ATOM,
              MDIA_NOT_FOUND,
              STSD_NOT_FOUND,
              MDHD_NOT_FOUND,
              INVALID_SEEKTABLE} status;

#ifndef STANDALONE
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

static PyObject*
ALACDecoder_seek(decoders_ALACDecoder* self, PyObject *args);

/*the ALACDecoder.close() method*/
static PyObject*
ALACDecoder_close(decoders_ALACDecoder* self, PyObject *args);

/*the ALACDecoder.__init__() method*/
int
ALACDecoder_init(decoders_ALACDecoder *self,
                 PyObject *args, PyObject *kwds);

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
     "Reads the given number of PCM frames from the ALAC file, if possible"},
    {"seek", (PyCFunction)ALACDecoder_seek,
     METH_VARARGS, "Seeks to the given PCM offset"},
    {"close", (PyCFunction)ALACDecoder_close,
     METH_NOARGS, "Closes the ALAC decoder stream"},
    {NULL}
};

void
ALACDecoder_dealloc(decoders_ALACDecoder *self);

PyObject*
ALACDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

PyObject*
alac_exception(status status);

PyTypeObject decoders_ALACDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
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

#endif

const char*
alac_strerror(status status);

static status
parse_decoding_parameters(decoders_ALACDecoder *self);

/*given a rewound BitstreamReader,
  walks through the open QuickTime stream looking for the 'mdat' atom
  or returns ERROR if one cannot be found*/
static status
seek_mdat(BitstreamReader* alac_stream);

/*swaps the ALAC-ordered set of channels to Wave order,
  depending on the number of ALAC-ordered channels*/
static void
alac_order_to_wave_order(aa_int* alac_ordered);

/*appends 1 or 2 channels worth of data from the current bitstream
  to the "samples" arrays
  returns OK on success
  or returns ERROR and sets self->error_message if some problem occurs*/
static status
read_frame(decoders_ALACDecoder *self,
           BitstreamReader *mdat,
           aa_int* frameset_channels,
           unsigned channel_count);

/*reads "subframe header" from the current bitstream*/
static void
read_subframe_header(BitstreamReader *bs,
                     struct alac_subframe_header *subframe_header);

/*reads a block of residuals from the current bitstream*/
static void
read_residuals(BitstreamReader *bs,
               a_int* residuals,
               unsigned int residual_count,
               unsigned int sample_size,
               unsigned int initial_history,
               unsigned int history_multiplier,
               unsigned int maximum_k);

/*reads an unsigned residual from the current bitstream*/
static unsigned
read_residual(BitstreamReader *bs,
              unsigned int lsb_count,
              unsigned int sample_size);

/*decodes the given residuals, QLP coefficient values and shift needed
  to the given samples*/
static void
decode_subframe(a_int* samples,
                unsigned sample_size,
                a_int* residuals,
                a_int* qlp_coeff,
                uint8_t qlp_shift_needed);

/*decorrelates 2 channels, in-place*/
static void
decorrelate_channels(a_int* left,
                     a_int* right,
                     unsigned interlacing_shift,
                     unsigned interlacing_leftweight);

/*returns 0 if the given sub atom name is found in the parent
  and sets "sub_atom" to that atom data and "sub_atom_size" to its size
  (not including the 64 bit header)
  returns 1 if the sub atom is not found in the parent*/
int
find_atom(BitstreamReader* parent,
          BitstreamReader* sub_atom, unsigned* sub_atom_size,
          const char* sub_atom_name);

/*returns 0 if the given sub atom path is found in the parent
  and sets "sub_atom" to that atom data and "sub_atom_size" to its size
  (not including the 64 bit header)
  returns 1 if the sub atom path is not found in the parent*/
int
find_sub_atom(BitstreamReader* parent,
              BitstreamReader* sub_atom, unsigned* sub_atom_size,
              ...);

void
swap_readers(BitstreamReader** a, BitstreamReader** b);

status
read_alac_atom(BitstreamReader* stsd_atom,
               unsigned int* max_samples_per_frame,
               unsigned int* bits_per_sample,
               unsigned int* history_multiplier,
               unsigned int* initial_history,
               unsigned int* maximum_k,
               unsigned int* channels,
               unsigned int* sample_rate);

status
read_mdhd_atom(BitstreamReader* mdhd_atom,
               unsigned int* total_frames);

static struct alac_stts*
alac_stts_copy(struct alac_stts* stts);

static void
alac_stts_print(struct alac_stts* stts, FILE* output);

/*reads a list of alac_stts structs from the "stts" atom
  to "block_sizes"*/
static status
read_stts_atom(BitstreamReader* stts_atom, a_obj* block_sizes);

static struct alac_stsc*
alac_stsc_copy(struct alac_stsc* stsc);

static void
alac_stsc_print(struct alac_stsc* stsc, FILE* output);

/*reads a list of alac_stsc structs from the "stsc" atom
  to "chunk_sizes"*/
static status
read_stsc_atom(BitstreamReader* stsc_atom, a_obj* chunk_sizes);

/*reads a list of chunk offsets from the "stco" atom
  to "chunk_offsets"*/
static status
read_stco_atom(BitstreamReader* stco_atom, a_unsigned* chunk_offsets);

static struct alac_seektable*
alac_seektable_copy(struct alac_seektable *entry);

static void
alac_seektable_print(struct alac_seektable *entry, FILE *output);

static status
populate_seektable(a_obj* block_sizes,
                   a_obj* chunk_sizes,
                   a_unsigned* chunk_offsets,
                   a_obj* seektable);
