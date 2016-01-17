#ifndef STANDALONE
#include <Python.h>
#include "mod_defs.h"
#endif
#include <stdlib.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

#include "pcm.h"

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

#ifndef STANDALONE

#if PY_MAJOR_VERSION >= 3
#ifndef PyInt_AsLong
#define PyInt_AsLong PyLong_AsLong
#endif
#endif

PyMethodDef module_methods[] = {
    {"empty_framelist", (PyCFunction)FrameList_empty,
     METH_VARARGS, "empty_framelist(channels, bits_per_sample) -> FrameList"},
    {"from_list", (PyCFunction)FrameList_from_list,
     METH_VARARGS,
     "from_list(int_list, channels, bits_per_sample, is_signed) -> FrameList"},
    {"from_frames", (PyCFunction)FrameList_from_frames,
     METH_VARARGS,
     "from_frames(framelist_list) -> FrameList"},
    {"from_channels", (PyCFunction)FrameList_from_channels,
     METH_VARARGS,
     "from_channels(framelist_list) -> FrameList"},
    {"empty_float_framelist", (PyCFunction)FloatFrameList_empty,
     METH_VARARGS, "empty_float_framelist(channels) -> FloatFrameList"},
    {"from_float_frames", (PyCFunction)FloatFrameList_from_frames,
     METH_VARARGS,
     "from_float_frames(floatframelist_list) -> FloatFrameList"},
    {"from_float_channels", (PyCFunction)FloatFrameList_from_channels,
     METH_VARARGS,
     "from_float_channels(floatframelist_list) -> FloatFrameList"},
    {NULL}
};

/******************
  FrameList Object
*******************/

PyGetSetDef FrameList_getseters[] = {
    {"frames", (getter)FrameList_frames,
     0, "frame count", NULL},
    {"channels", (getter)FrameList_channels,
     0, "channel count", NULL},
    {"bits_per_sample", (getter)FrameList_bits_per_sample,
     0, "bits per sample", NULL},
    {NULL}  /* Sentinel */
};

PyMethodDef FrameList_methods[] = {
    {"frame", (PyCFunction)FrameList_frame,
     METH_VARARGS,
     "F.frame(i) -> FrameList -- return the given PCM frame"},
    {"channel", (PyCFunction)FrameList_channel,
     METH_VARARGS,
     "F.channel(i) -> FrameList -- return the given channel"},
    {"to_bytes", (PyCFunction)FrameList_to_bytes,
     METH_VARARGS,
     "F.to_bytes(is_big_endian, is_signed) -> string"},
    {"split", (PyCFunction)FrameList_split,
     METH_VARARGS,
     "F.split(i) -> (FrameList,FrameList) -- "
     "splits the FrameList at the given index"},
    {"to_float", (PyCFunction)FrameList_to_float,
     METH_NOARGS,
     "F.to_float() -> FloatFrameList"},
    {"from_list", (PyCFunction)FrameList_from_list,
     METH_VARARGS | METH_CLASS,
     "FrameList.from_list(int_list, channels, bits_per_sample, is_signed) -> FrameList"
    },
    {"from_frames", (PyCFunction)FrameList_from_frames,
     METH_VARARGS | METH_CLASS,
     "FrameList.from_frames(framelist_list) -> FrameList"},
    {"from_channels", (PyCFunction)FrameList_from_channels,
     METH_VARARGS | METH_CLASS,
     "FrameList.from_channels(framelist_list) -> FrameList"},
    {"frame_count", (PyCFunction)FrameList_frame_count,
     METH_VARARGS,
     "F.frame_count(bytes) -> int -- "
     "given a number of bytes, returns the maximum number of frames "
     "that would fit or a minimum of 1"},
    {NULL}
};

static PySequenceMethods pcm_FrameListType_as_sequence = {
    (lenfunc)FrameList_len,          /* sq_length */
    (binaryfunc)FrameList_concat,    /* sq_concat */
    (ssizeargfunc)FrameList_repeat,  /* sq_repeat */
    (ssizeargfunc)FrameList_GetItem, /* sq_item */
    (ssizessizeargfunc)NULL,         /* sq_slice */
    (ssizeobjargproc)NULL,           /* sq_ass_item */
    (ssizessizeobjargproc)NULL,      /* sq_ass_slice */
    (objobjproc)NULL,                /* sq_contains */
    (binaryfunc)NULL,                /* sq_inplace_concat */
    (ssizeargfunc)NULL,              /* sq_inplace_repeat */
};

PyTypeObject pcm_FrameListType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pcm.FrameList",           /*tp_name*/
    sizeof(pcm_FrameList),     /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FrameList_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    &pcm_FrameListType_as_sequence, /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "FrameList(string, channels, bits_per_sample, is_big_endian, is_signed)",
    /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    (richcmpfunc)FrameList_richcompare, /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    FrameList_methods,         /* tp_methods */
    0,                         /* tp_members */
    FrameList_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FrameList_init,  /* tp_init */
    0,                         /* tp_alloc */
    FrameList_new,             /* tp_new */
};


