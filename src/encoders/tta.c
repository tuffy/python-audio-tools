#include "tta.h"
#include "../pcmconv.h"
#include "../common/tta_crc.h"

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

/*returns x/y rounded up
  each argument is evaluated twice*/
#ifndef DIV_CEIL
#define DIV_CEIL(x, y) ((x) / (y) + (((x) % (y)) ? 1 : 0))
#endif

#ifndef STANDALONE
PyObject*
encoders_encode_tta(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    PyObject* file_obj;
    FILE* output_file;
    BitstreamWriter *output;
    pcmreader* pcmreader;
    unsigned block_size;
    aa_int* framelist;
    struct tta_cache cache;
    a_int* frame_sizes;
    PyObject* frame_sizes_obj;
    unsigned i;
    static char *kwlist[] = {"file",
                             "pcmreader",
                             NULL};

    if (!PyArg_ParseTupleAndKeywords(
            args, keywds, "OO&", kwlist,
            &file_obj,
            pcmreader_converter,
            &pcmreader))
        return NULL;

    /*convert file object to bitstream writer*/
    if ((output_file = PyFile_AsFile(file_obj)) == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "file must by a concrete file object");
        return NULL;
    } else {
        /*initialize temporary buffers*/
        block_size = (pcmreader->sample_rate * 256) / 245;
        output = bw_open(output_file, BS_LITTLE_ENDIAN);
        framelist = aa_int_new();
        cache_init(&cache);
        frame_sizes = a_int_new();
    }

    /*convert PCMReader input to TTA frames*/
    if (pcmreader->read(pcmreader, block_size, framelist))
        goto error;
    while (framelist->_[0]->len) {
        Py_BEGIN_ALLOW_THREADS
        frame_sizes->append(frame_sizes,
                            encode_frame(output,
                                         &cache,
                                         framelist,
                                         pcmreader->bits_per_sample));
        Py_END_ALLOW_THREADS
        if (pcmreader->read(pcmreader, block_size, framelist))
            goto error;
    }

    /*convert list of frame sizes to Python list of integers*/
    frame_sizes_obj = PyList_New(0);
    for (i = 0; i < frame_sizes->len; i++) {
        PyObject* size = PyInt_FromLong((long)frame_sizes->_[i]);
        if (PyList_Append(frame_sizes_obj, size)) {
            Py_DECREF(frame_sizes_obj);
            Py_DECREF(size);
            goto error;
        } else {
            Py_DECREF(size);
        }
    }

    /*free temporary buffers*/
    framelist->del(framelist);
    cache_free(&cache);
    frame_sizes->del(frame_sizes);
    pcmreader->del(pcmreader);

    /*return list of frame size integers*/
    return frame_sizes_obj;
error:
    /*free temporary buffers*/
    framelist->del(framelist);
    cache_free(&cache);
    frame_sizes->del(frame_sizes);
    pcmreader->del(pcmreader);

    /*return exception*/
    return NULL;
}
#endif


static void
cache_init(struct tta_cache* cache)
{
    cache->correlated = aa_int_new();
    cache->predicted = aa_int_new();
    cache->residual = aa_int_new();
    cache->k0 = a_int_new();
    cache->sum0 = a_int_new();
    cache->k1 = a_int_new();
    cache->sum1 = a_int_new();
}


static void
cache_free(struct tta_cache* cache)
{
    cache->correlated->del(cache->correlated);
    cache->predicted->del(cache->predicted);
    cache->residual->del(cache->residual);
    cache->k0->del(cache->k0);
    cache->sum0->del(cache->sum0);
    cache->k1->del(cache->k1);
    cache->sum1->del(cache->sum1);
}


