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

from audiotools import MetaData,Con,re,os,cStringIO,Image,InvalidImage

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

class __24Bits__(Con.Adapter):
    def _encode(self, value, context):
        return chr((value & 0xFF0000) >> 16) + \
               chr((value & 0x00FF00) >> 8) + \
               chr(value & 0x0000FF)

    def _decode(self, obj, context):
        return (ord(obj[0]) << 16) | (ord(obj[1]) << 8) | ord(obj[2])

def UBInt24(name):
    return __24Bits__(Con.Bytes(name,3))

#UTF16CString and UTF16BECString implement a null-terminated string
#of UTF-16 characters by reading them as unsigned 16-bit integers,
#looking for the null terminator (0x0000) and then converting the integers
#back before decoding.  It's a little half-assed, but it seems to work.
#Even large UTF-16 characters with surrogate pairs (those above U+FFFF)
#shouldn't have embedded 0x0000 bytes in them,
#which ID3v2.2/2.3 aren't supposed to use anyway since they're limited
#to UCS-2 encoding.

class WidecharCStringAdapter(Con.Adapter):
    def __init__(self,obj,encoding):
        Con.Adapter.__init__(self,obj)
        self.encoding = encoding

    def _encode(self,obj,context):
        return Con.GreedyRepeater(Con.UBInt16("s")).parse(obj.encode(
                self.encoding)) + [0]

    def _decode(self,obj,context):
        c = Con.UBInt16("s")

        return "".join([c.build(s) for s in obj[0:-1]]).decode(self.encoding)

def UTF16CString(name):
    return WidecharCStringAdapter(Con.RepeatUntil(lambda obj, ctx: obj == 0x0,
                                                  Con.UBInt16(name)),
                                  encoding='utf-16')



def UTF16BECString(name):
    return WidecharCStringAdapter(Con.RepeatUntil(lambda obj, ctx: obj == 0x0,
                                                  Con.UBInt16(name)),
                                  encoding='utf-16be')

#######################
#ID3v2.2
#######################

class ID3v22Frame:
    FRAME = Con.Struct("id3v22_frame",
                       Con.Bytes("frame_id",3),
                       Con.PascalString("data",length_field=UBInt24("size")))
    #we use TEXT_TYPE to differentiate frames which are
    #supposed to return text unicode when __unicode__ is called
    #from those that just return summary data
    TEXT_TYPE = False

    def __init__(self,frame_id,data):
        self.id = frame_id
        self.data = data

    def build(self):
        return self.FRAME.build(Con.Container(frame_id=self.id,
                                              data=self.data))

    def __unicode__(self):
        if (len(self.data) <= 20):
            return unicode(self.data.encode('hex').upper())
        else:
            return unicode(self.data[0:19].encode('hex').upper()) + u"\u2026"

    @classmethod
    def parse(cls,container):
        if (container.frame_id.startswith('T')):
            encoding_byte = ord(container.data[0])
            return ID3v22TextFrame(container.frame_id,
                                   encoding_byte,
                                   container.data[1:].decode(
                    ID3v22TextFrame.ENCODING[encoding_byte]))
        elif (container.frame_id == 'PIC'):
            frame_data = cStringIO.StringIO(container.data)
            pic_header = ID3v22PicFrame.FRAME_HEADER.parse_stream(frame_data)
            return ID3v22PicFrame(
                frame_data.read(),
                pic_header.format.decode('ascii','replace'),
                pic_header.description,
                pic_header.picture_type)
        elif (container.frame_id == 'COM'):
            com_data = cStringIO.StringIO(container.data)
            try:
                com = ID3v22ComFrame.COMMENT_HEADER.parse_stream(com_data)
                return ID3v22ComFrame(
                    com.encoding,
                    com.language,
                    com.short_description,
                    com_data.read().decode(
                        ID3v22TextFrame.ENCODING[com.encoding],'replace'))
            except Con.core.ArrayError:
                return cls(frame_id=container.frame_id,data=container.data)
            except Con.core.FieldError:
                return cls(frame_id=container.frame_id,data=container.data)
        else:
            return cls(frame_id=container.frame_id,
                       data=container.data)

