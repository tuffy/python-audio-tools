#include <Python.h>
#include <cdio/cdda.h>
#include <cdio/paranoia.h>

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

static PyMethodDef cdioMethods[] = {
    {NULL, NULL, 0, NULL}  /*sentinel*/
};

struct cdio_log {
    int read;
    int verify;
    int fixup_edge;
    int fixup_atom;
    int scratch;
    int repair;
    int skip;
    int drift;
    int backoff;
    int overlap;
    int fixup_dropped;
    int fixup_duped;
    int readerr;
};

/*global pointer to the current cdio_log state
  to be used by the cddareader_callback*/
struct cdio_log *log_state = NULL;

static void
cddareader_callback(long int i, paranoia_cb_mode_t mode);

/*audiotools.cdio.CDDAReader object*/
typedef struct cdio_CDDAReader_s {
    PyObject_HEAD
    int is_cd_image;
    int is_logging;
    struct cdio_log log;
    union {
        struct {
            CdIo_t *image;
            lsn_t current_sector;
            lsn_t final_sector;
        } image;
        struct {
            cdrom_drive_t *drive;
            cdrom_paranoia_t *paranoia;
            lsn_t current_sector;
            lsn_t final_sector;
        } drive;
    } _;
    int (*first_track_num)(struct cdio_CDDAReader_s *self);
    int (*last_track_num)(struct cdio_CDDAReader_s *self);
    int (*track_lsn)(struct cdio_CDDAReader_s *self, int track_num);
    int (*track_last_lsn)(struct cdio_CDDAReader_s *self, int track_num);
    int (*first_sector)(struct cdio_CDDAReader_s *self);
    int (*last_sector)(struct cdio_CDDAReader_s *self);
    int (*read)(struct cdio_CDDAReader_s *self,
                unsigned to_read,
                int *samples);
    unsigned (*seek)(struct cdio_CDDAReader_s *self, unsigned sector);
    void (*set_speed)(struct cdio_CDDAReader_s *self, int new_speed);
    void (*dealloc)(struct cdio_CDDAReader_s *self);

    int closed;
    PyObject *audiotools_pcm;
} cdio_CDDAReader;

static PyObject*
CDDAReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

static int
CDDAReader_init(cdio_CDDAReader *self, PyObject *args, PyObject *kwds);

static int
CDDAReader_init_image(cdio_CDDAReader *self, const char *device);

static int
CDDAReader_init_device(cdio_CDDAReader *self, const char *device);

static void
CDDAReader_dealloc(cdio_CDDAReader *self);

static void
CDDAReader_dealloc_image(cdio_CDDAReader *self);

static void
CDDAReader_dealloc_device(cdio_CDDAReader *self);

static PyObject*
CDDAReader_sample_rate(cdio_CDDAReader *self, void *closure);

static PyObject*
CDDAReader_bits_per_sample(cdio_CDDAReader *self, void *closure);

static PyObject*
CDDAReader_channels(cdio_CDDAReader *self, void *closure);

static PyObject*
CDDAReader_channel_mask(cdio_CDDAReader *self, void *closure);

static PyObject*
CDDAReader_is_cd_image(cdio_CDDAReader *self, void *closure);

static int
CDDAReader_first_track_num_image(cdio_CDDAReader *self);

static int
CDDAReader_first_track_num_device(cdio_CDDAReader *self);

static int
CDDAReader_last_track_num_image(cdio_CDDAReader *self);

static int
CDDAReader_last_track_num_device(cdio_CDDAReader *self);

static int
CDDAReader_track_lsn_image(cdio_CDDAReader *self, int track_num);

static int
CDDAReader_track_lsn_device(cdio_CDDAReader *self, int track_num);

static int
CDDAReader_track_last_lsn_image(cdio_CDDAReader *self, int track_num);

static int
CDDAReader_track_last_lsn_device(cdio_CDDAReader *self, int track_num);

static PyObject*
CDDAReader_track_offsets(cdio_CDDAReader *self, void *closure);

