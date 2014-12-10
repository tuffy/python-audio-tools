/********************************************************
 Bitstream Library, a module for reading bits of data

 Copyright (C) 2007-2014  Brian Langenberger

 The Bitstream Library is free software; you can redistribute it and/or modify
 it under the terms of either:

   * the GNU Lesser General Public License as published by the Free
     Software Foundation; either version 3 of the License, or (at your
     option) any later version.

 or

   * the GNU General Public License as published by the Free Software
     Foundation; either version 2 of the License, or (at your option) any
     later version.

 or both in parallel, as here.

 The Bitstream Library is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 for more details.

 You should have received copies of the GNU General Public License and the
 GNU Lesser General Public License along with the GNU MP Library.  If not,
 see https://www.gnu.org/licenses/.
 *******************************************************/

#include <stdio.h>
#include <stdint.h>
#include <getopt.h>
#include <assert.h>
#include "array.h"

#define HELP_FORMAT "  %-15s %s\n"

struct state {
    unsigned size;
    unsigned value;
};

typedef uint16_t state_t;

void
unpack_state(state_t packed, struct state* unpacked);

state_t
pack_state(const struct state* unpacked);

int
last_state(const struct state* state);

a_int*
state_to_array(const struct state* state);

void
array_to_state(const a_int* array, struct state* state);

unsigned
array_to_unsigned(const a_int* array);

typedef void (*display_func_f)(FILE *output, const struct state* state);

void
read_bits_table_be_func(FILE *output, const struct state* state);
void
read_bits_table_le_func(FILE *output, const struct state* state);
void
unread_bit_table_be_func(FILE *output, const struct state* state);
void
unread_bit_table_le_func(FILE *output, const struct state* state);
void
read_unary_table_be_func(FILE *output, const struct state* state);
void
read_unary_table_le_func(FILE *output, const struct state* state);

void
read_bits_be_func(const struct state* state,
                  unsigned read_bits,
                  unsigned *value_size,
                  unsigned *value,
                  state_t *next_state);

void
read_bits_le_func(const struct state* state,
                  unsigned read_bits,
                  unsigned *value_size,
                  unsigned *value,
                  state_t *next_state);

void
unread_bit_be_func(const struct state* state,
                   int unread_bit,
                   int *limit_reached,
                   state_t *next_state);

void
unread_bit_le_func(const struct state* state,
                   int unread_bit,
                   int *limit_reached,
                   state_t *next_state);

void
read_unary_be_func(const struct state* state,
                   int stop_bit,
                   int *continue_,
                   unsigned *value,
                   state_t *next_state);

void
read_unary_le_func(const struct state* state,
                   int stop_bit,
                   int *continue_,
                   unsigned *value,
                   state_t *next_state);

int main(int argc, char *argv[])
{
    static int big_endian_arg = 0;
    static int little_endian_arg = 0;
    static int read_bits_table = 0;
    static int unread_bit_table = 0;
    static int read_unary_table = 0;

    static struct option long_options[] = {
        {"help", no_argument, 0, 'h'},
        {"be", no_argument, &big_endian_arg, 1},
        {"le", no_argument, &little_endian_arg, 1},
        {"rb", no_argument, &read_bits_table, 1},
        {"urb", no_argument, &unread_bit_table, 1},
        {"ru", no_argument, &read_unary_table, 1}
    };

    int option_index = 0;
    int c;
    state_t s;
    int big_endian;
    display_func_f display_func = NULL;

    do {
        c = getopt_long(argc, argv, "h", long_options, &option_index);
        switch (c) {
        case 'h':
            printf("Options:\n");
            printf(HELP_FORMAT, "-h, --help",
                   "show this help message and exit");
            printf(HELP_FORMAT, "--be",
                   "generate big-endian table (default)");
            printf(HELP_FORMAT, "--le",
                   "generate little-endian table");
            printf(HELP_FORMAT, "--rb",
                   "generate read_bits_table");
            printf(HELP_FORMAT, "--urb",
                   "generate unread_bit_table");
            printf(HELP_FORMAT, "--ru",
                   "generate read_unary_table");
            return 0;
        case '?':
            return 1;
        case 0:
        case -1:
        default:
            break;
        }
    } while (c != -1);

    if (!big_endian_arg && little_endian_arg) {
        big_endian = 0;
    } else {
        big_endian = 1;
    }

    if (read_bits_table) {
        display_func =
            big_endian ? read_bits_table_be_func : read_bits_table_le_func;
    } else if (unread_bit_table) {
        display_func =
            big_endian ? unread_bit_table_be_func : unread_bit_table_le_func;
    } else if (read_unary_table) {
        display_func =
            big_endian ? read_unary_table_be_func : read_unary_table_le_func;
    }

    if (display_func) {
        printf("{\n");
        for (s = 0; s <= 0x1FF; s++) {
            struct state state;
            unpack_state(s, &state);
            printf("/* state = 0x%X (%d bits, 0x%X buffer) */\n",
                   s, state.size, state.value);
            display_func(stdout, &state);
            if (!last_state(&state)) {
                printf(",");
            }
            printf("\n");
        }
        printf("}\n");
    }

    return 0;
}

