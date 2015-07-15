#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../pcm_conv.h"
#include "wavpack.h"
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

static wavpack_compression_t
str_to_compression(const char *compression);

#ifndef STANDALONE

PyObject*
encoders_encode_wavpack(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    static char *kwlist[] = {"filename",
                             "pcmreader",

                             "total_pcm_frames",
                             "block_size",
                             "compression",
                             "wave_header",
                             "wave_footer",
                             NULL};
    char *filename;
    FILE *output_file = NULL;
    BitstreamWriter *output;
    struct PCMReader *pcmreader = NULL;
    long long total_pcm_frames = 0;
    int block_size = 22050;
    char *compression_str = "standard";
    wavpack_compression_t compression;
#ifdef PY_SSIZE_T_CLEAN
    Py_ssize_t header_len = 0;
    Py_ssize_t footer_len = 0;
#else
    int header_len = 0;
    int footer_len = 0;
#endif
    uint8_t *header_data = NULL;
    uint8_t *footer_data = NULL;
    int result;

    if (!PyArg_ParseTupleAndKeywords(
            args,
            keywds,
            "sO&|Liss#s#",
            kwlist,
            &filename,
            py_obj_to_pcmreader,
            &pcmreader,

            &total_pcm_frames,
            &block_size,
            &compression_str,
            &header_data,
            &header_len,
            &footer_data,
            &footer_len)) {
        return NULL;
    }

    /*sanity-check options*/
    if ((total_pcm_frames < 0) || (total_pcm_frames > 0xFFFFFFFFLL)) {
        PyErr_SetString(PyExc_ValueError,
                        "total_pcm_frames must be between 0 and 0xFFFFFFFF");
        return NULL;
    }

    if (block_size <= 0) {
        PyErr_SetString(PyExc_ValueError, "block size must be > 0");
        return NULL;
    }

    if ((compression = str_to_compression(compression_str))
        == COMPRESSION_UNKNOWN) {
        PyErr_SetString(PyExc_ValueError, "unknown compression level");
        return NULL;
    }

    /*open output file for writing*/
    errno = 0;
    if ((output_file = fopen(filename, "wb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    }

    output = bw_open(output_file, BS_LITTLE_ENDIAN);

    /*perform actual encoding*/
    result = encode_wavpack(output,
                            pcmreader,
                            (uint32_t)total_pcm_frames,
                            (unsigned)block_size,
                            compression,
                            (uint32_t)header_len,
                            header_data,
                            (uint32_t)footer_len,
                            footer_data);

    /*cleanup PCMReader and output file*/
    output->close(output);
    pcmreader->del(pcmreader);

    /*return success or exception depending on result*/
    switch (result) {
    default:
        Py_INCREF(Py_None);
        return Py_None;
    case 1:
        PyErr_SetString(PyExc_IOError, "read error during encoding");
        return NULL;
    case 2:
        PyErr_SetString(PyExc_ValueError, "total frames mismatch");
        return NULL;
    }
}

#else

static int
read_file(const char *filename,
          uint32_t *size,
          uint8_t **data);

static const char*
compression_to_str(wavpack_compression_t compression);

#endif

static int
encode_wavpack(BitstreamWriter *output,
               struct PCMReader *pcmreader,
               uint32_t total_pcm_frames,
               unsigned block_size,
               wavpack_compression_t compression,
               uint32_t header_size,
               uint8_t *header_data,
               uint32_t footer_size,
               uint8_t *footer_data)
{
    audiotools__MD5Context md5;
    unsigned char stream_md5[16];
    int *samples;
    unsigned pcm_frames_read;
    uint32_t total_frames_written = 0;
    audiotools__MD5Init(&md5);

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
    if (pcmreader->channel_mask) {
        config.channel_mask = pcmreader->channel_mask;
    } else if (pcmreader->channels == 1) {
        config.channel_mask = 0x4;
    } else if (pcmreader->channels == 2) {
        config.channel_mask = 0x3;
    } else {
        config.channel_mask = 0;
    }
    config.num_channels = pcmreader->channels;
    config.sample_rate = pcmreader->sample_rate;
    config.flags = CONFIG_MD5_CHECKSUM | CONFIG_OPTIMIZE_MONO;

    switch (compression) {
    default:
        break;
    case COMPRESSION_FAST:
        config.flags |= CONFIG_FAST_FLAG;
        break;
    case COMPRESSION_HIGH:
        config.flags |= CONFIG_HIGH_FLAG;
        break;
    case COMPRESSION_VERYHIGH:
        config.flags |= CONFIG_VERY_HIGH_FLAG;
        break;
    }

    if (!WavpackSetConfiguration(context,
                                 &config,
                                 total_pcm_frames ? total_pcm_frames : -1)) {
        goto error;
    }

    /*write RIFF header, if given*/
    if (header_size) {
        if (!WavpackAddWrapper(context, header_data, header_size)) {
            goto error;
        }
    }

    /*allocate buffers and prepare for packing*/
    if (!WavpackPackInit(context)) {
        goto error;
    }

    /*actually compress audio and write blocks*/
    while ((pcm_frames_read =
            pcmreader->read(pcmreader, block_size, samples)) > 0) {
        if (!WavpackPackSamples(context, samples, pcm_frames_read)) {
            goto error;
        }
        update_md5sum(&md5,
                      samples,
                      pcmreader->channels,
                      pcmreader->bits_per_sample,
                      pcm_frames_read);
        total_frames_written += pcm_frames_read;
    }

    /*check for read error*/
    if (pcmreader->status != PCM_OK) {
        goto error;
    }

    /*flush final samples*/
    if (!WavpackFlushSamples(context)) {
        goto error;
    }

    /*write calculated MD5 sum*/
    audiotools__MD5Final(stream_md5, &md5);
    if (!WavpackStoreMD5Sum(context, stream_md5)) {
        goto error;
    }

    /*write RIFF trailer, if given*/
    if (footer_size) {
        if (!WavpackAddWrapper(context, footer_data, footer_size)) {
            goto error;
        }
    }

    if (!WavpackFlushSamples(context)) {
        goto error;
    }

    /*close Wavpack and deallocate temporary space*/
    WavpackCloseFile(context);
    free(samples);

    /*update total sample count, if necessary*/
    if (total_pcm_frames) {
        if (total_pcm_frames != total_frames_written) {
            return 2;
        }
    } else {
        output->seek(output, 12, BS_SEEK_SET);
        output->write(output, 32, total_frames_written);
    }

    /*deallocate temporary space and return success*/
    return 0;

error:
    /*deallocate temporary space and return error*/
    WavpackCloseFile(context);
    free(samples);
    return 1;
}

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int pcm_data[],
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames)
{
    const unsigned bytes_per_sample = bits_per_sample / 8;
    unsigned total_samples = pcm_frames * channels;
    const unsigned buffer_size = total_samples * bytes_per_sample;
    unsigned char buffer[buffer_size];
    unsigned char *output_buffer = buffer;
    void (*converter)(int, unsigned char *) =
        int_to_pcm_converter(bits_per_sample, 0, (bits_per_sample > 8) ? 1 : 0);

    for (; total_samples; total_samples--) {
        converter(*pcm_data, output_buffer);
        pcm_data += 1;
        output_buffer += bytes_per_sample;
    }

    audiotools__MD5Update(md5sum, buffer, buffer_size);
}

static int
block_out(BitstreamWriter *output, uint8_t *data, int32_t byte_count)
{
    output->write_bytes(output, data, (unsigned int)byte_count);
    return 1;
}

static wavpack_compression_t
str_to_compression(const char *compression)
{
    if (!strcmp(compression, "fast")) {
        return COMPRESSION_FAST;
    } else if (!strcmp(compression, "standard")) {
        return COMPRESSION_NORMAL;
    } else if (!strcmp(compression, "high")) {
        return COMPRESSION_HIGH;
    } else if (!strcmp(compression, "veryhigh")) {
        return COMPRESSION_VERYHIGH;
    } else {
        return COMPRESSION_UNKNOWN;
    }
}

#ifdef STANDALONE

#include <getopt.h>
#include <errno.h>
#include <assert.h>

static int
read_file(const char *filename,
          uint32_t *size,
          uint8_t **data)
{
    FILE *file = fopen(filename, "rb");
    const size_t block_size = 4096;
    size_t bytes_read;

    if (!file) {
        return 1;
    }

    *size = 0;
    *data = malloc(block_size);
    while ((bytes_read = fread(*data + *size,
                               sizeof(uint8_t),
                               block_size,
                               file)) > 0) {
        *size += bytes_read;
        *data = realloc(*data, *size + block_size);
    }

    return 0;
}

static const char*
compression_to_str(wavpack_compression_t compression)
{
    switch (compression) {
    default:
        return "unknown";
    case COMPRESSION_FAST:
        return "fast";
    case COMPRESSION_NORMAL:
        return "standard";
    case COMPRESSION_HIGH:
        return "high";
    case COMPRESSION_VERYHIGH:
        return "veryhigh";
    }
}


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

    uint32_t total_pcm_frames = 0;

    unsigned block_size = 22050;
    wavpack_compression_t compression = COMPRESSION_NORMAL;

    uint32_t header_size = 0;
    uint8_t *header_data = NULL;
    uint32_t footer_size = 0;
    uint8_t *footer_data = NULL;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"channel-mask",            required_argument, NULL, 'm'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {"total-pcm-frames",        required_argument, NULL, 'T'},
        {"block-size",              required_argument, NULL, 'B'},
        {"compression",             required_argument, NULL, 'C'},
        {"header",                  required_argument, NULL, 'H'},
        {"footer",                  required_argument, NULL, 'F'}};
    const static char* short_opts = "-hc:m:r:b:T:C:H:F:";

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
        case 'T':
            if (((total_pcm_frames = strtoul(optarg, NULL, 10)) == 0) &&
                errno) {
                printf("invalid --total-pcm-frames \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'B':
            if (((block_size = strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --block-size \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'C':
            if ((compression = str_to_compression(optarg))
                == COMPRESSION_UNKNOWN) {
                fprintf(stderr, "unknown compression: %s\n", optarg);
                fprintf(stderr,
                        "choose from 'fast', 'standard', 'high', 'veryhigh'\n");
                return 1;
            }
            break;
        case 'H':
            errno = 0;
            if (read_file(optarg, &header_size, &header_data)) {
                fprintf(stderr, "%s: %s\n", optarg, strerror(errno));
                return 1;
            }
            break;
        case 'F':
            errno = 0;
            if (read_file(optarg, &footer_size, &footer_data)) {
                fprintf(stderr, "%s: %s\n", optarg, strerror(errno));
                return 1;
            }
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: wvenc [options] <output.wv>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-m, --channel-mask=#      channel mask as hex value\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            printf("-T, --total-pcm-frames=#  total PCM frames of input\n");
            printf("\n");
            printf("-B, --block-size=#              block size\n");
            printf("-C, --compression=level         compression level\n");
            printf("-H, --header                    RIFF header\n");
            printf("-F, --footer                    RIFF footer\n");
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
    fprintf(stderr, "block size   %u\n", block_size);
    fprintf(stderr, "compression  %s\n", compression_to_str(compression));

    encode_wavpack(output,
                   pcmreader,
                   total_pcm_frames,
                   block_size,
                   compression,
                   header_size,
                   header_data,
                   footer_size,
                   footer_data);

    output->close(output);
    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);
    free(header_data);
    free(footer_data);

    return 0;
}

#endif
