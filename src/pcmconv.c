#include "pcmconv.h"
#include <stdlib.h>

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

#ifndef STANDALONE

PyObject*
open_audiotools_pcm(void)
{
    return PyImport_ImportModule("audiotools.pcm");
}

PyObject*
array_i_to_FrameList(PyObject* audiotools_pcm,
                     array_i* samples,
                     unsigned int channels,
                     unsigned int bits_per_sample)
{
    pcm_FrameList *framelist;

    framelist = (pcm_FrameList*)PyObject_CallMethod(audiotools_pcm,
                                                    "__blank__", NULL);

    if (framelist != NULL) {
        if ((samples->len % channels) == 0) {
            framelist->frames = samples->len / channels;
            framelist->channels = channels;
            framelist->bits_per_sample = bits_per_sample;
            framelist->samples_length = framelist->frames * framelist->channels;
            framelist->samples = realloc(framelist->samples,
                                         framelist->samples_length *
                                         sizeof(int));

            memcpy(framelist->samples, samples->_,
                   framelist->samples_length * sizeof(int));

            return (PyObject*)framelist;
        } else {
            Py_DECREF((PyObject*)framelist);
            PyErr_SetString(PyExc_ValueError,
                            "samples data not divisible by channel count");
            return NULL;
        }
    } else {
        return NULL;
    }
}

PyObject*
array_ia_to_FrameList(PyObject* audiotools_pcm,
                      array_ia* channels,
                      unsigned int bits_per_sample)
{
    unsigned c;
    unsigned i;
    pcm_FrameList *framelist;
    array_i* channel;

    framelist = (pcm_FrameList*)PyObject_CallMethod(audiotools_pcm,
                                                    "__blank__", NULL);
    if (framelist != NULL) {
        if (channels->len > 0) {
            framelist->frames = channels->_[0]->len;
            framelist->channels = channels->len;
            framelist->bits_per_sample = bits_per_sample;
            framelist->samples_length = (framelist->frames *
                                         framelist->channels);
            framelist->samples = realloc(framelist->samples,
                                         framelist->samples_length *
                                         sizeof(int));

            for (c = 0; c < channels->len; c++) {
                channel = channels->_[c];
                if (channel->len == framelist->frames) {
                    for (i = 0; i < framelist->frames; i++) {
                        framelist->samples[(i * channels->len) + c] =
                            channel->_[i];
                    }
                } else {
                    /*return an error if there's a channel length mismatch*/
                    Py_DECREF((PyObject*)framelist);
                    PyErr_SetString(PyExc_ValueError,
                                    "channel length mismatch");
                    return NULL;
                }
            }
        }

        return (PyObject*)framelist;
    } else {
        return NULL;
    }
}

PyObject*
empty_FrameList(PyObject* audiotools_pcm,
                unsigned int channels,
                unsigned int bits_per_sample)
{
    pcm_FrameList *framelist;

    framelist = (pcm_FrameList*)PyObject_CallMethod(audiotools_pcm,
                                                    "__blank__", NULL);

    if (framelist != NULL) {
        framelist->channels = channels;
        framelist->bits_per_sample = bits_per_sample;

        return (PyObject*)framelist;
    } else {
        return NULL;
    }
}

struct pcmreader_s*
open_pcmreader(PyObject* pcmreader_obj)
{
    struct pcmreader_s* pcmreader = malloc(sizeof(struct pcmreader_s));
    PyObject* attr;
    PyObject* audiotools_pcm;

    /*setup some placeholder values*/
    pcmreader->pcmreader_obj = NULL;
    pcmreader->framelist_type = NULL;
    pcmreader->sample_rate = 0;
    pcmreader->channels = 0;
    pcmreader->channel_mask = 0;
    pcmreader->bits_per_sample = 0;
    pcmreader->bytes_per_sample = 0;
    pcmreader->callbacks = NULL;

    pcmreader->read = pcmreader_read;
    pcmreader->close = pcmreader_close;
    pcmreader->add_callback = pcmreader_add_callback;
    pcmreader->del = pcmreader_del;

    /*attempt to extract proper values from the pcmreader_obj*/
    if ((attr = PyObject_GetAttrString(pcmreader_obj,
                                       "sample_rate")) == NULL)
        goto error;
    pcmreader->sample_rate = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader_obj,
                                       "bits_per_sample")) == NULL)
        goto error;
    pcmreader->bits_per_sample = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader_obj,
                                       "channels")) == NULL)
        goto error;
    pcmreader->channels = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader_obj,
                                       "channel_mask")) == NULL)
        goto error;
    pcmreader->channel_mask = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    pcmreader->bytes_per_sample = pcmreader->bits_per_sample / 8;

    /*attach and incref the wrapped PCMReader object*/
    pcmreader->pcmreader_obj = pcmreader_obj;
    Py_INCREF(pcmreader_obj);

    /*attach a pcm.FrameList type object for verification during reads*/
    if ((audiotools_pcm = PyImport_ImportModule("audiotools.pcm")) == NULL) {
        goto error;
    }

    pcmreader->framelist_type = PyObject_GetAttrString(audiotools_pcm,
                                                       "FrameList");

    Py_DECREF(audiotools_pcm);

    return pcmreader;

 error:
    Py_XDECREF(pcmreader->pcmreader_obj);
    Py_XDECREF(pcmreader->framelist_type);
    free(pcmreader);
    return NULL;
}

