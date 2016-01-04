#include "alac.h"
#include <string.h>
#include <assert.h>
#include <math.h>
#include "../common/m4a_atoms.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

static struct alac_frame_size*
push_frame_size(struct alac_frame_size *head,
                unsigned byte_size,
                unsigned pcm_frames_size);

static void
reverse_frame_sizes(struct alac_frame_size **head);

#ifdef STANDALONE
static unsigned
total_frame_sizes(const struct alac_frame_size *head);
#else
static unsigned
total_encoded_pcm_frames(const struct alac_frame_size *head);
#endif

static void
free_alac_frame_sizes(struct alac_frame_size *frame_sizes);

#ifndef STANDALONE

PyObject*
encoders_encode_alac(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    static char *kwlist[] = {"file",
                             "pcmreader",
                             "total_pcm_frames",
                             "block_size",
                             "initial_history",
                             "history_multiplier",
                             "maximum_k",
                             "version",
                             NULL};
    PyObject *file_obj;
    BitstreamWriter *output = NULL;
    struct PCMReader *pcmreader;
    long long total_pcm_frames;
    int block_size;
    int initial_history;
    int history_multiplier;
    int maximum_k;
    const char *version;
    struct alac_frame_size *frame_sizes;

    /*extract a file object, PCMReader-compatible object and encoding options*/
    if (!PyArg_ParseTupleAndKeywords(args, keywds, "OO&Liiiis",
                                     kwlist,
                                     &file_obj,
                                     py_obj_to_pcmreader,
                                     &pcmreader,
                                     &total_pcm_frames,
                                     &block_size,
                                     &initial_history,
                                     &history_multiplier,
                                     &maximum_k,
                                     &version)) {
        return NULL;
    }

    /*determine if the PCMReader is compatible with ALAC*/
    if ((pcmreader->bits_per_sample != 16) &&
        (pcmreader->bits_per_sample != 24)) {
        PyErr_SetString(PyExc_ValueError, "bits per sample must be 16 or 24");
        return NULL;
    }

    /*sanity-check arguments*/
    if (total_pcm_frames < 0) {
        PyErr_SetString(PyExc_ValueError,
                        "total_pcm_frames must be >= 0");
        return NULL;
    } else if (total_pcm_frames > 2147483647) {
        PyErr_SetString(PyExc_ValueError,
                        "total_pcm_frames must be < 2 ** 31 - 1");
        return NULL;
    } else if (block_size < 1) {
        PyErr_SetString(PyExc_ValueError, "block_size must be > 0");
        return NULL;
    } else if (initial_history < 0) {
        PyErr_SetString(PyExc_ValueError, "initial_history must be >= 0");
        return NULL;
    } else if (history_multiplier < 0) {
        PyErr_SetString(PyExc_ValueError, "history_multiplier must be >= 0");
        return NULL;
    } else if (maximum_k < 1) {
        PyErr_SetString(PyExc_ValueError, "maximum_k must be > 0");
        return NULL;
    }

    output = bw_open_external(file_obj,
                              BS_BIG_ENDIAN,
                              4096,
                              bw_write_python,
                              bs_setpos_python,
                              bs_getpos_python,
                              bs_free_pos_python,
                              bs_fseek_python,
                              bw_flush_python,
                              bs_close_python,
                              bs_free_python_nodecref);

    frame_sizes = encode_alac(output,
                              pcmreader,
                              (unsigned)total_pcm_frames,
                              block_size,
                              initial_history,
                              history_multiplier,
                              maximum_k,
                              version);

    if (frame_sizes) {
        output->flush(output);
        output->free(output);
        free_alac_frame_sizes(frame_sizes);

        Py_INCREF(Py_None);
        return Py_None;
    } else {
        /*indicate read error has occurred*/
        output->free(output);

        return NULL;
    }
}

#endif

#define BUFFER_SIZE 4096