static PyObject*
CDDAReader_track_lengths(cdio_CDDAReader *self, void *closure);

static PyObject*
CDDAReader_first_sector(cdio_CDDAReader *self, void *closure);

static int
CDDAReader_first_sector_image(cdio_CDDAReader *self);

static int
CDDAReader_first_sector_device(cdio_CDDAReader *self);

static PyObject*
CDDAReader_last_sector(cdio_CDDAReader *self, void *closure);

static int
CDDAReader_last_sector_image(cdio_CDDAReader *self);

static int
CDDAReader_last_sector_device(cdio_CDDAReader *self);

static PyGetSetDef CDDAReader_getseters[] = {
    {"sample_rate",
     (getter)CDDAReader_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)CDDAReader_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)CDDAReader_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)CDDAReader_channel_mask, NULL, "channel mask", NULL},
    {"is_cd_image",
     (getter)CDDAReader_is_cd_image, NULL, "is CD image", NULL},
    {"track_offsets",
     (getter)CDDAReader_track_offsets, NULL, "track offsets", NULL},
    {"track_lengths",
     (getter)CDDAReader_track_lengths, NULL, "track lengths", NULL},
    {"first_sector",
     (getter)CDDAReader_first_sector, NULL, "first sector", NULL},
    {"last_sector",
     (getter)CDDAReader_last_sector, NULL, "last sector", NULL},
    {NULL}
};

static PyObject*
CDDAReader_read(cdio_CDDAReader* self, PyObject *args);

static int
CDDAReader_read_image(cdio_CDDAReader *self,
                      unsigned sectors_to_read,
                      int *samples);

static int
CDDAReader_read_device(cdio_CDDAReader *self,
                       unsigned sectors_to_read,
                       int *samples);

static PyObject*
CDDAReader_seek(cdio_CDDAReader* self, PyObject *args);

static unsigned
CDDAReader_seek_image(cdio_CDDAReader *self, unsigned sector);

static unsigned
CDDAReader_seek_device(cdio_CDDAReader *self, unsigned sector);

static PyObject*
CDDAReader_close(cdio_CDDAReader* self, PyObject *args);

static PyObject*
CDDAReader_set_speed(cdio_CDDAReader *self, PyObject *args);

static void
CDDAReader_set_speed_image(cdio_CDDAReader *self, int new_speed);

static void
CDDAReader_set_speed_device(cdio_CDDAReader *self, int new_speed);

static int
cddareader_set_log_item(PyObject *dict, const char *key, int value);

static PyObject*
CDDAReader_log(cdio_CDDAReader *self, PyObject *args);

static PyObject*
CDDAReader_reset_log(cdio_CDDAReader *self, PyObject *args);

static void
cddareader_reset_log(struct cdio_log *log);

static PyMethodDef CDDAReader_methods[] = {
    {"read", (PyCFunction)CDDAReader_read,
     METH_VARARGS, "read(pcm_frames) -> Framelist"},
    {"seek", (PyCFunction)CDDAReader_seek,
     METH_VARARGS, "seek(pcm_frames)"},
    {"close", (PyCFunction)CDDAReader_close,
     METH_NOARGS, "closes CD stream"},
    {"set_speed", (PyCFunction)CDDAReader_set_speed,
     METH_VARARGS, "set_speed(speed)"},
    {"log", (PyCFunction)CDDAReader_log,
     METH_NOARGS, "log() -> {item:value, ...}"},
    {"reset_log", (PyCFunction)CDDAReader_reset_log,
     METH_NOARGS, "resets read log"},
    {NULL}
};

static PyTypeObject cdio_CDDAReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "cdio.CDDAReader",         /*tp_name*/
    sizeof(cdio_CDDAReader),   /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CDDAReader_dealloc, /*tp_dealloc*/
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
    "CDDAReader objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    CDDAReader_methods,        /* tp_methods */
    0,                         /* tp_members */
    CDDAReader_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CDDAReader_init, /* tp_init */
    0,                         /* tp_alloc */
    CDDAReader_new,            /* tp_new */
};
