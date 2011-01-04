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

const unsigned int read_bits_table[0x900][8] =
#include "read_bits_table.h"
    ;

const unsigned int read_bits_table_le[0x900][8] =
#include "read_bits_table_le.h"
    ;

const unsigned int unread_bit_table[0x900][2] =
#include "unread_bit_table.h"
    ;

const unsigned int unread_bit_table_le[0x900][2] =
#include "unread_bit_table_le.h"
    ;

const unsigned int read_unary_table[0x900][2] =
#include "read_unary_table.h"
    ;

const unsigned int read_unary_table_le[0x900][2] =
#include "read_unary_table_le.h"
    ;

const unsigned int read_limited_unary_table[0x900][18] =
#include "read_limited_unary_table.h"
    ;

const unsigned int read_limited_unary_table_le[0x900][18] =
#include "read_limited_unary_table_le.h"
    ;

Bitstream*
bs_open(FILE *f, bs_endianness endianness)
{
    Bitstream *bs = malloc(sizeof(Bitstream));
    bs->input.stdio.file = f;
    bs->state = 0;
    bs->callback = NULL;
    bs->exceptions = NULL;

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
    bs->close = bs_close_f;
    bs->mark = bs_mark;
    bs->rewind = bs_rewind;
    bs->unmark = bs_unmark;

    return bs;
}

void
bs_close_f(Bitstream *bs)
{
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    if (bs == NULL) return;

    if (bs->input.stdio.file != NULL)
        fclose(bs->input.stdio.file);

    for (c_node = bs->callback; c_node != NULL; c_node = c_next) {
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
    free(bs);
}

void
bs_add_callback(Bitstream *bs, void (*callback)(uint8_t, void*),
                void *data)
{
    struct bs_callback *callback_node = malloc(sizeof(struct bs_callback));
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = bs->callback;
    bs->callback = callback_node;
}

void
bs_call_callbacks(Bitstream *bs, uint8_t byte) {
    struct bs_callback *callback;
    for (callback = bs->callback;
         callback != NULL;
         callback = callback->next)
        callback->callback(byte, callback->data);
}

void
bs_pop_callback(Bitstream *bs) {
    struct bs_callback *c_node = bs->callback;
    if (c_node != NULL) {
        bs->callback = c_node->next;
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

unsigned int
bs_read_bits_be(Bitstream* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int bit_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator = (accumulator << bit_size) | ((result & 0xFF000) >> 12);
        count -= bit_size;
        context = (result & 0xFFF);
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
    int bit_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator |= (((result & 0xFF000) >> 12) << bit_offset);
        bit_offset += bit_size;
        count -= bit_size;
        context = (result & 0xFFF);
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
    int bit_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator = (accumulator << bit_size) | ((result & 0xFF000) >> 12);
        count -= bit_size;
        context = (result & 0xFFF);
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
    int bit_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator |= (((result & 0xFF000) >> 12) << bit_offset);
        bit_offset += bit_size;
        count -= bit_size;
        context = (result & 0xFFF);
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

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        count -= (result & 0xF00000) >> 20;
        context = (result & 0xFFF);
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

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][(count > 8 ? 8 : count) - 1];

        count -= (result & 0xF00000) >> 20;
        context = (result & 0xFFF);
    }

    bs->state = context;
}

void
bs_unread_bit_be(Bitstream* bs, int unread_bit)
{
    bs->state = unread_bit_table[bs->state][unread_bit];
    assert((bs->state >> 12) == 0);
}

void
bs_unread_bit_le(Bitstream* bs, int unread_bit)
{
    bs->state = unread_bit_table_le[bs->state][unread_bit];
    assert((bs->state >> 12) == 0);
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
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_unary_table[context][stop_bit];

        accumulator += ((result & 0xF000) >> 12);

        context = result & 0xFFF;
    } while (result >> 16);

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
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_unary_table_le[context][stop_bit];

        accumulator += ((result & 0xF000) >> 12);

        context = result & 0xFFF;
    } while (result >> 16);

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
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_limited_unary_table[context][stop_bit +
                                                   MIN(maximum_bits, 8)];

        value = ((result & 0xF000) >> 12);

        accumulator += value;
        maximum_bits -= value;

        context = result & 0xFFF;
    } while ((result >> 16) == 1);

    bs->state = context;

    if (result >> 17) {
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
            if ((byte = fgetc(bs->input.stdio.file)) == EOF)
                bs_abort(bs);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_limited_unary_table_le[context][stop_bit +
                                                      MIN(maximum_bits, 8)];

        value = ((result & 0xF000) >> 12);

        accumulator += value;
        maximum_bits -= value;

        context = result & 0xFFF;
    } while ((result >> 16) == 1);

    bs->state = context;

    if (result >> 17) {
        /*maximum_bits reached*/
        return -1;
    } else {
        /*stop bit reached*/
        return accumulator;
    }
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
    fgetpos(bs->input.stdio.file, &(bs->input.stdio.mark));
    bs->input.stdio.mark_state = bs->state;
}

