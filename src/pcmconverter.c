#include <Python.h>
#include "mod_defs.h"
#include "pcmconv.h"
#include "array.h"
#include "bitstream.h"
#include "samplerate/samplerate.h"
#include "pcmconverter.h"
#include "dither.c"

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

/*******************************************************
 Averager for reducing channel count from many to 1
*******************************************************/

static PyObject*
Averager_sample_rate(pcmconverter_Averager *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->sample_rate);
}

static PyObject*
Averager_bits_per_sample(pcmconverter_Averager *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->bits_per_sample);
}

static PyObject*
Averager_channels(pcmconverter_Averager *self, void *closure)
{
    return Py_BuildValue("i", 1);
}

static PyObject*
Averager_channel_mask(pcmconverter_Averager *self, void *closure)
{
    return Py_BuildValue("i", 0x4);
}

static PyObject*
Averager_read(pcmconverter_Averager *self, PyObject *args)
{
    if (self->pcmreader->read(self->pcmreader,
                              4096,
                              self->input_channels)) {
        /*error occured during call to .read()*/
        return NULL;
    } else {
        unsigned c;
        unsigned i;
        aa_int* input = self->input_channels;
        a_int* output = self->output_channel;
        const unsigned frame_count = input->_[0]->len;
        const unsigned channel_count = input->len;
        PyThreadState *thread_state = PyEval_SaveThread();

        output->reset(output);
        output->resize(output, frame_count);
        for (i = 0; i < frame_count; i++) {
            int64_t accumulator = 0;
            for (c = 0; c < channel_count; c++) {
                accumulator += input->_[c]->_[i];
            }
            a_append(output, (int)(accumulator / channel_count));
        }

        PyEval_RestoreThread(thread_state);
        return a_int_to_FrameList(self->audiotools_pcm,
                                  output,
                                  1,
                                  self->pcmreader->bits_per_sample);
    }
}

static PyObject*
Averager_close(pcmconverter_Averager *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Averager_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_Averager *self;

    self = (pcmconverter_Averager *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
Averager_dealloc(pcmconverter_Averager *self)
{
    if (self->pcmreader != NULL)
        self->pcmreader->del(self->pcmreader);
    self->input_channels->del(self->input_channels);
    self->output_channel->del(self->output_channel);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
Averager_init(pcmconverter_Averager *self, PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->input_channels = aa_int_new();
    self->output_channel = a_int_new();
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&", pcmreader_converter,
                          &(self->pcmreader)))
        return -1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}


/*******************************************************
 Downmixer for reducing channel count from many to 2
*******************************************************/

PyObject*
Downmixer_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_Downmixer *self;

    self = (pcmconverter_Downmixer *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
Downmixer_dealloc(pcmconverter_Downmixer *self)
{
    if (self->pcmreader != NULL)
        self->pcmreader->del(self->pcmreader);
    self->input_channels->del(self->input_channels);
    self->empty_channel->del(self->empty_channel);
    self->six_channels->del(self->six_channels);
    self->output_channels->del(self->output_channels);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
Downmixer_init(pcmconverter_Downmixer *self, PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->input_channels = aa_int_new();
    self->empty_channel = a_int_new();
    self->six_channels = al_int_new();
    self->output_channels = aa_int_new();
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&", pcmreader_converter,
                          &(self->pcmreader)))
        return -1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

static PyObject*
Downmixer_sample_rate(pcmconverter_Downmixer *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->sample_rate);
}

static PyObject*
Downmixer_bits_per_sample(pcmconverter_Downmixer *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->bits_per_sample);
}

static PyObject*
Downmixer_channels(pcmconverter_Downmixer *self, void *closure)
{
    return Py_BuildValue("I", 2);
}

static PyObject*
Downmixer_channel_mask(pcmconverter_Downmixer *self, void *closure)
{
    return Py_BuildValue("I", 0x3);
}

