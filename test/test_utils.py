#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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
import subprocess
import cStringIO
import unicodedata
import tempfile
import os
import os.path
import shutil
import time
import test_streams
from hashlib import md5

from test import (parser, BLANK_PCM_Reader, Combinations, Possibilities,
                  EXACT_BLANK_PCM_Reader, RANDOM_PCM_Reader,
                  TEST_COVER1, TEST_COVER2, TEST_COVER3, TEST_COVER4,
                  HUGE_BMP)


class InvalidTemporaryFile:
    def __init__(self, bad_path):
        self.name = bad_path


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


class UtilTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.line_checks = []

    #takes a list of argument strings
    #returns a returnval integer
    #self.stdout and self.stderr are set to file-like cStringIO objects
    def __run_app__(self, arguments):
        sub = subprocess.Popen(arguments,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

        self.stdout = cStringIO.StringIO(sub.stdout.read())
        self.stderr = cStringIO.StringIO(sub.stderr.read())
        sub.stdout.close()
        sub.stderr.close()
        returnval = sub.wait()
        return returnval

    def __add_check__(self, stream, unicode_string):
        self.line_checks.append((stream, unicode_string))

    def __run_checks__(self):
        for (stream, expected_output) in self.line_checks:
            stream_line = unicodedata.normalize(
                'NFC',
                getattr(self,
                        stream).readline().decode(audiotools.IO_ENCODING))
            expected_line = unicodedata.normalize(
                'NFC',
                expected_output) + unicode(os.linesep)
            self.assertEqual(stream_line, expected_line,
                             "%s != %s" % (
                    repr(stream_line),
                    repr(expected_line)))
        self.line_checks = []

    def __clear_checks__(self):
        self.line_checks = []

    def filename(self, s):
        return s.decode(audiotools.FS_ENCODING, 'replace')

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

    def __check_usage__(self, executable, s):
        self.__add_check__("stderr", u"*** Usage: " + s)
        self.__run_checks__()


class cd2track(UtilTest):
    @UTIL_CD2TRACK
    def setUp(self):
        self.type = audiotools.FlacAudio
        self.quality = "1"

        self.input_dir = tempfile.mkdtemp()

        self.stream = test_streams.Sine16_Stereo(793800, 44100,
                                                 8820.0, 0.70,
                                                 4410.0, 0.29, 1.0)

        self.cue_file = os.path.join(self.input_dir, "CDImage.cue")
        self.bin_file = os.path.join(self.input_dir, "CDImage.bin")

        f = open(self.cue_file, "w")
        f.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        f.close()

        f = open(self.bin_file, "w")
        audiotools.transfer_framelist_data(self.stream, f.write)
        f.close()

        self.output_dir = tempfile.mkdtemp()
        self.format = "%(track_number)2.2d.%(suffix)s"

        self.cwd_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.cwd_dir)

        self.unwritable_dir = tempfile.mkdtemp()
        os.chmod(self.unwritable_dir, 0)

    @UTIL_CD2TRACK
    def tearDown(self):
        os.chdir(self.original_dir)

        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))
        os.rmdir(self.cwd_dir)

        os.chmod(self.unwritable_dir, 0700)
        os.rmdir(self.unwritable_dir)

    def populate_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]
        for option in options:
            if (option == '-t'):
                populated.append(option)
                populated.append(self.type.NAME)
            elif (option == '-q'):
                populated.append(option)
                populated.append(self.quality)
            elif (option == '-d'):
                populated.append(option)
                populated.append(self.output_dir)
            elif (option == '--format'):
                populated.append(option)
                populated.append(self.format)
            elif (option == '--album-number'):
                populated.append(option)
                populated.append(str(8))
            elif (option == '--album-total'):
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

    @UTIL_CD2TRACK
    def test_options(self):
        from audiotools.text import (ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     LAB_CD2TRACK_PROGRESS)

        all_options = ["-t", "-q", "-d", "--format",
                       "--album-number", "--album-total"]
        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                options = self.populate_options(options)

                if ("-t" in options):
                    output_type = self.type
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    ("1" not in output_type.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["cd2track", "-V", "normal",
                                          "-c", self.cue_file] +
                                         options), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                self.assertEqual(
                    self.__run_app__(["cd2track", "-V", "normal",
                                      "-c", self.cue_file] +
                                     options), 0)

                if ("--format" in options):
                    output_format = self.format
                else:
                    output_format = None

                if ("-d" in options):
                    output_dir = self.output_dir
                else:
                    output_dir = "."

                base_metadata = audiotools.MetaData(track_total=3)
                if ("--album-number" in options):
                    base_metadata.album_number = 8
                if ("--album-total" in options):
                    base_metadata.album_total = 9

                output_filenames = []
                for i in xrange(3):
                    base_metadata.track_number = i + 1
                    output_filenames.append(
                        output_type.track_name(
                            "",
                            base_metadata,
                            output_format))

                #check that the output is being generated correctly
                for (i, path) in enumerate(output_filenames):
                    self.__check_info__(
                        audiotools.output_progress(
                            LAB_CD2TRACK_PROGRESS %
                            {"track_number": i + 1,
                             "filename": audiotools.Filename(
                                os.path.join(output_dir, path))},
                            i + 1, len(output_filenames)))

                #rip log is generated afterward as a table
                #FIXME - check table of rip log?

                #make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.assertEqual(len(output_tracks), 3)
                self.stream.reset()
                self.assert_(
                    audiotools.pcm_frame_cmp(
                        audiotools.PCMCat([t.to_pcm() for t in output_tracks]),
                        self.stream) is None)

                #make sure metadata fits our expectations
                for i in xrange(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if (metadata is not None):
                        self.assertEqual(metadata.track_name, None)
                        self.assertEqual(metadata.album_name, None)
                        self.assertEqual(metadata.artist_name, None)

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)

                        if ("--album-number" in options):
                            self.assertEqual(metadata.album_number, 8)
                        else:
                            self.assertEqual(metadata.album_number, None)

                        if ("--album-total" in options):
                            self.assertEqual(metadata.album_total, 9)
                        else:
                            self.assertEqual(metadata.album_total, None)

    @UTIL_CD2TRACK
    def test_unicode(self):
        from shutil import rmtree

        for (output_directory,
             format_string) in Possibilities(
            ["testdir",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046'.encode('utf-8')],
            ["%(track_number)d.%(suffix)s",
             u'%(track_number)d - abc\xe0\xe7\xe8\u3041\u3044\u3046.%(suffix)s'.encode('utf-8')]):
            if (os.path.isdir(output_directory)):
                rmtree(output_directory)

            self.assertEqual(
                self.__run_app__(
                    ["cd2track", "-c", self.cue_file,
                     "--type", "flac",
                     "--format", format_string,
                     "--dir", output_directory]), 0)

            tracks = [audiotools.open(
                    os.path.join(output_directory,
                                 format_string % {"track_number":i,
                                                  "suffix":"flac"}))
                      for i in range(1, 4)]

            self.assertEqual(sum([t.total_frames() for t in tracks]),
                             793800)

            if (os.path.isdir(output_directory)):
                rmtree(output_directory)


    def populate_bad_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]

        for option in sorted(options):
            if (option == '-t'):
                populated.append(option)
                populated.append("foo")
            elif (option == '-q'):
                populated.append(option)
                populated.append("bar")
            elif (option == '-d'):
                populated.append(option)
                populated.append(self.unwritable_dir)
            elif (option == '--format'):
                populated.append(option)
                populated.append("%(foo)s.%(suffix)s")
            elif (option == '--album-number'):
                populated.append(option)
                populated.append("foo")
            elif (option == '--album-total'):
                populated.append(option)
                populated.append("bar")
            else:
                populated.append(option)

        return populated

    @UTIL_CD2TRACK
    def test_errors(self):
        from audiotools.text import (ERR_DUPLICATE_OUTPUT_FILE,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_UNKNOWN_FIELD,
                                     LAB_SUPPORTED_FIELDS,
                                     ERR_ENCODING_ERROR,
                                     )

        self.assertEqual(
            self.__run_app__(["cd2track", "-c", self.cue_file,
                              "--format=foo"]), 1)
        self.__check_error__(ERR_DUPLICATE_OUTPUT_FILE %
                             (audiotools.Filename("foo"),))

        all_options = ["-t", "-q", "-d", "--format",
                       "--album-number", "--album-total"]
        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):

                options = self.populate_bad_options(options)

                if ("-t" in options):
                    self.assertEqual(
                        self.__run_app__(["cd2track", "-c", self.cue_file] +
                                         options),
                        2)
                    continue
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("--album-number" in options) or
                    ("--album-total" in options)):
                    self.assertEqual(
                        self.__run_app__(["cd2track", "-c", self.cue_file] +
                                         options),
                        2)
                    continue

                self.assertEqual(
                    self.__run_app__(["cd2track", "-c", self.cue_file] +
                                     options),
                    1)

                if ("-q" in options):
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": "bar",
                         "type": audiotools.DEFAULT_TYPE})
                    continue

                if ("--format" in options):
                    self.__check_error__(
                        ERR_UNKNOWN_FIELD % ("foo"))
                    self.__check_info__(LAB_SUPPORTED_FIELDS)
                    for field in sorted(audiotools.MetaData.FIELDS + \
                                            ("album_track_number", "suffix")):
                        if (field == 'track_number'):
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    self.__check_info__(u"%(basename)s")
                    continue

                if ("-d" in options):
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_type.track_name(
                            "",
                            audiotools.MetaData(track_number=1,
                                                track_total=3)))
                    self.__check_error__(
                        ERR_ENCODING_ERROR %
                        (audiotools.Filename(output_path),))
                    continue


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
        for i in xrange(10):
            import Image
            img = Image.new("RGB", (100, 100), "#%2.2X%2.2X%2.2X" % (i, i, i))
            data = cStringIO.StringIO()
            img.save(data, "PNG")
            img = audiotools.Image.new(data.getvalue(), u"", i / 2)
            self.images1.append(img)
            metadata.add_image(img)

        self.track1.set_metadata(metadata)

        metadata = audiotools.MetaData(track_name=u"Track")
        self.images2 = []
        for i in xrange(5):
            import Image
            img = Image.new("RGB", (100, 100), "#%2.2X%2.2X%2.2X" %
                            (100 + i, 100 + i, 100 + i))
            data = cStringIO.StringIO()
            img.save(data, "PNG")
            img = audiotools.Image.new(data.getvalue(), u"", i)
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

    def clean_output_dir(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

    def populate_options(self, options):
        populated = []
        for option in options:
            if (option == "-d"):
                populated.append(option)
                populated.append(self.output_dir)
            elif (option == "-p"):
                populated.append(option)
                populated.append(self.prefix)
            else:
                populated.append(option)

        return populated

    @UTIL_COVERDUMP
    def test_options(self):
        from audiotools.text import (LAB_ENCODE,
                                     )

        all_options = ["-d", "-p"]
        for count in xrange(len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options)
                self.clean_output_dir()
                self.assertEqual(
                    self.__run_app__(["coverdump", "-V", "normal",
                                      self.track1.filename] + options),
                    0)

                if ("-d" in options):
                    output_directory = self.output_dir
                else:
                    output_directory = "."

                template = "%(prefix)s%(filename)s%(filenum)2.2d.%(suffix)s"

                for (i, image) in enumerate(self.images1):
                    if ("-p" in options):
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

                    if ("-d" in options):
                        output_path = os.path.join(self.output_dir,
                                                   output_filename)
                    else:
                        output_path = os.path.join(".", output_filename)

                    self.__check_info__(
                        LAB_ENCODE %
                        {"source": audiotools.Filename(self.track1.filename),
                         "destination": audiotools.Filename(output_path)})
                    output_image = audiotools.Image.new(
                        open(output_path, "rb").read(),
                        u"",
                        i / 2)
                    self.assertEqual(output_image, image)

                self.clean_output_dir()
                self.assertEqual(
                    self.__run_app__(["coverdump", "-V", "normal",
                                      self.track2.filename] + options),
                    0)

                if ("-d" in options):
                    output_directory = self.output_dir
                else:
                    output_directory = "."

                template = "%(prefix)s%(filename)s.%(suffix)s"

                for (i, image) in enumerate(self.images2):
                    if ("-p" in options):
                        output_filename = template % {
                            "prefix": "PREFIX_",
                            "filename": self.filename_types[image.type],
                            "suffix": "png"}
                    else:
                        output_filename = template % {
                            "prefix": "",
                            "filename": self.filename_types[image.type],
                            "suffix": "png"}

                    if ("-d" in options):
                        output_path = os.path.join(self.output_dir,
                                                   output_filename)
                    else:
                        output_path = os.path.join(".", output_filename)

                    self.__check_info__(
                        LAB_ENCODE %
                        {"source": audiotools.Filename(self.track2.filename),
                         "destination": audiotools.Filename(output_path)})
                    output_image = audiotools.Image.new(
                        open(output_path, "rb").read(),
                        u"",
                        i)
                    self.assertEqual(output_image, image)

    @UTIL_COVERDUMP
    def test_unicode(self):
        from shutil import rmtree

        for (output_directory,
             file_path,
             prefix) in Possibilities(
            ["testdir",    #check --dir
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046'.encode('utf-8')],
            ["test.flac",  #check filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            [None,         #check --prefix
             "prefix_",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046_'.encode('utf-8')]):
            if (os.path.isdir(output_directory)):
                rmtree(output_directory)
            if (os.path.isfile(file_path)):
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

            if (os.path.isdir(output_directory)):
                rmtree(output_directory)
            if (os.path.isfile(file_path)):
                os.unlink(file_path)

    @UTIL_COVERDUMP
    def test_errors(self):
        from audiotools.text import (ERR_1_FILE_REQUIRED,
                                     ERR_ENCODING_ERROR,
                                     ERR_OUTPUT_IS_INPUT)

        #check no input files
        self.assertEqual(self.__run_app__(
                ["coverdump", "-V", "normal"]), 1)

        self.__check_error__(ERR_1_FILE_REQUIRED)

        #check multiple input files
        self.assertEqual(self.__run_app__(
                ["coverdump", "-V", "normal",
                 self.track1.filename, self.track2.filename]), 1)

        self.__check_error__(ERR_1_FILE_REQUIRED)

        #check unwritable output dir
        old_mode = os.stat(self.output_dir).st_mode
        try:
            os.chmod(self.output_dir, 0)
            self.assertEqual(self.__run_app__(
                    ["coverdump", "-V", "normal", "-d", self.output_dir,
                     self.track1.filename]), 1)
            self.__check_error__(
                ERR_ENCODING_ERROR %
                (audiotools.Filename(os.path.join(self.output_dir,
                                                  "front_cover01.png")),))
        finally:
            os.chmod(self.output_dir, old_mode)

        #check unwritable cwd
        old_mode = os.stat(self.cwd_dir).st_mode
        try:
            os.chmod(self.cwd_dir, 0)
            self.assertEqual(self.__run_app__(
                    ["coverdump", "-V", "normal",
                     self.track1.filename]), 1)
            self.__check_error__(
                ERR_ENCODING_ERROR %
                (audiotools.Filename("front_cover01.png"),))

        finally:
            os.chmod(self.cwd_dir, old_mode)

        #check input file same as output file
        track = audiotools.FlacAudio.from_pcm(
            os.path.join(self.output_dir, "front_cover.jpg"),
            BLANK_PCM_Reader(1))
        metadata = track.get_metadata()
        metadata.add_image(audiotools.Image.new(TEST_COVER1, u"", 0))
        track.update_metadata(metadata)

        self.assertEqual(self.__run_app__(
                ["coverdump", "-V", "normal",
                 "-d", self.output_dir, track.filename]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT %
            (audiotools.Filename(track.filename),))


class dvdainfo(UtilTest):
    @UTIL_DVDAINFO
    def setUp(self):
        self.invalid_dir1 = tempfile.mkdtemp()
        self.invalid_dir2 = tempfile.mkdtemp()
        f = open(os.path.join(self.invalid_dir2, "AUDIO_TS.IFO"), "wb")
        f.write(os.urandom(1000))
        f.close()

    @UTIL_DVDAINFO
    def tearDown(self):
        os.rmdir(self.invalid_dir1)
        os.unlink(os.path.join(self.invalid_dir2, "AUDIO_TS.IFO"))
        os.rmdir(self.invalid_dir2)

    @UTIL_DVDAINFO
    def test_errors(self):
        from audiotools.text import (ERR_NO_AUDIO_TS,
                                     ERR_DVDA_IOERROR_AUDIO_TS,
                                     ERR_DVDA_INVALID_AUDIO_TS)

        #test with no -A option
        self.assertEqual(self.__run_app__(["dvdainfo"]), 1)
        self.__check_error__(ERR_NO_AUDIO_TS)

        #test with an invalid AUDIO_TS dir
        self.assertEqual(self.__run_app__(["dvdainfo",
                                           "-A", self.invalid_dir1]), 1)
        self.__check_error__(ERR_DVDA_IOERROR_AUDIO_TS)

        #test with an invalid AUDIO_TS/AUDIO_TS.IFO file
        self.assertEqual(self.__run_app__(["dvdainfo",
                                           "-A", self.invalid_dir2]), 1)
        self.__check_error__(ERR_DVDA_INVALID_AUDIO_TS)


class dvda2track(UtilTest):
    @UTIL_DVDA2TRACK
    def setUp(self):
        self.invalid_dir1 = tempfile.mkdtemp()
        self.invalid_dir2 = tempfile.mkdtemp()
        f = open(os.path.join(self.invalid_dir2, "AUDIO_TS.IFO"), "wb")
        f.write(os.urandom(1000))
        f.close()

    @UTIL_DVDA2TRACK
    def tearDown(self):
        os.rmdir(self.invalid_dir1)
        os.unlink(os.path.join(self.invalid_dir2, "AUDIO_TS.IFO"))
        os.rmdir(self.invalid_dir2)

    @UTIL_DVDA2TRACK
    def test_errors(self):
        from audiotools.text import (ERR_NO_AUDIO_TS,
                                     ERR_DVDA_IOERROR_AUDIO_TS,
                                     ERR_DVDA_INVALID_AUDIO_TS)

        #test with no -A option
        self.assertEqual(self.__run_app__(["dvda2track"]), 1)
        self.__check_error__(ERR_NO_AUDIO_TS)

        #test with an invalid AUDIO_TS dir
        self.assertEqual(self.__run_app__(["dvda2track",
                                           "-A", self.invalid_dir1]), 1)
        self.__check_error__(ERR_DVDA_IOERROR_AUDIO_TS)

        #test with an invalid AUDIO_TS/AUDIO_TS.IFO file
        self.assertEqual(self.__run_app__(["dvda2track",
                                           "-A", self.invalid_dir2]), 1)
        self.__check_error__(ERR_DVDA_INVALID_AUDIO_TS)

        #FIXME
        #It's difficult to test an invalid --title or invalid --xmcd
        #without a valid AUDIO_TS.IFO file,
        #and a set of present IFO files and AOB files.
        #I'll need a way to generate synthetic ones.


class track2track(UtilTest):
    @UTIL_TRACK2TRACK
    def setUp(self):
        #input format should be something other than the user's default
        #and should support embedded metadata
        for self.input_format in [audiotools.ALACAudio,
                                  audiotools.AiffAudio]:
            if (self.input_format is not audiotools.DEFAULT_TYPE):
                break

        #output format shouldn't be the user's default, the input format
        #and should support embedded images and ReplayGain tags
        for self.output_format in [audiotools.FlacAudio,
                                   audiotools.WavPackAudio]:
            if (self.input_format is not audiotools.DEFAULT_TYPE):
                break

        self.input_dir = tempfile.mkdtemp()
        self.track1 = self.input_format.from_pcm(
            os.path.join(self.input_dir, "01.%s" % (self.input_format.SUFFIX)),
            BLANK_PCM_Reader(1))
        self.track_metadata = audiotools.MetaData(track_name=u"Track 1",
                                                  track_number=1,
                                                  album_name=u"Album",
                                                  artist_name=u"Artist")
        self.cover = audiotools.Image.new(TEST_COVER1, u"", 0)
        self.track_metadata.add_image(self.cover)
        # audiotools.Image.new(open("bigpng.png", "rb").read(), u"", 0))

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
        self.unwritable_file = "/dev/null/foo.%s" % (self.output_format.SUFFIX)
        f = open(os.path.join(self.input_dir,
                              "broken.%s" % (self.input_format.SUFFIX)), "wb")
        f.write(open(self.track1.filename, "rb").read()[0:-10])
        f.close()
        self.broken_track1 = audiotools.open(
            os.path.join(self.input_dir,
                         "broken.%s" % (self.input_format.SUFFIX)))

        #Why a static set of input/output arguments for each set of options?
        #Since track2track uses the standard interface for everything,
        #we're only testing that the options work.
        #The interface itself is tested at a lower level
        #in the test_core.py or test_formats.py modules.

    @UTIL_TRACK2TRACK
    def tearDown(self):
        os.chdir(self.original_dir)

        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))
        os.rmdir(self.cwd_dir)

        self.output_file.close()

        os.chmod(self.unwritable_dir, 0700)
        os.rmdir(self.unwritable_dir)

    def clean_output_dirs(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))

        f = open(self.output_file.name, "wb")
        f.close()

    def populate_options(self, options):
        populated = []

        for option in sorted(options):
            if (option == '-t'):
                populated.append(option)
                populated.append(self.type)
            elif (option == '-q'):
                populated.append(option)
                populated.append(self.quality)
            elif (option == '-d'):
                populated.append(option)
                populated.append(self.output_dir)
            elif (option == '--format'):
                populated.append(option)
                populated.append(self.format)
            elif (option == '-o'):
                populated.append(option)
                populated.append(self.output_file.name)
            else:
                populated.append(option)

        return populated

    def populate_bad_options(self, options):
        populated = []

        for option in sorted(options):
            if (option == '-t'):
                populated.append(option)
                populated.append("foo")
            elif (option == '-q'):
                populated.append(option)
                populated.append("bar")
            elif (option == '-d'):
                populated.append(option)
                populated.append(self.unwritable_dir)
            elif (option == '--format'):
                populated.append(option)
                populated.append("%(foo)s.%(suffix)s")
            elif (option == '-o'):
                populated.append(option)
                populated.append(self.unwritable_file)
            elif (option == '-x'):
                populated.append(option)
                populated.append(os.devnull)
            elif (option == '-j'):
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

        messenger = audiotools.Messenger("track2track", None)

        all_options = ["-t", "-q", "-d", "--format", "-o",
                       "--replay-gain", "--no-replay-gain"]

        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                self.__clear_checks__()

                options = self.populate_options(options) + \
                    ["-V", "normal", "-j", "1", self.track1.filename]

                if (("-d" in options) and ("-o" in options)):
                    #-d and -o trigger an error

                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 1)
                    self.__check_error__(ERR_TRACK2TRACK_O_AND_D)
                    self.__check_info__(ERR_TRACK2TRACK_O_AND_D_SUGGESTION)
                    continue

                if (("--format" in options) and ("-o" in options)):
                    self.__queue_warning__(ERR_TRACK2TRACK_O_AND_FORMAT)

                if ('-t' in options):
                    output_class = audiotools.TYPE_MAP[
                        options[options.index('-t') + 1]]
                elif ("-o" in options):
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
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": options[options.index("-q") + 1],
                         "type": output_class.NAME})
                    continue

                if ('--format' in options):
                    output_format = options[options.index('--format') + 1]
                else:
                    output_format = None

                metadata = self.track1.get_metadata()

                if ("-o" in options):
                    output_path = self.output_file.name
                elif ("-d" in options):
                    output_path = os.path.join(
                        self.output_dir,
                        output_class.track_name("", metadata, output_format))
                else:
                    output_path = os.path.join(
                        ".",
                        output_class.track_name("", metadata, output_format))

                self.assertEqual(
                    self.__run_app__(["track2track"] + options), 0)
                self.assert_(os.path.isfile(output_path))

                if ("-o" not in options):
                    self.__check_info__(
                        LAB_ENCODE %
                        {"source":
                             audiotools.Filename(self.track1.filename),
                         "destination":
                             audiotools.Filename(output_path)})

                track2 = audiotools.open(output_path)
                self.assertEqual(track2.NAME, output_class.NAME)
                if (self.track1.lossless() and
                    track2.lossless() and not
                    (output_class.supports_replay_gain() and
                     "--replay-gain" in options)):
                    self.assert_(
                        audiotools.pcm_frame_cmp(self.track1.to_pcm(),
                                                 track2.to_pcm()) is None)
                if (track2.get_metadata() is not None):
                    self.assertEqual(track2.get_metadata(), metadata)

                    image = track2.get_metadata().images()[0]
                    self.assertEqual(image.width, self.cover.width)
                    self.assertEqual(image.height, self.cover.height)

                if (output_class.supports_replay_gain()):
                    if (output_class.lossless_replay_gain()):
                        if (("-o" not in options) and
                            audiotools.ADD_REPLAYGAIN and
                            ("--no-replay-gain" not in options)):
                            self.__check_info__(RG_REPLAYGAIN_ADDED)
                            self.assert_(track2.replay_gain() is not None)
                    else:
                        if ("--replay-gain" in options):
                            self.__check_info__(RG_REPLAYGAIN_APPLIED)

    @UTIL_TRACK2TRACK
    def test_unicode(self):
        from shutil import rmtree

        for (output_directory,
             format_string,
             file_path) in Possibilities(
            ["testdir",        #check --dir
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046'.encode('utf-8')],
            ["new_file.flac",  #check --format]
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac'.encode('utf-8')],
            ["file.flac",      #check filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')]):
            if (os.path.isdir(output_directory)):
                rmtree(output_directory)
            if (os.path.isfile(file_path)):
                os.unlink(file_path)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(
                    ["track2track",
                     "--dir", output_directory,
                     "--format", format_string,
                     file_path]), 0)

            self.assertEqual(
                audiotools.pcm_frame_cmp(
                    track.to_pcm(),
                    audiotools.open(os.path.join(output_directory,
                                                 format_string)).to_pcm()),
                None)

            if (os.path.isdir(output_directory)):
                rmtree(output_directory)
            if (os.path.isfile(file_path)):
                os.unlink(file_path)

        for (file_path,
             output_path) in Possibilities(
            ["file.flac",        #check filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            ["output_file.flac", #check --output argument
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac'.encode('utf-8')]):
            if (os.path.isfile(output_path)):
                os.unlink(output_path)
            if (os.path.isfile(file_path)):
                os.unlink(file_path)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(
                    ["track2track", "-o", output_path, file_path]), 0)

            self.assertEqual(
                audiotools.pcm_frame_cmp(
                    track.to_pcm(),
                    audiotools.open(output_path).to_pcm()),
                None)

            if (os.path.isfile(output_path)):
                os.unlink(output_path)
            if (os.path.isfile(file_path)):
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
                                     )

        all_options = ["-t", "-q", "-d", "--format", "-o", "-j",
                       "--replay-gain", "--no-replay-gain"]
        for count in xrange(0, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                self.__clear_checks__()

                options = self.populate_bad_options(options) + \
                    [self.broken_track1.filename]

                if ("-t" in options):
                    self.assertEqual(
                        self.__run_app__(["track2track"] + options),
                        2)
                    continue
                elif ("-o" in options):
                    output_class = self.output_format
                else:
                    output_class = audiotools.TYPE_MAP[
                        audiotools.DEFAULT_TYPE]

                self.assertEqual(
                    self.__run_app__(["track2track"] + options),
                    1)

                if (("-o" in options) and
                    ("-d" in options)):
                    self.__check_error__(ERR_TRACK2TRACK_O_AND_D)
                    self.__check_info__(ERR_TRACK2TRACK_O_AND_D_SUGGESTION)
                    continue

                if (("--format" in options) and ("-o" in options)):
                    self.__queue_warning__(ERR_TRACK2TRACK_O_AND_FORMAT)

                if ("-q" in options):
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": "bar",
                         "type": output_class.NAME})
                    continue

                if ("-j" in options):
                    self.__check_error__(
                        ERR_INVALID_JOINT)
                    continue

                if ("-o" in options):
                    self.__check_error__(
                        u"[Errno 20] Not a directory: '%s'" %
                        (self.unwritable_file))
                    continue

                if ("--format" in options):
                    self.__check_error__(
                        ERR_UNKNOWN_FIELD % ("foo"))
                    self.__check_info__(LAB_SUPPORTED_FIELDS)
                    for field in sorted(audiotools.MetaData.FIELDS + \
                                            ("album_track_number", "suffix")):
                        if (field == 'track_number'):
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    self.__check_info__(u"%(basename)s")
                    continue

                if ("-d" in options):
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_class.track_name(
                            "",
                            self.track1.get_metadata(),
                            None))
                    self.__check_error__(
                        u"[Errno 13] Permission denied: '%s'" %
                        (output_path))
                    continue

                #the error triggered by a broken file is variable
                #so no need to check its exact value
                self.assert_(len(self.stderr.getvalue()) > 0)

        #check no input files
        self.assertEqual(self.__run_app__(["track2track"]), 1)
        self.__check_error__(ERR_FILES_REQUIRED)

        self.track2 = self.input_format.from_pcm(
            os.path.join(self.input_dir, "02.%s" % (self.input_format.SUFFIX)),
            BLANK_PCM_Reader(2))

        #check multiple input files and -o
        self.assertEqual(self.__run_app__(["track2track",
                                           "-o", self.output_file.name,
                                           self.track1.filename,
                                           self.track2.filename]), 1)
        self.__check_error__(ERR_TRACK2TRACK_O_AND_MULTIPLE)

        #check duplicate input file
        self.assertEqual(self.__run_app__(["track2track",
                                           self.track1.filename,
                                           self.track1.filename,
                                           self.track2.filename]), 1)
        self.__check_error__(
            ERR_DUPLICATE_FILE %
            (audiotools.Filename(self.track1.filename),))

        #check identical input and output file
        self.assertEqual(
            self.__run_app__(["track2track",
                              self.track1.filename,
                              "-t", self.input_format.NAME,
                              "-d", self.input_dir,
                              "--format=%(track_number)2.2d.%(suffix)s"]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT %
            (audiotools.Filename(self.track1.filename),))

        #check identical input and output file with -o
        self.assertEqual(self.__run_app__(["track2track",
                                           "-t", self.input_format.NAME,
                                           "-o", self.track1.filename,
                                           self.track1.filename]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT %
            (audiotools.Filename(self.track1.filename),))

        #check duplicate output files
        self.assertEqual(self.__run_app__(["track2track",
                                           "--format", "foo",
                                           self.track1.filename,
                                           self.track2.filename]), 1)
        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE % (
                audiotools.Filename(os.path.join(".", "foo")),))

        #check conversion from supported to unsupported channel count
        unsupported_count_file = tempfile.NamedTemporaryFile(
            suffix=".flac")
        try:
            supported_track = audiotools.WaveAudio.from_pcm(
                os.path.join(self.input_dir, "00 - channels.wav"),
                BLANK_PCM_Reader(1, channels=10, channel_mask=0))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "flac",
                                               "-d",
                                               self.output_dir,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_COUNT %
                {"target_filename": audiotools.Filename(
                        os.path.join(self.output_dir, "00 - .flac")),
                 "channels": 10})

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_count_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_COUNT %
                {"target_filename": audiotools.Filename(
                        unsupported_count_file.name),
                 "channels": 10})
        finally:
            unsupported_count_file.close()

        #check conversion from supported to unsupported channel mask
        unsupported_mask_file = tempfile.NamedTemporaryFile(
            suffix=".flac")
        try:
            supported_track = audiotools.WaveAudio.from_pcm(
                os.path.join(self.input_dir, "00 - mask.wav"),
                BLANK_PCM_Reader(1, channels=6, channel_mask=0x3F000))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "flac",
                                               "-d",
                                               self.output_dir,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_MASK %
                {"target_filename": audiotools.Filename(
                        os.path.join(self.output_dir, "00 - .flac")),
                 "assignment": audiotools.ChannelMask(0x3F000)})

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_mask_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_CHANNEL_MASK %
                {"target_filename": audiotools.Filename(
                        unsupported_mask_file.name),
                 "assignment": audiotools.ChannelMask(0x3F000)})
        finally:
            unsupported_mask_file.close()

        #check conversion from supported to unsupported bits-per-sample
        unsupported_bps_file = tempfile.NamedTemporaryFile(
            suffix=".shn")
        try:
            supported_track = audiotools.WaveAudio.from_pcm(
                os.path.join(self.input_dir, "00 - bps.wav"),
                BLANK_PCM_Reader(1, bits_per_sample=24))

            self.assertEqual(self.__run_app__(["track2track",
                                               "-t", "shn",
                                               "-d",
                                               self.output_dir,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_BITS_PER_SAMPLE %
                {"target_filename": audiotools.Filename(
                        os.path.join(self.output_dir, "00 - .shn")),
                 "bps": 24})

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_bps_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                ERR_UNSUPPORTED_BITS_PER_SAMPLE %
                {"target_filename": audiotools.Filename(
                        unsupported_bps_file.name),
                 "bps": 24})
        finally:
            unsupported_bps_file.close()

    @UTIL_TRACK2TRACK
    def test_replay_gain(self):
        temp_files = [os.path.join(
                self.input_dir,
                "%2.2d.%s" % (i + 1, self.input_format.SUFFIX))
                      for i in xrange(7)]
        temp_tracks = []

        temp_tracks.append(self.input_format.from_pcm(
                temp_files[0],
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50, 4410.0, 0.49, 1.0)))

        temp_tracks.append(self.input_format.from_pcm(
                temp_files[1],
                test_streams.Sine16_Stereo(66150, 44100,
                                           8820.0, 0.70, 4410.0, 0.29, 1.0)))
        temp_tracks.append(self.input_format.from_pcm(
                temp_files[2],
                test_streams.Sine16_Stereo(52920, 44100,
                                           441.0, 0.50, 441.0, 0.49, 0.5)))
        temp_tracks.append(self.input_format.from_pcm(
                temp_files[3],
                test_streams.Sine16_Stereo(61740, 44100,
                                           441.0, 0.61, 661.5, 0.37, 2.0)))
        temp_tracks.append(self.input_format.from_pcm(
                temp_files[4],
                test_streams.Sine16_Stereo(26460, 44100,
                                           441.0, 0.50, 882.0, 0.49, 0.7)))
        temp_tracks.append(self.input_format.from_pcm(
                temp_files[5],
                test_streams.Sine16_Stereo(61740, 44100,
                                           441.0, 0.50, 4410.0, 0.49, 1.3)))
        temp_tracks.append(self.input_format.from_pcm(
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
            self.__run_app__(["track2track",
                              "-d", self.output_dir,
                              "--format=%(track_name)s.%(suffix)s",
                              "-t", self.output_format.NAME,
                              "--replay-gain",
                              "-V", "quiet"] + \
                                 [f.filename for f in temp_tracks]), 0)

        converted_tracks = audiotools.open_files(
            [os.path.join(self.output_dir, f) for f in
             os.listdir(self.output_dir)], sorted=True)

        self.assertEqual(len(converted_tracks), 7)

        for (i, track) in enumerate(converted_tracks):
            self.assertEqual(track.get_metadata().track_name,
                             u"Track %d" % (i + 1))
            self.assert_(track.replay_gain() is not None)

        replay_gains = [track.replay_gain() for track in
                        converted_tracks]

        #tracks 0 and 1 should be on the same album
        self.assertEqual(replay_gains[0],
                         replay_gains[0])
        self.assertEqual(replay_gains[0].album_gain,
                         replay_gains[1].album_gain)

        self.assertNotEqual(replay_gains[0].album_gain,
                            replay_gains[2].album_gain)
        self.assertNotEqual(replay_gains[0].album_gain,
                            replay_gains[4].album_gain)

        #tracks 2 and 3 should be on the same album
        self.assertEqual(replay_gains[2].album_gain,
                         replay_gains[3].album_gain)

        self.assertNotEqual(replay_gains[3].album_gain,
                            replay_gains[0].album_gain)
        self.assertNotEqual(replay_gains[3].album_gain,
                            replay_gains[5].album_gain)

        #tracks 4, 5 and 6 should be on the same album
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
        self.cuesheet.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        self.cuesheet.flush()

        self.invalid_cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.invalid_cuesheet.write("Hello, World!")
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

    def populate_options(self, options, type, quality, outfile):
        populated = []

        for option in options:
            if (option == '-t'):
                populated.append(option)
                populated.append(type)
            elif (option == '-q'):
                populated.append(option)
                populated.append(quality)
            elif (option == '--cue'):
                populated.append(option)
                populated.append(self.cuesheet.name)
            elif (option == '-o'):
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
                for count in xrange(1, len(all_options) + 1):
                    for options in Combinations(all_options, count):
                        yield (type, quality, outfile, count, options)

    @UTIL_TRACKCAT
    def test_options(self):
        from audiotools.text import (ERR_FILES_REQUIRED,
                                     ERR_BPS_MISMATCH,
                                     ERR_CHANNEL_COUNT_MISMATCH,
                                     ERR_SAMPLE_RATE_MISMATCH,
                                     ERR_CUE_IOERROR,
                                     ERR_CUE_MISSING_TAG,
                                     ERR_DUPLICATE_FILE,
                                     ERR_OUTPUT_IS_INPUT,
                                     ERR_NO_OUTPUT_FILE,
                                     ERR_UNSUPPORTED_AUDIO_TYPE,
                                     ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_ENCODING_ERROR)

        #first, check the error conditions
        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac"]), 1)
        self.__check_error__(ERR_FILES_REQUIRED)

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
        self.__check_error__(ERR_CUE_MISSING_TAG % (1))

        self.assertEqual(
            self.__run_app__(["trackcat",
                              "-o", self.suffix_outfile.name,
                              self.track1.filename,
                              self.track1.filename]), 0)
        self.__check_warning__(
            ERR_DUPLICATE_FILE %
            (audiotools.Filename(self.track1.filename),))

        self.assertEqual(
            self.__run_app__(["trackcat",
                              "-o", self.track1.filename,
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename]), 1)
        self.__check_error__(
            ERR_OUTPUT_IS_INPUT %
            (audiotools.Filename(self.track1.filename),))

        #then, check the option combinations
        #along with a few different output files and types
        all_options = ["-t", "-q", "--cue", "-o"]
        for (type,
             quality,
             outfile,
             count,
             options) in self.output_combinations(all_options):
            if (os.path.isfile(outfile)):
                f = open(outfile, "wb")
                f.close()

            options = self.populate_options(options,
                                            type,
                                            quality,
                                            outfile) + \
                                            [self.track1.filename,
                                             self.track2.filename,
                                             self.track3.filename]

            #check a few common errors
            if ("-o" not in options):
                self.assertEqual(self.__run_app__(["trackcat"] + options),
                                 1)

                self.__check_error__(ERR_NO_OUTPUT_FILE)
                continue

            if ("-t" in options):
                output_format = audiotools.TYPE_MAP[type]
            else:
                try:
                    output_format = audiotools.filename_to_type(outfile)
                except audiotools.UnknownAudioType:
                    self.assertEqual(self.__run_app__(["trackcat"] +
                                                      options), 1)

                    self.__check_error__(
                        ERR_UNSUPPORTED_AUDIO_TYPE % (u"",))
                    continue

            if (("-q" in options) and
                (quality not in output_format.COMPRESSION_MODES)):
                self.assertEqual(self.__run_app__(["trackcat"] + options),
                                 1)
                self.__check_error__(
                    ERR_UNSUPPORTED_COMPRESSION_MODE %
                    {"quality": quality,
                     "type": output_format.NAME.decode('ascii')})
                continue

            if (outfile.startswith("/dev/")):
                self.assertEqual(self.__run_app__(["trackcat"] + options),
                                 1)
                self.__check_error__(
                    ERR_ENCODING_ERROR % (audiotools.Filename(outfile),))
                continue

            #check that no PCM data is lost
            self.assertEqual(
                self.__run_app__(["trackcat"] + options), 0)
            new_track = audiotools.open(outfile)
            self.assertEqual(new_track.NAME, output_format.NAME)
            self.assertEqual(new_track.total_frames(), 793800)
            self.assert_(audiotools.pcm_frame_cmp(
                    new_track.to_pcm(),
                    audiotools.PCMCat([track.to_pcm() for track in
                                       [self.track1,
                                        self.track2,
                                        self.track3]])) is None)

            #check that metadata is merged properly
            metadata = new_track.get_metadata()
            if (metadata is not None):
                self.assertEqual(metadata.track_name, None)
                self.assertEqual(metadata.album_name, u"Album")
                self.assertEqual(metadata.artist_name, u"Artist")
                self.assertEqual(metadata.track_number, None)
                self.assertEqual(metadata.track_total, 3)

            #check that the cuesheet is embedded properly
            if (("--cue" in options) and
                (output_format is audiotools.FlacAudio)):
                cuesheet = new_track.get_cuesheet()
                self.assert_(cuesheet is not None)
                self.assertEqual([t.ISRC() for t in cuesheet.tracks()],
                                 ['JPPI00652340',
                                  'JPPI00652349',
                                  'JPPI00652341'])
                self.assertEqual([[int(i.offset() * 75) for i in t.indexes()]
                                  for t in cuesheet.tracks()],
                                 [[0,], [225, 375], [675, 825]])
                self.assertEqual(list(cuesheet.pcm_lengths(793800, 44100)),
                                 [220500, 264600, 308700])

    @UTIL_TRACKCAT
    def test_unicode(self):
        for (input_filenames,
             output_path,
             cuesheet_file) in Possibilities(
            #check filename arguments
            [["track%d.flac" % (i) for i in range(3)],
             [(u'abc\xe0\xe7\xe8\u3041\u3044\u3046-%d.flac' %
               (i)).encode('utf-8') for i in range(3)]],
            #check output filename argument
            ["output.flac",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-out.flac'.encode('utf-8')],
            #check --cue argument
            [None,
             "cuesheet.cue",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.cue'.encode('utf-8')]):

            for input_filename in input_filenames:
                if (os.path.isfile(input_filename)):
                    os.unlink(input_filename)
            if (os.path.isfile(output_path)):
                os.unlink(output_path)
            if ((cuesheet_file is not None) and
                os.path.isfile(cuesheet_file)):
                os.unlink(cuesheet_file)

            tracks = [audiotools.FlacAudio.from_pcm(
                    input_filename,
                    EXACT_BLANK_PCM_Reader(pcm_frames))
                      for (input_filename, pcm_frames) in
                      zip(input_filenames, [220500, 264600, 308700])]

            if (cuesheet_file is not None):
                f = open(cuesheet_file, "wb")
                f.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
                f.close()

            self.assertEqual(
                self.__run_app__(
                    ["trackcat"] + input_filenames +
                    ([cuesheet_file] if cuesheet_file is not None else []) +
                    ["--output", output_path]), 0)

            self.assertEqual(
                audiotools.pcm_frame_cmp(
                    audiotools.PCMCat([t.to_pcm() for t in tracks]),
                    audiotools.open(output_path).to_pcm()), None)

            for input_filename in input_filenames:
                if (os.path.isfile(input_filename)):
                    os.unlink(input_filename)
            if (os.path.isfile(output_path)):
                os.unlink(output_path)
            if ((cuesheet_file is not None) and
                os.path.isfile(cuesheet_file)):
                os.unlink(cuesheet_file)


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
        self.broken_file.write(open(self.match_file1.name, "rb").read()[0:-1])
        self.broken_file.flush()

        for i in xrange(1, 4):
            track = self.type.from_pcm(
                os.path.join(self.match_dir1,
                             "%2.2d.%s" % (i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

            track = self.type.from_pcm(
                os.path.join(self.match_dir2,
                             "%2.2d.%s" % (i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

            track = self.type.from_pcm(
                os.path.join(self.mismatch_dir1,
                             "%2.2d.%s" % (i, self.type.SUFFIX)),
                RANDOM_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

        for i in xrange(1, 3):
            track = self.type.from_pcm(
                os.path.join(self.mismatch_dir2,
                             "%2.2d.%s" % (i, self.type.SUFFIX)),
                BLANK_PCM_Reader(i * 2))
            track.set_metadata(audiotools.MetaData(track_number=i))

        for i in xrange(1, 5):
            track = self.type.from_pcm(
                os.path.join(self.mismatch_dir3,
                             "%2.2d.%s" % (i, self.type.SUFFIX)),
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
    def test_combinations(self):
        from audiotools.text import (LAB_TRACKCMP_CMP,
                                     LAB_TRACKCMP_MISMATCH,
                                     LAB_TRACKCMP_TYPE_MISMATCH,
                                     LAB_TRACKCMP_OK,
                                     LAB_TRACKCMP_MISSING)

        #check matching file against maching file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_file2.name]),
            0)

        #check matching file against itself
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_file1.name]),
            0)

        #check matching file against mismatching file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.mismatch_file.name]),
            1)
        self.__check_info__(
            (LAB_TRACKCMP_CMP %
             {"file1":audiotools.Filename(self.match_file1.name),
              "file2":audiotools.Filename(self.mismatch_file.name)}) +
            u" : " +
            (LAB_TRACKCMP_MISMATCH %
             {"frame_number": 1}))

        #(ANSI output won't be generated because stdout isn't a TTY)

        #check matching file against missing file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, "/dev/null/foo"]),
            1)
        self.__check_error__(
            (LAB_TRACKCMP_CMP %
             {"file1":audiotools.Filename(self.match_file1.name),
              "file2":audiotools.Filename("/dev/null/foo")}) +
            u" : " + LAB_TRACKCMP_TYPE_MISMATCH)

        #check matching file against broken file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.broken_file.name]),
            1)
        self.__check_error__(u"EOF reading frame")

        #check file against directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_dir1]),
            1)
        self.__check_error__(
            (LAB_TRACKCMP_CMP %
             {"file1":audiotools.Filename(self.match_file1.name),
              "file2":audiotools.Filename(self.match_dir1)}) +
            u" : " + LAB_TRACKCMP_TYPE_MISMATCH)

        #check directory against file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_dir1, self.match_file1.name]),
            1)
        self.__check_error__(
            (LAB_TRACKCMP_CMP %
             {"file1":audiotools.Filename(self.match_dir1),
              "file2":audiotools.Filename(self.match_file1.name)}) +
            u" : " + LAB_TRACKCMP_TYPE_MISMATCH)

        #check matching directory against matching directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.match_dir2]),
            0)
        for i in xrange(1, 4):
            self.__check_info__(
                audiotools.output_progress(
                    (LAB_TRACKCMP_CMP %
                     {"file1":audiotools.Filename(
                                os.path.join(self.match_dir1,
                                             "%2.2d.%s" %
                                             (i, self.type.SUFFIX))),
                      "file2":audiotools.Filename(
                                os.path.join(self.match_dir2,
                                             "%2.2d.%s" %
                                             (i, self.type.SUFFIX)))}) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 3))

        #check matching directory against itself
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.match_dir1]),
            0)
        for i in xrange(1, 4):
            self.__check_info__(
                audiotools.output_progress(
                    (LAB_TRACKCMP_CMP %
                     {"file1":audiotools.Filename(
                                os.path.join(self.match_dir1,
                                             "%2.2d.%s" %
                                             (i, self.type.SUFFIX))),
                      "file2":audiotools.Filename(
                                os.path.join(self.match_dir1,
                                             "%2.2d.%s" %
                                             (i, self.type.SUFFIX)))}) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 3))

        #check matching directory against mismatching directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir1]),
            1)
        for i in xrange(1, 4):
            self.__check_info__(
                audiotools.output_progress(
                    (LAB_TRACKCMP_CMP %
                     {"file1":audiotools.Filename(
                            os.path.join(self.match_dir1,
                                         "%2.2d.%s" %
                                         (i, self.type.SUFFIX))),
                      "file2":audiotools.Filename(
                            os.path.join(self.mismatch_dir1,
                                         "%2.2d.%s" %
                                         (i, self.type.SUFFIX)))}) +
                    u" : " +
                    (LAB_TRACKCMP_MISMATCH %
                     {"frame_number": 1}),
                    i, 3))

        #check matching directory against directory missing file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir2]),
            1)
        self.__check_info__(
            LAB_TRACKCMP_MISSING % {
                "filename":audiotools.Filename(os.path.basename(
                        "03.%s" % (self.type.SUFFIX))),
                "directory":audiotools.Filename(self.mismatch_dir2)})

        for i in xrange(1, 3):
            self.__check_info__(
                audiotools.output_progress(
                    (LAB_TRACKCMP_CMP %
                     {"file1":audiotools.Filename(
                            os.path.join(self.match_dir1,
                                         "%2.2d.%s" %
                                         (i, self.type.SUFFIX))),
                      "file2":audiotools.Filename(
                            os.path.join(self.mismatch_dir2,
                                         "%2.2d.%s" %
                                         (i, self.type.SUFFIX)))}) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 2))

        #check matching directory against directory with extra file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir3]),
            1)
        self.__check_info__(
            LAB_TRACKCMP_MISSING % {
                "filename":audiotools.Filename(
                    "04.%s" % (self.type.SUFFIX)),
                "directory":audiotools.Filename(self.match_dir1)})

        for i in xrange(1, 4):
            self.__check_info__(
                audiotools.output_progress(
                    (LAB_TRACKCMP_CMP %
                     {"file1":audiotools.Filename(
                            os.path.join(self.match_dir1,
                                         "%2.2d.%s" %
                                         (i, self.type.SUFFIX))),
                      "file2":audiotools.Filename(
                                os.path.join(self.mismatch_dir3,
                                         "%2.2d.%s" %
                                             (i, self.type.SUFFIX)))}) +
                    u" : " +
                    LAB_TRACKCMP_OK,
                    i, 3))

        #check several files against CD image of those files
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
            tracks = [audio_format.from_pcm(track_file.name, reader)
                      for (track_file, reader) in
                      zip(track_files,
                          audiotools.pcm_split(image.to_pcm(), lengths))]

            for (i, track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            from random import shuffle

            shuffled = tracks[:]
            shuffle(shuffled)

            for order in [[track.filename for track in tracks],
                          [track.filename for track in reversed(tracks)],
                          [track.filename for track in shuffled]]:
                self.assertEqual(
                    self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                                      image.filename] + order), 0)
                for (i, track) in enumerate(tracks):
                    self.__check_info__(
                        audiotools.output_progress(
                            LAB_TRACKCMP_CMP %
                            {"file1":audiotools.Filename(image.filename),
                             "file2":audiotools.Filename(track.filename)} +
                            u" : " +
                            LAB_TRACKCMP_OK,
                            i + 1, len(tracks)))
        finally:
            image_file.close()
            for track_file in track_files:
                track_file.close()

    @UTIL_TRACKCMP
    def test_unicode(self):
        for (file1, file2) in Possibilities(
            ["file1.flac",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-1.flac'.encode('utf-8')],
            ["file2.flac",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac'.encode('utf-8')]):
            if (os.path.isfile(file1)):
                os.unlink(file1)
            if (os.path.isfile(file2)):
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

            self.assertEqual(
                audiotools.pcm_frame_cmp(
                    track1.to_pcm(),
                    track2.to_pcm()), None)

            if (os.path.isfile(file1)):
                os.unlink(file1)
            if (os.path.isfile(file2)):
                os.unlink(file2)


class trackinfo(UtilTest):
    METADATA_FORMATS = (audiotools.FlacAudio,
                        audiotools.OggFlacAudio,
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
    def test_trackinfo(self):
        import re
        import StringIO
        from audiotools.text import (LAB_TRACKINFO_CHANNELS,
                                     LAB_TRACKINFO_CHANNEL,
                                     MASK_FRONT_LEFT,
                                     MASK_FRONT_RIGHT)

        all_options = ["-n", "-L", "-b", "-%", "-C"]

        for track in self.metadata_tracks:
            for count in xrange(1, len(all_options) + 1):
                for options in Combinations(all_options, count):
                    self.assertEqual(
                        self.__run_app__(
                            ["trackinfo"] + options + [track.filename]), 0)

                    #check the initial output line
                    line = self.stdout.readline()
                    if ("-b" in options):
                        self.assert_(
                            re.match(r'\s*\d+ kbps: %s\n' %
                                     (track.filename), line) is not None)
                    elif ("-%" in options):
                        self.assert_(
                            re.match(r'\s*\d+%%: %s\n' %
                                     (track.filename), line) is not None)
                    else:
                        self.assert_(
                            re.match(r'\d+:\d+ 2ch 44.1kHz 16-bit: %s\n' %
                                     (track.filename), line) is not None)

                    #check metadata/low-level metadata if -n not present
                    if ("-n" not in options):
                        if ("-L" not in options):
                            for line in StringIO.StringIO(
                                unicode(track.get_metadata())):
                                self.__check_output__(line.rstrip('\r\n'))
                        else:
                            for line in StringIO.StringIO(
                                track.get_metadata().raw_info()):
                                self.__check_output__(line.rstrip('\r\n'))
                        if ("-C" in options):
                            self.__check_output__(u"")
                    else:
                        #no metadata display at all
                        pass

                    #check channel assignment if -C present
                    if ("-C" in options):
                        self.__check_output__(LAB_TRACKINFO_CHANNELS)
                        self.__check_output__(
                            LAB_TRACKINFO_CHANNEL %
                            {"channel_number":1,
                             "channel_name":MASK_FRONT_LEFT})
                        self.__check_output__(
                            LAB_TRACKINFO_CHANNEL %
                            {"channel_number":2,
                             "channel_name":MASK_FRONT_RIGHT})

    @UTIL_TRACKINFO
    def test_unicode(self):
        for filename in [
            "track.flac",
            u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')]:
            if (os.path.isfile(filename)):
                os.unlink(filename)

            track = audiotools.FlacAudio.from_pcm(
                filename,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(["trackinfo", filename]), 0)

            if (os.path.isfile(filename)):
                os.unlink(filename)


class tracklength(UtilTest):
    @UTIL_TRACKLENGTH
    def setUp(self):
        pass

    @UTIL_TRACKLENGTH
    def tearDown(self):
        pass

    @UTIL_TRACKLENGTH
    def test_tracklength(self):
        import shutil
        from audiotools.text import (LAB_TRACKLENGTH_FILE_FORMAT,
                                     LAB_TRACKLENGTH_FILE_COUNT,
                                     LAB_TRACKLENGTH_FILE_LENGTH,
                                     LAB_TRACKLENGTH_FILE_SIZE,
                                     LAB_TRACKLENGTH)

        track1 = audiotools.open("1s.flac")
        track2 = audiotools.open("1m.flac")
        track3 = audiotools.open("1h.flac")
        self.assertEqual(track1.seconds_length(), 1)
        self.assertEqual(track2.seconds_length(), 60)
        self.assertEqual(track3.seconds_length(), 60 * 60)
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac"]), 0)
        self.__check_output__(u"%6s %5s %7s %4s" %
                              (LAB_TRACKLENGTH_FILE_FORMAT,
                               LAB_TRACKLENGTH_FILE_COUNT,
                               LAB_TRACKLENGTH_FILE_LENGTH,
                               LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"%s %s %s %s" %
                              (u"-" * 6,
                               u"-" * 5,
                               u"-" * 7,
                               u"-" * 4))
        self.__check_output__(u"%6s %5s %7s %4s" %
                              (u"flac",
                               1,
                               LAB_TRACKLENGTH % {"hours":0,
                                                  "minutes":0,
                                                  "seconds":1},
                               380))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1s.flac"]), 0)
        self.__check_output__(u"%6s %5s %7s %4s" %
                              (LAB_TRACKLENGTH_FILE_FORMAT,
                               LAB_TRACKLENGTH_FILE_COUNT,
                               LAB_TRACKLENGTH_FILE_LENGTH,
                               LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"%s %s %s %s" %
                              (u"-" * 6,
                               u"-" * 5,
                               u"-" * 7,
                               u"-" * 4))
        self.__check_output__(u"%6s %5s %7s %4s" %
                              (u"flac",
                               2,
                               LAB_TRACKLENGTH % {"hours":0,
                                                  "minutes":0,
                                                  "seconds":2},
                               760))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac"]), 0)
        self.__check_output__(u"%6s %5s %7s %4s" %
                              (LAB_TRACKLENGTH_FILE_FORMAT,
                               LAB_TRACKLENGTH_FILE_COUNT,
                               LAB_TRACKLENGTH_FILE_LENGTH,
                               LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"%s %s %s %s" %
                              (u"-" * 6,
                               u"-" * 5,
                               u"-" * 7,
                               u"-" * 4))
        self.__check_output__(u"%6s %5s %7s %4s" %
                              (u"flac",
                               2,
                               LAB_TRACKLENGTH % {"hours":0,
                                                  "minutes":1,
                                                  "seconds":1},
                               u"9.8K"))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1m.flac"]), 0)
        self.__check_output__(u"%6s %5s %7s %5s" %
                              (LAB_TRACKLENGTH_FILE_FORMAT,
                               LAB_TRACKLENGTH_FILE_COUNT,
                               LAB_TRACKLENGTH_FILE_LENGTH,
                               LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"%s %s %s %s" %
                              (u"-" * 6,
                               u"-" * 5,
                               u"-" * 7,
                               u"-" * 5))
        self.__check_output__(u"%6s %5s %7s %5s" %
                              (u"flac",
                               3,
                               LAB_TRACKLENGTH % {"hours":0,
                                                  "minutes":2,
                                                  "seconds":1},
                               u"19.1K"))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1h.flac"]), 0)
        self.__check_output__(u"%6s %5s %7s %5s" %
                              (LAB_TRACKLENGTH_FILE_FORMAT,
                               LAB_TRACKLENGTH_FILE_COUNT,
                               LAB_TRACKLENGTH_FILE_LENGTH,
                               LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"%s %s %s %s" %
                              (u"-" * 6,
                               u"-" * 5,
                               u"-" * 7,
                               u"-" * 5))
        self.__check_output__(u"%6s %5s %7s %5s" %
                              (u"flac",
                               3,
                               LAB_TRACKLENGTH % {"hours":1,
                                                  "minutes":1,
                                                  "seconds":1},
                               u"22.5K"))

        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1h.flac",
                                           "1h.flac"]), 0)
        self.__check_output__(u"%6s %5s %7s %5s" %
                              (LAB_TRACKLENGTH_FILE_FORMAT,
                               LAB_TRACKLENGTH_FILE_COUNT,
                               LAB_TRACKLENGTH_FILE_LENGTH,
                               LAB_TRACKLENGTH_FILE_SIZE))
        self.__check_output__(u"%s %s %s %s" %
                              (u"-" * 6,
                               u"-" * 5,
                               u"-" * 7,
                               u"-" * 5))
        self.__check_output__(u"%6s %5s %7s %5s" %
                              (u"flac",
                               4,
                               LAB_TRACKLENGTH % {"hours":2,
                                                  "minutes":1,
                                                  "seconds":1},
                               u"35.3K"))

        tempdir = tempfile.mkdtemp()
        try:
            shutil.copy(track1.filename, tempdir)
            shutil.copy(track2.filename, tempdir)
            shutil.copy(track3.filename, tempdir)
            self.assertEqual(self.__run_app__(["tracklength", tempdir]), 0)
            self.__check_output__(u"%6s %5s %7s %5s" %
                                  (LAB_TRACKLENGTH_FILE_FORMAT,
                                   LAB_TRACKLENGTH_FILE_COUNT,
                                   LAB_TRACKLENGTH_FILE_LENGTH,
                                   LAB_TRACKLENGTH_FILE_SIZE))
            self.__check_output__(u"%s %s %s %s" %
                                  (u"-" * 6,
                                   u"-" * 5,
                                   u"-" * 7,
                                   u"-" * 5))
            self.__check_output__(u"%6s %5s %7s %5s" %
                                  (u"flac",
                                   3,
                                   LAB_TRACKLENGTH % {"hours":1,
                                                      "minutes":1,
                                                      "seconds":1},
                                   u"22.5K"))
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir, f))
            os.rmdir(tempdir)

    @UTIL_TRACKLENGTH
    def test_unicode(self):
        for filename in [
            "track.flac",
            u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')]:
            if (os.path.isfile(filename)):
                os.unlink(filename)

            track = audiotools.FlacAudio.from_pcm(
                filename,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(["tracklength", filename]), 0)

            if (os.path.isfile(filename)):
                os.unlink(filename)


class tracklint(UtilTest):
    @UTIL_TRACKLINT
    def setUp(self):
        pass

    @UTIL_TRACKLINT
    def tearDown(self):
        pass

    @UTIL_TRACKLINT
    def test_vorbis(self):
        for audio_class in [audiotools.OggFlacAudio,
                            audiotools.VorbisAudio]:
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
            tempmp = os.path.join(tempdir, "track.%s" % (audio_class.SUFFIX))
            undo = os.path.join(tempdir, "undo.db")
            try:
                track = audio_class.from_pcm(tempmp, BLANK_PCM_Reader(10))

                track.set_metadata(bad_vorbiscomment)
                metadata = track.get_metadata()
                if (isinstance(metadata, audiotools.FlacMetaData)):
                    metadata = metadata.get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                self.assertEqual(metadata, bad_vorbiscomment)
                for (key, value) in metadata.items():
                    self.assertEqual(value, bad_vorbiscomment[key])

                original_checksum = md5()
                f = open(track.filename, 'rb')
                audiotools.transfer_data(f.read, original_checksum.update)
                f.close()

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--fix", "--db=%s" % (undo),
                                 track.filename])

                metadata = track.get_metadata()
                self.assertNotEqual(metadata, bad_vorbiscomment)
                self.assertEqual(metadata, fixed)

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--undo", "--db=%s" % (undo),
                                 track.filename])

                metadata = track.get_metadata()
                if (isinstance(metadata, audiotools.FlacMetaData)):
                    metadata = metadata.get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                self.assertEqual(metadata, bad_vorbiscomment)
                self.assertNotEqual(metadata, fixed)
                for (key, value) in metadata.items():
                    self.assertEqual(value, bad_vorbiscomment[key])
            finally:
                for f in os.listdir(tempdir):
                    os.unlink(os.path.join(tempdir, f))
                os.rmdir(tempdir)

    @UTIL_TRACKLINT
    def test_flac1(self):
        #copy the test track to a temporary location
        tempflac = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            f = open("flac-id3.flac", "rb")
            audiotools.transfer_data(f.read, tempflac.write)
            f.close()
            tempflac.flush()

            tempflac.seek(0, 0)
            self.assertEqual(tempflac.read(3), "ID3")
            tempflac.seek(-0x80, 2)
            self.assertEqual(tempflac.read(3), "TAG")

            #ensure that FLACs tagged with ID3v2/ID3v1 comments are scrubbed
            self.assertEqual(self.__run_app__(
                    ["tracklint", "-V", "quiet", "--fix", tempflac.name]), 0)
            flac = audiotools.open(tempflac.name)
            md5sum = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_framelist_data(pcm, md5sum.update)
            pcm.close()
            self.assertEqual(md5sum.hexdigest(),
                             "9a0ab096c517a627b0ab5a0b959e5f36")
        finally:
            tempflac.close()

    @UTIL_TRACKLINT
    def test_flac2(self):
        #copy the test track to a temporary location
        tempflac = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            f = open("flac-disordered.flac", "rb")
            audiotools.transfer_data(f.read, tempflac.write)
            f.close()
            tempflac.flush()

            tempflac.seek(0, 0)
            self.assertEqual(tempflac.read(4), 'fLaC')
            self.assertNotEqual(ord(tempflac.read(1)) & 0x07, 0)

            #ensure that FLACs with improper metadata ordering are reordered
            self.assertEqual(self.__run_app__(
                    ["tracklint", "-V", "quiet", "--fix", tempflac.name]), 0)
            flac = audiotools.open(tempflac.name)
            md5sum = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_framelist_data(pcm, md5sum.update)
            pcm.close()
            self.assertEqual(md5sum.hexdigest(),
                             "9a0ab096c517a627b0ab5a0b959e5f36")
        finally:
            tempflac.close()

    @UTIL_TRACKLINT
    def test_flac3(self):
        #create a small temporary flac
        tempflacfile = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            tempflac = audiotools.FlacAudio.from_pcm(
                tempflacfile.name,
                BLANK_PCM_Reader(3))

            #build an image from metadata
            image = audiotools.Image.new(TEST_COVER1, u"Description", 0)
            good_mime_type = image.mime_type
            good_width = image.width
            good_height = image.height
            good_depth = image.color_depth
            good_count = image.color_count
            good_description = image.description
            good_type = image.type

            #update image with bogus fields
            image.width = 0
            image.height = 0
            image.color_depth = 0
            image.color_count = 0
            image.mime_type = u'img/jpg'

            #tag flac with bogus fields image
            metadata = tempflac.get_metadata()
            metadata.add_image(image)
            tempflac.set_metadata(metadata)

            #ensure bogus fields stick
            image = tempflac.get_metadata().images()[0]
            self.assertEqual(image.width, 0)
            self.assertEqual(image.height, 0)
            self.assertEqual(image.color_depth, 0)
            self.assertEqual(image.color_count, 0)
            self.assertEqual(image.mime_type, u'img/jpg')

            #fix flac with tracklint
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", tempflac.filename, "--fix"]),
                0)

            #ensure bogus fields are fixed
            tempflac = audiotools.open(tempflacfile.name)
            image = tempflac.get_metadata().images()[0]
            self.assertEqual(image.width, good_width)
            self.assertEqual(image.height, good_height)
            self.assertEqual(image.color_depth, good_depth)
            self.assertEqual(image.color_count, good_count)
            self.assertEqual(image.mime_type, good_mime_type)
            self.assertEqual(image.description, good_description)
            self.assertEqual(image.type, good_type)
        finally:
            tempflacfile.close()

    @UTIL_TRACKLINT
    def test_flac4(self):
        #create a small temporary FLAC
        tempflacfile = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            #update it with the data from "flac-nonmd5.flac"
            f = open("flac-nonmd5.flac", "rb")
            audiotools.transfer_data(f.read, tempflacfile.write)
            f.close()
            tempflacfile.flush()

            #ensure MD5SUM is empty
            tempflac = audiotools.open(tempflacfile.name)
            self.assertEqual(tempflac.__md5__, chr(0) * 16)

            #ensure file verifies okay
            self.assertEqual(tempflac.verify(), True)

            #fix FLAC with tracklint
            self.assertEqual(
                self.__run_app__(
                    ["tracklint", "-V", "quiet", tempflac.filename, "--fix"]),
                0)

            #ensure file's new MD5SUM matches its actual MD5SUM
            tempflac2 = audiotools.open(tempflacfile.name)
            self.assertEqual(tempflac2.__md5__,
                             "\xd2\xb1\x20\x19\x90\x19\xb6\x39" +
                             "\xd5\xa7\xe2\xb3\x46\x3e\x9c\x97")
            self.assertEqual(tempflac2.verify(), True)
        finally:
            tempflacfile.close()

    @UTIL_TRACKLINT
    def test_apev2(self):
        for audio_class in [audiotools.WavPackAudio]:
            bad_apev2 = audiotools.ApeTag(
                [audiotools.ape.ApeTagItem(0, False, "Title", "Track Name  "),
                 audiotools.ape.ApeTagItem(0, False, "Track", "02"),
                 audiotools.ape.ApeTagItem(0, False, "Artist", "  Some Artist"),
                 audiotools.ape.ApeTagItem(0, False, "Catalog", ""),
                 audiotools.ape.ApeTagItem(0, False, "Year", "  "),
                 audiotools.ape.ApeTagItem(0, False, "Comment", "  Some Comment  ")])

            fixed = audiotools.MetaData(
                track_name=u"Track Name",
                track_number=2,
                artist_name=u"Some Artist",
                comment=u"Some Comment")

            self.assertNotEqual(fixed, bad_apev2)

            tempdir = tempfile.mkdtemp()
            tempmp = os.path.join(tempdir, "track.%s" % (audio_class.SUFFIX))
            undo = os.path.join(tempdir, "undo.db")
            try:
                track = audio_class.from_pcm(tempmp, BLANK_PCM_Reader(10))

                track.set_metadata(bad_apev2)
                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_apev2)
                for key in metadata.keys():
                    self.assertEqual(metadata[key].data, bad_apev2[key].data)

                original_checksum = md5()
                f = open(track.filename, 'rb')
                audiotools.transfer_data(f.read, original_checksum.update)
                f.close()

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--fix", "--db=%s" % (undo),
                                 track.filename])

                metadata = track.get_metadata()
                self.assertNotEqual(metadata, bad_apev2)
                self.assertEqual(metadata, fixed)

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--undo", "--db=%s" % (undo),
                                 track.filename])

                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_apev2)
                self.assertNotEqual(metadata, fixed)
                for tag in metadata.tags:
                    self.assertEqual(tag.data, bad_apev2[tag.key].data)
            finally:
                for f in os.listdir(tempdir):
                    os.unlink(os.path.join(tempdir, f))
                os.rmdir(tempdir)

    def __id3_text__(self, bad_id3v2):
        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            album_number=3,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed, bad_id3v2)

        tempdir = tempfile.mkdtemp()
        tempmp = os.path.join(tempdir, "track.%s" % \
                                  (audiotools.MP3Audio.SUFFIX))
        undo = os.path.join(tempdir, "undo.db")
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
            f = open(track.filename, 'rb')
            audiotools.transfer_data(f.read, original_checksum.update)
            f.close()

            subprocess.call(["tracklint",
                             "-V", "quiet",
                             "--fix", "--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertNotEqual(metadata, bad_id3v2)
            self.assertEqual(metadata, fixed)

            subprocess.call(["tracklint",
                             "-V", "quiet",
                             "--undo", "--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertEqual(metadata, bad_id3v2)
            self.assertNotEqual(metadata, fixed)
            for (key, value) in metadata.items():
                self.assertEqual(value, bad_id3v2[key])
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir, f))
            os.rmdir(tempdir)

    def __id3_images__(self, metadata_class, bad_image, fixed_image):
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + audiotools.MP3Audio.SUFFIX)
        try:
            temp_track = audiotools.MP3Audio.from_pcm(
                temp_file.name,
                BLANK_PCM_Reader(5))
            metadata = metadata_class([])
            metadata.add_image(bad_image)
            temp_track.set_metadata(metadata)

            #first, ensure that the bad_image's fields stick
            bad_image2 = temp_track.get_metadata().images()[0]
            for attr in ["data", "mime_type", "width", "height",
                         "color_depth", "color_count", "description",
                         "type"]:
                self.assertEqual(getattr(bad_image2, attr),
                                 getattr(bad_image, attr))

            #fix the track with tracklint
            self.assertEqual(self.__run_app__(
                    ["tracklint", "-V", "quiet", "--fix", temp_file.name]),
                             0)
            temp_track = audiotools.open(temp_file.name)

            #then, ensure that the good fields are now in place
            good_image = temp_track.get_metadata().images()[0]
            for attr in ["data", "mime_type", "width", "height",
                         "color_depth", "color_count", "description",
                         "type"]:
                self.assertEqual(getattr(good_image, attr),
                                 getattr(fixed_image, attr))
        finally:
            temp_file.close()

    @UTIL_TRACKLINT
    def test_id3v22(self):
        self.__id3_text__(
            audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(
                        "TT2", u"Track Name  "),
                 audiotools.id3.ID3v22_T__Frame.converted(
                        "TRK", u"02"),
                 audiotools.id3.ID3v22_T__Frame.converted(
                        "TPA", u"003"),
                 audiotools.id3.ID3v22_T__Frame.converted(
                        "TP1", u"  Some Artist\u0000"),
                 audiotools.id3.ID3v22_T__Frame.converted(
                        "TRC", u""),
                 audiotools.id3.ID3v22_T__Frame.converted(
                        "TYE", u""),
                 audiotools.id3.ID3v22_COM_Frame.converted(
                        "COM", u"  Some Comment  ")]))

        #ID3v2.2 doesn't store most image fields internally
        #so there's little point in testing them for inaccuracies

    @UTIL_TRACKLINT
    def test_id3v23(self):
        self.__id3_text__(
            audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(
                        "TIT2", u"Track Name  "),
                 audiotools.id3.ID3v23_T___Frame.converted(
                        "TRCK", u"02"),
                 audiotools.id3.ID3v23_T___Frame.converted(
                        "TPOS", u"003"),
                 audiotools.id3.ID3v23_T___Frame.converted(
                        "TPE1", u"  Some Artist\u0000"),
                 audiotools.id3.ID3v23_T___Frame.converted(
                        "TYER", u""),
                 audiotools.id3.ID3v23_T___Frame.converted(
                        "TCOP", u""),
                 audiotools.id3.ID3v23_COMM_Frame.converted(
                        "COMM", u"  Some Comment  ")]))

        good_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)
        bad_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)

        #ID3v2.3 only stores MIME type internally
        #the rest are derived
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
                        "TIT2", u"Track Name  "),
                 audiotools.id3.ID3v24_T___Frame.converted(
                        "TRCK", u"02"),
                 audiotools.id3.ID3v24_T___Frame.converted(
                        "TPOS", u"003"),
                 audiotools.id3.ID3v24_T___Frame.converted(
                        "TPE1", u"  Some Artist\u0000"),
                 audiotools.id3.ID3v24_T___Frame.converted(
                        "TYER", u""),
                 audiotools.id3.ID3v24_T___Frame.converted(
                        "TCOP", u""),
                 audiotools.id3.ID3v24_COMM_Frame.converted(
                        "COMM", u"  Some Comment  ")]))

        good_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)
        bad_image = audiotools.Image.new(TEST_COVER1, u"Description", 0)

        #ID3v2.4 only stores MIME type internally
        #the rest are derived
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
        from audiotools.text import (ERR_ENCODING_ERROR)

        track_file = tempfile.NamedTemporaryFile(
            suffix="." + audiotools.MP3Audio.SUFFIX)
        track_file_stat = os.stat(track_file.name)[0]

        undo_db_dir = tempfile.mkdtemp()
        undo_db = os.path.join(undo_db_dir, "undo.db")

        try:
            track = audiotools.MP3Audio.from_pcm(track_file.name,
                                                 BLANK_PCM_Reader(5))
            track.set_metadata(audiotools.MetaData(
                    track_name=u"Track Name ",
                    track_number=1))
            if (track.get_metadata() is not None):
                #writable undo DB, unwritable file
                os.chmod(track.filename,
                         track_file_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["tracklint", "--fix", "--db", undo_db,
                         track.filename]), 1)

                self.__check_error__(ERR_ENCODING_ERROR %
                                     (audiotools.Filename(track.filename),))

                #no undo DB, unwritable file
                self.assertEqual(self.__run_app__(
                        ["tracklint", "--fix", track.filename]), 1)

                self.__check_error__(ERR_ENCODING_ERROR %
                                     (audiotools.Filename(track.filename),))
        finally:
            os.chmod(track_file.name, track_file_stat)
            track_file.close()
            for p in [os.path.join(undo_db_dir, f) for f in
                      os.listdir(undo_db_dir)]:
                os.unlink(p)
            os.rmdir(undo_db_dir)

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
            [M4A_HDLR_Atom(0, 0, '\x00\x00\x00\x00',
                           'mdir', 'appl', 0, 0, '', 0),
             M4A_Tree_Atom(
                    'ilst',
                    [M4A_ILST_Leaf_Atom(
                            '\xa9nam',
                            [M4A_ILST_Unicode_Data_Atom(
                                    0, 1,
                                    'Track Name  ')]),
                     M4A_ILST_Leaf_Atom(
                            '\xa9ART',
                            [M4A_ILST_Unicode_Data_Atom(
                                    0, 1,
                                    '  Some Artist')]),
                     M4A_ILST_Leaf_Atom(
                            'cprt',
                            [M4A_ILST_Unicode_Data_Atom(
                                    0, 1,
                                    '')]),
                     M4A_ILST_Leaf_Atom(
                            '\xa9day',
                            [M4A_ILST_Unicode_Data_Atom(
                                    0, 1,
                                    '  ')]),
                     M4A_ILST_Leaf_Atom(
                            '\xa9cmt',
                            [M4A_ILST_Unicode_Data_Atom(
                                    0, 1,
                                    '  Some Comment  ')]),
                     M4A_ILST_Leaf_Atom(
                            'trkn',
                            [M4A_ILST_TRKN_Data_Atom(2, 0)]),
                     M4A_ILST_Leaf_Atom(
                            'disk',
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
            tempmp = os.path.join(tempdir, "track.%s" % (audio_class.SUFFIX))
            undo = os.path.join(tempdir, "undo.db")
            try:
                track = audio_class.from_pcm(
                    tempmp,
                    BLANK_PCM_Reader(10))

                track.update_metadata(bad_m4a)
                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_m4a)
                for leaf in metadata.ilst_atom():
                    self.assertEqual(leaf, bad_m4a.ilst_atom()[leaf.name])

                original_checksum = md5()
                f = open(track.filename, 'rb')
                audiotools.transfer_data(f.read, original_checksum.update)
                f.close()

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--fix", "--db=%s" % (undo),
                                 track.filename])

                metadata = track.get_metadata()
                self.assertNotEqual(metadata, bad_m4a)
                self.assertEqual(metadata, fixed)

                subprocess.call(["tracklint",
                                 "-V", "quiet",
                                 "--undo", "--db=%s" % (undo),
                                 track.filename])

                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_m4a)
                self.assertNotEqual(metadata, fixed)
                for leaf in metadata.ilst_atom():
                    self.assertEqual(leaf, bad_m4a.ilst_atom()[leaf.name])
            finally:
                for f in os.listdir(tempdir):
                    os.unlink(os.path.join(tempdir, f))
                os.rmdir(tempdir)

    @UTIL_TRACKLINT
    def test_modtime1(self):
        import stat

        for audio_class in audiotools.AVAILABLE_TYPES:
            track_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(track_file.name,
                                             BLANK_PCM_Reader(5))
                metadata = audiotools.MetaData(
                    track_name="Track Name",
                    track_number=1,
                    track_total=2)
                track.set_metadata(metadata)
                if (track.get_metadata() is not None):
                    orig_stat = os.stat(track.filename)
                    time.sleep(1)

                    #should make no metadata changes
                    self.assertEqual(self.__run_app__(
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
            finally:
                track_file.close()

    @UTIL_TRACKLINT
    def test_modtime2(self):
        import stat

        for audio_class in audiotools.AVAILABLE_TYPES:
            track_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            undo_db = tempfile.NamedTemporaryFile(
                suffix=".db")
            try:
                track = audio_class.from_pcm(track_file.name,
                                             BLANK_PCM_Reader(5))
                metadata = audiotools.MetaData(
                    track_name="Track Name",
                    track_number=1,
                    track_total=2)
                track.set_metadata(metadata)
                if (track.get_metadata() is not None):
                    orig_stat = os.stat(track.filename)
                    time.sleep(1)

                    #should make no metadata changes
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--db", undo_db.name,
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
            finally:
                undo_db.close()
                track_file.close()

    @UTIL_TRACKLINT
    def test_unicode(self):
        for (input_filename,
             backup_database) in Possibilities(
            ["track.flac",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            ["undo.db",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.db'.encode('utf-8')]):
            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)
            if (os.path.isfile(backup_database)):
                os.unlink(backup_database)

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
                                  "--db", backup_database,
                                  input_filename]), 0)

            self.assertEqual(
                audiotools.open(input_filename).get_metadata().track_name,
                u"Track Name")

            self.assertEqual(
                self.__run_app__(["tracklint",
                                  "--undo",
                                  "--db", backup_database,
                                  input_filename]), 0)

            self.assertEqual(
                audiotools.open(input_filename).get_metadata().track_name,
                u"Track Name ")

            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)
            if (os.path.isfile(backup_database)):
                os.unlink(backup_database)

    @UTIL_TRACKLINT
    def test_errors1(self):
        from audiotools.text import (ERR_NO_UNDO_DB,
                                     ERR_OPEN_IOERROR,
                                     ERR_ENCODING_ERROR)

        for audio_class in audiotools.AVAILABLE_TYPES:
            track_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track_file_stat = os.stat(track_file.name)[0]

            undo_db_dir = tempfile.mkdtemp()
            undo_db = os.path.join(undo_db_dir, "undo.db")

            try:
                track = audio_class.from_pcm(track_file.name,
                                             BLANK_PCM_Reader(5))
                track.set_metadata(audiotools.MetaData(
                        track_name=u"Track Name ",
                        track_number=1,
                        track_total=2))

                #general-purpose errors
                self.assertEqual(self.__run_app__(
                        ["tracklint", "--undo", track.filename]), 1)
                self.__check_error__(ERR_NO_UNDO_DB)

                self.assertEqual(self.__run_app__(
                        ["tracklint", "--fix", "--db", "/dev/null/foo.db",
                         track.filename]), 1)
                self.__check_error__(
                    ERR_OPEN_IOERROR %
                    (audiotools.Filename("/dev/null/foo.db"),))

                self.assertEqual(self.__run_app__(
                        ["tracklint", "--undo", "--db", "/dev/null/foo.db",
                         track.filename]), 1)
                self.__check_error__(
                    ERR_OPEN_IOERROR %
                    (audiotools.Filename("/dev/null/foo.db"),))

                if (track.get_metadata() is not None):
                    #unwritable undo DB, writable file
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(
                        ERR_OPEN_IOERROR %
                        (audiotools.Filename("/dev/null/undo.db"),))

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--undo", "--db",
                             "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(
                        ERR_OPEN_IOERROR %
                        (audiotools.Filename("/dev/null/undo.db"),))

                    #unwritable undo DB, unwritable file
                    os.chmod(track.filename, track_file_stat & 0x7555)

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(
                        ERR_OPEN_IOERROR %
                        (audiotools.Filename("/dev/null/undo.db"),))

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--undo", "--db",
                             "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(
                        ERR_OPEN_IOERROR %
                        (audiotools.Filename("/dev/null/undo.db"),))

                    #restore from DB to unwritable file
                    os.chmod(track.filename, track_file_stat)
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", undo_db,
                             track.filename]), 0)
                    os.chmod(track.filename, track_file_stat & 0x7555)
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--undo", "--db", undo_db,
                             track.filename]), 1)
                    self.__check_error__(
                        ERR_ENCODING_ERROR %
                        (audiotools.Filename(track.filename),))

            finally:
                os.chmod(track_file.name, track_file_stat)
                track_file.close()
                for p in [os.path.join(undo_db_dir, f) for f in
                          os.listdir(undo_db_dir)]:
                    os.unlink(p)
                os.rmdir(undo_db_dir)

    @UTIL_TRACKLINT
    def test_errors2(self):
        from audiotools.text import (ERR_ENCODING_ERROR)

        for audio_class in audiotools.AVAILABLE_TYPES:
            track_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track_file_stat = os.stat(track_file.name)[0]

            undo_db_dir = tempfile.mkdtemp()
            undo_db = os.path.join(undo_db_dir, "undo.db")

            try:
                track = audio_class.from_pcm(track_file.name,
                                             BLANK_PCM_Reader(5))
                track.set_metadata(audiotools.MetaData(
                        track_name=u"Track Name ",
                        track_number=1))
                if (track.get_metadata() is not None):
                    #writable undo DB, unwritable file
                    os.chmod(track.filename,
                             track_file_stat & 0x7555)

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", undo_db,
                             track.filename]), 1)

                    self.__check_error__(
                        ERR_ENCODING_ERROR %
                        (audiotools.Filename(track.filename),))
            finally:
                os.chmod(track_file.name, track_file_stat)
                track_file.close()
                for p in [os.path.join(undo_db_dir, f) for f in
                          os.listdir(undo_db_dir)]:
                    os.unlink(p)
                os.rmdir(undo_db_dir)


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
            comment=u"Comment 1")

        self.image = audiotools.Image.new(TEST_COVER1, u"", 0)
        self.initial_metadata.add_image(self.image)

        track_base = audiotools.FlacAudio.from_pcm(
            track_file_base.name,
            BLANK_PCM_Reader(1))
        track_base.set_metadata(self.initial_metadata)
        self.track_data = open(track_base.filename, 'rb').read()
        track_file_base.close()

        self.track_file = tempfile.NamedTemporaryFile()

        self.comment_file = tempfile.NamedTemporaryFile(suffix=".txt")
        self.comment_file.write("Comment File")
        self.comment_file.flush()

    @UTIL_TRACKTAG
    def tearDown(self):
        self.track_file.close()
        self.comment_file.close()

    def populate_options(self, options):
        populated = []

        for option in sorted(options):
            if (option == '--name'):
                populated.append(option)
                populated.append("Name 3")
            elif (option == '--artist'):
                populated.append(option)
                populated.append("Artist 3")
            elif (option == '--album'):
                populated.append(option)
                populated.append("Album 3")
            elif (option == '--number'):
                populated.append(option)
                populated.append("5")
            elif (option == '--track-total'):
                populated.append(option)
                populated.append("6")
            elif (option == '--album-number'):
                populated.append(option)
                populated.append("7")
            elif (option == '--album-total'):
                populated.append(option)
                populated.append("8")
            elif (option == '--comment'):
                populated.append(option)
                populated.append("Comment 3")
            elif (option == '--comment-file'):
                populated.append(option)
                populated.append(self.comment_file.name)
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKTAG
    def test_options(self):
        from audiotools.text import (ERR_DUPLICATE_FILE,)

        #start out with a bit of sanity checking
        f = open(self.track_file.name, 'wb')
        f.write(self.track_data)
        f.close()

        track = audiotools.open(self.track_file.name)
        track.verify()
        metadata = track.get_metadata()
        self.assertEqual(metadata.images(),
                         [self.image])

        #Why not test all of tracktag's options?
        #The trouble is that it has 30 metadata-specific options
        #and the set of all possible combinations from 1 to 30 options
        #literally numbers in the millions.
        #Since most of those options are straight text,
        #we'll restrict the tests to the more interesting ones
        #which is still over 8000 different option combinations.
        most_options = ['-r', '--name', '--number', '--track-total',
                        '--album-number', '--comment', '--comment-file']

        #ensure tagging the same file twice triggers an error
        self.assertEqual(self.__run_app__(
                ["tracktag", "--name=Test",
                 self.track_file.name, self.track_file.name]), 1)
        self.__check_error__(ERR_DUPLICATE_FILE %
                             (audiotools.Filename(self.track_file.name),))

        for count in xrange(1, len(most_options) + 1):
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

                if ("--name" in options):
                    self.assertEqual(metadata.track_name, u"Name 3")
                elif ("-r" in options):
                    self.assertEqual(metadata.track_name, None)
                else:
                    self.assertEqual(metadata.track_name, u"Name 1")

                if ("--artist" in options):
                    self.assertEqual(metadata.artist_name, u"Artist 3")
                elif ("-r" in options):
                    self.assertEqual(metadata.artist_name, None)
                else:
                    self.assertEqual(metadata.artist_name, u"Artist 1")

                if ("--album" in options):
                    self.assertEqual(metadata.album_name, u"Album 3")
                elif ("-r" in options):
                    self.assertEqual(metadata.album_name, None)
                else:
                    self.assertEqual(metadata.album_name, u"Album 1")

                if ("--number" in options):
                    self.assertEqual(metadata.track_number, 5)
                elif ("-r" in options):
                    self.assertEqual(metadata.track_number, None)
                else:
                    self.assertEqual(metadata.track_number, 1)

                if ("--track-total" in options):
                    self.assertEqual(metadata.track_total, 6)
                elif ("-r" in options):
                    self.assertEqual(metadata.track_total, None)
                else:
                    self.assertEqual(metadata.track_total, 2)

                if ("--album-number" in options):
                    self.assertEqual(metadata.album_number, 7)
                elif ("-r" in options):
                    self.assertEqual(metadata.album_number, None)
                else:
                    self.assertEqual(metadata.album_number, 3)

                if ("--album-total" in options):
                    self.assertEqual(metadata.album_total, 8)
                elif ("-r" in options):
                    self.assertEqual(metadata.album_total, None)
                else:
                    self.assertEqual(metadata.album_total, 4)

                if ("--comment-file" in options):
                    self.assertEqual(metadata.comment, u"Comment File")
                elif ("--comment" in options):
                    self.assertEqual(metadata.comment, u"Comment 3")
                elif ("-r" in options):
                    self.assertEqual(metadata.comment, None)
                else:
                    self.assertEqual(metadata.comment, u"Comment 1")

                if ("-r" in options):
                    self.assertEqual(metadata.ISRC, None)
                else:
                    self.assertEqual(metadata.ISRC, u"ABCD00000000")

                if ("--replay-gain" in options):
                    self.assert_(track.replay_gain() is not None)

    @UTIL_TRACKTAG
    def test_replaygain(self):
        from audiotools.text import (RG_REPLAYGAIN_ADDED,
                                     RG_REPLAYGAIN_APPLIED)

        for audio_class in audiotools.AVAILABLE_TYPES:
            if (audio_class.supports_replay_gain()):
                track_file = tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)
                try:
                    track = audio_class.from_pcm(
                        track_file.name,
                        BLANK_PCM_Reader(5))
                    self.assertEqual(
                        self.__run_app__(["tracktag", "--replay-gain",
                                          track.filename]), 0)
                    if (audio_class.lossless_replay_gain()):
                        self.__check_info__(RG_REPLAYGAIN_ADDED)
                        track2 = audiotools.open(track_file.name)
                        self.assert_(track2.replay_gain() is not None)
                    else:
                        self.__check_info__(RG_REPLAYGAIN_APPLIED)
                finally:
                    track_file.close()

    @UTIL_TRACKTAG
    def test_unicode(self):
        for (input_filename,
             (argument, attribute),
             unicode_value) in Possibilities(
            ["track.flac",  #check filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            [("--name", "track_name"),  #check text arguments
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
            [u"text",
             u'value abc\xe0\xe7\xe8\u3041\u3044\u3046']):
            self.assert_(isinstance(unicode_value, unicode))

            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                BLANK_PCM_Reader(1))

            self.assertEqual(
                self.__run_app__(["tracktag",
                                  argument,
                                  unicode_value.encode('utf-8'),
                                  input_filename]), 0)

            set_value = getattr(audiotools.open(input_filename).get_metadata(),
                                attribute)
            if (set_value is not None):
                self.assertEqual(set_value, unicode_value)

            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)

        for (input_filename,
             comment_filename) in Possibilities(
            ["track.flac",     #check input filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            ["comment.txt",    #check comment filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.txt'.encode('utf-8')]):
            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)
            if (os.path.isfile(comment_filename)):
                os.unlink(comment_filename)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                BLANK_PCM_Reader(1))

            f = open(comment_filename, "wb")
            f.write("Test Text")
            f.close()

            self.assertEqual(
                self.__run_app__(["tracktag",
                                  "--comment-file", comment_filename,
                                  input_filename]), 0)

            self.assertEqual(
                audiotools.open(input_filename).get_metadata().comment,
                u"Test Text")

            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)
            if (os.path.isfile(comment_filename)):
                os.unlink(comment_filename)

