#include "tta.h"
#include "../common/tta_crc.h"
#include "../framelist.h"
#include <string.h>
#include <stdio.h>
#include <errno.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

typedef struct {
    uint32_t crc32;
    int is_valid;
} checksum_t;

typedef enum {
    OK,
    IO_ERROR,
    CRC_MISMATCH,
    FRAME_TOO_SMALL,
    INVALID_SIGNATURE,
    INVALID_FORMAT
} status_t;

struct residual_params {
    unsigned k0;
    unsigned k1;
    unsigned sum0;
    unsigned sum1;
};

struct filter_params {
    unsigned shift;
    int previous_residual;
    int round;
    int qm[8];
    int dx[8];
    int dl[8];
};

struct prediction_params {
    unsigned shift;
    int previous_sample;
};

/*******************************
 * private function signatures *
 *******************************/

/*initializes checksum on the given BitstreamReader*/
static void
checksum_init(BitstreamReader *frame, checksum_t *checksum);

/*sets checksum's is_valid field to 1 if the checksum validates
  or sets it to 0 if the checksum does not validate

  does not check for I/O errors when reading checksum

  removes checksum callback from frame*/
static void
checksum_validate(BitstreamReader *frame, checksum_t *checksum);

/*stops calculating checksum from stream by removing callback*/
static inline void
checksum_clear(BitstreamReader *frame);

/*reads a TTA header from the frame to "header"
  returns OK on success, or some error value*/
static status_t
read_header(BitstreamReader *frame, struct tta_header *header);

/*returns a freshly allocated array of "total_tta_frames" frame sizes*/
static status_t
read_seektable(BitstreamReader *frame,
               unsigned total_tta_frames,
               unsigned **seektable);

static unsigned
tta_block_size(unsigned current_tta_frame, const struct tta_header *header);

static status_t
read_tta_frame(BitstreamReader *frame,
               unsigned channels,
               unsigned bits_per_sample,
               unsigned block_size,
               int samples[]);

static void
init_residual_params(struct residual_params *params);

/*given raw TTA frame data and residual parameters,
  updates the parameters and returns the next residual*/
static int
read_residual(struct residual_params *params, BitstreamReader *frame);

static void
init_filter_params(unsigned bits_per_sample,
                   struct filter_params *params);

/*given a residual and filter parameters,
  updates the parameters and returns a predicted sample*/
static int
run_filter(struct filter_params *params, int residual);

static void
init_prediction_params(unsigned bits_per_sample,
                       struct prediction_params *params);

/*given a filtered sample and prediction parameters,
  updates the parameters and returns a predicted sample*/
static int
run_prediction(struct prediction_params *params, int filtered);

/*given a PCM frame's worth of predicted samples and channel count,
  decorrelates the samples*/
static void
decorrelate_channels(unsigned channel_count,
                     const int predicted[],
                     int samples[]);

#ifndef STANDALONE
static PyObject*
tta_exception(status_t error);
#endif

static const char*
tta_strerror(status_t error);

static inline unsigned
div_ceil(unsigned x, unsigned y)
{
    ldiv_t div = ldiv((long)x, (long)y);
    return div.rem ? ((unsigned)div.quot + 1) : (unsigned)div.quot;
}

/***********************************
 * public function implementations *
 ***********************************/

#ifndef STANDALONE

