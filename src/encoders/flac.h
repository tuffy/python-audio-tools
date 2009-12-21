struct flac_STREAMINFO {
  uint16_t minimum_block_size;  /*16  bits*/
  uint16_t maximum_block_size;  /*16  bits*/
  uint32_t minimum_frame_size;  /*24  bits*/
  uint32_t maximum_frame_size;  /*24  bits*/
  uint32_t sample_rate;         /*20  bits*/
  uint8_t channels;             /*3   bits*/
  uint8_t bits_per_sample;      /*5   bits*/
  uint64_t total_samples;       /*36  bits*/
  unsigned char md5sum[16];     /*128 bits*/

  unsigned int crc8;
  unsigned int crc16;
  unsigned int total_frames;
};

struct flac_frame_header {
  uint8_t blocking_strategy;
  uint32_t block_size;
  uint32_t sample_rate;
  uint8_t channel_assignment;
  uint8_t channel_count;
  uint8_t bits_per_sample;
  uint64_t frame_number;
};

typedef enum {FLAC_SUBFRAME_CONSTANT,
	      FLAC_SUBFRAME_VERBATIM,
	      FLAC_SUBFRAME_FIXED,
	      FLAC_SUBFRAME_LPC} flac_subframe_type;

struct flac_subframe_header {
  flac_subframe_type type;
  uint8_t order;
  uint8_t wasted_bits_per_sample;
};

typedef enum {OK,ERROR} status;

static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args);

void FlacEncoder_write_streaminfo(Bitstream *bs,
				  struct flac_STREAMINFO streaminfo);

void FlacEncoder_write_frame(Bitstream *bs,
			     struct flac_STREAMINFO *streaminfo,
			     struct ia_array *samples);


void FlacEncoder_write_frame_header(Bitstream *bs,
				    struct flac_STREAMINFO *streaminfo,
				    struct ia_array *samples);

void FlacEncoder_write_constant_subframe(BitbufferW *bbw,
					 int bits_per_sample,
					 int32_t sample);

void FlacEncoder_write_verbatim_subframe(BitbufferW *bbw,
					 int bits_per_sample,
					 struct i_array *samples);

void write_utf8(Bitstream *stream, unsigned int value);

void md5_update(void *data, unsigned char *buffer, unsigned long len);

#include "flac_crc.h"

