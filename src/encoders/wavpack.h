#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"
#include "../pcmconv.h"
#include "../common/md5.h"

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

#define WAVPACK_VERSION 0x407

typedef enum {OK, ERROR} status;

typedef enum {WV_WAVE_HEADER       = 0x1,
              WV_WAVE_FOOTER       = 0x2,
              WV_DECORR_TERMS      = 0x2,
              WV_DECORR_WEIGHTS    = 0x3,
              WV_DECORR_SAMPLES    = 0x4,
              WV_ENTROPY_VARIABLES = 0x5,
              WV_INT32_INFO        = 0x9,
              WV_BITSTREAM         = 0xA,
              WV_CHANNEL_INFO      = 0xD,
              WV_MD5               = 0x6} wv_metadata_function;

struct block_offset;
struct encoding_parameters;

struct wavpack_encoder_context {
    /*one encoding_parameters entry per block in a set
      for example, a 6 channel stream being split 2-1-1-2
      will have 4 encoding_parameters entries*/
    struct encoding_parameters* parameters;
    unsigned blocks_per_set;

    /*total PCM frames written*/
    uint32_t total_frames;

    /*running MD5 sum of PCM data*/
    audiotools__MD5Context md5;

    /*a linked list of offsets to all blocks in the file
      which we can seek to and repopulate once encoding is finished*/
    struct block_offset* offsets;

    /*RIFF WAVE header and footer data
      which may be populated from an external file*/
    struct {
        int header_written;   /*set to 1 once the header's been written*/
        uint8_t* header_data; /*may be NULL, indicating no external header*/
        uint8_t* footer_data; /*may be NULL, indicating no external footer*/
#ifdef PY_SSIZE_T_CLEAN
        Py_ssize_t header_len;
        Py_ssize_t footer_len;
#else
        int header_len;
        int footer_len;
#endif
    } wave;

    /*cached stuff we don't want to reallocate every time*/
    struct {
        array_ia* shifted;
        array_ia* mid_side;
        BitstreamWriter* sub_block;
        BitstreamWriter* sub_blocks;
    } cache;
};

struct block_offset {
    fpos_t offset;
    struct block_offset* next;
};

/*initializes temporary space and encoding parameters
  based on the input's channel count and mask
  and user-defined tunables*/
void
wavpack_init_context(struct wavpack_encoder_context* context,
                     unsigned channel_count, unsigned channel_mask,
                     int try_false_stereo,
                     int try_wasted_bits,
                     int try_joint_stereo,
                     unsigned correlation_passes);

/*deallocates any temporary space from the context*/
void
wavpack_free_context(struct wavpack_encoder_context* context);

/*these are the encoding parameters for a given block in a set*/
struct encoding_parameters {
    unsigned channel_count;       /*1 or 2*/

    int try_false_stereo;  /*check a 2 channel block for false stereo*/
    int try_wasted_bits;   /*check a block for wasted least-significant bits*/
    int try_joint_stereo;  /*apply joint stereo to 2 channel blocks*/

    /*desired number of correlation passes:  0, 1, 2, 5, 10 or 16
      this may be less than the actual number of correlation passes
      depending on if the block is determined to be false stereo*/
    unsigned correlation_passes;

    /*terms[p]  correlation term for pass p*/
    array_i* terms;
    /*deltas[p] correlation delta for pass p*/
    array_i* deltas;
    /*weights[p][c] correlation weights for pass p, channel c*/
    array_ia* weights;
    /*samples[p][c][s] correlation sample s for pass p, channel c*/
    array_iaa* samples;

    /*2 lists of 3 entropy variables, as entropy[c][s]*/
    int entropy_variables[2][3];
};

void
wavpack_init_block_parameters(struct encoding_parameters* parameters,
                              unsigned channel_count,
                              int try_false_stereo,
                              int try_wasted_bits,
                              int try_joint_stereo,
                              unsigned correlation_passes);

void
wavpack_free_block_parameters(struct encoding_parameters* parameters);

void
wavpack_encode_block(struct wavpack_encoder_context* context,
                     struct encoding_parameters* parameters,
                     const array_ia* channels,
                     uint32_t block_index, int first_block, int last_block);

unsigned
maximum_magnitude(const array_i* channel);

unsigned
wasted_bits(const array_i* channel);

uint32_t
calculate_crc(const array_ia* channels);

void
apply_joint_stereo(const array_ia* left_right, array_ia* mid_side);

#define WV_UNARY_LIMIT 16
#define MAXIMUM_TERM_COUNT 16
#define WEIGHT_MAXIMUM 1024
#define WEIGHT_MINIMUM -1024
