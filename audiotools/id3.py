#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2014  Brian Langenberger

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

from . import (MetaData, Image, InvalidImage)
import codecs

from id3v1 import ID3v1Comment


def is_latin_1(unicode_string):
    """returns True if the given unicode string is a subset of latin-1"""

    return frozenset(unicode_string).issubset(
        frozenset(map(unichr, range(32, 127) + range(160, 256))))


class UCS2Codec(codecs.Codec):
    """a special unicode codec for UCS-2

    this is a subset of UTF-16 with no support for surrogate pairs,
    limiting it to U+0000-U+FFFF"""

    @classmethod
    def fix_char(cls, c):
        """a filter which changes overly large c values to 'unknown'"""

        if (ord(c) <= 0xFFFF):
            return c
        else:
            return u"\ufffd"

    def encode(self, input, errors='strict'):
        """encodes unicode input to plain UCS-2 strings"""

        return codecs.utf_16_encode(u"".join(map(self.fix_char, input)),
                                    errors)

    def decode(self, input, errors='strict'):
        """decodes plain UCS-2 strings to unicode"""

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


def decode_syncsafe32(i):
    """given a 32 bit int, returns a 28 bit value
    with sync-safe bits removed

    may raise ValueError if the value is negative,
    larger than 32 bits or contains invalid sync-safe bits"""

    if (i >= (2 ** 32)):
        raise ValueError("value too large")
    elif (i < 0):
        raise ValueError("value cannot be negative")

    value = 0

    for x in xrange(4):
        if ((i & 0x80) == 0):
            value |= ((i & 0x7F) << (x * 7))
            i >>= 8
        else:
            raise ValueError("invalid sync-safe bit")

    return value

def encode_syncsafe32(i):
    """given a 28 bit int, returns a 32 bit value
    with sync-safe bits added

    may raise ValueError is the value is negative
    or larger than 28 bits"""

    if (i >= (2 ** 28)):
        raise ValueError("value too large")
    elif (i < 0):
        raise ValueError("value cannot be negative")

    value = 0

    for x in xrange(4):
        value |= ((i & 0x7F) << (x * 8))
        i >>= 7

    return value

class C_string:
    TERMINATOR = {'ascii': chr(0),
                  'latin_1': chr(0),
                  'latin-1': chr(0),
                  'ucs2': chr(0) * 2,
                  'utf_16': chr(0) * 2,
                  'utf-16': chr(0) * 2,
                  'utf_16be': chr(0) * 2,
                  'utf-16be': chr(0) * 2,
                  'utf_8': chr(0),
                  'utf-8': chr(0)}

    def __init__(self, encoding, unicode_string):
        """encoding is a string such as 'utf-8', 'latin-1', etc"""

        self.encoding = encoding
        self.unicode_string = unicode_string

    def __repr__(self):
        return "C_string(%s, %s)" % (repr(self.encoding),
                                     repr(self.unicode_string))

    def __unicode__(self):
        return self.unicode_string

    def __getitem__(self, char):
        return self.unicode_string[char]

    def __len__(self):
        return len(self.unicode_string)

    def __cmp__(self, c_string):
        return cmp(self.unicode_string, c_string.unicode_string)

    @classmethod
    def parse(cls, encoding, reader):
        """returns a C_string with the given encoding string
        from the given BitstreamReader
        raises LookupError if encoding is unknown
        raises IOError if a problem occurs reading the stream
        """

        try:
            terminator = cls.TERMINATOR[encoding]
            terminator_size = len(terminator)
        except KeyError:
            raise LookupError(encoding)

        s = []
        char = reader.read_bytes(terminator_size)
        while (char != terminator):
            s.append(char)
            char = reader.read_bytes(terminator_size)

        return cls(encoding, "".join(s).decode(encoding, 'replace'))

    def build(self, writer):
        """writes our C_string data to the given BitstreamWriter
        with the appropriate terminator"""

        writer.write_bytes(self.unicode_string.encode(self.encoding,
                                                      'replace'))
        writer.write_bytes(self.TERMINATOR[self.encoding])

    def size(self):
        """returns the length of our C string in bytes"""

        return (len(self.unicode_string.encode(self.encoding, 'replace')) +
                len(self.TERMINATOR[self.encoding]))


def __attrib_equals__(attributes, o1, o2):
    for attrib in attributes:
        if (((not hasattr(o1, attrib)) or
             (not hasattr(o2, attrib)) or
             (getattr(o1, attrib) != getattr(o2, attrib)))):
            return False
    else:
        return True


#takes a pair of integers (or None) for the current and total values
#returns a unicode string of their combined pair
#for example, __number_pair__(2,3) returns u"2/3"
#whereas      __number_pair__(4,0) returns u"4"
def __number_pair__(current, total):
    from . import config

    if (config.getboolean_default("ID3", "pad", False)):
        unslashed_format = u"%2.2d"
        slashed_format = u"%2.2d/%2.2d"
    else:
        unslashed_format = u"%d"
        slashed_format = u"%d/%d"

    if (current is None):
        if (total is None):
            return unslashed_format % (0,)
        else:
            return slashed_format % (0, total)
    else:  # current is not None
        if (total is None):
            return unslashed_format % (current,)
        else:
            return slashed_format % (current, total)


def read_id3v2_comment(filename):
    """given a filename, returns an ID3v22Comment or a subclass

    for example, if the file is ID3v2.3 tagged,
    this returns an ID3v23Comment
    """

    from .bitstream import BitstreamReader

    reader = BitstreamReader(file(filename, "rb"), 0)
    reader.mark()
    try:
        (tag, version_major, version_minor) = reader.parse("3b 8u 8u")
        if (tag != 'ID3'):
            raise ValueError("invalid ID3 header")
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
            raise ValueError("unsupported ID3 version")
    finally:
        reader.unmark()
        reader.close()


def skip_id3v2_comment(file):
    """seeks past an ID3v2 comment if found in the file stream
    returns the number of bytes skipped"""

    from .bitstream import BitstreamReader

    reader = BitstreamReader(file, 0)
    reader.mark()
    try:
        (tag_id, version_major, version_minor) = reader.parse("3b 8u 8u 8p")
        bytes_skipped = 6
    except IOError, err:
        reader.unmark()
        raise err

    if ((tag_id == 'ID3') and (version_major in (2, 3, 4))):
        reader.unmark()

        #parse the header
        tag_size = decode_syncsafe32(reader.read(32))
        bytes_skipped += 4

        #skip to the end of its length
        reader.skip_bytes(tag_size)
        bytes_skipped += tag_size

        #check for additional ID3v2 tags recursively
        del(reader)
        return bytes_skipped + skip_id3v2_comment(file)
    else:
        reader.rewind()
        reader.unmark()
        return 0


def total_id3v2_comments(file):
    """returns the number of nested ID3v2 comments found in the file stream"""

    from .bitstream import BitstreamReader

    reader = BitstreamReader(file, 0)
    reader.mark()
    try:
        (tag_id, version_major, version_minor) = reader.parse("3b 8u 8u 8p")
    except IOError, err:
        reader.unmark()
        raise err

    if ((tag_id == 'ID3') and (version_major in (2, 3, 4))):
        reader.unmark()

        #parse the header
        tag_size = decode_syncsafe32(reader.read(32))

        #skip to the end of its length
        reader.skip_bytes(tag_size)

        #check for additional ID3v2 tags recursively
        del(reader)
        return 1 + total_id3v2_comments(file)
    else:
        reader.rewind()
        reader.unmark()
        return 0

############################################################
# ID3v2.2 Comment
############################################################


