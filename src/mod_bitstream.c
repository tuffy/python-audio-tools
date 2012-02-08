#include <Python.h>
#include "bitstream.h"
#include "huffman.h"
#include "mod_bitstream.h"


/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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
    unsigned int count;
    unsigned int result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read(self->bitstream, count);
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
    unsigned int count;
    uint64_t result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_64(self->bitstream, count);
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
    unsigned int count;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->skip(self->bitstream, count);
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
    unsigned int count;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->skip_bytes(self->bitstream, count);
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
    unsigned int count;
    int result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_signed(self->bitstream, count);
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
    unsigned int count;
    int64_t result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_signed_64(self->bitstream, count);
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
                                                    *(huffman_tree->table));

        br_etry(self->bitstream);
        return Py_BuildValue("i", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_read_bytes(bitstream_BitstreamReader *self,
                           PyObject *args)
{
    PyObject* byte_string;
    unsigned int byte_count;

    if (!PyArg_ParseTuple(args, "I", &byte_count))
        return NULL;

    if ((byte_string = PyString_FromStringAndSize(NULL, byte_count)) == NULL)
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->read_bytes(self->bitstream,
                                    (uint8_t*)PyString_AsString(byte_string),
                                    byte_count);
        br_etry(self->bitstream);

        return byte_string;
    } else {
        br_etry(self->bitstream);
        Py_DECREF(byte_string);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
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
    self->bitstream->close_substream(self->bitstream);
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
                    (bs_callback_func)BitstreamReader_callback,
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
BitstreamReader_substream(bitstream_BitstreamReader *self, PyObject *args)
{
    PyTypeObject *type = self->ob_type;
    unsigned int bytes;
    bitstream_BitstreamReader *obj;

    if (!PyArg_ParseTuple(args, "I", &bytes))
        return NULL;

    obj = (bitstream_BitstreamReader *)type->tp_alloc(type, 0);
    obj->file_obj = NULL;
    obj->little_endian = self->little_endian;
    obj->bitstream = br_substream_new(obj->little_endian ?
                                      BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->substream_append(self->bitstream,
                                          obj->bitstream,
                                          bytes);
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
    unsigned int bytes;

    if (!PyArg_ParseTuple(args, "OI", &substream_obj, &bytes))
        return NULL;

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

    self->bitstream->substream_append(self->bitstream,
                                      substream->bitstream,
                                      bytes);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_parse(bitstream_BitstreamReader *self, PyObject *args)
{
    char* format;
    PyObject *values;
    PyObject *value = NULL;
    unsigned int size;
    bs_instruction type;

    if (!PyArg_ParseTuple(args, "s", &format))
        return NULL;

    values = PyList_New(0);

    if (!setjmp(*br_try(self->bitstream))) {
        while (!bs_parse_format(&format, &size, &type)) {
            value = NULL;
            switch (type) {
            case BS_INST_UNSIGNED:
                if ((value =
                     Py_BuildValue("I",
                                   self->bitstream->read(
                                       self->bitstream, size))) == NULL) {
                    goto error;
                } else if (PyList_Append(values, value) == -1) {
                    goto error;
                } else {
                    Py_DECREF(value);
                }
                break;
            case BS_INST_SIGNED:
                if ((value =
                     Py_BuildValue("i",
                                   self->bitstream->read_signed(
                                       self->bitstream, size))) == NULL) {
                    goto error;
                } else if (PyList_Append(values, value) == -1) {
                    goto error;
                } else {
                    Py_DECREF(value);
                }
                break;
            case BS_INST_UNSIGNED64:
                if ((value =
                     Py_BuildValue("K",
                                   self->bitstream->read_64(
                                       self->bitstream, size))) == NULL) {
                    goto error;
                } else if (PyList_Append(values, value) == -1) {
                    goto error;
                } else {
                    Py_DECREF(value);
                }
                break;
            case BS_INST_SIGNED64:
                if ((value =
                     Py_BuildValue("L",
                                   self->bitstream->read_signed_64(
                                       self->bitstream, size))) == NULL) {
                    goto error;
                } else if (PyList_Append(values, value) == -1) {
                    goto error;
                } else {
                    Py_DECREF(value);
                }
                break;
            case BS_INST_SKIP:
                self->bitstream->skip(self->bitstream, size);
                break;
            case BS_INST_SKIP_BYTES:
                self->bitstream->skip_bytes(self->bitstream, size);
                break;
            case BS_INST_BYTES:
                if ((value = PyString_FromStringAndSize(NULL, size)) == NULL) {
                    goto error;
                } else {
                    self->bitstream->read_bytes(
                                           self->bitstream,
                                           (uint8_t*)PyString_AsString(value),
                                           size);
                    if (PyList_Append(values, value) == -1)
                        goto error;
                    else
                        Py_DECREF(value);
                }
                break;
            case BS_INST_ALIGN:
                self->bitstream->byte_align(self->bitstream);
                break;
            }
        }

        br_etry(self->bitstream);
        return values;

    error:
        br_etry(self->bitstream);
        Py_DECREF(values);
        Py_XDECREF(value);
        return NULL;
    } else {
        br_etry(self->bitstream);
        Py_DECREF(values);
        Py_XDECREF(value);
        PyErr_SetString(PyExc_IOError, "I/O error parsing values");
        return NULL;
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
    unsigned int buffer_size = 4096;

    self->file_obj = NULL;

    if (!PyArg_ParseTuple(args, "Oi|I", &file_obj, &(self->little_endian),
                          &buffer_size))
        return -1;

    /*store a reference to the Python object so that it doesn't decref
      (and close) the file out from under us*/
    Py_INCREF(file_obj);
    self->file_obj = file_obj;

    if (PyFile_CheckExact(file_obj)) {
        self->bitstream = br_open(PyFile_AsFile(self->file_obj),
                                  self->little_endian ?
                                  BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

        /*swap the regular FILE-based close_substream method
          with a specialized one that does *not* perform fclose
          on the FILE pointer itself

          it is important that we leave that task
          to the file object itself*/
        self->bitstream->close_substream = br_close_substream_python_file;
    } else {
        self->bitstream = br_open_external(self->file_obj,
                                           self->little_endian ?
                                           BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
                                           br_read_python,
                                           br_close_python,
                                           br_free_python);
    }

    return 0;
}

void
br_close_substream_python_file(BitstreamReader* bs)
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
             c_node != NULL; c_node = c_node->next) {
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

    self->table = NULL;

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

    switch (compile_huffman_table(&(self->table),
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
    if (self->table != NULL)
        free(self->table);

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
    unsigned int buffer_size = 4096;

    self->file_obj = NULL;
    self->bitstream = NULL;

    if (!PyArg_ParseTuple(args, "Oi|I", &file_obj, &little_endian,
                          &buffer_size))
        return -1;

    /*store a reference to the Python object so that it doesn't decref
      (and close) the file out from under us*/
    Py_INCREF(file_obj);
    self->file_obj = file_obj;

    if (PyFile_CheckExact(file_obj)) {
        self->bitstream = bw_open(PyFile_AsFile(self->file_obj),
                                  little_endian ?
                                  BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);

        /*swap the regular FILE-based close_substream method
          with a specialized one that does *not* perform fclose
          on the FILE pointer itself

          it is important that we leave that task
          to the file object itself*/
        self->bitstream->close_substream = bw_close_substream_python_file;
    } else {
        self->bitstream = bw_open_python(self->file_obj,
                                         little_endian ?
                                         BS_LITTLE_ENDIAN : BS_BIG_ENDIAN,
                                         buffer_size);
    }

    return 0;
}

void
bw_close_substream_python_file(BitstreamWriter* bs)
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
    unsigned int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "II", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write(self->bitstream, count, value);
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
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed(self->bitstream, count, value);
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
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IK", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_64(self->bitstream, count, value);
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
    unsigned int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed_64(self->bitstream, count, value);
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
                    (bs_callback_func)BitstreamWriter_callback,
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
    self->bitstream->close_substream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamRecorder_write(bitstream_BitstreamRecorder *self,
                        PyObject *args)
{
    unsigned int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "II", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write(self->bitstream, count, value);
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
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed(self->bitstream, count, value);
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
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IK", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_64(self->bitstream, count, value);
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
    unsigned int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed_64(self->bitstream, count, value);
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
        (const char *)(self->bitstream->output.buffer->buffer +
                       self->bitstream->output.buffer->buffer_position),
        self->bitstream->output.buffer->buffer_size -
        self->bitstream->output.buffer->buffer_position);
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
                    (bs_callback_func)BitstreamWriter_callback,
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
    self->bitstream->close_substream(self->bitstream);
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
bitstream_build(BitstreamWriter* stream, char* format, PyObject* values)
{
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

    if (!setjmp(*bw_try(stream))) {
        while (!bs_parse_format(&format, &size, &type)) {
            switch (type) {
            case BS_INST_UNSIGNED:
                if ((value = PySequence_GetItem(values, i++)) != NULL) {
                    _unsigned = (unsigned int)PyInt_AsUnsignedLongMask(value);
                    Py_DECREF(value);
                    if (!PyErr_Occurred())
                        stream->write(stream, size, _unsigned);
                    else
                        goto write_error;
                } else {
                    goto write_error;
                }
                break;
            case BS_INST_SIGNED:
                if ((value = PySequence_GetItem(values, i++)) != NULL) {
                    _signed = (int)PyInt_AsLong(value);
                    Py_DECREF(value);
                    if (!PyErr_Occurred())
                        stream->write_signed(stream, size, _signed);
                    else
                        goto write_error;
                } else {
                    goto write_error;
                }
                break;
            case BS_INST_UNSIGNED64:
                if ((value = PySequence_GetItem(values, i++)) != NULL) {
                    _unsigned64 = PyInt_AsUnsignedLongLongMask(value);
                    Py_DECREF(value);
                    if (!PyErr_Occurred())
                        stream->write_64(stream, size, _unsigned64);
                    else
                        goto write_error;
                } else {
                    goto write_error;
                }
                break;
            case BS_INST_SIGNED64:
                if ((value = PySequence_GetItem(values, i++)) != NULL) {
                    _signed64 = PyLong_AsLongLong(value);
                    Py_DECREF(value);
                    if (!PyErr_Occurred())
                        stream->write_signed_64(stream, size, _signed64);
                    else
                        goto write_error;
                } else {
                    goto write_error;
                }
                break;
            case BS_INST_SKIP:
                stream->write(stream, size, 0);
                break;
            case BS_INST_SKIP_BYTES:
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                break;
            case BS_INST_BYTES:
                if ((value = PySequence_GetItem(values, i++)) != NULL) {
                    if (PyString_AsStringAndSize(value,
                                                 (char **)(&_bytes),
                                                 &bytes_len) != -1) {
                        if (size <= bytes_len) {
                            stream->write_bytes(stream, _bytes, size);
                            Py_DECREF(value);
                        } else {
                            PyErr_SetString(PyExc_ValueError,
                                            "string length too short");
                            Py_DECREF(value);
                            goto write_error;
                        }
                    } else {
                        Py_DECREF(value);
                        goto write_error;
                    }
                } else {
                    goto write_error;
                }
                break;
            case BS_INST_ALIGN:
                stream->byte_align(stream);
                break;
            }
        }

        bw_etry(stream);
        return 0;
    } else {
        PyErr_SetString(PyExc_IOError, "I/O error writing to stream");
        bw_etry(stream);
        return 1;
    }

 write_error:
    bw_etry(stream);
    return 1;
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
    self->bitstream->close_substream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamAccumulator_write(bitstream_BitstreamAccumulator *self,
                           PyObject *args)
{
    unsigned int count;
    unsigned int value;

    if (!PyArg_ParseTuple(args, "II", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write(self->bitstream, count, value);
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
    unsigned int count;
    int value;

    if (!PyArg_ParseTuple(args, "Ii", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed(self->bitstream, count, value);
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
    unsigned int count;
    uint64_t value;

    if (!PyArg_ParseTuple(args, "IK", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_64(self->bitstream, count, value);
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
    unsigned int count;
    int64_t value;

    if (!PyArg_ParseTuple(args, "IL", &count, &value))
        return NULL;

    if (!setjmp(*bw_try(self->bitstream))) {
        self->bitstream->write_signed_64(self->bitstream, count, value);
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

int br_read_python(void* user_data,
                   struct bs_buffer* buffer)
{
    PyObject* pcmreader = (PyObject*)user_data;
    PyObject* read_result;

    /*call read() method on pcmreader*/
    if ((read_result =
         PyObject_CallMethod(pcmreader, "read", "i", 4096)) != NULL) {
        uint8_t *string;
        Py_ssize_t string_size;

        /*convert returned object to string of bytes*/
        if (PyString_AsStringAndSize(read_result,
                                     (char**)&string,
                                     &string_size) != -1) {
            /*then append bytes to buffer and return success*/
            uint8_t* appended = buf_extend(buffer, (uint32_t)string_size);
            memcpy(appended, string, string_size);
            buffer->buffer_size += (uint32_t)string_size;

            return 0;
        } else {
            /*string conversion failed so print/clear error and return an EOF*/
            PyErr_Print();
            return 1;
        }
    } else {
        /*read() method call failed
          so print/clear error and return an EOF
          (which will likely generate an IOError exception if its own)*/
        PyErr_Print();
        return 1;
    }

}

void br_close_python(void* user_data)
{
    /*FIXME*/
}

void br_free_python(void* user_data)
{
    /*FIXME*/
}
