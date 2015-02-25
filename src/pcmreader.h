#ifndef STANDALONE
#include <Python.h>
#include "pcm.h"
#endif
#include <stdio.h>

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

typedef enum {
    PCM_OK,                /*no error has occurred*/
    PCM_READ_ERROR,        /*got exception from wrapped PCMReader*/
    PCM_NON_FRAMELIST,     /*got a non-framelist from wrapped PCMReader*/
    PCM_INVALID_FRAMELIST  /*framelist's parameters don't match stream*/
} pcm_status_t;

struct PCMReader {
    struct {
        struct {
            FILE *file;
            int (*converter)(const unsigned char *raw_pcm_data);
        } raw;
        #ifndef STANDALONE
        struct {
            PyObject *obj;             /*PCMReader object*/
            PyObject *framelist_type;  /*cached FrameList type*/
            int stream_finished;       /*flag indicating stream is empty*/
            pcm_FrameList *framelist;  /*framelist object*/
            unsigned frames_remaining; /*frames remaining in framelist*/
        } python;
        #endif
    } input;

    unsigned sample_rate;
    unsigned channels;
    unsigned channel_mask;
    unsigned bits_per_sample;

    /*current reading status, either PCM_OK
      or one of the error codes*/
    pcm_status_t status;

    /*reads up to the given number of PCM frames
      from this reader to the data array,
      which must be at least:

      pcm_frames * channels

      long in order to hold the returned data

      returns the amount of frames actually read
      which may be less than the number requested

      if an error occurs during reading, 0 is returned
      and the status attribute is set to an error code*/
    unsigned (*read)(struct PCMReader *self,
                     unsigned pcm_frames,
                     int *pcm_data);

    /*forwards a call to "close" to the wrapped PCMReader object*/
    void (*close)(struct PCMReader *self);

    /*decrefs any wrapped PCMReader object and deletes this reader*/
    void (*del)(struct PCMReader *self);
};

/*opens a PCMReader to a raw stream of PCM data*/
struct PCMReader*
pcmreader_open_raw(FILE *file,
                   unsigned sample_rate,
                   unsigned channels,
                   unsigned channel_mask,
                   unsigned bits_per_sample,
                   int is_little_endian,
                   int is_signed);

#ifndef STANDALONE

/*wraps a PCMReader struct around a PCMReader Python object*/
struct PCMReader*
pcmreader_open_python(PyObject *obj);

/*a converter function for use in PyArg_ParseTuple functions*/
int
py_obj_to_pcmreader(PyObject *obj, void **pcmreader);

#endif

/*given an array of channel data at least:

  pcm_frames * channel_count

  large, copies the requested channel to "channel_data" which must be
  "pcm_frames" large*/
void
get_channel_data(const int *pcm_data,
                 unsigned channel_number,
                 unsigned channel_count,
                 unsigned pcm_frames,
                 int *channel_data);

/*displays the PCMReader's parameters for debugging purposes*/
void
pcmreader_display(const struct PCMReader *pcmreader, FILE *output);
