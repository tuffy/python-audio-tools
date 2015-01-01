#include <Python.h>
#include "mod_defs.h"
#include "bitstream.h"
#include "huffman.h"
#include "buffer.h"
#include "mod_bitstream.h"

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

    bitstream_BitstreamReaderPositionType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamReaderPositionType) < 0)
        return MOD_ERROR_VAL;

    bitstream_BitstreamWriterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamWriterType) < 0)
        return MOD_ERROR_VAL;

    bitstream_BitstreamRecorderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamRecorderType) < 0)
        return MOD_ERROR_VAL;

    bitstream_BitstreamWriterPositionType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamWriterPositionType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&bitstream_BitstreamReaderType);
    PyModule_AddObject(m, "BitstreamReader",
                       (PyObject *)&bitstream_BitstreamReaderType);

    Py_INCREF(&bitstream_HuffmanTreeType);
    PyModule_AddObject(m, "HuffmanTree",
                       (PyObject *)&bitstream_HuffmanTreeType);

    Py_INCREF(&bitstream_BitstreamReaderPositionType);
    PyModule_AddObject(m, "BitstreamReaderPosition",
                       (PyObject *)&bitstream_BitstreamReaderPositionType);

    Py_INCREF(&bitstream_BitstreamWriterType);
    PyModule_AddObject(m, "BitstreamWriter",
                       (PyObject *)&bitstream_BitstreamWriterType);

    Py_INCREF(&bitstream_BitstreamRecorderType);
    PyModule_AddObject(m, "BitstreamRecorder",
                       (PyObject *)&bitstream_BitstreamRecorderType);

    Py_INCREF(&bitstream_BitstreamWriterPositionType);
    PyModule_AddObject(m, "BitstreamWriterPosition",
                       (PyObject *)&bitstream_BitstreamWriterPositionType);

    return MOD_SUCCESS_VAL(m);
}

