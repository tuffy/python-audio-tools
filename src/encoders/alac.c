#include "alac.h"
#include "alac_lpc.h"

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

PyObject* encoders_encode_alac(PyObject *dummy,
			       PyObject *args, PyObject *keywds) {

  static char *kwlist[] = {"file",
			   "pcmreader",
			   "block_size",
			   "initial_history",
			   "history_multiplier",
			   "maximum_k",
			   NULL};

  PyObject *file_obj;       /*the Python object of our output file*/
  FILE *output_file;        /*the FILE representation of our putput file*/
  Bitstream *stream = NULL; /*the Bitstream representation of our output file*/
  PyObject *pcmreader_obj;  /*the Python object of our input pcmreader*/
  struct pcm_reader *reader; /*the pcm_reader struct of our input pcmreader*/
  struct ia_array samples;  /*a buffer of input samples*/

  struct alac_encoding_options options;

  struct alac_encode_log encode_log; /*a log of encoded output*/
  PyObject *encode_log_obj;          /*the Python object of encoded output*/

  fpos_t starting_point;

  /*extract a file object, PCMReader-compatible object and encoding options*/
  if (!PyArg_ParseTupleAndKeywords(args,keywds,"OOiiii",
				   kwlist,
				   &file_obj,
				   &pcmreader_obj,
				   &(options.block_size),
				   &(options.initial_history),
				   &(options.history_multiplier),
				   &(options.maximum_k)))
    return NULL;

  /*check for negative block_size*/
  if (options.block_size <= 0) {
    PyErr_SetString(PyExc_ValueError,"block_size must be positive");
    return NULL;
  }

  /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
  if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
    return NULL;
  }

  /*initialize a buffer for input samples*/
  iaa_init(&samples,reader->channels,options.block_size);

  /*initialize the output log*/
  alac_log_init(&encode_log);

  /*determine if the PCMReader is compatible with ALAC*/
  if ((reader->bits_per_sample != 16) &&
      (reader->bits_per_sample != 24)) {
    PyErr_SetString(PyExc_ValueError,"bits per sample must be 16 or 24");
    goto error;
  }
  if (reader->channels > 2) {
    PyErr_SetString(PyExc_ValueError,"channels must be 1 or 2");
    goto error;
  }

  /*convert file object to bitstream writer*/
  if ((output_file = PyFile_AsFile(file_obj)) == NULL) {
    PyErr_SetString(PyExc_TypeError,"file must by a concrete file object");
    goto error;
  } else {
    stream = bs_open(output_file);
    bs_add_callback(stream,
		    ALACEncoder_byte_counter,
		    &(encode_log.frame_byte_size));
  }

  /*write "mdat" atom header*/
  if (fgetpos(output_file, &starting_point) != 0) {
    PyErr_SetFromErrno(PyExc_IOError);
    goto error;
  }
  stream->write_bits(stream,32,encode_log.mdat_byte_size);
  stream->write_bits(stream,32,0x6D646174);  /*"mdat" type*/

  /*write frames from pcm_reader until empty*/
  if (!pcmr_read(reader,options.block_size,&samples))
    goto error;
  while (iaa_getitem(&samples,0)->size > 0) {
    if (ALACEncoder_write_frame(stream,
				&encode_log,
				ftell(output_file),
				&options,
				reader->bits_per_sample,
				&samples) == ERROR)
      goto error;

    if (!pcmr_read(reader,options.block_size,&samples))
      goto error;
  }

  /*rewind stream and rewrite "mdat" atom header*/
  if (fsetpos(output_file, &starting_point) != 0) {
    PyErr_SetFromErrno(PyExc_IOError);
    goto error;
  }
  stream->write_bits(stream,32,encode_log.mdat_byte_size);

  /*close and free allocated files/buffers*/
  pcmr_close(reader);
  bs_free(stream);
  iaa_free(&samples);

  /*return the accumulated log of output*/
  encode_log_obj = alac_log_output(&encode_log);
  alac_log_free(&encode_log);
  return encode_log_obj;

 error:
  pcmr_close(reader);
  bs_free(stream);
  iaa_free(&samples);
  alac_log_free(&encode_log);
  return NULL;
}

