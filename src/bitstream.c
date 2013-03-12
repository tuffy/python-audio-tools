#include "bitstream.h"
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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

struct read_limited_unary {
    int continue_;
    int limit_reached;
    unsigned value;
    state_t state;
};

const struct read_bits read_bits_table[0x200][8] =
#include "read_bits_table.h"
    ;

const struct read_bits read_bits_table_le[0x200][8] =
#include "read_bits_table_le.h"
    ;

const struct unread_bit unread_bit_table[0x200][2] =
#include "unread_bit_table.h"
    ;

const struct unread_bit unread_bit_table_le[0x200][2] =
#include "unread_bit_table_le.h"
    ;

const struct read_unary read_unary_table[0x200][2] =
#include "read_unary_table.h"
    ;

const struct read_unary read_unary_table_le[0x200][2] =
#include "read_unary_table_le.h"
    ;

const struct read_limited_unary read_limited_unary_table[0x200][18] =
#include "read_limited_unary_table.h"
    ;

const struct read_limited_unary read_limited_unary_table_le[0x200][18] =
#include "read_limited_unary_table_le.h"
    ;


BitstreamReader*
br_open(FILE *f, bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
    bs->type = BR_FILE;
    bs->input.file = f;
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->marks = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;
    bs->marks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_f_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_f_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_f_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_f_be;
        bs->skip_unary = br_skip_unary_f_be;
        bs->read_limited_unary = br_read_limited_unary_f_be;
        bs->set_endianness = br_set_endianness_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_f_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_f_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_f_le;
        bs->skip_unary = br_skip_unary_f_le;
        bs->read_limited_unary = br_read_limited_unary_f_le;
        bs->set_endianness = br_set_endianness_f_le;
        break;
    }

    bs->skip_bytes = br_skip_bytes;
    bs->byte_align = br_byte_align;
    bs->read_huffman_code = br_read_huffman_code_f;
    bs->read_bytes = br_read_bytes_f;
    bs->parse = br_parse;
    bs->substream_append = br_substream_append_f;
    bs->close_internal_stream = br_close_internal_stream_f;
    bs->free = br_free_f;
    bs->close = br_close;
    bs->mark = br_mark_f;
    bs->rewind = br_rewind_f;
    bs->unmark = br_unmark_f;

    return bs;
}

BitstreamReader*
br_substream_new(bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
    bs->type = BR_SUBSTREAM;
    bs->input.substream = buf_new();
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->marks = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;
    bs->marks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_s_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_s_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_s_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_s_be;
        bs->skip_unary = br_skip_unary_s_be;
        bs->read_limited_unary = br_read_limited_unary_s_be;
        bs->set_endianness = br_set_endianness_s_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_s_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_s_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_s_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_s_le;
        bs->skip_unary = br_skip_unary_s_le;
        bs->read_limited_unary = br_read_limited_unary_s_le;
        bs->set_endianness = br_set_endianness_s_le;
        break;
    }

    bs->skip_bytes = br_skip_bytes;
    bs->byte_align = br_byte_align;
    bs->read_huffman_code = br_read_huffman_code_s;
    bs->read_bytes = br_read_bytes_s;
    bs->parse = br_parse;
    bs->substream_append = br_substream_append_s;
    bs->close_internal_stream = br_close_internal_stream_s;
    bs->free = br_free_s;
    bs->close = br_close;
    bs->mark = br_mark_s;
    bs->rewind = br_rewind_s;
    bs->unmark = br_unmark_s;

    return bs;
}

BitstreamReader*
br_open_buffer(struct bs_buffer* buffer, bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
    bs->type = BR_SUBSTREAM;
    bs->input.substream = buffer;
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->marks = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;
    bs->marks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_s_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_s_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_s_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_s_be;
        bs->skip_unary = br_skip_unary_s_be;
        bs->read_limited_unary = br_read_limited_unary_s_be;
        bs->set_endianness = br_set_endianness_s_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_s_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_s_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_s_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_s_le;
        bs->skip_unary = br_skip_unary_s_le;
        bs->read_limited_unary = br_read_limited_unary_s_le;
        bs->set_endianness = br_set_endianness_s_le;
        break;
    }

    bs->skip_bytes = br_skip_bytes;
    bs->byte_align = br_byte_align;
    bs->read_huffman_code = br_read_huffman_code_s;
    bs->read_bytes = br_read_bytes_s;
    bs->parse = br_parse;
    bs->substream_append = br_substream_append_s;
    bs->close_internal_stream = br_close_internal_stream_s;
    bs->free = br_free_f;
    bs->close = br_close;
    bs->mark = br_mark_s;
    bs->rewind = br_rewind_s;
    bs->unmark = br_unmark_s;

    return bs;
}

BitstreamReader*
br_open_external(void* user_data,
                 bs_endianness endianness,
                 ext_read_f read,
                 ext_close_f close,
                 ext_free_f free)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
    bs->type = BR_EXTERNAL;
    bs->input.external = ext_open_r(user_data, read, close, free);
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->marks = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;
    bs->marks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_e_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_e_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_e_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_e_be;
        bs->skip_unary = br_skip_unary_e_be;
        bs->read_limited_unary = br_read_limited_unary_e_be;
        bs->set_endianness = br_set_endianness_e_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_e_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_e_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_e_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_e_le;
        bs->skip_unary = br_skip_unary_e_le;
        bs->read_limited_unary = br_read_limited_unary_e_le;
        bs->set_endianness = br_set_endianness_e_le;
        break;
    }

    bs->skip_bytes = br_skip_bytes;
    bs->read_huffman_code = br_read_huffman_code_e;
    bs->byte_align = br_byte_align;
    bs->read_bytes = br_read_bytes_e;
    bs->parse = br_parse;
    bs->close_internal_stream = br_close_internal_stream_e;
    bs->free = br_free_e;
    bs->close = br_close;
    bs->mark = br_mark_e;
    bs->rewind = br_rewind_e;
    bs->unmark = br_unmark_e;
    bs->substream_append = br_substream_append_e;

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
                read_bits_table[result.state][MIN(count, 8) - 1];       \
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
FUNC_READ_BITS_BE(br_read_bits_s_be,
                  unsigned int, buf_getc, bs->input.substream)
FUNC_READ_BITS_LE(br_read_bits_s_le,
                  unsigned int, buf_getc, bs->input.substream)
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
FUNC_READ_BITS_BE(br_read_bits64_s_be,
                  uint64_t, buf_getc, bs->input.substream)
FUNC_READ_BITS_LE(br_read_bits64_s_le,
                  uint64_t, buf_getc, bs->input.substream)
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

#define BUFFER_SIZE 4096

/*the skip_bits functions differ from the read_bits functions
  in that they have no accumulator
  which allows them to skip over a potentially unlimited amount of bits*/
void
br_skip_bits_f_be(BitstreamReader* bs, unsigned int count)
{
    /*handle a common case where the input is byte-aligned,
      the count is an even number of bytes
      and there are no set callbacks to consider*/
    if ((bs->state == 0) && ((count % 8) == 0) && (bs->callbacks == NULL)) {
        while (count > 0) {
            const unsigned int to_read = MIN(BUFFER_SIZE, count / 8);
            static uint8_t dummy[BUFFER_SIZE];

            if (fread(dummy, sizeof(uint8_t), to_read, bs->input.file) !=
                to_read)
                br_abort(bs);
            else
                count -= (to_read * 8);
        }
    } else {
        struct read_bits result = {0, 0, bs->state};

        while (count > 0) {
            if (result.state == 0) {
                const int byte = fgetc(bs->input.file);
                if (byte != EOF) {
                    struct bs_callback* callback;
                    result.state = NEW_STATE(byte);
                    for (callback = bs->callbacks;
                         callback != NULL;
                         callback = callback->next)
                         callback->callback((uint8_t)byte,
                                            callback->data);
                } else {
                    br_abort(bs);
                }
            }

            result =
                read_bits_table[result.state][MIN(count, 8) - 1];

            count -= result.value_size;
        }

        bs->state = result.state;
    }
}

void
br_skip_bits_f_le(BitstreamReader* bs, unsigned int count)
{
    /*handle a common case where the input is byte-aligned,
      the count is an even number of bytes
      and there are no set callbacks to consider*/
    if ((bs->state == 0) && ((count % 8) == 0) && (bs->callbacks == NULL)) {
        while (count > 0) {
            const unsigned int to_read = MIN(BUFFER_SIZE, count / 8);
            static uint8_t dummy[BUFFER_SIZE];

            if (fread(dummy, sizeof(uint8_t), to_read, bs->input.file) !=
                to_read)
                br_abort(bs);
            else
                count -= (to_read * 8);
        }
    } else {
        struct read_bits result = {0, 0, bs->state};

        while (count > 0) {
            if (result.state == 0) {
                const int byte = fgetc(bs->input.file);
                if (byte != EOF) {
                    struct bs_callback* callback;
                    result.state = NEW_STATE(byte);
                    for (callback = bs->callbacks;
                         callback != NULL;
                         callback = callback->next)
                         callback->callback((uint8_t)byte,
                                            callback->data);
                } else {
                    br_abort(bs);
                }
            }

            result =
                read_bits_table_le[result.state][MIN(count, 8) - 1];

            count -= result.value_size;
        }

        bs->state = result.state;
    }
}

void
br_skip_bits_s_be(BitstreamReader* bs, unsigned int count)
{
    /*handle a common case where the input is byte-aligned,
      the count is an even number of bytes
      and there are no set callbacks to consider*/
    if ((bs->state == 0) && ((count % 8) == 0) && (bs->callbacks == NULL)) {
        count /= 8;
        if (count <= BUF_WINDOW_SIZE(bs->input.substream)) {
            bs->input.substream->window_start += count;
        } else {
            br_abort(bs);
        }
    } else {
        struct read_bits result = {0, 0, bs->state};

        while (count > 0) {
            if (result.state == 0) {
                const int byte = buf_getc(bs->input.substream);
                if (byte != EOF) {
                    struct bs_callback* callback;
                    result.state = NEW_STATE(byte);
                    for (callback = bs->callbacks;
                         callback != NULL;
                         callback = callback->next)
                         callback->callback((uint8_t)byte,
                                            callback->data);
                } else {
                    br_abort(bs);
                }
            }

            result =
                read_bits_table[result.state][MIN(count, 8) - 1];

            count -= result.value_size;
        }

        bs->state = result.state;
    }
}

void
br_skip_bits_s_le(BitstreamReader* bs, unsigned int count)
{
    /*handle a common case where the input is byte-aligned,
      the count is an even number of bytes
      and there are no set callbacks to consider*/
    if ((bs->state == 0) && ((count % 8) == 0) && (bs->callbacks == NULL)) {
        count /= 8;
        if (count <= BUF_WINDOW_SIZE(bs->input.substream)) {
            bs->input.substream->window_start += count;
        } else {
            br_abort(bs);
        }
    } else {
        struct read_bits result = {0, 0, bs->state};

        while (count > 0) {
            if (result.state == 0) {
                const int byte = buf_getc(bs->input.substream);
                if (byte != EOF) {
                    struct bs_callback* callback;
                    result.state = NEW_STATE(byte);
                    for (callback = bs->callbacks;
                         callback != NULL;
                         callback = callback->next)
                         callback->callback((uint8_t)byte,
                                            callback->data);
                } else {
                    br_abort(bs);
                }
            }

            result =
                read_bits_table_le[result.state][MIN(count, 8) - 1];

            count -= result.value_size;
        }

        bs->state = result.state;
    }
}

void
br_skip_bits_e_be(BitstreamReader* bs, unsigned int count)
{
    /*handle common case where input is byte-aligned,
      the count is an even number of bytes
      and there are no set callbacks to consider*/
    if ((bs->state == 0) && ((count % 8) == 0) && (bs->callbacks == NULL)) {
        while (count > 0) {
            const unsigned int to_read = MIN(BUFFER_SIZE, count / 8);
            static uint8_t dummy[BUFFER_SIZE];

            if (ext_fread(bs->input.external, dummy, to_read) != to_read)
                br_abort(bs);
            else
                count -= (to_read * 8);
        }
    } else {
        struct read_bits result = {0, 0, bs->state};

        while (count > 0) {
            if (result.state == 0) {
                const int byte = ext_getc(bs->input.external);
                if (byte != EOF) {
                    struct bs_callback* callback;
                    result.state = NEW_STATE(byte);
                    for (callback = bs->callbacks;
                         callback != NULL;
                         callback = callback->next)
                         callback->callback((uint8_t)byte,
                                            callback->data);
                } else {
                    br_abort(bs);
                }
            }

            result =
                read_bits_table[result.state][MIN(count, 8) - 1];

            count -= result.value_size;
        }

        bs->state = result.state;
    }
}

void
br_skip_bits_e_le(BitstreamReader* bs, unsigned int count)
{
    /*handle common case where input is byte-aligned,
      the count is an even number of bytes
      and there are no set callbacks to consider*/
    if ((bs->state == 0) && ((count % 8) == 0) && (bs->callbacks == NULL)) {
        while (count > 0) {
            const unsigned int to_read = MIN(BUFFER_SIZE, count / 8);
            static uint8_t dummy[BUFFER_SIZE];

            if (ext_fread(bs->input.external, dummy, to_read) != to_read)
                br_abort(bs);
            else
                count -= (to_read * 8);
        }
    } else {
        struct read_bits result = {0, 0, bs->state};

        while (count > 0) {
            if (result.state == 0) {
                const int byte = ext_getc(bs->input.external);
                if (byte != EOF) {
                    struct bs_callback* callback;
                    result.state = NEW_STATE(byte);
                    for (callback = bs->callbacks;
                         callback != NULL;
                         callback = callback->next)
                         callback->callback((uint8_t)byte,
                                            callback->data);
                } else {
                    br_abort(bs);
                }
            }

            result =
                read_bits_table_le[result.state][MIN(count, 8) - 1];

            count -= result.value_size;
        }

        bs->state = result.state;
    }
}

void
br_skip_bits_c(BitstreamReader* bs, unsigned int count)
{
    br_abort(bs);
}


