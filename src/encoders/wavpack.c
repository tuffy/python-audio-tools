#include "wavpack.h"
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
    unsigned i;

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

    context.wave.header_data = NULL;
    context.wave.footer_data = NULL;

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
    unsigned i;

    context.wave.header_data = NULL;
    context.wave.footer_data = NULL;

    file = fopen(filename, "wb");
    stream = bw_open(file, BS_LITTLE_ENDIAN);
    if ((pcmreader =
         open_pcmreader(pcmdata, 44100, 2, 0x3, 16, 0, 1)) == NULL) {
        return;
    }

#endif

    pcm_frames = array_ia_new();
    block_frames = array_ia_new();

    init_context(&context,
                 pcmreader->channels,
                 pcmreader->channel_mask,
                 try_false_stereo,
                 try_wasted_bits,
                 try_joint_stereo,
                 correlation_passes);

    pcmreader->add_callback(pcmreader, wavpack_md5_update, &(context.md5sum),
                            pcmreader->bits_per_sample >= 16,
                            1);

    /*read full list of PCM frames from pcmreader*/
    if (pcmreader->read(pcmreader, block_size, pcm_frames))
        goto error;

    while (pcm_frames->_[0]->len > 0) {
        unsigned pcm_frame_count = pcm_frames->_[0]->len;

        /*split PCM frames into 1-2 channel blocks*/
        for (block = 0; block < context.blocks_per_set; block++) {
            /*add a fresh block offset based on current file position*/
            add_block_offset(file, context.offsets);

            pcm_frames->split(pcm_frames,
                              context.parameters[block].channel_count,
                              block_frames,
                              pcm_frames);

            encode_block(stream,
                         &context,
                         pcmreader,
                         &(context.parameters[block]),
                         block_frames,
                         block_index,
                         block == 0,
                         block == (context.blocks_per_set - 1));
        }

        block_index += pcm_frame_count;
        if (pcmreader->read(pcmreader, block_size, pcm_frames))
            goto error;
    }

    /*add wave footer/MD5 sub-blocks to end of stream*/
    add_block_offset(file, context.offsets);
    encode_footer_block(stream, &context, pcmreader);

    /*update generated wave header, if necessary*/
    if (context.wave.header_data == NULL) {
        const uint64_t data_size = ((uint64_t)block_index *
                                    pcmreader->channels *
                                    (pcmreader->bits_per_sample / 8));
        const uint64_t max_size = 4294967296llu;

        if (data_size < max_size) {
            BitstreamWriter* sub_block = context.cache.sub_block;
            bw_reset_recorder(sub_block);

            /*maximum data size large enough to fit into 32-bit size field
              so go back and rewrite wave header properly*/
            fseek(file, 32, SEEK_SET);
            if (context.wave.footer_data == NULL) {
                write_wave_header(sub_block, pcmreader, block_index, 0);
            } else {
                write_wave_header(sub_block, pcmreader, block_index,
                                  context.wave.footer_len);
            }

            write_sub_block(stream, WV_WAVE_HEADER, 1, sub_block);
        }
    }

    /*go back and set block header data as necessary*/
    for (i = 0; i < context.offsets->len; i++) {
        fpos_t* pos = (fpos_t*)(context.offsets->_[i]);
        fsetpos(file, pos);
        fseek(file, 12, SEEK_CUR);
        stream->write(stream, 32, block_index);
    }

    /*close open file handles and deallocate temporary space*/
    free_context(&context);
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
    free_context(&context);
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

static void
init_context(struct wavpack_encoder_context* context,
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

    /*initialized cache items*/
    context->cache.shifted = array_ia_new();
    context->cache.mid_side = array_ia_new();
    context->cache.correlated = array_ia_new();
    context->cache.sub_block = bw_open_recorder(BS_LITTLE_ENDIAN);
    context->cache.sub_blocks = bw_open_recorder(BS_LITTLE_ENDIAN);

    /*initialize encoding parameters for each block in the set*/
    context->blocks_per_set = block_channels->len;
    context->parameters = malloc(sizeof(struct encoding_parameters) *
                                 context->blocks_per_set);

    for (i = 0; i < block_channels->len; i++) {
        init_block_parameters(&(context->parameters[i]),
                              block_channels->_[i],
                              try_false_stereo,
                              try_wasted_bits,
                              try_joint_stereo,
                              correlation_passes);
    }

    block_channels->del(block_channels);

    context->offsets = array_o_new(NULL, free, NULL);
    context->wave.header_written = 0;
    audiotools__MD5Init(&(context->md5sum));
}

static void
free_context(struct wavpack_encoder_context* context)
{
    unsigned i;

    context->cache.shifted->del(context->cache.shifted);
    context->cache.mid_side->del(context->cache.mid_side);
    context->cache.correlated->del(context->cache.correlated);
    context->cache.sub_block->close(context->cache.sub_block);
    context->cache.sub_blocks->close(context->cache.sub_blocks);

    for (i = 0; i < context->blocks_per_set; i++) {
        free_block_parameters(&(context->parameters[i]));
    }
    free(context->parameters);

    context->offsets->del(context->offsets);
}

static void
init_block_parameters(struct encoding_parameters* params,
                      unsigned channel_count,
                      int try_false_stereo,
                      int try_wasted_bits,
                      int try_joint_stereo,
                      unsigned correlation_passes)
{
    params->channel_count = channel_count;
    params->try_false_stereo = try_false_stereo;
    params->try_wasted_bits = try_wasted_bits;
    params->try_joint_stereo = try_joint_stereo;
    params->correlation_passes = correlation_passes;
    params->terms = array_i_new();
    params->deltas = array_i_new();
    params->weights = array_ia_new();
    params->samples = array_iaa_new();
    params->entropies = array_ia_new();

    reset_block_parameters(params, channel_count);
}

static void
reset_block_parameters(struct encoding_parameters* params,
                       unsigned channel_count)
{
    array_i* entropy;
    unsigned pass;

    params->effective_channel_count = channel_count;

    params->terms->reset(params->terms);
    params->deltas->reset(params->deltas);
    params->weights->reset(params->weights);
    params->samples->reset(params->samples);
    params->entropies->reset(params->entropies);

    /*setup some default correlation pass values*/
    if (channel_count == 1) {
        switch (params->correlation_passes) {
        case 0:
            break;
        case 1:
            params->terms->vset(params->terms, 1, 18);
            break;
        case 2:
            params->terms->vset(params->terms, 2, 17, 18);
            break;
        case 5:
        case 10:
        case 16:
            params->terms->vset(params->terms, 5, 3, 17, 2, 18, 18);
            break;
        default:
            /*invalid correlation pass count*/
            assert(0);
        }
        params->deltas->mset(params->deltas, params->terms->len, 2);
        for (pass = 0; pass < params->terms->len; pass++) {
            array_i* weights_p = params->weights->append(params->weights);
            array_ia* samples_p = params->samples->append(params->samples);

            weights_p->vappend(weights_p, 1, 0);
            init_correlation_samples(samples_p->append(samples_p),
                                     params->terms->_[pass]); /*channel 0*/
        }
    } else if (channel_count == 2) {
        switch (params->correlation_passes) {
        case 0:
            break;
        case 1:
            params->terms->vset(params->terms, 1, 18);
            break;
        case 2:
            params->terms->vset(params->terms, 2, 17, 18);
            break;
        case 5:
            params->terms->vset(params->terms, 5, 3, 17, 2, 18, 18);
            break;
        case 10:
            params->terms->vset(params->terms, 10,
                                4, 17, -1, 5, 3, 2, -2, 18, 18, 18);
            break;
        case 16:
            params->terms->vset(params->terms, 16,
                                2, 18, -1, 8, 6, 3, 5, 7,
                                4, 2, 18, -2, 3, 2, 18, 18);
            break;
        default:
            /*invalid correlation pass count*/
            assert(0);
        }
        params->deltas->mset(params->deltas, params->terms->len, 2);
        for (pass = 0; pass < params->terms->len; pass++) {
            array_i* weights_p = params->weights->append(params->weights);
            array_ia* samples_p = params->samples->append(params->samples);

            weights_p->vappend(weights_p, 2, 0, 0);
            init_correlation_samples(samples_p->append(samples_p),
                                     params->terms->_[pass]); /*channel 0*/
            init_correlation_samples(samples_p->append(samples_p),
                                     params->terms->_[pass]); /*channel 1*/
        }
    } else {
        /*invalid channel count*/
        assert(0);
    }

    entropy = params->entropies->append(params->entropies);
    entropy->mset(entropy, 3, 0);
    entropy = params->entropies->append(params->entropies);
    entropy->mset(entropy, 3, 0);
}

