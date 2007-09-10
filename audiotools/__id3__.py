#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007  Brian Langenberger

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

from audiotools import MetaData,Con,re,os,ImageMetaData,Image

class EndOfID3v2Stream(Exception): pass
class UnsupportedID3v2Version(Exception): pass

class ID3v2Comment(ImageMetaData,MetaData,dict):
    VALID_FRAME_ID = re.compile(r'[A-Z0-9]{4}')
    FRAME_ID_LENGTH = 4

    ID3v2_HEADER = Con.Struct("id3v2_header",
                              Con.Const(Con.Bytes("file_id",3),'ID3'),
                              Con.Byte("version_major"),
                              Con.Byte("version_minor"),
                              Con.Embed(Con.BitStruct("flags",
                                Con.StrictRepeater(8,
                                                   Con.Flag("flag")))),
                              Con.UBInt32("length"))
  
    FRAME_HEADER = Con.Struct("id3v24_frame",
                              Con.Bytes("frame_id",4),
                              Con.UBInt32("frame_size"),
                              Con.Embed(
            Con.BitStruct("flags",
                          Con.Padding(1),
                          Con.Flag("tag_alter"),
                          Con.Flag("file_alter"),
                          Con.Flag("read_only"),
                          Con.StrictRepeater(5,
                                             Con.Flag("reserved")),
                          Con.Flag("grouping"),
                          Con.Padding(2),
                          Con.Flag("compression"),
                          Con.Flag("encryption"),
                          Con.Flag("unsynchronization"),
                          Con.Flag("data_length"))))

    APIC_FRAME = Con.Struct('APIC',
                            Con.Byte('text_encoding'),
                            Con.CString('mime_type'),
                            Con.Byte('picture_type'),
                            Con.CString('description'),
                            Con.GreedyRepeater(
        Con.Byte('data')))

    ATTRIBUTE_MAP = {'track_name':'TIT2',
                     'track_number':'TRCK',
                     'album_name':'TALB',
                     'artist_name':'TPE1',
                     'performer_name':'TPE2',
                     'year':'TDRC'}
    
    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))
    
    #takes a filename
    #returns an ID3v2Comment-based object
    @classmethod
    def read_id3v2_comment(cls, filename):        
        f = file(filename,"rb")
        
        try:
             frames = {}

             f.seek(0,0)
             try:
                 header = ID3v2Comment.ID3v2_HEADER.parse_stream(f)
             except Con.ConstError:
                 return {}
             if (header.version_major == 0x04):
                 comment_class = ID3v2Comment
             elif (header.version_major == 0x03):
                 comment_class = ID3v2_3Comment
             elif (header.version_major == 0x02):
                 comment_class = ID3v2_2Comment
             else:
                 raise UnsupportedID3v2Version()

             while (True):
                 try:
                     (frame_id,frame_data) = \
                         comment_class.read_id3v2_frame(f)
                     frames[frame_id] = frame_data
                 except EndOfID3v2Stream:
                     break

             return comment_class(frames)

        finally:
            f.close()
    
    #takes a stream of ID3v2 data
    #returns a (frame id,frame data) tuple
    #raises EndOfID3v2Stream if we've reached the end of valid frames
    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16',
                      2:'UTF-16BE',
                      3:'UTF-8'}

        frame = cls.FRAME_HEADER.parse_stream(stream)

        if (cls.VALID_FRAME_ID.match(frame.frame_id)):
            if (frame.frame_id.startswith('T')):
                encoding = ord(stream.read(1))
                value = stream.read(cls.__de_syncsafe32__(frame.frame_size) - 1)
                return (frame.frame_id,
                        value.decode(
                            encode_map.get(encoding,
                                           'ISO-8859-1'),
                            'replace').rstrip(unichr(0x00))
                        )
            else:
                return (frame.frame_id,
                        stream.read(cls.__de_syncsafe32__(frame.frame_size)))
        else:
            raise EndOfID3v2Stream()


    #takes a list of ID3v2 syncsafe bytes and returns a single syncsafe int
    @classmethod
    def __de_syncsafe__(cls, bytes):
        #print bytes
        total = 0
        for byte in bytes:
            total = total << 7
            total += (byte & 0x7F)
        return total

    #takes a 28-bit syncsafed int and returns its 32-bit, de-syncsafed value
    @classmethod
    def __de_syncsafe32__(cls, i):
        return (i & 0x7F) + \
               ((i & 0x7F00) >> 1) + \
               ((i & 0x7F0000) >> 2) + \
               ((i & 0x7F000000) >> 3)

    #takes a 32-bit int and returns a 28-bit syncsafed value
    @classmethod
    def __syncsafe32__(cls, i):
        return (i & 0x7F) + \
               ((i & 0x3F80) << 1) + \
               ((i & 0x1FC000) << 2) + \
               ((i & 0xFE00000) << 3)

    #takes a list of (tag_id,tag_value) tuples
    #returns a string of the whole ID3v2.4 tag
    #tag_id should be a raw, 4 character string
    #value should be a unicode string
    @classmethod
    def build_id3v2(cls, taglist):
        tags = []
        for (t_id,t_value) in taglist:
            try:
                t_s = chr(0x00) + t_value.encode('ISO-8859-1')
            except UnicodeEncodeError:
                #t_s = chr(0x02) + t_value.encode('UTF-16-BE') + (chr(0) * 2)
                t_s = chr(0x03) + t_value.encode('UTF-8')

            tag = Con.Container()
            tag.compression = False
            tag.data_length = False
            tag.encryption = False
            tag.file_alter = False
            tag.frame_id = t_id
            tag.frame_size = ID3v2Comment.__syncsafe32__(len(t_s))
            tag.grouping = False
            tag.read_only = False
            tag.tag_alter = True
            tag.unsynchronization = False
            tag.reserved = [0] * 5

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)

        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = ID3v2Comment.__syncsafe32__(sum(map(len, tags)))
        header.unsynchronization = False
        header.version_major = 4
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)

    #metadata is a key->value dict of ID3v2 data
    def __init__(self, metadata):
        try:
            tracknum = int(metadata.get("TRCK",
                                        metadata.get("TRK",u"0")))
        except ValueError:
            tracknum = 0
        
        MetaData.__init__(self,
                          track_name=metadata.get("TIT2",
                                                  metadata.get("TT2",u"")),
                          
                          track_number=tracknum,
                          
                          album_name=metadata.get("TALB",
                                                  metadata.get("TAL",u"")),
                          
                          artist_name=metadata.get("TPE1",
                                       metadata.get("TP1",
                                        metadata.get("TOPE",
                                         metadata.get("TCOM",
                                          metadata.get("TOLY",
                                           metadata.get("TEXT",               
                                            metadata.get("TOA",
                                             metadata.get("TCM",u"")))))))),
                                                   
                          performer_name=metadata.get("TPE2",
                                           metadata.get("TPE3",
                                            metadata.get("TPE4",
                                             metadata.get("TP2",
                                              metadata.get("TP3",
                                               metadata.get("TP4",u"")))))),

                          copyright=u"",

                          year=metadata.get("TYER",
                                metadata.get("TYE",u""))
                          )

        if (metadata.has_key('APIC')):
            apic = self.APIC_FRAME.parse(metadata['APIC'])

            images = [APICImage(data="".join(map(chr,apic.data)),
                                mime_type=apic.mime_type,
                                description=apic.description,
                                apic_type=apic.picture_type)]
                            
        else:
            images = []

        ImageMetaData.__init__(self,images)
        dict.__init__(self,metadata)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (self.ATTRIBUTE_MAP.has_key(key)):
            if (key != 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = value
            else:
                self[self.ATTRIBUTE_MAP[key]] = unicode(value)

    #if a dict pair is updated (e.g. self['TIT2'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        
        if (self.ITEM_MAP.has_key(key)):
            if (key != 'TRCK'):
                self.__dict__[self.ITEM_MAP[key]] = value
            else:
                self.__dict__[self.ITEM_MAP[key]] = int(value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if (field != u""):
                tags[key] = unicode(field)

        try:
            if (tags["TPE1"] == tags["TPE2"]):
                del(tags["TPE2"])
        except KeyError:
            pass

        return ID3v2Comment(tags)

    def build_tag(self):
        return self.build_id3v2(self.items())

    def __comment_name__(self):
        return u'ID3v2.4'

    def __comment_pairs__(self):
        def __weight__(pair):
            if (pair[0] == 'TIT2'):
                return (1,pair[0],pair[1])
            elif (pair[0] in ('TPE1','TPE2','TPE3','TPE4')):
                return (5,pair[0],pair[1])
            elif (pair[0] == 'TALB'):
                return (2,pair[0],pair[1])
            elif (pair[0] == 'TRCK'):
                return (3,pair[0],pair[1])
            elif (pair[0] in ('TOPE','TCOM','TOLY','TEXT')):
                return (4,pair[0],pair[1])
            elif (pair[0].startswith('T')):
                return (6,pair[0],pair[1])
            else:
                return (7,pair[0],pair[1])

        def __by_weight__(item1,item2):
            return cmp(__weight__(item1),
                       __weight__(item2))

        pairs = []

        for (key,value) in sorted(self.items(),__by_weight__):
            if (isinstance(value,unicode)):
                pairs.append(('    ' + key,value))
            else:
                if (len(value) <= 20):
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex'))))
                else:
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex')[0:39].upper()) + u"\u2026"))

        return pairs

    def __unicode__(self):
        if (len(self.images()) == 0):
            return unicode(MetaData.__unicode__(self))
        else:
            return u"%s\n\n%s" % \
                (unicode(MetaData.__unicode__(self)),
                 "\n".join([unicode(p) for p in self.images()]))

    #takes a file stream
    #checks that stream for an ID3v2 comment
    #if found, repositions the stream past it
    #if not, leaves the stream in the current location
    @classmethod
    def skip(cls, file):
        if (file.read(3) == 'ID3'):
            file.seek(0,0)
            #parse the header
            h = ID3v2Comment.ID3v2_HEADER.parse_stream(file)
            #seek to the end of its length
            file.seek(ID3v2Comment.__de_syncsafe32__(h.length),1)
            #skip any null bytes after the ID3v2 tag
            c = file.read(1)
            while (c == '\x00'):
                c = file.read(1)
            file.seek(-1,1)
        else:
            try:
                file.seek(-3,1)
            except IOError:
                pass

class ID3v2_3Comment(ID3v2Comment):
    FRAME_HEADER = Con.Struct("id3v23_frame",
                              Con.Bytes("frame_id",4),
                              Con.UBInt32("frame_size"),
                              Con.Embed(
            Con.BitStruct("flags",
                          Con.Flag("tag_alter"),
                          Con.Flag("file_alter"),
                          Con.Flag("read_only"),
                          Con.Padding(5),
                          Con.Flag("compression"),
                          Con.Flag("encryption"),
                          Con.Flag("grouping"),
                          Con.Padding(5))))

    ATTRIBUTE_MAP = {'track_name':'TIT2',
                     'track_number':'TRCK',
                     'album_name':'TALB',
                     'artist_name':'TPE1',
                     'performer_name':'TPE2',
                     'year':'TDRC'}
    
    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #takes a stream of ID3v2 data
    #returns a (frame id,frame data) tuple
    #raises EndOfID3v2Stream if we've reached the end of valid frames
    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16'}

        frame = cls.FRAME_HEADER.parse_stream(stream)

        if (cls.VALID_FRAME_ID.match(frame.frame_id)):
            if (frame.frame_id.startswith('T')):
                encoding = ord(stream.read(1))
                value = stream.read(frame.frame_size - 1)

                return (frame.frame_id,
                        value.decode(
                        encode_map.get(encoding,
                                       'ISO-8859-1'),
                        'replace').rstrip(unichr(0x00))
                        )
            else:
                return (frame.frame_id,
                        stream.read(frame.frame_size))
        else:
            raise EndOfID3v2Stream()

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2_3Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if (field != u""):
                tags[key] = unicode(field)

        try:
            if (tags["TPE1"] == tags["TPE2"]):
                del(tags["TPE2"])
        except KeyError:
            pass

        return ID3v2_3Comment(tags)

    def __comment_name__(self):
        return u'ID3v2.3'

    @classmethod
    def build_id3v2(cls, taglist):
        tags = []

        for (t_id,t_value) in taglist:
            try:
                t_s = chr(0x00) + t_value.encode('ISO-8859-1')
            except UnicodeEncodeError:
                t_s = chr(0x01) + t_value.encode('UTF-16')

            tag = Con.Container()
            tag.tag_alter = False
            tag.file_alter = False
            tag.read_only = False
            tag.compression = False
            tag.encryption = False
            tag.grouping = False
            tag.frame_id = t_id
            tag.frame_size = len(t_s)

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)
        
        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = ID3v2Comment.__syncsafe32__(sum(map(len, tags)))
        header.unsynchronization = False
        header.version_major = 3
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)