status ALACEncoder_write_frame(Bitstream *bs,
			       struct alac_encode_log *log,
			       long starting_offset,
			       struct alac_encoding_options *options,
			       int bits_per_sample,
			       struct ia_array *samples) {
  log->frame_byte_size = 0;

  /*write uncompressed frame*/
  if (ALACEncoder_write_uncompressed_frame(bs,
					   options->block_size,
					   bits_per_sample,
					   samples) == ERROR)
    return ERROR;

  /*update log*/
  log->mdat_byte_size += log->frame_byte_size;
  ia_append(iaa_getitem(&(log->frame_log),LOG_SAMPLE_SIZE),
	    samples->arrays[0].size);
  ia_append(iaa_getitem(&(log->frame_log),LOG_BYTE_SIZE),
	    log->frame_byte_size);
  ia_append(iaa_getitem(&(log->frame_log),LOG_FILE_OFFSET),
	    starting_offset);

  return OK;
}

status ALACEncoder_write_uncompressed_frame(Bitstream *bs,
					    int block_size,
					    int bits_per_sample,
					    struct ia_array *samples) {
  int channels = samples->size;
  int pcm_frames = samples->arrays[0].size;
  int has_sample_size = (pcm_frames != block_size);
  int i,j;

  /*write frame header*/
  bs->write_bits(bs,3,channels - 1); /*channel count, offset 1*/
  bs->write_bits(bs,16,0);           /*unknown, all 0*/
  if (has_sample_size)               /*"has sample size"" flag*/
    bs->write_bits(bs,1,1);
  else
    bs->write_bits(bs,1,0);
  bs->write_bits(bs,2,0);  /*uncompressed frames never have wasted bits*/
  bs->write_bits(bs,1,1);  /*the "is not compressed flag" flag*/
  if (has_sample_size)
    bs->write_bits(bs,32,pcm_frames);

  /*write individual samples*/
  for (i = 0; i < pcm_frames; i++)
    for (j = 0; j < channels; j++)
      bs->write_signed_bits(bs,
			    bits_per_sample,
			    samples->arrays[j].data[i]);

  /*write footer and padding*/
  bs->write_bits(bs,3,0x7);
  bs->byte_align(bs);

  return OK;
}

