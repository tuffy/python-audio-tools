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


from audiotools import WaveContainer, InvalidFile
from audiotools.ape import ApeTaggedAudio, ApeGainedAudio


class InvalidWavPack(InvalidFile):
    pass


def __riff_chunk_ids__(data_size, data):
    (riff, size, wave) = data.parse("4b 32u 4b")
    if riff != b"RIFF":
        return
    elif wave != b"WAVE":
        return
    else:
        data_size -= 12

    while data_size > 0:
        (chunk_id, chunk_size) = data.parse("4b 32u")
        data_size -= 8
        if (chunk_size % 2) == 1:
            chunk_size += 1
        yield chunk_id
        if chunk_id != b"data":
            data.skip_bytes(chunk_size)
            data_size -= chunk_size


class WavPackAudio(ApeTaggedAudio, ApeGainedAudio, WaveContainer):
    """a WavPack audio file"""

    from audiotools.text import (COMP_WAVPACK_FAST,
                                 COMP_WAVPACK_VERYHIGH)

    SUFFIX = "wv"
    NAME = SUFFIX
    DESCRIPTION = u"WavPack"
    DEFAULT_COMPRESSION = "standard"
    COMPRESSION_MODES = ("fast", "standard", "high", "veryhigh")
    COMPRESSION_DESCRIPTIONS = {"fast": COMP_WAVPACK_FAST,
                                "veryhigh": COMP_WAVPACK_VERYHIGH}

    BITS_PER_SAMPLE = (8, 16, 24, 32)
    SAMPLING_RATE = (6000,  8000,  9600,   11025,
                     12000, 16000, 22050,  24000,
                     32000, 44100, 48000,  64000,
                     88200, 96000, 192000, 0)

    def __init__(self, filename):
        """filename is a plain string"""

        WaveContainer.__init__(self, filename)
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_frames__ = 0

        try:
            self.__read_info__()
        except IOError as msg:
            raise InvalidWavPack(str(msg))

    def lossless(self):
        """returns True"""

        return True

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        return self.__channel_mask__

    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        metadata = ApeTaggedAudio.get_metadata(self)
        if metadata is not None:
            metadata.frame_count = self.total_frames()
        return metadata

    def has_foreign_wave_chunks(self):
        """returns True if the audio file contains non-audio RIFF chunks

        during transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks"""

        for (sub_header, nondecoder, data_size, data) in self.sub_blocks():
            if (sub_header == 1) and nondecoder:
                if (set(__riff_chunk_ids__(data_size,
                                           data)) != {b"fmt ", b"data"}):
                    return True
            elif (sub_header == 2) and nondecoder:
                return True
        else:
            return False

    def wave_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        may raise ValueError if there's a problem with
        the header or footer data
        may raise IOError if there's a problem reading
        header or footer data from the file
        """

        head = None
        tail = None

        for (sub_block_id, nondecoder, data_size, data) in self.sub_blocks():
            if (sub_block_id == 1) and nondecoder:
                head = data.read_bytes(data_size)
            elif (sub_block_id == 2) and nondecoder:
                tail = data.read_bytes(data_size)

        if head is not None:
            return (head, tail if tail is not None else b"")
        else:
            raise ValueError("no wave header found")

    @classmethod
    def from_wave(cls, filename, header, pcmreader, footer, compression=None,
                  encoding_function=None):
        """encodes a new file from wave data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object

        header + pcm data + footer should always result
        in the original wave file being restored
        without need for any padding bytes

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        from audiotools.encoders import encode_wavpack
        from audiotools import BufferedPCMReader
        from audiotools import CounterPCMReader
        from audiotools.wav import (validate_header, validate_footer)
        from audiotools import EncodingError
        from audiotools import __default_quality__

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        # ensure header is valid
        try:
            (total_size, data_size) = validate_header(header)
        except ValueError as err:
            raise EncodingError(str(err))

        counter = CounterPCMReader(pcmreader)

        try:
            (encode_wavpack if encoding_function is None
             else encoding_function)(
                filename=filename,
                pcmreader=counter,
                compression=compression,
                wave_header=header,
                wave_footer=footer)

            counter.close()

            data_bytes_written = counter.bytes_written()

            # ensure output data size matches the "data" chunk's size
            if data_size != data_bytes_written:
                from audiotools.text import ERR_WAV_TRUNCATED_DATA_CHUNK
                raise EncodingError(ERR_WAV_TRUNCATED_DATA_CHUNK)

            # ensure footer validates correctly
            try:
                validate_footer(footer, data_bytes_written)
            except ValueError as err:
                raise EncodingError(str(err))

            # ensure total size is correct
            if (len(header) + data_size + len(footer)) != total_size:
                from audiotools.text import ERR_WAV_INVALID_SIZE
                raise EncodingError(ERR_WAV_INVALID_SIZE)

            return cls(filename)
        except (ValueError, IOError) as msg:
            counter.close()
            cls.__unlink__(filename)
            raise EncodingError(str(msg))
        except Exception as err:
            counter.close()
            cls.__unlink__(filename)
            raise err

    def blocks(self, reader=None):
        """yields (length, reader) tuples of WavPack frames

        length is the total length of all the substreams
        reader is a BitstreamReader which can be parsed
        """

        def blocks_iter(reader):
            try:
                while True:
                    (wvpk, block_size) = reader.parse("4b 32u 192p")
                    if wvpk == b"wvpk":
                        yield (block_size - 24,
                               reader.substream(block_size - 24))
                    else:
                        return
            except IOError:
                return

        if reader is None:
            from audiotools.bitstream import BitstreamReader

            with BitstreamReader(open(self.filename, "rb"), True) as reader:
                for block in blocks_iter(reader):
                    yield block
        else:
            for block in blocks_iter(reader):
                yield block

    def sub_blocks(self, reader=None):
        """yields (function, nondecoder, data_size, data) tuples

        function is an integer
        nondecoder is a boolean indicating non-decoder data
        data is a BitstreamReader which can be parsed
        """

        for (block_size, block_data) in self.blocks(reader):
            while block_size > 0:
                (metadata_function,
                 nondecoder_data,
                 actual_size_1_less,
                 large_block) = block_data.parse("5u 1u 1u 1u")

                if large_block:
                    sub_block_size = block_data.read(24)
                    block_size -= 4
                else:
                    sub_block_size = block_data.read(8)
                    block_size -= 2

                if actual_size_1_less:
                    yield (metadata_function,
                           nondecoder_data,
                           sub_block_size * 2 - 1,
                           block_data.substream(sub_block_size * 2 - 1))
                    block_data.skip(8)
                else:
                    yield (metadata_function,
                           nondecoder_data,
                           sub_block_size * 2,
                           block_data.substream(sub_block_size * 2))

                block_size -= sub_block_size * 2

    def __read_info__(self):
        from audiotools.bitstream import BitstreamReader
        from audiotools import ChannelMask

        with BitstreamReader(open(self.filename, "rb"), True) as reader:
            pos = reader.getpos()

            (block_id,
             total_samples,
             bits_per_sample,
             mono_output,
             initial_block,
             final_block,
             sample_rate) = reader.parse(
                "4b 64p 32u 64p 2u 1u 8p 1u 1u 5p 5p 4u 37p")

            if block_id != b"wvpk":
                from audiotools.text import ERR_WAVPACK_INVALID_HEADER
                raise InvalidWavPack(ERR_WAVPACK_INVALID_HEADER)

            if sample_rate != 0xF:
                self.__samplerate__ = WavPackAudio.SAMPLING_RATE[sample_rate]
            else:
                # if unknown, pull from SAMPLE_RATE sub-block
                for (block_id,
                     nondecoder,
                     data_size,
                     data) in self.sub_blocks(reader):
                    if (block_id == 0x7) and nondecoder:
                        self.__samplerate__ = data.read(data_size * 8)
                        break
                else:
                    # no SAMPLE RATE sub-block found
                    # so pull info from FMT chunk
                    reader.setpos(pos)
                    (self.__samplerate__,) = self.fmt_chunk(reader).parse(
                        "32p 32u")

            self.__bitspersample__ = [8, 16, 24, 32][bits_per_sample]
            self.__total_frames__ = total_samples

            if initial_block and final_block:
                if mono_output:
                    self.__channels__ = 1
                    self.__channel_mask__ = ChannelMask(0x4)
                else:
                    self.__channels__ = 2
                    self.__channel_mask__ = ChannelMask(0x3)
            else:
                # if not mono or stereo, pull from CHANNEL INFO sub-block
                reader.setpos(pos)
                for (block_id,
                     nondecoder,
                     data_size,
                     data) in self.sub_blocks(reader):
                    if (block_id == 0xD) and not nondecoder:
                        self.__channels__ = data.read(8)
                        self.__channel_mask__ = ChannelMask(
                            data.read((data_size - 1) * 8))
                        break
                else:
                    # no CHANNEL INFO sub-block found
                    # so pull info from FMT chunk
                    reader.setpos(pos)
                    fmt = self.fmt_chunk(reader)
                    compression_code = fmt.read(16)
                    self.__channels__ = fmt.read(16)
                    if compression_code == 1:
                        # this is theoretically possible
                        # with very old .wav files,
                        # but shouldn't happen in practice
                        self.__channel_mask__ = \
                            {1: ChannelMask.from_fields(front_center=True),
                             2: ChannelMask.from_fields(front_left=True,
                                                        front_right=True),
                             3: ChannelMask.from_fields(front_left=True,
                                                        front_right=True,
                                                        front_center=True),
                             4: ChannelMask.from_fields(front_left=True,
                                                        front_right=True,
                                                        back_left=True,
                                                        back_right=True),
                             5: ChannelMask.from_fields(front_left=True,
                                                        front_right=True,
                                                        back_left=True,
                                                        back_right=True,
                                                        front_center=True),
                             6: ChannelMask.from_fields(front_left=True,
                                                        front_right=True,
                                                        back_left=True,
                                                        back_right=True,
                                                        front_center=True,
                                                        low_frequency=True)
                             }.get(self.__channels__, ChannelMask(0))
                    elif compression_code == 0xFFFE:
                        fmt.skip(128)
                        mask = fmt.read(32)
                        self.__channel_mask__ = ChannelMask(mask)
                    else:
                        from audiotools.text import ERR_WAVPACK_UNSUPPORTED_FMT
                        raise InvalidWavPack(ERR_WAVPACK_UNSUPPORTED_FMT)

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

    def seekable(self):
        """returns True if the file is seekable"""

        return True

    @classmethod
    def supports_from_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        try:
            from audiotools.encoders import encode_wavpack
            return True
        except ImportError:
            return False

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
        and returns a new WavPackAudio object"""

        from audiotools.encoders import encode_wavpack
        from audiotools import BufferedPCMReader
        from audiotools import CounterPCMReader
        from audiotools import EncodingError
        from audiotools import __default_quality__

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        counter = CounterPCMReader(pcmreader)

        try:
            (encode_wavpack if encoding_function is None
             else encoding_function)(
                filename=filename,
                pcmreader=counter,
                total_pcm_frames=(total_pcm_frames if
                                  total_pcm_frames is not None else 0),
                compression=compression)
            counter.close()
        except (ValueError, IOError) as msg:
            counter.close()
            cls.__unlink__(filename)
            raise EncodingError(str(msg))
        except Exception:
            counter.close()
            cls.__unlink__(filename)
            raise

        # ensure actual total PCM frames matches argument, if any
        if (((total_pcm_frames is not None) and
             (counter.frames_written != total_pcm_frames))):
            cls.__unlink__(filename)
            from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
            raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

        return cls(filename)

    @classmethod
    def supports_to_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        try:
            from audiotools.decoders import WavPackDecoder
            return True
        except ImportError:
            return False

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from audiotools.decoders import WavPackDecoder
        from audiotools import PCMReaderError

        try:
            return WavPackDecoder(self.filename)
        except IOError as err:
            return PCMReaderError(error_message=str(err),
                                  sample_rate=self.__samplerate__,
                                  channels=self.__channels__,
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.__bitspersample__)

    def fmt_chunk(self, reader=None):
        """returns the 'fmt' chunk as a BitstreamReader"""

        for (block_id,
             nondecoder,
             data_size,
             data) in self.sub_blocks(reader):
            if (block_id == 1) and nondecoder:
                (riff, wave) = data.parse("4b 32p 4b")
                if (riff != b"RIFF") or (wave != b"WAVE"):
                    from audiotools.text import ERR_WAVPACK_INVALID_FMT
                    raise InvalidWavPack(ERR_WAVPACK_INVALID_FMT)
                else:
                    while True:
                        (chunk_id, chunk_size) = data.parse("4b 32u")
                        if chunk_id == b"fmt ":
                            return data.substream(chunk_size)
                        elif chunk_id == b"data":
                            from audiotools.text import ERR_WAVPACK_INVALID_FMT
                            raise InvalidWavPack(ERR_WAVPACK_INVALID_FMT)
                        else:
                            data.skip_bytes(chunk_size)
        else:
            from audiotools.text import ERR_WAVPACK_NO_FMT
            raise InvalidWavPack(ERR_WAVPACK_NO_FMT)

    @classmethod
    def supports_cuesheet(cls):
        return True

    def get_cuesheet(self):
        """returns the embedded Cuesheet-compatible object, or None

        raises IOError if a problem occurs when reading the file"""

        from audiotools import cue as cue
        from audiotools import SheetException

        metadata = self.get_metadata()

        if (metadata is not None):
            try:
                if (b'Cuesheet' in metadata.keys()):
                    return cue.read_cuesheet_string(
                        metadata[b'Cuesheet'].__unicode__())
                elif (b'CUESHEET' in metadata.keys()):
                    return cue.read_cuesheet_string(
                        metadata[b'CUESHEET'].__unicode__())
                else:
                    return None;
            except SheetException:
                # unlike FLAC, just because a cuesheet is embedded
                # does not mean it is compliant
                return None
        else:
            return None

    def set_cuesheet(self, cuesheet):
        """imports cuesheet data from a Sheet object

        Raises IOError if an error occurs setting the cuesheet"""

        import os.path
        from io import BytesIO
        from audiotools import (MetaData, Filename, FS_ENCODING)
        from audiotools import cue as cue
        from audiotools.cue import write_cuesheet
        from audiotools.ape import ApeTag

        if cuesheet is None:
            return self.delete_cuesheet()

        metadata = self.get_metadata()
        if metadata is None:
            metadata = ApeTag([])

        cuesheet_data = BytesIO()
        write_cuesheet(cuesheet,
                       u"%s" % (Filename(self.filename).basename(),),
                       cuesheet_data)

        metadata[b'Cuesheet'] = ApeTag.ITEM.string(
            b'Cuesheet',
            cuesheet_data.getvalue().decode(FS_ENCODING, 'replace'))

        self.update_metadata(metadata)

    def delete_cuesheet(self):
        """deletes embedded Sheet object, if any

        Raises IOError if a problem occurs when updating the file"""

        metadata = self.get_metadata()
        if ((metadata is not None) and isinstance(metadata, ApeTag)):
            if b"Cuesheet" in metadata.keys():
                del(metadata[b"Cuesheet"])
                self.update_metadata(metadata)
            elif b"CUESHEET" in metadata.keys():
                del(metadata[b"CUESHEET"])
                self.update_metadata(metadata)
