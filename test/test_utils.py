#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

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
import subprocess
from io import BytesIO, StringIO
import unicodedata
import tempfile
import os
import os.path
import shutil
import time
import test_streams
from hashlib import md5
from sys import version_info

from test import (parser, BLANK_PCM_Reader, Combinations, Possibilities,
                  EXACT_BLANK_PCM_Reader, EXACT_SILENCE_PCM_Reader,
                  RANDOM_PCM_Reader, EXACT_RANDOM_PCM_Reader,
                  TEST_COVER1, TEST_COVER2, TEST_COVER3, TEST_COVER4,
                  HUGE_BMP)


PY3 = version_info[0] >= 3


def do_nothing(self):
    pass


# add a bunch of decorator metafunctions like LIB_CORE
# which can be wrapped around individual tests as needed
for section in parser.sections():
    for option in parser.options(section):
        if parser.getboolean(section, option):
            vars()["{}_{}".format(section.upper(), option.upper())] = \
                lambda function: function
        else:
            vars()["{}_{}".format(section.upper(), option.upper())] = \
                lambda function: do_nothing


class UtilTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.line_checks = []

    # takes a list of argument strings
    # returns a returnval integer
    # self.stdout and self.stderr are set to file-like BytesIO objects
    def __run_app__(self, arguments):
        sub = subprocess.Popen(arguments,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

        self.stdout = StringIO(sub.stdout.read().decode("utf-8"))
        sub.stdout.close()
        self.stderr = StringIO(sub.stderr.read().decode("utf-8"))
        sub.stderr.close()

        returnval = sub.wait()
        # if returnval != 0:
        #     import sys
        #     from os import linesep
        #     sys.stderr.write(self.stdout.getvalue())
        #     sys.stderr.write(linesep)
        #     sys.stderr.write(self.stderr.getvalue())
        #     sys.stderr.write(linesep)
        return returnval

    def __add_check__(self, stream, unicode_string):
        self.line_checks.append((stream, unicode_string))

    def __run_checks__(self):
        for (stream, expected_output) in self.line_checks:
            stream_line = unicodedata.normalize(
                'NFC',
                getattr(self, stream).readline())
            expected_line = unicodedata.normalize(
                'NFC',
                expected_output) + os.linesep
            self.assertEqual(
                stream_line,
                expected_line,
                "{!r} != {!r}".format(stream_line, expected_line))
        self.line_checks = []

    def __clear_checks__(self):
        self.line_checks = []

    def __queue_output__(self, s):
        self.__add_check__("stdout", s)

    def __check_output__(self, s):
        self.__queue_output__(s)
        self.__run_checks__()

    def __queue_info__(self, s):
        self.__add_check__("stderr", s)

    def __check_info__(self, s):
        self.__queue_info__(s)
        self.__run_checks__()

    def __queue_error__(self, s):
        self.__add_check__("stderr", u"*** Error: " + s)

    def __check_error__(self, s):
        self.__queue_error__(s)
        self.__run_checks__()

    def __queue_warning__(self, s):
        self.__add_check__("stderr", u"*** Warning: " + s)

    def __check_warning__(self, s):
        self.__queue_warning__(s)
        self.__run_checks__()


class audiotools_config(UtilTest):
    @UTIL_AUDIOTOOLS_CONFIG
    def test_version(self):
        self.assertEqual(self.__run_app__(["audiotools-config",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    @UTIL_AUDIOTOOLS_CONFIG
    def test_execution(self):
        self.assertEqual(self.__run_app__(["audiotools-config"]), 0)


class cdda2track(UtilTest):
    @UTIL_CDDA2TRACK
    def setUp(self):
        self.type = audiotools.FlacAudio
        self.quality = "1"

        self.input_dir = tempfile.mkdtemp()

        self.stream = test_streams.Sine16_Stereo(793800, 44100,
                                                 8820.0, 0.70,
                                                 4410.0, 0.29, 1.0)

        self.cue_file = os.path.join(self.input_dir, "CDImage.cue")
        self.bin_file = os.path.join(self.input_dir, "CDImage.bin")

        with open(self.cue_file, "wb") as f:
            f.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')

        with open(self.bin_file, "wb") as f:
            audiotools.transfer_framelist_data(self.stream, f.write)

        self.output_dir = tempfile.mkdtemp()
        self.format = "%(track_number)2.2d.%(suffix)s"

        self.cwd_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.cwd_dir)

        self.unwritable_dir = tempfile.mkdtemp()
        os.chmod(self.unwritable_dir, 0)

        self.output_cue = os.path.join(self.output_dir, "CDImage.cue")
        self.unwritable_output_cue = os.path.join(self.unwritable_dir,
                                                  "CDImage.cue")

    @UTIL_CDDA2TRACK
    def tearDown(self):
        from shutil import rmtree

        os.chdir(self.original_dir)

        rmtree(self.input_dir)
        rmtree(self.output_dir)
        rmtree(self.cwd_dir)
        os.chmod(self.unwritable_dir, 0o700)
        rmtree(self.unwritable_dir)

    @UTIL_CDDA2TRACK
    def test_version(self):
        self.assertEqual(self.__run_app__(["cdda2track",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def populate_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]
        for option in options:
            if option == '-t':
                populated.append(option)
                populated.append(self.type.NAME)
            elif option == '-q':
                populated.append(option)
                populated.append(self.quality)
            elif option == '-d':
                populated.append(option)
                populated.append(self.output_dir)
            elif option == '--cue':
                populated.append(option)
                populated.append(self.output_cue)
            elif option == '--format':
                populated.append(option)
                populated.append(self.format)
            elif option == '--album-number':
                populated.append(option)
                populated.append(str(8))
            elif option == '--album-total':
                populated.append(option)
                populated.append(str(9))
            else:
                populated.append(option)
        return populated

    def clean_output_dirs(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))

    @UTIL_CDDA2TRACK
    def test_options(self):
        from audiotools.text import (ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     LAB_CD2TRACK_PROGRESS,
                                     RG_REPLAYGAIN_ADDED,
                                     LAB_CDDA2TRACK_WROTE_CUESHEET)

        all_options = ["-t", "-q", "-d", "--format",
                       "--album-number", "--album-total", "--cue"]
        for count in range(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                options = self.populate_options(options)

                if "-t" in options:
                    output_type = self.type
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    ("1" not in output_type.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["cdda2track", "-V", "normal",
                                          "-c", self.cue_file] +
                                         options), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality="1", type=output_type.NAME))
                    continue

                self.assertEqual(
                    self.__run_app__(["cdda2track", "-V", "normal",
                                      "-c", self.cue_file] +
                                     options), 0)

                if "--format" in options:
                    output_format = self.format
                else:
                    output_format = None

                if "-d" in options:
                    output_dir = self.output_dir
                else:
                    output_dir = "."

                base_metadata = audiotools.MetaData(track_total=3)
                if "--album-number" in options:
                    base_metadata.album_number = 8
                if "--album-total" in options:
                    base_metadata.album_total = 9

                output_filenames = []
                for i in range(3):
                    base_metadata.track_number = i + 1
                    output_filenames.append(
                        output_type.track_name(
                            "",
                            base_metadata,
                            output_format))

                # check that the output is being generated correctly
                for (i, path) in enumerate(output_filenames):
                    self.__check_info__(
                        audiotools.output_progress(
                            LAB_CD2TRACK_PROGRESS.format(
                                track_number=i + 1,
                                filename=audiotools.Filename(
                                    os.path.join(output_dir, path))),
                            i + 1, len(output_filenames)))

                # check that ReplayGain was written, if necessary
                if "-t" in options:
                    self.__check_info__(RG_REPLAYGAIN_ADDED)
                elif (output_type.supports_replay_gain() and
                      audiotools.ADD_REPLAYGAIN):
                    self.__check_info__(RG_REPLAYGAIN_ADDED)

                # check that cuesheet was generated correctly, if necessary
                if "--cue" in options:
                    self.__check_info__(
                        LAB_CDDA2TRACK_WROTE_CUESHEET.format(self.output_cue))

                    sheet = audiotools.read_sheet(self.cue_file)
                    cue = audiotools.read_sheet(self.output_cue)

                    self.assertEqual(sheet.pre_gap(), cue.pre_gap())

                    for track in sheet:
                        track_number = track.number()

                        self.assertEqual(sheet.track_offset(track_number),
                                         cue.track_offset(track_number))

                        self.assertEqual(sheet.track_length(track_number),
                                         cue.track_length(track_number))

                # rip log is generated afterward as a table
                # FIXME - check table of rip log?

                # make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.assertEqual(len(output_tracks), 3)
                self.stream.reset()
                self.assertTrue(
                    audiotools.pcm_cmp(
                        audiotools.PCMCat([t.to_pcm() for t in output_tracks]),
                        self.stream))

                # make sure metadata fits our expectations
                for i in range(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if metadata is not None:
                        self.assertEqual(metadata.track_name, None)
                        self.assertEqual(metadata.album_name, None)
                        self.assertEqual(metadata.artist_name, None)

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)

                        if "--album-number" in options:
                            self.assertEqual(metadata.album_number, 8)
                        else:
                            self.assertEqual(metadata.album_number, None)

                        if "--album-total" in options:
                            self.assertEqual(metadata.album_total, 9)
                        else:
                            self.assertEqual(metadata.album_total, None)

    @UTIL_CDDA2TRACK
    def test_unicode(self):
        from shutil import rmtree

        dirs = [d if PY3 else d.encode("UTF-8") for d in
                [u"testdir", u'abc\xe0\xe7\xe8\u3041\u3044\u3046']]

        formats = [f if PY3 else f.encode("UTF-8") for f in
                   [u"%(track_number)d.%(suffix)s",
                    u'%(track_number)d - abc\xe0\xe7\xe8\u3041\u3044\u3046.%(suffix)s']]

        for (output_directory,
             format_string) in Possibilities(dirs, formats):
            if os.path.isdir(output_directory):
                rmtree(output_directory)

            self.assertEqual(
                self.__run_app__(
                    ["cdda2track", "-c", self.cue_file,
                     "--type", "flac",
                     "--format", format_string,
                     "--dir", output_directory]), 0)

            tracks = [audiotools.open(
                      os.path.join(output_directory,
                                   format_string % {"track_number": i,
                                                    "suffix": "flac"}))
                      for i in range(1, 4)]

            self.assertEqual(sum([t.total_frames() for t in tracks]),
                             793800)

            if os.path.isdir(output_directory):
                rmtree(output_directory)

    def populate_bad_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]

        for option in sorted(options):
            if option == '-t':
                populated.append(option)
                populated.append("foo")
            elif option == '-q':
                populated.append(option)
                populated.append("bar")
            elif option == '-d':
                populated.append(option)
                populated.append(self.unwritable_dir)
            elif option == '--cue':
                populated.append(option)
                populated.append(self.unwritable_output_cue)
            elif option == '--format':
                populated.append(option)
                populated.append("%(foo)s.%(suffix)s")
            elif option == '--album-number':
                populated.append(option)
                populated.append("foo")
            elif option == '--album-total':
                populated.append(option)
                populated.append("bar")
            else:
                populated.append(option)

        return populated

    @UTIL_CDDA2TRACK
    def test_errors(self):
        from audiotools.text import (ERR_DUPLICATE_OUTPUT_FILE,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_UNKNOWN_FIELD,
                                     LAB_SUPPORTED_FIELDS,
                                     ERR_ENCODING_ERROR,
                                     ERR_OPEN_IOERROR,
                                     LAB_CD2TRACK_PROGRESS,
                                     RG_REPLAYGAIN_ADDED)

        self.assertEqual(
            self.__run_app__(["cdda2track", "-c", self.cue_file,
                              "--format=foo"]), 1)
        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE.format(audiotools.Filename("foo")))

        all_options = ["-t", "-q", "-d", "--format",
                       "--album-number", "--album-total", "--cue"]
        for count in range(1, len(all_options) + 1):
            for options in Combinations(all_options, count):

                options = self.populate_bad_options(options)

                if "-t" in options:
                    self.assertEqual(
                        self.__run_app__(["cdda2track", "-c", self.cue_file] +
                                         options),
                        2)
                    continue
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("--album-number" in options) or
                    ("--album-total" in options)):
                    self.assertEqual(
                        self.__run_app__(["cdda2track", "-c", self.cue_file] +
                                         options),
                        2)
                    continue

                self.assertEqual(
                    self.__run_app__(["cdda2track", "-c", self.cue_file] +
                                     options),
                    1)

                if "-q" in options:
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality="bar", type=audiotools.DEFAULT_TYPE))
                    continue

                if "--format" in options:
                    self.__check_error__(ERR_UNKNOWN_FIELD.format("foo"))
                    self.__check_info__(LAB_SUPPORTED_FIELDS)
                    for field in sorted(audiotools.MetaData.FIELDS +
                                        ("album_track_number", "suffix")):
                        if field == 'track_number':
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    self.__check_info__(u"%(basename)s")
                    continue

                if "-d" in options:
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_type.track_name(
                            "",
                            audiotools.MetaData(track_number=1,
                                                track_total=3)))
                    self.__check_error__(
                        ERR_ENCODING_ERROR.format(
                            audiotools.Filename(output_path)))
                    continue

                if "--cue" in options:
                    # files encode correctly
                    if "--format" in options:
                        output_format = self.format
                    else:
                        output_format = None

                    if "-d" in options:
                        output_dir = self.output_dir
                    else:
                        output_dir = "."

                    base_metadata = audiotools.MetaData(track_total=3)
                    if "--album-number" in options:
                        base_metadata.album_number = 8
                    if "--album-total" in options:
                        base_metadata.album_total = 9

                    output_filenames = []
                    for i in range(3):
                        base_metadata.track_number = i + 1
                        output_filenames.append(
                            output_type.track_name(
                                "",
                                base_metadata,
                                output_format))

                    for (i, path) in enumerate(output_filenames):
                        self.__check_info__(
                            audiotools.output_progress(
                                LAB_CD2TRACK_PROGRESS.format(
                                    track_number=i + 1,
                                    filename=audiotools.Filename(
                                        os.path.join(output_dir, path))),
                                i + 1, len(output_filenames)))

                    # ReplayGain applied correctly
                    if "-t" in options:
                        self.__check_info__(RG_REPLAYGAIN_ADDED)
                    elif (output_type.supports_replay_gain() and
                          audiotools.ADD_REPLAYGAIN):
                        self.__check_info__(RG_REPLAYGAIN_ADDED)

                    # cuesheet error comes up afterward
                    self.__check_error__(
                        ERR_OPEN_IOERROR.format(self.unwritable_output_cue))

                    continue


class cdda2track_pregap(UtilTest):
    def setUp(self):
        self.cuesheet = b'FILE "usandthem.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    INDEX 00 00:00:00\r\n    INDEX 01 00:00:33\r\n  TRACK 02 AUDIO\r\n    INDEX 01 08:13:33\r\n  TRACK 03 AUDIO\r\n    INDEX 00 13:24:33\r\n    INDEX 01 13:27:33\r\n  TRACK 04 AUDIO\r\n    INDEX 00 21:53:34\r\n    INDEX 01 21:55:33\r\n  TRACK 05 AUDIO\r\n    INDEX 00 27:20:35\r\n    INDEX 01 27:22:33\r\n  TRACK 06 AUDIO\r\n    INDEX 00 31:24:34\r\n    INDEX 01 31:26:33\r\n  TRACK 07 AUDIO\r\n    INDEX 00 38:09:33\r\n    INDEX 01 38:12:33\r\n  TRACK 08 AUDIO\r\n    INDEX 00 43:21:33\r\n    INDEX 01 43:23:33\r\n  TRACK 09 AUDIO\r\n    INDEX 00 49:47:33\r\n    INDEX 01 49:49:33\r\n  TRACK 10 AUDIO\r\n    INDEX 00 61:23:33\r\n    INDEX 01 61:27:33\r\n'
        self.pre_gap_length = 19404
        self.track_lengths = [21741300,
                              13847400,
                              22402800,
                              14420700,
                              10760400,
                              17904600,
                              13715100,
                              17022600,
                              30781800,
                              28312200]

    @UTIL_CDDA2TRACK
    def test_empty_pre_gap(self):
        from shutil import rmtree

        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        try:
            # populate cuesheet and bin file with empty pre-gap
            cue_file = os.path.join(input_dir, "CDImage.cue")
            bin_file = os.path.join(input_dir, "CDImage.bin")
            with open(cue_file, "wb") as f:
                f.write(self.cuesheet)
            with open(bin_file, "wb") as f:
                f.write(b"\x00" * self.pre_gap_length * 2 * 2)
                for track_length in self.track_lengths:
                    f.write(os.urandom(track_length * 2 * 2))

            # extract tracks with cdda2track
            self.assertEqual(
                self.__run_app__(["cdda2track", "-V", "quiet",
                                  "--no-musicbrainz",
                                  "--no-freedb",
                                  "-d", output_dir,
                                  "-c", cue_file,
                                  "-t", "wav",
                                  "--format=%(track_number)2.2d.wav"]),
                0)

            with audiotools.PCMFileReader(file=open(bin_file, "rb"),
                                          sample_rate=44100,
                                          channels=2,
                                          channel_mask=0x3,
                                          bits_per_sample=16) as binreader:

                # ensure there is no pre-gap
                self.assertFalse(
                    os.path.isfile(os.path.join(output_dir, "00.wav")))

                binreader.read(self.pre_gap_length)

                # ensure tracks match data in bin file
                for i, length in enumerate(self.track_lengths, 1):
                    output_track = audiotools.open(
                        os.path.join(output_dir,
                                     "{:02d}.wav".format(i))).to_pcm()

                    self.assertIsNone(audiotools.pcm_frame_cmp(
                        audiotools.LimitedPCMReader(binreader, length),
                        output_track))
        finally:
            rmtree(input_dir)
            rmtree(output_dir)

    @UTIL_CDDA2TRACK
    def test_popualated_pre_gap(self):
        from shutil import rmtree

        input_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        try:
            # populate cuesheet and bin file with empty pre-gap
            cue_file = os.path.join(input_dir, "CDImage.cue")
            bin_file = os.path.join(input_dir, "CDImage.bin")
            with open(cue_file, "wb") as f:
                f.write(self.cuesheet)
            with open(bin_file, "wb") as f:
                f.write(os.urandom(self.pre_gap_length * 2 * 2))
                for track_length in self.track_lengths:
                    f.write(os.urandom(track_length * 2 * 2))

            # extract tracks with cdda2track
            self.assertEqual(
                self.__run_app__(["cdda2track", "-V", "quiet",
                                  "--no-musicbrainz",
                                  "--no-freedb",
                                  "-d", output_dir,
                                  "-c", cue_file,
                                  "-t", "wav",
                                  "--format=%(track_number)2.2d.wav"]),
                0)

            with audiotools.PCMFileReader(file=open(bin_file, "rb"),
                                          sample_rate=44100,
                                          channels=2,
                                          channel_mask=0x3,
                                          bits_per_sample=16) as binreader:

                # ensure there is a pre-gap
                self.assertTrue(
                    os.path.isfile(os.path.join(output_dir, "00.wav")))

                output_track = audiotools.open(
                    os.path.join(output_dir, "00.wav")).to_pcm()

                self.assertIsNone(audiotools.pcm_frame_cmp(
                    audiotools.LimitedPCMReader(binreader, self.pre_gap_length),
                    output_track))

                # ensure tracks match data in bin file
                for i, length in enumerate(self.track_lengths, 1):
                    output_track = audiotools.open(
                        os.path.join(output_dir,
                                     "{:02d}.wav".format(i))).to_pcm()

                    self.assertIsNone(audiotools.pcm_frame_cmp(
                        audiotools.LimitedPCMReader(binreader, length),
                        output_track))
        finally:
            rmtree(input_dir)
            rmtree(output_dir)


