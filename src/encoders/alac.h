#ifndef A_SHN_ENCODE
#define A_SHN_ENCODE
#ifndef STANDALONE
#include <Python.h>
#endif

#include <stdint.h>
#include "../bitstream_w.h"
#include "../array.h"
#include "../pcmreader.h"

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

typedef enum {OK, ERROR, RESIDUAL_OVERFLOW} status;

/*this output log is a set of things Python-based ALAC atom writers will need
  in order to populate metadata*/
struct alac_encode_log {
    int frame_byte_size;
    int mdat_byte_size;
    struct ia_array frame_log;
};

struct alac_encoding_options {
    int block_size;
    int initial_history;
    int history_multiplier;
    int maximum_k;
    int minimum_interlacing_leftweight;
    int maximum_interlacing_leftweight;
    int minimum_interlacing_shift;
    int maximum_interlacing_shift;
    int channel_mask;

    /*a couple of temporary buffers
      so we don't have to allocate them all the time*/
    Bitstream *best_frame;
    Bitstream *current_frame;
};

enum {LOG_SAMPLE_SIZE, LOG_BYTE_SIZE, LOG_FILE_OFFSET};

void
alac_log_init(struct alac_encode_log *log);

void
alac_log_free(struct alac_encode_log *log);

#ifndef STANDALONE
PyObject
*alac_log_output(struct alac_encode_log *log);
#endif

void
alac_byte_counter(uint8_t byte, void* counter);

/*writes a full set of ALAC frames,
  complete with trailing stop '111' bits and byte-aligned*/
status
alac_write_frameset(Bitstream *bs,
                    struct alac_encode_log *log,
                    long starting_offset,
                    struct alac_encoding_options *options,
                    int bits_per_sample,
                    struct ia_array *samples);

/*write a single ALAC frame, compressed or uncompressed as necessary*/
status
alac_write_frame(Bitstream *bs,
                 struct alac_encoding_options *options,
                 int bits_per_sample,
                 struct ia_array *samples);

status
alac_write_uncompressed_frame(Bitstream *bs,
                              int block_size,
                              int bits_per_sample,
                              struct ia_array *samples);

status
alac_write_compressed_frame(Bitstream *bs,
                            struct alac_encoding_options *options,
                            int bits_per_sample,
                            struct ia_array *samples);

status
alac_write_interlaced_frame(Bitstream *bs,
                            struct alac_encoding_options *options,
                            int interlacing_shift,
                            int interlacing_leftweight,
                            int bits_per_sample,
                            struct ia_array *samples);

status
alac_correlate_channels(struct ia_array *output,
                        struct ia_array *input,
                        int interlacing_shift,
                        int interlacing_leftweight);

status
alac_encode_subframe(struct i_array *residuals,
                     struct i_array *samples,
                     struct i_array *coefficients,
                     int predictor_quantitization);

/*writes a single unsigned residal to the current bitstream*/
void
alac_write_residual(Bitstream *bs,
                    int residual,
                    int k,
                    int bits_per_sample);

status
alac_write_residuals(Bitstream *bs,
                     struct i_array *residuals,
                     int bits_per_sample,
                     struct alac_encoding_options *options);

void
alac_error(const char* message);

void
alac_warning(const char* message);

#endif
