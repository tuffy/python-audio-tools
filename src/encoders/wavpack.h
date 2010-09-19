#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream_w.h"
#include "../array.h"
#include "../pcmreader.h"
#include "../md5.h"

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
              WV_MD5               = 0x6} wv_metadata_function;



struct wavpack_encoder_context {
    uint8_t bits_per_sample;
    uint32_t sample_rate;
    uint16_t total_channels;
    uint32_t channel_mask;

    uint32_t block_index;
    uint32_t byte_count;
    struct i_array block_offsets;

    audiotools__MD5Context md5;
    uint32_t pcm_bytes;

    struct {
        int header_written;
        long header_offset;
        uint8_t* header;
        uint8_t* footer;
#ifdef PY_SSIZE_T_CLEAN
        Py_ssize_t header_len;
        Py_ssize_t footer_len;
#else
        int header_len;
        int footer_len;
#endif
    } wave;

    /*We'll try saving these from block to block
      which seems like how the reference encoder does things.
      Each sub-array is the decorrelation_weight values
      for each pass of a given channel.
      For example:
      decorrelation_weights.arrays[1].data[2]
      is the 3rd pass of channel 2.*/
    struct ia_array decorrelation_weights;

    struct {
        int joint_stereo;
        int decorrelation_passes;
    } options;
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

#define WV_UNARY_LIMIT 16
#define MAXIMUM_TERM_COUNT 16
#define WEIGHT_MAXIMUM 1024
#define WEIGHT_MINIMUM -1024

struct wavpack_residual {
    struct {
        int present;

        int count;
    } zeroes;
    struct {
        int present;

        int value;

        int unary;
        int fixed_value;
        int fixed_size;
        int has_extra_bit;
        int extra_bit;
        int sign;
    } golomb;

    /*These are the holding_one, holding_zero pairs
      that which have been output from the previous residual.*/
    int input_holding_zero;
    int input_holding_one;

