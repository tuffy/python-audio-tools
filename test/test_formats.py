#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import unittest
import audiotools
import tempfile
import os
import os.path
from hashlib import md5
import random
import decimal
import test_streams
from io import BytesIO
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


# add a bunch of decorator metafunctions like LIB_CORE
# which can be wrapped around individual tests as needed
for section in parser.sections():
    for option in parser.options(section):
        if (parser.getboolean(section, option)):
            vars()["%s_%s" % (section.upper(),
                              option.upper())] = lambda function: function
        else:
            vars()["%s_%s" % (section.upper(),
                              option.upper())] = lambda function: do_nothing


class CLOSE_PCM_Reader(audiotools.PCMReader):
    def __init__(self, pcmreader):
        audiotools.PCMReader.__init__(
            self,
            sample_rate=pcmreader.sample_rate,
            channels=pcmreader.channels,
            channel_mask=pcmreader.channel_mask,
            bits_per_sample=pcmreader.bits_per_sample)
        self.pcmreader = pcmreader
        self.closes_called = 0

    def read(self, pcm_frames):
        return self.pcmreader.read(pcm_frames)

    def close(self):
        self.closes_called += 1
        self.pcmreader.close()


class ERROR_PCM_Reader(audiotools.PCMReader):
    def __init__(self, error,
                 sample_rate=44100, channels=2, bits_per_sample=16,
                 channel_mask=None, failure_chance=.2, minimum_successes=0):
        if (channel_mask is None):
            channel_mask = audiotools.ChannelMask.from_channels(channels)
        audiotools.PCMReader.__init__(
            self,
            sample_rate=sample_rate,
            channels=channels,
            bits_per_sample=bits_per_sample,
            channel_mask=channel_mask)
        self.error = error

        # this is so we can generate some "live" PCM data
        # before erroring out due to our error
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
                [self.frame for i in range(pcm_frames)])
        else:
            if (random.random() <= self.failure_chance):
                raise self.error
            else:
                return audiotools.pcm.from_frames(
                    [self.frame for i in range(pcm_frames)])

    def close(self):
        pass


class Log:
    def __init__(self):
        self.results = []

    def update(self, *args):
        self.results.append(args)


class Filewrapper:
    def __init__(self, file):
        self.file = file

    def read(self, bytes):
        return self.file.read(bytes)

    def tell(self):
        return self.file.tell()

    def seek(self, pos):
        self.file.seek(pos)

    def close(self):
        self.file.close()


class AudioFileTest(unittest.TestCase):
    def setUp(self):
        self.audio_class = audiotools.AudioFile
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AUDIOFILE
    def test_init(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        # first check nonexistent files
        self.assertRaises(audiotools.InvalidFile,
                          self.audio_class,
                          "/dev/null/foo.%s" % (self.audio_class.SUFFIX))

        f = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            # then check empty files
            f.write(b"")
            f.flush()
            self.assertEqual(os.path.isfile(f.name), True)
            self.assertRaises(audiotools.InvalidFile,
                              self.audio_class,
                              f.name)

            # then check files with a bit of junk at the beginning
            f.write(b'\x1aS\xc9\xf0I\xb2"CW\xd6')
            f.flush()
            self.assertGreater(os.path.getsize(f.name), 0)
            self.assertRaises(audiotools.InvalidFile,
                              self.audio_class,
                              f.name)

            # finally, check unreadable files
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
        # generate a valid file and check audiotools.file_type
        self.audio_class.from_pcm(valid.name, BLANK_PCM_Reader(1))
        with open(valid.name, "rb") as f:
            self.assertEqual(audiotools.file_type(f), self.audio_class)

        # several invalid files and ensure audiotools.file_type
        # returns None
        # (though it's *possible* os.urandom might generate a valid file
        # by virtue of being random that's extremely unlikely in practice)
        for i in range(256):
            self.assertEqual(os.path.getsize(invalid.name), i)
            with open(invalid.name, "rb") as f:
                self.assertEqual(audiotools.file_type(f), None)
            invalid.write(os.urandom(1))
            invalid.flush()

        valid.close()
        invalid.close()

    @FORMAT_AUDIOFILE
    def test_bits_per_sample(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        for bps in (8, 16, 24):
            track = self.audio_class.from_pcm(
                temp.name, BLANK_PCM_Reader(1, bits_per_sample=bps))
            self.assertEqual(track.bits_per_sample(), bps)
            track2 = audiotools.open(temp.name)
            self.assertEqual(track2.bits_per_sample(), bps)
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

        dummy_metadata = audiotools.MetaData(
            **dict([(field, char) for (field, char) in zip(
                    audiotools.MetaData.FIELDS,
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

            # check that delete_metadata works
            nonblank_metadata = audiotools.MetaData(
                track_name=u"Track Name",
                track_number=1,
                track_total=2,
                album_name=u"Album Name")
            track.set_metadata(nonblank_metadata)
            self.assertEqual(track.get_metadata(), nonblank_metadata)
            track.delete_metadata()
            metadata = track.get_metadata()
            if (metadata is not None):
                self.assertEqual(
                    metadata,
                    audiotools.MetaData())

            track.set_metadata(nonblank_metadata)
            self.assertEqual(track.get_metadata(), nonblank_metadata)

            old_mode = os.stat(track.filename).st_mode
            os.chmod(track.filename, 0o400)
            try:
                # check IOError on set_metadata()
                self.assertRaises(IOError,
                                  track.set_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # check IOError on delete_metadata()
                self.assertRaises(IOError,
                                  track.delete_metadata)
            finally:
                os.chmod(track.filename, old_mode)

            os.chmod(track.filename, 0)
            try:
                # check IOError on get_metadata()
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
                self.assertEqual(int(track.seconds_length()), seconds)
        finally:
            temp.close()

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_pcm(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_convert(self):
        self.assert_(False)

    @FORMAT_AUDIOFILE
    def test_context_manager(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        with tempfile.NamedTemporaryFile(suffix=self.suffix) as temp:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(5))
            with track.to_pcm() as pcmreader:
                frame = pcmreader.read(4096)
                while (len(frame) > 0):
                    frame = pcmreader.read(4096)

    @FORMAT_AUDIOFILE
    def test_read_leaks(self):
        # this checks to make sure PCMReader implementations
        # aren't leaking file handles

        if (self.audio_class is audiotools.AudioFile):
            return
        elif (self.audio_class.NAME == "m4a"):
            # M4A implemented using external programs
            # so no need to check those
            return

        # make small temporary file
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        track = self.audio_class.from_pcm(temp.name,
                                          BLANK_PCM_Reader(10))

        # open it a large number of times
        for i in range(5000):
            pcmreader = track.to_pcm()
            pcmreader.close()
            del(pcmreader)

        temp.close()

    @FORMAT_AUDIOFILE
    def test_close(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        pcm_frames = 123456

        with tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX) as f:
            reader = CLOSE_PCM_Reader(EXACT_SILENCE_PCM_Reader(pcm_frames))
            self.assertEqual(reader.closes_called, 0)
            track = self.audio_class.from_pcm(f.name,
                                              reader)
            self.assertEqual(reader.closes_called, 1)

        with tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX) as f:
            reader = CLOSE_PCM_Reader(EXACT_SILENCE_PCM_Reader(pcm_frames))
            self.assertEqual(reader.closes_called, 0)
            track = self.audio_class.from_pcm(f.name,
                                              reader,
                                              total_pcm_frames=pcm_frames)
            self.assertEqual(reader.closes_called, 1)

    @FORMAT_AUDIOFILE
    def test_convert_progress(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        with tempfile.NamedTemporaryFile(suffix=self.suffix) as temp:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(10))
            if (track.lossless()):
                self.assertTrue(
                    audiotools.pcm_cmp(track.to_pcm(), BLANK_PCM_Reader(10)))
            for audio_class in audiotools.AVAILABLE_TYPES:
                with tempfile.NamedTemporaryFile(
                        suffix="." + audio_class.SUFFIX) as outfile:
                    log = Log()
                    track2 = track.convert(outfile.name,
                                           audio_class,
                                           progress=log.update)
                    self.assertGreater(
                        len(log.results),
                        0,
                        "no logging converting %s to %s" %
                        (self.audio_class.NAME,
                         audio_class.NAME))
                    self.assertEqual(len({r[1] for r in log.results}), 1)
                    for x, y in zip(log.results[1:], log.results):
                        self.assertGreaterEqual((x[0] - y[0]), 0)

                    if (track.lossless() and track2.lossless()):
                        self.assertTrue(
                            audiotools.pcm_cmp(track.to_pcm(),
                                               track2.to_pcm()),
                            "PCM mismatch converting %s to %s" % (
                                self.audio_class.NAME,
                                audio_class.NAME))

    @FORMAT_AUDIOFILE
    def test_track_name(self):
        import sys

        if (self.audio_class is audiotools.AudioFile):
            return

        format_template = u"Fo\u00f3 %%(%(field)s)s"
        # first, test the many unicode string fields
        for field in audiotools.MetaData.FIELDS:
            if (field not in audiotools.MetaData.INTEGER_FIELDS):
                metadata = audiotools.MetaData()
                value = u"\u00dcnicode value \u2ec1"
                setattr(metadata, field, value)
                format_string = format_template % {u"field": field}
                track_name = self.audio_class.track_name(
                    file_path="track",
                    track_metadata=metadata,
                    format=(format_string if
                            (sys.version_info[0] >= 3) else
                            format_string.encode("UTF-8", "replace")))
                self.assertGreater(len(track_name), 0)
                if (sys.version_info[0] >= 3):
                    self.assertEqual(
                        track_name,
                        (format_template %
                         {u"field": u"foo"} %
                         {u"foo": value}))
                else:
                    self.assertEqual(
                        track_name,
                        (format_template %
                         {u"field": u"foo"} %
                         {u"foo": value}).encode("UTF-8", "replace"))

        # then, check integer fields
        format_template = (u"Fo\u00f3 %(album_number)d " +
                           u"%(track_number)2.2d %(album_track_number)s")

        # first, check integers pulled from track metadata
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
            for basepath in [u"track",
                             u"/foo/bar/track",
                             u"/f\u00f3o/bar/tr\u00e1ck"]:
                metadata = audiotools.MetaData(track_number=track_number,
                                               album_number=album_number)

                if (sys.version_info[0] < 3):
                    track_name = self.audio_class.track_name(
                        file_path=basepath.encode("UTF-8", "replace"),
                        track_metadata=metadata,
                        format=format_template.encode("UTF-8", "replace"))

                    self.assertEqual(
                        track_name.decode("UTF-8", "replace"),
                        (format_template % {u"album_number":
                                            album_number,
                                            u"track_number":
                                            track_number,
                                            u"album_track_number":
                                            album_track_number}))
                else:
                    track_name = self.audio_class.track_name(
                        file_path=basepath,
                        track_metadata=metadata,
                        format=format_template)

                    self.assertEqual(
                        track_name,
                        (format_template % {u"album_number":
                                            album_number,
                                            u"track_number":
                                            track_number,
                                            u"album_track_number":
                                            album_track_number}))

        # also, check track_total/album_total from metadata
        format_template = u"Fo\u00f3 %(track_total)d %(album_total)d"
        for track_total in [0, 1, 25, 99]:
            for album_total in [0, 1, 25, 99]:
                metadata = audiotools.MetaData(track_total=track_total,
                                               album_total=album_total)

                if (sys.version_info[0] < 3):
                    track_name = self.audio_class.track_name(
                        file_path="track",
                        track_metadata=metadata,
                        format=format_template.encode("UTF-8", "replace"))

                    self.assertEqual(
                        track_name.decode("UTF-8", "replace"),
                        (format_template % {u"track_total":
                                            track_total,
                                            u"album_total":
                                            album_total}))
                else:
                    track_name = self.audio_class.track_name(
                        file_path="track",
                        track_metadata=metadata,
                        format=format_template)

                    self.assertEqual(
                        track_name,
                        (format_template % {u"track_total":
                                            track_total,
                                            u"album_total":
                                            album_total}))

        # ensure %(basename)s is set properly
        format_template = u"Fo\u00f3 %(basename)s"
        for (path, base) in [(u"track", u"track"),
                             (u"/foo/bar/track", u"track"),
                             (u"/f\u00f3o/bar/tr\u00e1ck", u"tr\u00e1ck")]:
            for metadata in [None, audiotools.MetaData()]:
                if (sys.version_info[0] < 3):
                    track_name = self.audio_class.track_name(
                        file_path=path.encode("UTF-8", "replace"),
                        track_metadata=metadata,
                        format=format_template.encode("UTF-8", "replace"))

                    self.assertEqual(
                         track_name.decode("UTF-8", "replace"),
                         format_template % {u"basename": base})
                else:
                    track_name = self.audio_class.track_name(
                        file_path=path,
                        track_metadata=metadata,
                        format=format_template)

                    self.assertEqual(
                         track_name,
                         format_template % {u"basename": base})

        # ensure %(suffix)s is set properly
        format_template = u"Fo\u00f3 %(suffix)s"
        for path in [u"track",
                     u"/foo/bar/track",
                     u"/f\u00f3o/bar/tr\u00e1ck"]:
            for metadata in [None, audiotools.MetaData()]:
                if (sys.version_info[0] < 3):
                    track_name = self.audio_class.track_name(
                        file_path=path.encode("UTF-8", "replace"),
                        track_metadata=metadata,
                        format=format_template.encode("UTF-8", "replace"))

                    self.assertEqual(
                        track_name.decode("UTF-8", "replace"),
                        (format_template % {
                         u"suffix":
                         self.audio_class.SUFFIX.decode('ascii')}))
                else:
                    track_name = self.audio_class.track_name(
                        file_path=path,
                        track_metadata=metadata,
                        format=format_template)

                    self.assertEqual(
                        track_name,
                        (format_template % {
                         u"suffix":
                         self.audio_class.SUFFIX}))

        for metadata in [None, audiotools.MetaData()]:
            # unsupported template fields raise UnsupportedTracknameField
            self.assertRaises(audiotools.UnsupportedTracknameField,
                              self.audio_class.track_name,
                              "", metadata, "%(foo)s")

            # broken template fields raise InvalidFilenameFormat
            self.assertRaises(audiotools.InvalidFilenameFormat,
                              self.audio_class.track_name,
                              "", metadata, "%")

            self.assertRaises(audiotools.InvalidFilenameFormat,
                              self.audio_class.track_name,
                              "", metadata, "%{")

            self.assertRaises(audiotools.InvalidFilenameFormat,
                              self.audio_class.track_name,
                              "", metadata, "%[")

            self.assertRaises(audiotools.InvalidFilenameFormat,
                              self.audio_class.track_name,
                              "", metadata, "%(")

            self.assertRaises(audiotools.InvalidFilenameFormat,
                              self.audio_class.track_name,
                              "", metadata, "%(track_name")

            self.assertRaises(audiotools.InvalidFilenameFormat,
                              self.audio_class.track_name,
                              "", metadata, "%(track_name)")

    @FORMAT_AUDIOFILE
    def test_replay_gain(self):
        if (self.audio_class.supports_replay_gain()):
            # make test file
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            track = self.audio_class.from_pcm(
                temp_file.name,
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50,
                                           4410.0, 0.49, 1.0))

            # ensure get_replay_gain() returns None
            self.assertEqual(track.get_replay_gain(), None)

            # set dummy gain with set_replay_gain()
            dummy_gain = audiotools.ReplayGain(
                track_gain=0.25,
                track_peak=0.125,
                album_gain=0.50,
                album_peak=1.0)
            track.set_replay_gain(dummy_gain)

            # ensure get_replay_gain() returns dummy gain
            self.assertEqual(track.get_replay_gain(), dummy_gain)

            # delete gain with delete_replay_gain()
            track.delete_replay_gain()

            # ensure get_replay_gain() returns None again
            self.assertEqual(track.get_replay_gain(), None)

            # calling delete_replay_gain() again is okay
            track.delete_replay_gain()
            self.assertEqual(track.get_replay_gain(), None)

            # ensure setting replay_gain on unwritable file
            # raises IOError
            # FIXME

            # ensure getting replay_gain on unreadable file
            # raises IOError
            # FIXME

            temp_file.close()

    @FORMAT_AUDIOFILE
    def test_read_after_eof(self):
        if (self.audio_class is audiotools.AudioFile):
            return None

        # build basic file
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            # build a generic file of silence
            temp_track = self.audio_class.from_pcm(
                temp_file.name,
                EXACT_SILENCE_PCM_Reader(44100))

            # read all the PCM frames from the file
            pcmreader = temp_track.to_pcm()
            f = pcmreader.read(4000)
            while (len(f) > 0):
                f = pcmreader.read(4000)

            self.assertEqual(len(f), 0)

            # then ensure subsequent reads return blank FrameList objects
            # without triggering an error
            for i in range(10):
                f = pcmreader.read(4000)
                self.assertEqual(len(f), 0)

            pcmreader.close()

            self.assertRaises(ValueError,
                              pcmreader.read,
                              4000)
        finally:
            temp_file.close()

    @FORMAT_AUDIOFILE
    def test_invalid_from_pcm(self):
        if (self.audio_class is audiotools.AudioFile):
            return

        # test our ERROR_PCM_Reader works
        self.assertRaises(ValueError,
                          ERROR_PCM_Reader(ValueError("error"),
                                           failure_chance=1.0).read,
                          1)
        self.assertRaises(IOError,
                          ERROR_PCM_Reader(IOError("error"),
                                           failure_chance=1.0).read,
                          1)

        # ensure that our dummy file doesn't exist
        dummy_filename = "invalid." + self.audio_class.SUFFIX
        if (os.path.isfile(dummy_filename)):
            os.unlink(dummy_filename)

        # a decoder that raises IOError on to_pcm()
        # should trigger an EncodingError
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          dummy_filename,
                          ERROR_PCM_Reader(IOError("I/O Error")))

        # ensure invalid files aren't left lying around
        self.assertFalse(os.path.isfile(dummy_filename))

        # perform the same check with total_pcm_frames set
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          dummy_filename,
                          ERROR_PCM_Reader(IOError("I/O Error")),
                          total_pcm_frames=44100)

        self.assertFalse(os.path.isfile(dummy_filename))

        # a decoder that raises ValueError on to_pcm()
        # should trigger an EncodingError
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          dummy_filename,
                          ERROR_PCM_Reader(ValueError("Value Error")))

        # and ensure invalid files aren't left lying around
        self.assertFalse(os.path.isfile(dummy_filename))

        # perform the same check with total_pcm_frames set
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          dummy_filename,
                          ERROR_PCM_Reader(ValueError("Value Error")),
                          total_pcm_frames=44100)

        self.assertFalse(os.path.isfile(dummy_filename))

    @FORMAT_AUDIOFILE
    def test_total_pcm_frames(self):
        # all formats take a total_pcm_frames argument to from_pcm()
        # none are expected to do anything useful with it
        # but all should raise an exception if the actual amount
        # of input frames doesn't match

        if (self.audio_class is audiotools.AudioFile):
            return

        temp_name = "test." + self.audio_class.SUFFIX

        if (os.path.isfile(temp_name)):
            os.unlink(temp_name)

        # encode a file without the total_pcm_frames argument
        track = self.audio_class.from_pcm(
            temp_name,
            EXACT_SILENCE_PCM_Reader(123456))
        track.verify()

        if (track.lossless()):
            self.assertEqual(track.total_frames(), 123456)

        del(track)
        os.unlink(temp_name)

        # encode a file with the total_pcm_frames argument
        track = self.audio_class.from_pcm(
            temp_name,
            EXACT_SILENCE_PCM_Reader(234567),
            total_pcm_frames=234567)
        track.verify()

        if (track.lossless()):
            self.assertEqual(track.total_frames(), 234567)

        del(track)
        os.unlink(temp_name)

        # check too many total_pcm_frames
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          temp_name,
                          EXACT_SILENCE_PCM_Reader(345678),
                          total_pcm_frames=345679)

        self.assertFalse(os.path.isfile(temp_name))

        # check not enough total_pcm_frames
        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          temp_name,
                          EXACT_SILENCE_PCM_Reader(345678),
                          total_pcm_frames=345677)

        self.assertFalse(os.path.isfile(temp_name))

    @FORMAT_AUDIOFILE
    def test_seekable(self):
        from hashlib import md5
        from random import randrange

        if (self.audio_class is audiotools.AudioFile):
            return

        total_pcm_frames = 44100 * 60 * 3

        # create a slightly long file
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            temp_track = self.audio_class.from_pcm(
                temp_file.name,
                EXACT_SILENCE_PCM_Reader(total_pcm_frames),
                total_pcm_frames=total_pcm_frames)

            if (temp_track.seekable()):
                # get a PCMReader of our format
                with temp_track.to_pcm() as pcmreader:
                    # hash its data when read to end
                    raw_data = md5()
                    frame = pcmreader.read(4096)
                    while (len(frame) > 0):
                        raw_data.update(frame.to_bytes(False, True))
                        frame = pcmreader.read(4096)

                    # seeking to negative values should raise ValueError
                    self.assertRaises(ValueError,
                                      pcmreader.seek,
                                      -1)

                    # seeking to offset 0 should always work
                    # (since it's a very basic rewind)
                    self.assertEqual(pcmreader.seek(0), 0)

                    # hash its data again and ensure a match
                    rewound_raw_data = md5()
                    frame = pcmreader.read(4096)
                    while (len(frame) > 0):
                        rewound_raw_data.update(frame.to_bytes(False, True))
                        frame = pcmreader.read(4096)
                    self.assertEqual(raw_data.digest(),
                                     rewound_raw_data.digest())

                    # try a bunch of random seeks
                    # and ensure the offset is always <= the seeked value
                    for i in range(10):
                        position = randrange(0, total_pcm_frames)
                        actual_position = pcmreader.seek(position)
                        self.assertLessEqual(actual_position, position)

                        # if lossless, ensure seeking works as advertised
                        # by comparing stream to file window
                        actual_remaining_frames = 0
                        desired_remaining_frames = (total_pcm_frames -
                                                    actual_position)
                        frame = pcmreader.read(4096)
                        while (len(frame) > 0):
                            actual_remaining_frames += frame.frames
                            frame = pcmreader.read(4096)

                        self.assertEqual(actual_remaining_frames,
                                         desired_remaining_frames)

                    # seeking to some huge value should work
                    # even if its position doesn't get to the end of the file
                    for value in [2 ** 31, 2 ** 34, 2 ** 38]:
                        seeked = pcmreader.seek(value)
                        self.assertLessEqual(seeked, value,
                                             "%s > %s" % (seeked, value))

                    # a PCMReader that's closed should raise ValueError
                    # whenever seek is called
                    pcmreader.close()
                    self.assertRaises(ValueError,
                                      pcmreader.seek,
                                      0)
                    for i in range(10):
                        self.assertRaises(ValueError,
                                          pcmreader.seek,
                                          randrange(0, total_pcm_frames))
            else:
                # ensure PCMReader has no .seek() method
                # or that method always returns to the start of the file
                with temp_track.to_pcm() as pcmreader:
                    if (hasattr(pcmreader, "seek") and
                        callable(pcmreader.seek)):
                        # try a bunch of random seeks
                        # and ensure the offset is always 0
                        for i in range(10):
                            position = randrange(0, total_pcm_frames)
                            self.assertEqual(pcmreader.seek(position), 0)

                        # seeking to some huge value should work
                        # even if its position doesn't get
                        # to the end of the file
                        for value in [2 ** 31, 2 ** 34, 2 ** 38]:
                            self.assertEqual(pcmreader.seek(value), 0)

                        # a PCMReader that's closed should raise ValueError
                        # whenever seek is called
                        pcmreader.close()
                        self.assertRaises(ValueError,
                                          pcmreader.seek,
                                          0)
                        for i in range(10):
                            self.assertRaises(ValueError,
                                              pcmreader.seek,
                                              randrange(0, total_pcm_frames))
        finally:
            temp_file.close()

    # FIXME
    @FORMAT_AUDIOFILE_PLACEHOLDER
    def test_cuesheet(self):
        self.assert_(False)

    # FIXME
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
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=channels,
                                                channel_mask=0))
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
                cm = audiotools.ChannelMask.from_fields(
                    **dict([(f, True) for f in mask]))
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=len(cm),
                                                channel_mask=int(cm)))
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
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1, sample_rate=rate))
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
            for total_pcm_frames in [None, 44100]:
                for compression in (None,) + self.audio_class.COMPRESSION_MODES:
                    # test silence
                    reader = MD5_Reader(BLANK_PCM_Reader(1))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)
                    checksum = md5()
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       checksum.update)
                    self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                    # test random noise
                    reader = MD5_Reader(RANDOM_PCM_Reader(1))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)
                    checksum = md5()
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       checksum.update)
                    self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                    # test randomly-sized chunks of silence
                    reader = MD5_Reader(Variable_Reader(BLANK_PCM_Reader(10)))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=(total_pcm_frames * 10)
                            if (total_pcm_frames is not None) else None)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=(total_pcm_frames * 10)
                            if (total_pcm_frames is not None) else None)
                    checksum = md5()
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       checksum.update)
                    self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                    # test randomly-sized chunks of random noise
                    reader = MD5_Reader(Variable_Reader(RANDOM_PCM_Reader(10)))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=(total_pcm_frames * 10)
                            if (total_pcm_frames is not None) else None)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=(total_pcm_frames * 10)
                            if (total_pcm_frames is not None) else None)
                    checksum = md5()
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       checksum.update)
                    self.assertEqual(reader.hexdigest(), checksum.hexdigest())

                    # test PCMReaders that trigger a DecodingError
                    self.assertRaises(
                        ValueError,
                        ERROR_PCM_Reader(ValueError("error"),
                                         failure_chance=1.0).read,
                        1)
                    self.assertRaises(
                        IOError,
                        ERROR_PCM_Reader(IOError("error"),
                                         failure_chance=1.0).read,
                        1)
                    self.assertRaises(
                        audiotools.EncodingError,
                        self.audio_class.from_pcm,
                        os.path.join(temp_dir, "invalid" + self.suffix),
                        ERROR_PCM_Reader(IOError("I/O Error")))

                    self.assertEqual(
                        os.path.isfile(
                            os.path.join(temp_dir,
                                         "invalid" + self.suffix)),
                        False)

                    self.assertRaises(audiotools.EncodingError,
                                      self.audio_class.from_pcm,
                                      os.path.join(temp_dir,
                                                   "invalid" + self.suffix),
                                      ERROR_PCM_Reader(IOError("I/O Error")))

                    self.assertEqual(
                        os.path.isfile(
                            os.path.join(temp_dir,
                                         "invalid" + self.suffix)),
                        False)

                    # test unwritable output file
                    self.assertRaises(audiotools.EncodingError,
                                      self.audio_class.from_pcm,
                                      "/dev/null/foo.%s" % (self.suffix),
                                      BLANK_PCM_Reader(1))

                    # test without suffix
                    reader = MD5_Reader(BLANK_PCM_Reader(1))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp2.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp2.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)
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

        # check various round-trip options
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
                        self.assertTrue(
                            audiotools.pcm_cmp(
                                track.to_pcm(), track2.to_pcm()),
                                "error round-tripping %s to %s" %
                                (self.audio_class.NAME,
                                 audio_class.NAME))
                    else:
                        pcm = track2.to_pcm()
                        counter = FrameCounter(pcm.channels,
                                               pcm.bits_per_sample,
                                               pcm.sample_rate)

                        audiotools.transfer_framelist_data(
                            pcm, counter.update)

                        self.assertEqual(
                            int(counter), 10,
                            "mismatch encoding %s (%s/%d != %s)" %
                            (audio_class.NAME,
                             counter,
                             int(counter),
                             10))

                    self.assertRaises(audiotools.EncodingError,
                                      track.convert,
                                      "/dev/null/foo.%s" %
                                      (audio_class.SUFFIX),
                                      audio_class)

                    for compression in audio_class.COMPRESSION_MODES:
                        track2 = track.convert(temp2.name,
                                               audio_class,
                                               compression)
                        if (track2.lossless()):
                            self.assertTrue(
                                audiotools.pcm_cmp(
                                    track.to_pcm(), track2.to_pcm()),
                                "error round-tripping %s to %s at %s" %
                                (self.audio_class.NAME,
                                 audio_class.NAME,
                                 compression))
                        else:
                            pcm = track2.to_pcm()
                            counter = FrameCounter(
                                pcm.channels,
                                pcm.bits_per_sample,
                                pcm.sample_rate)
                            audiotools.transfer_framelist_data(
                                pcm, counter.update)
                            self.assertEqual(
                                int(counter), 10,
                                ("mismatch encoding %s " +
                                 "at quality %s (%s != %s)") %
                                (audio_class.NAME, compression,
                                 counter, 10))

                        # check some obvious failures
                        self.assertRaises(audiotools.EncodingError,
                                          track.convert,
                                          "/dev/null/foo.%s" %
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
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1, bits_per_sample=bps))
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
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=channels,
                                                channel_mask=0))
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
            track = self.audio_class.from_pcm(
                temp.name, BLANK_PCM_Reader(1,
                                            channels=len(cm),
                                            channel_mask=int(cm)))
            self.assertEqual(track.channels(), len(cm))
            self.assertEqual(track.channel_mask(), cm)
            track = audiotools.open(temp.name)
            self.assertEqual(track.channels(), len(cm))
            self.assertEqual(track.channel_mask(), cm)
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
            for total_pcm_frames in [None, 44100 * 5]:
                for compression in (None,) + self.audio_class.COMPRESSION_MODES:
                    # test silence
                    reader = BLANK_PCM_Reader(5)
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)
                    counter = FrameCounter(2, 16, 44100)
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       counter.update)
                    self.assertEqual(int(counter), 5,
                                     "mismatch encoding %s at quality %s" %
                                     (self.audio_class.NAME,
                                      compression))

                    # test random noise
                    reader = RANDOM_PCM_Reader(5)
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)
                    counter = FrameCounter(2, 16, 44100)
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       counter.update)
                    self.assertEqual(int(counter), 5,
                                     "mismatch encoding %s at quality %s" %
                                     (self.audio_class.NAME,
                                      compression))

                    # test randomly-sized chunks of silence
                    reader = Variable_Reader(BLANK_PCM_Reader(5))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)

                    counter = FrameCounter(2, 16, 44100)
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       counter.update)
                    self.assertEqual(int(counter), 5,
                                     "mismatch encoding %s at quality %s" %
                                     (self.audio_class.NAME,
                                      compression))

                    # test randomly-sized chunks of random noise
                    reader = Variable_Reader(RANDOM_PCM_Reader(5))
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)

                    counter = FrameCounter(2, 16, 44100)
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       counter.update)
                    self.assertEqual(int(counter), 5,
                                     "mismatch encoding %s at quality %s" %
                                     (self.audio_class.NAME,
                                      compression))

                    # test PCMReaders that trigger a DecodingError
                    self.assertRaises(
                        ValueError,
                        ERROR_PCM_Reader(ValueError("error"),
                                         failure_chance=1.0).read,
                        1)
                    self.assertRaises(
                        IOError,
                        ERROR_PCM_Reader(IOError("error"),
                                         failure_chance=1.0).read,
                        1)
                    self.assertRaises(audiotools.EncodingError,
                                      self.audio_class.from_pcm,
                                      os.path.join(temp_dir,
                                                   "invalid" + self.suffix),
                                      ERROR_PCM_Reader(IOError("I/O Error")))

                    self.assertEqual(
                        os.path.isfile(
                            os.path.join(temp_dir,
                                         "invalid" + self.suffix)),
                        False)

                    self.assertRaises(audiotools.EncodingError,
                                      self.audio_class.from_pcm,
                                      os.path.join(temp_dir,
                                                   "invalid" + self.suffix),
                                      ERROR_PCM_Reader(IOError("I/O Error")))

                    self.assertEqual(
                        os.path.isfile(
                            os.path.join(temp_dir,
                                         "invalid" + self.suffix)),
                        False)

                    # test unwritable output file
                    self.assertRaises(audiotools.EncodingError,
                                      self.audio_class.from_pcm,
                                      "/dev/null/foo.%s" % (self.suffix),
                                      BLANK_PCM_Reader(1))

                    # test without suffix
                    reader = BLANK_PCM_Reader(5)
                    if (compression is None):
                        track = self.audio_class.from_pcm(
                            temp2.name,
                            reader,
                            total_pcm_frames=total_pcm_frames)
                    else:
                        track = self.audio_class.from_pcm(
                            temp2.name,
                            reader,
                            compression,
                            total_pcm_frames=total_pcm_frames)

                    counter = FrameCounter(2, 16, 44100)
                    audiotools.transfer_framelist_data(track.to_pcm(),
                                                       counter.update)
                    self.assertEqual(int(counter), 5,
                                     "mismatch encoding %s at quality %s" %
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

        # check various round-trip options
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)

        track = self.audio_class.from_pcm(
            temp.name,
            test_streams.Sine16_Stereo(220500, 44100,
                                       8820.0, 0.70, 4410.0, 0.29, 1.0))
        for audio_class in audiotools.AVAILABLE_TYPES:
            temp2 = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track2 = track.convert(temp2.name, audio_class)

            counter = FrameCounter(2, 16, 44100)
            audiotools.transfer_framelist_data(track2.to_pcm(),
                                               counter.update)
            self.assertEqual(
                int(counter), 5,
                "mismatch encoding %s" %
                (self.audio_class.NAME))

            self.assertRaises(audiotools.EncodingError,
                              track.convert,
                              "/dev/null/foo.%s" %
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
                    "mismatch encoding %s at quality %s" %
                    (self.audio_class.NAME,
                     compression))

                # check some obvious failures
                self.assertRaises(audiotools.EncodingError,
                                  track.convert,
                                  "/dev/null/foo.%s" %
                                  (audio_class.SUFFIX),
                                  audio_class,
                                  compression)

            temp2.close()

        temp.close()