class ID3v22TextFrame(ID3v22Frame):
    ENCODING = {0x00:"latin-1",
                0x01:"utf-16"}

    TEXT_TYPE = True

    #encoding is an encoding byte
    #s is a unicode string
    def __init__(self,frame_id,encoding,s):
        self.id = frame_id
        self.encoding = encoding
        self.string = s

    def __unicode__(self):
        return self.string

    def __int__(self):
        try:
            return int(re.findall(r'\d+',self.string)[0])
        except IndexError:
            return 0

    @classmethod
    def from_unicode(cls,frame_id,s):
        if (frame_id == 'COM'):
            return ID3v22ComFrame.from_unicode(s)

        for encoding in 0x00,0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(frame_id,encoding,s)
            except UnicodeEncodeError:
                continue

    def build(self):
        return self.FRAME.build(Con.Container(
                frame_id=self.id,
                data=chr(self.encoding) + \
                    self.string.encode(self.ENCODING[self.encoding],
                                       'replace')))

class ID3v22ComFrame(ID3v22TextFrame):
    COMMENT_HEADER = Con.Struct(
        "com_frame",
        Con.Byte("encoding"),
        Con.String("language",3),
        Con.Switch("short_description",
                   lambda ctx: ctx.encoding,
                   {0x00: Con.CString("s",encoding='latin-1'),
                    0x01: UTF16CString("s")}))

    TEXT_TYPE = True

    #encoding should be an integer
    #language should be a standard string
    #short_description and content should be unicode strings
    def __init__(self,encoding,language,short_description,content):
        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.content = content
        self.id = 'COM'

    def __unicode__(self):
        return self.content

    def __int__(self):
        return 0

    @classmethod
    def from_unicode(cls,s):
        for encoding in 0x00,0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding,'eng',u'',s)
            except UnicodeEncodeError:
                continue

    def build(self):
        return self.FRAME.build(Con.Container(
                frame_id=self.id,
                data=self.COMMENT_HEADER.build(Con.Container(
                        encoding=self.encoding,
                        language=self.language,
                        short_description=self.short_description)) +
                  self.content.encode(self.ENCODING[self.encoding],'replace')))

class ID3v22PicFrame(ID3v22Frame,Image):
    FRAME_HEADER = Con.Struct('pic_frame',
                              Con.Byte('text_encoding'),
                              Con.String('format',3),
                              Con.Byte('picture_type'),
                              Con.Switch("description",
                                         lambda ctx: ctx.text_encoding,
                                         {0x00: Con.CString("s",
                                                            encoding='latin-1'),
                                          0x01: UTF16CString("s")}))

    #format and description are unicode strings
    #pic_type is an int
    #data is a string
    def __init__(self, data, format, description, pic_type):
        ID3v22Frame.__init__(self,'PIC',None)

        try:
            img = Image.new(data,u'',0)
        except InvalidImage:
            img = Image(data=data,mime_type=u'',
                        width=0,height=0,color_depth=0,color_count=0,
                        description=u'',type=0)

        self.pic_type = pic_type
        self.format = format
        Image.__init__(self,
                       data=data,
                       mime_type=img.mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description,
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

    def __unicode__(self):
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width,self.height,self.mime_type)

    def build(self):
        try:
            self.description.encode('latin-1')
            text_encoding = 0
        except UnicodeEncodeError:
            text_encoding = 1

        return ID3v22Frame.FRAME.build(
            Con.Container(frame_id='PIC',
                          data=self.FRAME_HEADER.build(
                    Con.Container(text_encoding=text_encoding,
                                  format=self.format.encode('ascii'),
                                  picture_type=self.pic_type,
                                  description=self.description))+ self.data))

    @classmethod
    def converted(cls, image):
        return cls(data=image.data,
                   format={u"image/png":u"PNG",
                           u"image/jpeg":u"JPG",
                           u"image/jpg":u"JPG",
                           u"image/x-ms-bmp":u"BMP",
                           u"image/gif":u"GIF",
                           u"image/tiff":u"TIF"}.get(image.mime_type,
                                                     u"JPG"),
                   description=image.description,
                   pic_type={0:3,1:4,2:5,3:6}.get(image.type,0))

