#ifndef ARRAY_H
#define ARRAY_H

#include <stdint.h>

struct i_array {
  int32_t *data;
  uint32_t size;
  uint32_t total_size;
};

void init_i_array(struct i_array *array, uint32_t initial_size);

void free_i_array(struct i_array *array);

void reset_i_array(struct i_array *array);

void append_i(struct i_array* array, int32_t val);

int32_t getitem_i(struct i_array *array, int32_t index);

void print_i(struct i_array *array);

#endif

