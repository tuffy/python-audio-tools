#include "alac.h"
#include "../common/misc.h"
#include "../pcmconv.h"
#include <assert.h>
#include <math.h>

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

#define MAX_LPC_ORDER 8

/* #ifndef STANDALONE */


/*     /\*write "mdat" atom header*\/ */
/*     if (fgetpos(output_file, &starting_point) != 0) { */
/*         PyErr_SetFromErrno(PyExc_IOError); */
/*         goto error; */
/*     } */
/*     stream->write_64(stream, 32, encode_log.mdat_byte_size); */
/*     stream->write_64(stream, 32, 0x6D646174);  /\*"mdat" type*\/ */

/*     /\*write frames from pcm_reader until empty*\/ */
/*     if (!pcmr_read(reader, options.block_size, &samples)) */
/*         goto error; */
/*     while (iaa_getitem(&samples, 0)->size > 0) { */
/*         thread_state = PyEval_SaveThread(); */
/*         if (alac_write_frameset(stream, */
/*                                 &encode_log, */
/*                                 ftell(output_file), */
/*                                 &options, */
/*                                 reader->bits_per_sample, */
/*                                 &samples) == ERROR) { */
/*             PyEval_RestoreThread(thread_state); */
/*             goto error; */
/*         } else */
/*             PyEval_RestoreThread(thread_state); */

/*         if (!pcmr_read(reader, options.block_size, &samples)) */
/*             goto error; */
/*     } */

/*     /\*rewind stream and rewrite "mdat" atom header*\/ */
/*     if (fsetpos(output_file, &starting_point) != 0) { */
/*         PyErr_SetFromErrno(PyExc_IOError); */
/*         goto error; */
/*     } */
/*     stream->write_64(stream, 32, encode_log.mdat_byte_size); */

/*     /\*close and free allocated files/buffers*\/ */
/*     pcmr_close(reader); */
/*     stream->free(stream); */
/*     iaa_free(&samples); */
/*     options.best_frame->close(options.best_frame); */
/*     options.current_frame->close(options.current_frame); */

/*     /\*return the accumulated log of output*\/ */
/*     encode_log_obj = alac_log_output(&encode_log); */
/*     alac_log_free(&encode_log); */
/*     return encode_log_obj; */

/*  error: */
/*     options.best_frame->close(options.best_frame); */
/*     options.current_frame->close(options.current_frame); */
/*     pcmr_close(reader); */
/*     stream->free(stream); */
/*     iaa_free(&samples); */
/*     alac_log_free(&encode_log); */
/*     return NULL; */
/* } */

/* #else */

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
                             "minimum_interlacing_shift",
                             "maximum_interlacing_shift",
                             "minimum_interlacing_leftweight",
                             "maximum_interlacing_leftweight",
                             NULL};

    PyObject *file_obj;
    FILE *output_file;
    BitstreamWriter *output = NULL;
    PyObject *pcmreader_obj;
    pcmreader* pcmreader;
    struct alac_context encoder;
    array_ia* channels = array_ia_new();
    unsigned frame_file_offset;

    PyObject *log_output;
    PyThreadState *thread_state;

    alacenc_init_encoder(&encoder);

    encoder.options.minimum_interlacing_shift = 2;
    encoder.options.maximum_interlacing_shift = 2;
    encoder.options.minimum_interlacing_leftweight = 0;
    encoder.options.maximum_interlacing_leftweight = 4;

    /*extract a file object, PCMReader-compatible object and encoding options*/
    if (!PyArg_ParseTupleAndKeywords(
                    args, keywds, "OOiiii|iiii",
                    kwlist,
                    &file_obj,
                    &pcmreader_obj,
                    &(encoder.options.block_size),
                    &(encoder.options.initial_history),
                    &(encoder.options.history_multiplier),
                    &(encoder.options.maximum_k),
                    &(encoder.options.minimum_interlacing_shift),
                    &(encoder.options.maximum_interlacing_shift),
                    &(encoder.options.minimum_interlacing_leftweight),
                    &(encoder.options.maximum_interlacing_leftweight)))
        return NULL;

    /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
    if ((pcmreader = open_pcmreader(pcmreader_obj)) == NULL) {
        return NULL;
    }

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
                        alac_byte_counter,
                        &(encoder.mdat_byte_size));
    }

#else

