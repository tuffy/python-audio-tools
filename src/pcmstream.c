#include <Python.h>
#include "samplerate.h"

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

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/*PCMStreamReader definitions*/
typedef struct {
  PyObject_HEAD
  PyObject *substream;        /*the Python file object to get new samples from*/
  int sample_size;            /*the size of each PCM sample, in bytes*/
  char unhandled_bytes[3];    /*any partial PCM samples*/
  int unhandled_bytes_length; /*how many partial PCM bytes we have*/
} pcmstream_PCMStreamReader;

static void PCMStreamReader_dealloc(pcmstream_PCMStreamReader* self);

static PyObject *PCMStreamReader_new(PyTypeObject *type, 
				     PyObject *args, PyObject *kwds);

static int PCMStreamReader_init(pcmstream_PCMStreamReader *self, 
				PyObject *args, PyObject *kwds);

static PyObject *PCMStreamReader_close(pcmstream_PCMStreamReader* self);

static PyObject *PCMStreamReader_tell(pcmstream_PCMStreamReader* self);

static PyObject *PCMStreamReader_read(pcmstream_PCMStreamReader* self, 
				      PyObject *args);

static PyObject *PCMStreamReader_get_sample_size(
    pcmstream_PCMStreamReader *self,
    void *closure);

static PyObject *pcm_to_string(PyObject *dummy, PyObject *args);

long char_to_16bit(unsigned char *s);
void _16bit_to_char(long i, unsigned char *s);

long char_to_24bit(unsigned char *s);
void _24bit_to_char(long i, unsigned char *s);

long char_to_8bit(unsigned char *s);
void _8bit_to_char(long i, unsigned char *s);


/*Resampler definitions*/

typedef struct {
  PyObject_HEAD
  SRC_STATE *src_state;
  int channels;
} pcmstream_Resampler;

static void Resampler_dealloc(pcmstream_Resampler* self);

static PyObject *Resampler_new(PyTypeObject *type, 
			       PyObject *args, PyObject *kwds);

static int Resampler_init(pcmstream_Resampler *self, 
			  PyObject *args, PyObject *kwds);

static PyObject *Resampler_process(pcmstream_Resampler* self, 
				   PyObject *args);

static PyMethodDef module_methods[] = {
  {"pcm_to_string",(PyCFunction)pcm_to_string,
   METH_VARARGS,"Converts PCM integers to a string of PCM data."},
  {NULL}
};

static PyGetSetDef PCMStreamReader_getseters[] = {
    {"sample_size", 
     (getter)PCMStreamReader_get_sample_size, 0,
     "sample size",
     NULL},
    {NULL}  /* Sentinel */
};

static PyMethodDef PCMStreamReader_methods[] = {
  {"close", (PyCFunction)PCMStreamReader_close,
   METH_NOARGS,"Closes the PCMStreamReader and substream"},
  {"tell", (PyCFunction)PCMStreamReader_tell,
   METH_NOARGS,"Returns the current position in the substream"},
  {"read", (PyCFunction)PCMStreamReader_read,
   METH_VARARGS,"Reads the given number of bits from the substream"},
  {NULL}
};

static PyMethodDef Resampler_methods[] = {
  {"process", (PyCFunction)Resampler_process,
   METH_VARARGS,"Processes PCM samples into the new sample rate"},
  {NULL}
};

static PyTypeObject pcmstream_PCMStreamReaderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmstream.PCMStreamReader", /*tp_name*/
    sizeof(pcmstream_PCMStreamReader), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)PCMStreamReader_dealloc, /*tp_dealloc*/
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
    "PCMStreamReader objects", /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    PCMStreamReader_methods,   /* tp_methods */
    0,                         /* tp_members */
    PCMStreamReader_getseters, /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)PCMStreamReader_init, /* tp_init */
    0,                         /* tp_alloc */
    PCMStreamReader_new,       /* tp_new */
};


static PyTypeObject pcmstream_ResamplerType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmstream.Resampler", /*tp_name*/
    sizeof(pcmstream_Resampler), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Resampler_dealloc, /*tp_dealloc*/
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
    "Resampler objects",       /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    Resampler_methods,         /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Resampler_init,  /* tp_init */
    0,                         /* tp_alloc */
    Resampler_new,       /* tp_new */
};


#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

PyMODINIT_FUNC initpcmstream(void) {
    PyObject* m;

    pcmstream_PCMStreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmstream_PCMStreamReaderType) < 0)
      return;

    pcmstream_ResamplerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmstream_ResamplerType) < 0)
      return;

    m = Py_InitModule3("pcmstream", module_methods,
                       "A PCM stream reading, writing and editing module.");

    Py_INCREF(&pcmstream_PCMStreamReaderType);
    Py_INCREF(&pcmstream_ResamplerType);
    PyModule_AddObject(m, "PCMStreamReader", 
		       (PyObject *)&pcmstream_PCMStreamReaderType);
    PyModule_AddObject(m, "Resampler", 
		       (PyObject *)&pcmstream_ResamplerType);
}


