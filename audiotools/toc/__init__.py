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

"""the TOC file module"""

from audiotools import Sheet,SheetTrack,SheetIndex,SheetException


class TOCFile(Sheet):
    def __init__(self, type, tracks, catalog=None, cd_text=None):
        self.__type__ = type
        for (i,t) in enumerate(tracks, 1):
            t.__number__ = i
        self.__tracks__ = tracks
        self.__catalog__ = catalog
        self.__cd_text__ = cd_text

    def __repr__(self):
        return "TOCFile(%s)" % \
            ", ".join(["%s=%s" % (attr, repr(getattr(self, "__" + attr + "__")))
                       for attr in ["type",
                                    "tracks",
                                    "catalog",
                                    "cd_text"]])

    @classmethod
    def converted(cls, sheet, filename="CDImage.wav"):
        """given a Sheet object, returns a TOCFile object"""

        tracks = sheet.tracks()

        return cls(type="CD_DA",
                   tracks=[TOCTrack.converted(sheettrack=track,
                                              next_sheettrack=next_track,
                                              filename=filename)
                           for (track, next_track) in
                           zip(tracks, tracks[1:] + [None])],
                   catalog=sheet.catalog())

    def build(self):
        """returns the TOCFile as a string"""

        output = [self.__type__, ""]
        if (self.__catalog__ is not None):
            output.extend(["CATALOG %s" % (format_string(self.__catalog__)),
                           ""])
        if (self.__cd_text__ is not None):
            output.append(self.__cd_text__.build())
        output.extend([track.build() for track in self.__tracks__])

        return "\n".join(output) + "\n"

    def track(self, track_number):
        """given a track number (typically starting from 1)
        returns a SheetTrack object or raises KeyError if not found"""

        if (track_number < 1):
            raise KeyError(track_number)
        else:
            try:
                return self.__tracks__[track_number - 1]
            except IndexError:
                raise KeyError(track_number)

    def tracks(self):
        """returns a list of all SheetTrack objects in the tocfile"""

        return list(self.__tracks__)

    def catalog(self):
        """returns sheet's catalog number as a plain string, or None"""

        return self.__catalog__

    def image_formatted(self):
        """returns True if the tocfile is formatted for a CD image
        instead of for multiple individual tracks"""

        raise NotImplementedError()


