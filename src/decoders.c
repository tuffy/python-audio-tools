#include <Python.h>
#include "decoders.h"
#include "bitstream.h"

PyMODINIT_FUNC initdecoders(void) {
    PyObject* m;

    decoders_FlacDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&decoders_FlacDecoderType) < 0)
      return;

    m = Py_InitModule3("decoders", module_methods,
                       "Low-level audio format decoders");

    Py_INCREF(&decoders_FlacDecoderType);
    PyModule_AddObject(m, "FlacDecoder",
		       (PyObject *)&decoders_FlacDecoderType);
}


int FlacDecoder_init(decoders_FlacDecoder *self,
		     PyObject *args, PyObject *kwds) {
  char* filename;

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

  if (!FlacDecoder_read_metadata(self)) {
    return -1;
  }

  return 0;
}

void FlacDecoder_dealloc(decoders_FlacDecoder *self) {
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

#include "bitstream.c"