class ID3v2_2Comment(ID3v2Comment):
    VALID_FRAME_ID = re.compile(r'[A-Z0-9]{3}')
    FRAME_ID_LENGTH = 3

    FRAME_HEADER = Con.Struct("id3v22_frame",
                              Con.Bytes("frame_id",3),
                              Con.Embed(Con.BitStruct("size",
            Con.Bits("frame_size",24))))

    ATTRIBUTE_MAP = {'track_name':'TT2',
                     'track_number':'TRK',
                     'album_name':'TAL',
                     'artist_name':'TP1',
                     'performer_name':'TP2',
                     'year':'TYE'}
    
    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16'}

        frame = cls.FRAME_HEADER.parse_stream(stream)
        if (cls.VALID_FRAME_ID.match(frame.frame_id)):
            if (frame.frame_id.startswith('T')):
                encoding = ord(stream.read(1))
                value = stream.read(frame.frame_size - 1)
                return (frame.frame_id,
                        value.decode(encode_map.get(encoding,'ISO-8859-1'),
                                     'replace').rstrip(unichr(0x00)))
            else:
                return (frame.frame_id,
                        stream.read(frame.frame_size))
        else:
            raise EndOfID3v2Stream()

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2_2Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if (field != u""):
                tags[key] = unicode(field)

        if (tags["TP1"] == tags["TP2"]):
            del(tags["TP2"])

        return ID3v2_2Comment(tags)

    def __comment_name__(self):
        return u'ID3v2.2'

    def __comment_pairs__(self):
        def __weight__(pair):
            if (pair[0] == 'TT2'):
                return (1,pair[0],pair[1])
            elif (pair[0] in ('TP1','TP2','TP3','TP4')):
                return (5,pair[0],pair[1])
            elif (pair[0] == 'TAL'):
                return (2,pair[0],pair[1])
            elif (pair[0] == 'TRK'):
                return (3,pair[0],pair[1])
            elif (pair[0] in ('TOA','TCM')):
                return (4,pair[0],pair[1])
            elif (pair[0].startswith('T')):
                return (6,pair[0],pair[1])
            else:
                return (7,pair[0],pair[1])

        def __by_weight__(item1,item2):
            return cmp(__weight__(item1),
                       __weight__(item2))

        pairs = []

        for (key,value) in sorted(self.items(),__by_weight__):
            if (isinstance(value,unicode)):
                pairs.append(('    ' + key,value))
            else:
                if (len(value) <= 20):
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex'))))
                else:
                    pairs.append(('    ' + key,
                                  unicode(value.encode('hex')[0:39].upper()) + u"\u2026"))

        return pairs


    @classmethod
    def build_id3v2(cls, taglist):
        tags = []

        for (t_id,t_value) in taglist:
            try:
                t_s = chr(0x00) + t_value.encode('ISO-8859-1')
            except UnicodeEncodeError:
                t_s = chr(0x01) + t_value.encode('UTF-16')

            tag = Con.Container()
            tag.frame_id = t_id
            tag.frame_size = len(t_s)

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)
        
        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = ID3v2Comment.__syncsafe32__(sum(map(len, tags)))
        header.unsynchronization = False
        header.version_major = 3
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)


