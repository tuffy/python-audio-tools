#include <Python.h>
#include <stdint.h>

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

    uint32_t checksum;
    uint32_t track_index;
    uint32_t start_offset;
    uint32_t end_offset;

    PyObject* framelist_class;
} accuraterip_ChecksumV1;

static PyObject*
ChecksumV1_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
ChecksumV1_init(accuraterip_ChecksumV1 *self, PyObject *args, PyObject *kwds);

void
ChecksumV1_dealloc(accuraterip_ChecksumV1 *self);

static PyObject*
ChecksumV1_update(accuraterip_ChecksumV1* self, PyObject *args);

static PyObject*
ChecksumV1_checksum(accuraterip_ChecksumV1* self, PyObject *args);

static PyMethodDef ChecksumV1_methods[] = {
    {"update", (PyCFunction)ChecksumV1_update,
     METH_VARARGS, "update(framelist) updates with the given FrameList"},
    {"checksum", (PyCFunction)ChecksumV1_checksum,
     METH_NOARGS, "checksum() -> calculcated 32-bit checksum"},
    {NULL}
};

static PyTypeObject accuraterip_ChecksumV1Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_accuraterip.ChecksumV1", /*tp_name*/
    sizeof(accuraterip_ChecksumV1),   /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ChecksumV1_dealloc, /*tp_dealloc*/
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
    "ChecksumV1 objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ChecksumV1_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ChecksumV1_init, /* tp_init */
    0,                         /* tp_alloc */
    ChecksumV1_new,            /* tp_new */
};


typedef struct {
    PyObject_HEAD

    uint32_t checksum;
    uint32_t track_index;
    uint32_t start_offset;
    uint32_t end_offset;

    PyObject *framelist_class;
} accuraterip_ChecksumV2;

static PyObject*
ChecksumV2_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
ChecksumV2_init(accuraterip_ChecksumV2 *self, PyObject *args, PyObject *kwds);

void
ChecksumV2_dealloc(accuraterip_ChecksumV2 *self);

static PyObject*
ChecksumV2_update(accuraterip_ChecksumV2* self, PyObject *args);

static PyObject*
ChecksumV2_checksum(accuraterip_ChecksumV2* self, PyObject *args);

static PyMethodDef ChecksumV2_methods[] = {
    {"update", (PyCFunction)ChecksumV2_update,
     METH_VARARGS, "update(framelist) updates with the given FrameList"},
    {"checksum", (PyCFunction)ChecksumV2_checksum,
     METH_NOARGS, "checksum() -> calculcated 32-bit checksum"},
    {NULL}
};

static PyTypeObject accuraterip_ChecksumV2Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_accuraterip.ChecksumV2", /*tp_name*/
    sizeof(accuraterip_ChecksumV2),   /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ChecksumV2_dealloc, /*tp_dealloc*/
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
    "ChecksumV2 objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ChecksumV2_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ChecksumV2_init, /* tp_init */
    0,                         /* tp_alloc */
    ChecksumV2_new,            /* tp_new */
};
