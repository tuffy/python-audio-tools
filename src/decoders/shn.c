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

int
SHNDecoder_init(decoders_SHNDecoder *self,
                PyObject *args, PyObject *kwds)
{
    char* filename;
    FILE* fp;

    self->filename = NULL;
    self->bitstream = NULL;
    self->stream_finished = 0;

    self->means = array_ia_new();
    self->previous_samples = array_ia_new();

    /*setup temporary buffers*/
    self->samples = array_ia_new();
    self->unshifted = array_ia_new();
    self->pcm_header = array_i_new();
    self->pcm_footer = array_i_new();

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

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
        unsigned i;

        self->bitstream->parse(self->bitstream, "4b 8u",
                               magic_number,
                               &version);
        if (memcmp(magic_number, "ajkg", 4)) {
            PyErr_SetString(PyExc_ValueError, "invalid magic number");
            br_etry(self->bitstream);
            return -1;
        }
        if (version != 2) {
            PyErr_SetString(PyExc_ValueError, "invalid Shorten version");
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
            PyErr_SetString(PyExc_ValueError, "unsupported Shorten file type");
            br_etry(self->bitstream);
            return -1;
        }

        for (i = 0; i < self->header.channels; i++) {
            array_i* means = self->means->append(self->means);
            means->mset(means, self->header.mean_count, 0);
            self->previous_samples->append(self->previous_samples);
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
    self->means->del(self->means);
    self->previous_samples->del(self->previous_samples);
    self->samples->del(self->samples);
    self->unshifted->del(self->unshifted);
    self->pcm_header->del(self->pcm_header);
    self->pcm_footer->del(self->pcm_footer);

    Py_XDECREF(self->audiotools_pcm);

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
    unsigned c = 0;
    PyThreadState *thread_state = NULL;

    self->samples->reset(self->samples);
    self->unshifted->reset(self->unshifted);

    if (self->stream_finished) {
        return empty_FrameList(self->audiotools_pcm,
                               self->header.channels,
                               self->bits_per_sample);
    }

    thread_state = PyEval_SaveThread();

    if (!setjmp(*br_try(self->bitstream))) {
        while (1) {
            const unsigned command = read_unsigned(self->bitstream,
                                                   COMMAND_SIZE);

            if (((FN_DIFF0 <= command) && (command <= FN_DIFF3)) ||
                ((FN_QLPC <= command) && (command <= FN_ZERO))) {
                /*audio data commands*/
                array_i* means = self->means->_[c];
                array_i* previous_samples = self->previous_samples->_[c];
                array_i* samples = self->samples->append(self->samples);
                array_i* unshifted = self->unshifted->append(self->unshifted);

                switch (command) {
                case FN_DIFF0:
                    read_diff0(self->bitstream, self->block_length, means,
                               samples);
                    break;
                case FN_DIFF1:
                    read_diff1(self->bitstream, self->block_length,
                               previous_samples, samples);
                    break;
                case FN_DIFF2:
                    read_diff2(self->bitstream, self->block_length,
                               previous_samples, samples);
                    break;
                case FN_DIFF3:
                    read_diff3(self->bitstream, self->block_length,
                               previous_samples, samples);
                    break;
                case FN_QLPC:
                    read_qlpc(self->bitstream, self->block_length,
                              previous_samples, means, samples);
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
                    for (i = 0; i < samples->len; i++)
                        unshifted->append(unshifted,
                                          samples->_[i] << self->left_shift);
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

                /*once all channels are constructed,
                  return a complete set of PCM frames*/
                if (c == self->header.channels) {
                    br_etry(self->bitstream);
                    PyEval_RestoreThread(thread_state);
                    return array_ia_to_FrameList(self->audiotools_pcm,
                                                 self->unshifted,
                                                 self->bits_per_sample);
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
                    PyEval_RestoreThread(thread_state);
                    return empty_FrameList(self->audiotools_pcm,
                                           self->header.channels,
                                           self->bits_per_sample);
                    break;
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
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError,
                                "unknown command in Shorten stream");
                return NULL;
            }
        }
    } else {
        br_etry(self->bitstream);
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "I/O error reading Shorten file");
        return NULL;
    }
}

static void
read_diff0(BitstreamReader* bs, unsigned block_length,
           const array_i* means, array_i* samples)
{
    const int offset = shnmean(means);
    const unsigned energy = read_unsigned(bs, ENERGY_SIZE);
    unsigned i;

    samples->reset(samples);

    for (i = 0; i < block_length; i++) {
        const int residual = read_signed(bs, energy);
        samples->append(samples, residual + offset);
    }
}

static void
read_diff1(BitstreamReader* bs, unsigned block_length,
           array_i* previous_samples, array_i* samples)
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
    for (i = 1; i < (block_length + 1); i++) {
        const int residual = read_signed(bs, energy);
        samples->append(samples, samples->_[i - 1] + residual);
    }

    /*truncate samples to block length*/
    samples->tail(samples, block_length, samples);
}

