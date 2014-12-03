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

#ifndef __BITSTREAMLIB_H__
#define __BITSTREAMLIB_H__

#ifdef HAS_PYTHON
#include <Python.h>
#endif
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <limits.h>
#include "func_io.h"
#include "mini-gmp.h"

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

/*a jump table state value which must be at least 9 bits wide*/
typedef uint16_t state_t;

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;
typedef enum {BR_FILE, BR_BUFFER, BR_QUEUE, BR_EXTERNAL} br_type;
typedef enum {BW_FILE, BW_EXTERNAL, BW_RECORDER} bw_type;
typedef enum {BS_INST_UNSIGNED,
              BS_INST_SIGNED,
              BS_INST_UNSIGNED64,
              BS_INST_SIGNED64,
              BS_INST_UNSIGNED_BIGINT,
              BS_INST_SIGNED_BIGINT,
              BS_INST_SKIP,
              BS_INST_SKIP_BYTES,
              BS_INST_BYTES,
              BS_INST_ALIGN,
              BS_INST_EOF} bs_instruction_t;
typedef enum {BS_SEEK_SET=0,
              BS_SEEK_CUR=1,
              BS_SEEK_END=2} bs_whence;

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

struct BitstreamReader_s;
struct BitstreamQueue_s;
struct br_buffer;
struct br_queue;

/*a position on the BitstreamReader's stream which can be rewound to*/
typedef struct br_pos_s {
    /*our source reader
      attempting to setpos on some other reader will raise an error*/
    struct BitstreamReader_s *reader;

    /*the position in the stream*/
    union {
        fpos_t file;
        unsigned buffer;
        struct {
            unsigned pos;
            unsigned *pos_count;
        } queue;
        struct {
            void* pos;
            unsigned buffer_size;
            uint8_t* buffer;
            ext_free_pos_f free_pos;
        } external;
    } position;

    /*partial reader state*/
    state_t state;

    /*a function to delete position when finished with it*/
    void (*del)(struct br_pos_s *pos);
} br_pos_t;

/*a Huffman jump table entry

  if continue_ == 0, state indicates the BitstreamReader's new state
  and value indicates the value to be returned from the Huffman tree

  if continue_ == 1, node indicates the array index of the next
  br_huffman_table_t row of values to check against the current state*/
typedef struct {
    int continue_;
    unsigned node;
    state_t state;
    int value;
} br_huffman_entry_t;

/*a list of all the Huffman jump table entries for a given node
  where the current state is the index of which to use*/
typedef br_huffman_entry_t br_huffman_table_t[0x200];

/*typedefs for BitstreamReader methods

  One can pull them out of reader and use them like:

  br_read_f read = bitstreamreader->read;
  unsigned int value = read(bitstreamreader, bits);
*/

/*returns "count" number of unsigned bits from the current stream
  in the current endian format up to "count" bits wide*/
typedef unsigned int
(*br_read_f)(struct BitstreamReader_s* self, unsigned int count);

/*returns "count" number of signed bits from the current stream
  in the current endian format up to "count" bits wide*/
typedef int
(*br_read_signed_f)(struct BitstreamReader_s* self, unsigned int count);

/*returns "count" number of unsigned bits from the current stream
  in the current endian format up to 64 bits wide*/
typedef uint64_t
(*br_read_64_f)(struct BitstreamReader_s* self, unsigned int count);

/*returns "count" number of signed bits from the current stream
  in the current endian format up to 64 bits wide*/
typedef int64_t
(*br_read_signed_64_f)(struct BitstreamReader_s* self, unsigned int count);

/*reads "count" number of unsigned bits from the current stream
  to the given "value" in the current endian format
  "value" must have been initialized previously*/
typedef void
(*br_read_bigint_f)(struct BitstreamReader_s* self,
                    unsigned int count,
                    mpz_t value);

/*reads "count" number of signed bits from the current stream
  to the given "value" in the current endian format
  "value" must have been initialized previous*/
typedef void
(*br_read_signed_bigint_f)(struct BitstreamReader_s* self,
                           unsigned int count,
                           mpz_t value);

/*skips "count" number of bits from the current stream as if read
  callbacks are called on each skipped byte*/
typedef void
(*br_skip_f)(struct BitstreamReader_s* self, unsigned int count);

