#include "cdiomodule.h"
#include <limits.h>
#include <cdio/cd_types.h>
#include <cdio/audio.h>
#include <cdio/track.h>
#include <cdio/types.h>
#include "pcm_conv.h"
#include "framelist.h"
#include "mod_defs.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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
#ifndef PyInt_FromLong
#define PyInt_FromLong PyLong_FromLong
#endif
#endif

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

MOD_INIT(cdio)
{
    PyObject* m;

    MOD_DEF(m, "cdio", "a CDDA reading module", cdioMethods)

    cdio_CDDAReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&cdio_CDDAReaderType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&cdio_CDDAReaderType);
    PyModule_AddObject(m, "CDDAReader", (PyObject *)&cdio_CDDAReaderType);

    return MOD_SUCCESS_VAL(m);
}

static PyObject*
CDDAReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    cdio_CDDAReader *self;

    self = (cdio_CDDAReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static int
CDDAReader_init(cdio_CDDAReader *self, PyObject *args, PyObject *kwds)
{
    char *device = NULL;
    struct stat buf;

    self->is_cd_image = 0;
    self->is_logging = 0;
    self->dealloc = NULL;
    self->closed = 0;
    self->audiotools_pcm = NULL;
    cddareader_reset_log(&(self->log));

    if (!PyArg_ParseTuple(args, "s|i", &device, &(self->is_logging)))
        return -1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    /*identify whether drive is physical or a CD image*/
    if (stat(device, &buf)) {
        PyErr_SetFromErrno(PyExc_IOError);
        return -1;
    }
    if (S_ISREG(buf.st_mode)) {
        if (cdio_is_cuefile(device) ||
            cdio_is_binfile(device) ||
            cdio_is_tocfile(device) ||
            cdio_is_nrg(device)) {
            /*open CD image and set function pointers*/
            self->is_cd_image = 1;
            self->is_logging = 0;
            return CDDAReader_init_image(self, device);
        } else {
            /*unsupported file*/
            PyErr_SetString(PyExc_ValueError, "unsupported CD image type");
            return -1;
        }
    } else if (S_ISBLK(buf.st_mode)) {
        if (cdio_is_device(device, DRIVER_LINUX)) {
            /*open CD device and set function pointers*/
            self->is_cd_image = 0;
            return CDDAReader_init_device(self, device);
        } else {
            /*unsupported block device*/
            PyErr_SetString(PyExc_ValueError, "unsupported block device");
            return -1;
        }
    } else {
        /*unsupported file type*/
        PyErr_SetString(PyExc_ValueError, "unsupported file type");
        return -1;
    }
}

static int
CDDAReader_init_image(cdio_CDDAReader *self, const char *device)
{
    self->_.image.image = NULL;
    self->_.image.current_sector = 0;
    self->_.image.final_sector = 0;
    self->first_track_num  = CDDAReader_first_track_num_image;
    self->last_track_num = CDDAReader_last_track_num_image;
    self->track_lsn = CDDAReader_track_lsn_image;
    self->track_last_lsn = CDDAReader_track_last_lsn_image;
    self->first_sector = CDDAReader_first_sector_image;
    self->last_sector = CDDAReader_last_sector_image;
    self->read = CDDAReader_read_image;
    self->seek = CDDAReader_seek_image;
    self->set_speed = CDDAReader_set_speed_image;
    self->dealloc = CDDAReader_dealloc_image;

    /*open CD image based on what type it is*/
    if (cdio_is_cuefile(device)) {
        self->_.image.image = cdio_open_cue(device);
    } else if (cdio_is_tocfile(device)) {
        self->_.image.image = cdio_open_bincue(device);
    } else if (cdio_is_tocfile(device)) {
        self->_.image.image = cdio_open_cdrdao(device);
    } else if (cdio_is_nrg(device)) {
        self->_.image.image = cdio_open_nrg(device);
    }
    if (self->_.image.image == NULL) {
        PyErr_SetString(PyExc_IOError, "unable to open CD image");
        return -1;
    }
    self->_.image.final_sector = (lsn_t)self->last_sector(self);
    return 0;
}

static int
CDDAReader_init_device(cdio_CDDAReader *self, const char *device)
{
    self->_.drive.drive = NULL;
    self->_.drive.paranoia = NULL;
    self->_.drive.current_sector = 0;
    self->_.drive.final_sector = 0;

    if ((self->_.drive.drive = cdio_cddap_identify(device, 0, NULL)) == NULL) {
        PyErr_SetString(PyExc_IOError, "error opening CD-ROM");
        return -1;
    }
    if (cdio_cddap_open(self->_.drive.drive) != 0) {
        PyErr_SetString(PyExc_IOError, "error opening CD-ROM");
        return -1;
    }
    self->_.drive.paranoia = cdio_paranoia_init(self->_.drive.drive);
    paranoia_modeset(self->_.drive.paranoia,
                     PARANOIA_MODE_FULL^PARANOIA_MODE_NEVERSKIP);

    self->first_track_num  = CDDAReader_first_track_num_device;
    self->last_track_num = CDDAReader_last_track_num_device;
    self->track_lsn = CDDAReader_track_lsn_device;
    self->track_last_lsn = CDDAReader_track_last_lsn_device;
    self->first_sector = CDDAReader_first_sector_device;
    self->last_sector = CDDAReader_last_sector_device;
    self->read = CDDAReader_read_device;
    self->seek = CDDAReader_seek_device;
    self->set_speed = CDDAReader_set_speed_device;
    self->dealloc = CDDAReader_dealloc_device;

    self->_.drive.final_sector = self->last_sector(self);

    if ((self->_.drive.final_sector == -1) ||
            (self->first_sector(self) == -1)) {
        PyErr_SetString(PyExc_IOError, "no disc in CD-ROM drive");
        return -1;
    }

    return 0;
}

static void
CDDAReader_dealloc(cdio_CDDAReader *self)
{
    if (self->dealloc) {
        self->dealloc(self);
    }
    Py_XDECREF(self->audiotools_pcm);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static void
CDDAReader_dealloc_image(cdio_CDDAReader *self)
{
    if (self->_.image.image != NULL) {
        cdio_destroy(self->_.image.image);
    }
}

static void
CDDAReader_dealloc_device(cdio_CDDAReader *self)
{
    if (self->_.drive.paranoia) {
        cdio_paranoia_free(self->_.drive.paranoia);
    }
    if (self->_.drive.drive) {
        cdio_cddap_close(self->_.drive.drive);
    }
}

static PyObject*
CDDAReader_sample_rate(cdio_CDDAReader *self, void *closure)
{
    const int sample_rate = 44100;
    return Py_BuildValue("i", sample_rate);
}

static PyObject*
CDDAReader_bits_per_sample(cdio_CDDAReader *self, void *closure)
{
    const int bits_per_sample = 16;
    return Py_BuildValue("i", bits_per_sample);
}

static PyObject*
CDDAReader_channels(cdio_CDDAReader *self, void *closure)
{
    const int channels = 2;
    return Py_BuildValue("i", channels);
}

static PyObject*
CDDAReader_channel_mask(cdio_CDDAReader *self, void *closure)
{
    const int channel_mask = 0x3;
    return Py_BuildValue("i", channel_mask);
}

static PyObject*
CDDAReader_is_cd_image(cdio_CDDAReader *self, void *closure)
{
    return PyBool_FromLong(self->is_cd_image);
}

static int
CDDAReader_first_track_num_image(cdio_CDDAReader *self)
{
    return cdio_get_first_track_num(self->_.image.image);
}

static int
CDDAReader_first_track_num_device(cdio_CDDAReader *self)
{
    /*FIXME - not sure if there's a more accurate way to get this*/
    return 1;
}

static int
CDDAReader_last_track_num_image(cdio_CDDAReader *self)
{
    return cdio_get_last_track_num(self->_.image.image);
}

static int
CDDAReader_last_track_num_device(cdio_CDDAReader *self)
{
    /*FIXME - not sure if there's a more accurate way to get this*/
    return cdio_cddap_tracks(self->_.drive.drive);
}

static int
CDDAReader_track_lsn_image(cdio_CDDAReader *self, int track_num)
{
    const lsn_t lsn = cdio_get_track_lsn(self->_.image.image,
                                         (track_t)track_num);
    return (int)lsn;
}

static int
CDDAReader_track_lsn_device(cdio_CDDAReader *self, int track_num)
{
    const lsn_t lsn = cdio_cddap_track_firstsector(self->_.drive.drive,
                                                   (track_t)track_num);
    return lsn;
}

static int
CDDAReader_track_last_lsn_image(cdio_CDDAReader *self, int track_num)
{
    const lsn_t lsn = cdio_get_track_last_lsn(self->_.image.image,
                                              (track_t)track_num);
    return (int)lsn;
}

static int
CDDAReader_track_last_lsn_device(cdio_CDDAReader *self, int track_num)
{
    const lsn_t lsn = cdio_cddap_track_lastsector(self->_.drive.drive,
                                                  (track_t)track_num);
    return lsn;
}

static PyObject*
CDDAReader_track_offsets(cdio_CDDAReader *self, void *closure)
{
    const int first_track_num = self->first_track_num(self);
    const int last_track_num = self->last_track_num(self);
    int i;
    PyObject *offsets = PyDict_New();

    if (offsets == NULL) {
        /*error creating the dict*/
        return NULL;
    }

    for (i = first_track_num; i <= last_track_num; i++) {
        PyObject *track_num = PyInt_FromLong(i);
        PyObject *track_offset = PyInt_FromLong(
            self->track_lsn(self, i) * 588);
        int result;
        if ((track_num == NULL) || (track_offset == NULL)) {
            /*error creating one of the two int values*/
            Py_XDECREF(track_num);
            Py_XDECREF(track_offset);
            Py_DECREF(offsets);
            return NULL;
        }
        result = PyDict_SetItem(offsets, track_num, track_offset);
        Py_DECREF(track_num);
        Py_DECREF(track_offset);
        if (result == -1) {
            /*error setting dictionary item*/
            Py_DECREF(offsets);
            return NULL;
        }
    }

    return offsets;
}

static PyObject*
CDDAReader_track_lengths(cdio_CDDAReader *self, void *closure)
{
    const int first_track_num = self->first_track_num(self);
    const int last_track_num = self->last_track_num(self);
    int i;
    PyObject *lengths = PyDict_New();

    if (lengths == NULL) {
        /*error creating the dict*/
        return NULL;
    }

    for (i = first_track_num; i <= last_track_num; i++) {
        PyObject *track_num = PyInt_FromLong(i);
        PyObject *track_length = PyInt_FromLong(
            (self->track_last_lsn(self, i) -
             self->track_lsn(self, i) + 1) * 588);
        int result;
        if ((track_num == NULL) || (track_length == NULL)) {
            /*error creating one of the two int values*/
            Py_XDECREF(track_num);
            Py_XDECREF(track_length);
            Py_DECREF(lengths);
            return NULL;
        }
        result = PyDict_SetItem(lengths, track_num, track_length);
        Py_DECREF(track_num);
        Py_DECREF(track_length);
        if (result == -1) {
            /*error setting dictionary item*/
            Py_DECREF(lengths);
            return NULL;
        }
    }

    return lengths;
}

static PyObject*
CDDAReader_first_sector(cdio_CDDAReader *self, void *closure)
{
    const int first_sector = self->first_sector(self);
    return Py_BuildValue("i", first_sector);
}

static int
CDDAReader_first_sector_image(cdio_CDDAReader *self)
{
    return cdio_get_track_lsn(self->_.image.image,
                              self->first_track_num(self));
}

static int
CDDAReader_first_sector_device(cdio_CDDAReader *self)
{
    return cdio_cddap_track_firstsector(self->_.drive.drive,
                                        self->first_track_num(self));
}

static PyObject*
CDDAReader_last_sector(cdio_CDDAReader *self, void *closure)
{
    const int last_sector = self->last_sector(self);
    return Py_BuildValue("i", last_sector);
}

static int
CDDAReader_last_sector_image(cdio_CDDAReader *self)
{
    return cdio_get_track_last_lsn(self->_.image.image,
                                   self->last_track_num(self));
}

static int
CDDAReader_last_sector_device(cdio_CDDAReader *self)
{
    return cdio_cddap_track_lastsector(self->_.drive.drive,
                                       self->last_track_num(self));
}

static PyObject*
CDDAReader_read(cdio_CDDAReader* self, PyObject *args)
{
    int pcm_frames;
    unsigned sectors_to_read;
    pcm_FrameList *framelist;
    int sectors_read;
    PyThreadState *thread_state = NULL;

    if (!PyArg_ParseTuple(args, "i", &pcm_frames)) {
        return NULL;
    }

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    sectors_to_read = MAX(pcm_frames, 0) / (44100 / 75);
    if (sectors_to_read < 1) {
        sectors_to_read = 1;
    }

    framelist = new_FrameList(self->audiotools_pcm,
                              2,
                              16,
                              sectors_to_read * (44100 / 75));

    /*if logging is in progress, only let a single thread
      into this function at once so that the global callback
      can be set and used atomically

      since the callback function doesn't take any state
      we're forced to stick it in a global variable*/
    if (!self->is_logging) {
        thread_state = PyEval_SaveThread();
    }
    sectors_read = self->read(self, sectors_to_read, framelist->samples);
    if (!self->is_logging) {
        PyEval_RestoreThread(thread_state);
    }

    if (sectors_read >= 0) {
        /*reduce length of framelist if fewer samples are read*/
        framelist->frames = sectors_read * (44100 / 75);
        framelist->samples_length = sectors_read * (44100 / 75) * 2;
        return (PyObject*)framelist;
    } else {
        Py_DECREF((PyObject*)framelist);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static int
CDDAReader_read_image(cdio_CDDAReader *self,
                      unsigned sectors_to_read,
                      int *samples)
{
    const unsigned samples_per_sector = (44100 / 75) * 2;
    const unsigned initial_sectors_to_read = sectors_to_read;

    while (sectors_to_read &&
           (self->_.image.current_sector <= self->_.image.final_sector)) {
        uint8_t sector[CDIO_CD_FRAMESIZE_RAW];
        const int result = cdio_read_audio_sector(
            self->_.image.image,
            sector,
            self->_.image.current_sector);

        if (result == DRIVER_OP_SUCCESS) {
            pcm_to_int_converter(16, 0, 1)(samples_per_sector, sector, samples);
            samples += samples_per_sector;
            self->_.image.current_sector++;
            sectors_to_read--;
        } else {
            return -1;
        }
    }

    return initial_sectors_to_read - sectors_to_read;
}

static int
CDDAReader_read_device(cdio_CDDAReader *self,
                       unsigned sectors_to_read,
                       int *samples)
{
    const unsigned initial_sectors_to_read = sectors_to_read;

    if (self->is_logging) {
        log_state = &(self->log);
    }

    while (sectors_to_read &&
           (self->_.drive.current_sector <= self->_.drive.final_sector)) {
        int16_t *raw_sector =
            cdio_paranoia_read_limited(
                self->_.drive.paranoia,
                self->is_logging ? cddareader_callback : NULL,
                10);
        unsigned i;

        for (i = 0; i < ((44100 / 75) * 2); i++) {
            *samples = raw_sector[i];
            samples += 1;
        }

        self->_.drive.current_sector++;
        sectors_to_read--;
    }

    if (self->is_logging) {
        log_state = NULL;
    }

    return initial_sectors_to_read - sectors_to_read;
}

static PyObject*
CDDAReader_seek(cdio_CDDAReader* self, PyObject *args)
{
    long long seeked_offset;
    unsigned seeked_sector;
    unsigned found_sector;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot seek closed stream");
        return NULL;
    }
    if (!PyArg_ParseTuple(args, "L", &seeked_offset))
        return NULL;

    if (seeked_offset < 0) {
        seeked_offset = 0;
    }

    if (seeked_offset > UINT_MAX) {
        seeked_sector = UINT_MAX;
    } else {
        seeked_sector = (unsigned)(seeked_offset / (44100 / 75));
    }
    found_sector = self->seek(self, seeked_sector);
    return Py_BuildValue("I", found_sector * (44100 / 75));
}

static unsigned
CDDAReader_seek_image(cdio_CDDAReader *self, unsigned sector)
{
    self->_.image.current_sector =
        MIN(sector, self->_.image.final_sector - 1);
    return self->_.image.current_sector;
}

static unsigned
CDDAReader_seek_device(cdio_CDDAReader *self, unsigned sector)
{
    const unsigned desired_sector = MIN(sector, self->_.drive.final_sector - 1);
    /*not sure what this returns, but it isn't the sector seeked to*/
    cdio_paranoia_seek(self->_.drive.paranoia,
                       (int32_t)desired_sector,
                       (int)SEEK_SET);
    self->_.drive.current_sector = desired_sector;
    return self->_.drive.current_sector;
}

static PyObject*
CDDAReader_close(cdio_CDDAReader* self, PyObject *args)
{
    self->closed = 1;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
CDDAReader_set_speed(cdio_CDDAReader *self, PyObject *args)
{
    int new_speed;

    if (!PyArg_ParseTuple(args, "i", &new_speed))
        return NULL;

    self->set_speed(self, new_speed);

    Py_INCREF(Py_None);
    return Py_None;
}

static void
CDDAReader_set_speed_image(cdio_CDDAReader *self, int new_speed)
{
    /*not an actual CD device, so do nothing*/
}

static void
CDDAReader_set_speed_device(cdio_CDDAReader *self, int new_speed)
{
    cdio_cddap_speed_set(self->_.drive.drive, new_speed);
}

static void
cddareader_callback(long int i, paranoia_cb_mode_t mode)
{
    if (log_state) {
        switch (mode) {
        case PARANOIA_CB_READ:
            log_state->read++;
            break;
        case PARANOIA_CB_VERIFY:
            log_state->verify++;
            break;
        case PARANOIA_CB_FIXUP_EDGE:
            log_state->fixup_edge++;
            break;
        case PARANOIA_CB_FIXUP_ATOM:
            log_state->fixup_atom++;
            break;
        case PARANOIA_CB_SCRATCH:
            log_state->scratch++;
            break;
        case PARANOIA_CB_REPAIR:
            log_state->repair++;
            break;
        case PARANOIA_CB_SKIP:
            log_state->skip++;
            break;
        case PARANOIA_CB_DRIFT:
            log_state->drift++;
            break;
        case PARANOIA_CB_BACKOFF:
            log_state->backoff++;
            break;
        case PARANOIA_CB_OVERLAP:
            log_state->overlap++;
            break;
        case PARANOIA_CB_FIXUP_DROPPED:
            log_state->fixup_dropped++;
            break;
        case PARANOIA_CB_FIXUP_DUPED:
            log_state->fixup_duped++;
            break;
        case PARANOIA_CB_READERR:
            log_state->readerr++;
            break;
        default:
            break;
        }
    }
}

static void
cddareader_reset_log(struct cdio_log *log)
{
    log->read = 0;
    log->verify = 0;
    log->fixup_edge = 0;
    log->fixup_atom = 0;
    log->scratch = 0;
    log->repair = 0;
    log->skip = 0;
    log->drift = 0;
    log->backoff = 0;
    log->overlap = 0;
    log->fixup_dropped = 0;
    log->fixup_duped = 0;
    log->readerr = 0;
}

static int
cddareader_set_log_item(PyObject *dict, const char *key, int value)
{
    PyObject *value_obj = Py_BuildValue("i", value);
    if (value_obj) {
        const int result = PyDict_SetItemString(dict, key, value_obj);
        Py_DECREF(value_obj);
        if (result == 0) {
            return 0;
        } else {
            return 1;
        }
    } else {
        return 1;
    }
}

static PyObject*
CDDAReader_log(cdio_CDDAReader *self, PyObject *args)
{
    const struct cdio_log *log = &(self->log);
    PyObject *log_obj = PyDict_New();
    if (log_obj) {
        if (cddareader_set_log_item(log_obj, "read", log->read))
            goto error;
        if (cddareader_set_log_item(log_obj, "verify", log->verify))
            goto error;
        if (cddareader_set_log_item(log_obj, "fixup_edge", log->fixup_edge))
            goto error;
        if (cddareader_set_log_item(log_obj, "fixup_atom", log->fixup_atom))
            goto error;
        if (cddareader_set_log_item(log_obj, "scratch", log->scratch))
            goto error;
        if (cddareader_set_log_item(log_obj, "repair", log->repair))
            goto error;
        if (cddareader_set_log_item(log_obj, "skip", log->skip))
            goto error;
        if (cddareader_set_log_item(log_obj, "drift", log->drift))
            goto error;
        if (cddareader_set_log_item(log_obj, "backoff", log->backoff))
            goto error;
        if (cddareader_set_log_item(log_obj, "overlap", log->overlap))
            goto error;
        if (cddareader_set_log_item(log_obj, "fixup_dropped",
                                    log->fixup_dropped))
            goto error;
        if (cddareader_set_log_item(log_obj, "fixup_duped", log->fixup_duped))
            goto error;
        if (cddareader_set_log_item(log_obj, "readerr", log->readerr))
            goto error;

        return log_obj;
error:
        Py_DECREF(log_obj);
        return NULL;
    } else {
        return NULL;
    }
}

static PyObject*
CDDAReader_reset_log(cdio_CDDAReader *self, PyObject *args)
{
    cddareader_reset_log(&(self->log));
    Py_INCREF(Py_None);
    return Py_None;
}
