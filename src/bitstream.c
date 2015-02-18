/********************************************************
 Bitstream Library, a module for reading bits of data

 Copyright (C) 2007-2015  Brian Langenberger

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

#include "bitstream.h"
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

struct read_bits {
    unsigned value_size;
    unsigned value;
    state_t state;
};

struct unread_bit {
    int limit_reached;
    state_t state;
};

struct read_unary {
    int continue_;
    unsigned value;
    state_t state;
};

const static struct read_bits read_bits_table_be[0x200][8] =
#include "read_bits_table_be.h"
    ;

const static struct read_bits read_bits_table_le[0x200][8] =
#include "read_bits_table_le.h"
    ;

const static struct read_unary read_unary_table_be[0x200][2] =
#include "read_unary_table_be.h"
    ;

const static struct read_unary read_unary_table_le[0x200][2] =
#include "read_unary_table_le.h"
    ;


/*******************************************************************
 *                       function definitions                      *
 * These are used internally by the bitstream module but shouldn't *
 * be used elsewhere.  Stick with the exposed methods if possible. *
 *******************************************************************/

#define DEF_READ_BITS(FUNC_NAME, RETURN_TYPE)          \
  static RETURN_TYPE                                   \
  FUNC_NAME(BitstreamReader* self, unsigned int count);
DEF_READ_BITS(br_read_bits_f_be, unsigned int)
DEF_READ_BITS(br_read_bits_f_le, unsigned int)
DEF_READ_BITS(br_read_bits_b_be, unsigned int)
DEF_READ_BITS(br_read_bits_b_le, unsigned int)
DEF_READ_BITS(br_read_bits_q_be, unsigned int)
DEF_READ_BITS(br_read_bits_q_le, unsigned int)
DEF_READ_BITS(br_read_bits_e_be, unsigned int)
DEF_READ_BITS(br_read_bits_e_le, unsigned int)
DEF_READ_BITS(br_read_bits_c, unsigned int)
DEF_READ_BITS(br_read_signed_bits_be, int)
DEF_READ_BITS(br_read_signed_bits_le, int)
DEF_READ_BITS(br_read_bits64_f_be, uint64_t)
DEF_READ_BITS(br_read_bits64_f_le, uint64_t)
DEF_READ_BITS(br_read_bits64_b_be, uint64_t)
DEF_READ_BITS(br_read_bits64_b_le, uint64_t)
DEF_READ_BITS(br_read_bits64_q_be, uint64_t)
DEF_READ_BITS(br_read_bits64_q_le, uint64_t)
DEF_READ_BITS(br_read_bits64_e_be, uint64_t)
DEF_READ_BITS(br_read_bits64_e_le, uint64_t)
DEF_READ_BITS(br_read_bits64_c, uint64_t)
DEF_READ_BITS(br_read_signed_bits64_be, int64_t)
DEF_READ_BITS(br_read_signed_bits64_le, int64_t)


#define DEF_READ_BIGINT(FUNC_NAME)   \
    static void                      \
    FUNC_NAME(BitstreamReader* self, \
              unsigned int count,    \
              mpz_t value);
DEF_READ_BIGINT(br_read_bits_bigint_f_be)
DEF_READ_BIGINT(br_read_bits_bigint_f_le)
DEF_READ_BIGINT(br_read_bits_bigint_b_be)
DEF_READ_BIGINT(br_read_bits_bigint_b_le)
DEF_READ_BIGINT(br_read_bits_bigint_q_be)
DEF_READ_BIGINT(br_read_bits_bigint_q_le)
DEF_READ_BIGINT(br_read_bits_bigint_e_be)
DEF_READ_BIGINT(br_read_bits_bigint_e_le)
DEF_READ_BIGINT(br_read_bits_bigint_c)
DEF_READ_BIGINT(br_read_signed_bits_bigint_be)
DEF_READ_BIGINT(br_read_signed_bits_bigint_le)


#define DEF_SKIP(FUNC_NAME)                              \
    static void                                          \
    FUNC_NAME(BitstreamReader* self, unsigned int count);
DEF_SKIP(br_skip_bits_f_be)
DEF_SKIP(br_skip_bits_f_le)
DEF_SKIP(br_skip_bits_b_be)
DEF_SKIP(br_skip_bits_b_le)
DEF_SKIP(br_skip_bits_q_be)
DEF_SKIP(br_skip_bits_q_le)
DEF_SKIP(br_skip_bits_e_be)
DEF_SKIP(br_skip_bits_e_le)
DEF_SKIP(br_skip_bits_c)


#define DEF_UNREAD(FUNC_NAME)                        \
    static void                                      \
    FUNC_NAME(BitstreamReader* self, int unread_bit);

DEF_UNREAD(br_unread_bit_be)
DEF_UNREAD(br_unread_bit_le)
DEF_UNREAD(br_unread_bit_c)

#define DEF_READ_UNARY(FUNC_NAME)                  \
    static unsigned int                            \
    FUNC_NAME(BitstreamReader* self, int stop_bit);
DEF_READ_UNARY(br_read_unary_f_be)
DEF_READ_UNARY(br_read_unary_f_le)
DEF_READ_UNARY(br_read_unary_b_be)
DEF_READ_UNARY(br_read_unary_b_le)
DEF_READ_UNARY(br_read_unary_q_be)
DEF_READ_UNARY(br_read_unary_q_le)
DEF_READ_UNARY(br_read_unary_e_be)
DEF_READ_UNARY(br_read_unary_e_le)
DEF_READ_UNARY(br_read_unary_c)


#define DEF_SKIP_UNARY(FUNC_NAME)                  \
    static void                                    \
    FUNC_NAME(BitstreamReader* self, int stop_bit);
DEF_SKIP_UNARY(br_skip_unary_f_be)
DEF_SKIP_UNARY(br_skip_unary_f_le)
DEF_SKIP_UNARY(br_skip_unary_b_be)
DEF_SKIP_UNARY(br_skip_unary_b_le)
DEF_SKIP_UNARY(br_skip_unary_q_be)
DEF_SKIP_UNARY(br_skip_unary_q_le)
DEF_SKIP_UNARY(br_skip_unary_e_be)
DEF_SKIP_UNARY(br_skip_unary_e_le)
DEF_SKIP_UNARY(br_skip_unary_c)


#define DEF_SET_ENDIANNESS(FUNC_NAME)                           \
    static void                                                 \
    FUNC_NAME(BitstreamReader* self, bs_endianness endianness);
DEF_SET_ENDIANNESS(br_set_endianness_f)
DEF_SET_ENDIANNESS(br_set_endianness_b)
DEF_SET_ENDIANNESS(br_set_endianness_q)
DEF_SET_ENDIANNESS(br_set_endianness_e)
DEF_SET_ENDIANNESS(br_set_endianness_c)


#define DEF_READ_HUFFMAN_CODE(FUNC_NAME)                         \
    static int                                                   \
    FUNC_NAME(BitstreamReader* self, br_huffman_table_t table[]);
DEF_READ_HUFFMAN_CODE(br_read_huffman_code_file)
DEF_READ_HUFFMAN_CODE(br_read_huffman_code_b)
DEF_READ_HUFFMAN_CODE(br_read_huffman_code_q)
DEF_READ_HUFFMAN_CODE(br_read_huffman_code_e)
DEF_READ_HUFFMAN_CODE(br_read_huffman_code_c)


#define DEF_READ_BYTES(FUNC_NAME)      \
    static void                        \
    FUNC_NAME(BitstreamReader* self,   \
              uint8_t* bytes,          \
              unsigned int byte_count);
DEF_READ_BYTES(br_read_bytes_file)
DEF_READ_BYTES(br_read_bytes_b)
DEF_READ_BYTES(br_read_bytes_q)
DEF_READ_BYTES(br_read_bytes_e)
DEF_READ_BYTES(br_read_bytes_c)


static void
br_skip_bytes(BitstreamReader* self, unsigned int count);


static void
br_parse(BitstreamReader* self, const char* format, ...);


static int
br_byte_aligned(const BitstreamReader* self);


static void
br_byte_align(BitstreamReader* self);


static void
br_add_callback(BitstreamReader* self,
                bs_callback_f callback,
                void* data);


static void
br_push_callback(BitstreamReader* self,
                 struct bs_callback *callback);


static void
br_pop_callback(BitstreamReader* self,
                struct bs_callback *callback);


static void
br_call_callbacks(BitstreamReader* self,
                  uint8_t byte);


#define DEF_BR_GETPOS(FUNC_NAME)     \
    static br_pos_t*                 \
    FUNC_NAME(BitstreamReader* self);
DEF_BR_GETPOS(br_getpos_file)
DEF_BR_GETPOS(br_getpos_b)
DEF_BR_GETPOS(br_getpos_q)
DEF_BR_GETPOS(br_getpos_e)
DEF_BR_GETPOS(br_getpos_c)


#define DEF_BR_SETPOS(FUNC_NAME)                    \
    static void                                     \
    FUNC_NAME(BitstreamReader* self, br_pos_t* pos);
DEF_BR_SETPOS(br_setpos_file)
DEF_BR_SETPOS(br_setpos_b)
DEF_BR_SETPOS(br_setpos_q)
DEF_BR_SETPOS(br_setpos_e)
DEF_BR_SETPOS(br_setpos_c)


#define DEF_BR_POSDEL(FUNC_NAME) \
    static void                  \
    FUNC_NAME(br_pos_t* pos);
DEF_BR_POSDEL(br_pos_del_f)
DEF_BR_POSDEL(br_pos_del_b)
DEF_BR_POSDEL(br_pos_del_q)
DEF_BR_POSDEL(br_pos_del_e)


#define DEF_BR_SEEK(FUNC_NAME)                                        \
    static void                                                       \
    FUNC_NAME(BitstreamReader* self, long position, bs_whence whence);
DEF_BR_SEEK(br_seek_file)
DEF_BR_SEEK(br_seek_b)
DEF_BR_SEEK(br_seek_q)
DEF_BR_SEEK(br_seek_e)


#define DEF_BR_SIZE(FUNC_NAME, TYPE) \
    static unsigned                  \
    FUNC_NAME(const TYPE self);
DEF_BR_SIZE(br_size_f_e_c, BitstreamReader*)
DEF_BR_SIZE(br_size_b, BitstreamReader*)
DEF_BR_SIZE(br_size_q, BitstreamQueue*)


/*bs->substream(bs, bytes)  method*/
static BitstreamReader*
br_substream(BitstreamReader* self, unsigned bytes);


/*bs->enqueue(bs, bytes, queue)  method*/
static void
br_enqueue(BitstreamReader* self, unsigned bytes, BitstreamQueue* queue);


/*converts all read methods to ones that generate I/O errors
  in the event someone tries to read from a stream
  after it's been closed*/
static void
br_close_methods(BitstreamReader* self);


#define DEF_BR_CLOSE_INTERNAL(FUNC_NAME, TYPE) \
    static void                                \
    FUNC_NAME(TYPE self);
DEF_BR_CLOSE_INTERNAL(br_close_internal_stream_f, BitstreamReader*)
DEF_BR_CLOSE_INTERNAL(br_close_internal_stream_b, BitstreamReader*)
DEF_BR_CLOSE_INTERNAL(br_close_internal_stream_q, BitstreamQueue*)
DEF_BR_CLOSE_INTERNAL(br_close_internal_stream_e, BitstreamReader*)
DEF_BR_CLOSE_INTERNAL(br_close_internal_stream_c, BitstreamReader*)


#define DEF_BR_FREE(FUNC_NAME, TYPE) \
    static void                      \
    FUNC_NAME(TYPE self);
DEF_BR_FREE(br_free_f, BitstreamReader*)
DEF_BR_FREE(br_free_b, BitstreamReader*)
DEF_BR_FREE(br_free_q, BitstreamQueue*)
DEF_BR_FREE(br_free_e, BitstreamReader*)


static void
br_close(BitstreamReader* self);
static void
br_close_q(BitstreamQueue* self);


static void
br_push_q(BitstreamQueue* self, unsigned byte_count, const uint8_t* data);


static void
br_reset_q(BitstreamQueue* self);


#define DEF_WRITE(FUNC_NAME, VALUE_TYPE) \
    static void                          \
    FUNC_NAME(BitstreamWriter* self,     \
              unsigned int count,        \
              VALUE_TYPE value);
DEF_WRITE(bw_write_bits_f_be, unsigned int)
DEF_WRITE(bw_write_bits_f_le, unsigned int)
DEF_WRITE(bw_write_bits_e_be, unsigned int)
DEF_WRITE(bw_write_bits_e_le, unsigned int)
DEF_WRITE(bw_write_bits_r_be, unsigned int)
DEF_WRITE(bw_write_bits_r_le, unsigned int)
DEF_WRITE(bw_write_bits_a, unsigned int)
DEF_WRITE(bw_write_bits_c, unsigned int)
DEF_WRITE(bw_write_signed_bits_be, int)
DEF_WRITE(bw_write_signed_bits_le, int)
DEF_WRITE(bw_write_bits64_f_be, uint64_t)
DEF_WRITE(bw_write_bits64_f_le, uint64_t)
DEF_WRITE(bw_write_bits64_e_be, uint64_t)
DEF_WRITE(bw_write_bits64_e_le, uint64_t)
DEF_WRITE(bw_write_bits64_r_be, uint64_t)
DEF_WRITE(bw_write_bits64_r_le, uint64_t)
DEF_WRITE(bw_write_bits64_a, uint64_t)
DEF_WRITE(bw_write_bits64_c, uint64_t)
DEF_WRITE(bw_write_signed_bits64_be, int64_t)
DEF_WRITE(bw_write_signed_bits64_le, int64_t)


#define DEF_WRITE_BIGINT(FUNC_NAME)  \
    static void                      \
    FUNC_NAME(BitstreamWriter* self, \
              unsigned int count,    \
              const mpz_t value);
DEF_WRITE_BIGINT(bw_write_bits_bigint_f_be)
DEF_WRITE_BIGINT(bw_write_bits_bigint_f_le)
DEF_WRITE_BIGINT(bw_write_bits_bigint_e_be)
DEF_WRITE_BIGINT(bw_write_bits_bigint_e_le)
DEF_WRITE_BIGINT(bw_write_bits_bigint_r_be)
DEF_WRITE_BIGINT(bw_write_bits_bigint_r_le)
DEF_WRITE_BIGINT(bw_write_bits_bigint_a)
DEF_WRITE_BIGINT(bw_write_bits_bigint_c)
DEF_WRITE_BIGINT(bw_write_signed_bits_bigint_be)
DEF_WRITE_BIGINT(bw_write_signed_bits_bigint_le)


static void
bw_write_unary(BitstreamWriter* self, int stop_bit, unsigned int value);

static void
bw_write_unary_a(BitstreamWriter *self, int stop_bit, unsigned int value);


#define DEF_BW_SET_ENDIANNESS(FUNC_NAME)                       \
    static void                                                \
    FUNC_NAME(BitstreamWriter* self, bs_endianness endianness);
DEF_BW_SET_ENDIANNESS(bw_set_endianness_f)
DEF_BW_SET_ENDIANNESS(bw_set_endianness_e)
DEF_BW_SET_ENDIANNESS(bw_set_endianness_r)
DEF_BW_SET_ENDIANNESS(bw_set_endianness_a)
DEF_BW_SET_ENDIANNESS(bw_set_endianness_c)


static int
bw_write_huffman(BitstreamWriter* self,
                 bw_huffman_table_t table[],
                 int value);


#define DEF_WRITE_BYTES(FUNC_NAME)   \
    static void                      \
    FUNC_NAME(BitstreamWriter* self, \
              const uint8_t* bytes,  \
              unsigned int count);
DEF_WRITE_BYTES(bw_write_bytes_file)
DEF_WRITE_BYTES(bw_write_bytes_e)
DEF_WRITE_BYTES(bw_write_bytes_r)
DEF_WRITE_BYTES(bw_write_bytes_a)
DEF_WRITE_BYTES(bw_write_bytes_c)


static void
bw_build(BitstreamWriter* self, const char* format, ...);


static int
bw_byte_aligned(const BitstreamWriter* self);


static void
bw_byte_align(BitstreamWriter* self);


#define DEF_FLUSH(FUNC_NAME)         \
    static void                      \
    FUNC_NAME(BitstreamWriter* self);
DEF_FLUSH(bw_flush_f)
DEF_FLUSH(bw_flush_r_a_c)
DEF_FLUSH(bw_flush_e)


#define DEF_BW_GETPOS(FUNC_NAME)     \
    static bw_pos_t*                 \
    FUNC_NAME(BitstreamWriter* self);
DEF_BW_GETPOS(bw_getpos_file)
DEF_BW_GETPOS(bw_getpos_e)
DEF_BW_GETPOS(bw_getpos_r)
DEF_BW_GETPOS(bw_getpos_c)


#define DEF_BW_SETPOS(FUNC_NAME)                          \
    static void                                           \
    FUNC_NAME(BitstreamWriter* self, const bw_pos_t* pos);
DEF_BW_SETPOS(bw_setpos_file)
DEF_BW_SETPOS(bw_setpos_e)
DEF_BW_SETPOS(bw_setpos_r)
DEF_BW_SETPOS(bw_setpos_c)


#define DEF_BW_POSDEL(FUNC_NAME) \
    static void                  \
    FUNC_NAME(bw_pos_t* pos);
DEF_BW_POSDEL(bw_pos_del_f)
DEF_BW_POSDEL(bw_pos_del_e)
DEF_BW_POSDEL(bw_pos_del_r)


static void
bw_close_methods(BitstreamWriter* self);


#define DEF_BW_CLOSE_INTERNAL(FUNC_NAME, TYPE) \
    static void                                \
    FUNC_NAME(TYPE self);
DEF_BW_CLOSE_INTERNAL(bw_close_internal_stream_f, BitstreamWriter*)
DEF_BW_CLOSE_INTERNAL(bw_close_internal_stream_e, BitstreamWriter*)
DEF_BW_CLOSE_INTERNAL(bw_close_internal_stream_cf, BitstreamWriter*)
DEF_BW_CLOSE_INTERNAL(bw_close_internal_stream_r, BitstreamRecorder*)
DEF_BW_CLOSE_INTERNAL(bw_close_internal_stream_a, BitstreamAccumulator*)


#define DEF_BW_FREE(FUNC_NAME, TYPE) \
    static void                      \
    FUNC_NAME(TYPE self);
DEF_BW_FREE(bw_free_f, BitstreamWriter*)
DEF_BW_FREE(bw_free_e, BitstreamWriter*)
DEF_BW_FREE(bw_free_r, BitstreamRecorder*)
DEF_BW_FREE(bw_free_a, BitstreamAccumulator*)


static void
bw_close_f_e(BitstreamWriter* self);
static void
bw_close_r(BitstreamRecorder* self);
static void
bw_close_a(BitstreamAccumulator* self);


static unsigned int
bw_bits_written_r(const BitstreamRecorder* self);


static unsigned int
bw_bytes_written_r(const BitstreamRecorder* self);


static void
bw_reset_r(BitstreamRecorder* self);


static void
bw_copy_r(const BitstreamRecorder* self, BitstreamWriter* target);


static const uint8_t*
bw_data_r(const BitstreamRecorder* self);

static unsigned int
bw_bits_written_a(const BitstreamAccumulator* self);


static unsigned int
bw_bytes_written_a(const BitstreamAccumulator* self);


static void
bw_reset_a(BitstreamAccumulator* self);


static void
bw_add_callback(BitstreamWriter* self,
                bs_callback_f callback,
                void *data);


static void
bw_push_callback(BitstreamWriter* self,
                 struct bs_callback *callback);


static void
bw_pop_callback(BitstreamWriter* self,
                struct bs_callback *callback);


static void
bw_call_callbacks(BitstreamWriter* self,
                  uint8_t byte);


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

static inline unsigned
br_buf_size(const struct br_buffer *buf)
{
    return buf->size - buf->pos;
}

/*appends the given data to the buffer*/
static void
br_buf_extend(struct br_buffer *buf, const uint8_t *data, unsigned size)
{
    const unsigned new_size = buf->size + size;
    buf->data = realloc(buf->data, new_size);
    memcpy(buf->data + buf->size, data, size);
    buf->size = new_size;
}

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
static unsigned
br_buf_read(struct br_buffer *buf, uint8_t *data, unsigned size)
{
    const unsigned remaining_space = buf->size - buf->pos;
    const unsigned to_read = MIN(size, remaining_space);
    memcpy(data, buf->data + buf->pos, to_read);
    buf->pos += to_read;
    return to_read;
}

/*analagous to fseek, sets a position in the buffer*/
static int
br_buf_fseek(struct br_buffer *buf, long position, int whence);



/*******************************************************************
 *                          queue-specific                         *
 *******************************************************************/

struct br_queue {
    uint8_t *data;         /*data bytes*/
    unsigned pos;          /*current position of reader*/
    unsigned size;         /*amount of actually populated bytes*/
    unsigned maximum_size; /*total size of "data"*/
    unsigned pos_count;    /*number of live getpos positions*/
};

static inline struct br_queue*
br_queue_new(void)
{
    struct br_queue *queue = malloc(sizeof(struct br_queue));
    queue->data = NULL;
    queue->pos = 0;
    queue->size = 0;
    queue->maximum_size = 0;
    queue->pos_count = 0;
    return queue;
}

static inline void
br_queue_free(struct br_queue *buf)
{
    free(buf->data);
    free(buf);
}

static inline int
br_queue_getc(struct br_queue *buf)
{
    if (buf->pos < buf->size) {
        return buf->data[buf->pos++];
    } else {
        return EOF;
    }
}

static unsigned
br_queue_read(struct br_queue *buf, uint8_t *data, unsigned size)
{
    const unsigned remaining_space = buf->size - buf->pos;
    const unsigned to_read = MIN(size, remaining_space);
    memcpy(data, buf->data + buf->pos, to_read);
    buf->pos += to_read;
    return to_read;
}

/*analagous to fseek, sets position in the queue*/
static int
br_queue_fseek(struct br_queue *buf, long position, int whence);

/*returns the number of bytes available to be read*/
static inline unsigned
br_queue_size(const struct br_queue *buf)
{
    return buf->size - buf->pos;
}

/*returns the number of bytes that can be written before resizing*/
static inline unsigned
br_queue_available_size(const struct br_queue *buf)
{
    return buf->maximum_size - buf->size;
}

/*resize queue to hold the given number of additional bytes*/
static void
br_queue_resize_for(struct br_queue *buf, unsigned additional_bytes)
{
    unsigned current_space;

    /*garbage-collect initial data if there is any
      and there are no outstanding getpos positions*/
    if (buf->pos && (!buf->pos_count)) {
        const unsigned buf_size = br_queue_size(buf);
        if (buf_size) {
            memmove(buf->data, buf->data + buf->pos, buf_size);
        }
        buf->pos = 0;
        buf->size = buf_size;
    }

    /*if additional space is still required,
      realloc more space to fit*/
    current_space = br_queue_available_size(buf);

    if (current_space < additional_bytes) {
        buf->maximum_size += (additional_bytes - current_space);
        buf->data = realloc(buf->data, buf->maximum_size);
    }
}

/*returns the tail of the queue where new bytes can be added*/
static inline uint8_t*
br_queue_end(struct br_queue *buf)
{
    return buf->data + buf->size;
}


/*******************************************************************
 *                       write buffer-specific                     *
 *******************************************************************/

struct bw_buffer {
    unsigned pos;          /*the current position in the buffer*/
    unsigned max_pos;      /*the farthest written data*/
    unsigned buffer_size;  /*the total buffer size*/
    int resizable;         /*whether the buffer is resizable*/
    uint8_t* buffer;       /*the buffer data itself*/
};

static inline struct bw_buffer*
bw_buf_new(unsigned maximum_size)
{
    struct bw_buffer* buf = malloc(sizeof(struct bw_buffer));
    if (maximum_size) {
        buf->pos = buf->max_pos = 0;
        buf->buffer_size = maximum_size;
        buf->resizable = 0;
        buf->buffer = malloc(maximum_size);
        return buf;
    } else {
        buf->pos = buf->max_pos = buf->buffer_size = 0;
        buf->resizable = 1;
        buf->buffer = NULL;
        return buf;
    }
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
        if (buf->resizable) {
            buf->buffer_size += 4096;
            buf->buffer = realloc(buf->buffer, buf->buffer_size);
        } else {
            return EOF;
        }
    }
    buf->buffer[buf->pos++] = (uint8_t)c;
    buf->max_pos = MAX(buf->max_pos, buf->pos);
    return c;
}

static int
bw_buf_write(struct bw_buffer* buf, const uint8_t *data, unsigned data_size)
{
    const unsigned available_bytes = buf->buffer_size - buf->pos;
    if (available_bytes < data_size) {
        if (buf->resizable) {
            buf->buffer_size += (data_size - available_bytes);
            buf->buffer = realloc(buf->buffer, buf->buffer_size);
        } else {
            return 1;
        }
    }
    memcpy(buf->buffer + buf->pos, data, data_size);
    buf->pos += data_size;
    buf->max_pos = MAX(buf->max_pos, buf->pos);
    return 0;
}

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


/*returns a base BitstreamReader with many fields filled in
  and the rest to be filled in by the final implementation*/
static BitstreamReader*
__base_bitstreamreader__(bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
    bs->endianness = endianness;
    /*bs->type = ???*/
    /*bs->input.??? = ???*/
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        /*bs->read = ???*/
        bs->read_signed = br_read_signed_bits_be;
        /*bs->read_64 = ???*/
        bs->read_signed_64 = br_read_signed_bits64_be;
        /*bs->read_bigint = ???*/
        bs->read_signed_bigint = br_read_signed_bits_bigint_be;
        /*bs->skip = ???*/
        bs->unread = br_unread_bit_be;
        /*bs->read_unary = ???*/
        /*bs->skip_unary = ???*/
        break;
    case BS_LITTLE_ENDIAN:
        /*bs->read = ???*/
        bs->read_signed = br_read_signed_bits_le;
        /*bs->read_64 = ???*/
        bs->read_signed_64 = br_read_signed_bits64_le;
        /*bs->read_bigint = ???*/
        bs->read_signed_bigint = br_read_signed_bits_bigint_le;
        /*bs->skip = ???*/
        bs->unread = br_unread_bit_le;
        /*bs->read_unary = ???*/
        /*bs->skip_unary = ???*/
        break;
    }

    /*bs->set_endianness = ???*/
    /*bs->read_huffman_code = ???*/
    /*bs->read_bytes = ???*/
    bs->skip_bytes = br_skip_bytes;
    bs->parse = br_parse;
    bs->byte_aligned = br_byte_aligned;
    bs->byte_align = br_byte_align;

    bs->add_callback = br_add_callback;
    bs->push_callback = br_push_callback;
    bs->pop_callback = br_pop_callback;
    bs->call_callbacks = br_call_callbacks;

    /*bs->getpos = ???*/
    /*bs->setpos = ???*/
    /*bs->seek = ???*/

    bs->substream = br_substream;
    bs->enqueue = br_enqueue;

    /*bs->size = ???*/

    /*bs->close_internal_stream = ???*/
    /*bs->free = ???*/
    bs->close = br_close;

    return bs;
}


