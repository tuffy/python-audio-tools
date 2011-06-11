#include "bitstream.h"
#include <string.h>

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

const unsigned int read_bits_table[0x200][8] =
#include "read_bits_table.h"
    ;

const unsigned int read_bits_table_le[0x200][8] =
#include "read_bits_table_le.h"
    ;

const unsigned int unread_bit_table[0x200][2] =
#include "unread_bit_table.h"
    ;

const unsigned int unread_bit_table_le[0x200][2] =
#include "unread_bit_table_le.h"
    ;

const unsigned int read_unary_table[0x200][2] =
#include "read_unary_table.h"
    ;

const unsigned int read_unary_table_le[0x200][2] =
#include "read_unary_table_le.h"
    ;

const unsigned int read_limited_unary_table[0x200][18] =
#include "read_limited_unary_table.h"
    ;

const unsigned int read_limited_unary_table_le[0x200][18] =
#include "read_limited_unary_table_le.h"
    ;

BitstreamReader*
br_open(FILE *f, bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
#ifndef NDEBUG
    bs->type = BR_FILE;
#endif
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
        bs->read_signed = br_read_signed_bits_f_be;
        bs->read_64 = br_read_bits64_f_be;
        bs->skip = br_skip_bits_f_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_f_be;
        bs->read_limited_unary = br_read_limited_unary_f_be;
        bs->set_endianness = br_set_endianness_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_f_le;
        bs->read_signed = br_read_signed_bits_f_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->skip = br_skip_bits_f_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_f_le;
        bs->read_limited_unary = br_read_limited_unary_f_le;
        bs->set_endianness = br_set_endianness_f_le;
        break;
    }

    bs->byte_align = br_byte_align;
    bs->read_huffman_code = br_read_huffman_code_f;
    bs->read_bytes = br_read_bytes_f;
    bs->substream_append = br_substream_append_f;
    bs->close = br_close;
    bs->close_stream = br_close_stream_f;
    bs->mark = br_mark_f;
    bs->rewind = br_rewind_f;
    bs->unmark = br_unmark_f;

    return bs;
}

void
br_free(BitstreamReader *bs)
{
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;
    struct br_mark *m_node;
    struct br_mark *m_next;

    if (bs == NULL)
        return;

    for (c_node = bs->callbacks; c_node != NULL; c_node = c_next) {
        c_next = c_node->next;
        free(c_node);
    }
    for (c_node = bs->callbacks_used; c_node != NULL; c_node = c_next) {
        c_next = c_node->next;
        free(c_node);
    }

    if (bs->exceptions != NULL) {
        fprintf(stderr, "Warning: leftover etry entries on stack\n");
    }
    for (e_node = bs->exceptions; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }
    for (e_node = bs->exceptions_used; e_node != NULL; e_node = e_next) {
        e_next = e_node->next;
        free(e_node);
    }

    if (bs->marks != NULL) {
        fprintf(stderr, "Warning: leftover marks on stack\n");
    }
    for (m_node = bs->marks; m_node != NULL; m_node = m_next) {
        m_next = m_node->next;
        free(m_node);
    }
    for (m_node = bs->marks_used; m_node != NULL; m_node = m_next) {
        m_next = m_node->next;
        free(m_node);
    }

    free(bs);
}

void
br_close(BitstreamReader *bs)
{
    bs->close_stream(bs);
    br_free(bs);
}

void
br_noop(BitstreamReader *bs)
{
    return;
}

void
br_close_stream_f(BitstreamReader *bs)
{
    if (bs == NULL)
        return;
    else if (bs->input.file != NULL) {
        fclose(bs->input.file);
        bs->close_stream = br_noop;
    }
}

void
br_add_callback(BitstreamReader *bs, bs_callback_func callback, void *data)
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
    }
}


void
br_abort(BitstreamReader *bs)
{
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "EOF encountered, aborting\n");
        exit(1);
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

/*These are helper macros for unpacking the results
  of the various jump tables in a less error-prone fashion.*/
#define BYTE_BANK_SIZE 9

#define READ_BITS_OUTPUT_SIZE(x) ((x) >> (BYTE_BANK_SIZE + 8))
#define READ_BITS_OUTPUT_BITS(x) (((x) >> BYTE_BANK_SIZE) & 0xFF)
#define READ_UNARY_OUTPUT_BITS(x) (((x) >> BYTE_BANK_SIZE) & 0xF)
#define READ_UNARY_CONTINUE(x) (((x) >> (BYTE_BANK_SIZE + 4)) & 1)
#define READ_UNARY_LIMIT_REACHED(x) ((x) >> (BYTE_BANK_SIZE + 4 + 1))
#define NEXT_CONTEXT(x) ((x) & ((1 << BYTE_BANK_SIZE) - 1))
#define UNREAD_BIT_LIMIT_REACHED(x) ((x) >> BYTE_BANK_SIZE)
#define READ_HUFFMAN_CONTINUE(x) ((x) >> BYTE_BANK_SIZE)
#define READ_HUFFMAN_NEXT_NODE(x) ((x) >> (BYTE_BANK_SIZE + 1))
#define NEW_CONTEXT(x) (0x100 | (x))


/*the bs_read_bits_?_?? functions differ
  by the byte reader (fgetc or py_getc)
  or which table they access (read_bits_table or read_bits_table_le)*/
unsigned int
br_read_bits_f_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator = ((accumulator << output_size) |
                       READ_BITS_OUTPUT_BITS(result));

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_bits_f_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator |= (READ_BITS_OUTPUT_BITS(result) << bit_offset);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_bits_s_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator = ((accumulator << output_size) |
                       READ_BITS_OUTPUT_BITS(result));

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_bits_s_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator |= (READ_BITS_OUTPUT_BITS(result) << bit_offset);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
    return accumulator;
}

#ifndef STANDALONE
unsigned int
br_read_bits_p_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator = ((accumulator << output_size) |
                       READ_BITS_OUTPUT_BITS(result));

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_bits_p_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator |= (READ_BITS_OUTPUT_BITS(result) << bit_offset);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
    return accumulator;
}
#endif


int
br_read_signed_bits_f_be(BitstreamReader* bs, unsigned int count)
{
    if (!br_read_bits_f_be(bs, 1)) {
        return br_read_bits_f_be(bs, count - 1);
    } else {
        return br_read_bits_f_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
br_read_signed_bits_f_le(BitstreamReader* bs, unsigned int count)
{
    int unsigned_value = br_read_bits_f_le(bs, count - 1);

    if (!br_read_bits_f_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}

int
br_read_signed_bits_s_be(BitstreamReader* bs, unsigned int count)
{
    if (!br_read_bits_s_be(bs, 1)) {
        return br_read_bits_s_be(bs, count - 1);
    } else {
        return br_read_bits_s_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
br_read_signed_bits_s_le(BitstreamReader* bs, unsigned int count)
{
    int unsigned_value = br_read_bits_s_le(bs, count - 1);

    if (!br_read_bits_s_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}

#ifndef STANDALONE
int
br_read_signed_bits_p_be(BitstreamReader* bs, unsigned int count)
{
    if (!br_read_bits_p_be(bs, 1)) {
        return br_read_bits_p_be(bs, count - 1);
    } else {
        return br_read_bits_p_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
br_read_signed_bits_p_le(BitstreamReader* bs, unsigned int count)
{
    int unsigned_value = br_read_bits_p_le(bs, count - 1);

    if (!br_read_bits_p_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}
#endif


/*the read_bits64 functions differ from the read_bits functions
  only by the size of the accumulator*/
uint64_t
br_read_bits64_f_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator = ((accumulator << output_size) |
                       READ_BITS_OUTPUT_BITS(result));

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
    return accumulator;
}

uint64_t
br_read_bits64_f_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator |= (READ_BITS_OUTPUT_BITS(result) << bit_offset);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
    return accumulator;
}

uint64_t
br_read_bits64_s_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator = ((accumulator << output_size) |
                       READ_BITS_OUTPUT_BITS(result));

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
    return accumulator;
}

uint64_t
br_read_bits64_s_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator |= (READ_BITS_OUTPUT_BITS(result) << bit_offset);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
    return accumulator;
}

#ifndef STANDALONE
uint64_t
br_read_bits64_p_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator = ((accumulator << output_size) |
                       READ_BITS_OUTPUT_BITS(result));

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
    return accumulator;
}

uint64_t
br_read_bits64_p_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        accumulator |= (READ_BITS_OUTPUT_BITS(result) << bit_offset);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
    return accumulator;
}
#endif


/*the skip_bits functions differ from the read_bits functions
  in that they have no accumulator
  which allows them to skip over a potentially unlimited amount of bits*/
void
br_skip_bits_f_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
}

void
br_skip_bits_f_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
}

void
br_skip_bits_s_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
}

void
br_skip_bits_s_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
}

#ifndef STANDALONE
void
br_skip_bits_p_be(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        context = NEXT_CONTEXT(result);

        count -= output_size;
    }

    bs->state = context;
}