static struct alac_frame_size*
encode_alac(BitstreamWriter *output,
            struct PCMReader *pcmreader,
            unsigned total_pcm_frames,
            int block_size,
            int initial_history,
            int history_multiplier,
            int maximum_k,
            const char encoder_version[])
{
    time_t timestamp = time(NULL);

    if (total_pcm_frames) {
        /*output temporary metadata atoms based on dummy frame sizes list*/
        bw_pos_t *start = output->getpos(output);

        struct alac_frame_size *dummy_sizes =
            dummy_frame_sizes(block_size, total_pcm_frames);

        const unsigned metadata_size = write_metadata(
            output,
            timestamp,
            pcmreader->sample_rate,
            pcmreader->channels,
            pcmreader->bits_per_sample,
            total_pcm_frames,
            block_size,
            history_multiplier,
            initial_history,
            maximum_k,
            dummy_sizes,
            0,
            encoder_version);

        unsigned rewritten_size;

        /*write mdat atom to output*/
        struct alac_frame_size *actual_sizes =
            encode_mdat(output,
                        pcmreader,
                        block_size,
                        initial_history,
                        history_multiplier,
                        maximum_k);

        if (!actual_sizes) {
            free_alac_frame_sizes(dummy_sizes);
            start->del(start);
            return NULL;
        }

        assert(total_frame_sizes(actual_sizes) ==
               total_frame_sizes(dummy_sizes));
        free_alac_frame_sizes(dummy_sizes);

#ifndef STANDALONE
        if (total_encoded_pcm_frames(actual_sizes) != total_pcm_frames) {
            /*total PCM frames mismatch after encoding*/
            free_alac_frame_sizes(actual_sizes);
            start->del(start);
            PyErr_SetString(PyExc_IOError, "total PCM frames mismatch");
            return NULL;
        }
#endif

        /*rewrite start of file based on actual frame sizes list*/
        output->setpos(output, start);
        start->del(start);

        rewritten_size = write_metadata(output,
                                        timestamp,
                                        pcmreader->sample_rate,
                                        pcmreader->channels,
                                        pcmreader->bits_per_sample,
                                        total_pcm_frames,
                                        block_size,
                                        history_multiplier,
                                        initial_history,
                                        maximum_k,
                                        actual_sizes,
                                        metadata_size + 8,
                                        encoder_version);

#ifndef NDEBUG
        assert(rewritten_size == metadata_size);
#else
        if (rewritten_size != metadata_size) {
            fprintf(stderr,
                    "*** Warning: metadata size %u != %u\n",
                    rewritten_size, metadata_size);
        }
#endif

        /*return actual frame sizes list*/
        return actual_sizes;
    } else {
        FILE *tempfile = tmpfile();
        BitstreamWriter *temp_output = bw_open(tempfile, BS_BIG_ENDIAN);
        BitstreamAccumulator *metadata_size_writer =
            bw_open_accumulator(BS_BIG_ENDIAN);
        unsigned metadata_size;
        struct alac_frame_size *size;
        unsigned total_pcm_frames = 0;
        uint8_t buffer[BUFFER_SIZE];
        size_t bytes_read;

        /*write mdat atom to temporary file*/
        struct alac_frame_size *actual_sizes =
            encode_mdat(temp_output,
                        pcmreader,
                        block_size,
                        initial_history,
                        history_multiplier,
                        maximum_k);

        if (!actual_sizes) {
            metadata_size_writer->close(metadata_size_writer);
            temp_output->free(temp_output);
            fclose(tempfile);
            return NULL;
        }

        temp_output->flush(temp_output);
        temp_output->free(temp_output);

        /*determine total PCM frames written from frame sizes list*/
        for (size = actual_sizes; size; size = size->next) {
            total_pcm_frames += size->pcm_frames_size;
        }

        /*get metadata size in order to determine chunk offsets*/
        metadata_size = write_metadata(
            (BitstreamWriter*)metadata_size_writer,
            timestamp,
            pcmreader->sample_rate,
            pcmreader->channels,
            pcmreader->bits_per_sample,
            total_pcm_frames,
            block_size,
            history_multiplier,
            initial_history,
            maximum_k,
            actual_sizes,
            0,
            encoder_version);

        assert(metadata_size ==
               metadata_size_writer->bytes_written(metadata_size_writer));

        /*output metadata atoms*/
        metadata_size = write_metadata(
            output,
            timestamp,
            pcmreader->sample_rate,
            pcmreader->channels,
            pcmreader->bits_per_sample,
            total_pcm_frames,
            block_size,
            history_multiplier,
            initial_history,
            maximum_k,
            actual_sizes,
            metadata_size + 8,
            encoder_version);

        assert(metadata_size ==
              metadata_size_writer->bytes_written(metadata_size_writer));
        metadata_size_writer->close(metadata_size_writer);

        /*copy mdat atom from temporary file to output*/
        rewind(tempfile);
        while ((bytes_read = fread(buffer,
                                   sizeof(uint8_t),
                                   BUFFER_SIZE,
                                   tempfile)) > 0) {
            output->write_bytes(output, buffer, (unsigned)bytes_read);
        }

        /*close temporary file and return frame sizes list*/
        fclose(tempfile);
        return actual_sizes;
    }
}

static struct alac_frame_size*
encode_mdat(BitstreamWriter *output,
            struct PCMReader *pcmreader,
            int block_size,
            int initial_history,
            int history_multiplier,
            int maximum_k)
{
    struct alac_context encoder;
    int *samples = malloc(pcmreader->channels *
                          block_size *
                          sizeof(int));
    unsigned frame_byte_size = 0;
    bw_pos_t* mdat_header = NULL;
    unsigned pcm_frames_read;
    struct alac_frame_size *frame_sizes = NULL;

    init_encoder(&encoder, block_size);

    encoder.options.block_size = block_size;
    encoder.options.initial_history = initial_history;
    encoder.options.history_multiplier = history_multiplier;
    encoder.options.maximum_k = maximum_k;
    encoder.options.minimum_interlacing_leftweight = 0;
    encoder.options.maximum_interlacing_leftweight = 4;

    encoder.bits_per_sample = pcmreader->bits_per_sample;

    /*FIXME - check marks/rewinds for I/O errors*/
    mdat_header = output->getpos(output);

    output->add_callback(output,
                         (bs_callback_f)byte_counter,
                         &frame_byte_size);

    /*write placeholder mdat header*/
    output->write(output, 32, 0);
    output->write_bytes(output, (uint8_t*)"mdat", 4);

    /*write frames from pcm_reader until empty*/
    while ((pcm_frames_read = pcmreader->read(pcmreader,
                                              encoder.options.block_size,
                                              samples)) > 0) {
        frame_byte_size = 0;

        /*perform encoding*/
        write_frameset(output,
                       &encoder,
                       pcm_frames_read,
                       pcmreader->channels,
                       samples);

        /*log each frameset's size in bytes and size in samples*/
        frame_sizes = push_frame_size(frame_sizes,
                                      frame_byte_size,
                                      pcm_frames_read);
    }

    output->pop_callback(output, NULL);
    free(samples);

    if (pcmreader->status == PCM_OK) {
        /*return to header and rewrite it with the actual value*/
        unsigned total_mdat_size = 8;
        struct alac_frame_size *frame_size;

        for (frame_size = frame_sizes;
             frame_size;
             frame_size = frame_size->next) {
            total_mdat_size += frame_size->byte_size;
        }

        output->setpos(output, mdat_header);
        output->write(output, 32, total_mdat_size);
        mdat_header->del(mdat_header);

        /*close and free allocated files/buffers*/

        free_encoder(&encoder);

        reverse_frame_sizes(&frame_sizes);
        return frame_sizes;
    } else {
        if (mdat_header) {
            mdat_header->del(mdat_header);
        }

        free_encoder(&encoder);

        free_alac_frame_sizes(frame_sizes);
        return NULL;
    }
}

static struct alac_frame_size*
push_frame_size(struct alac_frame_size *head,
                unsigned byte_size,
                unsigned pcm_frames_size)
{
    struct alac_frame_size *frame_size = malloc(sizeof(struct alac_frame_size));
    frame_size->byte_size = byte_size;
    frame_size->pcm_frames_size = pcm_frames_size;
    frame_size->next = head;
    return frame_size;
}

static void
reverse_frame_sizes(struct alac_frame_size **head)
{
    struct alac_frame_size *reversed = NULL;
    struct alac_frame_size *top = *head;
    while (top) {
        *head = (*head)->next;
        top->next = reversed;
        reversed = top;
        top = *head;
    }
    *head = reversed;
}

