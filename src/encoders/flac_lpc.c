#include "flac_lpc.h"

#define MIN(x,y) ((x) < (y) ? (x) : (y))
#define MAX(x,y) ((x) > (y) ? (x) : (y))

void FlacEncoder_compute_best_lpc_coeffs(struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 struct i_array *coeffs,
					 int *shift_needed) {
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
  fa_init(&autocorrelation_values,options->max_lpc_order);
  FlacEncoder_compute_autocorrelation(&autocorrelation_values,
				      &windowed_signal,
				      options->max_lpc_order);

  /*compute LP coefficients*/
  faa_init(&lp_coefficients,options->max_lpc_order,options->max_lpc_order);
  fa_init(&error_values,options->max_lpc_order);
  FlacEncoder_compute_lp_coefficients(&lp_coefficients,
				      &error_values,
				      &autocorrelation_values,
				      options->max_lpc_order - 1);

  /*if non-exhaustive search, estimate best order*/
  lpc_order = FlacEncoder_compute_best_order(&error_values,
					     samples->size,
					     bits_per_sample + 5);

  /*if exhaustive search, calculate best order*/

  /*quantize coefficients*/

  /*return best QLP coefficients and shift-needed values*/

  /*free temporary values*/
  fa_free(&tukey_window);
  fa_free(&windowed_signal);
  fa_free(&autocorrelation_values);
  faa_free(&lp_coefficients);
  fa_free(&error_values);

  ia_reset(coeffs);
  ia_append(coeffs,1);
  *shift_needed = 0;
}

void FlacEncoder_rectangular_window(struct f_array *window,
				    int L) {
  int n;

  for (n = 0; n < L; n++)
    fa_append(window,1.0);
}

void FlacEncoder_hann_window(struct f_array *window,
			     int L) {
  int n;

  for (n = 0; n < L; n++)
    fa_append(window,0.5 * (1.0 - cos((2 * M_PI * n) /
				      (double)(L - 1))));
}

/*L is the window length
  p is the ratio of Hann window samples to rectangular window samples
  generates a Tukey window*/
void FlacEncoder_tukey_window(struct f_array *window,
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

  FlacEncoder_rectangular_window(&rect_window,L - hann_length);
  FlacEncoder_hann_window(&hann_window,hann_length);
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

void FlacEncoder_compute_autocorrelation(struct f_array *values,
					 struct f_array *windowed_signal,
					 int max_lpc_order) {
  int i,j;
  struct f_array lagged_signal;
  double sum;

  for (i = 0; i < max_lpc_order; i++) {
    sum = 0.0;
    fa_tail(&lagged_signal,windowed_signal,windowed_signal->size - i);
    for (j = 0; j < lagged_signal.size; j++)
      sum += (fa_getitem(windowed_signal,j) * fa_getitem(&lagged_signal,j));
    fa_append(values,sum);
  }
}

void FlacEncoder_compute_lp_coefficients(struct fa_array *lp_coefficients,
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
  uint32_t i;

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

int FlacEncoder_compute_best_order(struct f_array *error_values,
				   int total_samples,
				   int overhead_bits_per_order) {
  double error_scale = (M_LN2 * M_LN2) / (total_samples * 2);
  int best_order;
  double best_bits = 1e32;
  double bits;
  int order;

  for (order = 0; order < error_values->size; order++) {
    bits = FlacEncoder_compute_expected_bits_per_residual_sample(
      fa_getitem(error_values,order),
      error_scale) + (order * overhead_bits_per_order);
    if (bits < best_bits) {
      best_order = order;
      best_bits = bits;
    }
  }

  return 0;
}

double FlacEncoder_compute_expected_bits_per_residual_sample(double lpc_error,
							     double error_scale) {
  if (lpc_error > 0.0) {
    return MAX(log(error_scale * lpc_error) / (M_LN2 * 2),
	       0.0);
  } else if (lpc_error < 0.0) {
    return 1e32;
  } else {
    return 0.0;
  }
}