static PyObject*
Downmixer_read(pcmconverter_Downmixer *self, PyObject *args)
{
    if (self->pcmreader->read(self->pcmreader,
                              4096,
                              self->input_channels)) {
        /*error occured during call to .read()*/
        return NULL;
    } else {
        unsigned i;
        const unsigned frame_count = self->input_channels->_[0]->len;
        unsigned input_mask;
        unsigned mask;
        unsigned channel = 0;
        a_int* left;
        a_int* right;
        const double REAR_GAIN = 0.6;
        const double CENTER_GAIN = 0.7;
        const int SAMPLE_MIN =
        -(1 << (self->pcmreader->bits_per_sample - 1));
        const int SAMPLE_MAX =
        (1 << (self->pcmreader->bits_per_sample - 1)) - 1;
        PyThreadState *thread_state = PyEval_SaveThread();

        /*setup intermediate arrays*/
        if (self->empty_channel->len != frame_count)
            self->empty_channel->mset(self->empty_channel, frame_count, 0);
        self->six_channels->reset(self->six_channels);

        /*ensure PCMReader's channel mask is defined*/
        if (self->pcmreader->channel_mask != 0) {
            input_mask = self->pcmreader->channel_mask;
        } else {
            /*invent channel mask for input based on channel count*/
            switch (self->pcmreader->channels) {
            case 0:
                input_mask = 0x0;
                break;
            case 1:
                /*fC*/
                input_mask = 0x4;
                break;
            case 2:
                /*fL, fR*/
                input_mask = 0x3;
                break;
            case 3:
                /*fL, fR, fC*/
                input_mask = 0x7;
                break;
            case 4:
                /*fL, fR, bL, bR*/
                input_mask = 0x33;
                break;
            case 5:
                /*fL, fR, fC, bL, bR*/
                input_mask = 0x37;
                break;
            case 6:
                /*fL, fR, fC, LFE, bL, bR*/
                input_mask = 0x3F;
                break;
            default:
                /*more than 6 channels
                  fL, fR, fC, LFE, bL, bR, ...*/
                input_mask = 0x3F;
                break;
            }
        }

        /*split pcm.FrameList into 6 channels*/
        for (mask = 1; mask <= 0x20; mask <<= 1) {
            if (mask & input_mask) {
                /*channel exists in PCMReader object*/
                self->input_channels->_[channel]->link(
                    self->input_channels->_[channel],
                    self->six_channels->append(self->six_channels));

                channel++;
            } else {
                /*PCMReader object doesn't contain that channel
                  so pad with a channel of empty samples*/
                self->empty_channel->link(
                    self->empty_channel,
                    self->six_channels->append(self->six_channels));
            }
        }

        /*reset output and perform downmixing across 6 channels*/
        self->output_channels->reset(self->output_channels);
        left = self->output_channels->append(self->output_channels);
        left->resize(left, frame_count);
        right = self->output_channels->append(self->output_channels);
        right->resize(right, frame_count);

        for (i = 0; i < frame_count; i++) {
            /*bM (back mono) = 0.7 * (bL + bR)*/
            const double mono_rear = 0.7 * (self->six_channels->_[4]->_[i] +
                                            self->six_channels->_[5]->_[i]);

            /*left  = fL + rear_gain * bM + center_gain * fC*/
            const int left_i = (int)round(
                self->six_channels->_[0]->_[i] +
                REAR_GAIN * mono_rear +
                CENTER_GAIN * self->six_channels->_[2]->_[i]);

            /*right = fR - rear_gain * bM + center_gain * fC*/
            const int right_i = (int)round(
                self->six_channels->_[1]->_[i] -
                REAR_GAIN * mono_rear +
                CENTER_GAIN * self->six_channels->_[2]->_[i]);

            a_append(left, MAX(MIN(left_i, SAMPLE_MAX), SAMPLE_MIN));
            a_append(right, MAX(MIN(right_i, SAMPLE_MAX), SAMPLE_MIN));
        }

        PyEval_RestoreThread(thread_state);
        /*convert output to pcm.FrameList object and return it*/
        return aa_int_to_FrameList(self->audiotools_pcm,
                                   self->output_channels,
                                   self->pcmreader->bits_per_sample);
    }
}

static PyObject*
Downmixer_close(pcmconverter_Downmixer *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);

    Py_INCREF(Py_None);
    return Py_None;
}


/*******************************************************
 Resampler for changing a PCMReader's sample rate
*******************************************************/

#define RESAMPLER_BLOCK_SIZE 4096