void
br_skip_bits_p_le(BitstreamReader* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][MIN(count, 8) - 1];

        output_size = READ_BITS_OUTPUT_SIZE(result);

        context = NEXT_CONTEXT(result);

        count -= output_size;

        bit_offset += output_size;
    }

    bs->state = context;
}
#endif


void
br_unread_bit_be(BitstreamReader* bs, int unread_bit)
{
    unsigned int result = unread_bit_table[bs->state][unread_bit];
    assert(UNREAD_BIT_LIMIT_REACHED(result) == 0);
    bs->state = NEXT_CONTEXT(result);
}

void
br_unread_bit_le(BitstreamReader* bs, int unread_bit)
{
    unsigned int result = unread_bit_table_le[bs->state][unread_bit];
    assert(UNREAD_BIT_LIMIT_REACHED(result) == 0);
    bs->state = NEXT_CONTEXT(result);
}


unsigned int
br_read_unary_f_be(BitstreamReader* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_unary_table[context][stop_bit];

        accumulator += READ_UNARY_OUTPUT_BITS(result);

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_unary_f_le(BitstreamReader* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_unary_table_le[context][stop_bit];

        accumulator += READ_UNARY_OUTPUT_BITS(result);

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_unary_s_be(BitstreamReader* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_unary_table[context][stop_bit];

        accumulator += READ_UNARY_OUTPUT_BITS(result);

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_unary_s_le(BitstreamReader* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_unary_table_le[context][stop_bit];

        accumulator += READ_UNARY_OUTPUT_BITS(result);

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;
    return accumulator;
}

#ifndef STANDALONE
unsigned int
br_read_unary_p_be(BitstreamReader* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_unary_table[context][stop_bit];

        accumulator += READ_UNARY_OUTPUT_BITS(result);

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;
    return accumulator;
}

unsigned int
br_read_unary_p_le(BitstreamReader* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_unary_table_le[context][stop_bit];

        accumulator += READ_UNARY_OUTPUT_BITS(result);

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;
    return accumulator;
}
#endif


/*returns -1 on error, so cannot be unsigned*/
int
br_read_limited_unary_f_be(BitstreamReader* bs, int stop_bit, int maximum_bits)
{
    int context = bs->state;
    unsigned int result;
    unsigned int value;
    struct bs_callback* callback;
    int byte;
    int accumulator = 0;
    stop_bit *= 9;

    assert(maximum_bits > 0);

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_limited_unary_table[context][stop_bit +
                                                   MIN(maximum_bits, 8)];

        value = READ_UNARY_OUTPUT_BITS(result);

        accumulator += value;
        maximum_bits -= value;

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;

    if (READ_UNARY_LIMIT_REACHED(result)) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
}

int
br_read_limited_unary_f_le(BitstreamReader* bs, int stop_bit, int maximum_bits)
{
    int context = bs->state;
    unsigned int result;
    unsigned int value;
    struct bs_callback* callback;
    int byte;
    int accumulator = 0;
    stop_bit *= 9;

    assert(maximum_bits > 0);

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_limited_unary_table_le[context][stop_bit +
                                                      MIN(maximum_bits, 8)];

        value = READ_UNARY_OUTPUT_BITS(result);

        accumulator += value;
        maximum_bits -= value;

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;

    if (READ_UNARY_LIMIT_REACHED(result)) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
}

int
br_read_limited_unary_s_be(BitstreamReader* bs, int stop_bit, int maximum_bits)
{
    int context = bs->state;
    unsigned int result;
    unsigned int value;
    struct bs_callback* callback;
    int byte;
    int accumulator = 0;
    stop_bit *= 9;

    assert(maximum_bits > 0);

    do {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_limited_unary_table[context][stop_bit +
                                                   MIN(maximum_bits, 8)];

        value = READ_UNARY_OUTPUT_BITS(result);

        accumulator += value;
        maximum_bits -= value;

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;

    if (READ_UNARY_LIMIT_REACHED(result)) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
}

int
br_read_limited_unary_s_le(BitstreamReader* bs, int stop_bit, int maximum_bits)
{
    int context = bs->state;
    unsigned int result;
    unsigned int value;
    struct bs_callback* callback;
    int byte;
    int accumulator = 0;
    stop_bit *= 9;

    do {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_limited_unary_table_le[context][stop_bit +
                                                      MIN(maximum_bits, 8)];

        value = READ_UNARY_OUTPUT_BITS(result);

        accumulator += value;
        maximum_bits -= value;

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;

    if (READ_UNARY_LIMIT_REACHED(result)) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
}

#ifndef STANDALONE
int
br_read_limited_unary_p_be(BitstreamReader* bs,
                           int stop_bit,
                           int maximum_bits)
{
    int context = bs->state;
    unsigned int result;
    unsigned int value;
    struct bs_callback* callback;
    int byte;
    int accumulator = 0;
    stop_bit *= 9;

    do {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_limited_unary_table[context][stop_bit +
                                                   MIN(maximum_bits, 8)];

        value = READ_UNARY_OUTPUT_BITS(result);

        accumulator += value;
        maximum_bits -= value;

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;

    if (READ_UNARY_LIMIT_REACHED(result)) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
}

int
br_read_limited_unary_p_le(BitstreamReader* bs, int stop_bit, int maximum_bits)
{
    int context = bs->state;
    unsigned int result;
    unsigned int value;
    struct bs_callback* callback;
    int byte;
    int accumulator = 0;
    stop_bit *= 9;

    do {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                br_abort(bs);
            context = NEW_CONTEXT(byte);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_limited_unary_table_le[context][stop_bit +
                                                      MIN(maximum_bits, 8)];

        value = READ_UNARY_OUTPUT_BITS(result);

        accumulator += value;
        maximum_bits -= value;

        context = NEXT_CONTEXT(result);
    } while (READ_UNARY_CONTINUE(result));

    bs->state = context;

    if (READ_UNARY_LIMIT_REACHED(result)) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
}
#endif


void
br_read_bytes_f(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count) {
    unsigned int i;
    struct bs_callback* callback;

    if (bs->state == 0) {
        /*stream is byte-aligned, so perform optimized read*/

        /*fread bytes from file handle to output*/
        if (fread(bytes, sizeof(uint8_t), byte_count, bs->input.file) ==
            byte_count) {
            /*if sufficient bytes were read*/

            /*perform callbacks on the read bytes*/
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
                unsigned int byte_count) {
    unsigned int i;
    struct br_buffer* buffer;
    struct bs_callback* callback;

    if (bs->state == 0) {
        /*stream is byte-aligned, so perform optimized read*/

        buffer = bs->input.substream;

        if ((buffer->buffer_size - buffer->buffer_position) >= byte_count) {
            /*the buffer has enough bytes to read*/

            /*so copy bytes from buffer to output*/
            memcpy(bytes, buffer->buffer + buffer->buffer_position, byte_count);

            /*perform callbacks on the read bytes*/
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                for (i = 0; i < byte_count; i++)
                    callback->callback(bytes[i], callback->data);

            /*and increment buffer position*/
            buffer->buffer_position += byte_count;
        } else {
            /*the buffer has insufficient bytes,
              so shift position to the end (as if we've read them all)
              and raise an abort*/
            buffer->buffer_position = buffer->buffer_size;
            br_abort(bs);
        }
    } else {
        /*stream is not byte-aligned, so perform multiple reads*/
        for (i = 0; i < byte_count; i++)
            bytes[i] = bs->read(bs, 8);
    }
}

#ifndef STANDALONE
void
br_read_bytes_p(struct BitstreamReader_s* bs,
                uint8_t* bytes,
                unsigned int byte_count) {
    unsigned int i;

    /*this is the unoptimized version
      because it's easier than pulling bytes
      out of py_getc's buffer directly*/
    for (i = 0; i < byte_count; i++)
        bytes[i] = bs->read(bs, 8);
}
#endif


void
br_set_endianness_f_be(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_f_le;
        bs->read_signed = br_read_signed_bits_f_le;
        bs->read_64 = br_read_bits64_f_le;
        bs->skip = br_skip_bits_f_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_f_le;
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
        bs->read_signed = br_read_signed_bits_f_be;
        bs->read_64 = br_read_bits64_f_be;
        bs->skip = br_skip_bits_f_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_f_be;
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
        bs->read_signed = br_read_signed_bits_s_le;
        bs->read_64 = br_read_bits64_s_le;
        bs->skip = br_skip_bits_s_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_s_le;
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
        bs->read_signed = br_read_signed_bits_s_be;
        bs->read_64 = br_read_bits64_s_be;
        bs->skip = br_skip_bits_s_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_s_be;
        bs->read_limited_unary = br_read_limited_unary_s_be;
        bs->set_endianness = br_set_endianness_s_be;
    }
}

#ifndef STANDALONE
void
br_set_endianness_p_be(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = br_read_bits_p_le;
        bs->read_signed = br_read_signed_bits_p_le;
        bs->read_64 = br_read_bits64_p_le;
        bs->skip = br_skip_bits_p_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_p_le;
        bs->read_limited_unary = br_read_limited_unary_p_le;
        bs->set_endianness = br_set_endianness_p_le;
    }
}

void
br_set_endianness_p_le(BitstreamReader *bs, bs_endianness endianness)
{
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = br_read_bits_p_be;
        bs->read_signed = br_read_signed_bits_p_be;
        bs->read_64 = br_read_bits64_p_be;
        bs->skip = br_skip_bits_p_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_p_be;
        bs->read_limited_unary = br_read_limited_unary_p_be;
        bs->set_endianness = br_set_endianness_p_be;
    }
}
#endif


/*
Note that read_huffman_code has no endianness variants.
Which direction it reads from is decided when the table data is compiled.
*/
int
br_read_huffman_code_f(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200])
{
    struct br_huffman_table entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

    entry = table[node][context];
    while (READ_HUFFMAN_CONTINUE(entry.context_node)) {
        if ((byte = fgetc(bs->input.file)) == EOF)
            br_abort(bs);
        context = NEW_CONTEXT(byte);

        for (callback = bs->callbacks;
             callback != NULL;
             callback = callback->next)
            callback->callback((uint8_t)byte, callback->data);

        entry = table[READ_HUFFMAN_NEXT_NODE(entry.context_node)][context];
    }

    bs->state = NEXT_CONTEXT(entry.context_node);
    return entry.value;
}

int
br_read_huffman_code_s(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200])
{
    struct br_huffman_table entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

    entry = table[node][context];
    while (READ_HUFFMAN_CONTINUE(entry.context_node)) {
        if ((byte = buf_getc(bs->input.substream)) == EOF)
            br_abort(bs);
        context = NEW_CONTEXT(byte);

        for (callback = bs->callbacks;
             callback != NULL;
             callback = callback->next)
            callback->callback((uint8_t)byte, callback->data);

        entry = table[READ_HUFFMAN_NEXT_NODE(entry.context_node)][context];
    }

    bs->state = NEXT_CONTEXT(entry.context_node);
    return entry.value;
}

#ifndef STANDALONE
int
br_read_huffman_code_p(BitstreamReader *bs,
                       struct br_huffman_table table[][0x200])
{
    struct br_huffman_table entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

    entry = table[node][context];
    while (READ_HUFFMAN_CONTINUE(entry.context_node)) {
        if ((byte = py_getc(bs->input.python)) == EOF)
            br_abort(bs);
        context = NEW_CONTEXT(byte);

        for (callback = bs->callbacks;
             callback != NULL;
             callback = callback->next)
            callback->callback((uint8_t)byte, callback->data);

        entry = table[READ_HUFFMAN_NEXT_NODE(entry.context_node)][context];
    }

    bs->state = NEXT_CONTEXT(entry.context_node);
    return entry.value;
}
#endif


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

    mark->position.substream = bs->input.substream->buffer_position;
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
    bs->input.substream->mark_in_progress = 1;
}

#ifndef STANDALONE
void
br_mark_p(BitstreamReader* bs)
{
    struct br_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct br_mark));
    else {
        mark = bs->marks_used;
        bs->marks_used = bs->marks_used->next;
    }

    mark->position.python = bs->input.python->buffer_position;
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
    bs->input.python->mark_in_progress = 1;
}
#endif


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
        bs->input.substream->buffer_position = bs->marks->position.substream;
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

