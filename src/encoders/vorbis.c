#include "../pcmconv.h"
#include <stdlib.h>
#include <time.h>
#include <vorbis/vorbisenc.h>
#include <ogg/ogg.h>

#define BLOCK_SIZE 1024

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

typedef enum {
    ENCODE_OK,
    ERR_CHANNEL_COUNT,
    ERR_CHANNEL_ASSIGNMENT,
    ERR_IOERROR,    /*build exception from errno with filename*/
    ERR_INIT_VBR,
    ERR_OGG_INIT,
    ERR_OGG_IOERROR,
    ERR_PCMREADER,  /*don't generate new Python exception*/
    ERR_FRAMELIST_SIZE,
} result_t;

#ifndef STANDALONE
static PyObject*
encode_exception(result_t result);
#endif

static const char*
encode_strerror(result_t result);

static void
reorder_channels(unsigned channel_mask, aa_int *samples);

static result_t
encode_ogg_vorbis(char *filename, pcmreader *pcmreader, float quality);

#ifndef STANDALONE
PyObject*
encoders_encode_vorbis(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    char *filename;
    pcmreader *pcmreader;
    float quality;
    result_t result;

    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "quality",
                             NULL};

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "sO&f", kwlist,
                                     &filename,
                                     pcmreader_converter,
                                     &pcmreader,
                                     &quality)) {
        return NULL;
    }

    result = encode_ogg_vorbis(filename, pcmreader, quality);

    pcmreader->del(pcmreader);

    switch (result) {
    case ENCODE_OK:
        Py_INCREF(Py_None);
        return Py_None;
    case ERR_IOERROR:
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    case ERR_PCMREADER:
        /*exception built from PCMReader object, so pass it through*/
        return NULL;
    default:
        PyErr_SetString(encode_exception(result),
                        encode_strerror(result));
        return NULL;
    }
}

static PyObject*
encode_exception(result_t result)
{
    switch (result) {
    default:
    case ENCODE_OK:
    case ERR_CHANNEL_COUNT:
    case ERR_CHANNEL_ASSIGNMENT:
    case ERR_INIT_VBR:
    case ERR_OGG_INIT:
    case ERR_FRAMELIST_SIZE:
        return PyExc_ValueError;
    case ERR_PCMREADER:
    case ERR_IOERROR:
        return NULL;
    case ERR_OGG_IOERROR:
        return PyExc_IOError;
    }
}
#endif

static const char*
encode_strerror(result_t result)
{
    switch (result) {
    case ENCODE_OK:
    default:
        return "no error";
    case ERR_CHANNEL_COUNT:
        return "unsupported channel count";
    case ERR_CHANNEL_ASSIGNMENT:
        return "unsupported channel assignment";
    case ERR_IOERROR:
        return "I/O error";
    case ERR_INIT_VBR:
        return "error initializing Vorbis output";
    case ERR_OGG_INIT:
        return "error initializing Ogg stream";
    case ERR_OGG_IOERROR:
        return "I/O error writing Ogg page";
    case ERR_PCMREADER:
        return "error reading from PCMReader";
    case ERR_FRAMELIST_SIZE:
        return "FrameList too large, please use BufferedPCMReader";
    }
}

