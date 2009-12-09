#ifndef BITSTREAM_H
#define BITSTREAM_H

struct bs_callback {
  void (*callback)(unsigned int, void*);
  void *data;
  struct bs_callback* next;
};

typedef struct {
  FILE* file;
  int state;
  struct bs_callback* callback;
} Bitstream;

typedef enum {BYTE_ALIGN_READ,BYTE_ALIGN_WRITE} byte_align_mode;

const static unsigned int read_bits_table[0x900][8] =
#include "read_bits_table.h"
  ;

const static unsigned int write_bits_table[0x400][0x900] =
#include "write_bits_table.h"
  ;

const static unsigned int read_unary_table[0x900][2] =
#include "read_unary_table.h"
  ;

Bitstream* bs_open(FILE* f);

void bs_close(Bitstream* bs);

void bs_add_callback(Bitstream* bs,
		     void (*callback)(unsigned int, void*),
		     void *data);

static inline unsigned int read_bits(Bitstream* bs, unsigned int count) {
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
	callback->callback(byte,callback->data);
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

static inline int read_signed_bits(Bitstream* bs, unsigned int count) {
  if (!read_bits(bs,1)) {
    return read_bits(bs,count - 1);
  } else {
    return read_bits(bs,count - 1) - (1 << (count - 1));
  }
}

static inline uint64_t read_bits64(Bitstream* bs, unsigned int count) {
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
	callback->callback(byte,callback->data);
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

static inline unsigned int read_unary(Bitstream* bs, int stop_bit) {
  int context = bs->state;
  unsigned int result;
  struct bs_callback* callback;
  unsigned int byte;
  unsigned int accumulator = 0;

  do {
    if (context == 0) {
      byte = (unsigned int)fgetc(bs->file);
      for (callback = bs->callback; callback != NULL; callback = callback->next)
	callback->callback(byte,callback->data);
      context = 0x800 | byte;
    }

    result = read_unary_table[context][stop_bit];

    accumulator += ((result & 0xFF000) >> 12);

    context = result & 0xFFF;
  } while (result >> 24);

  bs->state = context;
  return accumulator;
}

int bs_eof(Bitstream* bs);

void write_bits(Bitstream* bs, unsigned int count, int value);
void write_unary(Bitstream* bs, int stop_bit, int value);

void byte_align(Bitstream* bs, byte_align_mode mode);

#endif
