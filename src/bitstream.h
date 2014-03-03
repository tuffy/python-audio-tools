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
#include <stdarg.h>
#include <limits.h>
#include "buffer.h"
#include "func_io.h"

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

/*a jump table state value which must be at least 9 bits wide*/
typedef int state_t;

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;
typedef enum {BR_FILE, BR_SUBSTREAM, BR_EXTERNAL} br_type;
typedef enum {BW_FILE, BW_EXTERNAL, BW_RECORDER, BW_ACCUMULATOR} bw_type;
typedef enum {BS_INST_UNSIGNED,
              BS_INST_SIGNED,
              BS_INST_UNSIGNED64,
              BS_INST_SIGNED64,
              BS_INST_SKIP,
              BS_INST_SKIP_BYTES,
              BS_INST_BYTES,
              BS_INST_ALIGN,
              BS_INST_EOF} bs_instruction_t;

typedef void (*bs_callback_f)(uint8_t, void*);

/*a stackable callback function,
  used by BitstreamReader and BitstreamWriter*/
struct bs_callback {
    void (*callback)(uint8_t, void*);
    void *data;
    struct bs_callback *next;
};

/*a stackable exception entry,
  used by BitstreamReader and BitstreamWriter*/
struct bs_exception {
    jmp_buf env;
    struct bs_exception *next;
};

/*a mark on the BitstreamReader's stream which can be rewound to*/
struct br_mark {
    union {
        fpos_t file;
        buf_pos_t substream;
        buf_pos_t external;
    } position;
    state_t state;
    struct br_mark *next;
};

/*a Huffman table entry indicating either a next node (if continue == 1)
  or final value and new context (if continue == 0)*/
struct br_huffman_table {
    int continue_;
    unsigned node;
    state_t state;
    int value;
};

/*******************************************************************
 *                          BitstreamReader                        *
 *******************************************************************/


