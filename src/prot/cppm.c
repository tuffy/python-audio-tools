#include "cppm.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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

int
CPPMDecoder_init(prot_CPPMDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    return 0;
}

void
CPPMDecoder_dealloc(prot_CPPMDecoder *self)
{
    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
CPPMDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    prot_CPPMDecoder *self;

    self = (prot_CPPMDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}
