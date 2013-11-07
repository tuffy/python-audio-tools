#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"
#include "../common/md5.h"
#include "../common/flac_crc.h"

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

struct flac_STREAMINFO {
    unsigned minimum_block_size;  /*16  bits*/
    unsigned maximum_block_size;  /*16  bits*/
    unsigned minimum_frame_size;  /*24  bits*/
    unsigned maximum_frame_size;  /*24  bits*/
    unsigned sample_rate;         /*20  bits*/
    unsigned channels;            /*3   bits*/
    unsigned bits_per_sample;     /*5   bits*/
    uint64_t total_samples;       /*36  bits*/
    uint8_t md5sum[16];           /*128 bits*/
};

struct flac_SEEKPOINT {
    uint64_t sample_number;       /*64 bits*/
    uint64_t byte_offset;         /*64 bits*/
    unsigned samples;             /*16 bits*/
};

struct flac_frame_header {
    unsigned blocking_strategy;
    unsigned block_size;
    unsigned sample_rate;
    unsigned channel_assignment;
    unsigned channel_count;
    unsigned bits_per_sample;
    unsigned frame_number;
};

typedef enum {FLAC_SUBFRAME_CONSTANT,
              FLAC_SUBFRAME_VERBATIM,
              FLAC_SUBFRAME_FIXED,
              FLAC_SUBFRAME_LPC} flac_subframe_type;

struct flac_subframe_header {
    flac_subframe_type type;
    unsigned order;
    unsigned wasted_bits_per_sample;
};

typedef enum {OK,
              ERROR,
              ERR_INVALID_SYNC_CODE,
              ERR_INVALID_RESERVED_BIT,
              ERR_INVALID_BITS_PER_SAMPLE,
              ERR_INVALID_SAMPLE_RATE,
              ERR_INVALID_FRAME_CRC,
              ERR_SAMPLE_RATE_MISMATCH,
              ERR_CHANNEL_COUNT_MISMATCH,
              ERR_BITS_PER_SAMPLE_MISMATCH,
              ERR_MAXIMUM_BLOCK_SIZE_EXCEEDED,
              ERR_INVALID_CODING_METHOD,
              ERR_INVALID_FIXED_ORDER,
              ERR_INVALID_SUBFRAME_TYPE} flac_status;

#ifndef STANDALONE
typedef struct {
    PyObject_HEAD

    PyObject* file;
    BitstreamReader* bitstream;
    int channel_mask;

    struct flac_STREAMINFO streaminfo;
    a_obj* seektable;
    uint64_t remaining_samples;
    int closed;

    audiotools__MD5Context md5;
    int perform_validation;
    int stream_finalized;

    /*temporary buffers we don't want to reallocate each time*/
    aa_int* subframe_data;
    a_int* residuals;
    a_int* qlp_coeffs;
    a_int* framelist_data;

    /*a framelist generator*/
    PyObject* audiotools_pcm;
} decoders_FlacDecoder;

