#include "accuraterip.h"
#include "pcm.h"
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

/**********************************************************************
  Offset checksum calculation adapted from Jon Lund Steffensen's work:

  http://jonls.dk/2009/10/calculating-accuraterip-checksums/

  The math is the same, but I find it clearer to store the initial
  and trailing values used to adjust the values sum in a seperate memory
  space rather than stuff them in the checksums area temporarily.
 **********************************************************************/

static PyMethodDef accuraterip_methods[] = {
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

MOD_INIT(_accuraterip)
{
    PyObject* m;

    MOD_DEF(m, "_accuraterip",
            "an AccurateRip checksum calculation module",
            accuraterip_methods)

    accuraterip_ChecksumType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&accuraterip_ChecksumType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&accuraterip_ChecksumType);
    PyModule_AddObject(m, "Checksum",
                       (PyObject *)&accuraterip_ChecksumType);

    return MOD_SUCCESS_VAL(m);
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
                             "accurateripv2_offset",
                             NULL};

    PyObject *pcm;
    int total_pcm_frames;
    int sample_rate = 44100;
    int is_first = 0;
    int is_last = 0;
    int pcm_frame_range = 1;
    int accurateripv2_offset = 0;

    self->accuraterip_v1.checksums = NULL;
    self->accuraterip_v1.initial_values = NULL;
    self->accuraterip_v1.final_values = NULL;
    self->framelist_class = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "i|iiiii", kwlist,
                                     &total_pcm_frames,
                                     &sample_rate,
                                     &is_first,
                                     &is_last,
                                     &pcm_frame_range,
                                     &accurateripv2_offset))
        return -1;

    if (total_pcm_frames > 0) {
        self->total_pcm_frames = total_pcm_frames;
    } else {
        PyErr_SetString(PyExc_ValueError, "total PCM frames must be > 0");
        return -1;
    }

    if (sample_rate > 0) {
        if (is_first) {
            self->start_offset = ((sample_rate / 75) * 5);
        } else {
            self->start_offset = 1;
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
    } else {
        PyErr_SetString(PyExc_ValueError, "sample rate must be > 0");
        return -1;
    }

    if (pcm_frame_range <= 0) {
        PyErr_SetString(PyExc_ValueError, "PCM frame range must be > 0");
        return -1;
    }

    if (accurateripv2_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "accurateripv2_offset must be >= 0");
        return -1;
    }

    self->pcm_frame_range = pcm_frame_range;
    self->processed_frames = 0;

    /*initialize AccurateRip V1 values*/
    self->accuraterip_v1.index = 1;
    self->accuraterip_v1.checksums = calloc(pcm_frame_range, sizeof(uint32_t));
    self->accuraterip_v1.initial_values = init_queue(pcm_frame_range - 1);
    self->accuraterip_v1.final_values = init_queue(pcm_frame_range - 1);
    self->accuraterip_v1.values_sum = 0;


    /*initialize AccurateRip V2 values*/
    self->accuraterip_v2.index = 1;
    self->accuraterip_v2.checksum = 0;
    self->accuraterip_v2.current_offset = accurateripv2_offset;
    self->accuraterip_v2.initial_offset = accurateripv2_offset;

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
    free(self->accuraterip_v1.checksums);
    free_queue(self->accuraterip_v1.initial_values);
    free_queue(self->accuraterip_v1.final_values);

    Py_XDECREF(self->framelist_class);

    Py_TYPE(self)->tp_free((PyObject*)self);
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
    pcm_FrameList *framelist;
    const unsigned channels = 2;
    unsigned i;

    if (!PyArg_ParseTuple(args, "O!", self->framelist_class, &framelist))
        return NULL;

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
    if ((self->processed_frames + framelist->frames) >
        (self->total_pcm_frames + self->pcm_frame_range - 1)) {
        PyErr_SetString(PyExc_ValueError, "too many samples for checksum");
        return NULL;
    }

    /*update checksum values*/
    for (i = 0; i < framelist->frames; i++) {
        const unsigned v = value(framelist->samples[i * channels],
                                 framelist->samples[i * channels + 1]);
        update_frame_v1(&(self->accuraterip_v1),
                        self->total_pcm_frames,
                        self->start_offset,
                        self->end_offset,
                        v);
        update_frame_v2(&(self->accuraterip_v2),
                        self->total_pcm_frames,
                        self->start_offset,
                        self->end_offset,
                        v);
    }

    self->processed_frames += framelist->frames;

    Py_INCREF(Py_None);
    return Py_None;
}