static void
read_diff2(BitstreamReader* bs, unsigned block_length,
           array_i* previous_samples, array_i* samples)
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
    for (i = 2; i < (block_length + 2); i++) {
        const int residual = read_signed(bs, energy);
        samples->append(samples,
                        (2 * samples->_[i - 1]) - samples->_[i - 2] + residual);
    }

    /*truncate samples to block length*/
    samples->tail(samples, block_length, samples);
}

static void
read_diff3(BitstreamReader* bs, unsigned block_length,
           array_i* previous_samples, array_i* samples)
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
    for (i = 3; i < (block_length + 3); i++) {
        const int residual = read_signed(bs, energy);
        samples->append(samples,
                        (3 * (samples->_[i - 1] - samples->_[i - 2])) +
                        samples->_[i - 3] + residual);
    }

    /*truncate samples to block length*/
    samples->tail(samples, block_length, samples);
}

static void
read_qlpc(BitstreamReader* bs, unsigned block_length,
          array_i* previous_samples, array_i* means, array_i* samples)
{
    /*read some QLPC setup values*/
    const int offset = shnmean(means);
    const unsigned energy = read_unsigned(bs, ENERGY_SIZE);
    const unsigned LPC_count = read_unsigned(bs, LPC_COUNT_SIZE);
    array_i* LPC_coeff = array_i_new();
    array_i* offset_samples = array_i_new();
    array_i* unoffset_samples = array_i_new();

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
        samples->reset(samples);
        for (i = 0; i < unoffset_samples->len; i++) {
            samples->append(samples, unoffset_samples->_[i] + offset);
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
shnmean(const array_i* values)
{
    return ((int)(values->len / 2) + values->sum(values)) / (int)(values->len);
}

static PyObject*
SHNDecoder_pcm_split(decoders_SHNDecoder* self, PyObject *args)
{
    if (!setjmp(*br_try(self->bitstream))) {
        array_i* header = self->pcm_header;
        array_i* footer = self->pcm_footer;
        array_i* current = header;
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
    if (!setjmp(*br_try(bs))) {
        command = read_unsigned(bs, COMMAND_SIZE);

        if (command == FN_VERBATIM) {
            BitstreamReader* verbatim;
            unsigned verbatim_size;

            verbatim = read_verbatim(bs, &verbatim_size);
            verbatim->mark(verbatim);

            if (!read_wave_header(verbatim, verbatim_size,
                                  sample_rate, channel_mask)) {
                verbatim->unmark(verbatim);
                verbatim->close(verbatim);
                bs->rewind(bs);
                bs->unmark(bs);
                br_etry(bs);
                return 0;
            } else {
                verbatim->rewind(verbatim);
            }

            if (!read_aiff_header(verbatim, verbatim_size,
                                  sample_rate, channel_mask)) {
                verbatim->unmark(verbatim);
                verbatim->close(verbatim);
                bs->rewind(bs);
                bs->unmark(bs);
                br_etry(bs);
                return 0;
            } else {
                verbatim->rewind(verbatim);
            }

            /*neither wave header or aiff header found,
              so use dummy values again*/
            verbatim->unmark(verbatim);
            verbatim->close(verbatim);
            bs->rewind(bs);
            bs->unmark(bs);
            *sample_rate = 44100;
            *channel_mask = 0;
            br_etry(bs);
            return 0;
        } else {
            /*VERBATIM isn't the first command
              so rewind and set some dummy values*/
            bs->rewind(bs);
            bs->unmark(bs);
            *sample_rate = 44100;
            *channel_mask = 0;
            br_etry(bs);
            return 0;
        }
    } else {
        bs->unmark(bs);
        br_etry(bs);
        br_abort(bs);
        return 0; /*won't get here*/
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
        const int f = (int)((long double)mantissa *
                            powl(2.0, (long double )exponent - 16383 - 63));
        if (sign)
            return -f;
        else
            return f;
    }
}
