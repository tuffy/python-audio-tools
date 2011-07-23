#include "misc.h"
#include <assert.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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
channel_mask_splits(struct i_array *counts,
                    unsigned int channel_count,
                    unsigned int channel_mask) {
    /*Although the WAVEFORMATEXTENSIBLE channel mask
      supports more left/right channels than these,
      everything beyond side-left/side-right
      is stored with a center channel in-between
      which means we can't pull them apart in pairs.*/
    unsigned int masks[] = {0x3,   0x1,   0x2,        /*fLfR, fL, fR*/
                            0x4,   0x8,               /*fC, LFE*/
                            0x30,  0x10,  0x20,       /*bLbR, bL, bR*/
                            0xC0,  0x40,  0x80,       /*fLoC, fRoC, fLoC, fRoC*/
                            0x100,                    /*bC*/
                            0x600, 0x200, 0x400,      /*sLsR, sL, sR*/
                            0};
    unsigned int channels;
    int i;

    assert(channel_count > 0);

    /*first, try to pull left/right channels out of the mask*/
    for (i = 0; channel_mask && masks[i]; i++) {
        if (channel_mask & masks[i]) {
            channels = count_one_bits(masks[i]);
            ia_append(counts, channels);
            channel_count -= channels;
            channel_mask ^= masks[i];
        }
    }

    /*any leftover channels are sent out in separate blocks
      (which may happen with a mask of 0)*/
    for (; channel_count > 0; channel_count--) {
        ia_append(counts, 1);
    }
}

unsigned int
count_one_bits(unsigned int i) {
    unsigned int bits;

    for (bits = 0; i != 0; i >>= 1)
        bits += (i & 1);

    return bits;
}
