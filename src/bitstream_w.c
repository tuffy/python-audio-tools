#include "bitstream_w.h"
#include <string.h>

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
  return bs;
}

void bs_close(Bitstream *bs) {
  struct bs_callback *node;
  struct bs_callback *next;

  if (bs == NULL) return;

  if (bs->file != NULL) fclose(bs->file);

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

const unsigned int write_bits_table[0x400][0x900] =
#include "write_bits_table.h"
  ;

const unsigned int write_unary_table[0x400][0x20] =
#include "write_unary_table.h"
    ;

/*****************************
   buffer writing functions

 these write bits to a buffer
which might be written to disk
******************************/

BitbufferW* bbw_open(unsigned int initial_size) {
  BitbufferW *bbw = malloc(sizeof(BitbufferW));
  bbw->actions = malloc(sizeof(BitbufferAction) * initial_size);
  bbw->size = 0;
  bbw->total_size = initial_size;
  bbw->bits_written = 0;
  return bbw;
}

void bbw_close(BitbufferW *bbw) {
  free(bbw->actions);
  free(bbw);
}

void bbw_reset(BitbufferW *bbw) {
  bbw->size = 0;
  bbw->bits_written = 0;
}

void bbw_dump(BitbufferW *bbw, Bitstream *bs) {
  unsigned int i;
  BitbufferAction action;

  /* fprintf(stderr,"dumping %d actions\n",bbw->size); */

  for (i = 0; i < bbw->size; i++) {
    action = bbw->actions[i];
    switch (action.action) {
    case BBW_WRITE_BITS:
      /* fprintf(stderr, */
      /* 	      "%5.5d - write_bits %d %u\n", */
      /* 	      i,bbw->keys[i].count,bbw->values[i].value); */
      write_bits(bs,action.key.count,action.value.value);
      break;
    case BBW_WRITE_SIGNED_BITS:
      /* fprintf(stderr, */
      /* 	      "%5.5d - write_signed_bits %d %d\n", */
      /* 	      i,bbw->keys[i].count,bbw->values[i].value); */
      write_signed_bits(bs,action.key.count,action.value.value);
      break;
    case BBW_WRITE_BITS64:
      /* fprintf(stderr, */
      /* 	      "%5.5d - write_bits64 %d %lu\n", */
      /* 	      i,bbw->keys[i].count,bbw->values[i].value64); */
      write_bits64(bs,action.key.count,action.value.value64);
      break;
    case BBW_WRITE_UNARY:
      /* fprintf(stderr, */
      /* 	      "%5.5d - write_unary %d %d\n", */
      /* 	      i,bbw->keys[i].count,bbw->values[i].value); */
      write_unary(bs,action.key.stop_bit,action.value.value);
      break;
    case BBW_BYTE_ALIGN:
      /* fprintf(stderr, */
      /* 	      "%5.5d - byte_align\n",i); */
      byte_align_w(bs);
      break;
    }
  }
}

void bbw_append(BitbufferW *target, BitbufferW *source) {
  /*if the target buffer is too small to contain the items from source
    realloc buffer sizes to fit*/
  if ((target->total_size - target->size) < source->size) {
    target->total_size = target->size + source->size;
    target->actions = realloc(target->actions,
			      sizeof(BitbufferAction) * target->total_size);
  }

  /*then memcpy source buffers to target buffers at the proper offset*/
  memcpy(target->actions + target->size,
	 source->actions,
	 sizeof(BitbufferAction) * source->size);

  /*and update the "size" and "bits_written" fields*/
  target->size += source->size;
  target->bits_written += source->bits_written;
}

void bbw_swap(BitbufferW *a, BitbufferW *b) {
  BitbufferW c;

  /*move values from a to c*/
  c.actions = a->actions;
  c.size = a->size;
  c.total_size = a->total_size;
  c.bits_written = a->bits_written;

  /*move values from b to a*/
  a->actions = b->actions;
  a->size = b->size;
  a->total_size = b->total_size;
  a->bits_written = b->bits_written;

  /*move values from c to b*/
  b->actions = c.actions;
  b->size = c.size;
  b->total_size = c.total_size;
  b->bits_written = c.bits_written;
}
