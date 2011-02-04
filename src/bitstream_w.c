#include "bitstream_w.h"
#include <string.h>
#include <assert.h>

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

Bitstream*
bs_open(FILE *f, bs_endianness endianness)
{
    Bitstream *bs = malloc(sizeof(Bitstream));
    bs->file = f;
    bs->buffer_size = 0;
    bs->buffer = 0;
    bs->callback = NULL;
    bs->records = NULL;

    switch (endianness) {
    case BS_BIG_ENDIAN:
        bs->write = write_bits_actual_be;
        bs->write_signed = write_signed_bits_actual_be;
        bs->write_64 = write_bits64_actual_be;
        bs->write_unary = write_unary_actual;
        bs->byte_align = byte_align_w_actual_be;
        bs->set_endianness = set_endianness_actual_be;
        break;
    case BS_LITTLE_ENDIAN:
        bs->write = write_bits_actual_le;
        bs->write_signed = write_signed_bits_actual_le;
        bs->write_64 = write_bits64_actual_le;
        bs->write_unary = write_unary_actual;
        bs->byte_align = byte_align_w_actual_le;
        bs->set_endianness = set_endianness_actual_le;
        break;
    }

    return bs;
}

Bitstream*
bs_open_accumulator(void)
{
    Bitstream *bs = malloc(sizeof(Bitstream));
    bs->file = NULL;
    bs->bits_written = 0;
    bs->callback = NULL;
    bs->records = NULL;

    bs->write = write_bits_accumulator;
    bs->write_signed = write_signed_bits_accumulator;
    bs->write_64 = write_bits64_accumulator;
    bs->write_unary = write_unary_accumulator;
    bs->byte_align = byte_align_w_accumulator;
    bs->set_endianness = set_endianness_accumulator;

    return bs;
}

Bitstream*
bs_open_recorder(void)
{
    Bitstream *bs = malloc(sizeof(Bitstream));
    bs->file = NULL;
    bs->bits_written = 0;
    bs->callback = NULL;

    bs->records_written = 0;
    bs->records_total = 0x100;
    bs->records = malloc(sizeof(BitstreamRecord) * bs->records_total);

    bs->write = write_bits_record;
    bs->write_signed = write_signed_bits_record;
    bs->write_64 = write_bits64_record;
    bs->write_unary = write_unary_record;
    bs->byte_align = byte_align_w_record;
    bs->set_endianness = set_endianness_record;

    return bs;
}

void
bs_close(Bitstream *bs)
{
    struct bs_callback *node;
    struct bs_callback *next;

    if (bs == NULL) return;

    if (bs->file != NULL) fclose(bs->file);
    if (bs->records != NULL) free(bs->records);

    for (node = bs->callback; node != NULL; node = next) {
        next = node->next;
        free(node);
    }
    free(bs);
}

void
bs_free(Bitstream *bs)
{
    struct bs_callback *node;
    struct bs_callback *next;

    if (bs == NULL) return;

    if (bs->file != NULL) fflush(bs->file);
    if (bs->records != NULL) free(bs->records);

    for (node = bs->callback; node != NULL; node = next) {
        next = node->next;
        free(node);
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

int
bs_eof(Bitstream *bs)
{
    return feof(bs->file);
}
/*******************************
   bitstream writing functions

 these write actual bits to disk
********************************/

void
write_bits_actual_be(Bitstream* bs, unsigned int count, int value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

    assert(value >= 0);
    assert(value < (1l << count));

    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value >> (count - bits_to_write);

        /*prepend value to buffer*/
        bs->buffer = (bs->buffer << bits_to_write) | value_to_write;
        bs->buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->buffer_size >= 8) {
            byte = (bs->buffer >> (bs->buffer_size - 8)) & 0xFF;
            fputc(byte, bs->file);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);

            bs->buffer_size -= 8;
        }

        /*decrement the count and value*/
        value -= (value_to_write << (count - bits_to_write));
        count -= bits_to_write;
    }
}

void
write_bits_actual_le(Bitstream* bs, unsigned int count, int value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

    assert(value >= 0);
    assert(value < (int64_t)(1LL << count));

    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value & ((1 << bits_to_write) - 1);

        /*append value to buffer*/
        bs->buffer |= (value_to_write << bs->buffer_size);
        bs->buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->buffer_size >= 8) {
            byte = bs->buffer & 0xFF;
            fputc(byte, bs->file);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            bs->buffer >>= 8;
            bs->buffer_size -= 8;
        }

        /*decrement the count and value*/
        value >>= bits_to_write;
        count -= bits_to_write;
    }
}

void
write_signed_bits_actual_be(Bitstream* bs, unsigned int count, int value)
{
    assert(value < (1 << (count - 1)));
    assert(value >= -(1 << (count - 1)));
    if (value >= 0) {
        write_bits_actual_be(bs, count, value);
    } else {
        write_bits_actual_be(bs, count, (1 << count) - (-value));
    }
}

