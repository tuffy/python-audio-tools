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

from audiotools import (MetaData, re, os, cStringIO,
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

def decode_syncsafe32(reader):
    from operator import or_
    return reduce(or_,
                  [size << (7 * (3 - i))
                   for (i, size) in
                   enumerate(reader.parse("1p 7u 1p 7u 1p 7u 1p 7u"))])

def encode_syncsafe32(writer, value):
    writer.build("1p 7u 1p 7u 1p 7u 1p 7u",
                 [(value >> (7 * i)) & 0x7F for i in [3, 2, 1, 0]])

def decode_ascii_c_string(reader):
    """given a BitstreamReader and encoding byte, return unicode string

    encoding is ASCII and unknown characters are replaced"""

    chars = []
    char = reader.read(8)
    while (char != 0):
        chars.append(char)
        char = reader.read(8)
    return "".join(map(chr, chars)).decode('ascii','replace')

def encode_ascii_c_string(writer, s):
    """write NULL-terminated ASCII unicode string to stream"""

    encoded = s.encode('ascii', 'replace')
    writer.build("%db 8u" % (len(encoded)), (encoded, 0))


class __Counter__:
    def __init__(self, value=0):
        self.value = value

    def __int__(self):
        return self.value

    def increment(self, b):
        self.value += 1

    def decrement(self, b):
        self.value -= 1


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

    ENCODING = {0x00: "latin-1",
                0x01: "ucs2"}

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

    def build(self, writer):
        """writes frame data to BitstreamWriter, without the header"""

        writer.write_bytes(self.data)

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
    def decode_text(cls, byte_string, encoding_byte):
        """given a plain text string and encoding byte, returns unicode

        if the byte is valid, this presumes the encoding is correct and uses
        text.decode('encoding', 'replace') to handle errors

        if the byte is invalid, we assume ASCII
        """

        try:
            return byte_string.decode(cls.ENCODING[encoding_byte], 'replace')
        except KeyError:
            return byte_string.decode('ascii', 'replace')

    @classmethod
    def encode_text(cls, unicode_string, encoding_byte):
        """given unicode text and an encoding byte, returns a raw string

        this presumes the encoding byte is sane,
        otherwise unicode.encode('encoding', 'replace') is applied
        """

        return unicode_string.encode(cls.ENCODING[encoding_byte], 'replace')

    @classmethod
    def decode_c_string(cls, reader, encoding_byte):
        """given a BitstreamReader and encoding byte, return unicode string

        this is designed to handle the dicey problem of string
        NULL terminators for wide characters
        """

        if (encoding_byte == 0):
            chars = []
            char = reader.read(8)
            while (char != 0):
                chars.append(char)
                char = reader.read(8)
            return "".join(map(chr, chars)).decode('latin-1','replace')
        elif (encoding_byte == 1):
            chars = []
            (high, low) = reader.parse("8u 8u")
            while ((high != 0) and (low != 0)):
                chars.append(high)
                chars.append(low)
                (high, low) = reader.parse("8u 8u")
            return "".join(map(chr, chars)).decode('ucs2','replace')
        else:
            raise ValueError(_(u"invalid encoding byte"))

    @classmethod
    def encode_c_string(cls, writer, unicode_string, encoding_byte):
        """given BitstreamWriter, unicode and encoding, write C string

        as with the decode_c_string, this is meant to handle
        NULL termination correctly
        """

        if (encoding_byte == 0):
            encoded = unicode_string.encode('latin-1')
            writer.build("%db 8u" % (len(encoded)), (encoded, 0))
        elif (encoding_byte == 1):
            encoded = unicode_string.encode('ucs2', 'replace')
            writer.build("%db 16u" % (len(encoded)), (encoded, 0))
        else:
            raise ValueError(_(u"invalid encoding byte"))

    @classmethod
    def encoding_byte(cls, unicode_string):
        """given a unicode string, returns the best encoding byte for it

        since all ID3v2 tags support some sort of unicode,
        something is certain to work
        """

        #see if unicode_string falls into a set of latin-1 chars
        #otherwise use unicode
        if (frozenset(unicode_string).issubset(
                frozenset(map(unichr, range(32, 127) + range(160,256))))):
            return 0
        else:
            return 1

    @classmethod
    def parse(cls, frame_id, frame_size, frame_data):
        """given an id string, size int and data BitstreamReader

        returns an ID3v22Frame or subclass"""

        if (frame_id.startswith('T')):
            encoding = frame_data.read(8)
            return ID3v22TextFrame(
                frame_id,
                encoding,
                cls.decode_text(frame_data.read_bytes(frame_size - 1),
                                encoding))

        elif (frame_id == 'PIC'):
            remaining_bytes = __Counter__(frame_size)
            frame_data.add_callback(remaining_bytes.decrement)
            (encoding,
             image_format,
             picture_type) = frame_data.parse("8u 3b 8u")
            description = cls.decode_c_string(frame_data, encoding)
            data = frame_data.read_bytes(remaining_bytes)

            return ID3v22PicFrame(data,
                                  image_format.decode('ascii', 'replace'),
                                  encoding,
                                  description,
                                  picture_type)

        elif (frame_id == 'COM'):
            remaining_bytes = __Counter__(frame_size)
            frame_data.add_callback(remaining_bytes.decrement)
            (encoding,
             language) = frame_data.parse("8u 3b")
            description = cls.decode_c_string(frame_data, encoding)
            content = cls.decode_text(frame_data.read_bytes(remaining_bytes),
                                      encoding)

            return ID3v22ComFrame(encoding,
                                  language,
                                  description,
                                  content)
        else:
            return cls(frame_id, frame_data.read_bytes(frame_size))

class ID3v22TextFrame(ID3v22Frame):
    """A container for individual ID3v2.2 text frames."""

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
        else:
            return cls(frame_id, cls.encoding_byte(s), s)

    def build(self, writer):
        """builds an ID3v2.2 text frame on the given BitstreamWriter"""

        writer.write(8, self.encoding)
        writer.write_bytes(self.encode_text(self.string, self.encoding))

class ID3v22ComFrame(ID3v22TextFrame):
    """A container for ID3v2.2 comment (COM) frames."""

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

        return cls(cls.encoding_byte(s), 'eng', u'', s)

    def build(self, writer):
        """builds a binary string of COM data to the given BitstreamWriter"""

        writer.build("8u 3b", (self.encoding, self.language))
        self.encode_c_string(writer, self.short_description, self.encoding)
        writer.write_bytes(self.encode_text(self.content, self.encoding))


class ID3v22PicFrame(ID3v22Frame, Image):
    """A container for ID3v2.2 image (PIC) frames."""

    def __init__(self, data, format, encoding, description, pic_type):
        """Fields are as follows:

        data        - a binary string of raw image data
        format      - a unicode string
        encoding    - a text encoding byte for the description
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
        self.encoding = encoding
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

    def build(self, writer):
        """builds a binary string of PIC data to the given BitstreamWriter"""

        writer.build("8u 3b 8u",
                     (self.encoding,
                      self.format.encode('ascii', 'replace'),
                      self.pic_type))
        self.encode_c_string(writer, description, self.encoding)
        writer.write_bytes(self.data)



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
                   encoding=cls.encoding_byte(image.description),
                   description=image.description,
                   pic_type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0))


class ID3v22Comment(MetaData):
    """A complete ID3v2.2 comment."""

    Frame = ID3v22Frame
    TextFrame = ID3v22TextFrame
    PictureFrame = ID3v22PicFrame
    CommentFrame = ID3v22ComFrame

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
        """frames should be a list of ID3v2?Frame-compatible objects."""

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
        """given a BitstreamReader, returns an ID3v22Comment object"""

        (tag_id,
         major_version,
         minor_version,
         unsync,
         compression) = stream.parse("3b 8u 8u 1u 1u 6p")

        if (major_version != 0x2):
            raise ValueError(_(u"unsupported major version"))

        total_size = decode_syncsafe32(stream)

        tag_stream = stream.substream(total_size)
        frames = []

        while (total_size > 0):
            (frame_id, frame_size) = tag_stream.parse("3b 24u")
            if ((frame_id == (chr(0) * 3)) and (frame_size == 0)):
                break
            total_size -= 6
            frames.append(cls.Frame.parse(frame_id,
                                          frame_size,
                                          tag_stream.substream(frame_size)))
            total_size -= frame_size

        return cls(frames)

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to an ID3v22Comment object."""

        if ((metadata is None) or
            (isinstance(metadata, cls) and (cls.Frame is metadata.Frame))):
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

    def build(self, writer):
        """generates an ID3v2.2 tag to the given file object"""

        from .bitstream import BitstreamRecorder

        subframes = BitstreamRecorder(0)
        frame_data = BitstreamRecorder(0)
        for frames in self.frames.values():
            for frame in frames:
                frame_data.reset()
                frame.build(frame_data)
                subframes.build("3b 24u", (frame.id, frame_data.bytes()))
                frame_data.copy(subframes)

        writer.build("3b 8u 8u 1u 1u 6p", ("ID3", 2, 0, 0, 0))
        encode_syncsafe32(writer, subframes.bytes())
        subframes.copy(writer)

    @classmethod
    def skip(cls, file):
        """Seeks past an ID3v2 comment if found in the file stream.
        Returns the number of bytes skipped.

        The stream must be seekable, obviously."""

        from .bitstream import BitstreamReader

        reader = BitstreamReader(file, 0)
        reader.mark()
        try:
            (tag_id, tag_version) = reader.parse("3b 16u 8p")
        except IOError, err:
            reader.unmark()
            raise err

        if ((tag_id == 'ID3') and (tag_version in (2, 3, 4))):
            reader.unmark()

            #parse the header
            bytes_skipped += 6
            tag_size = decode_syncsafe32(reader)
            bytes_skipped += 4

            #skip to the end of its length
            reader.skip_bytes(tag_size)
            bytes_skipped += tag_size

            #skip any null bytes after the IDv2 tag
            reader.mark()
            try:
                byte = reader.read(8)
                while (byte == 0):
                    reader.unmark()
                    bytes_skipped += 1
                    reader.mark()
                    byte = reader.read(8)

                reader.rewind()
                reader.unmark()

                return bytes_skipped
            except IOError, err:
                reader.unmark()
                raise err
        else:
            reader.rewind()
            reader.unmark()
            return 0


    @classmethod
    def read_id3v2_comment(cls, filename):
        """Given a filename, returns an ID3v22Comment or a subclass.

        For example, if the file is ID3v2.3 tagged,
        this returns an ID3v23Comment.
        """

        from .bitstream import BitstreamReader

        reader = BitstreamReader(file(filename, "rb"), 0)
        reader.mark()
        try:
            (tag, version_major, version_minor) = reader.parse("3b 8u 8u")
            if (tag != 'ID3'):
                raise UnsupportedID3v2Version()
            elif (version_major == 0x2):
                reader.rewind()
                return ID3v22Comment.parse(reader)
            elif (version_major == 0x3):
                reader.rewind()
                return ID3v23Comment.parse(reader)
            elif (version_major == 0x4):
                reader.rewind()
                return ID3v24Comment.parse(reader)
            else:
                raise UnsupportedID3v2Version()
        finally:
            reader.unmark()
            reader.close()

    def clean(self, fixes_performed):
        cleaned_frames = []

        for (key, frames) in self.frames.items():
            for frame in frames:
                if (hasattr(frame, "id") and
                    hasattr(frame, "encoding") and
                    hasattr(frame, "string")):
                    #check trailing whitespace
                    fix1 = frame.__class__(frame.id,
                                           frame.encoding,
                                           frame.string.rstrip())
                    if (fix1.string != frame.string):
                        fixes_performed.append(
                            _(u"removed trailing whitespace from %(field)s") %
                            {"field":frame.id.decode('ascii')})

                    #check leading whitespace
                    fix2 = frame.__class__(fix1.id,
                                           fix1.encoding,
                                           fix1.string.lstrip())
                    if (fix2.string != fix1.string):
                        fixes_performed.append(
                            _(u"removed leading whitespace from %(field)s") %
                            {"field":frame.id.decode('ascii')})

                    #check numerical field padding
                    if (fix2.id in self.INTEGER_ITEMS):
                        fix3 = frame.__class__(
                            fix2.id,
                            fix2.encoding,
                            __number_pair__(int(fix2), fix2.total()))
                        if (fix3.string != fix2.string):
                            if (__number_pair__ is __unpadded_number_pair__):
                                fixes_performed.append(
                                    _(u"removed leading zeroes from %(field)s" %
                                      {"field":frame.id.decode('ascii')}))
                            else:
                                fixes_performed.append(
                                    _(u"added leading zeroes to %(field)s" %
                                      {"field":frame.id.decode('ascii')}))
                    else:
                        fix3 = fix2

                    #check empty fields here
                    if (len(fix3.string) == 0):
                        fixes_performed.append(
                            _(u"removed empty field %(field)s") %
                            {"field":frame.id.decode('ascii')})
                    else:
                        cleaned_frames.append(fix3)
                elif (isinstance(frame, Image)):
                    fixed_image = Image.new(frame.data,
                                            frame.description,
                                            frame.type)
                    if ((fixed_image.mime_type != frame.mime_type) or
                        (fixed_image.width != frame.width) or
                        (fixed_image.height != frame.height) or
                        (fixed_image.color_depth != frame.color_depth) or
                        (fixed_image.color_count != frame.color_count)):
                        fixes_performed.append(
                            _(u"fixed embedded image metadata fields"))
                        cleaned_frames.append(
                            frame.__class__.converted(fixed_image))
                    else:
                        cleaned_frames.append(frame)
                else:
                    cleaned_frames.append(frame)

        return self.__class__(cleaned_frames)


#######################
#ID3v2.3
#######################


class ID3v23Frame(ID3v22Frame):
    """A container for individual ID3v2.3 frames."""

    @classmethod
    def parse(cls, frame_id, frame_size, frame_data):
        """given an id string, size int and data BitstreamReader

        returns an ID3v22Frame or subclass"""

        if (frame_id.startswith('T')):
            encoding = frame_data.read(8)
            return ID3v23TextFrame(
                frame_id,
                encoding,
                cls.decode_text(frame_data.read_bytes(frame_size - 1),
                                encoding))
        elif (frame_id == 'APIC'):
            remaining_bytes = __Counter__(frame_size)
            frame_data.add_callback(remaining_bytes.decrement)
            encoding = frame_data.read(8)
            mime_type = decode_ascii_c_string(frame_data)
            picture_type = frame_data.read(8)
            description = cls.decode_c_string(frame_data, encoding)
            data = frame_data.read_bytes(remaining_bytes)
            return ID3v23PicFrame(data,
                                  mime_type,
                                  encoding,
                                  description,
                                  picture_type)
        elif (frame_id == 'COMM'):
            remaining_bytes = __Counter__(frame_size)
            frame_data.add_callback(remaining_bytes.decrement)
            (encoding,
             language) = frame_data.parse("8u 3b")
            description = cls.decode_c_string(frame_data, encoding)
            content = cls.decode_text(frame_data.read_bytes(remaining_bytes),
                                      encoding)
            return ID3v23ComFrame(encoding,
                                  language,
                                  description,
                                  content)
        else:
            return cls(frame_id, frame_data.read_bytes(frame_size))

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

    def build(self, writer):
        """builds an ID3v2.3 text frame on the given BitstreamWriter"""

        writer.write(8, self.encoding)
        writer.write_bytes(self.encode_text(self.string, self.encoding))


class ID3v23PicFrame(ID3v23Frame, Image):
    """A container for ID3v2.3 image (APIC) frames."""

    def __init__(self, data, mime_type, encoding, description, pic_type):
        """Fields are as follows:

        data        - a binary string of raw image data
        mime_type   - a unicode string
        encoding    - an encoding byte
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
        self.encoding = encoding
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

    def build(self, writer):
        """builds a binary string of APIC data to the given BitstreamWriter"""

        writer.write(8, self.encoding)
        encode_ascii_c_string(writer, self.mime_type)
        writer.write(8, self.pic_type)
        self.encode_c_string(writer, self.description, self.encoding)
        writer.write_bytes(self.data)

    @classmethod
    def converted(cls, image):
        """Given an Image object, returns an ID3v23PicFrame object."""

        return cls(data=image.data,
                   mime_type=image.mime_type,
                   encoding=cls.encoding_byte(image.description),
                   description=image.description,
                   pic_type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0))


class ID3v23ComFrame(ID3v23TextFrame):
    """A container for ID3v2.3 comment (COMM) frames."""

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

    def build(self, writer):
        """builds a binary string of COM data to the given BitstreamWriter"""

        writer.build("8u 3b", (self.encoding, self.language))
        self.encode_c_string(writer, self.short_description, self.encoding)
        writer.write_bytes(self.encode_text(self.content, self.encoding))

class ID3v23Comment(ID3v22Comment):
    """A complete ID3v2.3 comment."""

    Frame = ID3v23Frame
    TextFrame = ID3v23TextFrame
    PictureFrame = ID3v23PicFrame

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

    @classmethod
    def parse(cls, stream):
        """given a BitstreamReader, returns an ID3v23Comment object"""

        (tag_id,
         major_version,
         minor_version,
         unsync,
         extended,
         experimental,
         footer) = stream.parse("3b 8u 8u 1u 1u 1u 1u 4p")

        if (major_version != 0x3):
            raise ValueError(_(u"unsupported major version"))

        total_size = decode_syncsafe32(stream)
        tag_stream = stream.substream(total_size)
        frames = []

        while (total_size > 0):
            (frame_id,
             frame_size,
             tag_alter,
             file_alter,
             read_only,
             compression,
             encryption,
             grouping) = tag_stream.parse("4b 32u 1u 1u 1u 5p 1u 1u 1u 5p")
            if ((frame_id == (chr(0) * 4)) and (frame_size == 0)):
                break
            total_size -= 10
            frames.append(cls.Frame.parse(frame_id,
                                          frame_size,
                                          tag_stream.substream(frame_size)))
            total_size -= frame_size

        return cls(frames)


    def build(self, writer):
        """generates an ID3v2.3 tag to the given BitstreamWriter"""

        from .bitstream import BitstreamRecorder

        subframes = BitstreamRecorder(0)
        frame_data = BitstreamRecorder(0)
        for frames in self.frames.values():
            for frame in frames:
                frame_data.reset()
                frame.build(frame_data)
                subframes.build("4b 32u 1u 1u 1u 5p 1u 1u 1u 5p",
                                (frame.id, frame_data.bytes(),
                                 0, 0, 0, 0, 0, 0))
                frame_data.copy(subframes)

        writer.build("3b 8u 8u 1u 1u 1u 1u 4p", ("ID3", 3, 0, 0, 0, 0, 0))
        encode_syncsafe32(writer, subframes.bytes())
        subframes.copy(writer)


#######################
#ID3v2.4
#######################


class ID3v24Frame(ID3v23Frame):
    """A container for individual ID3v2.4 frames."""

    ENCODING = {0x00: "latin-1",
                0x01: "utf-16",
                0x02: "utf-16be",
                0x03: "utf-8"}

    @classmethod
    def decode_c_string(cls, reader, encoding_byte):
        if (encoding_byte == 0):
            chars = []
            char = reader.read(8)
            while (char != 0):
                chars.append(char)
                char = reader.read(8)
            return "".join(map(chr, chars)).decode('latin-1','replace')
        elif (encoding_byte == 1):
            chars = []
            (high, low) = reader.parse("8u 8u")
            while ((high != 0) and (low != 0)):
                chars.append(high)
                chars.append(low)
                (high, low) = reader.parse("8u 8u")
            return "".join(map(chr, chars)).decode('utf-16','replace')
        elif (encoding_byte == 2):
            chars = []
            (high, low) = reader.parse("8u 8u")
            while ((high != 0) and (low != 0)):
                chars.append(high)
                chars.append(low)
                (high, low) = reader.parse("8u 8u")
            return "".join(map(chr, chars)).decode('utf-16be','replace')
        elif (encoding_byte == 3):
            chars = []
            char = reader.read(8)
            while (char != 0):
                chars.append(char)
                char = reader.read(8)
            return "".join(map(chr, chars)).decode('utf-8','replace')
        else:
            raise ValueError(_(u"invalid encoding byte"))

    @classmethod
    def encode_c_string(cls, writer, unicode_string, encoding_byte):
        """given BitstreamWriter, unicode and encoding, write C string

        as with the decode_c_string, this is meant to handle
        NULL termination correctly
        """

        if (encoding_byte == 0):
            encoded = unicode_string.encode('latin-1')
            writer.build("%db 8u" % (len(encoded)), (encoded, 0))
        elif (encoding_byte == 1):
            encoded = unicode_string.encode('utf-16', 'replace')
            writer.build("%db 16u" % (len(encoded)), (encoded, 0))
        elif (encoding_byte == 2):
            encoded = unicode_string.encode('utf-16be', 'replace')
            writer.build("%db 16u" % (len(encoded)), (encoded, 0))
        elif (encoding_byte == 3):
            encoded = unicode_string.encode('utf-8')
            writer.build("%db 8u" % (len(encoded)), (encoded, 0))
        else:
            raise ValueError(_(u"invalid encoding byte"))

    @classmethod
    def encoding_byte(cls, unicode_string):
        """given a unicode string, returns the best encoding byte for it

        since all ID3v2 tags support some sort of unicode,
        something is certain to work
        """

        #see if unicode_string falls into a set of latin-1 chars
        #otherwise use unicode
        if (frozenset(unicode_string).issubset(
                frozenset(map(unichr, range(32, 127) + range(160,256))))):
            return 0
        else:
            return 3

    @classmethod
    def parse(cls, frame_id, frame_size, frame_data):
        """given an id string, size int and data BitstreamReader

        returns an ID3v24Frame or subclass"""

        if (frame_id.startswith('T')):
            encoding = frame_data.read(8)
            return ID3v24TextFrame(
                frame_id,
                encoding,
                cls.decode_text(frame_data.read_bytes(frame_size - 1),
                                encoding))
        elif (frame_id == 'APIC'):
            remaining_bytes = __Counter__(frame_size)
            frame_data.add_callback(remaining_bytes.decrement)
            encoding = frame_data.read(8)
            mime_type = decode_ascii_c_string(frame_data)
            picture_type = frame_data.read(8)
            description = cls.decode_c_string(frame_data, encoding)
            data = frame_data.read_bytes(remaining_bytes)
            return ID3v24PicFrame(data,
                                  mime_type,
                                  encoding,
                                  description,
                                  picture_type)
        elif (frame_id == 'COMM'):
            remaining_bytes = __Counter__(frame_size)
            frame_data.add_callback(remaining_bytes.decrement)
            (encoding,
             language) = frame_data.parse("8u 3b")
            description = cls.decode_c_string(frame_data, encoding)
            content = cls.decode_text(frame_data.read_bytes(remaining_bytes),
                                      encoding)
            return ID3v24ComFrame(encoding,
                                  language,
                                  description,
                                  content)
        else:
            return cls(frame_id, frame_data.read_bytes(frame_size))

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

    def build(self, writer):
        """builds an ID3v2.4 text frame on the given BitstreamWriter"""

        writer.write(8, self.encoding)
        writer.write_bytes(self.encode_text(self.string, self.encoding))


class ID3v24PicFrame(ID3v24Frame, Image):
    """A container for ID3v2.4 image (APIC) frames."""

    def __init__(self, data, mime_type, encoding, description, pic_type):
        """Fields are as follows:

        data        - a binary string of raw image data
        mime_type   - a unicode string
        encoding    - an encoding byte
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
        self.encoding = encoding
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

    def build(self, writer):
        """builds a binary string of APIC data to the given BitstreamWriter"""

        writer.write(8, self.encoding)
        encode_ascii_c_string(writer, self.mime_type)
        writer.write(8, self.pic_type)
        self.encode_c_string(writer, self.description, self.encoding)
        writer.write_bytes(self.data)

    @classmethod
    def converted(cls, image):
        """Given an Image object, returns an ID3v24PicFrame object."""

        return cls(data=image.data,
                   mime_type=image.mime_type,
                   encoding=cls.encoding_byte(image.description),
                   description=image.description,
                   pic_type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0))