/*the FlacDecoder.sample_rate attribute getter*/
static PyObject*
FlacDecoder_sample_rate(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.bits_per_sample attribute getter*/
static PyObject*
FlacDecoder_bits_per_sample(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.channels attribute getter*/
static PyObject*
FlacDecoder_channels(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.channel_mask attribute getter*/
static PyObject*
FlacDecoder_channel_mask(decoders_FlacDecoder *self, void *closure);

/*the FlacDecoder.read() method*/
static PyObject*
FlacDecoder_read(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_seek(decoders_FlacDecoder* self, PyObject *args);

static PyObject*
FlacDecoder_offsets(decoders_FlacDecoder* self, PyObject *args);

/*the FlacDecoder.close() method*/
static PyObject*
FlacDecoder_close(decoders_FlacDecoder* self, PyObject *args);

/*the FlacDecoder.__init__() method*/
int
FlacDecoder_init(decoders_FlacDecoder *self,
                 PyObject *args, PyObject *kwds);

PyGetSetDef FlacDecoder_getseters[] = {
    {"sample_rate",
     (getter)FlacDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)FlacDecoder_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)FlacDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)FlacDecoder_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef FlacDecoder_methods[] = {
    {"read", (PyCFunction)FlacDecoder_read,
     METH_VARARGS,
     "Reads the given number of PCM frames from the FLAC file, if possible"},
    {"seek", (PyCFunction)FlacDecoder_seek,
     METH_VARARGS, "Tries to seek to the given PCM frames offset"},
    {"offsets", (PyCFunction)FlacDecoder_offsets,
     METH_NOARGS, "Returns a list of (offset, PCM frame count) values"},
    {"close", (PyCFunction)FlacDecoder_close,
     METH_NOARGS, "Closes the FLAC decoder stream"},
    {NULL}
};

void
FlacDecoder_dealloc(decoders_FlacDecoder *self);

static PyObject*
FlacDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

/*reads the STREAMINFO, SEEKTABLE and VORBIS_COMMENT blocks,
  skips any other metadata blocks,
  placing our internal stream at the first FLAC frame

  returns 0 on success, 1 on failure with PyErr set*/
int
flacdec_read_metadata(BitstreamReader *bitstream,
                      struct flac_STREAMINFO *streaminfo,
                      a_obj* seektable,
                      int *channel_mask);
#endif

/*reads a FLAC frame header from the sync code to the CRC-8
  and places the result in "header"*/
flac_status
flacdec_read_frame_header(BitstreamReader *bitstream,
                          struct flac_STREAMINFO *streaminfo,
                          struct flac_frame_header *header);

/*reads a FLAC subframe header from the padding bit to the wasted bps (if any)
  and places the result in "subframe_header"*/
flac_status
flacdec_read_subframe_header(BitstreamReader *bitstream,
                             struct flac_subframe_header *subframe_header);

/*returns a subframe's effective bits per sample
  based on the frame header and whether the subframe
  is the side channel in left-side/side-right/mid-side encoding*/
unsigned int
flacdec_subframe_bits_per_sample(struct flac_frame_header *frame_header,
                                 unsigned int channel_number);

/*reads a FLAC subframe from bitstream
  with block_size and effective bits_per_sample
  and places the result in "samples"

  "qlp_coeffs" and "residuals" are temporary buffers
  to be recycled as needed*/
flac_status
flacdec_read_subframe(BitstreamReader* bitstream,
                      a_int* qlp_coeffs,
                      a_int* residuals,
                      unsigned block_size,
                      unsigned bits_per_sample,
                      a_int* samples);

/*the following four functions are called by FlacDecoder_read_subframe
  depending on the subframe type in the subframe header
  all take the same arguments as FlacDecoder_read_subframe
  and, for fixed and lpc, an "order" argument - also from the subframe header*/
flac_status
flacdec_read_constant_subframe(BitstreamReader* bitstream,
                               unsigned block_size,
                               unsigned bits_per_sample,
                               a_int* samples);

flac_status
flacdec_read_verbatim_subframe(BitstreamReader* bitstream,
                               unsigned block_size,
                               unsigned bits_per_sample,
                               a_int* samples);

flac_status
flacdec_read_fixed_subframe(BitstreamReader* bitstream,
                            a_int* residuals,
                            unsigned order,
                            unsigned block_size,
                            unsigned bits_per_sample,
                            a_int* samples);

flac_status
flacdec_read_lpc_subframe(BitstreamReader* bitstream,
                          a_int* qlp_coeffs,
                          a_int* residuals,
                          unsigned order,
                          unsigned block_size,
                          unsigned bits_per_sample,
                          a_int* samples);

/*reads a chunk of residuals with the given "order" and "block_size"
  (determined from read_fixed_subframe or read_lpc_subframe)
  and places the result in "residuals"*/
flac_status
flacdec_read_residual(BitstreamReader* bitstream,
                      unsigned order,
                      unsigned block_size,
                      a_int* residuals);

void
flacdec_decorrelate_channels(unsigned channel_assignment,
                             const aa_int* subframes,
                             a_int* framelist);

const char*
FlacDecoder_strerror(flac_status error);

unsigned read_utf8(BitstreamReader *stream);

struct flac_SEEKPOINT*
seekpoint_copy(struct flac_SEEKPOINT* seekpoint);

#ifndef STANDALONE

flac_status
FlacDecoder_update_md5sum(decoders_FlacDecoder *self,
                          PyObject *framelist);

int
FlacDecoder_verify_okay(decoders_FlacDecoder *self);

#ifdef IS_PY3K

static PyTypeObject decoders_FlacDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.FlacDecoder",     /* tp_name */
    sizeof(decoders_FlacDecoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)FlacDecoders_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,       /* tp_flags */
    "FlacDecoder objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    FlacDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    FlacDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FlacDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    FlacDecoder_new,           /* tp_new */
};

#else

PyTypeObject decoders_FlacDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.FlacDecoder",    /*tp_name*/
    sizeof(decoders_FlacDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FlacDecoder_dealloc, /*tp_dealloc*/
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
    "FlacDecoder objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    FlacDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    FlacDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FlacDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    FlacDecoder_new,           /* tp_new */
};

#endif
#endif
