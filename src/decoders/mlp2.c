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

        decoder->substream[s].bypassed_LSBs = array_ia_new();
        decoder->substream[s].residuals = array_ia_new();
        decoder->substream[s].filtered = array_ia_new();

        /*init channel parameters*/
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            decoder->substream[s].parameters.channel[c].FIR.coeff =
                array_i_new();
            decoder->substream[s].parameters.channel[c].FIR.state =
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

        array_ia_del(decoder->substream[s].bypassed_LSBs);
        array_ia_del(decoder->substream[s].residuals);
        array_ia_del(decoder->substream[s].filtered);

        /*free channel parameters*/
        for (c = 0; c < MAX_MLP_CHANNELS; c++) {
            array_i_del(decoder->substream[s].parameters.channel[c].FIR.coeff);
            array_i_del(decoder->substream[s].parameters.channel[c].FIR.state);
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
                         decoder->substream[s - 1].info.substream_end - 2);
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
    if (!setjmp(*br_try(bs))) {
        unsigned last_block;

        do {
            mlp_status status;

            if ((status = read_mlp_block(decoder,
                                         substream,
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
read_mlp_block(MLPDecoder* decoder,
               struct substream* substream,
               BitstreamReader* bs,
               array_ia* framelist)
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
    if ((status = read_mlp_block_data(bs,
                                      substream->parameters.block_size,
                                      substream->header.min_channel,
                                      substream->header.max_channel,
                                      substream->parameters.matrix_len,
                                      substream->parameters.quant_step_size,
                                      substream->parameters.matrix,
                                      substream->parameters.channel,
                                      substream->bypassed_LSBs,
                                      substream->residuals)) != OK) {
        return status;
    }


    /*filter residuals based on FIR/IIR parameters*/
    substream->filtered->reset(substream->filtered);
    for (c = 0; c < substream->header.min_channel; c++) {
        /*initalize unused filter channels, if any*/
        substream->filtered->append(substream->filtered);
    }

    for (c = substream->header.min_channel;
         c <= substream->header.max_channel;
         c++) {
        array_i* filtered = substream->filtered->append(substream->filtered);
        if ((status =
             filter_mlp_channel(substream->residuals->_[c],
                                &(substream->parameters.channel[c].FIR),
                                &(substream->parameters.channel[c].IIR),
                                substream->parameters.quant_step_size[c],
                                filtered)) != OK) {
            return status;
        }
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
                     read_mlp_filter_parameters(bs,
                                                &(p->channel[c].FIR))) != OK)
                    return status;
                if (p->channel[c].FIR.state->len > 0)
                    /*FIR filters cannot have initial state*/
                    return INVALID_CHANNEL_PARAMETERS;
            } else if (header_present) {
                /*default FIR filter parameters*/
                p->channel[c].FIR.shift = 0;
                array_i_reset(p->channel[c].FIR.coeff);
                array_i_reset(p->channel[c].FIR.state);
            }

            if (p->flags[2] && bs->read(bs, 1)) {
                /*read IIR filter parameters*/
                if ((status =
                     read_mlp_filter_parameters(bs,
                                                &(p->channel[c].IIR))) != OK)
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
            array_i_reset(p->channel[c].FIR.state);
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
read_mlp_filter_parameters(BitstreamReader* bs,
                           struct filter_parameters* params)
{
    const unsigned order = bs->read(bs, 4);

    if (order > 8) {
        return INVALID_CHANNEL_PARAMETERS;
    } else if (order > 0) {
        unsigned coeff_bits;

        params->shift = bs->read(bs, 4);
        coeff_bits = bs->read(bs, 5);

        if ((1 < coeff_bits) && (coeff_bits < 16)) {
            const unsigned coeff_shift = bs->read(bs, 3);
            unsigned i;

            if ((coeff_bits + coeff_shift) > 16)
                return INVALID_CHANNEL_PARAMETERS;
            params->coeff->reset(params->coeff);
            for (i = 0; i < order; i++) {
                const int v = bs->read_signed(bs, coeff_bits);
                params->coeff->append(params->coeff, v << coeff_shift);
            }
            params->state->reset(params->state);
            if (bs->read(bs, 1)) {
                const unsigned state_bits = bs->read(bs, 4);
                const unsigned state_shift = bs->read(bs, 4);

                for (i = 0; i < order; i++) {
                    const int v = bs->read_signed(bs, state_bits);
                    params->state->append(params->state, v << state_shift);
                }
                params->state->reverse(params->state);
            }

            return OK;
        } else {
            return INVALID_CHANNEL_PARAMETERS;
        }
    } else {
        params->shift = 0;
        params->coeff->reset(params->coeff);
        params->state->reset(params->state);
        return OK;
    }
}

mlp_status
read_mlp_block_data(BitstreamReader* bs,
                    unsigned block_size,
                    unsigned min_channel,
                    unsigned max_channel,
                    unsigned matrix_len,
                    const unsigned* quant_step_size,
                    const struct matrix_parameters* matrix,
                    const struct channel_parameters* channel,
                    array_ia* bypassed_LSBs,
                    array_ia* residuals)
{
    int signed_huffman_offset[MAX_MLP_CHANNELS];
    unsigned LSB_bits[MAX_MLP_CHANNELS];
    static struct br_huffman_table mlp_codebook1[][0x200] =
#include "mlp_codebook1.h"
        ;
    static struct br_huffman_table mlp_codebook2[][0x200] =
#include "mlp_codebook2.h"
        ;
    static struct br_huffman_table mlp_codebook3[][0x200] =
#include "mlp_codebook3.h"
        ;

    unsigned c;
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

    /*reset bypassed_LSB and residuals arrays*/
    bypassed_LSBs->reset(bypassed_LSBs);
    for (i = 0; i < matrix_len; i++)
        bypassed_LSBs->append(bypassed_LSBs);
    residuals->reset(residuals);
    for (i = 0; i <= max_channel; i++)
        /*residual channels 0 to "min_channel"
          will be initialized but not actually used*/
        residuals->append(residuals);

    for (i = 0; i < block_size; i++) {
        unsigned m;

        /*read bypassed LSBs for each matrix*/
        for (m = 0; m < matrix_len; m++) {
            array_i* bypassed_LSB = bypassed_LSBs->_[m];
            if (matrix[m].LSB_bypass) {
                bypassed_LSB->append(bypassed_LSB, bs->read(bs, 1));
            } else {
                bypassed_LSB->append(bypassed_LSB, 0);
            }
        }

        /*read residuals for each channel*/
        for (c = min_channel; c <= max_channel; c++) {
            array_i* residual = residuals->_[c];
            int MSB;
            unsigned LSB;

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

            residual->append(residual,
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
        return x - (x % (1 << q));
}

mlp_status
filter_mlp_channel(const array_i* residuals,
                   struct filter_parameters* FIR,
                   struct filter_parameters* IIR,
                   unsigned quant_step_size,
                   array_i* filtered)
{
    const unsigned block_size = residuals->len;
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

    filtered->reset(filtered);
    for (i = 0; i < block_size; i++) {
        int64_t sum = 0;
        int shifted_sum;
        int j;
        int k;

        for (j = 0; j < FIR_order; j++) {
            if ((i - j - 1) < 0) {
                sum += ((int64_t)FIR->coeff->_[j] *
                        (int64_t)FIR->state->_[FIR_order + (i - j - 1)]);
            } else {
                sum += ((int64_t)FIR->coeff->_[j] *
                        (int64_t)filtered->_[i - j - 1]);
            }
        }

        for (k = 0; k < IIR_order; k++) {
            sum += ((int64_t)IIR->coeff->_[k] *
                    (int64_t)IIR->state->_[IIR_order + (i - k - 1)]);
        }

        shifted_sum = (int)(sum >> shift);

        filtered->append(filtered,
                         mask(shifted_sum + residuals->_[i], quant_step_size));

        IIR->state->append(IIR->state, filtered->_[i] - shifted_sum);
    }

    filtered->tail(filtered, 8, FIR->state);
    IIR->state->tail(IIR->state, 8, IIR->state);

    return OK;
}
