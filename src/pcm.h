#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

#include <stdint.h>

typedef struct {
  PyObject_HEAD;

  int frames;          /*the total number of PCM frames in this FrameList
			 aka the total number of rows in the "samples" array*/
  int channels;        /*the total number of channels in this FrameList
			 aka the total number of columns in "samples*/
  int bits_per_sample; /*the maximum size of each sample, in bits*/
  int is_signed;       /*1 if the samples are signed, 0 if unsigned*/

  int32_t* samples;    /*the actual sample data itself,
			 stored raw as 32-bit signed integers*/
  uint32_t samples_length; /*the total number of samples
			     which must be evenly distributable
			     between channels and bits-per-sample*/
} pcm_FrameList;

void FrameList_dealloc(pcm_FrameList* self);

PyObject *FrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int FrameList_init(pcm_FrameList *self, PyObject *args, PyObject *kwds);

int FrameList_CheckExact(PyObject *o);

PyObject* FrameList_frames(pcm_FrameList *self, void* closure);

PyObject* FrameList_channels(pcm_FrameList *self, void* closure);

PyObject* FrameList_bits_per_sample(pcm_FrameList *self, void* closure);

PyObject* FrameList_signed(pcm_FrameList *self, void* closure);

Py_ssize_t FrameList_len(pcm_FrameList *o);

PyObject* FrameList_GetItem(pcm_FrameList *o, Py_ssize_t i);

PyObject* FrameList_frame(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_channel(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_to_bytes(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_set_signed(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_set_unsigned(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_split(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_concat(pcm_FrameList *a, PyObject *bb);

PyObject* FrameList_from_list(PyObject *dummy, PyObject *args);

PyObject* FrameList_from_frames(PyObject *dummy, PyObject *args);

PyObject* FrameList_from_channels(PyObject *dummy, PyObject *args);

PyMethodDef module_methods[] = {
  {"from_list",(PyCFunction)FrameList_from_list,
   METH_VARARGS,"Converts a list of PCM integers to a FrameList"},
  {"from_frames",(PyCFunction)FrameList_from_frames,
   METH_VARARGS,"Converts a list of FrameList frames to a FrameList"},
  {"from_channels",(PyCFunction)FrameList_from_channels,
   METH_VARARGS,"Converts a list of FrameList channels to a FrameList"},
  {NULL}
};

PyGetSetDef FrameList_getseters[] = {
    {"frames", (getter)FrameList_frames, 0, "frame count", NULL},
    {"channels", (getter)FrameList_channels, 0, "channel count", NULL},
    {"bits_per_sample", (getter)FrameList_bits_per_sample,
     0, "bits per sample", NULL},
    {"signed", (getter)FrameList_signed, 0, "signed", NULL},
    {NULL}  /* Sentinel */
};

PyMethodDef FrameList_methods[] = {
  {"frame", (PyCFunction)FrameList_frame,
   METH_VARARGS,"Reads the given frame from the framelist"},
  {"channel", (PyCFunction)FrameList_channel,
   METH_VARARGS,"Reads the given channel from the framelist"},
  {"to_bytes", (PyCFunction)FrameList_to_bytes,
   METH_VARARGS,"Converts the framelist to a binary string"},
  {"set_signed", (PyCFunction)FrameList_set_signed,
   METH_NOARGS,"Sets the framelist's data to be signed"},
  {"set_unsigned", (PyCFunction)FrameList_set_unsigned,
   METH_NOARGS,"Sets the framelist's data to be unsigned"},
  {"split", (PyCFunction)FrameList_split,
   METH_VARARGS,"Splits the framelist into 2 sub framelists by number of frames"},
  {NULL}
};

static PySequenceMethods pcm_FrameListType_as_sequence = {
	(lenfunc)FrameList_len,		/* sq_length */
	(binaryfunc)FrameList_concat,	/* sq_concat */
	(ssizeargfunc)NULL,		/* sq_repeat */
	(ssizeargfunc)FrameList_GetItem, /* sq_item */
	(ssizessizeargfunc)NULL,        /* sq_slice */
	(ssizeobjargproc)NULL,		/* sq_ass_item */
	(ssizessizeobjargproc)NULL,	/* sq_ass_slice */
	(objobjproc)NULL,		/* sq_contains */
	(binaryfunc)NULL,               /* sq_inplace_concat */
	(ssizeargfunc)NULL,             /* sq_inplace_repeat */
};

PyTypeObject pcm_FrameListType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "pcm.FrameList",           /*tp_name*/
    sizeof(pcm_FrameList),     /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)FrameList_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    &pcm_FrameListType_as_sequence, /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "FrameList objects",       /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    FrameList_methods,         /* tp_methods */
    0,                         /* tp_members */
    FrameList_getseters,       /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)FrameList_init,  /* tp_init */
    0,                         /* tp_alloc */
    FrameList_new,             /* tp_new */
};

typedef int32_t (*FrameList_char_to_int_converter)(unsigned char *s);

void FrameList_char_to_samples(int32_t *samples,
			       unsigned char *data,
			       FrameList_char_to_int_converter converter,
			       uint32_t samples_length,
			       int bits_per_sample);

FrameList_char_to_int_converter FrameList_get_char_to_int_converter(
					      int bits_per_sample,
					      int is_big_endian,
					      int is_signed);

int32_t FrameList_S8_char_to_int(unsigned char *s);
int32_t FrameList_U8_char_to_int(unsigned char *s);

int32_t FrameList_SL16_char_to_int(unsigned char *s);
int32_t FrameList_SB16_char_to_int(unsigned char *s);
int32_t FrameList_UL16_char_to_int(unsigned char *s);
int32_t FrameList_UB16_char_to_int(unsigned char *s);

int32_t FrameList_SL24_char_to_int(unsigned char *s);
int32_t FrameList_SB24_char_to_int(unsigned char *s);
int32_t FrameList_UL24_char_to_int(unsigned char *s);
int32_t FrameList_UB24_char_to_int(unsigned char *s);


typedef void (*FrameList_int_to_char_converter)(int32_t i, unsigned char *s);

void FrameList_samples_to_char(unsigned char *data,
			       int32_t *samples,
			       FrameList_int_to_char_converter converter,
			       uint32_t samples_length,
			       int bits_per_sample);

FrameList_int_to_char_converter FrameList_get_int_to_char_converter(
                                              int bits_per_sample,
                                              int is_big_endian,
                                              int is_signed);

void FrameList_int_to_S8_char(int32_t i, unsigned char *s);
void FrameList_int_to_U8_char(int32_t i, unsigned char *s);

void FrameList_int_to_UB16_char(int32_t i, unsigned char *s);
void FrameList_int_to_SB16_char(int32_t i, unsigned char *s);
void FrameList_int_to_UL16_char(int32_t i, unsigned char *s);
void FrameList_int_to_SL16_char(int32_t i, unsigned char *s);

void FrameList_int_to_UB24_char(int32_t i, unsigned char *s);
void FrameList_int_to_SB24_char(int32_t i, unsigned char *s);
void FrameList_int_to_UL24_char(int32_t i, unsigned char *s);
void FrameList_int_to_SL24_char(int32_t i, unsigned char *s);
