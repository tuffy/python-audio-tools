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

from audiotools import (AudioFile, ChannelMask, InvalidFile,
                        WaveContainer, AiffContainer)

import os.path


class InvalidShorten(InvalidFile):
    pass


class ShortenAudio(WaveContainer, AiffContainer):
    """a Shorten audio file"""

    SUFFIX = "shn"
    NAME = SUFFIX
    DESCRIPTION = u"Shorten"

    def __init__(self, filename):
        """filename is a plain string"""

        from audiotools.bitstream import BitstreamReader
        from audiotools import ChannelMask
        import cStringIO

        AudioFile.__init__(self, filename)
        try:
            f = open(filename, 'rb')
        except IOError as msg:
            raise InvalidShorten(str(msg))

        reader = BitstreamReader(f, 0)
        try:
            if (reader.parse("4b 8u") != ["ajkg", 2]):
                raise InvalidShorten("invalid Shorten header")
        except IOError:
            raise InvalidShorten("invalid Shorten header")

        def read_unsigned(r, c):
            MSB = r.unary(1)
            LSB = r.read(c)
            return MSB * 2 ** c + LSB

        def read_long(r):
            return read_unsigned(r, read_unsigned(r, 2))

        # populate channels and bits_per_sample from Shorten header
        (file_type,
         self.__channels__,
         block_length,
         max_LPC,
         number_of_means,
         bytes_to_skip) = [read_long(reader) for i in range(6)]

        if ((1 <= file_type) and (file_type <= 2)):
            self.__bits_per_sample__ = 8
        elif ((3 <= file_type) and (file_type <= 6)):
            self.__bits_per_sample__ = 16
        else:
            # FIXME
            raise InvalidShorten("unsupported Shorten file type")

        # setup some default dummy metadata
        self.__sample_rate__ = 44100
        if (self.__channels__ == 1):
            self.__channel_mask__ = ChannelMask(0x4)
        elif (self.__channels__ == 2):
            self.__channel_mask__ = ChannelMask(0x3)
        else:
            self.__channel_mask__ = ChannelMask(0)
        self.__total_frames__ = 0

        # populate sample_rate and total_frames from first VERBATIM command
        command = read_unsigned(reader, 2)
        if (command == 9):
            verbatim_bytes = "".join([chr(read_unsigned(reader, 8) & 0xFF)
                                      for i in range(read_unsigned(reader,
                                                                   5))])
            try:
                wave = BitstreamReader(cStringIO.StringIO(verbatim_bytes), 1)
                header = wave.read_bytes(12)
                if (header.startswith("RIFF") and header.endswith("WAVE")):
                    # got RIFF/WAVE header, so parse wave blocks as needed
                    total_size = len(verbatim_bytes) - 12
                    while (total_size >= 8):
                        (chunk_id, chunk_size) = wave.parse("4b 32u")
                        total_size -= 8
                        if (chunk_id == 'fmt '):
                            from audiotools.wav import parse_fmt

                            (channels,
                             self.__sample_rate__,
                             bits_per_sample,
                             self.__channel_mask__) = parse_fmt(
                                wave.substream(chunk_size))
                        elif (chunk_id == 'data'):
                            self.__total_frames__ = \
                                (chunk_size //
                                 (self.__channels__ *
                                  (self.__bits_per_sample__ // 8)))
                        else:
                            if (chunk_size % 2):
                                wave.read_bytes(chunk_size + 1)
                                total_size -= (chunk_size + 1)
                            else:
                                wave.read_bytes(chunk_size)
                                total_size -= chunk_size
            except (IOError, ValueError):
                pass

            try:
                aiff = BitstreamReader(cStringIO.StringIO(verbatim_bytes), 0)
                header = aiff.read_bytes(12)
                if (header.startswith("FORM") and header.endswith("AIFF")):
                    # got FORM/AIFF header, so parse aiff blocks as needed
                    total_size = len(verbatim_bytes) - 12
                    while (total_size >= 8):
                        (chunk_id, chunk_size) = aiff.parse("4b 32u")
                        total_size -= 8
                        if (chunk_id == 'COMM'):
                            from audiotools.aiff import parse_comm

                            (channels,
                             total_sample_frames,
                             bits_per_sample,
                             self.__sample_rate__,
                             self.__channel_mask__) = parse_comm(
                                aiff.substream(chunk_size))
                        elif (chunk_id == 'SSND'):
                            # subtract 8 bytes for "offset" and "block size"
                            self.__total_frames__ = \
                                ((chunk_size - 8) //
                                 (self.__channels__ *
                                  (self.__bits_per_sample__ // 8)))
                        else:
                            if (chunk_size % 2):
                                aiff.read_bytes(chunk_size + 1)
                                total_size -= (chunk_size + 1)
                            else:
                                aiff.read_bytes(chunk_size)
                                total_size -= chunk_size
            except IOError:
                pass

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        return self.__channel_mask__

    def lossless(self):
        """returns True"""

        return True

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__total_frames__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from audiotools.decoders import SHNDecoder
        from audiotools import PCMReaderError

        try:
            return SHNDecoder(open(self.filename, "rb"))
        except (IOError, ValueError) as msg:
            # these may not be accurate if the Shorten file is broken
            # but if it is broken, there'll be no way to
            # cross-check the results anyway
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=44100,
                                  channels=2,
                                  channel_mask=0x3,
                                  bits_per_sample=16)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None,
                 total_pcm_frames=None,
                 block_size=256,
                 encoding_function=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new ShortenAudio object"""

        # can't build artificial header because we don't know
        # how long the PCMReader will be and there's no way
        # to go back and write one later because all the byte values
        # are stored variable-sized
        # so we have to build a temporary Wave file instead

        from audiotools import UnsupportedBitsPerSample

        if (pcmreader.bits_per_sample not in (8, 16)):
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        if (total_pcm_frames is not None):
            from audiotools.wav import wave_header

            return cls.from_wave(filename,
                                 wave_header(pcmreader.sample_rate,
                                             pcmreader.channels,
                                             pcmreader.channel_mask,
                                             pcmreader.bits_per_sample,
                                             total_pcm_frames),
                                 pcmreader,
                                 chr(0) * (((pcmreader.bits_per_sample // 8) *
                                            pcmreader.channels *
                                            total_pcm_frames) % 2),
                                 compression,
                                 block_size,
                                 encoding_function)
        else:
            from audiotools import WaveAudio
            import tempfile

            f = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                w = WaveAudio.from_pcm(f.name, pcmreader)
                (header, footer) = w.wave_header_footer()
                return cls.from_wave(filename,
                                     header,
                                     w.to_pcm(),
                                     footer,
                                     compression,
                                     block_size,
                                     encoding_function)
            finally:
                if (os.path.isfile(f.name)):
                    f.close()
                else:
                    f.close_called = True

    def has_foreign_wave_chunks(self):
        """returns True if the audio file contains non-audio RIFF chunks

        during transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks"""

        from audiotools import decoders
        from audiotools import bitstream
        import cStringIO

        try:
            (head, tail) = decoders.SHNDecoder(
                open(self.filename, "rb")).pcm_split()
            header = bitstream.BitstreamReader(cStringIO.StringIO(head), 1)
            (RIFF, SIZE, WAVE) = header.parse("4b 32u 4b")
            if ((RIFF != 'RIFF') or (WAVE != 'WAVE')):
                return False

            # if the tail has room for chunks, there must be some foreign ones
            if (len(tail) >= 8):
                return True

            # otherwise, check the header for foreign chunks
            total_size = len(head) - bitstream.format_byte_size("4b 32u 4b")
            while (total_size >= 8):
                (chunk_id, chunk_size) = header.parse("4b 32u")
                total_size -= bitstream.format_byte_size("4b 32u")
                if (chunk_id not in ('fmt ', 'data')):
                    return True
                else:
                    if (chunk_size % 2):
                        header.skip_bytes(chunk_size + 1)
                        total_size -= chunk_size + 1
                    else:
                        header.skip_bytes(chunk_size)
                        total_size -= chunk_size
            else:
                # no foreign chunks found
                return False
        except IOError:
            return False

    def wave_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        may raise ValueError if there's a problem with
        the header or footer data
        may raise IOError if there's a problem reading
        header or footer data from the file"""

        from audiotools import decoders
        from audiotools import bitstream
        import cStringIO

        (head, tail) = decoders.SHNDecoder(
            open(self.filename, "rb")).pcm_split()
        header = bitstream.BitstreamReader(cStringIO.StringIO(head), 1)
        (RIFF, SIZE, WAVE) = header.parse("4b 32u 4b")
        if ((RIFF != 'RIFF') or (WAVE != 'WAVE')):
            raise ValueError("invalid wave header")
        else:
            return (head, tail)

    @classmethod
    def from_wave(cls, filename, header, pcmreader, footer, compression=None,
                  block_size=256, encoding_function=None):
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

        from audiotools import (CounterPCMReader,
                                BufferedPCMReader,
                                UnsupportedBitsPerSample,
                                EncodingError)
        from audiotools.wav import (validate_header, validate_footer)

        if (encoding_function is None):
            from audiotools.encoders import encode_shn
        else:
            encode_shn = encoding_function

        if (pcmreader.bits_per_sample not in (8, 16)):
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        # ensure header is valid
        try:
            (total_size, data_size) = validate_header(header)
        except ValueError as err:
            raise EncodingError(str(err))

        counter = CounterPCMReader(pcmreader)

        try:
            if (len(footer) == 0):
                encode_shn(filename=filename,
                           pcmreader=BufferedPCMReader(counter),
                           is_big_endian=False,
                           signed_samples=pcmreader.bits_per_sample == 16,
                           header_data=header,
                           block_size=block_size)
            else:
                encode_shn(filename=filename,
                           pcmreader=BufferedPCMReader(counter),
                           is_big_endian=False,
                           signed_samples=pcmreader.bits_per_sample == 16,
                           header_data=header,
                           footer_data=footer,
                           block_size=block_size)

            data_bytes_written = counter.bytes_written()

            # ensure output data size matches the "data" chunk's size
            if (data_size != data_bytes_written):
                from audiotools.text import ERR_WAV_TRUNCATED_DATA_CHUNK
                raise EncodingError(ERR_WAV_TRUNCATED_DATA_CHUNK)

            # ensure footer validates correctly
            try:
                validate_footer(footer, data_bytes_written)
            except ValueError as err:
                raise EncodingError(str(err))

            # ensure total size is correct
            if ((len(header) + data_size + len(footer)) != total_size):
                from audiotools.text import ERR_WAV_INVALID_SIZE
                raise EncodingError(ERR_WAV_INVALID_SIZE)

            return cls(filename)
        except IOError as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception as err:
            cls.__unlink__(filename)
            raise err

    def has_foreign_aiff_chunks(self):
        """returns True if the audio file contains non-audio AIFF chunks

        during transcoding, if the source audio file has foreign AIFF chunks
        and the target audio format supports foreign AIFF chunks,
        conversion should be routed through .aiff conversion
        to avoid losing those chunks"""

        from audiotools import decoders
        from audiotools import bitstream
        import cStringIO

        try:
            (head, tail) = decoders.SHNDecoder(
                open(self.filename, "rb")).pcm_split()
            header = bitstream.BitstreamReader(cStringIO.StringIO(head), 0)
            (FORM, SIZE, AIFF) = header.parse("4b 32u 4b")
            if ((FORM != 'FORM') or (AIFF != 'AIFF')):
                return False

            # if the tail has room for chunks, there must be some foreign ones
            if (len(tail) >= 8):
                return True

            # otherwise, check the header for foreign chunks
            total_size = len(head) - bitstream.format_byte_size("4b 32u 4b")
            while (total_size >= 8):
                (chunk_id, chunk_size) = header.parse("4b 32u")
                total_size -= bitstream.format_byte_size("4b 32u")
                if (chunk_id not in ('COMM', 'SSND')):
                    return True
                else:
                    if (chunk_size % 2):
                        header.skip_bytes(chunk_size + 1)
                        total_size -= chunk_size + 1
                    else:
                        header.skip_bytes(chunk_size)
                        total_size -= chunk_size
            else:
                # no foreign chunks found
                return False
        except IOError:
            return False

    def aiff_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        if self.has_foreign_aiff_chunks() is False,
        may raise ValueError if the file has no header and footer
        for any reason"""

        from audiotools import decoders
        from audiotools import bitstream
        import cStringIO

        (head, tail) = decoders.SHNDecoder(
            open(self.filename, "rb")).pcm_split()
        header = bitstream.BitstreamReader(cStringIO.StringIO(head), 0)
        (FORM, SIZE, AIFF) = header.parse("4b 32u 4b")
        if ((FORM != 'FORM') or (AIFF != 'AIFF')):
            raise ValueError("invalid AIFF header")
        else:
            return (head, tail)

    @classmethod
    def from_aiff(cls, filename, header, pcmreader, footer, compression=None,
                  block_size=256, encoding_function=None):
        """encodes a new file from AIFF data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AiffAudio object

        header + pcm data + footer should always result
        in the original AIFF file being restored
        without need for any padding bytes

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        from audiotools import (CounterPCMReader,
                                BufferedPCMReader,
                                UnsupportedBitsPerSample,
                                EncodingError)
        from audiotools.aiff import (validate_header, validate_footer)

        if (encoding_function is None):
            from audiotools.encoders import encode_shn
        else:
            encode_shn = encoding_function

        if (pcmreader.bits_per_sample not in (8, 16)):
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        # ensure header is valid
        try:
            (total_size, ssnd_size) = validate_header(header)
        except ValueError as err:
            raise EncodingError(str(err))

        counter = CounterPCMReader(pcmreader)

        try:
            if (len(footer) == 0):
                encode_shn(filename=filename,
                           pcmreader=BufferedPCMReader(counter),
                           is_big_endian=True,
                           signed_samples=True,
                           header_data=header,
                           block_size=block_size)
            else:
                encode_shn(filename=filename,
                           pcmreader=BufferedPCMReader(counter),
                           is_big_endian=True,
                           signed_samples=True,
                           header_data=header,
                           footer_data=footer,
                           block_size=block_size)

            ssnd_bytes_written = counter.bytes_written()

            # ensure output data size matches the "SSND" chunk's size
            if (ssnd_size != ssnd_bytes_written):
                from audiotools.text import ERR_AIFF_TRUNCATED_SSND_CHUNK
                raise EncodingError(ERR_AIFF_TRUNCATED_SSND_CHUNK)

            # ensure footer validates correctly
            try:
                validate_footer(footer, ssnd_bytes_written)
            except ValueError as err:
                raise EncodingError(str(err))

            # ensure total size is correct
            if ((len(header) + ssnd_size + len(footer)) != total_size):
                from audiotools.text import ERR_AIFF_INVALID_SIZE
                raise EncodingError(ERR_AIFF_INVALID_SIZE)

            return cls(filename)
        except IOError as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception as err:
            cls.__unlink__(filename)
            raise err

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """encodes a new AudioFile from existing AudioFile

        take a filename string, target class and optional compression string
        encodes a new AudioFile in the target class and returns
        the resulting object
        may raise EncodingError if some problem occurs during encoding"""

        # A Shorten file cannot contain both RIFF and AIFF chunks
        # at the same time.

        from audiotools import WaveAudio
        from audiotools import AiffAudio
        from audiotools import to_pcm_progress

        if ((self.has_foreign_wave_chunks() and
             hasattr(target_class, "from_wave") and
             callable(target_class.from_wave))):
            return WaveContainer.convert(self,
                                         target_path,
                                         target_class,
                                         compression,
                                         progress)
        elif (self.has_foreign_aiff_chunks() and
              hasattr(target_class, "from_aiff") and
              callable(target_class.from_aiff)):
            return AiffContainer.convert(self,
                                         target_path,
                                         target_class,
                                         compression,
                                         progress)
        else:
            return target_class.from_pcm(
                target_path,
                to_pcm_progress(self, progress),
                compression,
                total_pcm_frames=self.total_frames())
