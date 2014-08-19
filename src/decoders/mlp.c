#include "mlp.h"

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

enum {FRAME_DATA};

MLPDecoder*
open_mlp_decoder(struct bs_buffer* frame_data)
{
    MLPDecoder* decoder = malloc(sizeof(MLPDecoder));
    unsigned c;
    unsigned s;

    decoder->reader = br_open_buffer(frame_data, BS_BIG_ENDIAN);
    decoder->frame_reader = br_substream_new(BS_BIG_ENDIAN);
    decoder->substream_reader = br_substream_new(BS_BIG_ENDIAN);
    decoder->major_sync_read = 0;

    decoder->framelist = aa_int_new();
    for (c = 0; c < MAX_MLP_CHANNELS; c++)
        decoder->framelist->append(decoder->framelist);

    for (s = 0; s < MAX_MLP_SUBSTREAMS; s++) {
        unsigned c;
        unsigned m;

        decoder->substream[s].residuals = aa_int_new();
        decoder->substream[s].filtered = a_int_new();

        /*init matrix parameters*/
        for (m = 0; m < MAX_MLP_MATRICES; m++) {
            decoder->substream[s].parameters.matrix[m].bypassed_LSB =
                a_int_new();
        }

        /*init channel parameters*/
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            decoder->substream[s].parameters.channel[c].FIR.coeff =
                a_int_new();
            decoder->substream[s].parameters.channel[c].FIR.state =
                a_int_new();
            decoder->substream[s].parameters.channel[c].IIR.coeff =
                a_int_new();
            decoder->substream[s].parameters.channel[c].IIR.state =
                a_int_new();
        }
    }

    return decoder;
}

void
close_mlp_decoder(MLPDecoder* decoder)
{
    unsigned s;

    decoder->reader->close(decoder->reader);
    decoder->frame_reader->close(decoder->frame_reader);
    decoder->substream_reader->close(decoder->substream_reader);
    aa_int_del(decoder->framelist);

    for (s = 0; s < MAX_MLP_SUBSTREAMS; s++) {
        unsigned c;
        unsigned m;

        aa_int_del(decoder->substream[s].residuals);
        a_int_del(decoder->substream[s].filtered);

        /*free matrix parameters*/
        for (m = 0; m < MAX_MLP_MATRICES; m++) {
            a_int_del(
                decoder->substream[s].parameters.matrix[m].bypassed_LSB);
        }

        /*free channel parameters*/
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            a_int_del(decoder->substream[s].parameters.channel[c].FIR.coeff);
            a_int_del(decoder->substream[s].parameters.channel[c].FIR.state);
            a_int_del(decoder->substream[s].parameters.channel[c].IIR.coeff);
            a_int_del(decoder->substream[s].parameters.channel[c].IIR.state);
        }
    }

    free(decoder);
}

int
mlp_packet_empty(MLPDecoder* decoder)
{
    BitstreamReader* reader = decoder->reader;
    struct bs_buffer* packet = reader->input.substream;
    const unsigned remaining_bytes = buf_window_size(packet);

    if (remaining_bytes >= 4) {
        unsigned total_frame_size;

        reader->mark(reader, FRAME_DATA);
        reader->parse(reader, "4p 12u 16p", &total_frame_size);
        reader->rewind(reader, FRAME_DATA);
        reader->unmark(reader, FRAME_DATA);

        return (remaining_bytes < (total_frame_size * 2));
    } else {
        /*not enough bytes for an MLP frame header*/
        return 1;
    }
}

mlp_status
read_mlp_frames(MLPDecoder* decoder,
                aa_int* framelist)
{
    BitstreamReader* reader = decoder->reader;
    struct bs_buffer* packet = reader->input.substream;

    while (buf_window_size(packet) >= 4) {
        unsigned total_frame_size;
        unsigned frame_bytes;

        reader->mark(reader, FRAME_DATA);
        reader->parse(reader, "4p 12u 16p", &total_frame_size);
        frame_bytes = (total_frame_size * 2) - 4;
        if (buf_window_size(packet) >= frame_bytes) {
            BitstreamReader* frame_reader = decoder->frame_reader;
            mlp_status status;

            reader->unmark(reader, FRAME_DATA);
            br_substream_reset(frame_reader);
            reader->substream_append(reader, frame_reader, frame_bytes);

            if ((status =
                 read_mlp_frame(decoder, frame_reader, framelist)) != OK)
                return status;
        } else {
            /*not enough of a frame left to read*/
            reader->rewind(reader, FRAME_DATA);
            reader->unmark(reader, FRAME_DATA);
            return OK;
        }
    }

    /*not enough of a frame left to read*/
    return OK;
}

