#include "bitstream_w.h"
#include <string.h>
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

Bitstream* bs_open(FILE *f) {
  Bitstream *bs = malloc(sizeof(Bitstream));
  bs->file = f;
  bs->state = 0;
  bs->callback = NULL;
  bs->records = NULL;

  bs->write_bits = write_bits_actual;
  bs->write_signed_bits = write_signed_bits_actual;
  bs->write_bits64 = write_bits64_actual;
  bs->write_unary = write_unary_actual;
  bs->byte_align = byte_align_w_actual;

  return bs;
}

Bitstream* bs_open_accumulator(void) {
  Bitstream *bs = malloc(sizeof(Bitstream));
  bs->file = NULL;
  bs->bits_written = 0;
  bs->callback = NULL;
  bs->records = NULL;

  bs->write_bits = write_bits_accumulator;
  bs->write_signed_bits = write_signed_bits_accumulator;
  bs->write_bits64 = write_bits64_accumulator;
  bs->write_unary = write_unary_accumulator;
  bs->byte_align = byte_align_w_accumulator;

  return bs;
}

Bitstream* bs_open_recorder(void) {
  Bitstream *bs = malloc(sizeof(Bitstream));
  bs->file = NULL;
  bs->bits_written = 0;
  bs->callback = NULL;

  bs->records_written = 0;
  bs->records_total = 0x100;
  bs->records = malloc(sizeof(BitstreamRecord) * bs->records_total);

  bs->write_bits = write_bits_record;
  bs->write_signed_bits = write_signed_bits_record;
  bs->write_bits64 = write_bits64_record;
  bs->write_unary = write_unary_record;
  bs->byte_align = byte_align_w_record;

  return bs;
}