static void
update_frame_v1(struct accuraterip_v1 *v1,
                unsigned total_pcm_frames,
                unsigned start_offset,
                unsigned end_offset,
                unsigned value)
{
    /*calculate initial checksum*/
    if ((v1->index >= start_offset) && (v1->index <= end_offset)) {
        v1->checksums[0] += (value * v1->index);
        v1->values_sum += value;
    }

    /*store the first (pcm_frame_range - 1) values in initial_values*/
    if ((v1->index >= start_offset) && (!queue_full(v1->initial_values))) {
        queue_push(v1->initial_values, value);
    }

    /*store the trailing (pcm_frame_range - 1) values in final_values*/
    if ((v1->index > end_offset) && (!queue_full(v1->final_values))) {
        queue_push(v1->final_values, value);
    }

    /*calculate incremental checksums*/
    if (v1->index > total_pcm_frames) {
        const uint32_t initial_value = queue_pop(v1->initial_values);

        const uint32_t final_value = queue_pop(v1->final_values);

        const uint32_t initial_value_product =
            (uint32_t)(start_offset - 1) * initial_value;

        const uint32_t final_value_product =
            (uint32_t)end_offset * final_value;

        v1->checksums[v1->index - total_pcm_frames] =
            v1->checksums[v1->index - total_pcm_frames - 1] +
            final_value_product -
            v1->values_sum -
            initial_value_product;

        v1->values_sum -= initial_value;
        v1->values_sum += final_value;
    }

    v1->index++;
}

static void
update_frame_v2(struct accuraterip_v2 *v2,
                unsigned total_pcm_frames,
                unsigned start_offset,
                unsigned end_offset,
                unsigned value)
{
    if (!v2->current_offset) {
        if ((v2->index >= start_offset) && (v2->index <= end_offset)) {
            const uint64_t v_i = ((uint64_t)value * (uint64_t)(v2->index));
            v2->checksum += (uint32_t)(v_i >> 32);
        }
        v2->index++;
    } else {
        v2->current_offset--;
    }
}

static PyObject*
Checksum_checksums_v1(accuraterip_Checksum* self, PyObject *args)
{
    const struct accuraterip_v1 *v1 = &(self->accuraterip_v1);
    unsigned i;

    if (self->processed_frames <
        (self->total_pcm_frames + self->pcm_frame_range - 1)) {
        PyErr_SetString(PyExc_ValueError, "insufficient samples for checksums");
        return NULL;
    }

    PyObject *checksums_obj = PyList_New(0);
    if (checksums_obj == NULL)
        return NULL;

    for (i = 0; i < self->pcm_frame_range; i++) {
        PyObject *number = PyLong_FromUnsignedLong(v1->checksums[i]);
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
Checksum_checksum_v2(accuraterip_Checksum* self, PyObject *args)
{
    const struct accuraterip_v1 *v1 = &(self->accuraterip_v1);
    const struct accuraterip_v2 *v2 = &(self->accuraterip_v2);

    if (self->processed_frames <
        (self->total_pcm_frames + self->pcm_frame_range - 1)) {
        PyErr_SetString(PyExc_ValueError, "insufficient samples for checksums");
        return NULL;
    } else {
        const uint32_t checksum_v2 =
            v2->checksum + v1->checksums[v2->initial_offset];

        return PyLong_FromUnsignedLong(checksum_v2);
    }
}

static struct queue*
init_queue(unsigned total_size)
{
    struct queue *queue = malloc(sizeof(struct queue));
    queue->values = malloc(total_size * sizeof(uint32_t));
    queue->total_size = total_size;
    queue->head_index = 0;
    queue->tail_index = 0;
    return queue;
}

static void
free_queue(struct queue *queue)
{
    if (queue != NULL) {
        free(queue->values);
        free(queue);
    }
}