mlp_status
read_mlp_frame(MLPDecoder* decoder,
               BitstreamReader* bs,
               aa_int* framelist)
{
    /*CHANNEL_MAP[a][c] where a is 5 bit channel assignment field
      and c is the MLP channel index
      yields the RIFF WAVE channel index*/
    const static int WAVE_CHANNEL[][6] = {
        /* 0x00 */ {  0, -1, -1, -1, -1, -1},
        /* 0x01 */ {  0,  1, -1, -1, -1, -1},
        /* 0x02 */ {  0,  1,  2, -1, -1, -1},
        /* 0x03 */ {  0,  1,  2,  3, -1, -1},
        /* 0x04 */ {  0,  1,  2, -1, -1, -1},
        /* 0x05 */ {  0,  1,  2,  3, -1, -1},
        /* 0x06 */ {  0,  1,  2,  3,  4, -1},
        /* 0x07 */ {  0,  1,  2, -1, -1, -1},
        /* 0x08 */ {  0,  1,  2,  3, -1, -1},
        /* 0x09 */ {  0,  1,  2,  3,  4, -1},
        /* 0x0A */ {  0,  1,  2,  3, -1, -1},
        /* 0x0B */ {  0,  1,  2,  3,  4, -1},
        /* 0x0C */ {  0,  1,  2,  3,  4,  5},
        /* 0x0D */ {  0,  1,  2,  3, -1, -1},
        /* 0x0E */ {  0,  1,  2,  3,  4, -1},
        /* 0x0F */ {  0,  1,  2,  3, -1, -1},
        /* 0x10 */ {  0,  1,  2,  3,  4, -1},
        /* 0x11 */ {  0,  1,  2,  3,  4,  5},
        /* 0x12 */ {  0,  1,  3,  4,  2, -1},
        /* 0x13 */ {  0,  1,  3,  4,  2, -1},
        /* 0x14 */ {  0,  1,  4,  5,  2,  3}
    };
    mlp_status status;

    /*check for major sync*/
    if (decoder->major_sync_read) {
        struct major_sync major_sync;

        switch (status = read_mlp_major_sync(bs, &major_sync)) {
        case OK:
            /*if major sync changes mid-stream, raise an exception*/
            if ((major_sync.bits_per_sample_0 !=
                 decoder->major_sync.bits_per_sample_0) ||
                (major_sync.bits_per_sample_1 !=
                 decoder->major_sync.bits_per_sample_1) ||
                (major_sync.sample_rate_0 !=
                 decoder->major_sync.sample_rate_0) ||
                (major_sync.sample_rate_1 !=
                 decoder->major_sync.sample_rate_1) ||
                (major_sync.channel_assignment !=
                 decoder->major_sync.channel_assignment) ||
                (major_sync.substream_count !=
                 decoder->major_sync.substream_count)) {
                return INVALID_MAJOR_SYNC;
            }
            break;
        case NO_MAJOR_SYNC:
            break;
        default:
            return status;
        }
    } else {
        switch (status = read_mlp_major_sync(bs, &(decoder->major_sync))) {
        case OK:
            decoder->major_sync_read = 1;
            break;
        case NO_MAJOR_SYNC:
            /*FIXME - ensure at least one major sync has been read*/
            break;
        default:
            return status;
        }
    }

    if (!setjmp(*br_try(bs))) {
        unsigned s;
        unsigned c;
        unsigned m;
        struct substream* substream0 = &(decoder->substream[0]);
        struct substream* substream1 = &(decoder->substream[1]);

        /*read 1 or 2 substream info blocks, depending on substream count*/

        for (s = 0; s < decoder->major_sync.substream_count; s++) {
            if ((status = read_mlp_substream_info(
                     bs,
                     &(decoder->substream[s].info))) != OK) {
                br_etry(bs);
                return status;
            }
        }

        br_substream_reset(decoder->substream_reader);
        if (decoder->substream[0].info.checkdata_present) {
            /*checkdata present, so last 2 bytes are CRC-8/parity*/
            struct checkdata checkdata = {0, 0x3C, 0};
            uint8_t parity;
            uint8_t CRC8;

            bs->add_callback(bs, mlp_checkdata_callback, &checkdata);
            bs->substream_append(bs, decoder->substream_reader,
                                 substream0->info.substream_end - 2);
            bs->pop_callback(bs, NULL);

            parity = (uint8_t)bs->read(bs, 8);
            if ((parity ^ checkdata.parity) != 0xA9) {
                br_etry(bs);
                return PARITY_MISMATCH;
            }

            CRC8 = (uint8_t)bs->read(bs, 8);
            if (checkdata.final_crc != CRC8) {
                br_etry(bs);
                return CRC8_MISMATCH;
            }
        } else {
            bs->substream_append(bs, decoder->substream_reader,
                                 decoder->substream[0].info.substream_end);
        }

        /*clear the bypassed LSB values in substream 0's matrix data*/
        for (m = 0; m < MAX_MLP_MATRICES; m++)
            a_int_reset(
               decoder->substream[0].parameters.matrix[m].bypassed_LSB);

        /*decode substream 0 bytes to channel data*/
        if ((status = read_mlp_substream(substream0,
                                         decoder->substream_reader,
                                         decoder->framelist)) != OK) {
            br_etry(bs);
            return status;
        }

        if (decoder->major_sync.substream_count == 1) {
            /*rematrix substream 0*/
            rematrix_mlp_channels(decoder->framelist,
                                  substream0->header.max_matrix_channel,
                                  substream0->header.noise_shift,
                                  &(substream0->header.noise_gen_seed),
                                  substream0->parameters.matrix_len,
                                  substream0->parameters.matrix,
                                  substream0->parameters.quant_step_size);

            /*apply output shifts to substream 0*/
            for (c = 0; c <= substream0->header.max_matrix_channel; c++) {
                const unsigned output_shift =
                    substream0->parameters.output_shift[c];
                if (output_shift) {
                    const unsigned block_size = decoder->framelist->_[c]->len;
                    unsigned i;
                    for (i = 0; i < block_size; i++) {
                        decoder->framelist->_[c]->_[i] <<= output_shift;
                    }
                }
            }

            /*append rematrixed data to final framelist in Wave order*/
            for (c = 0; c < framelist->len; c++) {
                a_int* out_channel = framelist->_[
                    WAVE_CHANNEL[decoder->major_sync.channel_assignment][c]];
                out_channel->extend(out_channel, decoder->framelist->_[c]);
            }

            /*clear out framelist for next run*/
            for (c = 0; c < decoder->framelist->len; c++) {
                decoder->framelist->_[c]->reset(decoder->framelist->_[c]);
            }
        } else {
            br_substream_reset(decoder->substream_reader);
            if (decoder->substream[0].info.checkdata_present) {
                /*checkdata present, so last 2 bytes are CRC-8/parity*/
                struct checkdata checkdata  = {0, 0x3C, 0};
                unsigned CRC8;
                unsigned parity;

                bs->add_callback(bs, mlp_checkdata_callback, &checkdata);
                bs->substream_append(bs, decoder->substream_reader,
                                     substream1->info.substream_end -
                                     substream0->info.substream_end -
                                     2);
                bs->pop_callback(bs, NULL);

                parity = (uint8_t)bs->read(bs, 8);
                if ((parity ^ checkdata.parity) != 0xA9) {
                    br_etry(bs);
                    return PARITY_MISMATCH;
                }

                CRC8 = (uint8_t)bs->read(bs, 8);
                if (checkdata.final_crc != CRC8) {
                    br_etry(bs);
                    return CRC8_MISMATCH;
                }
            } else {
                bs->substream_append(bs, decoder->substream_reader,
                                     substream1->info.substream_end -
                                     substream0->info.substream_end);
            }

            /*clear the bypassed LSB values in substream 1's matrix data*/
            for (m = 0; m < MAX_MLP_MATRICES; m++)
                a_int_reset(
                    decoder->substream[1].parameters.matrix[m].bypassed_LSB);

            /*decode substream 1 bytes to channel data*/
            if ((status = read_mlp_substream(substream1,
                                             decoder->substream_reader,
                                             decoder->framelist)) != OK) {
                br_etry(bs);
                return status;
            }

            /*rematrix substreams 0 and 1*/
            rematrix_mlp_channels(decoder->framelist,
                                  substream1->header.max_matrix_channel,
                                  substream1->header.noise_shift,
                                  &(substream1->header.noise_gen_seed),
                                  substream1->parameters.matrix_len,
                                  substream1->parameters.matrix,
                                  substream1->parameters.quant_step_size);

            /*apply output shifts to substreams 0 and 1*/
            for (c = 0; c <= substream1->header.max_matrix_channel; c++) {
                const unsigned output_shift =
                    substream1->parameters.output_shift[c];
                if (output_shift) {
                    const unsigned block_size = decoder->framelist->_[c]->len;
                    unsigned i;
                    for (i = 0; i < block_size; i++) {
                        decoder->framelist->_[c]->_[i] <<= output_shift;
                    }
                }
            }

            /*append rematrixed data to final framelist in Wave order*/
            for (c = 0; c < framelist->len; c++) {
                a_int* out_channel = framelist->_[
                    WAVE_CHANNEL[decoder->major_sync.channel_assignment][c]];
                out_channel->extend(out_channel, decoder->framelist->_[c]);
            }

            /*clear out framelist for next run*/
            for (c = 0; c < decoder->framelist->len; c++) {
                decoder->framelist->_[c]->reset(decoder->framelist->_[c]);
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
    bs->mark(bs, FRAME_DATA);
    if (!setjmp(*br_try(bs))) {
        const unsigned sync_words = bs->read(bs, 24);
        const unsigned stream_type = bs->read(bs, 8);

        if ((sync_words == 0xF8726F) && (stream_type == 0xBB)) {
            /*major sync found*/
            bs->parse(bs,
                      "4u 4u 4u 4u 11p 5u 48p 1u 15u 4u 92p",
                      &(major_sync->bits_per_sample_0),
                      &(major_sync->bits_per_sample_1),
                      &(major_sync->sample_rate_0),
                      &(major_sync->sample_rate_1),
                      &(major_sync->channel_assignment),
                      &(major_sync->is_VBR),
                      &(major_sync->peak_bitrate),
                      &(major_sync->substream_count));

            if ((major_sync->substream_count != 1) &&
                (major_sync->substream_count != 2))
                return INVALID_MAJOR_SYNC;

            bs->unmark(bs, FRAME_DATA);
            br_etry(bs);
            return OK;
        } else {
            bs->rewind(bs, FRAME_DATA);
            bs->unmark(bs, FRAME_DATA);
            br_etry(bs);
            return NO_MAJOR_SYNC;
        }
    } else {
        bs->rewind(bs, FRAME_DATA);
        bs->unmark(bs, FRAME_DATA);
        br_etry(bs);
        return NO_MAJOR_SYNC;
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
read_mlp_substream(struct substream* substream,
                   BitstreamReader* bs,
                   aa_int* framelist)
{
    if (!setjmp(*br_try(bs))) {
        unsigned last_block;

        do {
            mlp_status status;

            if ((status = read_mlp_block(substream,
                                         bs,
                                         framelist)) != OK) {
                br_etry(bs);
                return status;
            }

            last_block = bs->read(bs, 1);
        } while (last_block == 0);

        br_etry(bs);
        return OK;
    } else {
        br_etry(bs);
        return IO_ERROR;
    }
}

mlp_status
read_mlp_block(struct substream* substream,
               BitstreamReader* bs,
               aa_int* framelist)
{
    mlp_status status;
    unsigned c;

    /*decoding parameters present*/
    if (bs->read(bs, 1)) {
        unsigned restart_header;

        /*restart header present*/
        if ((restart_header = bs->read(bs, 1)) == 1) {
            if ((status =
                 read_mlp_restart_header(bs, &(substream->header))) != OK) {
                return status;
            }
        }

        if ((status =
             read_mlp_decoding_parameters(bs,
                                          restart_header,
                                          substream->header.min_channel,
                                          substream->header.max_channel,
                                          substream->header.max_matrix_channel,
                                          &(substream->parameters))) != OK) {
            return status;
        }
    }

    /*perform residuals decoding*/
    if ((status = read_mlp_residual_data(bs,
                                         substream->header.min_channel,
                                         substream->header.max_channel,
                                         substream->parameters.block_size,
                                         substream->parameters.matrix_len,
                                         substream->parameters.matrix,
                                         substream->parameters.quant_step_size,
                                         substream->parameters.channel,
                                         substream->residuals)) != OK) {
        return status;
    }


    /*filter residuals based on FIR/IIR parameters*/
    for (c = substream->header.min_channel;
         c <= substream->header.max_channel;
         c++) {
        if ((status =
             filter_mlp_channel(substream->residuals->_[c],
                                &(substream->parameters.channel[c].FIR),
                                &(substream->parameters.channel[c].IIR),
                                substream->parameters.quant_step_size[c],
                                substream->filtered)) != OK) {
            return status;
        }

        /*append filtered data to framelist*/
        framelist->_[c]->extend(framelist->_[c], substream->filtered);
    }

    return OK;
}

mlp_status
read_mlp_restart_header(BitstreamReader* bs,
                        struct restart_header* restart_header)
{
    unsigned header_sync;
    unsigned noise_type;
    unsigned output_timestamp;
    unsigned check_data_present;
    unsigned lossless_check;
    unsigned c;
    unsigned unknown1;
    unsigned unknown2;

    bs->parse(bs, "13u 1u 16u 4u 4u 4u 4u 23u 19u 1u 8u 16u",
              &header_sync, &noise_type, &output_timestamp,
              &(restart_header->min_channel),
              &(restart_header->max_channel),
              &(restart_header->max_matrix_channel),
              &(restart_header->noise_shift),
              &(restart_header->noise_gen_seed),
              &unknown1,
              &check_data_present,
              &lossless_check,
              &unknown2);

    if (header_sync != 0x18F5)
        return INVALID_RESTART_HEADER;
    if (noise_type != 0)
        return INVALID_RESTART_HEADER;
    if (restart_header->max_channel < restart_header->min_channel)
        return INVALID_RESTART_HEADER;
    if (restart_header->max_matrix_channel < restart_header->max_channel)
        return INVALID_RESTART_HEADER;

    for (c = 0; c <= restart_header->max_matrix_channel; c++) {
        if ((restart_header->channel_assignment[c] = bs->read(bs, 6)) >
            restart_header->max_matrix_channel) {
            return INVALID_RESTART_HEADER;
        }
    }

    restart_header->checksum = bs->read(bs, 8);

    return OK;
}

mlp_status
read_mlp_decoding_parameters(BitstreamReader* bs,
                             unsigned header_present,
                             unsigned min_channel,
                             unsigned max_channel,
                             unsigned max_matrix_channel,
                             struct decoding_parameters* p)
{
    mlp_status status;
    unsigned c;

    /*parameter presence flags*/
    if (header_present) {
        if (bs->read(bs, 1)) {
            bs->parse(bs, "1u 1u 1u 1u 1u 1u 1u 1u",
                      &(p->flags[0]), &(p->flags[1]), &(p->flags[2]),
                      &(p->flags[3]), &(p->flags[4]), &(p->flags[5]),
                      &(p->flags[6]), &(p->flags[7]));
        } else {
            p->flags[0] = p->flags[1] = p->flags[2] = p->flags[3] =
                p->flags[4] = p->flags[5] = p->flags[6] = p->flags[7] = 1;
        }
    } else if (p->flags[0] && bs->read(bs, 1)) {
        bs->parse(bs, "1u 1u 1u 1u 1u 1u 1u 1u",
                  &(p->flags[0]), &(p->flags[1]), &(p->flags[2]),
                  &(p->flags[3]), &(p->flags[4]), &(p->flags[5]),
                  &(p->flags[6]), &(p->flags[7]));
    }

    /*block size*/
    if (p->flags[7] && bs->read(bs, 1)) {
        if ((p->block_size = bs->read(bs, 9)) < 8)
            return INVALID_DECODING_PARAMETERS;
    } else if (header_present) {
        p->block_size = 8;
    }

    /*matrix parameters*/
    if (p->flags[6] && bs->read(bs, 1)) {
        if ((status = read_mlp_matrix_params(bs,
                                             max_matrix_channel,
                                             &(p->matrix_len),
                                             p->matrix)) != OK)
            return status;
    } else if (header_present) {
        p->matrix_len = 0;
    }

    /*output shifts*/
    if (p->flags[5] && bs->read(bs, 1)) {
        for (c = 0; c <= max_matrix_channel; c++)
            p->output_shift[c] = bs->read_signed(bs, 4);
    } else if (header_present) {
        for (c = 0; c < MAX_MLP_CHANNELS; c++)
            p->output_shift[c] = 0;
    }

    /*quant step sizes*/
    if (p->flags[4] && bs->read(bs, 1)) {
        for (c = 0; c <= max_channel; c++) {
            p->quant_step_size[c] = bs->read(bs, 4);
        }
    } else if (header_present) {
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            p->quant_step_size[c] = 0;
        }
    }

    /*channel parameters*/
    for (c = min_channel; c <= max_channel; c++) {
        if (bs->read(bs, 1)) {
            if (p->flags[3] && bs->read(bs, 1)) {
                /*read FIR filter parameters*/
                if ((status =
                     read_mlp_FIR_parameters(bs,
                                             &(p->channel[c].FIR))) != OK)
                    return status;
            } else if (header_present) {
                /*default FIR filter parameters*/
                p->channel[c].FIR.shift = 0;
                a_int_reset(p->channel[c].FIR.coeff);
            }

            if (p->flags[2] && bs->read(bs, 1)) {
                /*read IIR filter parameters*/
                if ((status =
                     read_mlp_IIR_parameters(bs,
                                             &(p->channel[c].IIR))) != OK)
                    return status;
            } else if (header_present) {
                /*default IIR filter parameters*/
                p->channel[c].IIR.shift = 0;
                a_int_reset(p->channel[c].IIR.coeff);
                a_int_reset(p->channel[c].IIR.state);
            }

            if (p->flags[1] && bs->read(bs, 1)) {
                p->channel[c].huffman_offset = bs->read_signed(bs, 15);
            } else if (header_present) {
                p->channel[c].huffman_offset = 0;
            }

            p->channel[c].codebook = bs->read(bs, 2);

            if ((p->channel[c].huffman_lsbs = bs->read(bs, 5)) > 24) {
                return INVALID_CHANNEL_PARAMETERS;
            }

        } else if (header_present) {
            /*default channel parameters*/
            p->channel[c].FIR.shift = 0;
            a_int_reset(p->channel[c].FIR.coeff);
            p->channel[c].IIR.shift = 0;
            a_int_reset(p->channel[c].IIR.coeff);
            a_int_reset(p->channel[c].IIR.state);
            p->channel[c].huffman_offset = 0;
            p->channel[c].codebook = 0;
            p->channel[c].huffman_lsbs = 24;
        }
    }

    return OK;
}

mlp_status
read_mlp_matrix_params(BitstreamReader* bs,
                       unsigned max_matrix_channel,
                       unsigned* matrix_len,
                       struct matrix_parameters* mp)
{
    unsigned m;

    *matrix_len = bs->read(bs, 4);
    for (m = 0; m < *matrix_len; m++) {
        unsigned c;
        unsigned fractional_bits;

        if ((mp[m].out_channel = bs->read(bs, 4)) > max_matrix_channel)
            return INVALID_MATRIX_PARAMETERS;
        if ((fractional_bits = bs->read(bs, 4)) > 14)
            return INVALID_MATRIX_PARAMETERS;
        mp[m].LSB_bypass = bs->read(bs, 1);
        for (c = 0; c < max_matrix_channel + 3; c++) {
            if (bs->read(bs, 1)) {
                const int v = bs->read_signed(bs, fractional_bits + 2);
                mp[m].coeff[c] = v << (14 - fractional_bits);
            } else {
                mp[m].coeff[c] = 0;
            }
        }
    }

    return OK;
}

mlp_status
read_mlp_FIR_parameters(BitstreamReader* bs,
                        struct filter_parameters* FIR)
{
    const unsigned order = bs->read(bs, 4);

    if (order > 8) {
        return INVALID_CHANNEL_PARAMETERS;
    } else if (order > 0) {
        unsigned coeff_bits;

        FIR->shift = bs->read(bs, 4);
        coeff_bits = bs->read(bs, 5);

        if ((1 <= coeff_bits) && (coeff_bits <= 16)) {
            const unsigned coeff_shift = bs->read(bs, 3);
            unsigned i;

            if ((coeff_bits + coeff_shift) > 16) {
                return INVALID_CHANNEL_PARAMETERS;
            }

            FIR->coeff->reset(FIR->coeff);
            for (i = 0; i < order; i++) {
                const int v = bs->read_signed(bs, coeff_bits);
                FIR->coeff->append(FIR->coeff, v << coeff_shift);
            }
            if (bs->read(bs, 1)) {
                return INVALID_CHANNEL_PARAMETERS;
            }


            return OK;
        } else {
            return INVALID_CHANNEL_PARAMETERS;
        }
    } else {
        FIR->shift = 0;
        FIR->coeff->reset(FIR->coeff);
        return OK;
    }
}

mlp_status
read_mlp_IIR_parameters(BitstreamReader* bs,
                        struct filter_parameters* IIR)
{
    const unsigned order = bs->read(bs, 4);

    if (order > 8) {
        return INVALID_CHANNEL_PARAMETERS;
    } else if (order > 0) {
        unsigned coeff_bits;

        IIR->shift = bs->read(bs, 4);
        coeff_bits = bs->read(bs, 5);

        if ((1 <= coeff_bits) && (coeff_bits <= 16)) {
            const unsigned coeff_shift = bs->read(bs, 3);
            unsigned i;

            if ((coeff_bits + coeff_shift) > 16) {
                return INVALID_CHANNEL_PARAMETERS;
            }

            IIR->coeff->reset(IIR->coeff);
            for (i = 0; i < order; i++) {
                const int v = bs->read_signed(bs, coeff_bits);
                IIR->coeff->append(IIR->coeff, v << coeff_shift);
            }
            IIR->state->reset(IIR->state);
            if (bs->read(bs, 1)) {
                const unsigned state_bits = bs->read(bs, 4);
                const unsigned state_shift = bs->read(bs, 4);

                for (i = 0; i < order; i++) {
                    const int v = bs->read_signed(bs, state_bits);
                    IIR->state->append(IIR->state, v << state_shift);
                }
                IIR->state->reverse(IIR->state);
            }

            return OK;
        } else {
            return INVALID_CHANNEL_PARAMETERS;
        }
    } else {
        IIR->shift = 0;
        IIR->coeff->reset(IIR->coeff);
        IIR->state->reset(IIR->state);
        return OK;
    }
}

mlp_status
read_mlp_residual_data(BitstreamReader* bs,
                       unsigned min_channel,
                       unsigned max_channel,
                       unsigned block_size,
                       unsigned matrix_len,
                       const struct matrix_parameters* matrix,
                       const unsigned* quant_step_size,
                       const struct channel_parameters* channel,
                       aa_int* residuals)
{
    int signed_huffman_offset[MAX_MLP_CHANNELS];
    unsigned LSB_bits[MAX_MLP_CHANNELS];
    static br_huffman_table_t mlp_codebook1[] =
#include "mlp_codebook1.h"
        ;
    static br_huffman_table_t mlp_codebook2[] =
#include "mlp_codebook2.h"
        ;
    static br_huffman_table_t mlp_codebook3[] =
#include "mlp_codebook3.h"
        ;

    unsigned c;
    unsigned m;
    unsigned i;

    /*calculate signed Huffman offset for each channel*/
    for (c = min_channel; c <= max_channel; c++) {
        LSB_bits[c] = channel[c].huffman_lsbs - quant_step_size[c];
        if (channel[c].codebook) {
            const int sign_shift = LSB_bits[c] + 2 - channel[c].codebook;
            if (sign_shift >= 0) {
                signed_huffman_offset[c] =
                    channel[c].huffman_offset -
                    (7 * (1 << LSB_bits[c])) -
                    (1 << sign_shift);
            } else {
                signed_huffman_offset[c] =
                    channel[c].huffman_offset -
                    (7 * (1 << LSB_bits[c]));
            }
        } else {
            const int sign_shift = LSB_bits[c] - 1;
            if (sign_shift >= 0) {
                signed_huffman_offset[c] =
                    channel[c].huffman_offset -
                    (1 << sign_shift);
            } else {
                signed_huffman_offset[c] = channel[c].huffman_offset;
            }
        }
    }

    /*reset residuals arrays*/
    residuals->reset(residuals);

    for (i = 0; i <= max_channel; i++) {
        /*residual channels 0 to "min_channel"
          will be initialized but not actually used*/
        a_int* channel = residuals->append(residuals);
        channel->resize(channel, block_size);
    }

    /*resize bypassed_LSB arrays for additional values*/
    for (m = 0; m < matrix_len; m++) {
        a_int* bypassed_LSB = matrix[m].bypassed_LSB;
        bypassed_LSB->resize(bypassed_LSB, bypassed_LSB->len + block_size);
    }

    for (i = 0; i < block_size; i++) {
        /*read bypassed LSBs for each matrix*/
        for (m = 0; m < matrix_len; m++) {
            a_int* bypassed_LSB = matrix[m].bypassed_LSB;
            if (matrix[m].LSB_bypass) {
                a_append(bypassed_LSB, bs->read(bs, 1));
            } else {
                a_append(bypassed_LSB, 0);
            }
        }

        /*read residuals for each channel*/
        for (c = min_channel; c <= max_channel; c++) {
            a_int* residual = residuals->_[c];
            register int MSB;
            register unsigned LSB;

            switch (channel[c].codebook) {
            case 0:
                MSB = 0;
                break;
            case 1:
                MSB = bs->read_huffman_code(bs, mlp_codebook1);
                break;
            case 2:
                MSB = bs->read_huffman_code(bs, mlp_codebook2);
                break;
            case 3:
                MSB = bs->read_huffman_code(bs, mlp_codebook3);
                break;
            default:
                MSB = -1;
                break;
            }
            if (MSB == -1)
                return INVALID_BLOCK_DATA;

            LSB = bs->read(bs, LSB_bits[c]);

            a_append(residual,
                     ((MSB << LSB_bits[c]) +
                      LSB +
                      signed_huffman_offset[c]) << quant_step_size[c]);
        }
    }

    return OK;
}

static inline int
mask(int x, unsigned q)
{
    if (q == 0)
        return x;
    else
        return (x >> q) << q;
}

mlp_status
filter_mlp_channel(const a_int* residuals,
                   struct filter_parameters* FIR,
                   struct filter_parameters* IIR,
                   unsigned quant_step_size,
                   a_int* filtered)
{
    const unsigned block_size = residuals->len;
    a_int* FIR_state = FIR->state;
    a_int* IIR_state = IIR->state;
    a_int* FIR_coeff = FIR->coeff;
    a_int* IIR_coeff = IIR->coeff;
    const int FIR_order = FIR->coeff->len;
    const int IIR_order = IIR->coeff->len;
    unsigned shift;
    int i;

    if ((FIR_order + IIR_order) > 8)
        return INVALID_FILTER_PARAMETERS;
    if ((FIR->shift > 0) && (IIR->shift > 0)) {
        if (FIR->shift != IIR->shift)
            return INVALID_FILTER_PARAMETERS;
        shift = FIR->shift;
    } else if (FIR_order > 0) {
        shift = FIR->shift;
    } else {
        shift = IIR->shift;
    }

    /*ensure arrays have enough space so we can use a_append*/
    FIR_state->resize(FIR_state, FIR_state->len + block_size);
    IIR_state->resize(IIR_state, IIR_state->len + block_size);
    filtered->reset(filtered);
    filtered->resize(filtered, block_size);

    for (i = 0; i < block_size; i++) {
        register int64_t sum = 0;
        int shifted_sum;
        int value;
        int j;
        int k;

        for (j = 0; j < FIR_order; j++)
            sum += (((int64_t)FIR_coeff->_[j] *
                     (int64_t)FIR_state->_[FIR_state->len - j  - 1]));

        for (k = 0; k < IIR_order; k++)
            sum += ((int64_t)IIR_coeff->_[k] *
                    (int64_t)IIR_state->_[IIR_state->len - k - 1]);

        shifted_sum = (int)(sum >> shift);

        value = mask(shifted_sum + residuals->_[i], quant_step_size);

        a_append(filtered, value);
        a_append(FIR_state, value);
        a_append(IIR_state, filtered->_[i] - shifted_sum);
    }

    FIR_state->tail(FIR_state, 8, FIR_state);
    IIR_state->tail(IIR_state, 8, IIR_state);

    return OK;
}

void
rematrix_mlp_channels(aa_int* channels,
                      unsigned max_matrix_channel,
                      unsigned noise_shift,
                      unsigned* noise_gen_seed,
                      unsigned matrix_count,
                      const struct matrix_parameters* matrix,
                      const unsigned* quant_step_size)
{
    const unsigned block_size = channels->_[0]->len;
    aa_int* noise = aa_int_new();
    unsigned i;
    unsigned m;

    /*generate noise channels*/
    for (i = 0; i < 2; i++) {
        a_int* channel = noise->append(noise);
        channel->resize(channel, block_size);
    }
    for (i = 0; i < block_size; i++) {
        const unsigned shifted = (*noise_gen_seed >> 7) & 0xFFFF;
        a_append(noise->_[0],
                 ((int8_t)(*noise_gen_seed >> 15)) << noise_shift);
        a_append(noise->_[1],
                 ((int8_t)(shifted)) << noise_shift);
        *noise_gen_seed = (((*noise_gen_seed << 16) & 0xFFFFFFFF) ^
                           shifted ^ (shifted << 5));
    }

    /*perform channel rematrixing*/
    for (m = 0; m < matrix_count; m++) {
        for (i = 0; i < block_size; i++) {
            register int64_t sum = 0;
            unsigned c;
            for (c = 0; c <= max_matrix_channel; c++)
                sum += ((int64_t)channels->_[c]->_[i] *
                        (int64_t)matrix[m].coeff[c]);
            sum += ((int64_t)noise->_[0]->_[i] *
                    (int64_t)matrix[m].coeff[max_matrix_channel + 1]);
            sum += ((int64_t)noise->_[1]->_[i] *
                    (int64_t)matrix[m].coeff[max_matrix_channel + 2]);

            channels->_[matrix[m].out_channel]->_[i] =
                mask((int)(sum >> 14),
                     quant_step_size[matrix[m].out_channel]) +
                matrix[m].bypassed_LSB->_[i];
        }
    }

    noise->del(noise);
}

void
mlp_checkdata_callback(uint8_t byte, void* checkdata)
{
    struct checkdata* cd = checkdata;
    const static uint8_t CRC8[] =
        {0x00, 0x63, 0xC6, 0xA5, 0xEF, 0x8C, 0x29, 0x4A,
         0xBD, 0xDE, 0x7B, 0x18, 0x52, 0x31, 0x94, 0xF7,
         0x19, 0x7A, 0xDF, 0xBC, 0xF6, 0x95, 0x30, 0x53,
         0xA4, 0xC7, 0x62, 0x01, 0x4B, 0x28, 0x8D, 0xEE,
         0x32, 0x51, 0xF4, 0x97, 0xDD, 0xBE, 0x1B, 0x78,
         0x8F, 0xEC, 0x49, 0x2A, 0x60, 0x03, 0xA6, 0xC5,
         0x2B, 0x48, 0xED, 0x8E, 0xC4, 0xA7, 0x02, 0x61,
         0x96, 0xF5, 0x50, 0x33, 0x79, 0x1A, 0xBF, 0xDC,
         0x64, 0x07, 0xA2, 0xC1, 0x8B, 0xE8, 0x4D, 0x2E,
         0xD9, 0xBA, 0x1F, 0x7C, 0x36, 0x55, 0xF0, 0x93,
         0x7D, 0x1E, 0xBB, 0xD8, 0x92, 0xF1, 0x54, 0x37,
         0xC0, 0xA3, 0x06, 0x65, 0x2F, 0x4C, 0xE9, 0x8A,
         0x56, 0x35, 0x90, 0xF3, 0xB9, 0xDA, 0x7F, 0x1C,
         0xEB, 0x88, 0x2D, 0x4E, 0x04, 0x67, 0xC2, 0xA1,
         0x4F, 0x2C, 0x89, 0xEA, 0xA0, 0xC3, 0x66, 0x05,
         0xF2, 0x91, 0x34, 0x57, 0x1D, 0x7E, 0xDB, 0xB8,
         0xC8, 0xAB, 0x0E, 0x6D, 0x27, 0x44, 0xE1, 0x82,
         0x75, 0x16, 0xB3, 0xD0, 0x9A, 0xF9, 0x5C, 0x3F,
         0xD1, 0xB2, 0x17, 0x74, 0x3E, 0x5D, 0xF8, 0x9B,
         0x6C, 0x0F, 0xAA, 0xC9, 0x83, 0xE0, 0x45, 0x26,
         0xFA, 0x99, 0x3C, 0x5F, 0x15, 0x76, 0xD3, 0xB0,
         0x47, 0x24, 0x81, 0xE2, 0xA8, 0xCB, 0x6E, 0x0D,
         0xE3, 0x80, 0x25, 0x46, 0x0C, 0x6F, 0xCA, 0xA9,
         0x5E, 0x3D, 0x98, 0xFB, 0xB1, 0xD2, 0x77, 0x14,
         0xAC, 0xCF, 0x6A, 0x09, 0x43, 0x20, 0x85, 0xE6,
         0x11, 0x72, 0xD7, 0xB4, 0xFE, 0x9D, 0x38, 0x5B,
         0xB5, 0xD6, 0x73, 0x10, 0x5A, 0x39, 0x9C, 0xFF,
         0x08, 0x6B, 0xCE, 0xAD, 0xE7, 0x84, 0x21, 0x42,
         0x9E, 0xFD, 0x58, 0x3B, 0x71, 0x12, 0xB7, 0xD4,
         0x23, 0x40, 0xE5, 0x86, 0xCC, 0xAF, 0x0A, 0x69,
         0x87, 0xE4, 0x41, 0x22, 0x68, 0x0B, 0xAE, 0xCD,
         0x3A, 0x59, 0xFC, 0x9F, 0xD5, 0xB6, 0x13, 0x70};

    cd->parity ^= byte;
    cd->crc = CRC8[(cd->final_crc = cd->crc ^ byte)];
}

#ifndef STANDALONE
PyObject*
mlp_python_exception(mlp_status mlp_status)
{
    switch (mlp_status) {
    case IO_ERROR:
        return PyExc_IOError;
    case OK:
    case NO_MAJOR_SYNC:
    case INVALID_MAJOR_SYNC:
    case INVALID_EXTRAWORD_PRESENT:
    case INVALID_RESTART_HEADER:
    case INVALID_DECODING_PARAMETERS:
    case INVALID_MATRIX_PARAMETERS:
    case INVALID_CHANNEL_PARAMETERS:
    case INVALID_BLOCK_DATA:
    case INVALID_FILTER_PARAMETERS:
    case PARITY_MISMATCH:
    case CRC8_MISMATCH:
    default:
        return PyExc_ValueError;
    }
}
#endif

const char*
mlp_python_exception_msg(mlp_status mlp_status)
{
    switch (mlp_status) {
    case OK:
    case NO_MAJOR_SYNC:
        return "no error";
    case IO_ERROR:
        return "I/O error reading MLP stream";
    case INVALID_MAJOR_SYNC:
        return "invalid MLP major sync";
    case INVALID_EXTRAWORD_PRESENT:
        return "invalid extraword present value in substream info";
    case INVALID_RESTART_HEADER:
        return "invalid MLP restart header";
    case INVALID_DECODING_PARAMETERS:
        return "invalid MLP decoding parameters";
    case INVALID_MATRIX_PARAMETERS:
        return "invalid MLP matrix parameters";
    case INVALID_CHANNEL_PARAMETERS:
        return "invalid MLP channel parameters";
    case INVALID_BLOCK_DATA:
        return "invalid MLP block data";
    case INVALID_FILTER_PARAMETERS:
        return "invalid MLP filter parameters";
    case PARITY_MISMATCH:
        return "parity mismatch decoding MLP substream";
    case CRC8_MISMATCH:
        return "CRC8 mismatch decoding MLP substream";
    default:
        return "unknown error";
    }
}