void
write_signed_bits_actual_le(Bitstream* bs, unsigned int count, int value) {
    assert(value < (1 << (count - 1)));
    assert(value >= -(1 << (count - 1)));
    if (value >= 0) {
        write_bits_actual_le(bs, count, value);
    } else {
        write_bits_actual_le(bs, count, (1 << count) - (-value));
    }
}

void
write_bits64_actual_be(Bitstream* bs, unsigned int count, uint64_t value)
{
    int bits_to_write;
    int value_to_write;
    unsigned int byte;
    struct bs_callback* callback;

    assert(value >= 0l);
    assert(value < (int64_t)(1ll << count));

    while (count > 0) {
        /*chop off up to 8 bits to write at a time*/
        bits_to_write = count > 8 ? 8 : count;
        value_to_write = value >> (count - bits_to_write);

        /*prepend value to buffer*/
        bs->buffer = (bs->buffer << bits_to_write) | value_to_write;
        bs->buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->buffer_size >= 8) {
            byte = (bs->buffer >> (bs->buffer_size - 8)) & 0xFF;
            fputc(byte, bs->file);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);

            bs->buffer_size -= 8;
        }

        /*decrement the count and value*/
        value -= (value_to_write << (count - bits_to_write));
        count -= bits_to_write;
    }
}

void
write_bits64_actual_le(Bitstream* bs, unsigned int count, uint64_t value)
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
        bs->buffer |= (value_to_write << bs->buffer_size);
        bs->buffer_size += bits_to_write;

        /*if buffer is over 8 bits,
          write a byte and remove it from the buffer*/
        if (bs->buffer_size >= 8) {
            byte = bs->buffer & 0xFF;
            fputc(byte, bs->file);
            for (callback = bs->callback;
                 callback != NULL;
                 callback = callback->next)
                callback->callback((uint8_t)byte, callback->data);
            bs->buffer >>= 8;
            bs->buffer_size -= 8;
        }

        /*decrement the count and value*/
        value >>= bits_to_write;
        count -= bits_to_write;
    }
}

#define UNARY_BUFFER_SIZE 30

void
write_unary_actual(Bitstream* bs, int stop_bit, int value) {
    void (*write_bits)(struct Bitstream_s* bs, unsigned int count, int value) =
        bs->write;

    unsigned int bits_to_write;

    /*send our pre-stop bits to write() in 30-bit chunks*/
    while (value > 0) {
        bits_to_write = value <= UNARY_BUFFER_SIZE ? value : UNARY_BUFFER_SIZE;
        if (stop_bit) { /*stop bit of 1, buffer value of all 0s*/
            write_bits(bs, bits_to_write, 0);
        } else {        /*stop bit of 0, buffer value of all 1s*/
            write_bits(bs, bits_to_write, (1 << bits_to_write) - 1);
        }
        value -= bits_to_write;
    }

    /*finally, send our stop bit*/
    write_bits(bs, 1, stop_bit);
}

void
byte_align_w_actual_be(Bitstream* bs)
{
    write_bits_actual_be(bs, 7, 0);
    bs->buffer = 0;
    bs->buffer_size = 0;
}

void
byte_align_w_actual_le(Bitstream* bs)
{
    write_bits_actual_le(bs, 7, 0);
    bs->buffer = 0;
    bs->buffer_size = 0;
}

void
set_endianness_actual_be(Bitstream* bs, bs_endianness endianness) {
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_LITTLE_ENDIAN) {
        bs->write = write_bits_actual_le;
        bs->write_signed = write_signed_bits_actual_le;
        bs->write_64 = write_bits64_actual_le;
        bs->write_unary = write_unary_actual;
        bs->byte_align = byte_align_w_actual_le;
        bs->set_endianness = set_endianness_actual_le;
    }
}

void
set_endianness_actual_le(Bitstream* bs, bs_endianness endianness) {
    bs->buffer = 0;
    bs->buffer_size = 0;
    if (endianness == BS_BIG_ENDIAN) {
        bs->write = write_bits_actual_be;
        bs->write_signed = write_signed_bits_actual_be;
        bs->write_64 = write_bits64_actual_be;
        bs->write_unary = write_unary_actual;
        bs->byte_align = byte_align_w_actual_be;
        bs->set_endianness = set_endianness_actual_be;
    }
}


void
write_bits_accumulator(Bitstream* bs, unsigned int count, int value)
{
    assert(value >= 0);
    assert(value < (1l << count));
    bs->bits_written += count;
}

void
write_signed_bits_accumulator(Bitstream* bs, unsigned int count, int value)
{
    assert(value < (1 << (count - 1)));
    assert(value >= -(1 << (count - 1)));
    bs->bits_written += count;
}

void
write_bits64_accumulator(Bitstream* bs, unsigned int count, uint64_t value)
{
    assert(value >= 0l);
    assert(value < (int64_t)(1ll << count));
    bs->bits_written += count;
}

void
write_unary_accumulator(Bitstream* bs, int stop_bit, int value)
{
    assert(value >= 0);
    bs->bits_written += (value + 1);
}