void
br_skip_bytes(BitstreamReader* bs, unsigned int count)
{
    /*try to generate large, byte-aligned chunks of bit skips*/
    while (count > 0) {
        const unsigned bytes_to_skip = MIN(0x10000000, count);
        bs->skip(bs, bytes_to_skip * 8);
        count -= bytes_to_skip;
    }
}


void
br_unread_bit_be(BitstreamReader* bs, int unread_bit)
{
    struct unread_bit result = unread_bit_table[bs->state][unread_bit];
    assert(result.limit_reached == 0);
    bs->state = result.state;
}

void
br_unread_bit_le(BitstreamReader* bs, int unread_bit)
{
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
                fgetc, bs->input.file, read_unary_table)
FUNC_READ_UNARY(br_read_unary_f_le,
                fgetc, bs->input.file, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_s_be,
                buf_getc, bs->input.substream, read_unary_table)
FUNC_READ_UNARY(br_read_unary_s_le,
                buf_getc, bs->input.substream, read_unary_table_le)
FUNC_READ_UNARY(br_read_unary_e_be,
                ext_getc, bs->input.external, read_unary_table)
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
                fgetc, bs->input.file, read_unary_table)
FUNC_SKIP_UNARY(br_skip_unary_f_le,
                fgetc, bs->input.file, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_s_be,
                buf_getc, bs->input.substream, read_unary_table)
FUNC_SKIP_UNARY(br_skip_unary_s_le,
                buf_getc, bs->input.substream, read_unary_table_le)
FUNC_SKIP_UNARY(br_skip_unary_e_be,
                ext_getc, bs->input.external, read_unary_table)
FUNC_SKIP_UNARY(br_skip_unary_e_le,
                ext_getc, bs->input.external, read_unary_table_le)

void
br_skip_unary_c(BitstreamReader* bs, int stop_bit)
{
    br_abort(bs);
}



#define FUNC_READ_LIMITED_UNARY(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG, UNARY_TABLE) \
    int                                                                 \
    FUNC_NAME(BitstreamReader* bs, int stop_bit, int maximum_bits)      \
    {                                                                   \
        struct read_limited_unary result = {0, 0, 0, bs->state};        \
        register int accumulator = 0;                                   \
                                                                        \
        assert(maximum_bits > 0);                                       \
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
            result = UNARY_TABLE[result.state][(stop_bit * 9) +         \
                                               MIN(maximum_bits, 8)];   \
                                                                        \
            accumulator += result.value;                                \
            maximum_bits -= result.value;                               \
        } while (result.continue_);                                     \
                                                                        \
        bs->state = result.state;                                       \
                                                                        \
        if (result.limit_reached) {                                     \
            /*maximum_bits reached*/                                    \
            return -1;                                                  \
        } else {                                                        \
            /*stop bit reached*/                                        \
            return accumulator;                                         \
        }                                                               \
    }

FUNC_READ_LIMITED_UNARY(br_read_limited_unary_f_be,
                        fgetc, bs->input.file, read_limited_unary_table)
FUNC_READ_LIMITED_UNARY(br_read_limited_unary_f_le,
                        fgetc, bs->input.file, read_limited_unary_table_le)
FUNC_READ_LIMITED_UNARY(br_read_limited_unary_s_be,
                        buf_getc, bs->input.substream,
                        read_limited_unary_table)
FUNC_READ_LIMITED_UNARY(br_read_limited_unary_s_le,
                        buf_getc, bs->input.substream,
                        read_limited_unary_table_le)
FUNC_READ_LIMITED_UNARY(br_read_limited_unary_e_be,
                        ext_getc, bs->input.external,
                        read_limited_unary_table)
FUNC_READ_LIMITED_UNARY(br_read_limited_unary_e_le,
                        ext_getc, bs->input.external,
                        read_limited_unary_table_le)

int
br_read_limited_unary_c(BitstreamReader* bs, int stop_bit, int maximum_bits)
{
    br_abort(bs);
    return 0;
}


#define FUNC_READ_HUFFMAN_CODE(FUNC_NAME, BYTE_FUNC, BYTE_FUNC_ARG) \
    int                                                             \
    FUNC_NAME(BitstreamReader *bs,                                  \
              struct br_huffman_table table[][0x200])               \
    {                                                               \
        struct br_huffman_table entry = table[0][bs->state];        \
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
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_s, buf_getc, bs->input.substream)
FUNC_READ_HUFFMAN_CODE(br_read_huffman_code_e, ext_getc, bs->input.external)

int
br_read_huffman_code_c(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200])
{
    br_abort(bs);
    return 0;
}

void
br_byte_align(BitstreamReader* bs)
{
    bs->state = 0;
}


void
br_read_bytes_f(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count)
{
    unsigned int i;

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
                 callback = callback->next)
                for (i = 0; i < byte_count; i++)
                    callback->callback(bytes[i], callback->data);
        } else {
            br_abort(bs);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (i = 0; i < byte_count; i++)
            bytes[i] = bs->read(bs, 8);
    }
}

void
br_read_bytes_s(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count)
{
    unsigned int i;

    if (bs->state == 0) {
        /*stream is byte-aligned, so perform optimized read*/

        /*buf_read bytes from buffer to output*/
        if ((unsigned int)buf_read(bs->input.substream,
                                   bytes,
                                   byte_count) == byte_count) {
            struct bs_callback* callback;
            /*if sufficient bytes were read
              perform callbacks on the read bytes*/
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                for (i = 0; i < byte_count; i++)
                    callback->callback(bytes[i], callback->data);
        } else {
            br_abort(bs);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (i = 0; i < byte_count; i++)
            bytes[i] = bs->read(bs, 8);
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
        unsigned i;

        /*stream is not byte-aligned, so perform multiple reads*/
        for (i = 0; i < byte_count; i++)
            bytes[i] = bs->read(bs, 8);
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
br_parse(struct BitstreamReader_s* stream, const char* format, ...)
{
    va_list ap;
    bs_instruction_t inst;

    va_start(ap, format);
    do {
        unsigned times;
        unsigned size;

        format = bs_parse_format(format, &times, &size, &inst);
        if (inst == BS_INST_UNSIGNED) {
            for (; times; times--) {
                unsigned *value = va_arg(ap, unsigned*);
                *value = stream->read(stream, size);
            }
        } else if (inst == BS_INST_SIGNED) {
            for (; times; times--) {
                int *value = va_arg(ap, int*);
                *value = stream->read_signed(stream, size);
            }
        } else if (inst == BS_INST_UNSIGNED64) {
            for (; times; times--) {
                uint64_t *value = va_arg(ap, uint64_t*);
                *value = stream->read_64(stream, size);
            }
        } else if (inst == BS_INST_SIGNED64) {
            for (; times; times--) {
                int64_t *value = va_arg(ap, int64_t*);
                *value = stream->read_signed_64(stream, size);
            }
        } else if (inst == BS_INST_SKIP) {
            for (; times; times--) {
                stream->skip(stream, size);
            }
        } else if (inst == BS_INST_SKIP_BYTES) {
            for (; times; times--) {
                stream->skip_bytes(stream, size);
            }
        } else if (inst == BS_INST_BYTES) {
            for (; times; times--) {
                uint8_t *value = va_arg(ap, uint8_t*);
                stream->read_bytes(stream, value, size);
            }
        } else if (inst == BS_INST_ALIGN) {
            stream->byte_align(stream);
        }
    } while (inst != BS_INST_EOF);
    va_end(ap);
}


void
br_set_endianness_f_be(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_f_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_f_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_f_le;
        bs->skip_unary = br_skip_unary_f_le;
        bs->read_limited_unary = br_read_limited_unary_f_le;
        bs->set_endianness = br_set_endianness_f_le;
    }
}

void
br_set_endianness_f_le(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_f_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_f_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_f_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_f_be;
        bs->skip_unary = br_skip_unary_f_be;
        bs->read_limited_unary = br_read_limited_unary_f_be;
        bs->set_endianness = br_set_endianness_f_be;
    }
}

void
br_set_endianness_s_be(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_s_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_s_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_s_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_s_le;
        bs->skip_unary = br_skip_unary_s_le;
        bs->read_limited_unary = br_read_limited_unary_s_le;
        bs->set_endianness = br_set_endianness_s_le;
    }
}

void
br_set_endianness_s_le(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_s_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_s_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_s_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_s_be;
        bs->skip_unary = br_skip_unary_s_be;
        bs->read_limited_unary = br_read_limited_unary_s_be;
        bs->set_endianness = br_set_endianness_s_be;
    }
}

void
br_set_endianness_e_be(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_e_le;
        bs->read_signed = br_read_signed_bits_le;
        bs->read_64 = br_read_bits64_e_le;
        bs->read_signed_64 = br_read_signed_bits64_le;
        bs->skip = br_skip_bits_e_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_e_le;
        bs->skip_unary = br_skip_unary_e_le;
        bs->read_limited_unary = br_read_limited_unary_e_le;
        bs->set_endianness = br_set_endianness_e_le;
    }
}

void
br_set_endianness_e_le(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_e_be;
        bs->read_signed = br_read_signed_bits_be;
        bs->read_64 = br_read_bits64_e_be;
        bs->read_signed_64 = br_read_signed_bits64_be;
        bs->skip = br_skip_bits_e_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_e_be;
        bs->skip_unary = br_skip_unary_e_be;
        bs->read_limited_unary = br_read_limited_unary_e_be;
        bs->set_endianness = br_set_endianness_e_be;
    }
}


void
br_set_endianness_c(BitstreamReader *bs, bs_endianness endianness)
{
    return;
}


void
br_close_methods(BitstreamReader* bs)
{
    /*swap read methods with closed methods that generate read errors*/
    bs->read = br_read_bits_c;
    bs->read_64 = br_read_bits64_c;
    bs->skip = br_skip_bits_c;
    bs->unread = br_unread_bit_c;
    bs->read_unary = br_read_unary_c;
    bs->skip_unary = br_skip_unary_c;
    bs->read_limited_unary = br_read_limited_unary_c;
    bs->read_huffman_code = br_read_huffman_code_c;
    bs->read_bytes = br_read_bytes_c;
    bs->set_endianness = br_set_endianness_c;
    bs->close_internal_stream = br_close_internal_stream_c;
    bs->mark = br_mark_c;
    bs->rewind = br_rewind_c;
    bs->unmark = br_unmark_c;
    bs->substream_append = br_substream_append_c;
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
br_close_internal_stream_s(BitstreamReader* bs)
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
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;
    struct br_mark *m_node;
    struct br_mark *m_next;

    /*deallocate callbacks*/
    for (c_node = bs->callbacks; c_node != NULL; c_node = c_next) {
        c_next = c_node->next;
        free(c_node);
    }

    /*deallocate used callbacks*/
    for (c_node = bs->callbacks_used; c_node != NULL; c_node = c_next) {
        c_next = c_node->next;
        free(c_node);
    }

    /*deallocate exceptions*/
    if (bs->exceptions != NULL) {
        fprintf(stderr, "Warning: leftover etry entries on stack\n");
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

    /*dealloate marks*/
    if (bs->marks != NULL) {
        fprintf(stderr, "Warning: leftover marks on stack\n");
    }
    for (m_node = bs->marks; m_node != NULL; m_node = m_next) {
        m_next = m_node->next;
        free(m_node);
    }

    /*deallocate used marks*/
    for (m_node = bs->marks_used; m_node != NULL; m_node = m_next) {
        m_next = m_node->next;
        free(m_node);
    }

    /*deallocate the struct itself*/
    free(bs);
}

void
br_free_s(BitstreamReader* bs)
{
    /*deallocate buffer*/
    buf_close(bs->input.substream);

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



void
br_mark_f(BitstreamReader* bs)
{
    struct br_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct br_mark));
    else {
        mark = bs->marks_used;
        bs->marks_used = bs->marks_used->next;
    }

    fgetpos(bs->input.file, &(mark->position.file));
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
}

void
br_mark_s(BitstreamReader* bs)
{
    struct br_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct br_mark));
    else {
        mark = bs->marks_used;
        bs->marks_used = bs->marks_used->next;
    }

    buf_set_rewindable(bs->input.substream, 1);
    buf_getpos(bs->input.substream, &(mark->position.substream));
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
}

void
br_mark_e(BitstreamReader* bs)
{
    struct br_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct br_mark));
    else {
        mark = bs->marks_used;
        bs->marks_used = bs->marks_used->next;
    }

    buf_set_rewindable(bs->input.external->buffer, 1);
    buf_getpos(bs->input.external->buffer, &(mark->position.external));
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
}

void
br_mark_c(BitstreamReader* bs)
{
    return;
}

