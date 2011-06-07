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


typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;
typedef enum {BR_FILE, BR_SUBSTREAM, BR_PYTHON} br_type;
typedef enum {BW_FILE, BW_RECORDER, BW_ACCUMULATOR} bw_type;


typedef enum {
    BS_WRITE_BITS,
    BS_WRITE_SIGNED_BITS,
    BS_WRITE_BITS64,
    BS_WRITE_UNARY,
    BS_BYTE_ALIGN,
    BS_SET_ENDIANNESS
} BitstreamRecordType;

typedef void (*bs_callback_func)(uint8_t, void*);


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

typedef struct {
    BitstreamRecordType type;
    union {
        unsigned int count;
        int stop_bit;
    } key;
    union {
        int signed_value;
        unsigned int unsigned_value;
        uint64_t value64;
        bs_endianness endianness;
    } value;
} BitstreamRecord;


typedef struct BitstreamReader_s {
#ifndef NDEBUG
    br_type type;
#endif

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

    struct bs_callback* callbacks_used;
    struct bs_exception* exceptions_used;
    struct bs_mark* marks_used;

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to "count" bits wide*/
    unsigned int (*read)(struct BitstreamReader_s* bs, unsigned int count);

    /*returns "count" number of signed bits from the current stream
      in the current endian format up to "count" bits wide*/
    int (*read_signed)(struct BitstreamReader_s* bs, unsigned int count);

    /*returns "count" number of unsigned bits from the current stream
      in the current endian format up to 64 bits wide*/
    uint64_t (*read_64)(struct BitstreamReader_s* bs, unsigned int count);

    /*skips "count" number of bits from the current stream*/
    void (*skip)(struct BitstreamReader_s* bs, unsigned int count);

    /*pushes a single 0 or 1 bit back onto the stream
      in the current endian format

      only a single bit is guaranteed to be unreadable*/
    void (*unread)(struct BitstreamReader_s* bs, int unread_bit);

    /*returns the number of non-stop bits before the 0 or 1 stop bit
      from the current stream in the current endian format*/
    unsigned int (*read_unary)(struct BitstreamReader_s* bs, int stop_bit);

    /*returns the number of non-stop bits before the 0 or 1 stop bit
      from the current stream in the current endian format
      and limited to "maximum_bits"

      may return -1 if the maximum bits are exceeded*/
    int (*read_limited_unary)(struct BitstreamReader_s* bs, int stop_bit,
                              int maximum_bits);

    /*reads the next Huffman code from the stream
      where the code tree is defined from the given compiled table*/
    int (*read_huffman_code)(struct BitstreamReader_s* bs,
                             struct bs_huffman_table table[][0x200]);

    /*aligns the stream to a byte boundary*/
    void (*byte_align)(struct BitstreamReader_s* bs);

    /*sets the stream's format to big endian or little endian
      which automatically byte aligns it*/
    void (*set_endianness)(struct BitstreamReader_s* bs,
                           bs_endianness endianness);

    /*closes the current input stream
      and deallocates the struct*/
    void (*close)(struct BitstreamReader_s* bs);

    /*closes the current input stream
      but does *not* perform any other deallocation*/
    void (*close_stream)(struct BitstreamReader_s* bs);

    /*pushes a new mark onto to the stream, which can be rewound to later

      all pushed marks should be unmarked once no longer needed*/
    void (*mark)(struct BitstreamReader_s* bs);

    /*rewinds the stream to the next previous mark on the mark stack

      rewinding does not affect the mark itself*/
    void (*rewind)(struct BitstreamReader_s* bs);

    /*pops the previous mark from the mark stack*/
    void (*unmark)(struct BitstreamReader_s* bs);

    /*extracts a substream of the current stream with the given length

      this byte-aligns the current stream before extracting the substream
      and immediately calls any callbacks on the extracted bytes

      the substream must be closed when finished via
      substream->close(substream) to free any temporary space*/
    struct BitstreamReader_s* (*substream)(struct BitstreamReader_s* bs,
                                           uint32_t bytes);

    /*this appends the given length of bytes from the current stream
      to the given substream

      in all other respects, it works identically to the previous method*/
    void (*substream_append)(struct BitstreamReader_s* bs,
                             struct BitstreamReader_s* substream,
                             uint32_t bytes);
} BitstreamReader;


