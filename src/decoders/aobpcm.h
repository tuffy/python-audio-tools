#ifndef AOBPCM2
#define AOBPCM2
#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdint.h>
#include "../bitstream.h"
#include "../array.h"

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

typedef struct {
    unsigned bps;        /*0 = 16bps, 1 = 24bps*/
    unsigned channels;
    unsigned bytes_per_sample; /* bits per sample / 8 */
    unsigned chunk_size; /* (bits per sample / 8) * channel count * 2 */
    int (*converter)(unsigned char *s);
} AOBPCMDecoder;

/*initializes the AOBPCMDecoder with the given bps and channel count*/
void
init_aobpcm_decoder(AOBPCMDecoder* decoder,
                    unsigned bits_per_sample,
                    unsigned channel_count);

int
aobpcm_packet_empty(AOBPCMDecoder* decoder,
                    struct bs_buffer* packet);

/*given an initialized AOBPCMDecoder
  along with packet data
  generates as many PCM frames as possible to framelist*/
void
read_aobpcm(AOBPCMDecoder* decoder,
            struct bs_buffer* packet,
            array_ia* framelist);

#endif
