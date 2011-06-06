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


typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;


struct bs_buffer {
    uint8_t* buffer;
    uint32_t buffer_size;
    uint32_t buffer_total_size;
    uint32_t buffer_position;
    int mark_in_progress;
};


typedef enum {
    BS_WRITE_BITS,
    BS_WRITE_SIGNED_BITS,
    BS_WRITE_BITS64,
    BS_WRITE_UNARY,
    BS_BYTE_ALIGN,
    BS_SET_ENDIANNESS
} BitstreamRecordType;


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


#ifndef NDEBUG
typedef enum {BS_FILE, BS_SUBSTREAM, BS_PYTHON} bs_type;
#endif


typedef struct BitstreamReader_s {
#ifndef NDEBUG
    bs_type type;
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


BitstreamReader*
bs_open_r(FILE *f, bs_endianness endianness);

/*performs bs->close_stream followed by bs_free*/
void
bs_close_r(BitstreamReader *bs);

void
bs_close_stream_f(BitstreamReader *bs);

/*this deallocates space created by bs_open,
  but does *not* close any file handles*/
void
bs_free_r(BitstreamReader *bs);

/*does nothing, used to override existing functions at runtime*/
void
bs_noop(BitstreamReader *bs);

void
bs_add_callback_r(BitstreamReader *bs, bs_callback_func callback, void *data);

/*explicitly passes "byte" to the set callbacks,
  as if the byte were read from the input stream*/
void
bs_call_callbacks(BitstreamReader *bs, uint8_t byte);

/*removes the most recently added callback, if any
  if "callback" is not NULL, the popped callback's data is copied to it
  for possible restoration via "bs_push_callback"

  this is often paired with bs_push_callback in order
  to temporarily disable a callback, for example:

  bs_pop_callback(reader, &saved_callback);  //save callback for later
  unchecksummed_value = bs->read(bs, 16);    //read a value
  bs_push_callback(reader, &saved_callback); //restored saved callback
*/
void
bs_pop_callback(BitstreamReader *bs, struct bs_callback *callback);

/*pushes the given callback back onto the callback stack
  note that the data from "callback" is copied onto a new internal struct;
  it does not need to be allocated from the heap

  if "callback" is NULL, this does nothing*/
void
bs_push_callback(BitstreamReader *bs, struct bs_callback *callback);

static inline long
bs_ftell(BitstreamReader *bs) {
    assert(bs->type == BS_FILE);
    return ftell(bs->input.file);
}


/*Called by the read functions if one attempts to read past
  the end of the stream.
  If an exception stack is available (with bs_try),
  this jumps to that location via longjmp(3).
  If not, this prints an error message and performs an unconditional exit.
*/
void
bs_abort(BitstreamReader *bs);


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
bs_try(BitstreamReader *bs);


/*Pops an entry off the current exception stack.
 (ends a try, essentially)*/
void
bs_etry(BitstreamReader *bs);


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
bs_read_bits_f_be(BitstreamReader* bs, unsigned int count);
unsigned int
bs_read_bits_f_le(BitstreamReader* bs, unsigned int count);
unsigned int
bs_read_bits_s_be(BitstreamReader* bs, unsigned int count);
unsigned int
bs_read_bits_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
unsigned int
bs_read_bits_p_be(BitstreamReader* bs, unsigned int count);
unsigned int
bs_read_bits_p_le(BitstreamReader* bs, unsigned int count);
#endif


int
bs_read_signed_bits_f_be(BitstreamReader* bs, unsigned int count);
int
bs_read_signed_bits_f_le(BitstreamReader* bs, unsigned int count);
int
bs_read_signed_bits_s_be(BitstreamReader* bs, unsigned int count);
int
bs_read_signed_bits_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
int
bs_read_signed_bits_p_be(BitstreamReader* bs, unsigned int count);
int
bs_read_signed_bits_p_le(BitstreamReader* bs, unsigned int count);
#endif


uint64_t
bs_read_bits64_f_be(BitstreamReader* bs, unsigned int count);
uint64_t
bs_read_bits64_f_le(BitstreamReader* bs, unsigned int count);
uint64_t
bs_read_bits64_s_be(BitstreamReader* bs, unsigned int count);
uint64_t
bs_read_bits64_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
uint64_t
bs_read_bits64_p_be(BitstreamReader* bs, unsigned int count);
uint64_t
bs_read_bits64_p_le(BitstreamReader* bs, unsigned int count);
#endif


void
bs_skip_bits_f_be(BitstreamReader* bs, unsigned int count);
void
bs_skip_bits_f_le(BitstreamReader* bs, unsigned int count);
void
bs_skip_bits_s_be(BitstreamReader* bs, unsigned int count);
void
bs_skip_bits_s_le(BitstreamReader* bs, unsigned int count);
#ifndef STANDALONE
void
bs_skip_bits_p_be(BitstreamReader* bs, unsigned int count);
void
bs_skip_bits_p_le(BitstreamReader* bs, unsigned int count);
#endif


/*unread_bit has no file/substream/Python variants
  because it never makes calls to the input stream*/
void
bs_unread_bit_be(BitstreamReader* bs, int unread_bit);
void
bs_unread_bit_le(BitstreamReader* bs, int unread_bit);


unsigned int
bs_read_unary_f_be(BitstreamReader* bs, int stop_bit);
unsigned int
bs_read_unary_f_le(BitstreamReader* bs, int stop_bit);
unsigned int
bs_read_unary_s_be(BitstreamReader* bs, int stop_bit);
unsigned int
bs_read_unary_s_le(BitstreamReader* bs, int stop_bit);
#ifndef STANDALONE
unsigned int
bs_read_unary_p_be(BitstreamReader* bs, int stop_bit);
unsigned int
bs_read_unary_p_le(BitstreamReader* bs, int stop_bit);
#endif


int
bs_read_limited_unary_f_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_f_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_s_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_s_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
#ifndef STANDALONE
int
bs_read_limited_unary_p_be(BitstreamReader* bs, int stop_bit, int maximum_bits);
int
bs_read_limited_unary_p_le(BitstreamReader* bs, int stop_bit, int maximum_bits);
#endif


/*This automatically flushes any current state,
  so make sure to call it while byte-aligned!*/
void
bs_set_endianness_f_be(BitstreamReader *bs, bs_endianness endianness);
void
bs_set_endianness_f_le(BitstreamReader *bs, bs_endianness endianness);
void
bs_set_endianness_s_be(BitstreamReader *bs, bs_endianness endianness);
void
bs_set_endianness_s_le(BitstreamReader *bs, bs_endianness endianness);
#ifndef STANDALONE
void
bs_set_endianness_p_be(BitstreamReader *bs, bs_endianness endianness);
void
bs_set_endianness_p_le(BitstreamReader *bs, bs_endianness endianness);
#endif


/*read_huffman_code has no endianness variants
  since that is determined when its jump table is compiled*/
int
bs_read_huffman_code_f(BitstreamReader *bs,
                       struct bs_huffman_table table[][0x200]);
int
bs_read_huffman_code_s(BitstreamReader *bs,
                       struct bs_huffman_table table[][0x200]);
#ifndef STANDALONE
int
bs_read_huffman_code_p(BitstreamReader *bs,
                       struct bs_huffman_table table[][0x200]);
#endif


/*none of the mark handling functions have endianness variants*/
void
bs_mark_f(BitstreamReader* bs);
void
bs_mark_s(BitstreamReader* bs);
#ifndef STANDALONE
void
bs_mark_p(BitstreamReader* bs);
#endif

void
bs_rewind_f(BitstreamReader* bs);
void
bs_rewind_s(BitstreamReader* bs);
#ifndef STANDALONE
void
bs_rewind_p(BitstreamReader* bs);
#endif

void
bs_unmark_f(BitstreamReader* bs);
void
bs_unmark_s(BitstreamReader* bs);
#ifndef STANDALONE
void
bs_unmark_p(BitstreamReader* bs);
#endif


/*byte_align doesn't have file *or* endianness variants*/
void
bs_byte_align_r(BitstreamReader* bs);


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


struct BitstreamReader_s*
bs_substream_new(bs_endianness endianness);

/*clears out the substream for possible reuse

  any marks are deleted and the stream is reset
  so that it can be appended to with fresh data*/
void
bs_substream_reset(struct BitstreamReader_s *substream);

void
bs_close_stream_s(struct BitstreamReader_s *stream);

/*variants for the stream->substream(stream, bytes) method

  these work by calling bs_substream_new to generate a plain substream
  with the appropriate endianness,
  then calling substream_append to fill it with data
  before returning the result*/
struct BitstreamReader_s*
bs_substream_f_be(struct BitstreamReader_s *stream, uint32_t bytes);

struct BitstreamReader_s*
bs_substream_f_le(struct BitstreamReader_s *stream, uint32_t bytes);

#ifndef STANDALONE
struct BitstreamReader_s*
bs_substream_p_be(struct BitstreamReader_s *stream, uint32_t bytes);

struct BitstreamReader_s*
bs_substream_p_le(struct BitstreamReader_s *stream, uint32_t bytes);
#endif

struct BitstreamReader_s*
bs_substream_s_be(struct BitstreamReader_s *stream, uint32_t bytes);

struct BitstreamReader_s*
bs_substream_s_le(struct BitstreamReader_s *stream, uint32_t bytes);

/*variants for the stream->substream_append(stream, substream, bytes) method

  note that they have no endianness variants*/

/*appends from a FILE-based stream to the buffer*/
void
bs_substream_append_f(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes);

#ifndef STANDALONE
/*appends from a Python-based stream to the buffer*/
void
bs_substream_append_p(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes);
#endif

/*appends from one buffer to another buffer*/
void
bs_substream_append_s(struct BitstreamReader_s *stream,
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
bs_open_python(PyObject *reader, bs_endianness endianness);

void
bs_close_stream_p(BitstreamReader *bs);

#endif


typedef struct {
    BitstreamRecordType type;
    union {
        unsigned int count;
        int stop_bit;
    } key;
    union {
        int value;
        uint64_t value64;
        bs_endianness endianness;
    } value;
} BitstreamRecord;


typedef struct BitstreamWriter_s {
    FILE *file;
    unsigned int buffer_size;
    unsigned int buffer;
    struct bs_callback *callback;

    int bits_written;    /*used by open_accumulator and open_recorder*/
    int records_written; /*used by open_recorder*/
    int records_total;   /*used by open_recorder*/
    BitstreamRecord *records;

    void (*write)(struct BitstreamWriter_s* bs,
                  unsigned int count,
                  int value);

    void (*write_signed)(struct BitstreamWriter_s* bs,
                         unsigned int count,
                         int value);

    void (*write_64)(struct BitstreamWriter_s* bs,
                     unsigned int count,
                     uint64_t value);

    void (*write_unary)(struct BitstreamWriter_s* bs,
                        int stop_bit,
                        int value);

    void (*byte_align)(struct BitstreamWriter_s* bs);

    void (*set_endianness)(struct BitstreamWriter_s* bs,
                           bs_endianness endianness);
} BitstreamWriter;


BitstreamWriter*
bs_open_w(FILE *f, bs_endianness endianness);

BitstreamWriter*
bs_open_accumulator(void);

BitstreamWriter*
bs_open_recorder(void);

/*this closes bs's open file, if any,
  deallocates any recorded output (for bs_open_accumulator BitstreamWriters)
  and frees any callbacks before deallocating the bs struct*/
void
bs_close_w(BitstreamWriter *bs);

/*this deallocates any recorded output
  (for bs_open_accumulator BitstreamWriters)
  and frees any callbacks before deallocating the bs struct
  it does not close any open FILE object but does fflush output*/
void
bs_free_w(BitstreamWriter *bs);

/*adds a callback function, which is called on every byte written
  the function's arguments are the written byte and a generic
  pointer to some other data structure
 */
void
bs_add_callback_w(BitstreamWriter *bs, bs_callback_func callback, void *data);

int bs_eof(BitstreamWriter *bs);


/*big-endian writers for concrete bitstreams*/
void
write_bits_actual_be(BitstreamWriter* bs, unsigned int count, int value);

void
write_signed_bits_actual_be(BitstreamWriter* bs, unsigned int count, int value);

void
write_bits64_actual_be(BitstreamWriter* bs, unsigned int count, uint64_t value);

void
byte_align_w_actual_be(BitstreamWriter* bs);

void
set_endianness_actual_be(BitstreamWriter* bs, bs_endianness endianness);


/*little-endian writers for concrete bitstreams*/
void
write_bits_actual_le(BitstreamWriter* bs, unsigned int count, int value);

void
write_signed_bits_actual_le(BitstreamWriter* bs, unsigned int count, int value);

void
write_bits64_actual_le(BitstreamWriter* bs, unsigned int count, uint64_t value);

void
byte_align_w_actual_le(BitstreamWriter* bs);

void
set_endianness_actual_le(BitstreamWriter* bs, bs_endianness endianness);


/*write unary uses the stream's current writers,
  so it has no endian variations*/
void
write_unary_actual(BitstreamWriter* bs, int stop_bit, int value);


/*write methods for a bs_open_accumulator

  The general idea is that one can use an accumulator to determine
  how big a portion of the stream might be, then substitute it
  for an actual stream to perform actual output.
  This "throw away" approach is sometimes faster in practice
  when recording the stream's output adds too much overhead
  vs. simply redoing the calculations.

  For example:
  accumulator = bs_open_accumulator();
  accumulator->write(accumulator, 8, 0x7F);
  accumulator->write_signed(accumulator, 4, 3);
  accumulator->write_signed(accumulator, 4, -1);

  assert(accumulator->bits_written == 16);

  bs_close_w(accumulator);
*/
void
write_bits_accumulator(BitstreamWriter* bs, unsigned int count, int value);

void
write_signed_bits_accumulator(BitstreamWriter* bs, unsigned int count,
                              int value);

void
write_bits64_accumulator(BitstreamWriter* bs, unsigned int count,
                         uint64_t value);

void
write_unary_accumulator(BitstreamWriter* bs, int stop_bit, int value);

void
byte_align_w_accumulator(BitstreamWriter* bs);

void
set_endianness_accumulator(BitstreamWriter* bs, bs_endianness endianness);


/*make room for at least one additional record*/
static inline void
bs_record_resize(BitstreamWriter* bs)
{
    if (bs->records_written >= bs->records_total) {
        bs->records_total *= 2;
        bs->records = realloc(bs->records,
                              sizeof(BitstreamRecord) *
                              bs->records_total);
    }
}

/*write methods for a bs_open_recorder

  The general idea is that one uses a recorder to calculate
  how big a stream might be, then dump it to an actual stream
  if it's found to be the proper size.
  For example:
  stream = bs_open("filename", BS_BIG_ENDIAN);

  recorder = bs_open_recorder();
  recorder->write(recorder, 8, 0x7F);
  recorder->write_signed(recorder, 4, 3);
  recorder->write_signed(recorder, 4, -1);

  if (recorder->bits_written < minimum_bits)
    bs_dump_records(stream, recorder);

  bs_close_w(recorder);
  bs_close_w(stream);
*/
void
write_bits_record(BitstreamWriter* bs, unsigned int count, int value);

void
write_signed_bits_record(BitstreamWriter* bs, unsigned int count, int value);

void
write_bits64_record(BitstreamWriter* bs, unsigned int count, uint64_t value);

void
write_unary_record(BitstreamWriter* bs, int stop_bit, int value);

void
byte_align_w_record(BitstreamWriter* bs);

void
set_endianness_record(BitstreamWriter* bs, bs_endianness endianness);


void
bs_dump_records(BitstreamWriter* target, BitstreamWriter* source);

/*clear the recorded output and reset for new output*/
static inline void
bs_reset_recorder(BitstreamWriter* bs)
{
    bs->bits_written = bs->records_written = 0;
}

void
bs_swap_records(BitstreamWriter* a, BitstreamWriter* b);

#endif