class ID3v22_Frame:
    def __init__(self, frame_id, data):
        self.id = frame_id
        self.data = data

    def copy(self):
        return self.__class__(self.id, self.data)

    def __repr__(self):
        return "ID3v22_Frame(%s, %s)" % (repr(self.id), repr(self.data))

    def raw_info(self):
        if (len(self.data) > 20):
            return u"%s = %s\u2026" % \
                (self.id.decode('ascii', 'replace'),
                 u"".join([u"%2.2X" % (ord(b)) for b in self.data[0:20]]))
        else:
            return u"%s = %s" % \
                (self.id.decode('ascii', 'replace'),
                 u"".join([u"%2.2X" % (ord(b)) for b in self.data]))

    def __eq__(self, frame):
        return __attrib_equals__(["id", "data"], self, frame)

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed ID3v2?_Frame"""

        return cls(frame_id, reader.read_bytes(frame_size))

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return len(self.data)

    @classmethod
    def converted(cls, frame_id, o):
        """given foreign data, returns an ID3v22_Frame"""

        raise NotImplementedError()

    def clean(self):
        """returns a cleaned ID3v22_Frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        return (self.__class__(self.id, self.data), [])


class ID3v22_T__Frame:
    NUMERICAL_IDS = ('TRK', 'TPA')

    def __init__(self, frame_id, encoding, data):
        """fields are as follows:
        | frame_id | 3 byte frame ID string  |
        | encoding | 1 byte encoding int     |
        | data     | text data as raw string |
        """

        assert((encoding == 0) or (encoding == 1))

        self.id = frame_id
        self.encoding = encoding
        self.data = data

    def copy(self):
        return self.__class__(self.id, self.encoding, self.data)

    def __repr__(self):
        return "ID3v22_T__Frame(%s, %s, %s)" % \
            (repr(self.id), repr(self.encoding), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s) %s" % \
            (self.id.decode('ascii'),
             {0: u"Latin-1", 1: u"UCS-2"}[self.encoding],
             unicode(self))

    def __eq__(self, frame):
        return __attrib_equals__(["id", "encoding", "data"], self, frame)

    def __unicode__(self):
        return self.data.decode(
            {0: 'latin-1', 1: 'ucs2'}[self.encoding],
            'replace').split(unichr(0), 1)[0]

    def number(self):
        """if the frame is numerical, returns the track/album_number portion
        raises TypeError if not"""

        import re

        if (self.id in self.NUMERICAL_IDS):
            unicode_value = unicode(self)
            int_string = re.search(r'\d+', unicode_value)
            if (int_string is not None):
                int_value = int(int_string.group(0))
                if (int_value == 0):
                    total_string = re.search(r'/\D*?(\d+)', unicode_value)
                    if (total_string is not None):
                        #don't return placeholder 0 value
                        #when a track_total value is present
                        #but track_number value is 0
                        return None
                    else:
                        return int_value
                else:
                    return int_value
            else:
                return None
        else:
            raise TypeError()

    def total(self):
        """if the frame is numerical, returns the track/album_total portion
        raises TypeError if not"""

        import re

        if (self.id in self.NUMERICAL_IDS):
            int_value = re.search(r'/\D*?(\d+)', unicode(self))
            if (int_value is not None):
                return int(int_value.group(1))
            else:
                return None
        else:
            raise TypeError()

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed text frame"""

        encoding = reader.read(8)
        return cls(frame_id, encoding, reader.read_bytes(frame_size - 1))

    def build(self, writer):
        """writes the frame's data to the BitstreamWriter
        not including its frame header"""

        writer.build("8u %db" % (len(self.data)), (self.encoding, self.data))

    def size(self):
        """returns the frame's total size
        not including its frame header"""

        return 1 + len(self.data)

    @classmethod
    def converted(cls, frame_id, unicode_string):
        """given a unicode string, returns a text frame"""

        if (is_latin_1(unicode_string)):
            return cls(frame_id, 0, unicode_string.encode('latin-1'))
        else:
            return cls(frame_id, 1, unicode_string.encode('ucs2'))

    def clean(self):
        """returns a cleaned frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        from .text import (CLEAN_REMOVE_EMPTY_TAG,
                           CLEAN_REMOVE_TRAILING_WHITESPACE,
                           CLEAN_REMOVE_LEADING_WHITESPACE,
                           CLEAN_REMOVE_LEADING_ZEROES,
                           CLEAN_ADD_LEADING_ZEROES)

        fixes_performed = []
        field = self.id.decode('ascii')
        value = unicode(self)

        #check for an empty tag
        if (len(value.strip()) == 0):
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        #check trailing whitespace
        fix1 = value.rstrip()
        if (fix1 != value):
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        #check leading whitespace
        fix2 = fix1.lstrip()
        if (fix2 != fix1):
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        #check leading zeroes for a numerical tag
        if (self.id in self.NUMERICAL_IDS):
            fix3 = __number_pair__(self.number(), self.total())
            if (fix3 != fix2):
                from . import config

                if (config.getboolean_default("ID3", "pad", False)):
                    fixes_performed.append(CLEAN_ADD_LEADING_ZEROES %
                                           {"field": field})
                else:
                    fixes_performed.append(CLEAN_REMOVE_LEADING_ZEROES %
                                           {"field": field})
        else:
            fix3 = fix2

        return (self.__class__.converted(self.id, fix3), fixes_performed)


