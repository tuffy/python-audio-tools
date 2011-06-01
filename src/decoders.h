#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

PyMethodDef module_methods[] = {
    {NULL}
};

/*the BitstreamReader object
  a simple wrapper around our Bitstream reading struct*/

typedef struct {
    PyObject_HEAD

    PyObject* file_obj;
    Bitstream* bitstream;
    int is_substream;
} decoders_BitstreamReader;

static PyObject*
BitstreamReader_read(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read64(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_byte_align(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_skip(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unread(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read_signed(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unary(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_limited_unary(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read_huffman_code(decoders_BitstreamReader *self,
                                  PyObject *args);

static PyObject*
BitstreamReader_tell(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_set_endianness(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_close(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_mark(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_rewind(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unmark(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_substream(decoders_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_substream_append(decoders_BitstreamReader *self,
                                 PyObject *args);

int
BitstreamReader_init(decoders_BitstreamReader *self, PyObject *args);

PyMethodDef BitstreamReader_methods[] = {
    {"read", (PyCFunction)BitstreamReader_read,
     METH_VARARGS, ""},
    {"read64", (PyCFunction)BitstreamReader_read64,
     METH_VARARGS, ""},
    {"skip", (PyCFunction)BitstreamReader_skip,
     METH_VARARGS, ""},
    {"byte_align", (PyCFunction)BitstreamReader_byte_align,
     METH_NOARGS, ""},
    {"unread", (PyCFunction)BitstreamReader_unread,
     METH_VARARGS, ""},
    {"read_signed", (PyCFunction)BitstreamReader_read_signed,
     METH_VARARGS, ""},
    {"unary", (PyCFunction)BitstreamReader_unary,
     METH_VARARGS, ""},
    {"limited_unary", (PyCFunction)BitstreamReader_limited_unary,
     METH_VARARGS, ""},
    {"read_huffman_code", (PyCFunction)BitstreamReader_read_huffman_code,
     METH_VARARGS, ""},
    {"tell", (PyCFunction)BitstreamReader_tell,
     METH_NOARGS, ""},
    {"set_endianness", (PyCFunction)BitstreamReader_set_endianness,
     METH_VARARGS, ""},
    {"close", (PyCFunction)BitstreamReader_close,
     METH_NOARGS, ""},
    {"mark", (PyCFunction)BitstreamReader_mark,
     METH_NOARGS, ""},
    {"rewind", (PyCFunction)BitstreamReader_rewind,
     METH_NOARGS, ""},
    {"unmark", (PyCFunction)BitstreamReader_unmark,
     METH_NOARGS, ""},
    {"substream", (PyCFunction)BitstreamReader_substream,
     METH_VARARGS, ""},
    {"substream_append", (PyCFunction)BitstreamReader_substream_append,
     METH_VARARGS, ""},
    {NULL}
};

void
BitstreamReader_dealloc(decoders_BitstreamReader *self);

static PyObject*
BitstreamReader_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds);

PyTypeObject decoders_BitstreamReaderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.BitstreamReader",    /*tp_name*/
    sizeof(decoders_BitstreamReader), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamReader_dealloc, /*tp_dealloc*/
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
    "BitstreamReader objects", /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    BitstreamReader_methods,   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)BitstreamReader_init,/* tp_init */
    0,                         /* tp_alloc */
    BitstreamReader_new,       /* tp_new */
};


typedef struct {
    PyObject_HEAD

    struct bs_huffman_table (*table)[][0x200];
} decoders_HuffmanTree;

int
HuffmanTree_init(decoders_HuffmanTree *self, PyObject *args);

void
HuffmanTree_dealloc(decoders_HuffmanTree *self);

static PyObject*
HuffmanTree_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

PyTypeObject decoders_HuffmanTreeType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.HuffmanTree",    /*tp_name*/
    sizeof(decoders_BitstreamReader), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamReader_dealloc, /*tp_dealloc*/
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
    "Huffman Tree objects",    /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    0,                         /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */

    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)HuffmanTree_init, /* tp_init */
    0,                         /* tp_alloc */
    HuffmanTree_new,          /* tp_new */
};
