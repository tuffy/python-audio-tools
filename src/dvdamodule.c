#include "dvdamodule.h"
#include "mod_defs.h"
#include "pcmconv.h"

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

MOD_INIT(dvda)
{
    PyObject* m;

    MOD_DEF(m, "dvda", "a DVD-Audio reading module", dvdaMethods)

    dvda_DVDAType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&dvda_DVDAType) < 0)
        return MOD_ERROR_VAL;

    dvda_TitlesetType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&dvda_TitlesetType) < 0)
        return MOD_ERROR_VAL;

    dvda_TitleType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&dvda_TitleType) < 0)
        return MOD_ERROR_VAL;

    dvda_TrackType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&dvda_TrackType) < 0)
        return MOD_ERROR_VAL;

    dvda_TrackReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&dvda_TrackReaderType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&dvda_DVDAType);
    PyModule_AddObject(m, "DVDA", (PyObject *)&dvda_DVDAType);

    Py_INCREF(&dvda_TitlesetType);
    PyModule_AddObject(m, "Titleset", (PyObject *)&dvda_TitlesetType);

    Py_INCREF(&dvda_TitleType);
    PyModule_AddObject(m, "Title", (PyObject *)&dvda_TitleType);

    Py_INCREF(&dvda_TrackType);
    PyModule_AddObject(m, "Track", (PyObject *)&dvda_TrackType);

    Py_INCREF(&dvda_TrackReaderType);
    PyModule_AddObject(m, "TrackReader", (PyObject *)&dvda_TrackReaderType);

    return MOD_SUCCESS_VAL(m);
}

/*******************************
 *         DVD object          *
 *******************************/

