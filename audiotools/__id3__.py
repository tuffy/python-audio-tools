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

from audiotools import (MetaData, Con, re, os, cStringIO,
                        Image, InvalidImage, config)
import codecs
import gettext

gettext.install("audiotools", unicode=True)


class UCS2Codec(codecs.Codec):
    """A special unicode codec for UCS-2.

    This is a subset of UTF-16 with no support for surrogate pairs,
    limiting it to U+0000-U+FFFF."""

    @classmethod
    def fix_char(cls, c):
        """A filter which changes overly large c values to "unknown"."""

        if (ord(c) <= 0xFFFF):
            return c
        else:
            return u"\ufffd"

    def encode(self, input, errors='strict'):
        """Encodes unicode input to plain UCS-2 strings."""

        return codecs.utf_16_encode(u"".join(map(self.fix_char, input)),
                                    errors)

    def decode(self, input, errors='strict'):
        """Decodes plain UCS-2 strings to unicode."""

        (chars, size) = codecs.utf_16_decode(input, errors, True)
        return (u"".join(map(self.fix_char, chars)), size)


class UCS2CodecStreamWriter(UCS2Codec, codecs.StreamWriter):
    pass


class UCS2CodecStreamReader(UCS2Codec, codecs.StreamReader):
    pass


def __reg_ucs2__(name):
    if (name == 'ucs2'):
        return (UCS2Codec().encode,
                UCS2Codec().decode,
                UCS2CodecStreamReader,
                UCS2CodecStreamWriter)
    else:
        return None

codecs.register(__reg_ucs2__)


class UnsupportedID3v2Version(Exception):
    """Raised if one encounters an ID3v2 tag not version .2, .3 or .4."""

    pass


class Syncsafe32(Con.Adapter):
    """An adapter for padding 24 bit values to 32 bits."""

    def __init__(self, name):
        Con.Adapter.__init__(self,
                             Con.StrictRepeater(4, Con.UBInt8(name)))

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


class __24BitsBE__(Con.Adapter):
    def _encode(self, value, context):
        return chr((value & 0xFF0000) >> 16) + \
               chr((value & 0x00FF00) >> 8) + \
               chr(value & 0x0000FF)

    def _decode(self, obj, context):
        return (ord(obj[0]) << 16) | (ord(obj[1]) << 8) | ord(obj[2])


def UBInt24(name):
    """An unsigned, big-endian, 24-bit struct."""

    return __24BitsBE__(Con.Bytes(name, 3))


#UTF16CString and UTF16BECString implement a null-terminated string
#of UTF-16 characters by reading them as unsigned 16-bit integers,
#looking for the null terminator (0x0000) and then converting the integers
#back before decoding.  It's a little half-assed, but it seems to work.
#Even large UTF-16 characters with surrogate pairs (those above U+FFFF)
#shouldn't have embedded 0x0000 bytes in them,
#which ID3v2.2/2.3 aren't supposed to use anyway since they're limited
#to UCS-2 encoding.

class WidecharCStringAdapter(Con.Adapter):
    """An adapter for handling NULL-terminated UTF-16/UCS-2 strings."""

    def __init__(self, obj, encoding):
        Con.Adapter.__init__(self, obj)
        self.encoding = encoding

    def _encode(self, obj, context):
        return Con.GreedyRepeater(Con.UBInt16("s")).parse(obj.encode(
                self.encoding)) + [0]

    def _decode(self, obj, context):
        c = Con.UBInt16("s")

        return "".join([c.build(s) for s in obj[0:-1]]).decode(self.encoding)


def UCS2CString(name):
    """A UCS-2 encoded, NULL-terminated string."""

    return WidecharCStringAdapter(Con.RepeatUntil(lambda obj, ctx: obj == 0x0,
                                                  Con.UBInt16(name)),
                                  encoding='ucs2')


def UTF16CString(name):
    """A UTF-16 encoded, NULL-terminated string."""

    return WidecharCStringAdapter(Con.RepeatUntil(lambda obj, ctx: obj == 0x0,
                                                  Con.UBInt16(name)),
                                  encoding='utf-16')


def UTF16BECString(name):
    """A UTF-16BE encoded, NULL-terminated string."""

    return WidecharCStringAdapter(Con.RepeatUntil(lambda obj, ctx: obj == 0x0,
                                                  Con.UBInt16(name)),
                                  encoding='utf-16be')


def __attrib_equals__(attributes, o1, o2):
    import operator

    try:
        return reduce(operator.and_,
                      [getattr(o1, attrib) == getattr(o2, attrib)
                       for attrib in attributes])
    except AttributeError:
        return False


#takes a pair of integers for the current and total values
#returns a unicode string of their combined pair
#for example, __number_pair__(2,3) returns u"2/3"
#whereas      __number_pair__(4,0) returns u"4"

def __padded_number_pair__(current, total):
    if (total == 0):
        return u"%2.2d" % (current)
    else:
        return u"%2.2d/%2.2d" % (current, total)

def __unpadded_number_pair__(current, total):
    if (total == 0):
        return u"%d" % (current)
    else:
        return u"%d/%d" % (current, total)

if (config.getboolean_default("ID3", "pad", False)):
    __number_pair__ = __padded_number_pair__
else:
    __number_pair__ = __unpadded_number_pair__


#######################
#ID3v2.2
#######################


