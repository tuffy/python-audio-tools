#include "mod_ogg.h"

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

int
Page_init(ogg_Page *self, PyObject *args, PyObject *keywds)
{
    static char *kwlist[] = {"packet_continuation",
                             "stream_beginning",
                             "stream_end",
                             "granule_position",
                             "bitstream_serial_number",
                             "sequence_number",
                             "segments",
                             NULL};

    int packet_continuation;
    int stream_beginning;
    int stream_end;
    long long granule_position;
    unsigned bitstream_serial_number;
    unsigned sequence_number;
    PyObject *segments;
    PyObject *segments_iter;
    PyObject *item;

    if (!PyArg_ParseTupleAndKeywords(
        args, keywds, "iiiLIIO", kwlist,
        &packet_continuation,
        &stream_beginning,
        &stream_end,
        &granule_position,
        &bitstream_serial_number,
        &sequence_number,
        &segments))
        return -1;

    /*populate header fields*/
    self->page.header.magic_number = 0x5367674F;
    self->page.header.version = 0;
    self->page.header.packet_continuation = packet_continuation ? 1 : 0;
    self->page.header.stream_beginning = stream_beginning ? 1 : 0;
    self->page.header.stream_end = stream_end ? 1 : 0;
    self->page.header.granule_position = granule_position;
    self->page.header.bitstream_serial_number = bitstream_serial_number;
    self->page.header.sequence_number = sequence_number;
    self->page.header.checksum = 0;
    self->page.header.segment_count = 0;

    /*then iterate over segments to populate binary blobs and lengths*/
    if ((segments_iter = PyObject_GetIter(segments)) == NULL) {
        return -1;
    }

    while ((item = PyIter_Next(segments_iter)) != NULL) {
        unsigned char *buffer;
        Py_ssize_t length;

        /*ensure we're not trying to add too many segments*/
        if (self->page.header.segment_count == 255) {
            PyErr_SetString(PyExc_ValueError,
                            "segment count cannot exceed 255");
            Py_DECREF(item);
            Py_DECREF(segments_iter);
            return -1;
        }

        /*get string data from segment*/
        if (PyString_AsStringAndSize(item, (char **)&buffer, &length) == -1) {
            Py_DECREF(item);
            Py_DECREF(segments_iter);
            return -1;
        }

        /*ensure segment is not too large*/
        if (length > 255) {
            PyErr_SetString(PyExc_ValueError,
                            "segments must be 255 bytes or less");
            Py_DECREF(item);
            Py_DECREF(segments_iter);
            return -1;
        }

        /*transfer segment size and data to page*/
        self->page.header.segment_lengths[self->page.header.segment_count] =
            (unsigned)length;

        memcpy(self->page.segment[self->page.header.segment_count],
               buffer,
               (size_t)length);

        self->page.header.segment_count++;

        Py_DECREF(item);
    }

    Py_DECREF(segments_iter);

    return PyErr_Occurred() ? -1 : 0;
}

void
Page_dealloc(ogg_Page *self)
{
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
Page_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    ogg_Page *self;

    self = (ogg_Page *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject *
Page_get_packet_continuation(ogg_Page *self, void *closure)
{
    return Py_BuildValue("i", self->page.header.packet_continuation);
}

static int
Page_set_packet_continuation(ogg_Page *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot delete attribute");
        return -1;
    }

    switch (PyObject_IsTrue(value)) {
    case 1:
        self->page.header.packet_continuation = 1;
        return 0;
    case 0:
        self->page.header.packet_continuation = 0;
        return 0;
    default:
        return -1;
    }
}

static PyObject *
Page_get_stream_beginning(ogg_Page *self, void *closure)
{
    return Py_BuildValue("i", self->page.header.stream_beginning);
}

static int
Page_set_stream_beginning(ogg_Page *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot delete attribute");
        return -1;
    }

    switch (PyObject_IsTrue(value)) {
    case 1:
        self->page.header.stream_beginning = 1;
        return 0;
    case 0:
        self->page.header.stream_beginning = 0;
        return 0;
    default:
        return -1;
    }
}

static PyObject *
Page_get_stream_end(ogg_Page *self, void *closure)
{
    return Py_BuildValue("i", self->page.header.stream_end);
}

static int
Page_set_stream_end(ogg_Page *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot delete attribute");
        return -1;
    }

    switch (PyObject_IsTrue(value)) {
    case 1:
        self->page.header.stream_end = 1;
        return 0;
    case 0:
        self->page.header.stream_end = 0;
        return 0;
    default:
        return -1;
    }
}

static PyObject *
Page_get_granule_position(ogg_Page *self, void *closure)
{
    return Py_BuildValue("L", self->page.header.granule_position);
}