/*pushes a single 0 or 1 bit back onto the stream
  in the current endian format

  unread bits are stored in the local bit buffer but
  *not* pushed back into the stream itself
  so a different unread bit will be lost
  upon calls to seek or setpos, though getpos will preserve it

  only a single bit is guaranteed to be unreadable
  attempting to unread more than will fit in the buffer
  will trigger a br_abort()*/
typedef void
(*br_unread_f)(struct BitstreamReader_s* self, int unread_bit);

/*returns the number of non-stop bits before the 0 or 1 stop bit
  from the current stream in the current endian format*/
typedef unsigned int
(*br_read_unary_f)(struct BitstreamReader_s* self, int stop_bit);

/*skips the number of non-stop bits before the next 0 or 1 stop bit
  from the current stream in the current endian format*/
typedef void
(*br_skip_unary_f)(struct BitstreamReader_s* self, int stop_bit);

/*reads the next Huffman code from the stream
  where the code tree is defined from the given compiled table*/
typedef int
(*br_read_huffman_code_f)(struct BitstreamReader_s* self,
                          br_huffman_table_t table[]);

/*reads "byte_count" number of 8-bit bytes and places them in "bytes"

  the stream is not required to be byte-aligned,
  but reading will often be optimized if it is

  if insufficient bytes can be read, br_abort is called
  and the contents of "bytes" are undefined*/
typedef void
(*br_read_bytes_f)(struct BitstreamReader_s* self,
                   uint8_t* bytes,
                   unsigned int byte_count);

/*skips "count" number of bytes from the current stream as if read
  callbacks are called on each skipped byte*/
typedef void
(*br_skip_bytes_f)(struct BitstreamReader_s* self,
                   unsigned int byte_count);

/*returns a new pos instance which can be rewound to
  may call br_abort() if the position cannot be gotten
  or the stream is closed*/
typedef br_pos_t*
(*br_getpos_f)(struct BitstreamReader_s* self);

/*sets the stream's position from a pos instance
  may call br_abort() if the position cannot be set
  the stream is closed, or the position is from another stream*/
typedef void
(*br_setpos_f)(struct BitstreamReader_s* self, br_pos_t* pos);

/*moves the stream directly to the given location, in bytes,
  relative to the beginning, current or end of the stream

  no callbacks are called on the intervening bytes*/
typedef void
(*br_seek_f)(struct BitstreamReader_s* self,
             long position,
             bs_whence whence);

/*******************************************************************
 *                          BitstreamReader                        *
 *******************************************************************/

