#include <Python.h>
#include "mod_defs.h"
#include "framelist.h"
#include "pcmreader.h"
#include "pcm_conv.h"
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

#define CHUNK_SIZE 4096

/*******************************************************
 Averager for reducing channel count from many to 1
*******************************************************/

static PyObject*
Averager_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_Averager *self;

    self = (pcmconverter_Averager *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
Averager_init(pcmconverter_Averager *self, PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&",
                          py_obj_to_pcmreader,
                          &(self->pcmreader)))
        return -1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
Averager_dealloc(pcmconverter_Averager *self)
{
    if (self->pcmreader)
        self->pcmreader->del(self->pcmreader);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

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
    const unsigned channel_count = self->pcmreader->channels;
    int pcm_data[CHUNK_SIZE * channel_count];
    const unsigned frames_read = self->pcmreader->read(self->pcmreader,
                                                       CHUNK_SIZE,
                                                       pcm_data);
    pcm_FrameList *framelist;
    unsigned i;

    if (!frames_read && (self->pcmreader->status != PCM_OK)) {
        /*some read error occurred*/
        return NULL;
    }

    framelist = new_FrameList(self->audiotools_pcm,
                              1,
                              self->pcmreader->bits_per_sample,
                              frames_read);

    for (i = 0; i < frames_read; i++) {
        int64_t accumulator = 0;
        unsigned c;
        for (c = 0; c < channel_count; c++) {
            accumulator += get_sample(pcm_data, c, channel_count, i);
        }
        put_sample(framelist->samples, 0, 1, i,
                   (int)(accumulator / channel_count));
    }

    return (PyObject*)framelist;
}