void
FrameList_dealloc(pcm_FrameList* self)
{
    free(self->samples);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject*
FrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcm_FrameList *self;

    self = (pcm_FrameList *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
FrameList_init(pcm_FrameList *self, PyObject *args, PyObject *kwds)
{
    unsigned char *data;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t data_size;
#else
    int data_size;
#endif
    int is_big_endian;
    int is_signed;

    if (!PyArg_ParseTuple(args, "s#IIii",
                          &data, &data_size,
                          &(self->channels),
                          &(self->bits_per_sample),
                          &(is_big_endian),
                          &is_signed))
        return -1;

    if (self->channels < 1) {
        PyErr_SetString(PyExc_ValueError,
                        "number of channels must be > 0");
        return -1;
    } else if ((self->bits_per_sample != 16) &&
               (self->bits_per_sample != 24) &&
               (self->bits_per_sample != 8)) {
        PyErr_SetString(PyExc_ValueError,
                        "bits_per_sample must be 8, 16 or 24");
        return -1;
    } else if (data_size % (self->channels * self->bits_per_sample / 8)) {
        PyErr_SetString(PyExc_ValueError,
                        "number of samples must be divisible by "
                        "bits-per-sample and number of channels");
        return -1;
    } else {
        const unsigned samples_length =
            data_size / (self->bits_per_sample / 8);
        self->frames = samples_length / self->channels;
        self->samples = malloc(sizeof(int) * samples_length);
        pcm_to_int_f converter = pcm_to_int_converter(self->bits_per_sample,
                                                      is_big_endian,
                                                      is_signed);
        if (converter) {
            converter(samples_length, data, self->samples);
        } else {
            PyErr_SetString(PyExc_ValueError,
                            "unsupported number of bits per sample");
            return -1;
        }
    }

    return 0;
}

pcm_FrameList*
FrameList_create(void)
{
    return (pcm_FrameList*)_PyObject_New(&pcm_FrameListType);
}

PyObject*
FrameList_empty(PyObject *dummy, PyObject *args)
{
    int channels;
    int bits_per_sample;
    pcm_FrameList *framelist;

    if (!PyArg_ParseTuple(args, "ii", &channels, &bits_per_sample)) {
        return NULL;
    }

    if (channels <= 0) {
        PyErr_SetString(PyExc_ValueError, "channels must be > 0");
        return NULL;
    }

    if ((bits_per_sample != 8) &&
        (bits_per_sample != 16) &&
        (bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError,
                        "bits_per_sample must be 8, 16 or 24");
        return NULL;
    }

    framelist = FrameList_create();
    framelist->frames = 0;
    framelist->channels = (unsigned)channels;
    framelist->bits_per_sample = (unsigned)bits_per_sample;
    framelist->samples = NULL;

    return (PyObject*)framelist;
}

int
FrameList_CheckExact(PyObject *o)
{
    return Py_TYPE(o) == &pcm_FrameListType;
}

PyObject*
FrameList_frames(pcm_FrameList *self, void* closure)
{
    return Py_BuildValue("i", self->frames);
}

PyObject*
FrameList_channels(pcm_FrameList *self, void* closure)
{
    return Py_BuildValue("i", self->channels);
}

PyObject*
FrameList_bits_per_sample(pcm_FrameList *self, void* closure)
{
    return Py_BuildValue("i", self->bits_per_sample);
}

Py_ssize_t
FrameList_len(pcm_FrameList *o)
{
    return FrameList_samples_length(o);
}

PyObject
*FrameList_richcompare(PyObject *a, PyObject *b, int op)
{
    switch (op) {
    case Py_EQ:
        if (FrameList_CheckExact(a) && FrameList_CheckExact(b) &&
            FrameList_equals((pcm_FrameList*)a, (pcm_FrameList*)b)) {
            Py_INCREF(Py_True);
            return Py_True;
        } else {
            Py_INCREF(Py_False);
            return Py_False;
        }
    case Py_NE:
        if (FrameList_CheckExact(a) && FrameList_CheckExact(b) &&
            FrameList_equals((pcm_FrameList*)a, (pcm_FrameList*)b)) {
            Py_INCREF(Py_False);
            return Py_False;
        } else {
            Py_INCREF(Py_True);
            return Py_True;
        }
    default:
        PyErr_SetString(PyExc_TypeError, "unsupported comparison");
        return NULL;
    }
}

int
FrameList_equals(pcm_FrameList *a, pcm_FrameList *b)
{
    return ((a->frames == b->frames) &&
            (a->channels == b->channels) &&
            (a->bits_per_sample == b->bits_per_sample) &&
            (memcmp(a->samples,
                    b->samples,
                    sizeof(int) * FrameList_samples_length(a)) == 0));
}

PyObject*
FrameList_GetItem(pcm_FrameList *o, Py_ssize_t i)
{
    if ((i >= 0) && (i < FrameList_samples_length(o))) {
        return Py_BuildValue("i", o->samples[i]);
    } else {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    }
}

PyObject*
FrameList_frame(pcm_FrameList *self, PyObject *args)
{
    int frame_number;
    pcm_FrameList *frame;

    if (!PyArg_ParseTuple(args, "i", &frame_number))
        return NULL;
    if ((frame_number < 0) || ((unsigned)frame_number >= self->frames)) {
        PyErr_SetString(PyExc_IndexError, "frame number out of range");
        return NULL;
    }

    frame = FrameList_create();
    frame->frames = 1;
    frame->channels = self->channels;
    frame->bits_per_sample = self->bits_per_sample;
    frame->samples = malloc(sizeof(int) * self->channels);
    memcpy(frame->samples,
           self->samples + (frame_number * self->channels),
           sizeof(int) * self->channels);
    return (PyObject*)frame;
}

PyObject*
FrameList_channel(pcm_FrameList *self, PyObject *args)
{
    int channel_number;
    pcm_FrameList *channel;
    unsigned i;

    if (!PyArg_ParseTuple(args, "i", &channel_number))
        return NULL;
    if ((channel_number < 0) || ((unsigned)channel_number >= self->channels)) {
        PyErr_SetString(PyExc_IndexError, "channel number out of range");
        return NULL;
    }

    channel = FrameList_create();
    channel->frames = self->frames;
    channel->channels = 1;
    channel->bits_per_sample = self->bits_per_sample;
    channel->samples = malloc(sizeof(int) * self->frames);

    for (i = 0; i < self->frames; i++) {
        channel->samples[i] = \
            self->samples[channel_number + (i * self->channels)];
    }

    return (PyObject*)channel;
}

PyObject*
FrameList_to_bytes(pcm_FrameList *self, PyObject *args)
{
    int is_big_endian;
    int is_signed;
    PyObject *bytes_obj;
    const unsigned samples_length = FrameList_samples_length(self);
    const Py_ssize_t bytes_size =
        ((self->bits_per_sample / 8) * samples_length);

    if (!PyArg_ParseTuple(args, "ii", &is_big_endian, &is_signed)) {
        return NULL;
    } else if ((bytes_obj =
                PyBytes_FromStringAndSize(NULL, bytes_size)) == NULL) {
        return NULL;
    } else {
        int_to_pcm_converter(
            self->bits_per_sample,
            is_big_endian,
            is_signed)(samples_length,
                       self->samples,
                       (unsigned char *)PyBytes_AsString(bytes_obj));
    }

    return bytes_obj;
}

PyObject*
FrameList_split(pcm_FrameList *self, PyObject *args)
{
    pcm_FrameList *head;
    pcm_FrameList *tail;
    PyObject* tuple;
    int split_point;

    if (!PyArg_ParseTuple(args, "i", &split_point)) {
        return NULL;
    }

    if (split_point < 0) {
        PyErr_SetString(PyExc_IndexError, "split point must be >= 0");
        return NULL;
    } else if ((unsigned)split_point >= self->frames) {
        head = self;
        Py_INCREF(head);
        tail = FrameList_create();
        tail->frames = 0;
        tail->channels = self->channels;
        tail->bits_per_sample = self->bits_per_sample;
        tail->samples = NULL;
    } else if (split_point == 0) {
        head = FrameList_create();
        head->frames = 0;
        head->channels = self->channels;
        head->bits_per_sample = self->bits_per_sample;
        head->samples = NULL;
        tail = self;
        Py_INCREF(tail);
    } else {
        const unsigned head_samples_length =
            split_point * self->channels;
        const unsigned tail_samples_length =
            (self->frames - split_point) * self->channels;
        head = FrameList_create();
        head->frames = split_point;
        head->samples = malloc(head_samples_length * sizeof(int));
        memcpy(head->samples,
               self->samples,
               head_samples_length * sizeof(int));

        tail = FrameList_create();
        tail->frames = (self->frames - split_point);
        tail->samples = malloc(tail_samples_length * sizeof(int));
        memcpy(tail->samples,
               self->samples + head_samples_length,
               tail_samples_length * sizeof(int));

        head->channels = tail->channels = self->channels;
        head->bits_per_sample = tail->bits_per_sample = self->bits_per_sample;
    }

    tuple = Py_BuildValue("(O,O)", head, tail);
    Py_DECREF(head);
    Py_DECREF(tail);
    return tuple;
}

PyObject*
FrameList_concat(pcm_FrameList *a, PyObject *bb)
{
    pcm_FrameList *concat;
    pcm_FrameList *b;

    if (FrameList_CheckExact(bb)) {
        b = (pcm_FrameList*)bb;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "can only concatenate FrameList with other FrameLists"
                        );
        return NULL;
    }

    if (a->channels != b->channels) {
        PyErr_SetString(PyExc_ValueError,
                        "both FrameLists must have the same number of channels"
                        );
        return NULL;
    }
    if (a->bits_per_sample != b->bits_per_sample) {
        PyErr_SetString(PyExc_ValueError,
                        "both FrameLists must have the same number "
                        "of bits per sample");
        return NULL;
    }

    concat = FrameList_create();
    concat->frames = a->frames + b->frames;
    concat->channels = a->channels;
    concat->bits_per_sample = a->bits_per_sample;
    concat->samples = malloc(FrameList_samples_length(concat) * sizeof(int));
    memcpy(concat->samples,
           a->samples,
           FrameList_samples_length(a) * sizeof(int));
    memcpy(concat->samples + FrameList_samples_length(a),
           b->samples,
           FrameList_samples_length(b) * sizeof(int));

    return (PyObject*)concat;
}

PyObject*
FrameList_repeat(pcm_FrameList *a, Py_ssize_t i)
{
    pcm_FrameList *repeat = FrameList_create();
    Py_ssize_t j;
    const unsigned a_samples_length = FrameList_samples_length(a);

    repeat->frames = (unsigned int)(a->frames * i);
    repeat->channels = a->channels;
    repeat->bits_per_sample = a->bits_per_sample;
    repeat->samples = malloc(sizeof(int) * FrameList_samples_length(repeat));

    for (j = 0; j < i; j++) {
        memcpy(repeat->samples + (j * a_samples_length),
               a->samples,
               a_samples_length * sizeof(int));
    }

    return (PyObject*)repeat;
}


PyObject*
FrameList_to_float(pcm_FrameList *self, PyObject *args)
{
    pcm_FloatFrameList *framelist = FloatFrameList_create();
    framelist->frames = self->frames;
    framelist->channels = self->channels;
    framelist->samples = malloc(sizeof(double) *
                                FloatFrameList_samples_length(framelist));

    int_to_double_converter(self->bits_per_sample)(
        FloatFrameList_samples_length(framelist),
        self->samples,
        framelist->samples);

    return (PyObject*)framelist;
}

PyObject*
FrameList_frame_count(pcm_FrameList *self, PyObject *args)
{
    int byte_count;
    int bytes_per_frame = self->channels * (self->bits_per_sample / 8);

    if (!PyArg_ParseTuple(args, "i", &byte_count))
        return NULL;
    else {
        byte_count -= (byte_count % bytes_per_frame);
        return Py_BuildValue("i",
                             byte_count ? byte_count / bytes_per_frame : 1);
    }
}

#endif


#ifndef STANDALONE
PyObject*
FrameList_from_list(PyObject *dummy, PyObject *args)
{
    pcm_FrameList *framelist;
    PyObject *list;
    Py_ssize_t list_len, i;
    long integer_val;
    int adjustment;
    int channels;
    int bits_per_sample;
    int is_signed;

    if (!PyArg_ParseTuple(args, "Oiii",
                          &list,
                          &channels,
                          &bits_per_sample,
                          &is_signed)) {
        return NULL;
    }

    if ((list_len = PySequence_Size(list)) == -1) {
        return NULL;
    }

    if (channels < 1) {
        PyErr_SetString(PyExc_ValueError, "channels must be > 0");
        return NULL;
    }

    if ((bits_per_sample != 8) &&
        (bits_per_sample != 16) &&
        (bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError,
                        "unsupported number of bits per sample");
        return NULL;
    }

    if (list_len % channels) {
        PyErr_SetString(PyExc_ValueError,
                        "number of samples must be divisible by "
                        "number of channels");
        return NULL;
    }

    if (is_signed) {
        adjustment = 0;
    } else {
        adjustment = (1 << (bits_per_sample - 1));
    }

    framelist = FrameList_create();
    framelist->channels = channels;
    framelist->bits_per_sample = bits_per_sample;
    framelist->samples = malloc(sizeof(int) * list_len);
    framelist->frames = (unsigned int)list_len / framelist->channels;
    for (i = 0; i < list_len; i++) {
        PyObject *integer_obj;
        if ((integer_obj = PySequence_GetItem(list, i)) == NULL) {
            Py_DECREF((PyObject*)framelist);
            return NULL;
        }
        integer_val = PyInt_AsLong(integer_obj);
        Py_DECREF(integer_obj);
        if ((integer_val == -1) && PyErr_Occurred()) {
            Py_DECREF((PyObject*)framelist);
            return NULL;
        }
        framelist->samples[i] = (int)(integer_val - adjustment);
    }

    return (PyObject*)framelist;
}

PyObject*
FrameList_from_frames(PyObject *dummy, PyObject *args)
{
    PyObject *list;
    Py_ssize_t list_len, i;
    pcm_FrameList *output_frame;
    PyObject *initial_frame_obj;
    pcm_FrameList *initial_frame;

    if (!PyArg_ParseTuple(args, "O", &list)) {
        return NULL;
    }

    if ((list_len = PySequence_Size(list)) == -1) {
        return NULL;
    }

    /*get first FrameList as a base
      for its channels/bits_per_sample values*/
    if ((initial_frame_obj = PySequence_GetItem(list, 0)) == NULL) {
        return NULL;
    }

    if (FrameList_CheckExact(initial_frame_obj)) {
        initial_frame = (pcm_FrameList*)initial_frame_obj;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "frames must be of type FrameList");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    if (initial_frame->frames != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all subframes must be 1 frame long");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    /*create output FrameList from initial values*/
    output_frame = FrameList_create();
    output_frame->frames = (unsigned int)list_len;
    output_frame->channels = initial_frame->channels;
    output_frame->bits_per_sample = initial_frame->bits_per_sample;
    output_frame->samples =
        malloc(sizeof(int) * FrameList_samples_length(output_frame));

    memcpy(output_frame->samples,
           initial_frame->samples,
           sizeof(int) * FrameList_samples_length(initial_frame));

    /*we're done with initial frame*/
    Py_DECREF((PyObject*)initial_frame);

    /*process remaining FrameLists in list*/
    for (i = 1; i < list_len; i++) {
        PyObject *list_frame_obj;
        pcm_FrameList *list_frame;

        if ((list_frame_obj = PySequence_GetItem(list, i)) == NULL) {
            Py_DECREF((PyObject*)output_frame);
            return NULL;
        }

        if (FrameList_CheckExact(list_frame_obj)) {
            list_frame = (pcm_FrameList*)list_frame_obj;
        } else {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_TypeError,
                            "frames must be of type FrameList");
            return NULL;
        }

        if (list_frame->frames != 1) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must be 1 frame long");
            return NULL;
        }

        if (output_frame->channels != list_frame->channels) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must have the same "
                            "number of channels");
            return NULL;
        }

        if (output_frame->bits_per_sample != list_frame->bits_per_sample) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must have the same "
                            "number of bits per sample");
            return NULL;
        }

        memcpy(output_frame->samples + (i * output_frame->channels),
               list_frame->samples,
               sizeof(int) * FrameList_samples_length(list_frame));

        Py_DECREF(list_frame_obj);
    }

    return (PyObject*)output_frame;
}

