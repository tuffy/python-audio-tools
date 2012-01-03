#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdlib.h>

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

#include "pcm.h"

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

#ifndef STANDALONE

PyMethodDef module_methods[] = {
    {"from_list", (PyCFunction)FrameList_from_list,
     METH_VARARGS,
     "from_list(int_list, channels, bits_per_sample, is_signed) -> FrameList"},
    {"from_frames", (PyCFunction)FrameList_from_frames,
     METH_VARARGS,
     "from_frames(framelist_list) -> FrameList"},
    {"from_channels", (PyCFunction)FrameList_from_channels,
     METH_VARARGS,
     "from_channels(framelist_list) -> FrameList"},
    {"from_float_frames", (PyCFunction)FloatFrameList_from_frames,
     METH_VARARGS,
     "from_float_frames(floatframelist_list) -> FloatFrameList"},
    {"from_float_channels", (PyCFunction)FloatFrameList_from_channels,
     METH_VARARGS,
     "from_float_channels(floatframelist_list) -> FloatFrameList"},
    {"__blank__", (PyCFunction)FrameList_blank,
     METH_NOARGS, "__blank__() -> FrameList"},
    {"__blank_float__", (PyCFunction)FloatFrameList_blank,
     METH_NOARGS, "__blank_float()__ -> FloatFrameList"},
    {NULL}
};

/******************
  FrameList Object
*******************/

PyGetSetDef FrameList_getseters[] = {
    {"frames", (getter)FrameList_frames, 0, "frame count", NULL},
    {"channels", (getter)FrameList_channels, 0, "channel count", NULL},
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
    (ssizeargfunc)NULL,              /* sq_repeat */
    (ssizeargfunc)FrameList_GetItem, /* sq_item */
    (ssizessizeargfunc)NULL,         /* sq_slice */
    (ssizeobjargproc)NULL,           /* sq_ass_item */
    (ssizessizeobjargproc)NULL,      /* sq_ass_slice */
    (objobjproc)NULL,                /* sq_contains */
    (binaryfunc)NULL,               /* sq_inplace_concat */
    (ssizeargfunc)NULL,             /* sq_inplace_repeat */
};

PyTypeObject pcm_FrameListType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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
    self->ob_type->tp_free((PyObject*)self);
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
    FrameList_char_to_int_converter converter;

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
        self->samples_length = data_size / (self->bits_per_sample / 8);
        self->frames = self->samples_length / self->channels;
        self->samples = malloc(sizeof(int) * self->samples_length);
        converter = FrameList_get_char_to_int_converter(self->bits_per_sample,
                                                        is_big_endian,
                                                        is_signed);
        if (converter) {
            FrameList_char_to_samples(self->samples,
                                      data,
                                      converter,
                                      self->samples_length,
                                      self->bits_per_sample);
        } else {
            PyErr_SetString(PyExc_ValueError,
                            "unsupported number of bits per sample");
            return -1;
        }
    }

    return 0;
}

PyObject*
FrameList_blank(PyObject *dummy, PyObject *args)
{
    pcm_FrameList *framelist = FrameList_create();
    framelist->frames = framelist->channels = 0;
    framelist->bits_per_sample = 8;
    framelist->samples_length = 0;
    framelist->samples = malloc(0);
    return (PyObject*)framelist;
}

pcm_FrameList*
FrameList_create(void)
{
    return (pcm_FrameList*)_PyObject_New(&pcm_FrameListType);
}

int
FrameList_CheckExact(PyObject *o)
{
    return o->ob_type == &pcm_FrameListType;
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
    return o->samples_length;
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
    unsigned i;

    if ((a->frames == b->frames) &&
        (a->channels == b->channels) &&
        (a->bits_per_sample == b->bits_per_sample) &&
        (a->samples_length == b->samples_length)) {
        for (i = 0; i < a->samples_length; i++) {
            if (a->samples[i] != b->samples[i])
                return 0;
        }
        return 1;
    } else {
        return 0;
    }
}

PyObject*
FrameList_GetItem(pcm_FrameList *o, Py_ssize_t i)
{
    if ((i >= o->samples_length) || (i < 0)) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    } else {
        return Py_BuildValue("i", o->samples[i]);
    }
}

