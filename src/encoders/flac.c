static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args) {
  PyObject *pcmreader;
  PyObject *result;

  long sample_rate;
  long bits_per_sample;
  long channels;
  PyObject *read;
  PyObject *close;

  /*extract a PCMReader-compatible object and its attributes*/
  if (!PyArg_ParseTuple(args,"O",&pcmreader))
    return NULL;

  if (!parse_pcmreader(pcmreader,&read,&close,
		       &sample_rate,&channels,&bits_per_sample))
    return NULL;


  printf("sample rate %ld\nchannels %ld\nbits per sample %ld\n",
	 sample_rate,channels,bits_per_sample);


  /*close PCMReader object when finished*/
  result = PyEval_CallObject(close,NULL);
  if (result == NULL)
    goto error;
  else
    Py_DECREF(result);

  Py_DECREF(read);
  Py_DECREF(close);
  Py_INCREF(Py_None);
  return Py_None;
 error:
  Py_DECREF(read);
  Py_DECREF(close);
  return NULL;
}