PyObject*
FrameList_from_channels(PyObject *dummy, PyObject *args)
{
    PyObject *list;
    Py_ssize_t list_len, i;
    pcm_FrameList *output_frame;
    PyObject *initial_frame_obj;
    pcm_FrameList *initial_frame;
    unsigned j;

    if (!PyArg_ParseTuple(args, "O", &list)) {
        return NULL;
    }

    if ((list_len = PySequence_Size(list)) == -1) {
        return NULL;
    }

    /*get first FrameList as a base
      for its frames/bits_per_sample values*/
    if ((initial_frame_obj = PySequence_GetItem(list, 0)) == NULL) {
        return NULL;
    }

    if (FrameList_CheckExact(initial_frame_obj)) {
        initial_frame = (pcm_FrameList*)initial_frame_obj;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "channels must be of type FrameList");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    if (initial_frame->channels != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all channels must be 1 channel wide");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    /*create output FrameList from initial values*/
    output_frame = FrameList_create();
    output_frame->frames = initial_frame->frames;
    output_frame->channels = (unsigned int)list_len;
    output_frame->bits_per_sample = initial_frame->bits_per_sample;
    output_frame->samples =
        malloc(sizeof(int) * FrameList_samples_length(output_frame));

    for (j = 0; j < FrameList_samples_length(initial_frame); j++) {
        output_frame->samples[j * list_len] = initial_frame->samples[j];
    }

    /*we're done with initial frame*/
    Py_DECREF(initial_frame_obj);

    /*process remaining FrameLists in list*/
    for (i = 1; i < list_len; i++) {
        PyObject *list_frame_obj;
        pcm_FrameList *list_frame;

        if ((list_frame_obj = PySequence_GetItem(list, i)) == NULL) {
            Py_DECREF((PyObject*)output_frame);
            return NULL;
        }

        if (FrameList_CheckExact(list_frame_obj)) {
            list_frame = (pcm_FrameList*)list_frame_obj;
        } else {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_TypeError,
                            "channels must be of type FrameList");
            return NULL;
        }

        if (list_frame->channels != 1) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all channels must be 1 channel wide");
            return NULL;
        }

        if (output_frame->frames != list_frame->frames) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all channels must have the same "
                            "number of frames");
            return NULL;
        }
        if (output_frame->bits_per_sample != list_frame->bits_per_sample) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all channels must have the same "
                            "number of bits per sample");
            return NULL;
        }


        for (j = 0; j < FrameList_samples_length(list_frame); j++) {
            output_frame->samples[(j * list_len) + i] = list_frame->samples[j];
        }

        Py_DECREF(list_frame_obj);
    }

    return (PyObject*)output_frame;
}

