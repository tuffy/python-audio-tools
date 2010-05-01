#include "shn.h"

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

PyObject* encoders_encode_shn(PyObject *dummy,
			      PyObject *args, PyObject *keywds) {

  static char *kwlist[] = {"filename",
			   "pcmreader",
			   "block_size",
			   "verbatim_chunks",
			   NULL};
  char *filename;
  FILE *file;
  Bitstream *stream;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;

  int block_size;
  int wrap = 3;

  struct ia_array wrapped_samples;

  /*verbatim chunk variables*/
  PyObject *verbatim_chunks;
  Py_ssize_t verbatim_chunks_len;
  PyObject *verbatim_chunk;
  char *string;
  Py_ssize_t string_len;

  /*whether we've hit "None" and performed encoding or not*/
  int encoding_performed = 0;

  Py_ssize_t i,j;

  int bytes_written = 0;

  /*extract a filename, PCMReader-compatible object and encoding options*/
  if (!PyArg_ParseTupleAndKeywords(args,keywds,"sOiO",
				   kwlist,
				   &filename,
				   &pcmreader_obj,
				   &block_size,
				   &verbatim_chunks))
    return NULL;

  /*check for negative block_size*/
  if (block_size <= 0) {
    PyErr_SetString(PyExc_ValueError,"block_size must be positive");
    return NULL;
  }

  /*determine if verbatim_chunks is a valid sequence*/
  if ((verbatim_chunks_len = PySequence_Length(verbatim_chunks)) == -1) {
    return NULL;
  }

  /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
  if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
    return NULL;
  }

  /*determine if the PCMReader is compatible with Shorten*/
  if ((reader->bits_per_sample != 8) && (reader->bits_per_sample != 16)) {
    PyErr_SetString(PyExc_ValueError,"bits_per_sample must be 8 or 16");
    return NULL;
  }

  /*open the given filename for writing*/
  if ((file = fopen(filename,"wb")) == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return NULL;
  } else {
    stream = bs_open(file);
  }

  /*initialize wrapped samples with 0s*/
  iaa_init(&wrapped_samples,reader->channels,wrap);
  for (i = 0; i < reader->channels; i++) {
    for (j = 0; j < wrap; j++) {
      ia_append(iaa_getitem(&wrapped_samples,i),0);
    }
  }

  /*write header*/
  stream->write_bits(stream,32,0x616A6B67); /*the magic number 'ajkg'*/
  stream->write_bits(stream,8,2);           /*the version number 2*/

  /*start counting written bytes *after* writing the 5 byte header*/
  bs_add_callback(stream,ShortenEncoder_byte_counter,&bytes_written);

  /*file type is either 2 (unsigned 8-bit) or 5 (signed 16-bit little-endian)*/
  if (reader->bits_per_sample == 8) {
    ShortenEncoder_put_long(stream,2);
  }
  if (reader->bits_per_sample == 16) {
    ShortenEncoder_put_long(stream,5);
  }

  ShortenEncoder_put_long(stream,reader->channels);
  ShortenEncoder_put_long(stream,block_size);
  ShortenEncoder_put_long(stream,0);                /*max LPC = 0*/
  ShortenEncoder_put_long(stream,0);                /*number of means = 0*/
  ShortenEncoder_put_long(stream,0);                /*bytes to skip = 0*/

  /*iterate through verbatim_chunks*/
  for (i = 0; i < verbatim_chunks_len; i++) {
    if ((verbatim_chunk = PySequence_GetItem(verbatim_chunks,i)) == NULL)
      goto error;

    if (verbatim_chunk != Py_None) {
      /*any non-None values are turned into FN_VERBATIM commands*/
      if (PyString_AsStringAndSize(verbatim_chunk,&string,&string_len) == -1) {
	Py_DECREF(verbatim_chunk);
	goto error;
      }
      ShortenEncoder_put_uvar(stream,2,FN_VERBATIM);
      ShortenEncoder_put_uvar(stream,VERBATIM_CHUNK_SIZE,string_len);
      for (j = 0; j < string_len; j++)
	ShortenEncoder_put_uvar(stream,VERBATIM_BYTE_SIZE,(unsigned char)string[j]);

    } else if (!encoding_performed) {
      /*once None is hit, perform full encoding of reader,
	if it hasn't already*/
      if (!ShortenEncoder_encode_stream(stream,reader,block_size,&wrapped_samples))
      	goto error;
      encoding_performed = 1;
    }

    Py_DECREF(verbatim_chunk);
  }

  /*send the FN_QUIT command*/
  ShortenEncoder_put_uvar(stream,2,FN_QUIT);

  /*byte-align output*/
  stream->byte_align(stream);

  /*then, due to Shorten's silly way of using bit buffers,
    output (not counting the 5 bytes of magic + version)
    must be padded to a multiple of 4 bytes
    or its reference decoder explodes*/
  stream->write_bits(stream,(4 - (bytes_written % 4)) * 8,0);

  iaa_free(&wrapped_samples);
  pcmr_close(reader);
  bs_close(stream);
  Py_INCREF(Py_None);
  return Py_None;

 error:
  pcmr_close(reader);
  bs_close(stream);
  return NULL;
}

