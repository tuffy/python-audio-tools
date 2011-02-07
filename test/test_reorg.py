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

class AudioFileTest(unittest.TestCase):
    def setUp(self):
        self.audio_class = audiotools.AudioFile
        self.suffix = "." + self.audio_class.SUFFIX

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

            #FIXME - check images

            #FIXME - check merge

            #FIXME - check IOError on set_metadata()

            #FIXME - check IOError on get_metadata()

            #FIXME - check IOError on delete_metadata()

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

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_pcm(self):
        self.assert_(False)

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_convert(self):
        self.assert_(False)

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_track_number(self):
        self.assert_(False)

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_album_number(self):
        self.assert_(False)

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_track_name(self):
        self.assert_(False)

    #FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_replay_gain(self):
        self.assert_(False)

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


class OggFlacFileTest(LosslessFileTest):
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


class SpeexFileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.SpeexAudio
        self.suffix = "." + self.audio_class.SUFFIX


class VorbisFileTest(LossyFileTest):
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


class WavPackFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio
        self.suffix = "." + self.audio_class.SUFFIX


if (__name__ == '__main__'):
    unittest.main()