class cddainfo(UtilTest):
    @UTIL_CDDAINFO
    def test_version(self):
        self.assertEqual(self.__run_app__(["cddainfo",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))


class cddaplay(UtilTest):
    @UTIL_CDDAPLAY
    def test_version(self):
        self.assertEqual(self.__run_app__(["cddaplay",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))


class coverdump(UtilTest):
    @UTIL_COVERDUMP
    def setUp(self):
        self.type = audiotools.FlacAudio

        self.input_file1 = tempfile.NamedTemporaryFile(
            suffix="." + self.type.SUFFIX)
        self.track1 = self.type.from_pcm(self.input_file1.name,
                                         BLANK_PCM_Reader(1))
        self.input_file2 = tempfile.NamedTemporaryFile(
            suffix="." + self.type.SUFFIX)
        self.track2 = self.type.from_pcm(self.input_file2.name,
                                         BLANK_PCM_Reader(1))

        self.prefix = "PREFIX_"

        self.output_dir = tempfile.mkdtemp()
        self.cwd_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.cwd_dir)

        metadata = audiotools.MetaData(track_name=u"Track")
        self.images1 = []
        for i in range(10):
            with open(os.path.join(self.original_dir,
                                   "{:02d}.png".format(i + 1)), "rb") as f:
                img = audiotools.Image.new(f.read(), u"", i // 2)
                self.images1.append(img)
                metadata.add_image(img)

        self.track1.set_metadata(metadata)

        metadata = audiotools.MetaData(track_name=u"Track")
        self.images2 = []
        for i in range(5):
            with open(os.path.join(self.original_dir,
                                   "{:02d}.png".format(i + 11)), "rb") as f:
                img = audiotools.Image.new(f.read(), u"", i)
                self.images2.append(img)
                metadata.add_image(img)

        self.track2.set_metadata(metadata)

        self.filename_types = ("front_cover", "back_cover",
                               "leaflet", "media", "other")

    @UTIL_COVERDUMP
    def tearDown(self):
        os.chdir(self.original_dir)

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))
        os.rmdir(self.cwd_dir)

        self.input_file1.close()
        self.input_file2.close()

    @UTIL_COVERDUMP
    def test_version(self):
        self.assertEqual(self.__run_app__(["coverdump",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def clean_output_dir(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

    def populate_options(self, options):
        populated = []
        for option in options:
            if option == "-d":
                populated.append(option)
                populated.append(self.output_dir)
            elif option == "-p":
                populated.append(option)
                populated.append(self.prefix)
            else:
                populated.append(option)

        return populated

    @UTIL_COVERDUMP
    def test_options(self):
        from audiotools.text import LAB_ENCODE

        all_options = ["-d", "-p"]
        for count in range(len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options)
                self.clean_output_dir()
                self.assertEqual(
                    self.__run_app__(["coverdump", "-V", "normal",
                                      self.track1.filename] + options),
                    0)

                if "-d" in options:
                    output_directory = self.output_dir
                else:
                    output_directory = "."

                template = "%(prefix)s%(filename)s%(filenum)2.2d.%(suffix)s"

                for (i, image) in enumerate(self.images1):
                    if "-p" in options:
                        output_filename = template % {
                            "prefix": "PREFIX_",
                            "filename": self.filename_types[image.type],
                            "filenum": (i % 2) + 1,
                            "suffix": "png"}
                    else:
                        output_filename = template % {
                            "prefix": "",
                            "filename": self.filename_types[image.type],
                            "filenum": (i % 2) + 1,
                            "suffix": "png"}

                    if "-d" in options:
                        output_path = os.path.join(self.output_dir,
                                                   output_filename)
                    else:
                        output_path = os.path.join(".", output_filename)

                    self.__check_info__(
                        LAB_ENCODE.format(
                            source=audiotools.Filename(self.track1.filename),
                            destination=audiotools.Filename(output_path)))
                    with open(output_path, "rb") as f:
                        output_image = audiotools.Image.new(
                            f.read(), u"", i // 2)
                    self.assertEqual(output_image, image)

                self.clean_output_dir()
                self.assertEqual(
                    self.__run_app__(["coverdump", "-V", "normal",
                                      self.track2.filename] + options),
                    0)

                if "-d" in options:
                    output_directory = self.output_dir
                else:
                    output_directory = "."

                template = "%(prefix)s%(filename)s.%(suffix)s"

                for (i, image) in enumerate(self.images2):
                    if "-p" in options:
                        output_filename = template % {
                            "prefix": "PREFIX_",
                            "filename": self.filename_types[image.type],
                            "suffix": "png"}
                    else:
                        output_filename = template % {
                            "prefix": "",
                            "filename": self.filename_types[image.type],
                            "suffix": "png"}

                    if "-d" in options:
                        output_path = os.path.join(self.output_dir,
                                                   output_filename)
                    else:
                        output_path = os.path.join(".", output_filename)

                    self.__check_info__(
                        LAB_ENCODE.format(
                            source=audiotools.Filename(self.track2.filename),
                            destination=audiotools.Filename(output_path)))
                    with open(output_path, "rb") as f:
                        output_image = audiotools.Image.new(
                            f.read(), u"", i)
                    self.assertEqual(output_image, image)

    @UTIL_COVERDUMP
    def test_unicode(self):
        from shutil import rmtree

        dirs = [d if PY3 else d.encode("UTF-8") for d in
                [u"testdir",
                 u'abc\xe0\xe7\xe8\u3041\u3044\u3046']]

        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"test.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        prefixes = [p if ((p is None) or PY3) else p.encode("UTF-8")
                    for p in [None,
                              u"prefix_",
                              u'abc\xe0\xe7\xe8\u3041\u3044\u3046_']]

        for (output_directory,
             file_path,
             prefix) in Possibilities(dirs, filenames, prefixes):
            if os.path.isdir(output_directory):
                rmtree(output_directory)
            if os.path.isfile(file_path):
                os.unlink(file_path)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))
            metadata = track.get_metadata()
            metadata.add_image(audiotools.Image.new(TEST_COVER1,
                                                    u"",
                                                    0))
            track.update_metadata(metadata)

            self.assertEqual(
                self.__run_app__(
                    ["coverdump",
                     "--dir", output_directory] +
                    (["--prefix", prefix] if prefix is not None else []) +
                    [file_path]), 0)

            self.assertEqual(
                os.path.isfile(
                    os.path.join(output_directory,
                                 (prefix if prefix is not None else "") +
                                 "front_cover.jpg")), True)

            if os.path.isdir(output_directory):
                rmtree(output_directory)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    @UTIL_COVERDUMP
    def test_errors(self):
        from audiotools.text import (ERR_1_FILE_REQUIRED,
                                     ERR_ENCODING_ERROR,
                                     ERR_OUTPUT_IS_INPUT)

        # check no input files
        self.assertEqual(
            self.__run_app__(["coverdump", "-V", "normal"]), 2)

        # check multiple input files
        self.assertEqual(
            self.__run_app__(["coverdump", "-V", "normal",
                              self.track1.filename, self.track2.filename]), 1)

        self.__check_error__(ERR_1_FILE_REQUIRED)

        # check unwritable output dir
        old_mode = os.stat(self.output_dir).st_mode
        try:
            os.chmod(self.output_dir, 0)
            self.assertEqual(
                self.__run_app__(["coverdump", "-V", "normal",
                                  "-d", self.output_dir,
                                  self.track1.filename]), 1)
            self.__check_error__(
                ERR_ENCODING_ERROR.format(
                    audiotools.Filename(
                        os.path.join(self.output_dir, "front_cover01.png"))))
        finally:
            os.chmod(self.output_dir, old_mode)

        # check unwritable cwd
        old_mode = os.stat(self.cwd_dir).st_mode
        try:
            os.chmod(self.cwd_dir, 0)
            self.assertEqual(
                self.__run_app__(["coverdump", "-V", "normal",
                                  self.track1.filename]), 1)
            self.__check_error__(
                ERR_ENCODING_ERROR.format(
                    audiotools.Filename("front_cover01.png")))

        finally:
            os.chmod(self.cwd_dir, old_mode)

        # check input file same as output file
        track = audiotools.FlacAudio.from_pcm(
            os.path.join(self.output_dir, "front_cover.jpg"),
            BLANK_PCM_Reader(1))
        metadata = track.get_metadata()
        metadata.add_image(audiotools.Image.new(TEST_COVER1, u"", 0))
        track.update_metadata(metadata)

        self.assertEqual(
            self.__run_app__(["coverdump", "-V", "normal",
                              "-d", self.output_dir, track.filename]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT.format(audiotools.Filename(track.filename)))


class covertag(UtilTest):
    @UTIL_COVERTAG
    def setUp(self):
        track_file_base = tempfile.NamedTemporaryFile()
        self.initial_metadata = audiotools.MetaData(
            track_name=u"Name 1",
            track_number=1,
            track_total=2,
            album_name=u"Album 1",
            artist_name=u"Artist 1",
            album_number=3,
            album_total=4,
            ISRC=u'ABCD00000000',
            comment=u"Comment 1")

        self.image = audiotools.Image.new(TEST_COVER1, u"", 0)
        self.initial_metadata.add_image(self.image)

        track_base = audiotools.FlacAudio.from_pcm(
            track_file_base.name,
            BLANK_PCM_Reader(1))
        track_base.set_metadata(self.initial_metadata)
        with open(track_base.filename, 'rb') as f:
            self.track_data = f.read()
        track_file_base.close()

        self.track_file = tempfile.NamedTemporaryFile()

        self.front_cover1 = tempfile.NamedTemporaryFile(suffix=".png")
        self.front_cover1.write(TEST_COVER4)
        self.front_cover1.flush()

        self.front_cover2 = tempfile.NamedTemporaryFile(suffix=".jpg")
        self.front_cover2.write(TEST_COVER3)
        self.front_cover2.flush()

        self.back_cover = tempfile.NamedTemporaryFile(suffix=".png")
        self.back_cover.write(TEST_COVER2)
        self.back_cover.flush()

        self.leaflet = tempfile.NamedTemporaryFile(suffix=".jpg")
        self.leaflet.write(TEST_COVER1)
        self.leaflet.flush()

        self.media = tempfile.NamedTemporaryFile(suffix=".png")
        self.media.write(TEST_COVER2)
        self.media.flush()

        self.other = tempfile.NamedTemporaryFile(suffix=".png")
        self.other.write(TEST_COVER4)
        self.other.flush()

        self.front_cover1_image = audiotools.Image.new(
            TEST_COVER4, u"", 0)
        self.front_cover2_image = audiotools.Image.new(
            TEST_COVER3, u"", 0)
        self.back_cover_image = audiotools.Image.new(
            TEST_COVER2, u"", 1)
        self.leaflet_image = audiotools.Image.new(
            TEST_COVER1, u"", 2)
        self.media_image = audiotools.Image.new(
            TEST_COVER2, u"", 3)
        self.other_image = audiotools.Image.new(
            TEST_COVER4, u"", 4)

    @UTIL_COVERTAG
    def tearDown(self):
        self.track_file.close()
        self.front_cover1.close()
        self.front_cover2.close()
        self.back_cover.close()
        self.leaflet.close()
        self.media.close()
        self.other.close()

    @UTIL_COVERTAG
    def test_version(self):
        self.assertEqual(self.__run_app__(["covertag",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def populate_options(self, options):
        populated = []
        front_covers = [self.front_cover1.name, self.front_cover2.name]

        for option in sorted(options):
            if option == '--front-cover':
                populated.append(option)
                populated.append(front_covers.pop(0))
            elif option == '--back-cover':
                populated.append(option)
                populated.append(self.back_cover.name)
            elif option == '--leaflet':
                populated.append(option)
                populated.append(self.leaflet.name)
            elif option == '--media':
                populated.append(option)
                populated.append(self.media.name)
            elif option == '--other-image':
                populated.append(option)
                populated.append(self.other.name)
            else:
                populated.append(option)

        return populated

    @UTIL_COVERTAG
    def test_options(self):
        from audiotools.text import ERR_DUPLICATE_FILE

        # start out with a bit of sanity checking
        with open(self.track_file.name, 'wb') as f:
            f.write(self.track_data)

        track = audiotools.open(self.track_file.name)
        track.verify()
        metadata = track.get_metadata()
        self.assertEqual(metadata.images(),
                         [self.image])

        covertag_options = ['-r', '--front-cover', '--front-cover',
                            '--back-cover', '--leaflet', '--media',
                            '--other-image']

        # ensure tagging the same file twice triggers an error
        self.assertEqual(
            self.__run_app__(["covertag", "--front-cover",
                              self.front_cover1.name,
                              self.track_file.name,
                              self.track_file.name]), 1)
        self.__check_error__(
            ERR_DUPLICATE_FILE.format(
                audiotools.Filename(self.track_file.name)))

        for count in range(1, len(covertag_options) + 1):
            for options in Combinations(covertag_options, count):
                f = open(self.track_file.name, 'wb')
                f.write(self.track_data)
                f.close()

                options = self.populate_options(options)
                self.assertEqual(
                    self.__run_app__(["covertag"] +
                                     options +
                                     [self.track_file.name]), 0)

                track = audiotools.open(self.track_file.name)
                track.verify()
                metadata = track.get_metadata()

                if '-r' in options:
                    if options.count('--front-cover') == 0:
                        self.assertEqual(metadata.front_covers(),
                                         [])
                    elif options.count('--front-cover') == 1:
                        self.assertEqual(metadata.front_covers(),
                                         [self.front_cover1_image])
                    elif options.count('--front-cover') == 2:
                        self.assertEqual(metadata.front_covers(),
                                         [self.front_cover1_image,
                                          self.front_cover2_image])
                else:
                    if options.count('--front-cover') == 0:
                        self.assertEqual(metadata.front_covers(),
                                         [self.image])
                    elif options.count('--front-cover') == 1:
                        self.assertEqual(metadata.front_covers(),
                                         [self.image,
                                          self.front_cover1_image])
                    elif options.count('--front-cover') == 2:
                        self.assertEqual(metadata.front_covers(),
                                         [self.image,
                                          self.front_cover1_image,
                                          self.front_cover2_image])
                if '--back-cover' in options:
                    self.assertEqual(metadata.back_covers(),
                                     [self.back_cover_image])
                else:
                    self.assertEqual(metadata.back_covers(),
                                     [])
                if '--leaflet' in options:
                    self.assertEqual(metadata.leaflet_pages(),
                                     [self.leaflet_image])
                else:
                    self.assertEqual(metadata.leaflet_pages(),
                                     [])
                if '--media' in options:
                    self.assertEqual(metadata.media_images(),
                                     [self.media_image])
                else:
                    self.assertEqual(metadata.media_images(),
                                     [])
                if '--other-image' in options:
                    self.assertEqual(metadata.other_images(),
                                     [self.other_image])
                else:
                    self.assertEqual(metadata.other_images(),
                                     [])

    @UTIL_COVERTAG
    def test_unicode(self):
        from shutil import rmtree

        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"test.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        image_paths = [f if PY3 else f.encode("UTF-8") for f in
                       [u"image.jpg",
                        u'abc\xe0\xe7\xe8\u3041\u3044\u3046.jpg']]

        for (file_path,
             option,
             image_path) in Possibilities(
            filenames, ["--front-cover",
                        "--back-cover",
                        "--leaflet",
                        "--media",
                        "--other-image"], image_paths):
            if os.path.isfile(file_path):
                os.unlink(file_path)
            if os.path.isfile(image_path):
                os.unlink(image_path)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))

            with open(image_path, "wb") as f:
                f.write(TEST_COVER1)

            self.assertEqual(
                self.__run_app__(
                    ["covertag", option, image_path, file_path]), 0)

            self.assertEqual(
                audiotools.open(file_path).get_metadata().images()[0].data,
                TEST_COVER1)

            if os.path.isfile(file_path):
                os.unlink(file_path)
            if os.path.isfile(image_path):
                os.unlink(image_path)


class covertag_errors(UtilTest):
    @UTIL_COVERTAG
    def test_bad_options(self):
        from audiotools.text import ERR_OPEN_IOERROR

        temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        temp_track_stat = os.stat(temp_track_file.name)[0]
        try:
            temp_track = audiotools.FlacAudio.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            self.assertEqual(
                self.__run_app__(["covertag",
                                  "--front-cover=/dev/null/foo.jpg",
                                  temp_track.filename]), 1)
            self.__check_error__(
                ERR_OPEN_IOERROR.format(
                    audiotools.Filename("/dev/null/foo.jpg")))
        finally:
            os.chmod(temp_track_file.name, temp_track_stat)
            temp_track_file.close()

    @UTIL_COVERTAG
    def test_oversized_metadata(self):
        from bz2 import decompress

        for audio_class in [audiotools.FlacAudio]:
            tempflac = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            big_bmp = tempfile.NamedTemporaryFile(suffix=".bmp")
            try:
                flac = audio_class.from_pcm(
                    tempflac.name,
                    BLANK_PCM_Reader(5))

                flac.set_metadata(audiotools.MetaData(track_name=u"Foo"))

                big_bmp.write(decompress(HUGE_BMP))
                big_bmp.flush()

                orig_md5 = md5()
                audiotools.transfer_framelist_data(flac.to_pcm(),
                                                   orig_md5.update)

                # ensure that setting a big image via covertag
                # doesn't break the file
                subprocess.call(["covertag", "-V", "quiet",
                                 "--front-cover={}".format(big_bmp.name),
                                 flac.filename])
                new_md5 = md5()
                audiotools.transfer_framelist_data(flac.to_pcm(),
                                                   new_md5.update)
                self.assertEqual(orig_md5.hexdigest(),
                                 new_md5.hexdigest())
            finally:
                tempflac.close()
                big_bmp.close()


class track2cdda(UtilTest):
    @UTIL_TRACK2CDDA
    def setUp(self):
        # if the user has an ~/.audiotools.cfg file, save it and its mode
        self.audiotools_cfg_path = os.path.expanduser("~/.audiotools.cfg")
        if os.path.isfile(self.audiotools_cfg_path):
            with open(self.audiotools_cfg_path, "rb") as f:
                self.audiotools_cfg = f.read()
            self.audiotools_cfg_mode = os.stat(
                self.audiotools_cfg_path).st_mode
        else:
            self.audiotools_cfg = None
            self.audiotools_cfg_mode = None

        # setup a couple of test tracks from a single big sine wave
        sine = audiotools.BufferedPCMReader(
            test_streams.Sine16_Stereo(12397980 + 10862124, 44100,
                                       441.0, 0.50,
                                       4410.0, 0.49, 1.0))

        self.track1 = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track2 = tempfile.NamedTemporaryFile(suffix=".flac")

        track1 = audiotools.FlacAudio.from_pcm(
            self.track1.name,
            audiotools.LimitedPCMReader(sine, 12397980),
            "0")

        track1.set_metadata(audiotools.MetaData(track_number=1,
                                                track_total=2))

        track2 = audiotools.FlacAudio.from_pcm(
            self.track2.name,
            audiotools.LimitedPCMReader(sine, 10862124),
            "0")

        track2.set_metadata(audiotools.MetaData(track_number=2,
                                                track_total=2))

        # setup a test cuesheet
        self.cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet.write(b'FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 04:36:50\n    INDEX 01 04:41:10\n')
        self.cuesheet.flush()

    @UTIL_TRACK2CDDA
    def tearDown(self):
        if ((self.audiotools_cfg is not None) and
            (self.audiotools_cfg_mode is not None)):
            # if saved .audiotools.cfg file
            # rewrite it to disk and restore its mode
            with open(self.audiotools_cfg_path, "wb") as f:
                f.write(self.audiotools_cfg)
            os.chmod(self.audiotools_cfg_path, self.audiotools_cfg_mode)
        else:
            # otherwise, remove any temporary file
            if os.path.isfile(self.audiotools_cfg_path):
                os.unlink(self.audiotools_cfg_path)

        self.track1.close()
        self.track2.close()
        self.cuesheet.close()

    @UTIL_TRACK2CDDA
    def test_version(self):
        self.assertEqual(self.__run_app__(["track2cdda",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    @UTIL_TRACK2CDDA
    def test_tracks_nocue(self):
        try:
            from pickle import load
        except ImportError:
            from cPickle import load

        # replace "cdrecord" with test program in config file
        config = audiotools.RawConfigParser()
        config.set_default("Binaries", "cdrecord",
                           os.path.abspath("test_cdrecord.py"))

        # check writing files track at a time with no write offset
        with open(self.audiotools_cfg_path, "w") as f:
            config.write(f)

        with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
            self.assertEqual(self.__run_app__(["track2cdda",
                                               "--cdrom",
                                               results_file.name,
                                               self.track1.name,
                                               self.track2.name]), 0)

            # both tracks should match
            with open(results_file.name, "rb") as f:
                self.assertIsNone(load(f))
                self.assertIsNone(load(f))

        # check writing files track at a time with positive write offset
        config.set_default("System", "cdrom_write_offset", "25")
        with open(self.audiotools_cfg_path, "w") as f:
            config.write(f)

        with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
            self.assertEqual(self.__run_app__(["track2cdda",
                                               "--cdrom",
                                               results_file.name,
                                               self.track1.name,
                                               self.track2.name]), 0)

            # both tracks should match
            with open(results_file.name, "rb") as f:
                self.assertIsNone(load(f))
                self.assertIsNone(load(f))

        # check writing files track at a time with negative write offset
        config.set_default("System", "cdrom_write_offset", "-25")
        with open(self.audiotools_cfg_path, "w") as f:
            config.write(f)

        with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
            self.assertEqual(self.__run_app__(["track2cdda",
                                               "--cdrom",
                                               results_file.name,
                                               self.track1.name,
                                               self.track2.name]), 0)

            # both tracks should match
            with open(results_file.name, "rb") as f:
                self.assertIsNone(load(f))
                self.assertIsNone(load(f))

    @UTIL_TRACK2CDDA
    def test_tracks_cue(self):
        try:
            from pickle import load
        except ImportError:
            from cPickle import load

        # replace "cdrdao" with test program in config file
        config = audiotools.RawConfigParser()
        config.set_default("Binaries", "cdrdao",
                           os.path.abspath("test_cdrdao.py"))

        # check writing files via cdrdao with no write offset
        with open(self.audiotools_cfg_path, "w") as f:
            config.write(f)

        with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
            self.assertEqual(self.__run_app__(["track2cdda",
                                               "--cdrom",
                                               results_file.name,
                                               "--cue",
                                               self.cuesheet.name,
                                               self.track1.name,
                                               self.track2.name]), 0)

            # both tracks should match
            with open(results_file.name, "rb") as f:
                self.assertIsNone(load(f))

        # check writing files via cdrdao with positive write offset
        config.set_default("System", "cdrom_write_offset", "25")
        with open(self.audiotools_cfg_path, "w") as f:
            config.write(f)

        with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
            self.assertEqual(self.__run_app__(["track2cdda",
                                               "--cdrom",
                                               results_file.name,
                                               "--cue",
                                               self.cuesheet.name,
                                               self.track1.name,
                                               self.track2.name]), 0)

            # both tracks should match
            with open(results_file.name, "rb") as f:
                self.assertIsNone(load(f))

        # check writing files via cdrdao with negative write offset
        config.set_default("System", "cdrom_write_offset", str(-25))
        with open(self.audiotools_cfg_path, "w") as f:
            config.write(f)

        with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
            self.assertEqual(self.__run_app__(["track2cdda",
                                               "--cdrom",
                                               results_file.name,
                                               "--cue",
                                               self.cuesheet.name,
                                               self.track1.name,
                                               self.track2.name]), 0)

            # both tracks should match
            with open(results_file.name, "rb") as f:
                self.assertIsNone(load(f))

    @UTIL_TRACK2CDDA
    def test_embedded_cuesheet(self):
        try:
            from pickle import load
        except ImportError:
            from cPickle import load

        with tempfile.NamedTemporaryFile(suffix=".flac") as combined_temp:
            combined_track = audiotools.FlacAudio.from_pcm(
                combined_temp.name,
                audiotools.PCMCat(
                    [audiotools.open(self.track1.name).to_pcm(),
                     audiotools.open(self.track2.name).to_pcm()]),
                "0")
            combined_track.set_cuesheet(
                audiotools.read_sheet(self.cuesheet.name))

            self.assertIsNotNone(combined_track.get_cuesheet())

            # replace "cdrdao" with test program in config file
            config = audiotools.RawConfigParser()
            config.set_default("Binaries", "cdrdao",
                               os.path.abspath("test_cdrdao.py"))

            # check writing files via cdrdao with no write offset
            with open(self.audiotools_cfg_path, "w") as f:
                config.write(f)

            with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
                self.assertEqual(self.__run_app__(["track2cdda",
                                                   "--cdrom",
                                                   results_file.name,
                                                   combined_track.filename]),
                                 0)

                # both tracks should match
                with open(results_file.name, "rb") as f:
                    self.assertIsNone(load(f))

            # check writing files via cdrdao with positive write offset
            config.set_default("System", "cdrom_write_offset", "25")
            with open(self.audiotools_cfg_path, "w") as f:
                config.write(f)

            with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
                self.assertEqual(self.__run_app__(["track2cdda",
                                                   "--cdrom",
                                                   results_file.name,
                                                   combined_track.filename]),
                                 0)

                # both tracks should match
                with open(results_file.name, "rb") as f:
                    self.assertIsNone(load(f))

            # check writing files via cdrdao with negative write offset
            config.set_default("System", "cdrom_write_offset", "-25")
            with open(self.audiotools_cfg_path, "w") as f:
                config.write(f)

            with tempfile.NamedTemporaryFile(suffix=".bin") as results_file:
                self.assertEqual(self.__run_app__(["track2cdda",
                                                   "--cdrom",
                                                   results_file.name,
                                                   combined_track.filename]),
                                 0)

                # both tracks should match
                with open(results_file.name, "rb") as f:
                    self.assertIsNone(load(f))


class track2track(UtilTest):
    @UTIL_TRACK2TRACK
    def setUp(self):
        # input format should be something other than the user's default
        # and should support embedded metadata
        for self.input_format in [audiotools.ALACAudio,
                                  audiotools.AiffAudio]:
            if self.input_format is not audiotools.DEFAULT_TYPE:
                break

        # output format shouldn't be the user's default, the input format
        # and should support embedded images and ReplayGain tags
        for self.output_format in [audiotools.FlacAudio,
                                   audiotools.WavPackAudio]:
            if self.input_format is not audiotools.DEFAULT_TYPE:
                break

        self.input_dir = tempfile.mkdtemp()
        self.track1 = self.input_format.from_pcm(
            os.path.join(self.input_dir,
                         "01.{}".format(self.input_format.SUFFIX)),
            BLANK_PCM_Reader(1))
        self.track_metadata = audiotools.MetaData(track_name=u"Track 1",
                                                  track_number=1,
                                                  album_name=u"Album",
                                                  artist_name=u"Artist")
        self.cover = audiotools.Image.new(TEST_COVER1, u"", 0)
        self.track_metadata.add_image(self.cover)

        self.track1.set_metadata(self.track_metadata)

        self.output_dir = tempfile.mkdtemp()
        self.output_file = tempfile.NamedTemporaryFile(
            suffix="." + self.output_format.SUFFIX)

        self.format = "%(track_number)2.2d - %(track_name)s.%(suffix)s"
        self.type = self.output_format.NAME
        self.quality = self.output_format.COMPRESSION_MODES[0]

        self.cwd_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.cwd_dir)

        self.unwritable_dir = tempfile.mkdtemp()
        os.chmod(self.unwritable_dir, 0)
        self.unwritable_file = \
            "/dev/null/foo.{}".format(self.output_format.SUFFIX)
        with open(os.path.join(
            self.input_dir,
            "broken.{}".format(self.input_format.SUFFIX)), "wb") as w:
            with open(self.track1.filename, "rb") as r:
                w.write(r.read()[0:-10])
        self.broken_track1 = audiotools.open(
            os.path.join(self.input_dir,
                         "broken.{}".format(self.input_format.SUFFIX)))

        # Why a static set of input/output arguments for each set of options?
        # Since track2track uses the standard interface for everything,
        # we're only testing that the options work.
        # The interface itself is tested at a lower level
        # in the test_core.py or test_formats.py modules.

    @UTIL_TRACK2TRACK
    def tearDown(self):
        from shutil import rmtree

        os.chdir(self.original_dir)

        rmtree(self.input_dir)
        rmtree(self.output_dir)
        rmtree(self.cwd_dir)

        self.output_file.close()

        os.chmod(self.unwritable_dir, 0o700)
        rmtree(self.unwritable_dir)

    def clean_output_dirs(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))

        f = open(self.output_file.name, "wb")
        f.close()

    @UTIL_TRACK2TRACK
    def test_version(self):
        self.assertEqual(self.__run_app__(["track2track",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def populate_options(self, options):
        populated = []

        for option in sorted(options):
            if option == '-t':
                populated.append(option)
                populated.append(self.type)
            elif option == '-q':
                populated.append(option)
                populated.append(self.quality)
            elif option == '-d':
                populated.append(option)
                populated.append(self.output_dir)
            elif option == '--format':
                populated.append(option)
                populated.append(self.format)
            elif option == '-o':
                populated.append(option)
                populated.append(self.output_file.name)
            elif option == '--sample-rate':
                populated.append(option)
                populated.append(str(48000))
            elif option == '--channels':
                populated.append(option)
                populated.append(str(1))
            elif option == '--bits-per-sample':
                populated.append(option)
                populated.append(str(8))
            else:
                populated.append(option)

        return populated

    def populate_bad_options(self, options):
        populated = []

        for option in sorted(options):
            if option == '-t':
                populated.append(option)
                populated.append("foo")
            elif option == '-q':
                populated.append(option)
                populated.append("bar")
            elif option == '-d':
                populated.append(option)
                populated.append(self.unwritable_dir)
            elif option == '--format':
                populated.append(option)
                populated.append("%(foo)s.%(suffix)s")
            elif option == '-o':
                populated.append(option)
                populated.append(self.unwritable_file)
            elif option == '-j':
                populated.append(option)
                populated.append(str(0))
            elif option == '--sample-rate':
                populated.append(option)
                populated.append(str(0))
            elif option == '--channels':
                populated.append(option)
                populated.append(str(0))
            elif option == '--bits-per-sample':
                populated.append(option)
                populated.append(str(0))
            else:
                populated.append(option)

        return populated

    @UTIL_TRACK2TRACK
    def test_options(self):
        from audiotools.text import (ERR_TRACK2TRACK_O_AND_D,
                                     ERR_TRACK2TRACK_O_AND_D_SUGGESTION,
                                     ERR_TRACK2TRACK_O_AND_FORMAT,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     LAB_ENCODE,
                                     RG_REPLAYGAIN_ADDED,
                                     RG_REPLAYGAIN_APPLIED)

        all_options = ["-t", "-q", "-d", "--format", "-o",
                       "--replay-gain", "--no-replay-gain",
                       "--sample-rate", "--channels", "--bits-per-sample"]

        for count in range(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                self.__clear_checks__()

                options = self.populate_options(options) + \
                    ["-V", "normal", "-j", "1", self.track1.filename]

                if ("-d" in options) and ("-o" in options):
                    # -d and -o trigger an error

                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 1)
                    self.__check_error__(ERR_TRACK2TRACK_O_AND_D)
                    self.__check_info__(ERR_TRACK2TRACK_O_AND_D_SUGGESTION)
                    continue

                if ("--format" in options) and ("-o" in options):
                    self.__queue_warning__(ERR_TRACK2TRACK_O_AND_FORMAT)

                if '-t' in options:
                    output_class = audiotools.TYPE_MAP[
                        options[options.index('-t') + 1]]
                elif "-o" in options:
                    output_class = self.output_format
                else:
                    output_class = audiotools.TYPE_MAP[
                        audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    (options[options.index("-q") + 1] not in
                     output_class.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality=options[options.index("-q") + 1],
                            type=output_class.NAME))
                    continue

                if '--format' in options:
                    output_format = options[options.index('--format') + 1]
                else:
                    output_format = None

                metadata = self.track1.get_metadata()

                if "-o" in options:
                    output_path = self.output_file.name
                elif "-d" in options:
                    output_path = os.path.join(
                        self.output_dir,
                        output_class.track_name("", metadata, output_format))
                else:
                    output_path = os.path.join(
                        ".",
                        output_class.track_name("", metadata, output_format))

                self.assertEqual(
                    self.__run_app__(["track2track"] + options), 0)
                self.assertTrue(os.path.isfile(output_path))

                if "-o" not in options:
                    self.__check_output__(
                        LAB_ENCODE.format(
                            source=audiotools.Filename(self.track1.filename),
                            destination=audiotools.Filename(output_path)))

                track2 = audiotools.open(output_path)
                self.assertEqual(track2.NAME, output_class.NAME)
                if (self.track1.lossless() and
                    track2.lossless() and not
                    (output_class.supports_replay_gain() and
                     "--replay-gain" in options) and
                    ("--sample-rate" not in options) and
                    ("--channels" not in options) and
                    ("--bits-per-sample" not in options)):

                    self.assertTrue(audiotools.pcm_cmp(self.track1.to_pcm(),
                                                       track2.to_pcm()))

                if track2.lossless():
                    self.assertEqual(
                        track2.sample_rate(),
                        44100 if ("--sample-rate" not in options) else 48000)
                    self.assertEqual(
                        track2.channels(),
                        2 if ("--channels" not in options) else 1)
                    self.assertEqual(
                        track2.bits_per_sample(),
                        16 if ("--bits-per-sample" not in options) else 8)

                if track2.get_metadata() is not None:
                    self.assertEqual(track2.get_metadata(), metadata)

                    image = track2.get_metadata().images()[0]
                    self.assertEqual(image.width, self.cover.width)
                    self.assertEqual(image.height, self.cover.height)

                if output_class.supports_replay_gain():
                    if (("-o" not in options) and
                        audiotools.ADD_REPLAYGAIN and
                        ("--no-replay-gain" not in options)):
                        self.__check_output__(RG_REPLAYGAIN_ADDED)
                        self.assertIsNotNone(track2.get_replay_gain())

    @UTIL_TRACK2TRACK
    def test_unicode(self):
        from shutil import rmtree

        dirs = [d if PY3 else d.encode("UTF-8") for d in
                [u"testdir", u'abc\xe0\xe7\xe8\u3041\u3044\u3046']]

        formats = [f if PY3 else f.encode("UTF-8") for f in
                   [u"new_file.flac",
                    u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac']]

        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"file.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        for (output_directory,
             format_string,
             file_path) in Possibilities(dirs, formats, filenames):
            if os.path.isdir(output_directory):
                rmtree(output_directory)
            if os.path.isfile(file_path):
                os.unlink(file_path)

            try:
                track = audiotools.FlacAudio.from_pcm(
                    file_path,
                    BLANK_PCM_Reader(1))

                self.assertEqual(
                    self.__run_app__(
                        ["track2track",
                         "--dir", output_directory,
                         "--format", format_string,
                         file_path]), 0)

                self.assertTrue(
                    audiotools.pcm_cmp(
                        track.to_pcm(),
                        audiotools.open(os.path.join(output_directory,
                                                     format_string)).to_pcm()))
            finally:
                if os.path.isdir(output_directory):
                    rmtree(output_directory)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"file.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        outputs = [o if PY3 else o.encode("UTF-8") for o in
                   [u"output_file.flac",
                    u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac']]

        for (file_path,
             output_path) in Possibilities(filenames, outputs):
            if os.path.isfile(output_path):
                os.unlink(output_path)
            if os.path.isfile(file_path):
                os.unlink(file_path)
            try:
                track = audiotools.FlacAudio.from_pcm(
                    file_path,
                    BLANK_PCM_Reader(1))

                self.assertEqual(
                    self.__run_app__(
                        ["track2track", "-o", output_path, file_path]), 0)

                self.assertTrue(
                    audiotools.pcm_cmp(
                        track.to_pcm(),
                        audiotools.open(output_path).to_pcm()))
            finally:
                if os.path.isfile(output_path):
                    os.unlink(output_path)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

    @UTIL_TRACK2TRACK
    def test_errors(self):
        from audiotools.text import (ERR_TRACK2TRACK_O_AND_D,
                                     ERR_TRACK2TRACK_O_AND_D_SUGGESTION,
                                     ERR_TRACK2TRACK_O_AND_FORMAT,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_INVALID_JOINT,
                                     ERR_UNKNOWN_FIELD,
                                     LAB_SUPPORTED_FIELDS,
                                     ERR_FILES_REQUIRED,
                                     ERR_TRACK2TRACK_O_AND_MULTIPLE,
                                     ERR_DUPLICATE_FILE,
                                     ERR_OUTPUT_IS_INPUT,
                                     ERR_DUPLICATE_OUTPUT_FILE,
                                     ERR_UNSUPPORTED_CHANNEL_COUNT,
                                     ERR_UNSUPPORTED_CHANNEL_MASK,
                                     ERR_UNSUPPORTED_BITS_PER_SAMPLE,
                                     ERR_INVALID_SAMPLE_RATE,
                                     ERR_INVALID_CHANNEL_COUNT,
                                     ERR_INVALID_BITS_PER_SAMPLE)

        all_options = ["-t", "-q", "-d", "--format", "-o", "-j",
                       "--replay-gain", "--no-replay-gain",
                       "--sample-rate", "--channels", "--bits-per-sample"]
        for count in range(0, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                self.__clear_checks__()

                options = self.populate_bad_options(options) + \
                    [self.broken_track1.filename]

                if "-t" in options:
                    self.assertEqual(
                        self.__run_app__(["track2track"] + options),
                        2)
                    continue
                elif "-o" in options:
                    output_class = self.output_format
                else:
                    output_class = audiotools.TYPE_MAP[
                        audiotools.DEFAULT_TYPE]

                self.assertEqual(
                    self.__run_app__(["track2track"] + options),
                    1)

                if ("-o" in options) and ("-d" in options):
                    self.__check_error__(ERR_TRACK2TRACK_O_AND_D)
                    self.__check_info__(ERR_TRACK2TRACK_O_AND_D_SUGGESTION)
                    continue

                if ("--format" in options) and ("-o" in options):
                    self.__queue_warning__(ERR_TRACK2TRACK_O_AND_FORMAT)

                if "-q" in options:
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality="bar", type=output_class.NAME))
                    continue

                if "--sample-rate" in options:
                    self.__check_error__(ERR_INVALID_SAMPLE_RATE)
                    continue

                if "--channels" in options:
                    self.__check_error__(ERR_INVALID_CHANNEL_COUNT)
                    continue

                if "--bits-per-sample" in options:
                    self.__check_error__(ERR_INVALID_BITS_PER_SAMPLE)
                    continue

                if "-j" in options:
                    self.__check_error__(
                        ERR_INVALID_JOINT)
                    continue

                if "-o" in options:
                    self.__check_error__(
                        u"[Errno 20] Not a directory: '{}'".format(
                            self.unwritable_file))
                    continue

                if "--format" in options:
                    self.__check_error__(ERR_UNKNOWN_FIELD.format("foo"))
                    self.__check_info__(LAB_SUPPORTED_FIELDS)
                    for field in sorted(audiotools.MetaData.FIELDS +
                                        ("album_track_number", "suffix")):
                        if field == 'track_number':
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    self.__check_info__(u"%(basename)s")
                    continue

                if "-d" in options:
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_class.track_name(
                            "",
                            self.track1.get_metadata(),
                            None))
                    self.__check_error__(
                        u"[Errno 13] Permission denied: '{}'".format(
                            output_path))
                    continue

                # the error triggered by a broken file is variable
                # so no need to check its exact value
                self.assertGreater(len(self.stderr.getvalue()), 0)

        # check no input files
        self.assertEqual(self.__run_app__(["track2track"]), 2)

        self.track2 = self.input_format.from_pcm(
            os.path.join(self.input_dir,
                         "02.{}".format(self.input_format.SUFFIX)),
            BLANK_PCM_Reader(2))

        # check multiple input files and -o
        self.assertEqual(self.__run_app__(["track2track",
                                           "-o", self.output_file.name,
                                           self.track1.filename,
                                           self.track2.filename]), 1)
        self.__check_error__(ERR_TRACK2TRACK_O_AND_MULTIPLE)

        # check duplicate input file
        self.assertEqual(self.__run_app__(["track2track",
                                           self.track1.filename,
                                           self.track1.filename,
                                           self.track2.filename]), 1)
        self.__check_error__(
            ERR_DUPLICATE_FILE.format(
                audiotools.Filename(self.track1.filename)))

        # check identical input and output file
        self.assertEqual(
            self.__run_app__(["track2track",
                              self.track1.filename,
                              "-t", self.input_format.NAME,
                              "-d", self.input_dir,
                              "--format=%(track_number)2.2d.%(suffix)s"]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT.format(
                audiotools.Filename(self.track1.filename)))

        # check identical input and output file with -o
        self.assertEqual(self.__run_app__(["track2track",
                                           "-t", self.input_format.NAME,
                                           "-o", self.track1.filename,
                                           self.track1.filename]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT.format(
                audiotools.Filename(self.track1.filename)))

        # check duplicate output files
        self.__run_app__(["track2track",
                          "--format", "foo",
                          self.track1.filename,
                          self.track2.filename])
        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE.format(
                audiotools.Filename(os.path.join(".", "foo"))))

        # check conversion from supported to unsupported channel count
        with tempfile.NamedTemporaryFile(
                suffix=".flac") as unsupported_count_file:
            supported_track = audiotools.WaveAudio.from_pcm(
                os.path.join(self.input_dir, "00 - channels.wav"),
                BLANK_PCM_Reader(1, channels=10, channel_mask=0))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "flac",
                                               "-d",
                                               self.output_dir,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_COUNT.format(
                    target_filename=audiotools.Filename(
                        os.path.join(self.output_dir, "00 - .flac")),
                    channels=10))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_count_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_COUNT.format(
                    target_filename=audiotools.Filename(
                        unsupported_count_file.name),
                    channels=10))

        # check conversion from supported to unsupported channel mask
        with tempfile.NamedTemporaryFile(
                 suffix=".flac") as unsupported_mask_file:
            supported_track = audiotools.WaveAudio.from_pcm(
                os.path.join(self.input_dir, "00 - mask.wav"),
                BLANK_PCM_Reader(1, channels=6, channel_mask=0x3F000))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "flac",
                                               "-d",
                                               self.output_dir,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_MASK.format(
                    target_filename=audiotools.Filename(
                        os.path.join(self.output_dir, "00 - .flac")),
                    assignment=audiotools.ChannelMask(0x3F000)))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_mask_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_MASK.format(
                    target_filename=audiotools.Filename(
                        unsupported_mask_file.name),
                    assignment=audiotools.ChannelMask(0x3F000)))

        # check conversion from supported to unsupported bits-per-sample
        with tempfile.NamedTemporaryFile(
                suffix=".m4a") as unsupported_bps_file:
            supported_track = audiotools.WaveAudio.from_pcm(
                os.path.join(self.input_dir, "00 - bps.wav"),
                BLANK_PCM_Reader(1, bits_per_sample=8))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "alac",
                                               "-d",
                                               self.output_dir,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_BITS_PER_SAMPLE.format(
                    target_filename=audiotools.Filename(
                        os.path.join(self.output_dir, "00 - .m4a")),
                    bps=8))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "alac",
                                               "-o",
                                               unsupported_bps_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_BITS_PER_SAMPLE.format(
                    target_filename=audiotools.Filename(
                        unsupported_bps_file.name),
                    bps=8))

    @UTIL_TRACK2TRACK
    def test_replay_gain(self):
        from audiotools.text import (LAB_ENCODE,
                                     RG_REPLAYGAIN_ADDED,
                                     RG_REPLAYGAIN_APPLIED,
                                     RG_REPLAYGAIN_ADDED_TO_ALBUM)

        temp_files = [os.path.join(self.input_dir,
                                   "{:02d}.{}".format(
                                       i + 1, self.input_format.SUFFIX))
                      for i in range(7)]
        temp_tracks = []

        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[0],
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50, 4410.0, 0.49, 1.0)))

        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[1],
                test_streams.Sine16_Stereo(66150, 44100,
                                           8820.0, 0.70, 4410.0, 0.29, 1.0)))
        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[2],
                test_streams.Sine16_Stereo(52920, 44100,
                                           441.0, 0.50, 441.0, 0.49, 0.5)))
        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[3],
                test_streams.Sine16_Stereo(61740, 44100,
                                           441.0, 0.61, 661.5, 0.37, 2.0)))
        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[4],
                test_streams.Sine16_Stereo(26460, 44100,
                                           441.0, 0.50, 882.0, 0.49, 0.7)))
        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[5],
                test_streams.Sine16_Stereo(61740, 44100,
                                           441.0, 0.50, 4410.0, 0.49, 1.3)))
        temp_tracks.append(
            self.input_format.from_pcm(
                temp_files[6],
                test_streams.Sine16_Stereo(79380, 44100,
                                           8820.0, 0.70, 4410.0, 0.29, 0.1)))

        temp_tracks[0].set_metadata(audiotools.MetaData(
            track_name=u"Track 3",
            album_name=u"Test Album",
            track_number=1,
            album_number=1))
        temp_tracks[1].set_metadata(audiotools.MetaData(
            track_name=u"Track 4",
            album_name=u"Test Album",
            track_number=2,
            album_number=1))
        temp_tracks[2].set_metadata(audiotools.MetaData(
            track_name=u"Track 5",
            album_name=u"Test Album",
            track_number=1,
            album_number=2))
        temp_tracks[3].set_metadata(audiotools.MetaData(
            track_name=u"Track 6",
            album_name=u"Test Album",
            track_number=2,
            album_number=2))
        temp_tracks[4].set_metadata(audiotools.MetaData(
            track_name=u"Track 7",
            album_name=u"Test Album",
            track_number=3,
            album_number=2))
        temp_tracks[5].set_metadata(audiotools.MetaData(
            track_name=u"Track 1",
            album_name=u"Test Album 2",
            track_number=1))
        temp_tracks[6].set_metadata(audiotools.MetaData(
            track_name=u"Track 2",
            album_name=u"Test Album 2",
            track_number=2))

        self.assertEqual(
            self.__run_app__(
                ["track2track",
                 "-d", self.output_dir,
                 "--format=%(track_name)s.%(suffix)s",
                 "-t", self.output_format.NAME,
                 "-V", "normal",
                 "-j", str(1),
                 "--replay-gain"] +
                [f.filename for f in temp_tracks]), 0)

        # check the conversion output text
        for (i, track) in enumerate([temp_tracks[5],
                                     temp_tracks[6],
                                     temp_tracks[0],
                                     temp_tracks[1],
                                     temp_tracks[2],
                                     temp_tracks[3],
                                     temp_tracks[4]], 1):
            output_filename = audiotools.Filename(
                os.path.join(
                    self.output_dir,
                    self.output_format.track_name(
                        track.filename,
                        track.get_metadata(),
                        "%(track_name)s.%(suffix)s")))
            self.__check_output__(
                audiotools.output_progress(
                    LAB_ENCODE.format(
                        source=audiotools.Filename(track.filename),
                        destination=output_filename),
                    i,
                    len(temp_tracks)))

        # check the ReplayGain completed text
        self.__check_output__(
            audiotools.output_progress(RG_REPLAYGAIN_ADDED, 1, 3))
        self.__check_output__(
            audiotools.output_progress(RG_REPLAYGAIN_ADDED_TO_ALBUM.format(1),
                                       2, 3))
        self.__check_output__(
            audiotools.output_progress(RG_REPLAYGAIN_ADDED_TO_ALBUM.format(2),
                                       3, 3))

        converted_tracks = audiotools.open_files(
            [os.path.join(self.output_dir, f) for f in
             os.listdir(self.output_dir)], sorted=True)

        self.assertEqual(len(converted_tracks), 7)

        for (i, track) in enumerate(converted_tracks):
            self.assertEqual(track.get_metadata().track_name,
                             u"Track {:d}".format(i + 1))
            self.assertIsNotNone(track.get_replay_gain())

        replay_gains = [track.get_replay_gain() for track in
                        converted_tracks]

        # tracks 0 and 1 should be on the same album
        self.assertEqual(replay_gains[0],
                         replay_gains[0])
        self.assertEqual(replay_gains[0].album_gain,
                         replay_gains[1].album_gain)

        self.assertNotEqual(replay_gains[0].album_gain,
                            replay_gains[2].album_gain)
        self.assertNotEqual(replay_gains[0].album_gain,
                            replay_gains[4].album_gain)

        # tracks 2 and 3 should be on the same album
        self.assertEqual(replay_gains[2].album_gain,
                         replay_gains[3].album_gain)

        self.assertNotEqual(replay_gains[3].album_gain,
                            replay_gains[0].album_gain)
        self.assertNotEqual(replay_gains[3].album_gain,
                            replay_gains[5].album_gain)

        # tracks 4, 5 and 6 should be on the same album
        self.assertEqual(replay_gains[4].album_gain,
                         replay_gains[5].album_gain)
        self.assertEqual(replay_gains[5].album_gain,
                         replay_gains[6].album_gain)
        self.assertEqual(replay_gains[4].album_gain,
                         replay_gains[6].album_gain)

        self.assertNotEqual(replay_gains[6].album_gain,
                            replay_gains[0].album_gain)
        self.assertNotEqual(replay_gains[6].album_gain,
                            replay_gains[2].album_gain)


