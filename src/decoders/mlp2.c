#include "mlp2.h"

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

extern unsigned
dvda_bits_per_sample(unsigned encoded);

extern unsigned
dvda_sample_rate(unsigned encoded);

extern unsigned
dvda_channel_count(unsigned encoded);

extern unsigned
dvda_channel_mask(unsigned encoded);

MLPDecoder*
open_mlp_decoder(struct bs_buffer* frame_data)
{
    MLPDecoder* decoder = malloc(sizeof(MLPDecoder));
    decoder->reader = br_open_buffer(frame_data, BS_BIG_ENDIAN);
    decoder->frame_reader = br_substream_new(BS_BIG_ENDIAN);
    decoder->substream_reader = br_substream_new(BS_BIG_ENDIAN);
    return decoder;
}

void
close_mlp_decoder(MLPDecoder* decoder)
{
    decoder->reader->close(decoder->reader);
    decoder->frame_reader->close(decoder->frame_reader);
    decoder->substream_reader->close(decoder->substream_reader);
    free(decoder);
}

int
mlp_packet_empty(MLPDecoder* decoder)
{
    BitstreamReader* reader = decoder->reader;
    struct bs_buffer* packet = reader->input.substream;
    const unsigned remaining_bytes =
        packet->buffer_size - packet->buffer_position;

    if (remaining_bytes >= 4) {
        unsigned total_frame_size;

        reader->mark(reader);
        reader->parse(reader, "4p 12u 16p", &total_frame_size);
        reader->rewind(reader);
        reader->unmark(reader);

        return (remaining_bytes < (total_frame_size * 2));
    } else {
        /*not enough bytes for an MLP frame header*/
        return 1;
    }
}

mlp_status
read_mlp_frames(MLPDecoder* decoder,
                array_ia* framelist)
{
    BitstreamReader* reader = decoder->reader;
    struct bs_buffer* packet = reader->input.substream;

    while ((packet->buffer_size - packet->buffer_position) >= 4) {
        unsigned total_frame_size;
        unsigned frame_bytes;

        reader->mark(reader);
        reader->parse(reader, "4p 12u 16p", &total_frame_size);
        frame_bytes = (total_frame_size * 2) - 4;
        if ((packet->buffer_size - packet->buffer_position) >= frame_bytes) {
            BitstreamReader* frame_reader = decoder->frame_reader;
            mlp_status status;

            reader->unmark(reader);
            br_substream_reset(frame_reader);
            reader->substream_append(reader, frame_reader, frame_bytes);

            printf("decoding frame with %u bytes\n", frame_bytes);

            if ((status =
                 read_mlp_frame(decoder, frame_reader, framelist)) != OK)
                return status;
        } else {
            /*not enough of a frame left to read*/
            reader->rewind(reader);
            reader->unmark(reader);
            return OK;
        }
    }

  /*not enough of a frame left to read*/
    return OK;
}

