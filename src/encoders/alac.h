#ifndef A_ALAC_ENCODE
#define A_ALAC_ENCODE
#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include <setjmp.h>
#include <time.h>
#include "../pcmreader.h"
#include "../bitstream.h"

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

#define MAX_QLP_COEFFS 8

struct alac_frame_size {
    unsigned byte_size;
    unsigned pcm_frames_size;
    struct alac_frame_size *next;  /*NULL at end of list*/
};

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

    double *tukey_window;

    BitstreamRecorder *residual0;
    BitstreamRecorder *residual1;

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
init_encoder(struct alac_context* encoder, unsigned block_size);

/*deallocates all the temporary buffers in encoder*/
static void
free_encoder(struct alac_context* encoder);

/*encodes the mdat atom and returns a linked list of frame sizes

  if "total_pcm_frames" is 0, assume the total size of the input
  stream is unknown and write to a temporary file before
  encoding to output*/
static struct alac_frame_size*
encode_alac(BitstreamWriter *output,
            struct PCMReader *pcmreader,
            unsigned total_pcm_frames,
            int block_size,
            int initial_history,
            int history_multiplier,
            int maximum_k,
            const char encoder_version[]);

/*encodes the entire mdat atom and returns a linked list of frame sizes*/
static struct alac_frame_size*
encode_mdat(BitstreamWriter *output,
            struct PCMReader *pcmreader,
            int block_size,
            int initial_history,
            int history_multiplier,
            int maximum_k);

/*writes a full set of ALAC frames,
  complete with trailing stop '111' bits and byte-aligned*/
static void
write_frameset(BitstreamWriter *bs,
               struct alac_context* encoder,
               unsigned pcm_frames,
               unsigned channel_count,
               const int channels[]);

/*write a single ALAC frame, compressed or uncompressed as necessary*/
static void
write_frame(BitstreamWriter *bs,
            struct alac_context* encoder,
            unsigned pcm_frames,
            unsigned channel_count,
            const int channel0[],
            const int channel1[]);

/*writes a single uncompressed ALAC frame, not including the channel count*/
static void
write_uncompressed_frame(BitstreamWriter *bs,
                         struct alac_context* encoder,
                         unsigned pcm_frames,
                         unsigned channel_count,
                         const int channel0[],
                         const int channel1[]);

static void
write_compressed_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned pcm_frames,
                       unsigned channel_count,
                       const int channel0[],
                       const int channel1[]);

static void
write_non_interlaced_frame(BitstreamWriter *bs,
                           struct alac_context* encoder,
                           unsigned pcm_frames,
                           unsigned uncompressed_LSBs,
                           const int LSBs[],
                           const int channel0[]);

static void
write_interlaced_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned pcm_frames,
                       unsigned uncompressed_LSBs,
                       const int LSBs[],
                       unsigned interlacing_shift,
                       unsigned interlacing_leftweight,
                       const int channel0[],
                       const int channel1[]);

static void
correlate_channels(unsigned pcm_frames,
                   const int channel0[],
                   const int channel1[],
                   unsigned interlacing_shift,
                   unsigned interlacing_leftweight,
                   int correlated0[],
                   int correlated1[]);

static void
compute_coefficients(struct alac_context* encoder,
                     unsigned sample_count,
                     const int samples[],
                     unsigned sample_size,
                     unsigned *order,
                     int qlp_coefficients[],
                     BitstreamWriter *residual);

static void
tukey_window(double alpha, unsigned block_size, double *window);

/*given a set of integer samples,
  returns a windowed set of floating point samples*/
static void
window_signal(unsigned sample_count,
              const int samples[],
              const double window[],
              double windowed_signal[]);

/*given a set of windowed samples and a maximum LPC order,
  returns a set of autocorrelation values whose length is max_lpc_order + 1*/
static void
autocorrelate(unsigned sample_count,
              const double windowed_signal[],
              unsigned max_lpc_order,
              double autocorrelated[]);

/*given a maximum LPC order of 8
  and set of autocorrelation values whose length is 9
  returns list of LP coefficient lists whose length is max_lpc_order*/
static void
compute_lp_coefficients(unsigned max_lpc_order,
                        const double autocorrelated[],
                        double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS]);

static void
quantize_coefficients(unsigned order,
                      double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS],
                      int qlp_coefficients[]);

static void
write_subframe_header(BitstreamWriter *bs,
                      unsigned order,
                      const int qlp_coefficients[]);

static void
calculate_residuals(unsigned sample_size,
                    unsigned sample_count,
                    const int samples[],
                    unsigned order,
                    const int qlp_coefficients[],
                    int residuals[]);

static void
encode_residuals(struct alac_context* encoder,
                 BitstreamWriter *residual_block,
                 unsigned sample_size,
                 unsigned residual_count,
                 const int residuals[]);

static void
write_residual(BitstreamWriter* residual_block,
               unsigned value,
               unsigned k,
               unsigned sample_size);

static struct alac_frame_size*
dummy_frame_sizes(unsigned block_size, unsigned total_pcm_frames);

/*writes the metadata atoms which precede the file's "mdat" atom
  and returns the total size of those atoms in bytes*/
static unsigned
write_metadata(BitstreamWriter* bw,
               time_t timestamp,
               unsigned sample_rate,
               unsigned channels,
               unsigned bits_per_sample,
               unsigned total_pcm_frames,
               unsigned block_size,
               unsigned history_multiplier,
               unsigned initial_history,
               unsigned maximum_K,
               const struct alac_frame_size *frame_sizes,
               unsigned frames_offset,
               const char version[]);

#endif
