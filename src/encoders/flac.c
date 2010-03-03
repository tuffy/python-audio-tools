#include "flac.h"
#include "flac_lpc.h"
#include "../pcmreader.h"
#include <openssl/md5.h>
#include <limits.h>
#include <assert.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

#define VERSION_STRING_(x) #x
#define VERSION_STRING(x) VERSION_STRING_(x)
const static char* AUDIOTOOLS_VERSION = VERSION_STRING(VERSION);

#define DEFAULT_PADDING_SIZE 1024

#define MIN(x,y) ((x) < (y) ? (x) : (y))
#define MAX(x,y) ((x) > (y) ? (x) : (y))

#ifndef STANDALONE
PyObject* encoders_encode_flac(PyObject *dummy,
			       PyObject *args, PyObject *keywds) {
  char *filename;
  FILE *file;
  Bitstream *stream;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;
  struct flac_STREAMINFO streaminfo;
  char version_string[0xFF];
  static char *kwlist[] = {"filename",
			   "pcmreader",
			   "block_size",
			   "max_lpc_order",
			   "min_residual_partition_order",
			   "max_residual_partition_order",
			   "mid_side",
			   "adaptive_mid_side",
			   "exhaustive_model_search",

			   "disable_verbatim_subframes",
			   "disable_constant_subframes",
			   "disable_fixed_subframes",
			   "disable_lpc_subframes",
			   NULL};
  MD5_CTX md5sum;

  struct ia_array samples;

  streaminfo.options.mid_side = 0;
  streaminfo.options.adaptive_mid_side = 0;
  streaminfo.options.exhaustive_model_search = 0;

  streaminfo.options.no_verbatim_subframes = 0;
  streaminfo.options.no_constant_subframes = 0;
  streaminfo.options.no_fixed_subframes = 0;
  streaminfo.options.no_lpc_subframes = 0;

  /*extract a filename, PCMReader-compatible object and encoding options:
    blocksize int*/
  if (!PyArg_ParseTupleAndKeywords(args,keywds,"sOiiii|iiiiiii",
				   kwlist,
				   &filename,
				   &pcmreader_obj,
				   &(streaminfo.options.block_size),
				   &(streaminfo.options.max_lpc_order),
				   &(streaminfo.options.min_residual_partition_order),
				   &(streaminfo.options.max_residual_partition_order),
				   &(streaminfo.options.mid_side),
				   &(streaminfo.options.adaptive_mid_side),
				   &(streaminfo.options.exhaustive_model_search),

				   &(streaminfo.options.no_verbatim_subframes),
				   &(streaminfo.options.no_constant_subframes),
				   &(streaminfo.options.no_fixed_subframes),
				   &(streaminfo.options.no_lpc_subframes)))
    return NULL;

  if (streaminfo.options.block_size <= 0) {
    PyErr_SetString(PyExc_ValueError,"blocksize must be positive");
    return NULL;
  }

  streaminfo.options.qlp_coeff_precision = FlacEncoder_qlp_coeff_precision(streaminfo.options.block_size);

  /*open the given filename for writing*/
  if ((file = fopen(filename,"wb")) == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return NULL;
  }

  /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
  if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
    fclose(file);
    Py_DECREF(pcmreader_obj);
    return NULL;
  }

#else

  int encoders_encode_flac(char *filename,
                           FILE *input,
			   int block_size,
			   int max_lpc_order,
			   int min_residual_partition_order,
			   int max_residual_partition_order,
			   int mid_side,
			   int adaptive_mid_side,
			   int exhaustive_model_search) {
  FILE *file;
  Bitstream *stream;
  struct pcm_reader *reader;
  struct flac_STREAMINFO streaminfo;
  char version_string[0xFF];
  MD5_CTX md5sum;

  struct ia_array samples;

  streaminfo.options.block_size = block_size;
  streaminfo.options.max_lpc_order = max_lpc_order;
  streaminfo.options.min_residual_partition_order = min_residual_partition_order;
  streaminfo.options.max_residual_partition_order = max_residual_partition_order;
  streaminfo.options.qlp_coeff_precision = FlacEncoder_qlp_coeff_precision(block_size);
  streaminfo.options.mid_side = mid_side;
  streaminfo.options.adaptive_mid_side = adaptive_mid_side;
  streaminfo.options.exhaustive_model_search = exhaustive_model_search;

  streaminfo.options.no_verbatim_subframes = 0;
  streaminfo.options.no_constant_subframes = 0;
  streaminfo.options.no_fixed_subframes = 0;
  streaminfo.options.no_lpc_subframes = 0;

  file = fopen(filename,"wb");
  reader = pcmr_open(input,48000,5,24,0,1);/*FIXME - assume CD quality for now*/

#endif

  if (reader->bits_per_sample <= 16) {
    streaminfo.options.max_rice_parameter = 0xE;
  } else {
    streaminfo.options.max_rice_parameter = 0x1E;
  }

  sprintf(version_string,"Python Audio Tools %s",AUDIOTOOLS_VERSION);
  MD5_Init(&md5sum);
  pcmr_add_callback(reader,md5_update,&md5sum);

  stream = bs_open(file);
  bs_add_callback(stream,flac_crc8,&(streaminfo.crc8));
  bs_add_callback(stream,flac_crc16,&(streaminfo.crc16));

  /*fill streaminfo with some placeholder values*/
  /* streaminfo.minimum_block_size = 0xFFFF; */
  /* streaminfo.maximum_block_size = 0; */
  streaminfo.minimum_block_size =
    streaminfo.maximum_block_size =
    streaminfo.options.block_size;
  streaminfo.minimum_frame_size = 0xFFFFFF;
  streaminfo.maximum_frame_size = 0;
  streaminfo.sample_rate = reader->sample_rate;
  streaminfo.channels = reader->channels;
  streaminfo.bits_per_sample = reader->bits_per_sample;
  streaminfo.total_samples = 0;
  memcpy(streaminfo.md5sum,
	 "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
	 16);
  streaminfo.crc8 = streaminfo.crc16 = 0;
  streaminfo.total_frames = 0;

  /*write FLAC stream header*/
  stream->write_bits(stream,32,0x664C6143);

  /*write metadata header*/
  stream->write_bits(stream,1,0);
  stream->write_bits(stream,7,0);
  stream->write_bits(stream,24,34);

  /*write placeholder STREAMINFO*/
  FlacEncoder_write_streaminfo(stream,streaminfo);

  /*write VORBIS_COMMENT*/
  stream->write_bits(stream,1,0);
  stream->write_bits(stream,7,4);
  stream->write_bits(stream,24,4 + strlen(version_string) + 4);

  /*this is a hack to fake little-endian output*/
  stream->write_bits(stream,8,strlen(version_string));
  stream->write_bits(stream,24,0);
  fputs(version_string,file);
  stream->write_bits(stream,32,0);

  /*write PADDING*/
  stream->write_bits(stream,1,1);
  stream->write_bits(stream,7,1);
  stream->write_bits(stream,24,DEFAULT_PADDING_SIZE);
  stream->write_bits(stream,DEFAULT_PADDING_SIZE * 8,0);

  /*build frames until reader is empty,
    which updates STREAMINFO in the process*/
  iaa_init(&samples,reader->channels,streaminfo.options.block_size);

  if (!pcmr_read(reader,streaminfo.options.block_size,&samples))
    goto error;

  while (iaa_getitem(&samples,0)->size > 0) {
    FlacEncoder_write_frame(stream,&streaminfo,&samples);

    if (!pcmr_read(reader,streaminfo.options.block_size,&samples))
      goto error;
  }

  /*go back and re-write STREAMINFO with complete values*/
  MD5_Final(streaminfo.md5sum,&md5sum);
  fseek(stream->file, 4 + 4, SEEK_SET);
  FlacEncoder_write_streaminfo(stream,streaminfo);

  iaa_free(&samples); /*deallocate the temporary samples block*/
  pcmr_close(reader); /*close the pcm_reader object
			which calls pcmreader.close() in the process*/
  bs_close(stream);     /*close the output file*/
#ifndef STANDALONE
  Py_INCREF(Py_None);
  return Py_None;
 error:
  /*an error result does everything a regular result does
    but returns NULL instead of Py_None*/
  iaa_free(&samples);
  pcmr_close(reader);
  bs_close(stream);
  return NULL;
}
#else
 return 1;
 error:
 iaa_free(&samples);
 pcmr_close(reader);
 bs_close(stream);
 return 0;
}
#endif


