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

from audiotools import (AudioFile, InvalidFile)
from .vorbis import (VorbisAudio, VorbisChannelMask)
from .vorbiscomment import VorbisComment


class InvalidOpus(InvalidFile):
    pass


#######################
#Vorbis File
#######################

class OpusAudio(VorbisAudio):
    """an Opus file"""

    SUFFIX = "opus"
    NAME = "opus"
    DESCRIPTION = u"Opus Audio Codec"
    DEFAULT_COMPRESSION = "10"
    COMPRESSION_MODES = tuple(map(str, range(0, 11)))
    COMPRESSION_DESCRIPTIONS = {"0": u"lowest quality, fastest encode",
                                "10": u"best quality, slowest encode"}
    BINARIES = ("opusenc", "opusdec")

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        self.__channels__ = 0
        self.__channel_mask__ = 0

        #get channel count and channel mask from first packet
        from .bitstream import BitstreamReader
        try:
            f = open(filename, "rb")
            try:
                ogg_reader = BitstreamReader(f, 1)
                (magic_number,
                 version,
                 header_type,
                 granule_position,
                 self.__serial_number__,
                 page_sequence_number,
                 checksum,
                 segment_count) = ogg_reader.parse(
                     "4b 8u 8u 64S 32u 32u 32u 8u")

                if (magic_number != 'OggS'):
                    from .text import ERR_OGG_INVALID_MAGIC_NUMBER
                    raise InvalidFLAC(ERR_OGG_INVALID_MAGIC_NUMBER)
                if (version != 0):
                    from .text import ERR_OGG_INVALID_VERSION
                    raise InvalidFLAC(ERR_OGG_INVALID_VERSION)

                segment_length = ogg_reader.read(8)

                (opushead,
                 version,
                 self.__channels__,
                 pre_skip,
                 input_sample_rate,
                 output_gain,
                 mapping_family) = ogg_reader.parse(
                     "8b 8u 8u 16u 32u 16s 8u")

                if (opushead != "OpusHead"):
                    from .text import ERR_OPUS_INVALID_TYPE
                    raise InvalidOpus(ERR_OPUS_INVALID_TYPE)
                if (version != 1):
                    from .text import ERR_OPUS_INVALID_VERSION
                    raise InvalidOpus(ERR_OPUS_INVALID_VERSION)
                if (self.__channels__ == 0):
                    from .text import ERR_OPUS_INVALID_CHANNELS
                    raise InvalidOpus(ERR_OPUS_INVALID_CHANNELS)

                #FIXME - assign channel mask from mapping family
                if (mapping_family == 0):
                    if (self.__channels__ == 1):
                        self.__channel_mask__ = VorbisChannelMask(0x4)
                    elif (self.__channels__ == 2):
                        self.__channel_mask__ = VorbisChannelMask(0x3)
                    else:
                        self.__channel_mask__ = VorbisChannelMask(0)
                else:
                    (stream_count,
                     coupled_stream_count) = ogg_reader.parse("8u 8u")
                    if (self.__channels__ !=
                        ((coupled_stream_count * 2) +
                         (stream_count - coupled_stream_count))):
                        from .text import ERR_OPUS_INVALID_CHANNELS
                        raise InvalidOpus(ERR_OPUS_INVALID_CHANNELS)
                    channel_mapping = [ogg_reader.read(8)
                                       for i in xrange(self.__channels__)]
            finally:
                f.close()
        except IOError, msg:
            raise InvalidOpus(str(msg))

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        from .bitstream import BitstreamReader
        from .bitstream import BitstreamRecorder
        from .bitstream import BitstreamWriter
        from .ogg import OggStreamWriter
        from .ogg import OggStreamReader
        from .ogg import read_ogg_packets_data
        from . import iter_first
        from .vorbiscomment import VorbisComment

        if (metadata is None):
            return

        if (not isinstance(metadata, OpusTags)):
            from .text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        original_reader = BitstreamReader(open(self.filename, "rb"), 1)
        original_ogg = OggStreamReader(original_reader)
        original_serial_number = original_ogg.serial_number
        original_packets = read_ogg_packets_data(original_reader)

        #save the current file's identification page/packet
        #(the ID packet is always fixed size, and fits in one page)
        identification_page = original_ogg.read_page()

        #discard the current file's comment packet
        original_packets.next()

        #save all the subsequent Ogg pages
        data_pages = list(original_ogg.pages())

        del(original_ogg)
        del(original_packets)
        original_reader.close()

        updated_writer = BitstreamWriter(open(self.filename, "wb"), 1)
        updated_ogg = OggStreamWriter(updated_writer, original_serial_number)

        #write the identification packet in its own page
        updated_ogg.write_page(*identification_page)

        #write the new comment packet in its own page(s)
        comment_writer = BitstreamRecorder(1)
        comment_writer.write_bytes("OpusTags")
        vendor_string = metadata.vendor_string.encode('utf-8')
        comment_writer.build("32u %db" % (len(vendor_string)),
                             (len(vendor_string), vendor_string))
        comment_writer.write(32, len(metadata.comment_strings))
        for comment_string in metadata.comment_strings:
            comment_string = comment_string.encode('utf-8')
            comment_writer.build("32u %db" % (len(comment_string)),
                                 (len(comment_string), comment_string))

        for (first_page, segments) in iter_first(
            updated_ogg.segments_to_pages(
                updated_ogg.packet_to_segments(comment_writer.data()))):
            updated_ogg.write_page(0, segments, 0 if first_page else 1, 0, 0)

        #write the subsequent Ogg pages
        for page in data_pages:
            updated_ogg.write_page(*page)

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return False

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        if (metadata is not None):
            metadata = OpusTags.converted(metadata)

            old_metadata = self.get_metadata()

            #port vendor string from old metadata to new metadata
            metadata.vendor_string = old_metadata.vendor_string

            #remove REPLAYGAIN_* tags from new metadata (if any)
            for key in [u"REPLAYGAIN_TRACK_GAIN",
                        u"REPLAYGAIN_TRACK_PEAK",
                        u"REPLAYGAIN_ALBUM_GAIN",
                        u"REPLAYGAIN_ALBUM_PEAK",
                        u"REPLAYGAIN_REFERENCE_LOUDNESS"]:
                try:
                    metadata[key] = old_metadata[key]
                except KeyError:
                    metadata[key] = []

            #port "ENCODER" tag from old metadata to new metadata
            if (u"ENCODER" in old_metadata):
                metadata[u"ENCODER"] = old_metadata[u"ENCODER"]

            self.update_metadata(metadata)

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from .bitstream import BitstreamReader
        from .ogg import read_ogg_packets
        from .vorbiscomment import VorbisComment

        packets = read_ogg_packets(
            BitstreamReader(open(self.filename, "rb"), 1))

        identification = packets.next()
        comment = packets.next()

        if (comment.read_bytes(8) != "OpusTags"):
            return None
        else:
            vendor_string = \
                comment.read_bytes(comment.read(32)).decode('utf-8')
            comment_strings = [
                comment.read_bytes(comment.read(32)).decode('utf-8')
                for i in xrange(comment.read(32))]
            return OpusTags(comment_strings, vendor_string)

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from . import MetaData

        #the comment packet is required,
        #so simply zero out its contents
        self.set_metadata(MetaData())

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        from .bitstream import BitstreamReader

        pcm_samples = 0
        end_of_stream = 0
        try:
            ogg_stream = BitstreamReader(file(self.filename, "rb"), 1)
            while (end_of_stream == 0):
                (magic_number,
                 version,
                 end_of_stream,
                 granule_position,
                 page_segment_count) = ogg_stream.parse(
                     "4b 8u 1p 1p 1u 5p 64S 32p 32p 32p 8u")
                ogg_stream.skip_bytes(sum([ogg_stream.read(8) for i in
                                           xrange(page_segment_count)]))

                if ((magic_number != "OggS") or (version != 0)):
                    return 0
                if (granule_position >= 0):
                    pcm_samples = granule_position

            ogg_stream.close()
            return pcm_samples
        except IOError:
            return 0

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return 48000

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        from . import PCMReader
        from . import BIN
        import subprocess
        import os

        sub = subprocess.Popen([BIN["opusdec"], "--quiet",
                                "--rate", str(48000),
                                self.filename, "-"],
                               stdout=subprocess.PIPE,
                               stderr=file(os.devnull, "a"))

        pcmreader = PCMReader(sub.stdout,
                              sample_rate=self.sample_rate(),
                              channels=self.channels(),
                              channel_mask=int(self.channel_mask()),
                              bits_per_sample=self.bits_per_sample(),
                              process=sub)

        if (self.channels() <= 2):
            return pcmreader
        elif (self.channels() <= 8):
            from . import ReorderedPCMReader

            standard_channel_mask = self.channel_mask()
            vorbis_channel_mask = VorbisChannelMask(self.channel_mask())
            return ReorderedPCMReader(
                pcmreader,
                [vorbis_channel_mask.channels().index(channel) for channel in
                 standard_channel_mask.channels()])
        else:
            return pcmreader

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AudioFile-compatible object

        may raise EncodingError if some problem occurs when
        encoding the input file.  This includes an error
        in the input stream, a problem writing the output file,
        or even an EncodingError subclass such as
        "UnsupportedBitsPerSample" if the input stream
        is formatted in a way this class is unable to support
        """

        from . import transfer_framelist_data
        from . import BIN
        from . import ignore_sigint
        from . import EncodingError
        from . import DecodingError
        from . import UnsupportedChannelMask
        from . import __default_quality__
        from .vorbis import VorbisChannelMask
        from . import ChannelMask
        import subprocess
        import os

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        devnull = file(os.devnull, 'ab')

        sub = subprocess.Popen([BIN["opusenc"], "--quiet",
                                "--comp", compression,
                                "--raw",
                                "--raw-bits", str(pcmreader.bits_per_sample),
                                "--raw-rate", str(pcmreader.sample_rate),
                                "--raw-chan", str(pcmreader.channels),
                                "--raw-endianness", str(0),
                                "-", filename],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull)

        if ((pcmreader.channels <= 2) or (int(pcmreader.channel_mask) == 0)):
            try:
                transfer_framelist_data(pcmreader, sub.stdin.write)
            except (IOError, ValueError), err:
                sub.stdin.close()
                sub.wait()
                cls.__unlink__(filename)
                raise EncodingError(str(err))
            except Exception, err:
                sub.stdin.close()
                sub.wait()
                cls.__unlink__(filename)
                raise err
        elif (pcmreader.channels <= 8):
            if (int(pcmreader.channel_mask) in
                (0x7,      # FR, FC, FL
                 0x33,     # FR, FL, BR, BL
                 0x37,     # FR, FC, FL, BL, BR
                 0x3f,     # FR, FC, FL, BL, BR, LFE
                 0x70f,    # FL, FC, FR, SL, SR, BC, LFE
                 0x63f)):  # FL, FC, FR, SL, SR, BL, BR, LFE

                standard_channel_mask = ChannelMask(pcmreader.channel_mask)
                vorbis_channel_mask = VorbisChannelMask(standard_channel_mask)
            else:
                raise UnsupportedChannelMask(filename,
                                             int(pcmreader.channel_mask))

            try:
                from . import ReorderedPCMReader

                transfer_framelist_data(
                    ReorderedPCMReader(
                        pcmreader,
                        [standard_channel_mask.channels().index(channel)
                         for channel in vorbis_channel_mask.channels()]),
                    sub.stdin.write)
            except (IOError, ValueError), err:
                sub.stdin.close()
                sub.wait()
                cls.__unlink__(filename)
                raise EncodingError(str(err))
            except Exception, err:
                sub.stdin.close()
                sub.wait()
                cls.__unlink__(filename)
                raise err

        else:
            raise UnsupportedChannelMask(filename,
                                         int(pcmreader.channel_mask))

        sub.stdin.close()

        if (sub.wait() == 0):
            return OpusAudio(filename)
        else:
            raise EncodingError(u"unable to encode file with opusenc")

    def verify(self, progress=None):
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        #Ogg stream verification is likely to be so fast
        #that individual calls to progress() are
        #a waste of time.
        if (progress is not None):
            progress(0, 1)

        try:
            f = open(self.filename, 'rb')
        except IOError, err:
            raise InvalidOpus(str(err))
        try:
            try:
                from . import verify
                verify.ogg(f)
                if (progress is not None):
                    progress(1, 1)
                return True
            except (IOError, ValueError), err:
                raise InvalidOpus(str(err))
        finally:
            f.close()


class OpusTags(VorbisComment):
    @classmethod
    def converted(cls, metadata):
        """converts metadata from another class to OpusTags"""

        from . import VERSION

        if (metadata is None):
            return None
        elif (isinstance(metadata, OpusTags)):
            return cls(metadata.comment_strings[:],
                       metadata.vendor_string)
        elif (metadata.__class__.__name__ == 'FlacMetaData'):
            if (metadata.has_block(4)):
                vorbis_comment = metadata.get_block(4)
                return cls(vorbis_comment.comment_strings[:],
                           vorbis_comment.vendor_string)
            else:
                return cls([], u"Python Audio Tools %s" % (VERSION))
        elif (metadata.__class__.__name__ in ('Flac_VORBISCOMMENT',
                                              'VorbisComment')):
            return cls(metadata.comment_strings[:],
                       metadata.vendor_string)
        else:
            comment_strings = []

            for (attr, key) in cls.ATTRIBUTE_MAP.items():
                value = getattr(metadata, attr)
                if (value is not None):
                    comment_strings.append(u"%s=%s" % (key, value))

            return cls(comment_strings, u"Python Audio Tools %s" % (VERSION))

    def __repr__(self):
        return "OpusTags(%s, %s)" % \
            (repr(self.comment_strings), repr(self.vendor_string))

    def __comment_name__(self):
        return u"Opus Tags"