#define BITSTREAMREADER_TYPE                                             \
    bs_endianness endianness;                                            \
    br_type type;                                                        \
                                                                         \
    union {                                                              \
        FILE* file;                                                      \
        struct br_buffer* buffer;                                        \
        struct br_queue* queue;                                          \
        struct br_external_input* external;                              \
    } input;                                                             \
                                                                         \
    state_t state;                                                       \
    struct bs_callback* callbacks;                                       \
    struct bs_exception* exceptions;                                     \
    struct bs_exception* exceptions_used;                                \
                                                                         \
    br_read_f read;                                                      \
    br_read_signed_f read_signed;                                        \
    br_read_64_f read_64;                                                \
    br_read_signed_64_f read_signed_64;                                  \
    br_read_bigint_f read_bigint;                                        \
    br_read_signed_bigint_f read_signed_bigint;                          \
    br_skip_f skip;                                                      \
    br_unread_f unread;                                                  \
    br_read_unary_f read_unary;                                          \
    br_skip_unary_f skip_unary;                                          \
                                                                         \
    /*sets the stream's format to big endian or little endian*/          \
    /*which automatically byte aligns it*/                               \
    void                                                                 \
    (*set_endianness)(struct BitstreamReader_s* self,                    \
                      bs_endianness endianness);                         \
                                                                         \
    br_read_huffman_code_f read_huffman_code;                            \
    br_read_bytes_f read_bytes;                                          \
    br_skip_bytes_f skip_bytes;                                          \
                                                                         \
    /*takes a format string,*/                                           \
    /*performs the indicated read operations with prefixed numeric lengths*/ \
    /*and places the results in the given argument pointers*/            \
    /*where the format actions are:*/                                    \
                                                                         \
    /* | format | action             | argument      | */                \
    /* |--------+--------------------+---------------| */                \
    /* | u      | read               | unsigned int* | */                \
    /* | s      | read_signed        | int*          | */                \
    /* | U      | read_64            | uint64_t*     | */                \
    /* | S      | read_signed_64     | int64_t*      | */                \
    /* | K      | read_bigint        | mpz_t*        | */                \
    /* | L      | read_signed_bigint | mpz_t*        | */                \
    /* | p      | skip               | N/A           | */                \
    /* | P      | skip_bytes         | N/A           | */                \
    /* | b      | read_bytes         | uint8_t*      | */                \
    /* | a      | byte_align         | N/A           | */                \
                                                                         \
    /*For example, one could read a 32 bit header as follows:*/          \
                                                                         \
    /*unsigned int arg1; //  2 unsigned bits */                          \
    /*unsigned int arg2; //  3 unsigned bits */                          \
    /*int arg3;          //  5 signed bits   */                          \
    /*unsigned int arg4; //  3 unsigned bits */                          \
    /*uint64_t arg5;     // 19 unsigned bits */                          \
                                                                         \
    /*reader->parse(reader, "2u3u5s3u19U",              */               \
    /*              &arg1, &arg2, &arg3, &arg4, &arg5); */               \
                                                                         \
    /*the "*" format multiplies the next format by the given amount*/    \
    /*For example, to read 4, signed 8 bit values:*/                     \
                                                                         \
    /*reader->parse(reader, "4* 8s", &arg1, &arg2, &arg3, &arg4);*/      \
                                                                         \
    /*an I/O error during reading will trigger a call to br_abort*/      \
                                                                         \
    void                                                                 \
    (*parse)(struct BitstreamReader_s* self, const char* format, ...);   \
                                                                         \
    /*returns 1 if the stream is byte-aligned, 0 if not*/                \
    int                                                                  \
    (*byte_aligned)(const struct BitstreamReader_s* self);               \
                                                                         \
    /*aligns the stream to a byte boundary*/                             \
    void                                                                 \
    (*byte_align)(struct BitstreamReader_s* self);                       \
                                                                         \
    /*pushes a callback function into the stream*/                       \
    /*which is called on every byte read*/                               \
    void                                                                 \
    (*add_callback)(struct BitstreamReader_s* self,                      \
                    bs_callback_f callback,                              \
                    void* data);                                         \
                                                                         \
    /*pushes the given callback onto the callback stack*/                \
    /*data from "callback" is copied onto a new internal struct*/        \
    /*it does not need to be allocated from the heap*/                   \
    void                                                                 \
    (*push_callback)(struct BitstreamReader_s* self,                     \
                     struct bs_callback* callback);                      \
                                                                         \
    /*pops the most recently added callback from the stack*/             \
    /*if "callback" is not NULL, data from the popped callback*/         \
    /*is copied to that struct*/                                         \
    void                                                                 \
    (*pop_callback)(struct BitstreamReader_s* self,                      \
                    struct bs_callback* callback);                       \
                                                                         \
    /*explicitly call all set callbacks as if "byte" had been read*/     \
    /*from the input stream*/                                            \
    void                                                                 \
    (*call_callbacks)(struct BitstreamReader_s* self,                    \
                      uint8_t byte);                                     \
                                                                         \
    br_getpos_f getpos;                                                  \
    br_setpos_f setpos;                                                  \
    br_seek_f seek;                                                      \
                                                                         \
    /*creates a substream from the current stream*/                      \
    /*containing the given number of bytes*/                             \
    /*and with the input stream's endianness*/                           \
                                                                         \
    /*the substream must be freed when finished*/                        \
                                                                         \
    /*br_abort() is called if insufficient bytes*/                       \
    /*are available on the input stream*/                                \
    struct BitstreamReader_s*                                            \
    (*substream)(struct BitstreamReader_s* self, unsigned bytes);        \
                                                                         \
    /*reads the next given number of bytes from the current stream*/     \
    /*to the end of the given queue*/                                    \
                                                                         \
    /*br_abort() is called if insufficient bytes*/                       \
    /*are available on the input stream*/                                \
    void                                                                 \
    (*enqueue)(struct BitstreamReader_s* self,                           \
               unsigned bytes,                                           \
               struct BitstreamQueue_s* queue);

