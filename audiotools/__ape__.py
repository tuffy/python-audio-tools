#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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
                        Con, transfer_data, subprocess, BIN, MetaData,
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


#######################
#MONKEY'S AUDIO
#######################


class ApeTagItem:
    """A container for APEv2 tag items."""

    APEv2_FLAGS = Con.BitStruct("APEv2_FLAGS",
      Con.Bits("undefined1", 5),
      Con.Flag("read_only"),
      Con.Bits("encoding", 2),
      Con.Bits("undefined2", 16),
      Con.Flag("contains_header"),
      Con.Flag("contains_no_footer"),
      Con.Flag("is_header"),
      Con.Bits("undefined3", 5))

    APEv2_TAG = Con.Struct("APEv2_TAG",
      Con.ULInt32("length"),
      Con.Embed(APEv2_FLAGS),
      Con.CString("key"),
      Con.MetaField("value",
        lambda ctx: ctx["length"]))


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

    def __repr__(self):
        return "ApeTagItem(%s,%s,%s,%s)" % \
            (repr(self.type),
             repr(self.read_only),
             repr(self.key),
             repr(self.data))

    def __str__(self):
        return self.data

    def __unicode__(self):
        return self.data.rstrip(chr(0)).decode('utf-8', 'replace')

    def build(self):
        """Returns this tag as a binary string of data."""

        return self.APEv2_TAG.build(
            Con.Container(key=self.key,
                          value=self.data,
                          length=len(self.data),
                          encoding=self.type,
                          undefined1=0,
                          undefined2=0,
                          undefined3=0,
                          read_only=self.read_only,
                          contains_header=False,
                          contains_no_footer=False,
                          is_header=False))


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

    ITEM = ApeTagItem

    APEv2_FLAGS = Con.BitStruct("APEv2_FLAGS",
      Con.Bits("undefined1", 5),
      Con.Flag("read_only"),
      Con.Bits("encoding", 2),
      Con.Bits("undefined2", 16),
      Con.Flag("contains_header"),
      Con.Flag("contains_no_footer"),
      Con.Flag("is_header"),
      Con.Bits("undefined3", 5))

    APEv2_FOOTER = Con.Struct("APEv2",
      Con.String("preamble", 8),
      Con.ULInt32("version_number"),
      Con.ULInt32("tag_size"),
      Con.ULInt32("item_count"),
      Con.Embed(APEv2_FLAGS),
      Con.ULInt64("reserved"))

    APEv2_HEADER = APEv2_FOOTER

    APEv2_TAG = ApeTagItem.APEv2_TAG

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


    def __init__(self, tags, tag_length=None):
        """Constructs an ApeTag from a list of ApeTagItem objects.

        tag_length is an optional total length integer."""

        for tag in tags:
            if (not isinstance(tag, ApeTagItem)):
                raise ValueError("%s is not ApeTag" % (repr(tag)))
        self.__dict__["tags"] = tags
        self.__dict__["tag_length"] = tag_length

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
        elif (key in MetaData.__FIELDS__):
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
        elif (key in MetaData.__FIELDS__):
            pass
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to an ApeTag object."""

        if ((metadata is None) or (isinstance(metadata, ApeTag))):
            return metadata
        else:
            tags = cls([])
            for (field, key) in cls.ATTRIBUTE_MAP.items():
                if (field not in cls.__INTEGER_FIELDS__):
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

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        metadata = self.__class__.converted(metadata)
        if (metadata is None):
            return

        for tag in metadata.tags:
            if ((tag.key not in ('Track', 'Media')) and
                (len(str(tag)) > 0) and
                (len(str(self.get(tag.key, ""))) == 0)):
                self[tag.key] = tag
        for attr in ("track_number", "track_total",
                     "album_number", "album_total"):
            if ((getattr(self, attr) == 0) and
                (getattr(metadata, attr) != 0)):
                setattr(self, attr, getattr(metadata, attr))

    def __comment_name__(self):
        return u'APEv2'

    #takes two (key,value) apetag pairs
    #returns cmp on the weighted set of them
    #(title first, then artist, album, tracknumber)
    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {"Title": 1,
                   "Album": 2,
                   "Track": 3,
                   "Media": 4,
                   "Artist": 5,
                   "Performer": 6,
                   "Composer": 7,
                   "Conductor": 8,
                   "Catalog": 9,
                   "Publisher": 10,
                   "ISRC": 11,
                   #"Media": 12,
                   "Year": 13,
                   "Record Date": 14,
                   "Copyright": 15}

        return cmp((KEY_MAP.get(pair1[0], 16), pair1[0], pair1[1]),
                   (KEY_MAP.get(pair2[0], 16), pair2[0], pair2[1]))

    def __comment_pairs__(self):
        items = []

        for tag in self.tags:
            if (tag.key in ('Cover Art (front)', 'Cover Art (back)')):
                pass
            elif (tag.type == 0):
                items.append((tag.key, unicode(tag)))
            else:
                if (len(str(tag)) <= 20):
                    items.append((tag.key, str(tag).encode('hex')))
                else:
                    items.append((tag.key,
                                  str(tag).encode('hex')[0:39].upper() +
                                  u"\u2026"))

        return sorted(items, ApeTag.__by_pair__)

    @classmethod
    def supports_images(cls):
        """Returns True."""

        return True

    def __parse_image__(self, key, type):
        data = cStringIO.StringIO(str(self[key]))
        description = Con.CString(None).parse_stream(data).decode('utf-8',
                                                                  'replace')
        data = data.read()
        return Image.new(data, description, type)

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        if (image.type == 0):
            self['Cover Art (front)'] = self.ITEM.external(
                'Cover Art (front)',
                Con.CString(None).build(image.description.encode(
                        'utf-8', 'replace')) + image.data)
        elif (image.type == 1):
            self['Cover Art (back)'] = self.ITEM.binary(
                'Cover Art (back)',
                Con.CString(None).build(image.description.encode(
                        'utf-8', 'replace')) + image.data)

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

        apefile.seek(-32, 2)
        footer = cls.APEv2_FOOTER.parse(apefile.read(32))

        if (footer.preamble != 'APETAGEX'):
            return None

        apefile.seek(-(footer.tag_size), 2)

        return cls([ApeTagItem(item_type=tag.encoding,
                               read_only=tag.read_only,
                               key=tag.key,
                               data=tag.value)
                    for tag in Con.StrictRepeater(
                      footer.item_count,
                      cls.APEv2_TAG).parse(apefile.read())],
                   tag_length=footer.tag_size + ApeTag.APEv2_FOOTER.sizeof()
                     if footer.contains_header else
                     footer.tag_size)

    def build(self):
        """Returns an APEv2 tag as a binary string."""

        header = Con.Container(preamble='APETAGEX',
                               version_number=2000,
                               tag_size=0,
                               item_count=len(self.tags),
                               undefined1=0,
                               undefined2=0,
                               undefined3=0,
                               read_only=False,
                               encoding=0,
                               contains_header=True,
                               contains_no_footer=False,
                               is_header=True,
                               reserved=0l)

        footer = Con.Container(preamble=header.preamble,
                               version_number=header.version_number,
                               tag_size=0,
                               item_count=len(self.tags),
                               undefined1=0,
                               undefined2=0,
                               undefined3=0,
                               read_only=False,
                               encoding=0,
                               contains_header=True,
                               contains_no_footer=False,
                               is_header=False,
                               reserved=0l)

        tags = "".join([tag.build() for tag in self.tags])

        footer.tag_size = header.tag_size = \
          len(tags) + len(ApeTag.APEv2_FOOTER.build(footer))

        return ApeTag.APEv2_FOOTER.build(header) + \
               tags + \
               ApeTag.APEv2_FOOTER.build(footer)


class ApeTaggedAudio:
    """A class for handling audio formats with APEv2 tags.

    This class presumes there will be a filename attribute which
    can be opened and checked for tags, or written if necessary."""

    APE_TAG_CLASS = ApeTag

    def get_metadata(self):
        """Returns an ApeTag object, or None.

        Raises IOError if unable to read the file."""

        f = file(self.filename, 'rb')
        try:
            return self.APE_TAG_CLASS.read(f)
        finally:
            f.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        Raises IOError if unable to write the file."""

        apetag = self.APE_TAG_CLASS.converted(metadata)

        if (apetag is None):
            return

        current_metadata = self.get_metadata()
        if (current_metadata is not None):  # there's existing tags to delete
            f = file(self.filename, "rb")
            untagged_data = f.read()[0:-current_metadata.tag_length]
            f.close()
            f = file(self.filename, "wb")
            f.write(untagged_data)
            f.write(apetag.build())
            f.close()
        else:                               # no existing tags
            f = file(self.filename, "ab")
            f.write(apetag.build())
            f.close()

    def delete_metadata(self):
        """Deletes the track's MetaData.

        Raises IOError if unable to write the file."""

        current_metadata = self.get_metadata()
        if (current_metadata is not None):  # there's existing tags to delete
            f = file(self.filename, "rb")
            untagged_data = f.read()[0:-current_metadata.tag_length]
            f.close()
            f = file(self.filename, "wb")
            f.write(untagged_data)
            f.close()


