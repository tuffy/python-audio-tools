#include "tta.h"
#include "../pcmconv.h"
#include "../common/tta_crc.h"

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

/*returns x/y rounded up
  each argument is evaluated twice*/
#ifndef DIV_CEIL
#define DIV_CEIL(x, y) ((x) / (y) + (((x) % (y)) ? 1 : 0))
#endif

PyObject*
encoders_encode_tta(PyObject *dummy, PyObject *args, PyObject *keywds)
{
    PyObject* file_obj;
    FILE* output_file;
    BitstreamWriter *output;
    pcmreader* pcmreader;
    unsigned block_size;
    array_ia* framelist;
    struct tta_cache cache;
    array_i* frame_sizes;
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
        block_size = (unsigned)DIV_CEIL(
            (uint64_t)(pcmreader->sample_rate * 256), 245);
        output = bw_open(output_file, BS_LITTLE_ENDIAN);
        framelist = array_ia_new();
        cache_init(&cache);
        frame_sizes = array_i_new();
    }

    /*convert PCMReader input to TTA frames*/
    if (pcmreader->read(pcmreader, block_size, framelist))
        goto error;
    while (framelist->_[0]->len) {
        frame_sizes->append(frame_sizes,
                            encode_frame(output,
                                         &cache,
                                         framelist,
                                         pcmreader->bits_per_sample));
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


static void
cache_init(struct tta_cache* cache)
{
    cache->correlated = array_ia_new();
    cache->predicted = array_ia_new();
    cache->residual = array_ia_new();
    cache->k0 = array_i_new();
    cache->sum0 = array_i_new();
    cache->k1 = array_i_new();
    cache->sum1 = array_i_new();
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
             array_ia* framelist,
             unsigned bits_per_sample)
{
    const unsigned channels = framelist->len;
    const unsigned block_size = framelist->_[0]->len;
    unsigned i;
    unsigned c;
    int frame_size = 0;
    uint32_t frame_crc = 0xFFFFFFFF;
    array_i* k0 = cache->k0;
    array_i* sum0 = cache->sum0;
    array_i* k1 = cache->k1;
    array_i* sum1 = cache->sum1;
    array_ia* residual = cache->residual;

    bw_add_callback(output, (bs_callback_func)tta_byte_counter, &frame_size);
    bw_add_callback(output, (bs_callback_func)tta_crc32, &frame_crc);

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
                if ((sum1->_[c] > 0) &&
                    (sum1->_[c] < (1 << (k1->_[c] + 4)))) {
                    k1->_[c] -= 1;
                } else if (sum1->_[c] > (1 << (k1->_[c] + 5))) {
                    k1->_[c] += 1;
                }
            }

            /*update k0 and sum0*/
            sum0->_[c] += u - (sum0->_[c] >> 4);
            if ((sum0->_[c] > 0) &&
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
correlate_channels(array_ia* channels,
                   array_ia* correlated)
{
    const unsigned block_size = channels->_[0]->len;
    unsigned c;

    correlated->reset(correlated);
    for (c = 0; c < channels->len; c++) {
        unsigned i;
        array_i* correlated_ch = correlated->append(correlated);
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
fixed_prediction(array_i* channel,
                 unsigned bits_per_sample,
                 array_i* predicted)
{
    const unsigned block_size = channel->len;
    unsigned i;
    unsigned shift;

    switch (bits_per_sample) {
    case 8:
        shift = 4;
        break;
    case 16:
        shift = 5;
        break;
    case 24:
        shift = 5;
        break;
    default:
        shift = 5;
        break;
    }

    predicted->reset_for(predicted, block_size);
    a_append(predicted, channel->_[0]);
    for (i = 1; i < block_size; i++) {
        const int64_t v = ((((int64_t)channel->_[i - 1]) << shift) -
                           channel->_[i - 1]);
        a_append(predicted, channel->_[i] - (int)(v >> shift));
    }
}

static void
hybrid_filter(array_i* predicted,
              unsigned bits_per_sample,
              array_i* residual)
{
    const unsigned block_size = predicted->len;
    unsigned i;
    int32_t shift;
    int32_t round;
    int32_t qm[] = {0, 0, 0, 0, 0, 0, 0, 0};
    int32_t dx[] = {0, 0, 0, 0, 0, 0, 0, 0};
    int32_t dl[] = {0, 0, 0, 0, 0, 0, 0, 0};

    switch (bits_per_sample) {
    case 8:
        shift = 10;
        break;
    case 16:
        shift = 9;
        break;
    case 24:
        shift = 10;
        break;
    default:
        shift = 10;
        break;
    }
    round = (1 << (shift - 1));
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
