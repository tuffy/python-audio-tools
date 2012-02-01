#include "shn.h"
#include "../pcmconv.h"

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
SHNDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds)
{
    decoders_SHNDecoder *self;

    self = (decoders_SHNDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

/*FIXME*/
int
SHNDecoder_init(decoders_SHNDecoder *self,
                PyObject *args, PyObject *kwds)
{
    char* filename;
    FILE* fp;

    self->filename = NULL;
    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    self->filename = strdup(filename);

    /*open the shn file*/
    if ((fp = fopen(filename, "rb")) == NULL) {
        self->bitstream = NULL;
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = br_open(fp, BS_BIG_ENDIAN);
    }

    /*read Shorten header for basic info*/
    if (!setjmp(*br_try(self->bitstream))) {
        uint8_t magic_number[4];
        unsigned version;

        self->bitstream->parse(self->bitstream, "4b 8u", magic_number, version);
        if (memcmp(magic_number, "ajkg", 4)) {
            PyErr_SetString(PyExc_IOError, "invalid magic number");
            br_etry(self->bitstream);
            return -1;
        }
        if (version != 2) {
            PyErr_SetString(PyExc_IOError, "invalid Shorten version");
            br_etry(self->bitstream);
            return -1;
        }

        self->header.file_type = read_long(self->bitstream);
        self->header.channels = read_long(self->bitstream);
        self->block_length = read_long(self->bitstream);
        self->header.max_LPC = read_long(self->bitstream);
        self->header.mean_count = read_long(self->bitstream);
        self->bitstream->skip_bytes(self->bitstream,
                                    read_long(self->bitstream));

        if ((1 <= self->header.file_type) && (self->header.file_type <= 2)) {
            self->bits_per_sample = 8;
            self->signed_samples = (self->header.file_type == 1);
        } else if ((3 <= self->header.file_type) &&
                   (self->header.file_type <= 6)) {
            self->bits_per_sample = 16;
            self->signed_samples = ((self->header.file_type == 3) ||
                                    (self->header.file_type == 5));
        } else {
            PyErr_SetString(PyExc_IOError, "unsupported Shorten file type");
            br_etry(self->bitstream);
            return -1;
        }

        /*process first instruction for wave/aiff header, if present*/
        if (process_header(self->bitstream,
                           &(self->sample_rate), &(self->channel_mask))) {
            br_etry(self->bitstream);
            return -1;
        }


        br_etry(self->bitstream);
        return 0;
    } else {
        /*read error in Shorten header*/
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading Shorten header");
        return -1;
    }
}

void
SHNDecoder_dealloc(decoders_SHNDecoder *self)
{
    if (self->bitstream != NULL) {
        self->bitstream->close(self->bitstream);
    }

    if (self->filename != NULL)
        free(self->filename);

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
SHNDecoder_sample_rate(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->sample_rate);
}

static PyObject*
SHNDecoder_bits_per_sample(decoders_SHNDecoder *self,
                           void *closure)
{
    return Py_BuildValue("I", self->bits_per_sample);
}

static PyObject*
SHNDecoder_channels(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->header.channels);
}

static PyObject*
SHNDecoder_channel_mask(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->channel_mask);
}

