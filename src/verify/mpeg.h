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

struct mpeg_header {
    int frame_sync;
    int mpeg_id;
    int layer_description;
    int protection;
    int bitrate;
    int sample_rate;
    int pad;
    int private;
    int channel_assignment;
    int mode_extension;
    int copyright;
    int original;
    int emphasis;
};

status
verifymodule_read_mpeg_header(BitstreamReader *bs, struct mpeg_header *header);

void
verifymodule_print_mpeg_header(struct mpeg_header *header);

int
verifymodule_mpeg_bitrate(struct mpeg_header *header);

int
verifymodule_mpeg_sample_rate(struct mpeg_header *header);

int
verifymodule_mpeg_channel_count(struct mpeg_header *header);