void bs_close(Bitstream *bs) {
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

void bs_free(Bitstream *bs) {
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

void bs_add_callback(Bitstream *bs,
		     void (*callback)(unsigned int, void*),
		     void *data) {
  struct bs_callback *callback_node = malloc(sizeof(struct bs_callback));
  callback_node->callback = callback;
  callback_node->data = data;
  callback_node->next = bs->callback;
  bs->callback = callback_node;
}

int bs_eof(Bitstream *bs) {
  return feof(bs->file);
}
/*******************************
   bitstream writing functions

 these write actual bits to disk
********************************/

void write_bits_actual(Bitstream* bs, unsigned int count, int value) {
  int bits_to_write;
  int value_to_write;
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

  assert(value >= 0);
  assert(value < (1l << count));

  while (count > 0) {
    /*chop off up to 8 bits to write at a time*/
    bits_to_write = count > 8 ? 8 : count;
    value_to_write = value >> (count - bits_to_write);

    /*feed them through the jump table*/
    result = write_bits_table[context][(value_to_write | (bits_to_write << 8))];

    /*write a byte if necessary*/
    if (result >> 18) {
      byte = (result >> 10) & 0xFF;
      fputc(byte,bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    /*update the context*/
    context = result & 0x3FF;

    /*decrement the count and value*/
    value -= (value_to_write << (count - bits_to_write));
    count -= bits_to_write;
  }
  bs->state = context;
}

void write_signed_bits_actual(Bitstream* bs, unsigned int count, int value) {
  assert(value < (1 << (count - 1)));
  assert(value >= -(1 << (count - 1)));
  if (value >= 0) {
    write_bits_actual(bs, count, value);
  } else {
    write_bits_actual(bs, count, (1 << count) - (-value));
  }
}

void write_bits64_actual(Bitstream* bs, unsigned int count, uint64_t value) {
  int bits_to_write;
  int value_to_write;
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

  assert(value >= 0l);
  assert(value < (1l << count));

  while (count > 0) {
    /*chop off up to 8 bits to write at a time*/
    bits_to_write = count > 8 ? 8 : count;
    value_to_write = value >> (count - bits_to_write);

    /*feed them through the jump table*/
    result = write_bits_table[context][(value_to_write | (bits_to_write << 8))];

    /*write a byte if necessary*/
    if (result >> 18) {
      byte = (result >> 10) & 0xFF;
      fputc(byte,bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    /*update the context*/
    context = result & 0x3FF;

    /*decrement the count and value*/
    value -= (value_to_write << (count - bits_to_write));
    count -= bits_to_write;
  }
  bs->state = context;
}


void write_unary_actual(Bitstream* bs, int stop_bit, int value) {
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

  assert(value >= 0);

  /*send continuation blocks until we get to 7 bits or less*/
  while (value >= 8) {
    result = write_unary_table[context][(stop_bit << 4) | 0x08];
    if (result >> 18) {
      byte = (result >> 10) & 0xFF;
      fputc(byte,bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
    }

    context = result & 0x3FF;

    value -= 8;
  }

  /*finally, send the remaning value*/
  result = write_unary_table[context][(stop_bit << 4) | value];

  if (result >> 18) {
    byte = (result >> 10) & 0xFF;
    fputc(byte,bs->file);
    for (callback = bs->callback; callback != NULL; callback = callback->next)
      callback->callback(byte,callback->data);
  }

  context = result & 0x3FF;
  bs->state = context;
}

void byte_align_w_actual(Bitstream* bs) {
  write_bits_actual(bs,7,0);
  bs->state = 0;
}

const unsigned int write_bits_table[0x400][0x900] =
#include "write_bits_table.h"
  ;

const unsigned int write_unary_table[0x400][0x20] =
#include "write_unary_table.h"
    ;


void write_bits_accumulator(Bitstream* bs, unsigned int count, int value) {
  assert(value >= 0);
  assert(value < (1l << count));
  bs->bits_written += count;
}

void write_signed_bits_accumulator(Bitstream* bs, unsigned int count, int value) {
  assert(value < (1 << (count - 1)));
  assert(value >= -(1 << (count - 1)));
  bs->bits_written += count;
}

void write_bits64_accumulator(Bitstream* bs, unsigned int count,
			      uint64_t value) {
  assert(value >= 0l);
  assert(value < (1l << count));
  bs->bits_written += count;
}

void write_unary_accumulator(Bitstream* bs, int stop_bit, int value) {
  assert(value >= 0);
  bs->bits_written += (value + 1);
}

void byte_align_w_accumulator(Bitstream* bs) {
  if (bs->bits_written % 8)
    bs->bits_written += (bs->bits_written % 8);
}


void write_bits_record(Bitstream* bs, unsigned int count, int value) {
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

void write_signed_bits_record(Bitstream* bs, unsigned int count,
			      int value) {
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

void write_bits64_record(Bitstream* bs, unsigned int count,
			 uint64_t value) {
  BitstreamRecord record;

  assert(value >= 0l);
  assert(value < (1l << count));
  record.type = BS_WRITE_BITS64;
  record.key.count = count;
  record.value.value64 = value;
  bs_record_resize(bs);
  bs->records[bs->records_written++] = record;
  bs->bits_written += count;
}

void write_unary_record(Bitstream* bs, int stop_bit, int value) {
  BitstreamRecord record;

  assert(value >= 0);
  record.type = BS_WRITE_UNARY;
  record.key.stop_bit = stop_bit;
  record.value.value = value;
  bs_record_resize(bs);
  bs->records[bs->records_written++] = record;
  bs->bits_written += (value + 1);
}

void byte_align_w_record(Bitstream* bs) {
  BitstreamRecord record;

  record.type = BS_BYTE_ALIGN;
  bs_record_resize(bs);
  bs->records[bs->records_written++] = record;
  if (bs->bits_written % 8)
    bs->bits_written += (8 - (bs->bits_written % 8));
}

void bs_dump_records(Bitstream* target, Bitstream* source) {
  int records_written = source->records_written;
  int i;
  BitstreamRecord record;

  for (i = 0; i < records_written; i++) {
    record = source->records[i];
    switch (record.type) {
    case BS_WRITE_BITS:
      target->write_bits(target,record.key.count,record.value.value);
      break;
    case BS_WRITE_SIGNED_BITS:
      target->write_signed_bits(target,record.key.count,record.value.value);
      break;
    case BS_WRITE_BITS64:
      target->write_bits64(target,record.key.count,record.value.value64);
      break;
    case BS_WRITE_UNARY:
      target->write_unary(target,record.key.stop_bit,record.value.value);
      break;
    case BS_BYTE_ALIGN:
      target->byte_align(target);
      break;
    }
  }
}

void bs_swap_records(Bitstream* a, Bitstream* b) {
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
