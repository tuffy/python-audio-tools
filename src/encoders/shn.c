#ifndef STANDALONE
#include <Python.h>
#endif
#include <string.h>
#include "shn.h"

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

#ifndef STANDALONE
PyObject*
encoders_encode_shn(PyObject *dummy,
                    PyObject *args, PyObject *keywds)
{
    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "is_big_endian",
                             "signed_samples",
                             "header_data",
                             "footer_data",
                             "block_size",
                             NULL};
    char *filename;
    FILE *output_file;
    BitstreamWriter* writer;
    struct PCMReader* pcmreader;
    int is_big_endian = 0;
    int signed_samples = 0;
    char* header_data;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t header_size;
#else
    int header_size;
#endif
    char* footer_data = NULL;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t footer_size = 0;
#else
    int footer_size = 0;
#endif
    unsigned block_size = 256;
    unsigned bytes_written = 0;
    unsigned i;

    /*fetch arguments*/
    if (!PyArg_ParseTupleAndKeywords(args, keywds, "sO&iis#|s#I",
                                     kwlist,
                                     &filename,
                                     py_obj_to_pcmreader,
                                     &pcmreader,
                                     &is_big_endian,
                                     &signed_samples,
                                     &header_data,
                                     &header_size,

                                     &footer_data,
                                     &footer_size,
                                     &block_size))
        return NULL;

    /*ensure PCMReader is compatible with Shorten*/
    if ((pcmreader->bits_per_sample != 8) &&
        (pcmreader->bits_per_sample != 16)) {
        pcmreader->del(pcmreader);
        PyErr_SetString(PyExc_ValueError, "unsupported bits per sample");
        return NULL;
    }

    /*open given filename for writing*/
    if ((output_file = fopen(filename, "wb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        pcmreader->del(pcmreader);
        return NULL;
    } else {
        writer = bw_open(output_file, BS_BIG_ENDIAN);
    }

    /*write magic number and version*/
    writer->build(writer, "4b 8u", "ajkg", 2);

    writer->add_callback(writer, (bs_callback_f)byte_counter, &bytes_written);

    /*write Shorten header*/
    write_header(writer,
                 pcmreader->bits_per_sample,
                 is_big_endian,
                 signed_samples,
                 pcmreader->channels,
                 block_size);

    /*issue initial VERBATIM command with header data*/
    write_unsigned(writer, COMMAND_SIZE, FN_VERBATIM);
    write_unsigned(writer, VERBATIM_SIZE, header_size);
    for (i = 0; i < header_size; i++)
        write_unsigned(writer, VERBATIM_BYTE_SIZE, (uint8_t)header_data[i]);

    /*process PCM frames*/
    if (encode_audio(writer, pcmreader, signed_samples, block_size))
        goto error;

    /*if there's footer data, issue a VERBATIM command for it*/
    if ((footer_data != NULL) && (footer_size > 0)) {
        write_unsigned(writer, COMMAND_SIZE, FN_VERBATIM);
        write_unsigned(writer, VERBATIM_SIZE, footer_size);
        for (i = 0; i < footer_size; i++)
            write_unsigned(writer, VERBATIM_BYTE_SIZE, (uint8_t)footer_data[i]);
    }

    /*issue QUIT command*/
    write_unsigned(writer, COMMAND_SIZE, FN_QUIT);

    /*pad output (not including header) to a multiple of 4 bytes*/
    writer->byte_align(writer);
    while ((bytes_written % 4) != 0) {
        writer->write(writer, 8, 0);
    }

    /*deallocate temporary buffers and close files*/
    pcmreader->del(pcmreader);
    writer->close(writer);

    Py_INCREF(Py_None);
    return Py_None;
 error:
    pcmreader->del(pcmreader);
    writer->close(writer);

    return NULL;
}
#endif

static void
write_header(BitstreamWriter* bs,
             unsigned bits_per_sample,
             int is_big_endian,
             int signed_samples,
             unsigned channels,
             unsigned block_size)
{
    if (bits_per_sample == 8)
        if (signed_samples)
            write_long(bs, 1); /*signed, 8-bit*/
        else
            write_long(bs, 2); /*unsigned, 8-bit*/
    else
        if (signed_samples)
            if (is_big_endian)
                write_long(bs, 3); /*signed, 16-bit, big-endian*/
            else
                write_long(bs, 5); /*signed, 16-bit, little-endian*/
        else
            if (is_big_endian)
                write_long(bs, 4); /*unsigned, 16-bit, big-endian*/
            else
                write_long(bs, 6); /*unsigned, 16-bit, little-endian*/
    write_long(bs, channels);
    write_long(bs, block_size);
    write_long(bs, 0); /*maximum LPC*/
    write_long(bs, 0); /*mean count*/
    write_long(bs, 0); /*bytes to skip*/
}

static int
encode_audio(BitstreamWriter* bs,
             struct PCMReader* pcmreader,
             int signed_samples,
             unsigned block_size)
{
    unsigned left_shift = 0;
    int sign_adjustment;

    int frame[block_size * pcmreader->channels];
    int *wrapped[pcmreader->channels];
    unsigned frames_read;
    unsigned c;

    /*allocate temporary wrapped samples buffer*/
    for (c = 0; c < pcmreader->channels; c++) {
        wrapped[c] = calloc(3, sizeof(int));
    }

    if (!signed_samples) {
        sign_adjustment = 1 << (pcmreader->bits_per_sample - 1);
    } else {
        sign_adjustment = 0;
    }

    while ((frames_read = pcmreader->read(pcmreader,
                                          block_size,
                                          frame)) > 0) {
        if (frames_read != block_size) {
            /*PCM frame count has changed, so issue BLOCKSIZE command*/
            block_size = frames_read;
            write_unsigned(bs, COMMAND_SIZE, FN_BLOCKSIZE);
            write_long(bs, block_size);
        }

        for (c = 0; c < pcmreader->channels; c++) {
            unsigned i;
            int channel[frames_read];

            get_channel_data(frame,
                             c,
                             pcmreader->channels,
                             frames_read,
                             channel);

            /*convert signed samples to unsigned, if necessary*/
            if (sign_adjustment != 0)
                for (i = 0; i < frames_read; i++)
                    channel[i] += sign_adjustment;

            if (all_zero(frames_read, channel)) {
                /*write ZERO command and wrap channel for next set*/
                write_unsigned(bs, COMMAND_SIZE, FN_ZERO);
            } else {
                unsigned diff = 1;
                unsigned energy = 0;
                const unsigned wasted_BPS = wasted_bits(frames_read, channel);
                int residual[frames_read];

                if (wasted_BPS != left_shift) {
                    /*issue BITSHIFT comand*/
                    left_shift = wasted_BPS;
                    write_unsigned(bs, COMMAND_SIZE, FN_BITSHIFT);
                    write_unsigned(bs, BITSHIFT_SIZE, left_shift);
                }

                /*apply left shift to channel data*/
                if (left_shift) {
                    for (i = 0; i < frames_read; i++) {
                        channel[i] >>= left_shift;
                    }
                }

                /*calculate best DIFF, energy and residuals for shifted data*/
                calculate_best_diff(frames_read,
                                    channel,
                                    wrapped[c],
                                    &diff,
                                    &energy,
                                    residual);

                /*issue DIFF command*/
                write_unsigned(bs, COMMAND_SIZE, diff);
                write_unsigned(bs, ENERGY_SIZE, energy);
                for (i = 0; i < frames_read; i++)
                    write_signed(bs, energy, residual[i]);
            }
        }
    }

    /*deallocate temporary wrapped samples buffer*/
    for (c = 0; c < pcmreader->channels; c++) {
        free(wrapped[c]);
    }

    /*return result*/
    return (pcmreader->status == PCM_OK) ? 0 : 1;
}

static int
all_zero(unsigned block_size, const int samples[])
{
    while (block_size) {
        if (samples[0] != 0) {
            return 0;
        } else {
            block_size -= 1;
            samples += 1;
        }
    }
    return 1;
}

static int
wasted_bits(unsigned block_size, const int samples[])
{
    unsigned i;
    unsigned wasted_bits_per_sample = UINT_MAX;

    for (i = 0; i < block_size; i++) {
        int sample = samples[i];
        if (sample != 0) {
            unsigned wasted_bits;
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

    if (wasted_bits_per_sample == UINT_MAX) {
        return 0;
    } else {
        return wasted_bits_per_sample;
    }
}

static void
calculate_best_diff(unsigned block_size,
                    const int samples[],
                    int prev_samples[3],
                    unsigned* diff,
                    unsigned* energy,
                    int residual[])
{
    int buffer[block_size + 3];
    int delta1[block_size + 2];
    int delta2[block_size + 1];
    int delta3[block_size];
    unsigned sum1;
    unsigned sum2;
    unsigned sum3;

    *energy = 0;

    /*combine samples and previous samples into a unified buffer*/
    memcpy(buffer, prev_samples, 3 * sizeof(int));
    memcpy(buffer + 3, samples, block_size * sizeof(int));

    /*determine delta1 from samples and previous samples*/
    compute_delta(block_size + 3, buffer, delta1);

    /*determine delta2 from delta1*/
    compute_delta(block_size + 2, delta1, delta2);

    /*determine delta3 from delta2*/
    compute_delta(block_size + 1, delta2, delta3);

    /*determine delta sums from deltas*/
    sum1 = delta_sum(block_size + 2, delta1);
    sum2 = delta_sum(block_size + 1, delta2);
    sum3 = delta_sum(block_size, delta3);

    /*determine DIFF command from minimum sum*/
    if (sum1 < MIN(sum2, sum3)) {
        /*use DIFF1 command*/
        *diff = 1;

        /*calculate energy from minimum sum*/
        *energy = ceil(log2((double)sum1 / (double)block_size + 2));

        /*residuals are determined from delta values*/
        memcpy(residual, delta1 + 2, block_size * sizeof(int));
    } else if (sum2 < sum3) {
        /*use DIFF2 command*/
        *diff = 2;

        /*calculate energy from minimum sum*/
        *energy = ceil(log2((double)sum2 / (double)block_size + 1));

        /*residuals are determined from delta values*/
        memcpy(residual, delta2 + 1, block_size * sizeof(int));
    } else {
        /*use DIFF3 command*/
        *diff = 3;

        /*calculate energy from minimum sum*/
        *energy = ceil(log2((double)sum3 / (double)block_size));

        /*residuals are determined from delta values*/
        memcpy(residual, delta3, block_size * sizeof(int));
    }

    /*wrap the trailing 3 samples to prev_samples for next time*/
    memcpy(prev_samples, buffer + block_size, 3 * sizeof(int));
}

static void
compute_delta(unsigned samples_count,
              const int samples[],
              int delta[])
{
    for (samples_count--; samples_count; samples_count--) {
        delta[0] = samples[1] - samples[0];
        delta += 1;
        samples += 1;
    }
}

static unsigned
delta_sum(unsigned samples_count, const int samples[])
{
    unsigned accumulator = 0;
    for (; samples_count; samples_count--) {
        accumulator += abs(samples[0]);
        samples += 1;
    }
    return accumulator;
}

static void
write_unsigned(BitstreamWriter* bs, unsigned c, unsigned value)
{
    const unsigned MSB = value >> c;
    const unsigned LSB = value - (MSB << c);
    bs->write_unary(bs, 1, MSB);
    bs->write(bs, c, LSB);
}

static void
write_signed(BitstreamWriter* bs, unsigned c, int value)
{
    if (value >= 0) {
        write_unsigned(bs, c + 1, value << 1);
    } else {
        write_unsigned(bs, c + 1, ((-value - 1) << 1) + 1);
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
write_long(BitstreamWriter* bs, unsigned value)
{
    if (value == 0) {
        write_unsigned(bs, 2, 0);
        write_unsigned(bs, 0, 0);
    } else {
        const unsigned LSBs = LOG2(value) + 1;
        write_unsigned(bs, 2, LSBs);
        write_unsigned(bs, LSBs, value);
    }
}

#ifdef STANDALONE
#include <getopt.h>
#include <errno.h>
#include <string.h>

int main(int argc, char* argv[]) {
    char* output_filename = NULL;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;

    unsigned block_size = 256;
    BitstreamRecorder* header = bw_open_bytes_recorder(BS_BIG_ENDIAN);
    BitstreamRecorder* footer = bw_open_bytes_recorder(BS_BIG_ENDIAN);

    struct PCMReader* pcmreader;
    FILE *output_file;
    BitstreamWriter* writer;
    unsigned bytes_written = 0;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"block-size",              required_argument, NULL, 'B'},
        {"header",                  required_argument, NULL, 'H'},
        {"footer",                  required_argument, NULL, 'F'},
        {NULL,                      no_argument,       NULL,  0}
    };
    const static char* short_opts = "-hc:r:b:B:H:F:";

    while ((c = getopt_long(argc,
                            argv,
                            short_opts,
                            long_opts,
                            NULL)) != -1) {
        FILE* f;

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
        case 'B':
            if (((block_size = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --block-size \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'H':
            header->reset(header);
            if ((f = fopen(optarg, "rb")) != NULL) {
                uint8_t bytes[4096];
                size_t byte_count;
                byte_count = fread(bytes, sizeof(uint8_t), 4096, f);
                while (byte_count > 0) {
                    header->write_bytes((BitstreamWriter*)header,
                                        bytes,
                                        (unsigned int)byte_count);
                    byte_count = fread(bytes, sizeof(uint8_t), 4096, f);
                }
                fclose(f);
            } else {
                fprintf(stderr, "*** Error: %s: %s\n",
                        optarg, strerror(errno));
                goto error;
            }
            break;
        case 'F':
            footer->reset(footer);
            if ((f = fopen(optarg, "rb")) != NULL) {
                uint8_t bytes[4096];
                size_t byte_count;
                byte_count = fread(bytes, sizeof(uint8_t), 4096, f);
                while (byte_count > 0) {
                    footer->write_bytes((BitstreamWriter*)footer,
                                        bytes,
                                        (unsigned int)byte_count);
                    byte_count = fread(bytes, sizeof(uint8_t), 4096, f);
                }
                fclose(f);
            } else {
                fprintf(stderr, "*** Error: %s: %s\n",
                        optarg, strerror(errno));
                goto error;
            }
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: shnenc [options] <output.shn>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("\n");
            printf("-B, --block-size=#              block size\n");
            printf("-H, --header=<filename>         header data\n");
            printf("-F, --footer=<filename>         footer data\n");
            goto exit;
        default:
            break;
        }
    }
    if (output_filename == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    }

    assert(channels > 0);
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16));
    assert(sample_rate > 0);

    /*open pcmreader on stdin*/
    pcmreader = pcmreader_open_raw(stdin,
                                   sample_rate,
                                   channels,
                                   0,
                                   bits_per_sample,
                                   1,
                                   1);

    pcmreader_display(pcmreader, stdout);
    printf("\n");
    printf("block size      %u\n", block_size);
    printf("header size     %u bytes\n", header->bytes_written(header));
    printf("footer size     %u bytes\n", footer->bytes_written(footer));

    /*open given filename for writing*/
    if ((output_file = fopen(output_filename, "wb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", output_filename, strerror(errno));
        pcmreader->close(pcmreader);
        goto error;
    } else {
        writer = bw_open(output_file, BS_BIG_ENDIAN);
    }

    /*write magic number and version*/
    writer->build(writer, "4b 8u", "ajkg", 2);

    writer->add_callback(writer, (bs_callback_f)byte_counter, &bytes_written);

    /*write Shorten header*/
    write_header(writer,
                 pcmreader->bits_per_sample,
                 0,
                 1,
                 pcmreader->channels,
                 block_size);

    /*issue initial VERBATIM command with header data*/
    if (header->bytes_written(header)) {
        const unsigned header_size = header->bytes_written(header);
        const uint8_t* header_data = header->data(header);
        unsigned i;

        write_unsigned(writer, COMMAND_SIZE, FN_VERBATIM);
        write_unsigned(writer, VERBATIM_SIZE, header_size);
        for (i = 0; i < header_size; i++) {
            write_unsigned(writer, VERBATIM_BYTE_SIZE, header_data[i]);
        }
    }

    /*process PCM frames*/
    if (encode_audio(writer, pcmreader, 1, block_size))
        goto error;

    /*if there's footer data, issue a VERBATIM command for it*/
    if (footer->bytes_written(footer)) {
        const unsigned footer_size = footer->bytes_written(footer);
        const uint8_t* footer_data = footer->data(footer);
        unsigned i;

        write_unsigned(writer, COMMAND_SIZE, FN_VERBATIM);
        write_unsigned(writer, VERBATIM_SIZE, footer->bytes_written(footer));
        for (i = 0; i < footer_size; i++) {
            write_unsigned(writer, VERBATIM_BYTE_SIZE, footer_data[i]);
        }
    }

    /*issue QUIT command*/
    write_unsigned(writer, COMMAND_SIZE, FN_QUIT);

    /*pad output (not including header) to a multiple of 4 bytes*/
    writer->byte_align(writer);
    while ((bytes_written % 4) != 0) {
        writer->write(writer, 8, 0);
    }

    /*deallocate temporary buffers and close files*/
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);
    writer->close(writer);

exit:
    header->close(header);
    footer->close(footer);
    return 0;

error:
    header->close(header);
    footer->close(footer);
    return 1;
}
#endif