class APICImage(Image):
    def __init__(self, data, mime_type, description, apic_type):
        #FIXME - replace this with a non-PIL image fetching solution
        import Image as PILImage
        import cStringIO
        i = PILImage.open(cStringIO.StringIO(data))

        self.apic_type = apic_type
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=i.size[0],
                       height=i.size[1],
                       color_depth=24,
                       color_count=0,
                       description=description.decode('ascii','replace'),
                       type={3:0,4:1,5:2,6:3}.get(apic_type,4))

    def type_string(self):
        return {0:"Other",
                1:"32x32 pixels 'file icon' (PNG only)",
                2:"Other file icon",
                3:"Cover (front)",
                4:"Cover (back)",
                5:"Leaflet page",
                6:"Media (e.g. label side of CD)",
                7:"Lead artist/lead performer/soloist",
                8:"Artist / Performer",
                9:"Conductor",
                10:"Band / Orchestra",
                11:"Composer",
                12:"Lyricist / Text writer",
                13:"Recording Location",
                14:"During recording",
                15:"During performance",
                16:"Movie/Video screen capture",
                17:"A bright coloured fish",
                18:"Illustration",
                19:"Band/Artist logotype",
                20:"Publisher/Studio logotype"}.get(self.apic_type,"Other")


    def __repr__(self):
        return "APICImage(mime_type=%s,description=%s,apic_type=%s,...)" % \
               (repr(self.mime_type),repr(self.description),
                repr(self.apic_type))

    def __unicode__(self):
        return u"Picture : %s (%d\u00D7%d,'%s')" % \
            (self.type_string(),
             self.width,self.height,self.mime_type)


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
    
    #takes an open mp3 file object
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
                return s[0:length]

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
        MetaData.__init__(self,
                          track_name=metadata[0],
                          track_number=metadata[5],
                          album_name=metadata[2],
                          artist_name=metadata[1],
                          performer_name=u"",
                          copyright=u"",
                          year=unicode(metadata[3]))
        list.__init__(self, metadata)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding list item
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        
        if (key in self.ATTRIBUTES):
            if (key != 'track_number'):
                self[self.ATTRIBUTES.index(key)] = value
            else:
                self[self.ATTRIBUTES.index(key)] = int(value)

    #if a list item is updated (e.g. self[1])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        
        if (key < len(self.ATTRIBUTES)):
            if (key != 5):
                self.__dict__[self.ATTRIBUTES[key]] = value
            else:
                self.__dict__[self.ATTRIBUTES[key]] = int(value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v1Comment))):
            return metadata

        return ID3v1Comment((metadata.track_name,
                             metadata.artist_name,
                             metadata.album_name,
                             metadata.year,
                             u"",
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
                                u"",
                                self.track_number)


class ID3CommentPair(MetaData):
    #id3v2 and id3v1 are ID3v2Comment and ID3v1Comment objects or None
    #values in ID3v2 take precendence over ID3v1, if present
    def __init__(self, id3v2_comment, id3v1_comment):
        self.__dict__['id3v2'] = id3v2_comment
        self.__dict__['id3v1'] = id3v1_comment

        if (self.id3v2 != None):
            base_comment = self.id3v2
        elif (self.id3v1 != None):
            base_comment = self.id3v1
        else:
            raise ValueError("id3v2 and id3v1 cannot both be blank")

        MetaData.__init__(
            self,
            track_name=base_comment.track_name,
            track_number=base_comment.track_number,
            album_name=base_comment.album_name,
            artist_name=base_comment.artist_name,
            performer_name=base_comment.performer_name,
            copyright=base_comment.copyright,
            year=base_comment.year)

    def __setattr__(self, key, value):
        if (self.id3v2 != None):
            setattr(self.id3v2,key,value)
        if (self.id3v1 != None):
            setattr(self.id3v1,key,value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3CommentPair))):
            return metadata

        return ID3CommentPair(
            ID3v2_3Comment.converted(metadata),
            ID3v1Comment.converted(metadata))
            

    def __unicode__(self):
        if ((self.id3v2 != None) and (self.id3v1 != None)):
            #both comments present
            return unicode(self.id3v2) + \
                   (os.linesep * 2) + \
                   unicode(self.id3v1)
        elif (self.id3v2 != None):
            #only ID3v2
            return unicode(self.id3v2)
        elif (self.id3v1 != None):
            #only ID3v1
            return unicode(self.id3v1)
        else:
            return u''
