#include "aobpcm2.h"

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

void
init_aobpcm_decoder(AOBPCMDecoder* decoder,
                    unsigned bits_per_sample,
                    unsigned channel_count)
{
    assert((bits_per_sample == 16) || (bits_per_sample == 24));
    assert((1 <= channel_count) && (channel_count <= 6));

    if (bits_per_sample == 16) {
        decoder->bps = 0;
    } else {
        decoder->bps = 1;
    }

    decoder->channels = channel_count;

    decoder->bytes_per_sample = bits_per_sample / 8;

    decoder->chunk_size = decoder->bytes_per_sample * channel_count * 2;

    decoder->converter = FrameList_get_char_to_int_converter(bits_per_sample,
                                                             0, 1);
}

int
aobpcm_packet_empty(AOBPCMDecoder* decoder,
                    struct bs_buffer* packet)
{
    return (packet->buffer_size -
            packet->buffer_position) < decoder->chunk_size;
}

unsigned
read_aobpcm(AOBPCMDecoder* decoder,
            struct bs_buffer* packet,
            array_ia* framelist)
{
    const static uint8_t AOB_BYTE_SWAP[2][6][36] = {
        { /*16 bps*/
            {1, 0, 3, 2},                                    /*1 ch*/
            {1, 0, 3, 2, 5, 4, 7, 6},                        /*2 ch*/
            {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10},          /*3 ch*/
            {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10,
             13, 12, 15, 14},                                /*4 ch*/
            {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10,
             13, 12, 15, 14, 17, 16, 19, 18},                /*5 ch*/
            {1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10,
             13, 12, 15, 14, 17, 16, 19, 18, 21, 20, 23, 22} /*6 ch*/
        },
        { /*24 bps*/
            {  2,  1,  5,  4,  0,  3},  /*1 ch*/
            {  2,  1,  5,  4,  8,  7,
               11, 10,  0,  3,  6,  9},  /*2 ch*/
            {  8,  7, 17, 16,  6, 15,
               2,  1,  5,  4, 11, 10,
               14, 13,  0,  3,  9, 12},  /*3 ch*/
            {  8,  7, 11, 10, 20, 19,
               23, 22,  6,  9, 18, 21,
               2,  1,  5,  4, 14, 13,
               17, 16,  0,  3, 12, 15},  /*4 ch*/
            {  8,  7, 11, 10, 14, 13,
               23, 22, 26, 25, 29, 28,
               6,  9, 12, 21, 24, 27,
               2,  1,  5,  4, 17, 16,
               20, 19,  0,  3, 15, 18},  /*5 ch*/
            {  8,  7, 11, 10, 26, 25,
               29, 28,  6,  9, 24, 27,
               2,  1,  5,  4, 14, 13,
               17, 16, 20, 19, 23, 22,
               32, 31, 35, 34,  0,  3,
               12, 15, 18, 21, 30, 33}  /*6 ch*/
        }
    };
    const unsigned bps = decoder->bps;
    const unsigned channels = decoder->channels;
    const unsigned chunk_size = decoder->chunk_size;
    const unsigned bytes_per_sample = decoder->bytes_per_sample;
    const FrameList_char_to_int_converter converter = decoder->converter;
    unsigned pcm_frames_decoded = 0;
    unsigned i;

    assert(framelist->len == channels);

    while ((packet->buffer_size - packet->buffer_position) >= chunk_size) {
        uint8_t unswapped[36];
        uint8_t* unswapped_ptr = unswapped;
        /*swap read bytes to proper order*/
        for (i = 0; i < chunk_size; i++) {
            unswapped[AOB_BYTE_SWAP[bps][channels - 1][i]] =
                (uint8_t)buf_getc(packet);
        }

        /*decode bytes to PCM ints and place them in proper channels*/
        for (i = 0; i < (channels * 2); i++) {
            array_i* channel = framelist->_[i % channels];
            channel->append(channel, converter(unswapped_ptr));
            unswapped_ptr += bytes_per_sample;
        }

        pcm_frames_decoded += 2;
    }

    return pcm_frames_decoded;
}