int
FrameList_converter(PyObject* obj, void** framelist)
{
    if (PyObject_TypeCheck(obj, &pcm_FrameListType)) {
        *framelist = obj;
        return 1;
    } else {
        PyErr_SetString(PyExc_TypeError, "not a FrameList object");
        return 0;
    }
}

/***********************
  FloatFrameList Object
************************/

PyGetSetDef FloatFrameList_getseters[] = {
    {"frames", (getter)FloatFrameList_frames, 0, "frame count", NULL},
    {"channels", (getter)FloatFrameList_channels, 0, "channel count", NULL},
    {NULL}  /* Sentinel */
};

PyMethodDef FloatFrameList_methods[] = {
    {"frame", (PyCFunction)FloatFrameList_frame,
     METH_VARARGS,
     "FF.frame(i) -> FloatFrameList -- return the given PCM frame"},
    {"channel", (PyCFunction)FloatFrameList_channel,
     METH_VARARGS,
     "FF.channel(i) -> FloatFrameList -- return the given channel"},
    {"split", (PyCFunction)FloatFrameList_split,
     METH_VARARGS,
     "FF.split(i) -> (FloatFrameList,FloatFrameList) -- "
     "splits the FloatFrameList at the given index"},
    {"from_frames", (PyCFunction)FloatFrameList_from_frames,
     METH_VARARGS | METH_CLASS,
     "FloatFrameList.from_frames(floatframelist_list) -> FloatFrameList"},
    {"from_channels", (PyCFunction)FloatFrameList_from_channels,
     METH_VARARGS | METH_CLASS,
     "FloatFrameList.from_channels(floatframelist_list) -> FloatFrameList"},
    {"to_int", (PyCFunction)FloatFrameList_to_int,
     METH_VARARGS,
     "FF.to_int(bits_per_sample) -> FrameList"},
    {NULL}
};

