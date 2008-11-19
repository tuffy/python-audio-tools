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

from audiotools import MetaData,Con,re,os,Image,InvalidImage

class EndOfID3v2Stream(Exception): pass
class UnsupportedID3v2Version(Exception): pass

class Syncsafe32(Con.Adapter):
    def __init__(self, name):
        Con.Adapter.__init__(self,
                             Con.StrictRepeater(4,Con.UBInt8(name)))

    def _encode(self, value, context):
        data = []
        for i in xrange(4):
            data.append(value & 0x7F)
            value = value >> 7
        data.reverse()
        return data

    def _decode(self, obj, context):
        i = 0
        for x in obj:
            i = (i << 7) | (x & 0x7F)
        return i

class ID3v2Comment(MetaData,dict):
    VALID_FRAME_ID = re.compile(r'[A-Z0-9]{4}')
    FRAME_ID_LENGTH = 4

    ID3v2_HEADER = Con.Struct("id3v2_header",
                              Con.Const(Con.Bytes("file_id",3),'ID3'),
                              Con.Byte("version_major"),
                              Con.Byte("version_minor"),
                              Con.Embed(Con.BitStruct("flags",
                                Con.StrictRepeater(8,
                                                   Con.Flag("flag")))),
                              Syncsafe32("length"))

    FRAME_HEADER = Con.Struct("id3v24_frame",
                              Con.Bytes("frame_id",4),
                              Syncsafe32("frame_size"),
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

    ATTRIBUTE_MAP = {'track_name':'TIT2',
                     'track_number':'TRCK',
                     'album_name':'TALB',
                     'artist_name':'TPE1',
                     'performer_name':'TPE2',
                     'composer_name':'TCOM',
                     'conductor_name':'TPE3',
                     'media':'TMED',
                     'ISRC':'TSRC',
                     'copyright':'TCOP',
                     'publisher':'TPUB',
                     'year':'TYER',
                     'date':'TRDA',
                     'album_number':'TPOS'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #takes a filename
    #returns an ID3v2Comment-based object
    @classmethod
    def read_id3v2_comment(cls, filename):
        import cStringIO

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

             stream = cStringIO.StringIO(f.read(header.length))
             while (True):
                 try:
                     (frame_id,frame_data) = comment_class.read_id3v2_frame(stream)
                     frames.setdefault(frame_id,[]).append(frame_data)
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

        try:
            frame = cls.FRAME_HEADER.parse_stream(stream)
        except:
            raise EndOfID3v2Stream()

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


    #takes a list of (tag_id,tag_value) tuples
    #returns a string of the whole ID3v2.4 tag
    #tag_id should be a raw, 4 character string
    #value should be a unicode string
    @classmethod
    def build_id3v2(cls, taglist):
        tags = []
        for (t_id,t_value) in taglist:
            if (t_id.startswith('T')):
                try:
                    t_s = chr(0x00) + t_value.encode('ISO-8859-1')
                except UnicodeEncodeError:
                    t_s = chr(0x03) + t_value.encode('UTF-8')
            else:
                t_s = t_value

            tag = Con.Container()
            tag.compression = False
            tag.data_length = False
            tag.encryption = False
            tag.file_alter = False
            tag.frame_id = t_id
            tag.frame_size = len(t_s)
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
        header.length = sum(map(len, tags))
        header.unsynchronization = False
        header.version_major = 4
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)

    #metadata is a key->value dict of ID3v2 data
    def __init__(self, metadata):
        tracknum = re.match(
            r'\d+',
            metadata.get("TRCK",metadata.get("TRK",[u"0"]))[0])
        if (tracknum is not None):
            tracknum = int(tracknum.group(0))
        else:
            tracknum = 0

        albumnum = re.match(
            r'\d+',
            metadata.get("TPOS",
                         metadata.get("TPA",[u"0"]))[0])
        if (albumnum is not None):
            albumnum = int(albumnum.group(0))
        else:
            albumnum = 0


        images = []
        if ('APIC' in metadata):
            for apic_frame in metadata['APIC']:
                try:
                    apic = APICImage.APIC_FRAME.parse(apic_frame)
                except Con.RangeError:
                    continue

                try:
                    images.append(APICImage(
                            data=apic.data,
                            mime_type=apic.mime_type.decode('ascii'),
                            description=apic.description.decode(
                                ('ascii',
                                 'utf-16',
                                 'utf-16be',
                                 'utf-8')[apic.text_encoding],'replace'),
                            apic_type=apic.picture_type))
                except InvalidImage:
                    pass

        if ('PIC' in metadata):
            for pic_frame in metadata['PIC']:
                try:
                    pic = PICImage.PIC_FRAME.parse(pic_frame)
                except Con.RangeError:
                    continue

                images.append(PICImage(data=pic.data,
                                       format=pic.format.decode('ascii'),
                                       description=pic.description.decode(
                    ('ascii','utf-16')[pic.text_encoding]),
                                       pic_type=pic.picture_type))

        MetaData.__init__(self,
                          track_name=metadata.get("TIT2",
                                                  metadata.get("TT2",[u""]))[0],

                          track_number=tracknum,

                          album_name=metadata.get("TALB",
                                                  metadata.get("TAL",[u""]))[0],

                          artist_name=metadata.get("TPE1",
                                       metadata.get("TP1",
                                        metadata.get("TOPE",
                                         metadata.get("TCOM",
                                          metadata.get("TOLY",
                                           metadata.get("TEXT",
                                            metadata.get("TOA",
                                             metadata.get("TCM",[u""]))))))))[0],

                          performer_name=metadata.get("TPE2",
                                           metadata.get("TPE3",
                                            metadata.get("TPE4",
                                             metadata.get("TP2",
                                              metadata.get("TP3",
                                               metadata.get("TP4",[u""]))))))[0],
                          composer_name=metadata.get("TCOM",
                                          metadata.get("TCM",[u""]))[0],

                          conductor_name=metadata.get("TPE3",[u""])[0],

                          media=metadata.get("TMED",
                                  metadata.get("TMT",[u""]))[0],

                          ISRC=metadata.get("TSRC",
                                 metadata.get("TRC",[u""]))[0],

                          catalog=u"",

                          copyright=metadata.get("TCOP",
                                      metadata.get("TCR",[u""]))[0],

                          publisher=metadata.get("TPUB",
                                      metadata.get("TPB",[u""]))[0],

                          year=metadata.get("TYER",
                                metadata.get("TYE",[u""]))[0],

                          date=metadata.get("TRDA",
                                 metadata.get("TRD",[u""]))[0],

                          album_number = albumnum,

                          images=images)


        dict.__init__(self,metadata)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (key in self.ATTRIBUTE_MAP):
            if (key in ('track_number','album_number')):
                #track_number and album_number integers
                #are converted to Unicode objects
                self[self.ATTRIBUTE_MAP[key]] = [unicode(value)]
            else:
                self[self.ATTRIBUTE_MAP[key]] = [value]

    #if a dict pair is updated (e.g. self['TIT2'])
    #make sure to update the corresponding attribute
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

        if (key in self.ITEM_MAP):
            if (key in ('TRCK','TPOS')):
                #track_number and album_number are converted
                #from Unicode objects to integers
                int_val = re.match(r'\d+',value[0])
                if (int_val is not None):
                    self.__dict__[self.ITEM_MAP[key]] = int(int_val.group(0))
            else:
                self.__dict__[self.ITEM_MAP[key]] = value[0]

    def add_image(self, image):
        image = APICImage.converted(image)

        self.setdefault('APIC',[]).append(image.build())
        MetaData.add_image(self, image)

    def delete_image(self, image):
        del(self['APIC'][self['APIC'].index(image.build())])
        MetaData.delete_image(self, image)


    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3v2Comment))):
            return metadata

        tags = {}

        for (key,field) in cls.ITEM_MAP.items():
            field = getattr(metadata,field)
            if ((field != u"") and (field != 0)):
                tags[key] = [unicode(field)]

        try:
            if (tags["TPE1"] == tags["TPE2"]):
                del(tags["TPE2"])
        except KeyError:
            pass


        if (len(metadata.images()) > 0):
            tags["APIC"] = [APICImage.converted(i).build()
                            for i in metadata.images()]

        return ID3v2Comment(tags)

    def build_tag(self):
        taglist = []
        for (key,values) in self.items():
            for value in values:
                taglist.append((key,value))
        return self.build_id3v2(taglist)

    def __comment_name__(self):
        return u'ID3v2.4'

    def __comment_pairs__(self):
        def __weight__(pair):
            if (pair[0] == 'TIT2'):
                return (1,pair[0],pair[1])
            elif (pair[0] == 'TALB'):
                return (2,pair[0],pair[1])
            elif (pair[0] == 'TRCK'):
                return (3,pair[0],pair[1])
            elif (pair[0] == 'TPOS'):
                return (4,pair[0],pair[1])
            elif (pair[0] == 'TPE1'):
                return (5,pair[0],pair[1])
            elif (pair[0] == 'TPE2'):
                return (6,pair[0],pair[1])
            elif (pair[0] == 'TCOM'):
                return (7,pair[0],pair[1])
            elif (pair[0] == 'TPE3'):
                return (8,pair[0],pair[1])

            elif (pair[0] == 'TPUB'):
                return (10,pair[0],pair[1])
            elif (pair[0] == 'TSRC'):
                return (11,pair[0],pair[1])
            elif (pair[0] == 'TMED'):
                return (12,pair[0],pair[1])
            elif (pair[0] == 'TYER'):
                return (13,pair[0],pair[1])
            elif (pair[0] == 'TRDA'):
                return (14,pair[0],pair[1])
            elif (pair[0] == 'TCOP'):
                return (15,pair[0],pair[1])
            elif (pair[0].startswith('T')):
                return (16,pair[0],pair[1])
            else:
                return (17,pair[0],pair[1])

        def __by_weight__(item1,item2):
            return cmp(__weight__(item1),
                       __weight__(item2))

        pairs = []

        for (key,values) in sorted(self.items(),__by_weight__):
            for value in values:
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
    def supports_images(cls):
        return True

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
            file.seek(h.length,1)
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
                     'composer_name':'TCOM',
                     'conductor_name':'TPE3',
                     'media':'TMED',
                     'ISRC':'TSRC',
                     'copyright':'TCOP',
                     'publisher':'TPUB',
                     'year':'TYER',
                     'date':'TRDA',
                     'album_number':'TPOS'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    #takes a stream of ID3v2 data
    #returns a (frame id,frame data) tuple
    #raises EndOfID3v2Stream if we've reached the end of valid frames
    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16'}

        try:
            frame = cls.FRAME_HEADER.parse_stream(stream)
        except:
            raise EndOfID3v2Stream()

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
            if ((field != u"") and (field != 0)):
                tags[key] = [unicode(field)]

        try:
            if (tags["TPE1"] == tags["TPE2"]):
                del(tags["TPE2"])
        except KeyError:
            pass

        if (len(metadata.images()) > 0):
            tags["APIC"] = [APICImage.converted(i).build()
                            for i in metadata.images()]

        return ID3v2_3Comment(tags)

    def __comment_name__(self):
        return u'ID3v2.3'

    @classmethod
    def build_id3v2(cls, taglist):
        tags = []

        for (t_id,t_value) in taglist:
            if (t_id.startswith('T')):
                try:
                    t_s = chr(0x00) + t_value.encode('ISO-8859-1')
                except UnicodeEncodeError:
                    t_s = chr(0x01) + t_value.encode('UTF-16')
            else:
                t_s = t_value

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
        header.length = sum(map(len, tags))
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
                     'composer_name':'TCM',
                     'media':'TMT',
                     'ISRC':'TRC',
                     'copyright':'TCR',
                     'publisher':'TPB',
                     'year':'TYE',
                     'date':'TRD',
                     'album_number':'TPA'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    @classmethod
    def read_id3v2_frame(cls, stream):
        encode_map = {0:'ISO-8859-1',
                      1:'UTF-16'}
        try:
            frame = cls.FRAME_HEADER.parse_stream(stream)
        except:
            raise EndOfID3v2Stream()

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
            if ((field != u"") and (field != 0)):
                tags[key] = [unicode(field)]

        if (tags["TP1"] == tags["TP2"]):
            del(tags["TP2"])

        if (len(metadata.images()) > 0):
            tags['PIC'] = [PICImage.converted(i).build()
                           for i in metadata.images()]

        return ID3v2_2Comment(tags)

    def __comment_name__(self):
        return u'ID3v2.2'

    def __comment_pairs__(self):
        def __weight__(pair):
            if (pair[0] == 'TT2'):
                return (1,pair[0],pair[1])
            elif (pair[0] == 'TAL'):
                return (2,pair[0],pair[1])
            elif (pair[0] == 'TRK'):
                return (3,pair[0],pair[1])
            elif (pair[0] == 'TPA'):
                return (4,pair[0],pair[1])
            elif (pair[0] == 'TP1'):
                return (5,pair[0],pair[1])
            elif (pair[0] == 'TCM'):
                return (6,pair[0],pair[1])

            elif (pair[0] == 'TPB'):
                return (9,pair[0],pair[1])
            elif (pair[0] == 'TRC'):
                return (10,pair[0],pair[1])
            elif (pair[0] == 'TMT'):
                return (11,pair[0],pair[1])
            elif (pair[0] == 'TOR'):
                return (12,pair[0],pair[1])
            elif (pair[0] == 'TRD'):
                return (13,pair[0],pair[1])
            elif (pair[0] == 'TCR'):
                return (14,pair[0],pair[1])
            elif (pair[0].startswith('T')):
                return (15,pair[0],pair[1])
            else:
                return (16,pair[0],pair[1])

        def __by_weight__(item1,item2):
            return cmp(__weight__(item1),
                       __weight__(item2))

        pairs = []

        for (key,values) in sorted(self.items(),__by_weight__):
            for value in values:
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
            if (t_id.startswith('T')):
                try:
                    t_s = chr(0x00) + t_value.encode('ISO-8859-1')
                except UnicodeEncodeError:
                    t_s = chr(0x01) + t_value.encode('UTF-16')
            else:
                t_s = t_value

            tag = Con.Container()
            tag.frame_id = t_id
            tag.frame_size = len(t_s)

            tags.append(cls.FRAME_HEADER.build(tag) + t_s)

        header = Con.Container()
        header.experimental = False
        header.extended_header = False
        header.file_id = 'ID3'
        header.footer = False
        header.length = sum(map(len, tags))
        header.unsynchronization = False
        header.version_major = 2
        header.version_minor = 0
        header.flag = [0,0,0,0,0,0,0,0]

        return cls.ID3v2_HEADER.build(header) + "".join(tags)

    def add_image(self, image):
        image = PICImage.converted(image)

        self.setdefault('PIC',[]).append(image.build())
        MetaData.add_image(self, image)

    def delete_image(self, image):
        del(self['PIC'][self['PIC'].index(image.build())])
        MetaData.delete_image(self, image)


