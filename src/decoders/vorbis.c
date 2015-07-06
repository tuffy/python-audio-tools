#include "vorbis.h"
#include "../framelist.h"

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

#define BITS_PER_SAMPLE 16

PyObject*
VorbisDecoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_VorbisDecoder *self;

    self = (decoders_VorbisDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
VorbisDecoder_dealloc(decoders_VorbisDecoder *self) {
    if (self->open_ok)
        ov_clear(&(self->vorbisfile));

    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
VorbisDecoder_init(decoders_VorbisDecoder *self, PyObject *args, PyObject *kwds) {
    char* filename;
    vorbis_info* info;

    self->open_ok = 0;
    self->channel_count = 0;
    self->rate = 0;
    self->closed = 0;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    /*open file using reference Ogg Vorbis decoder*/
    switch (ov_fopen(filename, &(self->vorbisfile))) {
    case 0:
    default:
        self->open_ok = 1;
        break;
    case OV_EREAD:
        PyErr_SetString(PyExc_ValueError, "I/O error");
        return -1;
    case OV_ENOTVORBIS:
        PyErr_SetString(PyExc_ValueError, "not a Vorbis file");
        return -1;
    case OV_EVERSION:
        PyErr_SetString(PyExc_ValueError, "Vorbis version mismatch");
        return -1;
    case OV_EBADHEADER:
        PyErr_SetString(PyExc_ValueError, "invalid Vorbis bitstream header");
        return -1;
    case OV_EFAULT:
        PyErr_SetString(PyExc_ValueError, "internal logic fault");
        return -1;
    }

    /*pull stream metadata from decoder*/
    if ((info = ov_info(&(self->vorbisfile), -1)) != NULL) {
        self->channel_count = info->channels;
        self->rate = info->rate;
    } else {
        PyErr_SetString(PyExc_ValueError, "unable to get Vorbis info");
        return -1;
    }

    /*open FrameList creator*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

static PyObject*
VorbisDecoder_sample_rate(decoders_VorbisDecoder *self, void *closure) {
    return Py_BuildValue("l", self->rate);
}

static PyObject*
VorbisDecoder_bits_per_sample(decoders_VorbisDecoder *self, void *closure) {
    const int bits_per_sample = BITS_PER_SAMPLE;

    return Py_BuildValue("i", bits_per_sample);
}

static PyObject*
VorbisDecoder_channels(decoders_VorbisDecoder *self, void *closure) {
    return Py_BuildValue("i", self->channel_count);
}

static PyObject*
VorbisDecoder_channel_mask(decoders_VorbisDecoder *self, void *closure) {
    int channel_mask;

    switch (self->channel_count) {
    case 1:
        /*fC*/
        channel_mask = 0x4;
        break;
    case 2:
        /*fL fR*/
        channel_mask = 0x1 | 0x2;
        break;
    case 3:
        /*fL fR fC*/
        channel_mask = 0x1 | 0x2 | 0x4;
        break;
    case 4:
        /*fL fR bL bR*/
        channel_mask = 0x1 | 0x2 | 0x10 | 0x20;
        break;
    case 5:
        /*fL fR fC bL bR*/
        channel_mask = 0x1 | 0x2 | 0x4 | 0x10 | 0x20;
        break;
    case 6:
        /*fL fR fC LFE bL bR*/
        channel_mask = 0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20;
        break;
    case 7:
        /*fL fR fC LFE bC sL sR*/
        channel_mask = 0x1 | 0x2 | 0x4 | 0x8 | 0x100 | 0x200 | 0x400;
        break;
    case 8:
        /*fL fR fC LFE bL bR sL sR*/
        channel_mask = 0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20 | 0x200 | 0x400;
        break;
    default:
        /*undefined*/
        channel_mask = 0x0;
        break;
    }

    return Py_BuildValue("i", channel_mask);
}

static PyObject*
VorbisDecoder_read(decoders_VorbisDecoder *self, PyObject *args) {
    int current_bitstream;
    long samples_read;
    float **pcm_channels;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "stream is closed");
        return NULL;
    }

    samples_read = ov_read_float(&(self->vorbisfile),
                                 &pcm_channels,
                                 4096,
                                 &current_bitstream);

    if (samples_read >= 0) {
        /*convert floating point samples to integer-based ones*/
        pcm_FrameList *framelist;
        int *samples;
        double_to_int_f converter = double_to_int_converter(BITS_PER_SAMPLE);
        int c;

        if ((samples_read == 0) && (self->vorbisfile.os.e_o_s == 0)) {
            /*EOF encountered without EOF being marked in stream*/
            PyErr_SetString(PyExc_IOError,
                            "I/O error reading from Ogg stream");
            return NULL;
        }

        framelist = new_FrameList(self->audiotools_pcm,
                                  self->channel_count,
                                  BITS_PER_SAMPLE,
                                  (unsigned)samples_read);

        samples = framelist->samples;

        for (c = 0; c < self->channel_count; c++) {
            long sample;
            for (sample = 0; sample < samples_read; sample++) {
                put_sample(samples,
                           c,
                           self->channel_count,
                           (unsigned)sample,
                           converter(pcm_channels[c][sample]));
            }
        }

        /*reorder channels to .wav order if necessary*/
        switch (self->channel_count) {
        case 1:
        case 2:
        default:
            /*no change*/
            break;
        case 3:
            /*fL fC fR -> fL fR fC*/
            swap_channel_data(samples, 1, 2,
                              self->channel_count, (unsigned)samples_read);
            break;
        case 4:
            /*fL fR bL bR -> fL fR bL bR*/
            /*no change*/
            break;
        case 5:
            /*fL fC fR bL bR -> fL fR fC bL bR*/
            swap_channel_data(samples, 1, 2,
                              self->channel_count, (unsigned)samples_read);
            break;
        case 6:
            /*fL fC fR bL bR LFE -> fL fR fC bL bR LFE*/
            swap_channel_data(samples, 1, 2,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC bL bR LFE -> fL fR fC LFE bR bL*/
            swap_channel_data(samples, 3, 5,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC LFE bR bL -> fL fR fC LFE bL bR*/
            swap_channel_data(samples, 4, 5,
                              self->channel_count, (unsigned)samples_read);
            break;
        case 7:
            /*fL fC fR sL sR bC LFE -> fL fR fC sL sR bC LFE*/
            swap_channel_data(samples, 1, 2,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC sL sR bC LFE -> fL fR fC LFE sR bC sL*/
            swap_channel_data(samples, 3, 6,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC LFE sR bC sL -> fL fR fC LFE bC sR sL*/
            swap_channel_data(samples, 4, 5,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC LFE bC sR sL -> fL fR fC LFE bC sL sR*/
            swap_channel_data(samples, 5, 6,
                              self->channel_count, (unsigned)samples_read);
            break;
        case 8:
            /*fL fC fR sL sR bL bR LFE -> fL fR fC sL sR bL bR LFE*/
            swap_channel_data(samples, 1, 2,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC sL sR bL bR LFE -> fL fR fC LFE sR bL bR sL*/
            swap_channel_data(samples, 3, 6,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC LFE sR bL bR sL -> fL fR fC LFE bL sR bR sL*/
            swap_channel_data(samples, 4, 5,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC LFE bL sR bR sL -> fL fR fC LFE bL bR sR sL*/
            swap_channel_data(samples, 5, 6,
                              self->channel_count, (unsigned)samples_read);

            /*fL fR fC LFE bL bR sR sL -> fL fR fC LFE bL bR sL sR*/
            swap_channel_data(samples, 6, 7,
                              self->channel_count, (unsigned)samples_read);
            break;
        }

        return (PyObject*)framelist;
    } else {
        switch (samples_read) {
        case OV_HOLE:
            PyErr_SetString(PyExc_ValueError, "data interruption detected");
            return NULL;
        case OV_EBADLINK:
            PyErr_SetString(PyExc_ValueError, "invalid stream section");
            return NULL;
        case OV_EINVAL:
            PyErr_SetString(PyExc_ValueError, "initial file headers corrupt");
            return NULL;
        default:
            PyErr_SetString(PyExc_ValueError, "unspecified error");
            return NULL;
        }
    }
}

static PyObject*
VorbisDecoder_close(decoders_VorbisDecoder *self, PyObject *args) {
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
VorbisDecoder_enter(decoders_VorbisDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
VorbisDecoder_exit(decoders_VorbisDecoder* self, PyObject *args)
{
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}
