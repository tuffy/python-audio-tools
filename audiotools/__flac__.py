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
                        Con, transfer_data, transfer_framelist_data,
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

class FlacMetaData(MetaData):
    """A class for managing a native FLAC's metadata."""

    def __init__(self, streaminfo=None, applications=None, seektable=None,
                 vorbis_comment=None, cuesheet=None, pictures=None):

        #IMPORTANT!
        #Externally converted FlacMetaData likely won't have a valid STREAMINFO
        #so set_metadata() must override this value with the current
        #FLAC's streaminfo before setting the metadata blocks.
        self.__dict__["streaminfo"] = streaminfo

        if (applications is None):
            self.__dict__["applications"] = []
        else:
            self.__dict__["applications"] = applications

        #Don't use an external SEEKTABLE, either.
        self.__dict__["seektable"] = seektable

        self.__dict__["vorbis_comment"] = vorbis_comment

        self.__dict__["cuesheet"] = cuesheet

        if (pictures is None):
            self.__dict__["pictures"] = []
        else:
            self.__dict__["pictures"] = pictures

    def __comment_name__(self):
        return u'FLAC'

    def __comment_pairs__(self):
        if (self.vorbis_comment is not None):
            return self.vorbis_comment.__comment_pairs__()
        else:
            return []

    def __unicode__(self):
        if (self.cuesheet is None):
            return MetaData.__unicode__(self)
        else:
            return u"%s%sCuesheet:\n%s" % (MetaData.__unicode__(self),
                                           os.linesep * 2,
                                           unicode(self.cuesheet))

    def __setattr__(self, key, value):
        if (key in self.__FIELDS__):
            if (self.vorbis_comment is None):
                self.vorbis_comment = Flac_VORBISCOMMENT(
                    u"Python Audio Tools %s" % (VERSION), [])

            setattr(self.vorbis_comment, key, value)
        else:
            self.__dict__[key] = value

    def __getattr__(self, key):
        if (key in self.__FIELDS__):
            if (self.vorbis_comment is not None):
                return getattr(self.vorbis_comment, key)
            elif (key in self.__INTEGER_FIELDS__):
                return 0
            else:
                return u""
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __delattr__(self, key):
        if (key in self.__FIELDS__):
            if (self.vorbis_comment is not None):
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
            return cls(vorbis_comment=Flac_VORBISCOMMENT.converted(metadata),
                       pictures=[Flac_PICTURE.converted(image)
                                 for image in metadata.images()])

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        self.vorbis_comment.merge(metadata)
        if (len(self.images()) == 0):
            for image in metadata.images():
                self.add_image(image)

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        self.__dict__['pictures'].append(Flac_PICTURE.converted(image))

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        self.__dict__['pictures'] = [
            cur_image for cur_image in self.__dict__['pictures']
            if (cur_image != image)]

    def images(self):
        """Returns a list of embedded Image objects."""

        return self.__dict__['pictures'][:]

    @classmethod
    def supports_images(cls):
        """Returns True."""

        return True

    def clean(self, fixes_performed):
        """Returns a new FlacMetaData object that's been cleaned of problems.

        Any fixes performed are appended to fixes_performed as Unicode."""

        #recursively clean up the text fields in FlacVorbisComment
        if (self.vorbis_comment is not None):
            vorbis_comment = self.vorbis_comment.clean(fixes_performed)
        else:
            vorbis_comment = None

        #recursively clean up any image blocks
        pictures = [image.clean(fixes_performed)
                    for image in self.pictures]

        return self.__class__(streaminfo=self.streaminfo,
                              applications=self.applications,
                              seektable=self.seektable,
                              vorbis_comment=vorbis_comment,
                              cuesheet=self.cuesheet,
                              pictures=pictures)


    def __repr__(self):
        return ("FlacMetaData(%s)" %
                (",".join(["%s=%s" % (key, getattr(self, key))
                           for key in ["streaminfo",
                                       "applications",
                                       "seektable",
                                       "vorbis_comment",
                                       "cuesheet",
                                       "pictures"]])))
    @classmethod
    def parse(cls, reader):
        streaminfo = None
        applications = []
        seektable = None
        vorbis_comment = None
        cuesheet = None
        pictures = []

        (last, block_type, block_length) = reader.parse("1u7u24u")

        while (not last):
            if (block_type == 0):   #STREAMINFO
                if (streaminfo is None):
                    streaminfo = Flac_STREAMINFO.parse(
                        reader.substream(block_length))
                else:
                    raise ValueError(
                        _(u"only 1 STREAMINFO allowed in metadata"))
            elif (block_type == 1): #PADDING
                reader.skip(block_length * 8)
            elif (block_type == 2): #APPLICATION
                applications.append(Flac_APPLIACTION.parse(
                        reader.substream(block_length), block_length))
            elif (block_type == 3): #SEEKTABLE
                if (seektable is None):
                    seektable = Flac_SEEKTABLE.parse(
                        reader.substream(block_length), block_length / 18)
                else:
                    raise ValueError(_(u"only 1 SEEKTABLE allowed in metadata"))
            elif (block_type == 4): #VORBIS_COMMENT
                if (vorbis_comment is None):
                    vorbis_comment = Flac_VORBISCOMMENT.parse(
                        reader.substream(block_length))
                else:
                    raise ValueError(
                        _(u"only 1 VORBISCOMMENT allowed in metadata"))
            elif (block_type == 5): #CUESHEET
                if (cuesheet is None):
                    cuesheet = Flac_CUESHEET.parse(
                        reader.substream(block_length))
                else:
                    raise ValueError(_(u"only 1 CUESHEET allowed in metadata"))
            elif (block_type == 6): #PICTURE
                pictures.append(Flac_PICTURE.parse(
                        reader.substream(block_length)))
            elif ((block_type >= 7) and (block_type <= 126)):
                raise ValueError(_(u"reserved metadata block type %d") %
                                 (block_type))
            else:
                raise ValueError(_(u"invalid metadata block type"))

            (last, block_type, block_length) = reader.parse("1u7u24u")

        return cls(streaminfo=streaminfo,
                   applications=applications,
                   seektable=seektable,
                   vorbis_comment=vorbis_comment,
                   cuesheet=cuesheet,
                   pictures=pictures)

    def blocks(self):
        if (self.streaminfo is not None):
            yield self.streaminfo
        for application in self.applications:
            yield self.application
        if (self.seektable is not None):
            yield self.seektable
        if (self.vorbis_comment is not None):
            yield self.vorbis_comment
        if (self.cuesheet is not None):
            yield self.cuesheet
        for picture in self.pictures:
            yield picture

    def build(self, writer, padding_bytes):
        from .encoders import BitstreamRecorder

        for block in self.blocks():
            block_data = BitstreamRecorder(0)
            block.build(block_data)
            if (block_data.bytes() < 2 ** 24):
                #skip oversized blocks altogether
                writer.build("1u7u24u", (0, block.BLOCK_ID, block_data.bytes()))
                block_data.copy(writer)

        writer.build("1u7u24u%dp" % (padding_bytes * 8),
                     (1, 1, padding_bytes))


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