class APICImage(Image):

    #FIXME - UTF-16 description strings will break this
    #        because of the embedded NULL bytes.
    #        Construct's CString won't look two bytes ahead
    #        to find a UTF-16 NULL, so we're hosed.
    #        Just another example of ID3v2 unpleasantness.
    APIC_FRAME = Con.Struct('APIC',
                            Con.Byte('text_encoding'),
                            Con.CString('mime_type'),
                            Con.Byte('picture_type'),
                            Con.CString('description'),
                            Con.StringAdapter(
        Con.GreedyRepeater(Con.Field('data',1))))

    #mime_type and description are unicode strings
    #apic_type is an int
    #data is a string
    def __init__(self, data, mime_type, description, apic_type):
        img = Image.new(data,u'',0)

        self.apic_type = apic_type
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description,
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
        return "APICImage(mime_type=%s,width=%s,height=%s,description=%s,type=%s,apic_type=%s,color_depth=%s,color_count=%s,...)" % \
               (repr(self.mime_type),repr(self.width),repr(self.height),
                repr(self.description),
                repr(self.type),repr(self.apic_type),
                repr(self.color_depth),repr(self.color_count))

    @classmethod
    def converted(cls, image):
        return APICImage(data=image.data,
                         mime_type=image.mime_type,
                         description=image.description,
                         apic_type={0:3,1:4,2:5,3:6}.get(image.type,0))

    def build(self):
        try:
            description = self.description.encode('ascii')
            text_encoding = 0
        except UnicodeEncodeError:
            description = self.description.encode('utf-8')
            text_encoding = 3

        return self.APIC_FRAME.build(
            Con.Container(text_encoding=text_encoding,
                          mime_type=self.mime_type.encode('ascii','replace'),
                          picture_type=self.apic_type,
                          description=description,
                          data=self.data))

