#ifndef PCM_H
#define PCM_H

#ifndef STANDALONE
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
#endif

#include <stdint.h>
#include "array.h"

/******************
  FrameList Object
*******************/

#ifndef STANDALONE
typedef struct {
  PyObject_HEAD;

  int frames;          /*the total number of PCM frames in this FrameList
			 aka the total number of rows in the "samples" array*/
  int channels;        /*the total number of channels in this FrameList
			 aka the total number of columns in "samples*/
  int bits_per_sample; /*the maximum size of each sample, in bits*/
  int is_signed;       /*1 if the samples are signed, 0 if unsigned*/

  ia_data_t* samples;    /*the actual sample data itself,
			   stored raw as 32-bit signed integers*/
  ia_size_t samples_length; /*the total number of samples
			     which must be evenly distributable
			     between channels and bits-per-sample*/
} pcm_FrameList;

void FrameList_dealloc(pcm_FrameList* self);

PyObject *FrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int FrameList_init(pcm_FrameList *self, PyObject *args, PyObject *kwds);

/*generates a new pcm_FrameList object via _PyObject_New
  whose fields *must* be populated by additional C code*/
pcm_FrameList* FrameList_create(void);

PyObject* FrameList_blank(PyObject *dummy, PyObject *args);

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

PyObject* FrameList_copy(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_to_float(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_frame_count(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_split(pcm_FrameList *self, PyObject *args);

PyObject* FrameList_concat(pcm_FrameList *a, PyObject *bb);

PyObject* FrameList_from_list(PyObject *dummy, PyObject *args);

PyObject* FrameList_from_frames(PyObject *dummy, PyObject *args);

PyObject* FrameList_from_channels(PyObject *dummy, PyObject *args);


/***********************
  FloatFrameList Object
************************/

typedef struct {
  PyObject_HEAD;

  int frames;          /*the total number of PCM frames in this FrameList
			 aka the total number of rows in the "samples" array*/
  int channels;        /*the total number of channels in this FrameList
			 aka the total number of columns in "samples*/

  fa_data_t *samples;  /*the actual sample data itself,
			 stored raw as doubles*/
  fa_size_t samples_length; /*the total number of samples
			     which must be evenly distributable
			     between channels and bits-per-sample*/
} pcm_FloatFrameList;

void FloatFrameList_dealloc(pcm_FloatFrameList* self);

PyObject *FloatFrameList_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int FloatFrameList_init(pcm_FloatFrameList *self, PyObject *args, PyObject *kwds);

int FloatFrameList_CheckExact(PyObject *o);

PyObject* FloatFrameList_blank(PyObject *dummy, PyObject *args);

pcm_FloatFrameList* FloatFrameList_create(void);

PyObject* FloatFrameList_frames(pcm_FloatFrameList *self, void* closure);

PyObject* FloatFrameList_channels(pcm_FloatFrameList *self, void* closure);

Py_ssize_t FloatFrameList_len(pcm_FloatFrameList *o);

PyObject* FloatFrameList_GetItem(pcm_FloatFrameList *o, Py_ssize_t i);

PyObject* FloatFrameList_frame(pcm_FloatFrameList *self, PyObject *args);

PyObject* FloatFrameList_channel(pcm_FloatFrameList *self, PyObject *args);

PyObject* FloatFrameList_copy(pcm_FloatFrameList *self, PyObject *args);

PyObject* FloatFrameList_to_int(pcm_FloatFrameList *self, PyObject *args);

PyObject* FloatFrameList_split(pcm_FloatFrameList *self, PyObject *args);

PyObject* FloatFrameList_concat(pcm_FloatFrameList *a, PyObject *bb);

PyObject* FloatFrameList_from_frames(PyObject *dummy, PyObject *args);

PyObject* FloatFrameList_from_channels(PyObject *dummy, PyObject *args);

#endif

typedef ia_data_t (*FrameList_char_to_int_converter)(unsigned char *s);

void FrameList_char_to_samples(ia_data_t *samples,
			       unsigned char *data,
			       FrameList_char_to_int_converter converter,
			       ia_size_t samples_length,
			       int bits_per_sample);

FrameList_char_to_int_converter FrameList_get_char_to_int_converter(
					      int bits_per_sample,
					      int is_big_endian,
					      int is_signed);

ia_data_t FrameList_S8_char_to_int(unsigned char *s);
ia_data_t FrameList_U8_char_to_int(unsigned char *s);

ia_data_t FrameList_SL16_char_to_int(unsigned char *s);
ia_data_t FrameList_SB16_char_to_int(unsigned char *s);
ia_data_t FrameList_UL16_char_to_int(unsigned char *s);
ia_data_t FrameList_UB16_char_to_int(unsigned char *s);

ia_data_t FrameList_SL24_char_to_int(unsigned char *s);
ia_data_t FrameList_SB24_char_to_int(unsigned char *s);
ia_data_t FrameList_UL24_char_to_int(unsigned char *s);
ia_data_t FrameList_UB24_char_to_int(unsigned char *s);


typedef void (*FrameList_int_to_char_converter)(ia_data_t i, unsigned char *s);

void FrameList_samples_to_char(unsigned char *data,
			       ia_data_t *samples,
			       FrameList_int_to_char_converter converter,
			       ia_size_t samples_length,
			       int bits_per_sample);

FrameList_int_to_char_converter FrameList_get_int_to_char_converter(
                                              int bits_per_sample,
                                              int is_big_endian,
                                              int is_signed);

void FrameList_int_to_S8_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_U8_char(ia_data_t i, unsigned char *s);

void FrameList_int_to_UB16_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_SB16_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_UL16_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_SL16_char(ia_data_t i, unsigned char *s);

void FrameList_int_to_UB24_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_SB24_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_UL24_char(ia_data_t i, unsigned char *s);
void FrameList_int_to_SL24_char(ia_data_t i, unsigned char *s);

#endif