BitstreamReader*
br_open(FILE *f, bs_endianness endianness)
{
    BitstreamReader *bs = __base_bitstreamreader__(endianness);
    bs->type = BR_FILE;
    bs->input.file = f;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_f_be;
        bs->read_64 = br_read_bits64_f_be;
        bs->read_bigint = br_read_bits_bigint_f_be;
        bs->skip = br_skip_bits_f_be;
        bs->read_unary = br_read_unary_f_be;
        bs->skip_unary = br_skip_unary_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_f_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->read_bigint = br_read_bits_bigint_f_le;
        bs->skip = br_skip_bits_f_le;
        bs->read_unary = br_read_unary_f_le;
        bs->skip_unary = br_skip_unary_f_le;
        break;
    }

    bs->set_endianness = br_set_endianness_f;
    bs->read_huffman_code = br_read_huffman_code_file;
    bs->read_bytes = br_read_bytes_file;

    bs->getpos = br_getpos_file;
    bs->setpos = br_setpos_file;
    bs->seek = br_seek_file;

    bs->size = br_size_f_e_c;

    bs->close_internal_stream = br_close_internal_stream_f;
    bs->free = br_free_f;

    return bs;
}


BitstreamReader*
br_open_buffer(const uint8_t *buffer,
               unsigned buffer_size,
               bs_endianness endianness)
{
    BitstreamReader *bs = __base_bitstreamreader__(endianness);
    bs->type = BR_BUFFER;
    bs->input.buffer = br_buf_new();
    br_buf_extend(bs->input.buffer, buffer, buffer_size);

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_b_be;
        bs->read_64 = br_read_bits64_b_be;
        bs->read_bigint = br_read_bits_bigint_b_be;
        bs->skip = br_skip_bits_b_be;
        bs->read_unary = br_read_unary_b_be;
        bs->skip_unary = br_skip_unary_b_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_b_le;
        bs->read_64 = br_read_bits64_b_le;
        bs->read_bigint = br_read_bits_bigint_b_le;
        bs->skip = br_skip_bits_b_le;
        bs->read_unary = br_read_unary_b_le;
        bs->skip_unary = br_skip_unary_b_le;
        break;
    }

    bs->set_endianness = br_set_endianness_b;
    bs->read_huffman_code = br_read_huffman_code_b;
    bs->read_bytes = br_read_bytes_b;

    bs->getpos = br_getpos_b;
    bs->setpos = br_setpos_b;
    bs->seek = br_seek_b;

    bs->size = br_size_b;

    bs->close_internal_stream = br_close_internal_stream_b;
    bs->free = br_free_b;

    return bs;
}

BitstreamQueue*
br_open_queue(bs_endianness endianness)
{
    BitstreamQueue *bs = malloc(sizeof(BitstreamQueue));

    bs->endianness = endianness;
    bs->type = BR_QUEUE;
    bs->input.queue = br_queue_new();
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_q_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_q_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->read_bigint = br_read_bits_bigint_q_be;
        bs->read_signed_bigint = br_read_signed_bits_bigint_be;
        bs->skip = br_skip_bits_q_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_q_be;
        bs->skip_unary = br_skip_unary_q_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_q_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_q_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->read_bigint = br_read_bits_bigint_q_le;
        bs->read_signed_bigint = br_read_signed_bits_bigint_le;
        bs->skip = br_skip_bits_q_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_q_le;
        bs->skip_unary = br_skip_unary_q_le;
        break;
    }

    bs->set_endianness = br_set_endianness_q;
    bs->read_huffman_code = br_read_huffman_code_q;
    bs->read_bytes = br_read_bytes_q;
    bs->skip_bytes = br_skip_bytes;
    bs->parse = br_parse;
    bs->byte_aligned = br_byte_aligned;
    bs->byte_align = br_byte_align;

    bs->add_callback = br_add_callback;
    bs->push_callback = br_push_callback;
    bs->pop_callback = br_pop_callback;
    bs->call_callbacks = br_call_callbacks;

    bs->getpos = br_getpos_q;
    bs->setpos = br_setpos_q;
    bs->seek = br_seek_q;

    bs->substream = br_substream;
    bs->enqueue = br_enqueue;

    bs->size = br_size_q;

    bs->close_internal_stream = br_close_internal_stream_q;
    bs->free = br_free_q;
    bs->close = br_close_q;

    bs->push = br_push_q;
    bs->reset = br_reset_q;

    return bs;
}

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
                 ext_free_f free)
{
    BitstreamReader *bs = __base_bitstreamreader__(endianness);
    bs->type = BR_EXTERNAL;
    bs->input.external = ext_open_r(user_data,
                                    buffer_size,
                                    read,
                                    setpos,
                                    getpos,
                                    free_pos,
                                    seek,
                                    close,
                                    free);

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_e_be;
        bs->read_64 = br_read_bits64_e_be;
        bs->read_bigint = br_read_bits_bigint_e_be;
        bs->skip = br_skip_bits_e_be;
        bs->read_unary = br_read_unary_e_be;
        bs->skip_unary = br_skip_unary_e_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_e_le;
        bs->read_64 = br_read_bits64_e_le;
        bs->read_bigint = br_read_bits_bigint_e_le;
        bs->skip = br_skip_bits_e_le;
        bs->read_unary = br_read_unary_e_le;
        bs->skip_unary = br_skip_unary_e_le;
        break;
    }

    bs->set_endianness = br_set_endianness_e;
    bs->read_huffman_code = br_read_huffman_code_e;
    bs->read_bytes = br_read_bytes_e;

    bs->setpos = br_setpos_e;
    bs->getpos = br_getpos_e;
    bs->seek = br_seek_e;

    bs->size = br_size_f_e_c;

    bs->close_internal_stream = br_close_internal_stream_e;
    bs->free = br_free_e;

    return bs;
}

/*These are helper macros for unpacking the results
  of the various jump tables in a less error-prone fashion.*/
#define NEW_STATE(x) (0x100 | (x))

#define FUNC_READ_BITS_BE(FUNC_NAME, RETURN_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    static RETURN_TYPE                                                  \
    FUNC_NAME(BitstreamReader* self, unsigned int count)                \
    {                                                                   \
        struct read_bits result = {0, 0, self->state};                  \
        register RETURN_TYPE accumulator = 0;                           \
                                                                        \
        while (count > 0) {                                             \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            result =                                                    \
                read_bits_table_be[result.state][MIN(count, 8) - 1];    \
                                                                        \
            accumulator =                                               \
                ((accumulator << result.value_size) | result.value);    \
                                                                        \
            count -= result.value_size;                                 \
        }                                                               \
                                                                        \
        self->state = result.state;                                     \
        return accumulator;                                             \
    }

#define FUNC_READ_BITS_LE(FUNC_NAME, RETURN_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    static RETURN_TYPE                                                  \
    FUNC_NAME(BitstreamReader* self, unsigned int count)                \
    {                                                                   \
        struct read_bits result = {0, 0, self->state};                  \
        register RETURN_TYPE accumulator = 0;                           \
        register unsigned bit_offset = 0;                               \
                                                                        \
        while (count > 0) {                                             \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            result =                                                    \
                read_bits_table_le[result.state][MIN(count, 8) - 1];    \
                                                                        \
            accumulator |=                                              \
                ((RETURN_TYPE)(result.value) << bit_offset);            \
                                                                        \
            count -= result.value_size;                                 \
            bit_offset += result.value_size;                            \
        }                                                               \
                                                                        \
        self->state = result.state;                                     \
        return accumulator;                                             \
    }

FUNC_READ_BITS_BE(br_read_bits_f_be,
                  unsigned int, fgetc, self->input.file)
FUNC_READ_BITS_LE(br_read_bits_f_le,
                  unsigned int, fgetc, self->input.file)
FUNC_READ_BITS_BE(br_read_bits_b_be,
                  unsigned int, br_buf_getc, self->input.buffer)
FUNC_READ_BITS_LE(br_read_bits_b_le,
                  unsigned int, br_buf_getc, self->input.buffer)
FUNC_READ_BITS_BE(br_read_bits_q_be,
                  unsigned int, br_queue_getc, self->input.queue)
FUNC_READ_BITS_LE(br_read_bits_q_le,
                  unsigned int, br_queue_getc, self->input.queue)
FUNC_READ_BITS_BE(br_read_bits_e_be,
                  unsigned int, ext_getc, self->input.external)
FUNC_READ_BITS_LE(br_read_bits_e_le,
                  unsigned int, ext_getc, self->input.external)
FUNC_READ_BITS_BE(br_read_bits64_f_be,
                  uint64_t, fgetc, self->input.file)
FUNC_READ_BITS_LE(br_read_bits64_f_le,
                  uint64_t, fgetc, self->input.file)
FUNC_READ_BITS_BE(br_read_bits64_b_be,
                  uint64_t, br_buf_getc, self->input.buffer)
FUNC_READ_BITS_LE(br_read_bits64_b_le,
                  uint64_t, br_buf_getc, self->input.buffer)
FUNC_READ_BITS_BE(br_read_bits64_q_be,
                  uint64_t, br_queue_getc, self->input.queue)
FUNC_READ_BITS_LE(br_read_bits64_q_le,
                  uint64_t, br_queue_getc, self->input.queue)
FUNC_READ_BITS_BE(br_read_bits64_e_be,
                  uint64_t, ext_getc, self->input.external)
FUNC_READ_BITS_LE(br_read_bits64_e_le,
                  uint64_t, ext_getc, self->input.external)

static unsigned int
br_read_bits_c(BitstreamReader* self, unsigned int count)
{
    br_abort(self);
    return 0;
}

static uint64_t
br_read_bits64_c(BitstreamReader* self, unsigned int count)
{
    br_abort(self);
    return 0;
}

static int
br_read_signed_bits_be(BitstreamReader* self, unsigned int count)
{
    if (!self->read(self, 1)) {
        return self->read(self, count - 1);
    } else {
        return self->read(self, count - 1) - (1 << (count - 1));
    }
}

static int
br_read_signed_bits_le(BitstreamReader* self, unsigned int count)
{
    const int unsigned_value = self->read(self, count - 1);

    if (!self->read(self, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}

static int64_t
br_read_signed_bits64_be(BitstreamReader* self, unsigned int count)
{
    if (!self->read(self, 1)) {
        return self->read_64(self, count - 1);
    } else {
        return self->read_64(self, count - 1) - (1ll << (count - 1));
    }
}

static int64_t
br_read_signed_bits64_le(BitstreamReader* self, unsigned int count)
{
    const int64_t unsigned_value = self->read_64(self, count - 1);

    if (!self->read(self, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1ll << (count - 1));
    }
}

#define FUNC_READ_BITS_BIGINT_BE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    static void                                                       \
    FUNC_NAME(BitstreamReader* self, unsigned int count, mpz_t value) \
    {                                                                 \
        struct read_bits result = {0, 0, self->state};                \
        mpz_t result_value;                                           \
        mpz_init(result_value);                                       \
        mpz_set_ui(value, 0);                                         \
                                                                      \
        while (count > 0) {                                           \
            if (result.state == 0) {                                  \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);            \
                if (byte != EOF) {                                    \
                    struct bs_callback* callback;                     \
                    result.state = NEW_STATE(byte);                   \
                    for (callback = self->callbacks;                  \
                         callback != NULL;                            \
                         callback = callback->next)                   \
                        callback->callback((uint8_t)byte,             \
                                           callback->data);           \
                } else {                                              \
                    mpz_clear(result_value);                          \
                    br_abort(self);                                   \
                }                                                     \
            }                                                         \
                                                                      \
            result =                                                  \
                read_bits_table_be[result.state][MIN(count, 8) - 1];  \
                                                                      \
            mpz_set_ui(result_value, result.value);                   \
                                                                      \
            /*value <<= result.value_size*/                           \
            mpz_mul_2exp(value, value, result.value_size);            \
                                                                      \
            /*value |= result_value*/                                 \
            mpz_ior(value, value, result_value);                      \
                                                                      \
            count -= result.value_size;                               \
        }                                                             \
                                                                      \
        self->state = result.state;                                   \
        mpz_clear(result_value);                                      \
    }
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_f_be, fgetc,
                         self->input.file)
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_b_be, br_buf_getc,
                         self->input.buffer)
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_q_be, br_queue_getc,
                         self->input.queue)
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_e_be, ext_getc,
                         self->input.external)

#define FUNC_READ_BITS_BIGINT_LE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    static void                                                       \
    FUNC_NAME(BitstreamReader* self, unsigned int count, mpz_t value) \
    {                                                                 \
        struct read_bits result = {0, 0, self->state};                \
        register unsigned bit_offset = 0;                             \
        mpz_t result_value;                                           \
        mpz_init(result_value);                                       \
        mpz_set_ui(value, 0);                                         \
                                                                      \
        while (count > 0) {                                           \
            if (result.state == 0) {                                  \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);            \
                if (byte != EOF) {                                    \
                    struct bs_callback* callback;                     \
                    result.state = NEW_STATE(byte);                   \
                    for (callback = self->callbacks;                  \
                         callback != NULL;                            \
                         callback = callback->next)                   \
                         callback->callback((uint8_t)byte,            \
                                            callback->data);          \
                } else {                                              \
                    mpz_clear(result_value);                          \
                    br_abort(self);                                   \
                }                                                     \
            }                                                         \
                                                                      \
            result =                                                  \
                read_bits_table_le[result.state][MIN(count, 8) - 1];  \
                                                                      \
            mpz_set_ui(result_value, result.value);                   \
                                                                      \
            /*result_value <<= bit_offset*/                           \
            mpz_mul_2exp(result_value, result_value, bit_offset);     \
                                                                      \
            /*value |= result_value*/                                 \
            mpz_ior(value, value, result_value);                      \
                                                                      \
            count -= result.value_size;                               \
            bit_offset += result.value_size;                          \
        }                                                             \
                                                                      \
        self->state = result.state;                                   \
        mpz_clear(result_value);                                      \
    }
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_f_le, fgetc,
                         self->input.file)
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_b_le, br_buf_getc,
                         self->input.buffer)
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_q_le, br_queue_getc,
                         self->input.queue)
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_e_le, ext_getc,
                         self->input.external)

static void
br_read_bits_bigint_c(BitstreamReader* self,
                      unsigned int count,
                      mpz_t value)
{
    br_abort(self);
}

static void
br_read_signed_bits_bigint_be(BitstreamReader* self,
                              unsigned int count,
                              mpz_t value)
{
    if (!self->read(self, 1)) {
        /*unsigned value*/

        self->read_bigint(self, count - 1, value);
    } else {
        /*signed value*/

        mpz_t unsigned_value;
        mpz_t to_subtract;

        mpz_init(unsigned_value);
        if (!setjmp(*br_try(self))) {
            self->read_bigint(self, count - 1, unsigned_value);
            br_etry(self);
        } else {
            /*be sure to free unsigned_value before re-raising error*/
            br_etry(self);
            mpz_clear(unsigned_value);
            br_abort(self);
        }

        /*value = unsigned_value - (1 << (count - 1))*/

        /*to_subtract = 1*/
        mpz_init_set_ui(to_subtract, 1);

        /*to_subtract <<= (count - 1)*/
        mpz_mul_2exp(to_subtract, to_subtract, count - 1);

        /*value = unsigned_value - to_subtract*/
        mpz_sub(value, unsigned_value, to_subtract);

        mpz_clear(unsigned_value);
        mpz_clear(to_subtract);
    }
}

static void
br_read_signed_bits_bigint_le(BitstreamReader* self,
                              unsigned int count,
                              mpz_t value)
{
    mpz_t unsigned_value;
    mpz_init(unsigned_value);

    if (!setjmp(*br_try(self))) {
        self->read_bigint(self, count - 1, unsigned_value);

        if (!self->read(self, 1)) {
            /*unsigned value*/

            mpz_set(value, unsigned_value);
        } else {
            /*signed value*/
            mpz_t to_subtract;

            /*to_subtract = 1*/
            mpz_init_set_ui(to_subtract, 1);

            /*to_subtract <<= (count - 1)*/
            mpz_mul_2exp(to_subtract, to_subtract, count - 1);

            /*value = unsigned_value - to_subtract*/
            mpz_sub(value, unsigned_value, to_subtract);

            mpz_clear(to_subtract);
        }
        br_etry(self);
        mpz_clear(unsigned_value);
    } else {
        /*be sure to free unsigned value before re-raising error*/
        br_etry(self);
        mpz_clear(unsigned_value);
        br_abort(self);
    }
}

#define BUFFER_SIZE 4096


/*the skip_bits functions differ from the read_bits functions
  in that they have no accumulator
  which allows them to skip over a potentially unlimited amount of bits*/
#define FUNC_SKIP_BITS_BE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
  static void                                                   \
  FUNC_NAME(BitstreamReader* self, unsigned int count)          \
  {                                                             \
      if ((self->state == 0) && ((count % 8) == 0)) {           \
          count /= 8;                                           \
          while (count > 0) {                                   \
              const unsigned int byte_count = MIN(BUFFER_SIZE,  \
                                                  count);       \
              static uint8_t dummy[BUFFER_SIZE];                \
              self->read_bytes(self, dummy, byte_count);        \
              count -= byte_count;                              \
          }                                                     \
      } else {                                                  \
          struct read_bits result = {0, 0, self->state};        \
                                                                \
          while (count > 0) {                                   \
              if (result.state == 0) {                          \
                  const int byte = BYTE_FUNC(BYTE_FUNC_ARG);    \
                  if (byte != EOF) {                            \
                      struct bs_callback* callback;             \
                      result.state = NEW_STATE(byte);           \
                      for (callback = self->callbacks;          \
                           callback != NULL;                    \
                           callback = callback->next)           \
                           callback->callback((uint8_t)byte,    \
                                              callback->data);  \
                  } else {                                      \
                      br_abort(self);                           \
                  }                                             \
              }                                                 \
                                                                \
              result = read_bits_table_be[result.state][MIN(count, 8) - 1]; \
                                                                \
              count -= result.value_size;                       \
          }                                                     \
                                                                \
          self->state = result.state;                             \
      }                                                         \
  }
FUNC_SKIP_BITS_BE(br_skip_bits_f_be, fgetc, self->input.file)
FUNC_SKIP_BITS_BE(br_skip_bits_b_be, br_buf_getc, self->input.buffer)
FUNC_SKIP_BITS_BE(br_skip_bits_q_be, br_queue_getc, self->input.queue)
FUNC_SKIP_BITS_BE(br_skip_bits_e_be, ext_getc, self->input.external)

#define FUNC_SKIP_BITS_LE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
  static void                                                  \
  FUNC_NAME(BitstreamReader* self, unsigned int count)         \
  {                                                            \
      if ((self->state == 0) && ((count % 8) == 0)) {          \
          count /= 8;                                          \
          while (count > 0) {                                  \
              const unsigned int byte_count = MIN(BUFFER_SIZE, \
                                                  count);      \
              static uint8_t dummy[BUFFER_SIZE];               \
              self->read_bytes(self, dummy, byte_count);       \
              count -= byte_count;                             \
          }                                                    \
      } else {                                                 \
          struct read_bits result = {0, 0, self->state};       \
                                                               \
          while (count > 0) {                                  \
              if (result.state == 0) {                         \
                  const int byte = BYTE_FUNC(BYTE_FUNC_ARG);   \
                  if (byte != EOF) {                           \
                      struct bs_callback* callback;            \
                      result.state = NEW_STATE(byte);          \
                      for (callback = self->callbacks;         \
                           callback != NULL;                   \
                           callback = callback->next)          \
                           callback->callback((uint8_t)byte,   \
                                              callback->data); \
                  } else {                                     \
                      br_abort(self);                          \
                  }                                            \
              }                                                \
                                                               \
              result = read_bits_table_le[result.state][MIN(count, 8) - 1]; \
                                                               \
              count -= result.value_size;                      \
          }                                                    \
                                                               \
          self->state = result.state;                          \
      }                                                        \
  }
FUNC_SKIP_BITS_LE(br_skip_bits_f_le, fgetc, self->input.file)
FUNC_SKIP_BITS_LE(br_skip_bits_b_le, br_buf_getc, self->input.buffer)
FUNC_SKIP_BITS_LE(br_skip_bits_q_le, br_queue_getc, self->input.queue)
FUNC_SKIP_BITS_LE(br_skip_bits_e_le, ext_getc, self->input.external)

static void
br_skip_bits_c(BitstreamReader* self, unsigned int count)
{
    br_abort(self);
}


static void
br_unread_bit_be(BitstreamReader* self, int unread_bit)
{
    const static struct unread_bit unread_bit_table_be[0x200][2] =
#include "unread_bit_table_be.h"
    ;
    struct unread_bit result = unread_bit_table_be[self->state][unread_bit];
    if (result.limit_reached) {
        br_abort(self);
    } else {
        self->state = result.state;
    }
}

static void
br_unread_bit_le(BitstreamReader* self, int unread_bit)
{
    const struct unread_bit unread_bit_table_le[0x200][2] =
#include "unread_bit_table_le.h"
    ;
    struct unread_bit result = unread_bit_table_le[self->state][unread_bit];
    if (result.limit_reached) {
        br_abort(self);
    } else {
        self->state = result.state;
    }
}

static void
br_unread_bit_c(BitstreamReader* self, int unread_bit)
{
    br_abort(self);
}


#define FUNC_READ_UNARY(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG, UNARY_TABLE) \
    static unsigned int                                                 \
    FUNC_NAME(BitstreamReader* self, int stop_bit)                      \
    {                                                                   \
        struct read_unary result = {0, 0, self->state};                 \
        register unsigned accumulator = 0;                              \
                                                                        \
        do {                                                            \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            result = UNARY_TABLE[result.state][stop_bit];               \
                                                                        \
            accumulator += result.value;                                \
        } while (result.continue_);                                     \
                                                                        \
        self->state = result.state;                                       \
        return accumulator;                                             \
    }

FUNC_READ_UNARY(br_read_unary_f_be,
                fgetc, self->input.file, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_f_le,
                fgetc, self->input.file, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_b_be,
                br_buf_getc, self->input.buffer, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_b_le,
                br_buf_getc, self->input.buffer, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_q_be,
                br_queue_getc, self->input.queue, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_q_le,
                br_queue_getc, self->input.queue, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_e_be,
                ext_getc, self->input.external, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_e_le,
                ext_getc, self->input.external, read_unary_table_le)

static unsigned int
br_read_unary_c(BitstreamReader* self, int stop_bit)
{
    br_abort(self);
    return 0;
}

#define FUNC_SKIP_UNARY(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG, UNARY_TABLE) \
    static void                                                         \
    FUNC_NAME(BitstreamReader* self, int stop_bit)                      \
    {                                                                   \
        struct read_unary result = {0, 0, self->state};                 \
        do {                                                            \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            result = UNARY_TABLE[result.state][stop_bit];               \
        } while (result.continue_);                                     \
                                                                        \
        self->state = result.state;                                     \
    }
FUNC_SKIP_UNARY(br_skip_unary_f_be,
                fgetc, self->input.file, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_f_le,
                fgetc, self->input.file, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_b_be,
                br_buf_getc, self->input.buffer, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_b_le,
                br_buf_getc, self->input.buffer, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_q_be,
                br_queue_getc, self->input.queue, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_q_le,
                br_queue_getc, self->input.queue, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_e_be,
                ext_getc, self->input.external, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_e_le,
                ext_getc, self->input.external, read_unary_table_le)

static void
br_skip_unary_c(BitstreamReader* self, int stop_bit)
{
    br_abort(self);
}


static void
__br_set_endianness__(BitstreamReader* self, bs_endianness endianness)
{
    self->endianness = endianness;
    self->state = 0;
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->read_signed = br_read_signed_bits_le;
        self->read_signed_64 = br_read_signed_bits64_le;
        self->read_signed_bigint = br_read_signed_bits_bigint_le;
        self->unread = br_unread_bit_le;
        break;
    case BS_BIG_ENDIAN:
        self->read_signed = br_read_signed_bits_be;
        self->read_signed_64 = br_read_signed_bits64_be;
        self->read_signed_bigint = br_read_signed_bits_bigint_be;
        self->unread = br_unread_bit_be;
        break;
    }
}

static void
br_set_endianness_f(BitstreamReader* self, bs_endianness endianness)
{
    __br_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->read = br_read_bits_f_le;
        self->read_64 = br_read_bits64_f_le;
        self->read_bigint = br_read_bits_bigint_f_le;
        self->skip = br_skip_bits_f_le;
        self->read_unary = br_read_unary_f_le;
        self->skip_unary = br_skip_unary_f_le;
        break;
    case BS_BIG_ENDIAN:
        self->read = br_read_bits_f_be;
        self->read_64 = br_read_bits64_f_be;
        self->read_bigint = br_read_bits_bigint_f_be;
        self->skip = br_skip_bits_f_be;
        self->read_unary = br_read_unary_f_be;
        self->skip_unary = br_skip_unary_f_be;
        break;
    }
}

static void
br_set_endianness_b(BitstreamReader* self, bs_endianness endianness)
{
    __br_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->read = br_read_bits_b_le;
        self->read_64 = br_read_bits64_b_le;
        self->read_bigint = br_read_bits_bigint_b_le;
        self->skip = br_skip_bits_b_le;
        self->read_unary = br_read_unary_b_le;
        self->skip_unary = br_skip_unary_b_le;
        break;
    case BS_BIG_ENDIAN:
        self->read = br_read_bits_b_be;
        self->read_64 = br_read_bits64_b_be;
        self->read_bigint = br_read_bits_bigint_b_be;
        self->skip = br_skip_bits_b_be;
        self->read_unary = br_read_unary_b_be;
        self->skip_unary = br_skip_unary_b_be;
        break;
    }
}

static void
br_set_endianness_q(BitstreamReader* self, bs_endianness endianness)
{
    __br_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->read = br_read_bits_q_le;
        self->read_64 = br_read_bits64_q_le;
        self->read_bigint = br_read_bits_bigint_q_le;
        self->skip = br_skip_bits_q_le;
        self->read_unary = br_read_unary_q_le;
        self->skip_unary = br_skip_unary_q_le;
        break;
    case BS_BIG_ENDIAN:
        self->read = br_read_bits_q_be;
        self->read_64 = br_read_bits64_q_be;
        self->read_bigint = br_read_bits_bigint_q_be;
        self->skip = br_skip_bits_q_be;
        self->read_unary = br_read_unary_q_be;
        self->skip_unary = br_skip_unary_q_be;
        break;
    }
}

static void
br_set_endianness_e(BitstreamReader* self, bs_endianness endianness)
{
    __br_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->read = br_read_bits_e_le;
        self->read_64 = br_read_bits64_e_le;
        self->read_bigint = br_read_bits_bigint_e_le;
        self->skip = br_skip_bits_e_le;
        self->read_unary = br_read_unary_e_le;
        self->skip_unary = br_skip_unary_e_le;
        break;
    case BS_BIG_ENDIAN:
        self->read = br_read_bits_e_be;
        self->read_64 = br_read_bits64_e_be;
        self->read_bigint = br_read_bits_bigint_e_be;
        self->skip = br_skip_bits_e_be;
        self->read_unary = br_read_unary_e_be;
        self->skip_unary = br_skip_unary_e_be;
        break;
    }
}