#ifndef STANDALONE
void
br_rewind_p(BitstreamReader* bs)
{
    if (bs->marks != NULL) {
        bs->input.python->buffer_position = bs->marks->position.python;
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}
#endif


void
br_unmark_f(BitstreamReader* bs)
{
    struct br_mark* mark = bs->marks;
    bs->marks = mark->next;
    mark->next = bs->marks_used;
    bs->marks_used = mark;
}

void
br_unmark_s(BitstreamReader* bs)
{
    struct br_mark* mark = bs->marks;
    bs->marks = mark->next;
    mark->next = bs->marks_used;
    bs->marks_used = mark;
    bs->input.substream->mark_in_progress = (bs->marks != NULL);
}

#ifndef STANDALONE
void
br_unmark_p(BitstreamReader* bs)
{
    struct br_mark* mark = bs->marks;
    bs->marks = mark->next;
    mark->next = bs->marks_used;
    bs->marks_used = mark;
    bs->input.python->mark_in_progress = (bs->marks != NULL);
}
#endif


void
br_byte_align(BitstreamReader* bs)
{
    bs->state = 0;
}


/*******************************************
 substream handlers

 for pulling smaller pieces out of a larger stream
 and processing them separately
 *******************************************/

struct br_buffer*
buf_new(void)
{
    struct br_buffer* stream = malloc(sizeof(struct br_buffer));
    stream->buffer_size = 0;
    stream->buffer_total_size = 1;
    stream->buffer = malloc(stream->buffer_total_size);
    stream->buffer_position = 0;
    stream->mark_in_progress = 0;
    return stream;
}

uint32_t
buf_size(struct br_buffer *stream)
{
    return stream->buffer_size - stream->buffer_position;
}

uint8_t*
buf_extend(struct br_buffer *stream, uint32_t data_size)
{
    uint32_t remaining_bytes;
    uint8_t* extended_buffer;

    remaining_bytes = stream->buffer_total_size - stream->buffer_size;

    assert(stream->buffer_total_size >= stream->buffer_size);

    if (stream->mark_in_progress) {
        /*we need to be able to rewind to any point in the buffer
          so it can only be extended if space is needed*/
        if (data_size > remaining_bytes) {
            while (data_size > remaining_bytes) {
                stream->buffer_total_size *= 2;
                remaining_bytes = (stream->buffer_total_size -
                                   stream->buffer_size);
            }
            stream->buffer = realloc(stream->buffer, stream->buffer_total_size);
        }
    } else {
        /*we don't need to rewind the buffer,
          so bytes at the beginning can be discarded
          if space is needed to extend it*/
        if (data_size > remaining_bytes) {
            if (data_size > (remaining_bytes + stream->buffer_position)) {
                /*if there's not enough bytes to recycle,
                  just extended the buffer outright*/
                while (data_size > (remaining_bytes +
                                    stream->buffer_position)) {
                    stream->buffer_total_size *= 2;
                    remaining_bytes = (stream->buffer_total_size -
                                       stream->buffer_size);
                }
                stream->buffer = realloc(stream->buffer,
                                         stream->buffer_total_size);
            } else {
                /*if there are enough bytes to recycle,
                  shift the buffer down and reuse them
                  if the buffer position is incremented*/
                if (stream->buffer_position > 0) {
                    memmove(stream->buffer,
                            stream->buffer + stream->buffer_position,
                            stream->buffer_size - stream->buffer_position);
                    stream->buffer_size -= stream->buffer_position;
                    stream->buffer_position = 0;
                }
            }
        }
    }

    extended_buffer = stream->buffer + stream->buffer_size;

    return extended_buffer;
}

void
buf_reset(struct br_buffer *stream)
{
    stream->buffer_size = 0;
    stream->buffer_position = 0;
    stream->mark_in_progress = 0;
}

int
buf_getc(struct br_buffer *stream)
{
    if (stream->buffer_position < stream->buffer_size) {
        return stream->buffer[stream->buffer_position++];
    } else
        return EOF;
}

void
buf_close(struct br_buffer *stream)
{
    if (stream->buffer != NULL)
        free(stream->buffer);
    free(stream);
}


struct BitstreamReader_s*
br_substream_new(bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
#ifndef NDEBUG
    bs->type = BR_SUBSTREAM;
#endif
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
        bs->read_signed = br_read_signed_bits_s_be;
        bs->read_64 = br_read_bits64_s_be;
        bs->skip = br_skip_bits_s_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_s_be;
        bs->read_limited_unary = br_read_limited_unary_s_be;
        bs->set_endianness = br_set_endianness_s_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_s_le;
        bs->read_signed = br_read_signed_bits_s_le;
        bs->read_64 = br_read_bits64_s_le;
        bs->skip = br_skip_bits_s_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_s_le;
        bs->read_limited_unary = br_read_limited_unary_s_le;
        bs->set_endianness = br_set_endianness_s_le;
        break;
    }

    bs->byte_align = br_byte_align;
    bs->read_huffman_code = br_read_huffman_code_s;
    bs->read_bytes = br_read_bytes_s;
    bs->substream_append = br_substream_append_s;
    bs->close = br_close;
    bs->close_stream = br_close_stream_s;
    bs->mark = br_mark_s;
    bs->rewind = br_rewind_s;
    bs->unmark = br_unmark_s;

    return bs;
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

void
br_substream_append_f(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes)
{
    uint8_t* extended_buffer;
    struct bs_callback *callback;
    uint32_t i;

    /*byte align the input stream*/
    stream->state = 0;

    /*extend the output stream's current buffer to fit additional bytes*/
    extended_buffer = buf_extend(substream->input.substream, bytes);

    /*read input stream to extended buffer*/
    if (fread(extended_buffer, sizeof(uint8_t), bytes,
              stream->input.file) != bytes)
        /*abort if the amount of read bytes is insufficient*/
        br_abort(stream);

    /*perform callbacks on bytes in extended buffer*/
    for (callback = stream->callbacks;
         callback != NULL;
         callback = callback->next) {
        for (i = 0; i < bytes; i++)
            callback->callback(extended_buffer[i], callback->data);
    }

    /*complete buffer extension*/
    substream->input.substream->buffer_size += bytes;
}

#ifndef STANDALONE
void
br_substream_append_p(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes)
{
    uint8_t* extended_buffer;
    struct bs_callback *callback;
    int byte;
    uint32_t i;

    /*byte align the input stream*/
    stream->state = 0;

    /*extend the output stream's current buffer to fit additional bytes*/
    extended_buffer = buf_extend(substream->input.substream, bytes);

    /*read input stream to extended buffer

      (it would be faster to incorperate py_getc's
       Python buffer handling in this routine
       instead of reading one byte at a time,
       but I'd like to separate those parts out beforehand*/
    for (i = 0; i < bytes; i++) {
        byte = py_getc(stream->input.python);
        if (byte != EOF)
            extended_buffer[i] = byte;
        else
            /*abort if EOF encountered during read*/
            br_abort(stream);
    }

    /*perform callbacks on bytes in extended buffer*/
    for (callback = stream->callbacks;
         callback != NULL;
         callback = callback->next) {
        for (i = 0; i < bytes; i++)
            callback->callback(extended_buffer[i], callback->data);
    }

    /*complete buffer extension*/
    substream->input.substream->buffer_size += bytes;
}
#endif

void
br_substream_append_s(struct BitstreamReader_s *stream,
                      struct BitstreamReader_s *substream,
                      uint32_t bytes)
{
    uint8_t* extended_buffer;
    struct bs_callback *callback;
    uint32_t i;

    /*byte align the input stream*/
    stream->state = 0;

    /*abort if there's sufficient bytes remaining
      in the input stream to pass to the output stream*/
    if (buf_size(stream->input.substream) < bytes)
        br_abort(stream);

    /*extend the output stream's current buffer to fit additional bytes*/
    extended_buffer = buf_extend(substream->input.substream, bytes);

    /*copy the requested bytes from the input buffer to the output buffer*/
    memcpy(extended_buffer,
           stream->input.substream->buffer +
           stream->input.substream->buffer_position,
           bytes);

    /*advance the input buffer past the requested bytes*/
    stream->input.substream->buffer_position += bytes;

    /*perform callbacks on bytes in the extended buffer*/
    for (callback = stream->callbacks;
         callback != NULL;
         callback = callback->next) {
        for (i = 0; i < bytes; i++)
            callback->callback(extended_buffer[i], callback->data);
    }

    /*complete buffer extension*/
    substream->input.substream->buffer_size += bytes;
}

void
br_close_stream_s(struct BitstreamReader_s *stream)
{
    buf_close(stream->input.substream);
}

#ifndef STANDALONE

/*******************************************
 Python stream handlers

 for making a Python file-like object behave
 like C file pointers
 *******************************************/

struct br_python_input*
py_open(PyObject* reader)
{
    struct br_python_input* input = malloc(sizeof(struct br_python_input));
    Py_INCREF(reader);
    input->reader_obj = reader;
    input->buffer = malloc(4096 * sizeof(uint8_t));
    input->buffer_total_size = 4096;
    input->buffer_size = 0;
    input->buffer_position = 0;
    input->mark_in_progress = 0;

    return input;
}

int
py_getc(struct br_python_input *stream)
{
    PyObject *buffer_obj;
    char *buffer_str;
    Py_ssize_t buffer_len;

    if (stream->buffer_position < stream->buffer_size) {
        /*if there's enough bytes in the buffer,
          simply return the next byte in the buffer*/
        return stream->buffer[stream->buffer_position++];
    } else {
        /*otherwise, call the read() method on our reader object
          to get more bytes for our buffer*/
        buffer_obj = PyObject_CallMethod(stream->reader_obj,
                                         "read",
                                         "i",
                                         4096);

        if (buffer_obj != NULL) {
            /*if calling read() succeeded, convert our new buffer into bytes*/
            if (!PyString_AsStringAndSize(buffer_obj,
                                          &buffer_str,
                                          &buffer_len)) {
                if (buffer_len > 0) {
                    /*if the size of the new string is greater than 0*/
                    if (!stream->mark_in_progress) {
                        /*and the stream has no mark,
                          overwrite the existing buffer*/
                        if (buffer_len > stream->buffer_total_size) {

                            stream->buffer = realloc(stream->buffer,
                                                     buffer_len);
                            stream->buffer_total_size = buffer_len;
                        }

                        memcpy(stream->buffer,
                               buffer_str,
                               buffer_len);
                        stream->buffer_size = buffer_len;
                        stream->buffer_position = 0;
                    } else {
                        /*and the stream has a mark,
                          extend the existing buffer*/
                        if (buffer_len > (stream->buffer_total_size -
                                          stream->buffer_position)) {

                            stream->buffer_total_size += buffer_len;
                            stream->buffer = realloc(
                                                stream->buffer,
                                                stream->buffer_total_size);
                        }

                        memcpy(stream->buffer + stream->buffer_position,
                               buffer_str,
                               buffer_len);
                        stream->buffer_size += buffer_len;
                    }

                    /*then, return the next byte in the buffer*/
                    Py_DECREF(buffer_obj);
                    return stream->buffer[stream->buffer_position++];
                } else {
                    /*if the size of the new string is 0, return EOF*/
                    Py_DECREF(buffer_obj);
                    return EOF;
                }
            } else {
                /*byte conversion failed, so print error and return EOF*/
                PyErr_PrintEx(1);
                Py_DECREF(buffer_obj);
                return EOF;
            }
        } else {
            /*calling read() failed, so print error and return EOF*/
            PyErr_PrintEx(1);
            return EOF;
        }
    }
}

int
py_close(struct br_python_input *stream)
{
    PyObject* close_result;

    close_result = PyObject_CallMethod(stream->reader_obj,
                                       "close",
                                       NULL);
    if (close_result != NULL)
        Py_DECREF(close_result);
    else {
        /*some exception occurred when calling close()
          so simply print it out and continue on
          since there's little we can do about it*/
        PyErr_PrintEx(1);
    }

    py_free(stream);

    return 0;
}

void
py_free(struct br_python_input *stream)
{
    Py_XDECREF(stream->reader_obj);
    free(stream->buffer);
    free(stream);
}


BitstreamReader*
br_open_python(PyObject *reader, bs_endianness endianness)
{
    BitstreamReader *bs = malloc(sizeof(BitstreamReader));
#ifndef NDEBUG
    bs->type = BR_PYTHON;
#endif
    bs->input.python = py_open(reader);
    bs->state = 0;
    bs->callbacks = NULL;
    bs->exceptions = NULL;
    bs->marks = NULL;
    bs->callbacks_used = NULL;
    bs->exceptions_used = NULL;
    bs->marks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = br_read_bits_p_be;
        bs->read_signed = br_read_signed_bits_p_be;
        bs->read_64 = br_read_bits64_p_be;
        bs->skip = br_skip_bits_p_be;
        bs->unread = br_unread_bit_be;
        bs->read_unary = br_read_unary_p_be;
        bs->read_limited_unary = br_read_limited_unary_p_be;
        bs->set_endianness = br_set_endianness_p_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = br_read_bits_p_le;
        bs->read_signed = br_read_signed_bits_p_le;
        bs->read_64 = br_read_bits64_p_le;
        bs->skip = br_skip_bits_p_le;
        bs->unread = br_unread_bit_le;
        bs->read_unary = br_read_unary_p_le;
        bs->read_limited_unary = br_read_limited_unary_p_le;
        bs->set_endianness = br_set_endianness_p_le;
        break;
    }

    bs->byte_align = br_byte_align;
    bs->read_huffman_code = br_read_huffman_code_p;
    bs->read_bytes = br_read_bytes_p;
    bs->substream_append = br_substream_append_p;
    bs->close = br_close;
    bs->close_stream = br_close_stream_p;
    bs->mark = br_mark_p;
    bs->rewind = br_rewind_p;
    bs->unmark = br_unmark_p;

    return bs;
}

