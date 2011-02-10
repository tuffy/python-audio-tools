#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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

import unittest
import audiotools
import ConfigParser
import tempfile
import os
import os.path
from hashlib import md5
import random
import decimal
import test_streams
from audiotools import Con

parser = ConfigParser.SafeConfigParser()
parser.read("test.cfg")

def do_nothing(self):
    pass

#add a bunch of decorator metafunctions like LIB_CORE
#which can be wrapped around individual tests as needed
for section in parser.sections():
    for option in parser.options(section):
        if (parser.getboolean(section, option)):
            vars()["%s_%s" % (section.upper(),
                              option.upper())] = lambda function: function
        else:
            vars()["%s_%s" % (section.upper(),
                              option.upper())] = lambda function: do_nothing

class BLANK_PCM_Reader:
    def __init__(self, length,
                 sample_rate=44100, channels=2, bits_per_sample=16,
                 channel_mask=None):
        self.length = length
        self.sample_rate = sample_rate
        self.channels = channels
        if (channel_mask is None):
            self.channel_mask = audiotools.ChannelMask.from_channels(channels)
        else:
            self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

        self.total_frames = length * sample_rate

        self.single_pcm_frame = audiotools.pcm.from_list(
            [1] * channels, channels, bits_per_sample, True)

    def read(self, bytes):
        if (self.total_frames > 0):
            frame = audiotools.pcm.from_frames(
                [self.single_pcm_frame] *
                min(self.single_pcm_frame.frame_count(bytes) / self.channels,
                    self.total_frames))
            self.total_frames -= frame.frames
            return frame
        else:
            return audiotools.pcm.FrameList(
                "", self.channels, self.bits_per_sample, True, True)

    def close(self):
        pass

class RANDOM_PCM_Reader(BLANK_PCM_Reader):
    def read(self, bytes):
        if (self.total_frames > 0):
            frames_to_read = min(
                self.single_pcm_frame.frame_count(bytes) / self.channels,
                self.total_frames)
            frame = audiotools.pcm.FrameList(
                os.urandom(frames_to_read *
                           (self.bits_per_sample / 8) *
                           self.channels),
                self.channels,
                self.bits_per_sample,
                True,
                True)
            self.total_frames -= frame.frames
            return frame
        else:
            return audiotools.pcm.FrameList(
                "", self.channels, self.bits_per_sample, True, True)

class MD5_Reader:
    def __init__(self, pcmreader):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.md5 = md5()

    def read(self, bytes):
        framelist = self.pcmreader.read(bytes)
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def close(self):
        self.pcmreader.close()

class Variable_Reader:
    def __init__(self, pcmreader):
        self.pcmreader = audiotools.BufferedPCMReader(pcmreader)
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.md5 = md5()
        self.range = range(self.channels * (self.bits_per_sample / 8),
                           4096)

    def read(self, bytes):
        return self.pcmreader.read(random.choice(self.range))

    def close(self):
        self.pcmreader.close()


class ERROR_PCM_Reader(audiotools.PCMReader):
    def __init__(self, error,
                 sample_rate=44100, channels=2, bits_per_sample=16,
                 channel_mask=None, failure_chance=.2, minimum_successes=0):
        if (channel_mask is None):
            channel_mask = audiotools.ChannelMask.from_channels(channels)
        audiotools.PCMReader.__init__(
            self,
            file=None,
            sample_rate=sample_rate,
            channels=channels,
            bits_per_sample=bits_per_sample,
            channel_mask=channel_mask)
        self.error = error

        #this is so we can generate some "live" PCM data
        #before erroring out due to our error
        self.failure_chance = failure_chance

        self.minimum_successes = minimum_successes

        self.frame = audiotools.pcm.from_list([0] * self.channels,
                                              self.channels,
                                              self.bits_per_sample,
                                              True)

    def read(self, bytes):
        if (self.minimum_successes > 0):
            self.minimum_successes -= 1
            return audiotools.pcm.from_frames(
                [self.frame for i in xrange(self.frame.frame_count(bytes))])
        else:
            if (random.random() <= self.failure_chance):
                raise self.error
            else:
                return audiotools.pcm.from_frames(
                    [self.frame for i in xrange(self.frame.frame_count(bytes))])

    def close(self):
        pass


class FrameCounter:
    def __init__(self, channels, bits_per_sample, sample_rate, value=0):
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.sample_rate = sample_rate
        self.value = value

    def update(self, f):
        self.value += len(f)

    def __int__(self):
        return int(round(decimal.Decimal(self.value) /
                         (self.channels *
                          (self.bits_per_sample / 8) *
                          self.sample_rate)))

def run_analysis(pcmreader):
    f = pcmreader.analyze_frame()
    while (f is not None):
        f = pcmreader.analyze_frame()


#probstat does this better, but I don't want to require that
#for something used only rarely
def Combinations(items, n):
    if (n == 0):
        yield []
    else:
        for i in xrange(len(items)):
            for combos in Combinations(items[i + 1:], n - 1):
                yield [items[i]] + combos


TEST_COVER1 = \
"""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
o/ez5iJPo7/8tO/0s8/+jxCO4T8AO2LoJg==""".decode('base64').decode('zlib')

TEST_COVER2 = \
"""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""".decode('base64').decode('zlib')

TEST_COVER3 = \
"""eJz7f+P/AwYBLzdPNwZGRkYGDyBk+H+bwZmBl5OLm4uDl5uLm4+Pl19YQVRYSEhYXUZOXEFP09BA\nT1NXx9jKy87YzM1cR9ch3NHNxy8oOMjILioxKiDBKzDIH2QIIx8fn7CgsJqoqJq/qa6pP8ng/wEG\nQQ6GFIYUZkZBBiZBRmZBxv9HGMTATkUGLBzsQHEJAUZGNBlmJiNHoIwImnogAIkKYoreYuBhZgRa\nxSzIYM9wpviCpICZQknDjcaLzEnsLrwdsiCuwwSfmS+4O6QFrBRyHF40bmRexHaED8R18FDz+cJ6\nBKYMSZeKsFoV0yOgsgnIuk7wdQg/ULP5wuaCTwvEoga4RUKc/baME5HdA9KVwu7CyXJ8XsMJJPdA\nLVrC0pRy3iEGyXAFMwewp5gcDZ8vMELzBZirMOPzBUkFNCdB/F75gmcCpt8VPCAemQBW1nCTEewk\nsEfk/98EALdspDk=\n""".decode('base64').decode('zlib')

#this is a very large, plain BMP encoded as bz2
HUGE_BMP = \
"""QlpoOTFBWSZTWSpJrRQACVR+SuEoCEAAQAEBEAIIAABAAAEgAAAIoABwU0yMTExApURDRoeppjv2
2uMceMt8M40qoj5nGLjFQkcuWdsL3rW+ugRSA6SFFV4lUR1/F3JFOFCQKkmtFA==""".decode('base64')


