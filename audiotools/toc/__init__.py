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

"""the TOC file module"""

from audiotools import Sheet, SheetTrack, SheetIndex, SheetException


class TOCFile(Sheet):
    def __init__(self, type, tracks, catalog=None, cd_text=None):
        from sys import version_info
        str_type = str if (version_info[0] >= 3) else unicode

        assert(isinstance(type, str_type))
        assert((catalog is None) or isinstance(catalog, str_type))
        assert((cd_text is None) or isinstance(cd_text, CDText))

        self.__type__ = type
        for (i, t) in enumerate(tracks, 1):
            t.__number__ = i
        self.__tracks__ = tracks
        self.__catalog__ = catalog
        self.__cd_text__ = cd_text

    def __repr__(self):
        return "TOCFile({})".format(
            ", ".join(["{}={!r}".format(attr,
                                        getattr(self, "__" + attr + "__"))
                       for attr in ["type",
                                    "tracks",
                                    "catalog",
                                    "cd_text"]]))

    @classmethod
    def converted(cls, sheet, filename=None):
        """given a Sheet object, returns a TOCFile object"""

        tracks = list(sheet)
        metadata = sheet.get_metadata()

        if metadata is not None:
            if metadata.catalog is not None:
                catalog = metadata.catalog
            else:
                catalog = None

            cd_text = CDText.from_disc_metadata(metadata)
        else:
            catalog = None
            cd_text = None

        return cls(type=u"CD_DA",
                   tracks=[TOCTrack.converted(sheettrack=track,
                                              next_sheettrack=next_track,
                                              filename=filename)
                           for (track, next_track) in
                           zip(tracks, tracks[1:] + [None])],
                   catalog=catalog,
                   cd_text=cd_text)

    def __len__(self):
        return len(self.__tracks__)

    def __getitem__(self, index):
        return self.__tracks__[index]

    def build(self):
        """returns the TOCFile as a string"""

        output = [self.__type__, u""]
        if self.__catalog__ is not None:
            output.extend([
                u"CATALOG {}".format(format_string(self.__catalog__)), u""])
        if self.__cd_text__ is not None:
            output.append(self.__cd_text__.build())
        output.extend([track.build() for track in self.__tracks__])

        return u"\n".join(output) + u"\n"

    def get_metadata(self):
        """returns MetaData of Sheet, or None
        this metadata often contains information such as catalog number
        or CD-TEXT values"""

        from audiotools import MetaData

        if (self.__catalog__ is not None) and (self.__cd_text__ is not None):
            metadata = self.__cd_text__.to_disc_metadata()
            metadata.catalog = self.__catalog__
            return metadata
        elif self.__catalog__ is not None:
            return MetaData(catalog=self.__catalog__)
        elif self.__cd_text__ is not None:
            return self.__cd_text__.to_disc_metadata()
        else:
            return None


