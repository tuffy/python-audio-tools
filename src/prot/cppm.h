#include <Python.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

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

typedef struct {
    PyObject_HEAD

    int        media_type;     /*read from DVD side data*/
    uint64_t   media_key;      /*read from AUDIO_TS/DVDAUDIO.MKB file*/
    uint64_t   id_album_media; /*pulled from DVD side data*/
} prot_CPPMDecoder;

/*the CPPMDecoder.__init__() method*/
int
CPPMDecoder_init(prot_CPPMDecoder *self,
                 PyObject *args, PyObject *kwds);

static PyObject*
CPPMDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds);

void
CPPMDecoder_dealloc(prot_CPPMDecoder *self);

static PyObject*
CPPMDecoder_media_type(prot_CPPMDecoder *self, void *closure);

static PyObject*
CPPMDecoder_media_key(prot_CPPMDecoder *self, void *closure);

static PyObject*
CPPMDecoder_id_album_media(prot_CPPMDecoder *self, void *closure);

PyGetSetDef CPPMDecoder_getseters[] = {
    {"media_type",
     (getter)CPPMDecoder_media_type, NULL, "media_type", NULL},
    {"media_key",
     (getter)CPPMDecoder_media_key, NULL, "media_key", NULL},
    {"id_album_media",
     (getter)CPPMDecoder_id_album_media, NULL, "id_album_media", NULL},
    {NULL}
};

static PyObject*
CPPMDecoder_decode(prot_CPPMDecoder *self, PyObject *args);

PyMethodDef CPPMDecoder_methods[] = {
    {"decode", (PyCFunction)CPPMDecoder_decode,
     METH_VARARGS, "Decodes one or more 2048 byte blocks"},
    {NULL}
};

PyTypeObject prot_CPPMDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "prot.CPPMDecoder",    /*tp_name*/
    sizeof(prot_CPPMDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)CPPMDecoder_dealloc, /*tp_dealloc*/
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
    "CPPMDecoder objects", /* tp_doc */
    0,                     /* tp_traverse */
    0,                     /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    0,                     /* tp_iter */
    0,                     /* tp_iternext */
    CPPMDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    CPPMDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)CPPMDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    CPPMDecoder_new,           /* tp_new */
};

typedef enum {COPYRIGHT_PROTECTION_NONE = 0,
              COPYRIGHT_PROTECTION_CPPM = 1} protection;

typedef struct {
    uint8_t  col;
    uint16_t row;
    uint64_t key;
} device_key_t;

int
cppm_init(prot_CPPMDecoder *p_ctx,
          char *dvd_dev,
          char *psz_file);

int
cppm_set_id_album(prot_CPPMDecoder *p_ctx,
                  int i_fd);

uint8_t*
cppm_get_mkb(char *psz_mkb);

int
cppm_process_mkb(uint8_t *p_mkb,
                 device_key_t *p_dev_keys,
                 int nr_dev_keys,
                 uint64_t *p_media_key);

int
cppm_decrypt(prot_CPPMDecoder *p_ctx,
             uint8_t *p_buffer,
             int nr_blocks,
             int preserve_cci);

int
cppm_decrypt_block(prot_CPPMDecoder *p_ctx,
                   uint8_t *p_buffer,
                   int preserve_cci);

/*given a block of raw AOB data, determine if its protection bit is set*/
int
mpeg2_check_pes_scrambling_control(uint8_t *p_block);

/*sets a block's protection bit to 0*/
void
mpeg2_reset_pes_scrambling_control(uint8_t *p_block);

/*locates a block's CCI bit and sets it to 0*/
void
mpeg2_reset_cci(uint8_t *p_block);
