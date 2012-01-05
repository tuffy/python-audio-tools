#include "wavpack.h"
#include "../common/misc.h"
#include <assert.h>
#include <limits.h>

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

#ifndef STANDALONE
PyObject*
encoders_encode_wavpack(PyObject *dummy,
                        PyObject *args, PyObject *keywds) {
    char *filename;
    FILE *file;
    BitstreamWriter *stream;
    PyObject *pcmreader_obj;
    pcmreader *pcmreader;
    struct wavpack_encoder_context context;
    array_ia* pcm_frames;
    array_ia* block_frames;
    unsigned block;
    uint32_t block_index = 0;

    unsigned block_size;
    int try_false_stereo = 0;
    int try_wasted_bits = 0;
    int try_joint_stereo = 0;
    unsigned correlation_passes = 0;

    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "block_size",

                             "false_stereo",
                             "wasted_bits",
                             "joint_stereo",
                             "decorrelation_passes",
                             "wave_header",
                             "wave_footer",
                             NULL};

    /*set some default option values*/

    if (!PyArg_ParseTupleAndKeywords(args,
                                     keywds,
                                     "sOI|iiiIs#s#",
                                     kwlist,
                                     &filename,
                                     &pcmreader_obj,
                                     &block_size,

                                     &try_false_stereo,
                                     &try_wasted_bits,
                                     &try_joint_stereo,
                                     &correlation_passes,
                                     &(context.wave.header_data),
                                     &(context.wave.header_len),
                                     &(context.wave.footer_data),
                                     &(context.wave.footer_len)))
        return NULL;

    /*open the given filename for writing*/
    if ((file = fopen(filename, "wb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    } else {
        stream = bw_open(file, BS_LITTLE_ENDIAN);
    }

    /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
    if ((pcmreader = open_pcmreader(pcmreader_obj)) == NULL) {
        fclose(file);
        return NULL;
    }
#else
void
encoders_encode_wavpack(char *filename,
                        FILE *pcmdata,
                        unsigned block_size,
                        int try_false_stereo,
                        int try_wasted_bits,
                        int try_joint_stereo,
                        unsigned correlation_passes) {
    FILE *file;
    BitstreamWriter *stream;
    pcmreader* pcmreader;
    struct wavpack_encoder_context context;
    array_ia* pcm_frames;
    array_ia* block_frames;
    unsigned block;
    uint32_t block_index = 0;

    file = fopen(filename, "wb");
    stream = bw_open(file, BS_LITTLE_ENDIAN);
    if ((pcmreader =
         open_pcmreader(pcmdata, 44100, 2, 0x3, 16, 0, 1)) == NULL) {
        return;
    }

#endif

    pcm_frames = array_ia_new();
    block_frames = array_ia_new();

    wavpack_init_context(&context,
                         pcmreader->channels,
                         pcmreader->channel_mask,
                         try_false_stereo,
                         try_wasted_bits,
                         try_joint_stereo,
                         correlation_passes);

    /*read full list of PCM frames from pcmreader*/
    if (pcmreader->read(pcmreader, block_size, pcm_frames))
        goto error;

    while (pcm_frames->_[0]->len > 0) {
        /*split PCM frames into 1-2 channel blocks*/
        printf("encoding block set\n");
        for (block = 0; block < context.blocks_per_set; block++) {
            pcm_frames->split(pcm_frames,
                              context.parameters[block].channel_count,
                              block_frames,
                              pcm_frames);

            wavpack_encode_block(&context,
                                 &(context.parameters[block]),
                                 block_frames,
                                 block_index,
                                 block == 0,
                                 block == (context.blocks_per_set - 1));
        }

        block_index += pcm_frames->_[0]->len;
        if (pcmreader->read(pcmreader, block_size, pcm_frames))
            goto error;
    }

    /*add wave footer/MD5 sub-blocks to end of stream*/

    /*update wave header, if necessary*/

    /*go back and set block header data as necessary*/

    /*close open file handles and deallocate temporary space*/
    wavpack_free_context(&context);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);
    stream->close(stream);
    pcm_frames->del(pcm_frames);
    block_frames->del(block_frames);

#ifndef STANDALONE
    Py_INCREF(Py_None);
    return Py_None;
#else
    return;
#endif

 error:
    /*close open file handles and deallocate temporary space*/
    wavpack_free_context(&context);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);
    stream->close(stream);
    pcm_frames->del(pcm_frames);
    block_frames->del(block_frames);

#ifndef STANDALONE
    return NULL;
#else
    fprintf(stderr, "* error encountered in encode_wavpack\n");
    return;
#endif
}

