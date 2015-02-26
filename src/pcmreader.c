#include <stdlib.h>
#include "pcmreader.h"
#ifndef STANDALONE
#include "pcm_conv.h"
#endif

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif

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

#define READER_DEFS(name)                         \
static unsigned                                   \
pcmreader_##name##_read(struct PCMReader *self,   \
                        unsigned pcm_frames,      \
                        int *pcm_data);           \
                                                  \
static void                                       \
pcmreader_##name##_close(struct PCMReader *self); \
                                                  \
static void                                       \
pcmreader_##name##_del(struct PCMReader *self);

#ifdef STANDALONE
READER_DEFS(raw)
#else
READER_DEFS(python)
#endif


#ifdef STANDALONE
struct PCMReader*
pcmreader_open_raw(FILE *file,
                   unsigned sample_rate,
                   unsigned channels,
                   unsigned channel_mask,
                   unsigned bits_per_sample,
                   int is_little_endian,
                   int is_signed)
{
    struct PCMReader *reader = malloc(sizeof(struct PCMReader));

    reader->input.raw.file = file;
    reader->input.raw.converter =
        pcm_to_int_converter(bits_per_sample, !is_little_endian, is_signed);

    reader->sample_rate = sample_rate;
    reader->channels = channels;
    reader->channel_mask = channel_mask;
    reader->bits_per_sample = bits_per_sample;

    reader->status = PCM_OK;

    reader->read = pcmreader_raw_read;
    reader->close = pcmreader_raw_close;
    reader->del = pcmreader_raw_del;
    return reader;
}

#else

#if PY_MAJOR_VERSION >= 3
#ifndef PyInt_AsLong
#define PyInt_AsLong PyLong_AsLong
#endif
#endif

static int
get_unsigned_attr(PyObject *obj, const char *attr, unsigned *value)
{
    PyObject *attr_obj = PyObject_GetAttrString(obj, attr);
    long long_value;

    if (!attr_obj) {
        return 1;
    }

    long_value = PyInt_AsLong(attr_obj);

    Py_DECREF(attr_obj);

    if (long_value < 0) {
        /*either an error occurred or the value is negative,
          both are errors when converting to an unsigned value*/
        return 1;
    }

    *value = (unsigned)long_value;
    return 0;
}

struct PCMReader*
pcmreader_open_python(PyObject *obj)
{
    struct PCMReader *reader = malloc(sizeof(struct PCMReader));
    PyObject* audiotools_pcm;

    if (get_unsigned_attr(obj, "sample_rate", &(reader->sample_rate)))
        goto error;
    if (get_unsigned_attr(obj, "channels", &(reader->channels)))
        goto error;
    if (get_unsigned_attr(obj, "channel_mask", &(reader->channel_mask)))
        goto error;
    if (get_unsigned_attr(obj, "bits_per_sample", &(reader->bits_per_sample)))
        goto error;

    reader->input.python.obj = obj;

    /*attach a pcm.FrameList type object for verification during reads*/
    if ((audiotools_pcm = PyImport_ImportModule("audiotools.pcm")) == NULL) {
        goto error;
    }

    reader->input.python.framelist_type =
        PyObject_GetAttrString(audiotools_pcm, "FrameList");

    Py_DECREF(audiotools_pcm);
    Py_INCREF(obj);

    reader->input.python.stream_finished = 0;
    reader->input.python.framelist = NULL;
    reader->input.python.frames_remaining = 0;

    reader->status = PCM_OK;

    reader->read = pcmreader_python_read;
    reader->close = pcmreader_python_close;
    reader->del = pcmreader_python_del;
    return reader;

error:
    free(reader);
    return NULL;
}

int
py_obj_to_pcmreader(PyObject *obj, void **pcmreader)
{
    struct PCMReader *pcmreader_s = pcmreader_open_python(obj);
    if (pcmreader_s) {
        *pcmreader = pcmreader_s;
        return 1;
    } else {
        return 0;
    }
}
#endif

void
get_channel_data(const int *pcm_data,
                 unsigned channel_number,
                 unsigned channel_count,
                 unsigned pcm_frames,
                 int *channel_data)
{
    pcm_data += channel_number;
    for (; pcm_frames; pcm_frames--) {
        *channel_data = *pcm_data;
        pcm_data += channel_count;
        channel_data += 1;
    }
}

void
pcmreader_display(const struct PCMReader *pcmreader, FILE *output)
{
    fprintf(output, "sample_rate      %u\n", pcmreader->sample_rate);
    fprintf(output, "channels         %u\n", pcmreader->channels);
    fprintf(output, "channel mask     %u\n", pcmreader->channel_mask);
    fprintf(output, "bits-per-sample  %u\n", pcmreader->bits_per_sample);
}

