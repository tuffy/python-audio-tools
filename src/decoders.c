#include <Python.h>
#include "decoders.h"

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

PyObject *decoders_read_bits(PyObject *dummy, PyObject *args) {
  int context;
  int bits;

  if (!PyArg_ParseTuple(args,"ii",&context,&bits))
    return NULL;

  return Py_BuildValue("i",read_bits_table[context][bits - 1]);
}

PyObject *decoders_read_unary(PyObject *dummy, PyObject *args) {
  int context;
  int stop_bit;

  if (!PyArg_ParseTuple(args, "ii", &context,&stop_bit))
    return NULL;

  return Py_BuildValue("i",read_unary_table[context][stop_bit]);
}

#include "decoders_flac.c"

#include "bitstream.c"
#include "array.c"

