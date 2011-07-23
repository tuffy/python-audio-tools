#include "pcmreader.h"
#include "pcm.h"

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
struct pcm_reader*
pcmr_open(PyObject *pcmreader)
{
    struct pcm_reader *reader = malloc(sizeof(struct pcm_reader));
    PyObject *attr;

    reader->callback = NULL;

    if ((reader->pcm_module = PyImport_ImportModule("audiotools.pcm")) == NULL)
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "sample_rate")) == NULL)
        goto error;
    reader->sample_rate = (unsigned int)PyInt_AsUnsignedLongMask(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "bits_per_sample")) == NULL)
        goto error;
    reader->bits_per_sample = (unsigned int)PyInt_AsUnsignedLongMask(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "channels")) == NULL)
        goto error;
    reader->channels = (unsigned int)PyInt_AsUnsignedLongMask(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((attr = PyObject_GetAttrString(pcmreader, "channel_mask")) == NULL)
        goto error;
    reader->channel_mask = (unsigned int)PyInt_AsUnsignedLongMask(attr);
    Py_DECREF(attr);
    if (PyErr_Occurred())
        goto error;

    if ((reader->read = PyObject_GetAttrString(pcmreader, "read")) == NULL)
        goto error;
    if (!PyCallable_Check(reader->read)) {
        Py_DECREF(reader->read);
        PyErr_SetString(PyExc_TypeError, "read parameter must be callable");
        goto error;
    }
    if ((reader->close = PyObject_GetAttrString(pcmreader, "close")) == NULL)
        goto error;
    if (!PyCallable_Check(reader->close)) {
        Py_DECREF(reader->read);
        Py_DECREF(reader->close);
        PyErr_SetString(PyExc_TypeError, "close parameter must be callable");
        goto error;
    }

    return reader;
 error:
    free(reader);
    return NULL;
}

int
pcmr_close(struct pcm_reader *reader)
{
    PyObject *result;
    int returnval;
    struct pcmr_callback *callback;
    struct pcmr_callback *next;

    result = PyEval_CallObject(reader->close, NULL);
    if (result == NULL)
        returnval = 0;
    else {
        Py_DECREF(result);
        returnval = 1;
    }

    for (callback = reader->callback; callback != NULL; callback = next) {
        next = callback->next;
        free(callback);
    }

    Py_DECREF(reader->read);
    Py_DECREF(reader->close);
    Py_DECREF(reader->pcm_module);
    free(reader);
    return returnval;
}
#else

struct pcm_reader*
pcmr_open(FILE *pcmreader,
          unsigned int sample_rate,
          unsigned int channels,
          unsigned int channel_mask,
          unsigned int bits_per_sample,
          unsigned int big_endian,
          unsigned int is_signed)
{
    struct pcm_reader *reader = malloc(sizeof(struct pcm_reader));
    reader->read = pcmreader;
    reader->sample_rate = sample_rate;
    reader->channels = channels;
    reader->channel_mask = channel_mask;
    reader->bits_per_sample = bits_per_sample;
    reader->big_endian = big_endian;
    reader->is_signed = is_signed;
    reader->callback = NULL;
    return reader;
}

int
pcmr_close(struct pcm_reader *reader)
{
    struct pcmr_callback *callback;
    struct pcmr_callback *next;

    for (callback = reader->callback; callback != NULL; callback = next) {
        next = callback->next;
        free(callback);
    }

    fclose(reader->read);
    free(reader);
    return 1;
}

#endif

void
pcmr_add_callback(struct pcm_reader *reader,
                  void (*callback)(void*, unsigned char*, unsigned long),
                  void *data,
                  int is_signed,
                  int little_endian)
{
    struct pcmr_callback *callback_node = malloc(sizeof(struct pcmr_callback));
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = reader->callback;
    callback_node->is_signed = is_signed;
    callback_node->little_endian = little_endian;
    reader->callback = callback_node;
}

#ifndef STANDALONE
int
pcmr_read(struct pcm_reader *reader,
          long sample_count,
          struct ia_array *samples)
{
    ia_size_t i, j;
    PyObject *args;
    PyObject *framelist_obj = NULL;
    pcm_FrameList *framelist;
    Py_ssize_t buffer_length;
    unsigned char *buffer;
    int buffer_is_signed = -1;
    int buffer_little_endian = -1;
    PyObject *buffer_obj = NULL;

    ia_data_t *buffer_samples;
    ia_size_t buffer_samples_length;
    struct i_array *channel;

    PyObject *framelist_type_obj = NULL;

    struct pcmr_callback *node;
    struct pcmr_callback *next;