static PySequenceMethods pcm_FloatFrameListType_as_sequence = {
    (lenfunc)FloatFrameList_len,          /* sq_length */
    (binaryfunc)FloatFrameList_concat,    /* sq_concat */
    (ssizeargfunc)FloatFrameList_repeat,  /* sq_repeat */
    (ssizeargfunc)FloatFrameList_GetItem, /* sq_item */
    (ssizessizeargfunc)NULL,              /* sq_slice */
    (ssizeobjargproc)NULL,                /* sq_ass_item */
    (ssizessizeobjargproc)NULL,           /* sq_ass_slice */
    (objobjproc)NULL,                     /* sq_contains */
    (binaryfunc)NULL,                     /* sq_inplace_concat */
    (ssizeargfunc)NULL,                   /* sq_inplace_repeat */
};

PyTypeObject pcm_FloatFrameListType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pcm.FloatFrameList",      /*tp_name*/
    sizeof(pcm_FloatFrameList), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FloatFrameList_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    &pcm_FloatFrameListType_as_sequence, /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "FloatFrameList(float_list, channels)",  /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    (richcmpfunc)FloatFrameList_richcompare, /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    FloatFrameList_methods,    /* tp_methods */
    0,                         /* tp_members */
    FloatFrameList_getseters,  /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FloatFrameList_init,  /* tp_init */
    0,                         /* tp_alloc */
    FloatFrameList_new,        /* tp_new */
};

