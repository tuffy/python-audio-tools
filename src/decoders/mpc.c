#include "mpc.h"

static PyObject*
MPCDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds)
{
    decoders_MPCDecoder *self;

    self = (decoders_MPCDecoder *)type->tp_alloc(type, 0);

    return (PyObject *) self;
}

int
MPCDecoder_init(decoders_MPCDecoder *self,
                PyObject *args, PyObject *kwds)
{
    self->audiotools_pcm = NULL;

    return 0;
}

void
MPCDecoder_dealloc(decoders_MPCDecoder *self)
{
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
MPCDecoder_sample_rate(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", 0);
}

static PyObject*
MPCDecoder_bits_per_sample(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", 0);
}

static PyObject*
MPCDecoder_channels(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", 0);
}

static PyObject*
MPCDecoder_channel_mask(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", 0);
}

