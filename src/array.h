#ifndef ARRAY2_H
#define ARRAY2_H

#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>

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

/*arrays are thin wrappers around malloc'ed data
  in order to provide a consistent interface for common array operations

  all have a "_" attribute to access the array's raw data,
  an unsigned "len" attribute for the array's current size
  and various methods to perform array-wise operations

  for example:

  int total = 0;
  array_i* a = array_i_new();    //initialize a new integer array
  a->vappend(a, 3, 1, 2, 3);     //append three integer values
  for (i = 0; i < a->len; i++) { //iterate over the array
      total += a->_[i];          //sum the values in the array
  }
  a->print(a, stdout);           //display the array
  a->del(a);                     //deallocate it once finished

  by providing internal methods with consistent naming,
  one doesn't have to remember different function names
  to perform the same function on arrays of different types
 */


/*appends a single value to the given array
  "array" is evaluated twice, while "value" is evaluated only once
  this presumes array has been resized in advance for additional items:

  array->reset(array);
  array->resize(array, count);
  for (i = 0; i < count; i++)
      a_append(array, data[i]);

  it works equally well for array_i and array_f
*/
#define a_append(array, value)((array)->_[(array)->len++] = (value))


/***************************************************************
 *                        integer arrays                       *
 *                     [1, 2, 3, 4, 5, ...]                    *
 ***************************************************************/

struct array_li_s;

struct array_i_s {
    int *_;
    unsigned len;
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

    /*appends "value", "count" number of times*/
    void (*mappend)(struct array_i_s *array, unsigned count, int value);

    /*sets the array to new values, removing any old ones*/
    void (*vset)(struct array_i_s *array, unsigned count, ...);

    /*sets the array to single values, removing any old ones*/
    void (*mset)(struct array_i_s *array, unsigned count, int value);

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

    /*makes "copy" a duplicate of this array*/
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
void array_i_mappend(struct array_i_s *array, unsigned count, int value);
void array_i_vset(struct array_i_s *array, unsigned count, ...);
void array_i_mset(struct array_i_s *array, unsigned count, int value);
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
 * the actual integer data is stored in a regular integer array*
 * which avoids needless copying in some read-only situations  *
 ***************************************************************/

struct array_li_s {
    const int *_;
    unsigned len;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_li_s *array);

    /*deletes any data in the array and resets its contents
      so that it can be linked to new data*/
    void (*reset)(struct array_li_s *array);

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

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_li_s *array, struct array_i_s *copy);

    /*links the contents of this array to a read-only array*/
    void (*link)(const struct array_li_s *array, struct array_li_s *link);

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
void array_li_reset(struct array_li_s *array);
int array_li_equals(const struct array_li_s *array,
                    const struct array_li_s *compare);
int array_li_min(const struct array_li_s *array);
int array_li_max(const struct array_li_s *array);
int array_li_sum(const struct array_li_s *array);
void array_li_copy(const struct array_li_s *array, struct array_i_s *copy);
void array_li_link(const struct array_li_s *array, struct array_li_s *link);
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
 *                 [1.0, 2.0, 3.0, 4.0, 5.0, ...]              *
 ***************************************************************/

struct array_lf_s;

struct array_f_s {
    double *_;
    unsigned len;
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

    /*appends "value", "count" number of times*/
    void (*mappend)(struct array_f_s *array, unsigned count, double value);

    /*sets the array to new values, removing any old ones*/
    void (*vset)(struct array_f_s *array, unsigned count, ...);

    /*sets the array to single values, removing any old ones*/
    void (*mset)(struct array_f_s *array, unsigned count, double value);

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

    /*makes "copy" a duplicate of this array*/
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
void array_f_mappend(struct array_f_s *array, unsigned count, double value);
void array_f_vset(struct array_f_s *array, unsigned count, ...);
void array_f_mset(struct array_f_s *array, unsigned count, double value);
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
 * the actual integer data is stored in a regular integer array*
 * which avoids needless copying in some read-only situations  *
 ***************************************************************/

struct array_lf_s {
    const double *_;
    unsigned len;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_lf_s *array);

