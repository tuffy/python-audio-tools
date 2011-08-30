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

from test import (parser, BLANK_PCM_Reader, Combinations,
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
            self.assertEqual(
                unicodedata.normalize(
                    'NFC',
                    getattr(self,
                            stream).readline().decode(audiotools.IO_ENCODING)),
                unicodedata.normalize(
                    'NFC',
                    expected_output) + unicode(os.linesep))
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

        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Album 3</title><artist><name>Artist 3</name></artist><release-event-list><event catalog-number="" date="2011"/></release-event-list><track-list><track><title>Track 3-1</title><duration>5000</duration></track><track><title>Track 3-2</title><duration>6000</duration></track><track><title>Track 3-3</title><duration>7000</duration></track></track-list></release></release-list></metadata>')
        self.xmcd_file.flush()
        self.xmcd_metadata = audiotools.read_metadata_file(self.xmcd_file.name)

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
        populated = []
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
            elif (option == '-x'):
                populated.append(option)
                populated.append(self.xmcd_file.name)
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
        messenger = audiotools.VerboseMessenger("cd2track")

        all_options = ["-t", "-q", "-d", "--format", "-x",
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
                        _(u"\"%(quality)s\" is not a supported " +
                          u"compression mode for type \"%(type)s\"") %
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
                if ("-x" in options):
                    for i in xrange(3):
                        base_metadata.track_name = \
                            self.xmcd_metadata.track_metadata(i + 1).track_name
                        base_metadata.track_number = i + 1
                        base_metadata.album_name = u"Album 3"
                        base_metadata.artist_name = u"Artist 3"
                        output_filenames.append(
                            output_type.track_name(
                                "",
                                base_metadata,
                                output_format))
                else:
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
                        _(u"track %(track_number)2.2d: %(log)s") % \
                            {"track_number": i + 1,
                             "log": str(audiotools.CDTrackLog())})
                    self.__check_info__(
                        _(u"track %(track_number)2.2d -> %(filename)s") % \
                            {"track_number": i + 1,
                             "filename": messenger.filename(
                                os.path.join(output_dir, path))})

                #make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.assertEqual(len(output_tracks), 3)
                self.stream.reset()
                self.assert_(
                    audiotools.pcm_frame_cmp(
                        audiotools.PCMCat(iter([t.to_pcm()
                                                for t in output_tracks])),
                        self.stream) is None)

                #make sure metadata fits our expectations
                for i in xrange(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if (metadata is not None):
                        if ("-x" in options):
                            self.assertEqual(
                                metadata.track_name,
                                self.xmcd_metadata.track_metadata(i + 1).track_name)
                            self.assertEqual(
                                metadata.album_name,
                                self.xmcd_metadata.track_metadata(i + 1).album_name)
                            self.assertEqual(
                                metadata.artist_name,
                                self.xmcd_metadata.track_metadata(i + 1).artist_name)
                        else:
                            self.assertEqual(metadata.track_name, u"")
                            self.assertEqual(metadata.album_name, u"")
                            self.assertEqual(metadata.artist_name, u"")

                        self.assertEqual(metadata.track_number, i + 1)
                        self.assertEqual(metadata.track_total, 3)

                        if ("--album-number" in options):
                            self.assertEqual(metadata.album_number, 8)
                        else:
                            self.assertEqual(metadata.album_number, 0)

                        if ("--album-total" in options):
                            self.assertEqual(metadata.album_total, 9)
                        else:
                            self.assertEqual(metadata.album_total, 0)

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
            elif (option == '-x'):
                populated.append(option)
                populated.append(os.devnull)
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
        filename = audiotools.Messenger("cd2track", None).filename

        all_options = ["-t", "-q", "-d", "--format", "-x",
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

                if (("-o" in options) and
                    ("-d" in options)):
                    self.__check_error__(
                        _(u"-o and -d options are not compatible"))
                    self.__check_info__(
                        _(u"Please specify either -o or -d but not both"))
                    continue

                if (("--format" in options) and ("-o" in options)):
                    self.__queue_warning__(
                        _(u"--format has no effect when used with -o"))

                if ("-q" in options):
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") %
                        {"quality": "bar",
                         "type":audiotools.DEFAULT_TYPE})
                    continue

                if ("-x" in options):
                    self.__check_error__(
                        _(u"Invalid XMCD or MusicBrainz XML file"))
                    continue

                if ("--format" in options):
                    self.__check_error__(
                        _(u"Unknown field \"%s\" in file format") % ("foo"))
                    self.__check_info__(_(u"Supported fields are:"))
                    for field in sorted(audiotools.MetaData.FIELDS + \
                                            ("album_track_number", "suffix")):
                        if (field == 'track_number'):
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    continue

                if ("-d" in options):
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_type.track_name(
                            "",
                            audiotools.MetaData(track_number=1,
                                                track_total=3),
                            audiotools.FILENAME_FORMAT))
                    self.__check_error__(
                        _(u"Unable to write \"%s\"") % \
                            (output_path))
                    continue


class cd2xmcd(UtilTest):
    @UTIL_CD2XMCD
    def setUp(self):
        self.type = audiotools.FlacAudio
        self.quality = "1"

        self.input_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.xmcd_output = os.path.join(self.output_dir, "output.xmcd")

        self.track_lengths = [7939176,
                              4799256,
                              6297480,
                              5383140,
                              5246136,
                              5052684,
                              5013876]

        self.stream = test_streams.Sine16_Stereo(sum(self.track_lengths),
                                                 44100, 8820.0, 0.70,
                                                 4410.0, 0.29, 1.0)

        self.cue_file = os.path.join(self.input_dir, "CDImage.cue")
        self.bin_file = os.path.join(self.input_dir, "CDImage.bin")

        f = open(self.cue_file, "w")
        f.write('FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 02:57:52\n    INDEX 01 03:00:02\n  TRACK 03 AUDIO\n    INDEX 00 04:46:17\n    INDEX 01 04:48:64\n  TRACK 04 AUDIO\n    INDEX 00 07:09:01\n    INDEX 01 07:11:49\n  TRACK 05 AUDIO\n    INDEX 00 09:11:46\n    INDEX 01 09:13:54\n  TRACK 06 AUDIO\n    INDEX 00 11:10:13\n    INDEX 01 11:12:51\n  TRACK 07 AUDIO\n    INDEX 00 13:03:74\n    INDEX 01 13:07:19\n')
        f.close()

        f = open(self.bin_file, "w")
        audiotools.transfer_framelist_data(self.stream, f.write)
        f.close()

    @UTIL_CD2XMCD
    def tearDown(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

    def clean_output_directory(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

    def populate_options(self, options):
        populated = []

        for option in options:
            if ("-x" in options):
                populated.append(option)
                populated.append(self.xmcd_output)
            else:
                populated.append(option)

        return populated

    @UTIL_CD2XMCD
    def test_options(self):
        all_options = ["-x", "--no-musicbrainz", "--no-freedb"]
        for count in xrange(len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options)
                self.clean_output_directory()

                time.sleep(2)
                self.assertEqual(
                    self.__run_app__(["cd2xmcd", "-D",
                                      "-c", self.cue_file] + options), 0)
                if ("-x" in options):
                    sheet = audiotools.read_metadata_file(self.xmcd_output)
                else:
                    temp = tempfile.NamedTemporaryFile()
                    try:
                        temp.write(self.stdout.getvalue())
                        temp.flush()
                        sheet = audiotools.read_metadata_file(temp.name)
                    finally:
                        temp.close()

                #ensure data is what we'd expect
                self.assertEqual(len(sheet), len(self.track_lengths))
                for i in xrange(1, len(self.track_lengths) + 1):
                    metadata = sheet.track_metadata(i)
                    if (("--no-musicbrainz" in options) and
                        ("--no-freedb" in options)):
                        self.assertEqual(metadata.track_name, u"")
                        self.assertEqual(metadata.album_name, u"")
                    else:
                        self.assertNotEqual(metadata.track_name, u"")
                        self.assertNotEqual(metadata.album_name, u"")
                    self.assertEqual(metadata.track_number, i)
                    self.assertEqual(metadata.track_total,
                                     len(self.track_lengths))

    @UTIL_CD2XMCD
    def test_errors(self):
        existing_filename = "/dev/null"

        self.assertEqual(self.__run_app__(["cd2xmcd", "-D",
                                           "-c", self.cue_file,
                                           "-x", existing_filename]), 1)

        self.__check_error__(u"[Errno 17] File exists: '%s'" % \
                                 (self.filename(existing_filename)))


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
            img = Image.new("RGB", (100,100), "#%2.2X%2.2X%2.2X" % (i, i, i))
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
            img = Image.new("RGB", (100,100), "#%2.2X%2.2X%2.2X" %
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
        msg = audiotools.VerboseMessenger("coverdump")

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
                            "prefix":"PREFIX_",
                            "filename":self.filename_types[image.type],
                            "filenum":(i % 2) + 1,
                            "suffix":"png"}
                    else:
                        output_filename = template % {
                            "prefix":"",
                            "filename":self.filename_types[image.type],
                            "filenum":(i % 2) + 1,
                            "suffix":"png"}

                    if ("-d" in options):
                        output_path = os.path.join(self.output_dir,
                                                   output_filename)
                    else:
                        output_path = os.path.join(".", output_filename)

                    self.__check_info__(
                        _(u"%(source)s -> %(destination)s") %
                        {"source":msg.filename(self.track1.filename),
                         "destination":msg.filename(output_path)})
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
                            "prefix":"PREFIX_",
                            "filename":self.filename_types[image.type],
                            "suffix":"png"}
                    else:
                        output_filename = template % {
                            "prefix":"",
                            "filename":self.filename_types[image.type],
                            "suffix":"png"}

                    if ("-d" in options):
                        output_path = os.path.join(self.output_dir,
                                                   output_filename)
                    else:
                        output_path = os.path.join(".", output_filename)

                    self.__check_info__(
                        _(u"%(source)s -> %(destination)s") %
                        {"source":msg.filename(self.track2.filename),
                         "destination":msg.filename(output_path)})
                    output_image = audiotools.Image.new(
                        open(output_path, "rb").read(),
                        u"",
                        i)
                    self.assertEqual(output_image, image)

    @UTIL_COVERDUMP
    def test_errors(self):
        msg = audiotools.VerboseMessenger("coverdump")

        #check no input files
        self.assertEqual(self.__run_app__(
                ["coverdump", "-V", "normal"]), 1)

        self.__check_error__(
            _(u"You must specify exactly 1 supported audio file"))

        #check multiple input files
        self.assertEqual(self.__run_app__(
                ["coverdump", "-V", "normal",
                 self.track1.filename, self.track2.filename]), 1)

        self.__check_error__(
            _(u"You must specify exactly 1 supported audio file"))

        #check unwritable output dir
        old_mode = os.stat(self.output_dir).st_mode
        try:
            os.chmod(self.output_dir, 0)
            self.assertEqual(self.__run_app__(
                    ["coverdump", "-V", "normal", "-d", self.output_dir,
                     self.track1.filename]), 1)
            self.__check_error__(
                _(u"Unable to write \"%s\"") % (msg.filename(
                        os.path.join(self.output_dir,
                                     "front_cover01.png"))))
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
                _(u"[Errno 13] Permission denied: '.'"))

        finally:
            os.chmod(self.cwd_dir, old_mode)


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
        #test with no -A option
        self.assertEqual(self.__run_app__(["dvdainfo"]), 1)
        self.__check_error__(
            _(u"You must specify the DVD-Audio's AUDIO_TS directory with -A"))

        #test with an invalid AUDIO_TS dir
        self.assertEqual(self.__run_app__(["dvdainfo",
                                           "-A", self.invalid_dir1]), 1)
        self.__check_error__(_(u"unable to open AUDIO_TS.IFO"))

        #test with an invalid AUDIO_TS/AUDIO_TS.IFO file
        self.assertEqual(self.__run_app__(["dvdainfo",
                                           "-A", self.invalid_dir2]), 1)
        self.__check_error__(_(u"invalid AUDIO_TS.IFO"))


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
        #test with no -A option
        self.assertEqual(self.__run_app__(["dvda2track"]), 1)
        self.__check_error__(
            _(u"You must specify the DVD-Audio's AUDIO_TS directory with -A"))

        #test with an invalid AUDIO_TS dir
        self.assertEqual(self.__run_app__(["dvda2track",
                                           "-A", self.invalid_dir1]), 1)
        self.__check_error__(_(u"unable to open AUDIO_TS.IFO"))

        #test with an invalid AUDIO_TS/AUDIO_TS.IFO file
        self.assertEqual(self.__run_app__(["dvda2track",
                                           "-A", self.invalid_dir2]), 1)
        self.__check_error__(_(u"invalid AUDIO_TS.IFO"))

        #FIXME
        #It's difficult to test an invalid --title or invalid --xmcd
        #without a valid AUDIO_TS.IFO file,
        #and a set of present IFO files and AOB files.
        #I'll need a way to generate synthetic ones.


class dvda2xmcd(UtilTest):
    @UTIL_DVDA2XMCD
    def setUp(self):
        self.invalid_dir1 = tempfile.mkdtemp()
        self.invalid_dir2 = tempfile.mkdtemp()
        f = open(os.path.join(self.invalid_dir2, "AUDIO_TS.IFO"), "wb")
        f.write(os.urandom(1000))
        f.close()

    @UTIL_DVDA2XMCD
    def tearDown(self):
        os.rmdir(self.invalid_dir1)
        os.unlink(os.path.join(self.invalid_dir2, "AUDIO_TS.IFO"))
        os.rmdir(self.invalid_dir2)

    @UTIL_DVDA2XMCD
    def test_errors(self):
        #test with no -A option
        self.assertEqual(self.__run_app__(["dvda2xmcd"]), 1)
        self.__check_error__(
            _(u"You must specify the DVD-Audio's AUDIO_TS directory with -A"))

        #test with an invalid AUDIO_TS dir
        self.assertEqual(self.__run_app__(["dvda2xmcd",
                                           "-A", self.invalid_dir1]), 1)
        self.__check_error__(_(u"unable to open AUDIO_TS.IFO"))

        #test with an invalid AUDIO_TS/AUDIO_TS.IFO file
        self.assertEqual(self.__run_app__(["dvda2xmcd",
                                           "-A", self.invalid_dir2]), 1)
        self.__check_error__(_(u"invalid AUDIO_TS.IFO"))

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
            if (self.input_format != audiotools.DEFAULT_TYPE):
                break

        #output format shouldn't be the user's default, the input format
        #and should support embedded images and ReplayGain tags
        for self.output_format in [audiotools.FlacAudio,
                                   audiotools.WavPackAudio]:
            if (self.input_format != audiotools.DEFAULT_TYPE):
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
        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Test Album</title><artist><name></name></artist><release-event-list><event catalog-number="" date=""/></release-event-list><track-list><track><title>Test Track</title><duration>6912</duration><artist><name>Test Artist</name></artist></track></track-list></release></release-list></metadata>')
        self.xmcd_file.flush()

        self.xmcd_metadata = audiotools.read_metadata_file(self.xmcd_file.name)

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
        self.xmcd_file.close()

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
            elif (option == '-x'):
                populated.append(option)
                populated.append(self.xmcd_file.name)
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
        messenger = audiotools.Messenger("track2track", None)

        all_options = ["-t", "-q", "-d", "--format", "-o", "-T",
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
                    self.__check_error__(
                        _(u"-o and -d options are not compatible"))
                    self.__check_info__(
                        _(u"Please specify either -o or -d but not both"))
                    continue

                if (("--format" in options) and ("-o" in options)):
                    self.__queue_warning__(
                        _(u"--format has no effect when used with -o"))

                if ('-t' in options):
                    output_class = audiotools.TYPE_MAP[
                        options[options.index('-t') + 1]]
                else:
                    output_class = audiotools.TYPE_MAP[
                        audiotools.DEFAULT_TYPE]

                if (("-q" in options) and
                    (options[options.index("-q") + 1] not in
                     output_class.COMPRESSION_MODES)):
                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 1)
                    self.__check_error__(
                    _(u"\"%(quality)s\" is not a supported " +
                      u"compression mode for type \"%(type)s\"") %
                    {"quality":options[options.index("-q") + 1],
                     "type":output_class.NAME})
                    continue

                if ('--format' in options):
                    output_format = options[options.index('--format') + 1]
                else:
                    output_format = audiotools.FILENAME_FORMAT

                if ('-x' in options):
                    metadata = self.xmcd_metadata[1]
                else:
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
                        _(u"%(source)s -> %(destination)s") %
                        {"source":
                             messenger.filename(self.track1.filename),
                         "destination":
                             messenger.filename(output_path)})

                track2 = audiotools.open(output_path)
                self.assertEqual(track2.NAME, output_class.NAME)
                if (self.track1.lossless() and track2.lossless()):
                    self.assert_(
                        audiotools.pcm_frame_cmp(self.track1.to_pcm(),
                                                 track2.to_pcm()) is None)
                if (track2.get_metadata() is not None):
                    self.assertEqual(track2.get_metadata(), metadata)

                    image = track2.get_metadata().images()[0]
                    if ('-T' in options):
                        self.assertEqual(max(image.width,
                                             image.height),
                                         audiotools.THUMBNAIL_SIZE)
                    else:
                        self.assertEqual(image.width, self.cover.width)
                        self.assertEqual(image.height, self.cover.height)

                if (('--no-replay-gain' in options) and
                    ('--replay-gain' not in options)):
                    self.assert_(track2.replay_gain() is None)
                elif (("-o" not in options) and
                      ('--no-replay-gain' not in options) and
                      (output_class.can_add_replay_gain())):
                    if (output_class.lossless_replay_gain()):
                        self.__check_info__(
                            _(u"Adding ReplayGain metadata.  This may take some time."))
                    else:
                        self.__check_info__(
                            _(u"Applying ReplayGain.  This may take some time."))
                    self.assert_(track2.replay_gain() is not None)

    @UTIL_TRACK2TRACK
    def test_errors(self):
        messenger = audiotools.Messenger("track2track", None)
        filename = messenger.filename

        all_options = ["-t", "-q", "-d", "--format", "-o", "-j",
                       "-T", "--replay-gain", "--no-replay-gain"]
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

                self.assertEqual(
                    self.__run_app__(["track2track"] + options),
                    1)

                if (("-o" in options) and
                    ("-d" in options)):
                    self.__check_error__(
                        _(u"-o and -d options are not compatible"))
                    self.__check_info__(
                        _(u"Please specify either -o or -d but not both"))
                    continue

                if (("--format" in options) and ("-o" in options)):
                    self.__queue_warning__(
                        _(u"--format has no effect when used with -o"))

                if ("-q" in options):
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") %
                        {"quality": "bar",
                         "type":self.output_format.NAME})
                    continue

                if ("-j" in options):
                    self.__check_error__(
                        _(u"You must run at least 1 process at a time"))
                    continue

                if ("-x" in options):
                    self.__check_error__(
                        _(u"Invalid XMCD or MusicBrainz XML file"))
                    continue

                if ("-o" in options):
                    self.__check_error__(
                        _(u"[Errno 20] Not a directory: '%s'") %
                        (self.unwritable_file))
                    continue

                if ("--format" in options):
                    self.__check_error__(
                        _(u"Unknown field \"%s\" in file format") % ("foo"))
                    self.__check_info__(_(u"Supported fields are:"))
                    for field in sorted(audiotools.MetaData.FIELDS + \
                                            ("album_track_number", "suffix")):
                        if (field == 'track_number'):
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    continue

                if ("-d" in options):
                    output_path = os.path.join(
                        self.unwritable_dir,
                        self.output_format.track_name(
                            "",
                            self.track1.get_metadata(),
                            audiotools.FILENAME_FORMAT))
                    self.__check_error__(
                        _(u"[Errno 13] Permission denied: '%s'") % \
                            (output_path))
                    continue

                #the error triggered by a broken file is variable
                #so no need to check its exact value
                self.assert_(len(self.stderr.getvalue()) > 0)

        #check no input files
        self.assertEqual(self.__run_app__(["track2track"]), 1)
        self.__check_error__(
            _(u"You must specify at least 1 supported audio file"))


        self.track2 = self.input_format.from_pcm(
            os.path.join(self.input_dir, "02.%s" % (self.input_format.SUFFIX)),
            BLANK_PCM_Reader(2))

        #check multiple input files and -o
        self.assertEqual(self.__run_app__(["track2track",
                                           "-o", self.output_file.name,
                                           self.track1.filename,
                                           self.track2.filename]), 1)
        self.__check_error__(
            _(u"You may specify only 1 input file for use with -o"))

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
                _(u"Unable to write \"%(target_filename)s\"" +
                  u" with %(channels)d channel input") %
                {"target_filename":filename(os.path.join(self.output_dir,
                                                         "00 - .flac")),
                 "channels":10})

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_count_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                _(u"Unable to write \"%(target_filename)s\"" +
                  u" with %(channels)d channel input") %
                {"target_filename":filename(unsupported_count_file.name),
                 "channels":10})
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
                _(u"Unable to write \"%(target_filename)s\"" +
                  u" with channel assignment \"%(assignment)s\"") %
                {"target_filename":filename(os.path.join(self.output_dir,
                                                         "00 - .flac")),
                 "assignment":audiotools.ChannelMask(0x3F000)})

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_mask_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                _(u"Unable to write \"%(target_filename)s\"" +
                  u" with channel assignment \"%(assignment)s\"") %
                {"target_filename":filename(unsupported_mask_file.name),
                 "assignment":audiotools.ChannelMask(0x3F000)})
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
                _(u"Unable to write \"%(target_filename)s\"" +
                  u" with %(bps)d bits per sample") %
                {"target_filename":filename(os.path.join(self.output_dir,
                                                         "00 - .shn")),
                 "bps":24})

            self.assertEqual(self.__run_app__(["track2track",
                                               "-o",
                                               unsupported_bps_file.name,
                                               supported_track.filename]), 1)
            self.__check_error__(
                _(u"Unable to write \"%(target_filename)s\"" +
                  u" with %(bps)d bits per sample") %
                {"target_filename":filename(unsupported_bps_file.name),
                 "bps":24})
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


