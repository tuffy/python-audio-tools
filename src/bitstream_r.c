#include "bitstream_r.h"
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

Bitstream*
bs_open(FILE *f, bs_endianness endianness)
{
    Bitstream *bs = malloc(sizeof(Bitstream));
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
        bs->read = bs_read_bits_f_be;
        bs->read_signed = bs_read_signed_bits_f_be;
        bs->read_64 = bs_read_bits64_f_be;
        bs->skip = bs_skip_bits_f_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_f_be;
        bs->read_limited_unary = bs_read_limited_unary_f_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_f_be;
        bs->substream = bs_substream_f_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = bs_read_bits_f_le;
        bs->read_signed = bs_read_signed_bits_f_le;
        bs->read_64 = bs_read_bits64_f_le;
        bs->skip = bs_skip_bits_f_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_f_le;
        bs->read_limited_unary = bs_read_limited_unary_f_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_f_le;
        bs->substream = bs_substream_f_le;
        break;
    }
    bs->read_huffman_code = bs_read_huffman_code_f;
    bs->substream_append = bs_substream_append_f;
    bs->close = bs_close;
    bs->close_stream = bs_close_stream_f;
    bs->mark = bs_mark_f;
    bs->rewind = bs_rewind_f;
    bs->unmark = bs_unmark_f;

    return bs;
}