void FlacEncoder_write_streaminfo(Bitstream *bs,
				  struct flac_STREAMINFO streaminfo) {
  int i;

  bs->write_bits(bs,16,MAX(MIN(streaminfo.minimum_block_size,
			       (1 << 16) - 1),0));

  bs->write_bits(bs,16,MAX(MIN(streaminfo.maximum_block_size,
			       (1 << 16) - 1),0));

  bs->write_bits(bs,24,MAX(MIN(streaminfo.minimum_frame_size,
			       (1 << 24) - 1),0));

  bs->write_bits(bs,24,MAX(MIN(streaminfo.maximum_frame_size,
			       (1 << 24) - 1),0));

  bs->write_bits(bs,20,MAX(MIN(streaminfo.sample_rate,
			       (1 << 20) - 1),0));

  bs->write_bits(bs,3,MAX(MIN(streaminfo.channels - 1,
			      (1 << 3) - 1),0));

  bs->write_bits(bs,5,MAX(MIN(streaminfo.bits_per_sample - 1,
			      (1 << 5) - 1),0));

  assert(streaminfo.total_samples >= 0);
  assert(streaminfo.total_samples < (1l << 36));
  bs->write_bits64(bs,36,streaminfo.total_samples);

  for (i = 0; i < 16; i++)
    bs->write_bits(bs,8,streaminfo.md5sum[i]);
}

