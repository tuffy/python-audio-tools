#include "alac.h"
#include "../pcmconv.h"
#include <assert.h>
#include <math.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

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

#define MAX_LPC_ORDER 8
#define INTERLACING_SHIFT 2

#ifndef STANDALONE

PyObject*
encoders_encode_alac(PyObject *dummy, PyObject *args, PyObject *keywds)
{

    static char *kwlist[] = {"file",
                             "pcmreader",
                             "block_size",
                             "initial_history",
                             "history_multiplier",
                             "maximum_k",
                             "minimum_interlacing_leftweight",
                             "maximum_interlacing_leftweight",
                             NULL};

    PyObject *file_obj;
    FILE *output_file;
    BitstreamWriter *output = NULL;
    pcmreader* pcmreader;
    struct alac_context encoder;
    array_ia* channels = array_ia_new();
    unsigned frame_file_offset;

    PyObject *log_output;

    init_encoder(&encoder);

    encoder.options.minimum_interlacing_leftweight = 0;
    encoder.options.maximum_interlacing_leftweight = 4;

    /*extract a file object, PCMReader-compatible object and encoding options*/
    if (!PyArg_ParseTupleAndKeywords(
                    args, keywds, "OO&iiii|ii",
                    kwlist,
                    &file_obj,
                    pcmreader_converter,
                    &pcmreader,
                    &(encoder.options.block_size),
                    &(encoder.options.initial_history),
                    &(encoder.options.history_multiplier),
                    &(encoder.options.maximum_k),
                    &(encoder.options.minimum_interlacing_leftweight),
                    &(encoder.options.maximum_interlacing_leftweight)))
        return NULL;

    encoder.bits_per_sample = pcmreader->bits_per_sample;

    /*determine if the PCMReader is compatible with ALAC*/
    if ((pcmreader->bits_per_sample != 16) &&
        (pcmreader->bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 16 or 24");
        goto error;
    }

    /*convert file object to bitstream writer*/
    if ((output_file = PyFile_AsFile(file_obj)) == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "file must by a concrete file object");
        goto error;
    } else {
        output = bw_open(output_file, BS_BIG_ENDIAN);
        bw_add_callback(output,
                        byte_counter,
                        &(encoder.mdat_byte_size));
    }

#else

int
ALACEncoder_encode_alac(char *filename,
                        pcmreader* pcmreader,
                        int block_size,
                        int initial_history,
                        int history_multiplier,
                        int maximum_k)
{
    FILE *output_file;
    BitstreamWriter *output = NULL;
    struct alac_context encoder;
    array_ia* channels = array_ia_new();
    unsigned frame_file_offset;

    init_encoder(&encoder);

    encoder.options.block_size = block_size;
    encoder.options.initial_history = initial_history;
    encoder.options.history_multiplier = history_multiplier;
    encoder.options.maximum_k = maximum_k;
    encoder.options.minimum_interlacing_leftweight = 0;
    encoder.options.maximum_interlacing_leftweight = 4;

    /*FIXME - make sure this opens correctly*/
    output_file = fopen(filename, "wb");
    encoder.bits_per_sample = pcmreader->bits_per_sample;

    /*convert file object to bitstream writer*/
    output = bw_open(output_file, BS_BIG_ENDIAN);
    bw_add_callback(output,
                    byte_counter,
                    &(encoder.mdat_byte_size));
#endif

    /*write placeholder mdat header*/
    output->write(output, 32, 0);
    output->write_bytes(output, (uint8_t*)"mdat", 4);

    /*write frames from pcm_reader until empty*/
    if (pcmreader->read(pcmreader, encoder.options.block_size, channels))
        goto error;
    while (channels->_[0]->len > 0) {
#ifndef STANDALONE
        Py_BEGIN_ALLOW_THREADS
#endif
        /*log the number of PCM frames in each ALAC frameset*/
        encoder.frame_log->_[LOG_SAMPLE_SIZE]->append(
            encoder.frame_log->_[LOG_SAMPLE_SIZE],
            channels->_[0]->len);

        frame_file_offset = encoder.mdat_byte_size;

        /*log each frameset's starting offset in the mdat atom*/
        encoder.frame_log->_[LOG_FILE_OFFSET]->append(
            encoder.frame_log->_[LOG_FILE_OFFSET],
            frame_file_offset);

        write_frameset(output, &encoder, channels);

        /*log each frame's total size in bytes*/
        encoder.frame_log->_[LOG_BYTE_SIZE]->append(
            encoder.frame_log->_[LOG_BYTE_SIZE],
            encoder.mdat_byte_size - frame_file_offset);

#ifndef STANDALONE
        Py_END_ALLOW_THREADS
#endif

        if (pcmreader->read(pcmreader, encoder.options.block_size, channels))
            goto error;
    }

    /*return to header and rewrite it with the actual value*/
    bw_pop_callback(output, NULL);
    fseek(output_file, 0, 0);
    output->write(output, 32, encoder.mdat_byte_size);

    /*close and free allocated files/buffers,
      which varies depending on whether we're running standlone or not*/

#ifndef STANDALONE

    log_output = alac_log_output(&encoder);

    pcmreader->del(pcmreader);
    output->free(output);
    free_encoder(&encoder);
    channels->del(channels);

    return log_output;

 error:

    pcmreader->del(pcmreader);
    output->free(output);
    free_encoder(&encoder);
    channels->del(channels);

    return NULL;
}
#else

    pcmreader->del(pcmreader);
    output->close(output);
    free_encoder(&encoder);
    channels->del(channels);

    return 0;
 error:
    pcmreader->del(pcmreader);
    output->close(output);
    free_encoder(&encoder);
    channels->del(channels);

    return 1;
}
#endif

