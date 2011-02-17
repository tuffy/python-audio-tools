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
import test_streams
from hashlib import md5

from test_reorg import (parser, BLANK_PCM_Reader, Combinations,
                        EXACT_BLANK_PCM_Reader,
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

    def filename(self, s):
        return s.decode(audiotools.FS_ENCODING, 'replace')

    def __check_output__(self, s):
        self.assertEqual(
            unicodedata.normalize(
                'NFC',
                self.stdout.readline().decode(audiotools.IO_ENCODING)),
            unicodedata.normalize('NFC', s) + unicode(os.linesep))

    def __check_info__(self, s):
        self.assertEqual(
            unicodedata.normalize(
                'NFC',
                self.stderr.readline().decode(audiotools.IO_ENCODING)),
            unicodedata.normalize('NFC', s) + unicode(os.linesep))

    def __check_error__(self, s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            u"*** Error: " + unicodedata.normalize('NFC', s) + unicode(os.linesep))

    def __check_warning__(self, s):
        self.assertEqual(
            unicodedata.normalize(
                'NFC',
                self.stderr.readline().decode(audiotools.IO_ENCODING)),
            u"*** Warning: " + unicodedata.normalize('NFC', s) + unicode(os.linesep))

    def __check_usage__(self, executable, s):
        self.assertEqual(
            unicodedata.normalize(
                'NFC',
                self.stderr.readline().decode(audiotools.IO_ENCODING)),
            u"*** Usage: " + executable.decode('ascii') + u" " + \
                unicodedata.normalize('NFC', s) + unicode(os.linesep))

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
        self.track_metadata.add_image(
            audiotools.Image.new(open("bigpng.png", "rb").read(), u"", 0))
        self.track1.set_metadata(self.track_metadata)

        self.output_dir = tempfile.mkdtemp()
        self.output_file = tempfile.NamedTemporaryFile()
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

    def clean_output_dirs(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir, f))

        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))

        f = open(self.output_file.name, "wb")
        f.close()

    @UTIL_TRACK2TRACK
    def test_options(self):
        messenger = audiotools.Messenger("track2track", None)

        all_options = ["-t", "-q", "-d", "--format", "-o", "-T",
                       "--replay-gain", "--no-replay-gain"]

        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                self.clean_output_dirs()

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
                elif ('-d' in options):
                    #output file in self.output_dir

                    if ('-t' in options):
                        output_class = audiotools.TYPE_MAP[
                            options[options.index('-t') + 1]]
                    else:
                        output_class = audiotools.TYPE_MAP[
                            audiotools.DEFAULT_TYPE]

                    if ('--format' in options):
                        output_format = options[options.index('--format') + 1]
                    else:
                        output_format = audiotools.FILENAME_FORMAT

                    if ('-x' in options):
                        metadata = self.xmcd_metadata[1]
                    else:
                        metadata = self.track1.get_metadata()

                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 0)

                    output_path = os.path.join(self.output_dir,
                                               output_class.track_name(
                            file_path="",
                            track_metadata=metadata,
                            format=output_format))
                    self.__check_info__(
                        _(u"%(source)s -> %(destination)s") %
                        {"source":
                             messenger.filename(self.track1.filename),
                         "destination":
                             messenger.filename(output_path)})
                    self.assert_(os.path.isfile(output_path))
                    track2 = audiotools.open(output_path)
                    self.assertEqual(track2.NAME, output_class.NAME)
                    self.assertEqual(track2.get_metadata(), metadata)

                    image = track2.get_metadata().images()[0]
                    if ('-T' in options):
                        self.assertEqual(max(image.width,
                                             image.height),
                                         audiotools.THUMBNAIL_SIZE)
                    else:
                        self.assertEqual(image.width, 10000)
                        self.assertEqual(image.height, 10000)

                    if (('--no-replay-gain' in options) and
                        ('--replay-gain' not in options)):
                        self.assert_(track2.replay_gain() is None)
                    elif ('--no-replay-gain' not in options):
                        self.assert_(track2.replay_gain() is not None)
                elif ('-o' in options):
                    #output file in self.output_file

                    if ('-t' in options):
                        output_class = audiotools.TYPE_MAP[
                            options[options.index('-t') + 1]]
                    else:
                        output_class = audiotools.TYPE_MAP[
                            audiotools.DEFAULT_TYPE]

                    if ('-x' in options):
                        metadata = self.xmcd_metadata[1]
                    else:
                        metadata = self.track1.get_metadata()

                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 0)

                    if ('--format' in options):
                        self.__check_warning__(
                            _(u"--format has no effect when used with -o"))

                    output_path = self.output_file.name
                    self.assert_(os.path.isfile(output_path))
                    track2 = audiotools.open(output_path)
                    self.assertEqual(track2.NAME, output_class.NAME)
                    self.assertEqual(track2.get_metadata(), metadata)

                    image = track2.get_metadata().images()[0]
                    if ('-T' in options):
                        self.assertEqual(max(image.width,
                                             image.height),
                                         audiotools.THUMBNAIL_SIZE)
                    else:
                        self.assertEqual(image.width, 10000)
                        self.assertEqual(image.height, 10000)

                    self.assert_(track2.replay_gain() is None)
                else:
                    #output file in cwd

                    if ('-t' in options):
                        output_class = audiotools.TYPE_MAP[
                            options[options.index('-t') + 1]]
                    else:
                        output_class = audiotools.TYPE_MAP[
                            audiotools.DEFAULT_TYPE]

                    if ('--format' in options):
                        output_format = options[options.index('--format') + 1]
                    else:
                        output_format = audiotools.FILENAME_FORMAT

                    if ('-x' in options):
                        metadata = self.xmcd_metadata[1]
                    else:
                        metadata = self.track1.get_metadata()

                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 0)

                    output_filename = output_class.track_name(
                        file_path="",
                        track_metadata=metadata,
                        format=output_format)
                    output_path = os.path.join(self.cwd_dir, output_filename)
                    self.__check_info__(
                        _(u"%(source)s -> %(destination)s") %
                        {"source":
                             messenger.filename(self.track1.filename),
                         "destination":
                             messenger.filename("./" + output_filename)})
                    self.assert_(os.path.isfile(output_path))
                    track2 = audiotools.open(output_path)
                    self.assertEqual(track2.NAME, output_class.NAME)
                    self.assertEqual(track2.get_metadata(), metadata)

                    image = track2.get_metadata().images()[0]
                    if ('-T' in options):
                        self.assertEqual(max(image.width,
                                             image.height),
                                         audiotools.THUMBNAIL_SIZE)
                    else:
                        self.assertEqual(image.width, 10000)
                        self.assertEqual(image.height, 10000)

                    if (('--no-replay-gain' in options) and
                        ('--replay-gain' not in options)):
                        self.assert_(track2.replay_gain() is None)
                    elif ('--no-replay-gain' not in options):
                        self.assert_(track2.replay_gain() is not None)

