#include <Python.h>
#include "encoders.h"

PyMODINIT_FUNC initencoders(void) {
  PyObject* m;

  m = Py_InitModule3("encoders", module_methods,
		     "Low-level audio format encoders");

}

PyObject *encoders_write_bits(PyObject *dummy, PyObject *args) {
  int context;
  int value;

  if (!PyArg_ParseTuple(args,"ii",&context,&value))
    return NULL;

  return Py_BuildValue("i",write_bits_table[context][value]);
}


PyObject *encoders_write_unary(PyObject *dummy, PyObject *args) {
  int context;
  int value;

  if (!PyArg_ParseTuple(args,"ii",&context,&value))
    return NULL;

  return Py_BuildValue("i",write_unary_table[context][value]);
}

#include "bitstream.c"
