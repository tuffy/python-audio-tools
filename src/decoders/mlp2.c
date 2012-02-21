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
    unsigned s;

    decoder->reader = br_open_buffer(frame_data, BS_BIG_ENDIAN);
    decoder->frame_reader = br_substream_new(BS_BIG_ENDIAN);
    decoder->substream_reader = br_substream_new(BS_BIG_ENDIAN);

    for (s = 0; s < MAX_MLP_SUBSTREAMS; s++) {
        unsigned c;

        /*init channel parameters*/
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            decoder->substream[s].parameters.channel[c].FIR.coeff =
                array_i_new();
            decoder->substream[s].parameters.channel[c].IIR.coeff =
                array_i_new();
            decoder->substream[s].parameters.channel[c].IIR.state =
                array_i_new();
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

    for (s = 0; s < MAX_MLP_SUBSTREAMS; s++) {
        unsigned c;

        /*free channel parameters*/
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            array_i_del(decoder->substream[s].parameters.channel[c].FIR.coeff);
            array_i_del(decoder->substream[s].parameters.channel[c].IIR.coeff);
            array_i_del(decoder->substream[s].parameters.channel[c].IIR.state);
        }
    }

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
        unsigned s;

        /*read 1 or 2 substream info blocks, depending on substream count*/
        /*FIXME - ensure at least one major sync has been read*/
        for (s = 0; s < decoder->major_sync.substream_count; s++) {
            if ((status =
                 read_mlp_substream_info(bs,
                                    &(decoder->substream[s].info))) != OK) {
                br_etry(bs);
                return status;
            }
        }

        /*decode 1 or 2 substreams to framelist, depending on substream count*/
        for (s = 0; s < decoder->major_sync.substream_count; s++) {
            br_substream_reset(decoder->substream_reader);
            if (decoder->substream[s].info.checkdata_present == 1){
                /*checkdata present, so last 2 bytes are CRC-8/parity*/
                unsigned CRC8;
                unsigned parity;

                if (s == 0) {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream[s].info.substream_end - 2);
                } else {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream[s].info.substream_end -
                         decoder->substream[s- 1].info.substream_end - 2);
                }

                if ((status = read_mlp_substream(decoder,
                                                 &(decoder->substream[s]),
                                                 decoder->substream_reader,
                                                 framelist)) != OK) {
                    br_etry(bs);
                    return status;
                }

                CRC8 = bs->read(bs, 8);
                parity = bs->read(bs, 8);

                /*FIXME - verify CRC8 and parity*/
            } else {
                if (s == 0) {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream[s].info.substream_end);
                } else {
                    bs->substream_append(bs, decoder->substream_reader,
                         decoder->substream[s].info.substream_end -
                         decoder->substream[s - 1].info.substream_end);
                }

                if ((status = read_mlp_substream(decoder,
                                                 &(decoder->substream[s]),
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
                   struct substream* substream,
                   BitstreamReader* bs,
                   array_ia* framelist)
{
    mlp_status status;

    if (bs->read(bs, 1)) {      /*decoding parmaters present*/
        unsigned restart_header;

        if ((restart_header = bs->read(bs, 1)) == 1) {
            /*restart header present*/
            if ((status =
                 read_mlp_restart_header(bs,
                                         &(substream->header))) != OK)
                return status;
        }

        if ((status = read_mlp_decoding_parameters(
                           bs,
                           restart_header,
                           substream->header.min_channel,
                           substream->header.max_channel,
                           substream->header.max_matrix_channel,
                           &(substream->parameters))) != OK)
            return status;
    }

    /*FIXME - perform substream decoding*/

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
    if (p->flags[0] && bs->read(bs, 1)) {
        bs->parse(bs, "1u 1u 1u 1u 1u 1u 1u 1u",
                  &(p->flags[0]), &(p->flags[1]), &(p->flags[2]),
                  &(p->flags[3]), &(p->flags[4]), &(p->flags[5]),
                  &(p->flags[6]), &(p->flags[7]));
    } else if (header_present) {
        p->flags[0] = p->flags[1] = p->flags[2] = p->flags[3] =
            p->flags[4] = p->flags[5] = p->flags[6] = p->flags[7] = 1;
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
        for (c = 0; c <= max_matrix_channel; c++)
            p->output_shift[c] = 0;
    }

    /*quant step sizes*/
    if (p->flags[4] && bs->read(bs, 1)) {
        for (c = min_channel; c <= max_channel; c++) {
            p->quant_step_size[c] = bs->read(bs, 4);
        }
    } else if (header_present) {
        for (c = min_channel; c <= max_channel; c++) {
            p->quant_step_size[c] = 0;
        }
    }

    /*channel parameters*/
    for (c = min_channel; c <= max_channel; c++) {
        if (bs->read(bs, 1)) {
            if (p->flags[3] && bs->read(bs, 1)) {
                /*read FIR filter parameters*/
                if ((status =
                     read_mlp_fir_params(bs,
                                         &(p->channel[c].FIR.shift),
                                         p->channel[c].FIR.coeff)) != OK)
                    return status;
            } else if (header_present) {
                /*default FIR filter parameters*/
                p->channel[c].FIR.shift = 0;
                array_i_reset(p->channel[c].FIR.coeff);
            }

            if (p->flags[2] && bs->read(bs, 1)) {
                /*read IIR filter parameters*/
                if ((status =
                     read_mlp_iir_params(bs,
                                         &(p->channel[c].IIR.shift),
                                         p->channel[c].IIR.coeff,
                                         p->channel[c].IIR.state)) != OK)
                    return status;
            } else if (header_present) {
                /*default IIR filter parameters*/
                p->channel[c].IIR.shift = 0;
                array_i_reset(p->channel[c].IIR.coeff);
                array_i_reset(p->channel[c].IIR.state);
            }

            if (p->flags[1] && bs->read(bs, 1)) {
                p->channel[c].huffman_offset = bs->read_signed(bs, 15);
            } else if (header_present) {
                p->channel[c].huffman_offset = 0;
            }

            p->channel[c].codebook = bs->read(bs, 2);

            if ((p->channel[c].huffman_lsbs = bs->read(bs, 5)) > 24)
                return INVALID_CHANNEL_PARAMETERS;

        } else if (header_present) {
            /*default channel parameters*/
            p->channel[c].FIR.shift = 0;
            array_i_reset(p->channel[c].FIR.coeff);
            p->channel[c].IIR.shift = 0;
            array_i_reset(p->channel[c].IIR.coeff);
            array_i_reset(p->channel[c].IIR.state);
            p->channel[c].huffman_offset = 0;
            p->channel[c].codebook = 0;
            p->channel[c].huffman_lsbs = 23;
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
read_mlp_fir_params(BitstreamReader* bs,
                    unsigned* shift,
                    array_i* coeffs)
{
    const unsigned order = bs->read(bs, 4);

    if (order > 8) {
        return INVALID_CHANNEL_PARAMETERS;
    } else if (order > 0) {
        unsigned coeff_bits;

        *shift = bs->read(bs, 4);
        coeff_bits = bs->read(bs, 5);

        if ((1 < coeff_bits) && (coeff_bits < 16)) {
            const unsigned coeff_shift = bs->read(bs, 3);
            unsigned f;

            if ((coeff_bits + coeff_shift) > 16)
                return INVALID_CHANNEL_PARAMETERS;
            coeffs->reset(coeffs);
            for (f = 0; f < order; f++) {
                const int v = bs->read_signed(bs, coeff_bits);
                coeffs->append(coeffs, v << coeff_shift);
            }
            if (bs->read(bs, 1))
                /*FIR params can't have state*/
                return INVALID_CHANNEL_PARAMETERS;
            else
                return OK;
        } else {
            return INVALID_CHANNEL_PARAMETERS;
        }
    } else {
        *shift = 0;
        coeffs->reset(coeffs);
        return OK;
    }
}

mlp_status
read_mlp_iir_params(BitstreamReader* bs,
                    unsigned* shift,
                    array_i* coeffs,
                    array_i* state)
{
    const unsigned order = bs->read(bs, 4);

    if (order > 8) {
        return INVALID_CHANNEL_PARAMETERS;
    } else if (order > 0) {
        unsigned coeff_bits;

        *shift = bs->read(bs, 4);
        coeff_bits = bs->read(bs, 5);

        if ((1 < coeff_bits) && (coeff_bits < 16)) {
            const unsigned coeff_shift = bs->read(bs, 3);
            unsigned i;

            if ((coeff_bits + coeff_shift) > 16)
                return INVALID_CHANNEL_PARAMETERS;
            coeffs->reset(coeffs);
            for (i = 0; i < order; i++) {
                const int v = bs->read_signed(bs, coeff_bits);
                coeffs->append(coeffs, v << coeff_shift);
            }
            state->reset(state);
            if (bs->read(bs, 1)) {
                const unsigned state_bits = bs->read(bs, 4);
                const unsigned state_shift = bs->read(bs, 4);

                for (i = 0; i < order; i++) {
                    const int v = bs->read_signed(bs, state_bits);
                    state->append(state, v << state_shift);
                }
                state->reverse(state);
            }
            return OK;
        } else {
            return INVALID_CHANNEL_PARAMETERS;
        }
    } else {
        *shift = 0;
        coeffs->reset(coeffs);
        state->reset(state);
        return OK;
    }
}