class ID3v22_TXX_Frame:
    def __init__(self, encoding, description, data):
        self.id = 'TXX'

        self.encoding = encoding
        self.description = description
        self.data = data

    def copy(self):
        return self.__class__(self.encoding,
                              self.description,
                              self.data)

    def __repr__(self):
        return "ID3v22_TXX_Frame(%s, %s, %s)" % \
            (repr(self.encoding), repr(self.description), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s, \"%s\") %s" % \
            (self.id,
             {0: u"Latin-1", 1: u"UCS-2"}[self.encoding],
             self.description,
             unicode(self))

    def __eq__(self, frame):
        return __attrib_equals__(["id", "encoding", "description", "data"])

    def __unicode__(self):
        return self.data.decode(
            {0: 'latin-1', 1: 'ucs2'}[self.encoding],
            'replace').split(unichr(0), 1)[0]

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed text frame"""

        encoding = reader.read(8)
        description = C_string.parse({0: "latin-1", 1: "ucs2"}[encoding],
                                     reader)
        data = reader.read_bytes(frame_size - 1 - description.size())

        return cls(encoding, description, data)

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.write(8, self.encoding)
        self.description.build(writer)
        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return 1 + self.description.size() + len(self.data)

    def clean(self):
        """returns a cleaned frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        from audiotools.text import (CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE)

        fixes_performed = []
        field = self.id.decode('ascii')
        value = unicode(self)

        #check for an empty tag
        if (len(value.strip()) == 0):
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        #check trailing whitespace
        fix1 = value.rstrip()
        if (fix1 != value):
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        #check leading whitespace
        fix2 = fix1.lstrip()
        if (fix2 != fix1):
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        return (self.__class__(self.encoding, self.description, fix2),
                fixes_performed)


class ID3v22_W__Frame:
    def __init__(self, frame_id, data):
        self.id = frame_id
        self.data = data

    def copy(self):
        return self.__class__(self.id, self.data)

    def __repr__(self):
        return "ID3v22_W__Frame(%s, %s)" % \
            (repr(self.id), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = %s" % (self.id.decode('ascii'),
                             self.data.decode('ascii', 'replace'))

    def __eq__(self, frame):
        return __attrib_equals__(["id", "data"], self, frame)

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        return cls(frame_id, reader.read_bytes(frame_size))

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return len(self.data)

    def clean(self):
        """returns a cleaned frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        return (self.__class__(self.id, self.data), [])


class ID3v22_WXX_Frame:
    def __init__(self, encoding, description, data):
        self.id = 'WXX'

        self.encoding = encoding
        self.description = description
        self.data = data

    def copy(self):
        return self.__class__(self.encoding,
                              self.description,
                              self.data)

    def __repr__(self):
        return "ID3v22_WXX_Frame(%s, %s, %s)" % \
            (repr(self.encoding), repr(self.description), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s, \"%s\") %s" % \
            (self.id,
             {0: u"Latin-1", 1: u"UCS-2"}[self.encoding],
             self.description,
             self.data.decode('ascii', 'replace'))

    def __eq__(self, frame):
        return __attrib_equals__(["id", "encoding", "description", "data"])

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed text frame"""

        encoding = reader.read(8)
        description = C_string.parse({0: "latin-1", 1: "ucs2"}[encoding],
                                     reader)
        data = reader.read_bytes(frame_size - 1 - description.size())

        return cls(encoding, description, data)

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.write(8, self.encoding)
        self.description.build(writer)
        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return 1 + self.description.size() + len(self.data)

    def clean(self):
        """returns a cleaned frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        return (self.__class__(self.encoding,
                               self.description,
                               self.data), [])


class ID3v22_COM_Frame:
    def __init__(self, encoding, language, short_description, data):
        """fields are as follows:
        | encoding          | 1 byte int of the comment's text encoding |
        | language          | 3 byte string of the comment's language   |
        | short_description | C_string of a short description           |
        | data              | plain string of the comment data itself   |
        """

        self.id = "COM"
        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.data = data

    def copy(self):
        return self.__class__(self.encoding,
                              self.language,
                              self.short_description,
                              self.data)

    def __repr__(self):
        return "ID3v22_COM_Frame(%s, %s, %s, %s)" % \
            (repr(self.encoding), repr(self.language),
             repr(self.short_description), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"COM = (%s, %s, \"%s\") %s" % \
            ({0: u'Latin-1', 1: 'UCS-2'}[self.encoding],
             self.language.decode('ascii', 'replace'),
             self.short_description,
             self.data.decode({0: 'latin-1', 1: 'ucs2'}[self.encoding]))

    def __eq__(self, frame):
        return __attrib_equals__(["encoding",
                                  "language",
                                  "short_description",
                                  "data"], self, frame)

    def __unicode__(self):
        return self.data.decode({0: 'latin-1', 1: 'ucs2'}[self.encoding],
                                'replace')

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed ID3v22_COM_Frame"""

        (encoding, language) = reader.parse("8u 3b")
        short_description = C_string.parse({0: 'latin-1', 1: 'ucs2'}[encoding],
                                           reader)
        data = reader.read_bytes(frame_size - (4 + short_description.size()))

        return cls(encoding, language, short_description, data)

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.build("8u 3b", (self.encoding, self.language))
        self.short_description.build(writer)
        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return 4 + self.short_description.size() + len(self.data)

    @classmethod
    def converted(cls, frame_id, unicode_string):
        if (is_latin_1(unicode_string)):
            return cls(0, "eng", C_string("latin-1", u""),
                       unicode_string.encode('latin-1'))
        else:
            return cls(1, "eng", C_string("ucs2", u""),
                       unicode_string.encode('ucs2'))

    def clean(self):
        """returns a cleaned frame of the same class
        or None if the frame should be omitted
        fix text will be appended to fixes_performed, if necessary"""

        from audiotools.text import (CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE)

        fixes_performed = []
        field = self.id.decode('ascii')
        text_encoding = {0: 'latin-1', 1: 'ucs2'}

        value = self.data.decode(text_encoding[self.encoding], 'replace')

        #check for an empty tag
        if (len(value.strip()) == 0):
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        #check trailing whitespace
        fix1 = value.rstrip()
        if (fix1 != value):
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        #check leading whitespace
        fix2 = fix1.lstrip()
        if (fix2 != fix1):
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        #stripping whitespace shouldn't alter text/description encoding

        return (self.__class__(self.encoding,
                               self.language,
                               self.short_description,
                               fix2.encode(text_encoding[self.encoding])),
                fixes_performed)


class ID3v22_PIC_Frame(Image):
    def __init__(self, image_format, picture_type, description, data):
        """fields are as follows:
        | image_format | a 3 byte image format, such as 'JPG'        |
        | picture_type | a 1 byte field indicating front cover, etc. |
        | description  | a description of the image as a C_string    |
        | data         | image data itself as a raw string           |
        """

        self.id = 'PIC'

        #add PIC-specific fields
        self.pic_format = image_format
        self.pic_type = picture_type
        self.pic_description = description

        #figure out image metrics from raw data
        try:
            metrics = Image.new(data, u'', 0)
        except InvalidImage:
            metrics = Image(data=data, mime_type=u'',
                            width=0, height=0, color_depth=0, color_count=0,
                            description=u'', type=0)

        #then initialize Image parent fields from metrics
        self.mime_type = metrics.mime_type
        self.width = metrics.width
        self.height = metrics.height
        self.color_depth = metrics.color_depth
        self.color_count = metrics.color_count
        self.data = data

    def copy(self):
        return ID3v22_PIC_Frame(self.pic_format,
                                self.pic_type,
                                self.pic_description,
                                self.data)

    def __repr__(self):
        return "ID3v22_PIC_Frame(%s, %s, %s, ...)" % \
            (repr(self.pic_format), repr(self.pic_type),
             repr(self.pic_description))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"PIC = (%s, %d\u00D7%d, %s, \"%s\") %d bytes" % \
            (self.type_string(),
             self.width,
             self.height,
             self.mime_type,
             self.pic_description,
             len(self.data))

    def type_string(self):
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

    def __getattr__(self, attr):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)

        if (attr == 'type'):
            return {3: FRONT_COVER,
                    4: BACK_COVER,
                    5: LEAFLET_PAGE,
                    6: MEDIA
                    }.get(self.pic_type, OTHER)
        elif (attr == 'description'):
            return unicode(self.pic_description)
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)
        if (attr == 'type'):
            self.__dict__["pic_type"] = {FRONT_COVER: 3,
                                         BACK_COVER: 4,
                                         LEAFLET_PAGE: 5,
                                         MEDIA: 6
                                         }.get(value, 0)  # other
        elif (attr == 'description'):
            if (is_latin_1(value)):
                self.__dict__["pic_description"] = C_string('latin-1', value)
            else:
                self.__dict__["pic_description"] = C_string('ucs2', value)
        else:
            self.__dict__[attr] = value

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        (encoding, image_format, picture_type) = reader.parse("8u 3b 8u")
        description = C_string.parse({0: 'latin-1',
                                      1: 'ucs2'}[encoding], reader)
        data = reader.read_bytes(frame_size - (5 + description.size()))
        return cls(image_format,
                   picture_type,
                   description,
                   data)

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.build("8u 3b 8u", ({'latin-1': 0,
                                   'ucs2': 1}[self.pic_description.encoding],
                                  self.pic_format,
                                  self.pic_type))
        self.pic_description.build(writer)
        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return (5 + self.pic_description.size() + len(self.data))

    @classmethod
    def converted(cls, frame_id, image):
        if (is_latin_1(image.description)):
            description = C_string('latin-1', image.description)
        else:
            description = C_string('ucs2', image.description)

        return cls(image_format={u"image/png": u"PNG",
                                 u"image/jpeg": u"JPG",
                                 u"image/jpg": u"JPG",
                                 u"image/x-ms-bmp": u"BMP",
                                 u"image/gif": u"GIF",
                                 u"image/tiff": u"TIF"}.get(image.mime_type,
                                                            'UNK'),
                   picture_type={0: 3,                   # front cover
                                 1: 4,                   # back cover
                                 2: 5,                   # leaflet page
                                 3: 6,                   # media
                                 }.get(image.type, 0),   # other
                   description=description,
                   data=image.data)

    def clean(self):
        """returns a cleaned ID3v22_PIC_Frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        #all the fields are derived from the image data
        #so there's no need to test for a mismatch

        #not sure if it's worth testing for bugs in the description
        #or format fields

        return (ID3v22_PIC_Frame(self.pic_format,
                                 self.pic_type,
                                 self.pic_description,
                                 self.data), [])


class ID3v22Comment(MetaData):
    NAME = u'ID3v2.2'

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

    RAW_FRAME = ID3v22_Frame
    TEXT_FRAME = ID3v22_T__Frame
    USER_TEXT_FRAME = ID3v22_TXX_Frame
    WEB_FRAME = ID3v22_W__Frame
    USER_WEB_FRAME = ID3v22_WXX_Frame
    COMMENT_FRAME = ID3v22_COM_Frame
    IMAGE_FRAME = ID3v22_PIC_Frame
    IMAGE_FRAME_ID = 'PIC'

    def __init__(self, frames, total_size=None):
        self.__dict__["frames"] = frames[:]
        self.__dict__["total_size"] = total_size

    def copy(self):
        return self.__class__([frame.copy() for frame in self])

    def __repr__(self):
        return "ID3v22Comment(%s, %s)" % (repr(self.frames),
                                          repr(self.total_size))

    def __iter__(self):
        return iter(self.frames)

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        from os import linesep

        return linesep.decode('ascii').join(
            ["%s:" % (self.NAME)] +
            [frame.raw_info() for frame in self])

    @classmethod
    def parse(cls, reader):
        """given a BitstreamReader, returns a parsed ID3v22Comment"""

        (id3,
         major_version,
         minor_version,
         flags) = reader.parse("3b 8u 8u 8u")
        if (id3 != 'ID3'):
            raise ValueError("invalid ID3 header")
        elif (major_version != 0x02):
            raise ValueError("invalid major version")
        elif (minor_version != 0x00):
            raise ValueError("invalid minor version")
        total_size = remaining_size = decode_syncsafe32(reader.read(32))

        frames = []

        while (remaining_size > 6):
            (frame_id, frame_size) = reader.parse("3b 24u")

            if (frame_id == chr(0) * 3):
                break
            elif (frame_id == 'TXX'):
                frames.append(
                    cls.USER_TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'WXX'):
                frames.append(
                    cls.USER_WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'COM'):
                frames.append(
                    cls.COMMENT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'PIC'):
                frames.append(
                    cls.IMAGE_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id.startswith('T')):
                frames.append(
                    cls.TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id.startswith('W')):
                frames.append(
                    cls.WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            else:
                frames.append(
                    cls.RAW_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))

            remaining_size -= (6 + frame_size)

        return cls(frames, total_size)

    def build(self, writer):
        """writes the complete ID3v22Comment data
        to the given BitstreamWriter"""

        tags_size = sum([6 + frame.size() for frame in self])

        writer.build("3b 8u 8u 8u 32u",
                     ("ID3", 0x02, 0x00, 0x00,
                      encode_syncsafe32(max(tags_size, self.total_size))))

        for frame in self:
            writer.build("3b 24u", (frame.id, frame.size()))
            frame.build(writer)

        #add buffer of NULL bytes if the total size of the tags
        #is less than the total size of the whole ID3v2.2 tag
        if ((self.total_size is not None) and
            ((self.total_size - tags_size) > 0)):
            writer.write_bytes(chr(0) * (self.total_size - tags_size))

    def size(self):
        """returns the total size of the ID3v22Comment, including its header"""

        return 10 + max(sum([6 + frame.size() for frame in self]),
                        self.total_size)

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, frame_id):
        frames = [frame for frame in self if (frame.id == frame_id)]
        if (len(frames) > 0):
            return frames
        else:
            raise KeyError(frame_id)

    def __setitem__(self, frame_id, frames):
        new_frames = frames[:]
        updated_frames = []

        for old_frame in self:
            if (old_frame.id == frame_id):
                try:
                    #replace current frame with newly set frame
                    updated_frames.append(new_frames.pop(0))
                except IndexError:
                    #no more newly set frames, so remove current frame
                    continue
            else:
                #passthrough unmatched frames
                updated_frames.append(old_frame)
        else:
            #append any leftover frames
            for new_frame in new_frames:
                updated_frames.append(new_frame)

        self.__dict__["frames"] = updated_frames

    def __delitem__(self, frame_id):
        updated_frames = [frame for frame in self if frame.id != frame_id]
        if (len(updated_frames) < len(self)):
            self.__dict__["frames"] = updated_frames
        else:
            raise KeyError(frame_id)

    def keys(self):
        return list(set([frame.id for frame in self]))

    def values(self):
        return [self[key] for key in self.keys()]

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def __getattr__(self, attr):
        if (attr in self.ATTRIBUTE_MAP):
            try:
                frame = self[self.ATTRIBUTE_MAP[attr]][0]
                if (attr in ('track_number', 'album_number')):
                    return frame.number()
                elif (attr in ('track_total', 'album_total')):
                    return frame.total()
                else:
                    return unicode(frame)
            except KeyError:
                return None
        elif (attr in self.FIELDS):
            return None
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if (attr in self.ATTRIBUTE_MAP):
            if (value is not None):
                import re

                frame_id = self.ATTRIBUTE_MAP[attr]
                if (attr == 'track_number'):
                    try:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            re.sub(r'\d+',
                                   unicode(int(value)),
                                   unicode(self[frame_id][0]),
                                   1))
                    except KeyError:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            __number_pair__(value, self.track_total))
                elif (attr == 'track_total'):
                    try:
                        if (re.search(r'/\D*\d+',
                                      unicode(self[frame_id][0])) is not None):
                            new_frame = self.TEXT_FRAME.converted(
                                frame_id,
                                re.sub(r'(/\D*)(\d+)',
                                       u"\\g<1>" + unicode(int(value)),
                                       unicode(self[frame_id][0]),
                                       1))
                        else:
                            new_frame = self.TEXT_FRAME.converted(
                                frame_id,
                                u"%s/%d" % (unicode(self[frame_id][0]),
                                            int(value)))
                    except KeyError:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            __number_pair__(self.track_number, value))
                elif (attr == 'album_number'):
                    try:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            re.sub(r'\d+',
                                   unicode(int(value)),
                                   unicode(self[frame_id][0]),
                                   1))
                    except KeyError:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            __number_pair__(value, self.album_total))
                elif (attr == 'album_total'):
                    try:
                        if (re.search(r'/\D*\d+',
                                      unicode(self[frame_id][0])) is not None):
                            new_frame = self.TEXT_FRAME.converted(
                                frame_id,
                                re.sub(r'(/\D*)(\d+)',
                                       u"\\g<1>" + unicode(int(value)),
                                       unicode(self[frame_id][0]),
                                       1))
                        else:
                            new_frame = self.TEXT_FRAME.converted(
                                frame_id,
                                u"%s/%d" % (unicode(self[frame_id][0]),
                                            int(value)))
                    except KeyError:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            __number_pair__(self.album_number, value))
                elif (attr == 'comment'):
                    new_frame = self.COMMENT_FRAME.converted(
                        frame_id, value)
                else:
                    new_frame = self.TEXT_FRAME.converted(
                        frame_id, unicode(value))

                try:
                    self[frame_id] = [new_frame] + self[frame_id][1:]
                except KeyError:
                    self[frame_id] = [new_frame]
            else:
                delattr(self, attr)
        elif (attr in MetaData.FIELDS):
            pass
        else:
            self.__dict__[attr] = value

    def __delattr__(self, attr):
        if (attr in self.ATTRIBUTE_MAP):
            updated_frames = []
            delete_frame_id = self.ATTRIBUTE_MAP[attr]
            for frame in self:
                if (frame.id == delete_frame_id):
                    if ((attr == 'track_number') or (attr == 'album_number')):
                        import re

                        #if *_number field contains a slashed total
                        if (re.search(r'\d+.*?/.*?\d+',
                                      unicode(frame)) is not None):
                            #replace unslashed portion with 0
                            updated_frames.append(
                                self.TEXT_FRAME.converted(
                                    frame.id,
                                    re.sub(r'\d+',
                                           unicode(int(0)),
                                           unicode(frame),
                                           1)))
                        else:
                            #otherwise, remove *_number field
                            continue
                    elif ((attr == 'track_total') or
                          (attr == 'album_total')):
                        import re

                        #if *_number is nonzero
                        _number = re.search(r'\d+',
                                            unicode(frame).split(u"/")[0])
                        if (((_number is not None) and
                             (int(_number.group(0)) != 0))):
                            #if field contains a slashed total
                            #remove slashed total from field
                            updated_frames.append(
                                self.TEXT_FRAME.converted(
                                    frame.id,
                                    re.sub(r'\s*/\D*\d+.*',
                                           u"",
                                           unicode(frame),
                                           1)))
                        else:
                            #if field contains a slashed total
                            #remove field entirely
                            if (re.search(r'/.*?\d+',
                                          unicode(frame)) is not None):
                                continue
                            else:
                                #no number or total,
                                #so pass frame through unchanged
                                updated_frames.append(frame)
                    else:
                        #handle the textual fields
                        #which are simply deleted outright
                        continue
                else:
                    updated_frames.append(frame)

            self.__dict__["frames"] = updated_frames

        elif (attr in MetaData.FIELDS):
            #ignore deleted attributes which are in MetaData
            #but we don't support
            pass
        else:
            try:
                del(self.__dict__[attr])
            except KeyError:
                raise AttributeError(attr)

    def images(self):
        return [frame for frame in self if (frame.id == self.IMAGE_FRAME_ID)]

    def add_image(self, image):
        self.frames.append(
            self.IMAGE_FRAME.converted(self.IMAGE_FRAME_ID, image))

    def delete_image(self, image):
        self.__dict__["frames"] = [frame for frame in self if
                                   ((frame.id != self.IMAGE_FRAME_ID) or
                                    (frame != image))]

    @classmethod
    def converted(cls, metadata):
        """converts a MetaData object to an ID3v2*Comment object"""

        if (metadata is None):
            return None
        elif (cls is metadata.__class__):
            return cls([frame.copy() for frame in metadata])

        frames = []

        for (attr, key) in cls.ATTRIBUTE_MAP.items():
            value = getattr(metadata, attr)
            if ((attr not in cls.INTEGER_FIELDS) and (value is not None)):
                if (attr == 'comment'):
                    frames.append(cls.COMMENT_FRAME.converted(key, value))
                else:
                    frames.append(cls.TEXT_FRAME.converted(key, value))

        if (((metadata.track_number is not None) or
             (metadata.track_total is not None))):
            frames.append(
                cls.TEXT_FRAME.converted(
                    cls.ATTRIBUTE_MAP["track_number"],
                    __number_pair__(metadata.track_number,
                                    metadata.track_total)))

        if (((metadata.album_number is not None) or
             (metadata.album_total is not None))):
            frames.append(
                cls.TEXT_FRAME.converted(
                    cls.ATTRIBUTE_MAP["album_number"],
                    __number_pair__(metadata.album_number,
                                    metadata.album_total)))

        for image in metadata.images():
            frames.append(cls.IMAGE_FRAME.converted(cls.IMAGE_FRAME_ID, image))

        if (hasattr(cls, 'ITUNES_COMPILATION_ID')):
            frames.append(
                cls.TEXT_FRAME.converted(
                    cls.ITUNES_COMPILATION_ID, u'1'))

        return cls(frames)

    def clean(self):
        """returns a new MetaData object that's been cleaned of problems"""

        new_frames = []
        fixes_performed = []

        for frame in self:
            (filtered_frame, frame_fixes) = frame.clean()
            if (filtered_frame is not None):
                new_frames.append(filtered_frame)
            fixes_performed.extend(frame_fixes)

        return (self.__class__(new_frames, self.total_size), fixes_performed)