class ID3v22Comment(MetaData):
    Frame = ID3v22Frame
    TextFrame = ID3v22TextFrame
    PictureFrame = ID3v22PicFrame
    CommentFrame = ID3v22ComFrame

    TAG_HEADER = Con.Struct("id3v22_header",
                            Con.Const(Con.Bytes("file_id",3),'ID3'),
                            Con.Byte("version_major"),
                            Con.Byte("version_minor"),
                            Con.Embed(Con.BitStruct("flags",
                                                    Con.Flag("unsync"),
                                                    Con.Flag("compression"),
                                                    Con.Padding(6))),
                            Syncsafe32("length"))

    ATTRIBUTE_MAP = {'track_name':'TT2',
                     'track_number':'TRK',
                     'album_name':'TAL',
                     'artist_name':'TP1',
                     'performer_name':'TP2',
                     'conductor_name':'TP3',
                     'composer_name':'TCM',
                     'media':'TMT',
                     'ISRC':'TRC',
                     'copyright':'TCR',
                     'publisher':'TPB',
                     'year':'TYE',
                     'date':'TRD',
                     'album_number':'TPA',
                     'comment':'COM'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    INTEGER_ITEMS = ('TRK','TPA')

    KEY_ORDER = ('TT2','TAL','TRK','TPA','TP1','TP2','TCM','TP3',
                 'TPB','TRC','TYE','TRD',None,'COM','PIC')

    #frames should be a list of ID3v22Frame-compatible objects
    def __init__(self,frames):
        self.frames = {}  #a frame_id->[frame list] mapping

        for frame in frames:
            self.frames.setdefault(frame.id,[]).append(frame)

        attribs = {}
        for key in self.frames.keys():
            if ((key in self.ITEM_MAP.keys()) and
                (self.frames[key][0].TEXT_TYPE)):
                if (key not in self.INTEGER_ITEMS):
                    attribs[self.ITEM_MAP[key]] = unicode(self.frames[key][0])
                else:
                    attribs[self.ITEM_MAP[key]] = int(self.frames[key][0])

        MetaData.__init__(self,**attribs)

    def __comment_name__(self):
        return u'ID3v2.2'

    def __comment_pairs__(self):
        key_order = list(self.KEY_ORDER)

        def by_weight(keyval1,keyval2):
            (key1,key2) = (keyval1[0],keyval2[0])

            if (key1 in key_order):
                order1 = key_order.index(key1)
            else:
                order1 = key_order.index(None)

            if (key2 in key_order):
                order2 = key_order.index(key2)
            else:
                order2 = key_order.index(None)

            return cmp((order1,key1),(order2,key2))

        pairs = []

        for (key,values) in sorted(self.frames.items(),by_weight):
            for value in values:
                pairs.append(('     ' + key,unicode(value)))

        return pairs

    def __unicode__(self):
        comment_pairs = self.__comment_pairs__()
        if (len(comment_pairs) > 0):
            max_key_length = max([len(pair[0]) for pair in comment_pairs])
            line_template = u"%%(key)%(length)d.%(length)ds : %%(value)s" % \
                            {"length":max_key_length}

            return unicode(os.linesep.join(
                [u"%s Comment:" % (self.__comment_name__())] + \
                [line_template % {"key":key,"value":value} for
                 (key,value) in comment_pairs]))
        else:
            return u""

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (key in self.ATTRIBUTE_MAP):
            self.frames[self.ATTRIBUTE_MAP[key]] = [
                self.TextFrame.from_unicode(self.ATTRIBUTE_MAP[key],value)]

    def add_image(self, image):
        image = self.picture_frame.converted(image)
        self.frames.setdefault('PIC',[]).append(image)

    def delete_image(self, image):
        del(self.frames['PIC'][self['PIC'].index(image)])

    def images(self):
        if ('PIC' in self.frames.keys()):
            return self.frames['PIC']
        else:
            return []

    #FIXME - lots of stuff expects ID3v2 comments to act as dicts
    #implement keys(),values(),items(),__getitem__(),__setitem__(),len()
    #such that the assumption still holds

    @classmethod
    def parse(cls, stream):
        header = cls.TAG_HEADER.parse_stream(stream)

        #read in the whole tag
        stream = cStringIO.StringIO(stream.read(header.length))

        #read in a collection of parsed Frame containers
        frames = []

        while (stream.tell() < header.length):
            try:
                container = cls.Frame.FRAME.parse_stream(stream)
            except Con.core.FieldError:
                break

            if (chr(0) in container.frame_id):
                break
            else:
                frames.append(cls.Frame.parse(container))

        return cls(frames)


    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or
            (isinstance(metadata,cls) and
             (cls.Frame is metadata.Frame))):
            return metadata

        frames = []

        for (key,field) in cls.ITEM_MAP.items():
            value = getattr(metadata,field)
            if (key not in cls.INTEGER_ITEMS):
                if (len(value.strip()) > 0):
                    frames.append(cls.TextFrame.from_unicode(key,value))
            else:
                if (value != 0):
                    frames.append(cls.TextFrame.from_unicode(key,unicode(value)))

        for image in metadata.images():
            frames.append(cls.PictureFrame.converted(image))

        return cls(frames)

    def build(self):
        subframes = "".join(["".join([value.build() for value in values])
                             for values in self.frames.values()])

        return self.TAG_HEADER.build(
            Con.Container(file_id='ID3',
                          version_major=0x02,
                          version_minor=0x00,
                          unsync=False,
                          compression=False,
                          length=len(subframes))) + subframes

    #takes a file stream
    #checks that stream for an ID3v2 comment
    #if found, repositions the stream past it
    #if not, leaves the stream in the current location
    @classmethod
    def skip(cls, file):
        if (file.read(3) == 'ID3'):
            file.seek(0,0)
            #parse the header
            h = cls.TAG_HEADER.parse_stream(file)
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

    #takes a filename
    #returns an ID3v2Comment-based object
    @classmethod
    def read_id3v2_comment(cls, filename):
        import cStringIO

        f = file(filename,"rb")

        try:
             f.seek(0,0)
             try:
                 header = ID3v2Comment.TAG_HEADER.parse_stream(f)
             except Con.ConstError:
                 raise UnsupportedID3v2Version()
             if (header.version_major == 0x04):
                 comment_class = ID3v24Comment
             elif (header.version_major == 0x03):
                 comment_class = ID3v23Comment
             elif (header.version_major == 0x02):
                 comment_class = ID3v22Comment
             else:
                 raise UnsupportedID3v2Version()

             f.seek(0,0)
             return comment_class.parse(f)
        finally:
            f.close()

