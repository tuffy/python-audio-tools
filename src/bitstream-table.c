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
#include <string.h>

#define HELP_FORMAT "  %-15s %s\n"

struct state {
    unsigned short size;
    /*bits from state where value[0] is least significant
      and value[7] is most significant*/
    unsigned short value[8];
};

typedef uint16_t state_t;

/*given a 9 bit unsigned integer, returns the unpacked state*/
void
unpack_state(state_t packed, struct state* unpacked);

/*packs the state as a 9 bit unsigned integer and returns it*/
state_t
pack_state(const struct state* unpacked);

void
state_print(FILE* output, const struct state* state);

/*returns a true value if the state is the last one possible*/
int
last_state(const struct state* state);

/*returns the state's value as an unsigned integer*/
unsigned
state_value(const struct state* unpacked);

unsigned
value_to_unsigned(const unsigned short value[], unsigned short len);

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
                   s, state.size, state_value(&state));
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
    } else {
        unsigned short size;
        for (size = 8; size > 0; size--) {
            if (packed & (1 << size)) {
                unsigned i;
                unpacked->size = size;
                for (i = 0; i < size; i++) {
                    unpacked->value[i] = (packed & (1 << i)) ? 1 : 0;
                }
                break;
            }
        }
    }
}

state_t
pack_state(const struct state* unpacked)
{
    if (unpacked->size) {
        state_t s = (1 << unpacked->size);
        unsigned short i;
        for (i = 0; i < unpacked->size; i++) {
            s |= (unpacked->value[i] << i);
        }
        return s;
    } else {
        return 0;
    }
}

void
state_print(FILE* output, const struct state* state)
{
    unsigned short i;
    fputs("[", output);
    for (i = 0; i < state->size; i++) {
        fprintf(output, "%hu", state->value[i]);
        if ((i + 1) < state->size) {
            fputs(",", output);
        }
    }
    fputs("]", output);
}

int
last_state(const struct state* state)
{
    const static unsigned short last[8] = {1,1,1,1,1,1,1,1};

    return (state->size == 8) &&
           (!memcmp(state->value, last, 8 * sizeof(unsigned short)));
}

unsigned
state_value(const struct state* unpacked)
{
    return value_to_unsigned(unpacked->value, unpacked->size);
}

unsigned
value_to_unsigned(const unsigned short value[], unsigned short len)
{
    unsigned u = 0;
    unsigned short i;
    for (i = 0; i < len; i++) {
        u |= (value[i] << i);
    }
    return u;
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
        if (read_bits >= state->size) {
            *value_size = state->size;
            *value = state_value(state);
            *next_state = 0;
        } else {
            struct state remaining;

            *value_size = read_bits;
            *value = value_to_unsigned(
                state->value + (state->size - read_bits), read_bits);

            remaining.size = state->size - read_bits;
            memcpy(remaining.value,
                   state->value,
                   remaining.size * sizeof(unsigned short));
            *next_state = pack_state(&remaining);
        }
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
        if (read_bits >= state->size) {
            *value_size = state->size;
            *value = state_value(state);
            *next_state = 0;
        } else {
            struct state remaining;

            *value_size = read_bits;
            *value = value_to_unsigned(state->value, read_bits);

            remaining.size = state->size - read_bits;
            memcpy(remaining.value,
                   state->value + read_bits,
                   remaining.size * sizeof(unsigned short));
            *next_state = pack_state(&remaining);
        }
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
        struct state next;

        /*append new bit to most-significant field*/
        next.size = state->size + 1;
        memcpy(next.value, state->value, state->size * sizeof(unsigned short));
        next.value[state->size] = unread_bit;
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
        struct state next;

        /*prepend new bit to least-significant field*/
        next.size = state->size + 1;
        memcpy(next.value + 1,
               state->value,
               state->size * sizeof(unsigned short));
        next.value[0] = unread_bit;
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
        unsigned i;
        *value = 0;

        /*check bits in bank from most significant to least significant
          until "stop_bit" is reached*/
        for (i = 0; i < state->size; i++) {
            const unsigned index = state->size - i - 1;
            if (state->value[index] == stop_bit) {
                struct state next;

                /*use remaining bits as next state*/
                next.size = index;
                memcpy(next.value,
                       state->value,
                       next.size * sizeof(unsigned short));

                *continue_ = 0;
                *next_state = pack_state(&next);
                return;
            } else {
                *value += 1;
            }
        }

        /*got to end of bits without hitting stop bit*/
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
        unsigned i;
        *value = 0;

        /*check bits in bank from least significant to most significant
          until "stop_bit" is reached*/
        for (i = 0; i < state->size; i++) {
            if (state->value[i] == stop_bit) {
                struct state next;

                /*use remaining bits as next state*/
                next.size = state->size - i - 1;
                memcpy(next.value,
                       state->value + i + 1,
                       next.size * sizeof(unsigned short));

                *continue_ = 0;
                *next_state = pack_state(&next);
                return;
            } else {
                *value += 1;
            }
        }

        /*got to end of bits without hitting stop bit*/
        *continue_ = 1;
        *next_state = 0;
    } else {
        *continue_ = 1;
        *value = 0;
        *next_state = 0;
    }
}