void
FloatFrameList_dealloc(pcm_FloatFrameList* self)
{
    free(self->samples);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject*
FloatFrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    pcm_FloatFrameList *self;

    self = (pcm_FloatFrameList *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
FloatFrameList_init(pcm_FloatFrameList *self, PyObject *args, PyObject *kwds)
{
    PyObject *data;
    Py_ssize_t data_size;
    Py_ssize_t i;

    if (!PyArg_ParseTuple(args, "OI",
                          &data,
                          &(self->channels)))
        return -1;

    if (self->channels < 1) {
        PyErr_SetString(PyExc_ValueError,
                        "number of channels must be > 0");
        return -1;
    } else if ((data_size = PySequence_Size(data)) == -1) {
        return -1;
    } else if (data_size % (self->channels)) {
        PyErr_SetString(PyExc_ValueError,
                        "number of samples must be divisible by "
                        "number of channels");
        return -1;
    } else {
        self->frames = ((unsigned int)data_size / self->channels);
        self->samples = malloc(sizeof(double) * (unsigned int)data_size);
    }

    for (i = 0; i < data_size; i++) {
        PyObject *data_item;
        if ((data_item = PySequence_GetItem(data, i)) == NULL)
            /*this shouldn't happen unless "data" changes mid-function*/
            return -1;

        if (((self->samples[i] = PyFloat_AsDouble(data_item)) == -1) &&
            PyErr_Occurred()) {
            Py_DECREF(data_item);
            return -1;
        }
        Py_DECREF(data_item);
    }

    return 0;
}

pcm_FloatFrameList*
FloatFrameList_create(void)
{
    return (pcm_FloatFrameList*)_PyObject_New(&pcm_FloatFrameListType);
}

PyObject*
FloatFrameList_empty(PyObject *dummy, PyObject *args)
{
    int channels;
    pcm_FloatFrameList *framelist;

    if (!PyArg_ParseTuple(args, "i", &channels)) {
        return NULL;
    }

    if (channels <= 0) {
        PyErr_SetString(PyExc_ValueError, "channels must be > 0");
        return NULL;
    }

    framelist = FloatFrameList_create();
    framelist->frames = 0;
    framelist->channels = (unsigned)channels;
    framelist->samples = NULL;
    return (PyObject*)framelist;
}

int
FloatFrameList_CheckExact(PyObject *o)
{
    return Py_TYPE(o) == &pcm_FloatFrameListType;
}

PyObject*
FloatFrameList_frames(pcm_FloatFrameList *self, void* closure)
{
    return Py_BuildValue("i", self->frames);
}

PyObject*
FloatFrameList_channels(pcm_FloatFrameList *self, void* closure)
{
    return Py_BuildValue("i", self->channels);
}

Py_ssize_t
FloatFrameList_len(pcm_FloatFrameList *o)
{
    return FloatFrameList_samples_length(o);
}

PyObject
*FloatFrameList_richcompare(PyObject *a, PyObject *b, int op)
{
    switch (op) {
    case Py_EQ:
        if (FloatFrameList_CheckExact(a) &&
            FloatFrameList_CheckExact(b) &&
            FloatFrameList_equals((pcm_FloatFrameList*)a,
                                  (pcm_FloatFrameList*)b)) {
            Py_INCREF(Py_True);
            return Py_True;
        } else {
            Py_INCREF(Py_False);
            return Py_False;
        }
    case Py_NE:
        if (FloatFrameList_CheckExact(a) &&
            FloatFrameList_CheckExact(b) &&
            FloatFrameList_equals((pcm_FloatFrameList*)a,
                                  (pcm_FloatFrameList*)b)) {
            Py_INCREF(Py_False);
            return Py_False;
        } else {
            Py_INCREF(Py_True);
            return Py_True;
        }
    default:
        PyErr_SetString(PyExc_TypeError, "unsupported comparison");
        return NULL;
    }
}

int
FloatFrameList_equals(pcm_FloatFrameList *a, pcm_FloatFrameList *b)
{
    return ((a->frames == b->frames) &&
            (a->channels == b->channels) &&
            (memcmp(a->samples,
                    b->samples,
                    sizeof(double) * FloatFrameList_samples_length(a)) == 0));
}

PyObject*
FloatFrameList_GetItem(pcm_FloatFrameList *o, Py_ssize_t i)
{
    if ((i >= FloatFrameList_samples_length(o)) || (i < 0)) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    } else {
        return Py_BuildValue("d", o->samples[i]);
    }
}

PyObject*
FloatFrameList_frame(pcm_FloatFrameList *self, PyObject *args)
{
    int frame_number;
    pcm_FloatFrameList *frame;

    if (!PyArg_ParseTuple(args, "i", &frame_number))
        return NULL;
    if ((frame_number < 0) || ((unsigned)frame_number >= self->frames)) {
        PyErr_SetString(PyExc_IndexError, "frame number out of range");
        return NULL;
    }

    frame = FloatFrameList_create();
    frame->frames = 1;
    frame->channels = self->channels;
    frame->samples = malloc(sizeof(double) * self->channels);
    memcpy(frame->samples,
           self->samples + (frame_number * self->channels),
           sizeof(double) * self->channels);
    return (PyObject*)frame;
}

PyObject*
FloatFrameList_channel(pcm_FloatFrameList *self, PyObject *args)
{
    int channel_number;
    pcm_FloatFrameList *channel;
    unsigned i, j;
    unsigned samples_length;
    int total_channels;

    if (!PyArg_ParseTuple(args, "i", &channel_number))
        return NULL;
    if ((channel_number < 0) || ((unsigned)channel_number >= self->channels)) {
        PyErr_SetString(PyExc_IndexError, "channel number out of range");
        return NULL;
    }

    channel = FloatFrameList_create();
    channel->frames = self->frames;
    channel->channels = 1;
    channel->samples = malloc(sizeof(double) * self->frames);

    samples_length = FloatFrameList_samples_length(self);
    total_channels = self->channels;
    for (j=0, i = channel_number;
         i < samples_length;
         j++, i += total_channels) {
        channel->samples[j] = self->samples[i];
    }

    return (PyObject*)channel;
}

PyObject*
FloatFrameList_to_int(pcm_FloatFrameList *self, PyObject *args)
{
    pcm_FrameList *framelist;
    int bits_per_sample;
    double_to_int_f converter;

    if (!PyArg_ParseTuple(args, "i", &bits_per_sample))
        return NULL;

    if ((converter = double_to_int_converter(bits_per_sample)) == NULL) {
        PyErr_SetString(PyExc_ValueError, "invalid bits-per-sample");
        return NULL;
    }

    framelist = FrameList_create();
    framelist->frames = self->frames;
    framelist->channels = self->channels;
    framelist->bits_per_sample = bits_per_sample;
    framelist->samples =
        malloc(sizeof(int) * FrameList_samples_length(framelist));

    converter(FloatFrameList_samples_length(self),
              self->samples,
              framelist->samples);

    return (PyObject*)framelist;
}

PyObject*
FloatFrameList_split(pcm_FloatFrameList *self, PyObject *args)
{
    pcm_FloatFrameList *head;
    pcm_FloatFrameList *tail;
    PyObject* tuple;
    int split_point;

    if (!PyArg_ParseTuple(args, "i", &split_point)) {
        return NULL;
    }

    if (split_point < 0) {
        PyErr_SetString(PyExc_IndexError, "split point must be >= 0");
        return NULL;
    } else if ((unsigned)split_point >= self->frames) {
        head = self;
        Py_INCREF(head);
        tail = FloatFrameList_create();
        tail->frames = 0;
        tail->channels = self->channels;
        tail->samples = NULL;
    } else if (split_point == 0) {
        head = FloatFrameList_create();
        head->frames = 0;
        head->channels = self->channels;
        head->samples = NULL;
        tail = self;
        Py_INCREF(tail);
    } else {
        const unsigned head_samples_length =
            split_point * self->channels;
        const unsigned tail_samples_length =
            (self->frames - split_point) * self->channels;
        head = FloatFrameList_create();
        head->frames = split_point;
        head->samples = malloc(head_samples_length * sizeof(double));
        memcpy(head->samples,
               self->samples,
               head_samples_length * sizeof(double));

        tail = FloatFrameList_create();
        tail->frames = (self->frames - split_point);
        tail->samples = malloc(tail_samples_length * sizeof(double));
        memcpy(tail->samples,
               self->samples + head_samples_length,
               tail_samples_length * sizeof(double));

        head->channels = tail->channels = self->channels;
    }

    tuple = Py_BuildValue("(O,O)", head, tail);
    Py_DECREF(head);
    Py_DECREF(tail);
    return tuple;
}

PyObject*
FloatFrameList_concat(pcm_FloatFrameList *a, PyObject *bb)
{
    pcm_FloatFrameList *concat;
    pcm_FloatFrameList *b;

    if (FloatFrameList_CheckExact(bb)) {
        b = (pcm_FloatFrameList*)bb;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "can only concatenate FloatFrameList "
                        "with other FloatFrameLists");
        return NULL;
    }

    if (a->channels != b->channels) {
        PyErr_SetString(PyExc_ValueError,
                        "both FloatFrameLists must have the same "
                        "number of channels");
        return NULL;
    }

    concat = FloatFrameList_create();
    concat->frames = a->frames + b->frames;
    concat->channels = a->channels;
    concat->samples =
        malloc(FloatFrameList_samples_length(concat) * sizeof(double));
    memcpy(concat->samples,
           a->samples,
           FloatFrameList_samples_length(a) * sizeof(double));
    memcpy(concat->samples + FloatFrameList_samples_length(a),
           b->samples,
           FloatFrameList_samples_length(b) * sizeof(double));

    return (PyObject*)concat;
}


