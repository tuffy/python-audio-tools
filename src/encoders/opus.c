#include "../pcmconv.h"
#include "../array.h"
#include "../bitstream.h"
#include <opus/opus.h>
#include <opus_multistream.h>
#include <ogg/ogg.h>
#include <time.h>
#include <stdlib.h>
#include <string.h>

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

#define BLOCK_SIZE 2880
#define OPUS_FRAME_LEN 0x100000

typedef enum {
    ENCODE_OK,
    ERR_IOERROR,
    ERR_ENCODER_INIT,
    ERR_PCMREADER,
    ERR_BLOCK_SIZE,
    ERR_ENCODE_ERROR
} result_t;

static result_t
encode_opus_file(char *filename, pcmreader *pcmreader,
                 int quality, unsigned original_sample_rate);

static void
reorder_channels(unsigned channel_mask, aa_int *samples);

#ifndef STANDALONE
PyObject*
encoders_encode_opus(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    char *filename;
    pcmreader* pcmreader = NULL;
    int quality;
    int original_sample_rate;
    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "quality",
                             "original_sample_rate",
                             NULL};
    result_t result;

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "sO&ii",
                                     kwlist,
                                     &filename,
                                     pcmreader_converter,
                                     &pcmreader,
                                     &quality,
                                     &original_sample_rate)) {
        if (pcmreader != NULL)
            pcmreader->del(pcmreader);
        return NULL;
    }

    /*sanity check quality*/
    if ((quality < 0) || (quality > 10)) {
        PyErr_SetString(PyExc_ValueError, "quality must be 0-10");
        pcmreader->del(pcmreader);
        return NULL;
    }

    /*sanity check original sample rate*/
    if (original_sample_rate <= 0) {
        PyErr_SetString(PyExc_ValueError, "original_sample_rate must be > 0");
        pcmreader->del(pcmreader);
        return NULL;
    }

    /*sanity check PCMReader*/
    if (pcmreader->sample_rate != 48000) {
        PyErr_SetString(PyExc_ValueError,
                        "PCMReader sample_rate must be 48000");
        pcmreader->del(pcmreader);
        return NULL;
    } else if (pcmreader->bits_per_sample != 16) {
        PyErr_SetString(PyExc_ValueError,
                        "PCMReader bits_per_sample must be 16");
        pcmreader->del(pcmreader);
        return NULL;
    }

    result = encode_opus_file(filename, pcmreader,
                              quality, original_sample_rate);

    pcmreader->del(pcmreader);

    switch (result) {
    case ENCODE_OK:
    default:
        Py_INCREF(Py_None);
        return Py_None;
    case ERR_IOERROR:
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    case ERR_ENCODER_INIT:
        PyErr_SetString(PyExc_ValueError, "error initializing encoder");
        return NULL;
    case ERR_PCMREADER:
        /*pass error through from PCMReader*/
        return NULL;
    case ERR_BLOCK_SIZE:
        PyErr_SetString(PyExc_ValueError,
                        "FrameList too large, please use BufferedPCMReader");
        return NULL;
    case ERR_ENCODE_ERROR:
        PyErr_SetString(PyExc_ValueError,
                        "Opus encoding error");
        return NULL;
    }
}
#endif

