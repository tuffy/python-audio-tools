#include "mpc.h"
#include "../framelist.h"

#define BITS_PER_SAMPLE 16

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

    memset(&self->reader, 0, sizeof(self->reader));
    self->demux = NULL;
    memset(&self->streaminfo, 0, sizeof(self->streaminfo));
    memset(&self->frameinfo, 0, sizeof(self->frameinfo));
    memset(&self->framebuffer, 0, sizeof(self->framebuffer));

    self->closed = 0;

    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    if (mpc_reader_init_stdio(&self->reader, filename) == MPC_STATUS_FAIL) {
        PyErr_SetString(PyExc_ValueError, "error opening file");
        return -1;
    }

    if ((self->demux = mpc_demux_init(&self->reader)) == NULL) {
        PyErr_SetString(PyExc_ValueError, "error initializing demuxer");
        return -1;
    }

    mpc_demux_get_info(self->demux, &self->streaminfo);

    self->frameinfo.buffer = self->framebuffer;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
MPCDecoder_dealloc(decoders_MPCDecoder *self)
{
    Py_XDECREF(self->audiotools_pcm);

    if (self->demux) {
        mpc_demux_exit(self->demux);
    }

    if (self->reader.data) {
        mpc_reader_exit_stdio(&self->reader);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
MPCDecoder_sample_rate(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->streaminfo.sample_freq);
}

static PyObject*
MPCDecoder_bits_per_sample(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", BITS_PER_SAMPLE);
}

static PyObject*
MPCDecoder_channels(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->streaminfo.channels);
}

static PyObject*
MPCDecoder_channel_mask(decoders_MPCDecoder *self, void *closure)
{
    return Py_BuildValue("i", 0);
}

static PyObject*
MPCDecoder_read(decoders_MPCDecoder* self, PyObject *args)
{
    pcm_FrameList *frame;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "stream is closed");
        return NULL;
    }

    if (mpc_demux_decode(self->demux, &self->frameinfo) == MPC_STATUS_FAIL) {
        PyErr_SetString(PyExc_ValueError, "error decoding MPC frame");
        return NULL;
    }

    if (self->frameinfo.bits == -1) {
        return empty_FrameList(self->audiotools_pcm,
                               self->streaminfo.channels,
                               BITS_PER_SAMPLE);
    }

    frame = new_FrameList(self->audiotools_pcm,
                          self->streaminfo.channels,
                          BITS_PER_SAMPLE,
                          self->frameinfo.samples);

#ifdef MPC_FIXED_POINT
    memcpy(frame->samples,
           self->frameinfo.buffer,
           sizeof(int) * self->frameinfo.samples * self->frameinfo.channels);
#else
    float_to_int_converter(BITS_PER_SAMPLE)(self->frameinfo.samples *
                                            self->streaminfo.channels,
                                            self->frameinfo.buffer,
                                            frame->samples);
#endif

    return (PyObject*)frame;
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