int
encode_frame(BitstreamWriter* output,
             struct tta_cache* cache,
             const aa_int* framelist,
             unsigned bits_per_sample)
{
    const unsigned channels = framelist->len;
    const unsigned block_size = framelist->_[0]->len;
    unsigned i;
    unsigned c;
    int frame_size = 0;
    uint32_t frame_crc = 0xFFFFFFFF;
    a_int* k0 = cache->k0;
    a_int* sum0 = cache->sum0;
    a_int* k1 = cache->k1;
    a_int* sum1 = cache->sum1;
    aa_int* residual = cache->residual;

    bw_add_callback(output, (bs_callback_f)tta_byte_counter, &frame_size);
    bw_add_callback(output, (bs_callback_f)tta_crc32, &frame_crc);

    cache->predicted->reset(cache->predicted);
    residual->reset(residual);

    if (channels == 1) {
        /*run fixed order prediction on correlated channels*/
        fixed_prediction(framelist->_[0],
                         bits_per_sample,
                         cache->predicted->append(cache->predicted));

        /*run hybrid filter on predicted channels*/
        hybrid_filter(cache->predicted->_[0],
                      bits_per_sample,
                      residual->append(residual));
    } else {
        /*correlate channels*/
        correlate_channels(framelist, cache->correlated);

        for (c = 0; c < channels; c++) {
            /*run fixed order prediction on correlated channels*/
            fixed_prediction(cache->correlated->_[c],
                             bits_per_sample,
                             cache->predicted->append(cache->predicted));

            /*run hybrid filter on predicted channels*/
            hybrid_filter(cache->predicted->_[c],
                          bits_per_sample,
                          residual->append(residual));
        }
    }

    /*setup Rice parameters*/
    k0->mset(k0, channels, 10);
    sum0->mset(sum0, channels, (1 << 14));
    k1->mset(k1, channels, 10);
    sum1->mset(sum1, channels, (1 << 14));

    /*encode residuals*/
    for (i = 0; i < block_size; i++) {
        for (c = 0; c < channels; c++) {
            const int r = residual->_[c]->_[i];
            unsigned u;

            /*convert from signed to unsigned*/
            if (r > 0) {
                u = (r * 2) - 1;
            } else {
                u = (-r) * 2;
            }

            if (u < (1 << k0->_[c])) {
                /*write MSB and LSB values*/
                output->write_unary(output, 0, 0);
                output->write(output, k0->_[c], u);
            } else {
                /*write MSB and LSB values*/
                const unsigned shifted = u - (1 << k0->_[c]);
                const unsigned MSB = 1 + (shifted >> k1->_[c]);
                const unsigned LSB = shifted - ((MSB - 1) << k1->_[c]);

                output->write_unary(output, 0, MSB);
                output->write(output, k1->_[c], LSB);

                /*update k1 and sum1*/
                sum1->_[c] += shifted - (sum1->_[c] >> 4);
                if ((k1->_[c] > 0) &&
                    (sum1->_[c] < (1 << (k1->_[c] + 4)))) {
                    k1->_[c] -= 1;
                } else if (sum1->_[c] > (1 << (k1->_[c] + 5))) {
                    k1->_[c] += 1;
                }
            }

            /*update k0 and sum0*/
            sum0->_[c] += u - (sum0->_[c] >> 4);
            if ((k0->_[c] > 0) &&
                (sum0->_[c] < (1 << (k0->_[c] + 4)))) {
                k0->_[c] -= 1;
            } else if (sum0->_[c] > (1 << (k0->_[c] + 5))) {
                k0->_[c] += 1;
            }

        }
    }

    /*byte align output*/
    output->byte_align(output);

    /*write calculate CRC32 value*/
    bw_pop_callback(output, NULL);
    output->write(output, 32, frame_crc ^ 0xFFFFFFFF);

    bw_pop_callback(output, NULL);

    return frame_size;
}

static void
correlate_channels(const aa_int* channels,
                   aa_int* correlated)
{
    const unsigned block_size = channels->_[0]->len;
    unsigned c;

    correlated->reset(correlated);
    for (c = 0; c < channels->len; c++) {
        unsigned i;
        a_int* correlated_ch = correlated->append(correlated);
        correlated_ch->resize(correlated_ch, block_size);

        if (c < (channels->len - 1)) {
            for (i = 0; i < block_size; i++) {
                a_append(correlated_ch,
                         channels->_[c + 1]->_[i] - channels->_[c]->_[i]);
            }
        } else {
            for (i = 0; i < block_size; i++) {
                a_append(correlated_ch,
                         channels->_[c]->_[i] -
                         (correlated->_[c - 1]->_[i] / 2));
            }
        }
    }
}

