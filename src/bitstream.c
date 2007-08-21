#include <Python.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007  Brian Langenberger

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

typedef struct {
  PyObject_HEAD
  PyObject *substream; /*the Python file object to get new bytes from*/
  char buffer[8];      /*our internal bit buffer*/
  int buffer_index;    /*a value from 0-7*/
  int buffer_length;   /*another value from 0-7*/
  /*index and length form a sliding window on the buffer
    reading bits increases the index until it hits the total length
    adding new bits means resetting the index and setting the
    buffer and length to the new bits' value
   */
} bitstream_BitStreamReader;

static void BitStreamReader_dealloc(bitstream_BitStreamReader* self);
static PyObject *BitStreamReader_new(PyTypeObject *type, 
				     PyObject *args, PyObject *kwds);
static int BitStreamReader_init(bitstream_BitStreamReader *self, 
				PyObject *args, PyObject *kwds);

static PyObject *BitStreamReader_close(bitstream_BitStreamReader* self);

static PyObject *BitStreamReader_tell(bitstream_BitStreamReader* self);

static PyObject *BitStreamReader_seek(bitstream_BitStreamReader* self, 
				      PyObject *args, PyObject *kwds);

static PyObject *BitStreamReader_read(bitstream_BitStreamReader* self, 
				      PyObject *args);

static PyObject *BitStreamReader_ungetc(bitstream_BitStreamReader* self,
					PyObject *args);

static PyObject *BitStreamReader_buffer(bitstream_BitStreamReader* self);

char *remaining_bits(bitstream_BitStreamReader *reader);
int remaining_bits_length(bitstream_BitStreamReader *reader);

void bytes_to_bits(char *bytes, Py_ssize_t bytes_length, char *bits);

static PyMethodDef module_methods[] = {
  {NULL}
};

static PyMethodDef BitStreamReader_methods[] = {
  {"close", (PyCFunction)BitStreamReader_close,
   METH_NOARGS,"Closes the BitStreamReader and substream"},
  {"tell", (PyCFunction)BitStreamReader_tell,
   METH_NOARGS,"Returns the current position in the substream"},
  {"seek", (PyCFunction)BitStreamReader_seek,
   METH_VARARGS | METH_KEYWORDS,"Seeks to a new position in the substream"},
  {"read", (PyCFunction)BitStreamReader_read,
   METH_VARARGS,"Reads the given number of bits from the substream"},
  {"buffer", (PyCFunction)BitStreamReader_buffer,
   METH_NOARGS, "Gets the current bit buffer as a string"},
  {"ungetc", (PyCFunction)BitStreamReader_ungetc,
   METH_VARARGS,"Pushes a single bit character back into the stream"},
  {NULL}
};


static PyTypeObject bitstream_BitStreamReaderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "bitstream.BitStreamReader", /*tp_name*/
    sizeof(bitstream_BitStreamReader), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)BitStreamReader_dealloc, /*tp_dealloc*/
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
    "BitStreamReader objects", /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    BitStreamReader_methods,   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)BitStreamReader_init, /* tp_init */
    0,                         /* tp_alloc */
    BitStreamReader_new,       /* tp_new */
};



#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

PyMODINIT_FUNC initbitstream(void) {
    PyObject* m;

    bitstream_BitStreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&bitstream_BitStreamReaderType) < 0)
        return;

    m = Py_InitModule3("bitstream", module_methods,
                       "A bit stream reading module.");

    Py_INCREF(&bitstream_BitStreamReaderType);
    PyModule_AddObject(m, "BitStreamReader", 
		       (PyObject *)&bitstream_BitStreamReaderType);
}

static PyObject *BitStreamReader_new(PyTypeObject *type, 
				     PyObject *args, PyObject *kwds) {
  bitstream_BitStreamReader *self;

  self = (bitstream_BitStreamReader *)type->tp_alloc(type, 0);
  
  return (PyObject *)self;
}

static int BitStreamReader_init(bitstream_BitStreamReader *self, 
				PyObject *args, PyObject *kwds) {
  PyObject *substream = NULL;

  if (!PyArg_ParseTuple(args, "O", &substream))
    return -1;

  Py_INCREF(substream);
  self->substream = substream;
  self->buffer_length = 0;
  self->buffer_index = 0;

  return 0;
}

static void
BitStreamReader_dealloc(bitstream_BitStreamReader* self)
{
  Py_DECREF(self->substream);
  self->ob_type->tp_free((PyObject*)self);
}

static PyObject *BitStreamReader_close(bitstream_BitStreamReader* self) {
  return PyObject_CallMethod(self->substream,"close",NULL);
}

static PyObject *BitStreamReader_tell(bitstream_BitStreamReader* self) {
  return PyObject_CallMethod(self->substream,"tell",NULL);
}

static PyObject *BitStreamReader_seek(bitstream_BitStreamReader* self, 
				      PyObject *args,
				      PyObject *kwds) {
  static long int position = 0;
  static long int whence = 0;
  static char *kwlist[] = {"pos", "whence", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kwds, "l|l", kwlist,
				   &position, &whence))
    return NULL;

  self->buffer_index = 0;
  self->buffer_length = 0;

  return PyObject_CallMethod(self->substream,"seek", "(l,l)",
			     position, whence);
}