PyObject*
FloatFrameList_repeat(pcm_FloatFrameList *a, Py_ssize_t i)
{
    pcm_FloatFrameList *repeat = FloatFrameList_create();
    Py_ssize_t j;
    const unsigned a_samples_length = FloatFrameList_samples_length(a);

    repeat->frames = (unsigned int)(a->frames * i);
    repeat->channels = a->channels;
    repeat->samples =
        malloc(sizeof(double) * FloatFrameList_samples_length(repeat));

    for (j = 0; j < i; j++) {
        memcpy(repeat->samples + (j * a_samples_length),
               a->samples,
               a_samples_length * sizeof(double));
    }

    return (PyObject*)repeat;
}


PyObject*
FloatFrameList_from_frames(PyObject *dummy, PyObject *args)
{
    PyObject *list;
    Py_ssize_t list_len, i;
    pcm_FloatFrameList *output_frame;
    PyObject *initial_frame_obj;
    pcm_FloatFrameList *initial_frame;

    if (!PyArg_ParseTuple(args, "O", &list)) {
        return NULL;
    }


    if ((list_len = PySequence_Size(list)) == -1) {
        return NULL;
    }

    /*get first FrameList as a base for its channels value*/
    if ((initial_frame_obj = PySequence_GetItem(list, 0)) == NULL) {
        return NULL;
    }

    if (FloatFrameList_CheckExact(initial_frame_obj)) {
        initial_frame = (pcm_FloatFrameList*)initial_frame_obj;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "frames must be of type FloatFrameList");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    if (initial_frame->frames != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all subframes must be 1 frame long");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    output_frame = FloatFrameList_create();
    output_frame->frames = (unsigned int)list_len;
    output_frame->channels = initial_frame->channels;
    output_frame->samples =
        malloc(sizeof(double) * FloatFrameList_samples_length(output_frame));

    memcpy(output_frame->samples,
           initial_frame->samples,
           sizeof(double) * FloatFrameList_samples_length(initial_frame));

    /*we're done with initial frame*/
    Py_DECREF((PyObject*)initial_frame);

    /*process remaining FloatFrameLists in list*/
    for (i = 1; i < list_len; i++) {
        PyObject *list_frame_obj;
        pcm_FloatFrameList *list_frame;

        if ((list_frame_obj = PySequence_GetItem(list, i)) == NULL) {
            Py_DECREF((PyObject*)output_frame);
            return NULL;
        }

        if (FloatFrameList_CheckExact(list_frame_obj)) {
            list_frame = (pcm_FloatFrameList*)list_frame_obj;
        } else {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_TypeError,
                            "frames must be of type FloatFrameList");
            return NULL;
        }

        if (list_frame->frames != 1) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must be 1 frame long");
            return NULL;
        }
        if (output_frame->channels != list_frame->channels) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must have the same "
                            "number of channels");
            return NULL;
        }

        memcpy(output_frame->samples + (i * output_frame->channels),
               list_frame->samples,
               sizeof(double) * FloatFrameList_samples_length(list_frame));

        Py_DECREF(list_frame_obj);
    }

    return (PyObject*)output_frame;
}