PyObject*
SHNDecoder_read(decoders_SHNDecoder* self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static unsigned
read_unsigned(BitstreamReader* bs, unsigned count)
{
    const unsigned MSB = bs->read_unary(bs, 1);
    const unsigned LSB = bs->read(bs, count);

    return (MSB << count) | LSB;
}

static int
read_signed(BitstreamReader* bs, unsigned count)
{
    /*1 additional sign bit*/
    const unsigned u = read_unsigned(bs, count + 1);
    if (u % 2)
        return -(u >> 1) - 1;
    else
        return u >> 1;
}

unsigned int
read_long(BitstreamReader* bs)
{
    return read_unsigned(bs, read_unsigned(bs, 2));
}

void
skip_unsigned(BitstreamReader* bs, unsigned int count)
{
    bs->skip_unary(bs, 1);
    bs->skip(bs, count);
}

void
skip_signed(BitstreamReader* bs, unsigned int count)
{
    bs->skip_unary(bs, 1);
    bs->skip(bs, count + 1);
}

static int
process_header(BitstreamReader* bs,
               unsigned* sample_rate, unsigned* channel_mask)
{
    unsigned command;

    bs->mark(bs);
    read_unsigned(bs, COMMAND_SIZE);
    if (command == FN_VERBATIM) {
        BitstreamReader* verbatim;
        unsigned verbatim_size;

        bs->unmark(bs);

        verbatim = read_verbatim(bs, &verbatim_size);

        verbatim->mark(verbatim);
        if (!read_wave_header(verbatim, verbatim_size,
                              sample_rate, channel_mask)) {
            verbatim->unmark(verbatim);
            verbatim->close(verbatim);
            return 0;
        } else {
            verbatim->rewind(verbatim);
        }

        if (!read_aiff_header(verbatim, verbatim_size,
                              sample_rate, channel_mask)) {
            verbatim->unmark(verbatim);
            verbatim->close(verbatim);
            return 0;
        } else {
            verbatim->rewind(verbatim);
        }

        /*neither wave header or aiff header found,
          so use dummy values again*/
        verbatim->close(verbatim);
        verbatim->unmark(verbatim);
        *sample_rate = 44100;
        *channel_mask = 0;
        return 0;
    } else {
        /*VERBATIM isn't the first command
          so rewind and set some dummy values*/
        bs->rewind(bs);
        bs->unmark(bs);
        *sample_rate = 44100;
        *channel_mask = 0;
        return 0;
    }
}

static BitstreamReader*
read_verbatim(BitstreamReader* bs, unsigned* verbatim_size)
{
    BitstreamReader* verbatim = br_substream_new(BS_BIG_ENDIAN);
    if (!setjmp(*br_try(bs))) {
        *verbatim_size = read_unsigned(bs, VERBATIM_CHUNK_SIZE);
        unsigned i;
        for (i = 0; i < *verbatim_size; i++) {
            const unsigned byte = read_unsigned(bs, VERBATIM_BYTE_SIZE) & 0xFF;
            buf_putc((int)byte, verbatim->input.substream);
        }
        br_etry(bs);
        return verbatim;
    } else {
        /*I/O error reading from main bitstream*/
        verbatim->close(verbatim);
        br_etry(bs);
        br_abort(bs);
        return NULL; /*shouldn't get here*/
    }
}

int
read_wave_header(BitstreamReader* bs, unsigned verbatim_size,
                 unsigned* sample_rate, unsigned* channel_mask)
{
    if (!setjmp(*br_try(bs))) {
        uint8_t RIFF[4];
        unsigned SIZE;
        uint8_t WAVE[4];

        bs->set_endianness(bs, BS_LITTLE_ENDIAN);
        bs->parse(bs, "4b 32u 4b", RIFF, &SIZE, WAVE);

        if (memcmp(RIFF, "RIFF", 4) || memcmp(WAVE, "WAVE", 4)) {
            br_etry(bs);
            return 1;
        } else {
            verbatim_size -= bs_format_byte_size("4b 32u 4b");
        }

        while (verbatim_size > 0) {
            uint8_t chunk_id[4];
            unsigned chunk_size;
            bs->parse(bs, "4b 32u", chunk_id, &chunk_size);
            verbatim_size -= bs_format_byte_size("4b 32u");
            if (!memcmp(chunk_id, "fmt ", 4)) {
                /*parse fmt chunk*/
                unsigned compression;
                unsigned channels;
                unsigned bytes_per_second;
                unsigned block_align;
                unsigned bits_per_sample;

                bs->parse(bs, "16u 16u 32u 32u 16u 16u",
                          &compression,
                          &channels,
                          sample_rate,
                          &bytes_per_second,
                          &block_align,
                          &bits_per_sample);
                if (compression == 1) {
                    /*if we have a multi-channel WAVE file
                      that's not WAVEFORMATEXTENSIBLE,
                      assume the channels follow
                      SMPTE/ITU-R recommendations
                      and hope for the best*/
                    switch (channels) {
                    case 1:
                        *channel_mask = 0x4;
                        break;
                    case 2:
                        *channel_mask = 0x3;
                        break;
                    case 3:
                        *channel_mask = 0x7;
                        break;
                    case 4:
                        *channel_mask = 0x33;
                        break;
                    case 5:
                        *channel_mask = 0x37;
                        break;
                    case 6:
                        *channel_mask = 0x3F;
                        break;
                    default:
                        *channel_mask = 0;
                        break;
                    }
                    br_etry(bs);
                    return 0;
                } else if (compression == 0xFFFE) {
                    unsigned cb_size;
                    unsigned valid_bits_per_sample;
                    uint8_t sub_format[16];
                    bs->parse(bs, "16u 16u 32u 16b",
                              &cb_size,
                              &valid_bits_per_sample,
                              channel_mask,
                              sub_format);
                    if (!memcmp(sub_format,
                                "\x01\x00\x00\x00\x00\x00\x10\x00"
                                "\x80\x00\x00\xaa\x00\x38\x9b\x71", 16)) {
                        br_etry(bs);
                        return 0;
                    } else {
                        /*invalid sub format*/
                        br_etry(bs);
                        return 1;
                    }
                } else {
                    /*unsupported wave compression*/
                    br_etry(bs);
                    return 1;
                }
            } else {
                if (chunk_size % 2) {
                    /*handle odd-sized chunks*/
                    bs->skip_bytes(bs, chunk_size + 1);
                    verbatim_size -= (chunk_size + 1);
                } else {
                    bs->skip_bytes(bs, chunk_size);
                    verbatim_size -= chunk_size;
                }
            }
        }

        /*no fmt chunk found in wave header*/
        br_etry(bs);
        return 1;
    } else {
        /*I/O error bouncing through wave chunks*/
        br_etry(bs);
        return 1;
    }
}

int
read_aiff_header(BitstreamReader* bs, unsigned verbatim_size,
                 unsigned* sample_rate, unsigned* channel_mask)
{
    if (!setjmp(*br_try(bs))) {
        uint8_t FORM[4];
        unsigned SIZE;
        uint8_t AIFF[4];

        bs->set_endianness(bs, BS_BIG_ENDIAN);
        bs->parse(bs, "4b 32u 4b", FORM, &SIZE, AIFF);

        if (memcmp(FORM, "FORM", 4) || memcmp(AIFF, "AIFF", 4)) {
            br_etry(bs);
            return 1;
        } else {
            verbatim_size -= bs_format_byte_size("4b 32u 4b");
        }

        while (verbatim_size > 0) {
            uint8_t chunk_id[4];
            unsigned chunk_size;
            bs->parse(bs, "4b 32u", chunk_id, &chunk_size);

            verbatim_size -= bs_format_byte_size("4b 32u");
            if (!memcmp(chunk_id, "COMM", 4)) {
                /*parse COMM chunk*/

                unsigned channels;
                unsigned total_sample_frames;
                unsigned bits_per_sample;

                bs->parse(bs, "16u 32u 16u",
                          &channels,
                          &total_sample_frames,
                          &bits_per_sample);

                *sample_rate = read_ieee_extended(bs);

                switch (channels) {
                case 1:
                    *channel_mask = 0x4;
                    break;
                case 2:
                    *channel_mask = 0x3;
                    break;
                case 3:
                    *channel_mask = 0x7;
                    break;
                case 4:
                    *channel_mask = 0x33;
                    break;
                case 5:
                    /*5 channels is undefined*/
                    *channel_mask = 0;
                    break;
                case 6:
                    *channel_mask = 0x707;
                    break;
                default:
                    *channel_mask = 0;
                    break;
                }

                br_etry(bs);
                return 0;
            } else {
                if (chunk_size % 2) {
                    /*handle odd-sized chunks*/
                    bs->skip_bytes(bs, chunk_size + 1);
                    verbatim_size -= (chunk_size + 1);
                } else {
                    bs->skip_bytes(bs, chunk_size);
                    verbatim_size -= chunk_size;
                }
            }
        }

        /*no COMM chunk found in aiff header*/
        br_etry(bs);
        return 1;
    } else {
        /*I/O error bouncing through aiff chunks*/
        br_etry(bs);
        return 1;
    }
}

int
read_ieee_extended(BitstreamReader* bs)
{
    unsigned sign;
    unsigned exponent;
    uint64_t mantissa;

    bs->parse(bs, "1u 15u 64U", &sign, &exponent, &mantissa);
    if ((exponent == 0) && (mantissa == 0)) {
        return 0;
    } else if (exponent == 0x7FFF) {
        return INT_MAX;
    } else {
        const int f = (int)((long double)mantissa *
                            powl(2.0, (long double )exponent - 16383 - 63));
        if (sign)
            return -f;
        else
            return f;
    }
}