static int
Page_set_granule_position(ogg_Page *self, PyObject *value, void *closure)
{
    PY_LONG_LONG position;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot delete attribute");
        return -1;
    } else if (((position = PyLong_AsLongLong(value)) == -1) &&
               PyErr_Occurred()) {
        return -1;
    } else {
        self->page.header.granule_position = (int64_t)position;
        return 0;
    }
}

static PyObject *
Page_get_bitstream_serial_number(ogg_Page *self, void *closure)
{
    return Py_BuildValue("I", self->page.header.bitstream_serial_number);
}

static int
Page_set_bitstream_serial_number(ogg_Page *self, PyObject *value,
                                 void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot delete attribute");
        return -1;
    } else {
        unsigned long number = PyLong_AsUnsignedLong(value);

        if (PyErr_Occurred()) {
            return -1;
        } else {
            self->page.header.bitstream_serial_number = (unsigned)number;
            return 0;
        }
    }
}

static PyObject *
Page_get_sequence_number(ogg_Page *self, void *closure)
{
    return Py_BuildValue("I", self->page.header.sequence_number);
}

static int
Page_set_sequence_number(ogg_Page *self, PyObject *value, void *closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot delete attribute");
        return -1;
    } else {
        unsigned long number = PyLong_AsUnsignedLong(value);

        if (PyErr_Occurred()) {
            return -1;
        } else {
            self->page.header.sequence_number = (unsigned)number;
            return 0;
        }
    }
}

static Py_ssize_t
Page_len(ogg_Page *self)
{
    return self->page.header.segment_count;
}

static PyObject*
Page_GetItem(ogg_Page *self, Py_ssize_t i)
{
    if (i < self->page.header.segment_count) {
        return PyString_FromStringAndSize(
            (char *)self->page.segment[i],
            (Py_ssize_t)self->page.header.segment_lengths[i]);
    } else {
        PyErr_SetString(PyExc_IndexError, "out of range");
        return NULL;
    }
}

static PyObject*
Page_append(ogg_Page *self, PyObject *args)
{
    uint8_t *buffer;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t buffer_len;
#else
    int buffer_len;
#endif

    if (self->page.header.segment_count == 255) {
        PyErr_SetString(PyExc_ValueError,
                        "segment count cannot exceed 255");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "s#", &buffer, &buffer_len)) {
        return NULL;
    }

    if (buffer_len > 255) {
        PyErr_SetString(PyExc_ValueError,
                        "segments must be 255 bytes or less");
        return NULL;
    }

    self->page.header.segment_lengths[self->page.header.segment_count] =
        (unsigned)buffer_len;

    memcpy(self->page.segment[self->page.header.segment_count],
           buffer,
           (size_t)buffer_len);

    self->page.header.segment_count++;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
Page_full(ogg_Page *self, PyObject *args)
{
    return PyBool_FromLong(self->page.header.segment_count == 255);
}

static PyObject*
Page_size(ogg_Page *self, PyObject *args)
{
    int size = 27 + self->page.header.segment_count;
    unsigned i;

    for (i = 0; i < self->page.header.segment_count; i++)
        size += self->page.header.segment_lengths[i];

    return Py_BuildValue("i", size);
}