static void
init_correlation_samples(array_i* samples,
                         int correlation_term)
{
    switch (correlation_term) {
    case 18:
    case 17:
        samples->mset(samples, 2, 0);
        break;
    case 8:
    case 7:
    case 6:
    case 5:
    case 4:
    case 3:
    case 2:
    case 1:
        samples->mset(samples, correlation_term, 0);
        break;
    case -1:
    case -2:
    case -3:
        samples->mset(samples, 1, 0);
        break;
    default:
        /*invalid correlation term*/
        assert(0);
    }
}

static void
roundtrip_block_parameters(struct encoding_parameters* params)
{
    unsigned pass;
    unsigned channel;
    unsigned sample;

    /*terms and deltas remain unchanged*/

    /*weights are round-tripped from previous block*/
    for (pass = 0; pass < params->weights->len; pass++) {
        array_i* weights_p = params->weights->_[pass];
        for (channel = 0; channel < weights_p->len; channel++) {
            weights_p->_[channel] =
                restore_weight(store_weight(weights_p->_[channel]));
        }
    }

    /*samples are round-tripped from previous block*/
    for (pass = 0; pass < params->samples->len; pass++) {
        array_ia* samples_p = params->samples->_[pass];
        for (channel = 0; channel < samples_p->len; channel++) {
            array_i* samples_p_c = samples_p->_[channel];
            for (sample = 0; sample < samples_p_c->len; sample++) {
                samples_p_c->_[sample] =
                    wv_exp2(wv_log2(samples_p_c->_[sample]));
            }
        }
    }

    /*entropy variables are round-tripped from previous block*/
    for (channel = 0; channel < params->effective_channel_count; channel++) {
        for (sample = 0; sample < 3; sample++) {
            params->entropies->_[channel]->_[sample] =
                wv_exp2(wv_log2(params->entropies->_[channel]->_[sample]));
        }
    }
}

static void
free_block_parameters(struct encoding_parameters* params)
{
    params->terms->del(params->terms);
    params->deltas->del(params->deltas);
    params->weights->del(params->weights);
    params->samples->del(params->samples);
    params->entropies->del(params->entropies);
}

static void
add_block_offset(FILE* file, array_o* offsets)
{
    fpos_t* pos = malloc(sizeof(fpos_t));
    fgetpos(file, pos);
    offsets->append(offsets, pos);
}

static void
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
                   uint32_t crc)
{
    bs->write_bytes(bs, (uint8_t*)"wvpk", 4);
    bs->write(bs, 32, sub_blocks_size + 24);
    bs->write(bs, 16, WAVPACK_VERSION);
    bs->write(bs, 8, 0);              /*track number*/
    bs->write(bs, 8, 0);              /*index number*/
    bs->write(bs, 32, 0xFFFFFFFF);    /*total samples placeholder*/
    bs->write(bs, 32, block_index);
    bs->write(bs, 32, block_samples);
    bs->write(bs, 2, bits_per_sample / 8 - 1);
    bs->write(bs, 1, 2 - channel_count);
    bs->write(bs, 1, 0);              /*hybrid mode*/
    bs->write(bs, 1, joint_stereo);
    bs->write(bs, 1, correlation_pass_count > 5);
    bs->write(bs, 1, 0);              /*hybrid noise shaping*/
    bs->write(bs, 1, 0);              /*floating point data*/
    bs->write(bs, 1, wasted_bps > 0); /*has extended size integers*/
    bs->write(bs, 1, 0);              /*hybrid controls bitrate*/
    bs->write(bs, 1, 0);              /*hybrid noise balanced*/
    bs->write(bs, 1, first_block);
    bs->write(bs, 1, last_block);
    bs->write(bs, 5, 0);              /*left shift data*/
    bs->write(bs, 5, maximum_magnitude);
    bs->write(bs, 4, encoded_sample_rate(sample_rate));
    bs->write(bs, 2, 0);              /*reserved*/
    bs->write(bs, 1, 0);              /*use IIR*/
    bs->write(bs, 1, false_stereo);
    bs->write(bs, 1, 0);              /*reserved*/
    bs->write(bs, 32, crc);
}

static unsigned
encoded_sample_rate(unsigned sample_rate)
{
    switch (sample_rate) {
    case 6000:   return 0;
    case 8000:   return 1;
    case 9600:   return 2;
    case 11025:  return 3;
    case 12000:  return 4;
    case 16000:  return 5;
    case 22050:  return 6;
    case 24000:  return 7;
    case 32000:  return 8;
    case 44100:  return 9;
    case 48000:  return 10;
    case 64000:  return 11;
    case 88200:  return 12;
    case 96000:  return 13;
    case 192000: return 14;
    default:     return 15;
    }
}

