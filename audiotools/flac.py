#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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


from . import (AudioFile, MetaData, InvalidFile, Image,
               WaveContainer, AiffContainer)
from .vorbiscomment import VorbisComment
from .id3 import skip_id3v2_comment


#######################
#FLAC
#######################


class InvalidFLAC(InvalidFile):
    pass


class FlacMetaDataBlockTooLarge(Exception):
    """raised if one attempts to build a FlacMetaDataBlock too large"""

    pass


class FlacMetaData(MetaData):
    """a class for managing a native FLAC's metadata"""

    def __init__(self, blocks):
        self.__dict__["block_list"] = list(blocks)

    def has_block(self, block_id):
        """returns True if the given block ID is present"""

        return block_id in [b.BLOCK_ID for b in self.block_list]

    def add_block(self, block):
        """adds the given block to our list of blocks"""

        #the specification only requires that STREAMINFO be first
        #the rest are largely arbitrary,
        #though I like to keep PADDING as the last block for aesthetic reasons
        PREFERRED_ORDER = [Flac_STREAMINFO.BLOCK_ID,
                           Flac_SEEKTABLE.BLOCK_ID,
                           Flac_CUESHEET.BLOCK_ID,
                           Flac_VORBISCOMMENT.BLOCK_ID,
                           Flac_PICTURE.BLOCK_ID,
                           Flac_APPLICATION.BLOCK_ID,
                           Flac_PADDING.BLOCK_ID]

        stop_blocks = set(
            PREFERRED_ORDER[PREFERRED_ORDER.index(block.BLOCK_ID) + 1:])

        for (index, old_block) in enumerate(self.block_list):
            if (old_block.BLOCK_ID in stop_blocks):
                self.block_list.insert(index, block)
                break
        else:
            self.block_list.append(block)

    def get_block(self, block_id):
        """returns the first instance of the given block_id

        may raise IndexError if the block is not in our list of blocks"""

        for block in self.block_list:
            if (block.BLOCK_ID == block_id):
                return block
        else:
            raise IndexError()

    def get_blocks(self, block_id):
        """returns all instances of the given block_id in our list of blocks"""

        return [b for b in self.block_list if (b.BLOCK_ID == block_id)]

    def replace_blocks(self, block_id, blocks):
        """replaces all instances of the given block_id with
        blocks taken from the given list

        if insufficient matching blocks are present,
        this uses add_block() to populate the remainder

        if additional matching blocks are present,
        they are removed
        """

        new_blocks = []

        for block in self.block_list:
            if (block.BLOCK_ID == block_id):
                if (len(blocks) > 0):
                    new_blocks.append(blocks.pop(0))
                else:
                    pass
            else:
                new_blocks.append(block)

        self.block_list = new_blocks

        while (len(blocks) > 0):
            self.add_block(blocks.pop(0))

    def __setattr__(self, key, value):
        if (key in self.FIELDS):
            try:
                vorbis_comment = self.get_block(Flac_VORBISCOMMENT.BLOCK_ID)
            except IndexError:
                #add VORBIS comment block if necessary
                from . import VERSION

                vorbis_comment = Flac_VORBISCOMMENT(
                    [], u"Python Audio Tools %s" % (VERSION))

                self.add_block(vorbis_comment)

            setattr(vorbis_comment, key, value)
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):
        if (key in self.FIELDS):
            try:
                return getattr(self.get_block(Flac_VORBISCOMMENT.BLOCK_ID),
                               key)
            except IndexError:
                #no VORBIS comment block, so all values are None
                return None
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __delattr__(self, key):
        if (key in self.FIELDS):
            try:
                delattr(self.get_block(Flac_VORBISCOMMENT.BLOCK_ID), key)
            except IndexError:
                #no VORBIS comment block, so nothing to delete
                pass
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    @classmethod
    def converted(cls, metadata):
        """takes a MetaData object and returns a FlacMetaData object"""

        if (metadata is None):
            return None
        elif (isinstance(metadata, FlacMetaData)):
            return cls([block.copy() for block in metadata.block_list])
        else:
            return cls([Flac_VORBISCOMMENT.converted(metadata)] +
                       [Flac_PICTURE.converted(image)
                        for image in metadata.images()] +
                       [Flac_PADDING(4096)])

    def add_image(self, image):
        """embeds an Image object in this metadata"""

        self.add_block(Flac_PICTURE.converted(image))

    def delete_image(self, image):
        """deletes an image object from this metadata"""

        self.block_list = [b for b in self.block_list
                           if not ((b.BLOCK_ID == Flac_PICTURE.BLOCK_ID) and
                                   (b == image))]

    def images(self):
        """returns a list of embedded Image objects"""

        return self.get_blocks(Flac_PICTURE.BLOCK_ID)

    @classmethod
    def supports_images(cls):
        """returns True"""

        return True

    def clean(self, fixes_performed):
        """returns a new FlacMetaData object that's been cleaned of problems

        any fixes performed are appended to fixes_performed as unicode"""

        from .text import (CLEAN_FLAC_REORDERED_STREAMINFO,
                           CLEAN_FLAC_MULITPLE_STREAMINFO,
                           CLEAN_FLAC_MULTIPLE_VORBISCOMMENT,
                           CLEAN_FLAC_MULTIPLE_SEEKTABLE,
                           CLEAN_FLAC_MULTIPLE_CUESHEET,
                           CLEAN_FLAC_UNDEFINED_BLOCK)

        cleaned_blocks = []

        for block in self.block_list:
            if (block.BLOCK_ID == Flac_STREAMINFO.BLOCK_ID):
                #reorder STREAMINFO block to be first, if necessary
                if (len(cleaned_blocks) == 0):
                    cleaned_blocks.append(block)
                elif (cleaned_blocks[0].BLOCK_ID != block.BLOCK_ID):
                    fixes_performed.append(
                        CLEAN_FLAC_REORDERED_STREAMINFO)
                    cleaned_blocks.insert(0, block)
                else:
                    fixes_performed.append(
                        CLEAN_FLAC_MULITPLE_STREAMINFO)
            elif (block.BLOCK_ID == Flac_VORBISCOMMENT.BLOCK_ID):
                if (block.BLOCK_ID in [b.BLOCK_ID for b in cleaned_blocks]):
                    #remove redundant VORBIS_COMMENT blocks
                    fixes_performed.append(
                        CLEAN_FLAC_MULTIPLE_VORBISCOMMENT)
                else:
                    #recursively clean up the text fields in FlacVorbisComment
                    cleaned_blocks.append(block.clean(fixes_performed))
            elif (block.BLOCK_ID == Flac_PICTURE.BLOCK_ID):
                #recursively clean up any image blocks
                cleaned_blocks.append(block.clean(fixes_performed))
            elif (block.BLOCK_ID == Flac_APPLICATION.BLOCK_ID):
                cleaned_blocks.append(block)
            elif (block.BLOCK_ID == Flac_SEEKTABLE.BLOCK_ID):
                #remove redundant seektable, if necessary
                if (block.BLOCK_ID in [b.BLOCK_ID for b in cleaned_blocks]):
                    fixes_performed.append(
                        CLEAN_FLAC_MULTIPLE_SEEKTABLE)
                else:
                    cleaned_blocks.append(block.clean(fixes_performed))
            elif (block.BLOCK_ID == Flac_CUESHEET.BLOCK_ID):
                #remove redundant cuesheet, if necessary
                if (block.BLOCK_ID in [b.BLOCK_ID for b in cleaned_blocks]):
                    fixes_performed.append(
                        CLEAN_FLAC_MULTIPLE_CUESHEET)
                else:
                    cleaned_blocks.append(block)
            elif (block.BLOCK_ID == Flac_PADDING.BLOCK_ID):
                cleaned_blocks.append(block)
            else:
                #remove undefined blocks
                fixes_performed.append(CLEAN_FLAC_UNDEFINED_BLOCK)

        return self.__class__(cleaned_blocks)

    def __repr__(self):
        return "FlacMetaData(%s)" % (self.block_list)

    @classmethod
    def parse(cls, reader):
        """returns a FlacMetaData object from the given BitstreamReader
        which has already parsed the 4-byte 'fLaC' file ID"""

        block_list = []

        last = 0

        while (last != 1):
            (last, block_type, block_length) = reader.parse("1u7u24u")

            if (block_type == 0):    # STREAMINFO
                block_list.append(
                    Flac_STREAMINFO.parse(reader.substream(block_length)))
            elif (block_type == 1):  # PADDING
                block_list.append(
                    Flac_PADDING.parse(
                        reader.substream(block_length), block_length))
            elif (block_type == 2):  # APPLICATION
                block_list.append(
                    Flac_APPLICATION.parse(
                        reader.substream(block_length), block_length))
            elif (block_type == 3):  # SEEKTABLE
                block_list.append(
                    Flac_SEEKTABLE.parse(
                        reader.substream(block_length), block_length / 18))
            elif (block_type == 4):  # VORBIS_COMMENT
                block_list.append(
                    Flac_VORBISCOMMENT.parse(
                        reader.substream(block_length)))
            elif (block_type == 5):  # CUESHEET
                block_list.append(
                    Flac_CUESHEET.parse(reader.substream(block_length)))
            elif (block_type == 6):  # PICTURE
                block_list.append(
                    Flac_PICTURE.parse(reader.substream(block_length)))
            elif ((block_type >= 7) and (block_type <= 126)):
                from .text import ERR_FLAC_RESERVED_BLOCK
                raise ValueError(ERR_FLAC_RESERVED_BLOCK % (block_type))
            else:
                from .text import ERR_FLAC_INVALID_BLOCK
                raise ValueError(ERR_FLAC_INVALID_BLOCK)

        return cls(block_list)

    def raw_info(self):
        """returns human-readable metadata as a unicode string"""

        from os import linesep

        return linesep.decode('ascii').join(
            ["FLAC Tags:"] + [block.raw_info() for block in self.blocks()])

    def blocks(self):
        """yields FlacMetaData's individual metadata blocks"""

        for block in self.block_list:
            yield block

    def build(self, writer):
        """writes the FlacMetaData to the given BitstreamWriter
        not including the 4-byte 'fLaC' file ID"""

        from . import iter_last

        for (last_block,
             block) in iter_last(iter([b for b in self.blocks()
                                       if (b.size() < (2 ** 24))])):
            if (not last_block):
                writer.build("1u7u24u", (0, block.BLOCK_ID, block.size()))
            else:
                writer.build("1u7u24u", (1, block.BLOCK_ID, block.size()))

            block.build(writer)

    def size(self):
        """returns the size of all metadata blocks
        including the block headers
        but not including the 4-byte 'fLaC' file ID"""

        from operator import add

        return reduce(add, [4 + b.size() for b in self.block_list], 0)


class Flac_STREAMINFO:
    BLOCK_ID = 0

    def __init__(self, minimum_block_size, maximum_block_size,
                 minimum_frame_size, maximum_frame_size,
                 sample_rate, channels, bits_per_sample,
                 total_samples, md5sum):
        """all values are non-negative integers except for md5sum
        which is a 16-byte binary string"""

        self.minimum_block_size = minimum_block_size
        self.maximum_block_size = maximum_block_size
        self.minimum_frame_size = minimum_frame_size
        self.maximum_frame_size = maximum_frame_size
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.total_samples = total_samples
        self.md5sum = md5sum

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_STREAMINFO(self.minimum_block_size,
                               self.maximum_block_size,
                               self.minimum_frame_size,
                               self.maximum_frame_size,
                               self.sample_rate,
                               self.channels,
                               self.bits_per_sample,
                               self.total_samples,
                               self.md5sum)

    def __eq__(self, block):
        for attr in ["minimum_block_size",
                     "maximum_block_size",
                     "minimum_frame_size",
                     "maximum_frame_size",
                     "sample_rate",
                     "channels",
                     "bits_per_sample",
                     "total_samples",
                     "md5sum"]:
            if ((not hasattr(block, attr)) or (getattr(self, attr) !=
                                               getattr(block, attr))):
                return False
        else:
            return True

    def __repr__(self):
        return ("Flac_STREAMINFO(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["minimum_block_size",
                                      "maximum_block_size",
                                      "minimum_frame_size",
                                      "maximum_frame_size",
                                      "sample_rate",
                                      "channels",
                                      "bits_per_sample",
                                      "total_samples",
                                      "md5sum"]]))

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep

        return linesep.decode('ascii').join(
            [u"  STREAMINFO:",
             u"    minimum block size = %d" % (self.minimum_block_size),
             u"    maximum block size = %d" % (self.maximum_block_size),
             u"    minimum frame size = %d" % (self.minimum_frame_size),
             u"    maximum frame size = %d" % (self.maximum_frame_size),
             u"           sample rate = %d" % (self.sample_rate),
             u"              channels = %d" % (self.channels),
             u"       bits-per-sample = %d" % (self.bits_per_sample),
             u"         total samples = %d" % (self.total_samples),
             u"               MD5 sum = %s" %
             (u"".join(["%2.2X" % (ord(b)) for b in self.md5sum]))])

    @classmethod
    def parse(cls, reader):
        """returns this metadata block from a BitstreamReader"""

        values = reader.parse("16u16u24u24u20u3u5u36U16b")
        values[5] += 1  # channels
        values[6] += 1  # bits-per-sample
        return cls(*values)

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        writer.build("16u16u24u24u20u3u5u36U16b",
                     (self.minimum_block_size,
                      self.maximum_block_size,
                      self.minimum_frame_size,
                      self.maximum_frame_size,
                      self.sample_rate,
                      self.channels - 1,
                      self.bits_per_sample - 1,
                      self.total_samples,
                      self.md5sum))

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        return 34


