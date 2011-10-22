#ifndef ARRAY2_H
#define ARRAY2_H

#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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


/***************************************************************
 *                        integer arrays                       *
 ***************************************************************/

typedef struct array_i_s {
    int *data;
    unsigned size;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_i_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_i_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_i_s *array);

    /*appends a single value to the array*/
    void (*append)(struct array_i_s *array, int value);

    /*appends several values to the array*/
    void (*vappend)(struct array_i_s *array, unsigned count, ...);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_i_s *array, struct array_i_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(struct array_i_s *array, struct array_i_s *compare);

    /*returns the smallest value in the array,
      or INT_MAX if the array is empty*/
    int (*min)(struct array_i_s *array);

    /*returns the largest value in the array,
      or INT_MIN if the array is empty*/
    int (*max)(struct array_i_s *array);

    /*returns the sum of all items in the array*/
    int (*sum)(struct array_i_s *array);

    /*returns a new array with all the items copied from this array*/
    void (*copy)(struct array_i_s *array, struct array_i_s *copy);

    /*returns a new array with "count" number of items
      copied from the start of this array, or as many as possible*/
    void (*head)(struct array_i_s *array, unsigned count,
                 struct array_i_s *head);

    /*returns a new array with "count" number of items
      copied from the end of this array, or as many as possible*/
    void (*tail)(struct array_i_s *array, unsigned count,
                 struct array_i_s *tail);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(struct array_i_s *array, unsigned count,
                  struct array_i_s *head, struct array_i_s *tail);

    /*returns a new array with items copied from "start" up to "end"*/
    void (*slice)(struct array_i_s *array,
                  unsigned start, unsigned end, unsigned jump,
                  struct array_i_s *slice);

    /*reverses the items in the array*/
    void (*reverse)(struct array_i_s *array);

    /*sorts the items in the array*/
    void (*sort)(struct array_i_s *array);

    void (*print)(struct array_i_s *array, FILE* output);
} array_i;

/*returns a new array_i with space for "count" items*/
array_i* array_i_new(unsigned count);

array_i* array_i_wrap(int* data, unsigned size, unsigned total_size);

void array_i_del(array_i *array);
void array_i_resize(array_i *array, unsigned minimum);
void array_i_reset(array_i *array);
void array_i_append(array_i *array, int value);
void array_i_vappend(array_i *array, unsigned count, ...);
void array_i_extend(array_i *array, array_i *to_add);
int array_i_equals(array_i *array, array_i *compare);
int array_i_min(array_i *array);
int array_i_max(array_i *array);
int array_i_sum(array_i *array);
void array_i_copy(array_i *array, array_i *copy);
void array_i_head(array_i *array, unsigned count, array_i *head);
void array_i_tail(array_i *array, unsigned count, array_i *tail);
void array_i_split(array_i *array, unsigned count,
                   array_i *head, array_i *tail);
void array_i_slice(array_i *array,
                   unsigned start, unsigned end, unsigned jump,
                   array_i *slice);
void array_i_reverse(array_i *array);
void array_i_sort(array_i *array);
void array_i_print(array_i *array, FILE* output);


/***************************************************************
 *                     floating point arrays                   *
 ***************************************************************/

typedef struct array_f_s {
    double *data;
    unsigned size;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_f_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_f_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_f_s *array);

    /*appends a single value to the array*/
    void (*append)(struct array_f_s *array, double value);

    /*appends several values to the array*/
    void (*vappend)(struct array_f_s *array, unsigned count, ...);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_f_s *array, struct array_f_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(struct array_f_s *array, struct array_f_s *compare);

    /*returns the smallest value in the array,
      or INT_MAX if the array is empty*/
    double (*min)(struct array_f_s *array);

    /*returns the largest value in the array,
      or INT_MIN if the array is empty*/
    double (*max)(struct array_f_s *array);

    /*returns the sum of all items in the array*/
    double (*sum)(struct array_f_s *array);

    /*returns a new array with all the items copied from this array*/
    void (*copy)(struct array_f_s *array, struct array_f_s *copy);

    /*returns a new array with "count" number of items
      copied from the start of this array, or as many as possible*/
    void (*head)(struct array_f_s *array, unsigned count,
                 struct array_f_s *head);

    /*returns a new array with "count" number of items
      copied from the end of this array, or as many as possible*/
    void (*tail)(struct array_f_s *array, unsigned count,
                 struct array_f_s *tail);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(struct array_f_s *array, unsigned count,
                  struct array_f_s *head, struct array_f_s *tail);

    /*returns a new array with items copied from "start" up to "end"*/
    void (*slice)(struct array_f_s *array,
                  unsigned start, unsigned end, unsigned jump,
                  struct array_f_s *slice);

    /*reverses the items in the array*/
    void (*reverse)(struct array_f_s *array);

    /*sorts the items in the array*/
    void (*sort)(struct array_f_s *array);

    void (*print)(struct array_f_s *array, FILE* output);
} array_f;

