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
  PyObject *verbatim_chunks;
  Py_ssize_t verbatim_chunks_len;
  PyObject *verbatim_chunk;
  Py_ssize_t i,j;

  char *string;
  Py_ssize_t string_len;

  int encoding_performed = 0;
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

  /*write header*/
  stream->write_bits(stream,32,0x616A6B67); /*the magic number 'ajkg'*/
  stream->write_bits(stream,8,2);           /*the version number 2*/

  /*start counting written bytes *after* writing the 5 byte header*/
  bs_add_callback(stream,shn_byte_counter,&bytes_written);

  /*file type is either 2 (unsigned 8-bit) or 5 (signed 16-bit little-endian)*/
  if (reader->bits_per_sample == 8) {
    shn_put_long(stream,2);
  }
  if (reader->bits_per_sample == 16) {
    shn_put_long(stream,5);
  }

  shn_put_long(stream,reader->channels);
  shn_put_long(stream,block_size);
  shn_put_long(stream,0);                /*max LPC = 0*/
  shn_put_long(stream,0);                /*number of means = 0*/
  shn_put_long(stream,0);                /*bytes to skip = 0*/

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
      shn_put_uvar(stream,2,FN_VERBATIM);
      shn_put_uvar(stream,VERBATIM_CHUNK_SIZE,string_len);
      for (j = 0; j < string_len; j++)
	shn_put_uvar(stream,VERBATIM_BYTE_SIZE,(unsigned char)string[j]);

    } else if (!encoding_performed) {
      /*once None is hit, perform full encoding of reader,
	if it hasn't already*/
      if (!shn_encode_stream(stream, reader, block_size, wrap))
      	goto error;
      encoding_performed = 1;
    }

    Py_DECREF(verbatim_chunk);
  }

  /*send the FN_QUIT command*/
  shn_put_uvar(stream,2,FN_QUIT);

  /*byte-align output*/
  stream->byte_align(stream);

  /*then, due to Shorten's silly way of using bit buffers,
    output (not counting the 5 bytes of magic + version)
    must be padded to a multiple of 4 bytes
    or its reference decoder explodes*/
  stream->write_bits(stream,(bytes_written % 4) * 8,0);

  pcmr_close(reader);
  bs_close(stream);
  Py_INCREF(Py_None);
  return Py_None;

 error:
  pcmr_close(reader);
  bs_close(stream);
  return NULL;
}

int shn_encode_stream(Bitstream* bs, struct pcm_reader *reader,
		      int block_size, int wrap) {
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
      shn_put_uvar(bs,2,FN_BLOCKSIZE);
      shn_put_long(bs,block_size);
    }

    /*then send a separate command for each channel*/
    for (i = 0; i < samples.size; i++) {
      /*FIXME - this will probably need to be adjusted
	to accomodate sample wrapping*/
      if (!shn_encode_channel(bs,iaa_getitem(&samples,i),wrap))
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

int shn_encode_channel(Bitstream* bs, struct i_array* samples, int wrap) {
  /*FIXME - for now, we'll just output ZERO commands*/
  shn_put_uvar(bs,2,FN_ZERO);
  return 1;
}

void shn_put_uvar(Bitstream* bs, int size, int value) {
  register int32_t msb; /*most significant bits*/
  register int32_t lsb; /*least significant bits*/

  msb = (int32_t)(value >> size);
  lsb = (int32_t)(value - (msb << size));
  bs->write_unary(bs,1,msb);
  bs->write_bits(bs,size,lsb);
}

void shn_put_var(Bitstream* bs, int size, int value) {
  return;
}

void shn_put_long(Bitstream* bs, int value) {
  int long_size = 3; /*FIXME - this is supposed to be computed dynamically
		       but I'm not convinced it really matters
		       considering how little longs are used
		       in the Shorten stream*/

  shn_put_uvar(bs,2,long_size);
  shn_put_uvar(bs,long_size,value);
}

void shn_byte_counter(unsigned int byte, void* counter) {
  int* i_counter = (int*)counter;
  *i_counter += 1;
}
