#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2008-2013  Brian Langenberger

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

"""the TOC file handling module"""

from . import SheetException

###################
#TOC Parsing
###################


class TOCException(SheetException):
    """raised by TOC file parsing errors"""

    pass


def parse(lines):
    """returns a TOCFile object from an iterator of lines

    raises TOCException if some problem occurs parsing the file"""

    import re
    from fractions import Fraction
    from audiotools import parse_timestamp, Sheet, SheetTrack, SheetIndex

    AUDIOFILE = re.compile(
        r'(AUDIO)?FILE\s*".*?"\s*(\d+:\d+:\d+|\d+)\s*(\d+:\d+:\d+|\d+)?')
    ISRC = re.compile(r'ISRC\s*"(.*)"')
    START = re.compile(r'START\s*(\d+:\d+:\d+|\d+)')
    INDEX = re.compile(r'INDEX\s*(\d+:\d+:\d+|\d+)')

    def make_indexes(index_start, index_offsets):
        for (number, offset) in enumerate(index_offsets, index_start):
            yield SheetIndex(number, Fraction(offset, 75))

    lines = list(lines)

    #FIXME - make this less stupid
    if ('CD_DA' not in [line.strip() for line in lines]):
        from .text import ERR_TOC_NO_HEADER
        raise TOCException(ERR_TOC_NO_HEADER)

    lines = iter(lines)

    cuesheet_tracks = []
    cuesheet_catalog_number = None

    track_number = None
    track_audio = True
    track_ISRC = None

    index_start = 1
    index_offsets = []

    line_number = 0

    try:
        while (True):
            line_number += 1
            line = lines.next().strip()

            if (len(line) == 0):
                pass
            elif (line == "TRACK AUDIO"):
                #start a new track
                if (track_number is not None):
                    cuesheet_tracks.append(
                        SheetTrack(track_number,
                                   list(make_indexes(index_start,
                                                     index_offsets)),
                                   track_audio,
                                   track_ISRC))
                    track_number += 1
                    track_indexes = []
                    track_audio = True
                    track_ISRC = None
                else:
                    track_number = 1
            elif (track_number is not None):
                #first index, which may be 1 or 0
                first_index = AUDIOFILE.match(line)
                if (first_index is not None):
                    index_start = 1
                    index_offsets = [parse_timestamp(first_index.group(2))]
                    continue

                start = START.match(line)
                if (start is not None):
                    #first index point is number 0
                    #and add a new index point number 1
                    assert(len(index_offsets) == 1)
                    index_start = 0
                    index_offsets.append(
                        index_offsets[0] + parse_timestamp(start.group(1)))
                    continue

                index = INDEX.match(line)
                if (index is not None):
                    #add a new index point
                    index_offsets.append(parse_timestamp(index.group(1)))
                    continue

                isrc = ISRC.match(line)
                if (isrc is not None):
                    #add ISRC to track
                    track_ISRC = isrc.group(1)

    except StopIteration:
        if (track_number is not None):
            cuesheet_tracks.append(
                SheetTrack(track_number,
                           list(make_indexes(index_start,
                                             index_offsets)),
                           track_audio,
                           track_ISRC))

        return Sheet(cuesheet_tracks, cuesheet_catalog_number)


# class TOCFile:
#     """an object representing a TOC file"""

#     def __init__(self):
#         self.lines = []
#         self.tracks = {}

#     def __repr__(self):
#         return "TOCFile(lines=%s,tracks=%s)" % (repr(self.lines),
#                                                 repr(self.tracks))

#     def catalog(self):
#         """returns the cuesheet's CATALOG number as a plain string, or None

#         if present, this value is typically a CD's UPC code"""

#         import re

#         for line in self.lines:
#             if (line.startswith('CATALOG')):
#                 result = re.search(r'"(.+)"', line)
#                 if (result is not None):
#                     return result.group(1)
#                 else:
#                     continue
#         else:
#             return None

#     def indexes(self):
#         """yields a set of index lists, one for each track in the file"""

#         for track in sorted(self.tracks.values()):
#             if (track.start != 0):
#                 yield (track.indexes[0], track.indexes[0] + track.start)
#             else:
#                 yield (track.indexes[0],)

#     def pcm_lengths(self, total_length, sample_rate):
#         """yields a list of PCM lengths for all audio tracks within the file

#         total_length is the length of the entire file in PCM frames"""

#         previous = None

#         for current in self.indexes():
#             if (previous is None):
#                 previous = current
#             else:
#                 track_length = ((max(current) - max(previous)) *
#                                 sample_rate / 75)
#                 total_length -= track_length
#                 yield track_length
#                 previous = current

#         yield total_length

#     def ISRCs(self):
#         """returns a track_number->ISRC dict of all non-empty tracks"""

#         return dict([(track.number, track.ISRC()) for track in
#                      self.tracks.values() if track.ISRC() is not None])

#     @classmethod
#     def file(cls, sheet, filename):
#         """constructs a new TOC file string from a compatible object

#         sheet must have catalog(), indexes() and ISRCs() methods
#         filename is a string to the filename the TOC file is created for
#         although we don't care whether the filename points to a real file,
#         other tools sometimes do
#         """

#         import cStringIO
#         from . import build_timestamp

#         catalog = sheet.catalog()        # a catalog string, or None
#         indexes = list(sheet.indexes())  # a list of index tuples
#         ISRCs = sheet.ISRCs()            # a track_number->ISRC dict

#         data = cStringIO.StringIO()
#         data.write("CD_DA\n\n")

#         if ((catalog is not None) and (len(catalog) > 0)):
#             data.write("CATALOG \"%s\"\n\n" % (catalog))

#         for (i, (current, next)) in enumerate(zip(indexes,
#                                                   indexes[1:] + [None])):
#             tracknum = i + 1

#             data.write("TRACK AUDIO\n")

#             if (tracknum in ISRCs.keys()):
#                 data.write("ISRC \"%s\"\n" % (ISRCs[tracknum]))

#             if (next is not None):
#                 data.write("AUDIOFILE \"%s\" %s %s\n" %
#                            (filename,
#                             build_timestamp(current[0]),
#                             build_timestamp(next[0] - current[0])))
#             else:
#                 data.write("AUDIOFILE \"%s\" %s\n" %
#                            (filename,
#                             build_timestamp(current[0])))
#             if (len(current) > 1):
#                 data.write("START %s\n" %
#                            (build_timestamp(current[-1] - current[0])))

#             if (next is not None):
#                 data.write("\n")

#         return data.getvalue()


# class Track:
#     """a track inside a TOCFile object"""

#     def __init__(self, number):
#         self.number = number
#         self.lines = []
#         self.indexes = []
#         self.start = 0

#     def __cmp__(self, t):
#         return cmp(self.number, t.number)

#     def __repr__(self):
#         return "Track(%s,lines=%s,indexes=%s,start=%s)" % \
#             (repr(self.number), repr(self.lines),
#              repr(self.indexes), repr(self.start))

#     def ISRC(self):
#         """returns the track's ISRC value, or None"""

#         import re

#         for line in self.lines:
#             if (line.startswith('ISRC')):
#                 match = re.search(r'"(.+)"', line)
#                 if (match is not None):
#                     return match.group(1)
#         else:
#             return None


def read_tocfile(filename):
    """returns a TOCFile from a TOC filename on disk

    raises TOCException if some error occurs reading or parsing the file
    """

    try:
        f = open(filename, 'r')
    except IOError, msg:
        raise TOCException(str(msg))
    try:
        return parse(iter(f.readlines()))
    finally:
        f.close()