mlp_status
read_mlp_frame(MLPDecoder* decoder,
               BitstreamReader* bs,
               array_ia* framelist)
{
    mlp_status status;

    /*check for major sync*/
    if ((status = read_mlp_major_sync(bs, &(decoder->major_sync))) != OK)
        return status;

    if (!setjmp(*br_try(bs))) {
        unsigned i;

        /*read 1 or 2 substream info blocks, depending on substream count*/
        /*FIXME - ensure at least one major sync has been read*/
        for (i = 0; i < decoder->major_sync.substream_count; i++) {
            if ((status =
                 read_mlp_substream_info(bs,
                                   &(decoder->substream_info[i]))) != OK) {
                br_etry(bs);
                return status;
            }

            printf("substream info %u %u %u %u\n",
                   decoder->substream_info[i].extraword_present,
                   decoder->substream_info[i].nonrestart_substream,
                   decoder->substream_info[i].checkdata_present,
                   decoder->substream_info[i].substream_end);
        }

        /*decode 1 or 2 substreams to framelist, depending on substream count*/
        for (i = 0; i < decoder->major_sync.substream_count; i++) {
            br_substream_reset(decoder->substream_reader);
            if (decoder->substream_info[i].checkdata_present == 1){
                /*checkdata present, so last 2 bytes are CRC-8/parity*/
                unsigned CRC8;
                unsigned parity;

                if (i == 0) {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream_info[i].substream_end - 2);
                } else {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream_info[i].substream_end -
                         decoder->substream_info[i - 1].substream_end - 2);
                }

                if ((status = read_mlp_substream(decoder,
                                                 decoder->substream_reader,
                                                 framelist)) != OK) {
                    br_etry(bs);
                    return status;
                }

                CRC8 = bs->read(bs, 8);
                parity = bs->read(bs, 8);

                /*FIXME - verify CRC8 and parity*/
            } else {
                if (i == 0) {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream_info[i].substream_end);
                } else {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream_info[i].substream_end -
                         decoder->substream_info[i - 1].substream_end);
                }

                if ((status = read_mlp_substream(decoder,
                                                 decoder->substream_reader,
                                                 framelist)) != OK) {
                    br_etry(bs);
                    return status;
                }
            }
        }

        br_etry(bs);
        return OK;
    } else {
        br_etry(bs);
        return IO_ERROR;
    }
}

mlp_status
read_mlp_major_sync(BitstreamReader* bs,
                    struct major_sync* major_sync)
{
    bs->mark(bs);
    if (!setjmp(*br_try(bs))) {
        unsigned sync_words = bs->read(bs, 24);
        unsigned stream_type = bs->read(bs, 8);

        if ((sync_words == 0xF8726F) && (stream_type == 0xBB)) {
            unsigned channel_assignment;

            /*major sync found*/
            bs->parse(bs,
                      "4u 4u 4u 4u 11p 5u 48p 1u 15u 4u 92p",
                      &(major_sync->bits_per_sample_0),
                      &(major_sync->bits_per_sample_1),
                      &(major_sync->sample_rate_0),
                      &(major_sync->sample_rate_1),
                      &channel_assignment,
                      &(major_sync->is_VBR),
                      &(major_sync->peak_bitrate),
                      &(major_sync->substream_count));

            if ((major_sync->substream_count != 1) &&
                (major_sync->substream_count != 2))
                return INVALID_MAJOR_SYNC;

            major_sync->channel_count = dvda_channel_count(channel_assignment);
            major_sync->channel_mask = dvda_channel_mask(channel_assignment);

            printf("major sync : %u %u %u %u %u %u %u\n",
                   major_sync->bits_per_sample_0,
                   major_sync->bits_per_sample_1,
                   major_sync->sample_rate_0,
                   major_sync->sample_rate_1,
                   channel_assignment,
                   major_sync->is_VBR,
                   major_sync->peak_bitrate);

            bs->unmark(bs);
            br_etry(bs);
            return OK;
        } else {
            bs->rewind(bs);
            bs->unmark(bs);
            br_etry(bs);
            return OK;
        }
    } else {
        bs->rewind(bs);
        bs->unmark(bs);
        br_etry(bs);
        return OK;
    }
}

mlp_status
read_mlp_substream_info(BitstreamReader* bs,
                        struct substream_info* substream_info)
{
    bs->parse(bs, "1u 1u 1u 1p 12u",
              &(substream_info->extraword_present),
              &(substream_info->nonrestart_substream),
              &(substream_info->checkdata_present),
              &(substream_info->substream_end));

    if (substream_info->extraword_present) {
        return INVALID_EXTRAWORD_PRESENT;
    }

    substream_info->substream_end *= 2;

    return OK;
}

mlp_status
read_mlp_substream(MLPDecoder* decoder,
                   BitstreamReader* bs,
                   array_ia* framelist)
{
    /*FIXME*/
    return OK;
}