PyObject*
FrameList_frame(pcm_FrameList *self, PyObject *args)
{
    int frame_number;
    pcm_FrameList *frame;

    if (!PyArg_ParseTuple(args, "i", &frame_number))
        return NULL;
    if ((frame_number < 0) || (frame_number >= self->frames)) {
        PyErr_SetString(PyExc_IndexError, "frame number out of range");
        return NULL;
    }

    frame = FrameList_create();
    frame->frames = 1;
    frame->channels = self->channels;
    frame->bits_per_sample = self->bits_per_sample;
    frame->samples = malloc(sizeof(int) * self->channels);
    frame->samples_length = self->channels;
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
    unsigned i, j;
    unsigned samples_length;
    int total_channels;

    if (!PyArg_ParseTuple(args, "i", &channel_number))
        return NULL;
    if ((channel_number < 0) || (channel_number >= self->channels)) {
        PyErr_SetString(PyExc_IndexError, "channel number out of range");
        return NULL;
    }

    channel = FrameList_create();
    channel->frames = self->frames;
    channel->channels = 1;
    channel->bits_per_sample = self->bits_per_sample;
    channel->samples = malloc(sizeof(int) * self->frames);
    channel->samples_length = self->frames;

    samples_length = self->samples_length;
    total_channels = self->channels;
    for (j=0, i = channel_number;
         i < samples_length;
         j++, i += total_channels) {
        channel->samples[j] = self->samples[i];
    }

    return (PyObject*)channel;
}

PyObject*
FrameList_to_bytes(pcm_FrameList *self, PyObject *args)
{
    int is_big_endian;
    int is_signed;
    unsigned char *bytes;
    Py_ssize_t bytes_size;
    PyObject *bytes_obj;

    if (!PyArg_ParseTuple(args, "ii", &is_big_endian, &is_signed))
        return NULL;

    bytes_size = (self->bits_per_sample / 8) * self->samples_length;
    bytes = malloc(bytes_size);

    if (bytes_size > 0) {
        FrameList_samples_to_char(
             bytes, self->samples,
             FrameList_get_int_to_char_converter(self->bits_per_sample,
                                                 is_big_endian,
                                                 is_signed),
             self->samples_length,
             self->bits_per_sample);
    }

    bytes_obj = PyString_FromStringAndSize((char*)bytes, bytes_size);
    free(bytes);
    return bytes_obj;
}

PyObject*
FrameList_split(pcm_FrameList *self, PyObject *args)
{
    pcm_FrameList *head = NULL;
    pcm_FrameList *tail = NULL;
    PyObject* tuple;
    int split_point;

    if (!PyArg_ParseTuple(args, "i", &split_point))
        goto error;

    if (split_point < 0) {
        PyErr_SetString(PyExc_IndexError, "split point must be positive");
        goto error;
    } else if (split_point >= self->frames) {
        head = self;
        Py_INCREF(head);
        tail = FrameList_create();
        tail->frames = 0;
        tail->channels = self->channels;
        tail->bits_per_sample = self->bits_per_sample;
        tail->samples_length = 0;
        tail->samples = malloc(0);
    } else if (split_point == 0) {
        head = FrameList_create();
        head->frames = 0;
        head->channels = self->channels;
        head->bits_per_sample = self->bits_per_sample;
        head->samples_length = 0;
        head->samples = malloc(0);
        tail = self;
        Py_INCREF(tail);
    } else {
        head = FrameList_create();
        head->frames = split_point;
        head->samples_length = (head->frames * self->channels);
        head->samples = malloc(head->samples_length * sizeof(int));
        memcpy(head->samples,
               self->samples,
               head->samples_length * sizeof(int));

        tail = FrameList_create();
        tail->frames = (self->frames - split_point);
        tail->samples_length = (tail->frames * self->channels);
        tail->samples = malloc(tail->samples_length * sizeof(int));
        memcpy(tail->samples,
               self->samples + head->samples_length,
               tail->samples_length * sizeof(int));

        head->channels = tail->channels = self->channels;
        head->bits_per_sample = tail->bits_per_sample = self->bits_per_sample;
    }

    tuple = Py_BuildValue("(O,O)", head, tail);
    Py_DECREF(head);
    Py_DECREF(tail);
    return tuple;
 error:
    Py_XDECREF(head);
    Py_XDECREF(tail);
    return NULL;
}

PyObject*
FrameList_concat(pcm_FrameList *a, PyObject *bb)
{
    pcm_FrameList *concat = NULL;
    pcm_FrameList *b;

    if (!FrameList_CheckExact(bb)) {
        PyErr_SetString(PyExc_TypeError,
                        "can only concatenate FrameList with other FrameLists"
                        );
        goto error;
    } else {
        b = (pcm_FrameList*)bb;
    }

    if (a->channels != b->channels) {
        PyErr_SetString(PyExc_ValueError,
                        "both FrameLists must have the same number of channels"
                        );
        goto error;
    }
    if (a->bits_per_sample != b->bits_per_sample) {
        PyErr_SetString(PyExc_ValueError,
                        "both FrameLists must have the same number "
                        "of bits per sample");
        goto error;
    }

    concat = FrameList_create();
    concat->frames = a->frames + b->frames;
    concat->channels = a->channels;
    concat->bits_per_sample = a->bits_per_sample;
    concat->samples_length = a->samples_length + b->samples_length;
    concat->samples = malloc(concat->samples_length * sizeof(int));
    memcpy(concat->samples, a->samples, a->samples_length * sizeof(int));
    memcpy(concat->samples + a->samples_length,
           b->samples,
           b->samples_length * sizeof(int));

    return (PyObject*)concat;
 error:
    Py_XDECREF(concat);
    return NULL;
}

