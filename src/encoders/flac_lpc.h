#ifndef A_FLAC_ENCODER_LPC
#define A_FLAC_ENCODER_LPC

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

#include "flac.h"

/*given a set of samples, bits_per_sample and encoding options,
  returns a set of LPC warm up samples, rice_parameters, residual,
  LPC coefficients and shift_needed values*/
void FlacEncoder_compute_best_lpc_coeffs(struct i_array *lpc_warm_up_samples,
					 struct i_array *lpc_residual,
					 struct i_array *lpc_rice_parameters,
					 struct i_array *coeffs,
					 int *shift_needed,

					 struct flac_encoding_options *options,
					 int bits_per_sample,
					 int wasted_bits_per_sample,
					 struct i_array *samples);

void FlacEncoder_rectangular_window(struct f_array *window,
				    int L);

void FlacEncoder_hann_window(struct f_array *window,
			     int L);

void FlacEncoder_tukey_window(struct f_array *window,
			      int L,
			      double p);

/*given a windowed signal and maximum LPC order,
  returns a set of autocorrelation values*/
void FlacEncoder_compute_autocorrelation(struct f_array *values,
					 struct f_array *windowed_signal,
					 int max_lpc_order);

/*takes a set of autocorrelation values and a maximum LPC order
  returns a list of lp_coefficient lists and a list of error values*/
void FlacEncoder_compute_lp_coefficients(struct fa_array *lp_coefficients,
					 struct f_array *error_values,
					 struct f_array *autocorrelation_values,
					 int max_lpc_order);

int FlacEncoder_compute_best_order(struct f_array *error_values,
				   int total_samples,
				   int overhead_bits_per_order);

double FlacEncoder_compute_expected_bits_per_residual_sample(double lpc_error,
							     double error_scale);

/*given a set of LP coefficent floats and precision value,
  returns a set of QLP coefficent ints and a shift_needed int*/
void FlacEncoder_quantize_coefficients(struct f_array *lp_coefficients,
				       int precision,
				       struct i_array *qlp_coefficients,
				       int *shift_needed);

#endif
