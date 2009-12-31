#include "flac_lpc.h"

void FlacEncoder_compute_best_lpc_coeffs(struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 struct i_array *coeffs,
					 int *shift_needed) {
  ia_reset(coeffs);

  ia_append(coeffs,1);
  *shift_needed = 0;
}