typedef struct BitstreamReader_s {
    br_type type;

    union {
        FILE* file;
        struct bs_buffer* substream;
        struct br_external_input* external;
    } input;

    state_t state;
    struct bs_callback* callbacks;
    struct bs_exception* exceptions;
    struct br_mark* marks;

    struct bs_callback* callbacks_used;
    struct bs_exception* exceptions_used;
    struct br_mark* marks_used;

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to "count" bits wide*/
    unsigned int
    (*read)(struct BitstreamReader_s* bs, unsigned int count);

    /*returns "count" number of signed bits from the current stream
      in the current endian format up to "count" bits wide*/
    int
    (*read_signed)(struct BitstreamReader_s* bs, unsigned int count);

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to 64 bits wide*/
    uint64_t
    (*read_64)(struct BitstreamReader_s* bs, unsigned int count);

    /*returns "count" number of signed bits from the current stream
      in the current endian format up to 64 bits wide*/
    int64_t
    (*read_signed_64)(struct BitstreamReader_s* bs, unsigned int count);

    /*skips "count" number of bits from the current stream as if read

      callbacks are called on each skipped byte*/
    void
    (*skip)(struct BitstreamReader_s* bs, unsigned int count);

    /*skips "count" number of bytes from the current stream as if read

      callbacks are called on each skipped byte*/
    void
    (*skip_bytes)(struct BitstreamReader_s* bs, unsigned int count);

    /*pushes a single 0 or 1 bit back onto the stream
      in the current endian format

      only a single bit is guaranteed to be unreadable*/
    void
    (*unread)(struct BitstreamReader_s* bs, int unread_bit);

    /*returns the number of non-stop bits before the 0 or 1 stop bit
      from the current stream in the current endian format*/
    unsigned int
    (*read_unary)(struct BitstreamReader_s* bs, int stop_bit);

    /*skips the number of non-stop bits before the next 0 or 1 stop bit
      from the current stream in the current endian format*/
    void
    (*skip_unary)(struct BitstreamReader_s* bs, int stop_bit);

    /*returns the number of non-stop bits before the 0 or 1 stop bit
      from the current stream in the current endian format
      and limited to "maximum_bits"

      may return -1 if the maximum bits are exceeded*/
    int
    (*read_limited_unary)(struct BitstreamReader_s* bs, int stop_bit,
                          int maximum_bits);

    /*reads the next Huffman code from the stream
      where the code tree is defined from the given compiled table*/
    int
    (*read_huffman_code)(struct BitstreamReader_s* bs,
                         struct br_huffman_table table[][0x200]);

    /*aligns the stream to a byte boundary*/
    void
    (*byte_align)(struct BitstreamReader_s* bs);

    /*reads "byte_count" number of 8-bit bytes
      and places them in "bytes"

      the stream is not required to be byte-aligned,
      but reading will often be optimized if it is

      if insufficient bytes can be read, br_abort is called
      and the contents of "bytes" are undefined*/
    void
    (*read_bytes)(struct BitstreamReader_s* bs,
                  uint8_t* bytes,
                  unsigned int byte_count);

    /*takes a format string,
      performs the indicated read operations with prefixed numeric lengths
      and places the results in the given argument pointers
      where the format actions are:

      | format | action         | argument      |
      |--------+----------------+---------------|
      | u      | read           | unsigned int* |
      | s      | read_signed    | int*          |
      | U      | read_64        | uint64_t*     |
      | S      | read_signed_64 | int64_t*      |
      | p      | skip           | N/A           |
      | P      | skip_bytes     | N/A           |
      | b      | read_bytes     | uint8_t*      |
      | a      | byte_align     | N/A           |

      For example, one could read a 32 bit header as follows:

      unsigned int arg1; //  2 unsigned bits
      unsigned int arg2; //  3 unsigned bits
      int arg3;          //  5 signed bits
      unsigned int arg4; //  3 unsigned bits
      uint64_t arg5;     // 19 unsigned bits

      reader->parse(reader, "2u3u5s3u19U", &arg1, &arg2, &arg3, &arg4, &arg5);

      the "*" format multiplies the next format by the given amount
      For example, to read 4, signed 8 bit values:

      reader->parse(reader, "4* 8s", &arg1, &arg2, &arg3, &arg4);

      an I/O error during reading will trigger a call to br_abort
    */
    void
    (*parse)(struct BitstreamReader_s* bs, const char* format, ...);

    /*sets the stream's format to big endian or little endian
      which automatically byte aligns it*/
    void
    (*set_endianness)(struct BitstreamReader_s* bs,
                      bs_endianness endianness);

    /*closes the BistreamReader's internal stream

     * for FILE objects, performs fclose
     * for substreams, does nothing
     * for external input, calls its .close() method

     once the substream is closed,
     the reader's methods are updated to generate errors if called again*/
    void
    (*close_internal_stream)(struct BitstreamReader_s* bs);

    /*frees the BitstreamReader's allocated data

      for FILE objects, does nothing
      for substreams, deallocates buffer
      for external input, calls its .free() method

      deallocates any callbacks/used callbacks
      deallocates any exceptions/used exceptions
      deallocates any marks/used marks

      deallocates the bitstream struct*/
    void
    (*free)(struct BitstreamReader_s* bs);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamReader_s* bs);

    /*pushes a new mark onto to the stream, which can be rewound to later

      all pushed marks should be unmarked once no longer needed*/
    void
    (*mark)(struct BitstreamReader_s* bs);

    /*rewinds the stream to the next previous mark on the mark stack

      rewinding does not affect the mark itself*/
    void
    (*rewind)(struct BitstreamReader_s* bs);

    /*pops the previous mark from the mark stack

      unmarking does not affect the stream's current position*/
    void
    (*unmark)(struct BitstreamReader_s* bs);

    /*this appends the given length of bytes from the current stream
      to the given substream

      br_abort() is called if insufficient bytes
      are available on the input stream*/
    void
    (*substream_append)(struct BitstreamReader_s* bs,
                        struct BitstreamReader_s* substream,
                        unsigned bytes);
} BitstreamReader;


/*************************************************************
   Bitstream Reader Function Matrix
   The read functions come in three input variants
   and two endianness variants named in the format:

   br_function_x_yy

   where "x" is "f" for raw file, "s" for substream
   or "e" for external functions
   and "yy" is "be" for big endian or "le" for little endian.
   For example:

   | Function          | Input     | Endianness    |
   |-------------------+-----------+---------------|
   | br_read_bits_f_be | raw file  | big endian    |
   | br_read_bits_f_le | raw file  | little endian |
   | br_read_bits_s_be | substream | big endian    |
   | br_read_bits_s_le | substream | little endian |
   | br_read_bits_e_be | function  | big endian    |
   | br_read_bits_e_le | function  | little endian |

 *************************************************************/