class track2track_errors(UtilTest):
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
        self.track_metadata.add_image(
            audiotools.Image.new(open("bigpng.png", "rb").read(), u"", 0))
        self.track1.set_metadata(self.track_metadata)

        self.output_dir = "/dev/null/directory/"
        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('Invalid XMCD file')
        self.xmcd_file.flush()

        self.format = "%(foo)s.%(bar)s"
        self.type = self.output_format.NAME
        self.quality = self.output_format.COMPRESSION_MODES[0]

        self.cwd_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.cwd_dir)
        os.chmod(self.cwd_dir, 0500)

        self.output_file = InvalidTemporaryFile(
            os.path.join(self.cwd_dir, "bad_filename"))

    @UTIL_TRACK2TRACK
    def tearDown(self):
        os.chdir(self.original_dir)

        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

        os.chmod(self.cwd_dir, 0700)
        for f in os.listdir(self.cwd_dir):
            os.unlink(os.path.join(self.cwd_dir, f))
        os.rmdir(self.cwd_dir)

        self.xmcd_file.close()

    @UTIL_TRACK2TRACK
    def test_bad_options(self):
        messenger = audiotools.Messenger("track2track", None)

        self.assertEqual(self.__run_app__(
                ["track2track", "-t", "wav", "-q", "help"]), 0)
        self.__check_error__(_(u"Audio type %s has no compression modes") % \
                                 (audiotools.WaveAudio.NAME))

        self.assertEqual(self.__run_app__(
                ["track2track", "-t", "flac", "-q", "foobar"]), 1)
        self.__check_error__(_(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") % \
                                 {"quality": "foobar",
                                  "type": audiotools.FlacAudio.NAME})

        self.assertEqual(self.__run_app__(
                ["track2track", "-t", "flac"]), 1)
        self.__check_error__(_(u"You must specify at least 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["track2track", "-j", str(0), "-t", "flac",
                 self.track1.filename]), 1)
        self.__check_error__(_(u'You must run at least 1 process at a time'))

        self.assertEqual(self.__run_app__(
                ["track2track", "-o", "fail.flac",
                 self.track1.filename, self.track1.filename]), 1)
        self.__check_error__(_(u'You may specify only 1 input file for use with -o'))

        all_options = ["-t", "-q", "-d", "--format", "-o", "-T",
                       "--replay-gain", "--no-replay-gain"]

        for count in xrange(1, len(all_options) + 1):
            for options in Combinations(all_options, count):
                options = self.populate_options(options) + \
                    ["-V", "normal", self.track1.filename]

                if (("-d" in options) and ("-o" in options)):
                    #-d and -o trigger an error

                    self.assertEqual(
                        self.__run_app__(["track2track"] + options), 1)
                    self.__check_error__(
                        _(u"-o and -d options are not compatible"))
                    self.__check_info__(
                        _(u"Please specify either -o or -d but not both"))
                elif ("-d" in options):
                    #an unwritable output directory should trigger an error

                    if ("-x" in options):
                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_error__(
                            _(u"Invalid XMCD or MusicBrainz XML file"))
                    elif ("--format" in options):
                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_error__(
                            _(u"Unknown field \"%(field)s\" in file format") %
                            {"field":u"foo"})
                    else:
                        output_path = os.path.join(
                            self.output_dir,
                            self.output_format.track_name(
                                file_path="",
                                track_metadata=self.track1.get_metadata(),
                                format=audiotools.FILENAME_FORMAT))

                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_error__(
                            _(u"Unable to write \"%(filename)s\"") %
                            {"filename":messenger.filename(output_path)})
                elif ("-o" in options):
                    #an unwritable output file should trigger an error

                    if ("-x" in options):
                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_error__(
                            _(u"Invalid XMCD or MusicBrainz XML file"))
                    else:
                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)

                        if ("--format" in options):
                            self.__check_warning__(
                                _(u"--format has no effect when used with -o"))
                        self.__check_error__(
                            _(u"%(filename)s: [Errno 13] Permission denied: '%(filename)s'") % \
                                {"filename":
                                     messenger.filename(self.output_file.name)})
                else:
                    #an unwritable cwd should trigger an error

                    if ("-x" in options):
                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_error__(
                            _(u"Invalid XMCD or MusicBrainz XML file"))
                    elif ("--format" in options):
                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_error__(
                            _(u"Unknown field \"%(field)s\" in file format") %
                            {"field":u"foo"})
                    else:
                        output_path = os.path.join(
                            ".",
                            self.output_format.track_name(
                                file_path="",
                                track_metadata=self.track1.get_metadata(),
                                format=audiotools.FILENAME_FORMAT))

                        self.assertEqual(
                            self.__run_app__(["track2track"] + options), 1)
                        self.__check_info__(
                            _(u"%(source)s -> %(destination)s") %
                            {"source":
                                 messenger.filename(self.track1.filename),
                             "destination":
                                 messenger.filename(output_path)})
                        self.__check_error__(
                            _(u"%(filename)s: [Errno 13] Permission denied: '%(filename)s'") %
                            {"filename":messenger.filename(output_path)})


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
        self.track2 = audiotools.FlacAudio.from_pcm(
            self.track2_file.name, self.stream2)
        self.track3 = audiotools.FlacAudio.from_pcm(
            self.track3_file.name, self.stream3)
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
                        output_format = audiotools.DEFAULT_TYPE

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

                self.assertEqual(
                    self.__run_app__(["trackcat"] + options), 0)
                new_track = audiotools.open(outfile)
                self.assertEqual(new_track.NAME, output_format.NAME)
                self.assertEqual(new_track.total_frames(), 793800)
                self.stream1.reset()
                self.stream2.reset()
                self.stream3.reset()
                self.assert_(audiotools.pcm_frame_cmp(
                        new_track.to_pcm(),
                        audiotools.PCMCat(iter([self.stream1,
                                                self.stream2,
                                                self.stream3]))) is None)

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

                track = audiotools.open(self.track_file.name)
                track.verify()
                metadata = track.get_metadata()

                if ("--name" in options):
                    self.assertEqual(metadata.track_name, u"Name 3")
                elif ("-x" in options):
                    self.assertEqual(metadata.track_name, u"Name 2")
                elif ("-r" in options):
                    self.assertEqual(metadata.track_name, u"")
                else:
                    self.assertEqual(metadata.track_name, u"Name 1")

                if ("--artist" in options):
                    self.assertEqual(metadata.artist_name, u"Artist 3")
                elif ("-x" in options):
                    self.assertEqual(metadata.artist_name, u"Artist 2")
                elif ("-r" in options):
                    self.assertEqual(metadata.artist_name, u"")
                else:
                    self.assertEqual(metadata.artist_name, u"Artist 1")

                if ("--album" in options):
                    self.assertEqual(metadata.album_name, u"Album 3")
                elif ("-x" in options):
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
                elif ("-x" in options):
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

                if ("--cue" in options):
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