class PICImage(Image):
    PIC_FRAME = Con.Struct('pic_frame',
                           Con.Byte('text_encoding'),
                           Con.String('format',3),
                           Con.Byte('picture_type'),
                           Con.CString('description'),
                           Con.StringAdapter(
        Con.GreedyRepeater(Con.Field('data',1))))

    #format and description are unicode strings
    #pic_type is an int
    #data is a string
    def __init__(self, data, format, description, pic_type):
        img = Image.new(data,u'',0)

        self.pic_type = pic_type
        self.format = format
        Image.__init__(self,
                       data=data,
                       mime_type=Image.new(data,u'',0).mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description.decode('ascii','replace'),
                       type={3:0,4:1,5:2,6:3}.get(pic_type,4))

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
                20:"Publisher/Studio logotype"}.get(self.pic_type,"Other")

    def __repr__(self):
        return "PICImage(format=%s,description=%s,pic_type=%s,...)" % \
               (repr(self.format),repr(self.description),
                repr(self.pic_type))

    @classmethod
    def converted(cls, image):
        return PICImage(data=image.data,
                        format={u"image/png":u"PNG",
                                u"image/jpeg":u"JPG",
                                u"image/jpg":u"JPG",
                                u"image/x-ms-bmp":u"BMP",
                                u"image/gif":u"GIF",
                                u"image/tiff":u"TIF"}.get(image.mime_type,
                                                          u"JPG"),
                        description=image.description,
                        pic_type={0:3,4:1,2:5,3:6}.get(image.type,0))

    def build(self):
        try:
            description = self.description.encode('ascii')
            text_encoding = 0
        except UnicodeEncodeError:
            description = self.description.encode('utf-16')
            text_encoding = 1

        return self.PIC_FRAME.build(
            Con.Container(text_encoding=text_encoding,
                          format=self.format.encode('ascii'),
                          picture_type=self.pic_type,
                          description=description,
                          data=self.data))


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
            if (key not in ('track_number','album_number')):
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
                                self[4],
                                self.track_number)


