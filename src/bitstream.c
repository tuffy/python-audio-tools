#include "bitstream.h"
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

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

const struct read_bits read_bits_table_be[0x200][8] =
#include "read_bits_table_be.h"
    ;

const struct read_bits read_bits_table_le[0x200][8] =
#include "read_bits_table_le.h"
    ;

const struct read_unary read_unary_table_be[0x200][2] =
#include "read_unary_table_be.h"
    ;

const struct read_unary read_unary_table_le[0x200][2] =
#include "read_unary_table_le.h"
    ;


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
        /*bs->set_endianness = ???*/
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
        /*bs->set_endianness = ???*/
        break;
    }

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
        bs->set_endianness = br_set_endianness_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_f_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->read_bigint = br_read_bits_bigint_f_le;
        bs->skip = br_skip_bits_f_le;
        bs->read_unary = br_read_unary_f_le;
        bs->skip_unary = br_skip_unary_f_le;
        bs->set_endianness = br_set_endianness_f_le;
        break;
    }

    bs->read_huffman_code = br_read_huffman_code_f;
    bs->read_bytes = br_read_bytes_f;

    bs->getpos = br_getpos_f;
    bs->setpos = br_setpos_f;
    bs->seek = br_seek_f;


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
        bs->set_endianness = br_set_endianness_b_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_b_le;
        bs->read_64 = br_read_bits64_b_le;
        bs->read_bigint = br_read_bits_bigint_b_le;
        bs->skip = br_skip_bits_b_le;
        bs->read_unary = br_read_unary_b_le;
        bs->skip_unary = br_skip_unary_b_le;
        bs->set_endianness = br_set_endianness_b_le;
        break;
    }

    bs->read_huffman_code = br_read_huffman_code_b;
    bs->read_bytes = br_read_bytes_b;

    bs->getpos = br_getpos_b;
    bs->setpos = br_setpos_b;
    bs->seek = br_seek_b;

    bs->close_internal_stream = br_close_internal_stream_b;
    bs->free = br_free_b;

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
        bs->set_endianness = br_set_endianness_e_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_e_le;
        bs->read_64 = br_read_bits64_e_le;
        bs->read_bigint = br_read_bits_bigint_e_le;
        bs->skip = br_skip_bits_e_le;
        bs->read_unary = br_read_unary_e_le;
        bs->skip_unary = br_skip_unary_e_le;
        bs->set_endianness = br_set_endianness_e_le;
        break;
    }

    bs->read_huffman_code = br_read_huffman_code_e;
    bs->read_bytes = br_read_bytes_e;

    bs->setpos = br_setpos_e;
    bs->getpos = br_getpos_e;
    bs->seek = br_seek_e;

    bs->close_internal_stream = br_close_internal_stream_e;
    bs->free = br_free_e;

    return bs;
}

/*These are helper macros for unpacking the results
  of the various jump tables in a less error-prone fashion.*/
#define NEW_STATE(x) (0x100 | (x))

#define FUNC_READ_BITS_BE(FUNC_NAME, RETURN_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    RETURN_TYPE                                                         \
    FUNC_NAME(BitstreamReader* bs, unsigned int count)                  \
    {                                                                   \
        struct read_bits result = {0, 0, bs->state};                    \
        register RETURN_TYPE accumulator = 0;                           \
                                                                        \
        while (count > 0) {                                             \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = bs->callbacks;                      \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(bs);                                       \
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
        bs->state = result.state;                                       \
        return accumulator;                                             \
    }

#define FUNC_READ_BITS_LE(FUNC_NAME, RETURN_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    RETURN_TYPE                                                         \
    FUNC_NAME(BitstreamReader* bs, unsigned int count)                  \
    {                                                                   \
        struct read_bits result = {0, 0, bs->state};                    \
        register RETURN_TYPE accumulator = 0;                           \
        register unsigned bit_offset = 0;                               \
                                                                        \
        while (count > 0) {                                             \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = bs->callbacks;                      \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(bs);                                       \
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
        bs->state = result.state;                                       \
        return accumulator;                                             \
    }

FUNC_READ_BITS_BE(br_read_bits_f_be,
                  unsigned int, fgetc, bs->input.file)
FUNC_READ_BITS_LE(br_read_bits_f_le,
                  unsigned int, fgetc, bs->input.file)
FUNC_READ_BITS_BE(br_read_bits_b_be,
                  unsigned int, br_buf_getc, bs->input.buffer)
FUNC_READ_BITS_LE(br_read_bits_b_le,
                  unsigned int, br_buf_getc, bs->input.buffer)
FUNC_READ_BITS_BE(br_read_bits_e_be,
                  unsigned int, ext_getc, bs->input.external)
FUNC_READ_BITS_LE(br_read_bits_e_le,
                  unsigned int, ext_getc, bs->input.external)
unsigned int
br_read_bits_c(BitstreamReader* bs, unsigned int count)
{
    br_abort(bs);
    return 0;
}


int
br_read_signed_bits_be(BitstreamReader* bs, unsigned int count)
{
    if (!bs->read(bs, 1)) {
        return bs->read(bs, count - 1);
    } else {
        return bs->read(bs, count - 1) - (1 << (count - 1));
    }
}

int
br_read_signed_bits_le(BitstreamReader* bs, unsigned int count)
{
    const int unsigned_value = bs->read(bs, count - 1);

    if (!bs->read(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}


FUNC_READ_BITS_BE(br_read_bits64_f_be,
                  uint64_t, fgetc, bs->input.file)
FUNC_READ_BITS_LE(br_read_bits64_f_le,
                  uint64_t, fgetc, bs->input.file)
FUNC_READ_BITS_BE(br_read_bits64_b_be,
                  uint64_t, br_buf_getc, bs->input.buffer)
FUNC_READ_BITS_LE(br_read_bits64_b_le,
                  uint64_t, br_buf_getc, bs->input.buffer)
FUNC_READ_BITS_BE(br_read_bits64_e_be,
                  uint64_t, ext_getc, bs->input.external)
FUNC_READ_BITS_LE(br_read_bits64_e_le,
                  uint64_t, ext_getc, bs->input.external)
uint64_t
br_read_bits64_c(BitstreamReader* bs, unsigned int count)
{
    br_abort(bs);
    return 0;
}

int64_t
br_read_signed_bits64_be(BitstreamReader* bs, unsigned int count)
{
    if (!bs->read(bs, 1)) {
        return bs->read_64(bs, count - 1);
    } else {
        return bs->read_64(bs, count - 1) - (1ll << (count - 1));
    }
}

int64_t
br_read_signed_bits64_le(BitstreamReader* bs, unsigned int count)
{
    const int64_t unsigned_value = bs->read_64(bs, count - 1);

    if (!bs->read(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1ll << (count - 1));
    }
}

#define FUNC_READ_BITS_BIGINT_BE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    void                                                              \
    FUNC_NAME(BitstreamReader* bs, unsigned int count, mpz_t value)   \
    {                                                                 \
        struct read_bits result = {0, 0, bs->state};                  \
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
                    for (callback = bs->callbacks;                    \
                         callback != NULL;                            \
                         callback = callback->next)                   \
                        callback->callback((uint8_t)byte,             \
                                           callback->data);           \
                } else {                                              \
                    mpz_clear(result_value);                          \
                    br_abort(bs);                                     \
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
        bs->state = result.state;                                     \
        mpz_clear(result_value);                                      \
    }
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_f_be, fgetc,
                         bs->input.file)
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_b_be, br_buf_getc,
                         bs->input.buffer)
FUNC_READ_BITS_BIGINT_BE(br_read_bits_bigint_e_be, ext_getc,
                         bs->input.external)

#define FUNC_READ_BITS_BIGINT_LE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    void                                                              \
    FUNC_NAME(BitstreamReader* bs, unsigned int count, mpz_t value)   \
    {                                                                 \
        struct read_bits result = {0, 0, bs->state};                  \
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
                    for (callback = bs->callbacks;                    \
                         callback != NULL;                            \
                         callback = callback->next)                   \
                         callback->callback((uint8_t)byte,            \
                                            callback->data);          \
                } else {                                              \
                    mpz_clear(result_value);                          \
                    br_abort(bs);                                     \
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
        bs->state = result.state;                                     \
        mpz_clear(result_value);                                      \
    }
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_f_le, fgetc,
                         bs->input.file)
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_b_le, br_buf_getc,
                         bs->input.buffer)
FUNC_READ_BITS_BIGINT_LE(br_read_bits_bigint_e_le, ext_getc,
                         bs->input.external)

void
br_read_bits_bigint_c(BitstreamReader* bs,
                      unsigned int count,
                      mpz_t value)
{
    br_abort(bs);
}

