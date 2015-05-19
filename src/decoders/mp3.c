#include "mp3.h"
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

static PyObject*
MP3Decoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds)
{
    decoders_MP3Decoder *self;

    self = (decoders_MP3Decoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
MP3Decoder_init(decoders_MP3Decoder *self,
                PyObject *args, PyObject *kwds)
{
    char *filename;
    int error;

    self->handle = NULL;

    self->channels = 0;
    self->rate = 0;
    self->encoding = 0;
    self->closed = 0;

    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    if ((self->handle = mpg123_new(NULL, &error)) == NULL) {
        PyErr_SetString(PyExc_ValueError, "error initializing decoder");
        return -1;
    }

    if ((error = mpg123_open(self->handle, filename)) != MPG123_OK) {
        PyErr_SetString(PyExc_ValueError, "error opening file");
        return -1;
    }

    if ((error = mpg123_getformat(self->handle,
                                  &(self->rate),
                                  &(self->channels),
                                  &(self->encoding))) != MPG123_OK) {
        PyErr_SetString(PyExc_ValueError, "error getting file format");
        return -1;
    }

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
MP3Decoders_dealloc(decoders_MP3Decoder *self)
{
    if (self->handle != NULL) {
        mpg123_close(self->handle);
        mpg123_delete(self->handle);
    }

    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
MP3Decoder_sample_rate(decoders_MP3Decoder *self, void *closure)
{
    return Py_BuildValue("l", self->rate);
}

static PyObject*
MP3Decoder_bits_per_sample(decoders_MP3Decoder *self, void *closure)
{
    return Py_BuildValue("i", 16);
}

static PyObject*
MP3Decoder_channels(decoders_MP3Decoder *self, void *closure)
{
    return Py_BuildValue("i", self->channels);
}

static PyObject*
MP3Decoder_channel_mask(decoders_MP3Decoder *self, void *closure)
{
    switch (self->channels) {
    case 1:
        return Py_BuildValue("i", 0x4);
    case 2:
        return Py_BuildValue("i", 0x3);
    default:
        return Py_BuildValue("i", 0);
    }
}

#define BUFFER_SIZE 4608
#define BITS_PER_SAMPLE 16

static PyObject*
MP3Decoder_read(decoders_MP3Decoder* self, PyObject *args)
{
    pcm_FrameList *framelist;
    int *samples;
    static int16_t buffer[BUFFER_SIZE];
    size_t buffer_size;
    size_t i;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "stream is closed");
        return NULL;
    }

    /*perform mpg123_read() to output buffer*/
    switch (mpg123_read(self->handle,
                        (unsigned char*)buffer,
                        BUFFER_SIZE,
                        &buffer_size)) {
    case MPG123_DONE:
        /*return empty framelist*/
        return empty_FrameList(self->audiotools_pcm,
                               self->channels,
                               16);
    case MPG123_OK:
        framelist = new_FrameList(self->audiotools_pcm,
                                  self->channels,
                                  BITS_PER_SAMPLE,
                                  (unsigned)(buffer_size / 2 / self->channels));

        samples = framelist->samples;

        for (i = 0; i < (buffer_size / 2); i++) {
            samples[i] = buffer[i];
        }

        return (PyObject*)framelist;
    default:
        /*raise exception*/
        PyErr_SetString(PyExc_ValueError, "error decoding MP3 frame");
        return NULL;
    }
}

static PyObject*
MP3Decoder_close(decoders_MP3Decoder* self, PyObject *args)
{
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MP3Decoder_enter(decoders_MP3Decoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
MP3Decoder_exit(decoders_MP3Decoder* self, PyObject *args)
{
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}
