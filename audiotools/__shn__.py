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

from audiotools import AudioFile,ChannelMask,PCMReader,transfer_framelist_data,WaveAudio,AiffAudio,AuAudio,cStringIO,EncodingError
import audiotools.decoders

class ShortenAudio(AudioFile):
    SUFFIX = "shn"
    NAME = SUFFIX

    def __init__(self, filename):
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
            self.__channel_mask__ = ChannelMask.from_channels(self.__channels__)
        except ValueError:
            self.__channel_mask__ = 0
        self.__format__ = None

        #the remainder requires parsing the file's VERBATIM blocks
        #which may contain Wave, AIFF or Sun AU info
        if (self.__blocks__[0] is not None):
            header = cStringIO.StringIO(self.__blocks__[0])
            for format in WaveAudio,AiffAudio,AuAudio:
                header.seek(0,0)
                if (format.is_type(header)):
                    self.__format__ = format
                    break
            if (self.__format__ is WaveAudio):
                for (chunk_id,chunk_data) in self.__wave_chunks__():
                    if (chunk_id == 'fmt '):
                        fmt_chunk = WaveAudio.FMT_CHUNK.parse(chunk_data)
                        self.__sample_rate__ = fmt_chunk.sample_rate
                        if (fmt_chunk.compression == 0xFFFE):
                            self.__channel_mask__ = WaveAudio.fmt_chunk_to_channel_mask(fmt_chunk.channel_mask)
            elif (self.__format__ is AiffAudio):
                for (chunk_id,chunk_data) in self.__aiff_chunks__():
                    if (chunk_id == 'COMM'):
                        comm_chunk = AiffAudio.COMM_CHUNK.parse(chunk_data)
                        self.__sample_rate__ = comm_chunk.sample_rate
            elif (self.__format__ is AuAudio):
                #FIXME - parse this
                pass

    def __wave_chunks__(self):
        total_size = sum([len(block) for block in self.__blocks__
                          if block is not None])
        wave_data = cStringIO.StringIO("".join([block for block in
                                                self.__blocks__
                                                if block is not None]))

        wave_data.read(12) #skip the RIFFxxxxWAVE header data
        total_size -= 12

        #iterate over all the non-data chunks
        while (total_size > 0):
            header = WaveAudio.CHUNK_HEADER.parse_stream(wave_data)
            total_size -= 8
            if (header.chunk_id != 'data'):
                yield (header.chunk_id,wave_data.read(header.chunk_length))
                total_size -= header.chunk_length
            else:
                continue

    def __aiff_chunks__(self):
        total_size = sum([len(block) for block in self.__blocks__
                          if block is not None])
        aiff_data = cStringIO.StringIO("".join([block for block in
                                                self.__blocks__
                                                if block is not None]))

        aiff_data.read(12) #skip the FORMxxxxAIFF header data
        total_size -= 12

        #iterate over all the non-ssnd chunks
        while (total_size > 0):
            header = AiffAudio.CHUNK_HEADER.parse_stream(aiff_data)
            total_size -= 8
            if (header.chunk_id != 'SSND'):
                yield (header.chunk_id,aiff_data.read(header.chunk_length))
                total_size -= header.chunk_length
            else:
                #not sure what Shorten does with the first 8 bytes
                #of the SSND chunk
                #it'll be a mess if it turns those into audio data
                continue

    @classmethod
    def is_type(cls, file):
        return (file.read(4) == 'ajkg') and (ord(file.read(1)) == 2)

    def bits_per_sample(self):
        if (not hasattr(self,"__bits_per_sample__")):
            self.__populate_metadata__()
        return self.__bits_per_sample__

    def channels(self):
        if (not hasattr(self,"__channels__")):
            self.__populate_metadata__()
        return self.__channels__

    def channel_mask(self):
        if (not hasattr(self,"__channel_mask__")):
            self.__populate_metadata__()
        return self.__channel_mask__

    def lossless(self):
        return True

    def total_frames(self):
        if (not hasattr(self,"__total_frames__")):
            self.__populate_metadata__()
        return self.__total_frames__

    def sample_rate(self):
        if (not hasattr(self,"__sample_rate__")):
            self.__populate_metadata__()
        return self.__sample_rate__

    def to_pcm(self):
        decoder = audiotools.decoders.SHNDecoder(self.filename)
        decoder.sample_rate = self.sample_rate()
        decoder.channel_mask = int(self.channel_mask())
        return decoder

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        tempwavefile = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            tempwave = WaveAudio.from_pcm(tempwavefile.name,pcmreader)
            return cls.from_wave(filename,
                                 tempwavefile.name,
                                 compression=compression)
        finally:
            tempwavefile.close()

    def to_wave(self, wave_filename):
        if (not hasattr(self,"__format__")):
            self.__populate_metadata__()
        if (self.__format__ is WaveAudio):
            try:
                f = open(wave_filename,'wb')
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
            WaveAudio.from_pcm(wave_filename,self.to_pcm())

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        wave = WaveAudio(wave_filename)
        (head,tail) = wave.pcm_split()
        if (len(tail) > 0):
            blocks = [head,None,tail]
        else:
            blocks = [head,None]

        import audiotools.encoders

        audiotools.encoders.encode_shn(filename=filename,
                                       pcmreader=wave.to_pcm(),
                                       block_size=256,
                                       verbatim_chunks=blocks)

        return cls(filename)

    @classmethod
    def supports_foreign_riff_chunks(cls):
        return True

    def has_foreign_riff_chunks(self):
        if (not hasattr(self,"__format__")):
            self.__populate_metadata__()
        if (self.__format__ is WaveAudio):
            for (chunk_id,chunk_data) in self.__wave_chunks__():
                if (chunk_id != 'fmt '):
                    return True
            else:
                return False
        else:
            return False