    /*These are the holding_one, holding_zero pairs
      that outputting this residual will generate
      such that the next residual can look at these values
      to determine its own holding_one and holding_zero pairs.*/
    int output_holding_zero;
    int output_holding_one;
};

void
wavpack_write_frame(Bitstream *bs,
                    struct wavpack_encoder_context *context,
                    struct ia_array *samples,
                    long channel_mask);

void
wavpack_write_footer_block(Bitstream *bs,
                           struct wavpack_encoder_context* context);

/*given a channel count and channel mask (which may be 0),
  build a list of 1 or 2 channel count values
  for each left/right pair*/
void
wavpack_channel_splits(struct i_array *counts,
                       int channel_count,
                       long channel_mask);

void
wavpack_initialize_block_header(struct wavpack_block_header* header,
                                struct wavpack_encoder_context* context,
                                int channel_count,
                                int pcm_frames,
                                int first_block,
                                int last_block);

void
wavpack_write_block(Bitstream* bs,
                    struct wavpack_encoder_context* context,
                    struct i_array* channel_A,
                    struct i_array* channel_B,
                    int channel_number,
                    int channel_count,
                    int first_block,
                    int last_block);

ia_data_t
wavpack_abs_maximum(ia_data_t sample, ia_data_t current_max);

void
wavpack_write_block_header(Bitstream *bs,
                           struct wavpack_block_header *header);

/*nondecoder data should be 0 or 1.
  block_size is in bytes.
  This will convert to WavPack's size value and set
  "actual size 1 less" as needed.*/
void
wavpack_write_subblock_header(Bitstream *bs,
                              wv_metadata_function metadata_function,
                              uint8_t nondecoder_data,
                              uint32_t block_size);

/*Writes the given set of decorrelation terms and deltas
  to the given bitstream in the proper order.*/
void
wavpack_write_decorr_terms(Bitstream *bs,
                           struct i_array* decorr_terms,
                           struct i_array* decorr_deltas);

void
wavpack_write_decorr_weights(Bitstream *bs,
                             int channel_count,
                             int term_count,
                             struct i_array* weights_A,
                             struct i_array* weights_B);

void
wavpack_write_decorr_samples(Bitstream *bs,
                             int channel_count,
                             struct i_array* decorr_terms,
                             struct ia_array* samples_A,
                             struct ia_array* samples_B);

/*Writes an entropy variables sub-block to the bitstream.
  The entropy variable list should be 3 elements long.
  If channel_count is 2, both sets of entropy variables are written.
  If it is 1, only channel A's entropy variables are written.*/
void
wavpack_write_entropy_variables(Bitstream *bs,
                                struct i_array *variables_A,
                                struct i_array *variables_B,
                                int channel_count);

/*Writes a bitstream sub-block to the bitstream.*/
void
wavpack_write_residuals(Bitstream *bs,
                        struct i_array *channel_A,
                        struct i_array *channel_B,
                        struct i_array *variables_A,
                        struct i_array *variables_B,
                        int channel_count);

void
wavpack_write_residual(Bitstream* bs,
                       struct wavpack_residual* residual_accumulator,
                       struct i_array** medians_pair,
                       int current_channel,
                       ia_data_t value);

/*Given a sample value and set of medians for the current channel,
  calculate a raw residual value and assign it to the given struct.
  The median values are also updated by this routine.
  This doesn't handle the "holding_one" and "holding_zero" aspects;
  those are figured out at final write-time.*/
void
wavpack_calculate_residual(struct wavpack_residual *residual,
                           struct i_array *medians,
                           int32_t value);

/*Writes a block of zeroes to the given residual struct.
  That block size may be 0, indiciating a "false alarm"
  with no actual zeroes to generate at write-time.*/
void
wavpack_calculate_zeroes(struct wavpack_residual *residual,
                         uint32_t zeroes);

/*Sets all the given medians to 0.*/
void
wavpack_clear_medians(struct i_array *medians_A,
                      struct i_array *medians_B,
                      int channel_count);


/*Computes and writes a modified Elias gamma code to the given bitstream.
  It requires an input value greater than 0.

  This is used by both the zeroes block and the unary escape code.
*/
void
wavpack_write_egc(Bitstream* bs, int value);

/*Outputs an accumulated residual value to the bitstream.*/
void
wavpack_flush_residual(Bitstream *bs,
                       struct wavpack_residual *residual);

void
wavpack_print_residual(FILE* output,
                       struct wavpack_residual* residual);

void
wavpack_print_medians(FILE *output,
                      struct i_array* medians_A,
                      struct i_array* medians_B,
                      int channel_count);

int32_t
wavpack_log2(int32_t sample);

/*Performs a decorrelation pass over channel_A and (optionally) channel_B,
  altering their values in the process.
  decorrelation_weight_A and (optionally) decorrelation_weight_B are updated
  in the process.
  If "channel_count" is 1, only channel_A and weight_A are used.
  Otherwise, channel_B is also used.*/
void
wavpack_perform_decorrelation_pass(struct i_array* channel_A,
                                   struct i_array* channel_B,
                                   int decorrelation_term,
                                   int decorrelation_delta,
                                   int* decorrelation_weight_A,
                                   int* decorrelation_weight_B,
                                   struct i_array* decorrelation_samples_A,
                                   struct i_array* decorrelation_samples_B,
                                   int channel_count);

void
wavpack_perform_decorrelation_pass_1ch(struct i_array* channel,
                                       int decorrelation_term,
                                       int decorrelation_delta,
                                       int* decorrelation_weight,
                                       struct i_array* decorrelation_samples);

/*Returns OK if the given options are compatible.
  Raises an error and returns ERROR if not.*/
status
wavpack_verify_tunables(struct wavpack_encoder_context* context);

/*given a set of channel data and encoding context
  (for compression options), calculates a block's tunable information*/
void
wavpack_calculate_tunables(struct wavpack_encoder_context* context,
                           struct i_array* channel_A,
                           struct i_array* channel_B,
                           int channel_number,
                           int channel_count,
                           struct i_array* decorrelation_terms,
                           struct i_array* decorrelation_deltas,
                           struct i_array* decorrelation_weights_A,
                           struct i_array* decorrelation_weights_B,
                           struct ia_array* decorrelation_samples_A,
                           struct ia_array* decorrelation_samples_B,
                           struct i_array* entropy_variables_A,
                           struct i_array* entropy_variables_B);

void
wavpack_store_tunables(struct wavpack_encoder_context* context,
                       int channel_number,
                       int channel_count,
                       struct i_array* decorrelation_weights_A,
                       struct i_array* decorrelation_weights_B);

/*Updates the contents of channel_A and channel_B to be
  joint stereo.*/
void
wavpack_perform_joint_stereo(struct i_array *channel_A,
                             struct i_array *channel_B);

void
wavpack_count_bytes(int byte, void* value);

void
wavpack_calculate_md5(void* data, unsigned char *buffer, unsigned long len);

void
wavpack_count_pcm_bytes(void* data, unsigned char* buffer, unsigned long len);

void
wavpack_write_wave_header_sub_block(Bitstream* stream,
                                    struct wavpack_encoder_context* context,
                                    uint32_t pcm_bytes);
