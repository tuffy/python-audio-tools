#ifndef A_SHN_ENCODE
#define A_SHN_ENCODE

#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"
#include "../pcmconv.h"

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

#define COMMAND_SIZE 2
#define ENERGY_SIZE 3
#define VERBATIM_SIZE 5
#define VERBATIM_BYTE_SIZE 8
#define BITSHIFT_SIZE 2

#define SAMPLES_TO_WRAP 3

enum {FN_DIFF0     = 0,
      FN_DIFF1     = 1,
      FN_DIFF2     = 2,
      FN_DIFF3     = 3,
      FN_QUIT      = 4,
      FN_BLOCKSIZE = 5,
      FN_BITSHIFT  = 6,
      FN_QLPC      = 7,
      FN_ZERO      = 8,
      FN_VERBATIM  = 9};

static void
write_unsigned(BitstreamWriter* bs, unsigned c, unsigned value);

static void
write_signed(BitstreamWriter* bs, unsigned c, int value);

static void
write_long(BitstreamWriter* bs, unsigned value);

static void
write_header(BitstreamWriter* bs,
             unsigned bits_per_sample,
             int is_big_endian,
             int signed_samples,
             unsigned channels,
             unsigned block_size);

/*returns 0 on success, 1 if an exception occurs during encoding*/
static int
encode_audio(BitstreamWriter* bs,
             pcmreader* pcmreader,
             int signed_samples,
             unsigned block_size);

static int
all_zero(const array_i* samples);

static int
wasted_bits(const array_i* samples);

static void
calculate_best_diff(const array_i* samples,
                    const array_i* prev_samples,
                    array_ia* deltas,
                    unsigned* diff,
                    unsigned* energy,
                    array_i* residuals);

#endif