#ifdef STANDALONE
static unsigned
total_frame_sizes(const struct alac_frame_size *head)
{
    unsigned total = 0;
    for (; head; head = head->next) {
        total += 1;
    }
    return total;
}
#else
static unsigned
total_encoded_pcm_frames(const struct alac_frame_size *head)
{
    unsigned total = 0;
    for (; head; head = head->next) {
        total += head->pcm_frames_size;
    }
    return total;
}
#endif

static void
free_alac_frame_sizes(struct alac_frame_size *frame_sizes)
{
    while (frame_sizes) {
        struct alac_frame_size *next = frame_sizes->next;
        free(frame_sizes);
        frame_sizes = next;
    }
}

static void
init_encoder(struct alac_context* encoder, unsigned block_size)
{
    encoder->tukey_window = malloc(sizeof(double) * block_size);
    tukey_window(0.5, block_size, encoder->tukey_window);

    encoder->residual0 = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->residual1 = bw_open_recorder(BS_BIG_ENDIAN);

    encoder->residual_block4 = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->residual_block8 = bw_open_recorder(BS_BIG_ENDIAN);

    encoder->compressed_frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->interlaced_frame = bw_open_recorder(BS_BIG_ENDIAN);
    encoder->best_interlaced_frame = bw_open_recorder(BS_BIG_ENDIAN);
}

static void
free_encoder(struct alac_context* encoder)
{
    free(encoder->tukey_window);

    encoder->residual0->close(encoder->residual0);
    encoder->residual1->close(encoder->residual1);

    encoder->residual_block4->close(encoder->residual_block4);
    encoder->residual_block8->close(encoder->residual_block8);

    encoder->compressed_frame->close(encoder->compressed_frame);
    encoder->interlaced_frame->close(encoder->interlaced_frame);
    encoder->best_interlaced_frame->close(encoder->best_interlaced_frame);
}

