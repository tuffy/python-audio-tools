#include "alac_lpc.h"

extern void FlacEncoder_tukey_window(struct f_array *window,
				     int L,
				     double p);

extern void FlacEncoder_compute_autocorrelation(struct f_array *values,
						struct f_array *windowed_signal,
						int max_lpc_order);

extern void FlacEncoder_compute_lp_coefficients(struct fa_array *lp_coefficients,
						struct f_array *error_values,
						struct f_array *autocorrelation_values,
						int max_lpc_order);

extern double FlacEncoder_compute_expected_bits_per_residual_sample(double lpc_error,
								  double error_scale);

extern void FlacEncoder_quantize_coefficients(struct f_array *lp_coefficients,
					      int precision,
					      struct i_array *qlp_coefficients,
					      int *shift_needed);

void ALACEncoder_compute_best_lpc_coeffs(struct i_array *coeffs,
					 int *shift_needed,

					 int bits_per_sample,
					 struct alac_encoding_options *options,
					 struct i_array *samples) {
  struct f_array tukey_window;
  struct f_array windowed_signal;
  struct f_array autocorrelation_values;
  struct fa_array lp_coefficients;
  struct f_array error_values;
  int lpc_order;

  /*window signal*/
  fa_init(&tukey_window,samples->size);
  fa_init(&windowed_signal,samples->size);
  FlacEncoder_tukey_window(&tukey_window,samples->size,0.5);
  fa_mul_ia(&windowed_signal,&tukey_window,samples);

  /*compute autocorrelation*/
  fa_init(&autocorrelation_values,MAX_LPC_ORDER);
  FlacEncoder_compute_autocorrelation(&autocorrelation_values,
				      &windowed_signal,
				      MAX_LPC_ORDER);

  /*compute LP coefficients*/
  faa_init(&lp_coefficients,
	   MAX_LPC_ORDER,
	   MAX_LPC_ORDER);
  fa_init(&error_values,MAX_LPC_ORDER);
  FlacEncoder_compute_lp_coefficients(&lp_coefficients,
				      &error_values,
				      &autocorrelation_values,
				      MAX_LPC_ORDER - 1);

  /*estimate whether to use order 4 or 8*/
  fa_tail(&error_values,&error_values,error_values.size - 1);
  lpc_order = ALACEncoder_compute_best_order(&error_values,
					     samples->size,
					     bits_per_sample + 5);

  /*quantize coefficients*/
  ia_reset(coeffs);
  FlacEncoder_quantize_coefficients(faa_getitem(&lp_coefficients,
						lpc_order - 1),
				    QLP_COEFFICIENT_PRECISION,
				    coeffs,
				    shift_needed);

  /*free temporary values*/
  fa_free(&tukey_window);
  fa_free(&windowed_signal);
  fa_free(&autocorrelation_values);

  return;
}

int ALACEncoder_compute_best_order(struct f_array *error_values,
				   int total_samples,
				   int overhead_bits_per_order) {
  double error_scale = (M_LN2 * M_LN2) / (double)(total_samples * 2);
  int best_order = 0;
  double best_bits = 1e32;
  double bits;
  int order;
  int i;

  for (i = 0,order = 1; i < error_values->size; i++,order++) {
    if ((order != MIN_LPC_ORDER) || (order != MAX_LPC_ORDER))
      continue;

    bits = FlacEncoder_compute_expected_bits_per_residual_sample(
      fa_getitem(error_values,i),
      error_scale) * (double)(total_samples - order) + (double)(order * overhead_bits_per_order);
    if (bits < best_bits) {
      best_order = order;
      best_bits = bits;
    }
  }

  return best_order;
}

