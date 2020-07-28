#ifndef STANDALONE
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#endif
#include "../bitstream.h"
#include "../pcmreader.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

typedef enum {
    FLAC_OK,           /*everything ok*/
    FLAC_READ_ERROR,   /*read error from PCMReader*/
    FLAC_PCM_MISMATCH, /*total PCM frames mismatch*/
    FLAC_NO_TEMPFILE   /*unable to open temporary file*/
} flacenc_status_t;

struct flac_encoding_options {
    unsigned block_size;                    /*typically 1152 or 4096*/
    unsigned min_residual_partition_order;  /*typically 0*/
    unsigned max_residual_partition_order;  /*typically 3-6*/
    unsigned max_lpc_order;                 /*typically 0,6,8,12*/
    int exhaustive_model_search;            /*a boolean*/
    int mid_side;                           /*a boolean*/
    int adaptive_mid_side;                  /*a boolean*/

    int use_verbatim;                       /*a boolean for debugging*/
    int use_constant;                       /*a boolean for debugging*/
    int use_fixed;                          /*a boolean for debugging*/

    unsigned qlp_coeff_precision;           /*derived from block size*/
    unsigned max_rice_parameter;            /*derived from bits-per-sample*/
    double *window;                         /*for windowing input samples*/
};

/*sets the encoding options to sensible defaults*/
void
flacenc_init_options(struct flac_encoding_options *options);

/*displays the encoding options for debugging purposes*/
void
flacenc_display_options(const struct flac_encoding_options *options,
                        FILE *output);


/*encodes a FLAC file using data from the given PCMReader
  to the given output stream
  using the given options*/
flacenc_status_t
flacenc_encode_flac(struct PCMReader *pcmreader,
                    BitstreamWriter *output,
                    struct flac_encoding_options *options,
                    uint64_t total_pcm_frames,
                    const char version[],
                    unsigned padding_size);

#ifndef STANDALONE
PyObject*
encoders_encode_flac(PyObject *dummy, PyObject *args, PyObject *keywds);
#endif
