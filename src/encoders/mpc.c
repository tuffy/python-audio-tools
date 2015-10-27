#include "../pcmreader.h"

#ifndef STANDALONE
PyObject*
encoders_encode_mpc(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    Py_INCREF(Py_None);
    return Py_None;
}
#endif

#ifdef STANDALONE
int main(int argc, char *argv[])
{
    return 0;
}
#endif
