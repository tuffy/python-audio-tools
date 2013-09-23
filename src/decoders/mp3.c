#include "mp3.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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

    self->audiotools_pcm = NULL;
    self->buffer = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    if ((self->handle = mpg123_new(NULL, NULL)) == NULL) {
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

    self->buffer = a_int_new();

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

    if (self->buffer != NULL)
        self->buffer->del(self->buffer);

    self->ob_type->tp_free((PyObject*)self);
}

/*the MP3Decoder.sample_rate attribute getter*/
static PyObject*
MP3Decoder_sample_rate(decoders_MP3Decoder *self, void *closure)
{
    return Py_BuildValue("l", self->rate);
}

/*the MP3Decoder.bits_per_sample attribute getter*/
static PyObject*
MP3Decoder_bits_per_sample(decoders_MP3Decoder *self, void *closure)
{
    return Py_BuildValue("i", 16);
}

/*the MP3Decoder.channels attribute getter*/
static PyObject*
MP3Decoder_channels(decoders_MP3Decoder *self, void *closure)
{
    return Py_BuildValue("i", self->channels);
}

/*the MP3Decoder.channel_mask attribute getter*/
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

/*the MP3Decoder.read() method*/
static PyObject*
MP3Decoder_read(decoders_MP3Decoder* self, PyObject *args)
{

    static int16_t buffer[BUFFER_SIZE];
    size_t buffer_size;
    size_t i;

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
        /*convert output buffer to FrameList object*/
        self->buffer->reset_for(self->buffer, (unsigned)(buffer_size / 2));
        for (i = 0; i < (buffer_size / 2); i++)
            a_append(self->buffer, buffer[i]);

        /*return FrameList object*/
        return a_int_to_FrameList(self->audiotools_pcm,
                                  self->buffer,
                                  self->channels,
                                  16);
    default:
        /*raise exception*/
        PyErr_SetString(PyExc_ValueError, "error decoding MP3 frame");
        return NULL;
    }
}


/*the MP3Decoder.close() method*/
static PyObject*
MP3Decoder_close(decoders_MP3Decoder* self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}
