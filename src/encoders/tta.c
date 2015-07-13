#include "tta.h"
#include "../common/tta_crc.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

struct prediction_params {
    unsigned shift;
    int previous_sample;
};

struct filter_params {
    unsigned shift;
    int previous_residual;
    int round;
    int qm[8];
    int dx[8];
    int dl[8];
};

struct residual_params {
    int k0;
    int k1;
    int sum0;
    int sum1;
};

/*******************************
 * private function signatures *
 *******************************/

static void
encode_frame(unsigned bits_per_sample,
             unsigned channels,
             unsigned block_size,
             const int samples[],
             BitstreamWriter *output);

static void
correlate_channels(unsigned channels,
                   const int samples[],
                   int correlated[]);

static void
init_prediction_params(unsigned bits_per_sample,
                       struct prediction_params *params);

static int
run_prediction(struct prediction_params *params, int correlated);

static void
init_filter_params(unsigned bits_per_sample,
                   struct filter_params *params);

static int
run_filter(struct filter_params *params, int predicted);

static void
init_residual_params(struct residual_params *params);

static void
write_residual(struct residual_params *params,
               int residual,
               BitstreamWriter *output);

static struct tta_frame_size*
append_size(struct tta_frame_size *stack, unsigned size);

static void
reverse_frame_sizes(struct tta_frame_size **stack);

/***********************************
 * public function implementations *
 ***********************************/

struct tta_frame_size*
ttaenc_encode_tta_frames(struct PCMReader *pcmreader,
                         BitstreamWriter *output)
{
    struct tta_frame_size *frame_sizes = NULL;
    const unsigned default_block_size = (pcmreader->sample_rate * 256) / 245;
    unsigned block_size;
    unsigned frame_size = 0;
    int *samples = malloc(default_block_size *
                          pcmreader->channels *
                          sizeof(int));

    output->add_callback(output, (bs_callback_f)byte_counter, &frame_size);

    while ((block_size =
            pcmreader->read(pcmreader, default_block_size, samples)) > 0) {
        encode_frame(pcmreader->bits_per_sample,
                     pcmreader->channels,
                     block_size,
                     samples,
                     output);
        frame_sizes = append_size(frame_sizes, frame_size);
        frame_size = 0;
    }

    output->pop_callback(output, NULL);

    free(samples);

    if (pcmreader->status == PCM_OK) {
        /*if not error, reverse frame lengths stack and return it*/
        reverse_frame_sizes(&frame_sizes);
        return frame_sizes;
    } else {
        /*otherwise, delete frame lengths stack and return NULL*/
        free_tta_frame_sizes(frame_sizes);
        return NULL;
    }

}

void
free_tta_frame_sizes(struct tta_frame_size *frame_sizes)
{
    while (frame_sizes) {
        struct tta_frame_size *next = frame_sizes->next;
        free(frame_sizes);
        frame_sizes = next;
    }
}

/************************************
 * private function implementations *
 ************************************/

static void
encode_frame(unsigned bits_per_sample,
             unsigned channels,
             unsigned block_size,
             const int samples[],
             BitstreamWriter *output)
{
    struct prediction_params prediction_params[channels];
    struct filter_params filter_params[channels];
    struct residual_params residual_params[channels];
    uint32_t crc32 = 0xFFFFFFFF;
    unsigned c;

    /*initialize per-channel parameters*/
    for (c = 0; c < channels; c++) {
        init_prediction_params(bits_per_sample, prediction_params + c);
        init_filter_params(bits_per_sample, filter_params + c);
        init_residual_params(residual_params + c);
    }

    output->add_callback(output, (bs_callback_f)tta_crc32, &crc32);

    for (; block_size; block_size--) {
        int correlated[channels];

        correlate_channels(channels, samples, correlated);

        for (c = 0; c < channels; c++) {
            write_residual(
                residual_params + c,
                run_filter(
                    filter_params + c,
                    run_prediction(
                        prediction_params + c,
                        correlated[c])),
                output);
        }

        samples += channels;
    }

    output->byte_align(output);
    output->pop_callback(output, NULL);
    output->write(output, 32, crc32 ^ 0xFFFFFFFF);
}