typedef struct BitstreamWriter_s {
    bw_type type;

    union {
        struct {
            FILE *file;
            unsigned int buffer_size;
            unsigned int buffer;
        } file;
        struct {
            unsigned int bits_written;
            unsigned int records_written;
            unsigned int records_total;
            BitstreamRecord* records;
        } recorder;
        unsigned int accumulator;
    } output;


    struct bs_callback *callbacks;
    struct bs_callback *callbacks_used;


    /*writes the given value as "count" number of unsigned bits
      to the current stream*/
    void (*write)(struct BitstreamWriter_s* bs,
                  unsigned int count,
                  unsigned int value);

    /*writes the given value as "count" number of signed bits
      to the current stream*/
    void (*write_signed)(struct BitstreamWriter_s* bs,
                         unsigned int count,
                         int value);

    /*writes the given value as "count" number of unsigned bits
      to the current stream, up to 64 bits wide*/
    void (*write_64)(struct BitstreamWriter_s* bs,
                     unsigned int count,
                     uint64_t value);

    /*writes "value" number of non stop bits to the current stream
      followed by a single stop bit*/
    void (*write_unary)(struct BitstreamWriter_s* bs,
                        int stop_bit,
                        unsigned int value);

    /*if the stream is not already byte-aligned,
      pad it with 0 bits until it is*/
    void (*byte_align)(struct BitstreamWriter_s* bs);

    /*byte aligns the stream and sets its format
      to big endian or little endian*/
    void (*set_endianness)(struct BitstreamWriter_s* bs,
                           bs_endianness endianness);

    unsigned int (*bits_written)(struct BitstreamWriter_s* bs);

    void (*close)(struct BitstreamWriter_s* bs);
    void (*close_stream)(struct BitstreamWriter_s* bs);
} BitstreamWriter;


BitstreamReader*
br_open(FILE *f, bs_endianness endianness);

/*performs bs->close_stream followed by bs_free*/
void
br_close(BitstreamReader *bs);

void
br_close_stream_f(BitstreamReader *bs);

/*this deallocates space created by bs_open,
  but does *not* close any file handles*/
void
br_free(BitstreamReader *bs);

/*does nothing, used to override existing functions at runtime*/
void
br_noop(BitstreamReader *bs);

void
br_add_callback(BitstreamReader *bs, bs_callback_func callback, void *data);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were read from the input stream*/
void
br_call_callbacks(BitstreamReader *bs, uint8_t byte);

/*removes the most recently added callback, if any
  if "callback" is not NULL, the popped callback's data is copied to it
  for possible restoration via "bs_push_callback"

  this is often paired with bs_push_callback in order
  to temporarily disable a callback, for example:

  br_pop_callback(reader, &saved_callback);  //save callback for later
  unchecksummed_value = bs->read(bs, 16);    //read a value
  br_push_callback(reader, &saved_callback); //restored saved callback
*/
void
br_pop_callback(BitstreamReader *bs, struct bs_callback *callback);

/*pushes the given callback back onto the callback stack
  note that the data from "callback" is copied onto a new internal struct;
  it does not need to be allocated from the heap

  if "callback" is NULL, this does nothing*/
void
br_push_callback(BitstreamReader *bs, struct bs_callback *callback);

static inline long
br_ftell(BitstreamReader *bs) {
    assert(bs->type == BR_FILE);
    return ftell(bs->input.file);
}


/*Called by the read functions if one attempts to read past
  the end of the stream.
  If an exception stack is available (with bs_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.
*/
void
br_abort(BitstreamReader *bs);


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
br_try(BitstreamReader *bs);


/*Pops an entry off the current exception stack.
 (ends a try, essentially)*/
void
br_etry(BitstreamReader *bs);


/*************************************************************
   Bitstream Reader Function Matrix
   The read functions come in three input variants
   and two endianness variants named in the format:

   br_function_x_yy

   where "x" is "f" for raw file, "s" for substream or "p" for Python input
   and "yy" is "be" for big endian or "le" for little endian.
   For example:

   | Function          | Input     | Endianness    |
   |-------------------+-----------+---------------|
   | br_read_bits_f_be | raw file  | big endian    |
   | br_read_bits_f_le | raw file  | little endian |
   | br_read_bits_s_be | substream | big endian    |
   | br_read_bits_s_le | substream | little endian |
   | br_read_bits_p_be | Python    | big endian    |
   | br_read_bits_p_le | Python    | little endian |

 *************************************************************/

