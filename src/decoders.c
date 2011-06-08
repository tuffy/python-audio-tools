#include <Python.h>
#include "bitstream.h"
#include "huffman.h"
#include "decoders.h"

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

extern PyTypeObject decoders_FlacDecoderType;
extern PyTypeObject decoders_OggFlacDecoderType;
extern PyTypeObject decoders_SHNDecoderType;
extern PyTypeObject decoders_ALACDecoderType;
extern PyTypeObject decoders_WavPackDecoderType;
extern PyTypeObject decoders_VorbisDecoderType;
extern PyTypeObject decoders_MLPDecoderType;
extern PyTypeObject decoders_AOBPCMDecoderType;
extern PyTypeObject decoders_Sine_Mono_Type;
extern PyTypeObject decoders_Sine_Stereo_Type;
extern PyTypeObject decoders_Sine_Simple_Type;

extern const unsigned int read_bits_table[0x900][8];
extern const unsigned int read_unary_table[0x900][2];
extern const unsigned int read_limited_unary_table[0x900][18];
extern const unsigned int unread_bit_table[0x900][2];

PyMODINIT_FUNC
initdecoders(void)
{
    PyObject* m;

    decoders_BitstreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_BitstreamReaderType) < 0)
        return;

    decoders_HuffmanTreeType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_HuffmanTreeType) < 0)
        return;

    decoders_FlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_FlacDecoderType) < 0)
        return;

    decoders_OggFlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_OggFlacDecoderType) < 0)
        return;

    decoders_SHNDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_SHNDecoderType) < 0)
        return;

    decoders_ALACDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_ALACDecoderType) < 0)
        return;

    decoders_WavPackDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_WavPackDecoderType) < 0)
        return;

    decoders_VorbisDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_VorbisDecoderType) < 0)
        return;

    decoders_MLPDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_MLPDecoderType) < 0)
        return;

    decoders_AOBPCMDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_AOBPCMDecoderType) < 0)
        return;

    decoders_Sine_Mono_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_Sine_Mono_Type) < 0)
        return;

    decoders_Sine_Stereo_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_Sine_Stereo_Type) < 0)
        return;

    decoders_Sine_Simple_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_Sine_Simple_Type) < 0)
        return;

    m = Py_InitModule3("decoders", module_methods,
                       "Low-level audio format decoders");

    Py_INCREF(&decoders_BitstreamReaderType);
    PyModule_AddObject(m, "BitstreamReader",
                       (PyObject *)&decoders_BitstreamReaderType);

    Py_INCREF(&decoders_HuffmanTreeType);
    PyModule_AddObject(m, "HuffmanTree",
                       (PyObject *)&decoders_HuffmanTreeType);

    Py_INCREF(&decoders_FlacDecoderType);
    PyModule_AddObject(m, "FlacDecoder",
                       (PyObject *)&decoders_FlacDecoderType);

    Py_INCREF(&decoders_OggFlacDecoderType);
    PyModule_AddObject(m, "OggFlacDecoder",
                       (PyObject *)&decoders_OggFlacDecoderType);

    Py_INCREF(&decoders_SHNDecoderType);
    PyModule_AddObject(m, "SHNDecoder",
                       (PyObject *)&decoders_SHNDecoderType);

    Py_INCREF(&decoders_ALACDecoderType);
    PyModule_AddObject(m, "ALACDecoder",
                       (PyObject *)&decoders_ALACDecoderType);

    Py_INCREF(&decoders_WavPackDecoderType);
    PyModule_AddObject(m, "WavPackDecoder",
                       (PyObject *)&decoders_WavPackDecoderType);

    Py_INCREF(&decoders_VorbisDecoderType);
    PyModule_AddObject(m, "VorbisDecoder",
                       (PyObject *)&decoders_VorbisDecoderType);

    Py_INCREF(&decoders_MLPDecoderType);
    PyModule_AddObject(m, "MLPDecoder",
                       (PyObject *)&decoders_MLPDecoderType);

    Py_INCREF(&decoders_AOBPCMDecoderType);
    PyModule_AddObject(m, "AOBPCMDecoder",
                       (PyObject *)&decoders_AOBPCMDecoderType);

    Py_INCREF(&decoders_Sine_Mono_Type);
    PyModule_AddObject(m, "Sine_Mono",
                       (PyObject *)&decoders_Sine_Mono_Type);

    Py_INCREF(&decoders_Sine_Stereo_Type);
    PyModule_AddObject(m, "Sine_Stereo",
                       (PyObject *)&decoders_Sine_Stereo_Type);

    Py_INCREF(&decoders_Sine_Simple_Type);
    PyModule_AddObject(m, "Sine_Simple",
                       (PyObject *)&decoders_Sine_Simple_Type);
}

