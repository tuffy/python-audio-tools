#include "array.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <float.h>
#include <assert.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

typedef int(*qsort_cmp)(const void *x, const void *y);

#define ARRAY_FUNC_DEFINITION(TYPE, CONTENT_TYPE, LINK_TYPE, CONTENT_TYPE_MIN, CONTENT_TYPE_MAX, CONTENT_TYPE_ACCUMULATOR, FORMAT_STRING)    \
struct TYPE##_s* TYPE##_new(void)                               \
{                                                               \
    struct TYPE##_s* a = malloc(sizeof(struct TYPE##_s));       \
    a->_ = malloc(sizeof(CONTENT_TYPE) * 1);                    \
    a->len = 0;                                                 \
    a->total_size = 1;                                          \
                                                                \
    a->del = TYPE##_del;                                        \
    a->resize = TYPE##_resize;                                  \
    a->resize_for = TYPE##_resize_for;                          \
    a->reset = TYPE##_reset;                                    \
    a->reset_for = TYPE##_reset_for;                            \
    a->append = TYPE##_append;                                  \
    a->vappend = TYPE##_vappend;                                \
    a->mappend = TYPE##_mappend;                                \
    a->vset = TYPE##_vset;                                      \
    a->mset = TYPE##_mset;                                      \
    a->extend = TYPE##_extend;                                  \
    a->equals = TYPE##_equals;                                  \
    a->min = TYPE##_min;                                        \
    a->max = TYPE##_max;                                        \
    a->sum = TYPE##_sum;                                        \
    a->copy = TYPE##_copy;                                      \
    a->link = TYPE##_link;                                      \
    a->swap = TYPE##_swap;                                      \
    a->head = TYPE##_head;                                      \
    a->tail = TYPE##_tail;                                      \
    a->de_head = TYPE##_de_head;                                \
    a->de_tail = TYPE##_de_tail;                                \
    a->split = TYPE##_split;                                    \
    a->concat = TYPE##_concat;                                  \
    a->reverse = TYPE##_reverse;                                \
    a->sort = TYPE##_sort;                                      \
    a->print = TYPE##_print;                                    \
                                                                \
    return a;                                                   \
}                                                               \
                                                                \
void TYPE##_del(TYPE *array)                                    \
{                                                               \
    free(array->_);                                             \
    free(array);                                                \
}                                                               \
                                                                \
void TYPE##_resize(TYPE *array, unsigned minimum)               \
{                                                               \
    if (minimum > array->total_size) {                          \
        array->total_size = minimum;                            \
        array->_ = realloc(array->_,                            \
                           sizeof(CONTENT_TYPE) * minimum);     \
    }                                                           \
}                                                               \
                                                                \
void TYPE##_resize_for(TYPE *array, unsigned additional_items)  \
{                                                               \
    array->resize(array, array->len + additional_items);        \
}                                                               \
                                                                \
void TYPE##_reset(TYPE *array)                                  \
{                                                               \
    array->len = 0;                                             \
}                                                               \
                                                                \
void TYPE##_reset_for(TYPE *array, unsigned minimum)            \
{                                                               \
    array->reset(array);                                        \
    array->resize(array, minimum);                              \
}                                                               \
                                                                \
void TYPE##_append(TYPE *array, CONTENT_TYPE value)             \
{                                                               \
    if (array->len == array->total_size)                        \
        array->resize(array, array->total_size * 2);            \
                                                                \
    array->_[array->len++] = value;                             \
}                                                               \
                                                                \
void TYPE##_vappend(TYPE *array, unsigned count, ...)           \
{                                                               \
    va_list ap;                                                 \
                                                                \
    array->resize(array, array->len + count);                   \
    va_start(ap, count);                                        \
    for (; count > 0; count--) {                                \
        const CONTENT_TYPE i = va_arg(ap, CONTENT_TYPE);        \
        array->_[array->len++] = i;                             \
    }                                                           \
    va_end(ap);                                                 \
}                                                               \
                                                                \
