#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

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

from __future__ import print_function
import sys
import audiotools
import test_streams
import re
import cPickle

if (__name__ == "__main__"):
    print(repr(sys.argv))

    write_offset = audiotools.config.getint_default("System",
                                                    "cdrom_write_offset",
                                                    0)

    sine = audiotools.PCMReaderWindow(
        test_streams.Sine16_Stereo(12397980 + 10862124, 44100,
                                   441.0, 0.50,
                                   4410.0, 0.49, 1.0),
        write_offset, 12397980 + 10862124)

    for line in open(sys.argv[6]).readlines():
        match = re.search(r'AUDIOFILE "(.+?)"', line)
        if (match is not None):
            f = open(sys.argv[3], "wb")
            cPickle.dump(
                audiotools.pcm_frame_cmp(
                    sine,
                    audiotools.open(match.group(1)).to_pcm()),
                f)
            f.close()
            sys.exit(0)
    else:
        sys.exit(1)