void FlacEncoder_write_frame(Bitstream *bs,
			     struct flac_STREAMINFO *streaminfo,
			     struct ia_array *samples) {
  ia_size_t i;
  long startpos;
  long framesize;

  Bitstream *left_subframe;
  Bitstream *right_subframe;
  Bitstream *side_subframe;

  Bitstream *avg_subframe;
  Bitstream *difference_subframe;

  struct i_array side_samples;
  struct i_array avg_subframe_samples;
  struct i_array difference_subframe_samples;

  streaminfo->crc8 = streaminfo->crc16 = 0;

  startpos = ftell(bs->file);

  /*for each channel in samples, write a subframe*/

  if (!(streaminfo->options.mid_side ||
	streaminfo->options.adaptive_mid_side) ||
      (samples->size != 2)) {
    /*if no mid/adaptive-mid-side or non-stereo, do independent*/
    FlacEncoder_write_frame_header(bs,streaminfo,samples,samples->size - 1);
    for (i = 0; i < samples->size; i++) {
      FlacEncoder_write_subframe(bs,
				 &(streaminfo->options),
				 streaminfo->bits_per_sample,
				 iaa_getitem(samples,i));
    }
  } else {
    /*otherwise, first try independent subframes*/
    left_subframe = bs_open_recorder();
    FlacEncoder_write_subframe(left_subframe,
			       &(streaminfo->options),
			       streaminfo->bits_per_sample,
			       iaa_getitem(samples,0));
    right_subframe = bs_open_recorder();
    FlacEncoder_write_subframe(right_subframe,
			       &(streaminfo->options),
			       streaminfo->bits_per_sample,
			       iaa_getitem(samples,1));

    /*then, try mid-side subframe*/
    avg_subframe = bs_open_recorder();
    difference_subframe = bs_open_recorder();

    ia_init(&avg_subframe_samples,iaa_getitem(samples,0)->size);
    ia_init(&difference_subframe_samples,iaa_getitem(samples,0)->size);

    FlacEncoder_build_mid_side_subframes(samples,
					 &avg_subframe_samples,
					 &difference_subframe_samples);

    FlacEncoder_write_subframe(avg_subframe,
  			       &(streaminfo->options),
  			       streaminfo->bits_per_sample,
  			       &avg_subframe_samples);

    FlacEncoder_write_subframe(difference_subframe,
  			       &(streaminfo->options),
  			       streaminfo->bits_per_sample + 1,
  			       &difference_subframe_samples);

    if (streaminfo->options.mid_side) {
      /*if mid-side is selected, try left-side and side-right also*/

      side_subframe = bs_open_recorder();
      ia_init(&side_samples,iaa_getitem(samples,0)->size);

      FlacEncoder_build_left_side_subframes(samples,&side_samples);

      FlacEncoder_write_subframe(side_subframe,
				 &(streaminfo->options),
				 streaminfo->bits_per_sample + 1,
				 &side_samples);

      if ((left_subframe->bits_written + right_subframe->bits_written) <
	  MIN(left_subframe->bits_written + side_subframe->bits_written,
	      MIN(side_subframe->bits_written + right_subframe->bits_written,
		  avg_subframe->bits_written + difference_subframe->bits_written))) {
	/*do independent subframes*/
	FlacEncoder_write_frame_header(bs,streaminfo,samples,1);
	bs_dump_records(bs,left_subframe);
	bs_dump_records(bs,right_subframe);
      } else if ((left_subframe->bits_written + side_subframe->bits_written) <
		 MIN(side_subframe->bits_written + right_subframe->bits_written,
		     avg_subframe->bits_written + difference_subframe->bits_written)) {
	/*do left-side subframes*/
	FlacEncoder_write_frame_header(bs,streaminfo,samples,0x8);
	bs_dump_records(bs,left_subframe);
	bs_dump_records(bs,side_subframe);
      } else if (side_subframe->bits_written + right_subframe->bits_written <
		 avg_subframe->bits_written + difference_subframe->bits_written) {
	/*do side-right subframes*/
	FlacEncoder_write_frame_header(bs,streaminfo,samples,0x9);
	bs_dump_records(bs,side_subframe);
	bs_dump_records(bs,right_subframe);
      } else {
	/*do mid-side subframes*/
	FlacEncoder_write_frame_header(bs,streaminfo,samples,0xA);
	bs_dump_records(bs,avg_subframe);
	bs_dump_records(bs,difference_subframe);
      }

      bs_close(side_subframe);
      ia_free(&side_samples);
    } else {
      /*otherwise, write the smaller of independent and mid-side to disk,
	along with a frame header*/
      if ((left_subframe->bits_written + right_subframe->bits_written) <=
	  (avg_subframe->bits_written + difference_subframe->bits_written)) {
	FlacEncoder_write_frame_header(bs,streaminfo,samples,1);
	bs_dump_records(bs,left_subframe);
	bs_dump_records(bs,right_subframe);
      } else {
	FlacEncoder_write_frame_header(bs,streaminfo,samples,0xA);
	bs_dump_records(bs,avg_subframe);
	bs_dump_records(bs,difference_subframe);
      }
    }

    bs_close(left_subframe);
    bs_close(right_subframe);
    bs_close(avg_subframe);
    bs_close(difference_subframe);
    ia_free(&avg_subframe_samples);
    ia_free(&difference_subframe_samples);
  }

  bs->byte_align(bs);

  /*write CRC-16*/
  bs->write_bits(bs, 16, streaminfo->crc16);

  /*update streaminfo with new values*/
  framesize = ftell(bs->file) - startpos;

  /* streaminfo->minimum_block_size = MIN(streaminfo->minimum_block_size, */
  /* 				       iaa_getitem(samples,0)->size); */
  /* streaminfo->maximum_block_size = MAX(streaminfo->maximum_block_size, */
  /* 				       iaa_getitem(samples,0)->size); */
  streaminfo->minimum_frame_size = MIN(streaminfo->minimum_frame_size,
				       framesize);
  streaminfo->maximum_frame_size = MAX(streaminfo->maximum_frame_size,
				       framesize);
  streaminfo->total_samples += iaa_getitem(samples,0)->size;
  streaminfo->total_frames++;
}

