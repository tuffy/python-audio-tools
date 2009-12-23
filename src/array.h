#ifndef ARRAY_H
#define ARRAY_H

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

#include <stdint.h>

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
static inline void ia_dupe(struct i_array *target, struct i_array *source) {
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

#endif
