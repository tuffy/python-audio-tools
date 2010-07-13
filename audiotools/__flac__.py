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


from audiotools import (AudioFile, MetaData, InvalidFile, PCMReader,
                        Con, transfer_data, transfer_framelist_data,
                        subprocess, BIN, BUFFER_SIZE, cStringIO,
                        os, open_files, Image, sys, WaveAudio, ReplayGain,
                        ignore_sigint, sheet_to_unicode, EncodingError,
                        UnsupportedChannelMask, DecodingError, Messenger,
                        BufferedPCMReader, calculate_replay_gain, ChannelMask,
                        PCMReaderError)
from __vorbiscomment__ import *
from __id3__ import ID3v2Comment
from __vorbis__ import OggStreamReader, OggStreamWriter

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


class FlacMetaDataBlock:
    """A container for FLAC metadata blocks."""

    def __init__(self, type, data):
        """Initialized with a type integer and data binary string."""

        self.type = type
        self.data = data

    def build_block(self, last=0):
        """Returns the entire block as a string, including header.

        last is a bit indicating this is the last block before audio data.
        Raises FlacMetaDataBlockTooLarge if data is too large to fit
        in a single FLAC metadata block."""

        if (len(self.data) > (1 << 24)):
            raise FlacMetaDataBlockTooLarge()

        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=self.type,
                          block_length=len(self.data))) + self.data


class FlacMetaData(MetaData):
    """A container for a FLAC file's list of metadata blocks."""

    def __init__(self, blocks):
        """blocks is a list of plain FlacMetaDataBlock objects.

        These are converted internally into MetaData/ImageMetaData fields
        as needed, depending on the type.
        """

        #IMPORTANT!
        #Externally converted FlacMetaData likely won't have a valid STREAMINFO
        #so set_metadata() must override this value with the current
        #FLAC's streaminfo before setting the metadata blocks.
        self.__dict__['streaminfo'] = None

        #Don't use an external SEEKTABLE, either.
        self.__dict__['seektable'] = None

        self.__dict__['vorbis_comment'] = None
        self.__dict__['cuesheet'] = None
        self.__dict__['image_blocks'] = []
        self.__dict__['extra_blocks'] = []

        for block in blocks:
            #metadata block data cannot exceed 2^24 bits
            if (len(block.data) > (1 << 24)):
                continue

            if ((block.type == 0) and (self.streaminfo is None)):
                #only one STREAMINFO allowed
                self.__dict__['streaminfo'] = block
            elif ((block.type == 4) and (self.vorbis_comment is None)):
                #only one VORBIS_COMMENT allowed
                comments = {}

                comment_container = FlacVorbisComment.VORBIS_COMMENT.parse(
                    block.data)

                for comment in comment_container.value:
                    try:
                        key = comment[0:comment.index("=")].upper()
                        value = comment[comment.index("=") + 1:].decode(
                            'utf-8')

                        comments.setdefault(key, []).append(value)
                    except ValueError:
                        pass

                self.__dict__['vorbis_comment'] = FlacVorbisComment(
                    comments, comment_container.vendor_string)

            elif ((block.type == 5) and (self.cuesheet is None)):
                #only one CUESHEET allowed
                self.__dict__['cuesheet'] = FlacCueSheet(
                    FlacCueSheet.CUESHEET.parse(block.data),
                    FlacAudio.STREAMINFO.parse(
                        self.streaminfo.data).samplerate)
            elif ((block.type == 3) and (self.seektable is None)):
                #only one SEEKTABLE allowed
                self.__dict__['seektable'] = block
            elif (block.type == 6):
                #multiple PICTURE blocks are ok
                image = FlacAudio.PICTURE_COMMENT.parse(block.data)

                self.__dict__['image_blocks'].append(FlacPictureComment(
                    type=image.type,
                    mime_type=image.mime_type.decode('ascii', 'replace'),
                    description=image.description.decode('utf-8', 'replace'),
                    width=image.width,
                    height=image.height,
                    color_depth=image.color_depth,
                    color_count=image.color_count,
                    data=image.data))
            elif (block.type != 1):
                #everything but the padding is stored as extra
                self.__dict__['extra_blocks'].append(block)

        if (self.vorbis_comment is None):
            self.vorbis_comment = FlacVorbisComment({})

    def __comment_name__(self):
        return u'FLAC'

    def __comment_pairs__(self):
        return self.vorbis_comment.__comment_pairs__()

    def __unicode__(self):
        if (self.cuesheet is None):
            return MetaData.__unicode__(self)
        else:
            return u"%s%sCuesheet:\n%s" % (MetaData.__unicode__(self),
                                           os.linesep * 2,
                                           unicode(self.cuesheet))

    def __setattr__(self, key, value):
        # self.__dict__[key] = value
        # setattr(self.vorbis_comment, key, value)
        if (key in self.__FIELDS__):
            setattr(self.vorbis_comment, key, value)
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):
        if (key in self.__FIELDS__):
            return getattr(self.vorbis_comment, key)
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __delattr__(self, key):
        if (key in self.__FIELDS__):
            delattr(self.vorbis_comment, key)
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    @classmethod
    def converted(cls, metadata):
        """Takes a MetaData object and returns a FlacMetaData object."""

        if ((metadata is None) or (isinstance(metadata, FlacMetaData))):
            return metadata
        else:
            blocks = []
            try:
                blocks.append(FlacMetaDataBlock(
                        type=4,
                        data=FlacVorbisComment.converted(metadata).build()))
            except FlacMetaDataBlockTooLarge:
                pass

            for image in metadata.images():
                try:
                    blocks.append(FlacMetaDataBlock(
                            type=6,
                            data=FlacPictureComment.converted(image).build()))
                except FlacMetaDataBlockTooLarge:
                    pass

            return FlacMetaData(blocks)

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        self.vorbis_comment.merge(metadata)

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        self.__dict__['image_blocks'].append(
            FlacPictureComment.converted(image))

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        image_blocks = self.__dict__['image_blocks']

        if (image in image_blocks):
            image_blocks.pop(image_blocks.index(image))

    def images(self):
        """Returns a list of embedded Image objects."""

        return self.__dict__['image_blocks'][:]

    def metadata_blocks(self):
        """Yields all current blocks as FlacMetaDataBlock-compatible objects.

        Note that any padding block is not returned.
        """

        yield self.streaminfo
        yield self.vorbis_comment

        if (self.seektable is not None):
            yield self.seektable

        if (self.cuesheet is not None):
            yield self.cuesheet

        for image in self.images():
            yield image

        for extra in self.extra_blocks:
            yield extra

    def build(self, padding_size=4096):
        """Returns all of a FLAC file's metadata as a binary string.

        padding_size indicates the side of the PADDING block to append
        (not counting its 32 bit header).
        """

        built_blocks = []
        blocks = self.metadata_blocks()

        #STREAMINFO must always be first and is always a fixed size
        built_blocks.append(blocks.next().build_block())

        #then come the rest of the blocks in any order
        for block in blocks:
            try:
                built_blocks.append(block.build_block())
            except FlacMetaDataBlockTooLarge:
                if (isinstance(block, VorbisComment)):
                    #if VORBISCOMMENT is too large, substitute a blank one
                    #(this only happens when one pushes over 16MB(!) of text
                    # into a comment, which simply isn't going to happen
                    # accidentcally)
                    built_blocks.append(FlacVorbisComment(
                            vorbis_data={},
                            vendor_string=block.vendor_string).build_block())

        #finally, append a fresh PADDING block
        built_blocks.append(
            FlacMetaDataBlock(type=1,
                              data=chr(0) * padding_size).build_block(last=1))

        return "".join(built_blocks)

    @classmethod
    def supports_images(cls):
        """Returns True."""

        return True