class Flac_PADDING:
    BLOCK_ID = 1

    def __init__(self, length):
        self.length = length

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_PADDING(self.length)

    def __repr__(self):
        return "Flac_PADDING(%d)" % (self.length)

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep

        return linesep.decode('ascii').join(
            [u"  PADDING:",
             u"    length = %d" % (self.length)])

    @classmethod
    def parse(cls, reader, block_length):
        """returns this metadata block from a BitstreamReader"""

        reader.skip_bytes(block_length)
        return cls(length=block_length)

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        writer.write_bytes(chr(0) * self.length)

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        return self.length


class Flac_APPLICATION:
    BLOCK_ID = 2

    def __init__(self, application_id, data):
        self.application_id = application_id
        self.data = data

    def __eq__(self, block):
        for attr in ["application_id", "data"]:
            if ((not hasattr(block, attr)) or (getattr(self, attr) !=
                                               getattr(block, attr))):
                return False
        else:
            return True

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_APPLICATION(self.application_id,
                                self.data)

    def __repr__(self):
        return "Flac_APPLICATION(%s, %s)" % (repr(self.application_id),
                                             repr(self.data))

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep

        return u"  APPLICATION:%s    %s (%d bytes)" % \
            (linesep.decode('ascii'),
             self.application_id.decode('ascii'),
             len(self.data))

    @classmethod
    def parse(cls, reader, block_length):
        """returns this metadata block from a BitstreamReader"""

        return cls(application_id=reader.read_bytes(4),
                   data=reader.read_bytes(block_length - 4))

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        writer.write_bytes(self.application_id)
        writer.write_bytes(self.data)

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        return len(self.application_id) + len(self.data)


class Flac_SEEKTABLE:
    BLOCK_ID = 3

    def __init__(self, seekpoints):
        """seekpoints is a list of
        (PCM frame offset, byte offset, PCM frame count) tuples"""
        self.seekpoints = seekpoints

    def __eq__(self, block):
        if (hasattr(block, "seekpoints")):
            return self.seekpoints == block.seekpoints
        else:
            return False

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_SEEKTABLE(self.seekpoints[:])

    def __repr__(self):
        return "Flac_SEEKTABLE(%s)" % (repr(self.seekpoints))

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep

        return linesep.decode('ascii').join(
            [u"  SEEKTABLE:",
             u"    first sample   file offset   frame samples"] +
            [u"  %14.1d %13.1X %15.d" % seekpoint
             for seekpoint in self.seekpoints])

    @classmethod
    def parse(cls, reader, total_seekpoints):
        """returns this metadata block from a BitstreamReader"""

        return cls([tuple(reader.parse("64U64U16u"))
                    for i in xrange(total_seekpoints)])

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        for seekpoint in self.seekpoints:
            writer.build("64U64U16u", seekpoint)

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        from .bitstream import format_size

        return (format_size("64U64U16u") / 8) * len(self.seekpoints)

    def clean(self, fixes_performed):
        """removes any empty seek points
        and ensures PCM frame offset and byte offset
        are both incrementing"""

        nonempty_points = [seekpoint for seekpoint in self.seekpoints
                           if (seekpoint[2] != 0)]
        if (len(nonempty_points) != len(self.seekpoints)):
            from .text import CLEAN_FLAC_REMOVE_SEEKPOINTS
            fixes_performed.append(CLEAN_FLAC_REMOVE_SEEKPOINTS)

        ascending_order = list(set(nonempty_points))
        ascending_order.sort()

        if (ascending_order != nonempty_points):
            from .text import CLEAN_FLAC_REORDER_SEEKPOINTS
            fixes_performed.append(CLEAN_FLAC_REORDER_SEEKPOINTS)

        return Flac_SEEKTABLE(ascending_order)


class Flac_VORBISCOMMENT(VorbisComment):
    BLOCK_ID = 4

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_VORBISCOMMENT(self.comment_strings[:],
                                  self.vendor_string)

    def __repr__(self):
        return "Flac_VORBISCOMMENT(%s, %s)" % \
            (repr(self.comment_strings), repr(self.vendor_string))

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep
        from . import output_table

        #align the text strings on the "=" sign, if any

        table = output_table()

        for comment in self.comment_strings:
            row = table.row()
            row.add_column(u" " * 4)
            if (u"=" in comment):
                (tag, value) = comment.split(u"=", 1)
                row.add_column(tag, "right")
                row.add_column(u"=")
                row.add_column(value)
            else:
                row.add_column(comment)
                row.add_column(u"")
                row.add_column(u"")

        return (u"  VORBIS_COMMENT:" + linesep.decode('ascii') +
                u"    %s" % (self.vendor_string) + linesep.decode('ascii') +
                linesep.decode('ascii').join(table.format()))

    @classmethod
    def converted(cls, metadata):
        """converts a MetaData object to a Flac_VORBISCOMMENT object"""

        if ((metadata is None) or (isinstance(metadata, Flac_VORBISCOMMENT))):
            return metadata
        else:
            #make VorbisComment do all the work,
            #then lift its data into a new Flac_VORBISCOMMENT
            metadata = VorbisComment.converted(metadata)
            return cls(metadata.comment_strings,
                       metadata.vendor_string)

    @classmethod
    def parse(cls, reader):
        """returns this metadata block from a BitstreamReader"""

        reader.set_endianness(1)
        vendor_string = reader.read_bytes(reader.read(32)).decode('utf-8',
                                                                  'replace')
        return cls([reader.read_bytes(reader.read(32)).decode('utf-8',
                                                              'replace')
                    for i in xrange(reader.read(32))], vendor_string)

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        writer.set_endianness(1)
        vendor_string = self.vendor_string.encode('utf-8')
        writer.build("32u%db" % (len(vendor_string)),
                     (len(vendor_string), vendor_string))
        writer.write(32, len(self.comment_strings))
        for comment_string in self.comment_strings:
            comment_string = comment_string.encode('utf-8')
            writer.build("32u%db" % (len(comment_string)),
                         (len(comment_string), comment_string))
        writer.set_endianness(0)

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        from operator import add

        return (4 + len(self.vendor_string.encode('utf-8')) +
                4 +
                reduce(add, [4 + len(comment.encode('utf-8'))
                             for comment in self.comment_strings], 0))


class Flac_CUESHEET:
    BLOCK_ID = 5

    def __init__(self, catalog_number, lead_in_samples, is_cdda, tracks):
        """catalog_number is a 128 byte ASCII string, padded with NULLs
        lead_in_samples is typically 2 seconds of samples
        is_cdda is 1 if audio if from CDDA, 0 otherwise
        tracks is a list of Flac_CHESHEET_track objects"""

        self.catalog_number = catalog_number
        self.lead_in_samples = lead_in_samples
        self.is_cdda = is_cdda
        self.tracks = tracks

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_CUESHEET(self.catalog_number,
                             self.lead_in_samples,
                             self.is_cdda,
                             [track.copy() for track in self.tracks])

    def __eq__(self, cuesheet):
        for attr in ["catalog_number",
                     "lead_in_samples",
                     "is_cdda",
                     "tracks"]:
            if ((not hasattr(cuesheet, attr)) or (getattr(self, attr) !=
                                                  getattr(cuesheet, attr))):
                return False
        else:
            return True

    def __repr__(self):
        return ("Flac_CUESHEET(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["catalog_number",
                                      "lead_in_samples",
                                      "is_cdda",
                                      "tracks"]]))

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep

        return linesep.decode('ascii').join(
            [u"  CUESHEET:",
             u"     catalog number = %s" %
             (self.catalog_number.decode('ascii', 'replace')),
             u"    lead-in samples = %d" % (self.lead_in_samples),
             u"            is CDDA = %d" % (self.is_cdda)] +
            [track.raw_info(4) for track in self.tracks])

    @classmethod
    def parse(cls, reader):
        """returns this metadata block from a BitstreamReader"""

        (catalog_number,
         lead_in_samples,
         is_cdda,
         track_count) = reader.parse("128b64U1u2071p8u")
        return cls(catalog_number,
                   lead_in_samples,
                   is_cdda,
                   [Flac_CUESHEET_track.parse(reader)
                    for i in xrange(track_count)])

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        writer.build("128b64U1u2071p8u",
                     (self.catalog_number,
                      self.lead_in_samples,
                      self.is_cdda,
                      len(self.tracks)))
        for track in self.tracks:
            track.build(writer)

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        from .bitstream import BitstreamAccumulator

        a = BitstreamAccumulator(0)
        self.build(a)
        return a.bytes()

    @classmethod
    def converted(cls, sheet, total_pcm_frames, sample_rate, is_cdda=True):
        """given a Sheet object, total PCM frames, sample rate and
        optional boolean indicating whether cuesheet is CD audio
        returns a Flac_CUESHEET object from that data"""

        flac_tracks = []

        #add tracks from sheet
        for track in sheet.tracks():
            flac_track_indexes = []
            flac_track_offset = 0
            #add indexes from track
            for (i, index) in enumerate(track.indexes()):
                if (i == 0):
                    #first index
                    flac_track_offset = int(index.offset() * sample_rate)

                flac_track_indexes.append(
                    Flac_CUESHEET_index(int(index.offset() * sample_rate) -
                                        flac_track_offset,
                                        index.number()))

            #pad ISRC value, if present and necessary
            if (track.ISRC() is not None):
                flac_track_isrc = \
                    track.ISRC() + chr(0) * (12 - len(track.ISRC()))
            else:
                flac_track_isrc = chr(0) * 12

            flac_tracks.append(
                Flac_CUESHEET_track(flac_track_offset,
                                    track.number(),
                                    flac_track_isrc,
                                    (0 if track.audio() else 1),
                                    0,
                                    flac_track_indexes))

        #add lead-out track
        flac_tracks.append(
            Flac_CUESHEET_track(total_pcm_frames, 170, chr(0) * 12, 0, 0, []))

        if (sheet.catalog() is None):
            catalog_number = chr(0) * 128
        else:
            catalog_number = \
                sheet.catalog() + (chr(0) * (128 - len(sheet.catalog())))

        #assume CDDA-standard 2 second lead-in
        #and is CD audio if file's specs match CD audio
        return cls(catalog_number,
                   sample_rate * 2,
                   (1 if is_cdda else 0),
                   flac_tracks)