class ID3CommentPair(MetaData):
    #id3v2 and id3v1 are ID3v2Comment and ID3v1Comment objects or None
    #values in ID3v2 take precendence over ID3v1, if present
    def __init__(self, id3v2_comment, id3v1_comment):
        self.__dict__['id3v2'] = id3v2_comment
        self.__dict__['id3v1'] = id3v1_comment

        if (self.id3v2 is not None):
            base_comment = self.id3v2
        elif (self.id3v1 is not None):
            base_comment = self.id3v1
        else:
            raise ValueError("id3v2 and id3v1 cannot both be blank")

        fields = dict([(field,getattr(base_comment,field))
                       for field in self.__FIELDS__])

        MetaData.__init__(self,**fields)

    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (self.id3v2 is not None):
            setattr(self.id3v2,key,value)
        if (self.id3v1 is not None):
            setattr(self.id3v1,key,value)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata,ID3CommentPair))):
            return metadata

        if (isinstance(metadata,ID3v2Comment)):
            return ID3CommentPair(metadata,
                                  ID3v1Comment.converted(metadata))
        else:
            return ID3CommentPair(
                ID3v2_3Comment.converted(metadata),
                ID3v1Comment.converted(metadata))


    def __unicode__(self):
        if ((self.id3v2 != None) and (self.id3v1 != None)):
            #both comments present
            return unicode(self.id3v2) + \
                   (os.linesep * 2) + \
                   unicode(self.id3v1)
        elif (self.id3v2 is not None):
            #only ID3v2
            return unicode(self.id3v2)
        elif (self.id3v1 is not None):
            #only ID3v1
            return unicode(self.id3v1)
        else:
            return u''

    #ImageMetaData passthroughs
    def images(self):
        if (self.id3v2 is not None):
            return self.id3v2.images()
        else:
            return []

    def add_image(self, image):
        if (self.id3v2 is not None):
            self.id3v2.add_image(image)

    def delete_image(self, image):
        if (self.id3v2 is not None):
            self.id3v2.delete_image(image)

    @classmethod
    def supports_images(cls):
        return True