class trackcat(UtilTest):
    @UTIL_TRACKCAT
    def setUp(self):
        self.stream1 = test_streams.Sine16_Stereo(220500, 44100,
                                                  441.0, 0.50,
                                                  4410.0, 0.49, 1.0)
        self.stream2 = test_streams.Sine16_Stereo(264600, 44100,
                                                  8820.0, 0.70,
                                                  4410.0, 0.29, 1.0)
        self.stream3 = test_streams.Sine16_Stereo(308700, 44100,
                                                  441.0, 0.50,
                                                  441.0, 0.49, 0.5)

        self.misfit_stream1 = test_streams.Sine24_Stereo(200000, 44100,
                                                         441.0, 0.50,
                                                         441.0, 0.49, 1.0)

        self.misfit_stream2 = test_streams.Sine16_Mono(200000, 44100,
                                                       441.0, 0.50,
                                                       441.0, 0.49)

        self.misfit_stream3 = test_streams.Sine16_Stereo(200000, 48000,
                                                         441.0, 0.50,
                                                         441.0, 0.49, 1.0)

        self.track1_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track2_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track3_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track4_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track5_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track6_file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.track1 = audiotools.FlacAudio.from_pcm(
            self.track1_file.name, self.stream1)
        self.track1.set_metadata(audiotools.MetaData(track_name=u"Track 1",
                                                     album_name=u"Album",
                                                     artist_name=u"Artist",
                                                     track_number=1,
                                                     track_total=3))
        self.track2 = audiotools.FlacAudio.from_pcm(
            self.track2_file.name, self.stream2)
        self.track2.set_metadata(audiotools.MetaData(track_name=u"Track 2",
                                                     album_name=u"Album",
                                                     artist_name=u"Artist",
                                                     track_number=2,
                                                     track_total=3))
        self.track3 = audiotools.FlacAudio.from_pcm(
            self.track3_file.name, self.stream3)
        self.track3.set_metadata(audiotools.MetaData(track_name=u"Track 3",
                                                     album_name=u"Album",
                                                     artist_name=u"Artist",
                                                     track_number=3,
                                                     track_total=3))
        self.track4 = audiotools.FlacAudio.from_pcm(
            self.track4_file.name, self.misfit_stream1)
        self.track5 = audiotools.FlacAudio.from_pcm(
            self.track5_file.name, self.misfit_stream2)
        self.track6 = audiotools.FlacAudio.from_pcm(
            self.track6_file.name, self.misfit_stream3)

        self.cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        self.cuesheet.flush()

        self.invalid_cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.invalid_cuesheet.write(b"Hello, World!")
        self.invalid_cuesheet.flush()

        self.suffix_outfile = tempfile.NamedTemporaryFile(suffix=".flac")
        self.nonsuffix_outfile = tempfile.NamedTemporaryFile()

    @UTIL_TRACKCAT
    def tearDown(self):
        self.track1_file.close()
        self.track2_file.close()
        self.track3_file.close()
        self.track4_file.close()
        self.track5_file.close()
        self.track6_file.close()
        self.cuesheet.close()
        self.invalid_cuesheet.close()
        self.suffix_outfile.close()
        self.nonsuffix_outfile.close()

    @UTIL_TRACKCAT
    def test_version(self):
        self.assertEqual(self.__run_app__(["trackcat",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def populate_options(self, options, type, quality, outfile):
        populated = []

        for option in options:
            if option == '-t':
                populated.append(option)
                populated.append(type)
            elif option == '-q':
                populated.append(option)
                populated.append(quality)
            elif option == '--cue':
                populated.append(option)
                populated.append(self.cuesheet.name)
            elif option == '-o':
                populated.append(option)
                populated.append(outfile)
            else:
                populated.append(option)

        return populated

    def output_combinations(self, all_options):
        for (type, quality) in [("flac", "8"),
                                ("wav", "foo")]:
            for outfile in [self.suffix_outfile.name,
                            self.nonsuffix_outfile.name,
                            "/dev/null/foo.wav",
                            "/dev/null/foo"]:
                for count in range(1, len(all_options) + 1):
                    for options in Combinations(all_options, count):
                        yield (type, quality, outfile, count, options)

    @UTIL_TRACKCAT
    def test_options(self):
        from audiotools.text import (ERR_FILES_REQUIRED,
                                     ERR_BPS_MISMATCH,
                                     ERR_CHANNEL_COUNT_MISMATCH,
                                     ERR_SAMPLE_RATE_MISMATCH,
                                     ERR_CUE_IOERROR,
                                     ERR_CUE_SYNTAX_ERROR,
                                     ERR_DUPLICATE_FILE,
                                     ERR_OUTPUT_IS_INPUT,
                                     ERR_NO_OUTPUT_FILE,
                                     ERR_UNSUPPORTED_AUDIO_TYPE,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_ENCODING_ERROR)

        # first, check the error conditions
        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac"]), 2)

        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename,
                              self.track4.filename]), 1)
        self.__check_error__(ERR_BPS_MISMATCH)

        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename,
                              self.track5.filename]), 1)
        self.__check_error__(ERR_CHANNEL_COUNT_MISMATCH)

        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename,
                              self.track6.filename]), 1)
        self.__check_error__(ERR_SAMPLE_RATE_MISMATCH)

        self.assertEqual(
            self.__run_app__(["trackcat", "--cue", "/dev/null/foo.cue",
                              "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename]), 1)
        self.__check_error__(ERR_CUE_IOERROR)

        self.assertEqual(
            self.__run_app__(["trackcat", "--cue", self.invalid_cuesheet.name,
                              "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename]), 1)
        self.__check_error__(ERR_CUE_SYNTAX_ERROR.format(1))

        self.assertEqual(
            self.__run_app__(["trackcat",
                              "-o", self.suffix_outfile.name,
                              self.track1.filename,
                              self.track1.filename]), 0)
        self.__check_warning__(
            ERR_DUPLICATE_FILE.format(
                audiotools.Filename(self.track1.filename)))

        self.assertEqual(
            self.__run_app__(["trackcat",
                              "-o", self.track1.filename,
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT.format(
                audiotools.Filename(self.track1.filename)))

        # then, check the option combinations
        # along with a few different output files and types
        all_options = ["-t", "-q", "--cue", "-o"]
        for (type,
             quality,
             outfile,
             count,
             options) in self.output_combinations(all_options):
            if os.path.isfile(outfile):
                f = open(outfile, "wb")
                f.close()

            options = self.populate_options(
                options, type, quality, outfile) + [self.track1.filename,
                                                    self.track2.filename,
                                                    self.track3.filename]

            # check a few common errors
            if "-o" not in options:
                self.assertEqual(self.__run_app__(["trackcat"] + options),
                                 1)

                self.__check_error__(ERR_NO_OUTPUT_FILE)
                continue

            if "-t" in options:
                output_format = audiotools.TYPE_MAP[type]
            else:
                try:
                    output_format = audiotools.filename_to_type(outfile)
                except audiotools.UnknownAudioType:
                    self.assertEqual(self.__run_app__(["trackcat"] +
                                                      options), 1)

                    self.__check_error__(
                        ERR_UNSUPPORTED_AUDIO_TYPE.format(u""))
                    continue

            if (("-q" in options) and
                (quality not in output_format.COMPRESSION_MODES)):
                self.assertEqual(self.__run_app__(["trackcat"] + options),
                                 1)
                self.__check_error__(
                    ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                        quality=quality, type=output_format.NAME))
                continue

            if outfile.startswith("/dev/"):
                self.assertEqual(self.__run_app__(["trackcat"] + options),
                                 1)
                self.__check_error__(
                    ERR_ENCODING_ERROR.format(audiotools.Filename(outfile)))
                continue

            # check that no PCM data is lost
            self.assertEqual(
                self.__run_app__(["trackcat"] + options), 0)
            new_track = audiotools.open(outfile)
            self.assertEqual(new_track.NAME, output_format.NAME)
            self.assertEqual(new_track.total_frames(), 793800)
            self.assertTrue(
                audiotools.pcm_cmp(
                    new_track.to_pcm(),
                    audiotools.PCMCat([track.to_pcm() for track in
                                      [self.track1,
                                       self.track2,
                                       self.track3]])))

            # check that metadata is merged properly
            metadata = new_track.get_metadata()
            if metadata is not None:
                self.assertEqual(metadata.track_name, None)
                self.assertEqual(metadata.album_name, u"Album")
                self.assertEqual(metadata.artist_name, u"Artist")
                self.assertEqual(metadata.track_number, None)
                self.assertEqual(metadata.track_total, 3)

            # check that the cuesheet is embedded properly
            if (("--cue" in options) and
                (output_format is audiotools.FlacAudio)):
                cuesheet = new_track.get_cuesheet()
                self.assertIsNotNone(cuesheet)
                self.assertEqual([t.get_metadata().ISRC for t in cuesheet],
                                 [u'JPPI00652340',
                                  u'JPPI00652349',
                                  u'JPPI00652341'])
                self.assertEqual([[int(i.offset() * 75) for i in t]
                                  for t in cuesheet],
                                 [[0, ], [225, 375], [675, 825]])

    @UTIL_TRACKCAT
    def test_unicode(self):
        filenames = [[f if PY3 else f.encode("UTF-8") for f in
                      filenames] for filenames in
                     [[u"track{:d}.flac".format(i) for i in range(3)],
                      [(u'abc\xe0\xe7\xe8\u3041\u3044\u3046-{:d}.flac'.format(i))
                       for i in range(3)]]]

        output_filenames = [f if PY3 else f.encode("UTF-8") for f in
                            [u"output.flac",
                             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-out.flac']]

        cuesheets = [c if ((c is None) or PY3) else c.encode("UTF-8")
                     for c in [None,
                               u"cuesheet.cue",
                               u'abc\xe0\xe7\xe8\u3041\u3044\u3046.cue']]

        for (input_filenames,
             output_path,
             cuesheet_file) in Possibilities(filenames,
                                             output_filenames,
                                             cuesheets):

            for input_filename in input_filenames:
                if os.path.isfile(input_filename):
                    os.unlink(input_filename)
            if os.path.isfile(output_path):
                os.unlink(output_path)
            if (cuesheet_file is not None) and os.path.isfile(cuesheet_file):
                os.unlink(cuesheet_file)

            tracks = [audiotools.FlacAudio.from_pcm(
                      input_filename, EXACT_BLANK_PCM_Reader(pcm_frames))
                      for (input_filename, pcm_frames) in
                      zip(input_filenames, [220500, 264600, 308700])]

            if cuesheet_file is not None:
                with open(cuesheet_file, "wb") as f:
                    f.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')

            self.assertEqual(
                self.__run_app__(
                    ["trackcat"] + input_filenames +
                    ([cuesheet_file] if cuesheet_file is not None else []) +
                    ["--output", output_path]), 0)

            self.assertTrue(
                audiotools.pcm_cmp(
                    audiotools.PCMCat([t.to_pcm() for t in tracks]),
                    audiotools.open(output_path).to_pcm()))

            for input_filename in input_filenames:
                if os.path.isfile(input_filename):
                    os.unlink(input_filename)
            if os.path.isfile(output_path):
                os.unlink(output_path)
            if (cuesheet_file is not None) and os.path.isfile(cuesheet_file):
                os.unlink(cuesheet_file)


class trackcat_pre_gap(UtilTest):
    @UTIL_TRACKCAT
    def test_pre_gap(self):
        from fractions import Fraction

        pre_gap_size = 19404
        track_lengths = [21741300, 13847400, 22402800, 14420700,
                         10760400, 17904600, 13715100, 17022600,
                         30781800, 28312200]
        with open("trackcat_pre_gap.cue", "rb") as f:
            cuesheet_data = f.read()
        # write individual tracks to disk along with track numbers
        temp_tracks_f = [tempfile.NamedTemporaryFile(suffix=".aiff")
                         for i in range(len(track_lengths))]
        temp_tracks = [audiotools.AiffAudio.from_pcm(
                       temp_f.name,
                       EXACT_RANDOM_PCM_Reader(length),
                       total_pcm_frames=length)
                       for (temp_f, length) in zip(temp_tracks_f,
                                                   track_lengths)]

        for (track_number, temp_track) in enumerate(temp_tracks, 1):
            temp_track.set_metadata(
                audiotools.MetaData(track_number=track_number))

        # write cuesheet to disk
        temp_cue_f = tempfile.NamedTemporaryFile(suffix=".cue")
        temp_cue_f.write(cuesheet_data)
        temp_cue_f.flush()

        with tempfile.NamedTemporaryFile(suffix=".flac") as temp_output_f:
            # concatenate files to image using cuesheet
            self.assertEqual(
                self.__run_app__(["trackcat",
                                  "--cue", temp_cue_f.name,
                                  "-q", "0",
                                  "-o", temp_output_f.name] +
                                 [temp_track_f.name for temp_track_f in
                                  temp_tracks_f] +
                                 ["--no-musicbrainz", "--no-freedb"]), 0)

            output_track = audiotools.open(temp_output_f.name)

            # ensure embedded cuesheet matches file lengths
            track_sheet = audiotools.open(temp_output_f.name).get_cuesheet()
            self.assertIsNotNone(track_sheet)
            self.assertEqual(track_sheet.pre_gap(),
                             Fraction(pre_gap_size, 44100))
            for (i, length) in enumerate(track_lengths, 1):
                self.assertEqual(track_sheet.track_length(i),
                                 Fraction(length, 44100))

            # ensure tracks in image match expected offset and data
            for (i, track, expected_length) in zip(range(len(track_lengths)),
                                                   temp_tracks,
                                                   track_lengths):
                offset = pre_gap_size + sum(track_lengths[0:i])
                pcmreader = output_track.to_pcm()
                seeked_offset = pcmreader.seek(offset)
                offset -= seeked_offset
                self.assertTrue(
                    audiotools.pcm_cmp(
                        track.to_pcm(),
                        audiotools.PCMReaderWindow(pcmreader,
                                                   offset,
                                                   expected_length)))

        temp_cue_f.close()

        # concatenate files to image without using cuesheet
        with tempfile.NamedTemporaryFile(suffix=".flac") as temp_output_f:
            # concatenate files to image using cuesheet
            self.assertEqual(
                self.__run_app__(["trackcat",
                                  "-q", "0",
                                  "-o", temp_output_f.name] +
                                 [temp_track_f.name for temp_track_f in
                                  temp_tracks_f] +
                                 ["--no-musicbrainz", "--no-freedb"]), 0)

            output_track = audiotools.open(temp_output_f.name)

            # ensure embedded cuesheet matches file lengths
            track_sheet = audiotools.open(temp_output_f.name).get_cuesheet()
            self.assertIsNotNone(track_sheet)
            self.assertEqual(track_sheet.pre_gap(),
                             Fraction(0, 44100))
            for (i, length) in enumerate(track_lengths, 1):
                self.assertEqual(track_sheet.track_length(i),
                                 Fraction(length, 44100))

            # ensure tracks in image match expected offset and data
            for (i, track, expected_length) in zip(range(len(track_lengths)),
                                                   temp_tracks,
                                                   track_lengths):
                offset = sum(track_lengths[0:i])
                pcmreader = output_track.to_pcm()
                seeked_offset = pcmreader.seek(offset)
                offset -= seeked_offset
                self.assertTrue(
                    audiotools.pcm_cmp(
                        track.to_pcm(),
                        audiotools.PCMReaderWindow(pcmreader,
                                                   offset,
                                                   expected_length)))

        # cleanup temporary files
        for temp_track_f in temp_tracks_f:
            temp_track_f.close()
        temp_cue_f.close()

    @UTIL_TRACKCAT
    def test_populated_pre_gap(self):
        from fractions import Fraction

        track_lengths = [19404,
                         21741300, 13847400, 22402800, 14420700,
                         10760400, 17904600, 13715100, 17022600,
                         30781800, 28312200]
        with open("trackcat_pre_gap.cue", "rb") as f:
            cuesheet_data = f.read()

        # write individual tracks to disk along with track numbers
        temp_tracks_f = [tempfile.NamedTemporaryFile(suffix=".aiff")
                         for i in range(len(track_lengths))]
        temp_tracks = [audiotools.AiffAudio.from_pcm(
                       temp_f.name,
                       EXACT_RANDOM_PCM_Reader(length),
                       total_pcm_frames=length)
                       for (temp_f, length) in zip(temp_tracks_f,
                                                   track_lengths)]

        for (track_number, temp_track) in enumerate(temp_tracks):
            temp_track.set_metadata(
                audiotools.MetaData(track_number=track_number))

        # write cuesheet to disk
        temp_cue_f = tempfile.NamedTemporaryFile(suffix=".cue")
        temp_cue_f.write(cuesheet_data)
        temp_cue_f.flush()

        with tempfile.NamedTemporaryFile(suffix=".flac") as temp_output_f:
            # concatenate files to image using cuesheet
            self.assertEqual(
                self.__run_app__(["trackcat",
                                  "--cue", temp_cue_f.name,
                                  "-q", "0",
                                  "-o", temp_output_f.name] +
                                 [temp_track_f.name for temp_track_f in
                                  temp_tracks_f] +
                                 ["--no-musicbrainz", "--no-freedb"]), 0)

            output_track = audiotools.open(temp_output_f.name)

            # ensure embedded cuesheet matches file lengths
            track_sheet = audiotools.open(temp_output_f.name).get_cuesheet()
            self.assertIsNotNone(track_sheet)
            self.assertEqual(track_sheet.pre_gap(),
                             Fraction(track_lengths[0], 44100))
            for (i, length) in enumerate(track_lengths[1:], 1):
                self.assertEqual(track_sheet.track_length(i),
                                 Fraction(length, 44100))

            # ensure tracks in image match expected offset and data
            for (i, track, expected_length) in zip(range(len(track_lengths)),
                                                   temp_tracks,
                                                   track_lengths):
                offset = sum(track_lengths[0:i])
                pcmreader = output_track.to_pcm()
                seeked_offset = pcmreader.seek(offset)
                offset -= seeked_offset
                self.assertTrue(
                    audiotools.pcm_cmp(
                        track.to_pcm(),
                        audiotools.PCMReaderWindow(pcmreader,
                                                   offset,
                                                   expected_length)))

        temp_cue_f.close()

        with tempfile.NamedTemporaryFile(suffix=".flac") as temp_output_f:
            # concatenate files to image without using cuesheet
            self.assertEqual(
                self.__run_app__(["trackcat",
                                  "-q", "0",
                                  "-o", temp_output_f.name] +
                                 [temp_track_f.name for temp_track_f in
                                  temp_tracks_f] +
                                 ["--no-musicbrainz", "--no-freedb"]), 0)

            output_track = audiotools.open(temp_output_f.name)

            # ensure embedded cuesheet matches file lengths
            track_sheet = audiotools.open(temp_output_f.name).get_cuesheet()
            self.assertIsNotNone(track_sheet)
            self.assertEqual(track_sheet.pre_gap(),
                             Fraction(track_lengths[0], 44100))
            for (i, length) in enumerate(track_lengths[1:], 1):
                self.assertEqual(track_sheet.track_length(i),
                                 Fraction(length, 44100))

            # ensure tracks in image match expected offset and data
            for (i, track, expected_length) in zip(range(len(track_lengths)),
                                                   temp_tracks,
                                                   track_lengths):
                offset = sum(track_lengths[0:i])
                pcmreader = output_track.to_pcm()
                seeked_offset = pcmreader.seek(offset)
                offset -= seeked_offset
                self.assertTrue(
                    audiotools.pcm_cmp(
                        track.to_pcm(),
                        audiotools.PCMReaderWindow(pcmreader,
                                                   offset,
                                                   expected_length)))

        # cleanup temporary files
        for temp_track_f in temp_tracks_f:
            temp_track_f.close()


class trackcmp(UtilTest):
    @UTIL_TRACKCMP
    def setUp(self):
        self.type = audiotools.FlacAudio

        self.match_dir1 = tempfile.mkdtemp()
        self.match_dir2 = tempfile.mkdtemp()
        self.mismatch_dir1 = tempfile.mkdtemp()
        self.mismatch_dir2 = tempfile.mkdtemp()
        self.mismatch_dir3 = tempfile.mkdtemp()

        self.match_file1 = tempfile.NamedTemporaryFile(
            suffix="." + self.type.SUFFIX)
        self.match_file2 = tempfile.NamedTemporaryFile(
            suffix="." + self.type.SUFFIX)
        self.mismatch_file = tempfile.NamedTemporaryFile(
            suffix="." + self.type.SUFFIX)
        self.broken_file = tempfile.NamedTemporaryFile(
            suffix="." + self.type.SUFFIX)

        self.type.from_pcm(self.match_file1.name,
                           BLANK_PCM_Reader(1))
        self.type.from_pcm(self.match_file2.name,
                           BLANK_PCM_Reader(1))
        self.type.from_pcm(self.mismatch_file.name,
                           RANDOM_PCM_Reader(1))
        with open(self.match_file1.name, "rb") as f:
            self.broken_file.write(f.read()[0:-1])
        self.broken_file.flush()

        for i in range(1, 4):
            track = self.type.from_pcm(
                os.path.join(self.match_dir1,
                             "{:02d}.{}".format(i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

            track = self.type.from_pcm(
                os.path.join(self.match_dir2,
                             "{:02d}.{}".format(i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

            track = self.type.from_pcm(
                os.path.join(self.mismatch_dir1,
                             "{:02d}.{}".format(i, self.type.SUFFIX)),
                RANDOM_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

        for i in range(1, 3):
            track = self.type.from_pcm(
                os.path.join(self.mismatch_dir2,
                             "{:02d}.{}".format(i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

        for i in range(1, 5):
            track = self.type.from_pcm(
                os.path.join(self.mismatch_dir3,
                             "{:02d}.{}".format(i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

    @UTIL_TRACKCMP
    def tearDown(self):
        for directory in [self.match_dir1,
                          self.match_dir2,
                          self.mismatch_dir1,
                          self.mismatch_dir2,
                          self.mismatch_dir3]:
            for f in os.listdir(directory):
                os.unlink(os.path.join(directory, f))
            os.rmdir(directory)

        self.match_file1.close()
        self.match_file2.close()
        self.mismatch_file.close()

    @UTIL_TRACKCMP
    def test_version(self):
        self.assertEqual(self.__run_app__(["trackcmp",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    @UTIL_TRACKCMP
    def test_combinations(self):
        from audiotools.text import (LAB_TRACKCMP_CMP,
                                     LAB_TRACKCMP_MISMATCH,
                                     LAB_TRACKCMP_TYPE_MISMATCH,
                                     LAB_TRACKCMP_OK,
                                     LAB_TRACKCMP_MISSING,
                                     LAB_TRACKCMP_ERROR)

        # check matching file against maching file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_file2.name]),
            0)

        # check matching file against itself
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_file1.name]),
            0)

        # check matching file against mismatching file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.mismatch_file.name]),
            1)
        self.__check_output__(
            LAB_TRACKCMP_CMP.format(
                file1=audiotools.Filename(self.match_file1.name),
                file2=audiotools.Filename(self.mismatch_file.name)) +
            u" : " +
            LAB_TRACKCMP_MISMATCH.format(1))

        # (ANSI output won't be generated because stdout isn't a TTY)

        # check matching file against missing file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, "/dev/null/foo"]),
            1)
        self.__check_error__(
            LAB_TRACKCMP_CMP.format(
                file1=audiotools.Filename(self.match_file1.name),
                file2=audiotools.Filename("/dev/null/foo")) +
            u" : " + LAB_TRACKCMP_TYPE_MISMATCH)

        # check matching file against broken file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.broken_file.name]),
            1)
        self.__check_output__(
            LAB_TRACKCMP_CMP.format(
                file1=audiotools.Filename(self.match_file1.name),
                file2=audiotools.Filename(self.broken_file.name)) +
            u" : " + LAB_TRACKCMP_ERROR)

        # check file against directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_dir1]),
            1)
        self.__check_error__(
            LAB_TRACKCMP_CMP.format(
                file1=audiotools.Filename(self.match_file1.name),
                file2=audiotools.Filename(self.match_dir1)) +
            u" : " + LAB_TRACKCMP_TYPE_MISMATCH)

        # check directory against file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_dir1, self.match_file1.name]),
            1)
        self.__check_error__(
            LAB_TRACKCMP_CMP.format(
                file1=audiotools.Filename(self.match_dir1),
                file2=audiotools.Filename(self.match_file1.name)) +
            u" : " + LAB_TRACKCMP_TYPE_MISMATCH)

        # check matching directory against matching directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.match_dir2]),
            0)
        for i in range(1, 4):
            self.__check_output__(
                audiotools.output_progress(
                    LAB_TRACKCMP_CMP.format(
                        file1=audiotools.Filename(
                            os.path.join(
                                self.match_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX))),
                        file2=audiotools.Filename(
                            os.path.join(
                                self.match_dir2,
                                "{:02d}.{}".format(i, self.type.SUFFIX)))) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 3))

        # check matching directory against itself
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.match_dir1]),
            0)
        for i in range(1, 4):
            self.__check_output__(
                audiotools.output_progress(
                    LAB_TRACKCMP_CMP.format(
                        file1=audiotools.Filename(
                            os.path.join(
                                self.match_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX))),
                        file2=audiotools.Filename(
                            os.path.join(
                                self.match_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX)))) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 3))

        # check matching directory against mismatching directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir1]),
            1)
        for i in range(1, 4):
            self.__check_output__(
                audiotools.output_progress(
                    LAB_TRACKCMP_CMP.format(
                        file1=audiotools.Filename(
                            os.path.join(
                                self.match_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX))),
                        file2=audiotools.Filename(
                            os.path.join(
                                self.mismatch_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX)))) +
                    u" : " +
                    LAB_TRACKCMP_MISMATCH.format(1),
                    i, 3))

        # check matching directory against directory missing file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir2]),
            1)
        self.__check_info__(
            LAB_TRACKCMP_MISSING.format(
                filename=audiotools.Filename(
                    os.path.basename("03.{}".format(self.type.SUFFIX))),
                directory=audiotools.Filename(self.mismatch_dir2)))

        for i in range(1, 3):
            self.__check_output__(
                audiotools.output_progress(
                    LAB_TRACKCMP_CMP.format(
                        file1=audiotools.Filename(
                            os.path.join(
                                self.match_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX))),
                        file2=audiotools.Filename(
                            os.path.join(
                                self.mismatch_dir2,
                                "{:02d}.{}".format(i, self.type.SUFFIX)))) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 2))

        # check matching directory against directory with extra file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir3]),
            1)
        self.__check_info__(
            LAB_TRACKCMP_MISSING.format(
                filename=audiotools.Filename("04.{}".format(self.type.SUFFIX)),
                directory=audiotools.Filename(self.match_dir1)))

        for i in range(1, 4):
            self.__check_output__(
                audiotools.output_progress(
                    LAB_TRACKCMP_CMP.format(
                        file1=audiotools.Filename(
                            os.path.join(
                                self.match_dir1,
                                "{:02d}.{}".format(i, self.type.SUFFIX))),
                        file2=audiotools.Filename(
                            os.path.join(
                                self.mismatch_dir3,
                                "{:02d}.{}".format(i, self.type.SUFFIX)))) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 3))

        # check several files against CD image of those files
        audio_format = audiotools.FlacAudio
        lengths = [44100, 88200, 176400]
        image_file = tempfile.NamedTemporaryFile(
            suffix="." + audio_format.SUFFIX)
        track_files = [tempfile.NamedTemporaryFile(
                       suffix="." + audio_format.SUFFIX) for l in lengths]
        try:
            image = audio_format.from_pcm(
                image_file.name,
                test_streams.Sine16_Stereo(sum(lengths), 44100,
                                           441.0, 0.50,
                                           4410.0, 0.49,
                                           1.0))

            tracks = []
            for i in range(len(lengths)):
                tracks.append(
                    audio_format.from_pcm(
                        track_files[i].name,
                        audiotools.PCMReaderWindow(
                            image.to_pcm(),
                            sum(lengths[0:i]),
                            lengths[i])))

            for (i, track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))
        finally:
            image_file.close()
            for track_file in track_files:
                track_file.close()

    @UTIL_TRACKCMP
    def test_unicode(self):
        file1s = [f if PY3 else f.encode("UTF-8") for f in
                  [u"file1.flac",
                   u'abc\xe0\xe7\xe8\u3041\u3044\u3046-1.flac']]

        file2s = [f if PY3 else f.encode("UTF-8") for f in
                  [u"file2.flac",
                   u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac']]

        for (file1, file2) in Possibilities(file1s, file2s):
            if os.path.isfile(file1):
                os.unlink(file1)
            if os.path.isfile(file2):
                os.unlink(file2)

            track1 = audiotools.FlacAudio.from_pcm(
                file1,
                BLANK_PCM_Reader(1))
            track2 = audiotools.FlacAudio.from_pcm(
                file2,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(
                    ["trackcmp", file1, file2]), 0)

            self.assertTrue(audiotools.pcm_cmp(track1.to_pcm(),
                                               track2.to_pcm()))

            if os.path.isfile(file1):
                os.unlink(file1)
            if os.path.isfile(file2):
                os.unlink(file2)


class trackinfo(UtilTest):
    METADATA_FORMATS = (audiotools.FlacAudio,
                        audiotools.MP3Audio,
                        audiotools.MP2Audio,
                        audiotools.VorbisAudio,
                        audiotools.AiffAudio,
                        audiotools.M4AAudio,
                        audiotools.ALACAudio,
                        audiotools.WavPackAudio)

    @UTIL_TRACKINFO
    def setUp(self):
        self.metadata_files = [
            tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            for format in self.METADATA_FORMATS]

        self.metadata_tracks = [
            format.from_pcm(file.name, BLANK_PCM_Reader(1))
            for (file, format) in zip(self.metadata_files,
                                      self.METADATA_FORMATS)]

        metadata = audiotools.MetaData(track_name=u"a",
                                       track_number=1,
                                       track_total=2,
                                       album_name=u"b",
                                       artist_name=u"c",
                                       comment=u"d")

        for track in self.metadata_tracks:
            track.set_metadata(metadata)

    @UTIL_TRACKINFO
    def tearDown(self):
        for file in self.metadata_files:
            file.close()

    @UTIL_TRACKINFO
    def test_version(self):
        self.assertEqual(self.__run_app__(["trackinfo",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    @UTIL_TRACKINFO
    def test_trackinfo(self):
        from io import StringIO
        import re
        from audiotools.text import (LAB_TRACKINFO_CHANNELS,
                                     LAB_TRACKINFO_CHANNEL,
                                     MASK_FRONT_LEFT,
                                     MASK_FRONT_RIGHT)

        all_options = ["-n", "-L", "-b", "-%", "-C"]

        for track in self.metadata_tracks:
            for count in range(1, len(all_options) + 1):
                for options in Combinations(all_options, count):
                    self.assertEqual(
                        self.__run_app__(
                            ["trackinfo"] + options + [track.filename]), 0)

                    # check the initial output line
                    line = self.stdout.readline()
                    if "-b" in options:
                        self.assertIsNotNone(
                            re.match(r'\s*\d+ kbps: {}\n'.format(
                                track.filename), line))
                    elif "-%" in options:
                        self.assertIsNotNone(
                            re.match(r'\s*\d+%: {}\n'.format(
                                track.filename), line))
                    else:
                        self.assertIsNotNone(
                            re.match(
                                r'\s*\d+:\d+ 2ch 44.1kHz 16-bit: {}\n'.format(
                                    track.filename), line))

                    # check metadata/low-level metadata if -n not present
                    if "-n" not in options:
                        if "-L" not in options:
                            for line in StringIO(
                                track.get_metadata().__unicode__()):
                                self.__check_output__(line.rstrip('\r\n'))
                        else:
                            for line in StringIO(
                                track.get_metadata().raw_info()):
                                self.__check_output__(line.rstrip('\r\n'))
                        if "-C" in options:
                            self.__check_output__(u"")
                    else:
                        # no metadata display at all
                        pass

                    # check channel assignment if -C present
                    if "-C" in options:
                        self.__check_output__(LAB_TRACKINFO_CHANNELS)
                        self.__check_output__(
                            LAB_TRACKINFO_CHANNEL.format(
                                channel_number=1,
                                channel_name=MASK_FRONT_LEFT))
                        self.__check_output__(
                            LAB_TRACKINFO_CHANNEL.format(
                                channel_number=2,
                                channel_name=MASK_FRONT_RIGHT))

    @UTIL_TRACKINFO
    def test_unicode(self):
        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"track.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        for filename in filenames:
            if os.path.isfile(filename):
                os.unlink(filename)

            track = audiotools.FlacAudio.from_pcm(
                filename,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(["trackinfo", filename]), 0)

            if os.path.isfile(filename):
                os.unlink(filename)


class trackcmp_cd_image(UtilTest):
    @UTIL_TRACKCMP
    def setUp(self):
        from audiotools import Sheet
        from audiotools import SheetTrack
        from audiotools import SheetIndex
        from fractions import Fraction

        self.temp_dir = tempfile.mkdtemp()

        self.track1 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.temp_dir, "01.flac"),
            EXACT_RANDOM_PCM_Reader(pcm_frames=44100 * 10),
            total_pcm_frames=44100 * 10)

        self.track2 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.temp_dir, "02.flac"),
            EXACT_RANDOM_PCM_Reader(pcm_frames=44100 * 15),
            total_pcm_frames=44100 * 15)

        self.track3 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.temp_dir, "03.flac"),
            EXACT_RANDOM_PCM_Reader(pcm_frames=44100 * 19),
            total_pcm_frames=44100 * 19)

        self.pre_gap = audiotools.FlacAudio.from_pcm(
            os.path.join(self.temp_dir, "gap.flac"),
            EXACT_RANDOM_PCM_Reader(pcm_frames=44100 * 3),
            total_pcm_frames=44100 * 3)

        self.no_pre_gap_sheet = Sheet([
            SheetTrack(1, [SheetIndex(1, Fraction(0, 1))]),
            SheetTrack(2, [SheetIndex(0, Fraction(8, 1)),
                           SheetIndex(1, Fraction(10, 1))]),
            SheetTrack(3, [SheetIndex(0, Fraction(23, 1)),
                           SheetIndex(1, Fraction(25, 1))])])

        self.pre_gap_sheet = Sheet([
            SheetTrack(1, [SheetIndex(0, Fraction(0, 1)),
                           SheetIndex(1, Fraction(3, 1))]),
            SheetTrack(2, [SheetIndex(0, Fraction(11, 1)),
                           SheetIndex(1, Fraction(13, 1))]),
            SheetTrack(3, [SheetIndex(0, Fraction(26, 1)),
                           SheetIndex(1, Fraction(28, 1))])])

    @UTIL_TRACKCMP
    def tearDown(self):
        from shutil import rmtree
        rmtree(self.temp_dir)

    def __compare_files__(self, number, total, image, track):
        from audiotools.text import LAB_TRACKCMP_CMP
        from audiotools.text import LAB_TRACKCMP_OK

        self.__check_output__(
            audiotools.output_progress(
                u"{} : {}".format(
                    LAB_TRACKCMP_CMP.format(
                        file1=audiotools.Filename(image.filename),
                        file2=audiotools.Filename(track.filename)),
                    LAB_TRACKCMP_OK),
                number, total))

    @UTIL_TRACKCMP
    def test_no_cuesheet(self):
        for seektable in [True, False]:
            image = audiotools.FlacAudio.from_pcm(
                os.path.join(self.temp_dir, "image.flac"),
                audiotools.PCMCat([self.track1.to_pcm(),
                                   self.track2.to_pcm(),
                                   self.track3.to_pcm()]))

            if seektable:
                self.assertTrue(image.seekable())
            else:
                m = image.get_metadata()
                m.replace_blocks(3, [])
                image.update_metadata(m)
                self.assertFalse(image.seekable())

            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  image.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 3, image, self.track1)
            self.__compare_files__(2, 3, image, self.track2)
            self.__compare_files__(3, 3, image, self.track3)

    @UTIL_TRACKCMP
    def test_embedded_cuesheet(self):
        for seektable in [True, False]:
            # test image with no disc pre-gap against tracks
            no_pre_gap_image = audiotools.FlacAudio.from_pcm(
                os.path.join(self.temp_dir, "image1.flac"),
                audiotools.PCMCat([self.track1.to_pcm(),
                                   self.track2.to_pcm(),
                                   self.track3.to_pcm()]))

            no_pre_gap_image.set_cuesheet(self.no_pre_gap_sheet)
            self.assertIsNotNone(no_pre_gap_image.get_cuesheet())

            if seektable:
                self.assertTrue(no_pre_gap_image.seekable())
            else:
                m = no_pre_gap_image.get_metadata()
                m.replace_blocks(3, [])
                no_pre_gap_image.update_metadata(m)
                self.assertFalse(no_pre_gap_image.seekable())

            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  no_pre_gap_image.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 3, no_pre_gap_image, self.track1)
            self.__compare_files__(2, 3, no_pre_gap_image, self.track2)
            self.__compare_files__(3, 3, no_pre_gap_image, self.track3)

            # test image with disc pre-gap against tracks, without pre-gap track
            pre_gap_image = audiotools.FlacAudio.from_pcm(
                os.path.join(self.temp_dir, "image2.flac"),
                audiotools.PCMCat([self.pre_gap.to_pcm(),
                                   self.track1.to_pcm(),
                                   self.track2.to_pcm(),
                                   self.track3.to_pcm()]))

            pre_gap_image.set_cuesheet(self.pre_gap_sheet)
            self.assertIsNotNone(pre_gap_image.get_cuesheet())

            if seektable:
                self.assertTrue(pre_gap_image.seekable())
            else:
                m = pre_gap_image.get_metadata()
                m.replace_blocks(3, [])
                pre_gap_image.update_metadata(m)
                self.assertFalse(pre_gap_image.seekable())

            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  pre_gap_image.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 3, pre_gap_image, self.track1)
            self.__compare_files__(2, 3, pre_gap_image, self.track2)
            self.__compare_files__(3, 3, pre_gap_image, self.track3)

            # test image with disc pre-gap against tracks, with pre-gap track
            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  pre_gap_image.filename,
                                  self.pre_gap.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 4, pre_gap_image, self.pre_gap)
            self.__compare_files__(2, 4, pre_gap_image, self.track1)
            self.__compare_files__(3, 4, pre_gap_image, self.track2)
            self.__compare_files__(4, 4, pre_gap_image, self.track3)

    @UTIL_TRACKCMP
    def test_external_cuesheet(self):
        from audiotools.cue import Cuesheet

        for seekable in [True, False]:
            # test image with no disc pre-gap against tracks
            no_pre_gap_image = audiotools.FlacAudio.from_pcm(
                os.path.join(self.temp_dir, "image1.flac"),
                audiotools.PCMCat([self.track1.to_pcm(),
                                   self.track2.to_pcm(),
                                   self.track3.to_pcm()]))

            no_pre_gap_cue = os.path.join(self.temp_dir, "image1.cue")
            with open(no_pre_gap_cue, "w") as w:
                w.write(Cuesheet.converted(self.no_pre_gap_sheet).build())

            self.assertIsNone(no_pre_gap_image.get_cuesheet())

            if seekable:
                self.assertTrue(no_pre_gap_image.seekable())
            else:
                m = no_pre_gap_image.get_metadata()
                m.replace_blocks(3, [])
                no_pre_gap_image.update_metadata(m)
                self.assertFalse(no_pre_gap_image.seekable())

            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  "--cue", no_pre_gap_cue,
                                  no_pre_gap_image.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 3, no_pre_gap_image, self.track1)
            self.__compare_files__(2, 3, no_pre_gap_image, self.track2)
            self.__compare_files__(3, 3, no_pre_gap_image, self.track3)

            # test image with disc pre-gap against tracks, without pre-gap track
            pre_gap_image = audiotools.FlacAudio.from_pcm(
                os.path.join(self.temp_dir, "image2.flac"),
                audiotools.PCMCat([self.pre_gap.to_pcm(),
                                   self.track1.to_pcm(),
                                   self.track2.to_pcm(),
                                   self.track3.to_pcm()]))

            pre_gap_cue = os.path.join(self.temp_dir, "image2.cue")
            with open(pre_gap_cue, "w") as w:
                w.write(Cuesheet.converted(self.pre_gap_sheet).build())

            self.assertIsNone(pre_gap_image.get_cuesheet())

            if seekable:
                self.assertTrue(pre_gap_image.seekable())
            else:
                m = pre_gap_image.get_metadata()
                m.replace_blocks(3, [])
                pre_gap_image.update_metadata(m)
                self.assertFalse(pre_gap_image.seekable())

            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  "--cue", pre_gap_cue,
                                  pre_gap_image.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 3, pre_gap_image, self.track1)
            self.__compare_files__(2, 3, pre_gap_image, self.track2)
            self.__compare_files__(3, 3, pre_gap_image, self.track3)

            # test image with disc pre-gap against tracks, with pre-gap track
            self.assertEqual(
                self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                  "--cue", pre_gap_cue,
                                  pre_gap_image.filename,
                                  self.pre_gap.filename,
                                  self.track1.filename,
                                  self.track2.filename,
                                  self.track3.filename]), 0)

            self.__compare_files__(1, 4, pre_gap_image, self.pre_gap)
            self.__compare_files__(2, 4, pre_gap_image, self.track1)
            self.__compare_files__(3, 4, pre_gap_image, self.track2)
            self.__compare_files__(4, 4, pre_gap_image, self.track3)