void
bs_free(Bitstream *bs) {
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;
    struct bs_mark *m_node;
    struct bs_mark *m_next;

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
bs_close(Bitstream *bs) {
    bs->close_stream(bs);
    bs_free(bs);
}

void
bs_noop(Bitstream *bs) {
    return;
}

void
bs_close_stream_f(Bitstream *bs)
{
    if (bs == NULL)
        return;
    else if (bs->input.file != NULL) {
        fclose(bs->input.file);
        bs->close_stream = bs_noop;
    }
}

void
bs_add_callback(Bitstream *bs, bs_callback_func callback, void *data)
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
bs_call_callbacks(Bitstream *bs, uint8_t byte) {
    struct bs_callback *callback;
    for (callback = bs->callbacks;
         callback != NULL;
         callback = callback->next)
        callback->callback(byte, callback->data);
}

void
bs_push_callback(Bitstream *bs, struct bs_callback *callback) {
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
bs_pop_callback(Bitstream *bs, struct bs_callback *callback) {
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
bs_abort(Bitstream *bs) {
    if (bs->exceptions != NULL) {
        longjmp(bs->exceptions->env, 1);
    } else {
        fprintf(stderr, "EOF encountered, aborting\n");
        exit(1);
    }
}


jmp_buf*
bs_try(Bitstream *bs) {
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
bs_etry(Bitstream *bs) {
    struct bs_exception *node = bs->exceptions;
    if (node != NULL) {
        bs->exceptions = node->next;
        node->next = bs->exceptions_used;
        bs->exceptions_used = node;
    } else {
        fprintf(stderr,"Warning: trying to pop from empty etry stack\n");
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
bs_read_bits_f_be(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits_f_le(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits_s_be(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits_s_le(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits_p_be(Bitstream* bs, unsigned int count) {
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
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
bs_read_bits_p_le(Bitstream* bs, unsigned int count) {
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
                bs_abort(bs);
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
bs_read_signed_bits_f_be(Bitstream* bs, unsigned int count)
{
    if (!bs_read_bits_f_be(bs, 1)) {
        return bs_read_bits_f_be(bs, count - 1);
    } else {
        return bs_read_bits_f_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
bs_read_signed_bits_f_le(Bitstream* bs, unsigned int count)
{
    int unsigned_value = bs_read_bits_f_le(bs, count - 1);

    if (!bs_read_bits_f_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}

int
bs_read_signed_bits_s_be(Bitstream* bs, unsigned int count)
{
    if (!bs_read_bits_s_be(bs, 1)) {
        return bs_read_bits_s_be(bs, count - 1);
    } else {
        return bs_read_bits_s_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
bs_read_signed_bits_s_le(Bitstream* bs, unsigned int count)
{
    int unsigned_value = bs_read_bits_s_le(bs, count - 1);

    if (!bs_read_bits_s_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}

#ifndef STANDALONE
int
bs_read_signed_bits_p_be(Bitstream* bs, unsigned int count) {
    if (!bs_read_bits_p_be(bs, 1)) {
        return bs_read_bits_p_be(bs, count - 1);
    } else {
        return bs_read_bits_p_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
bs_read_signed_bits_p_le(Bitstream* bs, unsigned int count) {
    int unsigned_value = bs_read_bits_p_le(bs, count - 1);

    if (!bs_read_bits_p_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}
#endif


/*the read_bits64 functions differ from the read_bits functions
  only by the size of the accumulator*/
uint64_t
bs_read_bits64_f_be(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits64_f_le(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits64_s_be(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits64_s_le(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_read_bits64_p_be(Bitstream* bs, unsigned int count) {
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
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
bs_read_bits64_p_le(Bitstream* bs, unsigned int count) {
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
                bs_abort(bs);
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
bs_skip_bits_f_be(Bitstream* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                bs_abort(bs);
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
bs_skip_bits_f_le(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_skip_bits_s_be(Bitstream* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                bs_abort(bs);
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
bs_skip_bits_s_le(Bitstream* bs, unsigned int count)
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
                bs_abort(bs);
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
bs_skip_bits_p_be(Bitstream* bs, unsigned int count) {
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
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
bs_skip_bits_p_le(Bitstream* bs, unsigned int count) {
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    int output_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
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
bs_unread_bit_be(Bitstream* bs, int unread_bit)
{
    unsigned int result = unread_bit_table[bs->state][unread_bit];
    assert(UNREAD_BIT_LIMIT_REACHED(result) == 0);
    bs->state = NEXT_CONTEXT(result);
}

void
bs_unread_bit_le(Bitstream* bs, int unread_bit)
{
    unsigned int result = unread_bit_table_le[bs->state][unread_bit];
    assert(UNREAD_BIT_LIMIT_REACHED(result) == 0);
    bs->state = NEXT_CONTEXT(result);
}


unsigned int
bs_read_unary_f_be(Bitstream* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                bs_abort(bs);
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
bs_read_unary_f_le(Bitstream* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->input.file)) == EOF)
                bs_abort(bs);
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
bs_read_unary_s_be(Bitstream* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                bs_abort(bs);
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
bs_read_unary_s_le(Bitstream* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = buf_getc(bs->input.substream)) == EOF)
                bs_abort(bs);
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
bs_read_unary_p_be(Bitstream* bs, int stop_bit) {
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
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
bs_read_unary_p_le(Bitstream* bs, int stop_bit) {
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
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
bs_read_limited_unary_f_be(Bitstream* bs, int stop_bit, int maximum_bits)
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
                bs_abort(bs);
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
bs_read_limited_unary_f_le(Bitstream* bs, int stop_bit, int maximum_bits)
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
                bs_abort(bs);
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
bs_read_limited_unary_s_be(Bitstream* bs, int stop_bit, int maximum_bits)
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
                bs_abort(bs);
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
bs_read_limited_unary_s_le(Bitstream* bs, int stop_bit, int maximum_bits)
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
                bs_abort(bs);
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
bs_read_limited_unary_p_be(Bitstream* bs, int stop_bit, int maximum_bits) {
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
                bs_abort(bs);
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
bs_read_limited_unary_p_le(Bitstream* bs, int stop_bit, int maximum_bits) {
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
                bs_abort(bs);
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
bs_set_endianness_f_be(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = bs_read_bits_f_le;
        bs->read_signed = bs_read_signed_bits_f_le;
        bs->read_64 = bs_read_bits64_f_le;
        bs->skip = bs_skip_bits_f_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_f_le;
        bs->read_limited_unary = bs_read_limited_unary_f_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_f_le;
        bs->substream = bs_substream_f_le;
    }
}

void
bs_set_endianness_f_le(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = bs_read_bits_f_be;
        bs->read_signed = bs_read_signed_bits_f_be;
        bs->read_64 = bs_read_bits64_f_be;
        bs->skip = bs_skip_bits_f_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_f_be;
        bs->read_limited_unary = bs_read_limited_unary_f_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_f_be;
        bs->substream = bs_substream_f_be;
    }
}

void
bs_set_endianness_s_be(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = bs_read_bits_s_le;
        bs->read_signed = bs_read_signed_bits_s_le;
        bs->read_64 = bs_read_bits64_s_le;
        bs->skip = bs_skip_bits_s_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_s_le;
        bs->read_limited_unary = bs_read_limited_unary_s_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_s_le;
        bs->substream = bs_substream_s_le;
    }
}

void
bs_set_endianness_s_le(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = bs_read_bits_s_be;
        bs->read_signed = bs_read_signed_bits_s_be;
        bs->read_64 = bs_read_bits64_s_be;
        bs->skip = bs_skip_bits_s_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_s_be;
        bs->read_limited_unary = bs_read_limited_unary_s_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_s_be;
        bs->substream = bs_substream_s_be;
    }
}

#ifndef STANDALONE
void
bs_set_endianness_p_be(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = bs_read_bits_p_le;
        bs->read_signed = bs_read_signed_bits_p_le;
        bs->read_64 = bs_read_bits64_p_le;
        bs->skip = bs_skip_bits_p_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_p_le;
        bs->read_limited_unary = bs_read_limited_unary_p_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_p_le;
        bs->substream = bs_substream_p_le;
    }
}

void
bs_set_endianness_p_le(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = bs_read_bits_p_be;
        bs->read_signed = bs_read_signed_bits_p_be;
        bs->read_64 = bs_read_bits64_p_be;
        bs->skip = bs_skip_bits_p_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_p_be;
        bs->read_limited_unary = bs_read_limited_unary_p_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_p_be;
        bs->substream = bs_substream_p_be;
    }
}
#endif


/*
Note that read_huffman_code has no endianness variants.
Which direction it reads from is decided when the table data is compiled.
*/
int
bs_read_huffman_code_f(Bitstream *bs,
                       struct bs_huffman_table table[][0x200]) {
    struct bs_huffman_table entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

    entry = table[node][context];
    while (READ_HUFFMAN_CONTINUE(entry.context_node)) {
        if ((byte = fgetc(bs->input.file)) == EOF)
            bs_abort(bs);
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
bs_read_huffman_code_s(Bitstream *bs,
                       struct bs_huffman_table table[][0x200]) {
    struct bs_huffman_table entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

    entry = table[node][context];
    while (READ_HUFFMAN_CONTINUE(entry.context_node)) {
        if ((byte = buf_getc(bs->input.substream)) == EOF)
            bs_abort(bs);
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
bs_read_huffman_code_p(Bitstream *bs,
                       struct bs_huffman_table table[][0x200]) {
    struct bs_huffman_table entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

    entry = table[node][context];
    while (READ_HUFFMAN_CONTINUE(entry.context_node)) {
        if ((byte = py_getc(bs->input.python)) == EOF)
            bs_abort(bs);
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
bs_mark_f(Bitstream* bs) {
    struct bs_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct bs_mark));
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
bs_mark_s(Bitstream* bs) {
    struct bs_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct bs_mark));
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
bs_mark_p(Bitstream* bs) {
    struct bs_mark* mark;

    if (bs->marks_used == NULL)
        mark = malloc(sizeof(struct bs_mark));
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
bs_rewind_f(Bitstream* bs) {
    if (bs->marks != NULL) {
        fsetpos(bs->input.file, &(bs->marks->position.file));
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

void
bs_rewind_s(Bitstream* bs) {
    if (bs->marks != NULL) {
        bs->input.substream->buffer_position = bs->marks->position.substream;
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

#ifndef STANDALONE
void
bs_rewind_p(Bitstream* bs) {
    if (bs->marks != NULL) {
        bs->input.python->buffer_position = bs->marks->position.python;
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}
#endif


void
bs_unmark_f(Bitstream* bs) {
    struct bs_mark* mark = bs->marks;
    bs->marks = mark->next;
    mark->next = bs->marks_used;
    bs->marks_used = mark;
}

void
bs_unmark_s(Bitstream* bs) {
    struct bs_mark* mark = bs->marks;
    bs->marks = mark->next;
    mark->next = bs->marks_used;
    bs->marks_used = mark;
    bs->input.substream->mark_in_progress = (bs->marks != NULL);
}

#ifndef STANDALONE
void
bs_unmark_p(Bitstream* bs) {
    struct bs_mark* mark = bs->marks;
    bs->marks = mark->next;
    mark->next = bs->marks_used;
    bs->marks_used = mark;
    bs->input.python->mark_in_progress = (bs->marks != NULL);
}
#endif


void
bs_byte_align_r(Bitstream* bs)
{
    bs->state = 0;
}


/*******************************************
 substream handlers

 for pulling smaller pieces out of a larger stream
 and processing them separately
 *******************************************/

struct bs_buffer*
buf_new(void) {
    struct bs_buffer* stream = malloc(sizeof(struct bs_buffer));
    stream->buffer_size = 0;
    stream->buffer_total_size = 1;
    stream->buffer = malloc(stream->buffer_total_size);
    stream->buffer_position = 0;
    stream->mark_in_progress = 0;
    return stream;
}

uint32_t
buf_size(struct bs_buffer *stream) {
    return stream->buffer_size - stream->buffer_position;
}

uint8_t*
buf_extend(struct bs_buffer *stream, uint32_t data_size) {
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
                  shift the buffer down and reuse them*/
                memmove(stream->buffer,
                        stream->buffer + stream->buffer_position,
                        stream->buffer_size - stream->buffer_position);
                stream->buffer_size -= stream->buffer_position;
                stream->buffer_position = 0;
            }
        }
    }

    extended_buffer = stream->buffer + stream->buffer_size;

    return extended_buffer;
}

void
buf_reset(struct bs_buffer *stream) {
    stream->buffer_size = 0;
    stream->buffer_position = 0;
    stream->mark_in_progress = 0;
}

int
buf_getc(struct bs_buffer *stream) {
    if (stream->buffer_position < stream->buffer_size) {
        return stream->buffer[stream->buffer_position++];
    } else
        return EOF;
}

void
buf_close(struct bs_buffer *stream) {
    if (stream->buffer != NULL)
        free(stream->buffer);
    free(stream);
}


struct Bitstream_s* bs_substream_new(bs_endianness endianness) {
    Bitstream *bs = malloc(sizeof(Bitstream));
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
        bs->read = bs_read_bits_s_be;
        bs->read_signed = bs_read_signed_bits_s_be;
        bs->read_64 = bs_read_bits64_s_be;
        bs->skip = bs_skip_bits_s_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_s_be;
        bs->read_limited_unary = bs_read_limited_unary_s_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_s_be;
        bs->substream = bs_substream_s_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = bs_read_bits_s_le;
        bs->read_signed = bs_read_signed_bits_s_le;
        bs->read_64 = bs_read_bits64_s_le;
        bs->skip = bs_skip_bits_s_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_s_le;
        bs->read_limited_unary = bs_read_limited_unary_s_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_s_le;
        bs->substream = bs_substream_s_le;
        break;
    }
    bs->read_huffman_code = bs_read_huffman_code_s;
    bs->substream_append = bs_substream_append_s;
    bs->close = bs_close;
    bs->close_stream = bs_close_stream_s;
    bs->mark = bs_mark_s;
    bs->rewind = bs_rewind_s;
    bs->unmark = bs_unmark_s;

    return bs;
}

void
bs_substream_reset(struct Bitstream_s *substream) {
    struct bs_mark *m_node;
    struct bs_mark *m_next;

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

struct Bitstream_s* bs_substream_f_be(struct Bitstream_s *stream,
                                      uint32_t bytes) {
    struct Bitstream_s* substream = bs_substream_new(BS_BIG_ENDIAN);
    bs_substream_append_f(stream, substream, bytes);
    return substream;
}

struct Bitstream_s* bs_substream_f_le(struct Bitstream_s *stream,
                                      uint32_t bytes) {
    struct Bitstream_s* substream = bs_substream_new(BS_LITTLE_ENDIAN);
    bs_substream_append_f(stream, substream, bytes);
    return substream;
}

#ifndef STANDALONE
struct Bitstream_s* bs_substream_p_be(struct Bitstream_s *stream,
                                      uint32_t bytes) {
    struct Bitstream_s* substream = bs_substream_new(BS_BIG_ENDIAN);
    bs_substream_append_p(stream, substream, bytes);
    return substream;
}

struct Bitstream_s* bs_substream_p_le(struct Bitstream_s *stream,
                                      uint32_t bytes) {
    struct Bitstream_s* substream = bs_substream_new(BS_LITTLE_ENDIAN);
    bs_substream_append_p(stream, substream, bytes);
    return substream;
}
#endif

struct Bitstream_s* bs_substream_s_be(struct Bitstream_s *stream,
                                      uint32_t bytes) {
    struct Bitstream_s* substream = bs_substream_new(BS_BIG_ENDIAN);
    bs_substream_append_s(stream, substream, bytes);
    return substream;
}

struct Bitstream_s* bs_substream_s_le(struct Bitstream_s *stream,
                                      uint32_t bytes) {
    struct Bitstream_s* substream = bs_substream_new(BS_LITTLE_ENDIAN);
    bs_substream_append_s(stream, substream, bytes);
    return substream;
}

void bs_substream_append_f(struct Bitstream_s *stream,
                           struct Bitstream_s *substream,
                           uint32_t bytes) {
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
        bs_abort(stream);

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
void bs_substream_append_p(struct Bitstream_s *stream,
                           struct Bitstream_s *substream,
                           uint32_t bytes) {
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
            bs_abort(stream);
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

void bs_substream_append_s(struct Bitstream_s *stream,
                           struct Bitstream_s *substream,
                           uint32_t bytes) {
    uint8_t* extended_buffer;
    struct bs_callback *callback;
    uint32_t i;

    /*byte align the input stream*/
    stream->state = 0;

    /*abort if there's sufficient bytes remaining
      in the input stream to pass to the output stream*/
    if (buf_size(stream->input.substream) < bytes)
        bs_abort(stream);

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

void bs_close_stream_s(struct Bitstream_s *stream) {
    buf_close(stream->input.substream);
}

#ifndef STANDALONE

/*******************************************
 Python stream handlers

 for making a Python file-like object behave
 like C file pointers
 *******************************************/

struct bs_python_input*
py_open(PyObject* reader) {
    struct bs_python_input* input = malloc(sizeof(struct bs_python_input));
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
py_getc(struct bs_python_input *stream) {
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
py_close(struct bs_python_input *stream) {
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
py_free(struct bs_python_input *stream) {
    Py_XDECREF(stream->reader_obj);
    free(stream->buffer);
    free(stream);
}


Bitstream*
bs_open_python(PyObject *reader, bs_endianness endianness) {
    Bitstream *bs = malloc(sizeof(Bitstream));
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
        bs->read = bs_read_bits_p_be;
        bs->read_signed = bs_read_signed_bits_p_be;
        bs->read_64 = bs_read_bits64_p_be;
        bs->skip = bs_skip_bits_p_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_p_be;
        bs->read_limited_unary = bs_read_limited_unary_p_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_p_be;
        bs->substream = bs_substream_p_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = bs_read_bits_p_le;
        bs->read_signed = bs_read_signed_bits_p_le;
        bs->read_64 = bs_read_bits64_p_le;
        bs->skip = bs_skip_bits_p_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_p_le;
        bs->read_limited_unary = bs_read_limited_unary_p_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_p_le;
        bs->substream = bs_substream_p_le;
        break;
    }
    bs->read_huffman_code = bs_read_huffman_code_p;
    bs->substream_append = bs_substream_append_p;
    bs->close = bs_close;
    bs->close_stream = bs_close_stream_p;
    bs->mark = bs_mark_p;
    bs->rewind = bs_rewind_p;
    bs->unmark = bs_unmark_p;

    return bs;
}

void
bs_close_stream_p(Bitstream *bs) {
    if (bs == NULL)
        return;
    else if (bs->input.python != NULL) {
        py_close(bs->input.python);
        bs->close_stream = bs_noop;
    }
}

#endif
