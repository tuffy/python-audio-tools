#include "ogg.h"
#include "ogg_crc.h"
#include <string.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

ogg_status
read_ogg_page_header(BitstreamReader *ogg_stream,
                     struct ogg_page_header *header) {
    int i;
    struct bs_callback callback;

    if ((header->magic_number =
         ogg_stream->read(ogg_stream, 32)) != 0x5367674F) {
        return OGG_INVALID_MAGIC_NUMBER;
    }

    if ((header->version = ogg_stream->read(ogg_stream, 8)) != 0) {
        return OGG_INVALID_STREAM_VERSION;
    }

    header->packet_continuation = ogg_stream->read(ogg_stream, 1);
    header->stream_beginning = ogg_stream->read(ogg_stream, 1);
    header->stream_end = ogg_stream->read(ogg_stream, 1);
    ogg_stream->skip(ogg_stream, 5);
    header->granule_position = ogg_stream->read_signed_64(ogg_stream, 64);
    header->bitstream_serial_number = ogg_stream->read(ogg_stream, 32);
    header->sequence_number = ogg_stream->read(ogg_stream, 32);

    /*the checksum field is *not* checksummed itself, naturally
      those 4 bytes are treated as 0*/
    br_pop_callback(ogg_stream, &callback);
    if (!setjmp(*br_try(ogg_stream))) {
        header->checksum = ogg_stream->read(ogg_stream, 32);
        br_etry(ogg_stream);
        br_push_callback(ogg_stream, &callback);
    } else {
        /*restore callback before propagating read error*/
        br_etry(ogg_stream);
        br_push_callback(ogg_stream, &callback);
        br_abort(ogg_stream);
    }
    br_call_callbacks(ogg_stream, 0);
    br_call_callbacks(ogg_stream, 0);
    br_call_callbacks(ogg_stream, 0);
    br_call_callbacks(ogg_stream, 0);

    header->segment_count = ogg_stream->read(ogg_stream, 8);
    for (i = 0; i < header->segment_count; i++) {
        header->segment_lengths[i] = ogg_stream->read(ogg_stream, 8);
    }

    return OGG_OK;
}

ogg_status
read_ogg_page(BitstreamReader *ogg_stream,
              struct ogg_page *page)
{
    uint32_t checksum = 0;

    if (!setjmp(*br_try(ogg_stream))) {
        uint8_t i;
        ogg_status result;

        /*attach checksum calculator to stream*/
        br_add_callback(ogg_stream, (bs_callback_f)ogg_crc, &checksum);

        /*read header*/
        if ((result = read_ogg_page_header(ogg_stream,
                                           &(page->header))) != OGG_OK) {
            /*abort if error in header*/
            br_pop_callback(ogg_stream, NULL);
            br_etry(ogg_stream);
            return result;
        }

        /*populate segments based on lengths in header*/
        for (i = 0; i < page->header.segment_count; i++) {
            ogg_stream->read_bytes(ogg_stream,
                                   page->segment[i],
                                   page->header.segment_lengths[i]);
        }

        /*remove checksum calculator from stream*/
        br_pop_callback(ogg_stream, NULL);

        /*no more I/O needed for page*/
        br_etry(ogg_stream);

        /*validate checksum*/
        if (checksum == page->header.checksum) {
            return OGG_OK;
        } else {
            return OGG_CHECKSUM_MISMATCH;
        }
    } else {
        br_pop_callback(ogg_stream, NULL);
        br_etry(ogg_stream);
        return OGG_PREMATURE_EOF;
    }
}

void
write_ogg_page_header(BitstreamWriter *ogg_stream,
                            const struct ogg_page_header *header)
{
    uint8_t i;
    struct bs_callback callback;

    ogg_stream->write(ogg_stream, 32, header->magic_number);
    ogg_stream->write(ogg_stream, 8, header->version);
    ogg_stream->write(ogg_stream, 1, header->packet_continuation);
    ogg_stream->write(ogg_stream, 1, header->stream_beginning);
    ogg_stream->write(ogg_stream, 1, header->stream_end);
    ogg_stream->write(ogg_stream, 5, 0);
    ogg_stream->write_signed_64(ogg_stream, 64, header->granule_position);
    ogg_stream->write(ogg_stream, 32, header->bitstream_serial_number);
    ogg_stream->write(ogg_stream, 32, header->sequence_number);

    /*the checksum field is *not* checksummed itself, naturally
      those 4 bytes are treated as 0*/
    bw_pop_callback(ogg_stream, &callback);
    ogg_stream->write(ogg_stream, 32, header->checksum);
    bw_push_callback(ogg_stream, &callback);
    bw_call_callbacks(ogg_stream, 0);
    bw_call_callbacks(ogg_stream, 0);
    bw_call_callbacks(ogg_stream, 0);
    bw_call_callbacks(ogg_stream, 0);

    ogg_stream->write(ogg_stream, 8, header->segment_count);
    for (i = 0; i < header->segment_count; i++)
        ogg_stream->write(ogg_stream, 8, header->segment_lengths[i]);
}