class tracklength(UtilTest):
    @UTIL_TRACKLENGTH
    def test_version(self):
        self.assertEqual(self.__run_app__(["tracklength",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    @UTIL_TRACKLENGTH
    def test_tracklength(self):
        import shutil
        from audiotools.text import (LAB_TRACKLENGTH_FILE_FORMAT,
                                     LAB_TRACKLENGTH_FILE_COUNT,
                                     LAB_TRACKLENGTH_FILE_LENGTH,
                                     LAB_TRACKLENGTH_FILE_SIZE,
                                     LAB_TRACKLENGTH,
                                     DIV)

        track1 = audiotools.open("1s.flac")
        track2 = audiotools.open("1m.flac")
        track3 = audiotools.open("1h.flac")
        self.assertEqual(track1.seconds_length(), 1)
        self.assertEqual(track2.seconds_length(), 60)
        self.assertEqual(track3.seconds_length(), 60 * 60)
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac"]), 0)
        self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>4s}".format(
            LAB_TRACKLENGTH_FILE_FORMAT,
            LAB_TRACKLENGTH_FILE_COUNT,
            LAB_TRACKLENGTH_FILE_LENGTH,
            LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"{} {} {} {}".format(
            DIV * 6,
            DIV * 5,
            DIV * 7,
            DIV * 4))
        self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>4d}".format(
            u"flac",
            1,
            LAB_TRACKLENGTH.format(
                hours=0, minutes=0, seconds=1),
            380))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1s.flac"]), 0)
        self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>4s}".format(
            LAB_TRACKLENGTH_FILE_FORMAT,
            LAB_TRACKLENGTH_FILE_COUNT,
            LAB_TRACKLENGTH_FILE_LENGTH,
            LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"{} {} {} {}".format(
            DIV * 6,
            DIV * 5,
            DIV * 7,
            DIV * 4))
        self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>4d}".format(
            u"flac",
            2,
            LAB_TRACKLENGTH.format(
                hours=0, minutes=0, seconds=2),
            760))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac"]), 0)
        self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>4s}".format(
            LAB_TRACKLENGTH_FILE_FORMAT,
            LAB_TRACKLENGTH_FILE_COUNT,
            LAB_TRACKLENGTH_FILE_LENGTH,
            LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"{} {} {} {}".format(
            DIV * 6,
            DIV * 5,
            DIV * 7,
            DIV * 4))
        self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>4s}".format(
            u"flac",
            2,
            LAB_TRACKLENGTH.format(
                hours=0, minutes=1, seconds=1),
            u"9.8K"))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1m.flac"]), 0)
        self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>5s}".format(
            LAB_TRACKLENGTH_FILE_FORMAT,
            LAB_TRACKLENGTH_FILE_COUNT,
            LAB_TRACKLENGTH_FILE_LENGTH,
            LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"{} {} {} {}".format(
            DIV * 6,
            DIV * 5,
            DIV * 7,
            DIV * 5))
        self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>5s}".format(
            u"flac",
            3,
            LAB_TRACKLENGTH.format(
                hours=0, minutes=2, seconds=1),
            u"19.1K"))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1h.flac"]), 0)
        self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>5s}".format(
            LAB_TRACKLENGTH_FILE_FORMAT,
            LAB_TRACKLENGTH_FILE_COUNT,
            LAB_TRACKLENGTH_FILE_LENGTH,
            LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"{} {} {} {}".format(
            DIV * 6,
            DIV * 5,
            DIV * 7,
            DIV * 5))
        self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>5s}".format(
            u"flac",
            3,
            LAB_TRACKLENGTH.format(
                hours=1, minutes=1, seconds=1),
            u"22.5K"))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1h.flac",
                                           "1h.flac"]), 0)
        self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>5s}".format(
            LAB_TRACKLENGTH_FILE_FORMAT,
            LAB_TRACKLENGTH_FILE_COUNT,
            LAB_TRACKLENGTH_FILE_LENGTH,
            LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"{} {} {} {}".format(
            DIV * 6,
            DIV * 5,
            DIV * 7,
            DIV * 5))
        self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>5s}".format(
            u"flac",
            4,
            LAB_TRACKLENGTH.format(
                hours=2, minutes=1, seconds=1),
            u"35.3K"))

        tempdir = tempfile.mkdtemp()
        try:
            shutil.copy(track1.filename, tempdir)
            shutil.copy(track2.filename, tempdir)
            shutil.copy(track3.filename, tempdir)
            self.assertEqual(self.__run_app__(["tracklength", tempdir]), 0)
            self.__check_output__(u"{:>6s} {:>5s} {:>7s} {:>5s}".format(
                LAB_TRACKLENGTH_FILE_FORMAT,
                LAB_TRACKLENGTH_FILE_COUNT,
                LAB_TRACKLENGTH_FILE_LENGTH,
                LAB_TRACKLENGTH_FILE_SIZE))
            self.__check_output__(u"{} {} {} {}".format(
                DIV * 6,
                DIV * 5,
                DIV * 7,
                DIV * 5))
            self.__check_output__(u"{:>6s} {:>5d} {:>7s} {:>5s}".format(
                u"flac",
                3,
                LAB_TRACKLENGTH.format(
                    hours=1, minutes=1, seconds=1),
                u"22.5K"))
        finally:
            from shutil import rmtree
            rmtree(tempdir)

    @UTIL_TRACKLENGTH
    def test_unicode(self):
        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"track.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        for filename in filenames:
            if os.path.isfile(filename):
                os.unlink(filename)

            track = audiotools.FlacAudio.from_pcm(
                filename,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(["tracklength", filename]), 0)

            if os.path.isfile(filename):
                os.unlink(filename)


