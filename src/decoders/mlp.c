#include "mlp.h"
#include "../pcm.h"
#include "pcm.h"

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

int
MLPDecoder_init(decoders_MLPDecoder *self,
                PyObject *args, PyObject *kwds) {
    char *filename;
    fpos_t pos;
    int substream;
    int matrix;
    int channel;

    self->substream_sizes = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return -1;

    /*open the MLP file*/
    self->file = fopen(filename, "rb");
    if (self->file == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = bs_open(self->file, BS_BIG_ENDIAN);
    }

    /*store initial position in stream*/
    if (fgetpos(self->bitstream->file, &pos) == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    }

    /*skip initial frame size, if possible*/
    if (mlp_total_frame_size(self->bitstream) == -1) {
        PyErr_SetString(PyExc_IOError, "unable to read initial major sync");
        return -1;
    }

    /*attempt to read initial major sync*/
    switch (mlp_read_major_sync(self, &(self->major_sync))) {
    case MLP_MAJOR_SYNC_OK:
        break;
    case MLP_MAJOR_SYNC_NOT_FOUND:
        PyErr_SetString(PyExc_ValueError, "invalid initial major sync");
        return -1;
    case MLP_MAJOR_SYNC_ERROR:
        PyErr_SetString(PyExc_IOError, "unable to read initial major sync");
        return -1;
    }
    if (self->major_sync.substream_count > 2) {
        PyErr_SetString(PyExc_ValueError,
                        "substream count cannot be greater than 2");
        return -1;
    }

    /*restore initial stream position*/
    if (fsetpos(self->bitstream->file, &pos) == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    }

    /*allocate space for decoding variables*/
    self->substream_sizes = malloc(sizeof(struct mlp_SubstreamSize) *
                                   self->major_sync.substream_count);

    self->restart_headers = malloc(sizeof(struct mlp_RestartHeader) *
                                   self->major_sync.substream_count);

    self->decoding_parameters = malloc(sizeof(struct mlp_DecodingParameters) *
                                       self->major_sync.substream_count);

    iaa_init(&(self->unfiltered_residuals), MAX_MLP_CHANNELS, 8);
    iaa_init(&(self->filtered_residuals), MAX_MLP_CHANNELS, 8);

    self->substream_samples = malloc(sizeof(struct ia_array) *
                                     self->major_sync.substream_count);

    iaa_init(&(self->frame_samples), MAX_MLP_CHANNELS, 8);

    for (substream = 0;
         substream < self->major_sync.substream_count;
         substream++) {
        for (channel = 0; channel < MAX_MLP_CHANNELS; channel++) {
            ia_init(&(self->decoding_parameters[substream].channel_parameters[channel].fir_filter_parameters.coefficients), 2);
            ia_init(&(self->decoding_parameters[substream].channel_parameters[channel].fir_filter_parameters.state), 2);
            ia_init(&(self->decoding_parameters[substream].channel_parameters[channel].iir_filter_parameters.coefficients), 2);
            ia_init(&(self->decoding_parameters[substream].channel_parameters[channel].iir_filter_parameters.state), 2);
        }
        iaa_init(&(self->substream_samples[substream]), MAX_MLP_CHANNELS, 8);

        for (matrix = 0; matrix < MAX_MLP_MATRICES; matrix++) {
            ia_init(&(self->decoding_parameters[substream].matrix_parameters.matrices[matrix].bypassed_lsbs), 8);
        }
    }



    /*initalize stream position callback*/
    self->bytes_read = 0;
    bs_add_callback(self->bitstream, mlp_byte_counter, &(self->bytes_read));

    return 0;
}

void mlp_byte_counter(int value, void* ptr) {
    uint64_t *bytes_read = ptr;
    *bytes_read += 1;
}

void
MLPDecoder_dealloc(decoders_MLPDecoder *self)
{
    int substream;
    int matrix;
    int channel;

    if (self->substream_sizes != NULL) {
        for (substream = 0;
             substream < self->major_sync.substream_count;
             substream++) {
            for (channel = 0; channel < MAX_MLP_CHANNELS; channel++) {
                ia_free(&(self->decoding_parameters[substream].channel_parameters[channel].fir_filter_parameters.coefficients));
                ia_free(&(self->decoding_parameters[substream].channel_parameters[channel].fir_filter_parameters.state));
                ia_free(&(self->decoding_parameters[substream].channel_parameters[channel].iir_filter_parameters.coefficients));
                ia_free(&(self->decoding_parameters[substream].channel_parameters[channel].iir_filter_parameters.state));
            }
            iaa_free(&(self->substream_samples[substream]));

            for (matrix = 0; matrix < MAX_MLP_MATRICES; matrix++) {
                ia_free(&(self->decoding_parameters[substream].matrix_parameters.matrices[matrix].bypassed_lsbs));
            }
        }

        iaa_free(&(self->unfiltered_residuals));
        iaa_free(&(self->filtered_residuals));
        iaa_free(&(self->frame_samples));

        free(self->substream_samples);
        free(self->substream_sizes);
        free(self->restart_headers);
        free(self->decoding_parameters);
    }

    if (self->file != NULL)
        bs_close(self->bitstream);

    self->ob_type->tp_free((PyObject*)self);
}