class track2xmcd(UtilTest):
    @UTIL_TRACK2XMCD
    def setUp(self):
        self.type = audiotools.FlacAudio
        self.track_lengths = [7939176,
                              4799256,
                              6297480,
                              5383140,
                              5246136,
                              5052684,
                              5013876]
        self.input_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.xmcd_output = os.path.join(self.output_dir, "output.xmcd")
        self.cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet.write('FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 02:57:52\n    INDEX 01 03:00:02\n  TRACK 03 AUDIO\n    INDEX 00 04:46:17\n    INDEX 01 04:48:64\n  TRACK 04 AUDIO\n    INDEX 00 07:09:01\n    INDEX 01 07:11:49\n  TRACK 05 AUDIO\n    INDEX 00 09:11:46\n    INDEX 01 09:13:54\n  TRACK 06 AUDIO\n    INDEX 00 11:10:13\n    INDEX 01 11:12:51\n  TRACK 07 AUDIO\n    INDEX 00 13:03:74\n    INDEX 01 13:07:19\n')
        self.cuesheet.flush()

    @UTIL_TRACK2XMCD
    def tearDown(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))
        os.rmdir(self.output_dir)

        self.cuesheet.close()

    def clean_output_directory(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

    def populate_options(self, options):
        populated = []
        for option in options:
            if (option == "-x"):
                populated.append(option)
                populated.append(self.xmcd_output)
            elif (option == "--cue"):
                populated.append(option)
                populated.append(self.cuesheet.name)
            else:
                populated.append(option)
        return populated

    @UTIL_TRACK2XMCD
    def test_options_separate_tracks(self):
        #generate a bunch of dummy tracks that have MusicBrainz/FreeDB matches
        tracks = [self.type.from_pcm(
                os.path.join(self.input_dir,
                             "%2.2d.%s" % (i + 1, self.type.SUFFIX)),
                EXACT_BLANK_PCM_Reader(pcm_frames))
                  for (i, pcm_frames) in enumerate(self.track_lengths)]
        for (i, track) in enumerate(tracks):
            track.set_metadata(audiotools.MetaData(
                    track_name=u"Track %d" % (i + 1),
                    album_name=u"Album",
                    track_number=i + 1,
                    track_total=len(self.track_lengths)))

        all_options = ["-x", "-m", "--cue", "--no-musicbrainz", "--no-freedb"]
        for count in xrange(len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options)
                self.clean_output_directory()

                self.assert_(not os.path.isfile(self.xmcd_output))

                #individual tracks ignores the --cue option
                if ("-m" in options):
                    self.assertEqual(
                        self.__run_app__(["track2xmcd", "-D", "-V", "normal"] +
                                         options +
                                         [t.filename for t in tracks]), 0)
                    if ("-x" in options):
                        sheet = audiotools.read_metadata_file(self.xmcd_output)
                    else:
                        if (("--no-musicbrainz" in options) and
                            ("--no-freedb" in options)):
                            sheet = audiotools.XMCD.from_string(self.stdout.getvalue())
                        elif ("--no-musicbrainz" in options):
                            sheet = audiotools.XMCD.from_string(self.stdout.getvalue())
                        elif ("--no-freedb" in options):
                            sheet = audiotools.MusicBrainzReleaseXML.from_string(self.stdout.getvalue())
                        else:
                            sheet = audiotools.MusicBrainzReleaseXML.from_string(self.stdout.getvalue())

                    #ensure data is pulled from the tracks themselves
                    self.assertEqual(len(sheet), len(self.track_lengths))
                    for i in xrange(1, len(self.track_lengths) + 1):
                        metadata = sheet.track_metadata(i)
                        self.assertEqual(metadata.track_name,
                                         u"Track %d" % (i))
                        self.assertEqual(metadata.album_name,
                                         u"Album")
                        self.assertEqual(metadata.track_number,
                                         i)
                        self.assertEqual(metadata.track_total,
                                         len(self.track_lengths))
                    continue

                time.sleep(2)
                self.assertEqual(
                    self.__run_app__(["track2xmcd", "-D", "-V", "normal"] +
                                     options +
                                     [t.filename for t in tracks]), 0)
                if ("-x" in options):
                    sheet = audiotools.read_metadata_file(self.xmcd_output)
                else:
                    temp = tempfile.NamedTemporaryFile()
                    try:
                        temp.write(self.stdout.getvalue())
                        temp.flush()
                        sheet = audiotools.read_metadata_file(temp.name)
                    finally:
                        temp.close()

                #ensure data is not pulled from the tracks
                self.assertEqual(len(sheet), len(self.track_lengths))
                for i in xrange(1, len(self.track_lengths) + 1):
                    metadata = sheet.track_metadata(i)
                    self.assertNotEqual(metadata.track_name,
                                     u"Track %d" % (i))
                    self.assertNotEqual(metadata.album_name,
                                     u"Album")
                    self.assertEqual(metadata.track_number,
                                     i)
                    self.assertEqual(metadata.track_total,
                                     len(self.track_lengths))


    @UTIL_TRACK2XMCD
    def test_options_single_file(self):
        #generate a single dummy track that has MusicBrainz/FreeDB matches

        track = self.type.from_pcm(
            os.path.join(self.input_dir, "track." + self.type.SUFFIX),
            EXACT_BLANK_PCM_Reader(sum(self.track_lengths)))
        track.set_metadata(audiotools.MetaData(track_name=u"Track",
                                               album_name=u"Album",
                                               track_number=1,
                                               track_total=1))

        all_options = ["-x", "-m", "--cue", "--no-musicbrainz", "--no-freedb"]
        for count in xrange(len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options)
                self.clean_output_directory()

                self.assert_(not os.path.isfile(self.xmcd_output))
                if ("-m" in options):
                    self.assertEqual(
                        self.__run_app__(["track2xmcd", "-D", "-V", "normal"] +
                                         options +
                                         [track.filename]), 0)
                    if ("-x" in options):
                        sheet = audiotools.read_metadata_file(self.xmcd_output)
                    else:
                        if (("--no-musicbrainz" in options) and
                            ("--no-freedb" in options)):
                            sheet = audiotools.XMCD.from_string(self.stdout.getvalue())
                        elif ("--no-musicbrainz" in options):
                            sheet = audiotools.XMCD.from_string(self.stdout.getvalue())
                        elif ("--no-freedb" in options):
                            sheet = audiotools.MusicBrainzReleaseXML.from_string(self.stdout.getvalue())
                        else:
                            sheet = audiotools.MusicBrainzReleaseXML.from_string(self.stdout.getvalue())

                    if ("--cue" in options):
                        self.assertEqual(len(sheet), len(self.track_lengths))
                        for i in xrange(1, len(self.track_lengths) + 1):
                            metadata = sheet.track_metadata(i)
                            self.assertEqual(metadata.track_name,
                                             u"Track")
                            self.assertEqual(metadata.album_name,
                                             u"Album")
                            self.assertEqual(metadata.track_number,
                                             i)
                            self.assertEqual(metadata.track_total,
                                             len(self.track_lengths))
                    else:
                        self.assertEqual(len(sheet), 1)
                        metadata = sheet.track_metadata(1)
                        self.assertEqual(metadata.track_name,
                                         u"Track")
                        self.assertEqual(metadata.album_name,
                                         u"Album")
                        self.assertEqual(metadata.track_number,
                                         1)
                        self.assertEqual(metadata.track_total,
                                         1)
                    continue

                time.sleep(2)
                self.assertEqual(
                    self.__run_app__(["track2xmcd", "-D", "-V", "normal"] +
                                     options +
                                     [track.filename]), 0)
                if ("-x" in options):
                    sheet = audiotools.read_metadata_file(self.xmcd_output)
                else:
                    temp = tempfile.NamedTemporaryFile()
                    try:
                        temp.write(self.stdout.getvalue())
                        temp.flush()
                        sheet = audiotools.read_metadata_file(temp.name)
                    finally:
                        temp.close()

                #ensure data is not pulled from tracks if --cue indicated
                if ("--cue" in options):
                    self.assertEqual(len(sheet), len(self.track_lengths))
                    for i in xrange(1, len(self.track_lengths) + 1):
                        metadata = sheet.track_metadata(i)
                        self.assertNotEqual(metadata.track_name,
                                            u"Track")
                        self.assertNotEqual(metadata.album_name,
                                            u"Album")
                        self.assertEqual(metadata.track_number,
                                         i)
                        self.assertEqual(metadata.track_total,
                                         len(self.track_lengths))
                else:
                    #otherwise, ensure data is built from single dummy track
                    self.assertEqual(len(sheet), 1)
                    metadata = sheet.track_metadata(1)
                    self.assertNotEqual(metadata.track_name,
                                        u"Track")
                    self.assertNotEqual(metadata.album_name,
                                        u"Album")
                    self.assertEqual(metadata.track_number,
                                     1)
                    self.assertEqual(metadata.track_total,
                                     1)

    @UTIL_TRACK2XMCD
    def test_options_single_file_embedded_cuesheet(self):
        #generate a single dummy track that has MusicBrainz/FreeDB matches

        track = self.type.from_pcm(
            os.path.join(self.input_dir, "track." + self.type.SUFFIX),
            EXACT_BLANK_PCM_Reader(sum(self.track_lengths)))
        track.set_metadata(audiotools.MetaData(track_name=u"Track",
                                               album_name=u"Album",
                                               track_number=1,
                                               track_total=1))

        #add cuesheet to dummy track
        track.set_cuesheet(audiotools.read_sheet(self.cuesheet.name))

        all_options = ["-x", "-m", "--cue", "--no-musicbrainz", "--no-freedb"]
        for count in xrange(len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options)
                self.clean_output_directory()

                self.assert_(not os.path.isfile(self.xmcd_output))
                if ("-m" in options):
                    self.assertEqual(
                        self.__run_app__(["track2xmcd", "-D", "-V", "normal"] +
                                         options +
                                         [track.filename]), 0)
                    if ("-x" in options):
                        sheet = audiotools.read_metadata_file(self.xmcd_output)
                    else:
                        if (("--no-musicbrainz" in options) and
                            ("--no-freedb" in options)):
                            sheet = audiotools.XMCD.from_string(self.stdout.getvalue())
                        elif ("--no-musicbrainz" in options):
                            sheet = audiotools.XMCD.from_string(self.stdout.getvalue())
                        elif ("--no-freedb" in options):
                            sheet = audiotools.MusicBrainzReleaseXML.from_string(self.stdout.getvalue())
                        else:
                            sheet = audiotools.MusicBrainzReleaseXML.from_string(self.stdout.getvalue())

                    self.assertEqual(len(sheet), len(self.track_lengths))
                    for i in xrange(1, len(self.track_lengths) + 1):
                        metadata = sheet.track_metadata(i)
                        self.assertEqual(metadata.track_name,
                                         u"Track")
                        self.assertEqual(metadata.album_name,
                                         u"Album")
                        self.assertEqual(metadata.track_number,
                                         i)
                        self.assertEqual(metadata.track_total,
                                         len(self.track_lengths))
                    continue

                time.sleep(2)
                self.assertEqual(
                    self.__run_app__(["track2xmcd", "-D", "-V", "normal"] +
                                     options +
                                     [track.filename]), 0)
                if ("-x" in options):
                    sheet = audiotools.read_metadata_file(self.xmcd_output)
                else:
                    temp = tempfile.NamedTemporaryFile()
                    try:
                        temp.write(self.stdout.getvalue())
                        temp.flush()
                        sheet = audiotools.read_metadata_file(temp.name)
                    finally:
                        temp.close()

                #ensure data is not pulled from track
                #whether --cue is indicated or not
                self.assertEqual(len(sheet), len(self.track_lengths))
                for i in xrange(1, len(self.track_lengths) + 1):
                    metadata = sheet.track_metadata(i)
                    self.assertNotEqual(metadata.track_name,
                                        u"Track")
                    self.assertNotEqual(metadata.album_name,
                                        u"Album")
                    self.assertEqual(metadata.track_number,
                                     i)
                    self.assertEqual(metadata.track_total,
                                     len(self.track_lengths))


    @UTIL_TRACK2XMCD
    def test_errors(self):
        self.assertEqual(self.__run_app__(["track2xmcd"]), 1)
        self.__check_error__(
            _(u"You must specify at least 1 supported audio file"))

        track1 = self.type.from_pcm(os.path.join(self.input_dir,
                                                 "01." + self.type.SUFFIX),
                                    BLANK_PCM_Reader(1))

        existing_filename = "/dev/null"

        self.assertEqual(self.__run_app__(["track2xmcd", "-x",
                                           existing_filename,
                                           track1.filename]),
                         1)

        self.__check_error__(u"[Errno 17] File exists: '%s'" % \
                                 (self.filename(existing_filename)))

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
        messenger = audiotools.Messenger("trackcat", None)

        #first, check the error conditions
        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac"]), 1)
        self.__check_error__(
            _(u"You must specify at least 1 supported audio file"))

        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename,
                              self.track4.filename]), 1)
        self.__check_error__(
            _(u"All audio files must have the same bits per sample"))

        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename,
                              self.track5.filename]), 1)
        self.__check_error__(
            _(u"All audio files must have the same channel count"))

        self.assertEqual(
            self.__run_app__(["trackcat", "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename,
                              self.track6.filename]), 1)
        self.__check_error__(
            _(u"All audio files must have the same sample rate"))

        self.assertEqual(
            self.__run_app__(["trackcat", "--cue", "/dev/null/foo.cue",
                              "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename]), 1)
        self.__check_error__(_(u"Unable to read cuesheet"))

        self.assertEqual(
            self.__run_app__(["trackcat", "--cue", self.invalid_cuesheet.name,
                              "-o", "fail.flac",
                              self.track1.filename,
                              self.track2.filename,
                              self.track3.filename]), 1)
        self.__check_error__(_(u"Missing tag at line 1"))

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

                    self.__check_error__(_(u"You must specify an output file"))
                    continue


                if ("-t" in options):
                    output_format = audiotools.TYPE_MAP[type]
                else:
                    try:
                        output_format = audiotools.filename_to_type(outfile)
                    except audiotools.UnknownAudioType:
                        self.assertEqual(self.__run_app__(["trackcat"] +
                                                          options), 1)

                        self.__check_error__(_(u"Unsupported audio type \"\""))
                        continue

                if (("-q" in options) and
                    (quality not in output_format.COMPRESSION_MODES)):
                    self.assertEqual(self.__run_app__(["trackcat"] + options),
                                     1)
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported " +
                          u"compression mode for type \"%(type)s\"") %
                        {"quality": quality,
                         "type": output_format.NAME.decode('ascii')})
                    continue

                if (outfile.startswith("/dev/")):
                    self.assertEqual(self.__run_app__(["trackcat"] + options),
                                     1)
                    self.__check_error__(
                        _(u"%(filename)s: [Errno 20] Not a directory: '%(filename)s'") %
                        {"filename":messenger.filename(outfile)})
                    continue

                #check that no PCM data is lost
                self.assertEqual(
                    self.__run_app__(["trackcat"] + options), 0)
                new_track = audiotools.open(outfile)
                self.assertEqual(new_track.NAME, output_format.NAME)
                self.assertEqual(new_track.total_frames(), 793800)
                self.assert_(audiotools.pcm_frame_cmp(
                        new_track.to_pcm(),
                        audiotools.PCMCat(iter([track.to_pcm() for track in
                                                [self.track1,
                                                 self.track2,
                                                 self.track3]]))) is None)

                #check that metadata is merged properly
                metadata = new_track.get_metadata()
                if (metadata is not None):
                    self.assertEqual(metadata.track_name, u"")
                    self.assertEqual(metadata.album_name, u"Album")
                    self.assertEqual(metadata.artist_name, u"Artist")
                    self.assertEqual(metadata.track_number, 0)
                    self.assertEqual(metadata.track_total, 3)

                #check that the cuesheet is embedded properly
                if (("--cue" in options) and
                    (output_format is audiotools.FlacAudio)):
                    cuesheet = new_track.get_cuesheet()
                    self.assert_(cuesheet is not None)
                    self.assertEqual(cuesheet.ISRCs(),
                                     {1: 'JPPI00652340',
                                      2: 'JPPI00652349',
                                      3: 'JPPI00652341'})
                    self.assertEqual(list(cuesheet.indexes()),
                                     [(0,), (225, 375), (675, 825)])
                    self.assertEqual(cuesheet.pcm_lengths(793800),
                                     [220500, 264600, 308700])


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
        msg = audiotools.VerboseMessenger("trackcmp")

        #check matching file against maching file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_file2.name]),
            0)

        #check matching file against mismatching file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.mismatch_file.name]),
            1)
        self.__check_info__(
            _(u"%(path1)s <> %(path2)s : %(result)s") % {
                "path1":msg.filename(self.match_file1.name),
                "path2":msg.filename(self.mismatch_file.name),
                "result":_(u"differ at PCM frame %(frame_number)d") %
                {"frame_number": 1}})
        #(ANSI output won't be generated because stdout isn't a TTY)

        #check matching file against missing file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, "/dev/null/foo"]),
            1)
        self.__check_error__(
            _(u"%(path1)s <> %(path2)s : %(result)s") % {
                "path1":msg.filename(self.match_file1.name),
                "path2":msg.filename("/dev/null/foo"),
                "result":_(u"must be either files or directories")})

        #check matching file against broken file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.broken_file.name]),
            1)
        self.__check_error__(_(u"EOF reading frame"))

        #check file against directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_file1.name, self.match_dir1]),
            1)
        self.__check_error__(
            _(u"%(path1)s <> %(path2)s : %(result)s") % {
                "path1":msg.filename(self.match_file1.name),
                "path2":msg.filename(self.match_dir1),
                "result":_(u"must be either files or directories")})

        #check directory against file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal",
                              self.match_dir1, self.match_file1.name]),
            1)
        self.__check_error__(
            _(u"%(path1)s <> %(path2)s : %(result)s") % {
                "path1":msg.filename(self.match_dir1),
                "path2":msg.filename(self.match_file1.name),
                "result":_(u"must be either files or directories")})

        #check matching directory against matching directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.match_dir2]),
            0)
        for i in xrange(1, 4):
            self.__check_info__(
                _(u"%(path1)s <> %(path2)s : %(result)s") % {
                    "path1":msg.filename(
                        os.path.join(self.match_dir1,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "path2":msg.filename(
                        os.path.join(self.match_dir2,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "result":_(u"OK")})

        #check matching directory against mismatching directory
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir1]),
            1)
        for i in xrange(1, 4):
            self.__check_info__(
                _(u"%(path1)s <> %(path2)s : %(result)s") % {
                    "path1":msg.filename(
                        os.path.join(self.match_dir1,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "path2":msg.filename(
                        os.path.join(self.mismatch_dir1,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "result":_(u"differ at PCM frame %(frame_number)d" %
                               {"frame_number":1})})

        #check matching directory against directory missing file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir2]),
            1)
        self.__check_info__(
            _(u"%(path)s : %(result)s") % {
                "path":os.path.join(self.mismatch_dir2,
                                    "track %2.2d" % (3)),
                "result":_(u"missing")})
        for i in xrange(1, 2):
            self.__check_info__(
                _(u"%(path1)s <> %(path2)s : %(result)s") % {
                    "path1":msg.filename(
                        os.path.join(self.match_dir1,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "path2":msg.filename(
                        os.path.join(self.mismatch_dir2,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "result":_(u"OK")})


        #check matching directory against directory with extra file
        self.assertEqual(
            self.__run_app__(["trackcmp", "-V", "normal", "-j", "1",
                              self.match_dir1, self.mismatch_dir3]),
            1)
        self.__check_info__(
            _(u"%(path)s : %(result)s") % {
                "path":os.path.join(self.match_dir1,
                                    "track %2.2d" % (4)),
                "result":_(u"missing")})
        for i in xrange(1, 3):
            self.__check_info__(
                _(u"%(path1)s <> %(path2)s : %(result)s") % {
                    "path1":msg.filename(
                        os.path.join(self.match_dir1,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "path2":msg.filename(
                        os.path.join(self.mismatch_dir3,
                                     "%2.2d.%s" % (i, self.type.SUFFIX))),
                    "result":_(u"OK")})


class trackinfo(UtilTest):
    @UTIL_TRACKINFO
    def setUp(self):
        pass

    @UTIL_TRACKINFO
    def tearDown(self):
        pass

    @UTIL_TRACKINFO
    def test_trackinfo(self):
        pass #FIXME - try all the options


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

        track1 = audiotools.open("1s.flac")
        track2 = audiotools.open("1m.flac")
        track3 = audiotools.open("1h.flac")
        self.assertEqual(track1.seconds_length(), 1)
        self.assertEqual(track2.seconds_length(), 60)
        self.assertEqual(track3.seconds_length(), 60 * 60)
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac"]), 0)
        self.__check_output__(u"0:00:01")
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1s.flac"]), 0)
        self.__check_output__(u"0:00:02")
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac"]), 0)
        self.__check_output__(u"0:01:01")
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1m.flac"]), 0)
        self.__check_output__(u"0:02:01")
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1h.flac"]), 0)
        self.__check_output__(u"1:01:01")
        self.assertEqual(self.__run_app__(["tracklength", "1s.flac",
                                           "1m.flac", "1h.flac",
                                           "1h.flac"]), 0)
        self.__check_output__(u"2:01:01")

        tempdir = tempfile.mkdtemp()
        try:
            shutil.copy(track1.filename, tempdir)
            shutil.copy(track2.filename, tempdir)
            shutil.copy(track3.filename, tempdir)
            self.assertEqual(self.__run_app__(["tracklength", tempdir]), 0)
            self.__check_output__(u"1:01:01")
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir, f))
            os.rmdir(tempdir)


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
                {"TITLE": [u"Track Name  "],
                 "TRACKNUMBER": [u"02"],
                 "DISCNUMBER": [u"003"],
                 "ARTIST": [u"  Some Artist"],
                 "PERFORMER": [u"Some Artist"],
                 "CATALOG": [u""],
                 "YEAR": [u"  "],
                 "COMMENT": [u"  Some Comment  "]})

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
                    metadata = metadata.vorbis_comment
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
                    metadata = metadata.vorbis_comment
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

            self.assertEqual(self.__run_app__(["trackinfo", tempflac.name]), 0)
            self.__check_error__(_(u"ID3v2 tag found at start of FLAC file.  Please remove with tracklint(1)"))

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

            self.assertEqual(self.__run_app__(["trackinfo", tempflac.name]), 0)
            self.__check_error__(_(u"STREAMINFO not first metadata block.  Please fix with tracklint(1)"))

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
            f = open("flac-nonmd5.flac","rb")
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
                [audiotools.ApeTagItem(0, False, "Title", "Track Name  "),
                 audiotools.ApeTagItem(0, False, "Track", "02"),
                 audiotools.ApeTagItem(0, False, "Artist", "  Some Artist"),
                 audiotools.ApeTagItem(0, False, "Performer", "Some Artist"),
                 audiotools.ApeTagItem(0, False, "Catalog", ""),
                 audiotools.ApeTagItem(0, False, "Year", "  "),
                 audiotools.ApeTagItem(0, False, "Comment", "  Some Comment  ")])

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

            track.set_metadata(bad_id3v2)
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
                [audiotools.ID3v22TextFrame.from_unicode(
                        "TT2", u"Track Name  "),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "TRK", u"02"),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "TPA", u"003"),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "TP1", u"  Some Artist\u0000"),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "TP2", u"Some Artist"),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "TRC", u""),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "TYE", u""),
                 audiotools.ID3v22TextFrame.from_unicode(
                        "COM", u"  Some Comment  ")]))

        #ID3v2.2 doesn't store most image fields internally
        #so there's little point in testing them for inaccuracies

    @UTIL_TRACKLINT
    def test_id3v23(self):
        self.__id3_text__(
            audiotools.ID3v23Comment(
                [audiotools.ID3v23TextFrame.from_unicode(
                        "TIT2", u"Track Name  "),
                 audiotools.ID3v23TextFrame.from_unicode(
                        "TRCK", u"02"),
                 audiotools.ID3v23TextFrame.from_unicode(
                        "TPOS", u"003"),
                 audiotools.ID3v23TextFrame.from_unicode(
                        "TPE1", u"  Some Artist\u0000"),
                 audiotools.ID3v23TextFrame.from_unicode(
                        "TPE2", u"Some Artist"),
                 audiotools.ID3v23TextFrame.from_unicode(
                        "TYER", u""),
                 audiotools.ID3v23TextFrame.from_unicode(
                        "TCOP", u""),
                 audiotools.ID3v23TextFrame.from_unicode(
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
                [audiotools.ID3v24TextFrame.from_unicode(
                        "TIT2", u"Track Name  "),
                 audiotools.ID3v24TextFrame.from_unicode(
                        "TRCK", u"02"),
                 audiotools.ID3v24TextFrame.from_unicode(
                        "TPOS", u"003"),
                 audiotools.ID3v24TextFrame.from_unicode(
                        "TPE1", u"  Some Artist\u0000"),
                 audiotools.ID3v24TextFrame.from_unicode(
                        "TPE2", u"Some Artist"),
                 audiotools.ID3v24TextFrame.from_unicode(
                        "TYER", u""),
                 audiotools.ID3v24TextFrame.from_unicode(
                        "TCOP", u""),
                 audiotools.ID3v24TextFrame.from_unicode(
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
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename": self.filename(track.filename),
                            "message": _(u"Stripped whitespace from track_name field")})
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename": self.filename(track.filename),
                            "message": _(u"Stripped whitespace from track_name field")})
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))

                #no undo DB, unwritable file
                self.assertEqual(self.__run_app__(
                        ["tracklint", "--fix", track.filename]), 1)
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename": self.filename(track.filename),
                            "message": _(u"Stripped whitespace from track_name field")})
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename": self.filename(track.filename),
                            "message": _(u"Stripped whitespace from track_name field")})
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))
        finally:
            os.chmod(track_file.name, track_file_stat)
            track_file.close()
            for p in [os.path.join(undo_db_dir, f) for f in
                      os.listdir(undo_db_dir)]:
                os.unlink(p)
            os.rmdir(undo_db_dir)

    @UTIL_TRACKLINT
    def test_m4a(self):
        bad_m4a = audiotools.M4AMetaData([])
        bad_m4a['\xa9nam'] = audiotools.M4AMetaData.text_atom(
            '\xa9nam', u"Track Name  ")
        bad_m4a['\xa9ART'] = audiotools.M4AMetaData.text_atom(
            '\xa9ART', u"  Some Artist")
        bad_m4a['aART'] = audiotools.M4AMetaData.text_atom(
            'aART', u"Some Artist")
        bad_m4a['cprt'] = audiotools.M4AMetaData.text_atom(
            'cprt', u"")
        bad_m4a['\xa9day'] = audiotools.M4AMetaData.text_atom(
            '\xa9day', u"  ")
        bad_m4a['\xa9cmt'] = audiotools.M4AMetaData.text_atom(
            '\xa9cmt', u"  Some Comment  ")
        bad_m4a['trkn'] = audiotools.M4AMetaData.trkn_atom(2, 0)
        bad_m4a['disk'] = audiotools.M4AMetaData.disk_atom(3, 0)

        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            album_number=3,
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

                track.set_metadata(bad_m4a)
                metadata = track.get_metadata()
                self.assertEqual(metadata, bad_m4a)
                for (key, value) in metadata.items():
                    self.assertEqual(value, bad_m4a[key])

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
                for (key, value) in metadata.items():
                    self.assertEqual(value, bad_m4a[key])
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
                    track_number=1)
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
                    track_number=1)
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
    def test_errors1(self):
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

                #general-purpose errors
                self.assertEqual(self.__run_app__(
                        ["tracklint", "--undo", track.filename]), 1)
                self.__check_error__(_(u"Cannot perform undo without undo db"))

                self.assertEqual(self.__run_app__(
                        ["tracklint", "--fix", "--db", "/dev/null/foo.db",
                         track.filename]), 1)
                self.__check_error__(_(u"Unable to open \"%s\"") % \
                                         (self.filename("/dev/null/foo.db")))

                self.assertEqual(self.__run_app__(
                        ["tracklint", "--undo", "--db", "/dev/null/foo.db",
                         track.filename]), 1)
                self.__check_error__(_(u"Unable to open \"%s\"") % \
                                         (self.filename("/dev/null/foo.db")))

                if (track.get_metadata() is not None):
                    #unwritable undo DB, writable file
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(_(u"Unable to open \"%s\"") %
                                         (self.filename("/dev/null/undo.db")))

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--undo", "--db",
                             "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(_(u"Unable to open \"%s\"") %
                                         (self.filename("/dev/null/undo.db")))

                    #unwritable undo DB, unwritable file
                    os.chmod(track.filename, track_file_stat & 0x7555)

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(_(u"Unable to open \"%s\"") %
                                         (self.filename("/dev/null/undo.db")))

                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--undo", "--db",
                             "/dev/null/undo.db",
                             track.filename]), 1)
                    self.__check_error__(_(u"Unable to open \"%s\"") %
                                         (self.filename("/dev/null/undo.db")))

                    #restore from DB to unwritable file
                    os.chmod(track.filename, track_file_stat)
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", "--db", undo_db,
                             track.filename]), 0)
                    os.chmod(track.filename, track_file_stat & 0x7555)
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--undo", "--db", undo_db,
                             track.filename]), 1)
                    self.__check_error__(_(u"Unable to write \"%s\"") %
                                         (self.filename(track.filename)))

            finally:
                os.chmod(track_file.name, track_file_stat)
                track_file.close()
                for p in [os.path.join(undo_db_dir, f) for f in
                          os.listdir(undo_db_dir)]:
                    os.unlink(p)
                os.rmdir(undo_db_dir)

    @UTIL_TRACKLINT
    def test_errors2(self):
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
                    self.__check_info__(
                        _(u"* %(filename)s: %(message)s") %
                        {"filename": self.filename(track.filename),
                         "message": _(u"Stripped whitespace from track_name field")})
                    #MP3 and MP2 have track name stripped twice
                    #because of the ID3 comment pair
                    if ((audio_class == audiotools.MP3Audio) or
                        (audio_class == audiotools.MP2Audio)):
                        self.__check_info__(
                            _(u"* %(filename)s: %(message)s") %
                            {"filename": self.filename(track.filename),
                             "message": _(u"Stripped whitespace from track_name field")})
                    self.__check_error__(_(u"Unable to write \"%s\"") %
                                         (self.filename(track.filename)))

                    #no undo DB, unwritable file
                    self.assertEqual(self.__run_app__(
                            ["tracklint", "--fix", track.filename]), 1)
                    self.__check_info__(
                        _(u"* %(filename)s: %(message)s") %
                        {"filename": self.filename(track.filename),
                         "message": _(u"Stripped whitespace from track_name field")})

                    #MP3 and MP2 have track name stripped twice
                    #because of the ID3 comment pair
                    if ((audio_class == audiotools.MP3Audio) or
                        (audio_class == audiotools.MP2Audio)):
                        self.__check_info__(
                            _(u"* %(filename)s: %(message)s") %
                            {"filename": self.filename(track.filename),
                             "message": _(u"Stripped whitespace from track_name field")})
                    self.__check_error__(_(u"Unable to write \"%s\"") %
                                         (self.filename(track.filename)))
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

        self.xmcd = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd.write('<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Album 2</title><artist><name></name></artist><release-event-list><event catalog-number="" date=""/></release-event-list><track-list><track><title>Name 2</title><duration>6912</duration><artist><name>Artist 2</name></artist></track></track-list></release></release-list></metadata>')
        self.xmcd.flush()

        self.cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cuesheet.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 03:40:72\r\n    INDEX 01 03:42:27\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 07:22:45\r\n    INDEX 01 07:24:37\r\n')
        self.cuesheet.flush()

        self.comment_file = tempfile.NamedTemporaryFile(suffix=".txt")
        self.comment_file.write("Comment File")
        self.comment_file.flush()

        self.front_cover = tempfile.NamedTemporaryFile(suffix=".png")
        self.front_cover.write(TEST_COVER4)
        self.front_cover.flush()

        self.back_cover = tempfile.NamedTemporaryFile(suffix=".png")
        self.back_cover.write(TEST_COVER2)
        self.back_cover.flush()

        self.front_cover_image = audiotools.Image.new(
            TEST_COVER4, u"", 0)
        self.back_cover_image = audiotools.Image.new(
            TEST_COVER2, u"", 1)

        self.thumbnailed_front_cover_image = self.front_cover_image.thumbnail(
            audiotools.THUMBNAIL_SIZE,
            audiotools.THUMBNAIL_SIZE,
            audiotools.THUMBNAIL_FORMAT)

        self.thumbnailed_back_cover_image = self.back_cover_image.thumbnail(
            audiotools.THUMBNAIL_SIZE,
            audiotools.THUMBNAIL_SIZE,
            audiotools.THUMBNAIL_FORMAT)

    @UTIL_TRACKTAG
    def tearDown(self):
        self.track_file.close()
        self.xmcd.close()
        self.cuesheet.close()
        self.comment_file.close()
        self.front_cover.close()
        self.back_cover.close()

    def populate_options(self, options):
        populated = []

        for option in sorted(options):
            if (option == '-x'):
                populated.append(option)
                populated.append(self.xmcd.name)
            elif (option == '--cue'):
                populated.append(option)
                populated.append(self.cuesheet.name)
            elif (option == '--name'):
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
            elif (option == '--front-cover'):
                populated.append(option)
                populated.append(self.front_cover.name)
            elif (option == '--back-cover'):
                populated.append(option)
                populated.append(self.back_cover.name)
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKTAG
    def test_options(self):
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
        most_options = ['-r', '-x', '--cue',
                        '--name', '--number', '--track-total',
                        '--album-number', '--comment', '--comment-file',
                        '--remove-images', '--front-cover', '--back-cover',
                        '-T']

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

                print options

                track = audiotools.open(self.track_file.name)
                track.verify()
                metadata = track.get_metadata()

                if ("--name" in options):
                    self.assertEqual(metadata.track_name, u"Name 3")
                elif (("-x" in options) and ("--number" not in options)):
                    self.assertEqual(metadata.track_name, u"Name 2")
                elif ("-r" in options):
                    self.assertEqual(metadata.track_name, u"")
                else:
                    self.assertEqual(metadata.track_name, u"Name 1")

                if ("--artist" in options):
                    self.assertEqual(metadata.artist_name, u"Artist 3")
                elif (("-x" in options) and ("--number" not in options)):
                    self.assertEqual(metadata.artist_name, u"Artist 2")
                elif ("-r" in options):
                    self.assertEqual(metadata.artist_name, u"")
                else:
                    self.assertEqual(metadata.artist_name, u"Artist 1")

                if ("--album" in options):
                    self.assertEqual(metadata.album_name, u"Album 3")
                elif (("-x" in options) and ("--number" not in options)):
                    self.assertEqual(metadata.album_name, u"Album 2")
                elif ("-r" in options):
                    self.assertEqual(metadata.album_name, u"")
                else:
                    self.assertEqual(metadata.album_name, u"Album 1")

                if ("--number" in options):
                    self.assertEqual(metadata.track_number, 5)
                elif ("-x" in options):
                    self.assertEqual(metadata.track_number, 1)
                elif ("-r" in options):
                    self.assertEqual(metadata.track_number, 0)
                else:
                    self.assertEqual(metadata.track_number, 1)

                if ("--track-total" in options):
                    self.assertEqual(metadata.track_total, 6)
                elif (("-x" in options) and ("--number" not in options)):
                    self.assertEqual(metadata.track_total, 1)
                elif ("-r" in options):
                    self.assertEqual(metadata.track_total, 0)
                else:
                    self.assertEqual(metadata.track_total, 2)

                if ("--album-number" in options):
                    self.assertEqual(metadata.album_number, 7)
                elif ("-r" in options):
                    self.assertEqual(metadata.album_number, 0)
                else:
                    self.assertEqual(metadata.album_number, 3)

                if ("--album-total" in options):
                    self.assertEqual(metadata.album_total, 8)
                elif ("-r" in options):
                    self.assertEqual(metadata.album_total, 0)
                else:
                    self.assertEqual(metadata.album_total, 4)

                if ("--comment-file" in options):
                    self.assertEqual(metadata.comment, u"Comment File")
                elif ("--comment" in options):
                    self.assertEqual(metadata.comment, u"Comment 3")
                elif ("-r" in options):
                    self.assertEqual(metadata.comment, u"")
                else:
                    self.assertEqual(metadata.comment, u"Comment 1")

                if (("--cue" in options) and ("--number" not in options)):
                    self.assertEqual(metadata.ISRC, u"JPPI00652340")
                elif ("-r" in options):
                    self.assertEqual(metadata.ISRC, u"")
                else:
                    self.assertEqual(metadata.ISRC, u"ABCD00000000")

                if (("--front-cover" in options) and
                    ("--back-cover" in options)):
                    #adding front and back cover

                    if (("-r" in options) or
                        ("--remove-images" in options)):
                        if ("-T" in options):
                            self.assertEqual(
                                metadata.front_covers(),
                                [self.thumbnailed_front_cover_image])
                            self.assertEqual(
                                metadata.back_covers(),
                                [self.thumbnailed_back_cover_image])
                        else:
                            self.assertEqual(metadata.front_covers(),
                                             [self.front_cover_image])
                            self.assertEqual(metadata.back_covers(),
                                             [self.back_cover_image])
                        self.assertEqual(len(metadata.images()), 2)
                    else:
                        if ("-T" in options):
                            self.assertEqual(
                                metadata.front_covers(),
                                [self.image,
                                 self.thumbnailed_front_cover_image])
                            self.assertEqual(
                                metadata.back_covers(),
                                [self.thumbnailed_back_cover_image])
                        else:
                            self.assertEqual(metadata.front_covers(),
                                             [self.image,
                                              self.front_cover_image])
                            self.assertEqual(metadata.back_covers(),
                                             [self.back_cover_image])
                        self.assertEqual(len(metadata.images()), 3)
                elif ("--front-cover" in options):
                    #adding front-cover

                    if (("-r" in options) or
                        ("--remove-images" in options)):
                        if ("-T" in options):
                            self.assertEqual(
                                metadata.images(),
                                [self.thumbnailed_front_cover_image])
                        else:
                            self.assertEqual(metadata.images(),
                                             [self.front_cover_image])
                        self.assertEqual(len(metadata.images()), 1)
                    else:
                        if ("-T" in options):
                            self.assertEqual(
                                metadata.images(),
                                [self.image,
                                 self.thumbnailed_front_cover_image])
                        else:
                            self.assertEqual(metadata.images(),
                                             [self.image,
                                              self.front_cover_image])
                        self.assertEqual(len(metadata.images()), 2)
                elif ("--back-cover" in options):
                    #adding back cover

                    if (("-r" in options) or
                        ("--remove-images" in options)):
                        if ("-T" in options):
                            self.assertEqual(
                                metadata.images(),
                                [self.thumbnailed_back_cover_image])
                        else:
                            self.assertEqual(metadata.images(),
                                             [self.back_cover_image])
                        self.assertEqual(len(metadata.images()), 1)
                    else:
                        self.assertEqual(metadata.front_covers(),
                                             [self.image])
                        if ("-T" in options):
                            self.assertEqual(
                                metadata.back_covers(),
                                [self.thumbnailed_back_cover_image])
                        else:
                            self.assertEqual(metadata.back_covers(),
                                             [self.back_cover_image])
                        self.assertEqual(len(metadata.images()), 2)
                else:
                    #no new images added

                    if (("-r" in options) or
                        ("--remove-images" in options)):
                        self.assertEqual(len(metadata.images()), 0)
                    else:
                        self.assertEqual(metadata.images(),
                                         [self.image])
                        self.assertEqual(len(metadata.images()), 1)


                if ("--replay-gain" in options):
                    self.assert_(track.replay_gain() is not None)

    @UTIL_TRACKTAG
    def test_replaygain(self):
        for audio_class in audiotools.AVAILABLE_TYPES:
            if (audio_class.can_add_replay_gain()):
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
                        self.__check_info__(
                            _(u"Adding ReplayGain metadata.  This may take some time."))
                        track2 = audiotools.open(track_file.name)
                        self.assert_(track2.replay_gain() is not None)
                    else:
                        self.__check_info__(
                            _(u"Applying ReplayGain.  This may take some time."))


                finally:
                    track_file.close()