static void
fixed_prediction(const a_int* channel,
                 unsigned bits_per_sample,
                 a_int* predicted)
{
    const unsigned block_size = channel->len;
    const unsigned shift = (bits_per_sample == 8) ? 4 : 5;
    unsigned i;

    predicted->reset_for(predicted, block_size);
    a_append(predicted, channel->_[0]);
    for (i = 1; i < block_size; i++) {
        const int64_t v = ((((int64_t)channel->_[i - 1]) << shift) -
                           channel->_[i - 1]);
        a_append(predicted, channel->_[i] - (int)(v >> shift));
    }
}

static void
hybrid_filter(const a_int* predicted,
              unsigned bits_per_sample,
              a_int* residual)
{
    const unsigned block_size = predicted->len;
    const int32_t shift = (bits_per_sample == 16) ? 9 : 10;
    const int32_t round = (1 << (shift - 1));
    int32_t qm[] = {0, 0, 0, 0, 0, 0, 0, 0};
    int32_t dx[] = {0, 0, 0, 0, 0, 0, 0, 0};
    int32_t dl[] = {0, 0, 0, 0, 0, 0, 0, 0};
    unsigned i;

    residual->reset_for(residual, block_size);

    for (i = 0; i < block_size; i++) {
        int p;
        int r;

        if (i == 0) {
            p = predicted->_[0];
            r = p + (round >> shift);
        } else {
            int64_t sum;

            if (residual->_[i - 1] < 0) {
                qm[0] -= dx[0];
                qm[1] -= dx[1];
                qm[2] -= dx[2];
                qm[3] -= dx[3];
                qm[4] -= dx[4];
                qm[5] -= dx[5];
                qm[6] -= dx[6];
                qm[7] -= dx[7];
            } else if (residual->_[i - 1] > 0) {
                qm[0] += dx[0];
                qm[1] += dx[1];
                qm[2] += dx[2];
                qm[3] += dx[3];
                qm[4] += dx[4];
                qm[5] += dx[5];
                qm[6] += dx[6];
                qm[7] += dx[7];
            }

            sum = round + (dl[0] * qm[0]) +
                          (dl[1] * qm[1]) +
                          (dl[2] * qm[2]) +
                          (dl[3] * qm[3]) +
                          (dl[4] * qm[4]) +
                          (dl[5] * qm[5]) +
                          (dl[6] * qm[6]) +
                          (dl[7] * qm[7]);

            p = predicted->_[i];
            r = p - (int)(sum >> shift);
        }
        a_append(residual, r);

        dx[0] = dx[1];
        dx[1] = dx[2];
        dx[2] = dx[3];
        dx[3] = dx[4];
        dx[4] = (dl[4] >= 0) ? 1 : -1;
        dx[5] = (dl[5] >= 0) ? 2 : -2;
        dx[6] = (dl[6] >= 0) ? 2 : -2;
        dx[7] = (dl[7] >= 0) ? 4 : -4;
        dl[0] = dl[1];
        dl[1] = dl[2];
        dl[2] = dl[3];
        dl[3] = dl[4];
        dl[4] = -dl[5] + (-dl[6] + (p - dl[7]));
        dl[5] = -dl[6] + (p - dl[7]);
        dl[6] = p - dl[7];
        dl[7] = p;
    }
}

void
tta_byte_counter(uint8_t byte, int* frame_size)
{
    *frame_size += 1;
}

#ifdef STANDALONE
#include <getopt.h>
#include <string.h>
#include <errno.h>

