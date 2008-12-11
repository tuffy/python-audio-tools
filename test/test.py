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


import audiotools
import audiotools.pcmstream
import audiotools.bitstream
import tempfile
import sys
import os
import random
import cStringIO
import unittest
import decimal as D
import subprocess
import filecmp

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

Con = audiotools.Con

#probstat does this better, but I don't want to require that
#for something used only rarely
def Combinations(items, n):
    if (n == 0):
        yield []
    else:
        for i in xrange(len(items)):
            for combos in Combinations(items[i + 1:], n - 1):
                yield [items[i]] + combos

class BLANK_PCM_Reader:
    #length is the total length of this PCM stream, in seconds
    def __init__(self, length,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = length
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.total_size = length * sample_rate * channels * bits_per_sample / 8
        self.current_size = self.total_size

    def read(self, bytes):
        if (self.current_size > 0):
            if (self.bits_per_sample > 8):
                buffer = ('\x01\x00' * (min(bytes,self.current_size) / 2)) + \
                          '\x00' * (min(bytes,self.current_size) % 2)
            else:
                buffer = chr(0) * (min(bytes,self.current_size))

            self.current_size -= len(buffer)
            return buffer
        else:
            return ""

    def close(self):
        pass

#this sends out random samples instead of a bunch of identical ones
class RANDOM_PCM_Reader(BLANK_PCM_Reader):
    def __init__(self, length,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        BLANK_PCM_Reader.__init__(self,length,
                                  sample_rate,channels,bits_per_sample)
        self.md5 = md5()

    def read(self, bytes):
        if (self.current_size > 0):
            buffer = os.urandom(min(bytes,self.current_size))
            self.md5.update(buffer)
            self.current_size -= len(buffer)
            return buffer
        else:
            return ""

    def hexdigest(self):
        return self.md5.hexdigest()

class EXACT_RANDOM_PCM_Reader(RANDOM_PCM_Reader):
    def __init__(self, pcm_frames,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = pcm_frames * sample_rate
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.total_size = pcm_frames * channels * bits_per_sample / 8
        self.current_size = self.total_size


        self.md5 = md5()

#this not only sends out random samples,
#but the amount sent on each read() is also random
#between 1 and audiotools.BUFFER_SIZE * 2
class VARIABLE_PCM_Reader(RANDOM_PCM_Reader):
    def read(self, bytes):
        if (self.current_size > 0):
            buffer = os.urandom(min(
                random.randint(1,audiotools.BUFFER_SIZE * 2),
                self.current_size))
            self.md5.update(buffer)
            self.current_size -= len(buffer)
            return buffer
        else:
            return ""

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
                                     #track_name=u"T\u2604rack Name",
                                     track_number=5,
                                     album_name=u"Album Name",
                                     artist_name=u"Artist Name",
                                     performer_name=u"Performer",
                                     composer_name=u"Composer",
                                     conductor_name=u"Conductor",
                                     media=u"CD",
                                     ISRC=u"US-PR3-08-12345",
                                     copyright=u"Copyright Attribution",
                                     year=u"2008",
                                     publisher=u"Test Records Inc.",
                                     #comment=u"Comment")
                                     comment=u"C\u2604mment")

    @classmethod
    def supports_images(cls):
        return True

class SmallDummyMetaData(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"Track Name",
                                     artist_name=u"Artist Name",
                                     year=u'2008',
                                     performer_name=u"Performer",
                                     track_number=5,
                                     album_name=u"Album Name",
                                     composer_name=u"Composer",
                                     album_number=6,
                                     comment=u"Comment")

    @classmethod
    def supports_images(cls):
        return True

class DummyMetaData2(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"New Track Name",
                                     track_number=6,
                                     album_name=u"New Album Name",
                                     artist_name=u"New Artist Name",
                                     performer_name=u"New Performer",
                                     composer_name=u"New Composer",
                                     conductor_name=u"New Conductor",
                                     media=u"CD-R",
                                     ISRC=u"US-PR3-08-54321",
                                     copyright=u"Copyright Attribution 2",
                                     year=u"2007",
                                     publisher=u"Testing Records Inc.")

    @classmethod
    def supports_images(cls):
        return True

TEST_LENGTH = 30
SHORT_LENGTH = 5

TEST_COVER1 = \
"""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
o/ez5iJPo7/8tO/0s8/+jxCO4T8AO2LoJg==""".decode('base64').decode('zlib')

TEST_COVER2 = \
"""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""".decode('base64').decode('zlib')

#this is an insane amount of different PCM combinations
PCM_COMBINATIONS = (
    (11025, 1, 8), (22050, 1, 8), (32000, 1, 8),  (44100, 1, 8),
    (48000, 1, 8), (96000, 1, 8), (192000, 1, 8), (11025, 2, 8),
    (22050, 2, 8), (32000, 2, 8), (44100, 2, 8),  (48000, 2, 8),
    (96000, 2, 8), (192000, 2, 8),(11025, 6, 8),  (22050, 6, 8),
    (32000, 6, 8), (44100, 6, 8), (48000, 6, 8),  (96000, 6, 8),
    (192000, 6, 8),(11025, 1, 16),(22050, 1, 16), (32000, 1, 16),
    (44100, 1, 16),(48000, 1, 16),(96000, 1, 16), (192000, 1, 16),
    (11025, 2, 16),(22050, 2, 16),(32000, 2, 16), (44100, 2, 16),
    (48000, 2, 16),(96000, 2, 16),(192000, 2, 16),(11025, 6, 16),
    (22050, 6, 16),(32000, 6, 16),(44100, 6, 16), (48000, 6, 16),
    (96000, 6, 16),(192000, 6, 16),(11025, 1, 24),(22050, 1, 24),
    (32000, 1, 24),(44100, 1, 24),(48000, 1, 24), (96000, 1, 24),
    (192000, 1, 24),(11025, 2, 24),(22050, 2, 24),(32000, 2, 24),
    (44100, 2, 24),(48000, 2, 24),(96000, 2, 24), (192000, 2, 24),
    (11025, 6, 24),(22050, 6, 24),(32000, 6, 24), (44100, 6, 24),
    (48000, 6, 24),(96000, 6, 24),(192000, 6, 24))

#these are combinations that tend to occur in nature
SHORT_PCM_COMBINATIONS = ((11025, 1, 8),  (22050, 1, 8),
                          (22050, 1, 16), (32000, 2, 16),
                          (44100, 1, 16), (44100, 2, 16),
                          (48000, 1, 16), (48000, 2, 16),
                          (48000, 6, 16),
                          (192000, 2, 24),(96000, 6, 24))

class DummyMetaData3(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(
            self,
            track_name=u"Track Name Three",
            track_number=5,
            album_name=u"Album Name",
            artist_name=u"Artist Name",
            performer_name=u"Performer",
            images=[audiotools.Image.new(TEST_COVER1,u'',0)])

    @classmethod
    def supports_images(cls):
        return True

############
#BEGIN TESTS
############

class TestPCMCombinations(unittest.TestCase):
    def testpcmcombinations(self):
        for (sample_rate,channels,bits_per_sample) in SHORT_PCM_COMBINATIONS:
            reader = BLANK_PCM_Reader(SHORT_LENGTH,
                                      sample_rate, channels,
                                      bits_per_sample)
            counter = PCM_Count()
            audiotools.transfer_data(reader.read,counter.write)
            self.assertEqual(len(counter),reader.total_size)

class TestAiffAudio(unittest.TestCase):
    def setUp(self):
        self.audio_class = audiotools.AiffAudio

    def __is_lossless__(self):
        short_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            short = self.audio_class.from_pcm(
                short_file.name,
                BLANK_PCM_Reader(5))
            return short.lossless()
        finally:
            short_file.close()

    #this is a basic test of CD-quality audio
    def testblankencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            self.assertEqual(new_file.channels(),2)
            self.assertEqual(new_file.bits_per_sample(),16)
            self.assertEqual(new_file.sample_rate(),44100)

            if (new_file.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    BLANK_PCM_Reader(TEST_LENGTH)),True)
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assertEqual(
                    (D.Decimal(len(counter) / 4) / 44100).to_integral(),
                    TEST_LENGTH)
                pcm.close()
        finally:
            temp.close()

    def testrandomencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            reader = VARIABLE_PCM_Reader(TEST_LENGTH)

            new_file = self.audio_class.from_pcm(
                temp.name,reader)

            self.assertEqual(new_file.channels(),2)
            self.assertEqual(new_file.bits_per_sample(),16)
            self.assertEqual(new_file.sample_rate(),44100)

            if (new_file.lossless()):
                md5sum = md5()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,md5sum.update)
                pcm.close()
                self.assertEqual(md5sum.hexdigest(),reader.hexdigest())
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assertEqual(
                    (D.Decimal(len(counter) / 4) / 44100).to_integral(),
                    TEST_LENGTH)
                pcm.close()
        finally:
            temp.close()


    def testunusualaudio(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            #not all of these combinations will be supported by all formats
            for (sample_rate,channels,bits_per_sample) in SHORT_PCM_COMBINATIONS:

                try:
                    new_file = self.audio_class.from_pcm(
                        temp.name,
                        BLANK_PCM_Reader(SHORT_LENGTH,
                                         sample_rate, channels,
                                         bits_per_sample))
                except audiotools.InvalidFormat:
                    continue


                if (new_file.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        BLANK_PCM_Reader(SHORT_LENGTH,
                                         sample_rate, channels,
                                         bits_per_sample)),
                                     True)

                    #lots of lossy formats convert BPS to 16 bits or float bits
                    #(MP3, Vorbis, etc.)
                    #only check an exact match on lossless
                    self.assertEqual(new_file.bits_per_sample(),
                                     bits_per_sample)
                    self.assertEqual(new_file.channels(),
                                     channels)
                    self.assertEqual(new_file.sample_rate(),sample_rate)
                else:
                    #If files are lossy,
                    #only be sure the lengths are the same.
                    #Everything else is too variable.

                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    self.assertEqual(
                        (D.Decimal(new_file.total_frames()) / \
                         new_file.sample_rate()).to_integral(),
                        SHORT_LENGTH,
                        "conversion mismatch on %sHz, %s channels, %s bps" % \
                            (sample_rate,channels,bits_per_sample))
                    pcm.close()

        finally:
            temp.close()

    def testwaveconversion(self):
        tempwav = tempfile.NamedTemporaryFile(suffix=".wav")
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp2 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))
            new_file.to_wave(tempwav.name)
            if (new_file.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    audiotools.WaveAudio(tempwav.name).to_pcm()),True)
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assertEqual(
                    (D.Decimal(len(counter) / 4) / 44100).to_integral(),
                    TEST_LENGTH)
                pcm.close()

            new_file2 = self.audio_class.from_wave(temp2.name,
                                                   tempwav.name)
            if (new_file2.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file2.to_pcm(),
                    new_file.to_pcm()),True)
            else:
                counter = PCM_Count()
                pcm = new_file2.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assert_(len(counter) > 0)
                pcm.close()
        finally:
            tempwav.close()
            temp.close()
            temp2.close()


    def testmassencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

        tempfiles = [(tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX),
            audio_class) for audio_class in audiotools.TYPE_MAP.values()]

        other_files = [audio_class.from_pcm(temp_file.name,
                                            BLANK_PCM_Reader(SHORT_LENGTH))
                       for (temp_file,audio_class) in tempfiles]
        for audio_file in other_files:
            audio_file.set_metadata(DummyMetaData3())

        try:
            for f in other_files:
                new_file = self.audio_class.from_pcm(
                    temp.name,
                    f.to_pcm())

                new_file.set_metadata(f.get_metadata())

                if (new_file.lossless() and f.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        f.to_pcm()),True,
                                     "PCM mismatch converting %s to %s" % \
                                     (repr(f),repr(new_file)))
                else:
                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    self.assert_(len(counter) > 0)

                new_file_metadata = new_file.get_metadata()
                f_metadata = f.get_metadata()

                if ((new_file_metadata is not None) and
                    (f_metadata is not None)):
                    self.assertEqual(
                        new_file_metadata,
                        f_metadata,
                        "metadata mismatch converting %s to %s (%s != %s)" % \
                        (repr(f),repr(new_file),
                         repr(f_metadata),
                         repr(new_file_metadata)))

                    if (new_file_metadata.supports_images() and
                        f_metadata.supports_images()):
                        self.assertEqual(new_file_metadata.images(),
                                         f_metadata.images())
        finally:
            temp.close()
            for (temp_file,audio_class) in tempfiles:
                temp_file.close()


    #just like testmassencode, but without file suffixes
    def testmassencode_nonsuffix(self):
        temp = tempfile.NamedTemporaryFile()

        tempfiles = [(tempfile.NamedTemporaryFile(),
                      audio_class) for audio_class in
                     audiotools.TYPE_MAP.values()]

        other_files = [audio_class.from_pcm(temp_file.name,
                                            BLANK_PCM_Reader(SHORT_LENGTH))
                       for (temp_file,audio_class) in tempfiles]
        for audio_file in other_files:
            audio_file.set_metadata(DummyMetaData3())

        try:
            for f in other_files:
                new_file = self.audio_class.from_pcm(
                    temp.name,
                    f.to_pcm())

                new_file.set_metadata(f.get_metadata())

                if (new_file.lossless() and f.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        f.to_pcm()),True,
                                     "PCM mismatch converting %s to %s" % \
                                     (repr(f),repr(new_file)))
                else:
                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    self.assert_(len(counter) > 0,
                                 "error converting %s to %s without suffix" % \
                                     (repr(f),repr(new_file)))

                new_file_metadata = new_file.get_metadata()
                f_metadata = f.get_metadata()

                if ((new_file_metadata is not None) and
                    (f_metadata is not None)):
                    self.assertEqual(
                        new_file_metadata,
                        f_metadata,
                        "metadata mismatch converting %s to %s (%s != %s)" % \
                        (repr(f),repr(new_file),
                         repr(f_metadata),
                         repr(new_file_metadata)))

                    if (new_file_metadata.supports_images() and
                        f_metadata.supports_images()):
                        self.assertEqual(new_file_metadata.images(),
                                         f_metadata.images())
        finally:
            temp.close()
            for (temp_file,audio_class) in tempfiles:
                temp_file.close()

    def testmetadata(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            metadata = DummyMetaData()
            new_file.set_metadata(metadata)
            if (new_file.get_metadata() is not None):
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

    def testimages(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if ((new_file.get_metadata() is not None)
                and (new_file.get_metadata().supports_images())):
                metadata = DummyMetaData()
                new_file.set_metadata(metadata)
                self.assertEqual(metadata,new_file.get_metadata())

                image1 = audiotools.Image.new(TEST_COVER1,u'',0)
                image2 = audiotools.Image.new(TEST_COVER2,u'',0)

                metadata.add_image(image1)
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)
                metadata.delete_image(metadata.images()[0])

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(len(metadata.images()),0)
                metadata.add_image(image2)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image2)
                self.assertEqual(metadata.front_covers()[0],image2)
        finally:
            temp.close()

    def testsplit(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(60))

            if (new_file.lossless()):
                PCM_LENGTHS = [s * 44100 for s in (5,10,15,4,16,10)]

                self.assertEqual(sum(PCM_LENGTHS),
                                 new_file.total_frames())

                for (sub_pcm,pcm_length) in zip(audiotools.pcm_split(
                    new_file.to_pcm(),
                    PCM_LENGTHS),
                                                PCM_LENGTHS):
                    sub_temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
                    try:
                        sub_file = self.audio_class.from_pcm(sub_temp.name,
                                                             sub_pcm)
                        self.assertEqual(sub_file.total_frames(),
                                         pcm_length)

                    finally:
                        sub_temp.close()

                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    audiotools.PCMCat(
                    audiotools.pcm_split(new_file.to_pcm(),PCM_LENGTHS))),
                                 True)

        finally:
            temp.close()


    #much like testmassencode, but using track2track
    def test_track2track_massencode(self):
        base_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            base = self.audio_class.from_pcm(base_file.name,
                                             BLANK_PCM_Reader(SHORT_LENGTH))
            metadata = DummyMetaData3()

            base.set_metadata(metadata)
            metadata = base.get_metadata()

            for new_audio_class in audiotools.TYPE_MAP.values():
                temp_file = tempfile.NamedTemporaryFile(
                    suffix="." + new_audio_class.SUFFIX)
                try:
                    subprocess.call(["track2track",
                                     '--no-replay-gain',
                                     "-t",new_audio_class.NAME,
                                     "-o",temp_file.name,
                                     base_file.name])

                    new_file = audiotools.open(temp_file.name)
                    self.assertEqual(new_file.NAME,new_audio_class.NAME)

                    if (base.lossless() and new_file.lossless()):
                        self.assertEqual(audiotools.pcm_cmp(
                                base.to_pcm(),
                                new_file.to_pcm()),True,
                                         "PCM mismatch converting %s to %s" % \
                                             (repr(base.NAME),
                                              repr(new_audio_class.NAME)))
                    else:
                        counter = PCM_Count()
                        pcm = new_file.to_pcm()
                        audiotools.transfer_data(pcm.read,counter.write)
                        self.assert_(len(counter) > 0)

                    new_metadata = new_file.get_metadata()

                    if ((metadata is not None) and
                        (new_metadata is not None)):
                        self.assertEqual(
                        new_metadata,
                        metadata,
                        "metadata mismatch converting %s to %s (%s != %s)" % \
                        (repr(base.NAME),
                         repr(new_audio_class.NAME),
                         repr(metadata),
                         repr(new_metadata)))

                        if (new_metadata.supports_images() and
                            metadata.supports_images()):
                            self.assertEqual(new_metadata.images(),
                                             metadata.images())

                finally:
                    temp_file.close()
        finally:
            base_file.close()

    #tests the splitting and concatenating programs
    def test_tracksplit_trackcat(self):
        if (not self.__is_lossless__()):
            return

        TOTAL_FRAMES = 24725400
        FILE_FRAMES = [8742384,7204176,8778840]
        CUE_SHEET = 'FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 03:16:55\n    INDEX 01 03:18:18\n  TRACK 03 AUDIO\n    INDEX 00 05:55:12\n    INDEX 01 06:01:45\n'

        base_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

        cue_file = tempfile.NamedTemporaryFile(suffix=".cue")
        cue_file.write(CUE_SHEET)
        cue_file.flush()

        joined_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

        try:
            base = self.audio_class.from_pcm(
                base_file.name,
                EXACT_RANDOM_PCM_Reader(TOTAL_FRAMES))

            if (not base.lossless()):
                return

            self.assertEqual(base.total_frames(),TOTAL_FRAMES)

            tempdir = tempfile.mkdtemp()

            subprocess.call(["tracksplit",
                             "-V","quiet",
                             "-t",self.audio_class.NAME,
                             "--cue=%s" % (cue_file.name),
                             "--no-replay-gain",
                             "-d",tempdir,
                             base.filename])

            split_files = list(audiotools.open_directory(tempdir))

            for (f,length) in zip(split_files,FILE_FRAMES):
                self.assertEqual(f.total_frames(),length)

            subprocess.call(["trackcat",
                             "-t",self.audio_class.NAME,
                             "-o",joined_file.name] + \
                            [f.filename for f in split_files])

            self.assertEqual(audiotools.pcm_cmp(
                    base.to_pcm(),
                    audiotools.open(joined_file.name).to_pcm()),
                             True)


            self.assertEqual(subprocess.call(["trackcmp",
                                              "-V","quiet",
                                              base.filename,
                                              joined_file.name]),0)

            self.assertEqual(subprocess.call(["trackcmp",
                                              "-V","quiet",
                                              base.filename,
                                              split_files[0].filename]),1)

            for f in split_files:
                os.unlink(f.filename)
            os.rmdir(tempdir)
        finally:
            base_file.close()
            cue_file.close()
            joined_file.close()

    def test_trackcmp(self):
        basedir = tempfile.mkdtemp()
        try:
            subdir1 = os.path.join(basedir,"subdir1")
            subdir2 = os.path.join(basedir,"subdir2")
            os.mkdir(subdir1)
            os.mkdir(subdir2)
            try:
                tempfile1 = self.audio_class.from_pcm(
                    os.path.join(subdir1,"track01.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(10))
                tempfile1.set_metadata(audiotools.MetaData(
                        track_number=1))

                tempfile2 = self.audio_class.from_pcm(
                    os.path.join(subdir1,"track02.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(5))
                tempfile2.set_metadata(audiotools.MetaData(
                        track_number=2))

                tempfile3 = self.audio_class.from_pcm(
                    os.path.join(subdir1,"track03.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(15))
                tempfile3.set_metadata(audiotools.MetaData(
                        track_number=3))
                try:
                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)
                    os.link(tempfile1.filename,
                            os.path.join(subdir2,
                                         "track01.%s" % \
                                             (self.audio_class.SUFFIX)))
                    tempfile4 = audiotools.open(
                            os.path.join(subdir2,
                                         "track01.%s" % \
                                             (self.audio_class.SUFFIX)))

                    self.assertEqual(filecmp.cmp(tempfile1.filename,
                                                 tempfile4.filename),
                                     True)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.link(tempfile2.filename,
                            os.path.join(subdir2,
                                         "track02.%s" % \
                                             (self.audio_class.SUFFIX)))
                    tempfile5 = audiotools.open(
                            os.path.join(subdir2,
                                         "track02.%s" % \
                                             (self.audio_class.SUFFIX)))

                    self.assertEqual(filecmp.cmp(tempfile2.filename,
                                                 tempfile5.filename),
                                     True)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.link(tempfile3.filename,
                            os.path.join(subdir2,
                                         "track03.%s" % \
                                             (self.audio_class.SUFFIX)))
                    tempfile6 = audiotools.open(
                            os.path.join(subdir2,
                                         "track03.%s" % \
                                             (self.audio_class.SUFFIX)))

                    self.assertEqual(filecmp.cmp(tempfile3.filename,
                                                 tempfile6.filename),
                                     True)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),0)

                    os.unlink(tempfile2.filename)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.unlink(tempfile3.filename)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.unlink(tempfile1.filename)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)
                finally:
                    for temp in (tempfile1,tempfile2,tempfile3,
                                 tempfile4,tempfile5,tempfile6):
                        if (os.path.isfile(temp.filename)):
                            os.unlink(temp.filename)
            finally:
                os.rmdir(subdir1)
                os.rmdir(subdir2)
        finally:
            os.rmdir(basedir)

    def test_tracklength(self):
        basedir = tempfile.mkdtemp()
        try:
            tempfile1 = self.audio_class.from_pcm(
                    os.path.join(basedir,"track01.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(10))

            tempfile2 = self.audio_class.from_pcm(
                    os.path.join(basedir,"track02.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(5))

            try:
                len1 = subprocess.Popen(["tracklength",
                                         tempfile1.filename],
                                        stdout=subprocess.PIPE)
                len1_result = len1.stdout.read()
                len1.wait()

                len2 = subprocess.Popen(["tracklength",
                                         tempfile2.filename],
                                        stdout=subprocess.PIPE)
                len2_result = len2.stdout.read()
                len2.wait()

                len3 = subprocess.Popen(["tracklength",
                                         basedir],
                                        stdout=subprocess.PIPE)
                len3_result = len3.stdout.read()
                len3.wait()

                self.assertEqual(len1_result,'0:00:10\n')
                self.assertEqual(len2_result,'0:00:05\n')
                self.assertEqual(len3_result,'0:00:15\n')
            finally:
                os.unlink(tempfile1.filename)
                os.unlink(tempfile2.filename)
        finally:
            os.rmdir(basedir)

    def test_tracktag_trackrename(self):
        template = "%(track_number)2.2d - %(album_number)d - %(album_track_number)s%(track_name)s%(album_name)s%(artist_name)s%(performer_name)s%(composer_name)s%(conductor_name)s%(media)s%(ISRC)s%(copyright)s%(publisher)s%(year)s%(suffix)s"

        basedir = tempfile.mkdtemp()
        try:
            track = self.audio_class.from_pcm(
                os.path.join(basedir,"track.%s" % (self.audio_class.SUFFIX)),
                BLANK_PCM_Reader(5))
            metadata = audiotools.MetaData(track_name="Name")
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if (metadata is None):
                return

            jpeg = os.path.join(basedir,"image1.jpg")
            png = os.path.join(basedir,"image2.png")

            f = open(jpeg,"wb")
            f.write(TEST_COVER1)
            f.close()
            f = open(png,"wb")
            f.write(TEST_COVER2)
            f.close()

            self.assertEqual(metadata.track_name,"Name")

            flag_field_values = zip(["--name",
                                     "--artist",
                                     "--performer",
                                     "--composer",
                                     "--conductor",
                                     "--album",
                                     "--number",
                                     "--ISRC",
                                     "--publisher",
                                     "--media-type",
                                     "--year",
                                     "--copyright",
                                     "--comment"],
                                    ["track_name",
                                     "artist_name",
                                     "performer_name",
                                     "composer_name",
                                     "conductor_name",
                                     "album_name",
                                     "track_number",
                                     "ISRC",
                                     "publisher",
                                     "media",
                                     "year",
                                     "copyright",
                                     "comment"],
                                    ["Track Name",
                                     "Artist Name",
                                     "Performer Name",
                                     "Composer Name",
                                     "Conductor Name",
                                     "Album Name",
                                     2,
                                     "ISRC-NUM",
                                     "Publisher Name",
                                     "Media",
                                     "2008",
                                     "Copyright Text",
                                     "Some Lengthy Text Comment"])

            for (flag,field,value) in flag_field_values:
                subprocess.call(["tracktag",
                                 flag,str(value),
                                 track.filename])
                setattr(metadata,field,value)
                self.assertEqual(metadata,track.get_metadata())

                new_path = os.path.join(basedir,
                                        self.audio_class.track_name(
                        metadata.track_number,
                        metadata,
                        metadata.album_number,
                        template))

                subprocess.call(["trackrename",
                                 "-V","quiet",
                                 "--format",template,
                                 track.filename])

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)

            os.rename(track.filename,
                      os.path.join(basedir,"track.%s" % \
                                       (self.audio_class.SUFFIX)))
            track = audiotools.open(os.path.join(basedir,"track.%s" % \
                                                     (self.audio_class.SUFFIX)))

            for (flag,field,value) in flag_field_values:
                subprocess.call(["tracktag",
                                 "--replace",
                                 flag,str(value),
                                 track.filename])
                metadata = audiotools.MetaData(**{field:value})
                self.assertEqual(metadata,track.get_metadata())

                os.rename(track.filename,
                          os.path.join(basedir,"track.%s" % \
                                           (self.audio_class.SUFFIX)))
                track = audiotools.open(os.path.join(basedir,"track.%s" % \
                                                         (self.audio_class.SUFFIX)))

                new_path = os.path.join(basedir,
                                        self.audio_class.track_name(
                        metadata.track_number,
                        metadata,
                        metadata.album_number,
                        template))

                subprocess.call(["trackrename",
                                 "-V","quiet",
                                 "--format",template,
                                 track.filename])

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)


            if (metadata.supports_images()):
                metadata = audiotools.MetaData(track_name='Images')
                track.set_metadata(metadata)
                self.assertEqual(metadata,track.get_metadata())

                flag_type_images_data = zip(["--front-cover",
                                             "--back-cover",
                                             "--leaflet",
                                             "--leaflet",
                                             "--media",
                                             "--other-image",],
                                            [0,1,2,2,3,4],
                                            [jpeg,jpeg,png,jpeg,png,jpeg],
                                            [TEST_COVER1,
                                             TEST_COVER1,
                                             TEST_COVER2,
                                             TEST_COVER1,
                                             TEST_COVER2,
                                             TEST_COVER1])

                for (flag,img_type,value,data) in flag_type_images_data:
                    subprocess.call(["tracktag",
                                     flag,str(value),
                                     track.filename])
                    metadata.add_image(audiotools.Image.new(
                            data,u"",img_type))
                    self.assertEqual(metadata.images(),
                                     track.get_metadata().images())

                for (flag,img_type,value,data) in flag_type_images_data:
                    subprocess.call(["tracktag",
                                     "--remove-images",
                                     flag,str(value),
                                     track.filename])
                    metadata = audiotools.MetaData(track_name='Images')
                    metadata.add_image(audiotools.Image.new(
                            data,u"",img_type))
                    self.assertEqual(metadata.images(),
                                     track.get_metadata().images())
        finally:
            for f in os.listdir(basedir):
                os.unlink(os.path.join(basedir,f))
            os.rmdir(basedir)

class TestForeignWaveChunks:
    def testforeignwavechunks(self):
        import filecmp

        tempwav1 = tempfile.NamedTemporaryFile(suffix=".wav")
        tempwav2 = tempfile.NamedTemporaryFile(suffix=".wav")
        audio = tempfile.NamedTemporaryFile(suffix='.'+self.audio_class.SUFFIX)
        try:
            #build a WAVE with some oddball chunks
            audiotools.WaveAudio.wave_from_chunks(
                tempwav1.name,
                [('fmt ','\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00'),
                 ('fooz','testtext'),
                 ('barz','somemoretesttext'),
                 ('bazz',chr(0) * 1024),
                 ('data','BZh91AY&SY\xdc\xd5\xc2\x8d\x06\xba\xa7\xc0\x00`\x00 \x000\x80MF\xa9$\x84\x9a\xa4\x92\x12qw$S\x85\t\r\xcd\\(\xd0'.decode('bz2'))])

            #convert it to our audio type
            wav = self.audio_class.from_wave(audio.name,
                                             tempwav1.name)

            #then convert it back to a WAVE
            wav.to_wave(tempwav2.name)

            #check that the two WAVEs are byte-for-byte identical
            self.assertEqual(filecmp.cmp(tempwav1.name,
                                         tempwav2.name,
                                         False),True)
        finally:
            tempwav1.close()
            tempwav2.close()
            audio.close()


class TestWaveAudio(TestForeignWaveChunks,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.WaveAudio

class TestAuAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.AuAudio

class TestFlacAudio(TestForeignWaveChunks,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio

    def testpreservevendortags(self):
        tempflac1 = tempfile.NamedTemporaryFile(suffix=".flac")
        tempflac2 = tempfile.NamedTemporaryFile(suffix=".flac")

        f1 = audiotools.FlacAudio.from_pcm(tempflac1.name,
                                           BLANK_PCM_Reader(3))
        f1.set_metadata(DummyMetaData())

        f2 = audiotools.FlacAudio.from_pcm(tempflac2.name,
                                           f1.to_pcm())

        f2.set_metadata(f1.get_metadata())

        self.assertEqual(f1.get_metadata().vorbis_comment.vendor_string,
                         f2.get_metadata().vorbis_comment.vendor_string)

class TestWavPackAudio(TestForeignWaveChunks,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio

class M4AMetadata:
    #M4A supports only a subset of the MetaData of every other format
    #so it must be handled separately
    def testmetadata(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if (new_file.get_metadata() is not None):
                metadata = audiotools.MetaData(track_name=u"Track Name",
                                               track_number=5,
                                               album_name=u"Album Name",
                                               artist_name=u"Artist Name",
                                               performer_name=u"Performer")
                new_file.set_metadata(metadata)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata,new_file.get_metadata())

                metadata2 = audiotools.MetaData(track_name=u"New Track Name",
                                                track_number=6,
                                                album_name=u"New Album Name",
                                                artist_name=u"New Artist Name",
                                                performer_name=u"New Performer")
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())

                metadata2.track_name = u'Track Name 3'
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())
        finally:
            temp.close()

    def testimages(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if ((new_file.get_metadata() is not None)
                and (new_file.get_metadata().supports_images())):
                metadata = SmallDummyMetaData()
                new_file.set_metadata(metadata)
                self.assertEqual(metadata,new_file.get_metadata())

                image1 = audiotools.Image.new(TEST_COVER1,u'',0)
                image2 = audiotools.Image.new(TEST_COVER2,u'',0)

                metadata.add_image(image1)
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)
                metadata.delete_image(metadata.images()[0])

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(len(metadata.images()),0)
                metadata.add_image(image2)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image2)
                self.assertEqual(metadata.front_covers()[0],image2)
        finally:
            temp.close()

# class TestAlacAudio(M4AMetadata,TestAiffAudio):
#    def setUp(self):
#        self.audio_class = audiotools.ALACAudio

class TestOggFlacAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.OggFlacAudio

class TestMP3Audio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.MP3Audio

class TestMP2Audio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio

class TestVorbisAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.VorbisAudio

class TestM4AAudio(M4AMetadata,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.M4AAudio

class TestAACAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.AACAudio

class TestMusepackAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.MusepackAudio

class TestSpeexAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.SpeexAudio

# class TestApeAudio(TestForeignWaveChunks,TestAiffAudio):
#    def setUp(self):
#        self.audio_class = audiotools.ApeAudio

class TestID3v2(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".mp3")

        self.mp3_file = audiotools.MP3Audio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    def __comment_test__(self,id3_class):
        self.mp3_file.set_metadata(
            id3_class.converted(DummyMetaData()))
        metadata = self.mp3_file.get_metadata()
        self.assertEqual(isinstance(metadata,id3_class),True)

        metadata.track_name = u"New Track Name"
        self.assertEqual(metadata.track_name,u"New Track Name")
        self.mp3_file.set_metadata(metadata)
        metadata2 = self.mp3_file.get_metadata()
        self.assertEqual(isinstance(metadata2,id3_class),True)
        self.assertEqual(metadata,metadata2)

        metadata = id3_class.converted(DummyMetaData3())
        for new_class in (audiotools.ID3v22Comment,
                          audiotools.ID3v23Comment,
                          audiotools.ID3v24Comment):
            self.assertEqual(metadata,new_class.converted(metadata))
            self.assertEqual(metadata.images(),
                             new_class.converted(metadata).images())

    def __dict_test__(self,id3_class):
        attribs1 = {}  #a dict of attribute -> value pairs ("track_name":u"foo")
        attribs2 = {}  #a dict of ID3v2 -> value pairs     ("TT2":u"foo")
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                attribs1[attribute] = attribs2[key] = u"value %d" % (i)
            else:
                attribs1[attribute] = attribs2[key] = i

        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        self.mp3_file.set_metadata(id3)
        self.assertEqual(self.mp3_file.get_metadata(),id3)
        id3 = self.mp3_file.get_metadata()

        #ensure that all the attributes match up
        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(id3,attribute),value)

        #ensure that all the keys match up
        for (key,value) in attribs2.items():
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(unicode(id3[key][0]),value)
            else:
                self.assertEqual(int(id3[key][0]),value)

        #ensure that changing attributes changes the underlying frame
        #>>> id3.track_name = u"bar"
        #>>> id3['TT2'][0] == u"bar"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                setattr(id3,attribute,u"new value %d" % (i))
                self.assertEqual(unicode(id3[key][0]),u"new value %d" % (i))
            else:
                setattr(id3,attribute,i + 10)
                self.assertEqual(int(id3[key][0]),i + 10)

        #reset and re-check everything for the next round
        id3 = id3_class.converted(audiotools.MetaData(**attribs1))
        self.mp3_file.set_metadata(id3)
        self.assertEqual(self.mp3_file.get_metadata(),id3)
        id3 = self.mp3_file.get_metadata()

        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(id3,attribute),value)

        for (key,value) in attribs2.items():
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(unicode(id3[key][0]),value)
            else:
                self.assertEqual(int(id3[key][0]),value)

        #ensure that changing the underlying frames changes attributes
        #>>> id3['TT2'] = [u"bar"]
        #>>> id3.track_name == u"bar"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                id3[key] = [u"new value %d" % (i)]
                self.mp3_file.set_metadata(id3)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(getattr(id3,attribute),u"new value %d" % (i))
            else:
                id3[key] = [i + 10]
                self.mp3_file.set_metadata(id3)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(getattr(id3,attribute),i + 10)

        #ensure that nutty track and album numbers are handled correctly
        #in both directions
        for attribute in ('track_number','album_number'):
            id3 = self.mp3_file.get_metadata()
            setattr(id3,attribute,u"5/10")
            self.mp3_file.set_metadata(id3)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(getattr(id3,attribute),5)
            self.assertEqual(
                unicode(id3[id3_class.ATTRIBUTE_MAP[attribute]][0]),u"5/10")

        id3.track_number = 1
        id3.album_number = 2
        self.mp3_file.set_metadata(id3)

        for attribute in ('track_number','album_number'):
            field = id3_class.ATTRIBUTE_MAP[attribute]
            id3 = self.mp3_file.get_metadata()
            id3[field] = [id3_class.TextFrame.from_unicode(field,u"5/10")]
            self.mp3_file.set_metadata(id3)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(getattr(id3,attribute),5)
            self.assertEqual(unicode(id3[field][0]),u"5/10")

        #finally, just for kicks, ensure that explicitly setting
        #frames also changes attributes
        #>>> id3['TT2'] = [id3_class.TextFrame.from_unicode('TT2',u"foo")]
        #>>> id3.track_name = u"foo"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            id3[key] = [id3_class.TextFrame.from_unicode(key,unicode(i))]
            self.mp3_file.set_metadata(id3)
            id3 = self.mp3_file.get_metadata()
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(getattr(id3,attribute),unicode(i))
            else:
                self.assertEqual(getattr(id3,attribute),i)

    def testid3v2_2(self):
        self.__comment_test__(audiotools.ID3v22Comment)
        self.__dict_test__(audiotools.ID3v22Comment)

    def testid3v2_3(self):
        self.__comment_test__(audiotools.ID3v23Comment)
        self.__dict_test__(audiotools.ID3v23Comment)

    def testid3v2_4(self):
        self.__comment_test__(audiotools.ID3v24Comment)
        self.__dict_test__(audiotools.ID3v24Comment)

    def testladder(self):
        self.mp3_file.set_metadata(DummyMetaData3())
        for new_class in (audiotools.ID3v22Comment,
                          audiotools.ID3v23Comment,
                          audiotools.ID3v24Comment,
                          audiotools.ID3v23Comment,
                          audiotools.ID3v22Comment):
            metadata = new_class.converted(self.mp3_file.get_metadata())
            self.mp3_file.set_metadata(metadata)
            metadata = self.mp3_file.get_metadata()
            self.assertEqual(isinstance(metadata,new_class),True)
            self.assertEqual(metadata.__comment_name__(),
                             new_class([]).__comment_name__())
            self.assertEqual(metadata,DummyMetaData3())
            self.assertEqual(metadata.images(),DummyMetaData3().images())

    def testsetpicture(self):
        m = DummyMetaData()
        m.add_image(audiotools.Image.new(TEST_COVER1,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         1))
        self.mp3_file.set_metadata(m)

        new_mp3_file = audiotools.open(self.file.name)
        m2 = new_mp3_file.get_metadata()

        self.assertEqual(m.images()[0].data,m2.images()[0].data)
        self.assertEqual(m.images()[0],m2.images()[0])

    def testconvertedpicture(self):
        flac_tempfile = tempfile.NamedTemporaryFile(suffix=".flac")

        try:
            flac_file = audiotools.FlacAudio.from_pcm(
                flac_tempfile.name,BLANK_PCM_Reader(TEST_LENGTH))

            m = DummyMetaData()
            m.add_image(audiotools.Image.new(
                TEST_COVER1,
                u'Unicode \u3057\u3066\u307f\u308b',
                1))
            flac_file.set_metadata(m)

            new_mp3 = audiotools.MP3Audio.from_pcm(
                self.file.name,
                flac_file.to_pcm())
            new_mp3.set_metadata(flac_file.get_metadata())

            self.assertEqual(flac_file.get_metadata().images(),
                             new_mp3.get_metadata().images())
        finally:
            flac_tempfile.close()

    def testucs2codec(self):
        #this should be 4 characters long in UCS-4 environments
        #if not, we're in a UCS-2 environment
        #which is limited to 16 bits anyway
        test_string = u'f\U0001d55foo'

        #u'\ufffd' is the "not found" character
        #this string should result from escaping through UCS-2
        test_string_out = u'f\ufffdoo'

        if (len(test_string) == 4):
            self.assertEqual(test_string,
                             test_string.encode('utf-16').decode('utf-16'))
            self.assertEqual(test_string.encode('ucs2').decode('ucs2'),
                             test_string_out)

            #ID3v2.4 supports UTF-8/UTF-16
            metadata = audiotools.ID3v24Comment.converted(DummyMetaData())
            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3,metadata)

            metadata.track_name = test_string

            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3,metadata)

            metadata.comment = test_string
            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3,metadata)

            metadata.add_image(audiotools.ID3v24Comment.PictureFrame.converted(
                    audiotools.Image.new(TEST_COVER1,
                                         test_string,
                                         0)))
            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3.images()[0].description,test_string)


            #ID3v2.3 and ID3v2.2 only support UCS-2
            for id3_class in (audiotools.ID3v23Comment,
                              audiotools.ID3v22Comment):
                metadata = audiotools.ID3v23Comment.converted(DummyMetaData())
                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3,metadata)

                #ensure that text fields round-trip correctly
                #(i.e. the extra-wide char gets replaced)
                metadata.track_name = test_string

                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3.track_name,test_string_out)

                #ensure that comment blocks round-trip correctly
                metadata.comment = test_string
                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3.track_name,test_string_out)

                #ensure that image comment fields round-trip correctly
                metadata.add_image(id3_class.PictureFrame.converted(
                        audiotools.Image.new(TEST_COVER1,
                                             test_string,
                                             0)))
                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3.images()[0].description,test_string_out)

    def tearDown(self):
        self.file.close()