static PyObject*
Resampler_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_Resampler *self;

    self = (pcmconverter_Resampler *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
Resampler_init(pcmconverter_Resampler *self, PyObject *args, PyObject *kwds)
{
    int error;

    self->pcmreader = NULL;
    self->pcmreader_channels = aa_int_new();
    self->src_state = NULL;
    self->in_buffer = NULL;
    self->out_buffer = NULL;
    self->output_framelist = a_int_new();
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&i", pcmreader_converter,
                          &(self->pcmreader),
                          &(self->sample_rate)))
        return -1;

    /*basic sanity checking*/
    if (self->sample_rate <= 0) {
        PyErr_SetString(PyExc_ValueError,
                        "new sample rate must be positive");
        return -1;
    }

    /*allocate fresh resampler state*/
    self->src_state = src_new(SRC_SINC_BEST_QUALITY,
                              self->pcmreader->channels,
                              &error);

    /*calculate ratio based on new and old sample rates*/
    self->ratio = ((double)self->sample_rate /
                   (double)self->pcmreader->sample_rate);

    /*allocate input and output buffers*/
    self->in_buffer = fb_init(
        self->pcmreader->channels,
        self->pcmreader->bits_per_sample,
        RESAMPLER_BLOCK_SIZE);
    self->out_buffer = fb_init(
        self->pcmreader->channels,
        self->pcmreader->bits_per_sample,
        (unsigned)(ceil(RESAMPLER_BLOCK_SIZE * self->ratio)));

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
Resampler_dealloc(pcmconverter_Resampler *self)
{
    if (self->pcmreader != NULL)
        self->pcmreader->del(self->pcmreader);

    self->pcmreader_channels->del(self->pcmreader_channels);
    if (self->src_state != NULL)
        src_delete(self->src_state);
    if (self->in_buffer != NULL)
        fb_free(self->in_buffer);
    if (self->out_buffer != NULL)
        fb_free(self->out_buffer);
    self->output_framelist->del(self->output_framelist);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
Resampler_read(pcmconverter_Resampler *self, PyObject *args)
{
    int end_of_input;

    do {
        SRC_DATA src_data;
        int process_result;

        /*read integer samples from PCMReader*/
        if (self->pcmreader->read(self->pcmreader,
                                  RESAMPLER_BLOCK_SIZE,
                                  self->pcmreader_channels)) {
            /*propagate PCMReader error*/
            return NULL;
        }

        fb_append_samples(self->in_buffer, self->pcmreader_channels);
        end_of_input = (self->in_buffer->frames == 0);

        /*run conversion on input float buffer and get output float buffer*/
        src_data.data_in = self->in_buffer->_;
        src_data.input_frames = self->in_buffer->frames;
        src_data.data_out = self->out_buffer->_;
        src_data.output_frames = self->out_buffer->max_frames;
        src_data.src_ratio = self->ratio;
        src_data.end_of_input = end_of_input;

        if ((process_result = src_process(self->src_state, &src_data)) != 0) {
            PyErr_SetString(PyExc_ValueError, src_strerror(process_result));
            return NULL;
        }

        /*update buffer sizes based on conversion results*/
        fb_pop_frames(self->in_buffer, (unsigned)src_data.input_frames_used);

        if (self->in_buffer->frames > 0) {
            /*output buffer too small to hold all of input,
              so expand output buffer to double its current size*/
            fb_increase_frame_size(self->out_buffer,
                                   self->out_buffer->max_frames);
        }

        self->out_buffer->frames += src_data.output_frames_gen;

        /*read as necessary until there's some output or no more input*/
    } while ((self->out_buffer->frames == 0) && (!end_of_input));

    /*convert out buffer to framelist and deduct outputted frames*/
    self->output_framelist->reset(self->output_framelist);
    fb_export_frames(self->out_buffer, self->output_framelist);
    self->out_buffer->frames = 0;

    return a_int_to_FrameList(self->audiotools_pcm,
                              self->output_framelist,
                              self->pcmreader->channels,
                              self->pcmreader->bits_per_sample);
}

static PyObject*
Resampler_close(pcmconverter_Resampler *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Resampler_sample_rate(pcmconverter_Resampler *self, void *closure)
{
    const int sample_rate = self->sample_rate;
    return Py_BuildValue("i", sample_rate);
}

static PyObject*
Resampler_bits_per_sample(pcmconverter_Resampler *self, void *closure)
{
    const int bits_per_sample = self->pcmreader->bits_per_sample;
    return Py_BuildValue("i", bits_per_sample);
}

static PyObject*
Resampler_channels(pcmconverter_Resampler *self, void *closure)
{
    const int channels = self->pcmreader->channels;
    return Py_BuildValue("i", channels);
}

static PyObject*
Resampler_channel_mask(pcmconverter_Resampler *self, void *closure)
{
    const int channel_mask = self->pcmreader->channel_mask;
    return Py_BuildValue("i", channel_mask);
}

static struct float_buffer*
fb_init(unsigned channels,
        unsigned bits_per_sample,
        unsigned max_frames)
{
    struct float_buffer *buffer = malloc(sizeof(struct float_buffer));

    buffer->_ = malloc(sizeof(float) * max_frames * channels);
    buffer->frames = 0;
    buffer->max_frames = max_frames;
    buffer->channels = channels;
    buffer->quantization = (1 << (bits_per_sample - 1));
    buffer->min_sample = -(1 << (bits_per_sample - 1));
    buffer->max_sample = (1 << (bits_per_sample - 1)) - 1;

    return buffer;
}

static void
fb_free(struct float_buffer *buffer)
{
    free(buffer->_);
    free(buffer);
}

static unsigned
fb_available_frames(const struct float_buffer *buffer)
{
    return buffer->max_frames - buffer->frames;
}

static void
fb_increase_frame_size(struct float_buffer *buffer, unsigned frames)
{
    buffer->max_frames += frames;
    buffer->_ = realloc(buffer->_,
                        sizeof(float) * buffer->max_frames * buffer->channels);
}

static void
fb_append_samples(struct float_buffer *buffer, const aa_int *samples)
{
    const unsigned added_frames = samples->_[0]->len;
    const unsigned quantization = buffer->quantization;
    unsigned c;

    assert(samples->len == buffer->channels);

    /*allocate more space in buffer if needed*/
    if (added_frames > fb_available_frames(buffer)) {
        fb_increase_frame_size(buffer,
                               added_frames - fb_available_frames(buffer));
    }

    /*quantize samples and append them to buffer*/
    for (c = 0; c < samples->len; c++) {
        const a_int *channel = samples->_[c];
        unsigned i;
        for (i = 0; i < channel->len; i++) {
            const int sample = channel->_[i];
            buffer->_[(buffer->frames + i) * buffer->channels + c] =
                (float)sample / quantization;
        }
    }

    /*update buffer length indicator*/
    buffer->frames += added_frames;
}

static void
fb_pop_frames(struct float_buffer *buffer, unsigned frames)
{
    assert(frames <= buffer->frames);

    /*shift samples down based on frames and channels*/
    memmove(buffer->_,
            buffer->_ + (frames * buffer->channels),
            (buffer->frames - frames) * buffer->channels * sizeof(float));

    /*update buffer size*/
    buffer->frames -= frames;
}

static void
fb_export_frames(struct float_buffer *buffer, a_int *samples) {
    const unsigned buffer_samples = buffer->frames * buffer->channels;
    const unsigned quantization = buffer->quantization;
    const int min_sample = buffer->min_sample;
    const int max_sample = buffer->max_sample;
    unsigned i;

    samples->resize_for(samples, buffer_samples);
    for (i = 0; i < buffer_samples; i++) {
        const int sample = (int)(buffer->_[i] * quantization);
        a_append(samples, MAX(MIN(sample, max_sample), min_sample));
    }
}

static unsigned
read_os_random(PyObject* os_module,
               uint8_t* buffer,
               unsigned buffer_size);

static void
close_os_random(PyObject* os_module);

static void
free_os_random(PyObject* os_module);

static PyObject*
BPSConverter_sample_rate(pcmconverter_BPSConverter *self, void *closure)
{
    return Py_BuildValue("i", self->pcmreader->sample_rate);
}

static PyObject*
BPSConverter_bits_per_sample(pcmconverter_BPSConverter *self, void *closure)
{
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
BPSConverter_channels(pcmconverter_BPSConverter *self, void *closure)
{
    return Py_BuildValue("i", self->pcmreader->channels);
}

static PyObject*
BPSConverter_channel_mask(pcmconverter_BPSConverter *self, void *closure)
{
    return Py_BuildValue("i", self->pcmreader->channel_mask);
}

static PyObject*
BPSConverter_read(pcmconverter_BPSConverter *self, PyObject *args)
{
    /*read FrameList from PCMReader*/
    if (self->pcmreader->read(self->pcmreader,
                              4096,
                              self->input_channels)) {
        return NULL;
    } else {
        /*convert old bits-per-sample to new bits-per-sample using shifts*/
        if (self->bits_per_sample < self->pcmreader->bits_per_sample) {
            BitstreamReader* white_noise = self->white_noise;

            /*decreasing bits-per-sample is a right shift*/
            if (!setjmp(*br_try(white_noise))) {
                const unsigned shift =
                    self->pcmreader->bits_per_sample - self->bits_per_sample;
                unsigned c;

                self->output_channels->reset(self->output_channels);

                for (c = 0; c < self->input_channels->len; c++) {
                    a_int* input_channel =
                        self->input_channels->_[c];
                    a_int* output_channel =
                        self->output_channels->append(self->output_channels);
                    unsigned i;

                    output_channel->resize(output_channel, input_channel->len);
                    for (i = 0; i < input_channel->len; i++) {
                        /*and add apply white noise dither
                          taken from os.random()*/
                        a_append(output_channel,
                                 (input_channel->_[i] >> shift) ^
                                 white_noise->read(white_noise, 1));
                    }
                }

                br_etry(white_noise);
                return aa_int_to_FrameList(self->audiotools_pcm,
                                           self->output_channels,
                                           self->bits_per_sample);
            } else {
                /*I/O error reading white noise from os.random()*/
                br_etry(white_noise);
                PyErr_SetString(
                    PyExc_IOError,
                    "I/O error reading dither data from os.urandom");
                return NULL;
            }
        } else if (self->bits_per_sample > self->pcmreader->bits_per_sample) {
            /*increasing bits-per-sample is a simple left shift*/
            const unsigned shift =
                self->bits_per_sample - self->pcmreader->bits_per_sample;
            unsigned c;

            self->output_channels->reset(self->output_channels);

            for (c = 0; c < self->input_channels->len; c++) {
                a_int* input_channel =
                    self->input_channels->_[c];
                a_int* output_channel =
                    self->output_channels->append(self->output_channels);
                unsigned i;

                output_channel->resize(output_channel, input_channel->len);
                for (i = 0; i < input_channel->len; i++) {
                    a_append(output_channel, input_channel->_[i] << shift);
                }
            }

            return aa_int_to_FrameList(self->audiotools_pcm,
                                       self->output_channels,
                                       self->bits_per_sample);
        } else {
            /*leaving bits-per-sample unchanged returns FrameList as-is*/
            return aa_int_to_FrameList(self->audiotools_pcm,
                                       self->input_channels,
                                       self->bits_per_sample);
        }
    }
}

static PyObject*
BPSConverter_close(pcmconverter_BPSConverter *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BPSConverter_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_BPSConverter *self;

    self = (pcmconverter_BPSConverter *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
BPSConverter_dealloc(pcmconverter_BPSConverter *self)
{
    if (self->pcmreader != NULL)
        self->pcmreader->del(self->pcmreader);
    self->input_channels->del(self->input_channels);
    self->output_channels->del(self->output_channels);
    Py_XDECREF(self->audiotools_pcm);
    if (self->white_noise != NULL)
        self->white_noise->close(self->white_noise);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
BPSConverter_init(pcmconverter_BPSConverter *self,
                  PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->input_channels = aa_int_new();
    self->output_channels = aa_int_new();
    self->audiotools_pcm = NULL;
    self->white_noise = NULL;

    if (!PyArg_ParseTuple(args, "O&i", pcmreader_converter,
                          &(self->pcmreader),
                          &(self->bits_per_sample)))
        return -1;

    /*ensure bits per sample is supported*/
    switch (self->bits_per_sample) {
    case 8:
    case 16:
    case 24:
        break;
    default:
        PyErr_SetString(PyExc_ValueError,
                        "new bits per sample must be 8, 16 or 24");
        return -1;
    }

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    if ((self->white_noise = open_dither()) == NULL)
        return -1;

    return 0;
}

MOD_INIT(pcmconverter)
{
    PyObject* m;

    MOD_DEF(m, "pcmconverter", "a PCM stream conversion module",
            module_methods)

    pcmconverter_AveragerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_AveragerType) < 0)
        return MOD_ERROR_VAL;

    pcmconverter_DownmixerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_DownmixerType) < 0)
        return MOD_ERROR_VAL;

    pcmconverter_ResamplerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_ResamplerType) < 0)
        return MOD_ERROR_VAL;

    pcmconverter_BPSConverterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_BPSConverterType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&pcmconverter_AveragerType);
    PyModule_AddObject(m, "Averager",
                       (PyObject *)&pcmconverter_AveragerType);

    Py_INCREF(&pcmconverter_DownmixerType);
    PyModule_AddObject(m, "Downmixer",
                       (PyObject *)&pcmconverter_DownmixerType);

    Py_INCREF(&pcmconverter_ResamplerType);
    PyModule_AddObject(m, "Resampler",
                       (PyObject *)&pcmconverter_ResamplerType);

    Py_INCREF(&pcmconverter_BPSConverterType);
    PyModule_AddObject(m, "BPSConverter",
                       (PyObject *)&pcmconverter_BPSConverterType);

    return MOD_SUCCESS_VAL(m);
}
