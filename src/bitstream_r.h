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

struct bs_mark {
    union {
        fpos_t file;
        uint32_t python;
    } position;
    int state;
    struct bs_mark *next;
};

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;


struct bs_huffman_table {
    unsigned int context_node;
    int value;
};


#ifndef STANDALONE

struct bs_python_input {
    PyObject* reader_obj;
    uint8_t* buffer;
    uint32_t buffer_total_size;
    uint32_t buffer_size;
    uint32_t buffer_position;
    int mark_in_progress;
};
#endif

typedef struct Bitstream_s {
    union {
        FILE* file;
#ifndef STANDALONE
        struct bs_python_input* python;
#endif
    } input;

    int state;
    struct bs_callback* callbacks;
    struct bs_exception* exceptions;
    struct bs_mark* marks;

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to "int" bits wide*/
    unsigned int (*read)(struct Bitstream_s* bs, unsigned int count);

    /*returns "count" number of signed bits from the current stream
      in the current endian format up to "int" bits wide*/
    int (*read_signed)(struct Bitstream_s* bs, unsigned int count);

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to 64 bits wide*/
    uint64_t (*read_64)(struct Bitstream_s* bs, unsigned int count);

    /*skips "count" number of bits from the current stream*/
    void (*skip)(struct Bitstream_s* bs, unsigned int count);

    /*pushes a single 0 or 1 bit back onto the stream
      in the current endian format

      only a single bit is guaranteed to be unreadable*/
    void (*unread)(struct Bitstream_s* bs, int unread_bit);

    /*returns the number of non-stop bits before the 0 or 1 stop bit
      from the current stream in the current endian format*/
    unsigned int (*read_unary)(struct Bitstream_s* bs, int stop_bit);

    /*returns the number of non-stop bits before the 0 or 1 stop bit
      from the current stream in the current endian format
      and limited to "maximum_bits"

      may return -1 if the maximum bits are exceeded*/
    int (*read_limited_unary)(struct Bitstream_s* bs, int stop_bit,
                              int maximum_bits);

    int (*read_huffman_code)(struct Bitstream_s* bs,
                             const struct bs_huffman_table table[][0x200]);

    /*aligns the stream to a byte boundary*/
    void (*byte_align)(struct Bitstream_s* bs);

    /*sets the stream's format to big endian or little endian
      which automatically byte aligns it*/
    void (*set_endianness)(struct Bitstream_s* bs,
                           bs_endianness endianness);

    /*closes the current input stream
      and deallocates the struct*/
    void (*close)(struct Bitstream_s* bs);

    /*closes the current input stream
      but does *not* perform any other deallocation*/
    void (*close_stream)(struct Bitstream_s* bs);

    /*pushes a new mark onto to the stream, which can be rewound to later

      all pushed marks should be unmarked once no longer needed*/
    void (*mark)(struct Bitstream_s* bs);

    /*rewinds the stream to the next previous mark on the mark stack

      rewinding does not affect the mark itself*/
    void (*rewind)(struct Bitstream_s* bs);

    /*pops the previous mark from the mark stack*/
    void (*unmark)(struct Bitstream_s* bs);
} Bitstream;

Bitstream*
bs_open(FILE *f, bs_endianness endianness);

/*performs bs->close_stream followed by bs_free*/
void
bs_close(Bitstream *bs);

void
bs_close_stream_f(Bitstream *bs);

/*this deallocates space created by bs_open,
  but does *not* close any file handles*/
void
bs_free(Bitstream *bs);

/*does nothing, used to override existing functions at runtime*/
void
bs_noop(Bitstream *bs);

void
bs_add_callback(Bitstream *bs, void (*callback)(uint8_t, void*), void *data);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were read from the input stream*/
void
bs_call_callbacks(Bitstream *bs, uint8_t byte);

/*removes the most recently added callback, if any*/
void
bs_pop_callback(Bitstream *bs);

static inline long
bs_ftell(Bitstream *bs) {
    return ftell(bs->input.file);
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

int
bs_read_huffman_code(Bitstream *bs,
                     const struct bs_huffman_table table[][0x200]);

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

/*decrefs any objects and space, but does not close input stream*/
void
py_free(struct bs_python_input *stream);

Bitstream*
bs_open_python(PyObject *reader, bs_endianness endianness);

void
bs_close_stream_p(Bitstream *bs);

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

int
bs_read_huffman_code_p(Bitstream *bs,
                       const struct bs_huffman_table table[][0x200]);

void
bs_mark_p(Bitstream* bs);

void
bs_rewind_p(Bitstream* bs);

void
bs_unmark_p(Bitstream* bs);

#endif

#endif
