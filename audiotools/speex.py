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

from audiotools import AudioFile, InvalidFile, BIN


class InvalidSpeex(InvalidFile):
    pass


class SpeexAudio(AudioFile):
    """an Ogg Speex audio file"""

    from audiotools.text import (COMP_SPEEX_0,
                                 COMP_SPEEX_10)

    SUFFIX = "spx"
    NAME = SUFFIX
    DESCRIPTION = "Ogg Speex"
    COMPRESSION_MODES = tuple(str(i) for i in range(11))
    COMPRESSION_DESCRIPTIONS = {"0": COMP_SPEEX_0, "10": COMP_SPEEX_10}
    BINARIES = ("speexdec", "speexenc")
    BINARY_URLS = {"speexenc": "http://www.speex.org",
                   "speexdec": "http://www.speex.org"}

    def __init__(self, filename):
        from audiotools.bitstream import BitstreamReader

        AudioFile.__init__(self, filename)

        try:
            with BitstreamReader(
                open(self.filename, "rb"), True) as ogg_reader:
                (magic_number,
                 version,
                 header_type,
                 granule_position,
                 self.__serial_number__,
                 page_sequence_number,
                 checksum,
                 segment_count) = ogg_reader.parse("4b 8u 8u 64S 32u 32u 32u 8u")

                if magic_number != b'OggS':
                    from audiotools.text import ERR_OGG_INVALID_MAGIC_NUMBER
                    raise InvalidVorbis(ERR_OGG_INVALID_MAGIC_NUMBER)
                if version != 0:
                    from audiotools.text import ERR_OGG_INVALID_VERSION
                    raise InvalidVorbis(ERR_OGG_INVALID_VERSION)

                segment_lengths = [ogg_reader.read(8) for i in
                                   range(segment_count)]

                (speex_string,
                 speex_version,
                 speex_version_id,
                 header_size,
                 self.__sampling_rate__,
                 mode,
                 mode_bitstream_version,
                 self.__channels__,
                 bitrate,
                 frame_size,
                 vbr,
                 frame_per_packet,
                 extra_headers,
                 reserved1,
                 reserved2) = ogg_reader.parse("8b 20b 13*32u")

                if speex_string != b"Speex   ":
                    raise InvalidSpeex(ERR_SPEEX_INVALID_VERSION)
        except IOError as err:
            raise InvalidSpeex(str(err))

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return 16

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        from audiotools._ogg import PageReader

        try:
            with PageReader(open(self.filename, "rb")) as reader:
                page = reader.read()
                pcm_samples = page.granule_position

                while not page.stream_end:
                    page = reader.read()
                    pcm_samples = max(pcm_samples, page.granule_position)

                return pcm_samples
        except (IOError, ValueError):
            return 0

    def lossless(self):
        """returns True if this track's data is stored losslessly"""

        return False

    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

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

        if metadata is None:
            return
        elif not isinstance(metadata, VorbisComment):
            from audiotools.text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)
        elif not os.access(self.filename, os.W_OK):
            raise IOError(self.filename)

        original_ogg = PacketReader(PageReader(open(self.filename, "rb")))
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

        # discard current file's comment packet
        comment_packet = original_ogg.read_packet()

        # generate new comment packet
        comment_writer = BitstreamRecorder(True)
        vendor_string = metadata.vendor_string.encode("utf-8")
        comment_writer.build("32u {:d}b".format(len(vendor_string)),
                             (len(vendor_string), vendor_string))
        comment_writer.write(32, len(metadata.comment_strings))
        for comment_string in metadata.comment_strings:
            comment_string = comment_string.encode("utf-8")
            comment_writer.build("32u {:d}b".format(len(comment_string)),
                                 (len(comment_string), comment_string))

        for page in packets_to_pages(
            [comment_writer.data()],
            self.__serial_number__,
            starting_sequence_number=sequence_number):
            new_ogg.write(page)
            sequence_number += 1

        # transfer remaining pages after re-sequencing
        page = original_ogg.read_page()
        page.sequence_number = sequence_number
        page.bitstream_serial_number = self.__serial_number__
        sequence_number += 1
        new_ogg.write(page)
        while not page.stream_end:
            page = original_ogg.read_page()
            page.sequence_number = sequence_number
            page.bitstream_serial_number = self.__serial_number__
            sequence_number += 1
            new_ogg.write(page)

        # commit changes
        original_ogg.close()
        new_ogg.close()

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        from audiotools.vorbiscomment import VorbisComment

        if metadata is None:
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

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from io import BytesIO
        from audiotools.bitstream import BitstreamReader
        from audiotools.ogg import PacketReader, PageReader
        from audiotools.vorbiscomment import VorbisComment

        with PacketReader(PageReader(open(self.filename, "rb"))) as reader:
            identification = reader.read_packet()

            comment = BitstreamReader(BytesIO(reader.read_packet()), True)

            vendor_string = \
                comment.read_bytes(comment.read(32)).decode('utf-8')

            comment_strings = [
                comment.read_bytes(comment.read(32)).decode('utf-8')
                for i in range(comment.read(32))]

            return VorbisComment(comment_strings, vendor_string)

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from audiotools import MetaData

        # the vorbis comment packet is required,
        # so simply zero out its contents
        self.set_metadata(MetaData())

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sampling_rate__

    @classmethod
    def supports_to_pcm(cls):
        """returns True if all necessary components are available
        to support the .to_pcm() method"""

        return BIN.can_execute(BIN["speexdec"])

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        from audiotools import PCMFileReader
        import os
        import subprocess

        sub = subprocess.Popen(
            [BIN["speexdec"], self.filename, "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"))

        return PCMFileReader(
            file=sub.stdout,
            sample_rate=self.sample_rate(),
            channels=self.channels(),
            channel_mask=int(self.channel_mask()),
            bits_per_sample=self.bits_per_sample(),
            process=sub)

    @classmethod
    def supports_from_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        return BIN.can_execute(BIN["speexenc"])

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None,
                 total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object
        optional compression level string,
        and optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AudioFile-compatible object

        specifying total_pcm_frames, when the number is known in advance,
        may allow the encoder to work more efficiently but is never required
        """

        import bisect
        import os
        import subprocess
        from audiotools import __default_quality__
        from audiotools import transfer_framelist_data
        from audiotools import EncodingError
        from audiotools import PCMConverter
        from audiotools import ChannelMask

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if pcmreader.bits_per_sample not in (8, 16, 24):
            from audiotools import UnsupportedBitsPerSample
            raise UnsupportedBitsPerSample(
                filename, pcmreader.bits_per_sample)

        if total_pcm_frames is not None:
            from audiotools import CounterPCMReader
            counter_reader = CounterPCMReader(pcmreader)
        else:
            counter_reader = pcmreader

        pcmreader = PCMConverter(
            counter_reader,
            sample_rate=[8000, 8000, 16000, 32000][bisect.bisect(
                [8000, 16000, 32000], pcmreader.sample_rate)],
            channels=min(pcmreader.channels, 2),
            channel_mask=ChannelMask.from_channels(
                min(pcmreader.channels, 2)),
            bits_per_sample=min(pcmreader.bits_per_sample, 16))

        BITS_PER_SAMPLE = {8: ['--8bit'],
                           16: ['--16bit']}[pcmreader.bits_per_sample]

        CHANNELS = {1: [], 2: ['--stereo']}[pcmreader.channels]

        sub = subprocess.Popen(
            [BIN['speexenc'],
             '--quality', str(compression),
             '--rate', str(pcmreader.sample_rate),
             '--le'] + \
            BITS_PER_SAMPLE + \
            CHANNELS + \
            ['-', filename],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"))

        try:
            transfer_framelist_data(pcmreader, sub.stdin.write)
        except (IOError, ValueError) as err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception as err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise err

        sub.stdin.close()

        if sub.wait() == 0:
            if ((total_pcm_frames is None) or
                (total_pcm_frames == counter_reader.frames_written)):
                return SpeexAudio(filename)
            else:
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                cls.__unlink__(filename)
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)
        else:
            raise EncodingError(u"unable to encode file with speexenc")