PyObject*
MLPDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_MLPDecoder *self;

    self = (decoders_MLPDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int mlp_sample_rate(struct mlp_MajorSync* major_sync) {
    switch (major_sync->group1_sample_rate) {
    case 0x0:
        return 48000;
    case 0x1:
        return 96000;
    case 0x2:
        return 192000;
    case 0x3:
        return 394000;
    case 0x4:
        return 768000;
    case 0x5:
        return 1536000;
    case 0x6:
        return 3072000;
    case 0x8:
        return 44100;
    case 0x9:
        return 88200;
    case 0xA:
        return 176400;
    case 0xB:
        return 352800;
    case 0xC:
        return 705600;
    case 0xD:
        return 1411200;
    case 0xE:
        return 2822400;
    default:
        return -1;
    }
}

static PyObject*
MLPDecoder_sample_rate(decoders_MLPDecoder *self, void *closure) {
    int rate = mlp_sample_rate(&(self->major_sync));
    if (rate > 0) {
        return Py_BuildValue("i", rate);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported sample rate");
        return NULL;
    }

}

int mlp_bits_per_sample(struct mlp_MajorSync* major_sync) {
    switch (major_sync->group1_bits) {
    case 0:
        return 16;
    case 1:
        return 20;
    case 2:
        return 24;
    default:
        return -1;
    }
}

static PyObject*
MLPDecoder_bits_per_sample(decoders_MLPDecoder *self, void *closure) {
    int bits_per_sample = mlp_bits_per_sample(&(self->major_sync));
    if (bits_per_sample > 0) {
        return Py_BuildValue("i", bits_per_sample);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported bits-per-sample");
        return NULL;
    }
}

int mlp_channel_count(struct mlp_MajorSync* major_sync) {
    switch (major_sync->channel_assignment) {
    case 0x0:
        return 1;
    case 0x1:
        return 2;
    case 0x2:
    case 0x4:
    case 0x7:
        return 3;
    case 0x3:
    case 0x5:
    case 0x8:
    case 0xA:
    case 0xD:
    case 0xF:
        return 4;
    case 0x6:
    case 0x9:
    case 0xB:
    case 0xE:
    case 0x10:
    case 0x12:
    case 0x13:
        return 5;
    case 0xC:
    case 0x11:
    case 0x14:
        return 6;
    default:
        return -1;
    }
}

static PyObject*
MLPDecoder_channels(decoders_MLPDecoder *self, void *closure) {
    int channels = mlp_channel_count(&(self->major_sync));
    if (channels > 0) {
        return Py_BuildValue("i", channels);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported channel assignment");
        return NULL;
    }
}

#define fL 0x1
#define fR 0x2
#define fC 0x4
#define LFE 0x8
#define bL 0x10
#define bR 0x20
#define bC 0x100

int mlp_channel_mask(struct mlp_MajorSync* major_sync) {
    switch (major_sync->channel_assignment) {
    case 0x0:
        return fC;
    case 0x1:
        return fL | fR;
    case 0x2:
        return fL | fR | bC;
    case 0x3:
        return fL | fR | bL | bR;
    case 0x4:
        return fL | fR | LFE;
    case 0x5:
        return fL | fR | LFE | bC;
    case 0x6:
        return fL | fR | LFE | bL | bR;
    case 0x7:
        return fL | fR | fC;
    case 0x8:
        return fL | fR | fC | bC;
    case 0x9:
        return fL | fR | fC | bL | bR;
    case 0xA:
        return fL | fR | fC | LFE;
    case 0xB:
        return fL | fR | fC | LFE | bC;
    case 0xC:
        return fL | fR | fC | LFE | bL | bR;
    case 0xD:
        return fL | fR | fC | bC;
    case 0xE:
        return fL | fR | fC | bL | bR;
    case 0xF:
        return fL | fR | fC | LFE;
    case 0x10:
        return fL | fR | fC | LFE | bC;
    case 0x11:
        return fL | fR | fC | LFE | bL | bR;
    case 0x12:
        return fL | fR | bL | bR | LFE;
    case 0x13:
        return fL | fR | bL | bR | fC;
    case 0x14:
        return fL | fR | bL | bR | fC | LFE;
    default:
        return -1;
    }

}

const static int mlp_channel_map[][6] = {
    /* 0x00 */ {  0, -1, -1, -1, -1, -1},
    /* 0x01 */ {  0,  1, -1, -1, -1, -1},
    /* 0x02 */ {  0,  1,  2, -1, -1, -1},
    /* 0x03 */ {  0,  1,  2,  3, -1, -1},
    /* 0x04 */ {  0,  1,  2, -1, -1, -1},
    /* 0x05 */ {  0,  1,  2,  3, -1, -1},
    /* 0x06 */ {  0,  1,  2,  3,  4, -1},
    /* 0x07 */ {  0,  1,  2, -1, -1, -1},
    /* 0x08 */ {  0,  1,  2,  3, -1, -1},
    /* 0x09 */ {  0,  1,  2,  3,  4, -1},
    /* 0x0A */ {  0,  1,  2,  3, -1, -1},
    /* 0x0B */ {  0,  1,  2,  3,  4, -1},
    /* 0x0C */ {  0,  1,  2,  3,  4,  5},
    /* 0x0D */ {  0,  1,  2,  3, -1, -1},
    /* 0x0E */ {  0,  1,  2,  3,  4, -1},
    /* 0x0F */ {  0,  1,  2,  3, -1, -1},
    /* 0x10 */ {  0,  1,  2,  3,  4, -1},
    /* 0x11 */ {  0,  1,  2,  3,  4,  5},
    /* 0x12 */ {  0,  1,  3,  4,  2, -1},
    /* 0x13 */ {  0,  1,  3,  4,  2, -1},
    /* 0x14 */ {  0,  1,  4,  5,  2,  3}
};

static PyObject*
MLPDecoder_channel_mask(decoders_MLPDecoder *self, void *closure) {
    int mask = mlp_channel_mask(&(self->major_sync));
    if (mask > 0) {
        return Py_BuildValue("i", mask);
    } else {
        PyErr_SetString(PyExc_ValueError, "unsupported channel assignment");
        return NULL;
    }
}

static PyObject*
MLPDecoder_read(decoders_MLPDecoder* self, PyObject *args) {
    int channel_count = mlp_channel_count(&(self->major_sync));
    int channel;

    PyObject* frame;
    struct ia_array wave_order;

    int frame_size = mlp_read_frame(self, &(self->frame_samples));

    if (frame_size > 0) {
        wave_order.size = channel_count;
        wave_order.arrays = malloc(sizeof(struct ia_array) * wave_order.size);

        /*reorder MLP channels into wave order*/
        for (channel = 0; channel < channel_count; channel++) {
            ia_link(&(wave_order.arrays[
                          mlp_channel_map[
                              self->major_sync.channel_assignment][channel]]),
                    &(self->frame_samples.arrays[channel]));
        }

        frame = ia_array_to_framelist(
                    &wave_order,
                    mlp_bits_per_sample(&(self->major_sync)));

        free(wave_order.arrays);

        return frame;
    } else if (frame_size == 0) {
        /*return empty FrameList object*/

        iaa_init(&wave_order, channel_count, 1);
        frame = ia_array_to_framelist(
                    &wave_order,
                    mlp_bits_per_sample(&(self->major_sync)));
        iaa_free(&wave_order);

        return frame;
    } else {
        return NULL;
    }
}

static PyObject*
MLPDecoder_close(decoders_MLPDecoder* self, PyObject *args) {
    /*FIXME - indicate stream is finished*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_analyze_frame(decoders_MLPDecoder* self, PyObject *args) {
    PyObject* substream_sizes = NULL;
    PyObject* substreams = NULL;
    PyObject* obj;

    struct mlp_MajorSync frame_major_sync;
    int substream;
    int total_frame_size;
    uint64_t target_read = self->bytes_read;
    int offset;

    offset = bs_ftell(self->bitstream);

    /*read the 32-bit total size value*/
    if ((total_frame_size =
         mlp_total_frame_size(self->bitstream)) == -1) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    target_read += total_frame_size;

    /*allocate space for Python objects*/
    substream_sizes = PyList_New(0);
    substreams = PyList_New(0);

    /*read a major sync, if present*/
    if (mlp_read_major_sync(self,
                            &frame_major_sync) == MLP_MAJOR_SYNC_ERROR) {
        PyErr_SetString(PyExc_IOError, "I/O error reading major sync");
        goto error;
    }
    /*FIXME - verify frame major sync against initial major sync*/

    /*read one SubstreamSize per substream*/
    for (substream = 0;
         substream < self->major_sync.substream_count;
         substream++) {
        if (mlp_read_substream_size(
                self->bitstream,
                &(self->substream_sizes[substream])) == OK) {
            obj = Py_BuildValue(
                      "{si si si}",
                      "nonrestart_substream",
                      self->substream_sizes[substream].nonrestart_substream,
                      "checkdata_present",
                      self->substream_sizes[substream].checkdata_present,
                      "substream_size",
                      self->substream_sizes[substream].substream_size);
            PyList_Append(substream_sizes, obj);
            Py_DECREF(obj);
        } else {
            goto error;
        }
    }

    /*read one Substream per substream*/
    for (substream = 0;
         substream < self->major_sync.substream_count;
         substream++) {
        if ((obj = mlp_analyze_substream(self, substream)) != NULL) {
            PyList_Append(substreams, obj);
            Py_DECREF(obj);
        } else
            goto error;
    }

    if (self->bytes_read != target_read) {
        PyErr_SetString(PyExc_ValueError,
                        "incorrect bytes read in frame\n");
        goto error;;
    }

    return Py_BuildValue("{si sN sN si}",
                         "total_frame_size", total_frame_size,
                         "substream_sizes", substream_sizes,
                         "substreams", substreams,
                         "offset", offset);
 error:
    Py_XDECREF(substream_sizes);
    Py_XDECREF(substreams);
    return NULL;
}

int
mlp_total_frame_size(Bitstream* bitstream) {
    int total_size;

    if (!setjmp(*bs_try(bitstream))) {
        bitstream->skip(bitstream, 4);
        total_size = bitstream->read(bitstream, 12) * 2;
        bitstream->skip(bitstream, 16);
        bs_etry(bitstream);
        return total_size;
    } else {
        bs_etry(bitstream);
        return -1;
    }
}

mlp_major_sync_status
mlp_read_major_sync(decoders_MLPDecoder* decoder,
                    struct mlp_MajorSync* major_sync) {
    Bitstream* bitstream = decoder->bitstream;

    if (!setjmp(*bs_try(bitstream))) {
        if (bitstream->read(bitstream, 24) != 0xF8726F) {
            /*sync words not found*/
            bs_etry(bitstream);
            fseek(bitstream->file, -3, SEEK_CUR);
            decoder->bytes_read -= 3;
            return MLP_MAJOR_SYNC_NOT_FOUND;
        }
        if (bitstream->read(bitstream, 8) != 0xBB) {
            /*stream type not 0xBB*/
            bs_etry(bitstream);
            fseek(bitstream->file, -4, SEEK_CUR);
            decoder->bytes_read -= 4;
            return MLP_MAJOR_SYNC_NOT_FOUND;
        }

        major_sync->group1_bits = bitstream->read(bitstream, 4);
        major_sync->group2_bits = bitstream->read(bitstream, 4);
        major_sync->group1_sample_rate = bitstream->read(bitstream, 4);
        major_sync->group2_sample_rate = bitstream->read(bitstream, 4);
        bitstream->skip(bitstream, 11); /*unknown 1*/
        major_sync->channel_assignment = bitstream->read(bitstream, 5);
        bitstream->skip(bitstream, 48); /*unknown 2*/
        bitstream->skip(bitstream, 1);  /*is VBR*/
        bitstream->skip(bitstream, 15); /*peak bitrate*/
        major_sync->substream_count = bitstream->read(bitstream, 4);
        bitstream->skip(bitstream, 92); /*unknown 3*/

        bs_etry(bitstream);
        return MLP_MAJOR_SYNC_OK;
    } else {
        bs_etry(bitstream);
        return MLP_MAJOR_SYNC_ERROR;
    }
}

int
mlp_read_frame(decoders_MLPDecoder* decoder,
               struct ia_array* frame_samples) {
    struct mlp_MajorSync frame_major_sync;
    int substream;
    int channel;
    unsigned int substream_channel_count;
    struct mlp_RestartHeader* restart_header;

    /*one ia_array per substream's samples,
      each with one or more channels of data*/
    struct ia_array* substream_samples = decoder->substream_samples;

    int total_frame_size;
    uint64_t target_read = decoder->bytes_read;

    /*read the 32-bit total size value*/
    if ((total_frame_size =
         mlp_total_frame_size(decoder->bitstream)) == -1) {
        return 0;
    }

    target_read += total_frame_size;

    /*read a major sync, if present*/
    if (mlp_read_major_sync(decoder,
                            &frame_major_sync) == MLP_MAJOR_SYNC_ERROR) {
        PyErr_SetString(PyExc_IOError, "I/O error reading major sync");
        return -1;
    }
    /*FIXME - verify frame major sync against initial major sync*/

    /*read one SubstreamSize per substream*/
    for (substream = 0;
         substream < decoder->major_sync.substream_count;
         substream++) {
        if (mlp_read_substream_size(
                decoder->bitstream,
                &(decoder->substream_sizes[substream])) == ERROR)
            return -1;
    }

    /*read one Substream per substream*/
    for (substream = 0;
         substream < decoder->major_sync.substream_count;
         substream++) {
        iaa_reset(&(substream_samples[substream]));
        if (mlp_read_substream(decoder,
                               substream,
                               &(substream_samples[substream])) == ERROR)
            return -1;
    }

    if (decoder->bytes_read != target_read) {
        PyErr_SetString(PyExc_ValueError,
                        "incorrect bytes read in frame\n");
        return -1;
    }

    /*convert 1-2 substreams into a single block of data*/
    for (substream = 0;
         substream < decoder->major_sync.substream_count;
         substream++) {
        substream_channel_count =
            mlp_substream_channel_count(decoder, substream);
        restart_header = &(decoder->restart_headers[substream]);
        for (channel = 0; channel < substream_channel_count; channel++) {
            /*The channels in the "channel_assignments" field
              seem to be offset by the "min_channel" value.*/
            ia_copy(&(frame_samples->arrays[
                          restart_header->min_channel +
                          restart_header->channel_assignments[channel]]),
                    &(decoder->substream_samples[substream].arrays[channel]));
        }
    }

    /*the final substream in our list of substreams*/
    substream = decoder->major_sync.substream_count - 1;

    /*rematrix all substream samples based on final substream's matrices*/
    mlp_rematrix_channels(
        frame_samples,
        mlp_channel_count(&(decoder->major_sync)),
        &(decoder->restart_headers[substream].noise_gen_seed),
        decoder->restart_headers[substream].noise_shift,
        &(decoder->decoding_parameters[substream].matrix_parameters),
        decoder->decoding_parameters[substream].quant_step_sizes);

    return total_frame_size;
}

mlp_status
mlp_read_substream_size(Bitstream* bitstream,
                        struct mlp_SubstreamSize* size) {
    if (bitstream->read(bitstream, 1) == 1) {
        PyErr_SetString(PyExc_ValueError,
                        "extraword cannot be present in substream size");
        return ERROR;
    }
    size->nonrestart_substream = bitstream->read(bitstream, 1);
    size->checkdata_present = bitstream->read(bitstream, 1);
    bitstream->skip(bitstream, 1);
    size->substream_size = bitstream->read(bitstream, 12) * 2;

    return OK;
}

mlp_status
mlp_read_substream(decoders_MLPDecoder* decoder,
                   int substream,
                   struct ia_array* samples) {
    Bitstream* bs = decoder->bitstream;
    int last_block = 0;
    int matrix;

    /*clear out the bypassed_lsbs values for each matrix*/
    for (matrix = 0; matrix < MAX_MLP_MATRICES; matrix++) {
        ia_reset(&(decoder->decoding_parameters[substream].matrix_parameters.matrices[matrix].bypassed_lsbs));
    }

    /*read blocks until "last" is indicated*/
    while (!last_block) {
        if (mlp_read_block(decoder, substream,
                           samples,
                           &last_block) == ERROR)
            return ERROR;
    }

    /*align stream to 16-bit boundary*/
    bs->byte_align(bs);
    if (decoder->bytes_read % 2)
        bs->skip(bs, 8);

    /*read checksum if indicated by the substream size field*/
    if (decoder->substream_sizes[substream].checkdata_present) {
        /*FIXME - verify checksum here*/
        bs->skip(bs, 16);
    }

    return OK;
}

PyObject*
mlp_analyze_substream(decoders_MLPDecoder* decoder,
                      int substream) {
    PyObject* blocks = PyList_New(0);
    PyObject* block;
    PyObject* restart_header;
    PyObject* decoding_parameters;
    PyObject* matrix_parameters;
    PyObject* output_shifts;
    PyObject* quant_step_sizes;
    PyObject* channel_parameters;
    PyObject* cp;
    PyObject* fir_coeffs;
    PyObject* iir_coeffs;
    PyObject* residuals;

    PyObject* list1;
    PyObject* list2;
    PyObject* obj;
    PyObject* obj2;

    int i;
    int j;
    int coeff_count;

    struct mlp_RestartHeader* header_s;
    struct mlp_DecodingParameters* parameter_s;
    struct mlp_MatrixParameters* matrix_s;
    struct mlp_Matrix* m_s;
    struct mlp_ChannelParameters* cp_s;
    struct mlp_FilterParameters* fir_s;
    struct mlp_FilterParameters* iir_s;
    struct i_array* channel;

    Bitstream* bs = decoder->bitstream;
    int last_block = 0;
    int substream_channel_count;

    /*read blocks until "last" is indicated*/
    while (!last_block) {
        /*initialize samples for next block*/
        iaa_reset(&(decoder->unfiltered_residuals));

        if (mlp_analyze_block(decoder, substream,
                              &(decoder->unfiltered_residuals),
                              &last_block) != ERROR) {
            substream_channel_count = mlp_substream_channel_count(decoder,
                                                                  substream);

            header_s = &(decoder->restart_headers[substream]);
            parameter_s = &(decoder->decoding_parameters[substream]);

            list1 = PyList_New(0);
            for (i = 0; i < substream_channel_count; i++) {
                obj = PyInt_FromLong(header_s->channel_assignments[i]);
                PyList_Append(list1, obj);
                Py_DECREF(obj);
            }

            restart_header = Py_BuildValue(
                "{si si si si si si si si si si sN}",
                "noise_type",
                header_s->noise_type,
                "output_timestamp",
                header_s->output_timestamp,
                "min_channel",
                header_s->min_channel,
                "max_channel",
                header_s->max_channel,
                "max_matrix_channel",
                header_s->max_matrix_channel,
                "noise_shift",
                header_s->noise_shift,
                "noise_gen_seed",
                header_s->noise_gen_seed,
                "data_check_present",
                header_s->data_check_present,
                "lossless_check",
                header_s->lossless_check,
                "checksum",
                header_s->checksum,
                "channel_assignments",
                list1);

            matrix_parameters = PyList_New(0);
            matrix_s = &(parameter_s->matrix_parameters);
            for (i = 0; i < matrix_s->count; i++) {
                m_s = &(matrix_s->matrices[i]);

                coeff_count = header_s->max_matrix_channel + 1 + 2;

                list1 = PyList_New(0);
                for (j = 0; j < coeff_count; j++) {
                    obj2 = PyInt_FromLong(m_s->coefficients[j]);
                    PyList_Append(list1, obj2);
                    Py_DECREF(obj2);
                }
                list2 = PyList_New(0);
                for (j = 0; j < m_s->bypassed_lsbs.size; j++) {
                    obj2 = PyInt_FromLong(m_s->bypassed_lsbs.data[j]);
                    PyList_Append(list2, obj2);
                    Py_DECREF(obj2);
                }
                obj = Py_BuildValue("{si si si sN sN}",
                                    "out_channel",
                                    m_s->out_channel,
                                    "fractional_bits",
                                    m_s->fractional_bits,
                                    "lsb_bypass",
                                    m_s->lsb_bypass,
                                    "coefficients",
                                    list1,
                                    "bypassed_lsbs",
                                    list2);
                PyList_Append(matrix_parameters, obj);
                Py_DECREF(obj);
            }

            output_shifts = PyList_New(0);
            for (i = 0; i <= header_s->max_matrix_channel; i++) {
                obj = PyInt_FromLong(parameter_s->output_shifts[i]);
                PyList_Append(output_shifts, obj);
                Py_DECREF(obj);
            }

            quant_step_sizes = PyList_New(0);
            for (i = 0; i < substream_channel_count; i++) {
                obj = PyInt_FromLong(parameter_s->quant_step_sizes[i]);
                PyList_Append(quant_step_sizes, obj);
                Py_DECREF(obj);
            }

            channel_parameters = PyList_New(0);
            for (i = 0; i < substream_channel_count; i++) {
                cp_s = &(parameter_s->channel_parameters[i]);

                fir_s = &(cp_s->fir_filter_parameters);
                list1 = PyList_New(0);
                for (j = 0; j < fir_s->coefficients.size; j++) {
                    obj = PyInt_FromLong(fir_s->coefficients.data[j]);
                    PyList_Append(list1, obj);
                    Py_DECREF(obj);
                }

                fir_coeffs = Py_BuildValue("{si sN}",
                                           "shift",
                                           fir_s->shift,
                                           "coefficients",
                                           list1);

                iir_s = &(cp_s->iir_filter_parameters);
                list1 = PyList_New(0);
                for (j = 0; j < iir_s->coefficients.size; j++) {
                    obj = PyInt_FromLong(iir_s->coefficients.data[j]);
                    PyList_Append(list1, obj);
                    Py_DECREF(obj);
                }
                list2 = PyList_New(0);
                for (j = 0; j < iir_s->state.size; j++) {
                    obj = PyInt_FromLong(iir_s->state.data[j]);
                    PyList_Append(list2, obj);
                    Py_DECREF(obj);
                }

                iir_coeffs = Py_BuildValue("{si sN sN}",
                                           "shift",
                                           iir_s->shift,
                                           "coefficients",
                                           list1,
                                           "state",
                                           list2);

                cp = Py_BuildValue(
                         "{si si si si sN sN}",
                         "huffman_offset",
                         cp_s->huffman_offset,
                         "signed_huffman_offset",
                         mlp_calculate_signed_offset(
                             cp_s->codebook,
                             cp_s->huffman_lsbs,
                             cp_s->huffman_offset,
                             parameter_s->quant_step_sizes[i]),
                         "codebook",
                         cp_s->codebook,
                         "huffman_lsbs",
                         cp_s->huffman_lsbs,
                         "fir_filter_parameters",
                         fir_coeffs,
                         "iir_filter_parameters",
                         iir_coeffs);
                PyList_Append(channel_parameters, cp);
                Py_DECREF(cp);
            }

            decoding_parameters = Py_BuildValue(
                "{si sN sN sN sN}",
                "block_size",
                parameter_s->block_size,
                "output_shifts",
                output_shifts,
                "quant_step_sizes",
                quant_step_sizes,
                "channel_parameters",
                channel_parameters,
                "matrix_parameters",
                matrix_parameters);

            residuals = PyList_New(0);
            for (i = 0; i < substream_channel_count; i++) {
                channel = &(decoder->unfiltered_residuals.arrays[i]);
                list1 = PyList_New(0);
                for (j = 0; j < channel->size; j++) {
                    obj = PyInt_FromLong(channel->data[j]);
                    PyList_Append(list1, obj);
                    Py_DECREF(obj);
                }
                PyList_Append(residuals, list1);
                Py_DECREF(list1);
            }

            block = Py_BuildValue("{sN sN sN}",
                                  "restart_header",
                                  restart_header,
                                  "decoding_parameters",
                                  decoding_parameters,
                                  "residuals",
                                  residuals);

            PyList_Append(blocks, block);
            Py_DECREF(block);
        } else {
            goto error;
        }
    }

    /*align stream to 16-bit boundary*/
    bs->byte_align(bs);
    if (decoder->bytes_read % 2)
        bs->skip(bs, 8);

    /*read checksum if indicated by the substream size field*/
    if (decoder->substream_sizes[substream].checkdata_present) {
        /*FIXME - verify checksum here*/
        bs->skip(bs, 16);
    }

    return blocks;
 error:
    Py_DECREF(blocks);
    return NULL;
}

unsigned int
mlp_substream_channel_count(decoders_MLPDecoder* decoder,
                            int substream) {
    return ((decoder->restart_headers[substream].max_channel) -
            (decoder->restart_headers[substream].min_channel)) + 1;
}

mlp_status
mlp_read_block(decoders_MLPDecoder* decoder,
               int substream,
               struct ia_array* block_data,
               int* last_block) {
    Bitstream* bitstream = decoder->bitstream;

    if (bitstream->read(bitstream, 1)) { /*check "params present" bit*/

        if (bitstream->read(bitstream, 1)) { /*check "header present" bit*/

            /*update substream's restart header*/
            if (mlp_read_restart_header(decoder, substream) == ERROR)
                return ERROR;
        }

        /*update substream's decoding parameters*/
        if (mlp_read_decoding_parameters(decoder, substream) == ERROR)
            return ERROR;
    }

    /*read block data based on decoding parameters*/
    iaa_reset(&(decoder->unfiltered_residuals));
    if (mlp_read_block_data(decoder,
                            substream,
                            &(decoder->unfiltered_residuals)) == ERROR)
        return ERROR;

    /*filter block's channels based on FIR/IIR filter parameters, if any*/
    if (mlp_filter_channels(&(decoder->unfiltered_residuals),
                            mlp_substream_channel_count(decoder, substream),
                            &(decoder->decoding_parameters[substream]),
                            block_data) == ERROR)
            return ERROR;

    /*update "last block" bit*/
    *last_block = bitstream->read(bitstream, 1);

    return OK;
}

mlp_status
mlp_analyze_block(decoders_MLPDecoder* decoder,
                  int substream,
                  struct ia_array* block_data,
                  int* last_block) {
    Bitstream* bitstream = decoder->bitstream;

    if (bitstream->read(bitstream, 1)) { /*check "params present" bit*/

        if (bitstream->read(bitstream, 1)) { /*check "header present" bit*/

            /*update substream's restart header*/
            if (mlp_read_restart_header(decoder, substream) == ERROR)
                return ERROR;
        }

        /*update substream's decoding parameters*/
        if (mlp_read_decoding_parameters(decoder, substream) == ERROR)
            return ERROR;
    }

    /*read block data based on decoding parameters*/
    if (mlp_read_block_data(decoder,
                            substream,
                            block_data) == ERROR)
        return ERROR;

    /*update "last block" bit*/
    *last_block = bitstream->read(bitstream, 1);

    return OK;
}

mlp_status
mlp_read_restart_header(decoders_MLPDecoder* decoder, int substream) {
    Bitstream* bs = decoder->bitstream;
    struct mlp_RestartHeader* header = &(decoder->restart_headers[substream]);
    struct mlp_DecodingParameters* parameters =
        &(decoder->decoding_parameters[substream]);
    struct mlp_ChannelParameters* channel_params;
    struct mlp_ParameterPresentFlags* flags =
        &(parameters->parameters_present_flags);
    int channel;

    /*read restart header values*/
    if (bs->read(bs, 13) != 0x18F5) {
        PyErr_SetString(PyExc_ValueError, "invalid restart header sync");
        return ERROR;
    }
    header->noise_type = bs->read(bs, 1);
    if (header->noise_type != 0) {
        PyErr_SetString(PyExc_ValueError, "MLP noise type must be 0");
        return ERROR;
    }

    header->output_timestamp = bs->read(bs, 16);
    header->min_channel = bs->read(bs, 4);
    header->max_channel = bs->read(bs, 4);
    header->max_matrix_channel = bs->read(bs, 4);
    header->noise_shift = bs->read(bs, 4);
    header->noise_gen_seed = bs->read(bs, 23);
    bs->skip(bs, 19);
    header->data_check_present = bs->read(bs, 1);
    header->lossless_check = bs->read(bs, 8);
    bs->skip(bs, 16);
    for (channel = 0; channel <= header->max_matrix_channel; channel++)
        header->channel_assignments[channel] = bs->read(bs, 6);
    header->checksum = bs->read(bs, 8);

    /*reset decoding parameters to default values*/
    flags->parameter_present_flags =
        flags->huffman_offset =
        flags->iir_filter_parameters =
        flags->fir_filter_parameters =
        flags->quant_step_sizes =
        flags->output_shifts =
        flags->matrix_parameters =
        flags->block_size = 1;

    parameters->block_size = 8;

    parameters->matrix_parameters.count = 0;

    for (channel = 0; channel < MAX_MLP_CHANNELS; channel++) {
        parameters->output_shifts[channel] = 0;
        parameters->quant_step_sizes[channel] = 0;
        channel_params = &(parameters->channel_parameters[channel]);

        ia_reset(&(channel_params->fir_filter_parameters.coefficients));
        channel_params->fir_filter_parameters.shift = 0;
        channel_params->fir_filter_parameters.has_state = 0;

        ia_reset(&(channel_params->iir_filter_parameters.coefficients));
        channel_params->iir_filter_parameters.shift = 0;
        channel_params->iir_filter_parameters.has_state = 0;
        ia_reset(&(channel_params->iir_filter_parameters.state));


        channel_params->huffman_offset = 0;
        channel_params->codebook = 0;
        channel_params->huffman_lsbs = 24;
    }

    return OK;
}

mlp_status
mlp_read_decoding_parameters(decoders_MLPDecoder* decoder, int substream) {
    struct mlp_DecodingParameters* parameters =
        &(decoder->decoding_parameters[substream]);
    struct mlp_ParameterPresentFlags* flags =
        &(parameters->parameters_present_flags);
    Bitstream* bs = decoder->bitstream;
    int substream_channel_count = mlp_substream_channel_count(decoder,
                                                              substream);
    int channel;

    /* parameters present flags */
    if (flags->parameter_present_flags && bs->read(bs, 1)) {
        flags->parameter_present_flags = bs->read(bs, 1);
        flags->huffman_offset = bs->read(bs, 1);
        flags->iir_filter_parameters = bs->read(bs, 1);
        flags->fir_filter_parameters = bs->read(bs, 1);
        flags->quant_step_sizes = bs->read(bs, 1);
        flags->output_shifts = bs->read(bs, 1);
        flags->matrix_parameters = bs->read(bs, 1);
        flags->block_size = bs->read(bs, 1);
    }

    /* block size */
    if (flags->block_size && bs->read(bs, 1)) {
        parameters->block_size = bs->read(bs, 9);
    }

    /* matrix parameters */
    if (flags->matrix_parameters && bs->read(bs, 1)) {
        if (mlp_read_matrix_parameters(
                bs,
                decoder->restart_headers[substream].max_matrix_channel,
                &(parameters->matrix_parameters)) == ERROR)
            return ERROR;
    }

    /* output shifts */
    if (flags->output_shifts && bs->read(bs, 1)) {
        for (channel = 0;
             channel <=
                 decoder->restart_headers[substream].max_matrix_channel;
             channel++)
            parameters->output_shifts[channel] = bs->read_signed(bs, 4);
    }

    /* quant step sizes */
    if (flags->quant_step_sizes && bs->read(bs, 1)) {
        for (channel = 0; channel < substream_channel_count; channel++)
            parameters->quant_step_sizes[channel] = bs->read(bs, 4);
    }

    /* one channel parameters per substream channel */
    for (channel = 0; channel < substream_channel_count; channel++) {
        if (bs->read(bs, 1))
            if (mlp_read_channel_parameters(
                    bs,
                    flags,
                    parameters->quant_step_sizes[channel],
                    &(parameters->channel_parameters[channel])) == ERROR)
                return ERROR;
    }

    return OK;
}

mlp_status
mlp_read_channel_parameters(Bitstream* bs,
                            struct mlp_ParameterPresentFlags* flags,
                            uint8_t quant_step_size,
                            struct mlp_ChannelParameters* parameters) {
    if (flags->fir_filter_parameters && bs->read(bs, 1)) {
        if (mlp_read_fir_filter_parameters(
                bs,
                &(parameters->fir_filter_parameters)) == ERROR)
            return ERROR;
    }

    if (flags->iir_filter_parameters && bs->read(bs, 1)) {
        if (mlp_read_iir_filter_parameters(
                bs,
                &(parameters->iir_filter_parameters)) == ERROR)
            return ERROR;
    }

    if (flags->huffman_offset && bs->read(bs, 1)) {
        parameters->huffman_offset = bs->read_signed(bs, 15);
    }

    parameters->codebook = bs->read(bs, 2);
    parameters->huffman_lsbs = bs->read(bs, 5);

    return OK;
}

mlp_status
mlp_read_fir_filter_parameters(Bitstream* bs,
                               struct mlp_FilterParameters* fir) {
    uint8_t order;
    uint8_t coefficient_bits;
    uint8_t coefficient_shift;
    int i;

    order = bs->read(bs, 4);

    if (order > 0) {
        ia_reset(&(fir->coefficients));

        fir->shift = bs->read(bs, 4);
        coefficient_bits = bs->read(bs, 5);
        coefficient_shift = bs->read(bs, 3);
        for (i = 0; i < order; i++)
            ia_append(&(fir->coefficients),
                      bs->read_signed(bs, coefficient_bits) <<
                      coefficient_shift);
        if (bs->read(bs, 1)) {
            PyErr_SetString(PyExc_ValueError,
                            "FIR coefficients cannot have state");
            return ERROR;
        }
    }

    return OK;
}

mlp_status
mlp_read_iir_filter_parameters(Bitstream* bs,
                               struct mlp_FilterParameters* iir) {
    uint8_t order;
    uint8_t coefficient_bits;
    uint8_t coefficient_shift;
    uint8_t state_bits;
    uint8_t state_shift;
    int i;

    order = bs->read(bs, 4);

    if (order > 0) {
        ia_reset(&(iir->coefficients));
        ia_reset(&(iir->state));

        iir->shift = bs->read(bs, 4);
        coefficient_bits = bs->read(bs, 5);
        coefficient_shift = bs->read(bs, 3);
        for (i = 0; i < order; i++)
            ia_append(&(iir->coefficients),
                      bs->read_signed(bs, coefficient_bits) <<
                      coefficient_shift);
        if ((iir->has_state = bs->read(bs, 1)) == 1) {
            state_bits = bs->read(bs, 4);
            state_shift = bs->read(bs, 4);

            for (i = 0; i < order; i++)
                ia_append(&(iir->state),
                          bs->read_signed(bs, state_bits) << state_shift);
            ia_reverse(&(iir->state));
        }
    }

    return OK;
}

mlp_status
mlp_read_matrix_parameters(Bitstream* bs,
                           int max_matrix_channel,
                           struct mlp_MatrixParameters* parameters) {
    struct mlp_Matrix* matrix;
    int i;
    int coeff_count;
    int coeff;
    uint8_t fractional_bits;

    coeff_count = max_matrix_channel + 1 + 2;

    parameters->count = bs->read(bs, 4);

    for (i = 0; i < parameters->count; i++) {
        matrix = &(parameters->matrices[i]);

        matrix->out_channel = bs->read(bs, 4);
        matrix->fractional_bits = fractional_bits = bs->read(bs, 4);
        matrix->lsb_bypass = bs->read(bs, 1);
        for (coeff = 0; coeff < coeff_count; coeff++) {
            if (bs->read(bs, 1))
                matrix->coefficients[coeff] =
                    (bs->read_signed(bs, fractional_bits + 2) <<
                     (14 - fractional_bits));
            else
                matrix->coefficients[coeff] = 0;
        }
    }

    return OK;
}

int32_t
mlp_calculate_signed_offset(uint8_t codebook,
                            uint8_t huffman_lsbs,
                            int16_t huffman_offset,
                            uint8_t quant_step_size) {
    int32_t lsb_bits;
    int32_t sign_shift;

    if (codebook > 0) {
        lsb_bits = huffman_lsbs - quant_step_size;
        sign_shift = lsb_bits + 2 - codebook;
        if (sign_shift >= 0)
            return huffman_offset - (7 << lsb_bits) - (1 << sign_shift);
        else
            return huffman_offset - (7 << lsb_bits);
    } else {
        lsb_bits = huffman_lsbs - quant_step_size;
        sign_shift = lsb_bits - 1;
        if (sign_shift >= 0)
            return huffman_offset - (1 << sign_shift);
        else
            return huffman_offset;
    }
}

mlp_status
mlp_read_block_data(decoders_MLPDecoder* decoder,
                    int substream,
                    struct ia_array* residuals) {
    struct mlp_DecodingParameters* parameters =
        &(decoder->decoding_parameters[substream]);
    struct mlp_ChannelParameters* channel_params;
    struct mlp_Matrix* matrix_params;
    Bitstream* bs = decoder->bitstream;
    int channel_count = mlp_substream_channel_count(decoder, substream);
    int msb;
    uint32_t lsb_count;
    int32_t signed_huffman_offset[MAX_MLP_CHANNELS];

    uint32_t pcm_frame;
    int channel;
    int32_t residual;

    int matrix;

    /*calculate all the signed huffman offsets
      based on the current huffman offsets/quant_step_sizes*/
    for (channel = 0; channel < channel_count; channel++) {
        channel_params = &(parameters->channel_parameters[channel]);
        signed_huffman_offset[channel] =
            mlp_calculate_signed_offset(channel_params->codebook,
                                        channel_params->huffman_lsbs,
                                        channel_params->huffman_offset,
                                        parameters->quant_step_sizes[channel]);
    }

    for (pcm_frame = 0; pcm_frame < parameters->block_size; pcm_frame++) {
        for (matrix = 0;
             matrix < parameters->matrix_parameters.count;
             matrix++) {
            matrix_params = &(parameters->matrix_parameters.matrices[matrix]);
            if (matrix_params->lsb_bypass)
                ia_append(&(matrix_params->bypassed_lsbs), bs->read(bs, 1));
            else
                ia_append(&(matrix_params->bypassed_lsbs), 0);
        }

        for (channel = 0; channel < channel_count; channel++) {
            channel_params = &(parameters->channel_parameters[channel]);
            lsb_count = (channel_params->huffman_lsbs -
                         parameters->quant_step_sizes[channel]);
            msb = mlp_read_code(bs, channel_params->codebook);
            if (msb < 0) {
                PyErr_SetString(PyExc_ValueError, "invalid MLP code");
                return ERROR;
            }
            residual = ((((msb << lsb_count) +
                          bs->read(bs, lsb_count)) +
                         signed_huffman_offset[channel]) <<
                        parameters->quant_step_sizes[channel]);
            ia_append(&(residuals->arrays[channel]), residual);
        }
    }

    return OK;
}

int
mlp_read_code(Bitstream* bs, int codebook) {
    int val;

    switch (codebook) {
    case 0:
        return 0;
    case 1:
        switch (val = bs->read_limited_unary(bs, 1, 9)) {
        case 0:
            return 7 + bs->read(bs, 2);
        case 1:
            val = bs->read_limited_unary(bs, 1, 7);
            if (val >= 0)
                return 11 + val;
            else
                return -1;
        case -1:
            return -1;
        default:
            return 8 - val;
        }
    case 2:
        switch (val = bs->read_limited_unary(bs, 1, 9)) {
        case 0:
            return 7 + bs->read(bs, 1);
        case 1:
            val = bs->read_limited_unary(bs, 1, 7);
            if (val >= 0)
                return 9 + val;
            else
                return -1;
        case -1:
            return -1;
        default:
            return 8 - val;
        }
    case 3:
        switch (val = bs->read_limited_unary(bs, 1, 9)) {
        case 0:
            return 7;
        case 1:
            val = bs->read_limited_unary(bs, 1, 7);
            if (val >= 0)
                return 8 + val;
            else
                return -1;
        case -1:
            return -1;
        default:
            return 8 - val;
        }
    default:
        return -1; /*unsupported codebook*/
    }
}

mlp_status
mlp_filter_channels(struct ia_array* unfiltered,
                    unsigned int channel_count,
                    struct mlp_DecodingParameters* parameters,
                    struct ia_array* filtered) {
    unsigned int channel;
    struct mlp_FilterParameters* fir_filter;
    struct mlp_FilterParameters* iir_filter;

    for (channel = 0; channel < channel_count; channel++) {
        fir_filter =
            &(parameters->channel_parameters[channel].fir_filter_parameters);
        iir_filter =
            &(parameters->channel_parameters[channel].iir_filter_parameters);
        if (mlp_filter_channel(&(unfiltered->arrays[channel]),
                               fir_filter,
                               iir_filter,
                               parameters->quant_step_sizes[channel],
                               &(filtered->arrays[channel])) == ERROR)
            return ERROR;
    }

    return OK;
}

mlp_status
mlp_filter_channel(struct i_array* unfiltered,
                   struct mlp_FilterParameters* fir_filter,
                   struct mlp_FilterParameters* iir_filter,
                   uint8_t quant_step_size,
                   struct i_array* filtered) {
    struct i_array fir_coefficients;
    struct i_array* fir_state;
    struct i_array iir_coefficients;
    struct i_array* iir_state;
    struct i_array fir_tail;
    struct i_array iir_tail;
    uint32_t shift;
    ia_data_t residual;
    ia_size_t i;
    ia_size_t j;
    int64_t accumulator;
    int32_t result;

    /*the number of bits to set to 0 at the beginning of each result*/
    int32_t mask = -1u << quant_step_size;

    ia_init(&fir_coefficients, 8);
    fir_state = &(fir_filter->state);
    ia_init(&iir_coefficients, 8);
    iir_state = &(iir_filter->state);

    if ((fir_filter->shift != 0) &&
        (iir_filter->shift != 0) &&
        (fir_filter->shift != iir_filter->shift)) {
        PyErr_SetString(PyExc_ValueError, "filter shifts must be identical");
        goto error;
    } else if (fir_filter->shift != 0) {
        shift = fir_filter->shift;
    } else {
        shift = iir_filter->shift;
    }

    ia_copy(&fir_coefficients, &(fir_filter->coefficients));
    ia_copy(&iir_coefficients, &(iir_filter->coefficients));

    ia_reverse(&fir_coefficients);
    ia_reverse(&iir_coefficients);

    for (i = 0; i < unfiltered->size; i++) {
        residual = unfiltered->data[i];
        accumulator = 0;
        ia_tail(&fir_tail, fir_state, fir_coefficients.size);
        ia_tail(&iir_tail, iir_state, iir_coefficients.size);
        for (j = 0; j < fir_coefficients.size; j++)
            accumulator += ((int64_t)fir_tail.data[j] *
                            (int64_t)fir_coefficients.data[j]);
        for (j = 0; j < iir_coefficients.size; j++)
            accumulator += ((int64_t)iir_tail.data[j] *
                            (int64_t)iir_coefficients.data[j]);

        accumulator >>= shift;
        result = (accumulator + residual) & mask;
        ia_append(filtered, result);
        ia_append(fir_state, result);
        ia_append(iir_state, result - accumulator);
    }

    ia_free(&fir_coefficients);
    ia_free(&iir_coefficients);
    ia_tail(iir_state, iir_state, 8);
    ia_tail(fir_state, fir_state, 8);

    return OK;
 error:
    ia_free(&fir_coefficients);
    ia_free(&iir_coefficients);
    return ERROR;
}

static inline int8_t
crop(int x) {
    if ((x % 256) / 128)
        return (x % 256) - 128;
    else
        return x % 256;
}

void
mlp_noise_channels(unsigned int pcm_frames,
                   uint32_t* noise_gen_seed,
                   uint8_t noise_shift,
                   struct i_array* noise_channel1,
                   struct i_array* noise_channel2) {
    unsigned int i;
    uint32_t seed = *noise_gen_seed;
    uint32_t shifted;

    for (i = 0; i < pcm_frames; i++) {
        shifted = (seed >> 7) & 0xFFFF;
        ia_append(noise_channel1, ((int8_t)(seed >> 15)) << noise_shift);
        ia_append(noise_channel2, ((int8_t)(shifted)) << noise_shift);
        seed = (((seed << 16) & 0xFFFFFFFF) ^ shifted ^ (shifted << 5));
    }

    *noise_gen_seed = seed;
}

void
mlp_rematrix_channels(struct ia_array* channels,
                      unsigned int channel_count,
                      uint32_t* noise_gen_seed,
                      uint8_t noise_shift,
                      struct mlp_MatrixParameters* matrices,
                      uint8_t* quant_step_sizes) {
    uint8_t i;
    unsigned int pcm_frames = channels->arrays[0].size;
    struct i_array noise_channel1;
    struct i_array noise_channel2;

    ia_init(&noise_channel1, pcm_frames);
    ia_init(&noise_channel2, pcm_frames);

    mlp_noise_channels(pcm_frames, noise_gen_seed, noise_shift,
                       &noise_channel1, &noise_channel2);

    for (i = 0; i < matrices->count; i++)
        mlp_rematrix_channel(channels,
                             channel_count,
                             &noise_channel1,
                             &noise_channel2,
                             &(matrices->matrices[i]),
                             quant_step_sizes);

    ia_free(&noise_channel1);
    ia_free(&noise_channel2);
}

void
mlp_rematrix_channel(struct ia_array* channels,
                     unsigned int channel_count,
                     struct i_array* noise_channel1,
                     struct i_array* noise_channel2,
                     struct mlp_Matrix* matrix,
                     uint8_t* quant_step_sizes) {
    unsigned int pcm_frames = channels->arrays[0].size;
    unsigned int i;
    unsigned int j;
    int64_t accumulator;
    int32_t mask = -1u << quant_step_sizes[matrix->out_channel];

    for (i = 0; i < pcm_frames; i++) {
        accumulator = 0;
        for (j = 0; j < channel_count; j++)
            accumulator += ((int64_t)channels->arrays[j].data[i] *
                            (int64_t)matrix->coefficients[j]);
        accumulator += ((int64_t)noise_channel1->data[i] *
                        (int64_t)matrix->coefficients[j++]);
        accumulator += ((int64_t)noise_channel2->data[i] *
                        (int64_t)matrix->coefficients[j++]);
        accumulator = (((accumulator >> 14) & mask) +
                       matrix->bypassed_lsbs.data[i]);
        channels->arrays[matrix->out_channel].data[i] = (ia_data_t)accumulator;
    }
}

#include "pcm.c"
