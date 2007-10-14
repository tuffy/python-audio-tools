#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/*PCMStreamReader definitions*/
typedef struct {
  PyObject_HEAD
  PyObject *substream;        /*the Python file object to get new samples from*/
  int sample_size;            /*the size of each PCM sample, in bytes*/
  char unhandled_bytes[3];    /*any partial PCM samples*/
  int unhandled_bytes_length; /*how many partial PCM bytes we have*/
} pcmstream_PCMStreamReader;

static void PCMStreamReader_dealloc(pcmstream_PCMStreamReader* self);

static PyObject *PCMStreamReader_new(PyTypeObject *type, 
				     PyObject *args, PyObject *kwds);

static int PCMStreamReader_init(pcmstream_PCMStreamReader *self, 
				PyObject *args, PyObject *kwds);

static PyObject *PCMStreamReader_close(pcmstream_PCMStreamReader* self);

static PyObject *PCMStreamReader_tell(pcmstream_PCMStreamReader* self);

static PyObject *PCMStreamReader_read(pcmstream_PCMStreamReader* self, 
				      PyObject *args);

static PyObject *PCMStreamReader_get_sample_size(
    pcmstream_PCMStreamReader *self,
    void *closure);

static PyObject *pcm_to_string(PyObject *dummy, PyObject *args);

long char_to_16bit(unsigned char *s);
void _16bit_to_char(long i, unsigned char *s);

long char_to_24bit(unsigned char *s);
void _24bit_to_char(long i, unsigned char *s);

long char_to_8bit(unsigned char *s);
void _8bit_to_char(long i, unsigned char *s);


/*Resampler definitions*/

typedef struct {
  PyObject_HEAD
  SRC_STATE *src_state;
  int channels;
} pcmstream_Resampler;

static void Resampler_dealloc(pcmstream_Resampler* self);

static PyObject *Resampler_new(PyTypeObject *type, 
			       PyObject *args, PyObject *kwds);

static int Resampler_init(pcmstream_Resampler *self, 
			  PyObject *args, PyObject *kwds);

static PyObject *Resampler_process(pcmstream_Resampler* self, 
				   PyObject *args);

static PyMethodDef module_methods[] = {
  {"pcm_to_string",(PyCFunction)pcm_to_string,
   METH_VARARGS,"Converts PCM integers to a string of PCM data."},
  {NULL}
};

static PyGetSetDef PCMStreamReader_getseters[] = {
    {"sample_size", 
     (getter)PCMStreamReader_get_sample_size, 0,
     "sample size",
     NULL},
    {NULL}  /* Sentinel */
};

static PyMethodDef PCMStreamReader_methods[] = {
  {"close", (PyCFunction)PCMStreamReader_close,
   METH_NOARGS,"Closes the PCMStreamReader and substream"},
  {"tell", (PyCFunction)PCMStreamReader_tell,
   METH_NOARGS,"Returns the current position in the substream"},
  {"read", (PyCFunction)PCMStreamReader_read,
   METH_VARARGS,"Reads the given number of bits from the substream"},
  {NULL}
};

static PyMethodDef Resampler_methods[] = {
  {"process", (PyCFunction)Resampler_process,
   METH_VARARGS,"Processes PCM samples into the new sample rate"},
  {NULL}
};

static PyTypeObject pcmstream_PCMStreamReaderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmstream.PCMStreamReader", /*tp_name*/
    sizeof(pcmstream_PCMStreamReader), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)PCMStreamReader_dealloc, /*tp_dealloc*/
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
    "PCMStreamReader objects", /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    PCMStreamReader_methods,   /* tp_methods */
    0,                         /* tp_members */
    PCMStreamReader_getseters, /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)PCMStreamReader_init, /* tp_init */
    0,                         /* tp_alloc */
    PCMStreamReader_new,       /* tp_new */
};


static PyTypeObject pcmstream_ResamplerType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcmstream.Resampler", /*tp_name*/
    sizeof(pcmstream_Resampler), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Resampler_dealloc, /*tp_dealloc*/
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
    "Resampler objects",       /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    Resampler_methods,         /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Resampler_init,  /* tp_init */
    0,                         /* tp_alloc */
    Resampler_new,       /* tp_new */
};


#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