############################################################
# ID3v2.3 Comment
############################################################


class ID3v23_Frame(ID3v22_Frame):
    def __repr__(self):
        return "ID3v23_Frame(%s, %s)" % (repr(self.id), repr(self.data))


class ID3v23_T___Frame(ID3v22_T__Frame):
    NUMERICAL_IDS = ('TRCK', 'TPOS')

    def __repr__(self):
        return "ID3v23_T___Frame(%s, %s, %s)" % \
            (repr(self.id), repr(self.encoding), repr(self.data))


class ID3v23_TXXX_Frame(ID3v22_TXX_Frame):
    def __init__(self, encoding, description, data):
        self.id = 'TXXX'

        self.encoding = encoding
        self.description = description
        self.data = data

    def __repr__(self):
        return "ID3v23_TXXX_Frame(%s, %s, %s)" % \
            (repr(self.encoding), repr(self.description), repr(self.data))


class ID3v23_W___Frame(ID3v22_W__Frame):
    def __repr__(self):
        return "ID3v23_W___Frame(%s, %s)" % \
            (repr(self.id), repr(self.data))


class ID3v23_WXXX_Frame(ID3v22_WXX_Frame):
    def __init__(self, encoding, description, data):
        self.id = 'WXXX'

        self.encoding = encoding
        self.description = description
        self.data = data

    def __repr__(self):
        return "ID3v23_WXXX_Frame(%s, %s, %s)" % \
            (repr(self.encoding), repr(self.description), repr(self.data))


