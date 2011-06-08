#include "shn.h"
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
SHNDecoder_init(decoders_SHNDecoder *self,
                PyObject *args, PyObject *kwds)
{
    char* filename;
    FILE* fp;
    int i, j;

    self->filename = NULL;
    self->bitshift = 0;
    self->verbatim = NULL;
    self->bits_per_sample = 0;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    self->filename = strdup(filename);

    /*open the shn file*/
    if ((fp = fopen(filename, "rb")) == NULL) {
        self->bitstream = NULL;
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = br_open(fp, BS_BIG_ENDIAN);
    }

    self->bitstream->mark(self->bitstream);

    if (SHNDecoder_read_header(self) == ERROR) {
        PyErr_SetString(PyExc_ValueError, "not a SHN file");
        return -1;
    }

    switch (self->file_type) {
    case 1:
    case 2:
        self->bits_per_sample = 8;
        break;
    case 3:
    case 4:
    case 5:
    case 6:
        self->bits_per_sample = 16;
        break;
        /*not sure if file types 11/12 for wav and aiff are used*/
    default:
        PyErr_SetString(PyExc_ValueError, "unsupported SHN file type");
        return -1;
    }

    iaa_init(&(self->buffer), self->channels, self->block_size + self->wrap);
    iaa_init(&(self->offset), self->channels, 1);
    ia_init(&(self->lpc_coeffs), 1);
    for (i = 0; i < self->channels; i++) {
        for (j = 0; j < self->wrap; j++) {
            ia_append(iaa_getitem(&(self->buffer), i), 0);
        }
        for (j = 0; j < self->nmean; j++) {
            ia_append(iaa_getitem(&(self->offset), i), 0);
        }
    }

    /*These are set to sensible defaults at init-time.

      But due to the grubby nature of Shorten,
      the decoder is expected to make one pass through the file
      parse any wav/aiff headers found (there should be one)
      and use that data to set these two fields
      so that this works like a proper PCMReader.

      Shorten simply wasn't designed for any sort of non-batch
      file compression/decompression whatsoever.*/
    self->sample_rate = 44100;
    self->channel_mask = 0x3;

    return 0;
}

PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

void
SHNDecoder_dealloc(decoders_SHNDecoder *self)
{
    if (self->filename != NULL)
        free(self->filename);

    if (self->bits_per_sample != 0) {
        iaa_free(&(self->buffer));
        iaa_free(&(self->offset));
        ia_free(&(self->lpc_coeffs));
    }
    if (self->verbatim != NULL)
        free(self->verbatim);

    if (self->bitstream != NULL) {
        self->bitstream->unmark(self->bitstream);
        self->bitstream->close(self->bitstream);
    }

    self->ob_type->tp_free((PyObject*)self);
}


PyObject*
SHNDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds)
{
    decoders_SHNDecoder *self;

    self = (decoders_SHNDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

static PyObject*
SHNDecoder_version(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->version);
}

static PyObject*
SHNDecoder_file_type(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->file_type);
}

static PyObject*
SHNDecoder_channels(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->channels);
}

static PyObject*
SHNDecoder_bits_per_sample(decoders_SHNDecoder *self,
                           void *closure)
{
    return Py_BuildValue("i", self->bits_per_sample);
}

static int
SHNDecoder_set_sample_rate(decoders_SHNDecoder *self,
                           PyObject *value,
                           void *closure)
{
    long long_value;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "cannot delete the sample_rate attribute");
        return -1;
    }

    if (((long_value = PyInt_AsLong(value)) == -1) && PyErr_Occurred())
        return -1;

    self->sample_rate = long_value;

    return 0;
}

static PyObject*
SHNDecoder_sample_rate(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
SHNDecoder_channel_mask(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->channel_mask);
}

static int
SHNDecoder_set_channel_mask(decoders_SHNDecoder *self,
                            PyObject *value,
                            void *closure)
{
    long long_value;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "cannot delete the channel_mask attribute");
        return -1;
    }

    if (((long_value = PyInt_AsLong(value)) == -1) && PyErr_Occurred())
        return -1;

    self->channel_mask = long_value;

    return 0;
}

