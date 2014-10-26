#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

PyObject*
bitstream_format_size(PyObject *dummy, PyObject *args);

PyObject*
bitstream_format_byte_size(PyObject *dummy, PyObject *args);

PyObject*
bitstream_parse_func(PyObject *dummy, PyObject *args);

PyObject*
bitstream_build_func(PyObject *dummy, PyObject *args);

PyMethodDef module_methods[] = {
    {"format_size", (PyCFunction)bitstream_format_size,
     METH_VARARGS, "Calculate size of format string in bits"}, /*FIXME*/
    {"format_byte_size", (PyCFunction)bitstream_format_byte_size,
     METH_VARARGS, "Calculate size of format string in bytes"},
    {"parse", (PyCFunction)bitstream_parse_func,
     METH_VARARGS, "parse(format, is_little_endian, data) -> [values]"},
    {"build", (PyCFunction)bitstream_build_func,
     METH_VARARGS, "build(format, is_little_endian, [values]) -> data"},
    {NULL}
};

/*the BitstreamReader object
  a simple wrapper around our Bitstream reading struct*/

typedef struct {
    PyObject_HEAD

    BitstreamReader* bitstream;
} bitstream_BitstreamReader;

static PyObject*
brpy_read_unsigned(BitstreamReader *br, unsigned bits);

static PyObject*
brpy_read_signed(BitstreamReader *br, unsigned bits);

/*reads byte_count bytes from reader to buffer
  returns 0 on success, 1 if a read error occurs with PyErr set accordingly*/
int
brpy_read_bytes_chunk(BitstreamReader *reader,
                      unsigned byte_count,
                      struct bs_buffer *buffer);

/*sets "minimum" to the smaller value of x or y
  returns the smaller object on success, or NULL with PyErr set
  if some comparison or conversion error occurs

  the reference count of either is *not* incremented*/
PyObject*
brpy_read_bytes_min(PyObject *x, PyObject *y, long *minimum);

/*given a byte count as a Python object (presumably numeric)
  returns a Python string of bytes read or NULL on error*/
static PyObject*
brpy_read_bytes_obj(BitstreamReader *reader, PyObject *byte_count);

/*skips byte_count bytes from reader
  returns 0 on success, 1 if a read error occurs with PyErr set accordingly*/
int
brpy_skip_bytes_chunk(BitstreamReader *reader,
                      unsigned byte_count);

/*given a byte count as a Python object (presumably numeric)
  returns 0 on success, 1 if a read error occurs with PyErr set accordingly*/
int
brpy_skip_bytes_obj(BitstreamReader *reader, PyObject *byte_count);

/*given a byte count, returns a Python string of bytes read
  or NULL on error*/
static PyObject*
brpy_read_bytes(BitstreamReader *reader, unsigned byte_count);

