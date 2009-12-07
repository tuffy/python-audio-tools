#include "array.h"

void init_i_array(struct i_array *array, uint32_t initial_size) {
  array->data = malloc(sizeof(int32_t) * initial_size);
  array->total_size = initial_size;
  array->size = 0;
}

void free_i_array(struct i_array *array) {
  free(array->data);
}

void reset_i_array(struct i_array *array) {
  array->size = 0;
}

void append_i(struct i_array* array, int32_t val) {
  if (array->size < array->total_size) {
    array->data[array->size++] = val;
  } else {
    array->total_size *= 2;
    array->data = realloc(array->data,array->total_size);
    array->data[array->size++] = val;
  }
}


int32_t getitem_i(struct i_array *array, int32_t index) {
  if (index >= 0) {
    return array->data[index];
  } else {
    return array->data[array->size + index];
  }
}

void print_i(struct i_array *array) {
  int32_t i;

  printf("[");
  if (array->size <= 10) {
    for (i = 0; i < array->size; i++) {
      printf("%d",array->data[i]);
      if ((i + 1) < array->size)
	printf(",");
    }
  } else {
    for (i = 0; i < 5; i++) {
      printf("%d,",getitem_i(array,i));
    }
    printf("...,");
    for (i = -5; i < 0; i++) {
      printf("%d",getitem_i(array,i));
      if ((i + 1) < 0)
	printf(",");
    }
  }
  printf("]");
}

void reverse_i(struct i_array* array) {
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

void head_i(struct i_array* target, struct i_array* source, uint32_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data;
}

void tail_i(struct i_array* target, struct i_array* source, uint32_t size) {
  target->size = size;
  target->total_size = source->total_size;
  target->data = source->data + (source->size - size);
}

void S8_to_char_i(unsigned char* target, struct i_array* source,
		  int channel, int total_channels) {
  uint32_t i;
  int32_t value;

  target += channel;

  for (i = 0; i < source->size; i++) {
    value = getitem_i(source,i);
    /*avoid overflow/underflow*/
    if (value > 0x80) value = 0x80;
    else if (value < -0x7F) value = -0x7F;

    target[0] = (value + 0x7F) & 0xFF;

    target += total_channels;
  }
}

void SL16_to_char_i(unsigned char* target, struct i_array* source,
		    int channel, int total_channels) {
  uint32_t i;
  int32_t value;

  target += (channel * 2);

  for (i = 0; i < source->size; i++) {
    value = getitem_i(source,i);
    /*avoid overflow/underflow*/
    if (value < -0x8000) value = -0x8000;
    else if (value > 0x7FFF) value = 0x7FFF;

    target[0] = value & 0x00FF;
    target[1] = (value & 0xFF00) >> 8;

    target += (total_channels * 2);
  }
}

void SL24_to_char_i(unsigned char* target, struct i_array* source,
		    int channel, int total_channels) {
  uint32_t i;
  int32_t value;

  target += (channel * 3);

  for (i = 0; i < source->size; i++) {
    value = getitem_i(source,i);
    /*avoid overflow/underflow*/
    if (value < -0x800000) value = -0x800000;
    else if (value > 0x7FFFFF) value = 0x7FFFFF;

    target[0] = value & 0x0000FF;
    target[1] = (value & 0x00FF00) >> 8;
    target[2] = (value & 0xFF0000) >> 16;

    target += (total_channels * 3);
  }
}
