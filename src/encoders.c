#include <Python.h>
#include "encoders.h"

PyMODINIT_FUNC initencoders(void) {
  PyObject* m;

  m = Py_InitModule3("encoders", module_methods,
		     "Low-level audio format encoders");

}

PyObject *encoders_write_bits(PyObject *dummy, PyObject *args) {
  return NULL;
}

PyObject *encoders_write_unary(PyObject *dummy, PyObject *args) {
  return NULL;
}

#include "bitstream.c"
