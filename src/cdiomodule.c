#include "cdiomodule.h"
#include <cdio/cd_types.h>
#include <cdio/audio.h>
#include <cdio/track.h>
#include <cdio/types.h>
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

PyMODINIT_FUNC
initcdio(void)
{
    PyObject* m;

    cdio_CDDAType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&cdio_CDDAType) < 0)
        return;

    cdio_CDImageType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&cdio_CDImageType) < 0)
        return;

    m = Py_InitModule3("cdio", cdioMethods,
                       "A CDDA reading module.");

    Py_INCREF(&cdio_CDDAType);
    PyModule_AddObject(m, "CDDA", (PyObject *)&cdio_CDDAType);

    Py_INCREF(&cdio_CDImageType);
    PyModule_AddObject(m, "CDImage", (PyObject *)&cdio_CDImageType);

    PyModule_AddIntConstant(m, "CD_IMAGE", CD_IMAGE);
    PyModule_AddIntConstant(m, "DEVICE_FILE", DEVICE_FILE);
    PyModule_AddIntConstant(m, "CUE_FILE", CUE_FILE);
    PyModule_AddIntConstant(m, "BIN_FILE", BIN_FILE);
    PyModule_AddIntConstant(m, "TOC_FILE", TOC_FILE);
    PyModule_AddIntConstant(m, "NRG_FILE", NRG_FILE);
}

/**********************/
/*audiotools.cdio.CDDA*/
/**********************/

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
    return Py_BuildValue("i", cdio_cddap_disc_firstsector(self->cdrom_drive));
}

static PyObject*
CDDA_last_sector(cdio_CDDAObject* self, PyObject *args)
{
    return Py_BuildValue("i", cdio_cddap_disc_lastsector(self->cdrom_drive));
}

static PyObject*
CDDA_track_type(cdio_CDDAObject* self, PyObject *args)
{
    track_t tracknum;

    if (!PyArg_ParseTuple(args, "H", &tracknum))
        return NULL;

    return Py_BuildValue("i",
                         cdio_get_track_format(self->cdrom_drive->p_cdio,
                                               tracknum));
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

/*************************/
/*audiotools.cdio.CDImage*/
/*************************/

static PyObject*
CDImage_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    cdio_CDImage *self;

    self = (cdio_CDImage *)type->tp_alloc(type, 0);
    self->image = NULL;
    self->current_sector = 0;

    self->pcm_module = NULL;

    return (PyObject *)self;
}