static result_t
encode_ogg_vorbis(char *filename, pcmreader *pcmreader, float quality)
{
    aa_int *samples;
    FILE *output;
    result_t result = ENCODE_OK;
    vorbis_info vorbis_info;
    vorbis_comment vorbis_comment;
    vorbis_dsp_state vorbis_dsp;
    vorbis_block vorbis_block;
    ogg_stream_state ogg_stream;
    ogg_page ogg_page;
    int end_of_stream = 0;

    /*ensure PCMReader object is compatible with Vorbis output*/
    if ((pcmreader->channels == 0) || (pcmreader->channels > 255)) {
        /*sanity check channel count*/
        return ERR_CHANNEL_COUNT;
    } else if (pcmreader->channel_mask != 0) {
        /*if channel assignment is defined,
          ensure it's compatible with Vorbis output*/
        const unsigned channels = pcmreader->channels;
        const unsigned channel_mask = pcmreader->channel_mask;

        if ((channels == 3) &&
            (channel_mask != (0x1 | 0x2 | 0x4))) {
            return ERR_CHANNEL_ASSIGNMENT;
        } else if ((channels == 4) &&
                   (channel_mask != (0x1 | 0x2 | 0x10 | 0x20))) {
            return ERR_CHANNEL_ASSIGNMENT;
        } else if ((channels == 5) &&
                   (channel_mask != (0x1 | 0x2 | 0x4 | 0x10 | 0x20))) {
            return ERR_CHANNEL_ASSIGNMENT;
        } else if ((channels == 6) &&
                   (channel_mask != (0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20))) {
            return ERR_CHANNEL_ASSIGNMENT;
        } else if ((channels == 7) &&
                   (channel_mask != (0x1 | 0x2 | 0x4 | 0x8 |
                                     0x100 | 0x200 | 0x400))) {
            return ERR_CHANNEL_ASSIGNMENT;
        } else if ((channels == 8) &&
                   (channel_mask != (0x1 | 0x2 | 0x4 | 0x8 |
                                     0x10 | 0x20 | 0x200 | 0x400))) {
            return ERR_CHANNEL_ASSIGNMENT;
        }
    }

    /*open output file for writing as Ogg stream*/
    if ((output = fopen(filename, "w")) == NULL) {
        return ERR_IOERROR;
    }

    samples = aa_int_new();

    vorbis_info_init(&vorbis_info);

    /*this may fail if the quality is unsupported, etc.*/
    if (vorbis_encode_init_vbr(&vorbis_info,
                               pcmreader->channels,
                               pcmreader->sample_rate,
                               quality)) {
        fclose(output);
        samples->del(samples);
        vorbis_info_clear(&vorbis_info);
        return ERR_INIT_VBR;
    }


    /*initialize analysis state and block storage*/
    vorbis_comment_init(&vorbis_comment);
    vorbis_analysis_init(&vorbis_dsp, &vorbis_info);
    vorbis_block_init(&vorbis_dsp, &vorbis_block);

    /*initialize packet -> Ogg page stream converter*/
    srand((unsigned)time(NULL));
    ogg_stream_init(&ogg_stream, rand());

    /*generate initial, comments and codebooks headers and write them out*/
    {
        ogg_packet header_initial;
        ogg_packet header_comment;
        ogg_packet header_codebooks;
        int i;

        vorbis_analysis_headerout(&vorbis_dsp,
                                  &vorbis_comment,
                                  &header_initial,
                                  &header_comment,
                                  &header_codebooks);
        ogg_stream_packetin(&ogg_stream, &header_initial);
        ogg_stream_packetin(&ogg_stream, &header_comment);
        ogg_stream_packetin(&ogg_stream, &header_codebooks);

        for (i = ogg_stream_flush(&ogg_stream, &ogg_page);
             i != 0;
             i = ogg_stream_flush(&ogg_stream, &ogg_page)) {
            fwrite(ogg_page.header, 1, ogg_page.header_len, output);
            fwrite(ogg_page.body, 1, ogg_page.body_len, output);
        }
    }

    while (!end_of_stream) {
        const int adjustment = 1 << (pcmreader->bits_per_sample - 1);
        ogg_packet ogg_packet;

        /*read FrameList from PCMReader*/
        if (pcmreader->read(pcmreader, BLOCK_SIZE, samples)) {
            result = ERR_PCMREADER;
            goto cleanup;
        } else if (samples->_[0]->len > BLOCK_SIZE) {
            result = ERR_FRAMELIST_SIZE;
            goto cleanup;
        }

        reorder_channels(pcmreader->channel_mask, samples);

        if (samples->_[0]->len != 0) {
            unsigned c;

            /*grab buffer to be populated*/
            const unsigned samples_read = samples->_[0]->len;
            float **buffer = vorbis_analysis_buffer(&vorbis_dsp, samples_read);

            /*populate buffer with floating point samples
              on channel-by-channel basis*/
            for (c = 0; c < samples->len; c++) {
                const a_int *channel = samples->_[c];
                unsigned i;

                for (i = 0; i < channel->len; i++) {
                    buffer[c][i] = (float)(channel->_[i]) / adjustment;
                }
            }

            vorbis_analysis_wrote(&vorbis_dsp, samples_read);
        } else {
            vorbis_analysis_wrote(&vorbis_dsp, 0);
        }

        while (vorbis_analysis_blockout(&vorbis_dsp, &vorbis_block) == 1) {
            vorbis_analysis(&vorbis_block, NULL);
            vorbis_bitrate_addblock(&vorbis_block);

            while (vorbis_bitrate_flushpacket(&vorbis_dsp, &ogg_packet)) {
                ogg_stream_packetin(&ogg_stream, &ogg_packet);

                while (!end_of_stream) {
                    if (ogg_stream_pageout(&ogg_stream, &ogg_page) == 0) {
                        break;
                    }

                    fwrite(ogg_page.header, 1, ogg_page.header_len, output);
                    fwrite(ogg_page.body, 1, ogg_page.body_len, output);

                    if (ogg_page_eos(&ogg_page))
                        end_of_stream = 1;
                }
            }
        }
    }

cleanup:
    ogg_stream_clear(&ogg_stream);
    vorbis_block_clear(&vorbis_block);
    vorbis_dsp_clear(&vorbis_dsp);
    vorbis_comment_clear(&vorbis_comment);
    vorbis_info_clear(&vorbis_info);
    samples->del(samples);
    fclose(output);

    return result;
}

