#include <stdint.h>

/*given a new byte and the previous checksum value,
  assigns a new checksum to that value*/

void
flac_crc8(uint8_t byte, void *checksum);

void
flac_crc16(uint8_t byte, void *checksum);