int
pcmreader_converter(PyObject* obj, void** pcm_reader)
{
    pcmreader* pcmreader_s = open_pcmreader(obj);
    if (pcmreader_s != NULL) {
        *pcm_reader = pcmreader_s;
        return 1;
    } else {
        return 0;
    }
}

int pcmreader_read(struct pcmreader_s* reader,
                    unsigned pcm_frames,
                    array_ia* channels)
{
    PyObject* framelist_obj;
    pcm_FrameList* framelist;
    unsigned frame;
    unsigned channel;
    array_i* channel_a;

    struct pcmreader_callback* callback;
    PyObject* string_obj;
    unsigned char* string;
    Py_ssize_t string_length;

    /*make a call to "pcmreader.read(pcm_frames)"
      where "pcm_frames" is set to the proper PCM frame count*/
    if (((framelist_obj =
          PyObject_CallMethod(reader->pcmreader_obj, "read", "i",
                              (int)pcm_frames))) == NULL) {
        /*ensure result isn't an exception*/
        return 1;
    }

    /*ensure result is a pcm.FrameList object*/
    if (framelist_obj->ob_type != (PyTypeObject*)reader->framelist_type) {
        Py_DECREF(framelist_obj);
        PyErr_SetString(PyExc_TypeError,
                        "results from pcmreader.read() must be FrameLists");
        return 1;
    } else {
        framelist = (pcm_FrameList*)framelist_obj;
    }

    /*split framelist's packed ints into a set of channels*/
    channels->reset(channels);
    for (channel = 0; channel < framelist->channels; channel++) {
        channel_a = channels->append(channels);
        channel_a->resize(channel_a, framelist->frames);
        for (frame = 0; frame < framelist->frames; frame++) {
            a_append(channel_a,
                     framelist->samples[(frame * framelist->channels) +
                                        channel]);
        }
    }

    /*apply all callbacks to pcm.FrameList object*/
    for (callback = reader->callbacks;
         callback != NULL;
         callback = callback->next) {
        string_obj = PyObject_CallMethod(framelist_obj,
                                         "to_bytes", "(ii)",
                                         !callback->little_endian,
                                         callback->is_signed);
        if (string_obj == NULL) {
            Py_DECREF(framelist_obj);
            return 1;
        }

        if (PyString_AsStringAndSize(string_obj,
                                     (char**)(&string),
                                     &string_length) == -1) {
            Py_DECREF(framelist_obj);
            Py_DECREF(string_obj);
            return 1;
        }

        callback->callback(callback->user_data,
                           string,
                           (unsigned long)string_length);

        Py_DECREF(string_obj);
    }

    /*free any allocated buffers and Python objects*/
    Py_DECREF(framelist_obj);

    return 0;
}

void pcmreader_close(struct pcmreader_s* reader)
{
    /*FIXME*/
}

void pcmreader_del(struct pcmreader_s* reader)
{
    struct pcmreader_callback *callback;
    struct pcmreader_callback *next;

    /*free callback nodes*/
    for (callback = reader->callbacks; callback != NULL; callback = next) {
        next = callback->next;
        free(callback);
    }

    /*decref wrapped PCMReader object*/
    Py_XDECREF(reader->pcmreader_obj);

    /*decref pcm.FrameList type*/
    Py_XDECREF(reader->framelist_type);

    /*free pcmreader struct*/
    free(reader);
}

#else