void
br_rewind_f(BitstreamReader* bs)
{
    if (bs->marks != NULL) {
        fsetpos(bs->input.file, &(bs->marks->position.file));
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

void
br_rewind_s(BitstreamReader* bs)
{
    if (bs->marks != NULL) {
        buf_setpos(bs->input.substream, bs->marks->position.substream);
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

void
br_rewind_e(BitstreamReader* bs)
{
    if (bs->marks != NULL) {
        buf_setpos(bs->input.external->buffer, bs->marks->position.external);
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

void
br_rewind_c(BitstreamReader* bs)
{
    return;
}

void
br_unmark_f(BitstreamReader* bs)
{
    struct br_mark* mark = bs->marks;
    if (mark != NULL) {
        bs->marks = mark->next;
        mark->next = bs->marks_used;
        bs->marks_used = mark;
    } else {
        fprintf(stderr, "No marks on stack to remove!\n");
    }
}

void
br_unmark_s(BitstreamReader* bs)
{
    struct br_mark* mark = bs->marks;
    if (mark != NULL) {
        bs->marks = mark->next;
        mark->next = bs->marks_used;
        bs->marks_used = mark;
        buf_set_rewindable(bs->input.substream, bs->marks != NULL);
    } else {
        fprintf(stderr, "No marks on stack to remove!\n");
    }
}

void
br_unmark_e(BitstreamReader* bs)
{
    struct br_mark* mark = bs->marks;
    if (mark != NULL) {
        bs->marks = mark->next;
        mark->next = bs->marks_used;
        bs->marks_used = mark;
        buf_set_rewindable(bs->input.external->buffer, bs->marks != NULL);
    } else {
        fprintf(stderr, "No marks on stack to remove!\n");
    }
}

void
br_unmark_c(BitstreamReader* bs)
{
    return;
}

void
br_substream_append_f(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      unsigned bytes)
{
    struct bs_buffer *output;
    assert(substream->type == BR_SUBSTREAM);
    output = substream->input.substream;

    /*byte align the input stream*/
    stream->state = 0;

    while (bytes) {
        const unsigned to_read = MIN(bytes, BUFFER_SIZE);
        uint8_t *output_buffer;
        /*make sure to resize *before* getting window_end
          in case realloc moves the buffer data*/
        buf_resize(output, to_read);
        output_buffer = BUF_WINDOW_END(output);

        if (fread(output_buffer,
                  sizeof(uint8_t),
                  to_read,
                  stream->input.file) == to_read) {
            struct bs_callback *callback;

            /*perform callbacks on newly read bytes*/
            for (callback = stream->callbacks;
                 callback != NULL;
                 callback = callback->next) {
                unsigned i;
                for (i = 0; i < bytes; i++)
                    callback->callback(output_buffer[i], callback->data);
            }

            /*increment window_end to accomodate new data*/
            output->window_end += to_read;
            bytes -= to_read;
        } else {
            /*abort if the amount of read bytes is insufficient*/
            br_abort(stream);
        }
    }
}

void
br_substream_append_s(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      unsigned bytes)
{
    assert(substream->type = BR_SUBSTREAM);

    if (BUF_WINDOW_SIZE(stream->input.substream) >= bytes) {
        struct bs_buffer *input = stream->input.substream;
        const uint8_t *input_data = BUF_WINDOW_START(input);
        struct bs_callback *callback;

        /*byte align the input stream*/
        stream->state = 0;

        /*transfer data from input stream's buffer to output stream's buffer*/
        buf_write(substream->input.substream, input_data, bytes);

        /*perform callbacks on read bytes*/
        for (callback = stream->callbacks;
             callback != NULL;
             callback = callback->next) {
            unsigned i;

            for (i = 0; i < bytes; i++)
                callback->callback(input_data[i], callback->data);
        }

        /*remove bytes from input stream's buffer*/
        input->window_start += bytes;
    } else {
        /*abort if there's insufficient bytes remaining
          in the input stream to pass to the output stream*/
        br_abort(stream);
    }
}

void
br_substream_append_e(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      unsigned bytes)
{
    struct bs_buffer *output;
    assert(substream->type == BR_SUBSTREAM);
    output = substream->input.substream;

    /*byte align the input stream*/
    stream->state = 0;

    while (bytes) {
        const unsigned to_read = MIN(bytes, BUFFER_SIZE);
        uint8_t *output_buffer;
        /*make sure to resize *before* getting window_end
          in case realloc moves the buffer data*/
        buf_resize(output, to_read);
        output_buffer = BUF_WINDOW_END(output);

        if (ext_fread(stream->input.external,
                      output_buffer,
                      to_read) == to_read) {
            struct bs_callback *callback;

            /*perform callbacks on newly read bytes*/
            for (callback = stream->callbacks;
                 callback != NULL;
                 callback = callback->next) {
                unsigned i;
                for (i = 0; i < bytes; i++)
                    callback->callback(output_buffer[i], callback->data);
            }

            /*increment window_end to accomodate new data*/
            output->window_end += to_read;
            bytes -= to_read;
        } else {
            /*abort if the amount of read bytes is insufficient*/
            br_abort(stream);
        }
    }
}

void
br_substream_append_c(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      unsigned bytes)
{
    br_abort(stream);
}


void
br_add_callback(BitstreamReader *bs, bs_callback_f callback, void *data)
{
    struct bs_callback *callback_node;

    if (bs->callbacks_used == NULL)
        callback_node = malloc(sizeof(struct bs_callback));
    else {
        callback_node = bs->callbacks_used;
        bs->callbacks_used = bs->callbacks_used->next;
    }
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = bs->callbacks;
    bs->callbacks = callback_node;
}

void
br_call_callbacks(BitstreamReader *bs, uint8_t byte)
{
    struct bs_callback *callback;
    for (callback = bs->callbacks;
         callback != NULL;
         callback = callback->next)
        callback->callback(byte, callback->data);
}

void
br_pop_callback(BitstreamReader *bs, struct bs_callback *callback)
{
    struct bs_callback *c_node = bs->callbacks;
    if (c_node != NULL) {
        if (callback != NULL) {
            callback->callback = c_node->callback;
            callback->data = c_node->data;
            callback->next = NULL;
        }
        bs->callbacks = c_node->next;
        c_node->next = bs->callbacks_used;
        bs->callbacks_used = c_node;
    } else {
        fprintf(stderr, "Warning: no callbacks available to pop\n");
    }
}

void
br_push_callback(BitstreamReader *bs, struct bs_callback *callback)
{
    struct bs_callback *callback_node;

    if (callback != NULL) {
        if (bs->callbacks_used == NULL)
            callback_node = malloc(sizeof(struct bs_callback));
        else {
            callback_node = bs->callbacks_used;
            bs->callbacks_used = bs->callbacks_used->next;
        }
        callback_node->callback = callback->callback;
        callback_node->data = callback->data;
        callback_node->next = bs->callbacks;
        bs->callbacks = callback_node;
    }
}


void
br_abort(BitstreamReader *bs)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "EOF encountered, aborting\n");
        abort();
    }
}

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
br_etry(BitstreamReader *bs)
{
    struct bs_exception *node = bs->exceptions;
    if (node != NULL) {
        bs->exceptions = node->next;
        node->next = bs->exceptions_used;
        bs->exceptions_used = node;
    } else {
        fprintf(stderr, "Warning: trying to pop from empty etry stack\n");
    }
}

void
br_substream_reset(struct BitstreamReader_s *substream)
{
    struct br_mark *m_node;
    struct br_mark *m_next;

    assert(substream->type == BR_SUBSTREAM);

    substream->state = 0;
    /*transfer all marks to recycle stack*/
    for (m_node = substream->marks; m_node != NULL; m_node = m_next) {
        m_next = m_node->next;
        m_node->next = substream->marks_used;
        substream->marks_used = m_node;
    }
    substream->marks = NULL;

    buf_reset(substream->input.substream);
}


BitstreamWriter*
bw_open(FILE *f, bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_FILE;

    bs->output.file = f;
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_f_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->write_signed = bw_write_signed_bits_f_p_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_be;
        bs->set_endianness = bw_set_endianness_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_f_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->write_signed = bw_write_signed_bits_f_p_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_le;
        bs->set_endianness = bw_set_endianness_f_le;
        break;
    }

    bs->write_bytes = bw_write_bytes_f;
    bs->write_unary = bw_write_unary_f_p_r;
    bs->write_huffman_code = bw_write_huffman;
    bs->build = bw_build;
    bs->byte_align = bw_byte_align_f_p_r;
    bs->bits_written = bw_bits_written_f_p_c;
    bs->bytes_written = bw_bytes_written;
    bs->flush = bw_flush_f;
    bs->close_internal_stream = bw_close_internal_stream_f;
    bs->free = bw_free_f_a;
    bs->close = bw_close;

    return bs;
}

BitstreamWriter*
bw_open_external(void* user_data,
                 bs_endianness endianness,
                 unsigned buffer_size,
                 ext_write_f write,
                 ext_flush_f flush,
                 ext_close_f close,
                 ext_free_f free)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_EXTERNAL;

    bs->output.external = ext_open_w(user_data,
                                     buffer_size,
                                     write,
                                     flush,
                                     close,
                                     free);
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_e_be;
        bs->write_64 = bw_write_bits64_e_be;
        bs->write_signed = bw_write_signed_bits_f_p_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_be;
        bs->set_endianness = bw_set_endianness_e_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_e_le;
        bs->write_64 = bw_write_bits64_e_le;
        bs->write_signed = bw_write_signed_bits_f_p_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_le;
        bs->set_endianness = bw_set_endianness_e_le;
        break;
    }

    bs->write_bytes = bw_write_bytes_e;
    bs->write_unary = bw_write_unary_f_p_r;
    bs->write_huffman_code = bw_write_huffman;
    bs->build = bw_build;
    bs->byte_align = bw_byte_align_f_p_r;
    bs->bits_written = bw_bits_written_f_p_c;
    bs->bytes_written = bw_bytes_written;
    bs->flush = bw_flush_e;
    bs->close_internal_stream = bw_close_internal_stream_e;
    bs->free = bw_free_e;
    bs->close = bw_close;

    return bs;
}


BitstreamWriter*
bw_open_recorder(bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_RECORDER;

    bs->output.buffer = buf_new();
    bs->buffer_size = 0;
    bs->buffer = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_r_be;
        bs->write_64 = bw_write_bits64_r_be;
        bs->write_signed = bw_write_signed_bits_f_p_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_be;
        bs->set_endianness = bw_set_endianness_r_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_r_le;
        bs->write_64 = bw_write_bits64_r_le;
        bs->write_signed = bw_write_signed_bits_f_p_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_le;
        bs->set_endianness = bw_set_endianness_r_le;
        break;
    }

    bs->write_bytes = bw_write_bytes_r;
    bs->write_unary = bw_write_unary_f_p_r;
    bs->write_huffman_code = bw_write_huffman;
    bs->build = bw_build;
    bs->byte_align = bw_byte_align_f_p_r;
    bs->bits_written = bw_bits_written_r;
    bs->bytes_written = bw_bytes_written;
    bs->flush = bw_flush_r_a_c;
    bs->close_internal_stream = bw_close_internal_stream_r_a;
    bs->free = bw_free_r;
    bs->close = bw_close;

    return bs;
}

BitstreamWriter*
bw_open_accumulator(bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_ACCUMULATOR;

    bs->output.accumulator = 0;
    bs->buffer = 0;
    bs->buffer_size = 0;

    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;

    bs->write = bw_write_bits_a;
    bs->write_bytes = bw_write_bytes_a;
    bs->write_signed = bw_write_signed_bits_a;
    bs->write_64 = bw_write_bits64_a;
    bs->write_signed_64 = bw_write_signed_bits64_a;
    bs->write_unary = bw_write_unary_a;
    bs->write_huffman_code = bw_write_huffman;
    bs->build = bw_build;
    bs->byte_align = bw_byte_align_a;
    bs->set_endianness = bw_set_endianness_a;
    bs->bits_written = bw_bits_written_a;
    bs->bytes_written = bw_bytes_written;
    bs->flush = bw_flush_r_a_c;
    bs->close_internal_stream = bw_close_internal_stream_r_a;
    bs->free = bw_free_f_a;
    bs->close = bw_close;

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
                   unsigned int, buf_putc, bs->output.buffer)
FUNC_WRITE_BITS_LE(bw_write_bits_r_le,
                   unsigned int, buf_putc, bs->output.buffer)

void
bw_write_bits_a(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    assert(value < (1ll << count));
    bs->output.accumulator += count;
}

void
bw_write_bits_c(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    bw_abort(bs);
}



void
bw_write_signed_bits_f_p_r_be(BitstreamWriter* bs, unsigned int count,
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
bw_write_signed_bits_f_p_r_le(BitstreamWriter* bs, unsigned int count,
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
bw_write_signed_bits_a(BitstreamWriter* bs, unsigned int count, int value)
{
    assert(value <= ((1 << (count - 1)) - 1));
    assert(value >= -(1 << (count - 1)));
    bs->output.accumulator += count;
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
                   uint64_t, buf_putc, bs->output.buffer)
FUNC_WRITE_BITS_LE(bw_write_bits64_r_le,
                   uint64_t, buf_putc, bs->output.buffer)

void
bw_write_bits64_a(BitstreamWriter* bs, unsigned int count, uint64_t value)
{
    assert(count < 64 ? value < (int64_t)(1ll << count) : 1);
    bs->output.accumulator += count;
}

void
bw_write_bits64_c(BitstreamWriter* bs, unsigned int count, uint64_t value)
{
    bw_abort(bs);
}

void
bw_write_signed_bits64_f_p_r_be(BitstreamWriter* bs, unsigned int count,
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
bw_write_signed_bits64_f_p_r_le(BitstreamWriter* bs, unsigned int count,
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
bw_write_signed_bits64_a(BitstreamWriter* bs, unsigned int count,
                         int64_t value)
{
    assert(value <= ((1ll << (count - 1)) - 1));
    assert(value >= -(1ll << (count - 1)));
    bs->output.accumulator += count;
}

void
bw_write_signed_bits64_c(BitstreamWriter* bs, unsigned int count,
                         int64_t value)
{
    bw_abort(bs);
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
bw_write_bytes_r(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count)
{
    unsigned i;

    if (bs->buffer_size == 0) {
        struct bs_callback* callback;

        /*stream is byte aligned, so perform optimized write*/
        buf_write(bs->output.buffer, bytes, count);

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
        ext_fwrite(bs->output.external, bytes, count);

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
bw_write_bytes_a(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count) {
    bs->output.accumulator += (count * 8);
}

void
bw_write_bytes_c(BitstreamWriter* bs, const uint8_t* bytes,
                 unsigned int count)
{
    bw_abort(bs);
}

#define UNARY_BUFFER_SIZE 30

void
bw_write_unary_f_p_r(BitstreamWriter* bs, int stop_bit, unsigned int value)
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
bw_write_unary_a(BitstreamWriter* bs, int stop_bit, unsigned int value)
{
    assert(value >= 0);
    bs->output.accumulator += (value + 1);
}

void
bw_write_unary_c(BitstreamWriter* bs, int stop_bit, unsigned int value)
{
    bw_abort(bs);
}


int
bw_write_huffman(BitstreamWriter* bs,
                 struct bw_huffman_table* table,
                 int value)
{
    while (table != NULL) {
        if (value == table->value) {
            bs->write(bs, table->write_count, table->write_value);
            return 0;
        } else if (value < table->value) {
            table = table->left;
        } else {
            table = table->right;
        }
    }

    /*walked outside of the Huffman table, so return error*/
    return 1;
}

int
bw_write_huffman_c(BitstreamWriter* bs,
                   struct bw_huffman_table* table,
                   int value)
{
    bw_abort(bs);

    return 1;  /*won't get here*/
}



void
bw_byte_align_f_p_r(BitstreamWriter* bs) {
    /*write enough 0 bits to completely fill the buffer
      which results in a byte being written*/
    if (bs->buffer_size > 0)
        bs->write(bs, 8 - bs->buffer_size, 0);
}

void
bw_byte_align_a(BitstreamWriter* bs)
{
    if (bs->output.accumulator % 8)
        bs->output.accumulator += (8 - (bs->output.accumulator % 8));
}

void
bw_byte_align_c(BitstreamWriter* bs)
{
    bw_abort(bs);
}

void
bw_set_endianness_f_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_f_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->write_signed = bw_write_signed_bits_f_p_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_le;
        bs->set_endianness = bw_set_endianness_f_le;
    }
}

void
bw_set_endianness_f_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_f_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->write_signed = bw_write_signed_bits_f_p_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_be;
        bs->set_endianness = bw_set_endianness_f_be;
    }
}

void
bw_set_endianness_r_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_r_le;
        bs->write_64 = bw_write_bits64_r_le;
        bs->write_signed = bw_write_signed_bits_f_p_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_le;
        bs->set_endianness = bw_set_endianness_r_le;
    }
}

void
bw_set_endianness_r_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_r_be;
        bs->write_64 = bw_write_bits64_r_be;
        bs->write_signed = bw_write_signed_bits_f_p_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_be;
        bs->set_endianness = bw_set_endianness_r_be;
    }
}

