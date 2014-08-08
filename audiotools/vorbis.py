#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

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

from audiotools import (AudioFile, InvalidFile, ChannelMask)


class InvalidVorbis(InvalidFile):
    pass


class VorbisAudio(AudioFile):
    """an Ogg Vorbis file"""

    from audiotools.text import (COMP_VORBIS_0,
                                 COMP_VORBIS_10)

    SUFFIX = "ogg"
    NAME = SUFFIX
    DESCRIPTION = u"Ogg Vorbis"
    DEFAULT_COMPRESSION = "3"
    COMPRESSION_MODES = tuple([str(i) for i in range(0, 11)])
    COMPRESSION_DESCRIPTIONS = {"0": COMP_VORBIS_0,
                                "10": COMP_VORBIS_10}

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        self.__sample_rate__ = 0
        self.__channels__ = 0
        try:
            self.__read_identification__()
        except IOError as msg:
            raise InvalidVorbis(str(msg))

    def __read_identification__(self):
        from audiotools.bitstream import BitstreamReader

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
                from audiotools.text import ERR_OGG_INVALID_MAGIC_NUMBER
                raise InvalidFLAC(ERR_OGG_INVALID_MAGIC_NUMBER)
            if (version != 0):
                from audiotools.text import ERR_OGG_INVALID_VERSION
                raise InvalidFLAC(ERR_OGG_INVALID_VERSION)

            segment_length = ogg_reader.read(8)

            (vorbis_type,
             header,
             version,
             self.__channels__,
             self.__sample_rate__,
             maximum_bitrate,
             nominal_bitrate,
             minimum_bitrate,
             blocksize0,
             blocksize1,
             framing) = ogg_reader.parse(
                "8u 6b 32u 8u 32u 32u 32u 32u 4u 4u 1u")

            if (vorbis_type != 1):
                from audiotools.text import ERR_VORBIS_INVALID_TYPE
                raise InvalidVorbis(ERR_VORBIS_INVALID_TYPE)
            if (header != 'vorbis'):
                from audiotools.text import ERR_VORBIS_INVALID_HEADER
                raise InvalidVorbis(ERR_VORBIS_INVALID_HEADER)
            if (version != 0):
                from audiotools.text import ERR_VORBIS_INVALID_VERSION
                raise InvalidVorbis(ERR_VORBIS_INVALID_VERSION)
            if (framing != 1):
                from audiotools.text import ERR_VORBIS_INVALID_FRAMING_BIT
                raise InvalidVorbis(ERR_VORBIS_INVALID_FRAMING_BIT)
        finally:
            f.close()

    def lossless(self):
        """returns False"""

        return False

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return 16

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        if (self.channels() == 1):
            return ChannelMask.from_fields(
                front_center=True)
        elif (self.channels() == 2):
            return ChannelMask.from_fields(
                front_left=True, front_right=True)
        elif (self.channels() == 3):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True)
        elif (self.channels() == 4):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True)
        elif (self.channels() == 5):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True,
                back_left=True, back_right=True)
        elif (self.channels() == 6):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True,
                back_left=True, back_right=True,
                low_frequency=True)
        elif (self.channels() == 7):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True,
                side_left=True, side_right=True,
                back_center=True, low_frequency=True)
        elif (self.channels() == 8):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                side_left=True, side_right=True,
                back_left=True, back_right=True,
                front_center=True, low_frequency=True)
        else:
            return ChannelMask(0)

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

        return self.__sample_rate__

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from audiotools.decoders import VorbisDecoder

        try:
            return VorbisDecoder(self.filename)
        except ValueError as err:
            from audiotools import PCMReaderError
            return PCMReaderError(str(err),
                                  self.sample_rate(),
                                  self.channels(),
                                  int(self.channel_mask()),
                                  self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new VorbisAudio object"""

        from audiotools import (BufferedPCMReader,
                                __default_quality__,
                                EncodingError)
        from audiotools.encoders import encode_vorbis

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        if ((pcmreader.channels > 2) and (pcmreader.channels <= 8)):
            channel_mask = int(pcmreader.channel_mask)
            if ((channel_mask != 0) and
                (channel_mask not in
                 (0x7,       # FR, FC, FL
                  0x33,      # FR, FL, BR, BL
                  0x37,      # FR, FC, FL, BL, BR
                  0x3f,      # FR, FC, FL, BL, BR, LFE
                  0x70f,     # FL, FC, FR, SL, SR, BC, LFE
                  0x63f))):  # FL, FC, FR, SL, SR, BL, BR, LFE
                raise UnsupportedChannelMask(filename, channel_mask)

        try:
            if (total_pcm_frames is not None):
                from audiotools import CounterPCMReader
                pcmreader = CounterPCMReader(pcmreader)

            encode_vorbis(filename,
                          BufferedPCMReader(pcmreader),
                          float(compression) / 10)

            if ((total_pcm_frames is not None) and
                (total_pcm_frames != pcmreader.frames_written)):
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                cls.__unlink__(filename)
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

            return VorbisAudio(filename)
        except (ValueError, IOError) as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))

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
        from audiotools.vorbiscomment import VorbisComment
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

        # transfer current file's identification packet in its own page
        identification_packet = original_ogg.read_packet()
        for (i, page) in enumerate(packet_to_pages(
                identification_packet,
                self.__serial_number__,
                starting_sequence_number=sequence_number)):
            page.stream_beginning = (i == 0)
            new_ogg.write(page)
            sequence_number += 1

        # discard the current file's comment packet
        comment_packet = original_ogg.read_packet()

        # generate new comment packet
        comment_writer = BitstreamRecorder(True)
        comment_writer.build("8u 6b", (3, "vorbis"))
        vendor_string = metadata.vendor_string.encode('utf-8')
        comment_writer.build("32u %db" % (len(vendor_string)),
                             (len(vendor_string), vendor_string))
        comment_writer.write(32, len(metadata.comment_strings))
        for comment_string in metadata.comment_strings:
            comment_string = comment_string.encode('utf-8')
            comment_writer.build("32u %db" % (len(comment_string)),
                                 (len(comment_string), comment_string))

        comment_writer.build("1u a", (1,))  # framing bit

        # transfer codebooks packet from original file to new file
        codebooks_packet = original_ogg.read_packet()

        for page in packets_to_pages(
                [comment_writer.data(), codebooks_packet],
                self.__serial_number__,
                starting_sequence_number=sequence_number):
            new_ogg.write(page)
            sequence_number += 1

        # transfer remaining pages after re-sequencing
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

        from audiotools.vorbiscomment import VorbisComment

        if (metadata is None):
            return self.delete_metadata()

        metadata = VorbisComment.converted(metadata)

        old_metadata = self.get_metadata()

        metadata.vendor_string = old_metadata.vendor_string

        # remove REPLAYGAIN_* tags from new metadata (if any)
        for key in [u"REPLAYGAIN_TRACK_GAIN",
                    u"REPLAYGAIN_TRACK_PEAK",
                    u"REPLAYGAIN_ALBUM_GAIN",
                    u"REPLAYGAIN_ALBUM_PEAK",
                    u"REPLAYGAIN_REFERENCE_LOUDNESS"]:
            try:
                metadata[key] = old_metadata[key]
            except KeyError:
                metadata[key] = []

        self.update_metadata(metadata)

    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from cStringIO import StringIO
        from audiotools.bitstream import BitstreamReader
        from audiotools.ogg import PacketReader, PageReader
        from audiotools.vorbiscomment import VorbisComment

        reader = PacketReader(PageReader(open(self.filename, "rb")))

        identification = reader.read_packet()
        comment = BitstreamReader(StringIO(reader.read_packet()), True)

        (packet_type, packet_header) = comment.parse("8u 6b")
        if ((packet_type == 3) and (packet_header == 'vorbis')):
            vendor_string = \
                comment.read_bytes(comment.read(32)).decode('utf-8')
            comment_strings = [
                comment.read_bytes(comment.read(32)).decode('utf-8')
                for i in range(comment.read(32))]
            if (comment.read(1) == 1):   # framing bit
                return VorbisComment(comment_strings, vendor_string)
            else:
                return None
        else:
            return None

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from audiotools import MetaData

        # the vorbis comment packet is required,
        # so simply zero out its contents
        self.set_metadata(MetaData())

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return True

    def get_replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values"""

        from audiotools import ReplayGain

        vorbis_metadata = self.get_metadata()

        if ((vorbis_metadata is not None) and
            (set(['REPLAYGAIN_TRACK_PEAK',
                  'REPLAYGAIN_TRACK_GAIN',
                  'REPLAYGAIN_ALBUM_PEAK',
                  'REPLAYGAIN_ALBUM_GAIN']).issubset(vorbis_metadata.keys()))):
            # we have ReplayGain data
            try:
                return ReplayGain(
                    vorbis_metadata['REPLAYGAIN_TRACK_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_TRACK_PEAK'][0],
                    vorbis_metadata['REPLAYGAIN_ALBUM_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_ALBUM_PEAK'][0])
            except (IndexError, ValueError):
                return None
        else:
            return None

    def set_replay_gain(self, replaygain):
        """given a ReplayGain object, sets the track's gain to those values

        may raise IOError if unable to modify the file"""

        if (replaygain is None):
            return self.delete_replay_gain()

        vorbis_comment = self.get_metadata()
        if (vorbis_comment is None):
            from audiotools.vorbiscomment import VorbisComment
            from audiotools import VERSION

            vorbis_comment = VorbisComment(
                [], u"Python Audio Tools %s" % (VERSION))

        vorbis_comment["REPLAYGAIN_TRACK_GAIN"] = [
            "%1.2f dB" % (replaygain.track_gain)]
        vorbis_comment["REPLAYGAIN_TRACK_PEAK"] = [
            "%1.8f" % (replaygain.track_peak)]
        vorbis_comment["REPLAYGAIN_ALBUM_GAIN"] = [
            "%1.2f dB" % (replaygain.album_gain)]
        vorbis_comment["REPLAYGAIN_ALBUM_PEAK"] = [
            "%1.8f" % (replaygain.album_peak)]
        vorbis_comment["REPLAYGAIN_REFERENCE_LOUDNESS"] = [u"89.0 dB"]

        self.update_metadata(vorbis_comment)

    def delete_replay_gain(self):
        """removes ReplayGain values from file, if any

        may raise IOError if unable to modify the file"""

        vorbis_comment = self.get_metadata()
        if (vorbis_comment is not None):
            for field in ["REPLAYGAIN_TRACK_GAIN",
                          "REPLAYGAIN_TRACK_PEAK",
                          "REPLAYGAIN_ALBUM_GAIN",
                          "REPLAYGAIN_ALBUM_PEAK",
                          "REPLAYGAIN_REFERENCE_LOUDNESS"]:
                try:
                    del(vorbis_comment[field])
                except KeyError:
                    pass

            self.update_metadata(vorbis_comment)

    @classmethod
    def available(cls, system_binaries):
        """returns True if all necessary compenents are available
        to support format"""

        try:
            from audiotools.decoders import VorbisDecoder
            from audiotools.encoders import encode_vorbis

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

        # display where to get vorbisfile
        messenger.info(
            ERR_LIBRARY_NEEDED %
            {"library": u"\"libvorbisfile\"",
             "format": format_})
        messenger.info(
            ERR_LIBRARY_DOWNLOAD_URL %
            {"library": u"libvorbisfile",
             "url": "http://www.xiph.org/"})

        messenger.info(ERR_PROGRAM_PACKAGE_MANAGER)


class VorbisChannelMask(ChannelMask):
    """the Vorbis-specific channel mapping"""

    def __repr__(self):
        return "VorbisChannelMask(%s)" % \
            ",".join(["%s=%s" % (field, getattr(self, field))
                      for field in self.SPEAKER_TO_MASK.keys()
                      if (getattr(self, field))])

    def channels(self):
        """returns a list of speaker strings this mask contains

        returned in the order in which they should appear
        in the PCM stream
        """

        count = len(self)
        if (count == 1):
            return ["front_center"]
        elif (count == 2):
            return ["front_left", "front_right"]
        elif (count == 3):
            return ["front_left", "front_center", "front_right"]
        elif (count == 4):
            return ["front_left", "front_right",
                    "back_left", "back_right"]
        elif (count == 5):
            return ["front_left", "front_center", "front_right",
                    "back_left", "back_right"]
        elif (count == 6):
            return ["front_left", "front_center", "front_right",
                    "back_left", "back_right", "low_frequency"]
        elif (count == 7):
            return ["front_left", "front_center", "front_right",
                    "side_left", "side_right", "back_center",
                    "low_frequency"]
        elif (count == 8):
            return ["front_left", "front_center", "front_right",
                    "side_left", "side_right",
                    "back_left", "back_right", "low_frequency"]
        else:
            return []