void FlacEncoder_write_frame_header(Bitstream *bs,
				    struct flac_STREAMINFO *streaminfo,
				    struct ia_array *samples,
				    int channel_assignment) {
  int block_size_bits;
  int sample_rate_bits;
  int bits_per_sample_bits;
  int block_size = iaa_getitem(samples,0)->size;

  /*determine the block size bits from the given amount of samples*/
  switch (block_size) {
  case 192:   block_size_bits = 0x1; break;
  case 576:   block_size_bits = 0x2; break;
  case 1152:  block_size_bits = 0x3; break;
  case 2304:  block_size_bits = 0x4; break;
  case 4608:  block_size_bits = 0x5; break;
  case 256:   block_size_bits = 0x8; break;
  case 512:   block_size_bits = 0x9; break;
  case 1024:  block_size_bits = 0xA; break;
  case 2048:  block_size_bits = 0xB; break;
  case 4096:  block_size_bits = 0xC; break;
  case 8192:  block_size_bits = 0xD; break;
  case 16384: block_size_bits = 0xE; break;
  case 32768: block_size_bits = 0xF; break;
  default:
    if (iaa_getitem(samples,0)->size < (0xFF + 1))
      block_size_bits = 0x6;
    else if (iaa_getitem(samples,0)->size < (0xFFFF + 1))
      block_size_bits = 0x7;
    else
      block_size_bits = 0x0;
    break;
  }

  /*determine sample rate bits from streaminfo*/
  switch (streaminfo->sample_rate) {
  case 88200:  sample_rate_bits = 0x1; break;
  case 176400: sample_rate_bits = 0x2; break;
  case 192000: sample_rate_bits = 0x3; break;
  case 8000:   sample_rate_bits = 0x4; break;
  case 16000:  sample_rate_bits = 0x5; break;
  case 22050:  sample_rate_bits = 0x6; break;
  case 24000:  sample_rate_bits = 0x7; break;
  case 32000:  sample_rate_bits = 0x8; break;
  case 44100:  sample_rate_bits = 0x9; break;
  case 48000:  sample_rate_bits = 0xA; break;
  case 96000:  sample_rate_bits = 0xB; break;
  default:
    if ((streaminfo->sample_rate <= 255000) &&
	((streaminfo->sample_rate % 1000) == 0))
      sample_rate_bits = 0xC;
    else if ((streaminfo->sample_rate <= 655350) &&
	     ((streaminfo->sample_rate % 10) == 0))
      sample_rate_bits = 0xE;
    else if (streaminfo->sample_rate <= 0xFFFF)
      sample_rate_bits = 0xD;
    else
      sample_rate_bits = 0x0;
    break;
  }

  /*determine bits-per-sample bits from streaminfo*/
  switch (streaminfo->bits_per_sample) {
  case 8:  bits_per_sample_bits = 0x1; break;
  case 12: bits_per_sample_bits = 0x2; break;
  case 16: bits_per_sample_bits = 0x4; break;
  case 20: bits_per_sample_bits = 0x5; break;
  case 24: bits_per_sample_bits = 0x6; break;
  default: bits_per_sample_bits = 0x0; break;
  }

  /*once the four bits-encoded fields are set, write the actual header*/
  bs->write_bits(bs, 14, 0x3FFE);              /*sync code*/
  bs->write_bits(bs, 1, 0);                    /*reserved*/
  bs->write_bits(bs, 1, 0);                    /*blocking strategy*/
  bs->write_bits(bs, 4, block_size_bits);      /*block size*/
  bs->write_bits(bs, 4, sample_rate_bits);     /*sample rate*/
  bs->write_bits(bs, 4, channel_assignment);   /*channel assignment*/
  bs->write_bits(bs, 3, bits_per_sample_bits); /*bits per sample*/
  bs->write_bits(bs, 1, 0);                    /*padding*/

  /*frame number is taken from total_frames in streaminfo*/
  write_utf8(bs, streaminfo->total_frames);

  /*if block_size_bits are 0x6 or 0x7, write a PCM frames field*/
  if (block_size_bits == 0x6)
    bs->write_bits(bs, 8, block_size - 1);
  else if (block_size_bits == 0x7)
    bs->write_bits(bs, 16, block_size - 1);

  /*if sample rate is unusual, write one of the three sample rate fields*/
  if (sample_rate_bits == 0xC)
    bs->write_bits(bs, 8, streaminfo->sample_rate / 1000);
  else if (sample_rate_bits == 0xD)
    bs->write_bits(bs, 16, streaminfo->sample_rate);
  else if (sample_rate_bits == 0xE)
    bs->write_bits(bs, 16, streaminfo->sample_rate / 10);

  /*write CRC-8*/
  bs->write_bits(bs, 8, streaminfo->crc8);
}