static void
correlate_channels(unsigned channels,
                   const int samples[],
                   int correlated[])
{
    assert(channels > 0);
    if (channels == 1) {
        correlated[0] = samples[0];
    } else {
        unsigned c;
        for (c = 0; c < (channels - 1); c++) {
            correlated[c] = samples[c + 1] - samples[c];
        }
        /*this should round toward zero*/
        correlated[channels - 1] =
            samples[channels - 1] - (correlated[channels - 2] / 2);
    }
}

static void
init_prediction_params(unsigned bits_per_sample,
                       struct prediction_params *params)
{
    switch (bits_per_sample) {
    case 8:
        params->shift = 4;
        break;
    case 16:
        params->shift = 5;
        break;
    case 24:
        params->shift = 5;
        break;
    }
    params->previous_sample = 0;
}

static int
run_prediction(struct prediction_params *params, int correlated)
{
    const int predicted =
        correlated - (((params->previous_sample << params->shift) -
                      params->previous_sample) >> params->shift);
    params->previous_sample = correlated;
    return predicted;
}

static void
init_filter_params(unsigned bits_per_sample,
                   struct filter_params *params)
{
    switch (bits_per_sample) {
    case 8:
        params->shift = 10;
        break;
    case 16:
        params->shift = 9;
        break;
    case 24:
        params->shift = 10;
        break;
    }
    params->previous_residual = 0;
    params->round = 1 << (params->shift - 1);
    params->qm[0] =
    params->qm[1] =
    params->qm[2] =
    params->qm[3] =
    params->qm[4] =
    params->qm[5] =
    params->qm[6] =
    params->qm[7] = 0;
    params->dx[0] =
    params->dx[1] =
    params->dx[2] =
    params->dx[3] =
    params->dx[4] =
    params->dx[5] =
    params->dx[6] =
    params->dx[7] = 0;
    params->dl[0] =
    params->dl[1] =
    params->dl[2] =
    params->dl[3] =
    params->dl[4] =
    params->dl[5] =
    params->dl[6] =
    params->dl[7] = 0;
}

static inline int
sign(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}

static int
run_filter(struct filter_params *params, int predicted)
{
    const int previous_sign = sign(params->previous_residual);
    int32_t sum = params->round;
    int residual = predicted;

    sum += params->dl[0] * (params->qm[0] += previous_sign * params->dx[0]);
    sum += params->dl[1] * (params->qm[1] += previous_sign * params->dx[1]);
    sum += params->dl[2] * (params->qm[2] += previous_sign * params->dx[2]);
    sum += params->dl[3] * (params->qm[3] += previous_sign * params->dx[3]);
    sum += params->dl[4] * (params->qm[4] += previous_sign * params->dx[4]);
    sum += params->dl[5] * (params->qm[5] += previous_sign * params->dx[5]);
    sum += params->dl[6] * (params->qm[6] += previous_sign * params->dx[6]);
    sum += params->dl[7] * (params->qm[7] += previous_sign * params->dx[7]);

    residual -= (sum >> params->shift);
    params->previous_residual = residual;

    params->dx[0] = params->dx[1];
    params->dx[1] = params->dx[2];
    params->dx[2] = params->dx[3];
    params->dx[3] = params->dx[4];
    params->dx[4] = params->dl[4] >= 0 ? 1 : -1;
    params->dx[5] = params->dl[5] >= 0 ? 2 : -2;
    params->dx[6] = params->dl[6] >= 0 ? 2 : -2;
    params->dx[7] = params->dl[7] >= 0 ? 4 : -4;
    params->dl[0] = params->dl[1];
    params->dl[1] = params->dl[2];
    params->dl[2] = params->dl[3];
    params->dl[3] = params->dl[4];
    params->dl[4] =
        -(params->dl[5]) + (-(params->dl[6]) + (predicted - params->dl[7]));
    params->dl[5] = -(params->dl[6]) + (predicted - params->dl[7]);
    params->dl[6] = predicted - params->dl[7];
    params->dl[7] = predicted;

    return residual;
}

static void
init_residual_params(struct residual_params *params)
{
    params->k0 = params->k1 = 10;
    params->sum0 = params->sum1 = 1 << 14;
}