void
write_ogg_page(BitstreamWriter *ogg_stream,
               const struct ogg_page *page)
{
    uint32_t checksum = 0;
    BitstreamWriter *temp = bw_open_recorder(BS_LITTLE_ENDIAN);
    uint8_t i;

    /*attach checksum calculator to temporary stream*/
    bw_add_callback(temp, (bs_callback_f)ogg_crc, &checksum);

    /*dump header and data to temporary stream*/
    write_ogg_page_header(temp, &(page->header));
    for (i = 0; i < page->header.segment_count; i++) {
        temp->write_bytes(temp,
                          page->segment[i],
                          page->header.segment_lengths[i]);
    }

    /*output header, calculated checksum and the rest to actual stream*/
    bw_rec_split(ogg_stream, temp, temp, 22);
    ogg_stream->write(ogg_stream, 32, checksum);
    bw_rec_split(NULL, temp, temp, 4);
    bw_rec_copy(ogg_stream, temp);

    /*remove temporary stream*/
    temp->close(temp);
}


OggPacketIterator*
oggiterator_open(FILE *stream)
{
    OggPacketIterator *iterator = malloc(sizeof(OggPacketIterator));
    iterator->reader = br_open(stream, BS_LITTLE_ENDIAN);

    /*force next read to read in a new page*/
    iterator->page.header.segment_count = 0;
    iterator->current_segment = 1;
    iterator->page.header.stream_end = 0;
    return iterator;
}

void
oggiterator_close(OggPacketIterator *iterator)
{
    iterator->reader->close(iterator->reader);
    free(iterator);
}

ogg_status
oggiterator_next_segment(OggPacketIterator *iterator,
                         uint8_t **segment_data,
                         uint8_t *segment_size)
{
    if (iterator->current_segment < iterator->page.header.segment_count) {
        /*return Ogg segment from current page*/
        *segment_size =
            iterator->page.header.segment_lengths[iterator->current_segment];
        *segment_data =
            iterator->page.segment[iterator->current_segment];
        iterator->current_segment++;
        return OGG_OK;
    } else {
        ogg_status result;

        /*current page's segments exhausted
          so read another unless the page is marked as the last*/
        if (!iterator->page.header.stream_end) {
            if ((result = read_ogg_page(iterator->reader,
                                        &(iterator->page))) == OGG_OK) {
                iterator->current_segment = 0;
                return oggiterator_next_segment(iterator,
                                                segment_data,
                                                segment_size);
            } else {
                return result;
            }
        } else {
            return OGG_STREAM_FINISHED;
        }
    }
}

ogg_status
oggiterator_next_packet(OggPacketIterator *iterator,
                        struct bs_buffer *packet)
{
    ogg_status result;
    uint8_t *segment_data;
    uint8_t segment_length;

    do {
        if ((result = oggiterator_next_segment(iterator,
                                               &segment_data,
                                               &segment_length)) == OGG_OK) {
            buf_write(packet, segment_data, segment_length);
        }
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
    /*perform simple round-trip using page reader and writer*/

    BitstreamReader *reader = br_open(stdin, BS_LITTLE_ENDIAN);
    BitstreamWriter *writer = bw_open(stdout, BS_LITTLE_ENDIAN);
    struct ogg_page page;

    do {
        ogg_status result;
        if ((result = read_ogg_page(reader, &page)) == OGG_OK) {
            write_ogg_page(writer, &page);
        } else {
            fprintf(stderr, "*** Error: %s", ogg_strerror(result));
            goto error;
        }
    } while (!page.header.stream_end);

    reader->close(reader);
    writer->close(writer);
    return 0;

error:
    reader->close(reader);
    writer->close(writer);
    return 1;
}
#endif
