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
    char *filename;

    self->reader = NULL;
    self->demux = NULL;
    self->streaminfo = NULL;

    self->closed = 0;

    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    self->reader = (mpc_reader*) malloc(sizeof(mpc_reader));

    if (mpc_reader_init_stdio(self->reader, filename) == MPC_STATUS_FAIL) {
        PyErr_SetString(PyExc_ValueError, "error opening file");
        return -1;
    }

    if ((self->demux = mpc_demux_init(self->reader)) == NULL) {
        PyErr_SetString(PyExc_ValueError, "error initializing demuxer");
        return -1;
    }

    self->streaminfo = (mpc_streaminfo*) malloc(sizeof(mpc_streaminfo));

    mpc_demux_get_info(self->demux, self->streaminfo);

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

static PyObject*
MPCDecoder_read(decoders_MPCDecoder* self, PyObject *args)
{
    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "stream is closed");
        return NULL;
    }

    return NULL;
}

static PyObject*
MPCDecoder_close(decoders_MPCDecoder* self, PyObject *args)
{
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MPCDecoder_enter(decoders_MPCDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
MPCDecoder_exit(decoders_MPCDecoder* self, PyObject *args)
{
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}