class tracklint(UtilTest):
    @UTIL_TRACKLINT
    def test_version(self):
        self.assertEqual(self.__run_app__(["tracklint",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    @UTIL_TRACKLINT
    def test_vorbis(self):
        for audio_class in [audiotools.VorbisAudio]:
            bad_vorbiscomment = audiotools.VorbisComment(
                [u"TITLE=Track Name  ",
                 u"TRACKNUMBER=02",
                 u"DISCNUMBER=003",
                 u"ARTIST=  Some Artist",
                 u"CATALOG=",
                 u"YEAR=  ",
                 u"COMMENT=  Some Comment  "],
                u"Vendor String")

            fixed = audiotools.MetaData(
                track_name=u"Track Name",
                track_number=2,
                album_number=3,
                artist_name=u"Some Artist",
                comment=u"Some Comment")

            self.assertNotEqual(fixed, bad_vorbiscomment)

            tempdir = tempfile.mkdtemp()
            tempmp = os.path.join(tempdir,
                                  "track.{}".format(audio_class.SUFFIX))
            try:
                track = audio_class.from_pcm(tempmp, BLANK_PCM_Reader(10))

                track.set_metadata(bad_vorbiscomment)
                metadata = track.get_metadata()
                if isinstance(metadata, audiotools.FlacMetaData):
                    metadata = metadata.get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                self.assertEqual(metadata, bad_vorbiscomment)
                for (key, value) in metadata.items():
                    self.assertEqual(value, bad_vorbiscomment[key])

                original_checksum = md5()
                with open(track.filename, 'rb') as f:
                    audiotools.transfer_data(f.read, original_checksum.update)

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--fix",
                                 track.filename])

                metadata = track.get_metadata()
                self.assertNotEqual(metadata, bad_vorbiscomment)
                self.assertEqual(metadata, fixed)
            finally:
                from shutil import rmtree
                rmtree(tempdir)

    @UTIL_TRACKLINT
    def test_flac1(self):
        # copy the test track to a temporary location
        with tempfile.NamedTemporaryFile(suffix=".flac") as tempflac:
            with open("flac-id3.flac", "rb") as f:
                audiotools.transfer_data(f.read, tempflac.write)
            tempflac.flush()

            tempflac.seek(0, 0)
            self.assertEqual(tempflac.read(3), b"ID3")
            tempflac.seek(-0x80, 2)
            self.assertEqual(tempflac.read(3), b"TAG")

            # ensure that FLACs tagged with ID3v2/ID3v1 comments are scrubbed
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", "--fix", tempflac.name]), 0)
            flac = audiotools.open(tempflac.name)
            md5sum = md5()
            audiotools.transfer_framelist_data(flac.to_pcm(), md5sum.update)
            self.assertEqual(md5sum.hexdigest(),
                             "9a0ab096c517a627b0ab5a0b959e5f36")

    @UTIL_TRACKLINT
    def test_flac2(self):
        # copy the test track to a temporary location
        with tempfile.NamedTemporaryFile(suffix=".flac") as tempflac:
            with open("flac-disordered.flac", "rb") as f:
                audiotools.transfer_data(f.read, tempflac.write)
            tempflac.flush()

            tempflac.seek(0, 0)
            self.assertEqual(tempflac.read(4), b'fLaC')
            self.assertNotEqual(ord(tempflac.read(1)) & 0x07, 0)

            # ensure that FLACs with improper metadata ordering are reordered
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", "--fix", tempflac.name]), 0)
            flac = audiotools.open(tempflac.name)
            md5sum = md5()
            audiotools.transfer_framelist_data(flac.to_pcm(), md5sum.update)
            self.assertEqual(md5sum.hexdigest(),
                             "9a0ab096c517a627b0ab5a0b959e5f36")

    @UTIL_TRACKLINT
    def test_flac3(self):
        # create a small temporary flac
        with tempfile.NamedTemporaryFile(suffix=".flac") as tempflacfile:
            tempflac = audiotools.FlacAudio.from_pcm(
                tempflacfile.name,
                BLANK_PCM_Reader(3))

            # build an image from metadata
            image = audiotools.Image.new(TEST_COVER1, u"Description", 0)
            good_mime_type = image.mime_type
            good_width = image.width
            good_height = image.height
            good_depth = image.color_depth
            good_count = image.color_count
            good_description = image.description
            good_type = image.type

            # update image with bogus fields
            image.width = 0
            image.height = 0
            image.color_depth = 0
            image.color_count = 0
            image.mime_type = u'img/jpg'

            # tag flac with bogus fields image
            metadata = tempflac.get_metadata()
            metadata.add_image(image)
            tempflac.update_metadata(metadata)

            # ensure bogus fields stick
            image = tempflac.get_metadata().images()[0]
            self.assertEqual(image.width, 0)
            self.assertEqual(image.height, 0)
            self.assertEqual(image.color_depth, 0)
            self.assertEqual(image.color_count, 0)
            self.assertEqual(image.mime_type, u'img/jpg')

            # fix flac with tracklint
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", tempflac.filename, "--fix"]),
                0)

            # ensure bogus fields are fixed
            tempflac = audiotools.open(tempflacfile.name)
            image = tempflac.get_metadata().images()[0]
            self.assertEqual(image.width, good_width)
            self.assertEqual(image.height, good_height)
            self.assertEqual(image.color_depth, good_depth)
            self.assertEqual(image.color_count, good_count)
            self.assertEqual(image.mime_type, good_mime_type)
            self.assertEqual(image.description, good_description)
            self.assertEqual(image.type, good_type)

    @UTIL_TRACKLINT
    def test_flac4(self):
        # create a small temporary FLAC
        with tempfile.NamedTemporaryFile(suffix=".flac") as tempflacfile:
            # update it with the data from "flac-nonmd5.flac"
            with open("flac-nonmd5.flac", "rb") as f:
                audiotools.transfer_data(f.read, tempflacfile.write)
            tempflacfile.flush()

            # ensure MD5SUM is empty
            tempflac = audiotools.open(tempflacfile.name)
            self.assertEqual(tempflac.__md5__, b"\x00" * 16)

            # ensure file verifies okay
            self.assertEqual(tempflac.verify(), True)

            # fix FLAC with tracklint
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", tempflac.filename, "--fix"]),
                0)

            # ensure file's new MD5SUM matches its actual MD5SUM
            tempflac2 = audiotools.open(tempflacfile.name)
            self.assertEqual(tempflac2.__md5__,
                             b"\xd2\xb1\x20\x19\x90\x19\xb6\x39" +
                             b"\xd5\xa7\xe2\xb3\x46\x3e\x9c\x97")
            self.assertEqual(tempflac2.verify(), True)

    @UTIL_TRACKLINT
    def test_apev2(self):
        for audio_class in [audiotools.WavPackAudio]:
            bad_apev2 = audiotools.ApeTag(
                [audiotools.ape.ApeTagItem(0, False, b"Title",
                                           b"Track Name  "),
                 audiotools.ape.ApeTagItem(0, False, b"Track", b"02"),
                 audiotools.ape.ApeTagItem(0, False, b"Artist",
                                           b"  Some Artist"),
                 audiotools.ape.ApeTagItem(0, False, b"Catalog", b""),
                 audiotools.ape.ApeTagItem(0, False, b"Year", b"  "),
                 audiotools.ape.ApeTagItem(0, False, b"Comment",
                                           b"  Some Comment  ")])

            fixed = audiotools.MetaData(
                track_name=u"Track Name",
                track_number=2,
                artist_name=u"Some Artist",
                comment=u"Some Comment")

            self.assertNotEqual(fixed, bad_apev2)

            tempdir = tempfile.mkdtemp()
            tempmp = os.path.join(tempdir,
                                  "track.{}".format(audio_class.SUFFIX))
            try:
                track = audio_class.from_pcm(tempmp, BLANK_PCM_Reader(10))

                track.set_metadata(bad_apev2)
                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_apev2)
                for key in metadata.keys():
                    self.assertEqual(metadata[key].data, bad_apev2[key].data)

                original_checksum = md5()
                with open(track.filename, 'rb') as f:
                    audiotools.transfer_data(f.read, original_checksum.update)

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--fix",
                                 track.filename])

                metadata = track.get_metadata()
                self.assertNotEqual(metadata, bad_apev2)
                self.assertEqual(metadata, fixed)
            finally:
                from shutil import rmtree
                rmtree(tempdir)

    def __id3_text__(self, bad_id3v2):
        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            album_number=3,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed, bad_id3v2)

        tempdir = tempfile.mkdtemp()
        tempmp = os.path.join(tempdir,
                              "track.{}".format(audiotools.MP3Audio.SUFFIX))
        try:
            track = audiotools.MP3Audio.from_pcm(
                tempmp,
                BLANK_PCM_Reader(10))

            track.update_metadata(bad_id3v2)
            metadata = track.get_metadata()
            self.assertEqual(metadata, bad_id3v2)
            for (key, value) in metadata.items():
                self.assertEqual(value, bad_id3v2[key])

            original_checksum = md5()
            with open(track.filename, 'rb') as f:
                audiotools.transfer_data(f.read, original_checksum.update)

            subprocess.call(["tracklint",
                             "-V", "quiet",
                             "--fix",
                             track.filename])

            metadata = track.get_metadata()
            self.assertNotEqual(metadata, bad_id3v2)
            self.assertEqual(metadata, fixed)
        finally:
            from shutil import rmtree
            rmtree(tempdir)

    def __id3_images__(self, metadata_class, bad_image, fixed_image):
        with tempfile.NamedTemporaryFile(
            suffix="." + audiotools.MP3Audio.SUFFIX) as temp_file:
            temp_track = audiotools.MP3Audio.from_pcm(
                temp_file.name,
                BLANK_PCM_Reader(5))
            metadata = metadata_class([])
            metadata.add_image(bad_image)
            temp_track.set_metadata(metadata)

            # first, ensure that the bad_image's fields stick
            bad_image2 = temp_track.get_metadata().images()[0]
            for attr in ["data", "mime_type", "width", "height",
                         "color_depth", "color_count", "description",
                         "type"]:
                self.assertEqual(getattr(bad_image2, attr),
                                 getattr(bad_image, attr))

            # fix the track with tracklint
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", "--fix", temp_file.name]),
                0)
            temp_track = audiotools.open(temp_file.name)

            # then, ensure that the good fields are now in place
            good_image = temp_track.get_metadata().images()[0]
            for attr in ["data", "mime_type", "width", "height",
                         "color_depth", "color_count", "description",
                         "type"]:
                self.assertEqual(getattr(good_image, attr),
                                 getattr(fixed_image, attr))

    @UTIL_TRACKLINT
    def test_id3v22(self):
        self.__id3_text__(
            audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(
                    b"TT2", u"Track Name  "),
                 audiotools.id3.ID3v22_T__Frame.converted(
                     b"TRK", u"02"),
                 audiotools.id3.ID3v22_T__Frame.converted(
                     b"TPA", u"003"),
                 audiotools.id3.ID3v22_T__Frame.converted(
                     b"TP1", u"  Some Artist\u0000"),
                 audiotools.id3.ID3v22_T__Frame.converted(
                     b"TRC", u""),
                 audiotools.id3.ID3v22_T__Frame.converted(
                     b"TYE", u""),
                 audiotools.id3.ID3v22_COM_Frame.converted(
                     b"COM", u"  Some Comment  ")]))

        # ID3v2.2 doesn't store most image fields internally
        # so there's little point in testing them for inaccuracies

    @UTIL_TRACKLINT
    def test_id3v23(self):
        self.__id3_text__(
            audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(
                    b"TIT2", u"Track Name  "),
                 audiotools.id3.ID3v23_T___Frame.converted(
                     b"TRCK", u"02"),
                 audiotools.id3.ID3v23_T___Frame.converted(
                     b"TPOS", u"003"),
                 audiotools.id3.ID3v23_T___Frame.converted(
                     b"TPE1", u"  Some Artist\u0000"),
                 audiotools.id3.ID3v23_T___Frame.converted(
                     b"TYER", u""),
                 audiotools.id3.ID3v23_T___Frame.converted(
                     b"TCOP", u""),
                 audiotools.id3.ID3v23_COMM_Frame.converted(
                     b"COMM", u"  Some Comment  ")]))

        good_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)
        bad_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)

        # ID3v2.3 only stores MIME type internally
        # the rest are derived
        bad_image.width = 500
        bad_image.height = 500
        bad_image.color_depth = 24
        bad_image.color_count = 0
        bad_image.mime_type = u'img/jpg'

        self.__id3_images__(audiotools.ID3v23Comment,
                            bad_image,
                            good_image)

    @UTIL_TRACKLINT
    def test_id3v24(self):
        self.__id3_text__(
            audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(
                    b"TIT2", u"Track Name  "),
                 audiotools.id3.ID3v24_T___Frame.converted(
                     b"TRCK", u"02"),
                 audiotools.id3.ID3v24_T___Frame.converted(
                     b"TPOS", u"003"),
                 audiotools.id3.ID3v24_T___Frame.converted(
                     b"TPE1", u"  Some Artist\u0000"),
                 audiotools.id3.ID3v24_T___Frame.converted(
                     b"TYER", u""),
                 audiotools.id3.ID3v24_T___Frame.converted(
                     b"TCOP", u""),
                 audiotools.id3.ID3v24_COMM_Frame.converted(
                     b"COMM", u"  Some Comment  ")]))

        good_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)
        bad_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)

        # ID3v2.4 only stores MIME type internally
        # the rest are derived
        bad_image.width = 500
        bad_image.height = 500
        bad_image.color_depth = 24
        bad_image.color_count = 0
        bad_image.mime_type = u'img/jpg'

        self.__id3_images__(audiotools.ID3v24Comment,
                            bad_image,
                            good_image)

    @UTIL_TRACKLINT
    def test_mp3(self):
        from audiotools.text import ERR_ENCODING_ERROR

        track_file = tempfile.NamedTemporaryFile(
            suffix="." + audiotools.MP3Audio.SUFFIX)
        track_file_stat = os.stat(track_file.name)[0]
        try:
            track = audiotools.MP3Audio.from_pcm(track_file.name,
                                                 BLANK_PCM_Reader(5))
            track.set_metadata(
                audiotools.MetaData(
                    track_name=u"Track Name ",
                    track_number=1))
            if track.get_metadata() is not None:
                # unwritable file
                os.chmod(track_file.name, 0o400)

                self.assertEqual(
                    self.__run_app__(
                        ["tracklint", "--fix", track.filename]), 1)

                self.__check_error__(
                    ERR_ENCODING_ERROR.format(
                        audiotools.Filename(track.filename)))
        finally:
            os.chmod(track_file.name, track_file_stat)
            track_file.close()

    @UTIL_TRACKLINT
    def test_m4a(self):
        from audiotools.m4a import M4A_Tree_Atom
        from audiotools.m4a import M4A_META_Atom
        from audiotools.m4a import M4A_HDLR_Atom
        from audiotools.m4a import M4A_ILST_Leaf_Atom
        from audiotools.m4a import M4A_ILST_Unicode_Data_Atom
        from audiotools.m4a import M4A_ILST_TRKN_Data_Atom
        from audiotools.m4a import M4A_ILST_DISK_Data_Atom
        from audiotools.m4a import M4A_FREE_Atom

        bad_m4a = M4A_META_Atom(
            0, 0,
            [M4A_HDLR_Atom(0, 0, b'\x00\x00\x00\x00',
                           b'mdir', b'appl', 0, 0, b'', 0),
             M4A_Tree_Atom(
                 b'ilst',
                 [M4A_ILST_Leaf_Atom(
                     b'\xa9nam',
                     [M4A_ILST_Unicode_Data_Atom(
                         0, 1,
                         b'Track Name  ')]),
                  M4A_ILST_Leaf_Atom(
                     b'\xa9ART',
                     [M4A_ILST_Unicode_Data_Atom(
                         0, 1,
                         b'  Some Artist')]),
                  M4A_ILST_Leaf_Atom(
                     b'cprt',
                     [M4A_ILST_Unicode_Data_Atom(
                         0, 1,
                         b'')]),
                  M4A_ILST_Leaf_Atom(
                     b'\xa9day',
                     [M4A_ILST_Unicode_Data_Atom(
                         0, 1,
                         b'  ')]),
                  M4A_ILST_Leaf_Atom(
                     b'\xa9cmt',
                     [M4A_ILST_Unicode_Data_Atom(
                         0, 1,
                         b'  Some Comment  ')]),
                  M4A_ILST_Leaf_Atom(
                      b'trkn',
                      [M4A_ILST_TRKN_Data_Atom(2, 0)]),
                  M4A_ILST_Leaf_Atom(
                      b'disk',
                      [M4A_ILST_DISK_Data_Atom(3, 0)])]),
             M4A_FREE_Atom(1024)])

        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            track_total=None,
            album_number=3,
            album_total=None,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed, bad_m4a)

        for audio_class in [audiotools.M4AAudio,
                            audiotools.ALACAudio]:
            tempdir = tempfile.mkdtemp()
            tempmp = os.path.join(tempdir,
                                  "track.{}".format(audio_class.SUFFIX))
            try:
                track = audio_class.from_pcm(
                    tempmp,
                    BLANK_PCM_Reader(10))

                track.update_metadata(bad_m4a)
                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_m4a)
                for leaf in metadata.ilst_atom():
                    self.assertEqual(leaf, bad_m4a.ilst_atom()[leaf.name])
            finally:
                from shutil import rmtree
                rmtree(tempdir)

    @UTIL_TRACKLINT
    def test_modtime1(self):
        import stat

        for audio_class in audiotools.AVAILABLE_TYPES:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as track_file:
                track = audio_class.from_pcm(track_file.name,
                                             BLANK_PCM_Reader(5))
                metadata = audiotools.MetaData(
                    track_name=u"Track Name",
                    track_number=1,
                    track_total=2)
                track.set_metadata(metadata)
                if track.get_metadata() is not None:
                    orig_stat = os.stat(track.filename)
                    time.sleep(1)

                    # should make no metadata changes
                    self.assertEqual(
                        self.__run_app__(
                            ["tracklint", "--fix", track.filename]), 0)

                    self.assertEqual(track.get_metadata(),
                                     metadata)

                    new_stat = os.stat(track.filename)

                    for field in [stat.ST_MODE,
                                  stat.ST_INO,
                                  stat.ST_DEV,
                                  stat.ST_NLINK,
                                  stat.ST_UID,
                                  stat.ST_GID,
                                  stat.ST_SIZE,
                                  stat.ST_MTIME,
                                  stat.ST_CTIME]:
                        self.assertEqual(orig_stat[field], new_stat[field])

    @UTIL_TRACKLINT
    def test_modtime2(self):
        import stat

        for audio_class in audiotools.AVAILABLE_TYPES:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as track_file:
                track = audio_class.from_pcm(track_file.name,
                                             BLANK_PCM_Reader(5))
                metadata = audiotools.MetaData(
                    track_name=u"Track Name",
                    track_number=1,
                    track_total=2)
                track.set_metadata(metadata)
                if track.get_metadata() is not None:
                    orig_stat = os.stat(track.filename)
                    time.sleep(1)

                    # should make no metadata changes
                    self.assertEqual(
                        self.__run_app__(
                            ["tracklint",
                             "--fix", track.filename]), 0)

                    self.assertEqual(track.get_metadata(),
                                     metadata)

                    new_stat = os.stat(track.filename)

                    for field in [stat.ST_MODE,
                                  stat.ST_INO,
                                  stat.ST_DEV,
                                  stat.ST_NLINK,
                                  stat.ST_UID,
                                  stat.ST_GID,
                                  stat.ST_SIZE,
                                  stat.ST_MTIME,
                                  stat.ST_CTIME]:
                        self.assertEqual(orig_stat[field], new_stat[field])

    @UTIL_TRACKLINT
    def test_unicode(self):
        track_filenames = [u"track.flac",
                           u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']

        for filename in track_filenames:
            if PY3:
                input_filename = filename
            else:
                input_filename = filename.encode("UTF-8")

            if os.path.isfile(input_filename):
                os.unlink(input_filename)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                BLANK_PCM_Reader(1))

            metadata = track.get_metadata()
            metadata.track_name = u"Track Name "
            track.update_metadata(metadata)

            self.assertEqual(
                audiotools.open(input_filename).get_metadata().track_name,
                u"Track Name ")

            self.assertEqual(
                self.__run_app__(["tracklint",
                                  "--fix",
                                  input_filename]), 0)

            self.assertEqual(
                audiotools.open(input_filename).get_metadata().track_name,
                u"Track Name")

            if os.path.isfile(input_filename):
                os.unlink(input_filename)


