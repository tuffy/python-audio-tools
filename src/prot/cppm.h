#include <Python.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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
} prot_CPPMDecoder;

/*the CPPMDecoder.__init__() method*/
int
CPPMDecoder_init(prot_CPPMDecoder *self,
                 PyObject *args, PyObject *kwds);

static PyObject*
CPPMDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

void
CPPMDecoder_dealloc(prot_CPPMDecoder *self);

PyGetSetDef CPPMDecoder_getseters[] = {
    {NULL}
};

PyMethodDef CPPMDecoder_methods[] = {
    {NULL}
};

PyTypeObject prot_CPPMDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "prot.CPPMDecoder",    /*tp_name*/
    sizeof(prot_CPPMDecoder), /*tp_basicsize*/
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