static void
init_encoder(struct alac_context* encoder)
{
    encoder->frame_byte_size = 0;
    encoder->mdat_byte_size = 0;

    encoder->frame_log = array_ia_new();
    encoder->frame_log->append(encoder->frame_log); /*LOG_SAMPLE_SIZE*/
    encoder->frame_log->append(encoder->frame_log); /*LOG_BYTE_SIZE*/
    encoder->frame_log->append(encoder->frame_log); /*LOG_FILE_OFFSET*/

    encoder->LSBs = array_i_new();
    encoder->channels_MSB = array_ia_new();

    encoder->correlated_channels = array_ia_new();
    encoder->qlp_coefficients0 = array_i_new();
    encoder->qlp_coefficients1 = array_i_new();
    encoder->residual0 = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->residual1 = bw_open_recorder(BS_BIG_ENDIAN);

    encoder->tukey_window = array_f_new();
    encoder->windowed_signal = array_f_new();
    encoder->autocorrelation_values = array_f_new();
    encoder->lp_coefficients = array_fa_new();
    encoder->qlp_coefficients4 = array_i_new();
    encoder->qlp_coefficients8 = array_i_new();
    encoder->residual_values4 = array_i_new();
    encoder->residual_values8 = array_i_new();
    encoder->residual_block4 = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->residual_block8 = bw_open_recorder(BS_BIG_ENDIAN);

    encoder->compressed_frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->interlaced_frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->best_interlaced_frame = bw_open_recorder(BS_BIG_ENDIAN);
}

static void
free_encoder(struct alac_context* encoder)
{
    encoder->frame_log->del(encoder->frame_log);

    encoder->LSBs->del(encoder->LSBs);
    encoder->channels_MSB->del(encoder->channels_MSB);

    encoder->correlated_channels->del(encoder->correlated_channels);
    encoder->qlp_coefficients0->del(encoder->qlp_coefficients0);
    encoder->qlp_coefficients1->del(encoder->qlp_coefficients1);
    encoder->residual0->close(encoder->residual0);
    encoder->residual1->close(encoder->residual1);

    encoder->tukey_window->del(encoder->tukey_window);
    encoder->windowed_signal->del(encoder->windowed_signal);
    encoder->autocorrelation_values->del(encoder->autocorrelation_values);
    encoder->lp_coefficients->del(encoder->lp_coefficients);
    encoder->qlp_coefficients4->del(encoder->qlp_coefficients4);
    encoder->qlp_coefficients8->del(encoder->qlp_coefficients8);
    encoder->residual_values4->del(encoder->residual_values4);
    encoder->residual_values8->del(encoder->residual_values8);
    encoder->residual_block4->close(encoder->residual_block4);
    encoder->residual_block8->close(encoder->residual_block8);

    encoder->compressed_frame->close(encoder->compressed_frame);
    encoder->interlaced_frame->close(encoder->interlaced_frame);
    encoder->best_interlaced_frame->close(encoder->best_interlaced_frame);
}

static inline array_ia*
extract_1ch(array_ia* frameset, unsigned channel, array_ia* pair)
{
    pair->reset(pair);
    frameset->_[channel]->swap(frameset->_[channel],
                               pair->append(pair));
    return pair;
}

static inline array_ia*
extract_2ch(array_ia* frameset, unsigned channel0, unsigned channel1,
            array_ia* pair)
{
    pair->reset(pair);
    frameset->_[channel0]->swap(frameset->_[channel0],
                                pair->append(pair));
    frameset->_[channel1]->swap(frameset->_[channel1],
                                pair->append(pair));
    return pair;
}


