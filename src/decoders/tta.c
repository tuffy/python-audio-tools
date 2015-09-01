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

/*given a total frame size (including the 4 bytes of CRC-32),
  returns a substream of (frame_size - 4) bytes
  or NULL if an error occurs
  with "error" set accordingly*/
static BitstreamReader*
read_frame(BitstreamReader *tta_file,
           unsigned frame_size,
           status_t *status);

/*reads a TTA header from the frame to "header"
  returns OK on success, or some error value*/
static status_t
read_header(BitstreamReader *frame, struct tta_header *header);

/*returns a freshly allocated array of "total_tta_frames" frame sizes*/
static unsigned*
read_seektable(BitstreamReader *frame, unsigned total_tta_frames);

static void
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
    BitstreamReader *header;
    BitstreamReader *seektable;
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

    self->bitstream = br_open_external(
        file,
        BS_LITTLE_ENDIAN,
        4096,
        (ext_read_f)br_read_python,
        (ext_setpos_f)bs_setpos_python,
        (ext_getpos_f)bs_getpos_python,
        (ext_free_pos_f)bs_free_pos_python,
        (ext_seek_f)bs_fseek_python,
        (ext_close_f)bs_close_python,
        (ext_free_f)bs_free_python_decref);

    /*read and validate header*/
    if ((header = read_frame(self->bitstream, 22, &status)) == NULL) {
        PyErr_SetString(tta_exception(status), tta_strerror(status));
        return -1;
    } else {
        status = read_header(header, &(self->header));
        header->close(header);
        if (status != OK) {
            PyErr_SetString(tta_exception(status), tta_strerror(status));
            return -1;
        }
    }

    /*calculate some parameters from header*/
    self->default_block_size = (self->header.sample_rate * 256) / 245;
    self->total_tta_frames = div_ceil(self->header.total_pcm_frames,
                                      self->default_block_size);
    self->current_tta_frame = 0;

    /*read seektable*/
    if ((seektable = read_frame(self->bitstream,
                                4 * self->total_tta_frames + 4,
                                &status)) == NULL) {
        PyErr_SetString(tta_exception(status), tta_strerror(status));
        return -1;
    } else {
        self->seektable = read_seektable(seektable, self->total_tta_frames);
        seektable->close(seektable);
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
    } else if (self->current_tta_frame == self->total_tta_frames) {
        return empty_FrameList(self->audiotools_pcm,
                               self->header.channels,
                               self->header.bits_per_sample);
    } else {
        unsigned block_size;
        status_t status;
        BitstreamReader *tta_frame =
            read_frame(self->bitstream,
                       self->seektable[self->current_tta_frame],
                       &status);
        pcm_FrameList *framelist;

        if (!tta_frame) {
            PyErr_SetString(tta_exception(status), tta_strerror(status));
            return NULL;
        }

        if ((self->current_tta_frame + 1) < self->total_tta_frames) {
            block_size = self->default_block_size;
        } else if ((self->header.total_pcm_frames %
                    self->default_block_size) == 0) {
            block_size = self->default_block_size;
        } else {
            block_size =
                self->header.total_pcm_frames % self->default_block_size;
        }

        framelist = new_FrameList(self->audiotools_pcm,
                                  self->header.channels,
                                  self->header.bits_per_sample,
                                  block_size);

        if (!setjmp(*br_try(tta_frame))) {
            read_tta_frame(tta_frame,
                           self->header.channels,
                           self->header.bits_per_sample,
                           block_size,
                           framelist->samples);

            br_etry(tta_frame);
            tta_frame->close(tta_frame);

            self->current_tta_frame += 1;

            return (PyObject*)framelist;
        } else {
            /*this implies the frame size in the seektable was read correctly,
              the TTA frame itself was read correctly,
              and it *still* had a read error during decoding
              which means there's either something wrong with the
              residual decoding function or the file is malicious*/

            br_etry(tta_frame);
            tta_frame->close(tta_frame);
            Py_DECREF((PyObject*)framelist);
            PyErr_SetString(tta_exception(IO_ERROR), tta_strerror(IO_ERROR));
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

        while (seeked_offset > self->default_block_size) {
            if (self->current_tta_frame < self->total_tta_frames) {
                const unsigned frame_size =
                    self->seektable[self->current_tta_frame];

                self->bitstream->seek(self->bitstream,
                                      (long)frame_size,
                                      BS_SEEK_CUR);

                current_pcm_frame += self->default_block_size;
                self->current_tta_frame++;
                seeked_offset -= self->default_block_size;
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

static BitstreamReader*
read_frame(BitstreamReader *tta_file,
           unsigned frame_size,
           status_t *status)
{
    uint32_t calculated_checksum = 0xFFFFFFFF;
    BitstreamReader *frame;

    if (frame_size <= 4) {
        *status = FRAME_TOO_SMALL;
        return NULL;
    }

    /*get the main data chunk to be returned*/
    tta_file->add_callback(tta_file,
                           (bs_callback_f)tta_crc32,
                           &calculated_checksum);
    if (!setjmp(*br_try(tta_file))) {
        frame = tta_file->substream(tta_file, frame_size - 4);
        br_etry(tta_file);
        tta_file->pop_callback(tta_file, NULL);
    } else {
        /*some I/O error getting the whole frame*/
        br_etry(tta_file);
        tta_file->pop_callback(tta_file, NULL);
        *status = IO_ERROR;
        return NULL;
    }

    /*validate CRC-32 at end of frame*/
    if (!setjmp(*br_try(tta_file))) {
        uint32_t frame_checksum = tta_file->read(tta_file, 32);
        br_etry(tta_file);

        if (frame_checksum == (calculated_checksum ^ 0xFFFFFFFF)) {
            return frame;
        } else {
            frame->close(frame);
            *status = CRC_MISMATCH;
            return NULL;
        }
    } else {
        /*some I/O error getting the checksum bytes*/
        br_etry(tta_file);
        frame->close(frame);
        *status = IO_ERROR;
        return NULL;
    }
}

static status_t
read_header(BitstreamReader *frame, struct tta_header *header)
{
    uint8_t signature[4];
    unsigned format;

    frame->parse(frame, "4b 3*16u 2*32u",
                 signature,
                 &format,
                 &(header->channels),
                 &(header->bits_per_sample),
                 &(header->sample_rate),
                 &(header->total_pcm_frames));

    if (memcmp(signature, "TTA1", 4)) {
        return INVALID_SIGNATURE;
    } else if (format != 1) {
        return INVALID_FORMAT;
    } else {
        return OK;
    }
}

/*returns a freshly allocated array of "total_tta_frames" frame sizes*/
static unsigned*
read_seektable(BitstreamReader *frame, unsigned total_tta_frames)
{
    unsigned *seektable = malloc(sizeof(unsigned) * total_tta_frames);
    unsigned i;

    for (i = 0; i < total_tta_frames; i++) {
        seektable[i] = frame->read(frame, 32);
    }

    return seektable;
}

static void
read_tta_frame(BitstreamReader *frame,
               unsigned channels,
               unsigned bits_per_sample,
               unsigned block_size,
               int samples[])
{
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
    BitstreamReader *packet;
    status_t status;
    struct tta_header header;
    unsigned default_block_size;
    unsigned total_tta_frames;
    unsigned current_tta_frame;
    unsigned *seektable = NULL;
    int_to_pcm_f converter;

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
    if ((packet = read_frame(input, 22, &status)) != NULL) {
        status = read_header(packet, &header);
        packet->close(packet);
        if (status != OK) {
            fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
            goto error;
        }
    } else {
        fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
        goto error;
    }

    /*calculate parameters from header*/
    default_block_size = (header.sample_rate * 256) / 245;
    total_tta_frames = div_ceil(header.total_pcm_frames, default_block_size);
    converter = int_to_pcm_converter(header.bits_per_sample, 0, 1);

    /*read seektable for frame sizes*/
    if ((packet = read_frame(input,
                             4 * total_tta_frames + 4,
                             &status)) != NULL) {
        seektable = read_seektable(packet, total_tta_frames);
        packet->close(packet);
    } else {
        fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
        goto error;
    }

    /*process all frames in file*/
    for (current_tta_frame = 0;
         current_tta_frame < total_tta_frames;
         current_tta_frame++) {
        unsigned block_size;

        if ((packet = read_frame(input,
                                 seektable[current_tta_frame],
                                 &status)) == NULL) {
            fprintf(stderr, "*** Error: %s\n", tta_strerror(status));
            goto error;
        }

        /*decode all samples in frame*/
        if ((current_tta_frame + 1) < total_tta_frames) {
            block_size = default_block_size;
        } else if ((header.total_pcm_frames % default_block_size) == 0) {
            block_size = default_block_size;
        } else {
            block_size = header.total_pcm_frames % default_block_size;
        }

        if (!setjmp(*br_try(packet))) {
            struct residual_params residual_params[header.channels];
            struct filter_params filter_params[header.channels];
            struct prediction_params prediction_params[header.channels];
            unsigned c;

            /*initialize per-channel parameters*/
            for (c = 0; c < header.channels; c++) {
                init_residual_params(&residual_params[c]);
                init_filter_params(header.bits_per_sample,
                                   &filter_params[c]);
                init_prediction_params(header.bits_per_sample,
                                       &prediction_params[c]);
            }

            for (; block_size; block_size--) {
                int predicted[header.channels];
                int samples[header.channels];
                unsigned char pcm_samples[header.channels *
                                          (header.bits_per_sample / 8)];

                for (c = 0; c < header.channels; c++) {
                    /*run fixed prediction over filtered value*/
                    predicted[c] = run_prediction(
                        &prediction_params[c],
                        /*run hybrid filter over residual*/
                        run_filter(
                            &filter_params[c],
                            /*decode a residual*/
                            read_residual(
                                &residual_params[c],
                                packet)));
                }

                /*decorrelate channels to samples*/
                decorrelate_channels(header.channels, predicted, samples);

                /*convert samples to raw bytes*/
                converter(header.channels, samples, pcm_samples);

                /*output samples to stdout*/
                fwrite(pcm_samples, sizeof(pcm_samples), 1, stdout);
            }

            br_etry(packet);
            packet->close(packet);
        } else {
            br_etry(packet);
            packet->close(packet);
            fputs("*** Error: I/O error reading audio packet\n", stderr);
            goto error;
        }

    }

    input->close(input);
    free(seektable);
    return 0;
error:
    input->close(input);
    free(seektable);
    return 1;
}

#endif
