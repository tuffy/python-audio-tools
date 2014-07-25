#include <Python.h>
#include <stdint.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

    unsigned total_pcm_frames;
    unsigned pcm_frame_range;
    unsigned i;
    unsigned j;
    unsigned start_offset;
    unsigned end_offset;
    uint64_t *checksums_v1;
    uint64_t *checksums_v2;
    uint32_t *initial_values;
    unsigned initial_values_index;
    uint32_t *final_values;
    unsigned final_values_index;
    uint64_t values_sum;

    PyObject* framelist_class;
} accuraterip_Checksum;

static PyObject*
Checksum_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
Checksum_init(accuraterip_Checksum *self, PyObject *args, PyObject *kwds);

void
Checksum_dealloc(accuraterip_Checksum *self);

static PyObject*
Checksum_update(accuraterip_Checksum* self, PyObject *args);

static void
checksum_update_frame(accuraterip_Checksum* self, int left, int right);

static PyObject*
Checksum_checksums_v1(accuraterip_Checksum* self, PyObject *args);

static PyObject*
Checksum_checksums_v2(accuraterip_Checksum* self, PyObject *args);

static PyMethodDef Checksum_methods[] = {
    {"update", (PyCFunction)Checksum_update,
     METH_VARARGS, "update(framelist)"},
    {"checksums_v1", (PyCFunction)Checksum_checksums_v1,
     METH_NOARGS, "checksums_v1() -> [crc, crc, ...]"},
    {"checksums_v2", (PyCFunction)Checksum_checksums_v2,
     METH_NOARGS, "checksums_v2() -> [crc, crc, ...]"},
    {NULL}
};

static PyTypeObject accuraterip_ChecksumType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_accuraterip.Checksum", /*tp_name*/
    sizeof(accuraterip_Checksum),   /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Checksum_dealloc, /*tp_dealloc*/
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
    "Checksum objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Checksum_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Checksum_init, /* tp_init */
    0,                         /* tp_alloc */
    Checksum_new,            /* tp_new */
};