class ID3v23_APIC_Frame(ID3v22_PIC_Frame):
    def __init__(self, mime_type, picture_type, description, data):
        """fields are as follows:
        | mime_type    | a C_string of the image's MIME type         |
        | picture_type | a 1 byte field indicating front cover, etc. |
        | description  | a description of the image as a C_string    |
        | data         | image data itself as a raw string           |
        """

        self.id = 'APIC'

        #add APIC-specific fields
        self.pic_type = picture_type
        self.pic_description = description
        self.pic_mime_type = mime_type

        #figure out image metrics from raw data
        try:
            metrics = Image.new(data, u'', 0)
        except InvalidImage:
            metrics = Image(data=data, mime_type=u'',
                            width=0, height=0, color_depth=0, color_count=0,
                            description=u'', type=0)

        #then initialize Image parent fields from metrics
        self.width = metrics.width
        self.height = metrics.height
        self.color_depth = metrics.color_depth
        self.color_count = metrics.color_count
        self.data = data

    def copy(self):
        return self.__class__(self.pic_mime_type,
                              self.pic_type,
                              self.pic_description,
                              self.data)

    def __repr__(self):
        return "ID3v23_APIC_Frame(%s, %s, %s, ...)" % \
            (repr(self.pic_mime_type), repr(self.pic_type),
             repr(self.pic_description))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"APIC = (%s, %d\u00D7%d, %s, \"%s\") %d bytes" % \
            (self.type_string(),
             self.width,
             self.height,
             self.pic_mime_type,
             self.pic_description,
             len(self.data))

    def __getattr__(self, attr):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)

        if (attr == 'type'):
            return {3: FRONT_COVER,
                    4: BACK_COVER,
                    5: LEAFLET_PAGE,
                    6: MEDIA
                    }.get(self.pic_type, 4)  # other
        elif (attr == 'description'):
            return unicode(self.pic_description)
        elif (attr == 'mime_type'):
            return unicode(self.pic_mime_type)
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)

        if (attr == 'type'):
            self.__dict__["pic_type"] = {FRONT_COVER: 3,
                                         BACK_COVER: 4,
                                         LEAFLET_PAGE: 5,
                                         MEDIA: 6
                                         }.get(value, 0)  # other
        elif (attr == 'description'):
            if (is_latin_1(value)):
                self.__dict__["pic_description"] = C_string('latin-1', value)
            else:
                self.__dict__["pic_description"] = C_string('ucs2', value)
        elif (attr == 'mime_type'):
            self.__dict__["pic_mime_type"] = C_string('ascii', value)
        else:
            self.__dict__[attr] = value

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """parses this frame from the given BitstreamReader"""

        encoding = reader.read(8)
        mime_type = C_string.parse('ascii', reader)
        picture_type = reader.read(8)
        description = C_string.parse({0: 'latin-1',
                                      1: 'ucs2'}[encoding], reader)
        data = reader.read_bytes(frame_size - (1 +
                                               mime_type.size() +
                                               1 +
                                               description.size()))

        return cls(mime_type, picture_type, description, data)

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.write(8, {'latin-1': 0,
                         'ucs2': 1}[self.pic_description.encoding])
        self.pic_mime_type.build(writer)
        writer.write(8, self.pic_type)
        self.pic_description.build(writer)
        writer.write_bytes(self.data)

    def size(self):
        """returns the size of this frame in bytes
        not including the frame header"""

        return (1 +
                self.pic_mime_type.size() +
                1 +
                self.pic_description.size() +
                len(self.data))

    @classmethod
    def converted(cls, frame_id, image):
        if (is_latin_1(image.description)):
            description = C_string('latin-1', image.description)
        else:
            description = C_string('ucs2', image.description)

        return cls(mime_type=C_string('ascii', image.mime_type),
                   picture_type={0: 3,                   # front cover
                                 1: 4,                   # back cover
                                 2: 5,                   # leaflet page
                                 3: 6,                   # media
                                 }.get(image.type, 0),   # other
                   description=description,
                   data=image.data)

    def clean(self):
        """returns a cleaned ID3v23_APIC_Frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        actual_mime_type = Image.new(self.data, u"", 0).mime_type
        if (unicode(self.pic_mime_type) != actual_mime_type):
            from audiotools.text import (CLEAN_FIX_IMAGE_FIELDS)
            return (ID3v23_APIC_Frame(
                C_string('ascii', actual_mime_type.encode('ascii')),
                self.pic_type,
                self.pic_description,
                self.data), [CLEAN_FIX_IMAGE_FIELDS])
        else:
            return (ID3v23_APIC_Frame(
                self.pic_mime_type,
                self.pic_type,
                self.pic_description,
                self.data), [])


class ID3v23_COMM_Frame(ID3v22_COM_Frame):
    def __init__(self, encoding, language, short_description, data):
        """fields are as follows:
        | encoding          | 1 byte int of the comment's text encoding |
        | language          | 3 byte string of the comment's language   |
        | short_description | C_string of a short description           |
        | data              | plain string of the comment data itself   |
        """

        self.id = "COMM"
        self.encoding = encoding
        self.language = language
        self.short_description = short_description
        self.data = data

    def __repr__(self):
        return "ID3v23_COMM_Frame(%s, %s, %s, %s)" % \
            (repr(self.encoding), repr(self.language),
             repr(self.short_description), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"COMM = (%s, %s, \"%s\") %s" % \
            ({0: u'Latin-1', 1: 'UCS-2'}[self.encoding],
             self.language.decode('ascii', 'replace'),
             self.short_description,
             self.data.decode({0: 'latin-1', 1: 'ucs2'}[self.encoding]))


class ID3v23Comment(ID3v22Comment):
    NAME = u'ID3v2.3'

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

    RAW_FRAME = ID3v23_Frame
    TEXT_FRAME = ID3v23_T___Frame
    WEB_FRAME = ID3v23_W___Frame
    USER_TEXT_FRAME = ID3v23_TXXX_Frame
    USER_WEB_FRAME = ID3v23_WXXX_Frame
    COMMENT_FRAME = ID3v23_COMM_Frame
    IMAGE_FRAME = ID3v23_APIC_Frame
    IMAGE_FRAME_ID = 'APIC'
    ITUNES_COMPILATION_ID = 'TCMP'

    def __repr__(self):
        return "ID3v23Comment(%s, %s)" % (repr(self.frames),
                                          repr(self.total_size))

    @classmethod
    def parse(cls, reader):
        """given a BitstreamReader, returns a parsed ID3v23Comment"""

        (id3,
         major_version,
         minor_version,
         flags) = reader.parse("3b 8u 8u 8u")
        if (id3 != 'ID3'):
            raise ValueError("invalid ID3 header")
        elif (major_version != 0x03):
            raise ValueError("invalid major version")
        elif (minor_version != 0x00):
            raise ValueError("invalid minor version")
        total_size = remaining_size = decode_syncsafe32(reader.read(32))

        frames = []

        while (remaining_size > 10):
            (frame_id, frame_size, frame_flags) = reader.parse("4b 32u 16u")

            if (frame_id == chr(0) * 4):
                break
            elif (frame_id == 'TXXX'):
                frames.append(
                    cls.USER_TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'WXXX'):
                frames.append(
                    cls.USER_WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'COMM'):
                frames.append(
                    cls.COMMENT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'APIC'):
                frames.append(
                    cls.IMAGE_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id.startswith('T')):
                frames.append(
                    cls.TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id.startswith('W')):
                frames.append(
                    cls.WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            else:
                frames.append(
                    cls.RAW_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))

            remaining_size -= (10 + frame_size)

        return cls(frames, total_size)

    def build(self, writer):
        """writes the complete ID3v23Comment data
        to the given BitstreamWriter"""

        tags_size = sum([10 + frame.size() for frame in self])

        writer.build("3b 8u 8u 8u 32u",
                     ("ID3", 0x03, 0x00, 0x00,
                      encode_syncsafe32(max(tags_size, self.total_size))))

        for frame in self:
            writer.build("4b 32u 16u", (frame.id, frame.size(), 0))
            frame.build(writer)

        #add buffer of NULL bytes if the total size of the tags
        #is less than the total size of the whole ID3v2.3 tag
        if ((self.total_size is not None) and
            ((self.total_size - tags_size) > 0)):
            writer.write_bytes(chr(0) * (self.total_size - tags_size))

    def size(self):
        """returns the total size of the ID3v23Comment, including its header"""

        return 10 + max(sum([10 + frame.size() for frame in self]),
                        self.total_size)


############################################################
# ID3v2.4 Comment
############################################################


class ID3v24_Frame(ID3v23_Frame):
    def __repr__(self):
        return "ID3v24_Frame(%s, %s)" % (repr(self.id), repr(self.data))


class ID3v24_T___Frame(ID3v23_T___Frame):
    def __init__(self, frame_id, encoding, data):
        assert((encoding == 0) or (encoding == 1) or
               (encoding == 2) or (encoding == 3))

        self.id = frame_id
        self.encoding = encoding
        self.data = data

    def __repr__(self):
        return "ID3v24_T___Frame(%s, %s, %s)" % \
            (repr(self.id), repr(self.encoding), repr(self.data))

    def __unicode__(self):
        return self.data.decode(
            {0: u"latin-1",
             1: u"utf-16",
             2: u"utf-16BE",
             3: u"utf-8"}[self.encoding], 'replace').split(unichr(0), 1)[0]

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s) %s" % (self.id.decode('ascii'),
                                  {0: u"Latin-1",
                                   1: u"UTF-16",
                                   2: u"UTF-16BE",
                                   3: u"UTF-8"}[self.encoding],
                                  unicode(self))

    @classmethod
    def converted(cls, frame_id, unicode_string):
        """given a unicode string, returns a text frame"""

        if (is_latin_1(unicode_string)):
            return cls(frame_id, 0, unicode_string.encode('latin-1'))
        else:
            return cls(frame_id, 3, unicode_string.encode('utf-8'))


class ID3v24_TXXX_Frame(ID3v23_TXXX_Frame):
    def __repr__(self):
        return "ID3v24_TXXX_Frame(%s, %s, %s)" % \
            (repr(self.encoding), repr(self.description), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s, \"%s\") %s" % \
            (self.id,
             {0: u"Latin-1",
              1: u"UTF-16",
              2: u"UTF-16BE",
              3: u"UTF-8"}[self.encoding],
             self.description,
             unicode(self))

    def __unicode__(self):
        return self.data.decode(
            {0: u"latin-1",
             1: u"utf-16",
             2: u"utf-16BE",
             3: u"utf-8"}[self.encoding], 'replace').split(unichr(0), 1)[0]

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed text frame"""

        encoding = reader.read(8)
        description = C_string.parse({0: "latin-1",
                                      1: "utf-16",
                                      2: "utf-16be",
                                      3: "utf-8"}[encoding],
                                     reader)
        data = reader.read_bytes(frame_size - 1 - description.size())

        return cls(encoding, description, data)


