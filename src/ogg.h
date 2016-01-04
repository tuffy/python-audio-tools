#ifndef STANDALONE
#include <Python.h>
#endif
#include "bitstream.h"

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

typedef enum {OGG_OK = 0,
              OGG_STREAM_FINISHED = 1,
              OGG_INVALID_MAGIC_NUMBER = -1,
              OGG_INVALID_STREAM_VERSION = -2,
              OGG_CHECKSUM_MISMATCH = -3,
              OGG_PREMATURE_EOF = -4} ogg_status;

struct ogg_page_header {
    unsigned magic_number;
    unsigned version;
    unsigned packet_continuation;
    unsigned stream_beginning;
    unsigned stream_end;
    int64_t granule_position;
    unsigned bitstream_serial_number;
    unsigned sequence_number;
    unsigned checksum;
    unsigned segment_count;
    unsigned segment_lengths[0x100];
};

struct ogg_page {
    struct ogg_page_header header;
    uint8_t segment[0x100][0x100];
};

ogg_status
read_ogg_page_header(BitstreamReader *ogg_stream,
                     struct ogg_page_header *header);

ogg_status
read_ogg_page(BitstreamReader *ogg_stream,
              struct ogg_page *page);

void
write_ogg_page(BitstreamWriter *ogg_stream,
               const struct ogg_page *page);


typedef struct OggPacketIterator_s {
    BitstreamReader *reader;
    struct ogg_page page;
    uint8_t current_segment;
} OggPacketIterator;

OggPacketIterator*
oggiterator_open(FILE *stream);

void
oggiterator_close(OggPacketIterator *iterator);

/*places a pointer to the next segment in "segment_data"
  and its size in "segment_size"
  the segment is pulled directly from an internal Ogg page
  and should *not* be freed when finished*/
ogg_status
oggiterator_next_segment(OggPacketIterator *iterator,
                         uint8_t **segment_data,
                         uint8_t *segment_size);

/*builds an entire Ogg packet from segments
  and returns a BitsreamReader of its data for further parsing
  the reader must be closed when finished with it

  endianness is applied to the newly created packet reader

  may return NULL and set "status" to something other than OGG_OK
  if an error occurs reading segments from the stream*/
BitstreamReader*
oggiterator_next_packet(OggPacketIterator *iterator,
                        bs_endianness endianness,
                        ogg_status *status);


char *
ogg_strerror(ogg_status err);


#ifndef STANDALONE
PyObject*
ogg_exception(ogg_status err);
#endif