PyObject*
FrameList_to_float(pcm_FrameList *self, PyObject *args)
{
    unsigned i;
    int adjustment;
    pcm_FloatFrameList *framelist = FloatFrameList_create();
    framelist->frames = self->frames;
    framelist->channels = self->channels;
    framelist->samples_length = self->samples_length;
    framelist->samples = malloc(sizeof(double) * framelist->samples_length);

    adjustment = 1 << (self->bits_per_sample - 1);
    for (i = 0; i < self->samples_length; i++) {
        framelist->samples[i] = ((double)self->samples[i]) / adjustment;
    }

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

void
FrameList_char_to_samples(int *samples,
                          unsigned char *data,
                          FrameList_char_to_int_converter converter,
                          unsigned samples_length,
                          int bits_per_sample)
{
    int bytes_per_sample = bits_per_sample / 8;
    int i;

    for (i = 0; i < samples_length; i++, data += bytes_per_sample) {
        samples[i] = converter(data);
    }
}

#ifndef STANDALONE
PyObject*
FrameList_from_list(PyObject *dummy, PyObject *args)
{
    pcm_FrameList *framelist = NULL;
    PyObject *list;
    PyObject *integer = NULL;
    Py_ssize_t list_len, i;
    long integer_val;
    int adjustment;
    unsigned int channels;
    unsigned int bits_per_sample;
    int is_signed;

    if (!PyArg_ParseTuple(args, "OIIi", &list,
                          &channels,
                          &bits_per_sample,
                          &is_signed))
        goto error;

    if ((list_len = PySequence_Size(list)) == -1)
        goto error;

    if (list_len % channels) {
        PyErr_SetString(PyExc_ValueError,
                        "number of samples must be divisible by "
                        "number of channels");
        goto error;
    }

    switch (bits_per_sample) {
    case 8:
    case 16:
    case 24:
        break;
    default:
        PyErr_SetString(PyExc_ValueError,
                        "unsupported number of bits per sample");
        goto error;
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
    framelist->samples_length = (unsigned int)list_len;
    framelist->frames = (unsigned int)list_len / framelist->channels;
    for (i = 0; i < list_len; i++) {
        if ((integer = PySequence_GetItem(list, i)) == NULL)
            goto error;
        if (((integer_val = PyInt_AsLong(integer)) == -1) &&
            PyErr_Occurred())
            goto error;
        else {
            framelist->samples[i] = (int)(integer_val - adjustment);
            Py_DECREF(integer);
        }
    }

    return (PyObject*)framelist;
 error:
    Py_XDECREF(framelist);
    Py_XDECREF(integer);
    return NULL;
}

PyObject*
FrameList_from_frames(PyObject *dummy, PyObject *args)
{
    PyObject *framelist_obj = NULL;
    pcm_FrameList *framelist = NULL;
    PyObject *list;
    PyObject *list_item = NULL;
    Py_ssize_t list_len, i;
    pcm_FrameList *frame;

    if (!PyArg_ParseTuple(args, "O", &list))
        goto error;

    if ((list_len = PySequence_Size(list)) == -1)
        goto error;

    if ((framelist_obj = PySequence_GetItem(list, 0)) == NULL)
        goto error;

    if (!FrameList_CheckExact(framelist_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "frames must be of type FrameList");
        goto error;
    }

    frame = (pcm_FrameList*)framelist_obj;
    if (frame->frames != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all subframes must be 1 frame long");
        goto error;
    }

    framelist = FrameList_create();
    framelist->frames = (unsigned int)list_len;
    framelist->channels = frame->channels;
    framelist->bits_per_sample = frame->bits_per_sample;
    framelist->samples_length = (unsigned int)list_len * frame->channels;
    framelist->samples = malloc(sizeof(int) * framelist->samples_length);

    memcpy(framelist->samples, frame->samples,
           sizeof(int) * frame->samples_length);

    for (i = 1; i < list_len; i++) {
        if ((list_item = PySequence_GetItem(list, i)) == NULL)
            goto error;
        if (!FrameList_CheckExact(list_item)) {
            PyErr_SetString(PyExc_TypeError,
                            "frames must be of type FrameList");
            goto error;
        }
        frame = (pcm_FrameList*)list_item;
        if (frame->channels != framelist->channels) {
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must have the same "
                            "number of channels");
            goto error;
        }
        if (frame->bits_per_sample != framelist->bits_per_sample) {
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must have the same "
                            "number of bits per sample");
            goto error;
        }

        if (frame->frames != 1) {
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must be 1 frame long");
            goto error;
        }

        memcpy(framelist->samples + (i * framelist->channels),
               frame->samples,
               sizeof(int) * frame->samples_length);
        Py_DECREF(list_item);
    }

    Py_DECREF(framelist_obj);
    return (PyObject*)framelist;
 error:
    Py_XDECREF(list_item);
    Py_XDECREF(framelist);
    Py_XDECREF(framelist_obj);
    return NULL;
}