/*BistreamReader open functions*/
BitstreamReader*
br_open(FILE *f, bs_endianness endianness);

BitstreamReader*
br_substream_new(bs_endianness endianness);

/*int read(void* user_data, struct bs_buffer* buffer)
  where "buffer" is where read output will be placed
  using buf_putc, buf_append, etc.

  note that "buffer" may already be holding data
  (especially if a mark is in place)
  so new data read to the buffer should be appended
  rather than replacing what's already there

  returns 0 on a successful read, 1 on a read error
  "size" will be set to 0 once EOF is reached


  void close(void* user_data)
  called when the stream is closed


  void free(void* user_data)
  called when the stream is deallocated
*/
BitstreamReader*
br_open_external(void* user_data,
                 bs_endianness endianness,
                 unsigned buffer_size,
                 ext_read_f read,
                 ext_close_f close,
                 ext_free_f free);

/*this is much like br_substream_new
  except that the buffer is passed in externally
  and *not* freed when the stream is*/
BitstreamReader*
br_open_buffer(struct bs_buffer* buffer, bs_endianness endianness);


/*bs->read(bs, count)  methods*/
unsigned int
br_read_bits_f_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_f_le(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_s_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_s_le(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_e_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_e_le(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_c(BitstreamReader* bs, unsigned int count);

/*bs->read_signed(bs, count)  methods*/
int
br_read_signed_bits_be(BitstreamReader* bs, unsigned int count);
int
br_read_signed_bits_le(BitstreamReader* bs, unsigned int count);


/*bs->read_64(bs, count)  methods*/
uint64_t
br_read_bits64_f_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_f_le(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_s_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_s_le(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_e_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_e_le(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_c(BitstreamReader* bs, unsigned int count);


/*bs->read_signed_64(bs, count)  methods*/
int64_t
br_read_signed_bits64_be(BitstreamReader* bs, unsigned int count);
int64_t
br_read_signed_bits64_le(BitstreamReader* bs, unsigned int count);


/*bs->skip(bs, count)  methods*/
void
br_skip_bits_f_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_f_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_s_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_s_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_e_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_e_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_c(BitstreamReader* bs, unsigned int count);


/*bs->skip_bytes(bs, count)  method*/
void
br_skip_bytes(BitstreamReader* bs, unsigned int count);


/*bs->unread(bs, unread_bit)  methods*/
void
br_unread_bit_be(BitstreamReader* bs, int unread_bit);
void
br_unread_bit_le(BitstreamReader* bs, int unread_bit);
void
br_unread_bit_c(BitstreamReader* bs, int unread_bit);

/*bs->read_unary(bs, stop_bit)  methods*/
unsigned int
br_read_unary_f_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_f_le(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_s_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_s_le(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_e_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_e_le(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_c(BitstreamReader* bs, int stop_bit);


/*bs->skip_unary(bs, stop_bit)  methods*/
void
br_skip_unary_f_be(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_f_le(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_s_be(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_s_le(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_e_be(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_e_le(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_c(BitstreamReader* bs, int stop_bit);


/*bs->read_limited_unary(bs, stop_bit, maximum_bits)  methods*/
int
br_read_limited_unary_f_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_f_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_s_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_s_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_e_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_e_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_c(BitstreamReader* bs, int stop_bit, int maximum_bits);


/*bs->read_huffman_code(bs, table)  methods*/
int
br_read_huffman_code_f(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200]);
int
br_read_huffman_code_s(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200]);
int
br_read_huffman_code_e(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200]);
int
br_read_huffman_code_c(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200]);


/*bs->byte_align(bs)  method*/
void
br_byte_align(BitstreamReader* bs);


/*bs->read_bytes(bs, bytes, byte_count)  methods*/
void
br_read_bytes_f(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count);
void
br_read_bytes_s(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count);
void
br_read_bytes_e(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count);
void
br_read_bytes_c(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count);

/*bs->parse(bs, format, ...)  method*/
void
br_parse(struct BitstreamReader_s* stream, const char* format, ...);


/*bs->set_endianness(bs, endianness)  methods*/
void
br_set_endianness_f_be(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_f_le(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_s_be(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_s_le(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_e_be(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_e_le(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_c(BitstreamReader *bs, bs_endianness endianness);


/*converts all read methods to ones that generate I/O errors
  in the event someone tries to read from a stream
  after it's been closed*/
void
br_close_methods(BitstreamReader* bs);


/*bs->close_internal_stream(bs)  methods*/
void
br_close_internal_stream_f(BitstreamReader* bs);
void
br_close_internal_stream_s(BitstreamReader* bs);
void
br_close_internal_stream_e(BitstreamReader* bs);
void
br_close_internal_stream_c(BitstreamReader* bs);


/*bs->free(bs)  methods*/
void
br_free_f(BitstreamReader* bs);
void
br_free_s(BitstreamReader* bs);
void
br_free_e(BitstreamReader* bs);


/*bs->close(bs)  method*/
void
br_close(BitstreamReader* bs);


/*bs->mark(bs)  methods*/
void
br_mark_f(BitstreamReader* bs);
void
br_mark_s(BitstreamReader* bs);
void
br_mark_e(BitstreamReader* bs);
void
br_mark_c(BitstreamReader* bs);

/*bs->rewind(bs)  methods*/
void
br_rewind_f(BitstreamReader* bs);
void
br_rewind_s(BitstreamReader* bs);
void
br_rewind_e(BitstreamReader* bs);
void
br_rewind_c(BitstreamReader* bs);

/*bs->unmark(bs)  methods*/
void
br_unmark_f(BitstreamReader* bs);
void
br_unmark_s(BitstreamReader* bs);
void
br_unmark_e(BitstreamReader* bs);
void
br_unmark_c(BitstreamReader* bs);


/*bs->substream_append(bs, substream, bytes)  method*/
void
br_substream_append(struct BitstreamReader_s *stream,
                    struct BitstreamReader_s *substream,
                    unsigned bytes);


/*unattached, BitstreamReader functions*/


/*adds the given callback to BitstreamReader's callback stack*/
void
br_add_callback(BitstreamReader *bs, bs_callback_f callback, void *data);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were read from the input stream*/
void
br_call_callbacks(BitstreamReader *bs, uint8_t byte);

/*removes the most recently added callback, if any
  if "callback" is not NULL, the popped callback's data is copied to it
  for possible restoration via "br_push_callback"

  this is often paired with bs_push_callback in order
  to temporarily disable a callback, for example:

  br_pop_callback(reader, &saved_callback);  //save callback for later
  unchecksummed_value = bs->read(bs, 16);    //read a value
  br_push_callback(reader, &saved_callback); //restore saved callback
*/
#define br_pop_callback(bs, callback) __br_pop_callback((bs), (callback), __FILE__, __LINE__)

void
__br_pop_callback(BitstreamReader *bs, struct bs_callback *callback,
                  const char *file, int lineno);

/*pushes the given callback back onto the callback stack
  note that the data from "callback" is copied onto a new internal struct;
  it does not need to be allocated from the heap*/
void
br_push_callback(BitstreamReader *bs, struct bs_callback *callback);


/*Called by the read functions if one attempts to read past
  the end of the stream.
  If an exception stack is available (with br_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.
*/
void
br_abort(BitstreamReader *bs);


/*Sets up an exception stack for use by setjmp(3).
  The basic call procudure is as follows:

  if (!setjmp(*br_try(bs))) {
    - perform reads here -
  } else {
    - catch read exception here -
  }
  br_etry(bs);  - either way, pop handler off exception stack -

  The idea being to avoid cluttering our read code with lots
  and lots of error checking tests, but rather assign a spot
  for errors to go if/when they do occur.
 */
jmp_buf*
br_try(BitstreamReader *bs);

/*Pops an entry off the current exception stack.
 (ends a try, essentially)*/
#define br_etry(bs) __br_etry((bs), __FILE__, __LINE__)

void
__br_etry(BitstreamReader *bs, const char *file, int lineno);

static inline long
br_ftell(BitstreamReader *bs) {
    assert(bs->type == BR_FILE);
    return ftell(bs->input.file);
}

/*clears out the substream for possible reuse

  any marks are deleted and the stream is reset
  so that it can be appended to with fresh data*/
void
br_substream_reset(struct BitstreamReader_s *substream);


/*******************************************************************
 *                          BitstreamWriter                        *
 *******************************************************************/

/*this is a basic binary tree in which the most common values
  (those with the smallest amount of bits to write)
  occur at the top of the tree*/
struct bw_huffman_table {
    int value;

    unsigned int write_count;
    unsigned int write_value;

    struct bw_huffman_table* left;
    struct bw_huffman_table* right;
};

typedef struct BitstreamWriter_s {
    bw_type type;

    union {
        FILE* file;
        struct bs_buffer* buffer;
        unsigned int accumulator;
        struct bw_external_output* external;
    } output;

    unsigned int buffer_size;
    unsigned int buffer;

    struct bs_callback* callbacks;
    struct bs_exception* exceptions;

    struct bs_callback* callbacks_used;
    struct bs_exception* exceptions_used;

    /*writes the given value as "count" number of unsigned bits
      to the current stream*/
    void
    (*write)(struct BitstreamWriter_s* bs,
             unsigned int count,
             unsigned int value);

    /*writes the given value as "count" number of signed bits
      to the current stream*/
    void
    (*write_signed)(struct BitstreamWriter_s* bs,
                    unsigned int count,
                    int value);

    /*writes the given value as "count" number of unsigned bits
      to the current stream, up to 64 bits wide*/
    void
    (*write_64)(struct BitstreamWriter_s* bs,
                unsigned int count,
                uint64_t value);

    /*writes the given value as "count" number of signed bits
      to the current stream, up to 64 bits wide*/
    void
    (*write_signed_64)(struct BitstreamWriter_s* bs,
                       unsigned int count,
                       int64_t value);

    /*writes "byte_count" number of bytes to the output stream

      the stream is not required to be byte-aligned,
      but writing will often be optimized if it is*/
    void
    (*write_bytes)(struct BitstreamWriter_s* bs,
                   const uint8_t* bytes,
                   unsigned int byte_count);

    /*writes "value" number of non stop bits to the current stream
      followed by a single stop bit*/
    void
    (*write_unary)(struct BitstreamWriter_s* bs,
                   int stop_bit,
                   unsigned int value);

    /*writes "value" is a Huffman code to the stream
      where the code tree is defined from the given compiled table

      returns 0 on success, or 1 if the code is not found in the table*/
    int
    (*write_huffman_code)(struct BitstreamWriter_s* bs,
                          struct bw_huffman_table* table,
                          int value);

    /*if the stream is not already byte-aligned,
      pad it with 0 bits until it is*/
    void
    (*byte_align)(struct BitstreamWriter_s* bs);

    /*byte aligns the stream and sets its format
      to big endian or little endian*/
    void
    (*set_endianness)(struct BitstreamWriter_s* bs,
                      bs_endianness endianness);

    /*takes a format string,
      peforms the indicated write operations with prefixed numeric lengths
      using the values from the given arguments
      where the format actions are

      | format | action          | argument     |
      |--------+-----------------+--------------|
      | u      | write           | unsigned int |
      | s      | write_signed    | int          |
      | U      | write_64        | uint64_t     |
      | S      | write_signed_64 | int64_t      |
      | p      | skip            | N/A          |
      | P      | skip_bytes      | N/A          |
      | b      | write_bytes     | uint8_t*     |
      | a      | byte_align      | N/A          |

      For example, one could write a 32 bit header as follows:

      unsigned int arg1; //  2 unsigned bits
      unsigned int arg2; //  3 unsigned bits
      int arg3;          //  5 signed bits
      unsigned int arg4; //  3 unsigned bits
      uint64_t arg5;     // 19 unsigned bits

      writer->build(writer, "2u3u5s3u19U", arg1, arg2, arg3, arg4, arg5);

      the "*" format multiplies the next format by the given amount
      For example, to write 4, signed 8 bit values:

      reader->parse(reader, "4* 8s", arg1, arg2, arg3, arg4);

      this is designed to perform the inverse of a BitstreamReader->parse()
     */
    void
    (*build)(struct BitstreamWriter_s* bs, const char* format, ...);

    /*returns the total bits written to the stream thus far

      this applies only to recorder and accumulator streams -
      file-based streams must use a callback to keep track of
      that information*/
    unsigned int
    (*bits_written)(struct BitstreamWriter_s* bs);

    /*returns the total bytes written to the stream thus far

      this applies only to recorder and accumulator streams -
      file-based streams must use a callback to keep track of
      that information*/
    unsigned int
    (*bytes_written)(struct BitstreamWriter_s* bs);

    /*flushes the current output stream's pending data*/
    void
    (*flush)(struct BitstreamWriter_s* bs);

    /*flushes and closes the BitstreamWriter's internal stream

     * for FILE objects, performs fclose
     * for recorders, does nothing
     * for Python writers, flushes output and calls object's .close() method

     once the internal stream is closed,
     the writer's I/O methods are updated to generate errors if called again*/
    void
    (*close_internal_stream)(struct BitstreamWriter_s* bs);

    /*for recorders, deallocates buffer
      for Python writers, flushes output if necessary and decrefs Python object

      deallocates any callbacks

      frees BitstreamWriter struct*/
    void
    (*free)(struct BitstreamWriter_s* bs);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamWriter_s* bs);

} BitstreamWriter;


/*************************************************************
 Bitstream Writer Function Matrix
 The write functions come in three output variants
 and two endianness variants for file and recorder output:

 bw_function_x or bw_function_x_yy

 where "x" is "f" for raw file, "p" for Python, "r" for recorder
 or "a" for accumulator
 and "yy" is "be" for big endian or "le" for little endian.

 For example:

 | Function           | Output      | Endianness    |
 |--------------------+-------------+---------------|
 | bw_write_bits_f_be | raw file    | big endian    |
 | bw_write_bits_f_le | raw file    | little endian |
 | bw_write_bits_p_be | Python      | big endian    |
 | bw_write_bits_p_le | Python      | little endian |
 | bw_write_bits_r_be | recorder    | big endian    |
 | bw_write_bits_r_le | recorder    | little endian |
 | bw_write_bits_a    | accumulator | N/A           |

 *************************************************************/

/*BistreamWriter open functions*/
BitstreamWriter*
bw_open(FILE *f, bs_endianness endianness);

/*int write(const uint8_t *data, unsigned data_size, void *user_data)
  where "data" is the bytes to be written,
  "data_size" is the amount of bytes to write
  and "user_data" is some function-specific pointer
  returns 0 on a successful write, 1 on a write error

  void flush(void* user_data)
  flushes any pending data

  note that high-level flushing will
  perform ext_write() followed by ext_flush()
  so the latter can be a no-op if necessary


  void close(void* user_data)
  closes the stream for further writing


  void free(void* user_data)
  deallocates anything in user_data, if necessary
*/
BitstreamWriter*
bw_open_external(void* user_data,
                 bs_endianness endianness,
                 unsigned buffer_size,
                 ext_write_f write,
                 ext_flush_f flush,
                 ext_close_f close,
                 ext_free_f free);

BitstreamWriter*
bw_open_recorder(bs_endianness endianness);

BitstreamWriter*
bw_open_accumulator(bs_endianness endianness);



/*bs->write(bs, count, value)  methods*/
void
bw_write_bits_f_be(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_f_le(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_e_be(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_e_le(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_r_be(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_r_le(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_a(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_c(BitstreamWriter* bs, unsigned int count, unsigned int value);

/*bs->write_signed(bs, count, value)  methods*/
void
bw_write_signed_bits_f_p_r_be(BitstreamWriter* bs, unsigned int count,
                              int value);
void
bw_write_signed_bits_f_p_r_le(BitstreamWriter* bs, unsigned int count,
                              int value);
void
bw_write_signed_bits_a(BitstreamWriter* bs, unsigned int count, int value);
void
bw_write_signed_bits_c(BitstreamWriter* bs, unsigned int count, int value);


/*bs->write_64(bs, count, value)  methods*/
void
bw_write_bits64_f_be(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_f_le(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_e_be(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_e_le(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_r_be(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_r_le(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_a(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_c(BitstreamWriter* bs, unsigned int count, uint64_t value);


/*bs->write_signed_64(bs, count, value)  methods*/
void
bw_write_signed_bits64_f_p_r_be(BitstreamWriter* bs, unsigned int count,
                                int64_t value);
void
bw_write_signed_bits64_f_p_r_le(BitstreamWriter* bs, unsigned int count,
                                int64_t value);
void
bw_write_signed_bits64_a(BitstreamWriter* bs, unsigned int count,
                         int64_t value);
void
bw_write_signed_bits64_c(BitstreamWriter* bs, unsigned int count,
                         int64_t value);


/*bs->write_bytes(bs, bytes, byte_count)  methods*/
void
bw_write_bytes_f(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_e(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_r(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_a(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_c(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);


/*bs->write_unary(bs, stop_bit, value)  methods*/
void
bw_write_unary_f_p_r(BitstreamWriter* bs, int stop_bit, unsigned int value);
void
bw_write_unary_a(BitstreamWriter* bs, int stop_bit, unsigned int value);
void
bw_write_unary_c(BitstreamWriter* bs, int stop_bit, unsigned int value);


/*bs->write_huffman_code(bs, table, value)  methods*/
int
bw_write_huffman(BitstreamWriter* bs,
                 struct bw_huffman_table* table,
                 int value);

int
bw_write_huffman_c(BitstreamWriter* bs,
                   struct bw_huffman_table* table,
                   int value);


/*bs->byte_align(bs)  methods*/
void
bw_byte_align_f_p_r(BitstreamWriter* bs);
void
bw_byte_align_a(BitstreamWriter* bs);
void
bw_byte_align_c(BitstreamWriter* bs);


/*bs->set_endianness(bs, endianness)  methods*/
void
bw_set_endianness_f_be(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_f_le(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_e_be(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_e_le(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_r_be(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_r_le(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_a(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_c(BitstreamWriter* bs, bs_endianness endianness);


/*bs->build(bs, format, ...)  method*/
void
bw_build(struct BitstreamWriter_s* stream, const char* format, ...);

/*bs->bytes_written(bs)  method*/
unsigned int
bw_bytes_written(BitstreamWriter* bs);

/*bs->bits_written(bs)  methods*/
unsigned int
bw_bits_written_f_p_c(BitstreamWriter* bs);
unsigned int
bw_bits_written_r(BitstreamWriter* bs);
unsigned int
bw_bits_written_a(BitstreamWriter* bs);


/*bs->flush(bs)  methods*/
void
bw_flush_f(BitstreamWriter* bs);
void
bw_flush_r_a_c(BitstreamWriter* bs);
void
bw_flush_e(BitstreamWriter* bs);



void
bw_close_methods(BitstreamWriter* bs);


/*bs->close_internal_stream(bs)  methods*/
void
bw_close_internal_stream_f(BitstreamWriter* bs);
void
bw_close_internal_stream_r_a(BitstreamWriter* bs);
void
bw_close_internal_stream_e(BitstreamWriter* bs);
void
bw_close_internal_stream_c(BitstreamWriter* bs);


/*bs->free(bs)  methods*/
void
bw_free_f_a(BitstreamWriter* bs);
void
bw_free_r(BitstreamWriter* bs);
void
bw_free_e(BitstreamWriter* bs);


/*bs->close(bs)  method*/
void
bw_close(BitstreamWriter* bs);


/*unattached, BitstreamWriter functions*/


/*adds a callback function, which is called on every byte written

  the function's arguments are the written byte and a generic
  pointer to some other data structure
 */
void
bw_add_callback(BitstreamWriter* bs, bs_callback_f callback, void *data);

/*removes the most recently added callback, if any
  if "callback" is not NULL, the popped callback's data is copied to it
  for possible restoration via "bw_push_callback"

  this is often paired with bs_push_callback in order
  to temporarily disable a callback, for example:

  bw_pop_callback(writer, &saved_callback);  //save callback for later
  bs->write(bs, 16, 0xAB);                   //write a value
  bw_push_callback(writer, &saved_callback); //restore saved callback
*/

#define bw_pop_callback(bs, callback) __bw_pop_callback((bs), (callback), __FILE__, __LINE__)

void
__bw_pop_callback(BitstreamWriter* bs, struct bs_callback* callback,
                  const char *file, int lineno);

/*pushes the given callback back onto the callback stack
  note that the data from "callback" is copied onto a new internal struct;
  it does not need to be allocated from the heap*/
void
bw_push_callback(BitstreamWriter* bs, struct bs_callback* callback);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were written to the output stream*/
void
bw_call_callbacks(BitstreamWriter *bs, uint8_t byte);


/*Called by the write functions if a write failure is indicated.
  If an exception is available (with bw_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.*/
void
bw_abort(BitstreamWriter* bs);

/*Sets up an exception stack for use by setjmp(3).
  The basic call procudure is as follows:

  if (!setjmp(*bw_try(bs))) {
    - perform writes here -
  } else {
    - catch write exception here -
  }
  bw_etry(bs);  - either way, pop handler off exception stack -

  The idea being to avoid cluttering our write code with lots
  and lots of error checking tests, but rather assign a spot
  for errors to go if/when they do occur.
 */
jmp_buf*
bw_try(BitstreamWriter *bs);

/*Pops an entry off the current exception stack.
 (ends a try, essentially)*/
#define bw_etry(bs) __bw_etry((bs), __FILE__, __LINE__)

void
__bw_etry(BitstreamWriter *bs, const char *file, int lineno);


static inline int
bw_closed(BitstreamWriter* bs) {
    return (bs->write == bw_write_bits_c);
}

static inline int
bw_eof(BitstreamWriter* bs) {
    assert(bs->type == BW_FILE);
    return feof(bs->output.file);
}

static inline long
bw_ftell(BitstreamWriter* bs) {
    assert(bs->type == BW_FILE);
    return ftell(bs->output.file);
}

/*writes "total" number of bytes from "buffer" to "target"*/
void
bw_dump_bytes(BitstreamWriter* target,
              const uint8_t* buffer, unsigned int total);

/*extracts up to the first "bytes" number of bytes from "source"
  to "buffer", removes them from the recorder
  and returns the amount of bytes actually read*/
unsigned
bw_read(BitstreamWriter* source, uint8_t* buffer, unsigned bytes);

/*given a BitstreamWriter recorder "source",
  writes all of its recorded output to "target"*/
void
bw_rec_copy(BitstreamWriter* target, BitstreamWriter* source);

/*given a BitstreamWriter recorder "source",
  writes up to "total_bytes" of recorded output to "target"
  while any remaining records are sent to "remaining"

  if "remaining" is the same writer as "source",
  sent records will be removed leaving only the remainder

  if "target" or "remaining" are NULL, those outputs are ignored

  returns the total bytes dumped to "target"*/
unsigned int
bw_rec_split(BitstreamWriter* target,
             BitstreamWriter* remaining,
             BitstreamWriter* source,
             unsigned int total_bytes);

/*clear the recorded output and reset for new output*/
void
bw_reset_recorder(BitstreamWriter* bs);

static inline void
bw_reset_accumulator(BitstreamWriter* bs)
{
    assert(bs->type == BW_ACCUMULATOR);

    bs->output.accumulator = 0;
}

void
bw_swap_records(BitstreamWriter* a, BitstreamWriter* b);

/*******************************************************************
 *                          format handlers                        *
 *******************************************************************/

/*parses (or continues parsing) the given format string
  and places the results in the "times", "size" and "inst" variables*/
const char*
bs_parse_format(const char *format,
                unsigned *times, unsigned *size, bs_instruction_t *inst);

/*returns the size of the given format string in bits*/
unsigned
bs_format_size(const char* format);

/*returns the size of the given format string in bytes*/
unsigned
bs_format_byte_size(const char* format);

#ifndef STANDALONE
/*******************************************************************
 *                          Python-specific                        *
 *******************************************************************/

int br_read_python(PyObject *reader,
                   struct bs_buffer* buffer,
                   unsigned buffer_size);

int bw_write_python(PyObject* writer,
                    struct bs_buffer* buffer,
                    unsigned buffer_size);

void bw_flush_python(PyObject* writer);

void bs_close_python(PyObject* obj);

void bs_free_python_decref(PyObject* obj);

void bs_free_python_nodecref(PyObject* obj);

#endif

/*******************************************************************
 *                           miscellaneous                         *
 *******************************************************************/

/*a trivial callback which increments "total_bytes" as an unsigned int*/
void
byte_counter(uint8_t byte, unsigned* total_bytes);

#endif
