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


/*appends a single value to the given array
  "array" is evaluated twice, while "value" is evaluated only once
  this presumes array has been resized in advance for additional items:

  array->reset(array);
  array->resize(array, count);
  for (i = 0; i < count; i++)
      a_append(array, data[i]);

  it works equally well for array_i and array_f
*/
#define a_append(array, value)((array)->data[(array)->size++] = (value))


/***************************************************************
 *                        integer arrays                       *
 ***************************************************************/

struct array_li_s;

struct array_i_s {
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
    void (*extend)(struct array_i_s *array, const struct array_i_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_i_s *array,
                  const struct array_i_s *compare);

    /*returns the smallest value in the array,
      or INT_MAX if the array is empty*/
    int (*min)(const struct array_i_s *array);

    /*returns the largest value in the array,
      or INT_MIN if the array is empty*/
    int (*max)(const struct array_i_s *array);

    /*returns the sum of all items in the array*/
    int (*sum)(const struct array_i_s *array);

    /*returns a new array with all the items copied from this array*/
    void (*copy)(const struct array_i_s *array, struct array_i_s *copy);

    /*links the contents of this array to a read-only array*/
    void (*link)(const struct array_i_s *array, struct array_li_s *link);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_i_s *array, struct array_i_s *swap);

    /*moves "count" number of items from the start of this array
      to "head", or as many as possible*/
    void (*head)(const struct array_i_s *array, unsigned count,
                 struct array_i_s *head);

    /*moves "count" number of items from the end of this array
      to "tail", or as many as possible*/
    void (*tail)(const struct array_i_s *array, unsigned count,
                 struct array_i_s *tail);

    /*moves all except the first "count" number of items
      from this array to "tail", or as many as possible*/
    void (*de_head)(const struct array_i_s *array, unsigned count,
                    struct array_i_s *tail);

    /*moves all except the last "count" number of items
      from this array to "head", or as many as possible*/
    void (*de_tail)(const struct array_i_s *array, unsigned count,
                    struct array_i_s *head);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_i_s *array, unsigned count,
                  struct array_i_s *head, struct array_i_s *tail);

    /*copies items from "start" up to "end" to "slice"*/
    void (*slice)(const struct array_i_s *array,
                  unsigned start, unsigned end, unsigned jump,
                  struct array_i_s *slice);

    /*reverses the items in the array*/
    void (*reverse)(struct array_i_s *array);

    /*sorts the items in the array*/
    void (*sort)(struct array_i_s *array);

    void (*print)(const struct array_i_s *array, FILE* output);
};

typedef struct array_i_s array_i;

/*returns a new array_i with space for "count" items*/
struct array_i_s* array_i_new(void);

struct array_i_s* array_i_wrap(int* data, unsigned size, unsigned total_size);

void array_i_del(struct array_i_s *array);
void array_i_resize(struct array_i_s *array, unsigned minimum);
void array_i_reset(struct array_i_s *array);
void array_i_append(struct array_i_s *array, int value);
void array_i_vappend(struct array_i_s *array, unsigned count, ...);
void array_i_extend(struct array_i_s *array, const struct array_i_s *to_add);
int array_i_equals(const struct array_i_s *array,
                   const struct array_i_s *compare);
int array_i_min(const struct array_i_s *array);
int array_i_max(const struct array_i_s *array);
int array_i_sum(const struct array_i_s *array);
void array_i_copy(const struct array_i_s *array, struct array_i_s *copy);
void array_i_link(const struct array_i_s *array, struct array_li_s *link);
void array_i_swap(struct array_i_s *array, struct array_i_s *swap);
void array_i_head(const struct array_i_s *array, unsigned count,
                  struct array_i_s *head);
void array_i_tail(const struct array_i_s *array, unsigned count,
                  struct array_i_s *tail);
void array_i_de_head(const struct array_i_s *array, unsigned count,
                     struct array_i_s *tail);
void array_i_de_tail(const struct array_i_s *array, unsigned count,
                     struct array_i_s *head);
