#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007  Brian Langenberger

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


from audiotools import AudioFile,InvalidFile,PCMReader,Con,BUFFER_SIZE,transfer_data

#######################
#RIFF WAVE
#######################

class __capped_stream_reader__:
    #allows a maximum number of bytes "length" to
    #be read from file-like object "stream"
    #(used for reading IFF chunks)
    def __init__(self, stream, length):
        self.stream = stream
        self.remaining = length

    def read(self, bytes):
        data = self.stream.read(min(bytes,self.remaining))
        self.remaining -= len(data)
        return data

    def close(self):
        self.stream.close()


class WaveReader(PCMReader):
    #wave_file should be a file-like stream of wave data
    def __init__(self, wave_file,
                 sample_rate, channels, bits_per_sample,
                 process = None):

        self.file = wave_file
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.process = process

        #build a capped reader for the data chunk
        try:
            header = WaveAudio.WAVE_HEADER.parse_stream(self.file)
        except Con.ConstError:
            raise WavException('invalid WAVE file')

        #this won't be pretty for a WAVE file missing a 'data' chunk
        #but those are seriously invalid anyway
        chunk_header = WaveAudio.CHUNK_HEADER.parse_stream(self.file)
        while (chunk_header.chunk_id != 'data'):
            #self.file.seek(chunk_header.chunk_length,1)
            self.file.read(chunk_header.chunk_length)
            chunk_header = WaveAudio.CHUNK_HEADER.parse_stream(self.file)

        #build a reader which reads no further than the 'data' chunk
        self.wave = __capped_stream_reader__(self.file,
                                             chunk_header.chunk_length)

    def read(self, bytes):
        return self.wave.read(bytes)

    def close(self):
        self.wave.close()
        if (self.process != None):
            self.process.wait()

class TempWaveReader(WaveReader):
    def __init__(self, tempfile):
        wave = WaveAudio(tempfile.name)
        WaveReader.__init__(self,
                            tempfile,
                            sample_rate = wave.sample_rate(),
                            channels = wave.channels(),
                            bits_per_sample = wave.bits_per_sample())
        self.tempfile = tempfile

    def close(self):
        WaveReader.close(self)
        self.tempfile.close()


class WavException(InvalidFile): pass

