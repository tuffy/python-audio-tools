#ifndef STANDALONE
#include <Python.h>
#endif
#include "array2.h"
#include "pcm.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2011  Brian Langenberger

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

/***************************************************************
      PCM reading functions

 these wrap around a Python PCMReader
 and perform the low-level task of converting Python FrameLists
 returned by pcmreader.read() to an ia_array struct
****************************************************************/

struct pcmr_callback2 {
    void (*callback)(void*, unsigned char*, unsigned long);
    int is_signed;
    int little_endian;
    void *data;
    struct pcmr_callback2 *next;
};

struct pcm_reader2 {
#ifndef STANDALONE
    PyObject *pcmreader;
    PyObject *framelist_type;
#else
    FILE *file;
#endif

    unsigned int sample_rate;
    unsigned int channels;
    unsigned int channel_mask;
    unsigned int bits_per_sample;
    unsigned int big_endian;
    unsigned int is_signed;

    unsigned int bytes_per_sample;

    struct pcmr_callback2* callback;

    unsigned buffer_size;

#ifndef STANDALONE
    uint8_t* buffer;
    FrameList_char_to_int_converter buffer_converter;
#endif

    uint8_t* callback_buffer;
};

#ifndef STANDALONE
struct pcm_reader2*
pcmr_open2(PyObject *pcmreader);
#else
struct pcm_reader2*
pcmr_open2(FILE *file,
           unsigned int sample_rate,
           unsigned int channels,
           unsigned int channel_mask,
           unsigned int bits_per_sample,
           unsigned int big_endian,
           unsigned int is_signed);
#endif

int
pcmr_close2(struct pcm_reader2 *reader);

int
pcmr_read2(struct pcm_reader2 *reader,
           unsigned pcm_frames,
           array_ia* samples);

void
pcmr_add_callback2(struct pcm_reader2 *reader,
                   void (*callback)(void*, unsigned char*, unsigned long),
                   void *data,
                   int is_signed,
                   int little_endian);
