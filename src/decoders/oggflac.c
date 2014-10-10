#ifdef STANDALONE
#include <string.h>
#include <errno.h>
#endif
#include "oggflac.h"
#include "../common/flac_crc.h"
#include "../pcmconv.h"

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

#ifndef STANDALONE
PyObject*
OggFlacDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_OggFlacDecoder *self;

    self = (decoders_OggFlacDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
OggFlacDecoder_dealloc(decoders_OggFlacDecoder *self) {
    self->subframe_data->del(self->subframe_data);
    self->residuals->del(self->residuals);
    self->qlp_coeffs->del(self->qlp_coeffs);
    self->framelist_data->del(self->framelist_data);
    Py_XDECREF(self->audiotools_pcm);

    if (self->ogg_packets != NULL)
        oggiterator_close(self->ogg_packets);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
OggFlacDecoder_init(decoders_OggFlacDecoder *self,
                    PyObject *args, PyObject *kwds) {
    char* filename;
    ogg_status result;
    BitstreamReader *header_packet;
    uint16_t header_packets;

    self->ogg_packets = NULL;
    self->ogg_file = NULL;
    self->subframe_data = aa_int_new();
    self->residuals = a_int_new();
    self->qlp_coeffs = a_int_new();
    self->framelist_data = a_int_new();
    self->audiotools_pcm = NULL;
    self->stream_finalized = 0;

    if (!PyArg_ParseTuple(args, "si", &filename, &(self->channel_mask)))
        return -1;

    if (self->channel_mask < 0) {
        PyErr_SetString(PyExc_ValueError, "channel_mask must be >= 0");
        return -1;
    }

    self->ogg_file = fopen(filename, "rb");
    if (self->ogg_file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->ogg_packets = oggiterator_open(self->ogg_file);
    }

    /*the first packet should be the FLAC's STREAMINFO*/
    if ((header_packet = oggiterator_next_packet(self->ogg_packets,
                                                 BS_BIG_ENDIAN,
                                                 &result)) != NULL) {
        const int streaminfo_ok = oggflac_read_streaminfo(header_packet,
                                                          &(self->streaminfo),
                                                          &header_packets);
        header_packet->close(header_packet);
        if (!streaminfo_ok) {
            return -1;
        }
    } else {
        PyErr_SetString(ogg_exception(result), ogg_strerror(result));
        return -1;
    }

    /*skip subsequent header packets*/
    for (; header_packets > 0; header_packets--) {
        if ((header_packet = oggiterator_next_packet(self->ogg_packets,
                                                     BS_BIG_ENDIAN,
                                                     &result)) != NULL) {
            header_packet->close(header_packet);
        } else {
            PyErr_SetString(ogg_exception(result), ogg_strerror(result));
            return -1;
        }
    }

    /*initialize the output MD5 sum*/
    audiotools__MD5Init(&(self->md5));

    /*setup a framelist generator function*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    /*mark stream as not closed and ready for reading*/
    self->closed = 0;

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
    return Py_BuildValue("i", self->channel_mask);
}

static PyObject*
OggFlacDecoder_read(decoders_OggFlacDecoder *self, PyObject *args) {
    BitstreamReader *packet;
    ogg_status ogg_status;
    flac_status flac_status;
    struct flac_frame_header frame_header;
    int channel;
    PyObject *framelist;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    self->subframe_data->reset(self->subframe_data);

    /*if all samples have been read, return an empty FrameList*/
    if (self->stream_finalized) {
        return empty_FrameList(self->audiotools_pcm,
                               self->streaminfo.channels,
                               self->streaminfo.bits_per_sample);
    }

    packet = oggiterator_next_packet(self->ogg_packets,
                                     BS_BIG_ENDIAN,
                                     &ogg_status);

    if (ogg_status == OGG_OK) {
        /*decode the next FrameList from the stream*/

        uint16_t crc16 = 0;
        packet->add_callback(packet, (bs_callback_f)flac_crc16, &crc16);

        if (!setjmp(*br_try(packet))) {
            /*read frame header*/
            if ((flac_status =
                 flacdec_read_frame_header(packet,
                                           &(self->streaminfo),
                                           &frame_header)) != OK) {
                br_etry(packet);
                packet->close(packet);
                PyErr_SetString(PyExc_ValueError,
                                FlacDecoder_strerror(flac_status));
                return NULL;
            }

            /*read 1 subframe per channel*/
            for (channel = 0; channel < frame_header.channel_count; channel++)
                if ((flac_status = flacdec_read_subframe(
                        packet,
                        self->qlp_coeffs,
                        self->residuals,
                        frame_header.block_size,
                        flacdec_subframe_bits_per_sample(&frame_header,
                                                         channel),
                        self->subframe_data->append(self->subframe_data))) !=
                    OK) {
                    br_etry(packet);
                    packet->close(packet);
                    PyErr_SetString(PyExc_ValueError,
                                    FlacDecoder_strerror(flac_status));
                    return NULL;
                }


            /*handle difference channels, if any*/
            flacdec_decorrelate_channels(frame_header.channel_assignment,
                                         self->subframe_data,
                                         self->framelist_data);

            /*check CRC-16*/
            packet->byte_align(packet);
            packet->read(packet, 16);
            if (crc16 != 0) {
                PyErr_SetString(PyExc_ValueError, "invalid checksum in frame");
                return NULL;
            }

            br_etry(packet);

            framelist = a_int_to_FrameList(self->audiotools_pcm,
                                           self->framelist_data,
                                           frame_header.channel_count,
                                           frame_header.bits_per_sample);

            if (framelist != NULL) {
                /*update MD5 sum*/
                if (OggFlacDecoder_update_md5sum(self, framelist) == 1)
                    /*return pcm.FrameList Python object*/
                    return framelist;
                else {
                    Py_DECREF(framelist);
                    return NULL;
                }
            } else {
                return NULL;
            }
        } else {
            /*read error decoding FLAC frame*/
            PyErr_SetString(PyExc_IOError, "I/O error decoding FLAC frame");
            br_etry(packet);
            packet->close(packet);
            return NULL;
        }
    } else if (ogg_status == OGG_STREAM_FINISHED) {
        /*Ogg stream is finished so verify stream's MD5 sum
          then return an empty FrameList if it matches correctly*/

        if (OggFlacDecoder_verify_okay(self)) {
            self->stream_finalized = 1;
            return empty_FrameList(self->audiotools_pcm,
                                   self->streaminfo.channels,
                                   self->streaminfo.bits_per_sample);
        } else {
            PyErr_SetString(PyExc_ValueError,
                            "MD5 mismatch at end of stream");
            return NULL;
        }
    } else {
        /*error reading the next Ogg packet,
          so raise the appropriate exception*/
        PyErr_SetString(ogg_exception(ogg_status), ogg_strerror(ogg_status));
        return NULL;
    }
}

static PyObject*
OggFlacDecoder_close(decoders_OggFlacDecoder *self, PyObject *args)
{
    /*mark stream as closed so more calls to read() generate ValueErrors*/
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
OggFlacDecoder_enter(decoders_OggFlacDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
OggFlacDecoder_exit(decoders_OggFlacDecoder* self, PyObject *args)
{
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

int
OggFlacDecoder_update_md5sum(decoders_OggFlacDecoder *self,
                             PyObject *framelist) {
    PyObject *string = PyObject_CallMethod(framelist,
                                           "to_bytes","ii",
                                           0,
                                           1);
    char *string_buffer;
    Py_ssize_t length;

    if (string != NULL) {
        if (PyBytes_AsStringAndSize(string, &string_buffer, &length) == 0) {
            audiotools__MD5Update(&(self->md5),
                                  (unsigned char *)string_buffer,
                                  length);
            Py_DECREF(string);
            return 1;
        } else {
            Py_DECREF(string);
            return 0;
        }
    } else {
        return 0;
    }
}

int
OggFlacDecoder_verify_okay(decoders_OggFlacDecoder *self) {
    unsigned char stream_md5sum[16];
    const static unsigned char blank_md5sum[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                                   0, 0, 0, 0, 0, 0, 0, 0};

    audiotools__MD5Final(stream_md5sum, &(self->md5));

    return ((memcmp(self->streaminfo.md5sum, blank_md5sum, 16) == 0) ||
            (memcmp(stream_md5sum, self->streaminfo.md5sum, 16) == 0));
}
#endif

int
oggflac_read_streaminfo(BitstreamReader *packet,
                        struct flac_STREAMINFO *streaminfo,
                        uint16_t *header_packets) {
    int i;

    if (!setjmp(*br_try(packet))) {
        if (packet->read(packet, 8) != 0x7F) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "invalid packet byte");
#else
            fprintf(stderr, "invalid packet byte\n");
#endif
            goto error;
        }
        if (packet->read_64(packet, 32) != 0x464C4143) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "invalid Ogg signature");
#else
            fprintf(stderr, "invalid Ogg signature\n");
#endif
            goto error;
        }
        if (packet->read(packet, 8) != 1) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "invalid major version");
#else
            fprintf(stderr, "invalid major version\n");
#endif
            goto error;
        }
        if (packet->read(packet, 8) != 0) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "invalid minor version");