static result_t
encode_opus_file(char *filename, pcmreader *pcmreader,
                 int quality, unsigned original_sample_rate)
{
    const int multichannel = (pcmreader->channels > 2);
    const unsigned channel_mapping = (pcmreader->channels > 8 ? 255 :
                                      pcmreader->channels > 2);
    int stream_count;
    int coupled_stream_count;
    unsigned char stream_map[255];

    result_t result = ENCODE_OK;
    FILE *output_file = NULL;
    ogg_stream_state ogg_stream;
    ogg_page ogg_page;
    OpusEncoder *opus_encoder = NULL;
    OpusMSEncoder *opus_ms_encoder = NULL;
    int error;
    aa_int *samples = NULL;
    opus_int16 *opus_samples = NULL;
    unsigned char opus_frame[OPUS_FRAME_LEN];
    ogg_int64_t granulepos = 0;
    ogg_int64_t packetno = 0;
    opus_int32 preskip;

    /*open output file for writing*/
    if ((output_file = fopen(filename, "w+b")) == NULL) {
        return ERR_IOERROR;
    }

    if (!multichannel) {
        if ((opus_encoder = opus_encoder_create(48000,
                                                pcmreader->channels,
                                                OPUS_APPLICATION_AUDIO,
                                                &error)) == NULL) {
            fclose(output_file);
            return ERR_ENCODER_INIT;
        }

        opus_encoder_ctl(opus_encoder, OPUS_SET_COMPLEXITY(quality));
        opus_encoder_ctl(opus_encoder, OPUS_GET_LOOKAHEAD(&preskip));
    } else {
        if ((opus_ms_encoder =
             opus_multistream_surround_encoder_create(
                 48000,
                 pcmreader->channels,
                 channel_mapping,
                 &stream_count,
                 &coupled_stream_count,
                 stream_map,
                 OPUS_APPLICATION_AUDIO,
                 &error)) == NULL) {
            fclose(output_file);
            return ERR_ENCODER_INIT;
        }

        opus_multistream_encoder_ctl(opus_ms_encoder,
                                     OPUS_SET_COMPLEXITY(quality));
        opus_multistream_encoder_ctl(opus_ms_encoder,
                                     OPUS_GET_LOOKAHEAD(&preskip));
    }


    srand((unsigned)time(NULL));
    ogg_stream_init(&ogg_stream, rand());

    /*write header and comment packets to Ogg stream*/
    {
        BitstreamRecorder *header =
            bw_open_bytes_recorder(BS_LITTLE_ENDIAN);
        BitstreamWriter *header_w =(BitstreamWriter*)header;
        BitstreamRecorder *comment =
            bw_open_bytes_recorder(BS_LITTLE_ENDIAN);
        BitstreamWriter *comment_w = (BitstreamWriter*)comment;
        int i;

        /*write header packet to Ogg stream*/
        const char opushead[] = "OpusHead";
        const char opuscomment[] = "OpusTags";
        const char *vendor_string = opus_get_version_string();
        const size_t vendor_string_len = strlen(vendor_string);
        ogg_packet packet_head;
        ogg_packet packet_tags;

        header_w->write_bytes(header_w,
                              (uint8_t*)opushead,
                              (unsigned)strlen(opushead));
        header_w->write(header_w, 8, 1);       /*version*/
        header_w->write(header_w, 8, pcmreader->channels);
        header_w->write(header_w, 16, preskip);
        header_w->write(header_w, 32, original_sample_rate);
        header_w->write(header_w, 16, 0);      /*output gain*/
        header_w->write(header_w, 8, channel_mapping);
        if (channel_mapping != 0) {
            header_w->write(header_w, 8, stream_count);
            header_w->write(header_w, 8, coupled_stream_count);
            for (i = 0; i < pcmreader->channels; i++) {
                header_w->write(header_w, 8, stream_map[i]);
            }
        }

        packet_head.packet = (uint8_t*)header->data(header);
        packet_head.bytes = header->bytes_written(header);
        packet_head.b_o_s = 1;
        packet_head.e_o_s = 0;
        packet_head.granulepos = 0;
        packet_head.packetno = packetno++;

        ogg_stream_packetin(&ogg_stream, &packet_head);

        for (i = ogg_stream_flush(&ogg_stream, &ogg_page);
             i != 0;
             i = ogg_stream_flush(&ogg_stream, &ogg_page)) {
            fwrite(ogg_page.header, 1, ogg_page.header_len, output_file);
            fwrite(ogg_page.body, 1, ogg_page.body_len, output_file);
        }

        /*write comment packet to Ogg stream*/
        comment_w->write_bytes(comment_w,
                               (uint8_t*)opuscomment,
                               (unsigned)strlen(opuscomment));
        comment_w->write(comment_w, 32, (unsigned)vendor_string_len);
        comment_w->write_bytes(comment_w,
                               (uint8_t*)vendor_string,
                               (unsigned)vendor_string_len);
        comment_w->write(comment_w, 32, 0);

        packet_tags.packet = (uint8_t*)comment->data(comment);
        packet_tags.bytes = comment->bytes_written(comment);
        packet_tags.b_o_s = 0;
        packet_tags.e_o_s = 0;
        packet_tags.granulepos = 0;
        packet_tags.packetno = packetno++;

        ogg_stream_packetin(&ogg_stream, &packet_tags);

        for (i = ogg_stream_flush(&ogg_stream, &ogg_page);
             i != 0;
             i = ogg_stream_flush(&ogg_stream, &ogg_page)) {
            fwrite(ogg_page.header, 1, ogg_page.header_len, output_file);
            fwrite(ogg_page.body, 1, ogg_page.body_len, output_file);
        }

        header->close(header);
        comment->close(comment);
    }

    samples = aa_int_new();
    opus_samples = malloc(sizeof(opus_int16) *
                          pcmreader->channels *
                          BLOCK_SIZE);

    /*for each non-empty FrameList from PCMReader, encode Opus frame*/
    if (pcmreader->read(pcmreader, BLOCK_SIZE, samples)) {
        result = ERR_PCMREADER;
        goto cleanup;
    } else if (samples->_[0]->len > BLOCK_SIZE) {
        result = ERR_BLOCK_SIZE;
        goto cleanup;
    }

    while (samples->_[0]->len > 0) {
        const int short_framelist = (samples->_[0]->len < BLOCK_SIZE);
        unsigned c;
        opus_int32 encoded_size;
        ogg_packet packet;

        granulepos += samples->_[0]->len;

        /*pad FrameList with additional null samples if necessary*/
        for (c = 0; c < samples->len; c++) {
            a_int *channel = samples->_[c];
            channel->mappend(channel, BLOCK_SIZE - samples->_[0]->len, 0);
        }

        /*rearrange channels to Vorbis order if necessary*/
        reorder_channels(pcmreader->channel_mask, samples);

        /*place samples in interleaved buffer*/
        for (c = 0; c < samples->len; c++) {
            unsigned i;
            a_int *channel = samples->_[c];

            for (i = 0; i < channel->len; i++) {
                opus_samples[c + (i * samples->len)] =
                    (opus_int16)channel->_[i];
            }
        }

        /*call opus_encode on interleaved buffer to get next packet*/
        if (!multichannel) {
            encoded_size = opus_encode(opus_encoder,
                                       opus_samples,
                                       samples->_[0]->len,
                                       opus_frame,
                                       OPUS_FRAME_LEN);
        } else {
            encoded_size = opus_multistream_encode(opus_ms_encoder,
                                                   opus_samples,
                                                   samples->_[0]->len,
                                                   opus_frame,
                                                   OPUS_FRAME_LEN);
        }

        /*get next FrameList to encode*/
        if (pcmreader->read(pcmreader, BLOCK_SIZE, samples)) {
            result = ERR_PCMREADER;
            goto cleanup;
        } else if (samples->_[0]->len > BLOCK_SIZE) {
            result = ERR_BLOCK_SIZE;
            goto cleanup;
        }

        /*dump Opus packet to Ogg stream*/
        /*do this *after* reading the next FrameList in order to detect
          the end of stream properly based on whether the FrameList
          has no frames*/
        packet.packet = (unsigned char *)opus_frame;
        packet.bytes = encoded_size;
        packet.b_o_s = 0;
        packet.e_o_s = (short_framelist || (samples->_[0]->len == 0));
        packet.granulepos = granulepos;
        packet.packetno = packetno;

        ogg_stream_packetin(&ogg_stream, &packet);
        while (ogg_stream_pageout(&ogg_stream, &ogg_page)) {
            fwrite(ogg_page.header, 1, ogg_page.header_len, output_file);
            fwrite(ogg_page.body, 1, ogg_page.body_len, output_file);
        }
    }

    /*flush any remaining Ogg pages to disk*/
    while (ogg_stream_flush(&ogg_stream, &ogg_page)) {
        fwrite(ogg_page.header, 1, ogg_page.header_len, output_file);
        fwrite(ogg_page.body, 1, ogg_page.body_len, output_file);
    }

cleanup:
    fclose(output_file);
    ogg_stream_clear(&ogg_stream);
    if (!multichannel) {
        opus_encoder_destroy(opus_encoder);
    } else {
        opus_multistream_encoder_destroy(opus_ms_encoder);
    }
    samples->del(samples);
    free(opus_samples);
    return result;
}


