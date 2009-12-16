static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args) {
  char *filename;
  FILE *file;
  Bitstream *stream;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;
  struct flac_STREAMINFO streaminfo;

  struct ia_array samples;

  int block_size = 4096;

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
  iaa_init(&samples,reader->channels,block_size);

  if (!pcmr_read(reader,block_size,&samples))
    goto error;

  while (iaa_getitem(&samples,0)->size > 0) {
    if (!FlacEncoder_write_frame(stream,&streaminfo,&samples))
      goto error;

    if (!pcmr_read(reader,block_size,&samples))
      goto error;
  }


  /*go back and re-write STREAMINFO with complete values*/



  /* if (!pcmr_read(reader,20,&samples)) */
  /*   goto error; */

  /* for (i = 0; i < reader->channels; i++) { */
  /*   ia_print(stdout,iaa_getitem(&samples,i)); */
  /*   printf(" %d\n",iaa_getitem(&samples,i)->size); */
  /* } */


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
  int i;

  write_bits(bs,16,streaminfo.minimum_block_size);
  write_bits(bs,16,streaminfo.maximum_block_size);
  write_bits(bs,24,streaminfo.minimum_frame_size);
  write_bits(bs,24,streaminfo.maximum_frame_size);
  write_bits(bs,20,streaminfo.sample_rate);
  write_bits(bs,3,streaminfo.channels - 1);
  write_bits(bs,5,streaminfo.bits_per_sample - 1);
  write_bits64(bs,36,streaminfo.total_samples);
  for (i = 0; i < 16; i++)
    write_bits(bs,8,streaminfo.md5sum[i]);
}

int FlacEncoder_write_frame(Bitstream *bs,
			    struct flac_STREAMINFO *streaminfo,
			    struct ia_array *samples) {
  if (!FlacEncoder_write_frame_header(bs,streaminfo,samples))
    return 0;

  streaminfo->total_samples++;

  return 1;
}

int FlacEncoder_write_frame_header(Bitstream *bs,
				   struct flac_STREAMINFO *streaminfo,
				   struct ia_array *samples) {
  int block_size_bits;

  /*from the given amount of samples, determine the block size bits*/
  switch (iaa_getitem(samples,0)->size) {
  case 192:   block_size_bits = 0x1; break;
  case 576:   block_size_bits = 0x2; break;
  case 1152:  block_size_bits = 0x3; break;
  case 2304:  block_size_bits = 0x4; break;
  case 4608:  block_size_bits = 0x5; break;
  case 256:   block_size_bits = 0x8; break;
  case 512:   block_size_bits = 0x9; break;
  case 1024:  block_size_bits = 0xA; break;
  case 2048:  block_size_bits = 0xB; break;
  case 4096:  block_size_bits = 0xC; break;
  case 8192:  block_size_bits = 0xD; break;
  case 16384: block_size_bits = 0xE; break;
  case 32768: block_size_bits = 0xF; break;
  default:
    if (iaa_getitem(samples,0)->size < (0xFF + 1))
      block_size_bits = 0x6;
    else if (iaa_getitem(samples,0)->size < (0xFFFF + 1))
      block_size_bits = 0x7;
    else {
      PyErr_SetString(PyExc_ValueError,"invalid sample rate");
      return 0;
    }
    break;
  }



  return 1;
}