typedef struct BitstreamReader_s {
    BITSTREAMREADER_TYPE

    /*returns the remaining size of the stream in bytes
      this is only applicable for substreams and queues
      otherwise it always returns 0*/
    unsigned
    (*size)(const struct BitstreamReader_s* self);

    /*closes the BistreamReader's internal stream

     * for FILE objects, performs fclose
     * for substreams, does nothing
     * for external input, calls its .close() method

     once the substream is closed,
     the reader's methods are updated to generate errors if called again*/
    void
    (*close_internal_stream)(struct BitstreamReader_s* self);

    /*frees the BitstreamReader's allocated data

      for FILE objects, does nothing
      for substreams, deallocates buffer
      for external input, calls its .free() method

      deallocates any callbacks
      deallocates any exceptions/used exceptions

      deallocates the bitstream struct*/
    void
    (*free)(struct BitstreamReader_s* self);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamReader_s* self);
} BitstreamReader;


/*BitstreamQueue is a subclass of BitstreamReader
  and can be used any place its parent is used
  but contains additional methods for pushing more data
  onto the end of the queue to be processed
  or getting a count of the bits remaining in the queue*/
typedef struct BitstreamQueue_s {
    BITSTREAMREADER_TYPE

    /*returns the remaining size of the stream in bytes
      this is only applicable for substreams and queues
      otherwise it always returns 0*/
    unsigned
    (*size)(const struct BitstreamQueue_s* self);

    /*closes the BistreamQueue's internal stream

     once the substream is closed,
     the reader's methods are updated to generate errors if called again*/
    void
    (*close_internal_stream)(struct BitstreamQueue_s* self);

    /*frees the BitstreamReader's allocated data

      for queues, deallocates buffer

      deallocates any callbacks
      deallocates any exceptions/used exceptions

      deallocates the bitstream struct*/
    void
    (*free)(struct BitstreamQueue_s* self);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamQueue_s* self);

    /*extends the queue with the given amount of data*/
    void
    (*push)(struct BitstreamQueue_s* self,
            unsigned byte_count,
            const uint8_t* data);

    /*removes all data in the queue*/
    void
    (*reset)(struct BitstreamQueue_s* self);
} BitstreamQueue;


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
   | br_read_bits_b_be | substream | big endian    |
   | br_read_bits_b_le | substream | little endian |
   | br_read_bits_e_be | function  | big endian    |
   | br_read_bits_e_le | function  | little endian |

 *************************************************************/


/*BistreamReader open functions*/
BitstreamReader*
br_open(FILE *f, bs_endianness endianness);

/*creates a BitstreamReader from the given raw data
  with the given endianness*/
BitstreamReader*
br_open_buffer(const uint8_t *buffer,
               unsigned buffer_size,
               bs_endianness endianness);

/*creates a BitstreamQueue which data can be appended to*/
BitstreamQueue*
br_open_queue(bs_endianness endianness);

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
                 ext_setpos_f setpos,
                 ext_getpos_f getpos,
                 ext_free_pos_f free_pos,
                 ext_seek_f seek,
                 ext_close_f close,
                 ext_free_f free);

/*Called by the read functions if one attempts to read past
  the end of the stream.
  If an exception stack is available (with br_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.
*/
#ifdef DEBUG
#define br_abort(bs) __br_abort__((bs), __LINE__)
void
__br_abort__(BitstreamReader* bs, int lineno);
#else
void
br_abort(BitstreamReader* bs);
#endif

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
br_try(BitstreamReader* bs);

/*Pops an entry off the current exception stack.
 (ends a try, essentially)*/
#define br_etry(bs) __br_etry((bs), __FILE__, __LINE__)

void
__br_etry(BitstreamReader* bs, const char *file, int lineno);

/*******************************************************************
 *                          BitstreamWriter                        *
 *******************************************************************/

/*this is a basic binary tree in which the most common values
  (those with the smallest amount of bits to write)
  occur at the top of the tree

  "smaller" and "larger" are array indexes where -1 means value not found*/
typedef struct {
    int value;

    unsigned int write_count;
    unsigned int write_value;

    int smaller;
    int larger;
} bw_huffman_table_t;

struct BitstreamWriter_s;
struct recorder_buffer;