void
bw_set_endianness_e_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_e_le;
        bs->write_64 = bw_write_bits64_e_le;
        bs->write_signed = bw_write_signed_bits_f_p_r_le;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_le;
        bs->set_endianness = bw_set_endianness_e_le;
    }
}

void
bw_set_endianness_e_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_e_be;
        bs->write_64 = bw_write_bits64_e_be;
        bs->write_signed = bw_write_signed_bits_f_p_r_be;
        bs->write_signed_64 = bw_write_signed_bits64_f_p_r_be;
        bs->set_endianness = bw_set_endianness_e_be;
    }
}


void
bw_set_endianness_a(BitstreamWriter* bs, bs_endianness endianness)
{
    /*swapping endianness results in a byte alignment*/
    bw_byte_align_a(bs);
}

void
bw_set_endianness_c(BitstreamWriter* bs, bs_endianness endianness)
{
    return;
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
        if (inst == BS_INST_UNSIGNED) {
            for (; times; times--) {
                const unsigned value = va_arg(ap, unsigned);
                stream->write(stream, size, value);
            }
        } else if (inst == BS_INST_SIGNED) {
            for (; times; times--) {
                const int value = va_arg(ap, int);
                stream->write_signed(stream, size, value);
            }
        } else if (inst == BS_INST_UNSIGNED64) {
            for (; times; times--) {
                const uint64_t value = va_arg(ap, uint64_t);
                stream->write_64(stream, size, value);
            }
        } else if (inst == BS_INST_SIGNED64) {
            for (; times; times--) {
                const int64_t value = va_arg(ap, int64_t);
                stream->write_signed_64(stream, size, value);
            }
        } else if (inst == BS_INST_SKIP) {
            for (; times; times--) {
                stream->write(stream, size, 0);
            }
        } else if (inst == BS_INST_SKIP_BYTES) {
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
        } else if (inst == BS_INST_BYTES) {
            for (; times; times--) {
                const uint8_t *value = va_arg(ap, uint8_t*);
                stream->write_bytes(stream, value, size);
            }
        } else if (inst == BS_INST_ALIGN) {
            stream->byte_align(stream);
        }
    } while (inst != BS_INST_EOF);
    va_end(ap);
}


unsigned int
bw_bits_written_f_p_c(BitstreamWriter* bs)
{
    /*actual file writing doesn't keep track of bits written
      since the total could be extremely large*/
    return 0;
}

unsigned int
bw_bits_written_r(BitstreamWriter* bs)
{
    return (BUF_WINDOW_SIZE(bs->output.buffer) * 8) + bs->buffer_size;
}

unsigned int
bw_bits_written_a(BitstreamWriter* bs)
{
    return bs->output.accumulator;
}

unsigned int
bw_bytes_written(BitstreamWriter* bs)
{
    return bs->bits_written(bs) / 8;
}


void
bw_flush_f(BitstreamWriter* bs)
{
    fflush(bs->output.file);
}

void
bw_flush_r_a_c(BitstreamWriter* bs)
{
    return;
}

void
bw_flush_e(BitstreamWriter* bs)
{
    ext_flush_w(bs->output.external);
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
    bs->write_huffman_code = bw_write_huffman_c;
    bs->flush = bw_flush_r_a_c;
    bs->byte_align = bw_byte_align_c;
    bs->set_endianness = bw_set_endianness_c;
    bs->close_internal_stream = bw_close_internal_stream_c;
}

void
bw_close_internal_stream_f(BitstreamWriter* bs)
{
    /*perform fclose on FILE object
      which automatically flushes its output*/
    fclose(bs->output.file);

    /*swap write methods with closed methods*/
    bw_close_methods(bs);
}

void
bw_close_internal_stream_r_a(BitstreamWriter* bs)
{
    bw_close_methods(bs);
}

void
bw_close_internal_stream_e(BitstreamWriter* bs)
{
    /*call .close() method (which automatically performs flush)*/
    ext_close_w(bs->output.external);

    /*swap read methods with closed methods*/
    bw_close_methods(bs);
}


void
bw_close_internal_stream_c(BitstreamWriter* bs)
{
    return;
}


