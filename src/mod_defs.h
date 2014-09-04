/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

#if PY_MAJOR_VERSION >= 3

#define MOD_ERROR_VAL NULL
#define MOD_SUCCESS_VAL(val) val
#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
#define MOD_DEF(ob, name, doc, methods) \
        static struct PyModuleDef moduledef = { \
            PyModuleDef_HEAD_INIT, name, doc, -1, methods \
            }; \
            ob = PyModule_Create(&moduledef);

#else

#define MOD_ERROR_VAL
#define MOD_SUCCESS_VAL(val)
#define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
#define MOD_DEF(ob, name, doc, methods) \
        ob = Py_InitModule3(name, methods, doc);

#endif
