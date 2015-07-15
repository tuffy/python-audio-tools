#include "wavpack.h"
#include "../pcm_conv.h"
#include "../framelist.h"
#include <string.h>

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int pcm_data[],
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames);

int
WavPackDecoder_init(decoders_WavPackDecoder *self,
                    PyObject *args,
                    PyObject *kwds) {
    char error[80];
    char *filename = NULL;
    self->audiotools_pcm = NULL;

    audiotools__MD5Init(&(self->md5));
    self->verifying_md5_sum = 1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    if (!PyArg_ParseTuple(args, "s", &filename)) {
        return -1;
    }

    /*open WavPack reader context*/
    if ((self->context = WavpackOpenFileInput(filename,
                                              error,
                                              0,
                                              0)) == NULL) {
        PyErr_SetString(PyExc_IOError, error);
        return -1;
    }

    /*mark stream as not closed and ready for reading*/
    self->closed = 0;

    return 0;
}

void
WavPackDecoder_dealloc(decoders_WavPackDecoder *self) {
    Py_XDECREF(self->audiotools_pcm);
    if (self->context) {
        WavpackCloseFile(self->context);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
WavPackDecoder_new(PyTypeObject *type,
                   PyObject *args, PyObject *kwds) {
    decoders_WavPackDecoder *self;

    self = (decoders_WavPackDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
WavPackDecoder_sample_rate(decoders_WavPackDecoder *self, void *closure)
{
    const uint32_t sample_rate = WavpackGetSampleRate(self->context);
    return Py_BuildValue("I", sample_rate);
}

static PyObject*
WavPackDecoder_bits_per_sample(decoders_WavPackDecoder *self, void *closure)
{
    const int bits_per_sample = WavpackGetBitsPerSample(self->context);
    return Py_BuildValue("i", bits_per_sample);
}

static PyObject*
WavPackDecoder_channels(decoders_WavPackDecoder *self, void *closure)
{
    const int channels = WavpackGetNumChannels(self->context);
    return Py_BuildValue("i", channels);
}

static PyObject*
WavPackDecoder_channel_mask(decoders_WavPackDecoder *self, void *closure)
{
    const int mask = WavpackGetChannelMask(self->context);
    return Py_BuildValue("i", mask);
}

static PyObject*
WavPackDecoder_close(decoders_WavPackDecoder* self, PyObject *args)
{
    /*mark stream as closed so more calls to read() generate ValueErrors*/
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
WavPackDecoder_enter(decoders_WavPackDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
WavPackDecoder_exit(decoders_WavPackDecoder* self, PyObject *args)
{
    /*FIXME*/
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject*
WavPackDecoder_read(decoders_WavPackDecoder* self, PyObject *args)
{
    int pcm_frames;
    pcm_FrameList *framelist;
    const unsigned channel_count = WavpackGetNumChannels(self->context);
    const unsigned bits_per_sample = WavpackGetBitsPerSample(self->context);
    uint32_t frames_read;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "i", &pcm_frames)) {
        return NULL;
    }

    /*clamp number of PCM frames to a reasonable range
      regardless of how many are requested*/
    pcm_frames = MIN(MAX(pcm_frames, 1), 48000);

    /*build FrameList to dump data into*/
    framelist = new_FrameList(self->audiotools_pcm,
                              channel_count,
                              bits_per_sample,
                              pcm_frames);

    /*perform actual read*/
    frames_read = WavpackUnpackSamples(self->context,
                                       framelist->samples,
                                       pcm_frames);

    /*reduce FrameList's size accordingly*/
    framelist->frames = frames_read;
    framelist->samples_length = framelist->frames * framelist->channels;

    if (self->verifying_md5_sum) {
        if (frames_read) {
            /*compute running MD5 sum*/
            update_md5sum(&(self->md5),
                          framelist->samples,
                          framelist->channels,
                          framelist->bits_per_sample,
                          framelist->frames);
        } else {
            /*verify final MD5 sum*/
            uint8_t stored_md5_sum[16];
            uint8_t stream_md5_sum[16];

            self->verifying_md5_sum = 0;

            if (WavpackGetMD5Sum(self->context, stored_md5_sum)) {
                audiotools__MD5Final(stream_md5_sum, &(self->md5));

                if (memcmp(stored_md5_sum, stream_md5_sum, 16)) {
                    Py_DECREF((PyObject*)framelist);
                    PyErr_SetString(PyExc_IOError,
                                    "MD5 mismatch at end of stream");
                    return NULL;
                }
            }
        }
    }

    return (PyObject*)framelist;
}


PyObject*
WavPackDecoder_seek(decoders_WavPackDecoder* self, PyObject *args)
{
    long long seeked_offset;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot seek closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "L", &seeked_offset)) {
        return NULL;
    }

    if (seeked_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "cannot seek to negative value");
        return NULL;
    } else if (seeked_offset == 0) {
        /*reset running MD5 sum calculation*/
        audiotools__MD5Init(&(self->md5));
        self->verifying_md5_sum = 1;
    } else {
        /*restrict seeked location to limit of file*/
        const uint32_t total_samples = WavpackGetNumSamples(self->context);
        if (seeked_offset >= total_samples) {
            seeked_offset = total_samples - 1;
        }

        /*seeking partway through file, so cease MD5 sum validation*/
        self->verifying_md5_sum = 0;
    }

    if (WavpackSeekSample(self->context, (uint32_t)seeked_offset)) {
        return Py_BuildValue("I", WavpackGetSampleIndex(self->context));
    } else {
        PyErr_SetString(PyExc_ValueError, "unable to seek to location");
        return NULL;
    }
}

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int pcm_data[],
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames)
{
    const unsigned bytes_per_sample = bits_per_sample / 8;
    unsigned total_samples = pcm_frames * channels;
    const unsigned buffer_size = total_samples * bytes_per_sample;
    unsigned char buffer[buffer_size];
    unsigned char *output_buffer = buffer;
    void (*converter)(int, unsigned char *) =
        int_to_pcm_converter(bits_per_sample, 0, (bits_per_sample > 8) ? 1 : 0);

    for (; total_samples; total_samples--) {
        converter(*pcm_data, output_buffer);
        pcm_data += 1;
        output_buffer += bytes_per_sample;
    }

    audiotools__MD5Update(md5sum, buffer, buffer_size);
}
