#include "mod_cppm.h"

int
CPPMDecoder_init(decoders_CPPMDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    char *mkb_file;
    char *dvda_device;

    self->decoder.media_type = 0;
    self->decoder.media_key = 0;
    self->decoder.id_album_media = 0;

    if (!PyArg_ParseTuple(args, "ss", &dvda_device, &mkb_file))
        return -1;

    /*initialize the decoder from the device path and mkb_file path*/
    switch (cppm_init(&(self->decoder), dvda_device, mkb_file)) {
    case -1: /*I/O error*/
        PyErr_SetFromErrno(PyExc_IOError);
        return -1;
    case -2: /*unsupported protection type*/
        PyErr_SetString(PyExc_ValueError, "unsupported protection type");
        return -1;
    default: /*all okay*/
        break;
    }

    return 0;
}

void
CPPMDecoder_dealloc(decoders_CPPMDecoder *self)
{
    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
CPPMDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_CPPMDecoder *self;

    self = (decoders_CPPMDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
CPPMDecoder_media_type(decoders_CPPMDecoder *self, void *closure) {
    return Py_BuildValue("i", self->decoder.media_type);
}

static PyObject*
CPPMDecoder_media_key(decoders_CPPMDecoder *self, void *closure) {
    return Py_BuildValue("K", self->decoder.media_key);
}

static PyObject*
CPPMDecoder_id_album_media(decoders_CPPMDecoder *self, void *closure) {
    return Py_BuildValue("K", self->decoder.id_album_media);
}

static PyObject*
CPPMDecoder_decode(decoders_CPPMDecoder *self, PyObject *args) {
    char* input_buffer;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t input_len;
#else
    int input_len;
#endif
    uint8_t* output_buffer;
    int output_len;
    PyObject* decoded;

    if (!PyArg_ParseTuple(args, "s#", &input_buffer, &input_len))
        return NULL;

    if (input_len % DVDCPXM_BLOCK_SIZE) {
        PyErr_SetString(PyExc_ValueError,
                        "encoded block must be a multiple of 2048");
        return NULL;
    }

    output_len = input_len;
    output_buffer = malloc(sizeof(uint8_t) * output_len);
    memcpy(output_buffer, input_buffer, input_len);

    cppm_decrypt(&(self->decoder),
                 output_buffer,
                 output_len / DVDCPXM_BLOCK_SIZE,
                 1);

    decoded = PyString_FromStringAndSize((char *)output_buffer,
                                         (Py_ssize_t)output_len);
    free(output_buffer);
    return decoded;
}
