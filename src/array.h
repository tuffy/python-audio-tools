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

void reverse_i(struct i_array* array);

void head_i(struct i_array* target, struct i_array* source, uint32_t size);

void tail_i(struct i_array* target, struct i_array* source, uint32_t size);

void S8_to_char_i(unsigned char* target, struct i_array* source,
		  int channel, int total_channels);

void SL16_to_char_i(unsigned char* target, struct i_array* source,
		    int channel, int total_channels);

void SL24_to_char_i(unsigned char* target, struct i_array* source,
		    int channel, int total_channels);

#endif