class TestFlacComment(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.flac_file = audiotools.FlacAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    def testsetpicture(self):
        m = DummyMetaData()
        m.add_image(audiotools.Image.new(TEST_COVER1,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         1))
        self.flac_file.set_metadata(m)

        new_flac_file = audiotools.open(self.file.name)
        m2 = new_flac_file.get_metadata()

        self.assertEqual(m.images()[0],m2.images()[0])

    def testconvertedpicture(self):
        mp3_tempfile = tempfile.NamedTemporaryFile(suffix=".mp3")

        try:
            mp3_file = audiotools.MP3Audio.from_pcm(
                mp3_tempfile.name,BLANK_PCM_Reader(TEST_LENGTH))

            m = DummyMetaData()
            m.add_image(audiotools.Image.new(
                TEST_COVER1,
                u'Unicode \u3057\u3066\u307f\u308b',
                1))
            mp3_file.set_metadata(m)

            new_flac = audiotools.FlacAudio.from_pcm(
                self.file.name,
                mp3_file.to_pcm())
            new_flac.set_metadata(mp3_file.get_metadata())

            self.assertEqual(mp3_file.get_metadata().images(),
                             new_flac.get_metadata().images())
        finally:
            mp3_tempfile.close()

    def tearDown(self):
        self.file.close()

class TestPCMConversion(unittest.TestCase):
    def setUp(self):
        self.tempwav = tempfile.NamedTemporaryFile(suffix=".wav")

    def tearDown(self):
        self.tempwav.close()

    def testconversions(self):
        for (input,output) in Combinations(SHORT_PCM_COMBINATIONS,2):
            #print >>sys.stderr,repr(input),repr(output)
            reader = BLANK_PCM_Reader(5,
                                      sample_rate=input[0],
                                      channels=input[1],
                                      bits_per_sample=input[2])
            converter = audiotools.PCMConverter(reader,
                                                sample_rate=output[0],
                                                channels=output[1],
                                                bits_per_sample=output[2])
            wave = audiotools.WaveAudio.from_pcm(self.tempwav.name,converter)
            converter.close()

            self.assertEqual(wave.sample_rate(),output[0])
            self.assertEqual(wave.channels(),output[1])
            self.assertEqual(wave.bits_per_sample(),output[2])
            self.assertEqual((D.Decimal(wave.cd_frames()) / 75).to_integral(),
                             5)

class TestPCMStreamReader(unittest.TestCase):
    def testinvalidstreams(self):
        self.assertRaises(ValueError,
                          audiotools.pcmstream.PCMStreamReader,
                          cStringIO.StringIO(chr(0) * 10),0,False,False)

        self.assertRaises(ValueError,
                          audiotools.pcmstream.PCMStreamReader,
                          cStringIO.StringIO(chr(0) * 10),5,False,False)

        r = audiotools.pcmstream.PCMStreamReader(None,2,False,False)
        self.assertRaises(AttributeError,r.read,10)

    def testroundtrip(self):
        for (bytes_per_sample,big_endian) in ((1,False),(2,False),(3,False),
                                              (1,True), (2,True), (3, True)):
            #channels and sample_rate don't really matter here
            data = VARIABLE_PCM_Reader(TEST_LENGTH,
                                       bits_per_sample=bytes_per_sample * 8)
            converter = audiotools.pcmstream.PCMStreamReader(data,
                                                             bytes_per_sample,
                                                             big_endian,
                                                             False)
            md5sum = md5()
            d = converter.read(audiotools.BUFFER_SIZE)
            while (len(d) > 0):
                md5sum.update(audiotools.pcmstream.pcm_to_string(
                    d,bytes_per_sample,big_endian))
                d = converter.read(audiotools.BUFFER_SIZE)

            self.assertEqual(data.hexdigest(),md5sum.hexdigest())

    def testfloatroundtrip(self):
        for (bytes_per_sample,big_endian) in ((1,False),(2,False),(3,False),
                                              (1,True), (2,True), (3, True)):
            data = VARIABLE_PCM_Reader(TEST_LENGTH,
                                       bits_per_sample=bytes_per_sample * 8)
            multiplier = 1 << ((bytes_per_sample * 8) - 1)
            converter = audiotools.pcmstream.PCMStreamReader(data,
                                                             bytes_per_sample,
                                                             big_endian,
                                                             True)

            md5sum = md5()
            d = converter.read(audiotools.BUFFER_SIZE) #a list of floats
            while (len(d) > 0):
                md5sum.update(audiotools.pcmstream.pcm_to_string(
                    [int(round(f * multiplier)) for f in d],
                    bytes_per_sample,big_endian))
                d = converter.read(audiotools.BUFFER_SIZE)

            self.assertEqual(data.hexdigest(),md5sum.hexdigest())

    def testbyteswap(self):
        for (bytes_per_sample,big_endian) in ((1,False),(2,False),(3,False),
                                              (1,True), (2,True), (3, True)):
            data = VARIABLE_PCM_Reader(SHORT_LENGTH,
                                       bits_per_sample=bytes_per_sample * 8)
            converter = audiotools.pcmstream.PCMStreamReader(data,
                                                             bytes_per_sample,
                                                             big_endian,
                                                             False)
            #our byteswapped data
            dump = cStringIO.StringIO()
            d = converter.read(audiotools.BUFFER_SIZE)
            while (len(d) > 0):
               dump.write(audiotools.pcmstream.pcm_to_string(
                   d,bytes_per_sample,not big_endian))
               d = converter.read(audiotools.BUFFER_SIZE)

            dump.seek(0,0)

            new_data = audiotools.PCMReader(
                dump,
                sample_rate=data.sample_rate,
                bits_per_sample=data.bits_per_sample,
                channels=data.channels)

            converter = audiotools.pcmstream.PCMStreamReader(new_data,
                                                             bytes_per_sample,
                                                             not big_endian,
                                                             False)

            md5sum = md5()
            d = converter.read(audiotools.BUFFER_SIZE)
            while (len(d) > 0):
                md5sum.update(audiotools.pcmstream.pcm_to_string(
                    d,bytes_per_sample,big_endian))
                d = converter.read(audiotools.BUFFER_SIZE)

            self.assertEqual(data.hexdigest(),md5sum.hexdigest())

    def test8bitpcmtostring(self):
        def _8bits():
            for i in xrange(0x100):
                yield chr(i)

        le_parser = Con.ULInt8('s')
        be_parser = Con.UBInt8('s')

        for c in _8bits():
            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        le_parser.parse(c) - 0x7F],1,False))

            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        be_parser.parse(c) - 0x7F],1,True))

    def test16bitpcmtostring(self):
        def _16bits():
            for i in xrange(0x100):
                for j in xrange(0x100):
                    yield chr(i) + chr(j)

        le_parser = Con.SLInt16('s')
        be_parser = Con.SBInt16('s')

        for c in _16bits():
            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        le_parser.parse(c)],2,False))

            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        be_parser.parse(c)],2,True))

    #this is extremely time-consuming
    #and not a test you'll want to run all the time
    #def test24bitpcmtostring(self):
    #    def _24bits():
    #        for i in xrange(0x100):
    #            for j in xrange(0x100):
    #                for k in xrange(0x100):
    #                    yield chr(i) + chr(j) + chr(k)
    #
    #    le_parser = Con.BitStruct('bits',Con.Bits('value',24,
    #                                              swapped=True,
    #                                              signed=True))
    #
    #    be_parser = Con.BitStruct('bits',Con.Bits('value',24,
    #                                              swapped=False,
    #                                              signed=True))
    #
    #    for c in _24bits():
    #        self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
    #                    le_parser.parse(c).value],3,False))
    #
    #        self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
    #                    be_parser.parse(c).value],3,True))

