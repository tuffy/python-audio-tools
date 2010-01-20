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
  void (*callback)(unsigned int, void*);
  void *data;
  struct bs_callback *next;
};

typedef struct Bitstream_s {
  FILE *file;
  int state;
  struct bs_callback *callback;

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

Bitstream* bs_open(FILE *f);

void bs_close(Bitstream *bs);

void bs_add_callback(Bitstream *bs,
		     void (*callback)(unsigned int, void*),
		     void *data);

int bs_eof(Bitstream *bs);


void write_bits_actual(Bitstream* bs, unsigned int count, int value);

void write_signed_bits_actual(Bitstream* bs, unsigned int count, int value);

void write_bits64_actual(Bitstream* bs, unsigned int count, uint64_t value);

void write_unary_actual(Bitstream* bs, int stop_bit, int value);

void byte_align_w_actual(Bitstream* bs);



typedef enum {BBW_WRITE_BITS,
	      BBW_WRITE_SIGNED_BITS,
	      BBW_WRITE_BITS64,
	      BBW_WRITE_UNARY,
	      BBW_BYTE_ALIGN} bbw_action;

typedef struct {
  bbw_action action;
  union {
    unsigned int count;
    int stop_bit;
  } key;
  union {
    int value;
    uint64_t value64;
  } value;
} BitbufferAction;

typedef struct {
  BitbufferAction *actions;
  unsigned int size;
  unsigned int total_size;
  unsigned int bits_written;
} BitbufferW;

BitbufferW* bbw_open(unsigned int initial_size);

void bbw_close(BitbufferW *bbw);

void bbw_reset(BitbufferW *bbw);

void bbw_dump(BitbufferW *bbw, Bitstream *bs);

void bbw_append(BitbufferW *target, BitbufferW *source);

void bbw_swap(BitbufferW *a, BitbufferW *b);

static inline void bbw_enlarge(BitbufferW *bbw) {
  bbw->total_size *= 2;
  bbw->actions = realloc(bbw->actions,
			 sizeof(BitbufferAction) * bbw->total_size);
}

static inline void bbw_write_bits(BitbufferW *bbw, unsigned int count,
				  int value) {
  BitbufferAction write;
  write.action = BBW_WRITE_BITS;
  write.key.count = count;
  write.value.value = value;

  if (bbw->size == bbw->total_size)
    bbw_enlarge(bbw);

  bbw->actions[bbw->size++] = write;
  bbw->bits_written += count;
}

static inline void bbw_write_signed_bits(BitbufferW *bbw, unsigned int count,
					 int value) {
  BitbufferAction write;
  write.action = BBW_WRITE_SIGNED_BITS;
  write.key.count = count;
  write.value.value = value;

  if (bbw->size == bbw->total_size)
    bbw_enlarge(bbw);

  bbw->actions[bbw->size++] = write;
  bbw->bits_written += count;
}

static inline void bbw_write_bits64(BitbufferW *bbw, unsigned int count,
				    uint64_t value) {
  BitbufferAction write;
  write.action = BBW_WRITE_BITS64;
  write.key.count = count;
  write.value.value64 = value;

  if (bbw->size == bbw->total_size)
    bbw_enlarge(bbw);

  bbw->actions[bbw->size++] = write;
  bbw->bits_written += count;
}

static inline void bbw_write_unary(BitbufferW *bbw, int stop_bit, int value) {
  BitbufferAction write;
  write.action = BBW_WRITE_UNARY;
  write.key.stop_bit = stop_bit;
  write.value.value64 = value;

  if (bbw->size == bbw->total_size)
    bbw_enlarge(bbw);

  bbw->actions[bbw->size++] = write;
  bbw->bits_written += (value + 1);
}


static inline void bbw_byte_align_w(BitbufferW *bbw) {
  BitbufferAction write;
  write.action = BBW_BYTE_ALIGN;

  if (bbw->size == bbw->total_size)
    bbw_enlarge(bbw);

  bbw->actions[bbw->size++] = write;
  bbw->bits_written += (bbw->bits_written % 8);
}


#endif
