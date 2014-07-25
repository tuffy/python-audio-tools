#include "accuraterip.h"
#include "pcm.h"

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

static PyMethodDef accuraterip_methods[] = {
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
init_accuraterip(void)
{
    PyObject* m;

    accuraterip_ChecksumType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&accuraterip_ChecksumType) < 0)
        return;

    m = Py_InitModule3("_accuraterip",
                       accuraterip_methods,
                       "An AccurateRip checksum calculation module.");

    Py_INCREF(&accuraterip_ChecksumType);
    PyModule_AddObject(m, "Checksum",
                       (PyObject *)&accuraterip_ChecksumType);
}

static PyObject*
Checksum_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    accuraterip_Checksum *self;

    self = (accuraterip_Checksum *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
Checksum_init(accuraterip_Checksum *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"total_pcm_frames",
                             "sample_rate",
                             "is_first",
                             "is_last",
                             "pcm_frame_range",
                             NULL};

    PyObject *pcm;
    int total_pcm_frames;
    int sample_rate = 44100;
    int is_first = 0;
    int is_last = 0;
    int pcm_frame_range = 1;

    self->total_pcm_frames = 0;
    self->pcm_frame_range = 1;
    self->i = 0;
    self->j = 0;
    self->start_offset = 0;
    self->end_offset = 0;
    self->checksums_v1 = NULL;
    self->checksums_v2 = NULL;
    self->initial_values = NULL;
    self->initial_values_index = 0;
    self->final_values = NULL;
    self->final_values_index = 0;
    self->values_sum = 0;

    self->framelist_class = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "i|iiii", kwlist,
                                     &total_pcm_frames,
                                     &sample_rate,
                                     &is_first,
                                     &is_last,
                                     &pcm_frame_range))
        return -1;

    if (total_pcm_frames <= 0) {
        PyErr_SetString(PyExc_ValueError, "total PCM frames must be > 0");
        return -1;
    } else {
        self->total_pcm_frames = total_pcm_frames;
    }

    if (sample_rate <= 0) {
        PyErr_SetString(PyExc_ValueError, "sample rate must be > 0");
        return -1;
    } else {
        if (is_first) {
            self->start_offset = ((sample_rate / 75) * 5) - 1;
        } else {
            self->start_offset = 0;
        }
        if (is_last) {
            const int offset = (total_pcm_frames - ((sample_rate / 75) * 5));
            if (offset >= 0) {
                self->end_offset = offset;
            } else {
                self->end_offset = 0;
            }
        } else {
            self->end_offset = total_pcm_frames;
        }
    }

    if (pcm_frame_range <= 0) {
        PyErr_SetString(PyExc_ValueError, "PCM frame range must be > 0");
        return -1;
    } else {
        self->pcm_frame_range = pcm_frame_range;
        self->checksums_v1 = calloc(pcm_frame_range, sizeof(uint64_t));
        self->checksums_v2 = calloc(pcm_frame_range, sizeof(uint64_t));
        self->initial_values = calloc(pcm_frame_range - 1, sizeof(uint32_t));
        self->initial_values_index = 0;
        self->final_values = calloc(pcm_frame_range - 1, sizeof(uint32_t));
        self->final_values_index = 0;
    }

    /*keep a copy of the FrameList class so we can check for it*/
    if ((pcm = PyImport_ImportModule("audiotools.pcm")) == NULL)
        return -1;
    self->framelist_class = PyObject_GetAttrString(pcm, "FrameList");
    Py_DECREF(pcm);
    if (self->framelist_class == NULL) {
        return -1;
    }

    return 0;
}

void
Checksum_dealloc(accuraterip_Checksum *self)
{
    free(self->checksums_v1);
    free(self->checksums_v2);
    free(self->initial_values);
    free(self->final_values);
    Py_XDECREF(self->framelist_class);

    self->ob_type->tp_free((PyObject*)self);
}

static inline unsigned
unsigned_(int v)
{
    return (unsigned)((v >= 0) ? v : ((1 << 16) - (-v)));
}

static inline unsigned
value(int l, int r)
{
    return (unsigned_(r) << 16) | unsigned_(l);
}

