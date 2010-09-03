#include "wavpack.h"
#include "../pcmreader.h"

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

PyObject*
encoders_encode_wavpack(PyObject *dummy,
                        PyObject *args, PyObject *keywds) {
    char *filename;
    FILE *file;
    Bitstream *stream;
    PyObject *pcmreader_obj;
    struct pcm_reader *reader;

    struct wavpack_encoder_context context;

    struct ia_array samples;
    ia_size_t i;

    int block_size;
    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "block_size",
                             NULL};
    if (!PyArg_ParseTupleAndKeywords(args,
                                     keywds,
                                     "sOi",
                                     kwlist,
                                     &filename,
                                     &pcmreader_obj,
                                     &block_size))
        return NULL;

    if (block_size <= 0) {
        PyErr_SetString(PyExc_ValueError, "block_size must be positive");
        return NULL;
    }

    /*open the given filename for writing*/
    if ((file = fopen(filename, "wb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    } else {
        stream = bs_open(file, BS_LITTLE_ENDIAN);
    }

    /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
    if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
        fclose(file);
        return NULL;
    }

    context.bits_per_sample = reader->bits_per_sample;
    context.sample_rate = reader->sample_rate;
    context.block_index = 0;
    ia_init(&(context.block_offsets), 1);

    iaa_init(&samples, reader->channels, block_size);

    /*build frames until reader is empty
      (WavPack doesn't have actual frames as such; it has sets of
       blocks joined by first-block/last-block bits in the header.
       However, I'll call that arrangement a "frame" for clarity.)*/
    if (!pcmr_read(reader, block_size, &samples))
        goto error;

    while (samples.arrays[0].size > 0) {
        wavpack_write_frame(stream, &context,
                            &samples, reader->channel_mask);

        if (!pcmr_read(reader, block_size, &samples))
            goto error;
    }

    /*go back and set block header data as necessary*/
    for (i = 0; i < context.block_offsets.size; i++) {
        fseek(file, context.block_offsets.data[i] + 12, SEEK_SET);
        stream->write_bits(stream, 32, context.block_index);
    }

    /*close open file handles and deallocate temporary space*/
    pcmr_close(reader);
    bs_close(stream);
    iaa_free(&samples);
    ia_free(&(context.block_offsets));

    Py_INCREF(Py_None);
    return Py_None;

 error:
    pcmr_close(reader);
    bs_close(stream);
    iaa_free(&samples);
    ia_free(&(context.block_offsets));

    return NULL;
}

static int
count_one_bits(int i) {
    int bits;

    for (bits = 0; i != 0; i >>= 1)
        bits += (i & 1);

    return bits;
}

static int
count_bits(int i) {
    int bits;

    for (bits = 0; i != 0; i >>= 1)
        bits++;

    return bits;
}

void
wavpack_channel_splits(struct i_array *counts,
                       int channel_count,
                       long channel_mask) {
    /*Although the WAVEFORMATEXTENSIBLE channel mask
      supports more left/right channels than these,
      everything beyond side-left/side-right
      is stored with a center channel in-between
      which means WavPack can't pull them apart in pairs.*/
    long masks[] = {0x3,   0x1,   0x2,        /*fLfR, fL, fR*/
                    0x4,   0x8,               /*fC, LFE*/
                    0x30,  0x10,  0x20,       /*bLbR, bL, bR*/
                    0xC0,  0x40,  0x80,       /*fLoCfRoC, fLoC, fRoC*/
                    0x100,                    /*bC*/
                    0x600, 0x200, 0x400,      /*sLsR, sL, sR*/
                    0};
    int channels;
    int i;

    /*first, try to pull left/right channels out of the mask*/
    for (i = 0; channel_mask && masks[i]; i++) {
        if (channel_mask & masks[i]) {
            channels = count_one_bits(masks[i]);
            ia_append(counts, channels);
            channel_count -= channels;
            channel_mask ^= masks[i];
        }
    }

    /*any leftover channels are sent out in separate blocks
      (which may happen with a mask of 0)*/
    for (; channel_count > 0; channel_count--) {
        ia_append(counts, 1);
    }
}