class WaveAudio(AudioFile):
    SUFFIX = "wav"

    WAVE_HEADER = Con.Struct("wave_header",
                             Con.Const(Con.Bytes("wave_id",4),'RIFF'),
                             Con.ULInt32("wave_size"),
                             Con.Const(Con.Bytes("riff_type",4),'WAVE'))

    CHUNK_HEADER = Con.Struct("chunk_header",
                              Con.Bytes("chunk_id",4),
                              Con.ULInt32("chunk_length"))
 
    FMT_CHUNK = Con.Struct("fmt_chunk",
                           Con.ULInt16("compression"),
                           Con.ULInt16("channels"),
                           Con.ULInt32("sample_rate"),
                           Con.ULInt32("bytes_per_second"),
                           Con.ULInt16("block_align"),
                           Con.ULInt16("bits_per_sample"))

    
    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        self.__wavtype__ = 0
        self.__channels__ = 0
        self.__samplespersec__ = 0
        self.__bytespersec__ = 0
        self.__blockalign__ = 0
        self.__bitspersample__ = 0
        self.__data_size__ = 0

        self.__chunk_ids__ = []
        self.__read_chunks__()

    @classmethod
    def is_type(cls, file):
        header = file.read(12)
        return ((header[0:4] == 'RIFF') and
                (header[8:12] == 'WAVE'))

    def lossless(self):
        return True

    #Returns the PCMReader object for this WAV's data
    def to_pcm(self):
        return WaveReader(file(self.filename,'rb'),
                          sample_rate = self.sample_rate(),
                          channels = self.channels(),
                          bits_per_sample = self.bits_per_sample())

    #Takes a filename and PCMReader containing WAV data
    #builds a WAV from that data and returns a new WaveAudio object
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        f = file(filename,"wb")
        try:
            header = Con.Container()
            header.wave_id = 'RIFF'
            header.riff_type = 'WAVE'
            header.wave_size = 0

            fmt_header = Con.Container()
            fmt_header.chunk_id = 'fmt '
            fmt_header.chunk_length = WaveAudio.FMT_CHUNK.sizeof()

            fmt = Con.Container()
            fmt.compression = 1
            fmt.channels = pcmreader.channels
            fmt.sample_rate = pcmreader.sample_rate
            fmt.bytes_per_second = \
                pcmreader.sample_rate * \
                pcmreader.channels * \
                (pcmreader.bits_per_sample / 8)
            fmt.block_align = \
                pcmreader.channels * \
                (pcmreader.bits_per_sample / 8)
            fmt.bits_per_sample = pcmreader.bits_per_sample

            data_header = Con.Container()
            data_header.chunk_id = 'data'
            data_header.chunk_length = 0

            #write out the basic headers first
            #we'll be back later to clean up the sizes
            f.write(WaveAudio.WAVE_HEADER.build(header))
            f.write(WaveAudio.CHUNK_HEADER.build(fmt_header))
            f.write(WaveAudio.FMT_CHUNK.build(fmt))
            f.write(WaveAudio.CHUNK_HEADER.build(data_header))

            #pcmreader should be little-endian audio
            #we can dump straight into the file
            buffer = pcmreader.read(BUFFER_SIZE)
            while (len(buffer) > 0):
                f.write(buffer)
                data_header.chunk_length += len(buffer)
                buffer = pcmreader.read(BUFFER_SIZE)

            #close up the PCM reader and flush our output
            pcmreader.close()
            f.flush()

            #go back to the beginning the re-write the header
            f.seek(0,0)
            header.wave_size = 4 + \
                WaveAudio.CHUNK_HEADER.sizeof() + \
                WaveAudio.FMT_CHUNK.sizeof() + \
                WaveAudio.CHUNK_HEADER.sizeof() + \
                data_header.chunk_length
            
            f.write(WaveAudio.WAVE_HEADER.build(header))
            f.write(WaveAudio.CHUNK_HEADER.build(fmt_header))
            f.write(WaveAudio.FMT_CHUNK.build(fmt))
            f.write(WaveAudio.CHUNK_HEADER.build(data_header))

        finally:
            f.close()
        
        return WaveAudio(filename)

    def to_wave(self, wave_filename):
        output = file(wave_filename,'wb')
        input = file(self.filename,'rb')
        try:
            transfer_data(input.read,output.write)
        finally:
            input.close()
            output.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        output = file(filename,'wb')
        input = file(wave_filename,'rb')
        try:
            transfer_data(input.read,output.write)
            return WaveAudio(filename)
        finally:
            input.close()
            output.close()

    def total_samples(self):
        return self.__data_size__ / (self.__bitspersample__ / 8) / \
               self.__channels__

    #returns the rate of samples per second (44100 for CD audio)
    def sample_rate(self):
        return self.__samplespersec__

    #returns the number of channels (2 for CD audio)
    def channels(self):
        return self.__channels__

    #returns the total bits per sample (16 for CD audio)
    def bits_per_sample(self):
        return self.__bitspersample__

    @classmethod
    def track_name(cls, track_number, track_metadata):
        return "track%(track_number)2.2d.cdda.wav" % \
               {"track_number":track_number}

    def __read_chunks__(self):
        wave_file = file(self.filename,"rb")

        __chunklist__ = []

        totalsize = self.__read_wave_header__(wave_file) - 4

        while (totalsize > 0):
            (chunk_format,chunk_size) = self.__read_chunk_header__(wave_file)
            self.__chunk_ids__.append(chunk_format)
            
            __chunklist__.append(chunk_format)
            #Fix odd-sized chunk sizes to be even
            if ((chunk_size & 1) == 1): chunk_size += 1
            
            if (chunk_format == "fmt "):
                self.__read_format_chunk__(wave_file, chunk_size)
            elif (chunk_format == "data"):
                self.__read_data_chunk__(wave_file, chunk_size)
            else:
                wave_file.seek(chunk_size,1)
            totalsize -= (chunk_size + 8)

    def __read_wave_header__(self, wave_file):
        try:
            header = WaveAudio.WAVE_HEADER.parse(wave_file.read(12))
        except Con.ConstError:
            raise WavException("not a RIFF WAVE file")
        
        return header.wave_size

    def __read_chunk_header__(self, wave_file):
        chunk = WaveAudio.CHUNK_HEADER.parse(wave_file.read(8))
        return (chunk.chunk_id,chunk.chunk_length)

    def __read_format_chunk__(self, wave_file, chunk_size):
        if (chunk_size < 16):
            raise WavException("fmt chunk is too short")

        fmt = WaveAudio.FMT_CHUNK.parse(wave_file.read(chunk_size))
        
        self.__wavtype__ = fmt.compression
        self.__channels__ = fmt.channels
        self.__samplespersec__ = fmt.sample_rate
        self.__bytespersec__ = fmt.bytes_per_second
        self.__blockalign__ = fmt.block_align
        self.__bitspersample__ = fmt.bits_per_sample

        if (self.__wavtype__ != 1):
            raise WavException("no support for compressed WAVE files")

    def __read_data_chunk__(self, wave_file, chunk_size):
        self.__data_size__ = chunk_size
        wave_file.seek(chunk_size,1)

    def chunk_ids(self):
        return self.__chunk_ids__[:]

    #iterates over the file's RIFF chunks,
    #returning a (chunk_id,chunk_data) tuple on each pass
    def chunks(self):
        wave_file = file(self.filename,'rb')
        total_size = self.__read_wave_header__(wave_file) - 4

        while (total_size > 0):
            (chunk_id,chunk_size) = self.__read_chunk_header__(wave_file)

            #Fix odd-sized chunks to have 16-bit boundaries
            if ((chunk_size & 1) == 1): chunk_size += 1
            
            yield (chunk_id,wave_file.read(chunk_size))

            total_size -= (chunk_size + 8)


    #takes our new RIFF WAVE filename
    #and an iterator of (chunk_id,chunk_data) tuples
    #builds a RIFF WAVE file from those chunks
    @classmethod
    def wave_from_chunks(cls, filename, chunk_iter):
        f = file(filename,'wb')

        header = Con.Container()
        header.wave_id = 'RIFF'
        header.riff_type = 'WAVE'
        header.wave_size = 4

        #write an unfinished header with an invalid size (for now)
        f.write(cls.WAVE_HEADER.build(header))
        
        for (chunk_id,chunk_data) in chunk_iter:

            #fix odd-sized chunks to fall on 16-bit boundaries
            if ((len(chunk_data) & 1) == 1): chunk_data += chr(0)

            chunk_header = cls.CHUNK_HEADER.build(
                Con.Container(chunk_id=chunk_id,
                              chunk_length=len(chunk_data)))
            f.write(chunk_header)
            header.wave_size += len(chunk_header)

            f.write(chunk_data)
            header.wave_size += len(chunk_data)

        #now that the chunks are done, go back and re-write the header
        f.seek(0,0)
        f.write(cls.WAVE_HEADER.build(header))
        f.close()

            
            