class TOCTrack(SheetTrack):
    def __init__(self, mode, flags, sub_channel_mode=None):
        from audiotools import SheetIndex
        from sys import version_info
        str_type = str if (version_info[0] >= 3) else unicode

        assert(isinstance(mode, str_type))
        assert((sub_channel_mode is None) or
               isinstance(sub_channel_mode, str_type))

        self.__number__ = None  # to be filled-in later
        self.__mode__ = mode
        self.__sub_channel_mode__ = sub_channel_mode
        self.__flags__ = flags

        indexes = []
        pre_gap = None
        file_start = None
        file_length = None
        for flag in flags:
            if isinstance(flag, TOCFlag_FILE):
                file_start = flag.start()
                file_length = flag.length()
            elif isinstance(flag, TOCFlag_START):
                if flag.start() is not None:
                    pre_gap = flag.start()
                else:
                    pre_gap = file_length
            elif isinstance(flag, TOCFlag_INDEX):
                indexes.append(flag.index())

        if pre_gap is None:
            # first index point is 1
            self.__indexes__ = ([SheetIndex(number=1, offset=file_start)] +
                                [SheetIndex(number=i, offset=index)
                                 for (i, index) in enumerate(indexes, 2)])
        else:
            # first index point is 0
            self.__indexes__ = ([SheetIndex(number=0,
                                            offset=file_start),
                                 SheetIndex(number=1,
                                            offset=file_start + pre_gap)] +
                                [SheetIndex(number=i, offset=index)
                                 for (i, index) in enumerate(indexes, 2)])

    @classmethod
    def converted(cls, sheettrack, next_sheettrack, filename=None):
        """given a SheetTrack object, returns a TOCTrack object"""

        metadata = sheettrack.get_metadata()

        flags = []

        if metadata is not None:
            if metadata.ISRC is not None:
                flags.append(TOCFlag_ISRC(metadata.ISRC))
            cdtext = CDText.from_track_metadata(metadata)
            if cdtext is not None:
                flags.append(cdtext)

        if sheettrack.copy_permitted():
            flags.append(TOCFlag_COPY(True))

        if sheettrack.pre_emphasis():
            flags.append(TOCFlag_PRE_EMPHASIS(True))

        if len(sheettrack) > 0:
            if ((next_sheettrack is not None) and
                (sheettrack.filename() == next_sheettrack.filename())):
                length = (next_sheettrack[0].offset() -
                          sheettrack[0].offset())
            else:
                length = None

            flags.append(TOCFlag_FILE(
                type=u"AUDIOFILE",
                filename=(filename if
                          filename is not None else
                          sheettrack.filename()),
                start=sheettrack[0].offset(),
                length=length))
            if sheettrack[0].number() == 0:
                # first index point is 0 so track contains pre-gap
                flags.append(TOCFlag_START(sheettrack[1].offset() -
                                           sheettrack[0].offset()))
                for index in sheettrack[2:]:
                    flags.append(TOCFlag_INDEX(index.offset()))
            else:
                # track contains no pre-gap
                for index in sheettrack[1:]:
                    flags.append(TOCFlag_INDEX(index.offset()))

        return cls(mode=(u"AUDIO" if sheettrack.is_audio() else u"MODE1"),
                   flags=flags)

    def first_flag(self, flag_class):
        """returns the first flag in the list with the given class
        or None if not found"""

        for flag in self.__flags__:
            if isinstance(flag, flag_class):
                return flag
        else:
            return None

    def all_flags(self, flag_class):
        """returns a list of all flags in the list with the given class"""

        return [f for f in self.__flags__ if isinstance(f, flag_class)]

    def __repr__(self):
        return "TOCTrack({})".format(
            ", ".join(["{}={!r}".format(attr,
                                        getattr(self, "__" + attr + "__"))
                       for attr in ["number",
                                    "mode",
                                    "sub_channel_mode",
                                    "flags"]]))

    def __len__(self):
        return len(self.__indexes__)

    def __getitem__(self, index):
        return self.__indexes__[index]

    def number(self):
        """returns track's number as an integer"""

        return self.__number__

    def get_metadata(self):
        """returns SheetTrack's MetaData, or None"""

        from audiotools import MetaData

        isrc = self.first_flag(TOCFlag_ISRC)
        cd_text = self.first_flag(CDText)
        if (isrc is not None) and (cd_text is not None):
            metadata = cd_text.to_track_metadata()
            metadata.ISRC = isrc.isrc()
            return metadata
        elif cd_text is not None:
            return cd_text.to_track_metadata()
        elif isrc is not None:
            return MetaData(ISRC=isrc.isrc())
        else:
            return None

    def filename(self):
        """returns SheetTrack's filename as a string"""

        filename = self.first_flag(TOCFlag_FILE)
        if filename is not None:
            return filename.filename()
        else:
            return u""

    def is_audio(self):
        """returns True if track contains audio data"""

        return self.__mode__ == u"AUDIO"

    def pre_emphasis(self):
        """returns whether SheetTrack has pre-emphasis"""

        pre_emphasis = self.first_flag(TOCFlag_PRE_EMPHASIS)
        if pre_emphasis is not None:
            return pre_emphasis.pre_emphasis()
        else:
            return False

    def copy_permitted(self):
        """returns whether copying is permitted"""

        copy = self.first_flag(TOCFlag_COPY)
        if copy is not None:
            return copy.copy()
        else:
            return False

    def build(self):
        """returns the TOCTrack as a string"""

        output = [(u"TRACK {}".format(self.__mode__) if
                   (self.__sub_channel_mode__ is None) else
                   u"TRACK {} {}".format(self.__mode__,
                                         self.__sub_channel_mode__))]
        output.extend([flag.build() for flag in self.__flags__])
        output.append(u"")
        return u"\n".join(output)


class TOCFlag(object):
    def __init__(self, attrs):
        self.__attrs__ = attrs

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(["{}={!r}".format(attr,
                                        getattr(self, "__" + attr + "__"))
                       for attr in self.__attrs__]))

    def build(self):
        """returns the TOCTracFlag as a string"""

        # implement this in TOCFlag subclasses
        raise NotImplementedError()


class TOCFlag_COPY(TOCFlag):
    def __init__(self, copy):
        TOCFlag.__init__(self, ["copy"])
        assert(isinstance(copy, bool))
        self.__copy__ = copy

    def copy(self):
        return self.__copy__

    def build(self):
        return u"COPY" if self.__copy__ else u"NO COPY"


