# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from audiotools import (MetaData, Image, InvalidImage, config)
import sys
import codecs

from audiotools.id3v1 import ID3v1Comment


def is_latin_1(unicode_string):
    """returns True if the given unicode string is a subset of latin-1"""

    try:
        latin1_chars = ({unichr(i) for i in range(32, 127)} |
                        {unichr(i) for i in range(160, 256)})
    except NameError:
        latin1_chars = ({chr(i) for i in range(32, 127)} |
                        {chr(i) for i in range(160, 256)})

    return {i for i in unicode_string}.issubset(latin1_chars)


class UCS2Codec(codecs.Codec):
    """a special unicode codec for UCS-2

    this is a subset of UTF-16 with no support for surrogate pairs,
    limiting it to U+0000-U+FFFF"""

    @classmethod
    def fix_char(cls, c):
        """a filter which changes overly large c values to 'unknown'"""

        if ord(c) <= 0xFFFF:
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
    if name == 'ucs2':
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

    if i >= (2 ** 32):
        raise ValueError("value of %s is too large" % (i))
    elif i < 0:
        raise ValueError("value cannot be negative")

    value = 0

    for x in range(4):
        if (i & 0x80) == 0:
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

    if i >= (2 ** 28):
        raise ValueError("value too large")
    elif i < 0:
        raise ValueError("value cannot be negative")

    value = 0

    for x in range(4):
        value |= ((i & 0x7F) << (x * 8))
        i >>= 7

    return value


class C_string(object):
    TERMINATOR = {'ascii': b"\x00",
                  'latin_1': b"\x00",
                  'latin-1': b"\x00",
                  'ucs2': b"\x00" * 2,
                  'utf_16': b"\x00" * 2,
                  'utf-16': b"\x00" * 2,
                  'utf_16be': b"\x00" * 2,
                  'utf-16be': b"\x00" * 2,
                  'utf_8': b"\x00",
                  'utf-8': b"\x00"}

    def __init__(self, encoding, unicode_string):
        """encoding is a string such as 'utf-8', 'latin-1', etc"""

        from sys import version_info
        str_type = str if (version_info[0] >= 3) else unicode
        assert(encoding in C_string.TERMINATOR.keys())
        assert(isinstance(unicode_string, str_type))

        self.encoding = encoding
        self.unicode_string = unicode_string

    def __repr__(self):
        return "C_string(%s, %s)" % (repr(self.encoding),
                                     repr(self.unicode_string))

    if sys.version_info[0] >= 3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return self.unicode_string

    def __getitem__(self, char):
        return self.unicode_string[char]

    def __len__(self):
        return len(self.unicode_string)

    def __eq__(self, s):
        return (self.unicode_string == (u"%s" % (s)))

    def __ne__(self, s):
        return (self.unicode_string != (u"%s" % (s)))

    def __lt__(self, s):
        return (self.unicode_string < (u"%s" % (s)))

    def __le__(self, s):
        return (self.unicode_string <= (u"%s" % (s)))

    def __gt__(self, s):
        return (self.unicode_string > (u"%s" % (s)))

    def __ge__(self, s):
        return (self.unicode_string >= (u"%s" % (s)))

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
        while char != terminator:
            s.append(char)
            char = reader.read_bytes(terminator_size)

        return cls(encoding, b"".join(s).decode(encoding, 'replace'))

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


def __padded__(value):
    """given an integer value, returns it as a unicode string
    with the proper padding"""

    if config.getboolean_default("ID3", "pad", False):
        return u"%2.2d" % (value)
    else:
        return u"%d" % (value)


# takes a pair of integers (or None) for the current and total values
# returns a unicode string of their combined pair
# for example, __number_pair__(2,3) returns u"2/3"
# whereas      __number_pair__(4,0) returns u"4"
def __number_pair__(current, total):
    if current is None:
        if total is None:
            return __padded__(0)
        else:
            return __padded__(0) + u"/" + __padded__(total)
    else:  # current is not None
        if total is None:
            return __padded__(current)
        else:
            return __padded__(current) + u"/" + __padded__(total)


def read_id3v2_comment(filename):
    """given a filename, returns an ID3v22Comment or a subclass

    for example, if the file is ID3v2.3 tagged,
    this returns an ID3v23Comment
    """

    from audiotools.bitstream import BitstreamReader

    with BitstreamReader(open(filename, "rb"), False) as reader:
        start = reader.getpos()
        (tag, version_major, version_minor) = reader.parse("3b 8u 8u")
        if tag != b'ID3':
            raise ValueError("invalid ID3 header")
        elif version_major == 0x2:
            reader.setpos(start)
            return ID3v22Comment.parse(reader)
        elif version_major == 0x3:
            reader.setpos(start)
            return ID3v23Comment.parse(reader)
        elif version_major == 0x4:
            reader.setpos(start)
            return ID3v24Comment.parse(reader)
        else:
            raise ValueError("unsupported ID3 version")


