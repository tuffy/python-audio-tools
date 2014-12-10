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

#include "array.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <float.h>
#include <assert.h>


#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

typedef int(*qsort_cmp)(const void *x, const void *y);

#define ARRAY_FUNC_DEFINITION(TYPE, CONTENT_TYPE, LINK_TYPE, CONTENT_TYPE_MIN, CONTENT_TYPE_MAX, CONTENT_TYPE_ACCUMULATOR, FORMAT_STRING)    \
                                                                     \
static void                                                          \
TYPE##_del(TYPE *self);                                              \
                                                                     \
static void                                                          \
TYPE##_resize(TYPE *self, unsigned minimum);                         \
                                                                     \
static void                                                          \
TYPE##_resize_for(TYPE *self, unsigned additional_items);            \
                                                                     \
static void                                                          \
TYPE##_reset(TYPE *self);                                            \
                                                                     \
static void                                                          \
TYPE##_reset_for(TYPE *self, unsigned minimum);                      \
                                                                     \
static void                                                          \
TYPE##_append(TYPE *self, CONTENT_TYPE value);                       \
                                                                     \
static void                                                          \
TYPE##_vappend(TYPE *self, unsigned count, ...);                     \
                                                                     \
static void                                                          \
TYPE##_mappend(TYPE *self, unsigned count,                           \
               CONTENT_TYPE value);                                  \
                                                                     \
static void                                                          \
TYPE##_insert(TYPE *self, unsigned index,                            \
              CONTENT_TYPE value);                                   \
                                                                     \
static void                                                          \
TYPE##_vset(TYPE *self, unsigned count, ...);                        \
                                                                     \
static void                                                          \
TYPE##_mset(TYPE *self, unsigned count,                              \
            CONTENT_TYPE value);                                     \
                                                                     \
static void                                                          \
TYPE##_extend(TYPE *self,                                            \
              const TYPE *to_add);                                   \
                                                                     \
static int                                                           \
TYPE##_equals(const TYPE *self,                                      \
              const TYPE *compare);                                  \
                                                                     \
static CONTENT_TYPE                                                  \
TYPE##_min(const TYPE *self);                                        \
                                                                     \
static CONTENT_TYPE                                                  \
TYPE##_max(const TYPE *self);                                        \
                                                                     \
static CONTENT_TYPE                                                  \
TYPE##_sum(const TYPE *self);                                        \
                                                                     \
static void                                                          \
TYPE##_copy(const TYPE *self,                                        \
            TYPE *copy);                                             \
                                                                     \
static void                                                          \
TYPE##_link(const TYPE *self,                                        \
            struct LINK_TYPE##_s *link);                             \
                                                                     \
static void                                                          \
TYPE##_swap(TYPE *self, TYPE *swap);                                 \
                                                                     \
static void                                                          \
TYPE##_head(const TYPE *self, unsigned count,                        \
            TYPE *head);                                             \
                                                                     \
static void                                                          \
TYPE##_tail(const TYPE *self, unsigned count,                        \
            TYPE *tail);                                             \
                                                                     \
static void                                                          \
TYPE##_de_head(const TYPE *self, unsigned count,                     \
               TYPE *tail);                                          \
                                                                     \
static void                                                          \
TYPE##_de_tail(const TYPE *self, unsigned count,                     \
               TYPE *head);                                          \
                                                                     \
static void                                                          \
TYPE##_split(const TYPE *self, unsigned count,                       \
             TYPE *head, TYPE *tail);                                \
                                                                     \
static void                                                          \
TYPE##_concat(const TYPE *self,                                      \
              const TYPE *tail,                                      \
              TYPE *combined);                                       \
                                                                     \
static void                                                          \
TYPE##_reverse(TYPE *self);                                          \
                                                                     \
static void                                                          \
TYPE##_sort(TYPE *self);                                             \
                                                                     \
static void                                                          \
TYPE##_print(const TYPE *self, FILE* output);                        \
                                                                     \