void
br_read_signed_bits_bigint_be(BitstreamReader* bs,
                              unsigned int count,
                              mpz_t value)
{
    if (!bs->read(bs, 1)) {
        /*unsigned value*/

        bs->read_bigint(bs, count - 1, value);
    } else {
        /*signed value*/

        mpz_t unsigned_value;
        mpz_t to_subtract;

        mpz_init(unsigned_value);
        if (!setjmp(*br_try(bs))) {
            bs->read_bigint(bs, count - 1, unsigned_value);
            br_etry(bs);
        } else {
            /*be sure to free unsigned_value before re-raising error*/
            br_etry(bs);
            mpz_clear(unsigned_value);
            br_abort(bs);
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

void
br_read_signed_bits_bigint_le(BitstreamReader* bs,
                              unsigned int count,
                              mpz_t value)
{
    mpz_t unsigned_value;
    mpz_init(unsigned_value);

    if (!setjmp(*br_try(bs))) {
        bs->read_bigint(bs, count - 1, unsigned_value);

        if (!bs->read(bs, 1)) {
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
        br_etry(bs);
        mpz_clear(unsigned_value);
    } else {
        /*be sure to free unsigned value before re-raising error*/
        br_etry(bs);
        mpz_clear(unsigned_value);
        br_abort(bs);
    }
}

#define BUFFER_SIZE 4096


/*the skip_bits functions differ from the read_bits functions
  in that they have no accumulator
  which allows them to skip over a potentially unlimited amount of bits*/
#define FUNC_SKIP_BITS_BE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
  void                                                          \
  FUNC_NAME(BitstreamReader* bs, unsigned int count)            \
  {                                                             \
      if ((bs->state == 0) && ((count % 8) == 0)) {             \
          count /= 8;                                           \
          while (count > 0) {                                   \
              const unsigned int byte_count = MIN(BUFFER_SIZE, count); \
              static uint8_t dummy[BUFFER_SIZE];                \
              bs->read_bytes(bs, dummy, byte_count);            \
              count -= byte_count;                              \
          }                                                     \
      } else {                                                  \
          struct read_bits result = {0, 0, bs->state};          \
                                                                \
          while (count > 0) {                                   \
              if (result.state == 0) {                          \
                  const int byte = BYTE_FUNC(BYTE_FUNC_ARG);    \
                  if (byte != EOF) {                            \
                      struct bs_callback* callback;             \
                      result.state = NEW_STATE(byte);           \
                      for (callback = bs->callbacks;            \
                           callback != NULL;                    \
                           callback = callback->next)           \
                           callback->callback((uint8_t)byte,    \
                                              callback->data);  \
                  } else {                                      \
                      br_abort(bs);                             \
                  }                                             \
              }                                                 \
                                                                \
              result = read_bits_table_be[result.state][MIN(count, 8) - 1]; \
                                                                \
              count -= result.value_size;                       \
          }                                                     \
                                                                \
          bs->state = result.state;                             \
      }                                                         \
  }
FUNC_SKIP_BITS_BE(br_skip_bits_f_be, fgetc, bs->input.file)
FUNC_SKIP_BITS_BE(br_skip_bits_b_be, br_buf_getc, bs->input.buffer)
FUNC_SKIP_BITS_BE(br_skip_bits_e_be, ext_getc, bs->input.external)

#define FUNC_SKIP_BITS_LE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
  void                                                         \
  FUNC_NAME(BitstreamReader* bs, unsigned int count)           \
  {                                                            \
      if ((bs->state == 0) && ((count % 8) == 0)) {            \
          count /= 8;                                          \
          while (count > 0) {                                  \
              const unsigned int byte_count = MIN(BUFFER_SIZE, count); \
              static uint8_t dummy[BUFFER_SIZE];               \
              bs->read_bytes(bs, dummy, byte_count);           \
              count -= byte_count;                             \
          }                                                    \
      } else {                                                 \
          struct read_bits result = {0, 0, bs->state};         \
                                                               \
          while (count > 0) {                                  \
              if (result.state == 0) {                         \
                  const int byte = BYTE_FUNC(BYTE_FUNC_ARG);   \
                  if (byte != EOF) {                           \
                      struct bs_callback* callback;            \
                      result.state = NEW_STATE(byte);          \
                      for (callback = bs->callbacks;           \
                           callback != NULL;                   \
                           callback = callback->next)          \
                           callback->callback((uint8_t)byte,   \
                                              callback->data); \
                  } else {                                     \
                      br_abort(bs);                            \
                  }                                            \
              }                                                \
                                                               \
              result = read_bits_table_le[result.state][MIN(count, 8) - 1]; \
                                                               \
              count -= result.value_size;                      \
          }                                                    \
                                                               \
          bs->state = result.state;                            \
      }                                                        \
  }
FUNC_SKIP_BITS_LE(br_skip_bits_f_le, fgetc, bs->input.file)
FUNC_SKIP_BITS_LE(br_skip_bits_b_le, br_buf_getc, bs->input.buffer)
FUNC_SKIP_BITS_LE(br_skip_bits_e_le, ext_getc, bs->input.external)

void

br_skip_bits_c(BitstreamReader* bs, unsigned int count)
{
    br_abort(bs);
}


void
br_unread_bit_be(BitstreamReader* bs, int unread_bit)
{
    const static struct unread_bit unread_bit_table_be[0x200][2] =
#include "unread_bit_table_be.h"
    ;
    struct unread_bit result = unread_bit_table_be[bs->state][unread_bit];
    assert(result.limit_reached == 0);
    bs->state = result.state;
}

void
br_unread_bit_le(BitstreamReader* bs, int unread_bit)
{
    const struct unread_bit unread_bit_table_le[0x200][2] =
#include "unread_bit_table_le.h"
    ;
    struct unread_bit result = unread_bit_table_le[bs->state][unread_bit];
    assert(result.limit_reached == 0);
    bs->state = result.state;
}

void
br_unread_bit_c(BitstreamReader* bs, int unread_bit)
{
    return;
}


#define FUNC_READ_UNARY(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG, UNARY_TABLE) \
    unsigned int                                                        \
    FUNC_NAME(BitstreamReader* bs, int stop_bit)                        \
    {                                                                   \
        struct read_unary result = {0, 0, bs->state};                   \
        register unsigned accumulator = 0;                              \
                                                                        \
        do {                                                            \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = bs->callbacks;                      \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(bs);                                       \
                }                                                       \
            }                                                           \
                                                                        \
            result = UNARY_TABLE[result.state][stop_bit];               \
                                                                        \
            accumulator += result.value;                                \
        } while (result.continue_);                                     \
                                                                        \
        bs->state = result.state;                                       \
        return accumulator;                                             \
    }

FUNC_READ_UNARY(br_read_unary_f_be,
                fgetc, bs->input.file, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_f_le,
                fgetc, bs->input.file, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_b_be,
                br_buf_getc, bs->input.buffer, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_b_le,
                br_buf_getc, bs->input.buffer, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_e_be,
                ext_getc, bs->input.external, read_unary_table_be)
FUNC_READ_UNARY(br_read_unary_e_le,
                ext_getc, bs->input.external, read_unary_table_le)
unsigned int
br_read_unary_c(BitstreamReader* bs, int stop_bit)
{
    br_abort(bs);
    return 0;
}

#define FUNC_SKIP_UNARY(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG, UNARY_TABLE) \
    void                                                                \
    FUNC_NAME(BitstreamReader* bs, int stop_bit)                        \
    {                                                                   \
        struct read_unary result = {0, 0, bs->state};                   \
        do {                                                            \
            if (result.state == 0) {                                    \
                const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
                if (byte != EOF) {                                      \
                    struct bs_callback* callback;                       \
                    result.state = NEW_STATE(byte);                     \
                    for (callback = bs->callbacks;                      \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                } else {                                                \
                    br_abort(bs);                                       \
                }                                                       \
            }                                                           \
                                                                        \
            result = UNARY_TABLE[result.state][stop_bit];               \
        } while (result.continue_);                                     \
                                                                        \
        bs->state = result.state;                                       \
    }
FUNC_SKIP_UNARY(br_skip_unary_f_be,
                fgetc, bs->input.file, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_f_le,
                fgetc, bs->input.file, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_b_be,
                br_buf_getc, bs->input.buffer, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_b_le,
                br_buf_getc, bs->input.buffer, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_e_be,
                ext_getc, bs->input.external, read_unary_table_be)
FUNC_SKIP_UNARY(br_skip_unary_e_le,
                ext_getc, bs->input.external, read_unary_table_le)

void
br_skip_unary_c(BitstreamReader* bs, int stop_bit)
{
    br_abort(bs);
}


static void
__br_set_endianness_be__(BitstreamReader* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read_signed = br_read_signed_bits_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->read_signed_bigint = br_read_signed_bits_bigint_le;
        bs->unread = br_unread_bit_le;
    }
}

static void
__br_set_endianness_le__(BitstreamReader* bs, bs_endianness endianness)
{

    bs->endianness = endianness;
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read_signed = br_read_signed_bits_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->read_signed_bigint = br_read_signed_bits_bigint_be;
        bs->unread = br_unread_bit_be;
    }
}

void
br_set_endianness_f_be(BitstreamReader *bs, bs_endianness endianness)
{
    __br_set_endianness_be__(bs, endianness);
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_f_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->read_bigint = br_read_bits_bigint_f_le;
        bs->skip = br_skip_bits_f_le;
        bs->read_unary = br_read_unary_f_le;
        bs->skip_unary = br_skip_unary_f_le;
        bs->set_endianness = br_set_endianness_f_le;
    }
}