static PyObject *PCMStreamReader_new(PyTypeObject *type, 
				     PyObject *args, PyObject *kwds) {
  pcmstream_PCMStreamReader *self;

  self = (pcmstream_PCMStreamReader *)type->tp_alloc(type, 0);
  
  return (PyObject *)self;
}

static int PCMStreamReader_init(pcmstream_PCMStreamReader *self, 
				PyObject *args, PyObject *kwds) {
  PyObject *substream = NULL;
  int sample_size;

  if (!PyArg_ParseTuple(args, "Oi", &substream,&sample_size))
    return -1;

  if (sample_size > 3) {
    PyErr_SetString(PyExc_ValueError,
		    "sample size cannot be greater than 3 bytes");
    return -1;
  }

  Py_INCREF(substream);
  self->substream = substream;
  self->unhandled_bytes_length = 0;
  self->sample_size = sample_size;

  return 0;
}

static void
PCMStreamReader_dealloc(pcmstream_PCMStreamReader* self)
{
  Py_XDECREF(self->substream);
  self->ob_type->tp_free((PyObject*)self);
}

static PyObject *PCMStreamReader_get_sample_size(
    pcmstream_PCMStreamReader *self,
    void *closure) {
  PyObject *sample_size;
  sample_size = Py_BuildValue("i",self->sample_size);
  return sample_size;
}

static PyObject *PCMStreamReader_close(pcmstream_PCMStreamReader* self) {
  return PyObject_CallMethod(self->substream,"close",NULL);
}

static PyObject *PCMStreamReader_tell(pcmstream_PCMStreamReader* self) {
  return PyObject_CallMethod(self->substream,"tell",NULL);
}

static PyObject *PCMStreamReader_read(pcmstream_PCMStreamReader* self, 
				      PyObject *args) {
  long int read_count;

  PyObject *list;
  PyObject *read_string;

  char *read_data;
  Py_ssize_t read_data_length;

  unsigned char *pcm_data;
  Py_ssize_t pcm_data_length;

  Py_ssize_t pcm_array_length;

  Py_ssize_t input = 0;
  Py_ssize_t output = 0;

  /*get the number of bytes to read*/
  if (!PyArg_ParseTuple(args,"l",&read_count))
    return NULL;

  read_string = PyObject_CallMethod(self->substream,"read","l",read_count);
  if (read_string == NULL) return NULL;

  if (PyString_AsStringAndSize(read_string,
			       &read_data, 
			       &read_data_length) == -1) {
    Py_DECREF(read_string);
    return NULL;
  }

  pcm_data_length = read_data_length + self->unhandled_bytes_length;
  pcm_data = (unsigned char *)calloc(pcm_data_length,sizeof(unsigned char));

  /*copy any old bytes to the pcm_data string*/
  if (self->unhandled_bytes_length > 0)
    memcpy(pcm_data, self->unhandled_bytes, 
	   (size_t)self->unhandled_bytes_length);

  /*add the new bytes to the pcm_data string, if any*/
  if (read_data_length > 0)
    memcpy(pcm_data + self->unhandled_bytes_length,
	   read_data, (size_t)read_data_length);

  /*make a new array long enough to hold our PCM values*/
  pcm_array_length = pcm_data_length / self->sample_size;
  list = PyList_New((Py_ssize_t)pcm_array_length);

  /*fill that array with values from the PCM stream*/
  switch(self->sample_size) {
  case 1:
    for (input = 0,output=0; 
	 (input < pcm_data_length) && (output < pcm_array_length);
	 input++,output++) {
      PyList_SET_ITEM(list, output,
		      PyInt_FromLong(char_to_8bit(pcm_data + input)));
    }
    break;
  case 2:
    for (input = 0,output=0; 
	 (input < pcm_data_length) && (output < pcm_array_length);
	 input += 2,output++) {
      PyList_SET_ITEM(list, output, 
		      PyInt_FromLong(char_to_16bit(pcm_data + input)));
    }
    break;
  case 3:
    for (input = 0,output=0; 
	 (input < pcm_data_length) && (output < pcm_array_length);
	 input += 3,output++) {
      PyList_SET_ITEM(list, output, 
		      PyInt_FromLong(char_to_24bit(pcm_data + input)));
    }
    break;
  }
  
  /*any leftover bytes are saved for next time*/
  if (input < pcm_data_length) {
    self->unhandled_bytes_length = pcm_data_length - input;

    memcpy(self->unhandled_bytes,pcm_data + input,
	   self->unhandled_bytes_length);
  } else {
    self->unhandled_bytes_length = 0;
  }

  /*remove the string we've read in*/
  Py_DECREF(read_string);

  /*remove the old PCM stream*/
  free(pcm_data);

  /*return our new list*/
  return list;
}

