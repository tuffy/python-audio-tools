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
#include "pcm.h"
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

    pcmstream_ResamplerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmstream_ResamplerType) < 0)
      return NULL;

    m = PyModule_Create(&pcmstreammodule);
    if (m == NULL)
      return NULL;

    Py_INCREF(&pcmstream_ResamplerType);
    PyModule_AddObject(m, "Resampler",
		       (PyObject *)&pcmstream_ResamplerType);
    return m;
}

#else

PyMODINIT_FUNC initpcmstream(void) {
    PyObject* m;

    pcmstream_ResamplerType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcmstream_ResamplerType) < 0)
      return;

    m = Py_InitModule3("pcmstream", module_methods,
                       "A PCM stream reading, writing and editing module.");

    Py_INCREF(&pcmstream_ResamplerType);
    PyModule_AddObject(m, "Resampler",
		       (PyObject *)&pcmstream_ResamplerType);
}

#endif

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
  PyObject *framelist_obj;
  int last;

  SRC_DATA src_data;
  int processing_error;

  static float data_out[OUTPUT_SAMPLES_LENGTH];

  Py_ssize_t i,j;

  PyObject *pcm = NULL;
  PyObject *framelist_type_obj = NULL;
  pcm_FloatFrameList *framelist;
  pcm_FloatFrameList *processed_samples = NULL;
  pcm_FloatFrameList *unprocessed_samples = NULL;
  PyObject *toreturn;

  src_data.data_in = NULL;

  if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
    goto error;

  /*grab (framelist,last) passed in from the method call*/
  if (!PyArg_ParseTuple(args,"Oi",&framelist_obj,&last))
    goto error;

  /*ensure input is a FloatFrameList*/
  if ((framelist_type_obj = PyObject_GetAttrString(pcm,"FloatFrameList")) == NULL)
    goto error;
  if (framelist_obj->ob_type == (PyTypeObject*)framelist_type_obj) {
    framelist = (pcm_FloatFrameList*)framelist_obj;
  } else {
    PyErr_SetString(PyExc_TypeError,"first argument must be a FloatFrameList");
    goto error;
  }

  if (framelist->channels != self->channels) {
    PyErr_SetString(PyExc_ValueError,"FrameList's channel count differs from Resampler's");
    goto error;
  }

  /*build SRC_DATA from our inputs*/
  if ((src_data.data_in = malloc(framelist->samples_length * sizeof(float))) == NULL) {
    PyErr_SetString(PyExc_MemoryError,"out of memory");
    goto error;
  }

  src_data.data_out = data_out;
  src_data.input_frames = framelist->frames;
  src_data.output_frames = OUTPUT_SAMPLES_LENGTH / self->channels;
  src_data.end_of_input = last;
  src_data.src_ratio = self->ratio;

  for (i = 0; i < framelist->samples_length; i++) {
    src_data.data_in[i] = framelist->samples[i];
  }

  /*run src_process() on our self->SRC_STATE and SRC_DATA*/
  if ((processing_error = src_process(self->src_state,&src_data)) != 0) {
    /*some sort of processing error raises ValueError*/
    PyErr_SetString(PyExc_ValueError,
		    src_strerror(processing_error));
    goto error;
  }


  /*turn our processed and unprocessed data into two new FloatFrameLists*/
  if ((processed_samples = (pcm_FloatFrameList*)PyObject_CallMethod(pcm,"__blank_float__",NULL)) == NULL)
    goto error;
  processed_samples->channels = self->channels;
  processed_samples->frames = src_data.output_frames_gen;
  processed_samples->samples_length = processed_samples->frames * processed_samples->channels;
  processed_samples->samples = realloc(processed_samples->samples,
				       sizeof(fa_data_t) * processed_samples->samples_length);

  if ((unprocessed_samples = (pcm_FloatFrameList*)PyObject_CallMethod(pcm,"__blank_float__",NULL)) == NULL)
    goto error;
  unprocessed_samples->channels = self->channels;
  unprocessed_samples->frames = src_data.input_frames - src_data.input_frames_used;
  unprocessed_samples->samples_length = unprocessed_samples->frames * unprocessed_samples->channels;
  unprocessed_samples->samples = realloc(unprocessed_samples->samples,
					 sizeof(fa_data_t) * unprocessed_samples->samples_length);


  /*successfully processed samples*/
  for (i = 0; i < src_data.output_frames_gen * self->channels; i++) {
    processed_samples->samples[i] = src_data.data_out[i];
  }

  /*not-yet-successfully processed samples*/
  for (i = src_data.input_frames_used * self->channels,j=0;
       i < (src_data.input_frames * self->channels);
       i++,j++) {
    unprocessed_samples->samples[j] = src_data.data_in[i];
  }


  /*return those two arrays as a tuple*/
  toreturn = PyTuple_Pack(2,processed_samples,unprocessed_samples);

  /*cleanup anything allocated*/
  free(src_data.data_in);
  Py_DECREF(pcm);
  Py_DECREF(framelist_type_obj);
  Py_DECREF(processed_samples);
  Py_DECREF(unprocessed_samples);

  return toreturn;

 error:
  if (src_data.data_in != NULL)
    free(src_data.data_in);
  Py_XDECREF(pcm);
  Py_XDECREF(framelist_type_obj);
  Py_XDECREF(processed_samples);
  Py_XDECREF(unprocessed_samples);

  return NULL;
}
