#include <Python.h>
#include <stdint.h>
#include "../bitstream_r.h"
#include "../array.h"

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

typedef struct {
  PyObject_HEAD

  char* filename;
  FILE* file;
  Bitstream* bitstream;

  int sample_rate;
  int channels;
  int channel_mask;
  int bits_per_sample;

  int total_frames;

  /*a bunch of decoding fields pulled from the stream's 'alac' atom*/
  int max_samples_per_frame;
  int history_multiplier;
  int initial_history;
  int maximum_k;

  struct ia_array samples;
  struct ia_array subframe_samples; /*a sample buffer for subframe output*/
  struct ia_array wasted_bits_samples;  /*a buffer for wasted-bits samples*/
  struct ia_array residuals; /*a buffer for residual values*/
} decoders_ALACDecoder;

struct alac_frame_header {
  uint8_t channels;
  uint8_t has_size;
  uint8_t wasted_bits;
  uint8_t is_not_compressed;
  uint32_t output_samples;
};

struct alac_subframe_header {
  uint8_t prediction_type;
  uint8_t prediction_quantitization;
  uint8_t rice_modifier;
  struct i_array predictor_coef_table;
};

typedef enum {OK,ERROR} status;

/*the ALACDecoder.sample_rate attribute getter*/
static PyObject *ALACDecoder_sample_rate(decoders_ALACDecoder *self,
					 void *closure);

/*the ALACDecoder.bits_per_sample attribute getter*/
static PyObject *ALACDecoder_bits_per_sample(decoders_ALACDecoder *self,
					     void *closure);

/*the ALACDecoder.channels attribute getter*/
static PyObject *ALACDecoder_channels(decoders_ALACDecoder *self,
				      void *closure);

/*the ALACDecoder.channel_mask attribute getter*/
static PyObject *ALACDecoder_channel_mask(decoders_ALACDecoder *self,
					  void *closure);

/*the ALACDecoder.read() method*/
PyObject *ALACDecoder_read(decoders_ALACDecoder* self,
			   PyObject *args);

/*the ALACDecoder.close() method*/
PyObject *ALACDecoder_close(decoders_ALACDecoder* self,
			    PyObject *args);

/*the ALACDecoder.__init__() method*/
int ALACDecoder_init(decoders_ALACDecoder *self,
		     PyObject *args, PyObject *kwds);

/*walks through the open QuickTime stream looking for the 'mdat' atom
  or returns ERROR if one cannot be found*/
status ALACDecoder_seek_mdat(decoders_ALACDecoder *self);

/*reads "frame_header" from the current bitstream*/
status ALACDecoder_read_frame_header(Bitstream *bs,
				     struct alac_frame_header *frame_header,
				     int max_samples_per_frame);

/*reads "subframe header" from the current bitstream*/
status ALACDecoder_read_subframe_header(Bitstream *bs,
					struct alac_subframe_header *subframe_header);

/*reads a block of "wasted_bits" samples from the current bitstream*/
status ALACDecoder_read_wasted_bits(Bitstream *bs,
				    struct ia_array *wasted_bits_samples,
				    int sample_count,
				    int channels,
				    int wasted_bits_size);

/*reads a block of residuals from the current bitstream*/
status ALACDecoder_read_residuals(Bitstream *bs,
				  struct i_array *residuals,
				  int residual_count,
				  int sample_size,
				  int initial_history,
				  int history_multiplier,
				  int maximum_k);

/*reads a signel residual from the current bitstream*/
int ALACDecoder_read_residual(Bitstream *bs,
			      int k,
			      int sample_size);

/*takes a set of residuals, coefficients and a predictor_quantitization value
  returns a set of decoded samples*/
status ALACDecoder_decode_subframe(struct i_array *samples,
				   struct i_array *residuals,
				   struct i_array *coefficients,
				   int predictor_quantitization);

status ALACDecoder_decorrelate_mono(struct ia_array *output,
				    struct ia_array *subframes);

status ALACDecoder_decorrelate_stereo_16(struct ia_array *output,
					 struct ia_array *subframes,
					 int interlacing_shift,
					 int interlacing_leftweight);

/*after a call to "read_subframe_header",
  call "free_subframe_header" to deallocate the predictor_coef_tables*/
static inline void ALACDecoder_free_subframe_header(struct alac_subframe_header *subframe_header) {
  ia_free(&(subframe_header->predictor_coef_table));
}

/*simple routines*/
void ALACDecoder_print_frame_header(struct alac_frame_header *frame_header);

void ALACDecoder_print_subframe_header(struct alac_subframe_header *subframe_header);

PyGetSetDef ALACDecoder_getseters[] = {
  {"sample_rate",
   (getter)ALACDecoder_sample_rate, NULL, "sample rate", NULL},
  {"bits_per_sample",
   (getter)ALACDecoder_bits_per_sample, NULL, "bits per sample", NULL},
  {"channels",
   (getter)ALACDecoder_channels, NULL, "channels", NULL},
  {"channel_mask",
   (getter)ALACDecoder_channel_mask, NULL, "channel_mask", NULL},
  {NULL}
};

PyMethodDef ALACDecoder_methods[] = {
  {"read", (PyCFunction)ALACDecoder_read,
   METH_VARARGS,"Reads the given number of bytes from the ALAC file, if possible"},
  {"close", (PyCFunction)ALACDecoder_close,
   METH_NOARGS,"Closes the ALAC decoder stream"},
  {NULL}
};

void ALACDecoder_dealloc(decoders_ALACDecoder *self);

PyObject *ALACDecoder_new(PyTypeObject *type,
			  PyObject *args, PyObject *kwds);

PyTypeObject decoders_ALACDecoderType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.ALACDecoder",    /*tp_name*/
    sizeof(decoders_ALACDecoder), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ALACDecoder_dealloc, /*tp_dealloc*/
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
    "ALACDecoder objects",     /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    ALACDecoder_methods,       /* tp_methods */
    0,                         /* tp_members */
    ALACDecoder_getseters,     /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ALACDecoder_init,/* tp_init */
    0,                         /* tp_alloc */
    ALACDecoder_new,           /* tp_new */
};
