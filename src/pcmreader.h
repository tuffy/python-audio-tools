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

/*This module is for abstracting away PCM reading
  for use by audio encoding routines so that they don't have
  to make calls to a PCMReader object directly*/

typedef enum {
    PCM_OK,                /*no error has occurred*/
    PCM_READ_ERROR,        /*got exception from wrapped PCMReader*/
    PCM_NON_FRAMELIST,     /*got a non-framelist from wrapped PCMReader*/
    PCM_INVALID_FRAMELIST  /*framelist's parameters don't match stream*/
} pcm_status_t;

struct PCMReader {
    struct {
        #ifdef STANDALONE
        struct {
            FILE *file;
            int (*converter)(const unsigned char *raw_pcm_data);
        } raw;
        struct {
            FILE *file;
            int (*converter)(const unsigned char *raw_pcm_data);
            unsigned total_pcm_frames;
        } error;
        #else
        struct {
            PyObject *obj;             /*PCMReader object*/
            PyObject *framelist_type;  /*cached FrameList type*/
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

#ifdef STANDALONE
/*opens a PCMReader to a raw stream of PCM data*/
struct PCMReader*
pcmreader_open_raw(FILE *file,
                   unsigned sample_rate,
                   unsigned channels,
                   unsigned channel_mask,
                   unsigned bits_per_sample,
                   int is_little_endian,
                   int is_signed);

struct PCMReader*
pcmreader_open_error(FILE *file,
                     unsigned sample_rate,
                     unsigned channels,
                     unsigned channel_mask,
                     unsigned bits_per_sample,
                     int is_little_endian,
                     int is_signed,
                     unsigned total_pcm_frames);

#else

/*wraps a PCMReader struct around a PCMReader Python object*/
struct PCMReader*
pcmreader_open_python(PyObject *obj);

/*a converter function for use in PyArg_ParseTuple functions*/
int
py_obj_to_pcmreader(PyObject *obj, void **pcmreader);

#endif

/*pcm_data must contain at least:  channel_count * pcm_frames  entries

  channel_data must contain at least:  pcm_frames  entries

  copies a channel's worth of data from pcm_data to channel_data*/
void
get_channel_data(const int *pcm_data,
                 unsigned channel_number,
                 unsigned channel_count,
                 unsigned pcm_frames,
                 int *channel_data);

/*constructs a channel of empty data*/
void
blank_channel_data(unsigned pcm_frames, int *channel_data);

static inline int
get_sample(const int *pcm_data,
           unsigned channel_number,
           unsigned channel_count,
           unsigned pcm_frame)
{
    return pcm_data[(pcm_frame * channel_count) + channel_number];
}

/*displays the PCMReader's parameters for debugging purposes*/
void
pcmreader_display(const struct PCMReader *pcmreader, FILE *output);
