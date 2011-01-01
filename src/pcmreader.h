#ifndef STANDALONE
#include <Python.h>
#else
#include <stdio.h>
#endif
#include "array.h"

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

struct pcmr_callback {
    void (*callback)(void*, unsigned char*, unsigned long);
    int is_signed;
    int little_endian;
    void *data;
    struct pcmr_callback *next;
};

struct pcm_reader {
#ifndef STANDALONE
    PyObject *read;
    PyObject *close;
    PyObject *pcm_module;
#else
    FILE *read;
#endif
    long sample_rate;
    long channels;
    long channel_mask;
    long bits_per_sample;
    long big_endian;
    long is_signed;

    struct pcmr_callback *callback;
};

/*given a Python object PCMReader
  return a pcm_reader struct, or NULL (with exception set) if an error occurs*/
#ifndef STANDALONE
struct pcm_reader*
pcmr_open(PyObject *pcmreader);
#else
struct pcm_reader*
pcmr_open(FILE *pcmreader,
          long sample_rate,
          long channels,
          long channel_mask,
          long bits_per_sample,
          long big_endian,
          long is_signed);
#endif

int
pcmr_close(struct pcm_reader *reader);

/*places "sample_count" number of samples from reader.read()
  into the "samples" buffer, after resetting it*/
int
pcmr_read(struct pcm_reader *reader,
          long sample_count,
          struct ia_array *samples);

void
pcmr_add_callback(struct pcm_reader *reader,
                  void (*callback)(void*, unsigned char*, unsigned long),
                  void *data,
                  int is_signed,
                  int little_endian);
