#include <stdint.h>

/*given a new byte and the previous checksum value,
  assigns a new checksum to that value*/

void
ogg_crc(uint8_t byte, void *checksum);