class Flac_CUESHEET_track:
    def __init__(self, offset, number, ISRC, track_type, pre_emphasis,
                 index_points):
        """offset is the track's first index point's offset
        from the start of the stream, in PCM frames
        number is the track number, typically starting from 1
        ISRC is a 12 byte ASCII string, padded with NULLs
        track_type is 0 for audio, 1 for non-audio
        pre_emphasis is 0 for no, 1 for yes
        index_points is a list of Flac_CUESHEET_index objects"""

        self.offset = offset
        self.number = number
        self.ISRC = ISRC
        self.track_type = track_type
        self.pre_emphasis = pre_emphasis
        self.index_points = index_points

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_CUESHEET_track(self.offset,
                                   self.number,
                                   self.ISRC,
                                   self.track_type,
                                   self.pre_emphasis,
                                   [index.copy() for index in
                                    self.index_points])

    def __repr__(self):
        return ("Flac_CUESHEET_track(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["offset",
                                      "number",
                                      "ISRC",
                                      "track_type",
                                      "pre_emphasis",
                                      "index_points"]]))

    def raw_info(self, indent):
        """returns a human-readable version of this track as unicode"""

        from os import linesep

        lines = [((u"track  : %(number)3.d  " +
                  u"offset : %(offset)9.d  " +
                  u"ISRC : %(ISRC)s") %
                 {"number":self.number,
                  "offset":self.offset,
                  "type":self.track_type,
                  "pre_emphasis":self.pre_emphasis,
                  "ISRC":self.ISRC.strip(chr(0)).decode('ascii', 'replace')})
                 ] + [i.raw_info(1) for i in self.index_points]

        return linesep.decode('ascii').join(
            [u" " * indent + line for line in lines])

    def __eq__(self, track):
        for attr in ["offset",
                     "number",
                     "ISRC",
                     "track_type",
                     "pre_emphasis",
                     "index_points"]:
            if ((not hasattr(track, attr)) or (getattr(self, attr) !=
                                               getattr(track, attr))):
                return False
        else:
            return True

    @classmethod
    def parse(cls, reader):
        """returns this cuesheet track from a BitstreamReader"""

        (offset,
         number,
         ISRC,
         track_type,
         pre_emphasis,
         index_points) = reader.parse("64U8u12b1u1u110p8u")
        return cls(offset, number, ISRC, track_type, pre_emphasis,
                   [Flac_CUESHEET_index.parse(reader)
                    for i in xrange(index_points)])

    def build(self, writer):
        """writes this cuesheet track to a BitstreamWriter"""

        writer.build("64U8u12b1u1u110p8u",
                     (self.offset,
                      self.number,
                      self.ISRC,
                      self.track_type,
                      self.pre_emphasis,
                      len(self.index_points)))
        for index_point in self.index_points:
            index_point.build(writer)


class Flac_CUESHEET_index:
    def __init__(self, offset, number):
        """offset is the index's offset from the track offset,
        in PCM frames
        number is the index's number typically starting from 1
        (a number of 0 indicates a track pre-gap)"""

        self.offset = offset
        self.number = number

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_CUESHEET_index(self.offset, self.number)

    def __repr__(self):
        return "Flac_CUESHEET_index(%s, %s)" % (repr(self.offset),
                                                repr(self.number))

    def __eq__(self, index):
        try:
            return ((self.offset == index.offset) and
                    (self.number == index.number))
        except AttributeError:
            return False

    @classmethod
    def parse(cls, reader):
        """returns this cuesheet index from a BitstreamReader"""

        (offset, number) = reader.parse("64U8u24p")

        return cls(offset, number)

    def build(self, writer):
        """writes this cuesheet index to a BitstreamWriter"""

        writer.build("64U8u24p", (self.offset, self.number))

    def raw_info(self, indent):
        return ((u" " * indent) +
                u"index : %3.2d  offset : %9.9s" %
                (self.number, u"+%d" % (self.offset)))


class Flac_PICTURE(Image):
    BLOCK_ID = 6

    def __init__(self, picture_type, mime_type, description,
                 width, height, color_depth, color_count, data):
        self.__dict__["data"] = data
        self.__dict__["mime_type"] = mime_type
        self.__dict__["width"] = width
        self.__dict__["height"] = height
        self.__dict__["color_depth"] = color_depth
        self.__dict__["color_count"] = color_count
        self.__dict__["description"] = description
        self.__dict__["picture_type"] = picture_type

    def copy(self):
        """returns a duplicate of this metadata block"""

        return Flac_PICTURE(self.picture_type,
                            self.mime_type,
                            self.description,
                            self.width,
                            self.height,
                            self.color_depth,
                            self.color_count,
                            self.data)

    def __getattr__(self, key):
        if (key == "type"):
            #convert FLAC picture_type to Image type
            #
            # | Item         | FLAC Picture ID | Image type |
            # |--------------+-----------------+------------|
            # | Other        |               0 |          4 |
            # | Front Cover  |               3 |          0 |
            # | Back Cover   |               4 |          1 |
            # | Leaflet Page |               5 |          2 |
            # | Media        |               6 |          3 |

            return {0: 4, 3: 0, 4: 1, 5: 2, 6: 3}.get(self.picture_type, 4)
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __setattr__(self, key, value):
        if (key == "type"):
            #convert Image type to FLAC picture_type
            #
            # | Item         | Image type | FLAC Picture ID |
            # |--------------+------------+-----------------|
            # | Other        |          4 |               0 |
            # | Front Cover  |          0 |               3 |
            # | Back Cover   |          1 |               4 |
            # | Leaflet Page |          2 |               5 |
            # | Media        |          3 |               6 |

            self.picture_type = {4: 0, 0: 3, 1: 4, 2: 5, 3: 6}.get(value, 0)
        else:
            self.__dict__[key] = value

    def __repr__(self):
        return ("Flac_PICTURE(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["picture_type",
                                      "mime_type",
                                      "description",
                                      "width",
                                      "height",
                                      "color_depth",
                                      "color_count"]]))

    def raw_info(self):
        """returns a human-readable version of this metadata block
        as unicode"""

        from os import linesep

        return linesep.decode('ascii').join(
            [u"  PICTURE:",
             u"    picture type = %d" % (self.picture_type),
             u"       MIME type = %s" % (self.mime_type),
             u"     description = %s" % (self.description),
             u"           width = %d" % (self.width),
             u"          height = %d" % (self.height),
             u"     color depth = %d" % (self.color_depth),
             u"     color count = %d" % (self.color_count),
             u"           bytes = %d" % (len(self.data))])

    @classmethod
    def parse(cls, reader):
        """returns this metadata block from a BitstreamReader"""

        return cls(
            picture_type=reader.read(32),
            mime_type=reader.read_bytes(reader.read(32)).decode('ascii'),
            description=reader.read_bytes(reader.read(32)).decode('utf-8'),
            width=reader.read(32),
            height=reader.read(32),
            color_depth=reader.read(32),
            color_count=reader.read(32),
            data=reader.read_bytes(reader.read(32)))

    def build(self, writer):
        """writes this metadata block to a BitstreamWriter"""

        writer.build("32u 32u%db 32u%db 32u 32u 32u 32u 32u%db" %
                     (len(self.mime_type.encode('ascii')),
                      len(self.description.encode('utf-8')),
                      len(self.data)),
                     (self.picture_type,
                      len(self.mime_type.encode('ascii')),
                      self.mime_type.encode('ascii'),
                      len(self.description.encode('utf-8')),
                      self.description.encode('utf-8'),
                      self.width,
                      self.height,
                      self.color_depth,
                      self.color_count,
                      len(self.data),
                      self.data))

    def size(self):
        """the size of this metadata block
        not including the 4-byte block header"""

        from .bitstream import format_size

        return format_size(
            "32u 32u%db 32u%db 32u 32u 32u 32u 32u%db" %
            (len(self.mime_type.encode('ascii')),
             len(self.description.encode('utf-8')),
             len(self.data))) / 8

    @classmethod
    def converted(cls, image):
        """converts an Image object to a FlacPictureComment"""

        return cls(
            picture_type={4: 0, 0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0),
            mime_type=image.mime_type,
            description=image.description,
            width=image.width,
            height=image.height,
            color_depth=image.color_depth,
            color_count=image.color_count,
            data=image.data)

    def type_string(self):
        """returns the image's type as a human readable plain string

        for example, an image of type 0 returns "Front Cover"
        """

        return {0: "Other",
                1: "File icon",
                2: "Other file icon",
                3: "Cover (front)",
                4: "Cover (back)",
                5: "Leaflet page",
                6: "Media",
                7: "Lead artist / lead performer / soloist",
                8: "Artist / Performer",
                9: "Conductor",
                10: "Band / Orchestra",
                11: "Composer",
                12: "Lyricist / Text writer",
                13: "Recording Location",
                14: "During recording",
                15: "During performance",
                16: "Movie / Video screen capture",
                17: "A bright colored fish",
                18: "Illustration",
                19: "Band/Artist logotype",
                20: "Publisher / Studio logotype"}.get(self.picture_type,
                                                       "Other")

    def clean(self, fixes_performed):
        from .image import image_metrics

        img = image_metrics(self.data)

        if (((self.mime_type != img.mime_type) or
             (self.width != img.width) or
             (self.height != img.height) or
             (self.color_depth != img.bits_per_pixel) or
             (self.color_count != img.color_count))):
            from .text import CLEAN_FIX_IMAGE_FIELDS
            fixes_performed.append(CLEAN_FIX_IMAGE_FIELDS)
            return self.__class__.converted(
                Image(type=self.type,
                      mime_type=img.mime_type,
                      description=self.description,
                      width=img.width,
                      height=img.height,
                      color_depth=img.bits_per_pixel,
                      color_count=img.color_count,
                      data=self.data))
        else:
            return self


