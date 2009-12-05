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

#include "decoders_flac.c"

#include "bitstream.c"