class AudioFileTest(unittest.TestCase):
    def setUp(self):
        self.audio_class = audiotools.AudioFile
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AUDIOFILE
    def test_init(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        #first check nonexistent files
        self.assertRaises(audiotools.InvalidFile,
                          self.audio_class,
                          "/dev/null/foo.%s" % (self.audio_class.SUFFIX))

        f = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            #then check empty files
            f.write("")
            f.flush()
            self.assertEqual(os.path.isfile(f.name), True)
            self.assertRaises(audiotools.InvalidFile,
                              self.audio_class,
                              f.name)

            #then check files with a bit of junk at the beginning
            f.write("".join(map(chr,
                                [26, 83, 201, 240, 73, 178, 34, 67, 87, 214])))
            f.flush()
            self.assert_(os.path.getsize(f.name) > 0)
            self.assertRaises(audiotools.InvalidFile,
                              self.audio_class,
                              f.name)

            #finally, check unreadable files
            original_stat = os.stat(f.name)[0]
            try:
                os.chmod(f.name, 0)
                self.assertRaises(audiotools.InvalidFile,
                                  self.audio_class,
                                  f.name)
            finally:
                os.chmod(f.name, original_stat)
        finally:
            f.close()

    @FORMAT_AUDIOFILE
    def test_is_type(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        valid = tempfile.NamedTemporaryFile(suffix=self.suffix)
        invalid = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            #generate a valid file and check its is_type routine
            self.audio_class.from_pcm(valid.name, BLANK_PCM_Reader(1))
            f = open(valid.name, 'rb')
            self.assertEqual(self.audio_class.is_type(f), True)
            f.close()

            #generate several invalid files and check its is_type routine
            for i in xrange(256):
                self.assertEqual(os.path.getsize(invalid.name), i)
                f = open(invalid.name, 'rb')
                self.assertEqual(self.audio_class.is_type(f), False)
                f.close()
                invalid.write(os.urandom(1))
                invalid.flush()

        finally:
            valid.close()
            invalid.close()

    @FORMAT_AUDIOFILE
    def test_bits_per_sample(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for bps in (8, 16, 24):
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, bits_per_sample=bps))
                self.assertEqual(track.bits_per_sample(), bps)
                track2 = audiotools.open(temp.name)
                self.assertEqual(track2.bits_per_sample(), bps)
        finally:
            temp.close()

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_channels(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_channel_mask(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_sample_rate(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_lossless(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE
    def test_metadata(self):
        import string
        import random

        #a nice sampling of Unicode characters
        chars = u"".join(map(unichr,
                             range(0x30, 0x39 + 1) +
                             range(0x41, 0x5A + 1) +
                             range(0x61, 0x7A + 1) +
                             range(0xC0, 0x17E + 1) +
                             range(0x18A, 0x1EB + 1) +
                             range(0x3041, 0x3096 + 1) +
                             range(0x30A1, 0x30FA + 1)))


        if (self.audio_class is audiotools.AudioFile):
            return

        dummy_metadata = audiotools.MetaData(**dict(
                [(field, char) for (field, char) in
                 zip(audiotools.MetaData.__FIELDS__,
                     string.ascii_letters)
                 if field not in audiotools.MetaData.__INTEGER_FIELDS__] +
                [(field, i + 1) for (i, field) in
                 enumerate(audiotools.MetaData.__INTEGER_FIELDS__)]))
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(1))
            track.set_metadata(dummy_metadata)
            track = audiotools.open(temp.name)
            metadata = track.get_metadata()
            if (metadata is None):
                return

            #not all formats necessarily support all metadata fields
            #we'll only test the fields that are supported
            live_fields = ([field for field in audiotools.MetaData.__FIELDS__
                            if ((field not in
                                 audiotools.MetaData.__INTEGER_FIELDS__) and
                                (len(getattr(metadata, field)) > 0))] +
                           [field for field in
                            audiotools.MetaData.__INTEGER_FIELDS__
                            if (getattr(metadata, field) > 0)])

            #check that setting the fields to random values works
            for field in live_fields:
                if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                    unicode_string = u"".join(
                        [random.choice(chars)
                         for i in xrange(random.choice(range(1, 21)))])
                    setattr(metadata, field, unicode_string)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), unicode_string)
                else:
                    number = random.choice(range(1, 100))
                    setattr(metadata, field, number)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), number)

            #check that blanking out the fields works
            for field in live_fields:
                if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                    setattr(metadata, field, u"")
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), u"")
                else:
                    setattr(metadata, field, 0)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), 0)

            #re-set the fields with random values
            for field in live_fields:
                if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                    unicode_string = u"".join(
                        [random.choice(chars)
                         for i in xrange(random.choice(range(1, 21)))])
                    setattr(metadata, field, unicode_string)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), unicode_string)
                else:
                    number = random.choice(range(1, 100))
                    setattr(metadata, field, number)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), number)

            #check that deleting the fields works
            for field in live_fields:
                delattr(metadata, field)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                    self.assertEqual(getattr(metadata, field), u"")
                else:
                    self.assertEqual(getattr(metadata, field), 0)

            #check that delete_metadata works
            nonblank_metadata = audiotools.MetaData(**dict(
                    [(field, c) for (field, c) in zip(
                            live_fields,
                            string.ascii_letters)
                     if field not in
                     audiotools.MetaData.__INTEGER_FIELDS__] +
                    [(field, i + 1) for (i, field) in enumerate(
                            live_fields)
                     if field in
                     audiotools.MetaData.__INTEGER_FIELDS__]))
            track.set_metadata(nonblank_metadata)
            self.assertEqual(track.get_metadata(), nonblank_metadata)
            track.delete_metadata()
            metadata = track.get_metadata()
            if (metadata is not None):
                for field in live_fields:
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                        self.assertEqual(getattr(metadata, field), u"")
                    else:
                        self.assertEqual(getattr(metadata, field), 0)

            track.set_metadata(nonblank_metadata)
            self.assertEqual(track.get_metadata(), nonblank_metadata)

            old_mode = os.stat(track.filename).st_mode
            os.chmod(track.filename, 0400)
            try:
                #check IOError on set_metadata()
                self.assertRaises(IOError,
                                  track.set_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #check IOError on delete_metadata()
                self.assertRaises(IOError,
                                  track.delete_metadata)
            finally:
                os.chmod(track.filename, old_mode)

            os.chmod(track.filename, 0)
            try:
                #check IOError on get_metadata()
                self.assertRaises(IOError,
                                  track.get_metadata)
            finally:
                os.chmod(track.filename, old_mode)

            #check merge
            def field_val(field, value, int_value):
                if (field in audiotools.MetaData.__INTEGER_FIELDS__):
                    return int_value
                else:
                    return value

            for i in xrange(10):
                shuffled_fields = live_fields[:]
                random.shuffle(shuffled_fields)

                for (range_a, range_b) in [
                    ((0, len(shuffled_fields) / 3), #no overlap
                     (-(len(shuffled_fields) / 3),
                       len(shuffled_fields) + 1)),

                    ((0, len(shuffled_fields) / 2), #partial overlap
                     (len(shuffled_fields) / 4,
                      len(shuffled_fields) / 4 + len(shuffled_fields) / 2)),

                    ((0, len(shuffled_fields) / 3), #complete overlap
                     (0, len(shuffled_fields) / 3))]:
                    fields_a = shuffled_fields[range_a[0]:range_a[1]]
                    fields_b = shuffled_fields[range_b[0]:range_b[1]]

                    metadata_a = audiotools.MetaData(**dict([
                                (field, field_val(field, u"a", 1)) for field
                                in fields_a]))
                    metadata_b = audiotools.MetaData(**dict([
                                (field, field_val(field, u"b", 2)) for field
                                in fields_b]))

                    track.delete_metadata()
                    track.set_metadata(metadata_a)
                    metadata_c = track.get_metadata()
                    self.assertEqual(metadata_c, metadata_a)
                    metadata_c.merge(metadata_b)
                    track.set_metadata(metadata_c)
                    metadata_c = track.get_metadata()

                    for field in live_fields:
                        if (field in fields_a):
                            if (field in
                                audiotools.MetaData.__INTEGER_FIELDS__):
                                self.assertEqual(getattr(metadata_c, field),
                                                 1)
                            else:
                                self.assertEqual(getattr(metadata_c, field),
                                                 u"a")
                        elif (field in fields_b):
                            if (field in
                                audiotools.MetaData.__INTEGER_FIELDS__):
                                self.assertEqual(getattr(metadata_c, field),
                                                 2)
                            else:
                                self.assertEqual(getattr(metadata_c, field),
                                                 u"b")
                        else:
                            if (field in
                                audiotools.MetaData.__INTEGER_FIELDS__):
                                self.assertEqual(getattr(metadata_c, field),
                                                 0)
                            else:
                                self.assertEqual(getattr(metadata_c, field),
                                                 u"")

            #check images
            metadata = audiotools.MetaData(**dict(
                    [(field, getattr(dummy_metadata, field))
                     for field in live_fields]))
            image_1 = audiotools.Image.new(TEST_COVER1, u"", 0)
            metadata.add_image(image_1)
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if (len(metadata.images()) > 0):
                #only check if images are actually supported

                self.assertEqual(metadata.images()[0], image_1)
                self.assertEqual(metadata.front_covers()[0], image_1)

                metadata.delete_image(metadata.images()[0])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(len(metadata.images()), 0)

                image_2 = audiotools.Image.new(TEST_COVER2, u"", 0)
                metadata.add_image(image_2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images()[0], image_2)
                self.assertEqual(metadata.front_covers()[0], image_2)


        finally:
            temp.close()

    @FORMAT_AUDIOFILE
    def test_length(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for seconds in [1, 2, 3, 4, 5, 10, 20, 60, 120]:
                track = self.audio_class.from_pcm(temp.name,
                                                  BLANK_PCM_Reader(seconds))
                self.assertEqual(track.total_frames(), seconds * 44100)
                self.assertEqual(track.cd_frames(), seconds * 75)
                self.assertEqual(track.seconds_length(), seconds)
        finally:
            temp.close()

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_pcm(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_convert(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE
    def test_track_number(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp_dir = tempfile.mkdtemp()
        try:
            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.track_number(), 0)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "01 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.track_number(), 1)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "202 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.track_number(), 2)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "303 45 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.track_number(), 3)

            track.set_metadata(audiotools.MetaData(track_number=2))
            metadata = track.get_metadata()
            if (metadata is not None):
                self.assertEqual(track.track_number(), 2)

                track = audiotools.open(
                    os.path.join(temp_dir, "202 - abcde" + self.suffix))
                track.set_metadata(audiotools.MetaData(track_number=1))
                self.assertEqual(track.get_metadata().track_number, 1)

                track = audiotools.open(
                    os.path.join(temp_dir, "01 - abcde" + self.suffix))
                track.set_metadata(audiotools.MetaData(track_number=3))
                self.assertEqual(track.get_metadata().track_number, 3)

                track = audiotools.open(
                    os.path.join(temp_dir, "abcde" + self.suffix))
                track.set_metadata(audiotools.MetaData(track_number=4))
                self.assertEqual(track.get_metadata().track_number, 4)
        finally:
            for f in os.listdir(temp_dir):
                os.unlink(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    @FORMAT_AUDIOFILE
    def test_album_number(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp_dir = tempfile.mkdtemp()
        try:
            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.album_number(), 0)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "01 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.album_number(), 0)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "202 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.album_number(), 2)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "303 45 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            self.assertEqual(track.album_number(), 3)

            track.set_metadata(audiotools.MetaData(album_number=2))
            metadata = track.get_metadata()
            if (metadata is not None):
                self.assertEqual(track.album_number(), 2)

                track = audiotools.open(
                    os.path.join(temp_dir, "202 - abcde" + self.suffix))
                track.set_metadata(audiotools.MetaData(album_number=1))
                self.assertEqual(track.album_number(), 1)

                track = audiotools.open(
                    os.path.join(temp_dir, "01 - abcde" + self.suffix))
                track.set_metadata(audiotools.MetaData(album_number=3))
                self.assertEqual(track.album_number(), 3)

                track = audiotools.open(
                    os.path.join(temp_dir, "abcde" + self.suffix))
                track.set_metadata(audiotools.MetaData(album_number=4))
                self.assertEqual(track.album_number(), 4)
        finally:
            for f in os.listdir(temp_dir):
                os.unlink(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    @FORMAT_AUDIOFILE
    def test_track_name(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        format_template = u"Fo\u00f3 %%(%(field)s)s"
        #first, test the many unicode string fields
        for field in audiotools.MetaData.__FIELDS__:
            if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                metadata = audiotools.MetaData()
                value = u"\u00dcnicode value \u2ec1"
                setattr(metadata, field, value)
                format_string = format_template % {u"field":
                                                       field.decode('ascii')}
                track_name = self.audio_class.track_name(
                    file_path="track",
                    track_metadata=metadata,
                    format=format_string.encode('utf-8'))
                self.assert_(len(track_name) > 0)
                self.assertEqual(
                    track_name,
                    (format_template % {u"field": u"foo"} % {u"foo": value}).encode(audiotools.FS_ENCODING))

        #then, check integer fields
        format_template = u"Fo\u00f3 %(album_number)d %(track_number)2.2d %(album_track_number)s"

        #first, check integers pulled from track metadata
        for (track_number, album_number, album_track_number) in [
            (0, 0, u"00"),
            (1, 0, u"01"),
            (25, 0, u"25"),
            (0, 1, u"100"),
            (1, 1, u"101"),
            (25, 1, u"125"),
            (0, 36, u"3600"),
            (1, 36, u"3601"),
            (25, 36, u"3625")]:
            for basepath in ["track",
                             "/foo/bar/track",
                             (u"/f\u00f3o/bar/tr\u00e1ck").encode(audiotools.FS_ENCODING)]:
                metadata = audiotools.MetaData(track_number=track_number,
                                               album_number=album_number)
                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"album_number": album_number,
                                                     u"track_number": track_number,
                                                     u"album_track_number": album_track_number}).encode('utf-8'))

        #then, check integers pulled from the track filename
        for metadata in [None, audiotools.MetaData()]:
            for basepath in ["track",
                             "/foo/bar/track",
                             (u"/f\u00f3o/bar/tr\u00e1ck").encode(audiotools.FS_ENCODING)]:
                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "01",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"album_number": 0,
                                                     u"track_number": 1,
                                                     u"album_track_number": u"01"}).encode('utf-8'))

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "track23",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"album_number": 0,
                                                     u"track_number": 23,
                                                     u"album_track_number": u"23"}).encode('utf-8'))

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "track123",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"album_number": 1,
                                                     u"track_number": 23,
                                                     u"album_track_number": u"123"}).encode('utf-8'))

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "4567",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"album_number": 45,
                                                     u"track_number": 67,
                                                     u"album_track_number": u"4567"}).encode('utf-8'))

        #then, ensure metadata takes precedence over filename for integers
        for (track_number, album_number,
             album_track_number, incorrect) in [(1, 0, u"01", "10"),
                                               (25, 0, u"25", "52"),
                                               (1, 1, u"101", "210"),
                                               (25, 1, u"125", "214"),
                                               (1, 36, u"3601", "4710"),
                                               (25, 36, u"3625", "4714")]:
            for basepath in ["track",
                             "/foo/bar/track",
                             (u"/f\u00f3o/bar/tr\u00e1ck").encode(audiotools.FS_ENCODING)]:
                metadata = audiotools.MetaData(track_number=track_number,
                                               album_number=album_number)
                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + incorrect,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"album_number": album_number,
                                                     u"track_number": track_number,
                                                     u"album_track_number": album_track_number}).encode('utf-8'))

        #also, check track_total/album_total from metadata
        format_template = u"Fo\u00f3 %(track_total)d %(album_total)d"
        for track_total in [0, 1, 25, 99]:
            for album_total in [0, 1, 25, 99]:
                metadata = audiotools.MetaData(track_total=track_total,
                                               album_total=album_total)
                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + incorrect,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"track_total": track_total,
                                                     u"album_total": album_total}).encode('utf-8'))

        #ensure %(basename)s is set properly
        format_template = u"Fo\u00f3 %(basename)s"
        for (path, base) in [("track", "track"),
                            ("/foo/bar/track", "track"),
                            ((u"/f\u00f3o/bar/tr\u00e1ck").encode(audiotools.FS_ENCODING), u"tr\u00e1ck")]:
            for metadata in [None, audiotools.MetaData()]:
                self.assertEqual(self.audio_class.track_name(
                        file_path=path,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"basename": base}).encode('utf-8'))

        #finally, ensure %(suffix)s is set properly
        format_template = u"Fo\u00f3 %(suffix)s"
        for path in ["track",
                     "/foo/bar/track",
                     (u"/f\u00f3o/bar/tr\u00e1ck").encode(audiotools.FS_ENCODING)]:
            for metadata in [None, audiotools.MetaData()]:
                self.assertEqual(self.audio_class.track_name(
                        file_path=path,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {u"suffix": self.audio_class.SUFFIX.decode('ascii')}).encode('utf-8'))

    @FORMAT_AUDIOFILE
    def test_replay_gain(self):
        if (self.audio_class.can_add_replay_gain() and
            self.audio_class.lossless_replay_gain()):
            track_data1 = test_streams.Sine16_Stereo(44100, 44100,
                                                     441.0, 0.50,
                                                     4410.0, 0.49, 1.0)

            track_data2 = test_streams.Sine16_Stereo(66150, 44100,
                                                     8820.0, 0.70,
                                                     4410.0, 0.29, 1.0)

            track_data3 = test_streams.Sine16_Stereo(52920, 44100,
                                                     441.0, 0.50,
                                                     441.0, 0.49, 0.5)

            track_file1 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
            track_file2 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
            track_file3 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
            try:
                track1 = self.audio_class.from_pcm(track_file1.name,
                                                   track_data1)
                track2 = self.audio_class.from_pcm(track_file2.name,
                                                   track_data2)
                track3 = self.audio_class.from_pcm(track_file3.name,
                                                   track_data3)

                self.assert_(track1.replay_gain() is None)
                self.assert_(track2.replay_gain() is None)
                self.assert_(track3.replay_gain() is None)

                self.audio_class.add_replay_gain([track_file1.name,
                                                  track_file2.name,
                                                  track_file3.name])

                gains = audiotools.replaygain.ReplayGain(44100)

                track_data1.reset()
                audiotools.transfer_data(track_data1.read, gains.update)
                track_gain1 = track1.replay_gain()
                (track_gain, track_peak) = gains.title_gain()
                self.assertEqual(round(track_gain1.track_gain, 4),
                                 round(track_gain, 4))
                self.assertEqual(round(track_gain1.track_peak, 4),
                                 round(track_peak, 4))

                track_data2.reset()
                audiotools.transfer_data(track_data2.read, gains.update)
                track_gain2 = track2.replay_gain()
                (track_gain, track_peak) = gains.title_gain()
                self.assertEqual(round(track_gain2.track_gain, 4),
                                 round(track_gain, 4))
                self.assertEqual(round(track_gain2.track_peak, 4),
                                 round(track_peak, 4))

                track_data3.reset()
                audiotools.transfer_data(track_data3.read, gains.update)
                track_gain3 = track3.replay_gain()
                (track_gain, track_peak) = gains.title_gain()
                self.assertEqual(round(track_gain3.track_gain, 4),
                                 round(track_gain, 4))
                self.assertEqual(round(track_gain3.track_peak, 4),
                                 round(track_peak, 4))

                album_gains = [round(t.replay_gain().album_gain, 4) for t in
                               [track1, track2, track3]]
                self.assertEqual(len(set(album_gains)), 1)
                album_peaks = [round(t.replay_gain().album_peak, 4) for t in
                               [track1, track2, track3]]
                self.assertEqual(len(set(album_peaks)), 1)

                (album_gain, album_peak) = gains.album_gain()
                self.assertEqual(album_gains[0], round(album_gain, 4))
                self.assertEqual(album_peaks[0], round(album_peak, 4))

                #FIXME - check that add_replay_gain raises
                #an exception when files are unreadable

                #FIXME - check that add_replay_gain raises
                #an exception when files are unwritable

                #FIXME - check that add_replay_gain raises
                #an exception when reading files produces an error

            finally:
                track_file1.close()
                track_file2.close()
                track_file3.close()


    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_cuesheet(self):
        self.assert_(False)

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_verify(self):
        self.assert_(False)


