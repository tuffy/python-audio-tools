#include <Python.h>
#include <alsa/asoundlib.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2008  Brian Langenberger

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

/*alsa.Output definition*/
typedef struct {
  PyObject_HEAD
  snd_pcm_t *playback;
  snd_pcm_hw_params_t *params;
} alsa_Output;

PyMODINIT_FUNC initalsa(void);
PyObject *ALSAOutput_new(PyTypeObject *type,
			 PyObject *args, PyObject *kwds);
int ALSAOutput_init(alsa_Output *self,
		    PyObject *args, PyObject *kwds);
void ALSAOutput_dealloc(alsa_Output* self);
PyObject *ALSAOutput_close(alsa_Output* self);
PyObject *ALSAOutput_setparams(alsa_Output* self,
			       PyObject *args);
PyObject *ALSAOutput_write(alsa_Output* self,
			   PyObject *args);

PyMethodDef module_methods[] = {
  {NULL}
};

PyMethodDef ALSAOutput_methods[] = {
  {"close", (PyCFunction)ALSAOutput_close,
   METH_NOARGS,"Closes the ALSA output stream."},
  {"setparams", (PyCFunction)ALSAOutput_setparams,
   METH_VARARGS,"Sets the PCM stream parameters."},
  {"write", (PyCFunction)ALSAOutput_write,
   METH_VARARGS,"Writes PCM data to output stream."},
  {NULL}
};

PyTypeObject alsa_OutputType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "alsa.Output", /*tp_name*/
    sizeof(alsa_Output), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ALSAOutput_dealloc, /*tp_dealloc*/
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
    "Output objects",          /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    ALSAOutput_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                          /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ALSAOutput_init, /* tp_init */
    0,                         /* tp_alloc */
    ALSAOutput_new,            /* tp_new */
};


PyMODINIT_FUNC initalsa(void) {
    PyObject* m;

    alsa_OutputType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&alsa_OutputType) < 0)
      return;

    m = Py_InitModule3("alsa", module_methods,
                       "An output-only ALSA interface module.");

    Py_INCREF(&alsa_OutputType);
    PyModule_AddObject(m, "Output",
		       (PyObject *)&alsa_OutputType);
}

PyObject *ALSAOutput_new(PyTypeObject *type,
			 PyObject *args, PyObject *kwds) {
  alsa_Output *self;

  self = (alsa_Output *)type->tp_alloc(type, 0);
  self->playback = NULL;
  self->params = NULL;

  return (PyObject *)self;
}

int ALSAOutput_init(alsa_Output *self,
		    PyObject *args, PyObject *kwds) {

  int err;
  char *device;

  if (!PyArg_ParseTuple(args, "s", &device))
    return -1;

  err = snd_pcm_open(&(self->playback), device, SND_PCM_STREAM_PLAYBACK, 0);
  if (err < 0) {
    PyErr_SetString(PyExc_IOError, snd_strerror(err));
    return -1;
  }

  err = snd_pcm_hw_params_malloc(&(self->params));
  if (err < 0) {
    PyErr_SetString(PyExc_IOError, snd_strerror(err));
    return -1;
  }

  err = snd_pcm_hw_params_any(self->playback, self->params);
  if (err < 0) {
    PyErr_SetString(PyExc_IOError, snd_strerror(err));
    return -1;
  }

  err = snd_pcm_hw_params_set_access(self->playback, self->params,
				     SND_PCM_ACCESS_RW_INTERLEAVED);
  if (err < 0) {
    PyErr_SetString(PyExc_IOError, snd_strerror(err));
    return -1;
  }

  return 0;
}

PyObject *ALSAOutput_close(alsa_Output* self) {
  if (self->params != NULL) {
    snd_pcm_hw_params_free(self->params);
    self->params = NULL;
  }

  if (self->playback != NULL) {
    snd_pcm_close(self->playback);
    self->playback = NULL;
  }

  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *ALSAOutput_setparams(alsa_Output* self,
			       PyObject *args) {
  unsigned int sample_rate;
  unsigned int channels;
  int bits_per_sample;
  snd_pcm_format_t pcm_format = SND_PCM_FORMAT_S16_LE;
  int err;
  int dir = 0;

  if (!PyArg_ParseTuple(args, "IIi", &sample_rate, &channels, &bits_per_sample))
    return NULL;

  if ((self->playback == NULL) || (self->params == NULL)) {
    PyErr_SetString(PyExc_IOError,
		    "ALSA stream is closed");
    return NULL;
  }

  if ((bits_per_sample != 8) &&
      (bits_per_sample != 16) &&
      (bits_per_sample != 24)) {
    PyErr_SetString(PyExc_ValueError,
		    "bits per sample must be 8, 16 or 24");
    return NULL;
  }


  /*test/set rate*/
  err = snd_pcm_hw_params_test_rate(self->playback, self->params,
				    sample_rate, dir);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }

  err = snd_pcm_hw_params_set_rate_near(self->playback, self->params,
					&sample_rate, &dir);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }

  /*test/set channels*/
  err = snd_pcm_hw_params_test_channels(self->playback, self->params,
				       channels);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }

  err = snd_pcm_hw_params_set_channels(self->playback, self->params,
				       channels);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }


  /*test/set bits-per-sample*/
  switch (bits_per_sample) {
  case 8: pcm_format = SND_PCM_FORMAT_U8; break;
  case 16: pcm_format = SND_PCM_FORMAT_S16_LE; break;
  case 24: pcm_format = SND_PCM_FORMAT_S24_LE; break;
  }

  err = snd_pcm_hw_params_test_format(self->playback, self->params,
				      pcm_format);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }

  err = snd_pcm_hw_params_set_format(self->playback, self->params,
				     pcm_format);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }


  err = snd_pcm_hw_params(self->playback, self->params);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }

  err = snd_pcm_prepare(self->playback);
  if (err < 0) {
    PyErr_SetString(PyExc_ValueError, snd_strerror(err));
    return NULL;
  }



  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *ALSAOutput_write(alsa_Output* self,
			   PyObject *args) {
  char *pcm_data;
  Py_ssize_t pcm_data_length;

  if (!PyArg_ParseTuple(args,"s#",&pcm_data,&pcm_data_length))
    return NULL;

  if ((self->playback == NULL) || (self->params == NULL)) {
    PyErr_SetString(PyExc_IOError,
		    "ALSA stream is closed");
    return NULL;
  }

  Py_BEGIN_ALLOW_THREADS
  snd_pcm_writei(self->playback, pcm_data,
		 (snd_pcm_uframes_t)pcm_data_length);
  Py_END_ALLOW_THREADS

  Py_INCREF(Py_None);
  return Py_None;
}

void ALSAOutput_dealloc(alsa_Output* self)
{
  if (self->params != NULL) {
    snd_pcm_hw_params_free(self->params);
  }

  if (self->playback != NULL) {
    snd_pcm_close(self->playback);
  }

  self->ob_type->tp_free((PyObject*)self);
}