class ApeAudio(ApeTaggedAudio, AudioFile):
    """A Monkey's Audio file."""

    SUFFIX = "ape"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "5000"
    COMPRESSION_MODES = tuple([str(x * 1000) for x in range(1, 6)])
    BINARIES = ("mac",)

    FILE_HEAD = Con.Struct("ape_head",
                           Con.String('id', 4),
                           Con.ULInt16('version'))

    #version >= 3.98
    APE_DESCRIPTOR = Con.Struct("ape_descriptor",
                                Con.ULInt16('padding'),
                                Con.ULInt32('descriptor_bytes'),
                                Con.ULInt32('header_bytes'),
                                Con.ULInt32('seektable_bytes'),
                                Con.ULInt32('header_data_bytes'),
                                Con.ULInt32('frame_data_bytes'),
                                Con.ULInt32('frame_data_bytes_high'),
                                Con.ULInt32('terminating_data_bytes'),
                                Con.String('md5', 16))

    APE_HEADER = Con.Struct("ape_header",
                            Con.ULInt16('compression_level'),
                            Con.ULInt16('format_flags'),
                            Con.ULInt32('blocks_per_frame'),
                            Con.ULInt32('final_frame_blocks'),
                            Con.ULInt32('total_frames'),
                            Con.ULInt16('bits_per_sample'),
                            Con.ULInt16('number_of_channels'),
                            Con.ULInt32('sample_rate'))

    #version <= 3.97
    APE_HEADER_OLD = Con.Struct("ape_header_old",
                                Con.ULInt16('compression_level'),
                                Con.ULInt16('format_flags'),
                                Con.ULInt16('number_of_channels'),
                                Con.ULInt32('sample_rate'),
                                Con.ULInt32('header_bytes'),
                                Con.ULInt32('terminating_bytes'),
                                Con.ULInt32('total_frames'),
                                Con.ULInt32('final_frame_blocks'))

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
