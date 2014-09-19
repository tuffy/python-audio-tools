#include <Python.h>
#include "mod_defs.h"
#include "bitstream.h"
#include "huffman.h"
#include "mod_bitstream.h"

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
#ifndef PyInt_AsLong
#define PyInt_AsLong PyLong_AsLong
#endif
#ifndef PyInt_FromLong
#define PyInt_FromLong PyLong_FromLong
#endif
#endif

MOD_INIT(bitstream)
{
    PyObject* m;

    MOD_DEF(m, "bitstream", "a bitstream handling module", module_methods)

    bitstream_BitstreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamReaderType) < 0)
        return MOD_ERROR_VAL;

    bitstream_HuffmanTreeType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_HuffmanTreeType) < 0)
        return MOD_ERROR_VAL;

    bitstream_BitstreamWriterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamWriterType) < 0)
        return MOD_ERROR_VAL;

    bitstream_BitstreamRecorderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamRecorderType) < 0)
        return MOD_ERROR_VAL;

    bitstream_BitstreamAccumulatorType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamAccumulatorType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&bitstream_BitstreamReaderType);
    PyModule_AddObject(m, "BitstreamReader",
                       (PyObject *)&bitstream_BitstreamReaderType);

    Py_INCREF(&bitstream_HuffmanTreeType);
    PyModule_AddObject(m, "HuffmanTree",
                       (PyObject *)&bitstream_HuffmanTreeType);

    Py_INCREF(&bitstream_BitstreamWriterType);
    PyModule_AddObject(m, "BitstreamWriter",
                       (PyObject *)&bitstream_BitstreamWriterType);

    Py_INCREF(&bitstream_BitstreamRecorderType);
    PyModule_AddObject(m, "BitstreamRecorder",
                       (PyObject *)&bitstream_BitstreamRecorderType);

    Py_INCREF(&bitstream_BitstreamAccumulatorType);
    PyModule_AddObject(m, "BitstreamAccumulator",
                       (PyObject *)&bitstream_BitstreamAccumulatorType);

    return MOD_SUCCESS_VAL(m);
}

static PyObject*
brpy_read_unsigned_be(BitstreamReader *br, unsigned bits)
{
    const unsigned buffer_size = sizeof(unsigned) * 8;
    PyObject *accumulator = PyInt_FromLong(0);

    while (bits > 0) {
        const unsigned bits_to_read = bits > buffer_size ? buffer_size : bits;
        unsigned result;
        PyObject *shift;
        PyObject *shifted;

        /*perform actual reading from stream*/
        if (!setjmp(*br_try(br))) {
            result = br->read(br, bits_to_read);
            br_etry(br);
        } else {
            br_etry(br);
            Py_DECREF(accumulator);
            PyErr_SetString(PyExc_IOError, "I/O error reading stream");
            return NULL;
        }

        /*prepend bits to accumulator*/
        shift = PyInt_FromLong(bits_to_read);
        shifted = PyNumber_Lshift(accumulator, shift);
        Py_DECREF(shift);
        Py_DECREF(accumulator);
        if (shifted == NULL) {
            return NULL;
        } else {
            PyObject *result_obj = Py_BuildValue("I", result);
            PyObject *prepended = PyNumber_Or(shifted, result_obj);
            Py_DECREF(result_obj);
            Py_DECREF(shifted);
            if (prepended == NULL) {
                return NULL;
            } else {
                accumulator = prepended;
            }
        }

        /*deduct count from remaining bits*/
        bits -= bits_to_read;
    }

    return accumulator;
}

static PyObject*
brpy_read_unsigned_le(BitstreamReader *br, unsigned bits)
{
    const unsigned buffer_size = sizeof(unsigned) * 8;
    PyObject *accumulator = PyInt_FromLong(0);
    PyObject *shift = PyInt_FromLong(0);

    while (bits > 0) {
        const unsigned bits_to_read = bits > buffer_size ? buffer_size : bits;
        unsigned result;
        PyObject *bits_to_read_obj;
        PyObject *next_shift;
        PyObject *result_obj;
        PyObject *shifted;

        /*perform actual reading from stream*/
        if (!setjmp(*br_try(br))) {
            result = br->read(br, bits_to_read);
            br_etry(br);
        } else {
            br_etry(br);
            Py_DECREF(accumulator);
            Py_DECREF(shift);
            PyErr_SetString(PyExc_IOError, "I/O error reading stream");
            return NULL;
        }

        /*append bits to accumulator*/
        result_obj = Py_BuildValue("I", result);
        shifted = PyNumber_Lshift(result_obj, shift);
        Py_DECREF(result_obj);
        if (shifted == NULL) {
            Py_DECREF(accumulator);
            Py_DECREF(shift);
            return NULL;
        } else {
            PyObject *appended = PyNumber_Or(shifted, accumulator);
            Py_DECREF(shifted);
            Py_DECREF(accumulator);
            if (appended == NULL) {
                Py_DECREF(shift);
                return NULL;
            } else {
                accumulator = appended;
            }
        }

        /*increment shift for next read*/
        bits_to_read_obj = PyInt_FromLong(bits_to_read);
        next_shift = PyNumber_Add(shift, bits_to_read_obj);
        Py_DECREF(bits_to_read_obj);
        Py_DECREF(shift);
        if (next_shift == NULL) {
            Py_DECREF(accumulator);
            return NULL;
        } else {
            shift = next_shift;
        }

        /*deduct count from remaining bits*/
        bits -= bits_to_read;
    }

    Py_DECREF(shift);
    return accumulator;
}

static PyObject*
brpy_read_signed_be(BitstreamReader *br, unsigned bits)
{
    unsigned sign_bit;
    PyObject* unsigned_value;

    /*read sign bit*/
    if (!setjmp(*br_try(br))) {
        sign_bit = br->read(br, 1);
        br_etry(br);
    } else {
        br_etry(br);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }

    /*read unsigned value*/
    if ((unsigned_value = brpy_read_unsigned_be(br, bits - 1)) == NULL) {
        /*pass exception to caller*/
        return NULL;
    }

    if (sign_bit == 0) {
        /*if unsigned, return unsigned as-is*/
        return unsigned_value;
    } else {
        /*otherwise, convert unsigned value to signed via:
          signed = unsigned - (1 << (bits - 1))
        */
        PyObject *one;
        PyObject *shift;
        PyObject *shifted;
        PyObject *signed_value;

        one = PyInt_FromLong(1);
        shift = PyInt_FromLong(bits - 1);
        shifted = PyNumber_Lshift(one, shift);
        Py_DECREF(one);
        Py_DECREF(shift);
        if (shifted == NULL) {
            Py_DECREF(unsigned_value);
            return NULL;
        }
        signed_value = PyNumber_Subtract(unsigned_value, shifted);
        Py_DECREF(unsigned_value);
        Py_DECREF(shifted);
        return signed_value; /*may be NULL if subtraction failed somehow*/
    }
}

static PyObject*
brpy_read_signed_le(BitstreamReader *br, unsigned bits)
{
    PyObject* unsigned_value;
    unsigned sign_bit;

    /*read unsigned value*/
    if ((unsigned_value = brpy_read_unsigned_le(br, bits - 1)) == NULL) {
        /*pass exception to caller*/
        return NULL;
    }

    /*read sign bit*/
    if (!setjmp(*br_try(br))) {
        sign_bit = br->read(br, 1);
        br_etry(br);
    } else {
        br_etry(br);
        Py_DECREF(unsigned_value);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }

    if (sign_bit == 0) {
        /*if unsigned, return unsigned as-is*/
        return unsigned_value;
    } else {
        /*otherwise, convert unsigned value to signed via:
          signed = unsigned - (1 << (bits - 1))
        */
        PyObject *one;
        PyObject *shift;
        PyObject *shifted;
        PyObject *signed_value;

        one = PyInt_FromLong(1);
        shift = PyInt_FromLong(bits - 1);
        shifted = PyNumber_Lshift(one, shift);
        Py_DECREF(one);
        Py_DECREF(shift);
        if (shifted == NULL) {
            Py_DECREF(unsigned_value);
            return NULL;
        }
        signed_value = PyNumber_Subtract(unsigned_value, shifted);
        Py_DECREF(unsigned_value);
        Py_DECREF(shifted);
        return signed_value; /*may be NULL if subtraction failed somehow*/
    }
}

static PyObject*
BitstreamReader_read(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    return self->read_unsigned(self->bitstream, (unsigned)count);
}

static PyObject*
BitstreamReader_read_signed(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count <= 0) {
        PyErr_SetString(PyExc_ValueError, "count must be > 0");
        return NULL;
    }

    return self->read_signed(self->bitstream, (unsigned)count);
}

