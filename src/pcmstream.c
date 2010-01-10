#include <Python.h>
#include "samplerate/samplerate.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

#ifdef IS_PY3K

static PyModuleDef pcmstreammodule = {
    PyModuleDef_HEAD_INIT,
    "pcmstream",
    "A PCM stream reading module.",
    -1,
    NULL,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit_pcmstream(void)
{
    PyObject* m;

    pcmstream_PCMStreamReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmstream_PCMStreamReaderType) < 0)
        return NULL;

    pcmstream_ResamplerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmstream_ResamplerType) < 0)
      return NULL;

    m = PyModule_Create(&pcmstreammodule);
    if (m == NULL)
      return NULL;

    Py_INCREF(&pcmstream_PCMStreamReaderType);
    PyModule_AddObject(m, "PCMStreamReader",
		       (PyObject *)&pcmstream_PCMStreamReaderType);

    Py_INCREF(&pcmstream_ResamplerType);
    PyModule_AddObject(m, "Resampler",
		       (PyObject *)&pcmstream_ResamplerType);
    return m;
}

void
PCMStreamReader_dealloc(pcmstream_PCMStreamReader* self)
{
  Py_XDECREF(self->substream);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

#else

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

void
PCMStreamReader_dealloc(pcmstream_PCMStreamReader* self)
{
  Py_XDECREF(self->substream);
  self->ob_type->tp_free((PyObject*)self);
}

#endif

/********************************/
/*PCMStreamReader implementation*/
/********************************/


PyObject *PCMStreamReader_new(PyTypeObject *type,
			      PyObject *args, PyObject *kwds) {
  pcmstream_PCMStreamReader *self;

  self = (pcmstream_PCMStreamReader *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

int PCMStreamReader_init(pcmstream_PCMStreamReader *self,
			 PyObject *args, PyObject *kwds) {
  PyObject *substream = NULL;
  int sample_size;
  int big_endian;
  int float_output;

  if (!PyArg_ParseTuple(args, "Oiii", &substream,&sample_size,
			&big_endian,&float_output))
    return -1;

  self->substream = NULL;

  if (!float_output) {
    if (!big_endian) {
      switch (sample_size) {  /*little-endian input, int output*/
      case 1: self->char_converter = char_to_python_S8long;   break;
      case 2: self->char_converter = char_to_python_SL16long; break;
      case 3: self->char_converter = char_to_python_SL24long; break;
      default: PyErr_SetString(PyExc_ValueError,
			       "sample size must be between 1 and 3 bytes");
	return -1;
      }
    } else {
      switch (sample_size) {  /*big-endian input, int output*/
      case 1: self->char_converter = char_to_python_S8long;   break;
      case 2: self->char_converter = char_to_python_SB16long; break;
      case 3: self->char_converter = char_to_python_SB24long; break;
      default: PyErr_SetString(PyExc_ValueError,
			       "sample size must be between 1 and 3 bytes");
	return -1;
      }
    }
  } else {
    if (!big_endian) {
      switch (sample_size) {  /*little-endian input, float output*/
      case 1: self->char_converter = char_to_python_S8float;   break;
      case 2: self->char_converter = char_to_python_SL16float; break;
      case 3: self->char_converter = char_to_python_SL24float; break;
      default: PyErr_SetString(PyExc_ValueError,
			       "sample size must be between 1 and 3 bytes");
	return -1;
      }
    } else {
      switch (sample_size) {  /*big-endian input, float output*/
      case 1: self->char_converter = char_to_python_S8float;   break;
      case 2: self->char_converter = char_to_python_SB16float; break;
      case 3: self->char_converter = char_to_python_SB24float; break;
      default: PyErr_SetString(PyExc_ValueError,
			       "sample size must be between 1 and 3 bytes");
	return -1;
      }
    }
  }

  Py_INCREF(substream);
  self->substream = substream;
  self->unhandled_bytes_length = 0;
  self->sample_size = sample_size;

  return 0;
}

PyObject *PCMStreamReader_get_sample_size(
    pcmstream_PCMStreamReader *self,
    void *closure) {
  PyObject *sample_size;
  sample_size = Py_BuildValue("i",self->sample_size);
  return sample_size;
}

PyObject *PCMStreamReader_close(pcmstream_PCMStreamReader* self) {
  return PyObject_CallMethod(self->substream,"close",NULL);
}

PyObject *PCMStreamReader_tell(pcmstream_PCMStreamReader* self) {
  return PyObject_CallMethod(self->substream,"tell",NULL);
}

PyObject *PCMStreamReader_read(pcmstream_PCMStreamReader* self,
				      PyObject *args) {
  long read_count;

  PyObject *list;
  PyObject *read_string;
  PyObject *long_obj;

  char *read_data;
  Py_ssize_t read_data_length;

  unsigned char *pcm_data;
  Py_ssize_t pcm_data_length;

  Py_ssize_t pcm_array_length;

  Py_ssize_t input = 0;
  Py_ssize_t output = 0;

  PyObject *(*char_converter)(unsigned char *s);
  int sample_size;

  /*get the number of bytes to read*/
  if (!PyArg_ParseTuple(args,"l",&read_count))
    return NULL;

  read_string = PyObject_CallMethod(self->substream,"read","l",read_count);
  if (read_string == NULL) return NULL;

#ifdef IS_PY3K
  if (PyBytes_AsStringAndSize(read_string,
			      &read_data,
			      &read_data_length) == -1) {
    Py_DECREF(read_string);
    return NULL;
  }
#else
  if (PyString_AsStringAndSize(read_string,
			       &read_data,
			       &read_data_length) == -1) {
    Py_DECREF(read_string);
    return NULL;
  }
#endif

  pcm_data_length = read_data_length + self->unhandled_bytes_length;
  pcm_data = (unsigned char *)malloc(pcm_data_length);

  if (pcm_data == NULL) {
    PyErr_SetString(PyExc_MemoryError,"out of memory");
    Py_XDECREF(read_string);
    return NULL;
  }

  char_converter = self->char_converter;
  sample_size = self->sample_size;

  /*copy any old bytes to the pcm_data string*/
  if (self->unhandled_bytes_length > 0)
    memcpy(pcm_data, self->unhandled_bytes,
	   (size_t)self->unhandled_bytes_length);

  /*add the new bytes to the pcm_data string, if any*/
  if (read_data_length > 0)
    memcpy(pcm_data + self->unhandled_bytes_length,
	   read_data, (size_t)read_data_length);

  /*remove the string we've read in*/
  Py_DECREF(read_string);


   /*make a new array long enough to hold our PCM values*/
   pcm_array_length = pcm_data_length / self->sample_size;
   list = PyList_New((Py_ssize_t)pcm_array_length);
   if (list == NULL) {
     free(pcm_data);
     return NULL;
   }

   /*fill that array with values from the PCM stream*/
  for (input = 0,output=0;
       (input < pcm_data_length) && (output < pcm_array_length);
       input += sample_size,output++) {
    long_obj = char_converter(pcm_data + input);
    if (PyList_SetItem(list, output,long_obj) == -1) {
      free(pcm_data);
      return NULL;
    }
  }

  /*any leftover bytes are saved for next time*/
  if (input < pcm_data_length) {
    self->unhandled_bytes_length = pcm_data_length - input;

    memcpy(self->unhandled_bytes,pcm_data + input,
	   self->unhandled_bytes_length);
  } else {
    self->unhandled_bytes_length = 0;
  }

  /*remove the old PCM stream*/
  free(pcm_data);

  /*return our new list*/
  return list;
}

PyObject *pcm_to_string(PyObject *dummy, PyObject *args) {
  PyObject *pcm_list = NULL;
  int sample_size;
  void (*long_to_char)(long i, unsigned char *s) = SL16long_to_char;
  int big_endian;

  PyObject *fast_list = NULL;
  int fast_list_size;

  unsigned char *pcm_data;
  int pcm_data_length;

  PyObject *output_string;

  int input = 0;
  int output = 0;
  long item;

  /*grab our input data as a fast Sequence*/
  if (!PyArg_ParseTuple(args,"Oii",&pcm_list,&sample_size,&big_endian))
    return NULL;

  if (!big_endian) {
    switch (sample_size) {
    case 1: long_to_char = S8long_to_char;   break;
    case 2: long_to_char = SL16long_to_char; break;
    case 3: long_to_char = SL24long_to_char; break;
    default: PyErr_SetString(PyExc_ValueError,
			     "sample size must be between 1 and 3 bytes");
      return NULL;
    }
  } else {
    switch (sample_size) {
    case 1: long_to_char = S8long_to_char;   break;
    case 2: long_to_char = SB16long_to_char; break;
    case 3: long_to_char = SB24long_to_char; break;
    default: PyErr_SetString(PyExc_ValueError,
			     "sample size must be between 1 and 3 bytes");
      return NULL;
    }
  }

  fast_list = PySequence_Fast(pcm_list,"samples are not a list");
  if (fast_list == NULL) {
    return NULL;
  }


  /*build a character string to hold our data*/
  fast_list_size = PySequence_Fast_GET_SIZE(fast_list);
  pcm_data_length = fast_list_size * sample_size;
  pcm_data = (unsigned char *)calloc(pcm_data_length,sizeof(unsigned char));


  /*perform the int->PCM data conversion*/
  for (input = 0,output = 0;
       (input < fast_list_size) && (output < pcm_data_length);
       input++,output += sample_size) {
#ifdef IS_PY3K
    item = PyLong_AsLong(PySequence_Fast_GET_ITEM(fast_list,input));
#else
    item = PyInt_AsLong(PySequence_Fast_GET_ITEM(fast_list,input));
#endif
    if ((item == -1) && (PyErr_Occurred())) {
      Py_DECREF(fast_list);
      free(pcm_data);
      return NULL;
    }
    long_to_char(item,pcm_data + output);
  }


  /*build our output string and free all the junk we've allocated*/
#ifdef IS_PY3K
  output_string = PyBytes_FromStringAndSize((char *)pcm_data,pcm_data_length);
#else
  output_string = PyString_FromStringAndSize((char *)pcm_data,pcm_data_length);
#endif

  Py_DECREF(fast_list);
  free(pcm_data);

  return output_string;
}


long char_to_S8long(unsigned char *s) {
  return (long)(s[0] - 0x7F);
}

PyObject *char_to_python_S8long(unsigned char *s) {
#ifdef IS_PY3K
  return PyLong_FromLong(char_to_S8long(s));
#else
  return PyInt_FromLong(char_to_S8long(s));
#endif
}

PyObject *char_to_python_S8float(unsigned char *s) {
  return PyFloat_FromDouble(((double)char_to_S8long(s)) / (double)128);
}

void S8long_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i > 0x80) i = 0x80; else if (i < -0x7F) i = -0x7F;

  s[0] = (i + 0x7F) & 0xFF;
}

long char_to_SL16long(unsigned char *s) {
  if ((s[1] & 0x80) != 0)
    return -(long)(0x10000 - ((s[1] << 8) | s[0])); /*negative*/
  else
    return (long)(s[1] << 8) | s[0];                /*positive*/
}

PyObject *char_to_python_SL16long(unsigned char *s) {
#ifdef IS_PY3K
  return PyLong_FromLong(char_to_SL16long(s));
#else
  return PyInt_FromLong(char_to_SL16long(s));
#endif
}

PyObject *char_to_python_SL16float(unsigned char *s) {
  return PyFloat_FromDouble(((double)char_to_SL16long(s)) / (double)32768);
}

void SL16long_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i < -0x8000) i = -0x8000; else if (i > 0x7FFF) i = 0x7FFF;

  s[0] = i & 0x00FF;
  s[1] = (i & 0xFF00) >> 8;
}

