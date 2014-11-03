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
#include "func_io.h"
#include "mini-gmp.h"

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
typedef uint16_t state_t;

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;
typedef enum {BR_FILE, BR_BUFFER, BR_EXTERNAL} br_type;
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
struct br_buffer;

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

/*******************************************************************
 *                          BitstreamReader                        *
 *******************************************************************/


typedef struct BitstreamReader_s {
    bs_endianness endianness;
    br_type type;

    union {
        FILE* file;
        struct br_buffer* buffer;
        struct br_external_input* external;
    } input;

    state_t state;
    struct bs_callback* callbacks;
    struct bs_exception* exceptions;

    struct bs_exception* exceptions_used;

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

    /*reads "count" number of unsigned bits from the current stream
      to the given "value" in the current endian format
      "value" must have been initialized previously*/
    void
    (*read_bigint)(struct BitstreamReader_s* bs,
                   unsigned int count,
                   mpz_t value);

    /*reads "count" number of signed bits from the current stream
      to the given "value" in the current endian format
      "value" must have been initialized previous*/
    void
    (*read_signed_bigint)(struct BitstreamReader_s* bs,
                          unsigned int count,
                          mpz_t value);

    /*skips "count" number of bits from the current stream as if read

      callbacks are called on each skipped byte*/
    void
    (*skip)(struct BitstreamReader_s* bs, unsigned int count);

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

    /*sets the stream's format to big endian or little endian
      which automatically byte aligns it*/
    void
    (*set_endianness)(struct BitstreamReader_s* bs,
                      bs_endianness endianness);

    /*reads the next Huffman code from the stream
      where the code tree is defined from the given compiled table*/
    int
    (*read_huffman_code)(struct BitstreamReader_s* bs,
                         br_huffman_table_t table[]);

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

    /*skips "count" number of bytes from the current stream as if read

      callbacks are called on each skipped byte*/
    void
    (*skip_bytes)(struct BitstreamReader_s* bs, unsigned int count);

    /*takes a format string,
      performs the indicated read operations with prefixed numeric lengths
      and places the results in the given argument pointers
      where the format actions are:

      | format | action             | argument      |
      |--------+--------------------+---------------|
      | u      | read               | unsigned int* |
      | s      | read_signed        | int*          |
      | U      | read_64            | uint64_t*     |
      | S      | read_signed_64     | int64_t*      |
      | K      | read_bigint        | mpz_t*        |
      | L      | read_signed_bigint | mpz_t*        |
      | p      | skip               | N/A           |
      | P      | skip_bytes         | N/A           |
      | b      | read_bytes         | uint8_t*      |
      | a      | byte_align         | N/A           |

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

    /*returns 1 if the stream is byte-aligned, 0 if not*/
    int
    (*byte_aligned)(const struct BitstreamReader_s* bs);

    /*aligns the stream to a byte boundary*/
    void
    (*byte_align)(struct BitstreamReader_s* bs);

    /*pushes a callback function into the stream
      which is called on every byte read*/
    void
    (*add_callback)(struct BitstreamReader_s* bs,
                    bs_callback_f callback,
                    void* data);

    /*pushes the given callback onto the callback stack
      data from "callback" is copied onto a new internal struct
      it does not need to be allocated from the heap*/
    void
    (*push_callback)(struct BitstreamReader_s* bs,
                     struct bs_callback* callback);

    /*pops the most recently added callback from the stack
      if "callback" is not NULL, data from the popped callback
      is copied to that struct*/
    void
    (*pop_callback)(struct BitstreamReader_s* bs,
                    struct bs_callback* callback);

    /*explicitly call all set callbacks as if "byte" had been read
      from the input stream*/
    void
    (*call_callbacks)(struct BitstreamReader_s* bs,
                      uint8_t byte);

    /*returns a new pos instance which can be rewound to
      may call br_abort() if the position cannot be gotten
      or the stream is closed*/
    br_pos_t*
    (*getpos)(struct BitstreamReader_s* bs);

    /*sets the stream's position from a pos instance
      may call br_abort() if the position cannot be set
      the stream is closed, or the position is from another stream*/
    void
    (*setpos)(struct BitstreamReader_s* bs, const br_pos_t* pos);

    /*moves the stream directly to the given location, in bytes,
      relative to the beginning, current or end of the stream

      no callbacks are called on the intervening bytes*/
    void
    (*seek)(struct BitstreamReader_s* bs, long position, bs_whence whence);

    /*creates a substream from the current stream
      containing the given number of bytes
      and with the input stream's endianness

      the substream must be freed when finished

      br_abort() is called if insufficient bytes
      are available on the input stream*/
    struct BitstreamReader_s*
    (*substream)(struct BitstreamReader_s* bs, unsigned bytes);

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

      deallocates any callbacks
      deallocates any exceptions/used exceptions
      deallocates any marks

      deallocates the bitstream struct*/
    void
    (*free)(struct BitstreamReader_s* bs);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamReader_s* bs);
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


