#include "array.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <float.h>
#include <assert.h>

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
        }                                                       \
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
    array->resize_for(array, to_add->len);                           \
    memcpy(array->_ + array->len,                                    \
           to_add->_,                                                \
           sizeof(CONTENT_TYPE) * to_add->len);                      \
    array->len += to_add->len;                                       \
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
    count = MAX(count, array->len);                                  \
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
    assert(array->_ != NULL);                                       \
    head->len = array->len - MAX(count, array->len);                \
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

ARRAY_FUNC_DEFINITION(array_i, int, array_li, INT_MIN, INT_MAX, 0, "%d")
ARRAY_FUNC_DEFINITION(array_f, double, array_lf, DBL_MIN, DBL_MAX, 0.0, "%f")
ARRAY_FUNC_DEFINITION(array_u, unsigned, array_lu, 0, UINT_MAX, 0, "%u")


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

ARRAY_A_FUNC_DEFINITION(array_ia, array_i, copy)
ARRAY_A_FUNC_DEFINITION(array_fa, array_f, copy)
ARRAY_A_FUNC_DEFINITION(array_lia, array_li, link)
ARRAY_A_FUNC_DEFINITION(array_lfa, array_lf, link)

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

ARRAY_AA_FUNC_DEFINITION(array_iaa, array_ia, copy)
ARRAY_AA_FUNC_DEFINITION(array_faa, array_fa, copy)


void*
array_o_dummy_copy(void* obj)
{
    return obj; /*does nothing*/
}

void
array_o_dummy_free(void* obj)
{
    return;     /*does nothing*/
}

void
array_o_dummy_print(void* obj, FILE* output)
{
    fprintf(output, "<OBJECT>");
}

struct array_o_s*
array_o_new(void* (*copy)(void* obj),
            void (*free)(void* obj),
            void (*print)(void* obj, FILE* output))
{
    struct array_o_s* a = malloc(sizeof(struct array_o_s));
    a->len = 0;
    a->total_size = 1;
    a->_ = malloc(sizeof(void*) * a->total_size);

    if (copy != NULL)
        a->copy_obj = copy;
    else
        a->copy_obj = array_o_dummy_copy;

    if (free != NULL)
        a->free_obj = free;
    else
        a->free_obj = array_o_dummy_free;

    if (print != NULL)
        a->print_obj = print;
    else
        a->print_obj = array_o_dummy_print;

    a->del = array_o_del;
    a->resize = array_o_resize;
    a->resize_for = array_o_resize_for;
    a->reset = array_o_reset;
    a->reset_for = array_o_reset_for;
    a->append = array_o_append;
    a->vappend = array_o_vappend;
    a->mappend = array_o_mappend;
    a->set = array_o_set;
    a->vset = array_o_vset;
    a->mset = array_o_mset;
    a->extend = array_o_extend;
    a->copy = array_o_copy;
    a->swap = array_o_swap;
    a->head = array_o_head;
    a->tail = array_o_tail;
    a->de_head = array_o_de_head;
    a->de_tail = array_o_de_tail;
    a->split = array_o_split;
    a->print = array_o_print;

    return a;
}

void
array_o_del(struct array_o_s *array)
{
    while (array->len) {
        array->free_obj(array->_[--array->len]);
    }
    free(array->_);
    free(array);
}

void array_o_resize(array_o *array, unsigned minimum)
{
    if (minimum > array->total_size) {
        array->total_size = minimum;
        array->_ = realloc(array->_, sizeof(void*) * minimum);
    }
}

void array_o_resize_for(array_o *array, unsigned additional_items)
{
    array->resize(array, array->len + additional_items);
}

void
array_o_reset(struct array_o_s *array)
{
    while (array->len) {
        array->free_obj(array->_[--array->len]);
    }
}

void array_o_reset_for(array_o *array, unsigned minimum)
{
    array->reset(array);
    array->resize(array, minimum);
}

void
array_o_append(struct array_o_s *array, void* value)
{
    if (array->len == array->total_size)
        array->resize(array, array->total_size * 2);

    array->_[array->len++] = array->copy_obj(value);
}

void array_o_vappend(struct array_o_s *array, unsigned count, ...)
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
array_o_mappend(struct array_o_s *array, unsigned count, void* value)
{
    array->resize(array, array->len + count);
    for (; count > 0; count--) {
        array->_[array->len++] = array->copy_obj(value);
    }
}

void
array_o_set(struct array_o_s *array, unsigned index, void* value)
{
    assert(index < array->len);
    array->free_obj(array->_[index]);
    array->_[index] = array->copy_obj(value);
}

void array_o_vset(struct array_o_s *array, unsigned count, ...)
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
array_o_mset(struct array_o_s *array, unsigned count, void* value)
{
    array->reset_for(array, count);
    for (; count > 0; count--) {
        array->_[array->len++] = array->copy_obj(value);
    }
}

void
array_o_extend(struct array_o_s *array, const struct array_o_s *to_add)
{
    unsigned i;
    const unsigned len = to_add->len;

    array->resize_for(array, to_add->len);

    for (i = 0; i < len; i++) {
        array->_[array->len++] = array->copy_obj(to_add->_[i]);
    }
}

void
array_o_copy(const struct array_o_s *array, struct array_o_s *copy)
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
array_o_swap(array_o *array, array_o *swap)
{
    array_o temp;
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
array_o_head(const struct array_o_s *array, unsigned count,
             struct array_o_s *head)
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
array_o_tail(const struct array_o_s *array, unsigned count,
             struct array_o_s *tail)
{
    const unsigned to_copy = MIN(count, array->len);

    if (tail != array) {
        unsigned i;

        tail->reset_for(tail, to_copy);
        for (i = array->len - to_copy; i < array->len; i++) {
            tail->_[tail->len++] = array->copy_obj(array->_[i]);
        }
    } else {
        struct array_o_s* temp = array_o_new(array->copy_obj,
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
array_o_de_head(const struct array_o_s *array, unsigned count,
                struct array_o_s *tail)
{
    array->tail(array, array->len - MIN(count, array->len), tail);
}

void
array_o_de_tail(const struct array_o_s *array, unsigned count,
                struct array_o_s *head)
{
    array->head(array, array->len - MIN(count, array->len), head);
}

void
array_o_split(const struct array_o_s *array, unsigned count,
              struct array_o_s *head, struct array_o_s *tail)
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
array_o_print(const struct array_o_s *array, FILE* output)
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
