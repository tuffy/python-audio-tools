#include <Python.h>
#include <cdio/cdda.h>
#include <cdio/cd_types.h>
#include <cdio/paranoia.h>
#include <cdio/audio.h>
#include <cdio/track.h>
#include "pcm.h"

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

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

static PyObject *read_callback = NULL;

typedef struct {
    PyObject_HEAD
    cdrom_drive_t *cdrom_drive;
    cdrom_paranoia_t *paranoia;
    PyObject *pcm_module;
} cdio_CDDAObject;

static void
CDDA_dealloc(cdio_CDDAObject* self);

static PyObject
*CDDA_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
CDDA_init(cdio_CDDAObject *self, PyObject *args, PyObject *kwds);

static PyObject
*CDDA_total_tracks(cdio_CDDAObject* self);

static PyObject
*CDDA_track_offsets(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_read_sector(cdio_CDDAObject* self);

static PyObject
*CDDA_read_sectors(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_first_sector(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_last_sector(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_track_type(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_seek(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_set_speed(cdio_CDDAObject* self, PyObject *args);

static PyObject
*CDDA_length_in_seconds(cdio_CDDAObject* self);

static PyObject
*set_read_callback(PyObject *dummy, PyObject *args);

void
read_sector_callback(long int i, paranoia_cb_mode_t mode);

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


static PyMethodDef cdioMethods[] = {
    {"set_read_callback", (PyCFunction)set_read_callback,
     METH_VARARGS, "Sets the global callback for CDDA.read_sector"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif


#ifdef IS_PY3K

static PyTypeObject cdio_CDDAType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "cdio.CDDA",               /* tp_name */
    sizeof(cdio_CDDAObject),   /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)CDDA_dealloc,  /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,   /* tp_flags */
    "CDDA objects",            /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
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


static PyModuleDef cdiomodule = {
    PyModuleDef_HEAD_INIT,
    "cdio",
    "A CDDA reading module.",
    -1,
    cdioMethods,
    NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_cdio(void)
{
    PyObject* m;

    cdio_CDDAType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&cdio_CDDAType) < 0)
        return NULL;

    m = PyModule_Create(&cdiomodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&cdio_CDDAType);
    PyModule_AddObject(m, "CDDA", (PyObject *)&cdio_CDDAType);
    return m;
}

static void
CDDA_dealloc(cdio_CDDAObject* self)
{
    if (self->paranoia != NULL)
        cdio_paranoia_free(self->paranoia);
    if (self->cdrom_drive != NULL)
        cdio_cddap_close(self->cdrom_drive);
    Py_TYPE(self)->tp_free((PyObject*)self);
}



#else

static PyTypeObject cdio_CDDAType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "cdio.CDDA",                 /*tp_name*/
    sizeof(cdio_CDDAObject),     /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CDDA_dealloc,   /*tp_dealloc*/
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
    "CDDA objects",             /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    CDDA_methods,               /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CDDA_init,        /* tp_init */
    0,                         /* tp_alloc */
    CDDA_new,                   /* tp_new */
};

PyMODINIT_FUNC
initcdio(void)
{
    PyObject* m;

    cdio_CDDAType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&cdio_CDDAType) < 0)
        return;

    m = Py_InitModule3("cdio", cdioMethods,
                       "A CDDA reading module.");

    Py_INCREF(&cdio_CDDAType);
    PyModule_AddObject(m, "CDDA", (PyObject *)&cdio_CDDAType);
}

static void
CDDA_dealloc(cdio_CDDAObject* self)
{
    if (self->paranoia != NULL)
        cdio_paranoia_free(self->paranoia);
    if (self->cdrom_drive != NULL)
        cdio_cddap_close(self->cdrom_drive);
    Py_XDECREF(self->pcm_module);
    if (self != NULL)
        self->ob_type->tp_free((PyObject*)self);
}
#endif


static PyObject*
CDDA_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    cdio_CDDAObject *self;

    self = (cdio_CDDAObject *)type->tp_alloc(type, 0);
    self->pcm_module = NULL;

    return (PyObject *)self;
}

static int
CDDA_init(cdio_CDDAObject *self, PyObject *args, PyObject *kwds)
{
    const char *drive = NULL;

    if (!PyArg_ParseTuple(args, "s", &drive))
        return -1;

    if ((self->pcm_module = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return -1;

    self->cdrom_drive = cdio_cddap_identify(drive, 0, NULL);
    if (self->cdrom_drive == NULL) {
        PyErr_SetString(PyExc_IOError,
                        "error opening CD-ROM");
        return -1;
    }

    if (0 != cdio_cddap_open(self->cdrom_drive)) {
        PyErr_SetString(PyExc_IOError,
                        "error opening CD-ROM");
        return -1;
    }

    self->paranoia = cdio_paranoia_init(self->cdrom_drive);
    paranoia_modeset(self->paranoia,
                     PARANOIA_MODE_FULL^PARANOIA_MODE_NEVERSKIP);

    return 0;
}

static PyObject*
CDDA_total_tracks(cdio_CDDAObject* self)
{
    track_t total;

    total = cdio_cddap_tracks(self->cdrom_drive);

    return Py_BuildValue("H", total);
}

static PyObject*
CDDA_track_offsets(cdio_CDDAObject* self, PyObject *args)
{
    track_t tracknum;

    if (!PyArg_ParseTuple(args, "H", &tracknum))
        return NULL;

    return Py_BuildValue("(i,i)",
                         cdio_cddap_track_firstsector(self->cdrom_drive,
                                                      tracknum),
                         cdio_cddap_track_lastsector(self->cdrom_drive,
                                                     tracknum));
}

#define SECTOR_LENGTH 2352

static PyObject*
CDDA_read_sector(cdio_CDDAObject* self)
{
    int16_t *raw_sector;
    int i;

    int current_sector_position = 0;

    pcm_FrameList *sector;
    PyThreadState *thread_state = NULL;

    sector = (pcm_FrameList*)PyObject_CallMethod(self->pcm_module,
                                                 "__blank__", NULL);
    if (sector == NULL)
        return NULL;

    if (read_callback == NULL) {
        thread_state = PyEval_SaveThread();
    }

    sector->frames = 44100 / 75;
    sector->channels = 2;
    sector->bits_per_sample = 16;
    sector->samples_length = (sector->frames * sector->channels);
    sector->samples = realloc(sector->samples,
                              sector->samples_length * sizeof(ia_data_t));

    raw_sector = cdio_paranoia_read_limited(self->paranoia,
                                            &read_sector_callback,
                                            10);
    for (i = 0; i < (SECTOR_LENGTH / 2); i++) {
        sector->samples[current_sector_position++] = raw_sector[i];
    }

    if (read_callback == NULL) {
        PyEval_RestoreThread(thread_state);
    }

    return (PyObject*)sector;
}

static PyObject*
CDDA_read_sectors(cdio_CDDAObject* self, PyObject *args)
{
    int16_t *raw_sector;
    int i;

    int current_sectors_position = 0;
    int sectors_read;
    int sectors_to_read;

    pcm_FrameList *sectors;
    PyThreadState *thread_state = NULL;

    if (!PyArg_ParseTuple(args, "i", &sectors_to_read))
        return NULL;

    sectors = (pcm_FrameList*)PyObject_CallMethod(self->pcm_module,
                                                  "__blank__", NULL);
    if (sectors == NULL)
        return NULL;

    if (read_callback == NULL) {
        thread_state = PyEval_SaveThread();
    }

    sectors->frames = sectors_to_read * (44100 / 75);
    sectors->channels = 2;
    sectors->bits_per_sample = 16;
    sectors->samples_length = (sectors->frames * sectors->channels);
    sectors->samples = realloc(sectors->samples,
                               sectors->samples_length * sizeof(ia_data_t));

    for (sectors_read = 0; sectors_read < sectors_to_read; sectors_read++) {
        raw_sector = cdio_paranoia_read_limited(self->paranoia,
                                                &read_sector_callback,
                                                10);
        for (i = 0; i < (SECTOR_LENGTH / 2); i++) {
            sectors->samples[current_sectors_position++] = raw_sector[i];
        }
    }

    if (read_callback == NULL) {
        PyEval_RestoreThread(thread_state);
    }

    return (PyObject*)sectors;
}

static PyObject*
CDDA_first_sector(cdio_CDDAObject* self, PyObject *args)
{
    lsn_t sector;

    sector = cdio_cddap_disc_firstsector(self->cdrom_drive);

    return Py_BuildValue("i", sector);
}

static PyObject*
CDDA_last_sector(cdio_CDDAObject* self, PyObject *args)
{
    lsn_t sector;

    sector = cdio_cddap_disc_lastsector(self->cdrom_drive);

    return Py_BuildValue("i", sector);
}

static PyObject*
CDDA_track_type(cdio_CDDAObject* self, PyObject *args)
{
    track_format_t format;
    track_t tracknum;

    if (!PyArg_ParseTuple(args, "H", &tracknum))
        return NULL;

    format = cdio_get_track_format(self->cdrom_drive->p_cdio, tracknum);
    return Py_BuildValue("i", format);
}

static PyObject*
CDDA_seek(cdio_CDDAObject* self, PyObject *args)
{
    off_t location;
    lsn_t new_location;

    if (!PyArg_ParseTuple(args, "l", &location))
        return NULL;

    new_location = cdio_paranoia_seek(self->paranoia,
                                      location,
                                      SEEK_SET);

    return Py_BuildValue("i", new_location);
}

static PyObject*
CDDA_set_speed(cdio_CDDAObject* self, PyObject *args)
{
    int new_speed;

    if (!PyArg_ParseTuple(args, "i", &new_speed))
        return NULL;

    cdio_cddap_speed_set(self->cdrom_drive, new_speed);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
CDDA_length_in_seconds(cdio_CDDAObject* self)
{
    msf_t first_track;
    msf_t leadout;
    int length;

    cdio_get_track_msf(self->cdrom_drive->p_cdio,
                       1, &first_track);
    cdio_get_track_msf(self->cdrom_drive->p_cdio,
                       CDIO_CDROM_LEADOUT_TRACK, &leadout);

    length = cdio_audio_get_msf_seconds(&leadout) -
        cdio_audio_get_msf_seconds(&first_track);

    return Py_BuildValue("i", length);
}


/*callback stuff*/


static PyObject*
set_read_callback(PyObject *dummy, PyObject *args)
{
    PyObject *result = NULL;
    PyObject *temp;

    if (PyArg_ParseTuple(args, "O:set_callback", &temp)) {
        if (!PyCallable_Check(temp)) {
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return NULL;
        }
        Py_XINCREF(temp);         /* Add a reference to new callback */
        Py_XDECREF(read_callback);  /* Dispose of previous callback */
        read_callback = temp;       /* Remember new callback */
        /* Boilerplate to return "None" */
        Py_INCREF(Py_None);
        result = Py_None;
    }
    return result;
}

void
read_sector_callback(long int i, paranoia_cb_mode_t mode)
{
    PyObject *arglist;
    PyObject *result;

    if (read_callback != NULL) {
        /*if a global callback has been set,
          build Python values and call it*/
        arglist = Py_BuildValue("(l,i)", i, mode);
        result = PyEval_CallObject(read_callback, arglist);
        Py_DECREF(arglist);
        Py_XDECREF(result);
    }
}
