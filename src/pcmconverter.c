#include <Python.h>
#include "pcmconv.h"
#include "array.h"
#include "samplerate/samplerate.h"

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

PyMethodDef module_methods[] = {
    {NULL}
};


/*******************************************************
 Downmixer for reducing channel count from many to 2
*******************************************************/

typedef struct {
    PyObject_HEAD

    struct pcmreader_s* pcmreader;
    array_ia* input_channels;
    array_i* empty_channel;
    array_lia* six_channels;
    array_ia* output_channels;
    PyObject* audiotools_pcm;
} pcmconverter_Downmixer;

static PyObject*
Downmixer_sample_rate(pcmconverter_Downmixer *self, void *closure);

static PyObject*
Downmixer_bits_per_sample(pcmconverter_Downmixer *self, void *closure);

static PyObject*
Downmixer_channels(pcmconverter_Downmixer *self, void *closure);

static PyObject*
Downmixer_channel_mask(pcmconverter_Downmixer *self, void *closure);

static PyObject*
Downmixer_read(pcmconverter_Downmixer *self, PyObject *args);

static PyObject*
Downmixer_close(pcmconverter_Downmixer *self, PyObject *args);

static PyObject*
Downmixer_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
Downmixer_dealloc(pcmconverter_Downmixer *self);

int
Downmixer_init(pcmconverter_Downmixer *self, PyObject *args, PyObject *kwds);

