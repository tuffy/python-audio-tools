#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

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

from audiotools import MetaData


class ID3v1Comment(MetaData):
    """a complete ID3v1.1 tag"""

    # All ID3v1 tags are treated as ID3v1.1
    # because plain ID3v1 tags don't support track number
    # which means it'll be impossible to "promote" a tag later on.

    ID3v1_FIELDS = {"track_name": "__track_name__",
                    "artist_name": "__artist_name__",
                    "album_name": "__album_name__",
                    "year": "__year__",
                    "comment": "__comment__",
                    "track_number": "__track_number__"}

    FIELD_LENGTHS = {"track_name": 30,
                     "artist_name": 30,
                     "album_name": 30,
                     "year": 4,
                     "comment": 28}

    def __init__(self, track_name=chr(0) * 30,
                 artist_name=chr(0) * 30,
                 album_name=chr(0) * 30,
                 year=chr(0) * 4,
                 comment=chr(0) * 28,
                 track_number=chr(0),
                 genre=chr(0)):
        """fields are as follows:

        | field        | length |
        |--------------+--------|
        | track_name   |     30 |
        | artist_name  |     30 |
        | album_name   |     30 |
        | year         |      4 |
        | comment      |     28 |
        | track_number |      1 |
        | genre        |      1 |
        |--------------+--------|

        all are binary strings of the given length
        and must not be any shorter or longer
        """

        if (len(track_name) != 30):
            raise ValueError("track_name must be exactly 30 bytes")
        if (len(artist_name) != 30):
            raise ValueError("artist_name must be exactly 30 bytes")
        if (len(album_name) != 30):
            raise ValueError("album_name must be exactly 30 bytes")
        if (len(year) != 4):
            raise ValueError("year must be exactly 4 bytes")
        if (len(comment) != 28):
            raise ValueError("comment must be exactly 28 bytes")
        if (len(track_number) != 1):
            raise ValueError("track_number must be exactly 1 byte")
        if (len(genre) != 1):
            raise ValueError("genre must be exactly 1 byte")

        self.__dict__['__track_name__'] = track_name
        self.__dict__['__artist_name__'] = artist_name
        self.__dict__['__album_name__'] = album_name
        self.__dict__['__year__'] = year
        self.__dict__['__comment__'] = comment
        self.__dict__['__track_number__'] = track_number
        self.__dict__['__genre__'] = genre

    def __repr__(self):
        return "ID3v1Comment(%s, %s, %s, %s, %s, %s, %s)" % \
            (repr(self.__dict__['__track_name__']),
             repr(self.__dict__['__artist_name__']),
             repr(self.__dict__['__album_name__']),
             repr(self.__dict__['__year__']),
             repr(self.__dict__['__comment__']),
             repr(self.__dict__['__track_number__']),
             repr(self.__dict__['__genre__']))

    def __getattr__(self, attr):
        if (attr == "track_number"):
            number = ord(self.__dict__['__track_number__'])
            if (number > 0):
                return number
            else:
                return None
        elif (attr in self.ID3v1_FIELDS):
            value = self.__dict__[self.ID3v1_FIELDS[attr]].rstrip(
                chr(0)).decode('ascii', 'replace')
            if (len(value) > 0):
                return value
            else:
                return None
        elif (attr in self.FIELDS):
            return None
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if (attr == "track_number"):
            if (value is None):
                self.__dict__['__track_number__'] = chr(0)
            else:
                self.__dict__['__track_number__'] = chr(min(int(value), 0xFF))
        elif (attr in self.FIELD_LENGTHS):
            if (value is None):
                delattr(self, attr)
            else:
                # all are text fields
                encoded = value.encode('ascii', 'replace')
                if (len(encoded) < self.FIELD_LENGTHS[attr]):
                    self.__dict__[self.ID3v1_FIELDS[attr]] = \
                        encoded + chr(0) * (self.FIELD_LENGTHS[attr] -
                                            len(encoded))
                elif (len(encoded) > self.FIELD_LENGTHS[attr]):
                    self.__dict__[self.ID3v1_FIELDS[attr]] = \
                        encoded[0:self.FIELD_LENGTHS[attr]]
                else:
                    self.__dict__[self.ID3v1_FIELDS[attr]] = encoded
        elif (attr in self.FIELDS):
            # field not supported by ID3v1Comment, so ignore it
            pass
        else:
            self.__dict__[attr] = value

    def __delattr__(self, attr):
        if (attr == "track_number"):
            self.__dict__['__track_number__'] = chr(0)
        elif (attr in self.FIELD_LENGTHS):
            self.__dict__[self.ID3v1_FIELDS[attr]] = \
                chr(0) * self.FIELD_LENGTHS[attr]
        elif (attr in self.FIELDS):
            # field not supported by ID3v1Comment, so ignore it
            pass
        else:
            del(self.__dict__[attr])

    def raw_info(self):
        """returns a human-readable version of this metadata
        as a unicode string"""

        from os import linesep

        return linesep.decode('ascii').join(
            [u"ID3v1.1:"] +
            [u"%s = %s" % (label, getattr(self, attr))
             for (label, attr) in [(u"  track name", "track_name"),
                                   (u" artist name", "artist_name"),
                                   (u"  album name", "album_name"),
                                   (u"        year", "year"),
                                   (u"     comment", "comment"),
                                   (u"track number", "track_number")]
             if (getattr(self, attr) is not None)] +
            [u"       genre = %d" % (ord(self.__genre__))])

    @classmethod
    def parse(cls, mp3_file):
        """given an MP3 file, returns an ID3v1Comment

        raises ValueError if the comment is invalid"""

        from audiotools.bitstream import BitstreamReader

        mp3_file.seek(-128, 2)
        reader = BitstreamReader(mp3_file, 0)
        (tag,
         track_name,
         artist_name,
         album_name,
         year,
         comment,
         track_number,
         genre) = reader.parse("3b 30b 30b 30b 4b 28b 8p 1b 1b")
        if (tag != 'TAG'):
            raise ValueError(u"invalid ID3v1 tag")

        return ID3v1Comment(track_name=track_name,
                            artist_name=artist_name,
                            album_name=album_name,
                            year=year,
                            comment=comment,
                            track_number=track_number,
                            genre=genre)

    def build(self, mp3_file):
        """given an MP3 file positioned at the file's end, generate a tag"""

        from audiotools.bitstream import BitstreamWriter

        BitstreamWriter(mp3_file, 0).build(
            "3b 30b 30b 30b 4b 28b 8p 1b 1b",
            ("TAG",
             self.__dict__['__track_name__'],
             self.__dict__['__artist_name__'],
             self.__dict__['__album_name__'],
             self.__dict__['__year__'],
             self.__dict__['__comment__'],
             self.__dict__['__track_number__'],
             self.__dict__['__genre__']))

    @classmethod
    def supports_images(cls):
        """returns False"""

        return False

    @classmethod
    def converted(cls, metadata):
        """converts a MetaData object to an ID3v1Comment object"""

        if (metadata is None):
            return None
        elif (isinstance(metadata, ID3v1Comment)):
            # duplicate all fields as-is
            return ID3v1Comment(track_name=metadata.__track_name__,
                                artist_name=metadata.__artist_name__,
                                album_name=metadata.__album_name__,
                                year=metadata.__year__,
                                comment=metadata.__comment__,
                                track_number=metadata.__track_number__,
                                genre=metadata.__genre__)
        else:
            # convert fields using setattr
            id3v1 = ID3v1Comment()
            for attr in ["track_name",
                         "artist_name",
                         "album_name",
                         "year",
                         "comment",
                         "track_number"]:
                setattr(id3v1, attr, getattr(metadata, attr))
            return id3v1

    def images(self):
        """returns an empty list of Image objects"""

        return []

    def clean(self):
        """returns a new ID3v1Comment object that's been cleaned of problems"""

        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE)

        fixes_performed = []
        fields = {}
        for (init_attr,
             attr,
             name) in [("track_name", "__track_name__", u"title"),
                       ("artist_name", "__artist_name__", u"artist"),
                       ("album_name", "__album_name__", u"album"),
                       ("year", "__year__", u"year"),
                       ("comment", "__comment__", u"comment")]:
            # strip out trailing NULL bytes
            initial_value = getattr(self, attr).rstrip(chr(0))

            fix1 = initial_value.rstrip()
            if (fix1 != initial_value):
                fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                       {"field": name})
            fix2 = fix1.lstrip()
            if (fix2 != fix1):
                fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                       {"field": name})

            # restore trailing NULL bytes
            fields[init_attr] = (fix2 + chr(0) *
                                 (self.FIELD_LENGTHS[init_attr] - len(fix2)))

        # copy non-text fields as-is
        fields["track_number"] = self.__track_number__
        fields["genre"] = self.__genre__

        return (ID3v1Comment(**fields), fixes_performed)