static PyObject*
brpy_read_unsigned(BitstreamReader *br, unsigned bits)
{
    if (!setjmp(*br_try(br))) {
        if (bits <= (sizeof(unsigned int) * 8)) {
            /*if bits are small enough, first try regular read*/
            const unsigned result = br->read(br, bits);
            br_etry(br);
            return Py_BuildValue("I", result);
        } else if (bits <= (sizeof(uint64_t) * 8)) {
            /*or try read_64*/
            const uint64_t result = br->read_64(br, bits);
            br_etry(br);
            return Py_BuildValue("K", result);
        } else {
            /*finally, try read_bigint*/
            mpz_t result;
            char *result_str;
            PyObject *result_obj;

            mpz_init(result);

            /*perform read*/
            if (!setjmp(*br_try(br))) {
                br->read_bigint(br, bits, result);
                br_etry(br);
            } else {
                /*ensure result gets cleared before re-raising error*/
                br_etry(br);
                mpz_clear(result);
                br_abort(br);
            }

            br_etry(br);

            /*serialize result as string*/
            result_str = mpz_get_str(NULL, 10, result);
            mpz_clear(result);

            /*convert to Python long*/
            result_obj = PyLong_FromString(result_str, NULL, 10);
            free(result_str);

            /*return result*/
            return result_obj;
        }
    } else {
        br_etry(br);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
brpy_read_signed(BitstreamReader *br, unsigned bits)
{
    if (!setjmp(*br_try(br))) {
        if (bits <= (sizeof(int) * 8)) {
            /*if bits are small enough, first try regular read*/
            const int result = br->read_signed(br, bits);
            br_etry(br);
            return Py_BuildValue("i", result);
        } else if (bits <= (sizeof(uint64_t) * 8)) {
            /*or try read_64*/
            const int64_t result = br->read_signed_64(br, bits);
            br_etry(br);
            return Py_BuildValue("L", result);
        } else {
            /*finally, try read_signed_bigint*/

            mpz_t result;
            char *result_str;
            PyObject *result_obj;

            mpz_init(result);

            if (!setjmp(*br_try(br))) {
                br->read_signed_bigint(br, bits, result);
                br_etry(br);
            } else {
                /*ensure result gets cleared before re-raising error*/
                br_etry(br);
                mpz_clear(result);
                br_abort(br);
            }

            br_etry(br);

            /*serialize result as string*/
            result_str = mpz_get_str(NULL, 10, result);
            mpz_clear(result);

            /*convert to Python long*/
            result_obj = PyLong_FromString(result_str, NULL, 10);
            free(result_str);

            /*return result*/
            return result_obj;
        }
    } else {
        br_etry(br);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
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

    return brpy_read_unsigned(self->bitstream, (unsigned)count);
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

    return brpy_read_signed(self->bitstream, (unsigned)count);
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

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->unread(self->bitstream, unread_bit);
        br_etry(self->bitstream);

        Py_INCREF(Py_None);
        return Py_None;
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error unreading bit");
        return NULL;
    }
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
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    switch (little_endian) {
    case 0:
        self->bitstream->set_endianness(self->bitstream, BS_BIG_ENDIAN);
        Py_INCREF(Py_None);
        return Py_None;
    case 1:
        self->bitstream->set_endianness(self->bitstream, BS_LITTLE_ENDIAN);
        Py_INCREF(Py_None);
        return Py_None;
    default:
        PyErr_SetString(
            PyExc_ValueError,
            "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }
}

static PyObject*
BitstreamReader_close(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_getpos(bitstream_BitstreamReader *self, PyObject *args)
{
    return PyObject_CallFunction(
        (PyObject*)&bitstream_BitstreamReaderPositionType, "O", self);
}

static PyObject*
BitstreamReader_setpos(bitstream_BitstreamReader *self, PyObject *args)
{
    bitstream_BitstreamReaderPosition* pos_obj;

    if (!PyArg_ParseTuple(args, "O!",
                          &bitstream_BitstreamReaderPositionType,
                          &pos_obj))
        return NULL;

    /*ensure position has come from this reader*/
    if (pos_obj->pos->reader != self->bitstream) {
        PyErr_SetString(PyExc_IOError,
                        "position is not from this BitstreamReader");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->setpos(self->bitstream, pos_obj->pos);
        br_etry(self->bitstream);

        Py_INCREF(Py_None);
        return Py_None;
    } else {
        /*raise IOError if some problem occurs setting the position*/
        br_etry(self->bitstream);

        PyErr_SetString(PyExc_IOError, "unable to set position");
        return NULL;
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
                PyErr_SetString(PyExc_IOError,
                                "I/O error performing seek");
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
                    PyErr_SetString(PyExc_IOError,
                                    "I/O error performing seek");
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
BitstreamReader_substream(bitstream_BitstreamReader *self, PyObject *args)
{
    PyTypeObject *type = Py_TYPE(self);
    long int bytes;

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

    if (!setjmp(*br_try(self->bitstream))) {
        bitstream_BitstreamReader *obj;
        BitstreamReader *substream =
            self->bitstream->substream(self->bitstream, (unsigned)bytes);

        br_etry(self->bitstream);

        obj = (bitstream_BitstreamReader *)type->tp_alloc(type, 0);
        obj->bitstream = substream;
        return (PyObject *)obj;
    } else {
        br_etry(self->bitstream);
        /*read error occurred during substream_append*/
        PyErr_SetString(PyExc_IOError, "I/O error creating substream");
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
    int little_endian;
    int buffer_size = 4096;

    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "Oi|i",
                          &file_obj,
                          &little_endian,
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

        /*FIXME - this presumes buffer can holder more bytes than
          an unsigned int, which isn't the case yet*/
        self->bitstream = br_open_buffer((uint8_t*)buffer,
                                         (unsigned)length,
                                         little_endian ?
                                         BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    } else {
        /*store a reference to the Python object so that it doesn't decref
          (and close) the file out from under us*/
        Py_INCREF(file_obj);

        self->bitstream = br_open_external(
            file_obj,
            little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
            (unsigned)buffer_size,
            (ext_read_f)br_read_python,
            (ext_setpos_f)bs_setpos_python,
            (ext_getpos_f)bs_getpos_python,
            (ext_free_pos_f)bs_free_pos_python,
            (ext_seek_f)bs_fseek_python,
            (ext_close_f)bs_close_python,
            (ext_free_f)bs_free_python_decref);
    }

    return 0;
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

    Py_TYPE(self)->tp_free((PyObject*)self);
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

static PyObject*
BitstreamReaderPosition_new(PyTypeObject *type, PyObject *args,
                            PyObject *kwds)
{
    bitstream_BitstreamReaderPosition *self;

    self = (bitstream_BitstreamReaderPosition *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamReaderPosition_init(bitstream_BitstreamReaderPosition *self,
                             PyObject *args)
{
    bitstream_BitstreamReader *reader_obj;
    BitstreamReader *reader;
    self->pos = NULL;

    if (PyArg_ParseTuple(args, "O!",
                         &bitstream_BitstreamReaderType,
                         &reader_obj)) {
        reader = reader_obj->bitstream;
    } else {
        return -1;
    }

    /*get position from reader*/
    if (!setjmp(*br_try(reader))) {
        self->pos = reader->getpos(reader);
        br_etry(reader);
        return 0;
    } else {
        /*some I/O error occurred getting position*/
        br_etry(reader);
        PyErr_SetString(PyExc_IOError, "I/O error getting position");
        return -1;
    }
}

void
BitstreamReaderPosition_dealloc(bitstream_BitstreamReaderPosition *self)
{
    /*since the position contains a copy of the "free" function
      needed to free the object returned by getpos,
      this position object can be safely freed after its parent reader*/
    if (self->pos) {
        self->pos->del(self->pos);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
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

    return 0;
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
    if (cmp_min == -1) {
        return -1;
    } else {
        const int cmp_max = PyObject_RichCompareBool(value, max_value, Py_LE);
        if (cmp_max == -1) {
            return -1;
        } else {
            return (cmp_min == 1) && (cmp_max == 1);
        }
    }
}

#define FUNC_VALIDATE_RANGE(FUNC_NAME, MIN_FUNC, MAX_FUNC, TYPE_STR) \
static int                                                           \
FUNC_NAME(unsigned bits, PyObject *value) {                          \
    PyObject *min_value;                                             \
    PyObject *max_value;                                             \
    int comparison;                                                  \
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
    comparison = bwpy_in_range(min_value, value, max_value);         \
    Py_DECREF(min_value);                                            \
    Py_DECREF(max_value);                                            \
                                                                     \
    switch (comparison) {                                            \
    case 1:                                                          \
        return 1;                                                    \
    case 0:                                                          \
        PyErr_Format(PyExc_ValueError,                               \
                     "value does not fit in %u " TYPE_STR " %s",     \
                     bits,                                           \
                     bits != 1 ? "bits" : "bit");                    \
        return 0;                                                    \
    default:                                                         \
        return 0;                                                    \
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
bwpy_write_unsigned(BitstreamWriter *bw, unsigned bits, PyObject *value)
{
    if (bits == 0) {
        /*do nothing*/
        return 0;
    }
    if (!bw_validate_unsigned_range(bits, value)) {
        return 1;
    }

    if (!setjmp(*bw_try(bw))) {
        if (bits <= (sizeof(unsigned int) * 8)) {
            /*value should fit in an unsigned int*/
            PyObject *long_obj = PyNumber_Long(value);
            if (long_obj) {
                const unsigned long u_value = PyLong_AsUnsignedLong(long_obj);
                Py_DECREF(long_obj);
                bw->write(bw, bits, (unsigned)u_value);
                bw_etry(bw);
                return 0;
            } else {
                bw_etry(bw);
                return 1;
            }
        } else if (bits <= (sizeof(uint64_t) * 8)) {
            /*value should fit in a uint64_t*/
            PyObject *long_obj = PyNumber_Long(value);
            if (long_obj) {
                const unsigned long long u_value =
                    PyLong_AsUnsignedLongLong(long_obj);
                Py_DECREF(long_obj);
                bw->write_64(bw, bits, (uint64_t)u_value);
                bw_etry(bw);
                return 0;
            } else {
                bw_etry(bw);
                return 1;
            }
        } else {
            /*finally, try write_bigint*/

            /*serialize long to string*/
            PyObject *string_obj = PyNumber_ToBase(value, 10);

            /*convert to mpz_t*/
            mpz_t value;
#if PY_MAJOR_VERSION >= 3
            /*I hope this is NULL-terminated
              since the documentation doesn't say*/
            mpz_init_set_str(value, PyUnicode_AsUTF8(string_obj), 10);
#else
            mpz_init_set_str(value, PyString_AsString(string_obj), 10);
#endif
            Py_DECREF(string_obj);

            /*perform write*/
            if (!setjmp(*bw_try(bw))) {
                bw->write_bigint(bw, bits, value);
                bw_etry(bw);
                mpz_clear(value);
            } else {
                /*ensure result gets cleared before re-raising error*/
                bw_etry(bw);
                mpz_clear(value);
                bw_abort(bw);
            }

            /*return sucess*/
            bw_etry(bw);
            return 0;
        }
    } else {
        bw_etry(bw);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return 1;
    }
}

static int
bwpy_write_signed(BitstreamWriter *bw, unsigned bits, PyObject *value)
{
    /*ensure value fits in range*/
    if (!bw_validate_signed_range(bits, value))
        return 1;

    if (!setjmp(*bw_try(bw))) {
        if (bits <= (sizeof(int) * 8)) {
            /*value should fit in a signed int*/
            const long i_value = PyInt_AsLong(value);
            bw->write_signed(bw, bits, (int)i_value);
            bw_etry(bw);
            return 0;
        } else if (bits <= (sizeof(int64_t) * 8)) {
            /*value should fit in an int64_t*/
            const long long i_value = PyLong_AsLongLong(value);
            bw->write_signed_64(bw, bits, (int64_t)i_value);
            bw_etry(bw);
            return 0;
        } else {
            /*finally, try write_signed_bigint*/

            /*serialize long to string*/
            PyObject *string_obj = PyNumber_ToBase(value, 10);

            /*convert to mpz_t*/
            mpz_t value;
#if PY_MAJOR_VERSION >= 3
            /*I hope this is NULL-terminated
              since the documentation doesn't say*/
            mpz_init_set_str(value, PyUnicode_AsUTF8(string_obj), 10);
#else
            mpz_init_set_str(value, PyString_AsString(string_obj), 10);
#endif
            Py_DECREF(string_obj);

            /*perform write*/
            if (!setjmp(*bw_try(bw))) {
                bw->write_signed_bigint(bw, bits, value);
                bw_etry(bw);
                mpz_clear(value);
            } else {
                /*ensure result gets cleared before re-raising error*/
                bw_etry(bw);
                mpz_clear(value);
                bw_abort(bw);
            }

            /*return sucess*/
            bw_etry(bw);
            return 0;
        }
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
    } else if (bwpy_write_unsigned(self->bitstream, (unsigned)count, value)) {
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

    if (bwpy_write_signed(self->bitstream, (unsigned)count, value)) {
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
    bitstream_HuffmanTree* huffman_tree;
    int value;
    BitstreamWriter* writer = self->bitstream;

    if (!PyArg_ParseTuple(args, "O!i",
                          &bitstream_HuffmanTreeType,
                          &huffman_tree,
                          &value))
        return NULL;

    if (!setjmp(*bw_try(writer))) {
        const int result = writer->write_huffman_code(
            writer, huffman_tree->bw_table, value);

        bw_etry(writer);

        if (result) {
            PyErr_SetString(PyExc_ValueError, "invalid HuffmanTree value");
            return NULL;
        } else {
            Py_INCREF(Py_None);
            return Py_None;
        }
    } else {
        bw_etry(writer);
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
BitstreamWriter_set_endianness(bitstream_BitstreamWriter *self,
                               PyObject *args)
{
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    switch (little_endian) {
    case 0:
        self->bitstream->set_endianness(self->bitstream, BS_BIG_ENDIAN);
        Py_INCREF(Py_None);
        return Py_None;
    case 1:
        self->bitstream->set_endianness(self->bitstream, BS_LITTLE_ENDIAN);
        Py_INCREF(Py_None);
        return Py_None;
    default:
        PyErr_SetString(
            PyExc_ValueError,
            "endianness must be 0 (big-endian) or 1 (little-endian)");
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
BitstreamWriter_getpos(bitstream_BitstreamWriter *self,
                       PyObject *args)
{
    return PyObject_CallFunction(
        (PyObject*)&bitstream_BitstreamWriterPositionType, "O", self);
}

static PyObject*
BitstreamWriter_setpos(bitstream_BitstreamWriter *self,
                       PyObject *args)
{
    bitstream_BitstreamWriterPosition* pos_obj;

    if (!PyArg_ParseTuple(args, "O!",
                          &bitstream_BitstreamWriterPositionType,
                          &pos_obj))
        return NULL;

    /*ensure position has come from this reader*/
    if (pos_obj->pos->writer != self->bitstream) {
        PyErr_SetString(PyExc_IOError,
                        "position is not from this BitstreamWriter");
        return NULL;
    }

    /*ensure stream is byte-aligned before setting position*/
    if (!self->bitstream->byte_aligned(self->bitstream)) {
        PyErr_SetString(PyExc_IOError, "stream must be byte-aligned");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->setpos(self->bitstream, pos_obj->pos);
        bw_etry(self->bitstream);

        Py_INCREF(Py_None);
        return Py_None;
    } else {
        /*raise IOError if some problem occurs setting the position*/
        bw_etry(self->bitstream);

        PyErr_SetString(PyExc_IOError, "unable to set position");
        return NULL;
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
    } else if (bwpy_write_unsigned((BitstreamWriter*)self->bitstream,
                                   (unsigned)count,
                                   value)) {
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


    if (bwpy_write_signed((BitstreamWriter*)self->bitstream,
                          (unsigned)count,
                          value)) {
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
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    int stop_bit;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &stop_bit, &value))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }

    /*recorders can fail to write if the stream is closed*/
    if (!setjmp(*bw_try(writer))) {
        writer->write_unary(writer, stop_bit, value);
        bw_etry(writer);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_write_huffman_code(bitstream_BitstreamRecorder *self,
                                     PyObject *args)
{
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    bitstream_HuffmanTree* huffman_tree;
    int value;

    if (!PyArg_ParseTuple(args, "O!i",
                          &bitstream_HuffmanTreeType,
                          &huffman_tree,
                          &value))
        return NULL;

    /*recorders can fail to write if the stream is closed*/
    if (!setjmp(*bw_try(writer))) {
        const int result = writer->write_huffman_code(
            writer, huffman_tree->bw_table, value);

        bw_etry(writer);

        if (result) {
            PyErr_SetString(PyExc_ValueError, "invalid HuffmanTree value");
            return NULL;
        } else {
            Py_INCREF(Py_None);
            return Py_None;
        }
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_byte_align(bitstream_BitstreamRecorder *self,
                             PyObject *args)
{
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;

    /*recorders can fail to write if the stream is closed*/
    if (!setjmp(*bw_try(writer))) {
        writer->byte_align(writer);
        bw_etry(writer);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_byte_aligned(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    return PyBool_FromLong(
        self->bitstream->byte_aligned((BitstreamWriter*)self->bitstream));
}

static PyObject*
BitstreamRecorder_write_bytes(bitstream_BitstreamRecorder *self,
                              PyObject *args)
{
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    const char* bytes;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t bytes_len;
#else
    int bytes_len;
#endif

    if (!PyArg_ParseTuple(args, "s#", &bytes, &bytes_len))
        return NULL;

    /*writers can fail to write if the stream is closed*/
    if (!setjmp(*bw_try(writer))) {
        writer->write_bytes(writer, (uint8_t*)bytes, bytes_len);
        bw_etry(writer);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(writer);
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
    } else if (bitstream_build((BitstreamWriter*)self->bitstream,
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
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    /*flush may fail if stream is closed*/
    if (!setjmp(*bw_try(writer))) {
        writer->flush(writer);
        bw_etry(writer);
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error writing stream");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_set_endianness(bitstream_BitstreamRecorder *self,
                                 PyObject *args)
{
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    switch (little_endian) {
    case 0:
        writer->set_endianness(writer, BS_BIG_ENDIAN);
        Py_INCREF(Py_None);
        return Py_None;
    case 1:
        writer->set_endianness(writer, BS_LITTLE_ENDIAN);
        Py_INCREF(Py_None);
        return Py_None;
    default:
        PyErr_SetString(
            PyExc_ValueError,
            "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }
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
    BitstreamRecorder* recorder = self->bitstream;

    return PyBytes_FromStringAndSize(
        (char*)recorder->data(recorder),
        (Py_ssize_t)recorder->bytes_written(recorder));
}

static PyObject*
BitstreamRecorder_swap(bitstream_BitstreamRecorder *self,
                       PyObject *args)
{
    bitstream_BitstreamRecorder *to_swap;

    if (!PyArg_ParseTuple(args, "O!",
                          &bitstream_BitstreamRecorderType, &to_swap))
        return NULL;

    recorder_swap(&(to_swap->bitstream), &(self->bitstream));

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
    if (Py_TYPE(writer) == &bitstream_BitstreamWriterType) {
        bitstream_BitstreamWriter* writer_obj =
            (bitstream_BitstreamWriter*)writer;
        return writer_obj->bitstream;
    } else if (Py_TYPE(writer) == &bitstream_BitstreamRecorderType) {
        bitstream_BitstreamRecorder* recorder_obj =
            (bitstream_BitstreamRecorder*)writer;
        return (BitstreamWriter*)recorder_obj->bitstream;
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
        if (!setjmp(*bw_try((BitstreamWriter*)self->bitstream))) {
            self->bitstream->copy(self->bitstream, target);
            bw_etry((BitstreamWriter*)self->bitstream);
            Py_INCREF(Py_None);
            return Py_None;
        } else {
            bw_etry((BitstreamWriter*)self->bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error writing stream");
            return NULL;
        }
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "argument must be a "
                        "BitstreamWriter or BitstreamRecorder");
        return NULL;
    }
}

static PyObject*
BitstreamRecorder_add_callback(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    BitstreamWriter *writer = (BitstreamWriter*)self->bitstream;
    PyObject* callback;

    if (!PyArg_ParseTuple(args, "O", &callback))
        return NULL;

    if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "callback must be callable");
        return NULL;
    }

    Py_INCREF(callback);
    writer->add_callback(writer,
                         (bs_callback_f)BitstreamWriter_callback,
                         callback);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_pop_callback(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    struct bs_callback callback;
    PyObject* callback_obj;

    if (writer->callbacks != NULL) {
        writer->pop_callback(writer, &callback);
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
    BitstreamWriter* writer = (BitstreamWriter*)self->bitstream;
    uint8_t byte;

    if (!PyArg_ParseTuple(args, "b", &byte))
        return NULL;

    writer->call_callbacks(writer, byte);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_getpos(bitstream_BitstreamRecorder *self,
                         PyObject *args)
{
    return PyObject_CallFunction(
        (PyObject*)&bitstream_BitstreamWriterPositionType, "O", self);
}

static PyObject*
BitstreamRecorder_setpos(bitstream_BitstreamRecorder *self,
                         PyObject *args)
{
    bitstream_BitstreamWriterPosition* pos_obj;
    BitstreamWriter *writer = (BitstreamWriter*)self->bitstream;

    if (!PyArg_ParseTuple(args, "O!",
                          &bitstream_BitstreamWriterPositionType,
                          &pos_obj))
        return NULL;

    /*ensure position has come from this reader*/
    if (pos_obj->pos->writer != writer) {
        PyErr_SetString(PyExc_IOError,
                        "position is not from this BitstreamWriter");
        return NULL;
    }

    /*ensure stream is byte-aligned before setting position*/
    if (!writer->byte_aligned(writer)) {
        PyErr_SetString(PyExc_IOError, "stream must be byte-aligned");
        return NULL;
    }

    if (!setjmp(*bw_try(writer))) {
        writer->setpos(writer, pos_obj->pos);
        bw_etry(writer);

        Py_INCREF(Py_None);
        return Py_None;
    } else {
        /*raise IOError if some problem occurs setting the position*/
        bw_etry(writer);

        PyErr_SetString(PyExc_IOError, "unable to set position");
        return NULL;
    }
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

static PyObject*
BitstreamWriterPosition_new(PyTypeObject *type, PyObject *args,
                            PyObject *kwds)
{
    bitstream_BitstreamWriterPosition *self;

    self = (bitstream_BitstreamWriterPosition *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamWriterPosition_init(bitstream_BitstreamWriterPosition *self,
                             PyObject *args)
{
    PyObject *writer_obj;
    BitstreamWriter *writer;

    self->pos = NULL;

    if (!PyArg_ParseTuple(args, "O", &writer_obj))
        return -1;
    if ((writer = internal_writer(writer_obj)) == NULL) {
        PyErr_SetString(
            PyExc_TypeError,
            "argument must be BitstreamWriter or BitstreamRecorder");
        return -1;
    }
    if (!writer->byte_aligned(writer)) {
        PyErr_SetString(PyExc_IOError, "stream must be byte-aligned");
        return -1;
    }
    if (!setjmp(*bw_try(writer))) {
        self->pos = writer->getpos(writer);
        bw_etry(writer);
        return 0;
    } else {
        bw_etry(writer);
        PyErr_SetString(PyExc_IOError, "I/O error getting current position");
        return -1;
    }
}

void
BitstreamWriterPosition_dealloc(bitstream_BitstreamWriterPosition *self)
{
    /*since the position contains a copy of the "free" function
      needed to free the object returned by getpos,
      this position object can be safely freed after its parent reader*/
    if (self->pos) {
        self->pos->del(self->pos);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
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
        BitstreamReader* stream =
            br_open_buffer(
                (uint8_t*)data,
                (unsigned)data_length,
                is_little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
        PyObject* values = PyList_New(0);
        if (!bitstream_parse(stream, format, values)) {
            stream->close(stream);
            return values;
        } else {
            stream->close(stream);
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
        BitstreamRecorder* stream;
        if (is_little_endian) {
            stream = bw_open_recorder(BS_LITTLE_ENDIAN);
        } else {
            stream = bw_open_recorder(BS_BIG_ENDIAN);
        }
        if (!bitstream_build((BitstreamWriter*)stream,
                             format,
                             iterator)) {
            PyObject* data = PyBytes_FromStringAndSize(
                (char *)stream->data(stream),
                (Py_ssize_t)stream->bytes_written(stream));
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
                const char* format,
                PyObject* values)
{
    bs_instruction_t inst;

    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        switch (inst) {
        case BS_INST_UNSIGNED:
        case BS_INST_UNSIGNED64:
        case BS_INST_UNSIGNED_BIGINT:
            for (; times; times--) {
                PyObject *py_value = brpy_read_unsigned(stream, size);
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
            break;
        case BS_INST_SIGNED:
        case BS_INST_SIGNED64:
        case BS_INST_SIGNED_BIGINT:
            if (size == 0) {
                PyErr_SetString(PyExc_ValueError, "count must be > 0");
                return 1;
            }
            for (; times; times--) {
                PyObject *py_value = brpy_read_signed(stream, size);
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
            break;
        case BS_INST_SKIP:
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
            break;
        case BS_INST_SKIP_BYTES:
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
            break;
        case BS_INST_BYTES:
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
            break;
        case BS_INST_ALIGN:
            stream->byte_align(stream);
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);

    return 0;
}

#define MISSING_VALUES "number of items is too short for format"

int
bitstream_build(BitstreamWriter* stream,
                const char* format,
                PyObject* iterator)
{
    bs_instruction_t inst;

    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        switch (inst) {
        case BS_INST_UNSIGNED:
        case BS_INST_UNSIGNED64:
        case BS_INST_UNSIGNED_BIGINT:
            {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    int result;

                    if (py_value == NULL) {
                        /*either iterator exhausted or error*/

                        if (!PyErr_Occurred()) {
                            /*iterator exhausted before values are consumed*/
                            PyErr_SetString(PyExc_IndexError,
                                            MISSING_VALUES);
                        }
                        return 1;
                    }

                    /*perform actual write*/
                    result = bwpy_write_unsigned(stream, size, py_value);
                    Py_DECREF(py_value);
                    if (result) {
                        return 1;
                    }
                }
            }
            break;
        case BS_INST_SIGNED:
        case BS_INST_SIGNED64:
        case BS_INST_SIGNED_BIGINT:
            {
                if (size == 0) {
                    PyErr_SetString(PyExc_ValueError, "size must be > 0");
                    return 1;
                }
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    int result;

                    if (py_value == NULL) {
                        /*either iterator exhausted or error*/

                        if (!PyErr_Occurred()) {
                            /*iterator exhausted before values are consumed*/
                            PyErr_SetString(PyExc_IndexError,
                                            MISSING_VALUES);
                        }
                        return 1;
                    }

                    /*ensure value is numeric*/
                    if (!PyNumber_Check(py_value)) {
                        PyErr_SetString(PyExc_TypeError,
                                        "value is not a number");
                        Py_DECREF(py_value);
                        return 1;
                    }

                    /*perform actual write*/
                    result = bwpy_write_signed(stream, size, py_value);
                    Py_DECREF(py_value);
                    if (result) {
                        return 1;
                    }
                }
            }
            break;
        case BS_INST_SKIP:
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
            break;
        case BS_INST_SKIP_BYTES:
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
            break;
        case BS_INST_BYTES:
            for (; times; times--) {
                PyObject *py_value = PyIter_Next(iterator);
                char *bytes;
                Py_ssize_t bytes_len;

                if (py_value == NULL) {
                    /*either iterator exhausted or error*/

                    if (!PyErr_Occurred()) {
                        /*iterator exhausted before values are consumed*/
                        PyErr_SetString(PyExc_IndexError, MISSING_VALUES);
                    }
                    bw_etry(stream);
                    return 1;
                }

                if (PyBytes_AsStringAndSize(py_value,
                                            &bytes,
                                            &bytes_len) == -1) {
                    /*some error converting object to bytes*/
                    Py_DECREF(py_value);
                    return 1;
                }

                if (bytes_len < size) {
                    /*bytes from iterator are too short
                      compared to size in format string*/
                    PyErr_SetString(PyExc_ValueError,
                                    "string length too short");
                    Py_DECREF(py_value);
                    return 1;
                }

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
                    PyErr_SetString(PyExc_ValueError,
                                    "I/O error writing to stream");
                    return 1;
                }
            }
            break;
        case BS_INST_ALIGN:
            if (!setjmp(*bw_try(stream))) {
                stream->byte_align(stream);
                bw_etry(stream);
            } else {
                bw_etry(stream);
                PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
                return 1;
            }
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);

    return 0;
}