void
br_close_stream_p(BitstreamReader *bs)
{
    if (bs == NULL)
        return;
    else if (bs->input.python != NULL) {
        py_close(bs->input.python);
        bs->close_stream = br_noop;
    }
}

#endif



BitstreamWriter*
bw_open(FILE *f, bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_FILE;

    bs->output.file.file = f;
    bs->output.file.buffer_size = 0;
    bs->output.file.buffer = 0;

    bs->first_placeholder = NULL;
    bs->final_placeholder = NULL;
    bs->placeholders_used = NULL;

    bs->callbacks = NULL;
    bs->callbacks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = bw_write_bits_f_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->set_endianness = bw_set_endianness_f_be;
        bs->split_record = bw_split_record_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = bw_write_bits_f_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->set_endianness = bw_set_endianness_f_le;
        bs->split_record = bw_split_record_le;
        break;
    }

    bs->write_placeholder = bw_write_placeholder_f;
    bs->write_64_placeholder = bw_write_64_placeholder_f;
    bs->fill_placeholder = bw_fill_placeholder_f;
    bs->fill_64_placeholder = bw_fill_64_placeholder_f;
    bs->write_signed = bw_write_signed_bits_f_r;
    bs->write_unary = bw_write_unary_f_r;
    bs->byte_align = bw_byte_align_f;
    bs->bits_written = bw_bits_written_f;
    bs->close = bw_close_new;
    bs->close_stream = bw_close_stream_f;

    return bs;
}

