#include <Python.h>
#ifdef HAS_UNPROT
#include "cppm.h"
#endif

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

typedef struct {
    PyObject_HEAD
#ifdef HAS_UNPROT
    struct cppm_decoder decoder;
#endif
} decoders_CPPMDecoder;

/*the CPPMDecoder.__init__() method*/
int
CPPMDecoder_init(decoders_CPPMDecoder *self,
                 PyObject *args, PyObject *kwds);

static PyObject*
CPPMDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

void
CPPMDecoder_dealloc(decoders_CPPMDecoder *self);

static PyObject*
CPPMDecoder_media_type(decoders_CPPMDecoder *self, void *closure);

static PyObject*
CPPMDecoder_media_key(decoders_CPPMDecoder *self, void *closure);

static PyObject*
CPPMDecoder_id_album_media(decoders_CPPMDecoder *self, void *closure);

PyGetSetDef CPPMDecoder_getseters[] = {
    {"media_type",
     (getter)CPPMDecoder_media_type, NULL, "media_type", NULL},
    {"media_key",
     (getter)CPPMDecoder_media_key, NULL, "media_key", NULL},
    {"id_album_media",
     (getter)CPPMDecoder_id_album_media, NULL, "id_album_media", NULL},
    {NULL}
};

static PyObject*
CPPMDecoder_decode(decoders_CPPMDecoder *self, PyObject *args);

PyMethodDef CPPMDecoder_methods[] = {
    {"decode", (PyCFunction)CPPMDecoder_decode,
     METH_VARARGS, "Decodes one or more 2048 byte blocks"},
    {NULL}
};

PyTypeObject decoders_CPPMDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.CPPMDecoder",    /*tp_name*/
    sizeof(decoders_CPPMDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CPPMDecoder_dealloc, /*tp_dealloc*/
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
    "CPPMDecoder objects", /* tp_doc */
    0,                     /* tp_traverse */
    0,                     /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    0,                     /* tp_iter */
    0,                     /* tp_iternext */
    CPPMDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    CPPMDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CPPMDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    CPPMDecoder_new,           /* tp_new */
};
