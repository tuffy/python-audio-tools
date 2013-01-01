#include "ogg.h"
#include "../common/ogg_crc.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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
    reader->ogg_stream = br_open(stream, BS_LITTLE_ENDIAN);
    reader->current_segment = 1;
    reader->current_header.page_segment_count = 0;
    reader->current_header.type = 0;
    reader->current_header.checksum = 0;
    reader->checksum = 0;
    br_add_callback(reader->ogg_stream, ogg_crc, &(reader->checksum));
    return reader;
}

void
oggreader_close(OggReader *reader) {
    reader->ogg_stream->close(reader->ogg_stream);
    free(reader);
}

ogg_status
oggreader_read_page_header(BitstreamReader *ogg_stream,
                           struct ogg_page_header *header) {
    int i;
    struct bs_callback callback;

    if (!setjmp(*br_try(ogg_stream))) {
        if ((header->magic_number =
             ogg_stream->read(ogg_stream, 32)) != 0x5367674F) {
            br_etry(ogg_stream);
            return OGG_INVALID_MAGIC_NUMBER;
        }

        if ((header->version = ogg_stream->read(ogg_stream, 8)) != 0) {
            br_etry(ogg_stream);
            return OGG_INVALID_STREAM_VERSION;
        }

        header->type = ogg_stream->read(ogg_stream, 8);
        header->granule_position = ogg_stream->read_64(ogg_stream, 64);
        header->bitstream_serial_number = ogg_stream->read(ogg_stream, 32);
        header->page_sequence_number = ogg_stream->read(ogg_stream, 32);

        /*the checksum field is *not* checksummed itself, naturally
          those 4 bytes are treated as 0*/
        br_pop_callback(ogg_stream, &callback);
        header->checksum = ogg_stream->read(ogg_stream, 32);
        br_push_callback(ogg_stream, &callback);
        br_call_callbacks(ogg_stream, 0);
        br_call_callbacks(ogg_stream, 0);
        br_call_callbacks(ogg_stream, 0);
        br_call_callbacks(ogg_stream, 0);

        header->page_segment_count = ogg_stream->read(ogg_stream, 8);
        header->segment_length_total = 0;
        for (i = 0; i < header->page_segment_count; i++) {
            header->page_segment_lengths[i] = ogg_stream->read(ogg_stream, 8);
            header->segment_length_total += header->page_segment_lengths[i];
        }

        br_etry(ogg_stream);
        return OGG_OK;
    } else {
        br_etry(ogg_stream);
        return OGG_PREMATURE_EOF;
    }
}

ogg_status
oggreader_next_segment(OggReader *reader,
                       BitstreamReader *packet,
                       uint8_t *segment_size) {
    ogg_status status;

    if (reader->current_segment < reader->current_header.page_segment_count) {
        /*return an Ogg segment from the current page*/
        *segment_size = reader->current_header.page_segment_lengths[
                                                reader->current_segment++];
        if (!setjmp(*br_try(reader->ogg_stream))) {
            reader->ogg_stream->substream_append(reader->ogg_stream,
                                                 packet,
                                                 *segment_size);
            br_etry(reader->ogg_stream);
            return OGG_OK;
        } else {
            br_etry(reader->ogg_stream);
            return OGG_PREMATURE_EOF;
        }
    } else {
        /*the current page is finished*/

        /*validate page checksum*/
        if (reader->current_header.checksum != reader->checksum) {
            return OGG_CHECKSUM_MISMATCH;
        }

        /*if the current page isn't the final page,
          read the next page from the stream*/
        if (reader->current_header.type & 0x4) {
            return OGG_STREAM_FINISHED;
        } else {
            reader->checksum = 0;
            status = oggreader_read_page_header(reader->ogg_stream,
                                                &(reader->current_header));
            reader->current_segment = 0;
            if (status == OGG_OK) {
                return oggreader_next_segment(reader, packet, segment_size);
            } else
                return status;
        }
    }
}

ogg_status
oggreader_next_packet(OggReader *reader, BitstreamReader *packet) {
    ogg_status result;
    uint8_t segment_length;

    br_substream_reset(packet);
    do {
        result = oggreader_next_segment(reader, packet, &segment_length);
    } while ((result == OGG_OK) && (segment_length == 255));

    return result;
}

char *
ogg_strerror(ogg_status err) {
    switch (err) {
    case OGG_OK:                    /*not an actual error*/
        return "no error";
    case OGG_STREAM_FINISHED:       /*not an actual error*/
        return "stream finished";
    case OGG_INVALID_MAGIC_NUMBER:
        return "invalid magic number";
    case OGG_INVALID_STREAM_VERSION:
        return "invalid stream version";
    case OGG_CHECKSUM_MISMATCH:
        return "checksum mismatch";
    case OGG_PREMATURE_EOF:
        return "premature EOF reading Ogg stream";
    }
    return "unknown error"; /*shouldn't get here*/
}

#ifndef STANDALONE
PyObject*
ogg_exception(ogg_status err) {
    switch (err) {
    case OGG_PREMATURE_EOF:
    case OGG_STREAM_FINISHED:       /*not an actual error*/
        return PyExc_IOError;
    case OGG_INVALID_MAGIC_NUMBER:
    case OGG_INVALID_STREAM_VERSION:
    case OGG_CHECKSUM_MISMATCH:
        return PyExc_ValueError;
    case OGG_OK:                    /*not an actual error*/
    default:
        return PyExc_ValueError;
    }
}
#endif

#ifdef EXECUTABLE
int main(int argc, char *argv[]) {
    FILE *f = fopen(argv[1], "rb");
    OggReader *reader = oggreader_open(f);
    BitstreamReader *packet = bs_substream_new(BS_LITTLE_ENDIAN);
    ogg_status result;

    do {
        result = oggreader_next_packet(reader, packet);
        if (result < 0) {
            fprintf(stderr, "Error : %s\n", ogg_error(result));
        } else if (result == OGG_OK) {
            printf("packet size %u\n", packet->input.substream->buffer_size);
        }
    } while (result == OGG_OK);

    packet->close(packet);
    oggreader_close(reader);
    fclose(f);
    return 0;
}
#endif
