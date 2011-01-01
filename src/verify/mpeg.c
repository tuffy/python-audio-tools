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

PyObject*
verifymodule_mpeg(PyObject *dummy, PyObject *args) {
    PyObject *file_obj;
    Bitstream *bitstream;
    int start_byte;
    int end_byte;
    int remaining_bytes;
    int frame_size;
    struct mpeg_header header;
    struct mpeg_header first_header;
    int first_header_read = 0;
    uint8_t *data_buffer = NULL;
    int data_buffer_size = 0;

    /*fixes a "may be used unitialized" warning*/
    first_header.mpeg_id = first_header.layer_description =
        first_header.sample_rate = first_header.channel_assignment = 0;

    if (!PyArg_ParseTuple(args, "Oii", &file_obj, &start_byte, &end_byte))
        return NULL;

    if (!PyFile_CheckExact(file_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be an actual file object");
        return NULL;
    } else {
        bitstream = bs_open(PyFile_AsFile(file_obj), BS_BIG_ENDIAN);
    }

    remaining_bytes = end_byte - start_byte;

    if (!setjmp(*bs_try(bitstream))) {
        while (remaining_bytes > 0) {
            if (verifymodule_read_mpeg_header(bitstream, &header) == OK) {
                remaining_bytes -= 4;  /*decrement the header size*/

                if (!first_header_read) {
                    first_header = header;
                    first_header_read = 1;
                } else {
                    if (first_header.mpeg_id != header.mpeg_id) {
                        PyErr_SetString(PyExc_ValueError,
                                "MPEG IDs not consistent in stream");
                        goto error;
                    }
                    if (first_header.layer_description !=
                        header.layer_description) {
                        PyErr_SetString(PyExc_ValueError,
                                "MPEG layers not consistent in stream");
                        goto error;
                    }
                    if (first_header.sample_rate != header.sample_rate) {
                        PyErr_SetString(PyExc_ValueError,
                                "sample rates not consistent in stream");
                        goto error;
                    }
                    if (verifymodule_mpeg_channel_count(&first_header) !=
                        verifymodule_mpeg_channel_count(&header)) {
                        PyErr_SetString(PyExc_ValueError,
                                "channel counts not consistent in stream");
                        goto error;
                    }
                }

                /* verifymodule_print_mpeg_header(&header); */

                if (header.layer_description == 3) {  /*Layer-1*/
                    frame_size = (((12 * verifymodule_mpeg_bitrate(&header)) /
                                   verifymodule_mpeg_sample_rate(&header)) +
                                  header.pad) * 4;
                } else {                             /*Layer-2/3*/
                    frame_size = (((144 * verifymodule_mpeg_bitrate(&header)) /
                                   verifymodule_mpeg_sample_rate(&header)) +
                                  header.pad);
                }
                frame_size -= 4;  /*decrement the header size*/

                /* printf("frame size : %d\n", frame_size); */

                if (data_buffer_size < frame_size) {
                    data_buffer = realloc(data_buffer, frame_size);
                    data_buffer_size = frame_size;
                }
                if (fread(data_buffer, sizeof(uint8_t), frame_size,
                          bitstream->file) != frame_size) {
                    PyErr_SetString(PyExc_IOError, "I/O error reading stream");
                    goto error;
                }
                remaining_bytes -= frame_size;
            } else {
                goto error;
            }
        }
    } else {
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        goto error;
    }

    bs_etry(bitstream);
    bitstream->file = NULL;
    bs_close(bitstream);
    if (data_buffer != NULL)
        free(data_buffer);
    Py_INCREF(Py_None);
    return Py_None;
 error:
    bs_etry(bitstream);
    bitstream->file = NULL;
    if (data_buffer != NULL)
        free(data_buffer);
    bs_close(bitstream);
    return NULL;
}

status
verifymodule_read_mpeg_header(Bitstream *bs, struct mpeg_header *header) {
    if ((header->frame_sync = bs->read(bs, 11)) != 0x7FF) {
        PyErr_SetString(PyExc_ValueError, "invalid frame sync");
        return ERROR;
    }

    if ((header->mpeg_id = bs->read(bs, 2)) == 1) {
        PyErr_SetString(PyExc_ValueError, "invalid MPEG ID");
        return ERROR;
    }

    if ((header->layer_description = bs->read(bs, 2)) == 0) {
        PyErr_SetString(PyExc_ValueError, "invalid layer description");
        return ERROR;
    }

    header->protection = bs->read(bs, 1);

    if ((header->bitrate = bs->read(bs, 4)) == 0xF) {
        PyErr_SetString(PyExc_ValueError, "invalid bitrate");
        return ERROR;
    }

    if ((header->sample_rate = bs->read(bs, 2)) == 3) {
        PyErr_SetString(PyExc_ValueError, "invalid sample rate");
        return ERROR;
    }

    header->pad = bs->read(bs, 1);
    header->private = bs->read(bs, 1);
    header->channel_assignment = bs->read(bs, 2);
    header->mode_extension = bs->read(bs, 2);
    header->copyright = bs->read(bs, 1);
    header->original = bs->read(bs, 1);
    header->emphasis = bs->read(bs, 2);

    return OK;
}

void
verifymodule_print_mpeg_header(struct mpeg_header *header) {
    printf("frame sync         : %d\n", header->frame_sync);
    printf("mpeg id            : %d\n", header->mpeg_id);
    printf("layer description  : %d\n", header->layer_description);
    printf("protection         : %d\n", header->protection);
    printf("bitrate            : %d (%d)\n",
           header->bitrate,
           verifymodule_mpeg_bitrate(header));
    printf("sample rate        : %d (%d)\n",
           header->sample_rate,
           verifymodule_mpeg_sample_rate(header));
    printf("pad                : %d\n", header->pad);
    printf("private            : %d\n", header->private);
    printf("channel assignment : %d\n", header->channel_assignment);
    printf("mode extension     : %d\n", header->mode_extension);
    printf("copyright          : %d\n", header->copyright);
    printf("original           : %d\n", header->original);
    printf("emphasis           : %d\n", header->emphasis);
}

int
verifymodule_mpeg_bitrate(struct mpeg_header *header) {
    switch (header->mpeg_id) {
    case 3:  /*MPEG-1*/
        switch (header->layer_description) {
        case 3:  /*Layer-1*/
            switch (header->bitrate) {
            case 0x0: return 0;
            case 0x1: return 32000;
            case 0x2: return 64000;
            case 0x3: return 96000;
            case 0x4: return 128000;
            case 0x5: return 160000;
            case 0x6: return 192000;
            case 0x7: return 224000;
            case 0x8: return 256000;
            case 0x9: return 288000;
            case 0xA: return 320000;
            case 0xB: return 352000;
            case 0xC: return 384000;
            case 0xD: return 416000;
            case 0xE: return 448000;
            case 0xF: return 0;
            }
            break;
        case 2:  /*Layer-2*/
            switch (header->bitrate) {
            case 0x0: return 0;
            case 0x1: return 32000;
            case 0x2: return 48000;
            case 0x3: return 56000;
            case 0x4: return 64000;
            case 0x5: return 80000;
            case 0x6: return 96000;
            case 0x7: return 112000;
            case 0x8: return 128000;
            case 0x9: return 160000;
            case 0xA: return 192000;
            case 0xB: return 224000;
            case 0xC: return 256000;
            case 0xD: return 320000;
            case 0xE: return 384000;
            case 0xF: return 0;
            }
            break;
        case 1:  /*Layer-3*/
            switch (header->bitrate) {
            case 0x0: return 0;
            case 0x1: return 32000;
            case 0x2: return 40000;
            case 0x3: return 48000;
            case 0x4: return 56000;
            case 0x5: return 64000;
            case 0x6: return 80000;
            case 0x7: return 96000;
            case 0x8: return 112000;
            case 0x9: return 128000;
            case 0xA: return 160000;
            case 0xB: return 192000;
            case 0xC: return 224000;
            case 0xD: return 256000;
            case 0xE: return 320000;
            case 0xF: return 0;
            }
            break;
        }
        break;
    case 2:
    case 0:  /*MPEG-2/2.5*/
        switch (header->layer_description) {
        case 3:  /*Layer-1*/
            switch (header->bitrate) {
            case 0x0: return 0;
            case 0x1: return 32000;
            case 0x2: return 48000;
            case 0x3: return 56000;
            case 0x4: return 64000;
            case 0x5: return 80000;
            case 0x6: return 96000;
            case 0x7: return 112000;
            case 0x8: return 128000;
            case 0x9: return 144000;
            case 0xA: return 160000;
            case 0xB: return 176000;
            case 0xC: return 192000;
            case 0xD: return 224000;
            case 0xE: return 256000;
            case 0xF: return 0;
            }
            break;
        case 2:  /*Layer-2*/
        case 1:  /*Layer-3*/
            switch (header->bitrate) {
            case 0x0: return 0;
            case 0x1: return 8000;
            case 0x2: return 16000;
            case 0x3: return 24000;
            case 0x4: return 32000;
            case 0x5: return 40000;
            case 0x6: return 48000;
            case 0x7: return 56000;
            case 0x8: return 64000;
            case 0x9: return 80000;
            case 0xA: return 96000;
            case 0xB: return 112000;
            case 0xC: return 128000;
            case 0xD: return 144000;
            case 0xE: return 160000;
            case 0xF: return 0;
            }
            break;
        }
        break;
    }
    return 0;
}

int
verifymodule_mpeg_sample_rate(struct mpeg_header *header) {
    switch (header->mpeg_id) {
    case 3:  /*MPEG-1*/
        switch (header->sample_rate) {
        case 0: return 44100;
        case 1: return 48000;
        case 2: return 32000;
        }
        break;
    case 2:  /*MPEG-2*/
        switch (header->sample_rate) {
        case 0: return 22050;
        case 1: return 24000;
        case 2: return 16000;
        }
        break;
    case 0:  /*MPEG-2.5*/
        switch (header->sample_rate) {
        case 0: return 11025;
        case 1: return 12000;
        case 2: return 8000;
        }
        break;
    }
    return 0;
}

int
verifymodule_mpeg_channel_count(struct mpeg_header *header) {
    switch (header->channel_assignment) {
    case 0:
    case 1:
    case 2:
        return 2;
    case 3:
        return 1;
    }
    return 0;
}
