#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

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


from audiotools import (AudioFile, WaveAudio, InvalidFile, PCMReader,
                        transfer_data, subprocess, BIN, MetaData,
                        os, re, TempWaveReader, Image, cStringIO)

import gettext

gettext.install("audiotools", unicode=True)


#takes a pair of integers for the current and total values
#returns a unicode string of their combined pair
#for example, __number_pair__(2,3) returns u"2/3"
#whereas      __number_pair__(4,0) returns u"4"
def __number_pair__(current, total):
    if (total == 0):
        return u"%d" % (current)
    else:
        return u"%d/%d" % (current, total)


def limited_transfer_data(from_function, to_function,
                          max_bytes):
    BUFFER_SIZE = 0x100000
    s = from_function(BUFFER_SIZE)
    while ((len(s) > 0) and (max_bytes > 0)):
        if (len(s) > max_bytes):
            s = s[0:max_bytes]
        to_function(s)
        max_bytes -= len(s)
        s = from_function(BUFFER_SIZE)


#######################
#MONKEY'S AUDIO
#######################


class ApeTagItem:
    FORMAT = "32u [ 1u 2u 29p ]"

    def __init__(self, item_type, read_only, key, data):
        """Fields are as follows:

        item_type is 0 = UTF-8, 1 = binary, 2 = external, 3 = reserved.
        read_only is True if the item is read only.
        key is an ASCII string.
        data is a binary string of the data itself.
        """

        self.type = item_type
        self.read_only = read_only
        self.key = key
        self.data = data

    def total_size(self):
        return 4 + 4 + len(self.key) + 1 + len(self.data)

    def copy(self):
        return ApeTagItem(self.type,
                          self.read_only,
                          self.key,
                          self.data)

    def __repr__(self):
        return "ApeTagItem(%s,%s,%s,%s)" % \
            (repr(self.type),
             repr(self.read_only),
             repr(self.key),
             repr(self.data))

    def raw_info_pair(self):
        if (self.type == 0):    # text
            if (self.read_only):
                return (self.key.decode('ascii'),
                        u"(read only) %s" % (self.data.decode('utf-8')))
            else:
                return (self.key.decode('ascii'), self.data.decode('utf-8'))
        elif (self.type == 1):  # binary
            return (self.key.decode('ascii'),
                    u"(binary) %d bytes" % (len(self.data)))
        elif (self.type == 2):  # external
            return (self.key.decode('ascii'),
                    u"(external) %d bytes" % (len(self.data)))
        else:                   # reserved
            return (self.key.decode('ascii'),
                    u"(reserved) %d bytes" % (len(self.data)))

    def __str__(self):
        return self.data

    def __unicode__(self):
        return self.data.rstrip(chr(0)).decode('utf-8', 'replace')

    @classmethod
    def parse(cls, reader):
        (item_value_length,
         read_only,
         encoding) = reader.parse(cls.FORMAT)

        key = []
        c = reader.read(8)
        while (c != 0):
            key.append(chr(c))
            c = reader.read(8)

        value = reader.read_bytes(item_value_length)

        return cls(encoding, read_only, "".join(key), value)

    def build(self, writer):
        writer.build("%s %db 8u %db" % (self.FORMAT,
                                        len(self.key),
                                        len(self.data)),
                     (len(self.data),
                      self.read_only,
                      self.type,
                      self.key, 0, self.data))

    @classmethod
    def binary(cls, key, data):
        """Returns an ApeTagItem of binary data.

        key is an ASCII string, data is a binary string."""

        return cls(1, False, key, data)

    @classmethod
    def external(cls, key, data):
        """Returns an ApeTagItem of external data.

        key is an ASCII string, data is a binary string."""

        return cls(2, False, key, data)

    @classmethod
    def string(cls, key, data):
        """Returns an ApeTagItem of text data.

        key is an ASCII string, data is a UTF-8 binary string."""

        return cls(0, False, key, data.encode('utf-8', 'replace'))


