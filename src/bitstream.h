#ifndef BITSTREAM_H
#define BITSTREAM_H

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2009  Brian Langenberger

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

typedef struct {
  FILE *file;
  int state;
  struct bs_callback *callback;
} Bitstream;

Bitstream* bs_open(FILE *f);

void bs_close(Bitstream *bs);

void bs_add_callback(Bitstream *bs,
		     void (*callback)(unsigned int, void*),
		     void *data);

int bs_eof(Bitstream *bs);



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



#endif
