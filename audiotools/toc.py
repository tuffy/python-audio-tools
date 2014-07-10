#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2008-2014  Brian Langenberger

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


def __parse__(lines):
    """returns a Sheet object from an iterator of lines

    raises TOCException if some problem occurs parsing the file"""

    import re
    from fractions import Fraction
    from audiotools import parse_timestamp, Sheet, SheetTrack, SheetIndex

    CATALOG = re.compile(r'CATALOG\s*"(.*?)"')
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
            else:
                catalog = CATALOG.match(line)
                if (catalog is not None):
                    cuesheet_catalog_number = catalog.group(1)
                    continue

    except StopIteration:
        if (track_number is not None):
            cuesheet_tracks.append(
                SheetTrack(track_number,
                           list(make_indexes(index_start,
                                             index_offsets)),
                           track_audio,
                           track_ISRC))

        return Sheet(cuesheet_tracks, cuesheet_catalog_number)


def read_tocfile(filename):
    """returns a Sheet from a TOC filename on disk

    raises TOCException if some error occurs reading or parsing the file
    """

    try:
        f = open(filename, 'r')
    except IOError, msg:
        raise TOCException(str(msg))
    try:
        return __parse__(iter(f.readlines()))
    finally:
        f.close()


def write_tocfile(sheet, filename, file):
    """given a Sheet object and filename string,
    writes a .toc file to the given file object"""

    from . import build_timestamp

    file.write("CD_DA\n\n")

    if ((sheet.catalog() is not None) and (len(sheet.catalog()) > 0)):
        file.write("CATALOG \"%s\"\n\n" % (sheet.catalog()))

    tracks = list(sheet.tracks())

    for (track, next_track) in zip(tracks, tracks[1:] + [None]):
        file.write("TRACK AUDIO\n")

        if (track.ISRC() is not None):
            file.write("  ISRC \"%s\"\n" % (track.ISRC()))

        track_indexes = list(track.indexes())
        if (next_track is not None):
            #total track length in fractions of seconds
            track_length = (min([i.offset() for i in next_track.indexes()]) -
                            min([i.offset() for i in track.indexes()]))

            file.write("  AUDIOFILE \"%s\" %s %s\n" %
                       (filename,
                        build_timestamp(int(track_indexes[0].offset() * 75)),
                        build_timestamp(int(track_length * 75))))
        else:
            file.write("  AUDIOFILE \"%s\" %s\n" %
                       (filename,
                        build_timestamp(int(track_indexes[0].offset() * 75))))

        if (track_indexes[0].number() == 0):
            #handle pre-gap track
            #before any additional indexes
            file.write("  START %s\n" %
                       (build_timestamp(
                        int((track_indexes[1].offset() -
                             track_indexes[0].offset()) * 75))))
            for index in track_indexes[2:]:
                file.write("  INDEX %s\n" %
                           (build_timestamp(int(index.offset() * 75))))
        else:
            #handle any additional indexes
            for index in track_indexes[1:]:
                file.write("  INDEX %s\n" %
                           (build_timestamp(int(index.offset() * 75))))

        if (next_track is not None):
            file.write("\n")
