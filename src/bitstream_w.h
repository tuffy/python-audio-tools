#ifndef BITSTREAM_H
#define BITSTREAM_H

#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

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

struct bs_callback {
    void (*callback)(uint8_t, void*);
    void *data;
    struct bs_callback *next;
};

typedef enum {BS_BIG_ENDIAN, BS_LITTLE_ENDIAN} bs_endianness;

typedef enum {
    BS_WRITE_BITS,
    BS_WRITE_SIGNED_BITS,
    BS_WRITE_BITS64,
    BS_WRITE_UNARY,
    BS_BYTE_ALIGN,
    BS_SET_ENDIANNESS
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
        bs_endianness endianness;
    } value;
} BitstreamRecord;

typedef struct Bitstream_s {
    FILE *file;
    unsigned int buffer_size;
    unsigned int buffer;
    struct bs_callback *callback;

    int bits_written;    /*used by open_accumulator and open_recorder*/
    int records_written; /*used by open_recorder*/
    int records_total;   /*used by open_recorder*/
    BitstreamRecord *records;

    void (*write)(struct Bitstream_s* bs,
                  unsigned int count,
                  int value);

    void (*write_signed)(struct Bitstream_s* bs,
                         unsigned int count,
                         int value);

    void (*write_64)(struct Bitstream_s* bs,
                     unsigned int count,
                     uint64_t value);

    void (*write_unary)(struct Bitstream_s* bs,
                        int stop_bit,
                        int value);

    void (*byte_align)(struct Bitstream_s* bs);

    void (*set_endianness)(struct Bitstream_s* bs,
                           bs_endianness endianness);
} Bitstream;

Bitstream*
bs_open(FILE *f, bs_endianness endianness);

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

/*adds a callback function, which is called on every byte written
  the function's arguments are the written byte and a generic
  pointer to some other data structure
 */
void
bs_add_callback(Bitstream *bs,
                void (*callback)(uint8_t, void*),
                void *data);

int bs_eof(Bitstream *bs);


/*big-endian writers for concrete bitstreams*/
void
write_bits_actual_be(Bitstream* bs, unsigned int count, int value);

void
write_signed_bits_actual_be(Bitstream* bs, unsigned int count, int value);

void
write_bits64_actual_be(Bitstream* bs, unsigned int count, uint64_t value);

void
byte_align_w_actual_be(Bitstream* bs);

void
set_endianness_actual_be(Bitstream* bs, bs_endianness endianness);


/*little-endian writers for concrete bitstreams*/
void
write_bits_actual_le(Bitstream* bs, unsigned int count, int value);

void
write_signed_bits_actual_le(Bitstream* bs, unsigned int count, int value);

void
write_bits64_actual_le(Bitstream* bs, unsigned int count, uint64_t value);

void
byte_align_w_actual_le(Bitstream* bs);

void
set_endianness_actual_le(Bitstream* bs, bs_endianness endianness);


/*write unary uses the stream's current writers,
  so it has no endian variations*/
void
write_unary_actual(Bitstream* bs, int stop_bit, int value);


/*write methods for a bs_open_accumulator

  The general idea is that one can use an accumulator to determine
  how big a portion of the stream might be, then substitute it
  for an actual stream to perform actual output.
  This "throw away" approach is sometimes faster in practice
  when recording the stream's output adds too much overhead
  vs. simply redoing the calculations.

  For example:
  accumulator = bs_open_accumulator();
  accumulator->write(accumulator, 8, 0x7F);
  accumulator->write_signed(accumulator, 4, 3);
  accumulator->write_signed(accumulator, 4, -1);

  assert(accumulator->bits_written == 16);

  bs_close(accumulator);
*/
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

void
set_endianness_accumulator(Bitstream* bs, bs_endianness endianness);


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

/*write methods for a bs_open_recorder

  The general idea is that one uses a recorder to calculate
  how big a stream might be, then dump it to an actual stream
  if it's found to be the proper size.
  For example:
  stream = bs_open("filename", BS_BIG_ENDIAN);

  recorder = bs_open_recorder();
  recorder->write(recorder, 8, 0x7F);
  recorder->write_signed(recorder, 4, 3);
  recorder->write_signed(recorder, 4, -1);

  if (recorder->bits_written < minimum_bits)
    bs_dump_records(stream, recorder);

  bs_close(recorder);
  bs_close(stream);
*/
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
set_endianness_record(Bitstream* bs, bs_endianness endianness);


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
