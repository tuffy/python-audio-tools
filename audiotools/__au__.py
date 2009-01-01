#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2009  Brian Langenberger

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


from audiotools import AudioFile,InvalidFile,PCMReader,Con,transfer_data,InvalidFormat,__capped_stream_reader__,BUFFER_SIZE,FILENAME_FORMAT
import audiotools.pcmstream

#######################
#Sun AU
#######################

class AuReader(PCMReader):
    #takes an open, properly positioned file handle
    #the total size of the data
    #and the usual sample_rate,channels,bits_per_sample stuff
    def __init__(self, au_file, data_size,
                 sample_rate,channels,bits_per_sample):
        self.stream = audiotools.pcmstream.PCMStreamReader(
            __capped_stream_reader__(au_file,data_size),
            bits_per_sample / 8,
            True, False)

        PCMReader.__init__(self,self.stream,
                           sample_rate,channels,bits_per_sample)

    #handles all the proper byte swapping
    def read(self, bytes):
        return audiotools.pcmstream.pcm_to_string(
            self.stream.read(bytes),self.bits_per_sample / 8,False)


class AuAudio(AudioFile):
    SUFFIX = "au"
    NAME = SUFFIX

    AU_HEADER = Con.Struct('header',
                           Con.Const(Con.String('magic_number',4),
                                     '.snd'),
                           Con.UBInt32('data_offset'),
                           Con.UBInt32('data_size'),
                           Con.UBInt32('encoding_format'),
                           Con.UBInt32('sample_rate'),
                           Con.UBInt32('channels'))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        f = file(filename,'rb')
        try:
            header = AuAudio.AU_HEADER.parse_stream(f)

            if (header.encoding_format not in (2,3,4)):
                raise InvalidFile("unsupported Sun AU encoding format")

            self.__bits_per_sample__ = {2:8,3:16,4:24}[header.encoding_format]
            self.__channels__ = header.channels
            self.__sample_rate__ = header.sample_rate
            self.__total_frames__ = header.data_size / \
                (self.__bits_per_sample__ / 8) / \
                self.__channels__
            self.__data_offset__ = header.data_offset
            self.__data_size__ = header.data_size
        except Con.ConstError:
            raise InvalidFile(str(msg))

    @classmethod
    def is_type(cls, file):
        return file.read(4) == ".snd"

    def lossless(self):
        return True

    def bits_per_sample(self):
        return self.__bits_per_sample__

    def channels(self):
        return self.__channels__

    def sample_rate(self):
        return self.__sample_rate__

    def total_frames(self):
        return self.__total_frames__


    def to_pcm(self):
        f = file(self.filename,'rb')
        f.seek(self.__data_offset__,0)

        return AuReader(f,self.__data_size__,
                        self.sample_rate(),
                        self.channels(),
                        self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        if (pcmreader.bits_per_sample not in (8,16,24)):
            raise InvalidFormat(
                "unsupported bits per sample %s" % (pcmreader.bits_per_sample))

        bytes_per_sample = pcmreader.bits_per_sample / 8

        converter = audiotools.pcmstream.PCMStreamReader(
            pcmreader,bytes_per_sample,False,False)

        header = Con.Container(magic_number='.snd',
                               data_offset=0,
                               data_size=0,
                               encoding_format={8:2,16:3,24:4}[pcmreader.bits_per_sample],
                               sample_rate=pcmreader.sample_rate,
                               channels=pcmreader.channels)

        f = file(filename,'wb')
        try:
            #send out a dummy header
            f.write(AuAudio.AU_HEADER.build(header))
            header.data_offset = f.tell()

            #send our big-endian PCM data
            #d will be a list of ints, so we can't use transfer_data
            d = converter.read(BUFFER_SIZE)
            while (len(d) > 0):
                s = audiotools.pcmstream.pcm_to_string(d,
                                                       bytes_per_sample,
                                                       True)
                f.write(s)

                header.data_size += len(s)
                d = converter.read(BUFFER_SIZE)

            #send out a complete header
            f.seek(0,0)
            f.write(AuAudio.AU_HEADER.build(header))
        finally:
            f.close()

        return AuAudio(filename)