class testbitstream(unittest.TestCase):
    def testinvalidstream(self):
        b = audiotools.bitstream.BitStreamReader(None)
        self.assertRaises(AttributeError,
                          b.read,10)

    def testcompliance(self):
        allbits = "".join(map(chr,range(0,0x100)) + \
                          map(chr,reversed(range(0,0x100)))) * 20
        for i in xrange(1,65):
            reader1 = Con.BitStreamReader(cStringIO.StringIO(allbits))
            reader2 = audiotools.bitstream.BitStreamReader(cStringIO.StringIO(allbits))
            sum1 = md5()
            sum2 = md5()

            for (reader,sum) in ((reader1,sum1),(reader2,sum2)):
                bits = reader.read(i)
                while (len(bits) > 0):
                    sum.update(bits)
                    bits = reader.read(i)
                reader.close()

            self.assertEqual(sum1.hexdigest(),sum2.hexdigest())

class testbufferedstream(unittest.TestCase):
    def testbuffer(self):
        reader = VARIABLE_PCM_Reader(TEST_LENGTH)
        bufferedreader = audiotools.BufferedPCMReader(reader)

        output = md5()

        s = bufferedreader.read(4096)
        while (len(s) > 0):
            output.update(s)
            s = bufferedreader.read(4096)

        self.assertEqual(output.hexdigest(),reader.hexdigest())

    def testrandombuffer(self):
        reader = VARIABLE_PCM_Reader(TEST_LENGTH)
        bufferedreader = audiotools.BufferedPCMReader(reader)
        size = reader.total_size

        output = md5()

        while (size > 0):
            buffer_length = min(size,random.randint(1,10000))
            s = bufferedreader.read(buffer_length)
            self.assertEqual(len(s),buffer_length)
            output.update(s)
            size -= buffer_length

        self.assertEqual(output.hexdigest(),reader.hexdigest())

class testtracknumber(unittest.TestCase):
    def testnumber(self):
        dir01 = tempfile.mkdtemp(suffix="01")
        dir02 = tempfile.mkdtemp(suffix="02")
        dir03 = tempfile.mkdtemp(suffix="03")
        try:
            file01 = audiotools.WaveAudio.from_pcm(
                os.path.join(dir03,"track01.wav"),
                BLANK_PCM_Reader(10))
            file02 = audiotools.WaveAudio.from_pcm(
                os.path.join(dir01,"track02.wav"),
                BLANK_PCM_Reader(10))
            file03 = audiotools.WaveAudio.from_pcm(
                os.path.join(dir02,"track03.wav"),
                BLANK_PCM_Reader(10))

            try:
                self.assertEqual(file01.track_number(),1)
                self.assertEqual(file02.track_number(),2)
                self.assertEqual(file03.track_number(),3)
            finally:
                os.unlink(file01.filename)
                os.unlink(file02.filename)
                os.unlink(file03.filename)
        finally:
            os.rmdir(dir01)
            os.rmdir(dir02)
            os.rmdir(dir03)

############
#END TESTS
############

if (__name__ == '__main__'):
    unittest.main()

