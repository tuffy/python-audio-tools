#ifndef ARRAY2_H
#define ARRAY2_H

#include <stdarg.h>
#include <stdio.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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

  array->reset_for(array, count);
  for (i = 0; i < count; i++)
      a_append(array, data[i]);

  it works equally well for array_i and array_f
*/
#define a_append(array, value)((array)->_[(array)->len++] = (value))


/******************************************************************/
/*arrays of plain C primitives such as int, double, unsigned, etc.*/
/******************************************************************/

#define ARRAY_TYPE_DEFINITION(TYPE, CONTENT_TYPE, LINK_TYPE)   \
struct LINK_TYPE##_s;                                          \
struct TYPE##_s {                                              \
    CONTENT_TYPE *_;                                           \
    unsigned len;                                              \
    unsigned total_size;                                       \
                                                                \
    /*deletes the array and any allocated data it contains*/    \
    void (*del)(struct TYPE##_s *array);                        \
                                                                \
    /*resizes the array to fit at least "minimum" items*/       \
    void (*resize)(struct TYPE##_s *array, unsigned minimum);   \
                                                                \
    /*resizes the array to fit "additional_items"*/             \
    void (*resize_for)(struct TYPE##_s *array,                  \
                       unsigned additional_items);              \
                                                                \
    /*deletes any data in the array and resets its contents*/   \
    /*so that it can be re-populated with new data*/            \
    void (*reset)(struct TYPE##_s *array);                      \
                                                                \
    /*deletes any data in the array,*/                          \
    /*resizes its contents to fit "minimum" number of items,*/  \
    /*and resets it contents so it can be re-populated*/        \
    void (*reset_for)(struct TYPE##_s *array,                   \
                      unsigned minimum);                        \
                                                                \
    /*appends a single value to the array*/                     \
    void (*append)(struct TYPE##_s *array, CONTENT_TYPE value); \
                                                                \
    /*appends several values to the array*/                     \
    void (*vappend)(struct TYPE##_s *array, unsigned count, ...);   \
                                                                    \
    /*appends "value", "count" number of times*/                        \
    void (*mappend)(struct TYPE##_s *array, unsigned count,             \
                    CONTENT_TYPE value);                                \
                                                                        \
    /*sets the array to new values, removing any old ones*/             \
    void (*vset)(struct TYPE##_s *array, unsigned count, ...);          \
                                                                        \
    /*sets the array to single values, removing any old ones*/          \
    void (*mset)(struct TYPE##_s *array, unsigned count,                \
                 CONTENT_TYPE value);                                   \
                                                                        \
    /*appends all the items in "to_add" to this array*/                 \
    void (*extend)(struct TYPE##_s *array,                              \
                   const struct TYPE##_s *to_add);                      \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct TYPE##_s *array,                         \
                  const struct TYPE##_s *compare);                      \
                                                                        \
    /*returns the smallest value in the array,*/                        \
    /*or INT_MAX if the array is empty*/                                \
    CONTENT_TYPE (*min)(const struct TYPE##_s *array);                  \
                                                                        \
    /*returns the largest value in the array,*/                         \
    /*or INT_MIN if the array is empty*/                                \
    CONTENT_TYPE (*max)(const struct TYPE##_s *array);                  \
                                                                        \
    /*returns the sum of all items in the array*/                       \
    CONTENT_TYPE (*sum)(const struct TYPE##_s *array);                  \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct TYPE##_s *array,                          \
                 struct TYPE##_s *copy);                                \
                                                                        \
    /*links the contents of this array to a read-only array*/           \
    void (*link)(const struct TYPE##_s *array,                          \
                 struct LINK_TYPE##_s *link);                           \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct TYPE##_s *array, struct TYPE##_s *swap);        \
                                                                        \
    /*moves "count" number of items from the start of this array*/      \
    /*to "head", or as many as possible*/                               \
    void (*head)(const struct TYPE##_s *array, unsigned count,          \
                 struct TYPE##_s *head);                                \
                                                                        \
    /*moves "count" number of items from the end of this array*/        \
    /*to "tail", or as many as possible*/                               \
    void (*tail)(const struct TYPE##_s *array, unsigned count,          \
                 struct TYPE##_s *tail);                                \
                                                                        \
    /*moves all except the first "count" number of items*/              \
    /*from this array to "tail", or as many as possible*/               \
    void (*de_head)(const struct TYPE##_s *array, unsigned count,       \
                    struct TYPE##_s *tail);                             \
                                                                        \
    /*moves all except the last "count" number of items*/               \
    /*from this array to "head", or as many as possible*/               \
    void (*de_tail)(const struct TYPE##_s *array, unsigned count,       \
                    struct TYPE##_s *head);                             \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct TYPE##_s *array, unsigned count,         \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
                                                                        \
    /*reverses the items in the array*/                                 \
    void (*reverse)(struct TYPE##_s *array);                            \
                                                                        \
    /*sorts the items in the array*/                                    \
    void (*sort)(struct TYPE##_s *array);                               \
                                                                        \
    void (*print)(const struct TYPE##_s *array, FILE* output);          \
};                                                                      \
typedef struct TYPE##_s TYPE;                                           \
struct TYPE##_s* TYPE##_new(void);                                      \
void TYPE##_del(struct TYPE##_s *array);                                \
void TYPE##_resize(struct TYPE##_s *array, unsigned minimum);           \
void TYPE##_resize_for(struct TYPE##_s *array, unsigned additional_items); \
void TYPE##_reset(struct TYPE##_s *array);                              \
void TYPE##_reset_for(struct TYPE##_s *array, unsigned minimum);        \
void TYPE##_append(struct TYPE##_s *array, CONTENT_TYPE value);         \
void TYPE##_vappend(struct TYPE##_s *array, unsigned count, ...);       \
void TYPE##_mappend(struct TYPE##_s *array, unsigned count,             \
                    CONTENT_TYPE value);                                \
void TYPE##_vset(struct TYPE##_s *array, unsigned count, ...);          \
void TYPE##_mset(struct TYPE##_s *array, unsigned count,                \
                 CONTENT_TYPE value);                                   \
void TYPE##_extend(struct TYPE##_s *array,                              \
                   const struct TYPE##_s *to_add);                      \
int TYPE##_equals(const struct TYPE##_s *array,                         \
                  const struct TYPE##_s *compare);                      \
CONTENT_TYPE TYPE##_min(const struct TYPE##_s *array);                  \
CONTENT_TYPE TYPE##_max(const struct TYPE##_s *array);                  \
CONTENT_TYPE TYPE##_sum(const struct TYPE##_s *array);                  \
void TYPE##_copy(const struct TYPE##_s *array, struct TYPE##_s *copy);  \
void TYPE##_link(const struct TYPE##_s *array,                          \
                 struct LINK_TYPE##_s *link);                           \
void TYPE##_swap(struct TYPE##_s *array, struct TYPE##_s *swap);        \
void TYPE##_head(const struct TYPE##_s *array, unsigned count,          \
                  struct TYPE##_s *head);                               \
void TYPE##_tail(const struct TYPE##_s *array, unsigned count,          \
                 struct TYPE##_s *tail);                                \
void TYPE##_de_head(const struct TYPE##_s *array, unsigned count,       \
                    struct TYPE##_s *tail);                             \
void TYPE##_de_tail(const struct TYPE##_s *array, unsigned count,       \
                    struct TYPE##_s *head);                             \
void TYPE##_split(const struct TYPE##_s *array, unsigned count,         \
                   struct TYPE##_s *head, struct TYPE##_s *tail);       \
void TYPE##_reverse(struct TYPE##_s *array);                            \
void TYPE##_sort(struct TYPE##_s *array);                               \
void TYPE##_print(const struct TYPE##_s *array, FILE* output);          \
                                                                        \
struct LINK_TYPE##_s {                                                  \
    const CONTENT_TYPE *_;                                              \
    unsigned len;                                                       \
                                                                        \
    /*deletes the array and any allocated data it contains*/            \
    void (*del)(struct LINK_TYPE##_s *array);                           \
                                                                        \
    /*deletes any data in the array and resets its contents*/           \
    /*so that it can be linked to new data*/                            \
    void (*reset)(struct LINK_TYPE##_s *array);                         \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct LINK_TYPE##_s *array,                    \
                  const struct LINK_TYPE##_s *compare);                 \
                                                                        \
    /*returns the smallest value in the array,*/                        \
    CONTENT_TYPE (*min)(const struct LINK_TYPE##_s *array);             \
                                                                        \
    /*returns the largest value in the array,*/                         \
    CONTENT_TYPE (*max)(const struct LINK_TYPE##_s *array);             \
                                                                        \
    /*returns the sum of all items in the array*/                       \
    CONTENT_TYPE (*sum)(const struct LINK_TYPE##_s *array);             \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct LINK_TYPE##_s *array,                     \
                 struct TYPE##_s *copy);                                \
                                                                        \
    /*links the contents of this array to a read-only array*/           \
    void (*link)(const struct LINK_TYPE##_s *array,                     \
                 struct LINK_TYPE##_s *link);                           \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct LINK_TYPE##_s *array,                           \
                 struct LINK_TYPE##_s *swap);                           \
                                                                        \
    /*moves "count" number of items from the start of this array*/      \
    /*to "head", or as many as possible*/                               \
    void (*head)(const struct LINK_TYPE##_s *array, unsigned count,     \
                 struct LINK_TYPE##_s *head);                           \
                                                                        \
    /*moves "count" number of items from the start of this array*/      \
    /*to "head", or as many as possible*/                               \
    void (*tail)(const struct LINK_TYPE##_s *array, unsigned count,     \
                 struct LINK_TYPE##_s *tail);                           \
                                                                        \
    /*moves all except the first "count" number of items*/              \
    /*from this array to "tail", or as many as possible*/               \
    void (*de_head)(const struct LINK_TYPE##_s *array, unsigned count,  \
                    struct LINK_TYPE##_s *tail);                        \
                                                                        \
    /*moves all except the last "count" number of items*/               \
    /*from this array to "head", or as many as possible*/               \
    void (*de_tail)(const struct LINK_TYPE##_s *array, unsigned count,  \
                    struct LINK_TYPE##_s *head);                        \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct LINK_TYPE##_s *array, unsigned count,    \
                  struct LINK_TYPE##_s *head, struct LINK_TYPE##_s *tail); \
                                                                        \
    void (*print)(const struct LINK_TYPE##_s *array, FILE* output);     \
};                                                                      \
typedef struct LINK_TYPE##_s LINK_TYPE;                                 \
struct LINK_TYPE##_s* LINK_TYPE##_new(void);                            \
void LINK_TYPE##_del(struct LINK_TYPE##_s *array);                      \
void LINK_TYPE##_reset(struct LINK_TYPE##_s *array);                    \
int LINK_TYPE##_equals(const struct LINK_TYPE##_s *array,               \
                       const struct LINK_TYPE##_s *compare);            \
CONTENT_TYPE LINK_TYPE##_min(const struct LINK_TYPE##_s *array);        \
CONTENT_TYPE LINK_TYPE##_max(const struct LINK_TYPE##_s *array);        \
CONTENT_TYPE LINK_TYPE##_sum(const struct LINK_TYPE##_s *array);        \
void LINK_TYPE##_copy(const struct LINK_TYPE##_s *array,                \
                      struct TYPE##_s *copy);                           \
void LINK_TYPE##_link(const struct LINK_TYPE##_s *array,                \
                      struct LINK_TYPE##_s *link);                      \
void LINK_TYPE##_swap(struct LINK_TYPE##_s *array,                      \
                      struct LINK_TYPE##_s *swap);                      \
void LINK_TYPE##_head(const struct LINK_TYPE##_s *array, unsigned count, \
                      struct LINK_TYPE##_s *head);                      \
void LINK_TYPE##_tail(const struct LINK_TYPE##_s *array, unsigned count, \
                      struct LINK_TYPE##_s *tail);                      \
void LINK_TYPE##_de_head(const struct LINK_TYPE##_s *array, unsigned count, \
                         struct LINK_TYPE##_s *tail);                   \
void LINK_TYPE##_de_tail(const struct LINK_TYPE##_s *array, unsigned count, \
                         struct LINK_TYPE##_s *head);                   \
void LINK_TYPE##_split(const struct LINK_TYPE##_s *array,               \
                       unsigned count,                                  \
                       struct LINK_TYPE##_s *head,                      \
                       struct LINK_TYPE##_s *tail);                     \
void LINK_TYPE##_print(const struct LINK_TYPE##_s *array, FILE* output);

ARRAY_TYPE_DEFINITION(array_i, int, array_li)
ARRAY_TYPE_DEFINITION(array_f, double, array_lf)
ARRAY_TYPE_DEFINITION(array_u, unsigned, array_lu)


/******************************************************************/
/*        arrays of arrays such as array_i, array_f, etc.         */
/******************************************************************/

#define ARRAY_A_TYPE_DEFINITION(TYPE, ARRAY_TYPE)               \
struct TYPE##_s {                                               \
    struct ARRAY_TYPE##_s **_;                                  \
    unsigned len;                                               \
    unsigned total_size;                                        \
                                                                \
    /*deletes the array and any allocated data it contains*/    \
    void (*del)(struct TYPE##_s *array);                        \
                                                                \
    /*resizes the array to fit at least "minimum" items*/       \
    void (*resize)(struct TYPE##_s *array, unsigned minimum);   \
                                                                \
    /*deletes any data in the array and resets its contents*/   \
    /*so that it can be re-populated with new data*/            \
    void (*reset)(struct TYPE##_s *array);                      \
                                                                        \
    /*returns a freshly appended array which values can be added to*/   \
    /*this array should *not* be deleted once it is done being used*/   \
    struct ARRAY_TYPE##_s* (*append)(struct TYPE##_s *array);           \
                                                                        \
    /*appends all the items in "to_add" to this array*/                 \
    void (*extend)(struct TYPE##_s *array,                              \
                   const struct TYPE##_s *to_add);                      \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct TYPE##_s *array,                         \
                  const struct TYPE##_s *compare);                      \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct TYPE##_s *array, struct TYPE##_s *copy);  \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct TYPE##_s *array, struct TYPE##_s *swap);        \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct TYPE##_s *array, unsigned count,         \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
                                                                        \
    /*splits each sub-array into "head" and "tail" arrays*/             \
    /*such that each "head" contains a copy of up to "count" items*/    \
    /*while each "tail" contains the rest*/                             \
    void (*cross_split)(const struct TYPE##_s *array, unsigned count,   \
                        struct TYPE##_s *head, struct TYPE##_s *tail);  \
                                                                        \
    /*reverses the items in the array*/                                 \
    void (*reverse)(struct TYPE##_s *array);                            \
                                                                        \
    void (*print)(const struct TYPE##_s *array, FILE* output);          \
};                                                                      \
typedef struct TYPE##_s TYPE;                                           \
struct TYPE##_s* TYPE##_new(void);                                      \
void TYPE##_del(struct TYPE##_s *array);                                \
void TYPE##_resize(struct TYPE##_s *array, unsigned minimum);           \
void TYPE##_reset(struct TYPE##_s *array);                              \
struct ARRAY_TYPE##_s* TYPE##_append(struct TYPE##_s *array);           \
void TYPE##_extend(struct TYPE##_s *array,                              \
                   const struct TYPE##_s *to_add);                      \
int TYPE##_equals(const struct TYPE##_s *array,                         \
                  const struct TYPE##_s *compare);                      \
void TYPE##_copy(const struct TYPE##_s *array, struct TYPE##_s *copy);  \
void TYPE##_swap(struct TYPE##_s *array, struct TYPE##_s *swap);        \
void TYPE##_reverse(struct TYPE##_s *array);                            \
void TYPE##_split(const struct TYPE##_s *array, unsigned count,         \
                    struct TYPE##_s *head, struct TYPE##_s *tail);      \
void TYPE##_cross_split(const struct TYPE##_s *array, unsigned count,   \
                          struct TYPE##_s *head, struct TYPE##_s *tail); \
void TYPE##_print(const struct TYPE##_s *array, FILE* output);

ARRAY_A_TYPE_DEFINITION(array_ia, array_i)
ARRAY_A_TYPE_DEFINITION(array_fa, array_f)
ARRAY_A_TYPE_DEFINITION(array_lia, array_li)
ARRAY_A_TYPE_DEFINITION(array_lfa, array_lf)

/******************************************************************/
/*   arrays of arrays of arraysuch as array_ia, array_fa, etc.    */
/******************************************************************/

#define ARRAY_AA_TYPE_DEFINITION(TYPE, ARRAY_TYPE)  \
struct TYPE##_s {                                   \
    struct ARRAY_TYPE##_s **_;                      \
    unsigned len;                                   \
    unsigned total_size;                            \
                                                                \
    /*deletes the array and any allocated data it contains*/    \
    void (*del)(struct TYPE##_s *array);                        \
                                                                \
    /*resizes the array to fit at least "minimum" items*/       \
    void (*resize)(struct TYPE##_s *array, unsigned minimum);   \
                                                                \
    /*deletes any data in the array and resets its contents*/   \
    /*so that it can be re-populated with new data*/            \
    void (*reset)(struct TYPE##_s *array);                      \
                                                                        \
    /*returns a freshly appended array_i which values can be added to*/ \
    /*this array should *not* be deleted once it is done being used*/   \
    struct ARRAY_TYPE##_s* (*append)(struct TYPE##_s *array);           \
                                                                        \
    /*appends all the items in "to_add" to this array*/                 \
    void (*extend)(struct TYPE##_s *array,                              \
                   const struct TYPE##_s *to_add);                      \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct TYPE##_s *array,                         \
                  const struct TYPE##_s *compare);                      \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct TYPE##_s *array,                          \
                 struct TYPE##_s *copy);                                \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct TYPE##_s *array, struct TYPE##_s *swap);        \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct TYPE##_s *array, unsigned count,         \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
                                                                        \
    /*reverses the items in the array*/                                 \
    void (*reverse)(struct TYPE##_s *array);                            \
                                                                        \
    void (*print)(const struct TYPE##_s *array, FILE* output);          \
};                                                                      \
typedef struct TYPE##_s TYPE;                                           \
struct TYPE##_s* TYPE##_new(void);                                      \
void TYPE##_del(struct TYPE##_s *array);                                \
void TYPE##_resize(struct TYPE##_s *array, unsigned minimum);           \
void TYPE##_reset(struct TYPE##_s *array);                              \
struct ARRAY_TYPE##_s* TYPE##_append(struct TYPE##_s *array);           \
void TYPE##_extend(struct TYPE##_s *array,                              \
                   const struct TYPE##_s *to_add);                      \
int TYPE##_equals(const struct TYPE##_s *array,                         \
                  const struct TYPE##_s *compare);                      \
void TYPE##_copy(const struct TYPE##_s *array,                          \
                 struct TYPE##_s *copy);                                \
void TYPE##_swap(struct TYPE##_s *array, struct TYPE##_s *swap);        \
void TYPE##_reverse(struct TYPE##_s *array);                            \
void TYPE##_split(const struct TYPE##_s *array, unsigned count,         \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
void TYPE##_print(const struct TYPE##_s *array, FILE* output);

ARRAY_AA_TYPE_DEFINITION(array_iaa, array_ia)
ARRAY_AA_TYPE_DEFINITION(array_faa, array_fa)

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

    /*resizes the array to fit "additional_items" number of new items,
      if necessary*/
    void (*resize_for)(struct array_o_s *array, unsigned additional_items);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct array_o_s *array);

    /*deletes any data in the array,
      resizes its contents to fit "minimum" number of items,
      and resets it contents so it can be re-populated with new data*/
    void (*reset_for)(struct array_o_s *array, unsigned minimum);

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

/*some placeholder functions for array_o objects*/
void*
array_o_dummy_copy(void* obj);
void
array_o_dummy_free(void* obj);
void
array_o_dummy_print(void* obj, FILE* output);

/*copy, free and print functions may be NULL,
  indicating no copy, free or print operations are necessary for object*/
struct array_o_s* array_o_new(void* (*copy)(void* obj),
                              void (*free)(void* obj),
                              void (*print)(void* obj, FILE* output));
void array_o_del(struct array_o_s *array);
void array_o_resize(struct array_o_s *array, unsigned minimum);
void array_o_resize_for(struct array_o_s *array, unsigned additional_items);
void array_o_reset(struct array_o_s *array);
void array_o_reset_for(struct array_o_s *array, unsigned minimum);
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
