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


void FlacEncoder_write_fixed_subframe(BitbufferW *bbw,
				      int bits_per_sample,
				      struct i_array *samples,
				      int predictor_order);

/*given a "predictor_order" int
  given a coding method (0 or 1)
  a list of rice_parameters ints
  and a list of residuals ints
  encodes the residuals into partitions and writes them to "bbw"
  (a Rice partition also requires a "partition_order" which can
  be derived from the length of "rice_parameters")
 */
void FlacEncoder_write_residual(BitbufferW *bbw,
				int predictor_order,
				int coding_method,
				struct i_array *rice_parameters,
				struct i_array *residuals);

/*given a coding method (0 or 1)
  a rice_parameter int
  and a list of residuals ints
  encodes the residual partition and writes them to "bbw"*/
void FlacEncoder_write_residual_partition(BitbufferW *bbw,
					  int coding_method,
					  int rice_parameter,
					  struct i_array *residuals);

void write_utf8(Bitstream *stream, unsigned int value);

void md5_update(void *data, unsigned char *buffer, unsigned long len);

#include "flac_crc.h"