class FlacVorbisComment(VorbisComment):
    """A slight variation of VorbisComment without the framing bit.

    Also includes a build_block() method for FlacMetaDataBlock
    compatiblity."""

    VORBIS_COMMENT = Con.Struct("vorbis_comment",
                                Con.PascalString(
            "vendor_string",
            length_field=Con.ULInt32("length")),
                                Con.PrefixedArray(
        length_field=Con.ULInt32("length"),
        subcon=Con.PascalString("value",
                                length_field=Con.ULInt32("length"))))

    def build_block(self, last=0):
        """Returns the entire block as a string, including header.

        last is a bit indicating this is the last block before audio data.
        Raises FlacMetaDataBlockTooLarge if data is too large to fit
        in a single FLAC metadata block."""

        block = self.build()
        if (len(block) > (1 << 24)):
            raise FlacMetaDataBlockTooLarge()

        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=4,
                          block_length=len(block))) + block

    @classmethod
    def converted(cls, metadata):
        """Converts metadata from another class to FlacVorbisComment."""

        if ((metadata is None) or (isinstance(metadata, FlacVorbisComment))):
            return metadata
        elif (isinstance(metadata, FlacMetaData)):
            return metadata.vorbis_comment
        elif (isinstance(metadata, VorbisComment)):
            return FlacVorbisComment(metadata, metadata.vendor_string)
        else:
            values = {}
            for key in cls.ATTRIBUTE_MAP.keys():
                if (key in cls.__INTEGER_FIELDS__):
                    if (getattr(metadata, key) != 0):
                        values[cls.ATTRIBUTE_MAP[key]] = \
                            [unicode(getattr(metadata, key))]
                elif (getattr(metadata, key) != u""):
                    values[cls.ATTRIBUTE_MAP[key]] = \
                        [unicode(getattr(metadata, key))]

            return FlacVorbisComment(values)


