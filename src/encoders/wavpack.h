#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"
#include "../pcmconv.h"
#include "../common/md5.h"

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

#define WAVPACK_VERSION 0x407

typedef enum {OK, ERROR} status;

typedef enum {WV_DUMMY             = 0x0,
              WV_WAVE_HEADER       = 0x1,
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

struct encoding_parameters;

struct wavpack_encoder_context {
    /*one encoding_parameters entry per block in a set
      for example, a 6 channel stream being split 2-1-1-2
      will have 4 encoding_parameters entries*/
    struct encoding_parameters* parameters;
    unsigned blocks_per_set;

    /*a stack of positions which may need to be populated*/
    struct bw_pos_stack *total_frames_positions;

    /*running MD5 sum of PCM data*/
    audiotools__MD5Context md5sum;

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

    /*the position in the file of the RIFF WAVE header
      in case it needs to be filled in*/
    bw_pos_t* wave_header_position;

    /*cached stuff we don't want to reallocate every time*/
    struct {
        aa_int* shifted;
        aa_int* mid_side;
        aa_int* correlated;
        aa_int* correlation_temp;
        BitstreamRecorder* sub_block;
    } cache;
};

/*initializes temporary space and encoding parameters
  based on the input's channel count and mask
  and user-defined tunables*/
static void
init_context(struct wavpack_encoder_context* context,
             unsigned channel_count,
             unsigned channel_mask,
             int try_false_stereo,
             int try_wasted_bits,
             int try_joint_stereo,
             unsigned correlation_passes);

/*deallocates any temporary space from the context*/
static void
free_context(struct wavpack_encoder_context* context);

/*these are the encoding parameters for a given block in a set*/
struct encoding_parameters {
    /*the actual channel count for a given set's block, must be 1 or 2*/
    unsigned channel_count;

    int try_false_stereo;  /*check a 2 channel block for false stereo*/
    int try_wasted_bits;   /*check a block for wasted least-significant bits*/
    int try_joint_stereo;  /*apply joint stereo to 2 channel blocks*/

    /*the effective channel count for a given set's block, must be 1 or 2*/
    unsigned effective_channel_count;

    /*desired number of correlation passes:  0, 1, 2, 5, 10 or 16
      this may be less than the actual number of correlation passes
      depending on if the block is determined to be false stereo*/
    unsigned correlation_passes;

    /*terms[p]  correlation term for pass p*/
    a_int* terms;
    /*deltas[p] correlation delta for pass p*/
    a_int* deltas;
    /*weights[p][c] correlation weights for pass p, channel c*/
    aa_int* weights;
    /*samples[p][c][s] correlation sample s for pass p, channel c*/
    aaa_int* samples;

    /*2 lists of 3 entropy variables, as entropy[c][s]*/
    aa_int* entropies;
};

struct wavpack_residual {
    int zeroes;
    int m;
    unsigned offset;
    unsigned add;
    unsigned sign;
};

static void
init_block_parameters(struct encoding_parameters* params,
                      unsigned channel_count,
                      int try_false_stereo,
                      int try_wasted_bits,
                      int try_joint_stereo,
                      unsigned correlation_passes);

/*channel count is the effective channel count for the block
  which may be different from its actual channel count
  depending on whether false stereo is indicated*/
static void
reset_block_parameters(struct encoding_parameters* params,
                       unsigned channel_count);

static void
init_correlation_samples(a_int* samples,
                         int correlation_term);

/*round-trips the correlation weights, samples and the entropy variables
  from the previous block
  this presumes that the current block and previous block
  have the same effective channel count*/
static void
roundtrip_block_parameters(struct encoding_parameters* params);

static void
free_block_parameters(struct encoding_parameters* params);

static void
write_block_header(BitstreamWriter* bs,
                   bw_pos_t **sub_blocks_size_pos,
                   unsigned total_pcm_frames,
                   bw_pos_t **total_pcm_frames_pos,
                   unsigned block_index,
                   unsigned block_samples,
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
static unsigned
encoded_sample_rate(unsigned sample_rate);

static void
encode_block(BitstreamWriter* bs,
             struct wavpack_encoder_context* context,
             const pcmreader* pcmreader,
             struct encoding_parameters* parameters,
             const aa_int* channels,
             unsigned total_pcm_frames,
             unsigned block_index,
             int first_block,
             int last_block);

static void
encode_footer_block(BitstreamWriter* bs,
                    struct wavpack_encoder_context* context,
                    const pcmreader* pcmreader,
                    unsigned total_pcm_frame);

static void
write_sub_block(BitstreamWriter* block,
                unsigned metadata_function,
                unsigned nondecoder_data,
                BitstreamRecorder* sub_block);


/*terms[p] and deltas[p] are the correlation term and deltas values
  for pass "p"*/
static void
write_correlation_terms(BitstreamWriter* bs,
                        const a_int* terms,
                        const a_int* deltas);

static int
store_weight(int weight);

static int
restore_weight(int value);

/*weights[p][c] are the correlation weight values for channel "c", pass "p"*/
static void
write_correlation_weights(BitstreamWriter* bs,
                          const aa_int* weights,
                          unsigned channel_count);

/*terms[p] are the correlation terms for pass "p"
  samples[p][c][s] are correlation samples for channel "c", pass "p"*/
static void
write_correlation_samples(BitstreamWriter* bs,
                          const a_int* terms,
                          const aaa_int* samples,
                          unsigned channel_count);

static void
correlate_channels(aa_int* correlated_samples,
                   aa_int* uncorrelated_samples,
                   a_int* terms,
                   a_int* deltas,
                   aa_int* weights,
                   aaa_int* samples,
                   unsigned channel_count,
                   aa_int* temp);

static int
apply_weight(int weight, int64_t sample);

static void
correlate_1ch(a_int* correlated,
              const a_int* uncorrelated,
              int term,
              int delta,
              int* weight,
              a_int* samples,
              a_int* temp);

static void
correlate_2ch(aa_int* correlated,
              const aa_int* uncorrelated,
              int term,
              int delta,
              a_int* weights,
              aa_int* samples,
              aa_int* temp);

static void
write_entropy_variables(BitstreamWriter* bs,
                        unsigned channel_count,
                        const aa_int* entropies);

static void
write_bitstream(BitstreamWriter* bs,
                aa_int* entropies,
                const aa_int* residuals);

static int
unary_undefined(int u_j_1, int m_j);

static void
encode_residual(int residual, a_int* entropy,
                int* m, unsigned* offset, unsigned* add, unsigned* sign);

static int
flush_residual(BitstreamWriter* bs,
               int u_i_2, int m_i_1, unsigned offset_i_1, unsigned add_i_1,
               unsigned sign_i_1, int zeroes_i_1, int m_i);

static void
write_egc(BitstreamWriter* bs, unsigned v);

static unsigned
maximum_magnitude(const a_int* channel);

static unsigned
wasted_bits(const a_int* channel);

static uint32_t
calculate_crc(const aa_int* channels);

static void
apply_joint_stereo(const aa_int* left_right, aa_int* mid_side);

static int
wv_log2(int value);

static int
wv_exp2(int value);

static void
wavpack_md5_update(void *data, unsigned char *buffer, unsigned long len);

static void
write_dummy_wave_header(BitstreamWriter* bs, const pcmreader* pcmreader,
                        unsigned wave_footer_len);

static void
write_wave_header(BitstreamWriter* bs, const pcmreader* pcmreader,
                  uint32_t total_frames, unsigned wave_footer_len);

#define WV_UNARY_LIMIT 16
#define MAXIMUM_TERM_COUNT 16
#define WEIGHT_MAXIMUM 1024
#define WEIGHT_MINIMUM -1024
