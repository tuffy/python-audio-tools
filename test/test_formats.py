#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

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
import tempfile
import os
import os.path
from hashlib import md5
import random
import decimal
import test_streams
import cStringIO
import subprocess
import struct

from test import (parser,
                  BLANK_PCM_Reader, RANDOM_PCM_Reader,
                  EXACT_BLANK_PCM_Reader, EXACT_SILENCE_PCM_Reader,
                  Variable_Reader,
                  EXACT_RANDOM_PCM_Reader, MD5_Reader,
                  Join_Reader, FrameCounter,
                  Combinations,
                  TEST_COVER1, TEST_COVER2, TEST_COVER3,
                  HUGE_BMP)


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

    def read(self, pcm_frames):
        if (self.minimum_successes > 0):
            self.minimum_successes -= 1
            return audiotools.pcm.from_frames(
                [self.frame for i in xrange(pcm_frames)])
        else:
            if (random.random() <= self.failure_chance):
                raise self.error
            else:
                return audiotools.pcm.from_frames(
                    [self.frame for i in xrange(pcm_frames)])

    def close(self):
        pass


class Log:
    def __init__(self):
        self.results = []

    def update(self, *args):
        self.results.append(args)


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

        if (self.audio_class is audiotools.AudioFile):
            return

        dummy_metadata = audiotools.MetaData(**dict(
                [(field, char) for (field, char) in
                 zip(audiotools.MetaData.FIELDS,
                     string.ascii_letters)
                 if field not in audiotools.MetaData.INTEGER_FIELDS] +
                [(field, i + 1) for (i, field) in
                 enumerate(audiotools.MetaData.INTEGER_FIELDS)]))
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(1))
            track.set_metadata(dummy_metadata)
            track = audiotools.open(temp.name)
            metadata = track.get_metadata()
            if (metadata is None):
                return

            #check that delete_metadata works
            nonblank_metadata = audiotools.MetaData(
                track_name=u"Track Name",
                track_number=1,
                album_name=u"Album Name")
            track.set_metadata(nonblank_metadata)
            self.assertEqual(track.get_metadata(), nonblank_metadata)
            track.delete_metadata()
            metadata = track.get_metadata()
            if (metadata is not None):
                self.assertEqual(
                    metadata,
                    audiotools.MetaData(track_name=u"",
                                        track_number=0,
                                        album_name=u""))

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
    def test_convert_progress(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(10))
            for audio_class in audiotools.AVAILABLE_TYPES:
                outfile = tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)
                log = Log()
                try:
                    track2 = track.convert(outfile.name,
                                           audio_class,
                                           progress=log.update)
                    self.assert_(len(log.results) > 0,
                                 "no logging converting %s to %s" %
                                 (self.audio_class.NAME,
                                  audio_class.NAME))
                    self.assert_(len(set([r[1] for r in log.results])) == 1)
                    for x, y in zip(log.results[1:], log.results):
                        self.assert_((x[0] - y[0]) >= 0)

                    if (track.lossless() and track2.lossless()):
                        self.assert_(audiotools.pcm_frame_cmp(
                                track.to_pcm(), track2.to_pcm()) is None)
                finally:
                    outfile.close()
        finally:
            temp.close()

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
            if (track.get_metadata() is None):
                self.assertEqual(track.album_number(), 2)

            track = self.audio_class.from_pcm(
                os.path.join(temp_dir, "303 45 - abcde" + self.suffix),
                BLANK_PCM_Reader(1))
            if (track.get_metadata() is None):
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
        for field in audiotools.MetaData.FIELDS:
            if (field not in audiotools.MetaData.INTEGER_FIELDS):
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
                    (format_template % {u"field": u"foo"} % \
                         {u"foo": value}).encode(audiotools.FS_ENCODING))

        #then, check integer fields
        format_template = (u"Fo\u00f3 %(album_number)d " +
                           u"%(track_number)2.2d %(album_track_number)s")

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
                             (u"/f\u00f3o/bar/tr\u00e1ck").encode(
                    audiotools.FS_ENCODING)]:
                metadata = audiotools.MetaData(track_number=track_number,
                                               album_number=album_number)
                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template % {
                            u"album_number": album_number,
                            u"track_number": track_number,
                            u"album_track_number": album_track_number}
                                  ).encode('utf-8'))

        #then, check integers pulled from the track filename
        for metadata in [None, audiotools.MetaData()]:
            for basepath in ["track",
                             "/foo/bar/track",
                             (u"/f\u00f3o/bar/tr\u00e1ck").encode(
                    audiotools.FS_ENCODING)]:

                if (metadata is None):
                    album_number = 0
                    track_number = 1
                    album_track_number = u"01"
                else:
                    album_number = 0
                    track_number = 0
                    album_track_number = u"00"

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "01",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"album_number": album_number,
                                   u"track_number": track_number,
                                   u"album_track_number": album_track_number}
                                  ).encode('utf-8'))

                if (metadata is None):
                    album_number = 0
                    track_number = 23
                    album_track_number = u"23"
                else:
                    album_number = 0
                    track_number = 0
                    album_track_number = u"00"

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "track23",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"album_number": album_number,
                                   u"track_number": track_number,
                                   u"album_track_number": album_track_number}
                                  ).encode('utf-8'))

                if (metadata is None):
                    album_number = 1
                    track_number = 23
                    album_track_number = u"123"
                else:
                    album_number = 0
                    track_number = 0
                    album_track_number = u"00"

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "track123",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"album_number": album_number,
                                   u"track_number": track_number,
                                   u"album_track_number": album_track_number}
                                  ).encode('utf-8'))

                if (metadata is None):
                    album_number = 45
                    track_number = 67
                    album_track_number = u"4567"
                else:
                    album_number = 0
                    track_number = 0
                    album_track_number = u"00"

                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + "4567",
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"album_number": album_number,
                                   u"track_number": track_number,
                                   u"album_track_number": album_track_number}
                                  ).encode('utf-8'))

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
                             (u"/f\u00f3o/bar/tr\u00e1ck").encode(
                    audiotools.FS_ENCODING)]:
                metadata = audiotools.MetaData(track_number=track_number,
                                               album_number=album_number)
                self.assertEqual(self.audio_class.track_name(
                        file_path=basepath + incorrect,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"album_number": album_number,
                                   u"track_number": track_number,
                                   u"album_track_number": album_track_number}
                                  ).encode('utf-8'))

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
                                 (format_template %
                                  {u"track_total": track_total,
                                   u"album_total": album_total}
                                  ).encode('utf-8'))

        #ensure %(basename)s is set properly
        format_template = u"Fo\u00f3 %(basename)s"
        for (path, base) in [("track", "track"),
                            ("/foo/bar/track", "track"),
                            ((u"/f\u00f3o/bar/tr\u00e1ck").encode(
                    audiotools.FS_ENCODING), u"tr\u00e1ck")]:
            for metadata in [None, audiotools.MetaData()]:
                self.assertEqual(self.audio_class.track_name(
                        file_path=path,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"basename": base}).encode('utf-8'))

        #finally, ensure %(suffix)s is set properly
        format_template = u"Fo\u00f3 %(suffix)s"
        for path in ["track",
                     "/foo/bar/track",
                     (u"/f\u00f3o/bar/tr\u00e1ck").encode(
                audiotools.FS_ENCODING)]:
            for metadata in [None, audiotools.MetaData()]:
                self.assertEqual(self.audio_class.track_name(
                        file_path=path,
                        track_metadata=metadata,
                        format=format_template.encode('utf-8')),
                                 (format_template %
                                  {u"suffix":
                                       self.audio_class.SUFFIX.decode(
                                'ascii')}).encode('utf-8'))

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

            track_file1 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            track_file2 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            track_file3 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
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

                self.assert_(track1.replay_gain() is not None)
                self.assert_(track2.replay_gain() is not None)
                self.assert_(track3.replay_gain() is not None)

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

    @FORMAT_AUDIOFILE
    def test_invalid_from_pcm(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        #test our ERROR_PCM_Reader works
        self.assertRaises(ValueError,
                          ERROR_PCM_Reader(ValueError("error"),
                                           failure_chance=1.0).read,
                          1)
        self.assertRaises(IOError,
                          ERROR_PCM_Reader(IOError("error"),
                                           failure_chance=1.0).read,
                          1)

        #ensure that our dummy file doesn't exist
        dummy_filename = "invalid." + self.audio_class.SUFFIX
        self.assert_(not os.path.isfile(dummy_filename))

        #a decoder that raises IOError on to_pcm()
        #should trigger an EncodingError
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          dummy_filename,
                          ERROR_PCM_Reader(IOError("I/O Error")))

        #and ensure invalid files aren't left lying around
        self.assert_(not os.path.isfile(dummy_filename))

        #a decoder that raises ValueError on to_pcm()
        #should trigger an EncodingError
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          dummy_filename,
                          ERROR_PCM_Reader(ValueError("Value Error")))

        #and ensure invalid files aren't left lying around
        self.assert_(not os.path.isfile(dummy_filename))

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
                        [(f, True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                if (int(track.channel_mask()) != 0):
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

    @FORMAT_LOSSLESS
    def test_convert(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        #check various round-trip options
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                test_streams.Sine16_Stereo(441000, 44100,
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

                        pcm = track2.to_pcm()
                        counter = FrameCounter(pcm.channels,
                                               pcm.bits_per_sample,
                                               pcm.sample_rate)

                        audiotools.transfer_framelist_data(pcm,
                                                           counter.update)
                        self.assertEqual(
                            int(counter), 10,
                            "mismatch encoding %s (%s/%d != %s)" % \
                                (audio_class.NAME,
                                 counter,
                                 int(counter),
                                 10))

                    self.assertRaises(audiotools.EncodingError,
                                      track.convert,
                                      "/dev/null/foo.%s" % \
                                          (audio_class.SUFFIX),
                                      audio_class)

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
                            pcm = track2.to_pcm()
                            counter = FrameCounter(pcm.channels,
                                                   pcm.bits_per_sample,
                                                   pcm.sample_rate)
                            audiotools.transfer_framelist_data(track2.to_pcm(),
                                                               counter.update)
                            self.assertEqual(
                                int(counter), 10,
                                ("mismatch encoding %s " +
                                 "at quality %s (%s != %s)") % \
                                     (audio_class.NAME, compression,
                                      counter, 10))

                        #check some obvious failures
                        self.assertRaises(audiotools.EncodingError,
                                          track.convert,
                                          "/dev/null/foo.%s" % \
                                              (audio_class.SUFFIX),
                                          audio_class,
                                          compression)

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

    @FORMAT_LOSSY
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

                    counter = FrameCounter(2, 16, 44100)
                    audiotools.transfer_framelist_data(track2.to_pcm(),
                                                       counter.update)
                    self.assertEqual(
                        int(counter), 5,
                        "mismatch encoding %s" % \
                            (self.audio_class.NAME))

                    self.assertRaises(audiotools.EncodingError,
                                      track.convert,
                                      "/dev/null/foo.%s" % \
                                          (audio_class.SUFFIX),
                                      audio_class)

                    for compression in audio_class.COMPRESSION_MODES:
                        track2 = track.convert(temp2.name,
                                               audio_class,
                                               compression)

                        counter = FrameCounter(2, 16, 44100)
                        audiotools.transfer_framelist_data(track2.to_pcm(),
                                                           counter.update)
                        self.assertEqual(
                            int(counter), 5,
                            "mismatch encoding %s at quality %s" % \
                                (self.audio_class.NAME,
                                 compression))

                        #check some obvious failures
                        self.assertRaises(audiotools.EncodingError,
                                          track.convert,
                                          "/dev/null/foo.%s" % \
                                              (audio_class.SUFFIX),
                                          audio_class,
                                          compression)

                finally:
                    temp2.close()
        finally:
            temp.close()


class TestForeignWaveChunks:
    @FORMAT_LOSSLESS
    def test_roundtrip_wave_chunks(self):
        import filecmp

        self.assert_(issubclass(self.audio_class,
                                audiotools.WaveContainer))

        tempwav1 = tempfile.NamedTemporaryFile(suffix=".wav")
        tempwav2 = tempfile.NamedTemporaryFile(suffix=".wav")
        audio = tempfile.NamedTemporaryFile(
            suffix='.' + self.audio_class.SUFFIX)
        try:
            #build a WAVE with some oddball chunks
            audiotools.WaveAudio.wave_from_chunks(
                tempwav1.name,
                [audiotools.wav.RIFF_Chunk(
                        'fmt ',
                        16,
                        '\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00'),
                 audiotools.wav.RIFF_Chunk(
                        'fooz',
                        8,
                        'testtext'),
                 audiotools.wav.RIFF_Chunk(
                        'barz',
                        16,
                        'somemoretesttext'),
                 audiotools.wav.RIFF_Chunk(
                        'bazz',
                        1024,
                        chr(0) * 1024),
                 audiotools.wav.RIFF_Chunk(
                        'data',
                        882000,
                        'BZh91AY&SY\xdc\xd5\xc2\x8d\x06\xba\xa7\xc0\x00`\x00 \x000\x80MF\xa9$\x84\x9a\xa4\x92\x12qw$S\x85\t\r\xcd\\(\xd0'.decode('bz2')),
                 audiotools.wav.RIFF_Chunk(
                        'spam',
                        12,
                        'anotherchunk')])

            wave = audiotools.open(tempwav1.name)
            wave.verify()

            #convert it to our audio type using convert()
            #(this used to be a to_wave()/from_wave() test,
            # but I may deprecate that interface from direct use
            # in favor of the more flexible convert() method)
            track = wave.convert(audio.name, audiotools.WaveAudio)

            self.assertEqual(track.has_foreign_riff_chunks(), True)

            #convert it back to WAVE via convert()
            track.convert(tempwav2.name, audiotools.WaveAudio)

            #check that the to WAVEs are byte-for-byte identical
            self.assertEqual(filecmp.cmp(tempwav1.name,
                                         tempwav2.name,
                                         False), True)

            #finally, ensure that setting metadata doesn't erase the chunks
            track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
            track = audiotools.open(track.filename)
            self.assertEqual(track.has_foreign_riff_chunks(), True)
        finally:
            tempwav1.close()
            tempwav2.close()
            audio.close()

    @FORMAT_LOSSLESS
    def test_convert_wave_chunks(self):
        import filecmp

        #no "t" in this set
        #which prevents a random generator from creating
        #"fmt " or "data" chunk names
        chunk_name_chars = "abcdefghijklmnopqrsuvwxyz "

        input_wave = tempfile.NamedTemporaryFile(suffix=".wav")
        track1_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        output_wave = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            #build a WAVE with some random oddball chunks
            base_chunks = [
                audiotools.wav.RIFF_Chunk(
                    'fmt ',
                    16,
                    '\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00'),
                audiotools.wav.RIFF_Chunk(
                    'data',
                    882000,
                    'BZh91AY&SY\xdc\xd5\xc2\x8d\x06\xba\xa7\xc0\x00`\x00 \x000\x80MF\xa9$\x84\x9a\xa4\x92\x12qw$S\x85\t\r\xcd\\(\xd0'.decode('bz2'))]

            for i in xrange(random.choice(range(1, 10))):
                chunk_size = random.choice(range(1, 1024)) * 2
                base_chunks.insert(
                    random.choice(range(0, len(base_chunks) + 1)),
                    audiotools.wav.RIFF_Chunk(
                        "".join([random.choice(chunk_name_chars)
                                 for i in xrange(4)]),
                        chunk_size,
                        os.urandom(chunk_size)))

            audiotools.WaveAudio.wave_from_chunks(input_wave.name, base_chunks)
            wave = audiotools.open(input_wave.name)
            wave.verify()
            self.assert_(wave.has_foreign_riff_chunks())

            #convert it to our audio type using convert()
            track1 = wave.convert(track1_file.name, self.audio_class)
            self.assert_(track1.has_foreign_riff_chunks())

            #convert it to every other WAVE-containing format
            for new_class in [t for t in audiotools.AVAILABLE_TYPES
                              if issubclass(t, audiotools.WaveContainer)]:
                track2_file = tempfile.NamedTemporaryFile(
                    suffix="." + new_class.SUFFIX)
                try:
                    track2 = track1.convert(track2_file.name, new_class)
                    self.assert_(track2.has_foreign_riff_chunks(),
                                 "format %s lost RIFF chunks" % (new_class))

                    #then, convert it back to a WAVE
                    track2.convert(output_wave.name, audiotools.WaveAudio)

                    #and ensure the result is byte-for-byte identical
                    self.assertEqual(filecmp.cmp(input_wave.name,
                                                 output_wave.name,
                                                 False), True,
                                     "format %s lost RIFF chunks" % (new_class))
                finally:
                    track2_file.close()
        finally:
            input_wave.close()
            track1_file.close()
            output_wave.close()

    @FORMAT_LOSSLESS
    def test_convert_progress_wave_chunks(self):
        import filecmp

        #no "t" in this set
        #which prevents a random generator from creating
        #"fmt " or "data" chunk names
        chunk_name_chars = "abcdefghijklmnopqrsuvwxyz "

        input_wave = tempfile.NamedTemporaryFile(suffix=".wav")
        track1_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        output_wave = tempfile.NamedTemporaryFile(suffix=".wav")

        try:
            #build a WAVE with some random oddball chunks
            base_chunks = [
                audiotools.wav.RIFF_Chunk(
                    'fmt ',
                    16,
                    '\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00'),
                audiotools.wav.RIFF_Chunk(
                    'data',
                    882000,
                    'BZh91AY&SY\xdc\xd5\xc2\x8d\x06\xba\xa7\xc0\x00`\x00 \x000\x80MF\xa9$\x84\x9a\xa4\x92\x12qw$S\x85\t\r\xcd\\(\xd0'.decode('bz2'))]

            for i in xrange(random.choice(range(1, 10))):
                chunk_size = random.choice(range(1, 1024)) * 2
                base_chunks.insert(
                    random.choice(range(0, len(base_chunks) + 1)),
                    audiotools.wav.RIFF_Chunk(
                        "".join([random.choice(chunk_name_chars)
                                 for i in xrange(4)]),
                        chunk_size,
                        os.urandom(chunk_size)))

            audiotools.WaveAudio.wave_from_chunks(input_wave.name, base_chunks)
            wave = audiotools.open(input_wave.name)
            wave.verify()
            self.assert_(wave.has_foreign_riff_chunks())

            #convert it to our audio type using convert
            track1 = wave.convert(track1_file.name, self.audio_class)
            self.assert_(track1.has_foreign_riff_chunks())

            #convert our track to every other format
            for new_class in audiotools.AVAILABLE_TYPES:
                track2_file = tempfile.NamedTemporaryFile(
                    suffix="." + new_class.SUFFIX)
                log = Log()
                try:
                    track2 = track1.convert(track2_file.name,
                                            new_class,
                                            progress=log.update)

                    self.assert_(
                        len(log.results) > 0,
                        "no logging converting %s to %s with RIFF chunks" %
                        (self.audio_class.NAME,
                         new_class.NAME))
                    self.assert_(len(set([r[1] for r in log.results])) == 1)
                    for x, y in zip(log.results[1:], log.results):
                        self.assert_((x[0] - y[0]) >= 0)

                    #if the format is a WAVE container, convert it back
                    if (issubclass(new_class, audiotools.WaveContainer)):
                        track2.convert(output_wave.name, audiotools.WaveAudio)

                        #and ensure the result is byte-for-byte identical
                        self.assertEqual(filecmp.cmp(input_wave.name,
                                                     output_wave.name,
                                                     False), True)
                finally:
                    track2_file.close()
        finally:
            input_wave.close()
            track1_file.close()
            output_wave.close()


class TestForeignAiffChunks:
    @FORMAT_LOSSLESS
    def test_roundtrip_aiff_chunks(self):
        import filecmp

        tempaiff1 = tempfile.NamedTemporaryFile(suffix=".aiff")
        tempaiff2 = tempfile.NamedTemporaryFile(suffix=".aiff")
        audio = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            #build an AIFF with some oddball chunks
            audiotools.AiffAudio.aiff_from_chunks(
                tempaiff1.name,
                [audiotools.aiff.AIFF_Chunk(
                        'COMM',
                        18,
                        '\x00\x02\x00\x00\xacD\x00\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00'),
                 audiotools.aiff.AIFF_Chunk(
                        'fooz',
                        8,
                        'testtext'),
                 audiotools.aiff.AIFF_Chunk(
                        'barz',
                        16,
                        'somemoretesttext'),
                 audiotools.aiff.AIFF_Chunk(
                        'bazz',
                        1024,
                        chr(0) * 1024),
                 audiotools.aiff.AIFF_Chunk(
                        'SSND',
                        176408,
                        'BZh91AY&SY&2\xd0\xeb\x00\x01Y\xc0\x04\xc0\x00\x00\x80\x00\x08 \x000\xcc\x05)\xa6\xa2\x93`\x94\x9e.\xe4\x8ap\xa1 Le\xa1\xd6'.decode('bz2')),
                 audiotools.aiff.AIFF_Chunk(
                        'spam',
                        12,
                        'anotherchunk')])

            aiff = audiotools.open(tempaiff1.name)
            aiff.verify()

            #convert it to our audio type via convert()
            track = aiff.convert(audio.name, self.audio_class)
            if (hasattr(track, "has_foreign_aiff_chunks")):
                self.assert_(track.has_foreign_aiff_chunks())

            #convert it back to AIFF via convert()
            self.assert_(
                track.convert(tempaiff2.name,
                              audiotools.AiffAudio).has_foreign_aiff_chunks())

            #check that the two AIFFs are byte-for-byte identical
            self.assertEqual(filecmp.cmp(tempaiff1.name,
                                         tempaiff2.name,
                                         False), True)

            #however, unlike WAVE, AIFF does support metadata
            #so setting it will make the files no longer
            #byte-for-byte identical, but the chunks in the new file
            #should be a superset of the chunks in the old

            track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
            track = audiotools.open(track.filename)
            chunk_ids = set([chunk.id for chunk in
                             track.convert(tempaiff2.name,
                                           audiotools.AiffAudio).chunks()])
            self.assert_(chunk_ids.issuperset(set(['COMM',
                                                   'fooz',
                                                   'barz',
                                                   'bazz',
                                                   'SSND',
                                                   'spam'])))
        finally:
            tempaiff1.close()
            tempaiff2.close()
            audio.close()

    @FORMAT_LOSSLESS
    def test_convert_aiff_chunks(self):
        import filecmp

        #no "M" or "N" in this set
        #which prevents a random generator from creating
        #"COMM" or "SSND" chunk names
        chunk_name_chars = "ABCDEFGHIJKLOPQRSTUVWXYZ"

        input_aiff = tempfile.NamedTemporaryFile(suffix=".aiff")
        track1_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        output_aiff = tempfile.NamedTemporaryFile(suffix=".aiff")
        try:
            #build an AIFF with some random oddball chunks
            base_chunks = [
                audiotools.aiff.AIFF_Chunk(
                    'COMM',
                    18,
                    '\x00\x02\x00\x00\xacD\x00\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00'),
                audiotools.aiff.AIFF_Chunk(
                    'SSND',
                    176408,
                    'BZh91AY&SY&2\xd0\xeb\x00\x01Y\xc0\x04\xc0\x00\x00\x80\x00\x08 \x000\xcc\x05)\xa6\xa2\x93`\x94\x9e.\xe4\x8ap\xa1 Le\xa1\xd6'.decode('bz2'))]
            for i in xrange(random.choice(range(1, 10))):
                block_size = random.choice(range(1, 1024)) * 2
                base_chunks.insert(
                    random.choice(range(0, len(base_chunks) + 1)),
                    audiotools.aiff.AIFF_Chunk(
                        "".join([random.choice(chunk_name_chars)
                                 for i in xrange(4)]),
                        block_size,
                        os.urandom(block_size)))

            audiotools.AiffAudio.aiff_from_chunks(input_aiff.name, base_chunks)
            aiff = audiotools.open(input_aiff.name)
            aiff.verify()
            self.assert_(aiff.has_foreign_aiff_chunks())

            #convert it to our audio type using convert()
            track1 = aiff.convert(track1_file.name, self.audio_class)
            self.assert_(track1.has_foreign_aiff_chunks())

            #convert it to every other AIFF-containing format
            for new_class in [t for t in audiotools.AVAILABLE_TYPES
                              if issubclass(t, audiotools.AiffContainer)]:
                track2_file = tempfile.NamedTemporaryFile(
                    suffix="." + new_class.SUFFIX)
                try:
                    track2 = track1.convert(track2_file.name, new_class)
                    self.assert_(track2.has_foreign_aiff_chunks(),
                                 "format %s lost AIFF chunks" % (new_class))

                    #then, convert it back to an AIFF
                    track2.convert(output_aiff.name, audiotools.AiffAudio)

                    #and ensure the result is byte-for-byte identical
                    self.assertEqual(filecmp.cmp(input_aiff.name,
                                                 output_aiff.name,
                                                 False), True)
                finally:
                    track2_file.close()
        finally:
            input_aiff.close()
            track1_file.close()
            output_aiff.close()

    @FORMAT_LOSSLESS
    def test_convert_progress_aiff_chunks(self):
        import filecmp

        #no "M" or "N" in this set
        #which prevents a random generator from creating
        #"COMM" or "SSND" chunk names
        chunk_name_chars = "ABCDEFGHIJKLOPQRSTUVWXYZ"

        input_aiff = tempfile.NamedTemporaryFile(suffix=".aiff")
        track1_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        output_aiff = tempfile.NamedTemporaryFile(suffix=".aiff")
        try:
            #build an AIFF with some random oddball chunks
            base_chunks = [
                audiotools.aiff.AIFF_Chunk(
                    "COMM",
                    18,
                    '\x00\x02\x00\x00\xacD\x00\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00'),
                audiotools.aiff.AIFF_Chunk(
                    "SSND",
                    176408,
                    'BZh91AY&SY&2\xd0\xeb\x00\x01Y\xc0\x04\xc0\x00\x00\x80\x00\x08 \x000\xcc\x05)\xa6\xa2\x93`\x94\x9e.\xe4\x8ap\xa1 Le\xa1\xd6'.decode('bz2'))]
            for i in xrange(random.choice(range(1, 10))):
                chunk_size = random.choice(range(1, 1024)) * 2
                base_chunks.insert(
                    random.choice(range(0, len(base_chunks) + 1)),
                    audiotools.aiff.AIFF_Chunk(
                        "".join([random.choice(chunk_name_chars)
                                 for i in xrange(4)]),
                        chunk_size,
                        os.urandom(chunk_size)))

            audiotools.AiffAudio.aiff_from_chunks(input_aiff.name, base_chunks)
            aiff = audiotools.open(input_aiff.name)
            aiff.verify()
            self.assert_(aiff.has_foreign_aiff_chunks())

            #convert it to our audio type using convert()
            track1 = aiff.convert(track1_file.name, self.audio_class)
            self.assert_(track1.has_foreign_aiff_chunks())

            #convert it to every other format
            for new_class in audiotools.AVAILABLE_TYPES:
                track2_file = tempfile.NamedTemporaryFile(
                    suffix="." + new_class.SUFFIX)
                log = Log()
                try:
                    track2 = track1.convert(track2_file.name,
                                            new_class,
                                            progress=log.update)

                    self.assert_(
                        len(log.results) > 0,
                        "no logging converting %s to %s with AIFF chunks" %
                        (self.audio_class.NAME,
                         new_class.NAME))
                    self.assert_(len(set([r[1] for r in log.results])) == 1)
                    for x, y in zip(log.results[1:], log.results):
                        self.assert_((x[0] - y[0]) >= 0)

                    #if the format is an AIFF container, convert it back
                    if (issubclass(new_class, audiotools.AiffContainer)):
                        track2.convert(output_aiff.name, audiotools.AiffAudio)

                        #and ensure the result is byte-for-byte identical
                        self.assertEqual(filecmp.cmp(input_aiff.name,
                                                     output_aiff.name,
                                                     False), True)
                finally:
                    track2_file.close()
        finally:
            input_aiff.close()
            track1_file.close()
            output_aiff.close()


class AiffFileTest(TestForeignAiffChunks, LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.AiffAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AIFF
    def test_ieee_extended(self):
        from audiotools.bitstream import BitstreamReader, BitstreamRecorder
        import audiotools.aiff

        for i in xrange(0, 192000 + 1):
            w = BitstreamRecorder(0)
            audiotools.aiff.build_ieee_extended(w, float(i))
            s = cStringIO.StringIO(w.data())
            self.assertEqual(w.data(), s.getvalue())
            self.assertEqual(i, audiotools.aiff.parse_ieee_extended(
                    BitstreamReader(s, 0)))

    @FORMAT_AIFF
    def test_verify(self):
        import audiotools.aiff

        #test truncated file
        for aiff_file in ["aiff-8bit.aiff",
                          "aiff-1ch.aiff",
                          "aiff-2ch.aiff",
                          "aiff-6ch.aiff"]:
            f = open(aiff_file, 'rb')
            aiff_data = f.read()
            f.close()

            temp = tempfile.NamedTemporaryFile(suffix=".aiff")

            try:
                #first, check that a truncated comm chunk raises an exception
                #at init-time
                for i in xrange(0, 0x25):
                    temp.seek(0, 0)
                    temp.write(aiff_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)

                    self.assertRaises(audiotools.InvalidFile,
                                      audiotools.AiffAudio,
                                      temp.name)

                #then, check that a truncated ssnd chunk raises an exception
                #at read-time
                for i in xrange(0x2F, len(aiff_data)):
                    temp.seek(0, 0)
                    temp.write(aiff_data[0:i])
                    temp.flush()
                    reader = audiotools.AiffAudio(temp.name).to_pcm()
                    self.assertNotEqual(reader, None)
                    self.assertRaises(IOError,
                                      audiotools.transfer_framelist_data,
                                      reader, lambda x: x)
            finally:
                temp.close()

        #test non-ASCII chunk ID
        temp = tempfile.NamedTemporaryFile(suffix=".aiff")
        try:
            f = open("aiff-metadata.aiff")
            aiff_data = list(f.read())
            f.close()
            aiff_data[0x89] = chr(0)
            temp.seek(0, 0)
            temp.write("".join(aiff_data))
            temp.flush()
            aiff = audiotools.open(temp.name)
            self.assertRaises(audiotools.InvalidFile,
                              aiff.verify)
        finally:
            temp.close()

        #test no SSND chunk
        aiff = audiotools.open("aiff-nossnd.aiff")
        self.assertRaises(audiotools.InvalidFile, aiff.verify)

        #test convert errors
        temp = tempfile.NamedTemporaryFile(suffix=".aiff")
        try:
            temp.write(open("aiff-2ch.aiff", "rb").read()[0:-10])
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

        COMM = audiotools.aiff.AIFF_Chunk(
            "COMM",
            18,
            '\x00\x01\x00\x00\x00\r\x00\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00')
        SSND = audiotools.aiff.AIFF_Chunk(
            "SSND",
            34,
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x02\x00\x03\x00\x02\x00\x01\x00\x00\xff\xff\xff\xfe\xff\xfd\xff\xfe\xff\xff\x00\x00')

        #test multiple COMM chunks found
        #test multiple SSND chunks found
        #test SSND chunk before COMM chunk
        #test no SSND chunk
        #test no COMM chunk
        for chunks in [[COMM, COMM, SSND],
                       [COMM, SSND, SSND],
                       [SSND, COMM],
                       [SSND],
                       [COMM]]:
            temp = tempfile.NamedTemporaryFile(suffix=".aiff")
            try:
                audiotools.AiffAudio.aiff_from_chunks(temp.name, chunks)
                self.assertRaises(
                    audiotools.InvalidFile,
                    audiotools.open(temp.name).verify)
            finally:
                temp.close()

    @FORMAT_AIFF
    def test_clean(self):
        import audiotools.aiff

        COMM = audiotools.aiff.AIFF_Chunk(
            "COMM",
            18,
            '\x00\x01\x00\x00\x00\r\x00\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00')
        SSND = audiotools.aiff.AIFF_Chunk(
            "SSND",
            34,
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x02\x00\x03\x00\x02\x00\x01\x00\x00\xff\xff\xff\xfe\xff\xfd\xff\xfe\xff\xff\x00\x00')

        #test multiple COMM chunks
        #test multiple SSND chunks
        #test data chunk before fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".aiff")
        fixed = tempfile.NamedTemporaryFile(suffix=".aiff")
        try:
            for chunks in [[COMM, COMM, SSND],
                           [COMM, SSND, COMM],
                           [COMM, SSND, SSND],
                           [SSND, COMM],
                           [SSND, COMM, COMM]]:
                audiotools.AiffAudio.aiff_from_chunks(temp.name, chunks)
                fixes = []
                aiff = audiotools.open(temp.name).clean(fixes, fixed.name)
                chunks = list(aiff.chunks())
                self.assertEquals([c.id for c in chunks],
                                  [c.id for c in [COMM, SSND]])
                self.assertEquals([c.__size__ for c in chunks],
                                  [c.__size__ for c in [COMM, SSND]])
                self.assertEquals([c.__data__ for c in chunks],
                                  [c.__data__ for c in [COMM, SSND]])
        finally:
            temp.close()
            fixed.close()


class ALACFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.ALACAudio
        self.suffix = "." + self.audio_class.SUFFIX

        from audiotools.decoders import ALACDecoder
        from audiotools.encoders import encode_alac
        self.decoder = ALACDecoder
        self.encode = encode_alac

    @FORMAT_ALAC
    def test_init(self):
        #check missing file
        self.assertRaises(audiotools.m4a.InvalidALAC,
                          audiotools.ALACAudio,
                          "/dev/null/foo")

        #check invalid file
        invalid_file = tempfile.NamedTemporaryFile(suffix=".m4a")
        try:
            for c in "invalidstringxxx":
                invalid_file.write(c)
                invalid_file.flush()
                self.assertRaises(audiotools.m4a.InvalidALAC,
                                  audiotools.ALACAudio,
                                  invalid_file.name)
        finally:
            invalid_file.close()

        #check some decoder errors,
        #mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(TypeError, self.decoder, None)

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
                        [(f, True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)

            for mask in [["front_center",
                          "front_left",
                          "front_right"],
                         ["front_center",
                          "front_left",
                          "front_right",
                          "back_center"],
                         ["front_center",
                          "front_left",
                          "front_right",
                          "back_left",
                          "back_right"],
                         ["front_center",
                          "front_left",
                          "front_right",
                          "back_left",
                          "back_right",
                          "low_frequency"],
                         ["front_center",
                          "front_left",
                          "front_right",
                          "back_left",
                          "back_right",
                          "back_center",
                          "low_frequency"],
                         ["front_center",
                          "front_left_of_center",
                          "front_right_of_center",
                          "front_left",
                          "front_right",
                          "back_left",
                          "back_right",
                          "low_frequency"]]:
                cm = audiotools.ChannelMask.from_fields(**dict(
                        [(f, True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)

            #ensure valid channel counts with invalid channel masks
            #raise an exception
            self.assertRaises(audiotools.UnsupportedChannelMask,
                              self.audio_class.from_pcm,
                              temp.name,
                              BLANK_PCM_Reader(1, channels=4,
                                               channel_mask=0x0033))

            self.assertRaises(audiotools.UnsupportedChannelMask,
                              self.audio_class.from_pcm,
                              temp.name,
                              BLANK_PCM_Reader(1, channels=5,
                                               channel_mask=0x003B))
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

    @FORMAT_ALAC
    def test_too(self):
        #ensure that the 'too' meta atom isn't modified by setting metadata
        temp = tempfile.NamedTemporaryFile(
            suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                BLANK_PCM_Reader(1))
            metadata = track.get_metadata()
            encoder = unicode(metadata['ilst']['\xa9too'])
            track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
            metadata = track.get_metadata()
            self.assertEqual(metadata.track_name, u"Foo")
            self.assertEqual(unicode(metadata['ilst']['\xa9too']), encoder)
        finally:
            temp.close()

    def __test_reader__(self, pcmreader, block_size=4096):
        if (not audiotools.BIN.can_execute(audiotools.BIN["alac"])):
            self.assert_(False,
                         "reference ALAC binary alac(1) required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".alac")
        self.audio_class.from_pcm(temp_file.name,
                                  pcmreader,
                                  block_size=block_size)

        alac = audiotools.open(temp_file.name)
        self.assert_(alac.total_frames() > 0)

        #first, ensure the ALAC-encoded file
        #has the same MD5 signature as pcmreader once decoded
        md5sum_decoder = md5()
        d = alac.to_pcm()
        f = d.read(audiotools.FRAMELIST_SIZE)
        while (len(f) > 0):
            md5sum_decoder.update(f.to_bytes(False, True))
            f = d.read(audiotools.FRAMELIST_SIZE)
        d.close()
        self.assertEqual(md5sum_decoder.digest(), pcmreader.digest())

        #then compare our .to_pcm() output
        #with that of the ALAC reference decoder
        reference = subprocess.Popen([audiotools.BIN["alac"],
                                      "-r", temp_file.name],
                                     stdout=subprocess.PIPE)
        md5sum_reference = md5()
        audiotools.transfer_data(reference.stdout.read, md5sum_reference.update)
        self.assertEqual(reference.wait(), 0)
        self.assertEqual(md5sum_reference.digest(), pcmreader.digest(),
                         "mismatch decoding %s from reference (%s != %s)" %
                         (repr(pcmreader),
                          md5sum_reference.hexdigest(),
                          pcmreader.hexdigest()))

    def __test_reader_nonalac__(self, pcmreader, block_size=4096):
        #This is for multichannel testing
        #since alac(1) doesn't handle them yet.
        #Unfortunately, it relies only on our built-in decoder
        #to test correctness.

        temp_file = tempfile.NamedTemporaryFile(suffix=".alac")
        self.audio_class.from_pcm(temp_file.name,
                                  pcmreader,
                                  block_size=block_size)

        alac = audiotools.open(temp_file.name)
        self.assert_(alac.total_frames() > 0)

        #first, ensure the ALAC-encoded file
        #has the same MD5 signature as pcmreader once decoded
        md5sum_decoder = md5()
        d = alac.to_pcm()
        f = d.read(audiotools.FRAMELIST_SIZE)
        while (len(f) > 0):
            md5sum_decoder.update(f.to_bytes(False, True))
            f = d.read(audiotools.FRAMELIST_SIZE)
        d.close()
        self.assertEqual(md5sum_decoder.digest(), pcmreader.digest())

    def __stream_variations__(self):
        for stream in [
            test_streams.Sine16_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine16_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine16_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Sine24_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine24_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine24_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine24_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine24_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine24_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine24_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine24_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1)]:
            yield stream

    def __multichannel_stream_variations__(self):
        for stream in [
            test_streams.Simple_Sine(200000, 44100, 0x0007, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (30720, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x0107, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (19200, 30000),
                                     (16640, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x0037, 16,
                                     (6400, 10000),
                                     (8960, 15000),
                                     (11520, 20000),
                                     (12800, 25000),
                                     (14080, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x003F, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000)),
            test_streams.Simple_Sine(200000, 44100, 0x013F, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000),
                                     (29000, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x00FF, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000),
                                     (29000, 40000),
                                     (28000, 45000)),

            test_streams.Simple_Sine(200000, 44100, 0x0007, 24,
                                     (1638400, 10000),
                                     (3276800, 20000),
                                     (7864320, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x0107, 24,
                                     (1638400, 10000),
                                     (3276800, 20000),
                                     (4915200, 30000),
                                     (4259840, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x0037, 24,
                                     (1638400, 10000),
                                     (2293760, 15000),
                                     (2949120, 20000),
                                     (3276800, 25000),
                                     (3604480, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x003F, 24,
                                     (1638400, 10000),
                                     (2949120, 15000),
                                     (4259840, 20000),
                                     (5570560, 25000),
                                     (6881280, 30000),
                                     (7864320, 35000)),
            test_streams.Simple_Sine(200000, 44100, 0x013F, 24,
                                     (1638400, 10000),
                                     (2949120, 15000),
                                     (4259840, 20000),
                                     (5570560, 25000),
                                     (6881280, 30000),
                                     (7864320, 35000),
                                     (7000000, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x00FF, 24,
                                     (1638400, 10000),
                                     (2949120, 15000),
                                     (4259840, 20000),
                                     (5570560, 25000),
                                     (6881280, 30000),
                                     (7864320, 35000),
                                     (7000000, 40000),
                                     (6000000, 45000))]:
            yield stream

    @FORMAT_ALAC
    def test_streams(self):
        for g in self.__stream_variations__():
            md5sum = md5()
            f = g.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = g.read(audiotools.FRAMELIST_SIZE)
            self.assertEqual(md5sum.digest(), g.digest())
            g.close()

        for g in self.__multichannel_stream_variations__():
            md5sum = md5()
            f = g.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = g.read(audiotools.FRAMELIST_SIZE)
            self.assertEqual(md5sum.digest(), g.digest())
            g.close()

    @FORMAT_ALAC
    def test_small_files(self):
        for g in [test_streams.Generate01,
                  test_streams.Generate02,
                  test_streams.Generate03,
                  test_streams.Generate04]:
            self.__test_reader__(g(44100), block_size=1152)

    @FORMAT_ALAC
    def test_full_scale_deflection(self):
        for (bps, fsd) in [(16, test_streams.fsd16),
                           (24, test_streams.fsd24)]:
            for pattern in [test_streams.PATTERN01,
                            test_streams.PATTERN02,
                            test_streams.PATTERN03,
                            test_streams.PATTERN04,
                            test_streams.PATTERN05,
                            test_streams.PATTERN06,
                            test_streams.PATTERN07]:
                self.__test_reader__(
                    test_streams.MD5Reader(fsd(pattern, 100)),
                    block_size=1152)

    @FORMAT_ALAC
    def test_sines(self):
        for g in self.__stream_variations__():
            self.__test_reader__(g, block_size=1152)

        for g in self.__multichannel_stream_variations__():
            self.__test_reader_nonalac__(g, block_size=1152)

    @FORMAT_ALAC
    def test_wasted_bps(self):
        self.__test_reader__(test_streams.WastedBPS16(1000),
                             block_size=1152)

    @FORMAT_ALAC
    def test_blocksizes(self):
        noise = struct.unpack(">32h", os.urandom(64))

        for block_size in [16, 17, 18, 19, 20, 21, 22, 23, 24,
                           25, 26, 27, 28, 29, 30, 31, 32, 33]:
            self.__test_reader__(test_streams.MD5Reader(
                    test_streams.FrameListReader(noise,
                                                 44100, 1, 16)),
                                 block_size=block_size)

    @FORMAT_ALAC
    def test_noise(self):
        for (channels, mask) in [
            (1, audiotools.ChannelMask.from_channels(1)),
            (2, audiotools.ChannelMask.from_channels(2))]:
            for bps in [16, 24]:
                #the reference decoder can't handle very large block sizes
                for blocksize in [32, 4096, 8192]:
                    self.__test_reader__(
                        MD5_Reader(EXACT_RANDOM_PCM_Reader(
                                pcm_frames=65536,
                                sample_rate=44100,
                                channels=channels,
                                channel_mask=mask,
                                bits_per_sample=bps)),
                        block_size=blocksize)

    @FORMAT_ALAC
    def test_fractional(self):
        def __perform_test__(block_size, pcm_frames):
            self.__test_reader__(
                MD5_Reader(EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                block_size=block_size)

        for pcm_frames in [31, 32, 33, 34, 35, 2046, 2047, 2048, 2049, 2050]:
            __perform_test__(33, pcm_frames)

        for pcm_frames in [254, 255, 256, 257, 258, 510, 511, 512,
                           513, 514, 1022, 1023, 1024, 1025, 1026,
                           2046, 2047, 2048, 2049, 2050, 4094, 4095,
                           4096, 4097, 4098]:
            __perform_test__(256, pcm_frames)

        for pcm_frames in [1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097, 4098]:
            __perform_test__(2048, pcm_frames)

        for pcm_frames in [1022, 1023, 1024, 1025, 1026, 2046, 2047, 2048,
                           2049, 2050, 4094, 4095, 4096, 4097, 4098, 4606,
                           4607, 4608, 4609, 4610, 8190, 8191, 8192, 8193,
                           8194, 16382, 16383, 16384, 16385, 16386]:
            __perform_test__(4608, pcm_frames)

    @FORMAT_ALAC
    def test_frame_header_variations(self):
        self.__test_reader__(test_streams.Sine16_Mono(200000, 96000,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=16)

        #The alac(1) decoder I'm using as a reference can't handle
        #this block size, even though iTunes handles the resulting files
        #just fine.  Therefore, it's likely an alac bug beyond my
        #capability to fix.
        #I don't expect anyone will use anything other than the default
        #block size anyway.

        # self.__test_reader__(test_streams.Sine16_Mono(200000, 96000,
        #                                               441.0, 0.61, 661.5, 0.37),
        #                      block_size=65535)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 9,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=1152)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 90,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=1152)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 90000,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=1152)


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
                        [(f, True) for f in mask]))
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
                        [(f, True) for f in mask]))
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=len(cm), channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
        finally:
            temp.close()

    @FORMAT_AU
    def test_verify(self):
        #test truncated file
        temp = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                BLANK_PCM_Reader(1))
            good_data = open(temp.name, 'rb').read()
            f = open(temp.name, 'wb')
            f.write(good_data[0:-10])
            f.close()
            reader = track.to_pcm()
            self.assertNotEqual(reader, None)
            self.assertRaises(IOError,
                              audiotools.transfer_framelist_data,
                              reader, lambda x: x)
        finally:
            temp.close()

        #test convert() error
        temp = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                BLANK_PCM_Reader(1))
            good_data = open(temp.name, 'rb').read()
            f = open(temp.name, 'wb')
            f.write(good_data[0:-10])
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


class FlacFileTest(TestForeignAiffChunks,
                   TestForeignWaveChunks,
                   LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio
        self.suffix = "." + self.audio_class.SUFFIX

        from audiotools.decoders import FlacDecoder
        from audiotools.encoders import encode_flac

        self.decoder = FlacDecoder
        self.encode = encode_flac
        self.encode_opts = [{"block_size":1152,
                             "max_lpc_order":0,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":3},
                            {"block_size":1152,
                             "max_lpc_order":0,
                             "adaptive_mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":3},
                            {"block_size":1152,
                             "max_lpc_order":0,
                             "exhaustive_model_search":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":3},
                            {"block_size":4096,
                             "max_lpc_order":6,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":4},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "adaptive_mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":4},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":5},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":6},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "mid_side":True,
                             "exhaustive_model_search":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":6},
                            {"block_size":4096,
                             "max_lpc_order":12,
                             "mid_side":True,
                             "exhaustive_model_search":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":6}]

    @FORMAT_FLAC
    def test_init(self):
        #check missing file
        self.assertRaises(audiotools.flac.InvalidFLAC,
                          audiotools.FlacAudio,
                          "/dev/null/foo")

        #check invalid file
        invalid_file = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for c in "invalidstringxxx":
                invalid_file.write(c)
                invalid_file.flush()
                self.assertRaises(audiotools.flac.InvalidFLAC,
                                  audiotools.FlacAudio,
                                  invalid_file.name)
        finally:
            invalid_file.close()

        #check some decoder errors,
        #mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(TypeError, self.decoder, None)

        self.assertRaises(ValueError, self.decoder, "/dev/null", -1)

        self.assertRaises(ValueError, self.decoder, "/dev/null", 0x3, -1)

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

            track.update_metadata(metadata)

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

            track.update_metadata(metadata)

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

            track.set_metadata(audiotools.MetaData(track_name=u"Testing"))

            #ensure that vendor_string isn't modified by setting metadata
            metadata = track.get_metadata()
            self.assert_(metadata is not None)
            self.assertEqual(metadata.track_name, u"Testing")
            self.assert_(
                metadata.get_block(audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                is not None)
            vorbis_comment = metadata.get_blocks(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
            proper_vendor_string = vorbis_comment[0].vendor_string
            vorbis_comment[0].vendor_string = u"Different String"
            metadata.replace_blocks(audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID,
                                    vorbis_comment)
            track.set_metadata(metadata)
            vendor_string = track.get_metadata().get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID).vendor_string
            self.assertEqual(vendor_string, proper_vendor_string)

            #FIXME - ensure that channel mask isn't modified
            #by setting metadata
        finally:
            temp.close()

    @FORMAT_FLAC
    def test_update_metadata(self):
        #build a temporary file
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            temp.write(open("flac-allframes.flac", "rb").read())
            temp.flush()
            flac_file = audiotools.open(temp.name)

            #attempt to adjust its metadata with bogus side data fields
            metadata = flac_file.get_metadata()
            streaminfo = metadata.get_block(audiotools.flac.Flac_STREAMINFO.BLOCK_ID)

            minimum_block_size = streaminfo.minimum_block_size
            maximum_block_size = streaminfo.maximum_block_size
            minimum_frame_size = streaminfo.minimum_frame_size
            maximum_frame_size = streaminfo.maximum_frame_size
            sample_rate = streaminfo.sample_rate
            channels = streaminfo.channels
            bits_per_sample = streaminfo.bits_per_sample
            total_samples = streaminfo.total_samples
            md5sum = streaminfo.md5sum

            streaminfo.minimum_block_size = 1
            streaminfo.maximum_block_size = 10
            streaminfo.minimum_frame_size = 2
            streaminfo.maximum_frame_size = 11
            streaminfo.sample_rate = 96000
            streaminfo.channels = 4
            streaminfo.bits_per_sample = 24
            streaminfo.total_samples = 96000
            streaminfo.md5sum = chr(1) * 16

            metadata.replace_blocks(audiotools.flac.Flac_STREAMINFO.BLOCK_ID,
                                    [streaminfo])

            #ensure that set_metadata() restores fields to original values
            flac_file.set_metadata(metadata)
            metadata = flac_file.get_metadata()
            streaminfo = metadata.get_block(audiotools.flac.Flac_STREAMINFO.BLOCK_ID)

            self.assertEqual(minimum_block_size,
                             streaminfo.minimum_block_size)
            self.assertEqual(maximum_block_size,
                             streaminfo.maximum_block_size)
            self.assertEqual(minimum_frame_size,
                             streaminfo.minimum_frame_size)
            self.assertEqual(maximum_frame_size,
                             streaminfo.maximum_frame_size)
            self.assertEqual(sample_rate,
                             streaminfo.sample_rate)
            self.assertEqual(channels,
                             streaminfo.channels)
            self.assertEqual(bits_per_sample,
                             streaminfo.bits_per_sample)
            self.assertEqual(total_samples,
                             streaminfo.total_samples)
            self.assertEqual(md5sum,
                             streaminfo.md5sum)

            #adjust its metadata with new bogus side data files
            metadata = flac_file.get_metadata()
            streaminfo = metadata.get_block(audiotools.flac.Flac_STREAMINFO.BLOCK_ID)
            streaminfo.minimum_block_size = 1
            streaminfo.maximum_block_size = 10
            streaminfo.minimum_frame_size = 2
            streaminfo.maximum_frame_size = 11
            streaminfo.sample_rate = 96000
            streaminfo.channels = 4
            streaminfo.bits_per_sample = 24
            streaminfo.total_samples = 96000
            streaminfo.md5sum = chr(1) * 16

            metadata.replace_blocks(audiotools.flac.Flac_STREAMINFO.BLOCK_ID,
                                    [streaminfo])

            #ensure that update_metadata() uses the bogus side data
            flac_file.update_metadata(metadata)
            metadata = flac_file.get_metadata()
            streaminfo = metadata.get_block(audiotools.flac.Flac_STREAMINFO.BLOCK_ID)
            self.assertEqual(streaminfo.minimum_block_size, 1)
            self.assertEqual(streaminfo.maximum_block_size, 10)
            self.assertEqual(streaminfo.minimum_frame_size, 2)
            self.assertEqual(streaminfo.maximum_frame_size, 11)
            self.assertEqual(streaminfo.sample_rate, 96000)
            self.assertEqual(streaminfo.channels, 4)
            self.assertEqual(streaminfo.bits_per_sample, 24)
            self.assertEqual(streaminfo.total_samples, 96000)
            self.assertEqual(streaminfo.md5sum, chr(1) * 16)
        finally:
            temp.close()

    # @FORMAT_FLAC
    @LIB_CUSTOM
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
            (4096, 4096, 12, 12, 44101, 0, 15, 80,
             '\xf5?\x86\x87m\xcdw\x83"\\\x93\xba\x8a\x93\x8c}'),
            (4096, 4096, 12, 12, 44100, 1, 15, 80,
             '\xf5?\x86\x87m\xcdw\x83"\\\x93\xba\x8a\x93\x8c}'),
            (4096, 4096, 12, 12, 44100, 0, 7, 80,
             '\xf5?\x86\x87m\xcdw\x83"\\\x93\xba\x8a\x93\x8c}'),
            (4096, 1, 12, 12, 44100, 0, 15, 80,
             '\xf5?\x86\x87m\xcdw\x83"\\\x93\xba\x8a\x93\x8c}'),
            (4096, 4096, 12, 12, 44100, 0, 15, 80,
             '\xf5?\x86\x87m\xcdw\x83"\\\x93\xba\x8a\x93\x8d}')]

        header = flac_data[0:8]
        data = flac_data[0x2A:]

        from audiotools.bitstream import BitstreamWriter

        for streaminfo in mismatch_streaminfos:
            temp = tempfile.NamedTemporaryFile(suffix=".flac")
            try:
                temp.seek(0, 0)
                temp.write(header)
                BitstreamWriter(temp.file, 0).build(
                    "16u 16u 24u 24u 20u 3u 5u 36U 16b",
                    streaminfo)
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

    def __stream_variations__(self):
        for stream in [
            test_streams.Sine8_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine8_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine8_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine8_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine8_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine8_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine8_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine8_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Sine16_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine16_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine16_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Sine24_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine24_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine24_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine24_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine24_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine24_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine24_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine24_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Simple_Sine(200000, 44100, 0x7, 8,
                                     (25, 10000),
                                     (50, 20000),
                                     (120, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 8,
                                     (25, 10000),
                                     (50, 20000),
                                     (75, 30000),
                                     (65, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 8,
                                     (25, 10000),
                                     (35, 15000),
                                     (45, 20000),
                                     (50, 25000),
                                     (55, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 8,
                                     (25, 10000),
                                     (45, 15000),
                                     (65, 20000),
                                     (85, 25000),
                                     (105, 30000),
                                     (120, 35000)),

            test_streams.Simple_Sine(200000, 44100, 0x7, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (30720, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (19200, 30000),
                                     (16640, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 16,
                                     (6400, 10000),
                                     (8960, 15000),
                                     (11520, 20000),
                                     (12800, 25000),
                                     (14080, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000)),

            test_streams.Simple_Sine(200000, 44100, 0x7, 24,
                                     (1638400, 10000),
                                     (3276800, 20000),
                                     (7864320, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 24,
                                     (1638400, 10000),
                                     (3276800, 20000),
                                     (4915200, 30000),
                                     (4259840, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 24,
                                     (1638400, 10000),
                                     (2293760, 15000),
                                     (2949120, 20000),
                                     (3276800, 25000),
                                     (3604480, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 24,
                                     (1638400, 10000),
                                     (2949120, 15000),
                                     (4259840, 20000),
                                     (5570560, 25000),
                                     (6881280, 30000),
                                     (7864320, 35000))]:
            yield stream

    @FORMAT_FLAC
    def test_streams(self):
        for g in self.__stream_variations__():
            md5sum = md5()
            f = g.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = g.read(audiotools.FRAMELIST_SIZE)
            self.assertEqual(md5sum.digest(), g.digest())
            g.close()

    def __test_reader__(self, pcmreader, **encode_options):
        if (not audiotools.BIN.can_execute(audiotools.BIN["flac"])):
            self.assert_(False,
                         "reference FLAC binary flac(1) required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.encode(temp_file.name,
                    audiotools.BufferedPCMReader(pcmreader),
                    **encode_options)

        self.assertEqual(subprocess.call([audiotools.BIN["flac"], "-ts",
                                          temp_file.name]),
                         0,
                         "flac decode error on %s with options %s" % \
                             (repr(pcmreader),
                              repr(encode_options)))

        flac = audiotools.open(temp_file.name)
        self.assert_(flac.total_frames() > 0)
        if (hasattr(pcmreader, "digest")):
            self.assertEqual(flac.__md5__, pcmreader.digest())

        md5sum = md5()
        d = self.decoder(temp_file.name, pcmreader.channel_mask)
        f = d.read(audiotools.FRAMELIST_SIZE)
        while (len(f) > 0):
            md5sum.update(f.to_bytes(False, True))
            f = d.read(audiotools.FRAMELIST_SIZE)
        d.close()
        self.assertEqual(md5sum.digest(), pcmreader.digest())

        temp_file.close()

    @FORMAT_FLAC
    def test_small_files(self):
        for g in [test_streams.Generate01,
                  test_streams.Generate02,
                  test_streams.Generate03,
                  test_streams.Generate04]:
            self.__test_reader__(g(44100),
                                 block_size=1152,
                                 max_lpc_order=16,
                                 min_residual_partition_order=0,
                                 max_residual_partition_order=3,
                                 mid_side=True,
                                 adaptive_mid_side=True,
                                 exhaustive_model_search=True)

    @FORMAT_FLAC
    def test_full_scale_deflection(self):
        for (bps, fsd) in [(8, test_streams.fsd8),
                           (16, test_streams.fsd16),
                           (24, test_streams.fsd24)]:
            for pattern in [test_streams.PATTERN01,
                            test_streams.PATTERN02,
                            test_streams.PATTERN03,
                            test_streams.PATTERN04,
                            test_streams.PATTERN05,
                            test_streams.PATTERN06,
                            test_streams.PATTERN07]:
                self.__test_reader__(
                    test_streams.MD5Reader(fsd(pattern, 100)),
                    block_size=1152,
                    max_lpc_order=16,
                    min_residual_partition_order=0,
                    max_residual_partition_order=3,
                    mid_side=True,
                    adaptive_mid_side=True,
                    exhaustive_model_search=True)

    @FORMAT_FLAC
    def test_sines(self):
        import sys

        for g in self.__stream_variations__():
            self.__test_reader__(g,
                                 block_size=1152,
                                 max_lpc_order=16,
                                 min_residual_partition_order=0,
                                 max_residual_partition_order=3,
                                 mid_side=True,
                                 adaptive_mid_side=True,
                                 exhaustive_model_search=True)

    @FORMAT_FLAC
    def test_wasted_bps(self):
        self.__test_reader__(test_streams.WastedBPS16(1000),
                             block_size=1152,
                             max_lpc_order=16,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

    @FORMAT_FLAC
    def test_blocksizes(self):
        #FIXME - handle 8bps/24bps also
        noise = struct.unpack(">32h", os.urandom(64))

        encoding_args = {"min_residual_partition_order": 0,
                         "max_residual_partition_order": 6,
                         "mid_side": True,
                         "adaptive_mid_side": True,
                         "exhaustive_model_search": True}
        for to_disable in [[],
                           ["disable_verbatim_subframes",
                            "disable_constant_subframes"],
                           ["disable_verbatim_subframes",
                            "disable_constant_subframes",
                            "disable_fixed_subframes"]]:
            for block_size in [16, 17, 18, 19, 20, 21, 22, 23,
                               24, 25, 26, 27, 28, 29, 30, 31, 32, 33]:
                for lpc_order in [0, 1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17,
                                  31, 32]:
                    args = encoding_args.copy()
                    for disable in to_disable:
                        args[disable] = True
                    args["block_size"] = block_size
                    args["max_lpc_order"] = lpc_order
                    self.__test_reader__(test_streams.MD5Reader(
                            test_streams.FrameListReader(noise,
                                                         44100, 1, 16)),
                                         **args)

    @FORMAT_FLAC
    def test_frame_header_variations(self):
        max_lpc_order = 16

        self.__test_reader__(test_streams.Sine16_Mono(200000, 96000,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=max_lpc_order,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 96000,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=65535,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 9,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=1152,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 90,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=1152,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 90000,
                                                      441.0, 0.61, 661.5, 0.37),
                             block_size=1152,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        #the reference encoder's test_streams.sh unit test
        #re-does the 9Hz/90Hz/90000Hz tests for some reason
        #which I won't repeat here

    @FORMAT_FLAC
    def test_option_variations(self):
        #testing all the option variations
        #against all the stream variations
        #along with a few extra option variations
        #takes a *long* time - so don't panic

        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for disable in [[],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes"],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes",
                             "disable_fixed_subframes"]]:
                for extra in [[],
                              #FIXME - no analogue for -p option
                              ["exhaustive_model_search"]]:
                    for d in disable:
                        encode_opts[d] = True
                    for e in extra:
                        encode_opts[e] = True
                    for g in self.__stream_variations__():
                        self.__test_reader__(g, **encode_opts)

    @FORMAT_FLAC
    def test_noise_silence(self):
        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for disable in [[],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes"],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes",
                             "disable_fixed_subframes"]]:
                for (channels, mask) in [
                    (1, audiotools.ChannelMask.from_channels(1)),
                    (2, audiotools.ChannelMask.from_channels(2)),
                    (4, audiotools.ChannelMask.from_fields(
                            front_left=True,
                            front_right=True,
                            back_left=True,
                            back_right=True)),
                    (8, audiotools.ChannelMask(0))]:
                    for bps in [8, 16, 24]:
                        for extra in  [[],
                                       #FIXME - no analogue for -p option
                                       ["exhaustive_model_search"]]:
                            for blocksize in [None, 32, 32768, 65535]:
                                for d in disable:
                                    encode_opts[d] = True
                                for e in extra:
                                    encode_opts[e] = True
                                if (blocksize is not None):
                                    encode_opts["block_size"] = blocksize

                                self.__test_reader__(
                                    MD5_Reader(EXACT_RANDOM_PCM_Reader(
                                            pcm_frames=65536,
                                            sample_rate=44100,
                                            channels=channels,
                                            channel_mask=mask,
                                            bits_per_sample=bps)),
                                    **encode_opts)

                                self.__test_reader__(
                                    MD5_Reader(EXACT_SILENCE_PCM_Reader(
                                            pcm_frames=65536,
                                            sample_rate=44100,
                                            channels=channels,
                                            channel_mask=mask,
                                            bits_per_sample=bps)),
                                    **encode_opts)

    @FORMAT_FLAC
    def test_fractional(self):
        def __perform_test__(block_size, pcm_frames):
            self.__test_reader__(
                MD5_Reader(EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                block_size=block_size,
                max_lpc_order=8,
                min_residual_partition_order=0,
                max_residual_partition_order=6)

        for pcm_frames in [31, 32, 33, 34, 35, 2046, 2047, 2048, 2049, 2050]:
            __perform_test__(33, pcm_frames)

        for pcm_frames in [254, 255, 256, 257, 258, 510, 511, 512, 513,
                           514, 1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097, 4098]:
            __perform_test__(256, pcm_frames)

        for pcm_frames in [1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097, 4098]:
            __perform_test__(2048, pcm_frames)

        for pcm_frames in [1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097,
                           4098, 4606, 4607, 4608, 4609, 4610, 8190,
                           8191, 8192, 8193, 8194, 16382, 16383, 16384,
                           16385, 16386]:
            __perform_test__(4608, pcm_frames)

    #PCMReaders don't yet support seeking,
    #so the seek tests can be skipped

    #cuesheets are supported at the metadata level,
    #which is tested above

    #WAVE and AIFF length fixups are handled by the
    #WaveAudio and AIFFAudio classes

    #multiple file handling is performed at the tool level

    #as is metadata handling

    # @FORMAT_FLAC
    @LIB_CUSTOM
    def test_clean(self):
        #metadata is tested separately

        #check FLAC files with ID3 tags
        f = open("flac-id3.flac", "rb")
        self.assertEqual(f.read(3), "ID3")
        f.close()
        track = audiotools.open("flac-id3.flac")
        metadata1 = track.get_metadata()
        fixes = []
        self.assertEqual(track.clean(fixes), None)
        self.assertEqual(fixes,
                         [_(u"removed ID3v2 tag"),
                          _(u"removed ID3v1 tag")])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = []
            self.assertNotEqual(track.clean(fixes, temp.name), None)
            self.assertEqual(fixes,
                             [_(u"removed ID3v2 tag"),
                              _(u"removed ID3v1 tag")])
            f = open(temp.name, "rb")
            self.assertEqual(f.read(4), "fLaC")
            f.close()
            track2 = audiotools.open(temp.name)
            self.assertEqual(metadata1, track2.get_metadata())
            self.assertEqual(audiotools.pcm_frame_cmp(
                    track.to_pcm(), track2.to_pcm()), None)
        finally:
            temp.close()

        #check FLAC files with STREAMINFO in the wrong location
        f = open("flac-disordered.flac", "rb")
        self.assertEqual(f.read(5), "fLaC\x04")
        f.close()
        track = audiotools.open("flac-disordered.flac")
        metadata1 = track.get_metadata()
        fixes = []
        self.assertEqual(track.clean(fixes), None)
        self.assertEqual(fixes,
                         [_(u"moved STREAMINFO to first block")])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = []
            self.assertNotEqual(track.clean(fixes, temp.name), None)
            self.assertEqual(fixes,
                             [_(u"moved STREAMINFO to first block")])
            f = open(temp.name, "rb")
            self.assertEqual(f.read(5), "fLaC\x00")
            f.close()
            track2 = audiotools.open(temp.name)
            self.assertEqual(metadata1, track2.get_metadata())
            self.assertEqual(audiotools.pcm_frame_cmp(
                    track.to_pcm(), track2.to_pcm()), None)
        finally:
            temp.close()

        #check FLAC files with empty MD5 sum
        track = audiotools.open("flac-nonmd5.flac")
        fixes = []
        self.assertEqual(track.get_metadata().get_block(
                audiotools.flac.Flac_STREAMINFO.BLOCK_ID).md5sum, chr(0) * 16)
        self.assertEqual(track.clean(fixes), None)
        self.assertEqual(fixes, [_(u"populated empty MD5SUM")])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = []
            self.assertNotEqual(track.clean(fixes, temp.name), None)
            self.assertEqual(fixes, [_(u"populated empty MD5SUM")])
            track2 = audiotools.open(temp.name)
            self.assertEqual(track2.get_metadata().get_block(
                    audiotools.flac.Flac_STREAMINFO.BLOCK_ID).md5sum,
                             '\xd2\xb1 \x19\x90\x19\xb69' +
                             '\xd5\xa7\xe2\xb3F>\x9c\x97')
            self.assertEqual(audiotools.pcm_frame_cmp(
                    track.to_pcm(), track2.to_pcm()), None)
        finally:
            temp.close()

        #check 24bps/6ch FLAC files without WAVEFORMATEXTENSIBLE_CHANNEL_MASK
        for (path, mask) in [("flac-nomask1.flac", 0x3F),
                             ("flac-nomask2.flac", 0x3F),
                             ("flac-nomask3.flac", 0x3),
                             ("flac-nomask4.flac", 0x3)]:
            track = audiotools.open(path)
            fixes = []
            self.assertEqual(track.clean(fixes), None)
            self.assertEqual(fixes,
                             [_(u"added WAVEFORMATEXTENSIBLE_CHANNEL_MASK")])
            temp = tempfile.NamedTemporaryFile(suffix=".flac")
            try:
                fixes = []
                track.clean(fixes, temp.name)
                self.assertEqual(
                    fixes,
                    [_(u"added WAVEFORMATEXTENSIBLE_CHANNEL_MASK")])
                new_track = audiotools.open(temp.name)
                self.assertEqual(new_track.channel_mask(),
                                 track.channel_mask())
                self.assertEqual(int(new_track.channel_mask()), mask)
                metadata = new_track.get_metadata()

                self.assertEqual(
                    metadata.get_block(audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[
                        u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"][0],
                    u"0x%.4X" % (mask))
            finally:
                temp.close()

        #check bad seekpoint destinations
        track = audiotools.open("flac-seektable.flac")
        fixes = []
        self.assertEqual(track.clean(fixes), None)
        self.assertEqual(fixes, [_(u"fixed invalid SEEKTABLE")])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = []
            track.clean(fixes, temp.name)
            self.assertEqual(
                fixes,
                [_(u"fixed invalid SEEKTABLE")])
            new_track = audiotools.open(temp.name)
            fixes = []
            new_track.clean(fixes, None)
            self.assertEqual(fixes, [])
        finally:
            temp.close()


    @FORMAT_FLAC
    def test_nonmd5(self):
        flac = audiotools.open("flac-nonmd5.flac")
        self.assertEqual(flac.__md5__, chr(0) * 16)
        md5sum = md5()

        #ensure that a FLAC file with an empty MD5 sum
        #decodes without errors
        audiotools.transfer_framelist_data(flac.to_pcm(),
                                           md5sum.update)
        self.assertEqual(md5sum.hexdigest(),
                         'd2b120199019b639d5a7e2b3463e9c97')

        #ensure that a FLAC file with an empty MD5 sum
        #verifies without errors
        self.assertEqual(flac.verify(), True)


class M4AFileTest(LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.M4AAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_M4A
    def test_length(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for seconds in [1, 2, 3, 4, 5, 10, 20, 60, 120]:
                track = self.audio_class.from_pcm(temp.name,
                                                  BLANK_PCM_Reader(seconds))
                self.assertEqual(int(round(track.seconds_length())), seconds)
        finally:
            temp.close()

    @FORMAT_LOSSY
    def test_channels(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for channels in [1, 2, 3, 4, 5, 6]:
                track = self.audio_class.from_pcm(temp.name, BLANK_PCM_Reader(
                        1, channels=channels, channel_mask=0))
            if (self.audio_class is audiotools.m4a.M4AAudio_faac):
                self.assertEqual(track.channels(), 2)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), 2)
            else:
                self.assertEqual(track.channels(), max(2, channels))
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), max(2, channels))
        finally:
            temp.close()

    @FORMAT_M4A
    def test_too(self):
        #ensure that the 'too' meta atom isn't modified by setting metadata
        temp = tempfile.NamedTemporaryFile(
            suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                BLANK_PCM_Reader(1))
            metadata = track.get_metadata()
            encoder = unicode(metadata['ilst']['\xa9too'])
            track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
            metadata = track.get_metadata()
            self.assertEqual(metadata.track_name, u"Foo")
            self.assertEqual(unicode(metadata['ilst']['\xa9too']), encoder)
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

    @FORMAT_MP3
    def test_verify(self):
        #test invalid file sent to to_pcm()

        #FIXME - mpg123 doesn't generate errors on invalid files
        #Ultimately, all of MP3/MP2 decoding needs to be internalized
        #so that these sorts of errors can be caught consistently.

        # temp = tempfile.NamedTemporaryFile(
        #     suffix=self.suffix)
        # try:
        #     track = self.audio_class.from_pcm(
        #         temp.name,
        #         BLANK_PCM_Reader(1))
        #     good_data = open(temp.name, 'rb').read()
        #     f = open(temp.name, 'wb')
        #     f.write(good_data[0:100])
        #     f.close()
        #     reader = track.to_pcm()
        #     audiotools.transfer_framelist_data(reader, lambda x: x)
        #     self.assertRaises(audiotools.DecodingError,
        #                       reader.close)
        # finally:
        #     temp.close()

        #test invalid file send to convert()
        # temp = tempfile.NamedTemporaryFile(
        #     suffix=self.suffix)
        # try:
        #     track = self.audio_class.from_pcm(
        #         temp.name,
        #         BLANK_PCM_Reader(1))
        #     good_data = open(temp.name, 'rb').read()
        #     f = open(temp.name, 'wb')
        #     f.write(good_data[0:100])
        #     f.close()
        #     if (os.path.isfile("dummy.wav")):
        #         os.unlink("dummy.wav")
        #     self.assertEqual(os.path.isfile("dummy.wav"), False)
        #     self.assertRaises(audiotools.EncodingError,
        #                       track.convert,
        #                       "dummy.wav",
        #                       audiotools.WaveAudio)
        #     self.assertEqual(os.path.isfile("dummy.wav"), False)
        # finally:
        #     temp.close()

        # #test verify() on invalid files
        # temp = tempfile.NamedTemporaryFile(
        #     suffix=self.suffix)
        # mpeg_data = cStringIO.StringIO()
        # frame_header = audiotools.MPEG_Frame_Header("header")
        # try:
        #     mpx_file = audiotools.open("sine" + self.suffix)
        #     self.assertEqual(mpx_file.verify(), True)

        #     for (header, data) in mpx_file.mpeg_frames():
        #         mpeg_data.write(frame_header.build(header))
        #         mpeg_data.write(data)
        #     mpeg_data = mpeg_data.getvalue()

        #     temp.seek(0, 0)
        #     temp.write(mpeg_data)
        #     temp.flush()

        #     #first, try truncating the file underfoot
        #     bad_mpx_file = audiotools.open(temp.name)
        #     for i in xrange(len(mpeg_data)):
        #         try:
        #             if ((mpeg_data[i] == chr(0xFF)) and
        #                 (ord(mpeg_data[i + 1]) & 0xE0)):
        #                 #skip sizes that may be the end of a frame
        #                 continue
        #         except IndexError:
        #             continue

        #         f = open(temp.name, "wb")
        #         f.write(mpeg_data[0:i])
        #         f.close()
        #         self.assertEqual(os.path.getsize(temp.name), i)
        #         self.assertRaises(audiotools.InvalidFile,
        #                           bad_mpx_file.verify)

        #     #then try swapping some of the header bits
        #     for (field, value) in [("sample_rate", 48000),
        #                            ("channel", 3)]:
        #         temp.seek(0, 0)
        #         for (i, (header, data)) in enumerate(mpx_file.mpeg_frames()):
        #             if (i == 1):
        #                 setattr(header, field, value)
        #                 temp.write(frame_header.build(header))
        #                 temp.write(data)
        #             else:
        #                 temp.write(frame_header.build(header))
        #                 temp.write(data)
        #         temp.flush()
        #         new_file = audiotools.open(temp.name)
        #         self.assertRaises(audiotools.InvalidFile,
        #                           new_file.verify)
        # finally:
        #     temp.close()
        pass

    @FORMAT_MP3
    def test_id3_ladder(self):
        temp_file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp_file.name,
                                              BLANK_PCM_Reader(5))

            dummy_metadata = audiotools.MetaData(track_name=u"Foo")

            #ensure that setting particular ID3 variant
            #sticks, even through get/set_metadata
            track.set_metadata(dummy_metadata)
            for new_class in (audiotools.ID3v22Comment,
                              audiotools.ID3v23Comment,
                              audiotools.ID3v24Comment,
                              audiotools.ID3v23Comment,
                              audiotools.ID3v22Comment):
                metadata = new_class.converted(track.get_metadata())
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(isinstance(metadata, new_class), True)
                self.assertEqual(metadata.__class__, new_class([]).__class__)
                self.assertEqual(metadata, dummy_metadata)
        finally:
            temp_file.close()

    @FORMAT_MP3
    def test_ucs2(self):
        temp_file = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp_file.name,
                                              BLANK_PCM_Reader(5))

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
                metadata = audiotools.ID3v24Comment.converted(
                    audiotools.MetaData(track_name=u"Foo"))
                track.set_metadata(metadata)
                id3 = track.get_metadata()
                self.assertEqual(id3, metadata)

                metadata.track_name = test_string

                track.set_metadata(metadata)
                id3 = track.get_metadata()
                self.assertEqual(id3, metadata)

                metadata.comment = test_string
                track.set_metadata(metadata)
                id3 = track.get_metadata()
                self.assertEqual(id3, metadata)

                metadata.add_image(
                    audiotools.ID3v24Comment.IMAGE_FRAME.converted(
                        audiotools.ID3v24Comment.IMAGE_FRAME_ID,
                        audiotools.Image.new(TEST_COVER1,
                                             test_string,
                                             0)))
                track.set_metadata(metadata)
                id3 = track.get_metadata()
                self.assertEqual(id3.images()[0].description, test_string)

                #ID3v2.3 and ID3v2.2 only support UCS-2
                for id3_class in (audiotools.ID3v23Comment,
                                  audiotools.ID3v22Comment):
                    metadata = audiotools.ID3v23Comment.converted(
                        audiotools.MetaData(track_name=u"Foo"))
                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3, metadata)

                    #ensure that text fields round-trip correctly
                    #(i.e. the extra-wide char gets replaced)
                    metadata.track_name = test_string

                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3.track_name, test_string_out)

                    #ensure that comment blocks round-trip correctly
                    metadata.comment = test_string
                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3.track_name, test_string_out)

                    #ensure that image comment fields round-trip correctly
                    metadata.add_image(id3_class.IMAGE_FRAME.converted(
                            id3_class.IMAGE_FRAME_ID,
                            audiotools.Image.new(TEST_COVER1,
                                                 test_string,
                                                 0)))
                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3.images()[0].description,
                                     test_string_out)
        finally:
            temp_file.close()


class MP2FileTest(MP3FileTest):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio
        self.suffix = "." + self.audio_class.SUFFIX


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


class OggFlacFileTest(OggVerify,
                      LosslessFileTest):
    def setUp(self):
        from audiotools.decoders import OggFlacDecoder

        self.audio_class = audiotools.OggFlacAudio
        self.suffix = "." + self.audio_class.SUFFIX

        self.decoder = OggFlacDecoder

    @FORMAT_OGGFLAC
    def test_init(self):
        #check missing file
        self.assertRaises(audiotools.flac.InvalidFLAC,
                          audiotools.OggFlacAudio,
                          "/dev/null/foo")

        #check invalid file
        invalid_file = tempfile.NamedTemporaryFile(suffix=".oga")
        try:
            for c in "invalidstringxxx":
                invalid_file.write(c)
                invalid_file.flush()
                self.assertRaises(audiotools.flac.InvalidFLAC,
                                  audiotools.OggFlacAudio,
                                  invalid_file.name)
        finally:
            invalid_file.close()

        #check some decoder errors,
        #mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(TypeError, self.decoder, None)

        self.assertRaises(ValueError, self.decoder, "/dev/null", -1)


class ShortenFileTest(TestForeignWaveChunks,
                      TestForeignAiffChunks,
                      LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.ShortenAudio
        self.suffix = "." + self.audio_class.SUFFIX

        from audiotools.decoders import SHNDecoder
        from audiotools.encoders import encode_shn
        self.decoder = SHNDecoder
        self.encode = encode_shn
        self.encode_opts = [{"block_size": 4},
                            {"block_size": 256},
                            {"block_size": 1024}]

    @FORMAT_SHORTEN
    def test_init(self):
        #check missing file
        self.assertRaises(audiotools.shn.InvalidShorten,
                          audiotools.ShortenAudio,
                          "/dev/null/foo")

        #check invalid file
        invalid_file = tempfile.NamedTemporaryFile(suffix=".shn")
        try:
            for c in "invalidstringxxx":
                invalid_file.write(c)
                invalid_file.flush()
                self.assertRaises(audiotools.shn.InvalidShorten,
                                  audiotools.ShortenAudio,
                                  invalid_file.name)
        finally:
            invalid_file.close()

        #check some decoder errors,
        #mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(TypeError, self.decoder, None)

        self.assertRaises(IOError, self.decoder, "/dev/null/foo")

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
        for (first, last, filename) in [(62, 89, "shorten-frames.shn"),
                                        (61, 116, "shorten-lpc.shn")]:

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
                    self.assertRaises(IOError,
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
                                      decoder.pcm_split)

                    decoder = audiotools.decoders.SHNDecoder(temp.name)
                    self.assertNotEqual(decoder, None)
                    self.assertRaises(IOError,
                                      audiotools.transfer_framelist_data,
                                      decoder, lambda x: x)
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

    def __stream_variations__(self):
        for stream in [
            test_streams.Sine8_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine8_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine8_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine8_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine8_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine8_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine8_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine8_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Sine16_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine16_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),
            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine16_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Simple_Sine(200000, 44100, 0x7, 8,
                                     (25, 10000),
                                     (50, 20000),
                                     (120, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 8,
                                     (25, 10000),
                                     (50, 20000),
                                     (75, 30000),
                                     (65, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 8,
                                     (25, 10000),
                                     (35, 15000),
                                     (45, 20000),
                                     (50, 25000),
                                     (55, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 8,
                                     (25, 10000),
                                     (45, 15000),
                                     (65, 20000),
                                     (85, 25000),
                                     (105, 30000),
                                     (120, 35000)),

            test_streams.Simple_Sine(200000, 44100, 0x7, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (30720, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (19200, 30000),
                                     (16640, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 16,
                                     (6400, 10000),
                                     (8960, 15000),
                                     (11520, 20000),
                                     (12800, 25000),
                                     (14080, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000))]:
            yield stream

    @FORMAT_SHORTEN
    def test_streams(self):
        for g in self.__stream_variations__():
            md5sum = md5()
            f = g.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = g.read(audiotools.FRAMELIST_SIZE)
            self.assertEqual(md5sum.digest(), g.digest())
            g.close()

    def __test_reader__(self, pcmreader, **encode_options):
        if (not audiotools.BIN.can_execute(audiotools.BIN["shorten"])):
            self.assert_(False,
                         "reference Shorten binary shorten(1) required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".shn")

        #construct a temporary wave file from pcmreader
        temp_input_wave_file = tempfile.NamedTemporaryFile(suffix=".wav")
        temp_input_wave = audiotools.WaveAudio.from_pcm(
            temp_input_wave_file.name, pcmreader)
        temp_input_wave.verify()

        options = encode_options.copy()
        (head, tail) = temp_input_wave.pcm_split()
        options["is_big_endian"] = False
        options["signed_samples"] = (pcmreader.bits_per_sample == 16)
        options["header_data"] = head
        if (len(tail) > 0):
            options["footer_data"] = tail

        self.encode(temp_file.name,
                    temp_input_wave.to_pcm(),
                    **options)

        shn = audiotools.open(temp_file.name)
        self.assert_(shn.total_frames() > 0)

        temp_wav_file1 = tempfile.NamedTemporaryFile(suffix=".wav")
        temp_wav_file2 = tempfile.NamedTemporaryFile(suffix=".wav")

        #first, ensure the Shorten-encoded file
        #has the same MD5 signature as pcmreader once decoded
        md5sum = md5()
        d = self.decoder(temp_file.name)
        f = d.read(audiotools.FRAMELIST_SIZE)
        while (len(f) > 0):
            md5sum.update(f.to_bytes(False, True))
            f = d.read(audiotools.FRAMELIST_SIZE)
        d.close()
        self.assertEqual(md5sum.digest(), pcmreader.digest())

        #then compare our .to_wave() output
        #with that of the Shorten reference decoder
        shn.convert(temp_wav_file1.name, audiotools.WaveAudio)
        subprocess.call([audiotools.BIN["shorten"],
                         "-x", shn.filename, temp_wav_file2.name])

        wave = audiotools.WaveAudio(temp_wav_file1.name)
        wave.verify()
        wave = audiotools.WaveAudio(temp_wav_file2.name)
        wave.verify()

        self.assertEqual(audiotools.pcm_frame_cmp(
                audiotools.WaveAudio(temp_wav_file1.name).to_pcm(),
                audiotools.WaveAudio(temp_wav_file2.name).to_pcm()),
                         None)

        temp_file.close()
        temp_wav_file1.close()
        temp_wav_file2.close()

        #then perform PCM -> aiff -> Shorten -> PCM testing

        #construct a temporary wave file from pcmreader
        temp_input_aiff_file = tempfile.NamedTemporaryFile(suffix=".aiff")
        temp_input_aiff = temp_input_wave.convert(temp_input_aiff_file.name,
                                                  audiotools.AiffAudio)
        temp_input_aiff.verify()

        options = encode_options.copy()
        options["is_big_endian"] = True
        options["signed_samples"] = True
        (head, tail) = temp_input_aiff.pcm_split()
        options["header_data"] = head
        if (len(tail) > 0):
            options["footer_data"] = tail

        self.encode(temp_file.name,
                    temp_input_aiff.to_pcm(),
                    **options)

        shn = audiotools.open(temp_file.name)
        self.assert_(shn.total_frames() > 0)

        temp_aiff_file1 = tempfile.NamedTemporaryFile(suffix=".aiff")
        temp_aiff_file2 = tempfile.NamedTemporaryFile(suffix=".aiff")

        #first, ensure the Shorten-encoded file
        #has the same MD5 signature as pcmreader once decoded
        md5sum = md5()
        d = self.decoder(temp_file.name)
        f = d.read(audiotools.BUFFER_SIZE)
        while (len(f) > 0):
            md5sum.update(f.to_bytes(False, True))
            f = d.read(audiotools.BUFFER_SIZE)
        d.close()
        self.assertEqual(md5sum.digest(), pcmreader.digest())

        #then compare our .to_aiff() output
        #with that of the Shorten reference decoder
        shn.convert(temp_aiff_file1.name, audiotools.AiffAudio)

        subprocess.call([audiotools.BIN["shorten"],
                         "-x", shn.filename, temp_aiff_file2.name])

        aiff = audiotools.AiffAudio(temp_aiff_file1.name)
        aiff.verify()
        aiff = audiotools.AiffAudio(temp_aiff_file2.name)
        aiff.verify()

        self.assertEqual(audiotools.pcm_frame_cmp(
                audiotools.AiffAudio(temp_aiff_file1.name).to_pcm(),
                audiotools.AiffAudio(temp_aiff_file2.name).to_pcm()),
                         None)

        temp_file.close()
        temp_input_aiff_file.close()
        temp_input_wave_file.close()
        temp_aiff_file1.close()
        temp_aiff_file2.close()

    @FORMAT_SHORTEN
    def test_small_files(self):
        for g in [test_streams.Generate01,
                  test_streams.Generate02,
                  test_streams.Generate03,
                  test_streams.Generate04]:
            gen = g(44100)
            self.__test_reader__(gen, block_size=256)

    @FORMAT_SHORTEN
    def test_full_scale_deflection(self):
        for (bps, fsd) in [(8, test_streams.fsd8),
                           (16, test_streams.fsd16)]:
            for pattern in [test_streams.PATTERN01,
                            test_streams.PATTERN02,
                            test_streams.PATTERN03,
                            test_streams.PATTERN04,
                            test_streams.PATTERN05,
                            test_streams.PATTERN06,
                            test_streams.PATTERN07]:
                stream = test_streams.MD5Reader(fsd(pattern, 100))
                self.__test_reader__(
                    stream, block_size=256)

    @FORMAT_SHORTEN
    def test_sines(self):
        for g in self.__stream_variations__():
            self.__test_reader__(g, block_size=256)

    @FORMAT_SHORTEN
    def test_blocksizes(self):
        noise = struct.unpack(">32h", os.urandom(64))

        for block_size in [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           256, 1024]:
            args = {"block_size": block_size}
            self.__test_reader__(test_streams.MD5Reader(
                    test_streams.FrameListReader(noise, 44100, 1, 16)), **args)

    @FORMAT_SHORTEN
    def test_noise(self):
        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(
                        front_left=True,
                        front_right=True,
                        back_left=True,
                        back_right=True)),
                (8, audiotools.ChannelMask(0))]:
                for bps in [8, 16]:
                    self.__test_reader__(
                        MD5_Reader(EXACT_RANDOM_PCM_Reader(
                                pcm_frames=65536,
                                sample_rate=44100,
                                channels=channels,
                                channel_mask=mask,
                                bits_per_sample=bps)),
                        **encode_opts)


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

    @FORMAT_VORBIS
    def test_big_comment(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(1))
            pcm = track.to_pcm()
            original_pcm_sum = md5()
            audiotools.transfer_framelist_data(pcm, original_pcm_sum.update)
            pcm.close()

            comment = audiotools.MetaData(
                track_name=u"Name",
                track_number=1,
                comment=u"abcdefghij" * 13005)
            track.set_metadata(comment)
            track = audiotools.open(track_file.name)
            self.assertEqual(comment, track.get_metadata())

            pcm = track.to_pcm()
            new_pcm_sum = md5()
            audiotools.transfer_framelist_data(pcm, new_pcm_sum.update)
            pcm.close()

            self.assertEqual(original_pcm_sum.hexdigest(),
                             new_pcm_sum.hexdigest())
        finally:
            track_file.close()

    @FORMAT_AUDIOFILE
    def test_replay_gain(self):
        self.assert_(True)
        #FIXME

        #ReplayGain gets punted to vorbisgain,
        #so we won't test it directly.
        #In the future, I should fold libvorbis
        #into the tools directly
        #and handle gain calculation/application
        #as floats from end-to-end
        #which should eliminate the vorbisgain requirement.


class WaveFileTest(TestForeignWaveChunks,
                   LosslessFileTest):
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
        #FIXME - truncate file underfoot
        # temp = tempfile.NamedTemporaryFile(suffix=".flac")
        # try:
        #     temp.write(open("wav-2ch.wav", "rb").read()[0:-10])
        #     temp.flush()
        #     flac = audiotools.open(temp.name)
        #     if (os.path.isfile("dummy.wav")):
        #         os.unlink("dummy.wav")
        #     self.assertEqual(os.path.isfile("dummy.wav"), False)
        #     self.assertRaises(audiotools.EncodingError,
        #                       flac.convert,
        #                       "dummy.wav",
        #                       audiotools.WaveAudio)
        #     self.assertEqual(os.path.isfile("dummy.wav"), False)
        # finally:
        #     temp.close()

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

            finally:
                temp.close()

        #test for non-ASCII chunk IDs
        from struct import pack

        chunks = list(audiotools.open("wav-2ch.wav").chunks()) + \
            [audiotools.wav.RIFF_Chunk("fooz", 10, chr(0) * 10)]
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
                              audiotools.open(temp.name).verify)
        finally:
            temp.close()

        FMT = audiotools.wav.RIFF_Chunk(
            "fmt ",
            16,
            '\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00')

        DATA = audiotools.wav.RIFF_Chunk(
            "data",
            26,
            '\x00\x00\x01\x00\x02\x00\x03\x00\x02\x00\x01\x00\x00\x00\xff\xff\xfe\xff\xfd\xff\xfe\xff\xff\xff\x00\x00')

        #test multiple fmt chunks
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            for chunks in [[FMT, FMT, DATA],
                           [FMT, DATA, FMT]]:
                audiotools.WaveAudio.wave_from_chunks(temp.name, chunks)
                self.assertRaises(
                    audiotools.InvalidFile,
                    audiotools.open(temp.name).verify)
        finally:
            temp.close()

        #test multiple data chunks
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [FMT, DATA, DATA])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

        #test data chunk before fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [DATA, FMT])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

        #test no fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [DATA])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

        #test no data chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [FMT])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

    @FORMAT_WAVE
    def test_clean(self):
        FMT = audiotools.wav.RIFF_Chunk(
            "fmt ",
            16,
            '\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00')

        DATA = audiotools.wav.RIFF_Chunk(
            "data",
            26,
            '\x00\x00\x01\x00\x02\x00\x03\x00\x02\x00\x01\x00\x00\x00\xff\xff\xfe\xff\xfd\xff\xfe\xff\xff\xff\x00\x00')

        #test multiple fmt chunks
        #test multiple data chunks
        #test data chunk before fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        fixed = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            for chunks in [[FMT, FMT, DATA],
                           [FMT, DATA, FMT],
                           [FMT, DATA, DATA],
                           [DATA, FMT],
                           [DATA, FMT, FMT]]:
                audiotools.WaveAudio.wave_from_chunks(temp.name, chunks)
                fixes = []
                wave = audiotools.open(temp.name).clean(fixes, fixed.name)
                chunks = list(wave.chunks())
                self.assertEquals([c.id for c in chunks],
                                  [c.id for c in [FMT, DATA]])
                self.assertEquals([c.__size__ for c in chunks],
                                  [c.__size__ for c in [FMT, DATA]])
                self.assertEquals([c.__data__ for c in chunks],
                                  [c.__data__ for c in [FMT, DATA]])
        finally:
            temp.close()
            fixed.close()

        #test converting 24bps file to WAVEFORMATEXTENSIBLE
        #FIXME

class WavPackFileTest(TestForeignWaveChunks,
                      LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio
        self.suffix = "." + self.audio_class.SUFFIX

        from audiotools.decoders import WavPackDecoder
        from audiotools.encoders import encode_wavpack

        self.decoder = WavPackDecoder
        self.encode = encode_wavpack
        self.encode_opts = [{"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": False,
                             "decorrelation_passes": 0},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "decorrelation_passes": 0},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "decorrelation_passes": 1},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "decorrelation_passes": 2},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "decorrelation_passes": 5},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "decorrelation_passes": 10},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "decorrelation_passes": 16}]

    @FORMAT_WAVPACK
    def test_init(self):
        #check missing file
        self.assertRaises(audiotools.wavpack.InvalidWavPack,
                          audiotools.WavPackAudio,
                          "/dev/null/foo")

        #check invalid file
        invalid_file = tempfile.NamedTemporaryFile(suffix=".wv")
        try:
            for c in "invalidstringxxx":
                invalid_file.write(c)
                invalid_file.flush()
                self.assertRaises(audiotools.wavpack.InvalidWavPack,
                                  audiotools.WavPackAudio,
                                  invalid_file.name)
        finally:
            invalid_file.close()

        #check some decoder errors,
        #mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(TypeError, self.decoder, None)

        self.assertRaises(IOError, self.decoder, "/dev/null/foo")

        self.assertRaises(IOError, self.decoder, "/dev/null", sample_rate=-1)

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

    def __stream_variations__(self):
        for stream in [
            test_streams.Sine8_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine8_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine8_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine8_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine8_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine8_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine8_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine8_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine8_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Sine16_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine16_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine16_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine16_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine16_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine16_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Sine24_Mono(200000, 48000, 441.0, 0.50, 441.0, 0.49),
            test_streams.Sine24_Mono(200000, 96000, 441.0, 0.61, 661.5, 0.37),
            test_streams.Sine24_Mono(200000, 44100, 441.0, 0.50, 882.0, 0.49),
            test_streams.Sine24_Mono(200000, 44100, 441.0, 0.50, 4410.0, 0.49),
            test_streams.Sine24_Mono(200000, 44100, 8820.0, 0.70, 4410.0, 0.29),

            test_streams.Sine24_Stereo(200000, 48000, 441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 48000, 441.0, 0.61, 661.5, 0.37, 1.0),
            test_streams.Sine24_Stereo(200000, 96000, 441.0, 0.50, 882.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 1.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 441.0, 0.49, 0.5),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.61, 661.5, 0.37, 2.0),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 882.0, 0.49, 0.7),
            test_streams.Sine24_Stereo(200000, 44100, 441.0, 0.50, 4410.0, 0.49, 1.3),
            test_streams.Sine24_Stereo(200000, 44100, 8820.0, 0.70, 4410.0, 0.29, 0.1),

            test_streams.Simple_Sine(200000, 44100, 0x7, 8,
                                     (25, 10000),
                                     (50, 20000),
                                     (120, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 8,
                                     (25, 10000),
                                     (50, 20000),
                                     (75, 30000),
                                     (65, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 8,
                                     (25, 10000),
                                     (35, 15000),
                                     (45, 20000),
                                     (50, 25000),
                                     (55, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 8,
                                     (25, 10000),
                                     (45, 15000),
                                     (65, 20000),
                                     (85, 25000),
                                     (105, 30000),
                                     (120, 35000)),

            test_streams.Simple_Sine(200000, 44100, 0x7, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (30720, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 16,
                                     (6400, 10000),
                                     (12800, 20000),
                                     (19200, 30000),
                                     (16640, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 16,
                                     (6400, 10000),
                                     (8960, 15000),
                                     (11520, 20000),
                                     (12800, 25000),
                                     (14080, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000)),

            test_streams.Simple_Sine(200000, 44100, 0x7, 24,
                                     (1638400, 10000),
                                     (3276800, 20000),
                                     (7864320, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x33, 24,
                                     (1638400, 10000),
                                     (3276800, 20000),
                                     (4915200, 30000),
                                     (4259840, 40000)),
            test_streams.Simple_Sine(200000, 44100, 0x37, 24,
                                     (1638400, 10000),
                                     (2293760, 15000),
                                     (2949120, 20000),
                                     (3276800, 25000),
                                     (3604480, 30000)),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 24,
                                     (1638400, 10000),
                                     (2949120, 15000),
                                     (4259840, 20000),
                                     (5570560, 25000),
                                     (6881280, 30000),
                                     (7864320, 35000))]:
            yield stream

    def __test_reader__(self, pcmreader, **encode_options):
        if (not audiotools.BIN.can_execute(audiotools.BIN["wvunpack"])):
            self.assert_(False,
                         "reference WavPack binary wvunpack(1) required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".wv")
        self.encode(temp_file.name,
                    audiotools.BufferedPCMReader(pcmreader),
                    **encode_options)

        sub = subprocess.Popen([audiotools.BIN["wvunpack"],
                                "-vmq", temp_file.name],
                               stdout=open(os.devnull, "wb"),
                               stderr=open(os.devnull, "wb"))

        self.assertEqual(sub.wait(), 0,
                         "wvunpack decode error on %s with options %s" % \
                             (repr(pcmreader),
                              repr(encode_options)))

        wavpack = self.decoder(temp_file.name)
        self.assertEqual(wavpack.sample_rate, pcmreader.sample_rate)
        self.assertEqual(wavpack.bits_per_sample, pcmreader.bits_per_sample)
        self.assertEqual(wavpack.channels, pcmreader.channels)
        self.assertEqual(wavpack.channel_mask, pcmreader.channel_mask)

        md5sum = md5()
        f = wavpack.read(audiotools.FRAMELIST_SIZE)
        while (len(f) > 0):
            md5sum.update(f.to_bytes(False, True))
            f = wavpack.read(audiotools.FRAMELIST_SIZE)
        wavpack.close()
        self.assertEqual(md5sum.digest(), pcmreader.digest())
        temp_file.close()

    @FORMAT_WAVPACK
    def test_small_files(self):
        for opts in self.encode_opts:
            for g in [test_streams.Generate01,
                      test_streams.Generate02,
                      test_streams.Generate03,
                      test_streams.Generate04]:
                gen = g(44100)
                self.__test_reader__(gen, **opts)

    @FORMAT_WAVPACK
    def test_full_scale_deflection(self):
        for opts in self.encode_opts:
            for (bps, fsd) in [(8, test_streams.fsd8),
                               (16, test_streams.fsd16),
                               (24, test_streams.fsd24)]:
                for pattern in [test_streams.PATTERN01,
                                test_streams.PATTERN02,
                                test_streams.PATTERN03,
                                test_streams.PATTERN04,
                                test_streams.PATTERN05,
                                test_streams.PATTERN06,
                                test_streams.PATTERN07]:
                    self.__test_reader__(
                        test_streams.MD5Reader(fsd(pattern, 100)), **opts)

    @FORMAT_WAVPACK
    def test_wasted_bps(self):
        for opts in self.encode_opts:
            self.__test_reader__(test_streams.WastedBPS16(1000), **opts)

    @FORMAT_WAVPACK
    def test_blocksizes(self):
        noise = struct.unpack(">32h", os.urandom(64))

        opts = {"false_stereo": False,
                "wasted_bits": False,
                "joint_stereo": False}
        for block_size in [16, 17, 18, 19, 20, 21, 22, 23,
                           24, 25, 26, 27, 28, 29, 30, 31, 32, 33]:
            for decorrelation_passes in [0, 1, 5]:
                opts_copy = opts.copy()
                opts_copy["block_size"] = block_size
                opts_copy["decorrelation_passes"] = decorrelation_passes
                self.__test_reader__(test_streams.MD5Reader(
                        test_streams.FrameListReader(noise,
                                                     44100, 1, 16)),
                                     **opts_copy)

    @FORMAT_WAVPACK
    def test_silence(self):
        for opts in self.encode_opts:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(
                        front_left=True,
                        front_right=True,
                        back_left=True,
                        back_right=True)),
                (8, audiotools.ChannelMask(0))]:
                for bps in [8, 16, 24]:
                    opts_copy = opts.copy()
                    for block_size in [44100, 32, 32768, 65535,
                                       16777215]:
                        opts_copy['block_size'] = block_size

                        self.__test_reader__(
                            MD5_Reader(
                                EXACT_SILENCE_PCM_Reader(
                                    pcm_frames=65536,
                                    sample_rate=44100,
                                    channels=channels,
                                    channel_mask=mask,
                                    bits_per_sample=bps)),
                            **opts_copy)

    @FORMAT_WAVPACK
    def test_noise(self):
        for opts in self.encode_opts:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(
                        front_left=True,
                        front_right=True,
                        back_left=True,
                        back_right=True)),
                (8, audiotools.ChannelMask(0))]:
                for bps in [8, 16, 24]:
                    opts_copy = opts.copy()
                    for block_size in [44100, 32, 32768, 65535,
                                       16777215]:
                        opts_copy['block_size'] = block_size

                        self.__test_reader__(
                            MD5_Reader(EXACT_RANDOM_PCM_Reader(
                                    pcm_frames=65536,
                                    sample_rate=44100,
                                    channels=channels,
                                    channel_mask=mask,
                                    bits_per_sample=bps)),
                            **opts_copy)

    @FORMAT_WAVPACK
    def test_fractional(self):
        def __perform_test__(block_size, pcm_frames):
            self.__test_reader__(
                MD5_Reader(EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                block_size=block_size,
                decorrelation_passes=5,
                false_stereo=False,
                wasted_bits=False,
                joint_stereo=False)

        for pcm_frames in [31, 32, 33, 34, 35, 2046, 2047, 2048, 2049, 2050]:
            __perform_test__(33, pcm_frames)

        for pcm_frames in [254, 255, 256, 257, 258, 510, 511, 512, 513,
                           514, 1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097, 4098]:
            __perform_test__(256, pcm_frames)

        for pcm_frames in [1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097, 4098]:
            __perform_test__(2048, pcm_frames)

        for pcm_frames in [1022, 1023, 1024, 1025, 1026, 2046, 2047,
                           2048, 2049, 2050, 4094, 4095, 4096, 4097,
                           4098, 4606, 4607, 4608, 4609, 4610, 8190,
                           8191, 8192, 8193, 8194, 16382, 16383, 16384,
                           16385, 16386]:
            __perform_test__(4608, pcm_frames)

        for pcm_frames in [44098, 44099, 44100, 44101, 44102, 44103,
                           88198, 88199, 88200, 88201, 88202, 88203]:
            __perform_test__(44100, pcm_frames)

    @FORMAT_WAVPACK
    def test_multichannel(self):
        def __permutations__(executables, options, total):
            if (total == 0):
                yield []
            else:
                for (executable, option) in zip(executables,
                                                options):
                    for permutation in __permutations__(executables,
                                                         options,
                                                         total - 1):
                        yield [executable(**option)] + permutation

        #test a mix of identical and non-identical channels
        #using different decorrelation, joint stereo and false stereo options
        combos = 0
        for (false_stereo, joint_stereo) in [(False, False),
                                             (False, True),
                                             (True, False),
                                             (True, True)]:
            for (channels, mask) in [(2, 0x3), (3, 0x7), (4, 0x33),
                                     (5, 0x3B), (6, 0x3F)]:
                for readers in __permutations__([
                        EXACT_BLANK_PCM_Reader,
                        EXACT_RANDOM_PCM_Reader,
                        test_streams.Sine16_Mono],
                                                [
                        {"pcm_frames": 100,
                         "sample_rate": 44100,
                         "channels": 1,
                         "bits_per_sample": 16},
                        {"pcm_frames": 100,
                         "sample_rate": 44100,
                         "channels": 1,
                         "bits_per_sample": 16},
                        {"pcm_frames": 100,
                         "sample_rate": 44100,
                         "f1": 441.0,
                         "a1": 0.61,
                         "f2": 661.5,
                         "a2": 0.37}],
                                                channels):
                    joined = MD5_Reader(Join_Reader(readers, mask))
                    self.__test_reader__(joined,
                                         block_size=44100,
                                         false_stereo=false_stereo,
                                         joint_stereo=joint_stereo,
                                         decorrelation_passes=1,
                                         wasted_bits=False)

    @FORMAT_WAVPACK
    def test_sines(self):
        for opts in self.encode_opts:
            for g in self.__stream_variations__():
                self.__test_reader__(g, **opts)

    @FORMAT_WAVPACK
    def test_option_variations(self):
        for block_size in [11025, 22050, 44100, 88200, 176400]:
            for false_stereo in [False, True]:
                for wasted_bits in [False, True]:
                    for joint_stereo in [False, True]:
                        for decorrelation_passes in [0, 1, 2, 5, 10, 16]:
                            self.__test_reader__(
                                test_streams.Sine16_Stereo(200000,
                                                           48000,
                                                           441.0,
                                                           0.50,
                                                           441.0,
                                                           0.49,
                                                           1.0),
                                block_size=block_size,
                                false_stereo=false_stereo,
                                wasted_bits=wasted_bits,
                                joint_stereo=joint_stereo,
                                decorrelation_passes=decorrelation_passes)


class SineStreamTest(unittest.TestCase):
    @FORMAT_SINES
    def test_init(self):
        from audiotools.decoders import Sine_Mono
        from audiotools.decoders import Sine_Stereo
        from audiotools.decoders import Sine_Simple

        #ensure that failed inits don't make Python explode
        self.assertRaises(ValueError, Sine_Mono,
                          -1, 4000, 44100, 1.0, 1.0, 1.0, 1.0)
        self.assertRaises(ValueError, Sine_Mono,
                          16, -1, 44100, 1.0, 1.0, 1.0, 1.0)
        self.assertRaises(ValueError, Sine_Mono,
                          16, 4000, -1, 1.0, 1.0, 1.0, 1.0)

        self.assertRaises(ValueError, Sine_Stereo,
                          -1, 4000, 44100, 1.0, 1.0, 1.0, 1.0, 1.0)
        self.assertRaises(ValueError, Sine_Stereo,
                          16, -1, 44100, 1.0, 1.0, 1.0, 1.0, 1.0)
        self.assertRaises(ValueError, Sine_Stereo,
                          16, 4000, -1, 1.0, 1.0, 1.0, 1.0, 1.0)

        self.assertRaises(ValueError, Sine_Simple,
                          -1, 4000, 44100, 100, 100)
        self.assertRaises(ValueError, Sine_Simple,
                          16, -1, 44100, 100, 100)
        self.assertRaises(ValueError, Sine_Simple,
                          16, 4000, -1, 100, 100)