/*a mark on the BitstreamWriter's stream which can be rewound to*/
typedef struct bw_pos_s {
    /*our source writer
      attempting to setpos on some other writer will raise an error*/
    struct BitstreamWriter_s *writer;

    /*the position in the stream*/
    union {
        fpos_t file;
        unsigned recorder;
        struct {
            void* pos;
            ext_free_pos_f free_pos;
        } external;
    } position;

    /*a function to delete position when finished with it*/
    void (*del)(struct bw_pos_s *pos);
} bw_pos_t;


struct bw_pos_stack {
    bw_pos_t* pos;
    struct bw_pos_stack* next;
};

/*writes the given value as "count" number of unsigned bits*/
typedef void
(*bw_write_f)(struct BitstreamWriter_s* self,
              unsigned int count,
              unsigned int value);

/*writes the given value as "count" number of signed bits*/
typedef void
(*bw_write_signed_f)(struct BitstreamWriter_s* self,
                     unsigned int count,
                     int value);

/*writes the given value as "count" number of unsigned bits*/
typedef void
(*bw_write_64_f)(struct BitstreamWriter_s* self,
                 unsigned int count,
                 uint64_t value);

/*writes the given value as "count" number of signed bits*/
typedef void
(*bw_write_signed_64_f)(struct BitstreamWriter_s* self,
                        unsigned int count,
                        int64_t value);

/*writes the given value as "count" number of unsigned bits*/
typedef void
(*bw_write_bigint_f)(struct BitstreamWriter_s* self,
                     unsigned int count,
                     const mpz_t value);

typedef void
(*bw_write_signed_bigint_f)(struct BitstreamWriter_s* self,
                            unsigned int count,
                            const mpz_t value);

/*writes "value" number of non stop bits to the current stream
  followed by a single stop bit*/
typedef void
(*bw_write_unary_f)(struct BitstreamWriter_s* self,
                    int stop_bit,
                    unsigned int value);

/*writes "value" is a Huffman code to the stream
  where the code tree is defined from the given compiled table
  returns 0 on success, or 1 if the code is not found in the table*/
typedef int
(*bw_write_huffman_code_f)(struct BitstreamWriter_s* self,
                           bw_huffman_table_t table[],
                           int value);

/*writes "byte_count" number of bytes to the output stream*/
typedef void
(*bw_write_bytes_f)(struct BitstreamWriter_s* self,
                    const uint8_t* bytes,
                    unsigned int byte_count);

/*returns a new pos instance which can be rewound to
  may call bw_abort() if the position cannot be
  gotten or the stream in closed*/
typedef bw_pos_t*
(*bw_getpos_f)(struct BitstreamWriter_s* self);

/*sets the streams position from a pos instance
  may call bw_abort() if the position cannot be set
  the stream is closed, or the position
  is from another stream*/
typedef void
(*bw_setpos_f)(struct BitstreamWriter_s* self,
               const bw_pos_t* pos);

