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


from audiotools import AudioFile,InvalidFile,PCMReader,Con,BUFFER_SIZE,transfer_data,__capped_stream_reader__,FILENAME_FORMAT,BIN,open_files,os,subprocess,cStringIO,EncodingError,DecodingError
import os.path
import gettext
from . import pcm

gettext.install("audiotools",unicode=True)

#######################
#RIFF WAVE
#######################


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
            raise WavException(_(u'Invalid WAVE file'))
        except Con.core.FieldError:
            self.wave = cStringIO.StringIO("")
            return

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
        bytes -= (bytes % (self.channels * self.bits_per_sample / 8))
        return pcm.FrameList(self.wave.read(
                max(bytes,self.channels * self.bits_per_sample / 8)),
                             self.channels,
                             self.bits_per_sample,
                             False,
                             True) #FIXME - 8bps may not be signed

    def close(self):
        self.wave.close()
        if (self.process is not None):
            if (self.process.wait() != 0):
                raise DecodingError()

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

def __blank_channel_mask__():
    c = Con.Container(undefined=0,undefined2=0)

    for attr in ('front_right_of_center',
                 'front_left_of_center',
                 'rear_right',
                 'rear_left',
                 'LFE',
                 'front_center',
                 'front_right',
                 'front_left',
                 'top_back_left',
                 'top_front_right',
                 'top_front_center',
                 'top_front_left',
                 'top_center',
                 'side_right',
                 'side_left',
                 'rear_center',
                 'top_back_right',
                 'top_back_center'):
        setattr(c,attr,False)

    return c

def __channel_mask__(total_channels):
    mask = {1:('front_center'),
            2:('front_left','front_right'),
            3:('front_left','front_right','front_center'),
            4:('front_left','front_right','rear_left','rear_right'),
            5:('front_left','front_right','side_left','side_right',
               'front_center'),
            6:('front_left','front_right','side_left','side_right',
               'front_center','LFE')}

    c = __blank_channel_mask__()
    for channel in mask[total_channels]:
        setattr(c,channel,True)
    return c