PyObject*
FrameList_from_channels(PyObject *dummy, PyObject *args)
{
    PyObject *framelist_obj = NULL;
    pcm_FrameList *framelist = NULL;
    PyObject *list;
    PyObject *list_item = NULL;
    Py_ssize_t list_len, i;
    pcm_FrameList *channel;
    unsigned j;

    if (!PyArg_ParseTuple(args, "O", &list))
        goto error;

    if ((list_len = PySequence_Size(list)) == -1)
        goto error;

    if ((framelist_obj = PySequence_GetItem(list, 0)) == NULL)
        goto error;

    if (!FrameList_CheckExact(framelist_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "channels must be of type FrameList");
        goto error;
    }

    channel = (pcm_FrameList*)framelist_obj;
    if (channel->channels != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all channels must be 1 channel wide");
        goto error;
    }

    framelist = FrameList_create();
    framelist->frames = channel->frames;
    framelist->channels = (unsigned int)list_len;
    framelist->bits_per_sample = channel->bits_per_sample;
    framelist->samples_length = framelist->frames * (unsigned int)list_len;
    framelist->samples = malloc(sizeof(int) * framelist->samples_length);

    for (j = 0; j < channel->samples_length; j++) {
        framelist->samples[j * list_len] = channel->samples[j];
    }

    for (i = 1; i < list_len; i++) {
        if ((list_item = PySequence_GetItem(list, i)) == NULL)
            goto error;
        if (!FrameList_CheckExact(list_item)) {
            PyErr_SetString(PyExc_TypeError,
                            "channels must be of type FrameList");
            goto error;
        }
        channel = (pcm_FrameList*)list_item;
        if (channel->frames != framelist->frames) {
            PyErr_SetString(PyExc_ValueError,
                            "all channels must have the same "
                            "number of frames");
            goto error;
        }
        if (channel->bits_per_sample != framelist->bits_per_sample) {
            PyErr_SetString(PyExc_ValueError,
                            "all channels must have the same "
                            "number of bits per sample");
            goto error;
        }

        if (channel->channels != 1) {
            PyErr_SetString(PyExc_ValueError,
                            "all channels must be 1 channel wide");
            goto error;
        }

        for (j = 0; j < channel->samples_length; j++) {
            framelist->samples[(j * list_len) + i] = channel->samples[j];
        }
        Py_DECREF(list_item);
    }

    Py_DECREF(framelist_obj);

    return (PyObject*)framelist;
 error:
    Py_XDECREF(framelist);
    Py_XDECREF(framelist_obj);
    Py_XDECREF(list_item);
    return NULL;
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
    {"to_int", (PyCFunction)FloatFrameList_to_int,
     METH_VARARGS,
     "FF.to_int(bits_per_sample) -> FrameList"},
    {NULL}
};

static PySequenceMethods pcm_FloatFrameListType_as_sequence = {
    (lenfunc)FloatFrameList_len,          /* sq_length */
    (binaryfunc)FloatFrameList_concat,    /* sq_concat */
    (ssizeargfunc)NULL,                   /* sq_repeat */
    (ssizeargfunc)FloatFrameList_GetItem, /* sq_item */
    (ssizessizeargfunc)NULL,              /* sq_slice */
    (ssizeobjargproc)NULL,                /* sq_ass_item */
    (ssizessizeobjargproc)NULL,           /* sq_ass_slice */
    (objobjproc)NULL,                     /* sq_contains */
    (binaryfunc)NULL,                     /* sq_inplace_concat */
    (ssizeargfunc)NULL,                   /* sq_inplace_repeat */
};