void
bw_free_f_a(BitstreamWriter* bs)
{
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    /*deallocate callbacks*/
    for (c_node = bs->callbacks; c_node != NULL; c_node = c_next) {
        c_next = c_node->next;
        free(c_node);
    }

    /*deallocate used callbacks*/
    for (c_node = bs->callbacks_used; c_node != NULL; c_node = c_next) {
        c_next = c_node->next;
        free(c_node);
    }

    /*deallocate exceptions*/
    if (bs->exceptions != NULL) {
        fprintf(stderr, "Warning: leftover etry entries on stack\n");
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
bw_free_r(BitstreamWriter* bs)
{
    /*deallocate buffer*/
    buf_close(bs->output.buffer);

    /*perform additional deallocations on rest of struct*/
    bw_free_f_a(bs);
}

void
bw_free_e(BitstreamWriter* bs)
{
    /*flush pending data if necessary*/
    if (!bw_closed(bs)) {
        ext_flush_w(bs->output.external);
    }

    ext_free_w(bs->output.external);

    /*perform additional deallocations on rest of struct*/
    bw_free_f_a(bs);
}


void
bw_close(BitstreamWriter* bs)
{
    bs->close_internal_stream(bs);
    bs->free(bs);
}


void
bw_add_callback(BitstreamWriter *bs, bs_callback_f callback, void *data)
{
    struct bs_callback *callback_node = malloc(sizeof(struct bs_callback));
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = bs->callbacks;
    bs->callbacks = callback_node;
}

void
bw_pop_callback(BitstreamWriter* bs, struct bs_callback* callback) {
    struct bs_callback *c_node = bs->callbacks;
    if (c_node != NULL) {
        if (callback != NULL) {
            callback->callback = c_node->callback;
            callback->data = c_node->data;
            callback->next = NULL;
        }
        bs->callbacks = c_node->next;
        c_node->next = bs->callbacks_used;
        bs->callbacks_used = c_node;
    } else {
        fprintf(stderr, "warning: no callbacks available to pop\n");
    }
}

void
bw_push_callback(BitstreamWriter* bs, struct bs_callback* callback) {
    struct bs_callback *callback_node;

    if (callback != NULL) {
        if (bs->callbacks_used == NULL)
            callback_node = malloc(sizeof(struct bs_callback));
        else {
            callback_node = bs->callbacks_used;
            bs->callbacks_used = bs->callbacks_used->next;
        }
        callback_node->callback = callback->callback;
        callback_node->data = callback->data;
        callback_node->next = bs->callbacks;
        bs->callbacks = callback_node;
    }
}

void
bw_call_callbacks(BitstreamWriter *bs, uint8_t byte) {
    struct bs_callback *callback;
    for (callback = bs->callbacks;
         callback != NULL;
         callback = callback->next)
        callback->callback(byte, callback->data);
}


void
bw_abort(BitstreamWriter *bs)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "EOF encountered, aborting\n");
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
bw_etry(BitstreamWriter *bs)
{
    struct bs_exception *node = bs->exceptions;
    if (node != NULL) {
        bs->exceptions = node->next;
        node->next = bs->exceptions_used;
        bs->exceptions_used = node;
    } else {
        fprintf(stderr, "Warning: trying to pop from empty etry stack\n");
    }
}


void
bw_dump_bytes(BitstreamWriter* target,
              const uint8_t* buffer, unsigned int total) {
    unsigned int i;
    struct bs_callback* callback;

    if (bw_closed(target))
        bw_abort(target);

    if (total == 0) {
        /*short-circuit an empty write*/
        return;
    } else if (target->buffer_size == 0) {
        /*perform faster dumping if target is byte-aligned*/
        switch (target->type) {
        case BW_FILE:
            if (fwrite(buffer, sizeof(uint8_t),
                       total, target->output.file) != total)
                bw_abort(target);
            break;
        case BW_EXTERNAL:
            for (i = 0; i < total; i++)
                target->write(target, 8, buffer[i]);
            break;
        case BW_RECORDER:
            buf_write(target->output.buffer, buffer, total);
            break;
        case BW_ACCUMULATOR:
            target->output.accumulator += (total * 8);
            break;
        }

        /*perform callbacks from target on written bytes*/
        for (callback = target->callbacks;
             callback != NULL;
             callback = callback->next)
            for (i = 0; i < total; i++)
                callback->callback(buffer[i], callback->data);
    } else {
        /*otherwise, proceed on a byte-by-byte basis*/
        for (i = 0; i < total; i++)
            target->write(target, 8, buffer[i]);
    }
}


void
bw_rec_copy(BitstreamWriter* target, BitstreamWriter* source)
{
    assert(source->type == BW_RECORDER);

    if (bw_closed(source) || bw_closed(target))
        bw_abort(source);

    /*dump all the bytes from our internal buffer*/
    bw_dump_bytes(target,
                  BUF_WINDOW_START(source->output.buffer),
                  BUF_WINDOW_SIZE(source->output.buffer));

    /*then dump remaining bits (if any) with a partial write() call*/
    if (source->buffer_size > 0)
        target->write(target,
                      source->buffer_size,
                      source->buffer & ((1 << source->buffer_size) - 1));
}


unsigned int
bw_rec_split(BitstreamWriter* target,
             BitstreamWriter* remaining,
             BitstreamWriter* source,
             unsigned int total_bytes) {
    const uint8_t* buffer = BUF_WINDOW_START(source->output.buffer);
    const unsigned buffer_size = BUF_WINDOW_SIZE(source->output.buffer);
    const unsigned to_target = MIN(total_bytes, buffer_size);
    const unsigned to_remaining = buffer_size - to_target;

    assert(source->type == BW_RECORDER);

    if (bw_closed(target) || bw_closed(remaining) || bw_closed(source))
        bw_abort(source);

    /*first, dump up to "total_bytes" from source to "target"
      if available*/
    if (target != NULL) {
        bw_dump_bytes(target, buffer, to_target);
    }

    if (remaining != NULL) {
        if (remaining != source) {
            /*then, dump the remaining bytes from source to "remaining"
              if it is a separate writer*/
            bw_dump_bytes(remaining, buffer + to_target, to_remaining);

            if (source->buffer_size > 0)
                remaining->write(
                    remaining,
                    source->buffer_size,
                    source->buffer & ((1 << source->buffer_size) - 1));
        } else {
            /*if remaining is the same as source,
              shift source's output buffer down*/
            memmove(BUF_WINDOW_START(remaining->output.buffer),
                    buffer + to_target,
                    to_remaining);
            remaining->output.buffer->window_end -= to_target;
        }
    }

    return to_target;
}

void
bw_reset_recorder(BitstreamWriter* bs)
{
    assert(bs->type == BW_RECORDER);

    bs->buffer = 0;
    bs->buffer_size = 0;
    buf_reset(bs->output.buffer);
}

void
bw_swap_records(BitstreamWriter* a, BitstreamWriter* b)
{
    BitstreamWriter c;

    assert(a->type == BW_RECORDER);
    assert(b->type == BW_RECORDER);
    assert(a->write == b->write);  /*ensure they have the same endianness*/

    c.output.buffer = a->output.buffer;
    c.buffer_size = a->buffer_size;
    c.buffer = a->buffer;
    a->output.buffer = b->output.buffer;
    a->buffer_size = b->buffer_size;
    a->buffer = b->buffer;
    b->output.buffer = c.output.buffer;
    b->buffer_size = c.buffer_size;
    b->buffer = c.buffer;
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
byte_counter(uint8_t byte, void *total_bytes)
{
    unsigned int *u = total_bytes;
    *u += 1;
}


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
                       struct br_huffman_table (*table)[][0x200]);

void
test_big_endian_parse(BitstreamReader* reader);

void
test_little_endian_reader(BitstreamReader* reader,
                          struct br_huffman_table (*table)[][0x200]);

void
test_little_endian_parse(BitstreamReader* reader);

void
test_close_errors(BitstreamReader* reader,
                  struct br_huffman_table (*table)[][0x200]);

void
test_try(BitstreamReader* reader,
         struct br_huffman_table (*table)[][0x200]);

void
test_callbacks_reader(BitstreamReader* reader,
                      int unary_0_reads,
                      int unary_1_reads,
                      struct br_huffman_table (*table)[][0x200],
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
BitstreamWriter*
get_edge_writer_be(void);
BitstreamWriter*
get_edge_recorder_be(void);
BitstreamWriter*
get_edge_accumulator_be(void);

void
validate_edge_writer_be(BitstreamWriter* writer);
void
validate_edge_recorder_be(BitstreamWriter* recorder);
void
validate_edge_accumulator(BitstreamWriter* accumulator);

BitstreamWriter*
get_edge_writer_le(void);
BitstreamWriter*
get_edge_recorder_le(void);
BitstreamWriter*
get_edge_accumulator_le(void);

void
validate_edge_writer_le(BitstreamWriter* writer);
void
validate_edge_recorder_le(BitstreamWriter* recorder);

/*this uses "temp_filename" as an output file and opens it separately*/
void
test_writer(bs_endianness endianness);

void
test_rec_copy_dumps(bs_endianness endianness,
                    BitstreamWriter* writer,
                    BitstreamWriter* recorder);

void
test_rec_split_dumps(bs_endianness endianness,
                     BitstreamWriter* writer,
                     BitstreamWriter* recorder);

void
test_writer_close_errors(BitstreamWriter* writer);

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

int ext_fread_test(FILE* user_data, struct bs_buffer* buffer);

void ext_fclose_test(FILE* user_data);

void ext_ffree_test(FILE* user_data);

int ext_fwrite_test(FILE* user_data,
                    struct bs_buffer* buffer,
                    unsigned buffer_size);

void ext_fflush_test(FILE* user_data);


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

void check_alignment_a(const align_check* check,
                       bs_endianness endianness);

void check_alignment_e(const align_check* check,
                       bs_endianness endianness);

void func_add_one(uint8_t byte, int* value);
void func_add_two(uint8_t byte, int* value);
void func_mult_three(uint8_t byte, int* value);

void test_buffer();

int main(int argc, char* argv[]) {
    int fd;
    FILE* temp_file;
    FILE* temp_file2;
    BitstreamReader* reader;
    BitstreamReader* subreader;
    BitstreamReader* subsubreader;
    struct sigaction new_action, old_action;

    struct huffman_frequency frequencies[] = {{3, 2, 0},
                                              {2, 2, 1},
                                              {1, 2, 2},
                                              {1, 3, 3},
                                              {0, 3, 4}};
    struct br_huffman_table (*be_table)[][0x200];
    struct br_huffman_table (*le_table)[][0x200];
    struct bs_buffer* buf;

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
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    test_close_errors(reader, le_table);
    reader->free(reader);

    fseek(temp_file, 0, SEEK_SET);

    /*test a big-endian stream using external functions*/
    reader = br_open_external(temp_file,
                              BS_BIG_ENDIAN,
                              (ext_read_f)ext_fread_test,
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
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    test_close_errors(reader, be_table);
    reader->free(reader);

    /*test a little-endian stream using external functions*/
    reader = br_open_external(temp_file,
                              BS_LITTLE_ENDIAN,
                              (ext_read_f)ext_fread_test,
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
    reader->mark(reader);

    /*check a big-endian substream built from a file*/
    subreader = br_substream_new(BS_BIG_ENDIAN);
    reader->skip(reader, 16);
    reader->substream_append(reader, subreader, 4);
    test_big_endian_reader(subreader, be_table);
    test_big_endian_parse(subreader);
    test_try(subreader, be_table);
    test_callbacks_reader(subreader, 14, 18, be_table, 14);
    br_substream_reset(subreader);

    reader->rewind(reader);
    reader->skip(reader, 16);
    reader->substream_append(reader, subreader, 4);
    test_close_errors(subreader, be_table);
    br_substream_reset(subreader);
    subreader->free(subreader);
    subreader = br_substream_new(BS_BIG_ENDIAN);

    /*check a big-endian substream built from another substream*/
    reader->rewind(reader);
    reader->skip(reader, 8);
    reader->substream_append(reader, subreader, 6);
    subreader->skip(subreader, 8);
    subsubreader = br_substream_new(BS_BIG_ENDIAN);
    subreader->substream_append(subreader, subsubreader, 4);
    test_big_endian_reader(subsubreader, be_table);
    test_big_endian_parse(subsubreader);
    test_try(subsubreader, be_table);
    test_callbacks_reader(subsubreader, 14, 18, be_table, 14);
    subsubreader->close(subsubreader);
    subreader->close(subreader);
    reader->rewind(reader);
    reader->unmark(reader);
    reader->free(reader);

    reader = br_open(temp_file, BS_LITTLE_ENDIAN);
    reader->mark(reader);

    /*check a little-endian substream built from a file*/
    subreader = br_substream_new(BS_LITTLE_ENDIAN);
    reader->skip(reader, 16);
    reader->substream_append(reader, subreader, 4);
    test_little_endian_reader(subreader, le_table);
    test_little_endian_parse(subreader);
    test_try(subreader, le_table);
    test_callbacks_reader(subreader, 14, 18, le_table, 13);
    br_substream_reset(subreader);

    reader->rewind(reader);
    reader->skip(reader, 16);
    reader->substream_append(reader, subreader, 4);
    test_close_errors(subreader, le_table);
    br_substream_reset(subreader);
    subreader->free(subreader);
    subreader = br_substream_new(BS_LITTLE_ENDIAN);

    /*check a little-endian substream built from another substream*/
    reader->rewind(reader);
    reader->skip(reader, 8);
    reader->substream_append(reader, subreader, 6);
    subreader->skip(subreader, 8);
    subsubreader = br_substream_new(BS_LITTLE_ENDIAN);
    subreader->substream_append(subreader, subsubreader, 4);
    test_little_endian_reader(subsubreader, le_table);
    test_little_endian_parse(subsubreader);
    test_try(subsubreader, le_table);
    test_callbacks_reader(subsubreader, 14, 18, le_table, 13);
    subsubreader->close(subsubreader);
    subreader->close(subreader);
    reader->rewind(reader);
    reader->unmark(reader);
    reader->free(reader);

    free(be_table);
    free(le_table);

    /*test the writer functions with each endianness*/
    test_writer(BS_BIG_ENDIAN);
    test_writer(BS_LITTLE_ENDIAN);

    /*check edge cases against known values*/
    test_edge_cases();

    fclose(temp_file);

    /*test buffer that's not rewindable*/
    buf = buf_new();
    test_buffer(buf);
    buf_close(buf);

    /*then test buffer that is rewindable*/
    buf = buf_new();
    buf_set_rewindable(buf, 1);
    test_buffer(buf);
    buf_close(buf);

    return 0;
}

void atexit_cleanup(void) {
    unlink(temp_filename);
}

void sigabort_cleanup(int signum) {
    unlink(temp_filename);
}

void test_big_endian_reader(BitstreamReader* reader,
                            struct br_huffman_table (*table)[][0x200]) {
    int bit;
    uint8_t sub_data[2];

    /*check the bitstream reader
      against some known big-endian values*/

    reader->mark(reader);
    assert(reader->read(reader, 2) == 0x2);
    assert(reader->read(reader, 3) == 0x6);
    assert(reader->read(reader, 5) == 0x07);
    assert(reader->read(reader, 3) == 0x5);
    assert(reader->read(reader, 19) == 0x53BC1);

    reader->rewind(reader);
    assert(reader->read_64(reader, 2) == 0x2);
    assert(reader->read_64(reader, 3) == 0x6);
    assert(reader->read_64(reader, 5) == 0x07);
    assert(reader->read_64(reader, 3) == 0x5);
    assert(reader->read_64(reader, 19) == 0x53BC1);

    reader->rewind(reader);
    assert(reader->read(reader, 2) == 0x2);
    reader->skip(reader, 3);
    assert(reader->read(reader, 5) == 0x07);
    reader->skip(reader, 3);
    assert(reader->read(reader, 19) == 0x53BC1);

    reader->rewind(reader);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0xE);
    reader->rewind(reader);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0x3);
    reader->rewind(reader);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0xC);

    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0xD);
    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0x7);
    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0x8);
    reader->rewind(reader);

    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    bit = reader->read(reader, 1);
    assert(bit == 0);
    reader->unread(reader, bit);
    assert(reader->read(reader, 2) == 1);
    reader->byte_align(reader);

    reader->rewind(reader);
    assert(reader->read(reader, 8) == 0xB1);
    reader->unread(reader, 0);
    assert(reader->read(reader, 1) == 0);
    reader->unread(reader, 1);
    assert(reader->read(reader, 1) == 1);

    reader->rewind(reader);
    assert(reader->read_signed(reader, 2) == -2);
    assert(reader->read_signed(reader, 3) == -2);
    assert(reader->read_signed(reader, 5) == 7);
    assert(reader->read_signed(reader, 3) == -3);
    assert(reader->read_signed(reader, 19) == -181311);

    reader->rewind(reader);
    assert(reader->read_signed_64(reader, 2) == -2);
    assert(reader->read_signed_64(reader, 3) == -2);
    assert(reader->read_signed_64(reader, 5) == 7);
    assert(reader->read_signed_64(reader, 3) == -3);
    assert(reader->read_signed_64(reader, 19) == -181311);

    reader->rewind(reader);
    assert(reader->read_unary(reader, 0) == 1);
    assert(reader->read_unary(reader, 0) == 2);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 4);

    reader->rewind(reader);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 1);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 3);
    assert(reader->read_unary(reader, 1) == 0);

    reader->rewind(reader);
    assert(reader->read_limited_unary(reader, 0, 2) == 1);
    assert(reader->read_limited_unary(reader, 0, 2) == -1);
    reader->rewind(reader);
    assert(reader->read_limited_unary(reader, 1, 2) == 0);
    assert(reader->read_limited_unary(reader, 1, 2) == 1);
    assert(reader->read_limited_unary(reader, 1, 2) == 0);
    assert(reader->read_limited_unary(reader, 1, 2) == -1);

    reader->rewind(reader);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 4);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 2);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 2);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 2);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 4);
    assert(reader->read_huffman_code(reader, *table) == 2);

    reader->rewind(reader);
    assert(reader->read(reader, 3) == 5);
    reader->byte_align(reader);
    assert(reader->read(reader, 3) == 7);
    reader->byte_align(reader);
    reader->byte_align(reader);
    assert(reader->read(reader, 8) == 59);
    reader->byte_align(reader);
    assert(reader->read(reader, 4) == 12);

    reader->rewind(reader);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\xB1\xED", 2) == 0);
    reader->rewind(reader);
    assert(reader->read(reader, 4) == 11);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\x1E\xD3", 2) == 0);

    reader->rewind(reader);
    assert(reader->read(reader, 3) == 5);
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    assert(reader->read(reader, 3) == 5);
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    assert(reader->read(reader, 4) == 3);
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    assert(reader->read(reader, 4) == 12);

    reader->rewind(reader);
    reader->mark(reader);
    assert(reader->read(reader, 4) == 0xB);
    reader->rewind(reader);
    assert(reader->read(reader, 8) == 0xB1);
    reader->rewind(reader);
    assert(reader->read(reader, 12) == 0xB1E);
    reader->unmark(reader);
    reader->mark(reader);
    assert(reader->read(reader, 4) == 0xD);
    reader->rewind(reader);
    assert(reader->read(reader, 8) == 0xD3);
    reader->rewind(reader);
    assert(reader->read(reader, 12) == 0xD3B);
    reader->unmark(reader);

    reader->rewind(reader);
    reader->unmark(reader);
}

void test_big_endian_parse(BitstreamReader* reader) {
    unsigned u1,u2,u3,u4,u5,u6;
    int s1,s2,s3,s4,s5;
    uint64_t U1,U2,U3,U4,U5;
    int64_t S1,S2,S3,S4,S5;
    uint8_t sub_data1[2];
    uint8_t sub_data2[2];

    reader->mark(reader);

    /*first, check all the defined format fields*/
    reader->parse(reader, "2u 3u 5u 3u 19u", &u1, &u2, &u3, &u4, &u5);
    assert(u1 == 0x2);
    assert(u2 == 0x6);
    assert(u3 == 0x07);
    assert(u4 == 0x5);
    assert(u5 == 0x53BC1);

    reader->rewind(reader);
    reader->parse(reader, "2s 3s 5s 3s 19s", &s1, &s2, &s3, &s4, &s5);
    assert(s1 == -2);
    assert(s2 == -2);
    assert(s3 == 7);
    assert(s4 == -3);
    assert(s5 == -181311);

    reader->rewind(reader);
    reader->parse(reader, "2U 3U 5U 3U 19U", &U1, &U2, &U3, &U4, &U5);
    assert(U1 == 0x2);
    assert(U2 == 0x6);
    assert(U3 == 0x07);
    assert(U4 == 0x5);
    assert(U5 == 0x53BC1);

    reader->rewind(reader);
    reader->parse(reader, "2S 3S 5S 3S 19S", &S1, &S2, &S3, &S4, &S5);
    assert(S1 == -2);
    assert(S2 == -2);
    assert(S3 == 7);
    assert(S4 == -3);
    assert(S5 == -181311);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 3p 5u 3p 19u", &u1, &u3, &u5);
    assert(u1 == 0x2);
    assert(u3 == 0x07);
    assert(u5 == 0x53BC1);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2p 1P 3u 19u", &u4, &u5);
    assert(u4 == 0x5);
    assert(u5 == 0x53BC1);

    reader->rewind(reader);
    reader->parse(reader, "2b 2b", sub_data1, sub_data2);
    assert(memcmp(sub_data1, "\xB1\xED", 2) == 0);
    assert(memcmp(sub_data2, "\x3B\xC1", 2) == 0);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u a 3u a 4u a 5u", &u1, &u2, &u3, &u4);
    assert(u1 == 2);
    assert(u2 == 7);
    assert(u3 == 3);
    assert(u4 == 24);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "3* 2u", &u1, &u2, &u3);
    assert(u1 == 2);
    assert(u2 == 3);
    assert(u3 == 0);

    u1 = u2 = u3 = u4 = u5 = u6 = 0;
    reader->rewind(reader);
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
    reader->rewind(reader);
    reader->parse(reader, "2u ? 3u", &u1);
    assert(u1 == 2);

    /*unknown instruction prefixed by number*/
    u1 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 10? 3u", &u1);
    assert(u1 == 2);

    /*unknown instruction prefixed by multiplier*/
    u1 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 10* ? 3u", &u1);
    assert(u1 == 2);

    /*unknown instruction prefixed by number and multiplier*/
    u1 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 10* 3? 3u", &u1);
    assert(u1 == 2);

    reader->rewind(reader);
    reader->unmark(reader);
}