class tracktag_misc(UtilTest):
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
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "-j", str(1)] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported " +
                          u"compression mode for type \"%(type)s\"") %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                if ("--cue" not in options):
                    self.assertEqual(
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "-j", str(1)] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        _(u"You must specify a cuesheet to split audio file"))
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal",
                                      "-j", str(1)] +
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
                        self.__run_app__(["tracksplit", "-V", "normal",
                                          "-j", str(1)] +
                                         options + [track.filename]), 1)
                    self.__check_error__(
                        _(u"\"%(quality)s\" is not a supported " +
                          u"compression mode for type \"%(type)s\"") %
                        {"quality": "1",
                         "type": output_type.NAME})
                    continue

                self.assertEqual(
                    self.__run_app__(["tracksplit", "-V", "normal",
                                      "-j", str(1)] +
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

    @UTIL_TRACKSPLIT
    def test_errors(self):
        track1 = self.type.from_pcm(self.unsplit_file.name,
                                    BLANK_PCM_Reader(18))

        track2 = self.type.from_pcm(self.unsplit_file2.name,
                                    BLANK_PCM_Reader(5))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-q", "help"]), 0)
        self.__check_info__(_(u"Available compression types for %s:") % \
                                (audiotools.FlacAudio.NAME))
        for m in audiotools.FlacAudio.COMPRESSION_MODES:
            self.assert_(self.stderr.readline().decode(audiotools.IO_ENCODING).lstrip().startswith(m.decode('ascii')))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "wav", "-q", "help"]), 0)

        self.__check_error__(_(u"Audio type %s has no compression modes") % \
                                 (audiotools.WaveAudio.NAME))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-q", "foobar"]), 1)

        self.__check_error__(_(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") % \
                                 {"quality": "foobar",
                                  "type": audiotools.FlacAudio.NAME})

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir, "/dev/null/foo"]), 1)

        self.__check_error__(_(u"Unable to open \"%s\"") % (u"/dev/null/foo"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir]), 1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name, self.unsplit_file2.name]), 1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-j", str(0), "-t", "flac", "-d",
                 self.output_dir,
                 "--cue", self.cuesheet.name, self.unsplit_file.name]), 1)

        self.__check_error__(_(u'You must run at least 1 process at a time'))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 "--cue", self.cuesheet.name, "-x", "/dev/null",
                 self.unsplit_file.name]), 1)

        self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 self.unsplit_file.name]), 1)

        self.__check_error__(_(u"You must specify a cuesheet to split audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-t", "flac", "-d", self.output_dir,
                 "--cue", self.cuesheet.name, track2.filename]), 1)

        self.__check_error__(_(u"Cuesheet too long for track being split"))

        self.assertEqual(self.__run_app__(
                ["tracksplit", "-j", str(1), "-t", "flac", "--format=%(foo)s", "-d",
                 self.output_dir, "--cue", self.cuesheet.name,
                 "-x", self.xmcd_file.name,
                 self.unsplit_file.name]), 1)

        self.__check_error__(_(u"Unknown field \"%s\" in file format") % \
                            ("foo"))
        self.__check_info__(_(u"Supported fields are:"))
        for field in sorted(audiotools.MetaData.__FIELDS__ + \
                                ("album_track_number", "suffix")):
            if (field == 'track_number'):
                self.__check_info__(u"%(track_number)2.2d")
            else:
                self.__check_info__(u"%%(%s)s" % (field))

        #FIXME? - check for broken cue sheet output?
