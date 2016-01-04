#ifndef STANDALONE
#include <Python.h>
#endif

#include "../bitstream.h"
#include "../pcmreader.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

struct tta_frame_size {
    unsigned pcm_frames;
    unsigned byte_size;
    struct tta_frame_size *next; /*NULL at end of list*/
};

/*encodes as many TTA frames as possible from pcmreader to output
  and returns a list of TTA frame sizes
  which must be deallocated when no longer needed
  using free_tta_frame_sizes()

  returns NULL if some error occurs reading from PCMReader*/
struct tta_frame_size*
ttaenc_encode_tta_frames(struct PCMReader *pcmreader,
                         BitstreamWriter *output);

/*given a list of TTA frame sizes, returns the total PCM frames*/
unsigned
total_tta_frame_sizes(const struct tta_frame_size *frame_sizes);

void
free_tta_frame_sizes(struct tta_frame_size *frame_sizes);