status
ALACEncoder_encode_alac(char *filename,
                        FILE *input,
                        int block_size,
                        int initial_history,
                        int history_multiplier,
                        int maximum_k)
{
    FILE *output_file;
    BitstreamWriter *output = NULL;
    pcmreader *pcmreader;
    struct alac_context encoder;
    array_ia* channels = array_ia_new();
    unsigned frame_file_offset;

    alacenc_init_encoder(&encoder);

    encoder.options.block_size = block_size;
    encoder.options.initial_history = initial_history;
    encoder.options.history_multiplier = history_multiplier;
    encoder.options.maximum_k = maximum_k;
    encoder.options.minimum_interlacing_shift = 2;
    encoder.options.maximum_interlacing_shift = 2;
    encoder.options.minimum_interlacing_leftweight = 0;
    encoder.options.maximum_interlacing_leftweight = 4;

    output_file = fopen(filename, "wb");
    /*assume CD quality for now*/
    pcmreader = open_pcmreader(input, 44100, 1, 0x4, 16, 0, 1);

    encoder.bits_per_sample = pcmreader->bits_per_sample;

    /*convert file object to bitstream writer*/
    output = bw_open(output_file, BS_BIG_ENDIAN);
    bw_add_callback(output,
                    alac_byte_counter,
                    &(encoder.mdat_byte_size));

    /*FIXME - handle thread state saving/restoring*/
#endif

    /*write placeholder mdat header*/
    output->write(output, 32, 0);
    output->write_bytes(output, (uint8_t*)"mdat", 4);

    /*write frames from pcm_reader until empty*/
    if (pcmreader->read(pcmreader, encoder.options.block_size, channels))
        goto error;
    while (channels->data[0]->size > 0) {
        /*log the number of PCM frames in each ALAC frameset*/
        encoder.frame_log->data[LOG_SAMPLE_SIZE]->append(
            encoder.frame_log->data[LOG_SAMPLE_SIZE],
            channels->data[0]->size);

        frame_file_offset = encoder.mdat_byte_size;

        /*log each frameset's starting offset in the mdat atom*/
        encoder.frame_log->data[LOG_FILE_OFFSET]->append(
            encoder.frame_log->data[LOG_FILE_OFFSET],
            frame_file_offset);

        if (alac_write_frameset(output, &encoder, channels) == ERROR)
            goto error;

        /*log each frame's total size in bytes*/
        encoder.frame_log->data[LOG_BYTE_SIZE]->append(
            encoder.frame_log->data[LOG_BYTE_SIZE],
            encoder.mdat_byte_size - frame_file_offset);

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
    alacenc_free_encoder(&encoder);
    channels->del(channels);

    return log_output;

 error:

    pcmreader->del(pcmreader);
    output->free(output);
    alacenc_free_encoder(&encoder);
    channels->del(channels);

    return NULL;
}
#else

    pcmreader->del(pcmreader);
    output->free(output);
    alacenc_free_encoder(&encoder);
    channels->del(channels);

    return OK;
 error:
    pcmreader->del(pcmreader);
    output->free(output);
    alacenc_free_encoder(&encoder);
    channels->del(channels);

    return ERROR;
}
#endif

void
alacenc_init_encoder(struct alac_context* encoder)
{
    encoder->frame_byte_size = 0;
    encoder->mdat_byte_size = 0;

    encoder->frame_log = array_ia_new();
    encoder->frame_log->append(encoder->frame_log); /*LOG_SAMPLE_SIZE*/
    encoder->frame_log->append(encoder->frame_log); /*LOG_BYTE_SIZE*/
    encoder->frame_log->append(encoder->frame_log); /*LOG_FILE_OFFSET*/

    encoder->LSBs = array_i_new();
    encoder->channels_MSB = array_ia_new();

    encoder->LPC_coefficients0 = array_i_new();
    encoder->LPC_coefficients1 = array_i_new();
    encoder->residual0 = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->residual1 = bw_open_recorder(BS_BIG_ENDIAN);

    encoder->tukey_window = array_f_new();
    encoder->windowed_signal = array_f_new();
    encoder->autocorrelation_values = array_f_new();
    encoder->lp_coefficients = array_fa_new();
    encoder->qlp_coefficients4 = array_i_new();
    encoder->qlp_coefficients8 = array_i_new();

    encoder->compressed_frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->best_frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->current_frame = bw_open_recorder(BS_BIG_ENDIAN);
}

void
alacenc_free_encoder(struct alac_context* encoder)
{
    encoder->frame_log->del(encoder->frame_log);

    encoder->LSBs->del(encoder->LSBs);
    encoder->channels_MSB->del(encoder->channels_MSB);

    encoder->LPC_coefficients0->del(encoder->LPC_coefficients0);
    encoder->LPC_coefficients1->del(encoder->LPC_coefficients1);
    encoder->residual0->close(encoder->residual0);
    encoder->residual1->close(encoder->residual1);

    encoder->tukey_window->del(encoder->tukey_window);
    encoder->windowed_signal->del(encoder->windowed_signal);
    encoder->autocorrelation_values->del(encoder->autocorrelation_values);
    encoder->lp_coefficients->del(encoder->lp_coefficients);
    encoder->qlp_coefficients4->del(encoder->qlp_coefficients4);
    encoder->qlp_coefficients8->del(encoder->qlp_coefficients8);

    encoder->compressed_frame->close(encoder->compressed_frame);
    encoder->best_frame->close(encoder->best_frame);
    encoder->current_frame->close(encoder->current_frame);
}

void
alac_byte_counter(uint8_t byte, void* counter)
{
    int* i_counter = (int*)counter;
    *i_counter += 1;
}

status
alac_write_frameset(BitstreamWriter *bs,
                    struct alac_context* encoder,
                    const array_ia* channels)
{
    switch (channels->size) {
    case 1:
    case 2:
        if (alac_write_frame(bs, encoder, channels) == OK) {
            bs->write(bs, 3, 7);  /*write the trailing '111' bits*/
            bs->byte_align(bs);   /*and byte-align frameset*/
            return OK;
        } else {
            return ERROR;
        }
    default:
        /*unsupported channel count*/
        return ERROR;
    }
}

status
alac_write_frame(BitstreamWriter *bs,
                 struct alac_context* encoder,
                 const array_ia* channels)
{
    BitstreamWriter *compressed_frame;

    assert((channels->size == 1) || (channels->size == 2));

    bs->write(bs, 3, channels->size - 1);

    if ((channels->data[0]->size >= 10)) {
        compressed_frame = encoder->compressed_frame;
        bw_reset_recorder(compressed_frame);
        switch (alac_write_compressed_frame(compressed_frame,
                                            encoder,
                                            channels)) {
        case OK:
            /*FIXME - compare size of compressed frame
              against the size of a hypothetical uncompressed frame*/
            bw_rec_copy(bs, compressed_frame);
            return OK;
        case ERROR:
            return ERROR;
        case RESIDUAL_OVERFLOW:
            return alac_write_uncompressed_frame(bs, encoder, channels);
        default:
            /*shouldn't get here*/
            abort();
            return ERROR;
        }
    } else {
        return alac_write_uncompressed_frame(bs, encoder, channels);
    }
}

