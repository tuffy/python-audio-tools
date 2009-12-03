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


int FlacDecoder_init(decoders_FlacDecoder *self,
		     PyObject *args, PyObject *kwds) {
  return 0;
}

void FlacDecoder_dealloc(decoders_FlacDecoder *self) {

}

PyObject *FlacDecoder_new(PyTypeObject *type,
			  PyObject *args, PyObject *kwds) {
  decoders_FlacDecoder *self;

  self = (decoders_FlacDecoder *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}
