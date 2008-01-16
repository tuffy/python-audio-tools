#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2008  Brian Langenberger

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


from audiotools import AudioFile,InvalidFile,Con,subprocess,BIN,open_files,os,ReplayGain,ignore_sigint
from __wav__ import WaveAudio,WaveReader
from __ape__ import ApeTaggedAudio

#######################
#WavPack
#######################

class WavPackAudio(ApeTaggedAudio,AudioFile):
    SUFFIX = "wv"
    DEFAULT_COMPRESSION = "veryhigh"
    COMPRESSION_MODES = ("fast","standard","high","veryhigh")
    BINARIES = ("wavpack","wvunpack")


    HEADER = Con.Struct("wavpackheader",
                        Con.Const(Con.String("id",4),'wvpk'),
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
        self.__total_frames__ = 0

        self.__read_info__()

    @classmethod
    def is_type(cls, file):
        return file.read(4) == 'wvpk'

    def lossless(self):
        return True

    @classmethod
    def supports_foreign_riff_chunks(cls):
        return True

    def __read_info__(self):
        f = file(self.filename)
        try:
            try:
                header = WavPackAudio.HEADER.parse(f.read(
                    WavPackAudio.HEADER.sizeof()))
            except Con.ConstError:
                raise InvalidFile('wavpack header ID invalid')
        
            self.__samplerate__ = WavPackAudio.SAMPLING_RATE[
                (header.sampling_rate_high << 1) |
                header.sampling_rate_low]
            self.__bitspersample__ = WavPackAudio.BITS_PER_SAMPLE[
                header.bits_per_sample]
            self.__total_frames__ = header.total_samples

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

    def total_frames(self):
        return self.__total_frames__

    def sample_rate(self):
        return self.__samplerate__
    
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        import tempfile

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        
        try:
            return cls.from_wave(filename,w.filename,compression)
        finally:
            del(w)
            f.close()
        
    def to_pcm(self):
        sub = subprocess.Popen([BIN['wvunpack'],
                                '-q','-y',
                                self.filename,
                                '-o','-'],
                               stdout=subprocess.PIPE)

        return WaveReader(sub.stdout,
                          sample_rate=self.sample_rate(),
                          channels=self.channels(),
                          bits_per_sample=self.bits_per_sample(),
                          process=sub)

    def to_wave(self, wave_filename):
        sub = subprocess.Popen([BIN['wvunpack'],
                                '-q','-y',
                                self.filename,
                                '-o',wave_filename])
        sub.wait()
        
    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        compression_param = {"fast":["-f"],
                             "standard":[],
                             "high":["-h"],
                             "veryhigh":["-hh"]}
                     
        sub = subprocess.Popen([BIN['wavpack'],
                                wave_filename] + \
                               compression_param[compression] + \
                               ['-q','-y','-o',
                                filename],
                               preexec_fn=ignore_sigint)

        sub.wait()
        return WavPackAudio(filename)

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track,cls)]        

        if ((len(track_names) > 0) and
            BIN.can_execute(BIN['wvgain'])):
            devnull = file(os.devnull,'ab')

            sub = subprocess.Popen([BIN['wvgain'],
                                    '-q','-a'] + track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()

    @classmethod
    def can_add_replay_gain(cls):
        return BIN.can_execute(BIN['wvgain'])

    def replay_gain(self):
        metadata = self.get_metadata()
        
        if (set(['replaygain_track_gain', 'replaygain_track_peak', 
                 'replaygain_album_gain', 'replaygain_album_peak']).issubset(
                metadata.keys())):  #we have ReplayGain data
            try:
                return ReplayGain(
                    metadata['replaygain_track_gain'][0:-len(" dB")],
                    metadata['replaygain_track_peak'],
                    metadata['replaygain_album_gain'][0:-len(" dB")],
                    metadata['replaygain_album_peak'])
            except ValueError:
                return None
        else:
            return None