static void
br_set_endianness_c(BitstreamReader* self, bs_endianness endianness)
{
    self->endianness = endianness;
}


#define FUNC_READ_HUFFMAN_CODE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    static int                                                      \
    FUNC_NAME(BitstreamReader* self,                                \
              br_huffman_table_t table[])                           \
    {                                                               \
        br_huffman_entry_t entry = table[0][self->state];           \
                                                                    \
        while (entry.continue_) {                                   \
            const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
            if (byte != EOF) {                                      \
                struct bs_callback* callback;                       \
                const state_t state = NEW_STATE(byte);              \
                                                                    \
                for (callback = self->callbacks;                    \
                     callback != NULL;                              \
                     callback = callback->next)                     \
                     callback->callback((uint8_t)byte,              \
                                        callback->data);            \
                                                                    \
                entry = table[entry.node][state];                   \
            } else {                                                \
                br_abort(self);                                     \
            }                                                       \
        }                                                           \
                                                                    \
        self->state = entry.state;                                  \
        return entry.value;                                         \
    }
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_file, fgetc, self->input.file)
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_b, br_buf_getc, self->input.buffer)
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_q, br_queue_getc, self->input.queue)
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_e, ext_getc, self->input.external)

static int
br_read_huffman_code_c(BitstreamReader* self,
                       br_huffman_table_t table[])
{
    br_abort(self);
    return 0;
}


static void
br_read_bytes_file(BitstreamReader* self,
                   uint8_t* bytes,
                   unsigned int byte_count)
{
    if (self->state == 0) {
        /*bit buffer is empty, so perform optimized read*/

        /*fread bytes from file handle to output*/
        if (fread(bytes, sizeof(uint8_t), byte_count, self->input.file) ==
            byte_count) {
            struct bs_callback* callback;
            /*if sufficient bytes were read
              perform callbacks on the read bytes*/
            for (callback = self->callbacks;
                 callback != NULL;
                 callback = callback->next) {
                bs_callback_f callback_func = callback->callback;
                void* callback_data = callback->data;
                unsigned int i;
                for (i = 0; i < byte_count; i++) {
                    callback_func(bytes[i], callback_data);
                }
            }
        } else {
            br_abort(self);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (; byte_count; byte_count--) {
            *bytes++ = self->read(self, 8);
        }
    }
}

#define READ_BYTES_FUNC(FUNC_NAME, READ_FUNC, READ_ARG)               \
  static void                                                         \
  FUNC_NAME(BitstreamReader* self,                                    \
            uint8_t* bytes,                                           \
            unsigned int byte_count)                                  \
  {                                                                   \
      if (self->state == 0) {                                         \
          /*bit buffer is empty, so perform optimized read*/          \
                                                                      \
          /*buf_read bytes from buffer to output*/                    \
          if (READ_FUNC(READ_ARG, bytes, byte_count) == byte_count) { \
              struct bs_callback* callback;                           \
              /*if sufficient bytes were read*/                       \
              /*perform callbacks on the read bytes*/                 \
              for (callback = self->callbacks;                        \
                   callback != NULL;                                  \
                   callback = callback->next) {                       \
                  bs_callback_f callback_func = callback->callback;   \
                  void* callback_data = callback->data;               \
                  unsigned int i;                                     \
                  for (i = 0; i < byte_count; i++) {                  \
                      callback_func(bytes[i], callback_data);         \
                  }                                                   \
              }                                                       \
          } else {                                                    \
              br_abort(self);                                         \
          }                                                           \
      } else {                                                        \
          /*stream is not byte-aligned, so perform multiple reads*/   \
          for (; byte_count; byte_count--) {                          \
              *bytes++ = self->read(self, 8);                         \
          }                                                           \
      }                                                               \
  }
READ_BYTES_FUNC(br_read_bytes_b, br_buf_read, self->input.buffer)
READ_BYTES_FUNC(br_read_bytes_q, br_queue_read, self->input.queue)
READ_BYTES_FUNC(br_read_bytes_e, ext_fread, self->input.external)

static void
br_read_bytes_c(BitstreamReader* self,
                uint8_t* bytes,
                unsigned int byte_count)
{
    br_abort(self);
}


static void
br_skip_bytes(BitstreamReader* self, unsigned int count)
{
    /*try to generate large, byte-aligned chunks of bit skips*/
    while (count > 0) {
        const unsigned int byte_count = MIN(BUFFER_SIZE, count);
        static uint8_t dummy[BUFFER_SIZE];
        self->read_bytes(self, dummy, byte_count);
        count -= byte_count;
    }
}


static void
br_parse(BitstreamReader* self, const char* format, ...)
{
    /*cache function pointers for reuse*/
    br_read_f read = self->read;
    br_read_signed_f read_signed = self->read_signed;
    br_read_64_f read_64 = self->read_64;
    br_read_signed_64_f read_signed_64 = self->read_signed_64;
    br_read_bigint_f read_bigint = self->read_bigint;
    br_read_signed_bigint_f read_signed_bigint = self->read_signed_bigint;
    br_skip_f skip = self->skip;
    br_skip_bytes_f skip_bytes = self->skip_bytes;
    br_read_bytes_f read_bytes = self->read_bytes;

    va_list ap;
    bs_instruction_t inst;

    va_start(ap, format);
    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        switch (inst) {
        case BS_INST_UNSIGNED:
            for (; times; times--) {
                unsigned *value = va_arg(ap, unsigned*);
                *value = read(self, size);
            }
            break;
        case BS_INST_SIGNED:
            for (; times; times--) {
                int *value = va_arg(ap, int*);
                *value = read_signed(self, size);
            }
            break;
        case BS_INST_UNSIGNED64:
            for (; times; times--) {
                uint64_t *value = va_arg(ap, uint64_t*);
                *value = read_64(self, size);
            }
            break;
        case BS_INST_SIGNED64:
            for (; times; times--) {
                int64_t *value = va_arg(ap, int64_t*);
                *value = read_signed_64(self, size);
            }
            break;
        case BS_INST_UNSIGNED_BIGINT:
            for (; times; times--) {
                mpz_t *value = va_arg(ap, mpz_t*);
                read_bigint(self, size, *value);
            }
            break;
        case BS_INST_SIGNED_BIGINT:
            for (; times; times--) {
                mpz_t *value = va_arg(ap, mpz_t*);
                read_signed_bigint(self, size, *value);
            }
            break;
        case BS_INST_SKIP:
            for (; times; times--) {
                skip(self, size);
            }
            break;
        case BS_INST_SKIP_BYTES:
            for (; times; times--) {
                skip_bytes(self, size);
            }
            break;
        case BS_INST_BYTES:
            for (; times; times--) {
                uint8_t *value = va_arg(ap, uint8_t*);
                read_bytes(self, value, size);
            }
            break;
        case BS_INST_ALIGN:
            self->byte_align(self);
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);
    va_end(ap);
}


static int
br_byte_aligned(const BitstreamReader* self)
{
    return (self->state == 0) || (self->state & 0x100);
}


static void
br_byte_align(BitstreamReader* self)
{
    if (!self->byte_aligned(self)) {
        self->state = 0;
    }
}



static br_pos_t*
br_getpos_file(BitstreamReader* self)
{
    br_pos_t* pos = malloc(sizeof(br_pos_t));
    pos->reader = self;
    fgetpos(self->input.file, &(pos->position.file));
    pos->state = self->state;
    pos->del = br_pos_del_f;
    return pos;
}

static br_pos_t*
br_getpos_b(BitstreamReader* self)
{
    br_pos_t* pos = malloc(sizeof(br_pos_t));
    pos->reader = self;
    pos->position.buffer = self->input.buffer->pos;
    pos->state = self->state;
    pos->del = br_pos_del_b;
    return pos;
}

static br_pos_t*
br_getpos_q(BitstreamReader* self)
{
    struct br_queue* queue = self->input.queue;
    br_pos_t* pos = malloc(sizeof(br_pos_t));

    /*increment reference count to keep track of active positions*/
    queue->pos_count++;

    pos->reader = self;
    pos->position.queue.pos = queue->pos;
    pos->position.queue.pos_count = &queue->pos_count;
    pos->state = self->state;
    pos->del = br_pos_del_q;
    return pos;
}

static br_pos_t*
br_getpos_e(BitstreamReader* self)
{
    struct br_external_input* input = self->input.external;
    const unsigned buffer_size = input->buffer.size - input->buffer.pos;
    void *ext_pos = input->getpos(input->user_data);
    br_pos_t* pos;

    if (ext_pos == NULL) {
        br_abort(self);
    }

    pos = malloc(sizeof(br_pos_t));
    pos->reader = self;
    pos->position.external.pos = ext_pos;
    pos->position.external.buffer_size = buffer_size;
    pos->position.external.buffer = malloc(buffer_size * sizeof(uint8_t));
    pos->position.external.free_pos = input->free_pos;
    memcpy(pos->position.external.buffer,
           input->buffer.data + input->buffer.pos,
           buffer_size * sizeof(uint8_t));
    pos->state = self->state;
    pos->del = br_pos_del_e;
    return pos;
}

static br_pos_t*
br_getpos_c(BitstreamReader* self)
{
    br_abort(self);
    return NULL;  /*shouldn't get here*/
}


static void
br_setpos_file(BitstreamReader* self, br_pos_t* pos)
{
    assert(pos->reader == self);
    fsetpos(self->input.file, &(pos->position.file));
    self->state = pos->state;
}

static void
br_setpos_b(BitstreamReader* self, br_pos_t* pos)
{
    assert(pos->reader == self);
    self->input.buffer->pos = pos->position.buffer;
    self->state = pos->state;
}

static void
br_setpos_q(BitstreamReader* self, br_pos_t* pos)
{
    assert(pos->reader == self);
    self->input.queue->pos = pos->position.queue.pos;
    self->state = pos->state;
}

static void
br_setpos_e(BitstreamReader* self, br_pos_t* pos)
{
    struct br_external_input* input = self->input.external;
    assert(pos->reader == self);

    if (input->setpos(input->user_data, pos->position.external.pos)) {
        br_abort(self);
    }
    memcpy(input->buffer.data,
           pos->position.external.buffer,
           pos->position.external.buffer_size);
    input->buffer.pos = 0;
    input->buffer.size = pos->position.external.buffer_size;
    self->state = pos->state;
}

static void
br_setpos_c(BitstreamReader* self, br_pos_t* pos)
{
    br_abort(self);
}


static void
br_pos_del_f(br_pos_t* pos)
{
    free(pos);
}

static void
br_pos_del_b(br_pos_t* pos)
{
    free(pos);
}

static void
br_pos_del_q(br_pos_t* pos)
{
    /*decrement reference count of open positions*/
    *pos->position.queue.pos_count -= 1;
    free(pos);
}

static void
br_pos_del_e(br_pos_t* pos)
{
    pos->position.external.free_pos(pos->position.external.pos);
    free(pos->position.external.buffer);
    free(pos);
}

#define SEEK_FUNC(FUNC_NAME, SEEK_FUNC, SEEK_ARG)                   \
  static void                                                       \
  FUNC_NAME(BitstreamReader* self, long position, bs_whence whence) \
  {                                                                 \
      self->state = 0;                                              \
      if (SEEK_FUNC(SEEK_ARG, position, whence)) {                  \
          br_abort(self);                                           \
      }                                                             \
  }
SEEK_FUNC(br_seek_file, fseek, self->input.file)
SEEK_FUNC(br_seek_b, br_buf_fseek, self->input.buffer)
SEEK_FUNC(br_seek_q, br_queue_fseek, self->input.queue)
SEEK_FUNC(br_seek_e, ext_fseek_r, self->input.external)

static unsigned
br_size_f_e_c(const BitstreamReader* self)
{
    return 0;
}

static unsigned
br_size_b(const BitstreamReader* self)
{
    return br_buf_size(self->input.buffer);
}

static unsigned
br_size_q(const BitstreamQueue* self)
{
    return br_queue_size(self->input.queue);
}


static BitstreamReader*
br_substream(BitstreamReader* self, unsigned bytes)
{
    BitstreamReader *substream = br_open_buffer(NULL, 0, self->endianness);
    struct br_buffer *buffer = substream->input.buffer;
    const unsigned BUF_SIZE = 1 << 20;

    if (!setjmp(*br_try(self))) {
        /*read input stream in chunks to avoid allocating
          a whole lot of data upfront
          in case "bytes" is much larger than the input stream*/
        while (bytes) {
            const unsigned to_read = MIN(BUF_SIZE, bytes);
            buffer->data = realloc(buffer->data, buffer->size + to_read);
            self->read_bytes(self, buffer->data + buffer->size, to_read);
            buffer->size += to_read;
            bytes -= to_read;
        }
        br_etry(self);
        return substream;
    } else {
        /*be sure to close partial substream before re-raising abort*/
        substream->close(substream);
        br_etry(self);
        br_abort(self);
        return NULL;  /*won't get here*/
    }
}


static void
br_enqueue(BitstreamReader* self, unsigned bytes, BitstreamQueue* queue)
{
    /*read input stream in chunks to avoid allocating
      a lot of data upfront
      in case "bytes" is much larger than the input stream*/
    const unsigned BUF_SIZE = 1 << 20;
    struct br_queue* output = queue->input.queue;
    while (bytes) {
        const unsigned to_read = MIN(BUF_SIZE, bytes);
        br_queue_resize_for(output, to_read);
        self->read_bytes(self, br_queue_end(output), to_read);
        output->size += to_read;
        bytes -= to_read;
    }
}


static void
br_close_methods(BitstreamReader* self)
{
    /*swap read methods with closed methods that generate read errors*/
    self->read = br_read_bits_c;
    self->read_64 = br_read_bits64_c;
    self->read_bigint = br_read_bits_bigint_c;
    self->skip = br_skip_bits_c;
    self->unread = br_unread_bit_c;
    self->read_unary = br_read_unary_c;
    self->skip_unary = br_skip_unary_c;
    self->read_huffman_code = br_read_huffman_code_c;
    self->read_bytes = br_read_bytes_c;
    self->set_endianness = br_set_endianness_c;

    self->getpos = br_getpos_c;
    self->setpos = br_setpos_c;

    self->size = br_size_f_e_c;

    self->close_internal_stream = br_close_internal_stream_c;
}


static void
br_close_internal_stream_f(BitstreamReader* self)
{
    /*perform fclose on FILE object*/
    fclose(self->input.file);

    /*swap read methods with closed methods*/
    br_close_methods(self);
}

static void
br_close_internal_stream_b(BitstreamReader* self)
{
    /*swap read methods with closed methods*/
    br_close_methods(self);
}

static void
br_close_internal_stream_q(BitstreamQueue* self)
{
    /*swap read methods with closed methods*/
    br_close_methods((BitstreamReader*)self);
}

static void
br_close_internal_stream_e(BitstreamReader* self)
{
    /*perform close operation on file-like object*/
    ext_close_r(self->input.external);

    /*swap read methods with closed methods*/
    br_close_methods(self);
}


static void
br_close_internal_stream_c(BitstreamReader* self)
{
    return;
}


static void
br_free_f(BitstreamReader* self)
{
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    /*deallocate callbacks*/
    while (self->callbacks != NULL) {
        self->pop_callback(self, NULL);
    }

    /*deallocate exceptions*/
    if (self->exceptions != NULL) {
        fprintf(stderr, "*** Warning: leftover etry entries on stack\n");
    }
    for (e_node = self->exceptions; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate used exceptions*/
    for (e_node = self->exceptions_used; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate the struct itself*/
    free(self);
}

static void
br_free_b(BitstreamReader* self)
{
    /*deallocate buffer*/
    br_buf_free(self->input.buffer);

    /*perform additional deallocations on rest of struct*/
    br_free_f(self);
}

static void
br_free_q(BitstreamQueue* self)
{
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    /*deallocate queue*/
    br_queue_free(self->input.queue);

    /*deallocate callbacks*/
    while (self->callbacks != NULL) {
        self->pop_callback((BitstreamReader*)self, NULL);
    }

    /*deallocate exceptions*/
    if (self->exceptions != NULL) {
        fprintf(stderr, "*** Warning: leftover etry entries on stack\n");
    }
    for (e_node = self->exceptions; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate used exceptions*/
    for (e_node = self->exceptions_used; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate the struct itself*/
    free(self);
}

static void
br_free_e(BitstreamReader* self)
{
    /*free internal file-like object, if necessary*/
    ext_free_r(self->input.external);

    /*perform additional deallocations on rest of struct*/
    br_free_f(self);
}


static void
br_close(BitstreamReader* self)
{
    self->close_internal_stream(self);
    self->free(self);
}

static void
br_close_q(BitstreamQueue* self)
{
    self->close_internal_stream(self);
    self->free(self);
}

static void
br_push_q(BitstreamQueue* self, unsigned byte_count, const uint8_t* data)
{
    struct br_queue *queue = self->input.queue;
    br_queue_resize_for(queue, byte_count);
    memcpy(br_queue_end(queue), data, byte_count);
    queue->size += byte_count;
}


static void
br_reset_q(BitstreamQueue* self)
{
    self->state = 0;

    /*if there are no outstanding getpos positions
      br_queue_resize_for will garbage-collect leftover space
      automatically, otherwise new data will be appended
      so that rewinding remains possible*/
    self->input.queue->pos = self->input.queue->size;
}


#ifdef DEBUG
void
__br_abort__(BitstreamReader* bs, int lineno)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "*** Error %d: EOF encountered, aborting\n", lineno);
        abort();
    }
}
#else
void
br_abort(BitstreamReader* bs)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "*** Error: EOF encountered, aborting\n");
        abort();
    }
}
#endif

jmp_buf*
br_try(BitstreamReader* bs)
{
    struct bs_exception *node;

    if (bs->exceptions_used == NULL)
        node = malloc(sizeof(struct bs_exception));
    else {
        node = bs->exceptions_used;
        bs->exceptions_used = bs->exceptions_used->next;
    }
    node->next = bs->exceptions;
    bs->exceptions = node;
    return &(node->env);
}

void
__br_etry(BitstreamReader* bs, const char *file, int lineno)
{
    struct bs_exception *node = bs->exceptions;
    if (node != NULL) {
        bs->exceptions = node->next;
        node->next = bs->exceptions_used;
        bs->exceptions_used = node;
    } else {
        fprintf(stderr,
                "*** Warning: %s %d: trying to pop from empty etry stack\n",
                file, lineno);
    }
}


BitstreamWriter*
bw_open(FILE *f, bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->endianness = endianness;
    bs->type = BW_FILE;

    bs->output.file = f;

    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_f_be;
        bs->write_signed = bw_write_signed_bits_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->write_signed_64 = bw_write_signed_bits64_be;
        bs->write_bigint = bw_write_bits_bigint_f_be;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_f_le;
        bs->write_signed = bw_write_signed_bits_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->write_signed_64 = bw_write_signed_bits64_le;
        bs->write_bigint = bw_write_bits_bigint_f_le;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_le;
        break;
    }

    bs->set_endianness = bw_set_endianness_f;
    bs->write_unary = bw_write_unary;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_file;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned;
    bs->byte_align = bw_byte_align;
    bs->flush = bw_flush_f;
    bs->add_callback = bw_add_callback;
    bs->push_callback = bw_push_callback;
    bs->pop_callback = bw_pop_callback;
    bs->call_callbacks = bw_call_callbacks;
    bs->getpos = bw_getpos_file;
    bs->setpos = bw_setpos_file;

    bs->close_internal_stream = bw_close_internal_stream_f;
    bs->free = bw_free_f;
    bs->close = bw_close_f_e;

    return bs;
}

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
                 ext_free_f free)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->endianness = endianness;
    bs->type = BW_EXTERNAL;

    bs->output.external = ext_open_w(user_data,
                                     buffer_size,
                                     write,
                                     setpos,
                                     getpos,
                                     free_pos,
                                     flush,
                                     close,
                                     free);
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_e_be;
        bs->write_signed = bw_write_signed_bits_be;
        bs->write_64 = bw_write_bits64_e_be;
        bs->write_signed_64 = bw_write_signed_bits64_be;
        bs->write_bigint = bw_write_bits_bigint_e_be;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_e_le;
        bs->write_signed = bw_write_signed_bits_le;
        bs->write_64 = bw_write_bits64_e_le;
        bs->write_signed_64 = bw_write_signed_bits64_le;
        bs->write_bigint = bw_write_bits_bigint_e_le;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_le;
        break;
    }

    bs->set_endianness = bw_set_endianness_e;
    bs->write_unary = bw_write_unary;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_e;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned;
    bs->byte_align = bw_byte_align;
    bs->flush = bw_flush_e;
    bs->add_callback = bw_add_callback;
    bs->push_callback = bw_push_callback;
    bs->pop_callback = bw_pop_callback;
    bs->call_callbacks = bw_call_callbacks;
    bs->setpos = bw_setpos_e;
    bs->getpos = bw_getpos_e;

    bs->close_internal_stream = bw_close_internal_stream_e;
    bs->free = bw_free_e;
    bs->close = bw_close_f_e;

    return bs;
}

BitstreamRecorder*
bw_open_recorder(bs_endianness endianness)
{
    return bw_open_limited_recorder(endianness, 0);
}


BitstreamRecorder*
bw_open_limited_recorder(bs_endianness endianness, unsigned maximum_size)
{
    BitstreamRecorder *bs = malloc(sizeof(BitstreamRecorder));
    bs->endianness = endianness;
    bs->type = BW_RECORDER;

    bs->output.recorder = bw_buf_new(maximum_size);
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_r_be;
        bs->write_signed = bw_write_signed_bits_be;
        bs->write_64 = bw_write_bits64_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_be;
        bs->write_bigint = bw_write_bits_bigint_r_be;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_r_le;
        bs->write_signed = bw_write_signed_bits_le;
        bs->write_64 = bw_write_bits64_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_le;
        bs->write_bigint = bw_write_bits_bigint_r_le;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_le;
        break;
    }

    bs->set_endianness = bw_set_endianness_r;
    bs->write_unary = bw_write_unary;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_r;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned;
    bs->byte_align = bw_byte_align;
    bs->flush = bw_flush_r_a_c;
    bs->add_callback = bw_add_callback;
    bs->push_callback = bw_push_callback;
    bs->pop_callback = bw_pop_callback;
    bs->call_callbacks = bw_call_callbacks;
    bs->getpos = bw_getpos_r;
    bs->setpos = bw_setpos_r;

    bs->bits_written = bw_bits_written_r;
    bs->bytes_written = bw_bytes_written_r;
    bs->reset = bw_reset_r;
    bs->copy = bw_copy_r;
    bs->data = bw_data_r;
    bs->close_internal_stream = bw_close_internal_stream_r;
    bs->free = bw_free_r;
    bs->close = bw_close_r;

    return bs;
}

BitstreamAccumulator*
bw_open_accumulator(bs_endianness endianness)
{
    BitstreamAccumulator *bs = malloc(sizeof(BitstreamAccumulator));
    bs->endianness = endianness;
    bs->type = BW_ACCUMULATOR;

    bs->output.accumulator = 0;
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_a;
        bs->write_signed = bw_write_signed_bits_be;
        bs->write_64 = bw_write_bits64_a;
        bs->write_signed_64 = bw_write_signed_bits64_be;
        bs->write_bigint = bw_write_bits_bigint_a;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_a;
        bs->write_signed = bw_write_signed_bits_le;
        bs->write_64 = bw_write_bits64_a;
        bs->write_signed_64 = bw_write_signed_bits64_le;
        bs->write_bigint = bw_write_bits_bigint_a;
        bs->write_signed_bigint = bw_write_signed_bits_bigint_le;
        break;
    }

    bs->set_endianness = bw_set_endianness_a;
    bs->write_unary = bw_write_unary_a;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_a;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned;
    bs->byte_align = bw_byte_align;
    bs->flush = bw_flush_r_a_c;
    bs->add_callback = bw_add_callback;
    bs->push_callback = bw_push_callback;
    bs->pop_callback = bw_pop_callback;
    bs->call_callbacks = bw_call_callbacks;
    bs->getpos = bw_getpos_r;
    bs->setpos = bw_setpos_r;

    bs->bits_written = bw_bits_written_a;
    bs->bytes_written = bw_bytes_written_a;
    bs->reset = bw_reset_a;
    bs->close_internal_stream = bw_close_internal_stream_a;
    bs->free = bw_free_a;
    bs->close = bw_close_a;

    return bs;
}


