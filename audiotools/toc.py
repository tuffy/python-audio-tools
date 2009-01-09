#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2008-2009  Brian Langenberger

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
from audiotools import SheetException,parse_timestamp,build_timestamp

###################
#TOC Parsing
###################

class TOCException(SheetException): pass

#takes an iterator of lines
#parses the TOCFile lines
#returns a TOCFile object
#or raises TOCException if we hit a parsing error
def parse(lines):
    TRACKLINE = re.compile(r'TRACK AUDIO')

    lines = list(lines)

    if ('CD_DA' not in [line.strip() for line in lines]):
        raise TOCException("no CD_DA TOC header found")

    lines = iter(lines)

    toc = TOCFile()
    track = None
    track_number = 0
    line_number = 0

    try:
        while (True):
            line_number += 1
            line = lines.next().strip()

            if (len(line) == 0):
                pass
            elif (TRACKLINE.match(line)):
                if (track is not None):
                    toc.tracks[track.number] = track
                track_number += 1
                track = Track(track_number)
            else:
                if (track is not None):
                    track.lines.append(line)
                    if (line.startswith('FILE') or
                        line.startswith('AUDIOFILE')):
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
                    toc.lines.append(line)
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

    def catalog(self):
        for line in self.lines:
            if (line.startswith('CATALOG')):
                result = re.search(r'"(.+)"',line)
                if (result is not None):
                    return result.group(1)
                else:
                    continue
        else:
            return None

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

    def single_file_type(self):
        return True

    #returns a track_number->ISRC dict
    #of all tracks whose ISRC is not empty
    def ISRCs(self):
        return dict([(track.number,track.ISRC()) for track in
                     self.tracks.values() if track.ISRC() is not None])

    #takes a sheet-compatible object with
    #catalog(), indexes() and ISRCs() methods
    #along with a filename string
    #returns a string of a newly-generated TOC file
    @classmethod
    def file(cls,sheet,filename):
        import cStringIO

        catalog = sheet.catalog()       #a catalog string, or None
        indexes = list(sheet.indexes()) #a list of index tuples
        ISRCs = sheet.ISRCs()           #a track_number->ISRC dict

        data = cStringIO.StringIO()
        data.write("CD_DA\n\n")

        if ((catalog is not None) and (len(catalog) > 0)):
            data.write("CATALOG \"%s\"\n\n" % (catalog))

        for (i,(current,next)) in enumerate(zip(indexes,indexes[1:] + [None])):
            tracknum = i + 1

            data.write("TRACK AUDIO\n")

            if (tracknum in ISRCs.keys()):
                data.write("ISRC \"%s\"\n" % (ISRCs[tracknum]))

            if (next is not None):
                data.write("AUDIOFILE \"%s\" %s %s\n" % \
                               (filename,
                                build_timestamp(current[0]),
                                build_timestamp(next[0] - current[0])))
            else:
                data.write("AUDIOFILE \"%s\" %s\n" % \
                               (filename,
                                build_timestamp(current[0])))
            if (len(current) > 1):
                data.write("START %s\n" % \
                               (build_timestamp(current[-1] - current[0])))

            if (next is not None):
                data.write("\n")

        return data.getvalue()

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

    #returns the ISRC value of this track, or None if it cannot be found
    def ISRC(self):
        for line in self.lines:
            if (line.startswith('ISRC')):
                match = re.search(r'"(.+)"',line)
                if (match is not None):
                    return match.group(1)
        else:
            return None

def read_tocfile(filename):
    try:
        f = open(filename,'r')
    except IOError,msg:
        raise TOCException(str(msg))
    try:
        return parse(iter(f.readlines()))
    finally:
        f.close()