static void
encode_block(BitstreamWriter* bs,
             struct wavpack_encoder_context* context,
             const pcmreader* pcmreader,
             struct encoding_parameters* parameters,
             const array_ia* channels,
             uint32_t block_index, int first_block, int last_block)
{
    int false_stereo;
    unsigned effective_channel_count;
    unsigned magnitude;
    unsigned wasted_bps;
    uint32_t total_frames;
    array_ia* shifted = context->cache.shifted;
    array_ia* mid_side = context->cache.mid_side;
    array_ia* correlated = context->cache.correlated;
    BitstreamWriter* sub_blocks = context->cache.sub_blocks;
    BitstreamWriter* sub_block = context->cache.sub_block;
    uint32_t crc;

    assert((channels->len == 1) || (channels->len == 2));

    shifted->reset(shifted);
    mid_side->reset(mid_side);
    correlated->reset(correlated);
    bw_reset_recorder(sub_blocks);

    total_frames = channels->_[0]->len;

    if ((channels->len == 1) ||
        (parameters->try_false_stereo &&
         (channels->_[0]->equals(channels->_[0], channels->_[1])))) {
        if (channels->len == 1) {
            false_stereo = 0;
            effective_channel_count = 1;
        } else {
            false_stereo = 1;
            effective_channel_count = 1;
        }

        /*calculate the maximum magnitude of channel_0 and channel_1*/
        magnitude = maximum_magnitude(channels->_[0]);

        /*calculate and apply any wasted least-significant bits*/
        if (parameters->try_wasted_bits) {
            wasted_bps = wasted_bits(channels->_[0]);
            if (wasted_bps > 0) {
                unsigned i;
                shifted->append(shifted);
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
        false_stereo = 0;
        effective_channel_count = 2;

        /*calculate the maximum magnitude of channel_0 and channel_1*/
        magnitude = MAX(maximum_magnitude(channels->_[0]),
                        maximum_magnitude(channels->_[1]));

        /*calculate and apply any wasted least-significant bits*/
        if (parameters->try_wasted_bits) {
            wasted_bps = MIN(wasted_bits(channels->_[0]),
                             wasted_bits(channels->_[1]));
            if (wasted_bps > 0) {
                unsigned i;
                shifted->append(shifted);
                shifted->append(shifted);
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

        /*apply joint stereo if requested*/
        if (parameters->try_joint_stereo) {
            apply_joint_stereo(shifted, mid_side);
        } else {
            shifted->copy(shifted, mid_side);
        }
    }

    if (effective_channel_count == parameters->effective_channel_count) {
        roundtrip_block_parameters(parameters);
    } else {
        reset_block_parameters(parameters, effective_channel_count);
    }


    /*if first block in file, write wave header*/
    if (!context->wave.header_written) {
        bw_reset_recorder(sub_block);
        if (context->wave.header_data == NULL) {
            /*no external RIFF WAVE header,
              so generate temporary one to be populated later*/
            if (context->wave.footer_data == NULL) {
                write_dummy_wave_header(sub_block, pcmreader,
                                        0);
            } else {
                write_dummy_wave_header(sub_block, pcmreader,
                                        context->wave.footer_len);
            }
            write_sub_block(sub_blocks, WV_DUMMY, 0, sub_block);
        } else {
            /*external header given, so output as-is*/
            sub_block->write_bytes(sub_block,
                                   context->wave.header_data,
                                   context->wave.header_len);
            write_sub_block(sub_blocks, WV_WAVE_HEADER, 1, sub_block);
        }

        context->wave.header_written = 1;
    }

    /*if correlation passes, write three correlation sub blocks*/
    if (parameters->terms->len > 0) {
        bw_reset_recorder(sub_block);
        write_correlation_terms(sub_block,
                                parameters->terms,
                                parameters->deltas);
        write_sub_block(sub_blocks, WV_TERMS, 0, sub_block);

        bw_reset_recorder(sub_block);
        write_correlation_weights(sub_block,
                                  parameters->weights,
                                  effective_channel_count);
        write_sub_block(sub_blocks, WV_WEIGHTS, 0, sub_block);

        bw_reset_recorder(sub_block);
        write_correlation_samples(sub_block,
                                  parameters->terms,
                                  parameters->samples,
                                  effective_channel_count);
        write_sub_block(sub_blocks, WV_SAMPLES, 0, sub_block);
    }

    /*if wasted BPS, write extended integers sub block*/
    if (wasted_bps > 0) {
        bw_reset_recorder(sub_block);
        sub_block->build(sub_block, "8u 8u 8u 8u",
                         0, wasted_bps, 0, 0);
        write_sub_block(sub_blocks, WV_INT32_INFO, 0, sub_block);
    }

    /*if total channels > 2, write channel info sub block*/
    if (pcmreader->channels > 2) {
        bw_reset_recorder(sub_block);
        sub_block->build(sub_block, "8u 32u",
                         pcmreader->channels,
                         pcmreader->channel_mask);
        write_sub_block(sub_blocks, WV_CHANNEL_INFO, 0, sub_block);
    }

    /*if nonstandard sample rate, write sample rate sub block*/
    if (encoded_sample_rate(pcmreader->sample_rate) == 15) {
        bw_reset_recorder(sub_block);
        sub_block->write(sub_block, 32, pcmreader->sample_rate);
        write_sub_block(sub_blocks, WV_SAMPLE_RATE, 1, sub_block);
    }

    if (effective_channel_count == 1) {         /*1 channel block*/
        if (parameters->terms->len > 0) {
            correlate_channels(correlated,
                               shifted,
                               parameters->terms,
                               parameters->deltas,
                               parameters->weights,
                               parameters->samples,
                               1);
        } else {
            shifted->copy(shifted, correlated);
        }
    } else {                                    /*2 channel block*/
        /*perform channel correlation*/
        if (parameters->terms->len > 0) {
            correlate_channels(correlated,
                               mid_side,
                               parameters->terms,
                               parameters->deltas,
                               parameters->weights,
                               parameters->samples,
                               2);
        } else {
            mid_side->copy(mid_side, correlated);
        }
    }

    /*write entropy variables sub block*/
    bw_reset_recorder(sub_block);
    write_entropy_variables(sub_block,
                            effective_channel_count,
                            parameters->entropies);
    write_sub_block(sub_blocks, WV_ENTROPY, 0, sub_block);

    /*write bitstream sub block*/
    bw_reset_recorder(sub_block);
    write_bitstream(sub_block,
                    parameters->entropies,
                    correlated);
    write_sub_block(sub_blocks, WV_BITSTREAM, 0, sub_block);

    /*finally, write block header using size of all sub blocks*/
    write_block_header(bs,
                       sub_blocks->bytes_written(sub_blocks),
                       block_index,
                       total_frames,
                       pcmreader->bits_per_sample,
                       channels->len,
                       (channels->len == 2) && parameters->try_joint_stereo,
                       parameters->terms->len,
                       wasted_bps,
                       first_block,
                       last_block,
                       magnitude,
                       pcmreader->sample_rate,
                       false_stereo,
                       crc);

    /*write sub block data to stream*/
    bw_rec_copy(bs, sub_blocks);
}

static void
write_sub_block(BitstreamWriter* block,
                unsigned metadata_function,
                unsigned nondecoder_data,
                BitstreamWriter* sub_block)
{
    unsigned actual_size_1_less;

    sub_block->byte_align(sub_block);
    actual_size_1_less = sub_block->bytes_written(sub_block) % 2;
    block->write(block, 5, metadata_function);
    block->write(block, 1, nondecoder_data);
    block->write(block, 1, actual_size_1_less);
    if (sub_block->bytes_written(sub_block) > (255 * 2)) {
        block->write(block, 1, 1);
        block->write(block, 24,
                     (sub_block->bytes_written(sub_block) / 2) +
                     actual_size_1_less);
    } else {
        block->write(block, 1, 0);
        block->write(block, 8,
                     (sub_block->bytes_written(sub_block) / 2) +
                     actual_size_1_less);
    }

    bw_rec_copy(block, sub_block);

    if (actual_size_1_less) {
        block->write(block, 8, 0);
    }
}

static void
write_correlation_terms(BitstreamWriter* bs,
                        const array_i* terms,
                        const array_i* deltas)
{
    unsigned total;
    unsigned pass;

    assert(terms->len == deltas->len);

    for (total = terms->len, pass = terms->len - 1;
         total > 0; total--,pass--) {
        bs->write(bs, 5, terms->_[pass] + 5);
        bs->write(bs, 3, deltas->_[pass]);
    }
}

static int
store_weight(int weight)
{
    weight = MIN(MAX(weight, -1024), 1024);

    if (weight > 0) {
        return (weight - ((weight + (1 << 6)) >> 7) + 4) >> 3;
    } else if (weight == 0) {
        return 0;
    } else {
        return (weight + 4) >> 3;
    }
}

static int
restore_weight(int value)
{
    if (value > 0) {
        return (value << 3) + (((value << 3) + (1 << 6)) >> 7);
    } else if (value == 0) {
        return 0;
    } else {
        return value << 3;
    }
}

static void
write_correlation_weights(BitstreamWriter* bs,
                          const array_ia* weights,
                          unsigned channel_count)
{
    unsigned total;
    unsigned pass;

    for (total = weights->len, pass = weights->len - 1;
         total > 0; total--,pass--) {
        bs->write(bs, 8, store_weight(weights->_[pass]->_[0]));
        if (channel_count == 2)
            bs->write(bs, 8, store_weight(weights->_[pass]->_[1]));
    }
}

static void
write_correlation_samples(BitstreamWriter* bs,
                          const array_i* terms,
                          const array_iaa* samples,
                          unsigned channel_count)
{
    unsigned total;
    unsigned pass;

    if (channel_count == 2) {
        for (total = terms->len, pass = terms->len - 1;
             total > 0; total--,pass--) {
            if ((17 <= terms->_[pass]) && (terms->_[pass] <= 18)) {
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[0]->_[0]));
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[0]->_[1]));
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[1]->_[0]));
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[1]->_[1]));
            } else if ((1 <= terms->_[pass]) && (terms->_[pass] <= 8)) {
                unsigned s;
                for (s = 0; s < terms->_[pass]; s++) {
                    bs->write_signed(bs, 16,
                                     wv_log2(samples->_[pass]->_[0]->_[s]));
                    bs->write_signed(bs, 16,
                                     wv_log2(samples->_[pass]->_[1]->_[s]));
                }
            } else if ((-3 <= terms->_[pass]) && (terms->_[pass] <= -1)) {
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[0]->_[0]));
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[1]->_[0]));
            } else {
                /*invalid correlation term*/
                assert(0);
            }
        }
    } else if (channel_count == 1) {
        for (total = terms->len, pass = terms->len - 1;
             total > 0; total--,pass--) {
            if ((17 <= terms->_[pass]) && (terms->_[pass] <= 18)) {
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[0]->_[0]));
                bs->write_signed(bs, 16, wv_log2(samples->_[pass]->_[0]->_[1]));
            } else if ((1 <= terms->_[pass]) && (terms->_[pass] <= 8)) {
                unsigned s;
                for (s = 0; s < terms->_[pass]; s++) {
                    bs->write_signed(bs, 16,
                                     wv_log2(samples->_[pass]->_[0]->_[s]));
                }
            } else {
                /*invalid correlation term*/
                assert(0);
            }
        }
    } else {
        /*channel count should be 1 or 2*/
        assert(0);
    }
}