class TOCTrack(SheetTrack):
    def __init__(self, mode, flags, sub_channel_mode=None):
        self.__number__ = None  # to be filled-in later
        self.__mode__ = mode
        self.__sub_channel_mode__ = sub_channel_mode
        self.__flags__ = flags

    def __repr__(self):
        return "TOCTrack(%s)" % \
            ", ".join(["%s=%s" % (attr, repr(getattr(self, "__" + attr + "__")))
                       for attr in ["number",
                                    "mode",
                                    "sub_channel_mode",
                                    "flags"]])

    def build(self):
        """returns the TOCTrack as a string"""

        output = [("TRACK %s" % (self.__mode__) if
                   (self.__sub_channel_mode__ is None) else
                   "TRACK %s %s" % (self.__mode__,
                                    self.__sub_channel_mode__))]
        output.extend([flag.build() for flag in self.__flags__])
        output.append("")
        return "\n".join(output)

    @classmethod
    def converted(cls, sheettrack, next_sheettrack, filename):
        """given a SheetTrack object, returns a TOCTrack object"""

        flags = []
        if (sheettrack.ISRC() is not None):
            flags.append(TOCFlag_ISRC(isrc=sheettrack.ISRC()))

        indexes = sheettrack.indexes()
        if (len(indexes) > 0):
            flags.append(
                TOCFlag_FILE(type="AUDIOFILE",
                             filename=filename,
                             start=indexes[0].offset(),
                             length=((next_sheettrack.index(1).offset() -
                                      sheettrack.index(1).offset())
                                     if (next_sheettrack is not None) else
                                     None)))
            if (indexes[0].number() == 0):
                #track contains pre-gap
                flags.append(TOCFlag_START(indexes[1].offset() -
                                           indexes[0].offset()))
                for index in indexes[2:]:
                    flags.append(TOCFlag_INDEX(index.offset()))
            else:
                #track contains no pre-gap
                for index in indexes[1:]:
                    flags.append(TOCFlag_INDEX(index.offset()))

        return cls(mode=("AUDIO" if sheettrack.audio() else "MODE1"),
                   flags=flags)


    def indexes(self):
        """returns a list of SheetIndex objects"""

        from audiotools import SheetIndex

        indexes = []
        pre_gap = None
        file_start = None
        file_length = None

        for flag in self.__flags__:
            if (isinstance(flag, TOCFlag_FILE)):
                file_start = flag.start()
                file_length = flag.length()
            elif (isinstance(flag, TOCFlag_START)):
                if (flag.start() is not None):
                    pre_gap = flag.start()
                else:
                    pre_gap = file_length
            elif (isinstance(flag, TOCFlag_INDEX)):
                indexes.append(flag.index())

        #FIXME - sanity-check contents of indexes, pre_gap and file_start

        if (pre_gap is None):
            #first index point is 1
            return ([SheetIndex(number=1, offset=file_start)] +
                    [SheetIndex(number=i, offset=index)
                     for (i,index) in enumerate(indexes, 2)])
        else:
            #first index point is 0
            return ([SheetIndex(number=0, offset=file_start),
                     SheetIndex(number=1, offset=file_start + pre_gap)] +
                    [SheetIndex(number=i, offset=index)
                     for (i,index) in enumerate(indexes, 2)])

    def number(self):
        """returns track's number as an integer"""

        return self.__number__

    def ISRC(self):
        """returns track's ISRC value as a plain string, or None"""

        for flag in self.__flags__:
            if (isinstance(flag, TOCFlag_ISRC)):
                return flag.__isrc__
        else:
            return None

    def audio(self):
        """returns True if track contains audio data"""

        return self.__mode__ == "AUDIO"


class TOCFlag:
    def __init__(self, attrs):
        self.__attrs__ = attrs

    def __repr__(self):
        return "%s(%s)" % \
            (self.__class__.__name__,
             ", ".join(["%s=%s" % (attr,
                                   repr(getattr(self, "__" + attr + "__")))
                        for attr in self.__attrs__]))

    def build(self):
        """returns the TOCTracFlag as a string"""

        #implement this in TOCFlag subclasses
        raise NotImplementedError()


class TOCFlag_COPY(TOCFlag):
    def __init__(self, copy):
        TOCFlag.__init__(self, ["copy"])
        self.__copy__ = copy

    def build(self):
        return "COPY" if self.__copy__ else "NO COPY"

class TOCFlag_PRE_EMPHASIS(TOCFlag):
    def __init__(self, pre_emphasis):
        TOCFlag.__init__(self, ["pre_emphasis"])
        self.__pre_emphasis__ = pre_emphasis

    def build(self):
        return "PRE_EMPHASIS" if self.__pre_emphasis__ else "NO PRE_EMPHASIS"

class TOCFlag_CHANNELS(TOCFlag):
    def __init__(self, channels):
        TOCFlag.__init__(self, ["channels"])
        self.__channels__ = channels

    def build(self):
        return ("TWO_CHANNEL_AUDIO" if
                (self.__channels__ == 2) else
                "FOUR_CHANNEL_AUDIO")

class TOCFlag_ISRC(TOCFlag):
    def __init__(self, isrc):
        TOCFlag.__init__(self, ["isrc"])
        self.__isrc__ = isrc

    def build(self):
        return "ISRC %s" % (format_string(self.__isrc__))

class TOCFlag_FILE(TOCFlag):
    def __init__(self, type, filename, start, length=None):
        TOCFlag.__init__(self, ["type", "filename", "start", "length"])
        self.__type__ = type
        self.__filename__ = filename
        self.__start__ = start
        self.__length__ = length

    def start(self):
        return self.__start__

    def length(self):
        return self.__length__

    def build(self):
        if (self.__length__ is None):
            return "%s %s %s" % (self.__type__,
                                 format_string(self.__filename__),
                                 format_timestamp(self.__start__))
        else:
            return "%s %s %s %s" % (self.__type__,
                                    format_string(self.__filename__),
                                    format_timestamp(self.__start__),
                                    format_timestamp(self.__length__))

