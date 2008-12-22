#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2008  Brian Langenberger

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import re

###################
#TOC Parsing
###################

class TOCException(ValueError): pass

def parse_timestamp(s):
    if (":" in s):
        (m,s,f) = map(int,s.split(":"))
        return (m * 60 * 75) + (s * 75) + f
    else:
        return int(s)

#takes an iterator of lines
#parses the TOCFile lines
#returns a TOCFile object
#or raises TOCException if we hit a parsing error
def parse(lines):
    TRACKLINE = re.compile(r'// Track \d+')

    line_number = 1

    try:
        if (lines.next().rstrip() != 'CD_DA'):
            raise TOCException("invalid TOC file header at line 1")
    except StopIteration:
        raise TOCException("invalid TOC file header at line 1")

    toc = TOCFile()
    track = None

    try:
        while (True):
            line_number += 1
            line = lines.next().rstrip()

            if (len(line) == 0):
                pass
            elif (TRACKLINE.match(line)):
                if (track is not None):
                    toc.tracks[track.number] = track
                track = Track(int(line[len('// Track '):]))
            else:
                if (track is not None):
                    track.lines.append(line)
                    if (line.startswith('FILE')):
                        if ('"' in line):
                            track.indexes = map(parse_timestamp,
                                                re.findall(r'\d+:\d+:\d+|\d+',
                                                           line[line.rindex('"') + 1:]))
                        else:
                            track.indexes = map(parse_timestamp,
                                                re.findall(r'\d+:\d+:\d+|\d+',
                                                           line))
                    elif (line.startswith('START')):
                        track.start = parse_timestamp(line[len('START '):])
                else:
                    TOCFile.lines.append(line)
    except StopIteration:
        if (track is not None):
            toc.tracks[track.number] = track
        return toc

class TOCFile:
    def __init__(self):
        self.lines = []
        self.tracks = {}

    def __repr__(self):
        return "TOCFile(lines=%s,tracks=%s)" % (repr(self.lines),
                                                repr(self.tracks))

    def indexes(self):
        for track in sorted(self.tracks.values()):
            if (track.start != 0):
                yield (track.indexes[0],track.indexes[0] + track.start)
            else:
                yield (track.indexes[0],)

    def pcm_lengths(self, total_length):
        previous = None

        for current in self.indexes():
            if (previous is None):
                previous = current
            else:
                track_length = (max(current) - max(previous)) * (44100 / 75)
                total_length -= track_length
                yield track_length
                previous = current

        yield total_length


class Track:
    def __init__(self, number):
        self.number = number
        self.lines = []
        self.indexes = []
        self.start = 0

    def __cmp__(self,t):
        return cmp(self.number,t.number)

    def __repr__(self):
        return "Track(%s,lines=%s,indexes=%s,start=%s)" % \
            (repr(self.number),repr(self.lines),
             repr(self.indexes),repr(self.start))
