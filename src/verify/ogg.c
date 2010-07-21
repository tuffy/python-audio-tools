PyObject*
verifymodule_ogg(PyObject *dummy, PyObject *args) {
    PyObject *file_obj;
    Bitstream *bitstream;
    struct ogg_header header;
    uint8_t *data_buffer = NULL;
    int data_buffer_size = 0;

    if (!PyArg_ParseTuple(args, "O", &file_obj))
        return NULL;

    if (!PyFile_CheckExact(file_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be an actual file object");
        return NULL;
    } else {
        bitstream = bs_open(PyFile_AsFile(file_obj));
    }

    do {
        if (verifymodule_read_ogg_header(bitstream, &header) == OK) {
            verifymodule_print_ogg_header(&header);

            if (data_buffer_size < header.segment_length_total) {
                data_buffer = realloc(data_buffer,
                                      header.segment_length_total);
                data_buffer_size = header.segment_length_total;
            }
            if (fread(data_buffer,
                      sizeof(uint8_t),
                      header.segment_length_total,
                      bitstream->file) != header.segment_length_total) {
                PyErr_SetString(PyExc_IOError, "I/O error reading stream");
                goto error;
            }
            printf("\n");
        } else {
            goto error;
        }
    } while (!(header.type & 0x4));

    free(data_buffer);
    bitstream->file = NULL;
    bs_close(bitstream);
    Py_INCREF(Py_None);
    return Py_None;
 error:
    if (data_buffer != NULL)
        free(data_buffer);
    bitstream->file = NULL;
    bs_close(bitstream);
    return NULL;
}

status
verifymodule_read_ogg_header(Bitstream *bs, struct ogg_header *header) {
    int i;

    if ((header->magic_number = read_bits(bs, 32)) != 0x4F676753) {
        PyErr_SetString(PyExc_ValueError, "invalid magic number");
        return ERROR;
    }

    if ((header->version = read_bits(bs, 8)) != 0) {
        PyErr_SetString(PyExc_ValueError, "invalid stream version");
        return ERROR;
    }

    header->type = read_bits(bs, 8);
    header->granule_position = verifymodule_ulint64(read_bits64(bs, 64));
    header->bitstream_serial_number = verifymodule_ulint32(read_bits(bs, 32));
    header->page_sequence_number = verifymodule_ulint32(read_bits(bs, 32));
    /*FIXME - read this differently*/
    header->checksum = verifymodule_ulint32(read_bits(bs, 32));
    header->page_segment_count = read_bits(bs, 8);
    header->segment_length_total = 0;
    for (i = 0; i < header->page_segment_count; i++) {
        header->page_segment_lengths[i] = read_bits(bs, 8);
        header->segment_length_total += header->page_segment_lengths[i];
    }

    return OK;
}

void
verifymodule_print_ogg_header(struct ogg_header *header) {
    printf("magic number         : 0x%X\n", header->magic_number);
    printf("version              : 0x%X\n", header->version);
    printf("type                 : 0x%X\n", header->type);
    printf("granule position     : 0x%llX\n", header->granule_position);
    printf("bitstream serial #   : 0x%X\n", header->bitstream_serial_number);
    printf("page sequence number : 0x%X\n", header->page_sequence_number);
    printf("page segment count   : 0x%X\n", header->page_segment_count);
}

uint32_t
verifymodule_ulint32(uint32_t i) {
    uint32_t x = 0;
    int j;

    for (j = 0; j < 4; j++) {
        x = (x << 8) | (i & 0xFF);
        i >>= 8;
    }

    return x;
}

uint64_t
verifymodule_ulint64(uint64_t i) {
    uint64_t x = 0;
    int j;

    for (j = 0; j < 8; j++) {
        x = (x << 8) | (i & 0xFF);
        i >>= 8;
    }

    return x;
}
