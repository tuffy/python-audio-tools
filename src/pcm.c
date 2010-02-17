#include <Python.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

#include "pcm.h"

PyMODINIT_FUNC initpcm(void) {
    PyObject* m;

    pcm_FrameListType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&pcm_FrameListType) < 0)
      return;

    m = Py_InitModule3("pcm", module_methods,
                       "A PCM FrameList handling module.");

    Py_INCREF(&pcm_FrameListType);
    PyModule_AddObject(m, "FrameList",
		       (PyObject *)&pcm_FrameListType);
}

void FrameList_dealloc(pcm_FrameList* self) {
  self->ob_type->tp_free((PyObject*)self);
}

PyObject *FrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  pcm_FrameList *self;

  self = (pcm_FrameList *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

int FrameList_init(pcm_FrameList *self, PyObject *args, PyObject *kwds) {
  return 0;
}

PyObject* FrameList_frames(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",0);
}

PyObject* FrameList_channels(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",0);
}

PyObject* FrameList_bits_per_sample(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",0);
}

PyObject* FrameList_signed(pcm_FrameList *self, void* closure) {
  return Py_BuildValue("i",0);
}