static PyObject *BitStreamReader_buffer(bitstream_BitStreamReader* self) {
  return PyString_FromStringAndSize(remaining_bits(self),
				    remaining_bits_length(self));
}

static PyObject *BitStreamReader_read(bitstream_BitStreamReader* self, 
				      PyObject *args) {
  static long int read_count = 0;
  Py_ssize_t bytes_to_read;

  char *byte_buffer;
  Py_ssize_t byte_length;

  PyObject *read_data = NULL;  /*input string from the file object*/

  char *bit_buffer;
  Py_ssize_t bit_length;

  char *leftover_bits;
  Py_ssize_t leftover_bits_length;

  PyObject *bit_string = NULL; /*output string to the user*/

  /*get the number of bits to read*/
  if (!PyArg_ParseTuple(args,"l",&read_count))
    return NULL;

  if (read_count > remaining_bits_length(self)) {
    /*If there's not enough bits in the buffer,
      we need to fetch at least 1 more byte.*/

    bytes_to_read = ((read_count - remaining_bits_length(self)) / 8);

    if (((read_count - remaining_bits_length(self)) % 8) > 0)
      bytes_to_read++;

    if (bytes_to_read < 1) bytes_to_read = 1;

    read_data = PyObject_CallMethod(self->substream,"read","l", 
				    bytes_to_read);

    if (read_data == NULL)
      return NULL;

    /*convert the returned Python object into a C string (with length)*/
    if (PyString_AsStringAndSize(read_data,
				 &byte_buffer,&byte_length) == -1) {
      Py_DECREF(read_data);
      return NULL;
    }

    Py_DECREF(read_data);

    /*Combine our new bytes with the contents of our internel bit buffer
      into one continual bit_buffer.
      This buffer may be larger than the user's request.
    */
    bit_length = (byte_length * 8) + remaining_bits_length(self);
    bit_buffer = (char *)malloc(bit_length);

    /*add the old bits*/
    memcpy(bit_buffer,remaining_bits(self),(size_t)remaining_bits_length(self));

    /*add the new bits*/
    bytes_to_bits(byte_buffer, byte_length, 
		  bit_buffer + remaining_bits_length(self));

    /*mark old bits as consumed*/
    self->buffer_index = 0;
    self->buffer_length = 0;

    /*If the request is larger than the number of bits we've received
      (which happens at the end of the stream)
      reduce the request accordingly.*/
    if (read_count > bit_length)
      read_count = bit_length;

    /*grab up to the requested number of bits to a Python
      string for returning to the user*/
    bit_string = PyString_FromStringAndSize(bit_buffer,
					    read_count);

    /*toss any remaining bits into our internal buffer*/
    leftover_bits = bit_buffer + read_count;
    leftover_bits_length = bit_length - read_count;

    memcpy(self->buffer,leftover_bits,(size_t)leftover_bits_length);

    self->buffer_index = 0;
    self->buffer_length = leftover_bits_length;

    free(bit_buffer);
  } else {
    /*if there are enough bits in the buffer,
      return those bits and increment the index*/
    bit_string = PyString_FromStringAndSize(remaining_bits(self),
					    read_count);
    self->buffer_index += read_count;
  }

  return bit_string;
}

static PyObject *BitStreamReader_ungetc(bitstream_BitStreamReader* self,
					PyObject *args) {
  char *bit;
  int bit_length;

  int old_length;
  
  if (!PyArg_ParseTuple(args,"s#",&bit,&bit_length))
    return NULL;

  if (bit_length != 1) {
    PyErr_SetString(PyExc_ValueError,"bit string must be exactly 1");
    return NULL;
  }

  if (remaining_bits_length(self) >= 8) {
    PyErr_SetString(PyExc_ValueError,"no more characters can be ungotten");
    return NULL;
  }

  old_length = remaining_bits_length(self);

  memmove(self->buffer + 1, remaining_bits(self), remaining_bits_length(self));

  if (bit[0] == (char)0)
    self->buffer[0] = (char)0;
  else
    self->buffer[0] = (char)1;
  
  self->buffer_index = 0;
  self->buffer_length = old_length + 1;

  Py_INCREF(Py_None);
  return Py_None;
}


/*takes a set of bytes and length,
  converts those bytes to bits in the bits array*/
void bytes_to_bits(char *bytes, Py_ssize_t bytes_length, char *bits) {
  int bit;
  int byte;
  int i;

  for (byte = 0,bit=0; byte < bytes_length; byte++) {
    for (i = 7; i >= 0; i--,bit++) {
      bits[bit] = ((bytes[byte] & (1 << i)) >> i);
    }
  }
}

char *remaining_bits(bitstream_BitStreamReader *reader) {
  return reader->buffer + reader->buffer_index;
}

int remaining_bits_length(bitstream_BitStreamReader *reader) {
  return reader->buffer_length - reader->buffer_index;
}