int ShortenEncoder_encode_stream(Bitstream* bs,
		      struct pcm_reader *reader,
		      int block_size,
		      struct ia_array* wrapped_samples) {
  struct ia_array samples;
  ia_size_t i;

  iaa_init(&samples,reader->channels,block_size);

  if (!pcmr_read(reader,block_size,&samples))
    goto error;

  /*iterate through all the integer arrays returned by "reader"*/
  while (samples.arrays[0].size > 0) {
    if (samples.arrays[0].size != block_size) {
      /*send a FN_BLOCKSIZE command if our returned block size changes
	(which should only happen at the end of the stream)*/
      block_size = samples.arrays[0].size;
      ShortenEncoder_put_uvar(bs,2,FN_BLOCKSIZE);
      ShortenEncoder_put_long(bs,block_size);
    }

    /*then send a separate command for each channel*/
    for (i = 0; i < samples.size; i++) {
      if (!ShortenEncoder_encode_channel(bs,
			      iaa_getitem(&samples,i),
			      iaa_getitem(wrapped_samples,i)))
	goto error;

    }

    if (!pcmr_read(reader,block_size,&samples))
      goto error;
  }

  iaa_free(&samples);
  return 1;
 error:
  iaa_free(&samples);
  return 0;
}

int ShortenEncoder_encode_channel(Bitstream* bs,
		       struct i_array* samples,
		       struct i_array* wrapped_samples) {
  struct i_array buffer;

  /*combine "samples" and "wrapped_samples" into a unified sample buffer*/
  ia_init(&buffer,wrapped_samples->size + samples->size);
  ia_copy(&buffer,wrapped_samples);
  ia_extend(&buffer,samples);

  switch (ShortenEncoder_compute_best_diff(&buffer,wrapped_samples->size)) {
  case FN_DIFF1:
    ShortenEncoder_put_uvar(bs,2,FN_DIFF1);
    ShortenEncoder_encode_diff(bs,&buffer,wrapped_samples,
			       ShortenEncoder_encode_diff1);
    break;
  case FN_DIFF2:
    ShortenEncoder_put_uvar(bs,2,FN_DIFF2);
    ShortenEncoder_encode_diff(bs,&buffer,wrapped_samples,
			       ShortenEncoder_encode_diff2);
    break;
  case FN_DIFF3:
    ShortenEncoder_put_uvar(bs,2,FN_DIFF3);
    ShortenEncoder_encode_diff(bs,&buffer,wrapped_samples,
			       ShortenEncoder_encode_diff3);
    break;
  }

  /*free allocated buffer*/
  ia_free(&buffer);

  /* shn_put_uvar(bs,2,FN_ZERO); */
  return 1;
}

int ShortenEncoder_compute_best_diff(struct i_array* buffer, int wrap) {
  /*I'm not using DIFF0 commands at all, so no delta0_sum*/
  uint64_t delta1_sum;
  uint64_t delta2_sum;
  uint64_t delta3_sum;

  struct i_array delta0;
  struct i_array delta1;
  struct i_array delta2;
  struct i_array delta3;
  struct i_array subtract;

  ia_size_t i;

  if (buffer->size <= 3)
    return FN_DIFF1;

  delta0.data = subtract.data = NULL;

  ia_tail(&delta0,buffer,buffer->size - wrap + 1);
  ia_tail(&subtract,&delta0,delta0.size - 1);
  ia_init(&delta1,buffer->size);
  ia_sub(&delta1,&delta0,&subtract);
  for (delta1_sum = 0,i = 0; i < delta1.size; i++)
    delta1_sum += abs(ia_getitem(&delta1,i));

  ia_tail(&subtract,&delta1,delta1.size - 1);
  ia_init(&delta2,buffer->size);
  ia_sub(&delta2,&delta1,&subtract);
  for (delta2_sum = 0,i = 0; i < delta2.size; i++)
    delta2_sum += abs(ia_getitem(&delta2,i));

  ia_tail(&subtract,&delta2,delta2.size - 1);
  ia_init(&delta3,buffer->size);
  ia_sub(&delta3,&delta2,&subtract);
  /*FIXME - not quite right
    Shorten's delta3 offset is last1 - (buf[-2] - buf[-3])*/
  for (delta3_sum = 0,i = 0; i < delta3.size; i++)
    delta3_sum += abs(ia_getitem(&delta3,i));

  ia_free(&delta1);
  ia_free(&delta2);
  ia_free(&delta3);

  if (delta1_sum < MIN(delta2_sum,delta3_sum))
    return FN_DIFF1;
  else if (delta2_sum < delta3_sum)
    return FN_DIFF2;
  else
    return FN_DIFF3;
}