long char_to_SL24long(unsigned char *s) {
  if ((s[2] & 0x80) != 0)
    return -(long)(0x1000000 - ((s[2] << 16) | (s[1] << 8) | s[0]));/*negative*/
  else
    return (long)(s[2] << 16) | (s[1] << 8) | s[0];                 /*positive*/
}

PyObject *char_to_python_SL24long(unsigned char *s) {
#ifdef IS_PY3K
  return PyLong_FromLong(char_to_SL24long(s));
#else
  return PyInt_FromLong(char_to_SL24long(s));
#endif
}

PyObject *char_to_python_SL24float(unsigned char *s) {
  return PyFloat_FromDouble(((double)char_to_SL24long(s)) / (double)8388608);
}

void SL24long_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i < -0x800000) i = -0x800000; else if (i > 0x7FFFFF) i = 0x7FFFFF;

  s[0] = i & 0x0000FF;
  s[1] = (i & 0x00FF00) >> 8;
  s[2] = (i & 0xFF0000) >> 16;
}

long char_to_SB16long(unsigned char *s) {
  if ((s[0] & 0x80) != 0)
    return -(long)(0x10000 - ((s[0] << 8) | s[1])); /*negative*/
  else
    return (long)(s[0] << 8) | s[1];                /*positive*/
}

