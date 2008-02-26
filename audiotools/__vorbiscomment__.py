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
                     'copyright':'COPYRIGHT',
                     'year':'YEAR'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #vorbis_data is a key->[value1,value2,...] dict of the original
    #Vorbis comment data.  keys should be upper case
    def __init__(self, vorbis_data, vendor_string=u""):
        MetaData.__init__(
            self,
            track_name = vorbis_data.get('TITLE',[u''])[0],
            track_number = int(vorbis_data.get('TRACKNUMBER',['0'])[0]),
            album_name = vorbis_data.get('ALBUM',[u''])[0],
            artist_name = vorbis_data.get('ARTIST',[u''])[0],
            performer_name = vorbis_data.get('PERFORMER',[u''])[0],
            copyright = vorbis_data.get('COPYRIGHT',[u''])[0],
            year = vorbis_data.get('YEAR',[u''])[0])
                          
        dict.__init__(self,vorbis_data)
        self.vendor_string = vendor_string

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        
        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key != 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = [value]
            else:
                self[self.ATTRIBUTE_MAP[key]] = [unicode(value)]

    #if a dict pair is updated (e.g. self['TITLE'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        
        if (self.ITEM_MAP.has_key(key)):
            if (key != 'TRACKNUMBER'):
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
                if (getattr(metadata,key) != u""):
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
                   "ARTIST":4,
                   "PERFORMER":5,
                   "TRACKNUMBER":3,
                   "COPYRIGHT":7,
                   "YEAR":6,
                   "REPLAYGAIN_ALBUM_GAIN":9,
                   "REPLAYGAIN_ALBUM_PEAK":9,
                   "REPLAYGAIN_TRACK_GAIN":9,
                   "REPLAYGAIN_TRACK_PEAK":9,
                   "REPLAYGAIN_REFERENCE_LOUDNESS":10}
        return cmp((KEY_MAP.get(pair1[0].upper(),8),pair1[0].upper(),pair1[1]),
                   (KEY_MAP.get(pair2[0].upper(),8),pair2[0].upper(),pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key,values) in self.items():
            for value in values:
                pairs.append((key,value))

        pairs.sort(VorbisComment.__by_pair__)
        return pairs

    #returns this VorbisComment as a binary string
    def build(self):
        comment = Con.Container()
        comment.vendor_string = self.vendor_string
        comment.framing = 1
        comment.value = []
        for (key,values) in self.items():
            for value in values:
                comment.value.append("%s=%s" % (key,
                                                value.encode('utf-8')))
        return self.VORBIS_COMMENT.build(comment)