static PyObject*
DVDA_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    dvda_DVDA *self;

    self = (dvda_DVDA *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static int
DVDA_init(dvda_DVDA *self, PyObject *args, PyObject *kwds)
{
    char *audio_ts = NULL;
    char *device = NULL;

    self->dvda = NULL;

    if (!PyArg_ParseTuple(args, "s|s", &audio_ts, &device))
        return -1;

    if ((self->dvda = dvda_open(audio_ts, device)) == NULL) {
        PyErr_SetString(PyExc_IOError, "invalid AUDIO_TS path");
        return -1;
    }

    return 0;
}

static void
DVDA_dealloc(dvda_DVDA *self)
{
    if (self->dvda) {
        dvda_close(self->dvda);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
DVDA_titleset(dvda_DVDA *self, PyObject *args)
{
    int titleset;

    if (!PyArg_ParseTuple(args, "i", &titleset)) {
        return NULL;
    }

    return PyObject_CallFunction(
        (PyObject*)&dvda_TitlesetType, "Oi", self, titleset);
}

static PyObject*
DVDA_titlesets(dvda_DVDA *self, void *closure)
{
    return Py_BuildValue("I", dvda_titleset_count(self->dvda));
}

/*******************************
 *       Titleset object       *
 *******************************/

static PyObject*
Titleset_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    dvda_Titleset *self;

    self = (dvda_Titleset *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static int
Titleset_init(dvda_Titleset *self, PyObject *args, PyObject *kwds)
{
    dvda_DVDA* dvda;
    int titleset_number;

    self->titleset = NULL;

    if (!PyArg_ParseTuple(args, "O!i",
                          &dvda_DVDAType,
                          &dvda,
                          &titleset_number))
        return -1;

    if (titleset_number <= 0) {
        PyErr_SetString(PyExc_IndexError, "no such titleset");
        return -1;
    }

    if ((self->titleset =
         dvda_open_titleset(dvda->dvda, (unsigned)titleset_number)) == NULL) {
        PyErr_SetString(PyExc_IndexError, "no such titleset");
        return -1;
    }

    return 0;
}

static void
Titleset_dealloc(dvda_Titleset *self)
{
    if (self->titleset) {
        dvda_close_titleset(self->titleset);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
Titleset_title(dvda_Titleset *self, PyObject *args)
{
    int title;

    if (!PyArg_ParseTuple(args, "i", &title)) {
        return NULL;
    }

    return PyObject_CallFunction(
        (PyObject*)&dvda_TitleType, "Oi", self, title);
}

static PyObject*
Titleset_number(dvda_Titleset *self, void *closure)
{
    return Py_BuildValue("I", dvda_titleset_number(self->titleset));
}

static PyObject*
Titleset_titles(dvda_Titleset *self, void *closure)
{
    return Py_BuildValue("I", dvda_title_count(self->titleset));
}

/*******************************
 *        Title object         *
 *******************************/

static PyObject*
Title_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    dvda_Title *self;

    self = (dvda_Title *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static int
Title_init(dvda_Title *self, PyObject *args, PyObject *kwds)
{
    dvda_Titleset* titleset;
    int title_number;

    self->title = NULL;

    if (!PyArg_ParseTuple(args, "O!i",
                          &dvda_TitlesetType,
                          &titleset,
                          &title_number))
        return -1;

    if (title_number <= 0) {
        PyErr_SetString(PyExc_IndexError, "no such title");
        return -1;
    }

    if ((self->title =
         dvda_open_title(titleset->titleset, (unsigned)title_number)) == NULL) {
        PyErr_SetString(PyExc_IndexError, "no such title");
        return -1;
    }

    return 0;
}

static void
Title_dealloc(dvda_Title *self)
{
    if (self->title) {
        dvda_close_title(self->title);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
Title_track(dvda_Title *self, PyObject *args)
{
    int track;

    if (!PyArg_ParseTuple(args, "i", &track)) {
        return NULL;
    }

    return PyObject_CallFunction(
        (PyObject*)&dvda_TrackType, "Oi", self, track);
}

static PyObject*
Title_number(dvda_Title *self, void *closure)
{
    return Py_BuildValue("I", dvda_title_number(self->title));
}

static PyObject*
Title_tracks(dvda_Title *self, void *closure)
{
    return Py_BuildValue("I", dvda_track_count(self->title));
}

static PyObject*
Title_pts_length(dvda_Title *self, void *closure)
{
    return Py_BuildValue("I", dvda_title_pts_length(self->title));
}

/*******************************
 *        Track object         *
 *******************************/

static PyObject*
Track_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    dvda_Track *self;

    self = (dvda_Track *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static int
Track_init(dvda_Track *self, PyObject *args, PyObject *kwds)
{
    dvda_Title* title;
    int track_number;

    self->track = NULL;

    if (!PyArg_ParseTuple(args, "O!i",
                          &dvda_TitleType,
                          &title,
                          &track_number))
        return -1;

    if (track_number <= 0) {
        PyErr_SetString(PyExc_IndexError, "no such track");
        return -1;
    }

    if ((self->track =
         dvda_open_track(title->title, (unsigned)track_number)) == NULL) {
        PyErr_SetString(PyExc_IndexError, "no such track");
        return -1;
    }

    return 0;
}

static void
Track_dealloc(dvda_Track *self)
{
    if (self->track) {
        dvda_close_track(self->track);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
Track_reader(dvda_Track *self, PyObject *args)
{
    return PyObject_CallFunction(
        (PyObject*)&dvda_TrackReaderType, "O", self);
}

static PyObject*
Track_number(dvda_Track *self, void *closure)
{
    return Py_BuildValue("I", dvda_track_number(self->track));
}

static PyObject*
Track_pts_index(dvda_Track *self, void *closure)
{
    return Py_BuildValue("I", dvda_track_pts_index(self->track));
}

static PyObject*
Track_pts_length(dvda_Track *self, void *closure)
{
    return Py_BuildValue("I", dvda_track_pts_length(self->track));
}

static PyObject*
Track_first_sector(dvda_Track *self, void *closure)
{
    return Py_BuildValue("I", dvda_track_first_sector(self->track));
}

static PyObject*
Track_last_sector(dvda_Track *self, void *closure)
{
    return Py_BuildValue("I", dvda_track_last_sector(self->track));
}

/*******************************
 *     TrackReader object      *
 *******************************/

static PyObject*
TrackReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    dvda_TrackReader *self;

    self = (dvda_TrackReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static int
TrackReader_init(dvda_TrackReader *self, PyObject *args, PyObject *kwds)
{
    dvda_Track* track;

    self->closed = 0;
    self->reader = NULL;
    self->audiotools_pcm = NULL;

    if (!PyArg_ParseTuple(args, "O!", &dvda_TrackType, &track))
        return -1;

    if ((self->reader = dvda_open_track_reader(track->track)) == NULL) {
        PyErr_SetString(PyExc_IOError, "unable to open track reader");
        return -1;
    }

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL) {
        return -1;
    }

    return 0;
}

static void
TrackReader_dealloc(dvda_TrackReader *self)
{
    if (self->reader) {
        dvda_close_track_reader(self->reader);
    }
    Py_XDECREF(self->audiotools_pcm);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
TrackReader_read(dvda_TrackReader *self, PyObject *args)
{
    int pcm_frames;
    unsigned requested_pcm_frames;
    unsigned received_pcm_frames;
    pcm_FrameList *framelist;
    const unsigned channel_count = dvda_channel_count(self->reader);
    const unsigned bits_per_sample = dvda_bits_per_sample(self->reader);

    /*if closed, raise ValueError*/
    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "unable to read closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "i", &pcm_frames)) {
        return NULL;
    }

    /*restrict requested number of PCM frames to a reasonable value*/
    requested_pcm_frames = MIN(MAX(pcm_frames, 1), 1 << 20);

    /*grab empty FrameList and make a buffer for it*/
    if ((framelist = (pcm_FrameList*)empty_FrameList(
            self->audiotools_pcm,
            channel_count,
            bits_per_sample)) == NULL) {
        return NULL;
    }
    framelist->samples = PyMem_Realloc(
        framelist->samples,
        requested_pcm_frames * channel_count * (bits_per_sample / 8) *
        sizeof(int));

    /*perform read to FrameList's buffer*/
    received_pcm_frames = dvda_read(self->reader,
                                    requested_pcm_frames,
                                    framelist->samples);

    /*fill in remaining FrameList parameters*/
    framelist->frames = received_pcm_frames;
    framelist->samples_length = received_pcm_frames * channel_count;

    /*return FrameList*/
    return (PyObject*)framelist;
}

static PyObject*
TrackReader_close(dvda_TrackReader *self, PyObject *args)
{
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
TrackReader_enter(dvda_TrackReader* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
TrackReader_exit(dvda_TrackReader* self, PyObject *args)
{
    self->closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
TrackReader_sample_rate(dvda_TrackReader *self, void *closure)
{
    return Py_BuildValue("I", dvda_sample_rate(self->reader));
}

static PyObject*
TrackReader_bits_per_sample(dvda_TrackReader *self, void *closure)
{
    return Py_BuildValue("I", dvda_bits_per_sample(self->reader));
}

static PyObject*
TrackReader_channels(dvda_TrackReader *self, void *closure)
{
    return Py_BuildValue("I", dvda_channel_count(self->reader));
}

static PyObject*
TrackReader_channel_mask(dvda_TrackReader *self, void *closure)
{
    return Py_BuildValue("I", dvda_riff_wave_channel_mask(self->reader));
}

static PyObject*
TrackReader_codec(dvda_TrackReader *self, void *closure)
{
    switch (dvda_codec(self->reader)) {
    case DVDA_PCM:
        return Py_BuildValue("s", "PCM");
    case DVDA_MLP:
        return Py_BuildValue("s", "MLP");
    default:
        /*shouldn't get here*/
        return Py_BuildValue("s", "unknown");
    }
}
