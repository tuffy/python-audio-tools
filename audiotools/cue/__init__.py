#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2014  Brian Langenberger

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

"""the cuesheet module"""

from audiotools import Sheet,SheetTrack,SheetIndex,SheetException


class Cuesheet(Sheet):
    def __init__(self, files,
                 catalog=None,
                 title=None,
                 performer=None,
                 songwriter=None,
                 cdtextfile=None):
        #FIXME - sanity check files
        self.__files__ = files
        self.__catalog__ = catalog
        self.__title__ = title
        self.__performer__ = performer
        self.__songwriter__ = songwriter
        self.__cdtextfile__ = cdtextfile

    def __repr__(self):
        return "Cuesheet(%s)" % \
            ", ".join(["%s=%s" % (attr, repr(getattr(self, "__" + attr + "__")))
                       for attr in ["files",
                                    "catalog",
                                    "title",
                                    "performer",
                                    "songwriter",
                                    "cdtextfile"]])

    @classmethod
    def converted(cls, sheet, filename="CDImage.wav"):
        """given a Sheet object, returns a Cuesheet object"""

        return cls(files=[File.converted(sheet, filename)],
                   catalog=sheet.catalog())

    def build(self):
        """returns the Cuesheet as a string"""

        items = []
        if (self.__catalog__ is not None):
            items.append("CATALOG %s" % (format_string(self.__catalog__)))
        if (self.__title__ is not None):
            items.append("TITLE %s" % (format_string(self.__title__)))
        if (self.__performer__ is not None):
            items.append("PERFORMER %s" % (format_string(self.__performer__)))
        if (self.__songwriter__ is not None):
            items.append("SONGWRITER %s" % (format_string(self.__songwriter__)))
        if (self.__cdtextfile__ is not None):
            items.append("CDTEXTFILE %s" % (format_string(self.__cdtextfile__)))

        if (len(items) > 0):
            return ("\r\n".join(items) +
                    "\r\n" +
                    "\r\n".join([f.build() for f in self.__files__]) +
                    "\r\n")
        else:
            return "\r\n".join([f.build() for f in self.__files__]) + "\r\n"

    def track(self, track_number, file=0):
        """given a track_number (typically starting from 1),
        returns a SheetTrack object or raises KeyError if not found"""

        return self.__files__[file].track(track_number)

    def tracks(self, file=0):
        """returns a list of all SheetTrack objects in the cuesheet"""

        return self.__files__[file].tracks()

    def catalog(self):
        """returns sheet's catalog number as a plain string, or None"""

        if (self.__catalog__ is not None):
            return self.__catalog__
        else:
            return None

    def image_formatted(self):
        """returns True if the cuesheet is formatted for a CD image
        instead of for multiple individual tracks"""

        return len(self.__files__) == 1


class File:
    def __init__(self, filename, file_type, tracks):
        self.__filename__ = filename
        self.__file_type__ = file_type
        self.__tracks__ = tracks

    def __repr__(self):
        return "File(%s)" % \
            ", ".join(["%s=%s" % (attr, repr(getattr(self, "__" + attr + "__")))
                       for attr in ["filename", "file_type", "tracks"]])

    @classmethod
    def converted(cls, sheet, filename):
        """given a Cuesheet object, returns a File object"""

        return cls(filename=filename,
                   file_type="WAVE",
                   tracks=[Track.converted(t) for t in sheet.tracks()])

    def build(self):
        """returns the File as a string"""

        return "FILE %s %s\r\n%s" % \
            (format_string(self.__filename__),
             self.__file_type__,
             "\r\n".join([t.build() for t in self.__tracks__]))

    def track(self, track_number):
        """given a track_number (typically starting from 1),
        returns a SheetTrack object or raises KeyError if not found"""

        for track in self.tracks():
            if (track_number == track.number()):
                return track
        else:
            raise KeyError(track_number)

    def tracks(self):
        """returns a list of all SheetTrack objects in the cuesheet"""

        return list(self.__tracks__)


