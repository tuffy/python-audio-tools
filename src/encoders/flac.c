#include "flac.h"
#include "../pcmconv.h"
#include "../common/md5.h"
#include <string.h>
#include <limits.h>
#include <float.h>
#include <math.h>
#include <assert.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

#define VERSION_STRING_(x) #x
#define VERSION_STRING(x) VERSION_STRING_(x)
const static char* AUDIOTOOLS_VERSION = VERSION_STRING(VERSION);

#define DEFAULT_PADDING_SIZE 4096

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

#ifndef STANDALONE
PyObject*
encoders_encode_flac(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    char *filename;
    FILE *output_file;
    BitstreamWriter* output_stream;
    struct flac_context encoder;
    pcmreader* pcmreader;
    char version_string[0xFF];
    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "block_size",
                             "max_lpc_order",
                             "min_residual_partition_order",
                             "max_residual_partition_order",
                             "mid_side",
                             "adaptive_mid_side",
                             "exhaustive_model_search",

                             "disable_verbatim_subframes",
                             "disable_constant_subframes",
                             "disable_fixed_subframes",
                             "disable_lpc_subframes",
                             "padding_size",
                             NULL};
    audiotools__MD5Context md5sum;

    aa_int* samples;

    unsigned long long current_offset = 0;
    PyObject *frame_offsets = NULL;
    PyObject *offset = NULL;

    unsigned block_size = 0;
    unsigned padding_size = DEFAULT_PADDING_SIZE;
    enum {STREAMINFO};

    encoder.options.mid_side = 0;
    encoder.options.adaptive_mid_side = 0;
    encoder.options.exhaustive_model_search = 0;

    encoder.options.no_verbatim_subframes = 0;
    encoder.options.no_constant_subframes = 0;
    encoder.options.no_fixed_subframes = 0;
    encoder.options.no_lpc_subframes = 0;

    /*extract a filename, PCMReader-compatible object and encoding options:
      blocksize int*/
    if (!PyArg_ParseTupleAndKeywords(
            args, keywds, "sO&IIII|iiiiiiiI",
            kwlist,
            &filename,
            pcmreader_converter,
            &pcmreader,
            &(encoder.options.block_size),
            &(encoder.options.max_lpc_order),
            &(encoder.options.min_residual_partition_order),
            &(encoder.options.max_residual_partition_order),
            &(encoder.options.mid_side),
            &(encoder.options.adaptive_mid_side),
            &(encoder.options.exhaustive_model_search),

            &(encoder.options.no_verbatim_subframes),
            &(encoder.options.no_constant_subframes),
            &(encoder.options.no_fixed_subframes),
            &(encoder.options.no_lpc_subframes),
            &padding_size))
        return NULL;

    block_size = encoder.options.block_size;

    /*open the given filename for writing*/
    if ((output_file = fopen(filename, "wb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    }

    /*build a list for frame offset info*/
    frame_offsets = PyList_New(0);

#else

int
encoders_encode_flac(char *filename,
                     pcmreader* pcmreader,
                     unsigned block_size,
                     unsigned max_lpc_order,
                     unsigned min_residual_partition_order,
                     unsigned max_residual_partition_order,
                     int mid_side,
                     int adaptive_mid_side,
                     int exhaustive_model_search) {
    FILE* output_file;
    BitstreamWriter* output_stream;
    unsigned long long current_offset = 0;
    struct flac_context encoder;
    char version_string[0xFF];
    audiotools__MD5Context md5sum;
    aa_int* samples;
    unsigned padding_size = DEFAULT_PADDING_SIZE;
    enum {STREAMINFO};

    /*set user-defined encoding options*/
    encoder.options.block_size = block_size;
    encoder.options.min_residual_partition_order =
        min_residual_partition_order;
    encoder.options.max_residual_partition_order =
        max_residual_partition_order;
    encoder.options.max_lpc_order = max_lpc_order;
    encoder.options.exhaustive_model_search = exhaustive_model_search;
    encoder.options.mid_side = mid_side;
    encoder.options.adaptive_mid_side = adaptive_mid_side;

    encoder.options.no_verbatim_subframes = 0;
    encoder.options.no_constant_subframes = 0;
    encoder.options.no_fixed_subframes = 0;
    encoder.options.no_lpc_subframes = 0;

    /*FIXME - check for invalid output file*/
    output_file = fopen(filename, "wb");

#endif

    /*set derived encoding options*/
    if (block_size <= 192)
        encoder.options.qlp_coeff_precision = 7;
    else if (block_size <= 384)
        encoder.options.qlp_coeff_precision = 8;
    else if (block_size <= 576)
        encoder.options.qlp_coeff_precision = 9;
    else if (block_size <= 1152)
        encoder.options.qlp_coeff_precision = 10;
    else if (block_size <= 2304)
        encoder.options.qlp_coeff_precision = 11;
    else if (block_size <= 4608)
        encoder.options.qlp_coeff_precision = 12;
    else
        encoder.options.qlp_coeff_precision = 13;

    if (pcmreader->bits_per_sample <= 16) {
        encoder.options.max_rice_parameter = 0xE;
    } else {
        encoder.options.max_rice_parameter = 0x1E;
    }

    sprintf(version_string, "Python Audio Tools %s", AUDIOTOOLS_VERSION);
    audiotools__MD5Init(&md5sum);
    pcmreader->add_callback(pcmreader, md5_update, &md5sum, 1, 1);

    output_stream = bw_open(output_file, BS_BIG_ENDIAN);

    /*fill streaminfo with some placeholder values*/
    encoder.streaminfo.minimum_block_size = block_size;
    encoder.streaminfo.maximum_block_size = block_size;
    encoder.streaminfo.minimum_frame_size = 0xFFFFFF;
    encoder.streaminfo.maximum_frame_size = 0;
    encoder.streaminfo.sample_rate = pcmreader->sample_rate;
    encoder.streaminfo.channels = pcmreader->channels;
    encoder.streaminfo.bits_per_sample = pcmreader->bits_per_sample;
    encoder.streaminfo.total_samples = 0;
    memcpy(encoder.streaminfo.md5sum,
           "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
           16);

    encoder.total_flac_frames = 0;
    flacenc_init_encoder(&encoder);

    /*write FLAC stream header*/
    output_stream->write_64(output_stream, 32, 0x664C6143);

    /*write metadata header*/
    output_stream->write(output_stream, 1, 0);
    output_stream->write(output_stream, 7, 0);
    output_stream->write(output_stream, 24, 34);

    /*write placeholder STREAMINFO*/
    output_stream->mark(output_stream, STREAMINFO);
    flacenc_write_streaminfo(output_stream, &(encoder.streaminfo));

    /*write VORBIS_COMMENT*/
    output_stream->write(output_stream, 1, 0);
    output_stream->write(output_stream, 7, 4);
    output_stream->write(output_stream, 24,
                         (unsigned int)(4 + strlen(version_string) + 4));

    /*write VORBIS_COMMENT fields as little-endian output*/
    output_stream->set_endianness(output_stream, BS_LITTLE_ENDIAN);
    output_stream->write(output_stream, 32, (unsigned)strlen(version_string));
    output_stream->write_bytes(output_stream,
                               (uint8_t*)version_string,
                               (unsigned)strlen(version_string));
    output_stream->write(output_stream, 32, 0);
    output_stream->set_endianness(output_stream, BS_BIG_ENDIAN);

    /*write PADDING*/
    output_stream->write(output_stream, 1, 1);
    output_stream->write(output_stream, 7, 1);
    output_stream->write(output_stream, 24, padding_size);
    output_stream->write(output_stream, padding_size * 8, 0);

    /*build frames until reader is empty,
      which updates STREAMINFO in the process*/
    samples = aa_int_new();

    if (pcmreader->read(pcmreader, block_size, samples))
        goto error;

    while (samples->_[0]->len > 0) {
#ifndef STANDALONE
        offset = Py_BuildValue("(K, I)",
                               current_offset,
                               samples->_[0]->len);
        PyList_Append(frame_offsets, offset);
        Py_DECREF(offset);
#endif
        encoder.frame->reset(encoder.frame);
        flacenc_write_frame((BitstreamWriter*)encoder.frame, &encoder, samples);
        encoder.streaminfo.total_samples += samples->_[0]->len;
        encoder.streaminfo.minimum_frame_size =
            MIN(encoder.streaminfo.minimum_frame_size,
                encoder.frame->bits_written(encoder.frame) / 8);
        encoder.streaminfo.maximum_frame_size =
            MAX(encoder.streaminfo.maximum_frame_size,
                encoder.frame->bits_written(encoder.frame) / 8);
        current_offset += encoder.frame->bytes_written(encoder.frame);
        encoder.frame->copy(encoder.frame, output_stream);

        if (pcmreader->read(pcmreader, block_size, samples))
            goto error;
    }

    /*go back and re-write STREAMINFO with complete values*/
    audiotools__MD5Final(encoder.streaminfo.md5sum, &md5sum);
    output_stream->rewind(output_stream, STREAMINFO);
    flacenc_write_streaminfo(output_stream, &encoder.streaminfo);
    output_stream->unmark(output_stream, STREAMINFO);

    samples->del(samples); /*deallocate the temporary samples block*/
    pcmreader->del(pcmreader);
    flacenc_free_encoder(&encoder);
    output_stream->close(output_stream); /*close the output file*/
#ifndef STANDALONE
    return frame_offsets;
 error:
    /*an error result does everything a regular result does
      but returns NULL instead of Py_None*/
    Py_XDECREF(frame_offsets);
    samples->del(samples);
    pcmreader->del(pcmreader);
    flacenc_free_encoder(&encoder);
    output_stream->unmark(output_stream, STREAMINFO);
    output_stream->close(output_stream); /*close the output file*/
    return NULL;
}
#else
    return 1;
 error:
    samples->del(samples);
    pcmreader->del(pcmreader);
    flacenc_free_encoder(&encoder);
    output_stream->unmark(output_stream, STREAMINFO);
    output_stream->close(output_stream); /*close the output file*/
    return 0;
}
#endif


void
flacenc_init_encoder(struct flac_context* encoder)
{
    encoder->average_samples = a_int_new();
    encoder->difference_samples = a_int_new();
    encoder->left_subframe = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->right_subframe = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->average_subframe = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->difference_subframe = bw_open_recorder(BS_BIG_ENDIAN);

    encoder->subframe_samples = a_int_new();

    encoder->frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->fixed_subframe = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->fixed_subframe_orders = aa_int_new();
    encoder->truncated_order = l_int_new();

    encoder->lpc_subframe = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->tukey_window = a_double_new();
    encoder->windowed_signal = a_double_new();
    encoder->autocorrelation_values = a_double_new();
    encoder->lp_coefficients = aa_double_new();
    encoder->lp_error = a_double_new();
    encoder->qlp_coefficients = a_int_new();
    encoder->lpc_residual = a_int_new();

    encoder->best_rice_parameters = a_int_new();
    encoder->rice_parameters = a_int_new();
    encoder->remaining_residuals = l_int_new();
    encoder->residual_partitions = al_int_new();
    encoder->best_residual_partitions = al_int_new();
}

void
flacenc_free_encoder(struct flac_context* encoder)
{
    encoder->average_samples->del(encoder->average_samples);
    encoder->difference_samples->del(encoder->difference_samples);
    encoder->left_subframe->close(encoder->left_subframe);
    encoder->right_subframe->close(encoder->right_subframe);
    encoder->average_subframe->close(encoder->average_subframe);
    encoder->difference_subframe->close(encoder->difference_subframe);

    encoder->subframe_samples->del(encoder->subframe_samples);

    encoder->frame->close(encoder->frame);
    encoder->fixed_subframe->close(encoder->fixed_subframe);
    encoder->fixed_subframe_orders->del(encoder->fixed_subframe_orders);
    encoder->truncated_order->del(encoder->truncated_order);

    encoder->lpc_subframe->close(encoder->lpc_subframe);
    encoder->tukey_window->del(encoder->tukey_window);
    encoder->windowed_signal->del(encoder->windowed_signal);
    encoder->autocorrelation_values->del(encoder->autocorrelation_values);
    encoder->lp_coefficients->del(encoder->lp_coefficients);
    encoder->lp_error->del(encoder->lp_error);
    encoder->qlp_coefficients->del(encoder->qlp_coefficients);
    encoder->lpc_residual->del(encoder->lpc_residual);

    encoder->best_rice_parameters->del(encoder->best_rice_parameters);
    encoder->rice_parameters->del(encoder->rice_parameters);
    encoder->remaining_residuals->del(encoder->remaining_residuals);
    encoder->residual_partitions->del(encoder->residual_partitions);
    encoder->best_residual_partitions->del(encoder->best_residual_partitions);
}

void
flacenc_write_streaminfo(BitstreamWriter* bs,
                         const struct flac_STREAMINFO* streaminfo)
{
    int i;

    bs->write(bs, 16, MAX(MIN(streaminfo->minimum_block_size,
                              (1 << 16) - 1), 0));

    bs->write(bs, 16, MAX(MIN(streaminfo->maximum_block_size,
                              (1 << 16) - 1),0));

    bs->write(bs, 24, MAX(MIN(streaminfo->minimum_frame_size,
                              (1 << 24) - 1), 0));

    bs->write(bs, 24, MAX(MIN(streaminfo->maximum_frame_size,
                              (1 << 24) - 1), 0));

    bs->write(bs, 20, MAX(MIN(streaminfo->sample_rate,
                              (1 << 20) - 1), 0));

    bs->write(bs, 3, MAX(MIN(streaminfo->channels - 1,
                             (1 << 3) - 1), 0));

    bs->write(bs, 5, MAX(MIN(streaminfo->bits_per_sample - 1,
                             (1 << 5) - 1), 0));

    assert(streaminfo->total_samples >= 0);
    assert(streaminfo->total_samples < (int64_t)(1ll << 36));
    bs->write_64(bs, 36, streaminfo->total_samples);

    for (i = 0; i < 16; i++)
        bs->write(bs, 8, streaminfo->md5sum[i]);
}


void
flacenc_write_frame_header(BitstreamWriter *bs,
                           const struct flac_STREAMINFO *streaminfo,
                           unsigned block_size,
                           unsigned channel_assignment,
                           unsigned frame_number)
{
    unsigned block_size_bits;
    unsigned sample_rate_bits;
    unsigned bits_per_sample_bits;
    int crc8 = 0;

    bs->add_callback(bs, (bs_callback_f)flac_crc8, &crc8);

    /*determine the block size bits from the given amount of samples*/
    switch (block_size) {
    case 192:   block_size_bits = 0x1; break;
    case 576:   block_size_bits = 0x2; break;
    case 1152:  block_size_bits = 0x3; break;
    case 2304:  block_size_bits = 0x4; break;
    case 4608:  block_size_bits = 0x5; break;
    case 256:   block_size_bits = 0x8; break;
    case 512:   block_size_bits = 0x9; break;
    case 1024:  block_size_bits = 0xA; break;
    case 2048:  block_size_bits = 0xB; break;
    case 4096:  block_size_bits = 0xC; break;
    case 8192:  block_size_bits = 0xD; break;
    case 16384: block_size_bits = 0xE; break;
    case 32768: block_size_bits = 0xF; break;
    default:
        if (block_size < (0xFF + 1))
            block_size_bits = 0x6;
        else if (block_size < (0xFFFF + 1))
            block_size_bits = 0x7;
        else
            block_size_bits = 0x0;
        break;
    }

    /*determine sample rate bits from streaminfo*/
    switch (streaminfo->sample_rate) {
    case 88200:  sample_rate_bits = 0x1; break;
    case 176400: sample_rate_bits = 0x2; break;
    case 192000: sample_rate_bits = 0x3; break;
    case 8000:   sample_rate_bits = 0x4; break;
    case 16000:  sample_rate_bits = 0x5; break;
    case 22050:  sample_rate_bits = 0x6; break;
    case 24000:  sample_rate_bits = 0x7; break;
    case 32000:  sample_rate_bits = 0x8; break;
    case 44100:  sample_rate_bits = 0x9; break;
    case 48000:  sample_rate_bits = 0xA; break;
    case 96000:  sample_rate_bits = 0xB; break;
    default:
        if ((streaminfo->sample_rate <= 255000) &&
            ((streaminfo->sample_rate % 1000) == 0))
            sample_rate_bits = 0xC;
        else if ((streaminfo->sample_rate <= 655350) &&
                 ((streaminfo->sample_rate % 10) == 0))
            sample_rate_bits = 0xE;
        else if (streaminfo->sample_rate <= 0xFFFF)
            sample_rate_bits = 0xD;
        else
            sample_rate_bits = 0x0;
        break;
    }

    /*determine bits-per-sample bits from streaminfo*/
    switch (streaminfo->bits_per_sample) {
    case 8:  bits_per_sample_bits = 0x1; break;
    case 12: bits_per_sample_bits = 0x2; break;
    case 16: bits_per_sample_bits = 0x4; break;
    case 20: bits_per_sample_bits = 0x5; break;
    case 24: bits_per_sample_bits = 0x6; break;
    default: bits_per_sample_bits = 0x0; break;
    }

    /*once the four bits-encoded fields are set, write the actual header*/
    bs->write(bs, 14, 0x3FFE);              /*sync code*/
    bs->write(bs, 1, 0);                    /*reserved*/
    bs->write(bs, 1, 0);                    /*blocking strategy*/
    bs->write(bs, 4, block_size_bits);      /*block size*/
    bs->write(bs, 4, sample_rate_bits);     /*sample rate*/
    bs->write(bs, 4, channel_assignment);   /*channel assignment*/
    bs->write(bs, 3, bits_per_sample_bits); /*bits per sample*/
    bs->write(bs, 1, 0);                    /*padding*/

    /*frame number is taken from total_frames in streaminfo*/
    write_utf8(bs, frame_number);

    /*if block_size_bits are 0x6 or 0x7, write a PCM frames field*/
    if (block_size_bits == 0x6)
        bs->write(bs, 8, block_size - 1);
    else if (block_size_bits == 0x7)
        bs->write(bs, 16, block_size - 1);

    /*if sample rate is unusual, write one of the three sample rate fields*/
    if (sample_rate_bits == 0xC)
        bs->write(bs, 8, streaminfo->sample_rate / 1000);
    else if (sample_rate_bits == 0xD)
        bs->write(bs, 16, streaminfo->sample_rate);
    else if (sample_rate_bits == 0xE)
        bs->write(bs, 16, streaminfo->sample_rate / 10);

    /*write CRC-8*/
    bs->pop_callback(bs, NULL);
    bs->write(bs, 8, crc8);
}

void
flacenc_write_frame(BitstreamWriter* bs,
                    struct flac_context* encoder,
                    const aa_int* samples)
{
    unsigned block_size = samples->_[0]->len;
    unsigned channel_count = samples->len;
    unsigned channel;
    int crc16 = 0;

    bs->add_callback(bs, (bs_callback_f)flac_crc16, &crc16);

    if ((encoder->streaminfo.channels == 2) &&
        ((encoder->options.mid_side || encoder->options.adaptive_mid_side))) {
        BitstreamRecorder* left_subframe = encoder->left_subframe;
        BitstreamRecorder* right_subframe = encoder->right_subframe;
        BitstreamRecorder* average_subframe = encoder->average_subframe;
        BitstreamRecorder* difference_subframe = encoder->difference_subframe;
        unsigned left_subframe_bits;
        unsigned right_subframe_bits;
        unsigned average_subframe_bits;
        unsigned difference_subframe_bits;

        left_subframe->reset(left_subframe);
        right_subframe->reset(right_subframe);
        average_subframe->reset(average_subframe);
        difference_subframe->reset(difference_subframe);

        flacenc_average_difference(samples,
                                   encoder->average_samples,
                                   encoder->difference_samples);

        flacenc_write_subframe((BitstreamWriter*)left_subframe,
                               encoder,
                               encoder->streaminfo.bits_per_sample,
                               samples->_[0]);

        flacenc_write_subframe((BitstreamWriter*)right_subframe,
                               encoder,
                               encoder->streaminfo.bits_per_sample,
                               samples->_[1]);

        flacenc_write_subframe((BitstreamWriter*)average_subframe,
                               encoder,
                               encoder->streaminfo.bits_per_sample,
                               encoder->average_samples);

        flacenc_write_subframe((BitstreamWriter*)difference_subframe,
                               encoder,
                               encoder->streaminfo.bits_per_sample + 1,
                               encoder->difference_samples);

        left_subframe_bits =
            left_subframe->bits_written(left_subframe);
        right_subframe_bits =
            right_subframe->bits_written(right_subframe);
        average_subframe_bits =
            average_subframe->bits_written(average_subframe);
        difference_subframe_bits =
            difference_subframe->bits_written(difference_subframe);

        if (encoder->options.mid_side) {
            if ((left_subframe_bits + right_subframe_bits) <
                MIN(MIN(left_subframe_bits + difference_subframe_bits,
                        difference_subframe_bits + right_subframe_bits),
                    average_subframe_bits + difference_subframe_bits)) {
                /*write subframes independently*/

                flacenc_write_frame_header(bs,
                                           &(encoder->streaminfo),
                                           block_size,
                                           0x1,
                                           encoder->total_flac_frames++);
                left_subframe->copy(left_subframe, bs);
                right_subframe->copy(right_subframe, bs);

            } else if (left_subframe_bits <
                       MIN(right_subframe_bits, average_subframe_bits)) {
                /*write left-difference subframes*/

                flacenc_write_frame_header(bs,
                                           &(encoder->streaminfo),
                                           block_size,
                                           0x8,
                                           encoder->total_flac_frames++);
                left_subframe->copy(left_subframe, bs);
                difference_subframe->copy(difference_subframe, bs);

            } else if (right_subframe_bits < average_subframe_bits) {
                /*write difference-right subframes*/

                flacenc_write_frame_header(bs,
                                           &(encoder->streaminfo),
                                           block_size,
                                           0x9,
                                           encoder->total_flac_frames++);
                difference_subframe->copy(difference_subframe, bs);
                right_subframe->copy(right_subframe, bs);

            } else {
                /*write average-difference subframes*/

                flacenc_write_frame_header(bs,
                                           &(encoder->streaminfo),
                                           block_size,
                                           0xA,
                                           encoder->total_flac_frames++);
                average_subframe->copy(average_subframe, bs);
                difference_subframe->copy(difference_subframe, bs);
            }
        } else if ((left_subframe_bits + right_subframe_bits) <
                   (average_subframe_bits + difference_subframe_bits)) {
            /*write subframes independently*/

            flacenc_write_frame_header(bs,
                                       &(encoder->streaminfo),
                                       block_size,
                                       0x1,
                                       encoder->total_flac_frames++);
            left_subframe->copy(left_subframe, bs);
            right_subframe->copy(right_subframe, bs);

        } else {
            /*write average-difference subframes*/

            flacenc_write_frame_header(bs,
                                       &(encoder->streaminfo),
                                       block_size,
                                       0xA,
                                       encoder->total_flac_frames++);
            average_subframe->copy(average_subframe, bs);
            difference_subframe->copy(difference_subframe, bs);
        }
    } else {
        /*write channels indepedently*/
        flacenc_write_frame_header(bs,
                                   &(encoder->streaminfo),
                                   block_size,
                                   channel_count - 1,
                                   encoder->total_flac_frames++);

        for (channel = 0; channel < channel_count; channel++)
            flacenc_write_subframe(bs,
                                   encoder,
                                   encoder->streaminfo.bits_per_sample,
                                   samples->_[channel]);
    }

    bs->byte_align(bs);
    bs->pop_callback(bs, NULL);
    bs->write(bs, 16, crc16);
}

void
flacenc_write_subframe(BitstreamWriter* bs,
                       struct flac_context* encoder,
                       unsigned bits_per_sample,
                       const a_int* samples)
{
    a_int* subframe_samples = encoder->subframe_samples;

    int try_VERBATIM = !encoder->options.no_verbatim_subframes;
    int try_CONSTANT = !encoder->options.no_constant_subframes;
    int try_FIXED = !encoder->options.no_fixed_subframes;
    int try_LPC = !((encoder->options.no_lpc_subframes) ||
                    (encoder->options.max_lpc_order == 0));

    unsigned wasted_bps;
    unsigned verbatim_bits = INT_MAX;

    /*check for CONSTANT subframe and return one, if allowed*/
    if (try_CONSTANT && flacenc_all_identical(samples)) {
        flacenc_write_constant_subframe(bs, bits_per_sample, 0,
                                        samples->_[0]);
    } else {
        /*extract wasted bits-per-sample, if any*/
        wasted_bps = flacenc_max_wasted_bits_per_sample(samples);
        if (wasted_bps > 0) {
            unsigned i;

            subframe_samples->reset_for(subframe_samples, samples->len);
            for (i = 0; i < samples->len; i++)
                a_append(subframe_samples, samples->_[i] >> wasted_bps);
        } else {
            samples->copy(samples, subframe_samples);
        }

        /*build FIXED subframe, if allowed*/
        if (try_FIXED) {
            encoder->fixed_subframe->reset(encoder->fixed_subframe);
            flacenc_write_fixed_subframe(
                (BitstreamWriter*)encoder->fixed_subframe,
                encoder,
                bits_per_sample,
                wasted_bps,
                subframe_samples);
        }

        /*build LPC subframe, if allowed*/
        if (try_LPC) {
            encoder->lpc_subframe->reset(encoder->lpc_subframe);
            flacenc_write_lpc_subframe(
                (BitstreamWriter*)encoder->lpc_subframe,
                encoder,
                bits_per_sample,
                wasted_bps,
                subframe_samples);
        }

        if (try_VERBATIM) {
            verbatim_bits = ((bits_per_sample - wasted_bps) *
                             subframe_samples->len);
        }

        if (try_FIXED && try_LPC && try_VERBATIM) {
            /*if FIXED = y , LPC = y , VERBATIM = y
              return min(FIXED, LPC, VERBATIM) subframes*/
            unsigned fixed_bits =
                encoder->fixed_subframe->bits_written(encoder->fixed_subframe);
            unsigned lpc_bits =
                encoder->lpc_subframe->bits_written(encoder->lpc_subframe);

            if (fixed_bits < MIN(lpc_bits, verbatim_bits)) {
                encoder->fixed_subframe->copy(encoder->fixed_subframe, bs);
            } else if (lpc_bits < verbatim_bits) {
                encoder->lpc_subframe->copy(encoder->lpc_subframe, bs);
            } else {
                flacenc_write_verbatim_subframe(bs,
                                                bits_per_sample,
                                                wasted_bps,
                                                subframe_samples);
            }
        } else if (!try_FIXED && !try_LPC && !try_VERBATIM) {
            /*if FIXED = n , LPC = n , VERBATIM = n
              return VERBATIM subframe anyway*/
            flacenc_write_verbatim_subframe(bs,
                                            bits_per_sample,
                                            wasted_bps,
                                            subframe_samples);
        } else if (try_FIXED && !try_LPC && !try_VERBATIM) {
            /*if FIXED = y , LPC = n , VERBATIM = n
              return FIXED subframe*/
            encoder->fixed_subframe->copy(encoder->fixed_subframe, bs);
        } else if (!try_FIXED && try_LPC && !try_VERBATIM) {
            /*if FIXED = n , LPC = y , VERBATIM = n
              return LPC subframe*/
            encoder->lpc_subframe->copy(encoder->lpc_subframe, bs);
        } else if (try_FIXED && try_LPC && !try_VERBATIM) {
            /*if FIXED = y , LPC = y , VERBATIM = n
              return min(FIXED, LPC) subframes*/
            if (encoder->fixed_subframe->bits_written(encoder->fixed_subframe) <
                encoder->lpc_subframe->bits_written(encoder->lpc_subframe)) {
                encoder->fixed_subframe->copy(encoder->fixed_subframe, bs);
            } else {
                encoder->lpc_subframe->copy(encoder->lpc_subframe, bs);
            }
        } else if (!try_FIXED && !try_LPC && try_VERBATIM) {
            /*if FIXED = n , LPC = n , VERBATIM = y
              return VERBATIM subframe*/
            flacenc_write_verbatim_subframe(bs,
                                            bits_per_sample,
                                            wasted_bps,
                                            subframe_samples);
        } else if (try_FIXED && !try_LPC && try_VERBATIM) {
            /*if FIXED = y , LPC = n , VERBATIM = y
              return min(FIXED, VERBATIM) subframes*/
            if (encoder->fixed_subframe->bits_written(encoder->fixed_subframe) <
                verbatim_bits) {
                encoder->fixed_subframe->copy(encoder->fixed_subframe, bs);
            } else {
                flacenc_write_verbatim_subframe(bs,
                                                bits_per_sample,
                                                wasted_bps,
                                                subframe_samples);
            }
        } else if (!try_FIXED && try_LPC && try_VERBATIM) {
            /*if FIXED = n , LPC = y , VERBATIM = y
              return min(LPC, VERBATIM) subframes*/
            if (encoder->lpc_subframe->bits_written(encoder->lpc_subframe) <
                verbatim_bits) {
                encoder->lpc_subframe->copy(encoder->lpc_subframe, bs);
            } else {
                flacenc_write_verbatim_subframe(bs,
                                                bits_per_sample,
                                                wasted_bps,
                                                subframe_samples);
            }
        } else {
            /*shouldn't get here
              since all the options are tested exhaustively*/
            assert(0);
        }
    }
}

void
flacenc_write_constant_subframe(BitstreamWriter *bs,
                                unsigned bits_per_sample,
                                unsigned wasted_bits_per_sample,
                                int sample)
{
    /*write subframe header*/
    bs->write(bs, 1, 0);
    bs->write(bs, 6, 0);
    if (wasted_bits_per_sample) {
        bs->write(bs, 1, 1);
        bs->write_unary(bs, 1, wasted_bits_per_sample - 1);
    } else
        bs->write(bs, 1, 0);

    /*write subframe sample*/
    bs->write_signed(bs, bits_per_sample, sample);
}

void
flacenc_write_verbatim_subframe(BitstreamWriter *bs,
                                unsigned bits_per_sample,
                                unsigned wasted_bits_per_sample,
                                const a_int* samples)
{
    unsigned i;

    /*write subframe header*/
    bs->write(bs, 1, 0);
    bs->write(bs, 6, 1);
    if (wasted_bits_per_sample) {
        bs->write(bs, 1, 1);
        bs->write_unary(bs, 1, wasted_bits_per_sample - 1);
    } else
        bs->write(bs, 1, 0);

    /*write subframe samples*/
    for (i = 0; i < samples->len; i++) {
        bs->write_signed(bs, bits_per_sample - wasted_bits_per_sample,
                         samples->_[i]);
    }
}

void
flacenc_write_fixed_subframe(BitstreamWriter* bs,
                             struct flac_context* encoder,
                             unsigned bits_per_sample,
                             unsigned wasted_bits_per_sample,
                             const a_int* samples)
{
    aa_int* fixed_subframe_orders = encoder->fixed_subframe_orders;
    a_int* order;
    l_int* truncated_order = encoder->truncated_order;

    uint64_t best_order_abs_sum;
    unsigned best_order;
    uint64_t order_abs_sum;
    unsigned i;

    fixed_subframe_orders->reset(fixed_subframe_orders);
    order = fixed_subframe_orders->append(fixed_subframe_orders);
    order->extend(order, samples);  /*order 0*/
    order->link(order, truncated_order);

    truncated_order->de_head(truncated_order, 4, truncated_order);
    best_order_abs_sum = flacenc_abs_sum(truncated_order);
    best_order = 0;

    if (samples->len > 4) {
        for (i = 0; i < MAX_FIXED_ORDER; i++) {
            /*orders 1 - 4*/
            order = fixed_subframe_orders->append(fixed_subframe_orders);
            flacenc_next_fixed_order(fixed_subframe_orders->_[i], order);
            order->link(order, truncated_order);
            truncated_order->de_head(truncated_order, 4 - (i + 1),
                                     truncated_order);
            order_abs_sum = flacenc_abs_sum(truncated_order);
            if (order_abs_sum < best_order_abs_sum) {
                best_order_abs_sum = order_abs_sum;
                best_order = i + 1;
            }
        }
    }

    bs->write(bs, 1, 0);               /*pad*/
    bs->write(bs, 3, 1);               /*FIXED subframe type*/
    bs->write(bs, 3, best_order);      /*FIXED subframe order*/
    if (wasted_bits_per_sample > 0) {  /*wasted bits-per-sample*/
        bs->write(bs, 1, 1);
        bs->write_unary(bs, 1, wasted_bits_per_sample - 1);
    } else {
        bs->write(bs, 1, 0);
    }

    for (i = 0; i < best_order; i++)   /*warm-up samples*/
        bs->write_signed(bs, bits_per_sample - wasted_bits_per_sample,
                         samples->_[i]);

    flacenc_encode_residuals(bs,
                             encoder,
                             samples->len,
                             best_order,
                             encoder->fixed_subframe_orders->_[best_order]);
}

void
flacenc_next_fixed_order(const a_int* order, a_int* next_order)
{
    unsigned i;
    unsigned order_size = order->len;
    int* order_data = order->_;

    assert(order_size > 1);
    next_order->reset_for(next_order, order_size - 1);
    for (i = 1; i < order_size; i++) {
        a_append(next_order, order_data[i] - order_data[i - 1]);
    }
}

void
flacenc_write_lpc_subframe(BitstreamWriter* bs,
                           struct flac_context* encoder,
                           unsigned bits_per_sample,
                           unsigned wasted_bits_per_sample,
                           const a_int* samples)
{
    a_double* windowed_signal = encoder->windowed_signal;
    a_double* autocorrelation_values = encoder->autocorrelation_values;
    aa_double* lp_coefficients = encoder->lp_coefficients;
    a_double* lp_error = encoder->lp_error;
    a_int* qlp_coefficients = encoder->qlp_coefficients;
    int qlp_shift_needed;

    if (samples->len <= (encoder->options.max_lpc_order + 1)) {
        /*not enough samples, so built LPC subframe with dummy coeffs*/
        qlp_coefficients->vset(qlp_coefficients, 1, 1);
        flacenc_encode_lpc_subframe(bs,
                                    encoder,
                                    bits_per_sample,
                                    wasted_bits_per_sample,
                                    2,
                                    0,
                                    qlp_coefficients,
                                    samples);
        return;
    }

    /*window signal*/
    flacenc_window_signal(encoder, samples, windowed_signal);

    /*transform windowed signal to autocorrelation values*/
    flacenc_autocorrelate(encoder->options.max_lpc_order,
                          windowed_signal,
                          autocorrelation_values);

    /*compute LP coefficients from autocorrelation values*/
    flacenc_compute_lp_coefficients(encoder->options.max_lpc_order,
                                    autocorrelation_values,
                                    lp_coefficients,
                                    lp_error);

    if (!encoder->options.exhaustive_model_search) {
        /*if not performing an exhaustive model search,
          estimate which set of LP coefficients is best
          and use those to build subframe*/
        const unsigned best_order =
            flacenc_estimate_best_lpc_order(
                bits_per_sample,
                encoder->options.qlp_coeff_precision,
                encoder->options.max_lpc_order,
                samples->len,
                lp_error);

        flacenc_quantize_coefficients(lp_coefficients,
                                      best_order,
                                      encoder->options.qlp_coeff_precision,
                                      qlp_coefficients,
                                      &qlp_shift_needed);

        flacenc_encode_lpc_subframe(bs,
                                    encoder,
                                    bits_per_sample,
                                    wasted_bits_per_sample,
                                    encoder->options.qlp_coeff_precision,
                                    qlp_shift_needed,
                                    qlp_coefficients,
                                    samples);
    } else {
        /*otherwise, build all possible subframes
          and return the one which is actually the smallest*/
        unsigned best_subframe_size = UINT_MAX;
        BitstreamRecorder *best_subframe = bw_open_recorder(BS_BIG_ENDIAN);
        BitstreamRecorder *subframe = bw_open_recorder(BS_BIG_ENDIAN);
        unsigned order;

        for (order = 1; order <= encoder->options.max_lpc_order; order++) {
            subframe->reset(subframe);

            flacenc_quantize_coefficients(
                lp_coefficients,
                order,
                encoder->options.qlp_coeff_precision,
                qlp_coefficients,
                &qlp_shift_needed);

            flacenc_encode_lpc_subframe((BitstreamWriter*)subframe,
                                        encoder,
                                        bits_per_sample,
                                        wasted_bits_per_sample,
                                        encoder->options.qlp_coeff_precision,
                                        qlp_shift_needed,
                                        qlp_coefficients,
                                        samples);

            if (subframe->bits_written(subframe) < best_subframe_size) {
                best_subframe_size = subframe->bits_written(subframe);
                recorder_swap(&best_subframe, &subframe);
            }
        }

        best_subframe->copy(best_subframe, bs);
        best_subframe->close(best_subframe);
        subframe->close(subframe);
    }
}

void
flacenc_encode_lpc_subframe(BitstreamWriter* bs,
                            struct flac_context* encoder,
                            unsigned bits_per_sample,
                            unsigned wasted_bits_per_sample,
                            unsigned qlp_precision,
                            unsigned qlp_shift_needed,
                            const a_int* qlp_coefficients,
                            const a_int* samples)
{
    a_int* lpc_residual = encoder->lpc_residual;
    const unsigned order = qlp_coefficients->len;
    unsigned i;

    assert(order > 0);

    bs->write(bs, 1, 0);               /*pad*/
    bs->write(bs, 1, 1);               /*subframe type*/
    bs->write(bs, 5, order - 1);       /*subframe order*/
    if (wasted_bits_per_sample > 0) {  /*wasted bits-per-sample*/
        bs->write(bs, 1, 1);
        bs->write_unary(bs, 1, wasted_bits_per_sample - 1);
    } else {
        bs->write(bs, 1, 0);
    }

    for (i = 0; i < order; i++)        /*warm-up samples*/
        bs->write_signed(bs, bits_per_sample - wasted_bits_per_sample,
                         samples->_[i]);

    bs->write(bs, 4, qlp_precision - 1);
    bs->write_signed(bs, 5, qlp_shift_needed);

    for (i = 0; i < order; i++)        /*QLP coefficients*/
        bs->write_signed(bs, qlp_precision, qlp_coefficients->_[i]);

    /*calculate signed residuals*/
    lpc_residual->reset_for(lpc_residual, samples->len - order);
    for (i = 0; i < samples->len - order; i++) {
        int64_t accumulator = 0;
        unsigned j;
        for (j = 0; j < order; j++)
            accumulator += ((int64_t)qlp_coefficients->_[j] *
                            (int64_t)samples->_[i + order - j - 1]);
        accumulator >>= qlp_shift_needed;
        a_append(lpc_residual,
                 samples->_[i + order] - (int)accumulator);
    }

    /*write residual block*/
    flacenc_encode_residuals(bs,
                             encoder,
                             samples->len,
                             order,
                             lpc_residual);
}


void
flacenc_window_signal(struct flac_context* encoder,
                      const a_int* samples,
                      a_double* windowed_signal)
{
    a_double* tukey_window = encoder->tukey_window;
    const unsigned N = samples->len;
    const double alpha = 0.5;
    unsigned n;

    if (tukey_window->len != samples->len) {
        const unsigned window1 = (unsigned)(alpha * (N - 1)) / 2;
        const unsigned window2 = (unsigned)((N - 1) * (1.0 - (alpha / 2.0)));

        tukey_window->reset_for(tukey_window, samples->len);

        for (n = 0; n < N; n++) {
            if (n <= window1) {
                a_append(tukey_window,
                         0.5 *
                         (1.0 +
                          cos(M_PI * (((2 * n) / (alpha * (N - 1))) - 1.0))));
            } else if (n <= window2) {
                a_append(tukey_window, 1.0);
            } else {
                a_append(tukey_window,
                         0.5 *
                         (1.0 +
                          cos(M_PI * (((2.0 * n) / (alpha * (N - 1))) -
                                      (2.0 / alpha) + 1.0))));
            }
        }
    }

    windowed_signal->reset_for(windowed_signal, samples->len);
    for (n = 0; n < N; n++) {
        a_append(windowed_signal, samples->_[n] * tukey_window->_[n]);
    }
}

void
flacenc_autocorrelate(unsigned max_lpc_order,
                      const a_double* windowed_signal,
                      a_double* autocorrelation_values)
{
    unsigned lag;

    autocorrelation_values->reset(autocorrelation_values);

    for (lag = 0; lag <= max_lpc_order; lag++) {
        double accumulator = 0.0;
        unsigned i;

        assert((windowed_signal->len - lag) > 0);
        for (i = 0; i < windowed_signal->len - lag; i++)
            accumulator += (windowed_signal->_[i] *
                            windowed_signal->_[i + lag]);
        autocorrelation_values->append(autocorrelation_values, accumulator);
    }
}

void
flacenc_compute_lp_coefficients(unsigned max_lpc_order,
                                const a_double* autocorrelation_values,
                                aa_double* lp_coefficients,
                                a_double* lp_error)
{
    unsigned i;
    a_double* lp_coeff;
    double k;

    assert(autocorrelation_values->len == (max_lpc_order + 1));

    lp_coefficients->reset(lp_coefficients);
    lp_error->reset(lp_error);

    k = autocorrelation_values->_[1] / autocorrelation_values->_[0];
    lp_coeff = lp_coefficients->append(lp_coefficients);
    lp_coeff->append(lp_coeff, k);
    lp_error->append(lp_error,
                     autocorrelation_values->_[0] * (1.0 - (k * k)));

    for (i = 1; i < max_lpc_order; i++) {
        double q = autocorrelation_values->_[i + 1];
        unsigned j;

        for (j = 0; j < i; j++)
            q -= (lp_coefficients->_[i - 1]->_[j] *
                  autocorrelation_values->_[i - j]);

        k = q / lp_error->_[i - 1];

        lp_coeff = lp_coefficients->append(lp_coefficients);
        for (j = 0; j < i; j++) {
            lp_coeff->append(lp_coeff,
                             lp_coefficients->_[i - 1]->_[j] -
                             (k * lp_coefficients->_[i - 1]->_[i - j - 1]));
        }
        lp_coeff->append(lp_coeff, k);

        lp_error->append(lp_error, lp_error->_[i - 1] * (1.0 - (k * k)));
    }
}

unsigned
flacenc_estimate_best_lpc_order(unsigned bits_per_sample,
                                unsigned qlp_precision,
                                unsigned max_lpc_order,
                                unsigned block_size,
                                const a_double* lp_error)
{
    const double error_scale = (M_LN2 * M_LN2) / ((double)block_size * 2.0);
    unsigned best_order = 0;
    double best_subframe_bits = DBL_MAX;
    unsigned i;

    assert(block_size > 0);

    for (i = 0; i < max_lpc_order; i++) {
        const unsigned order = i + 1;
        if (lp_error->_[i] > 0.0) {
            const unsigned header_bits =
                order * (bits_per_sample + qlp_precision);
            const double bits_per_residual =
                MAX(log(lp_error->_[i] * error_scale) / (M_LN2 * 2), 0.0);
            const double estimated_subframe_bits =
                (header_bits + bits_per_residual * (block_size - order));

            if (estimated_subframe_bits < best_subframe_bits) {
                best_order = order;
                best_subframe_bits = estimated_subframe_bits;
            }
        } else {
            return order;
        }
    }

    assert(best_order > 0);
    return best_order;
}

void
flacenc_quantize_coefficients(const aa_double* lp_coefficients,
                              unsigned order,
                              unsigned qlp_precision,

                              a_int* qlp_coefficients,
                              int* qlp_shift_needed)
{
    a_double* lp_coeffs = lp_coefficients->_[order - 1];
    double l = DBL_MIN;
    int log2cmax;
    unsigned i;
    int qlp_max;
    int qlp_min;
    double error;
    int error_i;

    assert(lp_coeffs->len == order);

    qlp_coefficients->reset(qlp_coefficients);

    for (i = 0; i < lp_coeffs->len; i++)
        l = MAX(fabs(lp_coeffs->_[i]), l);

    frexp(l, &log2cmax);

    *qlp_shift_needed = (int)(qlp_precision - 1) - (log2cmax - 1) - 1;
    *qlp_shift_needed = MAX(*qlp_shift_needed, -(1 << 4));
    *qlp_shift_needed = MIN(*qlp_shift_needed, (1 << 4) - 1);

    qlp_max = (1 << (qlp_precision - 1)) - 1;
    qlp_min = -(1 << (qlp_precision - 1));

    error = 0.0;

    if (*qlp_shift_needed >= 0) {
        for (i = 0; i < order; i++) {
            error += (lp_coeffs->_[i] * (1 << *qlp_shift_needed));
            error_i = (int)round(error);
            qlp_coefficients->append(qlp_coefficients,
                                     MIN(MAX(error_i, qlp_min), qlp_max));
            error -= (double)error_i;
        }
    } else {
        /*negative shifts are not allowed, so shrink coefficients*/
        for (i = 0; i < order; i++) {
            error += (lp_coeffs->_[i] / (1 << -(*qlp_shift_needed)));
            error_i = (int)round(error);
            qlp_coefficients->append(qlp_coefficients,
                                     MIN(MAX(error_i, qlp_min), qlp_max));
            error -= (double)error_i;
        }
        *qlp_shift_needed = 0;
    }
}

void
flacenc_encode_residuals(BitstreamWriter* bs,
                         struct flac_context* encoder,
                         unsigned block_size,
                         unsigned predictor_order,
                         const a_int* residuals)
{
    unsigned coding_method;
    unsigned partition_order;
    unsigned best_partition_order = 0;
    unsigned p;

    /*local links to the cached arrays*/

    uint64_t total_size;
    a_int* rice_parameters = encoder->rice_parameters;
    al_int* residual_partitions = encoder->residual_partitions;

    uint64_t best_total_size = ULLONG_MAX;
    a_int* best_rice_parameters = encoder->best_rice_parameters;
    al_int* best_residual_partitions = encoder->best_residual_partitions;


    l_int* remaining_residuals = encoder->remaining_residuals;

    void (*write)(struct BitstreamWriter_s* bs,
                  unsigned int count,
                  unsigned int value) = bs->write;

    void (*write_unary)(struct BitstreamWriter_s* bs,
                        int stop_bit,
                        unsigned int value) = bs->write_unary;

    rice_parameters->reset(rice_parameters);
    best_rice_parameters->reset(best_rice_parameters);

    for (partition_order = 0;
         partition_order <= encoder->options.max_residual_partition_order;
         partition_order++) {
        if ((block_size % (1 << partition_order)) == 0) {
            residuals->link(residuals, remaining_residuals);
            flacenc_encode_residual_partitions(
                remaining_residuals,
                block_size,
                predictor_order,
                partition_order,
                encoder->options.max_rice_parameter,

                rice_parameters,
                residual_partitions,
                &total_size);

            if (total_size < best_total_size) {
                best_partition_order = partition_order;

                rice_parameters->swap(rice_parameters,
                                      best_rice_parameters);

                residual_partitions->swap(residual_partitions,
                                          best_residual_partitions);

                best_total_size = total_size;
            }
        } else {
            /*stop once block_size is no longer equally divisible by
              2 ^ partition_order*/
            break;
        }
    }

    assert(remaining_residuals->len == 0);
    assert(best_rice_parameters->len == best_residual_partitions->len);

    if (best_rice_parameters->max(best_rice_parameters) > 14)
        coding_method = 1;
    else
        coding_method = 0;

    /* output best Rice parameters and residual partitions to disk */

    bs->write(bs, 2, coding_method);
    bs->write(bs, 4, best_partition_order);

    for (p = 0; p < best_residual_partitions->len; p++) {
        unsigned rice_parameter = (unsigned)(best_rice_parameters->_[p]);
        const int* partition_ = best_residual_partitions->_[p]->_;
        const unsigned partition_len = best_residual_partitions->_[p]->len;
        unsigned i;

        if (coding_method == 0)
            write(bs, 4, rice_parameter);
        else
            write(bs, 5, rice_parameter);

        for (i = 0; i < partition_len; i++) {
            register unsigned u;
            register unsigned MSB;
            register unsigned LSB;
            if (partition_[i] >= 0) {
                u = partition_[i] << 1;
            } else {
                u = ((-partition_[i] - 1) << 1) | 1;
            }
            MSB = u >> rice_parameter;
            LSB = u - (MSB << rice_parameter);
            write_unary(bs, 1, MSB);
            write(bs, rice_parameter, LSB);
        }
    }
}

void
flacenc_encode_residual_partitions(l_int* residuals,
                                   unsigned block_size,
                                   unsigned predictor_order,
                                   unsigned partition_order,
                                   unsigned maximum_rice_parameter,

                                   a_int* rice_parameters,
                                   al_int* partitions,
                                   uint64_t* total_size)
{
    unsigned p;

    *total_size = 0;
    rice_parameters->reset(rice_parameters);
    partitions->reset(partitions);

    for (p = 0; p < (1 << partition_order); p++) {
        l_int* partition = partitions->append(partitions);
        unsigned plength;
        uint64_t abs_partition_sum = 0;
        unsigned i;
        unsigned Rice;

        if (p == 0) {
            plength = (block_size >> partition_order) - predictor_order;
        } else {
            plength = block_size >> partition_order;
        }

        residuals->split(residuals, plength, partition, residuals);

        for (i = 0; i < partition->len; i++) {
            if (partition->_[i] >= 0)
                abs_partition_sum += partition->_[i];
            else
                abs_partition_sum -= partition->_[i];
        }

        /*compute best Rice parameter for partition*/
        Rice = 0;
        while ((uint64_t)(plength << Rice) < abs_partition_sum) {
            if (Rice < maximum_rice_parameter) {
                Rice++;
            } else {
                break;
            }
        }

        /*add estimated size of partition to total size*/
        if (Rice > 0) {
            *total_size += (4 + /*4 bit partition header*/
                            /*residual MSBs minus sign bit*/
                            (abs_partition_sum >> (Rice - 1)) +
                            /*residual LSBs plus stop bit*/
                            ((1 + Rice) * plength) -
                            (plength / 2));
        } else {
            *total_size += (4 + /*4 bit partition header*/
                            /*residual MSBs minus sign bit*/
                            (abs_partition_sum << 1) +
                            /*residual LSBs plus stop bit*/
                            plength -
                            (plength / 2));
        }

        rice_parameters->append(rice_parameters, (int)Rice);
    }
}

void
flacenc_average_difference(const aa_int* samples,
                           a_int* average,
                           a_int* difference)
{
    int* channel0;
    int* channel1;
    unsigned sample_count = samples->_[0]->len;
    unsigned i;

    assert(samples->_[0]->len == samples->_[1]->len);

    average->reset_for(average, sample_count);
    difference->reset_for(difference, sample_count);

    channel0 = samples->_[0]->_;
    channel1 = samples->_[1]->_;

    for (i = 0; i < sample_count; i++) {
        a_append(average, (channel0[i] + channel1[i]) >> 1);
        a_append(difference, channel0[i] - channel1[i]);
    }
}

void
write_utf8(BitstreamWriter* bs, unsigned int value) {
    if (value <= 0x7F) {
        /*1 byte only*/
        bs->write(bs, 8, value);
    } else {
        unsigned int total_bytes = 0;
        int shift;

        /*more than 1 byte*/

        if (value <= 0x7FF) {
            total_bytes = 2;
        } else if (value <= 0xFFFF) {
            total_bytes = 3;
        } else if (value <= 0x1FFFFF) {
            total_bytes = 4;
        } else if (value <= 0x3FFFFFF) {
            total_bytes = 5;
        } else if (value <= 0x7FFFFFFF) {
            total_bytes = 6;
        }

        shift = (total_bytes - 1) * 6;
        /*send out the initial unary + leftover most-significant bits*/
        bs->write_unary(bs, 0, total_bytes);
        bs->write(bs, 7 - total_bytes, value >> shift);

        /*then send the least-significant bits,
          6 at a time with a unary 1 value appended*/
        for (shift -= 6; shift >= 0; shift -= 6) {
            bs->write_unary(bs, 0, 1);
            bs->write(bs, 6, (value >> shift) & 0x3F);
        }
    }
}



void
md5_update(void *data, unsigned char *buffer, unsigned long len)
{
    audiotools__MD5Update((audiotools__MD5Context*)data,
                          (const void*)buffer,
                          len);
}

unsigned
flacenc_max_wasted_bits_per_sample(const a_int* samples)
{
    unsigned i;
    unsigned wasted_bits_per_sample = INT_MAX;

    for (i = 0; i < samples->len; i++) {
        unsigned wasted_bits;
        int sample = samples->_[i];
        if (sample != 0) {
            for (wasted_bits = 0;
                 ((sample & 1) == 0) && (sample != 0);
                 sample >>= 1)
                wasted_bits++;
            wasted_bits_per_sample = MIN(wasted_bits_per_sample,
                                         wasted_bits);
            if (wasted_bits_per_sample == 0)
                return 0;
        }
    }

    if (wasted_bits_per_sample == INT_MAX) {
        return 0;
    } else {
        return wasted_bits_per_sample;
    }
}

int
flacenc_all_identical(const a_int* samples)
{
    if (samples->len > 1) {
        const int first = samples->_[0];
        unsigned i;
        for (i = 1; i < samples->len; i++)
            if (samples->_[i] != first)
                return 0;

        return 1;
    } else {
        return 1;
    }
}

uint64_t
flacenc_abs_sum(const l_int* data)
{
    register uint64_t accumulator = 0;
    unsigned i;
    for (i = 0; i < data->len; i++)
        accumulator += abs(data->_[i]);

    return accumulator;
}

#ifdef STANDALONE
#include <getopt.h>
#include <errno.h>

int main(int argc, char *argv[]) {
    char* output_file = NULL;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;

    unsigned block_size = 4096;
    unsigned max_lpc_order = 12;
    unsigned min_partition_order = 0;
    unsigned max_partition_order = 6;
    int mid_side = 0;
    int adaptive_mid_side = 0;
    int exhaustive_model_search = 0;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"block-size",              required_argument, NULL, 'B'},
        {"max-lpc-order",           required_argument, NULL, 'l'},
        {"min-partition-order",     required_argument, NULL, 'P'},
        {"max-partition-order",     required_argument, NULL, 'R'},
        {"mid-side",                no_argument,       NULL, 'm'},
        {"adaptive-mid-side",       no_argument,       NULL, 'M'},
        {"exhaustive-model-search", no_argument,       NULL, 'e'},
        {NULL,                      no_argument,       NULL,  0}
    };
    const static char* short_opts = "-hc:r:b:B:l:P:R:mMe";

    while ((c = getopt_long(argc,
                            argv,
                            short_opts,
                            long_opts,
                            NULL)) != -1) {
        switch (c) {
        case 1:
            if (output_file == NULL) {
                output_file = optarg;
            } else {
                printf("only one output file allowed\n");
                return 1;
            }
            break;
        case 'c':
            if (((channels = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --channel \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'r':
            if (((sample_rate = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --sample-rate \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'b':
            if (((bits_per_sample = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --bits-per-sample \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'B':
            if (((block_size = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --block-size \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'l':
            if (((max_lpc_order = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --max-lpc-order \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'P':
            if (((min_partition_order =
                  strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --min-partition-order \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'R':
            if (((max_partition_order =
                  strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --max-partition-order \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'm':
            mid_side = 1;
            break;
        case 'M':
            adaptive_mid_side = 1;
            break;
        case 'e':
            exhaustive_model_search = 1;
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: flacenc [options] <output.flac>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("\n");
            printf("-B, --block-size=#              block size\n");
            printf("-l, --max-lpc-order=#           maximum LPC order\n");
            printf("-P, --min-partition-order=#     minimum partition order\n");
            printf("-R, --max-partition-order=#     maximum partition order\n");
            printf("-m, --mid-side                  use mid-side encoding\n");
            printf("-M, --adaptive-mid-side         "
                   "use adaptive mid-side encoding\n");
            printf("-m, --mid-side                  use mid-side encoding\n");
            printf("-e, --exhaustive-model-search   "
                   "search for best subframe exhaustively\n");
            return 0;
        default:
            break;
        }
    }
    if (output_file == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    }

    assert((channels > 0) && (channels <= 8));
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16) ||
           (bits_per_sample == 24));
    assert(sample_rate > 0);

    printf("Encoding from stdin using parameters:\n");
    printf("channels        %u\n", channels);
    printf("sample rate     %u\n", sample_rate);
    printf("bits per sample %u\n", bits_per_sample);
    printf("little-endian, signed samples\n");
    printf("\n");
    printf("block size              %u\n", block_size);
    printf("max LPC order           %u\n", max_lpc_order);
    printf("min partition order     %u\n", min_partition_order);
    printf("max partition order     %u\n", max_partition_order);
    printf("mid side                %d\n", mid_side);
    printf("adaptive mid side       %d\n", adaptive_mid_side);
    printf("exhaustive model search %d\n", exhaustive_model_search);

    if (encoders_encode_flac(output_file,
                             open_pcmreader(stdin,
                                            sample_rate,
                                            channels,
                                            0,
                                            bits_per_sample,
                                            0,
                                            1),
                             block_size,
                             max_lpc_order,
                             min_partition_order,
                             max_partition_order,
                             mid_side,
                             adaptive_mid_side,
                             exhaustive_model_search)) {
        return 0;
    } else {
        fprintf(stderr, "*** Error encoding FLAC file \"%s\"\n", output_file);
        return 1;
    }
}
#endif
