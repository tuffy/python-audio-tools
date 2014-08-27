#include "alsa.h"
#include "../pcmconv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger
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
    self->output = NULL;
    self->mixer = NULL;
    self->mixer_elem = NULL;
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
        self->buffer.int16 = NULL;
        output_format = SND_PCM_FORMAT_S16;
        break;
    case 24:
        self->bits_per_sample = bits_per_sample;
        self->buffer.float32 = NULL;
        output_format = SND_PCM_FORMAT_FLOAT;
        break;
    default:
        PyErr_SetString(
            PyExc_ValueError, "bits-per-sample must be 8, 16 or 24");
        return -1;
    }

    if ((error = snd_pcm_open(&self->output,
                              device,
                              SND_PCM_STREAM_PLAYBACK,
                              0)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to open ALSA output handle");
        return -1;
    }

    if ((error = snd_pcm_set_params(self->output,
                                    output_format,
                                    SND_PCM_ACCESS_RW_INTERLEAVED,
                                    channels,
                                    sample_rate,
                                    1,
                                    500000)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to set ALSA stream parameters");
        return -1;
    }

    if ((error = snd_mixer_open(&self->mixer, 0)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to open ALSA mixer");
        return -1;
    } else if ((error = snd_mixer_attach(self->mixer, device)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to attach ALSA mixer to card");
        return -1;
    } else if ((error = snd_mixer_selem_register(self->mixer,
                                                 NULL,
                                                 NULL)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to register ALSA mixer");
        return -1;
    } else if ((error = snd_mixer_load(self->mixer)) < 0) {
        PyErr_SetString(PyExc_IOError, "unable to load ALSA mixer");
        return -1;
    }

    /*walk through mixer elements to find Master or PCM*/
    self->mixer_elem = find_playback_mixer_element(self->mixer, "Master");
    if (self->mixer_elem == NULL) {
        /*this may be NULL if no Master or PCM found*/
        self->mixer_elem = find_playback_mixer_element(self->mixer, "PCM");
    }
    if (self->mixer_elem != NULL) {
        snd_mixer_selem_get_playback_volume_range(self->mixer_elem,
                                                  &self->volume_min,
                                                  &self->volume_max);
    }

    return 0;
}

static snd_mixer_elem_t*
find_playback_mixer_element(snd_mixer_t *mixer, const char *name)
{
    snd_mixer_elem_t *mixer_elem;

    for (mixer_elem = snd_mixer_first_elem(mixer);
         mixer_elem != NULL;
         mixer_elem = snd_mixer_elem_next(mixer_elem)) {
        const char *elem_name = snd_mixer_selem_get_name(mixer_elem);
        if ((elem_name != NULL) &&
            snd_mixer_selem_has_playback_volume(mixer_elem) &&
            (!strcmp(name, elem_name))) {
            return mixer_elem;
        }
    }

    return NULL;
}


void ALSAAudio_dealloc(output_ALSAAudio *self)
{
    Py_XDECREF(self->framelist_type);

    if (self->output != NULL)
        snd_pcm_close(self->output);
    if (self->mixer != NULL)
        snd_mixer_close(self->mixer);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* ALSAAudio_play(output_ALSAAudio *self, PyObject *args)
{
    PyObject *framelist_obj;
    pcm_FrameList *framelist;
    unsigned i;
    snd_pcm_uframes_t to_write;
    snd_pcm_sframes_t frames_written;
    PyThreadState *state;

    if (!PyArg_ParseTuple(args, "O", &framelist_obj))
        return NULL;

    /*ensure object is a FrameList*/
    if (Py_TYPE(framelist_obj) != (PyTypeObject*)self->framelist_type) {
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

    state = PyEval_SaveThread();

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
            frames_written = snd_pcm_writei(self->output,
                                            self->buffer.int8,
                                            to_write);
            if (frames_written < 0) {
                /*try to recover a single time*/
                frames_written = snd_pcm_recover(self->output,
                                                 frames_written,
                                                 1);
            }
            if (frames_written >= 0) {
                to_write -= frames_written;
            } else {
                switch (-frames_written) {
                case EBADFD:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "PCM not in correct state");
                    return NULL;
                case EPIPE:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "buffer underrun occurred");
                    return NULL;
                case ESTRPIPE:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "suspend event occurred");
                    return NULL;
                default:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "unknown ALSA write error");
                    return NULL;
                }
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
            frames_written = snd_pcm_writei(self->output,
                                            self->buffer.int16,
                                            to_write);
            if (frames_written < 0) {
                /*try to recover a single time*/
                frames_written = snd_pcm_recover(self->output,
                                                 frames_written,
                                                 1);
            }
            if (frames_written >= 0) {
                to_write -= frames_written;
            } else {
                switch (-frames_written) {
                case EBADFD:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "PCM not in correct state");
                    return NULL;
                case EPIPE:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "buffer underrun occurred");
                    return NULL;
                case ESTRPIPE:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "suspend event occurred");
                    return NULL;
                default:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "unknown ALSA write error");
                    return NULL;
                }
            }
        }
        break;
    case 24:
        /*resize internal buffer if needed*/
        if (self->buffer_size < framelist->samples_length) {
            self->buffer_size = framelist->samples_length;
            self->buffer.float32 = realloc(self->buffer.float32,
                                           self->buffer_size * sizeof(float));
        }

        /*transfer framelist data to buffer*/
        for (i = 0; i < framelist->samples_length; i++) {
            const float v = framelist->samples[i];
            self->buffer.float32[i] = v / (1 << 23);
        }

        /*output data to ALSA*/
        while (to_write > 0) {
            frames_written = snd_pcm_writei(self->output,
                                            self->buffer.float32,
                                            to_write);
            if (frames_written < 0) {
                /*try to recover a single time*/
                frames_written = snd_pcm_recover(self->output,
                                                 frames_written,
                                                 1);
            }
            if (frames_written >= 0) {
                to_write -= frames_written;
            } else {
                switch (-frames_written) {
                case EBADFD:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "PCM not in correct state");
                    return NULL;
                case EPIPE:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "buffer underrun occurred");
                    return NULL;
                case ESTRPIPE:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "suspend event occurred");
                    return NULL;
                default:
                    PyEval_RestoreThread(state);
                    PyErr_SetString(PyExc_IOError,
                                    "unknown ALSA write error");
                    return NULL;
                }
            }
        }
        break;
    default:
        /*shouldn't get here*/
        break;
    }

    PyEval_RestoreThread(state);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_pause(output_ALSAAudio *self, PyObject *args)
{
    snd_pcm_pause(self->output, 1);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_resume(output_ALSAAudio *self, PyObject *args)
{
    snd_pcm_pause(self->output, 0);

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
    if (self->mixer_elem != NULL) {
        /*get the average volume from all supported output channels*/
        const snd_mixer_selem_channel_id_t channels[] = {
            SND_MIXER_SCHN_FRONT_LEFT,
            SND_MIXER_SCHN_FRONT_RIGHT,
            SND_MIXER_SCHN_REAR_LEFT,
            SND_MIXER_SCHN_REAR_RIGHT,
            SND_MIXER_SCHN_FRONT_CENTER,
            SND_MIXER_SCHN_WOOFER,
            SND_MIXER_SCHN_SIDE_LEFT,
            SND_MIXER_SCHN_SIDE_RIGHT,
            SND_MIXER_SCHN_REAR_CENTER};
        const size_t channel_count =
            sizeof(channels) / sizeof(snd_mixer_selem_channel_id_t);
        size_t i;
        double total_volume = 0.0;
        unsigned total_channels = 0;

        for (i = 0; i < channel_count; i++) {
            long channel_volume;
            if (snd_mixer_selem_has_playback_channel(self->mixer_elem,
                                                     channels[i]) &&
                (snd_mixer_selem_get_playback_volume(self->mixer_elem,
                                                     channels[i],
                                                     &channel_volume) == 0)) {
                total_volume += channel_volume;
                total_channels++;
            }
        }

        if (total_channels > 0) {
            const double average_volume = total_volume / total_channels;

            /*convert to range min_volume->max_volume*/
            return PyFloat_FromDouble(average_volume / self->volume_max);
        } else {
            return PyFloat_FromDouble(0.0);
        }
    } else {
        return PyFloat_FromDouble(0.0);
    }
}

static PyObject* ALSAAudio_set_volume(output_ALSAAudio *self, PyObject *args)
{
    double new_volume_d;
    long new_volume;

    if (!PyArg_ParseTuple(args, "d", &new_volume_d))
        return NULL;

    new_volume = round(new_volume_d * self->volume_max);

    snd_mixer_selem_set_playback_volume_all(self->mixer_elem, new_volume);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject* ALSAAudio_close(output_ALSAAudio *self, PyObject *args)
{
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}