static void
reorder_channels(unsigned channel_mask, aa_int *samples)
{
    /*reorder channels if necessary based on assignment*/
    switch (channel_mask) {
    default:
        break;
    case (0x1 | 0x2 | 0x4):
        /*fL fR fC -> fL fC fR*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (0x1 | 0x2 | 0x10 | 0x20):
        /*fL fR bL bR -> fL fR bL bR*/
        /*no change*/
        break;
    case (0x1 | 0x2 | 0x4 | 0x10 | 0x20):
        /*fL fR fC bL bR -> fL fC fR bL bR*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20):
        /*fL fR fC LFE bL bR -> fL fR fC LFE bR bL*/
        a_int_swap(samples->_[4], samples->_[5]);

        /*fL fR fC LFE bR bL -> fL fR fC bL bR LFE*/
        a_int_swap(samples->_[3], samples->_[5]);

        /*fL fR fC bL bR LFE -> fL fC fR bL bR LFE*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (0x1 | 0x2 | 0x4 | 0x8 | 0x100 | 0x200 | 0x400):
        /*fL fR fC LFE bC sL sR -> fL fR fC LFE bC sR sL*/
        a_int_swap(samples->_[5], samples->_[6]);

        /*fL fR fC LFE bC sR sL -> fL fR fC LFE sR bC sL*/
        a_int_swap(samples->_[4], samples->_[5]);

        /*fL fR fC LFE sR bC sL -> fL fR fC sL sR bC LFE*/
        a_int_swap(samples->_[3], samples->_[6]);

        /*fL fR fC sL sR bC LFE -> fL fC fR sL sR bC LFE*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20 | 0x200 | 0x400):
        /*fL fR fC LFE bL bR sL sR -> fL fR fC LFE bL bR sR sL*/
        a_int_swap(samples->_[6], samples->_[7]);

        /*fL fR fC LFE bL bR sR sL -> fL fR fC LFE bL sR bR sL*/
        a_int_swap(samples->_[5], samples->_[6]);

        /*fL fR fC LFE bL sR bR sL -> fL fR fC LFE sR bL bR sL*/
        a_int_swap(samples->_[4], samples->_[5]);

        /*fL fR fC LFE sR bL bR sL -> fL fR fC sL sR bL bR LFE*/
        a_int_swap(samples->_[3], samples->_[6]);

        /*fL fR fC sL sR bL bR LFE -> fL fC fR sL sR bL bR LFE*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    }
}

#ifdef STANDALONE
#include <getopt.h>
#include <errno.h>
#include <assert.h>

int main(int argc, char *argv[])
{
    char* output_file = NULL;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;
    pcmreader *pcmreader = NULL;
    result_t result;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"sample-rate",             required_argument, NULL, 'r'},
        {"bits-per-sample",         required_argument, NULL, 'b'},
        {NULL,                      no_argument,       NULL,  0}
    };
    const static char* short_opts = "-hc:r:b:";

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
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: vorbisenc [options] <output.ogg>\n");
            printf("-c, --channels=#          number of input channels\n");
            printf("-r, --sample_rate=#       input sample rate in Hz\n");
            printf("-b, --bits-per-sample=#   bits per input sample\n");
            return 0;
        default:
            break;

        }
    }

    if (output_file == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    }

    assert((channels > 0) && (channels <= 255));
    assert((bits_per_sample == 8) ||
    (bits_per_sample == 16) ||
    (bits_per_sample == 24));
    assert(sample_rate > 0);

    printf("Encoding from stdin using parameters:\n");
    printf("channels        %u\n", channels);
    printf("sample rate     %u\n", sample_rate);
    printf("bits per sample %u\n", bits_per_sample);
    printf("little-endian, signed samples\n");

    pcmreader = open_pcmreader(stdin,
                               sample_rate,
                               channels,
                               0,
                               bits_per_sample,
                               0,
                               1);

    switch (result = encode_ogg_vorbis(output_file, pcmreader, 0.3)) {
    case ENCODE_OK:
        break;
    default:
        fprintf(stderr, "*** Error: %s", encode_strerror(result));
        break;
    }

    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}
#endif
