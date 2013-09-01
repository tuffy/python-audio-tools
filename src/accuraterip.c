#include "accuraterip.h"
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

static PyMethodDef accuraterip_methods[] = {
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
init_accuraterip(void)
{
    PyObject* m;

    accuraterip_ChecksumV1Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&accuraterip_ChecksumV1Type) < 0)
        return;

    accuraterip_ChecksumV2Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&accuraterip_ChecksumV2Type) < 0)
        return;

    m = Py_InitModule3("_accuraterip",
                       accuraterip_methods,
                       "An AccurateRip checksum calculation module.");

    Py_INCREF(&accuraterip_ChecksumV1Type);
    PyModule_AddObject(m, "ChecksumV1",
                       (PyObject *)&accuraterip_ChecksumV1Type);

    Py_INCREF(&accuraterip_ChecksumV2Type);
    PyModule_AddObject(m, "ChecksumV2",
                       (PyObject *)&accuraterip_ChecksumV2Type);

}

static PyObject*
ChecksumV1_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    accuraterip_ChecksumV1 *self;

    self = (accuraterip_ChecksumV1 *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
ChecksumV1_init(accuraterip_ChecksumV1 *self, PyObject *args, PyObject *kwds)
{
    PyObject *pcm;
    int is_first;
    int is_last;
    int sample_rate;
    int total_pcm_frames;

    self->checksum = 0;
    self->track_index = 1;
    self->framelist_class = NULL;

    if (!PyArg_ParseTuple(args, "iiii", &is_first, &is_last,
                          &sample_rate, &total_pcm_frames))
        return -1;

    if (sample_rate <= 0) {
        PyErr_SetString(PyExc_ValueError, "sample rate must be > 0");
        return -1;
    }

    if (total_pcm_frames <= 0) {
        PyErr_SetString(PyExc_ValueError, "total PCM frames must be > 0");
        return -1;
    }

    /*ensure total_pcm_frames is large enough*/
    /*FIXME*/

    if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return -1;

    if ((self->framelist_class =
         PyObject_GetAttrString(pcm, "FrameList")) == NULL) {
        Py_DECREF(pcm);
        return -1;
    } else {
        Py_DECREF(pcm);
    }

    if (is_first) {
        self->start_offset = (uint32_t)((sample_rate / 75) * 5);
    } else {
        self->start_offset = 0;
    }

    if (is_last) {
        self->end_offset = (uint32_t)(total_pcm_frames -
                                      ((sample_rate / 75) * 5));
    } else {
        self->end_offset = (uint32_t)total_pcm_frames;
    }

    return 0;
}

void
ChecksumV1_dealloc(accuraterip_ChecksumV1 *self)
{
    Py_XDECREF(self->framelist_class);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
ChecksumV1_update(accuraterip_ChecksumV1* self, PyObject *args)
{
    PyObject *framelist_obj;
    pcm_FrameList *framelist;
    unsigned i;

    if (!PyArg_ParseTuple(args, "O", &framelist_obj))
        return NULL;

    /*ensure framelist_obj is a FrameList object*/
    if (PyObject_IsInstance(framelist_obj, self->framelist_class)) {
        framelist = (pcm_FrameList*)framelist_obj;
    } else {
        PyErr_SetString(PyExc_TypeError, "objects must be of type FrameList");
        return NULL;
    }

    /*ensure FrameList is CD-formatted*/
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

    /*update CRC with values from FrameList*/
    for (i = 0; i < framelist->frames; i++) {
        if ((self->track_index >= self->start_offset) &&
            (self->track_index <= self->end_offset)) {
            const int left_s = framelist->samples[i * 2];
            const int right_s = framelist->samples[i * 2 + 1];
            const unsigned left_u =
                left_s >= 0 ? left_s : (1 << 16) - (-left_s);
            const unsigned right_u =
                right_s >= 0 ? right_s : (1 << 16) - (-right_s);
            const unsigned value = (right_u << 16) | left_u;

            self->checksum += (value * self->track_index);
        }

        self->track_index++;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
ChecksumV1_checksum(accuraterip_ChecksumV1* self, PyObject *args)
{
    return Py_BuildValue("I", self->checksum);
}


static PyObject*
ChecksumV2_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    accuraterip_ChecksumV2 *self;

    self = (accuraterip_ChecksumV2 *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
ChecksumV2_init(accuraterip_ChecksumV2 *self, PyObject *args, PyObject *kwds)
{
    PyObject *pcm;
    int is_first;
    int is_last;
    int sample_rate;
    int total_pcm_frames;

    self->checksum = 0;
    self->track_index = 1;
    self->framelist_class = NULL;

    if (!PyArg_ParseTuple(args, "iiii", &is_first, &is_last,
                          &sample_rate, &total_pcm_frames))
        return -1;

    if (sample_rate <= 0) {
        PyErr_SetString(PyExc_ValueError, "sample rate must be > 0");
        return -1;
    }

    if (total_pcm_frames <= 0) {
        PyErr_SetString(PyExc_ValueError, "total PCM frames must be > 0");
        return -1;
    }

    /*ensure total_pcm_frames is large enough*/
    /*FIXME*/

    if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return -1;

    if ((self->framelist_class =
         PyObject_GetAttrString(pcm, "FrameList")) == NULL) {
        Py_DECREF(pcm);
        return -1;
    } else {
        Py_DECREF(pcm);
    }

    if (is_first) {
        self->start_offset = (uint32_t)((sample_rate / 75) * 5);
    } else {
        self->start_offset = 0;
    }

    if (is_last) {
        self->end_offset = (uint32_t)(total_pcm_frames -
                                      ((sample_rate / 75) * 5));
    } else {
        self->end_offset = (uint32_t)total_pcm_frames;
    }

    return 0;
}

void
ChecksumV2_dealloc(accuraterip_ChecksumV2 *self)
{
    Py_XDECREF(self->framelist_class);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
ChecksumV2_update(accuraterip_ChecksumV2* self, PyObject *args)
{
    PyObject *framelist_obj;
    pcm_FrameList *framelist;
    unsigned i;

    if (!PyArg_ParseTuple(args, "O", &framelist_obj))
        return NULL;

    /*ensure framelist_obj is a FrameList object*/
    if (PyObject_IsInstance(framelist_obj, self->framelist_class)) {
        framelist = (pcm_FrameList*)framelist_obj;
    } else {
        PyErr_SetString(PyExc_TypeError, "objects must be of type FrameList");
        return NULL;
    }

    /*ensure FrameList is CD-formatted*/
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

    /*update CRC with values from FrameList*/
    for (i = 0; i < framelist->frames; i++) {
        if ((self->track_index >= self->start_offset) &&
            (self->track_index <= self->end_offset)) {
            const int left_s = framelist->samples[i * 2];
            const int right_s = framelist->samples[i * 2 + 1];
            const unsigned left_u =
                left_s >= 0 ? left_s : (1 << 16) - (-left_s);
            const unsigned right_u =
                right_s >= 0 ? right_s : (1 << 16) - (-right_s);
            const unsigned value = (right_u << 16) | left_u;

            const uint64_t calc_crc_new = ((uint64_t)(value) *
                                           (uint64_t)(self->track_index));
            const uint32_t low_calc =
                (uint32_t)(calc_crc_new & (uint64_t)0xFFFFFFFF);
            const uint32_t hi_calc =
                (uint32_t)(calc_crc_new / (uint64_t)0x100000000);
            self->checksum += hi_calc;
            self->checksum += low_calc;
        }

        self->track_index++;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
ChecksumV2_checksum(accuraterip_ChecksumV2* self, PyObject *args)
{
    return Py_BuildValue("I", self->checksum);
}
