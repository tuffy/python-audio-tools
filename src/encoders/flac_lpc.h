#ifndef A_FLAC_ENCODER_LPC
#define A_FLAC_ENCODER_LPC

#include "flac.h"

void FlacEncoder_compute_best_lpc_coeffs(struct flac_encoding_options *options,
					 int bits_per_sample,
					 struct i_array *samples,
					 struct i_array *coeffs,
					 int *shift_needed);

#endif