#######################
#ID3v2.3
#######################

class ID3v23Frame(ID3v22Frame):
    FRAME = Con.Struct("id3v23_frame",
                       Con.Bytes("frame_id",4),
                       Con.UBInt32("size"),
                       Con.Embed(Con.BitStruct("flags",
                                               Con.Flag('tag_alter'),
                                               Con.Flag('file_alter'),
                                               Con.Flag('read_only'),
                                               Con.Padding(5),
                                               Con.Flag('compression'),
                                               Con.Flag('encryption'),
                                               Con.Flag('grouping'),
                                               Con.Padding(5))),
                       Con.String("data",length=lambda ctx: ctx["size"]))

    def build(self,data=None):
        if (data is None):
            data = self.data

        return self.FRAME.build(Con.Container(frame_id=self.id,
                                              size=len(data),
                                              tag_alter=False,
                                              file_alter=False,
                                              read_only=False,
                                              compression=False,
                                              encryption=False,
                                              grouping=False,
                                              data=data))

    @classmethod
    def parse(cls,container):
        if (container.frame_id.startswith('T')):
            encoding_byte = ord(container.data[0])
            return ID3v23TextFrame(container.frame_id,
                                   encoding_byte,
                                   container.data[1:].decode(
                    ID3v23TextFrame.ENCODING[encoding_byte]))
        elif (container.frame_id == 'APIC'):
            frame_data = cStringIO.StringIO(container.data)
            pic_header = ID3v23PicFrame.FRAME_HEADER.parse_stream(frame_data)
            return ID3v23PicFrame(
                frame_data.read(),
                pic_header.mime_type,
                pic_header.description,
                pic_header.picture_type)
        elif (container.frame_id == 'COMM'):
            com_data = cStringIO.StringIO(container.data)
            try:
                com = ID3v23ComFrame.COMMENT_HEADER.parse_stream(com_data)
                return ID3v23ComFrame(
                    com.encoding,
                    com.language,
                    com.short_description,
                    com_data.read().decode(
                        ID3v23TextFrame.ENCODING[com.encoding],'replace'))
            except Con.core.ArrayError:
                return cls(frame_id=container.frame_id,data=container.data)
            except Con.core.FieldError:
                return cls(frame_id=container.frame_id,data=container.data)
        else:
            return cls(frame_id=container.frame_id,
                       data=container.data)

    def __unicode__(self):
        if (len(self.data) <= 20):
            return unicode(self.data.encode('hex').upper())
        else:
            return unicode(self.data[0:19].encode('hex').upper()) + u"\u2026"

