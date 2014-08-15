#include "shn.h"
#include "../pcmconv.h"
#include <string.h>
#include <math.h>

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
SHNDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds)
{
    decoders_SHNDecoder *self;

    self = (decoders_SHNDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
SHNDecoder_init(decoders_SHNDecoder *self,
                PyObject *args, PyObject *kwds)
{
    self->file = NULL;
    self->bitstream = NULL;
    self->stream_finished = 0;

    self->means = aa_int_new();
    self->previous_samples = aa_int_new();

    /*setup temporary buffers*/
    self->samples = aa_int_new();
    self->unshifted = aa_int_new();
    self->pcm_header = a_int_new();
    self->pcm_footer = a_int_new();

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    if (!PyArg_ParseTuple(args, "O", &(self->file))) {
        return -1;
    } else {
        Py_INCREF(self->file);
    }

    /*open the shn file*/
    if (PyFile_Check(self->file)) {
        self->bitstream = br_open(PyFile_AsFile(self->file), BS_BIG_ENDIAN);
    } else {
        self->bitstream = br_open_external(
            self->file,
            BS_BIG_ENDIAN,
            4096,
            (ext_read_f)br_read_python,
            (ext_close_f)bs_close_python,
            (ext_free_f)bs_free_python_nodecref);
    }

    /*read Shorten header for basic info*/
    switch (read_shn_header(self, self->bitstream)) {
    case INVALID_MAGIC_NUMBER:
        PyErr_SetString(PyExc_ValueError, "invalid magic number");
        return -1;
    case INVALID_SHORTEN_VERSION:
        PyErr_SetString(PyExc_ValueError, "invalid Shorten version");
        return -1;
    case UNSUPPORTED_FILE_TYPE:
        PyErr_SetString(PyExc_ValueError, "unsupported Shorten file type");
        return -1;
    case IOERROR:
        PyErr_SetString(PyExc_IOError, "I/O error reading Shorten header");
        return -1;
    default:
        /*mark stream as not closed and ready for reading*/
        self->closed = 0;

        return 0;
    }
}

void
SHNDecoder_dealloc(decoders_SHNDecoder *self)
{
    Py_XDECREF(self->file);
    self->means->del(self->means);
    self->previous_samples->del(self->previous_samples);
    self->samples->del(self->samples);
    self->unshifted->del(self->unshifted);
    self->pcm_header->del(self->pcm_header);
    self->pcm_footer->del(self->pcm_footer);

    Py_XDECREF(self->audiotools_pcm);

    if (self->bitstream != NULL) {
        self->bitstream->free(self->bitstream);
    }

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args)
{
    /*mark stream as closed so more calls to read() generate ValueErrors*/
    self->closed = 1;

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
    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    if (self->stream_finished) {
        return empty_FrameList(self->audiotools_pcm,
                               self->header.channels,
                               self->bits_per_sample);
    }

    self->unshifted->reset(self->unshifted);

    switch (read_framelist(self, self->unshifted)) {
    case OK:
        return aa_int_to_FrameList(self->audiotools_pcm,
                                   self->unshifted,
                                   self->bits_per_sample);
    case END_OF_STREAM:
        return empty_FrameList(self->audiotools_pcm,
                               self->header.channels,
                               self->bits_per_sample);
    case UNKNOWN_COMMAND:
        PyErr_SetString(PyExc_ValueError,
                        "unknown command in Shorten stream");
        return NULL;
    case IOERROR:
        PyErr_SetString(PyExc_IOError, "I/O error reading Shorten file");
        return NULL;
    default:
        /*shouldn't get here*/
        PyErr_SetString(PyExc_ValueError,
                        "unknown value from read_framelist()");
        return NULL;
    }
}

static PyObject*
SHNDecoder_pcm_split(decoders_SHNDecoder* self, PyObject *args)
{
    if (!setjmp(*br_try(self->bitstream))) {
        a_int* header = self->pcm_header;
        a_int* footer = self->pcm_footer;
        a_int* current = header;
        uint8_t* header_s;
        uint8_t* footer_s;
        PyObject* tuple;

        unsigned command;
        unsigned i;

        header->reset(header);
        footer->reset(footer);

        /*walk through file, processing all commands*/
        do {
            unsigned energy;
            unsigned LPC_count;
            unsigned verbatim_size;

            command = read_unsigned(self->bitstream, COMMAND_SIZE);

            switch (command) {
            case FN_DIFF0:
            case FN_DIFF1:
            case FN_DIFF2:
            case FN_DIFF3:
                /*all the DIFF commands have the same structure*/
                energy = read_unsigned(self->bitstream, ENERGY_SIZE);
                for (i = 0; i < self->block_length; i++) {
                    skip_signed(self->bitstream, energy);
                }
                current = footer;
                break;
            case FN_QUIT:
                self->stream_finished = 1;
                break;
            case FN_BLOCKSIZE:
                self->block_length = read_long(self->bitstream);
                break;
            case FN_BITSHIFT:
                skip_unsigned(self->bitstream, SHIFT_SIZE);
                break;
            case FN_QLPC:
                energy = read_unsigned(self->bitstream, ENERGY_SIZE);
                LPC_count = read_unsigned(self->bitstream, LPC_COUNT_SIZE);
                for (i = 0; i < LPC_count; i++) {
                    skip_signed(self->bitstream, LPC_COEFF_SIZE);
                }
                for (i = 0; i < self->block_length; i++) {
                    skip_signed(self->bitstream, energy);
                }
                current = footer;
                break;
            case FN_ZERO:
                current = footer;
                break;
            case FN_VERBATIM:
                /*any VERBATIM commands have their data appended
                  to header or footer*/
                verbatim_size = read_unsigned(self->bitstream,
                                              VERBATIM_CHUNK_SIZE);
                for (i = 0; i < verbatim_size; i++) {
                    current->append(current,
                                    read_unsigned(self->bitstream,
                                                  VERBATIM_BYTE_SIZE));
                }
                break;
            }
        } while (command != FN_QUIT);

        br_etry(self->bitstream);

        /*once all commands have been processed,
          transform the bytes in header and footer to strings*/
        header_s = malloc(sizeof(uint8_t) * header->len);
        for (i = 0; i < header->len; i++)
            header_s[i] = (uint8_t)(header->_[i] & 0xFF);

        footer_s = malloc(sizeof(uint8_t) * footer->len);
        for (i = 0; i < footer->len; i++)
            footer_s[i] = (uint8_t)(footer->_[i] & 0xFF);

        /*generate a tuple from the strings*/
        tuple = Py_BuildValue("(s#s#)",
                              header_s, header->len,
                              footer_s, footer->len);

        /*deallocate temporary space before returning tuple*/
        free(header_s);
        free(footer_s);

        return tuple;
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading Shorten file");
        return NULL;
    }
}
#endif

static status
read_shn_header(decoders_SHNDecoder* self, BitstreamReader* reader)
{
    if (!setjmp(*br_try(reader))) {
        uint8_t magic_number[4];
        unsigned version;
        unsigned i;

        reader->parse(reader, "4b 8u", magic_number, &version);
        if (memcmp(magic_number, "ajkg", 4)) {
            br_etry(reader);
            return INVALID_MAGIC_NUMBER;
        }
        if (version != 2) {
            br_etry(reader);
            return INVALID_SHORTEN_VERSION;
        }

        self->header.file_type = read_long(reader);
        self->header.channels = read_long(reader);
        self->block_length = read_long(reader);
        self->left_shift = 0;
        self->header.max_LPC = read_long(reader);
        self->header.mean_count = read_long(reader);
        reader->skip_bytes(reader, read_long(reader));

        if ((1 <= self->header.file_type) && (self->header.file_type <= 2)) {
            self->bits_per_sample = 8;
            self->signed_samples = (self->header.file_type == 1);
        } else if ((3 <= self->header.file_type) &&
                   (self->header.file_type <= 6)) {
            self->bits_per_sample = 16;
            self->signed_samples = ((self->header.file_type == 3) ||
                                    (self->header.file_type == 5));
        } else {
            br_etry(reader);
            return UNSUPPORTED_FILE_TYPE;
        }

        for (i = 0; i < self->header.channels; i++) {
            a_int* means = self->means->append(self->means);
            means->mset(means, self->header.mean_count, 0);
            self->previous_samples->append(self->previous_samples);
        }

        /*process first instruction for wave/aiff header, if present*/
        process_iff_header(reader,
                           &(self->sample_rate),
                           &(self->channel_mask));

        br_etry(reader);

        return OK;
    } else {
        /*read error in Shorten header*/
        br_etry(reader);
        return IOERROR;
    }
}

static status
read_framelist(decoders_SHNDecoder* self, aa_int* framelist)
{
    unsigned c = 0;

    self->samples->reset(self->samples);

    if (!setjmp(*br_try(self->bitstream))) {
        while (1) {
            const unsigned command = read_unsigned(self->bitstream,
                                                   COMMAND_SIZE);

            if (((FN_DIFF0 <= command) && (command <= FN_DIFF3)) ||
                ((FN_QLPC <= command) && (command <= FN_ZERO))) {
                /*audio data commands*/
                a_int* means = self->means->_[c];
                a_int* previous_samples = self->previous_samples->_[c];
                a_int* samples = self->samples->append(self->samples);
                a_int* unshifted = framelist->append(framelist);

                switch (command) {
                case FN_DIFF0:
                    read_diff0(self->bitstream,
                               self->block_length,
                               means,
                               samples);
                    break;
                case FN_DIFF1:
                    read_diff1(self->bitstream,
                               self->block_length,
                               previous_samples,
                               samples);
                    break;
                case FN_DIFF2:
                    read_diff2(self->bitstream,
                               self->block_length,
                               previous_samples,
                               samples);
                    break;
                case FN_DIFF3:
                    read_diff3(self->bitstream,
                               self->block_length,
                               previous_samples,
                               samples);
                    break;
                case FN_QLPC:
                    read_qlpc(self->bitstream,
                              self->block_length,
                              previous_samples,
                              means,
                              samples);
                    break;
                case FN_ZERO:
                    samples->mset(samples, self->block_length, 0);
                    break;
                default:
                    break; /*can't get here*/
                }

                /*calculate next mean for given channel*/
                means->append(means, shnmean(samples));
                means->tail(means, self->header.mean_count, means);

                /*wrap samples for next set of channels*/
                samples->tail(samples, MAX(3, self->header.max_LPC),
                              previous_samples);

                /*apply any left shift to channel*/
                if (self->left_shift) {
                    unsigned i;
                    unshifted->resize_for(unshifted, samples->len);
                    for (i = 0; i < samples->len; i++)
                        a_append(unshifted, samples->_[i] << self->left_shift);
                } else {
                    samples->copy(samples, unshifted);
                }

                /*if stream is unsigned, convert unshifted samples to signed*/
                if (!self->signed_samples) {
                    const int adjustment = 1 << (self->bits_per_sample - 1);
                    unsigned i;
                    for (i = 0; i < unshifted->len; i++)
                        unshifted->_[i] -= adjustment;
                }

                /*move on to next channel*/
                c++;

                /*return OK once all channels are constructed*/
                if (c == self->header.channels) {
                    br_etry(self->bitstream);
                    return OK;
                }
            } else if (((FN_QUIT <= command) && (command <= FN_BITSHIFT)) ||
                       (command == FN_VERBATIM)) {
                unsigned verbatim_size;
                unsigned i;

                /*non audio commands*/
                switch (command) {
                case FN_QUIT:
                    self->stream_finished = 1;
                    br_etry(self->bitstream);
                    return END_OF_STREAM;
                case FN_BLOCKSIZE:
                    self->block_length = read_long(self->bitstream);
                    break;
                case FN_BITSHIFT:
                    self->left_shift = read_unsigned(self->bitstream,
                                                     SHIFT_SIZE);
                    break;
                case FN_VERBATIM:
                    verbatim_size = read_unsigned(self->bitstream,
                                                  VERBATIM_CHUNK_SIZE);
                    for (i = 0; i < verbatim_size; i++)
                        skip_unsigned(self->bitstream, VERBATIM_BYTE_SIZE);
                    break;
                default:
                    break; /*can't get here*/
                }
            } else {
                /*unknown command*/
                br_etry(self->bitstream);
                return UNKNOWN_COMMAND;
            }
        }
    } else {
        br_etry(self->bitstream);
        return IOERROR;
    }
}

static void
read_diff0(BitstreamReader* bs, unsigned block_length,
           const a_int* means, a_int* samples)
{
    const int offset = shnmean(means);
    const unsigned energy = read_unsigned(bs, ENERGY_SIZE);
    unsigned i;

    samples->reset_for(samples, block_length);

    for (i = 0; i < block_length; i++) {
        const int residual = read_signed(bs, energy);
        a_append(samples, residual + offset);
    }
}

static void
read_diff1(BitstreamReader* bs, unsigned block_length,
           a_int* previous_samples, a_int* samples)
{
    unsigned i;
    unsigned energy;

    /*ensure "previous_samples" contains at least 1 value*/
    if (previous_samples->len < 1) {
        samples->mset(samples, 1 - previous_samples->len, 0);
        samples->extend(samples, previous_samples);
    } else {
        previous_samples->tail(previous_samples, 1, samples);
    }

    energy = read_unsigned(bs, ENERGY_SIZE);

    /*process the residuals to samples*/
    samples->resize_for(samples, block_length);
    for (i = 1; i < (block_length + 1); i++) {
        const int residual = read_signed(bs, energy);
        a_append(samples, samples->_[i - 1] + residual);
    }

    /*truncate samples to block length*/
    samples->tail(samples, block_length, samples);
}

static void
read_diff2(BitstreamReader* bs, unsigned block_length,
           a_int* previous_samples, a_int* samples)
{
    unsigned i;
    unsigned energy;

    /*ensure "previous_samples" contains at least 2 values*/
    if (previous_samples->len < 2) {
        samples->mset(samples, 2 - previous_samples->len, 0);
        samples->extend(samples, previous_samples);
    } else {
        previous_samples->tail(previous_samples, 2, samples);
    }

    energy = read_unsigned(bs, ENERGY_SIZE);

    /*process the residuals to samples*/
    samples->resize_for(samples, block_length);
    for (i = 2; i < (block_length + 2); i++) {
        const int residual = read_signed(bs, energy);
        a_append(samples,
                 (2 * samples->_[i - 1]) - samples->_[i - 2] + residual);
    }

    /*truncate samples to block length*/
    samples->tail(samples, block_length, samples);
}

static void
read_diff3(BitstreamReader* bs, unsigned block_length,
           a_int* previous_samples, a_int* samples)
{
    unsigned i;
    unsigned energy;

    /*ensure "previous_samples" contains at least 3 values*/
    if (previous_samples->len < 3) {
        samples->mset(samples, 3 - previous_samples->len, 0);
        samples->extend(samples, previous_samples);
    } else {
        previous_samples->tail(previous_samples, 3, samples);
    }

    energy = read_unsigned(bs, ENERGY_SIZE);

    /*process the residuals to samples*/
    samples->resize_for(samples, block_length);
    for (i = 3; i < (block_length + 3); i++) {
        const int residual = read_signed(bs, energy);
        a_append(samples,
                 (3 * (samples->_[i - 1] - samples->_[i - 2])) +
                 samples->_[i - 3] + residual);
    }

    /*truncate samples to block length*/
    samples->tail(samples, block_length, samples);
}

static void
read_qlpc(BitstreamReader* bs, unsigned block_length,
          a_int* previous_samples, a_int* means, a_int* samples)
{
    /*read some QLPC setup values*/
    const int offset = shnmean(means);
    const unsigned energy = read_unsigned(bs, ENERGY_SIZE);
    const unsigned LPC_count = read_unsigned(bs, LPC_COUNT_SIZE);
    a_int* LPC_coeff = a_int_new();
    a_int* offset_samples = a_int_new();
    a_int* unoffset_samples = a_int_new();

    if (!setjmp(*br_try(bs))) {
        int i;

        for (i = 0; i < LPC_count; i++)
            LPC_coeff->append(LPC_coeff, read_signed(bs, LPC_COEFF_SIZE));

        /*ensure "previous_samples" contains at least "LPC count" values*/
        if (previous_samples->len < LPC_count) {
            offset_samples->mset(offset_samples,
                                 LPC_count - previous_samples->len, 0);
            offset_samples->extend(offset_samples, previous_samples);
        } else {
            previous_samples->tail(previous_samples, LPC_count, offset_samples);
        }

        /*process the residuals to unoffset samples*/
        for (i = 0; i < block_length; i++) {
            const int residual = read_signed(bs, energy);
            int sum = 1 << 5;
            int j;
            for (j = 0; j < LPC_count; j++) {
                if ((i - j - 1) < 0) {
                    sum += LPC_coeff->_[j] *
                        (offset_samples->_[LPC_count + (i - j - 1)] -
                         offset);
                } else {
                    sum += LPC_coeff->_[j] * unoffset_samples->_[i - j - 1];
                }
            }
            unoffset_samples->append(unoffset_samples, (sum >> 5) + residual);
        }

        /*reapply offset to unoffset samples*/
        samples->reset_for(samples, unoffset_samples->len);
        for (i = 0; i < unoffset_samples->len; i++) {
            a_append(samples, unoffset_samples->_[i] + offset);
        }

        /*deallocate temporary arrays before returning successfully*/
        LPC_coeff->del(LPC_coeff);
        offset_samples->del(offset_samples);
        unoffset_samples->del(unoffset_samples);
        br_etry(bs);
    } else {
        /*error reading QLPC, so deallocate temporary arrays*/
        LPC_coeff->del(LPC_coeff);
        offset_samples->del(offset_samples);
        unoffset_samples->del(unoffset_samples);
        br_etry(bs);

        /*before aborting to the next spot on the abort stack*/
        br_abort(bs);
    }
}

static int
shnmean(const a_int* values)
{
    return ((int)(values->len / 2) + values->sum(values)) / (int)(values->len);
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

static void
process_iff_header(BitstreamReader* bs,
                   unsigned* sample_rate,
                   unsigned* channel_mask)
{
    enum {COMMAND_START, VERBATIM_START};
    unsigned command;

    bs->mark(bs, COMMAND_START);
    if (!setjmp(*br_try(bs))) {
        command = read_unsigned(bs, COMMAND_SIZE);

        if (command == FN_VERBATIM) {
            BitstreamReader* verbatim;
            unsigned verbatim_size;

            verbatim = read_verbatim(bs, &verbatim_size);
            verbatim->mark(verbatim, VERBATIM_START);

            if (!read_wave_header(verbatim, verbatim_size,
                                  sample_rate, channel_mask)) {
                verbatim->unmark(verbatim, VERBATIM_START);
                verbatim->close(verbatim);
                bs->rewind(bs, COMMAND_START);
                bs->unmark(bs, COMMAND_START);
                br_etry(bs);
                return;
            } else {
                verbatim->rewind(verbatim, VERBATIM_START);
            }

            if (!read_aiff_header(verbatim, verbatim_size,
                                  sample_rate, channel_mask)) {
                verbatim->unmark(verbatim, VERBATIM_START);
                verbatim->close(verbatim);
                bs->rewind(bs, COMMAND_START);
                bs->unmark(bs, COMMAND_START);
                br_etry(bs);
                return;
            } else {
                verbatim->rewind(verbatim, VERBATIM_START);
            }

            /*neither wave header or aiff header found,
              so use dummy values again*/
            verbatim->unmark(verbatim, VERBATIM_START);
            verbatim->close(verbatim);
            bs->rewind(bs, COMMAND_START);
            bs->unmark(bs, COMMAND_START);
            *sample_rate = 44100;
            *channel_mask = 0;
            br_etry(bs);
            return;
        } else {
            /*VERBATIM isn't the first command
              so rewind and set some dummy values*/
            bs->rewind(bs, COMMAND_START);
            bs->unmark(bs, COMMAND_START);
            *sample_rate = 44100;
            *channel_mask = 0;
            br_etry(bs);
            return;
        }
    } else {
        /*wrap IFF chunk reader in try block
          to unmark the stream prior to bubbling up
          the read exception to read_shn_header()*/
        bs->unmark(bs, COMMAND_START);
        br_etry(bs);
        br_abort(bs);
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
        const int f = (int)((double)mantissa *
                            pow(2.0, (double)exponent - 16383 - 63));
        if (sign)
            return -f;
        else
            return f;
    }
}

#ifdef STANDALONE
#include <errno.h>

int main(int argc, char* argv[]) {
    decoders_SHNDecoder decoder;
    FILE* file;
    aa_int* framelist;
    unsigned output_data_size;
    unsigned char* output_data;
    unsigned bytes_per_sample;
    FrameList_int_to_char_converter converter;

    if (argc < 2) {
        fprintf(stderr, "*** Usage: %s <file.shn>\n", argv[0]);
        return 1;
    }
    if ((file = fopen(argv[1], "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", argv[1], strerror(errno));
        return 1;
    } else {
        decoder.bitstream = br_open(file, BS_BIG_ENDIAN);
        decoder.stream_finished = 0;

        decoder.means = aa_int_new();
        decoder.previous_samples = aa_int_new();

        decoder.samples = aa_int_new();
        decoder.unshifted = aa_int_new();
        decoder.pcm_header = a_int_new();
        decoder.pcm_footer = a_int_new();

        framelist = aa_int_new();

        output_data_size = 1;
        output_data = malloc(output_data_size);
    }

    /*read Shorten header for basic info*/
    switch (read_shn_header(&decoder, decoder.bitstream)) {
    case INVALID_MAGIC_NUMBER:
        fprintf(stderr, "invalid magic number");
        goto error;
    case INVALID_SHORTEN_VERSION:
        fprintf(stderr, "invalid Shorten version");
        goto error;
    case UNSUPPORTED_FILE_TYPE:
        fprintf(stderr, "unsupported Shorten file type");
        goto error;
    case IOERROR:
        fprintf(stderr, "I/O error reading Shorten header");
        goto error;
    default:
        bytes_per_sample = decoder.bits_per_sample / 8;
        converter = FrameList_get_int_to_char_converter(
            decoder.bits_per_sample, 0, 1);
        break;
    }

    while (!decoder.stream_finished) {
        unsigned pcm_size;
        unsigned channel;
        unsigned frame;

        framelist->reset(framelist);
        /*decode set of commands into a single framelist*/
        switch (read_framelist(&decoder, framelist)) {
        case OK:
            /*convert framelist to string and output it to stdout*/
            pcm_size = (bytes_per_sample *
                        framelist->len *
                        framelist->_[0]->len);
            if (pcm_size > output_data_size) {
                output_data_size = pcm_size;
                output_data = realloc(output_data, output_data_size);
            }
            for (channel = 0; channel < framelist->len; channel++) {
                const a_int* channel_data = framelist->_[channel];
                for (frame = 0; frame < channel_data->len; frame++) {
                    converter(channel_data->_[frame],
                              output_data +
                              ((frame * framelist->len) + channel) *
                              bytes_per_sample);
                }
            }

            fwrite(output_data, sizeof(unsigned char), pcm_size, stdout);
            break;
        case END_OF_STREAM:
            /*automatically sets stream_finished to true*/
            break;
        case UNKNOWN_COMMAND:
            fprintf(stderr, "unknown command in Shorten stream");
            goto error;
        case IOERROR:
            fprintf(stderr, "I/O error reading Shorten file");
            goto error;
        default:
            /*shouldn't get here*/
            fprintf(stderr, "unknown value from read_framelist()");
            goto error;
        }
    }

    decoder.bitstream->close(decoder.bitstream);

    decoder.means->del(decoder.means);
    decoder.previous_samples->del(decoder.previous_samples);
    decoder.samples->del(decoder.samples);
    decoder.unshifted->del(decoder.unshifted);
    decoder.pcm_header->del(decoder.pcm_header);
    decoder.pcm_footer->del(decoder.pcm_footer);
    framelist->del(framelist);
    free(output_data);

    return 0;

error:
    decoder.bitstream->close(decoder.bitstream);

    decoder.means->del(decoder.means);
    decoder.previous_samples->del(decoder.previous_samples);
    decoder.samples->del(decoder.samples);
    decoder.unshifted->del(decoder.unshifted);
    decoder.pcm_header->del(decoder.pcm_header);
    decoder.pcm_footer->del(decoder.pcm_footer);
    framelist->del(framelist);
    free(output_data);

    return 1;
}
#endif
