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


from audiotools import (AudioFile, MetaData, InvalidFile, PCMReader,
                        transfer_data, transfer_framelist_data,
                        subprocess, BIN, BUFFER_SIZE, cStringIO,
                        os, open_files, Image, sys, WaveAudio, AiffAudio,
                        ReplayGain, ignore_sigint, sheet_to_unicode,
                        EncodingError, UnsupportedChannelMask, DecodingError,
                        UnsupportedChannelCount, analyze_frames,
                        Messenger, BufferedPCMReader, calculate_replay_gain,
                        ChannelMask, PCMReaderError, __default_quality__,
                        WaveContainer, AiffContainer, to_pcm_progress,
                        image_metrics)
from __vorbiscomment__ import *
from __id3__ import ID3v2Comment

import gettext

gettext.install("audiotools", unicode=True)


#######################
#FLAC
#######################


class InvalidFLAC(InvalidFile):
    pass


class FlacMetaDataBlockTooLarge(Exception):
    """Raised if one attempts to build a FlacMetaDataBlock too large."""

    pass

class FlacMetaData(MetaData):
    """A class for managing a native FLAC's metadata."""

    def __init__(self, blocks):
        self.__dict__["block_list"] = list(blocks)

    def has_block(self, block_id):
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

        blocks_to_skip = set(PREFERRED_ORDER[0:PREFERRED_ORDER.index(
                    block.BLOCK_ID)])

        for (index, old_block) in enumerate(self.block_list):
            if (old_block.BLOCK_ID not in blocks_to_skip):
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
                #add VORBISCOMMENT block if necessary
                vorbis_comment = Flac_VORBISCOMMENT(
                    [], u"Python Audio Tools %s" % (VERSION))

                self.add_block(vorbis_comment)

            setattr(vorbis_comment, key, value)
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):
        if (key in self.FIELDS):
            try:
                return getattr(self.get_block(Flac_VORBISCOMMENT.BLOCK_ID), key)
            except IndexError:
                if (key in self.INTEGER_FIELDS):
                    return 0
                else:
                    return u""
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
                #no VORBIS comment block
                pass
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    @classmethod
    def converted(cls, metadata):
        """Takes a MetaData object and returns a FlacMetaData object."""

        if (isinstance(metadata, OggFlacMetaData)):
            return cls(metadata.block_list)
        elif ((metadata is None) or (isinstance(metadata, FlacMetaData))):
            return metadata
        else:
            return cls([Flac_VORBISCOMMENT.converted(metadata)] +
                       [Flac_PICTURE.converted(image)
                        for image in metadata.images()] +
                       [Flac_PADDING(4096)])

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        try:
            vorbis_comment = self.get_block(Flac_VORBISCOMMENT.BLOCK_ID)
        except IndexError:
            vorbis_comment = Flac_VORBISCOMMENT(
                [], u"Python Audio Tools %s" % (VERSION))

        vorbis_comment.merge(metadata)
        if (len(self.images()) == 0):
            for image in metadata.images():
                self.add_image(image)

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        self.add_block(Flac_PICTURE.converted(image))

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        self.block_list = [b for b in self.block_list
                           if not ((b.BLOCK_ID == Flac_PICTURE.BLOCK_ID) and
                                   (b == image))]

    def images(self):
        """Returns a list of embedded Image objects."""

        return self.get_blocks(Flac_PICTURE.BLOCK_ID)

    @classmethod
    def supports_images(cls):
        """Returns True."""

        return True

    def clean(self, fixes_performed):
        """Returns a new FlacMetaData object that's been cleaned of problems.

        Any fixes performed are appended to fixes_performed as Unicode."""

        cleaned_blocks = []

        for block in self.block_list:
            if (block.BLOCK_ID == Flac_STREAMINFO.BLOCK_ID):
                #reorder STREAMINFO block to be first, if necessary
                if (len(cleaned_blocks) == 0):
                    cleaned_blocks.append(block)
                elif (cleaned_blocks[0].BLOCK_ID != block.BLOCK_ID):
                    fixes_performed.append(
                        _(u"moved STREAMINFO to first block"))
                    cleaned_blocks.insert(0, block)
                else:
                    fixes_performed.append(
                        _(u"removing redundant STREAMINFO block"))
            elif (block.BLOCK_ID == Flac_VORBISCOMMENT.BLOCK_ID):
                if (block.BLOCK_ID in [b.BLOCK_ID for b in cleaned_blocks]):
                    #remove redundant VORBIS_COMMENT blocks
                    fixes_performed.append(
                        _(u"removing redundant VORBIS_COMMENT block"))
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
                        _(u"removing redundant SEEKTABLE block"))
                else:
                    cleaned_blocks.append(block)
            elif (block.BLOCK_ID == Flac_CUESHEET.BLOCK_ID):
                #remove redundant cuesheet, if necessary
                if (block.BLOCK_ID in [b.BLOCK_ID for b in cleaned_blocks]):
                    fixes_performed.append(
                        _(u"removing redundant CUESHEET block"))
                else:
                    cleaned_blocks.append(block)
            elif (block.BLOCK_ID == Flac_PADDING.BLOCK_ID):
                cleaned_blocks.append(block)
            else:
                #remove undefined blocks
                fixes_performed.append(_(u"removing undefined block"))

        return self.__class__(cleaned_blocks)


    def __repr__(self):
        return "FlacMetaData(%s)" % (self.block_list)

    @classmethod
    def parse(cls, reader):
        block_list = []

        last = 0

        while (last != 1):
            (last, block_type, block_length) = reader.parse("1u7u24u")

            if (block_type == 0):   #STREAMINFO
                block_list.append(
                    Flac_STREAMINFO.parse(reader.substream(block_length)))
            elif (block_type == 1): #PADDING
                block_list.append(Flac_PADDING.parse(
                        reader.substream(block_length), block_length))
            elif (block_type == 2): #APPLICATION
                block_list.append(Flac_APPLICATION.parse(
                        reader.substream(block_length), block_length))
            elif (block_type == 3): #SEEKTABLE
                block_list.append(
                    Flac_SEEKTABLE.parse(reader.substream(block_length),
                                         block_length / 18))
            elif (block_type == 4): #VORBIS_COMMENT
                block_list.append(Flac_VORBISCOMMENT.parse(
                        reader.substream(block_length)))
            elif (block_type == 5): #CUESHEET
                block_list.append(
                    Flac_CUESHEET.parse(reader.substream(block_length)))
            elif (block_type == 6): #PICTURE
                block_list.append(Flac_PICTURE.parse(
                        reader.substream(block_length)))
            elif ((block_type >= 7) and (block_type <= 126)):
                raise ValueError(_(u"reserved metadata block type %d") %
                                 (block_type))
            else:
                raise ValueError(_(u"invalid metadata block type"))

        return cls(block_list)

    def raw_info(self):
        from os import linesep

        return linesep.decode('ascii').join(
            ["FLAC Tags:"] + [block.raw_info() for block in self.blocks()])

    def blocks(self):
        for block in self.block_list:
            yield block

    def build(self, writer):
        from . import iter_last

        for (last_block, block) in iter_last(iter([b for b in self.blocks()
                                                   if (b.size() < (2 ** 24))])):
            if (not last_block):
                writer.build("1u7u24u", (0, block.BLOCK_ID, block.size()))
            else:
                writer.build("1u7u24u", (1, block.BLOCK_ID, block.size()))

            block.build(writer)

    def size(self):
        from operator import add

        return reduce(add, [4 + b.size() for b in self.block_list], 0)