struct TYPE##_s*                                                     \
TYPE##_new(void)                                                     \
{                                                                    \
    struct TYPE##_s* a = malloc(sizeof(struct TYPE##_s));            \
    a->_ = malloc(sizeof(CONTENT_TYPE) * 1);                         \
    a->len = 0;                                                      \
    a->total_size = 1;                                               \
                                                                     \
    a->del = TYPE##_del;                                             \
    a->resize = TYPE##_resize;                                       \
    a->resize_for = TYPE##_resize_for;                               \
    a->reset = TYPE##_reset;                                         \
    a->reset_for = TYPE##_reset_for;                                 \
    a->append = TYPE##_append;                                       \
    a->vappend = TYPE##_vappend;                                     \
    a->mappend = TYPE##_mappend;                                     \
    a->insert = TYPE##_insert;                                       \
    a->vset = TYPE##_vset;                                           \
    a->mset = TYPE##_mset;                                           \
    a->extend = TYPE##_extend;                                       \
    a->equals = TYPE##_equals;                                       \
    a->min = TYPE##_min;                                             \
    a->max = TYPE##_max;                                             \
    a->sum = TYPE##_sum;                                             \
    a->copy = TYPE##_copy;                                           \
    a->link = TYPE##_link;                                           \
    a->swap = TYPE##_swap;                                           \
    a->head = TYPE##_head;                                           \
    a->tail = TYPE##_tail;                                           \
    a->de_head = TYPE##_de_head;                                     \
    a->de_tail = TYPE##_de_tail;                                     \
    a->split = TYPE##_split;                                         \
    a->concat = TYPE##_concat;                                       \
    a->reverse = TYPE##_reverse;                                     \
    a->sort = TYPE##_sort;                                           \
    a->print = TYPE##_print;                                         \
                                                                     \
    return a;                                                        \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_del(TYPE *self)                                               \
{                                                                    \
    free(self->_);                                                   \
    free(self);                                                      \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_resize(TYPE *self, unsigned minimum)                          \
{                                                                    \
    if (minimum > self->total_size) {                                \
        self->total_size = minimum;                                  \
        self->_ = realloc(self->_,                                   \
                          sizeof(CONTENT_TYPE) * minimum);           \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_resize_for(TYPE *self, unsigned additional_items)             \
{                                                                    \
    self->resize(self, self->len + additional_items);                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_reset(TYPE *self)                                             \
{                                                                    \
    self->len = 0;                                                   \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_reset_for(TYPE *self, unsigned minimum)                       \
{                                                                    \
    self->reset(self);                                               \
    self->resize(self, minimum);                                     \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_append(TYPE *self, CONTENT_TYPE value)                        \
{                                                                    \
    if (self->len == self->total_size)                               \
        self->resize(self, self->total_size * 2);                    \
                                                                     \
    self->_[self->len++] = value;                                    \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_vappend(TYPE *self, unsigned count, ...)                      \
{                                                                    \
    va_list ap;                                                      \
                                                                     \
    self->resize(self, self->len + count);                           \
    va_start(ap, count);                                             \
    for (; count > 0; count--) {                                     \
        const CONTENT_TYPE i = va_arg(ap, CONTENT_TYPE);             \
        self->_[self->len++] = i;                                    \
    }                                                                \
    va_end(ap);                                                      \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_mappend(TYPE *self, unsigned count, CONTENT_TYPE value)       \
{                                                                    \
    self->resize(self, self->len + count);                           \
    for (; count > 0; count--) {                                     \
        self->_[self->len++] = value;                                \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_insert(TYPE *self, unsigned index, CONTENT_TYPE value)        \
{                                                                    \
    index = MIN(index, self->len);                                   \
                                                                     \
    if (self->len == self->total_size)                               \
        self->resize(self, self->total_size * 2);                    \
                                                                     \
    memmove(self->_ + index + 1,                                     \
            self->_ + index,                                         \
            (self->len - index) * sizeof(CONTENT_TYPE));             \
    self->_[index] = value;                                          \
    self->len += 1;                                                  \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_vset(TYPE *self, unsigned count, ...)                         \
{                                                                    \
    va_list ap;                                                      \
                                                                     \
    self->reset_for(self, count);                                    \
    va_start(ap, count);                                             \
    for (; count > 0; count--) {                                     \
        const CONTENT_TYPE i = va_arg(ap, CONTENT_TYPE);             \
        self->_[self->len++] = i;                                    \
    }                                                                \
    va_end(ap);                                                      \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_mset(TYPE *self, unsigned count,                              \
            CONTENT_TYPE value)                                      \
{                                                                    \
    self->reset_for(self, count);                                    \
    for (; count > 0; count--) {                                     \
        self->_[self->len++] = value;                                \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_extend(TYPE *self,                                            \
              const TYPE *to_add)                                    \
{                                                                    \
    self->concat(self, to_add, self);                                \
}                                                                    \
                                                                     \
static int                                                           \
TYPE##_equals(const TYPE *self,                                      \
              const TYPE *compare)                                   \
{                                                                    \
    assert(self->_);                                                 \
    assert(compare->_);                                              \
    if (self->len == compare->len) {                                 \
        return (memcmp(self->_, compare->_,                          \
                       sizeof(CONTENT_TYPE) * self->len) == 0);      \
    } else {                                                         \
        return 0;                                                    \
    }                                                                \
}                                                                    \
                                                                     \
static CONTENT_TYPE                                                  \
TYPE##_min(const TYPE *self)                                         \
{                                                                    \
    CONTENT_TYPE min = CONTENT_TYPE_MAX;                             \
    unsigned i;                                                      \
                                                                     \
    assert(self->_);                                                 \
    for (i = 0; i < self->len; i++)                                  \
    if (self->_[i] < min)                                            \
        min = self->_[i];                                            \
                                                                     \
    return min;                                                      \
}                                                                    \
                                                                     \
static CONTENT_TYPE                                                  \
TYPE##_max(const TYPE *self)                                         \
{                                                                    \
    CONTENT_TYPE max = CONTENT_TYPE_MIN;                             \
    unsigned i;                                                      \
                                                                     \
    assert(self->_);                                                 \
    for (i = 0; i < self->len; i++)                                  \
        if (self->_[i] > max)                                        \
            max = self->_[i];                                        \
                                                                     \
    return max;                                                      \
}                                                                    \
                                                                     \
static CONTENT_TYPE                                                  \
TYPE##_sum(const TYPE *self)                                         \
{                                                                    \
    CONTENT_TYPE accumulator = CONTENT_TYPE_ACCUMULATOR;             \
    const CONTENT_TYPE *data = self->_;                              \
    unsigned size = self->len;                                       \
    unsigned i;                                                      \
                                                                     \
    assert(self->_);                                                 \
    for (i = 0; i < size; i++)                                       \
        accumulator += data[i];                                      \
                                                                     \
    return accumulator;                                              \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_copy(const TYPE *self,                                        \
            TYPE *copy)                                              \
{                                                                    \
    if (self != copy) {                                              \
        copy->resize(copy, self->len);                               \
        memcpy(copy->_, self->_,                                     \
               self->len * sizeof(CONTENT_TYPE));                    \
        copy->len = self->len;                                       \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_link(const TYPE *self,                                        \
            LINK_TYPE *link)                                         \
{                                                                    \
    link->_ = self->_;                                               \
    link->len = self->len;                                           \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_swap(TYPE *self, TYPE *swap)                                  \
{                                                                    \
    TYPE temp;                                                       \
    temp._ = self->_;                                                \
    temp.len = self->len;                                            \
    temp.total_size = self->total_size;                              \
    self->_ = swap->_;                                               \
    self->len = swap->len;                                           \
    self->total_size = swap->total_size;                             \
    swap->_ = temp._;                                                \
    swap->len = temp.len;                                            \
    swap->total_size = temp.total_size;                              \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_head(const TYPE *self, unsigned count,                        \
            TYPE *head)                                              \
{                                                                    \
    const unsigned to_copy = MIN(count, self->len);                  \
                                                                     \
    if (head != self) {                                              \
        head->resize(head, to_copy);                                 \
        memcpy(head->_, self->_, sizeof(CONTENT_TYPE) * to_copy);    \
        head->len = to_copy;                                         \
    } else {                                                         \
        head->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_tail(const TYPE *self, unsigned count,                        \
            TYPE *tail)                                              \
{                                                                    \
    const unsigned to_copy = MIN(count, self->len);                  \
                                                                     \
    if (tail != self) {                                              \
        tail->resize(tail, to_copy);                                 \
        memcpy(tail->_, self->_ + (self->len - to_copy),             \
               sizeof(CONTENT_TYPE) * to_copy);                      \
        tail->len = to_copy;                                         \
    } else {                                                         \
        memmove(tail->_, self->_ + (self->len - to_copy),            \
                sizeof(CONTENT_TYPE) * to_copy);                     \
        tail->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_de_head(const TYPE *self, unsigned count,                     \
               TYPE *tail)                                           \
{                                                                    \
    unsigned to_copy;                                                \
    count = MIN(count, self->len);                                   \
    to_copy = self->len - count;                                     \
                                                                     \
    if (tail != self) {                                              \
        tail->resize(tail, to_copy);                                 \
        memcpy(tail->_, self->_ + count,                             \
               sizeof(CONTENT_TYPE) * to_copy);                      \
        tail->len = to_copy;                                         \
    } else {                                                         \
        memmove(tail->_, self->_ + count,                            \
                sizeof(CONTENT_TYPE) * to_copy);                     \
        tail->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_de_tail(const TYPE *self, unsigned count,                     \
               TYPE *head)                                           \
{                                                                    \
    unsigned to_copy;                                                \
    count = MIN(count, self->len);                                   \
    to_copy = self->len - count;                                     \
                                                                     \
    if (head != self) {                                              \
        head->resize(head, to_copy);                                 \
        memcpy(head->_, self->_,                                     \
               sizeof(CONTENT_TYPE) * to_copy);                      \
        head->len = to_copy;                                         \
    } else {                                                         \
        head->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_split(const TYPE *self, unsigned count,                       \
             TYPE *head, TYPE *tail)                                 \
{                                                                    \
    /*ensure we don't try to move too many items*/                   \
    const unsigned to_head = MIN(count, self->len);                  \
    const unsigned to_tail = self->len - to_head;                    \
                                                                     \
    if ((head == self) && (tail == self)) {                          \
        /*do nothing*/                                               \
        return;                                                      \
    } else if (head == tail) {                                       \
        /*copy all data to head*/                                    \
        self->copy(self, head);                                      \
    } else if ((head != self) && (tail == self)) {                   \
        /*move "count" values to head and shift the rest down*/      \
        head->resize(head, to_head);                                 \
        memcpy(head->_, self->_, sizeof(CONTENT_TYPE) * to_head);    \
        head->len = to_head;                                         \
                                                                     \
        memmove(tail->_, self->_ + to_head,                          \
                sizeof(CONTENT_TYPE) * to_tail);                     \
        tail->len = to_tail;                                         \
    } else if ((head == self) && (tail != self)) {                   \
        /*move "count" values from our end to tail and reduce our size*/ \
        tail->resize(tail, to_tail);                                 \
        memcpy(tail->_, self->_ + to_head,                           \
               sizeof(CONTENT_TYPE) * to_tail);                      \
        tail->len = to_tail;                                         \
                                                                     \
        head->len = to_head;                                         \
    } else {                                                         \
        /*copy "count" values to "head" and the remainder to "tail"*/ \
        head->resize(head, to_head);                                 \
        memcpy(head->_, self->_,                                     \
               sizeof(CONTENT_TYPE) * to_head);                      \
        head->len = to_head;                                         \
                                                                     \
        tail->resize(tail, to_tail);                                 \
        memcpy(tail->_, self->_ + to_head,                           \
               sizeof(CONTENT_TYPE) * to_tail);                      \
        tail->len = to_tail;                                         \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_concat(const struct TYPE##_s *self,                           \
              const struct TYPE##_s *tail,                           \
              struct TYPE##_s *combined)                             \
{                                                                    \
    if (self == combined) {                                          \
        /*extend array with values from tail*/                       \
        combined->resize_for(combined, tail->len);                   \
        memcpy(combined->_ + combined->len,                          \
               tail->_,                                              \
               sizeof(CONTENT_TYPE) * tail->len);                    \
        combined->len += tail->len;                                  \
    } else {                                                         \
        /*concatenate array and tail to combined*/                   \
        combined->reset_for(combined, self->len + tail->len);        \
        memcpy(combined->_,                                          \
               self->_,                                              \
               sizeof(CONTENT_TYPE) * self->len);                    \
        memcpy(combined->_ + self->len,                              \
               tail->_,                                              \
               sizeof(CONTENT_TYPE) * tail->len);                    \
        combined->len = self->len + tail->len;                       \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_reverse(TYPE *self)                                           \
{                                                                    \
    unsigned i;                                                      \
    unsigned j;                                                      \
    CONTENT_TYPE *data = self->_;                                    \
                                                                     \
    if (self->len > 0) {                                             \
        for (i = 0, j = self->len - 1; i < j; i++, j--) {            \
            const CONTENT_TYPE x = data[i];                          \
            data[i] = data[j];                                       \
            data[j] = x;                                             \
        }                                                            \
    }                                                                \
}                                                                    \
                                                                     \
static int                                                           \
TYPE##_cmp(const CONTENT_TYPE *x, const CONTENT_TYPE *y)             \
{                                                                    \
    return *x - *y;                                                  \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_sort(TYPE *self)                                              \
{                                                                    \
    qsort(self->_, (size_t)(self->len),                              \
          sizeof(CONTENT_TYPE), (qsort_cmp)TYPE##_cmp);              \
}                                                                    \
                                                                     \
static void                                                          \
TYPE##_print(const TYPE *self, FILE *output)                         \
{                                                                    \
    unsigned i;                                                      \
                                                                     \
    putc('[', output);                                               \
    if (self->len == 1) {                                            \
        fprintf(output, FORMAT_STRING, self->_[0]);                  \
    } else if (self->len > 1) {                                      \
        for (i = 0; i < self->len - 1; i++)                          \
            fprintf(output, FORMAT_STRING ", ", self->_[i]);         \
        fprintf(output, FORMAT_STRING, self->_[i]);                  \
    }                                                                \
    putc(']', output);                                               \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_del(LINK_TYPE *self);                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_reset(LINK_TYPE *self);                                  \
                                                                     \
static int                                                           \
LINK_TYPE##_equals(const LINK_TYPE *self,                            \
                   const LINK_TYPE *compare);                        \
                                                                     \
static CONTENT_TYPE                                                  \
LINK_TYPE##_min(const LINK_TYPE *self);                              \
                                                                     \
static CONTENT_TYPE                                                  \
LINK_TYPE##_max(const LINK_TYPE *self);                              \
                                                                     \
static CONTENT_TYPE                                                  \
LINK_TYPE##_sum(const LINK_TYPE *self);                              \
                                                                     \
static void                                                          \
LINK_TYPE##_copy(const LINK_TYPE *self,                              \
                 struct TYPE##_s *copy);                             \
                                                                     \
static void                                                          \
LINK_TYPE##_link(const LINK_TYPE *self,                              \
                 LINK_TYPE *link);                                   \
                                                                     \
static void                                                          \
LINK_TYPE##_swap(LINK_TYPE *self,                                    \
                 LINK_TYPE *swap);                                   \
                                                                     \
static void                                                          \
LINK_TYPE##_head(const LINK_TYPE *self, unsigned count,              \
                 LINK_TYPE *head);                                   \
                                                                     \
static void                                                          \
LINK_TYPE##_tail(const LINK_TYPE *self, unsigned count,              \
                 LINK_TYPE *tail);                                   \
                                                                     \
static void                                                          \
LINK_TYPE##_de_head(const LINK_TYPE *self, unsigned count,           \
                    LINK_TYPE *tail);                                \
                                                                     \
static void                                                          \
LINK_TYPE##_de_tail(const LINK_TYPE *self, unsigned count,           \
                    LINK_TYPE *head);                                \
                                                                     \
static void                                                          \
LINK_TYPE##_split(const LINK_TYPE *self, unsigned count,             \
                  LINK_TYPE *head, LINK_TYPE *tail);                 \
                                                                     \
static void                                                          \
LINK_TYPE##_print(const LINK_TYPE *self, FILE* output);              \
                                                                     \
LINK_TYPE*                                                           \
LINK_TYPE##_new(void)                                                \
{                                                                    \
    struct LINK_TYPE##_s* array =                                    \
        malloc(sizeof(struct LINK_TYPE##_s));                        \
    array->_ = NULL;                                                 \
    array->len = 0;                                                  \
                                                                     \
    array->del = LINK_TYPE##_del;                                    \
    array->reset = LINK_TYPE##_reset;                                \
    array->equals = LINK_TYPE##_equals;                              \
    array->min = LINK_TYPE##_min;                                    \
    array->max = LINK_TYPE##_max;                                    \
    array->sum = LINK_TYPE##_sum;                                    \
    array->copy = LINK_TYPE##_copy;                                  \
    array->link = LINK_TYPE##_link;                                  \
    array->swap = LINK_TYPE##_swap;                                  \
    array->head = LINK_TYPE##_head;                                  \
    array->tail = LINK_TYPE##_tail;                                  \
    array->de_head = LINK_TYPE##_de_head;                            \
    array->de_tail = LINK_TYPE##_de_tail;                            \
    array->split = LINK_TYPE##_split;                                \
    array->print = LINK_TYPE##_print;                                \
                                                                     \
    return array;                                                    \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_del(LINK_TYPE *self)                                     \
{                                                                    \
    free(self);                                                      \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_reset(LINK_TYPE *self)                                   \
{                                                                    \
    self->len = 0;                                                   \
}                                                                    \
                                                                     \
static int                                                           \
LINK_TYPE##_equals(const LINK_TYPE *self,                            \
                   const LINK_TYPE *compare)                         \
{                                                                    \
    assert(self->_);                                                 \
    assert(compare->_);                                              \
    if (self->len == compare->len) {                                 \
        return (memcmp(self->_, compare->_,                          \
                       sizeof(CONTENT_TYPE) * self->len) == 0);      \
    } else {                                                         \
        return 0;                                                    \
    }                                                                \
}                                                                    \
                                                                     \
static CONTENT_TYPE                                                  \
LINK_TYPE##_min(const LINK_TYPE *self)                               \
{                                                                    \
    CONTENT_TYPE min = CONTENT_TYPE_MAX;                             \
    unsigned i;                                                      \
                                                                     \
    assert(self->_);                                                 \
    for (i = 0; i < self->len; i++)                                  \
    if (self->_[i] < min)                                            \
        min = self->_[i];                                            \
                                                                     \
    return min;                                                      \
}                                                                    \
                                                                     \
static CONTENT_TYPE                                                  \
LINK_TYPE##_max(const LINK_TYPE *self)                               \
{                                                                    \
    CONTENT_TYPE max = CONTENT_TYPE_MIN;                             \
    unsigned i;                                                      \
                                                                     \
    assert(self->_);                                                 \
    for (i = 0; i < self->len; i++)                                  \
        if (self->_[i] > max)                                        \
            max = self->_[i];                                        \
                                                                     \
    return max;                                                      \
}                                                                    \
                                                                     \
static CONTENT_TYPE                                                  \
LINK_TYPE##_sum(const LINK_TYPE *self)                               \
{                                                                    \
    CONTENT_TYPE accumulator = CONTENT_TYPE_ACCUMULATOR;             \
    const CONTENT_TYPE *data = self->_;                              \
    unsigned size = self->len;                                       \
    unsigned i;                                                      \
                                                                     \
    assert(self->_);                                                 \
    for (i = 0; i < size; i++)                                       \
        accumulator += data[i];                                      \
                                                                     \
    return accumulator;                                              \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_copy(const LINK_TYPE *self,                              \
                 TYPE *copy)                                         \
{                                                                    \
    copy->resize(copy, self->len);                                   \
    memcpy(copy->_, self->_, self->len * sizeof(CONTENT_TYPE));      \
    copy->len = self->len;                                           \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_link(const LINK_TYPE *self,                              \
                 LINK_TYPE *link)                                    \
{                                                                    \
    link->_ = self->_;                                               \
    link->len = self->len;                                           \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_swap(LINK_TYPE *self,                                    \
                 LINK_TYPE *swap)                                    \
{                                                                    \
    LINK_TYPE temp;                                                  \
    temp._ = self->_;                                                \
    temp.len = self->len;                                            \
    self->_ = swap->_;                                               \
    self->len = swap->len;                                           \
    swap->_ = temp._;                                                \
    swap->len = temp.len;                                            \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_head(const LINK_TYPE *self, unsigned count,              \
                 LINK_TYPE *head)                                    \
{                                                                    \
    const unsigned to_copy = MIN(count, self->len);                  \
    assert(self->_);                                                 \
    head->_ = self->_;                                               \
    head->len = to_copy;                                             \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_tail(const LINK_TYPE *self, unsigned count,              \
                 LINK_TYPE *tail)                                    \
{                                                                    \
    const unsigned to_copy = MIN(count, self->len);                  \
    assert(self->_);                                                 \
    tail->_ = self->_ + (self->len - to_copy);                       \
    tail->len = to_copy;                                             \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_de_head(const LINK_TYPE *self, unsigned count,           \
                    LINK_TYPE *tail)                                 \
{                                                                    \
    unsigned to_copy;                                                \
    assert(self->_);                                                 \
    count = MIN(count, self->len);                                   \
    to_copy = self->len - count;                                     \
                                                                     \
    tail->_ = self->_ + count;                                       \
    tail->len = to_copy;                                             \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_de_tail(const LINK_TYPE *self, unsigned count,           \
                    LINK_TYPE *head)                                 \
{                                                                    \
    head->_ = self->_;                                               \
    head->len = self->len - MIN(count, self->len);                   \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_split(const LINK_TYPE *self, unsigned count,             \
                  LINK_TYPE *head, LINK_TYPE *tail)                  \
{                                                                    \
    /*ensure we don't try to move too many items*/                   \
    const unsigned to_head = MIN(count, self->len);                  \
    const unsigned to_tail = self->len - to_head;                    \
    assert(self->_);                                                 \
                                                                     \
    if ((head == self) && (tail == self)) {                          \
        /*do nothing*/                                               \
        return;                                                      \
    } else if (head == tail) {                                       \
        /*copy all data to head*/                                    \
        head->_ = self->_;                                           \
        head->len = self->len;                                       \
    } else {                                                         \
        head->_ = self->_;                                           \
        head->len = to_head;                                         \
        tail->_ = self->_ + to_head;                                 \
        tail->len = to_tail;                                         \
    }                                                                \
}                                                                    \
                                                                     \
static void                                                          \
LINK_TYPE##_print(const LINK_TYPE *self, FILE *output)               \
{                                                                    \
    unsigned i;                                                      \
                                                                     \
    putc('[', output);                                               \
    if (self->len == 1) {                                            \
        fprintf(output, FORMAT_STRING, self->_[0]);                  \
    } else if (self->len > 1) {                                      \
        for (i = 0; i < self->len - 1; i++)                          \
            fprintf(output, FORMAT_STRING ", ", self->_[i]);         \
        fprintf(output, FORMAT_STRING, self->_[i]);                  \
    }                                                                \
    putc(']', output);                                               \
}

ARRAY_FUNC_DEFINITION(a_int, int, l_int, INT_MIN, INT_MAX, 0, "%d")
ARRAY_FUNC_DEFINITION(a_double, double, l_double, DBL_MIN, DBL_MAX, 0.0, "%f")
ARRAY_FUNC_DEFINITION(a_unsigned, unsigned, l_unsigned, 0, UINT_MAX, 0, "%u")


#define ARRAY_A_FUNC_DEFINITION(TYPE, ARRAY_TYPE, COPY_METH)   \
                                                               \
static void                                                    \
TYPE##_del(TYPE *self);                                        \
                                                               \
static void                                                    \
TYPE##_resize(TYPE *self, unsigned minimum);                   \
                                                               \
static void                                                    \
TYPE##_reset(TYPE *self);                                      \
                                                               \
static ARRAY_TYPE*                                             \
TYPE##_append(TYPE *self);                                     \
                                                               \
static void                                                    \
TYPE##_extend(TYPE *self,                                      \
              const TYPE *to_add);                             \
                                                               \
static int                                                     \
TYPE##_equals(const TYPE *self,                                \
              const TYPE *compare);                            \
                                                               \
static void                                                    \
TYPE##_copy(const TYPE *self, TYPE *copy);                     \
                                                               \
static void                                                    \
TYPE##_swap(TYPE *self, TYPE *swap);                           \
                                                               \
static void                                                    \
TYPE##_split(const TYPE *self, unsigned count,                 \
             TYPE *head, TYPE *tail);                          \
                                                               \
static void                                                    \
TYPE##_cross_split(const TYPE *self, unsigned count,           \
                   TYPE *head, TYPE *tail);                    \
                                                               \
static void                                                    \
TYPE##_reverse(TYPE *self);                                    \
                                                               \
static void                                                    \
TYPE##_print(const TYPE *self, FILE* output);                  \
                                                               \
struct TYPE##_s* TYPE##_new(void)                              \
{                                                              \
    struct TYPE##_s* a = malloc(sizeof(struct TYPE##_s));      \
    unsigned i;                                                \
                                                               \
    a->_ = malloc(sizeof(struct ARRAY_TYPE##_s*) * 1);         \
    a->len = 0;                                                \
    a->total_size = 1;                                         \
                                                               \
    for (i = 0; i < 1; i++) {                                  \
        a->_[i] = ARRAY_TYPE##_new();                          \
    }                                                          \
                                                               \
    a->del = TYPE##_del;                                       \
    a->resize = TYPE##_resize;                                 \
    a->reset = TYPE##_reset;                                   \
    a->append = TYPE##_append;                                 \
    a->extend = TYPE##_extend;                                 \
    a->equals = TYPE##_equals;                                 \
    a->copy = TYPE##_copy;                                     \
    a->swap = TYPE##_swap;                                     \
    a->split = TYPE##_split;                                   \
    a->cross_split = TYPE##_cross_split;                       \
    a->reverse = TYPE##_reverse;                               \
    a->print = TYPE##_print;                                   \
                                                               \
    return a;                                                  \
}                                                              \
                                                               \
static void                                                    \
TYPE##_del(TYPE *self)                                         \
{                                                              \
    unsigned i;                                                \
                                                               \
    for (i = 0; i < self->total_size; i++)                     \
        self->_[i]->del(self->_[i]);                           \
                                                               \
    free(self->_);                                             \
    free(self);                                                \
}                                                              \
                                                               \
static void                                                    \
TYPE##_resize(TYPE *self, unsigned minimum)                    \
{                                                              \
    if (minimum > self->total_size) {                          \
        self->_ = realloc(self->_,                             \
                           sizeof(ARRAY_TYPE*) * minimum);     \
        while (self->total_size < minimum) {                   \
            self->_[self->total_size++] = ARRAY_TYPE##_new();  \
        }                                                      \
    }                                                          \
}                                                              \
                                                               \
static void                                                    \
TYPE##_reset(TYPE *self)                                       \
{                                                              \
    unsigned i;                                                \
    for (i = 0; i < self->total_size; i++)                     \
        self->_[i]->reset(self->_[i]);                         \
    self->len = 0;                                             \
}                                                              \
                                                               \
static ARRAY_TYPE*                                             \
TYPE##_append(TYPE *self)                                      \
{                                                              \
    if (self->len == self->total_size)                         \
        self->resize(self, self->total_size * 2);              \
                                                               \
    return self->_[self->len++];                               \
}                                                              \
                                                               \
static void                                                    \
TYPE##_extend(TYPE *self,                                      \
              const TYPE *to_add)                              \
{                                                              \
    unsigned i;                                                \
    const unsigned len = to_add->len;                          \
    for (i = 0; i < len; i++) {                                \
        to_add->_[i]->COPY_METH(to_add->_[i],                  \
                                self->append(self));           \
    }                                                          \
}                                                              \
                                                               \
static int                                                     \
TYPE##_equals(const TYPE *self,                                \
              const TYPE *compare)                             \
{                                                              \
    unsigned i;                                                \
                                                               \
    if (self->len == compare->len) {                           \
        for (i = 0; i < self->len; i++)                        \
            if (!self->_[i]->equals(self->_[i], compare->_[i])) \
                return 0;                                      \
                                                               \
        return 1;                                              \
    } else                                                     \
        return 0;                                              \
}                                                              \
                                                               \
static void                                                    \
TYPE##_copy(const TYPE *self, TYPE *copy)                      \
{                                                              \
    unsigned i;                                                \
                                                               \
    if (self != copy) {                                        \
        copy->reset(copy);                                     \
        for (i = 0; i < self->len; i++)                        \
            self->_[i]->COPY_METH(self->_[i],                  \
                                  copy->append(copy));         \
    }                                                          \
}                                                              \
                                                               \
static void                                                    \
TYPE##_swap(TYPE *self, TYPE *swap)                            \
{                                                              \
    TYPE temp;                                                 \
    temp._ = self->_;                                          \
    temp.len = self->len;                                      \
    temp.total_size = self->total_size;                        \
    self->_ = swap->_;                                         \
    self->len = swap->len;                                     \
    self->total_size = swap->total_size;                       \
    swap->_ = temp._;                                          \
    swap->len = temp.len;                                      \
    swap->total_size = temp.total_size;                        \
}                                                              \
                                                               \
static void                                                    \
TYPE##_split(const TYPE *self, unsigned count,                 \
             TYPE *head, TYPE *tail)                           \
{                                                              \
    /*ensure we don't try to move too many items*/             \
    unsigned to_head = MIN(count, self->len);                  \
    unsigned i;                                                \
                                                               \
    if ((head == self) && (tail == self)) {                    \
        /*do nothing*/                                         \
        return;                                                \
    } else if ((head != self) && (tail == self)) {             \
        TYPE *temp;                                            \
        /*move "count" values to head and shift the rest down*/ \
                                                               \
        head->reset(head);                                     \
        for (i = 0; i < to_head; i++)                          \
            self->_[i]->swap(self->_[i], head->append(head));  \
                                                               \
        temp = TYPE##_new();                                   \
        for (; i < self->len; i++)                             \
            self->_[i]->swap(self->_[i], temp->append(temp));  \
                                                               \
        temp->swap(temp, tail);                                \
        temp->del(temp);                                       \
    } else if ((head == self) && (tail != self)) {             \
        /*move "count" values from our end to tail and reduce our size*/ \
                                                               \
        tail->reset(tail);                                     \
        for (i = to_head; i < self->len; i++) {                \
            self->_[i]->swap(self->_[i], tail->append(tail));  \
            self->_[i]->reset(self->_[i]);                     \
        }                                                      \
        head->len = to_head;                                   \
    } else {                                                   \
        /*copy "count" values to "head" and the remainder to "tail"*/ \
                                                               \
        head->reset(head);                                     \
        tail->reset(tail);                                     \
        for (i = 0; i < to_head; i++)                          \
            self->_[i]->COPY_METH(self->_[i], head->append(head)); \
                                                               \
        for (; i < self->len; i++)                             \
            self->_[i]->COPY_METH(self->_[i], tail->append(tail)); \
    }                                                          \
}                                                              \
                                                               \
static void                                                    \
TYPE##_cross_split(const TYPE *self, unsigned count,           \
                   TYPE *head, TYPE *tail)                     \
{                                                              \
    unsigned i;                                                \
                                                               \
    if ((head == self) && (tail == self)) {                    \
        /*do nothing*/                                         \
    } else if (head == tail) {                                 \
        self->copy(self, head);                                \
    } else if ((head != self) && (tail == self)) {             \
        head->reset(head);                                     \
        for (i = 0; i < self->len; i++) {                      \
            self->_[i]->split(self->_[i],                      \
                              count,                           \
                              head->append(head),              \
                              tail->_[i]);                     \
        }                                                      \
    } else if ((head == self) && (tail != self)) {             \
        tail->reset(tail);                                     \
        for (i = 0; i < self->len; i++) {                      \
            self->_[i]->split(self->_[i],                      \
                              count,                           \
                              head->_[i],                      \
                              tail->append(tail));             \
        }                                                      \
    } else {                                                   \
        head->reset(head);                                     \
        tail->reset(tail);                                     \
        for (i = 0; i < self->len; i++) {                      \
            self->_[i]->split(self->_[i],                      \
                              count,                           \
                              head->append(head),              \
                              tail->append(tail));             \
        }                                                      \
    }                                                          \
}                                                              \
                                                               \
static void                                                    \
TYPE##_reverse(TYPE *self)                                     \
{                                                              \
    unsigned i;                                                \
    unsigned j;                                                \
    ARRAY_TYPE **data = self->_;                               \
                                                               \
    if (self->len > 0) {                                       \
        for (i = 0, j = self->len - 1; i < j; i++, j--) {      \
            ARRAY_TYPE *x = data[i];                           \
            data[i] = data[j];                                 \
            data[j] = x;                                       \
        }                                                      \
    }                                                          \
}                                                              \
                                                               \
static void                                                    \
TYPE##_print(const TYPE *self, FILE *output)                   \
{                                                              \
    unsigned i;                                                \
                                                               \
    putc('[', output);                                         \
    if (self->len == 1) {                                      \
        self->_[0]->print(self->_[0], output);                 \
    } else if (self->len > 1) {                                \
        for (i = 0; i < self->len - 1; i++) {                  \
            self->_[i]->print(self->_[i], output);             \
            fprintf(output, ", ");                             \
        }                                                      \
        self->_[i]->print(self->_[i], output);                 \
    }                                                          \
    putc(']', output);                                         \
}

ARRAY_A_FUNC_DEFINITION(aa_int, a_int, copy)
ARRAY_A_FUNC_DEFINITION(aa_double, a_double, copy)
ARRAY_A_FUNC_DEFINITION(al_int, l_int, link)
ARRAY_A_FUNC_DEFINITION(al_double, l_double, link)

#define ARRAY_AA_FUNC_DEFINITION(TYPE, ARRAY_TYPE, COPY_METH) \
                                                              \
static void                                                   \
TYPE##_del(TYPE *self);                                       \
                                                              \
static void                                                   \
TYPE##_resize(TYPE *self, unsigned minimum);                  \
                                                              \
static void                                                   \
TYPE##_reset(TYPE *self);                                     \
                                                              \
static ARRAY_TYPE*                                            \
TYPE##_append(TYPE *self);                                    \
                                                              \
static void                                                   \
TYPE##_extend(TYPE *self,                                     \
              const TYPE *to_add);                            \
                                                              \
static int                                                    \
TYPE##_equals(const TYPE *self,                               \
              const TYPE *compare);                           \
                                                              \
static void                                                   \
TYPE##_copy(const TYPE *self,                                 \
            TYPE *copy);                                      \
                                                              \
static void                                                   \
TYPE##_swap(TYPE *self, TYPE *swap);                          \
                                                              \
static void                                                   \
TYPE##_split(const TYPE *self, unsigned count,                \
             TYPE *head, TYPE *tail);                         \
                                                              \
static void                                                   \
TYPE##_reverse(TYPE *self);                                   \
                                                              \
static void                                                   \
TYPE##_print(const TYPE *self, FILE* output);                 \
                                                              \
struct TYPE##_s*                                              \
TYPE##_new(void)                                              \
{                                                             \
    struct TYPE##_s* a = malloc(sizeof(struct TYPE##_s));     \
    unsigned i;                                               \
                                                              \
    a->_ = malloc(sizeof(struct ARRAY_TYPE##_s*) * 1);        \
    a->len = 0;                                               \
    a->total_size = 1;                                        \
                                                              \
    for (i = 0; i < 1; i++) {                                 \
        a->_[i] = ARRAY_TYPE##_new();                         \
    }                                                         \
                                                              \
    a->del = TYPE##_del;                                      \
    a->resize = TYPE##_resize;                                \
    a->reset = TYPE##_reset;                                  \
    a->append = TYPE##_append;                                \
    a->extend = TYPE##_extend;                                \
    a->equals = TYPE##_equals;                                \
    a->copy = TYPE##_copy;                                    \
    a->swap = TYPE##_swap;                                    \
    a->split = TYPE##_split;                                  \
    a->reverse = TYPE##_reverse;                              \
    a->print = TYPE##_print;                                  \
                                                              \
    return a;                                                 \
}                                                             \
                                                              \
static void                                                   \
TYPE##_del(TYPE *self)                                        \
{                                                             \
    unsigned i;                                               \
                                                              \
    for (i = 0; i < self->total_size; i++)                    \
        self->_[i]->del(self->_[i]);                          \
                                                              \
    free(self->_);                                            \
    free(self);                                               \
}                                                             \
                                                              \
static void                                                   \
TYPE##_resize(TYPE *self, unsigned minimum)                   \
{                                                             \
    if (minimum > self->total_size) {                         \
        self->_ = realloc(self->_,                            \
                           sizeof(ARRAY_TYPE*) * minimum);    \
        while (self->total_size < minimum) {                  \
            self->_[self->total_size++] = ARRAY_TYPE##_new(); \
        }                                                     \
    }                                                         \
}                                                             \
                                                              \
static void                                                   \
TYPE##_reset(TYPE *self)                                      \
{                                                             \
    unsigned i;                                               \
    for (i = 0; i < self->total_size; i++)                    \
        self->_[i]->reset(self->_[i]);                        \
    self->len = 0;                                            \
}                                                             \
                                                              \
static ARRAY_TYPE*                                            \
TYPE##_append(TYPE *self)                                     \
{                                                             \
    if (self->len == self->total_size)                        \
        self->resize(self, self->total_size * 2);             \
                                                              \
    return self->_[self->len++];                              \
}                                                             \
                                                              \
static void                                                   \
TYPE##_extend(TYPE *self, const TYPE *to_add)                 \
{                                                             \
    unsigned i;                                               \
    const unsigned len = to_add->len;                         \
    for (i = 0; i < len; i++) {                               \
        to_add->_[i]->COPY_METH(to_add->_[i], self->append(self)); \
    }                                                         \
}                                                             \
                                                              \
static int                                                    \
TYPE##_equals(const TYPE *self, const TYPE *compare)          \
{                                                             \
    unsigned i;                                               \
                                                              \
    if (self->len == compare->len) {                          \
        for (i = 0; i < self->len; i++)                       \
            if (!self->_[i]->equals(self->_[i], compare->_[i])) \
                return 0;                                     \
                                                              \
        return 1;                                             \
    } else                                                    \
        return 0;                                             \
}                                                             \
                                                              \
static void                                                   \
TYPE##_copy(const TYPE *self,                                 \
            TYPE *copy)                                       \
{                                                             \
    unsigned i;                                               \
                                                              \
    if (self != copy) {                                       \
        copy->reset(copy);                                    \
        for (i = 0; i < self->len; i++)                       \
            self->_[i]->COPY_METH(self->_[i],                 \
                                  copy->append(copy));        \
    }                                                         \
}                                                             \
                                                              \
static void                                                   \
TYPE##_swap(TYPE *self, TYPE *swap)                           \
{                                                             \
    TYPE temp;                                                \
    temp._ = self->_;                                         \
    temp.len = self->len;                                     \
    temp.total_size = self->total_size;                       \
    self->_ = swap->_;                                        \
    self->len = swap->len;                                    \
    self->total_size = swap->total_size;                      \
    swap->_ = temp._;                                         \
    swap->len = temp.len;                                     \
    swap->total_size = temp.total_size;                       \
}                                                             \
                                                              \
static void                                                   \
TYPE##_split(const TYPE *self, unsigned count,                \
             TYPE *head, TYPE *tail)                          \
{                                                             \
    /*ensure we don't try to move too many items*/            \
    unsigned to_head = MIN(count, self->len);                 \
    unsigned i;                                               \
                                                              \
    if ((head == self) && (tail == self)) {                   \
        /*do nothing*/                                        \
        return;                                               \
    } else if ((head != self) && (tail == self)) {            \
        TYPE *temp;                                           \
        /*move "count" values to head and shift the rest down*/ \
                                                              \
        head->reset(head);                                    \
        for (i = 0; i < to_head; i++)                         \
            self->_[i]->swap(self->_[i], head->append(head)); \
                                                              \
        temp = TYPE##_new();                                  \
        for (; i < self->len; i++)                            \
            self->_[i]->swap(self->_[i], temp->append(temp)); \
                                                              \
        temp->swap(temp, tail);                               \
        temp->del(temp);                                      \
    } else if ((head == self) && (tail != self)) {            \
        /*move "count" values from our end to tail and reduce our size*/ \
                                                              \
        tail->reset(tail);                                    \
        for (i = to_head; i < self->len; i++) {               \
            self->_[i]->swap(self->_[i], tail->append(tail)); \
            self->_[i]->reset(self->_[i]);                    \
        }                                                     \
        head->len = to_head;                                  \
    } else {                                                  \
        /*copy "count" values to "head" and the remainder to "tail"*/ \
                                                              \
        head->reset(head);                                    \
        tail->reset(tail);                                    \
        for (i = 0; i < to_head; i++)                         \
            self->_[i]->COPY_METH(self->_[i], head->append(head)); \
                                                              \
        for (; i < self->len; i++)                            \
            self->_[i]->COPY_METH(self->_[i], tail->append(tail)); \
    }                                                         \
}                                                             \
                                                              \
static void                                                   \
TYPE##_reverse(TYPE *self)                                    \
{                                                             \
    unsigned i;                                               \
    unsigned j;                                               \
    ARRAY_TYPE **data = self->_;                              \
                                                              \
    if (self->len > 0) {                                      \
        for (i = 0, j = self->len - 1; i < j; i++, j--) {     \
            ARRAY_TYPE *x = data[i];                          \
            data[i] = data[j];                                \
            data[j] = x;                                      \
        }                                                     \
    }                                                         \
}                                                             \
                                                              \
static void                                                   \
TYPE##_print(const TYPE *self, FILE *output)                  \
{                                                             \
    unsigned i;                                               \
                                                              \
    putc('[', output);                                        \
    if (self->len == 1) {                                     \
        self->_[0]->print(self->_[0], output);                \
    } else if (self->len > 1) {                               \
        for (i = 0; i < self->len - 1; i++) {                 \
            self->_[i]->print(self->_[i], output);            \
            fprintf(output, ", ");                            \
        }                                                     \
        self->_[i]->print(self->_[i], output);                \
    }                                                         \
    putc(']', output);                                        \
}

ARRAY_AA_FUNC_DEFINITION(aaa_int, aa_int, copy)
ARRAY_AA_FUNC_DEFINITION(aaa_double, aa_double, copy)


void*
a_obj_dummy_copy(void* obj)
{
    return obj; /*does nothing*/
}

void
a_obj_dummy_free(void* obj)
{
    return;     /*does nothing*/
}

void
a_obj_dummy_print(void* obj, FILE* output)
{
    fprintf(output, "<OBJECT>");
}

static void
a_obj_del(a_obj *self);

static void
a_obj_resize(a_obj *self, unsigned minimum);

static void
a_obj_resize_for(a_obj *self, unsigned additional_items);

static void
a_obj_reset(a_obj *self);

static void
a_obj_reset_for(a_obj *self, unsigned minimum);

static void
a_obj_append(a_obj *self, void* value);

static void
a_obj_vappend(a_obj *self, unsigned count, ...);

static void
a_obj_mappend(a_obj *self, unsigned count, void* value);

static void
a_obj_set(a_obj *self, unsigned index, void* value);

static void
a_obj_vset(a_obj *self, unsigned count, ...);

static void
a_obj_mset(a_obj *self, unsigned count, void* value);

static void
a_obj_extend(a_obj *self, const a_obj *to_add);

static void
a_obj_copy(const a_obj *self, a_obj *copy);

static void
a_obj_swap(a_obj *self, a_obj *swap);

static void
a_obj_head(const a_obj *self, unsigned count,
           a_obj *head);

static void
a_obj_tail(const a_obj *self, unsigned count,
           a_obj *tail);

static void
a_obj_de_head(const a_obj *self, unsigned count,
              a_obj *tail);

static void
a_obj_de_tail(const a_obj *self, unsigned count,
              a_obj *head);

static void
a_obj_split(const a_obj *self, unsigned count,
            a_obj *head, a_obj *tail);

static void
a_obj_concat(const a_obj *self,
             const a_obj *tail,
             a_obj *combined);

static void
a_obj_print(const a_obj *self, FILE* output);

struct a_obj_s*
a_obj_new(void* (*copy)(void* obj),
          void (*free)(void* obj),
          void (*print)(void* obj, FILE* output))
{
    struct a_obj_s* a = malloc(sizeof(struct a_obj_s));
    a->len = 0;
    a->total_size = 1;
    a->_ = malloc(sizeof(void*) * a->total_size);

    if (copy != NULL)
        a->copy_obj = copy;
    else
        a->copy_obj = a_obj_dummy_copy;

    if (free != NULL)
        a->free_obj = free;
    else
        a->free_obj = a_obj_dummy_free;

    if (print != NULL)
        a->print_obj = print;
    else
        a->print_obj = a_obj_dummy_print;

    a->del = a_obj_del;
    a->resize = a_obj_resize;
    a->resize_for = a_obj_resize_for;
    a->reset = a_obj_reset;
    a->reset_for = a_obj_reset_for;
    a->append = a_obj_append;
    a->vappend = a_obj_vappend;
    a->mappend = a_obj_mappend;
    a->set = a_obj_set;
    a->vset = a_obj_vset;
    a->mset = a_obj_mset;
    a->extend = a_obj_extend;
    a->copy = a_obj_copy;
    a->swap = a_obj_swap;
    a->head = a_obj_head;
    a->tail = a_obj_tail;
    a->de_head = a_obj_de_head;
    a->de_tail = a_obj_de_tail;
    a->split = a_obj_split;
    a->concat = a_obj_concat;
    a->concat = a_obj_concat;
    a->print = a_obj_print;

    return a;
}

static void
a_obj_del(a_obj *self)
{
    while (self->len) {
        self->free_obj(self->_[--self->len]);
    }
    free(self->_);
    free(self);
}

static void
a_obj_resize(a_obj *self, unsigned minimum)
{
    if (minimum > self->total_size) {
        self->total_size = minimum;
        self->_ = realloc(self->_, sizeof(void*) * minimum);
    }
}

static void
a_obj_resize_for(a_obj *self, unsigned additional_items)
{
    self->resize(self, self->len + additional_items);
}

static void
a_obj_reset(a_obj *self)
{
    while (self->len) {
        self->free_obj(self->_[--self->len]);
    }
}

static void
a_obj_reset_for(a_obj *self, unsigned minimum)
{
    self->reset(self);
    self->resize(self, minimum);
}

static void
a_obj_append(a_obj *self, void* value)
{
    if (self->len == self->total_size)
        self->resize(self, self->total_size * 2);

    self->_[self->len++] = self->copy_obj(value);
}

static void
a_obj_vappend(a_obj *self, unsigned count, ...)
{
    void* i;
    va_list ap;

    self->resize(self, self->len + count);
    va_start(ap, count);
    for (; count > 0; count--) {
        i = va_arg(ap, void*);
        self->_[self->len++] = self->copy_obj(i);
    }
    va_end(ap);
}

static void
a_obj_mappend(a_obj *self, unsigned count, void* value)
{
    self->resize(self, self->len + count);
    for (; count > 0; count--) {
        self->_[self->len++] = self->copy_obj(value);
    }
}

static void
a_obj_set(a_obj *self, unsigned index, void* value)
{
    assert(index < self->len);
    self->free_obj(self->_[index]);
    self->_[index] = self->copy_obj(value);
}

static void
a_obj_vset(a_obj *self, unsigned count, ...)
{
    void* i;
    va_list ap;

    self->reset_for(self, count);
    va_start(ap, count);
    for (; count > 0; count--) {
        i = va_arg(ap, void*);
        self->_[self->len++] = self->copy_obj(i);
    }
    va_end(ap);
}

static void
a_obj_mset(a_obj *self, unsigned count, void* value)
{
    self->reset_for(self, count);
    for (; count > 0; count--) {
        self->_[self->len++] = self->copy_obj(value);
    }
}

static void
a_obj_extend(a_obj *self, const a_obj *to_add)
{
    self->concat(self, to_add, self);
}

static void
a_obj_copy(const a_obj *self, a_obj *copy)
{
    if (self != copy) {
        unsigned i;

        copy->reset_for(copy, self->len);
        for (i = 0; i < self->len; i++) {
            copy->_[copy->len++] = self->copy_obj(self->_[i]);
        }
    }
}

static void
a_obj_swap(a_obj *self, a_obj *swap)
{
    a_obj temp;
    temp._ = self->_;
    temp.len = self->len;
    temp.total_size = self->total_size;
    self->_ = swap->_;
    self->len = swap->len;
    self->total_size = swap->total_size;
    swap->_ = temp._;
    swap->len = temp.len;
    swap->total_size = temp.total_size;
}

static void
a_obj_head(const a_obj *self, unsigned count,
           a_obj *head)
{
    const unsigned to_copy = MIN(count, self->len);

    if (head != self) {
        unsigned i;
        head->reset_for(head, to_copy);
        for (i = 0; i < to_copy; i++) {
            head->_[head->len++] = self->copy_obj(self->_[i]);
        }
    } else {
        while (head->len > to_copy) {
            self->free_obj(head->_[--head->len]);
        }
    }
}

static void
a_obj_tail(const a_obj *self, unsigned count,
           a_obj *tail)
{
    const unsigned to_copy = MIN(count, self->len);

    if (tail != self) {
        unsigned i;

        tail->reset_for(tail, to_copy);
        for (i = self->len - to_copy; i < self->len; i++) {
            tail->_[tail->len++] = self->copy_obj(self->_[i]);
        }
    } else {
        a_obj* temp = a_obj_new(self->copy_obj,
                                self->free_obj,
                                self->print_obj);
        unsigned i;
        temp->resize(temp, to_copy);
        for (i = self->len - to_copy; i < self->len; i++) {
            temp->_[temp->len++] = self->copy_obj(self->_[i]);
        }
        temp->swap(temp, tail);
        temp->del(temp);
    }
}

static void
a_obj_de_head(const a_obj *self, unsigned count,
              a_obj *tail)
{
    self->tail(self, self->len - MIN(count, self->len), tail);
}

static void
a_obj_de_tail(const a_obj *self, unsigned count,
              a_obj *head)
{
    self->head(self, self->len - MIN(count, self->len), head);
}

static void
a_obj_split(const a_obj *self, unsigned count,
            a_obj *head, a_obj *tail)
{
    const unsigned to_head = MIN(count, self->len);
    const unsigned to_tail = self->len - to_head;

    if ((head == self) && (tail == self)) {
        /*do nothing*/
        return;
    } else if (head == tail) {
        /*copy all data to head*/
        self->copy(self, head);
    } else if ((head == self) && (tail != self)) {
        self->tail(self, to_tail, tail);
        self->head(self, to_head, head);
    } else {
        self->head(self, to_head, head);
        self->tail(self, to_tail, tail);
    }
}

static void
a_obj_concat(const a_obj *self,
             const a_obj *tail,
             a_obj *combined)
{
    unsigned i;

    if (self == combined) {
        /*extend self with values from tail*/

        combined->resize_for(combined, tail->len);

        for (i = 0; i < tail->len; i++) {
            combined->_[combined->len++] = combined->copy_obj(tail->_[i]);
        }
    } else {
        /*concatenate self and tail to combined*/

        combined->reset_for(combined, self->len + tail->len);

        for (i = 0; i < self->len; i++) {
            combined->_[combined->len++] = combined->copy_obj(self->_[i]);
        }
        for (i = 0; i < tail->len; i++) {
            combined->_[combined->len++] = combined->copy_obj(tail->_[i]);
        }
    }
}

static void
a_obj_print(const a_obj *self, FILE* output)
{
    unsigned i;
    putc('[', output);
    if (self->len == 1) {
        self->print_obj(self->_[0], output);
    } else if (self->len > 1) {
        for (i = 0; i < self->len - 1; i++) {
            self->print_obj(self->_[i], output);
            fprintf(output, ", ");
        }
        self->print_obj(self->_[i], output);
    }
    putc(']', output);
}

/*****************************************************************
 BEGIN UNIT TESTS
 *****************************************************************/

#ifdef EXECUTABLE

#define ARRAY_TYPE_TEST_DEFINITION(TYPE, CONTENT_TYPE, LINK_TYPE)   \
void test_##TYPE(const CONTENT_TYPE *data, unsigned data_len,       \
                 CONTENT_TYPE data_min,                             \
                 CONTENT_TYPE data_max,                             \
                 CONTENT_TYPE data_sum,                             \
                 const CONTENT_TYPE *sorted_data);                  \
                                                                    \
void test_##LINK_TYPE(const TYPE *parent,                           \
                       CONTENT_TYPE data_min,                       \
                       CONTENT_TYPE data_max,                       \
                       CONTENT_TYPE data_sum);

ARRAY_TYPE_TEST_DEFINITION(a_int, int, l_int)
ARRAY_TYPE_TEST_DEFINITION(a_double, double, l_double)
ARRAY_TYPE_TEST_DEFINITION(a_unsigned, unsigned, l_unsigned)

#define ARRAY_A_TYPE_TEST_DEFINITION(TYPE, CONTENT_TYPE)            \
void test_##TYPE(unsigned arrays,                                   \
                 CONTENT_TYPE start,                                \
                 CONTENT_TYPE increment,                            \
                 unsigned total);

ARRAY_A_TYPE_TEST_DEFINITION(aa_int, int)
ARRAY_A_TYPE_TEST_DEFINITION(aa_double, double)

#define ARRAY_AA_TYPE_TEST_DEFINITION(TYPE, CONTENT_TYPE)           \
void test_##TYPE(unsigned arrays,                                   \
                 unsigned sub_arrays,                               \
                 CONTENT_TYPE start,                                \
                 CONTENT_TYPE increment,                            \
                 unsigned total);

ARRAY_AA_TYPE_TEST_DEFINITION(aaa_int, int)
ARRAY_AA_TYPE_TEST_DEFINITION(aaa_double, double)

int main(int argc, char *argv[]) {
    {
        int data[] = {5, 4, 3, 2, 1};
        int sorted_data[] = {1, 2, 3, 4, 5};

        test_a_int(data, 5, 1, 5, 15, sorted_data);
        test_aa_int(5, 0, 1, 20);
        test_aaa_int(2, 3, 0, 1, 4);
    }
    {
        double data[] = {10.0, 8.0, 6.0, 4.0, 2.0};
        double sorted_data[] = {2.0, 4.0, 6.0, 8.0, 10.0};

        test_a_double(data, 5, 2.0, 10.0, 30.0, sorted_data);
        test_aa_double(5, 0.0, 2.0, 20);
        test_aaa_double(2, 3, 0.0, 2.0, 4);
    }
    {
        unsigned data[] = {50, 40, 30, 20, 10};
        unsigned sorted_data[] = {10, 20, 30, 40, 50};
        test_a_unsigned(data, 5, 10, 50, 150, sorted_data);
    }

    return 0;
}

#define ARRAY_TYPE_TEST(TYPE, CONTENT_TYPE, LINK_TYPE)              \
void test_##TYPE(const CONTENT_TYPE *data, unsigned data_len,       \
                CONTENT_TYPE data_min,                              \
                CONTENT_TYPE data_max,                              \
                CONTENT_TYPE data_sum,                              \
                const CONTENT_TYPE *sorted_data)                    \
{                                                                   \
    TYPE *a;                                                        \
    TYPE *b;                                                        \
    unsigned i;                                                     \
                                                                    \
    assert(data_len >= 3);                                          \
                                                                    \
    /*test resize*/                                                 \
    a = TYPE##_new();                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size > 0);                                      \
    a->resize(a, 10);                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 10);                                    \
    a->resize(a, 20);                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 20);                                    \
    a->del(a);                                                      \
                                                                    \
    /*test resize_for*/                                             \
    a = TYPE##_new();                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size > 0);                                      \
    a->resize_for(a, 10);                                           \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 10);                                    \
    for (i = 0; i < 10; i++)                                        \
        a_append(a, data[0]);                                       \
    a->resize_for(a, 10);                                           \
    assert(a->len == 10);                                           \
    assert(a->total_size >= 20);                                    \
    a->del(a);                                                      \
                                                                    \
    /*test reset*/                                                  \
    a = TYPE##_new();                                               \
    a->resize(a, 10);                                               \
    for (i = 0; i < 10; i++)                                        \
        a_append(a, data[0]);                                       \
    assert(a->len == 10);                                           \
    a->reset(a);                                                    \
    assert(a->len == 0);                                            \
    a->del(a);                                                      \
                                                                    \
    /*test reset_for*/                                              \
    a = TYPE##_new();                                               \
    a->resize(a, 10);                                               \
    for (i = 0; i < 10; i++)                                        \
        a_append(a, data[0]);                                       \
    assert(a->len == 10);                                           \
    assert(a->total_size >= 10);                                    \
    a->reset_for(a, 20);                                            \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 20);                                    \
    a->del(a);                                                      \
                                                                    \
    /*test append*/                                                 \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i] == data[i]);                                 \
    a->del(a);                                                      \
                                                                    \
    /*test vappend*/                                                \
    a = TYPE##_new();                                               \
    a->vappend(a, 1, data[0]);                                      \
    assert(a->_[0] == data[0]);                                     \
    a->vappend(a, 2, data[0], data[1]);                             \
    assert(a->_[0] == data[0]);                                     \
    for (i = 0; i < 2; i++)                                         \
        assert(a->_[i + 1] == data[i]);                             \
    a->vappend(a, 3, data[0], data[1], data[2]);                    \
    assert(a->_[0] == data[0]);                                     \
    for (i = 0; i < 2; i++)                                         \
        assert(a->_[i + 1] == data[i]);                             \
    for (i = 0; i < 3; i++)                                         \
        assert(a->_[i + 3] == data[i]);                             \
    a->del(a);                                                      \
                                                                    \
    /*test mappend*/                                                \
    a = TYPE##_new();                                               \
    a->mappend(a, 100, data[0]);                                    \
    for (i = 0; i < 100; i++)                                       \
        assert(a->_[i] == data[0]);                                 \
    a->mappend(a, 200, data[1]);                                    \
    for (i = 0; i < 100; i++)                                       \
        assert(a->_[i] == data[0]);                                 \
    for (i = 0; i < 200; i++)                                       \
        assert(a->_[i + 100] == data[1]);                           \
    a->mappend(a, 300, data[2]);                                    \
    for (i = 0; i < 100; i++)                                       \
        assert(a->_[i] == data[0]);                                 \
    for (i = 0; i < 200; i++)                                       \
        assert(a->_[i + 100] == data[1]);                           \
    for (i = 0; i < 300; i++)                                       \
        assert(a->_[i + 300] == data[2]);                           \
    a->del(a);                                                      \
                                                                    \
    /*test insert*/                                                 \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->insert(a, 0, data[i]);                                   \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[a->len - i - 1] == data[i]);                    \
    a->del(a);                                                      \
                                                                    \
    /*test vset*/                                                   \
    a = TYPE##_new();                                               \
    a->vset(a, 1, data[0]);                                         \
    assert(a->_[0] == data[0]);                                     \
    a->vset(a, 2, data[0], data[1]);                                \
    for (i = 0; i < 2; i++)                                         \
        assert(a->_[i] == data[i]);                                 \
    a->vset(a, 3, data[0], data[1], data[2]);                       \
    for (i = 0; i < 3; i++)                                         \
        assert(a->_[i] == data[i]);                                 \
    a->del(a);                                                      \
                                                                    \
    /*test mset*/                                                   \
    a = TYPE##_new();                                               \
    a->mset(a, 100, data[0]);                                       \
    for (i = 0; i < 100; i++)                                       \
        assert(a->_[i] == data[0]);                                 \
    a->mset(a, 200, data[1]);                                       \
    for (i = 0; i < 200; i++)                                       \
        assert(a->_[i] == data[1]);                                 \
    a->mset(a, 300, data[2]);                                       \
    for (i = 0; i < 300; i++)                                       \
        assert(a->_[i] == data[2]);                                 \
    a->del(a);                                                      \
                                                                    \
    /*test extend*/                                                 \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
                                                                    \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    b->extend(b, a);                                                \
    for (i = 0; i < data_len; i++)                                  \
        assert(b->_[i] == data[i]);                                 \
    a->reset(a);                                                    \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, sorted_data[i]);                               \
    b->extend(b, a);                                                \
    for (i = 0; i < data_len; i++)                                  \
        assert(b->_[i] == data[i]);                                 \
    for (i = 0; i < data_len; i++)                                  \
        assert(b->_[i + data_len] == sorted_data[i]);               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test equals*/                                                 \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
                                                                    \
    for (i = 0; i < data_len; i++) {                                \
        a->append(a, data[i]);                                      \
        b->append(b, data[i]);                                      \
    }                                                               \
    assert(a->equals(a, a));                                        \
    assert(a->equals(a, b));                                        \
    b->reset(b);                                                    \
    for (i = 0; i < data_len; i++)                                  \
        b->append(b, sorted_data[i]);                               \
    assert(!a->equals(a, b));                                       \
    assert(!b->equals(b, a));                                       \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test min*/                                                    \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    assert(a->min(a) == data_min);                                  \
    a->del(a);                                                      \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, sorted_data[i]);                               \
    assert(a->min(a) == data_min);                                  \
    a->del(a);                                                      \
                                                                    \
    /*test max*/                                                    \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    assert(a->max(a) == data_max);                                  \
    a->del(a);                                                      \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, sorted_data[i]);                               \
    assert(a->max(a) == data_max);                                  \
    a->del(a);                                                      \
                                                                    \
    /*test sum*/                                                    \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    assert(a->sum(a) == data_sum);                                  \
    a->del(a);                                                      \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, sorted_data[i]);                               \
    assert(a->sum(a) == data_sum);                                  \
    a->del(a);                                                      \
                                                                    \
    /*test copy*/                                                   \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++) {                                \
        a->append(a, data[i]);                                      \
        b->append(b, sorted_data[i]);                               \
    }                                                               \
    assert(!a->equals(a, b));                                       \
    a->copy(a, b);                                                  \
    assert(a->equals(a, b));                                        \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test link*/                                                   \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    test_##LINK_TYPE(a, data_min, data_max, data_sum);              \
    a->del(a);                                                      \
                                                                    \
    /*test swap*/                                                   \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++) {                                \
        a->append(a, data[i]);                                      \
        b->append(b, sorted_data[i]);                               \
    }                                                               \
    for (i = 0; i < data_len; i++) {                                \
        assert(a->_[i] == data[i]);                                 \
        assert(b->_[i] == sorted_data[i]);                          \
    }                                                               \
    a->swap(a, a);                                                  \
    for (i = 0; i < data_len; i++) {                                \
        assert(a->_[i] == data[i]);                                 \
        assert(b->_[i] == sorted_data[i]);                          \
    }                                                               \
    a->swap(a, b);                                                  \
    for (i = 0; i < data_len; i++) {                                \
        assert(a->_[i] == sorted_data[i]);                          \
        assert(b->_[i] == data[i]);                                 \
    }                                                               \
    b->swap(b, a);                                                  \
    for (i = 0; i < data_len; i++) {                                \
        assert(a->_[i] == data[i]);                                 \
        assert(b->_[i] == sorted_data[i]);                          \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test head*/                                                   \
    for (i = 0; i < data_len; i++) {                                \
        unsigned j;                                                 \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->head(a, i, a);                                           \
        assert(a->len == i);                                        \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j] == data[j]);                             \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->head(a, data_len + 1, a);                                \
        assert(a->len == data_len);                                 \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->head(a, i, b);                                           \
        assert(a->len == data_len);                                 \
        assert(b->len == i);                                        \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == data[j]);                             \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->head(a, data_len + 1, b);                                \
        assert(a->equals(a, b));                                    \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test tail*/                                                   \
    for (i = 0; i < data_len; i++) {                                \
        unsigned j;                                                 \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->tail(a, i, a);                                           \
        assert(a->len == i);                                        \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j] == data[j + (data_len - i)]);            \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->tail(a, data_len + 1, a);                                \
        assert(a->len == data_len);                                 \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->tail(a, i, b);                                           \
        assert(a->len == data_len);                                 \
        assert(b->len == i);                                        \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == data[j + (data_len - i)]);            \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->tail(a, data_len + 1, b);                                \
        assert(a->equals(a, b));                                    \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test de_head*/                                                \
    for (i = 0; i < data_len; i++) {                                \
        unsigned j;                                                 \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_head(a, i, a);                                        \
        assert(a->len == (data_len - i));                           \
        for (j = 0; j < (data_len - i); j++)                        \
            assert(a->_[j] == data[j + i]);                         \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_head(a, data_len + 1, a);                             \
        assert(a->len == 0);                                        \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_head(a, i, b);                                        \
        assert(a->len == data_len);                                 \
        assert(b->len == (data_len - i));                           \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        for (j = 0; j < (data_len - i); j++)                        \
            assert(b->_[j] == data[j + i]);                         \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_head(a, data_len + 1, b);                             \
        assert(a->len == data_len);                                 \
        assert(b->len == 0);                                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test de_tail*/                                                \
    for (i = 0; i < data_len; i++) {                                \
        unsigned j;                                                 \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_tail(a, i, a);                                        \
        assert(a->len == (data_len - i));                           \
        for (j = 0; j < (data_len - i); j++)                        \
            assert(a->_[j] == data[j]);                             \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_tail(a, data_len + 1, a);                             \
        assert(a->len == 0);                                        \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_tail(a, i, b);                                        \
        assert(a->len == data_len);                                 \
        assert(b->len == (data_len - i));                           \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        for (j = 0; j < (data_len - i); j++)                        \
            assert(b->_[j] == data[j]);                             \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->de_tail(a, data_len + 1, b);                             \
        assert(a->len == data_len);                                 \
        assert(b->len == 0);                                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test split*/                                                  \
    for (i = 0; i < data_len; i++) {                                \
        unsigned j;                                                 \
        unsigned k;                                                 \
        TYPE *c;                                                    \
                                                                    \
        a = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
                                                                    \
        a->split(a, i, a, a);                                       \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        a->del(a);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->split(a, i, a, b);                                       \
        assert(a->len == i);                                        \
        assert(b->len == (data_len - i));                           \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j] == data[j]);                             \
        for (k = 0; j < data_len; j++,k++)                          \
            assert(b->_[k] == data[j]);                             \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->split(a, i, b, a);                                       \
        assert(a->len == (data_len - i));                           \
        assert(b->len == i);                                        \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == data[j]);                             \
        for (k = 0; j < data_len; j++,k++)                          \
            assert(a->_[k] == data[j]);                             \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        c = TYPE##_new();                                           \
        for (j = 0; j < data_len; j++)                              \
            a->append(a, data[j]);                                  \
        a->split(a, i, b, c);                                       \
        assert(a->len == data_len);                                 \
        for (j = 0; j < data_len; j++)                              \
            assert(a->_[j] == data[j]);                             \
        assert(b->len == i);                                        \
        assert(c->len == (data_len - i));                           \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == data[j]);                             \
        for (k = 0; j < data_len; j++,k++)                          \
            assert(c->_[k] == data[j]);                             \
        a->del(a);                                                  \
        b->del(b);                                                  \
        c->del(c);                                                  \
    }                                                               \
                                                                    \
    /*test concat*/                                                 \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    a->concat(a, a, a);                                             \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i] == data[i]);                                 \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i + data_len] == data[i]);                      \
    a->del(a);                                                      \
                                                                    \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    a->concat(a, a, b);                                             \
    for (i = 0; i < data_len; i++)                                  \
        assert(b->_[i] == data[i]);                                 \
    for (i = 0; i < data_len; i++)                                  \
        assert(b->_[i + data_len] == data[i]);                      \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++) {                                \
        a->append(a, data[i]);                                      \
        b->append(b, sorted_data[i]);                               \
    }                                                               \
    a->concat(a, b, a);                                             \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i] == data[i]);                                 \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i + data_len] == sorted_data[i]);               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    {                                                               \
        TYPE *c;                                                    \
                                                                    \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        c = TYPE##_new();                                           \
        for (i = 0; i < data_len; i++) {                            \
            a->append(a, data[i]);                                  \
            b->append(b, sorted_data[i]);                           \
        }                                                           \
        a->concat(a, b, c);                                         \
        for (i = 0; i < data_len; i++)                              \
            assert(c->_[i] == data[i]);                             \
        for (i = 0; i < data_len; i++)                              \
            assert(c->_[i + data_len] == sorted_data[i]);           \
        a->del(a);                                                  \
        b->del(b);                                                  \
        c->del(c);                                                  \
    }                                                               \
                                                                    \
    /*test reverse*/                                                \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    a->reverse(a);                                                  \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i] == data[data_len - i - 1]);                  \
    a->del(a);                                                      \
                                                                    \
    /*test sort*/                                                   \
    a = TYPE##_new();                                               \
    for (i = 0; i < data_len; i++)                                  \
        a->append(a, data[i]);                                      \
    a->sort(a);                                                     \
    for (i = 0; i < data_len; i++)                                  \
        assert(a->_[i] == sorted_data[i]);                          \
    a->del(a);                                                      \
}                                                                   \
                                                                    \