static inline int
adjustment(unsigned sum, unsigned k)
{
    if ((k > 0) && (1 << (k + 4) > sum)) {
        return -1;
    } else if (sum > (1 << (k + 5))) {
        return 1;
    } else {
        return 0;
    }
}

static void
write_residual(struct residual_params *params,
               int residual,
               BitstreamWriter *output)
{
    const unsigned unsigned_ =
        residual > 0 ? (residual * 2) - 1 : -(residual * 2);
    if (unsigned_ < (1 << params->k0)) {
        output->write_unary(output, 0, 0);
        output->write(output, params->k0, unsigned_);
    } else {
        const unsigned shifted = unsigned_ - (1 << params->k0);
        const unsigned MSB = 1 + (shifted >> params->k1);
        const unsigned LSB = shifted - ((MSB - 1) << params->k1);
        output->write_unary(output, 0, MSB);
        output->write(output, params->k1, LSB);
        params->sum1 += (shifted - (params->sum1 >> 4));
        params->k1 += adjustment(params->sum1, params->k1);
    }

    params->sum0 += (unsigned_ - (params->sum0 >> 4));
    params->k0 += adjustment(params->sum0, params->k0);
}

static struct tta_frame_size*
append_size(struct tta_frame_size *stack, unsigned size)
{
    struct tta_frame_size *frame_size = malloc(sizeof(struct tta_frame_size));
    frame_size->byte_size = size;
    frame_size->next = stack;
    return frame_size;
}

static void
reverse_frame_sizes(struct tta_frame_size **stack)
{
    struct tta_frame_size *reversed = NULL;
    struct tta_frame_size *top = *stack;
    while (top) {
        *stack = (*stack)->next;
        top->next = reversed;
        reversed = top;
        top = *stack;
    }
    *stack = reversed;
}

#ifndef STANDALONE

#if PY_MAJOR_VERSION >= 3
#ifndef PyInt_FromLong
#define PyInt_FromLong PyLong_FromLong
#endif
#endif

PyObject*
encoders_encode_tta(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    PyObject *file_obj;
    struct PCMReader *pcmreader;
    BitstreamWriter *output;
    struct tta_frame_size *frame_sizes;
    static char *kwlist[] = {"file", "pcmreader", NULL};

    if (!PyArg_ParseTupleAndKeywords(
            args, keywds, "OO&", kwlist,
            &file_obj,
            py_obj_to_pcmreader,
            &pcmreader)) {
        return NULL;
    }

    output = bw_open_external(file_obj,
                              BS_LITTLE_ENDIAN,
                              4096,
                              (ext_write_f)bw_write_python,
                              (ext_setpos_f)bs_setpos_python,
                              (ext_getpos_f)bs_getpos_python,
                              (ext_free_pos_f)bs_free_pos_python,
                              (ext_seek_f)bs_fseek_python,
                              (ext_flush_f)bw_flush_python,
                              (ext_close_f)bs_close_python,
                              (ext_free_f)bs_free_python_nodecref);

    frame_sizes = ttaenc_encode_tta_frames(pcmreader, output);

    pcmreader->del(pcmreader);

    if (frame_sizes) {
        PyObject *frame_size_list = PyList_New(0);
        struct tta_frame_size *sizes;
        for (sizes = frame_sizes; sizes; sizes = sizes->next) {
            PyObject *value = Py_BuildValue("I", sizes->byte_size);
            if (!PyList_Append(frame_size_list, value)) {
                Py_DECREF(value);
            } else {
                Py_DECREF(sizes);
                Py_DECREF(value);
                free_tta_frame_sizes(frame_sizes);
                return NULL;
            }
        }
        free_tta_frame_sizes(frame_sizes);
        output->flush(output);
        output->free(output);
        return frame_size_list;
    } else {
        /*some read error occurred during encoding*/
        output->free(output);
        PyErr_SetString(PyExc_IOError, "read error during encoding");
        return NULL;
    }
}
#endif


#ifdef STANDALONE
#include <getopt.h>
#include <string.h>
#include <errno.h>

static void
write_header(unsigned bits_per_sample,
             unsigned sample_rate,
             unsigned channels,
             unsigned total_pcm_frames,
             BitstreamWriter *output);

