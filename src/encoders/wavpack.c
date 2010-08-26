#include "wavpack.h"
#include "../pcmreader.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

PyObject*
encoders_encode_wavpack(PyObject *dummy,
                        PyObject *args, PyObject *keywds) {
    char *filename;
    FILE *file;
    Bitstream *stream;
    PyObject *pcmreader_obj;
    struct pcm_reader *reader;

    struct ia_array samples;

    int block_size;
    static char *kwlist[] = {"filename",
                             "pcmreader",
                             "block_size",
                             NULL};
    if (!PyArg_ParseTupleAndKeywords(args,
                                     keywds,
                                     "sOi",
                                     kwlist,
                                     &filename,
                                     &pcmreader_obj,
                                     &block_size))
        return NULL;

    if (block_size <= 0) {
        PyErr_SetString(PyExc_ValueError, "block_size must be positive");
        return NULL;
    }

    /*open the given filename for writing*/
    if ((file = fopen(filename, "wb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return NULL;
    } else {
        stream = bs_open(file, BS_LITTLE_ENDIAN);
    }

    /*transform the Python PCMReader-compatible object to a pcm_reader struct*/
    if ((reader = pcmr_open(pcmreader_obj)) == NULL) {
        fclose(file);
        return NULL;
    }

    iaa_init(&samples, reader->channels, block_size);

    /*build frames until reader is empty
      (WavPack doesn't have actual frames as such; it has sets of
       blocks joined by first-block/last-block bits in the header.
       However, I'll call that arrangement a "frame" for clarity.)*/
    if (!pcmr_read(reader, block_size, &samples))
        goto error;

    while (samples.arrays[0].size > 0) {
        WavPackEncoder_write_frame(stream, &samples, reader->channel_mask);

        if (!pcmr_read(reader, block_size, &samples))
            goto error;
    }

    /*go back and set block header data as necessary*/

    /*close open file handles and deallocate temporary space*/
    pcmr_close(reader);
    bs_close(stream);

    Py_INCREF(Py_None);
    return Py_None;

 error:
    pcmr_close(reader);
    bs_close(stream);
    return NULL;
}

static int
count_bits(int i) {
    int bits;

    for (bits = 0; i != 0; i >>= 1)
        bits += (i & 1);

    return bits;
}

void
WavPackEncoder_channel_splits(struct i_array *counts,
                              int channel_count,
                              long channel_mask) {
    /*Although the WAVEFORMATEXTENSIBLE channel mask
      supports more left/right channels than these,
      everything beyond side-left/side-right
      is stored with a center channel in-between
      which means WavPack can't pull them apart in pairs.*/
    long masks[] = {0x3,   0x1,   0x2,        /*fLfR, fL, fR*/
                    0x4,   0x8,               /*fC, LFE*/
                    0x30,  0x10,  0x20,       /*bLbR, bL, bR*/
                    0xC0,  0x40,  0x80,       /*fLoCfRoC, fLoC, fRoC*/
                    0x100,                    /*bC*/
                    0x600, 0x200, 0x400,      /*sLsR, sL, sR*/
                    0};
    int channels;
    int i;

    /*first, try to pull left/right channels out of the mask*/
    for (i = 0; channel_mask && masks[i]; i++) {
        if (channel_mask & masks[i]) {
            channels = count_bits(masks[i]);
            ia_append(counts, channels);
            channel_count -= channels;
            channel_mask ^= masks[i];
        }
    }

    /*any leftover samples are sent out in separate blocks
      (which may happen with a mask of 0)*/
    for (; channel_count > 0; channel_count--) {
        ia_append(counts, 1);
    }
}

void
WavPackEncoder_write_frame(Bitstream *bs,
                           struct ia_array *samples,
                           long channel_mask) {
    struct i_array counts;
    int current_channel;
    int i;

    ia_init(&counts, 1);

    fprintf(stderr, "writing %d channels of %d samples\n",
            samples->size, samples->arrays[0].size);
    WavPackEncoder_channel_splits(&counts, samples->size, channel_mask);

    fprintf(stderr, "channel counts : ");
    ia_print(stderr, &counts);
    fprintf(stderr, "\n");

    for (i = current_channel = 0; i < counts.size; i++) {
        WavPackEncoder_write_block(bs,
                                   &(samples->arrays[current_channel]),
                                   counts.data[i] == 2 ?
                                   &(samples->arrays[current_channel + 1]) :
                                   NULL,
                                   counts.data[i],
                                   i == 0,
                                   i == (counts.size - 1));
        current_channel += counts.data[i];
    }

    ia_free(&counts);

}

void
WavPackEncoder_write_block(Bitstream *bs,
                           struct i_array *channel_A,
                           struct i_array *channel_B,
                           int channel_count,
                           int first_block,
                           int last_block) {
    fprintf(stderr, "writing block with channels = %d\n", channel_count);
    fprintf(stderr, "first block = %d\n", first_block);
    fprintf(stderr, "last block = %d\n", last_block);
    return;
}
