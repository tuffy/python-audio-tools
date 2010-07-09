#include "bitstream_r.h"

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

const unsigned int read_bits_table[0x900][8] =
#include "read_bits_table.h"
    ;

const unsigned int unread_bit_table[0x900][2] =
#include "unread_bit_table.h"
    ;

const unsigned int read_unary_table[0x900][2] =
#include "read_unary_table.h"
    ;

Bitstream*
bs_open(FILE *f)
{
    Bitstream *bs = malloc(sizeof(Bitstream));
    bs->file = f;
    bs->state = 0;
    bs->callback = NULL;
    bs->exceptions = NULL;
    return bs;
}

void
bs_close(Bitstream *bs)
{
    struct bs_callback *c_node;
    struct bs_callback *c_next;
    struct bs_exception *e_node;
    struct bs_exception *e_next;

    if (bs == NULL) return;

    if (bs->file != NULL) fclose(bs->file);

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
bs_add_callback(Bitstream *bs, void (*callback)(int, void*),
                void *data)
{
    struct bs_callback *callback_node = malloc(sizeof(struct bs_callback));
    callback_node->callback = callback;
    callback_node->data = data;
    callback_node->next = bs->callback;
    bs->callback = callback_node;
}

int
bs_eof(Bitstream *bs)
{
    return feof(bs->file);
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
