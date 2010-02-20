#include <Python.h>

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

#include "pcm.h"

PyMODINIT_FUNC initpcm(void) {
    PyObject* m;

    pcm_FrameListType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcm_FrameListType) < 0)
      return;

    m = Py_InitModule3("pcm", module_methods,
                       "A PCM FrameList handling module.");

    Py_INCREF(&pcm_FrameListType);
    PyModule_AddObject(m, "FrameList",
		       (PyObject *)&pcm_FrameListType);
}

void FrameList_dealloc(pcm_FrameList* self) {
  free(self->samples);
  self->ob_type->tp_free((PyObject*)self);
}

PyObject *FrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  pcm_FrameList *self;

  self = (pcm_FrameList *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

int FrameList_init(pcm_FrameList *self, PyObject *args, PyObject *kwds) {
  unsigned char *data;
#ifdef PY_SSIZE_T_CLEAN
  Py_ssize_t data_size;
#else
  int data_size;
#endif
  int is_big_endian;

  if (!PyArg_ParseTuple(args, "s#iiii",
			&data,&data_size,
			&(self->channels),
			&(self->bits_per_sample),
			&(is_big_endian),
			&(self->is_signed)))
    return -1;

  if (data_size % (self->channels * self->bits_per_sample / 8)) {
    PyErr_SetString(PyExc_ValueError,
		    "number of samples must be divisible by bits-per-sample and number of channels");
    return -1;
  } else {
    self->samples_length = data_size / (self->bits_per_sample / 8);
    self->frames = self->samples_length / self->channels;
    self->samples = malloc(sizeof(int32_t) * self->samples_length);
    FrameList_char_to_samples(self->samples,
			      data,
			      FrameList_get_char_to_int_converter(
						    self->bits_per_sample,
						    is_big_endian,
						    self->is_signed),
			      self->samples_length,
			      self->bits_per_sample);
  }

  return 0;
}

PyObject* FrameList_frames(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",self->frames);
}

PyObject* FrameList_channels(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",self->channels);
}

PyObject* FrameList_bits_per_sample(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",self->bits_per_sample);
}

PyObject* FrameList_signed(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",self->is_signed);
}

Py_ssize_t FrameList_len(pcm_FrameList *o) {
  return o->samples_length;
}

PyObject* FrameList_GetItem(pcm_FrameList *o, Py_ssize_t i) {
  if ((i >= o->samples_length) || (i < 0)) {
    PyErr_SetString(PyExc_IndexError,"index out of range");
    return NULL;
  } else {
    return Py_BuildValue("i",o->samples[i]);
  }
}

PyObject* FrameList_frame(pcm_FrameList *self, PyObject *args) {
  int frame_number;
  pcm_FrameList *frame;

  if (!PyArg_ParseTuple(args,"i",&frame_number))
    return NULL;
  if ((frame_number < 0) || (frame_number >= self->frames)) {
    PyErr_SetString(PyExc_IndexError,"frame number out of range");
    return NULL;
  }

  frame = (pcm_FrameList*)_PyObject_New(&pcm_FrameListType);
  frame->frames = 1;
  frame->channels = self->channels;
  frame->bits_per_sample = self->bits_per_sample;
  frame->is_signed = self->is_signed;
  frame->samples = malloc(sizeof(int32_t) * self->channels);
  frame->samples_length = self->channels;
  memcpy(frame->samples,
	 self->samples + (frame_number * self->channels),
	 sizeof(int32_t) * self->channels);
  return (PyObject*)frame;
}

PyObject* FrameList_channel(pcm_FrameList *self, PyObject *args) {
  int channel_number;
  pcm_FrameList *channel;
  uint32_t i,j;
  uint32_t samples_length;
  int total_channels;

  if (!PyArg_ParseTuple(args,"i",&channel_number))
    return NULL;
  if ((channel_number < 0) || (channel_number >= self->channels)) {
    PyErr_SetString(PyExc_IndexError,"channel number out of range");
    return NULL;
  }

  channel = (pcm_FrameList*)_PyObject_New(&pcm_FrameListType);
  channel->frames = self->frames;
  channel->channels = 1;
  channel->bits_per_sample = self->bits_per_sample;
  channel->is_signed = self->is_signed;
  channel->samples = malloc(sizeof(int32_t) * self->frames);
  channel->samples_length = self->frames;

  samples_length = self->samples_length;
  total_channels = self->channels;
  for (j=0,i = channel_number; i < samples_length; j++,i += total_channels) {
    channel->samples[j] = self->samples[i];
  }

  return (PyObject*)channel;
}

PyObject* FrameList_to_bytes(pcm_FrameList *self, PyObject *args) {
  int is_big_endian;
  unsigned char *bytes;
  Py_ssize_t bytes_size;
  PyObject *bytes_obj;

  if (!PyArg_ParseTuple(args,"i",&is_big_endian))
    return NULL;

  bytes_size = (self->bits_per_sample / 8) * self->frames * self->channels;
  bytes = malloc(bytes_size);

  FrameList_samples_to_char(bytes, self->samples,
			    FrameList_get_int_to_char_converter(
					  self->bits_per_sample,
					  is_big_endian,
					  self->is_signed),
			    self->samples_length,
			    self->bits_per_sample);

  bytes_obj = PyString_FromStringAndSize((char*)bytes,bytes_size);
  free(bytes);
  return bytes_obj;
}

void FrameList_char_to_samples(int32_t *samples,
			       unsigned char *data,
			       FrameList_char_to_int_converter converter,
			       uint32_t samples_length,
			       int bits_per_sample) {
  int bytes_per_sample = bits_per_sample / 8;
  int i;

  for (i = 0; i < samples_length; i++, data += bytes_per_sample) {
    samples[i] = converter(data);
  }
}

PyObject *FrameList_from_list(PyObject *dummy, PyObject *args) {
  pcm_FrameList *framelist;
  PyObject *list;
  PyObject *integer;
  Py_ssize_t list_len,i;
  long integer_val;

  framelist = (pcm_FrameList*)_PyObject_New(&pcm_FrameListType);

  if (!PyArg_ParseTuple(args,"Oiii",&list,
			&(framelist->channels),
			&(framelist->bits_per_sample),
			&(framelist->is_signed)))
    goto error;

  if ((list_len = PySequence_Size(list)) == -1)
    goto error;

  if (list_len % framelist->channels) {
    PyErr_SetString(PyExc_ValueError,
		    "number of samples must be divisible by number of channels");
    goto error;
  }

  framelist->samples = malloc(sizeof(int32_t) * list_len);
  framelist->samples_length = list_len;
  framelist->frames = list_len / framelist->channels;
  for (i = 0; i < list_len; i++) {
    if ((integer = PySequence_GetItem(list,i)) == NULL)
      goto error;
    if (((integer_val = PyInt_AsLong(integer)) == -1) &&
	PyErr_Occurred())
      goto error;
    else {
      framelist->samples[i] = integer_val;
    }
  }

  return (PyObject*)framelist;
 error:
  Py_DECREF(framelist);
  return NULL;
}

FrameList_char_to_int_converter FrameList_get_char_to_int_converter(
                                              int bits_per_sample,
			         	      int is_big_endian,
				              int is_signed) {
  switch (bits_per_sample) {
  case 8:
    switch (is_big_endian) {
    case 0:
      switch (is_signed) {
      case 0:  /*8 bits-per-sample, little-endian, unsigned*/
	return FrameList_U8_char_to_int;
      default: /*8 bits-per-sample, little-endian, signed*/
	return FrameList_S8_char_to_int;
      }
    default:
      switch (is_signed) {
      case 0:  /*8 bits-per-sample, big-endian, unsigned*/
	return FrameList_U8_char_to_int;
      default: /*8 bits-per-sample, big-endian, signed*/
	return FrameList_S8_char_to_int;
      }
    }
  case 16:
    switch (is_big_endian) {
    case 0:
      switch (is_signed) {
      case 0:  /*16 bits-per-sample, little-endian, unsigned*/
	return FrameList_UL16_char_to_int;
      default: /*16 bits-per-sample, little-endian, signed*/
	return FrameList_SL16_char_to_int;
      }
    default:
      switch (is_signed) {
      case 0:  /*16 bits-per-sample, big-endian, unsigned*/
	return FrameList_UB16_char_to_int;
      default: /*16 bits-per-sample, big-endian, signed*/
	return FrameList_SB16_char_to_int;
      }
    }
  case 24:
    switch (is_big_endian) {
    case 0:
      switch (is_signed) {
      case 0:  /*24 bits-per-sample, little-endian, unsigned*/
	return FrameList_UL24_char_to_int;
      default: /*24 bits-per-sample, little-endian, signed*/
	return FrameList_SL24_char_to_int;
      }
    default:
      switch (is_signed) {
      case 0:  /*24 bits-per-sample, big-endian, unsigned*/
	return FrameList_UB24_char_to_int;
      default: /*24 bits-per-sample, big-endian, signed*/
	return FrameList_SB24_char_to_int;
      }
    }
  default:
    return NULL;
  }
}

int32_t FrameList_U8_char_to_int(unsigned char *s) {
  return (int32_t)s[0];
}

int32_t FrameList_S8_char_to_int(unsigned char *s) {
  if (s[0] & 0x80) {
    /*negative*/
    return -(int32_t)(0x100 - s[0]);
  } else {
    /*positive*/
    return (int32_t)s[0];
  }
}

int32_t FrameList_UB16_char_to_int(unsigned char *s) {
  return (int32_t)(s[0] << 8) | s[1];
}

int32_t FrameList_UL16_char_to_int(unsigned char *s) {
  return (int32_t)(s[1] << 8) | s[0];
}

int32_t FrameList_SL16_char_to_int(unsigned char *s) {
  if (s[1] & 0x80) {
    /*negative*/
    return -(int32_t)(0x10000 - ((s[1] << 8) | s[0]));
  } else {
    /*positive*/
    return (int32_t)(s[1] << 8) | s[0];
  }
}

int32_t FrameList_SB16_char_to_int(unsigned char *s) {
  if (s[0] & 0x80) {
    /*negative*/
    return -(int32_t)(0x10000 - ((s[0] << 8) | s[1]));
  } else {
    /*positive*/
    return (int32_t)(s[0] << 8) | s[1];
  }
}

int32_t FrameList_UL24_char_to_int(unsigned char *s) {
  return (int32_t)((s[2] << 16) | (s[1] << 8) | s[0]);
}

int32_t FrameList_UB24_char_to_int(unsigned char *s) {
  return (int32_t)((s[0] << 16) | (s[1] << 8) | s[2]);
}

int32_t FrameList_SL24_char_to_int(unsigned char *s) {
  if (s[2] & 0x80) {
    /*negative*/
    return -(int32_t)(0x1000000 - ((s[2] << 16) | (s[1] << 8) | s[0]));
  } else {
    /*positive*/
    return (int32_t)((s[2] << 16) | (s[1] << 8) | s[0]);
  }
}

int32_t FrameList_SB24_char_to_int(unsigned char *s) {
  if (s[0] & 0x80) {
    /*negative*/
    return -(int32_t)(0x1000000 - ((s[0] << 16) | (s[1] << 8) | s[2]));
  } else {
    /*positive*/
    return (int32_t)((s[0] << 16) | (s[1] << 8) | s[2]);
  }
}

void FrameList_samples_to_char(unsigned char *data,
			       int32_t *samples,
			       FrameList_int_to_char_converter converter,
			       uint32_t samples_length,
			       int bits_per_sample) {
  int bytes_per_sample = bits_per_sample / 8;
  int i;

  for (i = 0; i < samples_length; i++, data += bytes_per_sample) {
    converter(samples[i],data);
  }
}

FrameList_int_to_char_converter FrameList_get_int_to_char_converter(
                                              int bits_per_sample,
			         	      int is_big_endian,
				              int is_signed) {
  switch (bits_per_sample) {
  case 8:
    switch (is_big_endian) {
    case 0:
      switch (is_signed) {
      case 0:  /*8 bits-per-sample, little-endian, unsigned*/
	return FrameList_int_to_U8_char;
      default: /*8 bits-per-sample, little-endian, signed*/
	return FrameList_int_to_S8_char;
      }
    default:
      switch (is_signed) {
      case 0:  /*8 bits-per-sample, big-endian, unsigned*/
	return FrameList_int_to_U8_char;
      default: /*8 bits-per-sample, big-endian, signed*/
	return FrameList_int_to_S8_char;
      }
    }
  case 16:
    switch (is_big_endian) {
    case 0:
      switch (is_signed) {
      case 0:  /*16 bits-per-sample, little-endian, unsigned*/
	return FrameList_int_to_UL16_char;
      default: /*16 bits-per-sample, little-endian, signed*/
	return FrameList_int_to_SL16_char;
      }
    default:
      switch (is_signed) {
      case 0:  /*16 bits-per-sample, big-endian, unsigned*/
	return FrameList_int_to_UB16_char;
      default: /*16 bits-per-sample, big-endian, signed*/
	return FrameList_int_to_SB16_char;
      }
    }
  case 24:
    switch (is_big_endian) {
    case 0:
      switch (is_signed) {
      case 0:  /*24 bits-per-sample, little-endian, unsigned*/
  	return FrameList_int_to_UL24_char;
      default: /*24 bits-per-sample, little-endian, signed*/
  	return FrameList_int_to_SL24_char;
      }
    default:
      switch (is_signed) {
      case 0:  /*24 bits-per-sample, big-endian, unsigned*/
  	return FrameList_int_to_UB24_char;
      default: /*24 bits-per-sample, big-endian, signed*/
  	return FrameList_int_to_SB24_char;
      }
    }
  default:
    return NULL;
  }
}

void FrameList_int_to_S8_char(int32_t i, unsigned char *s) {
  if (i > 0x7F)
    i = 0x7F;  /*avoid overflow*/
  else if (i < -0x80)
    i = -0x80; /*avoid underflow*/

  if (i >= 0) {
    /*positive*/
    s[0] = i;
  } else {
    /*negative*/
    s[0] = (1 << 8) - (-i);
  }
}

void FrameList_int_to_U8_char(int32_t i, unsigned char *s) {
  s[0] = i & 0xFF;
}

void FrameList_int_to_UB16_char(int32_t i, unsigned char *s) {
  s[0] = (i >> 8) & 0xFF;
  s[1] = i & 0xFF;
}

void FrameList_int_to_SB16_char(int32_t i, unsigned char *s) {
  if (i > 0x7FFF)
    i = 0x7FFF;
  else if (i < -0x8000)
    i = -0x8000;

  if (i < 0) {
    i = (1 << 16) - (-i);
  }

  s[0] = i >> 8;
  s[1] = i & 0xFF;
}

void FrameList_int_to_UL16_char(int32_t i, unsigned char *s) {
  s[1] = (i >> 8) & 0xFF;
  s[0] = i & 0xFF;
}

void FrameList_int_to_SL16_char(int32_t i, unsigned char *s) {
  if (i > 0x7FFF)
    i = 0x7FFF;
  else if (i < -0x8000)
    i = -0x8000;

  if (i < 0) {
    i = (1 << 16) - (-i);
  }

  s[1] = i >> 8;
  s[0] = i & 0xFF;
}

void FrameList_int_to_UB24_char(int32_t i, unsigned char *s) {
  s[0] = (i >> 16) & 0xFF;
  s[1] = (i >> 8) & 0xFF;
  s[2] = i & 0xFF;
}

void FrameList_int_to_SB24_char(int32_t i, unsigned char *s) {
  if (i > 0x7FFFFF)
    i = 0x7FFFFF;
  else if (i < -0x800000)
    i = -0x800000;

  if (i < 0) {
    i = (1 << 24) - (-i);
  }

  s[0] = i >> 16;
  s[1] = (i >> 8) & 0xFF;
  s[2] = i & 0xFF;
}

void FrameList_int_to_UL24_char(int32_t i, unsigned char *s) {
  s[2] = (i >> 16) & 0xFF;
  s[1] = (i >> 8) & 0xFF;
  s[0] = i & 0xFF;
}

void FrameList_int_to_SL24_char(int32_t i, unsigned char *s) {
  if (i > 0x7FFFFF)
    i = 0x7FFFFF;
  else if (i < -0x800000)
    i = -0x800000;

  if (i < 0) {
    i = (1 << 24) - (-i);
  }

  s[2] = i >> 16;
  s[1] = (i >> 8) & 0xFF;
  s[0] = i & 0xFF;
}
