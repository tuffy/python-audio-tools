#include "sine.h"
#include "../pcm.h"
#include "pcm.h"

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

int
Sine_Mono_init(decoders_Sine_Mono* self, PyObject *args, PyObject *kwds) {
    double f1;
    double f2;

    iaa_init(&(self->buffer), 1, 8);

    if (!PyArg_ParseTuple(args, "iiidddd",
                          &(self->bits_per_sample),
                          &(self->total_pcm_frames),
                          &(self->sample_rate),
                          &f1, &(self->a1),
                          &f2, &(self->a2)))
        return -1;

    switch (self->bits_per_sample) {
    case 8:
        self->full_scale = 0x7F;
        break;
    case 16:
        self->full_scale = 0x7FFF;
        break;
    case 24:
        self->full_scale = 0x7FFFFF;
        break;
    default:
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 8, 16, 24");
        return -1;
    }

    if (self->total_pcm_frames < 0) {
        PyErr_SetString(PyExc_ValueError, "total_pcm_frames must be >= 0");
        return -1;
    }

    if (self->sample_rate < 1) {
        PyErr_SetString(PyExc_ValueError, "sample_rate must be > 0");
        return -1;
    }

    self->remaining_pcm_frames = self->total_pcm_frames;
    self->delta1 = 2 * M_PI / (self->sample_rate / f1);
    self->delta2 = 2 * M_PI / (self->sample_rate / f2);
    self->theta1 = 0.0l;

    return 0;
}

