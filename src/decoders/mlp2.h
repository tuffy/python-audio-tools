#ifndef MLPDEC2
#define MLPDEC2
#include <Python.h>
#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"
#include "../pcm.h"

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

typedef enum {OK,
              IO_ERROR,
              INVALID_MAJOR_SYNC,
              INVALID_EXTRAWORD_PRESENT} mlp_status;

struct major_sync {
    unsigned bits_per_sample_0;
    unsigned bits_per_sample_1;
    unsigned sample_rate_0;
    unsigned sample_rate_1;
    unsigned channel_count;
    unsigned channel_mask;
    unsigned is_VBR;
    unsigned peak_bitrate;
    unsigned substream_count;
};

struct substream_info {
    unsigned extraword_present;
    unsigned nonrestart_substream;
    unsigned checkdata_present;
    unsigned substream_end;
};

typedef struct {
    BitstreamReader* reader;
    BitstreamReader* frame_reader;
    BitstreamReader* substream_reader;

    struct major_sync major_sync;
    struct substream_info substream_info[2];

} MLPDecoder;

MLPDecoder*
open_mlp_decoder(struct bs_buffer* frame_data);

void
close_mlp_decoder(MLPDecoder* decoder);

/*returns 1 if there isn't enough data in the current packet
  to decode at least 1 MLP frame
  returns 0 otherwise*/
int
mlp_packet_empty(MLPDecoder* decoder);

/*given an MLPDecoder pointing to a buffer of frame data
  (including length headers), decode as many frames as possible to framelist
  returns OK on success, or something else if an error occurs*/
mlp_status
read_mlp_frames(MLPDecoder* decoder,
                array_ia* framelist);

mlp_status
read_mlp_frame(MLPDecoder* decoder,
               BitstreamReader* bs,
               array_ia* framelist);

mlp_status
read_mlp_major_sync(BitstreamReader* bs,
                    struct major_sync* major_sync);

mlp_status
read_mlp_substream_info(BitstreamReader* bs,
                        struct substream_info* substream_info);

mlp_status
read_mlp_substream(MLPDecoder* decoder,
                   BitstreamReader* bs,
                   array_ia* framelist);
#endif