void test_##LINK_TYPE(const TYPE *parent,                           \
                      CONTENT_TYPE data_min,                        \
                      CONTENT_TYPE data_max,                        \
                      CONTENT_TYPE data_sum)                        \
{                                                                   \
    unsigned i;                                                     \
    LINK_TYPE* a;                                                   \
    LINK_TYPE* b;                                                   \
    TYPE *c;                                                        \
                                                                    \
    /*test internal data*/                                          \
    a = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    assert(a->len == parent->len);                                  \
    for (i = 0; i < parent->len; i++)                               \
        assert(a->_[i] == parent->_[i]);                            \
    a->del(a);                                                      \
                                                                    \
    /*test reset*/                                                  \
    a = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    assert(a->len == parent->len);                                  \
    a->reset(a);                                                    \
    assert(a->len == 0);                                            \
    a->del(a);                                                      \
                                                                    \
    /*test equals*/                                                 \
    a = LINK_TYPE##_new();                                          \
    b = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    parent->link(parent, b);                                        \
    assert(a->equals(a, b));                                        \
    assert(b->equals(b, a));                                        \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test min*/                                                    \
    a = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    assert(a->min(a) == data_min);                                  \
    a->del(a);                                                      \
                                                                    \
    /*test max*/                                                    \
    a = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    assert(a->max(a) == data_max);                                  \
    a->del(a);                                                      \
                                                                    \
    /*test sum*/                                                    \
    a = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    assert(a->sum(a) == data_sum);                                  \
    a->del(a);                                                      \
                                                                    \
    /*test copy*/                                                   \
    a = LINK_TYPE##_new();                                          \
    c = TYPE##_new();                                               \
    parent->link(parent, a);                                        \
    a->copy(a, c);                                                  \
    assert(parent->equals(parent, c));                              \
    a->del(a);                                                      \
    c->del(c);                                                      \
                                                                    \
    /*test swap*/                                                   \
    a = LINK_TYPE##_new();                                          \
    b = LINK_TYPE##_new();                                          \
    parent->link(parent, a);                                        \
    assert(a->len == parent->len);                                  \
    assert(b->len == 0);                                            \
    for (i = 0; i < parent->len; i++)                               \
        assert(a->_[i] == parent->_[i]);                            \
    a->swap(a, b);                                                  \
    assert(a->len == 0);                                            \
    assert(b->len == parent->len);                                  \
    for (i = 0; i < parent->len; i++)                               \
        assert(b->_[i] == parent->_[i]);                            \
    b->swap(b, a);                                                  \
    assert(a->len == parent->len);                                  \
    assert(b->len == 0);                                            \
    for (i = 0; i < parent->len; i++)                               \
        assert(a->_[i] == parent->_[i]);                            \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test head*/                                                   \
    for (i = 0; i < parent->len; i++) {                             \
        unsigned j;                                                 \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->head(a, i, a);                                           \
        assert(a->len == i);                                        \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->head(a, parent->len + 1, a);                             \
        assert(a->len == parent->len);                              \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->head(a, i, b);                                           \
        assert(a->len == parent->len);                              \
        assert(b->len == i);                                        \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->head(a, parent->len + 1, b);                             \
        assert(a->equals(a, b));                                    \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test tail*/                                                   \
    for (i = 0; i < parent->len; i++) {                             \
        unsigned j;                                                 \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->tail(a, i, a);                                           \
        assert(a->len == i);                                        \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j] == parent->_[j + (parent->len - i)]);    \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->tail(a, parent->len + 1, a);                             \
        assert(a->len == parent->len);                              \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->tail(a, i, b);                                           \
        assert(a->len == parent->len);                              \
        assert(b->len == i);                                        \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == parent->_[j + (parent->len - i)]);    \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->tail(a, parent->len + 1, b);                             \
        assert(a->equals(a, b));                                    \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test de_head*/                                                \
    for (i = 0; i < parent->len; i++) {                             \
        unsigned j;                                                 \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_head(a, i, a);                                        \
        assert(a->len == (parent->len - i));                        \
        for (j = 0; j < (parent->len - i); j++)                     \
            assert(a->_[j] == parent->_[j + i]);                    \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_head(a, parent->len + 1, a);                          \
        assert(a->len == 0);                                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_head(a, i, b);                                        \
        assert(a->len == parent->len);                              \
        assert(b->len == (parent->len - i));                        \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        for (j = 0; j < (parent->len - i); j++)                     \
            assert(b->_[j] == parent->_[j + i]);                    \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_head(a, parent->len + 1, b);                          \
        assert(a->len == parent->len);                              \
        assert(b->len == 0);                                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test de_tail*/                                                \
    for (i = 0; i < parent->len; i++) {                             \
        unsigned j;                                                 \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_tail(a, i, a);                                        \
        assert(a->len == (parent->len - i));                        \
        for (j = 0; j < (parent->len - i); j++)                     \
            assert(a->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_tail(a, parent->len + 1, a);                          \
        assert(a->len == 0);                                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_tail(a, i, b);                                        \
        assert(a->len == parent->len);                              \
        assert(b->len == (parent->len - i));                        \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        for (j = 0; j < (parent->len - i); j++)                     \
            assert(b->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->de_tail(a, parent->len + 1, b);                          \
        assert(a->len == parent->len);                              \
        assert(b->len == 0);                                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
    }                                                               \
                                                                    \
    /*test split*/                                                  \
    for (i = 0; i < parent->len; i++) {                             \
        unsigned j;                                                 \
        unsigned k;                                                 \
        LINK_TYPE *c;                                               \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
                                                                    \
        a->split(a, i, a, a);                                       \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        a->del(a);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->split(a, i, a, b);                                       \
        assert(a->len == i);                                        \
        assert(b->len == (parent->len - i));                        \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j] == parent->_[j]);                        \
        for (k = 0; j < parent->len; j++,k++)                       \
            assert(b->_[k] == parent->_[j]);                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->split(a, i, b, a);                                       \
        assert(a->len == (parent->len - i));                        \
        assert(b->len == i);                                        \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == parent->_[j]);                        \
        for (k = 0; j < parent->len; j++,k++)                       \
            assert(a->_[k] == parent->_[j]);                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        a = LINK_TYPE##_new();                                      \
        b = LINK_TYPE##_new();                                      \
        c = LINK_TYPE##_new();                                      \
        parent->link(parent, a);                                    \
        a->split(a, i, b, c);                                       \
        assert(a->len == parent->len);                              \
        for (j = 0; j < parent->len; j++)                           \
            assert(a->_[j] == parent->_[j]);                        \
        assert(b->len == i);                                        \
        assert(c->len == (parent->len - i));                        \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j] == parent->_[j]);                        \
        for (k = 0; j < parent->len; j++,k++)                       \
            assert(c->_[k] == parent->_[j]);                        \
        a->del(a);                                                  \
        b->del(b);                                                  \
        c->del(c);                                                  \
    }                                                               \
}

