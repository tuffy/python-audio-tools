int FlacDecoder_init(decoders_FlacDecoder *self,
		     PyObject *args, PyObject *kwds) {
  char* filename;
  int i;

  if (!PyArg_ParseTuple(args, "s", &filename))
    return -1;

  self->filename = NULL;
  self->file = NULL;
  self->bitstream = NULL;

  /*open the flac file*/
  self->file = fopen(filename,"rb");
  if (self->file == NULL) {
    PyErr_SetFromErrnoWithFilename(PyExc_IOError,filename);
    return -1;
  } else {
    self->bitstream = bs_open(self->file);
  }

  self->filename = strdup(filename);

  /*read the STREAMINFO block and setup the total number of samples to read*/
  if (!FlacDecoder_read_metadata(self)) {
    return -1;
  }

  self->remaining_samples = self->streaminfo.total_samples;

  /*add callbacks for CRC8 and CRC16 calculation*/
  bs_add_callback(self->bitstream,crc8,&(self->crc8));
  bs_add_callback(self->bitstream,crc16,&(self->crc16));

  /*setup a bunch of temporary buffers*/
  for (i = 0; i < self->streaminfo.channels; i++) {
    ia_init(&(self->subframe_data[i]),
	    self->streaminfo.maximum_block_size);
  }
  ia_init(&(self->residuals),self->streaminfo.maximum_block_size);
  ia_init(&(self->qlp_coeffs),1);
  self->data = NULL;
  self->data_size = 0;

  return 0;
}

PyObject *FLACDecoder_close(decoders_FlacDecoder* self,
			    PyObject *args) {
  self->remaining_samples = 0;
  Py_INCREF(Py_None);
  return Py_None;
}

