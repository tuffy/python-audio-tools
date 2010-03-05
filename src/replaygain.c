#include <Python.h>
#include "replaygain.h"
#include "pcm.h"

PyMethodDef module_methods[] = {
  {NULL}
};

PyMethodDef ReplayGain_methods[] = {
  {"update",(PyCFunction)ReplayGain_update,
   METH_VARARGS,"Updates the ReplayGain object with a FloatFrameList"},
  {"title_gain",(PyCFunction)ReplayGain_title_gain,
   METH_NOARGS,"Returns a (title gain,title peak) tuple and resets"},
  {"album_gain",(PyCFunction)ReplayGain_album_gain,
   METH_NOARGS,"Returns an (album gain,album peak) tuple"},
  {NULL}
};

PyTypeObject replaygain_ReplayGainType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "replaygain.ReplayGain",   /*tp_name*/
    sizeof(replaygain_ReplayGain), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ReplayGain_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "ReplayGain objects",      /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,                         /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    ReplayGain_methods,        /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ReplayGain_init, /* tp_init */
    0,                         /* tp_alloc */
    ReplayGain_new,            /* tp_new */
};

void ReplayGain_dealloc(replaygain_ReplayGain* self) {
  self->ob_type->tp_free((PyObject*)self);
}

PyObject *ReplayGain_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  replaygain_ReplayGain *self;

  self = (replaygain_ReplayGain *)type->tp_alloc(type, 0);

  return (PyObject *)self;
}

int ReplayGain_init(replaygain_ReplayGain *self, PyObject *args, PyObject *kwds) {
  long sample_rate;

  if (!PyArg_ParseTuple(args,"l",&sample_rate))
    return -1;

  return 0;
}

PyObject* ReplayGain_update(replaygain_ReplayGain *self, PyObject *args) {
  PyObject *floatframelist_obj = NULL;
  PyObject *channels_obj = NULL;
  PyObject *channel_l_obj = NULL;
  PyObject *channel_r_obj = NULL;
  PyObject *pcm_obj = NULL;
  PyObject *floatframelist_type_obj = NULL;
  pcm_FloatFrameList *channel_l;
  pcm_FloatFrameList *channel_r;
  long channel_count;

  /*receive a (presumably) FloatFrameList from our arguments*/
  if (!PyArg_ParseTuple(args,"O",&floatframelist_obj))
    return NULL;

  /*get floatframelist.channels attrib and convert it to an integer*/
  if ((channels_obj = PyObject_GetAttrString(floatframelist_obj,"channels")) == NULL)
    goto error;
  if (((channel_count = PyInt_AsLong(channels_obj)) == -1) && PyErr_Occurred())
    goto error;

  /*call floatframelist.channel(0) and floatframelist.channel(1)*/
  switch (channel_count) {
  case 1:
     if ((channel_l_obj = PyObject_CallMethod(floatframelist_obj,"channel","(i)",0)) == NULL)
      goto error;
     if ((channel_r_obj = PyObject_CallMethod(floatframelist_obj,"channel","(i)",0)) == NULL)
       goto error;
     break;
  case 2:
    if ((channel_l_obj = PyObject_CallMethod(floatframelist_obj,"channel","(i)",0)) == NULL)
      goto error;
    if ((channel_r_obj = PyObject_CallMethod(floatframelist_obj,"channel","(i)",1)) == NULL)
      goto error;
    break;
  default:
    PyErr_SetString(PyExc_ValueError,"channel count must be 1 or 2");
    goto error;
  }

  /*ensure channel_l_obj and channel_r_obj are FloatFrameLists*/
  if ((pcm_obj = PyImport_ImportModule("audiotools.pcm")) == NULL)
    goto error;
  if ((floatframelist_type_obj = PyObject_GetAttrString(pcm_obj,"FloatFrameList")) == NULL)
    goto error;
  if (channel_l_obj->ob_type != (PyTypeObject*)floatframelist_type_obj) {
    PyErr_SetString(PyExc_TypeError,"channel 0 must be a FloatFrameList");
    goto error;
  }
  if (channel_r_obj->ob_type != (PyTypeObject*)floatframelist_type_obj) {
    PyErr_SetString(PyExc_TypeError,"channel 1 must be a FloatFrameList");
    goto error;
  }

  channel_l = (pcm_FloatFrameList*)channel_l_obj;
  channel_r = (pcm_FloatFrameList*)channel_r_obj;

  /*perform actual gain analysis on channels*/


  /*clean up Python objects and return None*/
  Py_XDECREF(channels_obj);
  Py_XDECREF(channel_l_obj);
  Py_XDECREF(channel_r_obj);
  Py_XDECREF(pcm_obj);
  Py_XDECREF(floatframelist_type_obj);
  Py_INCREF(Py_None);
  return Py_None;
 error:
  Py_XDECREF(channels_obj);
  Py_XDECREF(channel_l_obj);
  Py_XDECREF(channel_r_obj);
  Py_XDECREF(pcm_obj);
  Py_XDECREF(floatframelist_type_obj);
  return NULL;
}

PyObject* ReplayGain_title_gain(replaygain_ReplayGain *self) {
  /*FIXME - reset state and return real value*/
  return Py_BuildValue("(d,d)",0.0,1.0);
}

PyObject* ReplayGain_album_gain(replaygain_ReplayGain *self) {
  /*FIXME - return real value*/
  return Py_BuildValue("(d,d)",0.0,1.0);
}


PyMODINIT_FUNC initreplaygain(void) {
  PyObject* m;

  replaygain_ReplayGainType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&replaygain_ReplayGainType) < 0)
    return;

  m = Py_InitModule3("replaygain", module_methods,
		     "A ReplayGain calculation module.");

  Py_INCREF(&replaygain_ReplayGainType);
  PyModule_AddObject(m, "ReplayGain",
		     (PyObject *)&replaygain_ReplayGainType);
}