void test_little_endian_reader(BitstreamReader* reader,
                               struct br_huffman_table (*table)[][0x200]) {
    int bit;
    uint8_t sub_data[2];

    /*check the bitstream reader
      against some known little-endian values*/

    reader->mark(reader);
    assert(reader->read(reader, 2) == 0x1);
    assert(reader->read(reader, 3) == 0x4);
    assert(reader->read(reader, 5) == 0x0D);
    assert(reader->read(reader, 3) == 0x3);
    assert(reader->read(reader, 19) == 0x609DF);

    reader->rewind(reader);
    assert(reader->read_64(reader, 2) == 1);
    assert(reader->read_64(reader, 3) == 4);
    assert(reader->read_64(reader, 5) == 13);
    assert(reader->read_64(reader, 3) == 3);
    assert(reader->read_64(reader, 19) == 395743);

    reader->rewind(reader);
    assert(reader->read(reader, 2) == 0x1);
    reader->skip(reader, 3);
    assert(reader->read(reader, 5) == 0x0D);
    reader->skip(reader, 3);
    assert(reader->read(reader, 19) == 0x609DF);

    reader->rewind(reader);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0xD);
    reader->rewind(reader);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0xB);
    reader->rewind(reader);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0x1);

    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 1);
    assert(reader->read(reader, 4) == 0x6);
    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 2);
    assert(reader->read(reader, 4) == 0xD);
    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    reader->skip_bytes(reader, 3);
    assert(reader->read(reader, 4) == 0x0);
    reader->rewind(reader);

    reader->rewind(reader);
    assert(reader->read(reader, 1) == 1);
    bit = reader->read(reader, 1);
    assert(bit == 0);
    reader->unread(reader, bit);
    assert(reader->read(reader, 4) == 8);
    reader->byte_align(reader);

    reader->rewind(reader);
    assert(reader->read(reader, 8) == 0xB1);
    reader->unread(reader, 0);
    assert(reader->read(reader, 1) == 0);
    reader->unread(reader, 1);
    assert(reader->read(reader, 1) == 1);

    reader->rewind(reader);
    assert(reader->read_signed(reader, 2) == 1);
    assert(reader->read_signed(reader, 3) == -4);
    assert(reader->read_signed(reader, 5) == 13);
    assert(reader->read_signed(reader, 3) == 3);
    assert(reader->read_signed(reader, 19) == -128545);

    reader->rewind(reader);
    assert(reader->read_signed_64(reader, 2) == 1);
    assert(reader->read_signed_64(reader, 3) == -4);
    assert(reader->read_signed_64(reader, 5) == 13);
    assert(reader->read_signed_64(reader, 3) == 3);
    assert(reader->read_signed_64(reader, 19) == -128545);

    reader->rewind(reader);
    assert(reader->read_unary(reader, 0) == 1);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 0);
    assert(reader->read_unary(reader, 0) == 2);
    assert(reader->read_unary(reader, 0) == 2);

    reader->rewind(reader);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 3);
    assert(reader->read_unary(reader, 1) == 0);
    assert(reader->read_unary(reader, 1) == 1);
    assert(reader->read_unary(reader, 1) == 0);

    reader->rewind(reader);
    assert(reader->read_limited_unary(reader, 0, 2) == 1);
    assert(reader->read_limited_unary(reader, 0, 2) == 0);
    assert(reader->read_limited_unary(reader, 0, 2) == 0);
    assert(reader->read_limited_unary(reader, 0, 2) == -1);

    reader->rewind(reader);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 3);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 2);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 0);
    assert(reader->read_huffman_code(reader, *table) == 1);
    assert(reader->read_huffman_code(reader, *table) == 2);
    assert(reader->read_huffman_code(reader, *table) == 4);
    assert(reader->read_huffman_code(reader, *table) == 3);

    reader->rewind(reader);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\xB1\xED", 2) == 0);
    reader->rewind(reader);
    assert(reader->read(reader, 4) == 1);
    reader->read_bytes(reader, sub_data, 2);
    assert(memcmp(sub_data, "\xDB\xBE", 2) == 0);

    reader->rewind(reader);
    assert(reader->read(reader, 3) == 1);
    reader->byte_align(reader);
    assert(reader->read(reader, 3) == 5);
    reader->byte_align(reader);
    reader->byte_align(reader);
    assert(reader->read(reader, 8) == 59);
    reader->byte_align(reader);
    assert(reader->read(reader, 4) == 1);

    reader->rewind(reader);
    assert(reader->read(reader, 3) == 1);
    reader->set_endianness(reader, BS_BIG_ENDIAN);
    assert(reader->read(reader, 3) == 7);
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    assert(reader->read(reader, 4) == 11);
    reader->set_endianness(reader, BS_LITTLE_ENDIAN);
    assert(reader->read(reader, 4) == 1);

    reader->rewind(reader);
    assert(reader->read_limited_unary(reader, 1, 2) == 0);
    assert(reader->read_limited_unary(reader, 1, 2) == -1);

    reader->rewind(reader);
    reader->mark(reader);
    assert(reader->read(reader, 4) == 0x1);
    reader->rewind(reader);
    assert(reader->read(reader, 8) == 0xB1);
    reader->rewind(reader);
    assert(reader->read(reader, 12) == 0xDB1);
    reader->unmark(reader);
    reader->mark(reader);
    assert(reader->read(reader, 4) == 0xE);
    reader->rewind(reader);
    assert(reader->read(reader, 8) == 0xBE);
    reader->rewind(reader);
    assert(reader->read(reader, 12) == 0x3BE);
    reader->unmark(reader);

    reader->rewind(reader);
    reader->unmark(reader);
}

void test_little_endian_parse(BitstreamReader* reader) {
    unsigned u1,u2,u3,u4,u5,u6;
    int s1,s2,s3,s4,s5;
    uint64_t U1,U2,U3,U4,U5;
    int64_t S1,S2,S3,S4,S5;
    uint8_t sub_data1[2];
    uint8_t sub_data2[2];

    reader->mark(reader);

    /*first, check all the defined format fields*/
    reader->parse(reader, "2u 3u 5u 3u 19u", &u1, &u2, &u3, &u4, &u5);
    assert(u1 == 0x1);
    assert(u2 == 0x4);
    assert(u3 == 0x0D);
    assert(u4 == 0x3);
    assert(u5 == 0x609DF);

    reader->rewind(reader);
    reader->parse(reader, "2s 3s 5s 3s 19s", &s1, &s2, &s3, &s4, &s5);
    assert(s1 == 1);
    assert(s2 == -4);
    assert(s3 == 13);
    assert(s4 == 3);
    assert(s5 == -128545);

    reader->rewind(reader);
    reader->parse(reader, "2U 3U 5U 3U 19U", &U1, &U2, &U3, &U4, &U5);
    assert(u1 == 0x1);
    assert(u2 == 0x4);
    assert(u3 == 0x0D);
    assert(u4 == 0x3);
    assert(u5 == 0x609DF);

    reader->rewind(reader);
    reader->parse(reader, "2S 3S 5S 3S 19S", &S1, &S2, &S3, &S4, &S5);
    assert(s1 == 1);
    assert(s2 == -4);
    assert(s3 == 13);
    assert(s4 == 3);
    assert(s5 == -128545);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 3p 5u 3p 19u", &u1, &u3, &u5);
    assert(u1 == 0x1);
    assert(u3 == 0x0D);
    assert(u5 == 0x609DF);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2p 1P 3u 19u", &u4, &u5);
    assert(u4 == 0x3);
    assert(u5 == 0x609DF);

    reader->rewind(reader);
    reader->parse(reader, "2b 2b", sub_data1, sub_data2);
    assert(memcmp(sub_data1, "\xB1\xED", 2) == 0);
    assert(memcmp(sub_data2, "\x3B\xC1", 2) == 0);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u a 3u a 4u a 5u", &u1, &u2, &u3, &u4);
    assert(u1 == 1);
    assert(u2 == 5);
    assert(u3 == 11);
    assert(u4 == 1);

    u1 = u2 = u3 = u4 = u5 = 0;
    reader->rewind(reader);
    reader->parse(reader, "3* 2u", &u1, &u2, &u3);
    assert(u1 == 1);
    assert(u2 == 0);
    assert(u3 == 3);

    u1 = u2 = u3 = u4 = u5 = u6 = 0;
    reader->rewind(reader);
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
    reader->rewind(reader);
    reader->parse(reader, "2u ? 3u", &u1);
    assert(u1 == 1);

    /*unknown instruction prefixed by number*/
    u1 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 10? 3u", &u1);
    assert(u1 == 1);

    /*unknown instruction prefixed by multiplier*/
    u1 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 10* ? 3u", &u1);
    assert(u1 == 1);

    /*unknown instruction prefixed by number and multiplier*/
    u1 = 0;
    reader->rewind(reader);
    reader->parse(reader, "2u 10* 3? 3u", &u1);
    assert(u1 == 1);

    reader->rewind(reader);
    reader->unmark(reader);
}

