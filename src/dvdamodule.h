#include <Python.h>
#include <dvd-audio.h>

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

static PyMethodDef dvdaMethods[] = {
    {NULL, NULL, 0, NULL}  /*sentinel*/
};

/*******************************
 *         DVD object          *
 *******************************/

typedef struct dvda_DVDA_s {
    PyObject_HEAD

    DVDA *dvda;
} dvda_DVDA;

static PyObject*
DVDA_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
DVDA_init(dvda_DVDA *self, PyObject *args, PyObject *kwds);

static void
DVDA_dealloc(dvda_DVDA *self);

static PyObject*
DVDA_titleset(dvda_DVDA *self, PyObject *args);

static PyMethodDef DVDA_methods[] = {
    {"titleset", (PyCFunction)DVDA_titleset,
     METH_VARARGS, "titleset(number) -> Titleset"},
    {NULL}
};

static PyObject*
DVDA_titlesets(dvda_DVDA *self, void *closure);

static PyGetSetDef DVDA_getseters[] = {
    {"titlesets",
     (getter)DVDA_titlesets, NULL, "title sets", NULL},
    {NULL}
};

static PyTypeObject dvda_DVDAType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dvda.DVDA",               /*tp_name*/
    sizeof(dvda_DVDA),         /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)DVDA_dealloc,  /*tp_dealloc*/
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
    "DVDA objects",            /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    DVDA_methods,              /* tp_methods */
    0,                         /* tp_members */
    DVDA_getseters,            /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)DVDA_init,       /* tp_init */
    0,                         /* tp_alloc */
    DVDA_new,                  /* tp_new */
};

/*******************************
 *       Titleset object       *
 *******************************/

typedef struct dvda_Titleset_s {
    PyObject_HEAD

    DVDA_Titleset *titleset;
} dvda_Titleset;

static PyObject*
Titleset_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
Titleset_init(dvda_Titleset *self, PyObject *args, PyObject *kwds);

static void
Titleset_dealloc(dvda_Titleset *self);

static PyObject*
Titleset_title(dvda_Titleset *self, PyObject *args);

static PyMethodDef Titleset_methods[] = {
    {"title", (PyCFunction)Titleset_title,
     METH_VARARGS, "title(number) -> Title"},
    {NULL}
};

static PyObject*
Titleset_titles(dvda_Titleset *self, void *closure);

static PyGetSetDef Titleset_getseters[] = {
    {"titles",
     (getter)Titleset_titles, NULL, "titles", NULL},
    {NULL}
};

static PyTypeObject dvda_TitlesetType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dvda.Titleset",           /*tp_name*/
    sizeof(dvda_Titleset),     /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Titleset_dealloc, /*tp_dealloc*/
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
    "Titleset objects",        /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Titleset_methods,          /* tp_methods */
    0,                         /* tp_members */
    Titleset_getseters,        /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Titleset_init,   /* tp_init */
    0,                         /* tp_alloc */
    Titleset_new,              /* tp_new */
};

/*******************************
 *        Title object         *
 *******************************/

typedef struct dvda_Title_s {
    PyObject_HEAD

    DVDA_Title *title;
} dvda_Title;

static PyObject*
Title_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
Title_init(dvda_Title *self, PyObject *args, PyObject *kwds);

static void
Title_dealloc(dvda_Title *self);

static PyObject*
Title_track(dvda_Title *self, PyObject *args);

static PyMethodDef Title_methods[] = {
    {"track", (PyCFunction)Title_track,
     METH_VARARGS, "track(number) -> Track"},
    {NULL}
};

static PyObject*
Title_tracks(dvda_Title *self, void *closure);

static PyObject*
Title_pts_length(dvda_Title *self, void *closure);

static PyGetSetDef Title_getseters[] = {
    {"tracks",
     (getter)Title_tracks, NULL, "tracks", NULL},
    {"pts_length",
     (getter)Title_pts_length, NULL, "length in PTS ticks", NULL},
    {NULL}
};

static PyTypeObject dvda_TitleType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dvda.Title",              /*tp_name*/
    sizeof(dvda_Title),        /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Title_dealloc, /*tp_dealloc*/
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
    "Title objects",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Title_methods,             /* tp_methods */
    0,                         /* tp_members */
    Title_getseters,           /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Title_init,      /* tp_init */
    0,                         /* tp_alloc */
    Title_new,                 /* tp_new */
};

