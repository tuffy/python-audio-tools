#include "oggflac.h"

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
OggFlacDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_OggFlacDecoder *self;

    self = (decoders_OggFlacDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
OggFlacDecoder_dealloc(decoders_OggFlacDecoder *self) {
    self->packet->close(self->packet);
    if (self->ogg_stream != NULL)
        oggreader_close(self->ogg_stream);
    if (self->ogg_file != NULL)
        fclose(self->ogg_file);

    self->ob_type->tp_free((PyObject*)self);
}

int
OggFlacDecoder_init(decoders_OggFlacDecoder *self,
                    PyObject *args, PyObject *kwds) {
    char* filename;
    ogg_status result;
    uint16_t header_packets;

    self->ogg_stream = NULL;
    self->ogg_file = NULL;
    self->packet = bs_substream_new(BS_BIG_ENDIAN);

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;
    self->ogg_file = fopen(filename, "rb");
    if (self->ogg_file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->ogg_stream = oggreader_open(self->ogg_file);
    }

    /*the first packet should be the FLAC's STREAMINFO*/
    if ((result = oggreader_next_packet(self->ogg_stream,
                                        self->packet)) == OGG_OK) {
        if (oggflac_read_streaminfo(self->packet,
                                    &(self->streaminfo),
                                    &header_packets) != OK)
            return -1;
    } else {
        PyErr_SetString(ogg_exception(result), ogg_strerror(result));
        return -1;
    }

    /*skip subsequent header packets*/
    for (; header_packets > 0; header_packets--) {
        if ((result = oggreader_next_packet(self->ogg_stream,
                                            self->packet)) != OGG_OK) {
            PyErr_SetString(ogg_exception(result), ogg_strerror(result));
            return -1;
        }
    }

    return 0;
}

static PyObject*
OggFlacDecoder_sample_rate(decoders_OggFlacDecoder *self, void *closure) {
    return Py_BuildValue("i", self->streaminfo.sample_rate);
}

static PyObject*
OggFlacDecoder_bits_per_sample(decoders_OggFlacDecoder *self, void *closure) {
    return Py_BuildValue("i", self->streaminfo.bits_per_sample);
}

static PyObject*
OggFlacDecoder_channels(decoders_OggFlacDecoder *self, void *closure) {
    return Py_BuildValue("i", self->streaminfo.channels);
}

static PyObject*
OggFlacDecoder_channel_mask(decoders_OggFlacDecoder *self, void *closure) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
OggFlacDecoder_read(decoders_OggFlacDecoder *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
OggFlacDecoder_analyze_frame(decoders_OggFlacDecoder *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
OggFlacDecoder_close(decoders_OggFlacDecoder *self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

status
oggflac_read_streaminfo(Bitstream *packet,
                        struct flac_STREAMINFO *streaminfo,
                        uint16_t *header_packets) {
    int i;

    if (!setjmp(*bs_try(packet))) {
        if (packet->read(packet, 8) != 0x7F) {
            PyErr_SetString(PyExc_ValueError, "invalid packet byte");
            goto error;
        }
        if (packet->read_64(packet, 32) != 0x464C4143) {
            PyErr_SetString(PyExc_ValueError, "invalid Ogg signature");
            goto error;
        }
        if (packet->read(packet, 8) != 1) {
            PyErr_SetString(PyExc_ValueError, "invalid major version");
            goto error;
        }
        if (packet->read(packet, 8) != 0) {
            PyErr_SetString(PyExc_ValueError, "invalid minor version");
            goto error;
        }
        *header_packets = packet->read(packet, 16);
        if (packet->read_64(packet, 32) != 0x664C6143) {
            PyErr_SetString(PyExc_ValueError, "invalid fLaC signature");
            goto error;
        }
        packet->read(packet, 1); /*last block*/
        if (packet->read(packet, 7) != 0) {
            PyErr_SetString(PyExc_ValueError, "invalid block type");
            goto error;
        }
        packet->read(packet, 24); /*block length*/

        streaminfo->minimum_block_size = packet->read(packet, 16);
        streaminfo->maximum_block_size = packet->read(packet, 16);
        streaminfo->minimum_frame_size = packet->read(packet, 24);
        streaminfo->maximum_frame_size = packet->read(packet, 24);
        streaminfo->sample_rate = packet->read(packet, 20);
        streaminfo->channels = packet->read(packet, 3) + 1;
        streaminfo->bits_per_sample = packet->read(packet, 5) + 1;
        streaminfo->total_samples = packet->read_64(packet, 36);
        for (i = 0; i < 16; i++) {
            streaminfo->md5sum[i] = packet->read(packet, 8);
        }
    } else {
        PyErr_SetString(PyExc_IOError,
                        "EOF while reading STREAMINFO block");
        goto error;
    }

    bs_etry(packet);
    return OK;
 error:
    bs_etry(packet);
    return ERROR;
}
