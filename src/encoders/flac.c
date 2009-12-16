static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args) {
  char *filename;
  FILE *file;
  Bitstream *stream;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;
  struct flac_STREAMINFO streaminfo;

  struct ia_array samples;

  uint32_t i;

  /*extract a filename and PCMReader-compatible object*/
  if (!PyArg_ParseTuple(args,"sO",&filename,&pcmreader_obj))
    return NULL;

  /*open the given filename for writing*/
  if ((file = fopen(filename,"wb")) == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return NULL;
  }

  /*transform the Python PCMReader-compatible object to a struct pcm_reader*/
  if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
    fclose(file);
    Py_DECREF(pcmreader_obj);
    return NULL;
  }

  stream = bs_open(file);

  /*fill streaminfo with some placeholder values*/
  streaminfo.minimum_block_size = 0;
  streaminfo.maximum_block_size = 0xFFFF;
  streaminfo.minimum_frame_size = 0;
  streaminfo.maximum_frame_size = 0xFFFFFF;
  streaminfo.sample_rate = reader->sample_rate;
  streaminfo.channels = reader->channels;
  streaminfo.bits_per_sample = reader->bits_per_sample;
  streaminfo.total_samples = 0;
  memcpy(streaminfo.md5sum,
	 "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
	 16);

  /*write FLAC stream header*/
  write_bits(stream,32,0x664C6143);

  /*write metadata header*/
  write_bits(stream,1,1);
  write_bits(stream,7,0);
  write_bits(stream,24,34);

  /*write placeholder STREAMINFO*/
  FlacEncoder_write_streaminfo(stream,streaminfo);

  /*build frames until reader is empty,
    which updates STREAMINFO in the process*/

  /*go back and re-write STREAMINFO with complete values*/


  iaa_init(&samples,reader->channels,20);

  printf("sample rate %ld\nchannels %ld\nbits per sample %ld\n",
	 reader->sample_rate,reader->channels,reader->bits_per_sample);

  if (!pcmr_read(reader,20,&samples))
    goto error;

  for (i = 0; i < reader->channels; i++) {
    ia_print(stdout,iaa_getitem(&samples,i));
    printf(" %d\n",iaa_getitem(&samples,i)->size);
  }


  iaa_free(&samples); /*deallocate the temporary samples block*/
  pcmr_close(reader); /*close the pcm_reader object
			which calls pcmreader.close() in the process*/
  bs_close(stream);     /*close the output file*/
  Py_INCREF(Py_None);
  return Py_None;
 error:
  /*an error result does everything a regular result does
    but returns NULL instead of Py_None*/
  iaa_free(&samples);
  pcmr_close(reader);
  bs_close(stream);
  return NULL;
}

void FlacEncoder_write_streaminfo(Bitstream *bs,
				  struct flac_STREAMINFO streaminfo) {
  write_bits(bs,16,streaminfo.minimum_block_size);
  write_bits(bs,16,streaminfo.maximum_block_size);
  write_bits(bs,24,streaminfo.minimum_frame_size);
  write_bits(bs,24,streaminfo.maximum_frame_size);
  write_bits(bs,20,streaminfo.sample_rate);
  write_bits(bs,3,streaminfo.channels - 1);
  write_bits(bs,5,streaminfo.bits_per_sample - 1);
  write_bits64(bs,36,streaminfo.total_samples);
  fwrite(streaminfo.md5sum,sizeof(unsigned char),16,bs->file);
}