#define FUNC_WRITE_BITS_BE(FUNC_NAME, VALUE_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    static void                                                         \
    FUNC_NAME(BitstreamWriter* self, unsigned int count, VALUE_TYPE value) \
    {                                                                   \
        register unsigned buffer = self->buffer;                        \
        register unsigned buffer_size = self->buffer_size;              \
                                                                        \
        while (count > 0) {                                             \
            /*chop off up to 8 bits to write at a time*/                \
            const int bits_to_write = count > 8 ? 8 : count;            \
            const VALUE_TYPE value_to_write =                           \
                value >> (count - bits_to_write);                       \
                                                                        \
            /*new data is added to the buffer least-significant first*/ \
            buffer = (unsigned int)((buffer << bits_to_write) |         \
                                    value_to_write);                    \
            buffer_size += bits_to_write;                               \
                                                                        \
            /*if buffer is over 8 bits,*/                               \
            /*extract bits most-significant first*/                     \
            /*and remove them from the buffer*/                         \
            if (buffer_size >= 8) {                                     \
                const unsigned byte =                                   \
                    (buffer >> (buffer_size - 8)) & 0xFF;               \
                if (BYTE_FUNC(byte, BYTE_FUNC_ARG) != EOF) {            \
                    struct bs_callback* callback;                       \
                                                                        \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                                                                        \
                    buffer_size -= 8;                                   \
                } else {                                                \
                    self->buffer = buffer;                              \
                    self->buffer_size = buffer_size;                    \
                    bw_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            /*decrement the count and value*/                           \
            value -= (value_to_write << (count - bits_to_write));       \
            count -= bits_to_write;                                     \
        }                                                               \
        self->buffer = buffer;                                          \
        self->buffer_size = buffer_size;                                \
    }

#define FUNC_WRITE_BITS_LE(FUNC_NAME, VALUE_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    static void                                                         \
    FUNC_NAME(BitstreamWriter* self, unsigned int count, VALUE_TYPE value) \
    {                                                                   \
        register unsigned buffer = self->buffer;                        \
        register unsigned buffer_size = self->buffer_size;              \
                                                                        \
        while (count > 0) {                                             \
            /*chop off up to 8 bits to write at a time*/                \
            const int bits_to_write = count > 8 ? 8 : count;            \
            const VALUE_TYPE value_to_write =                           \
                value & ((1 << bits_to_write) - 1);                     \
                                                                        \
            /*new data is added to the buffer most-significant first*/  \
            buffer |= (unsigned int)(value_to_write << buffer_size);    \
            buffer_size += bits_to_write;                               \
                                                                        \
            /*if buffer is over 8 bits,*/                               \
            /*extract bits least-significant first*/                    \
            /*and remove them from the buffer*/                         \
            if (buffer_size >= 8) {                                     \
                const unsigned byte = buffer & 0xFF;                    \
                if (BYTE_FUNC(byte, BYTE_FUNC_ARG) != EOF) {            \
                    struct bs_callback* callback;                       \
                                                                        \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                    buffer >>= 8;                                       \
                    buffer_size -= 8;                                   \
                } else {                                                \
                    self->buffer = buffer;                              \
                    self->buffer_size = buffer_size;                    \
                    bw_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            /*decrement the count and value*/                           \
            value >>= bits_to_write;                                    \
            count -= bits_to_write;                                     \
        }                                                               \
        self->buffer = buffer;                                          \
        self->buffer_size = buffer_size;                                \
    }

FUNC_WRITE_BITS_BE(bw_write_bits_f_be,
                   unsigned int, fputc, self->output.file)
FUNC_WRITE_BITS_LE(bw_write_bits_f_le,
                   unsigned int, fputc, self->output.file)
FUNC_WRITE_BITS_BE(bw_write_bits_e_be,
                   unsigned int, ext_putc, self->output.external)
FUNC_WRITE_BITS_LE(bw_write_bits_e_le,
                   unsigned int, ext_putc, self->output.external)
FUNC_WRITE_BITS_BE(bw_write_bits_r_be,
                   unsigned int, bw_buf_putc, self->output.recorder)
FUNC_WRITE_BITS_LE(bw_write_bits_r_le,
                   unsigned int, bw_buf_putc, self->output.recorder)


static void
bw_write_bits_c(BitstreamWriter* self,
                unsigned int count,
                unsigned int value)
{
    bw_abort(self);
}

static void
bw_write_signed_bits_be(BitstreamWriter* self,
                        unsigned int count,
                        int value)
{
    if (value >= 0) {
        self->write(self, 1, 0);
        self->write(self, count - 1, value);
    } else {
        self->write(self, 1, 1);
        self->write(self, count - 1, (1 << (count - 1)) + value);
    }
}

static void
bw_write_signed_bits_le(BitstreamWriter* self,
                        unsigned int count,
                        int value)
{
    if (value >= 0) {
        self->write(self, count - 1, value);
        self->write(self, 1, 0);
    } else {
        self->write(self, count - 1, (1 << (count - 1)) + value);
        self->write(self, 1, 1);
    }
}

FUNC_WRITE_BITS_BE(bw_write_bits64_f_be,
                   uint64_t, fputc, self->output.file)
FUNC_WRITE_BITS_LE(bw_write_bits64_f_le,
                   uint64_t, fputc, self->output.file)
FUNC_WRITE_BITS_BE(bw_write_bits64_e_be,
                   uint64_t, ext_putc, self->output.external)
FUNC_WRITE_BITS_LE(bw_write_bits64_e_le,
                   uint64_t, ext_putc, self->output.external)
FUNC_WRITE_BITS_BE(bw_write_bits64_r_be,
                   uint64_t, bw_buf_putc, self->output.recorder)
FUNC_WRITE_BITS_LE(bw_write_bits64_r_le,
                   uint64_t, bw_buf_putc, self->output.recorder)

static void
bw_write_bits64_c(BitstreamWriter* self,
                  unsigned int count,
                  uint64_t value)
{
    bw_abort(self);
}


static void
bw_write_signed_bits64_be(BitstreamWriter* self,
                          unsigned int count,
                          int64_t value)
{
    if (value >= 0ll) {
        self->write(self, 1, 0);
        self->write_64(self, count - 1, value);
    } else {
        self->write(self, 1, 1);
        self->write_64(self, count - 1, (1ll << (count - 1)) + value);
    }
}

static void
bw_write_signed_bits64_le(BitstreamWriter* self,
                          unsigned int count,
                          int64_t value)
{
    if (value >= 0ll) {
        self->write_64(self, count - 1, value);
        self->write(self, 1, 0);
    } else {
        self->write_64(self, count - 1, (1ll << (count - 1)) + value);
        self->write(self, 1, 1);
    }
}


#define FUNC_WRITE_BITS_BIGINT_BE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG)  \
    static void                                                         \
    FUNC_NAME(BitstreamWriter* self, unsigned int count, const mpz_t value) \
    {                                                                   \
        register unsigned buffer = self->buffer;                        \
        register unsigned buffer_size = self->buffer_size;              \
        mpz_t temp_value;                                               \
        mpz_t value_to_write;                                           \
        mpz_init_set(temp_value, value);                                \
        mpz_init(value_to_write);                                       \
                                                                        \
        assert(mpz_sgn(value) >= 0);                                    \
        assert(mpz_sizeinbase(value, 2) <= count);                      \
                                                                        \
        while (count > 0) {                                             \
            /*chop off up to 8 bits to write at a time*/                \
            const int bits_to_write = count > 8 ? 8 : count;            \
            /*value_to_write = temp_value >> (count - bits_to_write)*/  \
            mpz_fdiv_q_2exp(value_to_write, temp_value,                 \
                            count - bits_to_write);                     \
                                                                        \
            /*new data is added to the buffer least-significant first*/ \
            buffer = (unsigned int)((buffer << bits_to_write) |         \
                                    mpz_get_ui(value_to_write));        \
            buffer_size += bits_to_write;                               \
                                                                        \
            /*if buffer is over 8 bits,*/                               \
            /*extract bits most-significant first*/                     \
            /*and remove them from the buffer*/                         \
            if (buffer_size >= 8) {                                     \
                const unsigned byte =                                   \
                    (buffer >> (buffer_size - 8)) & 0xFF;               \
                if (BYTE_FUNC(byte, BYTE_FUNC_ARG) != EOF) {            \
                    struct bs_callback* callback;                       \
                                                                        \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                                                                        \
                    buffer_size -= 8;                                   \
                } else {                                                \
                    self->buffer = buffer;                              \
                    self->buffer_size = buffer_size;                    \
                    mpz_clear(temp_value);                              \
                    mpz_clear(value_to_write);                          \
                    bw_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            /*decrement the count and value*/                           \
                                                                        \
            /*value_to_write <<= (count - bits_to_write)*/              \
            mpz_mul_2exp(value_to_write, value_to_write,                \
                         count - bits_to_write);                        \
            /*temp_value -= value_to_write*/                            \
            mpz_sub(temp_value, temp_value, value_to_write);            \
                                                                        \
            count -= bits_to_write;                                     \
        }                                                               \
        self->buffer = buffer;                                          \
        self->buffer_size = buffer_size;                                \
        mpz_clear(temp_value);                                          \
        mpz_clear(value_to_write);                                      \
    }
FUNC_WRITE_BITS_BIGINT_BE(bw_write_bits_bigint_f_be, fputc,
                          self->output.file)
FUNC_WRITE_BITS_BIGINT_BE(bw_write_bits_bigint_e_be, ext_putc,
                          self->output.external)
FUNC_WRITE_BITS_BIGINT_BE(bw_write_bits_bigint_r_be, bw_buf_putc,
                          self->output.recorder)

#define FUNC_WRITE_BITS_BIGINT_LE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG)  \
    static void                                                         \
    FUNC_NAME(BitstreamWriter* self, unsigned int count, const mpz_t value) \
    {                                                                   \
        register unsigned buffer = self->buffer;                        \
        register unsigned buffer_size = self->buffer_size;              \
        mpz_t temp_value;                                               \
        mpz_t value_to_write;                                           \
        mpz_t bitmask;                                                  \
        mpz_init_set(temp_value, value);                                \
        mpz_init(value_to_write);                                       \
        mpz_init(bitmask);                                              \
                                                                        \
        assert(mpz_sgn(value) >= 0);                                    \
        assert(mpz_sizeinbase(value, 2) <= count);                      \
                                                                        \
        while (count > 0) {                                             \
            /*chop off up to 8 bits to write at a time*/                \
                                                                        \
            const int bits_to_write = count > 8 ? 8 : count;            \
            /*bitmask = 1*/                                             \
            mpz_set_ui(bitmask, 1);                                     \
            /*bitmask <<= bits_to_write*/                               \
            mpz_mul_2exp(bitmask, bitmask, bits_to_write);              \
            /*bitmask -= 1*/                                            \
            mpz_sub_ui(bitmask, bitmask, 1);                            \
            /*value_to_write = temp_value & bitmask*/                   \
            mpz_and(value_to_write, temp_value, bitmask);               \
                                                                        \
            /*new data is added to the buffer most-significant first*/  \
            buffer |= (unsigned int)(mpz_get_ui(value_to_write) <<      \
                                     buffer_size);                      \
            buffer_size += bits_to_write;                               \
                                                                        \
            /*if buffer is over 8 bits,*/                               \
            /*extract bits least-significant first*/                    \
            /*and remove them from the buffer*/                         \
            if (buffer_size >= 8) {                                     \
                const unsigned byte = buffer & 0xFF;                    \
                if (BYTE_FUNC(byte, BYTE_FUNC_ARG) != EOF) {            \
                    struct bs_callback* callback;                       \
                                                                        \
                    for (callback = self->callbacks;                    \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                    buffer >>= 8;                                       \
                    buffer_size -= 8;                                   \
                } else {                                                \
                    self->buffer = buffer;                              \
                    self->buffer_size = buffer_size;                    \
                    mpz_clear(temp_value);                              \
                    mpz_clear(value_to_write);                          \
                    mpz_clear(bitmask);                                 \
                    bw_abort(self);                                     \
                }                                                       \
            }                                                           \
                                                                        \
            /*decrement the count and value*/                           \
                                                                        \
            /*temp_value >>= bits_to_write*/                            \
            mpz_fdiv_q_2exp(temp_value, temp_value, bits_to_write);     \
                                                                        \
            count -= bits_to_write;                                     \
        }                                                               \
        self->buffer = buffer;                                          \
        self->buffer_size = buffer_size;                                \
        mpz_clear(temp_value);                                          \
        mpz_clear(value_to_write);                                      \
        mpz_clear(bitmask);                                             \
    }
FUNC_WRITE_BITS_BIGINT_LE(bw_write_bits_bigint_f_le, fputc,
                          self->output.file)
FUNC_WRITE_BITS_BIGINT_LE(bw_write_bits_bigint_e_le, ext_putc,
                          self->output.external)
FUNC_WRITE_BITS_BIGINT_LE(bw_write_bits_bigint_r_le, bw_buf_putc,
                          self->output.recorder)

static void
bw_write_bits_bigint_c(BitstreamWriter* self,
                       unsigned int count,
                       const mpz_t value)
{
    bw_abort(self);
}

static void
bw_write_signed_bits_bigint_be(BitstreamWriter* self,
                               unsigned int count,
                               const mpz_t value)
{
    if (mpz_sgn(value) >= 0) {
        /*positive value*/
        self->write(self, 1, 0);
        self->write_bigint(self, count - 1, value);
    } else {
        /*negative value*/
        mpz_t modifier;
        mpz_t unsigned_value;
        mpz_init(unsigned_value);

        /*modifier = 1*/
        mpz_init_set_ui(modifier, 1);

        /*modifier <<= (count - 1)*/
        mpz_mul_2exp(modifier, modifier, count - 1);

        /*unsigned_value = modifier + value*/
        mpz_add(unsigned_value, modifier, value);

        mpz_clear(modifier);

        if (!setjmp(*bw_try(self))) {
            self->write(self, 1, 1);
            self->write_bigint(self, count - 1, unsigned_value);
            bw_etry(self);
            mpz_clear(unsigned_value);
        } else {
            /*ensure unsigned_value is freed before re-raising error*/
            bw_etry(self);
            mpz_clear(unsigned_value);
            bw_abort(self);
        }
    }
}

static void
bw_write_signed_bits_bigint_le(BitstreamWriter* self,
                               unsigned int count,
                               const mpz_t value)
{
    if (mpz_sgn(value) >= 0) {
        /*positive value*/
        self->write_bigint(self, count - 1, value);
        self->write(self, 1, 0);
    } else {
        /*negative value*/
        mpz_t modifier;
        mpz_t unsigned_value;
        mpz_init(unsigned_value);

        /*modifier = 1*/
        mpz_init_set_ui(modifier, 1);

        /*modifier <<= (count - 1)*/
        mpz_mul_2exp(modifier, modifier, count - 1);

        /*unsigned_value = modifier + value*/
        mpz_add(unsigned_value, modifier, value);

        mpz_clear(modifier);

        if (!setjmp(*bw_try(self))) {
            self->write_bigint(self, count - 1, unsigned_value);
            self->write(self, 1, 1);
            bw_etry(self);
            mpz_clear(unsigned_value);
        } else {
            /*ensure unsigned_value is freed before re-raising error*/
            bw_etry(self);
            mpz_clear(unsigned_value);
            bw_abort(self);
        }
    }
}

static void
bw_write_bits_a(BitstreamWriter *self, unsigned int count, unsigned int value)
{
    self->output.accumulator += count;
}

static void
bw_write_bits64_a(BitstreamWriter *self, unsigned int count, uint64_t value)
{
    self->output.accumulator += count;
}

static void
bw_write_bits_bigint_a(BitstreamWriter *self,
                       unsigned int count,
                       const mpz_t value)
{
    self->output.accumulator += count;
}

static void
bw_write_bytes_a(BitstreamWriter *self,
                 const uint8_t* bytes,
                 unsigned int byte_count)
{
    self->output.accumulator += (byte_count * 8);
}

#define UNARY_BUFFER_SIZE 30

static void
bw_write_unary(BitstreamWriter* self, int stop_bit, unsigned int value)
{
    /*send our pre-stop bits to write() in 30-bit chunks*/
    while (value > 0) {
        const unsigned int bits_to_write = MIN(value, UNARY_BUFFER_SIZE);
        if (stop_bit) { /*stop bit of 1, buffer value of all 0s*/
            self->write(self, bits_to_write, 0);
        } else {        /*stop bit of 0, buffer value of all 1s*/
            self->write(self, bits_to_write, (1 << bits_to_write) - 1);
        }
        value -= bits_to_write;
    }

    /*finally, send our stop bit*/
    self->write(self, 1, stop_bit);
}

static void
bw_write_unary_a(BitstreamWriter *self, int stop_bit, unsigned int value)
{
    self->output.accumulator += (value + 1);
}


static void
__bw_set_endianness__(BitstreamWriter* self, bs_endianness endianness)
{
    self->endianness = endianness;
    self->buffer = 0;
    self->buffer_size = 0;
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->write_signed = bw_write_signed_bits_le;
        self->write_signed_64 = bw_write_signed_bits64_le;
        self->write_signed_bigint = bw_write_signed_bits_bigint_le;
        break;
    case BS_BIG_ENDIAN:
        self->write_signed = bw_write_signed_bits_be;
        self->write_signed_64 = bw_write_signed_bits64_be;
        self->write_signed_bigint = bw_write_signed_bits_bigint_be;
        break;
    }
}

static void
bw_set_endianness_f(BitstreamWriter* self, bs_endianness endianness)
{
    __bw_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->write = bw_write_bits_f_le;
        self->write_64 = bw_write_bits64_f_le;
        self->write_bigint = bw_write_bits_bigint_f_le;
        break;
    case BS_BIG_ENDIAN:
        self->write = bw_write_bits_f_be;
        self->write_64 = bw_write_bits64_f_be;
        self->write_bigint = bw_write_bits_bigint_f_be;
        break;
    }
}

static void
bw_set_endianness_e(BitstreamWriter* self, bs_endianness endianness)
{
    __bw_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->write = bw_write_bits_e_le;
        self->write_64 = bw_write_bits64_e_le;
        self->write_bigint = bw_write_bits_bigint_e_le;
        break;
    case BS_BIG_ENDIAN:
        self->write = bw_write_bits_e_be;
        self->write_64 = bw_write_bits64_e_be;
        self->write_bigint = bw_write_bits_bigint_e_be;
        break;
    }
}

static void
bw_set_endianness_r(BitstreamWriter* self, bs_endianness endianness)
{
    __bw_set_endianness__(self, endianness);
    switch (endianness) {
    case BS_LITTLE_ENDIAN:
        self->write = bw_write_bits_r_le;
        self->write_64 = bw_write_bits64_r_le;
        self->write_bigint = bw_write_bits_bigint_r_le;
        break;
    case BS_BIG_ENDIAN:
        self->write = bw_write_bits_r_be;
        self->write_64 = bw_write_bits64_r_be;
        self->write_bigint = bw_write_bits_bigint_r_be;
        break;
    }
}

static void
bw_set_endianness_a(BitstreamWriter* self, bs_endianness endianness)
{
    __bw_set_endianness__(self, endianness);
}

static void
bw_set_endianness_c(BitstreamWriter* self, bs_endianness endianness)
{
    __bw_set_endianness__(self, endianness);
}


static int
bw_write_huffman(BitstreamWriter* self,
                 bw_huffman_table_t* table,
                 int value)
{
    int current_index = 0;

    while (current_index != -1) {
        if (table[current_index].value == value) {
            self->write(self,
                        table[current_index].write_count,
                        table[current_index].write_value);
            return 0;
        } else if (value < table[current_index].value) {
            current_index = table[current_index].smaller;
        } else {
            current_index = table[current_index].larger;
        }
    }

    /*walked outside of the Huffman table, so return error*/
    return 1;
}


static void
bw_write_bytes_file(BitstreamWriter* self,
                    const uint8_t* bytes,
                    unsigned int count)
{
    if (self->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so perform optimized write*/
        if (fwrite(bytes, sizeof(uint8_t), count, self->output.file) != count) {
            bw_abort(self);
        }

        /*perform callbacks on the written bytes*/
        for (callback = self->callbacks;
             callback != NULL;
             callback = callback->next) {
            bs_callback_f callback_func = callback->callback;
            void* callback_data = callback->data;
            unsigned int i;
            for (i = 0; i < count; i++) {
                callback_func(bytes[i], callback_data);
            }
        }
    } else {
        /*stream is not byte-aligned, so perform multiple writes*/
        unsigned int i;

        for (i = 0; i < count; i++)
            self->write(self, 8, bytes[i]);
    }
}

static void
bw_write_bytes_e(BitstreamWriter* self,
                 const uint8_t* bytes,
                 unsigned int count)
{

    if (self->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so performed optimized write*/
        if (ext_fwrite(self->output.external, bytes, count)) {
            bw_abort(self);
        }

        /*perform callbacks on the written bytes*/
        for (callback = self->callbacks;
             callback != NULL;
             callback = callback->next) {
            bs_callback_f callback_func = callback->callback;
            void* callback_data = callback->data;
            unsigned int i;
            for (i = 0; i < count; i++) {
                callback_func(bytes[i], callback_data);
            }
        }
    } else {
        /*stream is not byte-aligned, so perform multiple writes*/
        unsigned int i;

        for (i = 0; i < count; i++)
            self->write(self, 8, bytes[i]);
    }
}

static void
bw_write_bytes_r(BitstreamWriter* self,
                 const uint8_t* bytes,
                 unsigned int count)
{
    if (self->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so perform optimized write*/
        if (bw_buf_write(self->output.recorder, bytes, count)) {
            bw_abort(self);
        }

        /*perform callbacks on the written bytes*/
        for (callback = self->callbacks;
             callback != NULL;
             callback = callback->next) {
            bs_callback_f callback_func = callback->callback;
            void* callback_data = callback->data;
            unsigned int i;

            for (i = 0; i < count; i++) {
                callback_func(bytes[i], callback_data);
            }
        }
    } else {
        /*stream is not byte-aligned, so perform multiple writes*/
        unsigned int i;

        for (i = 0; i < count; i++)
            self->write(self, 8, bytes[i]);
    }
}

static void
bw_write_bytes_c(BitstreamWriter* self,
                 const uint8_t* bytes,
                 unsigned int count)
{
    bw_abort(self);
}


static void
bw_build(BitstreamWriter* self, const char* format, ...)
{
    /*cache function pointers for reuse*/
    bw_write_f write = self->write;
    bw_write_signed_f write_signed = self->write_signed;
    bw_write_64_f write_64 = self->write_64;
    bw_write_signed_64_f write_signed_64 = self->write_signed_64;
    bw_write_bigint_f write_bigint = self->write_bigint;
    bw_write_signed_bigint_f write_signed_bigint = self->write_signed_bigint;
    bw_write_bytes_f write_bytes = self->write_bytes;

    va_list ap;
    bs_instruction_t inst;

    va_start(ap, format);
    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        switch (inst) {
        case BS_INST_UNSIGNED:
            for (; times; times--) {
                const unsigned value = va_arg(ap, unsigned);
                write(self, size, value);
            }
            break;
        case BS_INST_SIGNED:
            for (; times; times--) {
                const int value = va_arg(ap, int);
                write_signed(self, size, value);
            }
            break;
        case BS_INST_UNSIGNED64:
            for (; times; times--) {
                const uint64_t value = va_arg(ap, uint64_t);
                write_64(self, size, value);
            }
            break;
        case BS_INST_SIGNED64:
            for (; times; times--) {
                const int64_t value = va_arg(ap, int64_t);
                write_signed_64(self, size, value);
            }
            break;
        case BS_INST_UNSIGNED_BIGINT:
            for (; times; times--) {
                mpz_t *value = va_arg(ap, mpz_t*);
                write_bigint(self, size, *value);
            }
            break;
        case BS_INST_SIGNED_BIGINT:
            for (; times; times--) {
                mpz_t *value = va_arg(ap, mpz_t*);
                write_signed_bigint(self, size, *value);
            }
            break;
        case BS_INST_SKIP:
            for (; times; times--) {
                write(self, size, 0);
            }
            break;
        case BS_INST_SKIP_BYTES:
            for (; times; times--) {
                /*somewhat inefficient,
                  but byte skipping is rare for BitstreamWriters anyway*/
                write(self, size, 0);
                write(self, size, 0);
                write(self, size, 0);
                write(self, size, 0);
                write(self, size, 0);
                write(self, size, 0);
                write(self, size, 0);
                write(self, size, 0);
            }
            break;
        case BS_INST_BYTES:
            for (; times; times--) {
                const uint8_t *value = va_arg(ap, uint8_t*);
                write_bytes(self, value, size);
            }
            break;
        case BS_INST_ALIGN:
            self->byte_align(self);
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);
    va_end(ap);
}

static int
bw_byte_aligned(const BitstreamWriter* self)
{
    return (self->buffer_size == 0);
}


static void
bw_byte_align(BitstreamWriter* bs)
{
    /*write enough 0 bits to completely fill the buffer
      which results in a byte being written*/
    if (bs->buffer_size > 0)
        bs->write(bs, 8 - bs->buffer_size, 0);
}


static void
bw_flush_f(BitstreamWriter* self)
{
    fflush(self->output.file);
}

static void
bw_flush_r_a_c(BitstreamWriter* self)
{
    /*recorders and accumulators are always flushed,
      closed streams do nothing when flushed*/
    return;
}

static void
bw_flush_e(BitstreamWriter* self)
{
    if (ext_flush_w(self->output.external)) {
        bw_abort(self);
    }
}

static bw_pos_t*
bw_getpos_file(BitstreamWriter* self)
{
    bw_pos_t* pos;

    assert(self->buffer_size == 0);

    pos = malloc(sizeof(bw_pos_t));
    pos->writer = self;
    fgetpos(self->output.file, &(pos->position.file));
    pos->del = bw_pos_del_f;
    return pos;
}

static bw_pos_t*
bw_getpos_e(BitstreamWriter* self)
{
    struct bw_external_output* output = self->output.external;
    bw_pos_t* pos;
    void* ext_pos;

    assert(self->buffer_size == 0);

    if ((ext_pos = ext_getpos_w(output)) == NULL) {
        /*some error getting position*/
        bw_abort(self);
    }

    pos = malloc(sizeof(bw_pos_t));
    pos->writer = self;
    pos->position.external.pos = ext_pos;
    pos->position.external.free_pos = output->free_pos;
    pos->del = bw_pos_del_e;
    return pos;
}

static bw_pos_t*
bw_getpos_r(BitstreamWriter* self)
{
    bw_pos_t* pos;

    assert(self->buffer_size == 0);

    pos = malloc(sizeof(bw_pos_t));
    pos->writer = self;
    bw_buf_getpos(self->output.recorder, &pos->position.recorder);
    pos->del = bw_pos_del_r;
    return pos;
}

static bw_pos_t*
bw_getpos_c(BitstreamWriter* self)
{
    bw_abort(self);
    return NULL;  /*shouldn't get here*/
}


static void
bw_setpos_file(BitstreamWriter* self, const bw_pos_t* pos)
{
    assert(pos->writer == self);
    assert(self->buffer_size == 0);

    fsetpos(self->output.file, &(pos->position.file));
}

static void
bw_setpos_e(BitstreamWriter* self, const bw_pos_t* pos)
{
    struct bw_external_output* output = self->output.external;

    assert(pos->writer == self);
    assert(self->buffer_size == 0);

    if (ext_setpos_w(output, pos->position.external.pos)) {
        bw_abort(self);
    }
}

static void
bw_setpos_r(BitstreamWriter* self, const bw_pos_t* pos)
{
    assert(pos->writer == self);
    assert(self->buffer_size == 0);

    if (bw_buf_setpos(self->output.recorder, pos->position.recorder)) {
        /*this may happen if someone resets the stream
          and then tries to setpos afterward*/
        bw_abort(self);
    }
}

static void
bw_setpos_c(BitstreamWriter* self, const bw_pos_t* pos)
{
    bw_abort(self);
}


static void
bw_pos_del_f(bw_pos_t* pos)
{
    free(pos);
}

static void
bw_pos_del_e(bw_pos_t* pos)
{
    pos->position.external.free_pos(pos->position.external.pos);
    free(pos);
}

static void
bw_pos_del_r(bw_pos_t* pos)
{
    free(pos);
}


static void
bw_close_methods(BitstreamWriter* self)
{
    /*swap read methods with closed methods that generate read errors*/
    self->write = bw_write_bits_c;
    self->write_64 = bw_write_bits64_c;
    self->write_bigint = bw_write_bits_bigint_c;
    self->write_bytes = bw_write_bytes_c;
    self->flush = bw_flush_r_a_c;
    self->set_endianness = bw_set_endianness_c;
    self->getpos = bw_getpos_c;
    self->setpos = bw_setpos_c;
}


static void
bw_close_internal_stream_f(BitstreamWriter* self)
{
    /*perform fclose on FILE object
      which automatically flushes its output*/
    fclose(self->output.file);

    /*swap write methods with closed methods*/
    bw_close_methods(self);
    self->close_internal_stream = bw_close_internal_stream_cf;
}

static void
bw_close_internal_stream_cf(BitstreamWriter* self)
{
    return;
}

static void
bw_close_internal_stream_r(BitstreamRecorder* self)
{
    bw_close_methods((BitstreamWriter*)self);
}

static void
bw_close_internal_stream_e(BitstreamWriter* self)
{
    /*call .close() method (which automatically performs flush)
      not much we can do if an error occurs at this point*/
    (void)ext_close_w(self->output.external);

    /*swap read methods with closed methods*/
    bw_close_methods(self);
    self->close_internal_stream = bw_close_internal_stream_cf;
}


static void
bw_free_f(BitstreamWriter* self)
{
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    /*deallocate callbacks*/
    while (self->callbacks != NULL) {
        self->pop_callback(self, NULL);
    }

    /*deallocate exceptions*/
    if (self->exceptions != NULL) {
        fprintf(stderr, "*** Warning: leftover etry entries on stack\n");
    }
    for (e_node = self->exceptions; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate used exceptions*/
    for (e_node = self->exceptions_used; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate the struct itself*/
    free(self);
}

static void
bw_free_e(BitstreamWriter* self)
{
    /*calls free function on user data*/
    ext_free_w(self->output.external);

    /*perform additional deallocations on rest of struct*/
    bw_free_f(self);
}


static void
bw_free_r(BitstreamRecorder* self)
{
    /*deallocate buffer*/
    bw_buf_free(self->output.recorder);

    /*perform additional deallocations on rest of struct*/
    bw_free_f((BitstreamWriter*)self);
}

static void
bw_close_f_e(BitstreamWriter* self)
{
    self->close_internal_stream(self);
    self->free(self);
}

static void
bw_close_r(BitstreamRecorder* self)
{
    self->close_internal_stream(self);
    self->free(self);
}

static unsigned int
bw_bits_written_r(const BitstreamRecorder* self)
{
    return (unsigned int)(bw_buf_size(self->output.recorder) * 8 +
                          self->buffer_size);
}

static unsigned int
bw_bytes_written_r(const BitstreamRecorder* self)
{
    return bw_buf_size(self->output.recorder);
}

static void
bw_reset_r(BitstreamRecorder* self)
{
    self->buffer = 0;
    self->buffer_size = 0;
    bw_buf_reset(self->output.recorder);
}


static void
bw_copy_r(const BitstreamRecorder* self, BitstreamWriter* target)
{
    /*dump all the bytes from our internal buffer*/
    target->write_bytes(target, self->data(self), self->bytes_written(self));

    /*then dump remaining bits with a partial write() call*/
    if (self->buffer_size > 0) {
        target->write(target,
                      self->buffer_size,
                      self->buffer & ((1 << self->buffer_size) - 1));
    }
}

static const uint8_t*
bw_data_r(const BitstreamRecorder* self)
{
    return self->output.recorder->buffer;
}

static unsigned int
bw_bits_written_a(const BitstreamAccumulator *self)
{
    return self->output.accumulator + self->buffer_size;
}

static unsigned int
bw_bytes_written_a(const BitstreamAccumulator *self)
{
    return self->bits_written(self) / 8;
}

static void
bw_reset_a(BitstreamAccumulator *self)
{
    self->buffer = 0;
    self->buffer_size = 0;
    self->output.accumulator = 0;
}

static void
bw_free_a(BitstreamAccumulator *self)
{
    /*perform deallocations on reset of struct*/
    bw_free_f((BitstreamWriter*)self);
}

static void
bw_close_internal_stream_a(BitstreamAccumulator* self)
{
    bw_close_methods((BitstreamWriter*)self);
}

static void
bw_close_a(BitstreamAccumulator* self)
{
    self->close_internal_stream(self);
    self->free(self);
}

void
bw_abort(BitstreamWriter* bs)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "*** Error: EOF encountered, aborting\n");
        abort();
    }
}


jmp_buf*
bw_try(BitstreamWriter* bs)
{
    struct bs_exception *node;

    if (bs->exceptions_used == NULL)
        node = malloc(sizeof(struct bs_exception));
    else {
        node = bs->exceptions_used;
        bs->exceptions_used = bs->exceptions_used->next;
    }
    node->next = bs->exceptions;
    bs->exceptions = node;
    return &(node->env);
}

void
__bw_etry(BitstreamWriter* bs, const char *file, int lineno)
{
    struct bs_exception *node = bs->exceptions;
    if (node != NULL) {
        bs->exceptions = node->next;
        node->next = bs->exceptions_used;
        bs->exceptions_used = node;
    } else {
        fprintf(stderr,
                "*** Warning: %s %d: trying to pop from empty etry stack\n",
                file, lineno);
    }
}


void
recorder_swap(BitstreamRecorder **a, BitstreamRecorder **b)
{
    BitstreamRecorder *c = *a;
    *a = *b;
    *b = c;
}

const char*
bs_parse_format(const char *format,
                unsigned *times, unsigned *size, bs_instruction_t *inst)
{
    unsigned argument = 0;
    unsigned sub_times;

    /*skip whitespace*/
    while (isspace(format[0])) {
        format++;
    }

    /*the next token may be 1 or more digits*/
    while (isdigit(format[0])) {
        argument = (argument * 10) + (unsigned)(format[0] - '0');
        format++;
    }

    /*assign "times", "size" and "inst"
      based on the following instruction character (if valid)*/
    switch (format[0]) {
    case 'u':
        *times = 1;
        *size = argument;
        *inst = BS_INST_UNSIGNED;
        return format + 1;
    case 's':
        *times = 1;
        *size = argument;
        *inst = BS_INST_SIGNED;
        return format + 1;
    case 'U':
        *times = 1;
        *size = argument;
        *inst = BS_INST_UNSIGNED64;
        return format + 1;
    case 'S':
        *times = 1;
        *size = argument;
        *inst = BS_INST_SIGNED64;
        return format + 1;
    case 'K':
        *times = 1;
        *size = argument;
        *inst = BS_INST_UNSIGNED_BIGINT;
        return format + 1;
    case 'L':
        *times = 1;
        *size = argument;
        *inst = BS_INST_SIGNED_BIGINT;
        return format + 1;
    case 'p':
        *times = 1;
        *size = argument;
        *inst = BS_INST_SKIP;
        return format + 1;
    case 'P':
        *times = 1;
        *size = argument;
        *inst = BS_INST_SKIP_BYTES;
        return format + 1;
    case 'b':
        *times = 1;
        *size = argument;
        *inst = BS_INST_BYTES;
        return format + 1;
    case 'a':
        *times = 0;
        *size = 0;
        *inst = BS_INST_ALIGN;
        return format + 1;
    case '*':
        format = bs_parse_format(format + 1, &sub_times, size, inst);
        *times = argument * sub_times;
        return format;
    case '\0':
        *times = 0;
        *size = 0;
        *inst = BS_INST_EOF;
        return format;
    default:
        *times = 0;
        *size = 0;
        *inst = BS_INST_EOF;
        return format + 1;
    }
}


unsigned
bs_format_size(const char* format)
{
    unsigned total_size = 0;
    bs_instruction_t inst;

    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        switch (inst) {
        case BS_INST_UNSIGNED:
        case BS_INST_SIGNED:
        case BS_INST_UNSIGNED64:
        case BS_INST_SIGNED64:
        case BS_INST_UNSIGNED_BIGINT:
        case BS_INST_SIGNED_BIGINT:
        case BS_INST_SKIP:
            total_size += (times * size);
            break;
        case BS_INST_SKIP_BYTES:
        case BS_INST_BYTES:
            total_size += (times * size * 8);
            break;
        case BS_INST_ALIGN:
            total_size += (8 - (total_size % 8));
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);

    return total_size;
}

unsigned
bs_format_byte_size(const char* format)
{
    return bs_format_size(format) / 8;
}

void
byte_counter(uint8_t byte, unsigned* total_bytes)
{
    *total_bytes += 1;
}


#define FUNC_ADD_CALLBACK(FUNC_NAME, PUSH_CALLBACK_FUNC, STREAM) \
  static void                                                    \
  FUNC_NAME(STREAM *self, bs_callback_f callback, void* data)    \
  {                                                              \
      struct bs_callback callback_node;                          \
                                                                 \
      callback_node.callback = callback;                         \
      callback_node.data = data;                                 \
      PUSH_CALLBACK_FUNC(self, &callback_node);                  \
  }
FUNC_ADD_CALLBACK(br_add_callback, br_push_callback, BitstreamReader)
FUNC_ADD_CALLBACK(bw_add_callback, bw_push_callback, BitstreamWriter)

#define FUNC_PUSH_CALLBACK(FUNC_NAME, STREAM)           \
  static void                                           \
  FUNC_NAME(STREAM *self, struct bs_callback *callback) \
  {                                                     \
      if (callback != NULL) {                           \
          struct bs_callback *callback_node =           \
            malloc(sizeof(struct bs_callback));         \
          callback_node->callback = callback->callback; \
          callback_node->data = callback->data;         \
          callback_node->next = self->callbacks;        \
          self->callbacks = callback_node;              \
      }                                                 \
  }
FUNC_PUSH_CALLBACK(br_push_callback, BitstreamReader)
FUNC_PUSH_CALLBACK(bw_push_callback, BitstreamWriter)

#define FUNC_POP_CALLBACK(FUNC_NAME, STREAM)                     \
  static void                                                    \
  FUNC_NAME(STREAM *self, struct bs_callback *callback)          \
  {                                                              \
      struct bs_callback *c_node = self->callbacks;              \
      if (c_node != NULL) {                                      \
          if (callback != NULL) {                                \
              callback->callback = c_node->callback;             \
              callback->data = c_node->data;                     \
              callback->next = NULL;                             \
          }                                                      \
          self->callbacks = c_node->next;                        \
          free(c_node);                                          \
      } else {                                                   \
          fprintf(stderr, "*** Warning: no callbacks to pop\n"); \
      }                                                          \
  }
FUNC_POP_CALLBACK(br_pop_callback, BitstreamReader)
FUNC_POP_CALLBACK(bw_pop_callback, BitstreamWriter)

#define FUNC_CALL_CALLBACKS(FUNC_NAME, STREAM)      \
  static void                                       \
  FUNC_NAME(STREAM *self, uint8_t byte)             \
  {                                                 \
      struct bs_callback *callback;                 \
      for (callback = self->callbacks;              \
           callback != NULL;                        \
           callback = callback->next) {             \
          callback->callback(byte, callback->data); \
      }                                             \
  }
FUNC_CALL_CALLBACKS(br_call_callbacks, BitstreamReader)
FUNC_CALL_CALLBACKS(bw_call_callbacks, BitstreamWriter)


#define FUNC_FSEEK(FUNC_NAME, TYPE)                             \
  static int                                                           \
  FUNC_NAME(TYPE buf, long position, int whence)                \
  {                                                             \
      switch (whence) {                                         \
      case 0:  /*SEEK_SET*/                                     \
          if (position < 0) {                                   \
              /*can't seek before the beginning of the buffer*/ \
              return -1;                                        \
          } else if (position > buf->size) {                    \
              /*can't seek past the end of the buffer*/         \
              return -1;                                        \
          } else {                                              \
              buf->pos = (unsigned)position;                    \
              return 0;                                         \
          }                                                     \
      case 1:  /*SEEK_CUR*/                                     \
          if ((position < 0) && (-position > buf->pos)) {       \
              /*can't seek past the beginning of the buffer*/   \
              return -1;                                        \
          } else if ((position > 0) && (position > (buf->size - buf->pos))) { \
              /*can't seek past the end of the buffer*/         \
              return -1;                                        \
          } else {                                              \
              buf->pos += position;                             \
              return 0;                                         \
          }                                                     \
      case 2:  /*SEEK_END*/                                     \
          if (position > 0) {                                   \
              /*can't seek past the end of the buffer*/         \
              return -1;                                        \
          } else if (-position > buf->size) {                   \
              /*can't seek past the beginning of the buffer*/   \
              return -1;                                        \
          } else {                                              \
              buf->pos = buf->size + (unsigned)position;        \
              return 0;                                         \
          }                                                     \
      default:                                                  \
          /*unknown "whence"*/                                  \
          return -1;                                            \
      }                                                         \
  }
FUNC_FSEEK(br_buf_fseek, struct br_buffer*)
FUNC_FSEEK(br_queue_fseek, struct br_queue*)


void
bw_pos_stack_push(struct bw_pos_stack** stack, bw_pos_t* pos)
{
    struct bw_pos_stack* new_node = malloc(sizeof(struct bw_pos_stack));
    new_node->pos = pos;
    new_node->next = *stack;
    *stack = new_node;
}

bw_pos_t*
bw_pos_stack_pop(struct bw_pos_stack** stack)
{
    struct bw_pos_stack *top_node = *stack;
    bw_pos_t *pos = top_node->pos;
    *stack = top_node->next;
    free(top_node);
    return pos;
}

#ifdef HAS_PYTHON

unsigned
br_read_python(PyObject *reader,
               uint8_t *buffer,
               unsigned buffer_size)
{
    /*call read() method on reader*/
    PyObject* read_result =
        PyObject_CallMethod(reader, "read", "I", buffer_size);
    char *string;
    Py_ssize_t string_size;
    unsigned to_copy;

    if (read_result == NULL) {
        /*some exception occurred, so clear result and return no bytes
          (which will likely turn into an I/O exception later)*/
        PyErr_Clear();
        return 0;
    }

    /*get string data from returned object*/
    if (PyBytes_AsStringAndSize(read_result,
                                &string,
                                &string_size) == -1) {
        /*got something that wasn't a string from .read()
          so clear exception and return no bytes*/
        Py_DECREF(read_result);
        PyErr_Clear();
        return 0;
    }

    /*write either "buffer_size" or "string_size" bytes to buffer
      whichever is less*/
    if (string_size >= buffer_size) {
        /*truncate strings larger than expected*/
        to_copy = buffer_size;
    } else {
        to_copy = (unsigned)string_size;
    }

    memcpy(buffer, (uint8_t*)string, to_copy);

    /*perform cleanup and return bytes actually read*/
    Py_DECREF(read_result);

    return to_copy;
}

int bw_write_python(PyObject* writer,
                    const uint8_t *buffer,
                    unsigned buffer_size)
{
#if PY_MAJOR_VERSION >= 3
    char format[] = "y#";
#else
    char format[] = "s#";
#endif
    PyObject* write_result = PyObject_CallMethod(writer,
                                                 "write", format,
                                                 buffer,
                                                 (int)buffer_size);
    if (write_result != NULL) {
        Py_DECREF(write_result);
        return 0;
    } else {
        /*write method call failed so clear error and return a failure
          which will probably turn into an I/O exception later*/
        PyErr_Clear();
        return 1;
    }
}

int
bw_flush_python(PyObject* writer)
{
    PyObject* flush_result = PyObject_CallMethod(writer, "flush", NULL);
    if (flush_result != NULL) {
        Py_DECREF(flush_result);
        return 0;
    } else {
        /*flush method call failed, so clear error and return failure*/
        PyErr_Clear();
        return EOF;
    }
}

int
bs_setpos_python(PyObject* stream, PyObject* pos)
{
    if (pos != NULL) {
        PyObject *seek = PyObject_GetAttrString(stream, "seek");
        if (seek != NULL) {
            PyObject *result = PyObject_CallFunctionObjArgs(seek, pos, NULL);
            Py_DECREF(seek);
            if (result != NULL) {
                Py_DECREF(result);
                return 0;
            } else {
                /*some error occurred calling seek()*/
                PyErr_Clear();
                return EOF;
            }
        } else {
            /*unable to find seek method in object*/
            PyErr_Clear();
            return EOF;
        }
    }
    /*do nothing if position is empty*/
    return 0;
}

PyObject*
bs_getpos_python(PyObject* stream)
{
    PyObject *pos = PyObject_CallMethod(stream, "tell", NULL);
    if (pos != NULL) {
        return pos;
    } else {
        PyErr_Clear();
        return NULL;
    }
}

void
bs_free_pos_python(PyObject* pos)
{
    Py_XDECREF(pos);
}

int
bs_fseek_python(PyObject* stream, long position, int whence)
{
    PyObject *result =
        PyObject_CallMethod(stream, "seek", "li", position, whence);
    if (result != NULL) {
        Py_DECREF(result);
        return 0;
    } else {
        return 1;
    }
}

int
bs_close_python(PyObject* obj)
{
    /*call close method on reader/writer*/
    PyObject* close_result = PyObject_CallMethod(obj, "close", NULL);
    if (close_result != NULL) {
        /*ignore result*/
        Py_DECREF(close_result);
        return 0;
    } else {
        /*close method call failed, so clear error and return failure*/
        PyErr_Clear();
        return EOF;
    }
}

void
bs_free_python_decref(PyObject* obj)
{
    Py_XDECREF(obj);
}

void
bs_free_python_nodecref(PyObject* obj)
{
    /*no DECREF, so does nothing*/
    return;
}

int
python_obj_seekable(PyObject* obj)
{
    PyObject *seek;
    PyObject *tell;

    /*ensure object has a seek() method*/
    seek = PyObject_GetAttrString(obj, "seek");
    if (seek != NULL) {
        const int callable = PyCallable_Check(seek);
        Py_DECREF(seek);
        if (callable == 0) {
            /*seek isn't callable*/
            return 0;
        }
    } else {
        /*no .seek() attr*/
        return 0;
    }

    /*ensure object has a tell() method*/
    tell = PyObject_GetAttrString(obj, "tell");
    if (tell != NULL) {
        const int callable = PyCallable_Check(tell);
        Py_DECREF(tell);
        return (callable == 1);
    } else {
        /*no .seek() attr*/
        return 0;
    }
}

#endif

/*****************************************************************
 BEGIN UNIT TESTS
 *****************************************************************/


#ifdef EXECUTABLE

#include <unistd.h>
#include <signal.h>
#include <sys/stat.h>
#include "huffman.h"

char temp_filename[] = "bitstream.XXXXXX";

void
atexit_cleanup(void);
void
sigabort_cleanup(int signum);

void
test_big_endian_reader(BitstreamReader* reader,
                       br_huffman_table_t table[]);

void
test_big_endian_parse(BitstreamReader* reader);

void
test_little_endian_reader(BitstreamReader* reader,
                          br_huffman_table_t table[]);

void
test_little_endian_parse(BitstreamReader* reader);

void
test_close_errors(BitstreamReader* reader,
                  br_huffman_table_t table[]);

void
test_try(BitstreamReader* reader,
         br_huffman_table_t table[]);

void
test_callbacks_reader(BitstreamReader* reader,
                      int unary_0_reads,
                      int unary_1_reads,
                      br_huffman_table_t table[],
                      int huffman_code_count);

void
test_edge_cases(void);
void
test_edge_reader_be(BitstreamReader* reader);
void
test_edge_reader_le(BitstreamReader* reader);
void
test_edge_writer(BitstreamWriter* (*get_writer)(void),
                 void (*validate_writer)(BitstreamWriter*));
void
test_edge_recorder(BitstreamRecorder* (*get_writer)(void),
                   void (*validate_writer)(BitstreamRecorder*));

BitstreamWriter*
get_edge_writer_be(void);
BitstreamRecorder*
get_edge_recorder_be(void);

void
validate_edge_writer_be(BitstreamWriter* writer);
void
validate_edge_recorder_be(BitstreamRecorder* recorder);

BitstreamWriter*
get_edge_writer_le(void);
BitstreamRecorder*
get_edge_recorder_le(void);

void
validate_edge_writer_le(BitstreamWriter* writer);
void
validate_edge_recorder_le(BitstreamRecorder* recorder);

/*this uses "temp_filename" as an output file and opens it separately*/
void
test_writer(bs_endianness endianness);

void
test_rec_copy_dumps(bs_endianness endianness,
                    BitstreamWriter* writer,
                    BitstreamRecorder* recorder);

void
test_writer_close_errors(BitstreamWriter* writer);
void
test_recorder_close_errors(BitstreamRecorder* recorder);

void
test_writer_marks(BitstreamWriter* writer);

void
writer_perform_write(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_signed(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_64(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_signed_64(BitstreamWriter* writer,
                               bs_endianness endianness);
void
writer_perform_write_bigint(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_signed_bigint(BitstreamWriter* writer,
                                   bs_endianness endianness);
void
writer_perform_write_unary_0(BitstreamWriter* writer,
                             bs_endianness endianness);
void
writer_perform_write_unary_1(BitstreamWriter* writer,
                             bs_endianness endianness);

void
writer_perform_build_u(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_U(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_s(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_S(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_K(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_L(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_b(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_build_mult(BitstreamWriter* writer,
                          bs_endianness endianness);

void
writer_perform_huffman(BitstreamWriter* writer,
                       bs_endianness endianness);

void
writer_perform_write_bytes(BitstreamWriter* writer,
                           bs_endianness endianness);

typedef void (*write_check)(BitstreamWriter*, bs_endianness);


void
check_output_file(void);

unsigned ext_fread_test(FILE* user_data,
                        uint8_t* buffer,
                        unsigned buffer_size);

int ext_fclose_test(FILE* user_data);

void ext_ffree_test(FILE* user_data);

int ext_fwrite_test(FILE* user_data,
                    const uint8_t* buffer,
                    unsigned buffer_size);

int ext_fflush_test(FILE* user_data);

int ext_fsetpos_test(FILE *user_data, fpos_t *pos);

fpos_t* ext_fgetpos_test(FILE *user_data);

int ext_fseek_test(FILE *user_data, long location, int whence);

void ext_free_pos_test(fpos_t *pos);

typedef struct {
    unsigned bits;
    unsigned value;
    unsigned resulting_bytes;
    unsigned resulting_value;
} align_check;

void check_alignment_f(const align_check* check,
                       bs_endianness endianness);

void check_alignment_r(const align_check* check,
                       bs_endianness endianness);


void check_alignment_e(const align_check* check,
                       bs_endianness endianness);

void func_add_one(uint8_t byte, int* value);
void func_add_two(uint8_t byte, int* value);
void func_mult_three(uint8_t byte, int* value);

int main(int argc, char* argv[]) {
    int fd;
    FILE* temp_file;
    FILE* temp_file2;
    BitstreamReader* reader;
    BitstreamReader* subreader;
    BitstreamReader* subsubreader;
    BitstreamQueue* queue;
    br_pos_t* pos;
    struct sigaction new_action, old_action;
    const uint8_t buffer_data[] = {0xB1, 0xED, 0x3B, 0xC1};

    struct huffman_frequency frequencies[] =
        {bw_str_to_frequency("11", 0),
         bw_str_to_frequency("10", 1),
         bw_str_to_frequency("01", 2),
         bw_str_to_frequency("001", 3),
         bw_str_to_frequency("000", 4)};
    br_huffman_table_t *be_table;
    br_huffman_table_t *le_table;

    new_action.sa_handler = sigabort_cleanup;
    sigemptyset(&new_action.sa_mask);
    new_action.sa_flags = 0;

    if ((fd = mkstemp(temp_filename)) == -1) {
        fprintf(stderr, "Error creating temporary file\n");
        return 1;
    } else if ((temp_file = fdopen(fd, "w+")) == NULL) {
        fprintf(stderr, "Error opening temporary file\n");
        unlink(temp_filename);
        close(fd);

        return 2;
    } else {
        atexit(atexit_cleanup);
        sigaction(SIGABRT, NULL, &old_action);
        if (old_action.sa_handler != SIG_IGN)
            sigaction(SIGABRT, &new_action, NULL);
    }

    /*compile the Huffman tables*/
    compile_br_huffman_table(&be_table, frequencies, 5, BS_BIG_ENDIAN);
    compile_br_huffman_table(&le_table, frequencies, 5, BS_LITTLE_ENDIAN);

    /*write some test data to the temporary file*/
    fputc(0xB1, temp_file);
    fputc(0xED, temp_file);
    fputc(0x3B, temp_file);
    fputc(0xC1, temp_file);
    fseek(temp_file, 0, SEEK_SET);

    /*test a big-endian stream*/
    reader = br_open(temp_file, BS_BIG_ENDIAN);
    test_big_endian_reader(reader, be_table);
    test_big_endian_parse(reader);
    test_try(reader, be_table);
    test_callbacks_reader(reader, 14, 18, be_table, 14);
    reader->free(reader);

    temp_file2 = fopen(temp_filename, "rb");
    reader = br_open(temp_file2, BS_BIG_ENDIAN);
    test_close_errors(reader, be_table);
    reader->close(reader);
    temp_file2 = fopen(temp_filename, "rb");
    reader = br_open(temp_file2, BS_LITTLE_ENDIAN);
    test_close_errors(reader, le_table);
    reader->free(reader);

    fseek(temp_file, 0, SEEK_SET);

    /*test a big-endian buffer*/
    reader = br_open_buffer(buffer_data, 4, BS_BIG_ENDIAN);
    test_big_endian_reader(reader, be_table);
    test_big_endian_parse(reader);
    test_try(reader, be_table);
    test_callbacks_reader(reader, 14, 18, be_table, 14);
    reader->free(reader);

    /*test a big-endian queue*/
    queue = br_open_queue(BS_BIG_ENDIAN);
    assert(queue->size(queue) == 0);
    queue->push(queue, 4, buffer_data);
    assert(queue->size(queue) == 4);
    test_big_endian_reader((BitstreamReader*)queue, be_table);
    test_big_endian_parse((BitstreamReader*)queue);
    test_try((BitstreamReader*)queue, be_table);
    test_callbacks_reader((BitstreamReader*)queue, 14, 18, be_table, 14);
    queue->skip_bytes((BitstreamReader*)queue, 4);
    assert(queue->size(queue) == 0);
    queue->push(queue, 4, buffer_data);
    assert(queue->size(queue) == 4);
    test_big_endian_reader((BitstreamReader*)queue, be_table);
    test_big_endian_parse((BitstreamReader*)queue);
    test_try((BitstreamReader*)queue, be_table);
    test_callbacks_reader((BitstreamReader*)queue, 14, 18, be_table, 14);
    queue->skip_bytes((BitstreamReader*)queue, 4);
    assert(queue->size(queue) == 0);

    fseek(temp_file, 0, SEEK_SET);

    reader = br_open(temp_file, BS_BIG_ENDIAN);
    reader->enqueue(reader, 4, queue);
    reader->free(reader);
    assert(queue->size(queue) == 4);
    test_big_endian_reader((BitstreamReader*)queue, be_table);
    test_big_endian_parse((BitstreamReader*)queue);
    test_try((BitstreamReader*)queue, be_table);
    test_callbacks_reader((BitstreamReader*)queue, 14, 18, be_table, 14);
    queue->free(queue);

    fseek(temp_file, 0, SEEK_SET);

    /*test a big-endian stream using external functions*/
    reader = br_open_external(temp_file,
                              BS_BIG_ENDIAN,
                              2,
                              (ext_read_f)ext_fread_test,
                              (ext_setpos_f)ext_fsetpos_test,
                              (ext_getpos_f)ext_fgetpos_test,
                              (ext_free_pos_f)ext_free_pos_test,
                              (ext_seek_f)ext_fseek_test,
                              (ext_close_f)ext_fclose_test,
                              (ext_free_f)ext_ffree_test);
    test_big_endian_reader(reader, be_table);
    test_big_endian_parse(reader);
    test_try(reader, be_table);
    test_callbacks_reader(reader, 14, 18, be_table, 14);
    reader->free(reader);

    fseek(temp_file, 0, SEEK_SET);

    /*test a little-endian stream*/
    reader = br_open(temp_file, BS_LITTLE_ENDIAN);
    test_little_endian_reader(reader, le_table);
    test_little_endian_parse(reader);
    test_try(reader, le_table);
    test_callbacks_reader(reader, 14, 18, le_table, 13);
    reader->free(reader);

    temp_file2 = fopen(temp_filename, "rb");
    reader = br_open(temp_file2, BS_LITTLE_ENDIAN);
    test_close_errors(reader, le_table);
    reader->close(reader);
    temp_file2 = fopen(temp_filename, "rb");
    reader = br_open(temp_file2, BS_BIG_ENDIAN);
    test_close_errors(reader, be_table);
    reader->close(reader);

    /*test a little-endian buffer*/
    reader = br_open_buffer(buffer_data, 4, BS_LITTLE_ENDIAN);
    test_little_endian_reader(reader, le_table);
    test_little_endian_parse(reader);
    test_try(reader, le_table);
    test_callbacks_reader(reader, 14, 18, le_table, 14);
    reader->free(reader);

    /*test a little-endian queue*/
    queue = br_open_queue(BS_LITTLE_ENDIAN);
    assert(queue->size(queue) == 0);
    queue->push(queue, 4, buffer_data);
    assert(queue->size(queue) == 4);
    test_little_endian_reader((BitstreamReader*)queue, le_table);
    test_little_endian_parse((BitstreamReader*)queue);
    test_try((BitstreamReader*)queue, le_table);
    test_callbacks_reader((BitstreamReader*)queue, 14, 18, le_table, 14);
    queue->skip_bytes((BitstreamReader*)queue, 4);
    assert(queue->size(queue) == 0);
    queue->push(queue, 4, buffer_data);
    assert(queue->size(queue) == 4);
    test_little_endian_reader((BitstreamReader*)queue, le_table);
    test_little_endian_parse((BitstreamReader*)queue);
    test_try((BitstreamReader*)queue, le_table);
    test_callbacks_reader((BitstreamReader*)queue, 14, 18, le_table, 14);
    queue->skip_bytes((BitstreamReader*)queue, 4);
    assert(queue->size(queue) == 0);

    fseek(temp_file, 0, SEEK_SET);

    reader = br_open(temp_file, BS_LITTLE_ENDIAN);
    reader->enqueue(reader, 4, queue);
    reader->free(reader);
    assert(queue->size(queue) == 4);
    test_little_endian_reader((BitstreamReader*)queue, le_table);
    test_little_endian_parse((BitstreamReader*)queue);
    test_try((BitstreamReader*)queue, le_table);
    test_callbacks_reader((BitstreamReader*)queue, 14, 18, le_table, 14);
    queue->free(queue);

    fseek(temp_file, 0, SEEK_SET);

    /*test a little-endian stream using external functions*/
    reader = br_open_external(temp_file,
                              BS_LITTLE_ENDIAN,
                              2,
                              (ext_read_f)ext_fread_test,
                              (ext_setpos_f)ext_fsetpos_test,
                              (ext_getpos_f)ext_fgetpos_test,
                              (ext_free_pos_f)ext_free_pos_test,
                              (ext_seek_f)ext_fseek_test,
                              (ext_close_f)ext_fclose_test,
                              (ext_free_f)ext_ffree_test);
    test_little_endian_reader(reader, le_table);
    test_little_endian_parse(reader);
    test_try(reader, le_table);
    test_callbacks_reader(reader, 14, 18, le_table, 13);
    reader->free(reader);

    fseek(temp_file, 0, SEEK_SET);


    /*pad the stream with some additional data on both ends*/
    fseek(temp_file, 0, SEEK_SET);
    fputc(0xFF, temp_file);
    fputc(0xFF, temp_file);
    fputc(0xB1, temp_file);
    fputc(0xED, temp_file);
    fputc(0x3B, temp_file);
    fputc(0xC1, temp_file);
    fputc(0xFF, temp_file);
    fputc(0xFF, temp_file);
    fseek(temp_file, 0, SEEK_SET);

    reader = br_open(temp_file, BS_BIG_ENDIAN);
    pos = reader->getpos(reader);

    /*check a big-endian substream built from a file*/
    reader->skip(reader, 16);
    subreader = reader->substream(reader, 4);
    test_big_endian_reader(subreader, be_table);
    test_big_endian_parse(subreader);
    test_try(subreader, be_table);
    test_callbacks_reader(subreader, 14, 18, be_table, 14);
    subreader->close(subreader);

    reader->setpos(reader, pos);
    reader->skip(reader, 16);
    subreader = reader->substream(reader, 4);
    test_close_errors(subreader, be_table);
    subreader->close(subreader);

    /*check a big-endian substream built from another substream*/
    reader->setpos(reader, pos);
    reader->skip(reader, 8);
    subreader = reader->substream(reader, 6);
    subreader->skip(subreader, 8);
    subsubreader = subreader->substream(subreader, 4);
    test_big_endian_reader(subsubreader, be_table);
    test_big_endian_parse(subsubreader);
    test_try(subsubreader, be_table);
    test_callbacks_reader(subsubreader, 14, 18, be_table, 14);
    subsubreader->close(subsubreader);
    subreader->close(subreader);
    reader->setpos(reader, pos);
    pos->del(pos);
    reader->free(reader);

    reader = br_open(temp_file, BS_LITTLE_ENDIAN);
    pos = reader->getpos(reader);

    /*check a little-endian substream built from a file*/
    reader->skip(reader, 16);
    subreader = reader->substream(reader, 4);
    test_little_endian_reader(subreader, le_table);
    test_little_endian_parse(subreader);
    test_try(subreader, le_table);
    test_callbacks_reader(subreader, 14, 18, le_table, 13);
    subreader->close(subreader);

    reader->setpos(reader, pos);
    reader->skip(reader, 16);
    subreader = reader->substream(reader, 4);
    test_close_errors(subreader, le_table);
    subreader->close(subreader);

    /*check a little-endian substream built from another substream*/
    reader->setpos(reader, pos);
    reader->skip(reader, 8);
    subreader = reader->substream(reader, 6);
    subreader->skip(subreader, 8);
    subsubreader = subreader->substream(subreader, 4);
    test_little_endian_reader(subsubreader, le_table);
    test_little_endian_parse(subsubreader);
    test_try(subsubreader, le_table);
    test_callbacks_reader(subsubreader, 14, 18, le_table, 13);
    subsubreader->close(subsubreader);
    subreader->close(subreader);
    reader->setpos(reader, pos);
    pos->del(pos);
    reader->free(reader);

    free(be_table);
    free(le_table);

    /*test the writer functions with each endianness*/
    test_writer(BS_BIG_ENDIAN);
    test_writer(BS_LITTLE_ENDIAN);

    /*check edge cases against known values*/
    test_edge_cases();

    fclose(temp_file);

    return 0;
}

void atexit_cleanup(void) {
    unlink(temp_filename);
}

void sigabort_cleanup(int signum) {
    unlink(temp_filename);
}

void test_big_endian_reader(BitstreamReader* reader,
                            br_huffman_table_t table[]) {
    unsigned i;
    uint8_t sub_data[2];
    const uint8_t actual_data[4] = {0xB1, 0xED, 0x3B, 0xC1};
    uint8_t read_data[4];
    mpz_t value;
    br_pos_t *pos1;
    br_pos_t *pos2;
    br_pos_t *pos3;

    mpz_init(value);

    /*check the bitstream reader
      against some known big-endian values*/

    pos1 = reader->getpos(reader);
    assert(reader->read(reader, 2) == 0x2);
    assert(reader->read(reader, 3) == 0x6);
    assert(reader->read(reader, 5) == 0x07);
    assert(reader->read(reader, 3) == 0x5);
    assert(reader->read(reader, 19) == 0x53BC1);

    reader->setpos(reader, pos1);
    assert(reader->read_64(reader, 2) == 0x2);
    assert(reader->read_64(reader, 3) == 0x6);
    assert(reader->read_64(reader, 5) == 0x07);
    assert(reader->read_64(reader, 3) == 0x5);
    assert(reader->read_64(reader, 19) == 0x53BC1);

    reader->setpos(reader, pos1);
    reader->read_bigint(reader, 2, value);
    assert(mpz_get_ui(value) == 0x2);
    reader->read_bigint(reader, 3, value);
    assert(mpz_get_ui(value) == 0x6);
    reader->read_bigint(reader, 5, value);
    assert(mpz_get_ui(value) == 0x07);
    reader->read_bigint(reader, 3, value);
    assert(mpz_get_ui(value) == 0x5);
    reader->read_bigint(reader, 19, value);
    assert(mpz_get_ui(value) == 0x53BC1);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 2) == 0x2);
    reader->skip(reader, 3);
    assert(reader->read(reader, 5) == 0x07);
    reader->skip(reader, 3);
    assert(reader->read(reader, 19) == 0x53BC1);

    reader->setpos(reader, pos1);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0xE);
    reader->setpos(reader, pos1);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0x3);
    reader->setpos(reader, pos1);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0xC);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0xD);
    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0x7);
    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0x8);
    reader->setpos(reader, pos1);

    assert(reader->byte_aligned(reader));
    for (i = 0; i < 32; i++) {
        const unsigned bit = reader->read(reader, 1);
        unsigned re_read;
        reader->unread(reader, bit);
        re_read = reader->read(reader, 1);
        assert(bit == re_read);
    }
    assert(reader->byte_aligned(reader));

    reader->setpos(reader, pos1);

    reader->unread(reader, reader->read(reader, 1));
    assert(reader->byte_aligned(reader));
    reader->byte_align(reader);
    reader->read_bytes(reader, read_data, 4);
    assert(reader->byte_aligned(reader));
    assert(!memcmp(read_data, actual_data, 4));

    reader->setpos(reader, pos1);
    assert(reader->read_signed(reader, 2) == -2);
    assert(reader->read_signed(reader, 3) == -2);
    assert(reader->read_signed(reader, 5) == 7);
    assert(reader->read_signed(reader, 3) == -3);
    assert(reader->read_signed(reader, 19) == -181311);

    reader->setpos(reader, pos1);
    assert(reader->read_signed_64(reader, 2) == -2);
    assert(reader->read_signed_64(reader, 3) == -2);
    assert(reader->read_signed_64(reader, 5) == 7);
    assert(reader->read_signed_64(reader, 3) == -3);
    assert(reader->read_signed_64(reader, 19) == -181311);

    reader->setpos(reader, pos1);
    reader->read_signed_bigint(reader, 2, value);
    assert(mpz_get_si(value) == -2);
    reader->read_signed_bigint(reader, 3, value);
    assert(mpz_get_si(value) == -2);
    reader->read_signed_bigint(reader, 5, value);
    assert(mpz_get_si(value) == 7);
    reader->read_signed_bigint(reader, 3, value);
    assert(mpz_get_si(value) == -3);
    reader->read_signed_bigint(reader, 19, value);
    assert(mpz_get_si(value) == -181311);

    reader->setpos(reader, pos1);
    assert(reader->read_unary(reader, 0) == 1);
    assert(reader->read_unary(reader, 0) == 2);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 4);

    reader->setpos(reader, pos1);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 1);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 3);
    assert(reader->read_unary(reader, 1) == 0);

    reader->setpos(reader, pos1);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 4);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 2);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 2);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 2);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 4);
    assert(reader->read_huffman_code(reader, table) == 2);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 3) == 5);
    reader->byte_align(reader);
    assert(reader->read(reader, 3) == 7);
    reader->byte_align(reader);
    reader->byte_align(reader);
    assert(reader->read(reader, 8) == 59);
    reader->byte_align(reader);
    assert(reader->read(reader, 4) == 12);

    reader->setpos(reader, pos1);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\xB1\xED", 2) == 0);
    reader->setpos(reader, pos1);
    assert(reader->read(reader, 4) == 11);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\x1E\xD3", 2) == 0);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 3) == 5);
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    assert(reader->read(reader, 3) == 5);
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    assert(reader->read(reader, 4) == 3);
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    assert(reader->read(reader, 4) == 12);

    reader->setpos(reader, pos1);
    pos2 = reader->getpos(reader);
    assert(reader->read(reader, 4) == 0xB);
    reader->setpos(reader, pos2);
    assert(reader->read(reader, 8) == 0xB1);
    reader->setpos(reader, pos2);
    assert(reader->read(reader, 12) == 0xB1E);
    pos2->del(pos2);
    pos3 = reader->getpos(reader);
    assert(reader->read(reader, 4) == 0xD);
    reader->setpos(reader, pos3);
    assert(reader->read(reader, 8) == 0xD3);
    reader->setpos(reader, pos3);
    assert(reader->read(reader, 12) == 0xD3B);
    pos3->del(pos3);

    reader->seek(reader, 3, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, 2, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, 1, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, 0, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 4, BS_SEEK_SET);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, -1, BS_SEEK_SET);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->seek(reader, -1, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, -2, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, -3, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, -4, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, -5, BS_SEEK_END);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 1, BS_SEEK_END);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 3, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 2, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 1, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 0, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_SET);
        reader->seek(reader, 4, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_SET);
        reader->seek(reader, -1, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -1, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -2, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -3, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -4, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_END);
        reader->seek(reader, -5, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_END);
        reader->seek(reader, 1, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->setpos(reader, pos1);
    pos1->del(pos1);

    mpz_clear(value);
}

