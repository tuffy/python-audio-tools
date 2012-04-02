#include "../common/ogg_crc.h"

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

PyObject*
verifymodule_ogg(PyObject *dummy, PyObject *args) {
    PyObject *file_obj;
    BitstreamReader *bitstream;
    int has_previous_header = 0;
    struct ogg_header previous_header;
    struct ogg_header header;
    uint8_t *data_buffer = NULL;
    int data_buffer_size = 0;
    int i;
    uint32_t checksum;

    /*fixes a "may be used unitialized" warning*/
    previous_header.bitstream_serial_number =
        previous_header.page_sequence_number = 0;

    if (!PyArg_ParseTuple(args, "O", &file_obj))
        return NULL;

    if (!PyFile_CheckExact(file_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be an actual file object");
        return NULL;
    } else {
        bitstream = br_open(PyFile_AsFile(file_obj), BS_LITTLE_ENDIAN);
        br_add_callback(bitstream, ogg_crc, &checksum);
    }

    if (!setjmp(*br_try(bitstream))) {
        do {
            checksum = 0;
            if (verifymodule_read_ogg_header(bitstream, &header) == OK) {
                if (data_buffer_size < header.segment_length_total) {
                    data_buffer = realloc(data_buffer,
                                          header.segment_length_total);
                    data_buffer_size = header.segment_length_total;
                }
                if (fread(data_buffer,
                          sizeof(uint8_t),
                          header.segment_length_total,
                          bitstream->input.file) !=
                    header.segment_length_total) {
                    PyErr_SetString(PyExc_IOError, "I/O error reading stream");
                    goto error;
                }

                for (i = 0; i < header.segment_length_total; i++)
                    ogg_crc(data_buffer[i], &checksum);
                if (header.checksum != checksum) {
                    PyErr_SetString(PyExc_ValueError,
                                    "checksum mismatch in stream");
                    goto error;
                }

                /* printf("calculated checksum : 0x%8.8X\n", checksum); */

                if (has_previous_header) {
                    if (header.bitstream_serial_number !=
                        previous_header.bitstream_serial_number) {
                        PyErr_SetString(PyExc_ValueError,
                                        "differing serial numbers in stream");
                        goto error;
                    }
                    if (header.page_sequence_number !=
                        (previous_header.page_sequence_number + 1)) {
                        PyErr_SetString(PyExc_ValueError,
                                        "page sequence number not incrementing");
                        goto error;
                    }
                    previous_header = header;
                } else {
                    previous_header = header;
                    has_previous_header = 1;
                }
            } else {
                goto error;
            }
        } while (!(header.type & 0x4));
    } else {
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        goto error;
    }

    br_etry(bitstream);
    free(data_buffer);
    bitstream->input.file = NULL;
    bitstream->free(bitstream);
    Py_INCREF(Py_None);
    return Py_None;
 error:
    br_etry(bitstream);
    if (data_buffer != NULL)
        free(data_buffer);
    bitstream->input.file = NULL;
    bitstream->free(bitstream);
    return NULL;
}

status
verifymodule_read_ogg_header(BitstreamReader *bs, struct ogg_header *header) {
    int i;
    uint8_t checksum[4];

    if ((header->magic_number = bs->read(bs, 32)) != 0x5367674F) {
        PyErr_SetString(PyExc_ValueError, "invalid magic number");
        return ERROR;
    }

    if ((header->version = bs->read(bs, 8)) != 0) {
        PyErr_SetString(PyExc_ValueError, "invalid stream version");
        return ERROR;
    }

    header->type = bs->read(bs, 8);
    header->granule_position = bs->read_64(bs, 64);
    header->bitstream_serial_number = bs->read(bs, 32);
    header->page_sequence_number = bs->read(bs, 32);

    if (fread(checksum, sizeof(uint8_t), 4, bs->input.file) == 4) {
        header->checksum = checksum[0] |
            (checksum[1] << 8) |
            (checksum[2] << 16) |
            (checksum[3] << 24);
        for (i = 0; i < 4; i++)
            br_call_callbacks(bs, 0);
    } else {
        PyErr_SetString(PyExc_IOError, "I/O reading stream");
        return ERROR;
    }

    header->page_segment_count = bs->read(bs, 8);
    header->segment_length_total = 0;
    for (i = 0; i < header->page_segment_count; i++) {
        header->page_segment_lengths[i] = bs->read(bs, 8);
        header->segment_length_total += header->page_segment_lengths[i];
    }

    return OK;
}
