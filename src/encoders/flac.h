#ifndef A_FLAC_ENCODE
#define A_FLAC_ENCODE
#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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

struct flac_encoding_options {
    unsigned block_size;                    /*typically 1152 or 4096*/
    unsigned min_residual_partition_order;  /*typically 0*/
    unsigned max_residual_partition_order;  /*typically 3-6*/
    unsigned max_lpc_order;                 /*typically 0,6,8,12*/
    int exhaustive_model_search;            /*a boolean*/
    int mid_side;                           /*a boolean*/
    int adaptive_mid_side;                  /*a boolean*/

    int no_verbatim_subframes;              /*a boolean for debugging*/
    int no_constant_subframes;              /*a boolean for debugging*/
    int no_fixed_subframes;                 /*a boolean for debugging*/
    int no_lpc_subframes;                   /*a boolean for debugging*/

    unsigned qlp_coeff_precision;           /*derived from block size*/
    unsigned max_rice_parameter;            /*derived from bits-per-sample*/
};

struct flac_STREAMINFO {
    unsigned int minimum_block_size;  /* 16 bits*/
    unsigned int maximum_block_size;  /* 16 bits*/
    unsigned int minimum_frame_size;  /* 24 bits*/
    unsigned int maximum_frame_size;  /* 24 bits*/
    unsigned int sample_rate;         /* 20 bits*/
    unsigned int channels;            /*  3 bits*/
    unsigned int bits_per_sample;     /*  5 bits*/
    uint64_t total_samples;           /* 36 bits*/
    unsigned char md5sum[16];         /*128 bits*/
};

/*this is a container for encoding options, STREAMINFO
  and reusable data buffers*/
struct flac_context {
    struct flac_encoding_options options;
    struct flac_STREAMINFO streaminfo;
    unsigned int total_flac_frames;

    array_i* average_samples;
    array_i* difference_samples;
    BitstreamWriter* left_subframe;
    BitstreamWriter* right_subframe;
    BitstreamWriter* average_subframe;
    BitstreamWriter* difference_subframe;

    array_i* subframe_samples;

    BitstreamWriter* frame;
    BitstreamWriter* fixed_subframe;
    array_ia* fixed_subframe_orders;
    array_li* truncated_order;

    BitstreamWriter* lpc_subframe;
    array_f* tukey_window;
    array_f* windowed_signal;
    array_f* autocorrelation_values;
    array_fa* lp_coefficients;
    array_f* lp_error;
    array_i* qlp_coefficients;
    array_i* lpc_residual;

    array_i* best_partition_sizes;
    array_i* best_rice_parameters;
    array_i* partition_sizes;
    array_i* rice_parameters;
    array_li* remaining_residuals;
    array_li* residual_partition;
};

struct flac_frame_header {
    uint8_t blocking_strategy;
    uint32_t block_size;
    uint32_t sample_rate;
    uint8_t channel_assignment;
    uint8_t channel_count;
    uint8_t bits_per_sample;
    uint64_t frame_number;
};

typedef enum {FLAC_SUBFRAME_CONSTANT,
              FLAC_SUBFRAME_VERBATIM,
              FLAC_SUBFRAME_FIXED,
              FLAC_SUBFRAME_LPC} flac_subframe_type;

struct flac_subframe_header {
    flac_subframe_type type;
    uint8_t order;
    uint8_t wasted_bits_per_sample;
};

typedef enum {OK, ERROR} status;

#define MAX_FIXED_ORDER 4

/*initializes all the temporary buffers in encoder*/
void
flacenc_init_encoder(struct flac_context* encoder);

/*deallocates all the temporary buffers in encoder*/
void
flacenc_free_encoder(struct flac_context* encoder);

/*writes a STREAMINFO metadata block to the BitstreamWriter*/
void
flacenc_write_streaminfo(BitstreamWriter* bs,
                         const struct flac_STREAMINFO* streaminfo);

/*given a set of output samples
  along with STREAMINFO information and encoding parameters
  writes a complete frame to the given BitstreamWriter*/
void
flacenc_write_frame(BitstreamWriter* bs,
                    struct flac_context* encoder,
                    const array_ia* samples);

/*takes a list of samples and the subframe's bits-per-sample
  (which may differ from the frame's bits-per-sample)
  and encodes the best subframe to the given bitstream
  depending on encoding parameters*/
void
flacenc_write_subframe(BitstreamWriter* bs,
                       struct flac_context* encoder,
                       unsigned bits_per_sample,
                       const array_i* samples);

/*writes a UTF-8 value to the bitstream*/
void
write_utf8(BitstreamWriter *stream, unsigned int value);

/*an MD5 summing callback, updated when reading input strings*/
void
md5_update(void *data, unsigned char *buffer, unsigned long len);

/*determines the number of wasted bits in the given set of samples*/
unsigned
flacenc_max_wasted_bits_per_sample(const array_i* samples);

/*calculates the average/difference samples from
  a two channel set of samples*/
void
flacenc_average_difference(const array_ia* samples,
                           array_i* average,
                           array_i* difference);

/*writes a FLAC frame header with the given attributes
  to the given BitstreamWriter*/
void
flacenc_write_frame_header(BitstreamWriter* bs,
                           const struct flac_STREAMINFO *streaminfo,
                           unsigned block_size,
                           unsigned channel_assignment,
                           unsigned frame_number);

