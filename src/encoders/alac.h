#ifndef A_ALAC_ENCODE
#define A_ALAC_ENCODE
#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include <setjmp.h>
#include "../bitstream.h"
#include "../array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

struct alac_encoding_options {
    unsigned block_size;
    unsigned initial_history;
    unsigned history_multiplier;
    unsigned maximum_k;
    unsigned minimum_interlacing_leftweight;
    unsigned maximum_interlacing_leftweight;
};

/*this is a container for encoding options and reusable data buffers*/
struct alac_context {
    struct alac_encoding_options options;

    unsigned bits_per_sample;

    a_unsigned* frame_sizes;
    unsigned total_pcm_frames;

    a_int* LSBs;
    aa_int* channels_MSB;

    aa_int* correlated_channels;
    a_int* qlp_coefficients0;
    a_int* qlp_coefficients1;
    BitstreamRecorder *residual0;
    BitstreamRecorder *residual1;

    a_double* tukey_window;
    a_double* windowed_signal;
    a_double* autocorrelation_values;
    aa_double* lp_coefficients;
    a_int* qlp_coefficients4;
    a_int* qlp_coefficients8;
    a_int* residual_values4;
    a_int* residual_values8;
    BitstreamRecorder *residual_block4;
    BitstreamRecorder *residual_block8;

    BitstreamRecorder *compressed_frame;
    BitstreamRecorder *interlaced_frame;
    BitstreamRecorder *best_interlaced_frame;

    /*set during write_frame
      in case a single residual value exceeds the maximum allowed
      when writing a compressed frame
      which means we need to write an uncompressed frame instead*/
    jmp_buf residual_overflow;
};

enum {LOG_SAMPLE_SIZE, LOG_BYTE_SIZE, LOG_FILE_OFFSET};

/*initializes all the temporary buffers in encoder*/
static void
init_encoder(struct alac_context* encoder);

/*deallocates all the temporary buffers in encoder*/
static void
free_encoder(struct alac_context* encoder);

#ifndef STANDALONE
PyObject
*alac_log_output(struct alac_context *encoder);
#endif

/*writes a full set of ALAC frames,
  complete with trailing stop '111' bits and byte-aligned*/
static void
write_frameset(BitstreamWriter *bs,
               struct alac_context* encoder,
               aa_int* channels);

/*write a single ALAC frame, compressed or uncompressed as necessary*/
static void
write_frame(BitstreamWriter *bs,
            struct alac_context* encoder,
            const aa_int* channels);

/*writes a single uncompressed ALAC frame, not including the channel count*/
static void
write_uncompressed_frame(BitstreamWriter *bs,
                         struct alac_context* encoder,
                         const aa_int* channels);

static void
write_compressed_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       const aa_int* channels);

static void
write_non_interlaced_frame(BitstreamWriter *bs,
                           struct alac_context* encoder,
                           unsigned uncompressed_LSBs,
                           const a_int* LSBs,
                           const aa_int* channels);

static void
correlate_channels(const aa_int* channels,
                   unsigned interlacing_shift,
                   unsigned interlacing_leftweight,
                   aa_int* correlated_channels);

static void
write_interlaced_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned uncompressed_LSBs,
                       const a_int* LSBs,
                       unsigned interlacing_shift,
                       unsigned interlacing_leftweight,
                       const aa_int* channels);

static void
compute_coefficients(struct alac_context* encoder,
                     const a_int* samples,
                     unsigned sample_size,
                     a_int* qlp_coefficients,
                     BitstreamWriter *residual);

/*given a set of integer samples,
  returns a windowed set of floating point samples*/
static void
window_signal(struct alac_context* encoder,
              const a_int* samples,
              a_double* windowed_signal);

/*given a set of windowed samples and a maximum LPC order,
  returns a set of autocorrelation values whose length is 9*/
static void
autocorrelate(const a_double* windowed_signal,
              a_double* autocorrelation_values);

/*given a maximum LPC order of 8
  and set of autocorrelation values whose length is 9
  returns list of LP coefficient lists whose length is max_lpc_order*/
static void
compute_lp_coefficients(const a_double* autocorrelation_values,
                        aa_double* lp_coefficients);

static void
quantize_coefficients(const aa_double* lp_coefficients,
                      unsigned order,
                      a_int* qlp_coefficients);

static void
write_subframe_header(BitstreamWriter *bs,
                      const a_int* qlp_coefficients);

static void
calculate_residuals(const a_int* samples,
                    unsigned sample_size,
                    const a_int* qlp_coefficients,
                    a_int* residuals);

static void
encode_residuals(struct alac_context* encoder,
                 unsigned sample_size,
                 const a_int* residuals,
                 BitstreamWriter *residual_block);

static void
write_residual(unsigned value, unsigned k, unsigned sample_size,
               BitstreamWriter* residual);

#ifndef STANDALONE

typedef struct {
    PyObject_HEAD

    struct alac_context encoder;
    PyObject *framelist_type;
    aa_int* channels;
    BitstreamRecorder* output_buffer;
} encoders_ALACEncoder;

static PyObject*
ALACEncoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

int
ALACEncoder_init(encoders_ALACEncoder *self,
                 PyObject *args, PyObject *kwds);

void
ALACEncoder_dealloc(encoders_ALACEncoder *self);

/*the ALAC.encode() method*/
static PyObject*
ALACEncoder_encode(encoders_ALACEncoder *self, PyObject *args);

PyGetSetDef ALACEncoder_getseters[] = {
    {NULL}
};

PyMethodDef ALACEncoder_methods[] = {
    {"encode", (PyCFunction)ALACEncoder_encode,
     METH_VARARGS, "encode(framelist) -> frame string"},
    {NULL}
};

PyTypeObject encoders_ALACEncoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "encoders.ALACEncoder",    /*tp_name*/
    sizeof(encoders_ALACEncoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ALACEncoder_dealloc, /*tp_dealloc*/
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
    "ALACEncoder objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ALACEncoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    ALACEncoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ALACEncoder_init,/* tp_init */
    0,                         /* tp_alloc */
    ALACEncoder_new,           /* tp_new */
};


#endif

#endif
