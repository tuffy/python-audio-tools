#ifndef BITSTREAM_H
#define BITSTREAM_H

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

struct bs_callback {
    void (*callback)(int, void*);
    void *data;
    struct bs_callback *next;
};

typedef struct {
    FILE *file;
    int state;
    struct bs_callback *callback;
} Bitstream;

Bitstream*
bs_open(FILE *f);

void
bs_close(Bitstream *bs);

void
bs_add_callback(Bitstream *bs, void (*callback)(int, void*),
                void *data);

int
bs_eof(Bitstream *bs);


void
bs_abort(Bitstream *bs);


typedef enum {BBW_WRITE_BITS,
              BBW_WRITE_SIGNED_BITS,
              BBW_WRITE_BITS64,
              BBW_WRITE_UNARY,
              BBW_BYTE_ALIGN} bbw_action;

typedef union {
    unsigned int count;
    int stop_bit;
} bbw_key;

typedef union {
    int value;
    uint64_t value64;
} bbw_value;

typedef struct {
    bbw_action *actions;
    bbw_key *keys;
    bbw_value *values;
    unsigned int size;
    unsigned int total_size;
    unsigned int bits_written;
} BitbufferW;

extern const unsigned int read_bits_table[0x900][8];
extern const unsigned int read_unary_table[0x900][2];
extern const unsigned int unread_bit_table[0x900][2];

static inline unsigned int
read_bits(Bitstream* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    unsigned int accumulator = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback(byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        accumulator = (accumulator << ((result & 0xF00000) >> 20)) |
            ((result & 0xFF000) >> 12);
        count -= ((result & 0xF00000) >> 20);
        context = (result & 0xFFF);
    }

    bs->state = context;
    return accumulator;
}

static inline int
read_signed_bits(Bitstream* bs, unsigned int count)
{
    if (!read_bits(bs, 1)) {
        return read_bits(bs, count - 1);
    } else {
        return read_bits(bs, count - 1) - (1 << (count - 1));
    }
}

static inline uint64_t
read_bits64(Bitstream* bs, unsigned int count)
{
    int context = bs->state;
    unsigned int result;
    int byte;
    struct bs_callback* callback;
    uint64_t accumulator = 0;

    while (count > 0) {
        if (context == 0) {
            if ((byte = fgetc(bs->file)) == EOF)
                bs_abort(bs);
            context = 0x800 | byte;
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback(byte, callback->data);
        }

        result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

        accumulator = (accumulator << ((result & 0xF00000) >> 20)) |
            ((result & 0xFF000) >> 12);
        count -= ((result & 0xF00000) >> 20);
        context = (result & 0xFFF);
    }

    bs->state = context;
    return accumulator;
}

static inline void
unread_bit(Bitstream* bs, int unread_bit)
{
    bs->state = unread_bit_table[bs->state][unread_bit];
    assert((bs->state >> 12) == 0);
}

static inline unsigned int
read_unary(Bitstream* bs, int stop_bit)
{
    int context = bs->state;
    unsigned int result;
    struct bs_callback* callback;
    int byte;
    unsigned int accumulator = 0;

    do {
        if (context == 0) {
            if ((byte = fgetc(bs->file)) == EOF)
                bs_abort(bs);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback(byte, callback->data);
            context = 0x800 | byte;
        }

        result = read_unary_table[context][stop_bit];

        accumulator += ((result & 0xFF000) >> 12);

        context = result & 0xFFF;
    } while (result >> 24);

    bs->state = context;
    return accumulator;
}

static inline void
byte_align_r(Bitstream* bs)
{
    bs->state = 0;
}

#endif
