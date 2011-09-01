#include "alac.h"
#include "../pcm.h"
#include "pcm.h"

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

int
ALACDecoder_init(decoders_ALACDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    char *filename;
    int i;
    static char *kwlist[] = {"filename",
                             "sample_rate",
                             "channels",
                             "channel_mask",
                             "bits_per_sample",
                             "total_frames",
                             "max_samples_per_frame",
                             "history_multiplier",
                             "initial_history",
                             "maximum_k",
                             NULL};
    int total_frames;

    self->filename = NULL;
    self->file = NULL;
    self->bitstream = NULL;
    self->data_allocated = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "siiiiiiiii", kwlist,
                                     &filename,
                                     &(self->sample_rate),
                                     &(self->channels),
                                     &(self->channel_mask),
                                     &(self->bits_per_sample),
                                     &total_frames,
                                     &(self->max_samples_per_frame),
                                     &(self->history_multiplier),
                                     &(self->initial_history),
                                     &(self->maximum_k)))
        return -1;

    if (self->sample_rate < 1) {
        PyErr_SetString(PyExc_ValueError, "sample_rate must be > 0");
        return -1;
    }
    if (self->channels < 1) {
        PyErr_SetString(PyExc_ValueError, "channels must be > 0");
        return -1;
    }
    if (self->channel_mask < 0) {
        PyErr_SetString(PyExc_ValueError, "channel_mask must be >= 0");
        return -1;
    }
    if ((self->bits_per_sample != 16) &&
        (self->bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 16 or 24");
        return -1;
    }
    if (total_frames < 0) {
        PyErr_SetString(PyExc_ValueError, "total_frames must be >= 0");
        return -1;
    }
    if (self->history_multiplier < 1) {
        PyErr_SetString(PyExc_ValueError, "history_multiplier must be > 0");
        return -1;
    }
    if (self->initial_history < 0) {
        PyErr_SetString(PyExc_ValueError, "initial_history must be >= 0");
        return -1;
    }
    if (self->maximum_k < 1) {
        PyErr_SetString(PyExc_ValueError, "maximum_k must be > 0");
        return -1;
    }

    self->total_samples = total_frames * self->channels;

    /*initialize final buffer*/
    iaa_init(&(self->samples),
             self->channels,
             self->max_samples_per_frame);

    /*initialize wasted-bits buffer, just in case*/
    iaa_init(&(self->wasted_bits_samples),
             self->channels,
             self->max_samples_per_frame);

    /*initialize a residuals buffer*/
    iaa_init(&(self->residuals),
             self->channels,
             self->max_samples_per_frame);

    /*initialize a subframe output buffer,
      whose data is not yet decorrelated*/
    iaa_init(&(self->subframe_samples),
             self->channels,
             self->max_samples_per_frame);

    /*initialize a list of subframe headers, one per channel*/
    self->subframe_headers = malloc(sizeof(struct alac_subframe_header) *
                                    self->channels);
    for (i = 0; i < self->channels; i++) {
        ia_init(&(self->subframe_headers[i].predictor_coef_table), 8);
    }

    self->data_allocated = 1;

    /*open the alac file*/
    if ((self->file = fopen(filename, "rb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = br_open(self->file, BS_BIG_ENDIAN);
    }
    self->filename = strdup(filename);

    /*seek to the 'mdat' atom, which contains the ALAC stream*/
    if (ALACDecoder_seek_mdat(self) == ERROR) {
        PyErr_SetString(PyExc_ValueError,
                        "Unable to locate 'mdat' atom in stream");
        return -1;
    }

    return 0;
}

void
ALACDecoder_dealloc(decoders_ALACDecoder *self)
{
    int i;

    if (self->data_allocated) {
        for (i = 0; i < self->channels; i++)
            ia_free(&(self->subframe_headers[i].predictor_coef_table));

        free(self->subframe_headers);
        free(self->filename);
        iaa_free(&(self->samples));
        iaa_free(&(self->subframe_samples));
        iaa_free(&(self->wasted_bits_samples));
        iaa_free(&(self->residuals));

        if (self->bitstream != NULL)
            /*this closes self->file also*/
            self->bitstream->close(self->bitstream);
    }

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
ALACDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_ALACDecoder *self;

    self = (decoders_ALACDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
ALACDecoder_sample_rate(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
ALACDecoder_bits_per_sample(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->bits_per_sample);
}

static PyObject*
ALACDecoder_channels(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->channels);
}

static PyObject*
ALACDecoder_channel_mask(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->channel_mask);
}


static PyObject*
ALACDecoder_read(decoders_ALACDecoder* self, PyObject *args)
{
    int current_channel = 0;
    int frame_channels;
    struct alac_frame_header frame_header;
    struct ia_array frame_samples;
    struct ia_array frame_subframe_samples;
    struct ia_array frame_wasted_bits;
    struct ia_array frame_residuals;

    int interlacing_shift;
    int interlacing_leftweight;

    int channel;
    int i, j;
    PyThreadState *thread_state;

    frame_header.output_samples = 0;
    iaa_reset(&(self->samples));

    if (self->total_samples < 1)
        goto write_frame;

    thread_state = PyEval_SaveThread();

    if (!setjmp(*br_try(self->bitstream))) {
        for (frame_channels = self->bitstream->read(self->bitstream, 3) + 1;
             frame_channels != 8;
             current_channel += frame_channels,
             frame_channels = self->bitstream->read(self->bitstream, 3) + 1) {

            /*initialize a set of partial output arrays
              as subset of our total output*/
            iaa_link(&frame_samples, &(self->samples));
            iaa_link(&frame_subframe_samples, &(self->subframe_samples));
            iaa_link(&frame_wasted_bits, &(self->wasted_bits_samples));
            iaa_link(&frame_residuals, &(self->residuals));
            frame_samples.arrays += current_channel;
            frame_samples.size = frame_channels;
            frame_subframe_samples.arrays += current_channel;
            frame_subframe_samples.size = frame_channels;
            frame_wasted_bits.arrays += current_channel;
            frame_wasted_bits.size = frame_channels;
            frame_residuals.arrays += current_channel;
            frame_residuals.size = frame_channels;

            ALACDecoder_read_frame_header(self->bitstream,
                                          &frame_header,
                                          self->max_samples_per_frame);

            if (frame_header.is_not_compressed) {
                /*uncompressed samples are interlaced between channels*/
                for (i = 0; i < frame_header.output_samples; i++)
                    for (channel = 0; channel < frame_channels; channel++)
                        ia_append(&(frame_samples.arrays[channel]),
                                  self->bitstream->read_signed(
                                                      self->bitstream,
                                                      self->bits_per_sample));
            } else {
                interlacing_shift =
                    self->bitstream->read(self->bitstream, 8);
                interlacing_leftweight =
                    self->bitstream->read(self->bitstream, 8);

                /*read the subframe headers*/
                for (i = 0; i < frame_channels; i++) {
                    ALACDecoder_read_subframe_header(
                            self->bitstream,
                            &(self->subframe_headers[current_channel + i]));
                    /*sanity check substream headers*/
                    if (self->subframe_headers[current_channel + i
                                               ].predictor_coef_table.size < 1) {
                        PyEval_RestoreThread(thread_state);
                        PyErr_SetString(PyExc_ValueError,
                                        "coefficient count must be greater than 0");
                        goto error;
                    }

                    if (self->subframe_headers[current_channel + i
                                               ].prediction_type != 0) {
                        PyEval_RestoreThread(thread_state);
                        PyErr_SetString(PyExc_ValueError,
                                        "unsupported prediction type");
                        goto error;
                    }
                }

                /*if there are wasted bits, read a block of interlaced
                  wasted-bits samples, each (wasted_bits * 8) large*/
                if (frame_header.wasted_bits > 0) {
                    iaa_reset(&frame_wasted_bits);
                    ALACDecoder_read_wasted_bits(self->bitstream,
                                                 &frame_wasted_bits,
                                                 frame_header.output_samples,
                                                 frame_channels,
                                                 frame_header.wasted_bits * 8);
                }

                /*then read in one residual block per frame channel*/
                for (i = 0; i < frame_channels; i++)
                    ALACDecoder_read_residuals(self->bitstream,
                                               &(frame_residuals.arrays[i]),
                                               frame_header.output_samples,
                                               self->bits_per_sample -
                                               (frame_header.wasted_bits * 8) +
                                               frame_channels - 1,
                                               self->initial_history,
                                               self->history_multiplier,
                                               self->maximum_k);

                /*decode the residuals into subframe_samples*/
                for (i = 0; i < frame_channels; i++)
                    ALACDecoder_decode_subframe(
                          &(frame_subframe_samples.arrays[i]),
                          &(frame_residuals.arrays[i]),
                          &(self->subframe_headers[
                            current_channel + i].predictor_coef_table),
                          self->subframe_headers[
                            current_channel + i].prediction_quantitization);

                /*perform channel decorrelation*/
                ALACDecoder_decorrelate_channels(
                          &frame_samples,
                          &frame_subframe_samples,
                          interlacing_shift,
                          interlacing_leftweight);

                /*finally, apply any wasted bits, if present*/
                if (frame_header.wasted_bits > 0) {
                    for (i = 0; i < frame_channels; i++)
                        for (j = 0; j < frame_header.output_samples; j++)
                            frame_samples.arrays[i].data[j] =
                                ((frame_samples.arrays[i].data[j] <<
                                  (frame_header.wasted_bits * 8)) |
                                 frame_wasted_bits.arrays[i].data[j]);
                }
            }

            /*whether compressed or uncompressed,
              deduct the frame's total samples from our remaining total*/
            self->total_samples -= (frame_header.output_samples *
                                    frame_channels);
        }

        /*once the '111' stop value has been read,
          byte align the stream for the next frame*/
        self->bitstream->byte_align(self->bitstream);
    } else {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError,
                        "EOF during frame reading");
        goto error;
    }

    br_etry(self->bitstream);
    PyEval_RestoreThread(thread_state);

 write_frame:
    /*transform the contents of self->samples into a pcm.FrameList object*/
    return ia_array_to_framelist(&(self->samples),
                                 self->bits_per_sample);
 error:
    br_etry(self->bitstream);

    return NULL;
}

static PyObject*
i_array_to_list(struct i_array *list)
{
    PyObject* toreturn;
    PyObject* item;
    ia_size_t i;

    if ((toreturn = PyList_New(0)) == NULL)
        return NULL;
    else {
        for (i = 0; i < list->size; i++) {
            item = PyInt_FromLong(list->data[i]);
            PyList_Append(toreturn, item);
            Py_DECREF(item);
        }
        return toreturn;
    }
}

static PyObject*
ia_array_to_list(struct ia_array *list)
{
    PyObject *toreturn;
    PyObject *sub_list;
    ia_size_t i;

    if ((toreturn = PyList_New(0)) == NULL)
        return NULL;
    else {
        for (i = 0; i < list->size; i++) {
            sub_list = i_array_to_list(&(list->arrays[i]));
            PyList_Append(toreturn, sub_list);
            Py_DECREF(sub_list);
        }
        return toreturn;
    }
}

static PyObject*
subframe_headers_list(struct alac_subframe_header *headers, int count)
{
    PyObject *list;
    PyObject *header;
    int i;

    if ((list = PyList_New(0)) == NULL)
        return NULL;
    else {
        for (i = 0; i < count; i++) {
            header = Py_BuildValue(
                    "{si si si sN}",
                    "prediction_type",
                    headers[i].prediction_type,
                    "prediction_quantitization",
                    headers[i].prediction_quantitization,
                    "rice_modifier",
                    headers[i].rice_modifier,
                    "coefficients",
                    i_array_to_list(&(headers[i].predictor_coef_table)));
            if (header != NULL) {
                PyList_Append(list, header);
                Py_DECREF(header);
            } else {
                Py_DECREF(list);
                return NULL;
            }
        }
        return list;
    }
}

/*this is essentially a stripped-down read() method
  which performs no actual frame calculation
  but returns a tree of frame data instead*/
static PyObject*
ALACDecoder_analyze_frame(decoders_ALACDecoder* self, PyObject *args)
{
    int frame_channels;
    struct alac_frame_header frame_header;
    struct ia_array frame_samples;
    struct ia_array frame_wasted_bits;
    struct ia_array frame_residuals;
    int i;
    int channel;
    int interlacing_shift;
    int interlacing_leftweight;
    long offset;
    PyObject *frame = NULL;
    PyObject *frame_list = NULL;

    if (self->total_samples < 1)
        goto finished;

    offset = br_ftell(self->bitstream);

    if (!setjmp(*br_try(self->bitstream))) {
        frame_list = PyList_New(0);
        for (frame_channels = self->bitstream->read(self->bitstream, 3) + 1;
             frame_channels != 8;
             frame_channels = self->bitstream->read(self->bitstream, 3) + 1) {

            iaa_link(&frame_samples, &(self->samples));
            iaa_link(&frame_wasted_bits, &(self->wasted_bits_samples));
            iaa_link(&frame_residuals, &(self->residuals));
            frame_samples.size = frame_channels;
            frame_wasted_bits.size = frame_channels;
            frame_residuals.size = frame_channels;

            ALACDecoder_read_frame_header(self->bitstream,
                                          &frame_header,
                                          self->max_samples_per_frame);

            if (frame_header.is_not_compressed) {
                iaa_reset(&frame_samples);
                for (i = 0; i < frame_header.output_samples; i++) {
                    for (channel = 0; channel < frame_channels; channel++) {
                        ia_append(&(frame_samples.arrays[channel]),
                                  self->bitstream->read_signed(
                                                      self->bitstream,
                                                      self->bits_per_sample));
                    }
                }

                frame = Py_BuildValue("{si si si si si sN si}",
                                      "channels",
                                      frame_channels,
                                      "has_size",
                                      frame_header.has_size,
                                      "wasted_bits",
                                      frame_header.wasted_bits,
                                      "is_not_compressed",
                                      frame_header.is_not_compressed,
                                      "output_samples",
                                      frame_header.output_samples,
                                      "samples",
                                      ia_array_to_list(&(frame_samples)),
                                      "offset", offset);
            } else {
                interlacing_shift =
                    self->bitstream->read(self->bitstream, 8);
                interlacing_leftweight =
                    self->bitstream->read(self->bitstream, 8);

                /*read the subframe headers*/
                for (i = 0; i < frame_channels; i++) {
                    ALACDecoder_read_subframe_header(
                                              self->bitstream,
                                              &(self->subframe_headers[i]));
                }

                /*if there are wasted bits, read a block of interlaced
                  wasted-bits samples, each (wasted_bits * 8) large*/
                iaa_reset(&(self->wasted_bits_samples));
                if (frame_header.wasted_bits > 0) {
                    ALACDecoder_read_wasted_bits(self->bitstream,
                                                 &(frame_wasted_bits),
                                                 frame_header.output_samples,
                                                 frame_channels,
                                                 frame_header.wasted_bits * 8);
                }

                /*read a block of residuals for each subframe*/
                for (i = 0; i < frame_channels; i++)
                    ALACDecoder_read_residuals(self->bitstream,
                                               &(frame_residuals.arrays[i]),
                                               frame_header.output_samples,
                                               self->bits_per_sample -
                                               (frame_header.wasted_bits * 8) +
                                               frame_channels - 1,
                                               self->initial_history,
                                               self->history_multiplier,
                                               self->maximum_k);

                frame = Py_BuildValue("{si si si si si si si sN sN sN si}",
                                      "channels",
                                      frame_channels,
                                      "has_size",
                                      frame_header.has_size,
                                      "wasted_bits",
                                      frame_header.wasted_bits,
                                      "is_not_compressed",
                                      frame_header.is_not_compressed,
                                      "output_samples",
                                      frame_header.output_samples,
                                      "interlacing_shift",
                                      interlacing_shift,
                                      "interlacing_leftweight",
                                      interlacing_leftweight,
                                      "subframe_headers",
                                      subframe_headers_list(
                                                      self->subframe_headers,
                                                      frame_channels),
                                      "wasted_bits",
                                      ia_array_to_list(&(frame_wasted_bits)),
                                      "residuals",
                                      ia_array_to_list(&(frame_residuals)),
                                      "offset",
                                      offset);
            }

            self->total_samples -= (frame_header.output_samples *
                                    frame_channels);

            PyList_Append(frame_list, frame);
        }
    } else {
        Py_XDECREF(frame);
        Py_XDECREF(frame_list);
        PyErr_SetString(PyExc_IOError,
                        "EOF during frame reading");
        goto error;
    }

    br_etry(self->bitstream);

    return frame_list;
 finished:
    Py_INCREF(Py_None);
    return Py_None;
 error:
    br_etry(self->bitstream);
    return NULL;
}

static PyObject*
ALACDecoder_close(decoders_ALACDecoder* self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

status
ALACDecoder_seek_mdat(decoders_ALACDecoder *self)
{
    uint32_t atom_size;
    uint32_t atom_type;
    struct stat file_stat;
    off_t i = 0;

    /*potential race condition here if file changes out from under us*/
    if (stat(self->filename, &file_stat))
        return ERROR;

    while (i < file_stat.st_size) {
        atom_size = self->bitstream->read(self->bitstream, 32);
        atom_type = self->bitstream->read(self->bitstream, 32);
        if (atom_type == 0x6D646174)
            return OK;
        if (fseek(self->file, atom_size - 8, SEEK_CUR) == -1)
            return ERROR;
        i += atom_size;
    }

    return ERROR;
}

void
ALACDecoder_read_frame_header(BitstreamReader *bs,
                              struct alac_frame_header *frame_header,
                              int max_samples_per_frame)
{
    /* frame_header->channels = bs->read(bs, 3) + 1; */
    bs->read(bs, 16); /*nobody seems to know what these are for*/
    frame_header->has_size = bs->read(bs, 1);
    frame_header->wasted_bits = bs->read(bs, 2);
    frame_header->is_not_compressed = bs->read(bs, 1);
    if (frame_header->has_size) {
        /*for when we hit the end of the stream
          and need a non-typical amount of samples*/
        frame_header->output_samples = bs->read(bs, 32);
    } else {
        frame_header->output_samples = max_samples_per_frame;
    }
}

void
ALACDecoder_read_subframe_header(BitstreamReader *bs,
                                 struct alac_subframe_header *subframe_header)
{
    int predictor_coef_num;
    int i;

    subframe_header->prediction_type = bs->read(bs, 4);
    subframe_header->prediction_quantitization = bs->read(bs, 4);
    subframe_header->rice_modifier = bs->read(bs, 3);
    predictor_coef_num = bs->read(bs, 5);
    ia_reset(&(subframe_header->predictor_coef_table));
    for (i = 0; i < predictor_coef_num; i++) {
        ia_append(&(subframe_header->predictor_coef_table),
                  bs->read_signed(bs, 16));
    }
}

void
ALACDecoder_read_wasted_bits(BitstreamReader *bs,
                             struct ia_array *wasted_bits_samples,
                             int sample_count,
                             int channels,
                             int wasted_bits_size)
{
    int i;
    int channel;

    for (i = 0; i < sample_count; i++) {
        for (channel = 0; channel < channels; channel++) {
            ia_append(iaa_getitem(wasted_bits_samples, channel),
                      bs->read(bs, wasted_bits_size));
        }
    }
}

/*this is the slow version*/
/*
  static inline int LOG2(int value) {
  double newvalue = trunc(log((double)value) / log((double)2));

  return (int)(newvalue);
  }
*/

/*the fast version used by ffmpeg and the "alac" decoder
  subtracts MSB zero bits from total bit size - 1,
  essentially counting the number of LSB non-zero bits, -1*/

/*my version just counts the number of non-zero bits and subtracts 1
  which is good enough for now*/
static inline int
LOG2(int value)
{
    int bits = -1;
    while (value) {
        bits++;
        value >>= 1;
    }
    return bits;
}

void
ALACDecoder_read_residuals(BitstreamReader *bs,
                           struct i_array *residuals,
                           int residual_count,
                           int sample_size,
                           int initial_history,
                           int history_multiplier,
                           int maximum_k)
{
    int history = initial_history;
    int sign_modifier = 0;
    int decoded_value;
    int residual;
    int block_size;
    int i, j;
    int k;

    ia_reset(residuals);

    for (i = 0; i < residual_count; i++) {
        /*figure out "k" based on the value of "history"*/
        k = MIN(LOG2((history >> 9) + 3), maximum_k);

        /*get an unsigned decoded_value based on "k"
          and on "sample_size" as a last resort*/
        decoded_value = ALACDecoder_read_residual(bs, k, sample_size) +
            sign_modifier;

        /*change decoded_value into a signed residual
          and append it to "residuals"*/
        residual = (decoded_value + 1) >> 1;
        if (decoded_value & 1)
            residual *= -1;

        ia_append(residuals, residual);

        /*then use our old unsigned decoded_value to update "history"
          and reset "sign_modifier"*/
        sign_modifier = 0;

        if (decoded_value > 0xFFFF)
            history = 0xFFFF;
        else
            history += ((decoded_value * history_multiplier) -
                        ((history * history_multiplier) >> 9));

        /*if history gets too small, we may have a block of 0 samples
          which can be compressed more efficiently*/
        if ((history < 128) && ((i + 1) < residual_count)) {
            k = MIN(7 - LOG2(history) + ((history + 16) / 64), maximum_k);
            block_size = ALACDecoder_read_residual(bs, k, 16);
            if (block_size > 0) {
                /*block of 0s found, so write them out*/
                for (j = 0; j < block_size; j++) {
                    ia_append(residuals, 0);
                    i++;
                }
            }
            if (block_size <= 0xFFFF) {
                sign_modifier = 1;
            }

            history = 0;
        }
    }
}

#define RICE_THRESHOLD 8

int
ALACDecoder_read_residual(BitstreamReader *bs,
                          int k,
                          int sample_size)
{
    int x = 0;  /*our final value*/
    int extrabits;

    /*read a unary 0 value to a maximum of RICE_THRESHOLD (8)*/
    x = bs->read_limited_unary(bs, 0, RICE_THRESHOLD + 1);

    if (x == -1) {
        x = bs->read(bs, sample_size);
    } else {
        if (k > 1) {
            /*x = x * ((2 ** k) - 1)*/
            x *= ((1 << k) - 1);

            extrabits = bs->read(bs, k);
            if (extrabits > 1)
                x += (extrabits - 1);
            else {
                if (extrabits == 1) {
                    bs->unread(bs, 1);
                } else {
                    bs->unread(bs, 0);
                }
            }
        }
    }

    return x;
}

static inline int
SIGN_ONLY(int value)
{
    if (value > 0)
        return 1;
    else if (value < 0)
        return -1;
    else
        return 0;
}

void
ALACDecoder_decode_subframe(struct i_array *samples,
                            struct i_array *residuals,
                            struct i_array *coefficients,
                            int predictor_quantitization)
{
    ia_data_t buffer0;
    ia_data_t residual;
    int64_t lpc_sum;
    int32_t output_value;
    int32_t val;
    int sign;
    int original_sign;
    int i = 0;
    int j;

    ia_reset(samples);

    /*first sample always copied verbatim*/
    ia_append(samples, residuals->data[i++]);

    /*grab a number of warm-up samples equal to coefficients' length*/
    for (j = 0; j < coefficients->size; j++) {
        /*these are adjustments to the previous sample
          rather than copied verbatim*/
        ia_append(samples, residuals->data[i] + samples->data[i - 1]);
        i++;
    }

    /*then calculate a new sample per remaining residual*/
    for (;i < residuals->size; i++) {
        residual = residuals->data[i];
        lpc_sum = 1 << (predictor_quantitization - 1);

        /*Note that buffer0 gets stripped from previously encoded samples
          then re-added prior to adding the next sample.
          It's a watermark sample, of sorts.*/
        buffer0 = samples->data[i - (coefficients->size + 1)];

        for (j = 0; j < coefficients->size; j++) {
            lpc_sum += ((int64_t)coefficients->data[j] *
                        (int64_t)(samples->data[i - j - 1] - buffer0));
        }

        /*sample = ((sum + 2 ^ (quant - 1)) / (2 ^ quant)) + residual + buffer0*/
        lpc_sum >>= predictor_quantitization;
        lpc_sum += buffer0;
        output_value = (int32_t)(residual + lpc_sum);
        ia_append(samples, output_value);

        /*At this point, except for buffer0, everything looks a lot like
          a FLAC LPC subframe.
          We're not done yet, though.
          ALAC's adaptive algorithm then adjusts the coefficients
          up or down 1 step based on previously decoded samples
          and the residual*/
        if (residual) {
            original_sign = SIGN_ONLY(residual);

            for (j = 0; j < coefficients->size; j++) {
                val = buffer0 - samples->data[i - coefficients->size + j];
                if (original_sign >= 0)
                    sign = SIGN_ONLY(val);
                else
                    sign = -SIGN_ONLY(val);
                coefficients->data[coefficients->size - j - 1] -= sign;
                residual -= (((val * sign) >> predictor_quantitization) *
                             (j + 1));
                if (SIGN_ONLY(residual) != original_sign)
                    break;
            }
        }
    }
}

void
ALACDecoder_decorrelate_channels(struct ia_array *output,
                                 struct ia_array *input,
                                 int interlacing_shift,
                                 int interlacing_leftweight)
{
    struct i_array *left_channel;
    struct i_array *right_channel;
    struct i_array *channel1;
    struct i_array *channel2;
    ia_size_t pcm_frames, i;
    ia_data_t right_i;

    if (input->size != 2) {
        for (i = 0; i < input->size; i++) {
            ia_copy(iaa_getitem(output, i), iaa_getitem(input, i));
        }
    } else {
        channel1 = iaa_getitem(input, 0);
        channel2 = iaa_getitem(input, 1);
        left_channel = iaa_getitem(output, 0);
        right_channel = iaa_getitem(output, 1);
        ia_reset(left_channel);
        ia_reset(right_channel);
        pcm_frames = channel1->size;

        if (interlacing_leftweight == 0) {
            ia_copy(left_channel, channel1);
            ia_copy(right_channel, channel2);
        } else {
            for (i = 0; i < pcm_frames; i++) {
                ia_append(right_channel,
                          (right_i = (channel1->data[i] -
                                      ((channel2->data[i] *
                                        interlacing_leftweight) >>
                                       interlacing_shift))));
                ia_append(left_channel, channel2->data[i] + right_i);
            }
        }
    }
}

void
ALACDecoder_print_frame_header(FILE *output,
                               struct alac_frame_header *frame_header)
{
    fprintf(output, "has_size : %d\n",
            frame_header->has_size);
    fprintf(output, "wasted bits : %d\n",
            frame_header->wasted_bits);
    fprintf(output, "is_not_compressed : %d\n",
            frame_header->is_not_compressed);
    fprintf(output, "output_samples : %d\n",
            frame_header->output_samples);
}

void
ALACDecoder_print_subframe_header(FILE *output,
                                  struct alac_subframe_header *subframe_header)
{
    fprintf(output, "prediction type : %d\n",
            subframe_header->prediction_type);
    fprintf(output, "prediction quantitization : %d\n",
            subframe_header->prediction_quantitization);
    fprintf(output, "rice modifier : %d\n",
            subframe_header->rice_modifier);
    fprintf(output, "predictor coefficients : ");
    ia_print(stdout,
             &(subframe_header->predictor_coef_table));
    fprintf(output, "\n");
}

#include "pcm.c"
