#include <Python.h>
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

/*This module is for abstracting away pcm.FrameList generation
  for use by audio decoding routines so that they don't have
  to make calls to audiotools.pcm.empty_framelist() directly.

  By returning pcm_FrameList structs, decoders can populate
  them directly in order to save a copying step.*/

/*returns an audiotools.pcm module object for generating blank FrameLists
  or NULL on error
  this must be PyXDECREF()ed once no longer needed*/
PyObject*
open_audiotools_pcm(void);

/*returns a new FrameList object with the given size
  meant for population by an audio decoding routine

  returns NULL if some error occurs getting new FrameList

  it can be cast to PyObject* for returning*/
pcm_FrameList*
new_FrameList(PyObject* audiotools_pcm,
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames);

/*returns an empty FrameList object with the given number of channels
  typically returned at the end of a stream*/
PyObject*
empty_FrameList(PyObject* audiotools_pcm,
                unsigned channels,
                unsigned bits_per_sample);

/*pcm_data must contain at least:  channel_count * pcm_frames  entries

  channel_data must contain at least:  pcm_frames  entries

  copies a channel's worth of data from channel_data to pcm_data*/
void
put_channel_data(int *pcm_data,
                 unsigned channel_number,
                 unsigned channel_count,
                 unsigned pcm_frames,
                 const int *channel_data);