static void
reorder_channels(unsigned channel_mask, aa_int *samples)
{
    enum {
        fL  = 0x1,
        fR  = 0x2,
        fC  = 0x4,
        LFE = 0x8,
        bL  = 0x10,
        bR  = 0x20,
        bC  = 0x100,
        sL  = 0x200,
        sR  = 0x400
    };
    void (*a_int_swap)(a_int* a, a_int* b) = samples->_[0]->swap;

    /*reorder channels if necessary based on assignment*/
    switch (channel_mask) {
    default:
        break;
    case (fL | fR | fC):
        /*fL fR fC -> fL fC fR*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (fL | fR | bL | bR):
        /*fL fR bL bR -> fL fR bL bR*/
        /*no change*/
        break;
    case (fL | fR | fC | bL | bR):
        /*fL fR fC bL bR -> fL fC fR bL bR*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (fL | fR | fC | LFE | bL | bR):
        /*fL fR fC LFE bL bR -> fL fR fC LFE bR bL*/
        a_int_swap(samples->_[4], samples->_[5]);

        /*fL fR fC LFE bR bL -> fL fR fC bL bR LFE*/
        a_int_swap(samples->_[3], samples->_[5]);

        /*fL fR fC bL bR LFE -> fL fC fR bL bR LFE*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (fL | fR | fC | LFE | bC | sL | sR):
        /*fL fR fC LFE bC sL sR -> fL fR fC LFE bC sR sL*/
        a_int_swap(samples->_[5], samples->_[6]);

        /*fL fR fC LFE bC sR sL -> fL fR fC LFE sR bC sL*/
        a_int_swap(samples->_[4], samples->_[5]);

        /*fL fR fC LFE sR bC sL -> fL fR fC sL sR bC LFE*/
        a_int_swap(samples->_[3], samples->_[6]);

        /*fL fR fC sL sR bC LFE -> fL fC fR sL sR bC LFE*/
        a_int_swap(samples->_[1], samples->_[2]);
        break;
    case (fL | fR | fC | LFE | bL | bR | sL | sR):
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
    unsigned original_sample_rate = 48000;
    const unsigned sample_rate = 48000;
    const unsigned bits_per_sample = 16;
    pcmreader *pcmreader = NULL;
    result_t result;

    char c;
    const static struct option long_opts[] = {
        {"help",                    no_argument,       NULL, 'h'},
        {"channels",                required_argument, NULL, 'c'},
        {"original-sample-rate",    required_argument, NULL, 'r'},
        {NULL,                      no_argument,       NULL,  0}
    };
    const static char* short_opts = "-hc:";

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
            if (((original_sample_rate =
                  strtoul(optarg, NULL, 10)) == 0) && errno) {
                printf("invalid --original-sample-rate \"%s\"\n", optarg);
                return 1;
            }
            break;
        case 'h': /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: vorbisenc [options] <output.ogg>\n");
            printf("-c, --channels=#          number of input channels\n");
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

    switch (result = encode_opus_file(output_file, pcmreader,
                                      10, original_sample_rate)) {
    case ENCODE_OK:
        break;
    default:
        fprintf(stderr, "*** Error: %d", result);
        break;
    }

    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}
#endif