PyObject*
FloatFrameList_from_channels(PyObject *dummy, PyObject *args)
{
    PyObject *list;
    Py_ssize_t list_len, i;
    pcm_FloatFrameList *output_frame;
    PyObject *initial_frame_obj;
    pcm_FloatFrameList *initial_frame;
    unsigned j;

    if (!PyArg_ParseTuple(args, "O", &list)) {
        return NULL;
    }

    if ((list_len = PySequence_Size(list)) == -1) {
        return NULL;
    }

    /*get first FloatFrameList as a base for its frames values*/
    if ((initial_frame_obj = PySequence_GetItem(list, 0)) == NULL) {
        return NULL;
    }

    if (FloatFrameList_CheckExact(initial_frame_obj)) {
        initial_frame = (pcm_FloatFrameList*)initial_frame_obj;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "channels must be of type FloatFrameList");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    if (initial_frame->channels != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all channels must be 1 channel wide");
        Py_DECREF(initial_frame_obj);
        return NULL;
    }

    /*create output FloatFrameList from initial values*/
    output_frame = FloatFrameList_create();
    output_frame->frames = initial_frame->frames;
    output_frame->channels = (unsigned int)list_len;
    output_frame->samples =
        malloc(sizeof(double) * FloatFrameList_samples_length(output_frame));

    for (j = 0; j < FloatFrameList_samples_length(initial_frame); j++) {
        output_frame->samples[j * list_len] = initial_frame->samples[j];
    }

    /*we're done with initial frame*/
    Py_DECREF(initial_frame_obj);

    /*process remaining FloatFrameLists in list*/
    for (i = 1; i < list_len; i++) {
        PyObject *list_frame_obj;
        pcm_FloatFrameList *list_frame;

        if ((list_frame_obj = PySequence_GetItem(list, i)) == NULL) {
            Py_DECREF((PyObject*)output_frame);
            return NULL;
        }

        if (FloatFrameList_CheckExact(list_frame_obj)) {
            list_frame = (pcm_FloatFrameList*)list_frame_obj;
        } else {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_TypeError,
                            "channels must be of type FloatFrameList");
            return NULL;
        }

        if (list_frame->channels != 1) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all channels must be 1 channel wide");
            return NULL;
        }

        if (output_frame->frames != list_frame->frames) {
            Py_DECREF((PyObject*)output_frame);
            Py_DECREF(list_frame_obj);
            PyErr_SetString(PyExc_ValueError,
                            "all channels must have the same "
                            "number of frames");
            return NULL;
        }

        for (j = 0; j < FloatFrameList_samples_length(list_frame); j++) {
            output_frame->samples[(j * list_len) + i] = list_frame->samples[j];
        }

        Py_DECREF(list_frame_obj);
    }

    return (PyObject*)output_frame;
}

int
FloatFrameList_converter(PyObject* obj, void** floatframelist)
{
    if (PyObject_TypeCheck(obj, &pcm_FloatFrameListType)) {
        *floatframelist = obj;
        return 1;
    } else {
        PyErr_SetString(PyExc_TypeError, "not a FloatFrameList object");
        return 0;
    }
}

MOD_INIT(pcm)
{
    PyObject* m;

    MOD_DEF(m, "pcm", "a PCM FrameList handling module", module_methods)

    if (!m)
        return MOD_ERROR_VAL;

    pcm_FrameListType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcm_FrameListType) < 0)
        return MOD_ERROR_VAL;

    pcm_FloatFrameListType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcm_FloatFrameListType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&pcm_FrameListType);
    PyModule_AddObject(m, "FrameList",
                       (PyObject *)&pcm_FrameListType);
    Py_INCREF(&pcm_FloatFrameListType);
    PyModule_AddObject(m, "FloatFrameList",
                       (PyObject *)&pcm_FloatFrameListType);

    return MOD_SUCCESS_VAL(m);
}

#endif
