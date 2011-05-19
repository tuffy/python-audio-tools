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
        uint32_t substream;
        uint32_t python;
    } position;
    int state;
    struct bs_mark *next;
};

struct bs_huffman_table {
    unsigned int context_node;
    int value;
};

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;

struct bs_buffer {
    uint8_t* buffer;
    uint32_t buffer_size;
    uint32_t buffer_total_size;
    uint32_t buffer_position;
    int mark_in_progress;
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
        struct bs_buffer* substream;
#ifndef STANDALONE
        struct bs_python_input* python;
#endif
    } input;

    int state;
    struct bs_callback* callbacks;
    struct bs_exception* exceptions;
    struct bs_mark* marks;

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to "count" bits wide*/
    unsigned int (*read)(struct Bitstream_s* bs, unsigned int count);

    /*returns "count" number of signed bits from the current stream
      in the current endian format up to "count" bits wide*/
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

    /*reads the next Huffman code from the stream
      where the code tree is defined from the given compiled table*/
    int (*read_huffman_code)(struct Bitstream_s* bs,
                             struct bs_huffman_table table[][0x200]);

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

    /*extracts a substream of the current stream with the given length

      this byte-aligns the current stream before extracting the substream
      and immediately calls any callbacks on the extracted bytes

      the substream must be closed when finished via
      substream->close(substream) to free any temporary space*/
    struct Bitstream_s* (*substream)(struct Bitstream_s* bs, uint32_t bytes);

    /*this appends the given length of bytes from the current stream
      to the given substream

      in all other respects, it works identically to the previous method*/
    void (*substream_append)(struct Bitstream_s* bs,
                             struct Bitstream_s* substream,
                             uint32_t bytes);
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


/*************************************************************
   Read Function Matrix
   The read functions come in three input variants
   and two endianness variants named in the format:

   bs_function_x_yy

   where "x" is "f" for raw file, "s" for substream or "p" for Python input
   and "yy" is "be" for big endian or "le" for little endian.
   For example:

   | Function          | Input     | Endianness    |
   |-------------------+-----------+---------------|
   | bs_read_bits_f_be | raw file  | big endian    |
   | bs_read_bits_f_le | raw file  | little endian |
   | bs_read_bits_s_be | substream | big endian    |
   | bs_read_bits_s_le | substream | little endian |
   | bs_read_bits_p_be | Python    | big endian    |
   | bs_read_bits_p_le | Python    | little endian |

 *************************************************************/

unsigned int
bs_read_bits_f_be(Bitstream* bs, unsigned int count);
unsigned int
bs_read_bits_f_le(Bitstream* bs, unsigned int count);
unsigned int
bs_read_bits_s_be(Bitstream* bs, unsigned int count);
unsigned int
bs_read_bits_s_le(Bitstream* bs, unsigned int count);
#ifndef STANDALONE
unsigned int
bs_read_bits_p_be(Bitstream* bs, unsigned int count);
unsigned int
bs_read_bits_p_le(Bitstream* bs, unsigned int count);
#endif


int
bs_read_signed_bits_f_be(Bitstream* bs, unsigned int count);
int
bs_read_signed_bits_f_le(Bitstream* bs, unsigned int count);
int
bs_read_signed_bits_s_be(Bitstream* bs, unsigned int count);
int
bs_read_signed_bits_s_le(Bitstream* bs, unsigned int count);
#ifndef STANDALONE
int
bs_read_signed_bits_p_be(Bitstream* bs, unsigned int count);
int
bs_read_signed_bits_p_le(Bitstream* bs, unsigned int count);
#endif


uint64_t
bs_read_bits64_f_be(Bitstream* bs, unsigned int count);
uint64_t
bs_read_bits64_f_le(Bitstream* bs, unsigned int count);
uint64_t
bs_read_bits64_s_be(Bitstream* bs, unsigned int count);
uint64_t
bs_read_bits64_s_le(Bitstream* bs, unsigned int count);
#ifndef STANDALONE
uint64_t
bs_read_bits64_p_be(Bitstream* bs, unsigned int count);
uint64_t
bs_read_bits64_p_le(Bitstream* bs, unsigned int count);
#endif


void
bs_skip_bits_f_be(Bitstream* bs, unsigned int count);
void
bs_skip_bits_f_le(Bitstream* bs, unsigned int count);
void
bs_skip_bits_s_be(Bitstream* bs, unsigned int count);
void
bs_skip_bits_s_le(Bitstream* bs, unsigned int count);
#ifndef STANDALONE
void
bs_skip_bits_p_be(Bitstream* bs, unsigned int count);
void
bs_skip_bits_p_le(Bitstream* bs, unsigned int count);
#endif


/*unread_bit has no file/substream/Python variants
  because it never makes calls to the input stream*/
void
bs_unread_bit_be(Bitstream* bs, int unread_bit);
void
bs_unread_bit_le(Bitstream* bs, int unread_bit);


unsigned int
bs_read_unary_f_be(Bitstream* bs, int stop_bit);
unsigned int
bs_read_unary_f_le(Bitstream* bs, int stop_bit);
unsigned int
bs_read_unary_s_be(Bitstream* bs, int stop_bit);
unsigned int
bs_read_unary_s_le(Bitstream* bs, int stop_bit);
#ifndef STANDALONE
unsigned int
bs_read_unary_p_be(Bitstream* bs, int stop_bit);
unsigned int
bs_read_unary_p_le(Bitstream* bs, int stop_bit);
#endif


