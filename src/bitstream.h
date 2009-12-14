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

Bitstream* bs_open(FILE* f);

void bs_close(Bitstream* bs);

void bs_add_callback(Bitstream* bs,
		     void (*callback)(unsigned int, void*),
		     void *data);

int bs_eof(Bitstream* bs);

#endif