BitstreamWriter*
bw_open_accumulator(bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_ACCUMULATOR;

    bs->output.accumulator = 0;

    bs->first_placeholder = NULL;
    bs->final_placeholder = NULL;
    bs->placeholders_used = NULL;

    bs->callbacks = NULL;
    bs->callbacks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->split_record = bw_split_record_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->split_record = bw_split_record_le;
        break;
    }

    bs->write = bw_write_bits_a;
    bs->write_placeholder = bw_write_placeholder_a;
    bs->fill_placeholder = bw_fill_placeholder_a;
    bs->write_signed = bw_write_signed_bits_a;
    bs->write_64 = bw_write_bits64_a;
    bs->write_64_placeholder = bw_write_64_placeholder_a;
    bs->fill_64_placeholder = bw_fill_64_placeholder_a;
    bs->write_unary = bw_write_unary_a;
    bs->byte_align = bw_byte_align_a;
    bs->set_endianness = bw_set_endianness_a;
    bs->bits_written = bw_bits_written_a;
    bs->close = bw_close_new;
    bs->close_stream = bw_close_stream_a;

    return bs;
}

BitstreamWriter*
bw_open_recorder(bs_endianness endianness)
{
    BitstreamWriter *bs = malloc(sizeof(BitstreamWriter));
    bs->type = BW_RECORDER;

    bs->output.recorder.bits_written = 0;
    bs->output.recorder.records_written = 0;
    bs->output.recorder.records_total = 0x100;
    bs->output.recorder.records = malloc(sizeof(BitstreamRecord) *
                                         bs->output.recorder.records_total);

    bs->first_placeholder = NULL;
    bs->final_placeholder = NULL;
    bs->placeholders_used = NULL;

    bs->callbacks = NULL;
    bs->callbacks_used = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->split_record = bw_split_record_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->split_record = bw_split_record_le;
        break;
    }

    bs->write = bw_write_bits_r;
    bs->write_placeholder = bw_write_placeholder_r;
    bs->fill_placeholder = bw_fill_placeholder_r;
    bs->write_signed = bw_write_signed_bits_f_r;
    bs->write_64 = bw_write_bits64_r;
    bs->write_64_placeholder = bw_write_64_placeholder_r;
    bs->fill_64_placeholder = bw_fill_64_placeholder_r;
    bs->write_unary = bw_write_unary_f_r;
    bs->byte_align = bw_byte_align_r;
    bs->set_endianness = bw_set_endianness_r;
    bs->bits_written = bw_bits_written_r;
    bs->close = bw_close_new;
    bs->close_stream = bw_close_stream_r;

    return bs;
}

void
bw_free(BitstreamWriter* bs)
{
    struct bs_callback* callback;
    struct bs_callback* next_callback;
    struct bw_placeholder* placeholder;
    struct bw_placeholder* next_placeholder;

    for (callback = bs->callbacks; callback != NULL; callback = next_callback) {
        next_callback = callback->next;
        free(callback);
    }

    if (bs->first_placeholder != NULL) {
        fprintf(stderr, "unused placeholders remain in stream\n");
        for (placeholder = bs->first_placeholder;
             placeholder != NULL;
             placeholder = next_placeholder) {
            next_placeholder = placeholder->next;
            free(placeholder);
        }
    }

    for (placeholder = bs->placeholders_used;
         placeholder != NULL;
         placeholder = next_placeholder) {
        next_placeholder = placeholder->next;
        free(placeholder);
    }

    free(bs);
}

void
bw_add_callback(BitstreamWriter *bs, bs_callback_func callback, void *data)
{
    struct bs_callback *callback_node = malloc(sizeof(struct bs_callback));
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = bs->callbacks;
    bs->callbacks = callback_node;
}

static inline void
bw_dump_record(BitstreamWriter* target, BitstreamRecord record) {
    switch (record.type) {
    case BS_WRITE_BITS:
        target->write(target,
                      record.count,
                      record.value.unsigned_value);
        break;
    case BS_WRITE_BITS64:
        target->write_64(target,
                         record.count,
                         record.value.value64);
        break;
    case BS_SET_ENDIANNESS:
        target->set_endianness(target,
                               record.value.endianness);
        break;
    }
}

void
bw_dump_records(BitstreamWriter* target, BitstreamWriter* source)
{
    unsigned int records_written;
    unsigned int new_records_total;
    unsigned int i;

    assert(source->type == BW_RECORDER);

    records_written = source->output.recorder.records_written;

    switch (target->type) {
    case BW_RECORDER:
        /*when dumping from one recorder to another,
          use memcpy instead of looping through the records*/

        for (new_records_total = target->output.recorder.records_total;
             (new_records_total -
              target->output.recorder.records_written) < records_written;)
            new_records_total *= 2;

        if (new_records_total != target->output.recorder.records_total)
            target->output.recorder.records =
                realloc(target->output.recorder.records,
                        sizeof(BitstreamRecord) *
                        new_records_total);

        memcpy(target->output.recorder.records +
               target->output.recorder.records_written,
               source->output.recorder.records,
               sizeof(BitstreamRecord) *
               source->output.recorder.records_written);

        target->output.recorder.records_written +=
            source->output.recorder.records_written;
        target->output.recorder.bits_written +=
            source->output.recorder.bits_written;
        break;
    case BW_ACCUMULATOR:
        /*when dumping from a recorder to an accumulator,
          simply copy over the total number of written bits*/
        target->output.accumulator = source->output.recorder.bits_written;
        break;
    case BW_FILE:
        for (i = 0; i < records_written; i++)
            bw_dump_record(target, source->output.recorder.records[i]);
        break;
    default:
        /*shouldn't get here*/
        assert(0);
        break;
    }
}

unsigned int
bw_dump_records_limited(BitstreamWriter* target,
                        BitstreamWriter* remaining,
                        BitstreamWriter* source,
                        unsigned int total_bytes) {
    BitstreamRecord record;
    BitstreamRecord head;
    BitstreamRecord tail;
    unsigned int records_written;
    unsigned int i;
    unsigned int total_bits = total_bytes * 8;
    unsigned int bits_dumped = 0;

    /*FIXME - handle case in which "source" == "remaining"
      in that event, wipe placeholders from source*/

    assert(source->type == BW_RECORDER);

    records_written = source->output.recorder.records_written;

    /*first, send records from "source" to "target"
      until the bits or records are exhausted*/
    for (i = 0; (total_bits > 0) && (i < records_written); i++) {
        record = source->output.recorder.records[i];

        /*if the sent record's size exceeds the bits remaining*/
        if (record.count > total_bits) {
            /*split it in two according to the target's endianness*/
            target->split_record(&record, &head, &tail, total_bits);

            /*sending the head portion to "target"*/
            bw_dump_record(target, head);

            /*and sending the remainder to "remaining"*/
            bw_dump_record(remaining, tail);

            /*before decrementing the remaining bits according to head*/
            total_bits -= head.count;

            /*and incrementing the bits written according to head*/
            bits_dumped += head.count;
        } else {
            /*otherwise, send it to "target" as-is*/
            bw_dump_record(target, record);

            /*before decrementing the remaining bits*/
            total_bits -= record.count;

            /*and incrementing the bits written*/
            bits_dumped += record.count;
        }
    }

    /*if any records remain, send them to "remaining"*/
    for (; i < records_written; i++) {
        bw_dump_record(remaining, source->output.recorder.records[i]);
    }

    assert((bits_dumped % 8) == 0);
    return bits_dumped / 8;
}

void
bw_swap_records(BitstreamWriter* a, BitstreamWriter* b)
{
    assert(a->type == BW_RECORDER);
    assert(b->type == BW_RECORDER);

    int bits_written = a->output.recorder.bits_written;
    int records_written = a->output.recorder.records_written;
    int records_total = a->output.recorder.records_total;
    BitstreamRecord *records = a->output.recorder.records;

    a->output.recorder.bits_written = b->output.recorder.bits_written;
    a->output.recorder.records_written = b->output.recorder.records_written;
    a->output.recorder.records_total = b->output.recorder.records_total;
    a->output.recorder.records = b->output.recorder.records;

    b->output.recorder.bits_written = bits_written;
    b->output.recorder.records_written = records_written;
    b->output.recorder.records_total = records_total;
    b->output.recorder.records = records;
}

void
bw_write_bits_f_be(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

    if (value >= (1l << count)) {
        fprintf(stderr, "writing %u %u\n", count, value);
        assert(value < (1l << count));
    }


    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value >> (count - bits_to_write);

        /*prepend value to buffer*/
        bs->output.file.buffer = ((bs->output.file.buffer << bits_to_write) |
                                  value_to_write);
        bs->output.file.buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->output.file.buffer_size >= 8) {
            byte = (bs->output.file.buffer >>
                    (bs->output.file.buffer_size - 8)) & 0xFF;
            fputc(byte, bs->output.file.file);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);

            bs->output.file.buffer_size -= 8;
        }

        /*decrement the count and value*/
        value -= (value_to_write << (count - bits_to_write));
        count -= bits_to_write;
    }
}