class tracktag_errors(UtilTest):
    @UTIL_TRACKTAG
    def test_bad_options(self):
        temp_comment = tempfile.NamedTemporaryFile(suffix=".txt")
        temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        temp_track_stat = os.stat(temp_track_file.name)[0]
        try:
            temp_track = audiotools.FlacAudio.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            temp_track.set_metadata(audiotools.MetaData(track_name=u"Foo"))

            self.assertEqual(self.__run_app__(
                ["tracktag", "-x", "/dev/null", temp_track.filename]), 1)
            self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

            self.assertEqual(self.__run_app__(
                    ["tracktag", "--front-cover=/dev/null/foo.jpg",
                     temp_track.filename]), 1)
            self.__check_error__(
                _(u"%(filename)s: %(message)s") % \
                    {"filename": self.filename(temp_track.filename),
                     "message": _(u"Unable to open file")})

            self.assertEqual(self.__run_app__(
                    ["tracktag", "--xmcd=/dev/null/foo.xmcd",
                     self.filename(temp_track.filename)]), 1)
            self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

            self.assertEqual(self.__run_app__(
                    ["tracktag", "--comment-file=/dev/null/foo.txt",
                     self.filename(temp_track.filename)]), 1)
            self.__check_error__(_(u"Unable to open comment file \"%s\"") % \
                                     (self.filename("/dev/null/foo.txt")))

            temp_comment.write(
                os.urandom(1024) + ((u"\uFFFD".encode('utf-8')) * 103))
            temp_comment.flush()

            self.assertEqual(self.__run_app__(
                    ["tracktag", "--comment-file=%s" % (temp_comment.name),
                     temp_track.filename]), 1)
            self.__check_error__(
                _(u"Comment file \"%s\" does not appear to be UTF-8 text") % \
                    (temp_comment.name))

            os.chmod(temp_track_file.name, temp_track_stat & 07555)
            self.assertEqual(self.__run_app__(
                    ["tracktag", "--name=Foo",
                     self.filename(temp_track.filename)]), 1)
            self.__check_error__(_(u"Unable to modify \"%s\"") % \
                                     (self.filename(temp_track.filename)))


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
            big_bmp = tempfile.NamedTemporaryFile(suffix=".bmp")
            big_text = tempfile.NamedTemporaryFile(suffix=".txt")
            try:
                flac = audio_class.from_pcm(
                    tempflac.name,
                    BLANK_PCM_Reader(5))

                flac.set_metadata(audiotools.MetaData(track_name=u"Foo"))

                big_bmp.write(HUGE_BMP.decode('bz2'))
                big_bmp.flush()

                big_text.write("QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2'))
                big_text.flush()

                orig_md5 = md5()
                pcm = flac.to_pcm()
                audiotools.transfer_framelist_data(pcm, orig_md5.update)
                pcm.close()

                #ensure that setting a big image via tracktag
                #doesn't break the file
                subprocess.call(["tracktag", "-V", "quiet",
                                 "--front-cover=%s" % (big_bmp.name),
                                 flac.filename])
                new_md5 = md5()
                pcm = flac.to_pcm()
                audiotools.transfer_framelist_data(pcm, new_md5.update)
                pcm.close()
                self.assertEqual(orig_md5.hexdigest(),
                                 new_md5.hexdigest())

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
                         "--front-cover=%s" % (big_bmp.name),
                         "--comment-file=%s" % (big_text.name),
                         wv.filename]), 0)

                self.assertEqual(len(wv.get_metadata().images()), 1)
                self.assert_(len(wv.get_metadata().comment) > 0)

                subprocess.call(["track2track", "-t", audio_class.NAME, "-o",
                                 flac.filename, wv.filename])

                flac = audiotools.open(tempflac.name)
                self.assertEqual(flac, wv)
            finally:
                tempflac.close()
                tempwv.close()
                big_bmp.close()
                big_text.close()