class ID3v24_APIC_Frame(ID3v23_APIC_Frame):
    def __repr__(self):
        return "ID3v24_APIC_Frame(%s, %s, %s, ...)" % \
            (repr(self.pic_mime_type), repr(self.pic_type),
             repr(self.pic_description))

    def __setattr__(self, attr, value):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)

        if (attr == 'type'):
            self.__dict__["pic_type"] = {FRONT_COVER: 3,
                                         BACK_COVER: 4,
                                         LEAFLET_PAGE: 5,
                                         MEDIA: 6
                                         }.get(value, 0)  # other
        elif (attr == 'description'):
            if (is_latin_1(value)):
                self.__dict__["pic_description"] = C_string('latin-1', value)
            else:
                self.__dict__["pic_description"] = C_string('utf-8', value)
        elif (attr == 'mime_type'):
            self.__dict__["pic_mime_type"] = C_string('ascii', value)
        else:
            self.__dict__[attr] = value

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """parses this frame from the given BitstreamReader"""

        encoding = reader.read(8)
        mime_type = C_string.parse('ascii', reader)
        picture_type = reader.read(8)
        description = C_string.parse({0: 'latin-1',
                                      1: 'utf-16',
                                      2: 'utf-16be',
                                      3: 'utf-8'}[encoding], reader)
        data = reader.read_bytes(frame_size - (1 +
                                               mime_type.size() +
                                               1 +
                                               description.size()))

        return cls(mime_type, picture_type, description, data)

    def build(self, writer):
        """writes this frame to the given BitstreamWriter
        not including its frame header"""

        writer.write(8, {'latin-1': 0,
                         'utf-16': 1,
                         'utf-16be': 2,
                         'utf-8': 3}[self.pic_description.encoding])
        self.pic_mime_type.build(writer)
        writer.write(8, self.pic_type)
        self.pic_description.build(writer)
        writer.write_bytes(self.data)

    @classmethod
    def converted(cls, frame_id, image):
        if (is_latin_1(image.description)):
            description = C_string('latin-1', image.description)
        else:
            description = C_string('utf-8', image.description)

        return cls(mime_type=C_string('ascii', image.mime_type),
                   picture_type={0: 3,                   # front cover
                                 1: 4,                   # back cover
                                 2: 5,                   # leaflet page
                                 3: 6,                   # media
                                 }.get(image.type, 0),   # other
                   description=description,
                   data=image.data)

    def clean(self):
        """returns a cleaned ID3v24_APIC_Frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        actual_mime_type = Image.new(self.data, u"", 0).mime_type
        if (unicode(self.pic_mime_type) != actual_mime_type):
            from audiotools.text import (CLEAN_FIX_IMAGE_FIELDS)
            return (ID3v24_APIC_Frame(
                C_string('ascii',
                         actual_mime_type.encode('ascii')),
                self.pic_type,
                self.pic_description,
                self.data), [CLEAN_FIX_IMAGE_FIELDS])
        else:
            return (ID3v24_APIC_Frame(
                self.pic_mime_type,
                self.pic_type,
                self.pic_description,
                self.data), [])


class ID3v24_W___Frame(ID3v23_W___Frame):
    def __repr__(self):
        return "ID3v24_W___Frame(%s, %s)" % \
            (repr(self.id), repr(self.data))


class ID3v24_WXXX_Frame(ID3v23_WXXX_Frame):
    def __repr__(self):
        return "ID3v24_WXXX_Frame(%s, %s, %s)" % \
            (repr(self.encoding), repr(self.description), repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s, \"%s\") %s" % \
            (self.id,
             {0: u'Latin-1',
              1: u'UTF-16',
              2: u'UTF-16BE',
              3: u'UTF-8'}[self.encoding],
             self.description,
             self.data.decode('ascii', 'replace'))

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed text frame"""

        encoding = reader.read(8)
        description = C_string.parse({0: 'latin-1',
                                      1: 'utf-16',
                                      2: 'utf-16be',
                                      3: 'utf-8'}[encoding],
                                     reader)
        data = reader.read_bytes(frame_size - 1 - description.size())

        return cls(encoding, description, data)