int
bs_read_limited_unary_f_be(Bitstream* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_f_le(Bitstream* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_s_be(Bitstream* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_s_le(Bitstream* bs, int stop_bit, int maximum_bits);
#ifndef STANDALONE
int
bs_read_limited_unary_p_be(Bitstream* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_p_le(Bitstream* bs, int stop_bit, int maximum_bits);
#endif


/*This automatically flushes any current state,
  so make sure to call it while byte-aligned!*/
void
bs_set_endianness_f_be(Bitstream *bs, bs_endianness endianness);
void
bs_set_endianness_f_le(Bitstream *bs, bs_endianness endianness);
void
bs_set_endianness_s_be(Bitstream *bs, bs_endianness endianness);
void
bs_set_endianness_s_le(Bitstream *bs, bs_endianness endianness);
#ifndef STANDALONE
void
bs_set_endianness_p_be(Bitstream *bs, bs_endianness endianness);
void
bs_set_endianness_p_le(Bitstream *bs, bs_endianness endianness);
#endif


/*read_huffman_code has no endianness variants
  since that is determined when its jump table is compiled*/
int
bs_read_huffman_code_f(Bitstream *bs,
                       struct bs_huffman_table table[][0x200]);
int
bs_read_huffman_code_s(Bitstream *bs,
                       struct bs_huffman_table table[][0x200]);
#ifndef STANDALONE
int
bs_read_huffman_code_p(Bitstream *bs,
                       struct bs_huffman_table table[][0x200]);
#endif


/*none of the mark handling functions have endianness variants*/
void
bs_mark_f(Bitstream* bs);
void
bs_mark_s(Bitstream* bs);
#ifndef STANDALONE
void
bs_mark_p(Bitstream* bs);
#endif

void
bs_rewind_f(Bitstream* bs);
void
bs_rewind_s(Bitstream* bs);
#ifndef STANDALONE
void
bs_rewind_p(Bitstream* bs);
#endif

void
bs_unmark_f(Bitstream* bs);
void
bs_unmark_s(Bitstream* bs);
#ifndef STANDALONE
void
bs_unmark_p(Bitstream* bs);
#endif


/*byte_align doesn't have file *or* endianness variants*/
void
bs_byte_align_r(Bitstream* bs);


/*returns a new bs_buffer struct which can be appended to and read from
  it must be closed later*/
struct bs_buffer*
buf_new(void);

uint32_t
buf_size(struct bs_buffer *stream);

/*returns a pointer to the new position in the buffer
  where one can begin appending new data

  update stream->buffer_size upon successfully populating the buffer

  For example:

  new_data = buf_extend(buffer, 10);
  if (fread(new_data, sizeof(uint8_t), 10, input_file) == 10)
      buffer->buffer_size += 10;
  else
      //trigger error here

*/
uint8_t*
buf_extend(struct bs_buffer *stream, uint32_t data_size);

/*clears out the buffer for possible reuse

  resets the position, size and resets any marks in progress*/
void
buf_reset(struct bs_buffer *stream);

/*analagous to fgetc, returns EOF at the end of buffer*/
int
buf_getc(struct bs_buffer *stream);

/*deallocates buffer struct*/
void
buf_close(struct bs_buffer *stream);


struct Bitstream_s*
bs_substream_new(bs_endianness endianness);

/*clears out the substream for possible reuse

  any marks are deleted and the stream is reset
  so that it can be appended to with fresh data*/
void
bs_substream_reset(struct Bitstream_s *substream);

void
bs_close_stream_s(struct Bitstream_s *stream);

/*variants for the stream->substream(stream, bytes) method

  these work by calling bs_substream_new to generate a plain substream
  with the appropriate endianness,
  then calling substream_append to fill it with data
  before returning the result*/
struct Bitstream_s*
bs_substream_f_be(struct Bitstream_s *stream, uint32_t bytes);

struct Bitstream_s*
bs_substream_f_le(struct Bitstream_s *stream, uint32_t bytes);

#ifndef STANDALONE
struct Bitstream_s*
bs_substream_p_be(struct Bitstream_s *stream, uint32_t bytes);

struct Bitstream_s*
bs_substream_p_le(struct Bitstream_s *stream, uint32_t bytes);
#endif

struct Bitstream_s*
bs_substream_s_be(struct Bitstream_s *stream, uint32_t bytes);

struct Bitstream_s*
bs_substream_s_le(struct Bitstream_s *stream, uint32_t bytes);

/*variants for the stream->substream_append(stream, substream, bytes) method

  note that they have no endianness variants*/

/*appends from a FILE-based stream to the buffer*/
void
bs_substream_append_f(struct Bitstream_s *stream,
                      struct Bitstream_s *substream,
                      uint32_t bytes);

#ifndef STANDALONE
/*appends from a Python-based stream to the buffer*/
void
bs_substream_append_p(struct Bitstream_s *stream,
                      struct Bitstream_s *substream,
                      uint32_t bytes);
#endif

/*appends from one buffer to another buffer*/
void
bs_substream_append_s(struct Bitstream_s *stream,
                      struct Bitstream_s *substream,
                      uint32_t bytes);



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

#endif

#endif