#define BITSTREAMWRITER_TYPE                                \
    bs_endianness endianness;                               \
    bw_type type;                                           \
                                                            \
    union {                                                 \
        FILE* file;                                         \
        struct bw_buffer* recorder;                         \
        struct bw_external_output* external;                \
    } output;                                               \
                                                            \
    unsigned int buffer_size;                               \
    unsigned int buffer;                                    \
                                                            \
    struct bs_callback* callbacks;                          \
    struct bs_exception* exceptions;                        \
    struct bs_exception* exceptions_used;                   \
                                                            \
    bw_write_f write;                                       \
                                                            \
    bw_write_signed_f write_signed;                         \
                                                            \
    bw_write_64_f write_64;                                 \
                                                            \
    bw_write_signed_64_f write_signed_64;                   \
                                                            \
    bw_write_bigint_f write_bigint;                         \
                                                            \
    bw_write_signed_bigint_f write_signed_bigint;           \
                                                            \
    bw_write_unary_f write_unary;                           \
                                                            \
    /*byte aligns the stream and sets its format*/          \
    /*to big endian or little endian*/                      \
    void                                                    \
    (*set_endianness)(struct BitstreamWriter_s* self,       \
                      bs_endianness endianness);            \
                                                            \
    bw_write_huffman_code_f write_huffman_code;             \
                                                            \
    bw_write_bytes_f write_bytes;                           \
                                                            \
    /*takes a format string,*/                              \
    /*peforms the indicated write operations with prefixed numeric lengths*/ \
    /*using the values from the given arguments*/           \
    /*where the format actions are*/                        \
                                                            \
    /*| format | action              | argument     |*/     \
    /*|--------+---------------------+--------------|*/     \
    /*| u      | write               | unsigned int |*/     \
    /*| s      | write_signed        | int          |*/     \
    /*| U      | write_64            | uint64_t     |*/     \
    /*| S      | write_signed_64     | int64_t      |*/     \
    /*| K      | write_bigint        | mpz_t*       |*/     \
    /*| L      | write_signed_bigint | mpz_t*       |*/     \
    /*| p      | skip                | N/A          |*/     \
    /*| P      | skip_bytes          | N/A          |*/     \
    /*| b      | write_bytes         | uint8_t*     |*/     \
    /*| a      | byte_align          | N/A          |*/     \
                                                            \
    /*For example, one could write a 32 bit header as follows:*/ \
                                                            \
    /*unsigned int arg1; //  2 unsigned bits*/              \
    /*unsigned int arg2; //  3 unsigned bits*/              \
    /*int arg3;          //  5 signed bits */               \
    /*unsigned int arg4; //  3 unsigned bits*/              \
    /*uint64_t arg5;     // 19 unsigned bits*/              \
                                                            \
    /*writer->build(writer, "2u3u5s3u19U", arg1, arg2, arg3, arg4, arg5);*/  \
                                                            \
    /*the "*" format multiplies the next format by the given amount*/ \
    /*For example, to write 4, signed 8 bit values:*/       \
                                                            \
    /*reader->parse(reader, "4* 8s", arg1, arg2, arg3, arg4);*/ \
                                                            \
    /*this is designed to perform the inverse of BitstreamReader->parse()*/ \
    void                                                    \
    (*build)(struct BitstreamWriter_s* self,                \
             const char* format, ...);                      \
                                                            \
    /*returns 1 if the stream is byte-aligned, 0 if not*/   \
    int                                                     \
    (*byte_aligned)(const struct BitstreamWriter_s* self);  \
                                                            \
    /*if the stream is not already byte-aligned*/           \
    /*pad it with 0 bits until it is*/                      \
    void                                                    \
    (*byte_align)(struct BitstreamWriter_s* self);          \
                                                            \
    /*flushes the current output stream's pending data*/    \
    void                                                    \
    (*flush)(struct BitstreamWriter_s* self);               \
                                                            \
    /*pushes a callback function into the stream*/          \
    /*which is called on every byte written*/               \
    void                                                    \
    (*add_callback)(struct BitstreamWriter_s* self,         \
                    bs_callback_f callback,                 \
                    void* data);                            \
                                                            \
    /*pushes the given callback onto the callback stack*/         \
    /*data from "callback" is copied onto a new internal struct*/ \
    /*it does not need to be allocated from the heap*/            \
    void                                                    \
    (*push_callback)(struct BitstreamWriter_s* self,        \
                     struct bs_callback* callback);         \
                                                            \
    /*pops the most recently added callback from the stack*/     \
    /*if "callback" is not NULL, data from the popped callback*/ \
    /*is copied to that struct*/                                 \
    void                                                    \
    (*pop_callback)(struct BitstreamWriter_s* self,         \
                    struct bs_callback* callback);          \
                                                            \
    /*explicitly call all set callbacks as if "byte" had been written*/ \
    /*to the input stream*/                                             \
    void                                                    \
    (*call_callbacks)(struct BitstreamWriter_s* self,       \
                      uint8_t byte);                        \
                                                            \
    bw_getpos_f getpos;                                     \
    bw_setpos_f setpos;

typedef struct BitstreamWriter_s {
    BITSTREAMWRITER_TYPE

    /*flushes and closes the BitstreamWriter's internal stream  */
    /*for FILE objects, performs fclose                         */
    /*for external functions, calls the defined close() function*/
    /*once the internal stream is closed,                       */
    /*the writer's I/O methods are updated                      */
    /*to generate errors if called again                        */
    void
    (*close_internal_stream)(struct BitstreamWriter_s* self);

    /*for external functions, call free function on user data*/
    /*deallocates any callbacks, exceptions and marks        */
    /*frees BitstreamWriter struct                           */
    void
    (*free)(struct BitstreamWriter_s* self);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamWriter_s* self);
} BitstreamWriter;