/*writes a CONSTANT subframe from the given sample
  to the given BitstreamWriter*/
void
flacenc_write_constant_subframe(BitstreamWriter* bs,
                                unsigned bits_per_sample,
                                unsigned wasted_bits_per_sample,
                                int sample);

/*writes a VERBATIM subframe from the given samples
  to the given BitstreamWriter*/
void
flacenc_write_verbatim_subframe(BitstreamWriter *bs,
                                unsigned bits_per_sample,
                                unsigned wasted_bits_per_sample,
                                const array_i* samples);

/*determines the best FIXED subframe order from the given samples
  and writes that subframe to the given BitstreamWriter*/
void
flacenc_write_fixed_subframe(BitstreamWriter* bs,
                             struct flac_context* encoder,
                             unsigned bits_per_sample,
                             unsigned wasted_bits_per_sample,
                             const array_i* samples);

/*a helper function for write_fixed_subframe
  which, given the residuals of one FIXED subframe order
  determines the residuals of the next order*/
void
flacenc_next_fixed_order(const array_i* order, array_i* next_order);

/*determines the best LPC subframe coefficients
  given a set of samples and encoding parameters
  and writes that subframe to the given BitstreamWriter*/
void
flacenc_write_lpc_subframe(BitstreamWriter* bs,
                           struct flac_context* encoder,
                           unsigned bits_per_sample,
                           unsigned wasted_bits_per_sample,
                           const array_i* samples);

/*given a set of samples and encoding parameters,
  determines the best QLP coefficients/precision/shift-needed
  for an LPC subframe*/
void
flacenc_best_lpc_coefficients(struct flac_context* encoder,
                              unsigned bits_per_sample,
                              unsigned wasted_bits_per_sample,
                              const array_i* samples,

                              array_i* qlp_coefficients,
                              unsigned* qlp_precision,
                              int* qlp_shift_needed);

/*given a set of encoding parameters for an LPC subframe,
  generates the subframe's residuals and encodes it
  to the given BitstreamWriter*/
void
flacenc_encode_lpc_subframe(BitstreamWriter* bs,
                            struct flac_context* encoder,
                            unsigned bits_per_sample,
                            unsigned wasted_bits_per_sample,
                            unsigned qlp_precision,
                            unsigned qlp_shift_needed,
                            const array_i* qlp_coefficients,
                            const array_i* samples);

/*given a set of integer samples,
  returns a windowed set of floating point samples*/
void
flacenc_window_signal(struct flac_context* encoder,
                      const array_i* samples,
                      array_f* windowed_signal);

/*given a set of windowed samples and a maximum LPC order,
  returns a set of autocorrelation values whose length is max_lpc_order + 1*/
void
flacenc_autocorrelate(unsigned max_lpc_order,
                      const array_f* windowed_signal,
                      array_f* autocorrelation_values);

/*given a maximum LPC order
  and set of autocorrelation values whose length is max_lpc_order + 1
  returns list of LP coefficient lists whose length is max_lpc_order
  and a list of error values whose length is also max_lpc_order*/
void
flacenc_compute_lp_coefficients(unsigned max_lpc_order,
                                const array_f* autocorrelation_values,
                                array_fa* lp_coefficients,
                                array_f* lp_error);

/*given a set of error values and a number of encoding parameters
  returns the best estimated LPC order value to use to encode those samples*/
unsigned
flacenc_estimate_best_lpc_order(unsigned bits_per_sample,
                                unsigned qlp_precision,
                                unsigned max_lpc_order,
                                unsigned block_size,
                                const array_f* lp_error);

/*given a list of LP coefficient lists, the LPC order to use
  and a QLP precision value (from the encoding paramters)
  returns a set of quantized QLP coefficient integers
  and a non-negative QLP shift-needed value*/
void
flacenc_quantize_coefficients(const array_fa* lp_coefficients,
                              unsigned order,
                              unsigned qlp_precision,

                              array_i* qlp_coefficients,
                              int* qlp_shift_needed);

/*given a set of residuals, encoding parameters
  and subframe block_size and order
  writes a block of residuals to the given BitstreamWriter*/
void
flacenc_encode_residuals(BitstreamWriter* bs,
                         struct flac_context* encoder,
                         unsigned block_size,
                         unsigned order,
                         const array_i* residuals);

/*encodes the given residual partition,
  not including its 4-5 bit Rice parameter*/
void
flacenc_encode_residual_partition(BitstreamWriter* bs,
                                  unsigned rice_parameter,
                                  const array_li* residual_partition);

/*given the abs_sum of a residual partition,
  returns the estimated best Rice parameter for that partition*/
unsigned
flacenc_best_rice_parameter(const struct flac_context* encoder,
                            uint64_t abs_partition_sum,
                            unsigned partition_size);

/*given a Rice parameter and the abs_sum of a residual partition
  along with its length, returns the estimated size of that partition*/
unsigned
flacenc_estimate_partition_size(unsigned rice_parameter,
                                uint64_t abs_partition_sum,
                                unsigned partition_size);

/*returns a true value if all samples are the same*/
int
flacenc_all_identical(const array_i* samples);

/*equivilent to sum(map(abs, data))*/
uint64_t
flacenc_abs_sum(const array_li* data);

#include "../common/flac_crc.h"

#endif
