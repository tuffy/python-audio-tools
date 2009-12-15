#include "array.h"

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

void ia_init(struct i_array *array, uint32_t initial_size) {
  array->data = malloc(sizeof(int32_t) * initial_size);
  array->total_size = initial_size;
  array->size = 0;
}

void ia_free(struct i_array *array) {
  free(array->data);
}

void ia_resize(struct i_array *array, uint32_t maximum_size) {
  if (array->total_size < maximum_size) {
    array->total_size = maximum_size;
    array->data = realloc(array->data,maximum_size * sizeof(int32_t));
  }
}

void ia_print(FILE *stream,struct i_array *array) {
  int32_t i;

  fprintf(stream,"[");
  if (array->size <= 10) {
    for (i = 0; i < array->size; i++) {
      fprintf(stream,"%d",array->data[i]);
      if ((i + 1) < array->size)
	fprintf(stream,",");
    }
  } else {
    for (i = 0; i < 5; i++) {
      fprintf(stream,"%d,",ia_getitem(array,i));
    }
    fprintf(stream,"...,");
    for (i = -5; i < 0; i++) {
      fprintf(stream,"%d",ia_getitem(array,i));
      if ((i + 1) < 0)
	fprintf(stream,",");
    }
  }
  fprintf(stream,"]");
}

void ia_U8_to_char(unsigned char* target, struct i_array* source,
		   int channel, int total_channels) {
  uint32_t i;
  int32_t value;

  target += channel;

  for (i = 0; i < source->size; i++) {
    value = ia_getitem(source,i);
    target[0] = value & 0xFF;
    target += total_channels;
  }
}

void ia_SL16_to_char(unsigned char* target, struct i_array* source,
		     int channel, int total_channels) {
  uint32_t i;
  int32_t value;

  target += (channel * 2);

  for (i = 0; i < source->size; i++) {
    value = ia_getitem(source,i);
    /*avoid overflow/underflow*/
    if (value < -0x8000) value = -0x8000;
    else if (value > 0x7FFF) value = 0x7FFF;

    target[0] = value & 0x00FF;
    target[1] = (value & 0xFF00) >> 8;

    target += (total_channels * 2);
  }
}

void ia_SL24_to_char(unsigned char* target, struct i_array* source,
		     int channel, int total_channels) {
  uint32_t i;
  int32_t value;

  target += (channel * 3);

  for (i = 0; i < source->size; i++) {
    value = ia_getitem(source,i);
    /*avoid overflow/underflow*/
    if (value < -0x800000) value = -0x800000;
    else if (value > 0x7FFFFF) value = 0x7FFFFF;

    target[0] = value & 0x0000FF;
    target[1] = (value & 0x00FF00) >> 8;
    target[2] = (value & 0xFF0000) >> 16;

    target += (total_channels * 3);
  }
}


void ia_char_to_U8(struct i_array *target, unsigned char *source,
		   int source_len, int channel, int total_channels) {
  source += channel;
  source_len -= channel;

  for (;source_len >= 1;
       source += total_channels, source_len -= total_channels) {
    ia_append(target,(int32_t)source[0]);
  }
}

void ia_char_to_SL16(struct i_array *target, unsigned char *source,
		     int source_len, int channel, int total_channels) {
  source += (channel * 2);
  source_len -= (channel * 2);

  for (;source_len >= 2;
       source += (total_channels * 2), source_len -= (total_channels * 2)) {
    if ((source[1] & 0x80) != 0)
      /*negative*/
      ia_append(target,-(int32_t)(0x10000 - ((source[1] << 8) | source[0])));
    else
      /*positive*/
      ia_append(target,(int32_t)(source[1] << 8) | source[0]);
  }
}

void ia_char_to_SL24(struct i_array *target, unsigned char *source,
		     int source_len, int channel, int total_channels) {
  source += (channel * 3);
  source_len -= (channel * 3);

  for (;source_len >= 3;
       source += (total_channels * 3), source_len -= (total_channels * 3)) {
    if ((source[2] & 0x80) != 0)
      /*negative*/
      ia_append(target,
		-(int32_t)(0x1000000 -
			   ((source[2] << 16) | (source[1] << 8) | source[0])));
    else
      /*positive*/
      ia_append(target,
		(int32_t)(source[2] << 16) | (source[1] << 8) | source[0]);
  }
}

void ia_add(struct i_array *target,
	    struct i_array *source1, struct i_array *source2) {
  uint32_t size = source1->size > source2->size ? source1->size : source2->size;
  uint32_t i;

  ia_resize(target,size);
  for (i = 0; i < size; i++)
    target->data[i] = source1->data[i] + source2->data[i];
  target->size = size;
}

void ia_sub(struct i_array *target,
	    struct i_array *source1, struct i_array *source2) {
   uint32_t size = source1->size > source2->size ? source1->size : source2->size;
  uint32_t i;

  ia_resize(target,size);
  for (i = 0; i < size; i++)
    target->data[i] = source1->data[i] - source2->data[i];
  target->size = size;
}


void iaa_init(struct ia_array *array, uint32_t total_arrays,
	      uint32_t initial_size) {
  uint32_t i;

  array->arrays = malloc(sizeof(struct i_array) * total_arrays);
  array->size = total_arrays;
  for (i = 0; i < total_arrays; i++)
    ia_init(&(array->arrays[i]),initial_size);
}

void iaa_free(struct ia_array *array) {
  uint32_t i;

  for (i = 0; i < array->size; i++)
    ia_free(&(array->arrays[i]));

  free(array->arrays);
}