void
byte_align_w_accumulator(Bitstream* bs)
{
    if (bs->bits_written % 8)
        bs->bits_written += (bs->bits_written % 8);
}

void
set_endianness_accumulator(Bitstream* bs, bs_endianness endianness) {
    /*swapping endianness results in a byte alignment*/
    byte_align_w_accumulator(bs);
}

void
write_bits_record(Bitstream* bs, unsigned int count, int value)
{
    BitstreamRecord record;

    assert(value >= 0);
    assert(value < (1l << count));
    record.type = BS_WRITE_BITS;
    record.key.count = count;
    record.value.value = value;
    bs_record_resize(bs);
    bs->records[bs->records_written++] = record;
    bs->bits_written += count;
}

void
write_signed_bits_record(Bitstream* bs, unsigned int count, int value)
{
    BitstreamRecord record;

    assert(value < (1 << (count - 1)));
    assert(value >= -(1 << (count - 1)));
    record.type = BS_WRITE_SIGNED_BITS;
    record.key.count = count;
    record.value.value = value;
    bs_record_resize(bs);
    bs->records[bs->records_written++] = record;
    bs->bits_written += count;
}

void
write_bits64_record(Bitstream* bs, unsigned int count, uint64_t value)
{
    BitstreamRecord record;

    assert(value >= 0l);
    assert(value < (int64_t)(1ll << count));
    record.type = BS_WRITE_BITS64;
    record.key.count = count;
    record.value.value64 = value;
    bs_record_resize(bs);
    bs->records[bs->records_written++] = record;
    bs->bits_written += count;
}

void
write_unary_record(Bitstream* bs, int stop_bit, int value)
{
    BitstreamRecord record;

    assert(value >= 0);
    record.type = BS_WRITE_UNARY;
    record.key.stop_bit = stop_bit;
    record.value.value = value;
    bs_record_resize(bs);
    bs->records[bs->records_written++] = record;
    bs->bits_written += (value + 1);
}

void
byte_align_w_record(Bitstream* bs)
{
    BitstreamRecord record;

    record.type = BS_BYTE_ALIGN;
    bs_record_resize(bs);
    bs->records[bs->records_written++] = record;
    if (bs->bits_written % 8)
        bs->bits_written += (8 - (bs->bits_written % 8));
}

void
set_endianness_record(Bitstream* bs, bs_endianness endianness) {
    BitstreamRecord record;

    record.type = BS_SET_ENDIANNESS;
    record.value.endianness = endianness;
    bs_record_resize(bs);
    bs->records[bs->records_written++] = record;
    if (bs->bits_written % 8)
        bs->bits_written += (8 - (bs->bits_written % 8));
}

void
bs_dump_records(Bitstream* target, Bitstream* source)
{
    int records_written = source->records_written;
    int new_records_total;
    int i;
    BitstreamRecord record;

    if (target->write == write_bits_record) {
        /*when dumping from one recorder to another,
          use memcpy instead of looping through the records*/

        for (new_records_total = target->records_total;
             (new_records_total -
              target->records_written) < records_written;)
            new_records_total *= 2;

        if (new_records_total != target->records_total)
            target->records = realloc(target->records,
                                      sizeof(BitstreamRecord) *
                                      new_records_total);

        memcpy(target->records + target->records_written,
               source->records,
               sizeof(BitstreamRecord) * source->records_written);

        target->records_written += source->records_written;
        target->bits_written += source->bits_written;
    } else if (target->write == write_bits_accumulator) {
        /*when dumping from a recorder to an accumulator,
          simply copy over the total number of written bits*/
        target->bits_written = source->bits_written;
    } else {
        for (i = 0; i < records_written; i++) {
            record = source->records[i];
            switch (record.type) {
            case BS_WRITE_BITS:
                target->write(target, record.key.count,
                              record.value.value);
                break;
            case BS_WRITE_SIGNED_BITS:
                target->write_signed(target, record.key.count,
                                     record.value.value);
                break;
            case BS_WRITE_BITS64:
                target->write_64(target, record.key.count,
                                 record.value.value64);
                break;
            case BS_WRITE_UNARY:
                target->write_unary(target, record.key.stop_bit,
                                    record.value.value);
                break;
            case BS_BYTE_ALIGN:
                target->byte_align(target);
                break;
            case BS_SET_ENDIANNESS:
                target->set_endianness(target,
                                       record.value.endianness);
                break;
            }
        }
    }
}

void
bs_swap_records(Bitstream* a, Bitstream* b)
{
    int bits_written = a->bits_written;
    int records_written = a->records_written;
    int records_total = a->records_total;
    BitstreamRecord *records = a->records;

    a->bits_written = b->bits_written;
    a->records_written = b->records_written;
    a->records_total = b->records_total;
    a->records = b->records;

    b->bits_written = bits_written;
    b->records_written = records_written;
    b->records_total = records_total;
    b->records = records;
}
