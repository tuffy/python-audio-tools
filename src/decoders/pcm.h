static PyObject*
ia_array_to_framelist(struct ia_array *data,
                      int bits_per_sample);

static PyObject*
ia_array_slice_to_framelist(struct ia_array *data,
                            int bits_per_sample,
                            int start_frame,
                            int end_frame);
