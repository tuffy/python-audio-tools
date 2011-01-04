#ifndef BITSTREAM_H
#define BITSTREAM_H
#ifndef STANDALONE
#include <Python.h>
#endif
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <setjmp.h>


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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

struct bs_callback {
    void (*callback)(uint8_t, void*);
    void *data;
    struct bs_callback *next;
};

struct bs_exception {
    jmp_buf env;
    struct bs_exception *next;
};

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;

#ifndef STANDALONE
struct bs_python_input {
    PyObject* reader_obj;
    uint8_t* buffer;
    uint32_t buffer_total_size;
    uint32_t buffer_size;
    uint32_t buffer_position;

    uint32_t marked_position;
    int mark_state;
    int mark_in_progress;
};
#endif

typedef struct Bitstream_s {
    union {
        struct {
            FILE* file;
            fpos_t mark;
            int mark_state;
        } stdio;
#ifndef STANDALONE
        struct bs_python_input* python;
#endif
    } input;

    int state;
    struct bs_callback* callback;
    struct bs_exception* exceptions;

    unsigned int (*read)(struct Bitstream_s* bs, unsigned int count);
    int (*read_signed)(struct Bitstream_s* bs, unsigned int count);
    uint64_t (*read_64)(struct Bitstream_s* bs, unsigned int count);
    void (*skip)(struct Bitstream_s* bs, unsigned int count);
    void (*unread)(struct Bitstream_s* bs, int unread_bit);
    unsigned int (*read_unary)(struct Bitstream_s* bs, int stop_bit);
    int (*read_limited_unary)(struct Bitstream_s* bs, int stop_bit,
                              int maximum_bits);
    void (*byte_align)(struct Bitstream_s* bs);
    void (*set_endianness)(struct Bitstream_s* bs,
                           bs_endianness endianness);
    void (*close)(struct Bitstream_s* bs);
    void (*mark)(struct Bitstream_s* bs);
    void (*rewind)(struct Bitstream_s* bs);
    void (*unmark)(struct Bitstream_s* bs);
} Bitstream;

Bitstream*
bs_open(FILE *f, bs_endianness endianness);

void
bs_close_f(Bitstream *bs);

void
bs_add_callback(Bitstream *bs, void (*callback)(uint8_t, void*),
                void *data);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were read from the input stream*/
void
bs_call_callbacks(Bitstream *bs, uint8_t byte);

/*removes the most recently added callback, if any*/
void
bs_pop_callback(Bitstream *bs);

static inline long
bs_ftell(Bitstream *bs) {
    return ftell(bs->input.stdio.file);
}


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

/*_be signifies the big-endian readers*/
unsigned int
bs_read_bits_be(Bitstream* bs, unsigned int count);

int
bs_read_signed_bits_be(Bitstream* bs, unsigned int count);

uint64_t
bs_read_bits64_be(Bitstream* bs, unsigned int count);

void
bs_skip_bits_be(Bitstream* bs, unsigned int count);

void
bs_unread_bit_be(Bitstream* bs, int unread_bit);

unsigned int
bs_read_unary_be(Bitstream* bs, int stop_bit);

int
bs_read_limited_unary_be(Bitstream* bs, int stop_bit, int maximum_bits);

void
bs_byte_align_r(Bitstream* bs);

/*This automatically flushes any current state,
  so make sure to call it while byte-aligned!*/
void
bs_set_endianness_be(Bitstream *bs, bs_endianness endianness);

/*_le signifies the little-endian readers*/
unsigned int
bs_read_bits_le(Bitstream* bs, unsigned int count);

uint64_t
bs_read_bits64_le(Bitstream* bs, unsigned int count);

int
bs_read_signed_bits_le(Bitstream* bs, unsigned int count);

void
bs_skip_bits_le(Bitstream* bs, unsigned int count);

void
bs_unread_bit_le(Bitstream* bs, int unread_bit);

unsigned int
bs_read_unary_le(Bitstream* bs, int stop_bit);

int
bs_read_limited_unary_le(Bitstream* bs, int stop_bit, int maximum_bits);

void
bs_set_endianness_le(Bitstream *bs, bs_endianness endianness);

/*mark a position in the bitstream which can be rewound to*/
void
bs_mark(Bitstream* bs);

/*return bitstream to previously marked position*/
void
bs_rewind(Bitstream* bs);

/*clear marked position in bitstream

  note that marking a position may require buffering lots of
  previously read data, so it's best not to hold a mark for too long
  unless you have a lot of memeory to spare*/
void
bs_unmark(Bitstream* bs);

#ifndef STANDALONE

/*given a file-like Python object with read() and close() methods,
  returns a newly allocated bs_python_input struct

  object is increfed*/
struct bs_python_input*
py_open(PyObject* reader);

/*analagous to fgetc, returns EOF at the end of stream
  or if some exception occurs when fetching from the reader object*/
int
py_getc(struct bs_python_input *stream);

/*closes the input stream and decrefs any objects*/
int
py_close(struct bs_python_input *stream);


Bitstream*
bs_open_python(PyObject *reader, bs_endianness endianness);

void
bs_close_p(Bitstream *bs);

/*_be signifies the big-endian readers*/
unsigned int
bs_read_bits_p_be(Bitstream* bs, unsigned int count);

int
bs_read_signed_bits_p_be(Bitstream* bs, unsigned int count);

uint64_t
bs_read_bits64_p_be(Bitstream* bs, unsigned int count);

void
bs_skip_bits_p_be(Bitstream* bs, unsigned int count);

unsigned int
bs_read_unary_p_be(Bitstream* bs, int stop_bit);

int
bs_read_limited_unary_p_be(Bitstream* bs, int stop_bit, int maximum_bits);


void
bs_set_endianness_p_be(Bitstream *bs, bs_endianness endianness);

/*_le signifies the little-endian readers*/
unsigned int
bs_read_bits_p_le(Bitstream* bs, unsigned int count);

uint64_t
bs_read_bits64_p_le(Bitstream* bs, unsigned int count);

int
bs_read_signed_bits_p_le(Bitstream* bs, unsigned int count);

void
bs_skip_bits_p_le(Bitstream* bs, unsigned int count);

unsigned int
bs_read_unary_p_le(Bitstream* bs, int stop_bit);

int
bs_read_limited_unary_p_le(Bitstream* bs, int stop_bit, int maximum_bits);

void
bs_set_endianness_p_le(Bitstream *bs, bs_endianness endianness);

void
bs_mark_p(Bitstream* bs);

void
bs_rewind_p(Bitstream* bs);

void
bs_unmark_p(Bitstream* bs);

#endif

#endif