status ALACEncoder_write_compressed_frame(Bitstream *bs,
					  struct alac_encoding_options *options,
					  int bits_per_sample,
					  struct ia_array *samples) {
  int channels = samples->size;
  int pcm_frames = samples->arrays[0].size;
  int has_sample_size = (pcm_frames != options->block_size);
  int has_wasted_bits = (bits_per_sample > 16);
  struct i_array wasted_bits;
  int interlacing_shift;
  int interlacing_leftweight;
  struct ia_array correlated_samples;
  struct ia_array lpc_coefficients;
  struct i_array *coefficients;
  int *shift_needed = NULL;
  struct ia_array residuals;

  int i,j;

  /*write frame header*/
  bs->write_bits(bs,3,channels - 1); /*channel count, offset 1*/
  bs->write_bits(bs,16,0);           /*unknown, all 0*/
  if (has_sample_size)               /*"has sample size"" flag*/
    bs->write_bits(bs,1,1);
  else
    bs->write_bits(bs,1,0);

  if (has_wasted_bits)               /*"has wasted bits" value*/
    bs->write_bits(bs,2,1);
  else
    bs->write_bits(bs,2,0);

  bs->write_bits(bs,1,0);  /*the "is not compressed flag" flag*/
  if (has_sample_size)
    bs->write_bits(bs,32,pcm_frames);

  /*if we have wasted bits, extract them from the front of each sample
    we'll only support 8 wasted bits, for 24bps input*/
  if (has_wasted_bits) {
    ia_init(&wasted_bits,channels * pcm_frames);
    for (i = 0; i < pcm_frames; i++)
      for (j = 0; j < channels; j++) {
	ia_append(&wasted_bits,samples->arrays[j].data[i] & 0xFF);
	samples->arrays[j].data[i] >>= 8;
      }
  }

  iaa_init(&correlated_samples,channels,pcm_frames);
  iaa_init(&residuals,channels,pcm_frames);

  /*if stereo, determine "interlacing shift" and "interlacing leftweight"*/
  /*FIXME - ultimately, these will be determined exhaustively
    for now, store channels independently*/
  interlacing_shift = 0;
  interlacing_leftweight = 0;

  /*apply channel correlation to samples*/
  ALACEncoder_correlate_channels(&correlated_samples,
				 samples,
				 interlacing_shift,
				 interlacing_leftweight);

  /*calculate the best "prediction quantitization" and "coefficient" values
    for each channel of audio*/
  /*FIXME - for now, let's use a set of dummy coefficients*/
  iaa_init(&lpc_coefficients,channels,MAX_LPC_ORDER);
  shift_needed = malloc(sizeof(int) * channels);
  for (i = 0; i < channels; i++) {
    ia_append(iaa_getitem(&lpc_coefficients,i),160);
    ia_append(iaa_getitem(&lpc_coefficients,i),-190);
    ia_append(iaa_getitem(&lpc_coefficients,i),170);
    ia_append(iaa_getitem(&lpc_coefficients,i),-130);
    shift_needed[i] = 6;
  }

  /*write 1 subframe header per channel*/
  for (i = 0; i < channels; i++) {
    bs->write_bits(bs,4,0);                /*prediction type of 0*/
    bs->write_bits(bs,4,shift_needed[i]);  /*prediction quantitization*/
    bs->write_bits(bs,3,4);                /*Rice modifier of 4 seems typical*/
    coefficients = iaa_getitem(&lpc_coefficients,i);
    bs->write_bits(bs,5,coefficients->size);
    for (j = 0; j < coefficients->size; j++)
      bs->write_signed_bits(bs,16,coefficients->data[j]);
  }

  /*write wasted bits block, if any*/
  if (has_wasted_bits) {
    for (i = 0; i < wasted_bits.size; i++)
      bs->write_bits(bs,8,wasted_bits.data[i]);
  }

  /*calculate residuals for each channel
    based on "coefficients", "quantitization", and "samples"*/
  for (i = 0; i < channels; i++)
    if (ALACEncoder_encode_subframe(&(residuals.arrays[i]),
				    &(correlated_samples.arrays[i]),
				    &(lpc_coefficients.arrays[i]),
				    shift_needed[i]) == ERROR)
      goto error;

  /*write 1 residual block per channel*/
  for (i = 0; i < channels; i++)
    if (ALACEncoder_write_residuals(bs,
				    &(residuals.arrays[i]),
				    bits_per_sample - (has_wasted_bits * 8) + channels - 1,
				    options) == ERROR)
      goto error;

  /*write frame footer and byte-align output*/
  bs->write_bits(bs,3,0x7);
  bs->byte_align(bs);

  /*clear any temporary buffers*/
  if (has_wasted_bits)
    ia_free(&wasted_bits);
  iaa_free(&correlated_samples);
  iaa_free(&lpc_coefficients);
  if (shift_needed != NULL)
    free(shift_needed);
  iaa_free(&residuals);

  return OK;

 error:
  if (has_wasted_bits)
    ia_free(&wasted_bits);
  iaa_free(&correlated_samples);
  iaa_free(&lpc_coefficients);
  if (shift_needed != NULL)
    free(shift_needed);
  iaa_free(&residuals);

  return ERROR;
}

status ALACEncoder_correlate_channels(struct ia_array *output,
				      struct ia_array *input,
				      int interlacing_shift,
				      int interlacing_leftweight) {
  struct i_array *left_channel;
  struct i_array *right_channel;
  struct i_array *channel1;
  struct i_array *channel2;
  ia_data_t left;
  ia_data_t right;
  ia_size_t pcm_frames,i;

  if (input->size != 2) {
    for (i = 0; i < input->size; i++) {
      ia_copy(iaa_getitem(output,i),iaa_getitem(input,i));
    }
  } else {
    left_channel = iaa_getitem(input,0);
    right_channel = iaa_getitem(input,1);
    channel1 = iaa_getitem(output,0);
    ia_reset(channel1);
    channel2 = iaa_getitem(output,1);
    ia_reset(channel2);
    pcm_frames = left_channel->size;

    if (interlacing_leftweight == 0) {
      ia_copy(channel1,left_channel);
      ia_copy(channel2,right_channel);
    } else {
      for (i = 0; i < pcm_frames; i++) {
	left = left_channel->data[i];
	right = right_channel->data[i];
	ia_append(channel1,right +
		  (((left - right) * interlacing_leftweight) >> interlacing_shift));
	ia_append(channel2,left - right);
      }
    }
  }

  return OK;
}