void
test_close_errors(BitstreamReader* reader,
                  struct br_huffman_table (*table)[][0x200]) {
    uint8_t bytes[10];
    struct BitstreamReader_s* subreader;

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
        reader->read_limited_unary(reader, 0, 10);
        assert(0);
    } else {
        br_etry(reader);
    }

    if (!setjmp(*br_try(reader))) {
        reader->read_huffman_code(reader, *table);
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

    reader->mark(reader); /*should do nothing*/

    if (!setjmp(*br_try(reader))) {
        reader->read(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
    }

    reader->rewind(reader);
    reader->unmark(reader);

    subreader = br_substream_new(BS_BIG_ENDIAN); /*doesn't really matter*/
    if (!setjmp(*br_try(reader))) {
        reader->substream_append(reader, subreader, 1);
        assert(0);
    } else {
        br_etry(reader);
    }
    subreader->close(subreader);
}

void test_try(BitstreamReader* reader,
              struct br_huffman_table (*table)[][0x200]) {
    uint8_t bytes[2];
    BitstreamReader* substream;

    reader->mark(reader);

    /*bounce to the very end of the stream*/
    reader->skip(reader, 31);
    reader->mark(reader);
    assert(reader->read(reader, 1) == 1);
    reader->rewind(reader);

    /*then test all the read methods to ensure they trigger br_abort

      in the case of unary/Huffman, the stream ends on a "1" bit
      whether reading it big-endian or little-endian*/

    if (!setjmp(*br_try(reader))) {
        reader->read(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_64(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_signed(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_signed_64(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->skip(reader, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->skip_bytes(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_unary(reader, 0);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        assert(reader->read_unary(reader, 1) == 0);
        reader->read_unary(reader, 1);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_limited_unary(reader, 0, 3);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        assert(reader->read_limited_unary(reader, 1, 3) == 0);
        reader->read_limited_unary(reader, 1, 3);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_huffman_code(reader, *table);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    if (!setjmp(*br_try(reader))) {
        reader->read_bytes(reader, bytes, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }
    substream = br_substream_new(BS_BIG_ENDIAN); /*doesn't really matter*/
    if (!setjmp(*br_try(reader))) {
        reader->substream_append(reader, substream, 2);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }

    /*ensure substream_append doesn't use all the RAM in the world
      on a failed read which is very large*/
    if (!setjmp(*br_try(reader))) {
        reader->substream_append(reader, substream, 4294967295);
        assert(0);
    } else {
        br_etry(reader);
        reader->rewind(reader);
    }

    substream->close(substream);

    reader->unmark(reader);

    reader->rewind(reader);
    reader->unmark(reader);
}

void test_callbacks_reader(BitstreamReader* reader,
                           int unary_0_reads,
                           int unary_1_reads,
                           struct br_huffman_table (*table)[][0x200],
                           int huffman_code_count) {
    int i;
    unsigned int byte_count;
    uint8_t bytes[2];
    struct bs_callback saved_callback;

    reader->mark(reader);
    br_add_callback(reader, (bs_callback_f)byte_counter, &byte_count);

    /*a single callback*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->read(reader, 4);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*calling callbacks directly*/
    byte_count = 0;
    for (i = 0; i < 20; i++)
        br_call_callbacks(reader, 0);
    assert(byte_count == 20);

    /*two callbacks*/
    byte_count = 0;
    br_add_callback(reader, (bs_callback_f)byte_counter, &byte_count);
    for (i = 0; i < 8; i++)
        reader->read(reader, 4);
    assert(byte_count == 8);
    br_pop_callback(reader, NULL);
    reader->rewind(reader);

    /*temporarily suspending the callback*/
    byte_count = 0;
    reader->read(reader, 8);
    assert(byte_count == 1);
    br_pop_callback(reader, &saved_callback);
    reader->read(reader, 8);
    reader->read(reader, 8);
    br_push_callback(reader, &saved_callback);
    reader->read(reader, 8);
    assert(byte_count == 2);
    reader->rewind(reader);

    /*temporarily adding two callbacks*/
    byte_count = 0;
    reader->read(reader, 8);
    assert(byte_count == 1);
    br_add_callback(reader, (bs_callback_f)byte_counter, &byte_count);
    reader->read(reader, 8);
    reader->read(reader, 8);
    br_pop_callback(reader, NULL);
    reader->read(reader, 8);
    assert(byte_count == 6);
    reader->rewind(reader);

    /*read_signed*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->read_signed(reader, 4);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*read_64*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->read_64(reader, 4);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*skip*/
    byte_count = 0;
    for (i = 0; i < 8; i++)
        reader->skip(reader, 4);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*skip_bytes*/
    byte_count = 0;
    for (i = 0; i < 2; i++)
        reader->skip_bytes(reader, 2);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*read_unary*/
    byte_count = 0;
    for (i = 0; i < unary_0_reads; i++)
        reader->read_unary(reader, 0);
    assert(byte_count == 4);
    byte_count = 0;
    reader->rewind(reader);
    for (i = 0; i < unary_1_reads; i++)
        reader->read_unary(reader, 1);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*read_limited_unary*/
    byte_count = 0;
    for (i = 0; i < unary_0_reads; i++)
        reader->read_limited_unary(reader, 0, 6);
    assert(byte_count == 4);
    byte_count = 0;
    reader->rewind(reader);
    for (i = 0; i < unary_1_reads; i++)
        reader->read_limited_unary(reader, 1, 6);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*read_huffman_code*/
    byte_count = 0;
    for (i = 0; i < huffman_code_count; i++)
        reader->read_huffman_code(reader, *table);
    assert(byte_count == 4);
    reader->rewind(reader);

    /*read_bytes*/
    byte_count = 0;
    reader->read_bytes(reader, bytes, 2);
    reader->read_bytes(reader, bytes, 2);
    assert(byte_count == 4);
    reader->rewind(reader);

    br_pop_callback(reader, NULL);
    reader->unmark(reader);
}

void
test_writer(bs_endianness endianness) {
    FILE* output_file;
    BitstreamWriter* writer;
    BitstreamWriter* sub_writer;
    BitstreamWriter* sub_sub_writer;

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
        checks[i](sub_writer, endianness);
        bw_rec_copy(writer, sub_writer);
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
    fclose(output_file);

    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    sub_writer = bw_open_recorder(endianness);
    test_rec_split_dumps(endianness, writer, sub_writer);
    fflush(output_file);
    check_output_file();
    sub_writer->close(sub_writer);
    writer->close(writer);
    fclose(output_file);

    sub_writer = bw_open_recorder(endianness);
    test_writer_close_errors(sub_writer);
    sub_writer->set_endianness(sub_writer, endianness == BS_BIG_ENDIAN ?
                               BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    test_writer_close_errors(sub_writer);
    sub_writer->free(sub_writer);

    /*perform accumulator-based checks*/
    for (i = 0; i < total_checks; i++) {
        writer = bw_open_accumulator(endianness);
        assert(writer->bits_written(writer) == 0);
        checks[i](writer, endianness);
        assert(writer->bits_written(writer) == 32);
        writer->close(writer);
    }

    writer = bw_open_accumulator(endianness);
    test_writer_close_errors(writer);
    writer->set_endianness(writer, endianness == BS_BIG_ENDIAN ?
                           BS_LITTLE_ENDIAN : BS_BIG_ENDIAN);
    test_writer_close_errors(writer);
    writer->free(writer);

    /*check swap records*/
    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    sub_writer = bw_open_recorder(endianness);
    sub_sub_writer = bw_open_recorder(endianness);
    sub_sub_writer->write(sub_sub_writer, 8, 0xB1);
    sub_sub_writer->write(sub_sub_writer, 8, 0xED);
    sub_writer->write(sub_writer, 8, 0x3B);
    sub_writer->write(sub_writer, 8, 0xC1);
    bw_swap_records(sub_writer, sub_sub_writer);
    bw_rec_copy(writer, sub_writer);
    bw_rec_copy(writer, sub_sub_writer);
    fflush(output_file);
    check_output_file();
    writer->close(writer);
    sub_writer->close(sub_writer);
    sub_sub_writer->close(sub_sub_writer);

    /*check recorder reset*/
    output_file = fopen(temp_filename, "wb");
    writer = bw_open(output_file, endianness);
    sub_writer = bw_open_recorder(endianness);
    sub_writer->write(sub_writer, 8, 0xAA);
    sub_writer->write(sub_writer, 8, 0xBB);
    sub_writer->write(sub_writer, 8, 0xCC);
    sub_writer->write(sub_writer, 8, 0xDD);
    sub_writer->write(sub_writer, 8, 0xEE);
    bw_reset_recorder(sub_writer);
    sub_writer->write(sub_writer, 8, 0xB1);
    sub_writer->write(sub_writer, 8, 0xED);
    sub_writer->write(sub_writer, 8, 0x3B);
    sub_writer->write(sub_writer, 8, 0xC1);
    bw_rec_copy(writer, sub_writer);
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

    /*check an accumulator-based byte-align*/
    for (i = 0; i < total_achecks; i++) {
        if (endianness == BS_BIG_ENDIAN) {
            check_alignment_a(&(achecks_be[i]), endianness);
        } else if (endianness == BS_LITTLE_ENDIAN) {
            check_alignment_a(&(achecks_le[i]), endianness);
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
        bw_add_callback(writer, (bs_callback_f)func_add_one, &(sums[0]));
        bw_add_callback(writer, (bs_callback_f)func_add_two, &(sums[1]));
        bw_add_callback(writer, (bs_callback_f)func_mult_three, &(sums[2]));
        checks[i](writer, endianness);
        writer->close(writer);
        assert(sums[0] == 4);
        assert(sums[1] == 8);
        assert(sums[2] == 81);
    }

    /*check recorder-based callback functions*/
    for (i = 0; i < total_checks; i++) {
        sums[0] = sums[1] = 0;
        sums[2] = 1;
        writer = bw_open_recorder(endianness);
        bw_add_callback(writer, (bs_callback_f)func_add_one, &(sums[0]));
        bw_add_callback(writer, (bs_callback_f)func_add_two, &(sums[1]));
        bw_add_callback(writer, (bs_callback_f)func_mult_three, &(sums[2]));
        checks[i](writer, endianness);
        writer->close(writer);
        assert(sums[0] == 4);
        assert(sums[1] == 8);
        assert(sums[2] == 81);
    }

    /*check accumulator-based callback functions*/
    for (i = 0; i < total_checks; i++) {
        sums[0] = sums[1] = 0;
        sums[2] = 1;
        writer = bw_open_accumulator(endianness);
        bw_add_callback(writer, (bs_callback_f)func_add_one, &(sums[0]));
        bw_add_callback(writer, (bs_callback_f)func_add_two, &(sums[1]));
        bw_add_callback(writer, (bs_callback_f)func_mult_three, &(sums[2]));
        checks[i](writer, endianness);
        writer->close(writer);

        /*this is correct
          for speed reasons, accumulators don't call any callback functions
          so the final values remain unchanged*/
        assert(sums[0] == 0);
        assert(sums[1] == 0);
        assert(sums[2] == 1);
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
                                  (ext_flush_f)ext_fflush_test,
                                  (ext_close_f)ext_fclose_test,
                                  (ext_free_f)ext_ffree_test);
        bw_add_callback(writer, (bs_callback_f)func_add_one, &(sums[0]));
        bw_add_callback(writer, (bs_callback_f)func_add_two, &(sums[1]));
        bw_add_callback(writer, (bs_callback_f)func_mult_three, &(sums[2]));
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
        checks[i](sub_sub_writer, endianness);
        assert(sub_writer->bits_written(sub_writer) == 0);
        assert(sub_writer->bits_written(sub_sub_writer) == 32);
        bw_rec_copy(sub_writer, sub_sub_writer);
        assert(sub_writer->bits_written(sub_writer) == 32);
        assert(sub_writer->bits_written(sub_sub_writer) == 32);
        bw_rec_copy(writer, sub_writer);
        fflush(output_file);
        check_output_file();
        writer->free(writer);
        sub_writer->close(sub_writer);
        sub_sub_writer->close(sub_sub_writer);
        fclose(output_file);
    }

    /*check that recorder->accumulator works*/
    for (i = 0; i < total_checks; i++) {
        writer = bw_open_accumulator(endianness);
        sub_writer = bw_open_recorder(endianness);
        assert(writer->bits_written(writer) == 0);
        assert(sub_writer->bits_written(sub_writer) == 0);
        checks[i](sub_writer, endianness);
        assert(writer->bits_written(writer) == 0);
        assert(sub_writer->bits_written(sub_writer) == 32);
        bw_rec_copy(writer, sub_writer);
        assert(writer->bits_written(writer) == 32);
        assert(sub_writer->bits_written(sub_writer) == 32);
        writer->close(writer);
        sub_writer->close(sub_writer);
    }
}

void
test_writer_close_errors(BitstreamWriter* writer)
{
    writer->close_internal_stream(writer);

    if (!setjmp(*bw_try(writer))) {
        writer->write(writer, 2, 1);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->write_signed(writer, 3, 1);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->write_64(writer, 4, 1);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->write_signed_64(writer, 5, 1);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->write_bytes(writer, (uint8_t*)"abcde", 5);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->byte_align(writer);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->write_unary(writer, 0, 5);
        assert(0);
    } else {
        bw_etry(writer);
    }

    if (!setjmp(*bw_try(writer))) {
        writer->build(writer, "1u", 1);
        assert(0);
    } else {
        bw_etry(writer);
    }

    assert(writer->bits_written(writer) == 0);

    writer->flush(writer);



}

void
writer_perform_write(BitstreamWriter* writer, bs_endianness endianness) {
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write(writer, 2, 2);
        writer->write(writer, 3, 6);
        writer->write(writer, 5, 7);
        writer->write(writer, 3, 5);
        writer->write(writer, 19, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write(writer, 2, 1);
        writer->write(writer, 3, 4);
        writer->write(writer, 5, 13);
        writer->write(writer, 3, 3);
        writer->write(writer, 19, 395743);
        break;
    }
}

void
writer_perform_write_signed(BitstreamWriter* writer, bs_endianness endianness) {
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_signed(writer, 2, -2);
        writer->write_signed(writer, 3, -2);
        writer->write_signed(writer, 5, 7);
        writer->write_signed(writer, 3, -3);
        writer->write_signed(writer, 19, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_signed(writer, 2, 1);
        writer->write_signed(writer, 3, -4);
        writer->write_signed(writer, 5, 13);
        writer->write_signed(writer, 3, 3);
        writer->write_signed(writer, 19, -128545);
        break;
    }
}

void
writer_perform_write_64(BitstreamWriter* writer, bs_endianness endianness) {
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_64(writer, 2, 2);
        writer->write_64(writer, 3, 6);
        writer->write_64(writer, 5, 7);
        writer->write_64(writer, 3, 5);
        writer->write_64(writer, 19, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_64(writer, 2, 1);
        writer->write_64(writer, 3, 4);
        writer->write_64(writer, 5, 13);
        writer->write_64(writer, 3, 3);
        writer->write_64(writer, 19, 395743);
        break;
    }
}

void
writer_perform_write_signed_64(BitstreamWriter* writer,
                               bs_endianness endianness)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_signed_64(writer, 2, -2);
        writer->write_signed_64(writer, 3, -2);
        writer->write_signed_64(writer, 5, 7);
        writer->write_signed_64(writer, 3, -3);
        writer->write_signed_64(writer, 19, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_signed_64(writer, 2, 1);
        writer->write_signed_64(writer, 3, -4);
        writer->write_signed_64(writer, 5, 13);
        writer->write_signed_64(writer, 3, 3);
        writer->write_signed_64(writer, 19, -128545);
        break;
    }
}

void
writer_perform_write_unary_0(BitstreamWriter* writer,
                             bs_endianness endianness) {
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_unary(writer, 0, 1);
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
}

void
writer_perform_write_unary_1(BitstreamWriter* writer,
                             bs_endianness endianness) {
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->write_unary(writer, 1, 0);
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
}

void
writer_perform_build_u(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->build(writer, "2u 3u 5u 3u 19u", 2, 6, 7, 5, 342977);
        break;
    case BS_LITTLE_ENDIAN:
        writer->build(writer, "2u 3u 5u 3u 19u", 1, 4, 13, 3, 395743);
        break;
    }
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

    writer->build(writer, "2U 3U 5U 3U 19U", v1, v2, v3, v4, v5);
}

void
writer_perform_build_s(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->build(writer, "2s 3s 5s 3s 19s", -2, -2, 7, -3, -181311);
        break;
    case BS_LITTLE_ENDIAN:
        writer->build(writer, "2s 3s 5s 3s 19s", 1, -4, 13, 3, -128545);
        break;
    }
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

    writer->build(writer, "2S 3S 5S 3S 19S", v1, v2, v3, v4, v5);
}

void
writer_perform_build_b(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    writer->build(writer, "2b 2b", (uint8_t*)"\xB1\xED", (uint8_t*)"\x3B\xC1");
}

void
writer_perform_build_mult(BitstreamWriter* writer,
                          bs_endianness endianness)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        writer->build(writer, "8* 4u", 11, 1, 14, 13, 3, 11, 12, 1);
        break;
    case BS_LITTLE_ENDIAN:
        writer->build(writer, "8* 4u", 1, 11, 13, 14, 11, 3, 1, 12);
        break;
    }
}


void
writer_perform_huffman(BitstreamWriter* writer,
                       bs_endianness endianness)
{
    struct bw_huffman_table* table;
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
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 4);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 2);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 2);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 2);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 4);
        writer->write_huffman_code(writer, table, 2);
        break;
    case BS_LITTLE_ENDIAN:
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 3);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 2);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 0);
        writer->write_huffman_code(writer, table, 1);
        writer->write_huffman_code(writer, table, 2);
        writer->write_huffman_code(writer, table, 4);
        writer->write_huffman_code(writer, table, 3);
        /*table makes us unable to generate single
          trailing 1 bit, so we have to do it manually*/
        writer->write(writer, 1, 1);
        break;
    }

    free_bw_huffman_table(table);
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
    BitstreamWriter* rec = bw_open_recorder(endianness);
    BitstreamWriter* bw = bw_open(f, endianness);
    BitstreamReader* br;
    struct stat s;

    rec->write(rec, check->bits, check->value);
    rec->byte_align(rec);
    bw_rec_copy(bw, rec);
    rec->close(rec);
    bw->close(bw);

    assert(stat(temp_filename, &s) == 0);
    assert(s.st_size == check->resulting_bytes);

    f = fopen(temp_filename, "rb");
    br = br_open(f, endianness);
    assert(br->read(br, check->resulting_bytes * 8) == check->resulting_value);
    br->close(br);
}

void check_alignment_a(const align_check* check,
                       bs_endianness endianness)
{
    BitstreamWriter* bw = bw_open_accumulator(endianness);

    bw->write(bw, check->bits, check->value);
    bw->byte_align(bw);

    assert(bw->bits_written(bw) == (check->resulting_bytes * 8));
    assert(bw->bytes_written(bw) == check->resulting_bytes);

    bw->close(bw);
}