class FlacPictureComment(Image):
    """This is a container for FLAC's PICTURE metadata blocks."""

    def __init__(self, type, mime_type, description,
                 width, height, color_depth, color_count, data):
        """Initialization fields are as follows:

        type - an integer type whose values are:
               0 - front cover
               1 - back cover
               2 - leaflet page
               3 - media
               4 - other
        mime_type   - unicode string of the image's MIME type
        description - a unicode string
        width       - width of image, as integer number of pixels
        height      - height of image, as integer number of pixels
        color_depth - color depth of image (24 for JPEG, 8 for GIF, etc.)
        color_count - number of palette colors, or 0
        data        - plain string of the actual binary image data
        """

        Image.__init__(self,
                       data=data,
                       mime_type=mime_type,
                       width=width,
                       height=height,
                       color_depth=color_depth,
                       color_count=color_count,
                       description=description,
                       type={3: 0, 4: 1, 5: 2, 6: 3}.get(type, 4))
        self.flac_type = type

    @classmethod
    def converted(cls, image):
        """Converts an Image object to a FlacPictureComment."""

        return FlacPictureComment(
            type={0: 3, 1: 4, 2: 5, 3: 6}.get(image.type, 0),
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
                20: "Publisher/Studio logotype"}.get(self.flac_type, "Other")

    def __repr__(self):
        return ("FlacPictureComment(type=%s,mime_type=%s,description=%s," +
                "width=%s,height=%s,...)") % \
                (repr(self.flac_type), repr(self.mime_type),
                 repr(self.description),
                 repr(self.width), repr(self.height))

    def build(self):
        """Returns a PICTURE comment as a raw string.

        This does not include the 32 bit header."""

        if (len(self.data) > (1 << 24)):
            raise FlacMetaDataBlockTooLarge()

        return FlacAudio.PICTURE_COMMENT.build(
            Con.Container(type=self.flac_type,
                          mime_type=self.mime_type.encode('ascii'),
                          description=self.description.encode('utf-8'),
                          width=self.width,
                          height=self.height,
                          color_depth=self.color_depth,
                          color_count=self.color_count,
                          data=self.data))

    def build_block(self, last=0):
        """Returns the entire block as a string, including header.

        last is a bit indicating this is the last block before audio data.
        Raises FlacMetaDataBlockTooLarge if data is too large to fit
        in a single FLAC metadata block."""

        block = self.build()
        if (len(block) > (1 << 24)):
            #why check both here and in build()?
            #because while the raw image data itself might be small enough
            #additional info like "description" could push it over
            #the metadata block size limit
            raise FlacMetaDataBlockTooLarge()

        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=6,
                          block_length=len(block))) + block


class FlacCueSheet:
    """A container for FLAC CUESHEET metadata blocks."""

    CUESHEET = Con.Struct(
        "flac_cuesheet",
        Con.String("catalog_number", 128),
        Con.UBInt64("lead_in_samples"),
        Con.Embed(Con.BitStruct("flags",
                                Con.Flag("is_cd"),
                                Con.Padding(7))),  # reserved
        Con.Padding(258),  # reserved
        Con.PrefixedArray(
            length_field=Con.Byte("count"),
            subcon=Con.Struct("cuesheet_tracks",
                              Con.UBInt64("track_offset"),
                              Con.Byte("track_number"),
                              Con.String("ISRC", 12),
                              Con.Embed(Con.BitStruct("sub_flags",
                                                      Con.Flag("non_audio"),
                                                      Con.Flag("pre_emphasis"),
                                                      Con.Padding(6))),
                              Con.Padding(13),
                              Con.PrefixedArray(
                    length_field=Con.Byte("count"),
                    subcon=Con.Struct("cuesheet_track_index",
                                      Con.UBInt64("offset"),
                                      Con.Byte("point_number"),
                                      Con.Padding(3))))))  # reserved

    def __init__(self, container, sample_rate=44100):
        """container is a Container object returned by CUESHEET.parse()."""

        self.type = 5
        self.container = container
        self.sample_rate = sample_rate

    def build_block(self, last=0):
        """Returns the entire block as a string, including header.

        last is a bit indicating this is the last block before audio data."""

        #the largest possible CUESHEET cannot exceed the metadata block size
        #so no need to test for it
        block = self.CUESHEET.build(self.container)

        return FlacAudio.METADATA_BLOCK_HEADER.build(
            Con.Container(last_block=last,
                          block_type=5,
                          block_length=len(block))) + block

    @classmethod
    def converted(cls, sheet, total_frames, sample_rate=44100):
        """Converts a cuesheet compatible object to FlacCueSheet objects.

        A total_frames integer (in PCM frames) is also required.
        """

        #number is the track number integer
        #ISRC is a 12 byte string, or None
        #indexes is a list of indexes()-compatible index points
        #(i.e. given incrementally as CD frames)
        #returns a Container
        def track_container(number, ISRC, indexes):
            if (ISRC is None):
                ISRC = chr(0) * 12

            if (len(indexes) == 1):
                base_number = 1
            else:
                base_number = 0

            return Con.Container(
                track_offset=indexes[0] * sample_rate / 75,
                track_number=number,
                ISRC=ISRC,
                non_audio=False,
                pre_emphasis=False,  # FIXME, check for this
                cuesheet_track_index=[Con.Container(
                        offset=((index - indexes[0]) * sample_rate / 75),
                        point_number=point_number + base_number)
                                      for (point_number, index) in
                                      enumerate(indexes)])

        catalog_number = sheet.catalog()
        if (catalog_number is None):
            catalog_number = ""

        ISRCs = sheet.ISRCs()

        return cls(Con.Container(
                catalog_number=catalog_number + \
                    (chr(0) * (128 - len(catalog_number))),
                lead_in_samples=sample_rate * 2,
                is_cd=True,
                cuesheet_tracks=[track_container(i + 1,
                                                 ISRCs.get(i + 1, None),
                                                 indexes)
                                 for (i, indexes) in
                                 enumerate(sheet.indexes())] + \
                                 [Con.Container(track_offset=total_frames,
                                                track_number=170,
                                                ISRC=chr(0) * 12,
                                                non_audio=False,
                                                pre_emphasis=False,
                                                cuesheet_track_index=[])]),
                   sample_rate)

    def catalog(self):
        """Returns the cuesheet's catalog number as a plain string."""

        if (len(self.container.catalog_number.rstrip(chr(0))) > 0):
            return self.container.catalog_number.rstrip(chr(0))
        else:
            return None

    def ISRCs(self):
        """Returns a list of ISRC values as plain strings."""

        return dict([(track.track_number, track.ISRC) for track in
                     self.container.cuesheet_tracks
                     if ((track.track_number != 170) and
                         (len(track.ISRC.strip(chr(0))) > 0))])

    def indexes(self):
        """Returns a list of (start, end) integer tuples."""

        return [tuple([(index.offset + track.track_offset) * 75 / \
                           self.sample_rate
                       for index in
                       sorted(track.cuesheet_track_index,
                              lambda i1, i2: cmp(i1.point_number,
                                                 i2.point_number))])
                for track in
                sorted(self.container.cuesheet_tracks,
                       lambda t1, t2: cmp(t1.track_number,
                                          t2.track_number))
                if (track.track_number != 170)]

    def pcm_lengths(self, total_length):
        """Returns a list of PCM lengths for all cuesheet audio tracks.

        Note that the total length variable is only for compatibility.
        It is not necessary for FlacCueSheets.
        """
        if (len(self.container.cuesheet_tracks) > 0):
            return [(current.track_offset +
                     max([i.offset for i in
                          current.cuesheet_track_index] + [0])) -
                    ((previous.track_offset +
                      max([i.offset for i in
                           previous.cuesheet_track_index] + [0])))
                    for (previous, current) in
                    zip(self.container.cuesheet_tracks,
                        self.container.cuesheet_tracks[1:])]
        else:
            return []

    def __unicode__(self):
        return sheet_to_unicode(self, None)


