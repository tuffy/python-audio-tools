#ifndef A_SHN_ENCODE
#define A_SHN_ENCODE

#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include "../bitstream_w.h"
#include "../array.h"
#include "../pcmreader.h"

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

#define ENERGY_SIZE 3
#define VERBATIM_CHUNK_SIZE 5
#define VERBATIM_BYTE_SIZE 8

enum {FN_DIFF0     = 0,
      FN_DIFF1     = 1,
      FN_DIFF2     = 2,
      FN_DIFF3     = 3,
      FN_QUIT      = 4,
      FN_BLOCKSIZE = 5,
      FN_QLPC      = 7,
      FN_ZERO      = 8,
      FN_VERBATIM  = 9};

typedef enum {OK,ERROR} status;

void ShortenEncoder_put_uvar(Bitstream* bs, int size, int value);
void ShortenEncoder_put_var(Bitstream* bs, int size, int value);
void ShortenEncoder_put_long(Bitstream* bs, int value);

int ShortenEncoder_encode_stream(Bitstream* bs,
		      struct pcm_reader* reader,
		      int block_size,
		      struct ia_array* wrapped_samples);

int ShortenEncoder_encode_channel(Bitstream* bs,
		       struct i_array* samples,
		       struct i_array* wrapped_samples);

int ShortenEncoder_compute_best_diff(struct i_array* buffer, int wrap);

int ShortenEncoder_encode_zero(struct i_array* buffer,
			       struct i_array* wrapped_samples);

int ShortenEncoder_encode_diff(Bitstream* bs,
			       struct i_array* buffer,
			       struct i_array* wrapped_samples,
			       ia_data_t (*calculator)(struct i_array* samples,
						       ia_size_t i));

ia_data_t ShortenEncoder_encode_diff1(struct i_array* samples, ia_size_t i);

ia_data_t ShortenEncoder_encode_diff2(struct i_array* samples, ia_size_t i);

ia_data_t ShortenEncoder_encode_diff3(struct i_array* samples, ia_size_t i);

int ShortenEncoder_encode_residuals(Bitstream* bs,
				    struct i_array* residuals);

int ShortenEncoder_compute_best_energysize(struct i_array *resuduals);

void ShortenEncoder_byte_counter(unsigned int byte, void* counter);

static inline uint64_t abs_sum(struct i_array *a) {
  register uint64_t sum = 0;
  ia_size_t a_size = a->size;
  ia_data_t *a_data = a->data;
  ia_size_t i;

  for (i = 0; i < a_size; i++)
    sum += abs(a_data[i]);

  return sum;
}

#endif