unsigned int
br_read_bits_f_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_f_le(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_s_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
unsigned int
br_read_bits_p_be(BitstreamReader* bs, unsigned int count);
unsigned int
br_read_bits_p_le(BitstreamReader* bs, unsigned int count);
#endif


int
br_read_signed_bits_f_be(BitstreamReader* bs, unsigned int count);
int
br_read_signed_bits_f_le(BitstreamReader* bs, unsigned int count);
int
br_read_signed_bits_s_be(BitstreamReader* bs, unsigned int count);
int
br_read_signed_bits_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
int
br_read_signed_bits_p_be(BitstreamReader* bs, unsigned int count);
int
br_read_signed_bits_p_le(BitstreamReader* bs, unsigned int count);
#endif


uint64_t
br_read_bits64_f_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_f_le(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_s_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
uint64_t
br_read_bits64_p_be(BitstreamReader* bs, unsigned int count);
uint64_t
br_read_bits64_p_le(BitstreamReader* bs, unsigned int count);
#endif


void
br_skip_bits_f_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_f_le(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_s_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
void
br_skip_bits_p_be(BitstreamReader* bs, unsigned int count);
void
br_skip_bits_p_le(BitstreamReader* bs, unsigned int count);
#endif


/*unread_bit has no file/substream/Python variants
  because it never makes calls to the input stream*/
void
br_unread_bit_be(BitstreamReader* bs, int unread_bit);
void
br_unread_bit_le(BitstreamReader* bs, int unread_bit);


unsigned int
br_read_unary_f_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_f_le(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_s_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_s_le(BitstreamReader* bs, int stop_bit);
#ifndef STANDALONE
unsigned int
br_read_unary_p_be(BitstreamReader* bs, int stop_bit);
unsigned int
br_read_unary_p_le(BitstreamReader* bs, int stop_bit);
#endif


int
br_read_limited_unary_f_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_f_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_s_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_s_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
#ifndef STANDALONE
int
br_read_limited_unary_p_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
br_read_limited_unary_p_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
#endif


/*This automatically flushes any current state,
  so make sure to call it while byte-aligned!*/
void
br_set_endianness_f_be(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_f_le(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_s_be(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_s_le(BitstreamReader *bs, bs_endianness endianness);
#ifndef STANDALONE
void
br_set_endianness_p_be(BitstreamReader *bs, bs_endianness endianness);
void
br_set_endianness_p_le(BitstreamReader *bs, bs_endianness endianness);
#endif


/*read_huffman_code has no endianness variants
  since that is determined when its jump table is compiled*/
int
br_read_huffman_code_f(BitstreamReader *bs,
                       struct bs_huffman_table table[][0x200]);
int
br_read_huffman_code_s(BitstreamReader *bs,
                       struct bs_huffman_table table[][0x200]);
#ifndef STANDALONE
int
br_read_huffman_code_p(BitstreamReader *bs,
                       struct bs_huffman_table table[][0x200]);
#endif


/*none of the mark handling functions have endianness variants*/
void
br_mark_f(BitstreamReader* bs);
void
br_mark_s(BitstreamReader* bs);
#ifndef STANDALONE
void
br_mark_p(BitstreamReader* bs);
#endif

void
br_rewind_f(BitstreamReader* bs);
void
br_rewind_s(BitstreamReader* bs);
#ifndef STANDALONE
void
br_rewind_p(BitstreamReader* bs);
#endif

void
br_unmark_f(BitstreamReader* bs);
void
br_unmark_s(BitstreamReader* bs);
#ifndef STANDALONE
void
br_unmark_p(BitstreamReader* bs);
#endif


/*byte_align doesn't have file *or* endianness variants*/
void
br_byte_align(BitstreamReader* bs);


/*returns a new br_buffer struct which can be appended to and read from
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


struct BitstreamReader_s*
br_substream_new(bs_endianness endianness);

/*clears out the substream for possible reuse

  any marks are deleted and the stream is reset
  so that it can be appended to with fresh data*/
void
br_substream_reset(struct BitstreamReader_s *substream);

void
br_close_stream_s(struct BitstreamReader_s *stream);

/*variants for the stream->substream(stream, bytes) method

  these work by calling br_substream_new to generate a plain substream
  with the appropriate endianness,
  then calling substream_append to fill it with data
  before returning the result*/
struct BitstreamReader_s*
br_substream_f_be(struct BitstreamReader_s *stream, uint32_t bytes);

struct BitstreamReader_s*
br_substream_f_le(struct BitstreamReader_s *stream, uint32_t bytes);

#ifndef STANDALONE
struct BitstreamReader_s*
br_substream_p_be(struct BitstreamReader_s *stream, uint32_t bytes);

struct BitstreamReader_s*
br_substream_p_le(struct BitstreamReader_s *stream, uint32_t bytes);
#endif

struct BitstreamReader_s*
br_substream_s_be(struct BitstreamReader_s *stream, uint32_t bytes);

struct BitstreamReader_s*
br_substream_s_le(struct BitstreamReader_s *stream, uint32_t bytes);

/*variants for the stream->substream_append(stream, substream, bytes) method

  note that they have no endianness variants*/

/*appends from a FILE-based stream to the buffer*/
void
br_substream_append_f(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes);

#ifndef STANDALONE
/*appends from a Python-based stream to the buffer*/
void
br_substream_append_p(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes);
#endif

/*appends from one buffer to another buffer*/
void
br_substream_append_s(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
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

BitstreamReader*
br_open_python(PyObject *reader, bs_endianness endianness);

void
br_close_stream_p(BitstreamReader *bs);

#endif


BitstreamWriter*
bw_open(FILE *f, bs_endianness endianness);

BitstreamWriter*
bw_open_accumulator(void);

BitstreamWriter*
bw_open_recorder(void);

void
bw_free(BitstreamWriter* bs);

/*adds a callback function, which is called on every byte written
  the function's arguments are the written byte and a generic
  pointer to some other data structure
 */
void
bw_add_callback(BitstreamWriter *bs, bs_callback_func callback, void *data);

static inline int
bw_eof(BitstreamWriter* bs) {
    assert(bs->type == BW_FILE);
    return feof(bs->output.file.file);
}

static inline long
bw_ftell(BitstreamWriter* bs) {
    assert(bs->type == BW_FILE);
    return ftell(bs->output.file.file);
}

/*make room for at least one additional record*/
static inline void
bs_record_resize(BitstreamWriter* bs)
{
    assert(bs->type == BW_RECORDER);
    if (bs->output.recorder.records_written >=
        bs->output.recorder.records_total) {
        bs->output.recorder.records_total *= 2;
        bs->output.recorder.records = realloc(
             bs->output.recorder.records,
             sizeof(BitstreamRecord) *
             bs->output.recorder.records_total);
    }
}

void
bw_dump_records(BitstreamWriter* target, BitstreamWriter* source);

/*clear the recorded output and reset for new output*/
static inline void
bw_reset_recorder(BitstreamWriter* bs)
{
    assert(bs->type == BW_RECORDER);
    bs->output.recorder.bits_written = bs->output.recorder.records_written = 0;
}

void
bw_swap_records(BitstreamWriter* a, BitstreamWriter* b);


/*************************************************************
 Bitstream Writer Function Matrix
 The write functions come in three output variants
 and two endianness variants for file output:

 bw_function_x or bw_function_x_yy

 where "x" is "f" for raw file, "r" for recorder or "a" for accumulator
 and "yy" is "be" for big endian or "le" for little endian.

 For example:

 | Function           | Output      | Endianness    |
 |--------------------+-------------+---------------|
 | bw_write_bits_f_be | raw file    | big endian    |
 | bw_write_bits_f_le | raw file    | little endian |
 | bw_write_bits_r    | recorder    | N/A           |
 | bw_write_bits_a    | accumulator | N/A           |

 *************************************************************/

void
bw_write_bits_f_be(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_f_le(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_r(BitstreamWriter* bs, unsigned int count, unsigned int value);
void
bw_write_bits_a(BitstreamWriter* bs, unsigned int count, unsigned int value);

void
bw_write_signed_bits_f_be(BitstreamWriter* bs, unsigned int count, int value);
void
bw_write_signed_bits_f_le(BitstreamWriter* bs, unsigned int count, int value);
void
bw_write_signed_bits_r(BitstreamWriter* bs, unsigned int count, int value);
void
bw_write_signed_bits_a(BitstreamWriter* bs, unsigned int count, int value);

void
bw_write_bits64_f_be(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_f_le(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_r(BitstreamWriter* bs, unsigned int count, uint64_t value);
void
bw_write_bits64_a(BitstreamWriter* bs, unsigned int count, uint64_t value);

void
bw_write_unary_f(BitstreamWriter* bs, int stop_bit, unsigned int value);
void
bw_write_unary_r(BitstreamWriter* bs, int stop_bit, unsigned int value);
void
bw_write_unary_a(BitstreamWriter* bs, int stop_bit, unsigned int value);

void
bw_byte_align_f_be(BitstreamWriter* bs);
void
bw_byte_align_f_le(BitstreamWriter* bs);
void
bw_byte_align_r(BitstreamWriter* bs);
void
bw_byte_align_a(BitstreamWriter* bs);

unsigned int
bw_bits_written_f(BitstreamWriter* bs);
unsigned int
bw_bits_written_r(BitstreamWriter* bs);
unsigned int
bw_bits_written_a(BitstreamWriter* bs);

void
bw_set_endianness_f_be(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_f_le(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_a(BitstreamWriter* bs, bs_endianness endianness);
void
bw_set_endianness_r(BitstreamWriter* bs, bs_endianness endianness);

void
bw_close_new(BitstreamWriter* bs);

void
bw_close_stream_f(BitstreamWriter* bs);
void
bw_close_stream_r(BitstreamWriter* bs);
void
bw_close_stream_a(BitstreamWriter* bs);



#endif