class trackplay(UtilTest):
    @UTIL_TRACKPLAY
    def test_version(self):
        self.assertEqual(self.__run_app__(["trackplay",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))


class trackrename(UtilTest):
    @UTIL_TRACKRENAME
    def setUp(self):
        self.type = audiotools.FlacAudio

        self.format = "%(track_number)2.2d.%(suffix)s"

        self.input_dir = tempfile.mkdtemp()

        self.track_names = ["02 - name." + self.type.SUFFIX,
                            "name." + self.type.SUFFIX,
                            "02 - name." + self.type.SUFFIX,
                            "name." + self.type.SUFFIX]
        self.track_metadata = [None,
                               None,
                               audiotools.MetaData(track_name=u"Track 1",
                                                   album_name=u"Album 1",
                                                   artist_name=u"Artist 1",
                                                   track_number=1),
                               audiotools.MetaData(track_name=u"Track 1",
                                                   album_name=u"Album 1",
                                                   artist_name=u"Artist 1",
                                                   track_number=1)]

    @UTIL_TRACKRENAME
    def tearDown(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

    @UTIL_TRACKRENAME
    def test_version(self):
        self.assertEqual(self.__run_app__(["trackrename",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def clean_input_directory(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))

    def populate_options(self, options):
        populated = []
        for option in options:
            if option == '--format':
                populated.append(option)
                populated.append(self.format)
            else:
                populated.append(option)
        return populated

    @UTIL_TRACKRENAME
    def test_options(self):
        from audiotools.text import LAB_ENCODE

        all_options = ["--format"]
        for count in range(0, len(all_options) + 1):
            for (name, metadata) in zip(self.track_names, self.track_metadata):
                for options in Combinations(all_options, count):
                    options = self.populate_options(options)
                    self.clean_input_directory()
                    track = self.type.from_pcm(
                        os.path.join(self.input_dir, name),
                        BLANK_PCM_Reader(1))

                    if metadata is not None:
                        track.set_metadata(metadata)

                    original_metadata = track.get_metadata()

                    with open(track.filename, 'rb') as f:
                        track_data = f.read()

                    self.assertEqual(
                        self.__run_app__(["trackrename", "-V", "normal",
                                          track.filename] + options), 0)

                    if "--format" in options:
                        output_format = self.format
                    else:
                        output_format = None

                    if metadata is not None:
                        base_metadata = metadata
                    else:
                        # track number via filename applies
                        # only if the file has no other metadata
                        if (name.startswith("02") and
                            (original_metadata is None)):
                            base_metadata = audiotools.MetaData(
                                track_number=2)
                        else:
                            base_metadata = None

                    destination_filename = os.path.join(
                        self.input_dir,
                        self.type.track_name(
                            file_path="",
                            track_metadata=base_metadata,
                            format=output_format))

                    self.__check_info__(
                        LAB_ENCODE.format(
                            source=audiotools.Filename(
                                track.filename),
                            destination=audiotools.Filename(
                                destination_filename)))

                    # check that the file is identical
                    with open(destination_filename, 'rb') as f:
                        self.assertEqual(track_data, f.read())

    @UTIL_TRACKRENAME
    def test_duplicate(self):
        from audiotools.text import (ERR_DUPLICATE_FILE,
                                     ERR_DUPLICATE_OUTPUT_FILE)

        name1 = "01 - name." + self.type.SUFFIX
        name2 = "02 - name." + self.type.SUFFIX

        track1 = self.type.from_pcm(
            os.path.join(self.input_dir, name1),
            BLANK_PCM_Reader(1))
        track1.set_metadata(audiotools.MetaData(track_number=1))

        track2 = self.type.from_pcm(
            os.path.join(self.input_dir, name2),
            BLANK_PCM_Reader(1))
        track2.set_metadata(audiotools.MetaData(track_number=2))

        self.assertEqual(
            self.__run_app__(["trackrename", "-V", "normal",
                              "--format", self.format,
                              track1.filename, track1.filename]), 1)

        self.__check_error__(
            ERR_DUPLICATE_FILE.format(
                audiotools.Filename(track1.filename)))

        self.assertEqual(
            self.__run_app__(["trackrename", "-V", "normal",
                              "--format", "foo",
                              track1.filename, track2.filename]), 1)

        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE.format(
                audiotools.Filename(
                    os.path.join(os.path.dirname(track1.filename), "foo"))))

    @UTIL_TRACKRENAME
    def test_errors(self):
        from audiotools.text import (ERR_FILES_REQUIRED,
                                     ERR_UNKNOWN_FIELD,
                                     LAB_SUPPORTED_FIELDS)

        tempdir = tempfile.mkdtemp()
        tempdir_stat = os.stat(tempdir)[0]
        track = self.type.from_pcm(
            os.path.join(tempdir, "01 - track.{}".format(self.type.SUFFIX)),
            BLANK_PCM_Reader(1))
        track.set_metadata(audiotools.MetaData(track_name=u"Name",
                                               track_number=1,
                                               album_name=u"Album"))
        try:
            self.assertEqual(self.__run_app__(["trackrename"]), 2)

            self.assertEqual(
                self.__run_app__(
                    ["trackrename", "--format=%(foo)s", track.filename]), 1)

            self.__check_error__(ERR_UNKNOWN_FIELD.format("foo"))
            self.__check_info__(LAB_SUPPORTED_FIELDS)
            for field in sorted(audiotools.MetaData.FIELDS +
                                ("album_track_number", "suffix")):
                if field == 'track_number':
                    self.__check_info__(u"%(track_number)2.2d")
                else:
                    self.__check_info__(u"%%(%s)s" % (field))
            self.__check_info__(u"%(basename)s")

            if track.get_metadata() is not None:
                os.chmod(tempdir, tempdir_stat & 0x7555)

                self.assertEqual(
                    self.__run_app__(
                        ["trackrename",
                         '--format=%(album_name)s/%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]), 1)

                self.__check_error__(
                    u"[Errno 13] Permission denied: \'{}\'".format(
                        audiotools.Filename(
                            os.path.join(
                                os.path.dirname(track.filename), "Album"))))

                self.assertEqual(
                    self.__run_app__(
                        ["trackrename",
                         '--format=%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]), 1)

        finally:
            os.chmod(tempdir, tempdir_stat)
            os.unlink(track.filename)
            os.rmdir(tempdir)

    @UTIL_TRACKRENAME
    def test_unicode(self):
        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"file.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        format_strings = [f if PY3 else f.encode("UTF-8") for f in
                          [u"new_file.flac",
                           u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac']]

        for (file_path,
             format_string) in Possibilities(filenames, format_strings):
            if os.path.isfile(file_path):
                os.unlink(file_path)
            if os.path.isfile(format_string):
                os.unlink(format_string)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))

            self.assertTrue(os.path.isfile(file_path))
            self.assertFalse(os.path.isfile(format_string))

            self.assertEqual(
                self.__run_app__(
                    ["trackrename", "--format", format_string, file_path]), 0)

            self.assertFalse(os.path.isfile(file_path))
            self.assertTrue(os.path.isfile(format_string))

            if os.path.isfile(file_path):
                os.unlink(file_path)
            if os.path.isfile(format_string):
                os.unlink(format_string)


class tracksplit(UtilTest):
    @UTIL_TRACKSPLIT
    def setUp(self):
        self.type = audiotools.FlacAudio
        self.quality = "1"

        self.output_dir = tempfile.mkdtemp()
        self.format = "%(track_number)2.2d.%(suffix)s"

        self.unsplit_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.unsplit_metadata = audiotools.MetaData(
            track_name=u"Track 1",
            track_number=1,
            track_total=2,
            album_number=4,
            album_total=5,
            album_name=u"Album 1",
            artist_name=u"Artist 1",
            performer_name=u"Performer 1")
        self.cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        self.cuesheet.flush()

        self.cuesheet2 = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet2.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC ABCD00000001\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC ABCD00000002\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC ABCD00000003\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        self.cuesheet2.flush()

        self.cuesheet3 = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet3.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n')
        self.cuesheet3.flush()

        self.unsplit_file2 = tempfile.NamedTemporaryFile(suffix=".flac")

        self.stream = test_streams.Sine16_Stereo(793800, 44100,
                                                 8820.0, 0.70,
                                                 4410.0, 0.29, 1.0)

        self.cwd_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.cwd_dir)

        self.unwritable_dir = tempfile.mkdtemp()
        os.chmod(self.unwritable_dir, 0)

    @UTIL_TRACKSPLIT
    def tearDown(self):
        from shutil import rmtree

        os.chdir(self.original_dir)

        self.unsplit_file.close()
        self.unsplit_file2.close()
        self.cuesheet.close()
        self.cuesheet2.close()
        self.cuesheet3.close()

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

        rmtree(self.cwd_dir)

        os.chmod(self.unwritable_dir, 0o700)
        os.rmdir(self.unwritable_dir)

    def clean_output_dirs(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))

    @UTIL_TRACKSPLIT
    def test_version(self):
        self.assertEqual(self.__run_app__(["tracksplit",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def populate_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]
        for option in sorted(options):
            if option == '-t':
                populated.append(option)
                populated.append(self.type.NAME)
            elif option == '-q':
                populated.append(option)
                populated.append(self.quality)
            elif option == '-d':
                populated.append(option)
                populated.append(self.output_dir)
            elif option == '--format':
                populated.append(option)
                populated.append(self.format)
            elif option == '--cue':
                populated.append(option)
                populated.append(self.cuesheet.name)
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKSPLIT
    def test_options_no_embedded_cue(self):
        from audiotools.text import (ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_TRACKSPLIT_NO_CUESHEET,
                                     LAB_ENCODE)

        all_options = ["--cue", "-t", "-q", "-d", "--format"]

        self.stream.reset()
        track = self.type.from_pcm(self.unsplit_file.name, self.stream)
        track.set_metadata(self.unsplit_metadata)

        for count in range(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                options = self.populate_options(options)

                if "-t" in options:
                    output_type = audiotools.FlacAudio
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    ("1" not in output_type.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "--no-freedb", "--no-musicbrainz",
                                          "--no-replay-gain"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality="1", type=output_type.NAME))
                    continue

                if "--cue" not in options:
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "--no-freedb", "--no-musicbrainz",
                                          "--no-replay-gain"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(ERR_TRACKSPLIT_NO_CUESHEET)
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal",
                                      "-j", "1",
                                      "--no-freedb", "--no-musicbrainz",
                                      "--no-replay-gain"] +
                                     options + [track.filename]), 0)
                if "--format" in options:
                    output_format = self.format
                else:
                    output_format = None

                if "-d" in options:
                    output_dir = self.output_dir
                else:
                    output_dir = "."

                base_metadata = audiotools.MetaData(
                    track_total=3,
                    album_number=4,
                    album_total=5,
                    album_name=u"Album 1",
                    artist_name=u"Artist 1",
                    performer_name=u"Performer 1")

                output_filenames = []

                for i in range(3):
                    base_metadata.track_number = i + 1
                    output_filenames.append(
                        output_type.track_name(
                            file_path="",
                            track_metadata=base_metadata,
                            format=output_format))

                # check that the output is being generated correctly
                for (i, path) in enumerate(output_filenames):
                    self.__check_output__(
                        audiotools.output_progress(
                            LAB_ENCODE.format(
                                source=audiotools.Filename(track.filename),
                                destination=audiotools.Filename(
                                    os.path.join(output_dir, path))),
                            i + 1, len(output_filenames)))

                # make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.stream.reset()
                with audiotools.PCMCat([t.to_pcm() for t in
                                        output_tracks]) as pcmreader:
                    self.assertTrue(
                        audiotools.pcm_cmp(pcmreader, self.stream))

                # make sure metadata fits our expectations
                for i in range(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if metadata is not None:
                        self.assertEqual(metadata.track_name, None)
                        self.assertEqual(metadata.album_name, u"Album 1")
                        self.assertEqual(metadata.artist_name, u"Artist 1")

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)
                        self.assertEqual(metadata.album_number, 4)
                        self.assertEqual(metadata.album_total, 5)
                        self.assertEqual(metadata.performer_name,
                                         u"Performer 1")

                if "--cue" in options:
                    for (i, ISRC) in enumerate([u"JPPI00652340",
                                                u"JPPI00652349",
                                                u"JPPI00652341"]):
                        metadata = output_tracks[i].get_metadata()
                        if metadata is not None:
                            self.assertEqual(metadata.ISRC, ISRC)

    @UTIL_TRACKSPLIT
    def test_options_embedded_cue(self):
        from audiotools.text import (ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     LAB_ENCODE)

        all_options = ["--cue", "-t", "-q", "-d", "--format"]

        self.stream.reset()
        track = self.type.from_pcm(self.unsplit_file.name, self.stream)
        track.set_metadata(self.unsplit_metadata)
        track.set_cuesheet(audiotools.read_sheet(self.cuesheet2.name))
        self.assertIsNotNone(track.get_cuesheet())

        for count in range(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                options = self.populate_options(options)

                if "-t" in options:
                    output_type = audiotools.FlacAudio
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    ("1" not in output_type.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "--no-freedb", "--no-musicbrainz",
                                          "--no-replay-gain"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality="1", type=output_type.NAME))
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal",
                                      "-j", "1",
                                      "--no-freedb", "--no-musicbrainz",
                                      "--no-replay-gain"] +
                                     options + [track.filename]), 0)

                if "--format" in options:
                    output_format = self.format
                else:
                    output_format = None

                if "-d" in options:
                    output_dir = self.output_dir
                else:
                    output_dir = "."

                base_metadata = audiotools.MetaData(
                    track_total=3,
                    album_number=4,
                    album_total=5,
                    album_name=u"Album 1",
                    artist_name=u"Artist 1",
                    performer_name=u"Performer 1")

                output_filenames = []
                for i in range(3):
                    base_metadata.track_number = i + 1
                    output_filenames.append(
                        output_type.track_name(
                            "",
                            base_metadata,
                            output_format))

                # check that the output is being generated correctly
                for (i, path) in enumerate(output_filenames):
                    self.__check_output__(
                        audiotools.output_progress(
                            LAB_ENCODE.format(
                                source=audiotools.Filename(
                                    track.filename),
                                destination=audiotools.Filename(
                                    os.path.join(output_dir, path))),
                            i + 1, len(output_filenames)))

                # make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.stream.reset()
                with audiotools.PCMCat([t.to_pcm() for t in
                                        output_tracks]) as pcmreader:
                    self.assertTrue(
                        audiotools.pcm_cmp(pcmreader, self.stream))

                # make sure metadata fits our expectations
                for i in range(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if metadata is not None:
                        self.assertEqual(metadata.track_name, None)
                        self.assertEqual(metadata.album_name, u"Album 1")
                        self.assertEqual(metadata.artist_name, u"Artist 1")

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)
                        self.assertEqual(metadata.album_number, 4)
                        self.assertEqual(metadata.album_total, 5)
                        self.assertEqual(metadata.performer_name,
                                         u"Performer 1")

                # check ISRC data
                if "--cue" in options:
                    for (i, ISRC) in enumerate([u"JPPI00652340",
                                                u"JPPI00652349",
                                                u"JPPI00652341"]):
                        metadata = output_tracks[i].get_metadata()
                        if metadata is not None:
                            self.assertEqual(metadata.ISRC, ISRC)
                else:
                    for (i, ISRC) in enumerate([u"ABCD00000001",
                                                u"ABCD00000002",
                                                u"ABCD00000003"]):
                        metadata = output_tracks[i].get_metadata()
                        if metadata is not None:
                            self.assertEqual(metadata.ISRC, ISRC)

    @UTIL_TRACKSPLIT
    def test_unicode(self):
        import shutil

        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"track.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        cuesheets = [c if PY3 else c.encode("UTF-8") for c in
                     [u"cuesheet.cue",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.cue']]

        dirs = [d if PY3 else d.encode("UTF-8") for d in
                [u"testdir",
                 u'abc\xe0\xe7\xe8\u3041\u3044\u3046-dir']]

        formats = [f if PY3 else f.encode("UTF-8") for f in
                   [u"%(track_number)d.%(suffix)s",
                    u'%(track_number)d - abc\xe0\xe7\xe8\u3041\u3044\u3046.%(suffix)s']]

        for (input_filename,
             cuesheet_file,
             output_directory,
             output_format) in Possibilities(filenames, cuesheets,
                                             dirs, formats):
            if os.path.isfile(input_filename):
                os.unlink(input_filename)
            if os.path.isfile(cuesheet_file):
                os.unlink(cuesheet_file)
            if os.path.isdir(output_directory):
                shutil.rmtree(output_directory)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                EXACT_BLANK_PCM_Reader(sum([220500, 264600, 308700])))

            with open(cuesheet_file, "wb") as f:
                f.write(b'FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')

            self.assertEqual(
                self.__run_app__(
                    ["tracksplit",
                     "--type", "flac",
                     "--cue", cuesheet_file,
                     "--dir", output_directory,
                     "--format", output_format,
                     input_filename]), 0)

            output_filenames = [output_format % {"track_number": i,
                                                 "suffix": "flac"}
                                for i in range(1, 4)]
            for f in output_filenames:
                self.assertEqual(
                    os.path.isfile(os.path.join(output_directory, f)), True)

            tracks = [audiotools.open(os.path.join(output_directory, f))
                      for f in output_filenames]

            self.assertTrue(
                audiotools.pcm_cmp(
                    track.to_pcm(),
                    audiotools.PCMCat([t.to_pcm() for t in tracks])))

            if os.path.isfile(input_filename):
                os.unlink(input_filename)
            if os.path.isfile(cuesheet_file):
                os.unlink(cuesheet_file)
            if os.path.isdir(output_directory):
                shutil.rmtree(output_directory)

    def populate_bad_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]

        for option in sorted(options):
            if option == '-t':
                populated.append(option)
                populated.append("foo")
            elif option == '-q':
                populated.append(option)
                populated.append("bar")
            elif option == '-d':
                populated.append(option)
                populated.append(self.unwritable_dir)
            elif option == '--format':
                populated.append(option)
                populated.append("%(foo)s.%(suffix)s")
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKSPLIT
    def test_errors(self):
        from audiotools.text import (ERR_OUTPUT_IS_INPUT,
                                     ERR_DUPLICATE_OUTPUT_FILE,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_UNKNOWN_FIELD,
                                     LAB_SUPPORTED_FIELDS,
                                     ERR_1_FILE_REQUIRED,
                                     ERR_TRACKSPLIT_NO_CUESHEET,
                                     ERR_TRACKSPLIT_OVERLONG_CUESHEET)

        # ensure that unsplitting file to itself generates an error
        track = self.type.from_pcm(self.unsplit_file.name,
                                   BLANK_PCM_Reader(18))
        self.assertEqual(
            self.__run_app__(
                ["tracksplit", self.unsplit_file.name,
                 "--no-freedb", "--no-musicbrainz",
                 "--cue", self.cuesheet3.name,
                 "-d", os.path.dirname(self.unsplit_file.name),
                 "--format", os.path.basename(self.unsplit_file.name)]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT.format(
                audiotools.Filename(self.unsplit_file.name)))

        # ensure that unsplitting file to identical names generates an error
        self.assertEqual(
            self.__run_app__(
                ["tracksplit", self.unsplit_file.name,
                 "--no-freedb", "--no-musicbrainz",
                 "--cue", self.cuesheet.name,
                 "-d", os.path.dirname(self.unsplit_file.name),
                 "--format", "foo"]), 1)
        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE.format(
                audiotools.Filename(
                    os.path.join(os.path.dirname(self.unsplit_file.name),
                                 "foo"))))

        track1 = self.type.from_pcm(self.unsplit_file.name,
                                    BLANK_PCM_Reader(18))

        track2 = self.type.from_pcm(self.unsplit_file2.name,
                                    BLANK_PCM_Reader(5))

        all_options = ["-t", "-q", "-d", "--format"]

        for count in range(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_bad_options(options)

                if "-t" in options:
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-j", "1",
                                          track1.filename] +
                                         options),
                        2)
                    continue
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-j", "1", "--cue",
                                      self.cuesheet.name,
                                      track1.filename] +
                                     options),
                    1)

                if "-q" in options:
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE.format(
                            quality="bar", type=audiotools.DEFAULT_TYPE))
                    continue

                if "--format" in options:
                    self.__check_error__(ERR_UNKNOWN_FIELD.format("foo"))
                    self.__check_info__(LAB_SUPPORTED_FIELDS)
                    for field in sorted(audiotools.MetaData.FIELDS +
                                        ("album_track_number", "suffix")):
                        if field == 'track_number':
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    self.__check_info__(u"%(basename)s")
                    continue

                if "-d" in options:
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_type.track_name(
                            "",
                            audiotools.MetaData(track_number=1,
                                                track_total=3)))
                    self.__check_error__(
                        u"[Errno 13] Permission denied: \'{}\'".format(
                            output_path))
                    continue

        self.assertEqual(
            self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir]), 2)

        self.assertEqual(
            self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name, self.unsplit_file2.name]), 2)

        self.assertEqual(
            self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name]), 1)

        self.__check_error__(ERR_TRACKSPLIT_NO_CUESHEET)

        self.assertEqual(
            self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 "--cue", self.cuesheet.name, track2.filename]), 1)

        self.__check_error__(ERR_TRACKSPLIT_OVERLONG_CUESHEET)

        # FIXME? - check for broken cue sheet output?