static int
CDImage_init(cdio_CDImage *self, PyObject *args, PyObject *kwds) {
    const char *image = NULL;
    int image_type;

    if (!PyArg_ParseTuple(args, "si", &image, &image_type))
        return -1;

    if ((self->pcm_module = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return -1;

    switch (image_type & 0x7) {
    case CUE_FILE:
        self->image = cdio_open_cue(image);
        break;
    case BIN_FILE:
        self->image = cdio_open_bincue(image);
        break;
    case TOC_FILE:
        self->image = cdio_open_cdrdao(image);
        break;
    case NRG_FILE:
        self->image = cdio_open_nrg(image);
        break;
    default:
        self->image = NULL;
        break;
    }

    if (self->image == NULL) {
        PyErr_SetString(PyExc_ValueError, "Unable to open image file");
        return -1;
    }

    return 0;
}

static void
CDImage_dealloc(cdio_CDImage* self) {
    if (self->image != NULL)
        cdio_destroy(self->image);

    Py_XDECREF(self->pcm_module);
    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
CDImage_total_tracks(cdio_CDImage* self) {
    return Py_BuildValue("H", cdio_get_last_track_num(self->image));
}

static PyObject*
CDImage_track_offsets(cdio_CDImage* self, PyObject *args) {
    track_t tracknum;

    if (!PyArg_ParseTuple(args, "H", &tracknum))
        return NULL;

    return Py_BuildValue("(i,i)",
                         cdio_get_track_lsn(self->image, tracknum),
                         cdio_get_track_last_lsn(self->image, tracknum));
}

static PyObject*
CDImage_read_sector(cdio_CDImage* self) {
    uint8_t* data;
    PyObject* to_return;

    data = malloc(CDIO_CD_FRAMESIZE_RAW);
    switch (cdio_read_audio_sector(self->image,
                                   data,
                                   self->current_sector)) {
    case DRIVER_OP_SUCCESS:
        to_return = PyObject_CallMethod(self->pcm_module,
                                        "FrameList",
                                        "s#iiii",
                                        (char *)data,
                                        (int)(CDIO_CD_FRAMESIZE_RAW),
                                        2, 16, 0, 1);
        free(data);
        self->current_sector += 1;
        return to_return;
    default:
        free(data);
        PyErr_SetString(PyExc_IOError, "error reading sectors");
        return NULL;
    }
}

static PyObject*
CDImage_read_sectors(cdio_CDImage* self, PyObject *args) {
    uint32_t sectors_to_read;
    uint8_t* data;
    PyObject* to_return;

    if (!PyArg_ParseTuple(args, "I", &sectors_to_read))
        return NULL;

    data = malloc(CDIO_CD_FRAMESIZE_RAW * sectors_to_read);
    switch (cdio_read_audio_sectors(self->image,
                                    data,
                                    self->current_sector,
                                    sectors_to_read)) {
    case DRIVER_OP_SUCCESS:
        to_return = PyObject_CallMethod(self->pcm_module,
                                        "FrameList",
                                        "s#iiii",
                                        (char *)data,
                                        (int)(CDIO_CD_FRAMESIZE_RAW *
                                              sectors_to_read),
                                        2, 16, 0, 1);
        free(data);
        self->current_sector += sectors_to_read;
        return to_return;
    default:
        free(data);
        PyErr_SetString(PyExc_IOError, "error reading sectors");
        return NULL;
    }
}

static PyObject*
CDImage_first_sector(cdio_CDImage* self, PyObject *args) {
    return Py_BuildValue("i",
                         cdio_get_track_lsn(self->image,
                             cdio_get_first_track_num(self->image)));
}

static PyObject*
CDImage_last_sector(cdio_CDImage* self, PyObject *args) {
    return Py_BuildValue("i",
                         cdio_get_track_last_lsn(self->image,
                             cdio_get_last_track_num(self->image)));
}

static PyObject*
CDImage_track_type(cdio_CDImage* self, PyObject *args) {
    track_t tracknum;

    if (!PyArg_ParseTuple(args, "H", &tracknum))
        return NULL;

        return Py_BuildValue("i",
                             cdio_get_track_format(self->image, tracknum));
}

static PyObject*
CDImage_seek(cdio_CDImage* self, PyObject *args) {
    if (!PyArg_ParseTuple(args, "i", &(self->current_sector)))
        return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
CDImage_length_in_seconds(cdio_CDImage* self) {
    msf_t first_track;
    msf_t leadout;
    int length;

    cdio_get_track_msf(self->image, 1, &first_track);
    cdio_get_track_msf(self->image, CDIO_CDROM_LEADOUT_TRACK, &leadout);

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

static PyObject*
cdio_identify_cdrom(PyObject *dummy, PyObject *args) {
    const char* device;
    struct stat buf;

    if (!PyArg_ParseTuple(args, "s", &device))
        return NULL;

    if (stat(device, &buf)) {
        PyErr_SetFromErrno(PyExc_IOError);
        return NULL;
    }

    if (S_ISREG(buf.st_mode)) {
         if (cdio_is_cuefile(device)) {
             return Py_BuildValue("i", CD_IMAGE | CUE_FILE);
         } else if (cdio_is_binfile(device)) {
             return Py_BuildValue("i", CD_IMAGE | BIN_FILE);
         } else if (cdio_is_tocfile(device)) {
             return Py_BuildValue("i", CD_IMAGE | TOC_FILE);
         } else if (cdio_is_nrg(device)) {
             return Py_BuildValue("i", CD_IMAGE | NRG_FILE);
         } else {
             PyErr_SetString(PyExc_ValueError, "unknown image file");
             return NULL;
         }
    } else if (S_ISBLK(buf.st_mode)) {
        if (cdio_is_device(device, DRIVER_LINUX)) {
            return Py_BuildValue("i", DEVICE_FILE);
        } else {
            PyErr_SetString(PyExc_ValueError, "unknown CD device");
            return NULL;
        }
    } else {
        PyErr_SetString(PyExc_ValueError, "unknown device");
        return NULL;
    }
}