void FlacEncoder_write_subframe(Bitstream *bs,
				struct flac_encoding_options *options,
				int bits_per_sample,
				struct i_array *samples) {
  ia_size_t i;
  ia_data_t first_sample;

  /*FIXED subframe params*/
  int fixed_predictor_order;
  struct i_array fixed_warm_up_samples;
  struct i_array fixed_residual;
  struct i_array fixed_rice_parameters;
  Bitstream *fixed_subframe;

  /*LPC subframe params*/
  struct i_array lpc_warm_up_samples;
  struct i_array lpc_residual;
  struct i_array lpc_rice_parameters;
  struct i_array lpc_coeffs;
  int lpc_shift_needed;
  Bitstream *lpc_subframe;


  /*check for a constant subframe*/
  if (!options->no_constant_subframes) {
    if (samples->size < 2) {
      FlacEncoder_write_constant_subframe(bs,
					  bits_per_sample,
					  ia_getitem(samples,0));
      return;
    }

    first_sample = ia_getitem(samples,0);
    for (i = 1; i < samples->size; i++) {
      if (ia_getitem(samples,i) != first_sample)
	break;
    }
    if (i == samples->size) {
      FlacEncoder_write_constant_subframe(bs,
					  bits_per_sample,
					  first_sample);
      return;
    }
  }

  /*first check FIXED subframe*/
  ia_init(&fixed_warm_up_samples,8);
  ia_init(&fixed_residual,samples->size);
  ia_init(&fixed_rice_parameters,1);
  fixed_subframe = bs_open_accumulator();

  if (!options->no_fixed_subframes) {
    fixed_predictor_order = FlacEncoder_compute_best_fixed_predictor_order(samples);

    FlacEncoder_evaluate_fixed_subframe(&fixed_warm_up_samples,
					&fixed_residual,
					&fixed_rice_parameters,
					options,
					bits_per_sample,
					samples,
					fixed_predictor_order);

    FlacEncoder_write_fixed_subframe(fixed_subframe,
				     &fixed_warm_up_samples,
				     &fixed_rice_parameters,
				     &fixed_residual,
				     bits_per_sample,
				     fixed_predictor_order);
  } else {
    fixed_predictor_order = -1;
    fixed_subframe->bits_written = INT_MAX;
  }

  /*then check LPC subframe, if necessary*/
  if ((options->max_lpc_order > 0) && (!options->no_lpc_subframes)) {
    options->max_lpc_order = MIN(options->max_lpc_order,
				 samples->size - 1);
    ia_init(&lpc_coeffs,1);
    ia_init(&lpc_warm_up_samples,options->max_lpc_order);
    ia_init(&lpc_residual,samples->size);
    ia_init(&lpc_rice_parameters,1);
    FlacEncoder_compute_best_lpc_coeffs(&lpc_warm_up_samples,
					&lpc_residual,
					&lpc_rice_parameters,
					&lpc_coeffs,
					&lpc_shift_needed,

					options,
					bits_per_sample,
					samples);

    lpc_subframe = bs_open_accumulator();

    FlacEncoder_write_lpc_subframe(lpc_subframe,
				   &lpc_warm_up_samples,
				   &lpc_rice_parameters,
				   &lpc_residual,
				   bits_per_sample,
				   &lpc_coeffs,
				   lpc_shift_needed);

    /*if neither FIXED nor LPC generate small enough subframes,
      use VERBATIM instead*/
    if (((bits_per_sample * samples->size) <= MIN(fixed_subframe->bits_written,
						  lpc_subframe->bits_written))
	&& (!options->no_verbatim_subframes)) {
      FlacEncoder_write_verbatim_subframe(bs,
					  bits_per_sample,
					  samples);
    } else if (fixed_subframe->bits_written <= lpc_subframe->bits_written) {
      /* otherwise perform actual writing on the smaller of the two*/
      FlacEncoder_write_fixed_subframe(bs,
				       &fixed_warm_up_samples,
				       &fixed_rice_parameters,
				       &fixed_residual,
				       bits_per_sample,
				       fixed_predictor_order);
    } else {
      FlacEncoder_write_lpc_subframe(bs,
				     &lpc_warm_up_samples,
				     &lpc_rice_parameters,
				     &lpc_residual,
				     bits_per_sample,
				     &lpc_coeffs,
				     lpc_shift_needed);
    }

    bs_close(lpc_subframe);

    ia_free(&lpc_rice_parameters);
    ia_free(&lpc_residual);
    ia_free(&lpc_warm_up_samples);
    ia_free(&lpc_coeffs);
  } else {
    /*if no LPC subframe, perform actual writing on the FIXED subframe
      so long as it's smaller than VERBATIM*/
    if (((bits_per_sample * samples->size) < fixed_subframe->bits_written) &&
	(!options->no_verbatim_subframes)) {
      FlacEncoder_write_verbatim_subframe(bs,
					  bits_per_sample,
					  samples);
    } else {
      /*if no FIXED subframe *and* no LPC subframe,
	give up and write a FIXED subframe anyway*/
      if (fixed_predictor_order < 0) {
	fixed_predictor_order = FlacEncoder_compute_best_fixed_predictor_order(samples);

	FlacEncoder_evaluate_fixed_subframe(&fixed_warm_up_samples,
					    &fixed_residual,
					    &fixed_rice_parameters,
					    options,
					    bits_per_sample,
					    samples,
					    fixed_predictor_order);
      }

      FlacEncoder_write_fixed_subframe(bs,
				       &fixed_warm_up_samples,
				       &fixed_rice_parameters,
				       &fixed_residual,
				       bits_per_sample,
				       fixed_predictor_order);
    }
  }

  bs_close(fixed_subframe);
  ia_free(&fixed_warm_up_samples);
  ia_free(&fixed_residual);
  ia_free(&fixed_rice_parameters);
}

void FlacEncoder_write_constant_subframe(Bitstream *bs,
					 int bits_per_sample,
					 ia_data_t sample) {
  /*write subframe header*/
  bs->write_bits(bs, 1, 0);
  bs->write_bits(bs, 6, 0);
  bs->write_bits(bs, 1, 0);

  /*write subframe sample*/
  bs->write_signed_bits(bs, bits_per_sample, sample);
}

void FlacEncoder_write_verbatim_subframe(Bitstream *bs,
					 int bits_per_sample,
					 struct i_array *samples) {
  ia_size_t i;

  /*write subframe header*/
  bs->write_bits(bs, 1, 0);
  bs->write_bits(bs, 6, 1);
  bs->write_bits(bs, 1, 0);

  /*write subframe samples*/
  for (i = 0; i < samples->size; i++) {
    bs->write_signed_bits(bs, bits_per_sample, ia_getitem(samples,i));
  }
}

void FlacEncoder_evaluate_fixed_subframe(struct i_array *warm_up_samples,
					 struct i_array *residuals,
					 struct i_array *rice_parameters,

					 struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 int predictor_order) {
  ia_data_t *samples_data = samples->data;
  ia_size_t i;

  /*write warm-up samples*/
  for (i = 0; i < predictor_order; i++)
    ia_append(warm_up_samples,samples_data[i]);

  /*calculate residual values based on predictor order*/
  switch (predictor_order) {
  case 0:
    for (i = 0; i < samples->size; i++)
      ia_append(residuals,samples_data[i]);
    break;
  case 1:
    for (i = 1; i < samples->size; i++)
      ia_append(residuals,samples_data[i] - samples_data[i - 1]);
    break;
  case 2:
    for (i = 2; i < samples->size; i++)
      ia_append(residuals,samples_data[i] -
		((2 * samples_data[i - 1]) - samples_data[i - 2]));
    break;
  case 3:
    for (i = 3; i < samples->size; i++)
      ia_append(residuals,samples_data[i] -
		((3 * samples_data[i - 1]) -
		 (3 * samples_data[i - 2]) +
		 samples_data[i - 3]));
    break;
  case 4:
    for (i = 4; i < samples->size; i++)
      ia_append(residuals,samples_data[i] -
		((4 * samples_data[i - 1]) -
		 (6 * samples_data[i - 2]) +
		 (4 * samples_data[i - 3]) -
		 samples_data[i - 4]));
    break;
  default:
    fprintf(stderr,"Invalid FIXED predictor order %d\n",predictor_order);
    exit(1);
  }

  /*write residuals*/
  FlacEncoder_evaluate_best_residual(rice_parameters, options, predictor_order,
				     residuals);
}

