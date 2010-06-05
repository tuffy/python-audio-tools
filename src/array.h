#ifndef ARRAY_H
#define ARRAY_H

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <float.h>
#include <limits.h>

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

/*FIXME - ensure the ia_* and fa_* functions have equivilents*/

#ifndef MIN
#define MIN(x,y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x,y) ((x) > (y) ? (x) : (y))
#endif

/*an array of int32_t values which can grow as needed
  typically for storing PCM sample values*/
typedef int32_t ia_data_t;
typedef uint32_t ia_size_t;
typedef int32_t ia_offset_t;

struct i_array {
  ia_data_t *data;
  ia_size_t size;
  ia_size_t total_size;
};

void ia_init(struct i_array *array, ia_size_t initial_size);

void ia_free(struct i_array *array);

static inline void ia_reset(struct i_array *array) {
  array->size = 0;
}

void ia_resize(struct i_array *array, ia_size_t maximum_size);

static inline void ia_append(struct i_array *array, ia_data_t val) {
  if (array->size < array->total_size) {
    array->data[array->size++] = val;
  } else {
    array->total_size *= 2;
    array->data = realloc(array->data,array->total_size * sizeof(ia_data_t));
    array->data[array->size++] = val;
  }
}

static inline ia_data_t ia_getitem(struct i_array *array, ia_offset_t index) {
  if (index >= 0) {
    return array->data[index];
  } else {
    return array->data[array->size + index];
  }
}

static inline void ia_setitem(struct i_array *array,
			      ia_offset_t index, ia_data_t value) {
  if (index >= 0) {
    array->data[index] = value;
  } else {
    array->data[array->size + index] = value;
  }
}

