#ifndef BITSTREAM_H
#define BITSTREAM_H

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <setjmp.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

struct bs_callback {
    void (*callback)(int, void*);
    void *data;
    struct bs_callback *next;
};

struct bs_exception {
    jmp_buf env;
    struct bs_exception *next;
};

typedef struct Bitstream_s {
    FILE *file;
    int state;
    struct bs_callback *callback;
    struct bs_exception *exceptions;

    unsigned int (*read)(struct Bitstream_s* bs, unsigned int count);
    int (*read_signed)(struct Bitstream_s* bs, unsigned int count);
    uint64_t (*read_64)(struct Bitstream_s* bs, unsigned int count);
    void (*unread)(struct Bitstream_s* bs, int unread_bit);
    unsigned int (*read_unary)(struct Bitstream_s* bs, int stop_bit);
    int (*read_limited_unary)(struct Bitstream_s* bs, int stop_bit,
                              int maximum_bits);
    void (*byte_align)(struct Bitstream_s* bs);
} Bitstream;

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_alignment;

Bitstream*
bs_open(FILE *f, bs_alignment alignment);

void
bs_close(Bitstream *bs);

void
bs_add_callback(Bitstream *bs, void (*callback)(int, void*),
                void *data);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were read from the input stream*/
void
bs_call_callbacks(Bitstream *bs, int byte);

static inline long
bs_ftell(Bitstream *bs) {
    return ftell(bs->file);
}

/*Returns true if the stream is at EOF.*/
int
bs_eof(Bitstream *bs);


/*Called by the read functions if one attempts to read past
  the end of the stream.
  If an exception stack is available (with bs_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.
*/
void
bs_abort(Bitstream *bs);


/*Sets up an exception stack for use by setjmp(3).
  The basic call procudure is as follows:

  if (!setjmp(*bs_try(bs))) {
    - perform reads here -
  } else {
    - catch read exception here -
  }
  bs_etry(bs);  - either way, pop handler off exception stack -

  The idea being to avoid cluttering our read code with lots
  and lots of error checking tests, but rather assign a spot
  for errors to go if/when they do occur.
 */
jmp_buf*
bs_try(Bitstream *bs);


/*Pops an entry off the current exception stack.
 (ends a try, essentially)*/
void
bs_etry(Bitstream *bs);


typedef enum {BBW_WRITE_BITS,
              BBW_WRITE_SIGNED_BITS,
              BBW_WRITE_BITS64,
              BBW_WRITE_UNARY,
              BBW_BYTE_ALIGN} bbw_action;

typedef union {
    unsigned int count;
    int stop_bit;
} bbw_key;

typedef union {
    int value;
    uint64_t value64;
} bbw_value;

typedef struct {
    bbw_action *actions;
    bbw_key *keys;
    bbw_value *values;
    unsigned int size;
    unsigned int total_size;
    unsigned int bits_written;
} BitbufferW;

extern const unsigned int read_bits_table[0x900][8];
extern const unsigned int read_unary_table[0x900][2];
extern const unsigned int read_limited_unary_table[0x900][18];
extern const unsigned int unread_bit_table[0x900][2];

/*_be signifies the big-endian readers*/
unsigned int
bs_read_bits_be(Bitstream* bs, unsigned int count);

int
bs_read_signed_bits(Bitstream* bs, unsigned int count);

uint64_t
bs_read_bits64_be(Bitstream* bs, unsigned int count);

void
bs_unread_bit_be(Bitstream* bs, int unread_bit);

unsigned int
bs_read_unary_be(Bitstream* bs, int stop_bit);

int
bs_read_limited_unary_be(Bitstream* bs, int stop_bit, int maximum_bits);

void
bs_byte_align_r(Bitstream* bs);

/*_le signifies the little-endian readers*/

/*FIXME - add little endian reader defs here*/

#endif