static void
correlate_channels(array_ia* correlated_samples,
                   array_ia* uncorrelated_samples,
                   array_i* terms,
                   array_i* deltas,
                   array_ia* weights,
                   array_iaa* samples,
                   unsigned channel_count)
{
    unsigned pass;
    unsigned total;

    assert(terms->len == deltas->len);
    assert(terms->len == weights->len);
    assert(terms->len == samples->len);
    assert(uncorrelated_samples->len == channel_count);

    if (channel_count == 1) {
        array_i* input_channel = array_i_new();
        array_i* output_channel = array_i_new();
        input_channel->swap(input_channel, uncorrelated_samples->_[0]);
        for (pass = terms->len - 1,total = terms->len;
             total > 0; pass--,total--) {
            correlate_1ch(output_channel,
                          input_channel,
                          terms->_[pass],
                          deltas->_[pass],
                          &(weights->_[pass]->_[0]),
                          samples->_[pass]->_[0]);

            if (total > 1) {
                input_channel->swap(input_channel, output_channel);
            }
        }

        correlated_samples->reset(correlated_samples);
        output_channel->swap(output_channel,
                             correlated_samples->append(correlated_samples));
        input_channel->del(input_channel);
        output_channel->del(output_channel);
    } else if (channel_count == 2) {
        for (pass = terms->len - 1,total = terms->len;
             total > 0; pass--,total--) {
            correlate_2ch(correlated_samples,
                          uncorrelated_samples,
                          terms->_[pass],
                          deltas->_[pass],
                          weights->_[pass],
                          samples->_[pass]);
            if (total > 1) {
                uncorrelated_samples->swap(uncorrelated_samples,
                                           correlated_samples);
            }
        }
    } else {
        /*invalid channel count*/
        assert(0);
    }
}

static int
apply_weight(int weight, int64_t sample)
{
    return (int)(((weight * sample) + 512) >> 10);
}

static int
update_weight(int64_t source, int result, int delta)
{
    if ((source == 0) || (result == 0)) {
        return 0;
    } else if ((source ^ result) >= 0) {
        return delta;
    } else {
        return -delta;
    }
}

static void
correlate_1ch(array_i* correlated,
              const array_i* uncorrelated,
              int term,
              int delta,
              int* weight,
              array_i* samples)
{
    unsigned i;
    correlated->reset(correlated);

    if (term == 18) {
        array_i* uncorr = array_i_new();

        assert(samples->len == 2);
        uncorr->vappend(uncorr, 2, samples->_[1], samples->_[0]);
        uncorr->extend(uncorr, uncorrelated);

        for (i = 2; i < uncorr->len; i++) {
            const int64_t temp = (3 * uncorr->_[i - 1] - uncorr->_[i - 2]) >> 1;
            correlated->append(correlated,
                               uncorr->_[i] - apply_weight(*weight, temp));
            *weight += update_weight(temp, correlated->_[i - 2], delta);
        }

        /*round-trip the final 2 uncorrelated samples for the next block*/
        samples->_[1] = uncorr->_[uncorr->len - 2];
        samples->_[0] = uncorr->_[uncorr->len - 1];

        uncorr->del(uncorr);
    } else if (term == 17) {
        array_i* uncorr = array_i_new();

        assert(samples->len == 2);
        uncorr->vappend(uncorr, 2, samples->_[1], samples->_[0]);
        uncorr->extend(uncorr, uncorrelated);

        for (i = 2; i < uncorr->len; i++) {
            const int64_t temp = 2 * uncorr->_[i - 1] - uncorr->_[i - 2];
            correlated->append(correlated,
                               uncorr->_[i] - apply_weight(*weight, temp));
            *weight += update_weight(temp, correlated->_[i - 2], delta);
        }

        /*round-trip the final 2 uncorrelated samples for the next block*/
        samples->_[1] = uncorr->_[uncorr->len - 2];
        samples->_[0] = uncorr->_[uncorr->len - 1];

        uncorr->del(uncorr);
    } else if ((1 <= term) && (term <= 8)) {
        array_i* uncorr = array_i_new();

        assert(samples->len == term);
        uncorr->extend(uncorr, samples);
        uncorr->extend(uncorr, uncorrelated);

        for (i = term; i < uncorr->len; i++) {
            correlated->append(correlated, uncorr->_[i] -
                               apply_weight(*weight, uncorr->_[i - term]));
            *weight += update_weight(uncorr->_[i - term],
                                     correlated->_[i - term], delta);
        }

        /*round-trip the final "terms" uncorrelated samples for the next block*/
        uncorrelated->tail(uncorrelated, term, samples);

        uncorr->del(uncorr);
    } else {
        /*invalid correlation term*/
        assert(0);
    }

    assert(correlated->len == uncorrelated->len);
}

