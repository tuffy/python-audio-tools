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
from test_reorg import (parser, BLANK_PCM_Reader, Combinations,
                        TEST_COVER1, TEST_COVER2, TEST_COVER3)

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

        # self.front_cover = tempfile.NamedTemporaryFile(suffix=".jpg")
        # self.front_cover.write(TEST_COVER1)
        # self.front_cover.flush()
        self.front_cover = "bigpng.png"

        self.back_cover = tempfile.NamedTemporaryFile(suffix=".png")
        self.back_cover.write(TEST_COVER2)
        self.back_cover.flush()

        self.front_cover_image = audiotools.Image.new(
            open("bigpng.png").read(), u"", 0)
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
                populated.append(self.front_cover)
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
        #we'll restrict the tests to the more interesting ones.
        most_options = ['-r', '-x', '--cue', '--replay-gain',
                        '--name', '--artist', '--album',
                        '--number', '--track-total',
                        '--album-number', '--album-total',
                        '--comment', '--comment-file',
                        '--remove-images', '--front-cover', '--back-cover',
                        '-T']

        for count in xrange(1, len(most_options) + 1):
            for options in Combinations(most_options, count):
                f = open(self.track_file.name, 'wb')
                f.write(self.track_data)
                f.close()

                options = self.populate_options(options)
                print options
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

                        
                #FIXME - check --replay-gain option
