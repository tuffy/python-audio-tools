#include <Python.h>
#include "bitstream.h"
#include "huffman.h"
#include "mod_bitstream.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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
initbitstream(void)
{
    PyObject* m;

    bitstream_BitstreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamReaderType) < 0)
        return;

    bitstream_HuffmanTreeType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_HuffmanTreeType) < 0)
        return;

    bitstream_BitstreamWriterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamWriterType) < 0)
        return;

    bitstream_BitstreamRecorderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamRecorderType) < 0)
        return;

    bitstream_BitstreamAccumulatorType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitstreamAccumulatorType) < 0)
        return;

    m = Py_InitModule3("bitstream", module_methods,
                       "A bitstream handling module");

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
}

static PyObject*
BitstreamReader_read(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;
    unsigned int result;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read(self->bitstream, (unsigned)count);
        br_etry(self->bitstream);
        return Py_BuildValue("I", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_read64(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;
    uint64_t result;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_64(self->bitstream, (unsigned)count);
        br_etry(self->bitstream);
        return Py_BuildValue("K", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
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
    int count;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "byte count must be >= 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->skip_bytes(self->bitstream, (unsigned)count);
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
BitstreamReader_byte_align(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
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
BitstreamReader_read_signed(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;
    int result;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_signed(self->bitstream,
                                              (unsigned)count);
        br_etry(self->bitstream);
        return Py_BuildValue("i", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_read_signed64(bitstream_BitstreamReader *self, PyObject *args)
{
    int count;
    int64_t result;

    if (!PyArg_ParseTuple(args, "i", &count)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_signed_64(self->bitstream,
                                                 (unsigned)count);
        br_etry(self->bitstream);
        return Py_BuildValue("L", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
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
BitstreamReader_limited_unary(bitstream_BitstreamReader *self, PyObject *args)
{
    int stop_bit;
    int maximum_bits;
    int result;

    if (!PyArg_ParseTuple(args, "ii", &stop_bit, &maximum_bits))
        return NULL;

    if ((stop_bit != 0) && (stop_bit != 1)) {
        PyErr_SetString(PyExc_ValueError, "stop bit must be 0 or 1");
        return NULL;
    }
    if (maximum_bits < 1) {
        PyErr_SetString(PyExc_ValueError,
                        "maximum bits must be greater than 0");
        return NULL;
    }

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_limited_unary(self->bitstream,
                                                     stop_bit,
                                                     maximum_bits);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }

    br_etry(self->bitstream);
    if (result >= 0) {
        return Py_BuildValue("i", result);
    } else {
        Py_INCREF(Py_None);
        return Py_None;
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

    if (huffman_tree_obj->ob_type != &bitstream_HuffmanTreeType) {
        PyErr_SetString(PyExc_TypeError, "argument must a HuffmanTree object");
        return NULL;
    }

    huffman_tree = (bitstream_HuffmanTree*)huffman_tree_obj;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_huffman_code(self->bitstream,
                                                    *(huffman_tree->br_table));

        br_etry(self->bitstream);
        return Py_BuildValue("i", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

#define BUFFER_SIZE 4096

static PyObject*
BitstreamReader_read_bytes(bitstream_BitstreamReader *self,
                           PyObject *args)
{
    int byte_count;


    if (!PyArg_ParseTuple(args, "i", &byte_count)) {
        return NULL;
    } else if (byte_count < 0) {
        PyErr_SetString(PyExc_ValueError, "byte count must be >= 0");
        return NULL;
    }

    if (byte_count <= BUFFER_SIZE) {
        static uint8_t read_buffer[BUFFER_SIZE];

        /*read the entire string using a single static buffer*/
        if (!setjmp(*br_try(self->bitstream))) {
            self->bitstream->read_bytes(self->bitstream,
                                        read_buffer,
                                        (unsigned)byte_count);
            br_etry(self->bitstream);

            return PyString_FromStringAndSize((char*)read_buffer,
                                              (Py_ssize_t)byte_count);
        } else {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error reading stream");
            return NULL;
        }
    } else {
        /*use multiple read buffers to fetch entire set of bytes*/
        struct bs_buffer* read_buffer = buf_new();
        PyObject* string_obj;

        if (!setjmp(*br_try(self->bitstream))) {
            while (byte_count > 0) {
                const unsigned to_read = MIN(byte_count, BUFFER_SIZE);

                buf_resize(read_buffer, to_read);
                self->bitstream->read_bytes(self->bitstream,
                                            buf_window_end(read_buffer),
                                            to_read);
                read_buffer->window_end += to_read;
                byte_count -= to_read;
            }
            br_etry(self->bitstream);

            string_obj = PyString_FromStringAndSize(
                (char *)buf_window_start(read_buffer),
                (Py_ssize_t)buf_window_size(read_buffer));

            buf_close(read_buffer);
            return string_obj;
        } else {
            br_etry(self->bitstream);
            buf_close(read_buffer);
            PyErr_SetString(PyExc_IOError, "I/O error reading stream");
            return NULL;
        }
    }

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
    self->bitstream->mark(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_rewind(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->rewind(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_unmark(bitstream_BitstreamReader *self, PyObject *args)
{
    self->bitstream->unmark(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
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
    br_add_callback(self->bitstream,
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
        br_pop_callback(self->bitstream, &callback);
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

    br_call_callbacks(self->bitstream, byte);

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
    PyTypeObject *type = self->ob_type;
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
    obj->file_obj = NULL;
    obj->little_endian = self->little_endian;
    obj->bitstream = br_substream_new(obj->little_endian ?
                                      BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

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

    if (self->ob_type != substream_obj->ob_type) {
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

        if (!bitstream_parse(self->bitstream, format, values)) {
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

    self->file_obj = NULL;

    if (!PyArg_ParseTuple(args, "Oi|i", &file_obj, &(self->little_endian),
                          &buffer_size)) {
        return -1;
    } else if (buffer_size <= 0) {
        PyErr_SetString(PyExc_ValueError, "buffer_size must be > 0");
        return -1;
    }

    /*store a reference to the Python object so that it doesn't decref
      (and close) the file out from under us*/
    Py_INCREF(file_obj);
    self->file_obj = file_obj;

    if (PyFile_CheckExact(file_obj)) {
        self->bitstream = br_open(PyFile_AsFile(self->file_obj),
                                  self->little_endian ?
                                  BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

        /*swap the regular FILE-based close_internal_stream method
          with a specialized one that does *not* perform fclose
          on the FILE pointer itself

          it is important that we leave that task
          to the file object itself*/
        self->bitstream->close_internal_stream =
            br_close_internal_stream_python_file;
    } else {
        self->bitstream = br_open_external(
            self->file_obj,
            self->little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
            (ext_read_f)br_read_python,
            (ext_close_f)bs_close_python,
            (ext_free_f)bs_free_python_nodecref);
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

    Py_XDECREF(self->file_obj);
    self->file_obj = NULL;

    self->ob_type->tp_free((PyObject*)self);
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

    reader->file_obj = NULL;
    reader->bitstream = br_substream_new(endianness ?
                                         BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    reader->little_endian = endianness;

    return (PyObject *)reader;
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
    if (self->br_table != NULL)
        free(self->br_table);

    free_bw_huffman_table(self->bw_table);

    self->ob_type->tp_free((PyObject*)self);
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

    self->file_obj = NULL;
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
    self->file_obj = file_obj;

    if (PyFile_CheckExact(file_obj)) {
        self->bitstream = bw_open(PyFile_AsFile(self->file_obj),
                                  little_endian ?
                                  BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

        /*swap the regular FILE-based close_internal_stream method
          with a specialized one that does *not* perform fclose
          on the FILE pointer itself

          it is important that we leave that task
          to the file object itself*/
        self->bitstream->close_internal_stream =
            bw_close_internal_stream_python_file;
    } else {
        self->bitstream = bw_open_external(
            self->file_obj,
            little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
            (unsigned)buffer_size,
            (ext_write_f)bw_write_python,
            (ext_flush_f)bw_flush_python,
            (ext_close_f)bs_close_python,
            (ext_free_f)bs_free_python_nodecref);
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

void
BitstreamWriter_dealloc(bitstream_BitstreamWriter *self)
{
    if (self->bitstream != NULL) {
        self->bitstream->free(self->bitstream);
    }

    Py_XDECREF(self->file_obj);

    self->ob_type->tp_free((PyObject*)self);
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
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write(self->bitstream, (unsigned)count, value);
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
BitstreamWriter_write_signed(bitstream_BitstreamWriter *self, PyObject *args)
{
    int count;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed(self->bitstream, (unsigned)count, value);
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
BitstreamWriter_write64(bitstream_BitstreamWriter *self, PyObject *args)
{
    int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "iK", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_64(self->bitstream, (unsigned)count, value);
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
BitstreamWriter_write_signed64(bitstream_BitstreamWriter *self, PyObject *args)
{
    int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "iL", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed_64(self->bitstream,
                                         (unsigned)count, value);
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

    if (huffman_tree_obj->ob_type != &bitstream_HuffmanTreeType) {
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
    } else if (bitstream_build(self->bitstream, format, iterator)) {
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
    self->bitstream->flush(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
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
    bw_add_callback(self->bitstream,
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
BitstreamWriter_call_callbacks(bitstream_BitstreamWriter *self,
                               PyObject *args)
{
    uint8_t byte;

    if (!PyArg_ParseTuple(args, "b", &byte))
        return NULL;

    bw_call_callbacks(self->bitstream, byte);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamWriter_close(bitstream_BitstreamWriter *self, PyObject *args)
{
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write(self->bitstream, (unsigned)count, value);
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
BitstreamRecorder_write_signed(bitstream_BitstreamRecorder *self,
                               PyObject *args)
{
    int count;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed(self->bitstream, (unsigned)count, value);
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
BitstreamRecorder_write64(bitstream_BitstreamRecorder *self,
                          PyObject *args)
{
    int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "iK", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_64(self->bitstream, (unsigned)count, value);
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
BitstreamRecorder_write_signed64(bitstream_BitstreamRecorder *self,
                                 PyObject *args)
{
    int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "iL", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed_64(self->bitstream,
                                         (unsigned)count, value);
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

    if (huffman_tree_obj->ob_type != &bitstream_HuffmanTreeType) {
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
    } else if (bitstream_build(self->bitstream, format, iterator)) {
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
    return PyString_FromStringAndSize(
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

    bw_swap_records(self->bitstream, to_swap->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_reset(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    bw_reset_recorder(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static BitstreamWriter*
internal_writer(PyObject *writer)
{
    bitstream_BitstreamWriter* writer_obj;
    bitstream_BitstreamRecorder* recorder_obj;
    bitstream_BitstreamAccumulator* accumulator_obj;

    if (writer->ob_type == &bitstream_BitstreamWriterType) {
        writer_obj = (bitstream_BitstreamWriter*)writer;
        return writer_obj->bitstream;
    } else if (writer->ob_type == &bitstream_BitstreamRecorderType) {
        recorder_obj = (bitstream_BitstreamRecorder*)writer;
        return recorder_obj->bitstream;
    } else if (writer->ob_type == &bitstream_BitstreamAccumulatorType) {
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
            bw_rec_copy(target, self->bitstream);
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
        total_bytes = bw_rec_split(target, remainder,
                                   self->bitstream, total_bytes);
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
    bw_add_callback(self->bitstream,
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
BitstreamRecorder_call_callbacks(bitstream_BitstreamRecorder *self,
                                 PyObject *args)
{
    uint8_t byte;

    if (!PyArg_ParseTuple(args, "b", &byte))
        return NULL;

    bw_call_callbacks(self->bitstream, byte);

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

    self->ob_type->tp_free((PyObject*)self);
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

    return 0;
}

void
BitstreamAccumulator_dealloc(bitstream_BitstreamAccumulator *self)
{
    if (self->bitstream != NULL)
        self->bitstream->free(self->bitstream);

    self->ob_type->tp_free((PyObject*)self);
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
    unsigned int value;

    if (!PyArg_ParseTuple(args, "iI", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write(self->bitstream, (unsigned)count, value);
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
BitstreamAccumulator_write_signed(bitstream_BitstreamAccumulator *self,
                                  PyObject *args)
{
    int count;
    int value;

    if (!PyArg_ParseTuple(args, "ii", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed(self->bitstream, (unsigned)count, value);
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
BitstreamAccumulator_write64(bitstream_BitstreamAccumulator *self,
                             PyObject *args)
{
    int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "iK", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_64(self->bitstream, (unsigned)count, value);
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
BitstreamAccumulator_write_signed64(bitstream_BitstreamAccumulator *self,
                                    PyObject *args)
{
    int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "iL", &count, &value)) {
        return NULL;
    } else if (count < 0) {
        PyErr_SetString(PyExc_ValueError, "count must be >= 0");
        return NULL;
    }

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed_64(self->bitstream,
                                         (unsigned)count, value);
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

    if (huffman_tree_obj->ob_type != &bitstream_HuffmanTreeType) {
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
    } else if (bitstream_build(self->bitstream, format, iterator)) {
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
    bw_reset_accumulator(self->bitstream);

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
        if (!bitstream_parse(stream, format, values)) {
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
        BitstreamWriter* stream = bw_open_recorder(
            is_little_endian ? BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
        if (!bitstream_build(stream, format, iterator)) {
            PyObject* data = PyString_FromStringAndSize(
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
bitstream_parse(BitstreamReader* stream, const char* format, PyObject* values)
{
    if (!setjmp(*br_try(stream))) {
        bs_instruction_t inst;

        do {
            unsigned times;
            unsigned size;

            format = bs_parse_format(format, &times, &size, &inst);
            if (inst == BS_INST_UNSIGNED) {
                for (; times; times--) {
                    const unsigned value = stream->read(stream, size);
                    PyObject *py_value;
                    if ((py_value = Py_BuildValue("I", value)) == NULL) {
                        br_etry(stream);
                        return 1;
                    } else if (PyList_Append(values, py_value) == -1) {
                        Py_DECREF(py_value);
                        br_etry(stream);
                        return 1;
                    } else {
                        Py_DECREF(py_value);
                    }
                }
            } else if (inst == BS_INST_SIGNED) {
                for (; times; times--) {
                    const int value = stream->read_signed(stream, size);
                    PyObject *py_value;
                    if ((py_value = Py_BuildValue("i", value)) == NULL) {
                        br_etry(stream);
                        return 1;
                    } else if (PyList_Append(values, py_value) == -1) {
                        Py_DECREF(py_value);
                        br_etry(stream);
                        return 1;
                    } else {
                        Py_DECREF(py_value);
                    }
                }
            } else if (inst == BS_INST_UNSIGNED64) {
                for (; times; times--) {
                    const uint64_t value = stream->read_64(stream, size);
                    PyObject *py_value;
                    if ((py_value = Py_BuildValue("K", value)) == NULL) {
                        br_etry(stream);
                        return 1;
                    } else if (PyList_Append(values, py_value) == -1) {
                        Py_DECREF(py_value);
                        br_etry(stream);
                        return 1;
                    } else {
                        Py_DECREF(py_value);
                    }
                }
            } else if (inst == BS_INST_SIGNED64) {
                for (; times; times--) {
                    const int64_t value = stream->read_signed_64(stream, size);
                    PyObject *py_value;
                    if ((py_value = Py_BuildValue("L", value)) == NULL) {
                        br_etry(stream);
                        return 1;
                    } else if (PyList_Append(values, py_value) == -1) {
                        Py_DECREF(py_value);
                        br_etry(stream);
                        return 1;
                    } else {
                        Py_DECREF(py_value);
                    }
                }
            } else if (inst == BS_INST_SKIP) {
                for (; times; times--) {
                    stream->skip(stream, size);
                }
            } else if (inst == BS_INST_SKIP_BYTES) {
                for (; times; times--) {
                    stream->skip_bytes(stream, size);
                }
            } else if (inst == BS_INST_BYTES) {
                for (; times; times--) {
                    PyObject *py_value;

                    if ((py_value =
                         PyString_FromStringAndSize(NULL, size)) == NULL) {
                        /*error getting new string object at that size*/
                        br_etry(stream);
                        return 1;
                    } else {
                        uint8_t *value = (uint8_t*)PyString_AsString(py_value);
                        /*ensure py_value gets DECREFed
                          especially if a read error occurs*/
                        if (!setjmp(*br_try(stream))) {
                            stream->read_bytes(stream, value, size);
                            br_etry(stream);
                        } else {
                            Py_DECREF(py_value);
                            br_etry(stream);
                            br_abort(stream);
                        }
                        if (PyList_Append(values, py_value) == -1) {
                            Py_DECREF(py_value);
                            br_etry(stream);
                            return 1;
                        } else {
                            Py_DECREF(py_value);
                        }
                    }
                }
            } else if (inst == BS_INST_ALIGN) {
                stream->byte_align(stream);
            }
        } while (inst != BS_INST_EOF);

        br_etry(stream);
        return 0;
    } else {
        br_etry(stream);
        PyErr_SetString(PyExc_IOError, "I/O error parsing values");
        return 1;
    }
}

#define MISSING_VALUES "number of items is too short for format"

int
bitstream_build(BitstreamWriter* stream,
                const char* format, PyObject* iterator)
{

    if (!setjmp(*bw_try(stream))) {
        bs_instruction_t inst;
        do {
            unsigned times;
            unsigned size;

            format = bs_parse_format(format, &times, &size, &inst);
            if (inst == BS_INST_UNSIGNED) {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    if (py_value != NULL) {
                        const unsigned long value =
                            PyInt_AsUnsignedLongMask(py_value);
                        Py_DECREF(py_value);
                        if (!PyErr_Occurred()) {
                            stream->write(stream, size, (unsigned)value);
                        } else {
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
            } else if (inst == BS_INST_SIGNED) {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    if (py_value != NULL) {
                        const long value = PyInt_AsLong(py_value);
                        Py_DECREF(py_value);
                        if (!PyErr_Occurred()) {
                            stream->write_signed(stream, size, (int)value);
                        } else {
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
            } else if (inst == BS_INST_UNSIGNED64) {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    if (py_value != NULL) {
                        const unsigned PY_LONG_LONG value =
                            PyInt_AsUnsignedLongLongMask(py_value);
                        Py_DECREF(py_value);
                        if (!PyErr_Occurred()) {
                            stream->write_64(stream, size, (uint64_t)value);
                        } else {
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
            } else if (inst == BS_INST_SIGNED64) {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    if (py_value != NULL) {
                        const PY_LONG_LONG u =
                            PyLong_AsLongLong(py_value);
                        Py_DECREF(py_value);
                        if (!PyErr_Occurred()) {
                            stream->write_signed_64(stream, size, (int64_t)u);
                        } else {
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
            } else if (inst == BS_INST_SKIP) {
                for (; times; times--) {
                    stream->write(stream, size, 0);
                }
            } else if (inst == BS_INST_SKIP_BYTES) {
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
            } else if (inst == BS_INST_BYTES) {
                for (; times; times--) {
                    PyObject *py_value = PyIter_Next(iterator);
                    if (py_value != NULL) {
                        char *bytes;
                        Py_ssize_t bytes_len;

                        if (PyString_AsStringAndSize(py_value,
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
            } else if (inst == BS_INST_ALIGN) {
                stream->byte_align(stream);
            }

        } while (inst != BS_INST_EOF);

        bw_etry(stream);
        return 0;
    } else {
        PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
        bw_etry(stream);
        return 1;
    }

}
