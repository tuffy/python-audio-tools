#include <openssl/md5.h>

#define MIN(x,y) ((x) < (y) ? (x) : (y))
#define MAX(x,y) ((x) > (y) ? (x) : (y))

static PyObject* encoders_encode_flac(PyObject *dummy, PyObject *args) {
  char *filename;
  FILE *file;
  Bitstream *stream;
  PyObject *pcmreader_obj;
  struct pcm_reader *reader;
  struct flac_STREAMINFO streaminfo;
  MD5_CTX md5sum;

  struct ia_array samples;

  int block_size;

  /*extract a filename, PCMReader-compatible object and encoding options:
    blocksize int*/
  if (!PyArg_ParseTuple(args,"sOi",&filename,&pcmreader_obj,&block_size))
    return NULL;

  if (block_size <= 0) {
    PyErr_SetString(PyExc_ValueError,"blocksize must be positive");
    return NULL;
  }

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

  MD5_Init(&md5sum);
  pcmr_add_callback(reader,md5_update,&md5sum);

  stream = bs_open(file);
  bs_add_callback(stream,flac_crc8,&(streaminfo.crc8));
  bs_add_callback(stream,flac_crc16,&(streaminfo.crc16));

  /*fill streaminfo with some placeholder values*/
  streaminfo.minimum_block_size = 0xFFFF;
  streaminfo.maximum_block_size = 0;
  streaminfo.minimum_frame_size = 0xFFFFFF;
  streaminfo.maximum_frame_size = 0;
  streaminfo.sample_rate = reader->sample_rate;
  streaminfo.channels = reader->channels;
  streaminfo.bits_per_sample = reader->bits_per_sample;
  streaminfo.total_samples = 0;
  memcpy(streaminfo.md5sum,
	 "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
	 16);
  streaminfo.crc8 = streaminfo.crc16 = 0;
  streaminfo.total_frames = 0;

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
  MD5_Final(streaminfo.md5sum,&md5sum);
  fseek(stream->file, 4 + 4, SEEK_SET);
  FlacEncoder_write_streaminfo(stream,streaminfo);


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
  uint32_t i;
  long startpos;
  long framesize;

  streaminfo->crc8 = streaminfo->crc16 = 0;

  startpos = ftell(bs->file);

  FlacEncoder_write_frame_header(bs,streaminfo,samples);

  for (i = 0; i < samples->size; i++)
    FlacEncoder_write_verbatim_subframe(bs,
    					streaminfo->bits_per_sample,
    					iaa_getitem(samples,i));

  byte_align_w(bs);

  /*write CRC-16*/
  write_bits(bs, 16, streaminfo->crc16);

  /*update streaminfo with new values*/
  framesize = ftell(bs->file) - startpos;

  streaminfo->minimum_block_size = MIN(streaminfo->minimum_block_size,
				       iaa_getitem(samples,0)->size);
  streaminfo->maximum_block_size = MAX(streaminfo->maximum_block_size,
				       iaa_getitem(samples,0)->size);
  streaminfo->minimum_frame_size = MIN(streaminfo->minimum_frame_size,
				       framesize);
  streaminfo->maximum_frame_size = MAX(streaminfo->maximum_frame_size,
				       framesize);
  streaminfo->total_samples += iaa_getitem(samples,0)->size;
  streaminfo->total_frames++;

  return 1;
}