/*returns a new array_f with space for "count" items*/
array_f* array_f_new(unsigned count);

array_f* array_f_wrap(double* data, unsigned size, unsigned total_size);

void array_f_del(array_f *array);
void array_f_resize(array_f *array, unsigned minimum);
void array_f_reset(array_f *array);
void array_f_append(array_f *array, double value);
void array_f_vappend(array_f *array, unsigned count, ...);
void array_f_extend(array_f *array, array_f *to_add);
int array_f_equals(array_f *array, array_f *compare);
double array_f_min(array_f *array);
double array_f_max(array_f *array);
double array_f_sum(array_f *array);
void array_f_copy(array_f *array, array_f *copy);
void array_f_head(array_f *array, unsigned count, array_f *head);
void array_f_tail(array_f *array, unsigned count, array_f *tail);
void array_f_split(array_f *array, unsigned count,
                   array_f *head, array_f *tail);
void array_f_slice(array_f *array,
                   unsigned start, unsigned end, unsigned jump,
                   array_f *slice);
void array_f_reverse(array_f *array);
void array_f_sort(array_f *array);
void array_f_print(array_f *array, FILE* output);


/***************************************************************
 *                    arrays of integer arrays                 *
 ***************************************************************/

typedef struct array_ia_s {
    array_i **data;
    unsigned size;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_ia_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_ia_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_ia_s *array);

    /*appends a single value to the array*/
    void (*append)(struct array_ia_s *array, array_i *value);

    /*appends several values to the array*/
    void (*vappend)(struct array_ia_s *array, unsigned count, ...);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_ia_s *array, struct array_ia_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(struct array_ia_s *array, struct array_ia_s *compare);

    /*reverses the items in the array*/
    void (*reverse)(struct array_ia_s *array);

    void (*print)(struct array_ia_s *array, FILE* output);
} array_ia;

array_ia* array_ia_new(unsigned count);

void array_ia_del(array_ia *array);
void array_ia_resize(array_ia *array, unsigned minimum);
void array_ia_reset(array_ia *array);
void array_ia_append(array_ia *array, array_i *value);
void array_ia_vappend(array_ia *array, unsigned count, ...);
void array_ia_extend(array_ia *array, array_ia *to_add);
int array_ia_equals(array_ia *array, array_ia *compare);
void array_ia_reverse(array_ia *array);
void array_ia_print(array_ia *array, FILE* output);


/***************************************************************
 *                     arrays of float arrays                  *
 ***************************************************************/

typedef struct array_fa_s {
    array_f **data;
    unsigned size;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_fa_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_fa_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_fa_s *array);

    /*appends a single value to the array*/
    void (*append)(struct array_fa_s *array, array_f *value);

    /*appends several values to the array*/
    void (*vappend)(struct array_fa_s *array, unsigned count, ...);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_fa_s *array, struct array_fa_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(struct array_fa_s *array, struct array_fa_s *compare);

    /*reverses the items in the array*/
    void (*reverse)(struct array_fa_s *array);

    void (*print)(struct array_fa_s *array, FILE* output);
} array_fa;

array_fa* array_fa_new(unsigned count);

void array_fa_del(array_fa *array);
void array_fa_resize(array_fa *array, unsigned minimum);
void array_fa_reset(array_fa *array);
void array_fa_append(array_fa *array, array_f *value);
void array_fa_vappend(array_fa *array, unsigned count, ...);
void array_fa_extend(array_fa *array, array_fa *to_add);
int array_fa_equals(array_fa *array, array_fa *compare);
void array_fa_reverse(array_fa *array);
void array_fa_print(array_fa *array, FILE* output);

#endif
