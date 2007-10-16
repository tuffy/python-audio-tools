#include <Python.h>
#include "samplerate/samplerate.h"

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

#include "pcmstream.h"
#include "samplerate/samplerate.c"

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
  return (long)(s[0] - 0x7F);
}

void _8bit_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i > 0x80) i = 0x80; else if (i < -0x7F) i = -0x7F;

  s[0] = (i + 0x7F) & 0xFF;
}

long char_to_16bit(unsigned char *s) {
  if ((s[1] & 0x80) != 0)
    return -(long)(0x10000 - ((s[1] << 8) | s[0])); /*negative*/
  else
    return (long)(s[1] << 8) | s[0];                /*positive*/
}

void _16bit_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i < -0x8000) i = -0x8000; else if (i > 0x7FFF) i = 0x7FFF;

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
  /*avoid overflow/underflow*/
  if (i < -0x800000) i = -0x800000; else if (i > 0x7FFFFF) i = 0x7FFFFF;

  s[0] = i & 0x0000FF;
  s[1] = (i & 0x00FF00) >> 8;
  s[2] = (i & 0xFF0000) >> 16;
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
  int quality;
  double ratio;

  if (!PyArg_ParseTuple(args, "idi", &channels, &ratio, &quality))
    return -1;

  if (channels < 1) {
    PyErr_SetString(PyExc_ValueError,
		    "channel count must be greater than 1");
    return -1;
  }
  if ((quality < 0) || (quality > 4)) {
    PyErr_SetString(PyExc_ValueError,
		    "quality must be between 0 and 4");
    return -1;
  }

  self->src_state = src_new(0,channels,&error);
  self->channels = channels;
  self->ratio = ratio;

  return 0;
}


#define OUTPUT_SAMPLES_LENGTH 0x100000

static PyObject *Resampler_process(pcmstream_Resampler* self, 
				   PyObject *args) {
  PyObject *samples_object;
  /*PyObject *samples_list;*/
  int samples_list_size;
  int last;

  SRC_DATA src_data;
  int processing_error;

  static float data_out[OUTPUT_SAMPLES_LENGTH];

  Py_ssize_t i,j;

  PyObject *processed_samples;
  PyObject *unprocessed_samples;
  PyObject *toreturn;
  PyObject *sample;


  /*grab (samples[],last) passed in from the method call*/
  if (!PyArg_ParseTuple(args,"Oi",&samples_object,&last))
    return NULL;


  /*ensure samples_object is a sequence*/
  if (!PySequence_Check(samples_object)) {
    PyErr_SetString(PyExc_TypeError,
		    "samples must be a sequence");
    Py_XDECREF(samples_object);
    return NULL;
  }


  /*grab the size of samples_object*/
  samples_list_size = PySequence_Size(samples_object);
  if (samples_list_size == -1) {
    PyErr_SetString(PyExc_ValueError,
		    "samples list must have a valid length");
    Py_XDECREF(samples_object);
    return NULL;
  }


  /*build SRC_DATA from our inputs*/
  src_data.data_in = (float *)malloc(samples_list_size * sizeof(float));

  if (src_data.data_in == NULL) {
    PyErr_SetString(PyExc_MemoryError,"out of memory");
    Py_XDECREF(samples_object);
    return NULL;
  }

  src_data.data_out = data_out;
  src_data.input_frames = samples_list_size / self->channels;
  src_data.output_frames = OUTPUT_SAMPLES_LENGTH / self->channels;
  src_data.end_of_input = last;
  src_data.src_ratio = self->ratio;

  for (i = 0; i < samples_list_size; i++) {
    sample = PySequence_ITEM(samples_object,i);

    if (sample == NULL) {
      /*IndexError trying to get item "i"*/
      Py_DECREF(samples_object);
      return NULL;
    } else {
      if (PyFloat_Check(sample)) {
	src_data.data_in[i] = (float)PyFloat_AS_DOUBLE(sample);
	Py_DECREF(sample);
      } else {
	/*our sample isn't a float*/
	Py_DECREF(samples_object);
	Py_DECREF(sample);
	PyErr_SetString(PyExc_ValueError,
			"samples must be floating point numbers");
	return NULL;
      }
    }
  }


  /*now that we've transferred everything from samples_object to src_data,
    we no longer need samples_object*/
  Py_DECREF(samples_object);


  /*run src_process() on our self->SRC_STATE and SRC_DATA*/
  if ((processing_error = src_process(self->src_state,&src_data)) != 0) {
    /*some sort of processing error raises ValueError*/
    free(src_data.data_in);
    
    PyErr_SetString(PyExc_ValueError,
		    src_strerror(processing_error));
    return NULL;
  }


  /*turn our processed and unprocessed data into two new arrays*/
  processed_samples = PyList_New((Py_ssize_t)src_data.output_frames_gen * self->channels);
  unprocessed_samples = PyList_New((Py_ssize_t)((src_data.input_frames - src_data.input_frames_used) * self->channels));
  
  /*successfully processed samples*/
  for (i = 0; i < src_data.output_frames_gen * self->channels; i++) {
    PyList_SET_ITEM(processed_samples,i,
		    PyFloat_FromDouble((double)src_data.data_out[i]));
  }

  /*not-yet-successfully processed samples*/
  for (i = src_data.input_frames_used * self->channels,j=0;
       i < (src_data.input_frames * self->channels);
       i++,j++) {
    PyList_SET_ITEM(unprocessed_samples,j,
		    PyFloat_FromDouble((double)src_data.data_in[i]));
  }
  

  /*cleanup anything allocated*/
  free(src_data.data_in);


  /*return those two arrays as a tuple*/
  toreturn = PyTuple_Pack(2,processed_samples,unprocessed_samples);

  return toreturn;
}