def skip_id3v2_comment(file):
    """seeks past an ID3v2 comment if found in the file stream
    returns the number of bytes skipped"""

    from audiotools.bitstream import parse

    start = file.tell()
    try:
        # check initial header
        if file.read(3) == b"ID3":
            bytes_skipped = 3
        else:
            file.seek(start)
            return 0

        # ensure major version is valid
        if ord(file.read(1)) in (2, 3, 4):
            bytes_skipped += 1
        else:
            file.seek(start)
            return 0

        # skip minor version
        file.read(1)
        bytes_skipped += 1

        # skip flags
        file.read(1)
        bytes_skipped += 1

        # get the whole size of the tag
        try:
            tag_size = decode_syncsafe32(parse("32u", False, file.read(4))[0])
        except ValueError:
            file.seek(start)
            return 0
        bytes_skipped += 4

        # skip to the end of its length
        file.read(tag_size)
        bytes_skipped += tag_size

        # check for additional ID3v2 tags recursively
        return bytes_skipped + skip_id3v2_comment(file)
    except IOError:
        file.seek(start)
        return 0


def total_id3v2_comments(file):
    """returns the number of nested ID3v2 comments found in the file stream"""

    from audiotools.bitstream import parse

    start = file.tell()
    try:
        # check initial header
        if file.read(3) != b"ID3":
            file.seek(start)
            return 0

        # ensure major version is valid
        if ord(file.read(1)) not in (2, 3, 4):
            file.seek(start)
            return 0

        # skip minor version
        file.read(1)

        # skip flags
        file.read(1)

        # get the whole size of the tag
        try:
            tag_size = decode_syncsafe32(parse("32u", False, file.read(4))[0])
        except ValueError:
            file.seek(start)
            return 0

        # skip to the end of its length
        file.read(tag_size)

        # check for additional ID3v2 tags recursively
        return 1 + total_id3v2_comments(file)
    except IOError as err:
        file.seek(start)
        return 0

############################################################
# ID3v2.2 Comment
############################################################


class ID3v22_Frame(object):
    def __init__(self, frame_id, data):
        self.id = frame_id
        self.data = data

    def copy(self):
        return self.__class__(self.id, self.data)

    def __repr__(self):
        return "ID3v22_Frame(%s, %s)" % (repr(self.id), repr(self.data))

    def raw_info(self):
        from audiotools import hex_string

        if len(self.data) > 20:
            return u"%s = %s\u2026" % \
                (self.id.decode('ascii', 'replace'),
                 hex_string(self.data[0:20]))
        else:
            return u"%s = %s" % \
                (self.id.decode('ascii', 'replace'),
                 hex_string(self.data))

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
        """returns a cleaned ID3v22_Frame and list of fixes,
        or None if the frame should be removed entirely"""

        return (self.__class__(self.id, self.data), [])


class ID3v22_T__Frame(object):
    NUMERICAL_IDS = (b'TRK', b'TPA')
    BOOLEAN_IDS = (b'TCP',)

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
             self.__unicode__())

    def __eq__(self, frame):
        return __attrib_equals__(["id", "encoding", "data"], self, frame)

    if sys.version_info[0] >= 3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return self.data.decode(
            {0: 'latin-1', 1: 'ucs2'}[self.encoding],
            'replace').split(u"\x00", 1)[0]

    def number(self):
        """if the frame is numerical, returns the track/album_number portion
        raises TypeError if not"""

        import re

        if self.id not in self.NUMERICAL_IDS:
            raise TypeError()

        unicode_value = self.__unicode__()

        int_string = re.search(r'\d+', unicode_value)
        if int_string is None:
            return None

        int_value = int(int_string.group(0))
        if (int_value == 0) and (u"/" in unicode_value):
            total_value = re.search(r'\d+',
                                    unicode_value.split(u"/")[1])
            if total_value is not None:
                # don't return placeholder 0 value
                # when a _total value is present
                # but _number value is 0
                return None
            else:
                return int_value
        else:
            return int_value

    def total(self):
        """if the frame is numerical, returns the track/album_total portion
        raises TypeError if not"""

        import re

        if self.id not in self.NUMERICAL_IDS:
            raise TypeError()

        unicode_value = self.__unicode__()

        if u"/" not in unicode_value:
            return None

        int_string = re.search(r'\d+', unicode_value.split(u"/")[1])

        if int_string is not None:
            return int(int_string.group(0))
        else:
            return None

    def true(self):
        """if the frame is boolean, returns True if it represents true
        raises TypeError if not"""

        if self.id not in self.BOOLEAN_IDS:
            raise TypeError()

        return self.__unicode__() == u"1"

    @classmethod
    def parse(cls, frame_id, frame_size, reader):
        """given a frame_id string, frame_size int and BitstreamReader
        of the remaining frame data, returns a parsed text frame"""

        encoding = reader.read(8)
        return cls(frame_id, encoding, reader.read_bytes(frame_size - 1))

    def build(self, writer):
        """writes the frame's data to the BitstreamWriter
        not including its frame header"""

        writer.write(8, self.encoding)
        writer.write_bytes(self.data)

    def size(self):
        """returns the frame's total size
        not including its frame header"""

        return 1 + len(self.data)

    @classmethod
    def converted(cls, frame_id, unicode_string):
        """given a unicode string, returns a text frame"""

        if is_latin_1(unicode_string):
            return cls(frame_id, 0, unicode_string.encode('latin-1'))
        else:
            return cls(frame_id, 1, unicode_string.encode('ucs2'))

    def clean(self):
        """returns a cleaned frame,
        or None if the frame should be removed entirely
        any fixes are appended to fixes_applied as unicode string"""

        from audiotools.text import (CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_ZEROES,
                                     CLEAN_ADD_LEADING_ZEROES)

        fixes_performed = []
        field = self.id.decode('ascii')
        value = self.__unicode__()

        # check for an empty tag
        if len(value.strip()) == 0:
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        # check trailing whitespace
        fix1 = value.rstrip()
        if fix1 != value:
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        # check leading whitespace
        fix2 = fix1.lstrip()
        if fix2 != fix1:
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        # check leading zeroes for a numerical tag
        if self.id in self.NUMERICAL_IDS:
            fix3 = __number_pair__(self.number(), self.total())
            if fix3 != fix2:
                from audiotools import config

                if config.getboolean_default("ID3", "pad", False):
                    fixes_performed.append(CLEAN_ADD_LEADING_ZEROES %
                                           {"field": field})
                else:
                    fixes_performed.append(CLEAN_REMOVE_LEADING_ZEROES %
                                           {"field": field})
        else:
            fix3 = fix2

        return (self.__class__.converted(self.id, fix3), fixes_performed)


