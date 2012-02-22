#ifndef MLPDEC2
#define MLPDEC2
#include <Python.h>
#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"
#include "../pcm.h"

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

/*streams can have only 1 or 2 substreams*/
#define MAX_MLP_SUBSTREAMS 2

#define MAX_MLP_MATRICES 6

/*6 channels + 2 matrix channels*/
#define MAX_MLP_CHANNELS 8

typedef enum {OK,
              IO_ERROR,
              INVALID_MAJOR_SYNC,
              INVALID_EXTRAWORD_PRESENT,
              INVALID_RESTART_HEADER,
              INVALID_DECODING_PARAMETERS,
              INVALID_MATRIX_PARAMETERS,
              INVALID_CHANNEL_PARAMETERS,
              INVALID_BLOCK_DATA} mlp_status;

struct major_sync {
    unsigned bits_per_sample_0;
    unsigned bits_per_sample_1;
    unsigned sample_rate_0;
    unsigned sample_rate_1;
    unsigned channel_count;
    unsigned channel_mask;
    unsigned is_VBR;
    unsigned peak_bitrate;
    unsigned substream_count;
};

struct substream_info {
    unsigned extraword_present;
    unsigned nonrestart_substream;
    unsigned checkdata_present;
    unsigned substream_end;
};

struct restart_header {
    unsigned min_channel;
    unsigned max_channel;
    unsigned max_matrix_channel;
    unsigned noise_shift;
    unsigned noise_gen_seed;
    unsigned channel_assignment[MAX_MLP_CHANNELS];
    unsigned checksum;
};

struct matrix_parameters {
    unsigned out_channel;
    unsigned factional_bits;
    unsigned LSB_bypass;
    int coeff[MAX_MLP_CHANNELS];
};

struct channel_parameters {
    struct {
        unsigned shift;
        array_i* coeff;
    } FIR;

    struct {
        unsigned shift;
        array_i* coeff;
        array_i* state;
    } IIR;

    int huffman_offset;
    unsigned codebook;
    unsigned huffman_lsbs;
};

struct decoding_parameters {
    unsigned flags[8];

    unsigned block_size;

    /*matrix parameters*/
    unsigned matrix_len;
    struct matrix_parameters matrix[MAX_MLP_MATRICES];

    unsigned output_shift[MAX_MLP_CHANNELS];

    unsigned quant_step_size[MAX_MLP_CHANNELS];

    /*channel parameters*/
    struct channel_parameters channel[MAX_MLP_CHANNELS];
};

struct substream {
    struct substream_info info;
    struct restart_header header;
    struct decoding_parameters parameters;

    array_ia* bypassed_LSBs;
    array_ia* residuals;
};

typedef struct {
    BitstreamReader* reader;
    BitstreamReader* frame_reader;
    BitstreamReader* substream_reader;

    struct major_sync major_sync;
    struct substream substream[MAX_MLP_SUBSTREAMS];

} MLPDecoder;

MLPDecoder*
open_mlp_decoder(struct bs_buffer* frame_data);

void
close_mlp_decoder(MLPDecoder* decoder);

/*returns 1 if there isn't enough data in the current packet
  to decode at least 1 MLP frame
  returns 0 otherwise*/
int
mlp_packet_empty(MLPDecoder* decoder);

/*given an MLPDecoder pointing to a buffer of frame data
  (including length headers), decode as many frames as possible to framelist
  returns OK on success, or something else if an error occurs*/
mlp_status
read_mlp_frames(MLPDecoder* decoder,
                array_ia* framelist);

mlp_status
read_mlp_frame(MLPDecoder* decoder,
               BitstreamReader* bs,
               array_ia* framelist);

mlp_status
read_mlp_major_sync(BitstreamReader* bs,
                    struct major_sync* major_sync);

mlp_status
read_mlp_substream_info(BitstreamReader* bs,
                        struct substream_info* substream_info);

mlp_status
read_mlp_substream(MLPDecoder* decoder,
                   struct substream* substream,
                   BitstreamReader* bs,
                   array_ia* framelist);

mlp_status
read_mlp_restart_header(BitstreamReader* bs,
                        struct restart_header* restart_header);

mlp_status
read_mlp_decoding_parameters(BitstreamReader* bs,
                             unsigned header_present,
                             unsigned min_channel,
                             unsigned max_channel,
                             unsigned max_matrix_channel,
                             struct decoding_parameters* p);

mlp_status
read_mlp_matrix_params(BitstreamReader* bs,
                       unsigned max_matrix_channel,
                       unsigned* matrix_len,
                       struct matrix_parameters* mp);

mlp_status
read_mlp_fir_params(BitstreamReader* bs,
                    unsigned* shift,
                    array_i* coeffs);

mlp_status
read_mlp_iir_params(BitstreamReader* bs,
                    unsigned* shift,
                    array_i* coeffs,
                    array_i* state);

mlp_status
read_mlp_block_data(BitstreamReader* bs,
                    unsigned block_size,
                    unsigned min_channel,
                    unsigned max_channel,
                    unsigned matrix_len,
                    const unsigned* quant_step_size,
                    const struct matrix_parameters* matrix,
                    const struct channel_parameters* channel,
                    array_ia* bypassed_LSBs,
                    array_ia* residuals);

#endif