class TestForeignWaveChunks:
    @FORMAT_LOSSLESS
    def test_convert_wave_chunks(self):
        import filecmp

        self.assert_(issubclass(self.audio_class,
                                audiotools.WaveContainer))

        # several even-sized chunks
        chunks1 = (("x\x9c\x0b\xf2ts\xdbQ\xc9\xcb\x10\xee\x18" +
                    "\xe6\x9a\x96[\xa2 \xc0\xc0\xc0\xc0\xc8\xc0" +
                    "\xc4\xe0\xb2\x86\x81A`#\x13\x03\x0b\x83" +
                    "\x00CZ~~\x15\x07P\xbc$\xb5\xb8\xa4$\xb5" +
                    "\xa2$)\xb1\xa8\n\xa4\xae8?757\xbf(\x15!^U" +
                    "\x05\xd40\nF\xc1(\x18\xc1 %\xb1$1\xa0\x94" +
                    "\x97\x01\x00`\xb0\x18\xf7").decode('zlib'),
                   (220500, 44100, 2, 16, 0x3),
                   "spam\x0c\x00\x00\x00anotherchunk")

        # several odd-sized chunks
        chunks2 = (("x\x9c\x0b\xf2ts\xcbc``\x08w\x0csM\xcb\xcf\xaf" +
                    "\xe2b@\x06i\xb9%\n\x02@\x9a\x11\x08]\xd60" +
                    "\x801#\x03\x07CRbQ\x157H\x1c\x01\x18R\x12K\x12" +
                    "\xf9\x81b\x00\x19\xdd\x0ba").decode('zlib'),
                   (15, 44100, 1, 8, 0x4),
                   "\x00barz\x0b\x00\x00\x00\x01\x01\x01\x01" +
                   "\x01\x01\x01\x01\x01\x01\x01\x00")

        for (header,
             (total_frames,
              sample_rate,
              channels,
              bits_per_sample,
              channel_mask), footer) in [chunks1, chunks2]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            try:
                # build our audio file from the from_pcm() interface
                track = self.audio_class.from_pcm(
                    temp1.name,
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=total_frames,
                        sample_rate=sample_rate,
                        channels=channels,
                        bits_per_sample=bits_per_sample,
                        channel_mask=channel_mask))

                # check has_foreign_wave_chunks
                self.assertEqual(track.has_foreign_wave_chunks(), False)
            finally:
                temp1.close()

        for (header,
             (total_frames,
              sample_rate,
              channels,
              bits_per_sample,
              channel_mask), footer) in [chunks1, chunks2]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            try:
                # build our audio file using the from_wave() interface
                track = self.audio_class.from_wave(
                    temp1.name,
                    header,
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=total_frames,
                        sample_rate=sample_rate,
                        channels=channels,
                        bits_per_sample=bits_per_sample,
                        channel_mask=channel_mask),
                    footer)

                # check has_foreign_wave_chunks
                self.assertEqual(track.has_foreign_wave_chunks(), True)

                # ensure wave_header_footer returns same header and footer
                (track_header,
                 track_footer) = track.wave_header_footer()
                self.assertEqual(header, track_header)
                self.assertEqual(footer, track_footer)

                # convert our file to every other WaveContainer format
                # (including our own)
                for new_class in audiotools.AVAILABLE_TYPES:
                    if (issubclass(new_class, audiotools.WaveContainer)):
                        temp2 = tempfile.NamedTemporaryFile(
                            suffix="." + new_class.SUFFIX)
                        log = Log()
                        try:
                            track2 = track.convert(temp2.name,
                                                   new_class,
                                                   progress=log.update)

                            # ensure the progress function
                            # gets called during conversion
                            self.assert_(
                                len(log.results) > 0,
                                "no logging converting %s to %s" %
                                (self.audio_class.NAME,
                                 new_class.NAME))

                            self.assert_(
                                len(set([r[1] for r in log.results])) == 1)
                            for x, y in zip(log.results[1:], log.results):
                                self.assert_((x[0] - y[0]) >= 0)

                            # ensure newly converted file
                            # matches has_foreign_wave_chunks
                            self.assertEqual(
                                track2.has_foreign_wave_chunks(), True)

                            # ensure newly converted file
                            # has same header and footer
                            (track2_header,
                             track2_footer) = track2.wave_header_footer()
                            self.assertEqual(header, track2_header)
                            self.assertEqual(footer, track2_footer)

                            # ensure newly converted file has same PCM data
                            self.assertTrue(
                                audiotools.pcm_cmp(
                                    track.to_pcm(), track2.to_pcm()))
                        finally:
                            temp2.close()
            finally:
                temp1.close()

        if (os.path.isfile("bad.wav")):
            os.unlink("bad.wav")

        for (header, footer) in [
            # wave header without "RIFF<size>WAVE raises an error
            ("", ""),
            ("FOOZ\x00\x00\x00\x00BARZ", ""),

            # invalid total size raises an error
            ("RIFFZ\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00" +
             "\x10\x00data2\x00\x00\x00", ""),

            # invalid data size raises an error
            ("RIFFV\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00" +
             "\x10\x00data6\x00\x00\x00", ""),

            # invalid chunk IDs in header raise an error
            ("RIFFb\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chn\x00\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data2\x00\x00\x00", ""),

            # mulitple fmt chunks raise an error
            ("RIFFn\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00" +
             "\x10\x00" +
             "fmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00" +
             "\x10\x00" +
             "data2\x00\x00\x00", ""),

            # data chunk before fmt chunk raises an error
            ("RIFFJ\x00\x00\x00WAVE" +
             "chnk\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data2\x00\x00\x00", ""),

            # bytes after data chunk raises an error
            ("RIFFb\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chnk\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data3\x00\x00\x00\x01", ""),

            # truncated chunks in header raise an error
            ("RIFFb\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chnk\x04\x00\x00\x00\x01\x02\x03", ""),

            # fmt chunk in footer raises an error
            ("RIFFz\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chnk\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data2\x00\x00\x00",
             "fmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00"),

            # data chunk in footer raises an error
            ("RIFFn\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chnk\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data2\x00\x00\x00",
             "data\x04\x00\x00\x00\x01\x02\x03\x04"),

            # invalid chunk IDs in footer raise an error
            ("RIFFn\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chnk\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data2\x00\x00\x00",
             "chn\x00\x04\x00\x00\x00\x01\x02\x03\x04"),

            # truncated chunks in footer raise an error
            ("RIFFn\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01" +
             "\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00" +
             "chnk\x04\x00\x00\x00\x01\x02\x03\x04" +
             "data2\x00\x00\x00",
             "chnk\x04\x00\x00\x00\x01\x02\x03")]:
            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_wave,
                              "bad.wav",
                              header,
                              EXACT_BLANK_PCM_Reader(25,
                                                     44100,
                                                     1,
                                                     16,
                                                     0x4),
                              footer)
            self.assertEqual(os.path.isfile("bad.wav"), False)


