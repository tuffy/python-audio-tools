#include "aobpcm.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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

static int
SL16_char_to_int(unsigned char *s);

static int
SL24_char_to_int(unsigned char *s);

void
init_aobpcm_decoder(AOBPCMDecoder* decoder,
                    unsigned bits_per_sample,
                    unsigned channel_count)
{
    assert((bits_per_sample == 16) || (bits_per_sample == 24));
    assert((1 <= channel_count) && (channel_count <= 6));

    if (bits_per_sample == 16) {
        decoder->bps = 0;
        decoder->converter = SL16_char_to_int;
    } else {
        decoder->bps = 1;
        decoder->converter = SL24_char_to_int;
    }

    decoder->channels = channel_count;

    decoder->bytes_per_sample = bits_per_sample / 8;

    decoder->chunk_size = decoder->bytes_per_sample * channel_count * 2;
}

int
aobpcm_packet_empty(AOBPCMDecoder* decoder,
                    struct bs_buffer* packet)
{
    return BUF_WINDOW_SIZE(packet) < decoder->chunk_size;
}

void
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
    unsigned i;

    assert(framelist->len == channels);

    while (BUF_WINDOW_SIZE(packet) >= chunk_size) {
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
            channel->append(channel, decoder->converter(unswapped_ptr));
            unswapped_ptr += bytes_per_sample;
        }
    }
}

static int
SL16_char_to_int(unsigned char *s)
{
    if (s[1] & 0x80) {
        /*negative*/
        return -(int)(0x10000 - ((s[1] << 8) | s[0]));
    } else {
        /*positive*/
        return (int)(s[1] << 8) | s[0];
    }
}

static int
SL24_char_to_int(unsigned char *s)
{
    if (s[2] & 0x80) {
        /*negative*/
        return -(int)(0x1000000 - ((s[2] << 16) | (s[1] << 8) | s[0]));
    } else {
        /*positive*/
        return (int)((s[2] << 16) | (s[1] << 8) | s[0]);
    }
}