class tracktag_errors(UtilTest):
    @UTIL_TRACKTAG
    def test_bad_options(self):
        from audiotools.text import (ERR_OPEN_IOERROR,
                                     ERR_ENCODING_ERROR,
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

            self.assertEqual(self.__run_app__(
                    ["tracktag", "--comment-file=/dev/null/foo.txt",
                     temp_track.filename]), 1)
            self.__check_error__(ERR_TRACKTAG_COMMENT_IOERROR %
                                 (audiotools.Filename("/dev/null/foo.txt"),))

            temp_comment.write(
                os.urandom(1024) + ((u"\uFFFD".encode('utf-8')) * 103))
            temp_comment.flush()

            self.assertEqual(self.__run_app__(
                    ["tracktag", "--comment-file=%s" % (temp_comment.name),
                     temp_track.filename]), 1)
            self.__check_error__(ERR_TRACKTAG_COMMENT_NOT_UTF8 %
                                 (audiotools.Filename(temp_comment.name),))

            os.chmod(temp_track_file.name, temp_track_stat & 07555)
            self.assertEqual(self.__run_app__(
                    ["tracktag", "--name=Bar",
                     temp_track.filename]), 1)
            self.__check_error__(ERR_ENCODING_ERROR %
                                 (audiotools.Filename(temp_track.filename),))
        finally:
            os.chmod(temp_track_file.name, temp_track_stat)
            temp_track_file.close()
            temp_comment.close()

    @UTIL_TRACKTAG
    def test_oversized_metadata(self):
        for audio_class in [audiotools.FlacAudio,
                            audiotools.OggFlacAudio]:
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

                big_text.write("QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2'))
                big_text.flush()

                orig_md5 = md5()
                pcm = flac.to_pcm()
                audiotools.transfer_framelist_data(pcm, orig_md5.update)
                pcm.close()

                #ensure that setting big text via tracktag
                #doesn't break the file
                subprocess.call(["tracktag", "-V", "quiet",
                                 "--comment-file=%s" % (big_text.name),
                                 flac.filename])
                new_md5 = md5()
                pcm = flac.to_pcm()
                audiotools.transfer_framelist_data(pcm, new_md5.update)
                pcm.close()
                self.assertEqual(orig_md5.hexdigest(),
                                 new_md5.hexdigest())

                subprocess.call(["track2track", "-V", "quiet", "-t", "wv",
                                 "-o", tempwv.name,
                                 flac.filename])

                wv = audiotools.open(tempwv.name)

                self.assertEqual(flac, wv)

                self.assertEqual(subprocess.call(
                        ["tracktag", "-V", "quiet",
                         "--comment-file=%s" % (big_text.name),
                         wv.filename]), 0)

                self.assert_(len(wv.get_metadata().comment) > 0)

                subprocess.call(["track2track", "-V", "quiet",
                                 "-t", audio_class.NAME, "-o",
                                 flac.filename, wv.filename])

                flac = audiotools.open(tempflac.name)
                self.assertEqual(flac, wv)
            finally:
                tempflac.close()
                tempwv.close()
                big_text.close()


class NoMetaData(Exception):
    pass


class tracktag_misc(UtilTest):
    @UTIL_TRACKTAG
    def test_text_options(self):
        def number_fields_values(fields, metadata_class):
            values = set([])
            for field in audiotools.MetaData.INTEGER_FIELDS:
                if (field in fields):
                    values.add(
                        (field,
                         audiotools.MetaData.INTEGER_FIELDS.index(
                                field) + 1))
                else:
                    values.add((field, None))

            return values

        def deleted_number_fields_values(fields, metadata_class):
            values = set([])
            for field in audiotools.MetaData.INTEGER_FIELDS:
                if (field not in fields):
                    values.add(
                        (field,
                         audiotools.MetaData.INTEGER_FIELDS.index(
                                field) + 1))
                else:
                    values.add((field, None))

            return values

        def metadata_fields_values(metadata):
            values = set([])
            for field in audiotools.MetaData.INTEGER_FIELDS:
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
                    if (metadata is None):
                        break
                    elif (getattr(metadata, field_name) is not None):
                        self.assertEqual(getattr(metadata, field_name),
                                         u'foo')

                        self.assertEqual(
                            self.__run_app__(['tracktag', remove_field,
                                              track.filename]), 0)

                        metadata = audiotools.open(
                            track.filename).get_metadata()

                        self.assertEqual(
                            getattr(metadata, field_name),
                            None,
                            "remove option failed for %s field %s" %
                            (audio_type.NAME, remove_field))

                number_fields = ['track_number',
                                 'track_total',
                                 'album_number',
                                 'album_total']
                try:
                    #make sure the number fields get set properly, if possible
                    for count in xrange(1, len(number_fields) + 1):
                        for fields in Combinations(number_fields, count):
                            self.assertEqual(
                                self.__run_app__(
                                    ["tracktag", '-r', track.filename] +
                                    self.populate_set_number_fields(fields)),
                                0)
                            metadata = audiotools.open(
                                track.filename).get_metadata()
                            if (metadata is None):
                                raise NoMetaData()

                            self.assert_(
                                metadata_fields_values(metadata).issubset(
                                    number_fields_values(
                                        fields, metadata.__class__)),
                                "%s not subset of %s for fields %s" % (
                                    metadata_fields_values(metadata),
                                    number_fields_values(
                                        fields, metadata.__class__),
                                    repr(fields)))

                    #make sure the number fields get removed properly, also
                    number_metadata = audiotools.MetaData(track_number=1,
                                                          track_total=2,
                                                          album_number=3,
                                                          album_total=4)
                    for count in xrange(1, len(number_fields) + 1):
                        for fields in Combinations(number_fields, count):
                            audiotools.open(track.filename).set_metadata(
                                number_metadata)
                            self.assertEqual(
                                self.__run_app__(
                                   ["tracktag", track.filename] +
                                   self.populate_delete_number_fields(fields)),
                                0)
                            metadata = audiotools.open(
                                track.filename).get_metadata()
                            self.assert_(
                                metadata_fields_values(metadata).issubset(
                                    deleted_number_fields_values(
                                        fields, metadata.__class__)),
                                "%s not subset of %s for options %s, fields %s, type %s" %
                                (metadata_fields_values(metadata),
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
            if (field == 'track_number'):
                options.append('--number')
                options.append(str(1))
            elif (field == 'track_total'):
                options.append('--track-total')
                options.append(str(2))
            elif (field == 'album_number'):
                options.append('--album-number')
                options.append(str(3))
            elif (field == 'album_total'):
                options.append('--album-total')
                options.append(str(4))
        return options

    def populate_delete_number_fields(self, fields):
        options = []
        for field in fields:
            if (field == 'track_number'):
                options.append('--remove-number')
            elif (field == 'track_total'):
                options.append('--remove-track-total')
            elif (field == 'album_number'):
                options.append('--remove-album-number')
            elif (field == 'album_total'):
                options.append('--remove-album-total')
        return options


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
        self.track_data = open(track_base.filename, 'rb').read()
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

    def populate_options(self, options):
        populated = []
        front_covers = [self.front_cover1.name, self.front_cover2.name]

        for option in sorted(options):
            if (option == '--front-cover'):
                populated.append(option)
                populated.append(front_covers.pop(0))
            elif (option == '--back-cover'):
                populated.append(option)
                populated.append(self.back_cover.name)
            elif (option == '--leaflet'):
                populated.append(option)
                populated.append(self.leaflet.name)
            elif (option == '--media'):
                populated.append(option)
                populated.append(self.media.name)
            elif (option == '--other-image'):
                populated.append(option)
                populated.append(self.other.name)
            else:
                populated.append(option)

        return populated

    @UTIL_COVERTAG
    def test_options(self):
        from audiotools.text import (ERR_DUPLICATE_FILE,)

        #start out with a bit of sanity checking
        f = open(self.track_file.name, 'wb')
        f.write(self.track_data)
        f.close()

        track = audiotools.open(self.track_file.name)
        track.verify()
        metadata = track.get_metadata()
        self.assertEqual(metadata.images(),
                         [self.image])

        covertag_options = ['-r', '--front-cover', '--front-cover',
                            '--back-cover', '--leaflet', '--media',
                            '--other-image']

        #ensure tagging the same file twice triggers an error
        self.assertEqual(self.__run_app__(
                ["covertag", "--front-cover", self.front_cover1.name,
                 self.track_file.name, self.track_file.name]), 1)
        self.__check_error__(ERR_DUPLICATE_FILE %
                             (audiotools.Filename(self.track_file.name),))

        for count in xrange(1, len(covertag_options) + 1):
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

                if ('-r' in options):
                    if (options.count('--front-cover') == 0):
                        self.assertEqual(metadata.front_covers(),
                                         [])
                    elif (options.count('--front-cover') == 1):
                        self.assertEqual(metadata.front_covers(),
                                         [self.front_cover1_image])
                    elif (options.count('--front-cover') == 2):
                        self.assertEqual(metadata.front_covers(),
                                         [self.front_cover1_image,
                                          self.front_cover2_image])
                else:
                    if (options.count('--front-cover') == 0):
                        self.assertEqual(metadata.front_covers(),
                                         [self.image])
                    elif (options.count('--front-cover') == 1):
                        self.assertEqual(metadata.front_covers(),
                                         [self.image,
                                          self.front_cover1_image])
                    elif (options.count('--front-cover') == 2):
                        self.assertEqual(metadata.front_covers(),
                                         [self.image,
                                          self.front_cover1_image,
                                          self.front_cover2_image])
                if ('--back-cover' in options):
                    self.assertEqual(metadata.back_covers(),
                                     [self.back_cover_image])
                else:
                    self.assertEqual(metadata.back_covers(),
                                     [])
                if ('--leaflet' in options):
                    self.assertEqual(metadata.leaflet_pages(),
                                     [self.leaflet_image])
                else:
                    self.assertEqual(metadata.leaflet_pages(),
                                     [])
                if ('--media' in options):
                    self.assertEqual(metadata.media_images(),
                                     [self.media_image])
                else:
                    self.assertEqual(metadata.media_images(),
                                     [])
                if ('--other-image' in options):
                    self.assertEqual(metadata.other_images(),
                                     [self.other_image])
                else:
                    self.assertEqual(metadata.other_images(),
                                     [])

    @UTIL_COVERTAG
    def test_unicode(self):
        from shutil import rmtree

        for (file_path,
             option,
             image_path) in Possibilities(
            ["test.flac",  #check filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            ["--front-cover",
             "--back-cover",
             "--leaflet",
             "--media",
             "--other-image"],
            ["image.jpg",  #check image path arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.jpg'.encode('utf-8')]):
            if (os.path.isfile(file_path)):
                os.unlink(file_path)
            if (os.path.isfile(image_path)):
                os.unlink(image_path)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))

            f = open(image_path, "wb")
            f.write(TEST_COVER1)
            f.close()

            self.assertEqual(
                self.__run_app__(
                    ["covertag", option, image_path, file_path]), 0)

            self.assertEqual(
                audiotools.open(file_path).get_metadata().images()[0].data,
                TEST_COVER1)

            if (os.path.isfile(file_path)):
                os.unlink(file_path)
            if (os.path.isfile(image_path)):
                os.unlink(image_path)

class covertag_errors(UtilTest):
    @UTIL_COVERTAG
    def test_bad_options(self):
        from audiotools.text import (ERR_OPEN_IOERROR,)

        temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        temp_track_stat = os.stat(temp_track_file.name)[0]
        try:
            temp_track = audiotools.FlacAudio.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            self.assertEqual(self.__run_app__(
                    ["covertag", "--front-cover=/dev/null/foo.jpg",
                     temp_track.filename]), 1)
            self.__check_error__(
                ERR_OPEN_IOERROR % (audiotools.Filename(u"/dev/null/foo.jpg"),))
        finally:
            os.chmod(temp_track_file.name, temp_track_stat)
            temp_track_file.close()

    @UTIL_COVERTAG
    def test_oversized_metadata(self):
        for audio_class in [audiotools.FlacAudio,
                            audiotools.OggFlacAudio]:
            tempflac = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            big_bmp = tempfile.NamedTemporaryFile(suffix=".bmp")
            try:
                flac = audio_class.from_pcm(
                    tempflac.name,
                    BLANK_PCM_Reader(5))

                flac.set_metadata(audiotools.MetaData(track_name=u"Foo"))

                big_bmp.write(HUGE_BMP.decode('bz2'))
                big_bmp.flush()

                orig_md5 = md5()
                pcm = flac.to_pcm()
                audiotools.transfer_framelist_data(pcm, orig_md5.update)
                pcm.close()

                #ensure that setting a big image via covertag
                #doesn't break the file
                subprocess.call(["covertag", "-V", "quiet",
                                 "--front-cover=%s" % (big_bmp.name),
                                 flac.filename])
                new_md5 = md5()
                pcm = flac.to_pcm()
                audiotools.transfer_framelist_data(pcm, new_md5.update)
                pcm.close()
                self.assertEqual(orig_md5.hexdigest(),
                                 new_md5.hexdigest())
            finally:
                tempflac.close()
                big_bmp.close()

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

    def clean_input_directory(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))

    def populate_options(self, options):
        populated = []
        for option in options:
            if (option == '--format'):
                populated.append(option)
                populated.append(self.format)
            else:
                populated.append(option)
        return populated

    @UTIL_TRACKRENAME
    def test_options(self):
        from audiotools.text import (LAB_ENCODE)

        all_options = ["--format"]
        for count in xrange(0, len(all_options) + 1):
            for (name, metadata) in zip(self.track_names, self.track_metadata):
                for options in Combinations(all_options, count):
                    options = self.populate_options(options)
                    self.clean_input_directory()
                    track = self.type.from_pcm(
                        os.path.join(self.input_dir, name),
                        BLANK_PCM_Reader(1))

                    if (metadata is not None):
                        track.set_metadata(metadata)

                    original_metadata = track.get_metadata()

                    track_data = open(track.filename, 'rb').read()

                    self.assertEqual(
                        self.__run_app__(["trackrename", "-V", "normal",
                                          track.filename] + options), 0)

                    if ("--format" in options):
                        output_format = self.format
                    else:
                        output_format = None

                    if (metadata is not None):
                        base_metadata = metadata
                    else:
                        #track number via filename applies
                        #only if the file has no other metadata
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
                        LAB_ENCODE %
                        {"source":
                             audiotools.Filename(track.filename),
                         "destination":
                             audiotools.Filename(destination_filename)})

                    #check that the file is identical
                    self.assertEqual(track_data,
                                     open(destination_filename, 'rb').read())

    @UTIL_TRACKRENAME
    def test_duplicate(self):
        from audiotools.text import (ERR_DUPLICATE_FILE,
                                     ERR_DUPLICATE_OUTPUT_FILE,
                                     )

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
            ERR_DUPLICATE_FILE %
            (audiotools.Filename(track1.filename),))

        self.assertEqual(
            self.__run_app__(["trackrename", "-V", "normal",
                              "--format", "foo",
                              track1.filename, track2.filename]), 1)

        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE %
            (audiotools.Filename(
                    os.path.join(
                        os.path.dirname(track1.filename), "foo")),))

    @UTIL_TRACKRENAME
    def test_errors(self):
        from audiotools.text import (ERR_FILES_REQUIRED,
                                     ERR_UNKNOWN_FIELD,
                                     LAB_SUPPORTED_FIELDS,
                                     )

        tempdir = tempfile.mkdtemp()
        tempdir_stat = os.stat(tempdir)[0]
        track = self.type.from_pcm(
            os.path.join(tempdir, "01 - track.%s" % (self.type.SUFFIX)),
            BLANK_PCM_Reader(1))
        track.set_metadata(audiotools.MetaData(track_name=u"Name",
                                               track_number=1,
                                               album_name=u"Album"))
        try:
            self.assertEqual(self.__run_app__(["trackrename"]), 1)
            self.__check_error__(ERR_FILES_REQUIRED)

            self.assertEqual(self.__run_app__(
                    ["trackrename", "--format=%(foo)s", track.filename]), 1)

            self.__check_error__(ERR_UNKNOWN_FIELD % ("foo"))
            self.__check_info__(LAB_SUPPORTED_FIELDS)
            for field in sorted(audiotools.MetaData.FIELDS + \
                                    ("album_track_number", "suffix")):
                if (field == 'track_number'):
                    self.__check_info__(u"%(track_number)2.2d")
                else:
                    self.__check_info__(u"%%(%s)s" % (field))
            self.__check_info__(u"%(basename)s")

            if (track.get_metadata() is not None):
                os.chmod(tempdir, tempdir_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["trackrename",
                         '--format=%(album_name)s/%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]), 1)

                self.__check_error__(
                    u"[Errno 13] Permission denied: \'%s\'" % \
                        (audiotools.Filename(
                            os.path.join(
                                os.path.dirname(track.filename), "Album")),))

                self.assertEqual(self.__run_app__(
                        ["trackrename",
                         '--format=%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]), 1)

        finally:
            os.chmod(tempdir, tempdir_stat)
            os.unlink(track.filename)
            os.rmdir(tempdir)

    @UTIL_TRACKRENAME
    def test_unicode(self):
        for (file_path,
             format_string) in Possibilities(
            ["file.flac",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            ["new_file.flac",
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-2.flac'.encode('utf-8')]):
            if (os.path.isfile(file_path)):
                os.unlink(file_path)
            if (os.path.isfile(format_string)):
                os.unlink(format_string)

            track = audiotools.FlacAudio.from_pcm(
                file_path,
                BLANK_PCM_Reader(1))

            self.assertEqual(os.path.isfile(file_path), True)
            self.assertEqual(os.path.isfile(format_string), False)

            self.assertEqual(
                self.__run_app__(
                    ["trackrename", "--format", format_string, file_path]), 0)

            self.assertEqual(os.path.isfile(file_path), False)
            self.assertEqual(os.path.isfile(format_string), True)

            if (os.path.isfile(file_path)):
                os.unlink(file_path)
            if (os.path.isfile(format_string)):
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
        self.cuesheet.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        self.cuesheet.flush()

        self.cuesheet2 = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet2.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC ABCD00000001\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC ABCD00000002\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC ABCD00000003\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        self.cuesheet2.flush()

        self.cuesheet3 = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet3.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n')
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
        os.chdir(self.original_dir)

        self.unsplit_file.close()
        self.unsplit_file2.close()
        self.cuesheet.close()
        self.cuesheet2.close()
        self.cuesheet3.close()

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))
        os.rmdir(self.cwd_dir)

        os.chmod(self.unwritable_dir, 0700)
        os.rmdir(self.unwritable_dir)

    def clean_output_dirs(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))

    def populate_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]
        for option in sorted(options):
            if (option == '-t'):
                populated.append(option)
                populated.append(self.type.NAME)
            elif (option == '-q'):
                populated.append(option)
                populated.append(self.quality)
            elif (option == '-d'):
                populated.append(option)
                populated.append(self.output_dir)
            elif (option == '--format'):
                populated.append(option)
                populated.append(self.format)
            elif (option == '--cue'):
                populated.append(option)
                populated.append(self.cuesheet.name)
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKSPLIT
    def test_options_no_embedded_cue(self):
        from audiotools.text import (ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     ERR_TRACKSPLIT_NO_CUESHEET)

        all_options = ["--cue", "-t", "-q", "-d", "--format"]

        self.stream.reset()
        track = self.type.from_pcm(self.unsplit_file.name, self.stream)
        track.set_metadata(self.unsplit_metadata)

        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                options = self.populate_options(options)

                if ("-t" in options):
                    output_type = audiotools.FlacAudio
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    ("1" not in output_type.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "--no-freedb", "--no-musicbrainz"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                if ("--cue" not in options):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "--no-freedb", "--no-musicbrainz"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(ERR_TRACKSPLIT_NO_CUESHEET)
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal",
                                      "--no-freedb", "--no-musicbrainz"] +
                                     options + [track.filename]), 0)
                if ("--format" in options):
                    output_format = self.format
                else:
                    output_format = None

                if ("-d" in options):
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

                for i in xrange(3):
                    base_metadata.track_number = i + 1
                    output_filenames.append(
                        output_type.track_name(
                            file_path="",
                            track_metadata=base_metadata,
                            format=output_format))

                #check that the output is being generated correctly
                for (i, path) in enumerate(output_filenames):
                    self.__check_info__(
                        audiotools.output_progress(
                            u"%(source)s -> %(destination)s" %
                            {"source":
                                 audiotools.Filename(track.filename),
                             "destination":
                                 audiotools.Filename(
                                    os.path.join(output_dir, path))},
                            i + 1, len(output_filenames)))

                #make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.stream.reset()
                self.assert_(
                    audiotools.pcm_frame_cmp(
                        audiotools.PCMCat([t.to_pcm() for t in output_tracks]),
                        self.stream) is None)

                #make sure metadata fits our expectations
                for i in xrange(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if (metadata is not None):
                        self.assertEqual(metadata.track_name, None)
                        self.assertEqual(metadata.album_name, u"Album 1")
                        self.assertEqual(metadata.artist_name, u"Artist 1")

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)
                        self.assertEqual(metadata.album_number, 4)
                        self.assertEqual(metadata.album_total, 5)
                        self.assertEqual(metadata.performer_name,
                                         u"Performer 1")

                if ("--cue" in options):
                    for (i, ISRC) in enumerate([u"JPPI00652340",
                                                u"JPPI00652349",
                                                u"JPPI00652341"]):
                        metadata = output_tracks[i].get_metadata()
                        if (metadata is not None):
                            self.assertEqual(metadata.ISRC, ISRC)

    @UTIL_TRACKSPLIT
    def test_options_embedded_cue(self):
        from audiotools.text import (ERR_UNSUPPORTED_COMPRESSION_MODE,
                                     LAB_ENCODE,
                                     )

        all_options = ["--cue", "-t", "-q", "-d", "--format"]

        self.stream.reset()
        track = self.type.from_pcm(self.unsplit_file.name, self.stream)
        track.set_metadata(self.unsplit_metadata)
        track.set_cuesheet(audiotools.read_sheet(self.cuesheet2.name))
        self.assert_(track.get_cuesheet() is not None)

        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()
                options = self.populate_options(options)

                if ("-t" in options):
                    output_type = audiotools.FlacAudio
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    ("1" not in output_type.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "--no-freedb", "--no-musicbrainz"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal",
                                      "-j", "1",
                                      "--no-freedb", "--no-musicbrainz"] +
                                     options + [track.filename]), 0)
                if ("--format" in options):
                    output_format = self.format
                else:
                    output_format = None

                if ("-d" in options):
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
                for i in xrange(3):
                    base_metadata.track_number = i + 1
                    output_filenames.append(
                        output_type.track_name(
                            "",
                            base_metadata,
                            output_format))

                #check that the output is being generated correctly
                for (i, path) in enumerate(output_filenames):
                    self.__check_info__(
                        audiotools.output_progress(
                            LAB_ENCODE %
                            {"source":
                                 audiotools.Filename(track.filename),
                             "destination":
                                 audiotools.Filename(
                                    os.path.join(output_dir, path))},
                            i + 1, len(output_filenames)))

                #make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.stream.reset()
                self.assert_(
                    audiotools.pcm_frame_cmp(
                        audiotools.PCMCat([t.to_pcm() for t in output_tracks]),
                        self.stream) is None)

                #make sure metadata fits our expectations
                for i in xrange(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if (metadata is not None):
                        self.assertEqual(metadata.track_name, None)
                        self.assertEqual(metadata.album_name, u"Album 1")
                        self.assertEqual(metadata.artist_name, u"Artist 1")

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)
                        self.assertEqual(metadata.album_number, 4)
                        self.assertEqual(metadata.album_total, 5)
                        self.assertEqual(metadata.performer_name,
                                         u"Performer 1")

                #check ISRC data
                if ("--cue" in options):
                    for (i, ISRC) in enumerate([u"JPPI00652340",
                                                u"JPPI00652349",
                                                u"JPPI00652341"]):
                        metadata = output_tracks[i].get_metadata()
                        if (metadata is not None):
                            self.assertEqual(metadata.ISRC, ISRC)
                else:
                    for (i, ISRC) in enumerate([u"ABCD00000001",
                                                u"ABCD00000002",
                                                u"ABCD00000003"]):
                        metadata = output_tracks[i].get_metadata()
                        if (metadata is not None):
                            self.assertEqual(metadata.ISRC, ISRC)

    @UTIL_TRACKSPLIT
    def test_unicode(self):
        import shutil

        for (input_filename,
             cuesheet_file,
             output_directory,
             output_format) in Possibilities(
            ["track.flac",    #check filename arguments
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.flac'.encode('utf-8')],
            ["cuesheet.cue",  #check --cue argument
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046.cue'.encode('utf-8')],
            ["testdir",       #check --dir argument
             u'abc\xe0\xe7\xe8\u3041\u3044\u3046-dir'.encode('utf-8')],
            ["%(track_number)d.%(suffix)s",  #check --format argument
             u'%(track_number)d - abc\xe0\xe7\xe8\u3041\u3044\u3046.%(suffix)s'.encode('utf-8')]):
            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)
            if (os.path.isfile(cuesheet_file)):
                os.unlink(cuesheet_file)
            if (os.path.isdir(output_directory)):
                shutil.rmtree(output_directory)

            track = audiotools.FlacAudio.from_pcm(
                input_filename,
                EXACT_BLANK_PCM_Reader(sum([220500, 264600, 308700])))

            f = open(cuesheet_file, "wb")
            f.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:03:00\r\n    INDEX 01 00:05:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
            f.close()

            self.assertEqual(
                self.__run_app__(
                    ["tracksplit",
                     "--type", "flac",
                     "--cue", cuesheet_file,
                     "--dir", output_directory,
                     "--format", output_format,
                     input_filename]), 0)

            output_filenames = [output_format % {"track_number":i,
                                                 "suffix":"flac"}
                                for i in range(1, 4)]
            for f in output_filenames:
                self.assertEqual(
                    os.path.isfile(os.path.join(output_directory, f)), True)

            tracks = [audiotools.open(os.path.join(output_directory, f))
                      for f in output_filenames]

            self.assertEqual(
                audiotools.pcm_frame_cmp(
                    track.to_pcm(),
                    audiotools.PCMCat([t.to_pcm() for t in tracks])),
                None)

            if (os.path.isfile(input_filename)):
                os.unlink(input_filename)
            if (os.path.isfile(cuesheet_file)):
                os.unlink(cuesheet_file)
            if (os.path.isdir(output_directory)):
                shutil.rmtree(output_directory)

    def populate_bad_options(self, options):
        populated = ["--no-musicbrainz", "--no-freedb"]

        for option in sorted(options):
            if (option == '-t'):
                populated.append(option)
                populated.append("foo")
            elif (option == '-q'):
                populated.append(option)
                populated.append("bar")
            elif (option == '-d'):
                populated.append(option)
                populated.append(self.unwritable_dir)
            elif (option == '--format'):
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
                                     ERR_TRACKSPLIT_OVERLONG_CUESHEET,

)

        #ensure that unsplitting file to itself generates an error
        track = self.type.from_pcm(self.unsplit_file.name,
                                   BLANK_PCM_Reader(18))
        self.assertEqual(
            self.__run_app__(
                ["tracksplit", self.unsplit_file.name,
                 "--no-freedb", "--no-musicbrainz",
                 "--cue", self.cuesheet3.name,
                 "-d", os.path.dirname(self.unsplit_file.name),
                 "--format", os.path.basename(self.unsplit_file.name)]), 1)
        self.__check_error__(ERR_OUTPUT_IS_INPUT %
                             (audiotools.Filename(self.unsplit_file.name),))

        #ensure that unsplitting file to identical names generates an error
        self.assertEqual(
            self.__run_app__(
                ["tracksplit", self.unsplit_file.name,
                 "--no-freedb", "--no-musicbrainz",
                 "--cue", self.cuesheet.name,
                 "-d", os.path.dirname(self.unsplit_file.name),
                 "--format", "foo"]), 1)
        self.__check_error__(
            ERR_DUPLICATE_OUTPUT_FILE %
            (audiotools.Filename(
                    os.path.join(os.path.dirname(self.unsplit_file.name),
                                 "foo")),))

        track1 = self.type.from_pcm(self.unsplit_file.name,
                                    BLANK_PCM_Reader(18))

        track2 = self.type.from_pcm(self.unsplit_file2.name,
                                    BLANK_PCM_Reader(5))

        all_options = ["-t", "-q", "-d", "--format"]

        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_bad_options(options)

                if ("-t" in options):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", track1.filename] +
                                         options),
                        2)
                    continue
                else:
                    output_type = audiotools.TYPE_MAP[audiotools.DEFAULT_TYPE]

                self.assertEqual(
                    self.__run_app__(["tracksplit", "--cue",
                                      self.cuesheet.name,
                                      track1.filename] +
                                     options),
                    1)

                if ("-q" in options):
                    self.__check_error__(
                        ERR_UNSUPPORTED_COMPRESSION_MODE %
                        {"quality": "bar",
                         "type": audiotools.DEFAULT_TYPE})
                    continue

                if ("--format" in options):
                    self.__check_error__(
                        ERR_UNKNOWN_FIELD % ("foo"))
                    self.__check_info__(LAB_SUPPORTED_FIELDS)
                    for field in sorted(audiotools.MetaData.FIELDS + \
                                            ("album_track_number", "suffix")):
                        if (field == 'track_number'):
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    self.__check_info__(u"%(basename)s")
                    continue

                if ("-d" in options):
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_type.track_name(
                            "",
                            audiotools.MetaData(track_number=1,
                                                track_total=3)))
                    self.__check_error__(
                        u"[Errno 13] Permission denied: \'%s\'" %
                        (output_path))
                    continue

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir]), 1)

        self.__check_error__(ERR_1_FILE_REQUIRED)

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name, self.unsplit_file2.name]), 1)

        self.__check_error__(ERR_1_FILE_REQUIRED)

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name]), 1)

        self.__check_error__(ERR_TRACKSPLIT_NO_CUESHEET)

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 "--cue", self.cuesheet.name, track2.filename]), 1)

        self.__check_error__(ERR_TRACKSPLIT_OVERLONG_CUESHEET)

        #FIXME? - check for broken cue sheet output?
