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


from audiotools import AudioFile,InvalidFile,PCMReader,Con,transfer_data,subprocess,BIN,cStringIO,ApeTaggedAudio
from audiotools_wav import *

#######################
#WavPack
#######################

class WavPackAudio(ApeTaggedAudio,AudioFile):
    SUFFIX = "wv"
    DEFAULT_COMPRESSION = "veryhigh"
    COMPRESSION_MODES = ("fast","standard","high","veryhigh")
    BINARIES = ("wavpack","wvunpack")


    HEADER = Con.Struct("wavpackheader",
                        Con.String("id",4),
                        Con.ULInt32("block_size"),
                        Con.ULInt16("version"),
                        Con.ULInt8("track_number"),
                        Con.ULInt8("index_number"),
                        Con.ULInt32("total_samples"),
                        Con.ULInt32("block_index"),
                        Con.ULInt32("block_samples"),
                        Con.Embed(
            Con.BitStruct("flags",
                          Con.Flag("floating_point_data"),
                          Con.Flag("hybrid_noise_shaping"),
                          Con.Flag("cross_channel_decorrelation"),
                          Con.Flag("joint_stereo"),
                          Con.Flag("hybrid_mode"),
                          Con.Flag("mono_output"),
                          Con.Bits("bits_per_sample",2),

                          Con.Bits("left_shift_data_low",3),
                          Con.Flag("final_block_in_sequence"),
                          Con.Flag("initial_block_in_sequence"),
                          Con.Flag("hybrid_noise_balanced"),
                          Con.Flag("hybrid_mode_control_bitrate"),
                          Con.Flag("extended_size_integers"),

                          Con.Bit("sampling_rate_low"),
                          Con.Bits("maximum_magnitude",5),
                          Con.Bits("left_shift_data_high",2),

                          Con.Flag("reserved2"),
                          Con.Flag("false_stereo"),
                          Con.Flag("use_IIR"),
                          Con.Bits("reserved1",2),
                          Con.Bits("sampling_rate_high",3)
                          )),
                        Con.ULInt32("crc"))

    BITS_PER_SAMPLE = (8,16,24,32)
    SAMPLING_RATE = (6000,  8000,  9600,   11025, 
                     12000, 16000, 22050,  24000,
                     32000, 44100, 48000,  64000, 
                     88200, 96000, 192000, 0)


    def __init__(self, filename):
        self.filename = filename
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_samples__ = 0

        self.__read_info__()

    @classmethod
    def is_type(cls, file):
        return file.read(4) == 'wvpk'

    def lossless(self):
        return True

    def __read_info__(self):
        f = file(self.filename)
        try:
            header = WavPackAudio.HEADER.parse(f.read(
                    WavPackAudio.HEADER.sizeof()))

            if (header.id != 'wvpk'):
                raise InvalidFile('wavpack header ID invalid')
        
            self.__samplerate__ = WavPackAudio.SAMPLING_RATE[
                (header.sampling_rate_high << 1) |
                header.sampling_rate_low]
            self.__bitspersample__ = WavPackAudio.BITS_PER_SAMPLE[
                header.bits_per_sample]
            self.__total_samples__ = header.total_samples

            self.__channels__ = 0

            #go through as many headers as necessary
            #to count the number of channels
            if (header.mono_output):
                self.__channels__ += 1
            else:
                self.__channels__ += 2

            while (not header.final_block_in_sequence):
                f.seek(header.block_size - 24,1)
                header = WavPackAudio.HEADER.parse(f.read(
                        WavPackAudio.HEADER.sizeof()))
                if (header.mono_output):
                    self.__channels__ += 1
                else:
                    self.__channels__ += 2
        finally:
            f.close()

    def bits_per_sample(self):
        return self.__bitspersample__

    def channels(self):
        return self.__channels__

    def total_samples(self):
        return self.__total_samples__

    def sample_rate(self):
        return self.__samplerate__
    
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        compression_param = {"fast":["-f"],
                             "standard":[],
                             "high":["-h"],
                             "veryhigh":["-hh"]}

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        
        sub = subprocess.Popen([BIN['wavpack'],
                                w.filename] + \
                               compression_param[compression] + \
                               ['-q','-y','-o',
                                filename])
        sub.wait()

        del(w)
        f.close()
        return WavPackAudio(filename)

    def to_pcm(self):
        sub = subprocess.Popen([BIN['wvunpack'],
                                '-q',
                                self.filename,
                                '-o','-'],
                               stdout=subprocess.PIPE)

        return WaveReader(sub.stdout,
                          sample_rate=self.sample_rate(),
                          channels=self.channels(),
                          bits_per_sample=self.bits_per_sample(),
                          process=sub)

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]        

        if ((len(track_names) > 0) and
            BIN.can_execute(BIN['wvgain'])):
            devnull = file(os.devnull,'a')

            sub = subprocess.Popen([BIN['wvgain'],
                                    '-q','-a'] + track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()