/*reverses the elements of "array" in place*/
static inline void ia_reverse(struct i_array *array) {
  ia_size_t start;
  ia_size_t end;
  ia_data_t val;

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

/*places a copied version of "source" to "target"*/
static inline void ia_copy(struct i_array *target, struct i_array *source) {
  ia_resize(target,source->size);
  memcpy(target->data,source->data,source->size * sizeof(ia_data_t));
  target->size = source->size;
}

/*appends the elements from "source" to the end of "target"*/
static inline void ia_extend(struct i_array *target, struct i_array *source) {
  ia_resize(target,target->size + source->size);
  memcpy(target->data + target->size,source->data,source->size * sizeof(ia_data_t));
  target->size += source->size;
}

void ia_from_list(struct i_array *target, int count, int *list);

/*places the first "size" number of elements from "source" to "target"

  "target" received a borrowed copy of "data"*/
static inline void ia_head(struct i_array *target, struct i_array *source, ia_size_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data;
}

/*This returns the 0th element of "source"
  and removes that value from the array by shifting its data up one notch.
  It's designed to be used in conjunction with ia_link()
  to avoid losing allocated data.*/
static inline ia_data_t ia_pop_head(struct i_array *source) {
  ia_data_t val = source->data[0];
  source->data++;
  source->size--;
  return val;
}

/*This returns the last element of "source"
  and removes that value from the array by shifting its size down one notch.

  Unline ia_pop_head, this will not lose allocated data.*/
static inline ia_data_t ia_pop_tail(struct i_array *source) {
  ia_data_t val = source->data[source->size - 1];
  source->size--;
  return val;
}

/*places the last "size" number of elements from "source" to "target"

  "target" received a borrowed copy of "data" if different from "source"
  otherwise, its data is shifted down appropriately*/
static inline void ia_tail(struct i_array *target, struct i_array *source, ia_size_t size) {
  if (target != source) {
    target->data = source->data + (source->size - size);
  } else {
    memmove(target->data,
	    source->data + (source->size - size),
	    size * sizeof(ia_data_t));
  }
  target->size = size;
  target->total_size = source->total_size;
}

/*splits source into two lists, "head" and "tail"
  where "head" contains "split" number of elements
  and "tail" contains the rest

  both elements received the same borrowed data element*/
static inline void ia_split(struct i_array *head, struct i_array *tail,
			    struct i_array *source, ia_size_t split) {
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

ia_data_t ia_sum(struct i_array *source);

ia_data_t ia_avg(struct i_array *source);

/*this calls "function" over the elements in source
  and returns a single value
  for example,  ia_reduce([1,2,3],0,f)  is the equivalent of calling:
  f(3,f(2,f(1,0)))
*/
static inline ia_data_t ia_reduce(struct i_array *source,
				  ia_data_t base,
				  ia_data_t (function)(ia_data_t, ia_data_t)) {
  ia_size_t i;

  if (source->size == 0)
    return base;
  else {
    for (i = 0; i < source->size; i++) {
      base = function(source->data[i],base);
    }
    return base;
  }
}

static inline ia_data_t ia_max(struct i_array *array) {
  ia_size_t i;
  ia_data_t max = INT_MIN;
  for (i = 0; i < array->size; i++)
    max = MAX(array->data[i],max);
  return max;
}

static inline ia_data_t ia_min(struct i_array *array) {
  ia_size_t i;
  ia_data_t min = INT_MAX;
  for (i = 0; i < array->size; i++)
    min = MIN(array->data[i],min);
  return min;
}



/*an array of i_array structs
  typically for storing multiple channels of PCM values*/
struct ia_array {
  struct i_array *arrays;
  ia_size_t size;
};

void iaa_init(struct ia_array *array, ia_size_t total_arrays,
	      ia_size_t initial_size);

void iaa_free(struct ia_array *array);

void iaa_copy(struct ia_array *target, struct ia_array *source);

static inline struct i_array* iaa_getitem(struct ia_array *array, ia_offset_t index) {
  if (index >= 0) {
    return &(array->arrays[index]);
  } else {
    return &(array->arrays[array->size + index]);
  }
}

static inline void iaa_reset(struct ia_array *array) {
  ia_size_t i;

  for (i = 0; i < array->size; i++)
    ia_reset(&(array->arrays[i]));
}


/*an array of double values which can grow as needed*/
typedef double fa_data_t;
typedef uint32_t fa_size_t;
typedef int32_t fa_offset_t;

struct f_array {
  fa_data_t *data;
  fa_size_t size;
  fa_size_t total_size;
};

void fa_init(struct f_array *array, fa_size_t initial_size);

void fa_free(struct f_array *array);

static inline void fa_reset(struct f_array *array) {
  array->size = 0;
}

void fa_resize(struct f_array *array, fa_size_t maximum_size);

static inline void fa_append(struct f_array *array, fa_data_t value) {
  if (array->size < array->total_size) {
    array->data[array->size++] = value;
  } else {
    array->total_size *= 2;
    array->data = realloc(array->data,array->total_size * sizeof(fa_data_t));
    array->data[array->size++] = value;
  }
}

static inline fa_data_t fa_getitem(struct f_array *array, fa_offset_t index) {
  if (index >= 0) {
    return array->data[index];
  } else {
    return array->data[array->size + index];
  }
}

static inline void fa_setitem(struct f_array *array, fa_offset_t index, fa_data_t value) {
  if (index >= 0) {
    array->data[index] = value;
  } else {
    array->data[array->size + index] = value;
  }
}

static inline void fa_head(struct f_array *target, struct f_array *source, fa_size_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data;
}

static inline void fa_tail(struct f_array *target, struct f_array *source, fa_size_t size) {
  if (target != source) {
    target->data = source->data + (source->size - size);
  } else {
    memmove(target->data,
	    source->data + (source->size - size),
	    size * sizeof(fa_data_t));
  }
  target->size = size;
  target->total_size = source->total_size;
}

/*splits source into two lists, "head" and "tail"
  where "head" contains "split" number of elements
  and "tail" contains the rest*/
static inline void fa_split(struct f_array *head, struct f_array *tail,
			    struct f_array *source, fa_size_t split) {
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
  memcpy(target->data,source->data,source->size * sizeof(fa_data_t));
  target->size = source->size;
}

static inline void fa_reverse(struct f_array *array) {
  fa_size_t start;
  fa_size_t end;
  fa_data_t val;

  for (start = 0,end = array->size - 1;
       start < end;
       start++,end--) {
    val = array->data[start];
    array->data[start] = array->data[end];
    array->data[end] = val;
  }
}

void fa_print(FILE *stream, struct f_array *array);

fa_data_t fa_sum(struct f_array *array);

void fa_mul(struct f_array *target,
	    struct f_array *source1, struct f_array *source2);

void fa_mul_ia(struct f_array *target,
	       struct f_array *source1, struct i_array *source2);

static inline fa_data_t fa_max(struct f_array *array) {
  fa_size_t i;
  fa_data_t max = -DBL_MAX;
  for (i = 0; i < array->size; i++)
    max = MAX(array->data[i],max);
  return max;
}

static inline fa_data_t fa_min(struct f_array *array) {
  fa_size_t i;
  fa_data_t min = DBL_MAX;
  for (i = 0; i < array->size; i++)
    min = MIN(array->data[i],min);
  return min;
}

static inline void fa_map(struct f_array *target,
			  struct f_array *source,
			  fa_data_t (function)(fa_data_t)) {
  fa_size_t i;
  fa_resize(target,source->size);
  for (i = 0; i < source->size; i++)
    target->data[i] = function(source->data[i]);
  target->size = source->size;
}

/*an array if f_array structs*/
struct fa_array {
  struct f_array *arrays;
  fa_size_t size;
};

static inline fa_data_t fa_reduce(struct f_array *source,
				  fa_data_t base,
				  fa_data_t (function)(fa_data_t, fa_data_t)) {
  fa_size_t i;

  if (source->size == 0)
    return base;
  else {
    for (i = 0; i < source->size; i++) {
      base = function(source->data[i],base);
    }
    return base;
  }
}

void faa_init(struct fa_array *array, fa_size_t total_arrays,
	      fa_size_t initial_size);

void faa_free(struct fa_array *array);

static inline struct f_array* faa_getitem(struct fa_array *array, fa_offset_t index) {
  if (index >= 0) {
    return &(array->arrays[index]);
  } else {
    return &(array->arrays[array->size + index]);
  }
}

static inline void faa_reset(struct fa_array *array) {
  fa_size_t i;

  for (i = 0; i < array->size; i++)
    fa_reset(&(array->arrays[i]));
}

void faa_print(FILE *stream, struct fa_array *array);

#endif
