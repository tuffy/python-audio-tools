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


from audiotools import AudioFile,InvalidFile,ChannelMask,PCMReader,Con,BUFFER_SIZE,transfer_data,__capped_stream_reader__,FILENAME_FORMAT,BIN,open_files,os,subprocess,cStringIO,EncodingError,DecodingError,UnsupportedChannelMask
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
                 sample_rate, channels, channel_mask, bits_per_sample,
                 process = None):

        self.file = wave_file
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.channel_mask = channel_mask

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
                             self.bits_per_sample != 8)

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
                            channel_mask = int(wave.channel_mask()),
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

def __channel_mask__(mask, channel_count):
    mask = ChannelMask(mask)
    c = __blank_channel_mask__()

    if (mask.defined()):
        attr_map = {"front_left":'front_left',
                    "front_right":'front_right',
                    "front_center":'front_center',
                    "low_frequency":'LFE',
                    "back_left":'rear_left',
                    "back_right":'rear_right',
                    "front_left_of_center":'front_left_of_center',
                    "front_right_of_center":'front_right_of_center',
                    "back_center":'rear_center',
                    "side_left":'side_left',
                    "side_right":'side_right',
                    "top_center":'top_center',
                    "top_front_left":'top_front_left',
                    "top_front_center":'top_front_center',
                    "top_front_right":'top_front_right',
                    "top_back_left":'top_back_left',
                    "top_back_center":'top_back_center',
                    "top_back_right":'top_back_right'}

        for channel in mask.channels():
            setattr(c,attr_map[channel],True)
    else:
        attr_map = ['front_left',
                    'front_right',
                    'front_center',
                    'LFE',
                    'rear_left',
                    'rear_right',
                    'front_left_of_center',
                    'front_right_of_center',
                    'rear_center',
                    'side_left',
                    'side_right',
                    'top_center',
                    'top_front_left',
                    'top_front_center',
                    'top_front_right',
                    'top_back_left',
                    'top_back_center',
                    'top_back_right']
        if (channel_count <= len(attr_map)):
            for channel in attr_map[0:channel_count]:
                setattr(c,channel,True)
        else:
            raise UnsupportedChannelMask()

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
                                         #0x80
                                         Con.Flag('front_right_of_center'),

                                         #0x40
                                         Con.Flag('front_left_of_center'),

                                         #0x20
                                         Con.Flag('rear_right'),

                                         #0x10
                                         Con.Flag('rear_left'),

                                         #0x8
                                         Con.Flag('LFE'),

                                         #0x4
                                         Con.Flag('front_center'),

                                         #0x2
                                         Con.Flag('front_right'),

                                         #0x1
                                         Con.Flag('front_left'),

                                         #0x8000
                                         Con.Flag('top_back_left'),

                                         #0x4000
                                         Con.Flag('top_front_right'),

                                         #0x2000
                                         Con.Flag('top_front_center'),

                                         #0x1000
                                         Con.Flag('top_front_left'),

                                         #0x800
                                         Con.Flag('top_center'),

                                         #0x400
                                         Con.Flag('side_right'),

                                         #0x200
                                         Con.Flag('side_left'),

                                         #0x100
                                         Con.Flag('rear_center'),

                                         #0x800000
                                         #0x400000
                                         #0x200000
                                         #0x100000
                                         #0x80000
                                         #0x40000
                                         Con.Bits('undefined',6),

                                         #0x20000
                                         Con.Flag('top_back_right'),

                                         #0x10000
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
        self.__channel_mask__ = 0

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

    def channel_mask(self):
        return self.__channel_mask__

    #Returns the PCMReader object for this WAV's data
    def to_pcm(self):
        return WaveReader(file(self.filename,'rb'),
                          sample_rate = self.sample_rate(),
                          channels = self.channels(),
                          bits_per_sample = self.bits_per_sample(),
                          channel_mask = int(self.channel_mask()))

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

            fmt = Con.Container()

            if ((pcmreader.channels <= 2) and
                (pcmreader.bits_per_sample <= 16)):
                fmt_header.chunk_length = 16
                fmt.compression = 1
            else:
                fmt_header.chunk_length = 40
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
            if (fmt.compression == 0xFFFE):
                fmt.channel_mask = __channel_mask__(pcmreader.channel_mask,
                                                    pcmreader.channels)
            else:
                fmt.channel_mask = __blank_channel_mask__()


            data_header = Con.Container()
            data_header.chunk_id = 'data'
            data_header.chunk_length = 0

            #write out the basic headers first
            #we'll be back later to clean up the sizes
            f.write(WaveAudio.WAVE_HEADER.build(header))
            f.write(WaveAudio.CHUNK_HEADER.build(fmt_header))
            f.write(WaveAudio.FMT_CHUNK.build(fmt))
            f.write(WaveAudio.CHUNK_HEADER.build(data_header))

            #dump pcmreader's FrameLists into the file as little-endian
            framelist = pcmreader.read(BUFFER_SIZE)
            while (len(framelist) > 0):
                if (framelist.bits_per_sample > 8):
                    bytes = framelist.to_bytes(False,True)
                else:
                    bytes = framelist.to_bytes(False,False)

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

    #takes a Container object parsed from the fmt_chunk.channel_mask
    #returns a proper ChannelMask object
    @classmethod
    def fmt_chunk_to_channel_mask(cls, fmt_channel_mask):
        channel_mask = ChannelMask(0)
        attr_map = {'front_left':"front_left",
                    'front_right':"front_right",
                    'front_center':"front_center",
                    'LFE':"low_frequency",
                    'rear_left':"back_left",
                    'rear_right':"back_right",
                    'front_left_of_center':"front_left_of_center",
                    'front_right_of_center':"front_right_of_center",
                    'rear_center':"back_center",
                    'side_left':"side_left",
                    'side_right':"side_right",
                    'top_center':"top_center",
                    'top_front_left':"top_front_left",
                    'top_front_center':"top_front_center",
                    'top_front_right':"top_front_right",
                    'top_back_left':"top_back_left",
                    'top_back_center':"top_back_center",
                    'top_back_right':"top_back_right"}
        for (key,value) in attr_map.items():
            if (getattr(fmt_channel_mask,key)):
                setattr(channel_mask,value,True)
            else:
                setattr(channel_mask,value,False)

        return channel_mask

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

        if (self.__wavtype__ == 0xFFFE):
            self.__channel_mask__ = WaveAudio.fmt_chunk_to_channel_mask(fmt.channel_mask)
        else:
            if (self.__channels__ == 1):
                self.__channel_mask__ = ChannelMask.from_fields(
                    front_center=True)
            elif (self.__channels__ == 2):
                self.__channel_mask__ = ChannelMask.from_fields(
                    front_left=True,front_right=True)
            #if we have a multi-channel WAVE file
            #that's not WAVEFORMATEXTENSIBLE,
            #assume the channels follow SMPTE/ITU-R recommendations
            #and hope for the best
            elif (self.__channels__ == 3):
                self.__channel_mask__ = ChannelMask.from_fields(
                    front_left=True,front_right=True,front_center=True)
            elif (self.__channels__ == 4):
                self.__channel_mask__ = ChannelMask.from_fields(
                    front_left=True,front_right=True,
                    back_left=True,back_right=True)
            elif (self.__channels__ == 5):
                self.__channel_mask__ = ChannelMask.from_fields(
                    front_left=True,front_right=True,
                    back_left=True,back_right=True,
                    front_center=True)
            elif (self.__channels__ == 6):
                self.__channel_mask__ = ChannelMask.from_fields(
                    front_left=True,front_right=True,
                    back_left=True,back_right=True,
                    front_center=True,low_frequency=True)
            else:
                self.__channel_mask__ = ChannelMask(0)

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