class Flac_STREAMINFO:
    BLOCK_ID = 0

    def __init__(self, minimum_block_size, maximum_block_size,
                 minimum_frame_size, maximum_frame_size,
                 sample_rate, channels, bits_per_sample,
                 total_samples, md5sum):
        self.minimum_block_size = minimum_block_size
        self.maximum_block_size = maximum_block_size
        self.minimum_frame_size = minimum_frame_size
        self.maximum_frame_size = maximum_frame_size
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.total_samples = total_samples
        self.md5sum = md5sum

    def __eq__(self, metadata):
        from operator import and_

        return reduce(and_, [getattr(self, attr) == getattr(metadata, attr)
                             for attr in ["minimum_block_size",
                                          "maximum_block_size",
                                          "minimum_frame_size",
                                          "maximum_frame_size",
                                          "sample_rate",
                                          "channels",
                                          "bits_per_sample",
                                          "total_samples",
                                          "md5sum"]])

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
             u"               MD5 sum = %s" % (u"".join(
                        ["%2.2X" % (ord(b)) for b in self.md5sum]))])

    @classmethod
    def parse(cls, reader):
        values = reader.parse("16u16u24u24u20u3u5u36U16b")
        values[5] += 1  #channels
        values[6] += 1  #bits-per-sample
        return cls(*values)

    def build(self, writer):
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
        return 34


class Flac_VORBISCOMMENT(VorbisComment):
    BLOCK_ID = 4

    def __repr__(self):
        return "Flac_VORBISCOMMENT(%s, %s)" % \
            (repr(self.comment_strings), repr(self.vendor_string))

    def raw_info(self):
        from os import linesep
        from . import display_unicode

        #align the text strings on the "=" sign, if any

        if (len(self.comment_strings) > 0):
            max_indent = max([len(display_unicode(comment.split(u"=", 1)[0]))
                              for comment in self.comment_strings
                              if u"=" in comment])
        else:
            max_indent = 0

        comment_strings = []
        for comment in self.comment_strings:
            if (u"=" in comment):
                comment_strings.append(
                    u" " * (4 + max_indent -
                            len(display_unicode(comment.split(u"=", 1)[0]))) +
                    comment)
            else:
                comment_strings.append(u" " * 4 + comment)

        return linesep.decode('ascii').join(
            [u"  VORBIS_COMMENT:",
             u"    %s" % (self.vendor_string)] +
            comment_strings)

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to a VorbisComment object."""

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
        reader.set_endianness(1)
        vendor_string = reader.read_bytes(reader.read(32)).decode('utf-8')
        return cls([reader.read_bytes(reader.read(32)).decode('utf-8')
                    for i in xrange(reader.read(32))], vendor_string)

    def build(self, writer):
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
        from operator import add

        return (4 + len(self.vendor_string.encode('utf-8')) +
                4 +
                reduce(add, [4 + len(comment.encode('utf-8'))
                             for comment in self.comment_strings], 0))


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

            return {0:4, 3:0, 4:1, 5:2, 6:3}.get(self.picture_type, 4)
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

            self.picture_type = {4:0, 0:3, 1:4, 2:5, 3:6}.get(value, 0)
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
        writer.build("32u [ 32u%db ] [32u%db ] 32u 32u 32u 32u [ 32u%db ]" %
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
        from .bitstream import format_size

        return format_size(
            "32u [ 32u%db ] [32u%db ] 32u 32u 32u 32u [ 32u%db ]" %
            (len(self.mime_type.encode('ascii')),
             len(self.description.encode('utf-8')),
             len(self.data))) / 8

    @classmethod
    def converted(cls, image):
        """Converts an Image object to a FlacPictureComment."""

        return cls(
            picture_type={4:0, 0:3, 1:4, 2:5, 3:6}.get(image.type, 0),
            mime_type=image.mime_type,
            description=image.description,
            width=image.width,
            height=image.height,
            color_depth=image.color_depth,
            color_count=image.color_count,
            data=image.data)

    def type_string(self):
        """Returns the image's type as a human readable plain string.

        For example, an image of type 0 returns "Front Cover".
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
        img = image_metrics(self.data)

        if ((self.mime_type != img.mime_type) or
            (self.width != img.width) or
            (self.height != img.height) or
            (self.color_depth != img.bits_per_pixel) or
            (self.color_count != img.color_count)):
            fixes_performed.append(_(u"fixed embedded image metadata fields"))
            return self.__class__.converted(Image(
                    type=self.type,
                    mime_type=img.mime_type,
                    description=self.description,
                    width=img.width,
                    height=img.height,
                    color_depth=img.bits_per_pixel,
                    color_count=img.color_count,
                    data=self.data))
        else:
            return self