/*bs->read(bs, count)  methods*/
unsigned int
br_read_bits_f_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_f_le(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_b_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_b_le(BitstreamReader* bs, unsigned int count);
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
br_read_bits64_b_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_b_le(BitstreamReader* bs, unsigned int count);
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


/*bs->read_bigint(bs, count, value)  methods*/
void
br_read_bits_bigint_f_be(BitstreamReader* bs,
                         unsigned int count,
                         mpz_t value);
void
br_read_bits_bigint_f_le(BitstreamReader* bs,
                         unsigned int count,
                         mpz_t value);
void
br_read_bits_bigint_b_be(BitstreamReader* bs,
                         unsigned int count,
                         mpz_t value);
void
br_read_bits_bigint_b_le(BitstreamReader* bs,
                         unsigned int count,
                         mpz_t value);
void
br_read_bits_bigint_e_be(BitstreamReader* bs,
                         unsigned int count,
                         mpz_t value);
void
br_read_bits_bigint_e_le(BitstreamReader* bs,
                         unsigned int count,
                         mpz_t value);
void
br_read_bits_bigint_c(BitstreamReader* bs,
                      unsigned int count,
                      mpz_t value);

/*bs->read_signed_bigint(bs, count, value)  methods*/
void
br_read_signed_bits_bigint_be(BitstreamReader* bs,
                              unsigned int count,
                              mpz_t value);
void
br_read_signed_bits_bigint_le(BitstreamReader* bs,
                              unsigned int count,
                              mpz_t value);


/*bs->skip(bs, count)  methods*/
void
br_skip_bits_f_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_f_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_b_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_b_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_e_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_e_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_c(BitstreamReader* bs, unsigned int count);


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
br_read_unary_b_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_b_le(BitstreamReader* bs, int stop_bit);
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
br_skip_unary_b_be(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_b_le(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_e_be(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_e_le(BitstreamReader* bs, int stop_bit);
void
br_skip_unary_c(BitstreamReader* bs, int stop_bit);


/*bs->set_endianness(bs, endianness)  methods*/
void
br_set_endianness_f(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_b(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_e(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_c(BitstreamReader *bs, bs_endianness endianness);


/*bs->read_huffman_code(bs, table)  methods*/
int
br_read_huffman_code_f(BitstreamReader *bs,
                       br_huffman_table_t table[]);
int
br_read_huffman_code_b(BitstreamReader *bs,
                       br_huffman_table_t table[]);
int
br_read_huffman_code_e(BitstreamReader *bs,
                       br_huffman_table_t table[]);
int
br_read_huffman_code_c(BitstreamReader *bs,
                       br_huffman_table_t table[]);


/*bs->read_bytes(bs, bytes, byte_count)  methods*/
void
br_read_bytes_f(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count);
void
br_read_bytes_b(struct BitstreamReader_s* bs,
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


/*bs->skip_bytes(bs, count)  method*/
void
br_skip_bytes(BitstreamReader* bs, unsigned int count);


/*bs->parse(bs, format, ...)  method*/
void
br_parse(struct BitstreamReader_s* stream, const char* format, ...);


/*bs->byte_aligned(bs)  method*/
int
br_byte_aligned(const BitstreamReader* bs);


/*bs->byte_align(bs)  method*/
void
br_byte_align(BitstreamReader* bs);


/*bs->add_callback(bs, callback, data)  method*/
void
br_add_callback(BitstreamReader *bs, bs_callback_f callback, void *data);


/*bs->push_callback(bs, callback)  method*/
void
br_push_callback(BitstreamReader *bs, struct bs_callback *callback);


/*bs->pop_callback(bs, callback)  method*/
void
br_pop_callback(BitstreamReader *bs, struct bs_callback *callback);


/*bs->call_callbacks(bs, byte)  method*/
void
br_call_callbacks(BitstreamReader *bs, uint8_t byte);


/*bs->getpos()  methods*/
br_pos_t*
br_getpos_f(BitstreamReader* bs);
br_pos_t*
br_getpos_b(BitstreamReader* bs);
br_pos_t*
br_getpos_e(BitstreamReader* bs);
br_pos_t*
br_getpos_c(BitstreamReader* bs);


/*bs->setpos(pos)  methods*/
void
br_setpos_f(BitstreamReader* bs, const br_pos_t* pos);
void
br_setpos_b(BitstreamReader* bs, const br_pos_t* pos);
void
br_setpos_e(BitstreamReader* bs, const br_pos_t* pos);
void
br_setpos_c(BitstreamReader* bs, const br_pos_t* pos);


/*pos->del()  methods*/
void
br_pos_del_f(br_pos_t* pos);
void
br_pos_del_b(br_pos_t* pos);
void
br_pos_del_e(br_pos_t* pos);


/*bs->seek(bs, position, whence)  methods*/
void
br_seek_f(BitstreamReader* bs, long position, bs_whence whence);
void
br_seek_b(BitstreamReader* bs, long position, bs_whence whence);
void
br_seek_e(BitstreamReader* bs, long position, bs_whence whence);
void
br_seek_c(BitstreamReader* bs, long position, bs_whence whence);


/*bs->substream(bs, bytes)  method*/
struct BitstreamReader_s*
br_substream(struct BitstreamReader_s *stream, unsigned bytes);


/*converts all read methods to ones that generate I/O errors
  in the event someone tries to read from a stream
  after it's been closed*/
void
br_close_methods(BitstreamReader* bs);


/*bs->close_internal_stream(bs)  methods*/
void
br_close_internal_stream_f(BitstreamReader* bs);
void
br_close_internal_stream_b(BitstreamReader* bs);
void
br_close_internal_stream_e(BitstreamReader* bs);
void
br_close_internal_stream_c(BitstreamReader* bs);


/*bs->free(bs)  methods*/
void
br_free_f(BitstreamReader* bs);
void
br_free_b(BitstreamReader* bs);
void
br_free_e(BitstreamReader* bs);


/*bs->close(bs)  method*/
void
br_close(BitstreamReader* bs);


/*Called by the read functions if one attempts to read past
  the end of the stream.
  If an exception stack is available (with br_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.
*/
#ifdef DEBUG
#define br_abort(bs) __br_abort__((bs), __LINE__)
void
__br_abort__(BitstreamReader *bs, int lineno);
#else
void
br_abort(BitstreamReader *bs);
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
    /*writes the given value as "count" number of unsigned bits*/ \
    void                                                    \
    (*write)(struct BitstreamWriter_s* bs,                  \
             unsigned int count,                            \
             unsigned int value);                           \
                                                            \
    /*writes the given value as "count" number of signed bits*/ \
    void                                                    \
    (*write_signed)(struct BitstreamWriter_s* bs,           \
                    unsigned int count,                     \
                    int value);                             \
                                                            \
    /*writes the given value as "count" number of unsigned bits*/ \
    void                                                    \
    (*write_64)(struct BitstreamWriter_s* bs,               \
                unsigned int count,                         \
                uint64_t value);                            \
                                                            \
    /*writes the given value as "count" number of signed bits*/ \
    void                                                    \
    (*write_signed_64)(struct BitstreamWriter_s* bs,        \
                       unsigned int count,                  \
                       int64_t value);                      \
                                                            \
    /*writes the given value as "count" number of unsigned bits*/ \
    void                                                    \
    (*write_bigint)(struct BitstreamWriter_s* bs,           \
                    unsigned int count,                     \
                    const mpz_t value);                     \
                                                            \
    void                                                    \
    (*write_signed_bigint)(struct BitstreamWriter_s* bs,    \
                           unsigned int count,              \
                           const mpz_t value);              \
                                                            \
    /*writes "value" number of non stop bits to the current stream*/ \
    /*followed by a single stop bit*/                                \
    void                                                    \
    (*write_unary)(struct BitstreamWriter_s* bs,            \
                   int stop_bit,                            \
                   unsigned int value);                     \
                                                            \
    /*byte aligns the stream and sets its format*/          \
    /*to big endian or little endian*/                      \
    void                                                    \
    (*set_endianness)(struct BitstreamWriter_s* bs,         \
                      bs_endianness endianness);            \
                                                            \
    /*writes "value" is a Huffman code to the stream*/                   \
    /*where the code tree is defined from the given compiled table*/     \
    /*returns 0 on success, or 1 if the code is not found in the table*/ \
    int                                                     \
    (*write_huffman_code)(struct BitstreamWriter_s* bs,     \
                          bw_huffman_table_t table[],       \
                          int value);                       \
                                                            \
    /*writes "byte_count" number of bytes to the output stream*/ \
    void                                                    \
    (*write_bytes)(struct BitstreamWriter_s* bs,            \
                   const uint8_t* bytes,                    \
                   unsigned int byte_count);                \
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
    (*build)(struct BitstreamWriter_s* bs,                  \
             const char* format, ...);                      \
                                                            \
    /*returns 1 if the stream is byte-aligned, 0 if not*/   \
    int                                                     \
    (*byte_aligned)(const struct BitstreamWriter_s* bs);    \
                                                            \
    /*if the stream is not already byte-aligned*/           \
    /*pad it with 0 bits until it is*/                      \
    void                                                    \
    (*byte_align)(struct BitstreamWriter_s* bs);            \
                                                            \
    /*flushes the current output stream's pending data*/    \
    void                                                    \
    (*flush)(struct BitstreamWriter_s* bs);                 \
                                                            \
    /*pushes a callback function into the stream*/          \
    /*which is called on every byte written*/               \
    void                                                    \
    (*add_callback)(struct BitstreamWriter_s* bs,           \
                    bs_callback_f callback,                 \
                    void* data);                            \
                                                            \
    /*pushes the given callback onto the callback stack*/         \
    /*data from "callback" is copied onto a new internal struct*/ \
    /*it does not need to be allocated from the heap*/            \
    void                                                    \
    (*push_callback)(struct BitstreamWriter_s* bs,          \
                     struct bs_callback* callback);         \
                                                            \
    /*pops the most recently added callback from the stack*/     \
    /*if "callback" is not NULL, data from the popped callback*/ \
    /*is copied to that struct*/                                 \
    void                                                    \
    (*pop_callback)(struct BitstreamWriter_s* bs,           \
                    struct bs_callback* callback);          \
                                                            \
    /*explicitly call all set callbacks as if "byte" had been written*/ \
    /*to the input stream*/                                             \
    void                                                    \
    (*call_callbacks)(struct BitstreamWriter_s* bs,         \
                      uint8_t byte);                        \
                                                            \
    /*returns a new pos instance which can be rewound to*/  \
    /*may call bw_abort() if the position cannot be*/       \
    /*gotten or the stream in closed*/                      \
    bw_pos_t*                                               \
    (*getpos)(struct BitstreamWriter_s* bs);                \
                                                            \
    /*sets the streams position from a pos instance*/       \
    /*may call bw_abort() if the position cannot be set*/   \
    /*the stream is closed, or the position*/               \
    /*is from another stream*/                              \
    void                                                    \
    (*setpos)(struct BitstreamWriter_s*,                    \
              const bw_pos_t* ps);

typedef struct BitstreamWriter_s {
    BITSTREAMWRITER_TYPE

    /*flushes and closes the BitstreamWriter's internal stream  */
    /*for FILE objects, performs fclose                         */
    /*for external functions, calls the defined close() function*/
    /*once the internal stream is closed,                       */
    /*the writer's I/O methods are updated                      */
    /*to generate errors if called again                        */
    void
    (*close_internal_stream)(struct BitstreamWriter_s* bs);

    /*for external functions, call free function on user data*/
    /*deallocates any callbacks, exceptions and marks        */
    /*frees BitstreamWriter struct                           */
    void
    (*free)(struct BitstreamWriter_s* bs);

    /*calls close_internal_stream(), followed by free()*/
    void
    (*close)(struct BitstreamWriter_s* bs);
} BitstreamWriter;


/*BitstreamRecorder is a subclass of BitstreamWriter
  and can be used anyplace its parent is used
  but contains additional methods for getting a count of bits written
  and dumping recorded data to another BitstreamWriter*/
typedef struct BitstreamRecorder_s {
    BITSTREAMWRITER_TYPE

    /*returns the total bits written to the stream thus far*/
    unsigned int
    (*bits_written)(const struct BitstreamRecorder_s* bs);

    /*returns the total bytes written to the stream thus far*/
    unsigned int
    (*bytes_written)(const struct BitstreamRecorder_s* bs);

    /*resets the stream for new values*/
    void
    (*reset)(struct BitstreamRecorder_s* bs);

    /*copies all the recorded data in a recorder to the target writer*/
    void
    (*copy)(const struct BitstreamRecorder_s* bs,
            struct BitstreamWriter_s* target);

    /*returns our internal buffer of data written so far
      not including any partial bytes
      use bytes_written() to determine this buffer's total size*/
    const uint8_t*
    (*data)(const struct BitstreamRecorder_s* bs);

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
bw_write_bits_c(BitstreamWriter* bs, unsigned int count, unsigned int value);

/*bs->write_signed(bs, count, value)  methods*/
void
bw_write_signed_bits_be(BitstreamWriter* bs, unsigned int count, int value);
void
bw_write_signed_bits_le(BitstreamWriter* bs, unsigned int count, int value);


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
bw_write_bits64_c(BitstreamWriter* bs, unsigned int count, uint64_t value);


/*bs->write_signed_64(bs, count, value)  methods*/
void
bw_write_signed_bits64_be(BitstreamWriter* bs, unsigned int count,
                          int64_t value);
void
bw_write_signed_bits64_le(BitstreamWriter* bs, unsigned int count,
                          int64_t value);


/*bs->write_bigint(bs, count, value)  methods*/
void
bw_write_bits_bigint_f_be(BitstreamWriter* bs,
                          unsigned int count,
                          const mpz_t value);
void
bw_write_bits_bigint_f_le(BitstreamWriter* bs,
                          unsigned int count,
                          const mpz_t value);
void
bw_write_bits_bigint_e_be(BitstreamWriter* bs,
                          unsigned int count,
                          const mpz_t value);
void
bw_write_bits_bigint_e_le(BitstreamWriter* bs,
                          unsigned int count,
                          const mpz_t value);
void
bw_write_bits_bigint_r_be(BitstreamWriter* bs,
                          unsigned int count,
                          const mpz_t value);
void
bw_write_bits_bigint_r_le(BitstreamWriter* bs,
                          unsigned int count,
                          const mpz_t value);
void
bw_write_bits_bigint_c(BitstreamWriter* bs,
                       unsigned int count,
                       const mpz_t value);


/*bs->write_signed_bigint(bs, count, value)  methods*/
void
bw_write_signed_bits_bigint_be(BitstreamWriter* bs,
                               unsigned int count,
                               const mpz_t value);
void
bw_write_signed_bits_bigint_le(BitstreamWriter* bs,
                               unsigned int count,
                               const mpz_t value);


/*bs->write_unary(bs, stop_bit, value)  methods*/
void
bw_write_unary(BitstreamWriter* bs, int stop_bit, unsigned int value);


/*bs->set_endianness(bs, endianness)  methods*/
void
bw_set_endianness_f(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_e(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_r(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_c(BitstreamWriter* bs, bs_endianness endianness);


/*bs->write_huffman_code(bs, table, value)  methods*/
int
bw_write_huffman(BitstreamWriter* bs,
                 bw_huffman_table_t table[],
                 int value);


/*bs->write_bytes(bs, bytes, byte_count)  methods*/
void
bw_write_bytes_f(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_e(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_r(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);
void
bw_write_bytes_c(BitstreamWriter* bs, const uint8_t* bytes, unsigned int count);


/*bs->build(bs, format, ...)  method*/
void
bw_build(struct BitstreamWriter_s* stream, const char* format, ...);


/*bs->byte_aligned(bs)  method*/
int
bw_byte_aligned_f_e_r(const BitstreamWriter* bs);
int
bw_byte_aligned_c(const BitstreamWriter* bs);


/*bs->byte_align(bs)  methods*/
void
bw_byte_align_f_e_r(BitstreamWriter* bs);
void
bw_byte_align_c(BitstreamWriter* bs);


/*bs->flush(bs)  methods*/
void
bw_flush_f(BitstreamWriter* bs);
void
bw_flush_r_c(BitstreamWriter* bs);
void
bw_flush_e(BitstreamWriter* bs);


/*bs->add_callback(bs, callback, data)  method*/
void
bw_add_callback(BitstreamWriter *bs, bs_callback_f callback, void *data);


/*bs->push_callback(bs, callback)  method*/
void
bw_push_callback(BitstreamWriter *bs, struct bs_callback *callback);


/*bs->pop_callback(bs, callback)  method*/
void
bw_pop_callback(BitstreamWriter *bs, struct bs_callback *callback);


/*bs->call_callbacks(bs, byte)  method*/
void
bw_call_callbacks(BitstreamWriter *bs, uint8_t byte);


/*bs->getpos(bs)  method*/
bw_pos_t*
bw_getpos_f(BitstreamWriter *bs);
bw_pos_t*
bw_getpos_e(BitstreamWriter *bs);
bw_pos_t*
bw_getpos_r(BitstreamWriter *bs);
bw_pos_t*
bw_getpos_c(BitstreamWriter *bs);


/*pos->del(pos)  method*/
void
bw_pos_del_f(bw_pos_t* pos);
void
bw_pos_del_e(bw_pos_t* pos);
void
bw_pos_del_r(bw_pos_t* pos);


/*bs->setpos(bs, pos)  method*/
void
bw_setpos_f(BitstreamWriter *bs, const bw_pos_t* pos);
void
bw_setpos_e(BitstreamWriter *bs, const bw_pos_t* pos);
void
bw_setpos_r(BitstreamWriter *bs, const bw_pos_t* pos);
void
bw_setpos_c(BitstreamWriter *bs, const bw_pos_t* pos);


void
bw_close_methods(BitstreamWriter* bs);


/*bs->close_internal_stream(bs)  methods*/
void
bw_close_internal_stream_f(BitstreamWriter* bs);
void
bw_close_internal_stream_e(BitstreamWriter* bs);
void
bw_close_internal_stream_cf(BitstreamWriter* bs);
void
bw_close_internal_stream_r(BitstreamRecorder* bs);


/*bs->free(bs)  methods*/
void
bw_free_f(BitstreamWriter* bs);
void
bw_free_e(BitstreamWriter* bs);
void
bw_free_r(BitstreamRecorder* bs);


/*bs->close(bs)  method*/
void
bw_close_f_e(BitstreamWriter* bs);
void
bw_close_r(BitstreamRecorder* bs);


/*bs->bits_written(bs)  methods*/
unsigned int
bw_bits_written_r(const BitstreamRecorder* bs);


/*bs->bytes_written(bs)  methods*/
unsigned int
bw_bytes_written_r(const BitstreamRecorder* bs);


/*bs->reset(bs)  methods*/
void
bw_reset_r(BitstreamRecorder* bs);


/*bs->copy(bs)  method*/
void
bw_copy_r(const BitstreamRecorder* bs, BitstreamWriter* target);


/*bs->split(bs, bytes, target, remainder)  method*/
unsigned
bw_split_r(const BitstreamRecorder* bs,
           unsigned bytes,
           BitstreamWriter* target,
           BitstreamWriter* remainder);


/*bs->data(bs)  method*/
const uint8_t*
bw_data_r(const BitstreamRecorder* bs);


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


static inline int
bw_closed(BitstreamWriter* bs) {
    return (bs->write == bw_write_bits_c);
}

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
 *                       read buffer-specific                      *
 *******************************************************************/

struct br_buffer {
    uint8_t *data;
    unsigned pos;
    unsigned size;
};

/*allocates new br_buffer struct with no data
  must be freed with br_buf_free()*/
static inline struct br_buffer*
br_buf_new(void)
{
    struct br_buffer *buf = malloc(sizeof(struct br_buffer));
    buf->data = NULL;
    buf->pos = 0;
    buf->size = 0;
    return buf;
}

/*deallocates a br_buffer struct and any data it may have*/
static inline void
br_buf_free(struct br_buffer *buf)
{
    free(buf->data);
    free(buf);
}

/*returns 1 if the buffer is empty*/
static inline int
br_buf_empty(const struct br_buffer *buf)
{
    return buf->pos == buf->size;
}

/*appends the given data to the buffer*/
void
br_buf_extend(struct br_buffer *buf, const uint8_t *data, unsigned size);

/*cleans out already read data from the buffer
  note that this will invalidate any position values!*/
void
br_buf_gc(struct br_buffer *buf);

/*returns the next character in the buffer, or EOF if no characters remain*/
static inline int
br_buf_getc(struct br_buffer *buf)
{
    if (buf->pos < buf->size) {
        return buf->data[buf->pos++];
    } else {
        return EOF;
    }
}

/*reads "size" amount of bytes from the buffer to "data"
  returns the amount of bytes actually read
  which may be less than the amount requested*/
unsigned
br_buf_read(struct br_buffer *buf, uint8_t *data, unsigned size);

/*gets the current position in the buffer*/
static inline void
br_buf_getpos(const struct br_buffer *buf, unsigned *pos)
{
    *pos = buf->pos;
}

/*sets the position in the buffer*/
static inline void
br_buf_setpos(struct br_buffer *buf, unsigned pos)
{
    buf->pos = pos;
}

/*analagous to fseek, sets a position in the buffer*/
int
br_buf_fseek(struct br_buffer *buf, long position, int whence);


/*******************************************************************
 *                       write buffer-specific                     *
 *******************************************************************/

struct bw_buffer {
    unsigned pos;         /*the current position in the buffer*/
    unsigned max_pos;     /*the farthest written data*/
    unsigned buffer_size; /*the total buffer size*/
    uint8_t* buffer;      /*the buffer data itself*/
};

static inline struct bw_buffer*
bw_buf_new(void)
{
    struct bw_buffer* buf = malloc(sizeof(struct bw_buffer));
    buf->pos = buf->max_pos = buf->buffer_size = 0;
    buf->buffer = NULL;
    return buf;
}

static inline void
bw_buf_free(struct bw_buffer* buf)
{
    free(buf->buffer);
    free(buf);
}

static inline int
bw_buf_putc(int c, struct bw_buffer* buf)
{
    if (buf->pos == buf->buffer_size) {
        buf->buffer_size += 4096;
        buf->buffer = realloc(buf->buffer, buf->buffer_size);
    }
    buf->buffer[buf->pos++] = (uint8_t)c;
    buf->max_pos = MAX(buf->max_pos, buf->pos);
    return c;
}

void
bw_buf_write(struct bw_buffer* buf, const uint8_t *data, unsigned data_size);

static inline void
bw_buf_getpos(const struct bw_buffer* buf, unsigned *pos)
{
    *pos = buf->pos;
}

/*returns 0 on a successful seek, EOF if a seek error occurs
  (usually if one sets a position on a buffer that's been reset)*/
static inline int
bw_buf_setpos(struct bw_buffer* buf, unsigned pos)
{
    if (pos <= buf->max_pos) {
        buf->pos = pos;
        return 0;
    } else {
        return EOF;
    }
}

static inline unsigned
bw_buf_size(const struct bw_buffer* buf) {
    return buf->max_pos;
}

static inline void
bw_buf_reset(struct bw_buffer* buf) {
    buf->pos = buf->max_pos = 0;
}

/*******************************************************************
 *                       bw_pos_stack handlers                     *
 *******************************************************************/

void
bw_pos_stack_push(struct bw_pos_stack** stack, bw_pos_t* pos);

bw_pos_t*
bw_pos_stack_pop(struct bw_pos_stack** stack);


#ifndef STANDALONE
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
