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

  int bits_written;
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
Bitstream* bs_open_accumulator(void);

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


void write_bits_accumulator(Bitstream* bs, unsigned int count, int value);

void write_signed_bits_accumulator(Bitstream* bs, unsigned int count,
				   int value);

void write_bits64_accumulator(Bitstream* bs, unsigned int count,
			      uint64_t value);

void write_unary_accumulator(Bitstream* bs, int stop_bit, int value);

void byte_align_w_accumulator(Bitstream* bs);

#endif