PyObject *char_to_python_SB16long(unsigned char *s) {
#ifdef IS_PY3K
  return PyLong_FromLong(char_to_SB16long(s));
#else
  return PyInt_FromLong(char_to_SB16long(s));
#endif
}

PyObject *char_to_python_SB16float(unsigned char *s) {
  return PyFloat_FromDouble(((double)char_to_SB16long(s)) / (double)32768);
}

void SB16long_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i < -0x8000) i = -0x8000; else if (i > 0x7FFF) i = 0x7FFF;

  s[0] = (i & 0xFF00) >> 8;
  s[1] = i & 0x00FF;
}

long char_to_SB24long(unsigned char *s) {
  if ((s[0] & 0x80) != 0)
    return -(long)(0x1000000 - ((s[0] << 16) | (s[1] << 8) | s[2]));/*negative*/
  else
    return (long)(s[0] << 16) | (s[1] << 8) | s[2];                 /*positive*/
}

PyObject *char_to_python_SB24long(unsigned char *s) {
#ifdef IS_PY3K
  return PyLong_FromLong(char_to_SB24long(s));
#else
  return PyInt_FromLong(char_to_SB24long(s));
#endif
}

PyObject *char_to_python_SB24float(unsigned char *s) {
  return PyFloat_FromDouble(((double)char_to_SB24long(s)) / (double)8388608);
}