class ID3v24_COMM_Frame(ID3v23_COMM_Frame):
    def __repr__(self):
        return "ID3v24_COMM_Frame(%s, %s, %s, %s)" % \
            (repr(self.encoding), repr(self.language),
             repr(self.short_description), repr(self.data))

    def __unicode__(self):
        return self.data.decode({0: 'latin-1',
                                 1: 'utf-16',
                                 2: 'utf-16be',
                                 3: 'utf-8'}[self.encoding], 'replace')

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"COMM = (%s, %s, \"%s\") %s" % \
            ({0: u'Latin-1',
              1: u'UTF-16',
              2: u'UTF-16BE',
              3: u'UTF-8'}[self.encoding],
             self.language.decode('ascii', 'replace'),
             self.short_description,
             self.data.decode({0: 'latin-1',
                               1: 'utf-16',
                               2: 'utf-16be',
                               3: 'utf-8'}[self.encoding]))

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed ID3v22_COM_Frame"""

        (encoding, language) = reader.parse("8u 3b")
        short_description = C_string.parse({0: 'latin-1',
                                            1: 'utf-16',
                                            2: 'utf-16be',
                                            3: 'utf-8'}[encoding],
                                           reader)
        data = reader.read_bytes(frame_size - (4 + short_description.size()))

        return cls(encoding, language, short_description, data)

    @classmethod
    def converted(cls, frame_id, unicode_string):
        if (is_latin_1(unicode_string)):
            return cls(0, "eng", C_string("latin-1", u""),
                       unicode_string.encode('latin-1'))
        else:
            return cls(3, "eng", C_string("utf-8", u""),
                       unicode_string.encode('utf-8'))

    def clean(self):
        """returns a cleaned frame of the same class
        or None if the frame should be omitted
        fix text will be appended to fixes_performed, if necessary"""

        from .text import (CLEAN_REMOVE_EMPTY_TAG,
                           CLEAN_REMOVE_TRAILING_WHITESPACE,
                           CLEAN_REMOVE_LEADING_WHITESPACE)

        fixes_performed = []
        field = self.id.decode('ascii')
        text_encoding = {0: 'latin-1',
                         1: 'utf-16',
                         2: 'utf-16be',
                         3: 'utf-8'}

        value = self.data.decode(text_encoding[self.encoding], 'replace')

        #check for an empty tag
        if (len(value.strip()) == 0):
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        #check trailing whitespace
        fix1 = value.rstrip()
        if (fix1 != value):
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        #check leading whitespace
        fix2 = fix1.lstrip()
        if (fix2 != fix1):
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        #stripping whitespace shouldn't alter text/description encoding

        return (self.__class__(self.encoding,
                               self.language,
                               self.short_description,
                               fix2.encode(text_encoding[self.encoding])),
                fixes_performed)


class ID3v24Comment(ID3v23Comment):
    NAME = u'ID3v2.4'

    RAW_FRAME = ID3v24_Frame
    TEXT_FRAME = ID3v24_T___Frame
    USER_TEXT_FRAME = ID3v24_TXXX_Frame
    WEB_FRAME = ID3v24_W___Frame
    USER_WEB_FRAME = ID3v24_WXXX_Frame
    COMMENT_FRAME = ID3v24_COMM_Frame
    IMAGE_FRAME = ID3v24_APIC_Frame
    IMAGE_FRAME_ID = 'APIC'
    ITUNES_COMPILATION_ID = 'TCMP'

    def __repr__(self):
        return "ID3v24Comment(%s, %s)" % (repr(self.frames),
                                          repr(self.total_size))

    @classmethod
    def parse(cls, reader):
        """given a BitstreamReader, returns a parsed ID3v24Comment"""

        (id3,
         major_version,
         minor_version,
         flags) = reader.parse("3b 8u 8u 8u")
        if (id3 != 'ID3'):
            raise ValueError("invalid ID3 header")
        elif (major_version != 0x04):
            raise ValueError("invalid major version")
        elif (minor_version != 0x00):
            raise ValueError("invalid minor version")
        total_size = remaining_size = decode_syncsafe32(reader.read(32))

        frames = []

        while (remaining_size > 10):
            frame_id = reader.read_bytes(4)
            frame_size = decode_syncsafe32(reader.read(32))
            flags = reader.read(16)

            if (frame_id == chr(0) * 4):
                break
            elif (frame_id == 'TXXX'):
                frames.append(
                    cls.USER_TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'WXXX'):
                frames.append(
                    cls.USER_WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'COMM'):
                frames.append(
                    cls.COMMENT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id == 'APIC'):
                frames.append(
                    cls.IMAGE_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id.startswith('T')):
                frames.append(
                    cls.TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif (frame_id.startswith('W')):
                frames.append(
                    cls.WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            else:
                frames.append(
                    cls.RAW_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))

            remaining_size -= (10 + frame_size)

        return cls(frames, total_size)

    def build(self, writer):
        """writes the complete ID3v24Comment data
        to the given BitstreamWriter"""

        tags_size = sum([10 + frame.size() for frame in self])

        writer.build("3b 8u 8u 8u 32u",
                     ("ID3", 0x04, 0x00, 0x00,
                      encode_syncsafe32(max(tags_size, self.total_size))))

        for frame in self:
            writer.write_bytes(frame.id)
            writer.write(32, encode_syncsafe32(frame.size()))
            writer.write(16, 0)
            frame.build(writer)

        #add buffer of NULL bytes if the total size of the tags
        #is less than the total size of the whole ID3v2.2 tag
        if ((self.total_size is not None) and
            ((self.total_size - tags_size) > 0)):
            writer.write_bytes(chr(0) * (self.total_size - tags_size))

    def size(self):
        """returns the total size of the ID3v24Comment, including its header"""

        return 10 + max(sum([10 + frame.size() for frame in self]),
                        self.total_size)


ID3v2Comment = ID3v22Comment


class ID3CommentPair(MetaData):
    """a pair of ID3v2/ID3v1 comments

    these can be manipulated as a set"""

    def __init__(self, id3v2_comment, id3v1_comment):
        """id3v2 and id3v1 are ID3v2Comment and ID3v1Comment objects or None

        values in ID3v2 take precendence over ID3v1, if present"""

        self.__dict__['id3v2'] = id3v2_comment
        self.__dict__['id3v1'] = id3v1_comment

        if (self.id3v2 is not None):
            base_comment = self.id3v2
        elif (self.id3v1 is not None):
            base_comment = self.id3v1
        else:
            raise ValueError("ID3v2 and ID3v1 cannot both be blank")

    def __repr__(self):
        return "ID3CommentPair(%s, %s)" % (repr(self.id3v2), repr(self.id3v1))

    def __getattr__(self, key):
        if (key in self.FIELDS):
            if (((self.id3v2 is not None) and
                 (getattr(self.id3v2, key) is not None))):
                return getattr(self.id3v2, key)
            elif (self.id3v1 is not None):
                return getattr(self.id3v1, key)
            else:
                raise ValueError("ID3v2 and ID3v1 cannot both be blank")
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
        """takes a MetaData object and returns an ID3CommentPair object"""

        if (metadata is None):
            return None
        elif (isinstance(metadata, ID3CommentPair)):
            return ID3CommentPair(
                metadata.id3v2.__class__.converted(metadata.id3v2),
                metadata.id3v1.__class__.converted(metadata.id3v1))
        elif (isinstance(metadata, ID3v2Comment)):
            return ID3CommentPair(metadata,
                                  id3v1_class.converted(metadata))
        else:
            return ID3CommentPair(
                id3v2_class.converted(metadata),
                id3v1_class.converted(metadata))

    def raw_info(self):
        """returns a human-readable version of this metadata pair
        as a unicode string"""

        if ((self.id3v2 is not None) and (self.id3v1 is not None)):
            #both comments present
            from os import linesep

            return (self.id3v2.raw_info() +
                    linesep.decode('ascii') * 2 +
                    self.id3v1.raw_info())
        elif (self.id3v2 is not None):
            #only ID3v2
            return self.id3v2.raw_info()
        elif (self.id3v1 is not None):
            #only ID3v1
            return self.id3v1.raw_info()
        else:
            return u''

    #ImageMetaData passthroughs
    def images(self):
        """returns a list of embedded Image objects"""

        if (self.id3v2 is not None):
            return self.id3v2.images()
        else:
            return []

    def add_image(self, image):
        """embeds an Image object in this metadata"""

        if (self.id3v2 is not None):
            self.id3v2.add_image(image)

    def delete_image(self, image):
        """deletes an Image object from this metadata"""

        if (self.id3v2 is not None):
            self.id3v2.delete_image(image)

    @classmethod
    def supports_images(cls):
        """returns True"""

        return True

    def clean(self):
        if (self.id3v2 is not None):
            (new_id3v2, id3v2_fixes) = self.id3v2.clean()
        else:
            new_id3v2 = None
            id3v2_fixes = []

        if (self.id3v1 is not None):
            (new_id3v1, id3v1_fixes) = self.id3v1.clean()
        else:
            new_id3v1 = None
            id3v1_fixes = []

        return (ID3CommentPair(new_id3v2, new_id3v1),
                id3v2_fixes + id3v1_fixes)