static void
write_frameset(BitstreamWriter *bs,
               struct alac_context* encoder,
               array_ia* channels)
{
    array_ia* channel_pair = array_ia_new();
    unsigned i;

    switch (channels->len) {
    case 1:
    case 2:
        write_frame(bs, encoder, channels);
        break;
    case 3:
        write_frame(bs, encoder,
                    extract_1ch(channels, 2, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 0, 1, channel_pair));
        break;
    case 4:
        write_frame(bs, encoder,
                    extract_1ch(channels, 2, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 0, 1, channel_pair));
        write_frame(bs, encoder,
                    extract_1ch(channels, 3, channel_pair));
        break;
    case 5:
        write_frame(bs, encoder,
                    extract_1ch(channels, 2, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 0, 1, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 3, 4, channel_pair));
        break;
    case 6:
        write_frame(bs, encoder,
                    extract_1ch(channels, 2, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 0, 1, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 4, 5, channel_pair));
        write_frame(bs, encoder,
                    extract_1ch(channels, 3, channel_pair));
        break;
    case 7:
        write_frame(bs, encoder,
                    extract_1ch(channels, 2, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 0, 1, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 4, 5, channel_pair));
        write_frame(bs, encoder,
                    extract_1ch(channels, 6, channel_pair));
        write_frame(bs, encoder,
                    extract_1ch(channels, 3, channel_pair));
        break;
    case 8:
        write_frame(bs, encoder,
                    extract_1ch(channels, 2, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 6, 7, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 0, 1, channel_pair));
        write_frame(bs, encoder,
                    extract_2ch(channels, 4, 5, channel_pair));
        write_frame(bs, encoder,
                    extract_1ch(channels, 3, channel_pair));
        break;
    default:
        for (i = 0; i < channels->len; i++) {
            write_frame(bs, encoder,
                        extract_1ch(channels, i, channel_pair));
        }
        break;
    }

    bs->write(bs, 3, 7);  /*write the trailing '111' bits*/
    bs->byte_align(bs);   /*and byte-align frameset*/
    channel_pair->del(channel_pair);
}

static void
write_frame(BitstreamWriter *bs,
            struct alac_context* encoder,
            const array_ia* channels)
{
    BitstreamWriter *compressed_frame;

    assert((channels->len == 1) || (channels->len == 2));

    bs->write(bs, 3, channels->len - 1);

    if ((channels->_[0]->len >= 10)) {
        compressed_frame = encoder->compressed_frame;
        bw_reset_recorder(compressed_frame);
        if (!setjmp(encoder->residual_overflow)) {
            write_compressed_frame(compressed_frame,
                                   encoder,
                                   channels);
            bw_rec_copy(bs, compressed_frame);
        } else {
            /*a residual overflow exception occurred,
              so write an uncompressed frame instead*/
            write_uncompressed_frame(bs, encoder, channels);
        }
    } else {
        return write_uncompressed_frame(bs, encoder, channels);
    }
}

static void
write_uncompressed_frame(BitstreamWriter *bs,
                         struct alac_context* encoder,
                         const array_ia* channels)
{
    unsigned i;
    unsigned c;

    bs->write(bs, 16, 0);  /*unused*/

    if (channels->_[0]->len == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, 0);  /*no uncompressed LSBs*/
    bs->write(bs, 1, 1);  /*not compressed*/

    if (channels->_[0]->len != encoder->options.block_size)
        bs->write(bs, 32, channels->_[0]->len);

    for (i = 0; i < channels->_[0]->len; i++) {
        for (c = 0; c < channels->len; c++) {
            bs->write_signed(bs,
                             encoder->bits_per_sample,
                             channels->_[c]->_[i]);
        }
    }
}