void
wavpack_init_context(struct wavpack_encoder_context* context,
                     unsigned channel_count, unsigned channel_mask,
                     int try_false_stereo,
                     int try_wasted_bits,
                     int try_joint_stereo,
                     unsigned correlation_passes) {
    array_i* block_channels = array_i_new();
    unsigned i;

    /*determine block split based on channel count and mask*/
    assert(channel_count > 0);
    if (channel_count == 1) {
        block_channels->vset(block_channels, 1, 1);
    } else if (channel_count == 2) {
        block_channels->vset(block_channels, 1, 2);
    } else {
        switch (channel_mask) {
        case 0x7:   /*front left, front right, front center*/
            block_channels->vset(block_channels, 2, 2, 1);
            break;
        case 0x33:  /*front left, front right, back left, back right*/
            block_channels->vset(block_channels, 2, 2, 2);
            break;
        case 0x107: /*front left, front right, front center, back center*/
            block_channels->vset(block_channels, 3, 2, 1, 1);
            break;
        case 0x37:  /*f. left, f. right, f. center, back left, back right*/
            block_channels->vset(block_channels, 3, 2, 1, 2);
            break;
        case 0x3F:  /*f. left, f.right, f. center, LFE, b. left, b. right*/
            block_channels->vset(block_channels, 4, 2, 1, 1, 2);
            break;
        default:
            /*store everything independently by default*/
            block_channels->mset(block_channels, channel_count, 1);
            break;
        }
    }

    context->cache.shifted = array_ia_new();
    context->cache.mid_side = array_ia_new();
    context->cache.sub_block = bw_open_recorder(BS_LITTLE_ENDIAN);
    context->cache.sub_blocks = bw_open_recorder(BS_LITTLE_ENDIAN);

    /*initialize encoding parameters for each block in the set*/
    context->blocks_per_set = block_channels->len;
    context->parameters = malloc(sizeof(struct encoding_parameters) *
                                 context->blocks_per_set);

    for (i = 0; i < block_channels->len; i++) {
        wavpack_init_block_parameters(&(context->parameters[i]),
                                      block_channels->_[i],
                                      try_false_stereo,
                                      try_wasted_bits,
                                      try_joint_stereo,
                                      correlation_passes);
    }

    block_channels->del(block_channels);
}

void
wavpack_free_context(struct wavpack_encoder_context* context)
{
    unsigned i;

    context->cache.shifted->del(context->cache.shifted);
    context->cache.mid_side->del(context->cache.mid_side);
    context->cache.sub_block->close(context->cache.sub_block);
    context->cache.sub_blocks->close(context->cache.sub_blocks);

    for (i = 0; i < context->blocks_per_set; i++) {
        wavpack_free_block_parameters(&(context->parameters[i]));
    }
    free(context->parameters);
}

void
wavpack_init_block_parameters(struct encoding_parameters* parameters,
                              unsigned channel_count,
                              int try_false_stereo,
                              int try_wasted_bits,
                              int try_joint_stereo,
                              unsigned correlation_passes)
{
    parameters->channel_count = channel_count;
    parameters->try_false_stereo = try_false_stereo;
    parameters->try_wasted_bits = try_wasted_bits;
    parameters->try_joint_stereo = try_joint_stereo;
    parameters->correlation_passes = correlation_passes;
    parameters->terms = array_i_new();
    parameters->deltas = array_i_new();
    parameters->weights = array_ia_new();
    parameters->samples = array_iaa_new();
}

void
wavpack_free_block_parameters(struct encoding_parameters* parameters)
{
    parameters->terms->del(parameters->terms);
    parameters->deltas->del(parameters->deltas);
    parameters->weights->del(parameters->weights);
    parameters->samples->del(parameters->samples);
}