void SB24long_to_char(long i, unsigned char *s) {
  /*avoid overflow/underflow*/
  if (i < -0x800000) i = -0x800000; else if (i > 0x7FFFFF) i = 0x7FFFFF;

  s[0] = (i & 0xFF0000) >> 16;
  s[1] = (i & 0x00FF00) >> 8;
  s[2] = i & 0x0000FF;
}

#ifdef IS_PY3K

void Resampler_dealloc(pcmstream_Resampler* self) {
  src_delete(self->src_state);
  Py_TYPE(self)->tp_free((PyObject*)self);
}

#else

void Resampler_dealloc(pcmstream_Resampler* self) {
  src_delete(self->src_state);
  self->ob_type->tp_free((PyObject*)self);
}

#endif

PyObject *Resampler_new(PyTypeObject *type,
			PyObject *args, PyObject *kwds) {
  pcmstream_Resampler *self;

  self = (pcmstream_Resampler *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

int Resampler_init(pcmstream_Resampler *self,
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

/**************************/
/*Resampler implementation*/
/**************************/

#define OUTPUT_SAMPLES_LENGTH 0x100000

PyObject *Resampler_process(pcmstream_Resampler* self,
				   PyObject *args) {
  PyObject *samples_object;
  PyObject *samples_list;
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


  /*ensure samples_object is a sequence and turn it into a fast sequence*/
#ifdef IS_PY3K
  if ((!PySequence_Check(samples_object)) || (PyBytes_Check(samples_object))) {
    PyErr_SetString(PyExc_TypeError,
		    "samples must be a sequence");
    return NULL;
  }
#else
  if ((!PySequence_Check(samples_object)) || (PyString_Check(samples_object))) {
    PyErr_SetString(PyExc_TypeError,
		    "samples must be a sequence");
    return NULL;
  }
#endif

  samples_list = PySequence_Fast(samples_object,
				 "samples must be a sequence");
  if (samples_list == NULL) {
    return NULL;
  }

  /*grab the size of samples_object*/
  samples_list_size = PySequence_Fast_GET_SIZE(samples_list);


  /*build SRC_DATA from our inputs*/
  src_data.data_in = (float *)malloc(samples_list_size * sizeof(float));

  if (src_data.data_in == NULL) {
    PyErr_SetString(PyExc_MemoryError,"out of memory");
    Py_XDECREF(samples_list);
    return NULL;
  }

  src_data.data_out = data_out;
  src_data.input_frames = samples_list_size / self->channels;
  src_data.output_frames = OUTPUT_SAMPLES_LENGTH / self->channels;
  src_data.end_of_input = last;
  src_data.src_ratio = self->ratio;

  for (i = 0; i < samples_list_size; i++) {
    sample = PySequence_Fast_GET_ITEM(samples_object,i);

    if (PyFloat_Check(sample)) {
      src_data.data_in[i] = (float)PyFloat_AsDouble(sample);
    } else {
      /*our sample isn't a float*/
      Py_XDECREF(samples_list);
      PyErr_SetString(PyExc_ValueError,
		      "samples must be floating point numbers");
      return NULL;
    }
  }


  /*now that we've transferred everything from samples_list to src_data,
    we no longer need samples_list*/
  Py_DECREF(samples_list);


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
    if (PyList_SetItem(processed_samples,i,
		       PyFloat_FromDouble((double)src_data.data_out[i])) == -1)
      goto error;
  }

  /*not-yet-successfully processed samples*/
  for (i = src_data.input_frames_used * self->channels,j=0;
       i < (src_data.input_frames * self->channels);
       i++,j++) {
    if (PyList_SetItem(unprocessed_samples,j,
		       PyFloat_FromDouble((double)src_data.data_in[i])) == -1)
      goto error;
  }


  /*cleanup anything allocated*/
  free(src_data.data_in);


  /*return those two arrays as a tuple*/
  toreturn = PyTuple_Pack(2,processed_samples,unprocessed_samples);

  Py_DECREF(processed_samples);
  Py_DECREF(unprocessed_samples);

  return toreturn;

 error:
  free(src_data.data_in);
  Py_DECREF(processed_samples);
  Py_DECREF(unprocessed_samples);

  return NULL;
}
