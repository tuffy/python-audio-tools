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

void ia_reset(struct i_array *array);

void ia_resize(struct i_array *array, uint32_t maximum_size);

void ia_append(struct i_array *array, int32_t val);

int32_t ia_getitem(struct i_array *array, int32_t index);

void ia_setitem(struct i_array *array, int32_t index, int32_t value);

void ia_print(struct i_array *array);

void ia_reverse(struct i_array *array);

void ia_head(struct i_array *target, struct i_array *source, uint32_t size);

void ia_tail(struct i_array *target, struct i_array *source, uint32_t size);

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
