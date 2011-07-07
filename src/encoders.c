#include <Python.h>
#include "bitstream.h"
#include "encoders.h"

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

PyMODINIT_FUNC
initencoders(void)
{
    PyObject* m;

    encoders_BitstreamWriterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&encoders_BitstreamWriterType) < 0)
        return;

    encoders_BitstreamRecorderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&encoders_BitstreamRecorderType) < 0)
        return;

    encoders_BitstreamAccumulatorType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&encoders_BitstreamAccumulatorType) < 0)
        return;

    m = Py_InitModule3("encoders", module_methods,
                       "Low-level audio format encoders");

    Py_INCREF(&encoders_BitstreamWriterType);
    PyModule_AddObject(m, "BitstreamWriter",
                       (PyObject *)&encoders_BitstreamWriterType);

    Py_INCREF(&encoders_BitstreamRecorderType);
    PyModule_AddObject(m, "BitstreamRecorder",
                       (PyObject *)&encoders_BitstreamRecorderType);

    Py_INCREF(&encoders_BitstreamAccumulatorType);
    PyModule_AddObject(m, "BitstreamAccumulator",
                       (PyObject *)&encoders_BitstreamAccumulatorType);
}

int
BitstreamWriter_init(encoders_BitstreamWriter *self, PyObject *args) {
    PyObject *file_obj;
    int little_endian;

    self->file_obj = NULL;

    if (!PyArg_ParseTuple(args, "Oi", &file_obj, &little_endian))
        return -1;

    if (!PyFile_CheckExact(file_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be an actual file object");
        return -1;
    }

    Py_INCREF(file_obj);
    self->file_obj = file_obj;

    self->bitstream = bw_open(PyFile_AsFile(self->file_obj),
                              little_endian ?
                              BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    return 0;
}

void
BitstreamWriter_dealloc(encoders_BitstreamWriter *self) {
    if (self->file_obj != NULL) {
        self->bitstream->output.file = NULL;
        bw_free(self->bitstream);
        Py_DECREF(self->file_obj);
    }

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
BitstreamWriter_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds) {
    encoders_BitstreamWriter *self;

    self = (encoders_BitstreamWriter *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
BitstreamWriter_write(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "II", &count, &value))
        return NULL;

    self->bitstream->write(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write_signed(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    self->bitstream->write_signed(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write64(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IK", &count, &value))
        return NULL;

    self->bitstream->write_64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write_signed64(encoders_BitstreamWriter *self, PyObject *args) {
    unsigned int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    self->bitstream->write_signed_64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_unary(encoders_BitstreamWriter *self, PyObject *args) {
    int stop_bit;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    self->bitstream->write_unary(self->bitstream, stop_bit, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_byte_align(encoders_BitstreamWriter *self, PyObject *args) {
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_set_endianness(encoders_BitstreamWriter *self,
                               PyObject *args) {
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    if ((little_endian != 0) && (little_endian != 1)) {
        PyErr_SetString(PyExc_ValueError,
                    "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }

    self->bitstream->set_endianness(
                    self->bitstream,
                    little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write_bytes(encoders_BitstreamWriter *self,
                            PyObject *args) {
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    self->bitstream->write_bytes(self->bitstream, (uint8_t*)bytes, bytes_len);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_build(encoders_BitstreamWriter *self, PyObject *args) {
    char* format;
    PyObject *values;

    if (!PyArg_ParseTuple(args, "sO", &format, &values))
        return NULL;

    if (bitstream_build(self->bitstream, format, values)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamWriter_add_callback(encoders_BitstreamWriter *self,
                             PyObject *args) {
    PyObject* callback;

    if (!PyArg_ParseTuple(args, "O", &callback))
        return NULL;

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
        return NULL;
    }

    Py_INCREF(callback);
    bw_add_callback(self->bitstream,
                    (bs_callback_func)BitstreamWriter_callback,
                    callback);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_pop_callback(encoders_BitstreamWriter *self,
                             PyObject *args) {
    struct bs_callback callback;
    PyObject* callback_obj;

    if (self->bitstream->callbacks != NULL) {
        bw_pop_callback(self->bitstream, &callback);
        callback_obj = callback.data;
        /*decref object from stack and then incref object for return
          should have a net effect of noop*/
        return callback_obj;
    } else {
        PyErr_SetString(PyExc_IndexError, "no callbacks to pop");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_close(encoders_BitstreamWriter *self, PyObject *args) {
    self->bitstream->flush(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    unsigned int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "II", &count, &value))
        return NULL;

    self->bitstream->write(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write_signed(encoders_BitstreamRecorder *self,
                               PyObject *args) {
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    self->bitstream->write_signed(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write64(encoders_BitstreamRecorder *self,
                          PyObject *args) {
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IK", &count, &value))
        return NULL;

    self->bitstream->write_64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write_signed64(encoders_BitstreamRecorder *self,
                                 PyObject *args) {
    unsigned int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    self->bitstream->write_signed_64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_unary(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    int stop_bit;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    self->bitstream->write_unary(self->bitstream, stop_bit, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_byte_align(encoders_BitstreamRecorder *self,
                             PyObject *args) {
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_set_endianness(encoders_BitstreamRecorder *self,
                                 PyObject *args) {
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    if ((little_endian != 0) && (little_endian != 1)) {
        PyErr_SetString(PyExc_ValueError,
                    "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }

    self->bitstream->set_endianness(
                    self->bitstream,
                    little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_bits(encoders_BitstreamRecorder *self,
                       PyObject *args) {
    return Py_BuildValue("I", self->bitstream->bits_written(self->bitstream));
}

static PyObject*
BitstreamRecorder_bytes(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    return Py_BuildValue("I",
                         self->bitstream->bits_written(self->bitstream) / 8);
}

static PyObject*
BitstreamRecorder_swap(encoders_BitstreamRecorder *self,
                       PyObject *args) {
    encoders_BitstreamRecorder *to_swap;

    if (!PyArg_ParseTuple(args, "O!",
                          &encoders_BitstreamRecorderType, &to_swap))
        return NULL;

    bw_swap_records(self->bitstream, to_swap->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write_bytes(encoders_BitstreamRecorder *self,
                              PyObject *args) {
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    self->bitstream->write_bytes(self->bitstream, (uint8_t*)bytes, bytes_len);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_build(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    char* format;
    PyObject *values;

    if (!PyArg_ParseTuple(args, "sO", &format, &values))
        return NULL;

    if (bitstream_build(self->bitstream, format, values)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamRecorder_reset(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    bw_reset_recorder(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static BitstreamWriter*
internal_writer(PyObject *writer) {
    encoders_BitstreamWriter* writer_obj;
    encoders_BitstreamRecorder* recorder_obj;
    encoders_BitstreamAccumulator* accumulator_obj;

    if (writer->ob_type == &encoders_BitstreamWriterType) {
        writer_obj = (encoders_BitstreamWriter*)writer;
        return writer_obj->bitstream;
    } else if (writer->ob_type == &encoders_BitstreamRecorderType) {
        recorder_obj = (encoders_BitstreamRecorder*)writer;
        return recorder_obj->bitstream;
    } else if (writer->ob_type == &encoders_BitstreamAccumulatorType) {
        accumulator_obj = (encoders_BitstreamAccumulator*)writer;
        return accumulator_obj->bitstream;
    } else {
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_copy(encoders_BitstreamRecorder *self,
                       PyObject *args) {
    PyObject* bitstreamwriter_obj;
    BitstreamWriter* target;

    if (!PyArg_ParseTuple(args, "O", &bitstreamwriter_obj))
        return NULL;

    if ((target = internal_writer(bitstreamwriter_obj)) != NULL) {
        bw_rec_copy(target, self->bitstream);

        Py_INCREF(Py_None);
        return Py_None;
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "argument must be a "
                        "BitstreamWriter, BitstreamRecorder "
                        "or BitstreamAccumulator");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_split(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    PyObject* target_obj;
    PyObject* remainder_obj;
    BitstreamWriter* target;
    BitstreamWriter* remainder;
    unsigned int total_bytes;

    if (!PyArg_ParseTuple(args, "OOI",
                          &target_obj, &remainder_obj, &total_bytes))
        return NULL;

    if (target_obj == Py_None) {
        target = NULL;
    } else if ((target = internal_writer(target_obj)) == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "target argument must be None, a "
                        "BitstreamWriter, BitstreamRecorder "
                        "or BitstreamAccumulator");
        return NULL;
    }

    if (remainder_obj == Py_None) {
        remainder = NULL;
    } else if ((remainder = internal_writer(remainder_obj)) == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "remainder argument must be None, a "
                        "BitstreamWriter, BitstreamRecorder "
                        "or BitstreamAccumulator");
        return NULL;
    }

    return Py_BuildValue("I", bw_rec_split(target,
                                           remainder,
                                           self->bitstream,
                                           total_bytes));
}

static PyObject*
BitstreamRecorder_add_callback(encoders_BitstreamRecorder *self,
                               PyObject *args) {
    PyObject* callback;

    if (!PyArg_ParseTuple(args, "O", &callback))
        return NULL;

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
        return NULL;
    }

    Py_INCREF(callback);
    bw_add_callback(self->bitstream,
                    (bs_callback_func)BitstreamWriter_callback,
                    callback);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_pop_callback(encoders_BitstreamRecorder *self,
                               PyObject *args) {
    struct bs_callback callback;
    PyObject* callback_obj;

    if (self->bitstream->callbacks != NULL) {
        bw_pop_callback(self->bitstream, &callback);
        callback_obj = callback.data;
        /*decref object from stack and then incref object for return
          should have a net effect of noop*/
        return callback_obj;
    } else {
        PyErr_SetString(PyExc_IndexError, "no callbacks to pop");
        return NULL;
    }
}


static PyObject*
BitstreamRecorder_close(encoders_BitstreamRecorder *self,
                        PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

int
BitstreamRecorder_init(encoders_BitstreamRecorder *self,
                       PyObject *args) {
    int little_endian;

    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return -1;

    self->bitstream = bw_open_recorder(little_endian ?
                                       BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    return 0;
}

void
BitstreamRecorder_dealloc(encoders_BitstreamRecorder *self) {
    if (self->bitstream != NULL)
        self->bitstream->close(self->bitstream);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
BitstreamRecorder_new(PyTypeObject *type, PyObject *args,
                      PyObject *kwds) {
    encoders_BitstreamRecorder *self;

    self = (encoders_BitstreamRecorder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
bitstream_build(BitstreamWriter* stream, char* format, PyObject* values) {
    Py_ssize_t i = 0;
    PyObject *value = NULL;
    unsigned int size;
    bs_instruction type;
    unsigned int _unsigned;
    int _signed;
    uint64_t _unsigned64;
    int64_t _signed64;
    uint8_t* _bytes;
    Py_ssize_t bytes_len;

    while (!bs_parse_format(&format, &size, &type)) {
        switch (type) {
        case BS_INST_UNSIGNED:
            if ((value = PySequence_GetItem(values, i++)) != NULL) {
                _unsigned = PyInt_AsUnsignedLongMask(value);
                if (!PyErr_Occurred())
                    stream->write(stream, size, _unsigned);
                else
                    return 1;
            } else {
                return 1;
            }
            break;
        case BS_INST_SIGNED:
            if ((value = PySequence_GetItem(values, i++)) != NULL) {
                _signed = PyInt_AsLong(value);
                if (!PyErr_Occurred())
                    stream->write_signed(stream, size, _signed);
                else
                    return 1;
            } else {
                return 1;
            }
            break;
        case BS_INST_UNSIGNED64:
            if ((value = PySequence_GetItem(values, i++)) != NULL) {
                _unsigned64 = PyInt_AsUnsignedLongLongMask(value);
                if (!PyErr_Occurred())
                    stream->write_64(stream, size, _unsigned64);
                else
                    return 1;
            } else {
                return 1;
            }
            break;
        case BS_INST_SIGNED64:
            if ((value = PySequence_GetItem(values, i++)) != NULL) {
                _signed64 = PyLong_AsLongLong(value);
                if (!PyErr_Occurred())
                    stream->write_signed_64(stream, size, _signed64);
                else
                    return 1;
            } else {
                return 1;
            }
            break;
        case BS_INST_SKIP:
            stream->write(stream, size, 0);
            break;
        case BS_INST_BYTES:
            if (((value = PySequence_GetItem(values, i++)) != NULL) &&
                (PyString_AsStringAndSize(value,
                                          (char **)(&_bytes),
                                          &bytes_len) != -1)) {
                if (size <= bytes_len) {
                    stream->write_bytes(stream, _bytes, size);
                } else {
                    PyErr_SetString(PyExc_ValueError,
                                    "string length too short");
                    return 1;
                }
            } else {
                return 1;
            }
            break;
        case BS_INST_ALIGN:
            stream->byte_align(stream);
            break;
        }
    }

    return 0;
}

PyObject*
encoders_format_size(PyObject *dummy, PyObject *args) {
    char* format_string;

    if (!PyArg_ParseTuple(args, "s", &format_string))
        return NULL;

    return Py_BuildValue("I", bs_format_size(format_string));
}

int
BitstreamAccumulator_init(encoders_BitstreamAccumulator *self, PyObject *args) {
    int little_endian;

    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return -1;

    self->bitstream = bw_open_accumulator(little_endian ?
                                          BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    return 0;
}

void
BitstreamAccumulator_dealloc(encoders_BitstreamAccumulator *self) {
    if (self->bitstream != NULL)
        self->bitstream->close(self->bitstream);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
BitstreamAccumulator_new(PyTypeObject *type, PyObject *args,
                         PyObject *kwds) {
    encoders_BitstreamAccumulator *self;

    self = (encoders_BitstreamAccumulator *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
BitstreamAccumulator_close(encoders_BitstreamAccumulator *self,
                           PyObject *args) {
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write(encoders_BitstreamAccumulator *self,
                           PyObject *args) {
    unsigned int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "II", &count, &value))
        return NULL;

    self->bitstream->write(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write_signed(encoders_BitstreamAccumulator *self,
                                  PyObject *args) {
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    self->bitstream->write_signed(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write64(encoders_BitstreamAccumulator *self,
                             PyObject *args) {
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IK", &count, &value))
        return NULL;

    self->bitstream->write_64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write_signed64(encoders_BitstreamAccumulator *self,
                                    PyObject *args) {
    unsigned int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    self->bitstream->write_signed_64(self->bitstream, count, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_unary(encoders_BitstreamAccumulator *self,
                           PyObject *args) {
    int stop_bit;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    self->bitstream->write_unary(self->bitstream, stop_bit, value);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_byte_align(encoders_BitstreamAccumulator *self,
                                PyObject *args) {
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_set_endianness(encoders_BitstreamAccumulator *self,
                                    PyObject *args) {
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    if ((little_endian != 0) && (little_endian != 1)) {
        PyErr_SetString(PyExc_ValueError,
                    "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }

    self->bitstream->set_endianness(
                    self->bitstream,
                    little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write_bytes(encoders_BitstreamAccumulator *self,
                                 PyObject *args) {
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    self->bitstream->write_bytes(self->bitstream, (uint8_t*)bytes, bytes_len);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_build(encoders_BitstreamAccumulator *self,
                           PyObject *args) {
    char* format;
    PyObject *values;

    if (!PyArg_ParseTuple(args, "sO", &format, &values))
        return NULL;

    if (bitstream_build(self->bitstream, format, values)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamAccumulator_bits(encoders_BitstreamAccumulator *self,
                          PyObject *args) {
    return Py_BuildValue("I", self->bitstream->bits_written(self->bitstream));
}

static PyObject*
BitstreamAccumulator_bytes(encoders_BitstreamAccumulator *self,
                          PyObject *args) {
    return Py_BuildValue("I",
                         self->bitstream->bits_written(self->bitstream) / 8);
}

void
BitstreamWriter_callback(uint8_t byte, PyObject *callback)
{
    PyObject* result = PyObject_CallFunction(callback, "B", byte);

    if (result != NULL) {
        Py_DECREF(result);
    } else {
        PyErr_PrintEx(0);
    }
}
