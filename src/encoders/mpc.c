#include "../libmpcpsy/libmpcpsy.h"
#include "../libmpcenc/libmpcenc.h"
#include "../pcmreader.h"

static void
encode_mpc_file(char *filename,
                struct PCMReader *pcmreader)
{
    PsyModel m;
    mpc_encoder_t e;

    // initialize tables
    m.SCF_Index_L = e.SCF_Index_L;
    m.SCF_Index_R = e.SCF_Index_R;
    Init_Psychoakustik(&m);
}

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
