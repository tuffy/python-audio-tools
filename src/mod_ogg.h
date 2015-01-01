#include <Python.h>
#include "ogg.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

PyMethodDef module_methods[] = {
    {NULL}
};

typedef struct {
    PyObject_HEAD

    struct ogg_page page;
} ogg_Page;

static PyObject*
Page_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
Page_init(ogg_Page *self, PyObject *args, PyObject *keywds);

void
Page_dealloc(ogg_Page *self);



static PyObject *
Page_get_packet_continuation(ogg_Page *self, void *closure);

static int
Page_set_packet_continuation(ogg_Page *self, PyObject *value, void *closure);

static PyObject *
Page_get_stream_beginning(ogg_Page *self, void *closure);

static int
Page_set_stream_beginning(ogg_Page *self, PyObject *value, void *closure);

static PyObject *
Page_get_stream_end(ogg_Page *self, void *closure);

static int
Page_set_stream_end(ogg_Page *self, PyObject *value, void *closure);

static PyObject *
Page_get_granule_position(ogg_Page *self, void *closure);

static int
Page_set_granule_position(ogg_Page *self, PyObject *value, void *closure);

static PyObject *
Page_get_bitstream_serial_number(ogg_Page *self, void *closure);

static int
Page_set_bitstream_serial_number(ogg_Page *self, PyObject *value,
                                 void *closure);

static PyObject *
Page_get_sequence_number(ogg_Page *self, void *closure);

static int
Page_set_sequence_number(ogg_Page *self, PyObject *value, void *closure);

PyGetSetDef Page_getseters[] = {
    {"packet_continuation",
     (getter)Page_get_packet_continuation,
     (setter)Page_set_packet_continuation,
     "packet continuation", NULL},
    {"stream_beginning",
     (getter)Page_get_stream_beginning,
     (setter)Page_set_stream_beginning,
     "stream beginning", NULL},
    {"stream_end",
     (getter)Page_get_stream_end,
     (setter)Page_set_stream_end,
     "stream ending", NULL},
    {"granule_position",
     (getter)Page_get_granule_position,
     (setter)Page_set_granule_position,
     "granule position", NULL},
    {"bitstream_serial_number",
     (getter)Page_get_bitstream_serial_number,
     (setter)Page_set_bitstream_serial_number,
     "bitstream serial number", NULL},
    {"sequence_number",
     (getter)Page_get_sequence_number,
     (setter)Page_set_sequence_number,
     "page sequence number", NULL},
    {NULL}
};

static Py_ssize_t
Page_len(ogg_Page *self);

static PyObject*
Page_GetItem(ogg_Page *self, Py_ssize_t i);

static PySequenceMethods ogg_PageType_as_sequence = {
    (lenfunc)Page_len,               /* sq_length */
    (binaryfunc)NULL,                /* sq_concat */
    (ssizeargfunc)NULL,              /* sq_repeat */
    (ssizeargfunc)Page_GetItem,      /* sq_item */
    (ssizessizeargfunc)NULL,         /* sq_slice */
    (ssizeobjargproc)NULL,           /* sq_ass_item */
    (ssizessizeobjargproc)NULL,      /* sq_ass_slice */
    (objobjproc)NULL,                /* sq_contains */
    (binaryfunc)NULL,                /* sq_inplace_concat */
    (ssizeargfunc)NULL,              /* sq_inplace_repeat */
};


static PyObject*
Page_append(ogg_Page *self, PyObject *args);

static PyObject*
Page_full(ogg_Page *self, PyObject *args);

static PyObject*
Page_size(ogg_Page *self, PyObject *args);

PyMethodDef Page_methods[] = {
    {"append", (PyCFunction)Page_append,
     METH_VARARGS, "append(segment)"},
    {"full", (PyCFunction)Page_full,
     METH_NOARGS, "full() -> True if Page can hold no more segments"},
    {"size", (PyCFunction)Page_size,
     METH_NOARGS, "size() -> total size of Ogg page in bytes"},
    {NULL}
};

PyTypeObject ogg_PageType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_ogg.Page",               /*tp_name*/
    sizeof(ogg_Page),          /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Page_dealloc,  /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    &ogg_PageType_as_sequence, /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "Ogg Page objects",        /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Page_methods,              /* tp_methods */
    0,                         /* tp_members */
    Page_getseters,            /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Page_init,       /* tp_init */
    0,                         /* tp_alloc */
    Page_new,                  /* tp_new */
};


typedef struct {
    PyObject_HEAD

    BitstreamReader *reader;
} ogg_PageReader;

static PyObject*
PageReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
PageReader_init(ogg_PageReader *self, PyObject *args, PyObject *kwds);

void
PageReader_dealloc(ogg_PageReader *self);

static PyObject*
PageReader_read(ogg_PageReader *self, PyObject *args);

static PyObject*
PageReader_close(ogg_PageReader *self, PyObject *args);

static PyObject*
PageReader_enter(ogg_PageReader *self, PyObject *args);

static PyObject*
PageReader_exit(ogg_PageReader *self, PyObject *args);

PyMethodDef PageReader_methods[] = {
    {"read", (PyCFunction)PageReader_read,
     METH_NOARGS, "read() -> Page"},
    {"close", (PyCFunction)PageReader_close,
     METH_NOARGS, "close()"},
    {"__enter__", (PyCFunction)PageReader_enter,
     METH_NOARGS, "__enter__() -> self"},
    {"__exit__", (PyCFunction)PageReader_exit,
     METH_VARARGS, "__exit__(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject ogg_PageReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_ogg.PageReader",         /*tp_name*/
    sizeof(ogg_PageReader),    /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)PageReader_dealloc, /*tp_dealloc*/
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
    "Ogg PageReader object",   /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    PageReader_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)PageReader_init, /* tp_init */
    0,                         /* tp_alloc */
    PageReader_new,            /* tp_new */
};


typedef struct {
    PyObject_HEAD

    BitstreamWriter *writer;
} ogg_PageWriter;

static PyObject*
PageWriter_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
PageWriter_init(ogg_PageWriter *self, PyObject *args, PyObject *kwds);

void
PageWriter_dealloc(ogg_PageWriter *self);

static PyObject*
PageWriter_write(ogg_PageWriter *self, PyObject *args);

static PyObject*
PageWriter_flush(ogg_PageWriter *self, PyObject *args);

static PyObject*
PageWriter_close(ogg_PageWriter *self, PyObject *args);

static PyObject*
PageWriter_enter(ogg_PageWriter *self, PyObject *args);

static PyObject*
PageWriter_exit(ogg_PageWriter *self, PyObject *args);

PyMethodDef PageWriter_methods[] = {
    {"write", (PyCFunction)PageWriter_write,
     METH_VARARGS, "write(Page)"},
    {"flush", (PyCFunction)PageWriter_flush,
     METH_NOARGS, "flush()"},
    {"close", (PyCFunction)PageWriter_close,
     METH_NOARGS, "close()"},
    {"__enter__", (PyCFunction)PageWriter_enter,
     METH_NOARGS, "__enter__() -> self"},
    {"__exit__", (PyCFunction)PageWriter_exit,
     METH_VARARGS, "__exit__(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

PyTypeObject ogg_PageWriterType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_ogg.PageWriter",         /*tp_name*/
    sizeof(ogg_PageWriter),    /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)PageWriter_dealloc, /*tp_dealloc*/
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
    "Ogg PageWriter object",   /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    PageWriter_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)PageWriter_init, /* tp_init */
    0,                         /* tp_alloc */
    PageWriter_new,            /* tp_new */
};
