#include "shn.h"
#include "../pcm.h"

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

int SHNDecoder_init(decoders_SHNDecoder *self,
		    PyObject *args, PyObject *kwds) {
  char* filename;
  FILE* fp;
  int i,j;

  if (!PyArg_ParseTuple(args, "s", &filename))
    return -1;

  /*open the shn file*/
  if ((fp = fopen(filename,"rb")) == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return -1;
  } else {
    self->bitstream = bs_open(fp);
  }

  if (!SHNDecoder_read_header(self)) {
    PyErr_SetString(PyExc_ValueError,"not a SHN file");
    return -1;
  } else {
    iaa_init(&(self->buffer),self->channels,self->block_size + self->wrap);
    for (i = 0; i < self->channels; i++) {
      for (j = 0; j < self->wrap; j++) {
    	ia_append(iaa_getitem(&(self->buffer),i),0);
      }
    }
  }

  self->filename = strdup(filename);

  self->bits_per_sample = 16; /*FIXME - this must come from file type*/
  self->sample_rate = 44100;  /*FIXME - this must come externally*/

  return 0;
}

PyObject *SHNDecoder_close(decoders_SHNDecoder* self,
			   PyObject *args) {
  Py_INCREF(Py_None);
  return Py_None;
}

void SHNDecoder_dealloc(decoders_SHNDecoder *self) {
  if (self->filename != NULL)
    free(self->filename);

  bs_close(self->bitstream);
  iaa_free(&(self->buffer));

  self->ob_type->tp_free((PyObject*)self);
}


