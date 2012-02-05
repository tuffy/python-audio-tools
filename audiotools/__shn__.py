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

from audiotools import (AudioFile, ChannelMask, PCMReader,
                        transfer_framelist_data, WaveAudio,
                        AiffAudio, cStringIO, EncodingError,
                        UnsupportedBitsPerSample, InvalidFile,
                        PCMReaderError,
                        WaveContainer, AiffContainer, to_pcm_progress,
                        parse_fmt, parse_comm)

import os.path


class InvalidShorten(InvalidFile):
    pass


class ShortenAudio(WaveContainer, AiffContainer):
    """A Shorten audio file."""

    SUFFIX = "shn"
    NAME = SUFFIX

    def __init__(self, filename):
        """filename is a plain string."""

        from audiotools.bitstream import BitstreamReader

        AudioFile.__init__(self, filename)
        try:
            f = open(filename, 'rb')
        except IOError, msg:
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

        #populate channels and bits_per_sample from Shorten header
        (file_type,
         self.__channels__,
         block_length,
         max_LPC,
         number_of_means,
         bytes_to_skip) = [read_long(reader) for i in xrange(6)]

        if ((1 <= file_type) and (file_type <= 2)):
            self.__bits_per_sample__ = 8
        elif ((3 <= file_type) and (file_type <= 6)):
            self.__bits_per_sample__ = 16
        else:
            raise InvalidShorten("unsupported Shorten file type")

        #setup some default dummy metadata
        self.__sample_rate__ = 44100
        if (self.__channels__ == 1):
            self.__channel_mask__ = ChannelMask(0x4)
        elif (self.__channels__ == 2):
            self.__channel_mask__ = ChannelMask(0x3)
        else:
            self.__channel_mask__ = ChannelMask(0)
        self.__total_frames__ = 0

        #populate sample_rate and total_frames from first VERBATIM command
        command = read_unsigned(reader, 2)
        if (command == 9):
            verbatim_bytes = "".join([chr(read_unsigned(reader, 8) & 0xFF)
                                      for i in xrange(
                        read_unsigned(reader, 5))])
            try:
                wave = BitstreamReader(cStringIO.StringIO(verbatim_bytes), 1)
                header = wave.read_bytes(12)
                if (header.startswith("RIFF") and header.endswith("WAVE")):
                    #got RIFF/WAVE header, so parse wave blocks as needed
                    total_size = len(verbatim_bytes) - 12
                    while (total_size >= 8):
                        (chunk_id, chunk_size) = wave.parse("4b 32u")
                        total_size -= 8
                        if (chunk_id == 'fmt '):
                            (channels,
                             self.__sample_rate__,
                             bits_per_sample,
                             self.__channel_mask__) = parse_fmt(
                                wave.substream(chunk_size))
                        elif (chunk_id == 'data'):
                            self.__total_frames__ = \
                                (chunk_size /
                                 (self.__channels__ *
                                  (self.__bits_per_sample__ / 8)))
                        else:
                            if (chunk_size % 2):
                                wave.read_bytes(chunk_size + 1)
                                total_size -= (chunk_size + 1)
                            else:
                                wave.read_bytes(chunk_size)
                                total_size -= chunk_size
            except (IOError,ValueError):
                pass

            try:
                aiff = BitstreamReader(cStringIO.StringIO(verbatim_bytes), 0)
                header = aiff.read_bytes(12)
                if (header.startswith("FORM") and header.endswith("AIFF")):
                    #got FORM/AIFF header, so parse aiff blocks as needed
                    total_size = len(verbatim_bytes) - 12
                    while (total_size >= 8):
                        (chunk_id, chunk_size) = aiff.parse("4b 32u")
                        total_size -= 8
                        if (chunk_id == 'COMM'):
                            (channels,
                             total_sample_frames,
                             bits_per_sample,
                             self.__sample_rate__,
                             self.__channel_mask__) = parse_comm(
                                aiff.substream(chunk_size))
                        elif (chunk_id == 'SSND'):
                            #subtract 8 bytes for "offset" and "block size"
                            self.__total_frames__ = \
                                ((chunk_size - 8) /
                                 (self.__channels__ *
                                  (self.__bits_per_sample__ / 8)))
                        else:
                            if (chunk_size % 2):
                                aiff.read_bytes(chunk_size + 1)
                                total_size -= (chunk_size + 1)
                            else:
                                aiff.read_bytes(chunk_size)
                                total_size -= chunk_size
            except IOError:
                pass

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        return (file.read(4) == 'ajkg') and (ord(file.read(1)) == 2)

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bits_per_sample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        return self.__channel_mask__

    def lossless(self):
        """Returns True."""

        return True

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__total_frames__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__sample_rate__

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        try:
            from . import decoders

            return decoders.SHNDecoder(self.filename)
        except (IOError, ValueError), msg:
            #these may not be accurate if the Shorten file is broken
            #but if it is broken, there'll be no way to
            #cross-check the results anyway
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=44100,
                                  channels=2,
                                  channel_mask=0x3,
                                  bits_per_sample=16)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None,
                 block_size=256):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new ShortenAudio object."""

        if (pcmreader.bits_per_sample not in (8, 16)):
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        import tempfile

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            w = WaveAudio.from_pcm(f.name, pcmreader)
            return cls.from_wave(filename, f.name, compression, block_size)
        finally:
            if (os.path.isfile(f.name)):
                f.close()
            else:
                f.close_called = True

    def to_wave(self, wave_filename, progress=None):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""


        from . import decoders

        try:
            (head, tail) = decoders.SHNDecoder(self.filename).pcm_split()
        except IOError,err:
            raise EncodingError(str(err))

        if ((head[0:4] == 'RIFF') and (head[8:12] == 'WAVE')):
            try:
                f = open(wave_filename, 'wb')
            except IOError, msg:
                raise EncodingError(str(msg))

            try:
                f.write(head)
                total_frames = self.total_frames()
                current_frames = 0
                decoder = decoders.SHNDecoder(self.filename)
                frame = decoder.read(4096)
                while (len(frame) > 0):
                    f.write(frame.to_bytes(False, self.bits_per_sample() > 8))
                    current_frames += frame.frames
                    if (progress is not None):
                        progress(current_frames, total_frames)
                    frame = decoder.read(4096)
                f.write(tail)
                f.close()
            except IOError, msg:
                self.__unlink__(wave_filename)
                raise EncodingError(str(msg))
        else:
            WaveAudio.from_pcm(wave_filename, to_pcm_progress(self, progress))

    def to_aiff(self, aiff_filename, progress=None):
        """Writes the contents of this file to the given .aiff filename string.

        Raises EncodingError if some error occurs during decoding."""

        from . import decoders

        try:
            (head, tail) = decoders.SHNDecoder(self.filename).pcm_split()
        except IOError:
            raise EncodingError(str(msg))

        if ((header[0:4] == 'FORM') and (head[8:12] == 'AIFF')):
            try:
                f = open(aiff_filename, 'wb')
            except IOError, msg:
                raise EncodingError(str(msg))

            try:
                f.write(head)
                total_frames = self.total_frames()
                current_frames = 0
                decoder = decoders.SHNDecoder(self.filename)
                frame = decoder.read(4096)
                while (len(frame) > 0):
                    f.write(frame.to_bytes(False, self.bits_per_sample() > 8))
                    current_frames += frame.frames
                    if (progress is not None):
                        progress(current_frames, total_frames)
                    frame = decoder.read(4096)
                f.write(tail)
                f.close()
            except IOError, msg:
                self.__unlink__(aiff_filename)
                raise EncodingError(str(msg))
        else:
            AiffAudio.from_pcm(aiff_filename, to_pcm_progress(self, progress))

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None,
                  block_size=256, progress=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new ShortenAudio object."""

        wave = WaveAudio(wave_filename)

        if (wave.bits_per_sample() not in (8, 16)):
            raise UnsupportedBitsPerSample(filename, wave.bits_per_sample())

        (head, tail) = wave.pcm_split()

        from .encoders import encode_shn

        try:
            if (len(tail) == 0):
                encode_shn(filename=filename,
                           pcmreader=to_pcm_progress(wave, progress),
                           header_data=head,
                           block_size=block_size)
            else:
                encode_shn(filename=filename,
                           pcmreader=to_pcm_progress(wave, progress),
                           header_data=head,
                           footer_data=tail,
                           block_size=block_size)

            return cls(filename)
        except IOError, err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            cls.__unlink__(filename)
            raise err

    @classmethod
    def from_aiff(cls, filename, aiff_filename, compression=None,
                  block_size=256, progress=None):
        """Encodes a new AudioFile from an existing .aiff file.

        Takes a filename string, aiff_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the aiff's data
        at the given filename with the specified compression level
        and returns a new ShortenAudio object."""

        aiff = AiffAudio(aiff_filename)

        if (aiff.bits_per_sample() not in (8, 16)):
            raise UnsupportedBitsPerSample(filename, aiff.bits_per_sample())

        (head, tail) = aiff.pcm_split()
        if (len(tail) > 0):
            blocks = [head, None, tail]
        else:
            blocks = [head, None]

        import audiotools.encoders

        try:
            audiotools.encoders.encode_shn(
                filename=filename,
                pcmreader=to_pcm_progress(aiff, progress),
                block_size=block_size,
                file_type={8: 1,  # 8-bit AIFF seems to be signed
                           16: 3}[aiff.bits_per_sample()],
                verbatim_chunks=blocks)

            return cls(filename)
        except IOError, err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            cls.__unlink__(filename)
            raise err

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """Encodes a new AudioFile from existing AudioFile.

        Take a filename string, target class and optional compression string.
        Encodes a new AudioFile in the target class and returns
        the resulting object.
        Metadata is not copied during conversion, but embedded
        RIFF chunks are (if any).
        May raise EncodingError if some problem occurs during encoding."""

        #Note that a Shorten file cannot contain
        #both RIFF chunks and AIFF chunks at the same time.

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

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        from . import decoders
        from . import bitstream

        try:
            (head, tail) = decoders.SHNDecoder(self.filename).pcm_split()
            header = bitstream.BitstreamReader(cStringIO.StringIO(head), 1)
            (RIFF, SIZE, WAVE) = header.parse("4b 32u 4b")
            if ((RIFF != 'RIFF') or (WAVE != 'WAVE')):
                return False

            #if the tail has room for chunks, there must be some foreign ones
            if (len(tail) >= 8):
                return True

            #otherwise, check the header for foreign chunks
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
                #no foreign chunks found
                return False
        except IOError:
            return False


    def has_foreign_aiff_chunks(self):
        """Returns True if the audio file contains non-audio AIFF chunks.

        During transcoding, if the source audio file has foreign AIFF chunks
        and the target audio format supports foreign AIFF chunks,
        conversion should be routed through .aiff conversion
        to avoid losing those chunks."""

        from . import decoders
        from . import bitstream

        try:
            (head, tail) = decoders.SHNDecoder(self.filename).pcm_split()
            header = bitstream.BitstreamReader(cStringIO.StringIO(head), 1)
            (FORM, SIZE, AIFF) = header.parse("4b 32u 4b")
            if ((FORM != 'FORM') or (AIFF != 'AIFF')):
                return False

            #if the tail has room for chunks, there must be some foreign ones
            if (len(tail) >= 8):
                return True

            #otherwise, check the header for foreign chunks
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
                #no foreign chunks found
                return False
        except IOError:
            return False
