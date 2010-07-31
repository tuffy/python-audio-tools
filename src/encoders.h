#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

PyObject*
encoders_encode_flac(PyObject *dummy,
                     PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_shn(PyObject *dummy,
                    PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_alac(PyObject *dummy,
                     PyObject *args, PyObject *keywds);

PyMethodDef module_methods[] = {
    {"encode_flac", (PyCFunction)encoders_encode_flac,
     METH_VARARGS | METH_KEYWORDS, "Encode FLAC file from PCMReader"},
    {"encode_shn", (PyCFunction)encoders_encode_shn,
     METH_VARARGS | METH_KEYWORDS, "Encode Shorten file from PCMReader"},
    {"encode_alac", (PyCFunction)encoders_encode_alac,
     METH_VARARGS | METH_KEYWORDS, "Encode ALAC file from PCMReader"},
    {NULL}
};

typedef struct {
    PyObject_HEAD

    PyObject* file_obj;
    Bitstream* bitstream;
} encoders_BitstreamWriter;

static PyObject*
BitstreamWriter_write(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_signed(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write64(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_unary(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_byte_align(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_close(encoders_BitstreamWriter *self, PyObject *args);

int
BitstreamWriter_init(encoders_BitstreamWriter *self, PyObject *args);

PyMethodDef BitstreamWriter_methods[] = {
    {"write", (PyCFunction)BitstreamWriter_write,
     METH_VARARGS, ""},
    {"write_signed", (PyCFunction)BitstreamWriter_write_signed,
     METH_VARARGS, ""},
    {"unary", (PyCFunction)BitstreamWriter_unary,
     METH_VARARGS, ""},
    {"byte_align", (PyCFunction)BitstreamWriter_byte_align,
     METH_NOARGS, ""},
    {"close", (PyCFunction)BitstreamWriter_close,
     METH_NOARGS, ""},
    {"write64", (PyCFunction)BitstreamWriter_write64,
     METH_VARARGS, ""},
    {NULL}
};

void
BitstreamWriter_dealloc(encoders_BitstreamWriter *self);

static PyObject*
BitstreamWriter_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds);

PyTypeObject encoders_BitstreamWriterType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "encoders.BitstreamWriters",    /*tp_name*/
    sizeof(encoders_BitstreamWriter), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamWriter_dealloc, /*tp_dealloc*/
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
    "BitstreamWriter objects", /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    BitstreamWriter_methods,   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)BitstreamWriter_init,/* tp_init */
    0,                         /* tp_alloc */
    BitstreamWriter_new,       /* tp_new */
};