class tracksplit_pre_gap(UtilTest):
    @UTIL_TRACKSPLIT
    def setUp(self):
        self.outdir = tempfile.mkdtemp()

    @UTIL_TRACKSPLIT
    def tearDown(self):
        from shutil import rmtree
        rmtree(self.outdir)

    @UTIL_TRACKSPLIT
    def test_pre_gap(self):
        pre_gap_size = 19404
        track_lengths = [21741300, 13847400, 22402800, 14420700,
                         10760400, 17904600, 13715100, 17022600,
                         30781800, 28312200]
        with open("trackcat_pre_gap.cue", "rb") as f:
            cuesheet_data = f.read()

        # write whole track to disk as image-type file
        temp_track_f = tempfile.NamedTemporaryFile(suffix=".wav")
        temp_track = audiotools.WaveAudio.from_pcm(
            temp_track_f.name,
            audiotools.PCMCat([
                EXACT_SILENCE_PCM_Reader(pre_gap_size),
                EXACT_RANDOM_PCM_Reader(sum(track_lengths))]),
            total_pcm_frames=pre_gap_size + sum(track_lengths))

        # write cuesheet to disk
        temp_cue_f = tempfile.NamedTemporaryFile(suffix=".cue")
        temp_cue_f.write(cuesheet_data)
        temp_cue_f.flush()

        # split image to directory using cuesheet
        self.assertEqual(
            self.__run_app__(["tracksplit",
                              "-d", self.outdir,
                              "--cue", temp_cue_f.name,
                              temp_track_f.name,
                              "--no-musicbrainz", "--no-freedb",
                              "-t", "wav",
                              "--format=%(track_number)2.2d.wav"]), 0)

        # ensure tracks in directory match expected lengths and data
        tracks = [audiotools.open(
            os.path.join(self.outdir, "{:02d}.wav".format(i)))
            for i in range(1, len(track_lengths) + 1)]

        for (i, track, expected_length) in zip(range(len(tracks)),
                                               tracks,
                                               track_lengths):
            self.assertEqual(track.total_frames(), expected_length)
            offset = pre_gap_size + sum(track_lengths[0:i])
            pcmreader = temp_track.to_pcm()
            self.assertEqual(pcmreader.seek(offset), offset)
            self.assertTrue(
                audiotools.pcm_cmp(
                    track.to_pcm(),
                    audiotools.PCMReaderHead(pcmreader, expected_length)))

        # cleanup temporary files
        temp_track_f.close()
        temp_cue_f.close()

    @UTIL_TRACKSPLIT
    def test_populated_pre_gap(self):
        pre_gap_size = 19404
        track_lengths = [21741300, 13847400, 22402800, 14420700,
                         10760400, 17904600, 13715100, 17022600,
                         30781800, 28312200]
        with open("trackcat_pre_gap.cue", "rb") as f:
            cuesheet_data = f.read()

        # write whole track to disk as image-type file
        temp_track_f = tempfile.NamedTemporaryFile(suffix=".wav")
        temp_track = audiotools.WaveAudio.from_pcm(
            temp_track_f.name,
            EXACT_RANDOM_PCM_Reader(pre_gap_size + sum(track_lengths)),
            total_pcm_frames=pre_gap_size + sum(track_lengths))

        # write cuesheet to disk
        temp_cue_f = tempfile.NamedTemporaryFile(suffix=".cue")
        temp_cue_f.write(cuesheet_data)
        temp_cue_f.flush()

        # split image to directory using cuesheet
        self.assertEqual(
            self.__run_app__(["tracksplit",
                              "-d", self.outdir,
                              "--cue", temp_cue_f.name,
                              temp_track_f.name,
                              "--no-musicbrainz", "--no-freedb",
                              "-t", "wav",
                              "--format=%(track_number)2.2d.wav"]), 0)

        # ensure tracks in directory match expected lengths and data
        tracks = [audiotools.open(
            os.path.join(self.outdir, "{:02d}.wav".format(i)))
            for i in range(0, len(track_lengths) + 1)]

        track = tracks[0]
        self.assertEqual(track.total_frames(), pre_gap_size)
        pcmreader = temp_track.to_pcm()
        self.assertTrue(
            audiotools.pcm_cmp(
                track.to_pcm(),
                audiotools.PCMReaderHead(pcmreader, pre_gap_size)))

        for (i, track, expected_length) in zip(range(len(tracks)),
                                               tracks[1:],
                                               track_lengths):
            self.assertEqual(track.total_frames(), expected_length)
            offset = pre_gap_size + sum(track_lengths[0:i])
            pcmreader = temp_track.to_pcm()
            self.assertEqual(pcmreader.seek(offset), offset)
            self.assertTrue(
                audiotools.pcm_cmp(
                    track.to_pcm(),
                    audiotools.PCMReaderHead(pcmreader, expected_length)))

        # cleanup temporary files
        temp_track_f.close()
        temp_cue_f.close()


