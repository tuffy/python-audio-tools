from audiotools import (AudioFile, InvalidFile)
from audiotools.ape import ApeTaggedAudio
from audiotools.bitstream import BitstreamReader, BitstreamWriter


class MPC_Size:
    def __init__(self, value, length):
        self.__value__ = value
        self.__length__ = length

    def __repr__(self):
        return "MPC_Size(%d, %d)" % (self.__value__, self.__length__)

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
    COMPRESSION_MODE = tuple(map(str, range(0, 11)))
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
        block = BitstreamReader(self.get_block(b"SH"), False)
        crc = block.read(32)
        if block.read(8) != 8:
            from audiotools.text import ERR_MPC_INVALID_VERSION
            raise InvalidMPC(ERR_MPC_INVALID_VERSION)
        self.__samples__ = int(MPC_Size.parse(block))
        beg_silence = int(MPC_Size.parse(block))
        self.__sample_rate__ = \
            [44100, 4800, 37800, 3200][block.read(3)]
        max_band = block.read(5) + 1
        self.__channels__ = block.read(4) + 1
        ms = block.read(1)
        block_pwr = block.read(3) * 2

    def blocks(self):
        with BitstreamReader(open(self.filename, "rb"), False) as r:
            if r.read_bytes(4) != b"MPCK":
                raise InvalidMPC(ERR_MPC_INVALID_ID)

            try:
                while True:
                    key = r.read_bytes(2)
                    size = MPC_Size.parse(r)
                    yield key, size, r.read_bytes(int(size) - len(size) - 2)
            except IOError:
                return

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

        # FIXME - update this once encoder is implemented
        return False

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
        peak_title = int(log10(replaygain.track_peak * 2 ** 15) * 20 * 256)
        gain_album = int(round((64.82 - replaygain.album_gain) * 256))
        peak_album = int(log10(replaygain.album_peak * 2 ** 15) * 20 * 256)

        #FIXME - check for missing "RG" block and add one if not present

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