static PyObject *pcm_to_string(PyObject *dummy, PyObject *args) {
  PyObject *pcm_list = NULL;
  int sample_size;

  PyObject *fast_list = NULL;
  int fast_list_size;

  unsigned char *pcm_data;
  int pcm_data_length;

  PyObject *output_string;

  int input = 0;
  int output = 0;
  long item;

  /*grab our input data as a fast Sequence*/
  if (!PyArg_ParseTuple(args,"Oi",&pcm_list,&sample_size))
    return NULL;

  if (sample_size > 3) {
    PyErr_SetString(PyExc_ValueError,
		    "sample size cannot be greater than 3 bytes");
    Py_DECREF(pcm_list);
    return NULL;
  }

  fast_list = PySequence_Fast(pcm_list,"samples are not a list");
  if (fast_list == NULL) {
    Py_DECREF(pcm_list);
    return NULL;
  }


  /*build a character string to hold our data*/
  fast_list_size = PySequence_Fast_GET_SIZE(fast_list);
  pcm_data_length = fast_list_size * sample_size;
  pcm_data = (unsigned char *)calloc(pcm_data_length,sizeof(unsigned char));

  /*perform the int->PCM data conversion*/
  switch (sample_size) {
  case 1:
    for (input = 0,output = 0;
	 (input < fast_list_size) && (output < pcm_data_length);
	 input++,output++) {
      item = PyInt_AsLong(PySequence_Fast_GET_ITEM(fast_list,input));
      if ((item == -1) && (PyErr_Occurred())) {
	Py_DECREF(fast_list);
	Py_DECREF(pcm_list);
	free(pcm_data);
	return NULL;
      }
      _8bit_to_char(item,pcm_data + output);
    }
    break;
  case 2:
    for (input = 0,output = 0;
	 (input < fast_list_size) && (output < pcm_data_length);
	 input++,output += 2) {
      item = PyInt_AsLong(PySequence_Fast_GET_ITEM(fast_list,input));
      if ((item == -1) && (PyErr_Occurred())) {
	Py_DECREF(fast_list);
	Py_DECREF(pcm_list);
	free(pcm_data);
	return NULL;
      }
      _16bit_to_char(item,pcm_data + output);
    }
    break;
  case 3:
    for (input = 0,output = 0;
	 (input < fast_list_size) && (output < pcm_data_length);
	 input++,output += 3) {
      item = PyInt_AsLong(PySequence_Fast_GET_ITEM(fast_list,input));
      if ((item == -1) && (PyErr_Occurred())) {
	Py_DECREF(fast_list);
	Py_DECREF(pcm_list);
	free(pcm_data);
	return NULL;
      }
      _24bit_to_char(item,pcm_data + output);
    }
    break;
  }

  /*build our output string and free all the junk we've allocated*/
  output_string = PyString_FromStringAndSize((char *)pcm_data,pcm_data_length);
  
  Py_DECREF(fast_list);
  Py_DECREF(pcm_list);
  free(pcm_data);
  
  return output_string;
}


long char_to_8bit(unsigned char *s) {
  return (long)s[0];
}

long char_to_16bit(unsigned char *s) {
  if ((s[1] & 0x80) != 0)
    return -(long)(0x10000 - ((s[1] << 8) | s[0])); /*negative*/
  else
    return (long)(s[1] << 8) | s[0];                /*positive*/
}

void _16bit_to_char(long i, unsigned char *s) {
  s[0] = i & 0x00FF;
  s[1] = (i & 0xFF00) >> 8;
}

long char_to_24bit(unsigned char *s) {
  if ((s[2] & 0x80) != 0)
    return -(long)(0x1000000 - ((s[2] << 16) | (s[1] << 8) | s[0]));/*negative*/
  else
    return (long)(s[2] << 16) | (s[1] << 8) | s[0];                 /*positive*/
}

void _24bit_to_char(long i, unsigned char *s) {
  s[0] = i & 0x0000FF;
  s[1] = (i & 0x00FF00) >> 8;
  s[2] = (i & 0xFF0000) >> 16;
}


void _8bit_to_char(long i, unsigned char *s) {
  s[0] = i & 0xFF;
}



static void Resampler_dealloc(pcmstream_Resampler* self) {
  src_delete(self->src_state);
  self->ob_type->tp_free((PyObject*)self);
}

static PyObject *Resampler_new(PyTypeObject *type, 
			       PyObject *args, PyObject *kwds) {
  pcmstream_Resampler *self;

  self = (pcmstream_Resampler *)type->tp_alloc(type, 0);
  
  return (PyObject *)self;
}

static int Resampler_init(pcmstream_Resampler *self, 
			  PyObject *args, PyObject *kwds) {
  int error;
  int channels;

  if (!PyArg_ParseTuple(args, "i", &channels))
    return -1;

  self->src_state = src_new(0,channels,&error);
  self->channels = channels;

  return 0;
}

static PyObject *Resampler_process(pcmstream_Resampler* self, 
				   PyObject *args) {
  PyObject *samples_list;
  double ratio;
  int last;

  /*grab (samples[],ratio,last) passed in from the method call*/
  if (!PyArg_ParseTuple(args,"Odi",&samples_list,&ratio,&last))
    return NULL;

  /*turn samples_list into an array of floats*/


  /*build SRC_DATA from our inputs*/


  /*run src_process() on our self->SRC_STATE and SRC_DATA*/


  /*turn our processed and unprocessed data into two arrays*/


  /*cleanup anything allocated*/
  Py_XDECREF(samples_list);

  /*return those two arrays as a tuple*/

  Py_INCREF(Py_None);
  return Py_None;
}