class ID3v24ComFrame(ID3v24TextFrame):
    """A container for ID3v2.4 comment (COMM) frames."""

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
        """Builds an ID3v24ComFrame from a unicode string."""

        for encoding in 0x00, 0x03, 0x01, 0x02:
            try:
                s.encode(cls.ENCODING[encoding])
                return cls(encoding, 'eng', u'', s)
            except UnicodeEncodeError:
                continue

    def build(self, writer):
        """builds a binary string of COM data to the given BitstreamWriter"""

        writer.build("8u 3b", (self.encoding, self.language))
        self.encode_c_string(writer, self.short_description, self.encoding)
        writer.write_bytes(self.encode_text(self.content, self.encoding))


class ID3v24Comment(ID3v23Comment):
    """A complete ID3v2.4 comment."""

    Frame = ID3v24Frame
    TextFrame = ID3v24TextFrame
    PictureFrame = ID3v24PicFrame

    def __repr__(self):
        return "ID3v24Comment(%s)" % (repr(self.__dict__["frames"]))

    def __comment_name__(self):
        return u'ID3v2.4'

    def build(self, writer):
        """generates an ID3v2.4 tag to the given BitstreamWriter"""

        from .bitstream import BitstreamRecorder

        subframes = BitstreamRecorder(0)
        frame_data = BitstreamRecorder(0)
        for frames in self.frames.values():
            for frame in frames:
                frame_data.reset()
                frame.build(frame_data)
                subframes.write_bytes(frame.id)
                encode_syncsafe32(subframes, frame_data.bytes())
                subframes.build("1p 1u 1u 1u 4p 1p 1u 2p 1u 1u 1u 1u",
                                (0, 0, 0, 0, 0, 0, 0, 0))
                frame_data.copy(subframes)

        writer.build("3b 8u 8u 1u 1u 1u 1u 4p", ("ID3", 4, 0, 0, 0, 0, 0))
        encode_syncsafe32(writer, subframes.bytes())
        subframes.copy(writer)

    @classmethod
    def parse(cls, stream):
        """given a BitstreamReader, returns an ID3v24Comment object"""

        (tag_id,
         major_version,
         minor_version,
         unsync,
         extended,
         experimental,
         footer) = stream.parse("3b 8u 8u 1u 1u 1u 1u 4p")

        if (major_version != 0x4):
            raise ValueError(_(u"unsupported major version"))

        total_size = decode_syncsafe32(stream)
        tag_stream = stream.substream(total_size)
        frames = []

        while (total_size > 0):
            frame_id = tag_stream.read_bytes(4)
            frame_size = decode_syncsafe32(tag_stream)
            (tag_alter,
             file_alter,
             read_only,
             grouping,
             compression,
             encryption,
             unsync,
             data_length) = tag_stream.parse(
                "1p 1u 1u 1u 4p 1p 1u 2p 1u 1u 1u 1u")
            if ((frame_id == (chr(0) * 4)) and (frame_size == 0)):
                break
            total_size -= 10
            frames.append(cls.Frame.parse(frame_id,
                                          frame_size,
                                          tag_stream.substream(frame_size)))
            total_size -= frame_size

        return cls(frames)


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

    def __getattr__(self, key):
        if (key in self.__INTEGER_FIELDS__):
            if ((self.id3v2 is not None) and
                (getattr(self.id3v2, key) != 0)):
                    return getattr(self.id3v2, key)
            if (self.id3v1 is not None):
                return getattr(self.id3v1, key)
            else:
                raise ValueError(_(u"ID3v2 and ID3v1 cannot both be blank"))
        elif (key in self.__FIELDS__):
            if ((self.id3v2 is not None) and
                (getattr(self.id3v2, key) != u'')):
                    return getattr(self.id3v2, key)
            if (self.id3v1 is not None):
                return getattr(self.id3v1, key)
            else:
                raise ValueError(_(u"ID3v2 and ID3v1 cannot both be blank"))
        else:
            raise AttributeError(key)

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

    def clean(self, fixes_performed):
        if (self.id3v2 is not None):
            new_id3v2 = self.id3v2.clean(fixes_performed)
        else:
            new_id3v2 = None

        if (self.id3v1 is not None):
            new_id3v1 = self.id3v1.clean(fixes_performed)
        else:
            new_id3v1 = None

        return ID3CommentPair(new_id3v2, new_id3v1)
