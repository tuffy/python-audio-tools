#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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
                        PCMReaderError)

import audiotools.decoders
import os.path


class InvalidShorten(InvalidFile):
    pass


class ShortenAudio(AudioFile):
    """A Shorten audio file."""

    SUFFIX = "shn"
    NAME = SUFFIX

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)
        try:
            f = open(filename, 'rb')
        except IOError, msg:
            raise InvalidShorten(str(msg))
        try:
            if (not ShortenAudio.is_type(f)):
                raise InvalidShorten(_(u'Shorten header not detected'))
        finally:
            f.close()

        #Why not call __populate_metadata__ here and raise InvalidShorten
        #if it errors out?
        #The problem is that __populate_metadata__ needs to walk
        #through the *entire* file in order to calculate total PCM frames
        #and so on.
        #That's an expensive operation to perform at init-time
        #so it's better to postpone it to an on-demand fetch.

    def __populate_metadata__(self):
        #set up some default values
        self.__bits_per_sample__ = 16
        self.__channels__ = 2
        self.__channel_mask__ = 0x3
        self.__sample_rate__ = 44100
        self.__total_frames__ = 0
        self.__blocks__ = []
        self.__format__ = None

        #grab a few pieces of technical metadata from the Shorten file itself
        #which requires a dry-run through the decoder
        try:
            decoder = audiotools.decoders.SHNDecoder(self.filename)
            try:

                self.__bits_per_sample__ = decoder.bits_per_sample
                self.__channels__ = decoder.channels
                (self.__total_frames__,
                 self.__blocks__) = decoder.metadata()
            finally:
                decoder.close()

            try:
                self.__channel_mask__ = ChannelMask.from_channels(
                    self.__channels__)
            except ValueError:
                self.__channel_mask__ = 0
        except (ValueError, IOError):
            #if we hit an error in SHNDecoder while reading
            #technical metadata, the default values will have to do
            return

        #the remainder requires parsing the file's VERBATIM blocks
        #which may contain Wave, AIFF or Sun AU info
        if (self.__blocks__[0] is not None):
            header = cStringIO.StringIO(self.__blocks__[0])
            for format in WaveAudio, AiffAudio:
                header.seek(0, 0)
                if (format.is_type(header)):
                    self.__format__ = format
                    break
            if (self.__format__ is WaveAudio):
                for (chunk_id, chunk_data) in self.__wave_chunks__():
                    if (chunk_id == 'fmt '):
                        fmt_chunk = WaveAudio.FMT_CHUNK.parse(chunk_data)
                        self.__sample_rate__ = fmt_chunk.sample_rate
                        if (fmt_chunk.compression == 0xFFFE):
                            self.__channel_mask__ = \
                                WaveAudio.fmt_chunk_to_channel_mask(
                                fmt_chunk.channel_mask)
            elif (self.__format__ is AiffAudio):
                for (chunk_id, chunk_data) in self.__aiff_chunks__():
                    if (chunk_id == 'COMM'):
                        comm_chunk = AiffAudio.COMM_CHUNK.parse(chunk_data)
                        self.__sample_rate__ = comm_chunk.sample_rate

    def __wave_chunks__(self):
        total_size = sum([len(block) for block in self.__blocks__
                          if block is not None])
        wave_data = cStringIO.StringIO("".join([block for block in
                                                self.__blocks__
                                                if block is not None]))

        wave_data.read(12)  # skip the RIFFxxxxWAVE header data
        total_size -= 12

        #iterate over all the non-data chunks
        while (total_size > 0):
            header = WaveAudio.CHUNK_HEADER.parse_stream(wave_data)
            total_size -= 8
            if (header.chunk_id != 'data'):
                yield (header.chunk_id, wave_data.read(header.chunk_length))
                total_size -= header.chunk_length
            else:
                continue

    def __aiff_chunks__(self):
        total_size = sum([len(block) for block in self.__blocks__
                          if block is not None])
        aiff_data = cStringIO.StringIO("".join([block for block in
                                                self.__blocks__
                                                if block is not None]))

        aiff_data.read(12)  # skip the FORMxxxxAIFF header data
        total_size -= 12

        #iterate over all the non-ssnd chunks
        while (total_size > 0):
            header = AiffAudio.CHUNK_HEADER.parse_stream(aiff_data)
            total_size -= 8
            if (header.chunk_id != 'SSND'):
                yield (header.chunk_id, aiff_data.read(header.chunk_length))
                total_size -= header.chunk_length
            else:
                #not sure what Shorten does with the first 8 bytes
                #of the SSND chunk
                #it'll be a mess if it turns those into audio data
                continue

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        return (file.read(4) == 'ajkg') and (ord(file.read(1)) == 2)

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        if (not hasattr(self, "__bits_per_sample__")):
            self.__populate_metadata__()
        return self.__bits_per_sample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        if (not hasattr(self, "__channels__")):
            self.__populate_metadata__()
        return self.__channels__

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        if (not hasattr(self, "__channel_mask__")):
            self.__populate_metadata__()
        return self.__channel_mask__

    def lossless(self):
        """Returns True."""

        return True

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        if (not hasattr(self, "__total_frames__")):
            self.__populate_metadata__()
        return self.__total_frames__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        if (not hasattr(self, "__sample_rate__")):
            self.__populate_metadata__()
        return self.__sample_rate__

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        try:
            sample_rate = self.sample_rate()
            channels = self.channels()
            channel_mask = int(self.channel_mask())
            bits_per_sample = self.bits_per_sample()

            decoder = audiotools.decoders.SHNDecoder(self.filename)
            decoder.sample_rate = sample_rate
            decoder.channel_mask = channel_mask
            return decoder
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
            raise UnsupportedBitsPerSample()

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

    def to_wave(self, wave_filename):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        if (not hasattr(self, "__format__")):
            try:
                self.__populate_metadata__()
            except IOError, msg:
                raise EncodingError(str(msg))
        if (self.__format__ is WaveAudio):
            try:
                f = open(wave_filename, 'wb')
            except IOError, msg:
                raise EncodingError(str(msg))
            for block in self.__blocks__:
                if (block is not None):
                    f.write(block)
                else:
                    try:
                        transfer_framelist_data(
                            audiotools.decoders.SHNDecoder(self.filename),
                            f.write)
                    except IOError, msg:
                        raise EncodingError(str(msg))
        else:
            WaveAudio.from_pcm(wave_filename, self.to_pcm())

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None,
                  block_size=256):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new ShortenAudio object."""

        wave = WaveAudio(wave_filename)

        if (wave.bits_per_sample() not in (8, 16)):
            raise UnsupportedBitsPerSample()

        (head, tail) = wave.pcm_split()
        if (len(tail) > 0):
            blocks = [head, None, tail]
        else:
            blocks = [head, None]

        import audiotools.encoders

        try:
            audiotools.encoders.encode_shn(filename=filename,
                                           pcmreader=wave.to_pcm(),
                                           block_size=block_size,
                                           verbatim_chunks=blocks)

            return cls(filename)
        except IOError, err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            cls.__unlink__(filename)
            raise err

    @classmethod
    def supports_foreign_riff_chunks(cls):
        """Returns True."""

        return True

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        if (not hasattr(self, "__format__")):
            self.__populate_metadata__()
        if (self.__format__ is WaveAudio):
            for (chunk_id, chunk_data) in self.__wave_chunks__():
                if (chunk_id != 'fmt '):
                    return True
            else:
                return False
        else:
            return False
