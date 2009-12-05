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


