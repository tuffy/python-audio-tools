#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../pcmreader.h"
#include "../bitstream.h"
#include <wavpack/wavpack.h>

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

static int
block_out(BitstreamWriter *output, uint8_t *data, int32_t byte_count);

/*FIXME - handle optional wav header, footer*/
static int
encode_wavpack(BitstreamWriter *output,
               struct PCMReader *pcmreader,
               unsigned block_size,
               unsigned correlation_passes,
               int false_stereo,
               int wasted_bits,
               int joint_stereo)
{
    int *samples;
    unsigned pcm_frames_read;
    uint32_t total_samples_written = 0;

    /*get context and set block output function*/
    WavpackContext *context =
        WavpackOpenFileOutput((WavpackBlockOutput)block_out,
                              output,
                              NULL);

    WavpackConfig config;

    if (context) {
        samples = malloc(pcmreader->channels * block_size * sizeof(int));
    } else {
        return 1;
    }

    /*set data format and encoding parameters*/
    memset(&config, 0, sizeof(WavpackConfig));
    config.bytes_per_sample = pcmreader->bits_per_sample / 8;
    config.bits_per_sample = pcmreader->bits_per_sample;
    config.channel_mask = pcmreader->channel_mask;
    config.num_channels = pcmreader->channels;
    config.sample_rate = pcmreader->sample_rate;
    config.flags = 0;
    /*FIXME - update flags based on encoding parameters*/

    /*FIXME - support sample count, if possible*/
    if (!WavpackSetConfiguration(context, &config, -1)) {
        goto error;
    }

    /*write RIFF header, if given*/
    /*FIXME*/

    /*allocate buffers and prepare for packing*/
    if (!WavpackPackInit(context)) {
        goto error;
    }

    /*actually compress audio and write blocks*/
    while ((pcm_frames_read =
            pcmreader->read(pcmreader, block_size, samples)) > 0) {
        fprintf(stderr, "read %u frames\n", pcm_frames_read);
        if (!WavpackPackSamples(context, samples, pcm_frames_read)) {
            goto error;
        }
        total_samples_written += pcm_frames_read;
    }

    /*check for read error*/
    /*FIXME*/

    /*flush final samples*/
    if (!WavpackFlushSamples(context)) {
        goto error;
    }

    /*write calculated MD5 sum*/
    /*FIXME*/

    /*write RIFF trailer, if given*/
    /*FIXME*/

    /*update total sample count, if necessary*/
    /*FIXME*/

    /*close Wavpack*/
    WavpackCloseFile(context);

    /*deallocate temporary space and return success*/
    free(samples);
    return 0;

error:
    /*deallocate temporary space and return error*/
    WavpackCloseFile(context);
    free(samples);
    return 1;
}

static int
block_out(BitstreamWriter *output, uint8_t *data, int32_t byte_count)
{
    /*FIXME - implement this*/
    fprintf(stderr, "wrote %d bytes\n", byte_count);
    output->write_bytes(output, data, (unsigned int)byte_count);
    return 0; /*FIXME - does this mean success?*/
}

#ifdef STANDALONE
#include <getopt.h>
#include <errno.h>
#include <assert.h>

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
    struct PCMReader *pcmreader;
    char* output_filename = NULL;
    FILE *output_file;
    BitstreamWriter *output;
    unsigned channels = 2;
    unsigned channel_mask = 0x3;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;

    unsigned block_size = 22050;
    unsigned correlation_passes = 5;
    int false_stereo = 0;
    int wasted_bits = 0;
    int joint_stereo = 0;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"channel-mask",            required_argument, NULL, 'm'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"block-size",              required_argument, NULL, 'B'},
        {"correlation-passes",      required_argument, NULL, 'p'},
        {"false-stereo",            no_argument,       NULL, 'f'},
        {"wasted-bits",             no_argument,       NULL, 'w'},
        {"joint-stereo",            no_argument,       NULL, 'j'}};
    const static char* short_opts = "-hc:m:r:b:B:p:fwj";

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
            if (((block_size = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --block-size \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'p':
            if (((correlation_passes =
                  strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --correlation_passes \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'f':
            false_stereo = 1;
            break;
        case 'w':
            wasted_bits = 1;
            break;
        case 'j':
            joint_stereo = 1;
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: wvenc [options] <output.wv>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-m, --channel-mask=#      channel mask as hex value\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("\n");
            printf("-B, --block-size=#              block size\n");
            printf("-p, --correlation_passes=#      "
                   "number of correlation passes\n");
            printf("-f, --false-stereo              check for false stereo\n");
            printf("-w, --wasted-bits               check for wasted bits\n");
            printf("-j, --joint-stereo              use joint stereo\n");
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
    assert((correlation_passes == 0) ||
           (correlation_passes == 1) ||
           (correlation_passes == 2) ||
           (correlation_passes == 5) ||
           (correlation_passes == 10) ||
           (correlation_passes == 16));
    assert(count_bits(channel_mask) == channels);

    pcmreader = pcmreader_open_raw(stdin,
                                   sample_rate,
                                   channels,
                                   channel_mask,
                                   bits_per_sample,
                                   1, 1);
    output = bw_open(output_file, BS_LITTLE_ENDIAN);

    pcmreader_display(pcmreader, stderr);
    fputs("\n", stderr);
    fprintf(stderr ,"block size         %u\n", block_size);
    fprintf(stderr, "correlation_passes %u\n", correlation_passes);
    fprintf(stderr, "false stereo       %d\n", false_stereo);
    fprintf(stderr, "wasted bits        %d\n", wasted_bits);
    fprintf(stderr, "joint stereo       %d\n", joint_stereo);

    encode_wavpack(output,
                   pcmreader,
                   block_size,
                   correlation_passes,
                   false_stereo,
                   wasted_bits,
                   joint_stereo);

    //encoders_encode_wavpack(output_file,
    //                        open_pcmreader(stdin,
    //                                       sample_rate,
    //                                       channels,
    //                                       channel_mask,
    //                                       bits_per_sample,
    //                                       0,
    //                                       1),
    //                        block_size,
    //                        false_stereo,
    //                        wasted_bits,
    //                        joint_stereo,
    //                        correlation_passes);

    output->close(output);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}

#endif