class ID3v22Frame:
    """A container for individual ID3v2.2 frames."""

    FRAME = Con.Struct("id3v22_frame",
                       Con.Bytes("frame_id", 3),
                       Con.PascalString("data", length_field=UBInt24("size")))
    #we use TEXT_TYPE to differentiate frames which are
    #supposed to return text unicode when __unicode__ is called
    #from those that just return summary data
    TEXT_TYPE = False

    def __init__(self, frame_id, data):
        """frame_id is the 3 byte ID.  data is a binary string."""

        self.id = frame_id
        self.data = data

    def __len__(self):
        return len(self.data)

    def __eq__(self, o):
        return __attrib_equals__(["frame_id", "data"], self, o)

    def build(self):
        """Returns a binary string of ID3v2.2 frame data."""

        return self.FRAME.build(Con.Container(frame_id=self.id,
                                              data=self.data))

    def __unicode__(self):
        if (self.id.startswith('W')):
            return self.data.rstrip(chr(0)).decode('iso-8859-1', 'replace')
        else:
            if (len(self.data) <= 20):
                return unicode(self.data.encode('hex').upper())
            else:
                return (unicode(self.data[0:19].encode('hex').upper()) +
                        u"\u2026")

    @classmethod
    def parse(cls, container):
        """Returns the appropriate ID3v22Frame subclass from a Container.

        Container is parsed from ID3v22Frame.FRAME
        and contains "frame_id and "data" attributes.
        """

        if (container.frame_id.startswith('T')):
            try:
                encoding_byte = ord(container.data[0])
                return ID3v22TextFrame(container.frame_id,
                                       encoding_byte,
                                       container.data[1:].decode(
                        ID3v22TextFrame.ENCODING[encoding_byte]))
            except IndexError:
                return ID3v22TextFrame(container.frame_id,
                                       0,
                                       u"")
        elif (container.frame_id == 'PIC'):
            frame_data = cStringIO.StringIO(container.data)
            pic_header = ID3v22PicFrame.FRAME_HEADER.parse_stream(frame_data)
            return ID3v22PicFrame(
                frame_data.read(),
                pic_header.format.decode('ascii', 'replace'),
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
                        ID3v22TextFrame.ENCODING[com.encoding], 'replace'))
            except Con.core.ArrayError:
                return cls(frame_id=container.frame_id, data=container.data)
            except Con.core.FieldError:
                return cls(frame_id=container.frame_id, data=container.data)
        else:
            return cls(frame_id=container.frame_id,
                       data=container.data)


class ID3v22TextFrame(ID3v22Frame):
    """A container for individual ID3v2.2 text frames."""

    ENCODING = {0x00: "latin-1",
                0x01: "ucs2"}

    TEXT_TYPE = True

    def __init__(self, frame_id, encoding, s):
        """frame_id is a 3 byte ID, encoding is 0/1, s is a unicode string."""

        self.id = frame_id
        self.encoding = encoding
        self.string = s

    def __eq__(self, o):
        return __attrib_equals__(["id", "encoding", "string"], self, o)

    def __len__(self):
        return len(self.string)

    def __unicode__(self):
        return self.string

    def __int__(self):
        try:
            return int(re.findall(r'\d+', self.string)[0])
        except IndexError:
            return 0

    def total(self):
        """If the frame is number/total formatted, return the "total" int."""

        try:
            return int(re.findall(r'\d+/(\d+)', self.string)[0])
        except IndexError:
            return 0

    @classmethod
    def from_unicode(cls, frame_id, s):
        """Builds an ID3v22TextFrame from 3 byte frame_id and unicode s."""

        if (frame_id == 'COM'):
            return ID3v22ComFrame.from_unicode(s)

        for encoding in 0x00, 0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(frame_id, encoding, s)
            except UnicodeEncodeError:
                continue

    def build(self):
        """Returns a binary string of ID3v2.2 frame data."""

        return self.FRAME.build(Con.Container(
                frame_id=self.id,
                data=chr(self.encoding) + \
                    self.string.encode(self.ENCODING[self.encoding],
                                       'replace')))


class ID3v22ComFrame(ID3v22TextFrame):
    """A container for ID3v2.2 comment (COM) frames."""

    COMMENT_HEADER = Con.Struct(
        "com_frame",
        Con.Byte("encoding"),
        Con.String("language", 3),
        Con.Switch("short_description",
                   lambda ctx: ctx.encoding,
                   {0x00: Con.CString("s", encoding='latin-1'),
                    0x01: UCS2CString("s")}))

    TEXT_TYPE = True

    def __init__(self, encoding, language, short_description, content):
        """encoding is 0/1, language is a string, the rest are unicode.

        We're mostly interested in encoding and content.
        The language and short_description fields are rarely used."""

        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.content = content
        self.id = 'COM'

    def __len__(self):
        return len(self.content)

    def __eq__(self, o):
        return __attrib_equals__(["encoding", "language",
                                  "short_description", "content"], self, o)

    def __unicode__(self):
        return self.content

    def __int__(self):
        return 0

    @classmethod
    def from_unicode(cls, s):
        """Builds an ID3v22ComFrame from a unicode string."""

        for encoding in 0x00, 0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding, 'eng', u'', s)
            except UnicodeEncodeError:
                continue

    def build(self):
        """Returns a binary string of ID3v2.2 frame data."""

        return self.FRAME.build(Con.Container(
                frame_id=self.id,
                data=self.COMMENT_HEADER.build(Con.Container(
                        encoding=self.encoding,
                        language=self.language,
                        short_description=self.short_description)) +
                  self.content.encode(self.ENCODING[self.encoding],
                                      'replace')))