void
br_set_endianness_f_le(BitstreamReader *bs, bs_endianness endianness)
{
    __br_set_endianness_le__(bs, endianness);
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_f_be;
        bs->read_64 = br_read_bits64_f_be;
        bs->read_bigint = br_read_bits_bigint_f_be;
        bs->skip = br_skip_bits_f_be;
        bs->read_unary = br_read_unary_f_be;
        bs->skip_unary = br_skip_unary_f_be;
        bs->set_endianness = br_set_endianness_f_be;
    }
}

void
br_set_endianness_b_be(BitstreamReader *bs, bs_endianness endianness)
{
    __br_set_endianness_be__(bs, endianness);
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_b_le;
        bs->read_64 = br_read_bits64_b_le;
        bs->read_bigint = br_read_bits_bigint_b_le;
        bs->skip = br_skip_bits_b_le;
        bs->read_unary = br_read_unary_b_le;
        bs->skip_unary = br_skip_unary_b_le;
        bs->set_endianness = br_set_endianness_b_le;
    }
}

void
br_set_endianness_b_le(BitstreamReader *bs, bs_endianness endianness)
{
    __br_set_endianness_le__(bs, endianness);
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_b_be;
        bs->read_64 = br_read_bits64_b_be;
        bs->read_bigint = br_read_bits_bigint_b_be;
        bs->skip = br_skip_bits_b_be;
        bs->read_unary = br_read_unary_b_be;
        bs->skip_unary = br_skip_unary_b_be;
        bs->set_endianness = br_set_endianness_b_be;
    }
}

void
br_set_endianness_e_be(BitstreamReader *bs, bs_endianness endianness)
{
    __br_set_endianness_be__(bs, endianness);
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_e_le;
        bs->read_64 = br_read_bits64_e_le;
        bs->read_bigint = br_read_bits_bigint_e_le;
        bs->skip = br_skip_bits_e_le;
        bs->read_unary = br_read_unary_e_le;
        bs->skip_unary = br_skip_unary_e_le;
        bs->set_endianness = br_set_endianness_e_le;
    }
}

void
br_set_endianness_e_le(BitstreamReader *bs, bs_endianness endianness)
{
    __br_set_endianness_le__(bs, endianness);
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_e_be;
        bs->read_64 = br_read_bits64_e_be;
        bs->read_bigint = br_read_bits_bigint_e_be;
        bs->skip = br_skip_bits_e_be;
        bs->read_unary = br_read_unary_e_be;
        bs->skip_unary = br_skip_unary_e_be;
        bs->set_endianness = br_set_endianness_e_be;
    }
}


void
br_set_endianness_c(BitstreamReader *bs, bs_endianness endianness)
{
    bs->endianness = endianness;
}


#define FUNC_READ_HUFFMAN_CODE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    int                                                             \
    FUNC_NAME(BitstreamReader *bs,                                  \
              br_huffman_table_t table[])                           \
    {                                                               \
        br_huffman_entry_t entry = table[0][bs->state];             \
                                                                    \
        while (entry.continue_) {                                   \
            const int byte = BYTE_FUNC(BYTE_FUNC_ARG);              \
            if (byte != EOF) {                                      \
                struct bs_callback* callback;                       \
                const state_t state = NEW_STATE(byte);              \
                                                                    \
                for (callback = bs->callbacks;                      \
                     callback != NULL;                              \
                     callback = callback->next)                     \
                     callback->callback((uint8_t)byte,              \
                                        callback->data);            \
                                                                    \
                entry = table[entry.node][state];                   \
            } else {                                                \
                br_abort(bs);                                       \
            }                                                       \
        }                                                           \
                                                                    \
        bs->state = entry.state;                                    \
        return entry.value;                                         \
    }
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_f, fgetc, bs->input.file)
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_b, br_buf_getc, bs->input.buffer)
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_e, ext_getc, bs->input.external)

int
br_read_huffman_code_c(BitstreamReader *bs,
                       br_huffman_table_t table[])
{
    br_abort(bs);
    return 0;
}


void
br_read_bytes_f(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count)
{
    if (bs->state == 0) {
        /*stream is byte-aligned, so perform optimized read*/

        /*fread bytes from file handle to output*/
        if (fread(bytes, sizeof(uint8_t), byte_count, bs->input.file) ==
            byte_count) {
            struct bs_callback* callback;
            /*if sufficient bytes were read
              perform callbacks on the read bytes*/
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next) {
                unsigned int i;
                for (i = 0; i < byte_count; i++)
                    callback->callback(bytes[i], callback->data);
            }
        } else {
            br_abort(bs);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (; byte_count; byte_count--) {
            *bytes++ = bs->read(bs, 8);
        }
    }
}

void
br_read_bytes_b(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count)
{
    if (bs->state == 0) {
        /*stream is byte-aligned, so perform optimized read*/

        /*buf_read bytes from buffer to output*/
        if (br_buf_read(bs->input.buffer,
                        bytes,
                        byte_count) == byte_count) {
            struct bs_callback* callback;
            /*if sufficient bytes were read
              perform callbacks on the read bytes*/
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next) {
                unsigned int i;
                for (i = 0; i < byte_count; i++)
                    callback->callback(bytes[i], callback->data);
            }
        } else {
            br_abort(bs);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (; byte_count; byte_count--) {
            *bytes++ = bs->read(bs, 8);
        }
    }
}

void
br_read_bytes_e(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count)
{
    if (bs->state == 0) {
        /*stream is byte-aligned, so perform optimized read*/

        /*ext_fread bytes from handle to putput*/
        if (ext_fread(bs->input.external, bytes, byte_count) == byte_count) {
            struct bs_callback* callback;
            /*if sufficient bytes were read
              perform callbacks on the read bytes*/
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next) {
                unsigned i;
                for (i = 0; i < byte_count; i++)
                    callback->callback(bytes[i], callback->data);
            }
        } else {
            br_abort(bs);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (; byte_count; byte_count--) {
            *bytes++ = bs->read(bs, 8);
        }
    }
}

void
br_read_bytes_c(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count)
{
    br_abort(bs);
}


void
br_skip_bytes(BitstreamReader* bs, unsigned int count)
{
    /*try to generate large, byte-aligned chunks of bit skips*/
    while (count > 0) {
        const unsigned int byte_count = MIN(BUFFER_SIZE, count);
        static uint8_t dummy[BUFFER_SIZE];
        bs->read_bytes(bs, dummy, byte_count);
        count -= byte_count;
    }
}


void
br_parse(struct BitstreamReader_s* stream, const char* format, ...)
{
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
                *value = stream->read(stream, size);
            }
            break;
        case BS_INST_SIGNED:
            for (; times; times--) {
                int *value = va_arg(ap, int*);
                *value = stream->read_signed(stream, size);
            }
            break;
        case BS_INST_UNSIGNED64:
            for (; times; times--) {
                uint64_t *value = va_arg(ap, uint64_t*);
                *value = stream->read_64(stream, size);
            }
            break;
        case BS_INST_SIGNED64:
            for (; times; times--) {
                int64_t *value = va_arg(ap, int64_t*);
                *value = stream->read_signed_64(stream, size);
            }
            break;
        case BS_INST_SKIP:
            for (; times; times--) {
                stream->skip(stream, size);
            }
            break;
        case BS_INST_SKIP_BYTES:
            for (; times; times--) {
                stream->skip_bytes(stream, size);
            }
            break;
        case BS_INST_BYTES:
            for (; times; times--) {
                uint8_t *value = va_arg(ap, uint8_t*);
                stream->read_bytes(stream, value, size);
            }
            break;
        case BS_INST_ALIGN:
            stream->byte_align(stream);
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);
    va_end(ap);
}


int
br_byte_aligned(const BitstreamReader* bs)
{
    return (bs->state == 0);
}


