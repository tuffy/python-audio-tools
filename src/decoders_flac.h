struct flac_STREAMINFO {
  uint16_t minimum_block_size;
  uint16_t maximum_block_size;
  uint32_t minimum_frame_size;
  uint32_t maximum_frame_size;
  uint32_t sample_rate;
  uint8_t channels;
  uint8_t bits_per_sample;
  uint64_t total_samples;
  unsigned char md5sum[16];
};

struct flac_frame_header {
  uint8_t blocking_strategy;
  uint32_t block_size;
  uint32_t sample_rate;
  uint8_t channel_assignment;
  uint8_t channel_count;
  uint8_t bits_per_sample;
  uint64_t frame_number;
};

typedef enum {FLAC_SUBFRAME_CONSTANT,
	      FLAC_SUBFRAME_VERBATIM,
	      FLAC_SUBFRAME_FIXED,
	      FLAC_SUBFRAME_LPC} flac_subframe_type;

struct flac_subframe_header {
  flac_subframe_type type;
  uint8_t order;
  uint8_t wasted_bits_per_sample;
};

typedef struct {
  PyObject_HEAD
  char* filename;

  FILE* file;
  Bitstream* bitstream;

  struct flac_STREAMINFO streaminfo;
} decoders_FlacDecoder;

static PyObject *FlacDecoder_sample_rate(decoders_FlacDecoder *self,
					 void *closure);
static PyObject *FlacDecoder_bits_per_sample(decoders_FlacDecoder *self,
					     void *closure);

static PyObject *FlacDecoder_channels(decoders_FlacDecoder *self,
				      void *closure);

PyObject *FLACDecoder_read(decoders_FlacDecoder* self,
			   PyObject *args);

int FlacDecoder_init(decoders_FlacDecoder *self,
		     PyObject *args, PyObject *kwds);

PyGetSetDef FlacDecoder_getseters[] = {
  {"sample_rate",
   (getter)FlacDecoder_sample_rate, NULL, "sample rate", NULL},
  {"bits_per_sample",
   (getter)FlacDecoder_bits_per_sample, NULL, "bits per sample", NULL},
  {"channels",
   (getter)FlacDecoder_channels, NULL, "channels", NULL},
  {NULL}
};

PyMethodDef FlacDecoder_methods[] = {
  {"read", (PyCFunction)FLACDecoder_read,
   METH_VARARGS,"Reads the given number of bytes from the FLAC file, if possible"},
  {NULL}
};

void FlacDecoder_dealloc(decoders_FlacDecoder *self);

PyObject *FlacDecoder_new(PyTypeObject *type,
			  PyObject *args, PyObject *kwds);

int FlacDecoder_read_metadata(decoders_FlacDecoder *self);

int FlacDecoder_read_frame_header(decoders_FlacDecoder *self,
				  struct flac_frame_header *header);

int FlacDecoder_read_subframe_header(decoders_FlacDecoder *self,
				     struct flac_subframe_header *subframe_header);

int FlacDecoder_read_subframe(decoders_FlacDecoder *self,
			      uint32_t block_size,
			      uint8_t bits_per_sample);

int FlacDecoder_read_fixed_subframe(decoders_FlacDecoder *self,
				    uint8_t order,
				    uint32_t block_size,
				    uint8_t bits_per_sample);

int FlacDecoder_read_residual(decoders_FlacDecoder *self,
			      uint8_t order,
			      uint32_t block_size);

#ifdef IS_PY3K

static PyTypeObject decoders_FlacDecoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "decoders.FlacDecoder",     /* tp_name */
    sizeof(decoders_FlacDecoder), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)FlacDecoders_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
        Py_TPFLAGS_BASETYPE,   /* tp_flags */
    "FlacDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    FlacDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    FlacDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FlacDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    FlacDecoder_new,       /* tp_new */
};

#else

PyTypeObject decoders_FlacDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.FlacDecoder",    /*tp_name*/
    sizeof(decoders_FlacDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FlacDecoder_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "FlacDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    FlacDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    FlacDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FlacDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    FlacDecoder_new,           /* tp_new */
};

#endif