static PyObject*
SHNDecoder_block_size(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->block_size);
}


PyObject*
SHNDecoder_read(decoders_SHNDecoder* self, PyObject *args)
{
    int channel = 0;
    int i;
    unsigned int cmd;
    unsigned int verbatim_length;

    PyObject *framelist;
    struct i_array* channel_data;
    struct i_array* offset_data;
    ia_data_t sum;

    int coffset;
    PyThreadState *thread_state;

    if (self->read_finished) {
        iaa_reset(&(self->buffer));
        goto finished;
    }

    if (!self->read_started) {
        self->bitstream->rewind(self->bitstream);

        if (SHNDecoder_read_header(self) == ERROR)
            return NULL;
    }

    thread_state = PyEval_SaveThread();
    if (!setjmp(*br_try(self->bitstream))) {
        /*read the next instructions to fill all buffers,
          until FN_QUIT reached*/
        while (channel < self->channels) {
            cmd = shn_read_uvar(self->bitstream, 2);

            switch (cmd) {
            case FN_DIFF0:
            case FN_DIFF1:
            case FN_DIFF2:
            case FN_DIFF3:
            case FN_ZERO:
            case FN_QLPC:
                /*calculate current coffset as adjusted average of offsets*/
                channel_data = iaa_getitem(&(self->buffer), channel);
                offset_data = iaa_getitem(&(self->offset), channel);

                if (self->nmean > 0)
                    coffset = ((((ia_data_t)self->nmean / 2) + ia_sum(offset_data))
                               / (ia_data_t)self->nmean) >> MIN(1, self->bitshift);
                else
                    coffset = 0;

                switch (cmd) {  /*audio commands handled here*/
                case FN_DIFF0:
                    SHNDecoder_read_diff(channel_data,
                                         self->bitstream,
                                         self->block_size,
                                         SHNDecoder_diff0);

                    /*DIFF0, and only DIFF0, also applies coffset*/
                    for (i = 0; i < channel_data->size; i++) {
                        ia_setitem(channel_data, i,
                                   ia_getitem(channel_data, i) + coffset);
                    }
                    break;
                case FN_DIFF1:
                    SHNDecoder_read_diff(channel_data,
                                         self->bitstream,
                                         self->block_size,
                                         SHNDecoder_diff1);
                    break;
                case FN_DIFF2:
                    SHNDecoder_read_diff(channel_data,
                                         self->bitstream,
                                         self->block_size,
                                         SHNDecoder_diff2);
                    break;
                case FN_DIFF3:
                    SHNDecoder_read_diff(channel_data,
                                         self->bitstream,
                                         self->block_size,
                                         SHNDecoder_diff3);
                    break;
                case FN_ZERO:
                    SHNDecoder_read_zero(channel_data,
                                         self->block_size);
                    break;
                case FN_QLPC:
                    SHNDecoder_read_lpc(self, channel_data, coffset);
                    break;
                }

                /*add new value to offset queue*/
                if (self->nmean > 0) {
                    /*calculate a fresh sum of samples*/
                    sum = (ia_data_t)self->block_size / 2;
                    for (i = 0; i < self->block_size; i++) {
                        sum += ia_getitem(channel_data, i + self->wrap);
                    }

                    /*shift the old offsets down a notch*/
                    for (i = 1; i < self->nmean; i++)
                        ia_setitem(offset_data, i - 1, ia_getitem(offset_data, i));

                    /*and append our new sum*/
                    ia_setitem(offset_data, self->nmean - 1,
                               (sum / (ia_data_t)self->block_size) <<
                               self->bitshift);
                }

                /*perform sample wrapping from the end of channel_data
                  to the beginning*/
                for (i = -self->wrap; i < 0; i++) {
                    ia_setitem(channel_data, self->wrap + i,
                               ia_getitem(channel_data, i));
                }

                /*if bitshift is set, shift all samples in the framelist
                  to the left
                  (analagous to FLAC's wasted-bits-per-sample)*/
                if (self->bitshift > 0) {
                    for (i = self->wrap; i < channel_data->size; i++) {
                        ia_setitem(channel_data, i,
                                   ia_getitem(channel_data, i) << self->bitshift);
                    }
                }

                channel++;
                break;
            case FN_VERBATIM:
                /*skip VERBATIM chunks*/
                verbatim_length = shn_read_uvar(self->bitstream,
                                                VERBATIM_CHUNK_SIZE);
                for (i = 0; i < verbatim_length; i++) {
                    shn_read_uvar(self->bitstream, VERBATIM_BYTE_SIZE);
                }
                break;
            case FN_BLOCKSIZE:
                self->block_size = shn_read_long(self->bitstream);
                break;
            case FN_BITSHIFT:
                self->bitshift = shn_read_uvar(self->bitstream, 2);
                break;
            case FN_QUIT:
                PyEval_RestoreThread(thread_state);
                self->read_finished = 1;
                br_etry(self->bitstream);
                iaa_reset(&(self->buffer));
                goto finished;
            default:
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(PyExc_ValueError,
                                "unknown command encountered"
                                "in Shorten stream");
                goto error;
            }
        }
    } else {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "EOF reading Shorten stream");
        goto error;
    }

    br_etry(self->bitstream);
    PyEval_RestoreThread(thread_state);

    /*once self->buffer is full of PCM data on each channel,
      convert the integer values to a pcm.FrameList object*/
    framelist = ia_array_slice_to_framelist(&(self->buffer),
                                            self->bits_per_sample,
                                            self->wrap,
                                            self->block_size + self->wrap);

    /*reset channels for next run*/
    for (channel = 0; channel < self->channels; channel++) {
        iaa_getitem(&(self->buffer), channel)->size = self->wrap;
    }

    /*then return the pcm.FrameList*/
    return framelist;

 finished:
    return ia_array_to_framelist(&(self->buffer),
                                 self->bits_per_sample);
 error:
    br_etry(self->bitstream);
    return NULL;
}