static PyObject*
PageReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    ogg_PageReader *self;

    self = (ogg_PageReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
PageReader_init(ogg_PageReader *self, PyObject *args, PyObject *kwds)
{
    PyObject *reader_obj;

    self->reader = NULL;

    if (!PyArg_ParseTuple(args, "O", &reader_obj))
        return -1;

    /*wrap Python object in func-based BitstreamReader*/
    Py_INCREF(reader_obj);
    self->reader = br_open_external(reader_obj,
                                    BS_LITTLE_ENDIAN,
                                    (ext_read_f)py_read,
                                    (ext_close_f)py_close,
                                    (ext_free_f)py_free);

    return 0;
}

void
PageReader_dealloc(ogg_PageReader *self)
{
    /*close BitstreamReader*/
    if (self->reader != NULL)
        self->reader->free(self->reader);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
PageReader_read(ogg_PageReader *self, PyObject *args)
{
    ogg_Page *page;
    ogg_status result;

    /*create new Page object*/
    page = (ogg_Page*)_PyObject_New(&ogg_PageType);

    /*populate Page object from stream*/
    result = read_ogg_page(self->reader, &(page->page));

    /*return Page object if no error occurs*/
    if (result == OGG_OK) {
        return (PyObject*)page;
    } else {
        page->ob_type->tp_free((PyObject*)page);
        PyErr_SetString(ogg_exception(result), ogg_strerror(result));
        return NULL;
    }
}


static PyObject*
PageReader_close(ogg_PageReader *self, PyObject *args)
{
    self->reader->close_internal_stream(self->reader);

    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject*
PageWriter_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    ogg_PageWriter *self;

    self = (ogg_PageWriter *)type->tp_alloc(type, 0);

    return (PyObject *)self;}

int
PageWriter_init(ogg_PageWriter *self, PyObject *args, PyObject *kwds)
{
    PyObject *writer_obj;

    self->writer = NULL;

    if (!PyArg_ParseTuple(args, "O", &writer_obj))
        return -1;

    /*wrap Python object in func-based BitstreamReader*/
    Py_INCREF(writer_obj);
    self->writer = bw_open_external(writer_obj,
                                    BS_LITTLE_ENDIAN,
                                    4096,
                                    (ext_write_f)py_write,
                                    (ext_flush_f)py_flush,
                                    (ext_close_f)py_close,
                                    (ext_free_f)py_free);

    return 0;
}

void
PageWriter_dealloc(ogg_PageWriter *self)
{
    /*close BitstreamWriter*/
    if (self->writer != NULL)
        self->writer->free(self->writer);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
PageWriter_write(ogg_PageWriter *self, PyObject *args)
{
    PyObject *page_obj;
    ogg_Page *page;

    /*ensure argument is Page object*/
    if (!PyArg_ParseTuple(args, "O", &page_obj)) {
        return NULL;
    } else if (page_obj->ob_type != &ogg_PageType) {
        PyErr_SetString(PyExc_TypeError, "argument must be a Page object");
        return NULL;
    } else {
        page = (ogg_Page*)page_obj;
    }

    /*write Page to stream*/
    write_ogg_page(self->writer, &page->page);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
PageWriter_flush(ogg_PageWriter *self, PyObject *args)
{
    self->writer->flush(self->writer);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
PageWriter_close(ogg_PageWriter *self, PyObject *args)
{
    self->writer->close_internal_stream(self->writer);

    Py_INCREF(Py_None);
    return Py_None;
}



PyMODINIT_FUNC
init_ogg(void)
{
    PyObject* m;

    ogg_PageType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&ogg_PageType) < 0)
        return;

    ogg_PageReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&ogg_PageReaderType) < 0)
        return ;

    ogg_PageWriterType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&ogg_PageWriterType) < 0)
        return ;

    m = Py_InitModule3("_ogg", module_methods,
                       "An Ogg page handling module");

    Py_INCREF(&ogg_PageType);
    PyModule_AddObject(m, "Page",
                       (PyObject *)&ogg_PageType);

    Py_INCREF(&ogg_PageReaderType);
    PyModule_AddObject(m, "PageReader",
                       (PyObject *)&ogg_PageReaderType);

    Py_INCREF(&ogg_PageWriterType);
    PyModule_AddObject(m, "PageWriter",
                       (PyObject *)&ogg_PageWriterType);
}


static int
py_read(PyObject *reader_obj, struct bs_buffer* buffer)
{
    PyObject *string_obj;

    /*call read() method on reader*/
    if ((string_obj = PyObject_CallMethod(reader_obj,
                                          "read", "i", 4096)) != NULL) {
        char *string;
        Py_ssize_t string_size;

        /*convert returned object to string of bytes*/
        if (PyString_AsStringAndSize(string_obj,
                                     &string,
                                     &string_size) != -1) {
            /*append bytes to buffer and return success*/
            buf_write(buffer, (uint8_t*)string, (unsigned)string_size);
            return 0;
        } else {
            /*string conversion failed*/
            PyErr_Print();
            return 1;
        }
    } else {
        /*read() method call failed*/
        PyErr_Print();
        return 1;
    }
}

int
py_write(PyObject *writer_obj, struct bs_buffer* buffer, unsigned buffer_size)
{
    while (buf_window_size(buffer) >= buffer_size) {
        PyObject* write_result =
            PyObject_CallMethod(writer_obj, "write", "s#",
                                buf_window_start(buffer),
                                buffer_size);
        if (write_result != NULL) {
            Py_DECREF(write_result);
            buffer->window_start += buffer_size;
        } else {
            PyErr_Print();
            return 1;
        }
    }

    return 0;
}

void
py_flush(PyObject *writer_obj)
{
    /*call .flush() method on writer*/
    PyObject *result = PyObject_CallMethod(writer_obj, "flush", NULL);

    if (result != NULL) {
        Py_DECREF(result);
    } else {
        PyErr_Print();
    }
}

static void
py_close(PyObject *reader_obj)
{
    PyObject *result = PyObject_CallMethod(reader_obj, "close", NULL);

    if (result != NULL) {
        Py_DECREF(result);
    } else {
        PyErr_Print();
    }
}

static void
py_free(PyObject *reader_obj)
{
    Py_DECREF(reader_obj);
}