class Flac_APPLICATION:
    BLOCK_ID = 2

    def __init__(self, application_id, data):
        self.application_id = application_id
        self.data = data

    def __repr__(self):
        return "Flac_APPLICATION(%s, %s)" % (repr(self.application_id),
                                             repr(self.data))

    def raw_info(self):
        from os import linesep

        return u"  APPLICATION:%s    %s (%d bytes)" % \
            (linesep.decode('ascii'),
             self.application_id.decode('ascii'),
             len(self.data))

    @classmethod
    def parse(cls, reader, block_length):
        return cls(application_id=reader.read_bytes(4),
                   data=reader.read_bytes(block_length - 4))

    def build(self, writer):
        writer.write_bytes(self.application_id)
        writer.write_bytes(self.data)

    def size(self):
        return len(self.application_id) + len(self.data)

class Flac_SEEKTABLE:
    BLOCK_ID = 3

    def __init__(self, seekpoints):
        self.seekpoints = seekpoints

    def __repr__(self):
        return "Flac_SEEKTABLE(%s)" % (repr(self.seekpoints))

    def raw_info(self):
        from os import linesep

        return linesep.decode('ascii').join(
            [u"  SEEKTABLE:",
             u"    first sample   file offset   frame samples"] +
            [u"  %14.d %13.X %15.d" % seekpoint
             for seekpoint in self.seekpoints])

    @classmethod
    def parse(cls, reader, total_seekpoints):
        return cls([tuple(reader.parse("64U64U16u"))
                    for i in xrange(total_seekpoints)])

    def build(self, writer):
        for seekpoint in self.seekpoints:
            writer.build("64U64U16u", seekpoint)

    def size(self):
        from .bitstream import format_size

        return (format_size("64U64U16u") / 8) * len(self.seekpoints)

class Flac_CUESHEET:
    BLOCK_ID = 5

    def __init__(self, catalog_number, lead_in_samples, is_cdda, tracks):
        self.catalog_number = catalog_number
        self.lead_in_samples = lead_in_samples
        self.is_cdda = is_cdda
        self.tracks = tracks

    def __eq__(self, cuesheet):
        from operator import and_
        try:
            return reduce(and_, [getattr(self, attr) == getattr(cuesheet, attr)
                                 for attr in ["catalog_number",
                                              "lead_in_samples",
                                              "is_cdda",
                                              "tracks"]])
        except AttributeError:
            return False

    def __repr__(self):
        return ("Flac_CUESHEET(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["catalog_number",
                                      "lead_in_samples",
                                      "is_cdda",
                                      "tracks"]]))

    def raw_info(self):
        from os import linesep

        return linesep.decode('ascii').join(
            [u"  CUESHEET:",
             u"     catalog number = %s" % \
                 (self.catalog_number.decode('ascii', 'replace')),
             u"    lead-in samples = %d" % (self.lead_in_samples),
             u"            is CDDA = %d" % (self.is_cdda),
             u"    track        offset          ISRC"] +
            [track.raw_info() for track in self.tracks])

    @classmethod
    def parse(cls, reader):
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
        writer.build("128b64U1u2071p8u",
                     (self.catalog_number,
                      self.lead_in_samples,
                      self.is_cdda,
                      len(self.tracks)))
        for track in self.tracks:
            track.build(writer)

    def size(self):
        from .bitstream import BitstreamAccumulator

        a = BitstreamAccumulator(0)
        self.build(a)
        return a.bytes()

    @classmethod
    def converted(cls, sheet, total_frames, sample_rate=44100):
        """Converts a cuesheet compatible object to Flac_CUESHEET objects.

        A total_frames integer (in PCM frames) is also required.
        """

        if (sheet.catalog() is None):
            catalog_number = chr(0) * 128
        else:
            catalog_number = sheet.catalog() + (chr(0) *
                                                (128 - len(sheet.catalog())))

        ISRCs = sheet.ISRCs()

        return cls(catalog_number=catalog_number,
                   lead_in_samples=sample_rate * 2,
                   is_cdda=1 if sample_rate == 44100 else 0,
                   tracks=
                   [Flac_CUESHEET_track(offset=indexes[0] * sample_rate / 75,
                                        number=i + 1,
                                        ISRC=ISRCs.get(i + 1, chr(0) * 12),
                                        track_type=0,
                                        pre_emphasis=0,
                                        index_points=
                                        [Flac_CUESHEET_index(
                            offset=(index - indexes[0]) * sample_rate / 75,
                            number=point_number + (1 if len(indexes) == 1
                                                   else 0))
                                         for (point_number, index)
                                         in enumerate(indexes)])
                    for (i, indexes) in enumerate(sheet.indexes())] +
                   #lead-out track
                   [Flac_CUESHEET_track(offset=total_frames,
                                        number=170,
                                        ISRC=chr(0) * 12,
                                        track_type=0,
                                        pre_emphasis=0,
                                        index_points=[])])


    def catalog(self):
        """Returns the cuesheet's catalog number as a plain string."""

        catalog_number = self.catalog_number.rstrip(chr(0))

        if (len(catalog_number) > 0):
            return catalog_number
        else:
            return None

    def ISRCs(self):
        """Returns a dict of ISRC values as plain strings."""

        return dict([(track.number, track.ISRC) for track in
                     self.tracks
                     if ((track.number != 170) and
                         (len(track.ISRC.strip(chr(0))) > 0))])


    def indexes(self, sample_rate=44100):
        """Returns a list of (start, end) integer tuples."""

        return [tuple([(index.offset + track.offset) * 75 / sample_rate
                       for index in
                       sorted(track.index_points,
                              lambda i1, i2: cmp(i1.number, i2.number))])
                for track in
                sorted(self.tracks, lambda t1, t2: cmp(t1.number, t2.number))
                if (track.number != 170)]


    def pcm_lengths(self, total_length):
        """Returns a list of PCM lengths for all cuesheet audio tracks.

        Note that the total length variable is only for compatibility.
        It is not necessary for FlacCueSheets.
        """

        if (len(self.tracks) > 0):
            return [(current.offset +
                     max([i.offset for i in current.index_points] + [0])) -
                    ((previous.offset +
                      max([i.offset for i in previous.index_points] + [0])))
                    for (previous, current) in
                    zip(self.tracks, self.tracks[1:])]
        else:
            return []

    def __unicode__(self):
       return sheet_to_unicode(self, None)