void
unpack_state(state_t packed, struct state* unpacked)
{
    if ((packed == 0) || (packed == 1)) {
        unpacked->size = 0;
        unpacked->value = 0;
    } else {
        unsigned size;
        for (size = 8; size > 0; size--) {
            if (packed & (1 << size)) {
                unpacked->size = size;
                unpacked->value = packed % (1 << size);
                break;
            }
        }
    }
}

state_t
pack_state(const struct state* unpacked)
{
    if (unpacked->size) {
        return (1 << unpacked->size) | unpacked->value;
    } else {
        return 0;
    }
}

int
last_state(const struct state* state)
{
    return (state->size == 8) && (state->value == 0xFF);
}

a_int*
state_to_array(const struct state* state)
{
    a_int *array = a_int_new();
    unsigned i;
    array->resize_for(array, state->size);
    for (i = 0; i < state->size; i++) {
        a_append(array, state->value & (1 << i) ? 1 : 0);
    }
    return array;
}

void
array_to_state(const a_int* array, struct state* state)
{
    assert(array->len <= 8);
    state->size = array->len;
    state->value = array_to_unsigned(array);
}

unsigned
array_to_unsigned(const a_int* array)
{
    unsigned i;
    const unsigned array_len = array->len;
    unsigned accumulator = 0;
    for (i = 0; i < array_len; i++) {
        if (array->_[i]) {
            accumulator |= (1 << i);
        }
    }
    return accumulator;
}

#define FUNC_READ_BITS_TABLE(FUNC_NAME, READ_FUNC)            \
  void                                                        \
  FUNC_NAME(FILE *output, const struct state* state)          \
  {                                                           \
      unsigned read_bits;                                     \
      fprintf(output, "{");                                   \
      for (read_bits = 1; read_bits <= 8; read_bits++) {      \
          unsigned value_size;                                \
          unsigned value;                                     \
          state_t next_state;                                 \
          READ_FUNC(state, read_bits,                         \
                    &value_size, &value, &next_state);        \
          fprintf(output, "{%d, 0x%X, 0x%X}",                 \
                  value_size, value, next_state);             \
          if (read_bits < 8) {                                \
              fprintf(output, ",");                           \
          }                                                   \
      }                                                       \
      fprintf(output, "}");                                   \
  }
FUNC_READ_BITS_TABLE(read_bits_table_be_func, read_bits_be_func)
FUNC_READ_BITS_TABLE(read_bits_table_le_func, read_bits_le_func)


#define FUNC_UNREAD_BIT_TABLE(FUNC_NAME, UNREAD_FUNC)        \
   void                                                      \
   FUNC_NAME(FILE *output, const struct state* state)        \
   {                                                         \
       int unread_bit;                                       \
       fprintf(output, "{");                                 \
       for (unread_bit = 0; unread_bit <= 1; unread_bit++) { \
           int limit_reached;                                \
           state_t next_state;                               \
           UNREAD_FUNC(state, unread_bit,                    \
                       &limit_reached, &next_state);         \
           fprintf(output, "{%d, 0x%X}",                     \
                   limit_reached, next_state);               \
           if (unread_bit < 1) {                             \
                fprintf(output, ",");                        \
           }                                                 \
       }                                                     \
       fprintf(output, "}");                                 \
   }
FUNC_UNREAD_BIT_TABLE(unread_bit_table_be_func, unread_bit_be_func)
FUNC_UNREAD_BIT_TABLE(unread_bit_table_le_func, unread_bit_le_func)


#define FUNC_READ_UNARY_TABLE(FUNC_NAME, READ_FUNC)   \
  void                                                \
  FUNC_NAME(FILE *output, const struct state* state)  \
  {                                                   \
      int stop_bit;                                   \
      fprintf(output, "{");                           \
      for (stop_bit = 0; stop_bit <= 1; stop_bit++) { \
          int continue_;                              \
          unsigned value;                             \
          state_t next_state;                         \
          READ_FUNC(state, stop_bit,                  \
                    &continue_, &value, &next_state); \
          fprintf(output, "{%d, 0x%X, 0x%X}",         \
                  continue_, value, next_state);      \
          if (stop_bit < 1) {                         \
            fprintf(output, ",");                     \
          }                                           \
      }                                               \
      fprintf(output, "}");                           \
  }
FUNC_READ_UNARY_TABLE(read_unary_table_be_func, read_unary_be_func)
FUNC_READ_UNARY_TABLE(read_unary_table_le_func, read_unary_le_func)