void array_i_split(const struct array_i_s *array, unsigned count,
                   struct array_i_s *head, struct array_i_s *tail);
void array_i_slice(const struct array_i_s *array,
                   unsigned start, unsigned end, unsigned jump,
                   struct array_i_s *slice);
void array_i_reverse(struct array_i_s *array);
void array_i_sort(struct array_i_s *array);
void array_i_print(const struct array_i_s *array, FILE* output);


/***************************************************************
 *                     linked integer arrays                   *
 ***************************************************************/

struct array_li_s {
    int *data;
    unsigned size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_li_s *array);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_li_s *array,
                  const struct array_li_s *compare);

    /*returns the smallest value in the array,
      or INT_MAX if the array is empty*/
    int (*min)(const struct array_li_s *array);

    /*returns the largest value in the array,
      or INT_MIN if the array is empty*/
    int (*max)(const struct array_li_s *array);

    /*returns the sum of all items in the array*/
    int (*sum)(const struct array_li_s *array);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_li_s *array, struct array_li_s *swap);

    /*moves "count" number of items from the start of this array
      to "head", or as many as possible*/
    void (*head)(const struct array_li_s *array, unsigned count,
                 struct array_li_s *head);

    /*moves "count" number of items from the start of this array
      to "head", or as many as possible*/
    void (*tail)(const struct array_li_s *array, unsigned count,
                 struct array_li_s *tail);

    /*moves all except the first "count" number of items
      from this array to "tail", or as many as possible*/
    void (*de_head)(const struct array_li_s *array, unsigned count,
                    struct array_li_s *tail);

    /*moves all except the last "count" number of items
      from this array to "head", or as many as possible*/
    void (*de_tail)(const struct array_li_s *array, unsigned count,
                    struct array_li_s *head);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_li_s *array, unsigned count,
                  struct array_li_s *head, struct array_li_s *tail);

    void (*print)(const struct array_li_s *array, FILE* output);
};

typedef struct array_li_s array_li;

struct array_li_s* array_li_new(void);

void array_li_del(struct array_li_s *array);
int array_li_equals(const struct array_li_s *array,
                    const struct array_li_s *compare);
int array_li_min(const struct array_li_s *array);
int array_li_max(const struct array_li_s *array);
int array_li_sum(const struct array_li_s *array);
void array_li_swap(struct array_li_s *array, struct array_li_s *swap);
void array_li_head(const struct array_li_s *array, unsigned count,
                   struct array_li_s *head);
void array_li_tail(const struct array_li_s *array, unsigned count,
                   struct array_li_s *tail);
void array_li_de_head(const struct array_li_s *array, unsigned count,
                      struct array_li_s *tail);
void array_li_de_tail(const struct array_li_s *array, unsigned count,
                      struct array_li_s *head);
void array_li_split(const struct array_li_s *array, unsigned count,
                    struct array_li_s *head, struct array_li_s *tail);
void array_li_print(const struct array_li_s *array, FILE* output);


/***************************************************************
 *                     floating point arrays                   *
 ***************************************************************/

struct array_lf_s;

struct array_f_s {
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
    void (*extend)(struct array_f_s *array, const struct array_f_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_f_s *array,
                  const struct array_f_s *compare);

    /*returns the smallest value in the array,
      or INT_MAX if the array is empty*/
    double (*min)(const struct array_f_s *array);

    /*returns the largest value in the array,
      or INT_MIN if the array is empty*/
    double (*max)(const struct array_f_s *array);

    /*returns the sum of all items in the array*/
    double (*sum)(const struct array_f_s *array);

    /*returns a new array with all the items copied from this array*/
    void (*copy)(const struct array_f_s *array, struct array_f_s *copy);