void FlacEncoder_write_fixed_subframe(Bitstream *bs,
				      struct i_array *warm_up_samples,
				      struct i_array *rice_parameters,
				      struct i_array *residuals,
				      int bits_per_sample,
				      int predictor_order) {
  ia_size_t i;

  /*write subframe header*/
  bs->write_bits(bs, 1, 0);
  bs->write_bits(bs, 6, 0x8 | predictor_order);
  bs->write_bits(bs, 1, 0); /*FIXME - handle wasted bits-per-sample*/

  /*write warm-up samples*/
  for (i = 0; i < predictor_order; i++)
    bs->write_signed_bits(bs, bits_per_sample, ia_getitem(warm_up_samples,i));

  /*write residual*/
  FlacEncoder_write_residual(bs, predictor_order, rice_parameters,
			     residuals);
}

void FlacEncoder_evaluate_lpc_subframe(struct i_array *warm_up_samples,
				       struct i_array *residual,
				       struct i_array *rice_parameters,
				       struct flac_encoding_options *options,
				       int bits_per_sample,
				       struct i_array *samples,
				       struct i_array *coeffs,
				       int shift_needed) {
  int predictor_order = coeffs->size;
  int64_t accumulator;
  int i,j;

  ia_size_t samples_size;
  ia_data_t *samples_data;
  ia_data_t *coeffs_data;

  /*write warm-up samples*/
  for (i = 0; i < predictor_order; i++) {
    ia_append(warm_up_samples,ia_getitem(samples,i));
  }

  /*calculate residual values*/
  samples_size = samples->size;
  samples_data = samples->data;
  coeffs_data = coeffs->data;

  for (i = predictor_order; i < samples_size; i++) {
    accumulator = 0;
    for (j = 0; j < predictor_order; j++) {
      accumulator += (int64_t)samples_data[i - j - 1] * (int64_t)coeffs_data[j];
    }
    ia_append(residual,
	      samples_data[i] - (ia_data_t)(accumulator >> shift_needed));
  }

  /*write residual*/
  FlacEncoder_evaluate_best_residual(rice_parameters, options, predictor_order,
				     residual);
}

void FlacEncoder_write_lpc_subframe(Bitstream *bs,
				    struct i_array *warm_up_samples,
				    struct i_array *rice_parameters,
				    struct i_array *residuals,
				    int bits_per_sample,
				    struct i_array *coeffs,
				    int shift_needed) {
  int predictor_order = coeffs->size;
  int qlp_precision = ia_reduce(coeffs,2,maximum_bits_size);
  ia_size_t i;

  /*write subframe header*/
  bs->write_bits(bs,1,0);
  bs->write_bits(bs,6,0x20 | (predictor_order - 1));
  bs->write_bits(bs,1,0);  /*FIXME - handle wasted bits-per-sample*/

  /*write warm-up samples*/
  for (i = 0; i < predictor_order; i++) {
    bs->write_signed_bits(bs,bits_per_sample,ia_getitem(warm_up_samples,i));
  }

  /*write QLP Precision*/
  bs->write_bits(bs,4,qlp_precision - 1);

  /*write QLP Shift Needed*/
  bs->write_signed_bits(bs,5,shift_needed);

  /*write QLP Coefficients*/
  for (i = 0; i < predictor_order; i++) {
    bs->write_signed_bits(bs,qlp_precision,ia_getitem(coeffs,i));
  }

  /*write residual*/
  FlacEncoder_write_residual(bs, predictor_order, rice_parameters,
			     residuals);
}

int FlacEncoder_estimate_residual_partition_size(int rice_parameter,
						 struct i_array *residuals,
						 uint64_t abs_residual_partition_sum) {
  if (rice_parameter != 0)
    return 4 + (1 + rice_parameter) * residuals->size +
      (int)(abs_residual_partition_sum >> (rice_parameter - 1)) -
      (int)(residuals->size >> 1);
  else
    return 4 + (1 + rice_parameter) * residuals->size +
      (int)(abs_residual_partition_sum << 1) -
      (int)(residuals->size >> 1);
}

void FlacEncoder_evaluate_best_residual(struct i_array *rice_parameters,
					struct flac_encoding_options *options,
					int predictor_order,
					struct i_array *residuals) {
  struct i_array working_rice_parameters;
  int block_size;
  int min_partition_order;
  int max_partition_order;
  int partition_order;


  struct i_array current_best_rice_parameters;
  int current_best_bits;
  int estimated_residual_bits;


  struct i_array remaining_residuals;
  struct i_array partition_residuals;
  uint64_t abs_residual_partition_sum;
  uint32_t partitions;
  uint32_t partition;

  /*keep dividing block_size by 2 until its no longer divisible by 2
    to determine the maximum partition order
    since there are 2 ^ partition_order number of partitions
    and the residuals must be evenly distributed between them*/
  for (block_size = predictor_order + residuals->size,max_partition_order = 0;
       (block_size > 1) && ((block_size % 2) == 0);
       max_partition_order++)
    block_size /= 2;

  /*although if the user-specified max_partition_order is smaller,
    use that instead*/
  max_partition_order = MIN(options->max_residual_partition_order,
			    max_partition_order);

  min_partition_order = MIN(options->min_residual_partition_order,
			    max_partition_order);

  block_size = predictor_order + residuals->size;

  /*initialize working space to try different residual sizes*/
  ia_init(&current_best_rice_parameters,0);
  current_best_bits = INT_MAX;
  ia_init(&working_rice_parameters,1 << max_partition_order);

  /*for each partition_order possibility*/
  for (partition_order = min_partition_order;
       partition_order <= max_partition_order;
       partition_order++) {
    ia_reset(&working_rice_parameters);
    estimated_residual_bits = 6; /*6 bits for coding method
				   and partition_order headers*/

    /*chop the residuals into 2 ^ partition_order number of partitions*/
    ia_link(&remaining_residuals,residuals);
    partitions = 1 << partition_order;
    for (partition = 0; partition < partitions; partition++) {
      if (partition == 0) {
	/*first partition contains (block_size / 2 ^ partition_order) - order
	  number of residuals*/

	ia_split(&partition_residuals,
		 &remaining_residuals,
		 &remaining_residuals,
		 (block_size / (1 << partition_order)) - predictor_order);
      } else {
	/*subsequent partitions contain (block_size / 2 ^ partition_order)
	  number of residuals*/

	ia_split(&partition_residuals,
		 &remaining_residuals,
		 &remaining_residuals,
		 block_size / (1 << partition_order));
      }

      abs_residual_partition_sum = abs_sum(&partition_residuals);

      /*for each partition, determine the Rice parameter*/
      /*and append that parameter to the parameter list*/
      ia_append(&working_rice_parameters,
		MIN(FlacEncoder_compute_best_rice_parameter(&partition_residuals,
							    abs_residual_partition_sum),
		    options->max_rice_parameter));

      estimated_residual_bits += FlacEncoder_estimate_residual_partition_size(
          ia_getitem(&working_rice_parameters,-1),
	  &partition_residuals,
	  abs_residual_partition_sum);
    }

    /*and if potential_residual is better than current_best (or no current_best)
      swap current_best for potential_residual*/
    if (estimated_residual_bits < current_best_bits) {
      ia_copy(&current_best_rice_parameters,&working_rice_parameters);
      current_best_bits = estimated_residual_bits;
    }
  }

  /*finally, send the best possible set of parameters to "rice_parameters"*/
  ia_copy(rice_parameters,&current_best_rice_parameters);

  ia_free(&working_rice_parameters);
  ia_free(&current_best_rice_parameters);
}