void
bw_write_bits_f_le(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

   assert(value < (int64_t)(1LL << count));

    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value & ((1 << bits_to_write) - 1);

        /*append value to buffer*/
        bs->output.file.buffer |= (value_to_write <<
                                   bs->output.file.buffer_size);
        bs->output.file.buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->output.file.buffer_size >= 8) {
            byte = bs->output.file.buffer & 0xFF;
            fputc(byte, bs->output.file.file);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            bs->output.file.buffer >>= 8;
            bs->output.file.buffer_size -= 8;
        }

        /*decrement the count and value*/
        value >>= bits_to_write;
        count -= bits_to_write;
    }
}

void
bw_write_bits_r(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    BitstreamRecord record;

    assert(value < (1l << count));
    record.type = BS_WRITE_BITS;
    record.count = count;
    record.value.unsigned_value = value;
    bs_record_resize(bs);
    bs->output.recorder.records[bs->output.recorder.records_written++] = record;
    bs->output.recorder.bits_written += count;
}

void
bw_write_bits_a(BitstreamWriter* bs, unsigned int count, unsigned int value)
{
    assert(value < (1l << count));
    bs->output.accumulator += count;
}


void
bw_write_placeholder_f(BitstreamWriter* bs, unsigned int count,
                       unsigned int temp_value) {
    struct bw_placeholder* placeholder = bw_new_placeholder(bs);

    /*populate placeholder*/
    placeholder->type = BS_WRITE_BITS;
    placeholder->count = count;
    placeholder->function.write = bs->write;
    bw_mark_f(bs, &(placeholder->position));

    /*then write dummy value to stream*/
    bs->write(bs, count, temp_value);
}

void
bw_write_placeholder_r(BitstreamWriter* bs, unsigned int count,
                       unsigned int temp_value)  {
    struct bw_placeholder* placeholder = bw_new_placeholder(bs);

    /*populate placeholder*/
    placeholder->type = BS_WRITE_BITS;
    placeholder->count = count;
    placeholder->function.write = bs->write;
    bw_mark_r(bs, &(placeholder->position));

    /*then write dummy value to stream*/
    bs->write(bs, count, temp_value);
}
void
bw_write_placeholder_a(BitstreamWriter* bs, unsigned int count,
                       unsigned int temp_value)  {
    struct bw_placeholder* placeholder = bw_new_placeholder(bs);

    /*populate placeholder*/
    placeholder->type = BS_WRITE_BITS;

    /*then write dummy value to stream*/
    bs->write(bs, count, temp_value);
}


void
bw_fill_placeholder_f(BitstreamWriter* bs, unsigned int final_value) {
    struct bw_placeholder* placeholder = bw_use_placeholder(bs);
    union bw_mark original_position;

    if (placeholder != NULL) {
        if (placeholder->type == BS_WRITE_BITS) {
            /*save current position in stream*/
            bw_mark_f(bs, &original_position);

            /*move stream to placeholder's position*/
            bw_rewind_f(bs, &(placeholder->position));

            /*update placeholder's value according to its bit count
              and saved write function (in case endianness has changed)*/
            placeholder->function.write(bs, placeholder->count, final_value);

            /*move stream back to saved position*/
            bw_rewind_f(bs, &original_position);
        } else {
            fprintf(stderr, "placeholder type mismatch\n");
        }
    } else {
        fprintf(stderr, "no placeholder entries remain in FIFO\n");
    }
}

void
bw_fill_placeholder_r(BitstreamWriter* bs, unsigned int final_value) {
    struct bw_placeholder* placeholder = bw_use_placeholder(bs);

    if (placeholder != NULL) {
        if (placeholder->type == BS_WRITE_BITS) {
            /*overwrite record at placeholder position with new value*/

            bs->output.recorder.records[placeholder->position.recorder
                                        ].value.unsigned_value = final_value;
        } else {
            fprintf(stderr, "placeholder type mismatch\n");
        }
    } else {
        fprintf(stderr, "no placeholder entries remain in FIFO\n");
    }
}


void
bw_fill_placeholder_a(BitstreamWriter* bs, unsigned int final_value) {
    struct bw_placeholder* placeholder = bw_use_placeholder(bs);

    if (placeholder != NULL) {
        if (placeholder->type != BS_WRITE_BITS) {
            fprintf(stderr, "placeholder type mismatch\n");
        }
    } else {
        fprintf(stderr, "no placeholder entries remain in FIFO\n");
    }
}



void
bw_write_signed_bits_f_r(BitstreamWriter* bs, unsigned int count, int value)
{
    assert(value < (1 << (count - 1)));
    assert(value >= -(1 << (count - 1)));
    if (value >= 0) {
        bs->write(bs, count, value);
    } else {
        bs->write(bs, count, (1 << count) - (-value));
    }
}

void
bw_write_signed_bits_a(BitstreamWriter* bs, unsigned int count, int value)
{
    assert(value < (1 << (count - 1)));
    assert(value >= -(1 << (count - 1)));
    bs->output.accumulator += count;
}


void
bw_write_bits64_f_be(BitstreamWriter* bs, unsigned int count, uint64_t value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

    assert(value < (int64_t)(1ll << count));

    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value >> (count - bits_to_write);

        /*prepend value to buffer*/
        bs->output.file.buffer = ((bs->output.file.buffer << bits_to_write) |
                                  value_to_write);
        bs->output.file.buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->output.file.buffer_size >= 8) {
            byte = (bs->output.file.buffer >>
                    (bs->output.file.buffer_size - 8)) & 0xFF;
            fputc(byte, bs->output.file.file);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);

            bs->output.file.buffer_size -= 8;
        }

        /*decrement the count and value*/
        value -= (value_to_write << (count - bits_to_write));
        count -= bits_to_write;
    }
}

void
bw_write_bits64_f_le(BitstreamWriter* bs,
                       unsigned int count,
                       uint64_t value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

    assert(value >= 0);
    assert(value < (int64_t)(1ll << count));

    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value & ((1 << bits_to_write) - 1);

        /*append value to buffer*/
        bs->output.file.buffer |= (value_to_write <<
                                   bs->output.file.buffer_size);
        bs->output.file.buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->output.file.buffer_size >= 8) {
            byte = bs->output.file.buffer & 0xFF;
            fputc(byte, bs->output.file.file);
            for (callback = bs->callbacks;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            bs->output.file.buffer >>= 8;
            bs->output.file.buffer_size -= 8;
        }

        /*decrement the count and value*/
        value >>= bits_to_write;
        count -= bits_to_write;
    }
}

void
bw_write_bits64_r(BitstreamWriter* bs, unsigned int count, uint64_t value)
{
    BitstreamRecord record;

    assert(value >= 0l);
    assert(value < (int64_t)(1ll << count));

    record.type = BS_WRITE_BITS64;
    record.count = count;
    record.value.value64 = value;
    bs_record_resize(bs);
    bs->output.recorder.records[bs->output.recorder.records_written++] = record;
    bs->output.recorder.bits_written += count;
}

void
bw_write_bits64_a(BitstreamWriter* bs, unsigned int count, uint64_t value)
{
    assert(value >= 0l);
    assert(value < (int64_t)(1ll << count));
    bs->output.accumulator += count;
}


void
bw_write_64_placeholder_f(BitstreamWriter* bs, unsigned int count,
                          uint64_t temp_value) {
    struct bw_placeholder* placeholder = bw_new_placeholder(bs);

    /*populate placeholder*/
    placeholder->type = BS_WRITE_BITS64;
    placeholder->count = count;
    placeholder->function.write_64 = bs->write_64;
    bw_mark_f(bs, &(placeholder->position));

    /*then write dummy value to stream*/
    bs->write_64(bs, count, temp_value);
}

void
bw_write_64_placeholder_r(BitstreamWriter* bs, unsigned int count,
                          uint64_t temp_value) {
    struct bw_placeholder* placeholder = bw_new_placeholder(bs);

    /*populate placeholder*/
    placeholder->type = BS_WRITE_BITS64;
    placeholder->count = count;
    placeholder->function.write_64 = bs->write_64;
    bw_mark_r(bs, &(placeholder->position));

    /*then write dummy value to stream*/
    bs->write_64(bs, count, temp_value);
}

void
bw_write_64_placeholder_a(BitstreamWriter* bs, unsigned int count,
                          uint64_t temp_value) {
    struct bw_placeholder* placeholder = bw_new_placeholder(bs);

    /*populate placeholder*/
    placeholder->type = BS_WRITE_BITS64;

    /*then write dummy value to stream*/
    bs->write(bs, count, temp_value);
}