#else
            fprintf(stderr, "invalid minor version\n");
#endif
            goto error;
        }
        *header_packets = packet->read(packet, 16);
        if (packet->read_64(packet, 32) != 0x664C6143) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "invalid fLaC signature");
#else
            fprintf(stderr, "invalid fLaC signature\n");
#endif
            goto error;
        }
        packet->read(packet, 1); /*last block*/
        if (packet->read(packet, 7) != 0) {
#ifndef STANDALONE
            PyErr_SetString(PyExc_ValueError, "invalid block type");
#else
            fprintf(stderr, "invalid block type\n");
#endif
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
#ifndef STANDALONE
        PyErr_SetString(PyExc_IOError, "EOF while reading STREAMINFO block");
#else
        fprintf(stderr, "EOF while reading STREAMINFO block\n");
#endif
        goto error;
    }

    br_etry(packet);
    return 1;
error:
    br_etry(packet);
    return 0;
}

#ifdef STANDALONE
int main(int argc, char* argv[]) {
    FILE* ogg_file;
    OggPacketIterator* ogg_packets = NULL;
    BitstreamReader* packet;
    struct flac_STREAMINFO streaminfo;
    uint16_t header_packets;
    a_int* residuals = NULL;
    a_int* qlp_coeffs = NULL;
    aa_int* subframe_data = NULL;
    a_int* framelist_data = NULL;
    ogg_status result;
    uint16_t crc16 = 0;

    FrameList_int_to_char_converter converter;
    unsigned pcm_size;
    unsigned output_data_size = 1;
    uint8_t* output_data = NULL;

    audiotools__MD5Context md5;
    unsigned char stream_md5sum[16];
    const static unsigned char blank_md5sum[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                                   0, 0, 0, 0, 0, 0, 0, 0};

    if (argc < 2) {
        fprintf(stderr, "*** Usage: %s <file.oga>\n", argv[0]);
        return 1;
    }

    /*open input file for reading*/
    if ((ogg_file = fopen(argv[1], "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", argv[1], strerror(errno));
        return 1;
    } else {
        /*open bitstream and setup temporary arrays/buffers*/
        ogg_packets = oggiterator_open(ogg_file);
        subframe_data = aa_int_new();
        residuals = a_int_new();
        qlp_coeffs = a_int_new();
        framelist_data = a_int_new();
        output_data = malloc(output_data_size);
    }

    /*the first packet should be the FLAC's STREAMINFO*/
    if ((packet = oggiterator_next_packet(ogg_packets,
                                          BS_BIG_ENDIAN,
                                          &result)) != NULL) {
        int streaminfo_ok = oggflac_read_streaminfo(packet,
                                                          &streaminfo,
                                                          &header_packets);

        packet->close(packet);

        if (streaminfo_ok) {
            converter = FrameList_get_int_to_char_converter(
                streaminfo.bits_per_sample, 0, 1);
        } else {
            fprintf(stderr, "*** Error: STREAMINFO parsing error\n");
            goto error;
        }
    } else {
        fprintf(stderr, "*** Error: %s\n", ogg_strerror(result));
        goto error;
    }

    /*skip subsequent header packets*/
    for (; header_packets > 0; header_packets--) {
        if ((packet = oggiterator_next_packet(ogg_packets,
                                              BS_BIG_ENDIAN,
                                              &result)) != NULL) {
            packet->close(packet);
        } else {
            fprintf(stderr, "*** Error: %s\n", ogg_strerror(result));
            goto error;
        }
    }

    /*initialize the output MD5 sum*/
    audiotools__MD5Init(&md5);


    /*decode the next FrameList from the stream*/
    packet = oggiterator_next_packet(ogg_packets, BS_BIG_ENDIAN, &result);
    /*add callback for CRC16 calculation*/
    packet->add_callback(packet, (bs_callback_f)flac_crc16, &crc16);

    while (result != OGG_STREAM_FINISHED) {
        if (result == OGG_OK) {
            flac_status flac_status;
            struct flac_frame_header frame_header;
            unsigned channel;

            subframe_data->reset(subframe_data);

            if (!setjmp(*br_try(packet))) {
                /*read frame header*/
                if ((flac_status =
                     flacdec_read_frame_header(packet,
                                               &streaminfo,
                                               &frame_header)) != OK) {
                    fprintf(stderr, "*** Error: %s\n",
                            FlacDecoder_strerror(flac_status));
                    br_etry(packet);
                    goto error;
                }

                /*read 1 subframe per channel*/
                for (channel = 0;
                     channel < frame_header.channel_count;
                     channel++)
                    if ((flac_status = flacdec_read_subframe(
                        packet,
                        qlp_coeffs,
                        residuals,
                        frame_header.block_size,
                        flacdec_subframe_bits_per_sample(&frame_header,
                                                         channel),
                        subframe_data->append(subframe_data))) != OK) {
                        fprintf(stderr, "*** Error: %s\n",
                                FlacDecoder_strerror(flac_status));
                        br_etry(packet);
                        goto error;
                    }

                br_etry(packet);
            } else {
                br_etry(packet);
                fprintf(stderr, "*** I/O Error reading FLAC frame\n");
                goto error;
            }

            /*handle difference channels, if any*/
            flacdec_decorrelate_channels(frame_header.channel_assignment,
                                         subframe_data,
                                         framelist_data);

            /*check CRC-16*/
            packet->byte_align(packet);
            packet->read(packet, 16);
            if (crc16 != 0) {
                fprintf(stderr, "*** Error: invalid checksum in frame\n");
                goto error;
            }

            /*turn FrameList into string of output*/
            pcm_size = (streaminfo.bits_per_sample / 8) * framelist_data->len;
            if (pcm_size > output_data_size) {
                output_data_size = pcm_size;
                output_data = realloc(output_data, output_data_size);
            }
            FrameList_samples_to_char(output_data,
                                      framelist_data->_,
                                      converter,
                                      framelist_data->len,
                                      streaminfo.bits_per_sample);

            /*update MD5 sum*/
            audiotools__MD5Update(&md5, output_data, pcm_size);

            /*output string to stdout*/
            fwrite(output_data, sizeof(unsigned char), pcm_size, stdout);

            packet->close(packet);
            packet = oggiterator_next_packet(ogg_packets,
                                             BS_BIG_ENDIAN,
                                             &result);
        } else {
            /*some error reading Ogg stream*/
            fprintf(stderr, "*** Error: %s\n", ogg_strerror(result));
            goto error;
        }
    }

    /*Ogg stream is finished so verify stream's MD5 sum*/
    audiotools__MD5Final(stream_md5sum, &md5);

    if (!((memcmp(streaminfo.md5sum, blank_md5sum, 16) == 0) ||
          (memcmp(stream_md5sum, streaminfo.md5sum, 16) == 0))) {
        fprintf(stderr, "*** MD5 mismatch at end of stream\n");
        goto error;
    }

    /*close streams, temporary buffers*/
    oggiterator_close(ogg_packets);
    subframe_data->del(subframe_data);
    residuals->del(residuals);
    qlp_coeffs->del(qlp_coeffs);
    framelist_data->del(framelist_data);
    free(output_data);

    return 0;

error:
    oggiterator_close(ogg_packets);
    subframe_data->del(subframe_data);
    residuals->del(residuals);
    qlp_coeffs->del(qlp_coeffs);
    framelist_data->del(framelist_data);
    free(output_data);

    return 1;
}
#endif
