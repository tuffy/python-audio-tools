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

    BitstreamWriter* frame;
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

/*writes a STREAMINFO metadata block to the bitstream*/
void
flacenc_write_streaminfo(BitstreamWriter* bs,
                         const struct flac_STREAMINFO* streaminfo);

/*takes a list of sample lists (one per channel)
  and the FLAC's streaminfo
  writes a full FLAC frame to the bitstream*/
void
flacenc_write_frame(BitstreamWriter* bs,
                    struct flac_context* encoder,
                    const array_ia* samples);

/*writes a UTF-8 value to the bitstream*/
void
write_utf8(BitstreamWriter *stream, unsigned int value);

/*an MD5 summing callback, updated when reading input strings*/
void
md5_update(void *data, unsigned char *buffer, unsigned long len);

int
flacenc_max_wasted_bits_per_sample(const array_i* samples);

/*takes a list of sample lists (one per channel)
  and the FLAC's streaminfo
  writes a FLAC frame header to the bitstream*/
void
flacenc_write_frame_header(BitstreamWriter* bs,
                           const struct flac_STREAMINFO *streaminfo,
                           unsigned block_size,
                           unsigned channel_assignment,
                           unsigned frame_number);

/*given a bits_per_sample and list of sample values,
  and the user-defined encoding options
  writes the best subframe to the bitbuffer*/
void
flacenc_write_subframe(struct flac_context* encoder,
                       int bits_per_sample,
                       const array_i* samples);

/*writes a CONSTANT subframe with the value "sample"
  to the bitbuffer*/
void
flacenc_write_constant_subframe(BitstreamWriter* bs,
                                int bits_per_sample,
                                int wasted_bits_per_sample,
                                int sample);

/*writes a VERBATIM subframe with the values "samples"
  to the bitbuffer*/
void
flacenc_write_verbatim_subframe(BitstreamWriter *bs,
                                int bits_per_sample,
                                int wasted_bits_per_sample,
                                const array_i* samples);

#include "../common/flac_crc.h"

#endif