PyObject *SHNDecoder_new(PyTypeObject *type,
			 PyObject *args, PyObject *kwds) {
  decoders_SHNDecoder *self;

  self = (decoders_SHNDecoder *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

static PyObject *SHNDecoder_version(decoders_SHNDecoder *self,
				    void *closure) {
  return Py_BuildValue("i",self->version);
}

static PyObject *SHNDecoder_file_type(decoders_SHNDecoder *self,
				      void *closure) {
  return Py_BuildValue("i",self->file_type);
}

static PyObject *SHNDecoder_channels(decoders_SHNDecoder *self,
				     void *closure) {
  return Py_BuildValue("i",self->channels);
}

static PyObject *SHNDecoder_bits_per_sample(decoders_SHNDecoder *self,
					    void *closure) {
  return Py_BuildValue("i",self->bits_per_sample);
}

static PyObject *SHNDecoder_sample_rate(decoders_SHNDecoder *self,
					void *closure) {
  return Py_BuildValue("i",self->sample_rate);
}

static PyObject *SHNDecoder_channel_mask(decoders_SHNDecoder *self,
					 void *closure) {
  /*FIXME - this should be able to take external channel mask values*/
  switch (self->channels) {
  case 1:
    return Py_BuildValue("i",0x4);
  case 2:
    return Py_BuildValue("i",0x3);
  default:
    return Py_BuildValue("i",0);
  }
}

static PyObject *SHNDecoder_block_size(decoders_SHNDecoder *self,
				       void *closure) {
  return Py_BuildValue("i",self->block_size);
}


PyObject *SHNDecoder_read(decoders_SHNDecoder* self,
			  PyObject *args) {
  int channel = 0;
  int i,j;
  unsigned int cmd;
  unsigned int verbatim_length;

  PyObject *pcm = NULL;
  pcm_FrameList *framelist;
  struct i_array* channel_data;

  if (!self->read_started) {
    fseek(self->bitstream->file,0,SEEK_SET);
    self->bitstream->state = 0;

    SHNDecoder_read_header(self);
  }

  if (self->read_finished) {
    goto finished;
  }

  /*read the next instructions to fill all buffers,
    until FN_QUIT reached*/
  while (channel < self->channels) {
    cmd = shn_read_uvar(self->bitstream,2);
    switch (cmd) {
    case FN_VERBATIM:
      /*skip VERBATIM chunks*/
      verbatim_length = shn_read_uvar(self->bitstream, VERBATIM_CHUNK_SIZE);
      for (i = 0; i < verbatim_length; i++) {
	shn_read_uvar(self->bitstream, VERBATIM_BYTE_SIZE);
      }
      break;
    case FN_DIFF0:
      SHNDecoder_read_diff(iaa_getitem(&(self->buffer),channel),
			   self->bitstream,
			   self->block_size,
			   SHNDecoder_diff0);
      channel++;
      break;
    case FN_DIFF1:
      SHNDecoder_read_diff(iaa_getitem(&(self->buffer),channel),
			   self->bitstream,
			   self->block_size,
			   SHNDecoder_diff1);
      channel++;
      break;
    case FN_DIFF2:
      SHNDecoder_read_diff(iaa_getitem(&(self->buffer),channel),
			   self->bitstream,
			   self->block_size,
			   SHNDecoder_diff2);
      channel++;
      break;
    case FN_DIFF3:
      SHNDecoder_read_diff(iaa_getitem(&(self->buffer),channel),
			   self->bitstream,
			   self->block_size,
			   SHNDecoder_diff3);
      channel++;
      break;
    case FN_ZERO:
      SHNDecoder_read_zero(iaa_getitem(&(self->buffer),channel),
			   self->block_size);
      channel++;
      break;
    case FN_QLPC:
      SHNDecoder_read_lpc(iaa_getitem(&(self->buffer),channel),
			  self->bitstream,
			  self->block_size);
      channel++;
      break;
    case FN_BLOCKSIZE:
      self->block_size = shn_read_long(self->bitstream);
      break;
    case FN_QUIT:
      self->read_finished = 1;
      goto finished;
    default:
      PyErr_SetString(PyExc_ValueError,"unknown command encountered in Shorten stream");
      goto error;
    }
  }

  /*once self->buffer is full of PCM data on each channel,
    convert the integer values to a pcm.FrameList object*/
  if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
    goto error;
  framelist = (pcm_FrameList*)PyObject_CallMethod(pcm,"__blank__",NULL);
  Py_DECREF(pcm);
  framelist->frames = self->block_size;
  framelist->channels = self->channels;
  framelist->bits_per_sample = self->bits_per_sample;
  framelist->samples_length = framelist->frames * framelist->channels;
  framelist->samples = realloc(framelist->samples,
			       sizeof(ia_data_t) * framelist->samples_length);

  for (channel = 0; channel < self->channels; channel++) {
    channel_data = iaa_getitem(&(self->buffer),channel);
    for (i = channel,j = 0; j < self->block_size;
  	 i += self->channels,j++)
      framelist->samples[i] = ia_getitem(channel_data,j + self->wrap);
  }

  /*wrap the last (usually 3) values back to the beginning
    of the buffers and reset their lengths for the next run*/
  for (channel = 0; channel < self->channels; channel++) {
    channel_data = iaa_getitem(&(self->buffer),channel);
    for (i = -self->wrap; i < 0; i++) {
      ia_setitem(channel_data,self->wrap + i,ia_getitem(channel_data,i));
    }
    channel_data->size = self->wrap;
  }

  /*then return the pcm.FrameList*/
  return (PyObject*)framelist;

 finished:
  if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
    goto error;
  framelist = (pcm_FrameList*)PyObject_CallMethod(pcm,"__blank__",NULL);
  Py_DECREF(pcm);
  framelist->frames = 0;
  framelist->channels = self->channels;
  framelist->bits_per_sample = self->bits_per_sample;
  framelist->samples_length = framelist->frames * framelist->channels;
  return (PyObject*)framelist;
 error:
  return NULL;
}

PyObject *SHNDecoder_verbatim(decoders_SHNDecoder* self,
			      PyObject *args) {
  unsigned int cmd;

  unsigned int verbatim_length;
  unsigned char* verbatim;
  unsigned int lpc_count;

  int i;
  unsigned int residual_size;
  PyObject* list;

  int previous_is_none = 0;

  if ((list = PyList_New(0)) == NULL)
    return NULL;

  /*rewind the stream and re-read the header*/
  fseek(self->bitstream->file,0,SEEK_SET);
  self->bitstream->state = 0;

  SHNDecoder_read_header(self);

  /*walk through the Shorten file,
    storing FN_VERBATIM instructions as strings
    and blocks of non-FM_VERBATIM instructions as None*/

  for (cmd = shn_read_uvar(self->bitstream,2);
       cmd != FN_QUIT;
       cmd = shn_read_uvar(self->bitstream,2)) {
    switch (cmd) {
    case FN_VERBATIM:
      verbatim_length = shn_read_uvar(self->bitstream, VERBATIM_CHUNK_SIZE);
      verbatim = malloc(verbatim_length);
      for (i = 0; i < verbatim_length; i++) {
	verbatim[i] = (shn_read_uvar(self->bitstream, VERBATIM_BYTE_SIZE) & 0xFF);
      }
      if (PyList_Append(list,
			PyString_FromStringAndSize((char *)verbatim,
						   verbatim_length)) == -1) {
	return NULL;
      } else {
	free(verbatim);
	previous_is_none = 0;
      }
      break;
    case FN_DIFF0:
    case FN_DIFF1:
    case FN_DIFF2:
    case FN_DIFF3:
      residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
      for (i = 0; i < self->block_size; i++) {
	shn_skip_var(self->bitstream, residual_size);
      }
      if (!previous_is_none) {
	Py_INCREF(Py_None);
	if (PyList_Append(list,Py_None) == -1) {
	  return NULL;
	}
      }
      previous_is_none = 1;
      break;
    case FN_ZERO:
      if (!previous_is_none) {
	Py_INCREF(Py_None);
	if (PyList_Append(list,Py_None) == -1) {
	  return NULL;
	}
      }
      previous_is_none = 1;
      break;
    case FN_QLPC:
      residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
      lpc_count = shn_read_uvar(self->bitstream, QLPC_SIZE);
      for (i = 0; i < lpc_count; i++) {
	shn_skip_var(self->bitstream, QLPC_QUANT);
      }
      for (i = 0; i < self->block_size; i++) {
	shn_skip_var(self->bitstream, residual_size);
      }
      if (!previous_is_none) {
	Py_INCREF(Py_None);
	if (PyList_Append(list,Py_None) == -1) {
	  return NULL;
	}
      }
      previous_is_none = 1;
      break;
    case FN_BLOCKSIZE:
      self->block_size = shn_read_long(self->bitstream);
      break;
    default:
      PyErr_SetString(PyExc_ValueError,"unknown command encountered in Shorten stream");
      Py_XDECREF(list);
      return NULL;
    }
  }

  self->read_started = 0;

  return list;
}

static PyObject *SHNDecoder_total_frames(decoders_SHNDecoder* self,
					 PyObject *args) {
  int total_samples = 0;
  unsigned int i;
  unsigned int cmd;
  unsigned int verbatim_length;
  unsigned int residual_size;
  unsigned int lpc_count;

  /*rewind the stream and re-read the header*/
  fseek(self->bitstream->file,0,SEEK_SET);
  self->bitstream->state = 0;

  SHNDecoder_read_header(self);

  /*walk through the Shorten file,
    counting the length of all audio data commands*/
  for (cmd = shn_read_uvar(self->bitstream,2);
       cmd != FN_QUIT;
       cmd = shn_read_uvar(self->bitstream,2)) {
    switch (cmd) {
    case FN_VERBATIM:
      verbatim_length = shn_read_uvar(self->bitstream, VERBATIM_CHUNK_SIZE);
      for (i = 0; i < verbatim_length; i++) {
	shn_skip_uvar(self->bitstream, VERBATIM_BYTE_SIZE);
      }
      break;
    case FN_DIFF0:
    case FN_DIFF1:
    case FN_DIFF2:
    case FN_DIFF3:
      total_samples += self->block_size;
      residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
      for (i = 0; i < self->block_size; i++) {
	shn_skip_var(self->bitstream, residual_size);
      }
      break;
    case FN_ZERO:
      total_samples += self->block_size;
      break;
    case FN_QLPC:
      total_samples += self->block_size;
      residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
      lpc_count = shn_read_uvar(self->bitstream, QLPC_SIZE);
      for (i = 0; i < lpc_count; i++) {
	shn_skip_var(self->bitstream, QLPC_QUANT);
      }
      for (i = 0; i < self->block_size; i++) {
	shn_skip_var(self->bitstream, residual_size);
      }
      break;
    case FN_BLOCKSIZE:
      self->block_size = shn_read_long(self->bitstream);
      break;
    default:
      PyErr_SetString(PyExc_ValueError,"unknown command encountered in Shorten stream");
      return NULL;
    }
  }

  return Py_BuildValue("i",total_samples / self->channels);
}


int SHNDecoder_read_header(decoders_SHNDecoder* self) {
  Bitstream* bs = self->bitstream;

  if (read_bits(bs, 32) != 0x616A6B67)
    return 0;

  self->version = read_bits(bs,8);
  self->file_type = shn_read_long(bs);
  self->channels = shn_read_long(bs);
  self->block_size = shn_read_long(bs);
  self->maxnlpc = shn_read_long(bs);
  self->nmean = shn_read_long(bs);
  self->nskip = shn_read_long(bs);
  /*FIXME - perform writing if bytes skipped*/
  self->wrap = self->maxnlpc > 3 ? self->maxnlpc : 3;

  self->read_started = 1;
  self->read_finished = 0;

  return 1;
}

void SHNDecoder_read_diff(struct i_array *buffer,
			  Bitstream* bs,
			  unsigned int block_size,
			  int (*calculation)(int residual,
					     struct i_array *buffer)) {
  unsigned int i;
  unsigned int residual_size = shn_read_uvar(bs,ENERGY_SIZE);

  for (i = 0; i < block_size; i++) {
    ia_append(buffer,calculation(shn_read_var(bs,residual_size),buffer));
  }
}

int SHNDecoder_diff0(int residual, struct i_array *buffer) {
  return residual;
}

int SHNDecoder_diff1(int residual, struct i_array *buffer) {
  return residual + ia_getitem(buffer,-1);
}

int SHNDecoder_diff2(int residual, struct i_array *buffer) {
  return residual + ((2 * ia_getitem(buffer,-1)) - ia_getitem(buffer,-2));
}

int SHNDecoder_diff3(int residual, struct i_array *buffer) {
  return residual + (3 * (ia_getitem(buffer,-1) -
			  ia_getitem(buffer,-2))) + ia_getitem(buffer,-3);
}

void SHNDecoder_read_zero(struct i_array *buffer,
			  unsigned int block_size) {
  int i;

  for (i = 0; i < block_size; i++) {
    ia_append(buffer,0);
  }
}

void SHNDecoder_read_lpc(struct i_array *buffer,
			 Bitstream* bs,
			 unsigned int block_size) {
  unsigned int residual_size = shn_read_uvar(bs, ENERGY_SIZE);
  unsigned int i,j;
  unsigned int lpc_count;
  struct i_array lpc_coeffs;
  struct i_array tail;
  int32_t sum;

  lpc_count = shn_read_uvar(bs, QLPC_SIZE);
  ia_init(&lpc_coeffs,lpc_count);
  for (i = 0; i < lpc_count; i++) {
    ia_append(&lpc_coeffs,shn_read_var(bs,QLPC_QUANT));
  }
  ia_reverse(&lpc_coeffs);
  for (i = 0; i < block_size; i++) {
    sum = QLPC_OFFSET;
    ia_tail(&tail,buffer,lpc_count);
    for (j = 0; j < lpc_count; j++) {
      sum += (int32_t)ia_getitem(&tail,j) * (int32_t)ia_getitem(&lpc_coeffs,j);
    }
    ia_append(buffer,shn_read_var(bs, residual_size) + (sum >> QLPC_QUANT));
  }
  ia_free(&lpc_coeffs);
}

unsigned int shn_read_uvar(Bitstream* bs, unsigned int count) {
  unsigned int high_bits = read_unary(bs,1);
  unsigned int low_bits = read_bits(bs,count);

  return (high_bits << count) | low_bits;
}

int shn_read_var(Bitstream* bs, unsigned int count) {
  unsigned int uvar = shn_read_uvar(bs, count + 1); /*1 additional sign bit*/
  if (uvar & 1)
    return ~(uvar >> 1);
  else
    return uvar >> 1;
}

unsigned int shn_read_long(Bitstream* bs) {
  return shn_read_uvar(bs,shn_read_uvar(bs,2));
}

void shn_skip_uvar(Bitstream* bs, unsigned int count) {
  read_unary(bs,1);
  read_bits(bs,count);
}

void shn_skip_var(Bitstream* bs, unsigned int count) {
  read_unary(bs,1);
  read_bits(bs,count + 1);
}
