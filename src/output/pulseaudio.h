#include <Python.h>
#include <pulse/pulseaudio.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger
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

typedef struct {
    PyObject_HEAD

    pa_threaded_mainloop* mainloop;
    pa_mainloop_api* mainloop_api;
    pa_context* context;
    pa_stream* stream;
} output_PulseAudio;

static PyObject* PulseAudio_play(output_PulseAudio *self, PyObject *args);
static PyObject* PulseAudio_pause(output_PulseAudio *self, PyObject *args);
static PyObject* PulseAudio_resume(output_PulseAudio *self, PyObject *args);
static PyObject* PulseAudio_flush(output_PulseAudio *self, PyObject *args);
static PyObject* PulseAudio_get_volume(output_PulseAudio *self, PyObject *args);
static PyObject* PulseAudio_set_volume(output_PulseAudio *self, PyObject *args);
static PyObject* PulseAudio_close(output_PulseAudio *self, PyObject *args);

static PyObject* PulseAudio_new(PyTypeObject *type,
                                PyObject *args,
                                PyObject *kwds);
void PulseAudio_dealloc(output_PulseAudio *self);
int PulseAudio_init(output_PulseAudio *self, PyObject *args, PyObject *kwds);

PyGetSetDef PulseAudio_getseters[] = {
    {NULL}
};

PyMethodDef PulseAudio_methods[] = {
    {"play", (PyCFunction)PulseAudio_play, METH_VARARGS, ""},
    {"pause", (PyCFunction)PulseAudio_pause, METH_NOARGS, ""},
    {"resume", (PyCFunction)PulseAudio_resume, METH_NOARGS, ""},
    {"flush", (PyCFunction)PulseAudio_flush, METH_NOARGS, ""},
    {"get_volume", (PyCFunction)PulseAudio_get_volume, METH_NOARGS, ""},
    {"set_volume", (PyCFunction)PulseAudio_set_volume, METH_VARARGS, ""},
    {"close", (PyCFunction)PulseAudio_close, METH_NOARGS, ""},
    {NULL}
};

PyTypeObject output_PulseAudioType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "output.PulseAudio",        /*tp_name*/
    sizeof(output_PulseAudio),  /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)PulseAudio_dealloc, /*tp_dealloc*/
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
    "PulseAudio objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    PulseAudio_methods,        /* tp_methods */
    0,                         /* tp_members */
    PulseAudio_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)PulseAudio_init, /* tp_init */
    0,                         /* tp_alloc */
    PulseAudio_new,            /* tp_new */
};