class ID3v23TextFrame(ID3v23Frame):
    ENCODING = {0x00:"latin-1",
                0x01:"utf-16"}

    TEXT_TYPE = True

    #encoding is an encoding byte
    #s is a unicode string
    def __init__(self,frame_id,encoding,s):
        self.id = frame_id
        self.encoding = encoding
        self.string = s

    def __unicode__(self):
        return self.string

    def __int__(self):
        try:
            return int(re.findall(r'\d+',self.string)[0])
        except IndexError:
            return 0

    @classmethod
    def from_unicode(cls,frame_id,s):
        if (frame_id == 'COMM'):
            return ID3v23ComFrame.from_unicode(s)

        for encoding in 0x00,0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return ID3v23TextFrame(frame_id,encoding,s)
            except UnicodeEncodeError:
                continue

    def build(self):
        return ID3v23Frame.build(
            self,
            chr(self.encoding) + \
                self.string.encode(self.ENCODING[self.encoding],
                                   'replace'))

class ID3v23PicFrame(ID3v23Frame,Image):
    FRAME_HEADER = Con.Struct('apic_frame',
                              Con.Byte('text_encoding'),
                              Con.CString('mime_type'),
                              Con.Byte('picture_type'),
                              Con.Switch("description",
                                         lambda ctx: ctx.text_encoding,
                                         {0x00: Con.CString("s",
                                                            encoding='latin-1'),
                                          0x01: UTF16CString("s")}))

    def __init__(self, data, mime_type, description, pic_type):
        ID3v23Frame.__init__(self,'APIC',None)

        try:
            img = Image.new(data,u'',0)
        except InvalidImage:
            img = Image(data=data,mime_type=u'',
                        width=0,height=0,color_depth=0,color_count=0,
                        description=u'',type=0)

        self.pic_type = pic_type
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description,
                       type={3:0,4:1,5:2,6:3}.get(pic_type,4))

    def __unicode__(self):
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width,self.height,self.mime_type)

    def build(self):
        try:
            self.description.encode('latin-1')
            text_encoding = 0
        except UnicodeEncodeError:
            text_encoding = 1

        return ID3v23Frame.build(self,
                                 self.FRAME_HEADER.build(
                Con.Container(text_encoding=text_encoding,
                              picture_type=self.pic_type,
                              mime_type=self.mime_type,
                              description=self.description)) + self.data)

    @classmethod
    def converted(cls, image):
        return cls(data=image.data,
                   mime_type=image.mime_type,
                   description=image.description,
                   pic_type={0:3,1:4,2:5,3:6}.get(image.type,0))

