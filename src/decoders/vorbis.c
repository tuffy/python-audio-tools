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
    ogg_status result;

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
    if ((result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        if (!vorbis_read_identification_packet(self->packet,
                                               &(self->identification)))
            goto error;
    } else {
        PyErr_SetString(ogg_exception(result), ogg_strerror(result));
        goto error;
    }

    /*skip comments packet, but ensure it's positioned properly*/
    if ((result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        if (vorbis_read_common_header(self->packet) != 3) {
            PyErr_SetString(PyExc_ValueError,
                            "comment not second Ogg packet");
            goto error;
        }
    } else {
        PyErr_SetString(ogg_exception(result), ogg_strerror(result));
        goto error;
    }

    /*read setup header*/
    if ((result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        /*FIXME - read setup here*/
    } else {
        PyErr_SetString(ogg_exception(result), ogg_strerror(result));
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

int
vorbis_read_identification_packet(
                        Bitstream *packet,
                        struct vorbis_identification_header *identification) {
    if (!setjmp(*bs_try(packet))) {
        if (vorbis_read_common_header(packet) != 1) {
            PyErr_SetString(PyExc_ValueError,
                            "identification header not first packet");
            goto error;
        }

        identification->vorbis_version = packet->read(packet, 32);
        if (identification->vorbis_version != 0) {
            PyErr_SetString(PyExc_ValueError,
                            "unsupported Vorbis version");
            goto error;
        }

        identification->channel_count = packet->read(packet, 8);
        if (identification->channel_count < 1) {
            PyErr_SetString(PyExc_ValueError,
                            "channel count must be greater than 0");
            goto error;
        }

        identification->sample_rate = packet->read(packet, 32);
        if (identification->sample_rate < 1) {
            PyErr_SetString(PyExc_ValueError,
                            "sample rate must be greater than 0");
            goto error;
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
            PyErr_SetString(PyExc_ValueError, "invalid block size value (0)");
            goto error;
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
            PyErr_SetString(PyExc_ValueError, "invalid block size value (1)");
            goto error;
        }

        if (identification->blocksize_0 > identification->blocksize_1) {
            PyErr_SetString(PyExc_ValueError,
                            "block size (0) > block size (1)");
            goto error;
        }

        if (packet->read(packet, 1) != 1) {
            PyErr_SetString(PyExc_ValueError, "invalid framing bit");
            goto error;
        }
    } else {
        PyErr_SetString(PyExc_IOError,
                        "EOF while reading identification packet");
        goto error;
    }

    bs_etry(packet);
    return 1;
 error:
    bs_etry(packet);
    return 0;
}