static PyObject*
Checksum_update(accuraterip_Checksum* self, PyObject *args)
{
    PyObject *framelist_obj;
    pcm_FrameList *framelist;
    const unsigned channels = 2;
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

    /*ensure we're not given too many samples*/
    if ((self->i + framelist->frames) >
        (self->total_pcm_frames + self->pcm_frame_range - 1)) {
        PyErr_SetString(PyExc_ValueError, "too many samples for checksum");
        return NULL;
    }

    /*update checksum values*/
    for (i = 0; i < framelist->frames; i++) {
        checksum_update_frame(self,
                              framelist->samples[i * channels],
                              framelist->samples[i * channels + 1]);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static void
checksum_update_frame(accuraterip_Checksum* self, int left, int right)
{
    const unsigned v = value(left, right);

    /*calculate initial checksum*/
    if ((self->i >= self->start_offset) && (self->i < self->end_offset)) {
        const uint64_t v_i = ((uint64_t)v * (uint64_t)(self->i + 1));
        self->checksums_v1[0] += v_i;
        self->checksums_v2[0] += (v_i & 0xFFFFFFFF);
        self->checksums_v2[0] += (v_i >> 32);
        self->values_sum += v;
    }

    /*store the first (pcm_frame_range - 1) values in initial_values*/
    if ((self->i >= self->start_offset) &&
        (self->initial_values_index < (self->pcm_frame_range - 1))) {
        self->initial_values[self->initial_values_index++] = v;
    }

    /*store the trailing (pcm_frame_range - 1) values in final_values*/
    if ((self->i >= self->end_offset) &&
        (self->final_values_index < (self->pcm_frame_range - 1))) {
        self->final_values[self->final_values_index++] = v;
    }

    /*calculate incremental checksums*/
    if (self->i >= self->total_pcm_frames) {
        const int64_t initial_value = (int64_t)self->initial_values[self->j];

        const int64_t final_value = (int64_t)self->final_values[self->j];

        const int64_t initial_value_product =
            (int64_t)self->start_offset * initial_value;

        const int64_t final_value_product =
            (int64_t)self->end_offset * final_value;

        const int64_t delta = final_value_product -
                              (int64_t)(self->values_sum) -
                              initial_value_product;

        self->checksums_v1[self->j + 1] = self->checksums_v1[self->j] + delta;

        self->checksums_v2[self->j + 1] = 0;

        self->values_sum -= initial_value;
        self->values_sum += final_value;
        self->j++;
    }
    self->i++;
}

static PyObject*
Checksum_checksums_v1(accuraterip_Checksum* self, PyObject *args)
{
    unsigned i;

    if (self->i < (self->total_pcm_frames + self->pcm_frame_range - 1)) {
        PyErr_SetString(PyExc_ValueError, "insufficient samples for checksums");
        return NULL;
    }

    PyObject *checksums_obj = PyList_New(0);
    if (checksums_obj == NULL)
        return NULL;

    for (i = 0; i < self->pcm_frame_range; i++) {
        const uint32_t checksum_v1 =
            (uint32_t)(self->checksums_v1[i] & 0xFFFFFFFF);
        PyObject *number = PyLong_FromUnsignedLong(checksum_v1);
        int result;
        if (number == NULL) {
            Py_DECREF(checksums_obj);
            return NULL;
        }
        result = PyList_Append(checksums_obj, number);
        Py_DECREF(number);
        if (result == -1) {
            Py_DECREF(checksums_obj);
            return NULL;
        }
    }

    return checksums_obj;
}

static PyObject*
Checksum_checksums_v2(accuraterip_Checksum* self, PyObject *args)
{
    unsigned i;

    if (self->i < (self->total_pcm_frames + self->pcm_frame_range - 1)) {
        PyErr_SetString(PyExc_ValueError, "insufficient samples for checksums");
        return NULL;
    }

    PyObject *checksums_obj = PyList_New(0);
    if (checksums_obj == NULL)
        return NULL;

    for (i = 0; i < self->pcm_frame_range; i++) {
        const uint32_t checksum_v2 =
            (uint32_t)(self->checksums_v2[i] & 0xFFFFFFFF);
        PyObject *number = PyLong_FromUnsignedLong(checksum_v2);
        int result;
        if (number == NULL) {
            Py_DECREF(checksums_obj);
            return NULL;
        }
        result = PyList_Append(checksums_obj, number);
        Py_DECREF(number);
        if (result == -1) {
            Py_DECREF(checksums_obj);
            return NULL;
        }
    }

    return checksums_obj;
}