void
br_byte_align(BitstreamReader* bs)
{
    bs->state = 0;
}

br_pos_t*
br_getpos_f(BitstreamReader* bs)
{
    br_pos_t* pos = malloc(sizeof(br_pos_t));
    pos->reader = bs;
    fgetpos(bs->input.file, &(pos->position.file));
    pos->state = bs->state;
    pos->del = br_pos_del_f;
    return pos;
}

br_pos_t*
br_getpos_b(BitstreamReader* bs)
{
    br_pos_t* pos = malloc(sizeof(br_pos_t));
    pos->reader = bs;
    br_buf_getpos(bs->input.buffer, &(pos->position.buffer));
    pos->state = bs->state;
    pos->del = br_pos_del_b;
    return pos;
}

br_pos_t*
br_getpos_e(BitstreamReader* bs)
{
    struct br_external_input* input = bs->input.external;
    const unsigned buffer_size = input->buffer.size - input->buffer.pos;
    void *ext_pos = ext_getpos_r(input);
    br_pos_t* pos;

    if (ext_pos == NULL) {
        br_abort(bs);
    }

    pos = malloc(sizeof(br_pos_t));
    pos->reader = bs;
    pos->position.external.pos = ext_pos;
    pos->position.external.buffer_size = buffer_size;
    pos->position.external.buffer = malloc(buffer_size * sizeof(uint8_t));
    pos->position.external.free_pos = input->free_pos;
    memcpy(pos->position.external.buffer,
           input->buffer.data + input->buffer.pos,
           buffer_size * sizeof(uint8_t));
    pos->state = bs->state;
    pos->del = br_pos_del_e;
    return pos;
}

br_pos_t*
br_getpos_c(BitstreamReader* bs)
{
    br_abort(bs);
    return NULL;  /*shouldn't get here*/
}


void
br_setpos_f(BitstreamReader* bs, const br_pos_t* pos)
{
    if (pos->reader != bs) {
        br_abort(bs);
    }
    fsetpos(bs->input.file, &(pos->position.file));
    bs->state = pos->state;
}

void
br_setpos_b(BitstreamReader* bs, const br_pos_t* pos)
{
    if (pos->reader != bs) {
        br_abort(bs);
    }
    br_buf_setpos(bs->input.buffer, pos->position.buffer);
    bs->state = pos->state;
}

void
br_setpos_e(BitstreamReader* bs, const br_pos_t* pos)
{
    struct br_external_input* input = bs->input.external;
    if (pos->reader != bs) {
        br_abort(bs);
    }
    if (ext_setpos_r(input, pos->position.external.pos)) {
        br_abort(bs);
    }
    memcpy(input->buffer.data,
           pos->position.external.buffer,
           pos->position.external.buffer_size);
    input->buffer.pos = 0;
    input->buffer.size = pos->position.external.buffer_size;
    bs->state = pos->state;
}

void
br_setpos_c(BitstreamReader* bs, const br_pos_t* pos)
{
    br_abort(bs);
}


void
br_pos_del_f(br_pos_t* pos)
{
    free(pos);
}

void
br_pos_del_b(br_pos_t* pos)
{
    free(pos);
}

void
br_pos_del_e(br_pos_t* pos)
{
    pos->position.external.free_pos(pos->position.external.pos);
    free(pos->position.external.buffer);
    free(pos);
}


void
br_seek_f(BitstreamReader* bs, long position, bs_whence whence)
{
    bs->state = 0;
    if (fseek(bs->input.file, position, whence)) {
        br_abort(bs);
    }
}

void
br_seek_b(BitstreamReader* bs, long position, bs_whence whence)
{
    bs->state = 0;
    if (br_buf_fseek(bs->input.buffer, position, whence)) {
        br_abort(bs);
    }
}

void
br_seek_e(BitstreamReader* bs, long position, bs_whence whence)
{
    bs->state = 0;
    if (ext_fseek_r(bs->input.external, position, whence)) {
        br_abort(bs);
    }
}

void
br_seek_c(BitstreamReader* bs, long position, bs_whence whence)
{
    br_abort(bs);
}


struct BitstreamReader_s*
br_substream(struct BitstreamReader_s *stream, unsigned bytes)
{
    BitstreamReader *substream = br_open_buffer(NULL, 0, stream->endianness);
    struct br_buffer *buffer = substream->input.buffer;
    const unsigned BUF_SIZE = 1 << 20;

    if (!setjmp(*br_try(stream))) {
        /*read input stream in chunks to avoid allocating
          a whole lot of data upfront
          in case "bytes" is much larger than the input stream*/
        while (bytes) {
            const unsigned to_read = MIN(BUF_SIZE, bytes);
            buffer->data = realloc(buffer->data, buffer->size + to_read);
            stream->read_bytes(stream, buffer->data + buffer->size, to_read);
            buffer->size += to_read;
            bytes -= to_read;
        }
        br_etry(stream);
        return substream;
    } else {
        /*be sure to close partial substream before re-raising abort*/
        substream->close(substream);
        br_etry(stream);
        br_abort(stream);
        return NULL;  /*won't get here*/
    }
}


void
br_close_methods(BitstreamReader* bs)
{
    /*swap read methods with closed methods that generate read errors*/
    bs->read = br_read_bits_c;
    bs->read_64 = br_read_bits64_c;
    bs->read_bigint = br_read_bits_bigint_c;
    bs->skip = br_skip_bits_c;
    bs->unread = br_unread_bit_c;
    bs->read_unary = br_read_unary_c;
    bs->skip_unary = br_skip_unary_c;
    bs->read_huffman_code = br_read_huffman_code_c;
    bs->read_bytes = br_read_bytes_c;
    bs->set_endianness = br_set_endianness_c;

    bs->getpos = br_getpos_c;
    bs->setpos = br_setpos_c;

    bs->close_internal_stream = br_close_internal_stream_c;
}


void
br_close_internal_stream_f(BitstreamReader* bs)
{
    /*perform fclose on FILE object*/
    fclose(bs->input.file);

    /*swap read methods with closed methods*/
    br_close_methods(bs);
}

void
br_close_internal_stream_b(BitstreamReader* bs)
{
    /*swap read methods with closed methods*/
    br_close_methods(bs);
}

void
br_close_internal_stream_e(BitstreamReader* bs)
{
    /*perform close operation on file-like object*/
    ext_close_r(bs->input.external);

    /*swap read methods with closed methods*/
    br_close_methods(bs);
}


void
br_close_internal_stream_c(BitstreamReader* bs)
{
    return;
}


void
br_free_f(BitstreamReader* bs)
{
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    /*deallocate callbacks*/
    while (bs->callbacks != NULL) {
        bs->pop_callback(bs, NULL);
    }

    /*deallocate exceptions*/
    if (bs->exceptions != NULL) {
        fprintf(stderr, "*** Warning: leftover etry entries on stack\n");
    }
    for (e_node = bs->exceptions; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate used exceptions*/
    for (e_node = bs->exceptions_used; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate the struct itself*/
    free(bs);
}

void
br_free_b(BitstreamReader* bs)
{
    /*deallocate buffer*/
    br_buf_free(bs->input.buffer);

    /*perform additional deallocations on rest of struct*/
    br_free_f(bs);
}

void
br_free_e(BitstreamReader* bs)
{
    /*free internal file-like object, if necessary*/
    ext_free_r(bs->input.external);

    /*perform additional deallocations on rest of struct*/
    br_free_f(bs);
}


void
br_close(BitstreamReader* bs)
{
    bs->close_internal_stream(bs);
    bs->free(bs);
}


#ifdef DEBUG
void
__br_abort__(BitstreamReader *bs, int lineno)
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
br_abort(BitstreamReader *bs)
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
br_try(BitstreamReader *bs)
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
__br_etry(BitstreamReader *bs, const char *file, int lineno)
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
        bs->write_signed = bw_write_signed_bits_f_e_r_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_be;
        bs->set_endianness = bw_set_endianness_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_f_le;
        bs->write_signed = bw_write_signed_bits_f_e_r_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_le;
        bs->set_endianness = bw_set_endianness_f_le;
        break;
    }

    bs->write_unary = bw_write_unary_f_e_r;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_f;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned_f_e_r;
    bs->byte_align = bw_byte_align_f_e_r;
    bs->flush = bw_flush_f;
    bs->add_callback = bw_add_callback;
    bs->push_callback = bw_push_callback;
    bs->pop_callback = bw_pop_callback;
    bs->call_callbacks = bw_call_callbacks;
    bs->getpos = bw_getpos_f;
    bs->setpos = bw_setpos_f;

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
        bs->write_signed = bw_write_signed_bits_f_e_r_be;
        bs->write_64 = bw_write_bits64_e_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_be;
        bs->set_endianness = bw_set_endianness_e_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_e_le;
        bs->write_signed = bw_write_signed_bits_f_e_r_le;
        bs->write_64 = bw_write_bits64_e_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_le;
        bs->set_endianness = bw_set_endianness_e_le;
        break;
    }

    bs->write_unary = bw_write_unary_f_e_r;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_e;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned_f_e_r;
    bs->byte_align = bw_byte_align_f_e_r;
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
    BitstreamRecorder *bs = malloc(sizeof(BitstreamRecorder));
    bs->endianness = endianness;
    bs->type = BW_RECORDER;

    bs->output.recorder = bw_buf_new();
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_r_be;
        bs->write_signed = bw_write_signed_bits_f_e_r_be;
        bs->write_64 = bw_write_bits64_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_be;
        bs->set_endianness = bw_set_endianness_r_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_r_le;
        bs->write_signed = bw_write_signed_bits_f_e_r_le;
        bs->write_64 = bw_write_bits64_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_le;
        bs->set_endianness = bw_set_endianness_r_le;
        break;
    }

    bs->write_unary = bw_write_unary_f_e_r;
    bs->write_huffman_code = bw_write_huffman;
    bs->write_bytes = bw_write_bytes_r;
    bs->build = bw_build;
    bs->byte_aligned = bw_byte_aligned_f_e_r;
    bs->byte_align = bw_byte_align_f_e_r;
    bs->flush = bw_flush_r_c;
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
    bs->split = bw_split_r;
    bs->data = bw_data_r;
    bs->close_internal_stream = bw_close_internal_stream_r;
    bs->free = bw_free_r;
    bs->close = bw_close_r;

    return bs;
}