PyTypeObject pcm_FloatFrameListType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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
    0,                         /* tp_richcompare */
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
    self->ob_type->tp_free((PyObject*)self);
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
    PyObject *data_item;
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
        self->samples_length = (unsigned int)data_size;
        self->frames = (self->samples_length / self->channels);
        self->samples = malloc(sizeof(double) * self->samples_length);
    }

    for (i = 0; i < data_size; i++) {
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

int
FloatFrameList_CheckExact(PyObject *o)
{
    return o->ob_type == &pcm_FloatFrameListType;
}

PyObject*
FloatFrameList_blank(PyObject *dummy, PyObject *args)
{
    pcm_FloatFrameList *framelist = FloatFrameList_create();
    framelist->frames = framelist->channels = 0;
    framelist->samples_length = 0;
    framelist->samples = malloc(0);
    return (PyObject*)framelist;
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
    return o->samples_length;
}

PyObject*
FloatFrameList_GetItem(pcm_FloatFrameList *o, Py_ssize_t i)
{
    if ((i >= o->samples_length) || (i < 0)) {
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
    if ((frame_number < 0) || (frame_number >= self->frames)) {
        PyErr_SetString(PyExc_IndexError, "frame number out of range");
        return NULL;
    }

    frame = FloatFrameList_create();
    frame->frames = 1;
    frame->channels = self->channels;
    frame->samples = malloc(sizeof(double) * self->channels);
    frame->samples_length = self->channels;
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
    if ((channel_number < 0) || (channel_number >= self->channels)) {
        PyErr_SetString(PyExc_IndexError, "channel number out of range");
        return NULL;
    }

    channel = FloatFrameList_create();
    channel->frames = self->frames;
    channel->channels = 1;
    channel->samples = malloc(sizeof(double) * self->frames);
    channel->samples_length = self->frames;

    samples_length = self->samples_length;
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
    unsigned i;
    int adjustment;
    int sample_min;
    int sample_max;
    pcm_FrameList *framelist;
    int bits_per_sample;

    if (!PyArg_ParseTuple(args, "i", &bits_per_sample))
        return NULL;

    framelist = FrameList_create();
    framelist->frames = self->frames;
    framelist->channels = self->channels;
    framelist->bits_per_sample = bits_per_sample;
    framelist->samples_length = self->samples_length;
    framelist->samples = malloc(sizeof(int) * framelist->samples_length);

    adjustment = 1 << (bits_per_sample - 1);
    sample_min = -adjustment;
    sample_max = adjustment - 1;
    for (i = 0; i < self->samples_length; i++) {
        framelist->samples[i] =  MAX(MIN((int)(
                                         self->samples[i] * adjustment),
                                         sample_max),
                                     sample_min);
    }

    return (PyObject*)framelist;
}

PyObject*
FloatFrameList_split(pcm_FloatFrameList *self, PyObject *args)
{
    pcm_FloatFrameList *head = NULL;
    pcm_FloatFrameList *tail = NULL;
    PyObject* tuple;
    int split_point;

    if (!PyArg_ParseTuple(args, "i", &split_point))
        goto error;

    if (split_point < 0) {
        PyErr_SetString(PyExc_IndexError, "split point must be positive");
        goto error;
    } else if (split_point >= self->frames) {
        head = self;
        Py_INCREF(head);
        tail = FloatFrameList_create();
        tail->frames = 0;
        tail->channels = self->channels;
        tail->samples_length = 0;
        tail->samples = malloc(0);
    } else if (split_point == 0) {
        head = FloatFrameList_create();
        head->frames = 0;
        head->channels = self->channels;
        head->samples_length = 0;
        head->samples = malloc(0);
        tail = self;
        Py_INCREF(tail);
    } else {
        head = FloatFrameList_create();
        head->frames = split_point;
        head->samples_length = (head->frames * self->channels);
        head->samples = malloc(head->samples_length * sizeof(double));
        memcpy(head->samples,
               self->samples,
               head->samples_length * sizeof(double));

        tail = FloatFrameList_create();
        tail->frames = (self->frames - split_point);
        tail->samples_length = (tail->frames * self->channels);
        tail->samples = malloc(tail->samples_length * sizeof(double));
        memcpy(tail->samples,
               self->samples + head->samples_length,
               tail->samples_length * sizeof(double));

        head->channels = tail->channels = self->channels;
    }

    tuple = Py_BuildValue("(O,O)", head, tail);
    Py_DECREF(head);
    Py_DECREF(tail);
    return tuple;
 error:
    Py_XDECREF(head);
    Py_XDECREF(tail);
    return NULL;
}

PyObject*
FloatFrameList_concat(pcm_FloatFrameList *a, PyObject *bb)
{
    pcm_FloatFrameList *concat = NULL;
    pcm_FloatFrameList *b;

    if (!FloatFrameList_CheckExact(bb)) {
        PyErr_SetString(PyExc_TypeError,
                        "can only concatenate FloatFrameList "
                        "with other FloatFrameLists");
        goto error;
    } else {
        b = (pcm_FloatFrameList*)bb;
    }

    if (a->channels != b->channels) {
        PyErr_SetString(PyExc_ValueError,
                        "both FloatFrameLists must have the same "
                        "number of channels");
        goto error;
    }

    concat = FloatFrameList_create();
    concat->frames = a->frames + b->frames;
    concat->channels = a->channels;
    concat->samples_length = a->samples_length + b->samples_length;
    concat->samples = malloc(concat->samples_length * sizeof(double));
    memcpy(concat->samples, a->samples, a->samples_length * sizeof(double));
    memcpy(concat->samples + a->samples_length,
           b->samples,
           b->samples_length * sizeof(double));

    return (PyObject*)concat;
 error:
    Py_XDECREF(concat);
    return NULL;
}

PyObject*
FloatFrameList_from_frames(PyObject *dummy, PyObject *args)
{
    PyObject *framelist_obj = NULL;
    pcm_FloatFrameList *framelist = NULL;
    PyObject *list;
    PyObject *list_item = NULL;
    Py_ssize_t list_len, i;
    pcm_FloatFrameList *frame;

    if (!PyArg_ParseTuple(args, "O", &list))
        goto error;

    if ((list_len = PySequence_Size(list)) == -1)
        goto error;

    if ((framelist_obj = PySequence_GetItem(list, 0)) == NULL)
        goto error;

    if (!FloatFrameList_CheckExact(framelist_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "frames must be of type FloatFrameList");
        goto error;
    }

    frame = (pcm_FloatFrameList*)framelist_obj;
    if (frame->frames != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all subframes must be 1 frame long");
        goto error;
    }

    framelist = FloatFrameList_create();
    framelist->frames = (unsigned int)list_len;
    framelist->channels = frame->channels;
    framelist->samples_length = (unsigned int)list_len * frame->channels;
    framelist->samples = malloc(sizeof(double) * framelist->samples_length);

    memcpy(framelist->samples, frame->samples,
           sizeof(double) * frame->samples_length);

    for (i = 1; i < list_len; i++) {
        if ((list_item = PySequence_GetItem(list, i)) == NULL)
            goto error;
        if (!FloatFrameList_CheckExact(list_item)) {
            PyErr_SetString(PyExc_TypeError,
                            "frames must be of type FloatFrameList");
            goto error;
        }
        frame = (pcm_FloatFrameList*)list_item;
        if (frame->channels != framelist->channels) {
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must have the same "
                            "number of channels");
            goto error;
        }

        if (frame->frames != 1) {
            PyErr_SetString(PyExc_ValueError,
                            "all subframes must be 1 frame long");
            goto error;
        }

        memcpy(framelist->samples + (i * framelist->channels),
               frame->samples,
               sizeof(double) * frame->samples_length);
        Py_DECREF(list_item);
    }

    Py_DECREF(framelist_obj);
    return (PyObject*)framelist;
 error:
    Py_XDECREF(framelist);
    Py_XDECREF(framelist_obj);
    Py_XDECREF(list_item);
    return NULL;
}

PyObject*
FloatFrameList_from_channels(PyObject *dummy, PyObject *args)
{
    PyObject *framelist_obj = NULL;
    pcm_FloatFrameList *framelist = NULL;
    PyObject *list;
    PyObject *list_item = NULL;
    Py_ssize_t list_len, i;
    pcm_FloatFrameList *channel;
    unsigned j;

    if (!PyArg_ParseTuple(args, "O", &list))
        goto error;

    if ((list_len = PySequence_Size(list)) == -1)
        goto error;

    if ((framelist_obj = PySequence_GetItem(list, 0)) == NULL)
        goto error;

    if (!FloatFrameList_CheckExact(framelist_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "channels must be of type FloatFrameList");
        goto error;
    }

    channel = (pcm_FloatFrameList*)framelist_obj;
    if (channel->channels != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "all channels must be 1 channel wide");
        goto error;
    }

    framelist = FloatFrameList_create();
    framelist->frames = channel->frames;
    framelist->channels = (unsigned int)list_len;
    framelist->samples_length = framelist->frames * (unsigned int)list_len;
    framelist->samples = malloc(sizeof(double) * framelist->samples_length);

    for (j = 0; j < channel->samples_length; j++) {
        framelist->samples[j * list_len] = channel->samples[j];
    }

    for (i = 1; i < list_len; i++) {
        if ((list_item = PySequence_GetItem(list, i)) == NULL)
            goto error;
        if (!FloatFrameList_CheckExact(list_item)) {
            PyErr_SetString(PyExc_TypeError,
                            "channels must be of type FloatFrameList");
            goto error;
        }
        channel = (pcm_FloatFrameList*)list_item;
        if (channel->frames != framelist->frames) {
            PyErr_SetString(PyExc_ValueError,
                            "all channels must have the same "
                            "number of frames");
            goto error;
        }

        if (channel->channels != 1) {
            PyErr_SetString(PyExc_ValueError,
                            "all channels must be 1 channel wide");
            goto error;
        }

        for (j = 0; j < channel->samples_length; j++) {
            framelist->samples[(j * list_len) + i] = channel->samples[j];
        }
        Py_DECREF(list_item);
    }

    Py_DECREF(framelist_obj);

    return (PyObject*)framelist;
 error:
    Py_XDECREF(framelist_obj);
    Py_XDECREF(framelist);
    Py_XDECREF(list_item);
    return NULL;
}