static PyObject*
BitstreamReader_skip(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->skip(self->bitstream, (unsigned)count);
        br_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_skip_bytes(bitstream_BitstreamReader *self, PyObject *args)
{
    PyObject *count;

    if (!PyArg_ParseTuple(args, "O", &count)) {
        return NULL;
    }

    if (brpy_skip_bytes_obj(self->bitstream, count)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamReader_byte_align(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_byte_aligned(bitstream_BitstreamReader *self, PyObject *args)
{
    return PyBool_FromLong(self->bitstream->byte_aligned(self->bitstream));
}


static PyObject*
BitstreamReader_unread(bitstream_BitstreamReader *self, PyObject *args)
{
    int unread_bit;

    if (!PyArg_ParseTuple(args, "i", &unread_bit))
        return NULL;

    if ((unread_bit != 0) && (unread_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "unread bit must be 0 or 1");
        return NULL;
    }

    self->bitstream->unread(self->bitstream, unread_bit);

    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject*
BitstreamReader_unary(bitstream_BitstreamReader *self, PyObject *args)
{
    int stop_bit;
    int result;

    if (!PyArg_ParseTuple(args, "i", &stop_bit))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_unary(self->bitstream, stop_bit);
        br_etry(self->bitstream);
        return Py_BuildValue("I", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_skip_unary(bitstream_BitstreamReader *self, PyObject *args)
{
    int stop_bit;

    if (!PyArg_ParseTuple(args, "i", &stop_bit))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->skip_unary(self->bitstream, stop_bit);
        br_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_read_huffman_code(bitstream_BitstreamReader *self,
                                  PyObject* args)
{
    PyObject* huffman_tree_obj;
    bitstream_HuffmanTree* huffman_tree;
    int result;

    if (!PyArg_ParseTuple(args, "O", &huffman_tree_obj))
        return NULL;

    if (Py_TYPE(huffman_tree_obj) != &bitstream_HuffmanTreeType) {
        PyErr_SetString(PyExc_TypeError, "argument must a HuffmanTree object");
        return NULL;
    }

    huffman_tree = (bitstream_HuffmanTree*)huffman_tree_obj;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_huffman_code(
            self->bitstream, huffman_tree->br_table);

        br_etry(self->bitstream);
        return Py_BuildValue("i", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

#define CHUNK_SIZE 4096

int
brpy_read_bytes_chunk(BitstreamReader *reader,
                      unsigned byte_count,
                      struct bs_buffer *buffer)
{
    if (!setjmp(*br_try(reader))) {
        while (byte_count > 0) {
            const unsigned to_read = MIN(byte_count, CHUNK_SIZE);
            static uint8_t temp[CHUNK_SIZE];

            reader->read_bytes(reader, temp, to_read);
            buf_write(buffer, temp, to_read);
            byte_count -= to_read;
        }

        br_etry(reader);
        return 0;
    } else {
        br_etry(reader);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return 1;
    }
}

PyObject*
brpy_read_bytes_min(PyObject *x, PyObject *y, long *minimum)
{
    const int cmp = PyObject_RichCompareBool(x, y, Py_LT);
    PyObject *smaller;

    if (cmp == 0) {
        smaller = y;
    } else if (cmp == 1) {
        smaller = x;
    } else {
        return NULL;
    }

    *minimum = PyInt_AsLong(smaller);
    if ((*minimum != -1) || (!PyErr_Occurred())) {
        return smaller;
    } else {
        return NULL;
    }
}

static PyObject*
brpy_read_bytes_obj(BitstreamReader *reader, PyObject *byte_count)
{
    PyObject *zero = PyInt_FromLong(0);
    int zero_cmp = PyObject_RichCompareBool(byte_count, zero, Py_GE);
    PyObject *chunk_size_obj;
    struct bs_buffer *buffer;

    /*ensure we've gotten a positive byte count*/
    if (zero_cmp == 0) {
        PyErr_SetString(PyExc_ValueError, "byte count must be >= 0");
        Py_DECREF(zero);
        return NULL;
    } else if (zero_cmp == -1) {
        /*some error during comparison*/
        Py_DECREF(zero);
        return NULL;
    }

    /*allocate temporary objects and buffer*/
    Py_INCREF(byte_count);
    buffer = buf_new();
    chunk_size_obj = PyInt_FromLong(MIN(UINT_MAX, LONG_MAX));

    /*read up to chunk_size bytes at a time from reader to buffer*/
    zero_cmp = PyObject_RichCompareBool(byte_count, zero, Py_GT);
    while (zero_cmp == 1) {
        /*the size of the chunk to read is chunk_size or byte_count,
          whichever is smaller*/
        long to_read;
        PyObject *to_read_obj;
        PyObject *subtracted;

        if ((to_read_obj = brpy_read_bytes_min(byte_count,
                                               chunk_size_obj,
                                               &to_read)) == NULL) {
            /*some error occurred during comparison*/
            goto error;
        }

        /*perform read from reader to buffer based on size*/
        if (brpy_read_bytes_chunk(reader, (unsigned)to_read, buffer)) {
            /*some error occurring during reading*/
            goto error;
        }

        /*deduct size of chunk from byte_count*/
        if ((subtracted = PyNumber_Subtract(byte_count, to_read_obj)) != NULL) {
            Py_DECREF(byte_count);
            byte_count = subtracted;
        } else {
            /*some error occurred during subtracting*/
            goto error;
        }

        /*check that byte_count is still greater than zero*/
        zero_cmp = PyObject_RichCompareBool(byte_count, zero, Py_GT);
    }

    if (zero_cmp == 0) {
        /*byte_count no longer greater than 0*/

        /*convert buffer to Python string*/
        PyObject *string_obj = PyBytes_FromStringAndSize(
            (char *)buf_window_start(buffer),
            buf_window_size(buffer));

        /*deallocate temporary objects and buffer*/
        Py_DECREF(byte_count);
        Py_DECREF(zero);
        buf_close(buffer);
        Py_DECREF(chunk_size_obj);

        /*return Python string*/
        return string_obj;
    } else {
        /*some error occurred during comparison*/
        goto error;
    }

error:
    /*deallocate temporary objects and buffer*/
    Py_DECREF(byte_count);
    Py_DECREF(zero);
    buf_close(buffer);
    Py_DECREF(chunk_size_obj);

    /*forward error to caller*/
    return NULL;
}


int
brpy_skip_bytes_chunk(BitstreamReader *reader,
                      unsigned byte_count)
{
    if (!setjmp(*br_try(reader))) {
        reader->skip_bytes(reader, byte_count);

        br_etry(reader);
        return 0;
    } else {
        br_etry(reader);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return 1;
    }
}

int
brpy_skip_bytes_obj(BitstreamReader *reader, PyObject *byte_count)
{
    PyObject *zero = PyInt_FromLong(0);
    int zero_cmp = PyObject_RichCompareBool(byte_count, zero, Py_GE);
    PyObject *chunk_size_obj;

    /*ensure we've gotten a positive byte count*/
    if (zero_cmp == 0) {
        PyErr_SetString(PyExc_ValueError, "byte count must be >= 0");
        Py_DECREF(zero);
        return 1;
    } else if (zero_cmp == -1) {
        /*some error during comparison*/
        Py_DECREF(zero);
        return 1;
    }

    /*allocate temporary objects*/
    Py_INCREF(byte_count);
    chunk_size_obj = PyInt_FromLong(MIN(UINT_MAX, LONG_MAX));

    /*read up to chunk_size bytes at a time from reader*/
    zero_cmp = PyObject_RichCompareBool(byte_count, zero, Py_GT);
    while (zero_cmp == 1) {
        /*the size of the chunk to read is chunk_size or byte_count,
          whichever is smaller*/
        long to_read;
        PyObject *to_read_obj;
        PyObject *subtracted;

        if ((to_read_obj = brpy_read_bytes_min(byte_count,
                                               chunk_size_obj,
                                               &to_read)) == NULL) {
            /*some error occurred during comparison*/
            goto error;
        }

        /*perform read from reader to buffer based on size*/
        if (brpy_skip_bytes_chunk(reader, (unsigned)to_read)) {
            /*some error occurring during reading*/
            goto error;
        }

        /*deduct size of chunk from byte_count*/
        if ((subtracted = PyNumber_Subtract(byte_count, to_read_obj)) != NULL) {
            Py_DECREF(byte_count);
            byte_count = subtracted;
        } else {
            /*some error occurred during subtracting*/
            goto error;
        }

        /*check that byte_count is still greater than zero*/
        zero_cmp = PyObject_RichCompareBool(byte_count, zero, Py_GT);
    }

    if (zero_cmp == 0) {
        /*byte_count no longer greater than 0*/

        /*deallocate temporary objects and buffer*/
        Py_DECREF(byte_count);
        Py_DECREF(zero);
        Py_DECREF(chunk_size_obj);

        /*return success*/
        return 0;
    } else {
        /*some error occurred during comparison*/
        goto error;
    }

error:
    /*deallocate temporary objects and buffer*/
    Py_DECREF(byte_count);
    Py_DECREF(zero);
    Py_DECREF(chunk_size_obj);

    /*return read error*/
    return 1;
}

static PyObject*
brpy_read_bytes(BitstreamReader *reader, unsigned byte_count)
{
    struct bs_buffer *buffer = buf_new();

    if (brpy_read_bytes_chunk(reader, byte_count, buffer)) {
        /*some error occurring during reading*/

        /*deallocate buffer*/
        buf_close(buffer);

        /*pass error along to caller*/
        return NULL;
    } else {
        /*convert buffer to Python string*/
        PyObject *string = PyBytes_FromStringAndSize(
            (char *)buf_window_start(buffer),
            buf_window_size(buffer));

        /*deallocate buffer*/
        buf_close(buffer);

        /*return string*/
        return string;
    }
}

static PyObject*
BitstreamReader_read_bytes(bitstream_BitstreamReader *self,
                           PyObject *args)
{
    PyObject *byte_count;

    if (!PyArg_ParseTuple(args, "O", &byte_count)) {
        return NULL;
    }

    return brpy_read_bytes_obj(self->bitstream, byte_count);
}

static PyObject*
BitstreamReader_set_endianness(bitstream_BitstreamReader *self,
                               PyObject *args)
{

    if (!PyArg_ParseTuple(args, "i", &(self->little_endian)))
        return NULL;

    if ((self->little_endian != 0) && (self->little_endian != 1)) {
        PyErr_SetString(PyExc_ValueError,
                    "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }

    self->bitstream->set_endianness(self->bitstream,
                                    self->little_endian ?
                                    BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    if (self->little_endian) {
        self->read_unsigned = brpy_read_unsigned_le;
        self->read_signed = brpy_read_signed_le;
    } else {
        self->read_unsigned = brpy_read_unsigned_be;
        self->read_signed = brpy_read_signed_be;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_close(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_mark(bitstream_BitstreamReader *self, PyObject *args)
{
    int mark_id = 0;

    if (!PyArg_ParseTuple(args, "|i", &mark_id)) {
        return NULL;
    } else {
        if (!setjmp(*br_try(self->bitstream))) {
            self->bitstream->mark(self->bitstream, mark_id);
            br_etry(self->bitstream);
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_IOError,
                            "I/O error getting current position");
            return NULL;
        }
    }
}

static PyObject*
BitstreamReader_has_mark(bitstream_BitstreamReader *self, PyObject *args)
{
    int mark_id = 0;

    if (!PyArg_ParseTuple(args, "|i", &mark_id)) {
        return NULL;
    } else {
        return PyBool_FromLong(
            self->bitstream->has_mark(self->bitstream, mark_id));
    }
}

static PyObject*
BitstreamReader_rewind(bitstream_BitstreamReader *self, PyObject *args)
{
    int mark_id = 0;

    if (!PyArg_ParseTuple(args, "|i", &mark_id)) {
        return NULL;
    } else {
        if (!setjmp(*br_try(self->bitstream))) {
            self->bitstream->rewind(self->bitstream, mark_id);
            br_etry(self->bitstream);
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error seeking to position");
            return NULL;
        }
    }
}

static PyObject*
BitstreamReader_unmark(bitstream_BitstreamReader *self, PyObject *args)
{
    int mark_id = 0;
    if (!PyArg_ParseTuple(args, "|i", &mark_id)) {
        return NULL;
    } else {
        self->bitstream->unmark(self->bitstream, mark_id);
        Py_INCREF(Py_None);
        return Py_None;
    }
}

/*given a numeric object
  extracts the highest possible long to "l"
  and returns a new reference to a numeric object with that amount removed*/
static PyObject*
extract_largest_long(PyObject *number, long *l)
{
    PyObject *long_max = PyInt_FromLong(LONG_MAX);

    if (PyObject_RichCompareBool(number, long_max, Py_GT)) {
        PyObject *to_return = PyNumber_Subtract(number, long_max);
        Py_DECREF(long_max);
        *l = LONG_MAX;
        return to_return;
    } else {
        Py_DECREF(long_max);
        *l = PyInt_AsLong(number);
        return PyNumber_Subtract(number, number);
    }
}

/*given a numeric object
  extracts the smallest possible long to "l"
  and returns a new reference to a numeric object with that amount removed*/
static PyObject*
extract_smallest_long(PyObject *number, long *l)
{
    PyObject *long_min = PyInt_FromLong(LONG_MIN);

    if (PyObject_RichCompareBool(number, long_min, Py_LT)) {
        PyObject *to_return = PyNumber_Subtract(number, long_min);
        Py_DECREF(long_min);
        *l = LONG_MIN;
        return to_return;
    } else {
        Py_DECREF(long_min);
        *l = PyInt_AsLong(number);
        return PyNumber_Subtract(number, number);
    }
}


static PyObject*
BitstreamReader_seek(bitstream_BitstreamReader *self, PyObject *args)
{
    BitstreamReader *stream = self->bitstream;
    PyObject *initial_position;
    PyObject *position;
    PyObject *temp;
    int whence = 0;
    PyObject *zero;
    long seek_position;

    if (!PyArg_ParseTuple(args, "O|i", &initial_position, &whence)) {
        return NULL;
    } else if (!PyNumber_Check(initial_position)) {
        PyErr_SetString(PyExc_TypeError, "position must be a numeric object");
        return NULL;
    }

    position = initial_position;
    Py_INCREF(position);
    zero = PyInt_FromLong(0);

    switch (whence) {
    case 0:  /*SEEK_SET*/
        {
            /*ensure position is non-negative*/
            if (PyObject_RichCompareBool(position, zero, Py_LT)) {
                PyErr_SetString(PyExc_IOError, "invalid seek position");
                goto error;
            }

            /*perform best absolute seek to initial position*/
            temp = extract_largest_long(position, &seek_position);
            Py_DECREF(position);
            position = temp;
            if (!setjmp(*br_try(stream))) {
                stream->seek(stream, seek_position, BS_SEEK_SET);
                br_etry(stream);
            } else {
                /*I/O error when seeking*/
                br_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error performing seek");
                goto error;
            }

            /*cover remaining distance with relative seeks*/
            while (PyObject_RichCompareBool(position, zero, Py_GT)) {
                temp = extract_largest_long(position, &seek_position);
                Py_DECREF(position);
                position = temp;
                if (!setjmp(*br_try(stream))) {
                    stream->seek(stream, seek_position, BS_SEEK_CUR);
                    br_etry(stream);
                } else {
                    /*I/O error when seeking*/
                    br_etry(stream);
                    PyErr_SetString(PyExc_IOError, "I/O error performing seek");
                    goto error;
                }
            }
        }
        break;
    case 1:  /*SEEK_CUR*/
        {
            if (PyObject_RichCompareBool(position, zero, Py_GT)) {
                /*cover positive distance with relative seeks*/
                while (PyObject_RichCompareBool(position, zero, Py_GT)) {
                    temp = extract_largest_long(position, &seek_position);
                    Py_DECREF(position);
                    position = temp;
                    if (!setjmp(*br_try(stream))) {
                        stream->seek(stream, seek_position, BS_SEEK_CUR);
                        br_etry(stream);
                    } else {
                        br_etry(stream);
                        PyErr_SetString(PyExc_IOError,
                                        "I/O error performing seek");
                        goto error;
                    }
                }
            } else if (PyObject_RichCompareBool(position, zero, Py_LT)) {
                /*cover negative distance with relative seeks*/
                while (PyObject_RichCompareBool(position, zero, Py_LT)) {
                    temp = extract_smallest_long(position, &seek_position);
                    Py_DECREF(position);
                    position = temp;
                    if (!setjmp(*br_try(stream))) {
                        stream->seek(stream, seek_position, BS_SEEK_CUR);
                        br_etry(stream);
                    } else {
                        br_etry(stream);
                        PyErr_SetString(PyExc_IOError,
                                        "I/O error performing seek");
                        goto error;
                    }
                }
            }
            /*position is 0, so no need to move anywhere*/
        }
        break;
    case 2:  /*SEEK_END*/
        {
            /*ensure position is non-positive*/
            if (PyObject_RichCompareBool(position, zero, Py_GT)) {
                PyErr_SetString(PyExc_IOError, "invalid seek position");
                goto error;
            }

            /*perform best absolute seek to initial position*/
            temp = extract_smallest_long(position, &seek_position);
            Py_DECREF(position);
            position = temp;
            if (!setjmp(*br_try(stream))) {
                stream->seek(stream, seek_position, BS_SEEK_END);
                br_etry(stream);
            } else {
                /*I/O error when seeking*/
                br_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error performing seek");
                goto error;
            }

            /*cover remaining distance with relative seeks*/
            while (PyObject_RichCompareBool(position, zero, Py_LT)) {
                temp = extract_smallest_long(position, &seek_position);
                Py_DECREF(position);
                position = temp;
                if (!setjmp(*br_try(stream))) {
                    stream->seek(stream, seek_position, BS_SEEK_CUR);
                    br_etry(stream);
                } else {
                    /*I/O error when seeking*/
                    br_etry(stream);
                    PyErr_SetString(PyExc_IOError, "I/O error performing seek");
                    goto error;
                }
            }
        }
        break;
    default:
        PyErr_SetString(PyExc_ValueError, "whence must be 0, 1 or 2");
        goto error;
    }

    Py_DECREF(position);
    Py_DECREF(zero);
    Py_INCREF(Py_None);
    return Py_None;
error:
    Py_DECREF(position);
    Py_DECREF(zero);
    return NULL;
}

static PyObject*
BitstreamReader_add_callback(bitstream_BitstreamReader *self, PyObject *args)
{
    PyObject* callback;

    if (!PyArg_ParseTuple(args, "O", &callback))
        return NULL;

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
        return NULL;
    }

    Py_INCREF(callback);
    self->bitstream->add_callback(self->bitstream,
                                  (bs_callback_f)BitstreamReader_callback,
                                  callback);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_pop_callback(bitstream_BitstreamReader *self, PyObject *args)
{
    struct bs_callback callback;
    PyObject* callback_obj;

    if (self->bitstream->callbacks != NULL) {
        self->bitstream->pop_callback(self->bitstream, &callback);
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
BitstreamReader_call_callbacks(bitstream_BitstreamReader *self, PyObject *args)
{
    uint8_t byte;

    if (!PyArg_ParseTuple(args, "b", &byte))
        return NULL;

    self->bitstream->call_callbacks(self->bitstream, byte);

    Py_INCREF(Py_None);
    return Py_None;
}

void
BitstreamReader_callback(uint8_t byte, PyObject *callback)
{
    PyObject* result = PyObject_CallFunction(callback, "B", byte);

    if (result != NULL) {
        Py_DECREF(result);
    } else {
        PyErr_PrintEx(0);
    }
}

static PyObject*
BitstreamReader_substream_meth(bitstream_BitstreamReader *self, PyObject *args)
{
    PyTypeObject *type = Py_TYPE(self);
    long int bytes;
    bitstream_BitstreamReader *obj;

    if (!PyArg_ParseTuple(args, "l", &bytes)) {
        return NULL;
    } else if (bytes < 0) {
        PyErr_SetString(PyExc_ValueError, "byte count must be >= 0");
        return NULL;
    } else if (bytes > UINT_MAX) {
        return PyErr_Format(PyExc_ValueError,
                            "byte count must be <= %u",
                            UINT_MAX);
    }

    obj = (bitstream_BitstreamReader *)type->tp_alloc(type, 0);
    obj->little_endian = self->little_endian;
    obj->bitstream = br_substream_new(obj->little_endian ?
                                      BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    if (self->little_endian) {
        obj->read_unsigned = brpy_read_unsigned_le;
        obj->read_signed = brpy_read_signed_le;
    } else {
        obj->read_unsigned = brpy_read_unsigned_be;
        obj->read_signed = brpy_read_signed_be;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->substream_append(self->bitstream,
                                          obj->bitstream,
                                          (unsigned)bytes);
        br_etry(self->bitstream);
        return (PyObject *)obj;
    } else {
        br_etry(self->bitstream);
        /*read error occurred during substream_append*/
        Py_DECREF((PyObject *)obj);
        PyErr_SetString(PyExc_IOError, "I/O error creating substream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_substream_append(bitstream_BitstreamReader *self,
                                 PyObject *args)
{
    PyObject *substream_obj;
    bitstream_BitstreamReader *substream;
    long int bytes;

    if (!PyArg_ParseTuple(args, "Ol", &substream_obj, &bytes)) {
        return NULL;
    } else if (bytes < 0) {
        PyErr_SetString(PyExc_ValueError, "byte count must be >= 0");
        return NULL;
    } else if (bytes > UINT_MAX) {
        return PyErr_Format(PyExc_ValueError,
                            "byte count must be < %u",
                            UINT_MAX);
    }

    if (Py_TYPE(self) != Py_TYPE(substream_obj)) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be a BitstreamReader");
        return NULL;
    } else
        substream = (bitstream_BitstreamReader*)substream_obj;

    if (substream->bitstream->type != BR_SUBSTREAM) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be a substream");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->substream_append(self->bitstream,
                                          substream->bitstream,
                                          (unsigned)bytes);

        br_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        br_etry(self->bitstream);
        /*read error occured during substream_append*/
        PyErr_SetString(PyExc_IOError, "I/O error appending substream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_parse(bitstream_BitstreamReader *self, PyObject *args)
{
    char* format;

    if (!PyArg_ParseTuple(args, "s", &format)) {
        return NULL;
    } else {
        PyObject *values = PyList_New(0);

        if (!bitstream_parse(self->bitstream,
                             self->read_unsigned,
                             self->read_signed,
                             format,
                             values)) {
            return values;
        } else {
            Py_DECREF(values);
            return NULL;
        }
    }
}

PyObject*
BitstreamReader_new(PyTypeObject *type,
                    PyObject *args, PyObject *kwds)
{
    bitstream_BitstreamReader *self;

    self = (bitstream_BitstreamReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamReader_init(bitstream_BitstreamReader *self,
                     PyObject *args)
{
    PyObject *file_obj;
    int buffer_size = 4096;

    self->bitstream = NULL;
    self->string_buffer = NULL;

    if (!PyArg_ParseTuple(args, "Oi|i",
                          &file_obj,
                          &(self->little_endian),
                          &buffer_size)) {
        return -1;
    } else if (buffer_size <= 0) {
        PyErr_SetString(PyExc_ValueError, "buffer_size must be > 0");
        return -1;
    }

    if (PyBytes_CheckExact(file_obj)) {
        /*dump contents of Python string into internal buffer*/
        char *buffer;
        Py_ssize_t length;

        if (PyBytes_AsStringAndSize(file_obj, &buffer, &length) == -1) {
            /*some error during string conversion*/
            return -1;
        }

        self->string_buffer = buf_new();

        /*FIXME - this presumes buffer can holder more bytes than
          an unsigned int, which isn't the case yet*/
        while (length > 0) {
            const unsigned to_write = (unsigned)MIN(length, UINT_MAX);
            buf_write(self->string_buffer, (uint8_t*)buffer, to_write);
            buffer += to_write;
            length -= to_write;
        }

        self->bitstream = br_open_buffer(self->string_buffer,
                                         self->little_endian ?
                                         BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    } else {
        /*store a reference to the Python object so that it doesn't decref
          (and close) the file out from under us*/
        Py_INCREF(file_obj);

        self->bitstream = br_open_external(
            file_obj,
            self->little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
            (unsigned)buffer_size,
            (ext_read_f)br_read_python,
            (ext_setpos_f)bs_setpos_python,
            (ext_getpos_f)bs_getpos_python,
            (ext_free_pos_f)bs_free_pos_python,
            (ext_seek_f)bs_fseek_python,
            (ext_close_f)bs_close_python,
            (ext_free_f)bs_free_python_decref);
    }

    if (self->little_endian) {
        self->read_unsigned = brpy_read_unsigned_le;
        self->read_signed = brpy_read_signed_le;
    } else {
        self->read_unsigned = brpy_read_unsigned_be;
        self->read_signed = brpy_read_signed_be;
    }

    return 0;
}

void
br_close_internal_stream_python_file(BitstreamReader* bs)
{
    /*swap read methods with closed methods*/
    br_close_methods(bs);
}

void
BitstreamReader_dealloc(bitstream_BitstreamReader *self)
{
    struct bs_callback *c_node;

    if (self->bitstream != NULL) {
        /*DECREF all active callback data*/
        for (c_node = self->bitstream->callbacks;
             c_node != NULL;
             c_node = c_node->next) {
            Py_DECREF(c_node->data);
        }

        /*perform free() on rest of BitstreamReader*/
        self->bitstream->free(self->bitstream);
    }

    if (self->string_buffer != NULL) {
        buf_close(self->string_buffer);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
BitstreamReader_Substream(PyObject *dummy, PyObject *args)
{
    int endianness;
    PyTypeObject *type = &bitstream_BitstreamReaderType;
    bitstream_BitstreamReader *reader;

    if (!PyArg_ParseTuple(args, "i", &endianness))
        return NULL;

    reader = (bitstream_BitstreamReader *)type->tp_alloc(type, 0);

    reader->bitstream = br_substream_new(endianness ?
                                         BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    reader->little_endian = endianness;

    return (PyObject *)reader;
}

static PyObject*
BitstreamReader_enter(bitstream_BitstreamReader *self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
BitstreamReader_exit(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

/*this functions similarly to json_to_frequencies -> compile_huffman_table*/
int
HuffmanTree_init(bitstream_HuffmanTree *self, PyObject *args)
{
    PyObject* frequencies_list;
    PyObject* bits_list;
    PyObject* value_obj;
    long value_int_value;
    PyObject* bits_int;
    long bits_int_value;
    int little_endian;
    Py_ssize_t list_length;
    Py_ssize_t bits_length;
    Py_ssize_t i,o,j;
    struct huffman_frequency* frequencies = NULL;
    struct huffman_frequency frequency;

    /*most of this stuff is for converting Python objects
      to plain integers for use by compile_huffman_table*/

    self->br_table = NULL;
    self->bw_table = NULL;

    if (!PyArg_ParseTuple(args, "Oi", &frequencies_list, &little_endian))
        return -1;

    if ((list_length = PySequence_Length(frequencies_list)) == -1) {
        return -1;
    }
    if (list_length < 1) {
        PyErr_SetString(PyExc_ValueError, "frequencies cannot be empty");
        return -1;
    }
    if (list_length % 2) {
        PyErr_SetString(PyExc_ValueError,
                        "frequencies must have an even number of elements");
        return -1;
    }

    frequencies = malloc(sizeof(struct huffman_frequency) * (list_length / 2));

    for (i = o = 0; i < list_length; i += 2,o++) {
        frequency.bits = frequency.length = 0;
        bits_list = value_obj = bits_int = NULL;

        if ((bits_list = PySequence_GetItem(frequencies_list, i)) == NULL)
            goto error;

        if ((value_obj = PySequence_GetItem(frequencies_list, i + 1)) == NULL)
            goto error;

        /*bits are always consumed in big-endian order*/
        if ((bits_length = PySequence_Length(bits_list)) == -1)
            goto error;

        for (j = 0; j < bits_length; j++) {
            bits_int = NULL;
            if ((bits_int = PySequence_GetItem(bits_list, j)) == NULL)
                goto error;
            if (((bits_int_value = PyInt_AsLong(bits_int)) == -1) &&
                PyErr_Occurred())
                goto error;

            if ((bits_int_value != 0) && (bits_int_value != 1)) {
                PyErr_SetString(PyExc_ValueError, "bits must be 0 or 1");
                goto error;
            }

            frequency.bits = (unsigned int)((frequency.bits << 1) |
                                            bits_int_value);
            frequency.length++;

            Py_DECREF(bits_int);
            bits_int = NULL;
        }

        /*value must always be an integer*/
        if (((value_int_value = PyInt_AsLong(value_obj)) == -1) &&
            PyErr_Occurred())
            goto error;

        frequency.value = (int)value_int_value;

        frequencies[o] = frequency;

        Py_DECREF(bits_list);
        Py_DECREF(value_obj);
        bits_list = value_obj = NULL;
    }

    switch (compile_br_huffman_table(&(self->br_table),
                                     frequencies,
                                     (unsigned int)(list_length / 2),
                                     little_endian ?
                                     BS_LITTLE_ENDIAN : BS_BIG_ENDIAN)) {
    case HUFFMAN_MISSING_LEAF:
        PyErr_SetString(PyExc_ValueError, "Huffman tree missing leaf");
        goto error;
    case HUFFMAN_DUPLICATE_LEAF:
        PyErr_SetString(PyExc_ValueError, "Huffman tree has duplicate leaf");
        goto error;
    case HUFFMAN_ORPHANED_LEAF:
        PyErr_SetString(PyExc_ValueError, "Huffman tree has orphaned leaf");
        goto error;
    case HUFFMAN_EMPTY_TREE:
        PyErr_SetString(PyExc_ValueError, "Huffman tree is empty");
        goto error;
    default:
        break;
    }

    switch (compile_bw_huffman_table(&(self->bw_table),
                                     frequencies,
                                     (unsigned int)(list_length / 2),
                                     little_endian ?
                                     BS_LITTLE_ENDIAN : BS_BIG_ENDIAN)) {
    /*these shouldn't be triggered if compile_br_table succeeds*/
    case HUFFMAN_MISSING_LEAF:
        PyErr_SetString(PyExc_ValueError, "Huffman tree missing leaf");
        goto error;
    case HUFFMAN_DUPLICATE_LEAF:
        PyErr_SetString(PyExc_ValueError, "Huffman tree has duplicate leaf");
        goto error;
    case HUFFMAN_ORPHANED_LEAF:
        PyErr_SetString(PyExc_ValueError, "Huffman tree has orphaned leaf");
        goto error;
    case HUFFMAN_EMPTY_TREE:
        PyErr_SetString(PyExc_ValueError, "Huffman tree is empty");
        goto error;
    default:
        break;
    }

    free(frequencies);
    return 0;
 error:
    Py_XDECREF(bits_int);
    Py_XDECREF(bits_list);
    Py_XDECREF(value_obj);
    if (frequencies != NULL)
        free(frequencies);
    return -1;
}

void
HuffmanTree_dealloc(bitstream_HuffmanTree *self)
{
    free(self->br_table);
    free(self->bw_table);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
HuffmanTree_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    bitstream_HuffmanTree *self;

    self = (bitstream_HuffmanTree *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamWriter_init(bitstream_BitstreamWriter *self, PyObject *args)
{
    PyObject *file_obj;
    int little_endian;
    int buffer_size = 4096;

    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "Oi|i", &file_obj, &little_endian,
                          &buffer_size)) {
        return -1;
    } else if (buffer_size <= 0) {
        PyErr_SetString(PyExc_ValueError, "buffer_size must be > 0");
        return -1;
    }

    /*store a reference to the Python object so that it doesn't decref
      (and close) the file out from under us*/
    Py_INCREF(file_obj);

    self->bitstream = bw_open_external(
        file_obj,
        little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
        (unsigned)buffer_size,
        (ext_write_f)bw_write_python,
        (ext_setpos_f)bs_setpos_python,
        (ext_getpos_f)bs_getpos_python,
        (ext_free_pos_f)bs_free_pos_python,
        (ext_flush_f)bw_flush_python,
        (ext_close_f)bs_close_python,
        (ext_free_f)bs_free_python_decref);

    if (little_endian) {
        self->write_unsigned = bwpy_write_unsigned_le;
        self->write_signed = bwpy_write_signed_le;
    } else {
        self->write_unsigned = bwpy_write_unsigned_be;
        self->write_signed = bwpy_write_signed_be;
    }

    return 0;
}

void
bw_close_internal_stream_python_file(BitstreamWriter* bs)
{
    /*flush pending output to FILE object*/
    fflush(bs->output.file);

    /*swap write methods with closed methods*/
    bw_close_methods(bs);
}

/*this is essentially:
  (1 << bits_to_write) - 1
  implemented as operations on Python numberic objects
  used by the write_unsigned() functions to eliminate
  unneeded right-side bits*/
static PyObject*
bwpy_unsigned_mask(unsigned bits_to_write)
{
    PyObject *one;
    PyObject *bits_to_write_obj;
    PyObject *shifted;
    PyObject *mask;

    one = PyInt_FromLong(1);
    bits_to_write_obj = PyInt_FromLong(bits_to_write);

    if ((shifted = PyNumber_Lshift(one, bits_to_write_obj)) == NULL) {
        Py_DECREF(one);
        Py_DECREF(bits_to_write_obj);
        return NULL;
    } else {
        Py_DECREF(bits_to_write_obj);
    }
    mask = PyNumber_Subtract(shifted, one); /*may return NULL*/
    Py_DECREF(one);
    Py_DECREF(shifted);
    return mask;
}

/*this is essentially:
  1 << (bits_to_write - 1)
  implemented as operations on Python numeric objects
  used by the write_signed() functions to
  convert signed values to unsigned*/
static PyObject*
bwpy_signed_mask(unsigned bits_to_write)
{
    PyObject *bits;
    PyObject *one;
    PyObject *mask;

    bits = PyInt_FromLong(bits_to_write - 1);
    one = PyInt_FromLong(1);
    mask = PyNumber_Lshift(one, bits); /*may return NULL*/
    Py_DECREF(bits);
    Py_DECREF(one);
    return mask;
}

static PyObject*
bwpy_min_unsigned(unsigned bits)
{
    return PyInt_FromLong(0);
}

static PyObject*
bwpy_max_unsigned(unsigned bits)
{
    /*(2 ^ bits) - 1*/
    PyObject *one;
    PyObject *bits_obj;
    PyObject *shifted;
    PyObject *value;

    one = PyInt_FromLong(1);
    bits_obj = PyInt_FromLong(bits);
    shifted = PyNumber_Lshift(one, bits_obj);
    Py_DECREF(bits_obj);
    if (shifted == NULL) {
        Py_DECREF(one);
        return NULL;
    }
    value = PyNumber_Subtract(shifted, one);
    Py_DECREF(shifted);
    Py_DECREF(one);
    return value;
}

static PyObject*
bwpy_min_signed(unsigned bits)
{
    /*-(2 ^ (bits - 1))*/
    PyObject *one;
    PyObject *bits_obj;
    PyObject *shifted;
    PyObject *value;

    one = PyInt_FromLong(1);
    bits_obj = PyInt_FromLong(bits - 1);
    shifted = PyNumber_Lshift(one, bits_obj);
    Py_DECREF(one);
    Py_DECREF(bits_obj);
    if (shifted == NULL)
        return NULL;
    value = PyNumber_Negative(shifted);
    Py_DECREF(shifted);
    return value;
}

static PyObject*
bwpy_max_signed(unsigned bits)
{
    /*(2 ^ (bits - 1)) - 1*/
    return bwpy_max_unsigned(bits - 1);
}

static int
bwpy_in_range(PyObject *min_value, PyObject *value, PyObject *max_value)
{
    const int cmp_min = PyObject_RichCompareBool(min_value, value, Py_LE);
    const int cmp_max = PyObject_RichCompareBool(value, max_value, Py_LE);

    return (cmp_min == 1) && (cmp_max == 1);
}

#define FUNC_VALIDATE_RANGE(FUNC_NAME, MIN_FUNC, MAX_FUNC, TYPE_STR) \
static int                                                           \
FUNC_NAME(unsigned bits, PyObject *value) {                          \
    PyObject *min_value;                                             \
    PyObject *max_value;                                             \
                                                                     \
    if (!PyNumber_Check(value)) {                                    \
        PyErr_SetString(PyExc_TypeError, "value is not a number");   \
        return 0;                                                    \
    }                                                                \
                                                                     \
    min_value = MIN_FUNC(bits);                                      \
    max_value = MAX_FUNC(bits);                                      \
                                                                     \
    if (min_value == NULL) {                                         \
        Py_XDECREF(max_value);                                       \
        return 0;                                                    \
    } else if (max_value == NULL) {                                  \
        Py_DECREF(min_value);                                        \
        return 0;                                                    \
    }                                                                \
                                                                     \
    if (!bwpy_in_range(min_value, value, max_value)) {               \
        PyErr_Format(PyExc_ValueError,                               \
                     "value does not fit in %u " TYPE_STR " %s",     \
                     bits,                                           \
                     bits != 1 ? "bits" : "bit");                    \
                                                                     \
        Py_DECREF(min_value);                                        \
        Py_DECREF(max_value);                                        \
        return 0;                                                    \
    } else {                                                         \
        Py_DECREF(min_value);                                        \
        Py_DECREF(max_value);                                        \
        return 1;                                                    \
    }                                                                \
}
FUNC_VALIDATE_RANGE(bw_validate_unsigned_range,
                    bwpy_min_unsigned,
                    bwpy_max_unsigned,
                    "unsigned")
FUNC_VALIDATE_RANGE(bw_validate_signed_range,
                    bwpy_min_signed,
                    bwpy_max_signed,
                    "signed")


static int
bwpy_write_unsigned_be(BitstreamWriter *bw, unsigned bits, PyObject *value)
{
    const unsigned buffer_size = MIN((sizeof(long) * 8) - 1,
                                     sizeof(unsigned) * 8);

    /*chop off up to "buffer_size" bits to write at a time*/
    while (bits > 0) {
        const unsigned bits_to_write = bits > buffer_size ? buffer_size : bits;
        PyObject *shift;
        PyObject *shifted;
        PyObject *mask;
        PyObject *masked;
        long masked_value;
        unsigned buffer;

        /*shift out the unneeded left bits*/
        shift = PyInt_FromLong((long)(bits - bits_to_write));
        if ((shifted = PyNumber_Rshift(value, shift)) != NULL) {
            Py_DECREF(shift);
        } else {
            Py_DECREF(shift);
            return 1;
        }

        /*mask out the unneeded right bits*/
        if ((mask = bwpy_unsigned_mask(bits_to_write)) == NULL)
            return 1;
        masked = PyNumber_And(shifted, mask);
        Py_DECREF(mask);
        Py_DECREF(shifted);
        if (masked == NULL) {
            return 1;
        }

        /*convert result from Python object to integer*/
        masked_value = PyInt_AsLong(masked);
        Py_DECREF(masked);
        if ((masked_value == -1) && PyErr_Occurred()) {
            return 1;
        }
        buffer = (unsigned)masked_value;

        /*write the value itself*/
        if (!setjmp(*bw_try(bw))) {
            bw->write(bw, bits_to_write, buffer);
            bw_etry(bw);
        } else {
            bw_etry(bw);
            PyErr_SetString(PyExc_IOError, "I/O error writing stream");
            return 1;
        }

        /*decrement the count*/
        bits -= bits_to_write;
    }

    return 0;
}

static int
bwpy_write_unsigned_le(BitstreamWriter *bw, unsigned bits, PyObject *value)
{
    const unsigned buffer_size = MIN((sizeof(long) * 8) - 1,
                                     sizeof(unsigned) * 8);
    Py_INCREF(value);

    while (bits > 0) {
        const unsigned bits_to_write = bits > buffer_size ? buffer_size : bits;
        PyObject *mask;
        PyObject *masked;
        PyObject *shift;
        PyObject *shifted;
        long masked_value;
        unsigned buffer;

        /*extract initial bits from value*/
        if ((mask = bwpy_unsigned_mask(bits_to_write)) == NULL) {
            return 1;
        }
        masked = PyNumber_And(value, mask);
        Py_DECREF(mask);
        if (masked == NULL) {
            Py_DECREF(value);
            return 1;
        }

        /*converted result from Python object to integer*/
        masked_value = PyInt_AsLong(masked);
        Py_DECREF(masked);
        if ((masked_value == -1) && PyErr_Occurred()) {
            Py_DECREF(value);
            return 1;
        }
        buffer = (unsigned)masked_value;

        /*write the value itself*/
        if (!setjmp(*bw_try(bw))) {
            bw->write(bw, bits_to_write, buffer);
            bw_etry(bw);
        } else {
            bw_etry(bw);
            PyErr_SetString(PyExc_IOError, "I/O error writing stream");
            return 1;
        }

        /*shift out the written bits*/
        shift = PyInt_FromLong(bits_to_write);
        shifted = PyNumber_Rshift(value, shift);
        Py_DECREF(shift);
        Py_DECREF(value);
        if (shifted != NULL) {
            value = shifted;
        } else {
            return 1;
        }

        /*decrement the count*/
        bits -= bits_to_write;
    }

    Py_DECREF(value);

    return 0;
}

static int
is_positive(PyObject *value)
{
    PyObject *zero = PyInt_FromLong(0);
    const int cmp_result = PyObject_RichCompareBool(value, zero, Py_GE);
    Py_DECREF(zero);
    return (cmp_result == 1);
}

static int
bwpy_write_signed_be(BitstreamWriter *bw, unsigned bits, PyObject *value)
{
    const int positive = is_positive(value);

    /*write sign bit first*/
    if (!setjmp(*bw_try(bw))) {
        bw->write(bw, 1, positive ? 0 : 1);
        bw_etry(bw);
    } else {
        bw_etry(bw);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return 1;
    }

    if (positive) {
        /*positive number*/
        return bwpy_write_unsigned_be(bw, bits - 1, value);
    } else {
        /*negative number*/
        PyObject *mask;
        PyObject *unsigned_value;

        if ((mask = bwpy_signed_mask(bits)) == NULL)
            return 1;
        if ((unsigned_value = PyNumber_Add(mask, value)) != NULL) {
            int result;

            Py_DECREF(mask);
            result = bwpy_write_unsigned_be(bw, bits - 1, unsigned_value);
            Py_DECREF(unsigned_value);
            return result;
        } else {
            Py_DECREF(mask);
            return 1;
        }
    }
}

static int
bwpy_write_signed_le(BitstreamWriter *bw, unsigned bits, PyObject *value)
{
    const int positive = is_positive(value);

    if (positive) {
        /*positive number*/
        int result = bwpy_write_unsigned_le(bw, bits - 1, value);
        if (result)
            return result;
    } else {
        /*negative number*/
        PyObject *mask;
        PyObject *unsigned_value;

        if ((mask = bwpy_signed_mask(bits)) == NULL)
            return 1;
        if ((unsigned_value = PyNumber_Add(mask, value)) != NULL) {
            int result;

            Py_DECREF(mask);
            result = bwpy_write_unsigned_le(bw, bits - 1, unsigned_value);
            Py_DECREF(unsigned_value);
            if (result)
                return result;
        } else {
            Py_DECREF(mask);
            return 1;
        }
    }

    /*write sign bit last*/
    if (!setjmp(*bw_try(bw))) {
        bw->write(bw, 1, positive ? 0 : 1);
        bw_etry(bw);
        return 0;
    } else {
        bw_etry(bw);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return 1;
    }
}

void
BitstreamWriter_dealloc(bitstream_BitstreamWriter *self)
{
    if (self->bitstream != NULL) {
        /*if stream is already closed,
          flush will do nothing*/
        if (!setjmp(*bw_try(self->bitstream))) {
            self->bitstream->flush(self->bitstream);
            bw_etry(self->bitstream);
        } else {
            /*trying to dealloc BitstreamWriter after stream is closed
              is likely to be a problem*/
            bw_etry(self->bitstream);
            fprintf(stderr,
                    "*** Warning: Error occurred trying "
                    "to flush stream during dealloc\n");
        }
        self->bitstream->free(self->bitstream);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
BitstreamWriter_new(PyTypeObject *type, PyObject *args,
                    PyObject *kwds)
{
    bitstream_BitstreamWriter *self;

    self = (bitstream_BitstreamWriter *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
BitstreamWriter_write(bitstream_BitstreamWriter *self, PyObject *args)
{
    int count;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "iO", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!bw_validate_unsigned_range((unsigned)count, value)) {
        return NULL;
    } else if (self->write_unsigned(self->bitstream, (unsigned)count, value)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamWriter_write_signed(bitstream_BitstreamWriter *self, PyObject *args)
{
    int count;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "iO", &count, &value)) {
        return NULL;
    } else if (count <= 0) {
        PyErr_SetString(PyExc_ValueError, "count must be > 0");
        return NULL;
    }

    if (!bw_validate_signed_range((unsigned)count, value)) {
        return NULL;
    } else if (self->write_signed(self->bitstream, (unsigned)count, value)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamWriter_unary(bitstream_BitstreamWriter *self, PyObject *args)
{
    int stop_bit;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_unary(self->bitstream, stop_bit, value);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_write_huffman_code(bitstream_BitstreamWriter *self,
                                   PyObject *args)
{
    PyObject* huffman_tree_obj;
    bitstream_HuffmanTree* huffman_tree;
    int value;

    if (!PyArg_ParseTuple(args, "Oi", &huffman_tree_obj, &value))
        return NULL;

    if (Py_TYPE(huffman_tree_obj) != &bitstream_HuffmanTreeType) {
        PyErr_SetString(PyExc_TypeError, "argument must a HuffmanTree object");
        return NULL;
    }

    huffman_tree = (bitstream_HuffmanTree*)huffman_tree_obj;

    if (!setjmp(*bw_try(self->bitstream))) {
        const int r = self->bitstream->write_huffman_code(
            self->bitstream, huffman_tree->bw_table, value);

        bw_etry(self->bitstream);

        if (r) {
            PyErr_SetString(PyExc_ValueError, "invalid HuffmanTree value");
            return NULL;
        } else {
            Py_INCREF(Py_None);
            return Py_None;
        }
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_byte_align(bitstream_BitstreamWriter *self, PyObject *args)
{
    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->byte_align(self->bitstream);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_byte_aligned(bitstream_BitstreamWriter *self, PyObject *args)
{
    return PyBool_FromLong(self->bitstream->byte_aligned(self->bitstream));
}

static PyObject*
BitstreamWriter_set_endianness(bitstream_BitstreamWriter *self,
                               PyObject *args)
{
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

    if (little_endian) {
        self->write_unsigned = bwpy_write_unsigned_le;
        self->write_signed = bwpy_write_signed_le;
    } else {
        self->write_unsigned = bwpy_write_unsigned_be;
        self->write_signed = bwpy_write_signed_be;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_write_bytes(bitstream_BitstreamWriter *self,
                            PyObject *args)
{
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_bytes(self->bitstream,
                                     (uint8_t*)bytes, bytes_len);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_build(bitstream_BitstreamWriter *self, PyObject *args)
{
    char* format;
    PyObject *values;
    PyObject *iterator;

    if (!PyArg_ParseTuple(args, "sO", &format, &values)) {
        return NULL;
    } else if ((iterator = PyObject_GetIter(values)) == NULL) {
        return NULL;
    } else if (bitstream_build(self->bitstream,
                               self->write_unsigned,
                               self->write_signed,
                               format,
                               iterator)) {
        Py_DECREF(iterator);
        return NULL;
    } else {
        Py_DECREF(iterator);
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamWriter_flush(bitstream_BitstreamWriter *self, PyObject *args)
{
    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->flush(self->bitstream);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_add_callback(bitstream_BitstreamWriter *self,
                             PyObject *args)
{
    PyObject* callback;

    if (!PyArg_ParseTuple(args, "O", &callback))
        return NULL;

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
        return NULL;
    }

    Py_INCREF(callback);
    self->bitstream->add_callback(self->bitstream,
                                  (bs_callback_f)BitstreamWriter_callback,
                                  callback);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_pop_callback(bitstream_BitstreamWriter *self,
                             PyObject *args)
{
    struct bs_callback callback;
    PyObject* callback_obj;

    if (self->bitstream->callbacks != NULL) {
        self->bitstream->pop_callback(self->bitstream, &callback);
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
BitstreamWriter_call_callbacks(bitstream_BitstreamWriter *self,
                               PyObject *args)
{
    uint8_t byte;

    if (!PyArg_ParseTuple(args, "b", &byte))
        return NULL;

    self->bitstream->call_callbacks(self->bitstream, byte);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_mark(bitstream_BitstreamWriter *self, PyObject *args)
{
    int mark_id = 0;
    BitstreamWriter *writer = self->bitstream;

    if (!PyArg_ParseTuple(args, "|i", &mark_id))
        return NULL;

    if ((writer->type == BW_EXTERNAL) &&
        (!python_obj_seekable(writer->output.external->user_data))) {
        PyErr_SetString(PyExc_IOError, "writer is not seekable");
        return NULL;
    }

    if (!(writer->byte_aligned(writer))) {
        PyErr_SetString(PyExc_IOError, "writer is not byte-aligned");
        return NULL;
    }

    if (!setjmp(*bw_try(writer))) {
        writer->mark(writer, mark_id);
        bw_etry(writer);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error getting stream's position");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_has_mark(bitstream_BitstreamWriter *self, PyObject *args)
{
    int mark_id = 0;

    if (!PyArg_ParseTuple(args, "|i", &mark_id)) {
        return NULL;
    } else {
        return PyBool_FromLong(
            self->bitstream->has_mark(self->bitstream, mark_id));
    }
}

static PyObject*
BitstreamWriter_rewind(bitstream_BitstreamWriter *self, PyObject *args)
{
    int mark_id = 0;
    BitstreamWriter *writer = self->bitstream;

    if (!PyArg_ParseTuple(args, "|i", &mark_id))
        return NULL;

    if ((writer->type == BW_EXTERNAL) &&
        (!python_obj_seekable(writer->output.external->user_data))) {
        PyErr_SetString(PyExc_IOError, "writer is not seekable");
        return NULL;
    }

    if (!(writer->byte_aligned(writer))) {
        PyErr_SetString(PyExc_IOError, "writer is not byte-aligned");
        return NULL;
    }

    if (!setjmp(*bw_try(writer))) {
        writer->rewind(writer, mark_id);
        bw_etry(writer);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error seeking in stream");
        return NULL;
    }
}

static PyObject*
BitstreamWriter_unmark(bitstream_BitstreamWriter *self, PyObject *args)
{
    int mark_id = 0;
    BitstreamWriter *writer = self->bitstream;

    if (!PyArg_ParseTuple(args, "|i", &mark_id)) {
        return NULL;
    } else {
        writer->unmark(writer, mark_id);

        Py_INCREF(Py_None);
        return Py_None;
    }

}

static PyObject*
BitstreamWriter_close(bitstream_BitstreamWriter *self, PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_enter(bitstream_BitstreamWriter *self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
BitstreamWriter_exit(bitstream_BitstreamWriter *self, PyObject *args)
{
    PyObject *exc_type;
    PyObject *exc_value;
    PyObject *traceback;

    if (!PyArg_ParseTuple(args, "OOO", &exc_type, &exc_value, &traceback))
        return NULL;

    if ((exc_type == Py_None) &&
        (exc_value == Py_None) &&
        (traceback == Py_None)) {
        /*writer exited normally, so perform flush*/
        if (!setjmp(*bw_try(self->bitstream))) {
            self->bitstream->flush(self->bitstream);
        }
        /*eat any error rather than propogate it with an exception*/
        bw_etry(self->bitstream);
    }

    /*close internal stream*/
    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    int count;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "iO", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!bw_validate_unsigned_range((unsigned)count, value)) {
        return NULL;
    } else if (self->write_unsigned(self->bitstream, (unsigned)count, value)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamRecorder_write_signed(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    int count;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "iO", &count, &value)) {
        return NULL;
    } else if (count <= 0) {
        PyErr_SetString(PyExc_ValueError, "count must be > 0");
        return NULL;
    }


    if (!bw_validate_signed_range((unsigned)count, value)) {
        return NULL;
    } else if (self->write_signed(self->bitstream, (unsigned)count, value)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamRecorder_unary(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    int stop_bit;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_unary(self->bitstream, stop_bit, value);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_write_huffman_code(bitstream_BitstreamRecorder *self,
                                     PyObject *args)
{
    PyObject* huffman_tree_obj;
    bitstream_HuffmanTree* huffman_tree;
    int value;

    if (!PyArg_ParseTuple(args, "Oi", &huffman_tree_obj, &value))
        return NULL;

    if (Py_TYPE(huffman_tree_obj) != &bitstream_HuffmanTreeType) {
        PyErr_SetString(PyExc_TypeError, "argument must a HuffmanTree object");
        return NULL;
    }

    huffman_tree = (bitstream_HuffmanTree*)huffman_tree_obj;

    if (self->bitstream->write_huffman_code(self->bitstream,
                                            huffman_tree->bw_table,
                                            value)) {
        PyErr_SetString(PyExc_ValueError, "invalid HuffmanTree value");
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamRecorder_byte_align(bitstream_BitstreamRecorder *self,
                             PyObject *args)
{
    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->byte_align(self->bitstream);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_byte_aligned(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    return PyBool_FromLong(self->bitstream->byte_aligned(self->bitstream));
}

static PyObject*
BitstreamRecorder_write_bytes(bitstream_BitstreamRecorder *self,
                              PyObject *args)
{
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_bytes(self->bitstream,
                                     (uint8_t*)bytes, bytes_len);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_build(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    char* format;
    PyObject *values;
    PyObject *iterator;

    if (!PyArg_ParseTuple(args, "sO", &format, &values)) {
        return NULL;
    } else if ((iterator = PyObject_GetIter(values)) == NULL) {
        return NULL;
    } else if (bitstream_build(self->bitstream,
                               self->write_unsigned,
                               self->write_signed,
                               format,
                               iterator)) {
        Py_DECREF(iterator);
        return NULL;
    } else {
        Py_DECREF(iterator);
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamRecorder_flush(bitstream_BitstreamRecorder *self, PyObject *args)
{
    self->bitstream->flush(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_set_endianness(bitstream_BitstreamRecorder *self,
                                 PyObject *args)
{
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

    if (little_endian) {
        self->write_unsigned = bwpy_write_unsigned_le;
        self->write_signed = bwpy_write_signed_le;
    } else {
        self->write_unsigned = bwpy_write_unsigned_be;
        self->write_signed = bwpy_write_signed_be;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_bits(bitstream_BitstreamRecorder *self,
                       PyObject *args)
{
    return Py_BuildValue("I", self->bitstream->bits_written(self->bitstream));
}

static PyObject*
BitstreamRecorder_bytes(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    return Py_BuildValue("I",
                         self->bitstream->bits_written(self->bitstream) / 8);
}

static PyObject*
BitstreamRecorder_data(bitstream_BitstreamRecorder *self,
                       PyObject *args)
{
    return PyBytes_FromStringAndSize(
        (char *)buf_window_start(self->bitstream->output.buffer),
        buf_window_size(self->bitstream->output.buffer));
}

static PyObject*
BitstreamRecorder_swap(bitstream_BitstreamRecorder *self,
                       PyObject *args)
{
    bitstream_BitstreamRecorder *to_swap;

    if (!PyArg_ParseTuple(args, "O!",
                          &bitstream_BitstreamRecorderType, &to_swap))
        return NULL;

    to_swap->bitstream->swap(to_swap->bitstream, self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_reset(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    self->bitstream->reset(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static BitstreamWriter*
internal_writer(PyObject *writer)
{
    bitstream_BitstreamWriter* writer_obj;
    bitstream_BitstreamRecorder* recorder_obj;
    bitstream_BitstreamAccumulator* accumulator_obj;

    if (Py_TYPE(writer) == &bitstream_BitstreamWriterType) {
        writer_obj = (bitstream_BitstreamWriter*)writer;
        return writer_obj->bitstream;
    } else if (Py_TYPE(writer) == &bitstream_BitstreamRecorderType) {
        recorder_obj = (bitstream_BitstreamRecorder*)writer;
        return recorder_obj->bitstream;
    } else if (Py_TYPE(writer) == &bitstream_BitstreamAccumulatorType) {
        accumulator_obj = (bitstream_BitstreamAccumulator*)writer;
        return accumulator_obj->bitstream;
    } else {
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_copy(bitstream_BitstreamRecorder *self,
                       PyObject *args)
{
    PyObject* bitstreamwriter_obj;
    BitstreamWriter* target;

    if (!PyArg_ParseTuple(args, "O", &bitstreamwriter_obj))
        return NULL;

    if ((target = internal_writer(bitstreamwriter_obj)) != NULL) {
        if (!setjmp(*bw_try(self->bitstream))) {
            self->bitstream->copy(self->bitstream, target);
            bw_etry(self->bitstream);
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            bw_etry(self->bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error writing stream");
            return NULL;
        }
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "argument must be a "
                        "BitstreamWriter, BitstreamRecorder "
                        "or BitstreamAccumulator");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_split(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    PyObject* target_obj;
    PyObject* remainder_obj;
    BitstreamWriter* target;
    BitstreamWriter* remainder;
    int total_bytes;

    if (!PyArg_ParseTuple(args, "OOi",
                          &target_obj, &remainder_obj, &total_bytes)) {
        return NULL;
    } else if (total_bytes < 0) {
        PyErr_SetString(PyExc_ValueError, "total_bytes must be >= 0");
        return NULL;
    }

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


    if (!setjmp(*bw_try(self->bitstream))) {
        total_bytes = self->bitstream->split(self->bitstream,
                                             total_bytes,
                                             target,
                                             remainder);
        bw_etry(self->bitstream);
        return Py_BuildValue("I", total_bytes);
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_add_callback(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    PyObject* callback;

    if (!PyArg_ParseTuple(args, "O", &callback))
        return NULL;

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
        return NULL;
    }

    Py_INCREF(callback);
    self->bitstream->add_callback(self->bitstream,
                                  (bs_callback_f)BitstreamWriter_callback,
                                  callback);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_pop_callback(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    struct bs_callback callback;
    PyObject* callback_obj;

    if (self->bitstream->callbacks != NULL) {
        self->bitstream->pop_callback(self->bitstream, &callback);
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
BitstreamRecorder_call_callbacks(bitstream_BitstreamRecorder *self,
                                 PyObject *args)
{
    uint8_t byte;

    if (!PyArg_ParseTuple(args, "b", &byte))
        return NULL;

    self->bitstream->call_callbacks(self->bitstream, byte);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_enter(bitstream_BitstreamRecorder *self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
BitstreamRecorder_exit(bitstream_BitstreamRecorder *self, PyObject *args)
{
    /*close internal stream*/
    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_close(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

int
BitstreamRecorder_init(bitstream_BitstreamRecorder *self,
                       PyObject *args)
{
    int little_endian;

    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return -1;

    self->bitstream = bw_open_recorder(little_endian ?
                                       BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    if (little_endian) {
        self->write_unsigned = bwpy_write_unsigned_le;
        self->write_signed = bwpy_write_signed_le;
    } else {
        self->write_unsigned = bwpy_write_unsigned_be;
        self->write_signed = bwpy_write_signed_be;
    }

    return 0;
}

void
BitstreamRecorder_dealloc(bitstream_BitstreamRecorder *self)
{
    if (self->bitstream != NULL)
        self->bitstream->free(self->bitstream);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
BitstreamRecorder_new(PyTypeObject *type, PyObject *args,
                      PyObject *kwds)
{
    bitstream_BitstreamRecorder *self;

    self = (bitstream_BitstreamRecorder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamAccumulator_init(bitstream_BitstreamAccumulator *self, PyObject *args)
{
    int little_endian;

    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return -1;

    self->bitstream = bw_open_accumulator(little_endian ?
                                          BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    if (little_endian) {
        self->write_unsigned = bwpy_write_unsigned_le;
        self->write_signed = bwpy_write_signed_le;
    } else {
        self->write_unsigned = bwpy_write_unsigned_be;
        self->write_signed = bwpy_write_signed_be;
    }

    return 0;
}

void
BitstreamAccumulator_dealloc(bitstream_BitstreamAccumulator *self)
{
    if (self->bitstream != NULL)
        self->bitstream->free(self->bitstream);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
BitstreamAccumulator_new(PyTypeObject *type, PyObject *args,
                         PyObject *kwds)
{
    bitstream_BitstreamAccumulator *self;

    self = (bitstream_BitstreamAccumulator *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
BitstreamAccumulator_enter(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
BitstreamAccumulator_exit(bitstream_BitstreamAccumulator *self,
                          PyObject *args)
{
    /*close internal stream*/
    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_close(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    int count;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "iO", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!bw_validate_unsigned_range((unsigned)count, value)) {
        return NULL;
    } else if (self->write_unsigned(self->bitstream, (unsigned)count, value)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamAccumulator_write_signed(bitstream_BitstreamAccumulator *self,
                                  PyObject *args)
{
    int count;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "iO", &count, &value)) {
        return NULL;
    } else if (count <= 0) {
        PyErr_SetString(PyExc_ValueError, "count must be > 0");
        return NULL;
    }

    if (!bw_validate_signed_range((unsigned)count, value)) {
        return NULL;
    } else if (self->write_signed(self->bitstream, (unsigned)count, value)) {
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamAccumulator_unary(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    int stop_bit;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_unary(self->bitstream, stop_bit, value);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamAccumulator_write_huffman_code(bitstream_BitstreamAccumulator *self,
                                        PyObject *args)
{
    PyObject* huffman_tree_obj;
    bitstream_HuffmanTree* huffman_tree;
    int value;

    if (!PyArg_ParseTuple(args, "Oi", &huffman_tree_obj, &value))
        return NULL;

    if (Py_TYPE(huffman_tree_obj) != &bitstream_HuffmanTreeType) {
        PyErr_SetString(PyExc_TypeError, "argument must a HuffmanTree object");
        return NULL;
    }

    huffman_tree = (bitstream_HuffmanTree*)huffman_tree_obj;

    if (self->bitstream->write_huffman_code(self->bitstream,
                                            huffman_tree->bw_table,
                                            value)) {
        PyErr_SetString(PyExc_ValueError, "invalid HuffmanTree value");
        return NULL;
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamAccumulator_byte_align(bitstream_BitstreamAccumulator *self,
                                PyObject *args)
{
    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->byte_align(self->bitstream);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamAccumulator_byte_aligned(bitstream_BitstreamAccumulator *self,
                                  PyObject *args)
{
    return PyBool_FromLong(self->bitstream->byte_aligned(self->bitstream));
}

static PyObject*
BitstreamAccumulator_set_endianness(bitstream_BitstreamAccumulator *self,
                                    PyObject *args)
{
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

    if (little_endian) {
        self->write_unsigned = bwpy_write_unsigned_le;
        self->write_signed = bwpy_write_signed_le;
    } else {
        self->write_unsigned = bwpy_write_unsigned_be;
        self->write_signed = bwpy_write_signed_be;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write_bytes(bitstream_BitstreamAccumulator *self,
                                 PyObject *args)
{
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_bytes(self->bitstream,
                                     (uint8_t*)bytes, bytes_len);
        bw_etry(self->bitstream);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamAccumulator_build(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    char* format;
    PyObject *values;
    PyObject *iterator;

    if (!PyArg_ParseTuple(args, "sO", &format, &values)) {
        return NULL;
    } else if ((iterator = PyObject_GetIter(values)) == NULL) {
        return NULL;
    } else if (bitstream_build(self->bitstream,
                               self->write_unsigned,
                               self->write_signed,
                               format,
                               iterator)) {
        Py_DECREF(iterator);
        return NULL;
    } else {
        Py_DECREF(iterator);
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static PyObject*
BitstreamAccumulator_flush(bitstream_BitstreamAccumulator *self, PyObject *args)
{
    self->bitstream->flush(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_bits(bitstream_BitstreamAccumulator *self,
                          PyObject *args)
{
    return Py_BuildValue("I", self->bitstream->bits_written(self->bitstream));
}

static PyObject*
BitstreamAccumulator_bytes(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    return Py_BuildValue("I",
                         self->bitstream->bits_written(self->bitstream) / 8);
}

static PyObject*
BitstreamAccumulator_reset(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    self->bitstream->reset(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
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

PyObject*
bitstream_parse_func(PyObject *dummy, PyObject *args)
{
    char *format;
    int is_little_endian;
    char *data;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t data_length;
#else
    int data_length;
#endif

    if (!PyArg_ParseTuple(args, "sis#",
                          &format, &is_little_endian, &data, &data_length)) {
        return NULL;
    } else {
        struct bs_buffer* buf = buf_new();
        BitstreamReader* stream =
            br_open_buffer(buf,
                is_little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
        PyObject* values = PyList_New(0);
        buf_write(buf, (uint8_t*)data, (unsigned)data_length);
        if (!bitstream_parse(stream,
                             is_little_endian ?
                             brpy_read_unsigned_le : brpy_read_unsigned_be,
                             is_little_endian ?
                             brpy_read_signed_le : brpy_read_signed_be,
                             format,
                             values)) {
            stream->close(stream);
            buf_close(buf);
            return values;
        } else {
            stream->close(stream);
            buf_close(buf);
            Py_DECREF(values);
            return NULL;
        }
    }
}

PyObject*
bitstream_build_func(PyObject *dummy, PyObject *args)
{
    char *format;
    int is_little_endian;
    PyObject *values;
    PyObject *iterator;

    if (!PyArg_ParseTuple(args, "siO", &format, &is_little_endian, &values)) {
        return NULL;
    } else if ((iterator = PyObject_GetIter(values)) == NULL) {
        return NULL;
    } else {
        BitstreamWriter* stream;
        write_object_f write_unsigned;
        write_object_f write_signed;
        if (is_little_endian) {
            stream = bw_open_recorder(BS_LITTLE_ENDIAN);
            write_unsigned = bwpy_write_unsigned_le;
            write_signed = bwpy_write_signed_le;
        } else {
            stream = bw_open_recorder(BS_BIG_ENDIAN);
            write_unsigned = bwpy_write_unsigned_be;
            write_signed = bwpy_write_signed_be;
        }
        if (!bitstream_build(stream,
                             write_unsigned,
                             write_signed,
                             format,
                             iterator)) {
            PyObject* data = PyBytes_FromStringAndSize(
                (char *)buf_window_start(stream->output.buffer),
                (Py_ssize_t)buf_window_size(stream->output.buffer));
            stream->close(stream);
            Py_DECREF(iterator);
            return data;
        } else {
            stream->close(stream);
            Py_DECREF(iterator);
            return NULL;
        }
    }
}

int
bitstream_parse(BitstreamReader* stream,
                read_object_f read_unsigned,
                read_object_f read_signed,
                const char* format,
                PyObject* values)
{
    bs_instruction_t inst;

    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        if ((inst == BS_INST_UNSIGNED) ||
            (inst == BS_INST_UNSIGNED64)) {
            for (; times; times--) {
                PyObject *py_value = read_unsigned(stream, size);
                if (py_value != NULL) {
                    /*append read object to list*/
                    const int append_ok = PyList_Append(values, py_value);
                    Py_DECREF(py_value);
                    if (append_ok == -1) {
                        /*append error occurred*/
                        return 1;
                    }
                } else {
                    /*read error occurred*/
                    return 1;
                }
            }
        } else if ((inst == BS_INST_SIGNED) ||
                   (inst == BS_INST_SIGNED64)) {
            if (size == 0) {
                PyErr_SetString(PyExc_ValueError, "count must be > 0");
                return 1;
            }
            for (; times; times--) {
                PyObject *py_value = read_signed(stream, size);
                if (py_value != NULL) {
                    /*append read object to list*/
                    const int append_ok = PyList_Append(values, py_value);
                    Py_DECREF(py_value);
                    if (append_ok == -1) {
                        /*append error occurred*/
                        return 1;
                    }
                } else {
                    /*read error occurred*/
                    return 1;
                }
            }
        } else if (inst == BS_INST_SKIP) {
            if (!setjmp(*br_try(stream))) {
                for (; times; times--) {
                    stream->skip(stream, size);
                }
                br_etry(stream);
            } else {
                br_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error reading stream");
                return 1;
            }
        } else if (inst == BS_INST_SKIP_BYTES) {
            if (!setjmp(*br_try(stream))) {
                for (; times; times--) {
                    stream->skip_bytes(stream, size);
                }
                br_etry(stream);
            } else {
                br_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error reading stream");
                return 1;
            }
        } else if (inst == BS_INST_BYTES) {
            for (; times; times--) {
                PyObject *py_value = brpy_read_bytes(stream, size);
                if (py_value != NULL) {
                    const int append_ok = PyList_Append(values, py_value);
                    Py_DECREF(py_value);
                    if (append_ok == -1) {
                        /*append error occurred*/
                        return 1;
                    }
                } else {
                    /*read error occurred*/
                    return 1;
                }
            }
        } else if (inst == BS_INST_ALIGN) {
            stream->byte_align(stream);
        }
    } while (inst != BS_INST_EOF);

    return 0;
}

#define MISSING_VALUES "number of items is too short for format"

int
bitstream_build(BitstreamWriter* stream,
                write_object_f write_unsigned,
                write_object_f write_signed,
                const char* format,
                PyObject* iterator)
{
    bs_instruction_t inst;

    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);

        if ((inst == BS_INST_UNSIGNED) ||
            (inst == BS_INST_UNSIGNED64)) {
            PyObject *min_value = bwpy_min_unsigned(size);
            PyObject *max_value = bwpy_max_unsigned(size);
            for (; times; times--) {
                PyObject *py_value = PyIter_Next(iterator);
                if (py_value != NULL) {
                    /*ensure value is numeric and in the right range*/

                    int result;

                    if (!PyNumber_Check(py_value)) {
                        PyErr_SetString(PyExc_TypeError,
                                        "value is not a number");
                        Py_DECREF(py_value);
                        Py_DECREF(min_value);
                        Py_DECREF(max_value);
                        return 1;
                    }

                    if (!bwpy_in_range(min_value, py_value, max_value)) {
                        PyErr_Format(PyExc_ValueError,
                                     "value does not fit in %u unsigned %s",
                                     size,
                                     size != 1 ? "bits" : "bit");
                        Py_DECREF(py_value);
                        Py_DECREF(min_value);
                        Py_DECREF(max_value);
                        return 1;
                    }

                    result = write_unsigned(stream, size, py_value);
                    Py_DECREF(py_value);
                    if (result) {
                        Py_DECREF(min_value);
                        Py_DECREF(max_value);
                        return 1;
                    }
                } else {
                    if (!PyErr_Occurred()) {
                        /*iterator exhausted before values are consumed*/
                        PyErr_SetString(PyExc_IndexError, MISSING_VALUES);
                    }
                    Py_DECREF(min_value);
                    Py_DECREF(max_value);
                    return 1;
                }
            }
            Py_DECREF(min_value);
            Py_DECREF(max_value);
        } else if ((inst == BS_INST_SIGNED) ||
                   (inst == BS_INST_SIGNED64)) {
            PyObject *min_value = bwpy_min_signed(size);
            PyObject *max_value = bwpy_max_signed(size);

            if (size == 0) {
                PyErr_SetString(PyExc_ValueError, "size must be > 0");
                Py_DECREF(min_value);
                Py_DECREF(max_value);
                return 1;
            }
            for (; times; times--) {
                PyObject *py_value = PyIter_Next(iterator);
                if (py_value != NULL) {
                    /*ensure value is numeric and in the right range*/

                    int result;

                    if (!PyNumber_Check(py_value)) {
                        PyErr_SetString(PyExc_TypeError,
                                        "value is not a number");
                        Py_DECREF(py_value);
                        Py_DECREF(min_value);
                        Py_DECREF(max_value);
                        return 1;
                    }

                    if (!bwpy_in_range(min_value, py_value, max_value)) {
                        PyErr_Format(PyExc_ValueError,
                                     "value does not fit in %u signed bits",
                                     size);
                        Py_DECREF(py_value);
                        Py_DECREF(min_value);
                        Py_DECREF(max_value);
                        return 1;
                    }

                    result = write_signed(stream, size, py_value);
                    Py_DECREF(py_value);
                    if (result) {
                        Py_DECREF(min_value);
                        Py_DECREF(max_value);
                        return 1;
                    }
                } else {
                    if (!PyErr_Occurred()) {
                        /*iterator exhausted before values are consumed*/
                        PyErr_SetString(PyExc_IndexError, MISSING_VALUES);
                    }
                    Py_DECREF(min_value);
                    Py_DECREF(max_value);
                    return 1;
                }
            }
            Py_DECREF(min_value);
            Py_DECREF(max_value);
        } else if (inst == BS_INST_SKIP) {
            if (!setjmp(*bw_try(stream))) {
                for (; times; times--) {
                    stream->write(stream, size, 0);
                }
                bw_etry(stream);
            } else {
                bw_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
                return 1;
            }
        } else if (inst == BS_INST_SKIP_BYTES) {
            if (!setjmp(*bw_try(stream))) {
                for (; times; times--) {
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                    stream->write(stream, size, 0);
                }
                bw_etry(stream);
            } else {
                bw_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
                return 1;
            }
        } else if (inst == BS_INST_BYTES) {
            if (!setjmp(*bw_try(stream))) {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    if (py_value != NULL) {
                        char *bytes;
                        Py_ssize_t bytes_len;

                        if (PyBytes_AsStringAndSize(py_value,
                                                    &bytes,
                                                    &bytes_len) != -1) {
                            if (size <= bytes_len) {
                                /*ensure py_value gets DECREFed
                                  especially if a write error occurs*/

                                if (!setjmp(*bw_try(stream))) {
                                    stream->write_bytes(stream,
                                                        (uint8_t*)bytes,
                                                        (unsigned)size);
                                    Py_DECREF(py_value);
                                    bw_etry(stream);
                                } else {
                                    Py_DECREF(py_value);
                                    bw_etry(stream);
                                    bw_abort(stream);
                                }
                            } else {
                                PyErr_SetString(PyExc_ValueError,
                                                "string length too short");
                                Py_DECREF(py_value);
                                bw_etry(stream);
                                return 1;
                            }
                        } else {
                            Py_DECREF(py_value);
                            bw_etry(stream);
                            return 1;
                        }
                    } else {
                        if (!PyErr_Occurred()) {
                            PyErr_SetString(PyExc_IndexError, MISSING_VALUES);
                        }
                        bw_etry(stream);
                        return 1;
                    }
                }
                bw_etry(stream);
            } else {
                bw_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
                return 1;
            }
        } else if (inst == BS_INST_ALIGN) {
            if (!setjmp(*bw_try(stream))) {
                stream->byte_align(stream);
                bw_etry(stream);
            } else {
                bw_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
                return 1;
            }

        }
    } while (inst != BS_INST_EOF);

    return 0;
}