class ID3v23ComFrame(ID3v23TextFrame):
    COMMENT_HEADER = ID3v22ComFrame.COMMENT_HEADER

    TEXT_TYPE = True

    def __init__(self,encoding,language,short_description,content):
        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.content = content
        self.id = 'COMM'

    def __unicode__(self):
        return self.content

    def __int__(self):
        return 0

    @classmethod
    def from_unicode(cls,s):
        for encoding in 0x00,0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding,'eng',u'',s)
            except UnicodeEncodeError:
                continue

    def build(self):
        return ID3v23Frame.build(
            self,
            self.COMMENT_HEADER.build(Con.Container(
                    encoding=self.encoding,
                    language=self.language,
                    short_description=self.short_description)) + \
                self.content.encode(self.ENCODING[self.encoding],'replace'))


class ID3v23Comment(ID3v22Comment):
    Frame = ID3v23Frame
    TextFrame = ID3v23TextFrame
    PictureFrame = ID3v23PicFrame

    TAG_HEADER = Con.Struct("id3v23_header",
                            Con.Const(Con.Bytes("file_id",3),'ID3'),
                            Con.Byte("version_major"),
                            Con.Byte("version_minor"),
                            Con.Embed(Con.BitStruct("flags",
                                                    Con.Flag("unsync"),
                                                    Con.Flag("extended"),
                                                    Con.Flag("experimental"),
                                                    Con.Flag("footer"),
                                                    Con.Padding(4))),
                            Syncsafe32("length"))

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
                     'album_number':'TPOS',
                     'comment':'COMM'}

    ITEM_MAP = dict(map(reversed,ATTRIBUTE_MAP.items()))

    INTEGER_ITEMS = ('TRCK','TPOS')

    KEY_ORDER = ('TIT2','TALB','TRCK','TPOS','TPE1','TPE2','TCOM',
                 'TPE3','TPUB','TSRC','TMED','TYER','TRDA','TCOP',
                 None,'COMM','APIC')

    def __comment_name__(self):
        return u'ID3v2.3'

    def __comment_pairs__(self):
        key_order = list(self.KEY_ORDER)

        def by_weight(keyval1,keyval2):
            (key1,key2) = (keyval1[0],keyval2[0])

            if (key1 in key_order):
                order1 = key_order.index(key1)
            else:
                order1 = key_order.index(None)

            if (key2 in key_order):
                order2 = key_order.index(key2)
            else:
                order2 = key_order.index(None)

            return cmp((order1,key1),(order2,key2))

        pairs = []

        for (key,values) in sorted(self.frames.items(),by_weight):
            for value in values:
                pairs.append(('    ' + key,unicode(value)))

        return pairs


    def add_image(self, image):
        image = self.picture_frame.converted(image)
        self.frames.setdefault('APIC',[]).append(image)

    def delete_image(self, image):
        del(self.frames['APIC'][self['APIC'].index(image)])

    def images(self):
        if ('APIC' in self.frames.keys()):
            return self.frames['APIC']
        else:
            return []

    def build(self):
        subframes = "".join(["".join([value.build() for value in values])
                             for values in self.frames.values()])

        return self.TAG_HEADER.build(
            Con.Container(file_id='ID3',
                          version_major=0x03,
                          version_minor=0x00,
                          unsync=False,
                          extended=False,
                          experimental=False,
                          footer=False,
                          length=len(subframes))) + subframes