PyMODINIT_FUNC
initpcm(void)
{
    PyObject* m;

    pcm_FrameListType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcm_FrameListType) < 0)
        return;

    pcm_FloatFrameListType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcm_FloatFrameListType) < 0)
        return;

    m = Py_InitModule3("pcm", module_methods,
                       "A PCM FrameList handling module.");

    Py_INCREF(&pcm_FrameListType);
    PyModule_AddObject(m, "FrameList",
                       (PyObject *)&pcm_FrameListType);
    Py_INCREF(&pcm_FloatFrameListType);
    PyModule_AddObject(m, "FloatFrameList",
                       (PyObject *)&pcm_FloatFrameListType);
}

#endif

FrameList_char_to_int_converter
FrameList_get_char_to_int_converter(int bits_per_sample,
                                    int is_big_endian,
                                    int is_signed)
{
    switch (bits_per_sample) {
    case 8:
        switch (is_big_endian) {
        case 0:
            switch (is_signed) {
            case 0:  /*8 bits-per-sample, little-endian, unsigned*/
                return FrameList_U8_char_to_int;
            default: /*8 bits-per-sample, little-endian, signed*/
                return FrameList_S8_char_to_int;
            }
        default:
            switch (is_signed) {
            case 0:  /*8 bits-per-sample, big-endian, unsigned*/
                return FrameList_U8_char_to_int;
            default: /*8 bits-per-sample, big-endian, signed*/
                return FrameList_S8_char_to_int;
            }
        }
    case 16:
        switch (is_big_endian) {
        case 0:
            switch (is_signed) {
            case 0:  /*16 bits-per-sample, little-endian, unsigned*/
                return FrameList_UL16_char_to_int;
            default: /*16 bits-per-sample, little-endian, signed*/
                return FrameList_SL16_char_to_int;
            }
        default:
            switch (is_signed) {
            case 0:  /*16 bits-per-sample, big-endian, unsigned*/
                return FrameList_UB16_char_to_int;
            default: /*16 bits-per-sample, big-endian, signed*/
                return FrameList_SB16_char_to_int;
            }
        }
    case 24:
        switch (is_big_endian) {
        case 0:
            switch (is_signed) {
            case 0:  /*24 bits-per-sample, little-endian, unsigned*/
                return FrameList_UL24_char_to_int;
            default: /*24 bits-per-sample, little-endian, signed*/
                return FrameList_SL24_char_to_int;
            }
        default:
            switch (is_signed) {
            case 0:  /*24 bits-per-sample, big-endian, unsigned*/
                return FrameList_UB24_char_to_int;
            default: /*24 bits-per-sample, big-endian, signed*/
                return FrameList_SB24_char_to_int;
            }
        }
    default:
        return NULL;
    }
}