static void
correlate_2ch(array_ia* correlated,
              const array_ia* uncorrelated,
              int term,
              int delta,
              array_i* weights,
              array_ia* samples)
{
    assert(uncorrelated->len == 2);
    assert(uncorrelated->_[0]->len == uncorrelated->_[1]->len);
    assert(weights->len == 2);
    assert(samples->len == 2);

    if (((17 <= term) && (term <= 18)) ||
        ((1 <= term) && (term <= 8))) {
        correlated->reset(correlated);
        correlate_1ch(correlated->append(correlated),
                      uncorrelated->_[0],
                      term, delta, &(weights->_[0]), samples->_[0]);
        correlate_1ch(correlated->append(correlated),
                      uncorrelated->_[1],
                      term, delta, &(weights->_[1]), samples->_[1]);
    } else if ((-3 <= term) && (term <= -1)) {
        array_ia* uncorr = array_ia_new();
        array_i* uncorr_0;
        array_i* uncorr_1;
        unsigned i;

        assert(samples->_[0]->len == 1);
        assert(samples->_[1]->len == 1);
        uncorr_0 = uncorr->append(uncorr);
        uncorr_1 = uncorr->append(uncorr);
        uncorr_0->extend(uncorr_0, samples->_[1]);
        uncorr_0->extend(uncorr_0, uncorrelated->_[0]);
        uncorr_1->extend(uncorr_1, samples->_[0]);
        uncorr_1->extend(uncorr_1, uncorrelated->_[1]);

        correlated->reset(correlated);
        correlated->append(correlated);
        correlated->append(correlated);

        if (term == -1) {
            for (i = 1; i < uncorr_0->len; i++) {
                array_i_append(correlated->_[0],
                               uncorr_0->_[i] -
                               apply_weight(weights->_[0],
                                            uncorr_1->_[i - 1]));
                array_i_append(correlated->_[1],
                               uncorr_1->_[i] -
                               apply_weight(weights->_[1],
                                            uncorr_0->_[i]));
                weights->_[0] += update_weight(uncorr_1->_[i - 1],
                                               correlated->_[0]->_[i - 1],
                                               delta);
                weights->_[1] += update_weight(uncorr_0->_[i],
                                               correlated->_[1]->_[i - 1],
                                               delta);
                weights->_[0] = MAX(MIN(weights->_[0], 1024), -1024);
                weights->_[1] = MAX(MIN(weights->_[1], 1024), -1024);
            }
        } else if (term == -2) {
            for (i = 1; i < uncorr_0->len; i++) {
                array_i_append(correlated->_[0],
                               uncorr_0->_[i] -
                               apply_weight(weights->_[0],
                                            uncorr_1->_[i]));
                array_i_append(correlated->_[1],
                               uncorr_1->_[i] -
                               apply_weight(weights->_[1],
                                            uncorr_0->_[i - 1]));
                weights->_[0] += update_weight(uncorr_1->_[i],
                                               correlated->_[0]->_[i - 1],
                                               delta);
                weights->_[1] += update_weight(uncorr_0->_[i - 1],
                                               correlated->_[1]->_[i - 1],
                                               delta);
                weights->_[0] = MAX(MIN(weights->_[0], 1024), -1024);
                weights->_[1] = MAX(MIN(weights->_[1], 1024), -1024);
            }
        } else if (term == -3) {
            for (i = 1; i < uncorr_0->len; i++) {
                array_i_append(correlated->_[0],
                               uncorr_0->_[i] -
                               apply_weight(weights->_[0],
                                            uncorr_1->_[i - 1]));
                array_i_append(correlated->_[1],
                               uncorr_1->_[i] -
                               apply_weight(weights->_[1],
                                            uncorr_0->_[i - 1]));
                weights->_[0] += update_weight(uncorr_1->_[i - 1],
                                               correlated->_[0]->_[i - 1],
                                               delta);
                weights->_[1] += update_weight(uncorr_0->_[i - 1],
                                               correlated->_[1]->_[i - 1],
                                               delta);
                weights->_[0] = MAX(MIN(weights->_[0], 1024), -1024);
                weights->_[1] = MAX(MIN(weights->_[1], 1024), -1024);
            }
        } else {
            /*shouldn't get here*/
            assert(0);
        }

        /*round-trip the final uncorrelated sample for the next block*/
        samples->_[1]->_[0] = uncorr_0->_[uncorr_0->len - 1];
        samples->_[0]->_[0] = uncorr_1->_[uncorr_1->len - 1];

        uncorr->del(uncorr);
    } else {
        /*invalid correlation term*/
        assert(0);
    }
}

static void
write_entropy_variables(BitstreamWriter* bs,
                        unsigned channel_count,
                        const array_ia* entropies)
{
    if (channel_count == 1) {
        assert(entropies->_[0]->len == 3);
        bs->write(bs, 16, wv_log2(entropies->_[0]->_[0]));
        bs->write(bs, 16, wv_log2(entropies->_[0]->_[1]));
        bs->write(bs, 16, wv_log2(entropies->_[0]->_[2]));
    } else if (channel_count == 2) {
        assert(entropies->_[0]->len == 3);
        assert(entropies->_[1]->len == 3);
        bs->write(bs, 16, wv_log2(entropies->_[0]->_[0]));
        bs->write(bs, 16, wv_log2(entropies->_[0]->_[1]));
        bs->write(bs, 16, wv_log2(entropies->_[0]->_[2]));
        bs->write(bs, 16, wv_log2(entropies->_[1]->_[0]));
        bs->write(bs, 16, wv_log2(entropies->_[1]->_[1]));
        bs->write(bs, 16, wv_log2(entropies->_[1]->_[2]));
    } else {
        /*invalid channel count*/
        assert(0);
    }
}

static inline unsigned
LOG2(unsigned value)
{
    unsigned bits = 0;
    assert(value > 0);
    while (value) {
        bits++;
        value >>= 1;
    }
    return bits - 1;
}