#######################
#ID3v2.4
#######################


class ID3v24Frame(ID3v23Frame):
    FRAME = Con.Struct("id3v24_frame",
                       Con.Bytes("frame_id",4),
                       Syncsafe32("size"),
                       Con.Embed(Con.BitStruct("flags",
                                               Con.Padding(1),
                                               Con.Flag('tag_alter'),
                                               Con.Flag('file_alter'),
                                               Con.Flag('read_only'),
                                               Con.Padding(5),
                                               Con.Flag('grouping'),
                                               Con.Padding(2),
                                               Con.Flag('compression'),
                                               Con.Flag('encryption'),
                                               Con.Flag('unsync'),
                                               Con.Flag('data_length'))),
                       Con.String("data",length=lambda ctx: ctx["size"]))

    def build(self,data=None):
        if (data is None):
            data = self.data

        return self.FRAME.build(Con.Container(frame_id=self.id,
                                              size=len(data),
                                              tag_alter=False,
                                              file_alter=False,
                                              read_only=False,
                                              compression=False,
                                              encryption=False,
                                              grouping=False,
                                              unsync=False,
                                              data_length=False,
                                              data=data))

    @classmethod
    def parse(cls,container):
        if (container.frame_id.startswith('T')):
            encoding_byte = ord(container.data[0])
            return ID3v24TextFrame(container.frame_id,
                                   encoding_byte,
                                   container.data[1:].decode(
                    ID3v24TextFrame.ENCODING[encoding_byte]))
        elif (container.frame_id == 'APIC'):
            frame_data = cStringIO.StringIO(container.data)
            pic_header = ID3v24PicFrame.FRAME_HEADER.parse_stream(frame_data)
            return ID3v24PicFrame(
                frame_data.read(),
                pic_header.mime_type,
                pic_header.description,
                pic_header.picture_type)
        elif (container.frame_id == 'COMM'):
            com_data = cStringIO.StringIO(container.data)
            try:
                com = ID3v24ComFrame.COMMENT_HEADER.parse_stream(com_data)
                return ID3v24ComFrame(
                    com.encoding,
                    com.language,
                    com.short_description,
                    com_data.read().decode(
                        ID3v24TextFrame.ENCODING[com.encoding],'replace'))
            except Con.core.ArrayError:
                return cls(frame_id=container.frame_id,data=container.data)
            except Con.core.FieldError:
                return cls(frame_id=container.frame_id,data=container.data)
        else:
            return cls(frame_id=container.frame_id,
                       data=container.data)

    def __unicode__(self):
        if (len(self.data) <= 20):
            return unicode(self.data.encode('hex').upper())
        else:
            return unicode(self.data[0:19].encode('hex').upper()) + u"\u2026"


class ID3v24TextFrame(ID3v24Frame):
    ENCODING = {0x00:"latin-1",
                0x01:"utf-16",
                0x02:"utf-16be",
                0x03:"utf-8"}

    TEXT_TYPE = True

    #encoding is an encoding byte
    #s is a unicode string
    def __init__(self,frame_id,encoding,s):
        self.id = frame_id
        self.encoding = encoding
        self.string = s

    def __unicode__(self):
        return self.string

    def __int__(self):
        try:
            return int(re.findall(r'\d+',self.string)[0])
        except IndexError:
            return 0

    @classmethod
    def from_unicode(cls,frame_id,s):
        if (frame_id == 'COMM'):
            return ID3v24ComFrame.from_unicode(s)

        for encoding in 0x00,0x03,0x01,0x02:
            try:
                s.encode(cls.ENCODING[encoding])
                return ID3v24TextFrame(frame_id,encoding,s)
            except UnicodeEncodeError:
                continue

    def build(self):
        return ID3v24Frame.build(
            self,
            chr(self.encoding) + \
                self.string.encode(self.ENCODING[self.encoding],
                                   'replace'))