static void
write_compressed_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       const array_ia* channels)
{
    unsigned uncompressed_LSBs;
    array_i* LSBs;
    array_ia* channels_MSB;
    unsigned i;
    unsigned c;
    unsigned leftweight;
    BitstreamWriter *interlaced_frame = encoder->interlaced_frame;
    BitstreamWriter *best_interlaced_frame = encoder->best_interlaced_frame;

    if (encoder->bits_per_sample <= 16) {
        /*no uncompressed least-significant bits*/
        uncompressed_LSBs = 0;
        LSBs = NULL;

        if (channels->len == 1) {
            write_non_interlaced_frame(bs,
                                       encoder,
                                       uncompressed_LSBs,
                                       LSBs,
                                       channels);
        } else {
            /*attempt all the interlacing leftweight combinations*/
            bw_maximize_recorder(best_interlaced_frame);

            for (leftweight = encoder->options.minimum_interlacing_leftweight;
                 leftweight <= encoder->options.maximum_interlacing_leftweight;
                 leftweight++) {
                bw_reset_recorder(interlaced_frame);
                write_interlaced_frame(interlaced_frame,
                                       encoder,
                                       0,
                                       LSBs,
                                       INTERLACING_SHIFT,
                                       leftweight,
                                       channels);
                if (interlaced_frame->bits_written(
                        interlaced_frame) <
                    best_interlaced_frame->bits_written(
                        best_interlaced_frame)) {
                    bw_swap_records(interlaced_frame,
                                    best_interlaced_frame);
                }
            }

            /*write the smallest leftweight to disk*/
            bw_rec_copy(bs, best_interlaced_frame);
        }
    } else {
        /*extract uncompressed least-significant bits*/
        uncompressed_LSBs = (encoder->bits_per_sample - 16) / 8;
        LSBs = encoder->LSBs;
        channels_MSB = encoder->channels_MSB;

        LSBs->reset(LSBs);
        channels_MSB->reset(channels_MSB);

        for (c = 0; c < channels->len; c++) {
            channels_MSB->append(channels_MSB);
        }

        for (i = 0; i < channels->_[0]->len; i++) {
            for (c = 0; c < channels->len; c++) {
                LSBs->append(LSBs,
                             channels->_[c]->_[i] &
                             ((1 << (encoder->bits_per_sample - 16)) - 1));
                channels_MSB->_[c]->append(channels_MSB->_[c],
                                              channels->_[c]->_[i] >>
                                              (encoder->bits_per_sample - 16));
            }
        }

        if (channels->len == 1) {
            write_non_interlaced_frame(bs,
                                       encoder,
                                       uncompressed_LSBs,
                                       LSBs,
                                       channels_MSB);
        } else {
            /*attempt all the interlacing leftweight combinations*/
            bw_maximize_recorder(best_interlaced_frame);

            for (leftweight = encoder->options.minimum_interlacing_leftweight;
                 leftweight <= encoder->options.maximum_interlacing_leftweight;
                 leftweight++) {
                bw_reset_recorder(interlaced_frame);
                write_interlaced_frame(interlaced_frame,
                                       encoder,
                                       uncompressed_LSBs,
                                       LSBs,
                                       INTERLACING_SHIFT,
                                       leftweight,
                                       channels_MSB);
                if (interlaced_frame->bits_written(
                        interlaced_frame) <
                    best_interlaced_frame->bits_written(
                        best_interlaced_frame)) {
                    bw_swap_records(interlaced_frame,
                                    best_interlaced_frame);
                }
            }

            /*write the smallest leftweight to disk*/
            bw_rec_copy(bs, best_interlaced_frame);
        }
    }
}

static void
write_non_interlaced_frame(BitstreamWriter *bs,
                           struct alac_context* encoder,
                           unsigned uncompressed_LSBs,
                           const array_i* LSBs,
                           const array_ia* channels)
{
    unsigned i;
    array_i* qlp_coefficients = encoder->qlp_coefficients0;
    BitstreamWriter* residual = encoder->residual0;

    assert(channels->len == 1);
    bw_reset_recorder(residual);

    bs->write(bs, 16, 0);  /*unused*/

    if (channels->_[0]->len == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, uncompressed_LSBs);
    bs->write(bs, 1, 0);   /*is compressed*/

    if (channels->_[0]->len != encoder->options.block_size)
        bs->write(bs, 32, channels->_[0]->len);

    bs->write(bs, 8, 0);   /*no interlacing shift*/
    bs->write(bs, 8, 0);   /*no interlacing leftweight*/

    compute_coefficients(encoder,
                         channels->_[0],
                         (encoder->bits_per_sample -
                          (uncompressed_LSBs * 8)),
                         qlp_coefficients,
                         residual);

    write_subframe_header(bs, qlp_coefficients);

    if (uncompressed_LSBs > 0) {
        for (i = 0; i < LSBs->len; i++) {
            bs->write(bs, uncompressed_LSBs * 8, LSBs->_[i]);
        }
    }

    bw_rec_copy(bs, residual);
}

