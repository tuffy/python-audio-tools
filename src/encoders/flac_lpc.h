#ifndef A_FLAC_ENCODER_LPC
#define A_FLAC_ENCODER_LPC

#include "flac.h"

void FlacEncoder_compute_best_lpc_coeffs(struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 struct i_array *coeffs,
					 int *shift_needed);

void FlacEncoder_rectangular_window(struct f_array *window,
				    int L);

void FlacEncoder_hann_window(struct f_array *window,
			     int L);

void FlacEncoder_tukey_window(struct f_array *window,
			      int L,
			      double p);

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

void FlacEncoder_quantize_coefficients(struct f_array *lp_coefficients,
				       int precision,
				       struct i_array *qlp_coefficients,
				       int *shift_needed);

#endif
