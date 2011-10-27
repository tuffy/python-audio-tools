#include "pcmreader2.h"
#include "pcm.h"
#include <stdlib.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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

struct pcm_reader2*
pcmr_open2(PyObject *pcmreader)
{
    struct pcm_reader2* reader = malloc(sizeof(struct pcm_reader2));
    PyObject* audiotools_pcm = PyImport_ImportModule("audiotools.pcm");
    PyObject* attr;

    /*this shouldn't happen in any normal install*/
    if (audiotools_pcm == NULL) {
        PyErr_Print();
        exit(1);
    }

    reader->callback = NULL;
    reader->buffer_size = 1;
    reader->callback_buffer = malloc(reader->buffer_size);

    reader->pcmreader = pcmreader;

    reader->framelist_type = PyObject_GetAttrString(audiotools_pcm,
                                                    "FrameList");

    /*nor should this*/
    if (reader->framelist_type == NULL) {
        PyErr_Print();
        exit(1);
    }

    Py_DECREF(audiotools_pcm);

    /*now that the basics are setup,
      try to pull attributes out of the main pcmreader object*/
    if ((attr = PyObject_GetAttrString(pcmreader, "sample_rate")) == NULL)
        goto error;
    reader->sample_rate = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "bits_per_sample")) == NULL)
        goto error;
    reader->bits_per_sample = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "channels")) == NULL)
        goto error;
    reader->channels = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "channel_mask")) == NULL)
        goto error;
    reader->channel_mask = (unsigned int)PyInt_AsLong(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    reader->bytes_per_sample = reader->bits_per_sample / 8;

    return reader;
 error:
    pcmr_close2(reader);
    return NULL;
}

int
pcmr_close2(struct pcm_reader2 *reader)
{
    struct pcmr_callback2 *callback;
    struct pcmr_callback2 *next;

    free(reader->callback_buffer);

    for (callback = reader->callback; callback != NULL; callback = next) {
        next = callback->next;
        free(callback);
    }

    Py_DECREF(reader->framelist_type);

    free(reader);
    return 1;
}

int
pcmr_read2(struct pcm_reader2 *reader,
           unsigned pcm_frames,
           array_ia* samples)
{
    PyObject* framelist_obj;
    pcm_FrameList* framelist;
    unsigned frame;
    unsigned channel;
    array_i* channel_a;

    struct pcmr_callback2* callback;
    PyObject* string_obj;
    unsigned char* string;
    Py_ssize_t string_length;

    /*make a call to "pcmreader.read(bytes)"
      where "bytes" is set to the proper PCM frame count*/
    if (((framelist_obj =
          PyObject_CallMethod(reader->pcmreader, "read", "i",
                              pcm_frames *
                              reader->channels *
                              reader->bytes_per_sample))) == NULL) {
        /*ensure result isn't an exception*/
        return 0;
    }

    /*ensure result is a pcm.FrameList object*/
    if (framelist_obj->ob_type != (PyTypeObject*)reader->framelist_type) {
        Py_DECREF(framelist_obj);
        PyErr_SetString(PyExc_TypeError,
                        "results from pcmreader.read() must be FrameLists");
        return 0;
    } else {
        framelist = (pcm_FrameList*)framelist_obj;
    }

    /*split framelist's packed ints into a set of channels*/
    samples->reset(samples);
    for (channel = 0; channel < framelist->channels; channel++) {
        channel_a = samples->append(samples);
        for (frame = 0; frame < framelist->frames; frame++) {
            channel_a->resize(channel_a, framelist->frames);
            a_append(channel_a,
                     framelist->samples[channel +
                                        (frame * framelist->channels)]);
        }
    }

    /*apply all callbacks to pcm.FrameList object*/
    for (callback = reader->callback;
         callback != NULL;
         callback = callback->next) {
        string_obj = PyObject_CallMethod(framelist_obj,
                                         "to_bytes", "(ii)",
                                         !callback->little_endian,
                                         callback->is_signed);
        if (string_obj == NULL) {
            Py_DECREF(framelist_obj);
            return 0;
        }

        if (PyString_AsStringAndSize(string_obj,
                                     (char**)(&string),
                                     &string_length) == -1) {
            Py_DECREF(framelist_obj);
            Py_DECREF(string_obj);
            return 0;
        }

        callback->callback(callback->data,
                           string, (unsigned long)string_length);

        Py_DECREF(string_obj);
    }

    /*free any allocated buffers and Python objects*/
    Py_DECREF(framelist_obj);

    return 1;
}

