#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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

from audiotools import MetaData,Con,os

class ID3v1Comment(MetaData,list):
    ID3v1 = Con.Struct("id3v1",
      Con.Const(Con.String("identifier",3),'TAG'),
      Con.String("song_title",30),
      Con.String("artist",30),
      Con.String("album",30),
      Con.String("year",4),
      Con.String("comment",28),
      Con.Padding(1),
      Con.Byte("track_number"),
      Con.Byte("genre"))

    ID3v1_NO_TRACKNUMBER = Con.Struct("id3v1_notracknumber",
      Con.Const(Con.String("identifier",3),'TAG'),
      Con.String("song_title",30),
      Con.String("artist",30),
      Con.String("album",30),
      Con.String("year",4),
      Con.String("comment",30),
      Con.Byte("genre"))

    ATTRIBUTES = ['track_name',
                  'artist_name',
                  'album_name',
                  'year',
                  'comment',
                  'track_number']

    #takes an MP3 filename
    #returns a (song title, artist, album, year, comment, track number) tuple
    #if no ID3v1 tag is present, returns a tuple with those fields blank
    #all text is in unicode
    #if track number is -1, the id3v1 comment could not be found
    @classmethod
    def read_id3v1_comment(cls, mp3filename):
        mp3file = file(mp3filename,"rb")
        try:
            mp3file.seek(-128,2)
            try:
                id3v1 = ID3v1Comment.ID3v1.parse(mp3file.read())
            except Con.adapters.PaddingError:
                mp3file.seek(-128,2)
                id3v1 = ID3v1Comment.ID3v1_NO_TRACKNUMBER.parse(mp3file.read())
                id3v1.track_number = 0
            except Con.ConstError:
                return tuple([u""] * 5 + [-1])

            field_list = (id3v1.song_title,
                          id3v1.artist,
                          id3v1.album,
                          id3v1.year,
                          id3v1.comment)

            return tuple(map(lambda t:
                             t.rstrip('\x00').decode('ascii','replace'),
                             field_list) + [id3v1.track_number])
        finally:
            mp3file.close()


    #takes several unicode strings (except for track_number, an int)
    #pads them with nulls and returns a complete ID3v1 tag
    @classmethod
    def build_id3v1(cls, song_title, artist, album, year, comment,
                    track_number):
        def __s_pad__(s,length):
            if (len(s) < length):
                return s + chr(0) * (length - len(s))
            else:
                s = s[0:length].rstrip()
                return s + chr(0) * (length - len(s))

        c = Con.Container()
        c.identifier = 'TAG'
        c.song_title = __s_pad__(song_title.encode('ascii','replace'),30)
        c.artist = __s_pad__(artist.encode('ascii','replace'),30)
        c.album = __s_pad__(album.encode('ascii','replace'),30)
        c.year = __s_pad__(year.encode('ascii','replace'),4)
        c.comment = __s_pad__(comment.encode('ascii','replace'),28)
        c.track_number = int(track_number)
        c.genre = 0

        return ID3v1Comment.ID3v1.build(c)

    #metadata is the title,artist,album,year,comment,tracknum tuple returned by
    #read_id3v1_comment
    def __init__(self, metadata):
        list.__init__(self, metadata)

    def supports_images(self):
        return False

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding list item
    def __setattr__(self, key, value):
        if (key in self.ATTRIBUTES):
            if (key != 'track_number'):
                self[self.ATTRIBUTES.index(key)] = value
            else:
                self[self.ATTRIBUTES.index(key)] = int(value)
        elif (key in MetaData.__FIELDS__):
            pass
        else:
            self.__dict__[key] = value

    def __delattr__(self,key):
        if (key == 'track_number'):
            setattr(self,key,0)
        elif (key in self.ATTRIBUTES):
            setattr(self,key,u"")

    def __getattr__(self,key):
        if (key in self.ATTRIBUTES):
            return self[self.ATTRIBUTES.index(key)]
        elif (key in MetaData.__INTEGER_FIELDS__):
            return 0
        elif (key in MetaData.__FIELDS__):
            return u""
        else:
            raise AttributeError(key)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v1Comment))):
            return metadata

        return ID3v1Comment((metadata.track_name,
                             metadata.artist_name,
                             metadata.album_name,
                             metadata.year,
                             metadata.comment,
                             int(metadata.track_number)))

    def __comment_name__(self):
        return u'ID3v1'

    def __comment_pairs__(self):
        return zip(('Title','Artist','Album','Year','Comment','Tracknum'),
                   self)

    def build_tag(self):
        return self.build_id3v1(self.track_name,
                                self.artist_name,
                                self.album_name,
                                self.year,
                                self.comment,
                                self.track_number)

    def images(self):
        return []