void
wavpack_encode_block(struct wavpack_encoder_context* context,
                     struct encoding_parameters* parameters,
                     const array_ia* channels,
                     uint32_t block_index, int first_block, int last_block)
{
    int mono_output;
    int false_stereo;
    unsigned magnitude;
    unsigned wasted_bps;
    unsigned total_frames;
    array_ia* shifted = context->cache.shifted;
    array_ia* mid_side = context->cache.mid_side;
    uint32_t crc;

    assert((channels->len == 1) || (channels->len == 2));

    shifted->reset(shifted);
    mid_side->reset(mid_side);

    total_frames = channels->_[0]->len;

    if ((channels->len == 1) ||
        (parameters->try_false_stereo &&
         (channels->_[0]->equals(channels->_[0], channels->_[1])))) {
        if (channels->len == 1) {
            mono_output = 1;
            false_stereo = 0;
        } else {
            mono_output = 0;
            false_stereo = 1;
        }

        /*calculate the maximum magnitude of channel_0 and channel_1*/
        magnitude = maximum_magnitude(channels->_[0]);

        /*calculate and apply any wasted least-significant bits*/
        if (parameters->try_wasted_bits) {
            wasted_bps = wasted_bits(channels->_[0]);
            if (wasted_bps > 0) {
                unsigned i;
                shifted->_[0]->resize(shifted->_[0], total_frames);
                for (i = 0; i < total_frames; i++) {
                    a_append(shifted->_[0], channels->_[0]->_[i] >> wasted_bps);
                }
            } else {
                channels->_[0]->copy(channels->_[0], shifted->append(shifted));
            }
        } else {
            wasted_bps = 0;
            channels->_[0]->copy(channels->_[0], shifted->append(shifted));
        }

        crc = calculate_crc(shifted);
    } else {
        mono_output = 0;
        false_stereo = 0;

        /*calculate the maximum magnitude of channel_0 and channel_1*/
        magnitude = MAX(maximum_magnitude(channels->_[0]),
                        maximum_magnitude(channels->_[1]));

        /*calculate and apply any wasted least-significant bits*/
        if (parameters->try_wasted_bits) {
            wasted_bps = MIN(wasted_bits(channels->_[0]),
                             wasted_bits(channels->_[1]));
            if (wasted_bps > 0) {
                unsigned i;
                shifted->_[0]->resize(shifted->_[0], total_frames);
                shifted->_[1]->resize(shifted->_[1], total_frames);
                for (i = 0; i < channels->_[0]->len; i++) {
                    a_append(shifted->_[0], channels->_[0]->_[i] >> wasted_bps);
                    a_append(shifted->_[1], channels->_[1]->_[i] >> wasted_bps);
                }
            } else {
                channels->copy(channels, shifted);
            }
        } else {
            wasted_bps = 0;
            channels->copy(channels, shifted);
        }

        crc = calculate_crc(shifted);

        apply_joint_stereo(shifted, mid_side);
    }
}

static inline unsigned
bits(int x)
{
    unsigned total = 0;
    while (x > 0) {
        x >>= 1;
        total += 1;
    }
    return total;
}

unsigned
maximum_magnitude(const array_i* channel)
{
    unsigned magnitude = 0;
    unsigned i;
    for (i = 0; i < channel->len; i++) {
        magnitude = MAX(bits(abs(channel->_[i])), magnitude);
    }
    return magnitude;
}

static inline unsigned
wasted(int x)
{
    if (x == 0) {
        return UINT_MAX;
    } else {
        unsigned total = 0;
        while (x % 2) {
            x /= 2;
            total += 1;
        }
        return total;
    }
}

unsigned
wasted_bits(const array_i* channel)
{
    unsigned wasted_bps = UINT_MAX;
    unsigned i;
    for (i = 0; i < channel->len; i++) {
        wasted_bps = MIN(wasted(channel->_[i]), wasted_bps);
    }
    if (wasted_bps == UINT_MAX) {
        return 0;
    } else {
        return wasted_bps;
    }
}

uint32_t
calculate_crc(const array_ia* channels)
{
    const unsigned ch_count = channels->len;
    const unsigned total_samples = ch_count * channels->_[0]->len;
    unsigned i;
    uint32_t crc = 0xFFFFFFFF;

    for (i = 0; i < total_samples; i++) {
        crc = ((3 * crc) + channels->_[i % ch_count]->_[i / ch_count]);
    }

    return crc;
}

void
apply_joint_stereo(const array_ia* left_right, array_ia* mid_side)
{
    unsigned total_samples = left_right->_[0]->len;
    const array_i* left = left_right->_[0];
    const array_i* right = left_right->_[1];
    array_i* mid;
    array_i* side;
    unsigned i;

    assert(left->len == right->len);

    mid_side->reset(mid_side);
    mid = mid_side->append(mid_side);
    side = mid_side->append(mid_side);
    mid->resize(mid, total_samples);
    side->resize(side, total_samples);
    for (i = 0; i < total_samples; i++) {
        a_append(mid, left->_[i] - right->_[i]);
        a_append(side, (left->_[i] + right->_[i]) / 2);
    }
}

#ifdef STANDALONE
int main(int argc, char *argv[]) {
    encoders_encode_wavpack(argv[1], stdin, 22050, 1, 1, 1, 0);
    return 0;
}

#endif
