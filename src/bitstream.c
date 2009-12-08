#include "bitstream.h"
#include <stdlib.h>
#include <stdint.h>

Bitstream* bs_open(FILE* f) {
  Bitstream* bs = malloc(sizeof(Bitstream));
  bs->file = f;
  bs->state = 0;
  bs->callback = NULL;
  return bs;
}

void bs_close(Bitstream* bs) {
  struct bs_callback* node;
  struct bs_callback* next;

  if (bs == NULL) return;

  if (bs->file != NULL) fclose(bs->file);

  for (node = bs->callback; node != NULL; node = next) {
    next = node->next;
    free(node);
  }
  free(bs);
}

void bs_add_callback(Bitstream* bs, void (*callback)(unsigned int)) {
  struct bs_callback* callback_node = malloc(sizeof(struct bs_callback));
  callback_node->callback = callback;
  callback_node->next = bs->callback;
  bs->callback = callback_node;
}

int bs_eof(Bitstream* bs) {
  return feof(bs->file);
}

void write_bits(Bitstream* bs, unsigned int count, int value) {
  int bits_to_write;
  int value_to_write;
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

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
	callback->callback(byte);
    }

    /*update the context*/
    context = result & 0x3FF;

    /*decrement the count and value*/
    value -= (value_to_write << (count - bits_to_write));
    count -= bits_to_write;
  }
  bs->state = context;
}


void write_unary(Bitstream* bs, int stop_bit, int value) {
  static unsigned int jumptable[0x400][0x20] =
#include "write_unary_table.h"
    ;
  int result;
  int context = bs->state;
  unsigned int byte;
  struct bs_callback* callback;

  /*send continuation blocks until we get to 7 bits or less*/
  while (value >= 8) {
    result = jumptable[context][(stop_bit << 4) | 0x08];
    if (result >> 18) {
      byte = (result >> 10) & 0xFF;
      fputc(byte,bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte);
    }

    context = result & 0x3FF;

    value -= 8;
  }

  result = jumptable[context][(stop_bit << 4) | value];

  if (result >> 18) {
      fputc((result >> 10) & 0xFF,bs->file);
  }

  context = result & 0x3FF;
  bs->state = context;
}

void byte_align(Bitstream* bs, byte_align_mode mode) {
  switch (mode) {
  case BYTE_ALIGN_READ:
    bs->state = 0;
    break;
  case BYTE_ALIGN_WRITE:
    write_bits(bs,7,0);
    bs->state = 0;
    break;
  }
}