PyGetSetDef Downmixer_getseters[] = {
    {"sample_rate", (getter)Downmixer_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)Downmixer_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels", (getter)Downmixer_channels, NULL, "channels", NULL},
    {"channel_mask", (getter)Downmixer_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef Downmixer_methods[] = {
    {"read", (PyCFunction)Downmixer_read, METH_VARARGS, ""},
    {"close", (PyCFunction)Downmixer_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject pcmconverter_DownmixerType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmconverter.Downmixer",     /*tp_name*/
    sizeof(pcmconverter_Downmixer),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Downmixer_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "Downmixer objects",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Downmixer_methods,         /* tp_methods */
    0,                         /* tp_members */
    Downmixer_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Downmixer_init,  /* tp_init */
    0,                         /* tp_alloc */
    Downmixer_new,             /* tp_new */
};

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

    self->ob_type->tp_free((PyObject*)self);
}

int
Downmixer_init(pcmconverter_Downmixer *self, PyObject *args, PyObject *kwds)
{
    self->pcmreader = NULL;
    self->input_channels = array_ia_new();
    self->empty_channel = array_i_new();
    self->six_channels = array_lia_new();
    self->output_channels = array_ia_new();
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
        array_i* left;
        array_i* right;
        const double REAR_GAIN = 0.6;
        const double CENTER_GAIN = 0.7;
        const int SAMPLE_MIN =
        -(1 << (self->pcmreader->bits_per_sample - 1));
        const int SAMPLE_MAX =
        (1 << (self->pcmreader->bits_per_sample - 1)) - 1;

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

        /*convert output to pcm.FrameList object and return it*/
        return array_ia_to_FrameList(self->audiotools_pcm,
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

typedef struct {
    PyObject_HEAD

    struct pcmreader_s* pcmreader;
    array_ia* input_channels;
    SRC_STATE *src_state;
    double ratio;
    unsigned unprocessed_frame_count;
    array_f* unprocessed_samples;
    array_i* processed_samples;
    int sample_rate;
    PyObject* audiotools_pcm;
} pcmconverter_Resampler;

static PyObject*
Resampler_sample_rate(pcmconverter_Resampler *self, void *closure);

static PyObject*
Resampler_bits_per_sample(pcmconverter_Resampler *self, void *closure);

static PyObject*
Resampler_channels(pcmconverter_Resampler *self, void *closure);

static PyObject*
Resampler_channel_mask(pcmconverter_Resampler *self, void *closure);

static PyObject*
Resampler_read(pcmconverter_Resampler *self, PyObject *args);

static PyObject*
Resampler_close(pcmconverter_Resampler *self, PyObject *args);

static PyObject*
Resampler_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
Resampler_dealloc(pcmconverter_Resampler *self);

int
Resampler_init(pcmconverter_Resampler *self, PyObject *args, PyObject *kwds);

PyGetSetDef Resampler_getseters[] = {
    {"sample_rate", (getter)Resampler_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)Resampler_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels", (getter)Resampler_channels, NULL, "channels", NULL},
    {"channel_mask", (getter)Resampler_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef Resampler_methods[] = {
    {"read", (PyCFunction)Resampler_read, METH_VARARGS, ""},
    {"close", (PyCFunction)Resampler_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject pcmconverter_ResamplerType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmconverter.Resampler",     /*tp_name*/
    sizeof(pcmconverter_Resampler),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Resampler_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "Resampler objects",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Resampler_methods,         /* tp_methods */
    0,                         /* tp_members */
    Resampler_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Resampler_init,  /* tp_init */
    0,                         /* tp_alloc */
    Resampler_new,             /* tp_new */
};

static PyObject*
Resampler_sample_rate(pcmconverter_Resampler *self, void *closure)
{
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
Resampler_bits_per_sample(pcmconverter_Resampler *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->bits_per_sample);
}

static PyObject*
Resampler_channels(pcmconverter_Resampler *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->channels);
}

static PyObject*
Resampler_channel_mask(pcmconverter_Resampler *self, void *closure)
{
    return Py_BuildValue("I", self->pcmreader->channel_mask);
}

#define OUTPUT_SAMPLES_LENGTH 0x100000

static PyObject*
Resampler_read(pcmconverter_Resampler *self, PyObject *args)
{
    /*read FrameList from PCMReader*/
    if (self->pcmreader->read(self->pcmreader,
                              4096,
                              self->input_channels)) {
        return NULL;
    } else {
        const unsigned input_frame_count = self->input_channels->_[0]->len;
        const unsigned channels = self->pcmreader->channels;
        SRC_DATA src_data;
        int processing_error;
        static float data_out[OUTPUT_SAMPLES_LENGTH];
        unsigned s = 0;
        unsigned c;
        unsigned i;

        /*populate SRC_DATA from unprocessed samples and FrameList*/
        src_data.input_frames = (self->unprocessed_frame_count +
                                 input_frame_count);
        src_data.data_in = malloc(src_data.input_frames *
                                  self->pcmreader->channels *
                                  sizeof(float));
        src_data.output_frames = (OUTPUT_SAMPLES_LENGTH /
                                  self->pcmreader->channels);
        src_data.data_out = data_out;
        src_data.end_of_input = (input_frame_count == 0);
        src_data.src_ratio = self->ratio;

        /*first append the unprocessed samples*/
        for (i = 0; i < self->unprocessed_samples->len; i++) {
            src_data.data_in[s++] = (float)(self->unprocessed_samples->_[i]);
        }
        /*then append the new input samples*/
        for (i = 0; i < input_frame_count; i++) {
            for (c = 0; c < channels; c++)
                src_data.data_in[s++] = self->input_channels->_[c]->_[i];
        }

        /*run src_process() on self->SRC_STATE and SRC_DATA*/
        if ((processing_error = src_process(self->src_state, &src_data)) != 0) {
            /*some sort of processing error raises ValueError*/
            PyErr_SetString(PyExc_ValueError,
                            src_strerror(processing_error));
            free(src_data.data_in);
            return NULL;
        } else {
            const unsigned processed_sample_count =
                (unsigned)(src_data.output_frames_gen *
                           self->pcmreader->channels);
            array_f* unprocessed_samples = self->unprocessed_samples;
            array_i* processed_samples = self->processed_samples;
            int i;

            /*save unprocessed samples for next run*/
            self->unprocessed_frame_count = (unsigned)(
                src_data.input_frames -
                src_data.input_frames_used);
            unprocessed_samples->reset(unprocessed_samples);
            unprocessed_samples->resize(unprocessed_samples,
                                        self->unprocessed_frame_count *
                                        self->pcmreader->channels);;
            for (i = (unsigned)(src_data.input_frames_used *
                                self->pcmreader->channels);
                 i < (src_data.input_frames * self->pcmreader->channels);
                 i++) {
                a_append(unprocessed_samples, src_data.data_in[i]);
            }

            /*convert processed samples to integer array*/
            processed_samples->reset(processed_samples);
            processed_samples->resize(processed_samples,
                                      processed_sample_count);
            for (i = 0; i < processed_sample_count; i++) {
                a_append(processed_samples, src_data.data_out[i]);
            }

            /*return FrameList*/
            free(src_data.data_in);
            return array_i_to_FrameList(self->audiotools_pcm,
                                        processed_samples,
                                        self->pcmreader->channels,
                                        self->pcmreader->bits_per_sample);
        }
    }
}

static PyObject*
Resampler_close(pcmconverter_Resampler *self, PyObject *args)
{
    self->pcmreader->close(self->pcmreader);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Resampler_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcmconverter_Resampler *self;

    self = (pcmconverter_Resampler *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
Resampler_dealloc(pcmconverter_Resampler *self)
{
    if (self->pcmreader != NULL)
        self->pcmreader->del(self->pcmreader);
    self->input_channels->del(self->input_channels);
    src_delete(self->src_state);
    self->unprocessed_samples->del(self->unprocessed_samples);
    self->processed_samples->del(self->processed_samples);
    Py_XDECREF(self->audiotools_pcm);

    self->ob_type->tp_free((PyObject*)self);
}

int
Resampler_init(pcmconverter_Resampler *self, PyObject *args, PyObject *kwds)
{
    int error;

    self->pcmreader = NULL;
    self->input_channels = array_ia_new();
    self->unprocessed_samples = array_f_new();
    self->processed_samples = array_i_new();
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O&i", pcmreader_converter,
                          &(self->pcmreader),
                          &(self->sample_rate)))
        return -1;

    if (self->sample_rate <= 0) {
        PyErr_SetString(PyExc_ValueError,
                        "new sample rate must be positive");
        return -1;
    }

    self->src_state = src_new(0, self->pcmreader->channels, &error);
    self->ratio = ((double)self->sample_rate /
                   (double)self->pcmreader->sample_rate);

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}


PyMODINIT_FUNC
initpcmconverter(void)
{
    PyObject* m;

    pcmconverter_DownmixerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_DownmixerType) < 0)
        return;

    pcmconverter_ResamplerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmconverter_ResamplerType) < 0)
        return;

    m = Py_InitModule3("pcmconverter", module_methods,
                       "A PCM stream conversion module");

    Py_INCREF(&pcmconverter_DownmixerType);
    PyModule_AddObject(m, "Downmixer",
                       (PyObject *)&pcmconverter_DownmixerType);

    Py_INCREF(&pcmconverter_ResamplerType);
    PyModule_AddObject(m, "Resampler",
                       (PyObject *)&pcmconverter_ResamplerType);
}

#include "samplerate/samplerate.c"