static int
wv_log2(int value)
{
    const static unsigned WLOG[] =
        {0x00, 0x01, 0x03, 0x04, 0x06, 0x07, 0x09, 0x0a,
         0x0b, 0x0d, 0x0e, 0x10, 0x11, 0x12, 0x14, 0x15,
         0x16, 0x18, 0x19, 0x1a, 0x1c, 0x1d, 0x1e, 0x20,
         0x21, 0x22, 0x24, 0x25, 0x26, 0x28, 0x29, 0x2a,
         0x2c, 0x2d, 0x2e, 0x2f, 0x31, 0x32, 0x33, 0x34,
         0x36, 0x37, 0x38, 0x39, 0x3b, 0x3c, 0x3d, 0x3e,
         0x3f, 0x41, 0x42, 0x43, 0x44, 0x45, 0x47, 0x48,
         0x49, 0x4a, 0x4b, 0x4d, 0x4e, 0x4f, 0x50, 0x51,
         0x52, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a,
         0x5c, 0x5d, 0x5e, 0x5f, 0x60, 0x61, 0x62, 0x63,
         0x64, 0x66, 0x67, 0x68, 0x69, 0x6a, 0x6b, 0x6c,
         0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72, 0x74, 0x75,
         0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d,
         0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85,
         0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d,
         0x8e, 0x8f, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95,
         0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b, 0x9b, 0x9c,
         0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4,
         0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xa9, 0xaa, 0xab,
         0xac, 0xad, 0xae, 0xaf, 0xb0, 0xb1, 0xb2, 0xb2,
         0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xb9,
         0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf, 0xc0, 0xc0,
         0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc6, 0xc7,
         0xc8, 0xc9, 0xca, 0xcb, 0xcb, 0xcc, 0xcd, 0xce,
         0xcf, 0xd0, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd4,
         0xd5, 0xd6, 0xd7, 0xd8, 0xd8, 0xd9, 0xda, 0xdb,
         0xdc, 0xdc, 0xdd, 0xde, 0xdf, 0xe0, 0xe0, 0xe1,
         0xe2, 0xe3, 0xe4, 0xe4, 0xe5, 0xe6, 0xe7, 0xe7,
         0xe8, 0xe9, 0xea, 0xea, 0xeb, 0xec, 0xed, 0xee,
         0xee, 0xef, 0xf0, 0xf1, 0xf1, 0xf2, 0xf3, 0xf4,
         0xf4, 0xf5, 0xf6, 0xf7, 0xf7, 0xf8, 0xf9, 0xf9,
         0xfa, 0xfb, 0xfc, 0xfc, 0xfd, 0xfe, 0xff, 0xff};

    unsigned a = abs(value) + (abs(value) >> 9);
    unsigned c = (a != 0) ? (LOG2(a) + 1) : 0;

    if (value >= 0) {
        if ((0 <= a) && (a < 256)) {
            return (c << 8) + WLOG[(a << (9 - c)) % 256];
        } else {
            return (c << 8) + WLOG[(a >> (c - 9)) % 256];
        }
    } else {
        if ((0 <= a) && (a < 256)) {
            return -((c << 8) + WLOG[(a << (9 - c)) % 256]);
        } else {
            return -((c << 8) + WLOG[(a >> (c - 9)) % 256]);
        }
    }
}

static int
wv_exp2(int value)
{
    const static int EXP2[] =
        {0x100, 0x101, 0x101, 0x102, 0x103, 0x103, 0x104, 0x105,
         0x106, 0x106, 0x107, 0x108, 0x108, 0x109, 0x10a, 0x10b,
         0x10b, 0x10c, 0x10d, 0x10e, 0x10e, 0x10f, 0x110, 0x110,
         0x111, 0x112, 0x113, 0x113, 0x114, 0x115, 0x116, 0x116,
         0x117, 0x118, 0x119, 0x119, 0x11a, 0x11b, 0x11c, 0x11d,
         0x11d, 0x11e, 0x11f, 0x120, 0x120, 0x121, 0x122, 0x123,
         0x124, 0x124, 0x125, 0x126, 0x127, 0x128, 0x128, 0x129,
         0x12a, 0x12b, 0x12c, 0x12c, 0x12d, 0x12e, 0x12f, 0x130,
         0x130, 0x131, 0x132, 0x133, 0x134, 0x135, 0x135, 0x136,
         0x137, 0x138, 0x139, 0x13a, 0x13a, 0x13b, 0x13c, 0x13d,
         0x13e, 0x13f, 0x140, 0x141, 0x141, 0x142, 0x143, 0x144,
         0x145, 0x146, 0x147, 0x148, 0x148, 0x149, 0x14a, 0x14b,
         0x14c, 0x14d, 0x14e, 0x14f, 0x150, 0x151, 0x151, 0x152,
         0x153, 0x154, 0x155, 0x156, 0x157, 0x158, 0x159, 0x15a,
         0x15b, 0x15c, 0x15d, 0x15e, 0x15e, 0x15f, 0x160, 0x161,
         0x162, 0x163, 0x164, 0x165, 0x166, 0x167, 0x168, 0x169,
         0x16a, 0x16b, 0x16c, 0x16d, 0x16e, 0x16f, 0x170, 0x171,
         0x172, 0x173, 0x174, 0x175, 0x176, 0x177, 0x178, 0x179,
         0x17a, 0x17b, 0x17c, 0x17d, 0x17e, 0x17f, 0x180, 0x181,
         0x182, 0x183, 0x184, 0x185, 0x187, 0x188, 0x189, 0x18a,
         0x18b, 0x18c, 0x18d, 0x18e, 0x18f, 0x190, 0x191, 0x192,
         0x193, 0x195, 0x196, 0x197, 0x198, 0x199, 0x19a, 0x19b,
         0x19c, 0x19d, 0x19f, 0x1a0, 0x1a1, 0x1a2, 0x1a3, 0x1a4,
         0x1a5, 0x1a6, 0x1a8, 0x1a9, 0x1aa, 0x1ab, 0x1ac, 0x1ad,
         0x1af, 0x1b0, 0x1b1, 0x1b2, 0x1b3, 0x1b4, 0x1b6, 0x1b7,
         0x1b8, 0x1b9, 0x1ba, 0x1bc, 0x1bd, 0x1be, 0x1bf, 0x1c0,
         0x1c2, 0x1c3, 0x1c4, 0x1c5, 0x1c6, 0x1c8, 0x1c9, 0x1ca,
         0x1cb, 0x1cd, 0x1ce, 0x1cf, 0x1d0, 0x1d2, 0x1d3, 0x1d4,
         0x1d6, 0x1d7, 0x1d8, 0x1d9, 0x1db, 0x1dc, 0x1dd, 0x1de,
         0x1e0, 0x1e1, 0x1e2, 0x1e4, 0x1e5, 0x1e6, 0x1e8, 0x1e9,
         0x1ea, 0x1ec, 0x1ed, 0x1ee, 0x1f0, 0x1f1, 0x1f2, 0x1f4,
         0x1f5, 0x1f6, 0x1f8, 0x1f9, 0x1fa, 0x1fc, 0x1fd, 0x1ff};
    if ((-32768 <= value) && (value < -2304)) {
        return -(EXP2[-value & 0xFF] << ((-value >> 8) - 9));
    } else if ((-2304 <= value) && (value < 0)) {
        return -(EXP2[-value & 0xFF] >> (9 - (-value >> 8)));
    } else if ((0 <= value) && (value <= 2304)) {
        return EXP2[value & 0xFF] >> (9 - (value >> 8));
    } else if ((2304 < value) && (value <= 32767)) {
        return EXP2[value & 0xFF] << ((value >> 8) - 9);
    } else {
        /*shouldn't get here from a 16-bit value*/
        abort();
        return 0;
    }
}

#define UNDEFINED (-1)

