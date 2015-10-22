#include <Python.h>
#include "../libmpcdec/mpcdec.h"

typedef struct {
    PyObject_HEAD

    mpc_reader reader;
    mpc_demux *demux;

    int channels;
    int sample_rate;
    int closed;

    PyObject *audiotools_pcm;
} decoders_MPCDecoder;

static PyObject*
MPCDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds);

int
MPCDecoder_init(decoders_MPCDecoder *self,
                PyObject *args, PyObject *kwds);

void
MPCDecoder_dealloc(decoders_MPCDecoder *self);

static PyObject*
MPCDecoder_sample_rate(decoders_MPCDecoder *self, void *closure);

static PyObject*
MPCDecoder_bits_per_sample(decoders_MPCDecoder *self, void *closure);

static PyObject*
MPCDecoder_channels(decoders_MPCDecoder *self, void *closure);

static PyObject*
MPCDecoder_channel_mask(decoders_MPCDecoder *self, void *closure);

static PyObject*
MPCDecoder_read(decoders_MPCDecoder* self, PyObject *args);

static PyObject*
MPCDecoder_close(decoders_MPCDecoder* self, PyObject *args);

static PyObject*
MPCDecoder_enter(decoders_MPCDecoder* self, PyObject *args);

static PyObject*
MPCDecoder_exit(decoders_MPCDecoder* self, PyObject *args);

PyGetSetDef MPCDecoder_getseters[] = {
    {"sample_rate",
     (getter)MPCDecoder_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)MPCDecoder_bits_per_sample, NULL, "bits-per-sample", NULL},
    {"channels",
     (getter)MPCDecoder_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)MPCDecoder_channel_mask, NULL, "channel mask", NULL},
    {NULL}
};

PyMethodDef MPCDecoder_methods[] = {
    {"read", (PyCFunction)MPCDecoder_read,
     METH_VARARGS, "read(pcm_frame_count) -> FrameList"},
    {"close", (PyCFunction)MPCDecoder_close,
     METH_NOARGS, "close() -> None"},
    {"__enter__", (PyCFunction)MPCDecoder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)MPCDecoder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject decoders_MPCDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.MPCDecoder",     /* tp_name */
    sizeof(decoders_MPCDecoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)MPCDecoder_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_compare */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,       /* tp_flags */
    "MPCDecoder objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    MPCDecoder_methods,        /* tp_methods */
    0,                         /* tp_members */
    MPCDecoder_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)MPCDecoder_init, /* tp_init */
    0,                         /* tp_alloc */
    MPCDecoder_new,            /* tp_new */
};

