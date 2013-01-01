#ifndef A_SHN_ENCODE
#define A_SHN_ENCODE
#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include <setjmp.h>
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

    unsigned frame_byte_size;
    unsigned mdat_byte_size;
    array_ia* frame_log;

    array_i* LSBs;
    array_ia* channels_MSB;

    array_ia* correlated_channels;
    array_i* qlp_coefficients0;
    array_i* qlp_coefficients1;
    BitstreamWriter *residual0;
    BitstreamWriter *residual1;

    array_f* tukey_window;
    array_f* windowed_signal;
    array_f* autocorrelation_values;
    array_fa* lp_coefficients;
    array_i* qlp_coefficients4;
    array_i* qlp_coefficients8;
    array_i* residual_values4;
    array_i* residual_values8;
    BitstreamWriter *residual_block4;
    BitstreamWriter *residual_block8;

    BitstreamWriter *compressed_frame;
    BitstreamWriter *interlaced_frame;
    BitstreamWriter *best_interlaced_frame;

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
               array_ia* channels);

/*write a single ALAC frame, compressed or uncompressed as necessary*/
static void
write_frame(BitstreamWriter *bs,
            struct alac_context* encoder,
            const array_ia* channels);

/*writes a single uncompressed ALAC frame, not including the channel count*/
static void
write_uncompressed_frame(BitstreamWriter *bs,
                         struct alac_context* encoder,
                         const array_ia* channels);

static void
write_compressed_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       const array_ia* channels);

static void
write_non_interlaced_frame(BitstreamWriter *bs,
                           struct alac_context* encoder,
                           unsigned uncompressed_LSBs,
                           const array_i* LSBs,
                           const array_ia* channels);

static void
correlate_channels(const array_ia* channels,
                   unsigned interlacing_shift,
                   unsigned interlacing_leftweight,
                   array_ia* correlated_channels);

static void
write_interlaced_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned uncompressed_LSBs,
                       const array_i* LSBs,
                       unsigned interlacing_shift,
                       unsigned interlacing_leftweight,
                       const array_ia* channels);

static void
compute_coefficients(struct alac_context* encoder,
                     const array_i* samples,
                     unsigned sample_size,
                     array_i* qlp_coefficients,
                     BitstreamWriter *residual);

/*given a set of integer samples,
  returns a windowed set of floating point samples*/
static void
window_signal(struct alac_context* encoder,
              const array_i* samples,
              array_f* windowed_signal);

/*given a set of windowed samples and a maximum LPC order,
  returns a set of autocorrelation values whose length is 9*/
static void
autocorrelate(const array_f* windowed_signal,
              array_f* autocorrelation_values);

/*given a maximum LPC order of 8
  and set of autocorrelation values whose length is 9
  returns list of LP coefficient lists whose length is max_lpc_order*/
static void
compute_lp_coefficients(const array_f* autocorrelation_values,
                        array_fa* lp_coefficients);

static void
quantize_coefficients(const array_fa* lp_coefficients,
                      unsigned order,
                      array_i* qlp_coefficients);

static void
write_subframe_header(BitstreamWriter *bs,
                      const array_i* qlp_coefficients);

static void
calculate_residuals(const array_i* samples,
                    unsigned sample_size,
                    const array_i* qlp_coefficients,
                    array_i* residuals);

static void
encode_residuals(struct alac_context* encoder,
                 unsigned sample_size,
                 const array_i* residuals,
                 BitstreamWriter *residual_block);

static void
write_residual(unsigned value, unsigned k, unsigned sample_size,
               BitstreamWriter* residual);

#endif