class FlacAudio(WaveContainer, AiffContainer):
    """a Free Lossless Audio Codec file"""

    from .text import (COMP_FLAC_0,
                       COMP_FLAC_8)

    SUFFIX = "flac"
    NAME = SUFFIX
    DESCRIPTION = u"Free Lossless Audio Codec"
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str, range(0, 9)))
    COMPRESSION_DESCRIPTIONS = {"0": COMP_FLAC_0,
                                "8": COMP_FLAC_8}

    METADATA_CLASS = FlacMetaData

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_frames__ = 0
        self.__stream_offset__ = 0
        self.__md5__ = chr(0) * 16

        try:
            self.__read_streaminfo__()
        except IOError, msg:
            raise InvalidFLAC(str(msg))

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        from . import ChannelMask

        if (self.channels() <= 2):
            return ChannelMask.from_channels(self.channels())

        try:
            metadata = self.get_metadata()
            if (metadata is not None):
                return ChannelMask(
                    int(metadata.get_block(
                        Flac_VORBISCOMMENT.BLOCK_ID)[
                            u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"][0], 16))
            else:
                #proceed to generate channel mask
                raise ValueError()
        except (IndexError, KeyError, ValueError):
            #if there is no VORBIS_COMMENT block
            #or no WAVEFORMATEXTENSIBLE_CHANNEL_MASK in that block
            #or it's not an integer,
            #use FLAC's default mask based on channels
            if (self.channels() == 3):
                return ChannelMask.from_fields(
                    front_left=True, front_right=True, front_center=True)
            elif (self.channels() == 4):
                return ChannelMask.from_fields(
                    front_left=True, front_right=True,
                    back_left=True, back_right=True)
            elif (self.channels() == 5):
                return ChannelMask.from_fields(
                    front_left=True, front_right=True, front_center=True,
                    back_left=True, back_right=True)
            elif (self.channels() == 6):
                return ChannelMask.from_fields(
                    front_left=True, front_right=True, front_center=True,
                    back_left=True, back_right=True,
                    low_frequency=True)
            else:
                return ChannelMask(0)

    def lossless(self):
        """returns True"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        #FlacAudio *always* returns a FlacMetaData object
        #even if the blocks aren't present
        #so there's no need to test for None

        f = file(self.filename, 'rb')
        try:
            f.seek(self.__stream_offset__, 0)
            if (f.read(4) != 'fLaC'):
                return None
            else:
                from .bitstream import BitstreamReader

                return FlacMetaData.parse(BitstreamReader(f, 0))
        finally:
            f.close()

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        from .bitstream import BitstreamWriter
        from .bitstream import BitstreamAccumulator
        from .bitstream import BitstreamReader
        from operator import add

        if (metadata is None):
            return

        if (not isinstance(metadata, FlacMetaData)):
            from .text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        has_padding = len(metadata.get_blocks(Flac_PADDING.BLOCK_ID)) > 0

        if (has_padding):
            total_padding_size = sum(
                [b.size() for b in metadata.get_blocks(Flac_PADDING.BLOCK_ID)])
        else:
            total_padding_size = 0

        metadata_delta = metadata.size() - self.metadata_length()

        if (has_padding and (metadata_delta <= total_padding_size)):
            #if padding size is larger than change in metadata
            #shrink padding blocks so that new size matches old size
            #(if metadata_delta is negative,
            # this will enlarge padding blocks as necessary)

            for padding in metadata.get_blocks(Flac_PADDING.BLOCK_ID):
                if (metadata_delta > 0):
                    #extract bytes from PADDING blocks
                    #until the metadata_delta is exhausted
                    if (metadata_delta <= padding.length):
                        padding.length -= metadata_delta
                        metadata_delta = 0
                    else:
                        metadata_delta -= padding.length
                        padding.length = 0
                elif (metadata_delta < 0):
                    #dump all our new bytes into the first PADDING block found
                    padding.length -= metadata_delta
                    metadata_delta = 0
                else:
                    break

            #then overwrite the beginning of the file
            stream = file(self.filename, 'r+b')
            stream.write('fLaC')
            metadata.build(BitstreamWriter(stream, 0))
            stream.close()
        else:
            #if padding is smaller than change in metadata,
            #or file has no padding,
            #rewrite entire file to fit new metadata

            from . import TemporaryFile, transfer_data

            #skip existing metadata blocks
            old_file = file(self.filename, "rb")
            old_file.seek(self.__stream_offset__)

            if (old_file.read(4) != 'fLaC'):
                 from .text import ERR_FLAC_INVALID_FILE
                 raise InvalidFLAC(ERR_FLAC_INVALID_FILE)

            stop = 0
            reader = BitstreamReader(old_file, 0)
            while (stop == 0):
                (stop, length) = reader.parse("1u 7p 24u")
                reader.skip_bytes(length)

            #write new metadata to new file
            new_file = TemporaryFile(self.filename)
            new_file.write("fLaC")
            writer = BitstreamWriter(new_file, 0)
            metadata.build(writer)
            writer.flush()

            #write remaining old data to new file
            transfer_data(old_file.read, new_file.write)

            #commit change to disk
            reader.close()
            writer.close()

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to read or write the file"""

        new_metadata = self.METADATA_CLASS.converted(metadata)

        if (new_metadata is None):
            return

        old_metadata = self.get_metadata()
        if (old_metadata is None):
            #this shouldn't happen
            old_metadata = FlacMetaData([])

        #replace old metadata's VORBIS_COMMENT with one from new metadata
        #(if any)
        if (new_metadata.has_block(Flac_VORBISCOMMENT.BLOCK_ID)):
            new_vorbiscomment = new_metadata.get_block(
                Flac_VORBISCOMMENT.BLOCK_ID)

            if (old_metadata.has_block(Flac_VORBISCOMMENT.BLOCK_ID)):
                #both new and old metadata has a VORBIS_COMMENT block

                old_vorbiscomment = old_metadata.get_block(
                    Flac_VORBISCOMMENT.BLOCK_ID)

                #update vendor string from our current VORBIS_COMMENT block
                new_vorbiscomment.vendor_string = \
                    old_vorbiscomment.vendor_string

                #update REPLAYGAIN_* tags from our current VORBIS_COMMENT block
                for key in [u"REPLAYGAIN_TRACK_GAIN",
                            u"REPLAYGAIN_TRACK_PEAK",
                            u"REPLAYGAIN_ALBUM_GAIN",
                            u"REPLAYGAIN_ALBUM_PEAK",
                            u"REPLAYGAIN_REFERENCE_LOUDNESS"]:
                    try:
                        new_vorbiscomment[key] = old_vorbiscomment[key]
                    except KeyError:
                        new_vorbiscomment[key] = []

                #update WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                #from our current VORBIS_COMMENT block, if any
                if (((self.channels() > 2) or
                     (self.bits_per_sample() > 16)) and
                    (u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" in
                     old_vorbiscomment.keys())):
                    new_vorbiscomment[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = \
                        old_vorbiscomment[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"]
                elif (u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" in
                      new_vorbiscomment.keys()):
                    new_vorbiscomment[
                        u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = []

                old_metadata.replace_blocks(Flac_VORBISCOMMENT.BLOCK_ID,
                                            [new_vorbiscomment])
            else:
                #new metadata has VORBIS_COMMENT block,
                #but old metadata does not

                #remove REPLAYGAIN_* tags from new VORBIS_COMMENT block
                for key in [u"REPLAYGAIN_TRACK_GAIN",
                            u"REPLAYGAIN_TRACK_PEAK",
                            u"REPLAYGAIN_ALBUM_GAIN",
                            u"REPLAYGAIN_ALBUM_PEAK",
                            u"REPLAYGAIN_REFERENCE_LOUDNESS"]:
                    new_vorbiscomment[key] = []

                #update WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                #from our actual mask if necessary
                if ((self.channels() > 2) or (self.bits_per_sample() > 16)):
                    new_vorbiscomment[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                        u"0x%.4X" % (self.channel_mask())]

                old_metadata.add_block(new_vorbiscomment)
        else:
            #new metadata has no VORBIS_COMMENT block
            pass

        #replace old metadata's PICTURE blocks with those from new metadata
        old_metadata.replace_blocks(
            Flac_PICTURE.BLOCK_ID,
            new_metadata.get_blocks(Flac_PICTURE.BLOCK_ID))

        #everything else remains as-is

        self.update_metadata(old_metadata)

    def metadata_length(self):
        """returns the length of all FLAC metadata blocks as an integer

        not including the 4 byte "fLaC" file header"""

        from .bitstream import BitstreamReader

        counter = 0
        f = file(self.filename, 'rb')
        try:
            f.seek(self.__stream_offset__, 0)
            reader = BitstreamReader(f, 0)

            if (reader.read_bytes(4) != 'fLaC'):
                from .text import ERR_FLAC_INVALID_FILE
                raise InvalidFLAC(ERR_FLAC_INVALID_FILE)

            stop = 0
            while (stop == 0):
                (stop, block_id, length) = reader.parse("1u 7u 24u")
                counter += 4

                reader.skip_bytes(length)
                counter += length

            return counter
        finally:
            f.close()

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        self.set_metadata(MetaData())

    @classmethod
    def __block_ids__(cls, flacfile):
        """yields a block_id int per metadata block

        raises ValueError if a block_id is invalid
        """

        valid_block_ids = frozenset(range(0, 6 + 1))
        from .bitstream import BitstreamReader
        reader = BitstreamReader(flacfile, 0)
        stop = 0
        while (stop == 0):
            (stop, block_id, length) = reader.parse("1u 7u 24u")
            if (block_id in valid_block_ids):
                yield block_id
            else:
                from .text import ERR_FLAC_INVALID_BLOCK
                raise ValueError(ERR_FLAC_INVALID_BLOCK)
            reader.skip_bytes(length)

    def set_cuesheet(self, cuesheet):
        """imports cuesheet data from a Sheet object

        Raises IOError if an error occurs setting the cuesheet"""

        if (cuesheet is not None):
            metadata = self.get_metadata()
            if (metadata is not None):
                metadata.add_block(
                    Flac_CUESHEET.converted(
                        cuesheet,
                        self.total_frames(),
                        self.sample_rate(),
                        (self.sample_rate() == 44100) and
                        (self.channels() == 2) and
                        (self.bits_per_sample() == 16)))
                self.update_metadata(metadata)

    def get_cuesheet(self):
        """returns the embedded Sheet object, or None

        Raises IOError if a problem occurs when reading the file"""

        def convert_track(track):
            """converts Flac_CUESHEET_track object to SheetTrack object"""

            from audiotools import SheetTrack

            return SheetTrack(
                track.number,
                [convert_index(track, i) for i in track.index_points],
                track.track_type == 0,
                (track.ISRC if
                 ((track.number != 170) and
                  (len(track.ISRC.strip(chr(0))) > 0)) else None))

        def convert_index(track, index):
            from fractions import Fraction
            from audiotools import SheetIndex

            return SheetIndex(
                index.number,
                Fraction(track.offset + index.offset, self.sample_rate()))

        metadata = self.get_metadata()
        if (metadata is not None):
            #get CUESHEET block from metadata, if any
            try:
                cuesheet = metadata.get_block(Flac_CUESHEET.BLOCK_ID)
            except IndexError:
                return None

            #convert CUESHEET block to Sheet object
            from audiotools import Sheet

            return Sheet([convert_track(t) for t in cuesheet.tracks if
                          t.number != 170],
                         (cuesheet.catalog_number.rstrip(chr(0)) if
                          len(cuesheet.catalog_number.rstrip(chr(0))) else
                          None))
        else:
            return None

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from . import decoders
        from . import PCMReaderError

        try:
            return decoders.FlacDecoder(self.filename,
                                        self.channel_mask(),
                                        self.__stream_offset__)
        except (IOError, ValueError), msg:
            #The only time this is likely to occur is
            #if the FLAC is modified between when FlacAudio
            #is initialized and when to_pcm() is called.
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None,
                 total_pcm_frames=None,
                 encoding_function=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new FlacAudio object"""

        from .encoders import encode_flac
        from . import EncodingError
        from . import UnsupportedChannelCount
        from . import BufferedPCMReader
        from . import __default_quality__

        if ((compression is None) or (compression not in
                                      cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        encoding_options = {
            "0": {"block_size": 1152,
                  "max_lpc_order": 0,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 3},
            "1": {"block_size": 1152,
                  "max_lpc_order": 0,
                  "adaptive_mid_side": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 3},
            "2": {"block_size": 1152,
                  "max_lpc_order": 0,
                  "exhaustive_model_search": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 3},
            "3": {"block_size": 4096,
                  "max_lpc_order": 6,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 4},
            "4": {"block_size": 4096,
                  "max_lpc_order": 8,
                  "adaptive_mid_side": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 4},
            "5": {"block_size": 4096,
                  "max_lpc_order": 8,
                  "mid_side": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 5},
            "6": {"block_size": 4096,
                  "max_lpc_order": 8,
                  "mid_side": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 6},
            "7": {"block_size": 4096,
                  "max_lpc_order": 8,
                  "mid_side": True,
                  "exhaustive_model_search": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 6},
            "8": {"block_size": 4096,
                  "max_lpc_order": 12,
                  "mid_side": True,
                  "exhaustive_model_search": True,
                  "min_residual_partition_order": 0,
                  "max_residual_partition_order": 6}}[compression]

        if (pcmreader.channels > 8):
            raise UnsupportedChannelCount(filename, pcmreader.channels)

        if (int(pcmreader.channel_mask) == 0):
            if (pcmreader.channels <= 6):
                channel_mask = {1: 0x0004,
                                2: 0x0003,
                                3: 0x0007,
                                4: 0x0033,
                                5: 0x0037,
                                6: 0x003F}[pcmreader.channels]
            else:
                channel_mask = 0

        elif (int(pcmreader.channel_mask) not in
              (0x0001,    # 1ch - mono
               0x0004,    # 1ch - mono
               0x0003,    # 2ch - left, right
               0x0007,    # 3ch - left, right, center
               0x0033,    # 4ch - left, right, back left, back right
               0x0603,    # 4ch - left, right, side left, side right
               0x0037,    # 5ch - L, R, C, back left, back right
               0x0607,    # 5ch - L, R, C, side left, side right
               0x003F,    # 6ch - L, R, C, LFE, back left, back right
               0x060F)):  # 6ch - L, R, C, LFE, side left, side right
            from . import UnsupportedChannelMask

            raise UnsupportedChannelMask(filename,
                                         int(pcmreader.channel_mask))
        else:
            channel_mask = int(pcmreader.channel_mask)

        if (total_pcm_frames is not None):
            expected_seekpoints = \
                ((total_pcm_frames // (pcmreader.sample_rate * 10)) +
                 (1 if (total_pcm_frames % (pcmreader.sample_rate * 10)) else
                  0))
            padding_size = 4096 + 4 + (expected_seekpoints * 18)
        else:
            padding_size = 4096

        try:
            offsets = (encode_flac if encoding_function is None
                       else encoding_function)(filename,
                                               pcmreader=
                                               BufferedPCMReader(pcmreader),
                                               padding_size=
                                               padding_size,
                                               **encoding_options)
            flac = FlacAudio(filename)
            metadata = flac.get_metadata()
            assert(metadata is not None)

            #generate SEEKTABLE from encoder offsets and add it to metadata
            seekpoint_interval = pcmreader.sample_rate * 10

            metadata.add_block(
                flac.seektable(
                    [(byte_offset,
                      pcm_frames) for byte_offset, pcm_frames in offsets],
                    seekpoint_interval))

            #if channels or bps is too high,
            #automatically generate and add channel mask
            if ((((pcmreader.channels > 2) or
                  (pcmreader.bits_per_sample > 16)) and
                 (channel_mask != 0))):
                vorbis = metadata.get_block(Flac_VORBISCOMMENT.BLOCK_ID)
                vorbis[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4X" % (channel_mask)]

            flac.update_metadata(metadata)

            return flac
        except (IOError, ValueError), err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            cls.__unlink__(filename)
            raise err

    def seektable(self, offsets=None, seekpoint_interval=None):
        """returns a new Flac_SEEKTABLE object
        created from parsing the FLAC file itself"""

        from bisect import bisect_right

        if (offsets is None):
            metadata_length = (self.__stream_offset__ +
                               4 + self.metadata_length())
            offsets = [(byte_offset - metadata_length,
                        pcm_frames) for byte_offset, pcm_frames in
                       self.to_pcm().offsets()]

        if (seekpoint_interval is None):
            seekpoint_interval = self.sample_rate() * 10

        total_samples = 0
        all_frames = {}
        sample_offsets = []
        for (byte_offset, pcm_frames) in offsets:
            all_frames[total_samples] = (byte_offset, pcm_frames)
            sample_offsets.append(total_samples)
            total_samples += pcm_frames

        seekpoints = []
        for pcm_frame in xrange(0,
                                self.total_frames(),
                                seekpoint_interval):
            flac_frame = bisect_right(sample_offsets, pcm_frame) - 1
            seekpoints.append((sample_offsets[flac_frame],
                               all_frames[sample_offsets[flac_frame]][0],
                               all_frames[sample_offsets[flac_frame]][1]))

        return Flac_SEEKTABLE(seekpoints)

    def has_foreign_wave_chunks(self):
        """returns True if the audio file contains non-audio RIFF chunks

        during transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks"""

        try:
            metadata = self.get_metadata()
            if (metadata is not None):
                return 'riff' in [
                    block.application_id for block in
                    metadata.get_blocks(Flac_APPLICATION.BLOCK_ID)]
            else:
                return False
        except IOError:
            return False

    def wave_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        may raise ValueError if there's a problem with
        the header or footer data
        may raise IOError if there's a problem reading
        header or footer data from the file
        """

        from .wav import pad_data

        header = []
        if (pad_data(self.total_frames(),
                     self.channels(),
                     self.bits_per_sample())):
            footer = [chr(0)]
        else:
            footer = []
        current_block = header

        metadata = self.get_metadata()
        if (metadata is None):
            raise ValueError("no foreign RIFF chunks")

        #convert individual chunks into combined header and footer strings
        for block in metadata.get_blocks(Flac_APPLICATION.BLOCK_ID):
            if (block.application_id == "riff"):
                chunk_id = block.data[0:4]
                #combine APPLICATION metadata blocks up to "data" as header
                if (chunk_id != "data"):
                    current_block.append(block.data)
                else:
                    #combine APPLICATION metadata blocks past "data" as footer
                    current_block.append(block.data)
                    current_block = footer

        #return tuple of header and footer
        if ((len(header) != 0) or (len(footer) != 0)):
            return ("".join(header), "".join(footer))
        else:
            raise ValueError("no foreign RIFF chunks")

    @classmethod
    def from_wave(cls, filename, header, pcmreader, footer, compression=None):
        """encodes a new file from wave data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        from .bitstream import BitstreamReader
        from .bitstream import BitstreamRecorder
        from .bitstream import format_byte_size
        import cStringIO
        from .wav import (pad_data, WaveAudio)
        from . import (EncodingError, CounterPCMReader)

        #split header and footer into distinct chunks
        header_len = len(header)
        footer_len = len(footer)
        fmt_found = False
        blocks = []
        try:
            #read everything from start of header to "data<size>"
            #chunk header
            r = BitstreamReader(cStringIO.StringIO(header), 1)
            (riff, remaining_size, wave) = r.parse("4b 32u 4b")
            if (riff != "RIFF"):
                from .text import ERR_WAV_NOT_WAVE
                raise EncodingError(ERR_WAV_NOT_WAVE)
            elif (wave != "WAVE"):
                from .text import ERR_WAV_INVALID_WAVE
                raise EncodingError(ERR_WAV_INVALID_WAVE)
            else:
                block_data = BitstreamRecorder(1)
                block_data.build("4b 32u 4b", (riff, remaining_size, wave))
                blocks.append(Flac_APPLICATION("riff", block_data.data()))
                total_size = remaining_size + 8
                header_len -= format_byte_size("4b 32u 4b")

            while (header_len):
                block_data = BitstreamRecorder(1)
                (chunk_id, chunk_size) = r.parse("4b 32u")
                #ensure chunk ID is valid
                if (not frozenset(chunk_id).issubset(
                        WaveAudio.PRINTABLE_ASCII)):
                    from .text import ERR_WAV_INVALID_CHUNK
                    raise EncodingError(ERR_WAV_INVALID_CHUNK)
                else:
                    header_len -= format_byte_size("4b 32u")
                    block_data.build("4b 32u", (chunk_id, chunk_size))

                if (chunk_id == "data"):
                    #transfer only "data" chunk header to APPLICATION block
                    if (header_len != 0):
                        from .text import ERR_WAV_HEADER_EXTRA_DATA
                        raise EncodingError(ERR_WAV_HEADER_EXTRA_DATA %
                                            (header_len))
                    elif (not fmt_found):
                        from .text import ERR_WAV_NO_FMT_CHUNK
                        raise EncodingError(ERR_WAV_NO_FMT_CHUNK)
                    else:
                        blocks.append(
                            Flac_APPLICATION("riff", block_data.data()))
                        data_chunk_size = chunk_size
                        break
                elif (chunk_id == "fmt "):
                    if (not fmt_found):
                        fmt_found = True
                        if (chunk_size % 2):
                            #transfer padded chunk to APPLICATION block
                            block_data.write_bytes(
                                r.read_bytes(chunk_size + 1))
                            header_len -= (chunk_size + 1)
                        else:
                            #transfer un-padded chunk to APPLICATION block
                            block_data.write_bytes(
                                r.read_bytes(chunk_size))
                            header_len -= chunk_size

                        blocks.append(
                            Flac_APPLICATION("riff", block_data.data()))
                    else:
                        from .text import ERR_WAV_MULTIPLE_FMT
                        raise EncodingError(ERR_WAV_MULTIPLE_FMT)
                else:
                    if (chunk_size % 2):
                        #transfer padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size + 1))
                        header_len -= (chunk_size + 1)
                    else:
                        #transfer un-padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size))
                        header_len -= chunk_size

                    blocks.append(Flac_APPLICATION("riff", block_data.data()))
            else:
                from .text import ERR_WAV_NO_DATA_CHUNK
                raise EncodingError(ERR_WAV_NO_DATA_CHUNK)
        except IOError:
            from .text import ERR_WAV_HEADER_IOERROR
            raise EncodingError(ERR_WAV_HEADER_IOERROR)

        try:
            #read everything from start of footer to end of footer
            r = BitstreamReader(cStringIO.StringIO(footer), 1)
            #skip initial footer pad byte
            if (data_chunk_size % 2):
                r.skip_bytes(1)
                footer_len -= 1

            while (footer_len):
                block_data = BitstreamRecorder(1)
                (chunk_id, chunk_size) = r.parse("4b 32u")

                if (not frozenset(chunk_id).issubset(
                        WaveAudio.PRINTABLE_ASCII)):
                    #ensure chunk ID is valid
                    from .text import ERR_WAV_INVALID_CHUNK
                    raise EncodingError(ERR_WAV_INVALID_CHUNK)
                elif (chunk_id == "fmt "):
                    #multiple "fmt " chunks is an error
                    from .text import ERR_WAV_MULTIPLE_FMT
                    raise EncodingError(ERR_WAV_MULTIPLE_FMT)
                elif (chunk_id == "data"):
                    #multiple "data" chunks is an error
                    from .text import ERR_WAV_MULTIPLE_DATA
                    raise EncodingError(ERR_WAV_MULTIPLE_DATA)
                else:
                    footer_len -= format_byte_size("4b 32u")
                    block_data.build("4b 32u", (chunk_id, chunk_size))

                    if (chunk_size % 2):
                        #transfer padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size + 1))
                        footer_len -= (chunk_size + 1)
                    else:
                        #transfer un-padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size))
                        footer_len -= chunk_size

                    blocks.append(Flac_APPLICATION("riff", block_data.data()))
        except IOError:
            from .text import ERR_WAV_FOOTER_IOERROR
            raise EncodingError(ERR_WAV_FOOTER_IOERROR)

        counter = CounterPCMReader(pcmreader)

        #perform standard FLAC encode from PCMReader
        flac = cls.from_pcm(filename, counter, compression)

        data_bytes_written = counter.bytes_written()

        #ensure processed PCM data equals size of "data" chunk
        if (data_bytes_written != data_chunk_size):
            cls.__unlink__(filename)
            from .text import ERR_WAV_TRUNCATED_DATA_CHUNK
            raise EncodingError(ERR_WAV_TRUNCATED_DATA_CHUNK)

        #ensure total size of header + PCM + footer matches wav's header
        if ((len(header) + data_bytes_written + len(footer)) != total_size):
            cls.__unlink__(filename)
            from .text import ERR_WAV_INVALID_SIZE
            raise EncodingError(ERR_WAV_INVALID_SIZE)

        #add chunks as APPLICATION metadata blocks
        metadata = flac.get_metadata()
        if (metadata is not None):
            for block in blocks:
                metadata.add_block(block)
            flac.update_metadata(metadata)

        #return encoded FLAC file
        return flac

    def has_foreign_aiff_chunks(self):
        """returns True if the audio file contains non-audio AIFF chunks"""

        try:
            metadata = self.get_metadata()
            if (metadata is not None):
                return 'aiff' in [
                    block.application_id for block in
                    metadata.get_blocks(Flac_APPLICATION.BLOCK_ID)]
            else:
                return False
        except IOError:
            return False

    def aiff_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        if self.has_foreign_aiff_chunks() is False,
        may raise ValueError if the file has no header and footer
        for any reason"""

        from .aiff import pad_data

        header = []
        if (pad_data(self.total_frames(),
                     self.channels(),
                     self.bits_per_sample())):
            footer = [chr(0)]
        else:
            footer = []
        current_block = header

        metadata = self.get_metadata()
        if (metadata is None):
            raise ValueError("no foreign AIFF chunks")

        #convert individual chunks into combined header and footer strings
        for block in metadata.get_blocks(Flac_APPLICATION.BLOCK_ID):
            if (block.application_id == "aiff"):
                chunk_id = block.data[0:4]
                #combine APPLICATION metadata blocks up to "SSND" as header
                if (chunk_id != "SSND"):
                    current_block.append(block.data)
                else:
                    #combine APPLICATION metadata blocks past "SSND" as footer
                    current_block.append(block.data)
                    current_block = footer

        #return tuple of header and footer
        if ((len(header) != 0) or (len(footer) != 0)):
            return ("".join(header), "".join(footer))
        else:
            raise ValueError("no foreign AIFF chunks")

    @classmethod
    def from_aiff(cls, filename, header, pcmreader, footer, compression=None):
        """encodes a new file from AIFF data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AiffAudio object

        header + pcm data + footer should always result
        in the original AIFF file being restored
        without need for any padding bytes

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        from .bitstream import BitstreamReader
        from .bitstream import BitstreamRecorder
        from .bitstream import format_byte_size
        import cStringIO
        from .aiff import (pad_data, AiffAudio)
        from . import (EncodingError, CounterPCMReader)

        #split header and footer into distinct chunks
        header_len = len(header)
        footer_len = len(footer)
        comm_found = False
        blocks = []
        try:
            #read everything from start of header to "SSND<size>"
            #chunk header
            r = BitstreamReader(cStringIO.StringIO(header), 0)
            (form, remaining_size, aiff) = r.parse("4b 32u 4b")
            if (form != "FORM"):
                from .text import ERR_AIFF_NOT_AIFF
                raise EncodingError(ERR_AIFF_NOT_AIFF)
            elif (aiff != "AIFF"):
                from .text import ERR_AIFF_INVALID_AIFF
                raise EncodingError(ERR_AIFF_INVALID_AIFF)
            else:
                block_data = BitstreamRecorder(0)
                block_data.build("4b 32u 4b", (form, remaining_size, aiff))
                blocks.append(Flac_APPLICATION("aiff", block_data.data()))
                total_size = remaining_size + 8
                header_len -= format_byte_size("4b 32u 4b")

            while (header_len):
                block_data = BitstreamRecorder(0)
                (chunk_id, chunk_size) = r.parse("4b 32u")
                #ensure chunk ID is valid
                if (not frozenset(chunk_id).issubset(
                        AiffAudio.PRINTABLE_ASCII)):
                    from .text import ERR_AIFF_INVALID_CHUNK
                    raise EncodingError(ERR_AIFF_INVALID_CHUNK)
                else:
                    header_len -= format_byte_size("4b 32u")
                    block_data.build("4b 32u", (chunk_id, chunk_size))

                if (chunk_id == "SSND"):
                    #transfer only "SSND" chunk header to APPLICATION block
                    #(including 8 bytes after ID/size header)
                    if (header_len > 8):
                        from .text import ERR_AIFF_HEADER_EXTRA_SSND
                        raise EncodingError(ERR_AIFF_HEADER_EXTRA_SSND)
                    elif (header_len < 8):
                        from .text import ERR_AIFF_HEADER_MISSING_SSND
                        raise EncodingError(ERR_AIFF_HEADER_MISSING_SSND)
                    elif (not comm_found):
                        from .text import ERR_AIFF_NO_COMM_CHUNK
                        raise EncodingError(ERR_AIFF_NO_COMM_CHUNK)
                    else:
                        block_data.write_bytes(r.read_bytes(8))
                        blocks.append(
                            Flac_APPLICATION("aiff", block_data.data()))
                        ssnd_chunk_size = (chunk_size - 8)
                        break
                elif (chunk_id == "COMM"):
                    if (not comm_found):
                        comm_found = True
                        if (chunk_size % 2):
                            #transfer padded chunk to APPLICATION block
                            block_data.write_bytes(
                                r.read_bytes(chunk_size + 1))
                            header_len -= (chunk_size + 1)
                        else:
                            #transfer un-padded chunk to APPLICATION block
                            block_data.write_bytes(
                                r.read_bytes(chunk_size))
                            header_len -= chunk_size
                        blocks.append(
                            Flac_APPLICATION("aiff", block_data.data()))
                    else:
                        from .text import ERR_AIFF_MULTIPLE_COMM_CHUNKS
                        raise EncodingError(ERR_AIFF_MULTIPLE_COMM_CHUNKS)
                else:
                    if (chunk_size % 2):
                        #transfer padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size + 1))
                        header_len -= (chunk_size + 1)
                    else:
                        #transfer un-padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size))
                        header_len -= chunk_size

                    blocks.append(Flac_APPLICATION("aiff", block_data.data()))
            else:
                from .text import ERR_AIFF_NO_SSND_CHUNK
                raise EncodingError(ERR_AIFF_NO_SSND_CHUNK)
        except IOError:
            from .text import ERR_AIFF_HEADER_IOERROR
            raise EncodingError(ERR_AIFF_HEADER_IOERROR)

        try:
            #read everything from start of footer to end of footer
            r = BitstreamReader(cStringIO.StringIO(footer), 0)
            #skip initial footer pad byte
            if (ssnd_chunk_size % 2):
                r.skip_bytes(1)
                footer_len -= 1

            while (footer_len):
                block_data = BitstreamRecorder(0)
                (chunk_id, chunk_size) = r.parse("4b 32u")

                if (not frozenset(chunk_id).issubset(
                        AiffAudio.PRINTABLE_ASCII)):
                    #ensure chunk ID is valid
                    from .text import ERR_AIFF_INVALID_CHUNK
                    raise EncodingError(ERR_AIFF_INVALID_CHUNK)
                elif (chunk_id == "COMM"):
                    #multiple "COMM" chunks is an error
                    from .text import ERR_AIFF_MULTIPLE_COMM_CHUNKS
                    raise EncodingError(ERR_AIFF_MULTIPLE_COMM_CHUNKS)
                elif (chunk_id == "SSND"):
                    #multiple "SSND" chunks is an error
                    from .text import ERR_AIFF_MULTIPLE_SSND_CHUNKS
                    raise EncodingError(ERR_AIFF_MULTIPLE_SSND_CHUNKS)
                else:
                    footer_len -= format_byte_size("4b 32u")
                    block_data.build("4b 32u", (chunk_id, chunk_size))

                    if (chunk_size % 2):
                        #transfer padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size + 1))
                        footer_len -= (chunk_size + 1)
                    else:
                        #transfer un-padded chunk to APPLICATION block
                        block_data.write_bytes(r.read_bytes(chunk_size))
                        footer_len -= chunk_size

                    blocks.append(Flac_APPLICATION("aiff", block_data.data()))
        except IOError:
            from .text import ERR_AIFF_FOOTER_IOERROR
            raise EncodingError(ERR_AIFF_FOOTER_IOERROR)

        counter = CounterPCMReader(pcmreader)

        #perform standard FLAC encode from PCMReader
        flac = cls.from_pcm(filename, counter, compression)

        ssnd_bytes_written = counter.bytes_written()

        #ensure processed PCM data equals size of "SSND" chunk
        if (ssnd_bytes_written != ssnd_chunk_size):
            cls.__unlink__(filename)
            from .text import ERR_AIFF_TRUNCATED_SSND_CHUNK
            raise EncodingError(ERR_AIFF_TRUNCATED_SSND_CHUNK)

        #ensure total size of header + PCM + footer matches aiff's header
        if ((len(header) + ssnd_bytes_written + len(footer)) != total_size):
            cls.__unlink__(filename)
            from .text import ERR_AIFF_INVALID_SIZE
            raise EncodingError(ERR_AIFF_INVALID_SIZE)

        #add chunks as APPLICATION metadata blocks
        metadata = flac.get_metadata()
        if (metadata is not None):
            for block in blocks:
                metadata.add_block(block)
            flac.update_metadata(metadata)

        #return encoded FLAC file
        return flac

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """encodes a new AudioFile from existing AudioFile

        take a filename string, target class and optional compression string
        encodes a new AudioFile in the target class and returns
        the resulting object
        may raise EncodingError if some problem occurs during encoding"""

        #If a FLAC has embedded RIFF *and* embedded AIFF chunks,
        #RIFF takes precedence if the target format supports both.
        #(it's hard to envision a scenario in which that would happen)

        from . import WaveAudio
        from . import AiffAudio
        from . import to_pcm_progress

        if ((self.has_foreign_wave_chunks() and
             hasattr(target_class, "from_wave") and
             callable(target_class.from_wave))):
            return WaveContainer.convert(self,
                                         target_path,
                                         target_class,
                                         compression,
                                         progress)
        elif (self.has_foreign_aiff_chunks() and
              hasattr(target_class, "from_aiff") and
              callable(target_class.from_aiff)):
            return AiffContainer.convert(self,
                                         target_path,
                                         target_class,
                                         compression,
                                         progress)
        else:
            return target_class.from_pcm(
                target_path,
                to_pcm_progress(self, progress),
                compression,
                total_pcm_frames=self.total_frames())

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bitspersample__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__total_frames__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__samplerate__

    def __read_streaminfo__(self):
        valid_header_types = frozenset(range(0, 6 + 1))
        f = file(self.filename, "rb")
        try:
            self.__stream_offset__ = skip_id3v2_comment(f)
            f.read(4)

            from .bitstream import BitstreamReader

            reader = BitstreamReader(f, 0)

            stop = 0

            while (stop == 0):
                (stop, header_type, length) = reader.parse("1u 7u 24u")
                if (header_type not in valid_header_types):
                    from .text import ERR_FLAC_INVALID_BLOCK
                    raise InvalidFLAC(ERR_FLAC_INVALID_BLOCK)
                elif (header_type == 0):
                    (self.__samplerate__,
                     self.__channels__,
                     self.__bitspersample__,
                     self.__total_frames__,
                     self.__md5__) = reader.parse("80p 20u 3u 5u 36U 16b")
                    self.__channels__ += 1
                    self.__bitspersample__ += 1
                    break
                else:
                    #though the STREAMINFO should always be first,
                    #we'll be permissive and check them all if necessary
                    reader.skip_bytes(length)
        finally:
            f.close()

    @classmethod
    def can_add_replay_gain(cls, audiofiles):
        """given a list of audiofiles,
        returns True if this class can add ReplayGain to those files
        returns False if not"""

        for audiofile in audiofiles:
            if (not isinstance(audiofile, FlacAudio)):
                return False
        else:
            return True

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """adds ReplayGain values to a list of filename strings

        all the filenames must be of this AudioFile type
        raises ValueError if some problem occurs during ReplayGain application
        """

        from . import open_files
        from . import calculate_replay_gain

        tracks = [track for track in open_files(filenames) if
                  isinstance(track, cls)]

        if (len(tracks) > 0):
            for (track,
                 track_gain,
                 track_peak,
                 album_gain,
                 album_peak) in calculate_replay_gain(tracks, progress):
                try:
                    metadata = track.get_metadata()
                    if (metadata is None):
                        return
                except IOError:
                    return
                try:
                    comment = metadata.get_block(
                        Flac_VORBISCOMMENT.BLOCK_ID)
                except IndexError:
                    from . import VERSION

                    comment = Flac_VORBISCOMMENT(
                        [], u"Python Audio Tools %s" % (VERSION))
                    metadata.add_block(comment)

                comment["REPLAYGAIN_TRACK_GAIN"] = [
                    "%1.2f dB" % (track_gain)]
                comment["REPLAYGAIN_TRACK_PEAK"] = [
                    "%1.8f" % (track_peak)]
                comment["REPLAYGAIN_ALBUM_GAIN"] = [
                    "%1.2f dB" % (album_gain)]
                comment["REPLAYGAIN_ALBUM_PEAK"] = ["%1.8f" % (album_peak)]
                comment["REPLAYGAIN_REFERENCE_LOUDNESS"] = [u"89.0 dB"]
                track.update_metadata(metadata)

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return True

    @classmethod
    def lossless_replay_gain(cls):
        """returns True"""

        return True

    def replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values"""

        from . import ReplayGain

        try:
            metadata = self.get_metadata()
            if (metadata is not None):
                vorbis_metadata = metadata.get_block(
                    Flac_VORBISCOMMENT.BLOCK_ID)
            else:
                return None
        except (IndexError, IOError):
            return None

        if (set(['REPLAYGAIN_TRACK_PEAK', 'REPLAYGAIN_TRACK_GAIN',
                 'REPLAYGAIN_ALBUM_PEAK', 'REPLAYGAIN_ALBUM_GAIN']).issubset(
                [key.upper() for key in vorbis_metadata.keys()])):
            # we have ReplayGain data
            try:
                return ReplayGain(
                    vorbis_metadata['REPLAYGAIN_TRACK_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_TRACK_PEAK'][0],
                    vorbis_metadata['REPLAYGAIN_ALBUM_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_ALBUM_PEAK'][0])
            except ValueError:
                return None
        else:
            return None

    def __eq__(self, audiofile):
        if (isinstance(audiofile, FlacAudio)):
            return self.__md5__ == audiofile.__md5__
        elif (isinstance(audiofile, AudioFile)):
            from . import FRAMELIST_SIZE

            try:
                from hashlib import md5
            except ImportError:
                from md5 import new as md5

            p = audiofile.to_pcm()
            m = md5()
            s = p.read(FRAMELIST_SIZE)
            while (len(s) > 0):
                m.update(s.to_bytes(False, True))
                s = p.read(FRAMELIST_SIZE)
            p.close()
            return m.digest() == self.__md5__
        else:
            return False

    def clean(self, fixes_performed, output_filename=None):
        """cleans the file of known data and metadata problems

        fixes_performed is a list-like object which is appended
        with Unicode strings of fixed problems

        output_filename is an optional filename of the fixed file
        if present, a new AudioFile is returned
        otherwise, only a dry-run is performed and no new file is written

        raises IOError if unable to write the file or its metadata
        """

        import os.path

        def seektable_valid(seektable, metadata_offset, input_file):
            from .bitstream import BitstreamReader
            reader = BitstreamReader(input_file, 0)

            for (pcm_frame_offset,
                 seekpoint_offset,
                 pcm_frame_count) in seektable.seekpoints:
                input_file.seek(seekpoint_offset + metadata_offset)
                try:
                    (sync_code,
                     reserved1,
                     reserved2) = reader.parse(
                         "14u 1u 1p 4p 4p 4p 3p 1u")
                    if (((sync_code != 0x3FFE) or
                         (reserved1 != 0) or
                         (reserved2 != 0))):
                        return False
                except IOError:
                    return False
            else:
                return True

        if (output_filename is None):
            #dry run only

            input_f = open(self.filename, "rb")
            try:
                #remove ID3 tags from before and after FLAC stream
                stream_offset = skip_id3v2_comment(input_f)
                if (stream_offset > 0):
                    from .text import CLEAN_FLAC_REMOVE_ID3V2
                    fixes_performed.append(CLEAN_FLAC_REMOVE_ID3V2)
                try:
                    input_f.seek(-128, 2)
                    if (input_f.read(3) == 'TAG'):
                        from .text import CLEAN_FLAC_REMOVE_ID3V1
                        fixes_performed.append(CLEAN_FLAC_REMOVE_ID3V1)
                except IOError:
                    #file isn't 128 bytes long
                    pass

                #fix empty MD5SUM
                if (self.__md5__ == chr(0) * 16):
                    from .text import CLEAN_FLAC_POPULATE_MD5
                    fixes_performed.append(CLEAN_FLAC_POPULATE_MD5)

                metadata = self.get_metadata()
                if (metadata is None):
                    return

                #fix missing WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                if ((self.channels() > 2) or (self.bits_per_sample() > 16)):
                    from .text import CLEAN_FLAC_ADD_CHANNELMASK
                    try:
                        if (u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" not in
                            metadata.get_block(
                                Flac_VORBISCOMMENT.BLOCK_ID).keys()):
                            fixes_performed.append(CLEAN_FLAC_ADD_CHANNELMASK)
                    except IndexError:
                        fixes_performed.append(CLEAN_FLAC_ADD_CHANNELMASK)

                #fix an invalid SEEKTABLE, if present
                try:
                    if (not seektable_valid(
                            metadata.get_block(Flac_SEEKTABLE.BLOCK_ID),
                            stream_offset + 4 + self.metadata_length(),
                            input_f)):
                        from .text import CLEAN_FLAC_FIX_SEEKTABLE
                        fixes_performed.append(CLEAN_FLAC_FIX_SEEKTABLE)
                except IndexError:
                    pass

                #fix any remaining metadata problems
                metadata.clean(fixes_performed)

            finally:
                input_f.close()
        else:
            #perform complete fix

            input_f = open(self.filename, "rb")
            try:
                #remove ID3 tags from before and after FLAC stream
                stream_size = os.path.getsize(self.filename)

                stream_offset = skip_id3v2_comment(input_f)
                if (stream_offset > 0):
                    from .text import CLEAN_FLAC_REMOVE_ID3V2
                    fixes_performed.append(CLEAN_FLAC_REMOVE_ID3V2)
                    stream_size -= stream_offset

                try:
                    input_f.seek(-128, 2)
                    if (input_f.read(3) == 'TAG'):
                        from .text import CLEAN_FLAC_REMOVE_ID3V1
                        fixes_performed.append(CLEAN_FLAC_REMOVE_ID3V1)
                        stream_size -= 128
                except IOError:
                    #file isn't 128 bytes long
                    pass

                output_f = open(output_filename, "wb")
                try:
                    input_f.seek(stream_offset, 0)
                    while (stream_size > 0):
                        s = input_f.read(4096)
                        if (len(s) > stream_size):
                            s = s[0:stream_size]
                        output_f.write(s)
                        stream_size -= len(s)
                finally:
                    output_f.close()

                output_track = self.__class__(output_filename)

                metadata = self.get_metadata()
                if (metadata is not None):
                    #fix empty MD5SUM
                    if (self.__md5__ == chr(0) * 16):
                        from hashlib import md5
                        from . import transfer_framelist_data

                        md5sum = md5()
                        transfer_framelist_data(
                            self.to_pcm(),
                            md5sum.update,
                            signed=True,
                            big_endian=False)
                        metadata.get_block(
                            Flac_STREAMINFO.BLOCK_ID).md5sum = md5sum.digest()
                        from .text import CLEAN_FLAC_POPULATE_MD5
                        fixes_performed.append(CLEAN_FLAC_POPULATE_MD5)

                    #fix missing WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                    if (((self.channels() > 2) or
                         (self.bits_per_sample() > 16))):
                        try:
                            vorbis_comment = metadata.get_block(
                                Flac_VORBISCOMMENT.BLOCK_ID)
                        except IndexError:
                            from . import VERSION

                            vorbis_comment = Flac_VORBISCOMMENT(
                                [], u"Python Audio Tools %s" % (VERSION))

                        if ((u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" not in
                             vorbis_comment.keys())):
                            from .text import CLEAN_FLAC_ADD_CHANNELMASK
                            fixes_performed.append(CLEAN_FLAC_ADD_CHANNELMASK)
                            vorbis_comment[
                                u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = \
                                [u"0x%.4X" % (self.channel_mask())]

                            metadata.replace_blocks(
                                Flac_VORBISCOMMENT.BLOCK_ID,
                                [vorbis_comment])

                    #fix an invalid SEEKTABLE, if present
                    try:
                        if (not seektable_valid(
                                metadata.get_block(Flac_SEEKTABLE.BLOCK_ID),
                                stream_offset + 4 + self.metadata_length(),
                                input_f)):
                            from .text import CLEAN_FLAC_FIX_SEEKTABLE
                            fixes_performed.append(CLEAN_FLAC_FIX_SEEKTABLE)

                            metadata.replace_blocks(Flac_SEEKTABLE.BLOCK_ID,
                                                    [self.seektable()])
                    except IndexError:
                        pass

                    #fix remaining metadata problems
                    #which automatically shifts STREAMINFO to the right place
                    #(the message indicating the fix has already been output)
                    output_track.update_metadata(
                        metadata.clean(fixes_performed))

                return output_track
            finally:
                input_f.close()


class FLAC_Data_Chunk:
    def __init__(self, total_frames, pcmreader):
        self.id = "data"
        self.__total_frames__ = total_frames
        self.__pcmreader__ = pcmreader

    def __repr__(self):
        return "FLAC_Data_Chunk()"

    def size(self):
        """returns size of chunk in bytes
        not including any spacer byte for odd-sized chunks"""

        return (self.__total_frames__ *
                self.__pcmreader__.channels *
                (self.__pcmreader__.bits_per_sample / 8))

    def verify(self):
        "returns True"

        return True

    def write(self, f):
        """writes the entire chunk to the given output file object
        returns size of entire chunk (including header and spacer)
        in bytes"""

        from struct import pack
        from . import FRAMELIST_SIZE

        f.write(self.id)
        f.write(pack("<I", self.size()))
        bytes_written = 8
        signed = (self.__pcmreader__.bits_per_sample > 8)
        s = self.__pcmreader__.read(FRAMELIST_SIZE)
        while (len(s) > 0):
            b = s.to_bytes(False, signed)
            f.write(b)
            bytes_written += len(b)
            s = self.__pcmreader__.read(FRAMELIST_SIZE)

        if (bytes_written % 2):
            f.write(chr(0))
            bytes_written += 1

        return bytes_written


class FLAC_SSND_Chunk(FLAC_Data_Chunk):
    def __init__(self, total_frames, pcmreader):
        self.id = "SSND"
        self.__total_frames__ = total_frames
        self.__pcmreader__ = pcmreader

    def __repr__(self):
        return "FLAC_SSND_Chunk()"

    def size(self):
        """returns size of chunk in bytes
        not including any spacer byte for odd-sized chunks"""

        return 8 + (self.__total_frames__ *
                    self.__pcmreader__.channels *
                    (self.__pcmreader__.bits_per_sample / 8))

    def write(self, f):
        """writes the entire chunk to the given output file object
        returns size of entire chunk (including header and spacer)
        in bytes"""

        from struct import pack
        from . import FRAMELIST_SIZE

        f.write(self.id)
        f.write(pack(">I", self.size()))
        bytes_written = 8
        f.write(pack(">II", 0, 0))
        bytes_written += 8
        s = self.__pcmreader__.read(FRAMELIST_SIZE)
        while (len(s) > 0):
            b = s.to_bytes(True, True)
            f.write(b)
            bytes_written += len(b)
            s = self.__pcmreader__.read(FRAMELIST_SIZE)

        if (bytes_written % 2):
            f.write(chr(0))
            bytes_written += 1

        return bytes_written


#######################
#Ogg FLAC
#######################


class OggFlacMetaData(FlacMetaData):
    @classmethod
    def converted(cls, metadata):
        """takes a MetaData object and returns an OggFlacMetaData object"""

        if (metadata is None):
            return None
        elif (isinstance(metadata, FlacMetaData)):
            return cls([block.copy() for block in metadata.block_list])
        else:
            return cls([Flac_VORBISCOMMENT.converted(metadata)] +
                       [Flac_PICTURE.converted(image)
                        for image in metadata.images()])

    def __repr__(self):
        return ("OggFlacMetaData(%s)" % (repr(self.block_list)))

    @classmethod
    def parse(cls, reader):
        """returns an OggFlacMetaData object from the given BitstreamReader

        raises IOError or ValueError if an error occurs reading MetaData"""

        from .ogg import read_ogg_packets

        streaminfo = None
        applications = []
        seektable = None
        vorbis_comment = None
        cuesheet = None
        pictures = []

        packets = read_ogg_packets(reader)

        streaminfo_packet = packets.next()
        streaminfo_packet.set_endianness(0)

        (packet_byte,
         ogg_signature,
         major_version,
         minor_version,
         header_packets,
         flac_signature,
         block_type,
         block_length,
         minimum_block_size,
         maximum_block_size,
         minimum_frame_size,
         maximum_frame_size,
         sample_rate,
         channels,
         bits_per_sample,
         total_samples,
         md5sum) = streaminfo_packet.parse(
             "8u 4b 8u 8u 16u 4b 8u 24u 16u 16u 24u 24u 20u 3u 5u 36U 16b")

        block_list = [Flac_STREAMINFO(minimum_block_size=minimum_block_size,
                                      maximum_block_size=maximum_block_size,
                                      minimum_frame_size=minimum_frame_size,
                                      maximum_frame_size=maximum_frame_size,
                                      sample_rate=sample_rate,
                                      channels=channels + 1,
                                      bits_per_sample=bits_per_sample + 1,
                                      total_samples=total_samples,
                                      md5sum=md5sum)]

        for (i, packet) in zip(range(header_packets), packets):
            packet.set_endianness(0)
            (block_type, length) = packet.parse("1p 7u 24u")
            if (block_type == 1):    # PADDING
                block_list.append(Flac_PADDING.parse(packet, length))
            if (block_type == 2):    # APPLICATION
                block_list.append(Flac_APPLICATION.parse(packet, length))
            elif (block_type == 3):  # SEEKTABLE
                block_list.append(Flac_SEEKTABLE.parse(packet, length / 18))
            elif (block_type == 4):  # VORBIS_COMMENT
                block_list.append(Flac_VORBISCOMMENT.parse(packet))
            elif (block_type == 5):  # CUESHEET
                block_list.append(Flac_CUESHEET.parse(packet))
            elif (block_type == 6):  # PICTURE
                block_list.append(Flac_PICTURE.parse(packet))
            elif ((block_type >= 7) and (block_type <= 126)):
                from .text import ERR_FLAC_RESERVED_BLOCK
                raise ValueError(ERR_FLAC_RESERVED_BLOCK % (block_type))
            elif (block_type == 127):
                from .text import ERR_FLAC_INVALID_BLOCK
                raise ValueError(ERR_FLAC_INVALID_BLOCK)

        return cls(block_list)

    def build(self, oggwriter):
        """oggwriter is an OggStreamWriter-compatible object"""

        from .bitstream import BitstreamRecorder
        from .bitstream import format_size
        from . import iter_first, iter_last

        packet = BitstreamRecorder(0)

        #build extended Ogg FLAC STREAMINFO block
        #which will always occupy its own page
        streaminfo = self.get_block(Flac_STREAMINFO.BLOCK_ID)

        #all our non-STREAMINFO blocks that are small enough
        #to fit in the output stream
        valid_blocks = [b for b in self.blocks()
                        if ((b.BLOCK_ID != Flac_STREAMINFO.BLOCK_ID) and
                            (b.size() < (2 ** 24)))]

        packet.build(
            "8u 4b 8u 8u 16u 4b 8u 24u 16u 16u 24u 24u 20u 3u 5u 36U 16b",
            (0x7F,
             "FLAC",
             1,
             0,
             len(valid_blocks),
             "fLaC",
             0,
             format_size("16u 16u 24u 24u 20u 3u 5u 36U 16b") / 8,
             streaminfo.minimum_block_size,
             streaminfo.maximum_block_size,
             streaminfo.minimum_frame_size,
             streaminfo.maximum_frame_size,
             streaminfo.sample_rate,
             streaminfo.channels - 1,
             streaminfo.bits_per_sample - 1,
             streaminfo.total_samples,
             streaminfo.md5sum))
        oggwriter.write_page(0, [packet.data()], 0, 1, 0)

        #FIXME - adjust non-STREAMINFO blocks to use fewer pages

        #pack remaining metadata blocks into as few pages as possible, if any
        if (len(valid_blocks)):
            for (last_block, block) in iter_last(iter(valid_blocks)):
                packet.reset()
                if (not last_block):
                    packet.build("1u 7u 24u",
                                 (0, block.BLOCK_ID, block.size()))
                else:
                    packet.build("1u 7u 24u",
                                 (1, block.BLOCK_ID, block.size()))
                block.build(packet)
                for (first_page, page_segments) in iter_first(
                    oggwriter.segments_to_pages(
                        oggwriter.packet_to_segments(packet.data()))):
                    oggwriter.write_page(0 if first_page else -1,
                                         page_segments,
                                         0 if first_page else 1, 0, 0)


class __Counter__:
    def __init__(self):
        self.value = 0

    def count_byte(self, i):
        self.value += 1

    def __int__(self):
        return self.value


class OggFlacAudio(FlacAudio):
    """a Free Lossless Audio Codec file inside an Ogg container"""

    from .text import (COMP_FLAC_0, COMP_FLAC_8)

    SUFFIX = "oga"
    NAME = SUFFIX
    DESCRIPTION = u"Ogg FLAC"
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str, range(0, 9)))
    COMPRESSION_DESCRIPTIONS = {"0": COMP_FLAC_0,
                                "8": COMP_FLAC_8}
    BINARIES = ("flac",)
    BINARY_URLS = {"flac": "http://flac.sourceforge.net"}

    METADATA_CLASS = OggFlacMetaData

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_frames__ = 0

        try:
            self.__read_streaminfo__()
        except IOError, msg:
            raise InvalidFLAC(str(msg))

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bitspersample__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__total_frames__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__samplerate__

    def get_metadata(self):
        """returns a MetaData object, or None

        raise ValueError if some error reading metadata
        raises IOError if unable to read the file"""

        f = open(self.filename, "rb")
        try:
            from .bitstream import BitstreamReader

            try:
                return OggFlacMetaData.parse(BitstreamReader(f, 1))
            except ValueError:
                return None
        finally:
            f.close()

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        if (metadata is None):
            return None

        if (not isinstance(metadata, OggFlacMetaData)):
            from .text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        #always overwrite Ogg FLAC with fresh metadata
        #
        #The trouble with Ogg FLAC padding is that Ogg header overhead
        #requires a variable amount of overhead bytes per Ogg page
        #which makes it very difficult to calculate how many
        #bytes to allocate to the PADDING packet.
        #We'd have to build a bunch of empty pages for padding
        #then go back and fill-in the initial padding page's length
        #field before re-checksumming it.

        from .bitstream import BitstreamWriter
        from .bitstream import BitstreamRecorder
        from .bitstream import BitstreamAccumulator
        from .bitstream import BitstreamReader
        from .ogg import OggStreamReader, OggStreamWriter
        from . import TemporaryFile, transfer_data

        new_writer = BitstreamWriter(TemporaryFile(self.filename), 1)

        original_reader = BitstreamReader(file(self.filename, 'rb'), 1)

        original_ogg = OggStreamReader(original_reader)

        new_ogg = OggStreamWriter(new_writer, self.__serial_number__)

        #write our new comment blocks to the new file
        metadata.build(new_ogg)

        #skip the metadata packets in the original file
        OggFlacMetaData.parse(original_reader)

        #transfer the remaining pages from the original file
        #(which are re-sequenced and re-checksummed automatically)
        for (granule_position,
             segments,
             continuation,
             first_page,
             last_page) in original_ogg.pages():
            new_ogg.write_page(granule_position,
                               segments,
                               continuation,
                               first_page,
                               last_page)

        original_reader.close()
        new_writer.close()


    def metadata_length(self):
        """returns the length of all Ogg FLAC metadata blocks as an integer

        this includes all Ogg page headers"""

        from .bitstream import BitstreamReader

        f = file(self.filename, 'rb')
        try:
            byte_count = __Counter__()
            ogg_stream = BitstreamReader(f, 1)
            ogg_stream.add_callback(byte_count.count_byte)

            OggFlacMetaData.parse(ogg_stream)

            return int(byte_count)
        finally:
            f.close()

    def __read_streaminfo__(self):
        from .bitstream import BitstreamReader

        f = open(self.filename, "rb")
        try:
            ogg_reader = BitstreamReader(f, 1)
            (magic_number,
             version,
             header_type,
             granule_position,
             self.__serial_number__,
             page_sequence_number,
             checksum,
             segment_count) = ogg_reader.parse("4b 8u 8u 64S 32u 32u 32u 8u")

            if (magic_number != 'OggS'):
                from .text import ERR_OGG_INVALID_MAGIC_NUMBER
                raise InvalidFLAC(ERR_OGG_INVALID_MAGIC_NUMBER)
            if (version != 0):
                from .text import ERR_OGG_INVALID_VERSION
                raise InvalidFLAC(ERR_OGG_INVALID_VERSION)

            segment_length = ogg_reader.read(8)

            ogg_reader.set_endianness(0)

            (packet_byte,
             ogg_signature,
             major_version,
             minor_version,
             self.__header_packets__,
             flac_signature,
             block_type,
             block_length,
             minimum_block_size,
             maximum_block_size,
             minimum_frame_size,
             maximum_frame_size,
             self.__samplerate__,
             self.__channels__,
             self.__bitspersample__,
             self.__total_frames__,
             self.__md5__) = ogg_reader.parse(
                 "8u 4b 8u 8u 16u 4b 8u 24u 16u 16u 24u 24u 20u 3u 5u 36U 16b")

            if (packet_byte != 0x7F):
                from .text import ERR_OGGFLAC_INVALID_PACKET_BYTE
                raise InvalidFLAC(ERR_OGGFLAC_INVALID_PACKET_BYTE)
            if (ogg_signature != 'FLAC'):
                from .text import ERR_OGGFLAC_INVALID_OGG_SIGNATURE
                raise InvalidFLAC(ERR_OGGFLAC_INVALID_OGG_SIGNATURE)
            if (major_version != 1):
                from .text import ERR_OGGFLAC_INVALID_MAJOR_VERSION
                raise InvalidFLAC(ERR_OGGFLAC_INVALID_MAJOR_VERSION)
            if (minor_version != 0):
                from .text import ERR_OGGFLAC_INVALID_MINOR_VERSION
                raise InvalidFLAC(ERR_OGGFLAC_INVALID_MINOR_VERSION)
            if (flac_signature != 'fLaC'):
                from .text import ERR_OGGFLAC_VALID_FLAC_SIGNATURE
                raise InvalidFLAC(ERR_OGGFLAC_VALID_FLAC_SIGNATURE)

            self.__channels__ += 1
            self.__bitspersample__ += 1
        finally:
            f.close()

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from . import decoders
        from . import PCMReaderError

        try:
            return decoders.OggFlacDecoder(self.filename,
                                           self.channel_mask())
        except (IOError, ValueError), msg:
            #The only time this is likely to occur is
            #if the Ogg FLAC is modified between when OggFlacAudio
            #is initialized and when to_pcm() is called.
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None,
                 total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new OggFlacAudio object"""

        from . import BIN
        from . import transfer_framelist_data
        from . import ignore_sigint
        from . import EncodingError
        from . import DecodingError
        from . import UnsupportedChannelCount
        from . import __default_quality__
        import subprocess
        import os

        SUBSTREAM_SAMPLE_RATES = frozenset([8000,  16000, 22050, 24000, 32000,
                                            44100, 48000, 96000])
        SUBSTREAM_BITS = frozenset([8, 12, 16, 20, 24])

        if ((compression is None) or (compression not in
                                      cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if (((pcmreader.sample_rate in SUBSTREAM_SAMPLE_RATES) and
             (pcmreader.bits_per_sample in SUBSTREAM_BITS))):
            lax = []
        else:
            lax = ["--lax"]

        if (pcmreader.channels > 8):
            raise UnsupportedChannelCount(filename, pcmreader.channels)

        if (int(pcmreader.channel_mask) == 0):
            if (pcmreader.channels <= 6):
                channel_mask = {1: 0x0004,
                                2: 0x0003,
                                3: 0x0007,
                                4: 0x0033,
                                5: 0x0037,
                                6: 0x003F}[pcmreader.channels]
            else:
                channel_mask = 0

        elif (int(pcmreader.channel_mask) not in
              (0x0001,    # 1ch - mono
               0x0004,    # 1ch - mono
               0x0003,    # 2ch - left, right
               0x0007,    # 3ch - left, right, center
               0x0033,    # 4ch - left, right, back left, back right
               0x0603,    # 4ch - left, right, side left, side right
               0x0037,    # 5ch - L, R, C, back left, back right
               0x0607,    # 5ch - L, R, C, side left, side right
               0x003F,    # 6ch - L, R, C, LFE, back left, back right
               0x060F)):  # 6ch - L, R, C, LFE, side left, side right
            from . import UnsupportedChannelMask

            raise UnsupportedChannelMask(filename,
                                         int(pcmreader.channel_mask))
        else:
            channel_mask = int(pcmreader.channel_mask)

        devnull = file(os.devnull, 'ab')

        sub = subprocess.Popen([BIN['flac']] + lax +
                               ["-s", "-f", "-%s" % (compression),
                                "-V", "--ogg",
                                "--endian=little",
                                "--channels=%d" % (pcmreader.channels),
                                "--bps=%d" % (pcmreader.bits_per_sample),
                                "--sample-rate=%d" % (pcmreader.sample_rate),
                                "--sign=signed",
                                "--force-raw-format",
                                "-o", filename, "-"],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)

        try:
            transfer_framelist_data(pcmreader, sub.stdin.write)
        except (ValueError, IOError), err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise err

        try:
            pcmreader.close()
        except DecodingError, err:
            raise EncodingError(err.error_message)
        sub.stdin.close()
        devnull.close()

        if (sub.wait() == 0):
            oggflac = OggFlacAudio(filename)
            if ((((pcmreader.channels > 2) or
                  (pcmreader.bits_per_sample > 16)) and
                 (channel_mask != 0))):
                metadata = oggflac.get_metadata()
                vorbis = metadata.get_block(Flac_VORBISCOMMENT.BLOCK_ID)
                vorbis[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4X" % (channel_mask)]
                oggflac.update_metadata(metadata)
            return oggflac
        else:
            #FIXME
            raise EncodingError(u"error encoding file with flac")

    def sub_pcm_tracks(self):
        """yields a PCMReader object per cuesheet track

        this currently does nothing since the FLAC reference
        decoder has limited support for Ogg FLAC
        """

        return iter([])

    def verify(self, progress=None):
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        from .verify import ogg as verify_ogg_stream

        #Ogg stream verification is likely to be so fast
        #that individual calls to progress() are
        #a waste of time.
        if (progress is not None):
            progress(0, 1)

        try:
            f = open(self.filename, 'rb')
        except IOError, err:
            raise InvalidFLAC(str(err))
        try:
            try:
                result = verify_ogg_stream(f)
                if (progress is not None):
                    progress(1, 1)
                return result is None
            except (IOError, ValueError), err:
                raise InvalidFLAC(str(err))
        finally:
            f.close()