static inline int SIGN_ONLY(int value) {
  if (value > 0)
    return 1;
  else if (value < 0)
    return -1;
  else
    return 0;
}

status ALACEncoder_encode_subframe(struct i_array *residuals,
				   struct i_array *samples,
				   struct i_array *coefficients,
				   int predictor_quantitization) {
  struct i_array remaining_samples;
  int64_t lpc_sum;
  ia_data_t buffer0;
  ia_data_t sample;
  ia_data_t residual;
  int32_t val;
  int sign;
  int i,j;

  if (coefficients->size < 1) {
    PyErr_SetString(PyExc_ValueError,"coefficient count must be greater than 0");
    return ERROR;
  } else if ((coefficients->size != 4) && (coefficients->size != 8)) {
    PyErr_WarnEx(PyExc_RuntimeWarning,"coefficient size not 4 or 8",1);
  }

  ia_reset(residuals);
  ia_link(&remaining_samples,samples);

  /*first sample always copied verbatim*/
  ia_append(residuals,ia_pop_head(&remaining_samples));

  /*grab a number of warm-up samples equal to coefficients' length*/
  for (i = 0; i < coefficients->size; i++)
    /*these are adjustments to the previous residual*/
    ia_append(residuals,
	      ia_pop_head(&remaining_samples) - ia_getitem(samples,i));

  /*then calculate a new residual per remaining sample*/
  for (i = coefficients->size + 1; remaining_samples.size > 0; i++) {
    /*Note that buffer0 gets stripped from previously encoded samples
      then re-added prior to adding the next sample.
      It's a watermark sample, of sorts.*/
    buffer0 = samples->data[i - (coefficients->size + 1)];

    sample = ia_pop_head(&remaining_samples);
    lpc_sum = 0;

    for (j = 0; j < coefficients->size; j++) {
      lpc_sum += (int64_t)((int64_t)coefficients->data[j] *
			   (int64_t)(samples->data[i - j - 1] - buffer0));
    }

    /*residual = sample - (((sum + 2 ^ (quant - 1)) / (2 ^ quant)) + buffer0)*/
    residual = (int32_t)(sample - ((((int64_t)(1 << (predictor_quantitization - 1)) + lpc_sum) >> (int64_t)predictor_quantitization) + buffer0));

    ia_append(residuals,residual);

    /*ALAC's adaptive algorithm then adjusts the coefficients
      up or down 1 step based on previously encoded samples
      and the residual*/
    if (residual > 0) {
      for (j = 0; (residual > 0) && (j < coefficients->size); j++) {
  	val = buffer0 - samples->data[i - coefficients->size + j];
  	sign = SIGN_ONLY(val);
  	coefficients->data[j] -= sign;
  	val *= sign;
  	residual -= (val >> predictor_quantitization) * (j + 1);
      }
    } else if (residual < 0) {
      for (j = 0; (residual < 0) && (j < coefficients->size); j++) {
	val = buffer0 - samples->data[i - coefficients->size + j];
  	sign = -SIGN_ONLY(val);
  	coefficients->data[coefficients->size - j - 1] -= sign;
  	val *= sign;
  	residual -= (val >> predictor_quantitization) * (j + 1);
      }
    }
  }

  return OK;
}

