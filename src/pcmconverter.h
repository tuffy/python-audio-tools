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

PyMethodDef module_methods[] = {
    {NULL}
};

typedef struct {
    PyObject_HEAD

    struct pcmreader_s* pcmreader;
    aa_int* input_channels;
    a_int* output_channel;
    PyObject* audiotools_pcm;
} pcmconverter_Averager;

static PyObject*
Averager_sample_rate(pcmconverter_Averager *self, void *closure);

static PyObject*
Averager_bits_per_sample(pcmconverter_Averager *self, void *closure);

static PyObject*
Averager_channels(pcmconverter_Averager *self, void *closure);

static PyObject*
Averager_channel_mask(pcmconverter_Averager *self, void *closure);

static PyObject*
Averager_read(pcmconverter_Averager *self, PyObject *args);

static PyObject*
Averager_close(pcmconverter_Averager *self, PyObject *args);

static PyObject*
Averager_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
Averager_dealloc(pcmconverter_Averager *self);

int
Averager_init(pcmconverter_Averager *self, PyObject *args, PyObject *kwds);

PyGetSetDef Averager_getseters[] = {
    {"sample_rate", (getter)Averager_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)Averager_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels", (getter)Averager_channels, NULL, "channels", NULL},
    {"channel_mask", (getter)Averager_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef Averager_methods[] = {
    {"read", (PyCFunction)Averager_read, METH_VARARGS, ""},
    {"close", (PyCFunction)Averager_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject pcmconverter_AveragerType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmconverter.Averager",     /*tp_name*/
    sizeof(pcmconverter_Averager),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Averager_dealloc, /*tp_dealloc*/
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
    "Averager objects",        /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Averager_methods,          /* tp_methods */
    0,                         /* tp_members */
    Averager_getseters,        /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Averager_init,   /* tp_init */
    0,                         /* tp_alloc */
    Averager_new,              /* tp_new */
};


typedef struct {
    PyObject_HEAD

    struct pcmreader_s* pcmreader;
    aa_int* input_channels;
    a_int* empty_channel;
    al_int* six_channels;
    aa_int* output_channels;
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

struct float_buffer {
    float *_;
    unsigned frames;
    unsigned max_frames;
    unsigned channels;
    unsigned quantization;
    int min_sample;
    int max_sample;
};

static struct float_buffer*
fb_init(unsigned channels,
        unsigned bits_per_sample,
        unsigned max_frames);

static void
fb_free(struct float_buffer *buffer);

/*amount of frames one can place in the buffer's available space*/
static unsigned
fb_available_frames(const struct float_buffer *buffer);

/*increases the frames the buffer can hold by the given amount*/
static void
fb_increase_frame_size(struct float_buffer *buffer, unsigned frames);

/*converts each channel in "samples" to floats and appends them to buffer*/
static void
fb_append_samples(struct float_buffer *buffer, const aa_int *samples);

/*removes the given number of frames from the start of the buffer*/
static void
fb_pop_frames(struct float_buffer *buffer, unsigned frames);

/*quantizes frames in buffer and appends them to samples*/
static void
fb_export_frames(struct float_buffer *buffer, a_int *samples);

typedef struct {
    PyObject_HEAD

    struct pcmreader_s* pcmreader;
    aa_int *pcmreader_channels;      /*a given read() call's input buffer*/
    SRC_STATE *src_state;            /*libsamplerate's internal state*/
    double ratio;                    /*the conversion ratio*/
    struct float_buffer *in_buffer;  /*input floating point samples*/
    struct float_buffer *out_buffer; /*output floating point samples*/
    a_int *output_framelist;         /*a FrameList output buffer*/
    int sample_rate;                 /*the output sample rate*/
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

typedef struct {
    PyObject_HEAD

    struct pcmreader_s* pcmreader;
    int bits_per_sample;
    aa_int* input_channels;
    aa_int* output_channels;
    BitstreamReader* white_noise;
    PyObject* audiotools_pcm;
} pcmconverter_BPSConverter;

static PyObject*
BPSConverter_sample_rate(pcmconverter_BPSConverter *self, void *closure);

static PyObject*
BPSConverter_bits_per_sample(pcmconverter_BPSConverter *self, void *closure);

static PyObject*
BPSConverter_channels(pcmconverter_BPSConverter *self, void *closure);

static PyObject*
BPSConverter_channel_mask(pcmconverter_BPSConverter *self, void *closure);

static PyObject*
BPSConverter_read(pcmconverter_BPSConverter *self, PyObject *args);

static PyObject*
BPSConverter_close(pcmconverter_BPSConverter *self, PyObject *args);

static PyObject*
BPSConverter_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

void
BPSConverter_dealloc(pcmconverter_BPSConverter *self);

int
BPSConverter_init(pcmconverter_BPSConverter *self,
                  PyObject *args, PyObject *kwds);

PyGetSetDef BPSConverter_getseters[] = {
    {"sample_rate", (getter)BPSConverter_sample_rate,
     NULL, "sample rate", NULL},
    {"bits_per_sample", (getter)BPSConverter_bits_per_sample,
     NULL, "bits per sample", NULL},
    {"channels", (getter)BPSConverter_channels,
     NULL, "channels", NULL},
    {"channel_mask", (getter)BPSConverter_channel_mask,
     NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef BPSConverter_methods[] = {
    {"read", (PyCFunction)BPSConverter_read, METH_VARARGS, ""},
    {"close", (PyCFunction)BPSConverter_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject pcmconverter_BPSConverterType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmconverter.BPSConverter",     /*tp_name*/
    sizeof(pcmconverter_BPSConverter),/*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BPSConverter_dealloc, /*tp_dealloc*/
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
    "BPSConverter objects",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    BPSConverter_methods,         /* tp_methods */
    0,                         /* tp_members */
    BPSConverter_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)BPSConverter_init,  /* tp_init */
    0,                         /* tp_alloc */
    BPSConverter_new,             /* tp_new */
};
