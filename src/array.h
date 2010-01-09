#ifndef ARRAY_H
#define ARRAY_H

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <float.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2009  Brian Langenberger

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

#define MIN(x,y) ((x) < (y) ? (x) : (y))
#define MAX(x,y) ((x) > (y) ? (x) : (y))

/*an array of int32_t values which can grow as needed
  typically for storing PCM sample values*/
struct i_array {
  int32_t *data;
  uint32_t size;
  uint32_t total_size;
};

void ia_init(struct i_array *array, uint32_t initial_size);

void ia_free(struct i_array *array);

static inline void ia_reset(struct i_array *array) {
  array->size = 0;
}

void ia_resize(struct i_array *array, uint32_t maximum_size);

static inline void ia_append(struct i_array *array, int32_t val) {
  if (array->size < array->total_size) {
    array->data[array->size++] = val;
  } else {
    array->total_size *= 2;
    array->data = realloc(array->data,array->total_size * sizeof(int32_t));
    array->data[array->size++] = val;
  }
}

static inline int32_t ia_getitem(struct i_array *array, int32_t index) {
  if (index >= 0) {
    return array->data[index];
  } else {
    return array->data[array->size + index];
  }
}

static inline void ia_setitem(struct i_array *array, int32_t index, int32_t value) {
  if (index >= 0) {
    array->data[index] = value;
  } else {
    array->data[array->size + index] = value;
  }
}

static inline void ia_reverse(struct i_array *array) {
  uint32_t start;
  uint32_t end;
  int32_t val;

  for (start = 0,end = array->size - 1;
       start < end;
       start++,end--) {
    val = array->data[start];
    array->data[start] = array->data[end];
    array->data[end] = val;
  }
}

/*duplicates the attributes of source in target,
  but not the array data itself
  analagous to calling ia_head(target,source,source->size)*/
static inline void ia_link(struct i_array *target, struct i_array *source) {
  target->size = source->size;
  target->total_size = source->total_size;
  target->data = source->data;
}

static inline void ia_head(struct i_array *target, struct i_array *source, uint32_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data;
}

static inline void ia_tail(struct i_array *target, struct i_array *source, uint32_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data + (source->size - size);
}

/*splits source into two lists, "head" and "tail"
  where "head" contains "split" number of elements
  and "tail" contains the rest*/
static inline void ia_split(struct i_array *head, struct i_array *tail,
			    struct i_array *source, uint32_t split) {
  if (split > source->size)
    split = source->size;

  head->size = split;
  head->total_size = source->total_size;
  head->data = source->data;

  tail->size = source->size - split;
  tail->total_size = source->total_size;
  tail->data = source->data + split;
}

void ia_print(FILE *stream, struct i_array *array);


void ia_U8_to_char(unsigned char *target, struct i_array *source,
		   int channel, int total_channels);

void ia_SL16_to_char(unsigned char *target, struct i_array *source,
		     int channel, int total_channels);

void ia_SL24_to_char(unsigned char *target, struct i_array *source,
		     int channel, int total_channels);


void ia_char_to_U8(struct i_array *target, unsigned char *source,
		   int source_len, int channel, int total_channels);

void ia_char_to_SL16(struct i_array *target, unsigned char *source,
		     int source_len, int channel, int total_channels);

void ia_char_to_SL24(struct i_array *target, unsigned char *source,
		     int source_len, int channel, int total_channels);

void ia_add(struct i_array *target,
	    struct i_array *source1, struct i_array *source2);

void ia_sub(struct i_array *target,
	    struct i_array *source1, struct i_array *source2);


/*an array of i_array structs
  typically for storing multiple channels of PCM values*/
struct ia_array {
  struct i_array *arrays;
  uint32_t size;
};

void iaa_init(struct ia_array *array, uint32_t total_arrays,
	      uint32_t initial_size);

void iaa_free(struct ia_array *array);

static inline struct i_array* iaa_getitem(struct ia_array *array, int32_t index) {
  if (index >= 0) {
    return &(array->arrays[index]);
  } else {
    return &(array->arrays[array->size + index]);
  }
}