static PyObject*
BitstreamReader_read(decoders_BitstreamReader *self, PyObject *args) {
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
BitstreamReader_read64(decoders_BitstreamReader *self, PyObject *args) {
    unsigned int count;
    uint64_t result;

    if (!PyArg_ParseTuple(args, "I", &count))
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        result = self->bitstream->read_64(self->bitstream, count);
        br_etry(self->bitstream);
        return Py_BuildValue("L", result);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_skip(decoders_BitstreamReader *self, PyObject *args) {
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
BitstreamReader_byte_align(decoders_BitstreamReader *self, PyObject *args) {
    self->bitstream->byte_align(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_unread(decoders_BitstreamReader *self, PyObject *args) {
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
BitstreamReader_read_signed(decoders_BitstreamReader *self, PyObject *args) {
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
BitstreamReader_unary(decoders_BitstreamReader *self, PyObject *args) {
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
BitstreamReader_limited_unary(decoders_BitstreamReader *self, PyObject *args) {
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
        br_etry(self->bitstream);
        if (result >= 0)
            return Py_BuildValue("i", result);
        else {
            Py_INCREF(Py_None);
            return Py_None;
        }
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
BitstreamReader_read_huffman_code(decoders_BitstreamReader *self,
                                  PyObject* args) {
    PyObject* huffman_tree_obj;
    decoders_HuffmanTree* huffman_tree;
    int result;

    if (!PyArg_ParseTuple(args, "O", &huffman_tree_obj))
        return NULL;

    if (huffman_tree_obj->ob_type != &decoders_HuffmanTreeType) {
        PyErr_SetString(PyExc_TypeError, "argument must a HuffmanTree object");
        return NULL;
    }

    huffman_tree = (decoders_HuffmanTree*)huffman_tree_obj;

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
BitstreamReader_read_bytes(decoders_BitstreamReader *self,
                           PyObject *args) {
    PyObject* byte_string;
    unsigned int byte_count;

    if (!PyArg_ParseTuple(args, "I", &byte_count))
        return NULL;

    if ((byte_string = PyString_FromStringAndSize(NULL, byte_count)) == NULL)
        return NULL;

    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->read_bytes(self->bitstream,
                                    byte_count,
                                    (uint8_t*)PyString_AsString(byte_string));
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
BitstreamReader_tell(decoders_BitstreamReader *self, PyObject *args) {
    return PyObject_CallMethod(self->file_obj, "tell", NULL);
}

static PyObject*
BitstreamReader_set_endianness(decoders_BitstreamReader *self,
                               PyObject *args) {
    int little_endian;

    if (!PyArg_ParseTuple(args, "i", &little_endian))
        return NULL;

    if ((little_endian != 0) && (little_endian != 1)) {
        PyErr_SetString(PyExc_ValueError,
                    "endianness must be 0 (big-endian) or 1 (little-endian)");
        return NULL;
    }

    self->bitstream->set_endianness(self->bitstream,
                                    little_endian ? BS_LITTLE_ENDIAN :
                                    BS_BIG_ENDIAN);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_close(decoders_BitstreamReader *self, PyObject *args) {
    PyObject* close_result = PyObject_CallMethod(self->file_obj,
                                                 "close", NULL);
    if (close_result) {
        Py_DECREF(close_result);
        Py_INCREF(Py_None);
        return Py_None;
    } else
        return NULL;
}

static PyObject*
BitstreamReader_mark(decoders_BitstreamReader *self, PyObject *args) {
    self->bitstream->mark(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_rewind(decoders_BitstreamReader *self, PyObject *args) {
    self->bitstream->rewind(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_unmark(decoders_BitstreamReader *self, PyObject *args) {
    self->bitstream->unmark(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
BitstreamReader_substream(decoders_BitstreamReader *self, PyObject *args) {
    PyTypeObject *type = self->ob_type;
    unsigned int bytes;
    decoders_BitstreamReader *obj;

    if (!PyArg_ParseTuple(args, "I", &bytes))
        return NULL;

    obj = (decoders_BitstreamReader *)type->tp_alloc(type, 0);
    obj->file_obj = NULL;
    obj->is_substream = 1;
    obj->bitstream = self->bitstream->substream(self->bitstream, bytes);

    return (PyObject *)obj;
}

static PyObject*
BitstreamReader_substream_append(decoders_BitstreamReader *self,
                                 PyObject *args) {
    PyObject *substream_obj;
    decoders_BitstreamReader *substream;
    unsigned int bytes;

    if (!PyArg_ParseTuple(args, "OI", &substream_obj, &bytes))
        return NULL;

    if (self->ob_type != substream_obj->ob_type) {
        PyErr_SetString(PyExc_TypeError,
                        "first argument must be a BitstreamReader");
        return NULL;
    } else
        substream = (decoders_BitstreamReader*)substream_obj;

    if (!substream->is_substream) {
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

PyObject*
BitstreamReader_new(PyTypeObject *type,
                    PyObject *args, PyObject *kwds)
{
    decoders_BitstreamReader *self;

    self = (decoders_BitstreamReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
BitstreamReader_init(decoders_BitstreamReader *self,
                     PyObject *args)
{
    PyObject *file_obj;
    int little_endian;

    self->file_obj = NULL;
    self->is_substream = 0;

    if (!PyArg_ParseTuple(args, "Oi", &file_obj, &little_endian))
        return -1;

    Py_INCREF(file_obj);
    self->file_obj = file_obj;

    if (PyFile_CheckExact(file_obj)) {
        self->bitstream = br_open(PyFile_AsFile(self->file_obj),
                                    little_endian ? BS_LITTLE_ENDIAN :
                                    BS_BIG_ENDIAN);
    } else {
        self->bitstream = br_open_python(self->file_obj,
                                         little_endian ? BS_LITTLE_ENDIAN :
                                         BS_BIG_ENDIAN);
    }

    return 0;
}

void
BitstreamReader_dealloc(decoders_BitstreamReader *self)
{
    if (self->bitstream != NULL)
        br_free(self->bitstream);
    Py_XDECREF(self->file_obj);
    self->file_obj = NULL;

    self->ob_type->tp_free((PyObject*)self);
}

/*this functions similarly to json_to_frequencies -> compile_huffman_table*/
int
HuffmanTree_init(decoders_HuffmanTree *self, PyObject *args) {
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

            frequency.bits = ((frequency.bits << 1) | bits_int_value);
            frequency.length++;

            Py_DECREF(bits_int);
            bits_int = NULL;
        }

        /*value must always be an integer*/
        if (((value_int_value = PyInt_AsLong(value_obj)) == -1) &&
            PyErr_Occurred())
            goto error;

        frequency.value = value_int_value;

        frequencies[o] = frequency;

        Py_DECREF(bits_list);
        Py_DECREF(value_obj);
        bits_list = value_obj = NULL;
    }

    switch (compile_huffman_table(&(self->table),
                                  frequencies,
                                  list_length / 2,
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
HuffmanTree_dealloc(decoders_HuffmanTree *self) {
    if (self->table != NULL)
        free(self->table);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
HuffmanTree_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_HuffmanTree *self;

    self = (decoders_HuffmanTree *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}