void test_big_endian_parse(BitstreamReader* reader) {
    unsigned u1,u2,u3,u4,u5,u6;
    int s1,s2,s3,s4,s5;
    uint64_t U1,U2,U3,U4,U5;
    int64_t S1,S2,S3,S4,S5;
    uint8_t sub_data1[2];
    uint8_t sub_data2[2];
    mpz_t B1,B2,B3,B4,B5;
    br_pos_t *pos;

    mpz_init(B1);
    mpz_init(B2);
    mpz_init(B3);
    mpz_init(B4);
    mpz_init(B5);

    pos = reader->getpos(reader);

    /*first, check all the defined format fields*/
    reader->parse(reader, "2u 3u 5u 3u 19u", &u1, &u2, &u3, &u4, &u5);
    assert(u1 == 0x2);
    assert(u2 == 0x6);
    assert(u3 == 0x07);
    assert(u4 == 0x5);
    assert(u5 == 0x53BC1);

    reader->setpos(reader, pos);
    reader->parse(reader, "2s 3s 5s 3s 19s", &s1, &s2, &s3, &s4, &s5);
    assert(s1 == -2);
    assert(s2 == -2);
    assert(s3 == 7);
    assert(s4 == -3);
    assert(s5 == -181311);

    reader->setpos(reader, pos);
    reader->parse(reader, "2U 3U 5U 3U 19U", &U1, &U2, &U3, &U4, &U5);
    assert(U1 == 0x2);
    assert(U2 == 0x6);
    assert(U3 == 0x07);
    assert(U4 == 0x5);
    assert(U5 == 0x53BC1);

    reader->setpos(reader, pos);
    reader->parse(reader, "2S 3S 5S 3S 19S", &S1, &S2, &S3, &S4, &S5);
    assert(S1 == -2);
    assert(S2 == -2);
    assert(S3 == 7);
    assert(S4 == -3);
    assert(S5 == -181311);

    reader->setpos(reader, pos);
    reader->parse(reader, "2K 3K 5K 3K 19K", &B1, &B2, &B3, &B4, &B5);
    assert(mpz_get_ui(B1) == 0x2);
    assert(mpz_get_ui(B2) == 0x6);
    assert(mpz_get_ui(B3) == 0x07);
    assert(mpz_get_ui(B4) == 0x5);
    assert(mpz_get_ui(B5) == 0x53BC1);

    reader->setpos(reader, pos);
    reader->parse(reader, "2L 3L 5L 3L 19L", &B1, &B2, &B3, &B4, &B5);
    assert(mpz_get_si(B1) == -2);
    assert(mpz_get_si(B2) == -2);
    assert(mpz_get_si(B3) == 7);
    assert(mpz_get_si(B4) == -3);
    assert(mpz_get_si(B5) == -181311);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 3p 5u 3p 19u", &u1, &u3, &u5);
    assert(u1 == 0x2);
    assert(u3 == 0x07);
    assert(u5 == 0x53BC1);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2p 1P 3u 19u", &u4, &u5);
    assert(u4 == 0x5);
    assert(u5 == 0x53BC1);

    reader->setpos(reader, pos);
    reader->parse(reader, "2b 2b", sub_data1, sub_data2);
    assert(memcmp(sub_data1, "\xB1\xED", 2) == 0);
    assert(memcmp(sub_data2, "\x3B\xC1", 2) == 0);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u a 3u a 4u a 5u", &u1, &u2, &u3, &u4);
    assert(u1 == 2);
    assert(u2 == 7);
    assert(u3 == 3);
    assert(u4 == 24);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "3* 2u", &u1, &u2, &u3);
    assert(u1 == 2);
    assert(u2 == 3);
    assert(u3 == 0);

    u1 = u2 = u3 = u4 = u5 = u6 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "3* 2* 2u", &u1, &u2, &u3, &u4, &u5, &u6);
    assert(u1 == 2);
    assert(u2 == 3);
    assert(u3 == 0);
    assert(u4 == 1);
    assert(u5 == 3);
    assert(u6 == 2);

    /*then check some errors which trigger an end-of-format*/

    /*unknown instruction*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u ? 3u", &u1);
    assert(u1 == 2);

    /*unknown instruction prefixed by number*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 10? 3u", &u1);
    assert(u1 == 2);

    /*unknown instruction prefixed by multiplier*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 10* ? 3u", &u1);
    assert(u1 == 2);

    /*unknown instruction prefixed by number and multiplier*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 10* 3? 3u", &u1);
    assert(u1 == 2);

    reader->setpos(reader, pos);
    pos->del(pos);

    mpz_clear(B1);
    mpz_clear(B2);
    mpz_clear(B3);
    mpz_clear(B4);
    mpz_clear(B5);
}

void test_little_endian_reader(BitstreamReader* reader,
                               br_huffman_table_t table[]) {
    unsigned i;
    uint8_t sub_data[2];
    const uint8_t actual_data[4] = {0xB1, 0xED, 0x3B, 0xC1};
    uint8_t read_data[4];
    mpz_t value;
    br_pos_t* pos1;
    br_pos_t* pos2;
    br_pos_t* pos3;

    mpz_init(value);

    /*check the bitstream reader
      against some known little-endian values*/

    pos1 = reader->getpos(reader);
    assert(reader->read(reader, 2) == 0x1);
    assert(reader->read(reader, 3) == 0x4);
    assert(reader->read(reader, 5) == 0x0D);
    assert(reader->read(reader, 3) == 0x3);
    assert(reader->read(reader, 19) == 0x609DF);

    reader->setpos(reader, pos1);
    assert(reader->read_64(reader, 2) == 1);
    assert(reader->read_64(reader, 3) == 4);
    assert(reader->read_64(reader, 5) == 13);
    assert(reader->read_64(reader, 3) == 3);
    assert(reader->read_64(reader, 19) == 395743);

    reader->setpos(reader, pos1);
    reader->read_bigint(reader, 2, value);
    assert(mpz_get_ui(value) == 1);
    reader->read_bigint(reader, 3, value);
    assert(mpz_get_ui(value) == 4);
    reader->read_bigint(reader, 5, value);
    assert(mpz_get_ui(value) == 13);
    reader->read_bigint(reader, 3, value);
    assert(mpz_get_ui(value) == 3);
    reader->read_bigint(reader, 19, value);
    assert(mpz_get_ui(value) == 395743);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 2) == 0x1);
    reader->skip(reader, 3);
    assert(reader->read(reader, 5) == 0x0D);
    reader->skip(reader, 3);
    assert(reader->read(reader, 19) == 0x609DF);

    reader->setpos(reader, pos1);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0xD);
    reader->setpos(reader, pos1);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0xB);
    reader->setpos(reader, pos1);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0x1);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0x6);
    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0xD);
    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0x0);
    reader->setpos(reader, pos1);

    for (i = 0; i < 32; i++) {
        const unsigned bit = reader->read(reader, 1);
        unsigned re_read;
        reader->unread(reader, bit);
        re_read = reader->read(reader, 1);
        assert(bit == re_read);
    }
    assert(reader->byte_aligned(reader));

    reader->setpos(reader, pos1);

    reader->unread(reader, reader->read(reader, 1));
    assert(reader->byte_aligned(reader));
    reader->byte_align(reader);
    reader->read_bytes(reader, read_data, 4);
    assert(reader->byte_aligned(reader));
    assert(!memcmp(read_data, actual_data, 4));

    reader->setpos(reader, pos1);
    assert(reader->read_signed(reader, 2) == 1);
    assert(reader->read_signed(reader, 3) == -4);
    assert(reader->read_signed(reader, 5) == 13);
    assert(reader->read_signed(reader, 3) == 3);
    assert(reader->read_signed(reader, 19) == -128545);

    reader->setpos(reader, pos1);
    assert(reader->read_signed_64(reader, 2) == 1);
    assert(reader->read_signed_64(reader, 3) == -4);
    assert(reader->read_signed_64(reader, 5) == 13);
    assert(reader->read_signed_64(reader, 3) == 3);
    assert(reader->read_signed_64(reader, 19) == -128545);

    reader->setpos(reader, pos1);
    reader->read_signed_bigint(reader, 2, value);
    assert(mpz_get_si(value) == 1);
    reader->read_signed_bigint(reader, 3, value);
    assert(mpz_get_si(value) == -4);
    reader->read_signed_bigint(reader, 5, value);
    assert(mpz_get_si(value) == 13);
    reader->read_signed_bigint(reader, 3, value);
    assert(mpz_get_si(value) == 3);
    reader->read_signed_bigint(reader, 19, value);
    assert(mpz_get_si(value) == -128545);

    reader->setpos(reader, pos1);
    assert(reader->read_unary(reader, 0) == 1);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 2);
    assert(reader->read_unary(reader, 0) == 2);

    reader->setpos(reader, pos1);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 3);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 1);
    assert(reader->read_unary(reader, 1) == 0);

    reader->setpos(reader, pos1);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 3);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 2);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 0);
    assert(reader->read_huffman_code(reader, table) == 1);
    assert(reader->read_huffman_code(reader, table) == 2);
    assert(reader->read_huffman_code(reader, table) == 4);
    assert(reader->read_huffman_code(reader, table) == 3);

    reader->setpos(reader, pos1);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\xB1\xED", 2) == 0);
    reader->setpos(reader, pos1);
    assert(reader->read(reader, 4) == 1);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\xDB\xBE", 2) == 0);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 3) == 1);
    reader->byte_align(reader);
    assert(reader->read(reader, 3) == 5);
    reader->byte_align(reader);
    reader->byte_align(reader);
    assert(reader->read(reader, 8) == 59);
    reader->byte_align(reader);
    assert(reader->read(reader, 4) == 1);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 3) == 1);
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    assert(reader->read(reader, 3) == 7);
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    assert(reader->read(reader, 4) == 11);
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    assert(reader->read(reader, 4) == 1);

    reader->setpos(reader, pos1);
    pos2 = reader->getpos(reader);
    assert(reader->read(reader, 4) == 0x1);
    reader->setpos(reader, pos2);
    assert(reader->read(reader, 8) == 0xB1);
    reader->setpos(reader, pos2);
    assert(reader->read(reader, 12) == 0xDB1);
    pos2->del(pos2);
    pos3 = reader->getpos(reader);
    assert(reader->read(reader, 4) == 0xE);
    reader->setpos(reader, pos3);
    assert(reader->read(reader, 8) == 0xBE);
    reader->setpos(reader, pos3);
    assert(reader->read(reader, 12) == 0x3BE);
    pos3->del(pos3);

    reader->seek(reader, 3, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, 2, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, 1, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, 0, BS_SEEK_SET);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 4, BS_SEEK_SET);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, -1, BS_SEEK_SET);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->seek(reader, -1, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, -2, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, -3, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, -4, BS_SEEK_END);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, -5, BS_SEEK_END);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 1, BS_SEEK_END);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 3, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 2, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 1, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, 0, BS_SEEK_SET);
    reader->seek(reader, 0, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_SET);
        reader->seek(reader, 4, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_SET);
        reader->seek(reader, -1, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -1, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xC1);
    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -2, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0x3B);
    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -3, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xED);
    reader->seek(reader, 0, BS_SEEK_END);
    reader->seek(reader, -4, BS_SEEK_CUR);
    assert(reader->read(reader, 8) == 0xB1);
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_END);
        reader->seek(reader, -5, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }
    if (!setjmp(*br_try(reader))) {
        reader->seek(reader, 0, BS_SEEK_END);
        reader->seek(reader, 1, BS_SEEK_CUR);
        reader->read(reader, 8);
        assert(0);
    } else {
        br_etry(reader);
        assert(1);
    }

    reader->setpos(reader, pos1);
    pos1->del(pos1);
    mpz_clear(value);
}