class NoMetaData(Exception):
    pass

class tracktag_misc(UtilTest):
    @UTIL_TRACKTAG
    def test_text_options(self):
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
                     elif (len(getattr(metadata, field_name)) > 0):
                         self.assertEqual(getattr(metadata, field_name),
                                          u'foo')

                         self.assertEqual(
                             self.__run_app__(['tracktag', remove_field,
                                               track.filename]), 0)

                         metadata = audiotools.open(
                             track.filename).get_metadata()

                         self.assertEqual(
                             getattr(metadata, field_name),
                             u'',
                             "remove option failed for %s field %s" %
                             (audio_type.NAME, remove_field))

                def number_fields_values(fields):
                    values = set([])
                    for field in audiotools.MetaData.INTEGER_FIELDS:
                        if (field in fields):
                            values.add(
                                (field,
                                 audiotools.MetaData.INTEGER_FIELDS.index(
                                        field) + 1))
                        else:
                            values.add((field, 0))
                    return values

                def deleted_number_fields_values(fields):
                    values = set([])
                    for field in audiotools.MetaData.INTEGER_FIELDS:
                        if (field not in fields):
                            values.add(
                                (field,
                                 audiotools.MetaData.INTEGER_FIELDS.index(
                                        field) + 1))
                        else:
                            values.add((field, 0))
                    return values

                def metadata_fields_values(metadata):
                    values = set([])
                    for field in audiotools.MetaData.INTEGER_FIELDS:
                        values.add((field, getattr(metadata, field)))
                    return values


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
                                    number_fields_values(fields)))

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
                                    deleted_number_fields_values(fields)),
                                "%s not subset of %s for options %s type %s" %
                                (metadata_fields_values(metadata),
                                 deleted_number_fields_values(fields),
                                 self.populate_delete_number_fields(fields),
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


    @UTIL_TRACKTAG
    def test_xmcd(self):
        LENGTH = 1134
        OFFSETS = [150, 18740, 40778, 44676, 63267]
        TRACK_LENGTHS = [y - x for x, y in zip(OFFSETS + [LENGTH * 75],
                                              (OFFSETS + [LENGTH * 75])[1:])]
        data = {"DTITLE": "Artist / Album",
                "TTITLE0": u"track one",
                "TTITLE1": u"track two",
                "TTITLE2": u"track three",
                "TTITLE3": u"track four",
                "TTITLE4": u"track five",
                "EXTT0": u"",
                "EXTT1": u"",
                "EXTT2": u"",
                "EXTT3": u"",
                "EXTT4": u""}

        #construct our XMCD file
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        xmcd_file.write(audiotools.XMCD(data, [u"# xmcd"]).to_string())
        xmcd_file.flush()

        #construct a batch of temporary tracks
        temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                       for i in xrange(len(OFFSETS))]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    EXACT_BLANK_PCM_Reader(length * 44100 / 75))
                      for (track, length) in zip(temp_tracks, TRACK_LENGTHS)]
            for (i, track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            #tag them with tracktag
            subprocess.call(["tracktag", "-x", xmcd_file.name] + \
                            [track.filename for track in tracks])

            #ensure the metadata values are correct
            for (track, name, i) in zip(tracks, [u"track one",
                                                 u"track two",
                                                 u"track three",
                                                 u"track four",
                                                 u"track five"],
                                      range(len(tracks))):
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, name)
                self.assertEqual(metadata.track_number, i + 1)
                self.assertEqual(metadata.album_name, u"Album")
                self.assertEqual(metadata.artist_name, u"Artist")
        finally:
            xmcd_file.close()
            for track in temp_tracks:
                track.close()

        #construct a fresh XMCD file
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        xmcd_file.write(audiotools.XMCD(data, [u"# xmcd"]).to_string())
        xmcd_file.flush()

        #construct a batch of temporary tracks with a file missing
        temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                       for i in xrange(len(OFFSETS))]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    EXACT_BLANK_PCM_Reader(length * 44100 / 75))
                      for (track, length) in zip(temp_tracks, TRACK_LENGTHS)]
            for (i, track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            del(tracks[2])

            #tag them with tracktag
            subprocess.call(["tracktag", "-x", xmcd_file.name] + \
                            [track.filename for track in tracks])

            #ensure the metadata values are correct
            for (track, name, i) in zip(tracks, [u"track one",
                                                 u"track two",
                                                 u"track four",
                                                 u"track five"],
                                      [0, 1, 3, 4]):
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, name)
                self.assertEqual(metadata.track_number, i + 1)
                self.assertEqual(metadata.album_name, u"Album")
                self.assertEqual(metadata.artist_name, u"Artist")
        finally:
            xmcd_file.close()
            for track in temp_tracks:
                track.close()

        #construct a fresh XMCD file with a track missing
        del(data["TTITLE2"])
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        xmcd_file.write(audiotools.XMCD(data, [u"# xmcd"]).to_string())
        xmcd_file.flush()

        #construct a batch of temporary tracks
        temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                       for i in xrange(len(OFFSETS))]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    EXACT_BLANK_PCM_Reader(length * 44100 / 75))
                      for (track, length) in zip(temp_tracks, TRACK_LENGTHS)]
            for (i, track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            #tag them with tracktag
            subprocess.call(["tracktag", "-x", xmcd_file.name] + \
                            [track.filename for track in tracks])

            #ensure the metadata values are correct
            for (track, name, i) in zip(tracks, [u"track one",
                                                 u"track two",
                                                 u"",
                                                 u"track four",
                                                 u"track five"],
                                      range(len(tracks))):
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, name)
                self.assertEqual(metadata.track_number, i + 1)
                self.assertEqual(metadata.album_name, u"Album")
                self.assertEqual(metadata.artist_name, u"Artist")
        finally:
            xmcd_file.close()
            for track in temp_tracks:
                track.close()

    @UTIL_TRACKTAG
    def test_cuesheet1(self):
        for audio_class in [audiotools.FlacAudio,
                            audiotools.WavPackAudio]:
            #create single track and cuesheet
            temp_track = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            temp_sheet = tempfile.NamedTemporaryFile(
                suffix=".cue")
            try:
                temp_sheet.write(
"""eJydkF1LwzAUQN8L/Q+X/oBxk6YfyVtoM4mu68iy6WudQ8qkHbNu+u9NneCc1IdCnk649xyuUQXk
epnpHGiOMU2Q+Z5xMCuLQs0tBOq92nTy7alus3b/AUeccL5/ZIHvZdLKWXkDjKcpIg2RszjxvYUy
09IUykCwanZNe2pAHrr6tXMjVtuZ+uG27l62Dk91T03VPG8np+oYwL1cK98DsEZmd4AE5CrXZU8c
O++wh2qzQxKc4X/S/l8vTQa3i7V2kWEap/iN57l66Pcjiq93IaWDUjpOyn9LETAVyASh1y0OR4Il
Fy3hYEs4qiXB6wOQULBQkOhCygalbISUUvrnACQVERfIr1scI4K5lk9od5+/""".decode('base64').decode('zlib'))
                temp_sheet.flush()
                album = audio_class.from_pcm(
                    temp_track.name,
                    EXACT_BLANK_PCM_Reader(69470436))
                sheet = audiotools.read_sheet(temp_sheet.name)

                #add metadata
                self.assertEqual(subprocess.call(["tracktag",
                                                  "--album", "Album Name",
                                                  "--artist", "Artist Name",
                                                  "--album-number", "2",
                                                  "--album-total", "3",
                                                  temp_track.name]), 0)

                metadata = audiotools.MetaData(
                    album_name=u"Album Name",
                    artist_name=u"Artist Name",
                    album_number=2,
                    album_total=3)

                #add cuesheet
                self.assertEqual(
                    subprocess.call(["tracktag", "--cue", temp_sheet.name,
                                     temp_track.name]), 0)

                #ensure metadata matches
                self.assertEqual(album.get_metadata(), metadata)

                #ensure cuesheet matches
                sheet2 = album.get_cuesheet()

                self.assertNotEqual(sheet2, None)
                self.assertEqual(sheet.catalog(),
                                 sheet2.catalog())
                self.assertEqual(sorted(sheet.ISRCs().items()),
                                 sorted(sheet2.ISRCs().items()))
                self.assertEqual(list(sheet.indexes()),
                                 list(sheet2.indexes()))
                self.assertEqual(list(sheet.pcm_lengths(69470436)),
                                 list(sheet2.pcm_lengths(69470436)))
            finally:
                temp_track.close()
                temp_sheet.close()

    @UTIL_TRACKTAG
    def test_cuesheet2(self):
        for audio_class in [audiotools.FlacAudio,
                            audiotools.WavPackAudio]:
            #create single track and cuesheet
            temp_track = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            temp_sheet = tempfile.NamedTemporaryFile(
                suffix=".cue")
            try:
                temp_sheet.write(
"""eJydkF1LwzAUQN8L/Q+X/oBxk6YfyVtoM4mu68iy6WudQ8qkHbNu+u9NneCc1IdCnk649xyuUQXk
epnpHGiOMU2Q+Z5xMCuLQs0tBOq92nTy7alus3b/AUeccL5/ZIHvZdLKWXkDjKcpIg2RszjxvYUy
09IUykCwanZNe2pAHrr6tXMjVtuZ+uG27l62Dk91T03VPG8np+oYwL1cK98DsEZmd4AE5CrXZU8c
O++wh2qzQxKc4X/S/l8vTQa3i7V2kWEap/iN57l66Pcjiq93IaWDUjpOyn9LETAVyASh1y0OR4Il
Fy3hYEs4qiXB6wOQULBQkOhCygalbISUUvrnACQVERfIr1scI4K5lk9od5+/""".decode('base64').decode('zlib'))
                temp_sheet.flush()
                album = audio_class.from_pcm(
                            temp_track.name,
                            EXACT_BLANK_PCM_Reader(69470436))
                sheet = audiotools.read_sheet(temp_sheet.name)

                #add cuesheet
                self.assertEqual(
                    subprocess.call(["tracktag", "--cue", temp_sheet.name,
                                     temp_track.name]), 0)

                #add metadata
                self.assertEqual(subprocess.call(["tracktag",
                                                  "--album", "Album Name",
                                                  "--artist", "Artist Name",
                                                  "--album-number", "2",
                                                  "--album-total", "3",
                                                  temp_track.name]), 0)

                metadata = audiotools.MetaData(
                    album_name=u"Album Name",
                    artist_name=u"Artist Name",
                    album_number=2,
                    album_total=3)

                #ensure metadata matches
                self.assertEqual(album.get_metadata(), metadata)

                #ensure cuesheet matches
                sheet2 = album.get_cuesheet()

                self.assertNotEqual(sheet2, None)
                self.assertEqual(sheet.catalog(),
                                 sheet2.catalog())
                self.assertEqual(sorted(sheet.ISRCs().items()),
                                 sorted(sheet2.ISRCs().items()))
                self.assertEqual(list(sheet.indexes()),
                                 list(sheet2.indexes()))
                self.assertEqual(list(sheet.pcm_lengths(69470436)),
                                 list(sheet2.pcm_lengths(69470436)))
            finally:
                temp_track.close()
                temp_sheet.close()