class TOCFlag_PRE_EMPHASIS(TOCFlag):
    def __init__(self, pre_emphasis):
        TOCFlag.__init__(self, ["pre_emphasis"])
        assert(isinstance(pre_emphasis, bool))
        self.__pre_emphasis__ = pre_emphasis

    def pre_emphasis(self):
        return self.__pre_emphasis__

    def build(self):
        return u"PRE_EMPHASIS" if self.__pre_emphasis__ else u"NO PRE_EMPHASIS"


class TOCFlag_CHANNELS(TOCFlag):
    def __init__(self, channels):
        TOCFlag.__init__(self, ["channels"])
        assert((channels == 2) or (channels == 4))
        self.__channels__ = channels

    def build(self):
        return (u"TWO_CHANNEL_AUDIO" if
                (self.__channels__ == 2) else
                u"FOUR_CHANNEL_AUDIO")


class TOCFlag_ISRC(TOCFlag):
    def __init__(self, isrc):
        TOCFlag.__init__(self, ["isrc"])
        from sys import version_info
        str_type = str if (version_info[0] >= 3) else unicode
        assert(isinstance(isrc, str_type))
        self.__isrc__ = isrc

    def isrc(self):
        return self.__isrc__

    def build(self):
        return u"ISRC {}".format(format_string(self.__isrc__))


class TOCFlag_FILE(TOCFlag):
    def __init__(self, type, filename, start, length=None):
        TOCFlag.__init__(self, ["type", "filename", "start", "length"])
        from sys import version_info
        from fractions import Fraction
        str_type = str if (version_info[0] >= 3) else unicode
        assert(isinstance(type, str_type))
        assert(isinstance(filename, str_type))
        assert(isinstance(start, Fraction))
        assert((length is None) or isinstance(length, Fraction))
        self.__type__ = type
        self.__filename__ = filename
        self.__start__ = start
        self.__length__ = length

    def filename(self):
        return self.__filename__

    def start(self):
        return self.__start__

    def length(self):
        return self.__length__

    def build(self):
        if self.__length__ is None:
            return u"{} {} {}".format(self.__type__,
                                      format_string(self.__filename__),
                                      format_timestamp(self.__start__))
        else:
            return u"{} {} {} {}".format(self.__type__,
                                         format_string(self.__filename__),
                                         format_timestamp(self.__start__),
                                         format_timestamp(self.__length__))


class TOCFlag_START(TOCFlag):
    def __init__(self, start=None):
        TOCFlag.__init__(self, ["start"])
        from fractions import Fraction
        assert((start is None) or isinstance(start, Fraction))
        self.__start__ = start

    def start(self):
        return self.__start__

    def build(self):
        if self.__start__ is None:
            return u"START"
        else:
            return u"START {}".format(format_timestamp(self.__start__))


class TOCFlag_INDEX(TOCFlag):
    def __init__(self, index):
        TOCFlag.__init__(self, ["index"])
        from fractions import Fraction
        assert(isinstance(index, Fraction))
        self.__index__ = index

    def index(self):
        return self.__index__

    def build(self):
        return u"INDEX {}".format(format_timestamp(self.__index__))


class CDText(object):
    def __init__(self, languages, language_map=None):
        self.__languages__ = languages
        self.__language_map__ = language_map

    def __repr__(self):
        return "CDText(languages={!r}, language_map={!r})".format(
            self.__languages__, self.__language_map__)

    def get(self, key, default):
        for language in self.__languages__:
            try:
                return language[key]
            except KeyError:
                pass
        else:
            return default

    def build(self):
        output = [u"CD_TEXT {"]
        if self.__language_map__ is not None:
            output.append(self.__language_map__.build())
            output.append(u"")
        output.extend([language.build() for language in self.__languages__])
        output.append(u"}")
        return u"\n".join(output)

    def to_disc_metadata(self):
        from audiotools import MetaData

        return MetaData(
            album_name=self.get(u"TITLE", None),
            performer_name=self.get(u"PERFORMER", None),
            artist_name=self.get(u"SONGWRITER", None),
            composer_name=self.get(u"COMPOSER", None),
            comment=self.get(u"MESSAGE", None))

    @classmethod
    def from_disc_metadata(cls, metadata):
        text_pairs = []
        if metadata is not None:
            if metadata.album_name is not None:
                text_pairs.append((u"TITLE", metadata.album_name))
            if metadata.performer_name is not None:
                text_pairs.append((u"PERFORMER", metadata.performer_name))
            if metadata.artist_name is not None:
                text_pairs.append((u"SONGWRITER", metadata.artist_name))
            if metadata.composer_name is not None:
                text_pairs.append((u"COMPOSER", metadata.composer_name))
            if metadata.comment is not None:
                text_pairs.append((u"MESSAGE", metadata.comment))

        if len(text_pairs) > 0:
            return cls(languages=[CDTextLanguage(language_id=0,
                                                 text_pairs=text_pairs)],
                       language_map=CDTextLanguageMap([(0, u"EN")]))
        else:
            return None

    def to_track_metadata(self):
        from audiotools import MetaData

        return MetaData(
            track_name=self.get(u"TITLE", None),
            performer_name=self.get(u"PERFORMER", None),
            artist_name=self.get(u"SONGWRITER", None),
            composer_name=self.get(u"COMPOSER", None),
            comment=self.get(u"MESSAGE", None),
            ISRC=self.get(u"ISRC", None))

    @classmethod
    def from_track_metadata(cls, metadata):
        text_pairs = []
        if metadata is not None:
            if metadata.track_name is not None:
                text_pairs.append((u"TITLE", metadata.track_name))
            if metadata.performer_name is not None:
                text_pairs.append((u"PERFORMER", metadata.performer_name))
            if metadata.artist_name is not None:
                text_pairs.append((u"SONGWRITER", metadata.artist_name))
            if metadata.composer_name is not None:
                text_pairs.append((u"COMPOSER", metadata.composer_name))
            if metadata.comment is not None:
                text_pairs.append((u"MESSAGE", metadata.comment))
            # ISRC is handled in its own flag

        if len(text_pairs) > 0:
            return cls(languages=[CDTextLanguage(language_id=0,
                                                 text_pairs=text_pairs)])
        else:
            return None


