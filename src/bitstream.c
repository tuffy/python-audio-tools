#include "bitstream.h"
#include <stdlib.h>
#include <stdint.h>

const static unsigned int read_bits_table[0x900][8] =
#include "read_bits_table.h"
    ;

const static unsigned int write_bits_table[0x400][0x900] =
#include "write_bits_table.h"
    ;

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

unsigned int read_bits(Bitstream* bs, unsigned int count) {
  int context = bs->state;
  unsigned int result;
  unsigned int byte;
  struct bs_callback* callback;
  unsigned int accumulator = 0;

  while (count > 0) {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      context = 0x800 | byte;
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte);
    }

    result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

    accumulator = (accumulator << ((result & 0xF00000) >> 20)) |
      ((result & 0xFF000) >> 12);
    count -= ((result & 0xF00000) >> 20);
    context = (result & 0xFFF);
  }

  bs->state = context;
  return accumulator;
}

uint64_t read_bits64(Bitstream* bs, unsigned int count) {
  int context = bs->state;
  unsigned int result;
  unsigned int byte;
  struct bs_callback* callback;
  uint64_t accumulator = 0;

  while (count > 0) {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      context = 0x800 | byte;
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte);
    }

    result = read_bits_table[context][(count > 8 ? 8 : count) - 1];

    accumulator = (accumulator << ((result & 0xF00000) >> 20)) |
      ((result & 0xFF000) >> 12);
    count -= ((result & 0xF00000) >> 20);
    context = (result & 0xFFF);
  }

  bs->state = context;
  return accumulator;
}

unsigned int read_unary(Bitstream* bs, int stop_bit) {
    static unsigned int jumptable[0x900][2] =
#include "read_unary_table.h"
    ;
  int context = bs->state;
  unsigned int result;
  struct bs_callback* callback;
  unsigned int byte;
  unsigned int accumulator = 0;

  do {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte);
      context = 0x800 | byte;
    }

    result = jumptable[context][stop_bit];

    accumulator += ((result & 0xFF000) >> 12);

    context = result & 0xFFF;
  } while (result >> 24);

  bs->state = context;
  return accumulator;
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