static void
write_seektable(const struct tta_frame_size *frame_sizes,
                BitstreamWriter *output);


static inline unsigned
div_ceil(unsigned x, unsigned y)
{
    ldiv_t div = ldiv((long)x, (long)y);
    return div.rem ? ((unsigned)div.quot + 1) : (unsigned)div.quot;
}


int
main(int argc, char* argv[]) {
    char* output_filename = NULL;
    FILE *output_file;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;
    unsigned total_pcm_frames = 0;

    struct PCMReader *pcmreader;
    BitstreamWriter *output;
    bw_pos_t *seektable_pos;
    unsigned i;
    struct tta_frame_size *frame_sizes;

    unsigned total_tta_frames;
    unsigned block_size;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"total-pcm-frames",        required_argument, NULL, 'T'},
        {NULL,                      no_argument,       NULL, 0}};
    const static char* short_opts = "-hc:r:b:T:";

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
            if (((total_pcm_frames = strtoul(optarg, NULL, 10)) == 0) &&
                errno) {
                printf("invalid --total-pcm-frames \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: ttaenc [options] <output.tta>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("-T, --total-pcm-frames=#  total PCM frames of input\n");
            return 0;
        default:
            break;
        }
    }

    errno = 0;
    if (output_filename == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    } else if ((output_file = fopen(output_filename, "wb")) == NULL) {
        fprintf(stderr, "*** Error %s: %s\n", output_filename, strerror(errno));
        return 1;
    }

    assert(channels > 0);
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16) ||
           (bits_per_sample == 24));
    assert(sample_rate > 0);
    assert(total_pcm_frames > 0);

    block_size = (sample_rate * 256) / 245;
    total_tta_frames = div_ceil(total_pcm_frames, block_size);

    printf("total TTA frames : %u\n", total_tta_frames);

    pcmreader = pcmreader_open_raw(stdin,
                                   sample_rate,
                                   channels,
                                   0,
                                   bits_per_sample,
                                   1, 1);
    output = bw_open(output_file, BS_LITTLE_ENDIAN);

    pcmreader_display(pcmreader, stderr);

    /*write TTA header*/
    write_header(bits_per_sample,
                 sample_rate,
                 channels,
                 total_pcm_frames,
                 output);

    /*write dummy seektable*/
    seektable_pos = output->getpos(output);
    for (i = 0; i < total_tta_frames; i++) {
        output->write(output, 32, 0);
    }
    output->write(output, 32, 0);

    /*write TTA frames*/
    frame_sizes = ttaenc_encode_tta_frames(pcmreader, output);

    /*write finalized seektable*/
    output->setpos(output, seektable_pos);
    write_seektable(frame_sizes, output);
    free_tta_frame_sizes(frame_sizes);
    seektable_pos->del(seektable_pos);

    /*close output file and PCMReader*/
    output->close(output);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}

static void
write_header(unsigned bits_per_sample,
             unsigned sample_rate,
             unsigned channels,
             unsigned total_pcm_frames,
             BitstreamWriter *output)
{
    const uint8_t signature[] = "TTA1";
    uint32_t crc32 = 0xFFFFFFFF;
    output->add_callback(output, (bs_callback_f)tta_crc32, &crc32);
    output->write_bytes(output, signature, 4);
    output->write(output, 16, 1);
    output->write(output, 16, channels);
    output->write(output, 16, bits_per_sample);
    output->write(output, 32, sample_rate);
    output->write(output, 32, total_pcm_frames);
    output->pop_callback(output, NULL);
    output->write(output, 32, crc32 ^ 0xFFFFFFFF);
}

static void
write_seektable(const struct tta_frame_size *frame_sizes,
                BitstreamWriter *output)
{
    uint32_t crc32 = 0xFFFFFFFF;
    output->add_callback(output, (bs_callback_f)tta_crc32, &crc32);
    for (; frame_sizes; frame_sizes = frame_sizes->next) {
        output->write(output, 32, frame_sizes->byte_size);
    }
    output->pop_callback(output, NULL);
    output->write(output, 32, crc32 ^ 0xFFFFFFFF);
}


#include "../common/tta_crc.c"
#endif
