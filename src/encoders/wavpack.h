#include <Python.h>
#include <stdint.h>
#include "../bitstream_w.h"
#include "../array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

typedef enum {OK, ERROR} status;

typedef enum {WV_DECORR_TERMS      = 0x2,
              WV_DECORR_WEIGHTS    = 0x3,
              WV_DECORR_SAMPLES    = 0x4,
              WV_ENTROPY_VARIABLES = 0x5,
              WV_INT32_INFO        = 0x9,
              WV_BITSTREAM         = 0xA} wv_metadata_function;

struct wavpack_encoder_context {
    uint8_t bits_per_sample;
    uint32_t sample_rate;
    uint32_t block_index;
    struct i_array block_offsets;
};

struct wavpack_block_header {
    /*block ID                                   32 bits*/
    uint32_t block_size;                       /*32 bits*/
    uint16_t version;                          /*16 bits*/
    uint8_t track_number;                      /*8 bits*/
    uint8_t index_number;                      /*8 bits*/
    uint32_t total_samples;                    /*32 bits*/
    uint32_t block_index;                      /*32 bits*/
    uint32_t block_samples;                    /*32 bits*/

    uint8_t bits_per_sample;                   /*2 bits*/
    uint8_t mono_output;                       /*1 bit*/
    uint8_t hybrid_mode;                       /*1 bit*/
    uint8_t joint_stereo;                      /*1 bit*/
    uint8_t cross_channel_decorrelation;       /*1 bit*/
    uint8_t hybrid_noise_shaping;              /*1 bit*/
    uint8_t floating_point_data;               /*1 bit*/
    uint8_t extended_size_integers;            /*1 bit*/
    uint8_t hybrid_parameters_control_bitrate; /*1 bit*/
    uint8_t hybrid_noise_balanced;             /*1 bit*/
    uint8_t initial_block_in_sequence;         /*1 bit*/
    uint8_t final_block_in_sequence;           /*1 bit*/
    uint8_t left_shift;                        /*5 bits*/
    uint8_t maximum_data_magnitude;            /*5 bits*/
    uint32_t sample_rate;                      /*4 bits*/
    /*reserved                                   2 bits*/
    uint8_t use_IIR;                           /*1 bit*/
    uint8_t false_stereo;                      /*1 bit*/
    /*reserved                                   1 bit*/

    uint32_t crc;                              /*32 bits*/
};

void
WavPackEncoder_write_frame(Bitstream *bs,
                           struct wavpack_encoder_context *context,
                           struct ia_array *samples,
                           long channel_mask);

/*given a channel count and channel mask (which may be 0),
  build a list of 1 or 2 channel count values
  for each left/right pair*/
void
WavPackEncoder_channel_splits(struct i_array *counts,
                              int channel_count,
                              long channel_mask);

void
WavPackEncoder_write_block(Bitstream *bs,
                           struct wavpack_encoder_context *context,
                           struct i_array *channel_A,
                           struct i_array *channel_B,
                           int channel_count,
                           int first_block,
                           int last_block);

ia_data_t
WavPackEncoder_abs_maximum(ia_data_t sample, ia_data_t current_max);

void
WavPackEncoder_write_block_header(Bitstream *bs,
                                  struct wavpack_block_header *header);

/*nondecoder data should be 0 or 1.
  block_size is in bytes.
  This will convert to WavPack's size value and set
  "actual size 1 less" as needed.*/
void
WavPackEncoder_write_subblock_header(Bitstream *bs,
                                     wv_metadata_function metadata_function,
                                     uint8_t nondecoder_data,
                                     uint32_t block_size);



