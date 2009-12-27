#include <Python.h>
#include <stdint.h>
#include "../bitstream_w.h"
#include "../array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2009  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *******************************************************/

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

/*writes a STREAMINFO metadata block to the bitstream*/
void FlacEncoder_write_streaminfo(Bitstream *bs,
				  struct flac_STREAMINFO streaminfo);

/*takes a list of sample lists (one per channel)
  and the FLAC's streaminfo
  writes a full FLAC frame to the bitstream*/
void FlacEncoder_write_frame(Bitstream *bs,
			     struct flac_STREAMINFO *streaminfo,
			     struct ia_array *samples);

/*takes a list of sample lists (one per channel)
  and the FLAC's streaminfo
  writes a FLAC frame header to the bitstream*/
void FlacEncoder_write_frame_header(Bitstream *bs,
				    struct flac_STREAMINFO *streaminfo,
				    struct ia_array *samples);


/*writes a CONSTANT subframe with the value "sample"
  to the bitbuffer*/
void FlacEncoder_write_constant_subframe(BitbufferW *bbw,
					 int bits_per_sample,
					 int32_t sample);

/*writes a VERBATIM subframe with the values "samples"
  to the bitbuffer*/
void FlacEncoder_write_verbatim_subframe(BitbufferW *bbw,
					 int bits_per_sample,
					 struct i_array *samples);

/*write a FIXED subframe with values from "samples"
  and the given "predictor_order" (from 0-4) to the bitbuffer*/
void FlacEncoder_write_fixed_subframe(BitbufferW *bbw,
				      int bits_per_sample,
				      struct i_array *samples,
				      int predictor_order);

/*writes an LPC subframe with values from "samples"
  a list of LPC coefficients and a LPC shift needed value
  to the bitbuffer*/
void FlacEncoder_write_lpc_subframe(BitbufferW *bbw,
				    int bits_per_sample,
				    struct i_array *samples,
				    struct i_array *coeffs,
				    int shift_needed);

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

/*writes a UTF-8 value to the bitstream*/
void write_utf8(Bitstream *stream, unsigned int value);

/*an MD5 summing callback, updated when reading input strings*/
void md5_update(void *data, unsigned char *buffer, unsigned long len);

#include "flac_crc.h"

