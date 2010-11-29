#include "mlp.h"

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
    int channel;

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

    for (substream = 0;
         substream < self->major_sync.substream_count;
         substream++) {
        for (channel = 0; channel < MAX_MLP_CHANNELS; channel++) {
            ia_init(&(self->decoding_parameters[substream].channel_parameters[channel].fir_filter_parameters.coefficients), 2);
            ia_init(&(self->decoding_parameters[substream].channel_parameters[channel].iir_filter_parameters.coefficients), 2);
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
    int channel;

    for (substream = 0;
         substream < self->major_sync.substream_count;
         substream++) {
        for (channel = 0; channel < MAX_MLP_CHANNELS; channel++) {
            ia_free(&(self->decoding_parameters[substream].channel_parameters[channel].fir_filter_parameters.coefficients));
            ia_free(&(self->decoding_parameters[substream].channel_parameters[channel].iir_filter_parameters.coefficients));
        }
    }

    bs_close(self->bitstream);
    free(self->substream_sizes);
    free(self->restart_headers);
    free(self->decoding_parameters);

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

static PyObject*
MLPDecoder_channel_mask(decoders_MLPDecoder *self, void *closure) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_read(decoders_MLPDecoder* self, PyObject *args) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_close(decoders_MLPDecoder* self, PyObject *args) {
    /*FIXME*/
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
MLPDecoder_analyze_frame(decoders_MLPDecoder* self, PyObject *args) {
    int frame_size = mlp_read_frame(self);
    if (frame_size > 0) {
        return Py_BuildValue("i", frame_size);
    } else if (frame_size == 0) {
        Py_INCREF(Py_None);
        return Py_None;
    } else {
        return NULL;
    }
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
mlp_read_frame(decoders_MLPDecoder* decoder) {
    struct mlp_MajorSync frame_major_sync;
    int substream;
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
        if (mlp_read_substream(decoder, substream) == ERROR)
            return -1;
    }

    if (decoder->bytes_read != target_read) {
        PyErr_SetString(PyExc_ValueError,
                        "incorrect bytes read in frame\n");
        return -1;
    }

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
                   int substream) {
    Bitstream* bs = decoder->bitstream;
    int last_block = 0;

    /*read blocks until "last" is indicated*/
    while (!last_block)
        if (mlp_read_block(decoder, substream, &last_block) == ERROR)
            return ERROR;

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

int
mlp_substream_channel_count(decoders_MLPDecoder* decoder,
                            int substream) {
    return ((decoder->restart_headers[substream].max_channel) -
            (decoder->restart_headers[substream].min_channel)) + 1;
}

mlp_status
mlp_read_block(decoders_MLPDecoder* decoder,
               int substream,
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
    if (mlp_read_block_data(decoder, substream) == ERROR)
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

    /*FIXME - reset matrix parameters*/

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
        channel_params->signed_huffman_offset = (-1) << 23;
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
        /*FIXME - read matrix parameters*/
        PyErr_SetString(PyExc_ValueError, "read matrix parameters");
        return ERROR;
    }

    /* output shifts */
    if (flags->output_shifts && bs->read(bs, 1)) {
        /*FIXME - output shifts*/
        PyErr_SetString(PyExc_ValueError, "read output shifts");
        return ERROR;
    }

    /* quant step sizes */
    if (flags->quant_step_sizes && bs->read(bs, 1)) {
        for (channel = 0; channel < substream_channel_count; channel++)
            parameters->quant_step_sizes[channel] = bs->read(bs, 4);
    }

    /* one channal parameters per substream channel */
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
    uint32_t lsb_bits;
    int32_t sign_shift;

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
        parameters->huffman_offset = bs->read(bs, 15);
    } else {
        parameters->huffman_offset = 0;
    }

    parameters->codebook = bs->read(bs, 2);
    parameters->huffman_lsbs = bs->read(bs, 5);

    if (parameters->codebook > 0) {
        lsb_bits = parameters->huffman_lsbs - quant_step_size;
        sign_shift = lsb_bits + 2 - parameters->codebook;
        if (sign_shift >= 0)
            parameters->signed_huffman_offset =
                parameters->huffman_offset -
                (7 << lsb_bits) - (1 << sign_shift);
        else
            parameters->signed_huffman_offset =
                parameters->huffman_offset -
                (7 << lsb_bits);
    } else {
        lsb_bits = parameters->huffman_lsbs - quant_step_size;
        sign_shift = lsb_bits - 1;
        if (sign_shift >= 0)
            parameters->signed_huffman_offset =
                parameters->huffman_offset - (1 << sign_shift);
        else
            parameters->signed_huffman_offset =
                parameters->huffman_offset;
    }

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
    /*FIXME*/
    PyErr_SetString(PyExc_ValueError, "implement iir filter parameters");
    return ERROR;
}

mlp_status
mlp_read_block_data(decoders_MLPDecoder* decoder, int substream) {
    struct mlp_DecodingParameters* parameters =
        &(decoder->decoding_parameters[substream]);
    struct mlp_ChannelParameters* channel_params;
    Bitstream* bs = decoder->bitstream;
    int channel_count = mlp_substream_channel_count(decoder, substream);
    uint32_t lsb_count;

    uint32_t pcm_frame;
    int channel;
    int32_t residual;

    for (pcm_frame = 0; pcm_frame < parameters->block_size; pcm_frame++) {
        for (channel = 0; channel < channel_count; channel++) {
            channel_params = &(parameters->channel_parameters[channel]);
            lsb_count = (channel_params->huffman_lsbs -
                         parameters->quant_step_sizes[channel]);
            residual = ((((mlp_read_code(bs, channel_params->codebook) <<
                           lsb_count) |
                          bs->read(bs, lsb_count)) +
                         channel_params->signed_huffman_offset) <<
                        parameters->quant_step_sizes[channel]);
            /*FIXME - store decoded residual once calculated*/
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
            return 8 + val;
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
