#ifndef BITSTREAM_H
#define BITSTREAM_H

#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

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

typedef enum {
    BS_WRITE_BITS,
    BS_WRITE_SIGNED_BITS,
    BS_WRITE_BITS64,
    BS_WRITE_UNARY,
    BS_BYTE_ALIGN
} BitstreamRecordType;

typedef struct {
    BitstreamRecordType type;
    union {
        unsigned int count;
        int stop_bit;
    } key;
    union {
        int value;
        uint64_t value64;
    } value;
} BitstreamRecord;

typedef struct Bitstream_s {
    FILE *file;
    int state;
    struct bs_callback *callback;

    int bits_written;    /*used by open_accumulator and open_recorder*/
    int records_written; /*used by open_recorder*/
    int records_total;   /*used by open_recorder*/
    BitstreamRecord *records;

    void (*write_bits)(struct Bitstream_s* bs, unsigned int count, int value);
    void (*write_signed_bits)(struct Bitstream_s* bs, unsigned int count,
                              int value);
    void (*write_bits64)(struct Bitstream_s* bs, unsigned int count,
                         uint64_t value);
    void (*write_unary)(struct Bitstream_s* bs, int stop_bit, int value);
    void (*byte_align)(struct Bitstream_s* bs);
} Bitstream;

extern const unsigned int write_bits_table[0x400][0x900];
extern const unsigned int write_unary_table[0x400][0x20];

Bitstream*
bs_open(FILE *f);

Bitstream*
bs_open_accumulator(void);

Bitstream*
bs_open_recorder(void);

/*this closes bs's open file, if any,
  deallocates any recorded output (for bs_open_accumulator Bitstreams)
  and frees any callbacks before deallocating the bs struct*/
void
bs_close(Bitstream *bs);

/*this deallocates any recorded output (for bs_open_accumulator Bitstreams)
  and frees any callbacks before deallocating the bs struct
  it does not close any open FILE object but does fflush output*/
void
bs_free(Bitstream *bs);

void
bs_add_callback(Bitstream *bs, void (*callback)(int, void*),
                void *data);

int bs_eof(Bitstream *bs);


void
write_bits_actual(Bitstream* bs, unsigned int count, int value);

void
write_signed_bits_actual(Bitstream* bs, unsigned int count, int value);

void
write_bits64_actual(Bitstream* bs, unsigned int count, uint64_t value);

void
write_unary_actual(Bitstream* bs, int stop_bit, int value);

void
byte_align_w_actual(Bitstream* bs);


void
write_bits_accumulator(Bitstream* bs, unsigned int count, int value);

void
write_signed_bits_accumulator(Bitstream* bs, unsigned int count, int value);

void
write_bits64_accumulator(Bitstream* bs, unsigned int count, uint64_t value);

void
write_unary_accumulator(Bitstream* bs, int stop_bit, int value);

void
byte_align_w_accumulator(Bitstream* bs);


/*make room for at least one additional record*/
static inline void
bs_record_resize(Bitstream* bs)
{
    if (bs->records_written >= bs->records_total) {
        bs->records_total *= 2;
        bs->records = realloc(bs->records,
                              sizeof(BitstreamRecord) * bs->records_total);
    }
}

void
write_bits_record(Bitstream* bs, unsigned int count, int value);

void
write_signed_bits_record(Bitstream* bs, unsigned int count, int value);

void
write_bits64_record(Bitstream* bs, unsigned int count, uint64_t value);

void
write_unary_record(Bitstream* bs, int stop_bit, int value);

void
byte_align_w_record(Bitstream* bs);

void
bs_dump_records(Bitstream* target, Bitstream* source);

/*clear the recorded output and reset for new output*/
static inline void
bs_reset_recorder(Bitstream* bs)
{
    bs->bits_written = bs->records_written = 0;
}

void
bs_swap_records(Bitstream* a, Bitstream* b);

#endif