struct pcmreader_s* open_pcmreader(FILE* file,
                                   unsigned int sample_rate,
                                   unsigned int channels,
                                   unsigned int channel_mask,
                                   unsigned int bits_per_sample,
                                   unsigned int big_endian,
                                   unsigned int is_signed)
{
    struct pcmreader_s* pcmreader = malloc(sizeof(struct pcmreader_s));

    pcmreader->file = file;
    pcmreader->sample_rate = sample_rate;
    pcmreader->channels = channels;
    pcmreader->channel_mask = channel_mask;
    pcmreader->bits_per_sample = bits_per_sample;
    pcmreader->bytes_per_sample = bits_per_sample / 8;

    pcmreader->big_endian = big_endian;
    pcmreader->is_signed = is_signed;

    pcmreader->buffer_size = 1;
    pcmreader->buffer = malloc(pcmreader->buffer_size);
    pcmreader->buffer_converter =
        FrameList_get_char_to_int_converter(pcmreader->bits_per_sample,
                                            pcmreader->big_endian,
                                            pcmreader->is_signed);;

    pcmreader->callbacks = NULL;

    pcmreader->read = pcmreader_read;
    pcmreader->close = pcmreader_close;
    pcmreader->add_callback = pcmreader_add_callback;
    pcmreader->del = pcmreader_del;

    return pcmreader;
}

int pcmreader_read(struct pcmreader_s* reader,
                   unsigned pcm_frames,
                   array_ia* channels)
{
    unsigned bytes_to_read = (pcm_frames *
                              reader->channels *
                              reader->bytes_per_sample);
    size_t bytes_read;
    unsigned frames_read;

    array_i* channel_a;
    unsigned int byte;
    unsigned int sample;
    unsigned int channel;
    unsigned int frame;

    struct pcmreader_callback *callback;
    FrameList_int_to_char_converter callback_converter;

    uint8_t* callback_buffer;

    if (reader->buffer_size < bytes_to_read) {
        reader->buffer_size = bytes_to_read;
        reader->buffer = realloc(reader->buffer, bytes_to_read);
    }

    /*read data into "buffer" as plain bytes*/
    bytes_read = fread(reader->buffer, sizeof(uint8_t), bytes_to_read,
                       reader->file);

    /*remove partial PCM frames, if any*/
    while (bytes_read % (reader->channels * reader->bytes_per_sample))
        bytes_read--;

    frames_read = (unsigned)(bytes_read /
                             (reader->channels * reader->bytes_per_sample));

    /*place "buffer" into "channels", split up by channel*/
    channels->reset(channels);
    for (channel = 0; channel < reader->channels; channel++) {
        channel_a = channels->append(channels);
        channel_a->resize(channel_a, frames_read);
        for (frame = 0; frame < frames_read; frame++) {
            sample = channel + (frame * reader->channels);
            a_append(channel_a,
                     reader->buffer_converter(reader->buffer +
                                              (sample *
                                               reader->bytes_per_sample)));
        }
    }

    /*apply all callbacks on that collection of samples*/
    for (callback = reader->callbacks;
         callback != NULL;
         callback = callback->next) {
        callback_converter =
            FrameList_get_int_to_char_converter(reader->bits_per_sample,
                                                !callback->little_endian,
                                                callback->is_signed);

        callback_buffer = malloc(bytes_read);

        for (byte = 0; byte < bytes_read; byte += reader->bytes_per_sample) {
            callback_converter(reader->buffer_converter(reader->buffer + byte),
                               callback_buffer + byte);
        }

        callback->callback(callback->user_data,
                           (unsigned char*)callback_buffer,
                           (unsigned long)bytes_read);

        free(callback_buffer);
    }

    return 0;
}

void pcmreader_close(struct pcmreader_s* reader)
{
    fclose(reader->file);
}

void pcmreader_del(struct pcmreader_s* reader)
{
    struct pcmreader_callback *callback;
    struct pcmreader_callback *next;

    /*free callback nodes*/
    for (callback = reader->callbacks; callback != NULL; callback = next) {
        next = callback->next;
        free(callback);
    }

    /*free temporary buffer*/
    free(reader->buffer);

    /*free pcmreader struct*/
    free(reader);
}


#endif


void pcmreader_add_callback(struct pcmreader_s* reader,
                            void (*callback)(void*,
                                             unsigned char*,
                                             unsigned long),
                            void *user_data,
                            int is_signed,
                            int little_endian)
{
    struct pcmreader_callback *callback_node =
        malloc(sizeof(struct pcmreader_callback));

    callback_node->callback = callback;
    callback_node->is_signed = is_signed;
    callback_node->little_endian = little_endian;
    callback_node->user_data = user_data;
    callback_node->next = reader->callbacks;

    reader->callbacks = callback_node;
}
