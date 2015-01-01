#ifndef STANDALONE
#include <Python.h>
#endif
#include "array.h"
#include "pcm.h"
#include <stdint.h>

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

#ifndef STANDALONE
/******************************************************
               array_* to FrameList utilities
*******************************************************/


/*returns an audiotools.pcm module object for generating blank FrameLists
  or NULL on error
  this must be PyXDECREF()ed once no longer needed*/
PyObject*
open_audiotools_pcm(void);

/*given a list of flattened PCM data,
  returns a new FrameList object containing that data
  with the given number of channels and bits per sample
  which Python will presumably DECREF once no longer needed
  or returns NULL with an exception set on error*/
PyObject*
a_int_to_FrameList(PyObject* audiotools_pcm,
                   a_int* samples,
                   unsigned int channels,
                   unsigned int bits_per_sample);

/*given a list of channel data lists,
  returns a new FrameList object
  which Python will presumably DECREF once no longer needed
  or returns NULL with an exception set on error*/
PyObject*
aa_int_to_FrameList(PyObject* audiotools_pcm,
                    aa_int* channels,
                    unsigned int bits_per_sample);

/*returns an empty FrameList object with the given number of channels
  typically returned at the end of a stream*/
PyObject*
empty_FrameList(PyObject* audiotools_pcm,
                unsigned int channels,
                unsigned int bits_per_sample);


/******************************************************
               PCMReader to array_ia utilities
*******************************************************/


struct pcmreader_callback;
struct pcmreader_s;

/*wraps a low-level pcmreader object
  around the given Python PCMReader object
  or returns NULL with an exception set
  if an error occurs during the wrapping procedure

  the object should be deallocated with  reader->del(reader)  when finished

  Python object is INCREFed by this function
  and DECREFed by del() once no longer in use*/
struct pcmreader_s*
open_pcmreader(PyObject* pcmreader);

/*for use with the PyArg_ParseTuple function*/
int
pcmreader_converter(PyObject* obj, void** pcmreader);

typedef struct pcmreader_s {
    PyObject* pcmreader_obj;
    PyObject* framelist_type;

    unsigned int sample_rate;
    unsigned int channels;
    unsigned int channel_mask;
    unsigned int bits_per_sample;
    unsigned int bytes_per_sample;

    struct pcmreader_callback* callbacks;

    /*reads up to the given number of PCM frames
      to the given set of channel data
      which is reset and appended to as needed

      returns 0 on success, 1 if there's an exception during reading*/
    int (*read)(struct pcmreader_s* reader,
                unsigned pcm_frames,
                aa_int* channels);

    /*forwards a call to "close" to the wrapped PCMReader object*/
    void (*close)(struct pcmreader_s* reader);

    /*adds a callback function to be called on each successful read()
      its first argument is user data
      the second is the PCM data as a string
      with the given signed/endianness values
      the third is the length of that PCM data in bytes*/
    void (*add_callback)(struct pcmreader_s* reader,
                         void (*callback)(void*, unsigned char*, unsigned long),
                         void *user_data,
                         int is_signed,
                         int little_endian);

    /*deletes and decrefs any attached callbacks
      clears any attached buffer
      and decrefs any wrapped PCMReader objects*/
    void (*del)(struct pcmreader_s* reader);
} pcmreader;

#else

struct pcmreader_callback;
struct pcmreader_s;

/*wraps a low-level pcmreader object
  around the given file object of PCM data

  the object should be deallocated with  reader->del(reader)  when finished*/
struct pcmreader_s* open_pcmreader(FILE* file,
                                   unsigned int sample_rate,
                                   unsigned int channels,
                                   unsigned int channel_mask,
                                   unsigned int bits_per_sample,
                                   unsigned int big_endian,
                                   unsigned int is_signed);

typedef struct pcmreader_s {
    FILE* file;

    unsigned int sample_rate;
    unsigned int channels;
    unsigned int channel_mask;
    unsigned int bits_per_sample;
    unsigned int bytes_per_sample;

    unsigned int big_endian;
    unsigned int is_signed;

    unsigned buffer_size;
    uint8_t* buffer;
    unsigned callback_buffer_size;
    uint8_t* callback_buffer;
    FrameList_char_to_int_converter buffer_converter;

    struct pcmreader_callback* callbacks;

    /*reads up to the given number of PCM frames
      to the given set of channel data
      which is reset and appended to as needed

      returns 0 on success, 1 if there's an exception during reading*/
    int (*read)(struct pcmreader_s* reader,
                 unsigned pcm_frames,
                 aa_int* channels);

    /*forwards a call to "close" to the wrapped PCMReader object*/
    void (*close)(struct pcmreader_s* reader);

    /*adds a callback function to be called on each successful read()
      its first argument is user data
      the second is the PCM data as a string
      with the given signed/endianness values
      the third is the length of that PCM data in bytes*/
    void (*add_callback)(struct pcmreader_s* reader,
                         void (*callback)(void*, unsigned char*, unsigned long),
                         void *user_data,
                         int is_signed,
                         int little_endian);

    /*deletes and decrefs any attached callbacks
      clears any attached buffer
      and decrefs any wrapped PCMReader objects*/
    void (*del)(struct pcmreader_s* reader);
} pcmreader;

#endif

int pcmreader_read(struct pcmreader_s* reader,
                   unsigned pcm_frames,
                   aa_int* channels);

void pcmreader_close(struct pcmreader_s* reader);

void pcmreader_add_callback(struct pcmreader_s* reader,
                            void (*callback)(void*,
                                             unsigned char*,
                                             unsigned long),
                            void *user_data,
                            int is_signed,
                            int little_endian);

void pcmreader_del(struct pcmreader_s* reader);

struct pcmreader_callback {
    void (*callback)(void*, unsigned char*, unsigned long);
    int is_signed;
    int little_endian;
    void *user_data;
    struct pcmreader_callback *next;
};
