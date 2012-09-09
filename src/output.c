#include <Python.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

PyMethodDef module_methods[] = {
    {NULL}
};

#ifdef CORE_AUDIO
extern PyTypeObject output_CoreAudioType;
#endif

PyMODINIT_FUNC
initoutput(void)
{
    PyObject* m;

#ifdef CORE_AUDIO
    output_CoreAudioType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&output_CoreAudioType) < 0)
        return;
#endif

    m = Py_InitModule3("output", module_methods,
                       "System-specific audio output");

#ifdef CORE_AUDIO
    Py_INCREF(&output_CoreAudioType);
    PyModule_AddObject(m, "CoreAudio",
                       (PyObject *)&output_CoreAudioType);
#else
    /*to avoid an unused variable warning if no output types are present*/
    (void)m;
#endif
}
