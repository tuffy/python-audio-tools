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

PyObject*
encoders_encode_flac(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_shn(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_alac(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_encode_wavpack(PyObject *dummy, PyObject *args, PyObject *keywds);

PyObject*
encoders_format_size(PyObject *dummy, PyObject *args);

PyMethodDef module_methods[] = {
    {"encode_flac", (PyCFunction)encoders_encode_flac,
     METH_VARARGS | METH_KEYWORDS, "Encode FLAC file from PCMReader"},
    {"encode_shn", (PyCFunction)encoders_encode_shn,
     METH_VARARGS | METH_KEYWORDS, "Encode Shorten file from PCMReader"},
    {"encode_alac", (PyCFunction)encoders_encode_alac,
     METH_VARARGS | METH_KEYWORDS, "Encode ALAC file from PCMReader"},
    {"encode_wavpack", (PyCFunction)encoders_encode_wavpack,
     METH_VARARGS | METH_KEYWORDS, "Encode WavPack file from PCMReader"},
    {"format_size", (PyCFunction)encoders_format_size,
     METH_VARARGS, "Calculate size of format string"},
    {NULL}
};

typedef struct {
    PyObject_HEAD

    PyObject* file_obj;
    BitstreamWriter* bitstream;
} encoders_BitstreamWriter;

static PyObject*
BitstreamWriter_write(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_signed(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write64(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_write_signed64(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_unary(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_byte_align(encoders_BitstreamWriter *self, PyObject *args);

static PyObject*
BitstreamWriter_set_endianness(encoders_BitstreamWriter *self,
                               PyObject *args);

static PyObject*
BitstreamWriter_write_bytes(encoders_BitstreamWriter *self,
                            PyObject *args);

static PyObject*
BitstreamWriter_add_callback(encoders_BitstreamWriter *self,
                             PyObject *args);

static PyObject*
BitstreamWriter_pop_callback(encoders_BitstreamWriter *self,
                             PyObject *args);

static PyObject*
BitstreamWriter_build(encoders_BitstreamWriter *self, PyObject *args);

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
    {"write_signed64", (PyCFunction)BitstreamWriter_write_signed64,
     METH_VARARGS, ""},
    {"set_endianness", (PyCFunction)BitstreamWriter_set_endianness,
     METH_VARARGS, ""},
    {"write_bytes", (PyCFunction)BitstreamWriter_write_bytes,
     METH_VARARGS, ""},
    {"build", (PyCFunction)BitstreamWriter_build,
     METH_VARARGS, ""},
    {"add_callback", (PyCFunction)BitstreamWriter_add_callback,
     METH_VARARGS, ""},
    {"pop_callback", (PyCFunction)BitstreamWriter_pop_callback,
     METH_NOARGS, ""},
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
    "encoders.BitstreamWriter",    /*tp_name*/
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
} encoders_BitstreamRecorder;

static PyObject*
BitstreamRecorder_write(encoders_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_write_signed(encoders_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_write64(encoders_BitstreamRecorder *self,
                          PyObject *args);

static PyObject*
BitstreamRecorder_write_signed64(encoders_BitstreamRecorder *self,
                                 PyObject *args);

static PyObject*
BitstreamRecorder_unary(encoders_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_byte_align(encoders_BitstreamRecorder *self,
                             PyObject *args);

static PyObject*
BitstreamRecorder_set_endianness(encoders_BitstreamRecorder *self,
                                 PyObject *args);

static PyObject*
BitstreamRecorder_bits(encoders_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_bytes(encoders_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_swap(encoders_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_write_bytes(encoders_BitstreamRecorder *self,
                              PyObject *args);

static PyObject*
BitstreamRecorder_build(encoders_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_add_callback(encoders_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_pop_callback(encoders_BitstreamRecorder *self,
                               PyObject *args);

static PyObject*
BitstreamRecorder_reset(encoders_BitstreamRecorder *self,
                        PyObject *args);

/*returns the internal BitstreamWriter struct of the given object
  or NULL if it is not a BitstreamWriter/Recorder/Accumulator*/
static BitstreamWriter*
internal_writer(PyObject *writer);

static PyObject*
BitstreamRecorder_copy(encoders_BitstreamRecorder *self,
                       PyObject *args);

static PyObject*
BitstreamRecorder_split(encoders_BitstreamRecorder *self,
                        PyObject *args);

static PyObject*
BitstreamRecorder_close(encoders_BitstreamRecorder *self,
                        PyObject *args);

int
BitstreamRecorder_init(encoders_BitstreamRecorder *self,
                       PyObject *args);

PyMethodDef BitstreamRecorder_methods[] = {
    {"write", (PyCFunction)BitstreamRecorder_write,
     METH_VARARGS, ""},
    {"write_signed", (PyCFunction)BitstreamRecorder_write_signed,
     METH_VARARGS, ""},
    {"unary", (PyCFunction)BitstreamRecorder_unary,
     METH_VARARGS, ""},
    {"byte_align", (PyCFunction)BitstreamRecorder_byte_align,
     METH_NOARGS, ""},
    {"close", (PyCFunction)BitstreamRecorder_close,
     METH_NOARGS, ""},
    {"write64", (PyCFunction)BitstreamRecorder_write64,
     METH_VARARGS, ""},
    {"write_signed64", (PyCFunction)BitstreamRecorder_write_signed64,
     METH_VARARGS, ""},
    {"set_endianness", (PyCFunction)BitstreamRecorder_set_endianness,
     METH_VARARGS, ""},
    {"write_bytes", (PyCFunction)BitstreamRecorder_write_bytes,
     METH_VARARGS, ""},
    {"bits", (PyCFunction)BitstreamRecorder_bits,
     METH_NOARGS, ""},
    {"bytes", (PyCFunction)BitstreamRecorder_bytes,
     METH_NOARGS, ""},
    {"reset", (PyCFunction)BitstreamRecorder_reset,
     METH_NOARGS, ""},
    {"copy", (PyCFunction)BitstreamRecorder_copy,
     METH_VARARGS, ""},
    {"split", (PyCFunction)BitstreamRecorder_split,
     METH_VARARGS, ""},
    {"build", (PyCFunction)BitstreamRecorder_build,
     METH_VARARGS, ""},
    {"swap", (PyCFunction)BitstreamRecorder_swap,
     METH_VARARGS, ""},
    {"add_callback", (PyCFunction)BitstreamRecorder_add_callback,
     METH_VARARGS, ""},
    {"pop_callback", (PyCFunction)BitstreamRecorder_pop_callback,
     METH_NOARGS, ""},
    {NULL}
};

void
BitstreamRecorder_dealloc(encoders_BitstreamRecorder *self);

static PyObject*
BitstreamRecorder_new(PyTypeObject *type, PyObject *args,
                      PyObject *kwds);

PyTypeObject encoders_BitstreamRecorderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "encoders.BitstreamRecorder",    /*tp_name*/
    sizeof(encoders_BitstreamRecorder), /*tp_basicsize*/
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
} encoders_BitstreamAccumulator;

static PyObject*
BitstreamAccumulator_write(encoders_BitstreamAccumulator *self,
                           PyObject *args);

static PyObject*
BitstreamAccumulator_write_signed(encoders_BitstreamAccumulator *self,
                                  PyObject *args);

static PyObject*
BitstreamAccumulator_write64(encoders_BitstreamAccumulator *self,
                             PyObject *args);

static PyObject*
BitstreamAccumulator_write_signed64(encoders_BitstreamAccumulator *self,
                                    PyObject *args);

static PyObject*
BitstreamAccumulator_unary(encoders_BitstreamAccumulator *self,
                           PyObject *args);

static PyObject*
BitstreamAccumulator_byte_align(encoders_BitstreamAccumulator *self,
                                PyObject *args);

static PyObject*
BitstreamAccumulator_set_endianness(encoders_BitstreamAccumulator *self,
                                    PyObject *args);

static PyObject*
BitstreamAccumulator_write_bytes(encoders_BitstreamAccumulator *self,
                                 PyObject *args);

static PyObject*
BitstreamAccumulator_build(encoders_BitstreamAccumulator *self, PyObject *args);

static PyObject*
BitstreamAccumulator_close(encoders_BitstreamAccumulator *self, PyObject *args);

int
BitstreamAccumulator_init(encoders_BitstreamAccumulator *self, PyObject *args);

static PyObject*
BitstreamAccumulator_bits(encoders_BitstreamAccumulator *self,
                          PyObject *args);

static PyObject*
BitstreamAccumulator_bytes(encoders_BitstreamAccumulator *self,
                           PyObject *args);


PyMethodDef BitstreamAccumulator_methods[] = {
    {"write", (PyCFunction)BitstreamAccumulator_write,
     METH_VARARGS, ""},
    {"write_signed", (PyCFunction)BitstreamAccumulator_write_signed,
     METH_VARARGS, ""},
    {"unary", (PyCFunction)BitstreamAccumulator_unary,
     METH_VARARGS, ""},
    {"byte_align", (PyCFunction)BitstreamAccumulator_byte_align,
     METH_NOARGS, ""},
    {"close", (PyCFunction)BitstreamAccumulator_close,
     METH_NOARGS, ""},
    {"write64", (PyCFunction)BitstreamAccumulator_write64,
     METH_VARARGS, ""},
    {"write_signed64", (PyCFunction)BitstreamAccumulator_write_signed64,
     METH_VARARGS, ""},
    {"set_endianness", (PyCFunction)BitstreamAccumulator_set_endianness,
     METH_VARARGS, ""},
    {"write_bytes", (PyCFunction)BitstreamAccumulator_write_bytes,
     METH_VARARGS, ""},
    {"build", (PyCFunction)BitstreamAccumulator_build,
     METH_VARARGS, ""},
    {"bits", (PyCFunction)BitstreamAccumulator_bits,
     METH_NOARGS, ""},
    {"bytes", (PyCFunction)BitstreamAccumulator_bytes,
     METH_NOARGS, ""},
    {NULL}
};

void
BitstreamAccumulator_dealloc(encoders_BitstreamAccumulator *self);

static PyObject*
BitstreamAccumulator_new(PyTypeObject *type, PyObject *args,
                         PyObject *kwds);

PyTypeObject encoders_BitstreamAccumulatorType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "encoders.BitstreamAccumulator",    /*tp_name*/
    sizeof(encoders_BitstreamAccumulator), /*tp_basicsize*/
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