    /*deletes any data in the array and resets its contents
      so that it can be linked to new data*/
    void (*reset)(struct array_lf_s *array);

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

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_lf_s *array, struct array_f_s *copy);

    /*links the contents of this array to a read-only array*/
    void (*link)(const struct array_lf_s *array, struct array_lf_s *link);

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
void array_lf_reset(struct array_lf_s *array);
int array_lf_equals(const struct array_lf_s *array,
                    const struct array_lf_s *compare);
double array_lf_min(const struct array_lf_s *array);
double array_lf_max(const struct array_lf_s *array);
double array_lf_sum(const struct array_lf_s *array);
void array_lf_copy(const struct array_lf_s *array, struct array_f_s *copy);
void array_lf_link(const struct array_lf_s *array, struct array_lf_s *link);
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
 *                   [[1, 2, 3], [4, 5, 6], ...]               *
 ***************************************************************/

struct array_ia_s {
    struct array_i_s **_;
    unsigned len;
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

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_ia_s *array, struct array_ia_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_ia_s *array, struct array_ia_s *swap);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_ia_s *array, unsigned count,
                  struct array_ia_s *head, struct array_ia_s *tail);

    /*splits each sub-array into "head" and "tail" arrays
      such that each "head" contains a copy of up to "count" items
      while each "tail" contains the rest*/
    void (*cross_split)(const struct array_ia_s *array, unsigned count,
                        struct array_ia_s *head, struct array_ia_s *tail);

    /*transposes rows and columns from array to zipped:
      [[1, 2, 3], [4, 5, 6] -> [[1, 4], [2, 5], [3, 6]]*/
    void (*zip)(const struct array_ia_s *array, struct array_ia_s *zipped);

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
void array_ia_copy(const struct array_ia_s *array, struct array_ia_s *copy);
void array_ia_swap(struct array_ia_s *array, struct array_ia_s *swap);
void array_ia_zip(const struct array_ia_s *array, struct array_ia_s *zipped);
void array_ia_reverse(struct array_ia_s *array);
void array_ia_split(const struct array_ia_s *array, unsigned count,
                    struct array_ia_s *head, struct array_ia_s *tail);
void array_ia_cross_split(const struct array_ia_s *array, unsigned count,
                          struct array_ia_s *head, struct array_ia_s *tail);
void array_ia_print(const struct array_ia_s *array, FILE* output);


/***************************************************************
 *                 arrays of linked integer arrays             *
 ***************************************************************/

struct array_lia_s {
    struct array_li_s **_;
    unsigned len;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_lia_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_lia_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_lia_s *array);

    /*returns a freshly appended array_li which can be linked to
      this array should *not* be deleted once it is done being used*/
    struct array_li_s* (*append)(struct array_lia_s *array);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_lia_s *array, const struct array_lia_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_lia_s *array,
                  const struct array_lia_s *compare);

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_lia_s *array, struct array_lia_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_lia_s *array, struct array_lia_s *swap);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_lia_s *array, unsigned count,
                  struct array_lia_s *head, struct array_lia_s *tail);

    /*splits each sub-array into "head" and "tail" arrays
      such that each "head" contains a copy of up to "count" items
      while each "tail" contains the rest*/
    void (*cross_split)(const struct array_lia_s *array, unsigned count,
                        struct array_lia_s *head, struct array_lia_s *tail);

    /*reverses the items in the array*/
    void (*reverse)(struct array_lia_s *array);

    void (*print)(const struct array_lia_s *array, FILE* output);
};

typedef struct array_lia_s array_lia;

struct array_lia_s* array_lia_new(void);

void array_lia_del(struct array_lia_s *array);
void array_lia_resize(struct array_lia_s *array, unsigned minimum);
void array_lia_reset(struct array_lia_s *array);
struct array_li_s* array_lia_append(struct array_lia_s *array);
void array_lia_extend(struct array_lia_s *array,
                      const struct array_lia_s *to_add);
int array_lia_equals(const struct array_lia_s *array,
                    const struct array_lia_s *compare);
void array_lia_copy(const struct array_lia_s *array, struct array_lia_s *copy);
void array_lia_swap(struct array_lia_s *array, struct array_lia_s *swap);
void array_lia_reverse(struct array_lia_s *array);
void array_lia_split(const struct array_lia_s *array, unsigned count,
                    struct array_lia_s *head, struct array_lia_s *tail);