int main(int argc, char* argv[]) {
    char* output_file = NULL;
    unsigned channels = 2;
    unsigned sample_rate = 44100;
    unsigned bits_per_sample = 16;
    unsigned total_pcm_frames = 0;

    unsigned total_tta_frames;
    unsigned block_size;

    FILE* file;
    BitstreamWriter* writer;
    a_int* tta_frame_sizes;
    pcmreader* pcmreader;
    aa_int* framelist;
    struct tta_cache cache;
    unsigned written_pcm_frames = 0;

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
    if (output_file == NULL) {
        printf("exactly 1 output file required\n");
        return 1;
    }

    assert(channels > 0);
    assert((bits_per_sample == 8) ||
           (bits_per_sample == 16) ||
           (bits_per_sample == 24));
    assert(sample_rate > 0);
    assert(total_pcm_frames > 0);

    printf("Encoding from stdin using parameters:\n");
    printf("channels         %u\n", channels);
    printf("sample rate      %u\n", sample_rate);
    printf("bits-per-sample  %u\n", bits_per_sample);
    printf("total PCM frames %u\n", total_pcm_frames);
    printf("little-endian, signed samples\n");

    block_size = (sample_rate * 256) / 245;

    total_tta_frames = DIV_CEIL(total_pcm_frames, block_size);
    printf("block size       %u\n", block_size);
    printf("total TTA frames %u\n", total_tta_frames);

    /*open output file for writing*/
    if ((file = fopen(output_file, "wb")) == NULL) {
        fprintf(stderr, "* %s: %s", output_file, strerror(errno));
        return 1;
    } else {
        /*allocate temporary buffers*/
        writer = bw_open(file, BS_LITTLE_ENDIAN);
        tta_frame_sizes = a_int_new();
        framelist = aa_int_new();
        cache_init(&cache);
    }

    /*write TTA header*/
    write_header(writer,
                 channels,
                 bits_per_sample,
                 sample_rate,
                 total_pcm_frames);

    /*write placeholder seektable*/
    tta_frame_sizes->mset(tta_frame_sizes, total_tta_frames, 0);
    write_seektable(writer, tta_frame_sizes);
    tta_frame_sizes->reset(tta_frame_sizes);

    /*write frames from PCMReader*/
    pcmreader = open_pcmreader(stdin,
                               sample_rate,
                               channels,
                               0,
                               bits_per_sample,
                               0,
                               1);
    pcmreader->read(pcmreader, block_size, framelist);
    while (framelist->_[0]->len) {
        /*actual size may be different from requested block size*/
        written_pcm_frames += framelist->_[0]->len;
        tta_frame_sizes->append(tta_frame_sizes,
                                encode_frame(writer,
                                             &cache,
                                             framelist,
                                             bits_per_sample));
        pcmreader->read(pcmreader, block_size, framelist);
    }

    /*ensure read frames are a match for --total-pcm-frames*/
    assert(written_pcm_frames == total_pcm_frames);
    assert(tta_frame_sizes->len == total_tta_frames);

    /*go back and write proper seektable*/
    fseek(file, 22, SEEK_SET);
    write_seektable(writer, tta_frame_sizes);

    /*deallocate temporary buffers*/
    pcmreader->del(pcmreader);
    tta_frame_sizes->del(tta_frame_sizes);
    framelist->del(framelist);
    cache_free(&cache);

    /*close output file*/
    writer->close(writer);

    return 0;
}

static void
write_header(BitstreamWriter* output,
             unsigned channels,
             unsigned bits_per_sample,
             unsigned sample_rate,
             unsigned total_pcm_frames)
{
    unsigned header_crc = 0xFFFFFFFF;
    bw_add_callback(output, (bs_callback_f)tta_crc32, &header_crc);
    output->build(output, "4b 16u 16u 16u 32u 32u",
                  "TTA1",
                  1,
                  channels,
                  bits_per_sample,
                  sample_rate,
                  total_pcm_frames);
    bw_pop_callback(output, NULL);
    output->write(output, 32, header_crc ^ 0xFFFFFFFF);
}

static void
write_seektable(BitstreamWriter* output,
                const a_int* frame_sizes)
{
    unsigned i;
    unsigned seektable_crc = 0xFFFFFFFF;
    bw_add_callback(output, (bs_callback_f)tta_crc32, &seektable_crc);
    for (i = 0; i < frame_sizes->len; i++) {
        output->write(output, 32, frame_sizes->_[i]);
    }
    bw_pop_callback(output, NULL);
    output->write(output, 32, seektable_crc ^ 0xFFFFFFFF);
}


#include "../common/tta_crc.c"
#endif
