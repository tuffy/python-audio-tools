#include "framelist.h"

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

PyObject*
open_audiotools_pcm(void)
{
    return PyImport_ImportModule("audiotools.pcm");
}

pcm_FrameList*
new_FrameList(PyObject* audiotools_pcm,
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames)
{
    /*have audiotools.pcm make an empty FrameList for us*/
    pcm_FrameList *framelist =
        (pcm_FrameList*)empty_FrameList(audiotools_pcm,
                                        channels,
                                        bits_per_sample);

    /*then resize it to hold the requested amount of data*/
    framelist->frames = pcm_frames;
    framelist->samples_length = pcm_frames * framelist->channels;
    framelist->samples = realloc(framelist->samples,
                                 sizeof(int) * framelist->samples_length);

    return framelist;
}

PyObject*
empty_FrameList(PyObject* audiotools_pcm,
                unsigned channels,
                unsigned bits_per_sample)
{
    return PyObject_CallMethod(
        audiotools_pcm,
        "empty_framelist", "ii", channels, bits_per_sample);
}
