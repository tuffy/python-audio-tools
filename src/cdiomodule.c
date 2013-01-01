#include "cdiomodule.h"
#include <cdio/cd_types.h>
#include <cdio/audio.h>
#include <cdio/track.h>
#include <cdio/types.h>
#include "pcm.h"

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
    self->pcm_module = NULL;

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
    track_t total = cdio_cddap_tracks(self->cdrom_drive);

    return Py_BuildValue("i", (int)total);
}

static PyObject*
CDDA_track_offsets(cdio_CDDAObject* self, PyObject *args)
{
    int tracknum;
    lsn_t first_sector;
    lsn_t last_sector;

    if (!PyArg_ParseTuple(args, "i", &tracknum))
        return NULL;

    first_sector = cdio_cddap_track_firstsector(self->cdrom_drive,
                                                (track_t)tracknum);
    last_sector = cdio_cddap_track_lastsector(self->cdrom_drive,
                                              (track_t)tracknum);

    return Py_BuildValue("(i,i)", (int)first_sector, (int)last_sector);
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

    if ((sector = (pcm_FrameList*)PyObject_CallMethod(
            self->pcm_module,
            "FrameList", "sIIii", "", 2, 16, 0, 0)) == NULL) {
        return NULL;
    }

    if (read_callback == NULL) {
        thread_state = PyEval_SaveThread();
    }

    sector->frames = 44100 / 75;
    sector->samples_length = (sector->frames * sector->channels);
    sector->samples = realloc(sector->samples,
                              sector->samples_length * sizeof(int));

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

    if ((sectors = (pcm_FrameList*)PyObject_CallMethod(
            self->pcm_module,
            "FrameList",
            "sIIii", "", 2, 16, 0, 0)) == NULL) {
        return NULL;
    }

    if (read_callback == NULL) {
        thread_state = PyEval_SaveThread();
    }

    sectors->frames = sectors_to_read * (44100 / 75);
    sectors->samples_length = (sectors->frames * sectors->channels);
    sectors->samples = realloc(sectors->samples,
                               sectors->samples_length * sizeof(int));

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
    int tracknum;

    if (!PyArg_ParseTuple(args, "i", &tracknum))
        return NULL;

    return Py_BuildValue("i",
                         cdio_get_track_format(self->cdrom_drive->p_cdio,
                                               (track_t)tracknum));
}

static PyObject*
CDDA_seek(cdio_CDDAObject* self, PyObject *args)
{
    off_t location;
    lsn_t new_location;

    if (!PyArg_ParseTuple(args, "l", &location))
        return NULL;

    new_location = cdio_paranoia_seek(self->paranoia,
                                      (int32_t)location,
                                      (int)SEEK_SET);

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
    self->pcm_module = NULL;
    self->image = NULL;

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
    track_t last_track = cdio_get_last_track_num(self->image);

    return Py_BuildValue("i", (int)last_track);
}

static PyObject*
CDImage_track_offsets(cdio_CDImage* self, PyObject *args) {
    /* track_t tracknum; */
    int tracknum;
    lsn_t first_sector;
    lsn_t last_sector;

    if (!PyArg_ParseTuple(args, "i", &tracknum))
        return NULL;

    first_sector = cdio_get_track_lsn(self->image, (track_t)tracknum);
    last_sector = cdio_get_track_last_lsn(self->image, (track_t)tracknum);

    return Py_BuildValue("(i,i)", (int)first_sector, (int)last_sector);
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
    int tracknum;

    if (!PyArg_ParseTuple(args, "i", &tracknum))
        return NULL;

        return Py_BuildValue("i",
                             cdio_get_track_format(self->image,
                                                   (track_t)tracknum));
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

static PyObject*
cdio_accuraterip_crc(PyObject *dummy, PyObject *args) {
    uint32_t crc;
    uint32_t track_index;
    PyObject *pcm = NULL;
    PyObject *framelist_class;
    PyObject *framelist_obj;
    pcm_FrameList *framelist;
    unsigned i;
    int left_v;
    int right_v;
    uint32_t left;
    uint32_t right;

    if (!PyArg_ParseTuple(args, "IIO", &crc, &track_index, &framelist_obj))
        return NULL;

    /*ensure framelist_obj is a FrameList*/
    if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return NULL;

    if ((framelist_class = PyObject_GetAttrString(pcm, "FrameList")) == NULL) {
        Py_DECREF(pcm);
        PyErr_SetString(PyExc_AttributeError, "FrameList class not found");
        return NULL;
    }

    if (!PyObject_IsInstance(framelist_obj, framelist_class)) {
        PyErr_SetString(PyExc_TypeError, "objects must be of type FrameList");
        Py_DECREF(framelist_class);
        Py_DECREF(pcm);
        return NULL;
    } else {
        /*convert framelist_obj to FrameList struct*/
        Py_DECREF(framelist_class);
        Py_DECREF(pcm);
        framelist = (pcm_FrameList*)framelist_obj;
    }

    /*check that FrameList is the appropriate type*/
    if (framelist->channels != 2) {
        PyErr_SetString(PyExc_ValueError,
                        "FrameList must be 2 channels");
        return NULL;
    }
    if (framelist->bits_per_sample != 16) {
        PyErr_SetString(PyExc_ValueError,
                        "FrameList must be 16 bits per sample");
        return NULL;
    }

    /*update CRC with values from FrameList struct*/
    for (i = 0; i < framelist->frames; i++) {
        left_v = framelist->samples[i * 2];
        right_v = framelist->samples[i * 2 + 1];
        left = left_v >= 0 ? left_v : (1 << 16) - (-left_v);
        right = right_v >= 0 ? right_v : (1 << 16) - (-right_v);
        crc += ((left | (right << 16)) * track_index);
        track_index++;
    }

    /*return new CRC*/
    return Py_BuildValue("(II)", crc, track_index);
}
