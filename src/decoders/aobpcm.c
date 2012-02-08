#include "aobpcm.h"

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
AOBPCMDecoder_init(decoders_AOBPCMDecoder *self,
                   PyObject *args, PyObject *kwds) {
    PyObject *reader;
    int i;

    self->reader = NULL;
    self->buffer = NULL;

    if (!PyArg_ParseTuple(args, "Oiiii",
                          &reader,
                          &(self->sample_rate),
                          &(self->channels),
                          &(self->channel_mask),
                          &(self->bits_per_sample)))
        return -1;

    if (self->sample_rate < 1) {
        PyErr_SetString(PyExc_ValueError, "sample_rate must be > 0");
        return -1;
    }

    if (self->channels < 1) {
        PyErr_SetString(PyExc_ValueError, "channels must be > 0");
        return -1;
    }

    if (self->channel_mask < 0) {
        PyErr_SetString(PyExc_ValueError, "channel_mask must be >= 0");
        return -1;
    }

    if ((self->bits_per_sample != 16) &&
        (self->bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError, "bits_per_sample must be 16,24");
        return -1;
    }

    Py_INCREF(reader);

    self->reader = br_open_external(reader,
                                    BS_BIG_ENDIAN,
                                    br_read_python,
                                    br_close_python,
                                    br_free_python);

    self->chunk_size = (self->bits_per_sample / 8) * self->channels * 2;
    self->buffer_size = DEFAULT_BUFFER_SIZE;
    self->buffer = malloc(sizeof(uint8_t) *
                          self->buffer_size *
                          self->chunk_size);

    for (i = 0; i < self->chunk_size; i++) {
        self->swap[i] =
            AOB_BYTE_SWAP[self->bits_per_sample == 24][self->channels - 1][i];
    }

    return 0;
}

static PyObject*
AOBPCMDecoder_new(PyTypeObject *type,
                  PyObject *args, PyObject *kwds) {
    decoders_AOBPCMDecoder *self;

    self = (decoders_AOBPCMDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
AOBPCMDecoder_dealloc(decoders_AOBPCMDecoder *self) {
    self->reader->close(self->reader);
    if (self->buffer != NULL)
        free(self->buffer);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
AOBPCMDecoder_sample_rate(decoders_AOBPCMDecoder *self, void *closure) {
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
AOBPCMDecoder_bits_per_sample(decoders_AOBPCMDecoder *self, void *closure) {
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
AOBPCMDecoder_channels(decoders_AOBPCMDecoder *self, void *closure) {
    return Py_BuildValue("i", self->channels);
}

static PyObject*
AOBPCMDecoder_channel_mask(decoders_AOBPCMDecoder *self, void *closure) {
    return Py_BuildValue("i", self->channel_mask);
}

static PyObject*
AOBPCMDecoder_read(decoders_AOBPCMDecoder* self, PyObject *args) {
    unsigned int i;

    for (i = 0; i < self->buffer_size; i++) {
        switch (aobpcm_read_chunk(self->buffer + (i * self->chunk_size),
                                  self->chunk_size,
                                  self->swap,
                                  self->reader)) {
        case 1:        /*read OK*/
            break;
        case 0:        /*EOF at start of read, which is OK*/
            goto done;
        case -1:       /*EOF in middle of read, which is an error*/
            PyErr_SetString(PyExc_IOError, "EOF reading PCM chunk");
            return NULL;
        }
    }

 done:
    /*generate pcm.FrameList object from little-endian string*/

    return bytes_to_framelist(self->buffer,
                              i * self->chunk_size,
                              self->channels,
                              self->bits_per_sample,
                              0,
                              1);
}

int
aobpcm_read_chunk(uint8_t* buffer,
                  int chunk_size,
                  uint8_t* swap,
                  BitstreamReader* reader) {
    int i;
    int byte;
    uint8_t unswapped[36];

    for (i = 0; i < chunk_size; i++) {
        if ((byte = ext_getc(reader->input.external)) != EOF) {
            unswapped[i] = (uint8_t)byte;
        } else {
            if (i == 0)
                return 0;  /*EOF at start of chunk*/
            else
                return -1; /*EOF in middle of chunk*/
        }
    }

    for (i = 0; i < chunk_size; i++) {
        buffer[swap[i]] = unswapped[i];
    }

    return 1; /*no errors reading chunk*/
}

static PyObject*
AOBPCMDecoder_close(decoders_AOBPCMDecoder* self, PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
bytes_to_framelist(uint8_t *bytes,
                   int bytes_length,
                   int channels,
                   int bits_per_sample,
                   int is_big_endian,
                   int is_signed) {
    PyObject *pcm = NULL;
    PyObject *framelist;

    if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return NULL;
    framelist = PyObject_CallMethod(pcm, "FrameList",
                                    "(s#iiii)",
                                    bytes, bytes_length,
                                    channels,
                                    bits_per_sample,
                                    is_big_endian,
                                    is_signed);
    Py_DECREF(pcm);
    return framelist;
}

static
int br_read_python(void* user_data,
                   struct bs_buffer* buffer)
{
    PyObject* pcmreader = (PyObject*)user_data;
    PyObject* read_result;

    /*call read() method on pcmreader*/
    if ((read_result =
         PyObject_CallMethod(pcmreader, "read", "i", 4096)) != NULL) {
        uint8_t *string;
        Py_ssize_t string_size;

        /*convert returned object to string of bytes*/
        if (PyString_AsStringAndSize(read_result,
                                     (char**)&string,
                                     &string_size) != -1) {
            /*then append bytes to buffer and return success*/
            uint8_t* appended = buf_extend(buffer, (uint32_t)string_size);
            memcpy(appended, string, string_size);
            buffer->buffer_size += (uint32_t)string_size;

            return 0;
        } else {
            /*string conversion failed so print/clear error and return an EOF*/
            PyErr_Print();
            return 1;
        }
    } else {
        /*read() method call failed
          so print/clear error and return an EOF
          (which will likely generate an IOError exception if its own)*/
        PyErr_Print();
        return 1;
    }

}

static
void br_close_python(void* user_data)
{
    /*FIXME*/
}

static
void br_free_python(void* user_data)
{
    Py_XDECREF((PyObject*)user_data);
}