#define FUNC_WRITE_BITS_BE(FUNC_NAME, VALUE_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    void                                                                \
    FUNC_NAME(BitstreamWriter* bs, unsigned int count, VALUE_TYPE value) \
    {                                                                   \
        /* assert(value < (1l << count));  */                           \
                                                                        \
        while (count > 0) {                                             \
            /*chop off up to 8 bits to write at a time*/                \
            const int bits_to_write = count > 8 ? 8 : count;            \
            const VALUE_TYPE value_to_write =                           \
                value >> (count - bits_to_write);                       \
                                                                        \
            /*new data is added to the buffer least-significant first*/ \
            bs->buffer = (unsigned int)((bs->buffer << bits_to_write) | \
                                        value_to_write);                \
            bs->buffer_size += bits_to_write;                           \
                                                                        \
            /*if buffer is over 8 bits,*/                               \
            /*extract bits most-significant first*/                     \
            /*and remove them from the buffer*/                         \
            if (bs->buffer_size >= 8) {                                 \
                const unsigned byte =                                   \
                    (bs->buffer >> (bs->buffer_size - 8)) & 0xFF;       \
                if (BYTE_FUNC(byte, BYTE_FUNC_ARG) != EOF) {            \
                    struct bs_callback* callback;                       \
                                                                        \
                    for (callback = bs->callbacks;                      \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                                                                        \
                    bs->buffer_size -= 8;                               \
                } else {                                                \
                    bw_abort(bs);                                       \
                }                                                       \
            }                                                           \
                                                                        \
            /*decrement the count and value*/                           \
            value -= (value_to_write << (count - bits_to_write));       \
            count -= bits_to_write;                                     \
        }                                                               \
    }

#define FUNC_WRITE_BITS_LE(FUNC_NAME, VALUE_TYPE, BYTE_FUNC, BYTE_FUNC_ARG) \
    void                                                                \
    FUNC_NAME(BitstreamWriter* bs, unsigned int count, VALUE_TYPE value) \
    {                                                                   \
        /* assert(value < (int64_t)(1LL << count)); */                  \
                                                                        \
        while (count > 0) {                                             \
            /*chop off up to 8 bits to write at a time*/                \
            const int bits_to_write = count > 8 ? 8 : count;            \
            const VALUE_TYPE value_to_write =                           \
                value & ((1 << bits_to_write) - 1);                     \
                                                                        \
            /*new data is added to the buffer most-significant first*/  \
            bs->buffer |= (unsigned int)(value_to_write <<              \
                                         bs->buffer_size);              \
            bs->buffer_size += bits_to_write;                           \
                                                                        \
            /*if buffer is over 8 bits,*/                               \
            /*extract bits least-significant first*/                    \
            /*and remove them from the buffer*/                         \
            if (bs->buffer_size >= 8) {                                 \
                const unsigned byte = bs->buffer & 0xFF;                \
                if (BYTE_FUNC(byte, BYTE_FUNC_ARG) != EOF) {            \
                    struct bs_callback* callback;                       \
                                                                        \
                    for (callback = bs->callbacks;                      \
                         callback != NULL;                              \
                         callback = callback->next)                     \
                         callback->callback((uint8_t)byte,              \
                                            callback->data);            \
                    bs->buffer >>= 8;                                   \
                    bs->buffer_size -= 8;                               \
                } else {                                                \
                    bw_abort(bs);                                       \
                }                                                       \
            }                                                           \
                                                                        \
            /*decrement the count and value*/                           \
            value >>= bits_to_write;                                    \
            count -= bits_to_write;                                     \
        }                                                               \
    }

FUNC_WRITE_BITS_BE(bw_write_bits_f_be,
                   unsigned int, fputc, bs->output.file)
FUNC_WRITE_BITS_LE(bw_write_bits_f_le,
                   unsigned int, fputc, bs->output.file)
FUNC_WRITE_BITS_BE(bw_write_bits_e_be,
                   unsigned int, ext_putc, bs->output.external)
FUNC_WRITE_BITS_LE(bw_write_bits_e_le,
                   unsigned int, ext_putc, bs->output.external)
FUNC_WRITE_BITS_BE(bw_write_bits_r_be,
                   unsigned int, bw_buf_putc, bs->output.recorder)
FUNC_WRITE_BITS_LE(bw_write_bits_r_le,
                   unsigned int, bw_buf_putc, bs->output.recorder)


void
bw_write_bits_c(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    bw_abort(bs);
}

void
bw_write_signed_bits_f_e_r_be(BitstreamWriter* bs, unsigned int count,
                              int value)
{
    assert(value <= ((1 << (count - 1)) - 1));
    assert(value >= -(1 << (count - 1)));

    if (value >= 0) {
        bs->write(bs, 1, 0);
        bs->write(bs, count - 1, value);
    } else {
        bs->write(bs, 1, 1);
        bs->write(bs, count - 1, (1 << (count - 1)) + value);
    }
}


void
bw_write_signed_bits_f_e_r_le(BitstreamWriter* bs, unsigned int count,
                              int value)
{
    assert(value <= ((1 << (count - 1)) - 1));
    assert(value >= -(1 << (count - 1)));

    if (value >= 0) {
        bs->write(bs, count - 1, value);
        bs->write(bs, 1, 0);
    } else {
        bs->write(bs, count - 1, (1 << (count - 1)) + value);
        bs->write(bs, 1, 1);
    }
}

void
bw_write_signed_bits_c(BitstreamWriter* bs, unsigned int count, int value)
{
    bw_abort(bs);
}


FUNC_WRITE_BITS_BE(bw_write_bits64_f_be,
                   uint64_t, fputc, bs->output.file)
FUNC_WRITE_BITS_LE(bw_write_bits64_f_le,
                   uint64_t, fputc, bs->output.file)
FUNC_WRITE_BITS_BE(bw_write_bits64_e_be,
                   uint64_t, ext_putc, bs->output.external)
FUNC_WRITE_BITS_LE(bw_write_bits64_e_le,
                   uint64_t, ext_putc, bs->output.external)
FUNC_WRITE_BITS_BE(bw_write_bits64_r_be,
                   uint64_t, bw_buf_putc, bs->output.recorder)
FUNC_WRITE_BITS_LE(bw_write_bits64_r_le,
                   uint64_t, bw_buf_putc, bs->output.recorder)

void
bw_write_bits64_c(BitstreamWriter* bs, unsigned int count, uint64_t value)
{
    bw_abort(bs);
}


void
bw_write_signed_bits64_f_e_r_be(BitstreamWriter* bs, unsigned int count,
                                int64_t value)
{
    assert(value <= ((1ll << (count - 1)) - 1));
    assert(value >= -(1ll << (count - 1)));

    if (value >= 0ll) {
        bs->write(bs, 1, 0);
        bs->write_64(bs, count - 1, value);
    } else {
        bs->write(bs, 1, 1);
        bs->write_64(bs, count - 1, (1ll << (count - 1)) + value);
    }
}

void
bw_write_signed_bits64_f_e_r_le(BitstreamWriter* bs, unsigned int count,
                                int64_t value)
{
    assert(value <= ((1ll << (count - 1)) - 1));
    assert(value >= -(1ll << (count - 1)));

    if (value >= 0ll) {
        bs->write_64(bs, count - 1, value);
        bs->write(bs, 1, 0);
    } else {
        bs->write_64(bs, count - 1, (1ll << (count - 1)) + value);
        bs->write(bs, 1, 1);
    }
}


void
bw_write_signed_bits64_c(BitstreamWriter* bs, unsigned int count,
                         int64_t value)
{
    bw_abort(bs);
}


#define UNARY_BUFFER_SIZE 30

void
bw_write_unary_f_e_r(BitstreamWriter* bs, int stop_bit, unsigned int value)
{
    unsigned int bits_to_write;

    /*send our pre-stop bits to write() in 30-bit chunks*/
    while (value > 0) {
        bits_to_write = value <= UNARY_BUFFER_SIZE ? value : UNARY_BUFFER_SIZE;
        if (stop_bit) { /*stop bit of 1, buffer value of all 0s*/
            bs->write(bs, bits_to_write, 0);
        } else {        /*stop bit of 0, buffer value of all 1s*/
            bs->write(bs, bits_to_write, (1 << bits_to_write) - 1);
        }
        value -= bits_to_write;
    }

    /*finally, send our stop bit*/
    bs->write(bs, 1, stop_bit);
}

void
bw_write_unary_c(BitstreamWriter* bs, int stop_bit, unsigned int value)
{
    bw_abort(bs);
}


void
bw_set_endianness_f_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_f_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->write_signed = bw_write_signed_bits_f_e_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_le;
        bs->set_endianness = bw_set_endianness_f_le;
    }
}