void check_alignment_e(const align_check* check,
                       bs_endianness endianness)
{
    FILE* f = fopen(temp_filename, "wb");
    BitstreamWriter* bw = bw_open_external(f,
                                           endianness,
                                           4096,
                                           (ext_write_f)ext_fwrite_test,
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
    sub_reader = br_substream_new(BS_BIG_ENDIAN);
    reader->substream_append(reader, sub_reader, 48);
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
    sub_reader = br_substream_new(BS_LITTLE_ENDIAN);
    reader->substream_append(reader, sub_reader, 48);
    test_edge_reader_le(sub_reader);
    sub_reader->close(sub_reader);
    reader->close(reader);

    /*test a bunch of known big-endian values via the bitstream writer*/
    test_edge_writer(get_edge_writer_be, validate_edge_writer_be);

    /*test a bunch of known big-endian values via the bitstream recorder*/
    test_edge_writer(get_edge_recorder_be, validate_edge_recorder_be);

    /*test a bunch of known big-endian values via the bitstream accumulator*/
    test_edge_writer(get_edge_accumulator_be, validate_edge_accumulator);

    /*test a bunch of known little-endian values via the bitstream writer*/
    test_edge_writer(get_edge_writer_le, validate_edge_writer_le);

    /*test a bunch of known little-endian values via the bitstream recorder*/
    test_edge_writer(get_edge_recorder_le, validate_edge_recorder_le);

    /*test a bunch of known little-endian values via the bitstream accumulator*/
    test_edge_writer(get_edge_accumulator_le, validate_edge_accumulator);
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

    reader->mark(reader);

    /*try the unsigned 32 and 64 bit values*/
    reader->rewind(reader);
    assert(reader->read(reader, 32) == 0);
    assert(reader->read(reader, 32) == 4294967295UL);
    assert(reader->read(reader, 32) == 2147483648UL);
    assert(reader->read(reader, 32) == 2147483647UL);
    assert(reader->read_64(reader, 64) == 0);
    assert(reader->read_64(reader, 64) == 0xFFFFFFFFFFFFFFFFULL);
    assert(reader->read_64(reader, 64) == 9223372036854775808ULL);
    assert(reader->read_64(reader, 64) == 9223372036854775807ULL);

    /*try the signed 32 and 64 bit values*/
    reader->rewind(reader);
    assert(reader->read_signed(reader, 32) == 0);
    assert(reader->read_signed(reader, 32) == -1);
    assert(reader->read_signed(reader, 32) == -2147483648LL);
    assert(reader->read_signed(reader, 32) == 2147483647LL);
    assert(reader->read_signed_64(reader, 64) == 0);
    assert(reader->read_signed_64(reader, 64) == -1);
    assert(reader->read_signed_64(reader, 64) == (9223372036854775808ULL * -1));
    assert(reader->read_signed_64(reader, 64) == 9223372036854775807LL);

    /*try the unsigned values via parse()*/
    reader->rewind(reader);
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
    reader->rewind(reader);
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

    reader->unmark(reader);
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

    reader->mark(reader);

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
    reader->rewind(reader);
    assert(reader->read_signed(reader, 32) == 0);
    assert(reader->read_signed(reader, 32) == -1);
    assert(reader->read_signed(reader, 32) == -2147483648LL);
    assert(reader->read_signed(reader, 32) == 2147483647LL);
    assert(reader->read_signed_64(reader, 64) == 0);
    assert(reader->read_signed_64(reader, 64) == -1);
    assert(reader->read_signed_64(reader, 64) == (9223372036854775808ULL * -1));
    assert(reader->read_signed_64(reader, 64) == 9223372036854775807LL);

    /*try the unsigned values via parse()*/
    reader->rewind(reader);
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
    reader->rewind(reader);
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

    reader->unmark(reader);
}

void
test_edge_writer(BitstreamWriter* (*get_writer)(void),
                 void (*validate_writer)(BitstreamWriter*))
{
    BitstreamWriter* writer;

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

    /*try the unsigned 32 and 64 bit values*/
    writer = get_writer();
    writer->write(writer, 32, 0);
    writer->write(writer, 32, 4294967295UL);
    writer->write(writer, 32, 2147483648UL);
    writer->write(writer, 32, 2147483647UL);
    writer->write_64(writer, 64, 0);
    writer->write_64(writer, 64, 0xFFFFFFFFFFFFFFFFULL);
    writer->write_64(writer, 64, 9223372036854775808ULL);
    writer->write_64(writer, 64, 9223372036854775807ULL);
    validate_writer(writer);

    /*try the signed 32 and 64 bit values*/
    writer = get_writer();
    writer->write_signed(writer, 32, 0);
    writer->write_signed(writer, 32, -1);
    writer->write_signed(writer, 32, -2147483648LL);
    writer->write_signed(writer, 32, 2147483647LL);
    writer->write_signed_64(writer, 64, 0);
    writer->write_signed_64(writer, 64, -1);
    writer->write_signed_64(writer, 64, (9223372036854775808ULL * -1));
    writer->write_signed_64(writer, 64, 9223372036854775807LL);
    validate_writer(writer);

    /*try the unsigned values via build()*/
    writer = get_writer();
    u_val_1 = 0;
    u_val_2 = 4294967295UL;
    u_val_3 = 2147483648UL;
    u_val_4 = 2147483647UL;
    u_val64_1 = 0;
    u_val64_2 = 0xFFFFFFFFFFFFFFFFULL;
    u_val64_3 = 9223372036854775808ULL;
    u_val64_4 = 9223372036854775807ULL;
    writer->build(writer, "32u 32u 32u 32u 64U 64U 64U 64U",
                  u_val_1, u_val_2, u_val_3, u_val_4,
                  u_val64_1, u_val64_2, u_val64_3, u_val64_4);
    validate_writer(writer);

    /*try the signed values via build()*/
    writer = get_writer();
    s_val_1 = 0;
    s_val_2 = -1;
    s_val_3 = -2147483648LL;
    s_val_4 = 2147483647LL;
    s_val64_1 = 0;
    s_val64_2 = -1;
    s_val64_3 = (9223372036854775808ULL * -1);
    s_val64_4 = 9223372036854775807LL;
    writer->build(writer, "32s 32s 32s 32s 64S 64S 64S 64S",
                  s_val_1, s_val_2, s_val_3, s_val_4,
                  s_val64_1, s_val64_2, s_val64_3, s_val64_4);
    validate_writer(writer);
}

BitstreamWriter*
get_edge_writer_be(void)
{
    return bw_open(fopen(temp_filename, "wb"), BS_BIG_ENDIAN);
}

BitstreamWriter*
get_edge_recorder_be(void)
{
    return bw_open_recorder(BS_BIG_ENDIAN);
}

BitstreamWriter*
get_edge_accumulator_be(void)
{
    return bw_open_accumulator(BS_BIG_ENDIAN);
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
validate_edge_recorder_be(BitstreamWriter* recorder)
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
    bw_rec_copy(writer, recorder);
    recorder->close(recorder);
    writer->close(writer);
    input_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 48, input_file) == 48);
    assert(memcmp(data, big_endian, 48) == 0);
    fclose(input_file);
}

void
validate_edge_accumulator(BitstreamWriter* accumulator)
{
    assert(accumulator->bits_written(accumulator) == 48 * 8);
    accumulator->close(accumulator);
}

BitstreamWriter*
get_edge_writer_le(void) {
    return bw_open(fopen(temp_filename, "wb"), BS_LITTLE_ENDIAN);
}

BitstreamWriter*
get_edge_recorder_le(void)
{
    return bw_open_recorder(BS_LITTLE_ENDIAN);
}

BitstreamWriter*
get_edge_accumulator_le(void)
{
    return bw_open_accumulator(BS_LITTLE_ENDIAN);
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
validate_edge_recorder_le(BitstreamWriter* recorder)
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
    bw_rec_copy(writer, recorder);
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
                    BitstreamWriter* recorder)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        recorder->write(recorder, 2, 2);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 6);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 5, 7);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 5);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 19, 342977);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        break;
    case BS_LITTLE_ENDIAN:
        recorder->write(recorder, 2, 1);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 4);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 5, 13);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 3);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 19, 395743);
        bw_rec_copy(writer, recorder);
        bw_reset_recorder(recorder);
        break;
    }
}

void
test_rec_split_dumps(bs_endianness endianness,
                     BitstreamWriter* writer,
                     BitstreamWriter* recorder)
{
    BitstreamWriter* dummy = bw_open_accumulator(endianness);

    switch (endianness) {
    case BS_BIG_ENDIAN:
        recorder->write(recorder, 2, 2);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 6);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 5, 7);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 5);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 19, 342977);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        break;
    case BS_LITTLE_ENDIAN:
        recorder->write(recorder, 2, 1);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 4);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 5, 13);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 3, 3);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        recorder->write(recorder, 19, 395743);
        bw_rec_split(dummy, writer, recorder, 0);
        bw_reset_recorder(recorder);
        break;
    }

    dummy->close(dummy);
}


int ext_fread_test(FILE* user_data,
                   struct bs_buffer* buffer)
{
    const static unsigned desired_size = 2;
    uint8_t data[2];
    const unsigned bytes_read = (unsigned)fread(data,
                                                sizeof(uint8_t),
                                                (size_t)desired_size,
                                                user_data);

    if (bytes_read > 0) {
        buf_write(buffer, data, bytes_read);
        return 0;
    } else {
        return 1;
    }
}

void ext_fclose_test(FILE* user_data)
{
    fclose(user_data);
}

void ext_ffree_test(FILE* user_data)
{
    return;
}

int ext_fwrite_test(FILE* user_data,
                    struct bs_buffer* buffer,
                    unsigned buffer_size)
{
    while (BUF_WINDOW_SIZE(buffer) >= buffer_size) {
        fwrite(BUF_WINDOW_START(buffer),
               sizeof(uint8_t),
               buffer_size,
               user_data);
        buffer->window_start += buffer_size;
    }

    return 0;
}

void ext_fflush_test(FILE* user_data)
{
    fflush(user_data);
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

void test_buffer(struct bs_buffer *buf)
{
    struct bs_buffer *buf2 = buf_new();
    uint8_t temp1[4] = {1, 2, 3, 4};
    uint8_t temp2[4];
    unsigned i;

    /*ensure reads from an empty buffer return nothing*/
    assert(BUF_WINDOW_SIZE(buf) == 0);
    assert(buf_getc(buf) == EOF);
    assert(buf_getc(buf) == EOF);
    assert(buf_read(buf, temp1, 1) == 0);

    /*try some simple buf_putc/buf_getc pairs*/
    buf_putc(1, buf);
    buf_putc(2, buf);
    assert(buf_getc(buf) == 1);
    buf_putc(3, buf);  /*may shift window down to make room*/
    assert(buf_getc(buf) == 2);
    assert(buf_getc(buf) == 3);
    assert(BUF_WINDOW_SIZE(buf) == 0);

    /*try some simple buf_write/buf_read pairs*/
    for (i = 0; i < 5; i++) {
        buf_write(buf, temp1, i);
        assert(BUF_WINDOW_SIZE(buf) == i);
        assert(memcmp(BUF_WINDOW_START(buf), temp1, i) == 0);
        assert(buf_read(buf, temp2, i) == i);
        assert(memcmp(temp1, temp2, (size_t)i) == 0);
        assert(BUF_WINDOW_SIZE(buf) == 0);
    }

    /*try a low-level resize using buf_resize() and BUF_WINDOW_END*/
    buf_putc(0, buf);
    buf_resize(buf, 4);
    memcpy(BUF_WINDOW_END(buf), temp1, 4);
    buf->window_end += 4;
    for (i = 0; i < 5; i++) {
        assert(buf_getc(buf) == i);
    }
    assert(BUF_WINDOW_SIZE(buf) == 0);

    /*try a buf_extend to combine a couple of buffers*/
    for (i = 0; i < 4; i++) {
        buf_putc(i, buf);
    }
    buf_extend(buf, buf2);
    buf_reset(buf);
    for (i = 4; i < 8; i++) {
        buf_putc(i, buf);
    }
    buf_extend(buf, buf2);
    assert(BUF_WINDOW_SIZE(buf2) == 8);
    for (i = 0; i < 8; i++) {
        assert(buf_getc(buf2) == i);
    }

    /*ensure buf_copy works like it should*/
    buf_reset(buf);
    for (i = 0; i < 4; i++) {
        buf_putc(i, buf);
    }
    assert(buf_getc(buf) == 0);
    buf_copy(buf, buf2);
    for (i = 1; i < 4; i++) {
        assert(buf_getc(buf) == i);
    }
    for (i = 1; i < 4; i++) {
        assert(buf_getc(buf2) == i);
    }

    /*toggle rewindability and test buf_getpos/buf_setpos*/
    buf_reset(buf);
    if (!buf->rewindable) {
        unsigned pos;

        buf_set_rewindable(buf, 1);

        buf_getpos(buf, &pos);
        /*new calls to putc must always append to buffer*/
        for (i = 0; i < 10; i++) {
            buf_putc(i, buf);
        }
        for (i = 0; i < 10; i++) {
            assert(buf_getc(buf) == i);
        }
        for (i = 10; i < 20; i++) {
            buf_putc(i, buf);
        }
        for (i = 10; i < 20; i++) {
            assert(buf_getc(buf) == i);
        }
        /*rewinding should always be possible*/
        buf_setpos(buf, pos);
        for (i = 0; i < 20; i++) {
            assert(buf_getc(buf) == i);
        }

        buf_set_rewindable(buf, 0);
    } else {
        const unsigned data_size = buf->data_size;

        buf_set_rewindable(buf, 0);

        /*no matter how many new bytes are added,
          the window size shouldn't get any larger*/
        for (i = 0; i < 10000; i++) {
            buf_putc(i % 256, buf);
            assert(buf_getc(buf) == (i % 256));
            assert(buf->data_size == data_size);
        }

        buf_set_rewindable(buf, 1);
    }

    buf_close(buf2);
}

#endif