class Flac_CUESHEET_track:
    def __init__(self, offset, number, ISRC, track_type, pre_emphasis,
                 index_points):
        self.offset = offset
        self.number = number
        self.ISRC = ISRC
        self.track_type = track_type
        self.pre_emphasis = pre_emphasis
        self.index_points = index_points

    def __repr__(self):
        return ("Flac_CUESHEET_track(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["offset",
                                      "number",
                                      "ISRC",
                                      "track_type",
                                      "pre_emphasis",
                                      "index_points"]]))

    def raw_info(self):
        if (len(self.ISRC.strip(chr(0))) > 0):
            return u"%9.d %13.d  %s" % \
                (self.number, self.offset, self.ISRC)
        else:
            return u"%9.d %13.d" % \
                (self.number, self.offset)

    def __eq__(self, track):
        from operator import and_
        try:
            return reduce(and_, [getattr(self, attr) == getattr(track, attr)
                                 for attr in ["offset",
                                              "number",
                                              "ISRC",
                                              "track_type",
                                              "pre_emphasis",
                                              "index_points"]])
        except AttributeError:
            return False

    @classmethod
    def parse(cls, reader):
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
        self.offset = offset
        self.number = number

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
        (offset, number) = reader.parse("64U8u24p")

        return cls(offset, number)

    def build(self, writer):
        writer.build("64U8u24p", (self.offset, self.number))


class Flac_PADDING:
    BLOCK_ID = 1

    def __init__(self, length):
        self.length = length

    def __repr__(self):
        return "Flac_PADDING(%d)" % (self.length)

    def raw_info(self):
        from os import linesep

        return linesep.decode('ascii').join(
            [u"  PADDING:",
             u"    length = %d" % (self.length)])

    @classmethod
    def parse(cls, reader, block_length):
        reader.skip_bytes(block_length)
        return cls(length=block_length)

    def build(self, writer):
        writer.write_bytes(chr(0) * self.length)

    def size(self):
        return self.length


