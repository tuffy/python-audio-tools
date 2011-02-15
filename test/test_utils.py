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
from test_reorg import (parser, BLANK_PCM_Reader, Combinations)

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
                populated.append('-t')
                populated.append(self.type)
            elif (option == '-q'):
                populated.append('-q')
                populated.append(self.quality)
            elif (option == '-d'):
                populated.append('-d')
                populated.append(self.output_dir)
            elif (option == '--format'):
                populated.append('--format')
                populated.append(self.format)
            elif (option == '-o'):
                populated.append('-o')
                populated.append(self.output_file.name)
            elif (option == '-x'):
                populated.append('-x')
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
                    ["-V", "normal", self.track1.filename]
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
