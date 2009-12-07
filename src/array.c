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