class CDTextLanguage(object):
    def __init__(self, language_id, text_pairs):
        self.__id__ = language_id
        self.__text_pairs__ = text_pairs

    def __repr__(self):
        return "CDTextLanguage(language_id={!r}, text_pairs={!r})".format(
            self.__id__, self.__text_pairs__)

    def __len__(self):
        return len(self.__text_pairs__)

    def __getitem__(self, key):
        for (k, v) in self.__text_pairs__:
            if k == key:
                return v
        else:
            raise KeyError(key)

    def build(self):
        output = [u"LANGUAGE {:d} {{".format(self.__id__)]
        for (key, value) in self.__text_pairs__:
            if key in {u"TOC_INFO1", u"TOC_INFO2", u"SIZE_INFO"}:
                output.append(u"  {} {}".format(key, format_binary(value)))
            else:
                output.append(u"  {} {}".format(key, format_string(value)))
        output.append(u"}")
        return u"\n".join([u"  " + l for l in output])


class CDTextLanguageMap(object):
    def __init__(self, mapping):
        self.__mapping__ = mapping

    def __repr__(self):
        return "CDTextLanguageMap(mapping={!r})".format(self.__mapping__)

    def build(self):
        output = [u"LANGUAGE_MAP {"]
        output.extend([u"  {:d} : {}".format(i, l)
                       for (i, l) in self.__mapping__])
        output.append(u"}")
        return u"\n".join([u"  " + l for l in output])


def format_string(s):
    return u"\"{}\"".format(s.replace(u'\\', u'\\\\').replace(u'"', u'\\"'))


def format_timestamp(t):
    sectors = int(t * 75)
    return u"{:02d}:{:02d}:{:02d}".format(sectors // 75 // 60,
                                          sectors // 75 % 60,
                                          sectors % 75)


def format_binary(s):
    return u"{{{}}}".format(",".join([u"{:d}".format(int(c)) for c in s]))


def read_tocfile(filename):
    """returns a Sheet from a TOC filename on disk

    raises TOCException if some error occurs reading or parsing the file
    """

    try:
        with open(filename, "rb") as f:
            return read_tocfile_string(f.read().decode("UTF-8"))
    except IOError:
        raise SheetException("unable to open file")


def read_tocfile_string(tocfile):
    """given a unicode string of .toc data, returns a TOCFile object

    raises SheetException if some error occurs parsing the file"""

    import audiotools.ply.lex as lex
    import audiotools.ply.yacc as yacc
    from audiotools.ply.yacc import NullLogger
    import audiotools.toc.tokrules
    import audiotools.toc.yaccrules
    from sys import version_info

    str_type = str if (version_info[0] >= 3) else unicode

    assert(isinstance(tocfile, str_type))

    lexer = lex.lex(module=audiotools.toc.tokrules)
    lexer.input(tocfile)
    parser = yacc.yacc(module=audiotools.toc.yaccrules,
                       debug=0,
                       errorlog=NullLogger(),
                       write_tables=0)
    try:
        return parser.parse(lexer=lexer)
    except ValueError as err:
        raise SheetException(str(err))


def write_tocfile(sheet, filename, file):
    """given a Sheet object and filename unicode string,
    writes a .toc file to the given file object"""

    file.write(
        TOCFile.converted(sheet, filename=filename).build().encode("UTF-8"))