    /*links the contents of this array to a read-only array*/
    void (*link)(const struct array_f_s *array, struct array_lf_s *link);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_f_s *array, struct array_f_s *swap);

    /*returns a new array with "count" number of items
      copied from the start of this array, or as many as possible*/
    void (*head)(const struct array_f_s *array, unsigned count,
                 struct array_f_s *head);

    /*returns a new array with "count" number of items
      copied from the end of this array, or as many as possible*/
    void (*tail)(const struct array_f_s *array, unsigned count,
                 struct array_f_s *tail);

    /*moves all except the first "count" number of items
      from this array to "tail", or as many as possible*/
    void (*de_head)(const struct array_f_s *array, unsigned count,
                    struct array_f_s *tail);

    /*moves all except the last "count" number of items
      from this array to "head", or as many as possible*/
    void (*de_tail)(const struct array_f_s *array, unsigned count,
                    struct array_f_s *head);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_f_s *array, unsigned count,
                  struct array_f_s *head, struct array_f_s *tail);

    /*copies items from "start" to "end" to "slice"*/
    void (*slice)(const struct array_f_s *array,
                  unsigned start, unsigned end, unsigned jump,
                  struct array_f_s *slice);

    /*reverses the items in the array*/
    void (*reverse)(struct array_f_s *array);

    /*sorts the items in the array*/
    void (*sort)(struct array_f_s *array);

    void (*print)(const struct array_f_s *array, FILE* output);
};

typedef struct array_f_s array_f;

/*returns a new array_f with space for "count" items*/
struct array_f_s* array_f_new(void);

struct array_f_s* array_f_wrap(double* data, unsigned size,
                               unsigned total_size);

void array_f_del(struct array_f_s *array);
void array_f_resize(struct array_f_s *array, unsigned minimum);
void array_f_reset(struct array_f_s *array);
void array_f_append(struct array_f_s *array, double value);
void array_f_vappend(struct array_f_s *array, unsigned count, ...);
void array_f_extend(struct array_f_s *array, const struct array_f_s *to_add);
int array_f_equals(const struct array_f_s *array,
                   const struct array_f_s *compare);
double array_f_min(const struct array_f_s *array);
double array_f_max(const struct array_f_s *array);
double array_f_sum(const struct array_f_s *array);
void array_f_copy(const struct array_f_s *array, struct array_f_s *copy);
void array_f_link(const struct array_f_s *array, struct array_lf_s *link);
void array_f_swap(struct array_f_s *array, struct array_f_s *swap);
void array_f_head(const struct array_f_s *array, unsigned count,
                  struct array_f_s *head);
void array_f_tail(const struct array_f_s *array, unsigned count,
                  struct array_f_s *tail);
void array_f_de_head(const struct array_f_s *array, unsigned count,
                     struct array_f_s *tail);
void array_f_de_tail(const struct array_f_s *array, unsigned count,
                     struct array_f_s *head);
void array_f_split(const struct array_f_s *array, unsigned count,
                   struct array_f_s *head, struct array_f_s *tail);
void array_f_slice(const struct array_f_s *array,
                   unsigned start, unsigned end, unsigned jump,
                   struct array_f_s *slice);
void array_f_reverse(struct array_f_s *array);
void array_f_sort(struct array_f_s *array);
void array_f_print(const struct array_f_s *array, FILE* output);


/***************************************************************
 *                  linked floating point arrays               *
 ***************************************************************/

struct array_lf_s {
    double *data;
    unsigned size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_lf_s *array);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_lf_s *array,
                  const struct array_lf_s *compare);

    /*returns the smallest value in the array,
      or INT_MAX if the array is empty*/
    double (*min)(const struct array_lf_s *array);

    /*returns the largest value in the array,
      or INT_MIN if the array is empty*/
    double (*max)(const struct array_lf_s *array);

    /*returns the sum of all items in the array*/
    double (*sum)(const struct array_lf_s *array);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_lf_s *array, struct array_lf_s *swap);

    /*returns a new array with "count" number of items
      copied from the start of this array, or as many as possible*/
    void (*head)(const struct array_lf_s *array, unsigned count,
                 struct array_lf_s *head);

    /*returns a new array with "count" number of items
      copied from the end of this array, or as many as possible*/
    void (*tail)(const struct array_lf_s *array, unsigned count,
                 struct array_lf_s *tail);

    /*moves all except the first "count" number of items
      from this array to "tail", or as many as possible*/
    void (*de_head)(const struct array_lf_s *array, unsigned count,
                    struct array_lf_s *tail);

    /*moves all except the last "count" number of items
      from this array to "head", or as many as possible*/
    void (*de_tail)(const struct array_lf_s *array, unsigned count,
                    struct array_lf_s *head);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_lf_s *array, unsigned count,
                  struct array_lf_s *head, struct array_lf_s *tail);

    void (*print)(const struct array_lf_s *array, FILE* output);
};