int FlacEncoder_compute_best_rice_parameter(struct i_array *residuals,
					    uint64_t abs_residual_partition_sum) {
  int i;

  for (i = 0; ((uint64_t)residuals->size * (uint64_t)(1 << i)) < abs_residual_partition_sum; i++)
    /*do nothing*/;

  return i;
}


void FlacEncoder_write_residual(Bitstream *bs,
				int predictor_order,
				struct i_array *rice_parameters,
				struct i_array *residuals) {
  uint32_t partition_order;
  int32_t partitions;
  int32_t partition;
  int32_t block_size = predictor_order + residuals->size;
  struct i_array remaining_residuals;
  struct i_array partition_residuals;
  int coding_method;

  /*derive the coding method value*/
  if (ia_max(rice_parameters) <= 0xE)
    coding_method = 0;
  else
    coding_method = 1;

  /*derive the partition_order value*/
  for (partitions = rice_parameters->size, partition_order = 0;
       partitions > 1; partition_order++)
    partitions /= 2;
  partitions = rice_parameters->size;

  bs->write_bits(bs, 2, coding_method);
  bs->write_bits(bs, 4, partition_order);

  /*for each rice_parameter, write a residual partition*/
  ia_link(&remaining_residuals,residuals);

  for (partition = 0; partition < partitions; partition++) {
    if (partition == 0) {
      /*the first partition contains (block_size / 2 ^ partition_order) - order
	number of residuals*/
      ia_split(&partition_residuals,
	       &remaining_residuals,
	       &remaining_residuals,
	       (block_size / (1 << partition_order)) - predictor_order);
    } else {
      /*subsequence partitions contain (block_size / 2 ^ partition_order)
	number of residuals*/
      ia_split(&partition_residuals,
	       &remaining_residuals,
	       &remaining_residuals,
	       block_size / (1 << partition_order));
    }
    FlacEncoder_write_residual_partition(bs,
					 coding_method,
					 ia_getitem(rice_parameters,
						    partition),
					 &partition_residuals);
  }

}

void FlacEncoder_write_residual_partition(Bitstream *bs,
					  int coding_method,
					  int rice_parameter,
					  struct i_array *residuals) {
  ia_size_t i;
  register int64_t residual;
  register int32_t msb;
  register int32_t lsb;

  ia_size_t residuals_size;
  ia_data_t *residuals_data;
  void (*write_bits)(struct Bitstream_s* bs, unsigned int count, int value);
  void (*write_unary)(struct Bitstream_s* bs, int stop_bit, int value);

  write_bits = bs->write_bits;
  write_unary = bs->write_unary;
  residuals_size = residuals->size;
  residuals_data = residuals->data;

  /*write the 4-5 bit Rice parameter header (depending on coding method)*/
  write_bits(bs, coding_method == 0 ? 4 : 5, rice_parameter);

  /*for each residual, write a unary/unsigned bits pair
    whose breakpoint depends on "rice_parameter"*/
  for (i = 0; i < residuals_size; i++) {
    residual = (int64_t)residuals_data[i];
    if (residual >= 0) {
      residual <<= 1;
    } else {
      residual = ((-residual - 1) << 1) | 1;
    }
    msb = (int32_t)(residual >> rice_parameter);
    lsb = (int32_t)(residual - (msb << rice_parameter));
    write_unary(bs,1,msb);
    write_bits(bs,rice_parameter,lsb);
  }
}

