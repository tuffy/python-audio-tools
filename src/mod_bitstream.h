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

static PyObject*
BitstreamReader_Substream(PyObject *dummy, PyObject *args);

PyObject*
bitstream_format_size(PyObject *dummy, PyObject *args);

PyMethodDef module_methods[] = {
    {"Substream", (PyCFunction)BitstreamReader_Substream,
     METH_VARARGS, "build a fresh Substream BitstreamReader"}, /*FIXME*/
    {"format_size", (PyCFunction)bitstream_format_size,
     METH_VARARGS, "Calculate size of format string"}, /*FIXME*/
    {NULL}
};

/*the BitstreamReader object
  a simple wrapper around our Bitstream reading struct*/

typedef struct {
    PyObject_HEAD

    PyObject* file_obj;
    BitstreamReader* bitstream;
    int little_endian;
} bitstream_BitstreamReader;

static PyObject*
BitstreamReader_read(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read64(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_byte_align(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_skip(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_skip_bytes(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unread(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read_signed(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_read_signed64(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unary(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_limited_unary(bitstream_BitstreamReader *self, PyObject *args);

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
BitstreamReader_mark(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_rewind(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_unmark(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_add_callback(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_pop_callback(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_call_callbacks(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_substream(bitstream_BitstreamReader *self, PyObject *args);

static PyObject*
BitstreamReader_substream_append(bitstream_BitstreamReader *self,
                                 PyObject *args);

static PyObject*
BitstreamReader_parse(bitstream_BitstreamReader *self, PyObject *args);

int
BitstreamReader_init(bitstream_BitstreamReader *self, PyObject *args);

PyMethodDef BitstreamReader_methods[] = {
    {"read", (PyCFunction)BitstreamReader_read, METH_VARARGS,
     "read(bits) -> unsigned int\n"
     "where bits <= 32"},
    {"read64", (PyCFunction)BitstreamReader_read64, METH_VARARGS,
     "read64(bits) -> unsigned long\n"
     "where bits may be greater than 32"},
    {"skip", (PyCFunction)BitstreamReader_skip, METH_VARARGS,
     "skip(bits)\n"
     "skips over the given number of bits"},
    {"skip_bytes", (PyCFunction)BitstreamReader_skip_bytes, METH_VARARGS,
     "skip_bytes(bytes)\n"
     "skips over the given number of bytes"},
    {"byte_align", (PyCFunction)BitstreamReader_byte_align, METH_NOARGS,
     "byte_align()\n"
     "moves to the next whole byte boundary, if necessary"},
    {"unread", (PyCFunction)BitstreamReader_unread, METH_VARARGS,
     "unread(bit)\n"
     "pushes a single bit back into the stream"},
    {"read_signed", (PyCFunction)BitstreamReader_read_signed, METH_VARARGS,
     "read_signed(bits) -> signed int\n"
     "where bits <= 32"},
    {"read_signed64", (PyCFunction)BitstreamReader_read_signed64, METH_VARARGS,
     "read_signed64(bits) -> signed long\n"
     "where bits may be greater than 32"},
    {"unary", (PyCFunction)BitstreamReader_unary, METH_VARARGS,
     "unary(stop_bit) -> unsigned int\n"
     "counts the number of bits until the next stop bit"},
    {"limited_unary", (PyCFunction)BitstreamReader_limited_unary, METH_VARARGS,
     "limited_unary(stop_bit, maximum_bits) -> signed int\n"
     "counts the number of bits until the next stop bit\n"
     "or returns -1 if the maximum bits are exceeded"},
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
     "\"#U\" -> read64(#)\n"
     "\"#S\" -> read_signed64(#)\n"
     "\"#p\" -> skip(#)\n"
     "\"#P\" -> skip_bytes(#)\n"
     "\"#b\" -> read_bytes(#)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "r.parse(\"3u 4s 36U\") == [r.read(3), r.read_signed(4), r.read64(36)]"},
    {"close", (PyCFunction)BitstreamReader_close, METH_NOARGS,
     "close()\n"
     "closes the stream and any underlying file object"},
    {"mark", (PyCFunction)BitstreamReader_mark, METH_NOARGS,
     "mark()\n"
     "pushes the current position onto a stack\n"
     "which may be returned to with calls to rewind()\n"
     "all marked positions should be unmarked when no longer needed"},
    {"rewind", (PyCFunction)BitstreamReader_rewind, METH_NOARGS,
     "rewind()\n"
     "returns to the most recently marked position in the stream"},
    {"unmark", (PyCFunction)BitstreamReader_unmark, METH_NOARGS,
     "unmark()\n"
     "removes the most recently marked position from the stream"},
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
    {"substream_append", (PyCFunction)BitstreamReader_substream_append,
     METH_VARARGS,
     "substream_append(BitstreamReader, bytes)\n"
     "appends an additional number of bytes to the given substream"},
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
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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

    struct br_huffman_table (*table)[][0x200];
} bitstream_HuffmanTree;

int
HuffmanTree_init(bitstream_HuffmanTree *self, PyObject *args);

void
HuffmanTree_dealloc(bitstream_HuffmanTree *self);

static PyObject*
HuffmanTree_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

PyTypeObject bitstream_HuffmanTreeType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "bitstream.HuffmanTree",    /*tp_name*/
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

PyObject*
bitstream_format_size(PyObject *dummy, PyObject *args) {
    char* format_string;

    if (!PyArg_ParseTuple(args, "s", &format_string))
        return NULL;

    return Py_BuildValue("I", bs_format_size(format_string));
}

typedef struct {
    PyObject_HEAD

    PyObject* file_obj;
    BitstreamWriter* bitstream;
} bitstream_BitstreamWriter;

static PyObject*
BitstreamWriter_write(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_signed(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write64(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_signed64(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_unary(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_byte_align(bitstream_BitstreamWriter *self, PyObject *args);

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
BitstreamWriter_build(bitstream_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_close(bitstream_BitstreamWriter *self, PyObject *args);

int
BitstreamWriter_init(bitstream_BitstreamWriter *self, PyObject *args);

PyMethodDef BitstreamWriter_methods[] = {
    {"write", (PyCFunction)BitstreamWriter_write, METH_VARARGS,
     "write(bits, unsigned int)\n"
     "where bits <= 32"},
    {"write_signed", (PyCFunction)BitstreamWriter_write_signed, METH_VARARGS,
     "write_signed(bits, signed int)\n"
     "where bits <= 32"},
    {"unary", (PyCFunction)BitstreamWriter_unary, METH_VARARGS,
     "unary(stop_bit, unsigned int)\n"
     "where \"stop_bit\" must be 0 or 1\n"
     "writes value as the given number of not stop_bit values (1 or 0)\n"
     "followed by a stop_bit"},
    {"byte_align", (PyCFunction)BitstreamWriter_byte_align, METH_NOARGS,
     "byte_align()\n"
     "pads the stream with 0 bits until the next whole byte"},
    {"close", (PyCFunction)BitstreamWriter_close, METH_NOARGS,
     "close()\n"
     "closes the stream and any underlying file object"},
    {"write64", (PyCFunction)BitstreamWriter_write64, METH_VARARGS,
     "write64(bits, unsigned long)\n"
     "where bits may be greater than 32"},
    {"write_signed64", (PyCFunction)BitstreamWriter_write_signed64,
     METH_VARARGS,
     "write_signed64(bits, signed long)\n"
     "where bits may be greater than 32"},
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
     "\"#U\" -> write64(#, unsigned long value)\n"
     "\"#S\" -> write_signed64(#, signed long value)\n"
     "\"#p\" -> write(#, 0)\n"
     "\"#P\" -> write(# * 8, 0)\n"
     "\"#b\" -> write_bytes(#, string value)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "w.build(\"3u 4s 36U\", [1, -2, 3L])\n   ==\n"
     "w.write(3, 1); w.write_signed(4, -2); w.write64(36, 3L)"},
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
    {NULL}
};

void
BitstreamWriter_dealloc(bitstream_BitstreamWriter *self);

static PyObject*
BitstreamWriter_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds);

PyTypeObject bitstream_BitstreamWriterType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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

    BitstreamWriter* bitstream;
} bitstream_BitstreamRecorder;

static PyObject*
BitstreamRecorder_write(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_write_signed(bitstream_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_write64(bitstream_BitstreamRecorder *self,
                          PyObject *args);

static PyObject*
BitstreamRecorder_write_signed64(bitstream_BitstreamRecorder *self,
                                 PyObject *args);

static PyObject*
BitstreamRecorder_unary(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_byte_align(bitstream_BitstreamRecorder *self,
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
BitstreamRecorder_reset(bitstream_BitstreamRecorder *self,
                        PyObject *args);

/*returns the internal BitstreamWriter struct of the given object
  or NULL if it is not a BitstreamWriter/Recorder/Accumulator*/
static BitstreamWriter*
internal_writer(PyObject *writer);

static PyObject*
BitstreamRecorder_copy(bitstream_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_split(bitstream_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_close(bitstream_BitstreamRecorder *self,
                        PyObject *args);

int
BitstreamRecorder_init(bitstream_BitstreamRecorder *self,
                       PyObject *args);

PyMethodDef BitstreamRecorder_methods[] = {
    {"write", (PyCFunction)BitstreamRecorder_write, METH_VARARGS,
     "write(bits, unsigned int)\n"
     "where bits <= 32"},
    {"write_signed", (PyCFunction)BitstreamRecorder_write_signed, METH_VARARGS,
     "write_signed(bits, signed int)\n"
     "where bits <= 32"},
    {"unary", (PyCFunction)BitstreamRecorder_unary, METH_VARARGS,
     "unary(stop_bit, unsigned int)\n"
     "where \"stop_bit\" must be 0 or 1\n"
     "writes value as the given number of not stop_bit values (1 or 0)\n"
     "followed by a stop_bit"},
    {"byte_align", (PyCFunction)BitstreamRecorder_byte_align, METH_NOARGS,
     "byte_align()\n"
     "pads the stream with 0 bits until the next whole byte"},
    {"close", (PyCFunction)BitstreamRecorder_close, METH_NOARGS,
    "close()\n"},
    {"write64", (PyCFunction)BitstreamRecorder_write64, METH_VARARGS,
     "write64(bits, unsigned long)\n"
     "where bits may be greater than 32"},
    {"write_signed64", (PyCFunction)BitstreamRecorder_write_signed64,
     METH_VARARGS,
     "write_signed64(bits, signed long)\n"
     "where bits may be greater than 32"},
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
     "returns the written data is a string"},
    {"reset", (PyCFunction)BitstreamRecorder_reset, METH_NOARGS,
     "reset()\n"
     "removes all written data and resets the stream for new data"},
    {"copy", (PyCFunction)BitstreamRecorder_copy, METH_VARARGS,
     "copy(target)\n"
     "copies the written data to \"target\", which must be a\n"
     "BitstreamWriter, Recorder or Accumulator"},
    {"split", (PyCFunction)BitstreamRecorder_split, METH_VARARGS,
     "split(target, remainder, bytes)\n"
     "copies the given number of written bytes to \"target\"\n"
     "and the remaining bytes to \"remainder\"\n"
     "where \"target\" and \"remainder\" must be a\n"
     "BitstreamWriter, Recorder, Accumulator or None"},
    {"build", (PyCFunction)BitstreamRecorder_build, METH_VARARGS,
     "build(format_string, [value1, value2, ...])\n"
     "where \"format_string\" maps to the calls:\n"
     "\"#u\" -> write(#, unsigned int value)\n"
     "\"#s\" -> write_signed(#, signed int value)\n"
     "\"#U\" -> write64(#, unsigned long value)\n"
     "\"#S\" -> write_signed64(#, signed long value)\n"
     "\"#p\" -> write(#, 0)\n"
     "\"#P\" -> write(# * 8, 0)\n"
     "\"#b\" -> write_bytes(#, string value)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "r.build(\"3u 4s 36U\", [1, -2, 3L])\n   ==\n"
     "r.write(3, 1); r.write_signed(4, -2); r.write64(36, 3L)"},
    {"swap", (PyCFunction)BitstreamRecorder_swap, METH_VARARGS,
     "swap(recorder)\n"
     "swaps our written data with that of another BitstreamRecorder"},
    {"add_callback", (PyCFunction)BitstreamRecorder_add_callback, METH_VARARGS,
     "add_callback(function)\n"
     "where \"function\" takes a single byte as an argument\n"
     "and is called upon each written byte to the stream"},
    {"pop_callback", (PyCFunction)BitstreamRecorder_pop_callback, METH_NOARGS,
     "pop_callback() -> function\n"
     "removes and returns the most recently added callback"},
    {"call_callbacks", (PyCFunction)BitstreamRecorder_call_callbacks,
     METH_VARARGS,
     "call_callbacks(byte)\n"
     "calls the attached callbacks as if the byte had been written"},
    {NULL}
};

void
BitstreamRecorder_dealloc(bitstream_BitstreamRecorder *self);

static PyObject*
BitstreamRecorder_new(PyTypeObject *type, PyObject *args,
                      PyObject *kwds);

PyTypeObject bitstream_BitstreamRecorderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
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

int
bitstream_build(BitstreamWriter* stream, char* format, PyObject* values);

typedef struct {
    PyObject_HEAD

    BitstreamWriter* bitstream;
} bitstream_BitstreamAccumulator;

static PyObject*
BitstreamAccumulator_write(bitstream_BitstreamAccumulator *self,
                           PyObject *args);

static PyObject*
BitstreamAccumulator_write_signed(bitstream_BitstreamAccumulator *self,
                                  PyObject *args);

static PyObject*
BitstreamAccumulator_write64(bitstream_BitstreamAccumulator *self,
                             PyObject *args);

static PyObject*
BitstreamAccumulator_write_signed64(bitstream_BitstreamAccumulator *self,
                                    PyObject *args);

static PyObject*
BitstreamAccumulator_unary(bitstream_BitstreamAccumulator *self,
                           PyObject *args);

static PyObject*
BitstreamAccumulator_byte_align(bitstream_BitstreamAccumulator *self,
                                PyObject *args);

static PyObject*
BitstreamAccumulator_set_endianness(bitstream_BitstreamAccumulator *self,
                                    PyObject *args);

static PyObject*
BitstreamAccumulator_write_bytes(bitstream_BitstreamAccumulator *self,
                                 PyObject *args);

static PyObject*
BitstreamAccumulator_build(bitstream_BitstreamAccumulator *self, PyObject *args);

static PyObject*
BitstreamAccumulator_close(bitstream_BitstreamAccumulator *self, PyObject *args);

int
BitstreamAccumulator_init(bitstream_BitstreamAccumulator *self, PyObject *args);

static PyObject*
BitstreamAccumulator_bits(bitstream_BitstreamAccumulator *self,
                          PyObject *args);

static PyObject*
BitstreamAccumulator_bytes(bitstream_BitstreamAccumulator *self,
                           PyObject *args);


PyMethodDef BitstreamAccumulator_methods[] = {
    {"write", (PyCFunction)BitstreamAccumulator_write, METH_VARARGS,
     "write(bits, unsigned int)\n"
     "where bits <= 32"},
    {"write_signed", (PyCFunction)BitstreamAccumulator_write_signed,
     METH_VARARGS,
    "write_signed(bits, signed int)\n"
     "where bits <= 32"},
    {"unary", (PyCFunction)BitstreamAccumulator_unary, METH_VARARGS,
     "unary(stop_bit, unsigned int)\n"
     "where \"stop_bit\" must be 0 or 1\n"
     "writes value as the given number of not stop_bit values (1 or 0)\n"
     "followed by a stop_bit"},
    {"byte_align", (PyCFunction)BitstreamAccumulator_byte_align, METH_NOARGS,
     "byte_align()\n"
     "pads the stream with 0 bits until the next whole byte"},
    {"close", (PyCFunction)BitstreamAccumulator_close, METH_NOARGS,
     "close()\n"
     "closes the stream and any underlying file object"},
    {"write64", (PyCFunction)BitstreamAccumulator_write64, METH_VARARGS,
     "write64(bits, unsigned long)\n"
     "where bits may be greater than 32"},
    {"write_signed64", (PyCFunction)BitstreamAccumulator_write_signed64,
     METH_VARARGS,
     "write_signed64(bits, signed long)\n"
     "where bits may be greater than 32"},
    {"set_endianness", (PyCFunction)BitstreamAccumulator_set_endianness,
     METH_VARARGS,
     "set_endianness(endianness)\n"
     "where 0 = big endian, 1 = little endian"},
    {"write_bytes", (PyCFunction)BitstreamAccumulator_write_bytes, METH_VARARGS,
     "write_bytes(bytes, string)"},
    {"build", (PyCFunction)BitstreamAccumulator_build, METH_VARARGS,
     "build(format_string, [value1, value2, ...])\n"
     "where \"format_string\" maps to the calls:\n"
     "\"#u\" -> write(#, unsigned int value)\n"
     "\"#s\" -> write_signed(#, signed int value)\n"
     "\"#U\" -> write64(#, unsigned long value)\n"
     "\"#S\" -> write_signed64(#, signed long value)\n"
     "\"#p\" -> write(#, 0)\n"
     "\"#P\" -> write(# * 8, 0)\n"
     "\"#b\" -> write_bytes(#, string value)\n"
     "\"a\"  -> byte_align()\n\n"
     "for instance:\n"
     "a.build(\"3u 4s 36U\", [1, -2, 3L])\n   ==\n"
     "a.write(3, 1); a.write_signed(4, -2); a.write64(36, 3L)"},
    {"bits", (PyCFunction)BitstreamAccumulator_bits, METH_NOARGS,
     "bits() -> unsigned int\n"
     "returns the total number of bits written thus far"},
    {"bytes", (PyCFunction)BitstreamAccumulator_bytes, METH_NOARGS,
     "bytes() -> unsigned int\n"
     "returns the total number of bytes written thus far"},
    {NULL}
};

void
BitstreamAccumulator_dealloc(bitstream_BitstreamAccumulator *self);

static PyObject*
BitstreamAccumulator_new(PyTypeObject *type, PyObject *args,
                         PyObject *kwds);

PyTypeObject bitstream_BitstreamAccumulatorType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "bitstream.BitstreamAccumulator",    /*tp_name*/
    sizeof(bitstream_BitstreamAccumulator), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitstreamAccumulator_dealloc, /*tp_dealloc*/
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
    "BitstreamAccumulator objects", /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /*  tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    BitstreamAccumulator_methods,   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)BitstreamAccumulator_init,/* tp_init */
    0,                         /* tp_alloc */
    BitstreamAccumulator_new,  /* tp_new */
};

void
BitstreamWriter_callback(uint8_t byte, PyObject *callback);