class FlacSeektable:

    #FIXME - should start using this

    SEEKTABLE = Con.GreedyRepeater(
            Con.Struct("seekpoint",
                       Con.UBInt64("first_sample_number"),
                       Con.UBInt64("first_byte_offset"),
                       Con.UBInt16("sample_count")))


class FlacAudio(AudioFile):
    """A Free Lossless Audio Codec file."""

    SUFFIX = "flac"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str, range(0, 9)))

    METADATA_BLOCK_HEADER = Con.BitStruct("metadata_block_header",
                                          Con.Bit("last_block"),
                                          Con.Bits("block_type", 7),
                                          Con.Bits("block_length", 24))

    STREAMINFO = Con.Struct("flac_streaminfo",
                                 Con.UBInt16("minimum_blocksize"),
                                 Con.UBInt16("maximum_blocksize"),
                                 Con.Embed(Con.BitStruct("flags",
                                   Con.Bits("minimum_framesize", 24),
                                   Con.Bits("maximum_framesize", 24),
                                   Con.Bits("samplerate", 20),
                                   Con.Bits("channels", 3),
                                   Con.Bits("bits_per_sample", 5),
                                   Con.Bits("total_samples", 36))),
                                 Con.StrictRepeater(16, Con.Byte("md5")))

    PICTURE_COMMENT = Con.Struct("picture_comment",
                                 Con.UBInt32("type"),
                                 Con.PascalString(
            "mime_type",
            length_field=Con.UBInt32("mime_type_length")),
                                 Con.PascalString(
            "description",
            length_field=Con.UBInt32("description_length")),
                                 Con.UBInt32("width"),
                                 Con.UBInt32("height"),
                                 Con.UBInt32("color_depth"),
                                 Con.UBInt32("color_count"),
                                 Con.PascalString(
            "data",
            length_field=Con.UBInt32("data_length")))

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
        except (Con.FieldError, Con.ArrayError):
            raise InvalidFLAC("invalid STREAMINFO block")

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        if (file.read(4) == 'fLaC'):
            block_ids = list(cls.__block_ids__(file))
            if ((len(block_ids) == 0) or (0 not in block_ids)):
                messenger = Messenger("audiotools", None)
                messenger.error(_(u"STREAMINFO block not found"))
            elif (block_ids[0] != 0):
                messenger = Messenger("audiotools", None)
                messenger.error(_(u"STREAMINFO not first metadata block.  " +
                                  u"Please fix with tracklint(1)"))
            else:
                return True
        else:
            #I've seen FLAC files tagged with ID3v2 comments.
            #Though the official flac binaries grudgingly accept these,
            #such tags are unnecessary and outside the specification
            #so I will encourage people to remove them.

            file.seek(-4, 1)
            ID3v2Comment.skip(file)
            if (file.read(4) == 'fLaC'):
                messenger = Messenger("audiotools", None)
                messenger.error(_(u"ID3v2 tag found at start of FLAC file.  " +
                                  u"Please remove with tracklint(1)"))
            return False

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        if (self.channels() <= 2):
            return ChannelMask.from_channels(self.channels())
        else:
            vorbis_comment = self.get_metadata().vorbis_comment
            if ("WAVEFORMATEXTENSIBLE_CHANNEL_MASK" in vorbis_comment.keys()):
                try:
                    return ChannelMask(
                        int(vorbis_comment[
                                "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"][0], 16))
                except ValueError:
                    pass

            #if there is no WAVEFORMATEXTENSIBLE_CHANNEL_MASK
            #or it's not an integer, use FLAC's default mask based on channels
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

    @classmethod
    def __help_output__(cls):
        help_data = cStringIO.StringIO()
        sub = subprocess.Popen([BIN['flac'], '--help'],
                               stdout=subprocess.PIPE)
        transfer_data(sub.stdout.read, help_data.write)
        sub.wait()
        return help_data.getvalue()

    @classmethod
    def supports_foreign_riff_chunks(cls):
        """Returns True."""

        return True

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        f = file(self.filename, 'rb')
        try:
            if (f.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            blocks = []

            while (True):
                header = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(f)
                blocks.append(FlacMetaDataBlock(
                    type=header.block_type,
                    data=f.read(header.block_length)))
                if (header.last_block == 1):
                    break

            return FlacMetaData(blocks)
        finally:
            f.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        metadata = FlacMetaData.converted(metadata)

        if (metadata is None):
            return
        old_metadata = self.get_metadata()

        #if metadata's STREAMINFO block matches old_metadata's STREAMINFO
        #we're almost certainly setting a modified version
        #of our original metadata
        #in that case, we skip the metadata block porting
        #and assume higher-level routines know what they're doing
        if ((old_metadata.streaminfo is not None) and
            (metadata.streaminfo is not None) and
            (old_metadata.streaminfo.data == metadata.streaminfo.data)):
            #do nothing
            pass
        else:
            #port over the old STREAMINFO and SEEKTABLE blocks
            old_streaminfo = old_metadata.streaminfo
            old_seektable = old_metadata.seektable
            metadata.streaminfo = old_streaminfo
            if (old_seektable is not None):
                metadata.seektable = old_seektable

            #grab "WAVEFORMATEXTENSIBLE_CHANNEL_MASK" from existing file
            #(if any)
            if ((self.channels() > 2) or (self.bits_per_sample() > 16)):
                metadata.vorbis_comment[
                    "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4x" % (int(self.channel_mask()))]

            #APPLICATION blocks should stay with the existing file (if any)
            metadata.extra_blocks = [block for block in metadata.extra_blocks
                                     if (block.type != 2)]

            for block in old_metadata.extra_blocks:
                if (block.type == 2):
                    metadata.extra_blocks.append(block)

        #always grab "vendor_string" from the existing file
        vendor_string = old_metadata.vorbis_comment.vendor_string
        metadata.vorbis_comment.vendor_string = vendor_string

        minimum_metadata_length = len(metadata.build(padding_size=0)) + 4
        current_metadata_length = self.metadata_length()

        if ((minimum_metadata_length <= current_metadata_length) and
            ((current_metadata_length - minimum_metadata_length) <
             (4096 * 2))):
            #if the FLAC file's metadata + padding is large enough
            #to accomodate the new chunk of metadata,
            #simply overwrite the beginning of the file

            stream = file(self.filename, 'r+b')
            stream.write('fLaC')
            stream.write(metadata.build(
                    padding_size=current_metadata_length - \
                        minimum_metadata_length))
            stream.close()
        else:
            #if the new metadata is too large to fit in the current file,
            #or if the padding gets unnecessarily large,
            #rewrite the entire file using a temporary file for storage

            import tempfile

            stream = file(self.filename, 'rb')

            if (stream.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            block = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(stream)
            while (block.last_block == 0):
                stream.seek(block.block_length, 1)
                block = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(stream)
            stream.seek(block.block_length, 1)

            file_data = tempfile.TemporaryFile()
            transfer_data(stream.read, file_data.write)
            file_data.seek(0, 0)

            stream = file(self.filename, 'wb')
            stream.write('fLaC')
            stream.write(metadata.build())
            transfer_data(file_data.read, stream.write)
            file_data.close()
            stream.close()

    def metadata_length(self):
        """Returns the length of all FLAC metadata blocks as an integer.

        This includes the 4 byte "fLaC" file header."""

        f = file(self.filename, 'rb')
        try:
            if (f.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            header = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(f)
            f.seek(header.block_length, 1)
            while (header.last_block == 0):
                header = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(f)
                f.seek(header.block_length, 1)
            return f.tell()
        finally:
            f.close()

    def delete_metadata(self):
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

        self.set_metadata(MetaData())

    @classmethod
    def __read_flac_header__(cls, flacfile):
        p = FlacAudio.METADATA_BLOCK_HEADER.parse(flacfile.read(4))
        return (p.last_block, p.block_type, p.block_length)

    @classmethod
    def __block_ids__(cls, flacfile):
        p = Con.Container(last_block=False,
                          block_type=None,
                          block_length=0)

        while (not p.last_block):
            p = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(flacfile)
            yield p.block_type
            flacfile.seek(p.block_length, 1)

    def set_cuesheet(self, cuesheet):
        """Imports cuesheet data from a Cuesheet-compatible object.

        This are objects with catalog(), ISRCs(), indexes(), and pcm_lengths()
        methods.  Raises IOError if an error occurs setting the cuesheet."""

        if (cuesheet is None):
            return

        metadata = self.get_metadata()
        if (metadata is None):
            metadata = FlacMetaData.converted(MetaData())

        metadata.cuesheet = FlacCueSheet.converted(
            cuesheet, self.total_frames(), self.sample_rate())
        self.set_metadata(metadata)

    def get_cuesheet(self):
        """Returns the embedded Cuesheet-compatible object, or None.

        Raises IOError if a problem occurs when reading the file."""

        metadata = self.get_metadata()
        if (metadata is not None):
            return metadata.cuesheet
        else:
            return None

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        from . import decoders

        try:
            return decoders.FlacDecoder(self.filename,
                                        self.channel_mask())
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
    def from_pcm(cls, filename, pcmreader, compression="8"):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new FlacAudio object."""

        from . import encoders

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

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

        if (int(pcmreader.channel_mask) == 0):
            if (pcmreader.channels <= 6):
                channel_mask = {1: 0x0004,
                                2: 0x0003,
                                3: 0x0007,
                                4: 0x0033,
                                5: 0x0037,
                                6: 0x003F}[pcmreader.channels]
            elif (pcmreader.channels <= 8):
                channel_mask = 0
            else:
                raise UnsupportedChannelMask()
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
            raise UnsupportedChannelMask()
        else:
            channel_mask = int(pcmreader.channel_mask)

        try:
            encoders.encode_flac(filename,
                                 pcmreader=BufferedPCMReader(pcmreader),
                                 **encoding_options)
            flac = FlacAudio(filename)

            if (((pcmreader.channels > 2) or
                 (pcmreader.bits_per_sample > 16)) and
                (channel_mask != 0)):
                metadata = flac.get_metadata()
                metadata.vorbis_comment[
                    "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4x" % (channel_mask)]
                flac.set_metadata(metadata)

            return flac
        except IOError, msg:
            raise EncodingError(str(msg))

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        return 'riff' in [block.data[0:4] for block in
                          self.get_metadata().extra_blocks
                          if block.type == 2]

    #generates a set of (chunk_id,chunk_data) tuples
    #for use by WaveAudio.from_chunks
    #these chunks are taken from "riff" APPLICATION blocks
    #or generated from our PCM data
    def riff_wave_chunks(self):
        """Generate a set of (chunk_id,chunk_data tuples)

        These are for use by WaveAudio.from_chunks
        and are taken from "riff" APPLICATION blocks
        or generated from our PCM data."""

        for application_block in [block.data for block in
                                  self.get_metadata().extra_blocks
                                  if (block.data.startswith("riff"))]:
            (chunk_id, chunk_data) = (application_block[4:8],
                                      application_block[12:])
            if (chunk_id == 'RIFF'):
                continue
            elif (chunk_id == 'data'):
                #FIXME - this is a lot more inefficient than it should be
                data = cStringIO.StringIO()
                pcm = self.to_pcm()
                if (self.bits_per_sample > 8):
                    transfer_framelist_data(pcm, data.write, True, False)
                else:
                    transfer_framelist_data(pcm, data.write, False, False)
                pcm.close()
                yield (chunk_id, data.getvalue())
                data.close()
            else:
                yield (chunk_id, chunk_data)

    def to_wave(self, wave_filename):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        if (self.has_foreign_riff_chunks()):
            WaveAudio.wave_from_chunks(wave_filename,
                                       self.riff_wave_chunks())
        else:
            WaveAudio.from_pcm(wave_filename, self.to_pcm())

    @classmethod
    def from_wave(cls, filename, wave_filename, compression="8"):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new FlacAudio object."""

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if (cls.supports_foreign_riff_chunks() and
            WaveAudio(wave_filename).has_foreign_riff_chunks()):
            flac = cls.from_pcm(filename,
                                WaveAudio(wave_filename).to_pcm(),
                                compression=compression)

            metadata = flac.get_metadata()

            wav = file(wave_filename, 'rb')
            try:
                wav_header = wav.read(12)

                metadata.extra_blocks.append(
                    FlacMetaDataBlock(2, "riff" + wav_header))

                total_size = WaveAudio.WAVE_HEADER.parse(
                    wav_header).wave_size - 4
                while (total_size > 0):
                    chunk_header = WaveAudio.CHUNK_HEADER.parse(wav.read(8))
                    if (chunk_header.chunk_id != 'data'):
                        metadata.extra_blocks.append(
                            FlacMetaDataBlock(2, "riff" +
                                              WaveAudio.CHUNK_HEADER.build(
                                    chunk_header) +
                                              wav.read(
                                    chunk_header.chunk_length)))
                    else:
                        metadata.extra_blocks.append(
                            FlacMetaDataBlock(2, "riff" +
                                              WaveAudio.CHUNK_HEADER.build(
                                    chunk_header)))
                        wav.seek(chunk_header.chunk_length, 1)
                    total_size -= (chunk_header.chunk_length + 8)

                flac.set_metadata(metadata)

                return flac
            finally:
                wav.close()
        else:
            return cls.from_pcm(filename,
                                WaveAudio(wave_filename).to_pcm(),
                                compression=compression)

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
        f = file(self.filename, "rb")
        if (f.read(4) != "fLaC"):
            raise InvalidFLAC(_(u"Not a FLAC file"))

        (stop, header_type, length) = FlacAudio.__read_flac_header__(f)
        if (header_type != 0):
            raise InvalidFLAC(_(u"STREAMINFO not first metadata block"))

        p = FlacAudio.STREAMINFO.parse(f.read(length))

        md5sum = "".join(["%.2X" % (x) for x in p.md5]).lower()

        self.__samplerate__ = p.samplerate
        self.__channels__ = p.channels + 1
        self.__bitspersample__ = p.bits_per_sample + 1
        self.__total_frames__ = p.total_samples
        self.__md5__ = "".join([chr(c) for c in p.md5])
        f.close()

    @classmethod
    def add_replay_gain(cls, filenames):
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
                 album_peak) in calculate_replay_gain(tracks):
                metadata = track.get_metadata()
                if (hasattr(metadata, "vorbis_comment")):
                    comment = metadata.vorbis_comment
                    comment["REPLAYGAIN_TRACK_GAIN"] = [
                        "%1.2f dB" % (track_gain)]
                    comment["REPLAYGAIN_TRACK_PEAK"] = [
                        "%1.8f" % (track_peak)]
                    comment["REPLAYGAIN_ALBUM_GAIN"] = [
                        "%1.2f dB" % (album_gain)]
                    comment["REPLAYGAIN_ALBUM_PEAK"] = ["%1.8f" % (album_peak)]
                    comment["REPLAYGAIN_REFERENCE_LOUDNESS"] = [u"89.0 dB"]
                    track.set_metadata(metadata)

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

        vorbis_metadata = self.get_metadata().vorbis_comment

        if (set(['REPLAYGAIN_TRACK_PEAK', 'REPLAYGAIN_TRACK_GAIN',
                 'REPLAYGAIN_ALBUM_PEAK', 'REPLAYGAIN_ALBUM_GAIN']).issubset(
                vorbis_metadata.keys())):  # we have ReplayGain data
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

    def sub_pcm_tracks(self):
        """Yields a PCMReader object per cuesheet track."""

        metadata = self.get_metadata()
        if ((metadata is not None) and (metadata.cuesheet is not None)):
            indexes = [(track.track_number,
                        [index.point_number for index in
                         sorted(track.cuesheet_track_index,
                                lambda i1, i2: cmp(i1.point_number,
                                                   i2.point_number))])
                       for track in
                       metadata.cuesheet.container.cuesheet_tracks]

            if (len(indexes) > 0):
                for ((cur_tracknum, cur_indexes),
                     (next_tracknum, next_indexes)) in zip(indexes,
                                                           indexes[1:]):
                    if (next_tracknum != 170):
                        cuepoint = "%s.%s-%s.%s" % (cur_tracknum,
                                                    max(cur_indexes),
                                                    next_tracknum,
                                                    max(next_indexes))
                    else:
                        cuepoint = "%s.%s-%s.0" % (cur_tracknum,
                                                   max(cur_indexes),
                                                   next_tracknum)

                    sub = subprocess.Popen([BIN['flac'], "-s", "-d", "-c",
                                            "--force-raw-format",
                                            "--endian=little",
                                            "--sign=signed",
                                            "--cue=%s" % (cuepoint),
                                            self.filename],
                                           stdout=subprocess.PIPE)

                    yield PCMReader(sub.stdout,
                                    sample_rate=self.__samplerate__,
                                    channels=self.__channels__,
                                    bits_per_sample=self.__bitspersample__,
                                    process=sub)

#######################
#Ogg FLAC
#######################


class OggFlacAudio(FlacAudio):
    """A Free Lossless Audio Codec file inside an Ogg container."""

    SUFFIX = "oga"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple(map(str, range(0, 9)))
    BINARIES = ("flac",)

    OGGFLAC_STREAMINFO = Con.Struct('oggflac_streaminfo',
                                    Con.Const(Con.Byte('packet_byte'),
                                              0x7F),
                                    Con.Const(Con.String('signature', 4),
                                              'FLAC'),
                                    Con.Byte('major_version'),
                                    Con.Byte('minor_version'),
                                    Con.UBInt16('header_packets'),
                                    Con.Const(Con.String('flac_signature', 4),
                                              'fLaC'),
                                    Con.Embed(
        FlacAudio.METADATA_BLOCK_HEADER),
                                    Con.Embed(
        FlacAudio.STREAMINFO))

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x21] == '\x7FFLAC')

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        stream = OggStreamReader(file(self.filename, "rb"))
        try:
            packets = stream.packets()

            blocks = [FlacMetaDataBlock(
                type=0,
                data=FlacAudio.STREAMINFO.build(
                  self.OGGFLAC_STREAMINFO.parse(packets.next())))]

            while (True):
                block = packets.next()
                header = FlacAudio.METADATA_BLOCK_HEADER.parse(
                    block[0:FlacAudio.METADATA_BLOCK_HEADER.sizeof()])
                blocks.append(
                    FlacMetaDataBlock(
                      type=header.block_type,
                      data=block[FlacAudio.METADATA_BLOCK_HEADER.sizeof():]))
                if (header.last_block == 1):
                    break

            return FlacMetaData(blocks)
        finally:
            stream.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        import tempfile

        comment = FlacMetaData.converted(metadata)

        #port over the old STREAMINFO and SEEKTABLE blocks
        if (comment is None):
            return
        old_metadata = self.get_metadata()
        old_streaminfo = old_metadata.streaminfo
        old_seektable = old_metadata.seektable
        comment.streaminfo = old_streaminfo
        if (old_seektable is not None):
            comment.seektable = old_seektable

        #grab "vendor_string" from the existing file
        vendor_string = old_metadata.vorbis_comment.vendor_string
        comment.vorbis_comment.vendor_string = vendor_string

        #grab "WAVEFORMATEXTENSIBLE_CHANNEL_MASK" from existing file
        #(if any)
        if ((self.channels() > 2) or (self.bits_per_sample() > 16)):
                comment.vorbis_comment[
                    "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4x" % (int(self.channel_mask()))]

        reader = OggStreamReader(file(self.filename, 'rb'))
        new_file = tempfile.TemporaryFile()
        writer = OggStreamWriter(new_file)

        #grab the serial number from the old file's current header
        pages = reader.pages()
        (header_page, header_data) = pages.next()
        serial_number = header_page.bitstream_serial_number
        del(pages)

        #skip the metadata packets in the old file
        packets = reader.packets(from_beginning=False)
        while (True):
            block = packets.next()
            header = FlacAudio.METADATA_BLOCK_HEADER.parse(
                block[0:FlacAudio.METADATA_BLOCK_HEADER.sizeof()])
            if (header.last_block == 1):
                break

        del(packets)

        #write our new comment blocks to the new file
        blocks = list(comment.metadata_blocks())

        #oggflac_streaminfo is a Container for STREAMINFO data
        #Ogg FLAC STREAMINFO differs from FLAC STREAMINFO,
        #so some fields need to be filled-in
        oggflac_streaminfo = FlacAudio.STREAMINFO.parse(blocks.pop(0).data)
        oggflac_streaminfo.packet_byte = 0x7F
        oggflac_streaminfo.signature = 'FLAC'
        oggflac_streaminfo.major_version = 0x1
        oggflac_streaminfo.minor_version = 0x0
        oggflac_streaminfo.header_packets = len(blocks) + 1  # +1 for padding
        oggflac_streaminfo.flac_signature = 'fLaC'
        oggflac_streaminfo.last_block = 0
        oggflac_streaminfo.block_type = 0
        oggflac_streaminfo.block_length = FlacAudio.STREAMINFO.sizeof()

        sequence_number = 0
        for (page_header, page_data) in OggStreamWriter.build_pages(
            0, serial_number, sequence_number,
            OggFlacAudio.OGGFLAC_STREAMINFO.build(oggflac_streaminfo),
            header_type=0x2):
            writer.write_page(page_header, page_data)
            sequence_number += 1

        #the non-STREAMINFO blocks are the same as FLAC, so write them out
        for block in blocks:
            try:
                for (page_header, page_data) in OggStreamWriter.build_pages(
                    0, serial_number, sequence_number,
                    block.build_block()):
                    writer.write_page(page_header, page_data)
                    sequence_number += 1
            except FlacMetaDataBlockTooLarge:
                if (isinstance(block, VorbisComment)):
                    #VORBISCOMMENT can't be skipped, so build an empty one
                    for (page_header,
                         page_data) in OggStreamWriter.build_pages(
                        0, serial_number, sequence_number,
                        FlacVorbisComment(
                            vorbis_data={},
                            vendor_string=block.vendor_string).build_block()):
                        writer.write_page(page_header, page_data)
                        sequence_number += 1
                else:
                    pass

        #finally, write out a padding block
        for (page_header, page_data) in OggStreamWriter.build_pages(
            0, serial_number, sequence_number,
            FlacMetaDataBlock(type=1,
                              data=chr(0) * 4096).build_block(last=1)):
            writer.write_page(page_header, page_data)
            sequence_number += 1

        #now write the rest of the old pages to the new file,
        #re-sequenced and re-checksummed
        for (page, data) in reader.pages(from_beginning=False):
            page.page_sequence_number = sequence_number
            page.checksum = OggStreamReader.calculate_ogg_checksum(page, data)
            writer.write_page(page, data)
            sequence_number += 1

        reader.close()

        #re-write the file with our new data in "new_file"
        f = file(self.filename, "wb")
        new_file.seek(0, 0)
        transfer_data(new_file.read, f.write)
        new_file.close()
        f.close()
        writer.close()

    def metadata_length(self):
        """Returns None."""

        return None

    def __read_streaminfo__(self):
        stream = OggStreamReader(file(self.filename, "rb"))
        try:
            packets = stream.packets()
            try:
                header = self.OGGFLAC_STREAMINFO.parse(packets.next())
            except Con.ConstError:
                raise InvalidFLAC(_(u'Invalid Ogg FLAC streaminfo'))
            except StopIteration:
                raise InvalidFLAC(_(u'Invalid Ogg FLAC streaminfo'))

            self.__samplerate__ = header.samplerate
            self.__channels__ = header.channels + 1
            self.__bitspersample__ = header.bits_per_sample + 1
            self.__total_frames__ = header.total_samples
            self.__header_packets__ = header.header_packets

            self.__md5__ = "".join([chr(c) for c in header.md5])

            del(packets)
        finally:
            stream.close()

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        sub = subprocess.Popen([BIN['flac'], "-s", "--ogg", "-d", "-c",
                                "--force-raw-format",
                                "--endian=little",
                                "--sign=signed",
                                self.filename],
                               stdout=subprocess.PIPE,
                               stderr=file(os.devnull, 'ab'))
        return PCMReader(sub.stdout,
                         sample_rate=self.__samplerate__,
                         channels=self.__channels__,
                         bits_per_sample=self.__bitspersample__,
                         channel_mask=int(self.channel_mask()),
                         process=sub,
                         signed=True,
                         big_endian=False)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="8"):
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

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if ((pcmreader.sample_rate in SUBSTREAM_SAMPLE_RATES) and
            (pcmreader.bits_per_sample in SUBSTREAM_BITS)):
            lax = []
        else:
            lax = ["--lax"]

        if (int(pcmreader.channel_mask) == 0):
            if (pcmreader.channels <= 6):
                channel_mask = {1: 0x0004,
                                2: 0x0003,
                                3: 0x0007,
                                4: 0x0033,
                                5: 0x0037,
                                6: 0x003F}[pcmreader.channels]
            elif (pcmreader.channels <= 8):
                channel_mask = 0
            else:
                raise UnsupportedChannelMask()
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
            raise UnsupportedChannelMask()
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

        transfer_framelist_data(pcmreader, sub.stdin.write)
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
                    "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4x" % (channel_mask)]
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

    @classmethod
    def supports_foreign_riff_chunks(cls):
        """Returns False."""

        #the --keep-foreign-metadata flag fails
        #when used with --ogg
        return False