void test_little_endian_parse(BitstreamReader* reader) {
    unsigned u1,u2,u3,u4,u5,u6;
    int s1,s2,s3,s4,s5;
    uint64_t U1,U2,U3,U4,U5;
    int64_t S1,S2,S3,S4,S5;
    uint8_t sub_data1[2];
    uint8_t sub_data2[2];
    mpz_t B1,B2,B3,B4,B5;
    br_pos_t* pos;

    mpz_init(B1);
    mpz_init(B2);
    mpz_init(B3);
    mpz_init(B4);
    mpz_init(B5);

    pos = reader->getpos(reader);

    /*first, check all the defined format fields*/
    reader->parse(reader, "2u 3u 5u 3u 19u", &u1, &u2, &u3, &u4, &u5);
    assert(u1 == 0x1);
    assert(u2 == 0x4);
    assert(u3 == 0x0D);
    assert(u4 == 0x3);
    assert(u5 == 0x609DF);

    reader->setpos(reader, pos);
    reader->parse(reader, "2s 3s 5s 3s 19s", &s1, &s2, &s3, &s4, &s5);
    assert(s1 == 1);
    assert(s2 == -4);
    assert(s3 == 13);
    assert(s4 == 3);
    assert(s5 == -128545);

    reader->setpos(reader, pos);
    reader->parse(reader, "2U 3U 5U 3U 19U", &U1, &U2, &U3, &U4, &U5);
    assert(u1 == 0x1);
    assert(u2 == 0x4);
    assert(u3 == 0x0D);
    assert(u4 == 0x3);
    assert(u5 == 0x609DF);

    reader->setpos(reader, pos);
    reader->parse(reader, "2S 3S 5S 3S 19S", &S1, &S2, &S3, &S4, &S5);
    assert(s1 == 1);
    assert(s2 == -4);
    assert(s3 == 13);
    assert(s4 == 3);
    assert(s5 == -128545);

    reader->setpos(reader, pos);
    reader->parse(reader, "2K 3K 5K 3K 19K", &B1, &B2, &B3, &B4, &B5);
    assert(mpz_get_ui(B1) == 0x1);
    assert(mpz_get_ui(B2) == 0x4);
    assert(mpz_get_ui(B3) == 0x0D);
    assert(mpz_get_ui(B4) == 0x3);
    assert(mpz_get_ui(B5) == 0x609DF);

    reader->setpos(reader, pos);
    reader->parse(reader, "2L 3L 5L 3L 19L", &B1, &B2, &B3, &B4, &B5);
    assert(mpz_get_si(B1) == 1);
    assert(mpz_get_si(B2) == -4);
    assert(mpz_get_si(B3) == 13);
    assert(mpz_get_si(B4) == 3);
    assert(mpz_get_si(B5) == -128545);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 3p 5u 3p 19u", &u1, &u3, &u5);
    assert(u1 == 0x1);
    assert(u3 == 0x0D);
    assert(u5 == 0x609DF);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2p 1P 3u 19u", &u4, &u5);
    assert(u4 == 0x3);
    assert(u5 == 0x609DF);

    reader->setpos(reader, pos);
    reader->parse(reader, "2b 2b", sub_data1, sub_data2);
    assert(memcmp(sub_data1, "\xB1\xED", 2) == 0);
    assert(memcmp(sub_data2, "\x3B\xC1", 2) == 0);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u a 3u a 4u a 5u", &u1, &u2, &u3, &u4);
    assert(u1 == 1);
    assert(u2 == 5);
    assert(u3 == 11);
    assert(u4 == 1);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "3* 2u", &u1, &u2, &u3);
    assert(u1 == 1);
    assert(u2 == 0);
    assert(u3 == 3);

    u1 = u2 = u3 = u4 = u5 = u6 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "3* 2* 2u", &u1, &u2, &u3, &u4, &u5, &u6);
    assert(u1 == 1);
    assert(u2 == 0);
    assert(u3 == 3);
    assert(u4 == 2);
    assert(u5 == 1);
    assert(u6 == 3);

    /*then check some errors which trigger an end-of-format*/

    /*unknown instruction*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u ? 3u", &u1);
    assert(u1 == 1);

    /*unknown instruction prefixed by number*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 10? 3u", &u1);
    assert(u1 == 1);

    /*unknown instruction prefixed by multiplier*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 10* ? 3u", &u1);
    assert(u1 == 1);

    /*unknown instruction prefixed by number and multiplier*/
    u1 = 0;
    reader->setpos(reader, pos);
    reader->parse(reader, "2u 10* 3? 3u", &u1);
    assert(u1 == 1);

    reader->setpos(reader, pos);
    pos->del(pos);

    mpz_clear(B1);
    mpz_clear(B2);
    mpz_clear(B3);
    mpz_clear(B4);
    mpz_clear(B5);
}