static void
write_interlaced_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned uncompressed_LSBs,
                       const array_i* LSBs,
                       unsigned interlacing_shift,
                       unsigned interlacing_leftweight,
                       const array_ia* channels)
{
    unsigned i;
    array_i* qlp_coefficients0 = encoder->qlp_coefficients0;
    BitstreamWriter* residual0 = encoder->residual0;
    array_i* qlp_coefficients1 = encoder->qlp_coefficients1;
    BitstreamWriter* residual1 = encoder->residual1;
    array_ia* correlated_channels = encoder->correlated_channels;

    assert(channels->len == 2);
    bw_reset_recorder(residual0);
    bw_reset_recorder(residual1);

    bs->write(bs, 16, 0);  /*unused*/

    if (channels->_[0]->len == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, uncompressed_LSBs);
    bs->write(bs, 1, 0);   /*is compressed*/

    if (channels->_[0]->len != encoder->options.block_size)
        bs->write(bs, 32, channels->_[0]->len);

    bs->write(bs, 8, interlacing_shift);
    bs->write(bs, 8, interlacing_leftweight);

    correlate_channels(channels,
                       interlacing_shift,
                       interlacing_leftweight,
                       correlated_channels);

    compute_coefficients(encoder,
                         correlated_channels->_[0],
                         (encoder->bits_per_sample -
                          (uncompressed_LSBs * 8) + 1),
                         qlp_coefficients0,
                         residual0);

    compute_coefficients(encoder,
                         correlated_channels->_[1],
                         (encoder->bits_per_sample -
                          (uncompressed_LSBs * 8) + 1),
                         qlp_coefficients1,
                         residual1);

    write_subframe_header(bs, qlp_coefficients0);
    write_subframe_header(bs, qlp_coefficients1);

    if (uncompressed_LSBs > 0) {
        for (i = 0; i < LSBs->len; i++) {
            bs->write(bs, uncompressed_LSBs * 8, LSBs->_[i]);
        }
    }

    bw_rec_copy(bs, residual0);
    bw_rec_copy(bs, residual1);
}

static void
correlate_channels(const array_ia* channels,
                   unsigned interlacing_shift,
                   unsigned interlacing_leftweight,
                   array_ia* correlated_channels)
{
    array_i* channel0;
    array_i* channel1;
    array_i* correlated0;
    array_i* correlated1;
    unsigned frame_count;
    unsigned i;
    int64_t leftweight;

    assert(channels->len == 2);
    assert(channels->_[0]->len == channels->_[1]->len);

    frame_count = channels->_[0]->len;
    channel0 = channels->_[0];
    channel1 = channels->_[1];

    correlated_channels->reset(correlated_channels);
    correlated0 = correlated_channels->append(correlated_channels);
    correlated1 = correlated_channels->append(correlated_channels);
    correlated0->resize(correlated0, frame_count);
    correlated1->resize(correlated1, frame_count);

    if (interlacing_leftweight > 0) {
        for (i = 0; i < frame_count; i++) {
            leftweight = channel0->_[i] - channel1->_[i];
            leftweight *= interlacing_leftweight;
            leftweight >>= interlacing_shift;
            a_append(correlated0,
                     channel1->_[i] + (int)leftweight);
            a_append(correlated1,
                     channel0->_[i] - channel1->_[i]);
        }
    } else {
        channel0->copy(channel0, correlated0);
        channel1->copy(channel1, correlated1);
    }
}

static void
compute_coefficients(struct alac_context* encoder,
                     const array_i* samples,
                     unsigned sample_size,
                     array_i* qlp_coefficients,
                     BitstreamWriter *residual)
{
    array_f* windowed_signal = encoder->windowed_signal;
    array_f* autocorrelation_values = encoder->autocorrelation_values;
    array_fa* lp_coefficients = encoder->lp_coefficients;
    array_i* qlp_coefficients4 = encoder->qlp_coefficients4;
    array_i* qlp_coefficients8 = encoder->qlp_coefficients8;
    array_i* residual_values4 = encoder->residual_values4;
    array_i* residual_values8 = encoder->residual_values8;
    BitstreamWriter *residual_block4 = encoder->residual_block4;
    BitstreamWriter *residual_block8 = encoder->residual_block8;

    /*window the input samples*/
    window_signal(encoder,
                  samples,
                  windowed_signal);

    /*compute autocorrelation values for samples*/
    autocorrelate(windowed_signal, autocorrelation_values);

    assert(autocorrelation_values->len == 9);

    if (autocorrelation_values->_[0] != 0.0) {
        /*transform autocorrelation values to lists of LP coefficients*/
        compute_lp_coefficients(autocorrelation_values,
                                lp_coefficients);

        /*quantize LP coefficients at order 4*/
        quantize_coefficients(lp_coefficients, 4, qlp_coefficients4);

        /*quantize LP coefficients at order 8*/
        quantize_coefficients(lp_coefficients, 8, qlp_coefficients8);

        /*calculate residuals for QLP coefficients at order 4*/
        calculate_residuals(samples, sample_size,
                            qlp_coefficients4, residual_values4);

        /*calculate residuals for QLP coefficients at order 8*/
        calculate_residuals(samples, sample_size,
                            qlp_coefficients8, residual_values8);

        /*encode residual block for QLP coefficients at order 4*/
        bw_reset_recorder(residual_block4);
        encode_residuals(encoder, sample_size,
                         residual_values4, residual_block4);

        /*encode residual block for QLP coefficients at order 8*/
        bw_reset_recorder(residual_block8);
        encode_residuals(encoder, sample_size,
                         residual_values8, residual_block8);

        /*return the LPC coefficients/residual which is the smallest*/
        if (residual_block4->bits_written(residual_block4) <
            (residual_block8->bits_written(residual_block8) + 64)) {
            /*use QLP coefficients with order 4*/
            qlp_coefficients4->copy(qlp_coefficients4,
                                    qlp_coefficients);
            bw_rec_copy(residual, residual_block4);
        } else {
            /*use QLP coefficients with order 8*/
            qlp_coefficients8->copy(qlp_coefficients8,
                                    qlp_coefficients);
            bw_rec_copy(residual, residual_block8);
        }
    } else {
        /*all samples are 0, so use a special case*/
        qlp_coefficients->mset(qlp_coefficients, 4, 0);

        calculate_residuals(samples, sample_size,
                            qlp_coefficients, residual_values4);

        encode_residuals(encoder, sample_size,
                         residual_values4, residual);
    }
}