/*******************************
 *        Track object         *
 *******************************/

typedef struct dvda_Track_s {
    PyObject_HEAD

    DVDA_Track *track;
} dvda_Track;

static PyObject*
Track_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
Track_init(dvda_Track *self, PyObject *args, PyObject *kwds);

static void
Track_dealloc(dvda_Track *self);

static PyObject*
Track_reader(dvda_Track *self, PyObject *args);

static PyMethodDef Track_methods[] = {
    {"reader", (PyCFunction)Track_reader,
     METH_NOARGS, "reader() -> TrackReader"},
    {NULL}
};

static PyObject*
Track_pts_index(dvda_Track *self, void *closure);

static PyObject*
Track_pts_length(dvda_Track *self, void *closure);

static PyObject*
Track_first_sector(dvda_Track *self, void *closure);

static PyObject*
Track_last_sector(dvda_Track *self, void *closure);

static PyGetSetDef Track_getseters[] = {
   {"pts_index",
    (getter)Track_pts_index, NULL, "PTS index", NULL},
   {"pts_length",
    (getter)Track_pts_length, NULL, "PTS length", NULL},
   {"first_sector",
    (getter)Track_first_sector, NULL, "first sector", NULL},
   {"last_sector",
    (getter)Track_last_sector, NULL, "last sector", NULL},
   {NULL}
};

static PyTypeObject dvda_TrackType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dvda.Track",              /*tp_name*/
    sizeof(dvda_Track),        /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Track_dealloc, /*tp_dealloc*/
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
    "Track objects",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Track_methods,             /* tp_methods */
    0,                         /* tp_members */
    Track_getseters,           /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Track_init,      /* tp_init */
    0,                         /* tp_alloc */
    Track_new,                 /* tp_new */
};

/*******************************
 *     TrackReader object      *
 *******************************/

typedef struct dvda_TrackReader_s {
    PyObject_HEAD

    int closed;
    DVDA_Track_Reader *reader;
    PyObject *audiotools_pcm;
} dvda_TrackReader;

static PyObject*
TrackReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
TrackReader_init(dvda_TrackReader *self, PyObject *args, PyObject *kwds);

static void
TrackReader_dealloc(dvda_TrackReader *self);

static PyObject*
TrackReader_read(dvda_TrackReader *self, PyObject *args);

static PyObject*
TrackReader_close(dvda_TrackReader *self, PyObject *args);

static PyMethodDef TrackReader_methods[] = {
    {"read", (PyCFunction)TrackReader_read,
     METH_VARARGS, "read(pcm_frames) -> FrameList"},
    {"close", (PyCFunction)TrackReader_close,
     METH_NOARGS, "close()"},
    {NULL}
};

static PyObject*
TrackReader_sample_rate(dvda_TrackReader *self, void *closure);

static PyObject*
TrackReader_bits_per_sample(dvda_TrackReader *self, void *closure);

static PyObject*
TrackReader_channels(dvda_TrackReader *self, void *closure);

static PyObject*
TrackReader_channel_mask(dvda_TrackReader *self, void *closure);

static PyObject*
TrackReader_total_pcm_frames(dvda_TrackReader *self, void *closure);

static PyObject*
TrackReader_codec(dvda_TrackReader *self, void *closure);

static PyGetSetDef TrackReader_getseters[] = {
    {"sample_rate",
     (getter)TrackReader_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)TrackReader_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)TrackReader_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)TrackReader_channel_mask, NULL, "channel mask", NULL},
    {"total_pcm_frames",
     (getter)TrackReader_total_pcm_frames, NULL, "total PCM frames", NULL},
    {"codec",
     (getter)TrackReader_codec, NULL, "codec", NULL},
    {NULL}
};

static PyTypeObject dvda_TrackReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dvda.TrackReader",        /*tp_name*/
    sizeof(dvda_TrackReader),  /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)TrackReader_dealloc, /*tp_dealloc*/
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
    "TrackReader objects",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    TrackReader_methods,       /* tp_methods */
    0,                         /* tp_members */
    TrackReader_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)TrackReader_init, /* tp_init */
    0,                         /* tp_alloc */
    TrackReader_new,           /* tp_new */
};
