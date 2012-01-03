#include "array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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

void
ia_init(struct i_array *array, ia_size_t initial_size)
{
    if (initial_size < 1)
        initial_size = 1;

    array->data = malloc(sizeof(ia_data_t) * initial_size);
    array->total_size = initial_size;
    array->size = 0;
}

void
ia_vappend(struct i_array *array, ia_size_t count, ...) {
    va_list ap;
    ia_size_t new_total_size;
    ia_data_t val;

    va_start(ap, count);

    /*allocate enough space for the new entries*/
    for (new_total_size = array->total_size;
         (array->size + count) > new_total_size;)
        new_total_size *= 2;
    if (new_total_size != array->total_size) {
        array->total_size = new_total_size;
        array->data = realloc(array->data,
                              new_total_size * sizeof(ia_data_t));
    }

    for (;count > 0; count--) {
        val = va_arg(ap, ia_data_t);
        array->data[array->size++] = val;
    }

    va_end(ap);
}

struct i_array
ia_blank(void) {
    struct i_array a;
    a.data = NULL;
    a.size = a.total_size = 0;
    return a;
}

void ia_free(struct i_array *array)
{
    if (array->data != NULL)
        free(array->data);
}

void
ia_resize(struct i_array *array, ia_size_t maximum_size)
{
    if (array->total_size < maximum_size) {
        array->total_size = maximum_size;
        array->data = realloc(array->data, maximum_size * sizeof(ia_data_t));
    }
}

void
ia_from_list(struct i_array *target, int count, int *list)
{
    int i;

    ia_resize(target, count);
    for (i = 0; i < count; i++)
        ia_append(target, list[i]);
}

void
ia_print(FILE *stream, struct i_array *array)
{
    ia_size_t i;

    fprintf(stream, "[");
    for (i = 0; i < array->size; i++) {
        fprintf(stream, "%d", ia_getitem(array, i));
        if ((i + 1) < array->size)
            fprintf(stream, ",");
    }
    fprintf(stream, "]");
}

void
ia_U8_to_char(unsigned char* target, struct i_array* source,
              int channel, int total_channels)
{
    ia_size_t i;
    ia_data_t value;

    target += channel;

    for (i = 0; i < source->size; i++) {
        value = ia_getitem(source, i);
        target[0] = value & 0xFF;
        target += total_channels;
    }
}

void
ia_SL16_to_char(unsigned char* target, struct i_array* source,
                int channel, int total_channels)
{
    ia_size_t i;
    ia_data_t value;

    target += (channel * 2);

    for (i = 0; i < source->size; i++) {
        value = ia_getitem(source, i);
        /*avoid overflow/underflow*/
        if (value < -0x8000) value = -0x8000;
        else if (value > 0x7FFF) value = 0x7FFF;

        target[0] = value & 0x00FF;
        target[1] = (value & 0xFF00) >> 8;

        target += (total_channels * 2);
    }
}

void
ia_SL24_to_char(unsigned char* target, struct i_array* source,
                int channel, int total_channels)
{
    ia_size_t i;
    ia_data_t value;

    target += (channel * 3);

    for (i = 0; i < source->size; i++) {
        value = ia_getitem(source, i);
        /*avoid overflow/underflow*/
        if (value < -0x800000) value = -0x800000;
        else if (value > 0x7FFFFF) value = 0x7FFFFF;

        target[0] = value & 0x0000FF;
        target[1] = (value & 0x00FF00) >> 8;
        target[2] = (value & 0xFF0000) >> 16;

        target += (total_channels * 3);
    }
}


void
ia_char_to_U8(struct i_array *target, unsigned char *source,
              int source_len, int channel, int total_channels)
{
    source += channel;
    source_len -= channel;

    /*FIXME - this can't be right, since it treats unsigned input as signed
      The long-term solution will be to have IO work on blobs of
      endian-independent integers, but that's further down the line.
      This will have to suffice in the short term.*/
    for (;source_len >= 1;
         source += total_channels, source_len -= total_channels)
        if ((source[0] & 0x80))
            ia_append(target, -(ia_data_t)(0x100 - source[0]));
        else
            ia_append(target, (ia_data_t)source[0]);
}

void
ia_char_to_SL16(struct i_array *target, unsigned char *source,
                int source_len, int channel, int total_channels)
{
    source += (channel * 2);
    source_len -= (channel * 2);

    for (;source_len >= 2;
         source += (total_channels * 2), source_len -= (total_channels * 2)) {
        if ((source[1] & 0x80) != 0)
            /*negative*/
            ia_append(target, -(ia_data_t)(0x10000 -
                                           ((source[1] << 8) | source[0])));
        else
            /*positive*/
            ia_append(target, (ia_data_t)(source[1] << 8) | source[0]);
    }
}

void
ia_char_to_SL24(struct i_array *target, unsigned char *source,
                int source_len, int channel, int total_channels)
{
    source += (channel * 3);
    source_len -= (channel * 3);

    for (;source_len >= 3;
         source += (total_channels * 3), source_len -= (total_channels * 3)) {
        if ((source[2] & 0x80) != 0)
            /*negative*/
            ia_append(target,
                      -(ia_data_t)(0x1000000 -
                                   ((source[2] << 16) |
                                    (source[1] << 8) |
                                    source[0])));
        else
            /*positive*/
            ia_append(target,
                      (ia_data_t)((source[2] << 16) |
                                  (source[1] << 8) |
                                  source[0]));
    }
}

void
ia_add(struct i_array *target, struct i_array *source1,
       struct i_array *source2)
{
    ia_size_t size = source1->size < source2->size ? source1->size :
        source2->size;
    ia_size_t i;