    /*make a call to "reader.read(bytes)"
      where "bytes" is set to the proper PCM frame count*/
    args = Py_BuildValue("(l)",  sample_count *
                         reader->bits_per_sample * samples->size / 8);
    framelist_obj = PyEval_CallObject(reader->read, args);
    Py_DECREF(args);
    if (framelist_obj == NULL)
        goto error;

    /*ensure result is a FrameList*/
    if ((framelist_type_obj = PyObject_GetAttrString(
                                reader->pcm_module, "FrameList")) == NULL)
        goto error;

    if (framelist_obj->ob_type == (PyTypeObject*)framelist_type_obj) {
        framelist = (pcm_FrameList*)framelist_obj;
        buffer_samples = framelist->samples;
        buffer_samples_length = framelist->samples_length;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "results from pcmreader.read() must be FrameLists");
        goto error;
    }

    /*place "buffer_samples" into "samples", split up by channel*/
    for (i = 0; i < reader->channels; i++) {
        channel = iaa_getitem(samples, i);
        ia_reset(channel);
        for (j = i; j < buffer_samples_length; j += reader->channels)
            ia_append(channel, buffer_samples[j]);
    }

    /*apply all callbacks to that collection of samples*/
    for (node = reader->callback; node != NULL; node = next) {
        if ((buffer_is_signed != node->is_signed) ||
            (buffer_little_endian != node->little_endian)) {
            buffer_obj = PyObject_CallMethod(framelist_obj,
                                             "to_bytes", "(ii)",
                                             !node->little_endian,
                                             node->is_signed);
            if (buffer_obj == NULL)
                goto error;
            if (PyString_AsStringAndSize(buffer_obj, (char**)(&buffer),
                                         &buffer_length) == -1)
                goto error;
            buffer_is_signed = node->is_signed;
            buffer_little_endian = node->little_endian;
        }

        next = node->next;
        node->callback(node->data, buffer, (unsigned long)buffer_length);
    }

    /*free any allocated buffers and Python objects*/
    Py_DECREF(framelist_obj);
    Py_XDECREF(buffer_obj);
    Py_DECREF(framelist_type_obj);
    return 1;
 error:
    Py_XDECREF(framelist_type_obj);
    Py_XDECREF(framelist_obj);
    Py_XDECREF(buffer_obj);
    return 0;
}
#else
int
pcmr_read(struct pcm_reader *reader,
          long sample_count,
          struct ia_array *samples)
{
    ia_size_t i, j;

    size_t buffer_length;
    unsigned char *buffer;
    ia_data_t *buffer_samples;
    ia_size_t buffer_samples_length;
    int buffer_is_signed = -1;
    int buffer_little_endian = -1;

    struct i_array *channel;

    struct pcmr_callback *node;
    struct pcmr_callback *next;

    /*read in "buffer" as a string of plain bytes*/
    buffer_length = sample_count * reader->bits_per_sample * samples->size / 8;
    buffer = malloc(buffer_length);
    buffer_length = fread(buffer, 1, buffer_length, reader->read);

    /*convert "buffer" to "buffer_samples", a list of int32s*/
    buffer_samples_length = buffer_length / (reader->bits_per_sample / 8);
    buffer_samples = malloc(sizeof(ia_data_t) * buffer_samples_length);

    FrameList_char_to_samples(
            buffer_samples,
            buffer,
            FrameList_get_char_to_int_converter(reader->bits_per_sample,
                                                reader->big_endian,
                                                reader->is_signed),
            buffer_samples_length,
            reader->bits_per_sample);

    /*place "buffer_samples" into "samples", split up by channel*/
    for (i = 0; i < reader->channels; i++) {
        channel = iaa_getitem(samples, i);
        ia_reset(channel);
        for (j = i; j < buffer_samples_length; j += reader->channels)
            ia_append(channel, buffer_samples[j]);
    }

    /*apply all callbacks to that collection of samples*/
    for (node = reader->callback; node != NULL; node = next) {
        /*convert "buffer_samples" back into a signed, little-endian string,
          if necessary*/
        if ((buffer_is_signed != node->is_signed) ||
            (buffer_little_endian != node->little_endian)) {
            FrameList_samples_to_char(
                buffer,
                buffer_samples,
                FrameList_get_int_to_char_converter(reader->bits_per_sample,
                                                    !node->little_endian,
                                                    node->is_signed),
                buffer_samples_length,
                reader->bits_per_sample);
            buffer_is_signed = node->is_signed;
            buffer_little_endian = node->little_endian;
        }

        next = node->next;
        node->callback(node->data, buffer, (unsigned long)buffer_length);
    }

    /*free any allocated buffers*/
    free(buffer_samples);
    free(buffer);
    return 1;
}
#endif