status
alac_write_uncompressed_frame(BitstreamWriter *bs,
                              struct alac_context* encoder,
                              const array_ia* channels)
{
    unsigned i;
    unsigned c;

    bs->write(bs, 16, 0);  /*unused*/

    if (channels->data[0]->size == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, 0);  /*no uncompressed LSBs*/
    bs->write(bs, 1, 1);  /*not compressed*/

    if (channels->data[0]->size != encoder->options.block_size)
        bs->write(bs, 32, channels->data[0]->size);

    for (i = 0; i < channels->data[0]->size; i++) {
        for (c = 0; c < channels->size; c++) {
            bs->write_signed(bs,
                             encoder->bits_per_sample,
                             channels->data[c]->data[i]);
        }
    }

    return OK;
}

status
alac_write_compressed_frame(BitstreamWriter *bs,
                            struct alac_context* encoder,
                            const array_ia* channels)
{
    unsigned uncompressed_LSBs;
    array_i* LSBs;
    array_ia* channels_MSB;
    unsigned i;
    unsigned c;

    if (encoder->bits_per_sample <= 16) {
        /*no uncompressed least-significant bits*/
        uncompressed_LSBs = 0;
        LSBs = NULL;

        if (channels->size == 1) {
            return alac_write_non_interlaced_frame(bs,
                                                   encoder,
                                                   uncompressed_LSBs,
                                                   LSBs,
                                                   channels);
        } else {
            /*FIXME*/
            assert(0);
            return ERROR;
        }
    } else {
        /*extract uncompressed least-significant bits*/
        uncompressed_LSBs = (encoder->bits_per_sample - 16) / 8;
        LSBs = encoder->LSBs;
        channels_MSB = encoder->channels_MSB;

        LSBs->reset(LSBs);
        channels_MSB->reset(channels_MSB);

        for (c = 0; c < channels->size; c++) {
            channels_MSB->append(channels_MSB);
        }

        for (i = 0; i < channels->data[0]->size; i++) {
            for (c = 0; c < channels->size; c++) {
                LSBs->append(LSBs,
                             channels->data[c]->data[i] &
                             ((1 << (encoder->bits_per_sample - 16)) - 1));
                channels_MSB->data[c]->append(channels_MSB->data[c],
                                              channels->data[c]->data[i] >>
                                              (encoder->bits_per_sample - 16));
            }
        }

        if (channels->size == 1) {
            return alac_write_non_interlaced_frame(bs,
                                                   encoder,
                                                   uncompressed_LSBs,
                                                   LSBs,
                                                   channels_MSB);
        } else {
            /*FIXME*/
            assert(0);
            return ERROR;
        }
    }
}

status
alac_write_non_interlaced_frame(BitstreamWriter *bs,
                                struct alac_context* encoder,
                                unsigned uncompressed_LSBs,
                                const array_i* LSBs,
                                const array_ia* channels)
{
    unsigned i;
    array_i* LPC_coefficients = encoder->LPC_coefficients0;
    BitstreamWriter* residual = encoder->residual0;

    bs->write(bs, 16, 0);  /*unusued*/

    if (channels->data[0]->size == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, uncompressed_LSBs);
    bs->write(bs, 1, 0);   /*is compressed*/

    if (channels->data[0]->size != encoder->options.block_size)
        bs->write(bs, 32, channels->data[0]->size);

    bs->write(bs, 8, 0);   /*no interlacing shift*/
    bs->write(bs, 8, 0);   /*no interlacing leftweight*/

    switch (alac_compute_coefficients(encoder,
                                      channels->data[0],
                                      LPC_coefficients,
                                      residual)) {
    case OK:
        break;
    case RESIDUAL_OVERFLOW:
        return RESIDUAL_OVERFLOW;
    case ERROR:
        return ERROR;
    default:
        /*shouldn't get here*/
        abort();
        return ERROR;
    }

    alac_write_subframe_header(bs, LPC_coefficients);

    if (uncompressed_LSBs > 0) {
        for (i = 0; i < LSBs->size; i++) {
            bs->write(bs, uncompressed_LSBs * 8, LSBs->data[i]);
        }
    }

    bw_rec_copy(bs, residual);

    return OK;
}

