#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"

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
              END_OF_STREAM,
              IOERROR,
              UNKNOWN_COMMAND,
              INVALID_MAGIC_NUMBER,
              INVALID_SHORTEN_VERSION,
              UNSUPPORTED_FILE_TYPE} status;

#define COMMAND_SIZE 2
#define ENERGY_SIZE 3
#define LPC_COUNT_SIZE 2
#define LPC_COEFF_SIZE 5
#define VERBATIM_CHUNK_SIZE 5
#define VERBATIM_BYTE_SIZE 8
#define SHIFT_SIZE 2

#define QLPC_SIZE 2
#define QLPC_QUANT 5
#define QLPC_OFFSET (1 << QLPC_QUANT);

enum {FN_DIFF0     = 0,
      FN_DIFF1     = 1,
      FN_DIFF2     = 2,
      FN_DIFF3     = 3,
      FN_QUIT      = 4,
      FN_BLOCKSIZE = 5,
      FN_BITSHIFT  = 6,
      FN_QLPC      = 7,
      FN_ZERO      = 8,
      FN_VERBATIM  = 9};

typedef struct {
#ifndef STANDALONE
    PyObject_HEAD
    PyObject *file;
#endif

    BitstreamReader* bitstream;

    /*fixed fields from the Shorten header*/
    struct {
        unsigned file_type;
        unsigned channels;
        unsigned max_LPC;
        unsigned mean_count;
    } header;

    /*fields which may change during decoding*/
    unsigned block_length;
    unsigned left_shift;

    /*derived fields about the stream itself*/
    unsigned bits_per_sample;
    unsigned signed_samples;
    unsigned sample_rate;
    unsigned channel_mask;
    int stream_finished;

    /*values that persist between commands*/
    aa_int* means;
    aa_int* previous_samples;

    /*temporary buffers we don't want to allocate all the time*/
    aa_int* unshifted;
    aa_int* samples;
    a_int* pcm_header;
    a_int* pcm_footer;

#ifndef STANDALONE
    /*a framelist generator*/
    PyObject* audiotools_pcm;
#endif

    /*a marker to indicate the stream has been explicitly closed*/
    int closed;
} decoders_SHNDecoder;

#ifndef STANDALONE
PyObject*
SHNDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

/*the SHNDecoder.__init__() method*/
int
SHNDecoder_init(decoders_SHNDecoder *self, PyObject *args, PyObject *kwds);

void SHNDecoder_dealloc(decoders_SHNDecoder *self);

/*the SHNDecoder.close() method*/
static PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args);

/*the SHNDecoder.sample_rate attribute getter*/
static PyObject*
SHNDecoder_sample_rate(decoders_SHNDecoder *self, void *closure);

/*the SHNDecoder.bits_per_sample attribute getter*/
static PyObject*
SHNDecoder_bits_per_sample(decoders_SHNDecoder *self, void *closure);

/*the SHNDecoder.channels attribute getter*/
static PyObject*
SHNDecoder_channels(decoders_SHNDecoder *self, void *closure);

/*the SHNDecoder.channel_mask attribute getter*/
static PyObject*
SHNDecoder_channel_mask(decoders_SHNDecoder *self, void *closure);

/*the SHNDecoder.read() method*/
static PyObject*
SHNDecoder_read(decoders_SHNDecoder* self, PyObject *args);

/*returns a pair of strings before and after PCM data*/
static PyObject*
SHNDecoder_pcm_split(decoders_SHNDecoder* self, PyObject *args);

PyGetSetDef SHNDecoder_getseters[] = {
    {"channels",
     (getter)SHNDecoder_channels, NULL, "channels", NULL},
    {"bits_per_sample",
     (getter)SHNDecoder_bits_per_sample, NULL, "bits_per_sample", NULL},
    {"sample_rate",
     (getter)SHNDecoder_sample_rate, NULL, "sample_rate", NULL},
    {"channel_mask",
     (getter)SHNDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef SHNDecoder_methods[] = {
    {"read", (PyCFunction)SHNDecoder_read,
     METH_VARARGS, "Reads a frame of data from the SHN file"},
    {"close", (PyCFunction)SHNDecoder_close,
     METH_NOARGS, "Closes the SHN decoder stream"},
    {"pcm_split", (PyCFunction)SHNDecoder_pcm_split,
     METH_NOARGS, "Returns a pair of strings before and after PCM data"},
    {NULL}
};

PyTypeObject decoders_SHNDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.SHNDecoder",     /*tp_name*/
    sizeof(decoders_SHNDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)SHNDecoder_dealloc, /*tp_dealloc*/
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
    "SHNDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    SHNDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    SHNDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)SHNDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    SHNDecoder_new,            /* tp_new */
};
#endif

static status
read_shn_header(decoders_SHNDecoder* self, BitstreamReader* reader);

static void
process_iff_header(BitstreamReader* bs,
                   unsigned* sample_rate,
                   unsigned* channel_mask);

static status
read_framelist(decoders_SHNDecoder* self, aa_int* framelist);

/*given a list of samples and a set of means for the given channel,
  reads a DIFF0 command and sets samples to "block_length" values*/
static void
read_diff0(BitstreamReader* bs, unsigned block_length,
           const a_int* means, a_int* samples);

/*given a list of previous samples (which may be empty)
  reads a DIFF1 command with the given block length
  and sets samples to "block_length" values*/
static void
read_diff1(BitstreamReader* bs, unsigned block_length,
           a_int* previous_samples, a_int* samples);

/*given a list of previous samples (which may be empty)
  reads a DIFF2 command with the given block length
  and sets samples to "block_length" values*/
static void
read_diff2(BitstreamReader* bs, unsigned block_length,
           a_int* previous_samples, a_int* samples);

/*given a list of previous samples (which may be empty)
  reads a DIFF3 command with the given block length
  and sets samples to "block_length" values*/
static void
read_diff3(BitstreamReader* bs, unsigned block_length,
           a_int* previous_samples, a_int* samples);

static void
read_qlpc(BitstreamReader* bs, unsigned block_length,
          a_int* previous_samples, a_int* means, a_int* samples);

static int
shnmean(const a_int* values);

/*reads the contents of a VERBATIM command
  into a substream for parsing*/
static BitstreamReader*
read_verbatim(BitstreamReader* bs, unsigned* verbatim_size);

int
read_wave_header(BitstreamReader* bs, unsigned verbatim_size,
                 unsigned* sample_rate, unsigned* channel_mask);

int
read_aiff_header(BitstreamReader* bs, unsigned verbatim_size,
                 unsigned* sample_rate, unsigned* channel_mask);

int
read_ieee_extended(BitstreamReader* bs);

static unsigned
read_unsigned(BitstreamReader* bs, unsigned count);

static int
read_signed(BitstreamReader* bs, unsigned count);

static unsigned
read_long(BitstreamReader* bs);

static void
skip_unsigned(BitstreamReader* bs, unsigned count);

static void
skip_signed(BitstreamReader* bs, unsigned count);