static void
window_signal(struct alac_context* encoder,
              const array_i* samples,
              array_f* windowed_signal)
{
    array_f* tukey_window = encoder->tukey_window;
    unsigned N = samples->len;
    unsigned n;
    double alpha = 0.5;
    unsigned window1;
    unsigned window2;

    if (tukey_window->len != samples->len) {
        tukey_window->reset_for(tukey_window, samples->len);

        window1 = (unsigned)(alpha * (N - 1)) / 2;
        window2 = (unsigned)((N - 1) * (1.0 - (alpha / 2.0)));

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

static void
autocorrelate(const array_f* windowed_signal,
              array_f* autocorrelation_values)
{
    unsigned lag;
    unsigned i;
    double accumulator;

    autocorrelation_values->reset(autocorrelation_values);

    for (lag = 0; lag <= MAX_LPC_ORDER; lag++) {
        accumulator = 0.0;
        assert((windowed_signal->len - lag) > 0);
        for (i = 0; i < windowed_signal->len - lag; i++)
            accumulator += (windowed_signal->_[i] *
                            windowed_signal->_[i + lag]);
        autocorrelation_values->append(autocorrelation_values, accumulator);
    }
}

static void
compute_lp_coefficients(const array_f* autocorrelation_values,
                        array_fa* lp_coefficients)
{
    unsigned i;
    unsigned j;
    array_f* lp_coeff;
    double k;
    double q;
    /*no exceptions occur here, so it's okay to allocate temp space*/
    array_f* lp_error = array_f_new();

    assert(autocorrelation_values->len == (MAX_LPC_ORDER + 1));

    lp_coefficients->reset(lp_coefficients);
    lp_error->reset(lp_error);

    k = autocorrelation_values->_[1] / autocorrelation_values->_[0];
    lp_coeff = lp_coefficients->append(lp_coefficients);
    lp_coeff->append(lp_coeff, k);
    lp_error->append(lp_error,
                     autocorrelation_values->_[0] * (1.0 - (k * k)));

    for (i = 1; i < MAX_LPC_ORDER; i++) {
        q = autocorrelation_values->_[i + 1];
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

    lp_error->del(lp_error);
}

static void
quantize_coefficients(const array_fa* lp_coefficients,
                      unsigned order,
                      array_i* qlp_coefficients)
{
    array_f* lp_coeffs = lp_coefficients->_[order - 1];
    int qlp_max;
    int qlp_min;
    double error;
    int error_i;
    unsigned i;

    assert(lp_coeffs->len == order);

    qlp_coefficients->reset(qlp_coefficients);

    qlp_max = (1 << 15) - 1;
    qlp_min = -(1 << 15);

    error = 0.0;

    for (i = 0; i < order; i++) {
        error += (lp_coeffs->_[i] * (1 << 9));
        error_i = (int)round(error);
        qlp_coefficients->append(qlp_coefficients,
                                 MIN(MAX(error_i, qlp_min), qlp_max));
        error -= (double)error_i;
    }
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

static inline int
TRUNCATE_BITS(int value, unsigned bits)
{
    /*truncate value to bits*/
    const int truncated = value & ((1 << bits) - 1);

    /*apply sign bit*/
    if (truncated & (1 << (bits - 1))) {
        return truncated - (1 << bits);
    } else {
        return truncated;
    }
}

static void
calculate_residuals(const array_i* samples,
                    unsigned sample_size,
                    const array_i* qlp_coefficients,
                    array_i* residuals)
{
    unsigned i = 0;

    /*no exceptions occur here either, so temporary array is safe*/
    array_i* coefficients = array_i_new();
    const unsigned coeff_count = qlp_coefficients->len;

    qlp_coefficients->copy(qlp_coefficients, coefficients);
    residuals->reset_for(residuals, samples->len);

    /*first sample always copied verbatim*/
    a_append(residuals, samples->_[i++]);

    if (coeff_count < 31) {
        unsigned j;

        for (; i < (coeff_count + 1); i++)
            a_append(residuals,
                     TRUNCATE_BITS(samples->_[i] - samples->_[i - 1],
                                   sample_size));

        for (; i < samples->len; i++) {
            const int base_sample = samples->_[i - coeff_count - 1];
            int64_t lpc_sum = 1 << 8;
            int error;

            for (j = 0; j < coeff_count; j++) {
                lpc_sum += ((int64_t)coefficients->_[j] *
                            (int64_t)(samples->_[i - j - 1] - base_sample));
            }

            lpc_sum >>= 9;

            error = TRUNCATE_BITS(samples->_[i] - base_sample - (int)lpc_sum,
                                  sample_size);
            a_append(residuals, error);

            if (error > 0) {
                for (j = 0; j < coeff_count; j++) {
                    const int diff = (base_sample -
                                      samples->_[i - coeff_count + j]);
                    const int sign = SIGN_ONLY(diff);
                    coefficients->_[coeff_count - j - 1] -= sign;
                    error -= ((diff * sign) >> 9) * (j + 1);
                    if (error <= 0)
                        break;
                }
            } else if (error < 0) {
                for (j = 0; j < coeff_count; j++) {
                    const int diff = (base_sample -
                                      samples->_[i - coeff_count + j]);
                    const int sign = SIGN_ONLY(diff);
                    coefficients->_[coeff_count - j - 1] += sign;
                    error -= ((diff * -sign) >> 9) * (j + 1);
                    if (error >= 0)
                        break;
                }
            }
        }
    } else {
        for (; i < samples->len; i++) {
            a_append(residuals,
                     TRUNCATE_BITS(samples->_[i] - samples->_[i - 1],
                                   sample_size));
        }
    }

    coefficients->del(coefficients);
}

static inline unsigned
LOG2(unsigned value)
{
    unsigned bits = 0;
    assert(value > 0);
    while (value) {
        bits++;
        value >>= 1;
    }
    return bits - 1;
}


static void
encode_residuals(struct alac_context* encoder,
                 unsigned sample_size,
                 const array_i* residuals,
                 BitstreamWriter *residual_block)
{
    int history = (int)encoder->options.initial_history;
    unsigned sign_modifier = 0;
    unsigned i = 0;
    unsigned unsigned_i;
    const unsigned max_unsigned = (1 << sample_size);
    const unsigned history_multiplier = encoder->options.history_multiplier;
    const unsigned maximum_k = encoder->options.maximum_k;
    unsigned k;
    unsigned zeroes;

    while (i < residuals->len) {
        if (residuals->_[i] >= 0) {
            unsigned_i = (unsigned)(residuals->_[i] << 1);
        } else {
            unsigned_i = (unsigned)(-residuals->_[i] << 1) - 1;
        }

        if (unsigned_i >= max_unsigned) {
            /*raise a residual overflow exception
              which means writing an uncompressed frame instead*/
            longjmp(encoder->residual_overflow, 1);
        }

        k = LOG2((history >> 9) + 3);
        k = MIN(k, maximum_k);
        write_residual(unsigned_i - sign_modifier, k, sample_size,
                       residual_block);
        sign_modifier = 0;

        if (unsigned_i <= 0xFFFF) {
            history += ((int)(unsigned_i * history_multiplier) -
                        ((history * (int)history_multiplier) >> 9));
            i++;

            if ((history < 128) && (i < residuals->len)) {
                /*handle potential block of 0 residuals*/
                k = 7 - LOG2(history) + ((history + 16) >> 6);
                k = MIN(k, maximum_k);
                zeroes = 0;
                while ((i < residuals->len) && (residuals->_[i] == 0)) {
                    zeroes++;
                    i++;
                }
                write_residual(zeroes, k, 16, residual_block);
                if (zeroes < 0xFFFF)
                    sign_modifier = 1;
                history = 0;
            }
        } else {
            i++;
            history = 0xFFFF;
        }
    }
}

static void
write_residual(unsigned value, unsigned k, unsigned sample_size,
                    BitstreamWriter* residual)
{
    const unsigned MSB = value / ((1 << k) - 1);
    const unsigned LSB = value % ((1 << k) - 1);
    if (MSB > 8) {
        residual->write(residual, 9, 0x1FF);
        residual->write(residual, sample_size, value);
    } else {
        residual->write_unary(residual, 0, MSB);
        if (k > 1) {
            if (LSB > 0) {
                residual->write(residual, k, LSB + 1);
            } else {
                residual->write(residual, k - 1, 0);
            }
        }
    }
}


static void
write_subframe_header(BitstreamWriter *bs,
                      const array_i* qlp_coefficients)
{
    unsigned i;

    bs->write(bs, 4, 0); /*prediction type*/
    bs->write(bs, 4, 9); /*QLP shift needed*/
    bs->write(bs, 3, 4); /*Rice modifier*/
    bs->write(bs, 5, qlp_coefficients->len);
    for (i = 0; i < qlp_coefficients->len; i++) {
        bs->write_signed(bs, 16, qlp_coefficients->_[i]);
    }
}

#ifndef STANDALONE
PyObject
*alac_log_output(struct alac_context *encoder)
{
    PyObject *sample_size_list = NULL;
    PyObject *byte_size_list = NULL;
    PyObject *file_offset_list = NULL;
    PyObject *to_return;
    array_i* log;
    int i;

    if ((sample_size_list = PyList_New(0)) == NULL)
        goto error;
    if ((byte_size_list = PyList_New(0)) == NULL)
        goto error;
    if ((file_offset_list = PyList_New(0)) == NULL)
        goto error;

    log = encoder->frame_log->_[LOG_SAMPLE_SIZE];
    for (i = 0; i < log->len; i++)
        if (PyList_Append(sample_size_list,
                          PyInt_FromLong(log->_[i])) == -1)
            goto error;

    log = encoder->frame_log->_[LOG_BYTE_SIZE];
    for (i = 0; i < log->len; i++)
        if (PyList_Append(byte_size_list,
                          PyInt_FromLong(log->_[i])) == -1)
            goto error;

    log = encoder->frame_log->_[LOG_FILE_OFFSET];
    for (i = 0; i < log->len; i++)
        if (PyList_Append(file_offset_list,
                          PyInt_FromLong(log->_[i])) == -1)
            goto error;

    to_return = Py_BuildValue("(O,O,O,i)",
                              sample_size_list,
                              byte_size_list,
                              file_offset_list,
                              encoder->mdat_byte_size);

    Py_DECREF(sample_size_list);
    Py_DECREF(byte_size_list);
    Py_DECREF(file_offset_list);

    return to_return;

 error:
    Py_XDECREF(sample_size_list);
    Py_XDECREF(byte_size_list);
    Py_XDECREF(file_offset_list);
    return NULL;
}
#else
#include <getopt.h>
#include <errno.h>

static unsigned
count_bits(unsigned value)
{
    unsigned bits = 0;
    while (value) {
        bits += value & 0x1;
        value >>= 1;
    }
    return bits;
}

int main(int argc, char *argv[]) {
    char* output_file = NULL;
    unsigned channels = 2;
    unsigned channel_mask = 0x3;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;

    int block_size = 4096;
    int initial_history = 10;
    int history_multiplier = 40;
    int maximum_k = 14;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"block-size",              required_argument, NULL, 'B'},
        {"initial-history",         required_argument, NULL, 'I'},
        {"history-multiplier",      required_argument, NULL, 'M'},
        {"maximum-K",               required_argument, NULL, 'K'},
        {NULL,                      no_argument, NULL, 0}};
    const static char* short_opts = "-hc:r:b:B:M:K:";

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
        case 'm':
            if (((channel_mask = strtoul(optarg, NULL, 16)) == 0) && errno) {
                printf("invalid --channel-mask \"%s\"\n", optarg);
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
            if (((block_size = strtol(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --block-size \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'I':
            if (((initial_history = strtol(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --initial-history \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'M':
            if (((history_multiplier =
                  strtol(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --history-multiplier \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'K':
            if (((maximum_k = strtol(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --maximum-K \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: alacenc [options] <output.m4a>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("\n");
            printf("-B, --block-size=#              block size\n");
            printf("-I, --initial-history=#         initial history\n");
            printf("-M, --history-multiplier=#      history multiplier\n");
            printf("-K, --maximum-K=#     maximum K\n");
            return 0;
        default:
            break;
        }
    }
    if (output_file == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    }

    assert(channels > 0);
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16) ||
           (bits_per_sample == 24));
    assert(sample_rate > 0);
    assert(count_bits(channel_mask) == channels);

    printf("Encoding from stdin using parameters:\n");
    printf("channels        %u\n", channels);
    printf("channel mask    0x%X\n", channel_mask);
    printf("sample rate     %u\n", sample_rate);
    printf("bits per sample %u\n", bits_per_sample);
    printf("little-endian, signed samples\n");
    printf("\n");
    printf("block size         %d\n", block_size);
    printf("initial history    %d\n", initial_history);
    printf("history multiplier %d\n", history_multiplier);
    printf("maximum K          %d\n", maximum_k);

    if (ALACEncoder_encode_alac(output_file,
                                open_pcmreader(stdin,
                                               sample_rate,
                                               channels,
                                               channel_mask,
                                               bits_per_sample,
                                               0,
                                               1),
                                block_size,
                                initial_history,
                                history_multiplier,
                                maximum_k)) {
        fprintf(stderr, "Error during encoding\n");
        return 1;
    } else {
        return 0;
    }
}
#endif