void
bw_fill_64_placeholder_f(BitstreamWriter* bs, uint64_t final_value) {
    struct bw_placeholder* placeholder = bw_use_placeholder(bs);
    union bw_mark original_position;

    if (placeholder != NULL) {
        if (placeholder->type == BS_WRITE_BITS64) {
            /*save current position in stream*/
            bw_mark_f(bs, &original_position);

            /*move stream to placeholder's position*/
            bw_rewind_f(bs, &(placeholder->position));

            /*update placeholder's value according to its bit count
              and saved write function (in case endianness has changed)*/
            placeholder->function.write_64(bs, placeholder->count, final_value);

            /*move stream back to saved position*/
            bw_rewind_f(bs, &original_position);
        } else {
            fprintf(stderr, "placeholder type mismatch\n");
        }
    } else {
        fprintf(stderr, "no placeholder entries remain in FIFO\n");
    }
}

void
bw_fill_64_placeholder_r(BitstreamWriter* bs, uint64_t final_value) {
    struct bw_placeholder* placeholder = bw_use_placeholder(bs);

    if (placeholder != NULL) {
        if (placeholder->type == BS_WRITE_BITS64) {
            /*overwrite record at placeholder position with new value*/

            bs->output.recorder.records[placeholder->position.recorder
                                        ].value.value64 = final_value;
        } else {
            fprintf(stderr, "placeholder type mismatch\n");
        }
    } else {
        fprintf(stderr, "no placeholder entries remain in FIFO\n");
    }
}

void
bw_fill_64_placeholder_a(BitstreamWriter* bs, uint64_t final_value) {
    struct bw_placeholder* placeholder = bw_use_placeholder(bs);

    if (placeholder != NULL) {
        if (placeholder->type != BS_WRITE_BITS64) {
            fprintf(stderr, "placeholder type mismatch\n");
        }
    } else {
        fprintf(stderr, "no placeholder entries remain in FIFO\n");
    }
}


#define UNARY_BUFFER_SIZE 30

void
bw_write_unary_f_r(BitstreamWriter* bs, int stop_bit, unsigned int value)
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
bw_byte_align_f(BitstreamWriter* bs) {
    /*write enough 0 bits to completely fill the buffer
      which results in a byte being written*/
    if (bs->output.file.buffer_size > 0)
        bs->write(bs, 8 - bs->output.file.buffer_size, 0);
}

void
bw_byte_align_r(BitstreamWriter* bs)
{
    if (bs->output.recorder.bits_written % 8)
        bw_write_bits_r(bs, 8 - (bs->output.recorder.bits_written % 8), 0);
}

void
bw_byte_align_a(BitstreamWriter* bs)
{
    if (bs->output.accumulator % 8)
        bs->output.accumulator += (8 - (bs->output.accumulator % 8));
}



unsigned int
bw_bits_written_f(BitstreamWriter* bs) {
    /*actual file writing doesn't keep track of bits written
      since the total could be extremely large*/
    return 0;
}

unsigned int
bw_bits_written_r(BitstreamWriter* bs) {
    return bs->output.recorder.bits_written;
}

unsigned int
bw_bits_written_a(BitstreamWriter* bs) {
    return bs->output.accumulator;
}


void
bw_set_endianness_f_be(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->output.file.buffer = 0;
    bs->output.file.buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = bw_write_bits_f_le;
        bs->write_64 = bw_write_bits64_f_le;
        bs->set_endianness = bw_set_endianness_f_le;
        bs->split_record = bw_split_record_le;
    }
}

void
bw_set_endianness_f_le(BitstreamWriter* bs, bs_endianness endianness)
{
    bs->output.file.buffer = 0;
    bs->output.file.buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = bw_write_bits_f_be;
        bs->write_64 = bw_write_bits64_f_be;
        bs->set_endianness = bw_set_endianness_f_be;
        bs->split_record = bw_split_record_be;
    }
}

void
bw_set_endianness_r(BitstreamWriter* bs, bs_endianness endianness)
{
    BitstreamRecord record;
    record.type = BS_SET_ENDIANNESS;
    record.count = 0;
    record.value.endianness = endianness;
    bs_record_resize(bs);
    bs->output.recorder.records[bs->output.recorder.records_written++] = record;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->split_record = bw_split_record_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->split_record = bw_split_record_le;
        break;
    }

    bw_byte_align_r(bs);
}

void
bw_set_endianness_a(BitstreamWriter* bs, bs_endianness endianness)
{
    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->split_record = bw_split_record_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->split_record = bw_split_record_le;
        break;
    }

    /*swapping endianness results in a byte alignment*/
    bw_byte_align_a(bs);
}


void
bw_mark_f(BitstreamWriter* bs, union bw_mark* position) {
    fgetpos(bs->output.file.file, &(position->file.pos));
    position->file.buffer_size = bs->output.file.buffer_size;
    position->file.buffer = bs->output.file.buffer;
}

void
bw_mark_r(BitstreamWriter* bs, union bw_mark* position) {
    position->recorder = bs->output.recorder.records_written;
}

void
bw_rewind_f(BitstreamWriter* bs, union bw_mark* position) {
    fsetpos(bs->output.file.file, &(position->file.pos));
    bs->output.file.buffer_size = position->file.buffer_size;
    bs->output.file.buffer = position->file.buffer;
}

void
bw_close_new(BitstreamWriter* bs) {
    bs->close_stream(bs);
    bw_free(bs);
}


void
bw_close_stream_f(BitstreamWriter* bs)
{
    fclose(bs->output.file.file);
}

void
bw_close_stream_r(BitstreamWriter* bs)
{
    free(bs->output.recorder.records);
}

void
bw_close_stream_a(BitstreamWriter* bs)
{
    return;
}

void
bw_split_record_be(BitstreamRecord* record,
                   BitstreamRecord* head,
                   BitstreamRecord* tail,
                   unsigned int bits)
{
    assert((record->type == BS_WRITE_BITS) ||
           (record->type == BS_WRITE_BITS64));

    head->type = tail->type = record->type;

    if (bits > 0) {
        if (record->count > bits) {
            /*put up to "bits" in "head"*/
            /*and the remainder in "tail"*/
            head->count = bits;
            tail->count = record->count - bits;
            switch (record->type) {
            case BS_WRITE_BITS:
                head->value.unsigned_value =
                    record->value.unsigned_value >> tail->count;
                tail->value.unsigned_value =
                    record->value.unsigned_value & ((1 << tail->count) - 1);
                break;
            case BS_WRITE_BITS64:
                head->value.value64 =
                    record->value.value64 >> tail->count;
                tail->value.value64 =
                    record->value.value64 & ((1 << tail->count) - 1);
                break;
            default:
                assert(0);
                break;
            }
        } else {
            /*put all data in "head"*/
            /*and no data in "tail", which means a 0 bit write*/
            head->count = record->count;
            tail->count = 0;
            switch (record->type) {
            case BS_WRITE_BITS:
                head->value.unsigned_value = record->value.unsigned_value;
                tail->value.unsigned_value = 0;
                break;
            case BS_WRITE_BITS64:
                head->value.value64 = record->value.value64;
                tail->value.value64 = 0;
                break;
            default:
                assert(0);
                break;
            }
        }
    } else {
        /*put no data in "head", which means a 0 bit write*/
        /*and all the data in "tail"*/
        head->count = 0;
        tail->count = record->count;
        switch (record->type) {
        case BS_WRITE_BITS:
            head->value.unsigned_value = 0;
            tail->value.unsigned_value = record->value.unsigned_value;
            break;
        case BS_WRITE_BITS64:
            head->value.value64 = 0;
            tail->value.value64 = record->value.value64;
            break;
        default:
            assert(0);
            break;
        }
    }
}

void
bw_split_record_le(BitstreamRecord* record,
                   BitstreamRecord* head,
                   BitstreamRecord* tail,
                   unsigned int bits)
{
    assert((record->type == BS_WRITE_BITS) ||
           (record->type == BS_WRITE_BITS64));

    head->type = tail->type = record->type;

    if (bits > 0) {
        if (record->count > bits) {
            /*put up to "bits" in "head"*/
            /*and the remainder in "tail"*/
            head->count = bits;
            tail->count = record->count - bits;
            switch (record->type) {
            case BS_WRITE_BITS:
                head->value.unsigned_value =
                    record->value.unsigned_value & ((1 << bits) - 1);
                tail->value.unsigned_value =
                    record->value.unsigned_value >> bits;
                break;
            case BS_WRITE_BITS64:
                head->value.value64 =
                    record->value.value64 & ((1 << bits) - 1);
                tail->value.value64 =
                    record->value.value64 >> bits;
                break;
            default:
                assert(0);
                break;
            }
        } else {
            /*put all data in "head"*/
            /*and no data in "tail", which means a 0 bit write*/
            head->count = record->count;
            tail->count = 0;
            switch (record->type) {
            case BS_WRITE_BITS:
                head->value.unsigned_value = record->value.unsigned_value;
                tail->value.unsigned_value = 0;
                break;
            case BS_WRITE_BITS64:
                head->value.value64 = record->value.value64;
                tail->value.value64 = 0;
                break;
            default:
                assert(0);
                break;
            }
        }
    } else {
        /*put no data in "head", which means a 0 bit write*/
        /*and all the data in "tail"*/
        head->count = 0;
        tail->count = record->count;
        switch (record->type) {
        case BS_WRITE_BITS:
            head->value.unsigned_value = 0;
            tail->value.unsigned_value = record->value.unsigned_value;
            break;
        case BS_WRITE_BITS64:
            head->value.value64 = 0;
            tail->value.value64 = record->value.value64;
            break;
        default:
            assert(0);
            break;
        }
    }
}