void Sine_Mono_dealloc(decoders_Sine_Mono* self) {
    iaa_free(&(self->buffer));

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
Sine_Mono_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_Sine_Mono *self;

    self = (decoders_Sine_Mono *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}


static PyObject*
Sine_Mono_read(decoders_Sine_Mono* self, PyObject* args) {
    int byte_count;
    int frames_to_read;
    int bytes_per_frame = self->bits_per_sample / 8;
    int i;
    double d;
    ia_data_t ia;
    struct i_array* buffer1;

    if (!PyArg_ParseTuple(args, "i", &byte_count))
        return NULL;

    byte_count -= (byte_count % bytes_per_frame);
    frames_to_read = byte_count ? byte_count / bytes_per_frame : 1;
    if (frames_to_read > self->remaining_pcm_frames)
        frames_to_read = self->remaining_pcm_frames;

    iaa_reset(&(self->buffer));
    buffer1 = &(self->buffer.arrays[0]);

    for (i = 0; i < frames_to_read; i++) {
        d = ((self->a1 * sin(self->theta1)) +
             (self->a2 * sin(self->theta2))) * (double)(self->full_scale);

        ia = (ia_data_t)(d + 0.5);
        ia_append(buffer1, ia);
        self->theta1 += self->delta1;
        self->theta2 += self->delta2;
    }

    self->remaining_pcm_frames -= frames_to_read;

    return ia_array_to_framelist(&(self->buffer), self->bits_per_sample);
}

static PyObject*
Sine_Mono_close(decoders_Sine_Mono* self, PyObject* args) {
    self->remaining_pcm_frames = 0;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Sine_Mono_reset(decoders_Sine_Mono* self, PyObject* args) {
    self->remaining_pcm_frames = self->total_pcm_frames;
    self->theta1 = self->theta2 = 0.0l;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Sine_Mono_channels(decoders_Sine_Mono *self, void *closure) {
    return Py_BuildValue("i", 1);
}

static PyObject*
Sine_Mono_bits_per_sample(decoders_Sine_Mono *self, void *closure) {
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
Sine_Mono_sample_rate(decoders_Sine_Mono *self, void *closure) {
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
Sine_Mono_channel_mask(decoders_Sine_Mono *self, void *closure) {
    return Py_BuildValue("i", 0x4);
}


int
Sine_Stereo_init(decoders_Sine_Stereo* self, PyObject *args, PyObject *kwds) {
    double f1;
    double f2;

    iaa_init(&(self->buffer), 2, 8);

    if (!PyArg_ParseTuple(args, "iiiddddd",
                          &(self->bits_per_sample),
                          &(self->total_pcm_frames),
                          &(self->sample_rate),
                          &f1, &(self->a1),
                          &f2, &(self->a2),
                          &(self->fmult)))
        return -1;

    switch (self->bits_per_sample) {
    case 8:
        self->full_scale = 0x7F;
        break;
    case 16:
        self->full_scale = 0x7FFF;
        break;
    case 24:
        self->full_scale = 0x7FFFFF;
        break;
    default:
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 8, 16, 24");
        return -1;
    }

    if (self->total_pcm_frames < 0) {
        PyErr_SetString(PyExc_ValueError, "total_pcm_frames must be >= 0");
        return -1;
    }

    if (self->sample_rate < 1) {
        PyErr_SetString(PyExc_ValueError, "sample_rate must be > 0");
        return -1;
    }

    self->remaining_pcm_frames = self->total_pcm_frames;
    self->delta1 = 2 * M_PI / (self->sample_rate / f1);
    self->delta2 = 2 * M_PI / (self->sample_rate / f2);
    self->theta1 = self->theta1 = 0.0l;

    return 0;
}

void Sine_Stereo_dealloc(decoders_Sine_Stereo* self) {
    iaa_free(&(self->buffer));

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
Sine_Stereo_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_Sine_Stereo *self;

    self = (decoders_Sine_Stereo *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
Sine_Stereo_read(decoders_Sine_Stereo* self, PyObject* args) {
    int byte_count;
    int frames_to_read;
    int bytes_per_frame = 2 * (self->bits_per_sample / 8);
    int i;
    double d;
    ia_data_t ia;
    struct i_array* buffer1;
    struct i_array* buffer2;

    if (!PyArg_ParseTuple(args, "i", &byte_count))
        return NULL;

    byte_count -= (byte_count % bytes_per_frame);
    frames_to_read = byte_count ? byte_count / bytes_per_frame : 1;
    if (frames_to_read > self->remaining_pcm_frames)
        frames_to_read = self->remaining_pcm_frames;

    iaa_reset(&(self->buffer));
    buffer1 = &(self->buffer.arrays[0]);
    buffer2 = &(self->buffer.arrays[1]);

    for (i = 0; i < frames_to_read; i++) {
        d = ((self->a1 * sin(self->theta1)) +
             (self->a2 * sin(self->theta2))) * (double)(self->full_scale);
        ia = (ia_data_t)(d + 0.5);
        ia_append(buffer1, ia);
        d = -((self->a1 * sin(self->theta1 * self->fmult)) +
              (self->a2 * sin(self->theta2 * self->fmult))) *
            (double)(self->full_scale);
        ia = (ia_data_t)(d + 0.5);
        ia_append(buffer2, ia);
        self->theta1 += self->delta1;
        self->theta2 += self->delta2;
    }

    self->remaining_pcm_frames -= frames_to_read;

    return ia_array_to_framelist(&(self->buffer), self->bits_per_sample);
}

static PyObject*
Sine_Stereo_close(decoders_Sine_Stereo* self, PyObject* args) {
    self->remaining_pcm_frames = 0;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Sine_Stereo_reset(decoders_Sine_Stereo* self, PyObject* args) {
    self->remaining_pcm_frames = self->total_pcm_frames;
    self->theta1 = self->theta2 = 0.0l;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Sine_Stereo_channels(decoders_Sine_Stereo *self, void *closure) {
    return Py_BuildValue("i", 2);
}

static PyObject*
Sine_Stereo_bits_per_sample(decoders_Sine_Stereo *self, void *closure) {
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
Sine_Stereo_sample_rate(decoders_Sine_Stereo *self, void *closure) {
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
Sine_Stereo_channel_mask(decoders_Sine_Stereo *self, void *closure) {
    return Py_BuildValue("i", 0x3);
}


int
Sine_Simple_init(decoders_Sine_Simple* self, PyObject *args, PyObject *kwds) {
    iaa_init(&(self->buffer), 1, 8);

    if (!PyArg_ParseTuple(args, "iiiii",
                          &(self->total_pcm_frames),
                          &(self->bits_per_sample),
                          &(self->sample_rate),
                          &(self->max_value),
                          &(self->count)))
        return -1;

    switch (self->bits_per_sample) {
    case 8:
    case 16:
    case 24:
        break;
    default:
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 8, 16, 24");
        return -1;
    }

    if (self->total_pcm_frames < 0) {
        PyErr_SetString(PyExc_ValueError, "total_pcm_frames must be >= 0");
        return -1;
    }

    if (self->sample_rate < 1) {
        PyErr_SetString(PyExc_ValueError, "sample_rate must be > 0");
        return -1;
    }


    self->remaining_pcm_frames = self->total_pcm_frames;
    self->i = 0;

    return 0;
}

void Sine_Simple_dealloc(decoders_Sine_Simple* self) {
    iaa_free(&(self->buffer));

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
Sine_Simple_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_Sine_Simple *self;

    self = (decoders_Sine_Simple *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}


static PyObject*
Sine_Simple_read(decoders_Sine_Simple* self, PyObject* args) {
    int byte_count;
    int frames_to_read;
    int bytes_per_frame = self->bits_per_sample / 8;
    int i;
    struct i_array* buffer;
    double d;
    ia_data_t ia;

    if (!PyArg_ParseTuple(args, "i", &byte_count))
        return NULL;

    iaa_reset(&(self->buffer));
    buffer = &(self->buffer.arrays[0]);

    byte_count -= (byte_count % bytes_per_frame);
    frames_to_read = byte_count ? byte_count / bytes_per_frame : 1;
    if (frames_to_read > self->remaining_pcm_frames)
        frames_to_read = self->remaining_pcm_frames;

    for (i = 0; i < frames_to_read; i++) {
        d = (double)(self->max_value) *
            sin(((M_PI * 2) *
                 (double)(self->i % self->count)) /
                (double)(self->count));
        ia = (ia_data_t)(round(d));
        ia_append(buffer, ia);
        self->i += 1;
    }

    self->remaining_pcm_frames -= frames_to_read;
    return ia_array_to_framelist(&(self->buffer), self->bits_per_sample);
}

static PyObject*
Sine_Simple_close(decoders_Sine_Simple* self, PyObject* args) {
    self->remaining_pcm_frames = 0;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Sine_Simple_reset(decoders_Sine_Simple* self, PyObject* args) {
    self->i = 0;
    self->remaining_pcm_frames = self->total_pcm_frames;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Sine_Simple_channels(decoders_Sine_Simple *self, void *closure) {
    return Py_BuildValue("i", 1);
}

static PyObject*
Sine_Simple_bits_per_sample(decoders_Sine_Simple *self, void *closure) {
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
Sine_Simple_sample_rate(decoders_Sine_Simple *self, void *closure) {
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
Sine_Simple_channel_mask(decoders_Sine_Simple *self, void *closure) {
    return Py_BuildValue("i", 0x4);
}

#include "pcm.c"
