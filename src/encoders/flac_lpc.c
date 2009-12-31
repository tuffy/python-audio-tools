#include "flac_lpc.h"

void FlacEncoder_compute_best_lpc_coeffs(struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 struct i_array *coeffs,
					 int *shift_needed) {
  /*window signal*/

  /*compute autocorrelation*/

  /*compute LP coefficients*/

  /*if non-exhaustive search, estimate best order*/

  /*if exhaustive search, calculate best order*/

  /*quantize coefficients*/

  /*return best QLP coefficients and shift-needed values*/

  ia_reset(coeffs);
  ia_append(coeffs,1);
  *shift_needed = 0;
}
