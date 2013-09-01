#include <Python.h>
#include <cdio/cdda.h>
#include <cdio/paranoia.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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

#define CD_IMAGE 1 << 3
#define DEVICE_FILE 0
#define CUE_FILE 1
#define BIN_FILE 2
#define TOC_FILE 3
#define NRG_FILE 4

/*audiotools.cdio.CDDA object*/
typedef struct {
    PyObject_HEAD
    cdrom_drive_t *cdrom_drive;
    cdrom_paranoia_t *paranoia;
    PyObject *pcm_module;
} cdio_CDDAObject;

static void
CDDA_dealloc(cdio_CDDAObject* self);

static PyObject*
CDDA_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
CDDA_init(cdio_CDDAObject *self, PyObject *args, PyObject *kwds);

static PyObject*
CDDA_total_tracks(cdio_CDDAObject* self);

static PyObject*
CDDA_track_offsets(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_read_sector(cdio_CDDAObject* self);

static PyObject*
CDDA_read_sectors(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_first_sector(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_last_sector(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_track_type(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_seek(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_set_speed(cdio_CDDAObject* self, PyObject *args);

static PyObject*
CDDA_length_in_seconds(cdio_CDDAObject* self);

static PyObject*
set_read_callback(PyObject *dummy, PyObject *args);

void
read_sector_callback(long int i, paranoia_cb_mode_t mode);

static PyObject*
cdio_identify_cdrom(PyObject *dummy, PyObject *args);

static PyMethodDef CDDA_methods[] = {
    {"total_tracks", (PyCFunction)CDDA_total_tracks,
     METH_NOARGS, "Returns the total number of tracks on the disc"},
    {"track_offsets", (PyCFunction)CDDA_track_offsets,
     METH_VARARGS, "Returns the starting and ending LSNs for the given track"},
    {"read_sector", (PyCFunction)CDDA_read_sector,
     METH_NOARGS, "Returns a sector at the current position as a string"},
    {"read_sectors", (PyCFunction)CDDA_read_sectors,
     METH_VARARGS,
     "Returns a number of sectors starting at the current position"},
    {"first_sector", (PyCFunction)CDDA_first_sector,
     METH_NOARGS, "Returns the first sector on the disc"},
    {"last_sector", (PyCFunction)CDDA_last_sector,
     METH_NOARGS, "Returns the last sector on the disc"},
    {"track_type", (PyCFunction)CDDA_track_type,
     METH_VARARGS, "Returns the type of the given track"},
    {"seek", (PyCFunction)CDDA_seek,
     METH_VARARGS, "Seeks to a specific LSN"},
    {"set_speed", (PyCFunction)CDDA_set_speed,
     METH_VARARGS, "Sets the speed of the drive"},
    {"length_in_seconds", (PyCFunction)CDDA_length_in_seconds,
     METH_NOARGS, "Returns the total length of the disc in seconds"},
    {NULL}  /* Sentinel */
};


/*audiotools.cdio.CDImage object*/
typedef struct {
    PyObject_HEAD

    CdIo_t* image;
    lsn_t current_sector;

    PyObject *pcm_module;
} cdio_CDImage;

static PyObject*
CDImage_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
CDImage_init(cdio_CDImage *self, PyObject *args, PyObject *kwds);

static void
CDImage_dealloc(cdio_CDImage* self);

static PyObject*
CDImage_total_tracks(cdio_CDImage* self);

static PyObject*
CDImage_track_offsets(cdio_CDImage* self, PyObject *args);

static PyObject*
CDImage_read_sector(cdio_CDImage* self);

static PyObject*
CDImage_read_sectors(cdio_CDImage* self, PyObject *args);

static PyObject*
CDImage_first_sector(cdio_CDImage* self, PyObject *args);

static PyObject*
CDImage_last_sector(cdio_CDImage* self, PyObject *args);

static PyObject*
CDImage_track_type(cdio_CDImage* self, PyObject *args);

static PyObject*
CDImage_seek(cdio_CDImage* self, PyObject *args);

static PyObject*
CDImage_length_in_seconds(cdio_CDImage* self);


static PyMethodDef CDImage_methods[] = {
    {"total_tracks", (PyCFunction)CDImage_total_tracks,
     METH_NOARGS, "Returns the total number of tracks on the disc"},
    {"track_offsets", (PyCFunction)CDImage_track_offsets,
     METH_VARARGS, "Returns the starting and ending LSNs for the given track"},
    {"read_sector", (PyCFunction)CDImage_read_sector,
     METH_NOARGS, "Returns a sector at the current position as a string"},
    {"read_sectors", (PyCFunction)CDImage_read_sectors,
     METH_VARARGS,
     "Returns a number of sectors starting at the current position"},
    {"first_sector", (PyCFunction)CDImage_first_sector,
     METH_NOARGS, "Returns the first sector on the disc"},
    {"last_sector", (PyCFunction)CDImage_last_sector,
     METH_NOARGS, "Returns the last sector on the disc"},
    {"track_type", (PyCFunction)CDImage_track_type,
     METH_VARARGS, "Returns the type of the given track"},
    {"seek", (PyCFunction)CDImage_seek,
     METH_VARARGS, "Seeks to a specific LSN"},
    {"length_in_seconds", (PyCFunction)CDImage_length_in_seconds,
     METH_NOARGS, "Returns the total length of the disc in seconds"},
    {NULL}
};


static PyMethodDef cdioMethods[] = {
    {"set_read_callback", (PyCFunction)set_read_callback,
     METH_VARARGS, "Sets the global callback for CDDA.read_sector"},
    {"identify_cdrom", (PyCFunction)cdio_identify_cdrom,
     METH_VARARGS, "Identifies a CD-ROM device"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

static PyTypeObject cdio_CDDAType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "cdio.CDDA",               /*tp_name*/
    sizeof(cdio_CDDAObject),   /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CDDA_dealloc,  /*tp_dealloc*/
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
    "CDDA objects",            /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    CDDA_methods,              /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CDDA_init,       /* tp_init */
    0,                         /* tp_alloc */
    CDDA_new,                  /* tp_new */
};

static PyTypeObject cdio_CDImageType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "cdio.CDImage",            /*tp_name*/
    sizeof(cdio_CDImage),      /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CDImage_dealloc, /*tp_dealloc*/
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
    "CDImage objects",         /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    CDImage_methods,           /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CDImage_init,    /* tp_init */
    0,                         /* tp_alloc */
    CDImage_new,               /* tp_new */
};