class Flac_VORBISCOMMENT(VorbisComment):
    BLOCK_ID = 4

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to a VorbisComment object."""

        if ((metadata is None) or (isinstance(metadata, Flac_VORBISCOMMENT))):
            return metadata
        elif (isinstance(metadata, FlacMetaData)):
            return metadata.vorbis_comment
        elif (isinstance(metadata, VorbisComment)):
            return cls(metadata, metadata.vendor_string)
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

            return cls(values)

    @classmethod
    def parse(cls, reader):
        reader.set_endianness(1)
        vendor_string = reader.read_bytes(reader.read(32)).decode('utf-8')
        comment_strings = {}
        for (key, value) in [comment_string.split(u"=", 1) for comment_string in
                             [reader.read_bytes(reader.read(32)).decode('utf-8')
                              for i in xrange(reader.read(32))]
                             if u"=" in comment_string]:
            comment_strings.setdefault(key, []).append(value)

        return cls(comment_strings, vendor_string)

    def build(self, writer):
        writer.set_endianness(1)
        vendor_string = self.vendor_string.encode('utf-8')
        writer.build("32u%db" % (len(vendor_string)),
                     (len(vendor_string), vendor_string))
        writer.write(32, sum(map(len, self.values())))
        for (key, values) in self.items():
            for value in values:
                comment = (u"%s=%s" % (key.upper(), value)).encode('utf-8')
                writer.build("32u%db" % (len(comment)), (len(comment), comment))

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
        return "Flac_APPLICATION(%s, %s)" % (self.application_id, self.data)

    @classmethod
    def parse(cls, reader, block_length):
        raise NotImplementedError() #FIXME

    def build(self, writer):
        raise NotImplementedError() #FIXME

class Flac_SEEKTABLE:
    BLOCK_ID = 3

    def __init__(self, seekpoints):
        self.seekpoints = seekpoints

    def __repr__(self):
        return "Flac_SEEKTABLE(%s)" % (repr(self.seekpoints))

    @classmethod
    def parse(cls, reader, total_seekpoints):
        return cls([tuple(reader.parse("64U64U16u"))
                    for i in xrange(total_seekpoints)])

    def build(self, writer):
        for seekpoint in self.seekpoints:
            writer.build("64U64U16u", seekpoint)

class Flac_CUESHEET:
    BLOCK_ID = 5

    def __init__(self, catalog_number, lead_in_samples, is_cdda, tracks):
        self.catalog_number = catalog_number
        self.lead_in_samples = lead_in_samples
        self.is_cdda = is_cdda
        self.tracks = tracks

    def __repr__(self):
        return ("Flac_CUESHEET(%s)" %
                ",".join(["%s=%s" % (key, repr(getattr(self, key)))
                          for key in ["catalog_number",
                                      "lead_in_samples",
                                      "is_cdda",
                                      "tracks"]]))

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

    @classmethod
    def converted(cls, sheet, total_frames, sample_rate=44100):
        """Converts a cuesheet compatible object to FlacCueSheet objects.

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

    @classmethod
    def parse(cls, reader):
        (offset, number) = reader.parse("64U8u24p")

        return cls(offset, number)

    def build(self, writer):
        writer.build("64U8u24p", (self.offset, self.number))


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
        self.__stream_offset__ = 0

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
            #proper FLAC file with no junk at the beginning
            try:
                block_ids = list(cls.__block_ids__(file))
            except Con.FieldError:
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
                    except Con.FieldError:
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

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        f = file(self.filename, 'rb')
        try:
            f.seek(self.__stream_offset__, 0)
            if (f.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            from .decoders import BitstreamReader

            return FlacMetaData.parse(BitstreamReader(f, 0))
        finally:
            f.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        from .encoders import BitstreamWriter
        from .encoders import BitstreamRecorder
        from .encoders import BitstreamAccumulator

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
            (old_metadata.streaminfo == metadata.streaminfo)):
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
            metadata.applications = [block for block in metadata.applications
                                     if (block.type != 2)]

        #always grab "vendor_string" from the existing file - if present
        if ((old_metadata.vorbis_comment is not None) and
            (metadata.vorbis_comment is not None)):
            vendor_string = old_metadata.vorbis_comment.vendor_string
            metadata.vorbis_comment.vendor_string = vendor_string

        new_metadata = BitstreamAccumulator(0)
        metadata.build(new_metadata, 0)
        minimum_metadata_length = new_metadata.bytes() + 4
        current_metadata_length = self.metadata_length()

        if ((minimum_metadata_length <= current_metadata_length) and
            ((current_metadata_length - minimum_metadata_length)
             < (4096 * 2)) and
            (self.__stream_offset__ == 0)):
            #if the FLAC file's metadata + padding is large enough
            #to accomodate the new chunk of metadata,
            #simply overwrite the beginning of the file

            stream = file(self.filename, 'r+b')
            stream.write('fLaC')
            metadata.build(BitstreamWriter(stream, 0),
                           current_metadata_length -
                           minimum_metadata_length)
            stream.close()
        else:
            #if the new metadata is too large to fit in the current file,
            #or if the padding gets unnecessarily large,
            #rewrite the entire file using a temporary file for storage

            import tempfile

            stream = file(self.filename, 'rb')
            stream.seek(self.__stream_offset__, 0)

            if (stream.read(4) != 'fLaC'):
                raise InvalidFLAC(_(u'Invalid FLAC file'))

            #skip the existing metadata blocks
            #FIXME - remove Construct-based parsing
            block = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(stream)
            while (block.last_block == 0):
                stream.seek(block.block_length, 1)
                block = FlacAudio.METADATA_BLOCK_HEADER.parse_stream(stream)
            stream.seek(block.block_length, 1)

            #write the remaining data stream to a temp file
            file_data = tempfile.TemporaryFile()
            transfer_data(stream.read, file_data.write)
            file_data.seek(0, 0)

            #finally, rebuild our file using new metadata and old stream
            stream = file(self.filename, 'wb')
            stream.write('fLaC')
            metadata.build(BitstreamWriter(stream, 0), 4096)
            transfer_data(file_data.read, stream.write)
            file_data.close()
            stream.close()

    def metadata_length(self):
        """Returns the length of all FLAC metadata blocks as an integer.

        This includes the 4 byte "fLaC" file header."""

        #FIXME - remove Construct-based parsing

        f = file(self.filename, 'rb')
        try:
            f.seek(self.__stream_offset__, 0)
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

        metadata.cuesheet = Flac_CUESHEET.converted(
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

            metadata.seektable = Flac_SEEKTABLE(seekpoints)

            #if channels or bps is too high,
            #automatically generate and add channel mask
            if (((pcmreader.channels > 2) or
                 (pcmreader.bits_per_sample > 16)) and
                (channel_mask != 0)):
                metadata.vorbis_comment[
                    "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4x" % (channel_mask)]

            flac.set_metadata(metadata)

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

        return 'riff' in [block.application_id for block in
                          self.get_metadata().applications]

    def riff_wave_chunks(self, progress=None):
        """Generate a set of (chunk_id,chunk_data tuples)

        These are for use by WaveAudio.from_chunks
        and are taken from "riff" APPLICATION blocks
        or generated from our PCM data."""

        for application_block in [block.data for block in
                                  self.get_metadata().applications
                                  if (block.application_id == "riff")]:
            (chunk_id, chunk_data) = (application_block[0:4],
                                      application_block[8:])
            if (chunk_id == 'RIFF'):
                continue
            elif (chunk_id == 'data'):
                #FIXME - this is a lot more inefficient than it should be
                data = cStringIO.StringIO()
                pcm = to_pcm_progress(self, progress)
                if (self.bits_per_sample > 8):
                    transfer_framelist_data(pcm, data.write, True, False)
                else:
                    transfer_framelist_data(pcm, data.write, False, False)
                pcm.close()
                yield (chunk_id, data.getvalue())
                data.close()
            else:
                yield (chunk_id, chunk_data)

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

            wav = file(wave_filename, 'rb')
            try:
                wav_header = wav.read(12)

                metadata.applications.append(
                    Flac_APPLICATION(application_id="riff",
                                     data=wav_header))

                total_size = WaveAudio.WAVE_HEADER.parse(
                    wav_header).wave_size - 4
                while (total_size > 0):
                    chunk_header = WaveAudio.CHUNK_HEADER.parse(wav.read(8))
                    if (chunk_header.chunk_id != 'data'):
                        metadata.applications.append(
                            Flac_APPLICATION(
                                application_id="riff",
                                data=WaveAudio.CHUNK_HEADER.build(
                                    chunk_header) +
                                wav.read(
                                    chunk_header.chunk_length)))
                    else:
                        metadata.applications.append(
                            Flac_APPLICATION(
                                application_id="riff",
                                data=WaveAudio.CHUNK_HEADER.build(
                                    chunk_header)))
                        wav.seek(chunk_header.chunk_length, 1)
                    total_size -= (chunk_header.chunk_length + 8)

                flac.set_metadata(metadata)

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

        return 'aiff' in [block.application_id for block in
                          self.get_metadata().applications]

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

                metadata.applications.append(
                    Flac_APPLICATION(application_id="aiff",
                                     data=aiff_header))

                total_size = AiffAudio.AIFF_HEADER.parse(
                    aiff_header).aiff_size - 4
                while (total_size > 0):
                    chunk_header = AiffAudio.CHUNK_HEADER.parse(aiff.read(8))
                    if (chunk_header.chunk_id != 'SSND'):
                        metadata.applications.append(
                            Flac_APPLICATION(
                                application_id="aiff",
                                data=AiffAudio.CHUNK_HEADER.build(
                                    chunk_header) +
                                aiff.read(chunk_header.chunk_length)))
                    else:
                        metadata.applications.append(
                                Flac_APPLICATION(
                                    application_id="aiff",
                                    data=AiffAudio.CHUNK_HEADER.build(
                                        chunk_header) + aiff.read(8)))
                        aiff.seek(chunk_header.chunk_length - 8, 1)
                    total_size -= (chunk_header.chunk_length + 8)

                flac.set_metadata(metadata)

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
        """Generate a set of (chunk_id,chunk_data tuples)

        These are for use by AiffAudio.from_chunks
        and are taken from "aiff" APPLICATION blocks
        or generated from our PCM data."""

        for application_block in [block.data for block in
                                  self.get_metadata().applications
                                  if (block.application_id == "aiff")]:
            (chunk_id, chunk_data) = (application_block[0:4],
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
                yield (chunk_id, data.getvalue())
                data.close()
            else:
                yield (chunk_id, chunk_data)

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
        f = file(self.filename, "rb")
        self.__stream_offset__ = ID3v2Comment.skip(f)
        f.read(4)

        (stop, header_type, length) = (False, None, 0)
        while (not stop):
            (stop, header_type, length) = \
                FlacAudio.__read_flac_header__(f)
            if (header_type == 0):
                p = self.STREAMINFO.parse(f.read(length))

                md5sum = "".join(["%.2X" % (x) for x in p.md5]).lower()

                self.__samplerate__ = p.samplerate
                self.__channels__ = p.channels + 1
                self.__bitspersample__ = p.bits_per_sample + 1
                self.__total_frames__ = p.total_samples
                self.__md5__ = "".join([chr(c) for c in p.md5])
                break
            else:
                f.seek(length, 1)
        f.close()

    def seektable(self, pcm_frames):
        """Returns a new FlacSeektable block from this file's data."""

        from bisect import bisect_right

        def seekpoints(reader, metadata_length):
            total_samples = 0

            for frame in analyze_frames(reader):
                yield (total_samples, frame['offset'] - metadata_length,
                       frame['block_size'])
                total_samples += frame['block_size']

        all_frames = dict([(point[0], (point[1], point[2]))
                           for point in seekpoints(self.to_pcm(),
                                                   self.metadata_length())])
        sample_offsets = all_frames.keys()
        sample_offsets.sort()

        seekpoints = []
        for pcm_frame in xrange(0, self.total_frames(), pcm_frames):
            flac_frame = bisect_right(sample_offsets, pcm_frame) - 1
            seekpoints.append(
                FlacSeekpoint(
                    sample_number=sample_offsets[flac_frame],
                    byte_offset=all_frames[sample_offsets[flac_frame]][0],
                    frame_samples=all_frames[sample_offsets[flac_frame]][1]))

        return FlacSeektable(seekpoints)

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

                #reorder metadata blocks such that STREAMINFO is first
                input_f.seek(stream_offset, 0)
                input_f.read(4)
                if (list(FlacAudio.__block_ids__(input_f))[0] != 0):
                    fixes_performed.append(
                        _(u"moved STREAMINFO to first block"))

                #fix any remaining metadata problems
                metadata = self.get_metadata()
                if (metadata is not None):
                    metadata.clean(fixes_performed)

                #fix empty MD5SUM
                if (self.__md5__ == chr(0) * 16):
                    fixes_performed.append(_(u"populated empty MD5SUM"))
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

                #reorder metadata blocks such that STREAMINFO is first
                input_f.seek(stream_offset, 0)
                input_f.read(4)
                if (list(FlacAudio.__block_ids__(input_f))[0] != 0):
                    fixes_performed.append(
                        _(u"moved STREAMINFO to first block"))

                #fix remaining metadata problems
                #which automatically shifts STREAMINFO to the right place
                #(the message indicating the fix has already been output)
                metadata = self.get_metadata()
                if (metadata is not None):
                    output_track.set_metadata(metadata.clean(fixes_performed))

                #fix empty MD5SUM
                #once the ID3 tags have been removed
                #and the STREAMINFO block moved to the first
                #which ensures the MD5SUM field is at a consistent place
                if (self.__md5__ == chr(0) * 16):
                    from hashlib import md5
                    md5sum = md5()
                    transfer_framelist_data(
                        self.to_pcm(),
                        md5sum.update,
                        signed=True,
                        big_endian=False)
                    output_f = open(output_filename, "r+b")
                    try:
                        output_f.seek(4 + 4 + 18)
                        output_f.write(md5sum.digest())
                    finally:
                        output_f.close()
                    fixes_performed.append(_(u"populated empty MD5SUM"))

                return output_track
            finally:
                input_f.close()


#######################
#Ogg FLAC
#######################


class OggFlacMetaData(FlacMetaData):
    @classmethod
    def converted(cls, metadata):
        raise NotImplementedError()

    def __repr__(self):
        return ("OggFlacMetaData(%s)" %
                (",".join(["%s=%s" % (key, getattr(self, key))
                           for key in ["streaminfo",
                                       "applications",
                                       "seektable",
                                       "vorbis_comment",
                                       "cuesheet",
                                       "pictures"]])))


    @classmethod
    def parse(cls, reader):
        streaminfo = None
        applications = []
        seektable = None
        vorbis_comment = None
        cuesheet = None
        pictures = []

        packets = read_ogg_packets(reader)

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
         md5sum) = packets.next().parse(
            "8u 4b 8u 8u 16u 4b 8u 24u 16u 16u 24u 24u 20u 3u 5u 36U 16b")

        streaminfo = Flac_STREAMINFO(minimum_block_size=minimum_block_size,
                                     maximum_block_size=maximum_block_size,
                                     minimum_frame_size=minimum_frame_size,
                                     maximum_frame_size=maximum_frame_size,
                                     sample_rate=sample_rate,
                                     channels=channels + 1,
                                     bits_per_sample=bits_per_sample + 1,
                                     total_samples=total_samples,
                                     md5sum=md5sum)

        for (i, packet) in zip(range(header_packets), packets):
            (block_type, length) = packet.parse("1p 7u 24u")
            if (block_type == 2):   #APPLICATION
                applications.append(
                    Flac_APPLICATION.parse(packet, block_length))
            elif (block_type == 3): #SEEKTABLE
                if (seektable is None):
                    seektable = Flac_SEEKTABLE.parse(packet, block_length / 18)
                else:
                    raise ValueError(_(u"only 1 SEEKTABLE allowed in metadata"))
            elif (block_type == 4): #VORBIS_COMMENT
                if (vorbis_comment is None):
                    vorbis_comment = Flac_VORBISCOMMENT.parse(packet)
                else:
                    raise ValueError(
                        _(u"only 1 VORBISCOMMENT allowed in metadata"))
            elif (block_type == 5): #CUESHEET
                if (cuesheet is None):
                    cuesheet = Flac_CUESHEET.parse(packet)
                else:
                    raise ValueError(_(u"only 1 CUESHEET allowed in metadata"))
            elif (block_type == 6): #PICTURE
                pictures.append(Flac_PICTURE.parse(packet))
            elif ((block_type >= 7) and (block_type <= 126)):
                raise ValueError(_(u"reserved metadata block type %d") %
                                 (block_type))
            elif (block_type == 127):
                raise ValueError(_(u"invalid metadata block type"))



        return cls(streaminfo=streaminfo,
                   applications=applications,
                   seektable=seektable,
                   vorbis_comment=vorbis_comment,
                   cuesheet=cuesheet,
                   pictures=pictures)


    def build(self, writer, padding_bytes):
        from .encoders import BitstreamRecorder

        #build a bunch of Ogg pages from our internal blocks

        raise NotImplementedError()

class __Counter__:
    def __init__(self):
        self.value = 0

    def count_byte(self, i):
        self.value += 1

    def __int__(self):
        return self.value

def read_ogg_packets(reader):
    from .decoders import Substream

    header_type = 0

    while (not (header_type & 0x4)):
        (magic_number,
         version,
         header_type,
         granule_position,
         serial_number,
         page_sequence_number,
         checksum,
         segment_count) = reader.parse("4b 8u 8u 64S 32u 32u 32u 8u")
        packet = Substream(0)
        for segment_length in [reader.read(8) for i in xrange(segment_count)]:
            reader.substream_append(packet, segment_length)
            if (segment_length != 255):
                yield packet
                packet = Substream(0)

class OggFlacAudio(AudioFile):
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

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        f = open(self.filename, "rb")
        try:
            from .decoders import BitstreamReader

            return OggFlacMetaData.parse(BitstreamReader(f, 1))
        finally:
            f.close()

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

    def delete_metadata(self):
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

        self.set_metadata(MetaData())

    def metadata_length(self):
        """Returns the length of all Ogg FLAC metadata blocks as an integer.

        This includes all Ogg page headers."""

        from .decoders import BitstreamReader

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
        from .decoders import BitstreamReader

        f = open(self.filename, "rb")
        try:
            ogg_reader = BitstreamReader(f, 1)
            (magic_number,
             version,
             header_type,
             granule_position,
             serial_number,
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
                    "WAVEFORMATEXTENSIBLE_CHANNEL_MASK"] = [
                    u"0x%.4x" % (channel_mask)]
                oggflac.set_metadata(metadata)
            return oggflac
        else:
            raise EncodingError(u"error encoding file with flac")

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