PyObject*
TTADecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_TTADecoder *self;

    self = (decoders_TTADecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
TTADecoder_init(decoders_TTADecoder *self, PyObject *args, PyObject *kwds) {
    PyObject *file;
    status_t status;

    self->seektable = NULL;
    self->bitstream = NULL;
    self->audiotools_pcm = NULL;
    self->frames_start = NULL;

    if (!PyArg_ParseTuple(args, "O", &file)) {
        return -1;
    } else {
        Py_INCREF(file);
    }

    self->bitstream = br_open_external(file,
                                       BS_LITTLE_ENDIAN,
                                       4096,
                                       br_read_python,
                                       bs_setpos_python,
                                       bs_getpos_python,
                                       bs_free_pos_python,
                                       bs_fseek_python,
                                       bs_close_python,
                                       bs_free_python_decref);

    /*read and validate header*/
    if ((status = read_header(self->bitstream, &(self->header))) != OK) {
        PyErr_SetString(tta_exception(status), tta_strerror(status));
        return -1;
    }

    /*calculate some parameters from header*/
    self->current_tta_frame = 0;

    /*read seektable*/
    if ((status = read_seektable(self->bitstream,
                                 self->header.total_tta_frames,
                                 &(self->seektable))) != OK) {
        PyErr_SetString(tta_exception(status), tta_strerror(status));
        return -1;
    }

    /*get FrameList generator for output*/
    self->audiotools_pcm = open_audiotools_pcm();

    /*mark beginning of frames for seeking*/
    self->frames_start = self->bitstream->getpos(self->bitstream);

    /*mark file as not closed*/
    self->closed = 0;

    return 0;
}

void
TTADecoder_dealloc(decoders_TTADecoder *self) {
    free(self->seektable);

    if (self->bitstream) {
        self->bitstream->free(self->bitstream);
    }

    Py_XDECREF(self->audiotools_pcm);

    if (self->frames_start) {
        self->frames_start->del(self->frames_start);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
TTADecoder_sample_rate(decoders_TTADecoder *self, void *closure)
{
    return Py_BuildValue("i", self->header.sample_rate);
}

static PyObject*
TTADecoder_bits_per_sample(decoders_TTADecoder *self, void *closure)
{
    return Py_BuildValue("i", self->header.bits_per_sample);
}

static PyObject*
TTADecoder_channels(decoders_TTADecoder *self, void *closure)
{
    return Py_BuildValue("i", self->header.channels);
}

static PyObject*
TTADecoder_channel_mask(decoders_TTADecoder *self, void *closure)
{
    switch (self->header.channels) {
    case 1:
        return Py_BuildValue("i", 0x4);
    case 2:
        return Py_BuildValue("i", 0x3);
    default:
        return Py_BuildValue("i", 0);
    }
}

PyObject*
TTADecoder_read(decoders_TTADecoder* self, PyObject *args)
{
    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    } else if (self->current_tta_frame == self->header.total_tta_frames) {
        return empty_FrameList(self->audiotools_pcm,
                               self->header.channels,
                               self->header.bits_per_sample);
    } else {
        const unsigned block_size =
            tta_block_size(self->current_tta_frame, &self->header);
        pcm_FrameList *framelist =
            new_FrameList(self->audiotools_pcm,
                          self->header.channels,
                          self->header.bits_per_sample,
                          block_size);
        status_t status;

        if ((status = read_tta_frame(self->bitstream,
                                     self->header.channels,
                                     self->header.bits_per_sample,
                                     block_size,
                                     framelist->samples)) == OK) {
            self->current_tta_frame += 1;
            return (PyObject*)framelist;
        } else {
            Py_DECREF((PyObject*)framelist);
            PyErr_SetString(tta_exception(status), tta_strerror(status));
            return NULL;
        }
    }
}

static PyObject*
TTADecoder_seek(decoders_TTADecoder *self, PyObject *args)
{
    long long seeked_offset;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot seek closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "L", &seeked_offset))
        return NULL;

    if (seeked_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "cannot seek to negative value");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        unsigned current_pcm_frame = 0;

        /*rewind to start of TTA blocks*/
        self->bitstream->setpos(self->bitstream, self->frames_start);

        /*skip frames until we reach the requested one
          or run out of frames entirely
          and adjust both current TTA frame and
          remaining number of PCM frames according to new position*/
        self->current_tta_frame = 0;

        while (seeked_offset > self->header.default_block_size) {
            if (self->current_tta_frame < self->header.total_tta_frames) {
                const unsigned frame_size =
                    self->seektable[self->current_tta_frame];

                self->bitstream->seek(self->bitstream,
                                      (long)frame_size,
                                      BS_SEEK_CUR);

                current_pcm_frame += self->header.default_block_size;
                self->current_tta_frame++;
                seeked_offset -= self->header.default_block_size;
            } else {
                /*no additional frames to seek to*/
                break;
            }
        }

        br_etry(self->bitstream);

        /*return PCM offset actually seeked to*/
        return Py_BuildValue("I", current_pcm_frame);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error seeking in stream");
        return NULL;
    }

    return Py_None;
}

