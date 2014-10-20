#ifndef MLPDEC2
#define MLPDEC2
#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"
#include "../buffer.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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
              NO_MAJOR_SYNC,
              INVALID_MAJOR_SYNC,
              INVALID_EXTRAWORD_PRESENT,
              INVALID_RESTART_HEADER,
              INVALID_DECODING_PARAMETERS,
              INVALID_MATRIX_PARAMETERS,
              INVALID_CHANNEL_PARAMETERS,
              INVALID_BLOCK_DATA,
              INVALID_FILTER_PARAMETERS,
              PARITY_MISMATCH,
              CRC8_MISMATCH} mlp_status;

struct major_sync {
    unsigned bits_per_sample_0;
    unsigned bits_per_sample_1;
    unsigned sample_rate_0;
    unsigned sample_rate_1;
    unsigned channel_assignment;
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
    a_int* bypassed_LSB;
};

struct filter_parameters {
    unsigned shift;
    a_int* coeff;
    a_int* state;
};

struct channel_parameters {
    struct filter_parameters FIR;
    struct filter_parameters IIR;

    int huffman_offset;
    unsigned codebook;
    unsigned huffman_lsbs;
};

struct decoding_parameters {
    unsigned flags[8];

    unsigned block_size;

    unsigned matrix_len;
    struct matrix_parameters matrix[MAX_MLP_MATRICES];

    unsigned output_shift[MAX_MLP_CHANNELS];

    unsigned quant_step_size[MAX_MLP_CHANNELS];

    struct channel_parameters channel[MAX_MLP_CHANNELS];
};

struct substream {
    struct substream_info info;

    struct restart_header header;

    struct decoding_parameters parameters;

    /*residuals[c][i] where c is channel and i is PCM frame*/
    aa_int* residuals;

    /*a temporary buffer of filtered residual data*/
    a_int* filtered;
};

typedef struct {
    struct major_sync major_sync;
    int major_sync_read;
    struct substream substream[MAX_MLP_SUBSTREAMS];

    aa_int* framelist;

} MLPDecoder;

struct checkdata {
    uint8_t parity;
    uint8_t crc;
    uint8_t final_crc;
};

MLPDecoder*
open_mlp_decoder(void);

void
close_mlp_decoder(MLPDecoder* decoder);

/*given a packet, returns the total size of the MLP frame
  no data is consumed from the packet

  if the packet doesn't contain at least 4 bytes, returns 0*/
unsigned
mlp_total_frame_size(const struct bs_buffer *packet);

/*returns 1 if there isn't enough data in the current packet
  to decode at least 1 MLP frame
  returns 0 otherwise*/
int
mlp_packet_empty(const struct bs_buffer *packet);

/*given an MLPDecoder
  along with packet data
  decode as many MLP frames as possible to framelist
  returns OK on success, or something else if an error occurs*/
mlp_status
read_mlp_frames(MLPDecoder* decoder,
                struct bs_buffer *packet,
                aa_int* framelist);

/*given MLPDecoder context and a buffer of single frame data
  (including major sync, but not including frame size header)
  returns 1 or more channels of PCM data in MLP channel order*/
mlp_status
read_mlp_frame(MLPDecoder* decoder,
               BitstreamReader* bs,
               aa_int* framelist);

/*given a buffer of frame data, returns 28 byte major sync, if present*/
mlp_status
read_mlp_major_sync(BitstreamReader* bs,
                    struct major_sync* major_sync);

/*given a buffer of frame data, returns 2 byte substream info*/
mlp_status
read_mlp_substream_info(BitstreamReader* bs,
                        struct substream_info* substream_info);

/*given a substream context and buffer of substream data,
  returns 1 or more channels of PCM data
  which may be offset depending on substream's min/max channel

  e.g. substream0 may have framelist->_[0] / framelist->_[1]
  and substream1 may have framelist->_[2] / framelist->_[3] / framelist->_[4]
  which should be combined into a single 5 channel stream*/
mlp_status
read_mlp_substream(struct substream* substream,
                   BitstreamReader* bs,
                   aa_int* framelist);

/*given a substream context and buffer of substream data,
  appends block's data to framelist as 1 or more channels of PCM data*/
mlp_status
read_mlp_block(struct substream* substream,
               BitstreamReader* bs,
               aa_int* framelist);

/*reads a restart header from a block*/
mlp_status
read_mlp_restart_header(BitstreamReader* bs,
                        struct restart_header* restart_header);

/*reads decoding parameters from a block
  depending on values from the most recent restart header*/
mlp_status
read_mlp_decoding_parameters(BitstreamReader* bs,
                             unsigned header_present,
                             unsigned min_channel,
                             unsigned max_channel,
                             unsigned max_matrix_channel,
                             struct decoding_parameters* p);

/*reads matrix parameters from decoding parameters
  depending on max_matrix_channel from the most recent restart header*/
mlp_status
read_mlp_matrix_params(BitstreamReader* bs,
                       unsigned max_matrix_channel,
                       unsigned* matrix_len,
                       struct matrix_parameters* mp);

mlp_status
read_mlp_FIR_parameters(BitstreamReader* bs,
                        struct filter_parameters* FIR);

mlp_status
read_mlp_IIR_parameters(BitstreamReader* bs,
                        struct filter_parameters* IIR);

/*given a block's residual data
  min_channel/max_channel from the restart header
  along with block_size in PCM frames, matrix_len, matrix parameters,
  quant_step_size and channel parameters from decoding parameters
  returns a list of bypassed_LSB values per matrix (which may be 0s)
  and a list of residual values per channel*/
mlp_status
read_mlp_residual_data(BitstreamReader* bs,
                       unsigned min_channel,
                       unsigned max_channel,
                       unsigned block_size,
                       unsigned matrix_len,
                       const struct matrix_parameters* matrix,
                       const unsigned* quant_step_size,
                       const struct channel_parameters* channel,
                       aa_int* residuals);

/*given a list of residuals for a given channel,
  the FIR/IIR filter parameters and a quant_step_size
  returns a list of filtered residuals
  along with updated FIR/IIR filter parameter state*/
mlp_status
filter_mlp_channel(const a_int* residuals,
                   struct filter_parameters* FIR,
                   struct filter_parameters* IIR,
                   unsigned quant_step_size,
                   a_int* filtered);

/*given a list of filtered residuals across all substreams
  max_matrix_channel, noise_shift, noise_gen_seed from the restart header
  matrix parameters, quant_step_size from the decoding parameters
  and bypassed_LSBs from the residual block
  returns a set of rematrixed channel data

  when 2 substreams are present in an MLP stream,
  one typically uses the parameters from the second substream*/
void
rematrix_mlp_channels(aa_int* channels,
                      unsigned max_matrix_channel,
                      unsigned noise_shift,
                      unsigned* noise_gen_seed,
                      unsigned matrix_count,
                      const struct matrix_parameters* matrix,
                      const unsigned* quant_step_size);

void
mlp_checkdata_callback(uint8_t byte, void* checkdata);

#ifndef STANDALONE
PyObject*
mlp_python_exception(mlp_status mlp_status);
#endif

const char*
mlp_python_exception_msg(mlp_status mlp_status);

#endif
