#include <Python.h>
#include <pulse/simple.h>
#include <pulse/error.h>

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

/*pulse.Output definition*/
typedef struct {
  PyObject_HEAD
  pa_simple *stream;
  pa_sample_spec pcm_format;
} pulse_Output;

PyMODINIT_FUNC initpulse(void);
PyObject *PulseOutput_new(PyTypeObject *type,
			  PyObject *args, PyObject *kwds);
int PulseOutput_init(pulse_Output *self,
		     PyObject *args, PyObject *kwds);
void PulseOutput_dealloc(pulse_Output* self);
PyObject *PulseOutput_close(pulse_Output* self);
PyObject *PulseOutput_setparams(pulse_Output* self,
				PyObject *args);
PyObject *PulseOutput_write(pulse_Output* self,
			    PyObject *args);

PyMethodDef module_methods[] = {
  {NULL}
};

PyMethodDef PulseOutput_methods[] = {
  {"close", (PyCFunction)PulseOutput_close,
   METH_NOARGS,"Closes the Pulse output stream."},
  {"write", (PyCFunction)PulseOutput_write,
   METH_VARARGS,"Writes PCM data to output stream."},
  {NULL}
};

PyTypeObject pulse_OutputType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pulse.Output", /*tp_name*/
    sizeof(pulse_Output), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)PulseOutput_dealloc, /*tp_dealloc*/
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
    PulseOutput_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                          /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)PulseOutput_init, /* tp_init */
    0,                         /* tp_alloc */
    PulseOutput_new,            /* tp_new */
};


PyMODINIT_FUNC initpulse(void) {
    PyObject* m;

    pulse_OutputType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pulse_OutputType) < 0)
      return;

    m = Py_InitModule3("pulse", module_methods,
                       "An output-only PulseAudio interface module.");

    Py_INCREF(&pulse_OutputType);
    PyModule_AddObject(m, "Output",
		       (PyObject *)&pulse_OutputType);
}

PyObject *PulseOutput_new(PyTypeObject *type,
			 PyObject *args, PyObject *kwds) {
  pulse_Output *self;

  self = (pulse_Output *)type->tp_alloc(type, 0);
  self->stream = NULL;

  return (PyObject *)self;
}

int PulseOutput_init(pulse_Output *self,
		    PyObject *args, PyObject *kwds) {

  unsigned int sample_rate;
  unsigned int channels;
  unsigned int bits_per_sample;
  int error;

  if (!PyArg_ParseTuple(args,"III",&sample_rate, &channels, &bits_per_sample))
    return -1;

  switch (bits_per_sample) {
  case 8: self->pcm_format.format = PA_SAMPLE_U8; break;
  case 16: self->pcm_format.format = PA_SAMPLE_S16LE; break;
  case 32: self->pcm_format.format = PA_SAMPLE_FLOAT32LE; break;
  default:
    PyErr_SetString(PyExc_IOError,
		    "8 and 16 bit ints or 32 bits floats are supported");
    return -1;
  }

  self->pcm_format.rate = (uint32_t)sample_rate;
  self->pcm_format.channels = (uint8_t)channels;

  self->stream = pa_simple_new(NULL,
			       "Python Audio Tools",
			       PA_STREAM_PLAYBACK,
			       NULL,
			       "pcm",
			       &(self->pcm_format),
			       NULL,
			       NULL,
			       &error);

  if (!self->stream) {
    PyErr_SetString(PyExc_IOError,
		    pa_strerror(error));
    return -1;
  }

  return 0;
}

PyObject *PulseOutput_close(pulse_Output* self) {
  if (self->stream != NULL) {
    pa_simple_free(self->stream);
    self->stream = NULL;
  }

  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *PulseOutput_write(pulse_Output* self,
			    PyObject *args) {
  char *pcm_data;
  Py_ssize_t pcm_data_length;
  int error;
  int write_result;

  if (!PyArg_ParseTuple(args,"s#",&pcm_data,&pcm_data_length))
    return NULL;

  if (self->stream == NULL) {
    PyErr_SetString(PyExc_IOError,"output stream is closed");
    return NULL;
  }

  /******THIS SEGFAULTS - DO NOT USE*******/
  /*Either I've made a stupid coding error, or there's some conflict
    between PulseAudio and Python's threading mechanism.
    Removing the BEGIN/END_ALLOW_THREADS macros makes this routine
    "work" (in the sense that it stops segfaulting) but having
    pulse.Output.write() block all threads and makes ReplayGain
    calculation cause stuttering
    (since it can't work in the background anymore).
    There might be a fix for this in the more advance PulseAudio API,
    but I'd rather punt to external programs in the short term.
  */

  Py_BEGIN_ALLOW_THREADS
  write_result = pa_simple_write(self->stream, pcm_data,
				 (size_t)pcm_data_length, &error);
  Py_END_ALLOW_THREADS

  if (write_result < 0) {
    PyErr_SetString(PyExc_IOError,
		    pa_strerror(error));
    return NULL;
  }

  Py_INCREF(Py_None);
  return Py_None;
}

void PulseOutput_dealloc(pulse_Output* self)
{
  if (self->stream != NULL) {
    pa_simple_free(self->stream);
  }

  PyObject_Del(self);
}