status
alac_compute_coefficients(struct alac_context* encoder,
                          const array_i* samples,
                          array_i* LPC_coefficients,
                          BitstreamWriter *residual)
{
    array_f* windowed_signal = encoder->windowed_signal;
    array_f* autocorrelation_values = encoder->autocorrelation_values;
    array_fa* lp_coefficients = encoder->lp_coefficients;
    array_i* qlp_coefficients4 = encoder->qlp_coefficients4;
    array_i* qlp_coefficients8 = encoder->qlp_coefficients8;

    /*window the input samples*/
    alac_window_signal(encoder,
                       samples,
                       windowed_signal);

    /*compute autocorrelation values for samples*/
    alac_autocorrelate(windowed_signal,
                       autocorrelation_values);

    assert(autocorrelation_values->size == 9);

    /*transform autocorrelation values to lists of LP coefficients*/
    alac_compute_lp_coefficients(autocorrelation_values,
                                 lp_coefficients);

    /*quantize LP coefficients at order 4*/
    alac_quantize_coefficients(lp_coefficients, 4, qlp_coefficients4);

    /*quantize LP coefficients at order 8*/
    alac_quantize_coefficients(lp_coefficients, 8, qlp_coefficients8);

    printf("QLP coefficients : ");
    qlp_coefficients4->print(qlp_coefficients4, stdout);
    printf("\n");
    printf("QLP coefficients : ");
    qlp_coefficients8->print(qlp_coefficients8, stdout);
    printf("\n");

    /*calculate residuals for LPC coefficients at order 4*/
    /*FIXME*/

    /*calculate residuals for LPC coefficients at order 8*/
    /*FIXME*/

    /*encode residual block for LPC coefficients at order 4*/
    /*FIXME*/

    /*encode residual block for LPC coefficients at order 8*/
    /*FIXME*/

    /*return the LPC coefficients/residual which is the smallest*/
    /*FIXME*/

    assert(0);
    return ERROR;
}