static PyObject*
BitstreamReader_read(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_byte_align(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_byte_aligned(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_skip(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_skip_bytes(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unread(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read_signed(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unary(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_skip_unary(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read_huffman_code(bitstream_BitstreamReader *self,
                                  PyObject *args);

static PyObject*
BitstreamReader_read_bytes(bitstream_BitstreamReader *self,
                           PyObject *args);

static PyObject*
BitstreamReader_set_endianness(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_close(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_getpos(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_setpos(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_seek(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_add_callback(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_pop_callback(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_call_callbacks(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_substream(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_parse(bitstream_BitstreamReader *self, PyObject *args);

int
BitstreamReader_init(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_enter(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_exit(bitstream_BitstreamReader *self, PyObject *args);

PyMethodDef BitstreamReader_methods[] = {
    {"read", (PyCFunction)BitstreamReader_read, METH_VARARGS,
     "read(bits) -> unsigned int"},
    {"skip", (PyCFunction)BitstreamReader_skip, METH_VARARGS,
     "skip(bits)\n"
     "skips over the given number of bits"},
    {"skip_bytes", (PyCFunction)BitstreamReader_skip_bytes, METH_VARARGS,
     "skip_bytes(bytes)\n"
     "skips over the given number of bytes"},
    {"byte_align", (PyCFunction)BitstreamReader_byte_align, METH_NOARGS,
     "byte_align()\n"
     "moves to the next whole byte boundary, if necessary"},
    {"byte_aligned", (PyCFunction)BitstreamReader_byte_aligned, METH_NOARGS,
     "byte_aligned() -> True if the stream is currently byte-aligned"},
    {"unread", (PyCFunction)BitstreamReader_unread, METH_VARARGS,
     "unread(bit)\n"
     "pushes a single bit back into the stream"},
    {"read_signed", (PyCFunction)BitstreamReader_read_signed, METH_VARARGS,
     "read_signed(bits) -> signed int"},
    {"unary", (PyCFunction)BitstreamReader_unary, METH_VARARGS,
     "unary(stop_bit) -> unsigned int\n"
     "counts the number of bits until the next stop bit"},
    {"skip_unary", (PyCFunction)BitstreamReader_skip_unary, METH_VARARGS,
     "skip_unary(stop_bit)\n"
     "skips a number of bits until the next stop bit"},
    {"read_huffman_code", (PyCFunction)BitstreamReader_read_huffman_code,
     METH_VARARGS,
     "read_huffman_code(huffman_tree) -> int\n"
     "given a compiled HuffmanTree, returns the next code from the stream"},
    {"read_bytes", (PyCFunction)BitstreamReader_read_bytes, METH_VARARGS,
     "read_bytes(bytes) -> string"},
    {"set_endianness", (PyCFunction)BitstreamReader_set_endianness,
     METH_VARARGS,
     "set_endianness(endianness)\n"
     "where 0 = big endian, 1 = little-endian\n"
     "the stream is automatically byte-aligned"},
    {"parse", (PyCFunction)BitstreamReader_parse, METH_VARARGS,
     "parse(format_string) -> [value1, value2, ...]\n"
     "where \"format_string\" maps to the calls:\n"
     "\"#u\" -> read(#)\n"
     "\"#s\" -> read_signed(#)\n"
     "\"#p\" -> skip(#)\n"
     "\"#P\" -> skip_bytes(#)\n"
     "\"#b\" -> read_bytes(#)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "r.parse(\"3u 4s 36u\") == [r.read(3), r.read_signed(4), r.read(36)]"},
    {"close", (PyCFunction)BitstreamReader_close, METH_NOARGS,
     "close()\n"
     "closes the stream and any underlying file object"},
    {"getpos", (PyCFunction)BitstreamReader_getpos, METH_NOARGS,
     "getpos() -> position"},
    {"setpos", (PyCFunction)BitstreamReader_setpos, METH_VARARGS,
     "setpos(position)"},
    {"seek", (PyCFunction)BitstreamReader_seek, METH_VARARGS,
     "seek(position, whence)\n"
     "positions the stream at the given position where\n"
     "position is stream position in bytes and\n"
     "whence 0 = stream start, 1 = current position, 2 = stream end\n"
     "no callbacks are performed on intervening bytes"},
    {"add_callback", (PyCFunction)BitstreamReader_add_callback, METH_VARARGS,
     "add_callback(function)\n"
     "where \"function\" takes a single byte as an argument\n"
     "and is called upon each read byte from the stream"},
    {"pop_callback", (PyCFunction)BitstreamReader_pop_callback, METH_NOARGS,
     "pop_callback() -> function\n"
     "removes and returns the most recently added callback"},
    {"call_callbacks", (PyCFunction)BitstreamReader_call_callbacks,
     METH_VARARGS,
     "call_callbacks(byte)\n"
     "calls the attached callbacks as if the byte had been read"},
    {"substream", (PyCFunction)BitstreamReader_substream, METH_VARARGS,
     "substream(bytes) -> BitstreamReader\n"
     "returns a sub-reader containing the given number of input bytes"},
    {"__enter__", (PyCFunction)BitstreamReader_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)BitstreamReader_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

void
BitstreamReader_dealloc(bitstream_BitstreamReader *self);

static PyObject*
BitstreamReader_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds);

void
BitstreamReader_callback(uint8_t byte, PyObject *callback);

PyTypeObject bitstream_BitstreamReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "bitstream.BitstreamReader",    /*tp_name*/
    sizeof(bitstream_BitstreamReader), /*tp_basicsize*/
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
    "BitstreamReader(file, endianness)", /* tp_doc */
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

    br_huffman_table_t* br_table;
    bw_huffman_table_t* bw_table;
} bitstream_HuffmanTree;

static PyObject*
HuffmanTree_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
HuffmanTree_init(bitstream_HuffmanTree *self, PyObject *args);

void
HuffmanTree_dealloc(bitstream_HuffmanTree *self);


PyTypeObject bitstream_HuffmanTreeType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "bitstream.HuffmanTree",    /*tp_name*/
    sizeof(bitstream_HuffmanTree), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)HuffmanTree_dealloc, /*tp_dealloc*/
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

/*BitstreamReaderPosition is an opaque container for positions
  returned by BitstreamReader.getpos()
  it has no methods or attributes and can't even be instantiated directly*/
typedef struct {
    PyObject_HEAD

    br_pos_t *pos;
} bitstream_BitstreamReaderPosition;

static PyObject*
BitstreamReaderPosition_new(PyTypeObject *type, PyObject *args,
                            PyObject *kwds);

int
BitstreamReaderPosition_init(bitstream_BitstreamReaderPosition *self,
                             PyObject *args);

void
BitstreamReaderPosition_dealloc(bitstream_BitstreamReaderPosition *self);

PyTypeObject bitstream_BitstreamReaderPositionType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "bitstream.BitstreamReaderPosition",    /*tp_name*/
    sizeof(bitstream_BitstreamReaderPosition), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamReaderPosition_dealloc, /*tp_dealloc*/
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
    "BitstreamReaderPosition", /* tp_doc */
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
    (initproc)BitstreamReaderPosition_init, /* tp_init */
    0,                         /* tp_alloc */
    BitstreamReaderPosition_new, /* tp_new */
};

PyObject*
bitstream_format_size(PyObject *dummy, PyObject *args)
{
    char* format_string;

    if (!PyArg_ParseTuple(args, "s", &format_string))
        return NULL;

    return Py_BuildValue("I", bs_format_size(format_string));
}

PyObject*
bitstream_format_byte_size(PyObject *dummy, PyObject *args)
{
    char* format_string;

    if (!PyArg_ParseTuple(args, "s", &format_string))
        return NULL;

    return Py_BuildValue("I", bs_format_byte_size(format_string));
}

typedef struct {
    PyObject_HEAD

    BitstreamWriter* bitstream;
} bitstream_BitstreamWriter;

static PyObject*
bwpy_min_unsigned(unsigned bits);

static PyObject*
bwpy_max_unsigned(unsigned bits);

static PyObject*
bwpy_min_signed(unsigned bits);

static PyObject*
bwpy_max_signed(unsigned bits);

static int
bwpy_in_range(PyObject *min_value, PyObject *value, PyObject *max_value);

static int
bw_validate_unsigned_range(unsigned bits, PyObject *value);

static int
bw_validate_signed_range(unsigned bits, PyObject *value);

static int
bwpy_write_unsigned(BitstreamWriter *bw, unsigned bits, PyObject *value);

static int
bwpy_write_signed(BitstreamWriter *bw, unsigned bits, PyObject *value);

static PyObject*
BitstreamWriter_write(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_signed(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_unary(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_huffman_code(bitstream_BitstreamWriter *self,
                                   PyObject *args);

static PyObject*
BitstreamWriter_byte_align(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_byte_aligned(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_set_endianness(bitstream_BitstreamWriter *self,
                               PyObject *args);

static PyObject*
BitstreamWriter_write_bytes(bitstream_BitstreamWriter *self,
                            PyObject *args);

static PyObject*
BitstreamWriter_add_callback(bitstream_BitstreamWriter *self,
                             PyObject *args);

static PyObject*
BitstreamWriter_pop_callback(bitstream_BitstreamWriter *self,
                             PyObject *args);

static PyObject*
BitstreamWriter_call_callbacks(bitstream_BitstreamWriter *self,
                               PyObject *args);

static PyObject*
BitstreamWriter_getpos(bitstream_BitstreamWriter *self,
                       PyObject *args);

static PyObject*
BitstreamWriter_setpos(bitstream_BitstreamWriter *self,
                       PyObject *args);

static PyObject*
BitstreamWriter_build(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_flush(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_close(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_enter(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_exit(bitstream_BitstreamWriter *self, PyObject *args);

int
BitstreamWriter_init(bitstream_BitstreamWriter *self, PyObject *args);

PyMethodDef BitstreamWriter_methods[] = {
    {"write", (PyCFunction)BitstreamWriter_write, METH_VARARGS,
     "write(bits, unsigned int)"},
    {"write_signed", (PyCFunction)BitstreamWriter_write_signed, METH_VARARGS,
     "write_signed(bits, signed int)"},
    {"unary", (PyCFunction)BitstreamWriter_unary, METH_VARARGS,
     "unary(stop_bit, unsigned int)\n"
     "where \"stop_bit\" must be 0 or 1\n"
     "writes value as the given number of not stop_bit values (1 or 0)\n"
     "followed by a stop_bit"},
    {"write_huffman_code",
    (PyCFunction)BitstreamWriter_write_huffman_code,
     METH_VARARGS, "write_huffman_code(huffman_tree, value)\n"
     "given a compiled HuffmanTree and int value,\n"
     "writes that value to the stream"},
    {"byte_align", (PyCFunction)BitstreamWriter_byte_align, METH_NOARGS,
     "byte_align()\n"
     "pads the stream with 0 bits until the next whole byte"},
    {"byte_aligned", (PyCFunction)BitstreamWriter_byte_aligned, METH_NOARGS,
     "byte_aligned() -> True if the stream is currently byte-aligned"},
    {"flush", (PyCFunction)BitstreamWriter_flush, METH_NOARGS,
     "flush()\n"
     "flushes pending data to any underlying file object"},
    {"close", (PyCFunction)BitstreamWriter_close, METH_NOARGS,
     "close()\n"
     "closes the stream and any underlying file object"},
    {"set_endianness", (PyCFunction)BitstreamWriter_set_endianness,
     METH_VARARGS,
     "set_endianness(endianness)\n"
     "where 0 = big endian, 1 = little endian"},
    {"write_bytes", (PyCFunction)BitstreamWriter_write_bytes, METH_VARARGS,
     "write_bytes(bytes, string)"},
    {"build", (PyCFunction)BitstreamWriter_build, METH_VARARGS,
     "build(format_string, [value1, value2, ...])\n"
     "where \"format_string\" maps to the calls:\n"
     "\"#u\" -> write(#, unsigned int value)\n"
     "\"#s\" -> write_signed(#, signed int value)\n"
     "\"#p\" -> write(#, 0)\n"
     "\"#P\" -> write(# * 8, 0)\n"
     "\"#b\" -> write_bytes(#, string value)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "w.build(\"3u 4s 36u\", [1, -2, 3L])\n   ==\n"
     "w.write(3, 1); w.write_signed(4, -2); w.write(36, 3L)"},
    {"add_callback", (PyCFunction)BitstreamWriter_add_callback, METH_VARARGS,
     "add_callback(function)\n"
     "where \"function\" takes a single byte as an argument\n"
     "and is called upon each written byte to the stream"},
    {"pop_callback", (PyCFunction)BitstreamWriter_pop_callback, METH_NOARGS,
     "pop_callback() -> function\n"
     "removes and returns the most recently added callback"},
    {"call_callbacks", (PyCFunction)BitstreamWriter_call_callbacks,
     METH_VARARGS,
     "call_callbacks(byte)\n"
     "calls the attached callbacks as if the byte had been written"},
    {"getpos", (PyCFunction)BitstreamWriter_getpos, METH_NOARGS,
     "getpos() -> position"},
    {"setpos", (PyCFunction)BitstreamWriter_setpos, METH_VARARGS,
     "setpos(position)"},
    {"__enter__", (PyCFunction)BitstreamWriter_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)BitstreamWriter_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

void
BitstreamWriter_dealloc(bitstream_BitstreamWriter *self);

static PyObject*
BitstreamWriter_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds);

PyTypeObject bitstream_BitstreamWriterType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "bitstream.BitstreamWriter", /*tp_name*/
    sizeof(bitstream_BitstreamWriter), /*tp_basicsize*/
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
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /*  tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
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


typedef struct {
    PyObject_HEAD

    BitstreamRecorder* bitstream;
} bitstream_BitstreamRecorder;

static PyObject*
BitstreamRecorder_write(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_write_signed(bitstream_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_unary(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_write_huffman_code(bitstream_BitstreamRecorder *self,
                                     PyObject *args);

static PyObject*
BitstreamRecorder_byte_align(bitstream_BitstreamRecorder *self,
                             PyObject *args);

static PyObject*
BitstreamRecorder_byte_aligned(bitstream_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_set_endianness(bitstream_BitstreamRecorder *self,
                                 PyObject *args);

static PyObject*
BitstreamRecorder_bits(bitstream_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_bytes(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_data(bitstream_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_swap(bitstream_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_write_bytes(bitstream_BitstreamRecorder *self,
                              PyObject *args);

static PyObject*
BitstreamRecorder_build(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_add_callback(bitstream_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_pop_callback(bitstream_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_call_callbacks(bitstream_BitstreamRecorder *self,
                                 PyObject *args);

static PyObject*
BitstreamRecorder_flush(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_reset(bitstream_BitstreamRecorder *self,
                        PyObject *args);

/*returns the internal BitstreamWriter struct of the given object
  or NULL if it is not a BitstreamWriter/Recorder*/
static BitstreamWriter*
internal_writer(PyObject *writer);

static PyObject*
BitstreamRecorder_copy(bitstream_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_getpos(bitstream_BitstreamRecorder *self,
                         PyObject *args);

static PyObject*
BitstreamRecorder_setpos(bitstream_BitstreamRecorder *self,
                         PyObject *args);

static PyObject*
BitstreamRecorder_close(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_enter(bitstream_BitstreamRecorder *self, PyObject *args);

static PyObject*
BitstreamRecorder_exit(bitstream_BitstreamRecorder *self, PyObject *args);

int
BitstreamRecorder_init(bitstream_BitstreamRecorder *self,
                       PyObject *args);

PyMethodDef BitstreamRecorder_methods[] = {
    {"write", (PyCFunction)BitstreamRecorder_write, METH_VARARGS,
     "write(bits, unsigned int)"},
    {"write_signed", (PyCFunction)BitstreamRecorder_write_signed, METH_VARARGS,
     "write_signed(bits, signed int)"},
    {"unary", (PyCFunction)BitstreamRecorder_unary, METH_VARARGS,
     "unary(stop_bit, unsigned int)\n"
     "where \"stop_bit\" must be 0 or 1\n"
     "writes value as the given number of not stop_bit values (1 or 0)\n"
     "followed by a stop_bit"},
    {"write_huffman_code",
    (PyCFunction)BitstreamRecorder_write_huffman_code,
     METH_VARARGS, "write_huffman_code(huffman_tree, value)\n"
     "given a compiled HuffmanTree and int value,\n"
     "writes that value to the stream"},
    {"byte_align", (PyCFunction)BitstreamRecorder_byte_align, METH_NOARGS,
     "byte_align()\n"
     "pads the stream with 0 bits until the next whole byte"},
    {"byte_aligned", (PyCFunction)BitstreamRecorder_byte_aligned, METH_NOARGS,
     "byte_aligned() -> True if the stream is currently byte-aligned"},
    {"flush", (PyCFunction)BitstreamRecorder_flush, METH_NOARGS,
     "flush()\n"
     "flushes pending data to any underlying file object"},
    {"close", (PyCFunction)BitstreamRecorder_close, METH_NOARGS,
    "close()\n"},
    {"set_endianness", (PyCFunction)BitstreamRecorder_set_endianness,
     METH_VARARGS,
     "set_endianness(endianness)\n"
     "where 0 = big endian, 1 = little endian"},
    {"write_bytes", (PyCFunction)BitstreamRecorder_write_bytes,
     METH_VARARGS,
     "write_bytes(bytes, string)"},
    {"bits", (PyCFunction)BitstreamRecorder_bits, METH_NOARGS,
     "bits() -> unsigned int\n"
     "returns the total number of bits written thus far"},
    {"bytes", (PyCFunction)BitstreamRecorder_bytes, METH_NOARGS,
     "bytes() -> unsigned int\n"
     "returns the total number of bytes written thus far"},
    {"data", (PyCFunction)BitstreamRecorder_data, METH_NOARGS,
     "data() -> string\n"
     "returns the written data as a string"},
    {"reset", (PyCFunction)BitstreamRecorder_reset, METH_NOARGS,
     "reset()\n"
     "removes all written data and resets the stream for new data"},
    {"copy", (PyCFunction)BitstreamRecorder_copy, METH_VARARGS,
     "copy(target)\n"
     "copies the written data to \"target\", which must be a\n"
     "BitstreamWriter or Recorder"},
    {"build", (PyCFunction)BitstreamRecorder_build, METH_VARARGS,
     "build(format_string, [value1, value2, ...])\n"
     "where \"format_string\" maps to the calls:\n"
     "\"#u\" -> write(#, unsigned int value)\n"
     "\"#s\" -> write_signed(#, signed int value)\n"
     "\"#p\" -> write(#, 0)\n"
     "\"#P\" -> write(# * 8, 0)\n"
     "\"#b\" -> write_bytes(#, string value)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "r.build(\"3u 4s 36u\", [1, -2, 3L])\n   ==\n"
     "r.write(3, 1); r.write_signed(4, -2); r.write(36, 3L)"},
    {"swap", (PyCFunction)BitstreamRecorder_swap, METH_VARARGS,
     "swap(recorder)\n"
     "swaps our written data with that of another BitstreamRecorder"},
    {"add_callback", (PyCFunction)BitstreamRecorder_add_callback,
     METH_VARARGS,
     "add_callback(function)\n"
     "where \"function\" takes a single byte as an argument\n"
     "and is called upon each written byte to the stream"},
    {"pop_callback", (PyCFunction)BitstreamRecorder_pop_callback,
     METH_NOARGS,
     "pop_callback() -> function\n"
     "removes and returns the most recently added callback"},
    {"call_callbacks", (PyCFunction)BitstreamRecorder_call_callbacks,
     METH_VARARGS,
     "call_callbacks(byte)\n"
     "calls the attached callbacks as if the byte had been written"},
    {"getpos", (PyCFunction)BitstreamRecorder_getpos, METH_NOARGS,
     "getpos() -> position"},
    {"setpos", (PyCFunction)BitstreamRecorder_setpos, METH_VARARGS,
     "setpos(position)"},
    {"__enter__", (PyCFunction)BitstreamRecorder_enter,
     METH_NOARGS, "enter() -> self"},
    {"__exit__", (PyCFunction)BitstreamRecorder_exit,
     METH_VARARGS, "exit(exc_type, exc_value, traceback) -> None"},
    {NULL}
};

void
BitstreamRecorder_dealloc(bitstream_BitstreamRecorder *self);

static PyObject*
BitstreamRecorder_new(PyTypeObject *type, PyObject *args,
                      PyObject *kwds);

PyTypeObject bitstream_BitstreamRecorderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "bitstream.BitstreamRecorder",    /*tp_name*/
    sizeof(bitstream_BitstreamRecorder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamRecorder_dealloc, /*tp_dealloc*/
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
    "BitstreamRecorder objects", /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /*  tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    BitstreamRecorder_methods, /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)BitstreamRecorder_init, /* tp_init */
    0,                         /* tp_alloc */
    BitstreamRecorder_new,       /* tp_new */
};

/*BitstreamWriterPosition is an opaque container for positions
  returned by BitstreamWriter.getpos()
  it has no methods or attributes and can't even be instantiated directly*/
typedef struct {
    PyObject_HEAD

    bw_pos_t *pos;
} bitstream_BitstreamWriterPosition;

static PyObject*
BitstreamWriterPosition_new(PyTypeObject *type, PyObject *args,
                            PyObject *kwds);

int
BitstreamWriterPosition_init(bitstream_BitstreamWriterPosition *self,
                             PyObject *args);

void
BitstreamWriterPosition_dealloc(bitstream_BitstreamWriterPosition *self);

PyTypeObject bitstream_BitstreamWriterPositionType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "bitstream.BitstreamWriterPosition",    /*tp_name*/
    sizeof(bitstream_BitstreamWriterPosition), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamWriterPosition_dealloc, /*tp_dealloc*/
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
    "BitstreamWriterPosition", /* tp_doc */
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
    (initproc)BitstreamWriterPosition_init, /* tp_init */
    0,                         /* tp_alloc */
    BitstreamWriterPosition_new, /* tp_new */
};

/*given a BitstreamReader, format string and list object
  parses the format from the reader and appends Python values to the list
  returns 0 on success, 1 on failure (with PyErr set)*/
int
bitstream_parse(BitstreamReader* stream,
                const char* format,
                PyObject* values);

/*given a BitstreamWriter, format string and PySequence of Python values,
  writes those values to the writer
  returns 0 on success, 1 on failure (with PyErr set)*/
int
bitstream_build(BitstreamWriter* stream,
                const char* format,
                PyObject* iterator);

void
BitstreamWriter_callback(uint8_t byte, PyObject *callback);

void
br_close_internal_stream_python_file(BitstreamReader* bs);

void
bw_close_internal_stream_python_file(BitstreamWriter* bs);