void FlacEncoder_write_frame_header(Bitstream *bs,
				    struct flac_STREAMINFO *streaminfo,
				    struct ia_array *samples) {
  int block_size_bits;
  int sample_rate_bits;
  int channel_assignment;
  int bits_per_sample_bits;
  int block_size = iaa_getitem(samples,0)->size;

  /*determine the block size bits from the given amount of samples*/
  switch (block_size) {
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
    else
      block_size_bits = 0x0;
    break;
  }

  /*determine sample rate bits from streaminfo*/
  switch (streaminfo->sample_rate) {
  case 88200:  sample_rate_bits = 0x1; break;
  case 176400: sample_rate_bits = 0x2; break;
  case 192000: sample_rate_bits = 0x3; break;
  case 8000:   sample_rate_bits = 0x4; break;
  case 16000:  sample_rate_bits = 0x5; break;
  case 22050:  sample_rate_bits = 0x6; break;
  case 24000:  sample_rate_bits = 0x7; break;
  case 32000:  sample_rate_bits = 0x8; break;
  case 44100:  sample_rate_bits = 0x9; break;
  case 48000:  sample_rate_bits = 0xA; break;
  case 96000:  sample_rate_bits = 0xB; break;
  default:
    if ((streaminfo->sample_rate <= 255000) &&
	((streaminfo->sample_rate % 1000) == 0))
      sample_rate_bits = 0xC;
    else if ((streaminfo->sample_rate <= 655350) &&
	     ((streaminfo->sample_rate % 10) == 0))
      sample_rate_bits = 0xE;
    else if (streaminfo->sample_rate <= 0xFFFF)
      sample_rate_bits = 0xF;
    else
      sample_rate_bits = 0x0;
    break;
  }

  /*FIXME - channel assignment should be passed in from write_frame*/
  channel_assignment = streaminfo->channels - 1;

  /*determine bits-per-sample bits from streaminfo*/
  switch (streaminfo->bits_per_sample) {
  case 8:  bits_per_sample_bits = 0x1; break;
  case 12: bits_per_sample_bits = 0x2; break;
  case 16: bits_per_sample_bits = 0x4; break;
  case 20: bits_per_sample_bits = 0x5; break;
  case 24: bits_per_sample_bits = 0x6; break;
  default: bits_per_sample_bits = 0x0; break;
  }

  /*once the four bits-encoded fields are set, write the actual header*/
  write_bits(bs, 14, 0x3FFE);              /*sync code*/
  write_bits(bs, 1, 0);                    /*reserved*/
  write_bits(bs, 1, 0);                    /*blocking strategy*/
  write_bits(bs, 4, block_size_bits);      /*block size*/
  write_bits(bs, 4, sample_rate_bits);     /*sample rate*/
  write_bits(bs, 4, channel_assignment);   /*channel assignment*/
  write_bits(bs, 3, bits_per_sample_bits); /*bits per sample*/
  write_bits(bs, 1, 0);                    /*padding*/

  /*frame number is taken from total_frames in streaminfo*/
  write_utf8(bs, streaminfo->total_frames);  /*FIXME - should be UTF-8*/

  /*if block_size_bits are 0x6 or 0x7, write a PCM frames field*/
  if (block_size_bits == 0x6)
    write_bits(bs, 8, block_size - 1);
  else if (block_size_bits == 0x7)
    write_bits(bs, 16, block_size - 1);

  /*if sample rate is unusual, write one of the three sample rate fields*/
  if (sample_rate_bits == 0xC)
    write_bits(bs, 8, streaminfo->sample_rate / 1000);
  else if (sample_rate_bits == 0xD)
    write_bits(bs, 16, streaminfo->sample_rate);
  else if (sample_rate_bits == 0xE)
    write_bits(bs, 16, streaminfo->sample_rate / 10);

  /*write CRC-8*/
  write_bits(bs, 8, streaminfo->crc8);
}

void FlacEncoder_write_constant_subframe(Bitstream *bs,
					 int bits_per_sample,
					 int32_t sample) {
  /*write subframe header*/
  write_bits(bs, 1, 0);
  write_bits(bs, 6, 0);
  write_bits(bs, 1, 0);

  /*write subframe sample*/
  write_signed_bits(bs, bits_per_sample, sample);
}

void FlacEncoder_write_verbatim_subframe(Bitstream *bs,
					 int bits_per_sample,
					 struct i_array *samples) {
  uint32_t i;

  /*write subframe header*/
  write_bits(bs, 1, 0);
  write_bits(bs, 6, 1);
  write_bits(bs, 1, 0);

  /*write subframe samples*/
  for (i = 0; i < samples->size; i++)
    write_signed_bits(bs, bits_per_sample, ia_getitem(samples,i));
}

void write_utf8(Bitstream *stream, unsigned int value) {
  if ((value >= 0) && (value <= 0x7F)) {
    /*1 byte UTF-8 sequence*/
    write_bits(stream,8,value);
  } else if ((value >= 0x80) && (value <= 0x7FF)) {
    /*2 byte UTF-8 sequence*/
    write_unary(stream,0,2);
    write_bits(stream,5,value >> 6);
    write_unary(stream,0,1);
    write_bits(stream,6,value & 0x3F);
  } else if ((value >= 0x800) && (value <= 0xFFFF)) {
    /*3 byte UTF-8 sequence*/
    write_unary(stream,0,3);
    write_bits(stream,4,value >> 12);
    write_unary(stream,0,1);
    write_bits(stream,6,(value >> 6) & 0x3F);
    write_unary(stream,0,1);
    write_bits(stream,6,value & 0x3F);
  } else if ((value >= 0x10000) && (value <= 0xFFFFF)) {
    /*4 byte UTF-8 sequence*/
    write_unary(stream,0,4);
    write_bits(stream,3,value >> 18);
    write_unary(stream,0,1);
    write_bits(stream,6,(value >> 12) & 0x3F);
    write_unary(stream,0,1);
    write_bits(stream,6,(value >> 6) & 0x3F);
    write_unary(stream,0,1);
    write_bits(stream,6,value & 0x3F);
  }
}

void md5_update(void *data, unsigned char *buffer, unsigned long len) {
  MD5_Update((MD5_CTX*)data, (const void*)buffer, len);
}

#include "flac_crc.c"