class FlacAudio(WaveContainer, AiffContainer):
    """A Free Lossless Audio Codec file."""

    SUFFIX = "flac"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str, range(0, 9)))
    COMPRESSION_DESCRIPTIONS = {"0": _(u"least amount of compresson, " +
                                       u"fastest compression speed"),
                                "8": _(u"most amount of compression, " +
                                       u"slowest compression speed")}

    METADATA_CLASS = FlacMetaData

    def __init__(self, filename):
        """filename is a plain string."""

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

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""


        if (file.read(4) == 'fLaC'):
            #proper FLAC file with no junk at the beginning
            try:
                block_ids = list(cls.__block_ids__(file))
            except (ValueError,IOError):
                return False
            if ((len(block_ids) == 0) or (0 not in block_ids)):
                return False
            else:
                return True
        else:
            #messed-up FLAC file with ID3v2 tags at the beginning
            #which can be fixed using clean()
            file.seek(0, 0)
            if (file.read(3) == 'ID3'):
                file.seek(-3, 1)
                ID3v2Comment.skip(file)
                if (file.read(4) == 'fLaC'):
                    try:
                        block_ids = list(cls.__block_ids__(file))
                    except (ValueError,IOError):
                        return False
                    if ((len(block_ids) == 0) or (0 not in block_ids)):
                        return False
                    else:
                        return True
                else:
                    return False
            else:
                return False

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        if (self.channels() <= 2):
            return ChannelMask.from_channels(self.channels())

        try:
            return ChannelMask(
                int(self.get_metadata().get_block(
                        Flac_VORBISCOMMENT.BLOCK_ID)[
                        u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"][0], 16))
        except (IndexError,KeyError,ValueError):
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
        """Returns True."""

        return True

    def get_metadata(self):
        """Returns a MetaData object.

        Raises IOError if unable to read the file."""

        #FlacAudio *always* returns a FlacMetaData object
        #even if the blocks aren't present
        #so there's no need to test for None

        f = file(self.filename, 'rb')
        try:
            f.seek(self.__stream_offset__, 0)
            if (f.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            from .bitstream import BitstreamReader

            return FlacMetaData.parse(BitstreamReader(f, 0))
        finally:
            f.close()

    def update_metadata(self, metadata):
        """Takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object.

        Raises IOError if unable to write the file.
        """

        from .bitstream import BitstreamWriter
        from .bitstream import BitstreamAccumulator
        from .bitstream import BitstreamReader
        from operator import add

        if (not isinstance(metadata, FlacMetaData)):
            raise ValueError(_(u"metadata not from audio file"))

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

            import tempfile

            stream = file(self.filename, 'rb')
            stream.seek(self.__stream_offset__, 0)

            if (stream.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            #skip the existing metadata blocks
            stop = 0
            reader = BitstreamReader(stream, 0)
            while (stop == 0):
                (stop, length) = reader.parse("1u 7p 24u")
                reader.skip_bytes(length)

            #write the remaining data stream to a temp file
            file_data = tempfile.TemporaryFile()
            transfer_data(stream.read, file_data.write)
            file_data.seek(0, 0)

            #finally, rebuild our file using new metadata and old stream
            stream = file(self.filename, 'wb')
            stream.write('fLaC')
            writer = BitstreamWriter(stream, 0)
            metadata.build(writer)
            writer.flush()
            transfer_data(file_data.read, stream.write)
            file_data.close()
            stream.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        new_metadata = self.METADATA_CLASS.converted(metadata)

        if (new_metadata is None):
            return

        old_metadata = self.get_metadata()

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

                #update WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                #from our current VORBIS_COMMENT block
                if (((self.channels() > 2) or (self.bits_per_sample() > 16)) and
                    (u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" in
                     old_vorbiscomment.keys())):
                    new_vorbiscomment[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = \
                        old_vorbiscomment[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"]

                old_metadata.replace_blocks(Flac_VORBISCOMMENT.BLOCK_ID,
                                            [new_vorbiscomment])
            else:
                #new metadata has VORBIS_COMMENT block,
                #but old metadata does not
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
        """Returns the length of all FLAC metadata blocks as an integer.

        not including the 4 byte "fLaC" file header."""

        from .bitstream import BitstreamReader

        counter = 0
        f = file(self.filename, 'rb')
        try:
            f.seek(self.__stream_offset__, 0)
            reader = BitstreamReader(f, 0)

            if (reader.read_bytes(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

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
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

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
                raise ValueError(_(u"invalid FLAC block ID"))
            reader.skip_bytes(length)

    def set_cuesheet(self, cuesheet):
        """Imports cuesheet data from a Cuesheet-compatible object.

        This are objects with catalog(), ISRCs(), indexes(), and pcm_lengths()
        methods.  Raises IOError if an error occurs setting the cuesheet."""

        if (cuesheet is not None):
            metadata = self.get_metadata()
            metadata.add_block(Flac_CUESHEET.converted(
                    cuesheet, self.total_frames(), self.sample_rate()))
            self.update_metadata(metadata)

    def get_cuesheet(self):
        """Returns the embedded Cuesheet-compatible object, or None.

        Raises IOError if a problem occurs when reading the file."""

        try:
            return self.get_metadata().get_block(Flac_CUESHEET.BLOCK_ID)
        except IndexError:
            return None

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        from . import decoders

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
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new FlacAudio object."""

        from . import encoders

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        encoding_options = {"0": {"block_size": 1152,
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
                                  "max_residual_partition_order": 6}}[
            compression]

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
             0x060F)):  # 6 ch - L, R, C, LFE, side left, side right
            raise UnsupportedChannelMask(filename,
                                         int(pcmreader.channel_mask))
        else:
            channel_mask = int(pcmreader.channel_mask)

        try:
            offsets = encoders.encode_flac(
                filename,
                pcmreader=BufferedPCMReader(pcmreader),
                **encoding_options)
            flac = FlacAudio(filename)
            metadata = flac.get_metadata()

            #generate SEEKTABLE from encoder offsets and add it to metadata
            from bisect import bisect_right

            metadata_length = flac.metadata_length()
            seekpoint_interval = pcmreader.sample_rate * 10
            total_samples = 0
            all_frames = {}
            sample_offsets = []
            for (byte_offset, pcm_frames) in offsets:
                all_frames[total_samples] = (byte_offset - metadata_length,
                                             pcm_frames)
                sample_offsets.append(total_samples)
                total_samples += pcm_frames

            seekpoints = []
            for pcm_frame in xrange(0,
                                    flac.total_frames(),
                                    seekpoint_interval):
                flac_frame = bisect_right(sample_offsets, pcm_frame) - 1
                seekpoints.append((sample_offsets[flac_frame],
                                   all_frames[sample_offsets[flac_frame]][0],
                                   all_frames[sample_offsets[flac_frame]][1]))

            metadata.add_block(Flac_SEEKTABLE(seekpoints))

            #if channels or bps is too high,
            #automatically generate and add channel mask
            if (((pcmreader.channels > 2) or
                 (pcmreader.bits_per_sample > 16)) and
                (channel_mask != 0)):
                metadata.get_block(Flac_VORBISCOMMENT.BLOCK_ID)[
                    u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4X" % (channel_mask)]

            flac.update_metadata(metadata)

            return flac
        except (IOError, ValueError), err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            cls.__unlink__(filename)
            raise err

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        return 'riff' in [
            block.application_id for block in
            self.get_metadata().get_blocks(Flac_APPLICATION.BLOCK_ID)]

    def riff_wave_chunks(self, progress=None):
        """Generate a set of (chunk_id, chunk_size, chunk_data) string tuples

        Note that chunk_size is also a string
        These are for use by WaveAudio.from_chunks
        and are taken from "riff" APPLICATION blocks
        or generated from our PCM data."""

        from struct import pack

        for application_block in [
            block.data for block in
            self.get_metadata().get_blocks(Flac_APPLICATION.BLOCK_ID)
            if (block.application_id == "riff")]:

            (chunk_id, chunk_size, chunk_data) = (application_block[0:4],
                                                  application_block[4:8],
                                                  application_block[8:])
            if (chunk_id == 'RIFF'):
                continue
            elif (chunk_id == 'data'):
                #FIXME - this is a lot more inefficient than it should be
                data = cStringIO.StringIO()
                pcm = to_pcm_progress(self, progress)
                if (pcm.bits_per_sample > 8):
                    transfer_framelist_data(pcm, data.write, True, False)
                else:
                    transfer_framelist_data(pcm, data.write, False, False)
                pcm.close()
                if (len(data.getvalue()) % 2):
                    yield (chunk_id,
                           pack("<I", len(data.getvalue())),
                           data.getvalue() + chr(0))
                else:
                    yield (chunk_id,
                           pack("<I", len(data.getvalue())),
                           data.getvalue())
                data.close()
            else:
                yield (chunk_id, chunk_size, chunk_data)

    def to_wave(self, wave_filename, progress=None):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        if (self.has_foreign_riff_chunks()):
            WaveAudio.wave_from_chunks(wave_filename,
                                       self.riff_wave_chunks(progress))
        else:
            WaveAudio.from_pcm(wave_filename, to_pcm_progress(self, progress))

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None,
                  progress=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new FlacAudio object."""

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if (WaveAudio(wave_filename).has_foreign_riff_chunks()):
            flac = cls.from_pcm(filename,
                                to_pcm_progress(WaveAudio(wave_filename),
                                                progress),
                                compression=compression)

            metadata = flac.get_metadata()

            from .bitstream import BitstreamReader,BitstreamRecorder

            wav = BitstreamReader(file(wave_filename, 'rb'), 1)
            chunk = BitstreamRecorder(1)
            try:
                (riff, total_size, wave) = wav.parse("4b 32u 4b")
                chunk.build("4b 32u 4b", (riff, total_size, wave))

                metadata.add_block(Flac_APPLICATION(
                        application_id="riff",
                        data=chunk.data()))

                total_size -= 4
                while (total_size > 0):
                    chunk.reset()
                    (chunk_id, chunk_size) = wav.parse("4b 32u")
                    chunk.build("4b 32u", (chunk_id, chunk_size))
                    total_size -= 8
                    if (chunk_id != 'data'):
                        chunk.write_bytes(wav.read_bytes(chunk_size))
                        total_size -= chunk_size
                        if (chunk_size % 2):
                            chunk.write_bytes(wav.read_bytes(1))
                            total_size -= 1
                    else:
                        wav.skip_bytes(chunk_size)
                        total_size -= chunk_size
                        if (chunk_size % 2):
                            wav.skip_bytes(1)
                            total_size -= 1

                    metadata.add_block(
                        Flac_APPLICATION(
                            application_id="riff",
                            data=chunk.data()))

                flac.update_metadata(metadata)

                return flac
            finally:
                wav.close()
        else:
            return cls.from_pcm(filename,
                                to_pcm_progress(WaveAudio(wave_filename),
                                                progress),
                                compression=compression)

    def has_foreign_aiff_chunks(self):
        """Returns True if the audio file contains non-audio AIFF chunks."""

        return 'aiff' in [
            block.application_id for block in
            self.get_metadata().get_blocks(Flac_APPLICATION.BLOCK_ID)]

    @classmethod
    def from_aiff(cls, filename, aiff_filename, compression=None,
                  progress=None):
        """Encodes a new AudioFile from an existing .aiff file.

        Takes a filename string, aiff_filename string
        of an existing AiffAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new FlacAudio object."""

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if (AiffAudio(aiff_filename).has_foreign_aiff_chunks()):
            flac = cls.from_pcm(filename,
                                to_pcm_progress(AiffAudio(aiff_filename),
                                                progress),
                                compression=compression)

            metadata = flac.get_metadata()

            aiff = file(aiff_filename, 'rb')
            try:
                aiff_header = aiff.read(12)

                metadata.add_block(
                    Flac_APPLICATION(application_id="aiff",
                                     data=aiff_header))

                total_size = AiffAudio.AIFF_HEADER.parse(
                    aiff_header).aiff_size - 4
                while (total_size > 0):
                    chunk_header = AiffAudio.CHUNK_HEADER.parse(aiff.read(8))
                    if (chunk_header.chunk_id != 'SSND'):
                        metadata.add_block(
                            Flac_APPLICATION(
                                application_id="aiff",
                                data=AiffAudio.CHUNK_HEADER.build(
                                    chunk_header) +
                                aiff.read(chunk_header.chunk_length)))
                    else:
                        metadata.add_block(
                                Flac_APPLICATION(
                                    application_id="aiff",
                                    data=AiffAudio.CHUNK_HEADER.build(
                                        chunk_header) + aiff.read(8)))
                        aiff.seek(chunk_header.chunk_length - 8, 1)
                    total_size -= (chunk_header.chunk_length + 8)

                flac.update_metadata(metadata)

                return flac
            finally:
                aiff.close()
        else:
            return cls.from_pcm(filename,
                                to_pcm_progress(AiffAudio(aiff_filename),
                                                progress),
                                compression=compression)

    def to_aiff(self, aiff_filename, progress=None):
        if (self.has_foreign_aiff_chunks()):
            AiffAudio.aiff_from_chunks(aiff_filename,
                                       self.aiff_chunks(progress))
        else:
            AiffAudio.from_pcm(aiff_filename, to_pcm_progress(self, progress))

    def aiff_chunks(self, progress=None):
        """Generate a set of (chunk_id, chunk_size, chunk_data) tuples

        These are for use by AiffAudio.from_chunks
        and are taken from "aiff" APPLICATION blocks
        or generated from our PCM data."""

        from struct import pack

        for application_block in [
            block.data for block in
            self.get_metadata().get_blocks(Flac_APPLICATION.BLOCK_ID)
            if (block.application_id == "aiff")]:
            (chunk_id, chunk_size, chunk_data) = (application_block[0:4],
                                                  application_block[4:8],
                                                  application_block[8:])
            if (chunk_id == 'FORM'):
                continue
            elif (chunk_id == 'SSND'):
                #FIXME - this is a lot more inefficient than it should be
                data = cStringIO.StringIO()
                data.write(chunk_data)
                pcm = to_pcm_progress(self, progress)
                transfer_framelist_data(pcm, data.write, True, True)
                pcm.close()
                if (len(data.getvalue()) % 2):
                    yield (chunk_id,
                           pack(">I", len(data.getvalue())),
                           data.getvalue() + chr(0))
                else:
                    yield (chunk_id,
                           pack(">I", len(data.getvalue())),
                           data.getvalue())
                data.close()
            else:
                yield (chunk_id, chunk_size, chunk_data)

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """Encodes a new AudioFile from existing AudioFile.

        Take a filename string, target class and optional compression string.
        Encodes a new AudioFile in the target class and returns
        the resulting object.
        May raise EncodingError if some problem occurs during encoding."""

        #If a FLAC has embedded RIFF *and* embedded AIFF chunks,
        #RIFF takes precedence if the target format supports both.
        #It's hard to envision a scenario in which that would happen.

        import tempfile

        if (target_class == WaveAudio):
            self.to_wave(target_path, progress=progress)
            return WaveAudio(target_path)
        elif (target_class == AiffAudio):
            self.to_aiff(target_path, progress=progress)
            return AiffAudio(target_path)
        elif (self.has_foreign_riff_chunks() and
              hasattr(target_class, "from_wave")):
            temp_wave = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                #we'll only log the second leg of conversion,
                #since that's likely to be the slower portion
                self.to_wave(temp_wave.name)
                return target_class.from_wave(target_path,
                                              temp_wave.name,
                                              compression,
                                              progress=progress)
            finally:
                temp_wave.close()
        elif (self.has_foreign_aiff_chunks() and
              hasattr(target_class, "from_aiff")):
            temp_aiff = tempfile.NamedTemporaryFile(suffix=".aiff")
            try:
                self.to_aiff(temp_aiff.name)
                return target_class.from_aiff(target_path,
                                              temp_aiff.name,
                                              compression,
                                              progress=progress)
            finally:
                temp_aiff.close()
        else:
            return target_class.from_pcm(target_path,
                                         to_pcm_progress(self, progress),
                                         compression)

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bitspersample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__total_frames__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__samplerate__

    def __read_streaminfo__(self):
        valid_header_types = frozenset(range(0, 6 + 1))
        f = file(self.filename, "rb")
        try:
            self.__stream_offset__ = ID3v2Comment.skip(f)
            f.read(4)

            from .bitstream import BitstreamReader

            reader = BitstreamReader(f, 0)

            stop = 0

            while (stop == 0):
                (stop, header_type, length) = reader.parse("1u 7u 24u")
                if (header_type not in valid_header_types):
                    raise InvalidFLAC(_("invalid header type"))
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
    def add_replay_gain(cls, filenames, progress=None):
        """Adds ReplayGain values to a list of filename strings.

        All the filenames must be of this AudioFile type.
        Raises ValueError if some problem occurs during ReplayGain application.
        """

        tracks = [track for track in open_files(filenames) if
                  isinstance(track, cls)]

        if (len(tracks) > 0):
            for (track,
                 track_gain,
                 track_peak,
                 album_gain,
                 album_peak) in calculate_replay_gain(tracks, progress):
                metadata = track.get_metadata()
                try:
                    comment = metadata.get_block(
                        Flac_VORBISCOMMENT.BLOCK_ID)
                except IndexError:
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
    def can_add_replay_gain(cls):
        """Returns True."""

        return True

    @classmethod
    def lossless_replay_gain(cls):
        """Returns True."""

        return True

    def replay_gain(self):
        """Returns a ReplayGain object of our ReplayGain values.

        Returns None if we have no values."""

        try:
            vorbis_metadata = self.get_metadata().get_block(
                Flac_VORBISCOMMENT.BLOCK_ID)
        except IndexError:
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
            try:
                from hashlib import md5
            except ImportError:
                from md5 import new as md5

            p = audiofile.to_pcm()
            m = md5()
            s = p.read(BUFFER_SIZE)
            while (len(s) > 0):
                m.update(s.to_bytes(False, True))
                s = p.read(BUFFER_SIZE)
            p.close()
            return m.digest() == self.__md5__
        else:
            return False

    def clean(self, fixes_performed, output_filename=None):
        """Cleans the file of known data and metadata problems.

        fixes_performed is a list-like object which is appended
        with Unicode strings of fixed problems

        output_filename is an optional filename of the fixed file
        if present, a new AudioFile is returned
        otherwise, only a dry-run is performed and no new file is written

        Raises IOError if unable to write the file or its metadata
        """

        if (output_filename is None):
            #dry run only

            input_f = open(self.filename, "rb")
            try:
                #remove ID3 tags from before and after FLAC stream
                stream_offset = ID3v2Comment.skip(input_f)
                if (stream_offset > 0):
                    fixes_performed.append(_(u"removed ID3v2 tag"))
                input_f.seek(-128, 2)
                if (input_f.read(3) == 'TAG'):
                    fixes_performed.append(_(u"removed ID3v1 tag"))

                #fix empty MD5SUM
                if (self.__md5__ == chr(0) * 16):
                    fixes_performed.append(_(u"populated empty MD5SUM"))

                #FLAC should always have metadata
                metadata = self.get_metadata()

                #fix missing WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                if ((self.channels() > 2) or (self.bits_per_sample() > 16)):
                    try:
                        if (u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" not in
                            metadata.get_block(
                                Flac_VORBISCOMMENT.BLOCK_ID).keys()):
                            fixes_performed.append(
                                _(u"added WAVEFORMATEXTENSIBLE_CHANNEL_MASK"))
                    except IndexError:
                        fixes_performed.append(
                            _(u"added WAVEFORMATEXTENSIBLE_CHANNEL_MASK"))

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

                stream_offset = ID3v2Comment.skip(input_f)
                if (stream_offset > 0):
                    fixes_performed.append(_(u"removed ID3v2 tag"))
                    stream_size -= stream_offset

                input_f.seek(-128, 2)
                if (input_f.read(3) == 'TAG'):
                    fixes_performed.append(_(u"removed ID3v1 tag"))
                    stream_size -= 128

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

                output_track = FlacAudio(output_filename)

                metadata = self.get_metadata()

                #fix empty MD5SUM
                if (self.__md5__ == chr(0) * 16):
                    from hashlib import md5
                    md5sum = md5()
                    transfer_framelist_data(
                        self.to_pcm(),
                        md5sum.update,
                        signed=True,
                        big_endian=False)
                    metadata.get_block(
                        Flac_STREAMINFO.BLOCK_ID).md5sum = md5sum.digest()
                    fixes_performed.append(_(u"populated empty MD5SUM"))

                #fix missing WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                if ((self.channels() > 2) or (self.bits_per_sample() > 16)):
                    try:
                        vorbis_comment = metadata.get_block(
                            Flac_VORBISCOMMENT.BLOCK_ID)
                    except IndexError:
                        vorbis_comment = Flac_VORBISCOMMENT(
                            [], u"Python Audio Tools %s" % (VERSION))

                    if (u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK" not in
                        vorbis_comment.keys()):
                        fixes_performed.append(
                            _(u"added WAVEFORMATEXTENSIBLE_CHANNEL_MASK"))
                        vorbis_comment[
                            u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = \
                            [u"0x%.4X" % (self.channel_mask())]

                        metadata.replace_blocks(Flac_VORBISCOMMENT.BLOCK_ID,
                                                [vorbis_comment])

                #fix remaining metadata problems
                #which automatically shifts STREAMINFO to the right place
                #(the message indicating the fix has already been output)
                output_track.update_metadata(metadata.clean(fixes_performed))

                return output_track
            finally:
                input_f.close()


#######################
#Ogg FLAC
#######################


class OggFlacMetaData(FlacMetaData):
    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or (isinstance(metadata, OggFlacMetaData))):
            return metadata
        elif (isinstance(metadata, FlacMetaData)):
            return cls(metadata.block_list)
        else:
            return cls([Flac_VORBISCOMMENT.converted(metadata)] +
                       [Flac_PICTURE.converted(image)
                        for image in metadata.images()])


    def __repr__(self):
        return ("OggFlacMetaData(%s)" % (repr(self.block_list)))


    @classmethod
    def parse(cls, reader):
        from . import read_ogg_packets

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

        block_list =[Flac_STREAMINFO(minimum_block_size=minimum_block_size,
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
            if (block_type == 1):   #PADDING
                block_list.append(Flac_PADDING.parse(packet, length))
            if (block_type == 2):   #APPLICATION
                block_list.append(Flac_APPLICATION.parse(packet, length))
            elif (block_type == 3): #SEEKTABLE
                block_list.append(Flac_SEEKTABLE.parse(packet, length / 18))
            elif (block_type == 4): #VORBIS_COMMENT
                block_list.append(Flac_VORBISCOMMENT.parse(packet))
            elif (block_type == 5): #CUESHEET
                block_list.append(Flac_CUESHEET.parse(packet))
            elif (block_type == 6): #PICTURE
                block_list.append(Flac_PICTURE.parse(packet))
            elif ((block_type >= 7) and (block_type <= 126)):
                raise ValueError(_(u"reserved metadata block type %d") %
                                 (block_type))
            elif (block_type == 127):
                raise ValueError(_(u"invalid metadata block type"))

        return cls(block_list)

    def build(self, oggwriter):
        """oggwriter is an OggStreamWriter-compatible object"""

        from .bitstream import BitstreamRecorder
        from .bitstream import format_size
        from . import iter_first,iter_last

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
            (0x7F, "FLAC", 1, 0, len(valid_blocks), "fLaC", 0,
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

        #pack remaining metadata blocks into as few pages as possible
        for (last_block, block) in iter_last(iter(valid_blocks)):

            packet.reset()
            if (not last_block):
                packet.build("1u 7u 24u", (0, block.BLOCK_ID, block.size()))
            else:
                packet.build("1u 7u 24u", (1, block.BLOCK_ID, block.size()))

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
    """A Free Lossless Audio Codec file inside an Ogg container."""

    SUFFIX = "oga"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str, range(0, 9)))
    COMPRESSION_DESCRIPTIONS = {"0": _(u"least amount of compresson, " +
                                       u"fastest compression speed"),
                                "8": _(u"most amount of compression, " +
                                       u"slowest compression speed")}
    BINARIES = ("flac",)

    METADATA_CLASS = OggFlacMetaData

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_frames__ = 0

        try:
            self.__read_streaminfo__()
        except IOError, msg:
            raise InvalidFLAC(str(msg))

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x21] == '\x7FFLAC')

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bitspersample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__total_frames__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__samplerate__

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        f = open(self.filename, "rb")
        try:
            from .bitstream import BitstreamReader

            return OggFlacMetaData.parse(BitstreamReader(f, 1))
        finally:
            f.close()

    def update_metadata(self, metadata):
        """Takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object.

        Raises IOError if unable to write the file.
        """

        if (not isinstance(metadata, OggFlacMetaData)):
            raise ValueError(_(u"metadata not from audio file"))

        #always overwrite Ogg FLAC with fresh metadata
        #
        #The trouble with Ogg FLAC padding is that Ogg header overhead
        #requires a variable amount of overhead bytes per Ogg page
        #which makes it very difficult to calculate how many
        #bytes to allocate to the PADDING packet.
        #We'd have to build a bunch of empty pages for padding
        #then go back and fill-in the initial padding page's length
        #field before re-checksumming it.

        import tempfile

        from .bitstream import BitstreamWriter
        from .bitstream import BitstreamRecorder
        from .bitstream import BitstreamAccumulator
        from .bitstream import BitstreamReader
        from . import OggStreamReader,OggStreamWriter

        new_file = tempfile.TemporaryFile()
        try:
            original_file = file(self.filename, 'rb')
            try:
                original_reader = BitstreamReader(original_file, 1)
                original_ogg = OggStreamReader(original_reader)

                new_writer = BitstreamWriter(new_file, 1)
                new_ogg = OggStreamWriter(new_writer,
                                          self.__serial_number__)

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
            finally:
                original_file.close()

            #copy temporary file data over our original file
            original_file = file(self.filename, "wb")
            try:
                new_file.seek(0, 0)
                transfer_data(new_file.read, original_file.write)
                new_file.close()
            finally:
                original_file.close()
        finally:
            new_file.close()

    def metadata_length(self):
        """Returns the length of all Ogg FLAC metadata blocks as an integer.

        This includes all Ogg page headers."""

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
                raise InvalidFLAC(_(u"invalid Ogg magic number"))
            if (version != 0):
                raise InvalidFLAC(_(u"invalid Ogg version"))

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
                raise InvalidFLAC(_(u"invalid packet byte"))
            if (ogg_signature != 'FLAC'):
                raise InvalidFLAC(_(u"invalid Ogg signature"))
            if (major_version != 1):
                raise InvalidFLAC(_(u"invalid major version"))
            if (minor_version != 0):
                raise InvalidFLAC(_(u"invalid minor version"))
            if (flac_signature != 'fLaC'):
                raise InvalidFLAC(_(u"invalid FLAC signature"))

            self.__channels__ += 1
            self.__bitspersample__ += 1
        finally:
            f.close()

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        from . import decoders

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
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new OggFlacAudio object."""

        SUBSTREAM_SAMPLE_RATES = frozenset([
                8000,  16000, 22050, 24000, 32000,
                44100, 48000, 96000])
        SUBSTREAM_BITS = frozenset([8, 12, 16, 20, 24])

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if ((pcmreader.sample_rate in SUBSTREAM_SAMPLE_RATES) and
            (pcmreader.bits_per_sample in SUBSTREAM_BITS)):
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
            raise UnsupportedChannelMask(filename,
                                         int(pcmreader.channel_mask))
        else:
            channel_mask = int(pcmreader.channel_mask)

        devnull = file(os.devnull, 'ab')

        sub = subprocess.Popen([BIN['flac']] + lax + \
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
            if (((pcmreader.channels > 2) or
                 (pcmreader.bits_per_sample > 16)) and
                (channel_mask != 0)):
                metadata = oggflac.get_metadata()
                metadata.vorbis_comment[
                    u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4X" % (channel_mask)]
                oggflac.set_metadata(metadata)
            return oggflac
        else:
            raise EncodingError(u"error encoding file with flac")

    def sub_pcm_tracks(self):
        """Yields a PCMReader object per cuesheet track.

        This currently does nothing since the FLAC reference
        decoder has limited support for Ogg FLAC.
        """

        return iter([])

    def verify(self, progress=None):
        """Verifies the current file for correctness.

        Returns True if the file is okay.
        Raises an InvalidFile with an error message if there is
        some problem with the file."""

        from audiotools import verify_ogg_stream

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
                return result
            except (IOError, ValueError), err:
                raise InvalidFLAC(str(err))
        finally:
            f.close()
