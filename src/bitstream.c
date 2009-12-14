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

void bs_add_callback(Bitstream* bs,
		     void (*callback)(unsigned int, void*),
		     void *data) {
  struct bs_callback* callback_node = malloc(sizeof(struct bs_callback));
  callback_node->callback = callback;
  callback_node->data = data;
  callback_node->next = bs->callback;
  bs->callback = callback_node;
}

int bs_eof(Bitstream* bs) {
  return feof(bs->file);
}