int
FrameList_U8_char_to_int(unsigned char *s)
{
    return ((int)s[0]) - (1 << 7);
}

int
FrameList_S8_char_to_int(unsigned char *s)
{
    if (s[0] & 0x80) {
        /*negative*/
        return -(int)(0x100 - s[0]);
    } else {
        /*positive*/
        return (int)s[0];
    }
}

int
FrameList_UB16_char_to_int(unsigned char *s)
{
    return ((int)(s[0] << 8) | s[1]) - (1 << 15);
}

int
FrameList_UL16_char_to_int(unsigned char *s)
{
    return ((int)(s[1] << 8) | s[0]) - (1 << 15);
}

int
FrameList_SL16_char_to_int(unsigned char *s)
{
    if (s[1] & 0x80) {
        /*negative*/
        return -(int)(0x10000 - ((s[1] << 8) | s[0]));
    } else {
        /*positive*/
        return (int)(s[1] << 8) | s[0];
    }
}

int
FrameList_SB16_char_to_int(unsigned char *s)
{
    if (s[0] & 0x80) {
        /*negative*/
        return -(int)(0x10000 - ((s[0] << 8) | s[1]));
    } else {
        /*positive*/
        return (int)(s[0] << 8) | s[1];
    }
}

int
FrameList_UL24_char_to_int(unsigned char *s)
{
    return ((int)((s[2] << 16) | (s[1] << 8) | s[0])) - (1 << 23);
}

int
FrameList_UB24_char_to_int(unsigned char *s)
{
    return ((int)((s[0] << 16) | (s[1] << 8) | s[2])) - (1 << 23);
}

int
FrameList_SL24_char_to_int(unsigned char *s)
{
    if (s[2] & 0x80) {
        /*negative*/
        return -(int)(0x1000000 - ((s[2] << 16) | (s[1] << 8) | s[0]));
    } else {
        /*positive*/
        return (int)((s[2] << 16) | (s[1] << 8) | s[0]);
    }
}

int
FrameList_SB24_char_to_int(unsigned char *s)
{
    if (s[0] & 0x80) {
        /*negative*/
        return -(int)(0x1000000 - ((s[0] << 16) | (s[1] << 8) | s[2]));
    } else {
        /*positive*/
        return (int)((s[0] << 16) | (s[1] << 8) | s[2]);
    }
}

void
FrameList_samples_to_char(unsigned char *data,
                          int *samples,
                          FrameList_int_to_char_converter converter,
                          unsigned samples_length,
                          int bits_per_sample)
{
    int bytes_per_sample = bits_per_sample / 8;
    int i;

    for (i = 0; i < samples_length; i++, data += bytes_per_sample) {
        converter(samples[i], data);
    }
}