class LosslessFileTest(AudioFileTest):
    @FORMAT_LOSSLESS
    def test_lossless(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(1))
            self.assertEqual(track.lossless(), True)
            track = audiotools.open(temp.name)
            self.assertEqual(track.lossless(), True)
        finally:
            temp.close()

    @FORMAT_LOSSLESS
    def test_channels(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for channels in [1, 2, 3, 4, 5, 6]:
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=channels, channel_mask=0))
            self.assertEqual(track.channels(), channels)
            track = audiotools.open(temp.name)
            self.assertEqual(track.channels(), channels)
        finally:
            temp.close()

    @FORMAT_LOSSLESS
    def test_channel_mask(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for mask in [["front_center"],
                         ["front_left",
                          "front_right"],
                         ["front_left",
                          "front_right",
                          "front_center"],
                         ["front_left",
                          "front_right",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "low_frequency",
                          "back_left",
                          "back_right"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f,True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
        finally:
            temp.close()

    @FORMAT_LOSSLESS
    def test_sample_rate(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for rate in [8000, 16000, 22050, 44100, 48000,
                         96000, 192000]:
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, sample_rate=rate))
                self.assertEqual(track.sample_rate(), rate)
                track = audiotools.open(temp.name)
                self.assertEqual(track.sample_rate(), rate)
        finally:
            temp.close()

    @FORMAT_LOSSLESS
    def test_pcm(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        temp2 = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.mkdtemp()
        try:
            for compression in (None,) + self.audio_class.COMPRESSION_MODES:
                #test silence
                reader = MD5_Reader(BLANK_PCM_Reader(1))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)
                checksum = md5()
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   checksum.update)
                self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                #test random noise
                reader = MD5_Reader(RANDOM_PCM_Reader(1))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)
                checksum = md5()
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   checksum.update)
                self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                #test randomly-sized chunks of silence
                reader = MD5_Reader(Variable_Reader(BLANK_PCM_Reader(10)))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)
                checksum = md5()
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   checksum.update)
                self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                #test randomly-sized chunks of random noise
                reader = MD5_Reader(Variable_Reader(RANDOM_PCM_Reader(10)))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)
                checksum = md5()
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   checksum.update)
                self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                #test PCMReaders that trigger a DecodingError
                self.assertRaises(ValueError,
                                  ERROR_PCM_Reader(ValueError("error"),
                                                   failure_chance=1.0).read,
                                  1)
                self.assertRaises(IOError,
                                  ERROR_PCM_Reader(IOError("error"),
                                                   failure_chance=1.0).read,
                                  1)
                self.assertRaises(audiotools.EncodingError,
                                  self.audio_class.from_pcm,
                                  os.path.join(temp_dir,
                                               "invalid" + self.suffix),
                                  ERROR_PCM_Reader(IOError("I/O Error")))

                self.assertEqual(os.path.isfile(
                        os.path.join(temp_dir,
                                     "invalid" + self.suffix)),
                                 False)

                self.assertRaises(audiotools.EncodingError,
                                  self.audio_class.from_pcm,
                                  os.path.join(temp_dir,
                                               "invalid" + self.suffix),
                                  ERROR_PCM_Reader(IOError("I/O Error")))

                self.assertEqual(os.path.isfile(
                        os.path.join(temp_dir,
                                     "invalid" + self.suffix)),
                                 False)

                #test unwritable output file
                self.assertRaises(audiotools.EncodingError,
                                  self.audio_class.from_pcm,
                                  "/dev/null/foo.%s" % (self.suffix),
                                  BLANK_PCM_Reader(1))

                #test without suffix
                reader = MD5_Reader(BLANK_PCM_Reader(1))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp2.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp2.name, reader,
                                                      compression)
                checksum = md5()
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   checksum.update)
                self.assertEqual(reader.hexdigest(), checksum.hexdigest())
        finally:
            temp.close()
            temp2.close()
            for f in os.listdir(temp_dir):
                os.unlink(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    # @FORMAT_LOSSLESS
    @LIB_CUSTOM
    def test_convert(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        #check various round-trip options
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                test_streams.Sine16_Stereo(220500, 44100,
                                           8820.0, 0.70, 4410.0, 0.29, 1.0))
            for audio_class in audiotools.AVAILABLE_TYPES:
                temp2 = tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)
                try:
                    track2 = track.convert(temp2.name,
                                           audio_class)
                    if (track2.lossless()):
                        self.assert_(
                            audiotools.pcm_frame_cmp(track.to_pcm(),
                                                     track2.to_pcm()) is None,
                            "error round-tripping %s to %s" % \
                                (self.audio_class.NAME,
                                 audio_class.NAME))
                    else:
                        counter = FrameCounter(2, 16, 44100)
                        audiotools.transfer_framelist_data(track.to_pcm(),
                                                           counter.update)
                        self.assertEqual(
                            int(counter), 5,
                            "mismatch encoding %s at quality %s" % \
                                (self.audio_class.NAME,
                                 compression))

                    for compression in audio_class.COMPRESSION_MODES:
                        track2 = track.convert(temp2.name,
                                               audio_class,
                                               compression)
                        if (track2.lossless()):
                            self.assert_(
                                audiotools.pcm_frame_cmp(
                                    track.to_pcm(), track2.to_pcm()) is None,
                                "error round-tripping %s to %s at %s" % \
                                    (self.audio_class.NAME,
                                     audio_class.NAME,
                                     compression))
                        else:
                            counter = FrameCounter(2, 16, 44100)
                            audiotools.transfer_framelist_data(track.to_pcm(),
                                                               counter.update)
                            self.assertEqual(
                                int(counter), 5,
                                "mismatch encoding %s at quality %s" % \
                                    (self.audio_class.NAME,
                                     compression))

                finally:
                    temp2.close()
        finally:
            temp.close()


