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
        WavPackEncoder_write_frame(stream, &context,
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
WavPackEncoder_channel_splits(struct i_array *counts,
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
WavPackEncoder_write_frame(Bitstream *bs,
                           struct wavpack_encoder_context *context,
                           struct ia_array *samples,
                           long channel_mask) {
    struct i_array counts;
    int current_channel;
    int i;

    ia_init(&counts, 1);

    fprintf(stderr, "writing %d channels of %d samples\n",
            samples->size, samples->arrays[0].size);
    WavPackEncoder_channel_splits(&counts, samples->size, channel_mask);

    fprintf(stderr, "channel counts : ");
    ia_print(stderr, &counts);
    fprintf(stderr, "\n");

    for (i = current_channel = 0; i < counts.size; i++) {
        WavPackEncoder_write_block(bs,
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
WavPackEncoder_abs_maximum(ia_data_t sample, ia_data_t current_max) {
    return MAX(abs(sample), current_max);
}

void
WavPackEncoder_write_block(Bitstream *bs,
                           struct wavpack_encoder_context *context,
                           struct i_array *channel_A,
                           struct i_array *channel_B,
                           int channel_count,
                           int first_block,
                           int last_block) {
    struct wavpack_block_header block_header;
    Bitstream *sub_blocks = bs_open_recorder();

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

    if (channel_count == 1)
        block_header.maximum_data_magnitude = count_bits(
                        ia_reduce(channel_A, 0, WavPackEncoder_abs_maximum));
    else
        block_header.maximum_data_magnitude = MAX(
            count_bits(ia_reduce(channel_A, 0, WavPackEncoder_abs_maximum)),
            count_bits(ia_reduce(channel_B, 0, WavPackEncoder_abs_maximum)));

    block_header.sample_rate = context->sample_rate;
    block_header.use_IIR = 0;

    /*perform sub-block generation based on channel data
      and encoding options*/
    /*FIXME - add this*/
    fprintf(stderr, "writing block with channels = %d\n", channel_count);
    fprintf(stderr, "first block = %d\n", first_block);
    fprintf(stderr, "last block = %d\n", last_block);

    /*FIXME - set these to 0 for now*/
    block_header.joint_stereo = 0;
    block_header.cross_channel_decorrelation = 0;
    block_header.false_stereo = 0;

    /*update block header fields*/
    block_header.block_size = sub_blocks->bits_written / 16;
    block_header.crc = 0; /*FIXME - figure out how to calculate this*/

    /*write block header*/
    WavPackEncoder_write_block_header(bs, &block_header);

    /*write sub-block data*/
    bs_dump_records(bs, sub_blocks);

    /*clear temporary space*/
    bs_close(sub_blocks);
}

void
WavPackEncoder_write_block_header(Bitstream *bs,
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
WavPackEncoder_write_subblock_header(Bitstream *bs,
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