class ID3v22PicFrame(ID3v22Frame, Image):
    """A container for ID3v2.2 image (PIC) frames."""

    FRAME_HEADER = Con.Struct('pic_frame',
                              Con.Byte('text_encoding'),
                              Con.String('format', 3),
                              Con.Byte('picture_type'),
                              Con.Switch("description",
                                         lambda ctx: ctx.text_encoding,
                                         {0x00: Con.CString(
                    "s",  encoding='latin-1'),
                                          0x01: UCS2CString("s")}))

    def __init__(self, data, format, description, pic_type):
        """Fields are as follows:

        data        - a binary string of raw image data
        format      - a unicode string
        description - a unicode string
        pic_type    - an integer
        """

        ID3v22Frame.__init__(self, 'PIC', None)

        try:
            img = Image.new(data, u'', 0)
        except InvalidImage:
            img = Image(data=data, mime_type=u'',
                        width=0, height=0, color_depth=0, color_count=0,
                        description=u'', type=0)

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
                       type={3: 0, 4: 1, 5: 2, 6: 3}.get(pic_type, 4))

    def type_string(self):
        """Returns the image's type as a human readable plain string.

        For example, an image of type 0 returns "Front Cover"""

        #FIXME - these should be internationalized
        return {0: "Other",
                1: "32x32 pixels 'file icon' (PNG only)",
                2: "Other file icon",
                3: "Cover (front)",
                4: "Cover (back)",
                5: "Leaflet page",
                6: "Media (e.g. label side of CD)",
                7: "Lead artist/lead performer/soloist",
                8: "Artist / Performer",
                9: "Conductor",
                10: "Band / Orchestra",
                11: "Composer",
                12: "Lyricist / Text writer",
                13: "Recording Location",
                14: "During recording",
                15: "During performance",
                16: "Movie/Video screen capture",
                17: "A bright coloured fish",
                18: "Illustration",
                19: "Band/Artist logotype",
                20: "Publisher/Studio logotype"}.get(self.pic_type, "Other")

    def __unicode__(self):
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width, self.height, self.mime_type)

    def __eq__(self, i):
        return Image.__eq__(self, i)

    def build(self):
        """Returns a binary string of ID3v2.2 frame data."""

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
                                  description=self.description)) + self.data))

    @classmethod
    def converted(cls, image):
        """Given an Image object, returns an ID3v22PicFrame object."""

        return cls(data=image.data,
                   format={u"image/png": u"PNG",
                           u"image/jpeg": u"JPG",
                           u"image/jpg": u"JPG",
                           u"image/x-ms-bmp": u"BMP",
                           u"image/gif": u"GIF",
                           u"image/tiff": u"TIF"}.get(image.mime_type,
                                                     u"JPG"),
                   description=image.description,
                   pic_type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0))