class ID3v24PicFrame(ID3v24Frame,Image):
    FRAME_HEADER = Con.Struct('apic_frame',
                              Con.Byte('text_encoding'),
                              Con.CString('mime_type'),
                              Con.Byte('picture_type'),
                              Con.Switch("description",
                                         lambda ctx: ctx.text_encoding,
                                         {0x00: Con.CString("s",
                                                            encoding='latin-1'),
                                          0x01: UTF16CString("s"),
                                          0x02: UTF16BECString("s"),
                                          0x03: Con.CString("s",
                                                            encoding='utf-8')}))


    def __init__(self, data, mime_type, description, pic_type):
        ID3v24Frame.__init__(self,'APIC',None)

        try:
            img = Image.new(data,u'',0)
        except InvalidImage:
            img = Image(data=data,mime_type=u'',
                        width=0,height=0,color_depth=0,color_count=0,
                        description=u'',type=0)

        self.pic_type = pic_type
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description,
                       type={3:0,4:1,5:2,6:3}.get(pic_type,4))

    def __unicode__(self):
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width,self.height,self.mime_type)

    def build(self):
        try:
            self.description.encode('latin-1')
            text_encoding = 0
        except UnicodeEncodeError:
            text_encoding = 1

        return ID3v24Frame.build(self,
                                 self.FRAME_HEADER.build(
                Con.Container(text_encoding=text_encoding,
                              picture_type=self.pic_type,
                              mime_type=self.mime_type,
                              description=self.description)) + self.data)

    @classmethod
    def converted(cls, image):
        return cls(data=image.data,
                   mime_type=image.mime_type,
                   description=image.description,
                   pic_type={0:3,1:4,2:5,3:6}.get(image.type,0))


class ID3v24ComFrame(ID3v24TextFrame):
    COMMENT_HEADER = Con.Struct(
        "com_frame",
        Con.Byte("encoding"),
        Con.String("language",3),
        Con.Switch("short_description",
                   lambda ctx: ctx.encoding,
                   {0x00: Con.CString("s",encoding='latin-1'),
                    0x01: UTF16CString("s"),
                    0x02: UTF16BECString("s"),
                    0x03: Con.CString("s",encoding='utf-8')}))

    TEXT_TYPE = True


    def __init__(self,encoding,language,short_description,content):
        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.content = content
        self.id = 'COMM'

    def __unicode__(self):
        return self.content

    def __int__(self):
        return 0

    @classmethod
    def from_unicode(cls,s):
        for encoding in 0x00,0x03,0x01,0x02:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding,'eng',u'',s)
            except UnicodeEncodeError:
                continue

    def build(self):
        return ID3v24Frame.build(
            self,
            self.COMMENT_HEADER.build(Con.Container(
                    encoding=self.encoding,
                    language=self.language,
                    short_description=self.short_description)) + \
                self.content.encode(self.ENCODING[self.encoding],'replace'))


class ID3v24Comment(ID3v23Comment):
    Frame = ID3v24Frame
    TextFrame = ID3v24TextFrame
    PictureFrame = ID3v24PicFrame

    def __comment_name__(self):
        return u'ID3v2.4'

    def build(self):
        subframes = "".join(["".join([value.build() for value in values])
                             for values in self.frames.values()])

        return self.TAG_HEADER.build(
            Con.Container(file_id='ID3',
                          version_major=0x04,
                          version_minor=0x00,
                          unsync=False,
                          extended=False,
                          experimental=False,
                          footer=False,
                          length=len(subframes))) + subframes

ID3v2Comment = ID3v22Comment

from __id3v1__ import *

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
                ID3v23Comment.converted(metadata),
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