void
bs_rewind(Bitstream* bs) {
    fsetpos(bs->input.stdio.file, &(bs->input.stdio.mark));
    bs->state = bs->input.stdio.mark_state;
}

void
bs_unmark(Bitstream* bs) {
    memset(&(bs->input.stdio.mark), 0, sizeof(fpos_t));
    bs->input.stdio.mark_state = 0;
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
    else
        /*some exception occurred when calling close()
          so simply print it out and continue on
          since there's little we can do about it*/
        PyErr_PrintEx(1);

    Py_XDECREF(stream->reader_obj);
    free(stream->buffer);
    free(stream);

    return 0;
}


Bitstream*
bs_open_python(PyObject *reader, bs_endianness endianness) {
    Bitstream *bs = malloc(sizeof(Bitstream));
    bs->input.python = py_open(reader);
    bs->state = 0;
    bs->callback = NULL;
    bs->exceptions = NULL;

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
    bs->close = bs_close_p;
    bs->mark = bs_mark_p;
    bs->rewind = bs_rewind_p;
    bs->unmark = bs_unmark_p;

    return bs;
}

void
bs_close_p(Bitstream *bs) {
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    if (bs == NULL) return;

    if (bs->input.python != NULL)
        py_close(bs->input.python);

    for (c_node = bs->callback; c_node != NULL; c_node = c_next) {
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
    free(bs);
}

/*_be signifies the big-endian readers*/
unsigned int
bs_read_bits_p_be(Bitstream* bs, unsigned int count) {
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;
    int bit_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator = (accumulator << bit_size) | ((result & 0xFF000) >> 12);
        count -= bit_size;
        context = (result & 0xFFF);
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
    int bit_size;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator = (accumulator << bit_size) | ((result & 0xFF000) >> 12);
        count -= bit_size;
        context = (result & 0xFFF);
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

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        count -= (result & 0xF00000) >> 20;
        context = (result & 0xFFF);
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
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_unary_table[context][stop_bit];

        accumulator += ((result & 0xF000) >> 12);

        context = result & 0xFFF;
    } while (result >> 16);

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
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_limited_unary_table[context][stop_bit +
                                                   MIN(maximum_bits, 8)];

        value = ((result & 0xF000) >> 12);

        accumulator += value;
        maximum_bits -= value;

        context = result & 0xFFF;
    } while ((result >> 16) == 1);

    bs->state = context;

    if (result >> 17) {
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
    int bit_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator |= (((result & 0xFF000) >> 12) << bit_offset);
        bit_offset += bit_size;
        count -= bit_size;
        context = (result & 0xFFF);
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
    int bit_size;
    int bit_offset = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][(count > 8 ? 8 : count) - 1];

        bit_size = (result & 0xF00000) >> 20;
        accumulator |= (((result & 0xFF000) >> 12) << bit_offset);
        bit_offset += bit_size;
        count -= bit_size;
        context = (result & 0xFFF);
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

    while (count > 0) {
        if (context == 0) {
            if ((byte = py_getc(bs->input.python)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
        }

        result = read_bits_table_le[context][(count > 8 ? 8 : count) - 1];

        count -= (result & 0xF00000) >> 20;
        context = (result & 0xFFF);
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
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_unary_table_le[context][stop_bit];

        accumulator += ((result & 0xF000) >> 12);

        context = result & 0xFFF;
    } while (result >> 16);

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
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_limited_unary_table_le[context][stop_bit +
                                                      MIN(maximum_bits, 8)];

        value = ((result & 0xF000) >> 12);

        accumulator += value;
        maximum_bits -= value;

        context = result & 0xFFF;
    } while ((result >> 16) == 1);

    bs->state = context;

    if (result >> 17) {
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

void
bs_mark_p(Bitstream* bs) {
    bs->input.python->marked_position = bs->input.python->buffer_position;
    bs->input.python->mark_state = bs->state;
    bs->input.python->mark_in_progress = 1;
}

void
bs_rewind_p(Bitstream* bs) {
    bs->input.python->buffer_position = bs->input.python->marked_position;
    bs->state = bs->input.python->mark_state;
}

void
bs_unmark_p(Bitstream* bs) {
    bs->input.python->mark_in_progress = 0;
}

#endif
