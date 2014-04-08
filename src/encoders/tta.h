#ifndef STANDALONE
#include <Python.h>
#endif
#include "../bitstream.h"
#include "../array.h"

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

struct tta_cache {
    aa_int* correlated;
    aa_int* predicted;
    aa_int* residual;
    a_int* k0;
    a_int* sum0;
    a_int* k1;
    a_int* sum1;
};

static void
cache_init(struct tta_cache* cache);

static void
cache_free(struct tta_cache* cache);

static int
encode_frame(BitstreamWriter* output,
             struct tta_cache* cache,
             const aa_int* framelist,
             unsigned bits_per_sample);

static void
correlate_channels(const aa_int* channels,
                   aa_int* correlated);

static void
fixed_prediction(const a_int* channel,
                 unsigned bits_per_sample,
                 a_int* predicted);

static void
hybrid_filter(const a_int* predicted,
              unsigned bits_per_sample,
              a_int* residual);

static void
tta_byte_counter(uint8_t byte, int* frame_size);

#ifdef STANDALONE
static void
write_header(BitstreamWriter* output,
             unsigned channels,
             unsigned bits_per_sample,
             unsigned sample_rate,
             unsigned total_pcm_frames);

static void
write_seektable(BitstreamWriter* output,
                const a_int* frame_sizes);
#endif
