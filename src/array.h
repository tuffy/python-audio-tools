/********************************************************
 Array Library, a simple module for handling arrays of data

 Copyright (C) 2007-2014  Brian Langenberger

 The Array Library is free software; you can redistribute it and/or modify
 it under the terms of either:

   * the GNU Lesser General Public License as published by the Free
     Software Foundation; either version 3 of the License, or (at your
     option) any later version.

 or

   * the GNU General Public License as published by the Free Software
     Foundation; either version 2 of the License, or (at your option) any
     later version.

 or both in parallel, as here.

 The Array Library is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 for more details.

 You should have received copies of the GNU General Public License and the
 GNU Lesser General Public License along with the GNU MP Library.  If not,
 see https://www.gnu.org/licenses/.
 *******************************************************/

#ifndef __ARRAYLIB_H__
#define __ARRAYLIB_H__

#include <stdarg.h>
#include <stdio.h>

/*arrays are thin wrappers around malloc'ed data
  in order to provide a consistent interface for common array operations

  all have a "_" attribute to access the array's raw data,
  an unsigned "len" attribute for the array's current size
  and various methods to perform array-wise operations

  for example:

  int total = 0;
  a_int* a = a_int_new();        //initialize a new integer array
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

#define ARRAY_TYPE_DEFINITION(TYPE, CONTENT_TYPE, LINK_TYPE)            \
struct LINK_TYPE##_s;                                                   \
struct TYPE##_s {                                                       \
    CONTENT_TYPE *_;                                                    \
    unsigned len;                                                       \
    unsigned total_size;                                                \
                                                                        \
    /*deletes the array and any allocated data it contains*/            \
    void (*del)(struct TYPE##_s *self);                                 \
                                                                        \
    /*resizes the array to fit at least "minimum" items*/               \
    void (*resize)(struct TYPE##_s *self, unsigned minimum);            \
                                                                        \
    /*resizes the array to fit "additional_items"*/                     \
    void (*resize_for)(struct TYPE##_s *self,                           \
                       unsigned additional_items);                      \
                                                                        \
    /*deletes any data in the array and resets its contents*/           \
    /*so that it can be re-populated with new data*/                    \
    void (*reset)(struct TYPE##_s *self);                               \
                                                                        \
    /*deletes any data in the array,*/                                  \
    /*resizes its contents to fit "minimum" number of items,*/          \
    /*and resets it contents so it can be re-populated*/                \
    void (*reset_for)(struct TYPE##_s *self,                            \
                      unsigned minimum);                                \
                                                                        \
    /*appends a single value to the array*/                             \
    void (*append)(struct TYPE##_s *self, CONTENT_TYPE value);          \
                                                                        \
    /*appends several values to the array*/                             \
    void (*vappend)(struct TYPE##_s *self, unsigned count, ...);        \
                                                                        \
    /*appends "value", "count" number of times*/                        \
    void (*mappend)(struct TYPE##_s *self, unsigned count,              \
                    CONTENT_TYPE value);                                \
                                                                        \
    void (*insert)(struct TYPE##_s *self, unsigned index,               \
                   CONTENT_TYPE value);                                 \
                                                                        \
    /*sets the array to new values, removing any old ones*/             \
    void (*vset)(struct TYPE##_s *self, unsigned count, ...);           \
                                                                        \
    /*sets the array to single values, removing any old ones*/          \
    void (*mset)(struct TYPE##_s *self, unsigned count,                 \
                 CONTENT_TYPE value);                                   \
                                                                        \
    /*appends all the items in "to_add" to this array*/                 \
    void (*extend)(struct TYPE##_s *self,                               \
                   const struct TYPE##_s *to_add);                      \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct TYPE##_s *self,                          \
                  const struct TYPE##_s *compare);                      \
                                                                        \
    /*returns the smallest value in the array,*/                        \
    /*or INT_MAX if the array is empty*/                                \
    CONTENT_TYPE (*min)(const struct TYPE##_s *self);                   \
                                                                        \
    /*returns the largest value in the array,*/                         \
    /*or INT_MIN if the array is empty*/                                \
    CONTENT_TYPE (*max)(const struct TYPE##_s *self);                   \
                                                                        \
    /*returns the sum of all items in the array*/                       \
    CONTENT_TYPE (*sum)(const struct TYPE##_s *self);                   \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct TYPE##_s *self,                           \
                 struct TYPE##_s *copy);                                \
                                                                        \
    /*links the contents of this array to a read-only array*/           \
    void (*link)(const struct TYPE##_s *self,                           \
                 struct LINK_TYPE##_s *link);                           \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct TYPE##_s *self, struct TYPE##_s *swap);         \
                                                                        \
    /*moves "count" number of items from the start of this array*/      \
    /*to "head", or as many as possible*/                               \
    void (*head)(const struct TYPE##_s *self, unsigned count,           \
                 struct TYPE##_s *head);                                \
                                                                        \
    /*moves "count" number of items from the end of this array*/        \
    /*to "tail", or as many as possible*/                               \
    void (*tail)(const struct TYPE##_s *self, unsigned count,           \
                 struct TYPE##_s *tail);                                \
                                                                        \
    /*moves all except the first "count" number of items*/              \
    /*from this array to "tail", or as many as possible*/               \
    void (*de_head)(const struct TYPE##_s *self, unsigned count,        \
                    struct TYPE##_s *tail);                             \
                                                                        \
    /*moves all except the last "count" number of items*/               \
    /*from this array to "head", or as many as possible*/               \
    void (*de_tail)(const struct TYPE##_s *self, unsigned count,        \
                    struct TYPE##_s *head);                             \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct TYPE##_s *self, unsigned count,          \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
                                                                        \
    /*concatenates "self" and "tail" into a single array*/              \
    /*and places the result in "combined"*/                             \
    void (*concat)(const struct TYPE##_s *self,                         \
                   const struct TYPE##_s *tail,                         \
                   struct TYPE##_s *combined);                          \
                                                                        \
    /*reverses the items in the array*/                                 \
    void (*reverse)(struct TYPE##_s *self);                             \
                                                                        \
    /*sorts the items in the array*/                                    \
    void (*sort)(struct TYPE##_s *self);                                \
                                                                        \
    void (*print)(const struct TYPE##_s *self, FILE* output);           \
};                                                                      \
typedef struct TYPE##_s TYPE;                                           \
                                                                        \
struct LINK_TYPE##_s {                                                  \
    const CONTENT_TYPE *_;                                              \
    unsigned len;                                                       \
                                                                        \
    /*deletes the array and any allocated data it contains*/            \
    void (*del)(struct LINK_TYPE##_s *self);                            \
                                                                        \
    /*deletes any data in the array and resets its contents*/           \
    /*so that it can be linked to new data*/                            \
    void (*reset)(struct LINK_TYPE##_s *self);                          \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct LINK_TYPE##_s *self,                     \
                  const struct LINK_TYPE##_s *compare);                 \
                                                                        \
    /*returns the smallest value in the array,*/                        \
    CONTENT_TYPE (*min)(const struct LINK_TYPE##_s *self);              \
                                                                        \
    /*returns the largest value in the array,*/                         \
    CONTENT_TYPE (*max)(const struct LINK_TYPE##_s *self);              \
                                                                        \
    /*returns the sum of all items in the array*/                       \
    CONTENT_TYPE (*sum)(const struct LINK_TYPE##_s *self);              \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct LINK_TYPE##_s *self,                      \
                 struct TYPE##_s *copy);                                \
                                                                        \
    /*links the contents of this array to a read-only array*/           \
    void (*link)(const struct LINK_TYPE##_s *self,                      \
                 struct LINK_TYPE##_s *link);                           \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct LINK_TYPE##_s *self,                            \
                 struct LINK_TYPE##_s *swap);                           \
                                                                        \
    /*moves "count" number of items from the start of this array*/      \
    /*to "head", or as many as possible*/                               \
    void (*head)(const struct LINK_TYPE##_s *self, unsigned count,      \
                 struct LINK_TYPE##_s *head);                           \
                                                                        \
    /*moves "count" number of items from the start of this array*/      \
    /*to "head", or as many as possible*/                               \
    void (*tail)(const struct LINK_TYPE##_s *self, unsigned count,      \
                 struct LINK_TYPE##_s *tail);                           \
                                                                        \
    /*moves all except the first "count" number of items*/              \
    /*from this array to "tail", or as many as possible*/               \
    void (*de_head)(const struct LINK_TYPE##_s *self, unsigned count,   \
                    struct LINK_TYPE##_s *tail);                        \
                                                                        \
    /*moves all except the last "count" number of items*/               \
    /*from this array to "head", or as many as possible*/               \
    void (*de_tail)(const struct LINK_TYPE##_s *self, unsigned count,   \
                    struct LINK_TYPE##_s *head);                        \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct LINK_TYPE##_s *self, unsigned count,     \
                  struct LINK_TYPE##_s *head, struct LINK_TYPE##_s *tail); \
                                                                        \
    void (*print)(const struct LINK_TYPE##_s *self, FILE* output);      \
};                                                                      \
typedef struct LINK_TYPE##_s LINK_TYPE;                                 \
                                                                        \
struct TYPE##_s*                                                        \
TYPE##_new(void);                                                       \
                                                                        \
LINK_TYPE*                                                              \
LINK_TYPE##_new(void);

ARRAY_TYPE_DEFINITION(a_int, int, l_int)
ARRAY_TYPE_DEFINITION(a_double, double, l_double)
ARRAY_TYPE_DEFINITION(a_unsigned, unsigned, l_unsigned)


/******************************************************************/
/*         arrays of arrays such as a_int, a_double etc.          */
/******************************************************************/

#define ARRAY_A_TYPE_DEFINITION(TYPE, ARRAY_TYPE)                       \
struct TYPE##_s {                                                       \
    struct ARRAY_TYPE##_s **_;                                          \
    unsigned len;                                                       \
    unsigned total_size;                                                \
                                                                        \
    /*deletes the array and any allocated data it contains*/            \
    void (*del)(struct TYPE##_s *self);                                 \
                                                                        \
    /*resizes the array to fit at least "minimum" items*/               \
    void (*resize)(struct TYPE##_s *self, unsigned minimum);            \
                                                                        \
    /*deletes any data in the array and resets its contents*/           \
    /*so that it can be re-populated with new data*/                    \
    void (*reset)(struct TYPE##_s *self);                               \
                                                                        \
    /*returns a freshly appended array which values can be added to*/   \
    /*this array should *not* be deleted once it is done being used*/   \
    struct ARRAY_TYPE##_s* (*append)(struct TYPE##_s *self);            \
                                                                        \
    /*appends all the items in "to_add" to this array*/                 \
    void (*extend)(struct TYPE##_s *self,                               \
                   const struct TYPE##_s *to_add);                      \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct TYPE##_s *self,                          \
                  const struct TYPE##_s *compare);                      \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct TYPE##_s *self, struct TYPE##_s *copy);   \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct TYPE##_s *self, struct TYPE##_s *swap);         \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct TYPE##_s *self, unsigned count,          \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
                                                                        \
    /*splits each sub-array into "head" and "tail" arrays*/             \
    /*such that each "head" contains a copy of up to "count" items*/    \
    /*while each "tail" contains the rest*/                             \
    void (*cross_split)(const struct TYPE##_s *self, unsigned count,    \
                        struct TYPE##_s *head, struct TYPE##_s *tail);  \
                                                                        \
    /*reverses the items in the array*/                                 \
    void (*reverse)(struct TYPE##_s *self);                             \
                                                                        \
    void (*print)(const struct TYPE##_s *self, FILE* output);           \
};                                                                      \
typedef struct TYPE##_s TYPE;                                           \
                                                                        \
TYPE*                                                                   \
TYPE##_new(void);

ARRAY_A_TYPE_DEFINITION(aa_int, a_int)
ARRAY_A_TYPE_DEFINITION(aa_double, a_double)
ARRAY_A_TYPE_DEFINITION(al_int, l_int)
ARRAY_A_TYPE_DEFINITION(al_double, l_double)

/******************************************************************/
/*   arrays of arrays of arrays such as aa_int, aa_double, etc.   */
/******************************************************************/

#define ARRAY_AA_TYPE_DEFINITION(TYPE, ARRAY_TYPE)                      \
struct TYPE##_s {                                                       \
    struct ARRAY_TYPE##_s **_;                                          \
    unsigned len;                                                       \
    unsigned total_size;                                                \
                                                                        \
    /*deletes the array and any allocated data it contains*/            \
    void (*del)(struct TYPE##_s *self);                                 \
                                                                        \
    /*resizes the array to fit at least "minimum" items*/               \
    void (*resize)(struct TYPE##_s *self, unsigned minimum);            \
                                                                        \
    /*deletes any data in the array and resets its contents*/           \
    /*so that it can be re-populated with new data*/                    \
    void (*reset)(struct TYPE##_s *self);                               \
                                                                        \
    /*returns a freshly appended array_i which values can be added to*/ \
    /*this array should *not* be deleted once it is done being used*/   \
    struct ARRAY_TYPE##_s* (*append)(struct TYPE##_s *self);            \
                                                                        \
    /*appends all the items in "to_add" to this array*/                 \
    void (*extend)(struct TYPE##_s *self,                               \
                   const struct TYPE##_s *to_add);                      \
                                                                        \
    /*returns 1 if all items in array equal those in compare,*/         \
    /*returns 0 if not*/                                                \
    int (*equals)(const struct TYPE##_s *self,                          \
                  const struct TYPE##_s *compare);                      \
                                                                        \
    /*makes "copy" a duplicate of this array*/                          \
    void (*copy)(const struct TYPE##_s *self,                           \
                 struct TYPE##_s *copy);                                \
                                                                        \
    /*swaps the contents of this array with another array*/             \
    void (*swap)(struct TYPE##_s *self, struct TYPE##_s *swap);         \
                                                                        \
    /*splits the array into "head" and "tail" arrays*/                  \
    /*such that "head" contains a copy of up to "count" items*/         \
    /*while "tail" contains the rest*/                                  \
    void (*split)(const struct TYPE##_s *self, unsigned count,          \
                  struct TYPE##_s *head, struct TYPE##_s *tail);        \
                                                                        \
    /*reverses the items in the array*/                                 \
    void (*reverse)(struct TYPE##_s *self);                             \
                                                                        \
    void (*print)(const struct TYPE##_s *self, FILE* output);           \
};                                                                      \
typedef struct TYPE##_s TYPE;                                           \
                                                                        \
struct TYPE##_s*                                                        \
TYPE##_new(void);

ARRAY_AA_TYPE_DEFINITION(aaa_int, aa_int)
ARRAY_AA_TYPE_DEFINITION(aaa_double, aa_double)

/***************************************************************
 *                        object arrays                        *
 *                  [ptr1*, ptr2*, ptr3*, ...]                 *
 ***************************************************************/

struct a_obj_s {
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
    void (*del)(struct a_obj_s *self);

    /*resizes the array to fit at least "minimum" number of items,
      if necessary*/
    void (*resize)(struct a_obj_s *self, unsigned minimum);

    /*resizes the array to fit "additional_items" number of new items,
      if necessary*/
    void (*resize_for)(struct a_obj_s *self, unsigned additional_items);

    /*deletes any data in the array and resets its contents
      so that it can be re-populated with new data*/
    void (*reset)(struct a_obj_s *self);

    /*deletes any data in the array,
      resizes its contents to fit "minimum" number of items,
      and resets it contents so it can be re-populated with new data*/
    void (*reset_for)(struct a_obj_s *self, unsigned minimum);

    /*appends a single value to the array*/
    void (*append)(struct a_obj_s *self, void* value);

    /*appends several values to the array*/
    void (*vappend)(struct a_obj_s *self, unsigned count, ...);

    /*appends "value", "count" number of times*/
    void (*mappend)(struct a_obj_s *self, unsigned count, void* value);

    /*deletes the item at the given index
      and sets it to the new value*/
    void (*set)(struct a_obj_s *self, unsigned index, void* value);

    /*sets the array to new values, removing any old ones*/
    void (*vset)(struct a_obj_s *self, unsigned count, ...);

    /*sets the array to single values, removing any old ones*/
    void (*mset)(struct a_obj_s *self, unsigned count, void* value);

    /*appends all the items in "to_add" to this array*/
    void (*extend)(struct a_obj_s *self, const struct a_obj_s *to_add);

    /*makes "copy" a duplicate of this array*/
    void (*copy)(const struct a_obj_s *self, struct a_obj_s *copy);

    /*swaps the contents of this array with another array*/
    void (*swap)(struct a_obj_s *self, struct a_obj_s *swap);

    /*moves "count" number of items from the start of this array
      to "head", or as many as possible*/
    void (*head)(const struct a_obj_s *self, unsigned count,
                 struct a_obj_s *head);

    /*moves "count" number of items from the end of this array
      to "tail", or as many as possible*/
    void (*tail)(const struct a_obj_s *self, unsigned count,
                 struct a_obj_s *tail);

    /*moves all except the first "count" number of items
      from this array to "tail", or as many as possible*/
    void (*de_head)(const struct a_obj_s *self, unsigned count,
                    struct a_obj_s *tail);

    /*moves all except the last "count" number of items
      from this array to "head", or as many as possible*/
    void (*de_tail)(const struct a_obj_s *self, unsigned count,
                    struct a_obj_s *head);

    /*splits the array into "head" and "tail" arrays
      such that "head" contains a copy of up to "count" items
      while "tail" contains the rest*/
    void (*split)(const struct a_obj_s *self, unsigned count,
                  struct a_obj_s *head, struct a_obj_s *tail);

    /*concatenates "array" and "tail" into a single array*/
    /*and places the result in "combined"*/
    void (*concat)(const struct a_obj_s *self,
                   const struct a_obj_s *tail,
                   struct a_obj_s *combined);

    void (*print)(const struct a_obj_s *self, FILE* output);
};

typedef struct a_obj_s a_obj;

typedef void* (*ARRAY_COPY_FUNC)(void* obj);
typedef void (*ARRAY_FREE_FUNC)(void* obj);
typedef void (*ARRAY_PRINT_FUNC)(void* obj, FILE* output);

/*some placeholder functions for a_obj objects*/
void*
a_obj_dummy_copy(void* obj);
void
a_obj_dummy_free(void* obj);
void
a_obj_dummy_print(void* obj, FILE* output);

/*copy, free and print functions may be NULL,
  indicating no copy, free or print operations are necessary for object*/
a_obj*
a_obj_new(void* (*copy)(void* obj),
          void (*free)(void* obj),
          void (*print)(void* obj, FILE* output));

#endif
