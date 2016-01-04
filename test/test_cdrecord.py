#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2016  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import audiotools
import test_streams
import cPickle

if (__name__ == "__main__"):
    write_offset = audiotools.config.getint_default("System",
                                                    "cdrom_write_offset",
                                                    0)

    sine = audiotools.BufferedPCMReader(
        audiotools.PCMReaderWindow(
            test_streams.Sine16_Stereo(12397980 + 10862124, 44100,
                                       441.0, 0.50,
                                       4410.0, 0.49, 1.0),
            write_offset, 12397980 + 10862124))

    f = open(sys.argv[5], "wb")

    cPickle.dump(audiotools.pcm_frame_cmp(
        audiotools.LimitedPCMReader(sine, 12397980),
        audiotools.open(sys.argv[8]).to_pcm()), f)

    cPickle.dump(audiotools.pcm_frame_cmp(
        audiotools.LimitedPCMReader(sine, 10862124),
        audiotools.open(sys.argv[9]).to_pcm()), f)

    f.close()