static void
write_bitstream(BitstreamWriter* bs,
                array_ia* entropies,
                const array_ia* residuals)
{
    const unsigned total_samples = (residuals->len * residuals->_[0]->len);
    unsigned i = 0;
    struct wavpack_residual res_i_1; /*residual (i - 1)*/
    struct wavpack_residual res_i;   /*residual i*/
    int u_i_2;                       /*unary (i - 2)*/

    res_i_1.zeroes = UNDEFINED;
    u_i_2 = UNDEFINED;
    res_i_1.m = UNDEFINED;
    res_i_1.offset = res_i_1.add = res_i_1.sign = UINT_MAX; /*placeholders*/

    while (i < total_samples) {
        const int r = residuals->_[i % residuals->len]->_[i / residuals->len];

        if ((entropies->_[0]->_[0] < 2) &&
            (entropies->_[1]->_[0] < 2) &&
            unary_undefined(u_i_2, res_i_1.m)) {

            if ((res_i_1.zeroes != UNDEFINED) &&
                (res_i_1.m == UNDEFINED)) { /*in a block of zeroes*/
                if (r == 0) {                  /*continue block of zeroes*/
                    res_i_1.zeroes++;
                } else {                       /*end block of zeroes*/
                    /*stick residual_{i} at end of zeroes*/
                    encode_residual(r,
                                    entropies->_[i % residuals->len],
                                    &(res_i_1.m),
                                    &(res_i_1.offset),
                                    &(res_i_1.add),
                                    &(res_i_1.sign));
                }
            } else {                           /*start block of zeroes*/
                if (r == 0) {
                    /*initialize zeroes*/
                    res_i.zeroes = 1;

                    /*clear residual_{i}*/
                    res_i.m = UNDEFINED;

                    /*flush previous residual_{i - 1}*/
                    u_i_2 = flush_residual(bs,
                                           u_i_2,
                                           res_i_1.m,
                                           res_i_1.offset,
                                           res_i_1.add,
                                           res_i_1.sign,
                                           res_i_1.zeroes,
                                           0); /*?*/
                    res_i_1 = res_i;

                    /*clear entropies*/
                    entropies->_[0]->mset(entropies->_[0], 3, 0);
                    entropies->_[1]->mset(entropies->_[1], 3, 0);
                } else {                      /*false-alarm block of zeroes*/
                    res_i.zeroes = 0;
                    encode_residual(r,
                                    entropies->_[i % residuals->len],
                                    &(res_i.m),
                                    &(res_i.offset),
                                    &(res_i.add),
                                    &(res_i.sign));
                    u_i_2 = flush_residual(bs,
                                           u_i_2,
                                           res_i_1.m,
                                           res_i_1.offset,
                                           res_i_1.add,
                                           res_i_1.sign,
                                           res_i_1.zeroes,
                                           res_i.m);
                    res_i_1 = res_i;
                }
            }
        } else {                               /*encode regular residual*/
            res_i.zeroes = UNDEFINED;
            encode_residual(r,
                            entropies->_[i % residuals->len],
                            &(res_i.m),
                            &(res_i.offset),
                            &(res_i.add),
                            &(res_i.sign));
            u_i_2 = flush_residual(bs,
                                   u_i_2,
                                   res_i_1.m,
                                   res_i_1.offset,
                                   res_i_1.add,
                                   res_i_1.sign,
                                   res_i_1.zeroes,
                                   res_i.m);
            res_i_1 = res_i;
        }

        i++;
    }

    /*flush final residual*/
    u_i_2 = flush_residual(bs,
                           u_i_2,
                           res_i_1.m,
                           res_i_1.offset,
                           res_i_1.add,
                           res_i_1.sign,
                           res_i_1.zeroes,
                           0);
}

static int
unary_undefined(int u_j_1, int m_j)
{
    if (m_j == UNDEFINED) {
        return 1; /*u_j is undefined*/
    } else if ((m_j == 0) && (u_j_1 != UNDEFINED) && ((u_j_1 % 2) == 0)) {
        return 1; /*u_j is undefined*/
    } else {
        return 0; /*u_j is not undefined*/
    }
}

static int
flush_residual(BitstreamWriter* bs,
               int u_i_2, int m_i_1, unsigned offset_i_1, unsigned add_i_1,
               unsigned sign_i_1, int zeroes_i_1, int m_i)
{
    int u_i_1;

    if (zeroes_i_1 != UNDEFINED) {
        write_egc(bs, zeroes_i_1);
    }

    if (m_i_1 != UNDEFINED) {
        /*calculate unary_{i - 1} for residual_{i - 1} based on m_{i}*/
        if ((m_i_1 > 0) && (m_i > 0)) {
            if ((u_i_2 == UNDEFINED) || ((u_i_2 % 2) == 0)) {
                u_i_1 = (m_i_1 * 2) + 1;
            } else {
                u_i_1 = (m_i_1 * 2) - 1;
            }
        } else if ((m_i_1 == 0) && (m_i > 0)) {
            if ((u_i_2 == UNDEFINED) || ((u_i_2 % 2) == 1)) {
                u_i_1 = 1;
            } else {
                u_i_1 = UNDEFINED;
            }
        } else if ((m_i_1 > 0) && (m_i == 0)) {
            if ((u_i_2 == UNDEFINED) || ((u_i_2 % 2) == 0)) {
                u_i_1 = m_i_1 * 2;
            } else {
                u_i_1 = (m_i_1 - 1) * 2;
            }
        } else if ((m_i_1 == 0) && (m_i == 0)) {
            if ((u_i_2 == UNDEFINED) || ((u_i_2 % 2) == 1)) {
                u_i_1 = 0;
            } else {
                u_i_1 = UNDEFINED;
            }
        } else {
            /*shouldn't get here*/
            assert(0);
            u_i_1 = UNDEFINED;
        }

        /*write residual_{i - 1} to disk using unary_{i - 1}*/
        if (u_i_1 != UNDEFINED) {
            if (u_i_1 < 16) {
                bs->write_unary(bs, 0, u_i_1);
            } else {
                bs->write_unary(bs, 0, 16);
                write_egc(bs, u_i_1 - 16);
            }
        }

        if (add_i_1 > 0) {
            unsigned p = LOG2(add_i_1);
            unsigned e = (1 << (p + 1)) - add_i_1 - 1;
            if (offset_i_1 < e) {
                unsigned r = offset_i_1;
                bs->write(bs, p, r);
            } else {
                unsigned r = (offset_i_1 + e) / 2;
                unsigned b = (offset_i_1 + e) % 2;
                bs->write(bs, p, r);
                bs->write(bs, 1, b);
            }
        }
        bs->write(bs, 1, sign_i_1);
    } else {
        u_i_1 = UNDEFINED;
    }

    return u_i_1;
}