static inline void iaa_reset(struct ia_array *array) {
  uint32_t i;

  for (i = 0; i < array->size; i++)
    ia_reset(&(array->arrays[i]));
}


/*an array of double values which can grow as needed*/
struct f_array {
  double *data;
  uint32_t size;
  uint32_t total_size;
};

void fa_init(struct f_array *array, uint32_t initial_size);

void fa_free(struct f_array *array);

static inline void fa_reset(struct f_array *array) {
  array->size = 0;
}

void fa_resize(struct f_array *array, uint32_t maximum_size);

static inline void fa_append(struct f_array *array, double value) {
  if (array->size < array->total_size) {
    array->data[array->size++] = value;
  } else {
    array->total_size *= 2;
    array->data = realloc(array->data,array->total_size * sizeof(double));
    array->data[array->size++] = value;
  }
}

static inline double fa_getitem(struct f_array *array, int32_t index) {
  if (index >= 0) {
    return array->data[index];
  } else {
    return array->data[array->size + index];
  }
}

static inline void fa_setitem(struct f_array *array, int32_t index, double value) {
  if (index >= 0) {
    array->data[index] = value;
  } else {
    array->data[array->size + index] = value;
  }
}

static inline void fa_head(struct f_array *target, struct f_array *source, uint32_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data;
}

static inline void fa_tail(struct f_array *target, struct f_array *source, uint32_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data + (source->size - size);
}

/*splits source into two lists, "head" and "tail"
  where "head" contains "split" number of elements
  and "tail" contains the rest*/
static inline void fa_split(struct f_array *head, struct f_array *tail,
			    struct f_array *source, uint32_t split) {
  if (split > source->size)
    split = source->size;

  head->size = split;
  head->total_size = source->total_size;
  head->data = source->data;

  tail->size = source->size - split;
  tail->total_size = source->total_size;
  tail->data = source->data + split;
}

static inline void fa_copy(struct f_array *target, struct f_array *source) {
  fa_resize(target,source->size);
  memcpy(target->data,source->data,source->size * sizeof(double));
  target->size = source->size;
}

static inline void fa_reverse(struct f_array *array) {
  uint32_t start;
  uint32_t end;
  double val;

  for (start = 0,end = array->size - 1;
       start < end;
       start++,end--) {
    val = array->data[start];
    array->data[start] = array->data[end];
    array->data[end] = val;
  }
}

void fa_print(FILE *stream, struct f_array *array);

double fa_sum(struct f_array *array);

void fa_mul(struct f_array *target,
	    struct f_array *source1, struct f_array *source2);

void fa_mul_ia(struct f_array *target,
	       struct f_array *source1, struct i_array *source2);

static inline double fa_max(struct f_array *array) {
  uint32_t i;
  double max = -DBL_MAX;
  for (i = 0; i < array->size; i++)
    max = MAX(array->data[i],max);
  return max;
}

static inline double fa_min(struct f_array *array) {
  uint32_t i;
  double min = DBL_MAX;
  for (i = 0; i < array->size; i++)
    min = MIN(array->data[i],min);
  return min;
}

static inline void fa_map(struct f_array *target,
			  struct f_array *source,
			  double (function)(double)) {
  uint32_t i;
  fa_resize(target,source->size);
  for (i = 0; i < source->size; i++)
    target->data[i] = function(source->data[i]);
  target->size = source->size;
}

/*an array if f_array structs*/
struct fa_array {
  struct f_array *arrays;
  uint32_t size;
};

void faa_init(struct fa_array *array, uint32_t total_arrays,
	      uint32_t initial_size);

void faa_free(struct fa_array *array);

static inline struct f_array* faa_getitem(struct fa_array *array, int32_t index) {
  if (index >= 0) {
    return &(array->arrays[index]);
  } else {
    return &(array->arrays[array->size + index]);
  }
}

static inline void faa_reset(struct fa_array *array) {
  uint32_t i;

  for (i = 0; i < array->size; i++)
    fa_reset(&(array->arrays[i]));
}

void faa_print(FILE *stream, struct fa_array *array);

#endif