class trackrename(UtilTest):
    @UTIL_TRACKRENAME
    def setUp(self):
        self.type = audiotools.FlacAudio

        self.format = "%(track_number)2.2d.%(suffix)s"

        self.input_dir = tempfile.mkdtemp()

        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Album 3</title><artist><name>Artist 3</name></artist><release-event-list><event catalog-number="" date="2011"/></release-event-list><track-list><track><title>Track 3-1</title><duration>5000</duration></track><track><title>Track 3-2</title><duration>6000</duration></track><track><title>Track 3-3</title><duration>7000</duration></track></track-list></release></release-list></metadata>')
        self.xmcd_file.flush()
        self.xmcd_metadata = audiotools.read_metadata_file(self.xmcd_file.name)

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
        self.xmcd_file.close()

        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

    def clean_input_directory(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))

    def populate_options(self, options):
        populated = []
        for option in options:
            if (option == '-x'):
                populated.append(option)
                populated.append(self.xmcd_file.name)
            elif (option == '--format'):
                populated.append(option)
                populated.append(self.format)
            else:
                populated.append(option)
        return populated

    @UTIL_TRACKRENAME
    def test_options(self):
        messenger = audiotools.Messenger("trackrename", None)

        all_options = ["-x", "--format"]
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

                    track_data = open(track.filename, 'rb').read()

                    self.assertEqual(
                        self.__run_app__(["trackrename", "-V", "normal",
                                          track.filename] + options), 0)

                    if ("--format" in options):
                        output_format = self.format
                    else:
                        output_format = None

                    #check that the output is being generated correctly
                    if ("-x" in options):
                        if (metadata is not None):
                            base_metadata = \
                                self.xmcd_metadata.track_metadata(
                                metadata.track_number)
                        elif (name.startswith("02")):
                            base_metadata = self.xmcd_metadata.track_metadata(2)
                        else:
                            base_metadata = None
                    elif (metadata is not None):
                        base_metadata = metadata
                    else:
                        if (name.startswith("02")):
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
                        _(u"%(source)s -> %(destination)s") %
                        {"source":
                             messenger.filename(track.filename),
                         "destination":
                             messenger.filename(destination_filename)})

                    #check that the file is identical
                    self.assertEqual(track_data,
                                     open(destination_filename, 'rb').read())

    @UTIL_TRACKRENAME
    def test_errors(self):
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
            self.__check_error__(_(u"You must specify at least 1 supported audio file"))

            self.assertEqual(self.__run_app__(
                    ["trackrename", "-x", "/dev/null", track.filename]), 1)
            self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

            self.assertEqual(self.__run_app__(
                    ["trackrename", "--format=%(foo)s", track.filename]), 1)

            self.__check_error__(_(u"Unknown field \"%s\" in file format") % \
                                     ("foo"))
            self.__check_info__(_(u"Supported fields are:"))
            for field in sorted(audiotools.MetaData.FIELDS + \
                                    ("album_track_number", "suffix")):
                if (field == 'track_number'):
                    self.__check_info__(u"%(track_number)2.2d")
                else:
                    self.__check_info__(u"%%(%s)s" % (field))

            if (track.get_metadata() is not None):
                os.chmod(tempdir, tempdir_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["trackrename",
                         '--format=%(album_name)s/%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]), 1)

                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         self.filename(
                        os.path.join(
                            "Album",
                            "%(track_number)2.2d - %(track_name)s.%(suffix)s" % \
                                {"track_number": 1,
                                 "track_name": "Name",
                                 "suffix": self.type.SUFFIX})))

                self.assertEqual(self.__run_app__(
                        ["trackrename",
                         '--format=%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]), 1)

        finally:
            os.chmod(tempdir, tempdir_stat)
            os.unlink(track.filename)
            os.rmdir(tempdir)




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

        self.unsplit_file2 = tempfile.NamedTemporaryFile(suffix=".flac")

        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Album 3</title><artist><name>Artist 3</name></artist><release-event-list><event catalog-number="" date="2011"/></release-event-list><track-list><track><title>Track 3-1</title><duration>5000</duration></track><track><title>Track 3-2</title><duration>6000</duration></track><track><title>Track 3-3</title><duration>7000</duration></track></track-list></release></release-list></metadata>')
        self.xmcd_file.flush()
        self.xmcd_metadata = audiotools.read_metadata_file(self.xmcd_file.name)

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
        self.xmcd_file.close()

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
        populated = []
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
            elif (option == '-x'):
                populated.append(option)
                populated.append(self.xmcd_file.name)
            elif (option == '--cue'):
                populated.append(option)
                populated.append(self.cuesheet.name)
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKSPLIT
    def test_options_no_embedded_cue(self):
        messenger = audiotools.Messenger("trackcat", None)

        all_options = ["--cue", "-t", "-q", "-d", "--format", "-x"]

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
                        self.__run_app__(["tracksplit", "-V", "normal"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported " +
                          u"compression mode for type \"%(type)s\"") %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                if ("--cue" not in options):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        _(u"You must specify a cuesheet to split audio file"))
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal"] +
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

                if ("-x" in options):
                    for i in xrange(3):
                        base_metadata.track_name = \
                            self.xmcd_metadata.track_metadata(i + 1).track_name
                        base_metadata.track_number = i + 1
                        base_metadata.album_name = u"Album 3"
                        base_metadata.artist_name = u"Artist 3"
                        output_filenames.append(
                            output_type.track_name(
                                "",
                                base_metadata,
                                output_format))
                else:
                    for i in xrange(3):
                        base_metadata.track_number = i + 1
                        output_filenames.append(
                            output_type.track_name(
                                "",
                                base_metadata,
                                output_format))

                #check that the output is being generated correctly
                for path in output_filenames:
                    self.__check_info__(
                        _(u"%(source)s -> %(destination)s") % \
                       {"source":
                            messenger.filename(track.filename),
                        "destination":
                            messenger.filename(
                                os.path.join(output_dir, path))})

                #make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.stream.reset()
                self.assert_(
                    audiotools.pcm_frame_cmp(
                        audiotools.PCMCat(iter([t.to_pcm()
                                                for t in output_tracks])),
                        self.stream) is None)

                #make sure metadata fits our expectations
                for i in xrange(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if (metadata is not None):
                        if ("-x" in options):
                            self.assertEqual(
                                metadata.track_name,
                                self.xmcd_metadata.track_metadata(i + 1).track_name)
                            self.assertEqual(
                                metadata.album_name,
                                self.xmcd_metadata.track_metadata(i + 1).album_name)
                            self.assertEqual(
                                metadata.artist_name,
                                self.xmcd_metadata.track_metadata(i + 1).artist_name)
                        else:
                            self.assertEqual(metadata.track_name, u"")
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
        messenger = audiotools.Messenger("trackcat", None)

        all_options = ["--cue", "-t", "-q", "-d", "--format", "-x"]

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
                        self.__run_app__(["tracksplit", "-V", "normal"] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported " +
                          u"compression mode for type \"%(type)s\"") %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal"] +
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
                if ("-x" in options):
                    for i in xrange(3):
                        base_metadata.track_name = \
                            self.xmcd_metadata.track_metadata(i + 1).track_name
                        base_metadata.track_number = i + 1
                        base_metadata.album_name = u"Album 3"
                        base_metadata.artist_name = u"Artist 3"
                        output_filenames.append(
                            output_type.track_name(
                                "",
                                base_metadata,
                                output_format))
                else:
                    for i in xrange(3):
                        base_metadata.track_number = i + 1
                        output_filenames.append(
                            output_type.track_name(
                                "",
                                base_metadata,
                                output_format))

                #check that the output is being generated correctly
                for path in output_filenames:
                    self.__check_info__(
                        _(u"%(source)s -> %(destination)s") % \
                       {"source":
                            messenger.filename(track.filename),
                        "destination":
                            messenger.filename(
                                os.path.join(output_dir, path))})

                #make sure no track data has been lost
                output_tracks = [
                    audiotools.open(os.path.join(output_dir, filename))
                    for filename in output_filenames]
                self.stream.reset()
                self.assert_(
                    audiotools.pcm_frame_cmp(
                        audiotools.PCMCat(iter([t.to_pcm()
                                                for t in output_tracks])),
                        self.stream) is None)

                #make sure metadata fits our expectations
                for i in xrange(len(output_tracks)):
                    metadata = output_tracks[i].get_metadata()
                    if (metadata is not None):
                        if ("-x" in options):
                            self.assertEqual(
                                metadata.track_name,
                                self.xmcd_metadata.track_metadata(i + 1).track_name)
                            self.assertEqual(
                                metadata.album_name,
                                self.xmcd_metadata.track_metadata(i + 1).album_name)
                            self.assertEqual(
                                metadata.artist_name,
                                self.xmcd_metadata.track_metadata(i + 1).artist_name)
                        else:
                            self.assertEqual(metadata.track_name, u"")
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
            elif (option == '-x'):
                populated.append(option)
                populated.append(os.devnull)
            else:
                populated.append(option)

        return populated

    @UTIL_TRACKSPLIT
    def test_errors(self):
        filename = audiotools.Messenger("tracksplit", None).filename

        track1 = self.type.from_pcm(self.unsplit_file.name,
                                    BLANK_PCM_Reader(18))

        track2 = self.type.from_pcm(self.unsplit_file2.name,
                                    BLANK_PCM_Reader(5))

        all_options = ["-t", "-q", "-d", "--format", "-x"]

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
                        _(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") %
                        {"quality": "bar",
                         "type":audiotools.DEFAULT_TYPE})
                    continue

                if ("-x" in options):
                    self.__check_error__(
                        _(u"Invalid XMCD or MusicBrainz XML file"))
                    continue

                if ("--format" in options):
                    self.__check_error__(
                        _(u"Unknown field \"%s\" in file format") % ("foo"))
                    self.__check_info__(_(u"Supported fields are:"))
                    for field in sorted(audiotools.MetaData.FIELDS + \
                                            ("album_track_number", "suffix")):
                        if (field == 'track_number'):
                            self.__check_info__(u"%(track_number)2.2d")
                        else:
                            self.__check_info__(u"%%(%s)s" % (field))
                    continue

                if ("-d" in options):
                    output_path = os.path.join(
                        self.unwritable_dir,
                        output_type.track_name(
                            "",
                            audiotools.MetaData(track_number=1,
                                                track_total=3),
                            audiotools.FILENAME_FORMAT))
                    self.__check_error__(
                        _(u"[Errno 13] Permission denied: \'%s\'") % \
                            (output_path))
                    continue

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir]), 1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name, self.unsplit_file2.name]), 1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name]), 1)

        self.__check_error__(_(u"You must specify a cuesheet to split audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 "--cue", self.cuesheet.name, track2.filename]), 1)

        self.__check_error__(_(u"Cuesheet too long for track being split"))

        #FIXME? - check for broken cue sheet output?