ARRAY_TYPE_TEST(a_int, int, l_int)
ARRAY_TYPE_TEST(a_double, double, l_double)
ARRAY_TYPE_TEST(a_unsigned, unsigned, l_unsigned)

#define ARRAY_A_TYPE_TEST(TYPE, ARRAY_TYPE, CONTENT_TYPE)           \
void test_##TYPE(unsigned arrays,                                   \
                 CONTENT_TYPE start,                                \
                 CONTENT_TYPE increment,                            \
                 unsigned total)                                    \
{                                                                   \
    TYPE *a;                                                        \
    TYPE *b;                                                        \
    unsigned i;                                                     \
    CONTENT_TYPE old_start;                                         \
                                                                    \
    /*test resize*/                                                 \
    a = TYPE##_new();                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size > 0);                                      \
    a->resize(a, 10);                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 10);                                    \
    a->resize(a, 20);                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 20);                                    \
    a->del(a);                                                      \
                                                                    \
    /*test reset*/                                                  \
    a = TYPE##_new();                                               \
    a->resize(a, 10);                                               \
    for (i = 0; i < 10; i++)                                        \
        (void)a->append(a);                                         \
    assert(a->len == 10);                                           \
    a->reset(a);                                                    \
    assert(a->len == 0);                                            \
    a->del(a);                                                      \
                                                                    \
    /*test append*/                                                 \
    /*note that we don't care about array contents,                 \
      only that there are arrays*/                                  \
    a = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = a->append(a);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            start += increment;                                     \
        }                                                           \
        assert(c->len == total);                                    \
    }                                                               \
    assert(a->len == arrays);                                       \
    a->del(a);                                                      \
                                                                    \
    /*test extend*/                                                 \
    old_start = start;                                              \
    a = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = a->append(a);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            start += increment;                                     \
        }                                                           \
    }                                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = b->append(b);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            start += increment;                                     \
        }                                                           \
    }                                                               \
    a->extend(a, b);                                                \
    assert(a->len == (arrays * 2));                                 \
    for (i = 0; i < arrays; i++) {                                  \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            assert(a->_[i]->_[j] == old_start);                     \
            old_start += increment;                                 \
        }                                                           \
    }                                                               \
    for (i = 0; i < arrays; i++) {                                  \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            assert(a->_[i + arrays]->_[j] == old_start);            \
            old_start += increment;                                 \
        }                                                           \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test equals*/                                                 \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = a->append(a);                               \
        ARRAY_TYPE *d = b->append(b);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            d->append(d, start);                                    \
            start += increment;                                     \
        }                                                           \
    }                                                               \
    assert(a->equals(a, b));                                        \
    assert(b->equals(b, a));                                        \
    b->reset(b);                                                    \
    assert(!a->equals(a, b));                                       \
    assert(!b->equals(b, a));                                       \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test copy*/                                                   \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = a->append(a);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            start += increment;                                     \
        }                                                           \
    }                                                               \
    assert(!a->equals(a, b));                                       \
    a->copy(a, b);                                                  \
    assert(a->equals(a, b));                                        \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test swap*/                                                   \
    old_start = start;                                              \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = a->append(a);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            start += increment;                                     \
        }                                                           \
    }                                                               \
    assert(a->len == arrays);                                       \
    assert(b->len == 0);                                            \
    a->swap(a, b);                                                  \
    assert(a->len == 0);                                            \
    assert(b->len == arrays);                                       \
    for (i = 0; i < arrays; i++) {                                  \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            assert(b->_[i]->_[j] == old_start);                     \
            old_start += increment;                                 \
        }                                                           \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test split*/                                                  \
    for (i = 0; i < arrays; i++) {                                  \
        TYPE *c;                                                    \
        unsigned j;                                                 \
        unsigned k;                                                 \
        CONTENT_TYPE old_start2;                                    \
                                                                    \
        /*split a to a,a*/                                          \
        old_start = start;                                          \
        a = TYPE##_new();                                           \
                                                                    \
        for (j = 0; j < arrays; j++) {                              \
            ARRAY_TYPE *d = a->append(a);                           \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->split(a, i, a, a);                                       \
        for (j = 0; j < arrays; j++) {                              \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
                                                                    \
        /*split a to a,b*/                                          \
        old_start = start;                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
                                                                    \
        for (j = 0; j < arrays; j++) {                              \
            ARRAY_TYPE *d = a->append(a);                           \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->split(a, i, a, b);                                       \
        assert(a->len == i);                                        \
        assert(b->len == (arrays - i));                             \
        for (j = 0; j < i; j++) {                                   \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        for (j = 0; j < (arrays - i); j++) {                        \
            for (k = 0; k < total; k++) {                           \
                assert(b->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        /*split a to b,a*/                                          \
        old_start = start;                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
                                                                    \
        for (j = 0; j < arrays; j++) {                              \
            ARRAY_TYPE *d = a->append(a);                           \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->split(a, i, b, a);                                       \
        assert(a->len == (arrays - i));                             \
        assert(b->len == i);                                        \
        for (j = 0; j < i; j++) {                                   \
            for (k = 0; k < total; k++) {                           \
                assert(b->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        for (j = 0; j < (arrays - i); j++) {                        \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        /*split a to b,c*/                                          \
        old_start = old_start2 = start;                             \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        c = TYPE##_new();                                           \
                                                                    \
        for (j = 0; j < arrays; j++) {                              \
            ARRAY_TYPE *d = a->append(a);                           \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->split(a, i, b, c);                                       \
        assert(a->len == arrays);                                   \
        for (j = 0; j < arrays; j++) {                              \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[j]->_[k] == old_start2);                \
                old_start2 += increment;                            \
            }                                                       \
        }                                                           \
        assert(b->len == i);                                        \
        assert(c->len == (arrays - i));                             \
        for (j = 0; j < i; j++) {                                   \
            for (k = 0; k < total; k++) {                           \
                assert(b->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        for (j = 0; j < (arrays - i); j++) {                        \
            for (k = 0; k < total; k++) {                           \
                assert(c->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
        b->del(b);                                                  \
        c->del(c);                                                  \
    }                                                               \
                                                                    \
    /*test cross_split*/                                            \
    for (i = 0; i < total; i++) {                                   \
        unsigned j;                                                 \
        unsigned k;                                                 \
        TYPE *c;                                                    \
        CONTENT_TYPE old_start2;                                    \
                                                                    \
        /*cross_split a to a,a*/                                    \
        old_start = start;                                          \
        a = TYPE##_new();                                           \
        for (j = 0; j < arrays; j++) {                              \
            ARRAY_TYPE *d = a->append(a);                           \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->cross_split(a, i, a, a);                                 \
        for (j = 0; j < arrays; j++) {                              \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[j]->_[k] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
                                                                    \
        /*cross_split a to a,b*/                                    \
        old_start = start;                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < arrays; j++)                                \
            (void)a->append(a);                                     \
        for (j = 0; j < total; j++) {                               \
            for (k = 0; k < arrays; k++) {                          \
                a->_[k]->append(a->_[k], start);                    \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->cross_split(a, i, a, b);                                 \
        for (j = 0; j < i; j++) {                                   \
            for (k = 0; k < arrays; k++) {                          \
                assert(a->_[k]->_[j] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        for (j = 0; j < (total - i); j++) {                         \
            for (k = 0; k < arrays; k++) {                          \
                assert(b->_[k]->_[j] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        /*cross_split a to b,a*/                                    \
        old_start = start;                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        for (j = 0; j < arrays; j++)                                \
            (void)a->append(a);                                     \
        for (j = 0; j < total; j++) {                               \
            for (k = 0; k < arrays; k++) {                          \
                a->_[k]->append(a->_[k], start);                    \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->cross_split(a, i, b, a);                                 \
        for (j = 0; j < i; j++) {                                   \
            for (k = 0; k < arrays; k++) {                          \
                assert(b->_[k]->_[j] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        for (j = 0; j < (total - i); j++) {                         \
            for (k = 0; k < arrays; k++) {                          \
                assert(a->_[k]->_[j] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        /*cross_split a to b,c*/                                    \
        old_start = old_start2 = start;                             \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        c = TYPE##_new();                                           \
        for (j = 0; j < arrays; j++)                                \
            (void)a->append(a);                                     \
        for (j = 0; j < total; j++) {                               \
            for (k = 0; k < arrays; k++) {                          \
                a->_[k]->append(a->_[k], start);                    \
                start += increment;                                 \
            }                                                       \
        }                                                           \
        a->cross_split(a, i, b, c);                                 \
        for (j = 0; j < total; j++) {                               \
            for (k = 0; k < arrays; k++) {                          \
                assert(a->_[k]->_[j] == old_start2);                \
                old_start2 += increment;                            \
            }                                                       \
        }                                                           \
        for (j = 0; j < i; j++) {                                   \
            for (k = 0; k < arrays; k++) {                          \
                assert(b->_[k]->_[j] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        for (j = 0; j < (total - i); j++) {                         \
            for (k = 0; k < arrays; k++) {                          \
                assert(c->_[k]->_[j] == old_start);                 \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
        a->del(a);                                                  \
        b->del(b);                                                  \
        c->del(c);                                                  \
    }                                                               \
                                                                    \
    /*test reverse*/                                                \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        ARRAY_TYPE *c = a->append(a);                               \
        unsigned j;                                                 \
        for (j = 0; j < total; j++) {                               \
            c->append(c, start);                                    \
            start += increment;                                     \
        }                                                           \
    }                                                               \
    a->copy(a, b);                                                  \
    a->reverse(a);                                                  \
    for (i = 0; i < arrays; i++) {                                  \
        assert(a->_[i]->equals(a->_[i], b->_[arrays - i - 1]));     \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
}

ARRAY_A_TYPE_TEST(aa_int, a_int, int)
ARRAY_A_TYPE_TEST(aa_double, a_double, double)

#define ARRAY_AA_TYPE_TEST(TYPE, A_TYPE, AA_TYPE, CONTENT_TYPE)     \
void test_##TYPE(unsigned arrays,                                   \
                 unsigned sub_arrays,                               \
                 CONTENT_TYPE start,                                \
                 CONTENT_TYPE increment,                            \
                 unsigned total)                                    \
{                                                                   \
    TYPE *a;                                                        \
    TYPE *b;                                                        \
    unsigned i;                                                     \
    CONTENT_TYPE old_start;                                         \
                                                                    \
    /*test resize*/                                                 \
    a = TYPE##_new();                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size > 0);                                      \
    a->resize(a, 10);                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 10);                                    \
    a->resize(a, 20);                                               \
    assert(a->len == 0);                                            \
    assert(a->total_size >= 20);                                    \
    a->del(a);                                                      \
                                                                    \
    /*test reset*/                                                  \
    a = TYPE##_new();                                               \
    a->resize(a, 10);                                               \
    for (i = 0; i < 10; i++)                                        \
        (void)a->append(a);                                         \
    assert(a->len == 10);                                           \
    a->reset(a);                                                    \
    assert(a->len == 0);                                            \
    a->del(a);                                                      \
                                                                    \
    /*test append*/                                                 \
    a = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* d = c->append(c);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
            assert(d->len == total);                                \
        }                                                           \
        assert(c->len == sub_arrays);                               \
    }                                                               \
    assert(a->len == arrays);                                       \
    a->del(a);                                                      \
                                                                    \
    /*test extend*/                                                 \
    old_start = start;                                              \
    a = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* d = c->append(c);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
            assert(d->len == total);                                \
        }                                                           \
    }                                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* d = c->append(c);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
            assert(d->len == total);                                \
        }                                                           \
    }                                                               \
    a->extend(a, b);                                                \
    assert(a->len == (arrays * 2));                                 \
    for (i = 0; i < arrays; i++) {                                  \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[i]->_[j]->_[k] == old_start);           \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
    }                                                               \
    for (i = 0; i < arrays; i++) {                                  \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                assert(a->_[i + arrays]->_[j]->_[k] == old_start);  \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test equals*/                                                 \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        A_TYPE *d = b->append(b);                                   \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* e = c->append(c);                              \
            AA_TYPE* f = d->append(d);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                e->append(e, start);                                \
                f->append(f, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
    }                                                               \
    assert(a->equals(a, b));                                        \
    assert(b->equals(b, a));                                        \
    b->reset(b);                                                    \
    assert(!a->equals(a, b));                                       \
    assert(!b->equals(b, a));                                       \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test copy*/                                                   \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* d = c->append(c);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
    }                                                               \
    assert(!a->equals(a, b));                                       \
    a->copy(a, b);                                                  \
    assert(a->equals(a, b));                                        \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test swap*/                                                   \
    old_start = start;                                              \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* d = c->append(c);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
    }                                                               \
    assert(a->len == arrays);                                       \
    assert(b->len == 0);                                            \
    a->swap(a, b);                                                  \
    assert(a->len == 0);                                            \
    assert(b->len == arrays);                                       \
    for (i = 0; i < arrays; i++) {                                  \
        unsigned j;                                                 \
        for (j = 0; j < sub_arrays; j++) {                          \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                assert(b->_[i]->_[j]->_[k] == old_start);           \
                old_start += increment;                             \
            }                                                       \
        }                                                           \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
                                                                    \
    /*test split*/                                                  \
    for (i = 0; i < arrays; i++) {                                  \
        TYPE *base = TYPE##_new();                                  \
        TYPE *c;                                                    \
        unsigned j;                                                 \
                                                                    \
        for (j = 0; j < arrays; j++) {                              \
            A_TYPE *c = base->append(base);                         \
            unsigned k;                                             \
                                                                    \
            for (k = 0; k < sub_arrays; k++) {                      \
                AA_TYPE* d = c->append(c);                          \
                unsigned l;                                         \
                for (l = 0; l < total; l++) {                       \
                    d->append(d, start);                            \
                    start += increment;                             \
                }                                                   \
            }                                                       \
        }                                                           \
                                                                    \
        /*split a to a,a*/                                          \
        a = TYPE##_new();                                           \
        base->copy(base, a);                                        \
        a->split(a, i, a, a);                                       \
        for (j = 0; j < arrays; j++)                                \
            assert(a->_[j]->equals(a->_[j], base->_[j]));           \
        a->del(a);                                                  \
                                                                    \
        /*split a to a,b*/                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        base->copy(base, a);                                        \
        a->split(a, i, a, b);                                       \
        for (j = 0; j < i; j++)                                     \
            assert(a->_[j]->equals(a->_[j], base->_[j]));           \
        for (j = 0; j < (arrays - i); j++)                          \
            assert(b->_[j]->equals(b->_[j], base->_[j + i]));       \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        /*split a to b,a*/                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        base->copy(base, a);                                        \
        a->split(a, i, b, a);                                       \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j]->equals(b->_[j], base->_[j]));           \
        for (j = 0; j < (arrays - i); j++)                          \
            assert(a->_[j]->equals(a->_[j], base->_[j + i]));       \
        a->del(a);                                                  \
        b->del(b);                                                  \
                                                                    \
        /*split a to b,c*/                                          \
        a = TYPE##_new();                                           \
        b = TYPE##_new();                                           \
        c = TYPE##_new();                                           \
        base->copy(base, a);                                        \
        a->split(a, i, b, c);                                       \
        for (j = 0; j < i; j++)                                     \
            assert(b->_[j]->equals(b->_[j], base->_[j]));           \
        for (j = 0; j < (arrays - i); j++)                          \
            assert(c->_[j]->equals(c->_[j], base->_[j + i]));       \
        a->del(a);                                                  \
        b->del(b);                                                  \
        c->del(c);                                                  \
                                                                    \
        base->del(base);                                            \
    }                                                               \
                                                                    \
    /*test reverse*/                                                \
    a = TYPE##_new();                                               \
    b = TYPE##_new();                                               \
    for (i = 0; i < arrays; i++) {                                  \
        A_TYPE *c = a->append(a);                                   \
        unsigned j;                                                 \
                                                                    \
        for (j = 0; j < sub_arrays; j++) {                          \
            AA_TYPE* d = c->append(c);                              \
            unsigned k;                                             \
            for (k = 0; k < total; k++) {                           \
                d->append(d, start);                                \
                start += increment;                                 \
            }                                                       \
        }                                                           \
    }                                                               \
    a->copy(a, b);                                                  \
    a->reverse(a);                                                  \
    for (i = 0; i < arrays; i++) {                                  \
        assert(a->_[i]->equals(a->_[i], b->_[arrays - i - 1]));     \
    }                                                               \
    a->del(a);                                                      \
    b->del(b);                                                      \
}

ARRAY_AA_TYPE_TEST(aaa_int, aa_int, a_int, int)
ARRAY_AA_TYPE_TEST(aaa_double, aa_double, a_double, double)

#endif