void
bw_set_endianness_f_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_f_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->write_signed = bw_write_signed_bits_f_e_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_be;
        bs->set_endianness = bw_set_endianness_f_be;
    }
}

void
bw_set_endianness_r_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_r_le;
        bs->write_64 = bw_write_bits64_r_le;
        bs->write_signed = bw_write_signed_bits_f_e_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_le;
        bs->set_endianness = bw_set_endianness_r_le;
    }
}

void
bw_set_endianness_r_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_r_be;
        bs->write_64 = bw_write_bits64_r_be;
        bs->write_signed = bw_write_signed_bits_f_e_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_be;
        bs->set_endianness = bw_set_endianness_r_be;
    }
}

void
bw_set_endianness_e_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_e_le;
        bs->write_64 = bw_write_bits64_e_le;
        bs->write_signed = bw_write_signed_bits_f_e_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_le;
        bs->set_endianness = bw_set_endianness_e_le;
    }
}

void
bw_set_endianness_e_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_e_be;
        bs->write_64 = bw_write_bits64_e_be;
        bs->write_signed = bw_write_signed_bits_f_e_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_e_r_be;
        bs->set_endianness = bw_set_endianness_e_be;
    }
}


void
bw_set_endianness_c(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->endianness = endianness;
}


int
bw_write_huffman(BitstreamWriter* bs,
                 bw_huffman_table_t* table,
                 int value)
{
    int current_index = 0;

    while (current_index != -1) {
        if (table[current_index].value == value) {
            bs->write(bs,
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


void
bw_write_bytes_f(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count)
{
    unsigned i;

    if (bs->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so perform optimized write*/
        if (fwrite(bytes, sizeof(uint8_t), count, bs->output.file) != count)
            bw_abort(bs);

        /*perform callbacks on the written bytes*/
        for (callback = bs->callbacks;
             callback != NULL;
             callback = callback->next)
            for (i = 0; i < count; i++)
                callback->callback(bytes[i], callback->data);
    } else {
        /*stream is not byte-aligned, so perform multiple writes*/
        for (i = 0; i < count; i++)
            bs->write(bs, 8, bytes[i]);
    }
}

void
bw_write_bytes_e(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count)
{
    unsigned int i;

    if (bs->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so performed optimized write*/
        if (ext_fwrite(bs->output.external, bytes, count)) {
            bw_abort(bs);
        }

        /*perform callbacks on the written bytes*/
        for (callback = bs->callbacks;
             callback != NULL;
             callback = callback->next)
            for (i = 0; i < count; i++)
                callback->callback(bytes[i], callback->data);
    } else {
        /*stream is not byte-aligned, so perform multiple writes*/
        for (i = 0; i < count; i++)
            bs->write(bs, 8, bytes[i]);
    }
}

void
bw_write_bytes_r(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count)
{
    unsigned i;

    if (bs->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so perform optimized write*/
        bw_buf_write(bs->output.recorder, bytes, count);

        /*perform callbacks on the written bytes*/
        for (callback = bs->callbacks;
             callback != NULL;
             callback = callback->next)
            for (i = 0; i < count; i++)
                callback->callback(bytes[i], callback->data);
    } else {
        /*stream is not byte-aligned, so perform multiple writes*/
        for (i = 0; i < count; i++)
            bs->write(bs, 8, bytes[i]);
    }
}

void
bw_write_bytes_c(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count)
{
    bw_abort(bs);
}


void
bw_build(struct BitstreamWriter_s* stream, const char* format, ...)
{
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
                stream->write(stream, size, value);
            }
            break;
        case BS_INST_SIGNED:
            for (; times; times--) {
                const int value = va_arg(ap, int);
                stream->write_signed(stream, size, value);
            }
            break;
        case BS_INST_UNSIGNED64:
            for (; times; times--) {
                const uint64_t value = va_arg(ap, uint64_t);
                stream->write_64(stream, size, value);
            }
            break;
        case BS_INST_SIGNED64:
            for (; times; times--) {
                const int64_t value = va_arg(ap, int64_t);
                stream->write_signed_64(stream, size, value);
            }
            break;
        case BS_INST_SKIP:
            for (; times; times--) {
                stream->write(stream, size, 0);
            }
            break;
        case BS_INST_SKIP_BYTES:
            for (; times; times--) {
                /*somewhat inefficient,
                  but byte skipping is rare for BitstreamWriters anyway*/
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
                stream->write(stream, size, 0);
            }
            break;
        case BS_INST_BYTES:
            for (; times; times--) {
                const uint8_t *value = va_arg(ap, uint8_t*);
                stream->write_bytes(stream, value, size);
            }
            break;
        case BS_INST_ALIGN:
            stream->byte_align(stream);
            break;
        case BS_INST_EOF:
            break;
        }
    } while (inst != BS_INST_EOF);
    va_end(ap);
}

int
bw_byte_aligned_f_e_r(const BitstreamWriter *bs)
{
    return (bs->buffer_size == 0);
}

int
bw_byte_aligned_c(const BitstreamWriter *bs)
{
    return 1;
}


void
bw_byte_align_f_e_r(BitstreamWriter* bs)
{
    /*write enough 0 bits to completely fill the buffer
      which results in a byte being written*/
    if (bs->buffer_size > 0)
        bs->write(bs, 8 - bs->buffer_size, 0);
}

void
bw_byte_align_c(BitstreamWriter* bs)
{
    bw_abort(bs);
}


void
bw_flush_f(BitstreamWriter* bs)
{
    fflush(bs->output.file);
}

void
bw_flush_e(BitstreamWriter* bs)
{
    if (ext_flush_w(bs->output.external)) {
        bw_abort(bs);
    }
}

void
bw_flush_r_c(BitstreamWriter* bs)
{
    /*recorders and accumulators are always flushed,
      closed streams do nothing when flushed*/
    return;
}


bw_pos_t*
bw_getpos_f(BitstreamWriter *bs)
{
    bw_pos_t* pos;

    assert(bw_byte_aligned_f_e_r(bs));

    pos = malloc(sizeof(bw_pos_t));
    pos->writer = bs;
    fgetpos(bs->output.file, &(pos->position.file));
    pos->del = bw_pos_del_f;
    return pos;
}

bw_pos_t*
bw_getpos_e(BitstreamWriter *bs)
{
    struct bw_external_output* output = bs->output.external;
    bw_pos_t* pos;
    void* ext_pos;

    assert(bw_byte_aligned_f_e_r(bs));

    if ((ext_pos = ext_getpos_w(output)) == NULL) {
        /*some error getting position*/
        bw_abort(bs);
    }

    pos = malloc(sizeof(bw_pos_t));
    pos->writer = bs;
    pos->position.external.pos = ext_pos;
    pos->position.external.free_pos = output->free_pos;
    pos->del = bw_pos_del_e;
    return pos;
}

bw_pos_t*
bw_getpos_r(BitstreamWriter *bs)
{
    bw_pos_t* pos;

    assert(bw_byte_aligned_f_e_r(bs));

    pos = malloc(sizeof(bw_pos_t));
    pos->writer = bs;
    bw_buf_getpos(bs->output.recorder, &pos->position.recorder);
    pos->del = bw_pos_del_r;
    return pos;
}

bw_pos_t*
bw_getpos_c(BitstreamWriter *bs)
{
    bw_abort(bs);
    return NULL;  /*shouldn't get here*/
}


void
bw_setpos_f(BitstreamWriter *bs, const bw_pos_t* pos)
{
    assert(pos->writer == bs);
    assert(bw_byte_aligned_f_e_r(bs));

    fsetpos(bs->output.file, &(pos->position.file));
}

void
bw_setpos_e(BitstreamWriter *bs, const bw_pos_t* pos)
{
    struct bw_external_output* output = bs->output.external;

    assert(pos->writer == bs);
    assert(bw_byte_aligned_f_e_r(bs));

    if (ext_setpos_w(output, pos->position.external.pos)) {
        bw_abort(bs);
    }
}

void
bw_setpos_r(BitstreamWriter *bs, const bw_pos_t* pos)
{
    assert(pos->writer == bs);
    assert(bw_byte_aligned_f_e_r(bs));

    if (bw_buf_setpos(bs->output.recorder, pos->position.recorder)) {
        /*this may happen if someone resets the stream
          and then tries to setpos afterward*/
        bw_abort(bs);
    }
}

void
bw_setpos_c(BitstreamWriter *bs, const bw_pos_t* pos)
{
    bw_abort(bs);
}


void
bw_pos_del_f(bw_pos_t* pos)
{
    free(pos);
}

void
bw_pos_del_e(bw_pos_t* pos)
{
    pos->position.external.free_pos(pos->position.external.pos);
    free(pos);
}

void
bw_pos_del_r(bw_pos_t* pos)
{
    free(pos);
}


void
bw_close_methods(BitstreamWriter* bs)
{
    /*swap read methods with closed methods that generate read errors*/
    bs->write = bw_write_bits_c;
    bs->write_64 = bw_write_bits64_c;
    bs->write_bytes = bw_write_bytes_c;
    bs->write_signed = bw_write_signed_bits_c;
    bs->write_signed_64 = bw_write_signed_bits64_c;
    bs->write_unary = bw_write_unary_c;
    bs->flush = bw_flush_r_c;
    bs->byte_aligned = bw_byte_aligned_c;
    bs->byte_align = bw_byte_align_c;
    bs->set_endianness = bw_set_endianness_c;
    bs->getpos = bw_getpos_c;
    bs->setpos = bw_setpos_c;
}


void
bw_close_internal_stream_f(BitstreamWriter* bs)
{
    /*perform fclose on FILE object
      which automatically flushes its output*/
    fclose(bs->output.file);

    /*swap write methods with closed methods*/
    bw_close_methods(bs);
    bs->close_internal_stream = bw_close_internal_stream_cf;
}

void
bw_close_internal_stream_cf(BitstreamWriter* bs)
{
    return;
}

void
bw_close_internal_stream_r(BitstreamRecorder* bs)
{
    bw_close_methods((BitstreamWriter*)bs);
}

void
bw_close_internal_stream_e(BitstreamWriter* bs)
{
    /*call .close() method (which automatically performs flush)
      not much we can do if an error occurs at this point*/
    (void)ext_close_w(bs->output.external);

    /*swap read methods with closed methods*/
    bw_close_methods(bs);
    bs->close_internal_stream = bw_close_internal_stream_cf;
}


void
bw_free_f(BitstreamWriter* bs)
{
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    /*deallocate callbacks*/
    while (bs->callbacks != NULL) {
        bs->pop_callback(bs, NULL);
    }

    /*deallocate exceptions*/
    if (bs->exceptions != NULL) {
        fprintf(stderr, "*** Warning: leftover etry entries on stack\n");
    }
    for (e_node = bs->exceptions; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate used exceptions*/
    for (e_node = bs->exceptions_used; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    /*deallocate the struct itself*/
    free(bs);
}

void
bw_free_r(BitstreamRecorder* bs)
{
    /*deallocate buffer*/
    bw_buf_free(bs->output.recorder);

    /*perform additional deallocations on rest of struct*/
    bw_free_f((BitstreamWriter*)bs);
}

void
bw_free_e(BitstreamWriter* bs)
{
    /*calls free function on user data*/
    ext_free_w(bs->output.external);

    /*perform additional deallocations on rest of struct*/
    bw_free_f(bs);
}

void
bw_close_f_e(BitstreamWriter* bs)
{
    bs->close_internal_stream(bs);
    bs->free(bs);
}

void
bw_close_r(BitstreamRecorder* bs)
{
    bs->close_internal_stream(bs);
    bs->free(bs);
}

unsigned int
bw_bits_written_r(const BitstreamRecorder* bs)
{
    return (unsigned int)(bw_buf_size(bs->output.recorder) * 8 +
                          bs->buffer_size);
}

unsigned int
bw_bytes_written_r(const BitstreamRecorder* bs)
{
    return bw_buf_size(bs->output.recorder);
}

void
bw_reset_r(BitstreamRecorder* bs)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    bw_buf_reset(bs->output.recorder);
}



void
bw_copy_r(const BitstreamRecorder* bs, BitstreamWriter* target)
{
    /*dump all the bytes from our internal buffer*/
    target->write_bytes(target, bs->data(bs), bs->bytes_written(bs));

    /*then dump remaining bits with a partial write() call*/
    if (bs->buffer_size > 0) {
        target->write(target,
                      bs->buffer_size,
                      bs->buffer & ((1 << bs->buffer_size) - 1));
    }
}


unsigned
bw_split_r(const BitstreamRecorder* bs,
           unsigned bytes,
           BitstreamWriter* target,
           BitstreamWriter* remainder)
{
    const BitstreamWriter* writer = (BitstreamWriter*)bs;

    const unsigned data_size = bs->bytes_written(bs);
    const unsigned to_target = MIN(bytes, data_size);
    const unsigned to_remainder = data_size - to_target;

    const uint8_t* data = bs->data(bs);
    const struct {
        unsigned int size;
        unsigned int value;
    } partial = {bs->buffer_size,
                 bs->buffer & ((1 << bs->buffer_size) - 1)};

    if ((writer == target) && (writer == remainder)) {
        /*nothing to do!*/
    } else if (writer == target) {
        /*copy tail of writer to "remainder" (if any) and shorten recorder*/
        if (remainder) {
            remainder->write_bytes(remainder, data + to_target, to_remainder);
            remainder->write(remainder, partial.size, partial.value);
        }
        target->buffer_size = 0;
        target->buffer = 0;
        target->output.recorder->max_pos = to_target;
        target->output.recorder->pos = MIN(target->output.recorder->pos,
                                           target->output.recorder->max_pos);
    } else if (writer == remainder) {
        /*copy head of writer to "target" (if any) and shift recorder down*/
        if (target) {
            target->write_bytes(target, data, to_target);
        }
        memmove(remainder->output.recorder->buffer,
                data + to_target,
                to_remainder);
        remainder->output.recorder->pos -= to_target;
        remainder->output.recorder->max_pos -= to_target;
    } else {
        /*copy head to "target" and remainder to "remainder" (if any)*/
        if (target) {
            target->write_bytes(target, data, to_target);
        }
        if (remainder) {
            remainder->write_bytes(remainder, data + to_target, to_remainder);
            remainder->write(remainder, partial.size, partial.value);
        }
    }

    return to_target;
}


const uint8_t*
bw_data_r(const BitstreamRecorder* bs)
{
    return bs->output.recorder->buffer;
}

void
bw_abort(BitstreamWriter *bs)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "*** Error: EOF encountered, aborting\n");
        abort();
    }
}