class TestForeignAiffChunks:
    @FORMAT_LOSSLESS
    def test_convert_aiff_chunks(self):
        import filecmp

        self.assert_(issubclass(self.audio_class,
                                audiotools.AiffContainer))

        # several even-sized chunks
        chunks1 = (("x\x9cs\xf3\x0f\xf2e\xe0\xad<\xe4\xe8\xe9\xe6\xe6" +
                    "\xec\xef\xeb\xcb\xc0\xc0 \xc4\xc0\xc4\xc0\x1c\x1b" +
                    "\xc2 \xe0\xc0\xb7\xc6\x85\x01\x0c\xdc\xfc\xfd\xa3" +
                    "\x80\x14GIjqIIjE\x89\x93c\x10\x88/P\x9c\x9f\x9b" +
                    "\x9a\x9b_\x94\x8a\x10\x8f\x02\x8a\xb30\x8c" +
                    "\x82Q0\nF.\x08\x0e\xf6sa\xe0-\x8d\x80\xf1\x01" +
                    "\xcf\x8c\x17\x18").decode('zlib'),
                   (220500, 44100, 2, 16, 0x3),
                   "SPAM\x00\x00\x00\x0canotherchunk")

        # several odd-sized chunks
        chunks2 = (("x\x9cs\xf3\x0f\xf2e``\xa8p\xf4tss\xf3\xf7\x8f" +
                    "\x02\xb2\xb9\x18\xe0\xc0\xd9\xdf\x17$+\xc4\xc0" +
                    "\x08$\xf9\x198\x1c\xf8\xd6\xb8@d\x9c\x1c\x83@j" +
                    "\xb9\x19\x11\x80!8\xd8\x0f$+\x0e\xd3\r" +
                    "\x00\x16\xa5\t3").decode('zlib'),
                   (15, 44100, 1, 8, 0x4),
                   "\x00BAZZ\x00\x00\x00\x0b\x02\x02\x02\x02" +
                   "\x02\x02\x02\x02\x02\x02\x02\x00")

        for (header,
             (total_frames,
              sample_rate,
              channels,
              bits_per_sample,
              channel_mask), footer) in [chunks1, chunks2]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            try:
                # build our audio file from the from_pcm() interface
                track = self.audio_class.from_pcm(
                    temp1.name,
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=total_frames,
                        sample_rate=sample_rate,
                        channels=channels,
                        bits_per_sample=bits_per_sample,
                        channel_mask=channel_mask))

                # check has_foreign_aiff_chunks()
                self.assertEqual(track.has_foreign_aiff_chunks(), False)
            finally:
                temp1.close()

        for (header,
             (total_frames,
              sample_rate,
              channels,
              bits_per_sample,
              channel_mask), footer) in [chunks1, chunks2]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            try:
                # build our audio file using from_aiff() interface
                track = self.audio_class.from_aiff(
                    temp1.name,
                    header,
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=total_frames,
                        sample_rate=sample_rate,
                        channels=channels,
                        bits_per_sample=bits_per_sample,
                        channel_mask=channel_mask),
                    footer)

                # check has_foreign_aiff_chunks()
                self.assertEqual(track.has_foreign_aiff_chunks(), True)

                # ensure aiff_header_footer returns same header and footer
                (track_header,
                 track_footer) = track.aiff_header_footer()
                self.assertEqual(header, track_header)
                self.assertEqual(footer, track_footer)

                # convert our file to every other AiffContainer format
                # (including our own)
                for new_class in audiotools.AVAILABLE_TYPES:
                    if (issubclass(new_class, audiotools.AiffContainer)):
                        temp2 = tempfile.NamedTemporaryFile(
                            suffix="." + new_class.SUFFIX)
                        log = Log()
                        try:
                            track2 = track.convert(temp2.name,
                                                   new_class,
                                                   progress=log.update)

                            # ensure the progress function
                            # gets called during conversion
                            self.assert_(
                                len(log.results) > 0,
                                "no logging converting %s to %s" %
                                (self.audio_class.NAME,
                                 new_class.NAME))

                            self.assert_(
                                len(set([r[1] for r in log.results])) == 1)
                            for x, y in zip(log.results[1:], log.results):
                                self.assert_((x[0] - y[0]) >= 0)

                            # ensure newly converted file
                            # matches has_foreign_wave_chunks
                            self.assertEqual(
                                track2.has_foreign_aiff_chunks(), True)

                            # ensure newly converted file
                            # has same header and footer
                            (track2_header,
                             track2_footer) = track2.aiff_header_footer()
                            self.assertEqual(header, track2_header)
                            self.assertEqual(footer, track2_footer)

                            # ensure newly converted file has same PCM data
                            self.assertTrue(
                                audiotools.pcm_cmp(track.to_pcm(),
                                                   track2.to_pcm()))
                        finally:
                            temp2.close()
            finally:
                temp1.close()

        if (os.path.isfile("bad.aiff")):
            os.unlink("bad.aiff")

        for (header, footer) in [
            # aiff header without "FORM<size>AIFF raises an error
            ("", ""),
            ("FOOZ\x00\x00\x00\x00BARZ", ""),

            # invalid total size raises an error
            ("FORM\x00\x00\x00tAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # invalid SSND size raises an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00<\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # invalid chunk IDs in header raise an error
            ("FORM\x00\x00\x00~AIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "CHN\x00\x00\x00\x00\x04\x01\x02\x03\x04" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # mulitple COMM chunks raise an error
            ("FORM\x00\x00\x00\x8cAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # SSND chunk before COMM chunk raises an error
            ("FORM\x00\x00\x00XAIFF" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # bytes missing from SSNK chunk raises an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00<\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # bytes after SSND chunk raises an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00<\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # truncated chunks in header raise an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # COMM chunk in footer raises an error
            ("FORM\x00\x00\x00\x8cAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # SSND chunk in footer raises an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00"),

            # invalid chunk IDs in footer raise an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3\00\x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00\x00"),

            # truncated chunks in footer raise an error
            ("FORM\x00\x00\x00rAIFF" +
             "COMM\x00\x00\x00\x12\x00\x01\x00\x00\x00\x19\x00" +
             "\x10@\x0e\xacD\x00\x00\x00\x00\x00\x00" +
             "SSND\x00\x00\x00:\x00\x00\x00\x00\x00\x00\x00\x00",
             "ID3 \x00\x00\x00\nID3\x02\x00\x00\x00\x00\x00")]:
            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_aiff,
                              "bad.aiff",
                              header,
                              EXACT_BLANK_PCM_Reader(25,
                                                     44100,
                                                     1,
                                                     16,
                                                     0x4),
                              footer)
            self.assertEqual(os.path.isfile("bad.aiff"), False)


class AiffFileTest(TestForeignAiffChunks, LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.AiffAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AIFF
    def test_ieee_extended(self):
        from audiotools.bitstream import BitstreamReader, BitstreamRecorder
        import audiotools.aiff

        for i in range(0, 192000 + 1):
            w = BitstreamRecorder(0)
            audiotools.aiff.build_ieee_extended(w, float(i))
            s = BytesIO(w.data())
            self.assertEqual(w.data(), s.getvalue())
            self.assertEqual(i, audiotools.aiff.parse_ieee_extended(
                BitstreamReader(s, False)))

    @FORMAT_AIFF
    def test_overlong_file(self):
        # trying to generate too large of a file
        # should throw an exception right away if total_pcm_frames known
        # instead of building it first

        self.assertEqual(os.path.isfile("invalid.aiff"), False)

        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          "invalid.aiff",
                          EXACT_SILENCE_PCM_Reader(
                              pcm_frames=715827883,
                              sample_rate=44100,
                              channels=2,
                              bits_per_sample=24),
                          total_pcm_frames=715827883)

        self.assertEqual(os.path.isfile("invalid.aiff"), False)

    @FORMAT_AIFF
    def test_verify(self):
        import audiotools.aiff

        # test truncated file
        for aiff_file in ["aiff-8bit.aiff",
                          "aiff-1ch.aiff",
                          "aiff-2ch.aiff",
                          "aiff-6ch.aiff"]:
            f = open(aiff_file, 'rb')
            aiff_data = f.read()
            f.close()

            temp = tempfile.NamedTemporaryFile(suffix=".aiff")

            try:
                # first, check that a truncated comm chunk raises an exception
                # at init-time
                for i in range(0, 0x25):
                    temp.seek(0, 0)
                    temp.write(aiff_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)

                    self.assertRaises(audiotools.InvalidFile,
                                      audiotools.AiffAudio,
                                      temp.name)

                # then, check that a truncated ssnd chunk raises an exception
                # at read-time
                for i in range(0x37, len(aiff_data)):
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

        # test non-ASCII chunk ID
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

        # test no SSND chunk
        aiff = audiotools.open("aiff-nossnd.aiff")
        self.assertRaises(audiotools.InvalidFile, aiff.verify)

        # test convert errors
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

        # test multiple COMM chunks found
        # test multiple SSND chunks found
        # test SSND chunk before COMM chunk
        # test no SSND chunk
        # test no COMM chunk
        for chunks in [[COMM, COMM, SSND],
                       [COMM, SSND, SSND],
                       [SSND, COMM],
                       [SSND],
                       [COMM]]:
            temp = tempfile.NamedTemporaryFile(suffix=".aiff")
            try:
                audiotools.AiffAudio.aiff_from_chunks(temp, chunks)
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

        # test multiple COMM chunks
        # test multiple SSND chunks
        # test data chunk before fmt chunk
        fixed = tempfile.NamedTemporaryFile(suffix=".aiff")
        try:
            for chunks in [[COMM, COMM, SSND],
                           [COMM, SSND, COMM],
                           [COMM, SSND, SSND],
                           [SSND, COMM],
                           [SSND, COMM, COMM]]:
                temp = tempfile.NamedTemporaryFile(suffix=".aiff")
                audiotools.AiffAudio.aiff_from_chunks(temp, chunks)
                temp.flush()
                fixes = audiotools.open(temp.name).clean(fixed.name)
                temp.close()
                aiff = audiotools.open(fixed.name)
                chunks = list(aiff.chunks())
                self.assertEquals([c.id for c in chunks],
                                  [c.id for c in [COMM, SSND]])
                self.assertEquals([c.__size__ for c in chunks],
                                  [c.__size__ for c in [COMM, SSND]])
                self.assertEquals([c.__data__ for c in chunks],
                                  [c.__data__ for c in [COMM, SSND]])
        finally:
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
        # check missing file
        self.assertRaises(audiotools.m4a.InvalidALAC,
                          audiotools.ALACAudio,
                          "/dev/null/foo")

        # check invalid file
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

        # check some decoder errors,
        # mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(TypeError, self.decoder, None)

    @FORMAT_ALAC
    def test_bits_per_sample(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for bps in (16, 24):
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1, bits_per_sample=bps))
                self.assertEqual(track.bits_per_sample(), bps)
                track2 = audiotools.open(temp.name)
                self.assertEqual(track2.bits_per_sample(), bps)
        finally:
            temp.close()

    @FORMAT_ALAC
    def test_channel_mask(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for mask in [["front_center"],
                         ["front_left",
                          "front_right"]]:
                cm = audiotools.ChannelMask.from_fields(
                    **dict([(f, True) for f in mask]))
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=len(cm),
                                                channel_mask=int(cm)))
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
                cm = audiotools.ChannelMask.from_fields(
                    **dict([(f, True) for f in mask]))
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=len(cm),
                                                channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), cm)

            # ensure valid channel counts with invalid channel masks
            # raise an exception
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

        # test truncating the mdat atom triggers IOError
        temp = tempfile.NamedTemporaryFile(suffix='.m4a')
        try:
            for i in range(0x16CD, len(alac_data)):
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

        # test a truncated file's convert() method raises EncodingError
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
        # ensure that the 'too' meta atom isn't modified by setting metadata
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

    def __test_reader__(self, pcmreader, total_pcm_frames, block_size=4096):
        if (not audiotools.BIN.can_execute(audiotools.BIN["alac"])):
            self.assert_(False,
                         "reference ALAC binary alac(1) required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".alac")
        self.audio_class.from_pcm(temp_file.name,
                                  pcmreader,
                                  block_size=block_size)

        alac = audiotools.open(temp_file.name)
        self.assert_(alac.total_frames() > 0)

        # first, ensure the ALAC-encoded file
        # has the same MD5 signature as pcmreader once decoded
        md5sum_decoder = md5()
        with alac.to_pcm() as d:
            f = d.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum_decoder.update(f.to_bytes(False, True))
                f = d.read(audiotools.FRAMELIST_SIZE)
        self.assertEqual(md5sum_decoder.digest(), pcmreader.digest())

        # then compare our .to_pcm() output
        # with that of the ALAC reference decoder
        reference = subprocess.Popen([audiotools.BIN["alac"],
                                      "-r", temp_file.name],
                                     stdout=subprocess.PIPE)
        md5sum_reference = md5()
        audiotools.transfer_data(reference.stdout.read,
                                 md5sum_reference.update)
        self.assertEqual(reference.wait(), 0)
        self.assertEqual(md5sum_reference.digest(), pcmreader.digest(),
                         "mismatch decoding %s from reference (%s != %s)" %
                         (repr(pcmreader),
                          md5sum_reference.hexdigest(),
                          pcmreader.hexdigest()))

        # then, perform test again using from_pcm()
        # with total_pcm_frames indicated
        pcmreader.reset()

        self.audio_class.from_pcm(temp_file.name,
                                  pcmreader,
                                  total_pcm_frames=total_pcm_frames,
                                  block_size=block_size)

        alac = audiotools.open(temp_file.name)
        self.assert_(alac.total_frames() > 0)

        # ensure the ALAC-encoded file
        # has the same MD5 signature as pcmreader once decoded
        md5sum_decoder = md5()
        with alac.to_pcm() as d:
            f = d.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum_decoder.update(f.to_bytes(False, True))
                f = d.read(audiotools.FRAMELIST_SIZE)
        self.assertEqual(md5sum_decoder.digest(), pcmreader.digest())

        # then compare our .to_pcm() output
        # with that of the ALAC reference decoder
        reference = subprocess.Popen([audiotools.BIN["alac"],
                                      "-r", temp_file.name],
                                     stdout=subprocess.PIPE)
        md5sum_reference = md5()
        audiotools.transfer_data(reference.stdout.read,
                                 md5sum_reference.update)
        self.assertEqual(reference.wait(), 0)
        self.assertEqual(md5sum_reference.digest(), pcmreader.digest(),
                         "mismatch decoding %s from reference (%s != %s)" %
                         (repr(pcmreader),
                          md5sum_reference.hexdigest(),
                          pcmreader.hexdigest()))

    def __test_reader_nonalac__(self, pcmreader, total_pcm_frames,
                                block_size=4096):
        # This is for multichannel testing
        # since alac(1) doesn't handle them yet.
        # Unfortunately, it relies only on our built-in decoder
        # to test correctness.

        temp_file = tempfile.NamedTemporaryFile(suffix=".alac")
        self.audio_class.from_pcm(temp_file.name,
                                  pcmreader,
                                  block_size=block_size)

        alac = audiotools.open(temp_file.name)
        self.assert_(alac.total_frames() > 0)

        # first, ensure the ALAC-encoded file
        # has the same MD5 signature as pcmreader once decoded
        md5sum_decoder = md5()
        with alac.to_pcm() as d:
            f = d.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum_decoder.update(f.to_bytes(False, True))
                f = d.read(audiotools.FRAMELIST_SIZE)
        self.assertEqual(md5sum_decoder.digest(), pcmreader.digest())

        # perform test again with total_pcm_frames indicated
        pcmreader.reset()
        self.audio_class.from_pcm(temp_file.name,
                                  pcmreader,
                                  total_pcm_frames=total_pcm_frames,
                                  block_size=block_size)

        alac = audiotools.open(temp_file.name)
        self.assert_(alac.total_frames() > 0)

        # first, ensure the ALAC-encoded file
        # has the same MD5 signature as pcmreader once decoded
        md5sum_decoder = md5()
        with alac.to_pcm() as d:
            f = d.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum_decoder.update(f.to_bytes(False, True))
                f = d.read(audiotools.FRAMELIST_SIZE)
        self.assertEqual(md5sum_decoder.digest(), pcmreader.digest())

    def __stream_variations__(self):
        for stream in [
            test_streams.Silence16_Mono(200000, 44100),
            test_streams.Silence16_Mono(200000, 96000),
            test_streams.Silence16_Stereo(200000, 44100),
            test_streams.Silence16_Stereo(200000, 96000),
            test_streams.Silence24_Mono(200000, 44100),
            test_streams.Silence24_Mono(200000, 96000),
            test_streams.Silence24_Stereo(200000, 44100),
            test_streams.Silence24_Stereo(200000, 96000),

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
                  test_streams.Generate02]:
            self.__test_reader__(g(44100), 1, block_size=1152)
        for g in [test_streams.Generate03,
                  test_streams.Generate04]:
            self.__test_reader__(g(44100), 5, block_size=1152)

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
                    len(pattern) * 100,
                    block_size=1152)

    @FORMAT_ALAC
    def test_sines(self):
        for g in self.__stream_variations__():
            self.__test_reader__(g, 200000, block_size=1152)

        for g in self.__multichannel_stream_variations__():
            self.__test_reader_nonalac__(g, 200000, block_size=1152)

    @FORMAT_ALAC
    def test_wasted_bps(self):
        self.__test_reader__(test_streams.WastedBPS16(1000),
                             1000,
                             block_size=1152)

    @FORMAT_ALAC
    def test_blocksizes(self):
        noise = struct.unpack(">32h", os.urandom(64))

        for block_size in [16, 17, 18, 19, 20, 21, 22, 23, 24,
                           25, 26, 27, 28, 29, 30, 31, 32, 33]:
            self.__test_reader__(
                test_streams.MD5Reader(
                    test_streams.FrameListReader(noise,
                                                 44100, 1, 16)),
                len(noise),
                block_size=block_size)

    @FORMAT_ALAC
    def test_noise(self):
        for (channels, mask) in [
            (1, audiotools.ChannelMask.from_channels(1)),
            (2, audiotools.ChannelMask.from_channels(2))]:
            for bps in [16, 24]:
                # the reference decoder can't handle very large block sizes
                for blocksize in [32, 4096, 8192]:
                    self.__test_reader__(
                        MD5_Reader(
                            EXACT_RANDOM_PCM_Reader(
                                pcm_frames=65536,
                                sample_rate=44100,
                                channels=channels,
                                channel_mask=mask,
                                bits_per_sample=bps)),
                        65536,
                        block_size=blocksize)

    @FORMAT_ALAC
    def test_fractional(self):
        def __perform_test__(block_size, pcm_frames):
            self.__test_reader__(
                MD5_Reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                pcm_frames,
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
                             200000,
                             block_size=16)

        # The alac(1) decoder I'm using as a reference can't handle
        # this block size, even though iTunes handles the resulting files
        # just fine.  Therefore, it's likely an alac bug beyond my
        # capability to fix.
        # I don't expect anyone will use anything other than the default
        # block size anyway.

        # self.__test_reader__(test_streams.Sine16_Mono(200000, 96000,
        #                                               441.0, 0.61, 661.5, 0.37),
        #                      block_size=65535)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 9,
                                                      441.0, 0.61, 661.5, 0.37),
                             200000,
                             block_size=1152)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 90,
                                                      441.0, 0.61, 661.5, 0.37),
                             200000,
                             block_size=1152)

        self.__test_reader__(test_streams.Sine16_Mono(200000, 90000,
                                                      441.0, 0.61, 661.5, 0.37),
                             200000,
                             block_size=1152)

    @FORMAT_ALAC
    def test_python_codec(self):
        def test_python_reader(pcmreader, total_pcm_frames, block_size=4096):
            # ALAC doesn't really have encoding options worth mentioning
            from audiotools.py_encoders import encode_mdat

            # encode file using Python-based encoder
            temp_file = tempfile.NamedTemporaryFile(suffix=".m4a")
            audiotools.ALACAudio.from_pcm(
                temp_file.name,
                pcmreader,
                block_size=block_size,
                encoding_function=encode_mdat)

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            from audiotools.py_decoders import ALACDecoder as ALACDecoder1
            from audiotools.decoders import ALACDecoder as ALACDecoder2

            self.assertTrue(
                audiotools.pcm_cmp(
                    ALACDecoder1(temp_file.name),
                    ALACDecoder2(temp_file.name)))

            # test from_pcm() with total_pcm_frames indicated
            pcmreader.reset()
            audiotools.ALACAudio.from_pcm(
                temp_file.name,
                pcmreader,
                total_pcm_frames=total_pcm_frames,
                block_size=block_size,
                encoding_function=encode_mdat)

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            from audiotools.py_decoders import ALACDecoder as ALACDecoder1
            from audiotools.decoders import ALACDecoder as ALACDecoder2

            self.assertTrue(
                audiotools.pcm_cmp(
                    ALACDecoder1(temp_file.name),
                    ALACDecoder2(temp_file.name)))

            temp_file.close()

        # test small files
        for g in [test_streams.Generate01,
                  test_streams.Generate02]:
            test_python_reader(g(44100), 1, block_size=1152)
        for g in [test_streams.Generate03,
                  test_streams.Generate04]:
            test_python_reader(g(44100), 5, block_size=1152)

        # test full scale deflection
        for (bps, fsd) in [(16, test_streams.fsd16),
                           (24, test_streams.fsd24)]:
            for pattern in [test_streams.PATTERN01,
                            test_streams.PATTERN02,
                            test_streams.PATTERN03,
                            test_streams.PATTERN04,
                            test_streams.PATTERN05,
                            test_streams.PATTERN06,
                            test_streams.PATTERN07]:
                test_python_reader(fsd(pattern, 100),
                                   len(pattern) * 100,
                                   block_size=1152)

        # test silence
        for g in [test_streams.Silence16_Mono(5000, 48000),
                  test_streams.Silence16_Stereo(5000, 48000),
                  test_streams.Silence24_Mono(5000, 48000),
                  test_streams.Silence24_Stereo(5000, 48000)]:
            test_python_reader(g, 5000, block_size=1152)

        # test sines
        for g in [test_streams.Sine16_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine16_Mono(5000, 96000,
                                           441.0, 0.61, 661.5, 0.37),
                  test_streams.Sine16_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine16_Stereo(5000, 96000,
                                             441.0, 0.50, 882.0, 0.49, 1.0),
                  test_streams.Sine24_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine24_Mono(5000, 96000,
                                           441.0, 0.61, 661.5, 0.37),
                  test_streams.Sine24_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine24_Stereo(5000, 96000,
                                             441.0, 0.50, 882.0, 0.49, 1.0)]:
            test_python_reader(g, 5000, block_size=1152)

        for g in [test_streams.Simple_Sine(5000, 44100, 0x0007, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (30720, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x0107, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (19200, 30000),
                                           (16640, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x0037, 16,
                                           (6400, 10000),
                                           (8960, 15000),
                                           (11520, 20000),
                                           (12800, 25000),
                                           (14080, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x003F, 16,
                                           (6400, 10000),
                                           (11520, 15000),
                                           (16640, 20000),
                                           (21760, 25000),
                                           (26880, 30000),
                                           (30720, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x013F, 16,
                                           (6400, 10000),
                                           (11520, 15000),
                                           (16640, 20000),
                                           (21760, 25000),
                                           (26880, 30000),
                                           (30720, 35000),
                                           (29000, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x00FF, 16,
                                           (6400, 10000),
                                           (11520, 15000),
                                           (16640, 20000),
                                           (21760, 25000),
                                           (26880, 30000),
                                           (30720, 35000),
                                           (29000, 40000),
                                           (28000, 45000)),

                  test_streams.Simple_Sine(5000, 44100, 0x0007, 24,
                                           (1638400, 10000),
                                           (3276800, 20000),
                                           (7864320, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x0107, 24,
                                           (1638400, 10000),
                                           (3276800, 20000),
                                           (4915200, 30000),
                                           (4259840, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x0037, 24,
                                           (1638400, 10000),
                                           (2293760, 15000),
                                           (2949120, 20000),
                                           (3276800, 25000),
                                           (3604480, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x003F, 24,
                                           (1638400, 10000),
                                           (2949120, 15000),
                                           (4259840, 20000),
                                           (5570560, 25000),
                                           (6881280, 30000),
                                           (7864320, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x013F, 24,
                                           (1638400, 10000),
                                           (2949120, 15000),
                                           (4259840, 20000),
                                           (5570560, 25000),
                                           (6881280, 30000),
                                           (7864320, 35000),
                                           (7000000, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x00FF, 24,
                                           (1638400, 10000),
                                           (2949120, 15000),
                                           (4259840, 20000),
                                           (5570560, 25000),
                                           (6881280, 30000),
                                           (7864320, 35000),
                                           (7000000, 40000),
                                           (6000000, 45000))]:
            test_python_reader(g, 5000, block_size=1152)

        # test wasted BPS
        test_python_reader(test_streams.WastedBPS16(1000),
                           1000,
                           block_size=1152)

        # test block sizes
        noise = struct.unpack(">32h", os.urandom(64))

        for block_size in [16, 17, 18, 19, 20, 21, 22, 23, 24,
                           25, 26, 27, 28, 29, 30, 31, 32, 33]:
            test_python_reader(
                test_streams.MD5Reader(
                    test_streams.FrameListReader(noise, 44100, 1, 16)),
                len(noise),
                block_size=block_size)

        # test noise
        for (channels, mask) in [
            (1, audiotools.ChannelMask.from_channels(1)),
            (2, audiotools.ChannelMask.from_channels(2))]:
            for bps in [16, 24]:
                # the reference decoder can't handle very large block sizes
                for blocksize in [32, 4096, 8192]:
                    test_python_reader(
                        EXACT_RANDOM_PCM_Reader(
                            pcm_frames=4097,
                            sample_rate=44100,
                            channels=channels,
                            channel_mask=mask,
                            bits_per_sample=bps),
                        4097,
                        block_size=blocksize)

        # test fractional
        for (block_size,
             pcm_frames) in [(33, [31, 32, 33, 34, 35, 2046,
                                   2047, 2048, 2049, 2050]),
                             (256, [254, 255, 256, 257, 258, 510, 511, 512,
                                    513, 514, 1022, 1023, 1024, 1025, 1026,
                                    2046, 2047, 2048, 2049, 2050, 4094, 4095,
                                    4096, 4097, 4098])]:
            for frame_count in pcm_frames:
                test_python_reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=frame_count,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16),
                    frame_count,
                    block_size=block_size)

        # test frame header variations
        test_python_reader(
            test_streams.Sine16_Mono(5000, 96000,
                                     441.0, 0.61, 661.5, 0.37),
            5000,
            block_size=16)

        test_python_reader(
            test_streams.Sine16_Mono(5000, 9,
                                     441.0, 0.61, 661.5, 0.37),
            5000,
            block_size=1152)

        test_python_reader(
            test_streams.Sine16_Mono(5000, 90,
                                     441.0, 0.61, 661.5, 0.37),
            5000,
            block_size=1152)

        test_python_reader(
            test_streams.Sine16_Mono(5000, 90000,
                                     441.0, 0.61, 661.5, 0.37),
            5000,
            block_size=1152)


class AUFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.AuAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_AU
    def test_overlong_file(self):
        # trying to generate too large of a file
        # should throw an exception right away if total_pcm_frames known
        # instead of building it first

        self.assertEqual(os.path.isfile("invalid.au"), False)

        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          "invalid.au",
                          EXACT_SILENCE_PCM_Reader(
                              pcm_frames=715827883,
                              sample_rate=44100,
                              channels=2,
                              bits_per_sample=24),
                          total_pcm_frames=715827883)

        self.assertEqual(os.path.isfile("invalid.au"), False)

    @FORMAT_AU
    def test_channel_mask(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for mask in [["front_center"],
                         ["front_left",
                          "front_right"]]:
                cm = audiotools.ChannelMask.from_fields(
                    **dict([(f, True) for f in mask]))
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=len(cm),
                                                channel_mask=int(cm)))
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
                cm = audiotools.ChannelMask.from_fields(
                    **dict([(f, True) for f in mask]))
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=len(cm),
                                                channel_mask=int(cm)))
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
                track = audiotools.open(temp.name)
                self.assertEqual(track.channels(), len(cm))
                self.assertEqual(track.channel_mask(), 0)
        finally:
            temp.close()

    @FORMAT_AU
    def test_verify(self):
        # test truncated file
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

        # test convert() error
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
        self.encode_opts = [{"block_size": 1152,
                             "max_lpc_order": 0,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 3},
                            {"block_size": 1152,
                             "max_lpc_order": 0,
                             "adaptive_mid_side": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 3},
                            {"block_size": 1152,
                             "max_lpc_order": 0,
                             "exhaustive_model_search": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 3},
                            {"block_size": 4096,
                             "max_lpc_order": 6,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 4},
                            {"block_size": 4096,
                             "max_lpc_order": 8,
                             "adaptive_mid_side": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 4},
                            {"block_size": 4096,
                             "max_lpc_order": 8,
                             "mid_side": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 5},
                            {"block_size": 4096,
                             "max_lpc_order": 8,
                             "mid_side": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 6},
                            {"block_size": 4096,
                             "max_lpc_order": 8,
                             "mid_side": True,
                             "exhaustive_model_search": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 6},
                            {"block_size": 4096,
                             "max_lpc_order": 12,
                             "mid_side": True,
                             "exhaustive_model_search": True,
                             "min_residual_partition_order": 0,
                             "max_residual_partition_order": 6}]

    @FORMAT_FLAC
    def test_init(self):
        # check missing file
        self.assertRaises(audiotools.flac.InvalidFLAC,
                          audiotools.FlacAudio,
                          "/dev/null/foo")

        # check invalid file
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

        # check some decoder errors,
        # mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(IOError, self.decoder, None)

        self.assertRaises(IOError, self.decoder, "filename")

    @FORMAT_FLAC
    def test_metadata2(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(temp.name,
                                              BLANK_PCM_Reader(1))

            # check that a non-cover image with a description round-trips
            m = audiotools.MetaData()
            m.add_image(
                audiotools.Image.new(
                    TEST_COVER1, u'Unicode \u3057\u3066\u307f\u308b', 1))
            track.set_metadata(m)

            new_track = audiotools.open(track.filename)
            m2 = new_track.get_metadata()

            self.assertEqual(m.images()[0], m2.images()[0])

            orig_md5 = md5()
            audiotools.transfer_framelist_data(track.to_pcm(), orig_md5.update)

            # add an image too large to fit into a FLAC metadata chunk
            metadata = track.get_metadata()
            metadata.add_image(
                audiotools.Image.new(HUGE_BMP.decode('bz2'), u'', 0))

            track.update_metadata(metadata)

            # ensure that setting the metadata doesn't break the file
            new_md5 = md5()
            audiotools.transfer_framelist_data(track.to_pcm(), new_md5.update)

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            # ensure that setting fresh oversized metadata
            # doesn't break the file
            metadata = audiotools.MetaData()
            metadata.add_image(
                audiotools.Image.new(HUGE_BMP.decode('bz2'), u'', 0))

            track.set_metadata(metadata)

            new_md5 = md5()
            audiotools.transfer_framelist_data(track.to_pcm(), new_md5.update)

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            # add a COMMENT block too large to fit into a FLAC metadata chunk
            metadata = track.get_metadata()
            metadata.comment = u"a" * 16777216

            track.update_metadata(metadata)

            # ensure that setting the metadata doesn't break the file
            new_md5 = md5()
            audiotools.transfer_framelist_data(track.to_pcm(), new_md5.update)

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            # ensure that setting fresh oversized metadata
            # doesn't break the file
            metadata = audiotools.MetaData(comment=u"a" * 16777216)

            track.set_metadata(metadata)

            new_md5 = md5()
            audiotools.transfer_framelist_data(track.to_pcm(), new_md5.update)

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            track.set_metadata(audiotools.MetaData(track_name=u"Testing"))

            # ensure that vendor_string isn't modified by setting metadata
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

            # FIXME - ensure that channel mask isn't modified
            # by setting metadata
        finally:
            temp.close()

    @FORMAT_FLAC
    def test_update_metadata(self):
        # build a temporary file
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            temp.write(open("flac-allframes.flac", "rb").read())
            temp.flush()
            flac_file = audiotools.open(temp.name)

            # attempt to adjust its metadata with bogus side data fields
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

            # ensure that set_metadata() restores fields to original values
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

            # adjust its metadata with new bogus side data files
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

            # ensure that update_metadata() uses the bogus side data
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

    @FORMAT_FLAC
    def test_verify(self):
        self.assertEqual(audiotools.open("flac-allframes.flac").__md5__,
                         'f53f86876dcd7783225c93ba8a938c7d'.decode('hex'))

        flac_data = open("flac-allframes.flac", "rb").read()

        self.assertEqual(audiotools.open("flac-allframes.flac").verify(),
                         True)

        # try changing the file underfoot
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            temp.write(flac_data)
            temp.flush()
            flac_file = audiotools.open(temp.name)
            self.assertEqual(flac_file.verify(), True)

            for i in range(0, len(flac_data)):
                f = open(temp.name, "wb")
                f.write(flac_data[0:i])
                f.close()
                self.assertRaises(audiotools.InvalidFile,
                                  flac_file.verify)

            for i in range(0x2A, len(flac_data)):
                for j in range(8):
                    new_data = list(flac_data)
                    new_data[i] = chr(ord(new_data[i]) ^ (1 << j))
                    f = open(temp.name, "wb")
                    f.write("".join(new_data))
                    f.close()
                    self.assertRaises(audiotools.InvalidFile,
                                      flac_file.verify)
        finally:
            temp.close()

        # check a FLAC file with a short header
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for i in range(0, 0x2A):
                temp.seek(0, 0)
                temp.write(flac_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                if (i < 4):
                    self.assertEqual(
                        audiotools.file_type(open(temp.name, "rb")),
                        None)
                self.assertRaises(IOError,
                                  audiotools.decoders.FlacDecoder,
                                  open(temp.name, "rb"))
        finally:
            temp.close()

        # check a FLAC file that's been truncated
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for i in range(0x2A, len(flac_data)):
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

        # test a FLAC file with a single swapped bit
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            for i in range(0x2A, len(flac_data)):
                for j in range(8):
                    bytes = map(ord, flac_data[:])
                    bytes[i] ^= (1 << j)
                    temp.seek(0, 0)
                    temp.write("".join(map(chr, bytes)))
                    temp.flush()
                    self.assertEqual(len(flac_data),
                                     os.path.getsize(temp.name))

                    with audiotools.open(temp.name).to_pcm() as decoders:
                        try:
                            self.assertRaises(
                                ValueError,
                                audiotools.transfer_framelist_data,
                                decoders, lambda x: x)
                        except IOError:
                            # Randomly swapping bits may send the decoder
                            # off the end of the stream before triggering
                            # a CRC-16 error.
                            # We simply need to catch that case and continue
                            continue
        finally:
            temp.close()

        # test a FLAC file with an invalid STREAMINFO block
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
                BitstreamWriter(temp.file, False).build(
                    "16u 16u 24u 24u 20u 3u 5u 36U 16b",
                    streaminfo)
                temp.write(data)
                temp.flush()
                with audiotools.open(temp.name).to_pcm() as decoders:
                    self.assertRaises(ValueError,
                                      audiotools.transfer_framelist_data,
                                      decoders, lambda x: x)
            finally:
                temp.close()

        # test that convert() from an invalid file also raises an exception
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
            test_streams.Silence8_Mono(200000, 44100),
            test_streams.Silence8_Mono(200000, 96000),
            test_streams.Silence8_Stereo(200000, 44100),
            test_streams.Silence8_Stereo(200000, 96000),
            test_streams.Silence16_Mono(200000, 44100),
            test_streams.Silence16_Mono(200000, 96000),
            test_streams.Silence16_Stereo(200000, 44100),
            test_streams.Silence16_Stereo(200000, 96000),
            test_streams.Silence24_Mono(200000, 44100),
            test_streams.Silence24_Mono(200000, 96000),
            test_streams.Silence24_Stereo(200000, 44100),
            test_streams.Silence24_Stereo(200000, 96000),

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

        self.assertEqual(
            subprocess.call([audiotools.BIN["flac"], "-ts", temp_file.name]),
            0,
            "flac decode error on %s with options %s" %
            (repr(pcmreader),
             repr(encode_options)))

        flac = audiotools.open(temp_file.name)
        self.assert_(flac.total_frames() > 0)
        if (hasattr(pcmreader, "digest")):
            self.assertEqual(flac.__md5__, pcmreader.digest())

        # check FlacDecoder using raw file
        md5sum = md5()
        d = self.decoder(open(temp_file.name, "rb"))
        f = d.read(audiotools.FRAMELIST_SIZE)
        while (len(f) > 0):
            md5sum.update(f.to_bytes(False, True))
            f = d.read(audiotools.FRAMELIST_SIZE)
        d.close()
        self.assertEqual(md5sum.digest(), pcmreader.digest())

        # check FlacDecoder using file-like wrapper
        md5sum = md5()
        d = self.decoder(Filewrapper(open(temp_file.name, "rb")))
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
        # FIXME - handle 8bps/24bps also
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
                    self.__test_reader__(
                        test_streams.MD5Reader(
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

        # the reference encoder's test_streams.sh unit test
        # re-does the 9Hz/90Hz/90000Hz tests for some reason
        # which I won't repeat here

    @FORMAT_FLAC
    def test_option_variations(self):
        # testing all the option variations
        # against all the stream variations
        # along with a few extra option variations
        # takes a *long* time - so don't panic

        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for disable in [[],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes"],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes",
                             "disable_fixed_subframes"]]:
                for extra in [[],
                              # FIXME - no analogue for -p option
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
                    (4, audiotools.ChannelMask.from_fields(front_left=True,
                                                           front_right=True,
                                                           back_left=True,
                                                           back_right=True)),
                    (8, audiotools.ChannelMask(0))]:
                    for bps in [8, 16, 24]:
                        for extra in [[],
                                      # FIXME - no analogue for -p option
                                      ["exhaustive_model_search"]]:
                            for blocksize in [None, 32, 32768, 65535]:
                                for d in disable:
                                    encode_opts[d] = True
                                for e in extra:
                                    encode_opts[e] = True
                                if (blocksize is not None):
                                    encode_opts["block_size"] = blocksize

                                self.__test_reader__(
                                    MD5_Reader(
                                        EXACT_RANDOM_PCM_Reader(
                                            pcm_frames=65536,
                                            sample_rate=44100,
                                            channels=channels,
                                            channel_mask=mask,
                                            bits_per_sample=bps)),
                                    **encode_opts)

                                self.__test_reader__(
                                    MD5_Reader(
                                        EXACT_SILENCE_PCM_Reader(
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
                MD5_Reader(
                    EXACT_RANDOM_PCM_Reader(
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

    # PCMReaders don't yet support seeking,
    # so the seek tests can be skipped

    # cuesheets are supported at the metadata level,
    # which is tested above

    # WAVE and AIFF length fixups are handled by the
    # WaveAudio and AIFFAudio classes

    # multiple file handling is performed at the tool level

    # as is metadata handling

    @FORMAT_FLAC
    def test_clean(self):
        # metadata is tested separately

        from audiotools.text import (CLEAN_FLAC_REMOVE_ID3V2,
                                     CLEAN_FLAC_REMOVE_ID3V1,
                                     CLEAN_FLAC_REORDERED_STREAMINFO,
                                     CLEAN_FLAC_POPULATE_MD5,
                                     CLEAN_FLAC_ADD_CHANNELMASK,
                                     CLEAN_FLAC_FIX_SEEKTABLE)

        # check FLAC files with ID3 tags
        f = open("flac-id3.flac", "rb")
        self.assertEqual(f.read(3), "ID3")
        f.close()
        track = audiotools.open("flac-id3.flac")
        metadata1 = track.get_metadata()
        fixes = track.clean()
        self.assertEqual(fixes,
                         [CLEAN_FLAC_REMOVE_ID3V2,
                          CLEAN_FLAC_REMOVE_ID3V1])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(fixes,
                             [CLEAN_FLAC_REMOVE_ID3V2,
                              CLEAN_FLAC_REMOVE_ID3V1])
            f = open(temp.name, "rb")
            self.assertEqual(f.read(4), "fLaC")
            f.close()
            track2 = audiotools.open(temp.name)
            self.assertEqual(metadata1, track2.get_metadata())
            self.assertTrue(
                audiotools.pcm_cmp(track.to_pcm(), track2.to_pcm()))
        finally:
            temp.close()

        # check FLAC files with double ID3 tags
        f = open("flac-id3-2.flac", "rb")
        self.assertEqual(f.read(3), "ID3")
        f.close()
        track = audiotools.open("flac-id3-2.flac")
        metadata1 = track.get_metadata()
        fixes = track.clean()
        self.assertEqual(fixes,
                         [CLEAN_FLAC_REMOVE_ID3V2])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(fixes,
                             [CLEAN_FLAC_REMOVE_ID3V2])
            f = open(temp.name, "rb")
            self.assertEqual(f.read(4), "fLaC")
            f.close()
            track2 = audiotools.open(temp.name)
            self.assertEqual(metadata1, track2.get_metadata())
            self.assertTrue(
                audiotools.pcm_cmp(track.to_pcm(), track2.to_pcm()))
        finally:
            temp.close()

        # check FLAC files with STREAMINFO in the wrong location
        f = open("flac-disordered.flac", "rb")
        self.assertEqual(f.read(5), "fLaC\x04")
        f.close()
        track = audiotools.open("flac-disordered.flac")
        metadata1 = track.get_metadata()
        fixes = track.clean()
        self.assertEqual(fixes,
                         [CLEAN_FLAC_REORDERED_STREAMINFO])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(fixes,
                             [CLEAN_FLAC_REORDERED_STREAMINFO])
            f = open(temp.name, "rb")
            self.assertEqual(f.read(5), "fLaC\x00")
            f.close()
            track2 = audiotools.open(temp.name)
            self.assertEqual(metadata1, track2.get_metadata())
            self.assertTrue(
                audiotools.pcm_cmp(track.to_pcm(), track2.to_pcm()))
        finally:
            temp.close()

        # check FLAC files with empty MD5 sum
        track = audiotools.open("flac-nonmd5.flac")
        fixes = []
        self.assertEqual(
            track.get_metadata().get_block(
                audiotools.flac.Flac_STREAMINFO.BLOCK_ID).md5sum, chr(0) * 16)
        fixes = track.clean()
        self.assertEqual(fixes, [CLEAN_FLAC_POPULATE_MD5])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(fixes, [CLEAN_FLAC_POPULATE_MD5])
            track2 = audiotools.open(temp.name)
            self.assertEqual(
                track2.get_metadata().get_block(
                    audiotools.flac.Flac_STREAMINFO.BLOCK_ID).md5sum,
                '\xd2\xb1 \x19\x90\x19\xb69' +
                '\xd5\xa7\xe2\xb3F>\x9c\x97')
            self.assertTrue(
                audiotools.pcm_cmp(track.to_pcm(), track2.to_pcm()))
        finally:
            temp.close()

        # check 24bps/6ch FLAC files without WAVEFORMATEXTENSIBLE_CHANNEL_MASK
        for (path, mask) in [("flac-nomask1.flac", 0x3F),
                             ("flac-nomask2.flac", 0x3F),
                             ("flac-nomask3.flac", 0x3),
                             ("flac-nomask4.flac", 0x3)]:
            no_blocks_file = tempfile.NamedTemporaryFile(suffix=".flac")
            try:
                no_blocks_file.write(open(path, "rb").read())
                no_blocks_file.flush()
                track = audiotools.open(no_blocks_file.name)
                metadata = track.get_metadata()
                for block_id in range(1, 7):
                    metadata.replace_blocks(block_id, [])
                track.update_metadata(metadata)

                for track in [audiotools.open(path),
                              audiotools.open(no_blocks_file.name)]:
                    fixes = track.clean()
                    self.assertEqual(fixes, [CLEAN_FLAC_ADD_CHANNELMASK])

                    temp = tempfile.NamedTemporaryFile(suffix=".flac")
                    try:
                        fixes = track.clean(temp.name)
                        self.assertEqual(
                            fixes,
                            [CLEAN_FLAC_ADD_CHANNELMASK])
                        new_track = audiotools.open(temp.name)
                        self.assertEqual(new_track.channel_mask(),
                                         track.channel_mask())
                        self.assertEqual(int(new_track.channel_mask()), mask)
                        metadata = new_track.get_metadata()

                        self.assertEqual(
                            metadata.get_block(
                                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[
                                u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"][0],
                            u"0x%.4X" % (mask))
                    finally:
                        temp.close()
            finally:
                no_blocks_file.close()

        # check bad seekpoint destinations
        track = audiotools.open("flac-seektable.flac")
        fixes = track.clean()
        self.assertEqual(fixes, [CLEAN_FLAC_FIX_SEEKTABLE])
        temp = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(
                fixes,
                [CLEAN_FLAC_FIX_SEEKTABLE])
            new_track = audiotools.open(temp.name)
            fixes = new_track.clean()
            self.assertEqual(fixes, [])
        finally:
            temp.close()

    @FORMAT_FLAC
    def test_nonmd5(self):
        flac = audiotools.open("flac-nonmd5.flac")
        self.assertEqual(flac.__md5__, chr(0) * 16)
        md5sum = md5()

        # ensure that a FLAC file with an empty MD5 sum
        # decodes without errors
        audiotools.transfer_framelist_data(flac.to_pcm(),
                                           md5sum.update)
        self.assertEqual(md5sum.hexdigest(),
                         'd2b120199019b639d5a7e2b3463e9c97')

        # ensure that a FLAC file with an empty MD5 sum
        # verifies without errors
        self.assertEqual(flac.verify(), True)

    @FORMAT_FLAC
    def test_python_codec(self):
        # Python decoder and encoder are far too slow
        # to run anything resembling a complete set of tests
        # so we'll cut them down to the very basics

        def test_python_reader(pcmreader, **encode_options):
            from audiotools.py_encoders import encode_flac

            # encode file using Python-based encoder
            temp_file = tempfile.NamedTemporaryFile(suffix=".flac")
            encode_flac(temp_file.name,
                        audiotools.BufferedPCMReader(pcmreader),
                        **encode_options)

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            from audiotools.py_decoders import FlacDecoder as FlacDecoder1
            from audiotools.decoders import FlacDecoder as FlacDecoder2

            self.assertTrue(
                audiotools.pcm_cmp(
                    FlacDecoder1(temp_file.name, 0),
                    FlacDecoder2(open(temp_file.name, "rb"))))

            temp_file.close()

        # test small files
        for g in [test_streams.Generate01,
                  test_streams.Generate02,
                  test_streams.Generate03,
                  test_streams.Generate04]:
            test_python_reader(g(44100),
                               block_size=1152,
                               max_lpc_order=16,
                               min_residual_partition_order=0,
                               max_residual_partition_order=3,
                               mid_side=True,
                               adaptive_mid_side=True,
                               exhaustive_model_search=True)

        # test full-scale deflection
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
                test_python_reader(
                    fsd(pattern, 100),
                    block_size=1152,
                    max_lpc_order=16,
                    min_residual_partition_order=0,
                    max_residual_partition_order=3,
                    mid_side=True,
                    adaptive_mid_side=True,
                    exhaustive_model_search=True)

        # test silence
        for g in [test_streams.Silence8_Mono(5000, 48000),
                  test_streams.Silence8_Stereo(5000, 48000),
                  test_streams.Silence16_Mono(5000, 48000),
                  test_streams.Silence16_Stereo(5000, 48000),
                  test_streams.Silence24_Mono(5000, 48000),
                  test_streams.Silence24_Stereo(5000, 48000)]:
            test_python_reader(g,
                               block_size=1152,
                               max_lpc_order=16,
                               min_residual_partition_order=0,
                               max_residual_partition_order=3,
                               mid_side=True,
                               adaptive_mid_side=True,
                               exhaustive_model_search=True)

        # test sines
        for g in [test_streams.Sine8_Mono(5000, 48000,
                                          441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine8_Stereo(5000, 48000,
                                            441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine16_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine16_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine24_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine24_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 8,
                                           (25, 10000),
                                           (50, 20000),
                                           (120, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 8,
                                           (25, 10000),
                                           (50, 20000),
                                           (75, 30000),
                                           (65, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 8,
                                           (25, 10000),
                                           (35, 15000),
                                           (45, 20000),
                                           (50, 25000),
                                           (55, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 8,
                                           (25, 10000),
                                           (45, 15000),
                                           (65, 20000),
                                           (85, 25000),
                                           (105, 30000),
                                           (120, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (30720, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (19200, 30000),
                                           (16640, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 16,
                                           (6400, 10000),
                                           (8960, 15000),
                                           (11520, 20000),
                                           (12800, 25000),
                                           (14080, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 16,
                                           (6400, 10000),
                                           (11520, 15000),
                                           (16640, 20000),
                                           (21760, 25000),
                                           (26880, 30000),
                                           (30720, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 24,
                                           (1638400, 10000),
                                           (3276800, 20000),
                                           (7864320, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 24,
                                           (1638400, 10000),
                                           (3276800, 20000),
                                           (4915200, 30000),
                                           (4259840, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 24,
                                           (1638400, 10000),
                                           (2293760, 15000),
                                           (2949120, 20000),
                                           (3276800, 25000),
                                           (3604480, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 24,
                                           (1638400, 10000),
                                           (2949120, 15000),
                                           (4259840, 20000),
                                           (5570560, 25000),
                                           (6881280, 30000),
                                           (7864320, 35000))]:
            test_python_reader(g,
                               block_size=1152,
                               max_lpc_order=16,
                               min_residual_partition_order=0,
                               max_residual_partition_order=3,
                               mid_side=True,
                               adaptive_mid_side=True,
                               exhaustive_model_search=True)

        # test wasted BPS
        test_python_reader(test_streams.WastedBPS16(1000),
                           block_size=1152,
                           max_lpc_order=16,
                           min_residual_partition_order=0,
                           max_residual_partition_order=3,
                           mid_side=True,
                           adaptive_mid_side=True,
                           exhaustive_model_search=True)

        # test block sizes
        noise = struct.unpack(">32h", os.urandom(64))

        encoding_args = {"min_residual_partition_order": 0,
                         "max_residual_partition_order": 6,
                         "mid_side": True,
                         "adaptive_mid_side": True,
                         "exhaustive_model_search": True}
        for block_size in [16, 17, 18, 19, 20, 21, 22, 23,
                           24, 25, 26, 27, 28, 29, 30, 31, 32, 33]:
            for lpc_order in [0, 1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 31, 32]:
                args = encoding_args.copy()
                args["block_size"] = block_size
                args["max_lpc_order"] = lpc_order
                test_python_reader(
                    test_streams.FrameListReader(noise, 44100, 1, 16),
                    **args)


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
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=channels,
                                                channel_mask=0))
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
        # ensure that the 'too' meta atom isn't modified by setting metadata
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
        # test invalid file sent to to_pcm()

        # FIXME - mpg123 doesn't generate errors on invalid files
        # Ultimately, all of MP3/MP2 decoding needs to be internalized
        # so that these sorts of errors can be caught consistently.

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

        # test invalid file send to convert()
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

        # # test verify() on invalid files
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

        #     # first, try truncating the file underfoot
        #     bad_mpx_file = audiotools.open(temp.name)
        #     for i in range(len(mpeg_data)):
        #         try:
        #             if ((mpeg_data[i] == chr(0xFF)) and
        #                 (ord(mpeg_data[i + 1]) & 0xE0)):
        #                 # skip sizes that may be the end of a frame
        #                 continue
        #         except IndexError:
        #             continue

        #         f = open(temp.name, "wb")
        #         f.write(mpeg_data[0:i])
        #         f.close()
        #         self.assertEqual(os.path.getsize(temp.name), i)
        #         self.assertRaises(audiotools.InvalidFile,
        #                           bad_mpx_file.verify)

        #     # then try swapping some of the header bits
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

            # ensure that setting particular ID3 variant
            # sticks, even through get/set_metadata
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

            # this should be 4 characters long in UCS-4 environments
            # if not, we're in a UCS-2 environment
            # which is limited to 16 bits anyway
            test_string = u'f\U0001d55foo'

            # u'\ufffd' is the "not found" character
            # this string should result from escaping through UCS-2
            test_string_out = u'f\ufffdoo'

            if (len(test_string) == 4):
                self.assertEqual(test_string,
                                 test_string.encode('utf-16').decode('utf-16'))
                self.assertEqual(test_string.encode('ucs2').decode('ucs2'),
                                 test_string_out)

                # ID3v2.4 supports UTF-8/UTF-16
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

                # ID3v2.3 and ID3v2.2 only support UCS-2
                for id3_class in (audiotools.ID3v23Comment,
                                  audiotools.ID3v22Comment):
                    metadata = audiotools.ID3v23Comment.converted(
                        audiotools.MetaData(track_name=u"Foo"))
                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3, metadata)

                    # ensure that text fields round-trip correctly
                    # (i.e. the extra-wide char gets replaced)
                    metadata.track_name = test_string

                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3.track_name, test_string_out)

                    # ensure that comment blocks round-trip correctly
                    metadata.comment = test_string
                    track.set_metadata(metadata)
                    id3 = track.get_metadata()
                    self.assertEqual(id3.track_name, test_string_out)

                    # ensure that image comment fields round-trip correctly
                    metadata.add_image(
                        id3_class.IMAGE_FRAME.converted(
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

    @FORMAT_MP3
    def test_clean(self):
        # check MP3 file with double ID3 tags

        from audiotools.text import CLEAN_REMOVE_DUPLICATE_ID3V2

        original_size = os.path.getsize("id3-2.mp3")

        track = audiotools.open("id3-2.mp3")
        # ensure second ID3 tag is ignored
        self.assertEqual(track.get_metadata().track_name, u"Title1")

        # ensure duplicate ID3v2 tag is detected and removed
        fixes = track.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_DUPLICATE_ID3V2])
        temp = tempfile.NamedTemporaryFile(suffix=".mp3")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_DUPLICATE_ID3V2])
            track2 = audiotools.open(temp.name)
            self.assertEqual(track2.get_metadata(), track.get_metadata())
            # ensure new file is exactly one tag smaller
            # and the padding is preserved in the old tag
            self.assertEqual(os.path.getsize(temp.name),
                             original_size - 0x46A)
        finally:
            temp.close()


class MP2FileTest(MP3FileTest):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio
        self.suffix = "." + self.audio_class.SUFFIX


class OggVerify:
    @FORMAT_VORBIS
    @FORMAT_OPUS
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

            # first, try truncating the file
            for i in range(len(good_file_data)):
                f = open(bad_file.name, "wb")
                f.write(good_file_data[0:i])
                f.flush()
                self.assertEqual(os.path.getsize(bad_file.name), i)
                try:
                    new_track = self.audio_class(bad_file.name)
                    self.assertRaises(audiotools.InvalidFile,
                                      new_track.verify)
                except audiotools.InvalidFile:
                    self.assert_(True)

            # then, try flipping a bit
            for i in range(len(good_file_data)):
                for j in range(8):
                    bad_file_data = list(good_file_data)
                    bad_file_data[i] = chr(ord(bad_file_data[i]) ^ (1 << j))
                    f = open(bad_file.name, "wb")
                    f.write("".join(bad_file_data))
                    f.close()
                    self.assertEqual(os.path.getsize(bad_file.name),
                                     len(good_file_data))
                    try:
                        new_track = self.audio_class(bad_file.name)
                        self.assertRaises(audiotools.InvalidFile,
                                          new_track.verify)
                    except audiotools.InvalidFile:
                        self.assert_(True)
        finally:
            good_file.close()
            bad_file.close()

        if (self.audio_class is audiotools.OpusAudio):
            # opusdec doesn't currently reject invalid
            # streams like it should
            # so the encoding test doesn't work right
            # (this is a known bug)
            return

        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            track = self.audio_class.from_pcm(
                temp.name,
                BLANK_PCM_Reader(1))
            self.assertEqual(track.verify(), True)
            good_data = open(temp.name, 'rb').read()
            f = open(temp.name, 'wb')
            f.write(good_data[0:min(100, len(good_data) - 1)])
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
        # check missing file
        self.assertRaises(audiotools.flac.InvalidFLAC,
                          audiotools.OggFlacAudio,
                          "/dev/null/foo")

        # check invalid file
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

        # check some decoder errors,
        # mostly to ensure a failed init doesn't make Python explode
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
        # check invalid file
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

        # check some decoder errors,
        # mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(IOError, self.decoder, None)

        self.assertRaises(IOError, self.decoder, "filename")

    @FORMAT_SHORTEN
    def test_bits_per_sample(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for bps in (8, 16):
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1, bits_per_sample=bps))
                self.assertEqual(track.bits_per_sample(), bps)
                track2 = audiotools.open(temp.name)
                self.assertEqual(track2.bits_per_sample(), bps)
        finally:
            temp.close()

    @FORMAT_SHORTEN
    def test_verify(self):
        # test changing the file underfoot
        temp = tempfile.NamedTemporaryFile(suffix=".shn")
        try:
            shn_data = open("shorten-frames.shn", "rb").read()
            temp.write(shn_data)
            temp.flush()
            shn_file = audiotools.open(temp.name)
            self.assertEqual(shn_file.verify(), True)

            for i in range(0, len(shn_data.rstrip(chr(0)))):
                f = open(temp.name, "wb")
                f.write(shn_data[0:i])
                f.close()
                self.assertRaises(audiotools.InvalidFile,
                                  shn_file.verify)

            # unfortunately, Shorten doesn't have any checksumming
            # or other ways to reliably detect swapped bits
        finally:
            temp.close()

        # testing truncating various Shorten files
        for (first, last, filename) in [(62, 89, "shorten-frames.shn"),
                                        (61, 116, "shorten-lpc.shn")]:

            f = open(filename, "rb")
            shn_data = f.read()
            f.close()

            temp = tempfile.NamedTemporaryFile(suffix=".shn")
            try:
                for i in range(0, first):
                    temp.seek(0, 0)
                    temp.write(shn_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)
                    self.assertRaises(IOError,
                                      audiotools.decoders.SHNDecoder,
                                      open(temp.name, "rb"))

                for i in range(first, len(shn_data[0:last].rstrip(chr(0)))):
                    temp.seek(0, 0)
                    temp.write(shn_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)
                    decoder = audiotools.decoders.SHNDecoder(
                        open(temp.name, "rb"))
                    self.assertNotEqual(decoder, None)
                    self.assertRaises(IOError,
                                      decoder.pcm_split)

                    decoder = audiotools.decoders.SHNDecoder(
                        open(temp.name, "rb"))
                    self.assertNotEqual(decoder, None)
                    self.assertRaises(IOError,
                                      audiotools.transfer_framelist_data,
                                      decoder, lambda x: x)
            finally:
                temp.close()

        # test running convert() on a truncated file
        # triggers EncodingError
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
            test_streams.Silence8_Mono(200000, 44100),
            test_streams.Silence8_Mono(200000, 96000),
            test_streams.Silence8_Stereo(200000, 44100),
            test_streams.Silence8_Stereo(200000, 96000),
            test_streams.Silence16_Mono(200000, 44100),
            test_streams.Silence16_Mono(200000, 96000),
            test_streams.Silence16_Stereo(200000, 44100),
            test_streams.Silence16_Stereo(200000, 96000),

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
                         "reference Shorten binary shorten(1) " +
                         "required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".shn")

        # construct a temporary wave file from pcmreader
        temp_input_wave_file = tempfile.NamedTemporaryFile(suffix=".wav")
        temp_input_wave = audiotools.WaveAudio.from_pcm(
            temp_input_wave_file.name, pcmreader)
        temp_input_wave.verify()

        options = encode_options.copy()
        (head, tail) = temp_input_wave.wave_header_footer()
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

        # first, ensure the Shorten-encoded file
        # has the same MD5 signature as pcmreader once decoded
        for shndec in [self.decoder(open(temp_file.name, "rb")),
                       self.decoder(Filewrapper(open(temp_file.name, "rb")))]:
            md5sum = md5()
            f = shndec.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = shndec.read(audiotools.FRAMELIST_SIZE)
            shndec.close()
            self.assertEqual(md5sum.digest(), pcmreader.digest())

        # then compare our .to_wave() output
        # with that of the Shorten reference decoder
        shn.convert(temp_wav_file1.name, audiotools.WaveAudio)
        subprocess.call([audiotools.BIN["shorten"],
                         "-x", shn.filename, temp_wav_file2.name])

        wave = audiotools.WaveAudio(temp_wav_file1.name)
        wave.verify()
        wave = audiotools.WaveAudio(temp_wav_file2.name)
        wave.verify()

        self.assertTrue(
            audiotools.pcm_cmp(
                audiotools.WaveAudio(temp_wav_file1.name).to_pcm(),
                audiotools.WaveAudio(temp_wav_file2.name).to_pcm()))

        temp_wav_file1.close()
        temp_wav_file2.close()

        # then perform PCM -> aiff -> Shorten -> PCM testing

        # construct a temporary wave file from pcmreader
        temp_input_aiff_file = tempfile.NamedTemporaryFile(suffix=".aiff")
        temp_input_aiff = temp_input_wave.convert(temp_input_aiff_file.name,
                                                  audiotools.AiffAudio)
        temp_input_aiff.verify()

        options = encode_options.copy()
        options["is_big_endian"] = True
        options["signed_samples"] = True
        (head, tail) = temp_input_aiff.aiff_header_footer()
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

        # first, ensure the Shorten-encoded file
        # has the same MD5 signature as pcmreader once decoded
        for shndec in [self.decoder(open(temp_file.name, "rb")),
                       self.decoder(Filewrapper(open(temp_file.name, "rb")))]:
            md5sum = md5()
            f = shndec.read(audiotools.BUFFER_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = shndec.read(audiotools.BUFFER_SIZE)
            shndec.close()
            self.assertEqual(md5sum.digest(), pcmreader.digest())

        # then compare our .to_aiff() output
        # with that of the Shorten reference decoder
        shn.convert(temp_aiff_file1.name, audiotools.AiffAudio)

        subprocess.call([audiotools.BIN["shorten"],
                         "-x", shn.filename, temp_aiff_file2.name])

        aiff = audiotools.AiffAudio(temp_aiff_file1.name)
        aiff.verify()
        aiff = audiotools.AiffAudio(temp_aiff_file2.name)
        aiff.verify()

        self.assertTrue(
            audiotools.pcm_cmp(
                audiotools.AiffAudio(temp_aiff_file1.name).to_pcm(),
                audiotools.AiffAudio(temp_aiff_file2.name).to_pcm()))

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
            self.__test_reader__(
                test_streams.MD5Reader(
                    test_streams.FrameListReader(noise, 44100, 1, 16)), **args)

    @FORMAT_SHORTEN
    def test_noise(self):
        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(front_left=True,
                                                       front_right=True,
                                                       back_left=True,
                                                       back_right=True)),
                (8, audiotools.ChannelMask(0))]:
                for bps in [8, 16]:
                    self.__test_reader__(
                        MD5_Reader(
                            EXACT_RANDOM_PCM_Reader(pcm_frames=65536,
                                                    sample_rate=44100,
                                                    channels=channels,
                                                    channel_mask=mask,
                                                    bits_per_sample=bps)),
                        **encode_opts)

    @FORMAT_SHORTEN
    def test_python_codec(self):
        def test_python_reader(pcmreader, total_pcm_frames, block_size=256):
            from audiotools.py_encoders import encode_shn

            temp_file = tempfile.NamedTemporaryFile(suffix=".shn")
            audiotools.ShortenAudio.from_pcm(
                temp_file.name,
                pcmreader,
                block_size=block_size,
                encoding_function=encode_shn)

            from audiotools.decoders import SHNDecoder as SHNDecoder1
            from audiotools.py_decoders import SHNDecoder as SHNDecoder2

            self.assertTrue(audiotools.pcm_cmp(
                SHNDecoder1(open(temp_file.name, "rb")),
                SHNDecoder2(temp_file.name)))

            # try test again, this time with total_pcm_frames indicated
            pcmreader.reset()
            audiotools.ShortenAudio.from_pcm(
                temp_file.name,
                pcmreader,
                total_pcm_frames=total_pcm_frames,
                block_size=block_size,
                encoding_function=encode_shn)

            self.assertTrue(audiotools.pcm_cmp(
                SHNDecoder1(open(temp_file.name, "rb")),
                SHNDecoder2(temp_file.name)))

            temp_file.close()

        # test small files
        for g in [test_streams.Generate01,
                  test_streams.Generate02]:
            test_python_reader(g(44100), 1, block_size=256)

        for g in [test_streams.Generate03,
                  test_streams.Generate04]:
            test_python_reader(g(44100), 5, block_size=256)

        # test full scale deflection
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
                test_python_reader(stream,
                                   len(pattern) * 100,
                                   block_size=256)

        # test silence
        for g in [test_streams.Silence8_Mono(5000, 48000),
                  test_streams.Silence8_Stereo(5000, 48000),
                  test_streams.Silence16_Mono(5000, 48000),
                  test_streams.Silence16_Stereo(5000, 48000)]:
            test_python_reader(g, 5000, block_size=256)

        # test sines
        for g in [test_streams.Sine8_Mono(5000, 48000,
                                          441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine8_Stereo(5000, 48000,
                                            441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine16_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine16_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 8,
                                           (25, 10000),
                                           (50, 20000),
                                           (120, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 8,
                                           (25, 10000),
                                           (50, 20000),
                                           (75, 30000),
                                           (65, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 8,
                                           (25, 10000),
                                           (35, 15000),
                                           (45, 20000),
                                           (50, 25000),
                                           (55, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 8,
                                           (25, 10000),
                                           (45, 15000),
                                           (65, 20000),
                                           (85, 25000),
                                           (105, 30000),
                                           (120, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (30720, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (19200, 30000),
                                           (16640, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 16,
                                           (6400, 10000),
                                           (8960, 15000),
                                           (11520, 20000),
                                           (12800, 25000),
                                           (14080, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 16,
                                           (6400, 10000),
                                           (11520, 15000),
                                           (16640, 20000),
                                           (21760, 25000),
                                           (26880, 30000),
                                           (30720, 35000))]:
            test_python_reader(g, 5000, block_size=256)

        # test block sizes
        noise = struct.unpack(">32h", os.urandom(64))

        for block_size in [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           256, 1024]:
            test_python_reader(
                test_streams.FrameListReader(noise, 44100, 1, 16),
                len(noise),
                block_size=block_size)

        # test noise
        for block_size in [4, 256, 1024]:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(front_left=True,
                                                       front_right=True,
                                                       back_left=True,
                                                       back_right=True)),
                (8, audiotools.ChannelMask(0))]:
                for bps in [8, 16]:
                    test_python_reader(
                        EXACT_RANDOM_PCM_Reader(
                            pcm_frames=5000,
                            sample_rate=44100,
                            channels=channels,
                            channel_mask=mask,
                            bits_per_sample=bps),
                        5000,
                        block_size=block_size)


class VorbisFileTest(OggVerify, LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.VorbisAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_VORBIS
    def test_channels(self):
        temp = tempfile.NamedTemporaryFile(suffix=self.suffix)
        try:
            for channels in [1, 2, 3, 4, 5, 6]:
                track = self.audio_class.from_pcm(
                    temp.name, BLANK_PCM_Reader(1,
                                                channels=channels,
                                                channel_mask=0))
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

            original_pcm_sum = md5()
            audiotools.transfer_framelist_data(track.to_pcm(),
                                               original_pcm_sum.update)

            comment = audiotools.MetaData(
                track_name=u"Name",
                track_number=1,
                comment=u"abcdefghij" * 13005)
            track.set_metadata(comment)
            track = audiotools.open(track_file.name)
            self.assertEqual(comment, track.get_metadata())

            new_pcm_sum = md5()
            audiotools.transfer_framelist_data(track.to_pcm(),
                                               new_pcm_sum.update)

            self.assertEqual(original_pcm_sum.hexdigest(),
                             new_pcm_sum.hexdigest())
        finally:
            track_file.close()


class OpusFileTest(OggVerify, LossyFileTest):
    def setUp(self):
        self.audio_class = audiotools.OpusAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_OPUS
    def test_channels(self):
        # FIXME - test Opus channel assignment
        pass

    @FORMAT_OPUS
    def test_big_comment(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(1))
            original_pcm_sum = md5()
            audiotools.transfer_framelist_data(track.to_pcm(),
                                               original_pcm_sum.update)

            comment = audiotools.MetaData(
                track_name=u"Name",
                track_number=1,
                comment=u"abcdefghij" * 13005)
            track.set_metadata(comment)
            track = audiotools.open(track_file.name)
            self.assertEqual(comment, track.get_metadata())

            new_pcm_sum = md5()
            audiotools.transfer_framelist_data(track.to_pcm(),
                                               new_pcm_sum.update)

            self.assertEqual(original_pcm_sum.hexdigest(),
                             new_pcm_sum.hexdigest())
        finally:
            track_file.close()


class WaveFileTest(TestForeignWaveChunks,
                   LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.WaveAudio
        self.suffix = "." + self.audio_class.SUFFIX

    @FORMAT_WAVE
    def test_overlong_file(self):
        # trying to generate too large of a file
        # should throw an exception right away if total_pcm_frames known
        # instead of building it first

        self.assertEqual(os.path.isfile("invalid.wav"), False)

        self.assertRaises(audiotools.EncodingError,
                          self.audio_class.from_pcm,
                          "invalid.wav",
                          EXACT_SILENCE_PCM_Reader(
                              pcm_frames=715827883,
                              sample_rate=44100,
                              channels=2,
                              bits_per_sample=24),
                          total_pcm_frames=715827883)

        self.assertEqual(os.path.isfile("invalid.wav"), False)

    @FORMAT_WAVE
    def test_verify(self):
        # test various truncated files with verify()
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

                # try changing the file out from under it
                for i in range(0, len(wav_data)):
                    f = open(temp.name, 'wb')
                    f.write(wav_data[0:i])
                    f.close()
                    self.assertEqual(os.path.getsize(temp.name), i)
                    self.assertRaises(audiotools.InvalidFile,
                                      wave.verify)
            finally:
                temp.close()

        # test running convert() on a truncated file
        # triggers EncodingError
        # FIXME - truncate file underfoot
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

        # test other truncated file combinations
        for (fmt_size, wav_file) in [(0x24, "wav-8bit.wav"),
                                     (0x24, "wav-1ch.wav"),
                                     (0x24, "wav-2ch.wav"),
                                     (0x3C, "wav-6ch.wav")]:
            f = open(wav_file, 'rb')
            wav_data = f.read()
            f.close()

            temp = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                # first, check that a truncated fmt chunk raises an exception
                # at init-time
                for i in range(0, fmt_size + 8):
                    temp.seek(0, 0)
                    temp.write(wav_data[0:i])
                    temp.flush()
                    self.assertEqual(os.path.getsize(temp.name), i)

                    self.assertRaises(audiotools.InvalidFile,
                                      audiotools.WaveAudio,
                                      temp.name)

            finally:
                temp.close()

        # test for non-ASCII chunk IDs
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

        # test multiple fmt chunks
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

        # test multiple data chunks
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [FMT, DATA, DATA])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

        # test data chunk before fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [DATA, FMT])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

        # test no fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            audiotools.WaveAudio.wave_from_chunks(temp.name, [DATA])
            self.assertRaises(
                audiotools.InvalidFile,
                audiotools.open(temp.name).verify)
        finally:
            temp.close()

        # test no data chunk
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

        # test multiple fmt chunks
        # test multiple data chunks
        # test data chunk before fmt chunk
        temp = tempfile.NamedTemporaryFile(suffix=".wav")
        fixed = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            for chunks in [[FMT, FMT, DATA],
                           [FMT, DATA, FMT],
                           [FMT, DATA, DATA],
                           [DATA, FMT],
                           [DATA, FMT, FMT]]:
                audiotools.WaveAudio.wave_from_chunks(temp.name, chunks)
                fixes = audiotools.open(temp.name).clean(fixed.name)
                wave = audiotools.open(fixed.name)
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

        # test converting 24bps file to WAVEFORMATEXTENSIBLE
        # FIXME


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
                             "correlation_passes": 0},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "correlation_passes": 0},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "correlation_passes": 1},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "correlation_passes": 2},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "correlation_passes": 5},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "correlation_passes": 10},
                            {"block_size": 44100,
                             "false_stereo": True,
                             "wasted_bits": True,
                             "joint_stereo": True,
                             "correlation_passes": 16}]

    @FORMAT_WAVPACK
    def test_init(self):
        # check missing file
        self.assertRaises(audiotools.wavpack.InvalidWavPack,
                          audiotools.WavPackAudio,
                          "/dev/null/foo")

        # check invalid file
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

        # check some decoder errors,
        # mostly to ensure a failed init doesn't make Python explode
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(IOError, self.decoder, None)

        self.assertRaises(IOError, self.decoder, "filename")

    @FORMAT_WAVPACK
    def test_verify(self):
        # test truncating a WavPack file causes verify()
        # to raise InvalidFile as necessary
        wavpackdata = open("wavpack-combo.wv", "rb").read()
        temp = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            self.assertEqual(audiotools.open("wavpack-combo.wv").verify(),
                             True)
            temp.write(wavpackdata)
            temp.flush()
            test_wavpack = audiotools.open(temp.name)
            for i in range(0, 0x20B):
                f = open(temp.name, "wb")
                f.write(wavpackdata[0:i])
                f.close()
                self.assertEqual(os.path.getsize(temp.name), i)
                self.assertRaises(audiotools.InvalidFile,
                                  test_wavpack.verify)

                # Swapping random bits doesn't affect WavPack's decoding
                # in many instances - which is surprising since I'd
                # expect its adaptive routines to be more susceptible
                # to values being out-of-whack during decorrelation.
                # This resilience may be related to its hybrid mode,
                # but it doesn't inspire confidence.

        finally:
            temp.close()

        # test truncating a WavPack file causes the WavPackDecoder
        # to raise IOError as necessary
        from audiotools.decoders import WavPackDecoder

        f = open("silence.wv")
        wavpack_data = f.read()
        f.close()

        temp = tempfile.NamedTemporaryFile(suffix=".wv")

        try:
            for i in range(0, len(wavpack_data)):
                temp.seek(0, 0)
                temp.write(wavpack_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                try:
                    decoder = WavPackDecoder(open(temp.name, "rb"))
                except IOError:
                    # chopping off the first few bytes might trigger
                    # an IOError at init-time, which is ok
                    continue
                self.assertNotEqual(decoder, None)
                decoder = WavPackDecoder(open(temp.name, "rb"))
                self.assertNotEqual(decoder, None)
                self.assertRaises(IOError,
                                  audiotools.transfer_framelist_data,
                                  decoder, lambda f: f)
        finally:
            temp.close()

        # test a truncated WavPack file's convert() method
        # generates EncodingErrors
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
            test_streams.Silence8_Mono(200000, 44100),
            test_streams.Silence8_Mono(200000, 96000),
            test_streams.Silence8_Stereo(200000, 44100),
            test_streams.Silence8_Stereo(200000, 96000),
            test_streams.Silence16_Mono(200000, 44100),
            test_streams.Silence16_Mono(200000, 96000),
            test_streams.Silence16_Stereo(200000, 44100),
            test_streams.Silence16_Stereo(200000, 96000),
            test_streams.Silence24_Mono(200000, 44100),
            test_streams.Silence24_Mono(200000, 96000),
            test_streams.Silence24_Stereo(200000, 44100),
            test_streams.Silence24_Stereo(200000, 96000),

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

    def __test_reader__(self, pcmreader, total_pcm_frames, **encode_options):
        if (not audiotools.BIN.can_execute(audiotools.BIN["wvunpack"])):
            self.assert_(False,
                         "reference WavPack binary wvunpack(1) " +
                         "required for this test")

        temp_file = tempfile.NamedTemporaryFile(suffix=".wv")

        self.encode(temp_file.name,
                    audiotools.BufferedPCMReader(pcmreader),
                    **encode_options)

        sub = subprocess.Popen([audiotools.BIN["wvunpack"],
                                "-vmq", temp_file.name],
                               stdout=open(os.devnull, "wb"),
                               stderr=open(os.devnull, "wb"))

        self.assertEqual(sub.wait(), 0,
                         "wvunpack decode error on %s with options %s" %
                         (repr(pcmreader),
                          repr(encode_options)))

        for wavpack in [self.decoder(open(temp_file.name, "rb")),
                        self.decoder(Filewrapper(open(temp_file.name, "rb")))]:
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

        # perform test again with total_pcm_frames indicated
        pcmreader.reset()

        self.encode(temp_file.name,
                    audiotools.BufferedPCMReader(pcmreader),
                    total_pcm_frames=total_pcm_frames,
                    **encode_options)

        sub = subprocess.Popen([audiotools.BIN["wvunpack"],
                                "-vmq", temp_file.name],
                               stdout=open(os.devnull, "wb"),
                               stderr=open(os.devnull, "wb"))

        self.assertEqual(sub.wait(), 0,
                         "wvunpack decode error on %s with options %s" %
                         (repr(pcmreader),
                          repr(encode_options)))

        for wavpack in [self.decoder(open(temp_file.name, "rb")),
                        self.decoder(Filewrapper(open(temp_file.name, "rb")))]:
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
                      test_streams.Generate02]:
                self.__test_reader__(g(44100), 1, **opts)
            for g in [test_streams.Generate03,
                      test_streams.Generate04]:
                self.__test_reader__(g(44100), 5, **opts)

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
                        test_streams.MD5Reader(fsd(pattern, 100)),
                        len(pattern) * 100,
                        **opts)

    @FORMAT_WAVPACK
    def test_wasted_bps(self):
        for opts in self.encode_opts:
            self.__test_reader__(test_streams.WastedBPS16(1000),
                                 1000,
                                 **opts)

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
                opts_copy["correlation_passes"] = decorrelation_passes
                self.__test_reader__(
                    test_streams.MD5Reader(
                        test_streams.FrameListReader(noise,
                                                     44100, 1, 16)),
                    len(noise),
                    **opts_copy)

    @FORMAT_WAVPACK
    def test_silence(self):
        for opts in self.encode_opts:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(front_left=True,
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
                            65536,
                            **opts_copy)

    @FORMAT_WAVPACK
    def test_noise(self):
        for opts in self.encode_opts:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2)),
                (4, audiotools.ChannelMask.from_fields(front_left=True,
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
                                EXACT_RANDOM_PCM_Reader(
                                    pcm_frames=65536,
                                    sample_rate=44100,
                                    channels=channels,
                                    channel_mask=mask,
                                    bits_per_sample=bps)),
                            65536,
                            **opts_copy)

    @FORMAT_WAVPACK
    def test_fractional(self):
        def __perform_test__(block_size, pcm_frames):
            self.__test_reader__(
                MD5_Reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                pcm_frames,
                block_size=block_size,
                correlation_passes=5,
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

        # test a mix of identical and non-identical channels
        # using different decorrelation, joint stereo and false stereo options
        combos = 0
        for (false_stereo, joint_stereo) in [(False, False),
                                             (False, True),
                                             (True, False),
                                             (True, True)]:
            for (channels, mask) in [(2, 0x3), (3, 0x7), (4, 0x33),
                                     (5, 0x3B), (6, 0x3F)]:
                for readers in __permutations__(
                    [EXACT_BLANK_PCM_Reader,
                     EXACT_RANDOM_PCM_Reader,
                     test_streams.Sine16_Mono],
                    [{"pcm_frames": 100,
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
                      "a2": 0.37}], channels):
                    joined = MD5_Reader(Join_Reader(readers, mask))
                    self.__test_reader__(joined,
                                         100,
                                         block_size=44100,
                                         false_stereo=false_stereo,
                                         joint_stereo=joint_stereo,
                                         correlation_passes=1,
                                         wasted_bits=False)

    @FORMAT_WAVPACK
    def test_sines(self):
        for opts in self.encode_opts:
            for g in self.__stream_variations__():
                self.__test_reader__(g, 200000, **opts)

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
                                200000,
                                block_size=block_size,
                                false_stereo=false_stereo,
                                wasted_bits=wasted_bits,
                                joint_stereo=joint_stereo,
                                correlation_passes=decorrelation_passes)

    @FORMAT_WAVPACK
    def test_python_codec(self):
        def test_python_reader(pcmreader, total_pcm_frames, **encode_options):
            from audiotools.py_encoders import encode_wavpack

            # encode file using Python-based encoder
            temp_file = tempfile.NamedTemporaryFile(suffix=".wv")

            encode_wavpack(temp_file.name,
                           audiotools.BufferedPCMReader(pcmreader),
                           **encode_options)

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            from audiotools.py_decoders import WavPackDecoder as WavPackDecoder1
            from audiotools.decoders import WavPackDecoder as WavPackDecoder2

            self.assertTrue(
                audiotools.pcm_cmp(
                    WavPackDecoder1(temp_file.name),
                    WavPackDecoder2(open(temp_file.name, "rb"))))

            # redo test with total_pcm_frames indicated
            pcmreader.reset()

            encode_wavpack(temp_file.name,
                           audiotools.BufferedPCMReader(pcmreader),
                           total_pcm_frames=total_pcm_frames,
                           **encode_options)

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            from audiotools.py_decoders import WavPackDecoder as WavPackDecoder1
            from audiotools.decoders import WavPackDecoder as WavPackDecoder2

            self.assertTrue(
                audiotools.pcm_cmp(
                    WavPackDecoder1(temp_file.name),
                    WavPackDecoder2(open(temp_file.name, "rb"))))

            temp_file.close()

        # test small files
        for opts in self.encode_opts:
            for g in [test_streams.Generate01,
                      test_streams.Generate02]:
                test_python_reader(g(44100), 1, **opts)
            for g in [test_streams.Generate03,
                      test_streams.Generate04]:
                test_python_reader(g(44100), 5, **opts)

        # test full scale deflection
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
                    test_python_reader(fsd(pattern, 100),
                                       len(pattern) * 100,
                                       **opts)

        # test wasted BPS
        for opts in self.encode_opts:
            test_python_reader(test_streams.WastedBPS16(1000),
                               1000,
                               **opts)

        # test block sizes
        noise = struct.unpack(">32h", os.urandom(64))

        opts = {"false_stereo": False,
                "wasted_bits": False,
                "joint_stereo": False}
        for block_size in [16, 17, 18, 19, 20, 21, 22, 23,
                           24, 25, 26, 27, 28, 29, 30, 31, 32, 33]:
            for decorrelation_passes in [0, 1, 5]:
                opts_copy = opts.copy()
                opts_copy["block_size"] = block_size
                opts_copy["correlation_passes"] = decorrelation_passes
                test_python_reader(
                    test_streams.FrameListReader(noise,
                                                 44100, 1, 16),
                    len(noise),
                    **opts_copy)

        # test silence
        for opts in self.encode_opts:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2))]:
                opts_copy = opts.copy()
                opts_copy['block_size'] = 4095
                test_python_reader(
                    EXACT_SILENCE_PCM_Reader(
                        pcm_frames=4096,
                        sample_rate=44100,
                        channels=channels,
                        channel_mask=mask,
                        bits_per_sample=16),
                    4096,
                    **opts_copy)

        # test noise
        for opts in self.encode_opts:
            for (channels, mask) in [
                (1, audiotools.ChannelMask.from_channels(1)),
                (2, audiotools.ChannelMask.from_channels(2))]:
                opts_copy = opts.copy()
                opts_copy['block_size'] = 4095
                test_python_reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=4096,
                        sample_rate=44100,
                        channels=channels,
                        channel_mask=mask,
                        bits_per_sample=16),
                    4096,
                    **opts_copy)

        # test fractional
        for (block_size,
             pcm_frames_list) in [(33, [31, 32, 33, 34, 35, 2046,
                                        2047, 2048, 2049, 2050]),
                                  (256, [254, 255, 256, 257, 258, 510,
                                         511, 512, 513, 514, 1022, 1023,
                                         1024, 1025, 1026, 2046, 2047, 2048,
                                         2049, 2050, 4094, 4095, 4096, 4097,
                                         4098])]:
            for pcm_frames in pcm_frames_list:
                test_python_reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16),
                    pcm_frames,
                    block_size=block_size,
                    correlation_passes=5,
                    false_stereo=False,
                    wasted_bits=False,
                    joint_stereo=False)

        # test sines
        for opts in self.encode_opts:
            for g in [test_streams.Sine8_Mono(5000, 48000,
                                              441.0, 0.50, 441.0, 0.49),
                      test_streams.Sine8_Stereo(5000, 48000,
                                                441.0, 0.50, 441.0, 0.49, 1.0),
                      test_streams.Sine16_Mono(5000, 48000,
                                               441.0, 0.50, 441.0, 0.49),
                      test_streams.Sine16_Stereo(5000, 48000,
                                                 441.0, 0.50, 441.0, 0.49, 1.0),
                      test_streams.Sine24_Mono(5000, 48000,
                                               441.0, 0.50, 441.0, 0.49),
                      test_streams.Sine24_Stereo(5000, 48000,
                                                 441.0, 0.50, 441.0, 0.49, 1.0),
                      test_streams.Simple_Sine(5000, 44100, 0x7, 8,
                                               (25, 10000),
                                               (50, 20000),
                                               (120, 30000)),
                      test_streams.Simple_Sine(5000, 44100, 0x33, 8,
                                               (25, 10000),
                                               (50, 20000),
                                               (75, 30000),
                                               (65, 40000)),
                      test_streams.Simple_Sine(5000, 44100, 0x37, 8,
                                               (25, 10000),
                                               (35, 15000),
                                               (45, 20000),
                                               (50, 25000),
                                               (55, 30000)),
                      test_streams.Simple_Sine(5000, 44100, 0x3F, 8,
                                               (25, 10000),
                                               (45, 15000),
                                               (65, 20000),
                                               (85, 25000),
                                               (105, 30000),
                                               (120, 35000)),

                      test_streams.Simple_Sine(5000, 44100, 0x7, 16,
                                               (6400, 10000),
                                               (12800, 20000),
                                               (30720, 30000)),
                      test_streams.Simple_Sine(5000, 44100, 0x33, 16,
                                               (6400, 10000),
                                               (12800, 20000),
                                               (19200, 30000),
                                               (16640, 40000)),
                      test_streams.Simple_Sine(5000, 44100, 0x37, 16,
                                               (6400, 10000),
                                               (8960, 15000),
                                               (11520, 20000),
                                               (12800, 25000),
                                               (14080, 30000)),
                      test_streams.Simple_Sine(5000, 44100, 0x3F, 16,
                                               (6400, 10000),
                                               (11520, 15000),
                                               (16640, 20000),
                                               (21760, 25000),
                                               (26880, 30000),
                                               (30720, 35000)),

                      test_streams.Simple_Sine(5000, 44100, 0x7, 24,
                                               (1638400, 10000),
                                               (3276800, 20000),
                                               (7864320, 30000)),
                      test_streams.Simple_Sine(5000, 44100, 0x33, 24,
                                               (1638400, 10000),
                                               (3276800, 20000),
                                               (4915200, 30000),
                                               (4259840, 40000)),
                      test_streams.Simple_Sine(5000, 44100, 0x37, 24,
                                               (1638400, 10000),
                                               (2293760, 15000),
                                               (2949120, 20000),
                                               (3276800, 25000),
                                               (3604480, 30000)),
                      test_streams.Simple_Sine(5000, 44100, 0x3F, 24,
                                               (1638400, 10000),
                                               (2949120, 15000),
                                               (4259840, 20000),
                                               (5570560, 25000),
                                               (6881280, 30000),
                                               (7864320, 35000))]:
                test_python_reader(g, 5000, **opts)


class TTAFileTest(LosslessFileTest):
    def setUp(self):
        self.audio_class = audiotools.TrueAudio
        self.suffix = "." + self.audio_class.SUFFIX

        from audiotools.decoders import TTADecoder

        self.decoder = TTADecoder
        self.encode = audiotools.TrueAudio.from_pcm

    @FORMAT_TTA
    def test_init(self):
        # check missing file
        self.assertRaises(audiotools.tta.InvalidTTA,
                          audiotools.TrueAudio,
                          "/dev/null/foo")

        # check invalid file
        invalid_file = tempfile.NamedTemporaryFile(suffix=".tta")
        try:
            for c in "invalidstringxxx":
                invalid_file.write(c)
                invalid_file.flush()
                self.assertRaises(audiotools.tta.InvalidTTA,
                                  audiotools.TrueAudio,
                                  invalid_file.name)
        finally:
            invalid_file.close()

        # check some decoder errors
        self.assertRaises(TypeError, self.decoder)

        self.assertRaises(IOError, self.decoder, None)

        self.assertRaises(IOError, self.decoder, "filename")

    @FORMAT_TTA
    def test_verify(self):
        tta_data = open("trueaudio.tta", "rb").read()

        self.assertEqual(audiotools.open("trueaudio.tta").verify(), True)

        # try changing the file underfoot
        temp = tempfile.NamedTemporaryFile(suffix=".tta")
        try:
            temp.write(tta_data)
            temp.flush()
            tta_file = audiotools.open(temp.name)
            self.assertEqual(tta_file.verify(), True)

            for i in range(0, len(tta_data)):
                f = open(temp.name, "wb")
                f.write(tta_data[0:i])
                f.close()
                self.assertRaises(audiotools.InvalidFile,
                                  tta_file.verify)

            for i in range(0x2A, len(tta_data)):
                for j in range(8):
                    new_data = list(tta_data)
                    new_data[i] = chr(ord(new_data[i]) ^ (1 << j))
                    f = open(temp.name, "wb")
                    f.write("".join(new_data))
                    f.close()
                    self.assertRaises(audiotools.InvalidFile,
                                      tta_file.verify)
        finally:
            temp.close()

        # check a TTA file with a short header
        temp = tempfile.NamedTemporaryFile(suffix=".tta")
        try:
            for i in range(0, 18):
                temp.seek(0, 0)
                temp.write(tta_data[0:i])
                temp.flush()
                self.assertEqual(os.path.getsize(temp.name), i)
                if (i < 4):
                    self.assertEqual(
                        audiotools.file_type(open(temp.name, "rb")),
                        None)
                self.assertRaises(IOError,
                                  audiotools.decoders.TTADecoder,
                                  open(temp.name, "rb"))
        finally:
            temp.close()

        # check a TTA file that's been truncated
        temp = tempfile.NamedTemporaryFile(suffix=".tta")
        try:
            for i in range(30, len(tta_data)):
                temp.seek(0, 0)
                temp.write(tta_data[0:i])
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

        # check a TTA file with a single swapped bit
        temp = tempfile.NamedTemporaryFile(suffix=".tta")
        try:
            for i in range(0x30, len(tta_data)):
                for j in range(8):
                    bytes = map(ord, tta_data[:])
                    bytes[i] ^= (1 << j)
                    temp.seek(0, 0)
                    temp.write("".join(map(chr, bytes)))
                    temp.flush()
                    self.assertEqual(len(tta_data),
                                     os.path.getsize(temp.name))

                    with audiotools.open(temp.name).to_pcm() as decoders:
                        try:
                            self.assertRaises(
                                ValueError,
                                audiotools.transfer_framelist_data,
                                decoders, lambda x: x)
                        except IOError:
                            # Randomly swapping bits may send the decoder
                            # off the end of the stream before triggering
                            # a CRC-16 error.
                            # We simply need to catch that case and continue
                            continue
        finally:
            temp.close()

    def __stream_variations__(self):
        for stream in [
            test_streams.Silence8_Mono(200000, 44100),
            test_streams.Silence8_Mono(200000, 96000),
            test_streams.Silence8_Stereo(200000, 44100),
            test_streams.Silence8_Stereo(200000, 96000),
            test_streams.Silence16_Mono(200000, 44100),
            test_streams.Silence16_Mono(200000, 96000),
            test_streams.Silence16_Stereo(200000, 44100),
            test_streams.Silence16_Stereo(200000, 96000),
            test_streams.Silence24_Mono(200000, 44100),
            test_streams.Silence24_Mono(200000, 96000),
            test_streams.Silence24_Stereo(200000, 44100),
            test_streams.Silence24_Stereo(200000, 96000),

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

    def __test_reader__(self, pcmreader, total_pcm_frames):
        if (not audiotools.BIN.can_execute(audiotools.BIN["tta"])):
            self.assert_(
                False,
                "reference TrueAudio binary tta(1) required for this test")

        temp_tta_file = tempfile.NamedTemporaryFile(suffix=".tta")
        self.encode(temp_tta_file.name, pcmreader)

        if ((pcmreader.bits_per_sample > 8) and (pcmreader.channels <= 6)):
            # reference decoder doesn't like 8 bit .wav files?!
            # or files with too many channels?
            temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
            sub = subprocess.Popen([audiotools.BIN["tta"],
                                    "-d", temp_tta_file.name,
                                    temp_wav_file.name],
                                   stdout=open(os.devnull, "wb"),
                                   stderr=open(os.devnull, "wb"))
            self.assertEqual(sub.wait(), 0,
                             "tta decode error on %s" % (repr(pcmreader)))
        else:
            temp_wav_file = None

        for tta in [self.decoder(open(temp_tta_file.name, "rb")),
                    self.decoder(Filewrapper(open(temp_tta_file.name, "rb")))]:
            self.assertEqual(tta.sample_rate, pcmreader.sample_rate)
            self.assertEqual(tta.bits_per_sample, pcmreader.bits_per_sample)
            self.assertEqual(tta.channels, pcmreader.channels)

            md5sum = md5()
            f = tta.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = tta.read(audiotools.FRAMELIST_SIZE)
            tta.close()
            self.assertEqual(md5sum.digest(), pcmreader.digest())

            if (temp_wav_file is not None):
                wav_md5sum = md5()
                audiotools.transfer_framelist_data(
                    audiotools.WaveAudio(temp_wav_file.name).to_pcm(),
                    wav_md5sum.update)
                self.assertEqual(md5sum.digest(), wav_md5sum.digest())

        if (temp_wav_file is not None):
            temp_wav_file.close()

        # perform test again with total_pcm_frames indicated
        pcmreader.reset()
        self.encode(temp_tta_file.name,
                    pcmreader,
                    total_pcm_frames=total_pcm_frames)

        if ((pcmreader.bits_per_sample > 8) and (pcmreader.channels <= 6)):
            # reference decoder doesn't like 8 bit .wav files?!
            # or files with too many channels?
            temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
            sub = subprocess.Popen([audiotools.BIN["tta"],
                                    "-d", temp_tta_file.name,
                                    temp_wav_file.name],
                                   stdout=open(os.devnull, "wb"),
                                   stderr=open(os.devnull, "wb"))
            self.assertEqual(sub.wait(), 0,
                             "tta decode error on %s" % (repr(pcmreader)))
        else:
            temp_wav_file = None

        for tta in [self.decoder(open(temp_tta_file.name, "rb")),
                    self.decoder(Filewrapper(open(temp_tta_file.name, "rb")))]:
            self.assertEqual(tta.sample_rate, pcmreader.sample_rate)
            self.assertEqual(tta.bits_per_sample, pcmreader.bits_per_sample)
            self.assertEqual(tta.channels, pcmreader.channels)

            md5sum = md5()
            f = tta.read(audiotools.FRAMELIST_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False, True))
                f = tta.read(audiotools.FRAMELIST_SIZE)
            tta.close()
            self.assertEqual(md5sum.digest(), pcmreader.digest())
            temp_tta_file.close()

            if (temp_wav_file is not None):
                wav_md5sum = md5()
                audiotools.transfer_framelist_data(
                    audiotools.WaveAudio(temp_wav_file.name).to_pcm(),
                    wav_md5sum.update)
                self.assertEqual(md5sum.digest(), wav_md5sum.digest())

        if (temp_wav_file is not None):
            temp_wav_file.close()

    @FORMAT_TTA
    def test_small_files(self):
        for g in [test_streams.Generate01,
                  test_streams.Generate02]:
            self.__test_reader__(g(44100), 1)
        for g in [test_streams.Generate03,
                  test_streams.Generate04]:
            self.__test_reader__(g(44100), 5)

    @FORMAT_TTA
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
                    len(pattern) * 100)

    @FORMAT_TTA
    def test_wasted_bps(self):
        self.__test_reader__(test_streams.WastedBPS16(1000), 1000)

    @FORMAT_TTA
    def test_silence(self):
        for (channels, mask) in [
            (1, audiotools.ChannelMask.from_channels(1)),
            (2, audiotools.ChannelMask.from_channels(2)),
            (4, audiotools.ChannelMask.from_fields(front_left=True,
                                                   front_right=True,
                                                   back_left=True,
                                                   back_right=True)),
            (8, audiotools.ChannelMask(0))]:
            for bps in [8, 16, 24]:
                self.__test_reader__(
                    MD5_Reader(
                        EXACT_SILENCE_PCM_Reader(
                            pcm_frames=65536,
                            sample_rate=44100,
                            channels=channels,
                            channel_mask=mask,
                            bits_per_sample=bps)),
                    65536)

    @FORMAT_TTA
    def test_noise(self):
        for (channels, mask) in [
            (1, audiotools.ChannelMask.from_channels(1)),
            (2, audiotools.ChannelMask.from_channels(2)),
            (4, audiotools.ChannelMask.from_fields(front_left=True,
                                                   front_right=True,
                                                   back_left=True,
                                                   back_right=True)),
            (8, audiotools.ChannelMask(0))]:
            for bps in [8, 16, 24]:
                self.__test_reader__(
                    MD5_Reader(
                        EXACT_RANDOM_PCM_Reader(
                            pcm_frames=65536,
                            sample_rate=44100,
                            channels=channels,
                            channel_mask=mask,
                            bits_per_sample=bps)),
                    65536)

    @FORMAT_TTA
    def test_sines(self):
        for g in self.__stream_variations__():
            self.__test_reader__(g, 200000)

    @FORMAT_TTA
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

        for (channels, mask) in [(2, 0x3), (3, 0x7), (4, 0x33),
                                 (5, 0x3B), (6, 0x3F)]:
            for readers in __permutations__(
                [EXACT_BLANK_PCM_Reader,
                 EXACT_RANDOM_PCM_Reader,
                 test_streams.Sine16_Mono],
                [{"pcm_frames": 100,
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
                  "a2": 0.37}], channels):
                    self.__test_reader__(
                        MD5_Reader(Join_Reader(readers, mask)),
                        100)

    @FORMAT_TTA
    def test_fractional(self):
        for pcm_frames in [46078, 46079, 46080, 46081, 46082]:
            self.__test_reader__(
                MD5_Reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                pcm_frames)

    @FORMAT_TTA
    def test_python_codec(self):
        def test_python_reader(pcmreader, pcm_frames):
            if (not audiotools.BIN.can_execute(audiotools.BIN["tta"])):
                self.assert_(
                    False,
                    "reference TrueAudio binary tta(1) required for this test")

            from audiotools.py_encoders import encode_tta
            from audiotools.py_decoders import TTADecoder as TTADecoder1
            from audiotools.decoders import TTADecoder as TTADecoder2

            # encode file using Python-based encoder
            temp_tta_file = tempfile.NamedTemporaryFile(suffix=".tta")

            self.encode(temp_tta_file.name,
                        pcmreader,
                        encoding_function=encode_tta)

            # verify against output of Python encoder
            # against reference tta decoder
            if ((pcmreader.bits_per_sample > 8) and (pcmreader.channels <= 6)):
                # reference decoder doesn't like 8 bit .wav files?!
                # or files with too many channels?
                temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
                sub = subprocess.Popen([audiotools.BIN["tta"],
                                        "-d", temp_tta_file.name,
                                        temp_wav_file.name],
                                       stdout=open(os.devnull, "wb"),
                                       stderr=open(os.devnull, "wb"))
                self.assertEqual(sub.wait(), 0,
                                 "tta decode error on %s" % (repr(pcmreader)))

                self.assertTrue(
                    audiotools.pcm_cmp(
                        TTADecoder2(open(temp_tta_file.name, "rb")),
                        audiotools.WaveAudio(temp_wav_file.name).to_pcm()))

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            self.assertTrue(
                audiotools.pcm_cmp(
                    TTADecoder1(temp_tta_file.name),
                    TTADecoder2(open(temp_tta_file.name, "rb"))))

            # perform tests again with total_pcm_frames indicated
            pcmreader.reset()

            self.encode(temp_tta_file.name,
                        pcmreader,
                        total_pcm_frames=pcm_frames,
                        encoding_function=encode_tta)

            # verify against output of Python encoder
            # against reference tta decoder
            if ((pcmreader.bits_per_sample > 8) and (pcmreader.channels <= 6)):
                # reference decoder doesn't like 8 bit .wav files?!
                # or files with too many channels?
                temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
                sub = subprocess.Popen([audiotools.BIN["tta"],
                                        "-d", temp_tta_file.name,
                                        temp_wav_file.name],
                                       stdout=open(os.devnull, "wb"),
                                       stderr=open(os.devnull, "wb"))
                self.assertEqual(sub.wait(), 0,
                                 "tta decode error on %s" % (repr(pcmreader)))

                self.assertTrue(
                    audiotools.pcm_cmp(
                        TTADecoder2(open(temp_tta_file.name, "rb")),
                        audiotools.WaveAudio(temp_wav_file.name).to_pcm()))

            # verify contents of file decoded by
            # Python-based decoder against contents decoded by
            # C-based decoder
            self.assertTrue(
                audiotools.pcm_cmp(
                    TTADecoder1(temp_tta_file.name),
                    TTADecoder2(open(temp_tta_file.name, "rb"))))

            temp_tta_file.close()

        # test small files
        for g in [test_streams.Generate01,
                  test_streams.Generate02]:
            test_python_reader(g(44100), 1)
        for g in [test_streams.Generate03,
                  test_streams.Generate04]:
            test_python_reader(g(44100), 5)

        # test full-scale deflection
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
                test_python_reader(fsd(pattern, 100), len(pattern) * 100)

        # test silence
        for g in [test_streams.Silence8_Mono(5000, 48000),
                  test_streams.Silence8_Stereo(5000, 48000),
                  test_streams.Silence16_Mono(5000, 48000),
                  test_streams.Silence16_Stereo(5000, 48000),
                  test_streams.Silence24_Mono(5000, 48000),
                  test_streams.Silence24_Stereo(5000, 48000)]:
            test_python_reader(g, 5000)

        # test sines
        for g in [test_streams.Sine8_Mono(5000, 48000,
                                          441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine8_Stereo(5000, 48000,
                                            441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine16_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine16_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Sine24_Mono(5000, 48000,
                                           441.0, 0.50, 441.0, 0.49),
                  test_streams.Sine24_Stereo(5000, 48000,
                                             441.0, 0.50, 441.0, 0.49, 1.0),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 8,
                                           (25, 10000),
                                           (50, 20000),
                                           (120, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 8,
                                           (25, 10000),
                                           (50, 20000),
                                           (75, 30000),
                                           (65, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 8,
                                           (25, 10000),
                                           (35, 15000),
                                           (45, 20000),
                                           (50, 25000),
                                           (55, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 8,
                                           (25, 10000),
                                           (45, 15000),
                                           (65, 20000),
                                           (85, 25000),
                                           (105, 30000),
                                           (120, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (30720, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 16,
                                           (6400, 10000),
                                           (12800, 20000),
                                           (19200, 30000),
                                           (16640, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 16,
                                           (6400, 10000),
                                           (8960, 15000),
                                           (11520, 20000),
                                           (12800, 25000),
                                           (14080, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 16,
                                           (6400, 10000),
                                           (11520, 15000),
                                           (16640, 20000),
                                           (21760, 25000),
                                           (26880, 30000),
                                           (30720, 35000)),
                  test_streams.Simple_Sine(5000, 44100, 0x7, 24,
                                           (1638400, 10000),
                                           (3276800, 20000),
                                           (7864320, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x33, 24,
                                           (1638400, 10000),
                                           (3276800, 20000),
                                           (4915200, 30000),
                                           (4259840, 40000)),
                  test_streams.Simple_Sine(5000, 44100, 0x37, 24,
                                           (1638400, 10000),
                                           (2293760, 15000),
                                           (2949120, 20000),
                                           (3276800, 25000),
                                           (3604480, 30000)),
                  test_streams.Simple_Sine(5000, 44100, 0x3F, 24,
                                           (1638400, 10000),
                                           (2949120, 15000),
                                           (4259840, 20000),
                                           (5570560, 25000),
                                           (6881280, 30000),
                                           (7864320, 35000))]:
            test_python_reader(g, 5000)

        # test wasted BPS
        test_python_reader(test_streams.WastedBPS16(1000), 1000)

        # test fractional blocks
        for pcm_frames in [46078, 46079, 46080, 46081, 46082]:
            test_python_reader(
                MD5_Reader(
                    EXACT_RANDOM_PCM_Reader(
                        pcm_frames=pcm_frames,
                        sample_rate=44100,
                        channels=2,
                        bits_per_sample=16)),
                pcm_frames)

    @FORMAT_TTA
    def test_clean(self):
        # check TTA file with double ID3 tags

        from audiotools.text import CLEAN_REMOVE_DUPLICATE_ID3V2

        original_size = os.path.getsize("tta-id3-2.tta")

        track = audiotools.open("tta-id3-2.tta")

        # ensure second ID3 tag is ignored
        self.assertEqual(track.get_metadata().track_name, u"Title1")

        # ensure duplicate ID3v2 tag is detected and removed
        fixes = track.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_DUPLICATE_ID3V2])
        temp = tempfile.NamedTemporaryFile(suffix=".tta")
        try:
            fixes = track.clean(temp.name)
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_DUPLICATE_ID3V2])
            track2 = audiotools.open(temp.name)
            self.assertEqual(track2.get_metadata(), track.get_metadata())
            # ensure new file is exactly one tag smaller
            # and the padding is preserved in the old tag
            self.assertEqual(os.path.getsize(temp.name),
                             original_size - 0x46A)
        finally:
            temp.close()


class SineStreamTest(unittest.TestCase):
    @FORMAT_SINES
    def test_init(self):
        from audiotools.decoders import Sine_Mono
        from audiotools.decoders import Sine_Stereo
        from audiotools.decoders import Sine_Simple

        # ensure that failed inits don't make Python explode
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
