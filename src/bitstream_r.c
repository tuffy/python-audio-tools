#include "bitstream_r.h"

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

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->read = bs_read_bits_be;
        bs->read_signed = bs_read_signed_bits_be;
        bs->read_64 = bs_read_bits64_be;
        bs->skip = bs_skip_bits_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_be;
        bs->read_limited_unary = bs_read_limited_unary_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->read = bs_read_bits_le;
        bs->read_signed = bs_read_signed_bits_le;
        bs->read_64 = bs_read_bits64_le;
        bs->skip = bs_skip_bits_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_le;
        bs->read_limited_unary = bs_read_limited_unary_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_le;
        break;
    }
    bs->read_huffman_code = bs_read_huffman_code;
    bs->close = bs_close;
    bs->close_stream = bs_close_stream_f;
    bs->mark = bs_mark;
    bs->rewind = bs_rewind;
    bs->unmark = bs_unmark;

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
    if (bs->exceptions != NULL) {
        fprintf(stderr, "Warning: leftover etry entries on stack\n");
    }
    for (e_node = bs->exceptions; e_node != NULL; e_node = e_next) {
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
bs_add_callback(Bitstream *bs, void (*callback)(uint8_t, void*),
                void *data)
{
    struct bs_callback *callback_node = malloc(sizeof(struct bs_callback));
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
bs_pop_callback(Bitstream *bs) {
    struct bs_callback *c_node = bs->callbacks;
    if (c_node != NULL) {
        bs->callbacks = c_node->next;
        free(c_node);
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
    struct bs_exception *node = malloc(sizeof(struct bs_exception));
    node->next = bs->exceptions;
    bs->exceptions = node;
    return &(node->env);
}

void
bs_etry(Bitstream *bs) {
    struct bs_exception *node = bs->exceptions;
    if (node != NULL) {
        bs->exceptions = node->next;
        free(node);
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
#define NEW_CONTEXT(x) (0x100 | (x))

unsigned int
bs_read_bits_be(Bitstream* bs, unsigned int count)
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
bs_read_bits_le(Bitstream* bs, unsigned int count)
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

int
bs_read_signed_bits_be(Bitstream* bs, unsigned int count)
{
    if (!bs_read_bits_be(bs, 1)) {
        return bs_read_bits_be(bs, count - 1);
    } else {
        return bs_read_bits_be(bs, count - 1) - (1 << (count - 1));
    }
}

int
bs_read_signed_bits_le(Bitstream* bs, unsigned int count)
{
    int unsigned_value = bs_read_bits_le(bs, count - 1);

    if (!bs_read_bits_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
}

uint64_t
bs_read_bits64_be(Bitstream* bs, unsigned int count)
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
bs_read_bits64_le(Bitstream* bs, unsigned int count)
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

void
bs_skip_bits_be(Bitstream* bs, unsigned int count)
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
bs_skip_bits_le(Bitstream* bs, unsigned int count)
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
bs_read_unary_be(Bitstream* bs, int stop_bit)
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
bs_read_unary_le(Bitstream* bs, int stop_bit)
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

/*returns -1 on error, so cannot be unsigned*/
int
bs_read_limited_unary_be(Bitstream* bs, int stop_bit, int maximum_bits)
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

/*returns -1 on error, so cannot be unsigned*/
int
bs_read_limited_unary_le(Bitstream* bs, int stop_bit, int maximum_bits)
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

void*
bs_read_huffman_code(Bitstream *bs, const struct bs_huffman_table* table) {
    const unsigned int total_tree_nodes = table->total_tree_nodes;
    struct bs_huffman_table_entry* entries = table->entries;
    struct bs_huffman_table_entry* entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

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

        entry = &(entries[(context * total_tree_nodes) + node]);
        context = entry->context;
        node = entry->node;
    } while (entry->value == NULL);

    bs->state = context;
    return entry->value;
}

void
bs_set_endianness_be(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->read = bs_read_bits_le;
        bs->read_signed = bs_read_signed_bits_le;
        bs->read_64 = bs_read_bits64_le;
        bs->skip = bs_skip_bits_le;
        bs->unread = bs_unread_bit_le;
        bs->read_unary = bs_read_unary_le;
        bs->read_limited_unary = bs_read_limited_unary_le;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_le;
    }
}

void
bs_set_endianness_le(Bitstream *bs, bs_endianness endianness) {
    bs->state = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->read = bs_read_bits_be;
        bs->read_signed = bs_read_signed_bits_be;
        bs->read_64 = bs_read_bits64_be;
        bs->skip = bs_skip_bits_be;
        bs->unread = bs_unread_bit_be;
        bs->read_unary = bs_read_unary_be;
        bs->read_limited_unary = bs_read_limited_unary_be;
        bs->byte_align = bs_byte_align_r;
        bs->set_endianness = bs_set_endianness_be;
    }
}

void
bs_byte_align_r(Bitstream* bs)
{
    bs->state = 0;
}

void
bs_mark(Bitstream* bs) {
    struct bs_mark* mark = malloc(sizeof(struct bs_mark));

    fgetpos(bs->input.file, &(mark->position.file));
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
}

void
bs_rewind(Bitstream* bs) {
    if (bs->marks != NULL) {
        fsetpos(bs->input.file, &(bs->marks->position.file));
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

void
bs_unmark(Bitstream* bs) {
    struct bs_mark* mark = bs->marks;
    bs->marks = mark->next;
    free(mark);
}

#ifndef STANDALONE

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
                        /*if the stream has no mark,
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
                        /*if the stream has a mark,
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
        break;
    }
    bs->read_huffman_code = bs_read_huffman_code_p;
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

/*_be signifies the big-endian readers*/
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

int
bs_read_signed_bits_p_be(Bitstream* bs, unsigned int count) {
    if (!bs_read_bits_p_be(bs, 1)) {
        return bs_read_bits_p_be(bs, count - 1);
    } else {
        return bs_read_bits_p_be(bs, count - 1) - (1 << (count - 1));
    }
}

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
    }
}

/*_le signifies the big-endian readers*/
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

int
bs_read_signed_bits_p_le(Bitstream* bs, unsigned int count) {
    int unsigned_value = bs_read_bits_p_le(bs, count - 1);

    if (!bs_read_bits_p_le(bs, 1)) {
        return unsigned_value;
    } else {
        return unsigned_value - (1 << (count - 1));
    }
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
    }
}

/*
Note that read_huffman_code has no endianness variants.
Which direction it reads from is decided when the table data is compiled.
*/
void*
bs_read_huffman_code_p(Bitstream *bs, const struct bs_huffman_table* table) {
    const unsigned int total_tree_nodes = table->total_tree_nodes;
    struct bs_huffman_table_entry* entries = table->entries;
    struct bs_huffman_table_entry* entry;
    int node = 0;
    int context = bs->state;
    struct bs_callback* callback;
    int byte;

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

        entry = &(entries[(context * total_tree_nodes) + node]);
        context = entry->context;
        node = entry->node;
    } while (entry->value == NULL);

    bs->state = context;
    return entry->value;
}

void
bs_mark_p(Bitstream* bs) {
    struct bs_mark* mark = malloc(sizeof(struct bs_mark));

    mark->position.python = bs->input.python->buffer_position;
    mark->state = bs->state;
    mark->next = bs->marks;
    bs->marks = mark;
    bs->input.python->mark_in_progress = 1;
}

void
bs_rewind_p(Bitstream* bs) {
    if (bs->marks != NULL) {
        bs->input.python->buffer_position = bs->marks->position.python;
        bs->state = bs->marks->state;
    } else {
        fprintf(stderr, "No marks on stack to rewind!\n");
    }
}

void
bs_unmark_p(Bitstream* bs) {
    struct bs_mark* mark = bs->marks;
    bs->marks = mark->next;
    free(mark);
    bs->input.python->mark_in_progress = (bs->marks != NULL);
}

#endif
