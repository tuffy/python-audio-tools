static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args) {
  PyObject *pcmreader;
  PyObject *result;

  struct ia_array samples;

  long sample_rate;
  long bits_per_sample;
  long channels;
  PyObject *read;
  PyObject *close;

  uint32_t i;

  /*extract a PCMReader-compatible object and its attributes*/
  if (!PyArg_ParseTuple(args,"O",&pcmreader))
    return NULL;

  if (!parse_pcmreader(pcmreader,&read,&close,
		       &sample_rate,&channels,&bits_per_sample))
    return NULL;

  iaa_init(&samples,channels,20);

  printf("sample rate %ld\nchannels %ld\nbits per sample %ld\n",
	 sample_rate,channels,bits_per_sample);

  if (!read_samples(read,20,bits_per_sample,&samples))
    goto error;

  for (i = 0; i < channels; i++) {
    ia_print(stdout,iaa_getitem(&samples,i));
    printf(" %d\n",iaa_getitem(&samples,i)->size);
  }

  /*close PCMReader object when finished*/
  result = PyEval_CallObject(close,NULL);
  if (result == NULL)
    goto error;
  else
    Py_DECREF(result);

  iaa_free(&samples);
  Py_DECREF(read);
  Py_DECREF(close);
  Py_INCREF(Py_None);
  return Py_None;
 error:
  iaa_free(&samples);
  Py_DECREF(read);
  Py_DECREF(close);
  return NULL;
}
