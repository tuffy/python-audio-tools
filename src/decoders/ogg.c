#include "ogg.h"

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

OggReader*
oggreader_open(FILE *stream) {
    OggReader *reader = malloc(sizeof(OggReader));
    reader->ogg_stream = bs_open(stream, BS_LITTLE_ENDIAN);
    reader->current_segment = 1;
    reader->current_header.page_segment_count = 0;
    return reader;
}

void
oggreader_close(OggReader *reader) {
    reader->ogg_stream->close(reader->ogg_stream);
    free(reader);
}

ogg_status
oggreader_read_page_header(Bitstream *ogg_stream,
                           struct ogg_page_header *header) {
    int i;
    uint8_t checksum[4];

    if ((header->magic_number = ogg_stream->read(ogg_stream, 32)) != 0x5367674F)
        return OGG_INVALID_MAGIC_NUMBER;

    if ((header->version = ogg_stream->read(ogg_stream, 8)) != 0)
        return OGG_INVALID_STREAM_VERSION;

    header->type = ogg_stream->read(ogg_stream, 8);
    header->granule_position = ogg_stream->read_64(ogg_stream, 64);
    header->bitstream_serial_number = ogg_stream->read(ogg_stream, 32);
    header->page_sequence_number = ogg_stream->read(ogg_stream, 32);

    if (fread(checksum, sizeof(uint8_t), 4, ogg_stream->input.file) == 4) {
        header->checksum = checksum[0] |
            (checksum[1] << 8) |
            (checksum[2] << 16) |
            (checksum[3] << 24);
        for (i = 0; i < 4; i++)
            bs_call_callbacks(ogg_stream, 0);
    } else {
        bs_abort(ogg_stream);
    }

    header->page_segment_count = ogg_stream->read(ogg_stream, 8);
    header->segment_length_total = 0;
    for (i = 0; i < header->page_segment_count; i++) {
        header->page_segment_lengths[i] = ogg_stream->read(ogg_stream, 8);
        header->segment_length_total += header->page_segment_lengths[i];
    }

    return OK;
}

ogg_status
oggreader_next_segment(OggReader *reader,
                       Bitstream *packet,
                       uint8_t *segment_size) {
    ogg_status status;

    if (reader->current_segment < reader->current_header.page_segment_count) {
        /*return an Ogg segment from the current page*/
        *segment_size = reader->current_header.page_segment_lengths[
                                                reader->current_segment++];
        reader->ogg_stream->substream_append(reader->ogg_stream,
                                             packet,
                                             *segment_size);
        return OK;
    } else {
        /*the current page is finished
          so validate the page's checksum
          then move on to the next page*/
        /*FIXME - validate checksum here*/

        status = oggreader_read_page_header(reader->ogg_stream,
                                            &(reader->current_header));
        reader->current_segment = 0;
        if (status == OK) {
            return oggreader_next_segment(reader, packet, segment_size);
        } else
            return status;
    }
}

ogg_status
oggreader_next_packet(OggReader *reader, Bitstream **packet) {
    *packet = bs_substream_new(BS_LITTLE_ENDIAN);
    ogg_status result;
    uint8_t segment_length;

    do {
        result = oggreader_next_segment(reader, *packet, &segment_length);
    } while ((result == OK) && (segment_length == 255));

    if (result != OK) {
        (*packet)->close(*packet);
    }

    return result;
}

char *
ogg_error(ogg_status err) {
    switch (err) {
    case OK:
        return "no error";
    case OGG_INVALID_MAGIC_NUMBER:
        return "invalid magic number";
    case OGG_INVALID_STREAM_VERSION:
        return "invalid stream version";
    }
    return ""; /*shouldn't get here*/
}

int main(int argc, char *argv[]) {
    FILE *f = fopen(argv[1], "rb");
    OggReader *reader = oggreader_open(f);
    Bitstream *packet;
    ogg_status error;
    int i;

    for (i = 0; i < 10000; i++) {
        if ((error = oggreader_next_packet(reader, &packet)) != OK) {
            fprintf(stderr, "Error : %s\n", ogg_error(error));
            break;
        } else {
            printf("packet size %u\n", packet->input.substream->buffer_size);
            packet->close(packet);
        }
    }

    oggreader_close(reader);
    fclose(f);
    return 0;
}
