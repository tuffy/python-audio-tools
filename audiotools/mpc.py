# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2016  James Buren and Brian Langenberger

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


from audiotools import (AudioFile, InvalidFile)
from audiotools.ape import ApeTaggedAudio
from audiotools.bitstream import BitstreamReader, BitstreamWriter


class MPC_Size:
    def __init__(self, value, length):
        self.__value__ = value
        self.__length__ = length

    def __repr__(self):
        return "MPC_Size({!r}, {!r})".format(self.__value__, self.__length__)

    def __int__(self):
        return self.__value__

    def __len__(self):
        return self.__length__

    @classmethod
    def parse(cls, reader):
        cont, value = reader.parse("1u 7u")
        length = 1

        while cont == 1:
            cont, value2 = reader.parse("1u 7u")
            value = (value << 7) | value2
            length += 1

        return cls(value, length)

    def build(self, writer):
        for i in reversed(range(self.__length__)):
            writer.write(1, 1 if (i > 0) else 0)
            writer.write(7, (self.__value__ >> (i * 7)) & 0x7F)


class InvalidMPC(InvalidFile):
    """raised by invalid files during MPC initialization"""

    pass


class MPCAudio(ApeTaggedAudio, AudioFile):
    """an MPC audio file"""

    SUFFIX = "mpc"
    NAME = SUFFIX
    DESCRIPTION = u"MusePack"
    DEFAULT_COMPRESSION = "5"

    # Ranges from 0 to 10. Lower levels mean lower kbps, and therefore
    # lower quality.
    COMPRESSION_MODES = tuple(map(str, range(0, 11)))
    COMPRESSION_DESCRIPTIONS = {"0": u"poor quality (~20 kbps)",
                                "1": u"poor quality (~30 kbps)",
                                "2": u"low quality (~60 kbps)",
                                "3": u"low/medium quality (~90 kbps)",
                                "4": u"medium quality (~130 kbps)",
                                "5": u"high quality (~180 kbps)",
                                "6": u"excellent quality (~210 kbps)",
                                "7": u"excellent quality (~240 kbps)",
                                "8": u"excellent quality (~270 kbps)",
                                "9": u"excellent quality (~300 kbps)",
                                "10": u"excellent quality (~350 kbps)"}

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        try:
            block = BitstreamReader(self.get_block(b"SH"), False)
            crc = block.read(32)
            if block.read(8) != 8:
                from audiotools.text import ERR_MPC_INVALID_VERSION
                raise InvalidMPC(ERR_MPC_INVALID_VERSION)
            self.__samples__ = int(MPC_Size.parse(block))
            beg_silence = int(MPC_Size.parse(block))
            self.__sample_rate__ = \
                [44100, 48000, 37800, 32000][block.read(3)]
            max_band = block.read(5) + 1
            self.__channels__ = block.read(4) + 1
            ms = block.read(1)
            block_pwr = block.read(3) * 2
        except IOError as err:
            raise InvalidMPC(str(err))

    def blocks(self):
        with BitstreamReader(open(self.filename, "rb"), False) as r:
            if r.read_bytes(4) != b"MPCK":
                from audiotools.text import ERR_MPC_INVALID_ID
                raise InvalidMPC(ERR_MPC_INVALID_ID)

            key = r.read_bytes(2)
            size = MPC_Size.parse(r)
            while key != b"SE":
                yield key, size, r.read_bytes(int(size) - len(size) - 2)
                key = r.read_bytes(2)
                size = MPC_Size.parse(r)
            yield key, size, r.read_bytes(int(size) - len(size) - 2)

    def get_block(self, block_id):
        for key, size, block in self.blocks():
            if key == block_id:
                return block
        else:
            raise KeyError(block_id)

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return 16

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def lossless(self):
        """returns True if this track's data is stored losslessly"""

        return False

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__samples__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    @classmethod
    def supports_to_pcm(cls):
        """returns True if all necessary components are available
        to support the .to_pcm() method"""

        try:
            from audiotools.decoders import MPCDecoder
            return True
        except ImportError:
            return False

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        from audiotools.decoders import MPCDecoder

        try:
            return MPCDecoder(self.filename)
        except (IOError, ValueError) as err:
            from audiotools import PCMReaderError
            return PCMReaderError(error_message=str(err),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def supports_from_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        try:
            from audiotools.encoders import encode_mpc
            return True
        except ImportError:
            return False

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None,
                 total_pcm_frames=None):
        from audiotools import __default_quality__
        from audiotools import PCMConverter
        from audiotools import ChannelMask
        from audiotools.encoders import encode_mpc

        if (compression is None) or (compression not in cls.COMPRESSION_MODES):
            compression = __default_quality__(cls.NAME)

        if pcmreader.bits_per_sample not in {8, 16, 24}:
            from audiotools import UnsupportedBitsPerSample
            pcmreader.close()
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        if pcmreader.sample_rate in (32000, 37800, 44100, 48000):
            sample_rate = pcmreader.sample_rate

            if total_pcm_frames is not None:
                from audiotools import CounterPCMReader
                pcmreader = CounterPCMReader(pcmreader)
        else:
            from bisect import bisect

            sample_rate = [32000,
                           32000,
                           37800,
                           44100,
                           48000][bisect([32000, 37800, 44100, 4800],
                                         pcmreader.sample_rate)]

            total_pcm_frames = None

        try:
            encode_mpc(
                filename,
                PCMConverter(pcmreader,
                             sample_rate=sample_rate,
                             channels=min(pcmreader.channels, 2),
                             channel_mask=int(ChannelMask.from_channels(
                                 min(pcmreader.channels, 2))),
                             bits_per_sample=16),
                float(compression),
                total_pcm_frames if (total_pcm_frames is not None) else 0)

            # ensure PCM frames match, if indicated
            if ((total_pcm_frames is not None) and
                (total_pcm_frames != pcmreader.frames_written)):
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                from audiotools import EncodingError
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

            return MPCAudio(filename)
        except (IOError, ValueError) as err:
            from audiotools import EncodingError
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception:
            cls.__unlink__(filename)
            raise
        finally:
            pcmreader.close()

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return True

    def get_replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values

        may raise IOError if unable to read the file"""

        from audiotools import ReplayGain

        try:
            rg = BitstreamReader(self.get_block(b"RG"), False)
        except KeyError:
            return None

        version = rg.read(8)
        if version != 1:
            return None

        gain_title = rg.read(16)
        peak_title = rg.read(16)
        gain_album = rg.read(16)
        peak_album = rg.read(16)

        if ((gain_title == 0) and (peak_title == 0) and
            (gain_album == 0) and (peak_album == 0)):
            return None
        else:
            return ReplayGain(
                track_gain=64.82 - float(gain_title) / 256,
                track_peak=(10 ** (float(peak_title) / 256 / 20)) / 2 ** 15,
                album_gain=64.82 - float(gain_album) / 256,
                album_peak=(10 ** (float(peak_album) / 256 / 20)) / 2 ** 15)

    def set_replay_gain(self, replaygain):
        """given a ReplayGain object, sets the track's gain to those values

        may raise IOError if unable to modify the file"""

        from math import log10
        from audiotools import TemporaryFile

        gain_title = int(round((64.82 - replaygain.track_gain) * 256))
        if replaygain.track_peak > 0.0:
            peak_title = int(log10(replaygain.track_peak * 2 ** 15) * 20 * 256)
        else:
            peak_title = 0
        gain_album = int(round((64.82 - replaygain.album_gain) * 256))
        if replaygain.album_peak > 0.0:
            peak_album = int(log10(replaygain.album_peak * 2 ** 15) * 20 * 256)
        else:
            peak_album = 0

        #FIXME - check for missing "RG" block and add one if not present

        metadata = self.get_metadata()

        writer = BitstreamWriter(TemporaryFile(self.filename), False)
        writer.write_bytes(b"MPCK")
        for key, size, block in self.blocks():
            if key != b"RG":
                writer.write_bytes(key)
                size.build(writer)
                writer.write_bytes(block)
            else:
                writer.write_bytes(b"RG")
                MPC_Size(2 + 1 + 1 + 2 * 4, 1).build(writer)
                writer.write(8, 1)
                writer.write(16, gain_title)
                writer.write(16, peak_title)
                writer.write(16, gain_album)
                writer.write(16, peak_album)

        if metadata is not None:
            writer.set_endianness(True)
            metadata.build(writer)

        writer.close()

    def delete_replay_gain(self):
        """removes ReplayGain values from file, if any

        may raise IOError if unable to modify the file"""

        from audiotools import TemporaryFile

        writer = BitstreamWriter(TemporaryFile(self.filename), False)
        writer.write_bytes(b"MPCK")
        for key, size, block in self.blocks():
            if key != b"RG":
                writer.write_bytes(key)
                size.build(writer)
                writer.write_bytes(block)
            else:
                writer.write_bytes(b"RG")
                MPC_Size(2 + 1 + 1 + 2 * 4, 1).build(writer)
                writer.write(8, 1)
                writer.write(16, 0)
                writer.write(16, 0)
                writer.write(16, 0)
                writer.write(16, 0)
        writer.close()
