#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2008  Brian Langenberger

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


from audiotools import MetaData,Con,VERSION

class VorbisComment(MetaData,dict):
    VORBIS_COMMENT = Con.Struct("vorbis_comment",
                                Con.PascalString("vendor_string",
                                                 length_field=Con.ULInt32("length")),
                                Con.PrefixedArray(
                                       length_field=Con.ULInt32("length"),
                                       subcon=Con.PascalString("value",
                                                             length_field=Con.ULInt32("length"))),
                                Con.Const(Con.Byte("framing"),1))

    ATTRIBUTE_MAP = {'track_name':'TITLE',
                     'track_number':'TRACKNUMBER',
                     'album_name':'ALBUM',
                     'artist_name':'ARTIST',
                     'performer_name':'PERFORMER',
                     'composer_name':'COMPOSER',
                     'conductor_name':'CONDUCTOR',
                     'media':'SOURCE MEDIUM',
                     'ISRC':'ISRC',
                     'catalog':'CATALOG',
                     'copyright':'COPYRIGHT',
                     'publisher':'PUBLISHER',
                     'year':'DATE',
                     'album_number':'DISCNUMBER',
                     'comment':'COMMENT'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #vorbis_data is a key->[value1,value2,...] dict of the original
    #Vorbis comment data.  keys should be upper case
    def __init__(self, vorbis_data, vendor_string=u""):
        try:
            track_number = int(vorbis_data.get('TRACKNUMBER',['0'])[0])
        except ValueError:
            track_number = 0

        try:
            album_number = int(vorbis_data.get('DISCNUMBER',['0'])[0])
        except ValueError:
            album_number = 0

        MetaData.__init__(
            self,
            track_name = vorbis_data.get('TITLE',[u''])[0],
            track_number = track_number,
            album_name = vorbis_data.get('ALBUM',[u''])[0],
            artist_name = vorbis_data.get('ARTIST',[u''])[0],
            performer_name = vorbis_data.get('PERFORMER',[u''])[0],
            composer_name = vorbis_data.get('COMPOSER',[u''])[0],
            conductor_name = vorbis_data.get('CONDUCTOR',[u''])[0],
            media = vorbis_data.get('SOURCE MEDIUM',[u''])[0],
            ISRC = vorbis_data.get('ISRC',[u''])[0],
            catalog = vorbis_data.get('CATALOG',[u''])[0],
            copyright = vorbis_data.get('COPYRIGHT',[u''])[0],
            publisher = vorbis_data.get('PUBLISHER',[u''])[0],
            year = vorbis_data.get('DATE',[u''])[0],
            date = u"",
            album_number = album_number,
            comment = vorbis_data.get('COMMENT',[u''])[0])

        dict.__init__(self,vorbis_data)
        self.vendor_string = vendor_string

    @classmethod
    def supports_images(cls):
        return False

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (key in self.ATTRIBUTE_MAP):
            if (key not in ('track_number','album_number')):
                self[self.ATTRIBUTE_MAP[key]] = [value]
            else:
                self[self.ATTRIBUTE_MAP[key]] = [unicode(value)]

    #if a dict pair is updated (e.g. self['TITLE'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

        if (self.ITEM_MAP.has_key(key)):
            if (key not in ('TRACKNUMBER','DISCNUMBER')):
                self.__dict__[self.ITEM_MAP[key]] = value[0]
            else:
                self.__dict__[self.ITEM_MAP[key]] = int(value[0])


    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,VorbisComment))):
            return metadata
        elif (hasattr(metadata,'vorbis_comment')):
            #This is a hack to support FlacMetaData.
            #We can't use isinstance() because FlacMetaData contains
            #FlacVorbisComment, and both are defined in __flac__
            #which must be defined *after* __vorbiscomment__ since
            #FlacVorbisComment is a subclass of VorbisComment.
            return metadata.vorbis_comment
        else:
            values = {}
            for key in cls.ATTRIBUTE_MAP.keys():
                if (key == 'track_number'):
                    if (metadata.track_number != 0):
                        values[cls.ATTRIBUTE_MAP[key]] = \
                            [unicode(getattr(metadata,key))]
                elif (key == 'album_number'):
                    if (metadata.album_number != 0):
                        values[cls.ATTRIBUTE_MAP[key]] = \
                            [unicode(getattr(metadata,key))]
                elif (getattr(metadata,key) != u""):
                    values[cls.ATTRIBUTE_MAP[key]] = \
                        [unicode(getattr(metadata,key))]

            return VorbisComment(values)

    def __comment_name__(self):
        return u'Vorbis'

    #takes two (key,value) vorbiscomment pairs
    #returns cmp on the weighted set of them
    #(title first, then artist, album, tracknumber, ... , replaygain)
    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {"TITLE":1,
                   "ALBUM":2,
                   "TRACKNUMBER":3,
                   "DISCNUMBER":4,
                   "ARTIST":5,
                   "PERFORMER":6,
                   "COMPOSER":7,
                   "CONDUCTOR":8,
                   "CATALOG":9,
                   "PUBLISHER":10,
                   "ISRC":11,
                   "SOURCE MEDIUM":12,
                   #"YEAR":13,
                   "DATE":14,
                   "COPYRIGHT":15,
                   "REPLAYGAIN_ALBUM_GAIN":17,
                   "REPLAYGAIN_ALBUM_PEAK":17,
                   "REPLAYGAIN_TRACK_GAIN":17,
                   "REPLAYGAIN_TRACK_PEAK":17,
                   "REPLAYGAIN_REFERENCE_LOUDNESS":18}
        return cmp((KEY_MAP.get(pair1[0].upper(),16),pair1[0].upper(),pair1[1]),
                   (KEY_MAP.get(pair2[0].upper(),16),pair2[0].upper(),pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key,values) in self.items():
            for value in values:
                pairs.append((key,value))

        pairs.sort(VorbisComment.__by_pair__)
        return pairs

    #returns this VorbisComment as a binary string
    def build(self):
        comment = Con.Container(vendor_string = self.vendor_string,
                                framing = 1,
                                value = [])

        for (key,values) in self.items():
            for value in values:
                if (value != u""):
                    comment.value.append("%s=%s" % (key,
                                                    value.encode('utf-8')))
        return self.VORBIS_COMMENT.build(comment)