static PyObject*
SHNDecoder_metadata(decoders_SHNDecoder* self, PyObject *args)
{
    unsigned int cmd;

    unsigned int verbatim_length;
    unsigned int lpc_count;

    int i;
    unsigned int residual_size;
    PyObject* list = NULL;

    int previous_is_none = 0;

    int total_samples = 0;

    if ((list = PyList_New(0)) == NULL)
        return NULL;

    /*rewind the stream and re-read the header*/
    self->bitstream->rewind(self->bitstream);

    if (SHNDecoder_read_header(self) == ERROR) {
        PyErr_SetString(PyExc_ValueError,
                        "error reading SHN header");
        Py_XDECREF(list);
        return NULL;
    }

    /*walk through the Shorten file,
      storing FN_VERBATIM instructions as strings,
      storing blocks of non-FM_VERBATIM instructions as None,
      and counting the length of all audio data commands*/

    if (!setjmp(*br_try(self->bitstream))) {
        for (cmd = shn_read_uvar(self->bitstream, 2);
             cmd != FN_QUIT;
             cmd = shn_read_uvar(self->bitstream, 2)) {
            switch (cmd) {
            case FN_VERBATIM:
                verbatim_length = shn_read_uvar(self->bitstream,
                                                VERBATIM_CHUNK_SIZE);
                self->verbatim = realloc(self->verbatim, verbatim_length);
                for (i = 0; i < verbatim_length; i++) {
                    self->verbatim[i] = (shn_read_uvar(
                                self->bitstream,
                                VERBATIM_BYTE_SIZE) & 0xFF);
                }
                if (PyList_Append(
                        list,
                        PyString_FromStringAndSize((char *)self->verbatim,
                                                   verbatim_length)) == -1) {
                    goto error;
                } else {
                    previous_is_none = 0;
                }
                break;
            case FN_DIFF0:
            case FN_DIFF1:
            case FN_DIFF2:
            case FN_DIFF3:
                total_samples += self->block_size;
                residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
                for (i = 0; i < self->block_size; i++) {
                    shn_skip_var(self->bitstream, residual_size);
                }
                if (!previous_is_none) {
                    Py_INCREF(Py_None);
                    if (PyList_Append(list, Py_None) == -1) {
                        goto error;
                    }
                }
                previous_is_none = 1;
                break;
            case FN_ZERO:
                total_samples += self->block_size;
                if (!previous_is_none) {
                    Py_INCREF(Py_None);
                    if (PyList_Append(list, Py_None) == -1) {
                        goto error;
                    }
                }
                previous_is_none = 1;
                break;
            case FN_QLPC:
                total_samples += self->block_size;
                residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
                lpc_count = shn_read_uvar(self->bitstream, QLPC_SIZE);
                for (i = 0; i < lpc_count; i++) {
                    shn_skip_var(self->bitstream, QLPC_QUANT);
                }
                for (i = 0; i < self->block_size; i++) {
                    shn_skip_var(self->bitstream, residual_size);
                }
                if (!previous_is_none) {
                    Py_INCREF(Py_None);
                    if (PyList_Append(list, Py_None) == -1) {
                        goto error;
                    }
                }
                previous_is_none = 1;
                break;
            case FN_BITSHIFT:
                shn_skip_uvar(self->bitstream, 2);
                break;
            case FN_BLOCKSIZE:
                self->block_size = shn_read_long(self->bitstream);
                break;
            default:
                PyErr_SetString(PyExc_ValueError,
                        "unknown command encountered in Shorten stream");
                goto error;
            }
        }
    } else {
        PyErr_SetString(PyExc_IOError, "EOF while reading Shorten stream");
        goto error;
    }

    self->read_started = 0;

    br_etry(self->bitstream);
    return Py_BuildValue("(i,O)", total_samples / self->channels, list);

 error:
    br_etry(self->bitstream);
    Py_XDECREF(list);
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

PyObject*
SHNDecoder_analyze_frame(decoders_SHNDecoder* self, PyObject *args)
{
    unsigned int cmd;
    PyObject *toreturn = NULL;
    unsigned int residual_size;
    unsigned int verbatim_length;
    unsigned int lpc_count;
    struct i_array *buffer = &(self->buffer.arrays[0]);
    struct i_array coefficients = self->lpc_coeffs;
    int byte_offset;
    int i;

    if (!self->read_started) {
        self->bitstream->rewind(self->bitstream);

        if (SHNDecoder_read_header(self) == ERROR) {
            PyErr_SetString(PyExc_ValueError, "error reading SHN header");
            return NULL;
        }
    }

    if (self->read_finished) {
        goto stream_finished;
    }

    byte_offset = br_ftell(self->bitstream);

    if (!setjmp(*br_try(self->bitstream))) {
        switch (cmd = shn_read_uvar(self->bitstream, 2)) {
        case FN_DIFF0:
        case FN_DIFF1:
        case FN_DIFF2:
        case FN_DIFF3:
            residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
            ia_reset(buffer);
            for (i = 0; i < self->block_size; i++) {
                ia_append(buffer, shn_read_var(self->bitstream, residual_size));
            }
            toreturn = Py_BuildValue("{sI si sI sN}",
                                     "command", cmd,
                                     "offset", byte_offset,
                                     "residual_size", residual_size,
                                     "residual", i_array_to_list(buffer));
            break;
        case FN_QUIT:
            self->read_finished = 1;
            toreturn = Py_BuildValue("{sI si}",
                                     "command", cmd,
                                     "offset", byte_offset);
            break;
        case FN_BLOCKSIZE:
            self->block_size = shn_read_long(self->bitstream);
            toreturn = Py_BuildValue("{sI si sI}",
                                     "command", cmd,
                                     "offset", byte_offset,
                                     "block_size", self->block_size);
            break;
        case FN_BITSHIFT:
            self->bitshift = shn_read_uvar(self->bitstream, 2);
            toreturn = Py_BuildValue("{sI si sI}",
                                     "command", cmd,
                                     "offset", byte_offset,
                                     "bit_shift", self->bitshift);
            break;
        case FN_QLPC:
            residual_size = shn_read_uvar(self->bitstream, ENERGY_SIZE);
            lpc_count = shn_read_uvar(self->bitstream, QLPC_SIZE);
            ia_reset(&coefficients);
            for (i = 0; i < lpc_count; i++) {
                ia_append(&coefficients,
                          shn_read_var(self->bitstream, QLPC_QUANT));
            }
            ia_reset(buffer);
            for (i = 0; i < self->block_size; i++) {
                ia_append(buffer, shn_read_var(self->bitstream,
                                                residual_size));
            }
            toreturn = Py_BuildValue("{sI si sN sI sN}",
                                     "command", cmd,
                                     "offset", byte_offset,
                                     "coefficients",
                                     i_array_to_list(&coefficients),
                                     "residual_size", residual_size,
                                     "residual", i_array_to_list(buffer));
            break;
        case FN_ZERO:
            toreturn = Py_BuildValue("{sI si}",
                                     "command", cmd,
                                     "offset", byte_offset);
            break;
        case FN_VERBATIM:
            verbatim_length = shn_read_uvar(self->bitstream,
                                            VERBATIM_CHUNK_SIZE);
            ia_reset(buffer);
            for (i = 0; i < verbatim_length; i++) {
                ia_append(buffer, shn_read_uvar(self->bitstream,
                                                 VERBATIM_BYTE_SIZE));
            }
            toreturn = Py_BuildValue("{sI si sN}",
                                     "command", cmd,
                                     "offset", byte_offset,
                                     "data", i_array_to_list(buffer));
            break;
        default:
            PyErr_SetString(PyExc_ValueError,
                            "unknown command encountered in Shorten stream");
            goto error;
        }
    } else {
        PyErr_SetString(PyExc_IOError, "EOF while reading Shorten stream");
        goto error;
    }

    br_etry(self->bitstream);
    return toreturn;

 error:
    br_etry(self->bitstream);
    return NULL;

 stream_finished:
    Py_INCREF(Py_None);
    return Py_None;
}

status
SHNDecoder_read_header(decoders_SHNDecoder* self)
{
    BitstreamReader* bs = self->bitstream;

    if (!setjmp(*br_try(bs))) {
        if (bs->read(bs, 32) != 0x616A6B67) {
            br_etry(bs);
            return ERROR;
        }

        self->version = bs->read(bs, 8);
        self->file_type = shn_read_long(bs);
        self->channels = shn_read_long(bs);
        self->block_size = shn_read_long(bs);
        self->maxnlpc = shn_read_long(bs);
        self->nmean = shn_read_long(bs);
        self->nskip = shn_read_long(bs);
        /*FIXME - perform writing if bytes skipped*/
        self->wrap = self->maxnlpc > 3 ? self->maxnlpc : 3;

        self->read_started = 1;
        self->read_finished = 0;

        br_etry(bs);
        return OK;
    } else {
        br_etry(bs);
        return ERROR;
    }
}

void
SHNDecoder_read_diff(struct i_array *buffer,
                     BitstreamReader* bs,
                     unsigned int block_size,
                     int (*calculation)(int residual,
                                        struct i_array *buffer))
{
    unsigned int i;
    unsigned int residual_size = shn_read_uvar(bs, ENERGY_SIZE);

    for (i = 0; i < block_size; i++) {
        ia_append(buffer, calculation(shn_read_var(bs, residual_size),
                                      buffer));
    }
}

int
SHNDecoder_diff0(int residual, struct i_array *buffer)
{
    return residual;
}

int
SHNDecoder_diff1(int residual, struct i_array *buffer)
{
    return residual + ia_getitem(buffer, -1);
}

int
SHNDecoder_diff2(int residual, struct i_array *buffer)
{
    return residual + ((2 * ia_getitem(buffer, -1)) - ia_getitem(buffer, -2));
}

int
SHNDecoder_diff3(int residual, struct i_array *buffer)
{
    return residual + (3 * (ia_getitem(buffer, -1) -
                            ia_getitem(buffer, -2))) + ia_getitem(buffer, -3);
}

void
SHNDecoder_read_zero(struct i_array *buffer,
                     unsigned int block_size)
{
    int i;

    for (i = 0; i < block_size; i++) {
        ia_append(buffer, 0);
    }
}

void
SHNDecoder_read_lpc(decoders_SHNDecoder *decoder,
                    struct i_array *buffer,
                    int coffset)
{
    BitstreamReader *bs = decoder->bitstream;
    unsigned int residual_size = shn_read_uvar(bs, ENERGY_SIZE);
    unsigned int i, j;
    unsigned int lpc_count;
    struct i_array *lpc_coeffs = &(decoder->lpc_coeffs);
    struct i_array tail;
    int32_t sum;

    lpc_count = shn_read_uvar(bs, QLPC_SIZE);
    ia_reset(lpc_coeffs);
    for (i = 0; i < lpc_count; i++) {
        ia_append(lpc_coeffs, shn_read_var(bs, QLPC_QUANT));
    }
    ia_reverse(lpc_coeffs);

    if (coffset != 0) {
        for (i = 0; i < decoder->wrap; i++)
            ia_setitem(buffer, i, ia_getitem(buffer, i) - coffset);
    }

    for (i = 0; i < decoder->block_size; i++) {
        sum = QLPC_OFFSET;
        ia_tail(&tail, buffer, lpc_count);
        for (j = 0; j < lpc_count; j++) {
            sum += (int32_t)ia_getitem(&tail, j) *
                (int32_t)ia_getitem(lpc_coeffs, j);
        }
        ia_append(buffer,
                  shn_read_var(bs, residual_size) + (sum >> QLPC_QUANT));
    }

    if (coffset != 0)
        for (i = 0; i < buffer->size; i++)
            ia_setitem(buffer, i, ia_getitem(buffer, i) + coffset);
}

unsigned int
shn_read_uvar(BitstreamReader* bs, unsigned int count)
{
    unsigned int high_bits = bs->read_unary(bs, 1);
    unsigned int low_bits = bs->read(bs, count);

    return (high_bits << count) | low_bits;
}

int
shn_read_var(BitstreamReader* bs, unsigned int count)
{
    unsigned int uvar = shn_read_uvar(bs, count + 1); /*1 additional sign bit*/
    if (uvar & 1)
        return ~(uvar >> 1);
    else
        return uvar >> 1;
}

unsigned int
shn_read_long(BitstreamReader* bs)
{
    return shn_read_uvar(bs, shn_read_uvar(bs, 2));
}

void
shn_skip_uvar(BitstreamReader* bs, unsigned int count)
{
    bs->read_unary(bs, 1);
    bs->read(bs, count);
}

void
shn_skip_var(BitstreamReader* bs, unsigned int count)
{
    bs->read_unary(bs, 1);
    bs->read(bs, count + 1);
}

char*
SHNDecoder_cmd_string(int cmd)
{
    switch (cmd) {
    case FN_DIFF0:
        return "DIFF0";
    case FN_DIFF1:
        return "DIFF1";
    case FN_DIFF2:
        return "DIFF2";
    case FN_DIFF3:
        return "DIFF3";
    case FN_QUIT:
        return "QUIT";
    case FN_BLOCKSIZE:
        return "BLOCKSIZE";
    case FN_QLPC:
        return "QLPC";
    case FN_ZERO:
        return "ZERO";
    case FN_VERBATIM:
        return "VERBATIM";
    default:
        return "UNKNOWN";
    }
}

#include "pcm.c"
