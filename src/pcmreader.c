#include <stdlib.h>
#include "pcmreader.h"
#include "pcm.h"

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

static unsigned
pcmreader_read(struct PCMReader *self,
               unsigned pcm_frames,
               int *pcm_data);

static void
pcmreader_close(struct PCMReader *self);

static void
pcmreader_del(struct PCMReader *self);


struct PCMReader*
pcmreader_open(FILE *file,
               unsigned sample_rate,
               unsigned channels,
               unsigned channel_mask,
               unsigned bits_per_sample,
               int is_little_endian,
               int is_signed)
{
    struct PCMReader *reader = malloc(sizeof(struct PCMReader));
    reader->raw_data = file;
    reader->sample_rate = sample_rate;
    reader->channels = channels;
    reader->channel_mask = channel_mask;
    reader->bits_per_sample = bits_per_sample;

    reader->bytes_per_sample = bits_per_sample / 8;
    reader->converter =
        FrameList_get_char_to_int_converter(bits_per_sample,
                                            !is_little_endian,
                                            is_signed);

    reader->read = pcmreader_read;
    reader->close = pcmreader_close;
    reader->del = pcmreader_del;
    return reader;
}

void
get_channel_data(const int *pcm_data,
                 unsigned channel_number,
                 unsigned channel_count,
                 unsigned pcm_frames,
                 int *channel_data)
{
    pcm_data += channel_number;
    for (; pcm_frames; pcm_frames--) {
        *channel_data = *pcm_data;
        pcm_data += channel_count;
        channel_data += 1;
    }
}

void
pcmreader_display(const struct PCMReader *pcmreader, FILE *output)
{
    fprintf(output, "sample_rate      %u\n", pcmreader->sample_rate);
    fprintf(output, "channels         %u\n", pcmreader->channels);
    fprintf(output, "channel mask     %u\n", pcmreader->channel_mask);
    fprintf(output, "bits-per-sample  %u\n", pcmreader->bits_per_sample);
}


static unsigned
pcmreader_read(struct PCMReader *self,
               unsigned pcm_frames,
               int *pcm_data)
{
    const register unsigned bytes_per_sample = self->bytes_per_sample;

    int (*converter)(unsigned char *) = self->converter;

    const unsigned bytes_to_read =
        pcm_frames * bytes_per_sample * self->channels;

    unsigned char buffer[bytes_to_read];

    const size_t bytes_read =
        fread(buffer, sizeof(unsigned char), bytes_to_read, self->raw_data);

    const unsigned pcm_frames_read =
        bytes_read / bytes_per_sample / self->channels;

    /*cull partial PCM frames*/
    const unsigned samples_read = pcm_frames_read * self->channels;

    register unsigned i;
    for (i = 0; i < samples_read; i++) {
        *pcm_data = converter(buffer + (i * bytes_per_sample));
        pcm_data += 1;
    }

    return pcm_frames_read;
}

static void
pcmreader_close(struct PCMReader *self)
{
    fclose(self->raw_data);
}

static void
pcmreader_del(struct PCMReader *self)
{
    free(self);
}

#ifdef EXECUTABLE

#define BLOCKSIZE 48000

int main(int argc, char *argv[])
{
    struct PCMReader *pcmreader = pcmreader_open(stdin,
                                                 44100,
                                                 2,
                                                 0,
                                                 16,
                                                 1,
                                                 1);
    int pcm_data[2 * BLOCKSIZE];
    unsigned pcm_frames;

    while ((pcm_frames = pcmreader->read(pcmreader,
                                         BLOCKSIZE,
                                         pcm_data)) > 0) {
        unsigned i;
        for (i = 0; i < pcm_frames; i++) {
            printf("%6d  %6d\n",
                   pcm_data[i * 2],
                   pcm_data[i * 2 + 1]);
        }
    }

    pcmreader->close(pcmreader);
    pcmreader->del(pcmreader);

    return 0;
}

#endif