void
wavpack_write_frame(Bitstream *bs,
                    struct wavpack_encoder_context *context,
                    struct ia_array *samples,
                    long channel_mask) {
    struct i_array counts;
    int current_channel;
    int i;

    ia_init(&counts, 1);

    fprintf(stderr, "writing %d channels of %d samples\n",
            samples->size, samples->arrays[0].size);
    wavpack_channel_splits(&counts, samples->size, channel_mask);

    fprintf(stderr, "channel counts : ");
    ia_print(stderr, &counts);
    fprintf(stderr, "\n");

    for (i = current_channel = 0; i < counts.size; i++) {
        wavpack_write_block(bs,
                            context,
                            &(samples->arrays[current_channel]),
                            counts.data[i] == 2 ?
                            &(samples->arrays[current_channel + 1]) :
                            NULL,
                            counts.data[i],
                            i == 0,
                            i == (counts.size - 1));
        current_channel += counts.data[i];
    }

    context->block_index += samples->arrays[0].size;
    ia_free(&counts);
}

ia_data_t
wavpack_abs_maximum(ia_data_t sample, ia_data_t current_max) {
    return MAX(abs(sample), current_max);
}

static inline uint32_t
wavpack_crc(ia_data_t sample, uint32_t crc) {
    return ((3 * crc) + sample) & 0xFFFFFFFF;
}

void
wavpack_write_block(Bitstream *bs,
                    struct wavpack_encoder_context *context,
                    struct i_array *channel_A,
                    struct i_array *channel_B,
                    int channel_count,
                    int first_block,
                    int last_block) {
    struct wavpack_block_header block_header;
    struct i_array entropy_variables_A;
    struct i_array entropy_variables_B;
    Bitstream *sub_blocks = bs_open_recorder();
    ia_size_t i;

    ia_init(&entropy_variables_A, 3);
    ia_init(&entropy_variables_B, 3);

    /*this only works if Bitstream is a physical file*/
    ia_append(&(context->block_offsets), ftell(bs->file));

    /*initialize the WavPack block header fields*/

    block_header.version = 0x407;
    block_header.track_number = 0;
    block_header.index_number = 0;
    block_header.total_samples = 0; /*we won't know this in advance*/
    block_header.block_index = context->block_index;
    block_header.block_samples = channel_A->size;
    block_header.bits_per_sample = context->bits_per_sample;
    block_header.mono_output = channel_count == 1 ? 1 : 0;
    block_header.hybrid_mode = 0;

    block_header.hybrid_noise_shaping = 0;
    block_header.floating_point_data = 0;
    block_header.extended_size_integers = 0;
    block_header.hybrid_parameters_control_bitrate = 0;
    block_header.hybrid_noise_balanced = 0;
    block_header.initial_block_in_sequence = first_block;
    block_header.final_block_in_sequence = last_block;
    block_header.left_shift = 0;
    block_header.crc = 0xFFFFFFFF;

    if (channel_count == 1)
        block_header.maximum_data_magnitude = count_bits(
                        ia_reduce(channel_A, 0, wavpack_abs_maximum));
    else
        block_header.maximum_data_magnitude = MAX(
            count_bits(ia_reduce(channel_A, 0, wavpack_abs_maximum)),
            count_bits(ia_reduce(channel_B, 0, wavpack_abs_maximum)));

    block_header.sample_rate = context->sample_rate;
    block_header.use_IIR = 0;

    /*perform sub-block generation based on channel data
      and encoding options*/
    /*FIXME - add this*/
    fprintf(stderr, "writing block with channels = %d\n", channel_count);
    fprintf(stderr, "first block = %d\n", first_block);
    fprintf(stderr, "last block = %d\n", last_block);

    /*FIXME - some dummy placeholders for now*/
    ia_append(&entropy_variables_A, 0);
    ia_append(&entropy_variables_A, 0);
    ia_append(&entropy_variables_A, 0);
    ia_append(&entropy_variables_B, 0);
    ia_append(&entropy_variables_B, 0);
    ia_append(&entropy_variables_B, 0);

    /*FIXME - set these to 0 for now*/
    block_header.joint_stereo = 0;
    block_header.cross_channel_decorrelation = 0;
    block_header.false_stereo = 0;

    wavpack_write_entropy_variables(sub_blocks,
                                    &entropy_variables_A,
                                    &entropy_variables_B,
                                    channel_count);

    wavpack_write_residuals(sub_blocks,
                            channel_A,
                            channel_B,
                            &entropy_variables_A,
                            &entropy_variables_B,
                            channel_count);

    /*update block header fields*/
    block_header.block_size = 24 + (sub_blocks->bits_written / 8);
    if (channel_count == 1) {
        for (i = 0; i < channel_A->size; i++) {
            block_header.crc = wavpack_crc(channel_A->data[i],
                                           block_header.crc);
        }
    } else {
        for (i = 0; i < channel_A->size; i++) {
            block_header.crc = wavpack_crc(channel_B->data[i],
                                           wavpack_crc(channel_A->data[i],
                                                       block_header.crc));
        }
    }

    /*write block header*/
    wavpack_write_block_header(bs, &block_header);

    /*write sub-block data*/
    bs_dump_records(bs, sub_blocks);

    /*clear temporary space*/
    bs_close(sub_blocks);
    ia_free(&entropy_variables_A);
    ia_free(&entropy_variables_B);
}