static void
encode_residual(int residual, array_i* entropy,
                int* m, unsigned* offset, unsigned* add, unsigned* sign)
{
    unsigned _unsigned;
    int median0;
    int median1;
    int median2;

    assert(entropy->len == 3);

    if (residual >= 0) {
        _unsigned = residual;
        *sign = 0;
    } else {
        _unsigned = -residual - 1;
        *sign = 1;
    }

    median0 = (entropy->_[0] >> 4) + 1;
    median1 = (entropy->_[1] >> 4) + 1;
    median2 = (entropy->_[2] >> 4) + 1;

    if (_unsigned < median0) {
        *m = 0;
        *offset = _unsigned;
        *add = median0 - 1;
        entropy->_[0] -= ((entropy->_[0] + 126) >> 7) * 2;
    } else if ((_unsigned - median0) < median1) {
        *m = 1;
        *offset = _unsigned - median0;
        *add = median1 - 1;
        entropy->_[0] += ((entropy->_[0] + 128) >> 7) * 5;
        entropy->_[1] -= ((entropy->_[1] + 62) >> 6) * 2;
    } else if ((_unsigned - (median0 + median1)) < median2) {
        *m = 2;
        *offset = _unsigned - (median0 + median1);
        *add = median2 - 1;
        entropy->_[0] += ((entropy->_[0] + 128) >> 7) * 5;
        entropy->_[1] += ((entropy->_[1] + 64) >> 6) * 5;
        entropy->_[2] -= ((entropy->_[2] + 30) >> 5) * 2;
    } else {
        *m = ((_unsigned - (median0 + median1)) / median2) + 2;
        *offset = _unsigned - (median0 + median1 + ((*m - 2) * median2));
        *add = median2 - 1;
        entropy->_[0] += ((entropy->_[0] + 128) >> 7) * 5;
        entropy->_[1] += ((entropy->_[1] + 64) >> 6) * 5;
        entropy->_[2] += ((entropy->_[2] + 32) >> 5) * 5;
    }
}

static void
write_egc(BitstreamWriter* bs, unsigned v)
{
    if (v <= 1) {
        bs->write_unary(bs, 0, v);
    } else {
        unsigned t = LOG2(v) + 1;
        bs->write_unary(bs, 0, t);
        bs->write(bs, t - 1, v % (1 << (t - 1)));
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

static unsigned
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
        while ((x % 2) == 0) {
            x /= 2;
            total += 1;
        }
        return total;
    }
}

static unsigned
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

static uint32_t
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

static void
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
        a_append(side, (left->_[i] + right->_[i]) >> 1);
    }
}

static void
encode_footer_block(BitstreamWriter* bs,
                    struct wavpack_encoder_context* context,
                    const pcmreader* pcmreader)
{
    BitstreamWriter* sub_blocks = context->cache.sub_blocks;
    BitstreamWriter* sub_block = context->cache.sub_block;
    unsigned char md5sum[16];

    bw_reset_recorder(sub_blocks);

    /*add MD5 sub block*/
    audiotools__MD5Final(md5sum, &(context->md5sum));
    bw_reset_recorder(sub_block);
    sub_block->write_bytes(sub_block, md5sum, 16);
    write_sub_block(sub_blocks, WV_MD5, 1, sub_block);

    /*if present, add RIFF WAVE footer sub block*/
    if (context->wave.footer_data != NULL) {
        bw_reset_recorder(sub_block);
        sub_block->write_bytes(sub_block,
                               context->wave.footer_data,
                               context->wave.footer_len);
        write_sub_block(sub_blocks, WV_WAVE_FOOTER, 1, sub_block);
    }

    write_block_header(bs,
                       sub_blocks->bytes_written(sub_blocks),
                       0xFFFFFFFF,  /*block index*/
                       0,           /*block samples*/
                       pcmreader->bits_per_sample,
                       1,           /*channel count*/
                       0,           /*joint stereo*/
                       0,           /*correlation passes*/
                       0,           /*wasted bps*/
                       1,           /*first block*/
                       1,           /*last block*/
                       0,           /*maximum magnitude*/
                       pcmreader->sample_rate,
                       0,           /*false stereo*/
                       0xFFFFFFFF); /*CRC*/

    bw_rec_copy(bs, sub_blocks);
}

static void
wavpack_md5_update(void *data, unsigned char *buffer, unsigned long len)
{
    audiotools__MD5Update((audiotools__MD5Context*)data,
                          (const void*)buffer,
                          len);
}

static void
write_dummy_wave_header(BitstreamWriter* bs, const pcmreader* pcmreader,
                        unsigned wave_footer_len)
{
    char* fmt;
    if ((pcmreader->channels <= 2) &&
        (pcmreader->bits_per_sample <= 16)) {
        /*classic fmt chunk*/
        fmt = "16u 16u 32u 32u 16u 16u";
    } else {
        /*extended fmt chunk*/
        fmt = "16u 16u 32u 32u 16u 16u 16u 16u 32u 16b";
    }

    /*"RIFF", <size>, "WAVE", "fmt ", <size>*/
    bs->write(bs, bs_format_size("4b 32u 4b 4b 32u"), 0);

    bs->write(bs, bs_format_size(fmt), 0); /*<fmt data>*/

    bs->write(bs, bs_format_size("4b 32u"), 0); /*"data", size*/
}

static void
write_wave_header(BitstreamWriter* bs, const pcmreader* pcmreader,
                  uint32_t total_frames, unsigned wave_footer_len)
{
    const unsigned avg_bytes_per_second = (pcmreader->sample_rate *
                                           pcmreader->channels *
                                           (pcmreader->bits_per_sample / 8));
    const unsigned block_align = (pcmreader->channels *
                                  (pcmreader->bits_per_sample / 8));
    unsigned total_size = 4 * 3;  /*'RIFF' + size + 'WAVE'*/
    char* fmt;
    unsigned data_size;

    total_size += 4 * 2;          /*'fmt ' + size*/
    if ((pcmreader->channels <= 2) &&
        (pcmreader->bits_per_sample <= 16)) {
        /*classic fmt chunk*/
        fmt = "16u 16u 32u 32u 16u 16u";
    } else {
        /*extended fmt chunk*/
        fmt = "16u 16u 32u 32u 16u 16u 16u 16u 32u 16b";
    }
    total_size += bs_format_size(fmt) / 8;

    total_size += 4 * 2;         /*'data' + size*/
    data_size = (total_frames *
                 pcmreader->channels *
                 (pcmreader->bits_per_sample / 8));
    total_size += data_size;

    total_size += wave_footer_len;
    bs->build(bs, "4b 32u 4b 4b 32u",
              "RIFF", total_size - 8, "WAVE",
              "fmt ", bs_format_size(fmt) / 8);
    if ((pcmreader->channels <= 2) &&
        (pcmreader->bits_per_sample <= 16)) {
        bs->build(bs, fmt,
                  1,                                   /*compression code*/
                  pcmreader->channels,
                  pcmreader->sample_rate,
                  avg_bytes_per_second,
                  block_align,
                  pcmreader->bits_per_sample);
    } else {
        bs->build(bs, fmt,
                  0xFFFE,                              /*compression code*/
                  pcmreader->channels,
                  pcmreader->sample_rate,
                  avg_bytes_per_second,
                  block_align,
                  pcmreader->bits_per_sample,
                  22,                                  /*CB size*/
                  pcmreader->bits_per_sample,
                  pcmreader->channel_mask,
                  "\x01\x00\x00\x00\x00\x00\x10\x00"
                  "\x80\x00\x00\xaa\x00\x38\x9b\x71"); /*sub format*/
    }
    bs->build(bs, "4b 32u", "data", data_size);
}

#ifdef STANDALONE
int main(int argc, char *argv[]) {
    encoders_encode_wavpack(argv[1], stdin, 22050, 1, 1, 1, 16);
    return 0;
}

#endif