void FlacDecoder_dealloc(decoders_FlacDecoder *self) {
  int i;

  for (i = 0; i < self->streaminfo.channels; i++) {
    ia_free(&(self->subframe_data[i]));
  }
  ia_free(&(self->residuals));
  ia_free(&(self->qlp_coeffs));

  if (self->filename != NULL)
    free(self->filename);

  bs_close(self->bitstream);

  Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject *FlacDecoder_new(PyTypeObject *type,
			  PyObject *args, PyObject *kwds) {
  decoders_FlacDecoder *self;

  self = (decoders_FlacDecoder *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

int FlacDecoder_read_metadata(decoders_FlacDecoder *self) {
  unsigned int last_block;
  unsigned int block_type;
  unsigned int block_length;

  if (read_bits(self->bitstream,32) != 0x664C6143u) {
    PyErr_SetString(PyExc_ValueError,"not a FLAC file");
    return 0;
  }

  last_block = read_bits(self->bitstream,1);
  block_type = read_bits(self->bitstream,7);
  block_length = read_bits(self->bitstream,24);

  if (block_type == 0) {
    self->streaminfo.minimum_block_size = read_bits(self->bitstream,16);
    self->streaminfo.maximum_block_size = read_bits(self->bitstream,16);
    self->streaminfo.minimum_frame_size = read_bits(self->bitstream,24);
    self->streaminfo.maximum_frame_size = read_bits(self->bitstream,24);
    self->streaminfo.sample_rate = read_bits(self->bitstream,20);
    self->streaminfo.channels = read_bits(self->bitstream,3) + 1;
    self->streaminfo.bits_per_sample = read_bits(self->bitstream,5) + 1;
    self->streaminfo.total_samples = read_bits64(self->bitstream,36);
    if (fread(self->streaminfo.md5sum,sizeof(unsigned char),16,self->file)
	!= 16) {
      PyErr_SetString(PyExc_ValueError,"unable to read md5sum");
      return 0;
    }
  } else {
    PyErr_SetString(PyExc_ValueError,"STREAMINFO not first metadata block");
    return 0;
  }

  while (!last_block) {
    last_block = read_bits(self->bitstream,1);
    block_type = read_bits(self->bitstream,7);
    block_length = read_bits(self->bitstream,24);
    fseek(self->file,block_length,SEEK_CUR);
  }

  return 1;
}

static PyObject *FlacDecoder_sample_rate(decoders_FlacDecoder *self,
					 void *closure) {
  return Py_BuildValue("i",self->streaminfo.sample_rate);
}

static PyObject *FlacDecoder_bits_per_sample(decoders_FlacDecoder *self,
					     void *closure) {
  return Py_BuildValue("i",self->streaminfo.bits_per_sample);
}

static PyObject *FlacDecoder_channels(decoders_FlacDecoder *self,
				      void *closure) {
  return Py_BuildValue("i",self->streaminfo.channels);
}

PyObject *FLACDecoder_read(decoders_FlacDecoder* self,
			   PyObject *args) {
  int bytes;
  struct flac_frame_header frame_header;
  int channel;
  int data_size;
  PyObject *string;

  int32_t i;
  int64_t mid;
  int32_t side;

  if (!PyArg_ParseTuple(args, "i", &bytes))
    return NULL;
  if (bytes < 0) {
    PyErr_SetString(PyExc_ValueError,"number of bytes must be positive");
    return NULL;
  }

  /*if all samples have been read, return an empty string*/
  if (self->remaining_samples < 1)
    return PyString_FromStringAndSize("",0);

  self->crc8 = self->crc16 = 0;

  if (!FlacDecoder_read_frame_header(self,&frame_header))
    return NULL;

  data_size = frame_header.block_size * frame_header.bits_per_sample *
    frame_header.channel_count / 8;
  if (data_size > self->data_size) {
    self->data = realloc(self->data,data_size);
    self->data_size = data_size;
  }

  for (channel = 0; channel < frame_header.channel_count; channel++) {
    if (((frame_header.channel_assignment == 0x8) &&
	 (channel == 1)) ||
	((frame_header.channel_assignment == 0x9) &&
	 (channel == 0)) ||
	((frame_header.channel_assignment == 0xA) &&
	 (channel == 1))) {
      if (!FlacDecoder_read_subframe(self,
				     frame_header.block_size,
				     frame_header.bits_per_sample + 1,
				     &(self->subframe_data[channel])))
	return NULL;
    } else {
      if (!FlacDecoder_read_subframe(self,
				     frame_header.block_size,
				     frame_header.bits_per_sample,
				     &(self->subframe_data[channel])))
	return NULL;
    }
  }

  /*handle difference channels, if any*/
  switch (frame_header.channel_assignment) {
  case 0x8:
    /*left-difference*/
    ia_sub(&(self->subframe_data[1]),
	   &(self->subframe_data[0]),&(self->subframe_data[1]));
    break;
  case 0x9:
    /*difference-right*/
    ia_add(&(self->subframe_data[0]),
	   &(self->subframe_data[0]),&(self->subframe_data[1]));
    break;
  case 0xA:
    /*mid-side*/
    for (i = 0; i < frame_header.block_size; i++) {
      mid = ia_getitem(&(self->subframe_data[0]),i);
      side = ia_getitem(&(self->subframe_data[1]),i);
      mid = (mid << 1) | (side & 1);
      ia_setitem(&(self->subframe_data[0]),i,(mid + side) >> 1);
      ia_setitem(&(self->subframe_data[1]),i,(mid - side) >> 1);
    }
    break;
  default:
    /*do nothing for independent channels*/
    break;
  }

  /*check CRC-16*/
  byte_align(self->bitstream,BYTE_ALIGN_READ);
  read_bits(self->bitstream,16);
  if (self->crc16 != 0) {
    PyErr_SetString(PyExc_ValueError,"invalid checksum in frame");
    return 0;
  }

  /*transform subframe data into single string*/
  for (channel = 0; channel < frame_header.channel_count; channel++) {
    switch (frame_header.bits_per_sample) {
    case 8:
      ia_S8_to_char(self->data,&(self->subframe_data[channel]),
		    channel,frame_header.channel_count);
      break;
    case 16:
      ia_SL16_to_char(self->data,&(self->subframe_data[channel]),
  		      channel,frame_header.channel_count);
      break;
    case 24:
      ia_SL24_to_char(self->data,&(self->subframe_data[channel]),
  		      channel,frame_header.channel_count);
      break;
    default:
      PyErr_SetString(PyExc_ValueError,"unsupported bits per sample value");
      return 0;
    }
  }

  /*decrement remaining samples*/
  self->remaining_samples -= frame_header.block_size;

  /*return string*/
  string = PyString_FromStringAndSize((char*)self->data,data_size);
  return string;
}

int FlacDecoder_read_frame_header(decoders_FlacDecoder *self,
				  struct flac_frame_header *header) {
  Bitstream *bitstream = self->bitstream;
  uint32_t block_size_bits;
  uint32_t sample_rate_bits;

  /*read and verify sync code*/
  if (read_bits(bitstream,14) != 0x3FFE) {
    PyErr_SetString(PyExc_ValueError,"invalid sync code");
    return 0;
  }

  /*read and verify reserved bit*/
  if (read_bits(bitstream,1) != 0) {
    PyErr_SetString(PyExc_ValueError,"invalid reserved bit");
    return 0;
  }

  header->blocking_strategy = read_bits(bitstream,1);

  block_size_bits = read_bits(bitstream,4);
  sample_rate_bits = read_bits(bitstream,4);
  header->channel_assignment = read_bits(bitstream,4);
  switch (header->channel_assignment) {
  case 0x8:
  case 0x9:
  case 0xA:
    header->channel_count = 2;
    break;
  default:
    header->channel_count = header->channel_assignment + 1;
    break;
  }

  switch (read_bits(bitstream,3)) {
  case 0:
    header->bits_per_sample = self->streaminfo.bits_per_sample; break;
  case 1:
    header->bits_per_sample = 8; break;
  case 2:
    header->bits_per_sample = 12; break;
  case 4:
    header->bits_per_sample = 16; break;
  case 5:
    header->bits_per_sample = 20; break;
  case 6:
    header->bits_per_sample = 24; break;
  default:
    PyErr_SetString(PyExc_ValueError,"invalid bits per sample");
    return 0;
  }
  read_bits(bitstream,1); /*padding*/

  header->frame_number = read_utf8(bitstream);

  switch (block_size_bits) {
  case 0x0: header->block_size = self->streaminfo.maximum_block_size; break;
  case 0x1: header->block_size = 192; break;
  case 0x2: header->block_size = 576; break;
  case 0x3: header->block_size = 1152; break;
  case 0x4: header->block_size = 2304; break;
  case 0x5: header->block_size = 4608; break;
  case 0x6: header->block_size = read_bits(bitstream,8) + 1; break;
  case 0x7: header->block_size = read_bits(bitstream,16) + 1; break;
  case 0x8: header->block_size = 256; break;
  case 0x9: header->block_size = 512; break;
  case 0xA: header->block_size = 1024; break;
  case 0xB: header->block_size = 2048; break;
  case 0xC: header->block_size = 4096; break;
  case 0xD: header->block_size = 8192; break;
  case 0xE: header->block_size = 16384; break;
  case 0xF: header->block_size = 32768; break;
  }

  switch (sample_rate_bits) {
  case 0x0: header->sample_rate = self->streaminfo.sample_rate; break;
  case 0x1: header->sample_rate = 88200; break;
  case 0x2: header->sample_rate = 176400; break;
  case 0x3: header->sample_rate = 192000; break;
  case 0x4: header->sample_rate = 8000; break;
  case 0x5: header->sample_rate = 16000; break;
  case 0x6: header->sample_rate = 22050; break;
  case 0x7: header->sample_rate = 24000; break;
  case 0x8: header->sample_rate = 32000; break;
  case 0x9: header->sample_rate = 44100; break;
  case 0xA: header->sample_rate = 48000; break;
  case 0xB: header->sample_rate = 96000; break;
  case 0xC: header->sample_rate = read_bits(bitstream,8) * 1000; break;
  case 0xD: header->sample_rate = read_bits(bitstream,16); break;
  case 0xE: header->sample_rate = read_bits(bitstream,16) * 10; break;
  case 0xF:
    PyErr_SetString(PyExc_ValueError,"invalid sample rate");
    return 0;
  }

  /*check for valid CRC-8 value*/
  read_bits(bitstream,8);
  if (self->crc8 != 0) {
    PyErr_SetString(PyExc_ValueError,"invalid checksum in frame header");
    return 0;
  }

  return 1;
}

int FlacDecoder_read_subframe(decoders_FlacDecoder *self,
			      uint32_t block_size,
			      uint8_t bits_per_sample,
			      struct i_array *samples) {
  struct flac_subframe_header subframe_header;
  uint32_t i;

  if (!FlacDecoder_read_subframe_header(self,&subframe_header))
    return 0;

  /*account for wasted bits-per-sample*/
  if (subframe_header.wasted_bits_per_sample > 0)
    bits_per_sample -= subframe_header.wasted_bits_per_sample;

  switch (subframe_header.type) {
  case FLAC_SUBFRAME_CONSTANT:
    if (!FlacDecoder_read_constant_subframe(self, block_size, bits_per_sample,
					    samples))
      return 0;
    break;
  case FLAC_SUBFRAME_VERBATIM:
    if (!FlacDecoder_read_verbatim_subframe(self, block_size, bits_per_sample,
					    samples))
      return 0;
    break;
  case FLAC_SUBFRAME_FIXED:
    if (!FlacDecoder_read_fixed_subframe(self, subframe_header.order,
					 block_size, bits_per_sample,
					 samples))
      return 0;
    break;
  case FLAC_SUBFRAME_LPC:
    if (!FlacDecoder_read_lpc_subframe(self, subframe_header.order,
				       block_size, bits_per_sample,
				       samples))
      return 0;
    break;
  }

  /*reinsert wasted bits-per-sample, if necessary*/
  if (subframe_header.wasted_bits_per_sample > 0)
    for (i = 0; i < block_size; i++)
      ia_setitem(samples,i,ia_getitem(samples,i) << subframe_header.wasted_bits_per_sample);

  return 1;
}

int FlacDecoder_read_subframe_header(decoders_FlacDecoder *self,
				     struct flac_subframe_header *subframe_header) {
  Bitstream *bitstream = self->bitstream;
  uint8_t subframe_type;

  read_bits(bitstream,1);  /*padding*/
  subframe_type = read_bits(bitstream,6);
  if (subframe_type == 0) {
    subframe_header->type = FLAC_SUBFRAME_CONSTANT;
    subframe_header->order = 0;
  } else if (subframe_type == 1) {
    subframe_header->type = FLAC_SUBFRAME_VERBATIM;
    subframe_header->order = 0;
  } else if ((subframe_type & 0x38) == 0x08) {
    subframe_header->type = FLAC_SUBFRAME_FIXED;
    subframe_header->order = subframe_type & 0x07;
  } else if ((subframe_type & 0x20) == 0x20) {
    subframe_header->type = FLAC_SUBFRAME_LPC;
    subframe_header->order = (subframe_type & 0x1F) + 1;
  } else {
    PyErr_SetString(PyExc_ValueError,"invalid subframe type");
    return 0;
  }

  if (read_bits(bitstream,1) == 0) {
    subframe_header->wasted_bits_per_sample = 0;
  } else {
    subframe_header->wasted_bits_per_sample = read_unary(bitstream,1) + 1;
  }

  return 1;
}

int FlacDecoder_read_constant_subframe(decoders_FlacDecoder *self,
				       uint32_t block_size,
				       uint8_t bits_per_sample,
				       struct i_array *samples) {
  int32_t value = read_signed_bits(self->bitstream,bits_per_sample);
  int32_t i;

  ia_reset(samples);

  for (i = 0; i < block_size; i++)
    ia_append(samples,value);

  return 1;
}

int FlacDecoder_read_verbatim_subframe(decoders_FlacDecoder *self,
				       uint32_t block_size,
				       uint8_t bits_per_sample,
				       struct i_array *samples) {
  int32_t i;

  ia_reset(samples);
  for (i = 0; i < block_size; i++)
    ia_append(samples,read_signed_bits(self->bitstream,bits_per_sample));

  return 1;
}

int FlacDecoder_read_fixed_subframe(decoders_FlacDecoder *self,
				    uint8_t order,
				    uint32_t block_size,
				    uint8_t bits_per_sample,
				    struct i_array *samples) {
  int32_t i;
  Bitstream *bitstream = self->bitstream;
  struct i_array *residuals = &(self->residuals);

  ia_reset(residuals);
  ia_reset(samples);

  /*read "order" number of warm-up samples*/
  for (i = 0; i < order; i++) {
    ia_append(samples,read_signed_bits(bitstream,bits_per_sample));
  }

  /*read the residual*/
  if (!FlacDecoder_read_residual(self,order,block_size,residuals))
    return 0;

  /*calculate subframe samples from warm-up samples and residual*/
  switch (order) {
  case 0:
    for (i = 0; i < residuals->size; i++) {
      ia_append(samples,
	       ia_getitem(residuals,i));
    }
    break;
  case 1:
    for (i = 0; i < residuals->size; i++) {
      ia_append(samples,
	       ia_getitem(samples,-1) +
	       ia_getitem(residuals,i));
    }
    break;
  case 2:
    for (i = 0; i < residuals->size; i++) {
      ia_append(samples,
	       (2 * ia_getitem(samples,-1)) -
	       ia_getitem(samples,-2) +
	       ia_getitem(residuals,i));
    }
    break;
  case 3:
    for (i = 0; i < residuals->size; i++) {
      ia_append(samples,
	       (3 * ia_getitem(samples,-1)) -
	       (3 * ia_getitem(samples,-2)) +
	       ia_getitem(samples,-3) +
	       ia_getitem(residuals,i));
    }
    break;
  case 4:
    for (i = 0; i < residuals->size; i++) {
      ia_append(samples,
	       (4 * ia_getitem(samples,-1)) -
	       (6 * ia_getitem(samples,-2)) +
	       (4 * ia_getitem(samples,-3)) -
	       ia_getitem(samples,-4) +
	       ia_getitem(residuals,i));
    }
    break;
  default:
    PyErr_SetString(PyExc_ValueError,"invalid FIXED subframe order");
    return 0;
  }

  return 1;
}

int FlacDecoder_read_lpc_subframe(decoders_FlacDecoder *self,
				  uint8_t order,
				  uint32_t block_size,
				  uint8_t bits_per_sample,
				  struct i_array *samples) {
  int i,j;
  Bitstream *bitstream = self->bitstream;
  uint32_t qlp_precision;
  uint32_t qlp_shift_needed;
  struct i_array tail;
  int64_t accumulator;

  struct i_array *qlp_coeffs = &(self->qlp_coeffs);
  struct i_array *residuals = &(self->residuals);

  ia_reset(residuals);
  ia_reset(samples);
  ia_reset(qlp_coeffs);

  /*read order number of warm-up samples*/
  for (i = 0; i < order; i++) {
    ia_append(samples,read_signed_bits(bitstream,bits_per_sample));
  }

  /*read QLP precision*/
  qlp_precision = read_bits(bitstream,4) + 1;

  /*read QLP shift needed*/
  qlp_shift_needed = read_bits(bitstream,5);

  /*read order number of QLP coefficients of size qlp_precision*/
  for (i = 0; i < order; i++) {
    ia_append(qlp_coeffs,read_signed_bits(bitstream,qlp_precision));
  }
  ia_reverse(qlp_coeffs);

  /*read the residual*/
  if (!FlacDecoder_read_residual(self,order,block_size,residuals))
    return 0;

  /*calculate subframe samples from warm-up samples and residual*/
  for (i = 0; i < residuals->size; i++) {
    accumulator = 0;
    ia_tail(&tail,samples,order);
    for (j = 0; j < qlp_coeffs->size; j++) {
      accumulator += (int64_t)ia_getitem(&tail,j) * (int64_t)ia_getitem(qlp_coeffs,j);
    }
    ia_append(samples,
	     (accumulator >> qlp_shift_needed) + ia_getitem(residuals,i));
  }

  return 1;
}

int FlacDecoder_read_residual(decoders_FlacDecoder *self,
			      uint8_t order,
			      uint32_t block_size,
			      struct i_array *residuals) {
  Bitstream *bitstream = self->bitstream;
  uint32_t coding_method = read_bits(bitstream,2);
  uint32_t partition_order = read_bits(bitstream,4);
  int total_partitions = 1 << partition_order;
  int partition;
  uint32_t rice_parameter;
  uint32_t partition_samples;
  uint32_t i;
  int32_t msb;
  int32_t lsb;
  int32_t value;

  ia_reset(residuals);

  for (partition = 0; partition < total_partitions; partition++) {
    if (partition == 0) {
      partition_samples = (block_size / (1 << partition_order)) - order;
    } else {
      partition_samples = block_size / (1 << partition_order);
    }

    switch (coding_method) {
    case 0:
      rice_parameter = read_bits(bitstream,4);
      break;
    case 1:
      rice_parameter = read_bits(bitstream,5);
      break;
    default:
      PyErr_SetString(PyExc_ValueError,"invalid partition coding method");
      return 0;
    }

    for (i = 0; i < partition_samples; i++) {
      msb = read_unary(bitstream,1);
      lsb = read_bits(bitstream,rice_parameter);
      value = (msb << rice_parameter) | lsb;
      if (value & 1) {
	value = -(value >> 1) - 1;
      } else {
	value = value >> 1;
      }

      ia_append(residuals,value);
    }
  }

  return 1;
}

void crc8(unsigned int byte, void *checksum) {
  const static uint32_t sumtable[0x100] =
    {0x00,0x07,0x0E,0x09,0x1C,0x1B,0x12,0x15,
     0x38,0x3F,0x36,0x31,0x24,0x23,0x2A,0x2D,
     0x70,0x77,0x7E,0x79,0x6C,0x6B,0x62,0x65,
     0x48,0x4F,0x46,0x41,0x54,0x53,0x5A,0x5D,
     0xE0,0xE7,0xEE,0xE9,0xFC,0xFB,0xF2,0xF5,
     0xD8,0xDF,0xD6,0xD1,0xC4,0xC3,0xCA,0xCD,
     0x90,0x97,0x9E,0x99,0x8C,0x8B,0x82,0x85,
     0xA8,0xAF,0xA6,0xA1,0xB4,0xB3,0xBA,0xBD,
     0xC7,0xC0,0xC9,0xCE,0xDB,0xDC,0xD5,0xD2,
     0xFF,0xF8,0xF1,0xF6,0xE3,0xE4,0xED,0xEA,
     0xB7,0xB0,0xB9,0xBE,0xAB,0xAC,0xA5,0xA2,
     0x8F,0x88,0x81,0x86,0x93,0x94,0x9D,0x9A,
     0x27,0x20,0x29,0x2E,0x3B,0x3C,0x35,0x32,
     0x1F,0x18,0x11,0x16,0x03,0x04,0x0D,0x0A,
     0x57,0x50,0x59,0x5E,0x4B,0x4C,0x45,0x42,
     0x6F,0x68,0x61,0x66,0x73,0x74,0x7D,0x7A,
     0x89,0x8E,0x87,0x80,0x95,0x92,0x9B,0x9C,
     0xB1,0xB6,0xBF,0xB8,0xAD,0xAA,0xA3,0xA4,
     0xF9,0xFE,0xF7,0xF0,0xE5,0xE2,0xEB,0xEC,
     0xC1,0xC6,0xCF,0xC8,0xDD,0xDA,0xD3,0xD4,
     0x69,0x6E,0x67,0x60,0x75,0x72,0x7B,0x7C,
     0x51,0x56,0x5F,0x58,0x4D,0x4A,0x43,0x44,
     0x19,0x1E,0x17,0x10,0x05,0x02,0x0B,0x0C,
     0x21,0x26,0x2F,0x28,0x3D,0x3A,0x33,0x34,
     0x4E,0x49,0x40,0x47,0x52,0x55,0x5C,0x5B,
     0x76,0x71,0x78,0x7F,0x6A,0x6D,0x64,0x63,
     0x3E,0x39,0x30,0x37,0x22,0x25,0x2C,0x2B,
     0x06,0x01,0x08,0x0F,0x1A,0x1D,0x14,0x13,
     0xAE,0xA9,0xA0,0xA7,0xB2,0xB5,0xBC,0xBB,
     0x96,0x91,0x98,0x9F,0x8A,0x8D,0x84,0x83,
     0xDE,0xD9,0xD0,0xD7,0xC2,0xC5,0xCC,0xCB,
     0xE6,0xE1,0xE8,0xEF,0xFA,0xFD,0xF4,0xF3};

  *((int*)checksum) = sumtable[*((int*)checksum) ^ byte];
}

void crc16(unsigned int byte, void *checksum) {
  const static uint32_t sumtable[0x100] =
    {0x0000,0x8005,0x800f,0x000a,0x801b,0x001e,0x0014,0x8011,
     0x8033,0x0036,0x003c,0x8039,0x0028,0x802d,0x8027,0x0022,
     0x8063,0x0066,0x006c,0x8069,0x0078,0x807d,0x8077,0x0072,
     0x0050,0x8055,0x805f,0x005a,0x804b,0x004e,0x0044,0x8041,
     0x80c3,0x00c6,0x00cc,0x80c9,0x00d8,0x80dd,0x80d7,0x00d2,
     0x00f0,0x80f5,0x80ff,0x00fa,0x80eb,0x00ee,0x00e4,0x80e1,
     0x00a0,0x80a5,0x80af,0x00aa,0x80bb,0x00be,0x00b4,0x80b1,
     0x8093,0x0096,0x009c,0x8099,0x0088,0x808d,0x8087,0x0082,
     0x8183,0x0186,0x018c,0x8189,0x0198,0x819d,0x8197,0x0192,
     0x01b0,0x81b5,0x81bf,0x01ba,0x81ab,0x01ae,0x01a4,0x81a1,
     0x01e0,0x81e5,0x81ef,0x01ea,0x81fb,0x01fe,0x01f4,0x81f1,
     0x81d3,0x01d6,0x01dc,0x81d9,0x01c8,0x81cd,0x81c7,0x01c2,
     0x0140,0x8145,0x814f,0x014a,0x815b,0x015e,0x0154,0x8151,
     0x8173,0x0176,0x017c,0x8179,0x0168,0x816d,0x8167,0x0162,
     0x8123,0x0126,0x012c,0x8129,0x0138,0x813d,0x8137,0x0132,
     0x0110,0x8115,0x811f,0x011a,0x810b,0x010e,0x0104,0x8101,
     0x8303,0x0306,0x030c,0x8309,0x0318,0x831d,0x8317,0x0312,
     0x0330,0x8335,0x833f,0x033a,0x832b,0x032e,0x0324,0x8321,
     0x0360,0x8365,0x836f,0x036a,0x837b,0x037e,0x0374,0x8371,
     0x8353,0x0356,0x035c,0x8359,0x0348,0x834d,0x8347,0x0342,
     0x03c0,0x83c5,0x83cf,0x03ca,0x83db,0x03de,0x03d4,0x83d1,
     0x83f3,0x03f6,0x03fc,0x83f9,0x03e8,0x83ed,0x83e7,0x03e2,
     0x83a3,0x03a6,0x03ac,0x83a9,0x03b8,0x83bd,0x83b7,0x03b2,
     0x0390,0x8395,0x839f,0x039a,0x838b,0x038e,0x0384,0x8381,
     0x0280,0x8285,0x828f,0x028a,0x829b,0x029e,0x0294,0x8291,
     0x82b3,0x02b6,0x02bc,0x82b9,0x02a8,0x82ad,0x82a7,0x02a2,
     0x82e3,0x02e6,0x02ec,0x82e9,0x02f8,0x82fd,0x82f7,0x02f2,
     0x02d0,0x82d5,0x82df,0x02da,0x82cb,0x02ce,0x02c4,0x82c1,
     0x8243,0x0246,0x024c,0x8249,0x0258,0x825d,0x8257,0x0252,
     0x0270,0x8275,0x827f,0x027a,0x826b,0x026e,0x0264,0x8261,
     0x0220,0x8225,0x822f,0x022a,0x823b,0x023e,0x0234,0x8231,
     0x8213,0x0216,0x021c,0x8219,0x0208,0x820d,0x8207,0x0202};
  uint32_t old_checksum = *((int*)checksum);

  *((int*)checksum) = (sumtable[(old_checksum >> 8) ^ byte] ^ (old_checksum << 8)) & 0xFFFF;
}

uint32_t read_utf8(Bitstream *stream) {
  uint32_t total_bytes = read_unary(stream,0);
  uint32_t value = read_bits(stream,7 - total_bytes);
  for (;total_bytes > 1;total_bytes--) {
    value = (value << 6) | (read_bits(stream,8) & 0x3F);
  }

  return value;
}