void
wavpack_write_block_header(Bitstream *bs,
                           struct wavpack_block_header *header) {
    bs->write_bits(bs, 32, 0x6B707677); /*block header*/
    bs->write_bits(bs, 32, header->block_size);
    bs->write_bits(bs, 16, header->version);
    bs->write_bits(bs, 8,  header->track_number);
    bs->write_bits(bs, 8,  header->index_number);
    bs->write_bits(bs, 32, header->total_samples);
    bs->write_bits(bs, 32, header->block_index);
    bs->write_bits(bs, 32, header->block_samples);
    switch (header->bits_per_sample) {
    case 8:  bs->write_bits(bs, 2, 0); break;
    case 16: bs->write_bits(bs, 2, 1); break;
    case 24: bs->write_bits(bs, 2, 2); break;
    case 32: bs->write_bits(bs, 2, 3); break;
    }
    bs->write_bits(bs, 1,  header->mono_output);
    bs->write_bits(bs, 1,  header->hybrid_mode);
    bs->write_bits(bs, 1,  header->joint_stereo);
    bs->write_bits(bs, 1,  header->cross_channel_decorrelation);
    bs->write_bits(bs, 1,  header->hybrid_noise_shaping);
    bs->write_bits(bs, 1,  header->floating_point_data);
    bs->write_bits(bs, 1,  header->extended_size_integers);
    bs->write_bits(bs, 1,  header->hybrid_parameters_control_bitrate);
    bs->write_bits(bs, 1,  header->hybrid_noise_balanced);
    bs->write_bits(bs, 1,  header->initial_block_in_sequence);
    bs->write_bits(bs, 1,  header->final_block_in_sequence);
    bs->write_bits(bs, 5,  header->left_shift);
    bs->write_bits(bs, 5,  header->maximum_data_magnitude);
    switch (header->sample_rate) {
    case 6000:   bs->write_bits(bs, 4, 0x0); break;
    case 8000:   bs->write_bits(bs, 4, 0x1); break;
    case 9600:   bs->write_bits(bs, 4, 0x2); break;
    case 11025:  bs->write_bits(bs, 4, 0x3); break;
    case 12000:  bs->write_bits(bs, 4, 0x4); break;
    case 16000:  bs->write_bits(bs, 4, 0x5); break;
    case 22050:  bs->write_bits(bs, 4, 0x6); break;
    case 24000:  bs->write_bits(bs, 4, 0x7); break;
    case 32000:  bs->write_bits(bs, 4, 0x8); break;
    case 44100:  bs->write_bits(bs, 4, 0x9); break;
    case 48000:  bs->write_bits(bs, 4, 0xA); break;
    case 64000:  bs->write_bits(bs, 4, 0xB); break;
    case 88200:  bs->write_bits(bs, 4, 0xC); break;
    case 96000:  bs->write_bits(bs, 4, 0xD); break;
    case 192000: bs->write_bits(bs, 4, 0xE); break;
    default:     bs->write_bits(bs, 4, 0xF); break;
    }
    bs->write_bits(bs, 2,  0);
    bs->write_bits(bs, 1,  header->use_IIR);
    bs->write_bits(bs, 1,  header->false_stereo);
    bs->write_bits(bs, 1,  0);
    bs->write_bits(bs, 32, header->crc);
}