struct bw_placeholder*
bw_new_placeholder(BitstreamWriter* bs) {
    struct bw_placeholder* placeholder;

    /*first, either allocate or recycle a placeholder entry*/
    if (bs->placeholders_used != NULL) {
        placeholder = bs->placeholders_used;
        bs->placeholders_used = bs->placeholders_used->next;
    } else {
        placeholder = malloc(sizeof(struct bw_placeholder));
    }

    /*then place it in the bitstream's FIFO*/
    if (bs->final_placeholder != NULL) {
        bs->final_placeholder->next = placeholder;
        bs->final_placeholder = placeholder;
    } else {
        bs->first_placeholder = bs->final_placeholder = placeholder;
    }

    placeholder->next = NULL;

    return placeholder;
}

struct bw_placeholder*
bw_use_placeholder(BitstreamWriter* bs) {
    struct bw_placeholder* placeholder = bs->first_placeholder;

    if (placeholder != NULL) {
        bs->first_placeholder = bs->first_placeholder->next;
        if (bs->first_placeholder == NULL)
            /*if we've used the last placeholder,
              the final placeholder must also be marked used*/
            bs->final_placeholder = NULL;
        placeholder->next = bs->placeholders_used;
        bs->placeholders_used = placeholder;
        return placeholder;
    } else
        return NULL;
}



/*****************************************************************
 BEGIN UNIT TESTS
 *****************************************************************/


#ifdef EXECUTABLE

#include <unistd.h>
#include <signal.h>
#include "huffman.h"

char temp_filename[] = "bitstream.XXXXXX";

void atexit_cleanup(void);
void sigabort_cleanup(int signum);

void test_big_endian_reader(BitstreamReader* reader,
                            struct br_huffman_table (*table)[][0x200]);
void test_little_endian_reader(BitstreamReader* reader,
                               struct br_huffman_table (*table)[][0x200]);

void test_try(BitstreamReader* reader,
              struct br_huffman_table (*table)[][0x200]);

void test_callbacks_reader(BitstreamReader* reader,
                           int unary_0_reads,
                           int unary_1_reads,
                           struct br_huffman_table (*table)[][0x200],
                           int huffman_code_count);

void
byte_counter(uint8_t byte, unsigned int* count);

/*this uses "temp_filename" as an output file and opens it separately*/
void
test_writer(bs_endianness endianness);

void
writer_perform_write(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_signed(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_64(BitstreamWriter* writer, bs_endianness endianness);
void
writer_perform_write_unary_0(BitstreamWriter* writer,
                             bs_endianness endianness);
void
writer_perform_write_unary_1(BitstreamWriter* writer,
                             bs_endianness endianness);

typedef void (*write_check)(BitstreamWriter*, bs_endianness);


void
check_output_file(void);

int main(int argc, char* argv[]) {
    int fd;
    FILE* temp_file;
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
    compile_huffman_table(&be_table, frequencies, 5, BS_BIG_ENDIAN);
    compile_huffman_table(&le_table, frequencies, 5, BS_LITTLE_ENDIAN);

    /*write some test data to the temporary file*/
    fputc(0xB1, temp_file);
    fputc(0xED, temp_file);
    fputc(0x3B, temp_file);
    fputc(0xC1, temp_file);
    fseek(temp_file, 0, SEEK_SET);

    /*test a big-endian stream*/
    reader = br_open(temp_file, BS_BIG_ENDIAN);
    test_big_endian_reader(reader, be_table);
    test_try(reader, be_table);
    test_callbacks_reader(reader, 14, 18, be_table, 14);
    br_free(reader);

    fseek(temp_file, 0, SEEK_SET);

    /*test a little-endian stream*/
    reader = br_open(temp_file, BS_LITTLE_ENDIAN);
    test_little_endian_reader(reader, le_table);
    test_try(reader, le_table);
    test_callbacks_reader(reader, 14, 18, le_table, 13);
    br_free(reader);

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
    test_try(subreader, be_table);
    test_callbacks_reader(subreader, 14, 18, be_table, 14);
    br_substream_reset(subreader);

    /*check a big-endian substream built from another substream*/
    reader->rewind(reader);
    reader->skip(reader, 8);
    reader->substream_append(reader, subreader, 6);
    subreader->skip(subreader, 8);
    subsubreader = br_substream_new(BS_BIG_ENDIAN);
    subreader->substream_append(subreader, subsubreader, 4);
    test_big_endian_reader(subsubreader, be_table);
    test_try(subsubreader, be_table);
    test_callbacks_reader(subsubreader, 14, 18, be_table, 14);
    subsubreader->close(subsubreader);
    subreader->close(subreader);
    reader->rewind(reader);
    reader->unmark(reader);
    br_free(reader);

    reader = br_open(temp_file, BS_LITTLE_ENDIAN);
    reader->mark(reader);

    /*check a little-endian substream built from a file*/
    subreader = br_substream_new(BS_LITTLE_ENDIAN);
    reader->skip(reader, 16);
    reader->substream_append(reader, subreader, 4);
    test_little_endian_reader(subreader, le_table);
    test_try(subreader, le_table);
    test_callbacks_reader(subreader, 14, 18, le_table, 13);
    br_substream_reset(subreader);

    /*check a little-endian substream built from another substream*/
    reader->rewind(reader);
    reader->skip(reader, 8);
    reader->substream_append(reader, subreader, 6);
    subreader->skip(subreader, 8);
    subsubreader = br_substream_new(BS_LITTLE_ENDIAN);
    subreader->substream_append(subreader, subsubreader, 4);
    test_little_endian_reader(subsubreader, le_table);
    test_try(subsubreader, le_table);
    test_callbacks_reader(subsubreader, 14, 18, le_table, 13);
    subsubreader->close(subsubreader);
    subreader->close(subreader);
    reader->rewind(reader);
    reader->unmark(reader);
    br_free(reader);

    free(be_table);
    free(le_table);

    test_writer(BS_BIG_ENDIAN);
    test_writer(BS_LITTLE_ENDIAN);

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
        reader->skip(reader, 2);
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
    br_add_callback(reader, (bs_callback_func)byte_counter, &byte_count);

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
    br_add_callback(reader, (bs_callback_func)byte_counter, &byte_count);
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
    br_add_callback(reader, (bs_callback_func)byte_counter, &byte_count);
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
byte_counter(uint8_t byte, unsigned int* count) {
    (*count)++;
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
                            writer_perform_write_unary_0,
                            writer_perform_write_unary_1};
    int total_checks = 5;

    /*perform file-based checks*/
    for (i = 0; i < total_checks; i++) {
        output_file = fopen(temp_filename, "wb");
        assert(output_file != NULL);
        writer = bw_open(output_file, endianness);
        checks[i](writer, endianness);
        fflush(output_file);
        check_output_file();
        bw_free(writer);
        fclose(output_file);
    }

    /*perform recorder-based checks*/
    for (i = 0; i < total_checks; i++) {
        output_file = fopen(temp_filename, "wb");
        assert(output_file != NULL);
        writer = bw_open(output_file, endianness);
        sub_writer = bw_open_recorder(endianness);
        assert(sub_writer->bits_written(sub_writer) == 0);
        checks[i](sub_writer, endianness);
        bw_dump_records(writer, sub_writer);
        fflush(output_file);
        check_output_file();
        bw_free(writer);
        assert(sub_writer->bits_written(sub_writer) == 32);
        sub_writer->close(sub_writer);
        fclose(output_file);
    }

    /*perform accumulator-based checks*/
    for (i = 0; i < total_checks; i++) {
        writer = bw_open_accumulator(endianness);
        assert(writer->bits_written(writer) == 0);
        checks[i](writer, endianness);
        assert(writer->bits_written(writer) == 32);
        writer->close(writer);
    }

    /*check endianness setting*/
    /*FIXME*/

    /*check a file-based byte-align*/
    /*FIXME*/

    /*check a recoder-based byte-align*/
    /*FIXME*/

    /*check an accumulator-based byte-align*/
    /*FIXME*/

    /*check partial dump*/
    /*FIXME*/

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
        bw_dump_records(sub_writer, sub_sub_writer);
        assert(sub_writer->bits_written(sub_writer) == 32);
        assert(sub_writer->bits_written(sub_sub_writer) == 32);
        bw_dump_records(writer, sub_writer);
        fflush(output_file);
        check_output_file();
        bw_free(writer);
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
        bw_dump_records(writer, sub_writer);
        assert(writer->bits_written(writer) == 32);
        assert(sub_writer->bits_written(sub_writer) == 32);
        writer->close(writer);
        sub_writer->close(sub_writer);
    }
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
check_output_file(void) {
    FILE* output_file;
    uint8_t data[255];
    uint8_t expected_data[] = {0xB1, 0xED, 0x3B, 0xC1};

    output_file = fopen(temp_filename, "rb");
    assert(fread(data, sizeof(uint8_t), 255, output_file) == 4);
    assert(memcmp(data, expected_data, 4) == 0);

    fclose(output_file);
}


#endif