int ShortenEncoder_encode_diff(Bitstream* bs,
			       struct i_array* buffer,
			       struct i_array* wrapped_samples,
			       ia_data_t (*calculator)(struct i_array* samples,
						       ia_size_t i)) {
  struct i_array residuals;
  struct i_array samples_tail;
  ia_size_t i;

  /*initialize space for residuals*/
  ia_init(&residuals,wrapped_samples->size);

  /*transform samples into residuals*/
  for (i = wrapped_samples->size; i < buffer->size; i++) {
    ia_append(&residuals,calculator(buffer,i));
  }

  /*write encoded residuals*/
  ShortenEncoder_encode_residuals(bs,&residuals);

  /*set new wrapped samples values*/
  ia_tail(&samples_tail,buffer,wrapped_samples->size);
  ia_copy(wrapped_samples,&samples_tail);

  /*free allocated space*/
  ia_free(&residuals);

  return 1;
}

ia_data_t ShortenEncoder_encode_diff1(struct i_array* samples, ia_size_t i) {
  return ia_getitem(samples,i) - ia_getitem(samples,i - 1);
}

ia_data_t ShortenEncoder_encode_diff2(struct i_array* samples, ia_size_t i) {
  return ia_getitem(samples,i) - ((2 * ia_getitem(samples,i - 1)) -
				  ia_getitem(samples,i - 2));
}

ia_data_t ShortenEncoder_encode_diff3(struct i_array* samples, ia_size_t i) {
  return ia_getitem(samples,i) - ((3 * ia_getitem(samples,i - 1)) -
				  (3 * ia_getitem(samples,i - 2)) +
				  ia_getitem(samples,i - 3));
}

int ShortenEncoder_encode_residuals(Bitstream* bs,
			 struct i_array* residuals) {
  int energy_size = ShortenEncoder_compute_best_energysize(residuals);
  ia_size_t i;

  ShortenEncoder_put_uvar(bs,ENERGY_SIZE,energy_size);
  for (i = 0; i < residuals->size; i++) {
    ShortenEncoder_put_var(bs,energy_size,ia_getitem(residuals,i));
  }

  return 1;
}

void ShortenEncoder_put_uvar(Bitstream* bs, int size, int value) {
  register int32_t msb; /*most significant bits*/
  register int32_t lsb; /*least significant bits*/

  msb = (int32_t)(value >> size);
  lsb = (int32_t)(value - (msb << size));
  bs->write_unary(bs,1,msb);
  bs->write_bits(bs,size,lsb);
}

void ShortenEncoder_put_var(Bitstream* bs, int size, int value) {
  if (value >= 0) {
    ShortenEncoder_put_uvar(bs,size + 1,value << 1);
  } else {
    ShortenEncoder_put_uvar(bs,size + 1,((-value - 1) << 1) | 1);
  }
}

void ShortenEncoder_put_long(Bitstream* bs, int value) {
  int long_size = 3; /*FIXME - this is supposed to be computed dynamically
		       but I'm not convinced it really matters
		       considering how little longs are used
		       in the Shorten stream*/

  ShortenEncoder_put_uvar(bs,2,long_size);
  ShortenEncoder_put_uvar(bs,long_size,value);
}

void ShortenEncoder_byte_counter(unsigned int byte, void* counter) {
  int* i_counter = (int*)counter;
  *i_counter += 1;
}

int ShortenEncoder_compute_best_energysize(struct i_array *residuals) {
  uint64_t abs_residual_partition_sum = abs_sum(residuals);
  int i;

  for (i = 0; ((uint64_t)residuals->size * (uint64_t)(1 << i)) < abs_residual_partition_sum; i++)
    /*do nothing*/;

  return i;
}
