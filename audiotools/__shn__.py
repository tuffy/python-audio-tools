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
                        UnsupportedBitsPerSample)

import audiotools.decoders


class ShortenAudio(AudioFile):
    SUFFIX = "shn"
    NAME = SUFFIX

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)

    def __populate_metadata__(self):
        #grab a few pieces of technical metadata from the Shorten file itself
        #which requires a dry-run through the decoder
        decoder = audiotools.decoders.SHNDecoder(self.filename)
        self.__bits_per_sample__ = decoder.bits_per_sample
        self.__channels__ = decoder.channels
        (self.__total_frames__,
         self.__blocks__) = decoder.metadata()
        decoder.close()

        #set up some default values
        self.__sample_rate__ = 44100
        try:
            self.__channel_mask__ = ChannelMask.from_channels(
                self.__channels__)
        except ValueError:
            self.__channel_mask__ = 0
        self.__format__ = None

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

        decoder = audiotools.decoders.SHNDecoder(self.filename)
        decoder.sample_rate = self.sample_rate()
        decoder.channel_mask = int(self.channel_mask())
        return decoder

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
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
        w = WaveAudio.from_pcm(f.name, pcmreader)
        try:
            return cls.from_wave(filename, f.name, compression)
        finally:
            f.close()

    def to_wave(self, wave_filename):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        if (not hasattr(self, "__format__")):
            self.__populate_metadata__()
        if (self.__format__ is WaveAudio):
            try:
                f = open(wave_filename, 'wb')
            except IOError:
                raise EncodingError()
            for block in self.__blocks__:
                if (block is not None):
                    f.write(block)
                else:
                    transfer_framelist_data(
                        audiotools.decoders.SHNDecoder(self.filename),
                        f.write)
        else:
            WaveAudio.from_pcm(wave_filename, self.to_pcm())

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
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
                                           block_size=256,
                                           verbatim_chunks=blocks)

            return cls(filename)
        except IOError:
            raise EncodingError("shn")

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
