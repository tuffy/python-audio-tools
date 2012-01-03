#include <Python.h>
#include "prot.h"

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

extern PyTypeObject prot_CPPMDecoderType;

PyMODINIT_FUNC
initprot(void)
{
    PyObject* m;

    prot_CPPMDecoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&prot_CPPMDecoderType) < 0)
        return;

    m = Py_InitModule3("prot", module_methods,
                       "Low-level protection handlers");

    Py_INCREF(&prot_CPPMDecoderType);
    PyModule_AddObject(m, "CPPMDecoder",
                       (PyObject *)&prot_CPPMDecoderType);
}
