#include "vorbis.h"

PyObject*
VorbisDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_VorbisDecoder *self;

    self = (decoders_VorbisDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
VorbisDecoder_dealloc(decoders_VorbisDecoder *self) {
    self->packet->close(self->packet);
    if (self->ogg_stream != NULL)
        oggreader_close(self->ogg_stream);

    self->ob_type->tp_free((PyObject*)self);
}

int
VorbisDecoder_init(decoders_VorbisDecoder *self, PyObject *args, PyObject *kwds) {
    char* filename;
    ogg_status ogg_result;
    vorbis_status vorbis_result;

    self->ogg_stream = NULL;
    self->ogg_file = NULL;
    self->packet = bs_substream_new(BS_LITTLE_ENDIAN);

    if (!PyArg_ParseTuple(args, "s", &filename))
        goto error;
    self->ogg_file = fopen(filename, "rb");
    if (self->ogg_file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        goto error;
    } else {
        self->ogg_stream = oggreader_open(self->ogg_file);
    }

    /*read identification packet*/
    if ((ogg_result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        if ((vorbis_result =
             vorbis_read_identification_packet(self->packet,
                                               &(self->identification))) !=
            VORBIS_OK) {
            PyErr_SetString(vorbis_exception(vorbis_result),
                            vorbis_strerror(vorbis_result));
            goto error;
        }
    } else {
        PyErr_SetString(ogg_exception(ogg_result), ogg_strerror(ogg_result));
        goto error;
    }

    /*skip comments packet, but ensure it's positioned properly*/
    if ((ogg_result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        if (vorbis_read_common_header(self->packet) != 3) {
            PyErr_SetString(PyExc_ValueError,
                            "comment not second Ogg packet");
            goto error;
        }
    } else {
        PyErr_SetString(ogg_exception(ogg_result), ogg_strerror(ogg_result));
        goto error;
    }

    /*read setup header*/
    if ((ogg_result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        if ((vorbis_result = vorbis_read_setup_packet(self->packet)) !=
            VORBIS_OK) {
            PyErr_SetString(vorbis_exception(vorbis_result),
                            vorbis_strerror(vorbis_result));
            goto error;
        }
    } else {
        PyErr_SetString(ogg_exception(ogg_result), ogg_strerror(ogg_result));
        goto error;
    }

    return 0;

 error:
    return -1;
}

static PyObject*
VorbisDecoder_sample_rate(decoders_VorbisDecoder *self, void *closure) {
    return Py_BuildValue("i", self->identification.sample_rate);
}

static PyObject*
VorbisDecoder_bits_per_sample(decoders_VorbisDecoder *self, void *closure) {
    return Py_BuildValue("i", 16);
}

static PyObject*
VorbisDecoder_channels(decoders_VorbisDecoder *self, void *closure) {
    return Py_BuildValue("i", self->identification.channel_count);
}

static PyObject*
VorbisDecoder_channel_mask(decoders_VorbisDecoder *self, void *closure) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
VorbisDecoder_read(decoders_VorbisDecoder *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
VorbisDecoder_analyze_frame(decoders_VorbisDecoder *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
VorbisDecoder_close(decoders_VorbisDecoder *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

char*
vorbis_strerror(vorbis_status error) {
    switch (error) {
    case VORBIS_OK:
        return "no error";
    case VORBIS_PREMATURE_EOF:
        return "premature EOF reading packet";
    case VORBIS_ID_HEADER_NOT_1ST:
        return "identification header not first packet";
    case VORBIS_SETUP_NOT_3RD:
        return "setup header not third packet";
    case VORBIS_UNSUPPORTED_VERSION:
        return "unsupported Vorbis version";
    case VORBIS_INVALID_CHANNEL_COUNT:
        return "channel count must be greater than 0";
    case VORBIS_INVALID_SAMPLE_RATE:
        return "sample rate must be greater than 0";
    case VORBIS_INVALID_BLOCK_SIZE_0:
        return "invalid block size value (0)";
    case VORBIS_INVALID_BLOCK_SIZE_1:
        return "invalid block size value (1)";
    case VORBIS_INVALID_FRAMING_BIT:
        return "invalid framing bit";
    case VORBIS_INVALID_CODEBOOK_SYNC:
        return "invalid codebook sync";
    case VORBIS_UNSUPPORTED_CODEBOOK_LOOKUP_TYPE:
        return "unsupported codebook lookup type";
    case VORBIS_NOT_IMPLEMENTED:
        return "not yet implemented";
    }

    return "unknown error"; /*shouldn't get here*/
}

PyObject*
vorbis_exception(vorbis_status error) {
    switch (error) {
        /*most of the errors are ValueErrors*/
    case VORBIS_OK:
    case VORBIS_ID_HEADER_NOT_1ST:
    case VORBIS_SETUP_NOT_3RD:
    case VORBIS_UNSUPPORTED_VERSION:
    case VORBIS_INVALID_CHANNEL_COUNT:
    case VORBIS_INVALID_SAMPLE_RATE:
    case VORBIS_INVALID_BLOCK_SIZE_0:
    case VORBIS_INVALID_BLOCK_SIZE_1:
    case VORBIS_INVALID_FRAMING_BIT:
    case VORBIS_INVALID_CODEBOOK_SYNC:
    case VORBIS_UNSUPPORTED_CODEBOOK_LOOKUP_TYPE:
        return PyExc_ValueError;
    case VORBIS_NOT_IMPLEMENTED:
        return PyExc_NotImplementedError;
    case VORBIS_PREMATURE_EOF:
        return PyExc_IOError;
    }

    return PyExc_ValueError; /*shouldn't get here*/
}

static float
float32_unpack(Bitstream *bs) {
    int mantissa = bs->read(bs, 21);
    int exponent = bs->read(bs, 10);
    int sign = bs->read(bs, 1);

    return ldexpf(sign ? -mantissa : mantissa,
                  exponent - 788);
}

static int
lookup1_values(int codebook_entries, int codebook_dimensions) {
    int value = 0;
    int i;
    int j;

    do {
        value++;
        for (i = 0, j = value; i < codebook_dimensions - 1; i++)
            j *= value;
    } while (j <= codebook_entries);

    return value - 1;
}

int
vorbis_read_common_header(Bitstream *packet) {
    uint8_t vorbis[] = {0x76, 0x6F, 0x72, 0x62, 0x69, 0x73};
    int packet_type = packet->read(packet, 8);
    int i;

    for (i = 0; i < 6; i++) {
        if (packet->read(packet, 8) != vorbis[i])
            return -1;
    }

    return packet_type;
}

vorbis_status
vorbis_read_identification_packet(
                        Bitstream *packet,
                        struct vorbis_identification_header *identification) {
    if (!setjmp(*bs_try(packet))) {
        if (vorbis_read_common_header(packet) != 1) {
            bs_etry(packet);
            return VORBIS_ID_HEADER_NOT_1ST;
        }

        identification->vorbis_version = packet->read(packet, 32);
        if (identification->vorbis_version != 0) {
            bs_etry(packet);
            return VORBIS_UNSUPPORTED_VERSION;
        }

        identification->channel_count = packet->read(packet, 8);
        if (identification->channel_count < 1) {
            bs_etry(packet);
            return VORBIS_INVALID_CHANNEL_COUNT;
        }

        identification->sample_rate = packet->read(packet, 32);
        if (identification->sample_rate < 1) {
            bs_etry(packet);
            return VORBIS_INVALID_SAMPLE_RATE;
        }

        identification->bitrate_maximum = packet->read(packet, 32);
        identification->bitrate_nominal = packet->read(packet, 32);
        identification->bitrate_minimum = packet->read(packet, 32);
        identification->blocksize_0 = 1 << packet->read(packet, 4);
        if ((identification->blocksize_0 != 64) &&
            (identification->blocksize_0 != 128) &&
            (identification->blocksize_0 != 256) &&
            (identification->blocksize_0 != 512) &&
            (identification->blocksize_0 != 1024) &&
            (identification->blocksize_0 != 2048) &&
            (identification->blocksize_0 != 4096) &&
            (identification->blocksize_0 != 8192)) {
            bs_etry(packet);
            return VORBIS_INVALID_BLOCK_SIZE_0;
        }

        identification->blocksize_1 = 1 << packet->read(packet, 4);
        if ((identification->blocksize_1 != 64) &&
            (identification->blocksize_1 != 128) &&
            (identification->blocksize_1 != 256) &&
            (identification->blocksize_1 != 512) &&
            (identification->blocksize_1 != 1024) &&
            (identification->blocksize_1 != 2048) &&
            (identification->blocksize_1 != 4096) &&
            (identification->blocksize_1 != 8192)) {
            bs_etry(packet);
            return VORBIS_INVALID_BLOCK_SIZE_1;
        }

        if (identification->blocksize_0 > identification->blocksize_1) {
            bs_etry(packet);
            return VORBIS_INVALID_BLOCK_SIZE_1;
        }

        if (packet->read(packet, 1) != 1) {
            bs_etry(packet);
            return VORBIS_INVALID_FRAMING_BIT;
        }
    } else {
        bs_etry(packet);
        return VORBIS_PREMATURE_EOF;
    }

    bs_etry(packet);
    return VORBIS_OK;
}

vorbis_status
vorbis_read_setup_packet(Bitstream *packet) {
    vorbis_status result;

    if (!setjmp(*bs_try(packet))) {
        if (vorbis_read_common_header(packet) != 5) {
            bs_etry(packet);
            return VORBIS_SETUP_NOT_3RD;
        }

        /*read codebooks*/
        if ((result = vorbis_read_codebooks(packet)) != VORBIS_OK) {
            bs_etry(packet);
            return result;
        }

        /*read time domain transforms*/
        /*FIXME*/

        /*read floors*/
        /*FIXME*/

        /*read residues*/
        /*FIXME*/

        /*read mappings*/
        /*FIXME*/

        /*read modes*/
        /*FIXME*/

        /*read framing bit*/
        /*FIXME*/

    } else {
        bs_etry(packet);
        return VORBIS_PREMATURE_EOF;
    }

    bs_etry(packet);
    return VORBIS_OK;
}

vorbis_status
vorbis_read_codebooks(Bitstream *packet) {
    int codebook_count = packet->read(packet, 8) + 1;
    int codebook;
    uint32_t codebook_dimensions;
    uint32_t codebook_entries;
    uint32_t codebook_entry;
    int entry_length;
    int codebook_lookup_type;
    int codebook_value_bits;
    int codebook_lookup_values;
    int codebook_lookup_value;

    for (codebook = 0; codebook < codebook_count; codebook++) {
        if (packet->read(packet, 24) != 0x564342)
            return VORBIS_INVALID_CODEBOOK_SYNC;
        codebook_dimensions = packet->read(packet, 16);
        codebook_entries = packet->read(packet, 24);

        /*first, read all the codebook entry lengths*/
        if (packet->read(packet, 1)) {
            /*ordered flag set*/
            printf("ordered flag set\n");
            /*FIXME*/
            return VORBIS_NOT_IMPLEMENTED;
        } else {
            /*ordered flag not set*/
            if (packet->read(packet, 1)) {
                /*sparse flag set*/
                for (codebook_entry = 0;
                     codebook_entry < codebook_entries;
                     codebook_entry++) {
                    if (packet->read(packet, 1)) {
                        /*read entry from stream*/
                        entry_length = packet->read(packet, 5) + 1;
                    }
                    /*otherwise, skip entry*/
                }
            } else {
                /*parse flag not set*/
                for (codebook_entry = 0;
                     codebook_entry < codebook_entries;
                     codebook_entry++) {
                    entry_length = packet->read(packet, 5) + 1;
                    /*FIXME - store this somewhere*/
                }
            }
        }

        /*then, read the vector lookup table*/
        codebook_lookup_type = packet->read(packet, 4);
        if ((codebook_lookup_type == 1) ||
            (codebook_lookup_type == 2)) {
            float32_unpack(packet);  /*codebook minimum value*/
            float32_unpack(packet);  /*codebook delta value*/
            codebook_value_bits = packet->read(packet, 4) + 1;
            packet->read(packet, 1); /*codebook sequence p*/
            if (codebook_lookup_type == 1) {
                codebook_lookup_values = lookup1_values(codebook_entries,
                                                        codebook_dimensions);
            } else {
                codebook_lookup_values = (codebook_entries *
                                          codebook_dimensions);
            }
            for (codebook_lookup_value = 0;
                 codebook_lookup_value < codebook_lookup_values;
                 codebook_lookup_value++) {
                packet->read(packet, codebook_value_bits);
                /*FIXME - store this somewhere*/
            }
        } else if (codebook_lookup_type > 2)
            return VORBIS_UNSUPPORTED_CODEBOOK_LOOKUP_TYPE;
    }

    return VORBIS_OK;
}

/*codeword helper functions for transforming
  the list of frequencies into a proper Huffman lookup table*/
static struct vorbis_codeword*
codeword_new_leaf(int value, unsigned int length, unsigned int bits) {
    struct vorbis_codeword* leaf = malloc(sizeof(struct vorbis_codeword));
    leaf->is_leaf = 1;
    leaf->value = value;
    leaf->bits = bits;
    leaf->length = length;
    return leaf;
}

static struct vorbis_codeword*
codeword_new_tree(void) {
    struct vorbis_codeword* tree = malloc(sizeof(struct vorbis_codeword));
    tree->is_leaf = 0;
    tree->bit_0 = NULL;
    tree->bit_1 = NULL;
    return tree;
}

static void
codeword_free_tree(struct vorbis_codeword* tree) {
    if (tree == NULL) {
        return;
    } else if (tree->is_leaf) {
        free(tree);
    } else {
        codeword_free_tree(tree->bit_0);
        codeword_free_tree(tree->bit_1);
        free(tree);
    }
}

static unsigned int
codeword_total_leaf_nodes(struct vorbis_codeword* tree) {
    if (tree == NULL) {
        return 0;
    } else if (tree->is_leaf) {
        return 1;
    } else {
        return (codeword_total_leaf_nodes(tree->bit_0) +
                codeword_total_leaf_nodes(tree->bit_1));
    }
}

static struct vorbis_codeword*
codeword_add_length(struct vorbis_codeword* tree,
                    unsigned int current_depth,
                    unsigned int length,
                    unsigned int bits,
                    int value) {
    struct vorbis_codeword* new_leaf;

    if (current_depth == length) {
        if (tree != NULL)
            /*node already present, so return failure*/
            return NULL;
        else
            /*node not yet present, so add new node*/
            return codeword_new_leaf(value, length, bits);
    } else if (current_depth < length) {
        if (tree != NULL) {
            if (tree->is_leaf) {
                /*can't add leaf nodes to other leaves*/
                return NULL;
            } else {
                /*try bit 0 first*/
                new_leaf = codeword_add_length(tree->bit_0,
                                               current_depth + 1,
                                               length,
                                               bits << 1,
                                               value);
                if (new_leaf != NULL) {
                    tree->bit_0 = new_leaf;
                    return tree;
                }

                /*then try the 1 bit*/
                new_leaf = codeword_add_length(tree->bit_1,
                                               current_depth + 1,
                                               length,
                                               (bits << 1) | 1,
                                               value);
                if (new_leaf != NULL) {
                    tree->bit_1 = new_leaf;
                    return tree;
                }

                /*if neither works, return failure*/
                return NULL;
            }
        } else {
            /*tree not yet large enough, so add new non-leaf node*/
            tree = codeword_new_tree();
            tree->bit_0 = codeword_add_length(tree->bit_0,
                                              current_depth + 1,
                                              length,
                                              bits << 1,
                                              value);
            return tree;
        }
    } else {
        /*walked too far within tree, so return failure*/
        return NULL;
    }
}

static struct huffman_frequency*
codeword_tree_to_frequencies(struct vorbis_codeword* tree) {
    struct huffman_frequency* frequencies =
        malloc(sizeof(struct huffman_frequency) *
               (codeword_total_leaf_nodes(tree) + 1));
    int index = 0;

    codeword_tree_to_frequencies_(tree, frequencies, &index);
    frequencies[index].length = 0;
    return frequencies;
}

static void
codeword_tree_to_frequencies_(struct vorbis_codeword* tree,
                              struct huffman_frequency* frequencies,
                              int* index) {
    if (tree == NULL) {
        return;
    } else if (tree->is_leaf) {
        frequencies[*index].value = tree->value;
        frequencies[*index].bits = tree->bits;
        frequencies[*index].length = tree->length;
        *index += 1;
    } else {
        codeword_tree_to_frequencies_(tree->bit_0,
                                      frequencies,
                                      index);
        codeword_tree_to_frequencies_(tree->bit_1,
                                      frequencies,
                                      index);
    }
}
