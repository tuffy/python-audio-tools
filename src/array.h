#ifndef ARRAY_H
#define ARRAY_H

#include <stdint.h>

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

void ia_S8_to_char(unsigned char *target, struct i_array *source,
		   int channel, int total_channels);

void ia_SL16_to_char(unsigned char *target, struct i_array *source,
		     int channel, int total_channels);

void ia_SL24_to_char(unsigned char *target, struct i_array *source,
		     int channel, int total_channels);

void ia_add(struct i_array *target,
	    struct i_array *source1, struct i_array *source2);

void ia_sub(struct i_array *target,
	    struct i_array *source1, struct i_array *source2);

#endif