void TYPE##_mappend(TYPE *array, unsigned count, CONTENT_TYPE value) \
{                                                                    \
    array->resize(array, array->len + count);                        \
    for (; count > 0; count--) {                                     \
        array->_[array->len++] = value;                              \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_vset(TYPE *array, unsigned count, ...)                   \
{                                                                    \
    va_list ap;                                                      \
                                                                     \
    array->reset_for(array, count);                                  \
    va_start(ap, count);                                             \
    for (; count > 0; count--) {                                     \
        const CONTENT_TYPE i = va_arg(ap, CONTENT_TYPE);             \
        array->_[array->len++] = i;                                  \
    }                                                                \
    va_end(ap);                                                      \
}                                                                    \
                                                                     \
void TYPE##_mset(TYPE *array, unsigned count, CONTENT_TYPE value)    \
{                                                                    \
    array->reset_for(array, count);                                  \
    for (; count > 0; count--) {                                     \
        array->_[array->len++] = value;                              \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_extend(TYPE *array, const TYPE *to_add)                  \
{                                                                    \
    array->concat(array, to_add, array);                             \
}                                                                    \
                                                                     \
int TYPE##_equals(const TYPE *array, const TYPE *compare)            \
{                                                                    \
    assert(array->_ != NULL);                                        \
    assert(compare->_ != NULL);                                      \
    if (array->len == compare->len) {                                \
        return (memcmp(array->_, compare->_,                         \
                       sizeof(CONTENT_TYPE) * array->len) == 0);     \
    } else {                                                         \
        return 0;                                                    \
    }                                                                \
}                                                                    \
                                                                     \
CONTENT_TYPE TYPE##_min(const TYPE *array)                           \
{                                                                    \
    CONTENT_TYPE min = CONTENT_TYPE_MAX;                             \
    unsigned i;                                                      \
                                                                     \
    assert(array->_ != NULL);                                        \
    for (i = 0; i < array->len; i++)                                 \
    if (array->_[i] < min)                                           \
        min = array->_[i];                                           \
                                                                     \
    return min;                                                      \
}                                                                    \
                                                                     \
CONTENT_TYPE TYPE##_max(const TYPE *array)                           \
{                                                                    \
    CONTENT_TYPE max = CONTENT_TYPE_MIN;                             \
    unsigned i;                                                      \
                                                                     \
    assert(array->_ != NULL);                                        \
    for (i = 0; i < array->len; i++)                                 \
        if (array->_[i] > max)                                       \
            max = array->_[i];                                       \
                                                                     \
    return max;                                                      \
}                                                                    \
                                                                     \
CONTENT_TYPE TYPE##_sum(const TYPE *array)                           \
{                                                                    \
    CONTENT_TYPE accumulator = CONTENT_TYPE_ACCUMULATOR;             \
    const CONTENT_TYPE *data = array->_;                             \
    unsigned size = array->len;                                      \
    unsigned i;                                                      \
                                                                     \
    assert(array->_ != NULL);                                        \
    for (i = 0; i < size; i++)                                       \
        accumulator += data[i];                                      \
                                                                     \
    return accumulator;                                              \
}                                                                    \
                                                                     \
void TYPE##_copy(const TYPE *array, TYPE *copy)                      \
{                                                                    \
    if (array != copy) {                                             \
        copy->resize(copy, array->len);                              \
        memcpy(copy->_, array->_,                                    \
               array->len * sizeof(CONTENT_TYPE));                   \
        copy->len = array->len;                                      \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_link(const TYPE *array, LINK_TYPE *link)                 \
{                                                                    \
    link->_ = array->_;                                              \
    link->len = array->len;                                          \
}                                                                    \
                                                                     \
void TYPE##_swap(TYPE *array, TYPE *swap)                            \
{                                                                    \
    TYPE temp;                                                       \
    temp._ = array->_;                                               \
    temp.len = array->len;                                           \
    temp.total_size = array->total_size;                             \
    array->_ = swap->_;                                              \
    array->len = swap->len;                                          \
    array->total_size = swap->total_size;                            \
    swap->_ = temp._;                                                \
    swap->len = temp.len;                                            \
    swap->total_size = temp.total_size;                              \
}                                                                    \
                                                                     \
void TYPE##_head(const TYPE *array, unsigned count, TYPE *head)      \
{                                                                    \
    const unsigned to_copy = MIN(count, array->len);                 \
                                                                     \
    if (head != array) {                                             \
        head->resize(head, to_copy);                                 \
        memcpy(head->_, array->_, sizeof(CONTENT_TYPE) * to_copy);   \
        head->len = to_copy;                                         \
    } else {                                                         \
        head->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_tail(const TYPE *array, unsigned count, TYPE *tail)      \
{                                                                    \
    const unsigned to_copy = MIN(count, array->len);                 \
                                                                     \
    if (tail != array) {                                             \
        tail->resize(tail, to_copy);                                 \
        memcpy(tail->_, array->_ + (array->len - to_copy),           \
               sizeof(CONTENT_TYPE) * to_copy);                      \
        tail->len = to_copy;                                         \
    } else {                                                         \
        memmove(tail->_, array->_ + (array->len - to_copy),          \
                sizeof(CONTENT_TYPE) * to_copy);                     \
        tail->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_de_head(const TYPE *array, unsigned count, TYPE *tail)   \
{                                                                    \
    unsigned to_copy;                                                \
    count = MIN(count, array->len);                                  \
    to_copy = array->len - count;                                    \
                                                                     \
    if (tail != array) {                                             \
        tail->resize(tail, to_copy);                                 \
        memcpy(tail->_, array->_ + count,                            \
               sizeof(CONTENT_TYPE) * to_copy);                      \
        tail->len = to_copy;                                         \
    } else {                                                         \
        memmove(tail->_, array->_ + count,                           \
                sizeof(CONTENT_TYPE) * to_copy);                     \
        tail->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_de_tail(const TYPE *array, unsigned count, TYPE *head)   \
{                                                                    \
    unsigned to_copy;                                                \
    count = MIN(count, array->len);                                  \
    to_copy = array->len - count;                                    \
                                                                     \
    if (head != array) {                                             \
        head->resize(head, to_copy);                                 \
        memcpy(head->_, array->_,                                    \
               sizeof(CONTENT_TYPE) * to_copy);                      \
        head->len = to_copy;                                         \
    } else {                                                         \
        head->len = to_copy;                                         \
    }                                                                \
}                                                                    \
                                                                     \
void TYPE##_split(const TYPE *array, unsigned count, TYPE *head, TYPE *tail) \
{                                                                       \
    /*ensure we don't try to move too many items*/                  \
    const unsigned to_head = MIN(count, array->len);                \
    const unsigned to_tail = array->len - to_head;                  \
                                                                    \
    if ((head == array) && (tail == array)) {                       \
        /*do nothing*/                                              \
        return;                                                     \
    } else if (head == tail) {                                      \
        /*copy all data to head*/                                   \
        array->copy(array, head);                                   \
    } else if ((head != array) && (tail == array)) {                \
        /*move "count" values to head and shift the rest down*/     \
        head->resize(head, to_head);                                \
        memcpy(head->_, array->_, sizeof(CONTENT_TYPE) * to_head);  \
        head->len = to_head;                                        \
                                                                    \
        memmove(tail->_, array->_ + to_head,                        \
                sizeof(CONTENT_TYPE) * to_tail);                    \
        tail->len = to_tail;                                        \
    } else if ((head == array) && (tail != array)) {                \
        /*move "count" values from our end to tail and reduce our size*/ \
        tail->resize(tail, to_tail);                                \
        memcpy(tail->_, array->_ + to_head,                         \
               sizeof(CONTENT_TYPE) * to_tail);                     \
        tail->len = to_tail;                                        \
                                                                    \
        head->len = to_head;                                        \
    } else {                                                        \
        /*copy "count" values to "head" and the remainder to "tail"*/ \
        head->resize(head, to_head);                                \
        memcpy(head->_, array->_,                                   \
               sizeof(CONTENT_TYPE) * to_head);                     \
        head->len = to_head;                                        \
                                                                    \
        tail->resize(tail, to_tail);                                \
        memcpy(tail->_, array->_ + to_head,                         \
               sizeof(CONTENT_TYPE) * to_tail);                     \
        tail->len = to_tail;                                        \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_concat(const struct TYPE##_s *array,                    \
                   const struct TYPE##_s *tail,                     \
                   struct TYPE##_s *combined)                       \
{                                                                   \
    if (array == combined) {                                        \
        /*extend array with values from tail*/                      \
        combined->resize_for(combined, tail->len);                  \
        memcpy(combined->_ + combined->len,                         \
               tail->_,                                             \
               sizeof(CONTENT_TYPE) * tail->len);                   \
        combined->len += tail->len;                                 \
    } else {                                                        \
        /*concatenate array and tail to combined*/                  \
        combined->reset_for(combined, array->len + tail->len);      \
        memcpy(combined->_,                                         \
               array->_,                                            \
               sizeof(CONTENT_TYPE) * array->len);                  \
        memcpy(combined->_ + array->len,                            \
               tail->_,                                             \
               sizeof(CONTENT_TYPE) * tail->len);                   \
        combined->len = array->len + tail->len;                     \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_reverse(TYPE *array)                                    \
{                                                                   \
    unsigned i;                                                     \
    unsigned j;                                                     \
    CONTENT_TYPE *data = array->_;                                  \
                                                                    \
    if (array->len > 0) {                                           \
        for (i = 0, j = array->len - 1; i < j; i++, j--) {          \
            const CONTENT_TYPE x = data[i];                         \
            data[i] = data[j];                                      \
            data[j] = x;                                            \
        }                                                           \
    }                                                               \
}                                                                   \
                                                                    \
int TYPE##_cmp(const CONTENT_TYPE *x, const CONTENT_TYPE *y)        \
{                                                                   \
    return *x - *y;                                                 \
}                                                                   \
                                                                    \
void TYPE##_sort(TYPE *array)                                       \
{                                                                   \
    qsort(array->_, (size_t)(array->len),                           \
          sizeof(CONTENT_TYPE), (qsort_cmp)TYPE##_cmp);             \
}                                                                   \
                                                                    \
void TYPE##_print(const TYPE *array, FILE *output)                  \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    putc('[', output);                                              \
    if (array->len == 1) {                                          \
        fprintf(output, FORMAT_STRING, array->_[0]);                \
    } else if (array->len > 1) {                                    \
        for (i = 0; i < array->len - 1; i++)                        \
            fprintf(output, FORMAT_STRING ", ", array->_[i]);       \
        fprintf(output, FORMAT_STRING, array->_[i]);                \
    }                                                               \
    putc(']', output);                                              \
}                                                                   \
                                                                    \
struct LINK_TYPE##_s* LINK_TYPE##_new(void)                         \
{                                                                   \
    struct LINK_TYPE##_s* array =                                   \
        malloc(sizeof(struct LINK_TYPE##_s));                       \
    array->_ = NULL;                                                \
    array->len = 0;                                                 \
                                                                    \
    array->del = LINK_TYPE##_del;                                   \
    array->reset = LINK_TYPE##_reset;                               \
    array->equals = LINK_TYPE##_equals;                             \
    array->min = LINK_TYPE##_min;                                   \
    array->max = LINK_TYPE##_max;                                   \
    array->sum = LINK_TYPE##_sum;                                   \
    array->copy = LINK_TYPE##_copy;                                 \
    array->link = LINK_TYPE##_link;                                 \
    array->swap = LINK_TYPE##_swap;                                 \
    array->head = LINK_TYPE##_head;                                 \
    array->tail = LINK_TYPE##_tail;                                 \
    array->de_head = LINK_TYPE##_de_head;                           \
    array->de_tail = LINK_TYPE##_de_tail;                           \
    array->split = LINK_TYPE##_split;                               \
    array->print = LINK_TYPE##_print;                               \
                                                                    \
    return array;                                                   \
}                                                                   \
                                                                    \
void LINK_TYPE##_del(LINK_TYPE *array)                              \
{                                                                   \
    free(array);                                                    \
}                                                                   \
                                                                    \
void LINK_TYPE##_reset(LINK_TYPE *array)                            \
{                                                                   \
    array->len = 0;                                                 \
}                                                                   \
                                                                    \
int LINK_TYPE##_equals(const LINK_TYPE *array, const LINK_TYPE *compare) \
{                                                                   \
    assert(array->_ != NULL);                                       \
    assert(compare->_ != NULL);                                     \
    if (array->len == compare->len) {                               \
        return (memcmp(array->_, compare->_,                        \
                       sizeof(CONTENT_TYPE) * array->len) == 0);    \
    } else {                                                        \
        return 0;                                                   \
    }                                                               \
}                                                                   \
                                                                    \
CONTENT_TYPE LINK_TYPE##_min(const LINK_TYPE *array)                \
{                                                                   \
    CONTENT_TYPE min = CONTENT_TYPE_MAX;                            \
    unsigned i;                                                     \
                                                                    \
    assert(array->_ != NULL);                                       \
    for (i = 0; i < array->len; i++)                                \
    if (array->_[i] < min)                                          \
        min = array->_[i];                                          \
                                                                    \
    return min;                                                     \
}                                                                   \
                                                                    \
CONTENT_TYPE LINK_TYPE##_max(const LINK_TYPE *array)                \
{                                                                   \
    CONTENT_TYPE max = CONTENT_TYPE_MIN;                            \
    unsigned i;                                                     \
                                                                    \
    assert(array->_ != NULL);                                       \
    for (i = 0; i < array->len; i++)                                \
        if (array->_[i] > max)                                      \
            max = array->_[i];                                      \
                                                                    \
    return max;                                                     \
}                                                                   \
                                                                    \
CONTENT_TYPE LINK_TYPE##_sum(const LINK_TYPE *array)                \
{                                                                   \
    CONTENT_TYPE accumulator = CONTENT_TYPE_ACCUMULATOR;            \
    const CONTENT_TYPE *data = array->_;                            \
    unsigned size = array->len;                                     \
    unsigned i;                                                     \
                                                                    \
    assert(array->_ != NULL);                                       \
    for (i = 0; i < size; i++)                                      \
        accumulator += data[i];                                     \
                                                                    \
    return accumulator;                                             \
}                                                                   \
                                                                    \
void LINK_TYPE##_copy(const LINK_TYPE *array, TYPE *copy)           \
{                                                                   \
    copy->resize(copy, array->len);                                 \
    memcpy(copy->_, array->_, array->len * sizeof(CONTENT_TYPE));   \
    copy->len = array->len;                                         \
}                                                                   \
                                                                    \
void LINK_TYPE##_link(const LINK_TYPE *array, LINK_TYPE *link)      \
{                                                                   \
    link->_ = array->_;                                             \
    link->len = array->len;                                         \
}                                                                   \
                                                                    \
void LINK_TYPE##_swap(LINK_TYPE *array, LINK_TYPE *swap)            \
{                                                                   \
    LINK_TYPE temp;                                                 \
    temp._ = array->_;                                              \
    temp.len = array->len;                                          \
    array->_ = swap->_;                                             \
    array->len = swap->len;                                         \
    swap->_ = temp._;                                               \
    swap->len = temp.len;                                           \
}                                                                   \
                                                                    \
void LINK_TYPE##_head(const LINK_TYPE *array, unsigned count, LINK_TYPE *head) \
{                                                                   \
    const unsigned to_copy = MIN(count, array->len);                \
    assert(array->_ != NULL);                                       \
    head->_ = array->_;                                             \
    head->len = to_copy;                                            \
}                                                                   \
                                                                    \
void LINK_TYPE##_tail(const LINK_TYPE *array, unsigned count, LINK_TYPE *tail) \
{                                                                   \
    const unsigned to_copy = MIN(count, array->len);                \
    assert(array->_ != NULL);                                       \
    tail->_ = array->_ + (array->len - to_copy);                    \
    tail->len = to_copy;                                            \
}                                                                   \
                                                                    \
void LINK_TYPE##_de_head(const LINK_TYPE *array, unsigned count, LINK_TYPE *tail) \
{                                                                   \
    unsigned to_copy;                                               \
    assert(array->_ != NULL);                                       \
    count = MIN(count, array->len);                                 \
    to_copy = array->len - count;                                   \
                                                                    \
    tail->_ = array->_ + count;                                     \
    tail->len = to_copy;                                            \
}                                                                   \
                                                                    \
void LINK_TYPE##_de_tail(const LINK_TYPE *array, unsigned count, LINK_TYPE *head) \
{                                                                   \
    head->_ = array->_;                                             \
    head->len = array->len - MIN(count, array->len);                \
}                                                                   \
                                                                    \
void LINK_TYPE##_split(const LINK_TYPE *array, unsigned count,      \
                       LINK_TYPE *head, LINK_TYPE *tail)            \
{                                                                   \
    /*ensure we don't try to move too many items*/                  \
    const unsigned to_head = MIN(count, array->len);                \
    const unsigned to_tail = array->len - to_head;                  \
    assert(array->_ != NULL);                                       \
                                                                    \
    if ((head == array) && (tail == array)) {                       \
        /*do nothing*/                                              \
        return;                                                     \
    } else if (head == tail) {                                      \
        /*copy all data to head*/                                   \
        head->_ = array->_;                                         \
        head->len = array->len;                                     \
    } else {                                                        \
        head->_ = array->_;                                         \
        head->len = to_head;                                        \
        tail->_ = array->_ + to_head;                               \
        tail->len = to_tail;                                        \
    }                                                               \
}                                                                   \
                                                                    \
void LINK_TYPE##_print(const LINK_TYPE *array, FILE *output)        \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    putc('[', output);                                              \
    if (array->len == 1) {                                          \
        fprintf(output, FORMAT_STRING, array->_[0]);                \
    } else if (array->len > 1) {                                    \
        for (i = 0; i < array->len - 1; i++)                        \
            fprintf(output, FORMAT_STRING ", ", array->_[i]);       \
        fprintf(output, FORMAT_STRING, array->_[i]);                \
    }                                                               \
    putc(']', output);                                              \
}

ARRAY_FUNC_DEFINITION(a_int, int, l_int, INT_MIN, INT_MAX, 0, "%d")
ARRAY_FUNC_DEFINITION(a_double, double, l_double, DBL_MIN, DBL_MAX, 0.0, "%f")
ARRAY_FUNC_DEFINITION(a_unsigned, unsigned, l_unsigned, 0, UINT_MAX, 0, "%u")


#define ARRAY_A_FUNC_DEFINITION(TYPE, ARRAY_TYPE, COPY_METH)   \
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
void TYPE##_del(TYPE *array)                                   \
{                                                              \
    unsigned i;                                                \
                                                               \
    for (i = 0; i < array->total_size; i++)                    \
        array->_[i]->del(array->_[i]);                         \
                                                               \
    free(array->_);                                            \
    free(array);                                               \
}                                                              \
                                                               \
void TYPE##_resize(TYPE *array, unsigned minimum)              \
{                                                              \
    if (minimum > array->total_size) {                         \
        array->_ = realloc(array->_,                           \
                           sizeof(ARRAY_TYPE*) * minimum);     \
        while (array->total_size < minimum) {                  \
            array->_[array->total_size++] = ARRAY_TYPE##_new();     \
        }                                                           \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_reset(TYPE *array)                                      \
{                                                                   \
    unsigned i;                                                     \
    for (i = 0; i < array->total_size; i++)                         \
        array->_[i]->reset(array->_[i]);                            \
    array->len = 0;                                                 \
}                                                                   \
                                                                    \
ARRAY_TYPE* TYPE##_append(TYPE *array)                              \
{                                                                   \
    if (array->len == array->total_size)                            \
        array->resize(array, array->total_size * 2);                \
                                                                    \
    return array->_[array->len++];                                  \
}                                                                   \
                                                                    \
void TYPE##_extend(TYPE *array, const TYPE *to_add)                 \
{                                                                   \
    unsigned i;                                                     \
    const unsigned len = to_add->len;                               \
    for (i = 0; i < len; i++) {                                     \
        to_add->_[i]->COPY_METH(to_add->_[i], array->append(array)); \
    }                                                               \
}                                                                   \
                                                                    \
int TYPE##_equals(const TYPE *array, const TYPE *compare)           \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    if (array->len == compare->len) {                               \
        for (i = 0; i < array->len; i++)                            \
            if (!array->_[i]->equals(array->_[i], compare->_[i]))   \
                return 0;                                           \
                                                                    \
        return 1;                                                   \
    } else                                                          \
        return 0;                                                   \
}                                                                   \
                                                                    \
void TYPE##_copy(const TYPE *array, TYPE *copy)                     \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    if (array != copy) {                                            \
        copy->reset(copy);                                          \
        for (i = 0; i < array->len; i++)                            \
            array->_[i]->COPY_METH(array->_[i], copy->append(copy)); \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_swap(TYPE *array, TYPE *swap)                           \
{                                                                   \
    TYPE temp;                                                      \
    temp._ = array->_;                                              \
    temp.len = array->len;                                          \
    temp.total_size = array->total_size;                            \
    array->_ = swap->_;                                             \
    array->len = swap->len;                                         \
    array->total_size = swap->total_size;                           \
    swap->_ = temp._;                                               \
    swap->len = temp.len;                                           \
    swap->total_size = temp.total_size;                             \
}                                                                   \
                                                                    \
void TYPE##_split(const TYPE *array, unsigned count,                \
                  TYPE *head, TYPE *tail)                           \
{                                                                   \
    /*ensure we don't try to move too many items*/                  \
    unsigned to_head = MIN(count, array->len);                      \
    unsigned i;                                                     \
                                                                    \
    if ((head == array) && (tail == array)) {                       \
        /*do nothing*/                                              \
        return;                                                     \
    } else if ((head != array) && (tail == array)) {                \
        TYPE *temp;                                                 \
        /*move "count" values to head and shift the rest down*/     \
                                                                    \
        head->reset(head);                                          \
        for (i = 0; i < to_head; i++)                               \
            array->_[i]->swap(array->_[i], head->append(head));     \
                                                                    \
        temp = TYPE##_new();                                        \
        for (; i < array->len; i++)                                 \
            array->_[i]->swap(array->_[i], temp->append(temp));     \
                                                                    \
        temp->swap(temp, tail);                                     \
        temp->del(temp);                                            \
    } else if ((head == array) && (tail != array)) {                \
        /*move "count" values from our end to tail and reduce our size*/ \
                                                                    \
        tail->reset(tail);                                          \
        for (i = to_head; i < array->len; i++) {                    \
            array->_[i]->swap(array->_[i], tail->append(tail));     \
            array->_[i]->reset(array->_[i]);                        \
        }                                                           \
        head->len = to_head;                                        \
    } else {                                                        \
        /*copy "count" values to "head" and the remainder to "tail"*/ \
                                                                    \
        head->reset(head);                                          \
        tail->reset(tail);                                          \
        for (i = 0; i < to_head; i++)                               \
            array->_[i]->COPY_METH(array->_[i], head->append(head)); \
                                                                    \
        for (; i < array->len; i++)                                 \
            array->_[i]->COPY_METH(array->_[i], tail->append(tail)); \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_cross_split(const TYPE *array, unsigned count,          \
                        TYPE *head, TYPE *tail)                     \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    if ((head == array) && (tail == array)) {                       \
        /*do nothing*/                                              \
    } else if (head == tail) {                                      \
        array->copy(array, head);                                   \
    } else if ((head != array) && (tail == array)) {                \
        head->reset(head);                                          \
        for (i = 0; i < array->len; i++) {                          \
            array->_[i]->split(array->_[i],                         \
                               count,                               \
                               head->append(head),                  \
                               tail->_[i]);                         \
        }                                                           \
    } else if ((head == array) && (tail != array)) {                \
        tail->reset(tail);                                          \
        for (i = 0; i < array->len; i++) {                          \
            array->_[i]->split(array->_[i],                         \
                               count,                               \
                               head->_[i],                          \
                               tail->append(tail));                 \
        }                                                           \
    } else {                                                        \
        head->reset(head);                                          \
        tail->reset(tail);                                          \
        for (i = 0; i < array->len; i++) {                          \
            array->_[i]->split(array->_[i],                         \
                               count,                               \
                               head->append(head),                  \
                               tail->append(tail));                 \
        }                                                           \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_reverse(TYPE *array)                                    \
{                                                                   \
    unsigned i;                                                     \
    unsigned j;                                                     \
    ARRAY_TYPE **data = array->_;                                   \
                                                                    \
    if (array->len > 0) {                                           \
        for (i = 0, j = array->len - 1; i < j; i++, j--) {          \
            ARRAY_TYPE *x = data[i];                                \
            data[i] = data[j];                                      \
            data[j] = x;                                            \
        }                                                           \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_print(const TYPE *array, FILE *output)                  \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    putc('[', output);                                              \
    if (array->len == 1) {                                          \
        array->_[0]->print(array->_[0], output);                    \
    } else if (array->len > 1) {                                    \
        for (i = 0; i < array->len - 1; i++) {                      \
            array->_[i]->print(array->_[i], output);                \
            fprintf(output, ", ");                                  \
        }                                                           \
        array->_[i]->print(array->_[i], output);                    \
    }                                                               \
    putc(']', output);                                              \
}

ARRAY_A_FUNC_DEFINITION(aa_int, a_int, copy)
ARRAY_A_FUNC_DEFINITION(aa_double, a_double, copy)
ARRAY_A_FUNC_DEFINITION(al_int, l_int, link)
ARRAY_A_FUNC_DEFINITION(al_double, l_double, link)

#define ARRAY_AA_FUNC_DEFINITION(TYPE, ARRAY_TYPE, COPY_METH) \
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
void TYPE##_del(TYPE *array)                                  \
{                                                             \
    unsigned i;                                               \
                                                              \
    for (i = 0; i < array->total_size; i++)                   \
        array->_[i]->del(array->_[i]);                        \
                                                              \
    free(array->_);                                           \
    free(array);                                              \
}                                                             \
                                                              \
void TYPE##_resize(TYPE *array, unsigned minimum)             \
{                                                             \
    if (minimum > array->total_size) {                        \
        array->_ = realloc(array->_,                          \
                           sizeof(ARRAY_TYPE*) * minimum);    \
        while (array->total_size < minimum) {                 \
            array->_[array->total_size++] = ARRAY_TYPE##_new();     \
        }                                                           \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_reset(TYPE *array)                                      \
{                                                                   \
    unsigned i;                                                     \
    for (i = 0; i < array->total_size; i++)                         \
        array->_[i]->reset(array->_[i]);                            \
    array->len = 0;                                                 \
}                                                                   \
                                                                    \
ARRAY_TYPE* TYPE##_append(TYPE *array)                              \
{                                                                   \
    if (array->len == array->total_size)                            \
        array->resize(array, array->total_size * 2);                \
                                                                    \
    return array->_[array->len++];                                  \
}                                                                   \
                                                                    \
void TYPE##_extend(TYPE *array, const TYPE *to_add)                 \
{                                                                   \
    unsigned i;                                                     \
    const unsigned len = to_add->len;                               \
    for (i = 0; i < len; i++) {                                     \
        to_add->_[i]->COPY_METH(to_add->_[i], array->append(array)); \
    }                                                               \
}                                                                   \
int TYPE##_equals(const TYPE *array, const TYPE *compare)           \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    if (array->len == compare->len) {                               \
        for (i = 0; i < array->len; i++)                            \
            if (!array->_[i]->equals(array->_[i], compare->_[i]))   \
                return 0;                                           \
                                                                    \
        return 1;                                                   \
    } else                                                          \
        return 0;                                                   \
}                                                                   \
void TYPE##_copy(const TYPE *array, TYPE *copy)                     \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    if (array != copy) {                                            \
        copy->reset(copy);                                          \
        for (i = 0; i < array->len; i++)                            \
            array->_[i]->COPY_METH(array->_[i], copy->append(copy)); \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_swap(TYPE *array, TYPE *swap)                           \
{                                                                   \
    TYPE temp;                                                      \
    temp._ = array->_;                                              \
    temp.len = array->len;                                          \
    temp.total_size = array->total_size;                            \
    array->_ = swap->_;                                             \
    array->len = swap->len;                                         \
    array->total_size = swap->total_size;                           \
    swap->_ = temp._;                                               \
    swap->len = temp.len;                                           \
    swap->total_size = temp.total_size;                             \
}                                                                   \
                                                                    \
void TYPE##_split(const TYPE *array, unsigned count,                \
                  TYPE *head, TYPE *tail)                           \
{                                                                   \
    /*ensure we don't try to move too many items*/                  \
    unsigned to_head = MIN(count, array->len);                      \
    unsigned i;                                                     \
                                                                    \
    if ((head == array) && (tail == array)) {                       \
        /*do nothing*/                                              \
        return;                                                     \
    } else if ((head != array) && (tail == array)) {                \
        TYPE *temp;                                                 \
        /*move "count" values to head and shift the rest down*/     \
                                                                    \
        head->reset(head);                                          \
        for (i = 0; i < to_head; i++)                               \
            array->_[i]->swap(array->_[i], head->append(head));     \
                                                                    \
        temp = TYPE##_new();                                        \
        for (; i < array->len; i++)                                 \
            array->_[i]->swap(array->_[i], temp->append(temp));     \
                                                                    \
        temp->swap(temp, tail);                                     \
        temp->del(temp);                                            \
    } else if ((head == array) && (tail != array)) {                \
        /*move "count" values from our end to tail and reduce our size*/ \
                                                                    \
        tail->reset(tail);                                          \
        for (i = to_head; i < array->len; i++) {                    \
            array->_[i]->swap(array->_[i], tail->append(tail));     \
            array->_[i]->reset(array->_[i]);                        \
        }                                                           \
        head->len = to_head;                                        \
    } else {                                                        \
        /*copy "count" values to "head" and the remainder to "tail"*/ \
                                                                    \
        head->reset(head);                                          \
        tail->reset(tail);                                          \
        for (i = 0; i < to_head; i++)                               \
            array->_[i]->COPY_METH(array->_[i], head->append(head)); \
                                                                    \
        for (; i < array->len; i++)                                 \
            array->_[i]->COPY_METH(array->_[i], tail->append(tail)); \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_reverse(TYPE *array)                                    \
{                                                                   \
    unsigned i;                                                     \
    unsigned j;                                                     \
    ARRAY_TYPE **data = array->_;                                   \
                                                                    \
    if (array->len > 0) {                                           \
        for (i = 0, j = array->len - 1; i < j; i++, j--) {          \
            ARRAY_TYPE *x = data[i];                                \
            data[i] = data[j];                                      \
            data[j] = x;                                            \
        }                                                           \
    }                                                               \
}                                                                   \
                                                                    \
void TYPE##_print(const TYPE *array, FILE *output)                  \
{                                                                   \
    unsigned i;                                                     \
                                                                    \
    putc('[', output);                                              \
    if (array->len == 1) {                                          \
        array->_[0]->print(array->_[0], output);                    \
    } else if (array->len > 1) {                                    \
        for (i = 0; i < array->len - 1; i++) {                      \
            array->_[i]->print(array->_[i], output);                \
            fprintf(output, ", ");                                  \
        }                                                           \
        array->_[i]->print(array->_[i], output);                    \
    }                                                               \
    putc(']', output);                                              \
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

void
a_obj_del(struct a_obj_s *array)
{
    while (array->len) {
        array->free_obj(array->_[--array->len]);
    }
    free(array->_);
    free(array);
}

void a_obj_resize(a_obj *array, unsigned minimum)
{
    if (minimum > array->total_size) {
        array->total_size = minimum;
        array->_ = realloc(array->_, sizeof(void*) * minimum);
    }
}

void a_obj_resize_for(a_obj *array, unsigned additional_items)
{
    array->resize(array, array->len + additional_items);
}

void
a_obj_reset(struct a_obj_s *array)
{
    while (array->len) {
        array->free_obj(array->_[--array->len]);
    }
}

void a_obj_reset_for(a_obj *array, unsigned minimum)
{
    array->reset(array);
    array->resize(array, minimum);
}

void
a_obj_append(struct a_obj_s *array, void* value)
{
    if (array->len == array->total_size)
        array->resize(array, array->total_size * 2);

    array->_[array->len++] = array->copy_obj(value);
}

void a_obj_vappend(struct a_obj_s *array, unsigned count, ...)
{
    void* i;
    va_list ap;

    array->resize(array, array->len + count);
    va_start(ap, count);
    for (; count > 0; count--) {
        i = va_arg(ap, void*);
        array->_[array->len++] = array->copy_obj(i);
    }
    va_end(ap);
}

void
a_obj_mappend(struct a_obj_s *array, unsigned count, void* value)
{
    array->resize(array, array->len + count);
    for (; count > 0; count--) {
        array->_[array->len++] = array->copy_obj(value);
    }
}

void
a_obj_set(struct a_obj_s *array, unsigned index, void* value)
{
    assert(index < array->len);
    array->free_obj(array->_[index]);
    array->_[index] = array->copy_obj(value);
}

void a_obj_vset(struct a_obj_s *array, unsigned count, ...)
{
    void* i;
    va_list ap;

    array->reset_for(array, count);
    va_start(ap, count);
    for (; count > 0; count--) {
        i = va_arg(ap, void*);
        array->_[array->len++] = array->copy_obj(i);
    }
    va_end(ap);
}

void
a_obj_mset(struct a_obj_s *array, unsigned count, void* value)
{
    array->reset_for(array, count);
    for (; count > 0; count--) {
        array->_[array->len++] = array->copy_obj(value);
    }
}

void
a_obj_extend(struct a_obj_s *array, const struct a_obj_s *to_add)
{
    array->concat(array, to_add, array);
}

void
a_obj_copy(const struct a_obj_s *array, struct a_obj_s *copy)
{
    if (array != copy) {
        unsigned i;

        copy->reset_for(copy, array->len);
        for (i = 0; i < array->len; i++) {
            copy->_[copy->len++] = array->copy_obj(array->_[i]);
        }
    }
}

void
a_obj_swap(a_obj *array, a_obj *swap)
{
    a_obj temp;
    temp._ = array->_;
    temp.len = array->len;
    temp.total_size = array->total_size;
    array->_ = swap->_;
    array->len = swap->len;
    array->total_size = swap->total_size;
    swap->_ = temp._;
    swap->len = temp.len;
    swap->total_size = temp.total_size;
}

void
a_obj_head(const struct a_obj_s *array, unsigned count,
           struct a_obj_s *head)
{
    const unsigned to_copy = MIN(count, array->len);

    if (head != array) {
        unsigned i;
        head->reset_for(head, to_copy);
        for (i = 0; i < to_copy; i++) {
            head->_[head->len++] = array->copy_obj(array->_[i]);
        }
    } else {
        while (head->len > to_copy) {
            array->free_obj(head->_[--head->len]);
        }
    }
}

void
a_obj_tail(const struct a_obj_s *array, unsigned count,
           struct a_obj_s *tail)
{
    const unsigned to_copy = MIN(count, array->len);

    if (tail != array) {
        unsigned i;

        tail->reset_for(tail, to_copy);
        for (i = array->len - to_copy; i < array->len; i++) {
            tail->_[tail->len++] = array->copy_obj(array->_[i]);
        }
    } else {
        struct a_obj_s* temp = a_obj_new(array->copy_obj,
                                             array->free_obj,
                                             array->print_obj);
        unsigned i;
        temp->resize(temp, to_copy);
        for (i = array->len - to_copy; i < array->len; i++) {
            temp->_[temp->len++] = array->copy_obj(array->_[i]);
        }
        temp->swap(temp, tail);
        temp->del(temp);
    }
}

void
a_obj_de_head(const struct a_obj_s *array, unsigned count,
              struct a_obj_s *tail)
{
    array->tail(array, array->len - MIN(count, array->len), tail);
}

void
a_obj_de_tail(const struct a_obj_s *array, unsigned count,
                struct a_obj_s *head)
{
    array->head(array, array->len - MIN(count, array->len), head);
}

void
a_obj_split(const struct a_obj_s *array, unsigned count,
            struct a_obj_s *head, struct a_obj_s *tail)
{
    const unsigned to_head = MIN(count, array->len);
    const unsigned to_tail = array->len - to_head;

    if ((head == array) && (tail == array)) {
        /*do nothing*/
        return;
    } else if (head == tail) {
        /*copy all data to head*/
        array->copy(array, head);
    } else if ((head == array) && (tail != array)) {
        array->tail(array, to_tail, tail);
        array->head(array, to_head, head);
    } else {
        array->head(array, to_head, head);
        array->tail(array, to_tail, tail);
    }
}

void
a_obj_concat(const struct a_obj_s *array,
             const struct a_obj_s *tail,
             struct a_obj_s *combined)
{
    unsigned i;

    if (array == combined) {
        /*extend array with values from tail*/

        combined->resize_for(combined, tail->len);

        for (i = 0; i < tail->len; i++) {
            combined->_[combined->len++] = combined->copy_obj(tail->_[i]);
        }
    } else {
        /*concatenate array and tail to combined*/

        combined->reset_for(combined, array->len + tail->len);

        for (i = 0; i < array->len; i++) {
            combined->_[combined->len++] = combined->copy_obj(array->_[i]);
        }
        for (i = 0; i < tail->len; i++) {
            combined->_[combined->len++] = combined->copy_obj(tail->_[i]);
        }
    }
}

void
a_obj_print(const struct a_obj_s *array, FILE* output)
{
    unsigned i;
    putc('[', output);
    if (array->len == 1) {
        array->print_obj(array->_[0], output);
    } else if (array->len > 1) {
        for (i = 0; i < array->len - 1; i++) {
            array->print_obj(array->_[i], output);
            fprintf(output, ", ");
        }
        array->print_obj(array->_[i], output);
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
