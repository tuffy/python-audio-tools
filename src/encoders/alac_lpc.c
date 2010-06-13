#include "alac_lpc.h"

static fa_data_t f_abs_max(fa_data_t val, fa_data_t max) {
  fa_data_t abs = fabs(val);
  return MAX(abs,max);
}

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
  ALACEncoder_tukey_window(&tukey_window,samples->size,0.5);
  fa_mul_ia(&windowed_signal,&tukey_window,samples);

  /*compute autocorrelation*/
  fa_init(&autocorrelation_values,MAX_LPC_ORDER + 1);
  ALACEncoder_compute_autocorrelation(&autocorrelation_values,
				      &windowed_signal,
				      MAX_LPC_ORDER + 1);

  /*compute LP coefficients*/
  faa_init(&lp_coefficients,
	   MAX_LPC_ORDER,
	   MAX_LPC_ORDER + 1);
  fa_init(&error_values,MAX_LPC_ORDER);
  ALACEncoder_compute_lp_coefficients(&lp_coefficients,
				      &error_values,
				      &autocorrelation_values,
				      MAX_LPC_ORDER);

  /*estimate whether to use order 4 or 8*/
  fa_tail(&error_values,&error_values,error_values.size - 1);
  lpc_order = ALACEncoder_compute_best_order(&error_values,
					     samples->size,
					     bits_per_sample + 5);

  /*quantize coefficients*/
  ia_reset(coeffs);
  ALACEncoder_quantize_coefficients(faa_getitem(&lp_coefficients,
						lpc_order - 1),
				    QLP_COEFFICIENT_PRECISION,
				    coeffs,
				    shift_needed);

  /*free temporary values*/
  fa_free(&error_values);
  faa_free(&lp_coefficients);
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
    if ((order != MIN_LPC_ORDER) && (order != MAX_LPC_ORDER))
      continue;

    bits = ALACEncoder_compute_expected_bits_per_residual_sample(
      fa_getitem(error_values,i),
      error_scale) * (double)(total_samples - order) + (double)(order * overhead_bits_per_order);
    if (bits < best_bits) {
      best_order = order;
      best_bits = bits;
    }
  }

  return best_order;
}


/*This is a lazy cut-&-paste from FlacEncoder.
  These functions should be shifted to a central LPC computation area*/

void ALACEncoder_rectangular_window(struct f_array *window,
				    int L) {
  int n;

  for (n = 0; n < L; n++)
    fa_append(window,1.0);
}

void ALACEncoder_hann_window(struct f_array *window,
			     int L) {
  int n;

  for (n = 0; n < L; n++)
    fa_append(window,0.5 * (1.0 - cos((2 * M_PI * n) /
				      (double)(L - 1))));
}

void ALACEncoder_tukey_window(struct f_array *window,
			      int L,
			      double p) {
  int hann_length = (int)(p * L) - 1;
  int i;
  struct f_array hann_window;
  struct f_array hann_head;
  struct f_array hann_tail;
  struct f_array rect_window;

  fa_init(&hann_window,hann_length);
  fa_init(&rect_window,L - hann_length);

  ALACEncoder_rectangular_window(&rect_window,L - hann_length);
  ALACEncoder_hann_window(&hann_window,hann_length);
  fa_split(&hann_head,&hann_tail,&hann_window,hann_length / 2);

  for (i = 0; i < hann_head.size; i++)
    fa_append(window,fa_getitem(&hann_head,i));
  for (i = 0; i < rect_window.size; i++)
    fa_append(window,fa_getitem(&rect_window,i));
  for (i = 0; i < hann_tail.size; i++)
    fa_append(window,fa_getitem(&hann_tail,i));

  fa_free(&hann_window);
  fa_free(&rect_window);
}

void ALACEncoder_compute_autocorrelation(struct f_array *values,
					 struct f_array *windowed_signal,
					 int max_lpc_order) {
  int i,j;
  struct f_array lagged_signal;
  double sum;
  fa_data_t *windowed_signal_data = windowed_signal->data;
  fa_data_t *lagged_signal_data;

  for (i = 0; i < max_lpc_order; i++) {
    sum = 0.0;
    fa_tail(&lagged_signal,windowed_signal,windowed_signal->size - i);
    lagged_signal_data = lagged_signal.data;
    for (j = 0; j < lagged_signal.size; j++)
      sum += (windowed_signal_data[j] * lagged_signal_data[j]);
    fa_append(values,sum);
  }
}

