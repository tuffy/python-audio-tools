static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args) {
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;

  struct ia_array samples;

  uint32_t i;

  /*extract a PCMReader-compatible object and its attributes*/
  if (!PyArg_ParseTuple(args,"O",&pcmreader_obj))
    return NULL;

  if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
    Py_DECREF(pcmreader_obj);
    return NULL;
  }

  iaa_init(&samples,reader->channels,20);

  printf("sample rate %ld\nchannels %ld\nbits per sample %ld\n",
	 reader->sample_rate,reader->channels,reader->bits_per_sample);

  if (!pcmr_read(reader,20,&samples))
    goto error;

  for (i = 0; i < reader->channels; i++) {
    ia_print(stdout,iaa_getitem(&samples,i));
    printf(" %d\n",iaa_getitem(&samples,i)->size);
  }

  /*close PCMReader object and free samples when finished*/
  iaa_free(&samples);
  pcmr_close(reader);
  Py_INCREF(Py_None);
  return Py_None;
 error:
  iaa_free(&samples);
  pcmr_close(reader);
  return NULL;
}