class ID3v22Comment(MetaData):
    """A complete ID3v2.2 comment."""

    Frame = ID3v22Frame
    TextFrame = ID3v22TextFrame
    PictureFrame = ID3v22PicFrame
    CommentFrame = ID3v22ComFrame

    TAG_HEADER = Con.Struct("id3v22_header",
                            Con.Const(Con.Bytes("file_id", 3), 'ID3'),
                            Con.Byte("version_major"),
                            Con.Byte("version_minor"),
                            Con.Embed(Con.BitStruct("flags",
                                                    Con.Flag("unsync"),
                                                    Con.Flag("compression"),
                                                    Con.Padding(6))),
                            Syncsafe32("length"))

    ATTRIBUTE_MAP = {'track_name': 'TT2',
                     'track_number': 'TRK',
                     'track_total': 'TRK',
                     'album_name': 'TAL',
                     'artist_name': 'TP1',
                     'performer_name': 'TP2',
                     'conductor_name': 'TP3',
                     'composer_name': 'TCM',
                     'media': 'TMT',
                     'ISRC': 'TRC',
                     'copyright': 'TCR',
                     'publisher': 'TPB',
                     'year': 'TYE',
                     'date': 'TRD',
                     'album_number': 'TPA',
                     'album_total': 'TPA',
                     'comment': 'COM'}

    INTEGER_ITEMS = ('TRK', 'TPA')

    KEY_ORDER = ('TT2', 'TAL', 'TRK', 'TPA', 'TP1', 'TP2', 'TCM', 'TP3',
                 'TPB', 'TRC', 'TYE', 'TRD', None, 'COM', 'PIC')

    def __init__(self, frames):
        """frame should be a list of ID3v2?Frame-compatible objects."""

        self.__dict__["frames"] = {}  # a frame_id->[frame list] mapping

        for frame in frames:
            self.__dict__["frames"].setdefault(frame.id, []).append(frame)

    def __repr__(self):
        return "ID3v22Comment(%s)" % (repr(self.__dict__["frames"]))

    def __comment_name__(self):
        return u'ID3v2.2'

    def __comment_pairs__(self):
        key_order = list(self.KEY_ORDER)

        def by_weight(keyval1, keyval2):
            (key1, key2) = (keyval1[0], keyval2[0])

            if (key1 in key_order):
                order1 = key_order.index(key1)
            else:
                order1 = key_order.index(None)

            if (key2 in key_order):
                order2 = key_order.index(key2)
            else:
                order2 = key_order.index(None)

            return cmp((order1, key1), (order2, key2))

        pairs = []

        for (key, values) in sorted(self.frames.items(), by_weight):
            for value in values:
                pairs.append(('     ' + key, unicode(value)))

        return pairs

    def __unicode__(self):
        comment_pairs = self.__comment_pairs__()
        if (len(comment_pairs) > 0):
            max_key_length = max([len(pair[0]) for pair in comment_pairs])
            line_template = u"%%(key)%(length)d.%(length)ds : %%(value)s" % \
                            {"length": max_key_length}

            return unicode(os.linesep.join(
                [u"%s Comment:" % (self.__comment_name__())] + \
                [line_template % {"key": key, "value": value} for
                 (key, value) in comment_pairs]))
        else:
            return u""

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        if (key in self.ATTRIBUTE_MAP):
            if (key == 'track_number'):
                value = __number_pair__(value, self.track_total)
            elif (key == 'track_total'):
                value = __number_pair__(self.track_number, value)
            elif (key == 'album_number'):
                value = __number_pair__(value, self.album_total)
            elif (key == 'album_total'):
                value = __number_pair__(self.album_number, value)

            self.frames[self.ATTRIBUTE_MAP[key]] = [
                self.TextFrame.from_unicode(self.ATTRIBUTE_MAP[key],
                                            unicode(value))]
        elif (key in MetaData.__FIELDS__):
            pass
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):
        if (key in self.ATTRIBUTE_MAP):
            try:
                frame = self.frames[self.ATTRIBUTE_MAP[key]][0]
                if (key in ('track_number', 'album_number')):
                    return int(frame)
                elif (key in ('track_total', 'album_total')):
                    return frame.total()
                else:
                    return unicode(frame)
            except KeyError:
                if (key in MetaData.__INTEGER_FIELDS__):
                    return 0
                else:
                    return u""
        elif (key in MetaData.__FIELDS__):
            return u""
        else:
            raise AttributeError(key)

    def __delattr__(self, key):
        if (key in self.ATTRIBUTE_MAP):
            if (key == 'track_number'):
                setattr(self, 'track_number', 0)
                if ((self.track_number == 0) and (self.track_total == 0)):
                    del(self.frames[self.ATTRIBUTE_MAP[key]])
            elif (key == 'track_total'):
                setattr(self, 'track_total', 0)
                if ((self.track_number == 0) and (self.track_total == 0)):
                    del(self.frames[self.ATTRIBUTE_MAP[key]])
            elif (key == 'album_number'):
                setattr(self, 'album_number', 0)
                if ((self.album_number == 0) and (self.album_total == 0)):
                    del(self.frames[self.ATTRIBUTE_MAP[key]])
            elif (key == 'album_total'):
                setattr(self, 'album_total', 0)
                if ((self.album_number == 0) and (self.album_total == 0)):
                    del(self.frames[self.ATTRIBUTE_MAP[key]])
            elif (self.ATTRIBUTE_MAP[key] in self.frames):
                del(self.frames[self.ATTRIBUTE_MAP[key]])
        elif (key in MetaData.__FIELDS__):
            pass
        else:
            raise AttributeError(key)

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        image = self.PictureFrame.converted(image)
        self.frames.setdefault('PIC', []).append(image)

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        del(self.frames['PIC'][self['PIC'].index(image)])

    def images(self):
        """Returns a list of embedded Image objects."""

        if ('PIC' in self.frames.keys()):
            return self.frames['PIC'][:]
        else:
            return []

    def __getitem__(self, key):
        return self.frames[key]

    #this should always take a list of items,
    #either unicode strings (for text fields)
    #or something Frame-compatible (for everything else)
    #or possibly both in one list
    def __setitem__(self, key, values):
        frames = []
        for value in values:
            if (isinstance(value, unicode)):
                frames.append(self.TextFrame.from_unicode(key, value))
            elif (isinstance(value, int)):
                frames.append(self.TextFrame.from_unicode(key, unicode(value)))
            elif (isinstance(value, self.Frame)):
                frames.append(value)

        self.frames[key] = frames

    def __delitem__(self, key):
        del(self.frames[key])

    def len(self):
        return len(self.frames)

    def keys(self):
        return self.frames.keys()

    def values(self):
        return self.frames.values()

    def items(self):
        return self.frames.items()

    @classmethod
    def parse(cls, stream):
        """Given a file stream, returns an ID3v22Comment object."""

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
            except Con.core.ArrayError:
                break

            if (chr(0) in container.frame_id):
                break
            else:
                try:
                    frames.append(cls.Frame.parse(container))
                except UnicodeDecodeError:
                    break

        return cls(frames)

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to an ID3v22Comment object."""

        if ((metadata is None) or
            (isinstance(metadata, cls) and
             (cls.Frame is metadata.Frame))):
            return metadata

        frames = []

        for (field, key) in cls.ATTRIBUTE_MAP.items():
            value = getattr(metadata, field)
            if (key not in cls.INTEGER_ITEMS):
                if (len(value.strip()) > 0):
                    frames.append(cls.TextFrame.from_unicode(key, value))

        frames.append(cls.TextFrame.from_unicode(
                cls.INTEGER_ITEMS[0],
                __number_pair__(metadata.track_number,
                                metadata.track_total)))

        if ((metadata.album_number != 0) or
            (metadata.album_total != 0)):
            frames.append(cls.TextFrame.from_unicode(
                cls.INTEGER_ITEMS[1],
                __number_pair__(metadata.album_number,
                                metadata.album_total)))

        for image in metadata.images():
            frames.append(cls.PictureFrame.converted(image))

        if (hasattr(cls, 'ITUNES_COMPILATION')):
            frames.append(cls.TextFrame.from_unicode(
                    cls.ITUNES_COMPILATION, u'1'))

        return cls(frames)

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        metadata = self.__class__.converted(metadata)
        if (metadata is None):
            return

        for (key, values) in metadata.frames.items():
            if ((key not in self.INTEGER_ITEMS) and
                (len(values) > 0) and
                (len(values[0]) > 0) and
                (len(self.frames.get(key, [])) == 0)):
                self.frames[key] = values

        for attr in ("track_number", "track_total",
                     "album_number", "album_total"):
            if ((getattr(self, attr) == 0) and
                (getattr(metadata, attr) != 0)):
                setattr(self, attr, getattr(metadata, attr))

    def build(self):
        """Returns an ID3v2.2 comment as a binary string."""

        subframes = "".join(["".join([value.build() for value in values])
                             for values in self.frames.values()])

        return self.TAG_HEADER.build(
            Con.Container(file_id='ID3',
                          version_major=0x02,
                          version_minor=0x00,
                          unsync=False,
                          compression=False,
                          length=len(subframes))) + subframes

    @classmethod
    def skip(cls, file):
        """Seeks past an ID3v2 comment if found in the file stream.

        The stream must be seekable, obviously."""

        if (file.read(3) == 'ID3'):
            file.seek(0, 0)
            #parse the header
            h = cls.TAG_HEADER.parse_stream(file)
            #seek to the end of its length
            file.seek(h.length, 1)
            #skip any null bytes after the ID3v2 tag
            c = file.read(1)
            while (c == '\x00'):
                c = file.read(1)
            file.seek(-1, 1)
        else:
            try:
                file.seek(-3, 1)
            except IOError:
                pass

    @classmethod
    def read_id3v2_comment(cls, filename):
        """Given a filename, returns an ID3v22Comment or a subclass.

        For example, if the file is ID3v2.3 tagged,
        this returns an ID3v23Comment.
        """

        import cStringIO

        f = file(filename, "rb")

        try:
            f.seek(0, 0)
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

            f.seek(0, 0)
            return comment_class.parse(f)
        finally:
            f.close()


#######################
#ID3v2.3
#######################


class ID3v23Frame(ID3v22Frame):
    """A container for individual ID3v2.3 frames."""

    FRAME = Con.Struct("id3v23_frame",
                       Con.Bytes("frame_id", 4),
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
                       Con.String("data", length=lambda ctx: ctx["size"]))

    def build(self, data=None):
        """Returns a binary string of ID3v2.3 frame data."""

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
    def parse(cls, container):
        """Returns the appropriate ID3v23Frame subclass from a Container.

        Container is parsed from ID3v23Frame.FRAME
        and contains "frame_id and "data" attributes.
        """

        if (container.frame_id.startswith('T')):
            try:
                encoding_byte = ord(container.data[0])
                return ID3v23TextFrame(container.frame_id,
                                       encoding_byte,
                                       container.data[1:].decode(
                        ID3v23TextFrame.ENCODING[encoding_byte]))
            except IndexError:
                return ID3v23TextFrame(container.frame_id,
                                       0,
                                       u"")
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
                        ID3v23TextFrame.ENCODING[com.encoding], 'replace'))
            except Con.core.ArrayError:
                return cls(frame_id=container.frame_id, data=container.data)
            except Con.core.FieldError:
                return cls(frame_id=container.frame_id, data=container.data)
        else:
            return cls(frame_id=container.frame_id,
                       data=container.data)

    def __unicode__(self):
        if (self.id.startswith('W')):
            return self.data.rstrip(chr(0)).decode('iso-8859-1', 'replace')
        else:
            if (len(self.data) <= 20):
                return unicode(self.data.encode('hex').upper())
            else:
                return (unicode(self.data[0:19].encode('hex').upper()) +
                        u"\u2026")


class ID3v23TextFrame(ID3v23Frame):
    """A container for individual ID3v2.3 text frames."""

    ENCODING = {0x00: "latin-1",
                0x01: "ucs2"}

    TEXT_TYPE = True

    def __init__(self, frame_id, encoding, s):
        """frame_id is a 4 byte ID, encoding is 0/1, s is a unicode string."""

        self.id = frame_id
        self.encoding = encoding
        self.string = s

    def __len__(self):
        return len(self.string)

    def __eq__(self, o):
        return __attrib_equals__(["id", "encoding", "string"], self, o)

    def __unicode__(self):
        return self.string

    def __int__(self):
        try:
            return int(re.findall(r'\d+', self.string)[0])
        except IndexError:
            return 0

    def total(self):
        """If the frame is number/total formatted, return the "total" int."""

        try:
            return int(re.findall(r'\d+/(\d+)', self.string)[0])
        except IndexError:
            return 0

    @classmethod
    def from_unicode(cls, frame_id, s):
        """Builds an ID3v23TextFrame from 4 byte frame_id and unicode s."""

        if (frame_id == 'COMM'):
            return ID3v23ComFrame.from_unicode(s)

        for encoding in 0x00, 0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return ID3v23TextFrame(frame_id, encoding, s)
            except UnicodeEncodeError:
                continue

    def build(self):
        """Returns a binary string of ID3v2.3 frame data."""

        return ID3v23Frame.build(
            self,
            chr(self.encoding) + \
                self.string.encode(self.ENCODING[self.encoding],
                                   'replace'))


class ID3v23PicFrame(ID3v23Frame, Image):
    """A container for ID3v2.3 image (APIC) frames."""

    FRAME_HEADER = Con.Struct('apic_frame',
                              Con.Byte('text_encoding'),
                              Con.CString('mime_type'),
                              Con.Byte('picture_type'),
                              Con.Switch("description",
                                         lambda ctx: ctx.text_encoding,
                                         {0x00: Con.CString(
                    "s", encoding='latin-1'),
                                          0x01: UCS2CString("s")}))

    def __init__(self, data, mime_type, description, pic_type):
        """Fields are as follows:

        data        - a binary string of raw image data
        mime_type   - a unicode string
        description - a unicode string
        pic_type    - an integer
        """

        ID3v23Frame.__init__(self, 'APIC', None)

        try:
            img = Image.new(data, u'', 0)
        except InvalidImage:
            img = Image(data=data, mime_type=u'',
                        width=0, height=0, color_depth=0, color_count=0,
                        description=u'', type=0)

        self.pic_type = pic_type
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description,
                       type={3: 0, 4: 1, 5: 2, 6: 3}.get(pic_type, 4))

    def __eq__(self, i):
        return Image.__eq__(self, i)

    def __unicode__(self):
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width, self.height, self.mime_type)

    def build(self):
        """Returns a binary string of ID3v2.3 frame data."""

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
        """Given an Image object, returns an ID3v23PicFrame object."""

        return cls(data=image.data,
                   mime_type=image.mime_type,
                   description=image.description,
                   pic_type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0))


class ID3v23ComFrame(ID3v23TextFrame):
    """A container for ID3v2.3 comment (COMM) frames."""

    COMMENT_HEADER = ID3v22ComFrame.COMMENT_HEADER

    TEXT_TYPE = True

    def __init__(self, encoding, language, short_description, content):
        """Fields are as follows:

        encoding          - a text encoding integer 0/1
        language          - a 3 byte language field
        short_description - a unicode string
        contenxt          - a unicode string
        """

        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.content = content
        self.id = 'COMM'

    def __len__(self):
        return len(self.content)

    def __eq__(self, o):
        return __attrib_equals__(["encoding", "language",
                                  "short_description", "content"], self, o)

    def __unicode__(self):
        return self.content

    def __int__(self):
        return 0

    @classmethod
    def from_unicode(cls, s):
        """Builds an ID3v23ComFrame from a unicode string."""

        for encoding in 0x00, 0x01:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding, 'eng', u'', s)
            except UnicodeEncodeError:
                continue

    def build(self):
        """Returns a binary string of ID3v2.3 frame data."""

        return ID3v23Frame.build(
            self,
            self.COMMENT_HEADER.build(Con.Container(
                    encoding=self.encoding,
                    language=self.language,
                    short_description=self.short_description)) + \
                self.content.encode(self.ENCODING[self.encoding], 'replace'))


class ID3v23Comment(ID3v22Comment):
    """A complete ID3v2.3 comment."""

    Frame = ID3v23Frame
    TextFrame = ID3v23TextFrame
    PictureFrame = ID3v23PicFrame

    TAG_HEADER = Con.Struct("id3v23_header",
                            Con.Const(Con.Bytes("file_id", 3), 'ID3'),
                            Con.Byte("version_major"),
                            Con.Byte("version_minor"),
                            Con.Embed(Con.BitStruct("flags",
                                                    Con.Flag("unsync"),
                                                    Con.Flag("extended"),
                                                    Con.Flag("experimental"),
                                                    Con.Flag("footer"),
                                                    Con.Padding(4))),
                            Syncsafe32("length"))

    ATTRIBUTE_MAP = {'track_name': 'TIT2',
                     'track_number': 'TRCK',
                     'track_total': 'TRCK',
                     'album_name': 'TALB',
                     'artist_name': 'TPE1',
                     'performer_name': 'TPE2',
                     'composer_name': 'TCOM',
                     'conductor_name': 'TPE3',
                     'media': 'TMED',
                     'ISRC': 'TSRC',
                     'copyright': 'TCOP',
                     'publisher': 'TPUB',
                     'year': 'TYER',
                     'date': 'TRDA',
                     'album_number': 'TPOS',
                     'album_total': 'TPOS',
                     'comment': 'COMM'}

    INTEGER_ITEMS = ('TRCK', 'TPOS')

    KEY_ORDER = ('TIT2', 'TALB', 'TRCK', 'TPOS', 'TPE1', 'TPE2', 'TCOM',
                 'TPE3', 'TPUB', 'TSRC', 'TMED', 'TYER', 'TRDA', 'TCOP',
                 None, 'COMM', 'APIC')

    ITUNES_COMPILATION = 'TCMP'

    def __comment_name__(self):
        return u'ID3v2.3'

    def __comment_pairs__(self):
        key_order = list(self.KEY_ORDER)

        def by_weight(keyval1, keyval2):
            (key1, key2) = (keyval1[0], keyval2[0])

            if (key1 in key_order):
                order1 = key_order.index(key1)
            else:
                order1 = key_order.index(None)

            if (key2 in key_order):
                order2 = key_order.index(key2)
            else:
                order2 = key_order.index(None)

            return cmp((order1, key1), (order2, key2))

        pairs = []

        for (key, values) in sorted(self.frames.items(), by_weight):
            for value in values:
                pairs.append(('    ' + key, unicode(value)))

        return pairs

    def add_image(self,  image):
        """Embeds an Image object in this metadata."""

        image = self.PictureFrame.converted(image)
        self.frames.setdefault('APIC', []).append(image)

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        del(self.frames['APIC'][self['APIC'].index(image)])

    def images(self):
        """Returns a list of embedded Image objects."""

        if ('APIC' in self.frames.keys()):
            return self.frames['APIC'][:]
        else:
            return []

    def build(self):
        """Returns an ID3v2.3 comment as a binary string."""

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
    """A container for individual ID3v2.4 frames."""

    FRAME = Con.Struct("id3v24_frame",
                       Con.Bytes("frame_id", 4),
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
                       Con.String("data", length=lambda ctx: ctx["size"]))

    def build(self, data=None):
        """Returns a binary string of ID3v2.4 frame data."""

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
    def parse(cls, container):
        """Returns the appropriate ID3v24Frame subclass from a Container.

        Container is parsed from ID3v24Frame.FRAME
        and contains "frame_id and "data" attributes.
        """

        if (container.frame_id.startswith('T')):
            try:
                encoding_byte = ord(container.data[0])
                return ID3v24TextFrame(container.frame_id,
                                       encoding_byte,
                                       container.data[1:].decode(
                        ID3v24TextFrame.ENCODING[encoding_byte]))
            except IndexError:
                return ID3v24TextFrame(container.frame_id,
                                       0,
                                       u"")
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
                        ID3v24TextFrame.ENCODING[com.encoding], 'replace'))
            except Con.core.ArrayError:
                return cls(frame_id=container.frame_id, data=container.data)
            except Con.core.FieldError:
                return cls(frame_id=container.frame_id, data=container.data)
        else:
            return cls(frame_id=container.frame_id,
                       data=container.data)

    def __unicode__(self):
        if (self.id.startswith('W')):
            return self.data.rstrip(chr(0)).decode('iso-8859-1', 'replace')
        else:
            if (len(self.data) <= 20):
                return unicode(self.data.encode('hex').upper())
            else:
                return (unicode(self.data[0:19].encode('hex').upper()) +
                        u"\u2026")


class ID3v24TextFrame(ID3v24Frame):
    """A container for individual ID3v2.4 text frames."""

    ENCODING = {0x00: "latin-1",
                0x01: "utf-16",
                0x02: "utf-16be",
                0x03: "utf-8"}

    TEXT_TYPE = True

    #encoding is an encoding byte
    #s is a unicode string
    def __init__(self, frame_id, encoding, s):
        """frame_id is a 4 byte ID, encoding is 0-3, s is a unicode string."""

        self.id = frame_id
        self.encoding = encoding
        self.string = s

    def __eq__(self, o):
        return __attrib_equals__(["id", "encoding", "string"], self, o)

    def __len__(self):
        return len(self.string)

    def __unicode__(self):
        return self.string

    def __int__(self):
        try:
            return int(re.findall(r'\d+', self.string)[0])
        except IndexError:
            return 0

    def total(self):
        """If the frame is number/total formatted, return the "total" int."""

        try:
            return int(re.findall(r'\d+/(\d+)', self.string)[0])
        except IndexError:
            return 0

    @classmethod
    def from_unicode(cls, frame_id, s):
        """Builds an ID3v24TextFrame from 4 byte frame_id and unicode s."""

        if (frame_id == 'COMM'):
            return ID3v24ComFrame.from_unicode(s)

        for encoding in 0x00, 0x03, 0x01, 0x02:
            try:
                s.encode(cls.ENCODING[encoding])
                return ID3v24TextFrame(frame_id, encoding, s)
            except UnicodeEncodeError:
                continue

    def build(self):
        """Returns a binary string of ID3v2.4 frame data."""

        return ID3v24Frame.build(
            self,
            chr(self.encoding) + \
                self.string.encode(self.ENCODING[self.encoding],
                                   'replace'))


class ID3v24PicFrame(ID3v24Frame, Image):
    """A container for ID3v2.4 image (APIC) frames."""

    FRAME_HEADER = Con.Struct('apic_frame',
                              Con.Byte('text_encoding'),
                              Con.CString('mime_type'),
                              Con.Byte('picture_type'),
                              Con.Switch("description",
                                         lambda ctx: ctx.text_encoding,
                                         {0x00: Con.CString(
                    "s", encoding='latin-1'),
                                          0x01: UTF16CString("s"),
                                          0x02: UTF16BECString("s"),
                                          0x03: Con.CString(
                    "s", encoding='utf-8')}))

    def __init__(self, data, mime_type, description, pic_type):
        """Fields are as follows:

        data        - a binary string of raw image data
        mime_type   - a unicode string
        description - a unicode string
        pic_type    - an integer
        """

        ID3v24Frame.__init__(self, 'APIC', None)

        try:
            img = Image.new(data, u'', 0)
        except InvalidImage:
            img = Image(data=data, mime_type=u'',
                        width=0, height=0, color_depth=0, color_count=0,
                        description=u'', type=0)

        self.pic_type = pic_type
        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=description,
                       type={3: 0, 4: 1, 5: 2, 6: 3}.get(pic_type, 4))

    def __eq__(self, i):
        return Image.__eq__(self, i)

    def __unicode__(self):
        return u"%s (%d\u00D7%d,'%s')" % \
               (self.type_string(),
                self.width, self.height, self.mime_type)

    def build(self):
        """Returns a binary string of ID3v2.4 frame data."""

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
        """Given an Image object, returns an ID3v24PicFrame object."""

        return cls(data=image.data,
                   mime_type=image.mime_type,
                   description=image.description,
                   pic_type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0))


class ID3v24ComFrame(ID3v24TextFrame):
    """A container for ID3v2.4 comment (COMM) frames."""

    COMMENT_HEADER = Con.Struct(
        "com_frame",
        Con.Byte("encoding"),
        Con.String("language", 3),
        Con.Switch("short_description",
                   lambda ctx: ctx.encoding,
                   {0x00: Con.CString("s", encoding='latin-1'),
                    0x01: UTF16CString("s"),
                    0x02: UTF16BECString("s"),
                    0x03: Con.CString("s", encoding='utf-8')}))

    TEXT_TYPE = True

    def __init__(self, encoding, language, short_description, content):
        """Fields are as follows:

        encoding          - a text encoding integer 0-3
        language          - a 3 byte language field
        short_description - a unicode string
        contenxt          - a unicode string
        """

        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.content = content
        self.id = 'COMM'

    def __eq__(self, o):
        return __attrib_equals__(["encoding", "language",
                                  "short_description", "content"], self, o)

    def __unicode__(self):
        return self.content

    def __int__(self):
        return 0

    @classmethod
    def from_unicode(cls, s):
        """Builds an ID3v24ComFrame from a unicode string."""

        for encoding in 0x00, 0x03, 0x01, 0x02:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding, 'eng', u'', s)
            except UnicodeEncodeError:
                continue

    def build(self):
        """Returns a binary string of ID3v2.4 frame data."""

        return ID3v24Frame.build(
            self,
            self.COMMENT_HEADER.build(Con.Container(
                    encoding=self.encoding,
                    language=self.language,
                    short_description=self.short_description)) + \
                self.content.encode(self.ENCODING[self.encoding], 'replace'))


class ID3v24Comment(ID3v23Comment):
    """A complete ID3v2.4 comment."""

    Frame = ID3v24Frame
    TextFrame = ID3v24TextFrame
    PictureFrame = ID3v24PicFrame

    def __repr__(self):
        return "ID3v24Comment(%s)" % (repr(self.__dict__["frames"]))

    def __comment_name__(self):
        return u'ID3v2.4'

    def build(self):
        """Returns an ID3v2.4 comment as a binary string."""

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
    """A pair of ID3v2/ID3v1 comments.

    These can be manipulated as a set."""

    def __init__(self, id3v2_comment, id3v1_comment):
        """id3v2 and id3v1 are ID3v2Comment and ID3v1Comment objects or None.

        Values in ID3v2 take precendence over ID3v1, if present."""

        self.__dict__['id3v2'] = id3v2_comment
        self.__dict__['id3v1'] = id3v1_comment

        if (self.id3v2 is not None):
            base_comment = self.id3v2
        elif (self.id3v1 is not None):
            base_comment = self.id3v1
        else:
            raise ValueError(_(u"ID3v2 and ID3v1 cannot both be blank"))

        fields = dict([(field, getattr(base_comment, field))
                       for field in self.__FIELDS__])

        MetaData.__init__(self, **fields)

    def __setattr__(self, key, value):
        self.__dict__[key] = value

        if (self.id3v2 is not None):
            setattr(self.id3v2, key, value)
        if (self.id3v1 is not None):
            setattr(self.id3v1, key, value)

    def __delattr__(self, key):
        if (self.id3v2 is not None):
            delattr(self.id3v2, key)
        if (self.id3v1 is not None):
            delattr(self.id3v1, key)

    @classmethod
    def converted(cls, metadata,
                  id3v2_class=ID3v23Comment,
                  id3v1_class=ID3v1Comment):
        """Takes a MetaData object and returns an ID3CommentPair object."""

        if ((metadata is None) or (isinstance(metadata, ID3CommentPair))):
            return metadata

        if (isinstance(metadata, ID3v2Comment)):
            return ID3CommentPair(metadata,
                                  id3v1_class.converted(metadata))
        else:
            return ID3CommentPair(
                id3v2_class.converted(metadata),
                id3v1_class.converted(metadata))

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        self.id3v2.merge(metadata)
        self.id3v1.merge(metadata)

    def __unicode__(self):
        if ((self.id3v2 is not None) and (self.id3v1 is not None)):
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
        """Returns a list of embedded Image objects."""

        if (self.id3v2 is not None):
            return self.id3v2.images()
        else:
            return []

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        if (self.id3v2 is not None):
            self.id3v2.add_image(image)

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        if (self.id3v2 is not None):
            self.id3v2.delete_image(image)

    @classmethod
    def supports_images(cls):
        """Returns True."""

        return True