void
read_bits_be_func(const struct state* state,
                  unsigned read_bits,
                  unsigned *value_size,
                  unsigned *value,
                  state_t *next_state)
{
    if (state->size) {
        a_int *bits = state_to_array(state);
        a_int *to_return = a_int_new();
        struct state next;

        /*chop off the least-significant "read_bits" from the bank*/
        bits->tail(bits, read_bits, to_return);

        /*use the remaining most-significant bits in the bank
          as our next state*/
        bits->de_tail(bits, read_bits, bits);

        /*convert arrays to values*/
        *value_size = to_return->len;
        *value = array_to_unsigned(to_return);
        array_to_state(bits, &next);
        *next_state = pack_state(&next);

        bits->del(bits);
        to_return->del(to_return);
    } else {
        *value_size = 0;
        *value = 0;
        *next_state = 0;
    }
}

void
read_bits_le_func(const struct state* state,
                  unsigned read_bits,
                  unsigned *value_size,
                  unsigned *value,
                  state_t *next_state)
{
    if (state->size) {
        a_int *bits = state_to_array(state);
        a_int *to_return = a_int_new();
        struct state next;

        /*chop off the most significant "read_bits" from the bank*/
        bits->head(bits, read_bits, to_return);

        /*use the remaining least significant bits in the bank
          as our next state*/
        bits->de_head(bits, read_bits, bits);

        /*convert arrays to values*/
        *value_size = to_return->len;
        *value = array_to_unsigned(to_return);
        array_to_state(bits, &next);
        *next_state = pack_state(&next);

        bits->del(bits);
        to_return->del(to_return);
    } else {
        *value_size = 0;
        *value = 0;
        *next_state = 0;
    }
}

void
unread_bit_be_func(const struct state* state,
                   int unread_bit,
                   int *limit_reached,
                   state_t *next_state)
{
    if (state->size < 8) {
        a_int *bits = state_to_array(state);
        struct state next;

        /*append new bit to most-significant field*/
        bits->append(bits, unread_bit);
        array_to_state(bits, &next);
        bits->del(bits);
        *limit_reached = 0;
        *next_state = pack_state(&next);
    } else {
        *limit_reached = 1;
        *next_state = pack_state(state);
    }
}

void
unread_bit_le_func(const struct state* state,
                   int unread_bit,
                   int *limit_reached,
                   state_t *next_state)
{
    if (state->size < 8) {
        a_int *bits = state_to_array(state);
        struct state next;

        /*prepend new bit to least-significant field*/
        bits->insert(bits, 0, unread_bit);
        array_to_state(bits, &next);
        bits->del(bits);
        *limit_reached = 0;
        *next_state = pack_state(&next);
    } else {
        *limit_reached = 1;
        *next_state = pack_state(state);
    }
}

void
read_unary_be_func(const struct state* state,
                   int stop_bit,
                   int *continue_,
                   unsigned *value,
                   state_t *next_state)
{
    if (state->size) {
        a_int *bits = state_to_array(state);
        *value = 0;
        unsigned i;

        /*check bits in bank from most significant to least significant
          until "stop_bit" is reached*/
        for (i = 0; i < bits->len; i++) {
            const unsigned index = bits->len - i - 1;
            if (bits->_[index] == stop_bit) {
                struct state next;

                /*use remaining bits as next state*/
                bits->head(bits, index, bits);
                *continue_ = 0;
                array_to_state(bits, &next);
                bits->del(bits);
                *next_state = pack_state(&next);
                return;
            } else {
                *value += 1;
            }
        }

        /*got to end of bits without hitting stop bit*/
        bits->del(bits);
        *continue_ = 1;
        *next_state = 0;
    } else {
        *continue_ = 1;
        *value = 0;
        *next_state = 0;
    }
}

void
read_unary_le_func(const struct state* state,
                   int stop_bit,
                   int *continue_,
                   unsigned *value,
                   state_t *next_state)
{
    if (state->size) {
        a_int *bits = state_to_array(state);
        *value = 0;
        unsigned i;

        /*check bits in bank from least significant to most significant
          until "stop_bit" is reached*/
        for (i = 0; i < bits->len; i++) {
            if (bits->_[i] == stop_bit) {
                struct state next;

                /*use remaining bits as next state*/
                bits->de_head(bits, i + 1, bits);
                *continue_ = 0;
                array_to_state(bits, &next);
                bits->del(bits);
                *next_state = pack_state(&next);
                return;
            } else {
                *value += 1;
            }
        }

        /*got to end of bits without hitting stop bit*/
        bits->del(bits);
        *continue_ = 1;
        *next_state = 0;
    } else {
        *continue_ = 1;
        *value = 0;
        *next_state = 0;
    }
}
