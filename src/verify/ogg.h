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

struct ogg_header {
    uint32_t magic_number;
    uint8_t version;
    uint8_t type;
    uint64_t granule_position;
    uint32_t bitstream_serial_number;
    uint32_t page_sequence_number;
    uint32_t checksum;
    uint8_t page_segment_count;
    uint8_t page_segment_lengths[0x100];
    uint32_t segment_length_total;
};

status
verifymodule_read_ogg_header(BitstreamReader *bs, struct ogg_header *header);

void
verifymodule_print_ogg_header(struct ogg_header *header);