FrameList_int_to_char_converter
FrameList_get_int_to_char_converter(int bits_per_sample,
                                    int is_big_endian,
                                    int is_signed)
{
    switch (bits_per_sample) {
    case 8:
        switch (is_big_endian) {
        case 0:
            switch (is_signed) {
            case 0:  /*8 bits-per-sample, little-endian, unsigned*/
                return FrameList_int_to_U8_char;
            default: /*8 bits-per-sample, little-endian, signed*/
                return FrameList_int_to_S8_char;
            }
        default:
            switch (is_signed) {
            case 0:  /*8 bits-per-sample, big-endian, unsigned*/
                return FrameList_int_to_U8_char;
            default: /*8 bits-per-sample, big-endian, signed*/
                return FrameList_int_to_S8_char;
            }
        }
    case 16:
        switch (is_big_endian) {
        case 0:
            switch (is_signed) {
            case 0:  /*16 bits-per-sample, little-endian, unsigned*/
                return FrameList_int_to_UL16_char;
            default: /*16 bits-per-sample, little-endian, signed*/
                return FrameList_int_to_SL16_char;
            }
        default:
            switch (is_signed) {
            case 0:  /*16 bits-per-sample, big-endian, unsigned*/
                return FrameList_int_to_UB16_char;
            default: /*16 bits-per-sample, big-endian, signed*/
                return FrameList_int_to_SB16_char;
            }
        }
    case 24:
        switch (is_big_endian) {
        case 0:
            switch (is_signed) {
            case 0:  /*24 bits-per-sample, little-endian, unsigned*/
                return FrameList_int_to_UL24_char;
            default: /*24 bits-per-sample, little-endian, signed*/
                return FrameList_int_to_SL24_char;
            }
        default:
            switch (is_signed) {
            case 0:  /*24 bits-per-sample, big-endian, unsigned*/
                return FrameList_int_to_UB24_char;
            default: /*24 bits-per-sample, big-endian, signed*/
                return FrameList_int_to_SB24_char;
            }
        }
    default:
        return NULL;
    }
}

void
FrameList_int_to_S8_char(int i, unsigned char *s)
{
    if (i > 0x7F)
        i = 0x7F;  /*avoid overflow*/
    else if (i < -0x80)
        i = -0x80; /*avoid underflow*/

    if (i >= 0) {
        /*positive*/
        s[0] = i;
    } else {
        /*negative*/
        s[0] = (1 << 8) - (-i);
    }
}

void
FrameList_int_to_U8_char(int i, unsigned char *s)
{
    i += (1 << 7);
    s[0] = i & 0xFF;
}

void
FrameList_int_to_UB16_char(int i, unsigned char *s)
{
    i += (1 << 15);
    s[0] = (i >> 8) & 0xFF;
    s[1] = i & 0xFF;
}

void
FrameList_int_to_SB16_char(int i, unsigned char *s)
{
    if (i > 0x7FFF)
        i = 0x7FFF;
    else if (i < -0x8000)
        i = -0x8000;

    if (i < 0) {
        i = (1 << 16) - (-i);
    }

    s[0] = i >> 8;
    s[1] = i & 0xFF;
}

void
FrameList_int_to_UL16_char(int i, unsigned char *s)
{
    i += (1 << 15);
    s[1] = (i >> 8) & 0xFF;
    s[0] = i & 0xFF;
}

void
FrameList_int_to_SL16_char(int i, unsigned char *s)
{
    if (i > 0x7FFF)
        i = 0x7FFF;
    else if (i < -0x8000)
        i = -0x8000;

    if (i < 0) {
        i = (1 << 16) - (-i);
    }

    s[1] = i >> 8;
    s[0] = i & 0xFF;
}

void
FrameList_int_to_UB24_char(int i, unsigned char *s)
{
    i += (1 << 23);
    s[0] = (i >> 16) & 0xFF;
    s[1] = (i >> 8) & 0xFF;
    s[2] = i & 0xFF;
}

void
FrameList_int_to_SB24_char(int i, unsigned char *s)
{
    if (i > 0x7FFFFF)
        i = 0x7FFFFF;
    else if (i < -0x800000)
        i = -0x800000;

    if (i < 0) {
        i = (1 << 24) - (-i);
    }

    s[0] = i >> 16;
    s[1] = (i >> 8) & 0xFF;
    s[2] = i & 0xFF;
}

void
FrameList_int_to_UL24_char(int i, unsigned char *s)
{
    i += (1 << 23);
    s[2] = (i >> 16) & 0xFF;
    s[1] = (i >> 8) & 0xFF;
    s[0] = i & 0xFF;
}

void
FrameList_int_to_SL24_char(int i, unsigned char *s)
{
    if (i > 0x7FFFFF)
        i = 0x7FFFFF;
    else if (i < -0x800000)
        i = -0x800000;

    if (i < 0) {
        i = (1 << 24) - (-i);
    }

    s[2] = i >> 16;
    s[1] = (i >> 8) & 0xFF;
    s[0] = i & 0xFF;
}
