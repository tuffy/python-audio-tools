#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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

from audiotools import MetaData


class ID3v1Comment(MetaData):
    """A complete ID3v1 tag."""

    def __init__(self, track_name, artist_name, album_name,
                 year, comment, track_number, genre):
        #pre-emptively cut down overlong fields
        MetaData.__init__(self,
                          track_name=track_name[0:30],
                          artist_name=artist_name[0:30],
                          album_name=album_name[0:30],
                          year=year[0:4],
                          comment=comment[0:28],
                          track_number=track_number)
        self.__dict__['genre'] = genre

    def raw_info(self):
        from os import linesep

        return linesep.decode('ascii').join(
            [u"ID3v1:",
             u"  track name = %s" % (self.track_name),
             u" artist name = %s" % (self.artist_name),
             u"  album name = %s" % (self.album_name),
             u"        year = %s" % (self.year),
             u"     comment = %s" % (self.comment),
             u"track number = %d" % (self.track_number),
             u"       genre = %d" % (self.genre)])

    @classmethod
    def parse(cls, mp3_file):
        """given an MP3 file, returns an ID3v1Comment

        raises ValueError if the comment is invalid"""

        from .bitstream import BitstreamReader

        mp3_file.seek(-128, 2)
        reader = BitstreamReader(mp3_file, 0)
        (tag,
         track_name,
         artist_name,
         album_name,
         year,
         comment) = reader.parse("3b 30b 30b 30b 4b 28b")
        if (tag != 'TAG'):
            raise ValueError(_(u"invalid ID3v1 tag"))
        separator = reader.read(8)
        if (separator == 0):
            track_number = reader.read(8)
        else:
            track_number = 0
            comment = chr(separator) + reader.read_bytes(1)
        genre = reader.read(8)

        return cls(track_name=
                   track_name.rstrip(chr(0)).decode('ascii', 'replace'),
                   artist_name=
                   artist_name.rstrip(chr(0)).decode('ascii', 'replace'),
                   album_name=
                   album_name.rstrip(chr(0)).decode('ascii', 'replace'),
                   year=
                   year.rstrip(chr(0)).decode('ascii', 'replace'),
                   comment=
                   comment.rstrip(chr(0)).decode('ascii', 'replace'),
                   track_number=track_number,
                   genre=genre)

    def build(self, mp3_file):
        """given an MP3 file positioned at the file's end, generate a tag"""

        def __s_pad__(s, length):
            if (len(s) < length):
                return s + chr(0) * (length - len(s))
            else:
                s = s[0:length].rstrip()
                return s + chr(0) * (length - len(s))

        from .bitstream import BitstreamWriter

        BitstreamWriter(mp3_file, 0).build(
            "3b 30b 30b 30b 4b 28b 8p 8u 8u",
            ("TAG",
             __s_pad__(self.track_name.encode('ascii', 'replace'), 30),
             __s_pad__(self.artist_name.encode('ascii', 'replace'), 30),
             __s_pad__(self.album_name.encode('ascii', 'replace'), 30),
             __s_pad__(self.year.encode('ascii', 'replace'), 4),
             __s_pad__(self.comment.encode('ascii', 'replace'), 28),
             self.track_number,
             self.genre))

    @classmethod
    def supports_images(cls):
        """Returns False."""

        return False

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to an ID3v1Comment object."""

        if (metadata is None):
            return None
        elif (isinstance(metadata, ID3v1Comment)):
            return ID3v1Comment(track_name=metadata.track_name,
                                artist_name=metadata.artist_name,
                                album_name=metadata.album_name,
                                year=metadata.year,
                                comment=metadata.comment,
                                track_number=metadata.track_number,
                                genre=metadata.genre)
        else:
            return ID3v1Comment(track_name=metadata.track_name,
                                artist_name=metadata.artist_name,
                                album_name=metadata.album_name,
                                year=metadata.year,
                                comment=metadata.comment,
                                track_number=metadata.track_number,
                                genre=0)

    def images(self):
        """Returns an empty list of Image objects."""

        return []

    def clean(self, fixes_performed):
        fields = {}
        for (attr, name) in [("track_name", u"title"),
                             ("artist_name", u"artist"),
                             ("album_name", u"album"),
                             ("year", u"year"),
                             ("comment", u"comment")]:
            fix1 = getattr(self, attr).rstrip()
            if (fix1 != getattr(self, attr)):
                fixes_performed.append(
                    _(u"removed trailing whitespace from %(field)s") %
                    {"field":name})
            fix2 = fix1.lstrip()
            if (fix2 != fix1):
                fixes_performed.append(
                    _(u"removed leading whitespace from %(field)s") %
                    {"field":name})
            fields[attr] = fix2

        for attr in ["track_number", "genre"]:
            fields[attr] = getattr(self, attr)

        return ID3v1Comment(**fields)