class ApeTag(MetaData):
    """A complete APEv2 tag."""

    HEADER_FORMAT = "8b 32u 32u 32u [ 1u 2u 26p 1u 1u 1u ] 64p"

    ITEM = ApeTagItem

    ATTRIBUTE_MAP = {'track_name': 'Title',
                     'track_number': 'Track',
                     'track_total': 'Track',
                     'album_number': 'Media',
                     'album_total': 'Media',
                     'album_name': 'Album',
                     'artist_name': 'Artist',
                     #"Performer" is not a defined APEv2 key
                     #it would be nice to have, yet would not be standard
                     'performer_name': 'Performer',
                     'composer_name': 'Composer',
                     'conductor_name': 'Conductor',
                     'ISRC': 'ISRC',
                     'catalog': 'Catalog',
                     'copyright': 'Copyright',
                     'publisher': 'Publisher',
                     'year': 'Year',
                     'date': 'Record Date',
                     'comment': 'Comment'}

    INTEGER_ITEMS = ('Track', 'Media')

    def __init__(self, tags, contains_header=True, contains_footer=True):
        """Constructs an ApeTag from a list of ApeTagItem objects."""

        for tag in tags:
            if (not isinstance(tag, ApeTagItem)):
                raise ValueError("%s is not ApeTag" % (repr(tag)))
        self.__dict__["tags"] = list(tags)
        self.__dict__["contains_header"] = contains_header
        self.__dict__["contains_footer"] = contains_footer

    def __repr__(self):
        return "ApeTag(%s, %s, %s)" % (repr(self.tags),
                                       repr(self.contains_header),
                                       repr(self.contains_footer))

    def total_size(self):
        size = 0
        if (self.contains_header):
            size += 32
        for tag in self.tags:
            size += tag.total_size()
        if (self.contains_footer):
            size += 32
        return size

    def __eq__(self, metadata):
        if (isinstance(metadata, ApeTag)):
            if (set(self.keys()) != set(metadata.keys())):
                return False

            for tag in self.tags:
                try:
                    if (tag.data != metadata[tag.key].data):
                        return False
                except KeyError:
                    return False
            else:
                return True
        elif (isinstance(metadata, MetaData)):
            return MetaData.__eq__(self, metadata)
        else:
            return False

    def keys(self):
        return [tag.key for tag in self.tags]

    def __contains__(self, key):
        for tag in self.tags:
            if (tag.key == key):
                return True
        else:
            return False

    def __getitem__(self, key):
        for tag in self.tags:
            if (tag.key == key):
                return tag
        else:
            raise KeyError(key)

    def get(self, key, default):
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        for i in xrange(len(self.tags)):
            if (self.tags[i].key == key):
                self.tags[i] = value
                return
        else:
            self.tags.append(value)

    def index(self, key):
        for (i, tag) in enumerate(self.tags):
            if (tag.key == key):
                return i
        else:
            raise ValueError(key)

    def __delitem__(self, key):
        for i in xrange(len(self.tags)):
            if (self.tags[i].key == key):
                del(self.tags[i])
                return
        else:
            raise KeyError(key)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        if (key in self.ATTRIBUTE_MAP):
            if (key == 'track_number'):
                self['Track'] = self.ITEM.string(
                    'Track', __number_pair__(value, self.track_total))
            elif (key == 'track_total'):
                self['Track'] = self.ITEM.string(
                    'Track', __number_pair__(self.track_number, value))
            elif (key == 'album_number'):
                self['Media'] = self.ITEM.string(
                    'Media', __number_pair__(value, self.album_total))
            elif (key == 'album_total'):
                self['Media'] = self.ITEM.string(
                    'Media', __number_pair__(self.album_number, value))
            else:
                self[self.ATTRIBUTE_MAP[key]] = self.ITEM.string(
                    self.ATTRIBUTE_MAP[key], value)
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):
        if (key == 'track_number'):
            try:
                return int(re.findall('\d+',
                                      unicode(self.get("Track", u"0")))[0])
            except IndexError:
                return 0
        elif (key == 'track_total'):
            try:
                return int(re.findall('\d+/(\d+)',
                                      unicode(self.get("Track", u"0")))[0])
            except IndexError:
                return 0
        elif (key == 'album_number'):
            try:
                return int(re.findall('\d+',
                                      unicode(self.get("Media", u"0")))[0])
            except IndexError:
                return 0
        elif (key == 'album_total'):
            try:
                return int(re.findall('\d+/(\d+)',
                                      unicode(self.get("Media", u"0")))[0])
            except IndexError:
                return 0
        elif (key in self.ATTRIBUTE_MAP):
            return unicode(self.get(self.ATTRIBUTE_MAP[key], u''))
        elif (key in MetaData.FIELDS):
            return u''
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __delattr__(self, key):
        if (key == 'track_number'):
            setattr(self, 'track_number', 0)
            if ((self.track_number == 0) and (self.track_total == 0)):
                del(self['Track'])
        elif (key == 'track_total'):
            setattr(self, 'track_total', 0)
            if ((self.track_number == 0) and (self.track_total == 0)):
                del(self['Track'])
        elif (key == 'album_number'):
            setattr(self, 'album_number', 0)
            if ((self.album_number == 0) and (self.album_total == 0)):
                del(self['Media'])
        elif (key == 'album_total'):
            setattr(self, 'album_total', 0)
            if ((self.album_number == 0) and (self.album_total == 0)):
                del(self['Media'])
        elif (key in self.ATTRIBUTE_MAP):
            try:
                del(self[self.ATTRIBUTE_MAP[key]])
            except ValueError:
                pass
        elif (key in MetaData.FIELDS):
            pass
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to an ApeTag object."""

        if (metadata is None):
            return None
        elif (isinstance(metadata, ApeTag)):
            return ApeTag([tag.copy() for tag in metadata.tags],
                          contains_header=metadata.contains_header,
                          contains_footer=metadata.contains_footer)
        else:
            tags = cls([])
            for (field, key) in cls.ATTRIBUTE_MAP.items():
                if (field not in cls.INTEGER_FIELDS):
                    field = unicode(getattr(metadata, field))
                    if (len(field) > 0):
                        tags[key] = cls.ITEM.string(key, field)

            if ((metadata.track_number != 0) or
                (metadata.track_total != 0)):
                tags["Track"] = cls.ITEM.string(
                    "Track", __number_pair__(metadata.track_number,
                                             metadata.track_total))

            if ((metadata.album_number != 0) or
                (metadata.album_total != 0)):
                tags["Media"] = cls.ITEM.string(
                    "Media", __number_pair__(metadata.album_number,
                                             metadata.album_total))

            for image in metadata.images():
                tags.add_image(image)

            return tags

    def raw_info(self):
        from os import linesep
        from . import display_unicode

        #align tag values on the "=" sign
        if (len(self.tags) > 0):
            max_indent = max([len(display_unicode(tag.raw_info_pair()[0]))
                              for tag in self.tags])
            tag_strings = [u"%s%s = %s" %
                           (u" " * (max_indent - len(display_unicode(key))),
                            key, value) for (key, value) in
                           [tag.raw_info_pair() for tag in self.tags]]
        else:
            tag_strings = []

        return linesep.decode('ascii').join([u"APEv2:"] + tag_strings)

    @classmethod
    def supports_images(cls):
        """Returns True."""

        return True

    def __parse_image__(self, key, type):
        data = cStringIO.StringIO(self[key].data)
        description = []
        c = data.read(1)
        while (c != '\x00'):
            description.append(c)
            c = data.read(1)

        return Image.new(data.read(),
                         "".join(description).decode('utf-8', 'replace'),
                         type)

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        if (image.type == 0):
            self['Cover Art (front)'] = self.ITEM.binary(
                'Cover Art (front)',
                image.description.encode('utf-8', 'replace') +
                chr(0) +
                image.data)
        elif (image.type == 1):
            self['Cover Art (back)'] = self.ITEM.binary(
                'Cover Art (back)',
                image.description.encode('utf-8', 'replace') +
                chr(0) +
                image.data)

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        if ((image.type == 0) and 'Cover Art (front)' in self.keys()):
            del(self['Cover Art (front)'])
        elif ((image.type == 1) and 'Cover Art (back)' in self.keys()):
            del(self['Cover Art (back)'])

    def images(self):
        """Returns a list of embedded Image objects."""

        #APEv2 supports only one value per key
        #so a single front and back cover are all that is possible
        img = []
        if ('Cover Art (front)' in self.keys()):
            img.append(self.__parse_image__('Cover Art (front)', 0))
        if ('Cover Art (back)' in self.keys()):
            img.append(self.__parse_image__('Cover Art (back)', 1))
        return img

    @classmethod
    def read(cls, apefile):
        """Returns an ApeTag object from an APEv2 tagged file object.

        May return None if the file object has no tag."""

        from .bitstream import BitstreamReader

        apefile.seek(-32, 2)
        reader = BitstreamReader(apefile, 1)

        (preamble,
         version,
         tag_size,
         item_count,
         read_only,
         item_encoding,
         is_header,
         no_footer,
         has_header) = reader.parse(cls.HEADER_FORMAT)

        if ((preamble != "APETAGEX") or (version != 2000)):
            return None

        apefile.seek(-tag_size, 2)

        return cls([ApeTagItem.parse(reader)
                    for i in xrange(item_count)],
                   contains_header=has_header,
                   contains_footer=True)

    def build(self, writer):
        """Outputs an APEv2 tag to writer"""

        from .bitstream import BitstreamRecorder

        tags = BitstreamRecorder(1)

        for tag in self.tags:
            tag.build(tags)

        if (self.contains_header):
            writer.build(ApeTag.HEADER_FORMAT,
                         ("APETAGEX",                # preamble
                          2000,                      # version
                          tags.bytes() + 32,         # tag size
                          len(self.tags),            # item count
                          0,                         # read only
                          0,                         # encoding
                          1,                         # is header
                          not self.contains_footer,  # no footer
                          self.contains_header))     # has header

        tags.copy(writer)
        if (self.contains_footer):
            writer.build(ApeTag.HEADER_FORMAT,
                         ("APETAGEX",                # preamble
                          2000,                      # version
                          tags.bytes() + 32,         # tag size
                          len(self.tags),            # item count
                          0,                         # read only
                          0,                         # encoding
                          0,                         # is header
                          not self.contains_footer,  # no footer
                          self.contains_header))     # has header

    def clean(self, fixes_applied):
        tag_items = []
        for tag in self.tags:
            if (tag.type == 0):
                text = unicode(tag)

                #check trailing whitespace
                fix1 = text.rstrip()
                if (fix1 != text):
                    fixes_applied.append(
                        _(u"removed trailing whitespace from %(field)s") %
                        {"field": tag.key.decode('ascii')})

                #check leading whitespace
                fix2 = fix1.lstrip()
                if (fix2 != fix1):
                    fixes_applied.append(
                        _(u"removed leading whitespace from %(field)s") %
                        {"field": tag.key.decode('ascii')})

                if (tag.key in self.INTEGER_ITEMS):
                    try:
                        current = int(re.findall('\d+', fix2)[0])
                    except IndexError:
                        current = 0
                    try:
                        total = int(re.findall('\d+/(\d+)', fix2)[0])
                    except IndexError:
                        total = 0
                    if (total != 0):
                        fix3 = u"%d/%d" % (current, total)
                    else:
                        fix3 = unicode(current)
                    if (fix3 != fix2):
                        fixes_applied.append(
                            _(u"removed leading zeroes from %(field)s") %
                            {"field": tag.key.decode('ascii')})
                else:
                    fix3 = fix2

                if (len(fix3) > 0):
                    tag_items.append(ApeTagItem.string(tag.key, fix3))
                else:
                    fixes_applied.append(
                        _("removed empty field %(field)s") %
                        {"field": tag.key.decode('ascii')})
            else:
                tag_items.append(tag)

        return self.__class__(tag_items,
                              self.contains_header,
                              self.contains_footer)


class ApeTaggedAudio:
    """A class for handling audio formats with APEv2 tags.

    This class presumes there will be a filename attribute which
    can be opened and checked for tags, or written if necessary."""

    def get_metadata(self):
        """Returns an ApeTag object, or None.

        Raises IOError if unable to read the file."""

        f = file(self.filename, 'rb')
        try:
            return ApeTag.read(f)
        finally:
            f.close()

    def update_metadata(self, metadata):
        if (metadata is None):
            return
        elif (not isinstance(metadata, ApeTag)):
            raise ValueError(_(u"metadata not from audio file"))

        from .bitstream import BitstreamReader, BitstreamWriter

        f = file(self.filename, "r+b")
        f.seek(-32, 2)

        (preamble,
         version,
         tag_size,
         item_count,
         read_only,
         item_encoding,
         is_header,
         no_footer,
         has_header) = BitstreamReader(f, 1).parse(ApeTag.HEADER_FORMAT)

        if ((preamble == 'APETAGEX') and (version == 2000)):
            if (has_header):
                old_tag_size = 32 + tag_size
            else:
                old_tag_size = tag_size

            if (metadata.total_size() >= old_tag_size):
                #metadata has grown
                #so append it to existing file
                f.seek(-old_tag_size, 2)
                metadata.build(BitstreamWriter(f, 1))
            else:
                #metadata has shrunk
                #so rewrite file with smaller metadata
                import tempfile
                from os.path import getsize
                rewritten = tempfile.TemporaryFile()

                #copy everything but the last "old_tag_size" bytes
                #from existing file to rewritten file
                f = open(self.filename, "rb")
                limited_transfer_data(f.read, rewritten.write,
                                      os.path.getsize(self.filename) -
                                      old_tag_size)
                f.close()

                #append new tag to rewritten file
                metadata.build(BitstreamWriter(rewritten, 1))

                #finally, overwrite current file with rewritten file
                rewritten.seek(0, 0)
                f = open(self.filename, "wb")
                transfer_data(rewritten.read, f.write)
                f.close()
                rewritten.close()
        else:
            #no existing metadata, so simply append a fresh tag
            f = file(self.filename, "ab")
            metadata.build(BitstreamWriter(f, 1))
            f.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        Raises IOError if unable to write the file."""

        if (metadata is None):
            return

        from .bitstream import BitstreamWriter

        old_metadata = self.get_metadata()
        new_metadata = ApeTag.converted(metadata)

        if (old_metadata is not None):
            #transfer ReplayGain tags from old metadata to new metadata
            for tag in ["replaygain_track_gain",
                        "replaygain_track_peak",
                        "replaygain_album_gain",
                        "replaygain_album_peak"]:
                try:
                    #if old_metadata has tag, shift it over
                    new_metadata[tag] = old_metadata[tag]
                except KeyError:
                    try:
                        #otherwise, if new_metadata has tag, delete it
                        del(new_metadata[tag])
                    except KeyError:
                        #if neither has tag, ignore it
                        continue

            #transfer Cuesheet from old metadata to new metadata
            if ("Cuesheet" in old_metadata):
                new_metadata["Cuesheet"] = old_metadata["Cuesheet"]
            elif ("Cuesheet" in new_metadata):
                del(new_metadata["Cuesheet"])

            self.update_metadata(new_metadata)
        else:
            #delete ReplayGain tags from new metadata
            for tag in ["replaygain_track_gain",
                        "replaygain_track_peak",
                        "replaygain_album_gain",
                        "replaygain_album_peak"]:
                try:
                    del(new_metadata[tag])
                except KeyError:
                    continue

            #delete Cuesheet from new metadata
            if ("Cuesheet" in new_metadata):
                del(new_metadata["Cuesheet"])

            #no existing metadata, so simply append a fresh tag
            f = file(self.filename, "ab")
            new_metadata.build(BitstreamWriter(f, 1))
            f.close()

    def delete_metadata(self):
        """Deletes the track's MetaData.

        Raises IOError if unable to write the file."""

        from .bitstream import BitstreamReader, BitstreamWriter

        f = file(self.filename, "r+b")
        f.seek(-32, 2)

        (preamble,
         version,
         tag_size,
         item_count,
         read_only,
         item_encoding,
         is_header,
         no_footer,
         has_header) = BitstreamReader(f, 1).parse(ApeTag.HEADER_FORMAT)

        if ((preamble == 'APETAGEX') and (version == 2000)):
            #there's existing metadata to delete
            #so rewrite file without trailing metadata tag
            if (has_header):
                old_tag_size = 32 + tag_size
            else:
                old_tag_size = tag_size

            import tempfile
            from os.path import getsize
            rewritten = tempfile.TemporaryFile()

            #copy everything but the last "old_tag_size" bytes
            #from existing file to rewritten file
            f = open(self.filename, "rb")
            limited_transfer_data(f.read, rewritten.write,
                                  os.path.getsize(self.filename) -
                                  old_tag_size)
            f.close()

            #finally, overwrite current file with rewritten file
            rewritten.seek(0, 0)
            f = open(self.filename, "wb")
            transfer_data(rewritten.read, f.write)
            f.close()
            rewritten.close()


