#include "flac_lpc.h"

void FlacEncoder_compute_best_lpc_coeffs(struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 struct i_array *coeffs,
					 int *shift_needed) {
  struct f_array tukey_window;
  struct f_array windowed_signal;
  struct f_array autocorrelation_values;

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

  /*if non-exhaustive search, estimate best order*/

  /*if exhaustive search, calculate best order*/

  /*quantize coefficients*/

  /*return best QLP coefficients and shift-needed values*/

  /*free temporary values*/
  fa_free(&tukey_window);
  fa_free(&windowed_signal);

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
