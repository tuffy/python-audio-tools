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

from audiotools import (AudioFile, InvalidFile)
from audiotools.vorbis import (VorbisAudio, VorbisChannelMask)
from audiotools.vorbiscomment import VorbisComment


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

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        self.__channels__ = 0
        self.__channel_mask__ = 0

        #get channel count and channel mask from first packet
        from audiotools.bitstream import BitstreamReader
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
                    from audiotools.text import ERR_OGG_INVALID_MAGIC_NUMBER
                    raise InvalidFLAC(ERR_OGG_INVALID_MAGIC_NUMBER)
                if (version != 0):
                    from audiotools.text import ERR_OGG_INVALID_VERSION
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
                    from audiotools.text import ERR_OPUS_INVALID_TYPE
                    raise InvalidOpus(ERR_OPUS_INVALID_TYPE)
                if (version != 1):
                    from audiotools.text import ERR_OPUS_INVALID_VERSION
                    raise InvalidOpus(ERR_OPUS_INVALID_VERSION)
                if (self.__channels__ == 0):
                    from audiotools.text import ERR_OPUS_INVALID_CHANNELS
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
                        from audiotools.text import ERR_OPUS_INVALID_CHANNELS
                        raise InvalidOpus(ERR_OPUS_INVALID_CHANNELS)
                    channel_mapping = [ogg_reader.read(8)
                                       for i in xrange(self.__channels__)]
            finally:
                f.close()
        except IOError as msg:
            raise InvalidOpus(str(msg))

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        import os
        from audiotools import TemporaryFile
        from audiotools.ogg import (PageReader, PacketReader,
                                    PageWriter, packet_to_pages)
        from audiotools.bitstream import BitstreamRecorder

        if (metadata is None):
            return
        elif (not isinstance(metadata, VorbisComment)):
            from audiotools.text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)
        elif (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        original_ogg = PacketReader(PageReader(file(self.filename, "rb")))
        new_ogg = PageWriter(TemporaryFile(self.filename))

        #transfer current file's identification page/packet
        #(the ID packet is always fixed size, and fits in one page)
        identification_page = original_ogg.read_page()
        new_ogg.write(identification_page)
        sequence_number = 1

        #discard the current file's comment packet
        original_ogg.read_packet()

        #write the new comment packet in its own page(s)
        comment_writer = BitstreamRecorder(True)
        comment_writer.write_bytes("OpusTags")
        vendor_string = metadata.vendor_string.encode('utf-8')
        comment_writer.build("32u %db" % (len(vendor_string)),
                             (len(vendor_string), vendor_string))
        comment_writer.write(32, len(metadata.comment_strings))
        for comment_string in metadata.comment_strings:
            comment_string = comment_string.encode('utf-8')
            comment_writer.build("32u %db" % (len(comment_string)),
                                 (len(comment_string), comment_string))

        for page in packet_to_pages(
                comment_writer.data(),
                identification_page.bitstream_serial_number,
                starting_sequence_number=sequence_number):
            new_ogg.write(page)
            sequence_number += 1

        #transfer remaining pages after re-sequencing
        page = original_ogg.read_page()
        page.sequence_number = sequence_number
        sequence_number += 1
        new_ogg.write(page)
        while (not page.stream_end):
            page = original_ogg.read_page()
            page.sequence_number = sequence_number
            sequence_number += 1
            new_ogg.write(page)

        original_ogg.close()
        new_ogg.close()

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return False

    def get_replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values

        may raise IOError if unable to read the file"""

        return None

    def set_replay_gain(self, replaygain):
        """given a ReplayGain object, sets the track's gain to those values

        may raise IOError if unable to modify the file"""

        pass

    def delete_replay_gain(self):
        """removes ReplayGain values from file, if any

        may raise IOError if unable to modify the file"""

        pass

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        if (metadata is not None):
            metadata = VorbisComment.converted(metadata)

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

        from audiotools.ogg import PacketReader, PageReader
        from cStringIO import StringIO
        from audiotools.bitstream import BitstreamReader

        packets = PacketReader(PageReader(open(self.filename, "rb")))

        identification = packets.read_packet()
        comment = BitstreamReader(StringIO(packets.read_packet()), True)

        if (comment.read_bytes(8) == "OpusTags"):
            vendor_string = \
                comment.read_bytes(comment.read(32)).decode('utf-8')
            comment_strings = [
                comment.read_bytes(comment.read(32)).decode('utf-8')
                for i in xrange(comment.read(32))]
            return VorbisComment(comment_strings, vendor_string)
        else:
            return None

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from audiotools import MetaData

        #the comment packet is required,
        #so simply zero out its contents
        self.set_metadata(MetaData())

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        from audiotools._ogg import PageReader

        try:
            reader = PageReader(file(self.filename, "rb"))
            page = reader.read()
            pcm_samples = page.granule_position

            while (not page.stream_end):
                page = reader.read()
                pcm_samples = max(pcm_samples, page.granule_position)

            reader.close()
            return pcm_samples
        except (IOError, ValueError):
            return 0

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return 48000

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        from audiotools.decoders import OpusDecoder

        return OpusDecoder(self.filename)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
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

        from audiotools import (BufferedPCMReader,
                                PCMConverter,
                                __default_quality__,
                                EncodingError)
        from audiotools.encoders import encode_opus

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        if ((pcmreader.channels > 2) and (pcmreader.channels <= 8)):
            channel_mask = int(pcmreader.channel_mask)
            if ((channel_mask != 0) and
                (channel_mask not in
                 (0x7,      # FR, FC, FL
                  0x33,     # FR, FL, BR, BL
                  0x37,     # FR, FC, FL, BL, BR
                  0x3f,     # FR, FC, FL, BL, BR, LFE
                  0x70f,    # FL, FC, FR, SL, SR, BC, LFE
                  0x63f))):  # FL, FC, FR, SL, SR, BL, BR, LFE
                raise UnsupportedChannelMask(filename, channel_mask)

        try:
            encode_opus(filename,
                        BufferedPCMReader(
                            PCMConverter(pcmreader,
                                         sample_rate=48000,
                                         channels=pcmreader.channels,
                                         channel_mask=pcmreader.channel_mask,
                                         bits_per_sample=16)),
                        quality=int(compression),
                        original_sample_rate=pcmreader.sample_rate)

            return cls(filename)
        except (ValueError, IOError) as err:
            cls.__unlink__(filename)
            raise EncodingError(err)

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        import os
        from audiotools import TemporaryFile
        from audiotools.ogg import (PageReader,
                                    PacketReader,
                                    PageWriter,
                                    packet_to_pages,
                                    packets_to_pages)
        from audiotools.bitstream import BitstreamRecorder

        if (metadata is None):
            return
        elif (not isinstance(metadata, VorbisComment)):
            from audiotools.text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)
        elif (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        original_ogg = PacketReader(PageReader(file(self.filename, "rb")))
        new_ogg = PageWriter(TemporaryFile(self.filename))

        sequence_number = 0

        #transfer current file's identification packet in its own page
        identification_packet = original_ogg.read_packet()
        for (i, page) in enumerate(packet_to_pages(
                identification_packet,
                self.__serial_number__,
                starting_sequence_number=sequence_number)):
            page.stream_beginning = (i == 0)
            new_ogg.write(page)
            sequence_number += 1

        #discard the current file's comment packet
        comment_packet = original_ogg.read_packet()

        #generate new comment packet
        comment_writer = BitstreamRecorder(True)
        comment_writer.write_bytes("OpusTags")
        vendor_string = metadata.vendor_string.encode('utf-8')
        comment_writer.build("32u %db" % (len(vendor_string)),
                             (len(vendor_string), vendor_string))
        comment_writer.write(32, len(metadata.comment_strings))
        for comment_string in metadata.comment_strings:
            comment_string = comment_string.encode('utf-8')
            comment_writer.build("32u %db" % (len(comment_string)),
                                 (len(comment_string), comment_string))

        for page in packet_to_pages(
                comment_writer.data(),
                self.__serial_number__,
                starting_sequence_number=sequence_number):
            new_ogg.write(page)
            sequence_number += 1

        #transfer remaining pages after re-sequencing
        page = original_ogg.read_page()
        page.sequence_number = sequence_number
        sequence_number += 1
        new_ogg.write(page)
        while (not page.stream_end):
            page = original_ogg.read_page()
            page.sequence_number = sequence_number
            page.bitstream_serial_number = self.__serial_number__
            sequence_number += 1
            new_ogg.write(page)

        original_ogg.close()
        new_ogg.close()

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        if (metadata is not None):
            metadata = VorbisComment.converted(metadata)

            old_metadata = self.get_metadata()

            metadata.vendor_string = old_metadata.vendor_string

            #port REPLAYGAIN and ENCODER from old metadata to new metadata
            for key in [u"REPLAYGAIN_TRACK_GAIN",
                        u"REPLAYGAIN_TRACK_PEAK",
                        u"REPLAYGAIN_ALBUM_GAIN",
                        u"REPLAYGAIN_ALBUM_PEAK",
                        u"REPLAYGAIN_REFERENCE_LOUDNESS",
                        u"ENCODER"]:
                try:
                    metadata[key] = old_metadata[key]
                except KeyError:
                    metadata[key] = []

            self.update_metadata(metadata)

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from cStringIO import StringIO
        from audiotools.bitstream import BitstreamReader
        from audiotools.ogg import PacketReader, PageReader

        reader = PacketReader(PageReader(open(self.filename, "rb")))

        identification = reader.read_packet()
        comment = BitstreamReader(StringIO(reader.read_packet()), True)

        if (comment.read_bytes(8) == "OpusTags"):
            vendor_string = \
                comment.read_bytes(comment.read(32)).decode('utf-8')
            comment_strings = [
                comment.read_bytes(comment.read(32)).decode('utf-8')
                for i in xrange(comment.read(32))]

            return VorbisComment(comment_strings, vendor_string)
        else:
            return None

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from audiotools import MetaData

        #the vorbis comment packet is required,
        #so simply zero out its contents
        self.set_metadata(MetaData())

    def verify(self, progress=None):
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        #Checking for a truncated Ogg stream typically involves
        #verifying that the "end of stream" flag is set on the last
        #Ogg page in the stream in the event that one or more whole
        #pages is lost.  But since the OpusFile decoder doesn't perform
        #this check and doesn't provide any access to its internal
        #Ogg decoder (unlike Vorbis), we'll perform that check externally.
        #
        #And since it's a fast check, we won't bother to update progress.

        from audiotools.ogg import PageReader
        import os.path

        try:
            reader = PageReader(open(self.filename, "rb"))
        except IOError as err:
            raise InvalidOpus(str(err))

        try:
            page = reader.read()
            while (not page.stream_end):
                page = reader.read()
            reader.close()
        except (IOError, ValueError) as err:
            raise InvalidOpus(str(err))

        return AudioFile.verify(self, progress)

    @classmethod
    def available(cls, system_binaries):
        """returns True if all necessary compenents are available
        to support format"""

        try:
            from audiotools.decoders import OpusDecoder
            from audiotools.encoders import encode_opus

            return True
        except ImportError:
            return False

    @classmethod
    def missing_components(cls, messenger):
        """given a Messenger object, displays missing binaries or libraries
        needed to support this format and where to get them"""

        from audiotools.text import (ERR_LIBRARY_NEEDED,
                                     ERR_LIBRARY_DOWNLOAD_URL,
                                     ERR_PROGRAM_PACKAGE_MANAGER)

        format_ = cls.NAME.decode('ascii')

        #display where to get vorbisfile
        messenger.info(
            ERR_LIBRARY_NEEDED %
            {"library": u"\"libopus\" and \"opusfile\"",
             "format": format_})
        messenger.info(
            ERR_LIBRARY_DOWNLOAD_URL %
            {"library": u"libopus and opusfile",
             "url": "http://www.opus-codec.org/"})

        messenger.info(ERR_PROGRAM_PACKAGE_MANAGER)