void
wavpack_write_subblock_header(Bitstream *bs,
                              wv_metadata_function metadata_function,
                              uint8_t nondecoder_data,
                              uint32_t block_size) {
    bs->write_bits(bs, 5, metadata_function);
    bs->write_bits(bs, 1, nondecoder_data);
    bs->write_bits(bs, 1, block_size % 2);

    /*convert block_size bytes to WavPack's 16-bit block size field*/
    block_size = (block_size / 2) + (block_size % 2);

    if (block_size > 0xFF) {
        bs->write_bits(bs, 1,  1);
        bs->write_bits(bs, 24, block_size);
    } else {
        bs->write_bits(bs, 1,  0);
        bs->write_bits(bs, 8,  block_size);
    }
}

int32_t wavpack_log2(int32_t sample) {
    int32_t asample = abs(sample) + (abs(sample) >> 9);
    int bitcount = count_bits(asample);
    static const uint8_t log2_table[] = {
        0x00, 0x01, 0x03, 0x04, 0x06, 0x07, 0x09, 0x0a,
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

    if ((0 <= asample) && (asample < 256) && (sample >= 0)) {
        return (bitcount << 8) + log2_table[(asample << (9 - bitcount)) % 256];
    } else if ((256 <= asample) && (sample >= 0)) {
        return (bitcount << 8) + log2_table[(asample >> (bitcount - 9)) % 256];
    } else if ((0 <= asample) && (asample < 256) && (sample < 0)) {
        return -((bitcount << 8) + log2_table[(asample << (9 - bitcount)) % 256]);
    } else if ((256 <= asample) && (sample < 0)) {
        return -((bitcount << 8) + log2_table[(asample >> (bitcount - 9)) % 256]);
    }

    return 0;  /*it shouldn't be possible to get here*/
}

void
wavpack_write_entropy_variables(Bitstream *bs,
                                struct i_array *variables_A,
                                struct i_array *variables_B,
                                int channel_count) {
    wavpack_write_subblock_header(bs, 5, 0, 6 * channel_count);
    bs->write_signed_bits(bs, 16, wavpack_log2(variables_A->data[0]));
    bs->write_signed_bits(bs, 16, wavpack_log2(variables_A->data[1]));
    bs->write_signed_bits(bs, 16, wavpack_log2(variables_A->data[2]));
    if (channel_count > 1) {
        bs->write_signed_bits(bs, 16, wavpack_log2(variables_B->data[0]));
        bs->write_signed_bits(bs, 16, wavpack_log2(variables_B->data[1]));
        bs->write_signed_bits(bs, 16, wavpack_log2(variables_B->data[2]));
    }
}

void
wavpack_write_residuals(Bitstream *bs,
                        struct i_array *channel_A,
                        struct i_array *channel_B,
                        struct i_array *variables_A,
                        struct i_array *variables_B,
                        int channel_count) {
    Bitstream *residual_data = bs_open_recorder();
    ia_size_t pcm_frame;
    ia_size_t channel;
    int zeroes = 0;
    int32_t residual;
    struct i_array *channels[] = {channel_A, channel_B};

    /*These are our temporary entropy variables copy
      since the encoder will modify them as it goes.*/
    struct i_array medians_A;
    struct i_array medians_B;
    struct i_array *medians[] = {&medians_A, &medians_B};

    struct wavpack_residual *residuals = malloc(
                        (sizeof(struct wavpack_residual) *
                         channel_A->size * channel_count) + 1);
    struct wavpack_residual *current_residual = residuals;

    ia_init(&medians_A, 3);
    ia_init(&medians_B, 3);
    ia_copy(&medians_A, variables_A);
    if (channel_count > 1)
        ia_copy(&medians_B, variables_B);
    else {
        ia_append(&medians_B, 0);
        ia_append(&medians_B, 0);
        ia_append(&medians_B, 0);
    }

    /*this bounces between interleaved channel data, as necessary*/
    for (pcm_frame = channel = 0;
         pcm_frame < channel_A->size;
         pcm_frame += (channel = (channel + 1) % channel_count) == 0 ? 1 : 0) {
        residual = channels[channel]->data[pcm_frame];
        if ((medians_A.data[0] < 2) && (medians_B.data[0] < 2)) {
            /*special case for handling large runs of 0 residuals*/

            if (zeroes == 0) {
                /*no currently running block of 0 residuals*/

                if (residual != 0) {
                    /*false alarm - no actual block of 0 residuals
                      so prepend with a 0 unary value*/
                    wavpack_calculate_zeroes(current_residual++, 0);
                    wavpack_clear_medians(&medians_A, &medians_B,
                                          channel_count);
                    wavpack_calculate_residual(current_residual++,
                                               medians[channel],
                                               residual);
                } else {
                    /*begin block of 0 residuals*/
                    zeroes = 1;
                }
            } else {
                /*a currently running block of 0 residuals*/

                if (residual == 0) {
                    /*continue the block of 0 residuals*/
                    zeroes++;
                } else {
                    /*flush block of 0 residuals*/
                    wavpack_calculate_zeroes(current_residual++, zeroes);
                    wavpack_clear_medians(&medians_A, &medians_B,
                                          channel_count);
                    zeroes = 0;
                    wavpack_calculate_residual(current_residual++,
                                               medians[channel],
                                               residual);
                }
            }
        } else {
            /*the typical residual writing case*/

            wavpack_calculate_residual(current_residual++,
                                       medians[channel],
                                       residual);
        }
    }

    /*write out any pending zero block*/
    if (zeroes > 0) {
        wavpack_calculate_zeroes(current_residual++, zeroes);
        wavpack_clear_medians(&medians_A, &medians_B, channel_count);
    }

    /*add the end-of-stream block*/
    current_residual->type = WV_RESIDUAL_FINISHED;

    /*make a second output pass over our residuals
      which calculates holding_one and holding_zero as necessary*/
    wavpack_output_residuals(residual_data, residuals);

    /*once all the residual data has been written,
      pad the output buffer to a multiple of 16 bits*/
    while ((residual_data->bits_written % 16) != 0)
        residual_data->write_bits(residual_data, 1, 1);

    /*write the sub-block header*/
    wavpack_write_subblock_header(bs, 0xA, 0, residual_data->bits_written / 8);

    /*write out the residual data*/
    bs_dump_records(bs, residual_data);

    /*clear any temporary space*/
    bs_close(residual_data);
    ia_free(&medians_A);
    ia_free(&medians_B);
    free(residuals);
}

/*The actual median values are stored as fractions of integers.
  This chops off the fractional portion and returns its
  integer value which has a minimum value of 1.*/
static inline int32_t
get_median(struct i_array *medians, int i) {
    return (medians->data[i] >> 4) + 1;
}

static inline void
inc_median(struct i_array *medians, int i) {
    medians->data[i] += (((medians->data[i] + (128 >> i)) /
                          (128 >> i)) * 5);
}

static inline void
dec_median(struct i_array *medians, int i) {
    medians->data[i] -= (((medians->data[i] + (128 >> i) - 2) /
                          (128 >> i)) * 2);
}

void
wavpack_calculate_residual(struct wavpack_residual *residual,
                           struct i_array *medians,
                           int32_t value) {
    uint8_t sign;
    uint32_t low;
    uint32_t high;
    uint32_t ones_count;
    uint32_t max_code;
    uint32_t code;
    uint32_t extras;
    uint32_t bit_count;

    if (value < 0) {
        sign = 1;
        value = -value - 1;
    } else {
        sign = 0;
    }

    /*First, figure out which medians our value falls between
      and get the "ones_count", "low" and "high" values.
      Note that "ones_count" is the unary-0 value preceeding
      each coded residual, per the documentation:

    | range                                             | prob. | coding    |
    |---------------------------------------------------+-------+-----------|
    |              0 <= residual < m(0)                 | 1/2   | 0(ab)S    |
    |           m(0) <= residual < m(0)+m(1)            | 1/4   | 10(ab)S   |
    |      m(0)+m(1) <= residual < m(0)+m(1)+m(2)       | 1/8   | 110(ab)S  |
    | m(0)+m(1)+m(2) <= residual < m(0)+m(1)+(2 * m(2)) | 1/16  | 1110(ab)S |
    |                      ...                          | ...   | ...       |

    "high" and "low" are the medians on each side of the residual.
    At the same time, increment or decrement medians as necessary.
    However, don't expect to send out the "ones_count" value as-is -
    one must adjust its value based on the *next* residual's unary value.
    If next is 0, multiply by 2.  If not, multiply by 2 and add 1.
    */
    if (value < get_median(medians, 0)) {
        /*value below the 1st median*/

        ones_count = 0;
        low = 0;
        high = get_median(medians, 0) - 1;
        dec_median(medians, 0);
    } else if ((value - get_median(medians, 0)) < get_median(medians, 1)) {
        /*value between the 1st and 2nd medians*/

        ones_count = 1;
        low = get_median(medians, 0);
        high = low + get_median(medians, 1) - 1;
        inc_median(medians, 0);
        dec_median(medians, 1);
    } else if ((value - (get_median(medians, 0) +
                         get_median(medians, 1))) < get_median(medians, 2)) {
        /*value between the 2nd and 3rd medians*/

        ones_count = 2;
        low = get_median(medians, 0) + get_median(medians, 1);
        high = low + get_median(medians, 2) - 1;
        inc_median(medians, 0);
        inc_median(medians, 1);
        dec_median(medians, 2);
    } else {
        /*value above the 3rd median*/
        ones_count = 2 + ((value - (get_median(medians, 0) +
                                    get_median(medians, 1))) /
                          get_median(medians, 2));
        low = (get_median(medians, 0) +
               get_median(medians, 1)) + ((ones_count - 2) *
                                          get_median(medians, 2));
        high = low + get_median(medians, 2) - 1;
        inc_median(medians, 0);
        inc_median(medians, 1);
        inc_median(medians, 2);
    }

    residual->type = WV_RESIDUAL_GOLOMB;
    residual->residual.golomb.unary = ones_count;
    residual->residual.golomb.sign = sign;

    /*then calculate our fixed value and its size*/
    if (high != low) {
        max_code = high - low;
        code = value - low;
        bit_count = count_bits(max_code);
        extras = (1 << bit_count) - max_code - 1;

        if (code < extras) {
            residual->residual.golomb.fixed = code;
            residual->residual.golomb.fixed_size = bit_count - 1;
            residual->residual.golomb.has_extra_bit = 0;
        } else {
            residual->residual.golomb.fixed = (code + extras) >> 1;
            residual->residual.golomb.fixed_size = bit_count - 1;
            residual->residual.golomb.has_extra_bit = 1;
            residual->residual.golomb.extra_bit = (code + extras) & 1;
        }
    } else {
        residual->residual.golomb.fixed = 0;
        residual->residual.golomb.fixed_size = 0;
        residual->residual.golomb.has_extra_bit = 0;
    }
}

void
wavpack_calculate_zeroes(struct wavpack_residual *residual,
                         uint32_t zeroes) {
    residual->type = WV_RESIDUAL_ZEROES;
    residual->residual.zeroes_count = zeroes;
}

void
wavpack_output_residuals(Bitstream *bs, struct wavpack_residual *residual) {
    struct wavpack_residual *previous_residual = NULL;
    int holding_zero = 0;
    int holding_one = 0;

    for(; residual->type != WV_RESIDUAL_FINISHED; residual++) {
        if (previous_residual == NULL) {
            previous_residual = residual;
            continue;
        }

        /*Output the previous residual based
          on the contents of the current residual.*/

        switch (previous_residual->type) {
        case WV_RESIDUAL_ZEROES:
            /*If the previous is a block of zeroes,
              output them as-is and continue on
              without adjusting the holding_one/zero bits.*/
            wavpack_output_residual(bs, previous_residual, 0);
            break;
        case WV_RESIDUAL_GOLOMB:
            /*Update the previous residual's unary value
              based on the current residual's unary value
              and our desired "holding_one" and "holding_zero" values.*/

            if (residual->residual.golomb.unary == 0) {
                /*If the current unary value is 0,
                  adjust the previous unary value such that
                  holding_one becomes 0.*/

                if (holding_zero) {
                    /*If holding_zero is already set,
                      output previous as a non-unary code and reset.*/
                    holding_zero = 0;
                    holding_one = 0;
                    wavpack_output_residual(bs, previous_residual, 0);
                } else {
                    /*Otherwise, adjust previous to set
                      holding_one to 0 and holding_zero to 1.*/
                    wavpack_set_holding(previous_residual,
                                        holding_one, 0);
                    holding_zero = 1;
                    holding_one = 0;
                    wavpack_output_residual(bs, previous_residual, 1);
                }
            } else {
                /*Otherwise, adjust the previous unary value
                  such that holding_one remains 1.
                  We can go from holding_one -> holding_one so
                  long as the unary value is above 0.*/
                if (holding_zero) {
                    holding_zero = 0;
                    holding_one = 0;
                    wavpack_output_residual(bs, previous_residual, 0);
                } else {
                    wavpack_set_holding(previous_residual,
                                        holding_one, 1);
                    holding_one = 1;
                    holding_zero = 0;
                    wavpack_output_residual(bs, previous_residual, 1);
                }
            }
            break;
        default:
            break;
        }

        previous_residual = residual;
    }

    /*And, don't forget to output the final residual.*/
    if (holding_zero) {
        wavpack_output_residual(bs, previous_residual, 0);
    } else {
        wavpack_output_residual(bs, previous_residual, 1);
    }
}

void
wavpack_clear_medians(struct i_array *medians_A,
                      struct i_array *medians_B,
                      int channel_count) {
    medians_A->data[0] = 0;
    medians_A->data[1] = 0;
    medians_A->data[2] = 0;
    if (channel_count > 1) {
        medians_B->data[0] = 0;
        medians_B->data[1] = 0;
        medians_B->data[2] = 0;
    }
}

struct wavpack_residual*
wavpack_previous_golomb(struct wavpack_residual *residual,
                        struct wavpack_residual *first_residual) {
    if (residual == first_residual)
        return NULL;
    else {
        for (residual--; residual != first_residual; residual--) {
            if (residual->type == WV_RESIDUAL_GOLOMB)
                return residual;
        }

        return NULL;
    }
}

struct wavpack_residual*
wavpack_next_golomb(struct wavpack_residual *residual) {
    if (residual->type == WV_RESIDUAL_FINISHED)
        return NULL;
    else {
        for (residual++; residual->type != WV_RESIDUAL_FINISHED; residual++) {
            if (residual->type == WV_RESIDUAL_GOLOMB)
                return residual;
        }

        return NULL;
    }
}

void
wavpack_set_holding(struct wavpack_residual *residual,
                    int current_holding_one,
                    int new_holding_one) {
    if (new_holding_one) {
        if (current_holding_one) {
            residual->residual.golomb.unary =
                ((residual->residual.golomb.unary - 1) * 2) + 1;
        } else {
            residual->residual.golomb.unary =
                (residual->residual.golomb.unary * 2) + 1;
        }
    } else {
        if (current_holding_one) {
            residual->residual.golomb.unary =
                (residual->residual.golomb.unary - 1) * 2;
        } else {
            residual->residual.golomb.unary *= 2;
        }
    }
}

void
wavpack_output_residual(Bitstream *bs,
                        struct wavpack_residual *residual,
                        int write_unary) {
    int32_t escape_code;
    int escape_size;

    switch (residual->type) {
    case WV_RESIDUAL_GOLOMB:
        if (write_unary) {
            if (residual->residual.golomb.unary >= WV_UNARY_LIMIT) {
                /*generate escape code*/
                bs->write_unary(bs, 0, 16);

                /*build an Elias gamma code from the unary value (- 16) */
                escape_code = residual->residual.golomb.unary - 16;
                if (escape_code < 2) {
                    bs->write_unary(bs, 0, escape_code);
                } else {
                    escape_size = count_bits(escape_code) - 1;
                    bs->write_unary(bs, 0, escape_size + 1);
                    bs->write_bits(bs, escape_size,
                                   escape_code % (1 << escape_size));
                }
            } else {
                bs->write_unary(bs, 0, residual->residual.golomb.unary);
            }
        }
        bs->write_bits(bs,
                       residual->residual.golomb.fixed_size,
                       residual->residual.golomb.fixed);
        if (residual->residual.golomb.has_extra_bit)
            bs->write_bits(bs, 1,
                           residual->residual.golomb.extra_bit);
        bs->write_bits(bs, 1, residual->residual.golomb.sign);
        break;
    case WV_RESIDUAL_ZEROES:
        if (residual->residual.zeroes_count == 0) {
            bs->write_bits(bs, 1, 0);
        } else {
            escape_size = count_bits(residual->residual.zeroes_count) - 1;
            bs->write_unary(bs, 0, escape_size + 1);
            bs->write_bits(bs, escape_size,
                        residual->residual.zeroes_count % (1 << escape_size));
        }
        break;
    default:
        break;
    }
}

void
wavpack_print_residual(FILE *output,
                       struct wavpack_residual *residual,
                       int write_unary) {
    switch (residual->type) {
    case WV_RESIDUAL_ZEROES:
        fprintf(output, "zeroes count %u\n",
                residual->residual.zeroes_count);
        break;
    case WV_RESIDUAL_GOLOMB:
        if (write_unary) {
            fprintf(output, "unary %u , ", residual->residual.golomb.unary);
        }

        fprintf(output, "value %u , size %u , ",
                residual->residual.golomb.fixed,
                residual->residual.golomb.fixed_size);

        if (residual->residual.golomb.has_extra_bit) {
            fprintf(output, "extra %u , ",
                    residual->residual.golomb.extra_bit);
        }

        fprintf(output, "sign %u\n",
                residual->residual.golomb.sign);

        break;
    default:
        fprintf(output, "unknown residual\n");
        break;
    }
}