void array_lia_cross_split(const struct array_lia_s *array, unsigned count,
                          struct array_lia_s *head, struct array_lia_s *tail);
void array_lia_print(const struct array_lia_s *array, FILE* output);


/***************************************************************
 *                     arrays of float arrays                  *
 *             [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], ...]         *
 ***************************************************************/

struct array_fa_s {
    struct array_f_s **_;
    unsigned len;
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

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_fa_s *array, struct array_fa_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_fa_s *array, struct array_fa_s *swap);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_fa_s *array, unsigned count,
                  struct array_fa_s *head, struct array_fa_s *tail);

    /*splits each sub-array into "head" and "tail" arrays
      such that each "head" contains a copy of up to "count" items
      while each "tail" contains the rest*/
    void (*cross_split)(const struct array_fa_s *array, unsigned count,
                        struct array_fa_s *head, struct array_fa_s *tail);

    /*transposes rows and columns from array to zipped:
      [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0] ->
      [[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]*/
    void (*zip)(const struct array_fa_s *array, struct array_fa_s *zipped);

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
void array_fa_copy(const struct array_fa_s *array, struct array_fa_s *copy);
void array_fa_swap(struct array_fa_s *array, struct array_fa_s *swap);
void array_fa_reverse(struct array_fa_s *array);
void array_fa_split(const struct array_fa_s *array, unsigned count,
                    struct array_fa_s *head, struct array_fa_s *tail);
void array_fa_cross_split(const struct array_fa_s *array, unsigned count,
                          struct array_fa_s *head, struct array_fa_s *tail);
void array_fa_zip(const struct array_fa_s *array, struct array_fa_s *zipped);
void array_fa_print(const struct array_fa_s *array, FILE* output);


/***************************************************************
 *              arrays of linked floating point arrays         *
 ***************************************************************/

struct array_lfa_s {
    struct array_lf_s **_;
    unsigned len;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_lfa_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_lfa_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_lfa_s *array);

    /*returns a freshly appended array_li which can be linked to
      this array should *not* be deleted once it is done being used*/
    struct array_lf_s* (*append)(struct array_lfa_s *array);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_lfa_s *array, const struct array_lfa_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_lfa_s *array,
                  const struct array_lfa_s *compare);

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_lfa_s *array, struct array_lfa_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_lfa_s *array, struct array_lfa_s *swap);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_lfa_s *array, unsigned count,
                  struct array_lfa_s *head, struct array_lfa_s *tail);

    /*splits each sub-array into "head" and "tail" arrays
      such that each "head" contains a copy of up to "count" items
      while each "tail" contains the rest*/
    void (*cross_split)(const struct array_lfa_s *array, unsigned count,
                        struct array_lfa_s *head, struct array_lfa_s *tail);

    /*reverses the items in the array*/
    void (*reverse)(struct array_lfa_s *array);

    void (*print)(const struct array_lfa_s *array, FILE* output);
};

typedef struct array_lfa_s array_lfa;

struct array_lfa_s* array_lfa_new(void);

void array_lfa_del(struct array_lfa_s *array);
void array_lfa_resize(struct array_lfa_s *array, unsigned minimum);
void array_lfa_reset(struct array_lfa_s *array);
struct array_lf_s* array_lfa_append(struct array_lfa_s *array);
void array_lfa_extend(struct array_lfa_s *array,
                      const struct array_lfa_s *to_add);
int array_lfa_equals(const struct array_lfa_s *array,
                     const struct array_lfa_s *compare);
void array_lfa_copy(const struct array_lfa_s *array, struct array_lfa_s *copy);
void array_lfa_swap(struct array_lfa_s *array, struct array_lfa_s *swap);
void array_lfa_reverse(struct array_lfa_s *array);
void array_lfa_split(const struct array_lfa_s *array, unsigned count,
                     struct array_lfa_s *head, struct array_lfa_s *tail);
void array_lfa_cross_split(const struct array_lfa_s *array, unsigned count,
                           struct array_lfa_s *head, struct array_lfa_s *tail);
void array_lfa_print(const struct array_lfa_s *array, FILE* output);



/***************************************************************
 *             arrays of arrays of integer arrays              *
 *  [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]], ...]   *
 ***************************************************************/