jmp_buf*
bw_try(BitstreamWriter *bs)
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
__bw_etry(BitstreamWriter *bs, const char *file, int lineno)
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
  void                                                           \
  FUNC_NAME(STREAM *bs, bs_callback_f callback, void *data)      \
  {                                                              \
      struct bs_callback callback_node;                          \
                                                                 \
      callback_node.callback = callback;                         \
      callback_node.data = data;                                 \
      PUSH_CALLBACK_FUNC(bs, &callback_node);                    \
  }
FUNC_ADD_CALLBACK(br_add_callback, br_push_callback, BitstreamReader)
FUNC_ADD_CALLBACK(bw_add_callback, bw_push_callback, BitstreamWriter)

#define FUNC_PUSH_CALLBACK(FUNC_NAME, STREAM)           \
  void                                                  \
  FUNC_NAME(STREAM *bs, struct bs_callback *callback)   \
  {                                                     \
      if (callback != NULL) {                           \
          struct bs_callback *callback_node =           \
            malloc(sizeof(struct bs_callback));         \
          callback_node->callback = callback->callback; \
          callback_node->data = callback->data;         \
          callback_node->next = bs->callbacks;          \
          bs->callbacks = callback_node;                \
      } \
  }
FUNC_PUSH_CALLBACK(br_push_callback, BitstreamReader)
FUNC_PUSH_CALLBACK(bw_push_callback, BitstreamWriter)

