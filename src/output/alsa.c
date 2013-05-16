#include "alsa.h"
#include "../pcmconv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger
 further modified by Brian Langenberger for use in Python Audio Tools

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

static PyObject* ALSAAudio_new(PyTypeObject *type,
                               PyObject *args,
                               PyObject *kwds)
{
    output_ALSAAudio *self;

    self = (output_ALSAAudio *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int ALSAAudio_init(output_ALSAAudio *self, PyObject *args, PyObject *kwds)
{
    PyObject *audiotools_pcm = NULL;
    char *device;
    int sample_rate = 44100;
    int channels = 2;
    int bits_per_sample = 16;
    int error;
    snd_pcm_format_t output_format = SND_PCM_FORMAT_S16_LE;

    self->framelist_type = NULL;
    self->handle = NULL;
    self->buffer_size = 0;

    /*get FrameList type for comparison during .play() operation*/
    if ((audiotools_pcm = open_audiotools_pcm()) != NULL) {
        self->framelist_type = PyObject_GetAttrString(audiotools_pcm,
                                                      "FrameList");
        Py_DECREF(audiotools_pcm);
        if (self->framelist_type == NULL) {
            /*unable to get audiotools.pcm.FrameList type*/
            return -1;
        }
    } else {
        /*unable to open audiotools.pcm module*/
        return -1;
    }

    if (!PyArg_ParseTuple(args, "siii",
                          &device,
                          &sample_rate,
                          &channels,
                          &bits_per_sample))
        return -1;

    /*sanity check output parameters*/
    if (sample_rate > 0) {
        self->sample_rate = sample_rate;
    } else {
        PyErr_SetString(
            PyExc_ValueError, "sample rate must be a postive value");
        return -1;
    }

    if (channels > 0) {
        self->channels = channels;
    } else {
        PyErr_SetString(
            PyExc_ValueError, "channels must be a positive value");
        return -1;
    }

    switch (bits_per_sample) {
    case 8:
        self->bits_per_sample = bits_per_sample;
        self->buffer.int8 = NULL;
        output_format = SND_PCM_FORMAT_S8;
        break;
    case 16:
        self->bits_per_sample = bits_per_sample;
        self->buffer.int8 = NULL;
        output_format = SND_PCM_FORMAT_S16;
        break;
    case 24:
        self->bits_per_sample = bits_per_sample;
        self->buffer.int8 = NULL;
        output_format = SND_PCM_FORMAT_S24;
        break;
    default:
        PyErr_SetString(
            PyExc_ValueError, "bits-per-sample must be 8, 16 or 24");
        return -1;
    }

    if ((error = snd_pcm_open(&self->handle,
                              device,
                              SND_PCM_STREAM_PLAYBACK,
                              0)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to open ALSA handle");
        return -1;
    }
    if ((error = snd_pcm_set_params(self->handle,
                                    output_format,
                                    SND_PCM_ACCESS_RW_INTERLEAVED,
                                    channels,
                                    sample_rate,
                                    1,
                                    500000)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to set ALSA stream parameters");
        return -1;
    }

    return 0;
}

void ALSAAudio_dealloc(output_ALSAAudio *self)
{
    Py_XDECREF(self->framelist_type);

    if (self->handle != NULL)
        snd_pcm_close(self->handle);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject* ALSAAudio_play(output_ALSAAudio *self, PyObject *args)
{
    PyObject *framelist_obj;
    pcm_FrameList *framelist;
    unsigned i;
    snd_pcm_uframes_t to_write;

    if (!PyArg_ParseTuple(args, "O", &framelist_obj))
        return NULL;

    /*ensure object is a FrameList*/
    if (framelist_obj->ob_type != (PyTypeObject*)self->framelist_type) {
        PyErr_SetString(PyExc_TypeError,
                        "argument must be FrameList object");
        return NULL;
    } else {
        framelist = (pcm_FrameList*)framelist_obj;
    }

    if (framelist->bits_per_sample != self->bits_per_sample) {
        PyErr_SetString(PyExc_ValueError,
                        "FrameList has different bits_per_sample than stream");
        return NULL;
    }

    if (framelist->channels != self->channels) {
        PyErr_SetString(PyExc_ValueError,
                        "FrameList has different channels than stream");
        return NULL;
    }

    to_write = framelist->frames;

    switch (self->bits_per_sample) {
    case 8:
        /*resize internal buffer if needed*/
        if (self->buffer_size < framelist->samples_length) {
            self->buffer_size = framelist->samples_length;
            self->buffer.int8 = realloc(self->buffer.int8,
                                        self->buffer_size * sizeof(int8_t));
        }

        /*transfer framelist data to buffer*/
        for (i = 0; i < framelist->samples_length; i++) {
            self->buffer.int8[i] = framelist->samples[i];
        }

        /*output data to ALSA*/
        while (to_write > 0) {
            const snd_pcm_sframes_t frames_written =
                snd_pcm_writei(self->handle, self->buffer.int8, to_write);
            if (frames_written >= 0) {
                to_write -= frames_written;
            } else {
                PyErr_SetString(PyExc_IOError, "error writing frame to output");
                return NULL;
            }
        }
        break;
    case 16:
        /*resize internal buffer if needed*/
        if (self->buffer_size < framelist->samples_length) {
            self->buffer_size = framelist->samples_length;
            self->buffer.int16 = realloc(self->buffer.int16,
                                         self->buffer_size * sizeof(int16_t));
        }

        /*transfer framelist data to buffer*/
        for (i = 0; i < framelist->samples_length; i++) {
            self->buffer.int16[i] = framelist->samples[i];
        }

        /*output data to ALSA*/
        while (to_write > 0) {
            const snd_pcm_sframes_t frames_written =
                snd_pcm_writei(self->handle, self->buffer.int16, to_write);
            if (frames_written >= 0) {
                to_write -= frames_written;
            } else {
                PyErr_SetString(PyExc_IOError, "error writing frame to output");
                return NULL;
            }
        }
        break;
    case 24:
        /*resize internal buffer if needed*/
        if (self->buffer_size < framelist->samples_length) {
            self->buffer_size = framelist->samples_length;
            self->buffer.int24 = realloc(self->buffer.int24,
                                         self->buffer_size * sizeof(int32_t));
        }

        /*transfer framelist data to buffer*/
        for (i = 0; i < framelist->samples_length; i++) {
            self->buffer.int24[i] = framelist->samples[i];
        }

        /*output data to ALSA*/
        while (to_write > 0) {
            const snd_pcm_sframes_t frames_written =
                snd_pcm_writei(self->handle, self->buffer.int24, to_write);
            if (frames_written >= 0) {
                to_write -= frames_written;
            } else {
                PyErr_SetString(PyExc_IOError, "error writing frame to output");
                return NULL;
            }
        }
        break;
    default:
        /*shouldn't get here*/
        break;
    }

    /* frames = snd_pcm_writei(self->handle, data, data_len); */

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_pause(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_resume(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_flush(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_get_volume(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    return PyFloat_FromDouble(0.0);
}

static PyObject* ALSAAudio_set_volume(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_close(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}





