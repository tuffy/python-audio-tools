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
    def converted(cls, sheet):
        """given a Sheet object, returns a Cuesheet object"""

        def group_tracks(tracks):
            current_file = None
            current_tracks = []
            for track in tracks:
                if (current_file is None):
                    current_file = track.filename()
                    current_tracks = [track]
                elif (current_file != track.filename()):
                    yield (current_file, current_tracks)
                    current_file = track.filename()
                    current_tracks = [track]
                else:
                    current_tracks.append(track)
            else:
                if (current_file is not None):
                    yield (current_file, current_tracks)

        metadata = sheet.get_metadata()

        args = {"files":[File(filename=filename,
                               file_type="WAVE",
                               tracks=map(Track.converted, tracks))
                          for (filename, tracks) in group_tracks(sheet)]}

        if (metadata is not None):
           args["catalog"] = encode_string(metadata.catalog)
           args["title"] = encode_string(metadata.album_name)
           args["performer"] = encode_string(metadata.performer_name)
           args["songwriter"] = encode_string(metadata.artist_name)

        return cls(**args)

    def __len__(self):
        return sum(map(len, self.__files__))

    def __getitem__(self, index):
        not_found = IndexError(index)
        for file in self.__files__:
            if (index < len(file)):
                return file[index]
            else:
                index -= len(file)
        else:
            raise not_found

    def get_metadata(self):
        """returns MetaData of Sheet, or None
        this metadata often contains information such as catalog number
        or CD-TEXT values"""

        from operator import or_

        if (reduce(or_, [(attr is not None) for attr in
                         [self.__catalog__,
                          self.__title__,
                          self.__performer__,
                          self.__songwriter__]], False)):
            from audiotools import MetaData

            return MetaData(catalog=decode_string(self.__catalog__),
                            album_name=decode_string(self.__title__),
                            performer_name=decode_string(self.__performer__),
                            artist_name=decode_string(self.__songwriter__))
        else:
            return None

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


class File:
    def __init__(self, filename, file_type, tracks):
        self.__filename__ = filename
        self.__file_type__ = file_type
        for t in tracks:
            t.__parent_file__ = self
        self.__tracks__ = tracks

    def __len__(self):
        return len(self.__tracks__)

    def __getitem__(self, index):
        return self.__tracks__[index]

    def __repr__(self):
        return "File(%s)" % \
            ", ".join(["%s=%s" % (attr, repr(getattr(self, "__" + attr + "__")))
                       for attr in ["filename", "file_type", "tracks"]])

    def filename(self):
        return self.__filename__

    def build(self):
        """returns the File as a string"""

        return "FILE %s %s\r\n%s" % \
            (format_string(self.__filename__),
             self.__file_type__,
             "\r\n".join([t.build() for t in self.__tracks__]))


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
        self.__parent_file__ = None  # to be assigned by File
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

        metadata = sheettrack.get_metadata()

        args = {"number":sheettrack.number(),
                "track_type":("AUDIO" if sheettrack.is_audio() else
                              "MODE1/2352"),
                "indexes":[Index.converted(i) for i in sheettrack]}

        if (metadata is not None):
            args["isrc"] = encode_string(metadata.ISRC)
            args["title"] = encode_string(metadata.track_name)
            args["performer"] = encode_string(metadata.performer_name)
            args["songwriter"] = encode_string(metadata.artist_name)

        return cls(**args)

    def __len__(self):
        return len(self.__indexes__)

    def __getitem__(self, index):
        return self.__indexes__[index]

    def number(self):
        """return SheetTrack's number, starting from 1"""

        return self.__number__

    def get_metadata(self):
        """returns SheetTrack's MetaData, or None"""

        from operator import or_

        if (reduce(or_, [(attr is not None) for attr in
                         [self.__isrc__,
                          self.__title__,
                          self.__performer__,
                          self.__songwriter__]], False)):
            from audiotools import MetaData

            return MetaData(ISRC=decode_string(self.__isrc__),
                            track_name=decode_string(self.__title__),
                            performer_name=decode_string(self.__performer__),
                            artist_name=decode_string(self.__songwriter__))
        else:
            return None

    def filename(self):
        """returns SheetTrack's filename as a string"""

        if (self.__parent_file__ is not None):
            return self.__parent_file__.filename()
        else:
            return ""

    def is_audio(self):
        """returns whether SheetTrack contains audio data"""

        return self.__track_type__ == "AUDIO"

    def pre_emphasis(self):
        """returns whether SheetTrack has pre-emphasis"""

        if (self.__flags__ is not None):
            return "PRE" in self.__flags__
        else:
            return False

    def copy_permitted(self):
        """returns whether copying is permitted"""

        if (self.__flags__ is not None):
            return "DCP" in self.__flags__
        else:
            return False

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

def decode_string(s):
    if (s is not None):
        #FIXME - make a best guess at text encoding?
        return s.decode("ascii", "replace")
    else:
        return None


def encode_string(u):
    if (u is not None):
        #FIXME - make a best guess at text encoding?
        return u.encode("ascii", "replace")
    else:
        return None


def read_cuesheet(filename):
    """returns a Cuesheet from a cuesheet filename on disk

    raises SheetException if some error occurs reading or parsing the file
    """

    try:
        return read_cuesheet_string(open(filename, "rb").read())
    except IOError:
        raise SheetException("unable to open file")


def read_cuesheet_string(cuesheet):
    """given a plain string of cuesheet data returns a Cuesheet object

    raises SheetException if some error occurs parsing the file"""

    import audiotools.ply.lex as lex
    import audiotools.ply.yacc as yacc
    from audiotools.ply.yacc import NullLogger
    import audiotools.cue.tokrules
    import audiotools.cue.yaccrules

    lexer = lex.lex(module=audiotools.cue.tokrules)
    lexer.input(cuesheet)
    parser = yacc.yacc(module=audiotools.cue.yaccrules,
                       debug=0,
                       errorlog=NullLogger(),
                       write_tables=0)
    try:
        return parser.parse(lexer=lexer)
    except ValueError, err:
        raise SheetException(str(err))


def write_cuesheet(sheet, filename, file):
    """given a Sheet object and filename string,
    writes a .cue file to the given file object"""

    file.write(Cuesheet.converted(sheet, filename=filename).build())
