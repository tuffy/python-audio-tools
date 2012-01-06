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
              WV_TERMS             = 0x2,
              WV_WEIGHTS           = 0x3,
              WV_SAMPLES           = 0x4,
              WV_ENTROPY           = 0x5,
              WV_SAMPLE_RATE       = 0x7,
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
    audiotools__MD5Context md5sum;

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
        array_ia* correlated;
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
    array_ia* entropies;
};

struct wavpack_residual {
    int zeroes;
    int m;
    unsigned offset;
    unsigned add;
    unsigned sign;
};

void
wavpack_init_block_parameters(struct encoding_parameters* params,
                              unsigned channel_count,
                              int try_false_stereo,
                              int try_wasted_bits,
                              int try_joint_stereo,
                              unsigned correlation_passes);

void
wavpack_reset_block_parameters(struct encoding_parameters* params,
                               unsigned channel_count);

void
init_correlation_samples(array_i* samples,
                         int correlation_term);

void
wavpack_free_block_parameters(struct encoding_parameters* params);

void
add_block_offset(FILE* file, struct block_offset** offsets);

void
write_block_header(BitstreamWriter* bs,
                   unsigned sub_blocks_size,
                   uint32_t block_index,
                   uint32_t block_samples,
                   unsigned bits_per_sample,
                   unsigned channel_count,
                   int joint_stereo,
                   unsigned correlation_pass_count,
                   unsigned wasted_bps,
                   int first_block,
                   int last_block,
                   unsigned maximum_magnitude,
                   unsigned sample_rate,
                   int false_stereo,
                   uint32_t crc);

/*given a sample rate in Hz,
  returns its 4-bit encoded version
  or 15 if the rate has no encoded version*/
unsigned
encoded_sample_rate(unsigned sample_rate);

void
wavpack_encode_block(BitstreamWriter* bs,
                     struct wavpack_encoder_context* context,
                     const pcmreader* pcmreader,
                     struct encoding_parameters* parameters,
                     const array_ia* channels,
                     uint32_t block_index, int first_block, int last_block);

void
wavpack_encode_footer_block(BitstreamWriter* bs,
                            struct wavpack_encoder_context* context,
                            const pcmreader* pcmreader);

void
write_sub_block(BitstreamWriter* block,
                unsigned metadata_function,
                unsigned nondecoder_data,
                BitstreamWriter* sub_block);

/*terms[p] and deltas[p] are the correlation term and deltas values
  for pass "p"*/
void
write_correlation_terms(BitstreamWriter* bs,
                        const array_i* terms,
                        const array_i* deltas);

int
store_weight(int weight);

/*weights[p][c] are the correlation weight values for channel "c", pass "p"*/
void
write_correlation_weights(BitstreamWriter* bs,
                          const array_ia* weights,
                          unsigned channel_count);

/*terms[p] are the correlation terms for pass "p"
  samples[p][c][s] are correlation samples for channel "c", pass "p"*/
void
write_correlation_samples(BitstreamWriter* bs,
                          const array_i* terms,
                          const array_iaa* samples,
                          unsigned channel_count);

void
correlate_channels(array_ia* correlated_samples,
                   array_ia* uncorrelated_samples,
                   array_i* terms,
                   array_i* deltas,
                   array_ia* weights,
                   array_iaa* samples,
                   unsigned channel_count);

int
apply_weight(int weight, int sample);

int
update_weight(int source, int result, int delta);

void
correlate_1ch(array_i* correlated,
              const array_i* uncorrelated,
              int term,
              int delta,
              int* weight,
              array_i* samples);

void
correlate_2ch(array_ia* correlated,
              const array_ia* uncorrelated,
              int term,
              int delta,
              array_i* weights,
              array_ia* samples);

void
write_entropy_variables(BitstreamWriter* bs,
                        unsigned channel_count,
                        const array_ia* entropies);

void
write_bitstream(BitstreamWriter* bs,
                array_ia* entropies,
                const array_ia* residuals);

int
unary_undefined(int u_j_1, int m_j);

void
write_residual(BitstreamWriter* bs,
               int u, unsigned offset, unsigned add, unsigned sign);

int
unary(int u_j_1, int m_j, int m_j_1);

void
encode_residual(int residual, array_i* entropy,
                int* m, unsigned* offset, unsigned* add, unsigned* sign);

int
flush_residual(BitstreamWriter* bs,
               int u_i_2, int m_i_1, unsigned offset_i_1, unsigned add_i_1,
               unsigned sign_i_1, int zeroes_i_1, int m_i);

void
write_egc(BitstreamWriter* bs, unsigned v);

unsigned
maximum_magnitude(const array_i* channel);

unsigned
wasted_bits(const array_i* channel);

uint32_t
calculate_crc(const array_ia* channels);

void
apply_joint_stereo(const array_ia* left_right, array_ia* mid_side);

int
wv_log2(int value);

static void
wavpack_md5_update(void *data, unsigned char *buffer, unsigned long len);

static void
write_wave_header(BitstreamWriter* bs, const pcmreader* pcmreader,
                  uint32_t total_frames, unsigned wave_footer_len);

#define WV_UNARY_LIMIT 16
#define MAXIMUM_TERM_COUNT 16
#define WEIGHT_MAXIMUM 1024
#define WEIGHT_MINIMUM -1024