void ALACEncoder_write_residual(Bitstream *bs,
				int residual,
				int k,
				int bits_per_sample) {
  int q = residual / ((1 << k) - 1);
  int e = residual % ((1 << k) - 1);
  if (q > 8) {
    bs->write_unary(bs,0,9);
    bs->write_bits(bs,bits_per_sample,residual);
  } else {
    if (q > 0)
      bs->write_unary(bs,0,q);
    else
      bs->write_bits(bs,1,0);
    if (e > 0)
      bs->write_bits(bs,k,e + 1);
    else
      bs->write_bits(bs,k - 1,0);
  }
}

static inline int LOG2(int value) {
  int bits = -1;
  while (value) {
    bits++;
    value >>= 1;
  }
  return bits;
}

status ALACEncoder_write_residuals(Bitstream *bs,
				   struct i_array *residuals,
				   int bits_per_sample,
				   struct alac_encoding_options *options) {
  int history = options->initial_history;
  int history_multiplier = options->history_multiplier;
  int maximum_k = options->maximum_k;
  int sign_modifier = 0;
  int i;
  int k;
  ia_data_t signed_residual;
  ia_data_t unsigned_residual;
  int zero_block_size;

  for (i = 0; i < residuals->size;) {
    k = MIN(LOG2((history >> 9) + 3),maximum_k);
    signed_residual = residuals->data[i];
    if (signed_residual >= 0)
      unsigned_residual = (signed_residual * 2) - sign_modifier;
    else
      unsigned_residual = ((-signed_residual * 2) - 1) - sign_modifier;

    ALACEncoder_write_residual(bs,unsigned_residual,k,bits_per_sample);

    if (unsigned_residual <= 0xFFFF)
      history += ((unsigned_residual * history_multiplier) -
		  ((history * history_multiplier) >> 9));
    else
      history = 0xFFFF;
    sign_modifier = 0;
    i++;

    /*the special case for handling blocks of 0 residuals*/
    if ((history < 128) && (i < residuals->size)) {
      zero_block_size = 0;
      k = 7 - LOG2(history) + ((history + 16) >> 6);
      while (((signed_residual = residuals->data[i]) == 0) &&
	     (i < residuals->size)) {
	zero_block_size++;
	i++;
      }
      ALACEncoder_write_residual(bs,zero_block_size,k,16);
      if (zero_block_size <= 0xFFFF)
	sign_modifier = 1;
      history = 0;
    }

  }

  return OK;
}

void ALACEncoder_byte_counter(unsigned int byte, void* counter) {
  int* i_counter = (int*)counter;
  *i_counter += 1;
}

void alac_log_init(struct alac_encode_log *log) {
  log->frame_byte_size = 0;
  log->mdat_byte_size = 8;
  iaa_init(&(log->frame_log),3,1024);
}
void alac_log_free(struct alac_encode_log *log) {
  iaa_free(&(log->frame_log));
}
PyObject *alac_log_output(struct alac_encode_log *log) {
  PyObject *log_sample_size;
  PyObject *log_byte_size;
  PyObject *log_file_offset;
  struct i_array *log_array;
  int i;

  if ((log_sample_size = PyList_New(0)) == NULL)
    return NULL;
  if ((log_byte_size = PyList_New(0)) == NULL)
    return NULL;
  if ((log_file_offset = PyList_New(0)) == NULL)
    return NULL;

  log_array = iaa_getitem(&(log->frame_log),LOG_SAMPLE_SIZE);
  for (i = 0; i < log_array->size; i++)
    if (PyList_Append(log_sample_size,
		      PyInt_FromLong(log_array->data[i])) == -1)
      return NULL;

  log_array = iaa_getitem(&(log->frame_log),LOG_BYTE_SIZE);
  for (i = 0; i < log_array->size; i++)
    if (PyList_Append(log_byte_size,
		      PyInt_FromLong(log_array->data[i])) == -1)
      return NULL;

  log_array = iaa_getitem(&(log->frame_log),LOG_FILE_OFFSET);
  for (i = 0; i < log_array->size; i++)
    if (PyList_Append(log_file_offset,
		      PyInt_FromLong(log_array->data[i])) == -1)
      return NULL;

  return Py_BuildValue("(O,O,O,i)",
		       log_sample_size,
		       log_byte_size,
		       log_file_offset,
		       log->mdat_byte_size);
}
