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


import audiotools
import tempfile
import sys
import cStringIO
import unittest

class BLANK_PCM_Reader:
    #length is the total length of this PCM stream, in seconds
    def __init__(self, length,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = length
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        byte_total = length * sample_rate * channels * bits_per_sample / 8
        self.buffer = cStringIO.StringIO('\x01\x00' * (byte_total / 2))

    def read(self, bytes):
        return self.buffer.read(bytes)

    def close(self):
        self.buffer.close()

class PCM_Count:
    def __init__(self):
        self.count = 0
    
    def write(self, bytes):
        self.count += len(bytes)
    
    def __len__(self):
        return self.count

class DummyMetaData(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"Track Name",
                                     track_number=5,
                                     album_name=u"Album Name",
                                     artist_name=u"Artist Name")
        
class DummyMetaData2(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"New Track Name",
                                     track_number=6,
                                     album_name=u"New Album Name",
                                     artist_name=u"New Artist Name")


TEST_LENGTH = 30
SHORT_LENGTH = 5

class TestWaveAudio(unittest.TestCase):
    def setUp(self):
        self.audio_class = audiotools.WaveAudio

    def testblankencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            self.assertEqual(new_file.channels(),2)
            self.assertEqual(new_file.bits_per_sample(),16),
            self.assertEqual(new_file.sample_rate(),44100)
            
            if (new_file.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    BLANK_PCM_Reader(TEST_LENGTH)),True)
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assert_(len(counter) > 0)
        finally:
            temp.close()

    def testmassencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

        tempfiles = [(tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX),
            audio_class) for audio_class in audiotools.AVAILABLE_TYPES]
        
        other_files = [
            audio_class.from_pcm(temp_file.name,
                                 BLANK_PCM_Reader(SHORT_LENGTH))
            for (temp_file,audio_class) in tempfiles]
        try:
            for f in other_files:
                new_file = self.audio_class.from_pcm(
                    temp.name,
                    f.to_pcm())
                
                if (new_file.lossless() and f.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        f.to_pcm()),True)
                else:
                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    self.assert_(len(counter) > 0)
        finally:
            temp.close()
            for (temp_file,audio_class) in tempfiles:
                temp_file.close()


    def testmetadata(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if (new_file.get_metadata() is not None):
                metadata = DummyMetaData()
                new_file.set_metadata(metadata)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata,new_file.get_metadata())

                metadata2 = DummyMetaData2()
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())

                metadata2.track_name = u'Track Name 3'
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())
        finally:
            temp.close()

class TestAiffAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.AiffAudio

class TestAuAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.AuAudio

class TestFlacAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio

class TestWavPackAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio

class TestOggFlacAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.OggFlacAudio

class TestMP3Audio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.MP3Audio

class TestMP2Audio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio

class TestVorbisAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.VorbisAudio

class TestM4AAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.M4AAudio

class TestMusepackAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.MusepackAudio

class TestSpeexAudio(TestWaveAudio):
    def setUp(self):
        self.audio_class = audiotools.SpeexAudio


if (__name__ == '__main__'):
    unittest.main()

