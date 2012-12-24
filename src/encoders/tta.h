#ifndef STANDALONE
#include <Python.h>
#endif
#include "../bitstream.h"
#include "../array.h"

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

struct tta_cache {
    array_ia* correlated;
    array_ia* predicted;
    array_ia* residual;
    array_i* k0;
    array_i* sum0;
    array_i* k1;
    array_i* sum1;
};

static void
cache_init(struct tta_cache* cache);

static void
cache_free(struct tta_cache* cache);

static int
encode_frame(BitstreamWriter* output,
             struct tta_cache* cache,
             array_ia* framelist,
             unsigned bits_per_sample);

static void
correlate_channels(array_ia* channels,
                   array_ia* correlated);

static void
fixed_prediction(array_i* channel,
                 unsigned bits_per_sample,
                 array_i* predicted);

static void
hybrid_filter(array_i* predicted,
              unsigned bits_per_sample,
              array_i* filtered);

static void
tta_byte_counter(uint8_t byte, int* frame_size);