int FlacEncoder_compute_best_fixed_predictor_order(struct i_array *samples) {
  struct i_array delta0;
  struct i_array delta1;
  struct i_array delta2;
  struct i_array delta3;
  struct i_array delta4;
  struct i_array subtract;

  uint64_t delta0_sum;
  uint64_t delta1_sum;
  uint64_t delta2_sum;
  uint64_t delta3_sum;
  uint64_t delta4_sum;

  ia_data_t *delta0_data;
  ia_data_t *delta1_data;
  ia_data_t *delta2_data;
  ia_data_t *delta3_data;
  ia_data_t *delta4_data;
  ia_size_t i;

  if (samples->size < 5)
    return 0;

  delta0.data = NULL; /*to elimate a "used without being defined" warning*/
  ia_tail(&delta0,samples,samples->size - 1);
  delta0_data = delta0.data;
  for (delta0_sum = 0,i = 3; i < delta0.size; i++)
    delta0_sum += abs(delta0_data[i]);

  ia_init(&delta1,samples->size);
  ia_tail(&subtract,&delta0,delta0.size - 1);
  ia_sub(&delta1,&delta0,&subtract);
  delta1_data = delta1.data;
  for (delta1_sum = 0,i = 2; i < delta1.size; i++)
    delta1_sum += abs(delta1_data[i]);

  ia_init(&delta2,samples->size);
  ia_tail(&subtract,&delta1,delta1.size - 1);
  ia_sub(&delta2,&delta1,&subtract);
  delta2_data = delta2.data;
  for (delta2_sum = 0,i = 2; i < delta2.size; i++)
    delta2_sum += abs(delta2_data[i]);

  ia_init(&delta3,samples->size);
  ia_tail(&subtract,&delta2,delta2.size - 1);
  ia_sub(&delta3,&delta2,&subtract);
  delta3_data = delta3.data;
  for (delta3_sum = 0,i = 1; i < delta3.size; i++)
    delta3_sum += abs(delta3_data[i]);

  ia_init(&delta4,samples->size);
  ia_tail(&subtract,&delta3,delta3.size - 1);
  ia_sub(&delta4,&delta3,&subtract);
  delta4_data = delta4.data;
  for (delta4_sum = 0,i = 0; i < delta4.size; i++)
    delta4_sum += abs(delta4_data[i]);

  ia_free(&delta1);
  ia_free(&delta2);
  ia_free(&delta3);
  ia_free(&delta4);

  if (delta0_sum < MIN(delta1_sum,MIN(delta2_sum,MIN(delta3_sum,delta4_sum))))
    return 0;
  else if (delta1_sum < MIN(delta2_sum,MIN(delta3_sum,delta4_sum)))
    return 1;
  else if (delta2_sum < MIN(delta3_sum,delta4_sum))
    return 2;
  else if (delta3_sum < delta4_sum)
    return 3;
  else
    return 4;
}

void write_utf8(Bitstream *stream, unsigned int value) {
  if ((value >= 0) && (value <= 0x7F)) {
    /*1 byte UTF-8 sequence*/
    stream->write_bits(stream,8,value);
  } else if ((value >= 0x80) && (value <= 0x7FF)) {
    /*2 byte UTF-8 sequence*/
    stream->write_unary(stream,0,2);
    stream->write_bits(stream,5,value >> 6);
    stream->write_unary(stream,0,1);
    stream->write_bits(stream,6,value & 0x3F);
  } else if ((value >= 0x800) && (value <= 0xFFFF)) {
    /*3 byte UTF-8 sequence*/
    stream->write_unary(stream,0,3);
    stream->write_bits(stream,4,value >> 12);
    stream->write_unary(stream,0,1);
    stream->write_bits(stream,6,(value >> 6) & 0x3F);
    stream->write_unary(stream,0,1);
    stream->write_bits(stream,6,value & 0x3F);
  } else if ((value >= 0x10000) && (value <= 0xFFFFF)) {
    /*4 byte UTF-8 sequence*/
    stream->write_unary(stream,0,4);
    stream->write_bits(stream,3,value >> 18);
    stream->write_unary(stream,0,1);
    stream->write_bits(stream,6,(value >> 12) & 0x3F);
    stream->write_unary(stream,0,1);
    stream->write_bits(stream,6,(value >> 6) & 0x3F);
    stream->write_unary(stream,0,1);
    stream->write_bits(stream,6,value & 0x3F);
  }
}

int FlacEncoder_qlp_coeff_precision(int block_size) {
  if (block_size <= 192)
    return 7;
  else if (block_size <= 384)
    return 8;
  else if (block_size <= 576)
    return 9;
  else if (block_size <= 1152)
    return 10;
  else if (block_size <= 2304)
    return 11;
  else if (block_size <= 4608)
    return 12;
  else
    return 13;
}

void FlacEncoder_build_mid_side_subframes(struct ia_array *samples,
					  struct i_array *mid_subframe,
					  struct i_array *side_subframe) {
  struct i_array *left = iaa_getitem(samples,0);
  struct i_array *right = iaa_getitem(samples,1);
  ia_data_t *left_data = left->data;
  ia_data_t *right_data = right->data;
  ia_data_t *mid_data;
  ia_data_t *side_data;
  ia_size_t sample_size = left->size;
  ia_size_t i;

  ia_resize(mid_subframe,sample_size);
  ia_resize(side_subframe,sample_size);
  mid_data = mid_subframe->data;
  side_data = side_subframe->data;
  mid_subframe->size = sample_size;
  side_subframe->size = sample_size;

  for (i = 0; i < sample_size; i++) {
    mid_data[i] = (left_data[i] + right_data[i]) >> 1;
    side_data[i] = left_data[i] - right_data[i];
  }
}

void FlacEncoder_build_left_side_subframes(struct ia_array *samples,
					   struct i_array *left_side) {
  ia_sub(left_side,
	 iaa_getitem(samples,0),iaa_getitem(samples,1));
}

void FlacEncoder_build_side_right_subframes(struct ia_array *samples,
					    struct i_array *side_right) {
  ia_sub(side_right,
	 iaa_getitem(samples,0),iaa_getitem(samples,1));
}

void md5_update(void *data, unsigned char *buffer, unsigned long len) {
  MD5_Update((MD5_CTX*)data, (const void*)buffer, len);
}

int maximum_bits_size(int value, int current_maximum) {
  int bits = 1;
  if (value < 0) {
    value = -value;
  }
  for (;value > 0; value >>= 1)
    bits++;

  if (bits > current_maximum)
    return bits;
  else
    return current_maximum;
}

#include "flac_crc.c"

#ifdef STANDALONE

int main(int argc, char *argv[]) {
  encoders_encode_flac(argv[1],
		       stdin,
		       4096,12,0,6,1,1,1);

  return 0;
}
#endif