class ID3v22_TXX_Frame(object):
    def __init__(self, encoding, description, data):
        self.id = b'TXX'

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
             self.__unicode__())

    def __eq__(self, frame):
        return __attrib_equals__(["id", "encoding", "description", "data"])

    if sys.version_info[0] >= 3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return self.data.decode(
            {0: 'latin-1', 1: 'ucs2'}[self.encoding],
            'replace').split(u'\x00', 1)[0]

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
        value = self.__unicode__()

        # check for an empty tag
        if len(value.strip()) == 0:
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        # check trailing whitespace
        fix1 = value.rstrip()
        if fix1 != value:
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        # check leading whitespace
        fix2 = fix1.lstrip()
        if fix2 != fix1:
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        return (self.__class__(self.encoding, self.description, fix2),
                fixes_performed)


class ID3v22_W__Frame(object):
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


class ID3v22_WXX_Frame(object):
    def __init__(self, encoding, description, data):
        self.id = b'WXX'

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


class ID3v22_COM_Frame(object):
    def __init__(self, encoding, language, short_description, data):
        """fields are as follows:
        | encoding          | 1 byte int of the comment's text encoding |
        | language          | 3 byte string of the comment's language   |
        | short_description | C_string of a short description           |
        | data              | plain string of the comment data itself   |
        """

        self.id = b"COM"
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

    def __ne__(self, frame):
        return not self.__eq__(frame)

    if sys.version_info[0] >= 3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

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
        if is_latin_1(unicode_string):
            return cls(0, b"eng", C_string("latin-1", u""),
                       unicode_string.encode('latin-1'))
        else:
            return cls(1, b"eng", C_string("ucs2", u""),
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

        # check for an empty tag
        if len(value.strip()) == 0:
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        # check trailing whitespace
        fix1 = value.rstrip()
        if fix1 != value:
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        # check leading whitespace
        fix2 = fix1.lstrip()
        if fix2 != fix1:
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        # stripping whitespace shouldn't alter text/description encoding

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

        self.id = b'PIC'

        # add PIC-specific fields
        self.pic_format = image_format
        self.pic_type = picture_type
        self.pic_description = description

        # figure out image metrics from raw data
        try:
            metrics = Image.new(data, u'', 0)
        except InvalidImage:
            metrics = Image(data=data, mime_type=u'',
                            width=0, height=0, color_depth=0, color_count=0,
                            description=u'', type=0)

        # then initialize Image parent fields from metrics
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
        return {0: u"Other",
                1: u"32x32 pixels 'file icon' (PNG only)",
                2: u"Other file icon",
                3: u"Cover (front)",
                4: u"Cover (back)",
                5: u"Leaflet page",
                6: u"Media (e.g. label side of CD)",
                7: u"Lead artist/lead performer/soloist",
                8: u"Artist / Performer",
                9: u"Conductor",
                10: u"Band / Orchestra",
                11: u"Composer",
                12: u"Lyricist / Text writer",
                13: u"Recording Location",
                14: u"During recording",
                15: u"During performance",
                16: u"Movie/Video screen capture",
                17: u"A bright coloured fish",
                18: u"Illustration",
                19: u"Band/Artist logotype",
                20: u"Publisher/Studio logotype"}.get(self.pic_type, u"Other")

    def __getattr__(self, attr):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)

        if attr == 'type':
            return {3: FRONT_COVER,
                    4: BACK_COVER,
                    5: LEAFLET_PAGE,
                    6: MEDIA
                    }.get(self.pic_type, OTHER)
        elif attr == 'description':
            return self.pic_description.__unicode__()
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)
        if attr == 'type':
            Image.__setattr__(self,
                              "pic_type", {FRONT_COVER: 3,
                                           BACK_COVER: 4,
                                           LEAFLET_PAGE: 5,
                                           MEDIA: 6}.get(value, 0))
        elif attr == 'description':
            Image.__setattr__(
                self,
                "pic_description",
                C_string("latin-1" if is_latin_1(value) else "ucs2",
                         value))
        else:
            Image.__setattr__(self, attr, value)

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
        if is_latin_1(image.description):
            description = C_string('latin-1', image.description)
        else:
            description = C_string('ucs2', image.description)

        return cls(image_format={u"image/png": b"PNG",
                                 u"image/jpeg": b"JPG",
                                 u"image/jpg": b"JPG",
                                 u"image/x-ms-bmp": b"BMP",
                                 u"image/gif": b"GIF",
                                 u"image/tiff": b"TIF"}.get(image.mime_type,
                                                            b'UNK'),
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

        # all the fields are derived from the image data
        # so there's no need to test for a mismatch

        # not sure if it's worth testing for bugs in the description
        # or format fields

        return (ID3v22_PIC_Frame(self.pic_format,
                                 self.pic_type,
                                 self.pic_description,
                                 self.data), [])


class ID3v22Comment(MetaData):
    NAME = u'ID3v2.2'

    ATTRIBUTE_MAP = {'track_name': b'TT2',
                     'track_number': b'TRK',
                     'track_total': b'TRK',
                     'album_name': b'TAL',
                     'artist_name': b'TP1',
                     'performer_name': b'TP2',
                     'conductor_name': b'TP3',
                     'composer_name': b'TCM',
                     'media': b'TMT',
                     'ISRC': b'TRC',
                     'copyright': b'TCR',
                     'publisher': b'TPB',
                     'year': b'TYE',
                     'date': b'TRD',
                     'album_number': b'TPA',
                     'album_total': b'TPA',
                     'comment': b'COM',
                     'compilation': b'TCP'}

    RAW_FRAME = ID3v22_Frame
    TEXT_FRAME = ID3v22_T__Frame
    USER_TEXT_FRAME = ID3v22_TXX_Frame
    WEB_FRAME = ID3v22_W__Frame
    USER_WEB_FRAME = ID3v22_WXX_Frame
    COMMENT_FRAME = ID3v22_COM_Frame
    IMAGE_FRAME = ID3v22_PIC_Frame
    IMAGE_FRAME_ID = b'PIC'

    def __init__(self, frames, total_size=None):
        MetaData.__setattr__(self, "frames", frames[:])
        MetaData.__setattr__(self, "total_size", total_size)

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

        return linesep.join(
            ["%s:" % (self.NAME)] +
            [frame.raw_info() for frame in self])

    @classmethod
    def parse(cls, reader):
        """given a BitstreamReader, returns a parsed ID3v22Comment"""

        (id3,
         major_version,
         minor_version,
         flags) = reader.parse("3b 8u 8u 8u")
        if id3 != b'ID3':
            raise ValueError("invalid ID3 header")
        elif major_version != 0x02:
            raise ValueError("invalid major version")
        elif minor_version != 0x00:
            raise ValueError("invalid minor version")
        total_size = remaining_size = decode_syncsafe32(reader.read(32))

        frames = []

        while remaining_size > 6:
            (frame_id, frame_size) = reader.parse("3b 24u")

            if frame_id == b"\x00" * 3:
                break
            elif frame_id == b'TXX':
                frames.append(
                    cls.USER_TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'WXX':
                frames.append(
                    cls.USER_WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'COM':
                frames.append(
                    cls.COMMENT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'PIC':
                frames.append(
                    cls.IMAGE_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id.startswith(b'T'):
                frames.append(
                    cls.TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id.startswith(b'W'):
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
                     (b"ID3", 0x02, 0x00, 0x00,
                      encode_syncsafe32(
                          max(tags_size,
                              (self.total_size if
                               self.total_size is not None else 0)))))

        for frame in self:
            writer.build("3b 24u", (frame.id, frame.size()))
            frame.build(writer)

        # add buffer of NULL bytes if the total size of the tags
        # is less than the total size of the whole ID3v2.2 tag
        if (((self.total_size is not None) and
             ((self.total_size - tags_size) > 0))):
            writer.write_bytes(u"\x00" * (self.total_size - tags_size))

    def size(self):
        """returns the total size of the ID3v22Comment, including its header"""

        return 10 + max(sum([6 + frame.size() for frame in self]),
                        (self.total_size if self.total_size is not None
                         else 0))

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, frame_id):
        frames = [frame for frame in self if (frame.id == frame_id)]
        if len(frames) > 0:
            return frames
        else:
            raise KeyError(frame_id)

    def __setitem__(self, frame_id, frames):
        new_frames = frames[:]
        updated_frames = []

        for old_frame in self:
            if old_frame.id == frame_id:
                try:
                    # replace current frame with newly set frame
                    updated_frames.append(new_frames.pop(0))
                except IndexError:
                    # no more newly set frames, so remove current frame
                    continue
            else:
                # passthrough unmatched frames
                updated_frames.append(old_frame)
        else:
            # append any leftover frames
            for new_frame in new_frames:
                updated_frames.append(new_frame)

        MetaData.__setattr__(self, "frames", updated_frames)

    def __delitem__(self, frame_id):
        updated_frames = [frame for frame in self if frame.id != frame_id]
        if len(updated_frames) < len(self):
            MetaData.__setattr__(self, "frames", updated_frames)
        else:
            raise KeyError(frame_id)

    def keys(self):
        return list({frame.id for frame in self})

    def values(self):
        return [self[key] for key in self.keys()]

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def __getattr__(self, attr):
        if attr in self.ATTRIBUTE_MAP:
            try:
                frame = self[self.ATTRIBUTE_MAP[attr]][0]
                if attr in {'track_number', 'album_number'}:
                    return frame.number()
                elif attr in {'track_total', 'album_total'}:
                    return frame.total()
                elif attr == 'compilation':
                    return frame.true()
                else:
                    return frame.__unicode__()
            except KeyError:
                return None
        elif attr in self.FIELDS:
            return None
        else:
            return MetaData.__getattribute__(self, attr)

    def __setattr__(self, attr, value):
        def swap_number(unicode_value, new_number):
            import re

            return re.sub(r'\d+', __padded__(new_number), unicode_value, 1)

        def swap_slashed_number(unicode_value, new_number):
            if u"/" in unicode_value:
                (first, second) = unicode_value.split(u"/", 1)
                return u"/".join([first, swap_number(second, new_number)])
            else:
                return u"/".join([unicode_value, __padded__(new_number)])

        if attr in self.ATTRIBUTE_MAP:
            if value is not None:
                frame_id = self.ATTRIBUTE_MAP[attr]

                if attr in {'track_number', 'album_number'}:
                    try:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            swap_number(self[frame_id][0].__unicode__(),
                                        value))
                    except KeyError:
                        # no frame found with track/album_number's ID,
                        # so create a new frame for it
                        # with the value padded appropriately
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            __padded__(value))
                elif attr in {'track_total', 'album_total'}:
                    try:
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            swap_slashed_number(
                                self[frame_id][0].__unicode__(),
                                value))
                    except KeyError:
                        # no frame found with track_total's ID
                        # so create a new frame for it
                        # with the value padded appropriately
                        new_frame = self.TEXT_FRAME.converted(
                            frame_id,
                            __number_pair__(None, value))
                elif attr == 'comment':
                    new_frame = self.COMMENT_FRAME.converted(
                        frame_id, value)
                elif attr == 'compilation':
                    new_frame = self.TEXT_FRAME.converted(
                        frame_id, u"%d" % (1 if value else 0))
                else:
                    new_frame = self.TEXT_FRAME.converted(
                        frame_id, u"%s" % (value,))

                try:
                    self[frame_id] = [new_frame] + self[frame_id][1:]
                except KeyError:
                    self[frame_id] = [new_frame]
            else:
                delattr(self, attr)
        elif attr in MetaData.FIELDS:
            pass
        else:
            MetaData.__setattr__(self, attr, value)

    def __delattr__(self, attr):
        import re

        def zero_number(unicode_value):
            return re.sub(r'\d+', u"0", unicode_value, 1)

        if attr in self.ATTRIBUTE_MAP:
            updated_frames = []
            delete_frame_id = self.ATTRIBUTE_MAP[attr]
            for frame in self:
                if frame.id == delete_frame_id:
                    if attr in {'track_number', 'album_number'}:
                        current_value = frame.__unicode__()
                        if u"/" in current_value:
                            # if *_number field contains a slashed total,
                            # replace unslashed portion with 0
                            updated_frames.append(
                                self.TEXT_FRAME.converted(
                                    frame.id,
                                    zero_number(current_value)))
                        else:
                            # otherwise, remove *_number field
                            continue
                    elif attr in {'track_total', 'album_total'}:
                        current_value = frame.__unicode__()
                        if u"/" in current_value:
                            (first, second) = current_value.split(u"/", 1)
                            number = re.search(r'\d+', first)
                            if ((number is not None) and
                                (int(number.group(0)) != 0)):
                                # field contains nonzero number part
                                # so remove only slashed part
                                updated_frames.append(
                                    self.TEXT_FRAME.converted(
                                        frame.id, first.rstrip()))
                            else:
                                # number part is zero, so remove entire tag
                                continue
                        else:
                            # oddball tag with no slash
                            # so pass it through unchanged
                            updated_frames.append(frame)
                    else:
                        # handle the textual fields
                        # which are simply deleted outright
                        continue
                else:
                    updated_frames.append(frame)

            MetaData.__setattr__(self, "frames", updated_frames)

        elif attr in MetaData.FIELDS:
            # ignore deleted attributes which are in MetaData
            # but we don't support
            pass
        else:
            MetaData.__delattr__(self, attr)

    def images(self):
        return [frame for frame in self if (frame.id == self.IMAGE_FRAME_ID)]

    def add_image(self, image):
        self.frames.append(
            self.IMAGE_FRAME.converted(self.IMAGE_FRAME_ID, image))

    def delete_image(self, image):
        MetaData.__setattr__(
            self,
            "frames",
            [frame for frame in self if
             ((frame.id != self.IMAGE_FRAME_ID) or (frame != image))])

    @classmethod
    def converted(cls, metadata):
        """converts a MetaData object to an ID3v2*Comment object"""

        if metadata is None:
            return None
        elif cls is metadata.__class__:
            return cls([frame.copy() for frame in metadata])

        frames = []

        for (attr, key) in cls.ATTRIBUTE_MAP.items():
            value = getattr(metadata, attr)
            if (cls.FIELD_TYPES[attr] == type(u"")) and (value is not None):
                if attr == 'comment':
                    frames.append(cls.COMMENT_FRAME.converted(key, value))
                else:
                    frames.append(cls.TEXT_FRAME.converted(key, value))
            elif attr == 'compilation':
                frames.append(
                    cls.TEXT_FRAME.converted(key, u"%d" % (1 if value else 0)))

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

        return cls(frames)

    def clean(self):
        """returns a new MetaData object that's been cleaned of problems"""

        new_frames = []
        fixes_performed = []

        for frame in self:
            (filtered_frame, frame_fixes) = frame.clean()
            if filtered_frame is not None:
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
    NUMERICAL_IDS = (b'TRCK', b'TPOS')
    BOOLEAN_IDS = (b'TCMP',)

    def __repr__(self):
        return "ID3v23_T___Frame(%s, %s, %s)" % \
            (repr(self.id), repr(self.encoding), repr(self.data))


class ID3v23_TXXX_Frame(ID3v22_TXX_Frame):
    def __init__(self, encoding, description, data):
        self.id = b'TXXX'

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
        self.id = b'WXXX'

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

        self.id = b'APIC'

        # add APIC-specific fields
        self.pic_type = picture_type
        self.pic_description = description
        self.pic_mime_type = mime_type

        # figure out image metrics from raw data
        try:
            metrics = Image.new(data, u'', 0)
        except InvalidImage:
            metrics = Image(data=data, mime_type=u'',
                            width=0, height=0, color_depth=0, color_count=0,
                            description=u'', type=0)

        # then initialize Image parent fields from metrics
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

        if attr == 'type':
            return {3: FRONT_COVER,
                    4: BACK_COVER,
                    5: LEAFLET_PAGE,
                    6: MEDIA
                    }.get(self.pic_type, 4)  # other
        elif attr == 'description':
            return self.pic_description.__unicode__()
        elif attr == 'mime_type':
            return self.pic_mime_type.__unicode__()
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        from audiotools import (FRONT_COVER,
                                BACK_COVER,
                                LEAFLET_PAGE,
                                MEDIA,
                                OTHER)

        if attr == 'type':
            Image.__setattr__(self,
                              "pic_type",
                              {FRONT_COVER: 3,
                               BACK_COVER: 4,
                               LEAFLET_PAGE: 5,
                               MEDIA: 6}.get(value, 0))
        elif attr == 'description':
            Image.__setattr__(
                self,
                "pic_description",
                C_string("latin-1" if is_latin_1(value) else "ucs2",
                         value))
        elif attr == 'mime_type':
            Image.__setattr__(self, "pic_mime_type", C_string('ascii', value))
        else:
            Image.__setattr__(self, attr, value)

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
        if is_latin_1(image.description):
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
        if self.pic_mime_type.__unicode__() != actual_mime_type:
            from audiotools.text import (CLEAN_FIX_IMAGE_FIELDS)
            return (ID3v23_APIC_Frame(
                C_string('ascii', actual_mime_type),
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

        self.id = b"COMM"
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

    ATTRIBUTE_MAP = {'track_name': b'TIT2',
                     'track_number': b'TRCK',
                     'track_total': b'TRCK',
                     'album_name': b'TALB',
                     'artist_name': b'TPE1',
                     'performer_name': b'TPE2',
                     'composer_name': b'TCOM',
                     'conductor_name': b'TPE3',
                     'media': b'TMED',
                     'ISRC': b'TSRC',
                     'copyright': b'TCOP',
                     'publisher': b'TPUB',
                     'year': b'TYER',
                     'date': b'TRDA',
                     'album_number': b'TPOS',
                     'album_total': b'TPOS',
                     'comment': b'COMM',
                     'compilation': b'TCMP'}

    RAW_FRAME = ID3v23_Frame
    TEXT_FRAME = ID3v23_T___Frame
    WEB_FRAME = ID3v23_W___Frame
    USER_TEXT_FRAME = ID3v23_TXXX_Frame
    USER_WEB_FRAME = ID3v23_WXXX_Frame
    COMMENT_FRAME = ID3v23_COMM_Frame
    IMAGE_FRAME = ID3v23_APIC_Frame
    IMAGE_FRAME_ID = b'APIC'
    ITUNES_COMPILATION_ID = b'TCMP'

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
        if id3 != b'ID3':
            raise ValueError("invalid ID3 header")
        elif major_version != 0x03:
            raise ValueError("invalid major version")
        elif minor_version != 0x00:
            raise ValueError("invalid minor version")
        total_size = remaining_size = decode_syncsafe32(reader.read(32))

        frames = []

        while remaining_size > 10:
            (frame_id, frame_size, frame_flags) = reader.parse("4b 32u 16u")

            if frame_id == b"\x00" * 4:
                break
            elif frame_id == b'TXXX':
                frames.append(
                    cls.USER_TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'WXXX':
                frames.append(
                    cls.USER_WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'COMM':
                frames.append(
                    cls.COMMENT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'APIC':
                frames.append(
                    cls.IMAGE_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id.startswith(b'T'):
                frames.append(
                    cls.TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id.startswith(b'W'):
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
                     (b"ID3", 0x03, 0x00, 0x00,
                      encode_syncsafe32(
                          max(tags_size,
                              (self.total_size if
                               self.total_size is not None else 0)))))

        for frame in self:
            writer.build("4b 32u 16u", (frame.id, frame.size(), 0))
            frame.build(writer)

        # add buffer of NULL bytes if the total size of the tags
        # is less than the total size of the whole ID3v2.3 tag
        if (((self.total_size is not None) and
             ((self.total_size - tags_size) > 0))):
            writer.write_bytes(b"\x00" * (self.total_size - tags_size))

    def size(self):
        """returns the total size of the ID3v23Comment, including its header"""

        return 10 + max(sum([10 + frame.size() for frame in self]),
                        (self.total_size if self.total_size is not None
                         else 0))


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
             3: u"utf-8"}[self.encoding], 'replace').split(u"\x00", 1)[0]

    def raw_info(self):
        """returns a human-readable version of this frame as unicode"""

        return u"%s = (%s) %s" % (self.id.decode('ascii'),
                                  {0: u"Latin-1",
                                   1: u"UTF-16",
                                   2: u"UTF-16BE",
                                   3: u"UTF-8"}[self.encoding],
                                  self.__unicode__())

    @classmethod
    def converted(cls, frame_id, unicode_string):
        """given a unicode string, returns a text frame"""

        if is_latin_1(unicode_string):
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
             self.__unicode__())

    def __unicode__(self):
        return self.data.decode(
            {0: u"latin-1",
             1: u"utf-16",
             2: u"utf-16BE",
             3: u"utf-8"}[self.encoding], 'replace').split(u"\x00", 1)[0]

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

        if attr == 'type':
            Image.__setattr__(
                self,
                "pic_type",
                {FRONT_COVER: 3,
                 BACK_COVER: 4,
                 LEAFLET_PAGE: 5,
                 MEDIA: 6}.get(value, 0))
        elif attr == 'description':
            Image.__setattr__(
                self,
                "pic_description",
                C_string("latin-1" if is_latin_1(value) else "utf-8", value))
        elif attr == 'mime_type':
            Image.__setattr__(self, "pic_mime_type", C_string('ascii', value))
        else:
            Image.__setattr__(self, attr, value)

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
        if is_latin_1(image.description):
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
        if self.pic_mime_type.__unicode__() != actual_mime_type:
            from audiotools.text import (CLEAN_FIX_IMAGE_FIELDS)
            return (ID3v24_APIC_Frame(
                C_string('ascii', actual_mime_type),
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
        if is_latin_1(unicode_string):
            return cls(0, b"eng", C_string("latin-1", u""),
                       unicode_string.encode('latin-1'))
        else:
            return cls(3, b"eng", C_string("utf-8", u""),
                       unicode_string.encode('utf-8'))

    def clean(self):
        """returns a cleaned frame of the same class
        or None if the frame should be omitted
        fix text will be appended to fixes_performed, if necessary"""

        from audiotools.text import (CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE)

        fixes_performed = []
        field = self.id.decode('ascii')
        text_encoding = {0: 'latin-1',
                         1: 'utf-16',
                         2: 'utf-16be',
                         3: 'utf-8'}

        value = self.data.decode(text_encoding[self.encoding], 'replace')

        # check for an empty tag
        if len(value.strip()) == 0:
            return (None, [CLEAN_REMOVE_EMPTY_TAG % {"field": field}])

        # check trailing whitespace
        fix1 = value.rstrip()
        if fix1 != value:
            fixes_performed.append(CLEAN_REMOVE_TRAILING_WHITESPACE %
                                   {"field": field})

        # check leading whitespace
        fix2 = fix1.lstrip()
        if fix2 != fix1:
            fixes_performed.append(CLEAN_REMOVE_LEADING_WHITESPACE %
                                   {"field": field})

        # stripping whitespace shouldn't alter text/description encoding

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
    IMAGE_FRAME_ID = b'APIC'
    ITUNES_COMPILATION_ID = b'TCMP'

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
        if id3 != b'ID3':
            raise ValueError("invalid ID3 header")
        elif major_version != 0x04:
            raise ValueError("invalid major version")
        elif minor_version != 0x00:
            raise ValueError("invalid minor version")
        total_size = remaining_size = decode_syncsafe32(reader.read(32))

        frames = []

        while remaining_size > 10:
            frame_id = reader.read_bytes(4)
            frame_size = decode_syncsafe32(reader.read(32))
            flags = reader.read(16)

            if frame_id == b"\x00" * 4:
                break
            elif frame_id == b'TXXX':
                frames.append(
                    cls.USER_TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'WXXX':
                frames.append(
                    cls.USER_WEB_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'COMM':
                frames.append(
                    cls.COMMENT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id == b'APIC':
                frames.append(
                    cls.IMAGE_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id.startswith(b'T'):
                frames.append(
                    cls.TEXT_FRAME.parse(
                        frame_id, frame_size, reader.substream(frame_size)))
            elif frame_id.startswith(b'W'):
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
                     (b"ID3", 0x04, 0x00, 0x00,
                      encode_syncsafe32(
                          max(tags_size,
                              (self.total_size if
                               self.total_size is not None else 0)))))

        for frame in self:
            writer.write_bytes(frame.id)
            writer.write(32, encode_syncsafe32(frame.size()))
            writer.write(16, 0)
            frame.build(writer)

        # add buffer of NULL bytes if the total size of the tags
        # is less than the total size of the whole ID3v2.2 tag
        if (((self.total_size is not None) and
             ((self.total_size - tags_size) > 0))):
            writer.write_bytes(b"\x00" * (self.total_size - tags_size))

    def size(self):
        """returns the total size of the ID3v24Comment, including its header"""

        return 10 + max(sum([10 + frame.size() for frame in self]),
                        (self.total_size if self.total_size is not None
                         else 0))


ID3v2Comment = ID3v22Comment


class ID3CommentPair(MetaData):
    """a pair of ID3v2/ID3v1 comments

    these can be manipulated as a set"""

    def __init__(self, id3v2_comment, id3v1_comment):
        """id3v2 and id3v1 are ID3v2Comment and ID3v1Comment objects or None

        values in ID3v2 take precendence over ID3v1, if present"""

        MetaData.__setattr__(self, "id3v2", id3v2_comment)
        MetaData.__setattr__(self, "id3v1", id3v1_comment)

        if self.id3v2 is not None:
            base_comment = self.id3v2
        elif self.id3v1 is not None:
            base_comment = self.id3v1
        else:
            raise ValueError("ID3v2 and ID3v1 cannot both be blank")

    def __repr__(self):
        return "ID3CommentPair(%s, %s)" % (repr(self.id3v2), repr(self.id3v1))

    def __getattr__(self, attr):
        assert((self.id3v2 is not None) or (self.id3v1 is not None))
        if attr in self.FIELDS:
            if self.id3v2 is not None:
                # ID3v2 takes precedence over ID3v1
                field = getattr(self.id3v2, attr)
                if field is not None:
                    return field
                elif self.id3v1 is not None:
                    return getattr(self.id3v1, attr)
                else:
                    return None
            elif self.id3v1 is not None:
                return getattr(self.id3v1, attr)
        else:
            return MetaData.__getattribute__(self, attr)

    def __setattr__(self, attr, value):
        assert((self.id3v2 is not None) or (self.id3v1 is not None))
        if attr in self.FIELDS:
            if self.id3v2 is not None:
                setattr(self.id3v2, attr, value)
            if self.id3v1 is not None:
                setattr(self.id3v1, attr, value)
        else:
            MetaData.__setattr__(self, attr, value)

    def __delattr__(self, attr):
        assert((self.id3v2 is not None) or (self.id3v1 is not None))
        if attr in self.FIELDS:
            if self.id3v2 is not None:
                delattr(self.id3v2, attr)
            if self.id3v1 is not None:
                delattr(self.id3v1, attr)
        else:
            MetaData.__delattr__(self, attr)

    @classmethod
    def converted(cls, metadata,
                  id3v2_class=ID3v23Comment,
                  id3v1_class=ID3v1Comment):
        """takes a MetaData object and returns an ID3CommentPair object"""

        if metadata is None:
            return None
        elif isinstance(metadata, ID3CommentPair):
            return ID3CommentPair(
                metadata.id3v2.__class__.converted(metadata.id3v2),
                metadata.id3v1.__class__.converted(metadata.id3v1))
        elif isinstance(metadata, ID3v2Comment):
            return ID3CommentPair(metadata,
                                  id3v1_class.converted(metadata))
        else:
            return ID3CommentPair(
                id3v2_class.converted(metadata),
                id3v1_class.converted(metadata))

    def raw_info(self):
        """returns a human-readable version of this metadata pair
        as a unicode string"""

        if (self.id3v2 is not None) and (self.id3v1 is not None):
            # both comments present
            from os import linesep

            return (self.id3v2.raw_info() +
                    linesep * 2 +
                    self.id3v1.raw_info())
        elif self.id3v2 is not None:
            # only ID3v2
            return self.id3v2.raw_info()
        elif self.id3v1 is not None:
            # only ID3v1
            return self.id3v1.raw_info()
        else:
            return u''

    # ImageMetaData passthroughs
    def images(self):
        """returns a list of embedded Image objects"""

        if self.id3v2 is not None:
            return self.id3v2.images()
        else:
            return []

    def add_image(self, image):
        """embeds an Image object in this metadata"""

        if self.id3v2 is not None:
            self.id3v2.add_image(image)

    def delete_image(self, image):
        """deletes an Image object from this metadata"""

        if self.id3v2 is not None:
            self.id3v2.delete_image(image)

    @classmethod
    def supports_images(cls):
        """returns True"""

        return True

    def clean(self):
        if self.id3v2 is not None:
            (new_id3v2, id3v2_fixes) = self.id3v2.clean()
        else:
            new_id3v2 = None
            id3v2_fixes = []

        if self.id3v1 is not None:
            (new_id3v1, id3v1_fixes) = self.id3v1.clean()
        else:
            new_id3v1 = None
            id3v1_fixes = []

        return (ID3CommentPair(new_id3v2, new_id3v1),
                id3v2_fixes + id3v1_fixes)