class Track(SheetTrack):
    def __init__(self, number,
                 track_type,
                 indexes,
                 isrc=None,
                 pregap=None,
                 postgap=None,
                 flags=None,
                 title=None,
                 performer=None,
                 songwriter=None):
        self.__number__ = number
        self.__track_type__ = track_type
        self.__indexes__ = indexes
        self.__isrc__ = isrc
        self.__pregap__ = pregap
        self.__postgap__ = postgap
        self.__flags__ = flags
        self.__title__ = title
        self.__performer__ = performer
        self.__songwriter__ = songwriter

    def __repr__(self):
        return "Track(%s)" % \
            ", ".join(["%s=%s" % (attr, repr(getattr(self, "__" + attr + "__")))
                       for attr in ["number",
                                    "track_type",
                                    "indexes",
                                    "isrc",
                                    "pregap",
                                    "postgap",
                                    "flags",
                                    "title",
                                    "performer",
                                    "songwriter"]])

    @classmethod
    def converted(cls, sheettrack):
        """given a SheetTrack object, returns a Track object"""

        return cls(number=sheettrack.number(),
                   track_type="AUDIO" if sheettrack.audio() else "MODE1/2352",
                   indexes=[Index.converted(i) for i in
                            sheettrack.indexes()],
                   isrc=sheettrack.ISRC())

    def build(self):
        """returns the Track as a string"""

        items = []

        if (self.__title__ is not None):
            items.append("    TITLE %s" %
                         (format_string(self.__title__)))

        if (self.__performer__ is not None):
            items.append("    PERFORMER %s" %
                         (format_string(self.__performer__)))

        if (self.__songwriter__ is not None):
            items.append("    SONGWRITER %s" %
                         (format_string(self.__songwriter__)))

        if (self.__flags__ is not None):
            items.append("    FLAGS %s" % (" ".join(self.__flags__)))

        if (self.__isrc__ is not None):
            items.append("    ISRC %s" % (self.__isrc__))

        if (self.__pregap__ is not None):
            items.append("    PREGAP %s" %
                         (format_timestamp(self.__pregap__)))

        for index in self.__indexes__:
            items.append(index.build())

        if (self.__postgap__ is not None):
            items.append("    POSTGAP %s" %
                         (format_timestamp(self.__postgap__)))

        return "  TRACK %2.2d %s\r\n%s" % (self.__number__,
                                           self.__track_type__,
                                           "\r\n".join(items))

    def index(self, index_number):
        """given index number (often starting from 1)
        returns SheetIndex object or raises KeyError if not found"""

        for index in self.__indexes__:
            if (index_number == index.number()):
                return index
        else:
            raise KeyError(index_number)

    def indexes(self):
        """returns a list of SheetIndex objects"""

        return list(self.__indexes__)

    def number(self):
        """returns track's number as an integer"""

        return self.__number__

    def ISRC(self):
        """returns track's ISRC value as plain string, or None"""

        return self.__isrc__

    def audio(self):
        """returns True if track contains audio data"""

        return self.__track_type__ == "AUDIO"


class Index(SheetIndex):
    def __init__(self, number, timestamp):
        self.__number__ = number
        self.__timestamp__ = timestamp

    def __repr__(self):
        return "Index(number=%s, timestamp=%s)" % \
            (repr(self.__number__),
             repr(self.__timestamp__))

    @classmethod
    def converted(cls, index):
        """given a SheetIndex object, returns an Index object"""

        return cls(number=index.number(),
                   timestamp=int(index.offset() * 75))

    def build(self):
        """returns the Index as a string"""

        return "    INDEX %2.2d %s" % (self.__number__,
                                       format_timestamp(self.__timestamp__))

    def number(self):
        """returns the index's number (typically starting from 1)"""

        return self.__number__

    def offset(self):
        """returns the index's offset from the start of the stream
        in seconds as a Fraction object"""

        from fractions import Fraction

        return Fraction(self.__timestamp__, 75)


def format_string(s):
    return "\"%s\"" % (s)


def format_timestamp(t):
    return "%2.2d:%2.2d:%2.2d" % (t / 75 / 60,
                                  t / 75 % 60,
                                  t % 75)


def read_cuesheet(filename):
    """returns a Cuesheet from a cuesheet filename on disk

    raises CueException if some error occurs reading or parsing the file
    """

    try:
        return read_cuesheet_string(open(filename, "rb").read())
    except IOError:
        raise CueException("unable to open file")


def read_cuesheet_string(cuesheet):
    """given a plain string of cuesheet data returns a Cuesheet object

    raises CueException if some error occurs parsing the file"""

    import ply.lex as lex
    import ply.yacc as yacc
    from ply.yacc import NullLogger
    import audiotools.cue.tokrules
    import audiotools.cue.yaccrules

    lexer = lex.lex(module=audiotools.cue.tokrules)
    lexer.input(cuesheet)
    parser = yacc.yacc(module=audiotools.cue.yaccrules,
                       debug=0,
                       errorlog=NullLogger(),
                       write_tables=0)
    return parser.parse(lexer=lexer)


def write_cuesheet(sheet, filename, file):
    """given a Sheet object and filename string,
    writes a .cue file to the given file object"""

    file.write(Cuesheet.converted(sheet, filename=filename).build())