/*BitstreamRecorder is a subclass of BitstreamWriter
  and can be used any place its parent is used
  but contains additional methods for getting a count of bits written
  and dumping recorded data to another BitstreamWriter*/
typedef struct BitstreamRecorder_s {
    BITSTREAMWRITER_TYPE

    /*returns the total bits written to the stream thus far*/
    unsigned int
    (*bits_written)(const struct BitstreamRecorder_s* self);

    /*returns the total bytes written to the stream thus far*/
    unsigned int
    (*bytes_written)(const struct BitstreamRecorder_s* self);

    /*resets the stream for new values*/
    void
    (*reset)(struct BitstreamRecorder_s* self);

    /*copies all the recorded data in a recorder to the target writer*/
    void
    (*copy)(const struct BitstreamRecorder_s* self,
            struct BitstreamWriter_s* target);

    /*returns our internal buffer of data written so far
      not including any partial bytes
      use bytes_written() to determine this buffer's total size*/
    const uint8_t*
    (*data)(const struct BitstreamRecorder_s* self);

    /*flushes and closes the internal stream*/
    /*for recorders, does nothing           */
    /*once the internal stream is closed,   */
    /*the writer's I/O methods are updated  */
    /*to generate errors if called again    */
    void
    (*close_internal_stream)(struct BitstreamRecorder_s* bs);

    /*for recorders, deallocates buffer              */
    /*deallocates any callbacks, exceptions and marks*/
    /*frees BitstreamRecorder struct                 */
    void
    (*free)(struct BitstreamRecorder_s* bs);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamRecorder_s* bs);
} BitstreamRecorder;


/*************************************************************
 Bitstream Writer Function Matrix
 The write functions come in three output variants
 and two endianness variants for file and recorder output:

 bw_function_x or bw_function_x_yy

 where "x" is "f" for raw file, "e" for external function,
 "r" for recorder or "a" for accumulator
 and "yy" is "be" for big endian or "le" for little endian.

 For example:

 | Function           | Output      | Endianness    |
 |--------------------+-------------+---------------|
 | bw_write_bits_f_be | raw file    | big endian    |
 | bw_write_bits_f_le | raw file    | little endian |
 | bw_write_bits_e_be | function    | big endian    |
 | bw_write_bits_e_le | function    | little endian |
 | bw_write_bits_r_be | recorder    | big endian    |
 | bw_write_bits_r_le | recorder    | little endian |

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
                 ext_setpos_f setpos,
                 ext_getpos_f getpos,
                 ext_free_pos_f free_pos,
                 ext_flush_f flush,
                 ext_close_f close,
                 ext_free_f free);

BitstreamRecorder*
bw_open_recorder(bs_endianness endianness);


/*unattached, BitstreamWriter functions*/

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


void
recorder_swap(BitstreamRecorder **a, BitstreamRecorder **b);


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


/*******************************************************************
 *                       bw_pos_stack handlers                     *
 *******************************************************************/

void
bw_pos_stack_push(struct bw_pos_stack** stack, bw_pos_t* pos);

bw_pos_t*
bw_pos_stack_pop(struct bw_pos_stack** stack);


#ifdef HAS_PYTHON
/*******************************************************************
 *                          Python-specific                        *
 *******************************************************************/

unsigned
br_read_python(PyObject *reader,
               uint8_t *buffer,
               unsigned buffer_size);

int
bw_write_python(PyObject* writer,
                const uint8_t *buffer,
                unsigned buffer_size);

int
bw_flush_python(PyObject* writer);

int
bs_setpos_python(PyObject* stream, PyObject* pos);

PyObject*
bs_getpos_python(PyObject* stream);

void
bs_free_pos_python(PyObject* pos);

int
bs_fseek_python(PyObject* stream, long position, int whence);

int
bs_close_python(PyObject* obj);

void
bs_free_python_decref(PyObject* obj);

void
bs_free_python_nodecref(PyObject* obj);

int
python_obj_seekable(PyObject* obj);

#endif

/*******************************************************************
 *                           miscellaneous                         *
 *******************************************************************/

/*a trivial callback which increments "total_bytes" as an unsigned int*/
void
byte_counter(uint8_t byte, unsigned* total_bytes);

#endif