class WaveAudio(AudioFile):
    SUFFIX = "wav"
    NAME = SUFFIX

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
                           Con.ULInt16("bits_per_sample"),
                           Con.If(lambda ctx: ctx['compression'] == 0xFFFE,
                                  Con.Embed(
                Con.Struct('extensible',
                           Con.ULInt16('cb_size'),
                           Con.ULInt16('valid_bits_per_sample'),
                           Con.BitStruct('channel_mask',
                                         #byte 1
                                         Con.Flag('front_right_of_center'),
                                         Con.Flag('front_left_of_center'),
                                         Con.Flag('rear_right'),
                                         Con.Flag('rear_left'),
                                         Con.Flag('LFE'),
                                         Con.Flag('front_center'),
                                         Con.Flag('front_right'),
                                         Con.Flag('front_left'),

                                         #byte 2
                                         Con.Flag('top_back_left'),
                                         Con.Flag('top_front_right'),
                                         Con.Flag('top_front_center'),
                                         Con.Flag('top_front_left'),
                                         Con.Flag('top_center'),
                                         Con.Flag('side_right'),
                                         Con.Flag('side_left'),
                                         Con.Flag('rear_center'),

                                         #byte 3
                                         Con.Bits('undefined',6),
                                         Con.Flag('top_back_right'),
                                         Con.Flag('top_back_center'),

                                         Con.Bits('undefined2',8)
                                         ),
                           Con.String('sub_format',16)))
                                  )
                           )


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

        try:
            self.__read_chunks__()
        except WavException,msg:
            raise InvalidFile(str(msg))

    @classmethod
    def is_type(cls, file):
        header = file.read(12)
        return ((header[0:4] == 'RIFF') and
                (header[8:12] == 'WAVE'))

    def lossless(self):
        return True

    @classmethod
    def supports_foreign_riff_chunks(cls):
        return True

    def has_foreign_riff_chunks(self):
        return set(['fmt ','data']) != set(self.__chunk_ids__)

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
        try:
            f = file(filename,"wb")
        except IOError:
            raise EncodingError(None)
        try:
            header = Con.Container()
            header.wave_id = 'RIFF'
            header.riff_type = 'WAVE'
            header.wave_size = 0

            fmt_header = Con.Container()
            fmt_header.chunk_id = 'fmt '
            #fmt_header.chunk_length = WaveAudio.FMT_CHUNK.sizeof()

            if (pcmreader.channels <= 2):
                fmt_header.chunk_length = 16
            else:
                fmt_header.chunk_length = 40

            fmt = Con.Container()

            if (pcmreader.channels <= 2):
                fmt.compression = 1
            else:
                fmt.compression = 0xFFFE

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

            #these fields only apply to WAVEFORMATEXTENSIBLE Waves
            fmt.cb_size = 22
            fmt.valid_bits_per_sample = pcmreader.bits_per_sample
            fmt.sub_format = "0100000000001000800000aa00389b71".decode('hex')
            fmt.channel_mask = __channel_mask__(pcmreader.channels)


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
            framelist = pcmreader.read(BUFFER_SIZE)
            while (len(framelist) > 0):
                if (framelist.bits_per_sample > 8):
                    framelist.set_signed()
                else:
                    framelist.set_unsigned()
                bytes = framelist.to_bytes(False)
                f.write(bytes)
                data_header.chunk_length += len(bytes)
                framelist = pcmreader.read(BUFFER_SIZE)

            #close up the PCM reader and flush our output
            try:
                pcmreader.close()
            except DecodingError:
                raise EncodingError()
            f.flush()

            #go back to the beginning the re-write the header
            f.seek(0,0)
            header.wave_size = 4 + \
                WaveAudio.CHUNK_HEADER.sizeof() + \
                fmt_header.chunk_length + \
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
        try:
            output = file(wave_filename,'wb')
            input = file(self.filename,'rb')
        except IOError:
            raise EncodingError()
        try:
            transfer_data(input.read,output.write)
        finally:
            input.close()
            output.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        try:
            output = file(filename,'wb')
            input = file(wave_filename,'rb')
        except IOError:
            raise EncodingError(None)
        try:
            transfer_data(input.read,output.write)
            return WaveAudio(filename)
        finally:
            input.close()
            output.close()

    def total_frames(self):
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
    def can_add_replay_gain(cls):
        return BIN.can_execute(BIN['wavegain'])

    @classmethod
    def lossless_replay_gain(cls):
        return False

    @classmethod
    def add_replay_gain(cls, filenames):
        if (not BIN.can_execute(BIN['wavegain'])):
            return

        devnull = file(os.devnull,'ab')
        for track_name in [track.filename for track in
                           open_files(filenames) if
                           isinstance(track,cls)]:
            #wavegain's -y option fails spectacularly
            #if the wave file is on a different filesystem than
            #its current working directory
            #due to temp file usage
            working_dir = os.getcwd()
            try:
                if (os.path.dirname(track_name) != ""):
                    os.chdir(os.path.dirname(track_name))
                sub = subprocess.Popen([BIN['wavegain'],"-y",track_name],
                                       stdout=devnull,
                                       stderr=devnull)
                sub.wait()
            finally:
                os.chdir(working_dir)

        devnull.close()

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
            return header.wave_size
        except Con.ConstError:
            raise WavException(_(u"Not a RIFF WAVE file"))
        except Con.core.FieldError:
            raise WavException(_(u"Invalid RIFF WAVE file"))

    def __read_chunk_header__(self, wave_file):
        try:
            chunk = WaveAudio.CHUNK_HEADER.parse(wave_file.read(8))
            return (chunk.chunk_id,chunk.chunk_length)
        except Con.core.FieldError:
            raise WavException(_(u"Invalid RIFF WAVE file"))

    def __read_format_chunk__(self, wave_file, chunk_size):
        if (chunk_size < 16):
            raise WavException(_(u"fmt chunk is too short"))

        fmt = WaveAudio.FMT_CHUNK.parse(wave_file.read(chunk_size))

        self.__wavtype__ = fmt.compression
        self.__channels__ = fmt.channels
        self.__samplespersec__ = fmt.sample_rate
        self.__bytespersec__ = fmt.bytes_per_second
        self.__blockalign__ = fmt.block_align
        self.__bitspersample__ = fmt.bits_per_sample

        if ((self.__wavtype__ != 1) and (self.__wavtype__ != 0xFFFE)):
            raise WavException(_(u"No support for compressed WAVE files"))

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