class LossyFileTest(AudioFileTest):
    @FORMAT_LOSSY
    def test_bits_per_sample(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for bps in (8, 16, 24):
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, bits_per_sample=bps))
                self.assertEqual(track.bits_per_sample(), 16)
                track2 = audiotools.open(temp.name)
                self.assertEqual(track2.bits_per_sample(), 16)
        finally:
            temp.close()

    @FORMAT_LOSSY
    def test_lossless(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(1))
            self.assertEqual(track.lossless(), False)
            track = audiotools.open(temp.name)
            self.assertEqual(track.lossless(), False)
        finally:
            temp.close()

    @FORMAT_LOSSY
    def test_channels(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for channels in [1, 2, 3, 4, 5, 6]:
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=channels, channel_mask=0))
            self.assertEqual(track.channels(), 2)
            track = audiotools.open(temp.name)
            self.assertEqual(track.channels(), 2)
        finally:
            temp.close()

    @FORMAT_LOSSY
    def test_channel_mask(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            cm = audiotools.ChannelMask.from_fields(
                front_left=True,
                front_right=True)
            track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                    1, channels=len(cm), channel_mask=int(cm)))
            self.assertEqual(track.channels(), len(cm))
            self.assertEqual(track.channel_mask(), cm)
            track = audiotools.open(temp.name)
            self.assertEqual(track.channels(), len(cm))
            self.assertEqual(track.channel_mask(), cm)
        finally:
            temp.close()

    @FORMAT_LOSSY
    def test_sample_rate(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                    1, sample_rate=44100))
            self.assertEqual(track.sample_rate(), 44100)
            track = audiotools.open(temp.name)
            self.assertEqual(track.sample_rate(), 44100)
        finally:
            temp.close()

    @FORMAT_LOSSY
    def test_pcm(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        temp2 = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.mkdtemp()
        try:
            for compression in (None,) + self.audio_class.COMPRESSION_MODES:
                #test silence
                reader = BLANK_PCM_Reader(5)
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)
                counter = FrameCounter(2, 16, 44100)
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   counter.update)
                self.assertEqual(int(counter), 5,
                                 "mismatch encoding %s at quality %s" % \
                                     (self.audio_class.NAME,
                                      compression))

                #test random noise
                reader = RANDOM_PCM_Reader(5)
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)
                counter = FrameCounter(2, 16, 44100)
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   counter.update)
                self.assertEqual(int(counter), 5,
                                 "mismatch encoding %s at quality %s" % \
                                     (self.audio_class.NAME,
                                      compression))

                #test randomly-sized chunks of silence
                reader = Variable_Reader(BLANK_PCM_Reader(5))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)

                counter = FrameCounter(2, 16, 44100)
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   counter.update)
                self.assertEqual(int(counter), 5,
                                 "mismatch encoding %s at quality %s" % \
                                     (self.audio_class.NAME,
                                      compression))

                #test randomly-sized chunks of random noise
                reader = Variable_Reader(RANDOM_PCM_Reader(5))
                if (compression is None):
                    track = self.audio_class.from_pcm(temp.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp.name, reader,
                                                      compression)

                counter = FrameCounter(2, 16, 44100)
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   counter.update)
                self.assertEqual(int(counter), 5,
                                 "mismatch encoding %s at quality %s" % \
                                     (self.audio_class.NAME,
                                      compression))

                #test PCMReaders that trigger a DecodingError
                self.assertRaises(ValueError,
                                  ERROR_PCM_Reader(ValueError("error"),
                                                   failure_chance=1.0).read,
                                  1)
                self.assertRaises(IOError,
                                  ERROR_PCM_Reader(IOError("error"),
                                                   failure_chance=1.0).read,
                                  1)
                self.assertRaises(audiotools.EncodingError,
                                  self.audio_class.from_pcm,
                                  os.path.join(temp_dir,
                                               "invalid" + self.suffix),
                                  ERROR_PCM_Reader(IOError("I/O Error")))

                self.assertEqual(os.path.isfile(
                        os.path.join(temp_dir,
                                     "invalid" + self.suffix)),
                                 False)

                self.assertRaises(audiotools.EncodingError,
                                  self.audio_class.from_pcm,
                                  os.path.join(temp_dir,
                                               "invalid" + self.suffix),
                                  ERROR_PCM_Reader(IOError("I/O Error")))

                self.assertEqual(os.path.isfile(
                        os.path.join(temp_dir,
                                     "invalid" + self.suffix)),
                                 False)

                #test unwritable output file
                self.assertRaises(audiotools.EncodingError,
                                  self.audio_class.from_pcm,
                                  "/dev/null/foo.%s" % (self.suffix),
                                  BLANK_PCM_Reader(1))

                #test without suffix
                reader = BLANK_PCM_Reader(5)
                if (compression is None):
                    track = self.audio_class.from_pcm(temp2.name, reader)
                else:
                    track = self.audio_class.from_pcm(temp2.name, reader,
                                                      compression)

                counter = FrameCounter(2, 16, 44100)
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   counter.update)
                self.assertEqual(int(counter), 5,
                                 "mismatch encoding %s at quality %s" % \
                                     (self.audio_class.NAME,
                                      compression))
        finally:
            temp.close()
            temp2.close()
            for f in os.listdir(temp_dir):
                os.unlink(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    # @FORMAT_LOSSY
    @LIB_CUSTOM
    def test_convert(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        self.assert_(False)

class AACFileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.AACAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AAC
    def test_length(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for seconds in [1, 2, 3, 4, 5, 10, 20, 60, 120]:
                track = self.audio_class.from_pcm(temp.name,
                                                  BLANK_PCM_Reader(seconds))
                self.assertEqual(int(round(track.seconds_length())), seconds)
        finally:
            temp.close()


class AiffFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.AiffAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AIFF
    def test_channel_mask(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        #AIFF's support channels are a little odd

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for mask in [["front_center"],
                         ["front_left",
                          "front_right"],
                         ["front_left",
                          "front_right",
                          "front_center"],
                         ["front_left",
                          "front_right",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "back_center",
                          "side_left",
                          "side_right"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f,True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
        finally:
            temp.close()

class ALACFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.ALACAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_ALAC
    def test_bits_per_sample(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for bps in (16, 24):
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, bits_per_sample=bps))
                self.assertEqual(track.bits_per_sample(), bps)
                track2 = audiotools.open(temp.name)
                self.assertEqual(track2.bits_per_sample(), bps)
        finally:
            temp.close()

    @FORMAT_ALAC
    def test_channel_mask(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for mask in [["front_center"],
                         ["front_left",
                          "front_right"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f,True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)

            for mask in [["front_left",
                          "front_right",
                          "front_center"],
                         ["front_left",
                          "front_right",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "low_frequency",
                          "back_left",
                          "back_right"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f,True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
        finally:
            temp.close()

    @FORMAT_ALAC
    def test_verify(self):
        alac_data = open("alac-allframes.m4a", "rb").read()

        #test truncating the mdat atom triggers IOError
        temp = tempfile.NamedTemporaryFile(suffix='.m4a')
        try:
            for i in xrange(0x16CD, len(alac_data)):
                temp.seek(0, 0)
                temp.write(alac_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                decoder = audiotools.open(temp.name).to_pcm()
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError,
                                  audiotools.transfer_framelist_data,
                                  decoder, lambda x: x)

                decoder = audiotools.open(temp.name).to_pcm()
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError, run_analysis, decoder)
                self.assertRaises(audiotools.InvalidFile,
                                  audiotools.open(temp.name).verify)
        finally:
            temp.close()

        #test a truncated file's convert() method raises EncodingError
        temp = tempfile.NamedTemporaryFile(suffix=".m4a")
        try:
            temp.write(open("alac-allframes.m4a", "rb").read()[0:-10])
            temp.flush()
            flac = audiotools.open(temp.name)
            if (os.path.isfile("dummy.wav")):
                os.unlink("dummy.wav")
            self.assertEqual(os.path.isfile("dummy.wav"), False)
            self.assertRaises(audiotools.EncodingError,
                              flac.convert,
                              "dummy.wav",
                              audiotools.WaveAudio)
            self.assertEqual(os.path.isfile("dummy.wav"), False)
        finally:
            temp.close()

class AUFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.AuAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AU
    def test_channel_mask(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for mask in [["front_center"],
                         ["front_left",
                          "front_right"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f,True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)

            for mask in [["front_left",
                          "front_right",
                          "front_center"],
                         ["front_left",
                          "front_right",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "back_left",
                          "back_right"],
                         ["front_left",
                          "front_right",
                          "front_center",
                          "low_frequency",
                          "back_left",
                          "back_right"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f,True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
        finally:
            temp.close()


class FlacFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_FLAC
    def test_metadata2(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(1))

            #check that a non-cover image with a description round-trips
            m = audiotools.MetaData()
            m.add_image(audiotools.Image.new(
                    TEST_COVER1, u'Unicode \u3057\u3066\u307f\u308b', 1))
            track.set_metadata(m)

            new_track = audiotools.open(track.filename)
            m2 = new_track.get_metadata()

            self.assertEqual(m.images()[0], m2.images()[0])

            orig_md5 = md5()
            pcm = track.to_pcm()
            audiotools.transfer_framelist_data(pcm, orig_md5.update)
            pcm.close()

            #add an image too large to fit into a FLAC metadata chunk
            metadata = track.get_metadata()
            metadata.add_image(
                audiotools.Image.new(HUGE_BMP.decode('bz2'), u'', 0))

            track.set_metadata(metadata)

            #ensure that setting the metadata doesn't break the file
            new_md5 = md5()
            pcm = track.to_pcm()
            audiotools.transfer_framelist_data(pcm, new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #ensure that setting fresh oversized metadata
            #doesn't break the file
            metadata = audiotools.MetaData()
            metadata.add_image(
                audiotools.Image.new(HUGE_BMP.decode('bz2'), u'', 0))

            track.set_metadata(metadata)

            new_md5 = md5()
            pcm = track.to_pcm()
            audiotools.transfer_framelist_data(pcm, new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #add a COMMENT block too large to fit into a FLAC metadata chunk
            metadata = track.get_metadata()
            metadata.comment = "QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2').decode('ascii')

            track.set_metadata(metadata)

            #ensure that setting the metadata doesn't break the file
            new_md5 = md5()
            pcm = track.to_pcm()
            audiotools.transfer_framelist_data(pcm, new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #ensure that setting fresh oversized metadata
            #doesn't break the file
            metadata = audiotools.MetaData(
                comment="QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2').decode('ascii'))

            track.set_metadata(metadata)

            new_md5 = md5()
            pcm = track.to_pcm()
            audiotools.transfer_framelist_data(pcm, new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #ensure that vendor_string isn't modified by setting metadata
            metadata = track.get_metadata()
            proper_vendor_string = metadata.vorbis_comment.vendor_string
            metadata.vorbis_comment.vendor_string = u"Invalid String"
            track.set_metadata(metadata)
            self.assertEqual(track.get_metadata().vorbis_comment.vendor_string,
                             proper_vendor_string)

            #FIXME - ensure that channel mask isn't modified
            #by setting metadata
        finally:
            temp.close()

    @FORMAT_FLAC
    def test_verify(self):
        self.assertEqual(audiotools.open("flac-allframes.flac").__md5__,
                         'f53f86876dcd7783225c93ba8a938c7d'.decode('hex'))

        flac_data = open("flac-allframes.flac", "rb").read()

        self.assertEqual(audiotools.open("flac-allframes.flac").verify(),
                         True)

        #try changing the file underfoot
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            temp.write(flac_data)
            temp.flush()
            flac_file = audiotools.open(temp.name)
            self.assertEqual(flac_file.verify(), True)

            for i in xrange(0, len(flac_data)):
                f = open(temp.name, "wb")
                f.write(flac_data[0:i])
                f.close()
                self.assertRaises(audiotools.InvalidFile,
                                  flac_file.verify)

            for i in xrange(0x2A, len(flac_data)):
                for j in xrange(8):
                    new_data = list(flac_data)
                    new_data[i] = chr(ord(new_data[i]) ^ (1 << j))
                    f = open(temp.name, "wb")
                    f.write("".join(new_data))
                    f.close()
                    self.assertRaises(audiotools.InvalidFile,
                                      flac_file.verify)
        finally:
            temp.close()

        #check a FLAC file with a short header
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for i in xrange(0, 0x2A):
                temp.seek(0, 0)
                temp.write(flac_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                if (i < 8):
                    f = open(temp.name, 'rb')
                    self.assertEqual(audiotools.FlacAudio.is_type(f), False)
                    f.close()
                self.assertRaises(IOError,
                                  audiotools.decoders.FlacDecoder,
                                  temp.name, 1)
        finally:
            temp.close()

        #check a FLAC file that's been truncated
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for i in xrange(0x2A, len(flac_data)):
                temp.seek(0, 0)
                temp.write(flac_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                decoder = audiotools.open(temp.name).to_pcm()
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError,
                                  audiotools.transfer_framelist_data,
                                  decoder, lambda x: x)

                decoder = audiotools.open(temp.name).to_pcm()
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError, run_analysis, decoder)
                self.assertRaises(audiotools.InvalidFile,
                                  audiotools.open(temp.name).verify)
        finally:
            temp.close()

        #test a FLAC file with a single swapped bit
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for i in xrange(0x2A, len(flac_data)):
                for j in xrange(8):
                    bytes = map(ord, flac_data[:])
                    bytes[i] ^= (1 << j)
                    temp.seek(0, 0)
                    temp.write("".join(map(chr, bytes)))
                    temp.flush()
                    self.assertEqual(len(flac_data),
                                     os.path.getsize(temp.name))

                    decoders = audiotools.open(temp.name).to_pcm()
                    try:
                        self.assertRaises(ValueError,
                                          audiotools.transfer_framelist_data,
                                          decoders, lambda x: x)
                    except IOError:
                        #Randomly swapping bits may send the decoder
                        #off the end of the stream before triggering
                        #a CRC-16 error.
                        #We simply need to catch that case and continue on.
                        continue
        finally:
            temp.close()

        #test a FLAC file with an invalid STREAMINFO block
        mismatch_streaminfos = [
            Con.Container(minimum_blocksize=4096,
                          maximum_blocksize=4096,
                          minimum_framesize=12,
                          maximum_framesize=12,
                          samplerate=44101,
                          channels=0,
                          bits_per_sample=15,
                          total_samples=80,
                          md5=[245, 63, 134, 135, 109, 205, 119,
                               131, 34, 92, 147, 186, 138, 147,
                               140, 125]),
            Con.Container(minimum_blocksize=4096,
                          maximum_blocksize=4096,
                          minimum_framesize=12,
                          maximum_framesize=12,
                          samplerate=44100,
                          channels=1,
                          bits_per_sample=15,
                          total_samples=80,
                          md5=[245, 63, 134, 135, 109, 205, 119,
                               131, 34, 92, 147, 186, 138, 147,
                               140, 125]),
            Con.Container(minimum_blocksize=4096,
                          maximum_blocksize=4096,
                          minimum_framesize=12,
                          maximum_framesize=12,
                          samplerate=44100,
                          channels=0,
                          bits_per_sample=7,
                          total_samples=80,
                          md5=[245, 63, 134, 135, 109, 205, 119,
                               131, 34, 92, 147, 186, 138, 147,
                               140, 125]),
            Con.Container(minimum_blocksize=4096,
                          maximum_blocksize=1,
                          minimum_framesize=12,
                          maximum_framesize=12,
                          samplerate=44100,
                          channels=0,
                          bits_per_sample=15,
                          total_samples=80,
                          md5=[245, 63, 134, 135, 109, 205, 119,
                               131, 34, 92, 147, 186, 138, 147,
                               140, 125]),
            Con.Container(minimum_blocksize=4096,
                          maximum_blocksize=1,
                          minimum_framesize=12,
                          maximum_framesize=12,
                          samplerate=44100,
                          channels=0,
                          bits_per_sample=15,
                          total_samples=80,
                          md5=[246, 63, 134, 135, 109, 205, 119,
                               131, 34, 92, 147, 186, 138, 147,
                               140, 125])]

        header = flac_data[0:8]
        data = flac_data[0x2A:]

        for streaminfo in mismatch_streaminfos:
            temp = tempfile.NamedTemporaryFile(suffix=".flac")
            try:
                temp.seek(0, 0)
                temp.write(header)
                temp.write(audiotools.FlacAudio.STREAMINFO.build(streaminfo)),
                temp.write(data)
                temp.flush()
                decoders = audiotools.open(temp.name).to_pcm()
                self.assertRaises(ValueError,
                                  audiotools.transfer_framelist_data,
                                  decoders, lambda x: x)
            finally:
                temp.close()

        #test that convert() from an invalid file also raises an exception
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            temp.write(flac_data[0:-10])
            temp.flush()
            flac = audiotools.open(temp.name)
            if (os.path.isfile("dummy.wav")):
                os.unlink("dummy.wav")
            self.assertEqual(os.path.isfile("dummy.wav"), False)
            self.assertRaises(audiotools.EncodingError,
                              flac.convert,
                              "dummy.wav",
                              audiotools.WaveAudio)
            self.assertEqual(os.path.isfile("dummy.wav"), False)
        finally:
            temp.close()



class M4AFileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.M4AAudio
        self.suffix = "." + self.audio_class.SUFFIX


class MP2FileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_MP2
    def test_length(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for seconds in [1, 2, 3, 4, 5, 10, 20, 60, 120]:
                track = self.audio_class.from_pcm(temp.name,
                                                  BLANK_PCM_Reader(seconds))
                self.assertEqual(int(round(track.seconds_length())), seconds)
        finally:
            temp.close()


class MP3FileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.MP3Audio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_MP3
    def test_length(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for seconds in [1, 2, 3, 4, 5, 10, 20, 60, 120]:
                track = self.audio_class.from_pcm(temp.name,
                                                  BLANK_PCM_Reader(seconds))
                self.assertEqual(int(round(track.seconds_length())), seconds)
        finally:
            temp.close()


class OggVerify:
    @FORMAT_VORBIS
    @FORMAT_OGGFLAC
    def test_verify(self):
        good_file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        bad_file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            good_track = self.audio_class.from_pcm(
                good_file.name,
                BLANK_PCM_Reader(1))
            good_file.seek(0, 0)
            good_file_data = good_file.read()
            self.assertEqual(len(good_file_data),
                             os.path.getsize(good_file.name))
            bad_file.write(good_file_data)
            bad_file.flush()

            track = audiotools.open(bad_file.name)
            self.assertEqual(track.verify(), True)

            #first, try truncating the file
            for i in xrange(len(good_file_data)):
                f = open(bad_file.name, "wb")
                f.write(good_file_data[0:i])
                f.flush()
                self.assertEqual(os.path.getsize(bad_file.name), i)
                self.assertRaises(audiotools.InvalidFile,
                                  track.verify)

            #then, try flipping a bit
            for i in xrange(len(good_file_data)):
                for j in xrange(8):
                    bad_file_data = list(good_file_data)
                    bad_file_data[i] = chr(ord(bad_file_data[i]) ^ (1 << j))
                    f = open(bad_file.name, "wb")
                    f.write("".join(bad_file_data))
                    f.close()
                    self.assertEqual(os.path.getsize(bad_file.name),
                                     len(good_file_data))
                    self.assertRaises(audiotools.InvalidFile,
                                      track.verify)
        finally:
            good_file.close()
            bad_file.close()

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                BLANK_PCM_Reader(1))
            self.assertEqual(track.verify(), True)
            good_data = open(temp.name, 'rb').read()
            f = open(temp.name, 'wb')
            f.write(good_data[0:100])
            f.close()
            if (os.path.isfile("dummy.wav")):
                os.unlink("dummy.wav")
            self.assertEqual(os.path.isfile("dummy.wav"), False)
            self.assertRaises(audiotools.EncodingError,
                              track.convert,
                              "dummy.wav",
                              audiotools.WaveAudio)
            self.assertEqual(os.path.isfile("dummy.wav"), False)
        finally:
            temp.close()


class OggFlacFileTest(OggVerify, LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.OggFlacAudio
        self.suffix = "." + self.audio_class.SUFFIX


class ShortenFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.ShortenAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_SHORTEN
    def test_bits_per_sample(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for bps in (8, 16):
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, bits_per_sample=bps))
                self.assertEqual(track.bits_per_sample(), bps)
                track2 = audiotools.open(temp.name)
                self.assertEqual(track2.bits_per_sample(), bps)
        finally:
            temp.close()

    @FORMAT_SHORTEN
    def test_verify(self):
        def first_non_header(filename):
            d = audiotools.open(filename).to_pcm()
            return d.analyze_frame()['offset']

        def last_byte(filename):
            d = audiotools.open(filename).to_pcm()
            frame = d.analyze_frame()
            while (frame['command'] != 4):
                frame = d.analyze_frame()
            else:
                return frame['offset']

        def run_analysis(pcmreader):
            f = pcmreader.analyze_frame()
            while (f is not None):
                f = pcmreader.analyze_frame()

        #test changing the file underfoot
        temp = tempfile.NamedTemporaryFile(suffix=".shn")
        try:
            shn_data = open("shorten-frames.shn", "rb").read()
            temp.write(shn_data)
            temp.flush()
            shn_file = audiotools.open(temp.name)
            self.assertEqual(shn_file.verify(), True)


            for i in xrange(0, len(shn_data.rstrip(chr(0)))):
                f = open(temp.name, "wb")
                f.write(shn_data[0:i])
                f.close()
                self.assertRaises(audiotools.InvalidFile,
                                  shn_file.verify)

            #unfortunately, Shorten doesn't have any checksumming
            #or other ways to reliably detect swapped bits
        finally:
            temp.close()

        #testing truncating various Shorten files
        for filename in ["shorten-frames.shn", "shorten-lpc.shn"]:
            first = first_non_header(filename)
            last = last_byte(filename) + 1

            f = open(filename, "rb")
            shn_data = f.read()
            f.close()

            temp = tempfile.NamedTemporaryFile(suffix=".shn")
            try:
                for i in xrange(0, first):
                    temp.seek(0, 0)
                    temp.write(shn_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)
                    self.assertRaises(ValueError,
                                      audiotools.decoders.SHNDecoder,
                                      temp.name)

                for i in xrange(first, len(shn_data[0:last].rstrip(chr(0)))):
                    temp.seek(0, 0)
                    temp.write(shn_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)
                    decoder = audiotools.decoders.SHNDecoder(temp.name)
                    self.assertNotEqual(decoder, None)
                    self.assertRaises(IOError,
                                      decoder.metadata)

                    decoder = audiotools.decoders.SHNDecoder(temp.name)
                    self.assertNotEqual(decoder, None)
                    decoder.sample_rate = 44100
                    decoder.channel_mask = 1
                    self.assertRaises(IOError,
                                      audiotools.transfer_framelist_data,
                                      decoder, lambda x: x)

                    decoder = audiotools.decoders.SHNDecoder(temp.name)
                    decoder.sample_rate = 44100
                    decoder.channel_mask = 1
                    self.assertNotEqual(decoder, None)
                    self.assertRaises(IOError, run_analysis, decoder)
            finally:
                temp.close()

        #test running convert() on a truncated file
        #triggers EncodingError
        temp = tempfile.NamedTemporaryFile(suffix=".shn")
        try:
            temp.write(open("shorten-frames.shn", "rb").read()[0:-10])
            temp.flush()
            flac = audiotools.open(temp.name)
            if (os.path.isfile("dummy.wav")):
                os.unlink("dummy.wav")
            self.assertEqual(os.path.isfile("dummy.wav"), False)
            self.assertRaises(audiotools.EncodingError,
                              flac.convert,
                              "dummy.wav",
                              audiotools.WaveAudio)
            self.assertEqual(os.path.isfile("dummy.wav"), False)
        finally:
            temp.close()


class SpeexFileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.SpeexAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_SPEEX
    def test_verify(self):
        good_file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        bad_file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            good_track = self.audio_class.from_pcm(
                good_file.name,
                BLANK_PCM_Reader(1))
            good_file.seek(0, 0)
            good_file_data = good_file.read()
            self.assertEqual(len(good_file_data),
                             os.path.getsize(good_file.name))
            bad_file.write(good_file_data)
            bad_file.flush()

            track = audiotools.open(bad_file.name)
            self.assertEqual(track.verify(), True)

            #first, try truncating the file
            for i in xrange(len(good_file_data)):
                f = open(bad_file.name, "wb")
                f.write(good_file_data[0:i])
                f.flush()
                self.assertEqual(os.path.getsize(bad_file.name), i)
                self.assertRaises(audiotools.InvalidFile,
                                  track.verify)

            #then, try flipping a bit
            for i in xrange(len(good_file_data)):
                for j in xrange(8):
                    bad_file_data = list(good_file_data)
                    bad_file_data[i] = chr(ord(bad_file_data[i]) ^ (1 << j))
                    f = open(bad_file.name, "wb")
                    f.write("".join(bad_file_data))
                    f.close()
                    self.assertEqual(os.path.getsize(bad_file.name),
                                     len(good_file_data))
                    self.assertRaises(audiotools.InvalidFile,
                                      track.verify)

            #convert() doesn't seem to error out properly
        finally:
            good_file.close()
            bad_file.close()


class VorbisFileTest(OggVerify, LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.VorbisAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_VORBIS
    def test_channels(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for channels in [1, 2, 3, 4, 5, 6]:
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=channels, channel_mask=0))
            self.assertEqual(track.channels(), channels)
            track = audiotools.open(temp.name)
            self.assertEqual(track.channels(), channels)
        finally:
            temp.close()


class WaveFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.WaveAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_WAVE
    def test_verify(self):
        #test various truncated files with verify()
        for wav_file in ["wav-8bit.wav",
                         "wav-1ch.wav",
                         "wav-2ch.wav",
                         "wav-6ch.wav"]:
            temp = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                wav_data = open(wav_file, 'rb').read()
                temp.write(wav_data)
                temp.flush()
                wave = audiotools.open(temp.name)

                #try changing the file out from under it
                for i in xrange(0, len(wav_data)):
                    f = open(temp.name, 'wb')
                    f.write(wav_data[0:i])
                    f.close()
                    self.assertEqual(os.path.getsize(temp.name), i)
                    self.assertRaises(audiotools.InvalidFile,
                                      wave.verify)
            finally:
                temp.close()

        #test running convert() on a truncated file
        #triggers EncodingError
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            temp.write(open("wav-2ch.wav", "rb").read()[0:-10])
            temp.flush()
            flac = audiotools.open(temp.name)
            if (os.path.isfile("dummy.wav")):
                os.unlink("dummy.wav")
            self.assertEqual(os.path.isfile("dummy.wav"), False)
            self.assertRaises(audiotools.EncodingError,
                              flac.convert,
                              "dummy.wav",
                              audiotools.WaveAudio)
            self.assertEqual(os.path.isfile("dummy.wav"), False)
        finally:
            temp.close()

        #test other truncated file combinations
        for (fmt_size, wav_file) in [(0x24, "wav-8bit.wav"),
                                     (0x24, "wav-1ch.wav"),
                                     (0x24, "wav-2ch.wav"),
                                     (0x3C, "wav-6ch.wav")]:
            f = open(wav_file, 'rb')
            wav_data = f.read()
            f.close()

            temp = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                #first, check that a truncated fmt chunk raises an exception
                #at init-time
                for i in xrange(0, fmt_size + 8):
                    temp.seek(0, 0)
                    temp.write(wav_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)

                    self.assertRaises(audiotools.InvalidFile,
                                      audiotools.WaveAudio,
                                      temp.name)

                #then, check that a truncated data chunk raises an exception
                #at read-time
                for i in xrange(fmt_size + 8, len(wav_data)):
                    temp.seek(0, 0)
                    temp.write(wav_data[0:i])
                    temp.flush()
                    wave = audiotools.WaveAudio(temp.name)
                    reader = wave.to_pcm()
                    self.assertNotEqual(reader, None)
                    self.assertRaises(IOError,
                                      audiotools.transfer_framelist_data,
                                      reader, lambda x: x)
                    self.assertRaises(audiotools.EncodingError,
                                      wave.to_wave,
                                      "dummy.wav")
                    self.assertRaises(audiotools.EncodingError,
                                      wave.from_wave,
                                      "dummy.wav",
                                      temp.name)
            finally:
                temp.close()

        #test for non-ASCII chunk IDs
        chunks = list(audiotools.open("wav-2ch.wav").chunks()) + \
            [("fooz", chr(0) * 10)]
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name,
                                                  iter(chunks))
            f = open(temp.name, 'rb')
            wav_data = list(f.read())
            f.close()
            wav_data[-15] = chr(0)
            temp.seek(0, 0)
            temp.write("".join(wav_data))
            temp.flush()
            self.assertRaises(audiotools.InvalidFile,
                              audiotools.open,
                              temp.name)
        finally:
            temp.close()


class WavPackFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_WAVPACK
    def test_verify(self):
        #test truncating a WavPack file causes verify()
        #to raise InvalidFile as necessary
        wavpackdata = open("wavpack-combo.wv", "rb").read()
        temp = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            self.assertEqual(audiotools.open("wavpack-combo.wv").verify(),
                             True)
            temp.write(wavpackdata)
            temp.flush()
            test_wavpack = audiotools.open(temp.name)
            for i in xrange(0, 0x20B):
                f = open(temp.name, "wb")
                f.write(wavpackdata[0:i])
                f.close()
                self.assertEqual(os.path.getsize(temp.name), i)
                self.assertRaises(audiotools.InvalidFile,
                                  test_wavpack.verify)

                #Swapping random bits doesn't affect WavPack's decoding
                #in many instances - which is surprising since I'd
                #expect its adaptive routines to be more susceptible
                #to values being out-of-whack during decorrelation.
                #This resilience may be related to its hybrid mode,
                #but it doesn't inspire confidence.

        finally:
            temp.close()

        #test truncating a WavPack file causes the WavPackDecoder
        #to raise IOError as necessary
        from audiotools.decoders import WavPackDecoder

        f = open("silence.wv")
        wavpack_data = f.read()
        f.close()

        temp = tempfile.NamedTemporaryFile(suffix=".wv")

        try:
            for i in xrange(0, len(wavpack_data)):
                temp.seek(0, 0)
                temp.write(wavpack_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                try:
                    decoder = WavPackDecoder(temp.name)
                except IOError:
                    #chopping off the first few bytes might trigger
                    #an IOError at init-time, which is ok
                    continue
                self.assertNotEqual(decoder, None)
                decoder = WavPackDecoder(temp.name)
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError,
                                  audiotools.transfer_framelist_data,
                                  decoder, lambda f: f)

                decoder = WavPackDecoder(temp.name)
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError, run_analysis, decoder)
        finally:
            temp.close()

        #test a truncated WavPack file's to_pcm() routine
        #generates DecodingErrors on close
        temp = tempfile.NamedTemporaryFile(
            suffix=".wv")
        try:
            temp.write(open("wavpack-combo.wv", "rb").read())
            temp.flush()
            wavpack = audiotools.open(temp.name)
            f = open(temp.name, "wb")
            f.write(open("wavpack-combo.wv", "rb").read()[0:-0x20B])
            f.close()
            reader = wavpack.to_pcm()
            audiotools.transfer_framelist_data(reader, lambda x: x)
            self.assertRaises(audiotools.DecodingError,
                              reader.close)
        finally:
            temp.close()

        #test a truncated WavPack file's convert() method
        #generates EncodingErrors
        temp = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            temp.write(open("wavpack-combo.wv", "rb").read())
            temp.flush()
            wavpack = audiotools.open(temp.name)
            f = open(temp.name, "wb")
            f.write(open("wavpack-combo.wv", "rb").read()[0:-0x20B])
            f.close()
            if (os.path.isfile("dummy.wav")):
                os.unlink("dummy.wav")
            self.assertEqual(os.path.isfile("dummy.wav"), False)
            self.assertRaises(audiotools.EncodingError,
                              wavpack.convert,
                              "dummy.wav",
                              audiotools.WaveAudio)
            self.assertEqual(os.path.isfile("dummy.wav"), False)
        finally:
            temp.close()


if (__name__ == '__main__'):
    unittest.main()