void
alac_window_signal(struct alac_context* encoder,
                   const array_i* samples,
                   array_f* windowed_signal)
{
    array_f* tukey_window = encoder->tukey_window;
    unsigned N = samples->size;
    unsigned n;
    double alpha = 0.5;
    unsigned window1;
    unsigned window2;

    if (tukey_window->size != samples->size) {
        tukey_window->resize(tukey_window, samples->size);
        tukey_window->reset(tukey_window);

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

    windowed_signal->resize(windowed_signal, samples->size);
    windowed_signal->reset(windowed_signal);
    for (n = 0; n < N; n++) {
        a_append(windowed_signal, samples->data[n] * tukey_window->data[n]);
    }
}

void
alac_autocorrelate(const array_f* windowed_signal,
                   array_f* autocorrelation_values)
{
    unsigned lag;
    unsigned i;
    double accumulator;

    autocorrelation_values->reset(autocorrelation_values);

    for (lag = 0; lag <= MAX_LPC_ORDER; lag++) {
        accumulator = 0.0;
        assert((windowed_signal->size - lag) > 0);
        for (i = 0; i < windowed_signal->size - lag; i++)
            accumulator += (windowed_signal->data[i] *
                            windowed_signal->data[i + lag]);
        autocorrelation_values->append(autocorrelation_values, accumulator);
    }
}

void
alac_compute_lp_coefficients(const array_f* autocorrelation_values,
                             array_fa* lp_coefficients)
{
    unsigned i;
    unsigned j;
    array_f* lp_coeff;
    double k;
    double q;
    array_f* lp_error = array_f_new();

    assert(autocorrelation_values->size == (MAX_LPC_ORDER + 1));

    lp_coefficients->reset(lp_coefficients);
    lp_error->reset(lp_error);

    k = autocorrelation_values->data[1] / autocorrelation_values->data[0];
    lp_coeff = lp_coefficients->append(lp_coefficients);
    lp_coeff->append(lp_coeff, k);
    lp_error->append(lp_error,
                     autocorrelation_values->data[0] * (1.0 - (k * k)));

    for (i = 1; i < MAX_LPC_ORDER; i++) {
        q = autocorrelation_values->data[i + 1];
        for (j = 0; j < i; j++)
            q -= (lp_coefficients->data[i - 1]->data[j] *
                  autocorrelation_values->data[i - j]);

        k = q / lp_error->data[i - 1];

        lp_coeff = lp_coefficients->append(lp_coefficients);
        for (j = 0; j < i; j++) {
            lp_coeff->append(lp_coeff,
                             lp_coefficients->data[i - 1]->data[j] -
                             (k *
                              lp_coefficients->data[i - 1]->data[i - j - 1]));
        }
        lp_coeff->append(lp_coeff, k);

        lp_error->append(lp_error, lp_error->data[i - 1] * (1.0 - (k * k)));
    }

    lp_error->del(lp_error);
}

void
alac_quantize_coefficients(const array_fa* lp_coefficients,
                           unsigned order,
                           array_i* qlp_coefficients)
{
    array_f* lp_coeffs = lp_coefficients->data[order - 1];
    int qlp_max;
    int qlp_min;
    double error;
    int error_i;
    unsigned i;

    assert(lp_coeffs->size == order);

    qlp_coefficients->reset(qlp_coefficients);

    qlp_max = (1 << 15) - 1;
    qlp_min = -(1 << 15);

    error = 0.0;

    for (i = 0; i < order; i++) {
        error += (lp_coeffs->data[i] * (1 << 9));
        error_i = (int)round(error);
        qlp_coefficients->append(qlp_coefficients,
                                 MIN(MAX(error_i, qlp_min), qlp_max));
        error -= (double)error_i;
    }
}

void
alac_write_subframe_header(BitstreamWriter *bs,
                           const array_i* LPC_coefficients)
{
    /*FIXME*/
    assert(0);
}

/* status */
/* alac_write_frame(BitstreamWriter *bs, */
/*                  struct alac_encoding_options *options, */
/*                  int bits_per_sample, */
/*                  struct ia_array *samples) { */
/*     BitstreamWriter *compressed_frame; */

/*     if (samples->arrays[0].size < 10) { */
/*         /\*write uncompressed frame if not enough samples remain*\/ */
/*         if (alac_write_uncompressed_frame( */
/*                 bs, options->block_size, bits_per_sample, samples) == ERROR) */
/*             return ERROR; */
/*         else */
/*             return OK; */
/*     } else { */
/*         /\*otherwise, attempt compressed frame*\/ */
/*         compressed_frame = bw_open_recorder(BS_BIG_ENDIAN); */

/*         switch (alac_write_compressed_frame(compressed_frame, */
/*                                             options, */
/*                                             bits_per_sample, */
/*                                             samples)) { */
/*         case ERROR: */
/*             goto error; */
/*         case RESIDUAL_OVERFLOW: */
/*             if (alac_write_uncompressed_frame(bs, */
/*                                               options->block_size, */
/*                                               bits_per_sample, */
/*                                               samples) == ERROR) */
/*                 goto error; */
/*             else */
/*                 break; */
/*         case OK: */
/*             if (compressed_frame->bits_written(compressed_frame) < */
/*                 ((samples->size * samples->arrays[0].size * bits_per_sample) + */
/*                  56)) */
/*                 /\*if our compressed frame is small enough, write it out*\/ */
/*                 bw_rec_copy(bs, compressed_frame); */
/*             else { */
/*                 /\*otherwise, build an uncompressed frame instead*\/ */
/*                 if (alac_write_uncompressed_frame(bs, */
/*                                                   options->block_size, */
/*                                                   bits_per_sample, */
/*                                                   samples) == ERROR) */
/*                     return ERROR; */
/*             } */
/*             break; */
/*         } */

/*         compressed_frame->close(compressed_frame); */
/*         return OK; */

/*     error: */
/*         compressed_frame->close(compressed_frame); */
/*         return ERROR; */
/*     } */
/* } */


/* status */
/* alac_write_uncompressed_frame(BitstreamWriter *bs, */
/*                               int block_size, */
/*                               int bits_per_sample, */
/*                               struct ia_array *samples) */
/* { */
/*     int channels = samples->size; */
/*     int pcm_frames = samples->arrays[0].size; */
/*     int has_sample_size = (pcm_frames != block_size); */
/*     int i, j; */

/*     /\*write frame header*\/ */
/*     bs->write(bs, 16, 0);           /\*unknown, all 0*\/ */
/*     if (has_sample_size)               /\*"has sample size"" flag*\/ */
/*         bs->write(bs, 1, 1); */
/*     else */
/*         bs->write(bs, 1, 0); */
/*     bs->write(bs, 2, 0);  /\*uncompressed frames never have wasted bits*\/ */
/*     bs->write(bs, 1, 1);  /\*the "is not compressed flag" flag*\/ */
/*     if (has_sample_size) */
/*         bs->write_64(bs, 32, pcm_frames); */

/*     /\*write individual samples*\/ */
/*     for (i = 0; i < pcm_frames; i++) */
/*         for (j = 0; j < channels; j++) */
/*             bs->write_signed(bs, */
/*                              bits_per_sample, */
/*                              samples->arrays[j].data[i]); */

/*     return OK; */
/* } */

/* status */
/* alac_write_compressed_frame(BitstreamWriter *bs, */
/*                             struct alac_encoding_options *options, */

/*                             int bits_per_sample, */
/*                             struct ia_array *samples) */
/* { */
/*     int interlacing_shift; */
/*     int interlacing_leftweight; */
/*     BitstreamWriter *best_frame = options->best_frame; */
/*     BitstreamWriter *current_frame = options->current_frame; */

/*     if (samples->size != 2) { */
/*         return alac_write_interlaced_frame(bs, */
/*                                            options, */
/*                                            0, 0, */
/*                                            bits_per_sample, */
/*                                            samples); */
/*     } else { */
/*         bw_maximize_recorder(best_frame); */

/*         /\*attempt all the interlacing shift options*\/ */
/*         for (interlacing_shift = options->minimum_interlacing_shift; */
/*              interlacing_shift <= options->maximum_interlacing_shift; */
/*              interlacing_shift++) { */
/*             /\*attempt all the interlacing leftweight options*\/ */
/*             for (interlacing_leftweight = */
/*                      options->minimum_interlacing_leftweight; */
/*                  interlacing_leftweight <= */
/*                      options->maximum_interlacing_leftweight; */
/*                  interlacing_leftweight++) { */
/*                 bw_reset_recorder(current_frame); */
/*                 switch (alac_write_interlaced_frame(current_frame, */
/*                                                     options, */
/*                                                     interlacing_shift, */
/*                                                     interlacing_leftweight, */
/*                                                     bits_per_sample, */
/*                                                     samples)) { */
/*                 case ERROR: */
/*                     goto error; */
/*                 case RESIDUAL_OVERFLOW: */
/*                     goto overflow; */
/*                 case OK: */
/*                     if (current_frame->bits_written(current_frame) < */
/*                         best_frame->bits_written(best_frame)) */
/*                         bw_swap_records(current_frame, best_frame); */
/*                     break; */
/*                 } */
/*             } */
/*         } */

/*         /\*use the shift and leftweight that uses the least bits*\/ */
/*         bw_rec_copy(bs, best_frame); */
/*         return OK; */
/*     error: */
/*         return ERROR; */
/*     overflow: */
/*         return RESIDUAL_OVERFLOW; */
/*     } */
/* } */

/* status */
/* alac_write_interlaced_frame(BitstreamWriter *bs, */
/*                             struct alac_encoding_options *options, */
/*                             int interlacing_shift, */
/*                             int interlacing_leftweight, */
/*                             int bits_per_sample, */
/*                             struct ia_array *samples) */
/* { */
/*     int channels = samples->size; */
/*     int pcm_frames = samples->arrays[0].size; */
/*     int has_sample_size = (pcm_frames != options->block_size); */
/*     int has_wasted_bits = (bits_per_sample > 16); */
/*     struct i_array wasted_bits; */
/*     struct ia_array *cropped_samples = NULL; */
/*     struct ia_array correlated_samples; */
/*     struct ia_array lpc_coefficients; */
/*     struct i_array *coefficients; */
/*     int *shift_needed = NULL; */
/*     struct ia_array residuals; */
/*     status return_status = OK; */

/*     int i, j; */

/*     /\*write frame header*\/ */
/*     bs->write(bs, 16, 0);           /\*unknown, all 0*\/ */
/*     if (has_sample_size)                 /\*"has sample size"" flag*\/ */
/*         bs->write(bs, 1, 1); */
/*     else */
/*         bs->write(bs, 1, 0); */

/*     if (has_wasted_bits)                 /\*"has wasted bits" value*\/ */
/*         bs->write(bs, 2, 1); */
/*     else */
/*         bs->write(bs, 2, 0); */

/*     bs->write(bs, 1, 0);  /\*the "is not compressed flag" flag*\/ */

/*     if (has_sample_size) */
/*         bs->write_64(bs, 32, pcm_frames); */

/*     /\*if we have wasted bits, extract them from the front of each sample */
/*       we'll only support 8 wasted bits, for 24bps input*\/ */
/*     if (has_wasted_bits) { */
/*         ia_init(&wasted_bits, channels * pcm_frames); */
/*         cropped_samples = malloc(sizeof(struct ia_array)); */
/*         iaa_init(cropped_samples, channels, pcm_frames); */
/*         iaa_copy(cropped_samples, samples); */
/*         samples = cropped_samples; */
/*         for (i = 0; i < pcm_frames; i++) */
/*             for (j = 0; j < channels; j++) { */
/*                 ia_append(&wasted_bits, samples->arrays[j].data[i] & 0xFF); */
/*                 samples->arrays[j].data[i] >>= 8; */
/*             } */
/*     } */

/*     iaa_init(&correlated_samples, channels, pcm_frames); */
/*     iaa_init(&residuals, channels, pcm_frames); */

/*     assert(interlacing_shift < (1 << 8)); */
/*     assert(interlacing_leftweight < (1 << 8)); */
/*     bs->write(bs, 8, interlacing_shift); */
/*     bs->write(bs, 8, interlacing_leftweight); */

/*     /\*apply channel correlation to samples*\/ */
/*     alac_correlate_channels(&correlated_samples, */
/*                             samples, */
/*                             interlacing_shift, */
/*                             interlacing_leftweight); */

/*     /\*calculate the best "prediction quantitization" and "coefficient" values */
/*       for each channel of audio*\/ */
/*     iaa_init(&lpc_coefficients, channels, 4); */
/*     shift_needed = malloc(sizeof(int) * channels); */
/*     for (i = 0; i < channels; i++) { */
/*         alac_compute_best_lpc_coeffs(iaa_getitem(&lpc_coefficients, i), */
/*                                      &(shift_needed[i]), */
/*                                      bits_per_sample - (has_wasted_bits * 8), */
/*                                      options, */
/*                                      iaa_getitem(samples, i)); */
/*     } */

/*     /\*write 1 subframe header per channel*\/ */
/*     for (i = 0; i < channels; i++) { */
/*         bs->write(bs, 4, 0);                /\*prediction type of 0*\/ */
/*         assert(shift_needed[i] < (1 << 4)); */
/*         bs->write(bs, 4, shift_needed[i]);  /\*prediction quantitization*\/ */
/*         bs->write(bs, 3, 4);                /\*Rice modifier of 4 seems typical*\/ */
/*         coefficients = iaa_getitem(&lpc_coefficients, i); */
/*         assert(coefficients->size < (1 << 5)); */
/*         bs->write(bs, 5, coefficients->size); */
/*         for (j = 0; j < coefficients->size; j++) { */
/*             assert(coefficients->data[j] < (1 << (16 - 1))); */
/*             assert(coefficients->data[j] >= -(1 << (16 - 1))); */
/*             bs->write_signed(bs, 16, coefficients->data[j]); */
/*         } */
/*     } */

/*     /\*write wasted bits block, if any*\/ */
/*     if (has_wasted_bits) { */
/*         for (i = 0; i < wasted_bits.size; i++) { */
/*             assert(wasted_bits.data[i] < (1 << 8)); */
/*             bs->write(bs, 8, wasted_bits.data[i]); */
/*         } */
/*     } */

/*     /\*calculate residuals for each channel */
/*       based on "coefficients", "quantitization", and "samples"*\/ */
/*     for (i = 0; i < channels; i++) */
/*         if ((return_status = alac_encode_subframe( */
/*                                             &(residuals.arrays[i]), */
/*                                             &(correlated_samples.arrays[i]), */
/*                                             &(lpc_coefficients.arrays[i]), */
/*                                             shift_needed[i])) != OK) */
/*             goto finished; */

/*     /\*write 1 residual block per channel*\/ */
/*     for (i = 0; i < channels; i++) { */
/*         if ((return_status = alac_write_residuals( */
/*                     bs, */
/*                     &(residuals.arrays[i]), */
/*                     bits_per_sample - (has_wasted_bits * 8) + channels - 1, */
/*                     options)) != OK) */
/*             goto finished; */
/*     } */
/*  finished: */
/*     /\*clear any temporary buffers*\/ */
/*     if (has_wasted_bits) { */
/*         ia_free(&wasted_bits); */
/*         iaa_free(cropped_samples); */
/*         free(cropped_samples); */
/*     } */
/*     iaa_free(&correlated_samples); */
/*     iaa_free(&lpc_coefficients); */
/*     if (shift_needed != NULL) */
/*         free(shift_needed); */
/*     iaa_free(&residuals); */

/*     return return_status; */
/* } */

/* status */
/* alac_correlate_channels(struct ia_array *output, */
/*                         struct ia_array *input, */
/*                         int interlacing_shift, */
/*                         int interlacing_leftweight) */
/* { */
/*     struct i_array *left_channel; */
/*     struct i_array *right_channel; */
/*     struct i_array *channel1; */
/*     struct i_array *channel2; */
/*     ia_data_t left; */
/*     ia_data_t right; */
/*     ia_size_t pcm_frames, i; */

/*     assert(input->size > 0); */
/*     if (input->size != 2) { */
/*         for (i = 0; i < input->size; i++) { */
/*             ia_copy(iaa_getitem(output, i), iaa_getitem(input, i)); */
/*         } */
/*     } else { */
/*         left_channel = iaa_getitem(input, 0); */
/*         right_channel = iaa_getitem(input, 1); */
/*         channel1 = iaa_getitem(output, 0); */
/*         ia_reset(channel1); */
/*         channel2 = iaa_getitem(output, 1); */
/*         ia_reset(channel2); */
/*         pcm_frames = left_channel->size; */

/*         if (interlacing_leftweight == 0) { */
/*             ia_copy(channel1, left_channel); */
/*             ia_copy(channel2, right_channel); */
/*         } else { */
/*             for (i = 0; i < pcm_frames; i++) { */
/*                 left = left_channel->data[i]; */
/*                 right = right_channel->data[i]; */
/*                 ia_append(channel1, right + */
/*                           (((left - right) * interlacing_leftweight) >> */
/*                            interlacing_shift)); */
/*                 ia_append(channel2, left - right); */
/*             } */
/*         } */
/*     } */

/*     return OK; */
/* } */

/* static inline int */
/* SIGN_ONLY(int value) */
/* { */
/*     if (value > 0) */
/*         return 1; */
/*     else if (value < 0) */
/*         return -1; */
/*     else */
/*         return 0; */
/* } */

/* status */
/* alac_encode_subframe(struct i_array *residuals, */
/*                      struct i_array *samples, */
/*                      struct i_array *coefficients, */
/*                      int predictor_quantitization) */
/* { */
/*     int64_t lpc_sum; */
/*     ia_data_t buffer0; */
/*     ia_data_t sample; */
/*     ia_data_t residual; */
/*     int32_t val; */
/*     int sign; */
/*     int i = 0; */
/*     int j; */
/*     int original_sign; */

/*     assert(samples->size > 5); */
/*     if (coefficients->size < 1) { */
/*         alac_error("coefficient count must be greater than 0"); */
/*         return ERROR; */
/*     } else if ((coefficients->size != 4) && (coefficients->size != 8)) { */
/*         alac_warning("coefficient size not 4 or 8"); */
/*     } */

/*     ia_reset(residuals); */

/*     /\*first sample always copied verbatim*\/ */
/*     ia_append(residuals, samples->data[i++]); */

/*     /\*grab a number of warm-up samples equal to coefficients' length*\/ */
/*     for (j = 0; j < coefficients->size; j++) { */
/*         /\*these are adjustments to the previous sample*\/ */
/*         ia_append(residuals, samples->data[i] - samples->data[i - 1]); */
/*         i++; */
/*     } */

/*     /\*then calculate a new residual per remaining sample*\/ */
/*     for (; i < samples->size; i++) { */
/*         /\*Note that buffer0 gets stripped from previously encoded samples */
/*           then re-added prior to adding the next sample. */
/*           It's a watermark sample, of sorts.*\/ */
/*         buffer0 = samples->data[i - (coefficients->size + 1)]; */

/*         sample = samples->data[i]; */
/*         lpc_sum = 1 << (predictor_quantitization - 1); */

/*         for (j = 0; j < coefficients->size; j++) { */
/*             lpc_sum += (int64_t)((int64_t)coefficients->data[j] * */
/*                                  (int64_t)(samples->data[i - j - 1] - */
/*                                            buffer0)); */
/*         } */

/*         lpc_sum >>= predictor_quantitization; */
/*         lpc_sum += buffer0; */
/*         /\*residual = sample - (((sum + 2 ^ (quant - 1)) / (2 ^ quant)) + buffer0)*\/ */
/*         residual = (int32_t)(sample - lpc_sum); */

/*         ia_append(residuals, residual); */

/*         /\*ALAC's adaptive algorithm then adjusts the coefficients */
/*           up or down 1 step based on previously encoded samples */
/*           and the residual*\/ */

/*         /\*FIXME - shift this into its own routine, perhaps*\/ */
/*         if (residual) { */
/*             original_sign = SIGN_ONLY(residual); */

/*             for (j = 0; j < coefficients->size; j++) { */
/*                 val = buffer0 - samples->data[i - coefficients->size + j]; */
/*                 if (original_sign >= 0) */
/*                     sign = SIGN_ONLY(val); */
/*                 else */
/*                     sign = -SIGN_ONLY(val); */
/*                 coefficients->data[coefficients->size - j - 1] -= sign; */
/*                 residual -= (((val * sign) >> predictor_quantitization) * */
/*                              (j + 1)); */
/*                 if (SIGN_ONLY(residual) != original_sign) */
/*                     break; */
/*             } */
/*         } */
/*     } */

/*     return OK; */
/* } */

/* void */
/* alac_write_residual(BitstreamWriter *bs, */
/*                     int residual, */
/*                     int k, */
/*                     int bits_per_sample) */
/* { */
/*     int q = residual / ((1 << k) - 1); */
/*     int e = residual % ((1 << k) - 1); */
/*     if (q > 8) { */
/*         bs->write(bs, 9, 0x1FF); */
/*         assert(residual < (1 << bits_per_sample)); */
/*         bs->write(bs, bits_per_sample, residual); */
/*     } else { */
/*         if (q > 0) */
/*             bs->write_unary(bs, 0, q); */
/*         else */
/*             bs->write(bs, 1, 0); */
/*         if (k > 1) { */
/*             if (e > 0) { */
/*                 assert((e + 1) < (1 << k)); */
/*                 bs->write(bs, k, e + 1); */
/*             } else { */
/*                 assert((k - 1) > 0); */
/*                 bs->write(bs, k - 1, 0); */
/*             } */
/*         } */
/*     } */
/* } */

/* static inline int */
/* LOG2(int value) */
/* { */
/*     int bits = -1; */
/*     assert(value >= 0); */
/*     while (value) { */
/*         bits++; */
/*         value >>= 1; */
/*     } */
/*     return bits; */
/* } */

/* status */
/* alac_write_residuals(BitstreamWriter *bs, */
/*                      struct i_array *residuals, */
/*                      int bits_per_sample, */
/*                      struct alac_encoding_options *options) */
/* { */
/*     int history = options->initial_history; */
/*     int history_multiplier = options->history_multiplier; */
/*     int maximum_k = options->maximum_k; */
/*     int sign_modifier = 0; */
/*     int i; */
/*     int k; */
/*     ia_data_t signed_residual; */
/*     ia_data_t unsigned_residual; */
/*     int zero_block_size; */
/*     int max_residual = (1 << bits_per_sample); */

/*     for (i = 0; i < residuals->size;) { */
/*         k = MIN(LOG2((history >> 9) + 3), maximum_k); */
/*         assert(k > 0); */
/*         signed_residual = residuals->data[i]; */
/*         if (signed_residual >= 0) */
/*             unsigned_residual = (signed_residual * 2); */
/*         else */
/*             unsigned_residual = ((-signed_residual * 2) - 1); */

/*         if (unsigned_residual >= max_residual) */
/*             return RESIDUAL_OVERFLOW; */
/*         alac_write_residual(bs, unsigned_residual - sign_modifier, */
/*                             k, bits_per_sample); */

/*         if (unsigned_residual <= 0xFFFF) */
/*             history += ((unsigned_residual * history_multiplier) - */
/*                         ((history * history_multiplier) >> 9)); */
/*         else */
/*             history = 0xFFFF; */
/*         sign_modifier = 0; */
/*         i++; */

/*         /\*the special case for handling blocks of 0 residuals*\/ */
/*         if ((history < 128) && (i < residuals->size)) { */
/*             zero_block_size = 0; */
/*             k = MIN(7 - LOG2(history) + ((history + 16) >> 6), maximum_k); */
/*             while ((residuals->data[i] == 0) && (i < residuals->size)) { */
/*                 zero_block_size++; */
/*                 i++; */
/*             } */
/*             alac_write_residual(bs, zero_block_size, k, 16); */
/*             if (zero_block_size <= 0xFFFF) */
/*                 sign_modifier = 1; */
/*             history = 0; */
/*         } */

/*     } */

/*     return OK; */
/* } */

/* void */
/* alac_error(const char* message) */
/* { */
/* #ifndef STANDALONE */
/*     PyErr_SetString(PyExc_ValueError, message); */
/* #else */
/*     fprintf(stderr, "Error: %s\n", message); */
/* #endif */
/* } */

/* void */
/* alac_warning(const char* message) */
/* { */
/* #ifndef STANDALONE */
/*     PyErr_WarnEx(PyExc_RuntimeWarning, message, 1); */
/* #else */
/*     fprintf(stderr, "Warning: %s\n", message); */
/* #endif */
/* } */

/* void */
/* alac_log_init(struct alac_encode_log *log) */
/* { */
/*     log->frame_byte_size = 0; */
/*     log->mdat_byte_size = 0; */
/*     iaa_init(&(log->frame_log), 3, 1024); */
/* } */

/* void */
/* alac_log_free(struct alac_encode_log *log) */
/* { */
/*     iaa_free(&(log->frame_log)); */
/* } */

/* #ifndef STANDALONE */
/* PyObject* */
/* alac_log_output(struct alac_encode_log *log) */
/* { */

/* } */
/* #endif */

#ifdef STANDALONE
int main(int argc, char *argv[]) {
    if (ALACEncoder_encode_alac(argv[1],
                                stdin,
                                4096,
                                10,
                                40,
                                14) == ERROR) {
        fprintf(stderr, "Error during encoding\n");
        return 1;
    } else {
        return 0;
    }
}
#else

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

    log = encoder->frame_log->data[LOG_SAMPLE_SIZE];
    for (i = 0; i < log->size; i++)
        if (PyList_Append(sample_size_list,
                          PyInt_FromLong(log->data[i])) == -1)
            goto error;

    log = encoder->frame_log->data[LOG_BYTE_SIZE];
    for (i = 0; i < log->size; i++)
        if (PyList_Append(byte_size_list,
                          PyInt_FromLong(log->data[i])) == -1)
            goto error;

    log = encoder->frame_log->data[LOG_FILE_OFFSET];
    for (i = 0; i < log->size; i++)
        if (PyList_Append(file_offset_list,
                          PyInt_FromLong(log->data[i])) == -1)
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

#endif