#ifdef STANDALONE
static unsigned
pcmreader_raw_read(struct PCMReader *self,
                   unsigned pcm_frames,
                   int *pcm_data)
{
    const register unsigned bytes_per_sample = self->bits_per_sample / 8;

    int (*converter)(const unsigned char *) = self->input.raw.converter;

    const unsigned bytes_to_read =
        pcm_frames * bytes_per_sample * self->channels;

    unsigned char buffer[bytes_to_read];

    const size_t bytes_read =
        fread(buffer,
              sizeof(unsigned char),
              bytes_to_read,
              self->input.raw.file);

    const unsigned pcm_frames_read =
        bytes_read / bytes_per_sample / self->channels;

    /*cull partial PCM frames*/
    const unsigned samples_read = pcm_frames_read * self->channels;

    register unsigned i;
    for (i = 0; i < samples_read; i++) {
        *pcm_data = converter(buffer + (i * bytes_per_sample));
        pcm_data += 1;
    }

    return pcm_frames_read;
}

static void
pcmreader_raw_close(struct PCMReader *self)
{
    fclose(self->input.raw.file);
}

static void
pcmreader_raw_del(struct PCMReader *self)
{
    free(self);
}

#else

static unsigned
pcmreader_python_read(struct PCMReader *self,
                      unsigned pcm_frames,
                      int *pcm_data)
{
    const unsigned initial_frames = pcm_frames;

    while (pcm_frames && !self->input.python.stream_finished) {
        unsigned to_transfer;
        pcm_FrameList *framelist;

        if (self->input.python.framelist) {
            framelist = self->input.python.framelist;
        } else {
            PyObject *framelist_obj;

            /*need to read a new framelist from wrapped PCMReader*/
            if ((framelist_obj =
                 PyObject_CallMethod(self->input.python.obj,
                                     "read", "i", pcm_frames)) == NULL) {
                /*ensure result isn't an exception*/
                self->status = PCM_READ_ERROR;
                self->input.python.stream_finished = 1;
                return 0;
            }

            /*ensure result is a pcm.FrameList object*/
            if (Py_TYPE(framelist_obj) ==
                (PyTypeObject*)self->input.python.framelist_type) {
                framelist = (pcm_FrameList*)framelist_obj;
            } else {
                self->status = PCM_NON_FRAMELIST;
                self->input.python.stream_finished = 1;
                return 0;
            }

            /*ensure FrameList object matches stream's parameters*/
            if ((framelist->channels != self->channels) ||
                (framelist->bits_per_sample != self->bits_per_sample)) {
                self->status = PCM_INVALID_FRAMELIST;
                self->input.python.stream_finished = 1;
                return 0;
            }

            self->input.python.stream_finished = (framelist->frames == 0);
            self->input.python.framelist = framelist;
            self->input.python.frames_remaining = framelist->frames;
        }

        /*transfer data from FrameList to buffer*/
        to_transfer = MIN(self->input.python.frames_remaining, pcm_frames);

        memcpy(pcm_data,
               framelist->samples +
               (framelist->channels *
                (framelist->frames - self->input.python.frames_remaining)),
               sizeof(int) * framelist->channels * to_transfer);

        /*advance buffers*/
        pcm_frames -= to_transfer;
        pcm_data += (to_transfer * framelist->channels);
        if ((self->input.python.frames_remaining -= to_transfer) == 0) {
            /*and remove FrameList if we've exhausted it*/
            Py_DECREF((PyObject*)self->input.python.framelist);
            self->input.python.framelist = NULL;
        }
    }

    return initial_frames - pcm_frames;
}

static void
pcmreader_python_close(struct PCMReader *self)
{
    PyObject *result =
        PyObject_CallMethod(self->input.python.obj, "close", NULL);
    if (result) {
        Py_DECREF(result);
    } else {
        PyErr_Clear();
    }
}

static void
pcmreader_python_del(struct PCMReader *self) {
    Py_XDECREF(self->input.python.obj);
    Py_XDECREF(self->input.python.framelist_type);
    Py_XDECREF((PyObject*)self->input.python.framelist);
    free(self);
}

#endif

#ifdef EXECUTABLE

#define BLOCKSIZE 48000

int main(int argc, char *argv[])
{
    struct PCMReader *pcmreader = pcmreader_open(stdin,
                                                 44100,
                                                 2,
                                                 0,
                                                 16,
                                                 1,
                                                 1);
    int pcm_data[2 * BLOCKSIZE];
    unsigned pcm_frames;

    while ((pcm_frames = pcmreader->read(pcmreader,
                                         BLOCKSIZE,
                                         pcm_data)) > 0) {
        unsigned i;
        for (i = 0; i < pcm_frames; i++) {
            printf("%6d  %6d\n",
                   pcm_data[i * 2],
                   pcm_data[i * 2 + 1]);
        }
    }

    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}

#endif