static void
write_frameset(BitstreamWriter *bs,
               struct alac_context* encoder,
               unsigned pcm_frames,
               unsigned channel_count,
               const int channels[])
{
    int channel0[pcm_frames];
    int channel1[pcm_frames];
    unsigned i;

    switch (channel_count) {
    case 1:
        write_frame(bs, encoder, pcm_frames, 1, channels, NULL);
        break;
    case 2:
        get_channel_data(channels, 0, 2, pcm_frames, channel0);
        get_channel_data(channels, 1, 2, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        break;
    case 3:
        get_channel_data(channels, 2, 3, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 0, 3, pcm_frames, channel0);
        get_channel_data(channels, 1, 3, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        break;
    case 4:
        get_channel_data(channels, 2, 4, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 0, 4, pcm_frames, channel0);
        get_channel_data(channels, 1, 4, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 3, 4, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        break;
    case 5:
        get_channel_data(channels, 2, 5, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 0, 5, pcm_frames, channel0);
        get_channel_data(channels, 1, 5, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 3, 5, pcm_frames, channel0);
        get_channel_data(channels, 4, 5, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        break;
    case 6:
        get_channel_data(channels, 2, 6, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 0, 6, pcm_frames, channel0);
        get_channel_data(channels, 1, 6, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 4, 6, pcm_frames, channel0);
        get_channel_data(channels, 5, 6, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 3, 6, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        break;
    case 7:
        get_channel_data(channels, 2, 7, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 0, 7, pcm_frames, channel0);
        get_channel_data(channels, 1, 7, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 4, 7, pcm_frames, channel0);
        get_channel_data(channels, 5, 7, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 6, 7, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 3, 7, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        break;
    case 8:
        get_channel_data(channels, 2, 8, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        get_channel_data(channels, 6, 8, pcm_frames, channel0);
        get_channel_data(channels, 7, 8, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 0, 8, pcm_frames, channel0);
        get_channel_data(channels, 1, 8, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 4, 8, pcm_frames, channel0);
        get_channel_data(channels, 5, 8, pcm_frames, channel1);
        write_frame(bs, encoder, pcm_frames, 2, channel0, channel1);
        get_channel_data(channels, 3, 8, pcm_frames, channel0);
        write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        break;
    default:
        for (i = 0; i < channel_count; i++) {
            get_channel_data(channels, i, channel_count, pcm_frames, channel0);
            write_frame(bs, encoder, pcm_frames, 1, channel0, NULL);
        }
        break;
    }

    bs->write(bs, 3, 7);  /*write the trailing '111' bits*/
    bs->byte_align(bs);   /*and byte-align frameset*/
}

static void
write_frame(BitstreamWriter *bs,
            struct alac_context* encoder,
            unsigned pcm_frames,
            unsigned channel_count,
            const int channel0[],
            const int channel1[])
{
    BitstreamRecorder *compressed_frame = encoder->compressed_frame;

    assert((channel_count == 1) || (channel_count == 2));

    bs->write(bs, 3, channel_count - 1);

    if (pcm_frames >= 10) {
        compressed_frame->reset(compressed_frame);
        if (!setjmp(encoder->residual_overflow)) {
            write_compressed_frame(bs,
                                   encoder,
                                   pcm_frames,
                                   channel_count,
                                   channel0, channel1);

            compressed_frame->copy(compressed_frame, bs);
        } else {
            /*a residual overflow exception occurred,
              so write an uncompressed frame instead*/
            write_uncompressed_frame(bs,
                                     encoder,
                                     pcm_frames,
                                     channel_count,
                                     channel0, channel1);
        }
    } else {
        write_uncompressed_frame(bs,
                                 encoder,
                                 pcm_frames,
                                 channel_count,
                                 channel0, channel1);
    }
}

static void
write_uncompressed_frame(BitstreamWriter *bs,
                         struct alac_context* encoder,
                         unsigned pcm_frames,
                         unsigned channel_count,
                         const int channel0[],
                         const int channel1[])
{
    unsigned i;
    const unsigned bits_per_sample = encoder->bits_per_sample;

    assert((channel_count == 1) || (channel_count == 2));

    bs->write(bs, 16, 0);  /*unused*/

    if (pcm_frames == encoder->options.block_size) {
        bs->write(bs, 1, 0);
    } else {
        bs->write(bs, 1, 1);
    }

    bs->write(bs, 2, 0);  /*no uncompressed LSBs*/
    bs->write(bs, 1, 1);  /*not compressed*/

    if (pcm_frames != encoder->options.block_size) {
        bs->write(bs, 32, pcm_frames);
    }

    if (channel_count == 2) {
        for (i = 0; i < pcm_frames; i++) {
            bs->write_signed(bs, bits_per_sample, channel0[i]);
            bs->write_signed(bs, bits_per_sample, channel1[i]);
        }
    } else {
        for (i = 0; i < pcm_frames; i++) {
            bs->write_signed(bs, bits_per_sample, channel0[i]);
        }
    }
}

static void
write_compressed_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned pcm_frames,
                       unsigned channel_count,
                       const int channel0[],
                       const int channel1[])
{
    assert((channel_count == 1) || (channel_count == 2));

    if (encoder->bits_per_sample <= 16) {
        /*no uncompressed least-significant bits*/

        if (channel_count == 1) {
            write_non_interlaced_frame(bs,
                                       encoder,
                                       pcm_frames,
                                       0, NULL,
                                       channel0);
        } else {
            unsigned leftweight;
            BitstreamRecorder *interlaced_frame =
                encoder->interlaced_frame;
            BitstreamRecorder *best_interlaced_frame =
                encoder->best_interlaced_frame;
            unsigned best_interlaced_frame_bits =
                UINT_MAX;

            /*attempt all the interlacing leftweight combinations*/
            for (leftweight = encoder->options.minimum_interlacing_leftweight;
                 leftweight <= encoder->options.maximum_interlacing_leftweight;
                 leftweight++) {

                interlaced_frame->reset(interlaced_frame);

                write_interlaced_frame((BitstreamWriter*)interlaced_frame,
                                       encoder,
                                       pcm_frames,
                                       0, NULL,
                                       INTERLACING_SHIFT,
                                       leftweight,
                                       channel0, channel1);

                if (interlaced_frame->bits_written(interlaced_frame) <
                    best_interlaced_frame_bits) {
                    best_interlaced_frame_bits =
                        interlaced_frame->bits_written(interlaced_frame);
                    recorder_swap(&best_interlaced_frame,
                                  &interlaced_frame);
                }
            }

            /*write the smallest leftweight to disk*/
            best_interlaced_frame->copy(best_interlaced_frame, bs);
        }
    } else {
        unsigned uncompressed_LSBs = (encoder->bits_per_sample - 16) / 8;
        int LSBs[pcm_frames * channel_count];
        int MSBs0[pcm_frames];
        int MSBs1[pcm_frames];
        unsigned i;
        const unsigned lsb_mask = (1 << (encoder->bits_per_sample - 16)) - 1;
        const unsigned msb_shift = encoder->bits_per_sample - 16;

        if (channel_count == 2) {
            unsigned leftweight;
            BitstreamRecorder *interlaced_frame =
                encoder->interlaced_frame;
            BitstreamRecorder *best_interlaced_frame =
                encoder->best_interlaced_frame;
            unsigned best_interlaced_frame_bits =
                UINT_MAX;

            /*extract uncompressed least-significant bits*/
            for (i = 0; i < pcm_frames; i++) {
                LSBs[i * 2] = channel0[i] & lsb_mask;
                LSBs[i * 2 + 1] = channel1[i] & lsb_mask;
                MSBs0[i] = channel0[i] >> msb_shift;
                MSBs1[i] = channel1[i] >> msb_shift;
            }

            /*attempt all the interlacing leftweight combinations*/
            for (leftweight = encoder->options.minimum_interlacing_leftweight;
                 leftweight <= encoder->options.maximum_interlacing_leftweight;
                 leftweight++) {

                interlaced_frame->reset(interlaced_frame);

                write_interlaced_frame((BitstreamWriter*)interlaced_frame,
                                       encoder,
                                       pcm_frames,
                                       uncompressed_LSBs, LSBs,
                                       INTERLACING_SHIFT,
                                       leftweight,
                                       MSBs0, MSBs1);

                if (interlaced_frame->bits_written(interlaced_frame) <
                    best_interlaced_frame_bits) {
                    best_interlaced_frame_bits =
                        interlaced_frame->bits_written(interlaced_frame);
                    recorder_swap(&best_interlaced_frame,
                                  &interlaced_frame);
                }
            }

            /*write the smallest leftweight to disk*/
            best_interlaced_frame->copy(best_interlaced_frame, bs);
        } else {
            /*extract uncompressed least-significant bits*/
            for (i = 0; i < pcm_frames; i++) {
                LSBs[i] = channel0[i] & lsb_mask;
                MSBs0[i] = channel0[i] >> msb_shift;
            }

            write_non_interlaced_frame(bs,
                                       encoder,
                                       pcm_frames,
                                       uncompressed_LSBs, LSBs,
                                       MSBs0);
        }
    }
}

static void
write_non_interlaced_frame(BitstreamWriter *bs,
                           struct alac_context* encoder,
                           unsigned pcm_frames,
                           unsigned uncompressed_LSBs,
                           const int LSBs[],
                           const int channel0[])
{
    unsigned i;
    unsigned order;
    int qlp_coefficients[MAX_QLP_COEFFS];
    BitstreamRecorder* residual = encoder->residual0;

    residual->reset(residual);

    bs->write(bs, 16, 0);  /*unused*/

    if (pcm_frames == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, uncompressed_LSBs);
    bs->write(bs, 1, 0);   /*is compressed*/

    if (pcm_frames != encoder->options.block_size)
        bs->write(bs, 32, pcm_frames);

    bs->write(bs, 8, 0);   /*no interlacing shift*/
    bs->write(bs, 8, 0);   /*no interlacing leftweight*/

    compute_coefficients(encoder,
                         pcm_frames,
                         channel0,
                         (encoder->bits_per_sample - (uncompressed_LSBs * 8)),
                         &order,
                         qlp_coefficients,
                         (BitstreamWriter*)residual);

    write_subframe_header(bs, order, qlp_coefficients);

    if (uncompressed_LSBs > 0) {
        for (i = 0; i < pcm_frames; i++) {
            bs->write(bs, uncompressed_LSBs * 8, LSBs[i]);
        }
    }

    residual->copy(residual, bs);
}

static void
write_interlaced_frame(BitstreamWriter *bs,
                       struct alac_context* encoder,
                       unsigned pcm_frames,
                       unsigned uncompressed_LSBs,
                       const int LSBs[],
                       unsigned interlacing_shift,
                       unsigned interlacing_leftweight,
                       const int channel0[],
                       const int channel1[])
{
    unsigned i;
    unsigned order0;
    int qlp_coefficients0[MAX_LPC_ORDER];
    unsigned order1;
    int qlp_coefficients1[MAX_LPC_ORDER];
    BitstreamRecorder* residual0 = encoder->residual0;
    BitstreamRecorder* residual1 = encoder->residual1;
    int correlated0[pcm_frames];
    int correlated1[pcm_frames];

    residual0->reset(residual0);
    residual1->reset(residual1);

    bs->write(bs, 16, 0);  /*unused*/

    if (pcm_frames == encoder->options.block_size)
        bs->write(bs, 1, 0);
    else
        bs->write(bs, 1, 1);

    bs->write(bs, 2, uncompressed_LSBs);
    bs->write(bs, 1, 0);   /*is compressed*/

    if (pcm_frames != encoder->options.block_size)
        bs->write(bs, 32, pcm_frames);

    bs->write(bs, 8, interlacing_shift);
    bs->write(bs, 8, interlacing_leftweight);

    correlate_channels(pcm_frames,
                       channel0,
                       channel1,
                       interlacing_shift,
                       interlacing_leftweight,
                       correlated0,
                       correlated1);

    compute_coefficients(encoder,
                         pcm_frames,
                         correlated0,
                         (encoder->bits_per_sample -
                          (uncompressed_LSBs * 8) + 1),
                         &order0,
                         qlp_coefficients0,
                         (BitstreamWriter*)residual0);

    compute_coefficients(encoder,
                         pcm_frames,
                         correlated1,
                         (encoder->bits_per_sample -
                          (uncompressed_LSBs * 8) + 1),
                         &order1,
                         qlp_coefficients1,
                         (BitstreamWriter*)residual1);

    write_subframe_header(bs, order0, qlp_coefficients0);
    write_subframe_header(bs, order1, qlp_coefficients1);

    if (uncompressed_LSBs > 0) {
        for (i = 0; i < pcm_frames * 2; i++) {
            bs->write(bs, uncompressed_LSBs * 8, LSBs[i]);
        }
    }

    residual0->copy(residual0, bs);
    residual1->copy(residual1, bs);
}

static void
correlate_channels(unsigned pcm_frames,
                   const int channel0[],
                   const int channel1[],
                   unsigned interlacing_shift,
                   unsigned interlacing_leftweight,
                   int correlated0[],
                   int correlated1[])
{
    if (interlacing_leftweight > 0) {
        unsigned i;

        for (i = 0; i < pcm_frames; i++) {
            int64_t leftweight = channel0[i] - channel1[i];
            leftweight *= interlacing_leftweight;
            leftweight >>= interlacing_shift;
            correlated0[i] = channel1[i] + (int)leftweight;
            correlated1[i] = channel0[i] - channel1[i];
        }
    } else {
        memcpy(correlated0, channel0, pcm_frames * sizeof(int));
        memcpy(correlated1, channel1, pcm_frames * sizeof(int));
    }
}

static void
compute_coefficients(struct alac_context* encoder,
                     unsigned sample_count,
                     const int samples[],
                     unsigned sample_size,
                     unsigned *order,
                     int qlp_coefficients[],
                     BitstreamWriter *residual)
{
    double windowed_signal[sample_count];
    double autocorrelated[MAX_QLP_COEFFS + 1];

    /*window the input samples*/
    window_signal(sample_count,
                  samples,
                  encoder->tukey_window,
                  windowed_signal);

    /*compute autocorrelation values for samples*/
    autocorrelate(sample_count,
                  windowed_signal,
                  MAX_QLP_COEFFS,
                  autocorrelated);

    if (autocorrelated[0] != 0.0) {
        int qlp_coefficients4[4];
        int qlp_coefficients8[8];
        double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS];
        int residual_values4[sample_count];
        int residual_values8[sample_count];
        BitstreamRecorder *residual_block4 = encoder->residual_block4;
        BitstreamRecorder *residual_block8 = encoder->residual_block8;

        /*transform autocorrelation values to lists of LP coefficients*/
        compute_lp_coefficients(MAX_QLP_COEFFS,
                                autocorrelated,
                                lp_coeff);

        /*quantize LP coefficients at order 4*/
        quantize_coefficients(4, lp_coeff, qlp_coefficients4);

        /*quantize LP coefficients at order 8*/
        quantize_coefficients(8, lp_coeff, qlp_coefficients8);

        /*calculate residuals for QLP coefficients at order 4*/
        calculate_residuals(sample_size,
                            sample_count,
                            samples,
                            4,
                            qlp_coefficients4,
                            residual_values4);

        /*calculate residuals for QLP coefficients at order 8*/
        calculate_residuals(sample_size,
                            sample_count,
                            samples,
                            8,
                            qlp_coefficients8,
                            residual_values8);

        /*encode residual block for QLP coefficients at order 4*/
        residual_block4->reset(residual_block4);
        encode_residuals(encoder,
                         (BitstreamWriter*)residual_block4,
                         sample_size,
                         sample_count,
                         residual_values4);

        /*encode residual block for QLP coefficients at order 8*/
        residual_block8->reset(residual_block8);
        encode_residuals(encoder,
                         (BitstreamWriter*)residual_block8,
                         sample_size,
                         sample_count,
                         residual_values8);

        /*return the LPC coefficients/residual which is the smallest*/
        if (residual_block4->bits_written(residual_block4) <
            (residual_block8->bits_written(residual_block8) + 64)) {
            /*use QLP coefficients with order 4*/
            *order = 4;
            memcpy(qlp_coefficients, qlp_coefficients4, 4 * sizeof(int));
            residual_block4->copy(residual_block4, residual);
        } else {
            /*use QLP coefficients with order 8*/
            *order = 8;
            memcpy(qlp_coefficients, qlp_coefficients8, 8 * sizeof(int));
            residual_block8->copy(residual_block8, residual);
        }
    } else {
        /*all samples are 0, so use a special case*/
        int residual_values4[sample_count];

        *order = 4;
        qlp_coefficients[0] =
        qlp_coefficients[1] =
        qlp_coefficients[2] =
        qlp_coefficients[3] = 0;

        calculate_residuals(sample_size,
                            sample_count,
                            samples,
                            *order,
                            qlp_coefficients,
                            residual_values4);

        encode_residuals(encoder,
                         residual,
                         sample_size,
                         sample_count,
                         residual_values4);
    }
}

static void
tukey_window(double alpha, unsigned block_size, double *window)
{
    unsigned Np = alpha / 2 * block_size - 1;
    unsigned i;
    for (i = 0; i < block_size; i++) {
        if (i <= Np) {
            window[i] = (1 - cos(M_PI * i / Np)) / 2;
        } else if (i >= (block_size - Np - 1)) {
            window[i] = (1 - cos(M_PI * (block_size - i - 1) / Np)) / 2;
        } else {
            window[i] = 1.0;
        }
    }
}

static void
window_signal(unsigned sample_count,
              const int samples[],
              const double window[],
              double windowed_signal[])
{
    unsigned i;
    for (i = 0; i < sample_count; i++) {
        windowed_signal[i] = samples[i] * window[i];
    }
}

static void
autocorrelate(unsigned sample_count,
              const double windowed_signal[],
              unsigned max_lpc_order,
              double autocorrelated[])
{
    unsigned i;

    for (i = 0; i <= max_lpc_order; i++) {
        register double a = 0.0;
        register unsigned j;
        for (j = 0; j < sample_count - i; j++) {
            a += windowed_signal[j] * windowed_signal[j + i];
        }
        autocorrelated[i] = a;
    }
}

static void
compute_lp_coefficients(unsigned max_lpc_order,
                        const double autocorrelated[],
                        double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS])
{
    double k;
    double q;
    unsigned i;
    double error[max_lpc_order];

    k = autocorrelated[1] / autocorrelated[0];
    lp_coeff[0][0] = k;
    error[0] = autocorrelated[0] * (1.0 - pow(k, 2));
    for (i = 1; i < max_lpc_order; i++) {
        double sum = 0.0;
        unsigned j;
        for (j = 0; j < i; j++) {
            sum += lp_coeff[i - 1][j] * autocorrelated[i - j];
        }
        q = autocorrelated[i + 1] - sum;
        k = q / error[i - 1];
        for (j = 0; j < i; j++) {
            lp_coeff[i][j] =
                lp_coeff[i - 1][j] - (k * lp_coeff[i - 1][i - j - 1]);
        }
        lp_coeff[i][i] = k;
        error[i] = error[i - 1] * (1.0 - pow(k, 2));
    }
}

static void
quantize_coefficients(unsigned order,
                      double lp_coeff[MAX_QLP_COEFFS][MAX_QLP_COEFFS],
                      int qlp_coefficients[])
{
    const unsigned precision = 16;
    const int max_coeff = (1 << (precision - 1)) - 1;
    const int min_coeff = -(1 << (precision - 1));
    const int shift = 9;
    unsigned error = 0.0;
    unsigned i;

    for (i = 0; i < order; i++) {
        const double sum = error + lp_coeff[order - 1][i] * (1 << shift);
        const long round_sum = lround(sum);
        qlp_coefficients[i] = (int)(MIN(MAX(round_sum, min_coeff), max_coeff));
        assert(qlp_coefficients[i] <= (1 << (precision - 1)) - 1);
        assert(qlp_coefficients[i] >= -(1 << (precision - 1)));
        error = sum - qlp_coefficients[i];
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
calculate_residuals(unsigned sample_size,
                    unsigned sample_count,
                    const int samples[],
                    unsigned order,
                    const int qlp_coefficients[],
                    int residuals[])
{
    unsigned i = 0;
    int coefficients[order];

    memcpy(coefficients, qlp_coefficients, order * sizeof(int));

    /*first sample always copied verbatim*/
    residuals[0] = samples[i++];

    if (order < 31) {
        unsigned j;

        for (; i < (order + 1); i++) {
            residuals[i] = TRUNCATE_BITS(samples[i] - samples[i - 1],
                                         sample_size);
        }

        for (; i < sample_count; i++) {
            const int base_sample = samples[i - order - 1];
            int64_t lpc_sum = 1 << 8;
            int error;

            for (j = 0; j < order; j++) {
                lpc_sum += ((int64_t)coefficients[j] *
                            (int64_t)(samples[i - j - 1] - base_sample));
            }

            lpc_sum >>= 9;

            error = TRUNCATE_BITS(samples[i] - base_sample - (int)lpc_sum,
                                  sample_size);
            residuals[i] = error;

            if (error > 0) {
                for (j = 0; j < order; j++) {
                    const int diff = (base_sample -
                                      samples[i - order + j]);
                    const int sign = SIGN_ONLY(diff);
                    coefficients[order - j - 1] -= sign;
                    error -= ((diff * sign) >> 9) * (j + 1);
                    if (error <= 0)
                        break;
                }
            } else if (error < 0) {
                for (j = 0; j < order; j++) {
                    const int diff = (base_sample - samples[i - order + j]);
                    const int sign = SIGN_ONLY(diff);
                    coefficients[order - j - 1] += sign;
                    error -= ((diff * -sign) >> 9) * (j + 1);
                    if (error >= 0)
                        break;
                }
            }
        }
    } else {
        /*not sure if this ever happens*/
        for (; i < sample_count; i++) {
            residuals[i] = TRUNCATE_BITS(samples[i] - samples[i - 1],
                                         sample_size);
        }
    }
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
                 BitstreamWriter *residual_block,
                 unsigned sample_size,
                 unsigned residual_count,
                 const int residuals[])
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

    while (i < residual_count) {
        if (residuals[i] >= 0) {
            unsigned_i = (unsigned)(residuals[i] << 1);
        } else {
            unsigned_i = (unsigned)(-residuals[i] << 1) - 1;
        }

        if (unsigned_i >= max_unsigned) {
            /*raise a residual overflow exception
              which means writing an uncompressed frame instead*/
            longjmp(encoder->residual_overflow, 1);
        }

        k = LOG2((history >> 9) + 3);
        k = MIN(k, maximum_k);
        write_residual(residual_block,
                       unsigned_i - sign_modifier,
                       k,
                       sample_size);
        sign_modifier = 0;

        if (unsigned_i <= 0xFFFF) {
            history += ((int)(unsigned_i * history_multiplier) -
                        ((history * (int)history_multiplier) >> 9));
            i++;

            if ((history < 128) && (i < residual_count)) {
                /*handle potential block of 0 residuals*/
                k = 7 - LOG2(history) + ((history + 16) >> 6);
                k = MIN(k, maximum_k);
                zeroes = 0;
                while ((i < residual_count) && (residuals[i] == 0)) {
                    zeroes++;
                    i++;
                }
                write_residual(residual_block, zeroes, k, 16);
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
write_residual(BitstreamWriter* residual_block,
               unsigned value,
               unsigned k,
               unsigned sample_size)
{
    const unsigned MSB = value / ((1 << k) - 1);
    const unsigned LSB = value % ((1 << k) - 1);
    if (MSB > 8) {
        residual_block->write(residual_block, 9, 0x1FF);
        residual_block->write(residual_block, sample_size, value);
    } else {
        residual_block->write_unary(residual_block, 0, MSB);
        if (k > 1) {
            if (LSB > 0) {
                residual_block->write(residual_block, k, LSB + 1);
            } else {
                residual_block->write(residual_block, k - 1, 0);
            }
        }
    }
}


static void
write_subframe_header(BitstreamWriter *bs,
                      unsigned order,
                      const int qlp_coefficients[])
{
    unsigned i;

    bs->write(bs, 4, 0); /*prediction type*/
    bs->write(bs, 4, 9); /*QLP shift needed*/
    bs->write(bs, 3, 4); /*Rice modifier*/
    bs->write(bs, 5, order);
    for (i = 0; i < order; i++) {
        bs->write_signed(bs, 16, qlp_coefficients[i]);
    }
}

static struct alac_frame_size*
dummy_frame_sizes(unsigned block_size, unsigned total_pcm_frames)
{
    struct alac_frame_size *sizes = NULL;

    while (total_pcm_frames) {
        if (total_pcm_frames > block_size) {
            sizes = push_frame_size(sizes, 0, block_size);
            total_pcm_frames -= block_size;
        } else {
            sizes = push_frame_size(sizes, 0, total_pcm_frames);
            total_pcm_frames -= total_pcm_frames;
        }
    }

    reverse_frame_sizes(&sizes);
    return sizes;
}

static unsigned
write_metadata(BitstreamWriter* bw,
               time_t timestamp,
               unsigned sample_rate,
               unsigned channels,
               unsigned bits_per_sample,
               unsigned total_pcm_frames,
               unsigned block_size,
               unsigned history_multiplier,
               unsigned initial_history,
               unsigned maximum_K,
               const struct alac_frame_size *frame_sizes,
               unsigned frames_offset,
               const char encoder_version[])
{
    const qt_time_t qt_timestamp = time_to_mac_utc(timestamp);
    const unsigned geometry[9] = {0x10000, 0x0, 0x0, 0x0, 0x10000,
                                  0x0, 0x0, 0x0, 0x40000000};

    /*total size of all metadata atoms*/
    unsigned total_size = 0;

    /*the largest ALAC frame size, in bytes*/
    unsigned max_coded_frame_size = 0;

    /*bitrate in bits-per-second*/
    unsigned long long bitrate = 0;

    /*number of ALAC frames per chunk*/
    const unsigned alac_frames_per_chunk = 5;

    /*current chunk number*/
    unsigned current_chunk = 0;

    /*size of the current chunk, in ALAC frames*/
    unsigned chunk_size = 0;

    /*some atoms to generate*/
    struct qt_atom *ftyp;
    struct qt_atom *stts = qt_stts_new(0, 0);
    struct qt_atom *stsc = qt_stsc_new(0, 0);
    struct qt_atom *stsz = qt_stsz_new(0, 0, 0);
    struct qt_atom *stco = qt_stco_new(0, 0);
    struct qt_atom *stbl;
    struct qt_atom *moov;
    struct qt_atom *meta;
    struct qt_atom *free;

    const struct alac_frame_size *size;
    struct stsc_entry *latest_entry;

    /*walk through frames to determine max coded frame size, bitrate
      and other stbl sub-atom parameters*/
    for (size = frame_sizes; size; size = size->next) {
        bitrate += (size->byte_size * 8);

        if (size->byte_size > max_coded_frame_size) {
            max_coded_frame_size = size->byte_size;
        }
        qt_stts_add_time(stts, size->pcm_frames_size);

        if (chunk_size == 0) {
            /*add a new offset at the start of a chunk*/
            qt_stco_add_offset(stco, frames_offset);
        }

        if ((chunk_size += 1) == alac_frames_per_chunk) {
            /*add a new stsc entry*/
            latest_entry = qt_stsc_latest_entry(stsc);
            current_chunk += 1;
            if ((!latest_entry) ||
                (latest_entry->frames_per_chunk != chunk_size)) {
                /*add a new entry*/
                qt_stsc_add_chunk_size(stsc,
                                       current_chunk,
                                       chunk_size,
                                       1);
            }
            chunk_size = 0;
        }
        qt_stsz_add_size(stsz, size->byte_size);
        frames_offset += size->byte_size;
    }
    latest_entry = qt_stsc_latest_entry(stsc);
    if ((chunk_size > 0) &&
        ((!latest_entry) || (latest_entry->frames_per_chunk != chunk_size))) {
        /*add a new stsc entry*/
        current_chunk += 1;
        qt_stsc_add_chunk_size(stsc, current_chunk, chunk_size, 1);
    }

    /*determine bitrate based on size of mdat contents,
      total PCM frames and sample rate*/
    bitrate *= sample_rate;
    bitrate /= total_pcm_frames;

    /*ftyp atom*/
    ftyp = qt_ftyp_new((uint8_t*)"M4A ", 0, 4,
                       (uint8_t*)"M4A ",
                       (uint8_t*)"mp42",
                       (uint8_t*)"isom",
                       (uint8_t*)"\x00\x00\x00\x00");
    ftyp->build(ftyp, bw);
    total_size += ftyp->size(ftyp);
    ftyp->free(ftyp);

    /*stbl atom*/
    stbl = qt_tree_new("stbl", 5,
      qt_stsd_new(0, 0, 1,
        qt_alac_new(1,
                    0,
                    0,
                    (uint8_t*)"\x00\x00\x00\x00",
                    channels,
                    bits_per_sample,
                    0,
                    0,
                    0xAC440000,
                    qt_sub_alac_new(block_size,
                                    bits_per_sample,
                                    history_multiplier,
                                    initial_history,
                                    maximum_K,
                                    channels,
                                    0xFF,
                                    max_coded_frame_size,
                                    (unsigned)bitrate,
                                    sample_rate))),
      stts,
      stsc,
      stsz,
      stco);

    /*meta atom*/
    meta = qt_meta_new(0, 0, 3,
      qt_hdlr_new(0, 0,
                  "\x00\x00\x00\x00",
                  "mdir",
                  "appl",
                  0, 0, 2, (uint8_t*)"\x00\xFF"),
      qt_tree_new("ilst", 1,
        qt_tree_new("\xA9""too", 1,
          qt_data_new(1,
                      (unsigned)strlen(encoder_version),
                      (uint8_t*)encoder_version))),
      qt_free_new(4096));

    /*moov atom*/
    moov = qt_tree_new("moov", 3,
      qt_mvhd_new(0, 0, qt_timestamp, qt_timestamp, sample_rate,
                  total_pcm_frames, 0x10000, 0x100, geometry,
                  0, 0, 0, 0, 2),
      qt_tree_new("trak", 2,
        qt_tkhd_new(0, 7, qt_timestamp, qt_timestamp, 1,
                    total_pcm_frames, 0, 0, 0x100, geometry, 0, 0),
        qt_tree_new("mdia", 3,
          qt_mdhd_new(0, 0, qt_timestamp, qt_timestamp,
                      sample_rate, total_pcm_frames, "und", 0),
          qt_hdlr_new(0, 0,
                      "\x00\x00\x00\x00",
                      "soun",
                      "\x00\x00\x00\x00",
                      0, 0, 2, (uint8_t*)"\x00\x00"),
          qt_tree_new("minf", 3,
            qt_smhd_new(0, 0, 0),
            qt_tree_new("dinf", 1,
              qt_dref_new(0, 0, 1,
                qt_leaf_new("url ", 4, (uint8_t*)"\x00\x00\x00\x01"))),
            stbl))),
      qt_tree_new("udta", 1,
        meta));
    moov->build(moov, bw);
    total_size += moov->size(moov);
    moov->free(moov);

    /*free atom*/
    free = qt_free_new(4096);
    free->build(free, bw);
    total_size += free->size(free);
    free->free(free);

    return total_size;
}

#ifdef STANDALONE
#include <getopt.h>
#include <errno.h>

int main(int argc, char *argv[]) {
    const char encoder_version[] = "Python Audio Tools";
    struct PCMReader *pcmreader = NULL;
    char *output_filename = NULL;
    FILE *output_file = NULL;
    BitstreamWriter *output = NULL;
    unsigned total_pcm_frames = 0;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;

    int block_size = 4096;
    int initial_history = 10;
    int history_multiplier = 40;
    int maximum_k = 14;

    struct alac_frame_size *frame_sizes;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"total-pcm-frames",        required_argument, NULL, 'T'},
        {"block-size",              required_argument, NULL, 'B'},
        {"initial-history",         required_argument, NULL, 'I'},
        {"history-multiplier",      required_argument, NULL, 'M'},
        {"maximum-K",               required_argument, NULL, 'K'},
        {NULL,                      no_argument, NULL, 0}};
    const static char* short_opts = "-hc:r:b:T:B:M:K:";

    while ((c = getopt_long(argc,
                            argv,
                            short_opts,
                            long_opts,
                            NULL)) != -1) {
        switch (c) {
        case 1:
            if (output_filename == NULL) {
                output_filename = optarg;
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
        case 'T':
            if (((total_pcm_frames = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --total-pcm-frames \"%s\"\n", optarg);
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
            printf("-T, --total-pcm-frames=#    total PCM frames of input\n");
            printf("-B, --block-size=#          block size\n");
            printf("-I, --initial-history=#     initial history\n");
            printf("-M, --history-multiplier=#  history multiplier\n");
            printf("-K, --maximum-K=#           maximum K\n");
            return 0;
        default:
            break;
        }
    }
    if (output_filename) {
        errno = 0;
        if ((output_file = fopen(output_filename, "wb")) == NULL) {
            fprintf(stderr, "%s: %s", output_filename, strerror(errno));
            return 1;
        } else {
            output = bw_open(output_file, BS_BIG_ENDIAN);
        }
    } else {
        fputs("exactly 1 output file required\n", stderr);
        return 1;
    }

    assert(channels > 0);
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16) ||
           (bits_per_sample == 24));
    assert(sample_rate > 0);

    pcmreader = pcmreader_open_raw(stdin,
                                   sample_rate,
                                   channels,
                                   0,
                                   bits_per_sample,
                                   1, 1);

    pcmreader_display(pcmreader, stderr);
    fputs("\n", stderr);
    fprintf(stderr, "total PCM frames   %u\n", total_pcm_frames);
    fprintf(stderr, "block size         %d\n", block_size);
    fprintf(stderr, "initial history    %d\n", initial_history);
    fprintf(stderr, "history multiplier %d\n", history_multiplier);
    fprintf(stderr, "maximum K          %d\n", maximum_k);

    frame_sizes = encode_alac(output,
                              pcmreader,
                              total_pcm_frames,
                              block_size,
                              initial_history,
                              history_multiplier,
                              maximum_k,
                              encoder_version);

    output->close(output);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    if (frame_sizes) {
        struct alac_frame_size *sizes;
        for (sizes = frame_sizes; sizes; sizes = sizes->next) {
            fprintf(stderr, "frame size : %u bytes, %u samples\n",
                    sizes->byte_size, sizes->pcm_frames_size);
        }
        free_alac_frame_sizes(frame_sizes);
        return 0;
    } else {
        fputs("*** Error during encoding\n", stderr);
        return 1;
    }
}
#endif
