#ifndef BITSTREAM
#define BITSTREAM

struct bs_callback {
  void (*callback)(unsigned int);
  struct bs_callback* next;
};

typedef struct {
  FILE* file;
  int state;
  struct bs_callback* callback;
} Bitstream;


Bitstream* bs_open(FILE* f);
void bs_close(Bitstream* bs);
void bs_add_callback(Bitstream* bs, void (*callback)(unsigned int));
unsigned int read_bits(Bitstream* bs, unsigned int count);
uint64_t read_bits64(Bitstream* bs, unsigned int count);
unsigned int read_unary(Bitstream* bs, int stop_bit);
int bs_eof(Bitstream* bs);
void write_bits(Bitstream* bs, unsigned int count, int value);
void write_unary(Bitstream* bs, int stop_bit, int value);

#endif