PyObject*
TTADecoder_close(decoders_TTADecoder* self, PyObject *args)
{
    self->closed = 1;

    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
TTADecoder_enter(decoders_TTADecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
TTADecoder_exit(decoders_TTADecoder* self, PyObject *args)
{
    self->closed = 1;

    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

#endif

/************************************
 * private function implementations *
 ************************************/

static void
checksum_init(BitstreamReader *frame, checksum_t *checksum)
{
    checksum->crc32 = 0xFFFFFFFF;
    checksum->is_valid = 0;

    frame->add_callback(frame,
                        (bs_callback_f)tta_crc32,
                        &checksum->crc32);
}

static void
checksum_validate(BitstreamReader *frame, checksum_t *checksum)
{
    uint32_t frame_crc32;
    frame->pop_callback(frame, NULL);
    frame_crc32 = frame->read(frame, 32);
    checksum->is_valid = (frame_crc32 == (checksum->crc32 ^ 0xFFFFFFFF));
}

static void
checksum_clear(BitstreamReader *frame)
{
    if (frame->callbacks != NULL) {
        frame->pop_callback(frame, NULL);
    }
}

static status_t
read_header(BitstreamReader *frame, struct tta_header *header)
{
    checksum_t checksum;
    uint8_t signature[4];
    unsigned format;

    checksum_init(frame, &checksum);

    if (!setjmp(*br_try(frame))) {
        frame->read_bytes(frame, signature, 4);
        format = frame->read(frame, 16);
        header->channels = frame->read(frame, 16);
        header->bits_per_sample = frame->read(frame, 16);
        header->sample_rate = frame->read(frame, 32);
        header->total_pcm_frames = frame->read(frame, 32);

        header->default_block_size = (header->sample_rate * 256) / 245;
        header->total_tta_frames = div_ceil(header->total_pcm_frames,
                                            header->default_block_size);

        checksum_validate(frame, &checksum);
        br_etry(frame);
    } else {
        checksum_clear(frame);
        br_etry(frame);
        return IO_ERROR;
    }

    if (memcmp(signature, "TTA1", 4)) {
        return INVALID_SIGNATURE;
    } else if (format != 1) {
        return INVALID_FORMAT;
    } else if (!checksum.is_valid) {
        return CRC_MISMATCH;
    } else {
        return OK;
    }
}

/*returns a freshly allocated array of "total_tta_frames" frame sizes*/
static status_t
read_seektable(BitstreamReader *frame,
               unsigned total_tta_frames,
               unsigned **seektable)
{
    checksum_t checksum;
    unsigned i;

    checksum_init(frame, &checksum);

    *seektable = malloc(sizeof(unsigned) * total_tta_frames);
    if (!setjmp(*br_try(frame))) {
        for (i = 0; i < total_tta_frames; i++) {
            (*seektable)[i] = frame->read(frame, 32);
        }

        checksum_validate(frame, &checksum);
        br_etry(frame);
    } else {
        checksum_clear(frame);
        br_etry(frame);
        return IO_ERROR;
    }

    return checksum.is_valid ? OK : CRC_MISMATCH;
}

static unsigned
tta_block_size(unsigned current_tta_frame, const struct tta_header *header)
{
    if ((current_tta_frame + 1) < header->total_tta_frames) {
        return header->default_block_size;
    } else if ((header->total_pcm_frames % header->default_block_size) == 0) {
        return header->default_block_size;
    } else {
        return header->total_pcm_frames % header->default_block_size;
    }
}

static status_t
read_tta_frame(BitstreamReader *frame,
               unsigned channels,
               unsigned bits_per_sample,
               unsigned block_size,
               int samples[])
{
    checksum_t checksum;
    struct residual_params residual_params[channels];
    struct filter_params filter_params[channels];
    struct prediction_params prediction_params[channels];
    unsigned c;

    /*initialize per-channel parameters*/
    for (c = 0; c < channels; c++) {
        init_residual_params(&residual_params[c]);
        init_filter_params(bits_per_sample, &filter_params[c]);
        init_prediction_params(bits_per_sample, &prediction_params[c]);
    }

    checksum_init(frame, &checksum);

    if (!setjmp(*br_try(frame))) {
        /*decode one PCM frame at a time*/
        for (; block_size; block_size--) {
            int predicted[channels];

            for (c = 0; c < channels; c++) {
                /*run fixed prediction over filtered value*/
                predicted[c] = run_prediction(
                    &prediction_params[c],
                    /*run hybrid filter over residual*/
                    run_filter(
                        &filter_params[c],
                        /*decode a residual*/
                        read_residual(
                            &residual_params[c],
                            frame)));
            }

            /*decorrelate channels to samples*/
            decorrelate_channels(channels,
                                 predicted,
                                 samples);

            /*move on to next batch of samples*/
            samples += channels;
        }

        frame->byte_align(frame);
        checksum_validate(frame, &checksum);
        br_etry(frame);
    } else {
        checksum_clear(frame);
        br_etry(frame);
        return IO_ERROR;
    }

    return checksum.is_valid ? OK : CRC_MISMATCH;
}

static void
init_residual_params(struct residual_params *params)
{
    params->k0 = params->k1 = 10;
    params->sum0 = params->sum1 = 1 << 14;
}

static inline int
adjustment(unsigned sum, unsigned k)
{
    if ((k > 0) && (1 << (k + 4) > sum)) {
        return -1;
    } else if (sum > (1 << (k + 5))) {
        return 1;
    } else {
        return 0;
    }
}

static int
read_residual(struct residual_params *params, BitstreamReader *frame)
{
    const unsigned MSB = frame->read_unary(frame, 0);
    int unsigned_;
    int residual;

    if (MSB) {
        const unsigned LSB = frame->read(frame, params->k1);
        const unsigned unshifted = ((MSB - 1) << params->k1) | LSB;
        unsigned_ = unshifted + (1 << params->k0);
        params->sum1 += (unshifted - (params->sum1 >> 4));
        params->k1 += adjustment(params->sum1, params->k1);
    } else {
        unsigned_ = frame->read(frame, params->k0);
    }

    if (unsigned_ % 2) {
        residual = (unsigned_ + 1) >> 1;
    } else {
        residual = -(unsigned_ >> 1);
    }
    params->sum0 += (unsigned_ - (params->sum0 >> 4));
    params->k0 += adjustment(params->sum0, params->k0);

    return residual;
}

static void
init_filter_params(unsigned bits_per_sample,
                   struct filter_params *params)
{
    switch (bits_per_sample) {
    case 8:
        params->shift = 10;
        break;
    case 16:
        params->shift = 9;
        break;
    case 24:
        params->shift = 10;
        break;
    }
    params->previous_residual = 0;
    params->round = 1 << (params->shift - 1);
    params->qm[0] =
    params->qm[1] =
    params->qm[2] =
    params->qm[3] =
    params->qm[4] =
    params->qm[5] =
    params->qm[6] =
    params->qm[7] = 0;
    params->dx[0] =
    params->dx[1] =
    params->dx[2] =
    params->dx[3] =
    params->dx[4] =
    params->dx[5] =
    params->dx[6] =
    params->dx[7] = 0;
    params->dl[0] =
    params->dl[1] =
    params->dl[2] =
    params->dl[3] =
    params->dl[4] =
    params->dl[5] =
    params->dl[6] =
    params->dl[7] = 0;
}

static inline int
sign(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}

static int
run_filter(struct filter_params *params, int residual)
{
    const int previous_sign = sign(params->previous_residual);
    int32_t sum = params->round;
    int filtered = residual;

    params->previous_residual = residual;

    sum += params->dl[0] * (params->qm[0] += previous_sign * params->dx[0]);
    sum += params->dl[1] * (params->qm[1] += previous_sign * params->dx[1]);
    sum += params->dl[2] * (params->qm[2] += previous_sign * params->dx[2]);
    sum += params->dl[3] * (params->qm[3] += previous_sign * params->dx[3]);
    sum += params->dl[4] * (params->qm[4] += previous_sign * params->dx[4]);
    sum += params->dl[5] * (params->qm[5] += previous_sign * params->dx[5]);
    sum += params->dl[6] * (params->qm[6] += previous_sign * params->dx[6]);
    sum += params->dl[7] * (params->qm[7] += previous_sign * params->dx[7]);

    filtered += (sum >> params->shift);

    params->dx[0] = params->dx[1];
    params->dx[1] = params->dx[2];
    params->dx[2] = params->dx[3];
    params->dx[3] = params->dx[4];
    params->dx[4] = params->dl[4] >= 0 ? 1 : -1;
    params->dx[5] = params->dl[5] >= 0 ? 2 : -2;
    params->dx[6] = params->dl[6] >= 0 ? 2 : -2;
    params->dx[7] = params->dl[7] >= 0 ? 4 : -4;
    params->dl[0] = params->dl[1];
    params->dl[1] = params->dl[2];
    params->dl[2] = params->dl[3];
    params->dl[3] = params->dl[4];
    params->dl[4] =
        -(params->dl[5]) + (-(params->dl[6]) + (filtered - params->dl[7]));
    params->dl[5] = -(params->dl[6]) + (filtered - params->dl[7]);
    params->dl[6] = filtered - params->dl[7];
    params->dl[7] = filtered;

    return filtered;
}

static void
init_prediction_params(unsigned bits_per_sample,
                       struct prediction_params *params)
{
    switch (bits_per_sample) {
    case 8:
        params->shift = 4;
        break;
    case 16:
        params->shift = 5;
        break;
    case 24:
        params->shift = 5;
        break;
    }
    params->previous_sample = 0;
}

static int
run_prediction(struct prediction_params *params, int filtered)
{
    const int predicted =
        filtered + (((params->previous_sample << params->shift) -
                    params->previous_sample) >> params->shift);
    params->previous_sample = predicted;
    return predicted;
}

static void
decorrelate_channels(unsigned channel_count,
                     const int predicted[],
                     int samples[])
{
    if (channel_count == 1) {
        samples[0] = predicted[0];
    } else if (channel_count > 1) {
        samples[channel_count - 1] =
            predicted[channel_count - 1] +
            (predicted[channel_count - 2] / 2);
        for (channel_count--; channel_count; channel_count--) {
            samples[channel_count - 1] =
                samples[channel_count] - predicted[channel_count - 1];
        }
    }
}

#ifndef STANDALONE
static PyObject*
tta_exception(status_t error)
{
    switch (error) {
    case OK:
    default:
    case CRC_MISMATCH:
    case INVALID_SIGNATURE:
    case INVALID_FORMAT:
        return PyExc_ValueError;
    case IO_ERROR:
    case FRAME_TOO_SMALL:
        return PyExc_IOError;
    }
}
#endif

static const char*
tta_strerror(status_t error)
{
    switch (error) {
    case OK:
    default:
        return "no error";
    case IO_ERROR:
        return "I/O error";
    case CRC_MISMATCH:
        return "CRC-32 mismatch";
    case FRAME_TOO_SMALL:
        return "frame too small";
    case INVALID_SIGNATURE:
        return "invalid file signature";
    case INVALID_FORMAT:
        return "invalid file format";
    }
}

#ifdef STANDALONE

int
main(int argc, char *argv[])
{
    FILE *file;
    BitstreamReader *input;
    status_t status;
    struct tta_header header;
    unsigned current_tta_frame;
    unsigned *seektable = NULL;
    int_to_pcm_f convert;
    int *samples = NULL;
    unsigned char *pcm_samples = NULL;

    if (argc < 2) {
        fputs("*** Usage: ttadec <file.tta>\n", stderr);
        return 1;
    }

    errno = 0;
    if ((file = fopen(argv[1], "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", argv[1], strerror(errno));
        return 1;
    } else {
        input = br_open(file, BS_LITTLE_ENDIAN);
    }

    /*read and validate header*/
    if ((status = read_header(input, &header)) != OK) {
        fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
        goto error;
    }

    /*calculate parameters from header*/
    samples = malloc(sizeof(int) *
                     header.default_block_size *
                     header.channels);
    pcm_samples = malloc(sizeof(unsigned char) *
                         header.default_block_size *
                         header.channels *
                         (header.bits_per_sample / 8));
    convert = int_to_pcm_converter(header.bits_per_sample, 0, 1);

    /*read seektable for frame sizes*/
    if ((status = read_seektable(input,
                                 header.total_tta_frames,
                                 &seektable)) != OK) {
        fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
        goto error;
    }

    /*process all frames in file*/
    for (current_tta_frame = 0;
         current_tta_frame < header.total_tta_frames;
         current_tta_frame++) {
        const unsigned block_size = tta_block_size(current_tta_frame, &header);

        if ((status = read_tta_frame(input,
                                     header.channels,
                                     header.bits_per_sample,
                                     block_size,
                                     samples)) != OK) {
            fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
            goto error;
        } else {
            const unsigned total_samples = header.channels * block_size;

            convert(total_samples, samples, pcm_samples);

            fwrite(pcm_samples,
                   sizeof(unsigned char),
                   block_size * header.channels * (header.bits_per_sample / 8),
                   stdout);
        }
    }

    input->close(input);
    free(seektable);
    free(samples);
    free(pcm_samples);
    return 0;
error:
    input->close(input);
    free(seektable);
    free(samples);
    free(pcm_samples);
    return 1;
}

#endif