void
test_close_errors(BitstreamReader* reader,
                  br_huffman_table_t table[]) {
    uint8_t bytes[10];
    struct BitstreamReader_s* subreader;
    br_pos_t *pos;

    if (!setjmp(*br_try(reader))) {
        pos = reader->getpos(reader);
        br_etry(reader);
    } else {
        br_etry(reader);
        assert(0);
    }


    reader->close_internal_stream(reader);

    /*ensure all read methods on a closed file
      either call br_abort or do nothing*/

    if (!setjmp(*br_try(reader))) {
        reader->read(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read_signed(reader, 3);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read_64(reader, 4);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read_signed_64(reader, 5);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->skip(reader, 6);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->skip_bytes(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->unread(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read_unary(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read_huffman_code(reader, table);
        assert(0);
    } else {
        br_etry(reader);
    }

    reader->byte_align(reader); /*should do nothing*/

    if (!setjmp(*br_try(reader))) {
        reader->read_bytes(reader, bytes, 10);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->parse(reader, "10b", bytes);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        /*getting the pos of a closed stream is an I/O error*/
        br_pos_t* pos2 = reader->getpos(reader);
        pos2->del(pos2);
        br_etry(reader);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        /*setting the pos of a closed stream is an I/O error*/
        reader->setpos(reader, pos);
        br_etry(reader);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        subreader = reader->substream(reader, 1);
        subreader->close(subreader);
        assert(0);
    } else {
        br_etry(reader);
    }

    pos->del(pos);
}

void test_try(BitstreamReader* reader,
              br_huffman_table_t table[]) {
    uint8_t bytes[2];
    BitstreamReader* substream;
    br_pos_t* pos1;
    br_pos_t* pos2;

    pos1 = reader->getpos(reader);

    /*bounce to the very end of the stream*/
    reader->skip(reader, 31);
    pos2 = reader->getpos(reader);
    assert(reader->read(reader, 1) == 1);
    reader->setpos(reader, pos2);

    /*then test all the read methods to ensure they trigger br_abort

      in the case of unary/Huffman, the stream ends on a "1" bit
      whether reading it big-endian or little-endian*/

    if (!setjmp(*br_try(reader))) {
        reader->read(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_64(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_signed(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_signed_64(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->skip(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->skip_bytes(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_unary(reader, 0);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        assert(reader->read_unary(reader, 1) == 0);
        reader->read_unary(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_huffman_code(reader, table);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_bytes(reader, bytes, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }
    if (!setjmp(*br_try(reader))) {
        substream = reader->substream(reader, 2);
        substream->close(substream);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }

    /*ensure substream_append doesn't use all the RAM in the world
      on a failed read which is very large*/
    if (!setjmp(*br_try(reader))) {
        substream = reader->substream(reader, 4294967295);
        substream->close(substream);
        assert(0);
    } else {
        br_etry(reader);
        reader->setpos(reader, pos2);
    }

    pos2->del(pos2);

    reader->setpos(reader, pos1);
    pos1->del(pos1);
}

void test_callbacks_reader(BitstreamReader* reader,
                           int unary_0_reads,
                           int unary_1_reads,
                           br_huffman_table_t table[],
                           int huffman_code_count) {
    int i;
    unsigned int byte_count;
    uint8_t bytes[2];
    struct bs_callback saved_callback;
    br_pos_t* pos;

    pos = reader->getpos(reader);
    reader->add_callback(reader, (bs_callback_f)byte_counter, &byte_count);

    /*a single callback*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->read(reader, 4);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*calling callbacks directly*/
    byte_count = 0;
    for (i = 0; i < 20; i++)
        reader->call_callbacks(reader, 0);
    assert(byte_count == 20);

    /*two callbacks*/
    byte_count = 0;
    reader->add_callback(reader, (bs_callback_f)byte_counter, &byte_count);
    for (i = 0; i < 8; i++)
        reader->read(reader, 4);
    assert(byte_count == 8);
    reader->pop_callback(reader, NULL);
    reader->setpos(reader, pos);

    /*temporarily suspending the callback*/
    byte_count = 0;
    reader->read(reader, 8);
    assert(byte_count == 1);
    reader->pop_callback(reader, &saved_callback);
    reader->read(reader, 8);
    reader->read(reader, 8);
    reader->push_callback(reader, &saved_callback);
    reader->read(reader, 8);
    assert(byte_count == 2);
    reader->setpos(reader, pos);

    /*temporarily adding two callbacks*/
    byte_count = 0;
    reader->read(reader, 8);
    assert(byte_count == 1);
    reader->add_callback(reader, (bs_callback_f)byte_counter, &byte_count);
    reader->read(reader, 8);
    reader->read(reader, 8);
    reader->pop_callback(reader, NULL);
    reader->read(reader, 8);
    assert(byte_count == 6);
    reader->setpos(reader, pos);

    /*read_signed*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->read_signed(reader, 4);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*read_64*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->read_64(reader, 4);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*skip*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->skip(reader, 4);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*skip_bytes*/
    byte_count = 0;
    for (i = 0; i < 2; i++)
        reader->skip_bytes(reader, 2);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*read_unary*/
    byte_count = 0;
    for (i = 0; i < unary_0_reads; i++)
        reader->read_unary(reader, 0);
    assert(byte_count == 4);
    byte_count = 0;
    reader->setpos(reader, pos);
    for (i = 0; i < unary_1_reads; i++)
        reader->read_unary(reader, 1);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*read_huffman_code*/
    byte_count = 0;
    for (i = 0; i < huffman_code_count; i++)
        reader->read_huffman_code(reader, table);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    /*read_bytes*/
    byte_count = 0;
    reader->read_bytes(reader, bytes, 2);
    reader->read_bytes(reader, bytes, 2);
    assert(byte_count == 4);
    reader->setpos(reader, pos);

    reader->pop_callback(reader, NULL);
    pos->del(pos);
}

void
test_writer(bs_endianness endianness) {
    FILE* output_file;
    BitstreamWriter* writer;
    BitstreamRecorder* sub_writer;
    BitstreamRecorder* sub_sub_writer;

    int i;
    write_check checks[] = {writer_perform_write,
                            writer_perform_write_signed,
                            writer_perform_write_64,
                            writer_perform_write_signed_64,
                            writer_perform_write_bigint,
                            writer_perform_write_signed_bigint,
                            writer_perform_write_unary_0,
                            writer_perform_write_unary_1,
                            writer_perform_huffman,
                            writer_perform_write_bytes,
                            writer_perform_build_u,
                            writer_perform_build_U,
                            writer_perform_build_s,
                            writer_perform_build_S,
                            writer_perform_build_K,
                            writer_perform_build_L,
                            writer_perform_build_b,
                            writer_perform_build_mult};
    int total_checks = 14;

    align_check achecks_be[] = {{0, 0, 0, 0},
                                {1, 1, 1, 0x80},
                                {2, 1, 1, 0x40},
                                {3, 1, 1, 0x20},
                                {4, 1, 1, 0x10},
                                {5, 1, 1, 0x08},
                                {6, 1, 1, 0x04},
                                {7, 1, 1, 0x02},
                                {8, 1, 1, 0x01},
                                {9, 1, 2, 0x0080},
                                {10, 1, 2, 0x0040},
                                {11, 1, 2, 0x0020},
                                {12, 1, 2, 0x0010},
                                {13, 1, 2, 0x0008},
                                {14, 1, 2, 0x0004},
                                {15, 1, 2, 0x0002},
                                {16, 1, 2, 0x0001}};
    align_check achecks_le[] = {{0, 0, 0, 0},
                                {1, 0x01, 1, 0x01},
                                {2, 0x02, 1, 0x02},
                                {3, 0x04, 1, 0x04},
                                {4, 0x08, 1, 0x08},
                                {5, 0x10, 1, 0x10},
                                {6, 0x20, 1, 0x20},
                                {7, 0x40, 1, 0x40},
                                {8, 0x80, 1, 0x80},
                                {9, 0x0100, 2, 0x0100},
                                {10, 0x0200, 2, 0x0200},
                                {11, 0x0400, 2, 0x0400},
                                {12, 0x0800, 2, 0x0800},
                                {13, 0x1000, 2, 0x1000},
                                {14, 0x2000, 2, 0x2000},
                                {15, 0x4000, 2, 0x4000},
                                {16, 0x8000, 2, 0x8000}};
    int total_achecks = 17;
    unsigned sums[3];

    /*perform file-based checks*/
    for (i = 0; i < total_checks; i++) {
        output_file = fopen(temp_filename, "wb");
        assert(output_file != NULL);
        writer = bw_open(output_file, endianness);
        checks[i](writer, endianness);
        fflush(output_file);
        check_output_file();
        writer->free(writer);
        fclose(output_file);
    }

    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    test_writer_close_errors(writer);
    writer->set_endianness(writer, endianness == BS_BIG_ENDIAN ?
                           BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    test_writer_close_errors(writer);
    writer->free(writer);

    /*perform external function-based checks*/
    for (i = 0; i < total_checks; i++) {
        output_file = fopen(temp_filename, "wb");
        assert(output_file != NULL);
        writer = bw_open_external(output_file,
                                  endianness,
                                  2,
                                  (ext_write_f)ext_fwrite_test,
                                  (ext_setpos_f)ext_fsetpos_test,
                                  (ext_getpos_f)ext_fgetpos_test,
                                  (ext_free_pos_f)ext_free_pos_test,
                                  (ext_flush_f)ext_fflush_test,
                                  (ext_close_f)ext_fclose_test,
                                  (ext_free_f)ext_ffree_test);
        checks[i](writer, endianness);
        writer->flush(writer);
        check_output_file();
        writer->free(writer);
        fclose(output_file);
    }

    output_file = fopen(temp_filename, "wb");
    writer = bw_open_external(output_file,
                              endianness,
                              2,
                              (ext_write_f)ext_fwrite_test,
                              (ext_setpos_f)ext_fsetpos_test,
                              (ext_getpos_f)ext_fgetpos_test,
                              (ext_free_pos_f)ext_free_pos_test,
                              (ext_flush_f)ext_fflush_test,
                              (ext_close_f)ext_fclose_test,
                              (ext_free_f)ext_ffree_test);
    test_writer_close_errors(writer);
    writer->set_endianness(writer, endianness == BS_BIG_ENDIAN ?
                           BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    test_writer_close_errors(writer);
    writer->free(writer);

    /*perform recorder-based checks*/
    for (i = 0; i < total_checks; i++) {
        output_file = fopen(temp_filename, "wb");
        assert(output_file != NULL);
        writer = bw_open(output_file, endianness);
        sub_writer = bw_open_recorder(endianness);
        assert(sub_writer->bits_written(sub_writer) == 0);
        checks[i]((BitstreamWriter*)sub_writer, endianness);
        sub_writer->copy(sub_writer, writer);
        fflush(output_file);
        check_output_file();
        writer->free(writer);
        assert(sub_writer->bits_written(sub_writer) == 32);
        sub_writer->close(sub_writer);
        fclose(output_file);
    }

    /*perform partial recorder dumps*/
    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    sub_writer = bw_open_recorder(endianness);
    test_rec_copy_dumps(endianness, writer, sub_writer);
    fflush(output_file);
    check_output_file();
    sub_writer->close(sub_writer);
    writer->close(writer);

    sub_writer = bw_open_recorder(endianness);
    test_recorder_close_errors(sub_writer);
    sub_writer->set_endianness((BitstreamWriter*)sub_writer,
                               endianness == BS_BIG_ENDIAN ?
                               BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    test_recorder_close_errors(sub_writer);
    sub_writer->free(sub_writer);

    /*check recorder reset*/
    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    sub_writer = bw_open_recorder(endianness);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xAA);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xBB);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xCC);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xDD);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xEE);
    sub_writer->reset(sub_writer);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xB1);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xED);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0x3B);
    sub_writer->write((BitstreamWriter*)sub_writer, 8, 0xC1);
    sub_writer->copy(sub_writer, writer);
    fflush(output_file);
    sub_writer->close(sub_writer);
    writer->close(writer);
    check_output_file();


    /*check endianness setting*/
    /*FIXME*/

    /*check a file-based byte-align*/
    for (i = 0; i < total_achecks; i++) {
        if (endianness == BS_BIG_ENDIAN) {
            check_alignment_f(&(achecks_be[i]), endianness);
        } else if (endianness == BS_LITTLE_ENDIAN) {
            check_alignment_f(&(achecks_le[i]), endianness);
        }
    }

    /*check a recoder-based byte-align*/
    for (i = 0; i < total_achecks; i++) {
        if (endianness == BS_BIG_ENDIAN) {
            check_alignment_r(&(achecks_be[i]), endianness);
        } else if (endianness == BS_LITTLE_ENDIAN) {
            check_alignment_r(&(achecks_le[i]), endianness);
        }
    }

    /*check an external function-based byte-align*/
    for (i = 0; i < total_achecks; i++) {
        if (endianness == BS_BIG_ENDIAN) {
            check_alignment_e(&(achecks_be[i]), endianness);
        } else if (endianness == BS_LITTLE_ENDIAN) {
            check_alignment_e(&(achecks_le[i]), endianness);
        }
    }

    /*check file-based callback functions*/
    for (i = 0; i < total_checks; i++) {
        sums[0] = sums[1] = 0;
        sums[2] = 1;
        output_file = fopen(temp_filename, "wb");
        writer = bw_open(output_file, endianness);
        writer->add_callback(writer, (bs_callback_f)func_add_one, &(sums[0]));
        writer->add_callback(writer, (bs_callback_f)func_add_two, &(sums[1]));
        writer->add_callback(writer, (bs_callback_f)func_mult_three, &(sums[2]));
        checks[i](writer, endianness);
        writer->close(writer);
        assert(sums[0] == 4);
        assert(sums[1] == 8);
        assert(sums[2] == 81);
    }

    /*check recorder-based callback functions*/
    for (i = 0; i < total_checks; i++) {
        BitstreamRecorder *recorder;
        sums[0] = sums[1] = 0;
        sums[2] = 1;
        recorder = bw_open_recorder(endianness);
        recorder->add_callback((BitstreamWriter*)recorder,
                               (bs_callback_f)func_add_one,
                               &(sums[0]));
        recorder->add_callback((BitstreamWriter*)recorder,
                               (bs_callback_f)func_add_two,
                               &(sums[1]));
        recorder->add_callback((BitstreamWriter*)recorder,
                               (bs_callback_f)func_mult_three,
                               &(sums[2]));
        checks[i]((BitstreamWriter*)recorder, endianness);
        recorder->close(recorder);
        assert(sums[0] == 4);
        assert(sums[1] == 8);
        assert(sums[2] == 81);
    }

    /*check an external function callback functions*/
    for (i = 0; i < total_checks; i++) {
        sums[0] = sums[1] = 0;
        sums[2] = 1;
        output_file = fopen(temp_filename, "wb");
        writer = bw_open_external(output_file,
                                  endianness,
                                  2,
                                  (ext_write_f)ext_fwrite_test,
                                  (ext_setpos_f)ext_fsetpos_test,
                                  (ext_getpos_f)ext_fgetpos_test,
                                  (ext_free_pos_f)ext_free_pos_test,
                                  (ext_flush_f)ext_fflush_test,
                                  (ext_close_f)ext_fclose_test,
                                  (ext_free_f)ext_ffree_test);
        writer->add_callback(writer, (bs_callback_f)func_add_one, &(sums[0]));
        writer->add_callback(writer, (bs_callback_f)func_add_two, &(sums[1]));
        writer->add_callback(writer, (bs_callback_f)func_mult_three, &(sums[2]));
        checks[i](writer, endianness);
        writer->close(writer);
        assert(sums[0] == 4);
        assert(sums[1] == 8);
        assert(sums[2] == 81);
    }

    /*check that recorder->recorder->file works*/
    for (i = 0; i < total_checks; i++) {
        output_file = fopen(temp_filename, "wb");
        assert(output_file != NULL);
        writer = bw_open(output_file, endianness);
        sub_writer = bw_open_recorder(endianness);
        sub_sub_writer = bw_open_recorder(endianness);
        assert(sub_writer->bits_written(sub_writer) == 0);
        assert(sub_writer->bits_written(sub_sub_writer) == 0);
        checks[i]((BitstreamWriter*)sub_sub_writer, endianness);
        assert(sub_writer->bits_written(sub_writer) == 0);
        assert(sub_writer->bits_written(sub_sub_writer) == 32);
        sub_sub_writer->copy(sub_sub_writer, (BitstreamWriter*)sub_writer);
        assert(sub_writer->bits_written(sub_writer) == 32);
        assert(sub_writer->bits_written(sub_sub_writer) == 32);
        sub_writer->copy(sub_writer, writer);
        fflush(output_file);
        check_output_file();
        writer->free(writer);
        sub_writer->close(sub_writer);
        sub_sub_writer->close(sub_sub_writer);
        fclose(output_file);
    }

    /*check that file-based marks work*/
    output_file = fopen(temp_filename, "w+b");
    writer = bw_open(output_file, endianness);
    test_writer_marks(writer);
    writer->free(writer);
    fseek(output_file, 0, 0);
    assert(fgetc(output_file) == 0xFF);
    assert(fgetc(output_file) == 0x00);
    assert(fgetc(output_file) == 0xFF);
    fclose(output_file);

    /*check that function-based marks work*/
    output_file = fopen(temp_filename, "w+b");
    writer = bw_open_external(output_file,
                              endianness,
                              4096,
                              (ext_write_f)ext_fwrite_test,
                              (ext_setpos_f)ext_fsetpos_test,
                              (ext_getpos_f)ext_fgetpos_test,
                              (ext_free_pos_f)ext_free_pos_test,
                              (ext_flush_f)ext_fflush_test,
                              (ext_close_f)ext_fclose_test,
                              (ext_free_f)ext_ffree_test);
    test_writer_marks(writer);
    writer->flush(writer);
    writer->free(writer);
    fseek(output_file, 0, 0);
    assert(fgetc(output_file) == 0xFF);
    assert(fgetc(output_file) == 0x00);
    assert(fgetc(output_file) == 0xFF);
    fclose(output_file);
}

#define TEST_CLOSE_ERRORS(FUNC_NAME, CLASS)    \
void                                           \
FUNC_NAME(CLASS main_writer)                   \
{                                              \
    BitstreamWriter *writer;                   \
    main_writer->close_internal_stream(main_writer); \
    writer = (BitstreamWriter*)main_writer;    \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->write(writer, 2, 1);           \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->write_signed(writer, 3, 1);    \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->write_64(writer, 4, 1);        \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->write_signed_64(writer, 5, 1); \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->write_bytes(writer, (uint8_t*)"abcde", 5); \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->write_unary(writer, 0, 5);     \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    if (!setjmp(*bw_try(writer))) {            \
        writer->build(writer, "1u", 1);        \
        assert(0);                             \
    } else {                                   \
        bw_etry(writer);                       \
    }                                          \
                                               \
    writer->flush(writer);                     \
}
TEST_CLOSE_ERRORS(test_writer_close_errors, BitstreamWriter*)
TEST_CLOSE_ERRORS(test_recorder_close_errors, BitstreamRecorder*)

void
writer_perform_write(BitstreamWriter* writer, bs_endianness endianness) {
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write(writer, 2, 2);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 3, 6);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 5, 7);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 3, 5);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 19, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write(writer, 2, 1);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 3, 4);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 5, 13);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 3, 3);
        assert(writer->byte_aligned(writer) == 0);
        writer->write(writer, 19, 395743);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_write_signed(BitstreamWriter* writer, bs_endianness endianness) {
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_signed(writer, 2, -2);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 3, -2);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 5, 7);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 3, -3);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 19, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_signed(writer, 2, 1);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 3, -4);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 5, 13);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 3, 3);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed(writer, 19, -128545);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_write_64(BitstreamWriter* writer, bs_endianness endianness) {
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_64(writer, 2, 2);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 3, 6);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 5, 7);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 3, 5);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 19, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_64(writer, 2, 1);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 3, 4);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 5, 13);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 3, 3);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_64(writer, 19, 395743);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_write_signed_64(BitstreamWriter* writer,
                               bs_endianness endianness)
{
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_signed_64(writer, 2, -2);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 3, -2);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 5, 7);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 3, -3);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 19, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_signed_64(writer, 2, 1);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 3, -4);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 5, 13);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 3, 3);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_signed_64(writer, 19, -128545);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_write_bigint(BitstreamWriter* writer, bs_endianness endianness)
{
    mpz_t value;
    mpz_init(value);
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        mpz_set_ui(value, 2);
        writer->write_bigint(writer, 2, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 6);
        writer->write_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 7);
        writer->write_bigint(writer, 5, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 5);
        writer->write_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 342977);
        writer->write_bigint(writer, 19, value);
        break;
    case BS_LITTLE_ENDIAN:
        mpz_set_ui(value, 1);
        writer->write_bigint(writer, 2, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 4);
        writer->write_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 13);
        writer->write_bigint(writer, 5, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 3);
        writer->write_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_ui(value, 395743);
        writer->write_bigint(writer, 19, value);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
    mpz_clear(value);
}

void
writer_perform_write_signed_bigint(BitstreamWriter* writer,
                                   bs_endianness endianness)
{
    mpz_t value;
    mpz_init(value);

    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        mpz_set_si(value, -2);
        writer->write_signed_bigint(writer, 2, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, -2);
        writer->write_signed_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, 7);
        writer->write_signed_bigint(writer, 5, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, -3);
        writer->write_signed_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, -181311);
        writer->write_signed_bigint(writer, 19, value);
        break;
    case BS_LITTLE_ENDIAN:
        mpz_set_si(value, 1);
        writer->write_signed_bigint(writer, 2, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, -4);
        writer->write_signed_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, 13);
        writer->write_signed_bigint(writer, 5, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, 3);
        writer->write_signed_bigint(writer, 3, value);
        assert(writer->byte_aligned(writer) == 0);
        mpz_set_si(value, -128545);
        writer->write_signed_bigint(writer, 19, value);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);

    mpz_clear(value);
}

