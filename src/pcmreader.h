#include <stdio.h>

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

struct PCMReader {
    FILE *raw_data;

    unsigned sample_rate;
    unsigned channels;
    unsigned channel_mask;
    unsigned bits_per_sample;

    unsigned bytes_per_sample;
    int (*converter)(unsigned char *raw_pcm_data);

    /*reads up to the given number of PCM frames
      from this reader to the data array,
      which must be at least:

      pcm_frames * channels

      long in order to hold the returned data

      returns the amount of frames actually read
      which may be less than the number requested*/
    unsigned (*read)(struct PCMReader *self,
                     unsigned pcm_frames,
                     int *pcm_data);

    /*forwards a call to "close" to the wrapped PCMReader object*/
    void (*close)(struct PCMReader *self);

    /*decrefs any wrapped PCMReader object and deletes this reader*/
    void (*del)(struct PCMReader *self);
};

/*opens a PCMReader to a raw stream of PCM data*/
struct PCMReader*
pcmreader_open(FILE *file,
               unsigned sample_rate,
               unsigned channels,
               unsigned channel_mask,
               unsigned bits_per_sample,
               int is_little_endian,
               int is_signed);

/*given an array of channel data at least:

  pcm_frames * channel_count

  large, copies the requested channel to "channel_data" which must be
  "pcm_frames" large*/
void
get_channel_data(const int *pcm_data,
                 unsigned channel_number,
                 unsigned channel_count,
                 unsigned pcm_frames,
                 int *channel_data);

/*displays the PCMReader's parameters for debugging purposes*/
void
pcmreader_display(const struct PCMReader *pcmreader, FILE *output);