typedef struct array_lf_s array_lf;

struct array_lf_s* array_lf_new(void);

void array_lf_del(struct array_lf_s *array);
int array_lf_equals(const struct array_lf_s *array,
                    const struct array_lf_s *compare);
double array_lf_min(const struct array_lf_s *array);
double array_lf_max(const struct array_lf_s *array);
double array_lf_sum(const struct array_lf_s *array);
void array_lf_swap(struct array_lf_s *array, struct array_lf_s *swap);
void array_lf_head(const struct array_lf_s *array, unsigned count,
                   struct array_lf_s *head);
void array_lf_tail(const struct array_lf_s *array, unsigned count,
                   struct array_lf_s *tail);
void array_lf_de_head(const struct array_lf_s *array, unsigned count,
                      struct array_lf_s *tail);
void array_lf_de_tail(const struct array_lf_s *array, unsigned count,
                      struct array_lf_s *head);
void array_lf_split(const struct array_lf_s *array, unsigned count,
                    struct array_lf_s *head, struct array_lf_s *tail);
void array_lf_print(const struct array_lf_s *array, FILE* output);



/***************************************************************
 *                    arrays of integer arrays                 *
 ***************************************************************/

struct array_ia_s {
    struct array_i_s **data;
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

    /*returns a freshly appended array_i which values can be added to
      this array should *not* be deleted once it is done being used*/
    struct array_i_s* (*append)(struct array_ia_s *array);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_ia_s *array, const struct array_ia_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_ia_s *array,
                  const struct array_ia_s *compare);

    /*reverses the items in the array*/
    void (*reverse)(struct array_ia_s *array);

    void (*print)(const struct array_ia_s *array, FILE* output);
};

typedef struct array_ia_s array_ia;

struct array_ia_s* array_ia_new(void);

void array_ia_del(struct array_ia_s *array);
void array_ia_resize(struct array_ia_s *array, unsigned minimum);
void array_ia_reset(struct array_ia_s *array);
struct array_i_s* array_ia_append(struct array_ia_s *array);
void array_ia_extend(struct array_ia_s *array, const struct array_ia_s *to_add);
int array_ia_equals(const struct array_ia_s *array,
                    const struct array_ia_s *compare);
void array_ia_reverse(struct array_ia_s *array);
void array_ia_print(const struct array_ia_s *array, FILE* output);


/***************************************************************
 *                     arrays of float arrays                  *
 ***************************************************************/

struct array_fa_s {
    struct array_f_s **data;
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

    /*returns a freshly appended array_f which values can be added to
      this array should *not* be deleted once it is done being used*/
    struct array_f_s* (*append)(struct array_fa_s *array);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_fa_s *array, const struct array_fa_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_fa_s *array,
                  const struct array_fa_s *compare);

    /*reverses the items in the array*/
    void (*reverse)(struct array_fa_s *array);

    void (*print)(const struct array_fa_s *array, FILE* output);
};

typedef struct array_fa_s array_fa;

struct array_fa_s* array_fa_new(void);

void array_fa_del(struct array_fa_s *array);
void array_fa_resize(struct array_fa_s *array, unsigned minimum);
void array_fa_reset(struct array_fa_s *array);
struct array_f_s* array_fa_append(struct array_fa_s *array);
void array_fa_extend(struct array_fa_s *array, const struct array_fa_s *to_add);
int array_fa_equals(const struct array_fa_s *array,
                    const struct array_fa_s *compare);
void array_fa_reverse(struct array_fa_s *array);
void array_fa_print(const struct array_fa_s *array, FILE* output);

#endif