void
writer_perform_write_unary_0(BitstreamWriter* writer,
                             bs_endianness endianness) {
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_unary(writer, 0, 1);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_unary(writer, 0, 2);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 4);
        writer->write_unary(writer, 0, 2);
        writer->write_unary(writer, 0, 1);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 3);
        writer->write_unary(writer, 0, 4);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write(writer, 1, 1);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_unary(writer, 0, 1);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 2);
        writer->write_unary(writer, 0, 2);
        writer->write_unary(writer, 0, 2);
        writer->write_unary(writer, 0, 5);
        writer->write_unary(writer, 0, 3);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 1);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write_unary(writer, 0, 0);
        writer->write(writer, 2, 3);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_write_unary_1(BitstreamWriter* writer,
                             bs_endianness endianness) {
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_unary(writer, 1, 0);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 3);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 2);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 5);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_unary(writer, 1, 0);
        assert(writer->byte_aligned(writer) == 0);
        writer->write_unary(writer, 1, 3);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 1);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 0);
        writer->write_unary(writer, 1, 2);
        writer->write_unary(writer, 1, 5);
        writer->write_unary(writer, 1, 0);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_build_u(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->build(writer, "2u 3u 5u 3u 19u", 2, 6, 7, 5, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        writer->build(writer, "2u 3u 5u 3u 19u", 1, 4, 13, 3, 395743);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_build_U(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    const uint64_t v1 = (endianness == BS_BIG_ENDIAN) ? 2 : 1;
    const uint64_t v2 = (endianness == BS_BIG_ENDIAN) ? 6 : 4;
    const uint64_t v3 = (endianness == BS_BIG_ENDIAN) ? 7 : 13;
    const uint64_t v4 = (endianness == BS_BIG_ENDIAN) ? 5 : 3;
    const uint64_t v5 = (endianness == BS_BIG_ENDIAN) ? 342977 : 395743;

    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2U 3U 5U 3U 19U", v1, v2, v3, v4, v5);
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_build_K(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    mpz_t B1,B2,B3,B4,B5;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        mpz_init_set_ui(B1, 2);
        mpz_init_set_ui(B2, 6);
        mpz_init_set_ui(B3, 7);
        mpz_init_set_ui(B4, 5);
        mpz_init_set_ui(B5, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        mpz_init_set_ui(B1, 1);
        mpz_init_set_ui(B2, 4);
        mpz_init_set_ui(B3, 13);
        mpz_init_set_ui(B4, 3);
        mpz_init_set_ui(B5, 395743);
        break;
    }

    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2K 3K 5K 3K 19K", &B1, &B2, &B3, &B4, &B5);
    assert(writer->byte_aligned(writer) == 1);

    mpz_clear(B1);
    mpz_clear(B2);
    mpz_clear(B3);
    mpz_clear(B4);
    mpz_clear(B5);
}

void
writer_perform_build_s(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->build(writer, "2s 3s 5s 3s 19s", -2, -2, 7, -3, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        writer->build(writer, "2s 3s 5s 3s 19s", 1, -4, 13, 3, -128545);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_build_S(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    const int64_t v1 = (endianness == BS_BIG_ENDIAN) ? -2 : 1;
    const int64_t v2 = (endianness == BS_BIG_ENDIAN) ? -2 : -4;
    const int64_t v3 = (endianness == BS_BIG_ENDIAN) ? 7 : 13;
    const int64_t v4 = (endianness == BS_BIG_ENDIAN) ? -3 : 3;
    const int64_t v5 = (endianness == BS_BIG_ENDIAN) ? -181311 : -128545;

    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2S 3S 5S 3S 19S", v1, v2, v3, v4, v5);
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_build_L(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    mpz_t B1,B2,B3,B4,B5;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        mpz_init_set_si(B1, -2);
        mpz_init_set_si(B2, -2);
        mpz_init_set_si(B3, 7);
        mpz_init_set_si(B4, -3);
        mpz_init_set_si(B5, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        mpz_init_set_si(B1, 1);
        mpz_init_set_si(B2, -4);
        mpz_init_set_si(B3, 13);
        mpz_init_set_si(B4, 3);
        mpz_init_set_si(B5, -128545);
        break;
    }

    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2L 3L 5L 3L 19L", &B1, &B2, &B3, &B4, &B5);
    assert(writer->byte_aligned(writer) == 1);

    mpz_clear(B1);
    mpz_clear(B2);
    mpz_clear(B3);
    mpz_clear(B4);
    mpz_clear(B5);
}

void
writer_perform_build_b(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2b 2b", (uint8_t*)"\xB1\xED", (uint8_t*)"\x3B\xC1");
    assert(writer->byte_aligned(writer) == 1);
}

void
writer_perform_build_mult(BitstreamWriter* writer,
                          bs_endianness endianness)
{
    assert(writer->byte_aligned(writer) == 1);
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->build(writer, "8* 4u", 11, 1, 14, 13, 3, 11, 12, 1);
        break;
    case BS_LITTLE_ENDIAN:
        writer->build(writer, "8* 4u", 1, 11, 13, 14, 11, 3, 1, 12);
        break;
    }
    assert(writer->byte_aligned(writer) == 1);
}


void
writer_perform_huffman(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    bw_huffman_table_t* table;
    struct huffman_frequency frequencies[] =
        {bw_str_to_frequency("11", 0),
         bw_str_to_frequency("10", 1),
         bw_str_to_frequency("01", 2),
         bw_str_to_frequency("001", 3),
         bw_str_to_frequency("000", 4)};
    const unsigned int total_frequencies = 5;

    assert(compile_bw_huffman_table(&table,
                                    frequencies,
                                    total_frequencies,
                                    endianness) == 0);

    switch (endianness) {
    case BS_BIG_ENDIAN:
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 4) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 2) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 2) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 2) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 4) == 0);
        assert(writer->write_huffman_code(writer, table, 2) == 0);
        break;
    case BS_LITTLE_ENDIAN:
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 3) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 2) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 0) == 0);
        assert(writer->write_huffman_code(writer, table, 1) == 0);
        assert(writer->write_huffman_code(writer, table, 2) == 0);
        assert(writer->write_huffman_code(writer, table, 4) == 0);
        assert(writer->write_huffman_code(writer, table, 3) == 0);
        /*table makes us unable to generate single
          trailing 1 bit, so we have to do it manually*/
        writer->write(writer, 1, 1);
        break;
    }

    free(table);
}


void
writer_perform_write_bytes(BitstreamWriter* writer,
                           bs_endianness endianness)
{
    writer->write_bytes(writer, (uint8_t*)"\xB1\xED\x3B\xC1", 4);
}

void
check_output_file(void) {
    FILE* output_file;
    uint8_t data[255];
    uint8_t expected_data[] = {0xB1, 0xED, 0x3B, 0xC1};

    output_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 255, output_file) == 4);
    assert(memcmp(data, expected_data, 4) == 0);

    fclose(output_file);
}

void check_alignment_f(const align_check* check,
                       bs_endianness endianness)
{
    FILE* f = fopen(temp_filename, "wb");
    BitstreamWriter* bw = bw_open(f, endianness);
    BitstreamReader* br;
    struct stat s;

    bw->write(bw, check->bits, check->value);
    bw->byte_align(bw);
    bw->close(bw);

    assert(stat(temp_filename, &s) == 0);
    assert(s.st_size == check->resulting_bytes);

    f = fopen(temp_filename, "rb");
    br = br_open(f, endianness);
    assert(br->read(br, check->resulting_bytes * 8) == check->resulting_value);
    br->close(br);
}

void check_alignment_r(const align_check* check,
                       bs_endianness endianness)
{
    FILE* f = fopen(temp_filename, "wb");
    BitstreamRecorder* rec = bw_open_recorder(endianness);
    BitstreamWriter* bw = bw_open(f, endianness);
    BitstreamReader* br;
    struct stat s;

    rec->write((BitstreamWriter*)rec, check->bits, check->value);
    rec->byte_align((BitstreamWriter*)rec);
    rec->copy(rec, bw);
    rec->close(rec);
    bw->close(bw);

    assert(stat(temp_filename, &s) == 0);
    assert(s.st_size == check->resulting_bytes);

    f = fopen(temp_filename, "rb");
    br = br_open(f, endianness);
    assert(br->read(br, check->resulting_bytes * 8) == check->resulting_value);
    br->close(br);
}


void check_alignment_e(const align_check* check,
                       bs_endianness endianness)
{
    FILE* f = fopen(temp_filename, "wb");
    BitstreamWriter* bw = bw_open_external(
        f,
        endianness,
        4096,
        (ext_write_f)ext_fwrite_test,
        (ext_setpos_f)ext_fsetpos_test,
        (ext_getpos_f)ext_fgetpos_test,
        (ext_free_pos_f)ext_free_pos_test,
        (ext_flush_f)ext_fflush_test,
        (ext_close_f)ext_fclose_test,
        (ext_free_f)ext_ffree_test);
    BitstreamReader* br;
    struct stat s;

    bw->write(bw, check->bits, check->value);
    bw->byte_align(bw);
    bw->close(bw);

    assert(stat(temp_filename, &s) == 0);
    assert(s.st_size == check->resulting_bytes);

    f = fopen(temp_filename, "rb");
    br = br_open(f, endianness);
    assert(br->read(br, check->resulting_bytes * 8) == check->resulting_value);
    br->close(br);
}

void test_edge_cases(void) {
    const static uint8_t big_endian[] =
        {0, 0, 0, 0, 255, 255, 255, 255,
         128, 0, 0, 0, 127, 255, 255, 255,
         0, 0, 0, 0, 0, 0, 0, 0,
         255, 255, 255, 255, 255, 255, 255, 255,
         128, 0, 0, 0, 0, 0, 0, 0,
         127, 255, 255, 255, 255, 255, 255, 255};
    const static uint8_t little_endian[] =
        {0, 0, 0, 0, 255, 255, 255, 255,
         0, 0, 0, 128, 255, 255, 255, 127,
         0, 0, 0, 0, 0, 0, 0, 0,
         255, 255, 255, 255, 255, 255, 255, 255,
         0, 0, 0, 0, 0, 0, 0, 128,
         255, 255, 255, 255, 255, 255, 255, 127};

    FILE* output_file;
    BitstreamReader* reader;
    BitstreamReader* sub_reader;

    /*write the temp file with a collection of known big-endian test bytes*/
    output_file = fopen(temp_filename, "wb");
    assert(fwrite(big_endian, sizeof(uint8_t), 48, output_file) == 48);
    fclose(output_file);

    /*ensure a big-endian reader reads the values correctly*/
    reader = br_open(fopen(temp_filename, "rb"), BS_BIG_ENDIAN);
    test_edge_reader_be(reader);
    reader->close(reader);

    /*ensure a big-endian sub-reader reads the values correctly*/
    reader = br_open(fopen(temp_filename, "rb"), BS_BIG_ENDIAN);
    sub_reader = reader->substream(reader, 48);
    test_edge_reader_be(sub_reader);
    sub_reader->close(sub_reader);
    reader->close(reader);

    /*write the temp file with a collection of known little-endian test bytes*/
    output_file = fopen(temp_filename, "wb");
    assert(fwrite(little_endian, sizeof(uint8_t), 48, output_file) == 48);
    fclose(output_file);

    /*ensure a little-endian reader reads the values correctly*/
    reader = br_open(fopen(temp_filename, "rb"), BS_LITTLE_ENDIAN);
    test_edge_reader_le(reader);
    reader->close(reader);

    /*ensure a little-endian sub-reader reads the values correctly*/
    reader = br_open(fopen(temp_filename, "rb"), BS_LITTLE_ENDIAN);
    sub_reader = reader->substream(reader, 48);
    test_edge_reader_le(sub_reader);
    sub_reader->close(sub_reader);
    reader->close(reader);

    /*test a bunch of known big-endian values via the bitstream writer*/
    test_edge_writer(get_edge_writer_be, validate_edge_writer_be);

    /*test a bunch of known big-endian values via the bitstream recorder*/
    test_edge_recorder(get_edge_recorder_be, validate_edge_recorder_be);

    /*test a bunch of known little-endian values via the bitstream writer*/
    test_edge_writer(get_edge_writer_le, validate_edge_writer_le);

    /*test a bunch of known little-endian values via the bitstream recorder*/
    test_edge_recorder(get_edge_recorder_le, validate_edge_recorder_le);
}

void
test_edge_reader_be(BitstreamReader* reader)
{
    unsigned int u_val_1;
    unsigned int u_val_2;
    unsigned int u_val_3;
    unsigned int u_val_4;
    int s_val_1;
    int s_val_2;
    int s_val_3;
    int s_val_4;
    uint64_t u_val64_1;
    uint64_t u_val64_2;
    uint64_t u_val64_3;
    uint64_t u_val64_4;
    int64_t s_val64_1;
    int64_t s_val64_2;
    int64_t s_val64_3;
    int64_t s_val64_4;
    br_pos_t* pos;

    pos = reader->getpos(reader);

    /*try the unsigned 32 and 64 bit values*/
    reader->setpos(reader, pos);
    assert(reader->read(reader, 32) == 0);
    assert(reader->read(reader, 32) == 4294967295UL);
    assert(reader->read(reader, 32) == 2147483648UL);
    assert(reader->read(reader, 32) == 2147483647UL);
    assert(reader->read_64(reader, 64) == 0);
    assert(reader->read_64(reader, 64) == 0xFFFFFFFFFFFFFFFFULL);
    assert(reader->read_64(reader, 64) == 9223372036854775808ULL);
    assert(reader->read_64(reader, 64) == 9223372036854775807ULL);

    /*try the signed 32 and 64 bit values*/
    reader->setpos(reader, pos);
    assert(reader->read_signed(reader, 32) == 0);
    assert(reader->read_signed(reader, 32) == -1);
    assert(reader->read_signed(reader, 32) == -2147483648LL);
    assert(reader->read_signed(reader, 32) == 2147483647LL);
    assert(reader->read_signed_64(reader, 64) == 0);
    assert(reader->read_signed_64(reader, 64) == -1);
    assert(reader->read_signed_64(reader, 64) == (9223372036854775808ULL * -1));
    assert(reader->read_signed_64(reader, 64) == 9223372036854775807LL);

    /*try the unsigned values via parse()*/
    reader->setpos(reader, pos);
    reader->parse(reader,
                  "32u 32u 32u 32u 64U 64U 64U 64U",
                  &u_val_1, &u_val_2, &u_val_3, &u_val_4,
                  &u_val64_1, &u_val64_2, &u_val64_3, &u_val64_4);
    assert(u_val_1 == 0);
    assert(u_val_2 == 4294967295UL);
    assert(u_val_3 == 2147483648UL);
    assert(u_val_4 == 2147483647UL);
    assert(u_val64_1 == 0);
    assert(u_val64_2 == 0xFFFFFFFFFFFFFFFFULL);
    assert(u_val64_3 == 9223372036854775808ULL);
    assert(u_val64_4 == 9223372036854775807ULL);

    /*try the signed values via parse()*/
    reader->setpos(reader, pos);
    reader->parse(reader,
                  "32s 32s 32s 32s 64S 64S 64S 64S",
                  &s_val_1, &s_val_2, &s_val_3, &s_val_4,
                  &s_val64_1, &s_val64_2, &s_val64_3, &s_val64_4);
    assert(s_val_1 == 0);
    assert(s_val_2 == -1);
    assert(s_val_3 == -2147483648LL);
    assert(s_val_4 == 2147483647LL);
    assert(s_val64_1 == 0);
    assert(s_val64_2 == -1);
    assert(s_val64_3 == (9223372036854775808ULL * -1));
    assert(s_val64_4 == 9223372036854775807LL);

    pos->del(pos);
}

void
test_edge_reader_le(BitstreamReader* reader)
{
    unsigned int u_val_1;
    unsigned int u_val_2;
    unsigned int u_val_3;
    unsigned int u_val_4;
    int s_val_1;
    int s_val_2;
    int s_val_3;
    int s_val_4;
    uint64_t u_val64_1;
    uint64_t u_val64_2;
    uint64_t u_val64_3;
    uint64_t u_val64_4;
    int64_t s_val64_1;
    int64_t s_val64_2;
    int64_t s_val64_3;
    int64_t s_val64_4;
    br_pos_t* pos;

    pos = reader->getpos(reader);

    /*try the unsigned 32 and 64 bit values*/
    assert(reader->read(reader, 32) == 0);
    assert(reader->read(reader, 32) == 4294967295UL);
    assert(reader->read(reader, 32) == 2147483648UL);
    assert(reader->read(reader, 32) == 2147483647UL);
    assert(reader->read_64(reader, 64) == 0);
    assert(reader->read_64(reader, 64) == 0xFFFFFFFFFFFFFFFFULL);
    assert(reader->read_64(reader, 64) == 9223372036854775808ULL);
    assert(reader->read_64(reader, 64) == 9223372036854775807ULL);

    /*try the signed 32 and 64 bit values*/
    reader->setpos(reader, pos);
    assert(reader->read_signed(reader, 32) == 0);
    assert(reader->read_signed(reader, 32) == -1);
    assert(reader->read_signed(reader, 32) == -2147483648LL);
    assert(reader->read_signed(reader, 32) == 2147483647LL);
    assert(reader->read_signed_64(reader, 64) == 0);
    assert(reader->read_signed_64(reader, 64) == -1);
    assert(reader->read_signed_64(reader, 64) == (9223372036854775808ULL * -1));
    assert(reader->read_signed_64(reader, 64) == 9223372036854775807LL);

    /*try the unsigned values via parse()*/
    reader->setpos(reader, pos);
    reader->parse(reader,
                  "32u 32u 32u 32u 64U 64U 64U 64U",
                  &u_val_1, &u_val_2, &u_val_3, &u_val_4,
                  &u_val64_1, &u_val64_2, &u_val64_3, &u_val64_4);
    assert(u_val_1 == 0);
    assert(u_val_2 == 4294967295UL);
    assert(u_val_3 == 2147483648UL);
    assert(u_val_4 == 2147483647UL);
    assert(u_val64_1 == 0);
    assert(u_val64_2 == 0xFFFFFFFFFFFFFFFFULL);
    assert(u_val64_3 == 9223372036854775808ULL);
    assert(u_val64_4 == 9223372036854775807ULL);

    /*try the signed values via parse()*/
    reader->setpos(reader, pos);
    reader->parse(reader,
                  "32s 32s 32s 32s 64S 64S 64S 64S",
                  &s_val_1, &s_val_2, &s_val_3, &s_val_4,
                  &s_val64_1, &s_val64_2, &s_val64_3, &s_val64_4);
    assert(s_val_1 == 0);
    assert(s_val_2 == -1);
    assert(s_val_3 == -2147483648LL);
    assert(s_val_4 == 2147483647LL);
    assert(s_val64_1 == 0);
    assert(s_val64_2 == -1);
    assert(s_val64_3 == (9223372036854775808ULL * -1));
    assert(s_val64_4 == 9223372036854775807LL);

    pos->del(pos);
}

#define TEST_WRITER(FUNC_NAME, CLASS)                                   \
void                                                                    \
FUNC_NAME(CLASS (*get_writer)(void),                                    \
                 void (*validate_writer)(CLASS))                        \
{                                                                       \
    CLASS writer;                                                       \
                                                                        \
    unsigned int u_val_1;                                               \
    unsigned int u_val_2;                                               \
    unsigned int u_val_3;                                               \
    unsigned int u_val_4;                                               \
    int s_val_1;                                                        \
    int s_val_2;                                                        \
    int s_val_3;                                                        \
    int s_val_4;                                                        \
    uint64_t u_val64_1;                                                 \
    uint64_t u_val64_2;                                                 \
    uint64_t u_val64_3;                                                 \
    uint64_t u_val64_4;                                                 \
    int64_t s_val64_1;                                                  \
    int64_t s_val64_2;                                                  \
    int64_t s_val64_3;                                                  \
    int64_t s_val64_4;                                                  \
                                                                        \
    /*try the unsigned 32 and 64 bit values*/                           \
    writer = get_writer();                                              \
    writer->write((BitstreamWriter*)writer, 32, 0);                     \
    writer->write((BitstreamWriter*)writer, 32, 4294967295UL);          \
    writer->write((BitstreamWriter*)writer, 32, 2147483648UL);          \
    writer->write((BitstreamWriter*)writer, 32, 2147483647UL);          \
    writer->write_64((BitstreamWriter*)writer, 64, 0);                  \
    writer->write_64((BitstreamWriter*)writer,                          \
                     64, 0xFFFFFFFFFFFFFFFFULL);                        \
    writer->write_64((BitstreamWriter*)writer,                          \
                     64, 9223372036854775808ULL);                       \
    writer->write_64((BitstreamWriter*)writer,                          \
                     64, 9223372036854775807ULL);                       \
    validate_writer(writer);                                            \
                                                                        \
    /*try the signed 32 and 64 bit values*/                             \
    writer = get_writer();                                              \
    writer->write_signed((BitstreamWriter*)writer, 32, 0);              \
    writer->write_signed((BitstreamWriter*)writer, 32, -1);             \
    writer->write_signed((BitstreamWriter*)writer, 32, -2147483648LL);  \
    writer->write_signed((BitstreamWriter*)writer, 32, 2147483647LL);   \
    writer->write_signed_64((BitstreamWriter*)writer, 64, 0);           \
    writer->write_signed_64((BitstreamWriter*)writer, 64, -1);          \
    writer->write_signed_64((BitstreamWriter*)writer,                   \
                            64, (9223372036854775808ULL * -1));         \
    writer->write_signed_64((BitstreamWriter*)writer,                   \
                            64, 9223372036854775807LL);                 \
    validate_writer(writer);                                            \
                                                                        \
    /*try the unsigned values via build()*/                             \
    writer = get_writer();                                              \
    u_val_1 = 0;                                                        \
    u_val_2 = 4294967295UL;                                             \
    u_val_3 = 2147483648UL;                                             \
    u_val_4 = 2147483647UL;                                             \
    u_val64_1 = 0;                                                      \
    u_val64_2 = 0xFFFFFFFFFFFFFFFFULL;                                  \
    u_val64_3 = 9223372036854775808ULL;                                 \
    u_val64_4 = 9223372036854775807ULL;                                 \
    writer->build((BitstreamWriter*)writer,                             \
                  "32u 32u 32u 32u 64U 64U 64U 64U",                    \
                  u_val_1, u_val_2, u_val_3, u_val_4,                   \
                  u_val64_1, u_val64_2, u_val64_3, u_val64_4);          \
    validate_writer(writer);                                            \
                                                                        \
    /*try the signed values via build()*/                               \
    writer = get_writer();                                              \
    s_val_1 = 0;                                                        \
    s_val_2 = -1;                                                       \
    s_val_3 = -2147483648LL;                                            \
    s_val_4 = 2147483647LL;                                             \
    s_val64_1 = 0;                                                      \
    s_val64_2 = -1;                                                     \
    s_val64_3 = (9223372036854775808ULL * -1);                          \
    s_val64_4 = 9223372036854775807LL;                                  \
    writer->build((BitstreamWriter*)writer,                             \
                  "32s 32s 32s 32s 64S 64S 64S 64S",                    \
                  s_val_1, s_val_2, s_val_3, s_val_4,                   \
                  s_val64_1, s_val64_2, s_val64_3, s_val64_4);          \
    validate_writer(writer);                                            \
}
TEST_WRITER(test_edge_writer, BitstreamWriter*)
TEST_WRITER(test_edge_recorder, BitstreamRecorder*)

BitstreamWriter*
get_edge_writer_be(void)
{
    return bw_open(fopen(temp_filename, "wb"), BS_BIG_ENDIAN);
}

BitstreamRecorder*
get_edge_recorder_be(void)
{
    return bw_open_recorder(BS_BIG_ENDIAN);
}

void
validate_edge_writer_be(BitstreamWriter* writer)
{
    const static uint8_t big_endian[] =
        {0, 0, 0, 0, 255, 255, 255, 255,
         128, 0, 0, 0, 127, 255, 255, 255,
         0, 0, 0, 0, 0, 0, 0, 0,
         255, 255, 255, 255, 255, 255, 255, 255,
         128, 0, 0, 0, 0, 0, 0, 0,
         127, 255, 255, 255, 255, 255, 255, 255};
    uint8_t data[48];
    FILE* input_file;

    writer->close(writer);
    input_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 48, input_file) == 48);
    assert(memcmp(data, big_endian, 48) == 0);
    fclose(input_file);
}

void
validate_edge_recorder_be(BitstreamRecorder* recorder)
{
    BitstreamWriter* writer;
    const static uint8_t big_endian[] =
        {0, 0, 0, 0, 255, 255, 255, 255,
         128, 0, 0, 0, 127, 255, 255, 255,
         0, 0, 0, 0, 0, 0, 0, 0,
         255, 255, 255, 255, 255, 255, 255, 255,
         128, 0, 0, 0, 0, 0, 0, 0,
         127, 255, 255, 255, 255, 255, 255, 255};
    uint8_t data[48];
    FILE* input_file;

    assert(recorder->bits_written(recorder) == (48 * 8));

    writer = bw_open(fopen(temp_filename, "wb"), BS_BIG_ENDIAN);
    recorder->copy(recorder, writer);
    recorder->close(recorder);
    writer->close(writer);
    input_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 48, input_file) == 48);
    assert(memcmp(data, big_endian, 48) == 0);
    fclose(input_file);
}


BitstreamWriter*
get_edge_writer_le(void) {
    return bw_open(fopen(temp_filename, "wb"), BS_LITTLE_ENDIAN);
}

BitstreamRecorder*
get_edge_recorder_le(void)
{
    return bw_open_recorder(BS_LITTLE_ENDIAN);
}


void
validate_edge_writer_le(BitstreamWriter* writer) {
    const static uint8_t little_endian[] =
        {0, 0, 0, 0, 255, 255, 255, 255,
         0, 0, 0, 128, 255, 255, 255, 127,
         0, 0, 0, 0, 0, 0, 0, 0,
         255, 255, 255, 255, 255, 255, 255, 255,
         0, 0, 0, 0, 0, 0, 0, 128,
         255, 255, 255, 255, 255, 255, 255, 127};
    uint8_t data[48];
    FILE* input_file;

    writer->close(writer);
    input_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 48, input_file) == 48);
    assert(memcmp(data, little_endian, 48) == 0);
    fclose(input_file);
}

void
validate_edge_recorder_le(BitstreamRecorder* recorder)
{
    BitstreamWriter* writer;
    const static uint8_t little_endian[] =
        {0, 0, 0, 0, 255, 255, 255, 255,
         0, 0, 0, 128, 255, 255, 255, 127,
         0, 0, 0, 0, 0, 0, 0, 0,
         255, 255, 255, 255, 255, 255, 255, 255,
         0, 0, 0, 0, 0, 0, 0, 128,
         255, 255, 255, 255, 255, 255, 255, 127};
    uint8_t data[48];
    FILE* input_file;

    writer = bw_open(fopen(temp_filename, "wb"), BS_LITTLE_ENDIAN);
    recorder->copy(recorder, writer);
    recorder->close(recorder);
    writer->close(writer);
    input_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 48, input_file) == 48);
    assert(memcmp(data, little_endian, 48) == 0);
    fclose(input_file);
}

void
test_rec_copy_dumps(bs_endianness endianness,
                    BitstreamWriter* writer,
                    BitstreamRecorder* recorder)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        recorder->write((BitstreamWriter*)recorder, 2, 2);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 6);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 5, 7);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 5);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 19, 342977);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        break;
    case BS_LITTLE_ENDIAN:
        recorder->write((BitstreamWriter*)recorder, 2, 1);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 4);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 5, 13);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 3);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 19, 395743);
        recorder->copy(recorder, writer);
        recorder->reset(recorder);
        break;
    }
}


unsigned ext_fread_test(FILE* user_data,
                        uint8_t* buffer,
                        unsigned buffer_size)
{
    const size_t read = fread(buffer, sizeof(uint8_t), buffer_size, user_data);
    return (unsigned)read;
}

int ext_fclose_test(FILE* user_data)
{
    return fclose(user_data);
}

void ext_ffree_test(FILE* user_data)
{
    return;
}

int ext_fwrite_test(FILE* user_data,
                    const uint8_t* buffer,
                    unsigned buffer_size)
{
    const size_t written = fwrite(buffer,
                                  sizeof(uint8_t),
                                  buffer_size,
                                  user_data);
    if (written == buffer_size) {
        return 0;
    } else {
        return 1;
    }
}

int ext_fflush_test(FILE* user_data)
{
    return fflush(user_data);
}

int ext_fsetpos_test(FILE *user_data, fpos_t *pos)
{
    if (!fsetpos(user_data, pos)) {
        return 0;
    } else {
        return EOF;
    }
}

fpos_t* ext_fgetpos_test(FILE *user_data)
{
    fpos_t* pos = malloc(sizeof(fpos_t));
    if (!fgetpos(user_data, pos)) {
        return pos;
    } else {
        free(pos);
        return NULL;
    }
}

int ext_fseek_test(FILE *user_data, long location, int whence)
{
    return fseek(user_data, location, whence);
}

void ext_free_pos_test(fpos_t *pos)
{
    free(pos);
}

void func_add_one(uint8_t byte, int* value)
{
    *value += 1;
}

void func_add_two(uint8_t byte, int* value)
{
    *value += 2;
}

void func_mult_three(uint8_t byte, int* value)
{
    *value *= 3;
}

void
test_writer_marks(BitstreamWriter* writer)
{
    bw_pos_t* pos;
    writer->write(writer, 1, 1);
    writer->write(writer, 2, 3);
    writer->write(writer, 3, 7);
    writer->write(writer, 2, 3);
    pos = writer->getpos(writer);
    writer->write(writer, 8, 0xFF);
    writer->write(writer, 8, 0xFF);
    writer->setpos(writer, pos);
    writer->write(writer, 8, 0);
    pos->del(pos);
}
#endif