static PyObject*
Averager_close(pcmconverter_Averager *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
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
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
Downmixer_init(pcmconverter_Downmixer *self, PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&",
                          py_obj_to_pcmreader,
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
    const double REAR_GAIN = 0.6;
    const double CENTER_GAIN = 0.7;
    const int SAMPLE_MIN = -(1 << (self->pcmreader->bits_per_sample - 1));
    const int SAMPLE_MAX = (1 << (self->pcmreader->bits_per_sample - 1)) - 1;
    unsigned mask;
    unsigned input_mask;
    int pcm_data[CHUNK_SIZE * self->pcmreader->channels];
    const unsigned frames_read = self->pcmreader->read(self->pcmreader,
                                                       CHUNK_SIZE,
                                                       pcm_data);
    pcm_FrameList *framelist;
    unsigned input_channel = 0;
    unsigned output_channel = 0;
    unsigned i;
    static int fL[CHUNK_SIZE];
    static int fR[CHUNK_SIZE];
    static int fC[CHUNK_SIZE];
    static int LFE[CHUNK_SIZE];
    static int bL[CHUNK_SIZE];
    static int bR[CHUNK_SIZE];
    int *six_channels[] = {fL, fR, fC, LFE, bL, bR};

    if (!frames_read && (self->pcmreader->status != PCM_OK)) {
        return NULL;
    }

    framelist = new_FrameList(self->audiotools_pcm,
                              2,
                              self->pcmreader->bits_per_sample,
                              frames_read);

    /*ensure PCMReader's channel mask is defined*/
    if (self->pcmreader->channel_mask != 0) {
        input_mask = self->pcmreader->channel_mask;
    } else {
        /*invent channel mask for input based on channel count*/
        switch (self->pcmreader->channels) {
        case 0: input_mask = 0x0; break;
        case 1: /*fC*/ input_mask = 0x4; break;
        case 2: /*fL, fR*/ input_mask = 0x3; break;
        case 3: /*fL, fR, fC*/ input_mask = 0x7; break;
        case 4: /*fL, fR, bL, bR*/ input_mask = 0x33; break;
        case 5: /*fL, fR, fC, bL, bR*/ input_mask = 0x37; break;
        case 6: /*fL, fR, fC, LFE, bL, bR*/ input_mask = 0x3F; break;
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
            /*PCMReader contains that channel*/
            get_channel_data(pcm_data,
                             input_channel++,
                             self->pcmreader->channels,
                             frames_read,
                             six_channels[output_channel++]);
        } else {
            /*PCMReader object doesn't contain that channel
              so pad with a channel of empty samples*/
            blank_channel_data(frames_read, six_channels[output_channel++]);
        }
    }

    for (i = 0; i < frames_read; i++) {
        /*bM (back mono) = 0.7 * (bL + bR)*/
        const double mono_rear = 0.7 * (bL[i] + bR[i]);

        /*left  = fL + rear_gain * bM + center_gain * fC*/
        const long int left_i =
            lround(fL[i] + REAR_GAIN * mono_rear + CENTER_GAIN * fC[i]);

        /*right = fR - rear_gain * bM + center_gain * fC*/
        const long int right_i =
            lround(fR[i] - REAR_GAIN * mono_rear + CENTER_GAIN * fC[i]);

        put_sample(framelist->samples, 0, 2, i,
                   (int)(MAX(MIN(left_i, SAMPLE_MAX), SAMPLE_MIN)));
        put_sample(framelist->samples, 1, 2, i,
                   (int)(MAX(MIN(right_i, SAMPLE_MAX), SAMPLE_MIN)));
    }

    return (PyObject*)framelist;
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

/*the amount of PCM frames to resample at once*/
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
    self->src_state = NULL;
    self->src_data.data_in = NULL;
    self->src_data.data_out = NULL;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&i",
                          py_obj_to_pcmreader,
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

    /*allocate fresh resampler I/O state*/
    self->src_data.data_in =
        malloc(sizeof(float) * RESAMPLER_BLOCK_SIZE * self->pcmreader->channels);

    self->src_data.input_frames = 0;

    self->src_data.data_out =
        malloc(sizeof(float) * RESAMPLER_BLOCK_SIZE * self->pcmreader->channels);

    self->src_data.output_frames = RESAMPLER_BLOCK_SIZE;

    self->src_data.src_ratio = ((double)self->sample_rate /
                                (double)self->pcmreader->sample_rate);

    self->src_data.end_of_input = 0;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
Resampler_dealloc(pcmconverter_Resampler *self)
{
    if (self->pcmreader)
        self->pcmreader->del(self->pcmreader);
    if (self->src_state)
        src_delete(self->src_state);
    free(self->src_data.data_in);
    free(self->src_data.data_out);
    Py_XDECREF(self->audiotools_pcm);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
Resampler_read(pcmconverter_Resampler *self, PyObject *args)
{
    /*get data from PCMReader*/
    const unsigned channels = self->pcmreader->channels;
    const unsigned bits_per_sample = self->pcmreader->bits_per_sample;
    int pcm_data[RESAMPLER_BLOCK_SIZE * channels];
    const unsigned frames_read =
        self->pcmreader->read(
            self->pcmreader,
            (unsigned)(RESAMPLER_BLOCK_SIZE - self->src_data.input_frames),
            pcm_data);
    int process_result;
    pcm_FrameList *framelist;

    if (!frames_read && (self->pcmreader->status != PCM_OK)) {
        return NULL;
    }

    /*convert data to floats and append them to input buffer*/
    int_to_float_converter(
        bits_per_sample)(frames_read * channels,
                         pcm_data,
                         self->src_data.data_in +
                         (self->src_data.input_frames * channels));
    self->src_data.input_frames += frames_read;
    self->src_data.end_of_input = (frames_read == 0);

    /*run conversion on input data*/
    if ((process_result =
         src_process(self->src_state, &(self->src_data))) != 0) {
        PyErr_SetString(PyExc_ValueError, src_strerror(process_result));
        return NULL;
    }

    /*preserve any leftover input data*/
    memmove(self->src_data.data_in,
            self->src_data.data_in +
            (self->src_data.input_frames_used * channels),
            (self->src_data.input_frames -
             self->src_data.input_frames_used) * channels * sizeof(float));
    self->src_data.input_frames -= self->src_data.input_frames_used;

    /*build FrameList from output data*/
    framelist = new_FrameList(self->audiotools_pcm,
                              channels,
                              bits_per_sample,
                              (unsigned)(self->src_data.output_frames_gen));
    float_to_int_converter(
        bits_per_sample)(framelist->samples_length,
                         self->src_data.data_out,
                         framelist->samples);

    /*return built FrameList*/
    return (PyObject*)framelist;
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

static unsigned
read_os_random(void *user_data,
               uint8_t* buffer,
               unsigned buffer_size);

static int
close_os_random(void *user_data);

static void
free_os_random(void *user_data);

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
    if (self->white_noise != NULL)
        self->white_noise->close(self->white_noise);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

int
BPSConverter_init(pcmconverter_BPSConverter *self,
                  PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->white_noise = NULL;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&i",
                          py_obj_to_pcmreader,
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
    int shift = self->bits_per_sample - self->pcmreader->bits_per_sample;

    /*read FrameList from PCMReader*/
    pcm_FrameList *framelist = new_FrameList(
        self->audiotools_pcm,
        self->pcmreader->channels,
        self->bits_per_sample,
        CHUNK_SIZE);

    const unsigned frames_read =
        self->pcmreader->read(self->pcmreader,
                              CHUNK_SIZE,
                              framelist->samples);

    unsigned i;

    if (!frames_read && (self->pcmreader->status != PCM_OK)) {
        Py_DECREF((PyObject*)framelist);
        return NULL;
    }

    framelist->frames = frames_read;
    framelist->samples_length = frames_read * framelist->channels;

    if (shift > 0) {
        /*going from fewer bits-per-sample to more, like 16 to 24 bps
          so perform left shift on each sample*/
        for (i = 0; i < framelist->samples_length; i++) {
            framelist->samples[i] <<= shift;
        }
    } else if (shift < 0) {
        /*going from more bits-per-sample to fewer, like 24bps to 16
          so perform right shift on each sample and add dither*/
        BitstreamReader *white_noise = self->white_noise;
        br_read_f read = white_noise->read;

        shift = abs(shift);
        for (i = 0; i < framelist->samples_length; i++) {
            framelist->samples[i] >>= shift;
            framelist->samples[i] |= read(white_noise, 1);
        }
    }

    return (PyObject*)framelist;
}

static PyObject*
BPSConverter_close(pcmconverter_BPSConverter *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject*
BufferedPCMReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_BufferedPCMReader *self;

    self = (pcmconverter_BufferedPCMReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BufferedPCMReader_init(pcmconverter_BufferedPCMReader *self,
                       PyObject *args, PyObject *kwds)
{
    self->closed = 0;
    self->pcmreader = NULL;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&",
                          py_obj_to_pcmreader,
                          &(self->pcmreader)))
        return -1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
BufferedPCMReader_dealloc(pcmconverter_BufferedPCMReader *self)
{
    if (self->pcmreader)
        self->pcmreader->del(self->pcmreader);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
BufferedPCMReader_sample_rate(pcmconverter_BufferedPCMReader *self,
                              void *closure)
{
    return Py_BuildValue("I", self->pcmreader->sample_rate);
}

static PyObject*
BufferedPCMReader_bits_per_sample(pcmconverter_BufferedPCMReader *self,
                                  void *closure)
{
    return Py_BuildValue("I", self->pcmreader->bits_per_sample);
}

static PyObject*
BufferedPCMReader_channels(pcmconverter_BufferedPCMReader *self,
                           void *closure)
{
    return Py_BuildValue("I", self->pcmreader->channels);
}

static PyObject*
BufferedPCMReader_channel_mask(pcmconverter_BufferedPCMReader *self,
                               void *closure)
{
    return Py_BuildValue("I", self->pcmreader->channel_mask);
}

static PyObject*
BufferedPCMReader_read(pcmconverter_BufferedPCMReader *self, PyObject *args)
{
    int pcm_frames;
    pcm_FrameList *framelist;
    unsigned frames_read;

    if (!PyArg_ParseTuple(args, "i", &pcm_frames)) {
        return NULL;
    } else if (pcm_frames <= 0) {
        PyErr_SetString(PyExc_ValueError, "PCM frames must be >= 1");
        return NULL;
    } else if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read from closed stream");
        return NULL;
    }

    /*generate FrameList to populate*/
    framelist = new_FrameList(self->audiotools_pcm,
                              self->pcmreader->channels,
                              self->pcmreader->bits_per_sample,
                              pcm_frames);

    /*populate FrameList from sub-pcmreader*/
    frames_read = self->pcmreader->read(self->pcmreader,
                                        pcm_frames,
                                        framelist->samples);

    /*free FrameList and return error if generated by sub-pcmreader*/
    if (!frames_read && (self->pcmreader->status != PCM_OK)) {
        Py_DECREF((PyObject*)framelist);
        PyErr_SetString(PyExc_IOError, "I/O error reading from stream");
        return NULL;
    }

    /*adjust size of FrameList if necessary*/
    if (frames_read != pcm_frames) {
        framelist->frames = frames_read;
        framelist->samples_length = framelist->frames * framelist->channels;
    }

    /*return fresh FrameList object*/
    return (PyObject*)framelist;
}

static PyObject*
BufferedPCMReader_close(pcmconverter_BufferedPCMReader *self, PyObject *args)
{
    if (!self->closed) {
        self->closed = 1;
        self->pcmreader->close(self->pcmreader);
    }
    Py_INCREF(Py_None);
    return Py_None;
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

    pcmconverter_BufferedPCMReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_BufferedPCMReaderType) < 0)
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

    Py_INCREF(&pcmconverter_BufferedPCMReaderType);
    PyModule_AddObject(m, "BufferedPCMReader",
                       (PyObject *)&pcmconverter_BufferedPCMReaderType);

    return MOD_SUCCESS_VAL(m);
}