struct array_iaa_s {
    struct array_ia_s **_;
    unsigned len;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_iaa_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_iaa_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_iaa_s *array);

    /*returns a freshly appended array_i which values can be added to
      this array should *not* be deleted once it is done being used*/
    struct array_ia_s* (*append)(struct array_iaa_s *array);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_iaa_s *array, const struct array_iaa_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_iaa_s *array,
                  const struct array_iaa_s *compare);

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_iaa_s *array, struct array_iaa_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_iaa_s *array, struct array_iaa_s *swap);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_iaa_s *array, unsigned count,
                  struct array_iaa_s *head, struct array_iaa_s *tail);

    /*reverses the items in the array*/
    void (*reverse)(struct array_iaa_s *array);

    void (*print)(const struct array_iaa_s *array, FILE* output);
};

typedef struct array_iaa_s array_iaa;

struct array_iaa_s* array_iaa_new(void);

void array_iaa_del(struct array_iaa_s *array);
void array_iaa_resize(struct array_iaa_s *array, unsigned minimum);
void array_iaa_reset(struct array_iaa_s *array);
struct array_ia_s* array_iaa_append(struct array_iaa_s *array);
void array_iaa_extend(struct array_iaa_s *array,
                     const struct array_iaa_s *to_add);
int array_iaa_equals(const struct array_iaa_s *array,
                    const struct array_iaa_s *compare);
void array_iaa_copy(const struct array_iaa_s *array, struct array_iaa_s *copy);
void array_iaa_swap(struct array_iaa_s *array, struct array_iaa_s *swap);
void array_iaa_reverse(struct array_iaa_s *array);
void array_iaa_split(const struct array_iaa_s *array, unsigned count,
                    struct array_iaa_s *head, struct array_iaa_s *tail);
void array_iaa_print(const struct array_iaa_s *array, FILE* output);


/***************************************************************
 *              arrays of arrays of float arrays               *
 *      [[[1.0, 2.0], [3.0]], [[7.0, 8.0], [9.0]], ...]        *
 ***************************************************************/

struct array_faa_s {
    struct array_fa_s **_;
    unsigned len;
    unsigned total_size;

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_faa_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_faa_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_faa_s *array);

    /*returns a freshly appended array_i which values can be added to
      this array should *not* be deleted once it is done being used*/
    struct array_fa_s* (*append)(struct array_faa_s *array);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_faa_s *array, const struct array_faa_s *to_add);

    /*returns 1 if all items in array equal those in compare,
      returns 0 if not*/
    int (*equals)(const struct array_faa_s *array,
                  const struct array_faa_s *compare);

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_faa_s *array, struct array_faa_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_faa_s *array, struct array_faa_s *swap);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_faa_s *array, unsigned count,
                  struct array_faa_s *head, struct array_faa_s *tail);

    /*reverses the items in the array*/
    void (*reverse)(struct array_faa_s *array);

    void (*print)(const struct array_faa_s *array, FILE* output);
};

typedef struct array_faa_s array_faa;

struct array_faa_s* array_faa_new(void);

void array_faa_del(struct array_faa_s *array);
void array_faa_resize(struct array_faa_s *array, unsigned minimum);
void array_faa_reset(struct array_faa_s *array);
struct array_fa_s* array_faa_append(struct array_faa_s *array);
void array_faa_extend(struct array_faa_s *array,
                     const struct array_faa_s *to_add);
int array_faa_equals(const struct array_faa_s *array,
                    const struct array_faa_s *compare);
void array_faa_copy(const struct array_faa_s *array, struct array_faa_s *copy);
void array_faa_swap(struct array_faa_s *array, struct array_faa_s *swap);
void array_faa_reverse(struct array_faa_s *array);
void array_faa_split(const struct array_faa_s *array, unsigned count,
                    struct array_faa_s *head, struct array_faa_s *tail);
void array_faa_print(const struct array_faa_s *array, FILE* output);


/***************************************************************
 *                        object arrays                        *
 *                  [ptr1*, ptr2*, ptr3*, ...]                 *
 ***************************************************************/

struct array_o_s {
    void **_;
    unsigned len;
    unsigned total_size;