class tracktag(UtilTest):
    @UTIL_TRACKTAG
    def setUp(self):
        track_file_base = tempfile.NamedTemporaryFile()
        self.initial_metadata = audiotools.MetaData(
            track_name=u"Name 1",
            track_number=1,
            track_total=2,
            album_name=u"Album 1",
            artist_name=u"Artist 1",
            album_number=3,
            album_total=4,
            ISRC=u'ABCD00000000',
            comment=u"Comment 1",
            compilation=False)

        self.image = audiotools.Image.new(TEST_COVER1, u"", 0)
        self.initial_metadata.add_image(self.image)

        track_base = audiotools.FlacAudio.from_pcm(
            track_file_base.name,
            BLANK_PCM_Reader(1))
        track_base.set_metadata(self.initial_metadata)
        with open(track_base.filename, 'rb') as f:
            self.track_data = f.read()
        track_file_base.close()

        self.track_file = tempfile.NamedTemporaryFile()

        self.comment_file = tempfile.NamedTemporaryFile(suffix=".txt")
        self.comment_file.write(b"Comment File")
        self.comment_file.flush()

    @UTIL_TRACKTAG
    def tearDown(self):
        self.track_file.close()
        self.comment_file.close()

    @UTIL_TRACKTAG
    def test_version(self):
        self.assertEqual(self.__run_app__(["tracktag",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))

    def populate_options(self, options):
        populated = []

        for option in sorted(options):
            if option == '--name':
                populated.append(option)
                populated.append("Name 3")
            elif option == '--artist':
                populated.append(option)
                populated.append("Artist 3")
            elif option == '--album':
                populated.append(option)
                populated.append("Album 3")
            elif option == '--number':
                populated.append(option)
                populated.append("5")
            elif option == '--track-total':
                populated.append(option)
                populated.append("6")
            elif option == '--album-number':
                populated.append(option)
                populated.append("7")
            elif option == '--album-total':
                populated.append(option)
                populated.append("8")
            elif option == '--comment':
                populated.append(option)
                populated.append("Comment 3")
            elif option == '--comment-file':
                populated.append(option)
                populated.append(self.comment_file.name)
            elif option == '--compilation':
                populated.append(option)
                populated.append('yes')
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKTAG
    def test_options(self):
        from audiotools.text import ERR_DUPLICATE_FILE

        # start out with a bit of sanity checking
        with open(self.track_file.name, 'wb') as f:
            f.write(self.track_data)

        track = audiotools.open(self.track_file.name)
        track.verify()
        metadata = track.get_metadata()
        self.assertEqual(metadata.images(),
                         [self.image])

        # Why not test all of tracktag's options?
        # The trouble is that it has 30 metadata-specific options
        # and the set of all possible combinations from 1 to 30 options
        # literally numbers in the millions.
        # Since most of those options are straight text,
        # we'll restrict the tests to the more interesting ones
        # which is still over 8000 different option combinations.
        most_options = ['-r', '--name', '--number', '--track-total',
                        '--album-number', '--comment', '--comment-file',
                        '--compilation']

        # ensure tagging the same file twice triggers an error
        self.assertEqual(
            self.__run_app__(["tracktag", "--name=Test",
                              self.track_file.name, self.track_file.name]), 1)
        self.__check_error__(
            ERR_DUPLICATE_FILE.format(
                audiotools.Filename(self.track_file.name)))

        for count in range(1, len(most_options) + 1):
            for options in Combinations(most_options, count):
                f = open(self.track_file.name, 'wb')
                f.write(self.track_data)
                f.close()

                options = self.populate_options(options)

                self.assertEqual(
                    self.__run_app__(["tracktag"] +
                                     options +
                                     [self.track_file.name]), 0)

                track = audiotools.open(self.track_file.name)
                track.verify()
                metadata = track.get_metadata()

                if "--name" in options:
                    self.assertEqual(metadata.track_name, u"Name 3")
                elif "-r" in options:
                    self.assertIsNone(metadata.track_name)
                else:
                    self.assertEqual(metadata.track_name, u"Name 1")

                if "--artist" in options:
                    self.assertEqual(metadata.artist_name, u"Artist 3")
                elif "-r" in options:
                    self.assertIsNone(metadata.artist_name)
                else:
                    self.assertEqual(metadata.artist_name, u"Artist 1")

                if "--album" in options:
                    self.assertEqual(metadata.album_name, u"Album 3")
                elif "-r" in options:
                    self.assertIsNone(metadata.album_name)
                else:
                    self.assertEqual(metadata.album_name, u"Album 1")

                if "--number" in options:
                    self.assertEqual(metadata.track_number, 5)
                elif "-r" in options:
                    self.assertIsNone(metadata.track_number)
                else:
                    self.assertEqual(metadata.track_number, 1)

                if "--track-total" in options:
                    self.assertEqual(metadata.track_total, 6)
                elif "-r" in options:
                    self.assertIsNone(metadata.track_total)
                else:
                    self.assertEqual(metadata.track_total, 2)

                if "--album-number" in options:
                    self.assertEqual(metadata.album_number, 7)
                elif "-r" in options:
                    self.assertIsNone(metadata.album_number)
                else:
                    self.assertEqual(metadata.album_number, 3)

                if "--album-total" in options:
                    self.assertEqual(metadata.album_total, 8)
                elif "-r" in options:
                    self.assertIsNone(metadata.album_total)
                else:
                    self.assertEqual(metadata.album_total, 4)

                if "--comment-file" in options:
                    self.assertEqual(metadata.comment, u"Comment File")
                elif "--comment" in options:
                    self.assertEqual(metadata.comment, u"Comment 3")
                elif "-r" in options:
                    self.assertIsNone(metadata.comment)
                else:
                    self.assertEqual(metadata.comment, u"Comment 1")

                if "--compilation" in options:
                    self.assertEqual(metadata.compilation, True)
                elif "-r" in options:
                    self.assertIsNone(metadata.compilation)
                else:
                    self.assertEqual(metadata.compilation, False)

                if "-r" in options:
                    self.assertIsNone(metadata.ISRC)
                else:
                    self.assertEqual(metadata.ISRC, u"ABCD00000000")

                if "--replay-gain" in options:
                    self.assert_(track.replay_gain() is not None)

    @UTIL_TRACKTAG
    def test_replaygain(self):
        from audiotools.text import (RG_REPLAYGAIN_ADDED,
                                     RG_REPLAYGAIN_APPLIED,
                                     RG_REPLAYGAIN_ADDED_TO_ALBUM)

        for audio_class in audiotools.AVAILABLE_TYPES:
            def temp_file():
                return tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)

            if not audio_class.supports_replay_gain():
                continue

            # try a track with no metadata
            with temp_file() as f:
                track = audio_class.from_pcm(
                    f.name,
                    test_streams.Sine16_Stereo(44100 * 5,
                                               44100,
                                               8820.0, 0.70,
                                               4410.0, 0.29, 1.0))

                self.assertEqual(
                    self.__run_app__(["tracktag",
                                      "-V", "normal",
                                      "--replay-gain", track.filename]), 0)
                self.__check_output__(RG_REPLAYGAIN_ADDED)
                track2 = audiotools.open(f.name)
                self.assertIsNotNone(track2.get_replay_gain())

            # try a track with track number metadata
            with temp_file() as f:
                track = audio_class.from_pcm(
                    f.name,
                    test_streams.Sine16_Stereo(44100 * 5,
                                               44100,
                                               8820.0, 0.70,
                                               4410.0, 0.29, 1.0))
                metadata = audiotools.MetaData(track_name=u"Track Name",
                                               track_number=1,
                                               track_total=2)
                track.set_metadata(metadata)
                if track.get_metadata() is None:
                    continue

                self.assertEqual(
                    self.__run_app__(["tracktag",
                                      "-V", "normal",
                                      "--replay-gain", track.filename]), 0)
                self.__check_output__(RG_REPLAYGAIN_ADDED)
                track2 = audiotools.open(f.name)
                self.assertIsNotNone(track2.get_replay_gain())

            # try a track with album number metadata
            with temp_file() as f:
                track = audio_class.from_pcm(
                    f.name,
                    test_streams.Sine16_Stereo(44100 * 5,
                                               44100,
                                               8820.0, 0.70,
                                               4410.0, 0.29, 1.0))
                metadata = audiotools.MetaData(track_name=u"Track Name",
                                               track_number=1,
                                               track_total=2,
                                               album_number=3,
                                               album_total=4)
                track.set_metadata(metadata)

                self.assertEqual(
                    self.__run_app__(["tracktag",
                                      "-V", "normal",
                                      "--replay-gain", track.filename]), 0)
                self.__check_output__(RG_REPLAYGAIN_ADDED_TO_ALBUM.format(3))
                track2 = audiotools.open(f.name)
                self.assertIsNotNone(track2.get_replay_gain())

    @UTIL_TRACKTAG
    def test_unicode(self):
        filenames = [f if PY3 else f.encode("UTF-8") for f in
                     [u"track.flac",
                      u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        unicode_values = [u"text",
                          u'value abc\xe0\xe7\xe8\u3041\u3044\u3046']

        for (input_filename,
             (argument, attribute),
             unicode_value) in Possibilities(
            filenames,
            [("--name", "track_name"),  # check text arguments
             ("--artist", "artist_name"),
             ("--album", "album_name"),
             ("--performer", "performer_name"),
             ("--composer", "composer_name"),
             ("--conductor", "conductor_name"),
             ("--catalog", "catalog"),
             ("--ISRC", "ISRC"),
             ("--publisher", "publisher"),
             ("--media-type", "media"),
             ("--year", "year"),
             ("--date", "date"),
             ("--copyright", "copyright"),
             ("--comment", "comment")],
            unicode_values):

            if os.path.isfile(input_filename):
                os.unlink(input_filename)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(["tracktag",
                                  argument,
                                  unicode_value if PY3 else
                                  unicode_value.encode('utf-8'),
                                  input_filename]), 0)

            set_value = getattr(audiotools.open(input_filename).get_metadata(),
                                attribute)
            if set_value is not None:
                self.assertEqual(set_value, unicode_value)

            if os.path.isfile(input_filename):
                os.unlink(input_filename)

        input_filenames = [f if PY3 else f.encode("UTF-8") for f in
                           [u"track.flac",
                            u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac']]

        comment_filenames = [f if PY3 else f.encode("UTF-8") for f in
                             [u"comment.txt",
                              u'abc\xe0\xe7\xe8\u3041\u3044\u3046.txt']]

        for (input_filename,
             comment_filename) in Possibilities(input_filenames,
                                                comment_filenames):
            if os.path.isfile(input_filename):
                os.unlink(input_filename)
            if os.path.isfile(comment_filename):
                os.unlink(comment_filename)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                BLANK_PCM_Reader(1))

            with open(comment_filename, "wb") as f:
                f.write(b"Test Text")

            self.assertEqual(
                self.__run_app__(["tracktag",
                                  "--comment-file", comment_filename,
                                  input_filename]), 0)

            self.assertEqual(
                audiotools.open(input_filename).get_metadata().comment,
                u"Test Text")

            if os.path.isfile(input_filename):
                os.unlink(input_filename)
            if os.path.isfile(comment_filename):
                os.unlink(comment_filename)


class tracktag_errors(UtilTest):
    @UTIL_TRACKTAG
    def test_bad_options(self):
        from audiotools.text import (ERR_ENCODING_ERROR,
                                     ERR_TRACKTAG_COMMENT_IOERROR,
                                     ERR_TRACKTAG_COMMENT_NOT_UTF8)

        temp_comment = tempfile.NamedTemporaryFile(suffix=".txt")
        temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        temp_track_stat = os.stat(temp_track_file.name)[0]
        try:
            temp_track = audiotools.FlacAudio.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            temp_track.set_metadata(audiotools.MetaData(track_name=u"Foo"))

            self.assertEqual(
                self.__run_app__(["tracktag",
                                  "--comment-file=/dev/null/foo.txt",
                                  temp_track.filename]), 1)
            self.__check_error__(
                ERR_TRACKTAG_COMMENT_IOERROR.format(
                    audiotools.Filename("/dev/null/foo.txt")))

            temp_comment.write(
                os.urandom(1024) + ((u"\uFFFD".encode('utf-8')) * 103))
            temp_comment.flush()

            self.assertEqual(
                self.__run_app__(["tracktag",
                                  "--comment-file={}".format(temp_comment.name),
                                  temp_track.filename]), 1)
            self.__check_error__(
                ERR_TRACKTAG_COMMENT_NOT_UTF8.format(
                    audiotools.Filename(temp_comment.name)))

            os.chmod(temp_track_file.name, temp_track_stat & 0o7555)
            self.assertEqual(
                self.__run_app__(["tracktag", "--name=Bar",
                                 temp_track.filename]), 1)
            self.__check_error__(
                ERR_ENCODING_ERROR.format(
                    audiotools.Filename(temp_track.filename)))
        finally:
            os.chmod(temp_track_file.name, temp_track_stat)
            temp_track_file.close()
            temp_comment.close()

    @UTIL_TRACKTAG
    def test_oversized_metadata(self):
        for audio_class in [audiotools.FlacAudio]:
            tempflac = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            tempwv = tempfile.NamedTemporaryFile(
                suffix="." + audiotools.WavPackAudio.SUFFIX)
            big_text = tempfile.NamedTemporaryFile(suffix=".txt")
            try:
                flac = audio_class.from_pcm(
                    tempflac.name,
                    BLANK_PCM_Reader(5))

                flac.set_metadata(audiotools.MetaData(track_name=u"Foo"))

                big_text.write(b"a" * 16777216)
                big_text.flush()

                orig_md5 = md5()
                audiotools.transfer_framelist_data(flac.to_pcm(),
                                                   orig_md5.update)

                # ensure that setting big text via tracktag
                # doesn't break the file
                subprocess.call(["tracktag", "-V", "quiet",
                                 "--comment-file={}".format(big_text.name),
                                 flac.filename])
                new_md5 = md5()
                audiotools.transfer_framelist_data(flac.to_pcm(),
                                                   new_md5.update)
                self.assertEqual(orig_md5.hexdigest(),
                                 new_md5.hexdigest())

                subprocess.call(["track2track", "-V", "quiet", "-t", "wv",
                                 "-o", tempwv.name,
                                 flac.filename])

                wv = audiotools.open(tempwv.name)

                self.assertTrue(audiotools.pcm_cmp(flac.to_pcm(),
                                                   wv.to_pcm()))

                self.assertEqual(
                    subprocess.call(["tracktag", "-V", "quiet",
                                     "--comment-file={}".format(big_text.name),
                                     wv.filename]), 0)

                self.assertGreater(len(wv.get_metadata().comment), 0)

                subprocess.call(["track2track", "-V", "quiet",
                                 "-t", audio_class.NAME, "-o",
                                 flac.filename, wv.filename])

                self.assertTrue(
                    audiotools.pcm_cmp(
                        audiotools.open(tempflac.name).to_pcm(),
                        wv.to_pcm()))
            finally:
                tempflac.close()
                tempwv.close()
                big_text.close()


class NoMetaData(Exception):
    pass


class tracktag_misc(UtilTest):
    @UTIL_TRACKTAG
    def test_text_options(self):
        INTEGER_FIELDS = [f for f in audiotools.MetaData.FIELDS
                          if audiotools.MetaData.FIELD_TYPES[f] is int]

        def number_fields_values(fields, metadata_class):
            values = set([])
            for field in INTEGER_FIELDS:
                if field in fields:
                    values.add((field, INTEGER_FIELDS.index(field) + 1))
                else:
                    values.add((field, None))

            return values

        def deleted_number_fields_values(fields, metadata_class):
            values = set([])
            for field in INTEGER_FIELDS:
                if field not in fields:
                    values.add((field, INTEGER_FIELDS.index(field) + 1))
                else:
                    values.add((field, None))

            return values

        def metadata_fields_values(metadata):
            values = set([])
            for field in INTEGER_FIELDS:
                values.add((field, getattr(metadata, field)))
            return values

        for audio_type in audiotools.AVAILABLE_TYPES:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_type.SUFFIX)
            try:
                track = audio_type.from_pcm(temp_file.name,
                                            BLANK_PCM_Reader(1))
                for (field_name,
                     add_field,
                     remove_field) in zip(
                    ['track_name',
                     'artist_name',
                     'performer_name',
                     'composer_name',
                     'conductor_name',
                     'album_name',
                     'catalog',
                     'ISRC',
                     'publisher',
                     'media',
                     'year',
                     'date',
                     'copyright',
                     'comment'],
                    ['--name',
                     '--artist',
                     '--performer',
                     '--composer',
                     '--conductor',
                     '--album',
                     '--catalog',
                     '--ISRC',
                     '--publisher',
                     '--media-type',
                     '--year',
                     '--date',
                     '--copyright',
                     '--comment'],
                    ['--remove-name',
                     '--remove-artist',
                     '--remove-performer',
                     '--remove-composer',
                     '--remove-conductor',
                     '--remove-album',
                     '--remove-catalog',
                     '--remove-ISRC',
                     '--remove-publisher',
                     '--remove-media-type',
                     '--remove-year',
                     '--remove-date',
                     '--remove-copyright',
                     '--remove-comment']):
                    self.assertEqual(
                        self.__run_app__(['tracktag', add_field, 'foo',
                                          track.filename]), 0)
                    new_track = audiotools.open(track.filename)
                    metadata = new_track.get_metadata()
                    if metadata is None:
                        break
                    elif getattr(metadata, field_name) is not None:
                        self.assertEqual(getattr(metadata, field_name),
                                         u'foo')

                        self.assertEqual(
                            self.__run_app__(['tracktag', remove_field,
                                              track.filename]), 0)

                        metadata = audiotools.open(
                            track.filename).get_metadata()

                        self.assertTrue(
                            (metadata is None) or
                            (getattr(metadata, field_name) is None),
                            "remove option failed for {} field {}".format(
                                audio_type.NAME, remove_field))

                number_fields = ['track_number',
                                 'track_total',
                                 'album_number',
                                 'album_total']
                try:
                    # make sure the number fields get set properly, if possible
                    for count in range(1, len(number_fields) + 1):
                        for fields in Combinations(number_fields, count):
                            self.assertEqual(
                                self.__run_app__(
                                    ["tracktag", '-r', track.filename] +
                                    self.populate_set_number_fields(fields)),
                                0)
                            metadata = audiotools.open(
                                track.filename).get_metadata()
                            if metadata is None:
                                raise NoMetaData()

                            self.assertTrue(
                                metadata_fields_values(metadata).issubset(
                                    number_fields_values(
                                        fields, metadata.__class__)),
                                "{} not subset of {} for fields {!r}".format(
                                    metadata_fields_values(metadata),
                                    number_fields_values(
                                        fields, metadata.__class__),
                                    fields))

                    # make sure the number fields get removed properly, also
                    number_metadata = audiotools.MetaData(track_number=1,
                                                          track_total=2,
                                                          album_number=3,
                                                          album_total=4)
                    for count in range(1, len(number_fields) + 1):
                        for fields in Combinations(number_fields, count):
                            audiotools.open(track.filename).set_metadata(
                                number_metadata)
                            self.assertEqual(
                                self.__run_app__(
                                    ["tracktag", track.filename] +
                                    self.populate_delete_number_fields(
                                        fields)),
                                0)
                            metadata = audiotools.open(
                                track.filename).get_metadata()
                            if metadata is None:
                                metadata = audiotools.MetaData()
                            self.assertTrue(
                                metadata_fields_values(metadata).issubset(
                                    deleted_number_fields_values(
                                        fields, metadata.__class__)),
                                ("{} not subset of {} for " +
                                 "options {}, fields {}, type {}").format(
                                    metadata_fields_values(metadata),
                                    deleted_number_fields_values(
                                        fields, metadata.__class__),
                                    self.populate_delete_number_fields(
                                        fields),
                                    fields,
                                    audio_type.NAME))
                except NoMetaData:
                    pass

            finally:
                temp_file.close()

    def populate_set_number_fields(self, fields):
        options = []
        for field in fields:
            if field == 'track_number':
                options.append('--number')
                options.append(str(1))
            elif field == 'track_total':
                options.append('--track-total')
                options.append(str(2))
            elif field == 'album_number':
                options.append('--album-number')
                options.append(str(3))
            elif field == 'album_total':
                options.append('--album-total')
                options.append(str(4))
        return options

    def populate_delete_number_fields(self, fields):
        options = []
        for field in fields:
            if field == 'track_number':
                options.append('--remove-number')
            elif field == 'track_total':
                options.append('--remove-track-total')
            elif field == 'album_number':
                options.append('--remove-album-number')
            elif field == 'album_total':
                options.append('--remove-album-total')
        return options


class trackverify(UtilTest):
    @UTIL_TRACKVERIFY
    def test_version(self):
        self.assertEqual(self.__run_app__(["trackverify",
                                           "--version"]), 0)
        if PY3:
            self.__check_output__(audiotools.VERSION_STR)
        else:
            self.__check_info__(audiotools.VERSION_STR.decode("ascii"))
