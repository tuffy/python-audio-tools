#include <stdint.h>
#include "../pcmreader.h"
#include "../bitstream.h"
#include "../common/md5.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

typedef enum {
    COMPRESSION_UNKNOWN,
    COMPRESSION_FAST,
    COMPRESSION_NORMAL,
    COMPRESSION_HIGH,
    COMPRESSION_VERYHIGH
} wavpack_compression_t;

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int pcm_data[],
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames);

static int
block_out(BitstreamWriter *output, uint8_t *data, int32_t byte_count);

static int
encode_wavpack(BitstreamWriter *output,
               struct PCMReader *pcmreader,
               uint32_t total_pcm_frames,
               unsigned block_size,
               wavpack_compression_t compression,
               uint32_t header_size,
               uint8_t *header_data,
               uint32_t footer_size,
               uint8_t *footer_data);