void ALACEncoder_compute_lp_coefficients(struct fa_array *lp_coefficients,
					 struct f_array *error_values,
					 struct f_array *autocorrelation_values,
					 int max_lpc_order) {
  /*r is autocorrelation_values
    a is lp_coefficients, a list of LP coefficient lists
    E is error_values
    M is max_lpc_order
    q and k are temporary values*/

  double qm;
  double km;
  struct f_array a;
  struct f_array r;
  struct f_array *a_i;
  struct f_array ra_i;
  struct f_array *a_im;
  int m;
  fa_size_t i;

  fa_init(&a,max_lpc_order);
  fa_init(&ra_i,max_lpc_order);


  /*E(0) = r(0)*/
  fa_append(error_values,fa_getitem(autocorrelation_values,0));

  /*a(1)(1) = k(1) = r(1) / E(0)*/
  km = fa_getitem(autocorrelation_values,1) / fa_getitem(error_values,0);
  fa_append(faa_getitem(lp_coefficients,0),km);

  /*E(1) = E(0) * (1 - (k(1) ^ 2))*/
  fa_append(error_values,
	    fa_getitem(error_values,-1) * (1 - (km * km)));

  for (m = 2; m <= max_lpc_order; m++) {
    /*q(m) = r(m) - sum(i = 1 to m - 1, a(i)(m - 1) * r(m - i))*/
    fa_copy(&a,faa_getitem(lp_coefficients,m - 2));
    fa_reverse(&a);
    fa_tail(&r,autocorrelation_values,autocorrelation_values->size - 1);
    fa_mul(&a,&a,&r);
    qm = fa_getitem(autocorrelation_values,m) - fa_sum(&a);

    /*k(m) = q(m) / E(m - 1)*/
    km = qm / fa_getitem(error_values,m - 1);

    /*a(i)(m) = a(i)(m - 1) - k(m) * a(m - i)(m - 1) for i = 1 to m - 1*/
    a_i = faa_getitem(lp_coefficients,m - 2);
    fa_copy(&ra_i,a_i);
    fa_reverse(&ra_i);

    a_im = faa_getitem(lp_coefficients,m - 1);
    for (i = 0; i < ra_i.size; i++) {
      fa_append(a_im,fa_getitem(a_i,i) - (km * fa_getitem(&ra_i,i)));
    }

    /*a(m)(m) = k(m)*/
    fa_append(a_im,km);

    /*E(m) = E(m - 1) * (1 - k(m) ^ 2)*/
    fa_append(error_values, fa_getitem(error_values,-1) * (1 - (km * km)));

    /*continue until m == M*/
  }

  fa_free(&a);
  fa_free(&ra_i);
}

double ALACEncoder_compute_expected_bits_per_residual_sample(double lpc_error,
							     double error_scale) {
  if (lpc_error > 0.0) {
    return MAX(log(error_scale * lpc_error) / (M_LN2 * 2.0),0.0);
  } else if (lpc_error < 0.0) {
    return 1e32;
  } else {
    return 0.0;
  }
}

void ALACEncoder_quantize_coefficients(struct f_array *lp_coefficients,
				       int precision,
				       struct i_array *qlp_coefficients,
				       int *shift_needed) {
  int log2cmax;
  int32_t qlp_coeff_min;
  int32_t qlp_coeff_max;
  fa_size_t i;
  int32_t qlp;
  double error = 0.0;

  precision--;

  (void)frexp(fa_reduce(lp_coefficients,0.0,f_abs_max),&log2cmax);

  *shift_needed = 9;

  qlp_coeff_max = (1 << precision) - 1;
  qlp_coeff_min = -(1 << precision);

  for (i = 0; i < lp_coefficients->size; i++) {
    error += fa_getitem(lp_coefficients,i) * (1 << *shift_needed);
    qlp = MIN(MAX(lround(error),qlp_coeff_min),qlp_coeff_max);
    ia_append(qlp_coefficients,qlp);
    error -= qlp;
  }
}