    /*called when an object is duplicated between arrays*/
    void* (*copy_obj)(void* obj);

    /*called when an object is removed from the array
      may be NULL, meaning no free is performed*/
    void (*free_obj)(void* obj);

    /*called by the a->print(a, FILE) method to display an object
      may be NULL, meaning some default is printed*/
    void (*print_obj)(void* obj, FILE* output);

    /*deletes the array and any allocated data it contains*/
    void (*del)(struct array_o_s *array);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct array_o_s *array, unsigned minimum);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_o_s *array);

    /*appends a single value to the array*/
    void (*append)(struct array_o_s *array, void* value);

    /*appends several values to the array*/
    void (*vappend)(struct array_o_s *array, unsigned count, ...);

    /*appends "value", "count" number of times*/
    void (*mappend)(struct array_o_s *array, unsigned count, void* value);

    /*deletes the item at the given index
      and sets it to the new value*/
    void (*set)(struct array_o_s *array, unsigned index, void* value);

    /*sets the array to new values, removing any old ones*/
    void (*vset)(struct array_o_s *array, unsigned count, ...);

    /*sets the array to single values, removing any old ones*/
    void (*mset)(struct array_o_s *array, unsigned count, void* value);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct array_o_s *array, const struct array_o_s *to_add);

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct array_o_s *array, struct array_o_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct array_o_s *array, struct array_o_s *swap);

    /*moves "count" number of items from the start of this array
      to "head", or as many as possible*/
    void (*head)(const struct array_o_s *array, unsigned count,
                 struct array_o_s *head);

    /*moves "count" number of items from the end of this array
      to "tail", or as many as possible*/
    void (*tail)(const struct array_o_s *array, unsigned count,
                 struct array_o_s *tail);

    /*moves all except the first "count" number of items
      from this array to "tail", or as many as possible*/
    void (*de_head)(const struct array_o_s *array, unsigned count,
                    struct array_o_s *tail);

    /*moves all except the last "count" number of items
      from this array to "head", or as many as possible*/
    void (*de_tail)(const struct array_o_s *array, unsigned count,
                    struct array_o_s *head);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct array_o_s *array, unsigned count,
                  struct array_o_s *head, struct array_o_s *tail);

    void (*print)(const struct array_o_s *array, FILE* output);
};

typedef struct array_o_s array_o;

typedef void* (*ARRAY_COPY_FUNC)(void* obj);
typedef void (*ARRAY_FREE_FUNC)(void* obj);
typedef void (*ARRAY_PRINT_FUNC)(void* obj, FILE* output);

/*copy, free and print functions may be NULL,
  indicating no copy, free or print operations are necessary for object*/
struct array_o_s* array_o_new(void* (*copy)(void* obj),
                              void (*free)(void* obj),
                              void (*print)(void* obj, FILE* output));
void array_o_del(struct array_o_s *array);
void array_o_resize(struct array_o_s *array, unsigned minimum);
void array_o_reset(struct array_o_s *array);
void array_o_append(struct array_o_s *array, void* value);
void array_o_vappend(struct array_o_s *array, unsigned count, ...);
void array_o_mappend(struct array_o_s *array, unsigned count, void* value);
void array_o_set(struct array_o_s *array, unsigned index, void* value);
void array_o_vset(struct array_o_s *array, unsigned count, ...);
void array_o_mset(struct array_o_s *array, unsigned count, void* value);
void array_o_extend(struct array_o_s *array, const struct array_o_s *to_add);
void array_o_copy(const struct array_o_s *array, struct array_o_s *copy);
void array_o_swap(struct array_o_s *array, struct array_o_s *swap);
void array_o_head(const struct array_o_s *array, unsigned count,
                  struct array_o_s *head);
void array_o_tail(const struct array_o_s *array, unsigned count,
                  struct array_o_s *tail);
void array_o_de_head(const struct array_o_s *array, unsigned count,
                     struct array_o_s *tail);
void array_o_de_tail(const struct array_o_s *array, unsigned count,
                     struct array_o_s *head);
void array_o_split(const struct array_o_s *array, unsigned count,
                   struct array_o_s *head, struct array_o_s *tail);
void array_o_print(const struct array_o_s *array, FILE* output);

#endif