#define FUNC_POP_CALLBACK(FUNC_NAME, STREAM)                     \
  void                                                           \
  FUNC_NAME(STREAM *bs, struct bs_callback *callback)            \
  {                                                              \
      struct bs_callback *c_node = bs->callbacks;                \
      if (c_node != NULL) {                                      \
          if (callback != NULL) {                                \
              callback->callback = c_node->callback;             \
              callback->data = c_node->data;                     \
              callback->next = NULL;                             \
          }                                                      \
          bs->callbacks = c_node->next;                          \
          free(c_node);                                          \
      } else {                                                   \
          fprintf(stderr, "*** Warning: no callbacks to pop\n"); \
      }                                                          \
  }
FUNC_POP_CALLBACK(br_pop_callback, BitstreamReader)
FUNC_POP_CALLBACK(bw_pop_callback, BitstreamWriter)

#define FUNC_CALL_CALLBACKS(FUNC_NAME, STREAM)      \
  void                                              \
  FUNC_NAME(STREAM *bs, uint8_t byte)               \
  {                                                 \
      struct bs_callback *callback;                 \
      for (callback = bs->callbacks;                \
           callback != NULL;                        \
           callback = callback->next) {             \
          callback->callback(byte, callback->data); \
      }                                             \
  }
FUNC_CALL_CALLBACKS(br_call_callbacks, BitstreamReader)
FUNC_CALL_CALLBACKS(bw_call_callbacks, BitstreamWriter)


/*******************************************************************
 *                       read buffer-specific                      *
 *******************************************************************/

void
br_buf_extend(struct br_buffer *buf, const uint8_t *data, unsigned size)
{
    const unsigned new_size = buf->size + size;
    buf->data = realloc(buf->data, new_size);
    memcpy(buf->data + buf->size, data, size);
    buf->size = new_size;
}


unsigned
br_buf_read(struct br_buffer *buf, uint8_t *data, unsigned size)
{
    const unsigned remaining_space = buf->size - buf->pos;
    const unsigned to_read = MIN(size, remaining_space);
    memcpy(data, buf->data + buf->pos, to_read);
    buf->pos += to_read;
    return to_read;
}

int
br_buf_fseek(struct br_buffer *buf, long position, int whence)
{
    switch (whence) {
    case 0:  /*SEEK_SET*/
        if (position < 0) {
            /*can't seek before the beginning of the buffer*/
            return -1;
        } else if (position > buf->size) {
            /*can't seek past the end of the buffer*/
            return -1;
        } else {
            buf->pos = (unsigned)position;
            return 0;
        }
    case 1:  /*SEEK_CUR*/
        if ((position < 0) && (-position > buf->pos)) {
            /*can't seek past the beginning of the buffer*/
            return -1;
        } else if ((position > 0) && (position > (buf->size - buf->pos))) {
            /*can't seek past the end of the buffer*/
            return -1;
        } else {
            buf->pos += position;
            return 0;
        }
    case 2:  /*SEEK_END*/
        if (position > 0) {
            /*can't seek past the end of the buffer*/
            return -1;
        } else if (-position > buf->size) {
            /*can't seek past the beginning of the buffer*/
            return -1;
        } else {
            buf->pos = buf->size + (unsigned)position;
            return 0;
        }
    default:
        /*unknown "whence"*/
        return -1;
    }
}

/*******************************************************************
 *                       write buffer-specific                     *
 *******************************************************************/


void
bw_buf_write(struct bw_buffer* buf, const uint8_t *data, unsigned data_size)
{
    const unsigned available_bytes = buf->buffer_size - buf->pos;
    if (available_bytes < data_size) {
        buf->buffer_size += (data_size - available_bytes);
        buf->buffer = realloc(buf->buffer, buf->buffer_size);
    }
    memcpy(buf->buffer + buf->pos, data, data_size);
    buf->pos += data_size;
    buf->max_pos = MAX(buf->max_pos, buf->pos);
}

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

#ifndef STANDALONE

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
test_rec_split_dumps(bs_endianness endianness,
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
    br_pos_t* pos;
    struct sigaction new_action, old_action;

    struct huffman_frequency frequencies[] = {{3, 2, 0},
                                              {2, 2, 1},
                                              {1, 2, 2},
                                              {1, 3, 3},
                                              {0, 3, 4}};
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
    int bit;
    uint8_t sub_data[2];
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

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    bit = reader->read(reader, 1);
    assert(bit == 0);
    reader->unread(reader, bit);
    assert(reader->read(reader, 2) == 1);
    reader->byte_align(reader);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 8) == 0xB1);
    reader->unread(reader, 0);
    assert(reader->read(reader, 1) == 0);
    reader->unread(reader, 1);
    assert(reader->read(reader, 1) == 1);

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
    br_pos_t *pos;

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
}

void test_little_endian_reader(BitstreamReader* reader,
                               br_huffman_table_t table[]) {
    int bit;
    uint8_t sub_data[2];
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

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 1) == 1);
    bit = reader->read(reader, 1);
    assert(bit == 0);
    reader->unread(reader, bit);
    assert(reader->read(reader, 4) == 8);
    reader->byte_align(reader);

    reader->setpos(reader, pos1);
    assert(reader->read(reader, 8) == 0xB1);
    reader->unread(reader, 0);
    assert(reader->read(reader, 1) == 0);
    reader->unread(reader, 1);
    assert(reader->read(reader, 1) == 1);

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
    br_pos_t* pos;

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

    reader->unread(reader, 1); /*should do nothing*/

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
                            writer_perform_write_unary_0,
                            writer_perform_write_unary_1,
                            writer_perform_huffman,
                            writer_perform_write_bytes,
                            writer_perform_build_u,
                            writer_perform_build_U,
                            writer_perform_build_s,
                            writer_perform_build_S,
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

    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    sub_writer = bw_open_recorder(endianness);
    test_rec_split_dumps(endianness, writer, sub_writer);
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
        writer->byte_align(writer);            \
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
    uint64_t v1,v2,v3,v4,v5;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        v1 = 2;
        v2 = 6;
        v3 = 7;
        v4 = 5;
        v5 = 342977;
        break;
    case BS_LITTLE_ENDIAN:
        v1 = 1;
        v2 = 4;
        v3 = 13;
        v4 = 3;
        v5 = 395743;
        break;
    }

    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2U 3U 5U 3U 19U", v1, v2, v3, v4, v5);
    assert(writer->byte_aligned(writer) == 1);
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
    int64_t v1,v2,v3,v4,v5;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        v1 = -2;
        v2 = -2;
        v3 = 7;
        v4 = -3;
        v5 = -181311;
        break;
    case BS_LITTLE_ENDIAN:
        v1 = 1;
        v2 = -4;
        v3 = 13;
        v4 = 3;
        v5 = -128545;
        break;
    }

    assert(writer->byte_aligned(writer) == 1);
    writer->build(writer, "2S 3S 5S 3S 19S", v1, v2, v3, v4, v5);
    assert(writer->byte_aligned(writer) == 1);
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
    struct huffman_frequency frequencies[] = {{3, 2, 0},
                                              {2, 2, 1},
                                              {1, 2, 2},
                                              {1, 3, 3},
                                              {0, 3, 4}};
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

void
test_rec_split_dumps(bs_endianness endianness,
                     BitstreamWriter* writer,
                     BitstreamRecorder* recorder)
{
    BitstreamRecorder* dummy = bw_open_recorder(endianness);

    switch (endianness) {
    case BS_BIG_ENDIAN:
        recorder->write((BitstreamWriter*)recorder, 2, 2);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 6);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 5, 7);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 5);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 19, 342977);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        break;
    case BS_LITTLE_ENDIAN:
        recorder->write((BitstreamWriter*)recorder, 2, 1);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 4);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 5, 13);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 3, 3);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        recorder->write((BitstreamWriter*)recorder, 19, 395743);
        recorder->split(recorder, 0, (BitstreamWriter*)dummy, writer);
        recorder->reset(recorder);
        break;
    }

    dummy->close(dummy);
}


unsigned ext_fread_test(FILE* user_data,
                        uint8_t* buffer,
                        unsigned buffer_size)
{
    const size_t read = fread(buffer, sizeof(uint8_t), buffer_size, user_data);
    if (read >= 0) {
        return (unsigned)read;
    }else {
        return 0;
    }
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