    ia_resize(target, size);
    for (i = 0; i < size; i++)
        target->data[i] = source1->data[i] + source2->data[i];
    target->size = size;
}

void
ia_sub(struct i_array *target, struct i_array *source1,
       struct i_array *source2)
{
    ia_size_t size = source1->size < source2->size ? source1->size :
        source2->size;
    ia_size_t i;
    ia_data_t *target_data = target->data;
    ia_data_t *source1_data = source1->data;
    ia_data_t *source2_data = source2->data;

    ia_resize(target, size);
    for (i = 0; i < size; i++)
        target_data[i] = source1_data[i] - source2_data[i];
    target->size = size;
}

ia_data_t
ia_sum(struct i_array *source)
{
    ia_data_t accumulator = 0;
    ia_size_t i;

    for (i = 0; i < source->size; i++)
        accumulator += source->data[i];

    return accumulator;
}

ia_data_t
ia_avg(struct i_array *source)
{
    ia_data_t accumulator = 0;
    ia_size_t i;

    for (i = 0; i < source->size; i++)
        accumulator += source->data[i];

    return accumulator / source->size;
}

void
iaa_init(struct ia_array *array, ia_size_t total_arrays,
         ia_size_t initial_size)
{
    ia_size_t i;

    array->arrays = malloc(sizeof(struct i_array) * total_arrays);
    array->size = total_arrays;
    array->total_size = total_arrays;
    for (i = 0; i < total_arrays; i++)
        ia_init(&(array->arrays[i]), initial_size);
}


struct ia_array
iaa_blank(void) {
    struct ia_array a;
    a.size = 0;
    a.total_size = 0;
    a.arrays = NULL;
    return a;
}


void
iaa_free(struct ia_array *array)
{
    ia_size_t i;

    for (i = 0; i < array->total_size; i++)
        ia_free(&(array->arrays[i]));

    if (array->arrays != NULL)
        free(array->arrays);
}

void
iaa_copy(struct ia_array *target, struct ia_array *source)
{
    ia_size_t i;

    for (i = 0; i < source->size; i++)
        ia_copy(&(target->arrays[i]), &(source->arrays[i]));
    target->size = source->size;
}

void iaa_print(FILE *stream, struct ia_array *array) {
    ia_size_t i;

    fprintf(stream, "[");
    for (i = 0; i < array->size; i++) {
        ia_print(stream, iaa_getitem(array, i));
        if ((i + 1) < array->size)
            fprintf(stream, ",");
    }
    fprintf(stream, "]");
}

void
fa_init(struct f_array *array, fa_size_t initial_size)
{
    if (initial_size < 1)
        initial_size = 1;

    array->data = malloc(sizeof(fa_data_t) * initial_size);
    array->total_size = initial_size;
    array->size = 0;
}

void
fa_free(struct f_array *array)
{
    free(array->data);
}

void
fa_resize(struct f_array *array, fa_size_t maximum_size)
{
    if (array->total_size < maximum_size) {
        array->total_size = maximum_size;
        array->data = realloc(array->data, maximum_size * sizeof(fa_data_t));
    }
}

void
fa_print(FILE *stream, struct f_array *array)
{
    fa_size_t i;

    fprintf(stream, "[");
    if (array->size <= 20) {
        for (i = 0; i < array->size; i++) {
            fprintf(stream, "%f", array->data[i]);
            if ((i + 1) < array->size)
                fprintf(stream, ",");
        }
    } else {
        for (i = 0; i < 5; i++) {
            fprintf(stream, "%f,", fa_getitem(array, i));
        }
        fprintf(stream, "...,");
        for (i = -5; i < 0; i++) {
            fprintf(stream, "%f", fa_getitem(array, i));
            if ((i + 1) < array->size)
                fprintf(stream, ",");
        }
    }
    fprintf(stream, "]");
}

fa_data_t
fa_sum(struct f_array *array)
{
    fa_data_t accumulator = 0.0;
    fa_size_t i;

    for (i = 0; i < array->size; i++)
        accumulator += array->data[i];

    return accumulator;
}

void
fa_mul(struct f_array *target, struct f_array *source1,
       struct f_array *source2)
{
    fa_size_t size = source1->size < source2->size ? source1->size :
        source2->size;
    fa_size_t i;

    fa_resize(target, size);
    for (i = 0; i < size; i++)
        target->data[i] = source1->data[i] * source2->data[i];
    target->size = size;
}

void
fa_mul_ia(struct f_array *target, struct f_array *source1,
          struct i_array *source2)
{
    fa_size_t size = source1->size < source2->size ? source1->size :
        source2->size;
    fa_size_t i;

    fa_resize(target, size);
    for (i = 0; i < size; i++)
        target->data[i] = source1->data[i] * source2->data[i];
    target->size = size;
}

void
faa_init(struct fa_array *array, fa_size_t total_arrays,
         fa_size_t initial_size)
{
    fa_size_t i;

    if (total_arrays > 0) {
        array->arrays = malloc(sizeof(struct f_array) * total_arrays);
        array->size = total_arrays;
        for (i = 0; i < total_arrays; i++)
            fa_init(&(array->arrays[i]), initial_size);
    } else {
        array->arrays = NULL;
        array->size = 0;
    }
}

void
faa_free(struct fa_array *array)
{
    fa_size_t i;

    for (i = 0; i < array->size; i++)
        fa_free(&(array->arrays[i]));

    free(array->arrays);
}

void
faa_print(FILE *stream, struct fa_array *array)
{
    fa_size_t i;

    fprintf(stream, "[");
    for (i = 0; i < array->size; i++) {
        fa_print(stream, faa_getitem(array, i));
        if ((i + 1) < array->size)
            fprintf(stream, ",");
    }
    fprintf(stream, "]");
}
