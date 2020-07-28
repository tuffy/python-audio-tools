#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <alsa/asoundlib.h>
#include "../framelist.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger
 further modified by Brian Langenberger for use in Python Audio Tools

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

typedef struct output_ALSAAudio_s {
    PyObject_HEAD

    unsigned sample_rate;
    unsigned channels;
    unsigned bits_per_sample;

    unsigned buffer_size;
    union {
        int8_t *int8;
        int16_t *int16;
        int32_t *int32;
        //float *float32;
    } buffer;

    int (*play)(struct output_ALSAAudio_s *self, pcm_FrameList *framelist);

    PyObject *framelist_type;
    snd_pcm_t *output;
    snd_mixer_t *mixer;
    snd_mixer_elem_t *mixer_elem;
    long volume_min;
    long volume_max;
} output_ALSAAudio;

static PyObject*
ALSAAudio_play(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_pause(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_resume(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_flush(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_get_volume(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_set_volume(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_close(output_ALSAAudio *self, PyObject *args);

static PyObject*
ALSAAudio_new(PyTypeObject *type,
              PyObject *args,
              PyObject *kwds);

void
ALSAAudio_dealloc(output_ALSAAudio *self);

int
ALSAAudio_init(output_ALSAAudio *self, PyObject *args, PyObject *kwds);

PyGetSetDef ALSAAudio_getseters[] = {
    {NULL}
};

PyMethodDef ALSAAudio_methods[] = {
    {"play", (PyCFunction)ALSAAudio_play, METH_VARARGS, ""},
    {"pause", (PyCFunction)ALSAAudio_pause, METH_NOARGS, ""},
    {"resume", (PyCFunction)ALSAAudio_resume, METH_NOARGS, ""},
    {"flush", (PyCFunction)ALSAAudio_flush, METH_NOARGS, ""},
    {"get_volume", (PyCFunction)ALSAAudio_get_volume, METH_NOARGS, ""},
    {"set_volume", (PyCFunction)ALSAAudio_set_volume, METH_VARARGS, ""},
    {"close", (PyCFunction)ALSAAudio_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject output_ALSAAudioType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "output.ALSAAudio",        /*tp_name*/
    sizeof(output_ALSAAudio),  /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ALSAAudio_dealloc, /*tp_dealloc*/
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
    "ALSAAudio objects",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ALSAAudio_methods,         /* tp_methods */
    0,                         /* tp_members */
    ALSAAudio_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ALSAAudio_init,  /* tp_init */
    0,                         /* tp_alloc */
    ALSAAudio_new,             /* tp_new */
};

static snd_mixer_elem_t*
find_playback_mixer_element(snd_mixer_t *mixer, const char *name);