class TOCFlag_START(TOCFlag):
    def __init__(self, start=None):
        TOCFlag.__init__(self, ["start"])
        self.__start__ = start

    def start(self):
        return self.__start__

    def build(self):
        if (self.__start__ is None):
            return "START"
        else:
            return "START %s" % (format_timestamp(self.__start__))

class TOCFlag_INDEX(TOCFlag):
    def __init__(self, index):
        TOCFlag.__init__(self, ["index"])
        self.__index__ = index

    def index(self):
        return self.__index__

    def build(self):
        return "INDEX %s" % (format_timestamp(self.__index__))

class CDText:
    def __init__(self, languages, language_map=None):
        self.__languages__ = languages
        self.__language_map__ = language_map

    def __repr__(self):
        return "CDText(languages=%s, language_map=%s)" % \
            (repr(self.__languages__),
             repr(self.__language_map__))

    def build(self):
        output = ["CD_TEXT {"]
        if (self.__language_map__ is not None):
            output.append(self.__language_map__.build())
            output.append("")
        output.extend([language.build() for language in self.__languages__])
        output.append("}")
        return "\n".join(output)

class CDTextLanguage:
    def __init__(self, language_id, text_pairs):
        self.__id__ = language_id
        self.__text_pairs__ = text_pairs

    def __repr__(self):
        return "CDTextLanguage(language_id=%s, text_pairs=%s)" % \
            (repr(self.__id__),
             repr(self.__text_pairs__))

    def build(self):
        output = ["LANGUAGE %d {" % (self.__id__)]
        for (key, value) in self.__text_pairs__:
            if (key in ["TOC_INFO1",
                        "TOC_INFO2",
                        "SIZE_INFO"]):
                output.append("  %s %s" % (key, format_binary(value)))
            else:
                output.append("  %s %s" % (key, format_string(value)))
        output.append("}")
        return "\n".join(["  " + l for l in output])

class CDTextLanguageMap:
    def __init__(self, mapping):
        self.__mapping__ = mapping

    def __repr__(self):
        return "CDTextLanguageMap(mapping=%s)" % (repr(self.__mapping__))

    def build(self):
        output = ["LANGUAGE_MAP {"]
        output.extend(["  %d : %s" % (i,l) for (i,l) in self.__mapping__])
        output.append("}")
        return "\n".join(["  " + l for l in output])

def format_string(s):
    return "\"%s\"" % (s)

def format_timestamp(t):
    sectors = int(t * 75)
    return "%2.2d:%2.2d:%2.2d" % (sectors / 75 / 60,
                                  sectors / 75 % 60,
                                  sectors % 75)
def format_binary(s):
    return "{%s}" % (",".join([str(int(c)) for c in s]))

def read_tocfile(filename):
    """returns a Sheet from a TOC filename on disk

    raises TOCException if some error occurs reading or parsing the file
    """

    import ply.lex as lex
    import ply.yacc as yacc
    from ply.yacc import NullLogger
    import audiotools.toc.tokrules
    import audiotools.toc.yaccrules

    lexer = lex.lex(module=audiotools.toc.tokrules)
    try:
        lexer.input(open(filename, "rb").read())
    except IOError:
        raise TOCException("unable to open file")
    parser = yacc.yacc(module=audiotools.toc.yaccrules,
                       debug=0,
                       errorlog=NullLogger(),
                       write_tables=0)
    try:
        return parser.parse(lexer=lexer)
    except ValueError:
        raise SheetException(str(err))


def write_tocfile(sheet, filename, file):
    """given a Sheet object and filename string,
    writes a .toc file to the given file object"""

    file.write(TOCFile.converted(sheet, filename=filename).build())