#else

struct pcm_reader2*
pcmr_open2(FILE *file,
           unsigned int sample_rate,
           unsigned int channels,
           unsigned int channel_mask,
           unsigned int bits_per_sample,
           unsigned int big_endian,
           unsigned int is_signed)
{
    struct pcm_reader2* reader = malloc(sizeof(struct pcm_reader2));

    /*first, assign the reader's attributes from the arguments*/
    reader->file = file;
    reader->sample_rate = sample_rate;
    reader->channels = channels;
    reader->channel_mask = channel_mask;
    reader->bits_per_sample = bits_per_sample;
    reader->big_endian = big_endian;
    reader->is_signed = is_signed;

    reader->bytes_per_sample = reader->bits_per_sample / 8;

    reader->callback = NULL;

    reader->buffer_size = 1;
    reader->buffer = malloc(reader->buffer_size);
    reader->buffer_converter =
        FrameList_get_char_to_int_converter(reader->bits_per_sample,
                                            reader->big_endian,
                                            reader->is_signed);

    reader->callback_buffer = malloc(reader->buffer_size);

    return reader;
}

int
pcmr_close2(struct pcm_reader2 *reader)
{
    struct pcmr_callback2 *callback;
    struct pcmr_callback2 *next;

    for (callback = reader->callback; callback != NULL; callback = next) {
        next = callback->next;
        free(callback);
    }

    free(reader->buffer);
    free(reader->callback_buffer);
    fclose(reader->file);
    free(reader);
    return 1;
}

int
pcmr_read2(struct pcm_reader2 *reader,
           unsigned pcm_frames,
           array_ia* samples)
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

    struct pcmr_callback2 *callback;
    FrameList_int_to_char_converter callback_converter;

    if (reader->buffer_size < bytes_to_read) {
        reader->buffer_size = bytes_to_read;
        reader->buffer =
            realloc(reader->buffer, bytes_to_read);
        reader->callback_buffer =
            realloc(reader->callback_buffer, bytes_to_read);
    }

    /*read data into "buffer" as plain bytes*/
    bytes_read = fread(reader->buffer, sizeof(uint8_t), bytes_to_read,
                       reader->file);

    /*remove partial PCM frames*/
    while (bytes_read % (reader->channels * reader->bytes_per_sample))
        bytes_read--;

    frames_read = (unsigned)(bytes_read /
                             (reader->channels * reader->bytes_per_sample));

    /*place "buffer" into "samples", split up by channel*/
    samples->reset(samples);
    for (channel = 0; channel < reader->channels; channel++) {
        channel_a = samples->append(samples);
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
    for (callback = reader->callback;
         callback != NULL;
         callback = callback->next) {
        callback_converter =
            FrameList_get_int_to_char_converter(reader->bits_per_sample,
                                                !callback->little_endian,
                                                callback->is_signed);

        for (byte = 0; byte < bytes_read; byte += reader->bytes_per_sample) {
            callback_converter(reader->buffer_converter(reader->buffer + byte),
                               reader->callback_buffer + byte);
        }

        callback->callback(callback->data,
                           (unsigned char*)reader->callback_buffer,
                           (unsigned long)bytes_read);
    }

    return 1;
}
#endif

void
pcmr_add_callback2(struct pcm_reader2 *reader,
                   void (*callback)(void*, unsigned char*, unsigned long),
                   void *data,
                   int is_signed,
                   int little_endian)
{
    struct pcmr_callback2 *callback_node =
        malloc(sizeof(struct pcmr_callback2));
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = reader->callback;
    callback_node->is_signed = is_signed;
    callback_node->little_endian = little_endian;
    reader->callback = callback_node;
}