class ApeAudio(ApeTaggedAudio, AudioFile):
    """A Monkey's Audio file."""

    SUFFIX = "ape"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "5000"
    COMPRESSION_MODES = tuple([str(x * 1000) for x in range(1, 6)])
    BINARIES = ("mac",)

    # FILE_HEAD = Con.Struct("ape_head",
    #                        Con.String('id', 4),
    #                        Con.ULInt16('version'))

    # #version >= 3.98
    # APE_DESCRIPTOR = Con.Struct("ape_descriptor",
    #                             Con.ULInt16('padding'),
    #                             Con.ULInt32('descriptor_bytes'),
    #                             Con.ULInt32('header_bytes'),
    #                             Con.ULInt32('seektable_bytes'),
    #                             Con.ULInt32('header_data_bytes'),
    #                             Con.ULInt32('frame_data_bytes'),
    #                             Con.ULInt32('frame_data_bytes_high'),
    #                             Con.ULInt32('terminating_data_bytes'),
    #                             Con.String('md5', 16))

    # APE_HEADER = Con.Struct("ape_header",
    #                         Con.ULInt16('compression_level'),
    #                         Con.ULInt16('format_flags'),
    #                         Con.ULInt32('blocks_per_frame'),
    #                         Con.ULInt32('final_frame_blocks'),
    #                         Con.ULInt32('total_frames'),
    #                         Con.ULInt16('bits_per_sample'),
    #                         Con.ULInt16('number_of_channels'),
    #                         Con.ULInt32('sample_rate'))

    # #version <= 3.97
    # APE_HEADER_OLD = Con.Struct("ape_header_old",
    #                             Con.ULInt16('compression_level'),
    #                             Con.ULInt16('format_flags'),
    #                             Con.ULInt16('number_of_channels'),
    #                             Con.ULInt32('sample_rate'),
    #                             Con.ULInt32('header_bytes'),
    #                             Con.ULInt32('terminating_bytes'),
    #                             Con.ULInt32('total_frames'),
    #                             Con.ULInt32('final_frame_blocks'))

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)

        (self.__samplespersec__,
         self.__channels__,
         self.__bitspersample__,
         self.__totalsamples__) = ApeAudio.__ape_info__(filename)

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        return file.read(4) == "MAC "

    def lossless(self):
        """Returns True."""

        return True

    @classmethod
    def supports_foreign_riff_chunks(cls):
        """Returns True."""

        return True

    def has_foreign_riff_chunks(self):
        """Returns True."""

        #FIXME - this isn't strictly true
        #I'll need a way to detect foreign chunks in APE's stream
        #without decoding it first,
        #but since I'm not supporting APE anyway, I'll take the lazy way out
        return True

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bitspersample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__totalsamples__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__samplespersec__

    @classmethod
    def __ape_info__(cls, filename):
        f = file(filename, 'rb')
        try:
            file_head = cls.FILE_HEAD.parse_stream(f)

            if (file_head.id != 'MAC '):
                raise InvalidFile(_(u"Invalid Monkey's Audio header"))

            if (file_head.version >= 3980):  # the latest APE file type
                descriptor = cls.APE_DESCRIPTOR.parse_stream(f)
                header = cls.APE_HEADER.parse_stream(f)

                return (header.sample_rate,
                        header.number_of_channels,
                        header.bits_per_sample,
                        ((header.total_frames - 1) * \
                         header.blocks_per_frame) + \
                         header.final_frame_blocks)
            else:                           # old-style APE file (obsolete)
                header = cls.APE_HEADER_OLD.parse_stream(f)

                if (file_head.version >= 3950):
                    blocks_per_frame = 0x48000
                elif ((file_head.version >= 3900) or
                      ((file_head.version >= 3800) and
                       (header.compression_level == 4000))):
                    blocks_per_frame = 0x12000
                else:
                    blocks_per_frame = 0x2400

                if (header.format_flags & 0x01):
                    bits_per_sample = 8
                elif (header.format_flags & 0x08):
                    bits_per_sample = 24
                else:
                    bits_per_sample = 16

                return (header.sample_rate,
                        header.number_of_channels,
                        bits_per_sample,
                        ((header.total_frames - 1) * \
                         blocks_per_frame) + \
                         header.final_frame_blocks)

        finally:
            f.close()

    def to_wave(self, wave_filename):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        if (self.filename.endswith(".ape")):
            devnull = file(os.devnull, "wb")
            sub = subprocess.Popen([BIN['mac'],
                                    self.filename,
                                    wave_filename,
                                    '-d'],
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()
        else:
            devnull = file(os.devnull, 'ab')
            import tempfile
            ape = tempfile.NamedTemporaryFile(suffix='.ape')
            f = file(self.filename, 'rb')
            transfer_data(f.read, ape.write)
            f.close()
            ape.flush()
            sub = subprocess.Popen([BIN['mac'],
                                    ape.name,
                                    wave_filename,
                                    '-d'],
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            ape.close()
            devnull.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new ApeAudio object."""

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        devnull = file(os.devnull, "wb")
        sub = subprocess.Popen([BIN['mac'],
                                wave_filename,
                                filename,
                                "-c%s" % (compression)],
                               stdout=devnull,
                               stderr=devnull)
        sub.wait()
        devnull.close()
        return ApeAudio(filename)
