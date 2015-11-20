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
import tempfile

from test import (parser, BLANK_PCM_Reader, EXACT_SILENCE_PCM_Reader,
                  Combinations,
                  TEST_COVER1, TEST_COVER2, TEST_COVER3, TEST_COVER4,
                  HUGE_BMP)


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


class MetaDataTest(unittest.TestCase):
    def setUp(self):
        self.metadata_class = audiotools.MetaData
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "catalog",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "date",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = []

    def empty_metadata(self):
        return self.metadata_class()

    @METADATA_METADATA
    def test_roundtrip(self):
        for audio_class in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX) as temp_file:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))
                metadata = self.empty_metadata()
                setattr(metadata, self.supported_fields[0], u"Foo")
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertIsInstance(metadata2, self.metadata_class)

                # also ensure that the new track is playable
                audiotools.transfer_framelist_data(track.to_pcm(),
                                                   lambda f: f)

    @METADATA_METADATA
    def test_attribs(self):
        import sys
        import string
        import random

        # a nice sampling of Unicode characters
        chars = u"".join([u"".join(map(chr if (sys.version_info[0] >= 3)
                                       else unichr, l))
                          for l in [range(0x30, 0x39 + 1),
                                    range(0x41, 0x5A + 1),
                                    range(0x61, 0x7A + 1),
                                    range(0xC0, 0x17E + 1),
                                    range(0x18A, 0x1EB + 1),
                                    range(0x3041, 0x3096 + 1),
                                    range(0x30A1, 0x30FA + 1)]])

        for audio_class in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as temp_file:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                # check that setting the fields to random values works
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    if field_type is type(u""):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in range(random.choice(range(1, 21)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    elif field_type is int:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)
                    elif field_type is bool:
                        value = random.choice([False, True])
                        setattr(metadata, field, value)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), value)

                # check that blanking out the fields works
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    self.assertIsNone(getattr(metadata, field))
                    if field_type is type(u""):
                        setattr(metadata, field, u"")
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), u"")
                    elif field_type is int:
                        setattr(metadata, field, None)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        if metadata is not None:
                            self.assertIsNone(getattr(metadata, field))
                    elif field_type is bool:
                        setattr(metadata, field, None)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        if metadata is not None:
                            self.assertIsNone(getattr(metadata, field))

                # re-set the fields with random values
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    if field_type is type(u""):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in range(random.choice(range(1, 21)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    elif field_type is int:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)
                    elif field_type is bool:
                        value = random.choice([False, True])
                        setattr(metadata, field, value)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), value)

                    # check that deleting the fields works
                    delattr(metadata, field)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    if metadata is not None:
                        self.assertEqual(
                            getattr(metadata, field),
                            None,
                            "{!r} != {} for field {}".format(
                                getattr(metadata, field), None, field))

                # check an unsupported field
                metadata = self.empty_metadata()
                self.assertRaises(AttributeError,
                                  getattr,
                                  metadata,
                                  "foo")

                metadata.foo = u"foo"
                self.assertEqual(metadata.foo, u"foo")
                metadata.foo = u"bar"
                self.assertEqual(metadata.foo, u"bar")

                del(metadata.foo)
                self.assertRaises(AttributeError,
                                  getattr,
                                  metadata,
                                  "foo")

    @METADATA_METADATA
    def test_field_mapping(self):
        # ensure that setting a class field
        # updates its corresponding low-level implementation

        # ensure that updating the low-level implementation
        # is reflected in the class field

        pass

    @METADATA_METADATA
    def test_foreign_field(self):
        pass

    @METADATA_METADATA
    def test_converted(self):
        # build a generic MetaData with everything
        image1 = audiotools.Image.new(TEST_COVER1, u"Text 1", 0)
        image2 = audiotools.Image.new(TEST_COVER2, u"Text 2", 1)
        image3 = audiotools.Image.new(TEST_COVER3, u"Text 3", 2)

        metadata_orig = audiotools.MetaData(track_name=u"a",
                                            track_number=1,
                                            track_total=2,
                                            album_name=u"b",
                                            artist_name=u"c",
                                            performer_name=u"d",
                                            composer_name=u"e",
                                            conductor_name=u"f",
                                            media=u"g",
                                            ISRC=u"h",
                                            catalog=u"i",
                                            copyright=u"j",
                                            publisher=u"k",
                                            year=u"l",
                                            date=u"m",
                                            album_number=3,
                                            album_total=4,
                                            comment=u"n",
                                            images=[image1, image2, image3])

        # ensure converted() builds something with our class
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new.__class__, self.metadata_class)

        # ensure our fields match
        for field in audiotools.MetaData.FIELDS:
            if field in self.supported_fields:
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            else:
                self.assertIsNone(getattr(metadata_new, field))

        # ensure images match, if supported
        if self.metadata_class.supports_images():
            self.assertEqual(metadata_new.images(),
                             [image1, image2, image3])

        # subclasses should ensure non-MetaData fields are converted

        # ensure that convert() builds a whole new object
        metadata_new.track_name = u"Foo"
        self.assertEqual(metadata_new.track_name, u"Foo")
        metadata_new2 = self.metadata_class.converted(metadata_new)
        self.assertEqual(metadata_new2.track_name, u"Foo")
        metadata_new2.track_name = u"Bar"
        self.assertEqual(metadata_new2.track_name, u"Bar")
        self.assertEqual(metadata_new.track_name, u"Foo")

    @METADATA_METADATA
    def test_supports_images(self):
        self.assertEqual(self.metadata_class.supports_images(), True)

    @METADATA_METADATA
    def test_images(self):
        # perform tests only if images are actually supported
        if self.metadata_class.supports_images():
            for audio_class in self.supported_formats:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)
                try:
                    track = audio_class.from_pcm(temp_file.name,
                                                 BLANK_PCM_Reader(1))

                    metadata = self.empty_metadata()
                    self.assertEqual(metadata.images(), [])

                    image1 = audiotools.Image.new(TEST_COVER1,
                                                  u"Text 1", 0)
                    image2 = audiotools.Image.new(TEST_COVER2,
                                                  u"Text 2", 1)
                    image3 = audiotools.Image.new(TEST_COVER3,
                                                  u"Text 3", 2)

                    track.set_metadata(metadata)
                    metadata = track.get_metadata()

                    # ensure that adding one image works
                    metadata.add_image(image1)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertIn(image1, metadata.images())
                    self.assertNotIn(image2, metadata.images())
                    self.assertNotIn(image3, metadata.images())

                    # ensure that adding a second image works
                    metadata.add_image(image2)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertIn(image1, metadata.images())
                    self.assertIn(image2, metadata.images())
                    self.assertNotIn(image3, metadata.images())

                    # ensure that adding a third image works
                    metadata.add_image(image3)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertIn(image1, metadata.images())
                    self.assertIn(image2, metadata.images())
                    self.assertIn(image3, metadata.images())

                    # ensure that deleting the first image works
                    metadata.delete_image(image1)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertNotIn(image1, metadata.images())
                    self.assertIn(image2, metadata.images())
                    self.assertIn(image3, metadata.images())

                    # ensure that deleting the second image works
                    metadata.delete_image(image2)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertNotIn(image1, metadata.images())
                    self.assertNotIn(image2, metadata.images())
                    self.assertIn(image3, metadata.images())

                    # ensure that deleting the third image works
                    metadata.delete_image(image3)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertNotIn(image1, metadata.images())
                    self.assertNotIn(image2, metadata.images())
                    self.assertNotIn(image3, metadata.images())

                finally:
                    temp_file.close()

    @METADATA_METADATA
    def test_mode(self):
        import os

        # ensure that setting, updating and deleting metadata
        # doesn't change the file's original mode
        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                mode = 0o755
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))
                original_mode = os.stat(track.filename).st_mode

                os.chmod(track.filename, mode)
                # may not round-trip as expected on some systems
                mode = os.stat(track.filename).st_mode
                self.assertNotEqual(mode, original_mode)

                metadata = self.empty_metadata()
                metadata.track_name = u"Test 1"
                track.set_metadata(metadata)

                self.assertEqual(os.stat(track.filename).st_mode, mode)

                metadata = track.get_metadata()
                metadata.track_name = u"Test 2"
                track.update_metadata(metadata)

                self.assertEqual(os.stat(track.filename).st_mode, mode)

                track.delete_metadata()

                self.assertEqual(os.stat(track.filename).st_mode, mode)
            finally:
                temp_file.close()

    @METADATA_METADATA
    def test_delete_metadata(self):
        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                self.assertTrue((track.get_metadata() is None) or
                                (track.get_metadata().track_name is None))

                track.set_metadata(
                    audiotools.MetaData(track_name=u"Track Name"))
                self.assertEqual(track.get_metadata().track_name,
                                 u"Track Name")

                track.delete_metadata()
                self.assertTrue((track.get_metadata() is None) or
                                (track.get_metadata().track_name is None))

                track.set_metadata(
                    audiotools.MetaData(track_name=u"Track Name"))
                self.assertEqual(track.get_metadata().track_name,
                                 u"Track Name")

                track.set_metadata(None)
                self.assertTrue((track.get_metadata() is None) or
                                (track.get_metadata().track_name is None))
            finally:
                temp_file.close()

    @METADATA_METADATA
    def test_raw_info(self):
        import sys

        if sys.version_info[0] >= 3:
            __unicode__ = str
        else:
            __unicode__ = unicode

        if self.metadata_class is audiotools.MetaData:
            return

        # ensure raw_info() returns a Unicode object
        # and has at least some output

        metadata = self.empty_metadata()
        for field in self.supported_fields:
            field_type = audiotools.MetaData.FIELD_TYPES[field]
            if field_type is type(u""):
                setattr(metadata, field, u"A" * 5)
            elif field_type is int:
                setattr(metadata, field, 1)
            elif field_type is bool:
                setattr(metadata, field, True)
        raw_info = metadata.raw_info()
        self.assertIsInstance(raw_info, __unicode__)
        self.assertGreater(len(raw_info), 0)

    @LIB_CUESHEET
    @METADATA_METADATA
    def test_cuesheet(self):
        for audio_class in self.supported_formats:
            if not audio_class.supports_cuesheet():
                continue

            from audiotools import Sheet, SheetTrack, SheetIndex
            from fractions import Fraction

            sheet = Sheet(sheet_tracks=[
                          SheetTrack(
                              number=1,
                              track_indexes=[
                                  SheetIndex(number=1,
                                             offset=Fraction(0, 1))],
                              filename=u"CDImage.wav"),
                          SheetTrack(
                              number=2,
                              track_indexes=[
                                  SheetIndex(number=0,
                                             offset=Fraction(4507, 25)),
                                  SheetIndex(number=1,
                                             offset=Fraction(4557, 25))],
                              filename=u"CDImage.wav"),
                          SheetTrack(
                              number=3,
                              track_indexes=[
                                  SheetIndex(number=0,
                                             offset=Fraction(27013, 75)),
                                  SheetIndex(number=1,
                                             offset=Fraction(27161, 75))],
                              filename=u"CDImage.wav"),
                          SheetTrack(
                              number=4,
                              track_indexes=[
                                  SheetIndex(number=0,
                                             offset=Fraction(37757, 75)),
                                  SheetIndex(number=1,
                                             offset=Fraction(37907, 75))],
                              filename=u"CDImage.wav"),
                          SheetTrack(
                              number=5,
                              track_indexes=[
                                  SheetIndex(number=0,
                                             offset=Fraction(11213, 15)),
                                  SheetIndex(number=1,
                                             offset=Fraction(11243, 15))],
                              filename=u"CDImage.wav"),
                          SheetTrack(
                              number=6,
                              track_indexes=[
                                  SheetIndex(number=0,
                                             offset=Fraction(13081, 15)),
                                  SheetIndex(number=1,
                                             offset=Fraction(13111, 15))],
                              filename=u"CDImage.wav")])

            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as temp_file:
                # build empty audio file
                temp_track = audio_class.from_pcm(
                    temp_file.name,
                    EXACT_SILENCE_PCM_Reader(43646652),
                    total_pcm_frames=43646652)

                # ensure it has no cuesheet
                self.assertIsNone(temp_track.get_cuesheet())

                # set cuesheet
                temp_track.set_cuesheet(sheet)

                # ensure its cuesheet matches the original
                track_sheet = temp_track.get_cuesheet()
                self.assertIsNotNone(track_sheet)
                self.assertEqual(track_sheet, sheet)

                # deleting cuesheet should delete cuesheet
                temp_track.delete_cuesheet()
                self.assertIsNone(temp_track.get_cuesheet())

                # setting cuesheet to None should delete cuesheet
                temp_track.set_cuesheet(sheet)
                self.assertEqual(temp_track.get_cuesheet(), sheet)
                temp_track.set_cuesheet(None)
                self.assertIsNone(temp_track.get_cuesheet())

    @LIB_CUESHEET
    @METADATA_METADATA
    def test_metadata_independence(self):
        from audiotools import Sheet, SheetTrack, SheetIndex
        from fractions import Fraction

        metadata = audiotools.MetaData(track_name=u"Track Name",
                                       track_number=1)

        replay_gain = audiotools.ReplayGain(track_gain=2.0,
                                            track_peak=0.25,
                                            album_gain=1.0,
                                            album_peak=0.5)

        sheet = Sheet(sheet_tracks=[
                      SheetTrack(
                          number=1,
                          track_indexes=[
                              SheetIndex(number=1,
                                         offset=Fraction(0, 1))],
                          filename=u"CDImage.wav"),
                      SheetTrack(
                          number=2,
                          track_indexes=[
                              SheetIndex(number=0,
                                         offset=Fraction(4507, 25)),
                              SheetIndex(number=1,
                                         offset=Fraction(4557, 25))],
                          filename=u"CDImage.wav"),
                      SheetTrack(
                          number=3,
                          track_indexes=[
                              SheetIndex(number=0,
                                         offset=Fraction(27013, 75)),
                              SheetIndex(number=1,
                                         offset=Fraction(27161, 75))],
                          filename=u"CDImage.wav"),
                      SheetTrack(
                          number=4,
                          track_indexes=[
                              SheetIndex(number=0,
                                         offset=Fraction(37757, 75)),
                              SheetIndex(number=1,
                                         offset=Fraction(37907, 75))],
                          filename=u"CDImage.wav"),
                      SheetTrack(
                          number=5,
                          track_indexes=[
                              SheetIndex(number=0,
                                         offset=Fraction(11213, 15)),
                              SheetIndex(number=1,
                                         offset=Fraction(11243, 15))],
                          filename=u"CDImage.wav"),
                      SheetTrack(
                          number=6,
                          track_indexes=[
                              SheetIndex(number=0,
                                         offset=Fraction(13081, 15)),
                              SheetIndex(number=1,
                                         offset=Fraction(13111, 15))],
                          filename=u"CDImage.wav")])

        for audio_class in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as temp_file:
                if audio_class.supports_cuesheet():
                    track = audio_class.from_pcm(
                        temp_file.name,
                        EXACT_SILENCE_PCM_Reader(43646652),
                        total_pcm_frames=43646652)
                else:
                    track = audio_class.from_pcm(
                        temp_file.name,
                        EXACT_SILENCE_PCM_Reader(44100 * 5),
                        total_pcm_frames=44100 * 5)

                self.assertTrue(
                    (track.get_metadata() is None) or
                    ((track.get_metadata().track_name is None) and
                     (track.get_metadata().track_number is None)))

                # if class supports metadata
                if audio_class.supports_metadata():
                    # setting metadata should work
                    track.set_metadata(metadata)
                    self.assertEqual(track.get_metadata(), metadata)

                    # and deleting metadata should work
                    track.delete_metadata()

                    # note that some classes can't delete metadata
                    # entirely since it contains non-textual data
                    self.assertTrue(
                        (track.get_metadata() is None) or
                        ((track.get_metadata().track_name is None) and
                         (track.get_metadata().track_number is None)))

                    track.set_metadata(metadata)
                    self.assertEqual(track.get_metadata(), metadata)
                    track.set_metadata(None)
                    self.assertTrue(
                        (track.get_metadata() is None) or
                        ((track.get_metadata().track_name is None) and
                         (track.get_metadata().track_number is None)))
                else:
                    # otherwise they should do nothing
                    track.set_metadata(metadata)
                    self.assertTrue(
                        (track.get_metadata() is None) or
                        ((track.get_metadata().track_name is None) and
                         (track.get_metadata().track_number is None)))

                    track.delete_metadata()
                    self.assertTrue(
                        (track.get_metadata() is None) or
                        ((track.get_metadata().track_name is None) and
                         (track.get_metadata().track_number is None)))

                    track.set_metadata(None)
                    self.assertTrue(
                        (track.get_metadata() is None) or
                        ((track.get_metadata().track_name is None) and
                         (track.get_metadata().track_number is None)))

                self.assertIsNone(track.get_replay_gain())

                # if class supports ReplayGain
                if audio_class.supports_replay_gain():
                    # setting ReplayGain should work
                    track.set_replay_gain(replay_gain)
                    self.assertEqual(track.get_replay_gain(), replay_gain)

                    # and deleting ReplayGain should work
                    track.delete_replay_gain()
                    self.assertIsNone(track.get_replay_gain())

                    track.set_replay_gain(replay_gain)
                    self.assertEqual(track.get_replay_gain(), replay_gain)
                    track.set_replay_gain(None)
                    self.assertIsNone(track.get_replay_gain())
                else:
                    # otherwise they should do nothing
                    track.set_replay_gain(replay_gain)
                    self.assertIsNone(track.get_replay_gain())

                    track.delete_replay_gain()
                    self.assertIsNone(track.get_replay_gain())

                    track.set_replay_gain(None)
                    self.assertIsNone(track.get_replay_gain())

                self.assertIsNone(track.get_cuesheet())

                # if class supports cuesheets
                if audio_class.supports_cuesheet():
                    # setting cuesheet should work
                    track.set_cuesheet(sheet)
                    self.assertEqual(track.get_cuesheet(), sheet)

                    # and deleting cuesheet should work
                    track.delete_cuesheet()
                    self.assertIsNone(track.get_cuesheet())

                    track.set_cuesheet(sheet)
                    self.assertEqual(track.get_cuesheet(), sheet)
                    track.set_cuesheet(None)
                    self.assertIsNone(track.get_cuesheet())
                else:
                    # otherwise they should do nothing
                    track.set_cuesheet(sheet)
                    self.assertIsNone(track.get_cuesheet())

                    track.delete_cuesheet()
                    self.assertIsNone(track.get_cuesheet())

                    track.set_cuesheet(None)
                    self.assertIsNone(track.get_cuesheet())

                # deleting metadata doesn't affect
                # ReplayGain or embedded cuesheet (if supported)
                track.set_metadata(metadata)
                track.set_replay_gain(replay_gain)
                track.set_cuesheet(sheet)
                track.delete_metadata()
                if track.supports_replay_gain():
                    self.assertEqual(track.get_replay_gain(), replay_gain)
                else:
                    self.assertIsNone(track.get_replay_gain())
                if track.supports_cuesheet():
                    self.assertEqual(track.get_cuesheet(), sheet)
                else:
                    self.assertIsNone(track.get_cuesheet())

                # deleting ReplayGain doesn't affect
                # metadata or embedded cuesheet (if supported)
                track.set_metadata(metadata)
                track.set_replay_gain(replay_gain)
                track.set_cuesheet(sheet)
                track.delete_replay_gain()
                if track.supports_metadata():
                    self.assertEqual(track.get_metadata(), metadata)
                else:
                    self.assertIsNone(track.get_metadata())
                if track.supports_cuesheet():
                    self.assertEqual(track.get_cuesheet(), sheet)
                else:
                    self.assertIsNone(track.get_cuesheet())

                # deleting cuesheet doesn't affect
                # metadata or ReplayGain (if supported)
                track.set_metadata(metadata)
                track.set_replay_gain(replay_gain)
                track.set_cuesheet(sheet)
                track.delete_cuesheet()
                if track.supports_metadata():
                    self.assertEqual(track.get_metadata(), metadata)
                else:
                    self.assertIsNone(track.get_metadata())
                if track.supports_replay_gain():
                    self.assertEqual(track.get_replay_gain(), replay_gain)
                else:
                    self.assertIsNone(track.get_replay_gain())

    @METADATA_METADATA
    def test_converted_duplication(self):
        # ensure the converting a metadata object to its own class
        # doesn't share the same fields as the original object
        # so that updating one doesn't update the other
        metadata1 = self.metadata_class.converted(
            audiotools.MetaData(track_name=u"Track Name 1",
                                track_number=1))

        if self.metadata_class.supports_images():
            metadata1.add_image(audiotools.Image.new(TEST_COVER1,
                                                     u"",
                                                     audiotools.FRONT_COVER))

        metadata2 = self.metadata_class.converted(metadata1)
        self.assertIsNotNone(metadata2)
        self.assertIsInstance(metadata2, self.metadata_class)

        self.assertEqual(metadata1.track_name, metadata2.track_name)
        self.assertEqual(metadata1.track_number, metadata2.track_number)
        self.assertEqual(metadata1.images(), metadata2.images())

        metadata2.track_name = u"Track Name 2"
        metadata2.track_number = 2
        self.assertNotEqual(metadata1.track_name, metadata2.track_name)
        self.assertNotEqual(metadata1.track_number, metadata2.track_number)
        if self.metadata_class.supports_images():
            metadata2.delete_image(metadata2.images()[0])
            self.assertNotEqual(metadata1.images(), metadata2.images())

    @METADATA_METADATA
    def test_converted_none(self):
        self.assertIsNone(self.metadata_class.converted(None))

    @METADATA_METADATA
    def test_intersection(self):
        # get metadata in our class and set some fields
        base = self.empty_metadata()
        base.track_name = u"Name 1"
        base.track_number = 1
        self.assertEqual(base.track_name, u"Name 1")
        self.assertEqual(base.track_number, 1)

        # test against None
        self.assertIsNone(base.intersection(None))

        # test against no intersecting fields
        no_matches = audiotools.MetaData(album_name=u"Name 2",
                                         artist_name=u"Name 3")
        test = base.intersection(no_matches)
        self.assertIs(type(test), audiotools.MetaData)
        self.assertEqual(set(test.filled_fields()), set())

        no_matches = self.empty_metadata()
        no_matches.album_name = u"Name 2"
        no_matches.artist_name = u"Name 3"
        test = base.intersection(no_matches)
        self.assertIs(type(test), type(base))
        self.assertEqual(set(test.filled_fields()), set())

        no_matches = audiotools.MetaData(track_name=u"Name 2",
                                         track_number=2)
        test = base.intersection(no_matches)
        self.assertIs(type(test), audiotools.MetaData)
        self.assertEqual(set(test.filled_fields()), set())

        no_matches = self.empty_metadata()
        no_matches.track_name = u"Name 2"
        no_matches.track_number = 2
        test = base.intersection(no_matches)
        self.assertIs(type(test), type(base))
        self.assertEqual(set(test.filled_fields()), set())

        # test against some intersecting fields
        some_matches = audiotools.MetaData(track_name=u"Name 1",
                                           album_name=u"Name 2")
        test = base.intersection(some_matches)
        self.assertIs(type(test), audiotools.MetaData)
        self.assertEqual(set(test.filled_fields()),
                         {("track_name", u"Name 1")})

        some_matches = self.empty_metadata()
        some_matches.track_name = u"Name 1"
        some_matches.album_name = u"Name 2"
        test = base.intersection(some_matches)
        self.assertIs(type(test), type(base))
        self.assertEqual(set(test.filled_fields()),
                         {("track_name", u"Name 1")})

        some_matches = audiotools.MetaData(track_name=u"Name 2",
                                           track_number=1)
        test = base.intersection(some_matches)
        self.assertIs(type(test), audiotools.MetaData)
        self.assertEqual(set(test.filled_fields()),
                         {("track_number", 1)})

        some_matches = self.empty_metadata()
        some_matches.track_name = u"Name 2"
        some_matches.track_number = 1
        test = base.intersection(some_matches)
        self.assertIs(type(test), type(base))
        self.assertEqual(set(test.filled_fields()),
                         {("track_number", 1)})

        # test against all intersecting fields
        all_matches = audiotools.MetaData(track_name=u"Name 1",
                                          track_number=1)
        test = base.intersection(all_matches)
        self.assertIs(type(test), audiotools.MetaData)
        self.assertEqual(set(test.filled_fields()),
                         {("track_name", u"Name 1"),
                          ("track_number", 1)})

        test = base.intersection(base)
        self.assertIs(type(test), type(base))
        self.assertTrue(test is not base)
        self.assertEqual(set(test.filled_fields()),
                         {("track_name", u"Name 1"),
                          ("track_number", 1)})

        # test against intersecting images (if applicable)
        if self.metadata_class.supports_images():
            img1 = audiotools.Image.new(TEST_COVER1,
                                        u"",
                                        audiotools.FRONT_COVER)

            img2 = audiotools.Image.new(TEST_COVER2,
                                        u"",
                                        audiotools.FRONT_COVER)

            img3 = audiotools.Image.new(TEST_COVER3,
                                        u"",
                                        audiotools.BACK_COVER)

            base = self.empty_metadata()
            base.add_image(img1)
            self.assertEqual(base.images(), [img1])

            # test against no matching images
            no_matches = audiotools.MetaData()
            self.assertEqual(no_matches.images(), [])
            test = base.intersection(no_matches)
            self.assertIs(type(test), audiotools.MetaData)
            self.assertEqual(test.images(), [])

            no_matches = self.empty_metadata()
            self.assertEqual(no_matches.images(), [])
            test = base.intersection(no_matches)
            self.assertIs(type(test), type(base))
            self.assertEqual(test.images(), [])

            no_matches = audiotools.MetaData()
            no_matches.add_image(img2)
            self.assertEqual(no_matches.images(), [img2])
            test = base.intersection(no_matches)
            self.assertIs(type(test), audiotools.MetaData)
            self.assertEqual(test.images(), [])

            no_matches = self.empty_metadata()
            no_matches.add_image(img2)
            self.assertEqual(no_matches.images(), [img2])
            test = base.intersection(no_matches)
            self.assertIs(type(test), type(base))
            self.assertEqual(test.images(), [])

            # test against some matching images (if possible)
            base2 = self.empty_metadata()
            base2.add_image(img1)
            base2.add_image(img2)
            if len(base2.images()) > 1:
                self.assertEqual(base2.images(), [img1, img2])

                some_matches = audiotools.MetaData()
                some_matches.add_image(img2)
                some_matches.add_image(img3)
                self.assertEqual(some_matches.images(), [img2, img3])
                test = base2.intersection(some_matches)
                self.assertIs(type(test), audiotools.MetaData)
                self.assertEqual(test.images(), [img2])

                some_matches = self.empty_metadata()
                some_matches.add_image(img2)
                some_matches.add_image(img3)
                self.assertEqual(some_matches.images(), [img2, img3])
                test = base2.intersection(some_matches)
                self.assertIs(type(test), type(base2))
                self.assertEqual(test.images(), [img2])

            # test against all matching images
            all_matches = audiotools.MetaData()
            all_matches.add_image(img1)
            self.assertEqual(all_matches.images(), [img1])
            test = base.intersection(all_matches)
            self.assertIs(type(test), audiotools.MetaData)
            self.assertEqual(test.images(), [img1])

            all_matches = self.empty_metadata()
            all_matches.add_image(img1)
            self.assertEqual(all_matches.images(), [img1])
            test = base.intersection(all_matches)
            self.assertIs(type(test), type(base))
            self.assertEqual(test.images(), [img1])


class WavPackApeTagMetaData(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.ApeTag
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "ISRC",
                                 "catalog",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "date",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.WavPackAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_WAVPACK
    def test_getitem(self):
        from audiotools.ape import ApeTag, ApeTagItem

        # getitem with no matches raises KeyError
        self.assertRaises(KeyError, ApeTag([]).__getitem__, b"Title")

        # getitem with one match returns that item
        self.assertEqual(ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])[b"Foo"],
                         ApeTagItem(0, 0, b"Foo", b"Bar"))

        # getitem with multiple matches returns the first match
        # (this is not a valid ApeTag and should be cleaned)
        self.assertEqual(ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar"),
                                 ApeTagItem(0, 0, b"Foo", b"Baz")])[b"Foo"],
                         ApeTagItem(0, 0, b"Foo", b"Bar"))

        # tag items *are* case-sensitive according to the specification
        self.assertRaises(
            KeyError,
            ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")]).__getitem__,
            b"foo")

    @METADATA_WAVPACK
    def test_setitem(self):
        from audiotools.ape import ApeTag, ApeTagItem

        # setitem adds new key if necessary
        metadata = ApeTag([])
        metadata[b"Foo"] = ApeTagItem(0, 0, b"Foo", b"Bar")
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Bar")])

        # setitem replaces matching key with new value
        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])
        metadata[b"Foo"] = ApeTagItem(0, 0, b"Foo", b"Baz")
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Baz")])

        # setitem leaves other items alone
        # when adding or replacing tags
        metadata = ApeTag([ApeTagItem(0, 0, b"Kelp", b"Spam")])
        metadata[b"Foo"] = ApeTagItem(0, 0, b"Foo", b"Bar")
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Kelp", b"Spam"),
                          ApeTagItem(0, 0, b"Foo", b"Bar")])

        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar"),
                           ApeTagItem(0, 0, b"Kelp", b"Spam")])
        metadata[b"Foo"] = ApeTagItem(0, 0, b"Foo", b"Baz")
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Baz"),
                          ApeTagItem(0, 0, b"Kelp", b"Spam")])

        # setitem is case-sensitive
        metadata = ApeTag([ApeTagItem(0, 0, b"foo", b"Spam")])
        metadata[b"Foo"] = ApeTagItem(0, 0, b"Foo", b"Bar")
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"foo", b"Spam"),
                          ApeTagItem(0, 0, b"Foo", b"Bar")])

    @METADATA_WAVPACK
    def test_getattr(self):
        from audiotools.ape import ApeTag, ApeTagItem

        # track_number grabs the first available integer from "Track"
        self.assertIsNone(ApeTag([]).track_number)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Track", b"2")]).track_number,
            2)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Track", b"2/3")]).track_number,
            2)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Track", b"foo 2 bar")]).track_number,
            2)

        # album_number grabs the first available from "Media"
        self.assertIsNone(ApeTag([]).album_number)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Media", b"4")]).album_number,
            4)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Media", b"4/5")]).album_number,
            4)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Media", b"foo 4 bar")]).album_number,
            4)

        # track_total grabs the second number in a slashed field, if any
        self.assertIsNone(ApeTag([]).track_total)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Track", b"2")]).track_total,
            None)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Track", b"2/3")]).track_total,
            3)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0,
                               b"Track",
                               b"foo 2 bar / baz 3 blah")]).track_total,
            3)

        # album_total grabs the second number in a slashed field, if any
        self.assertIsNone(ApeTag([]).album_total)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Media", b"4")]).album_total,
            None)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Media", b"4/5")]).album_total,
            5)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0,
                               b"Media",
                               b"foo 4 bar / baz 5 blah")]).album_total,
            5)

        # other fields grab the first available item
        # (though proper APEv2 tags should only contain one)
        self.assertEqual(ApeTag([]).track_name,
                         None)

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Title", b"foo")]).track_name,
            u"foo")

        self.assertEqual(
            ApeTag([ApeTagItem(0, 0, b"Title", b"foo"),
                    ApeTagItem(0, 0, b"Title", b"bar")]).track_name,
            u"foo")

    @METADATA_WAVPACK
    def test_setattr(self):
        from audiotools.ape import ApeTag, ApeTagItem

        # track_number adds new field if necessary
        metadata = ApeTag([])
        metadata.track_number = 2
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"2")])
        self.assertEqual(metadata.track_number, 2)

        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])
        metadata.track_number = 2
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Bar"),
                          ApeTagItem(0, 0, b"Track", b"2")])
        self.assertEqual(metadata.track_number, 2)

        # track_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1")])
        metadata.track_number = 2
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"2")])
        self.assertEqual(metadata.track_number, 2)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1/3")])
        metadata.track_number = 2
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"2/3")])
        self.assertEqual(metadata.track_number, 2)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"foo 1 bar")])
        metadata.track_number = 2
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"foo 2 bar")])
        self.assertEqual(metadata.track_number, 2)

        # album_number adds new field if necessary
        metadata = ApeTag([])
        metadata.album_number = 4
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"4")])
        self.assertEqual(metadata.album_number, 4)

        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])
        metadata.album_number = 4
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Bar"),
                          ApeTagItem(0, 0, b"Media", b"4")])
        self.assertEqual(metadata.album_number, 4)

        # album_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3")])
        metadata.album_number = 4
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"4")])
        self.assertEqual(metadata.album_number, 4)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3/5")])
        metadata.album_number = 4
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"4/5")])
        self.assertEqual(metadata.album_number, 4)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"foo 3 bar")])
        metadata.album_number = 4
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"foo 4 bar")])
        self.assertEqual(metadata.album_number, 4)

        # track_total adds a new field if necessary
        metadata = ApeTag([])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"0/3")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Bar"),
                          ApeTagItem(0, 0, b"Track", b"0/3")])
        self.assertEqual(metadata.track_total, 3)

        # track_total adds a slashed side of the integer field
        # and leaves other junk in that field alone
        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"1/3")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1  ")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"1  /3")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1/2")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"1/3")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1 / baz 2 blah")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"1 / baz 3 blah")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track",
                                      b"foo 1 bar / baz 2 blah")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track",
                                     b"foo 1 bar / baz 3 blah")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1 / 2 / 4")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"1 / 3 / 4")])
        self.assertEqual(metadata.track_total, 3)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"foo / 2")])
        metadata.track_total = 3
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"foo / 3")])
        self.assertEqual(metadata.track_total, 3)

        # album_total adds a new field if necessary
        metadata = ApeTag([])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"0/5")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Bar"),
                          ApeTagItem(0, 0, b"Media", b"0/5")])
        self.assertEqual(metadata.album_total, 5)

        # album_total adds a slashed side of the integer field
        # and leaves other junk in that field alone
        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"3/5")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3  ")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"3  /5")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3/4")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"3/5")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"1 / baz 2 blah")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"1 / baz 5 blah")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media",
                                      b"foo 1 bar / baz 2 blah")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media",
                                     b"foo 1 bar / baz 5 blah")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3 / 4 / 6")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"3 / 5 / 6")])
        self.assertEqual(metadata.album_total, 5)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"foo / 4")])
        metadata.album_total = 5
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"foo / 5")])
        self.assertEqual(metadata.album_total, 5)

        # other fields add a new item if necessary
        # while leaving the rest alone
        metadata = ApeTag([])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Title", b"Track Name")])
        self.assertEqual(metadata.track_name, u"Track Name")

        metadata = ApeTag([ApeTagItem(0, 0, b"Foo", b"Bar")])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Foo", b"Bar"),
                          ApeTagItem(0, 0, b"Title", b"Track Name")])
        self.assertEqual(metadata.track_name, u"Track Name")

        # other fields update the first match
        # while leaving the rest alone
        metadata = ApeTag([ApeTagItem(0, 0, b"Title", b"Blah")])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Title", b"Track Name")])
        self.assertEqual(metadata.track_name, u"Track Name")

        metadata = ApeTag([ApeTagItem(0, 0, b"Title", b"Blah"),
                           ApeTagItem(0, 0, b"Title", b"Spam")])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Title", b"Track Name"),
                          ApeTagItem(0, 0, b"Title", b"Spam")])
        self.assertEqual(metadata.track_name, u"Track Name")

        # setting field to an empty string is okay
        metadata = ApeTag([])
        metadata.track_name = u""
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Title", b"")])
        self.assertEqual(metadata.track_name, u"")

    @METADATA_WAVPACK
    def test_delattr(self):
        from audiotools.ape import ApeTag, ApeTagItem

        # deleting nonexistent field is okay
        for field in audiotools.MetaData.FIELDS:
            metadata = ApeTag([])
            delattr(metadata, field)
            self.assertIsNone(getattr(metadata, field))

        # deleting field removes all instances of it
        metadata = ApeTag([])
        del(metadata.track_name)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_name)

        metadata = ApeTag([ApeTagItem(0, 0, b"Title", b"Track Name")])
        del(metadata.track_name)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_name)

        metadata = ApeTag([ApeTagItem(0, 0, b"Title", b"Track Name"),
                           ApeTagItem(0, 0, b"Title", b"Track Name 2")])
        del(metadata.track_name)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_name)

        # setting field to None is the same as deleting field
        metadata = ApeTag([])
        metadata.track_name = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_name)

        metadata = ApeTag([ApeTagItem(0, 0, b"Title", b"Track Name")])
        metadata.track_name = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_name)

        metadata = ApeTag([ApeTagItem(0, 0, b"Title", b"Track Name"),
                           ApeTagItem(0, 0, b"Title", b"Track Name 2")])
        metadata.track_name = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_name)

        # deleting track_number without track_total removes "Track" field
        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1")])
        del(metadata.track_number)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_number)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1")])
        metadata.track_number = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_number)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"foo 1 bar")])
        metadata.track_number = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_number)

        # deleting track_number with track_total converts track_number to 0
        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1/2")])
        del(metadata.track_number)
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Track", b"0/2")])
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1/2")])
        metadata.track_number = None
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Track", b"0/2")])
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track",
                                      b"foo 1 bar / baz 2 blah")])
        metadata.track_number = None
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track",
                                     b"foo 0 bar / baz 2 blah")])
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)

        # deleting track_total without track_number removes "Track" field
        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"0/2")])
        del(metadata.track_total)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_number)
        self.assertIsNone(metadata.track_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"0/2")])
        metadata.track_total = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_number)
        self.assertIsNone(metadata.track_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track",
                                      b"foo 0 bar / baz 2 blah")])
        metadata.track_total = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.track_number)
        self.assertIsNone(metadata.track_total)

        # deleting track_total with track_number removes slashed field
        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1/2")])
        del(metadata.track_total)
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Track", b"1")])
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track", b"1/2/3")])
        del(metadata.track_total)
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Track", b"1")])
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track",
                                      b"foo 1 bar / baz 2 blah")])
        del(metadata.track_total)
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"foo 1 bar")])
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Track",
                                      b"foo 1 bar / baz 2 blah")])
        metadata.track_total = None
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Track", b"foo 1 bar")])
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)

        # deleting album_number without album_total removes "Media" field
        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"0/4")])
        del(metadata.album_total)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"0/4")])
        metadata.album_total = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media",
                                      b"foo 0 bar / baz 4 blah")])
        metadata.album_total = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)

        # deleting album_number with album_total converts album_number to 0
        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3/4")])
        del(metadata.album_number)
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Media", b"0/4")])
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"3/4")])
        metadata.album_number = None
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Media", b"0/4")])
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media",
                                      b"foo 3 bar / baz 4 blah")])
        metadata.album_number = None
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media",
                                     b"foo 0 bar / baz 4 blah")])
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)

        # deleting album_total without album_number removes "Media" field
        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"0/4")])
        del(metadata.album_total)
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"0/4")])
        metadata.album_total = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media",
                                      b"foo 0 bar / baz 4 blah")])
        metadata.album_total = None
        self.assertEqual(metadata.tags, [])
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)

        # deleting album_total with album_number removes slashed field
        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"1/2")])
        del(metadata.album_total)
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Media", b"1")])
        self.assertEqual(metadata.album_number, 1)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media", b"1/2/3")])
        del(metadata.album_total)
        self.assertEqual(metadata.tags, [ApeTagItem(0, 0, b"Media", b"1")])
        self.assertEqual(metadata.album_number, 1)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media",
                                      b"foo 1 bar / baz 2 blah")])
        del(metadata.album_total)
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"foo 1 bar")])
        self.assertEqual(metadata.album_number, 1)
        self.assertIsNone(metadata.album_total)

        metadata = ApeTag([ApeTagItem(0, 0, b"Media",
                                      b"foo 1 bar / baz 2 blah")])
        metadata.album_total = None
        self.assertEqual(metadata.tags,
                         [ApeTagItem(0, 0, b"Media", b"foo 1 bar")])
        self.assertEqual(metadata.album_number, 1)
        self.assertIsNone(metadata.album_total)

    @METADATA_WAVPACK
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as temp_file:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(10))
                temp_file_stat = os.stat(temp_file.name)[0]

                # update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # replaygain strings not updated with set_metadata()
                # but can be updated with update_metadata()
                self.assertRaises(KeyError,
                                  track.get_metadata().__getitem__,
                                  b"replaygain_track_gain")
                metadata[b"replaygain_track_gain"] = \
                    audiotools.ape.ApeTagItem.string(
                        b"replaygain_track_gain", u"???")
                track.set_metadata(metadata)
                self.assertRaises(KeyError,
                                  track.get_metadata().__getitem__,
                                  b"replaygain_track_gain")
                track.update_metadata(metadata)
                self.assertEqual(
                    track.get_metadata()[b"replaygain_track_gain"],
                    audiotools.ape.ApeTagItem.string(
                        b"replaygain_track_gain", u"???"))

                # cuesheet not updated with set_metadata()
                # but can be updated with update_metadata()
                metadata[b"Cuesheet"] = \
                    audiotools.ape.ApeTagItem.string(
                        b"Cuesheet", u"???")
                track.set_metadata(metadata)
                self.assertRaises(KeyError,
                                  track.get_metadata().__getitem__,
                                  b"Cuesheet")
                track.update_metadata(metadata)
                self.assertEqual(
                    track.get_metadata()[b"Cuesheet"],
                    audiotools.ape.ApeTagItem.string(
                        b"Cuesheet", u"???"))

    @METADATA_WAVPACK
    def test_foreign_field(self):
        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem(0, False, b"Title", b'Track Name'),
             audiotools.ape.ApeTagItem(0, False, b"Album", b'Album Name'),
             audiotools.ape.ApeTagItem(0, False, b"Track", b"1/3"),
             audiotools.ape.ApeTagItem(0, False, b"Media", b"2/4"),
             audiotools.ape.ApeTagItem(0, False, b"Foo", b"Bar")])
        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertEqual(metadata, metadata2)
                self.assertEqual(metadata.__class__, metadata2.__class__)
                self.assertEqual(metadata2[b"Foo"].__unicode__(), u"Bar")
            finally:
                temp_file.close()

    @METADATA_WAVPACK
    def test_field_mapping(self):
        mapping = [('track_name', b'Title', u'a'),
                   ('album_name', b'Album', u'b'),
                   ('artist_name', b'Artist', u'c'),
                   ('performer_name', b'Performer', u'd'),
                   ('composer_name', b'Composer', u'e'),
                   ('conductor_name', b'Conductor', u'f'),
                   ('ISRC', b'ISRC', u'g'),
                   ('catalog', b'Catalog', u'h'),
                   ('publisher', b'Publisher', u'i'),
                   ('year', b'Year', u'j'),
                   ('date', b'Record Date', u'k'),
                   ('comment', b'Comment', u'l')]

        for format in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX) as temp_file:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                # ensure that setting a class field
                # updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(metadata[key].__unicode__(), value)
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(metadata2[key].__unicode__(), value)

                # ensure that updating the low-level implementation
                # is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[key] = audiotools.ape.ApeTagItem.string(
                        key, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(metadata[key].__unicode__(), value)
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(metadata[key].__unicode__(), value)

                # ensure that setting numerical fields also
                # updates the low-level implementation
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.track_number = 1
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[b'Track'].__unicode__(), u'1')
                metadata.track_total = 2
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[b'Track'].__unicode__(), u'1/2')
                del(metadata.track_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[b'Track'].__unicode__(), u'1')
                del(metadata.track_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                if metadata is not None:
                    self.assertRaises(KeyError,
                                      metadata.__getitem__,
                                      b'Track')

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.album_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[b'Media'].__unicode__(), u'3')
                metadata.album_total = 4
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[b'Media'].__unicode__(), u'3/4')
                del(metadata.album_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[b'Media'].__unicode__(), u'3')
                del(metadata.album_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                if metadata is not None:
                    self.assertRaises(KeyError,
                                      metadata.__getitem__,
                                      b'Media')

                # and ensure updating the low-level implementation
                # updates the numerical fields
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata[b'Track'] = audiotools.ape.ApeTagItem.string(
                    b'Track', u"1")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 1)
                self.assertIsNone(metadata.track_total)
                metadata[b'Track'] = audiotools.ape.ApeTagItem.string(
                    b'Track', u"1/2")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 1)
                self.assertEqual(metadata.track_total, 2)
                metadata[b'Track'] = audiotools.ape.ApeTagItem.string(
                    b'Track', u"0/2")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertIsNone(metadata.track_number)
                self.assertEqual(metadata.track_total, 2)
                del(metadata[b'Track'])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                if metadata is not None:
                    self.assertIsNone(metadata.track_number)
                    self.assertIsNone(metadata.track_total)

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata[b'Media'] = audiotools.ape.ApeTagItem.string(
                    b'Media', u"3")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 3)
                self.assertIsNone(metadata.album_total)
                metadata[b'Media'] = audiotools.ape.ApeTagItem.string(
                    b'Media', u"3/4")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 3)
                self.assertEqual(metadata.album_total, 4)
                metadata[b'Media'] = audiotools.ape.ApeTagItem.string(
                    b'Media', u"0/4")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertIsNone(metadata.album_number)
                self.assertEqual(metadata.album_total, 4)
                del(metadata[b'Media'])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                if metadata is not None:
                    self.assertIsNone(metadata.album_number)
                    self.assertIsNone(metadata.album_total)

    @METADATA_WAVPACK
    def test_converted(self):
        # build a generic MetaData with everything
        image1 = audiotools.Image.new(TEST_COVER1, u"Text 1", 0)
        image2 = audiotools.Image.new(TEST_COVER2, u"Text 2", 1)

        metadata_orig = audiotools.MetaData(track_name=u"a",
                                            track_number=1,
                                            track_total=2,
                                            album_name=u"b",
                                            artist_name=u"c",
                                            performer_name=u"d",
                                            composer_name=u"e",
                                            conductor_name=u"f",
                                            media=u"g",
                                            ISRC=u"h",
                                            catalog=u"i",
                                            copyright=u"j",
                                            publisher=u"k",
                                            year=u"l",
                                            date=u"m",
                                            album_number=3,
                                            album_total=4,
                                            comment=u"n",
                                            images=[image1, image2])

        # ensure converted() builds something with our class
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new.__class__, self.metadata_class)

        # ensure our fields match
        for field in audiotools.MetaData.FIELDS:
            if field in self.supported_fields:
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            else:
                self.assertIsNone(getattr(metadata_new, field))

        # ensure images match, if supported
        self.assertEqual(metadata_new.images(), [image1, image2])

        # ensure non-MetaData fields are converted
        metadata_orig = self.empty_metadata()
        metadata_orig[b'Foo'] = audiotools.ape.ApeTagItem.string(
            b'Foo', u'Bar')
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_orig[b'Foo'].data,
                         metadata_new[b'Foo'].data)

        # ensure that convert() builds a whole new object
        metadata_new.track_name = u"Foo"
        self.assertEqual(metadata_new.track_name, u"Foo")
        metadata_new2 = self.metadata_class.converted(metadata_new)
        self.assertEqual(metadata_new2.track_name, u"Foo")
        metadata_new2.track_name = u"Bar"
        self.assertEqual(metadata_new2.track_name, u"Bar")
        self.assertEqual(metadata_new.track_name, u"Foo")

    @METADATA_WAVPACK
    def test_images(self):
        for audio_class in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as temp_file:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                metadata = self.empty_metadata()
                self.assertEqual(metadata.images(), [])

                image1 = audiotools.Image.new(TEST_COVER1,
                                              u"Text 1", 0)
                image2 = audiotools.Image.new(TEST_COVER2,
                                              u"Text 2", 1)

                # ensure that adding one image works
                metadata.add_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1])

                # ensure that adding a second image works
                metadata.add_image(image2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1,
                                                     image2])

                # ensure that deleting the first image works
                metadata.delete_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image2])

                # ensure that deleting the second image works
                metadata.delete_image(image2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                if metadata is not None:
                    self.assertEqual(metadata.images(), [])

    @METADATA_WAVPACK
    def test_clean(self):
        from audiotools.ape import ApeTag, ApeTagItem
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_DUPLICATE_TAG,
                                     CLEAN_FIX_TAG_FORMATTING)

        # although the spec says APEv2 tags should be sorted
        # ascending by size, I don't think anybody does this in practice

        # check trailing whitespace
        metadata = ApeTag(
            [ApeTagItem.string(b'Title', u'Foo ')])
        self.assertEqual(metadata.track_name, u'Foo ')
        self.assertEqual(metadata[b'Title'].data, u'Foo '.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": b'Title'.decode('ascii')}])
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(cleaned[b'Title'].data, u'Foo'.encode('utf-8'))

        # check leading whitespace
        metadata = ApeTag(
            [ApeTagItem.string(b'Title', u' Foo')])
        self.assertEqual(metadata.track_name, u' Foo')
        self.assertEqual(metadata[b'Title'].data, u' Foo'.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": b'Title'.decode('ascii')}])
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(cleaned[b'Title'].data, u'Foo'.encode('utf-8'))

        # check empty fields
        metadata = ApeTag(
            [ApeTagItem.string(b'Title', u'')])
        self.assertEqual(metadata.track_name, u'')
        self.assertEqual(metadata[b'Title'].data, u''.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": b'Title'.decode('ascii')}])
        self.assertIsNone(cleaned.track_name)
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          b'Title')

        # check duplicate fields
        metadata = ApeTag(
            [ApeTagItem.string(b'Title', u'Track Name 1'),
             ApeTagItem.string(b'Title', u'Track Name 2')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_DUPLICATE_TAG %
                          {"field": b'Title'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Title', u'Track Name 1')])

        # check fields that differ only by case
        metadata = ApeTag(
            [ApeTagItem.string(b'title', u'Track Name 1'),
             ApeTagItem.string(b'Title', u'Track Name 2')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_DUPLICATE_TAG %
                          {"field": b'Title'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'title', u'Track Name 1')])

        # check leading zeroes
        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'01')])
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata[b'Track'].data, u'01'.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertIsNone(cleaned.track_total)
        self.assertEqual(cleaned[b'Track'].data, u'1'.encode('utf-8'))

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'01/2')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata[b'Track'].data, u'01/2'.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, 2)
        self.assertEqual(cleaned[b'Track'].data, u'1/2'.encode('utf-8'))

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'1/02')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata[b'Track'].data, u'1/02'.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, 2)
        self.assertEqual(cleaned[b'Track'].data, u'1/2'.encode('utf-8'))

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'01/02')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata[b'Track'].data, u'01/02'.encode('utf-8'))
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, 2)
        self.assertEqual(cleaned[b'Track'].data, u'1/2'.encode('utf-8'))

        # check junk in slashed fields
        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'1/foo')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'1')])

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'foo/2')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'0/2')])

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'1/ baz 2 blah')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'1/2')])

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'foo 1 bar /2')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'1/2')])

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'foo 1 bar / baz 2 blah')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'1/2')])

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'1/2/3')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'1/2')])

        metadata = ApeTag(
            [ApeTagItem.string(b'Track', u'1 / 2 / 3')])
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_FIX_TAG_FORMATTING %
                          {"field": b'Track'.decode('ascii')}])
        self.assertEqual(cleaned.tags,
                         [ApeTagItem.string(b'Track', u'1/2')])

        # images don't store metadata,
        # so no need to check their fields

    @METADATA_WAVPACK
    def test_replay_gain(self):
        import test_streams

        for input_class in [audiotools.WavPackAudio]:
            with tempfile.NamedTemporaryFile(
                suffix="." + input_class.SUFFIX) as temp1:
                track1 = input_class.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assertIsNone(
                    track1.get_replay_gain(),
                    "ReplayGain present for class {}".format(input_class.NAME))
                track1.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                audiotools.add_replay_gain([track1])
                self.assertEqual(track1.get_metadata().track_name, u"Foo")
                self.assertIsNotNone(
                    track1.get_replay_gain(),
                    "ReplayGain not present for class {}".format(
                        input_class.NAME))

                for output_class in [audiotools.WavPackAudio]:
                    with tempfile.NamedTemporaryFile(
                        suffix="." + input_class.SUFFIX) as temp2:
                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))

                        # ensure that ReplayGain doesn't get ported
                        # via set_metadata()
                        self.assertIsNone(
                            track2.get_replay_gain(),
                            "ReplayGain present for class {}".format(
                                output_class.NAME))
                        track2.set_metadata(track1.get_metadata())
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Foo")
                        self.assertIsNone(
                            track2.get_replay_gain(),
                            "ReplayGain present for class {} from {}".format(
                                output_class.NAME, input_class.NAME))

                        # and if ReplayGain is already set,
                        # ensure set_metadata() doesn't remove it
                        audiotools.add_replay_gain([track2])
                        old_replay_gain = track2.get_replay_gain()
                        self.assertIsNotNone(old_replay_gain)
                        track2.set_metadata(
                            audiotools.MetaData(track_name=u"Bar"))
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Bar")
                        self.assertEqual(track2.get_replay_gain(),
                                         old_replay_gain)

    @METADATA_WAVPACK
    def test_intersection2(self):
        from audiotools.ape import ApeTag, ApeTagItem

        base = ApeTag([ApeTagItem.string(b"Foo", u"A"),
                       ApeTagItem.string(b"Bar", u"B")])

        # test no matches
        no_matches = ApeTag([ApeTagItem.string(b"Bar", u"C"),
                             ApeTagItem.string(b"Baz", u"D")])
        test = base.intersection(no_matches)
        self.assertIs(type(test), ApeTag)
        self.assertEqual(test.tags, [])

        # test some matches
        some_matches = ApeTag([ApeTagItem.string(b"Bar", u"B"),
                               ApeTagItem.string(b"Baz", u"D")])
        test = base.intersection(some_matches)
        self.assertIs(type(test), ApeTag)
        self.assertEqual(test.tags, [ApeTagItem.string(b"Bar", u"B")])

        # test all matches
        some_matches = ApeTag([ApeTagItem.string(b"Bar", u"B"),
                               ApeTagItem.string(b"Foo", u"A")])
        test = base.intersection(some_matches)
        self.assertIs(type(test), ApeTag)
        self.assertEqual(test.tags,
                         [ApeTagItem.string(b"Foo", u"A"),
                          ApeTagItem.string(b"Bar", u"B")])


class ID3v1MetaData(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.ID3v1Comment
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "album_name",
                                 "artist_name",
                                 "year",
                                 "comment"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio]

    def empty_metadata(self):
        return self.metadata_class()

    @METADATA_ID3V1
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                metadata = self.empty_metadata()
                metadata.track_name = u"Foo"
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")
            finally:
                temp_file.close()

    @METADATA_ID3V1
    def test_supports_images(self):
        self.assertEqual(self.metadata_class.supports_images(), False)

    @METADATA_ID3V1
    def test_attribs(self):
        import sys
        import string
        import random

        # ID3v1 only supports ASCII characters
        # and not very many of them
        chars = u"".join([u"".join(map(chr if (sys.version_info[0] >= 3)
                                       else unichr, l))
                          for l in [range(0x30, 0x39 + 1),
                                    range(0x41, 0x5A + 1),
                                    range(0x61, 0x7A + 1)]])

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                # check that setting the fields to random values works
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    if field_type is type(u""):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in range(random.choice(range(1, 5)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    elif field_type is int:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)
                    elif field_type is bool:
                        value = random.choice([False, True])
                        setattr(metadata, field, value)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), value)

                # check that overlong fields are truncated
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    if field_type is type(u""):
                        unicode_string = u"a" * 50
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        if field == "comment":
                            self.assertEqual(getattr(metadata, field),
                                             u"a" * 28)
                        elif field == "year":
                            self.assertEqual(getattr(metadata, field),
                                             u"a" * 4)
                        else:
                            self.assertEqual(getattr(metadata, field),
                                             u"a" * 30)

                # check that blanking out the fields works
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    if field_type is type(u""):
                        setattr(metadata, field, u"")
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertIsNone(getattr(metadata, field))
                    elif field_type is int:
                        setattr(metadata, field, 0)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertIsNone(getattr(metadata, field))

                # re-set the fields with random values
                for field in self.supported_fields:
                    field_type = audiotools.MetaData.FIELD_TYPES[field]
                    metadata = self.empty_metadata()
                    if field_type is type(u""):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in range(random.choice(range(1, 5)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    elif field_type is int:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)

                # check that deleting the fields works
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    delattr(metadata, field)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertIsNone(getattr(metadata, field))

            finally:
                temp_file.close()

    @METADATA_ID3V1
    def test_field_mapping(self):
        mapping = [('track_name', u'a'),
                   ('artist_name', u'b'),
                   ('album_name', u'c'),
                   ('year', u'1234'),
                   ('comment', u'd'),
                   ('track_number', 1)]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                # ensure that setting a class field
                # updates its corresponding low-level implementation
                for (field, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)

                # ID3v1 no longer has a low-level implementation
                # since it builds and parses directly on strings
            finally:
                temp_file.close()

    @METADATA_ID3V1
    def test_clean(self):
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE)

        # check trailing whitespace
        metadata = audiotools.ID3v1Comment(track_name=u"Title ")
        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"title"}])
        self.assertEqual(
            cleaned,
            audiotools.ID3v1Comment(track_name=u"Title"))

        # check leading whitespace
        metadata = audiotools.ID3v1Comment(track_name=u" Title")
        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": u"title"}])
        self.assertEqual(
            cleaned,
            audiotools.ID3v1Comment(track_name=u"Title"))

        # ID3v1 has no empty fields, image data or leading zeroes
        # so those can be safely ignored

    @METADATA_ID3V1
    def test_intersection2(self):
        from audiotools.id3v1 import ID3v1Comment

        base = ID3v1Comment(track_name=u"A", genre=1)
        self.assertEqual(base.track_name, u"A")
        self.assertEqual(base.__genre__, 1)

        # test no matches
        no_matches = ID3v1Comment(track_name=u"B", album_name=u"C")
        test = base.intersection(no_matches)
        self.assertIs(type(test), ID3v1Comment)
        self.assertIsNone(test.track_name)
        self.assertIsNone(test.album_name)
        self.assertEqual(test.__genre__, 0)

        # test some matches
        some_matches = ID3v1Comment(track_name=u"B", genre=1)
        test = base.intersection(some_matches)
        self.assertIs(type(test), ID3v1Comment)
        self.assertIsNone(test.track_name)
        self.assertEqual(test.__genre__, 1)

        some_matches = ID3v1Comment(artist_name=u"B", genre=1)
        test = base.intersection(some_matches)
        self.assertIs(type(test), ID3v1Comment)
        self.assertIsNone(test.track_name)
        self.assertIsNone(test.artist_name)
        self.assertEqual(test.__genre__, 1)

        # test all matches
        all_matches = ID3v1Comment(track_name=u"A", genre=1)
        test = base.intersection(all_matches)
        self.assertIs(type(test), ID3v1Comment)
        self.assertEqual(test.track_name, u"A")
        self.assertEqual(test.__genre__, 1)


class ID3v22MetaData(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.ID3v22Comment
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "date",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio,
                                  audiotools.AiffAudio]

    def empty_metadata(self):
        return self.metadata_class([])

    def text_tag(self, attribute, unicode_text):
        return self.metadata_class.TEXT_FRAME.converted(
            self.metadata_class.ATTRIBUTE_MAP[attribute],
            unicode_text)

    def unknown_tag(self, binary_string):
        from audiotools.id3 import ID3v22_Frame

        return ID3v22_Frame(b"XXX", binary_string)

    @METADATA_ID3V2
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")
            finally:
                temp_file.close()

    @METADATA_ID3V2
    def test_foreign_field(self):
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame(b"TT2", 0, b"Track Name"),
             audiotools.id3.ID3v22_T__Frame(b"TAL", 0, b"Album Name"),
             audiotools.id3.ID3v22_T__Frame(b"TRK", 0, b"1/3"),
             audiotools.id3.ID3v22_T__Frame(b"TPA", 0, b"2/4"),
             audiotools.id3.ID3v22_T__Frame(b"TFO", 0, b"Bar")])
        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertEqual(metadata, metadata2)
                self.assertEqual(metadata.__class__, metadata2.__class__)
                self.assertEqual(metadata[b"TFO"][0].data, b"Bar")
            finally:
                temp_file.close()

    @METADATA_ID3V2
    def test_field_mapping(self):
        from audiotools.id3 import __padded__ as padded
        from audiotools.id3 import __number_pair__ as number_pair

        id3_class = self.metadata_class

        SPECIAL_ATTRIBS = ('track_number',
                           'track_total',
                           'album_number',
                           'album_total',
                           'compilation')

        attribs1 = {}  # a dict of attribute -> value pairs
                       # ("track_name":u"foo")
        attribs2 = {}  # a dict of ID3v2 -> value pairs
                       # ("TT2":u"foo")
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if attribute not in SPECIAL_ATTRIBS:
                attribs1[attribute] = attribs2[key] = u"value {:d}".format(i)
        attribs1["track_number"] = 2
        attribs1["track_total"] = 10
        attribs1["album_number"] = 1
        attribs1["album_total"] = 3
        attribs1["compilation"] = True

        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        # ensure that all the attributes match up
        for (attribute, value) in attribs1.items():
            self.assertEqual(getattr(id3, attribute), value)

        # ensure that all the keys for non-integer items match up
        for (key, value) in attribs2.items():
            self.assertEqual(u"{}".format(id3[key][0]), value)

        # ensure the keys for integer items match up
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]][0].number(),
            attribs1["track_number"])
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]][0].total(),
            attribs1["track_total"])
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]][0].number(),
            attribs1["album_number"])
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]][0].total(),
            attribs1["album_total"])

        # ensure the key for compilation matches up
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.BOOLEAN_IDS[0]][0].true(),
            attribs1["compilation"])

        # ensure that changing attributes changes the underlying frame
        # >>> id3.track_name = u"bar"
        # >>> id3['TT2'][0] == u"bar"
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if ((key not in id3_class.TEXT_FRAME.NUMERICAL_IDS) and
                (key not in id3_class.TEXT_FRAME.BOOLEAN_IDS)):
                setattr(id3, attribute, u"new value {:d}".format(i))
                self.assertEqual(u"{}".format(id3[key][0]),
                                 u"new value {:d}".format(i))

        # ensure that changing integer attributes changes the underlying frame
        # >>> id3.track_number = 2
        # >>> id3['TRK'][0] == u"2"
        id3.track_number = 3
        id3.track_total = None
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]][0].__unicode__(),
            padded(3))

        id3.track_total = 8
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]][0].__unicode__(),
            number_pair(3, 8))

        id3.album_number = 2
        id3.album_total = None
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]][0].__unicode__(),
            padded(2))

        id3.album_total = 4
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]][0].__unicode__(),
            number_pair(2, 4))

        # ensure that changing boolean attributes changes
        # the underlying frame:
        # >>> id3.compilation = True
        # >>> id3['TCP'][0] == u"1"
        id3.compilation = False
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.BOOLEAN_IDS[0]][0].__unicode__(),
            u"0")

        id3.compilation = True
        self.assertEqual(
            id3[id3_class.TEXT_FRAME.BOOLEAN_IDS[0]][0].__unicode__(),
            u"1")

        # reset and re-check everything for the next round
        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        # ensure that all the attributes match up
        for (attribute, value) in attribs1.items():
            self.assertEqual(getattr(id3, attribute), value)

        for (key, value) in attribs2.items():
            if key not in id3_class.TEXT_FRAME.NUMERICAL_IDS:
                self.assertEqual(id3[key][0].__unicode__(), value)
            else:
                self.assertEqual(int(id3[key][0]), value)

        # ensure that changing the underlying frames changes attributes
        # >>> id3['TT2'] = [ID3v22_T__Frame('TT2, u"bar")]
        # >>> id3.track_name == u"bar"
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if attribute not in SPECIAL_ATTRIBS:
                id3[key] = [id3_class.TEXT_FRAME(
                    key, 0, (u"new value {:d}".format(i)).encode("ascii"))]
                self.assertEqual(getattr(id3, attribute),
                                 u"new value {:d}".format(i))

        # ensure that changing the underlying integer frames changes attributes
        key = id3_class.TEXT_FRAME.NUMERICAL_IDS[0]
        id3[key] = [id3_class.TEXT_FRAME(key, 0, b"7")]
        self.assertEqual(id3.track_number, 7)

        id3[key] = [id3_class.TEXT_FRAME(key, 0, b"8/9")]
        self.assertEqual(id3.track_number, 8)
        self.assertEqual(id3.track_total, 9)

        key = id3_class.TEXT_FRAME.NUMERICAL_IDS[1]
        id3[key] = [id3_class.TEXT_FRAME(key, 0, b"4")]
        self.assertEqual(id3.album_number, 4)

        id3[key] = [id3_class.TEXT_FRAME(key, 0, b"5/6")]
        self.assertEqual(id3.album_number, 5)
        self.assertEqual(id3.album_total, 6)

        key = id3_class.TEXT_FRAME.BOOLEAN_IDS[0]
        id3[key] = [id3_class.TEXT_FRAME(key, 0, b"1")]
        self.assertEqual(id3.compilation, True)

        # finally, just for kicks, ensure that explicitly setting
        # frames also changes attributes
        # >>> id3['TT2'] = [id3_class.TEXT_FRAME.from_unicode('TT2',u"foo")]
        # >>> id3.track_name = u"foo"
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if attribute not in SPECIAL_ATTRIBS:
                id3[key] = [id3_class.TEXT_FRAME.converted(key,
                                                           u"{}".format(i))]
                self.assertEqual(getattr(id3, attribute), u"{}".format(i))

        # and ensure explicitly setting integer frames also changes attribs
        id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]] = [
            id3_class.TEXT_FRAME.converted(
                id3_class.TEXT_FRAME.NUMERICAL_IDS[0],
                u"4")]
        self.assertEqual(id3.track_number, 4)
        self.assertIsNone(id3.track_total)

        id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]] = [
            id3_class.TEXT_FRAME.converted(
                id3_class.TEXT_FRAME.NUMERICAL_IDS[0],
                u"2/10")]
        self.assertEqual(id3.track_number, 2)
        self.assertEqual(id3.track_total, 10)

        id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]] = [
            id3_class.TEXT_FRAME.converted(
                id3_class.TEXT_FRAME.NUMERICAL_IDS[1],
                u"3")]
        self.assertEqual(id3.album_number, 3)
        self.assertIsNone(id3.album_total)

        id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]] = [
            id3_class.TEXT_FRAME.converted(
                id3_class.TEXT_FRAME.NUMERICAL_IDS[1],
                u"5/7")]
        self.assertEqual(id3.album_number, 5)
        self.assertEqual(id3.album_total, 7)

    @METADATA_ID3V2
    def test_getitem(self):
        field = self.metadata_class.ATTRIBUTE_MAP["track_name"]

        # getitem with no matches raises KeyError
        metadata = self.metadata_class([])
        self.assertRaises(KeyError,
                          metadata.__getitem__,
                          field)

        metadata = self.metadata_class([self.unknown_tag(b"FOO")])
        self.assertRaises(KeyError,
                          metadata.__getitem__,
                          field)

        # getitem with one match returns that item
        metadata = self.metadata_class([self.text_tag("track_name",
                                                      u"Track Name")])
        self.assertEqual(metadata[field],
                         [self.text_tag("track_name",
                                        u"Track Name")])

        metadata = self.metadata_class([self.text_tag("track_name",
                                                      u"Track Name"),
                                        self.unknown_tag(b"FOO")])
        self.assertEqual(metadata[field],
                         [self.text_tag("track_name",
                                        u"Track Name")])

        # getitem with multiple matches returns all items, in order
        metadata = self.metadata_class([self.text_tag("track_name", u"1"),
                                        self.text_tag("track_name", u"2"),
                                        self.text_tag("track_name", u"3")])
        self.assertEqual(metadata[field],
                         [self.text_tag("track_name", u"1"),
                          self.text_tag("track_name", u"2"),
                          self.text_tag("track_name", u"3")])

        metadata = self.metadata_class([self.text_tag("track_name", u"1"),
                                        self.unknown_tag(b"FOO"),
                                        self.text_tag("track_name", u"2"),
                                        self.unknown_tag(b"BAR"),
                                        self.text_tag("track_name", u"3")])
        self.assertEqual(metadata[field],
                         [self.text_tag("track_name", u"1"),
                          self.text_tag("track_name", u"2"),
                          self.text_tag("track_name", u"3")])

    @METADATA_ID3V2
    def test_setitem(self):
        field = self.metadata_class.ATTRIBUTE_MAP["track_name"]

        # setitem replaces all keys with new values
        # - zero new values
        metadata = self.metadata_class([])
        metadata[field] = []
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("track_name", u"X")])
        metadata[field] = []
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("track_name", u"X"),
                                        self.text_tag("track_name", u"Y")])
        metadata[field] = []
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        # - one new value
        metadata = self.metadata_class([])
        metadata[field] = [self.text_tag("track_name", u"A")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X")])
        metadata[field] = [self.text_tag("track_name", u"A")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X"),
                                        self.text_tag("track_name", u"Y")])
        metadata[field] = [self.text_tag("track_name", u"A")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A")])

        # - two new values
        metadata = self.metadata_class([])
        metadata[field] = [self.text_tag("track_name", u"A"),
                           self.text_tag("track_name", u"B")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A"),
                          self.text_tag("track_name", u"B")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X")])
        metadata[field] = [self.text_tag("track_name", u"A"),
                           self.text_tag("track_name", u"B")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A"),
                          self.text_tag("track_name", u"B")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X"),
                                        self.text_tag("track_name", u"Y")])
        metadata[field] = [self.text_tag("track_name", u"A"),
                           self.text_tag("track_name", u"B")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A"),
                          self.text_tag("track_name", u"B")])

        # setitem leaves other items alone
        metadata = self.metadata_class([self.unknown_tag(b"FOO")])
        metadata[field] = []
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [self.unknown_tag(b"FOO")])

        metadata = self.metadata_class([self.unknown_tag(b"FOO"),
                                        self.text_tag("track_name", u"X")])
        metadata[field] = [self.text_tag("track_name", u"A")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.unknown_tag(b"FOO"),
                          self.text_tag("track_name", u"A")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X"),
                                        self.unknown_tag(b"FOO"),
                                        self.text_tag("track_name", u"Y")])
        metadata[field] = [self.text_tag("track_name", u"A"),
                           self.text_tag("track_name", u"B")]
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A"),
                          self.unknown_tag(b"FOO"),
                          self.text_tag("track_name", u"B")])

    @METADATA_ID3V2
    def test_getattr(self):
        # track_number grabs the first available integer, if any
        metadata = self.metadata_class([])
        self.assertIsNone(metadata.track_number)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"1")])
        self.assertEqual(metadata.track_number, 1)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo")])
        self.assertIsNone(metadata.track_number)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"1/2")])
        self.assertEqual(metadata.track_number, 1)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo 1 bar")])
        self.assertEqual(metadata.track_number, 1)

        # album_number grabs the first available integer, if any
        metadata = self.metadata_class([])
        self.assertIsNone(metadata.album_number)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"2")])
        self.assertEqual(metadata.album_number, 2)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"foo")])
        self.assertIsNone(metadata.album_number)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"2/4")])
        self.assertEqual(metadata.album_number, 2)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"foo 2 bar")])
        self.assertEqual(metadata.album_number, 2)

        # track_total grabs the first slashed field integer, if any
        metadata = self.metadata_class([])
        self.assertIsNone(metadata.track_total)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"1")])
        self.assertIsNone(metadata.track_total)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo")])
        self.assertIsNone(metadata.track_total)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"1/2")])
        self.assertEqual(metadata.track_total, 2)

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo 1 bar / baz 2 blah")])
        self.assertEqual(metadata.track_total, 2)

        # album_total grabs the first slashed field integer, if any
        metadata = self.metadata_class([])
        self.assertIsNone(metadata.album_total)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"2")])
        self.assertIsNone(metadata.album_total)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"foo")])
        self.assertIsNone(metadata.album_total)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"2/4")])
        self.assertEqual(metadata.album_total, 4)

        metadata = self.metadata_class([
            self.text_tag("album_number", u"foo 2 bar / baz 4 blah")])
        self.assertEqual(metadata.album_total, 4)

        # other fields grab the first available item, if any
        metadata = self.metadata_class([])
        self.assertIsNone(metadata.track_name)

        metadata = self.metadata_class([self.text_tag("track_name", u"1")])
        self.assertEqual(metadata.track_name, u"1")

        metadata = self.metadata_class([self.text_tag("track_name", u"1"),
                                        self.text_tag("track_name", u"2")])
        self.assertEqual(metadata.track_name, u"1")

    @METADATA_ID3V2
    def test_setattr(self):
        from audiotools.id3 import __padded__ as padded
        from audiotools.id3 import __number_pair__ as number_pair

        # track_number adds new field if necessary
        metadata = self.metadata_class([])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        number_pair(1, None))])

        # track_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = self.metadata_class([
            self.text_tag("track_number", u"6")])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        number_pair(1, None))])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"6"),
            self.text_tag("track_number", u"10")])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        number_pair(1, None)),
                          self.text_tag("track_number", u"10")])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"6/2")])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        u"{}/2".format(padded(1)))])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo 6 bar")])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        u"foo {} bar".format(padded(1)))])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo 6 bar / blah 7 baz")])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.frames,
                         [self.text_tag(
                             "track_number",
                             u"foo {} bar / blah 7 baz".format(padded(1)))])

        # album_number adds new field if necessary
        metadata = self.metadata_class([])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        padded(3))])

        # album_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = self.metadata_class([
            self.text_tag("album_number", u"7")])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        padded(3))])

        metadata = self.metadata_class([
            self.text_tag("album_number", u"7"),
            self.text_tag("album_number", u"10")])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        padded(3)),
                          self.text_tag("album_number", u"10")])

        metadata = self.metadata_class([
            self.text_tag("album_number", u"7/4")])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        u"{}/4".format(padded(3)))])

        metadata = self.metadata_class([
            self.text_tag("album_number", u"foo 7 bar")])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        u"foo {} bar".format(padded(3)))])

        metadata = self.metadata_class([
            self.text_tag("album_number", u"foo 7 bar / blah 8 baz")])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.frames,
                         [self.text_tag(
                             "album_number",
                             u"foo {} bar / blah 8 baz".format(padded(3)))])

        # track_total adds new field if necessary
        metadata = self.metadata_class([])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        number_pair(0, 2))])

        # track_total updates the second integer field
        # and leaves other junk in that field alone
        metadata = self.metadata_class([
            self.text_tag("track_number", u"6")])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        u"6/{}".format(padded(2)))])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"6"),
            self.text_tag("track_number", u"10")])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                         u"6/{}".format(padded(2))),
                          self.text_tag("track_number", u"10")])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"6/7")])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        u"6/{}".format(padded(2)))])

        metadata = self.metadata_class([
            self.text_tag("track_number", u"foo 6 bar / blah 7 baz")])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag(
                             "track_number",
                             u"foo 6 bar / blah {} baz".format(padded(2)))])

        # album_total adds new field if necessary
        metadata = self.metadata_class([])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        number_pair(0, 4))])

        # album_total updates the second integer field
        # and leaves other junk in that field alone
        metadata = self.metadata_class([
            self.text_tag("album_number", u"9")])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_total",
                                        u"9/{}".format(padded(4)))])

        metadata = self.metadata_class([
            self.text_tag("album_number", u"9"),
            self.text_tag("album_number", u"10")])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        u"9/{}".format(padded(4))),
                          self.text_tag("album_number", u"10")])

        metadata = self.metadata_class([
            self.text_tag("album_number", u"9/10")])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        u"9/{}".format(padded(4)))])

        metadata = self.metadata_class([
            self.text_tag("album_total", u"foo 9 bar / blah 10 baz")])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag(
                             "album_number",
                             u"foo 9 bar / blah {} baz".format(padded(4)))])

        # other fields update the first match
        # while leaving the rest alone
        metadata = self.metadata_class([])
        metadata.track_name = u"A"
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X")])
        metadata.track_name = u"A"
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A")])

        metadata = self.metadata_class([self.text_tag("track_name", u"X"),
                                        self.text_tag("track_name", u"Y")])
        metadata.track_name = u"A"
        self.assertEqual(metadata.track_name, u"A")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"A"),
                          self.text_tag("track_name", u"Y")])

        # setting field to an empty string is okay
        metadata = self.metadata_class([])
        metadata.track_name = u""
        self.assertEqual(metadata.track_name, u"")
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_name", u"")])

    @METADATA_ID3V2
    def test_delattr(self):
        # deleting nonexistent field is okay
        for field in audiotools.MetaData.FIELDS:
            metadata = self.metadata_class([])
            delattr(metadata, field)
            self.assertIsNone(getattr(metadata, field))

        # deleting field removes all instances of it
        metadata = self.metadata_class([self.text_tag("track_name", u"A")])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("track_name", u"A"),
                                        self.text_tag("track_name", u"B")])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        # setting field to None is the same as deleting field
        for field in audiotools.MetaData.FIELDS:
            metadata = self.metadata_class([])
            setattr(metadata, field, None)
            self.assertIsNone(getattr(metadata, field))

        metadata = self.metadata_class([self.text_tag("track_name", u"A")])
        metadata.track_name = None
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("track_name", u"A"),
                                        self.text_tag("track_name", u"B")])
        metadata.track_name = None
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata.frames, [])

        # deleting track_number without track_total removes field
        metadata = self.metadata_class([self.text_tag("track_number", u"1")])
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("track_number", u"1"),
                                        self.text_tag("track_number", u"2")])
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("track_number",
                                                      u"foo 1 bar")])
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.frames, [])

        # deleting track_number with track_total converts track_number to None
        metadata = self.metadata_class([self.text_tag("track_number", u"1/2")])
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number", u"0/2")])

        metadata = self.metadata_class([self.text_tag(
            "track_number", u"foo 1 bar / blah 2 baz")])
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number",
                                        u"foo 0 bar / blah 2 baz")])

        # deleting track_total without track_number removes field
        metadata = self.metadata_class([self.text_tag(
            "track_number", u"0/1")])
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag(
            "track_number", u"foo 0 bar / 1")])
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag(
            "track_number", u"foo / 1")])
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.frames, [])

        # deleting track_total with track_number removes slashed field
        metadata = self.metadata_class([self.text_tag(
            "track_number", u"1/2")])
        del(metadata.track_total)
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number", u"1")])

        metadata = self.metadata_class([self.text_tag(
            "track_number", u"1 / 2")])
        del(metadata.track_total)
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number", u"1")])

        metadata = self.metadata_class([self.text_tag(
            "track_number", u"foo 1 bar / baz 2 blah")])
        del(metadata.track_total)
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.frames,
                         [self.text_tag("track_number", u"foo 1 bar")])

        # deleting album_number without album_total removes field
        metadata = self.metadata_class([self.text_tag("album_number", u"3")])
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("album_number", u"3"),
                                        self.text_tag("album_number", u"4")])
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag("album_number",
                                                      u"foo 3 bar")])
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.frames, [])

        # deleting album_number with album_total converts album_number to None
        metadata = self.metadata_class([self.text_tag("album_number", u"3/4")])
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number", u"0/4")])

        metadata = self.metadata_class([self.text_tag(
            "album_number", u"foo 3 bar / blah 4 baz")])
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number",
                                        u"foo 0 bar / blah 4 baz")])

        # deleting album_total without album_number removes field
        metadata = self.metadata_class([self.text_tag(
            "album_number", u"0/1")])
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag(
            "album_number", u"foo 0 bar / 1")])
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.frames, [])

        metadata = self.metadata_class([self.text_tag(
            "album_number", u"foo / 1")])
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.frames, [])

        # deleting album_total with album_number removes slashed field
        metadata = self.metadata_class([self.text_tag(
            "album_number", u"3/4")])
        del(metadata.album_total)
        self.assertEqual(metadata.album_number, 3)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number", u"3")])

        metadata = self.metadata_class([self.text_tag(
            "album_number", u"3 / 4")])
        del(metadata.album_total)
        self.assertEqual(metadata.album_number, 3)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number", u"3")])

        metadata = self.metadata_class([self.text_tag(
            "album_number", u"foo 3 bar / baz 4 blah")])
        del(metadata.album_total)
        self.assertEqual(metadata.album_number, 3)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.frames,
                         [self.text_tag("album_number", u"foo 3 bar")])

    @METADATA_ID3V2
    def test_sync_safe(self):
        from audiotools.id3 import decode_syncsafe32, encode_syncsafe32

        # ensure values round-trip correctly across several bytes
        for value in range(16384):
            self.assertEqual(decode_syncsafe32(encode_syncsafe32(value)),
                             value)

        self.assertEqual(decode_syncsafe32(encode_syncsafe32(2 ** 28 - 1)),
                         2 ** 28 - 1)

        # ensure values that are too large don't decode
        self.assertRaises(ValueError, decode_syncsafe32, 2 ** 32)

        # ensure negative values don't decode
        self.assertRaises(ValueError, decode_syncsafe32, -1)

        # ensure values with invalid padding don't decode
        self.assertRaises(ValueError, decode_syncsafe32, 0x80)
        self.assertRaises(ValueError, decode_syncsafe32, 0x80 << 8)
        self.assertRaises(ValueError, decode_syncsafe32, 0x80 << 16)
        self.assertRaises(ValueError, decode_syncsafe32, 0x80 << 24)

        # ensure values that are too large don't encode
        self.assertRaises(ValueError, encode_syncsafe32, 2 ** 28)

        # ensure values that are negative don't encode
        self.assertRaises(ValueError, encode_syncsafe32, -1)

    @METADATA_ID3V2
    def test_padding(self):
        from os.path import getsize
        from operator import or_

        with open("sine.mp3", "rb") as f:
            mp3_data = f.read()

        # build temporary track with no metadata
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3")
        temp_file_name = temp_file.name
        temp_file.write(mp3_data)
        temp_file.flush()

        mp3_track = audiotools.open(temp_file_name)
        self.assertIsNone(mp3_track.get_metadata())

        # tag track with our metadata
        metadata = self.empty_metadata()
        metadata.track_name = u"Track Name"
        mp3_track.update_metadata(metadata)

        self.assertEqual(mp3_track.get_metadata().track_name, u"Track Name")

        self.assertEqual(getsize(temp_file_name),
                         metadata.size() + len(mp3_data))

        # add a bunch of padding to track's metadata
        # and ensure it still works
        for padding in range(1024):
            # grab existing tag from file
            metadata = mp3_track.get_metadata()
            old_metadata_size = metadata.total_size

            # add another padding byte
            metadata.total_size += 1
            mp3_track.update_metadata(metadata)

            # ensure file isn't broken
            self.assertTrue(
                audiotools.pcm_cmp(
                    audiotools.open("sine.mp3").to_pcm(),
                    audiotools.open(temp_file_name).to_pcm()))

            # ensure metadata is unchanged
            # and has the expected buffer size
            new_metadata = audiotools.open(temp_file_name).get_metadata()
            self.assertEqual(new_metadata.total_size, old_metadata_size + 1)
            self.assertEqual(new_metadata, metadata)
        temp_file.close()

    @METADATA_ID3V2
    def test_clean(self):
        from audiotools.text import CLEAN_REMOVE_TRAILING_WHITESPACE
        from audiotools.text import CLEAN_REMOVE_LEADING_WHITESPACE
        from audiotools.text import CLEAN_REMOVE_EMPTY_TAG
        from audiotools.text import CLEAN_ADD_LEADING_ZEROES
        from audiotools.text import CLEAN_REMOVE_LEADING_ZEROES

        # check trailing whitespace
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame.converted(b"TT2", u"Title ")])
        self.assertEqual(metadata.track_name, u"Title ")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"TT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        # check leading whitespace
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame.converted(b"TT2", u" Title")])
        self.assertEqual(metadata.track_name, u" Title")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": u"TT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        # check empty fields
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame.converted(b"TT2", u"")])
        self.assertEqual(metadata[b"TT2"][0].data, b"")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": u"TT2"}])
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          b"TT2")

        # check leading zeroes,
        # depending on whether we're preserving them or not

        id3_pad = audiotools.config.get_default("ID3", "pad", "off")
        try:
            # pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "on")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             True)

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(b"TRK", u"1")])
            self.assertEqual(metadata.track_number, 1)
            self.assertIsNone(metadata.track_total)
            self.assertEqual(metadata[b"TRK"][0].data, b"1")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_ADD_LEADING_ZEROES %
                              {"field": u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertIsNone(cleaned.track_total)
            self.assertEqual(cleaned[b"TRK"][0].data, b"01")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(b"TRK", u"1/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRK"][0].data, b"1/2")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_ADD_LEADING_ZEROES %
                              {"field": u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRK"][0].data, b"01/02")

            # don't pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "off")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             False)

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(b"TRK", u"01")])
            self.assertEqual(metadata.track_number, 1)
            self.assertIsNone(metadata.track_total)
            self.assertEqual(metadata[b"TRK"][0].data, b"01")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertIsNone(cleaned.track_total)
            self.assertEqual(cleaned[b"TRK"][0].data, b"1")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(b"TRK", u"01/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRK"][0].data, b"01/2")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRK"][0].data, b"1/2")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(b"TRK", u"1/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRK"][0].data, b"1/02")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRK"][0].data, b"1/2")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted(b"TRK", u"01/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRK"][0].data, b"01/02")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRK"][0].data, b"1/2")
        finally:
            audiotools.config.set_default("ID3", "pad", id3_pad)

    @METADATA_ID3V2
    def test_intersection2(self):
        from audiotools.id3 import ID3v22Comment
        from audiotools.id3 import ID3v22_T__Frame
        from audiotools.id3 import ID3v22_TXX_Frame

        base = ID3v22Comment(
            [ID3v22_T__Frame.converted(b"TT2", u"Foo"),
             ID3v22_TXX_Frame(0, b"Bar", b"Baz")])
        self.assertEqual(base.track_name, u"Foo")

        # test no matches
        no_matches = ID3v22Comment(
            [ID3v22_T__Frame.converted(b"TT2", u"Bar"),
             ID3v22_T__Frame.converted(b"TAL", u"Baz")])
        test = base.intersection(no_matches)
        self.assertIs(type(test), ID3v22Comment)
        self.assertEqual(test.frames, [])

        # test some matches
        some_matches = ID3v22Comment(
            [ID3v22_T__Frame.converted(b"TT2", u"Bar"),
             ID3v22_TXX_Frame(0, b"Bar", b"Baz")])
        test = base.intersection(some_matches)
        self.assertIs(type(test), ID3v22Comment)
        self.assertEqual(test.frames, [ID3v22_TXX_Frame(0, b"Bar", b"Baz")])

        # test all matches
        all_matches = ID3v22Comment(
            [ID3v22_TXX_Frame(0, b"Bar", b"Baz"),
             ID3v22_T__Frame.converted(b"TT2", u"Foo")])
        test = base.intersection(all_matches)
        self.assertIs(type(test), ID3v22Comment)
        self.assertEqual(test.frames,
                         [ID3v22_T__Frame.converted(b"TT2", u"Foo"),
                          ID3v22_TXX_Frame(0, b"Bar", b"Baz")])


class ID3v23MetaData(ID3v22MetaData):
    def setUp(self):
        self.metadata_class = audiotools.ID3v23Comment
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "date",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio]

    def unknown_tag(self, binary_string):
        from audiotools.id3 import ID3v23_Frame

        return ID3v23_Frame(b"XXXX", binary_string)

    @METADATA_ID3V2
    def test_foreign_field(self):
        metadata = self.metadata_class(
            [audiotools.id3.ID3v23_T___Frame(b"TIT2", 0, b"Track Name"),
             audiotools.id3.ID3v23_T___Frame(b"TALB", 0, b"Album Name"),
             audiotools.id3.ID3v23_T___Frame(b"TRCK", 0, b"1/3"),
             audiotools.id3.ID3v23_T___Frame(b"TPOS", 0, b"2/4"),
             audiotools.id3.ID3v23_T___Frame(b"TFOO", 0, b"Bar")])
        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertEqual(metadata, metadata2)
                self.assertEqual(metadata.__class__, metadata2.__class__)
                self.assertEqual(metadata[b"TFOO"][0].data, b"Bar")
            finally:
                temp_file.close()

    def empty_metadata(self):
        return self.metadata_class([])

    @METADATA_ID3V2
    def test_sync_safe(self):
        # this is tested by ID3v22 and doesn't need to be tested again
        self.assertTrue(True)

    @METADATA_ID3V2
    def test_clean(self):
        from audiotools.text import (CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_LEADING_ZEROES,
                                     CLEAN_ADD_LEADING_ZEROES)

        # check trailing whitespace
        metadata = audiotools.ID3v23Comment(
            [audiotools.id3.ID3v23_T___Frame.converted(b"TIT2", u"Title ")])
        self.assertEqual(metadata.track_name, u"Title ")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        # check leading whitespace
        metadata = audiotools.ID3v23Comment(
            [audiotools.id3.ID3v23_T___Frame.converted(b"TIT2", u" Title")])
        self.assertEqual(metadata.track_name, u" Title")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        # check empty fields
        metadata = audiotools.ID3v23Comment(
            [audiotools.id3.ID3v23_T___Frame.converted(b"TIT2", u"")])
        self.assertEqual(metadata[b"TIT2"][0].data, b"")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": u"TIT2"}])
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          b"TIT2")

        # check leading zeroes,
        # depending on whether we're preserving them or not

        id3_pad = audiotools.config.get_default("ID3", "pad", "off")
        try:
            # pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "on")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             True)

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(b"TRCK", u"1")])
            self.assertEqual(metadata.track_number, 1)
            self.assertIsNone(metadata.track_total)
            self.assertEqual(metadata[b"TRCK"][0].data, b"1")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_ADD_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertIsNone(cleaned.track_total)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"01")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(b"TRCK", u"1/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"1/2")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_ADD_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"01/02")

            # don't pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "off")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             False)

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(b"TRCK", u"01")])
            self.assertEqual(metadata.track_number, 1)
            self.assertIsNone(metadata.track_total)
            self.assertEqual(metadata[b"TRCK"][0].data, b"01")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertIsNone(cleaned.track_total)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(b"TRCK", u"01/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"01/2")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1/2")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(b"TRCK", u"1/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"1/02")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1/2")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted(b"TRCK", u"01/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"01/02")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1/2")
        finally:
            audiotools.config.set_default("ID3", "pad", id3_pad)

    @METADATA_ID3V2
    def test_intersection2(self):
        from audiotools.id3 import ID3v23Comment
        from audiotools.id3 import ID3v23_T___Frame
        from audiotools.id3 import ID3v23_TXXX_Frame

        base = ID3v23Comment(
            [ID3v23_T___Frame.converted(b"TIT2", u"Foo"),
             ID3v23_TXXX_Frame(0, b"Bar", b"Baz")])
        self.assertEqual(base.track_name, u"Foo")

        # test no matches
        no_matches = ID3v23Comment(
            [ID3v23_T___Frame.converted(b"TIT2", u"Bar"),
             ID3v23_T___Frame.converted(b"TALB", u"Baz")])
        test = base.intersection(no_matches)
        self.assertIs(type(test), ID3v23Comment)
        self.assertEqual(test.frames, [])

        # test some matches
        some_matches = ID3v23Comment(
            [ID3v23_T___Frame.converted(b"TIT2", u"Bar"),
             ID3v23_TXXX_Frame(0, b"Bar", b"Baz")])
        test = base.intersection(some_matches)
        self.assertIs(type(test), ID3v23Comment)
        self.assertEqual(test.frames, [ID3v23_TXXX_Frame(0, b"Bar", b"Baz")])

        # test all matches
        all_matches = ID3v23Comment(
            [ID3v23_TXXX_Frame(0, b"Bar", b"Baz"),
             ID3v23_T___Frame.converted(b"TIT2", u"Foo")])
        test = base.intersection(all_matches)
        self.assertIs(type(test), ID3v23Comment)
        self.assertEqual(test.frames,
                         [ID3v23_T___Frame.converted(b"TIT2", u"Foo"),
                          ID3v23_TXXX_Frame(0, b"Bar", b"Baz")])


class ID3v24MetaData(ID3v22MetaData):
    def setUp(self):
        self.metadata_class = audiotools.ID3v24Comment
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "date",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio]

    def unknown_tag(self, binary_string):
        from audiotools.id3 import ID3v24_Frame

        return ID3v24_Frame(b"XXXX", binary_string)

    def empty_metadata(self):
        return self.metadata_class([])

    @METADATA_ID3V2
    def test_sync_safe(self):
        # this is tested by ID3v22 and doesn't need to be tested again
        self.assertTrue(True)

    @METADATA_ID3V2
    def test_clean(self):
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_ADD_LEADING_ZEROES,
                                     CLEAN_REMOVE_LEADING_ZEROES)

        # check trailing whitespace
        metadata = audiotools.ID3v24Comment(
            [audiotools.id3.ID3v24_T___Frame.converted(b"TIT2", u"Title ")])
        self.assertEqual(metadata.track_name, u"Title ")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        # check leading whitespace
        metadata = audiotools.ID3v24Comment(
            [audiotools.id3.ID3v24_T___Frame.converted(b"TIT2", u" Title")])
        self.assertEqual(metadata.track_name, u" Title")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        # check empty fields
        metadata = audiotools.ID3v24Comment(
            [audiotools.id3.ID3v24_T___Frame.converted(b"TIT2", u"")])
        self.assertEqual(metadata[b"TIT2"][0].data, b"")
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": u"TIT2"}])
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          b"TIT2")

        # check leading zeroes,
        # depending on whether we're preserving them or not

        id3_pad = audiotools.config.get_default("ID3", "pad", "off")
        try:
            # pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "on")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             True)

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(b"TRCK", u"1")])
            self.assertEqual(metadata.track_number, 1)
            self.assertIsNone(metadata.track_total)
            self.assertEqual(metadata[b"TRCK"][0].data, b"1")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_ADD_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertIsNone(cleaned.track_total)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"01")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(b"TRCK", u"1/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"1/2")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_ADD_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"01/02")

            # don't pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "off")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             False)

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(b"TRCK", u"01")])
            self.assertEqual(metadata.track_number, 1)
            self.assertIsNone(metadata.track_total)
            self.assertEqual(metadata[b"TRCK"][0].data, b"01")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertIsNone(cleaned.track_total)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(b"TRCK", u"01/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"01/2")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1/2")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(b"TRCK", u"1/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"1/02")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1/2")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted(b"TRCK", u"01/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata[b"TRCK"][0].data, b"01/02")
            (cleaned, fixes) = metadata.clean()
            self.assertEqual(fixes,
                             [CLEAN_REMOVE_LEADING_ZEROES %
                              {"field": u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned[b"TRCK"][0].data, b"1/2")
        finally:
            audiotools.config.set_default("ID3", "pad", id3_pad)

    @METADATA_ID3V2
    def test_intersection2(self):
        from audiotools.id3 import ID3v24Comment
        from audiotools.id3 import ID3v24_T___Frame
        from audiotools.id3 import ID3v24_TXXX_Frame

        base = ID3v24Comment(
            [ID3v24_T___Frame.converted(b"TIT2", u"Foo"),
             ID3v24_TXXX_Frame(0, b"Bar", b"Baz")])
        self.assertEqual(base.track_name, u"Foo")

        # test no matches
        no_matches = ID3v24Comment(
            [ID3v24_T___Frame.converted(b"TIT2", u"Bar"),
             ID3v24_T___Frame.converted(b"TALB", u"Baz")])
        test = base.intersection(no_matches)
        self.assertIs(type(test), ID3v24Comment)
        self.assertEqual(test.frames, [])

        # test some matches
        some_matches = ID3v24Comment(
            [ID3v24_T___Frame.converted(b"TIT2", u"Bar"),
             ID3v24_TXXX_Frame(0, b"Bar", b"Baz")])
        test = base.intersection(some_matches)
        self.assertIs(type(test), ID3v24Comment)
        self.assertEqual(test.frames, [ID3v24_TXXX_Frame(0, b"Bar", b"Baz")])

        # test all matches
        all_matches = ID3v24Comment(
            [ID3v24_TXXX_Frame(0, b"Bar", b"Baz"),
             ID3v24_T___Frame.converted(b"TIT2", u"Foo")])
        test = base.intersection(all_matches)
        self.assertIs(type(test), ID3v24Comment)
        self.assertEqual(test.frames,
                         [ID3v24_T___Frame.converted(b"TIT2", u"Foo"),
                          ID3v24_TXXX_Frame(0, b"Bar", b"Baz")])


class ID3CommentPairMetaData(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.ID3CommentPair
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "date",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_ID3V2
    def test_field_mapping(self):
        pass


class FlacMetaData(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.FlacMetaData
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "catalog",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.FlacAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_FLAC
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # streaminfo not updated with set_metadata()
                # but can be updated with update_metadata()
                old_streaminfo = metadata.get_block(
                    audiotools.flac.Flac_STREAMINFO.BLOCK_ID)
                new_streaminfo = audiotools.flac.Flac_STREAMINFO(
                    minimum_block_size=old_streaminfo.minimum_block_size,
                    maximum_block_size=old_streaminfo.maximum_block_size,
                    minimum_frame_size=0,
                    maximum_frame_size=old_streaminfo.maximum_frame_size,
                    sample_rate=old_streaminfo.sample_rate,
                    channels=old_streaminfo.channels,
                    bits_per_sample=old_streaminfo.bits_per_sample,
                    total_samples=old_streaminfo.total_samples,
                    md5sum=old_streaminfo.md5sum)
                metadata.replace_blocks(
                    audiotools.flac.Flac_STREAMINFO.BLOCK_ID, [new_streaminfo])
                track.set_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                    audiotools.flac.Flac_STREAMINFO.BLOCK_ID),
                    old_streaminfo)
                track.update_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                    audiotools.flac.Flac_STREAMINFO.BLOCK_ID),
                    new_streaminfo)

                # vendor_string not updated with set_metadata()
                # but can be updated with update_metadata()
                old_vorbiscomment = metadata.get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                new_vorbiscomment = audiotools.flac.Flac_VORBISCOMMENT(
                    comment_strings=old_vorbiscomment.comment_strings[:],
                    vendor_string=u"Vendor String")
                metadata.replace_blocks(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID,
                    [new_vorbiscomment])
                track.set_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID).vendor_string,
                    old_vorbiscomment.vendor_string)
                track.update_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID).vendor_string,
                    new_vorbiscomment.vendor_string)

                # REPLAYGAIN_* tags not updated with set_metadata()
                # but can be updated with update_metadata()
                old_vorbiscomment = metadata.get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                new_vorbiscomment = audiotools.flac.Flac_VORBISCOMMENT(
                    comment_strings=old_vorbiscomment.comment_strings +
                    [u"REPLAYGAIN_REFERENCE_LOUDNESS=89.0 dB"],
                    vendor_string=old_vorbiscomment.vendor_string)
                self.assertEqual(
                    new_vorbiscomment[u"REPLAYGAIN_REFERENCE_LOUDNESS"],
                    [u"89.0 dB"])
                metadata.replace_blocks(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID,
                    [new_vorbiscomment])
                track.set_metadata(metadata)
                self.assertRaises(
                    KeyError,
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                        ).__getitem__,
                    u"REPLAYGAIN_REFERENCE_LOUDNESS")
                track.update_metadata(metadata)
                self.assertEqual(
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                        )[u"REPLAYGAIN_REFERENCE_LOUDNESS"],
                    [u"89.0 dB"])

                # WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                # not updated with set_metadata()
                # but can be updated with update_metadata()
                old_vorbiscomment = metadata.get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                new_vorbiscomment = audiotools.flac.Flac_VORBISCOMMENT(
                    comment_strings=old_vorbiscomment.comment_strings +
                    [u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK=0x0003"],
                    vendor_string=old_vorbiscomment.vendor_string)
                self.assertEqual(
                    new_vorbiscomment[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"],
                    [u"0x0003"])
                metadata.replace_blocks(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID,
                    [new_vorbiscomment])
                track.set_metadata(metadata)
                self.assertRaises(
                    KeyError,
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                        ).__getitem__,
                    u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK")
                track.update_metadata(metadata)
                self.assertEqual(
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                        )[u"WAVEFORMATEXTENSIBLE_CHANNEL_MASK"],
                    [u"0x0003"])

                # cuesheet not updated with set_metadata()
                # but can be updated with update_metadata()
                new_cuesheet = audiotools.flac.Flac_CUESHEET(
                    catalog_number=b"\x00" * 128,
                    lead_in_samples=0,
                    is_cdda=1,
                    tracks=[audiotools.flac.Flac_CUESHEET_track(
                            offset=0,
                            number=0,
                            ISRC=b" " * 12,
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[audiotools.flac.Flac_CUESHEET_index(
                                track_offset=0,
                                offset=0,
                                number=0)])])
                metadata = track.get_metadata()
                self.assertRaises(IndexError,
                                  metadata.get_block,
                                  audiotools.flac.Flac_CUESHEET.BLOCK_ID)
                metadata.add_block(new_cuesheet)
                track.set_metadata(metadata)
                self.assertRaises(IndexError,
                                  track.get_metadata().get_block,
                                  audiotools.flac.Flac_CUESHEET.BLOCK_ID)
                track.update_metadata(metadata)
                self.assertEqual(
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_CUESHEET.BLOCK_ID),
                    new_cuesheet)

                # seektable not updated with set_metadata()
                # but can be updated with update_metadata()

                # Ogg FLAC doesn't really support seektables as such

                metadata = track.get_metadata()

                old_seektable = metadata.get_block(
                    audiotools.flac.Flac_SEEKTABLE.BLOCK_ID)

                new_seektable = audiotools.flac.Flac_SEEKTABLE(
                    seekpoints=[(1, 1, 4096)] +
                    old_seektable.seekpoints[1:])
                metadata.replace_blocks(
                    audiotools.flac.Flac_SEEKTABLE.BLOCK_ID,
                    [new_seektable])
                track.set_metadata(metadata)
                self.assertEqual(
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
                    old_seektable)
                track.update_metadata(metadata)
                self.assertEqual(
                    track.get_metadata().get_block(
                        audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
                    new_seektable)

                # application blocks not updated with set_metadata()
                # but can be updated with update_metadata()
                application = audiotools.flac.Flac_APPLICATION(
                    application_id=b"fooz",
                    data=b"kelp")
                metadata = track.get_metadata()
                self.assertRaises(IndexError,
                                  metadata.get_block,
                                  audiotools.flac.Flac_APPLICATION.BLOCK_ID)
                metadata.add_block(application)
                track.set_metadata(metadata)
                self.assertRaises(IndexError,
                                  track.get_metadata().get_block,
                                  audiotools.flac.Flac_APPLICATION.BLOCK_ID)
                track.update_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                    audiotools.flac.Flac_APPLICATION.BLOCK_ID),
                    application)
            finally:
                temp_file.close()

    @METADATA_FLAC
    def test_foreign_field(self):
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TITLE=Track Name",
                 u"ALBUM=Album Name",
                 u"TRACKNUMBER=1",
                 u"TRACKTOTAL=3",
                 u"DISCNUMBER=2",
                 u"DISCTOTAL=4",
                 u"FOO=Bar"], u"")])
        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertEqual(metadata, metadata2)
                self.assertIsInstance(metadata, audiotools.FlacMetaData)
                self.assertEqual(track.get_metadata().get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u"FOO"],
                    [u"Bar"])
            finally:
                temp_file.close()

    @METADATA_FLAC
    def test_field_mapping(self):
        mapping = [('track_name', u'TITLE', u'a'),
                   ('track_number', u'TRACKNUMBER', 1),
                   ('track_total', u'TRACKTOTAL', 2),
                   ('album_name', u'ALBUM', u'b'),
                   ('artist_name', u'ARTIST', u'c'),
                   ('performer_name', u'PERFORMER', u'd'),
                   ('composer_name', u'COMPOSER', u'e'),
                   ('conductor_name', u'CONDUCTOR', u'f'),
                   ('media', u'SOURCE MEDIUM', u'g'),
                   ('ISRC', u'ISRC', u'h'),
                   ('catalog', u'CATALOG', u'i'),
                   ('copyright', u'COPYRIGHT', u'j'),
                   ('year', u'DATE', u'k'),
                   ('album_number', u'DISCNUMBER', 3),
                   ('album_total', u'DISCTOTAL', 4),
                   ('comment', u'COMMENT', u'l')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                # ensure that setting a class field
                # updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                            )[key][0],
                        u"{}".format(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                            )[key][0],
                        u"{}".format(value))

                # ensure that updating the low-level implementation
                # is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata.get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[key] = \
                        [u"{}".format(value)]
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                            )[key][0],
                        u"{}".format(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                            )[key][0],
                        u"{}".format(value))
            finally:
                # temp_file.close()
                pass

    @METADATA_FLAC
    def test_converted(self):
        MetaDataTest.test_converted(self)

        metadata_orig = self.empty_metadata()
        metadata_orig.get_block(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u'FOO'] = [u'bar']

        self.assertEqual(metadata_orig.get_block(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u'FOO'], [u'bar'])

        metadata_new = self.metadata_class.converted(metadata_orig)

        self.assertEqual(metadata_orig.get_block(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u'FOO'],
            metadata_new.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u'FOO'])

        # ensure that convert() builds a whole new object
        metadata_new.track_name = u"Foo"
        self.assertEqual(metadata_new.track_name, u"Foo")
        metadata_new2 = self.metadata_class.converted(metadata_new)
        self.assertEqual(metadata_new2, metadata_new)
        metadata_new2.track_name = u"Bar"
        self.assertEqual(metadata_new2.track_name, u"Bar")
        self.assertEqual(metadata_new.track_name, u"Foo")

    @METADATA_FLAC
    def test_oversized(self):
        from bz2 import decompress

        oversized_image = audiotools.Image.new(decompress(HUGE_BMP), u'', 0)
        oversized_text = u"a" * 16777216

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                # check that setting an oversized field fails properly
                metadata = self.empty_metadata()
                metadata.track_name = oversized_text
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertNotEqual(metadata.track_name, oversized_text)

                # check that setting an oversized image fails properly
                metadata = self.empty_metadata()
                metadata.add_image(oversized_image)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertNotEqual(metadata.images(), [oversized_image])
            finally:
                temp_file.close()

    @METADATA_FLAC
    def test_totals(self):
        metadata = self.empty_metadata()
        metadata.get_block(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
            )[u"TRACKNUMBER"] = [u"2/4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata.get_block(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
            )[u"DISCNUMBER"] = [u"1/3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

    @METADATA_FLAC
    def test_clean(self):
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_ZEROES,
                                     CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_FIX_IMAGE_FIELDS,
                                     CLEAN_FLAC_REMOVE_SEEKPOINTS,
                                     CLEAN_FLAC_REORDER_SEEKPOINTS,
                                     CLEAN_FLAC_MULITPLE_STREAMINFO,
                                     CLEAN_FLAC_MULTIPLE_VORBISCOMMENT,
                                     CLEAN_FLAC_MULTIPLE_SEEKTABLE,
                                     CLEAN_FLAC_MULTIPLE_CUESHEET)
        # check no blocks
        metadata = audiotools.FlacMetaData([])
        (cleaned, results) = metadata.clean()
        self.assertEqual(metadata, cleaned)
        self.assertEqual(results, [])

        # check trailing whitespace
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT([u"TITLE=Foo "], u"")])
        self.assertEqual(metadata.track_name, u'Foo ')
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(results,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"TITLE"}])

        # check leading whitespace
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT([u"TITLE= Foo"], u"")])
        self.assertEqual(metadata.track_name, u' Foo')
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(results,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": u"TITLE"}])

        # check leading zeroes
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT([u"TRACKNUMBER=01"], u"")])
        self.assertEqual(
            metadata.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u"TRACKNUMBER"],
            [u"01"])
        (cleaned, results) = metadata.clean()
        self.assertEqual(
            cleaned.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u"TRACKNUMBER"],
            [u"1"])
        self.assertEqual(results,
                         [CLEAN_REMOVE_LEADING_ZEROES %
                          {"field": u"TRACKNUMBER"}])

        # check empty fields
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT([u"TITLE=  "], u"")])
        self.assertEqual(
            metadata.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[u"TITLE"], [u'  '])
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned,
                         audiotools.FlacMetaData([
                             audiotools.flac.Flac_VORBISCOMMENT([], u"")]))

        self.assertEqual(results,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": u"TITLE"}])

        # check mis-tagged images
        with open("metadata_flac_clean.jpg", "rb") as jpg:
            metadata = audiotools.FlacMetaData(
                [audiotools.flac.Flac_PICTURE(
                 0, u"image/jpeg", u"", 20, 20, 24, 10,
                 jpg.read())])
        self.assertEqual(
            len(metadata.get_blocks(audiotools.flac.Flac_PICTURE.BLOCK_ID)), 1)
        image = metadata.images()[0]
        self.assertEqual(image.mime_type, u"image/jpeg")
        self.assertEqual(image.width, 20)
        self.assertEqual(image.height, 20)
        self.assertEqual(image.color_depth, 24)
        self.assertEqual(image.color_count, 10)

        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FIX_IMAGE_FIELDS])
        self.assertEqual(
            len(cleaned.get_blocks(audiotools.flac.Flac_PICTURE.BLOCK_ID)), 1)
        image = cleaned.images()[0]
        self.assertEqual(image.mime_type, u"image/png")
        self.assertEqual(image.width, 10)
        self.assertEqual(image.height, 10)
        self.assertEqual(image.color_depth, 8)
        self.assertEqual(image.color_count, 1)

        # check seektable with empty seekpoints
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_SEEKTABLE([(0, 10, 10),
                                             (10, 20, 0),
                                             (10, 20, 0),
                                             (10, 20, 0),
                                             (10, 20, 20)])])
        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_REMOVE_SEEKPOINTS])
        self.assertEqual(
            cleaned.get_block(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            audiotools.flac.Flac_SEEKTABLE([(0, 10, 10),
                                            (10, 20, 20)]))

        # check seektable with duplicate seekpoints
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                             (2, 20, 10),
                                             (2, 20, 10),
                                             (2, 20, 10),
                                             (4, 40, 10)])])
        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_REORDER_SEEKPOINTS])
        self.assertEqual(
            cleaned.get_block(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                            (2, 20, 10),
                                            (4, 40, 10)]))

        # check seektable with mis-ordered seekpoints
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                             (6, 60, 10),
                                             (4, 40, 10),
                                             (2, 20, 10),
                                             (8, 80, 10)])])
        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_REORDER_SEEKPOINTS])
        self.assertEqual(
            cleaned.get_block(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                            (2, 20, 10),
                                            (4, 40, 10),
                                            (6, 60, 10),
                                            (8, 80, 10)]))

        # check that cleanup doesn't disturb other metadata blocks
        # FIXME
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_STREAMINFO(
                minimum_block_size=4096,
                maximum_block_size=4096,
                minimum_frame_size=14,
                maximum_frame_size=18,
                sample_rate=44100,
                channels=2,
                bits_per_sample=16,
                total_samples=149606016,
                md5sum=(b'\xae\x87\x1c\x8e\xe1\xfc\x16\xde' +
                        b'\x86\x81&\x8e\xc8\xd52\xff')),
            audiotools.flac.Flac_APPLICATION(application_id=b"FOOZ",
                                             data=b"KELP"),
            audiotools.flac.Flac_SEEKTABLE([
                (0, 0, 4096),
                (8335360, 30397, 4096),
                (8445952, 30816, 4096),
                (17379328, 65712, 4096),
                (17489920, 66144, 4096),
                (28041216, 107360, 4096),
                (28151808, 107792, 4096),
                (41672704, 160608, 4096),
                (41783296, 161040, 4096),
                (54444032, 210496, 4096),
                (54558720, 210944, 4096),
                (65687552, 254416, 4096),
                (65802240, 254864, 4096),
                (76267520, 295744, 4096),
                (76378112, 296176, 4096),
                (89624576, 347920, 4096),
                (89739264, 348368, 4096),
                (99688448, 387232, 4096),
                (99803136, 387680, 4096),
                (114176000, 443824, 4096),
                (114286592, 444256, 4096),
                (125415424, 487728, 4096),
                (125526016, 488160, 4096),
                (138788864, 539968, 4096),
                (138903552, 540416, 4096)]),
            audiotools.flac.Flac_VORBISCOMMENT([u"TITLE=Foo "], u""),
            audiotools.flac.Flac_CUESHEET(
                catalog_number=b'4560248013904' + b"\x00" * (128 - 13),
                lead_in_samples=88200,
                is_cdda=1,
                tracks=[
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=0,
                        number=1,
                        ISRC=b'JPK631002201',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=0,
                                offset=0,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=8336076,
                        number=2,
                        ISRC=b'JPK631002202',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=8336076,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=8336076,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=17379516,
                        number=3,
                        ISRC=b'JPK631002203',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=17379516,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=17379516,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=28042308,
                        number=4,
                        ISRC=b'JPK631002204',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=28042308,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=28042308,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=41672736,
                        number=5,
                        ISRC=b'JPK631002205',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=41672736,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=41672736,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=54447624,
                        number=6,
                        ISRC=b'JPK631002206',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=54447624,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=54447624,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=65689596,
                        number=7,
                        ISRC=b'JPK631002207',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=65689596,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=65689596,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=76267716,
                        number=8,
                        ISRC=b'JPK631002208',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=76267716,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=76267716,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=89627076,
                        number=9,
                        ISRC=b'JPK631002209',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=89627076,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=89627076,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=99691872,
                        number=10,
                        ISRC=b'JPK631002210',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=99691872,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=99691872,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=114176076,
                        number=11,
                        ISRC=b'JPK631002211',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=114176076,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=114176076,
                                offset=113484,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=125415696,
                        number=12,
                        ISRC=b'JPK631002212',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=125415696,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=125415696,
                                offset=114072,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=138791520,
                        number=13,
                        ISRC=b'JPK631002213',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=138791520,
                                offset=0,
                                number=0),
                            audiotools.flac.Flac_CUESHEET_index(
                                track_offset=138791520,
                                offset=114072,
                                number=1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=149606016,
                        number=170,
                        ISRC=b"\x00" * 12,
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[])]),
            audiotools.flac.Flac_PICTURE(0, u"image/jpeg", u"",
                                         500, 500, 24, 0, TEST_COVER1)])

        self.assertEqual([b.BLOCK_ID for b in metadata.block_list],
                         [audiotools.flac.Flac_STREAMINFO.BLOCK_ID,
                          audiotools.flac.Flac_APPLICATION.BLOCK_ID,
                          audiotools.flac.Flac_SEEKTABLE.BLOCK_ID,
                          audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID,
                          audiotools.flac.Flac_CUESHEET.BLOCK_ID,
                          audiotools.flac.Flac_PICTURE.BLOCK_ID])

        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"TITLE"}])

        for block_id in [audiotools.flac.Flac_STREAMINFO.BLOCK_ID,
                         audiotools.flac.Flac_APPLICATION.BLOCK_ID,
                         audiotools.flac.Flac_SEEKTABLE.BLOCK_ID,
                         audiotools.flac.Flac_CUESHEET.BLOCK_ID,
                         audiotools.flac.Flac_PICTURE.BLOCK_ID]:
            self.assertEqual(metadata.get_blocks(block_id),
                             cleaned.get_blocks(block_id))
        self.assertNotEqual(
            metadata.get_blocks(audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID),
            cleaned.get_blocks(audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID))

        # ensure second STREAMINFO block is removed, if present
        streaminfo1 = audiotools.flac.Flac_STREAMINFO(
            1, 10, 1, 20, 44100, 2, 16, 5000, chr(0) * 16)
        streaminfo2 = audiotools.flac.Flac_STREAMINFO(
            1, 20, 1, 30, 88200, 4, 24, 5000, chr(0) * 16)
        self.assertNotEqual(streaminfo1, streaminfo2)
        metadata = audiotools.flac.FlacMetaData([streaminfo1, streaminfo2])
        self.assertEqual(
            metadata.get_blocks(audiotools.flac.Flac_STREAMINFO.BLOCK_ID),
            [streaminfo1, streaminfo2])

        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_MULITPLE_STREAMINFO])
        self.assertEqual(
            cleaned.get_blocks(audiotools.flac.Flac_STREAMINFO.BLOCK_ID),
            [streaminfo1])

        # ensure second VORBISCOMMENT block is removed, if present
        comment1 = audiotools.flac.Flac_VORBISCOMMENT(
            [u"TITLE=Foo"],
            u"vendor string")

        comment2 = audiotools.flac.Flac_VORBISCOMMENT(
            [u"TITLE=Bar"],
            u"vendor string")
        self.assertNotEqual(comment1, comment2)
        metadata = audiotools.flac.FlacMetaData([streaminfo1,
                                                 comment1,
                                                 comment2])
        self.assertEqual(metadata.get_blocks(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID),
            [comment1, comment2])

        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_MULTIPLE_VORBISCOMMENT])
        self.assertEqual(
            cleaned.get_blocks(audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID),
            [comment1])

        # ensure second SEEKTABLE block is removed, if present
        seektable1 = audiotools.flac.Flac_SEEKTABLE([(0, 0, 4096),
                                                     (4096, 10, 4096)])
        seektable2 = audiotools.flac.Flac_SEEKTABLE([(0, 0, 4096),
                                                     (4096, 10, 4096),
                                                     (8192, 20, 4096)])
        self.assertNotEqual(seektable1, seektable2)
        metadata = audiotools.flac.FlacMetaData([streaminfo1,
                                                 seektable1,
                                                 seektable2])

        self.assertEqual(metadata.get_blocks(
            audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            [seektable1, seektable2])

        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_MULTIPLE_SEEKTABLE])
        self.assertEqual(
            cleaned.get_blocks(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            [seektable1])

        # ensure second CUESHEET block is removed, if present
        cuesheet1 = audiotools.flac.Flac_CUESHEET.converted(
            audiotools.read_sheet("metadata_flac_cuesheet-1.cue"),
            160107696,
            44100)
        cuesheet2 = audiotools.flac.Flac_CUESHEET.converted(
            audiotools.read_sheet("metadata_flac_cuesheet-2.cue"),
            119882616,
            44100)

        self.assertNotEqual(cuesheet1, cuesheet2)
        metadata = audiotools.flac.FlacMetaData([streaminfo1,
                                                 cuesheet1,
                                                 cuesheet2])

        self.assertEqual(metadata.get_blocks(
            audiotools.flac.Flac_CUESHEET.BLOCK_ID),
            [cuesheet1, cuesheet2])

        (cleaned, results) = metadata.clean()
        self.assertEqual(results,
                         [CLEAN_FLAC_MULTIPLE_CUESHEET])
        self.assertEqual(
            cleaned.get_blocks(audiotools.flac.Flac_CUESHEET.BLOCK_ID),
            [cuesheet1])

    @METADATA_FLAC
    def test_replay_gain(self):
        import test_streams

        for input_class in [audiotools.FlacAudio, audiotools.VorbisAudio]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + input_class.SUFFIX)
            try:
                track1 = input_class.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assertIsNone(
                    track1.get_replay_gain(),
                    "ReplayGain present for class {}".format(input_class.NAME))

                track1.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                audiotools.add_replay_gain([track1])
                self.assertEqual(track1.get_metadata().track_name, u"Foo")
                self.assertIsNotNone(
                    track1.get_replay_gain(),
                    "ReplayGain not present for class {}".format(
                        input_class.NAME))

                for output_class in [audiotools.FlacAudio]:
                    temp2 = tempfile.NamedTemporaryFile(
                        suffix="." + input_class.SUFFIX)
                    try:
                        # ensure file with no metadata blocks
                        # has metadata set correctly
                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))
                        metadata = track2.get_metadata()
                        for block_id in range(1, 7):
                            metadata.replace_blocks(block_id, [])
                        track2.update_metadata(metadata)
                        self.assertIsNone(track2.get_replay_gain())

                        audiotools.add_replay_gain([track2])
                        self.assertIsNotNone(track2.get_replay_gain())

                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))

                        # ensure that ReplayGain doesn't get ported
                        # via set_metadata()
                        self.assertIsNone(
                            track2.get_replay_gain(),
                            "ReplayGain present for class {}".format(
                                output_class.NAME))
                        track2.set_metadata(track1.get_metadata())
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Foo")
                        self.assertIsNone(
                            track2.get_replay_gain(),
                            "ReplayGain present for class {} from {}".format(
                                output_class.NAME, input_class.NAME))

                        # and if ReplayGain is already set,
                        # ensure set_metadata() doesn't remove it
                        audiotools.add_replay_gain([track2])
                        old_replay_gain = track2.get_replay_gain()
                        self.assertIsNotNone(old_replay_gain)
                        track2.set_metadata(
                            audiotools.MetaData(track_name=u"Bar"))
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Bar")
                        self.assertEqual(track2.get_replay_gain(),
                                         old_replay_gain)
                    finally:
                        temp2.close()
            finally:
                temp1.close()

    @METADATA_FLAC
    def test_getattr(self):
        # track_number grabs the first available integer, if any
        self.assertEqual(
            audiotools.FlacMetaData([]).track_number, None)

        self.assertEqual(
            audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=10"],
                    u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=10",
                     u"TRACKNUMBER=5"],
                    u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=foo 10 bar"],
                    u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=foo",
                     u"TRACKNUMBER=10"],
                    u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=foo",
                     u"TRACKNUMBER=foo 10 bar"],
                    u"vendor")]).track_number,
            10)

        # track_number is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"tRaCkNuMbEr=10"],
                    u"vendor")]).track_number,
            10)

        # album_number grabs the first available integer, if any
        self.assertEqual(
            audiotools.FlacMetaData([]).album_number, None)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=20"],
                    u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=20",
                     u"DISCNUMBER=5"],
                    u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=foo 20 bar"],
                    u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=foo",
                     u"DISCNUMBER=20"],
                    u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=foo",
                     u"DISCNUMBER=foo 20 bar"],
                    u"vendor")]).album_number,
            20)

        # album_number is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"dIsCnUmBeR=20"],
                    u"vendor")]).album_number,
            20)

        # track_total grabs the first available TRACKTOTAL integer
        # before falling back on slashed fields, if any
        self.assertEqual(
            audiotools.FlacMetaData([]).track_total, None)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKTOTAL=15"],
                    u"vendor")]).track_total,
            15)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=5/10"],
                    u"vendor")]).track_total,
            10)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=5/10",
                     u"TRACKTOTAL=15"],
                    u"vendor")]).track_total,
            15)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKTOTAL=15",
                     u"TRACKNUMBER=5/10"],
                    u"vendor")]).track_total,
            15)

        # track_total is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"tracktotal=15"],
                    u"vendor")]).track_total,
            15)

        # track_total supports aliases
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TOTALTRACKS=15"],
                    u"vendor")]).track_total,
            15)

        # album_total grabs the first available DISCTOTAL integer
        # before falling back on slashed fields, if any
        self.assertEqual(
            audiotools.FlacMetaData([]).album_total, None)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCTOTAL=25"],
                    u"vendor")]).album_total,
            25)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=10/30"],
                    u"vendor")]).album_total,
            30)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=10/30",
                     u"DISCTOTAL=25"],
                    u"vendor")]).album_total,
            25)

        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCTOTAL=25",
                     u"DISCNUMBER=10/30"],
                    u"vendor")]).album_total,
            25)

        # album_total is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"disctotal=25"],
                    u"vendor")]).album_total,
            25)

        # album_total supports aliases
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TOTALDISCS=25"],
                    u"vendor")]).album_total,
            25)

        # other fields grab the first available item
        self.assertEqual(
            audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE=first",
                     u"TITLE=last"],
                    u"vendor")]).track_name,
            u"first")

    @METADATA_FLAC
    def test_setattr(self):
        # track_number adds new field if necessary
        for metadata in [audiotools.FlacMetaData(
                         [audiotools.flac.Flac_VORBISCOMMENT([],
                                                             u"vendor")]),
                         audiotools.FlacMetaData([])]:

            self.assertIsNone(metadata.track_number)
            metadata.track_number = 11
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"TRACKNUMBER=11"])
            self.assertEqual(metadata.track_number, 11)

            metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=blah"],
                    u"vendor")])
            self.assertIsNone(metadata.track_number)
            metadata.track_number = 11
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"TRACKNUMBER=blah",
                              u"TRACKNUMBER=11"])
            self.assertEqual(metadata.track_number, 11)

        # track_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=10/12"], u"vendor")])
        self.assertEqual(metadata.track_number, 10)
        metadata.track_number = 11
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=11/12"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=foo 10 bar"],
                u"vendor")])
        self.assertEqual(metadata.track_number, 10)
        metadata.track_number = 11
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=foo 11 bar"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=foo 10 bar",
                 u"TRACKNUMBER=blah"],
                u"vendor")])
        self.assertEqual(metadata.track_number, 10)
        metadata.track_number = 11
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=foo 11 bar",
                          u"TRACKNUMBER=blah"])
        self.assertEqual(metadata.track_number, 11)

        # album_number adds new field if necessary
        for metadata in [
            audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT([], u"vendor")]),
                audiotools.FlacMetaData([])]:

            self.assertIsNone(metadata.album_number)
            metadata.album_number = 3
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"DISCNUMBER=3"])
            self.assertEqual(metadata.album_number, 3)

            metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=blah"],
                    u"vendor")])
            self.assertIsNone(metadata.album_number)
            metadata.album_number = 3
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"DISCNUMBER=blah",
                              u"DISCNUMBER=3"])
            self.assertEqual(metadata.album_number, 3)

        # album_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2/4"], u"vendor")])
        self.assertEqual(metadata.album_number, 2)
        metadata.album_number = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=3/4"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=foo 2 bar"],
                u"vendor")])
        self.assertEqual(metadata.album_number, 2)
        metadata.album_number = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=foo 3 bar"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=foo 2 bar",
                 u"DISCNUMBER=blah"],
                u"vendor")])
        self.assertEqual(metadata.album_number, 2)
        metadata.album_number = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=foo 3 bar",
                          u"DISCNUMBER=blah"])
        self.assertEqual(metadata.album_number, 3)

        # track_total adds new TRACKTOTAL field if necessary
        for metadata in [
            audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT([], u"vendor")]),
                audiotools.FlacMetaData([])]:

            self.assertIsNone(metadata.track_total)
            metadata.track_total = 12
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"TRACKTOTAL=12"])
            self.assertEqual(metadata.track_total, 12)

            metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKTOTAL=blah"],
                    u"vendor")])
            self.assertIsNone(metadata.track_total)
            metadata.track_total = 12
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"TRACKTOTAL=blah",
                              u"TRACKTOTAL=12"])
            self.assertEqual(metadata.track_total, 12)

        # track_total updates first integer TRACKTOTAL field first if possible
        # including aliases
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKTOTAL=blah",
                 u"TRACKTOTAL=2"],
                u"vendor")])
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=blah",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TOTALTRACKS=blah",
                 u"TOTALTRACKS=2"],
                u"vendor")])
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TOTALTRACKS=blah",
                          u"TOTALTRACKS=3"])
        self.assertEqual(metadata.track_total, 3)

        # track_total updates slashed TRACKNUMBER field if necessary
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1/4",
                 u"TRACKTOTAL=2"],
                u"vendor")])
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1/4",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1/4"],
                u"vendor")])
        self.assertEqual(metadata.track_total, 4)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1/3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER= foo / 4 bar"],
                u"vendor")])
        self.assertEqual(metadata.track_total, 4)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER= foo / 3 bar"])
        self.assertEqual(metadata.track_total, 3)

        # album_total adds new DISCTOTAL field if necessary
        for metadata in [audiotools.FlacMetaData(
                [audiotools.flac.Flac_VORBISCOMMENT([], u"vendor")]),
                audiotools.FlacMetaData([])]:

            self.assertIsNone(metadata.album_total)
            metadata.album_total = 4
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"DISCTOTAL=4"])
            self.assertEqual(metadata.album_total, 4)

            metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCTOTAL=blah"],
                    u"vendor")])
            self.assertIsNone(metadata.album_total)
            metadata.album_total = 4
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"DISCTOTAL=blah",
                              u"DISCTOTAL=4"])
            self.assertEqual(metadata.album_total, 4)

        # album_total updates DISCTOTAL field first if possible
        # including aliases
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCTOTAL=blah",
                 u"DISCTOTAL=3"],
                u"vendor")])
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 4
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCTOTAL=blah",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TOTALDISCS=blah",
                 u"TOTALDISCS=3"],
                u"vendor")])
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 4
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TOTALDISCS=blah",
                          u"TOTALDISCS=4"])
        self.assertEqual(metadata.album_total, 4)

        # album_total updates slashed DISCNUMBER field if necessary
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2/3",
                 u"DISCTOTAL=5"],
                u"vendor")])
        self.assertEqual(metadata.album_total, 5)
        metadata.album_total = 6
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2/3",
                          u"DISCTOTAL=6"])
        self.assertEqual(metadata.album_total, 6)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2/3"],
                u"vendor")])
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 6
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2/6"])
        self.assertEqual(metadata.album_total, 6)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER= foo / 3 bar"],
                u"vendor")])
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 6
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER= foo / 6 bar"])
        self.assertEqual(metadata.album_total, 6)

        # other fields update the first match
        # while leaving the rest alone
        metadata = audiotools.FlacMetaData([])
        metadata.track_name = u"blah"
        self.assertEqual(metadata.track_name, u"blah")
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TITLE=blah"])

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TITLE=foo",
                 u"TITLE=bar",
                 u"FOO=baz"],
                u"vendor")])
        metadata.track_name = u"blah"
        self.assertEqual(metadata.track_name, u"blah")
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TITLE=blah",
                          u"TITLE=bar",
                          u"FOO=baz"])

        # setting field to an empty string is okay
        for metadata in [
                audiotools.FlacMetaData(
                    [audiotools.flac.Flac_VORBISCOMMENT([], u"vendor")]),
                audiotools.FlacMetaData([])]:
            metadata.track_name = u""
            self.assertEqual(metadata.track_name, u"")
            self.assertEqual(metadata.get_block(4).comment_strings,
                             [u"TITLE="])

    @METADATA_FLAC
    def test_delattr(self):
        # deleting nonexistent field is okay
        for field in audiotools.MetaData.FIELDS:
            for metadata in [
                    audiotools.FlacMetaData(
                        [audiotools.flac.Flac_VORBISCOMMENT([], u"vendor")]),
                    audiotools.FlacMetaData([])]:

                delattr(metadata, field)
                self.assertIsNone(getattr(metadata, field))

        # deleting field removes all instances of it
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_VORBISCOMMENT(
                [u"TITLE=track name"],
                u"vendor")])
        del(metadata.track_name)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_VORBISCOMMENT(
                [u"TITLE=track name",
                 u"ALBUM=album name"],
                u"vendor")])
        del(metadata.track_name)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"ALBUM=album name"])
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_VORBISCOMMENT(
                [u"TITLE=track name",
                 u"TITLE=track name 2",
                 u"ALBUM=album name",
                 u"TITLE=track name 3"],
                u"vendor")])
        del(metadata.track_name)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"ALBUM=album name"])
        self.assertIsNone(metadata.track_name)

        # setting field to None is the same as deleting field
        metadata = audiotools.FlacMetaData([])
        metadata.track_name = None
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TITLE=track name"],
                u"vendor")])
        metadata.track_name = None
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        # deleting track_number removes TRACKNUMBER field
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1"],
                u"vendor")])
        del(metadata.track_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        # deleting slashed TRACKNUMBER converts it to fresh TRACKTOTAL field
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1/3"],
                u"vendor")])
        del(metadata.track_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=3"])
        self.assertIsNone(metadata.track_number)

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1/3",
                 u"TRACKTOTAL=4"],
                u"vendor")])
        self.assertEqual(metadata.track_total, 4)
        del(metadata.track_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=4"])
        self.assertEqual(metadata.track_total, 4)
        self.assertIsNone(metadata.track_number)

        # deleting track_total removes TRACKTOTAL/TOTALTRACKS fields
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKTOTAL=3",
                 u"TOTALTRACKS=4"],
                u"vendor")])
        del(metadata.track_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertIsNone(metadata.track_total)

        # deleting track_total also removes slashed side of TRACKNUMBER fields
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1/3"],
                u"vendor")])
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER=1 / foo 3 baz"],
                u"vendor")])
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"TRACKNUMBER= foo 1 bar / blah 4 baz"], u"vendor")])
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER= foo 1 bar"])

        # deleting album_number removes DISCNUMBER field
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2"],
                u"vendor")])
        del(metadata.album_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])

        # deleting slashed DISCNUMBER converts it to fresh DISCTOTAL field
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2/4"],
                u"vendor")])
        del(metadata.album_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCTOTAL=4"])

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2/4",
                 u"DISCTOTAL=5"],
                u"vendor")])
        self.assertEqual(metadata.album_total, 5)
        del(metadata.album_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCTOTAL=5"])
        self.assertEqual(metadata.album_total, 5)

        # deleting album_total removes DISCTOTAL/TOTALDISCS fields
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCTOTAL=4",
                 u"TOTALDISCS=5"],
                u"vendor")])
        del(metadata.album_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertIsNone(metadata.album_total)

        # deleting album_total also removes slashed side of DISCNUMBER fields
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2/4"],
                u"vendor")])
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER=2 / foo 4 baz"],
                u"vendor")])
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_VORBISCOMMENT(
                [u"DISCNUMBER= foo 2 bar / blah 4 baz"], u"vendor")])
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER= foo 2 bar"])

    @LIB_CUESHEET
    @METADATA_FLAC
    def test_flac_cuesheet(self):
        self.assertTrue(
            audiotools.BIN.can_execute(audiotools.BIN["metaflac"]),
            "reference binary metaflac(1) required for this test")

        from test import EXACT_SILENCE_PCM_Reader
        from shutil import copy
        from audiotools.cue import read_cuesheet
        import subprocess

        for (cuesheet_filename,
             total_pcm_frames,
             sample_rate) in [("metadata_flac_cuesheet-1.cue",
                               160107696,
                               44100),
                              ("metadata_flac_cuesheet-2.cue",
                               119882616,
                               44100),
                              ("metadata_flac_cuesheet-3.cue",
                               122513916,
                               44100)]:
            temp_flac1 = tempfile.NamedTemporaryFile(suffix=".flac")
            temp_flac2 = tempfile.NamedTemporaryFile(suffix=".flac")
            try:
                # build a FLAC full of silence with the total number of frames
                flac1 = audiotools.FlacAudio.from_pcm(
                    temp_flac1.name,
                    EXACT_SILENCE_PCM_Reader(total_pcm_frames),
                    total_pcm_frames=total_pcm_frames)

                # copy it to another temp file
                copy(temp_flac1.name, temp_flac2.name)

                # set_cuesheet() to first FLAC file
                flac1.set_cuesheet(read_cuesheet(cuesheet_filename))

                # import cuesheet to first FLAC file with metaflac
                # and get its CUESHEET block
                temp_cue = tempfile.NamedTemporaryFile(suffix=".cue")
                try:
                    with open(cuesheet_filename, "rb") as f:
                        temp_cue.write(f.read())
                        temp_cue.flush()

                    self.assertEqual(
                        subprocess.call([audiotools.BIN["metaflac"],
                                         "--import-cuesheet-from",
                                         temp_cue.name, temp_flac2.name]), 0)
                finally:
                    temp_cue.close()

                flac2 = audiotools.FlacAudio(temp_flac2.name)

                # ensure get_cuesheet() data matches
                self.assertEqual(flac1.get_cuesheet(),
                                 flac2.get_cuesheet())

                # ensure CUESHEET blocks match in get_metadata()
                self.assertEqual(flac1.get_metadata().get_block(5),
                                 flac2.get_metadata().get_block(5))
            finally:
                temp_flac1.close()
                temp_flac2.close()

    @METADATA_FLAC
    def test_id3(self):
        from zlib import decompress

        id3v2_tag = decompress(b'x\x9c\xf3t1ff\x00\x02\xd6\xd8\x90' +
                               b'\x00WC C\x00\x88=]\x8c\x15BR\x8bK\x14' +
                               b'\x1c\x8bJ2\x8bKB<C\x8c\x80\xa2|\xc82' +
                               b'\xc1\xf9y\xe9\x0c\xa3`\x14\x0c\r\x00' +
                               b'\x00{g\x0c\xcf')
        id3v1_tag = decompress(b'x\x9c\x0bqt\xf7t1V\x08I-.Q\x08\xce' +
                               b'\xcfKg@\x07pY\xc7\xa2\x92\xcc\xe2\x12' +
                               b'\x0cy\xca\xc0\x7f\x00\x1dK\x0b*')

        dummy_flac = tempfile.NamedTemporaryFile(suffix=".flac")
        dummy_id3flac = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            # build test FLAC file with test metadata
            flac = audiotools.FlacAudio.from_pcm(
                dummy_flac.name,
                BLANK_PCM_Reader(2))
            metadata = flac.get_metadata()
            metadata.track_name = u"Test Name"
            metadata.album_name = u"Test Album"
            flac.update_metadata(metadata)
            self.assertEqual(flac.verify(), True)

            # wrap in ID3v2/ID3v1 tags (with different values)
            dummy_id3flac.write(id3v2_tag)
            with open(dummy_flac.name, "rb") as f:
                dummy_id3flac.write(f.read())
            dummy_id3flac.write(id3v1_tag)
            dummy_id3flac.flush()

            # ensure file tests okay
            flac2 = audiotools.open(dummy_id3flac.name)
            self.assertEqual(flac2.verify(), True)

            # ensure start and end of file still match tags
            with open(dummy_id3flac.name, "rb") as f:
                self.assertEqual(f.read()[0:len(id3v2_tag)], id3v2_tag)
            with open(dummy_id3flac.name, "rb") as f:
                self.assertEqual(f.read()[-len(id3v1_tag):], id3v1_tag)

            # ensure metadata values don't come from ID3v2/ID3v1
            metadata = flac2.get_metadata()
            self.assertEqual(metadata.track_name, u"Test Name")
            self.assertEqual(metadata.album_name, u"Test Album")

            # update metadata with new values
            # (these are short enough that padding should still be used)
            metadata.track_name = u"Test Name2"
            metadata.album_name = u"Test Album2"
            flac2.update_metadata(metadata)

            # ensure start and end of file still match tags
            with open(dummy_id3flac.name, "rb") as f:
                self.assertEqual(f.read()[0:len(id3v2_tag)], id3v2_tag)
            with open(dummy_id3flac.name, "rb") as f:
                self.assertEqual(f.read()[-len(id3v1_tag):], id3v1_tag)

            # ensure file still tests okay
            self.assertEqual(flac2.verify(), True)

            # ensure metadata values still don't come from ID3v2/ID3v1
            metadata = flac2.get_metadata()
            self.assertEqual(metadata.track_name, u"Test Name2")
            self.assertEqual(metadata.album_name, u"Test Album2")

            # update metadata with large values
            # (this should be long enough that padding can't be used)
            metadata.comment = u" " * 2 ** 20
            flac2.update_metadata(metadata)

            # ensure start and end of file still match tags
            with open(dummy_id3flac.name, "rb") as f:
                self.assertEqual(f.read()[0:len(id3v2_tag)], id3v2_tag)
            with open(dummy_id3flac.name, "rb") as f:
                self.assertEqual(f.read()[-len(id3v1_tag):], id3v1_tag)

            # ensure file still tests okay
            self.assertEqual(flac2.verify(), True)

            # ensure metadata matches large values
            metadata = flac2.get_metadata()
            self.assertEqual(metadata.track_name, u"Test Name2")
            self.assertEqual(metadata.album_name, u"Test Album2")
            self.assertEqual(metadata.comment, u" " * 2 ** 20)
        finally:
            dummy_flac.close()
            dummy_id3flac.close()

    @METADATA_FLAC
    def test_intersection2(self):
        from audiotools.flac import FlacMetaData
        from audiotools.flac import Flac_STREAMINFO
        from audiotools.flac import Flac_APPLICATION
        from audiotools.flac import Flac_PADDING

        base = FlacMetaData([Flac_STREAMINFO(0, 1, 2, 3, 4, 5, 6, 7,
                                             b"\00" * 16),
                             Flac_APPLICATION(b"test", b"data"),
                             Flac_PADDING(1234)])

        # test no matches
        no_matches = FlacMetaData([Flac_STREAMINFO(7, 6, 5, 4, 3, 2, 1, 0,
                                                   b"\x01" * 16),
                                   Flac_PADDING(1235)])
        test = base.intersection(no_matches)
        self.assertIs(type(test), FlacMetaData)
        self.assertEqual(test.block_list, [])

        # test some matches
        some_matches = FlacMetaData([Flac_PADDING(1235),
                                     Flac_STREAMINFO(0, 1, 2, 3, 4, 5, 6, 7,
                                                     b"\00" * 16)])
        test = base.intersection(some_matches)
        self.assertIs(type(test), FlacMetaData)
        self.assertEqual(test.block_list,
                         [Flac_STREAMINFO(0, 1, 2, 3, 4, 5, 6, 7, b"\00" * 16)])

        some_matches = FlacMetaData([Flac_PADDING(1235),
                                     Flac_APPLICATION(b"test", b"data"),
                                     Flac_PADDING(1234)])
        test = base.intersection(some_matches)
        self.assertIs(type(test), FlacMetaData)
        self.assertEqual(test.block_list,
                         [Flac_APPLICATION(b"test", b"data"),
                          Flac_PADDING(1234)])

        # test all matches
        all_matches = FlacMetaData([Flac_PADDING(1234),
                                    Flac_STREAMINFO(0, 1, 2, 3, 4, 5, 6, 7,
                                                    b"\00" * 16),
                                    Flac_APPLICATION(b"test", b"data")])
        test = base.intersection(all_matches)
        self.assertIs(type(test), FlacMetaData)
        self.assertEqual(test.block_list,
                         [Flac_STREAMINFO(0, 1, 2, 3, 4, 5, 6, 7,
                                          b"\00" * 16),
                          Flac_APPLICATION(b"test", b"data"),
                          Flac_PADDING(1234)])


class M4AMetaDataTest(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.M4A_META_Atom
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "composer_name",
                                 "performer_name",
                                 "copyright",
                                 "year",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.M4AAudio,
                                  audiotools.ALACAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_M4A
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # set_metadata can't alter the '\xa9too' field
                metadata = track.get_metadata()
                old_ilst = metadata.ilst_atom()[b"\xa9too"]
                new_ilst = audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                    b'\xa9too',
                    [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(
                        0, 1, b"Fooz")])
                metadata.ilst_atom().replace_child(new_ilst)
                self.assertEqual(metadata.ilst_atom()[b"\xa9too"],
                                 new_ilst)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.ilst_atom()[b"\xa9too"], old_ilst)

                # update_metadata can alter the '\xa9too' field
                metadata = track.get_metadata()
                old_ilst = metadata.ilst_atom()[b"\xa9too"]
                new_ilst = audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                    b'\xa9too',
                    [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(
                        0, 1, b"Fooz")])
                metadata.ilst_atom().replace_child(new_ilst)
                self.assertEqual(metadata.ilst_atom()[b"\xa9too"],
                                 new_ilst)
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.ilst_atom()[b"\xa9too"], new_ilst)
            finally:
                temp_file.close()

    @METADATA_M4A
    def test_foreign_field(self):
        from audiotools.m4a_atoms import M4A_META_Atom
        from audiotools.m4a_atoms import M4A_HDLR_Atom
        from audiotools.m4a_atoms import M4A_Tree_Atom
        from audiotools.m4a_atoms import M4A_ILST_Leaf_Atom
        from audiotools.m4a_atoms import M4A_ILST_Unicode_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_TRKN_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_DISK_Data_Atom
        from audiotools.m4a_atoms import M4A_FREE_Atom

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_HDLR_Atom(0, 0, b'\x00\x00\x00\x00',
                           b'mdir', b'appl', 0, 0, b'', 0),
             M4A_Tree_Atom(
                 b'ilst',
                 [M4A_ILST_Leaf_Atom(
                     b'\xa9nam',
                     [M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name")]),
                  M4A_ILST_Leaf_Atom(
                      b'\xa9alb',
                      [M4A_ILST_Unicode_Data_Atom(0, 1, b"Album Name")]),
                  M4A_ILST_Leaf_Atom(
                      b'trkn', [M4A_ILST_TRKN_Data_Atom(1, 3)]),
                  M4A_ILST_Leaf_Atom(
                      b'disk', [M4A_ILST_DISK_Data_Atom(2, 4)]),
                  M4A_ILST_Leaf_Atom(
                      b'\xa9foo',
                      [M4A_ILST_Unicode_Data_Atom(0, 1, b"Bar")])]),
             M4A_FREE_Atom(1024)])

        for format in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX) as temp_file:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertEqual(metadata, metadata2)
                self.assertEqual(metadata.__class__, metadata2.__class__)
                self.assertEqual(
                    track.get_metadata().ilst_atom()[b"\xa9foo"].data,
                    b"\x00\x00\x00\x13data\x00\x00\x00\x01\x00\x00\x00\x00Bar")

    @METADATA_M4A
    def test_field_mapping(self):
        mapping = [('track_name', b'\xA9nam', u'a'),
                   ('artist_name', b'\xA9ART', u'b'),
                   ('year', b'\xA9day', u'c'),
                   ('album_name', b'\xA9alb', u'd'),
                   ('composer_name', b'\xA9wrt', u'e'),
                   ('comment', b'\xA9cmt', u'f'),
                   ('copyright', b'cprt', u'g'),
                   ('performer_name', b'aART', u'h')]

        for format in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX) as temp_file:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                # ensure that setting a class field
                # updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[b'ilst'][key][b'data'].data.decode('utf-8'),
                        value)
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[b'ilst'][key][b'data'].data.decode('utf-8'),
                        value)

                # ensure that updating the low-level implementation
                # is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[b'ilst'].add_child(
                        audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                            key,
                            [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(
                                0, 1, value.encode('utf-8'))]))
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[b'ilst'][key][b'data'].data.decode('utf-8'),
                        value)
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[b'ilst'][key][b'data'].data.decode('utf-8'),
                        value)

                # ensure that setting numerical fields also
                # updates the low-level implementation
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.track_number = 1
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(
                    metadata[b'ilst'][b'trkn'][b'data'].track_number,
                    1)
                self.assertEqual(
                    metadata[b'ilst'][b'trkn'][b'data'].track_total,
                    0)
                metadata.track_total = 2
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(
                    metadata[b'ilst'][b'trkn'][b'data'].track_number,
                    1)
                self.assertEqual(
                    metadata[b'ilst'][b'trkn'][b'data'].track_total,
                    2)
                del(metadata.track_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(
                    metadata[b'ilst'][b'trkn'][b'data'].track_number,
                    0)
                self.assertEqual(
                    metadata[b'ilst'][b'trkn'][b'data'].track_total,
                    2)
                del(metadata.track_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata[b'ilst'].__getitem__,
                                  b'trkn')

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.album_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(
                    metadata[b'ilst'][b'disk'][b'data'].disk_number,
                    3)
                self.assertEqual(
                    metadata[b'ilst'][b'disk'][b'data'].disk_total,
                    0)

                metadata.album_total = 4
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(
                    metadata[b'ilst'][b'disk'][b'data'].disk_number,
                    3)
                self.assertEqual(
                    metadata[b'ilst'][b'disk'][b'data'].disk_total,
                    4)
                del(metadata.album_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(
                    metadata[b'ilst'][b'disk'][b'data'].disk_number,
                    0)
                self.assertEqual(
                    metadata[b'ilst'][b'disk'][b'data'].disk_total,
                    4)
                del(metadata.album_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata[b'ilst'].__getitem__,
                                  b'disk')

    @METADATA_M4A
    def test_getattr(self):
        from audiotools.m4a_atoms import M4A_META_Atom
        from audiotools.m4a_atoms import M4A_Tree_Atom
        from audiotools.m4a_atoms import M4A_ILST_Leaf_Atom
        from audiotools.m4a_atoms import M4A_ILST_Unicode_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_TRKN_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_DISK_Data_Atom

        # no ilst atom is okay
        for attr in audiotools.MetaData.FIELDS:
            metadata = M4A_META_Atom(0, 0, [])
            self.assertIsNone(getattr(metadata, attr))

        # empty ilst atom is okay
        for attr in audiotools.MetaData.FIELDS:
            metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
            self.assertIsNone(getattr(metadata, attr))

        # fields grab the first available atom from ilst atom, if any
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst',
                           [M4A_ILST_Leaf_Atom(b'\xa9nam', [])])])
        self.assertIsNone(metadata.track_name)

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Track Name")])])])
        self.assertEqual(metadata.track_name, u"Track Name")

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Track Name")]),
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Another Name")])])])
        self.assertEqual(metadata.track_name, u"Track Name")

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Track Name"),
                     M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Another Name")])])])
        self.assertEqual(metadata.track_name, u"Track Name")

        # ensure track_number/_total/album_number/_total fields work
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst',
                           [M4A_ILST_Leaf_Atom(
                               b'trkn',
                               [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                            M4A_ILST_Leaf_Atom(
                                b'disk',
                                [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.album_total, 4)

    @METADATA_M4A
    def test_setattr(self):
        from audiotools.m4a_atoms import M4A_META_Atom
        from audiotools.m4a_atoms import M4A_Tree_Atom
        from audiotools.m4a_atoms import M4A_ILST_Leaf_Atom
        from audiotools.m4a_atoms import M4A_ILST_Unicode_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_TRKN_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_DISK_Data_Atom

        # fields add a new ilst atom, if necessary
        metadata = M4A_META_Atom(0, 0, [])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.track_name, u"Track Name")
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'\xa9nam',
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    b"Track Name")])])]))

        # fields add a new entry to ilst atom, if necessary
        metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.track_name, u"Track Name")
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'\xa9nam',
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    b"Track Name")])])]))

        # fields overwrite first child of ilst atom and leave rest alone
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Old Track Name")])])])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.track_name, u"Track Name")
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'\xa9nam',
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    b"Track Name")])])]))

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Old Track Name")]),
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                b"Old Track Name 2")])])])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.track_name, u"Track Name")
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'\xa9nam',
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    b"Track Name")]),
                    M4A_ILST_Leaf_Atom(
                        b'\xa9nam',
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    b"Old Track Name 2")])])]))

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1, b"Old Track Name"),
                     M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name 2")])])])
        metadata.track_name = u"Track Name"
        self.assertEqual(metadata.track_name, u"Track Name")
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'\xa9nam',
                        [M4A_ILST_Unicode_Data_Atom(
                            0, 1, b"Track Name"),
                         M4A_ILST_Unicode_Data_Atom(
                             0, 1, b"Track Name 2")])])]))

        # setting track_number/_total/album_number/_total
        # adds a new field if necessary
        metadata = M4A_META_Atom(0, 0, [])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(1, 0)])])]))

        metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
        metadata.track_number = 1
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(1, 0)])])]))

        metadata = M4A_META_Atom(0, 0, [])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(0, 2)])])]))

        metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
        metadata.track_total = 2
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(0, 2)])])]))

        metadata = M4A_META_Atom(0, 0, [])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'disk',
                                   [M4A_ILST_DISK_Data_Atom(3, 0)])])]))

        metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
        metadata.album_number = 3
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'disk',
                                   [M4A_ILST_DISK_Data_Atom(3, 0)])])]))

        metadata = M4A_META_Atom(0, 0, [])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'disk',
                                   [M4A_ILST_TRKN_Data_Atom(0, 4)])])]))

        metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
        metadata.album_total = 4
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'disk',
                                   [M4A_ILST_TRKN_Data_Atom(0, 4)])])]))

        # setting track_number/_total/album_number/_total
        # overwrites existing field if necessary
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst',
                           [M4A_ILST_Leaf_Atom(
                               b'trkn',
                               [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                            M4A_ILST_Leaf_Atom(
                                b'disk',
                                [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        metadata.track_number = 6
        self.assertEqual(metadata.track_number, 6)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(6, 2)]),
                                M4A_ILST_Leaf_Atom(
                                    b'disk',
                                    [M4A_ILST_DISK_Data_Atom(3, 4)])])]))

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst',
                           [M4A_ILST_Leaf_Atom(
                               b'trkn',
                               [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                            M4A_ILST_Leaf_Atom(
                                b'disk',
                                [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        metadata.track_total = 7
        self.assertEqual(metadata.track_total, 7)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(1, 7)]),
                                M4A_ILST_Leaf_Atom(
                                    b'disk',
                                    [M4A_ILST_DISK_Data_Atom(3, 4)])])]))

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst',
                           [M4A_ILST_Leaf_Atom(
                               b'trkn',
                               [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                            M4A_ILST_Leaf_Atom(
                                b'disk',
                                [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        metadata.album_number = 8
        self.assertEqual(metadata.album_number, 8)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                                M4A_ILST_Leaf_Atom(
                                    b'disk',
                                    [M4A_ILST_DISK_Data_Atom(8, 4)])])]))

        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst',
                           [M4A_ILST_Leaf_Atom(
                               b'trkn',
                               [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                            M4A_ILST_Leaf_Atom(
                                b'disk',
                                [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        metadata.album_total = 9
        self.assertEqual(metadata.album_total, 9)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst',
                               [M4A_ILST_Leaf_Atom(
                                   b'trkn',
                                   [M4A_ILST_TRKN_Data_Atom(1, 2)]),
                                M4A_ILST_Leaf_Atom(
                                    b'disk',
                                    [M4A_ILST_DISK_Data_Atom(3, 9)])])]))

    @METADATA_M4A
    def test_delattr(self):
        from audiotools.m4a_atoms import M4A_META_Atom
        from audiotools.m4a_atoms import M4A_Tree_Atom
        from audiotools.m4a_atoms import M4A_ILST_Leaf_Atom
        from audiotools.m4a_atoms import M4A_ILST_Unicode_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_TRKN_Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_DISK_Data_Atom

        # fields remove all matching children from ilst atom
        # - no ilst atom
        metadata = M4A_META_Atom(0, 0, [])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata, M4A_META_Atom(0, 0, []))

        # - empty ilst atom
        metadata = M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # - 1 matching item in ilst atom
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name")])])])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # - 2 maching items in ilst atom
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name")]),
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name 2")])])])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # - 2 matching data atoms in ilst child
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name"),
                     M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name 2")])])])
        del(metadata.track_name)
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # setting item to None is the same as deleting it
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'\xa9nam',
                    [M4A_ILST_Unicode_Data_Atom(0, 1, b"Track Name")])])])
        metadata.track_name = None
        self.assertIsNone(metadata.track_name)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # removing track number removes atom if track total is 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'trkn',
                    [M4A_ILST_TRKN_Data_Atom(1, 0)])])])
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # removing track number sets value to None if track total is > 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'trkn',
                    [M4A_ILST_TRKN_Data_Atom(1, 2)])])])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        del(metadata.track_number)
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'trkn',
                        [M4A_ILST_TRKN_Data_Atom(0, 2)])])]))

        # removing track total removes atom if track number is 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'trkn',
                    [M4A_ILST_TRKN_Data_Atom(0, 2)])])])
        self.assertIsNone(metadata.track_number)
        self.assertEqual(metadata.track_total, 2)
        del(metadata.track_total)
        self.assertIsNone(metadata.track_number)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # removing track total sets value to None if track number is > 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'trkn',
                    [M4A_ILST_TRKN_Data_Atom(1, 2)])])])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        del(metadata.track_total)
        self.assertEqual(metadata.track_number, 1)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'trkn',
                        [M4A_ILST_TRKN_Data_Atom(1, 0)])])]))

        # removing album number removes atom if album total is 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'disk',
                    [M4A_ILST_DISK_Data_Atom(3, 0)])])])
        self.assertEqual(metadata.album_number, 3)
        self.assertIsNone(metadata.album_total)
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # removing album number sets value to None if album total is > 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'disk',
                    [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.album_total, 4)
        del(metadata.album_number)
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'disk',
                        [M4A_ILST_DISK_Data_Atom(0, 4)])])]))

        # removing album total removes atom if album number if 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'disk',
                    [M4A_ILST_DISK_Data_Atom(0, 4)])])])
        self.assertIsNone(metadata.album_number)
        self.assertEqual(metadata.album_total, 4)
        del(metadata.album_total)
        self.assertIsNone(metadata.album_number)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata,
                         M4A_META_Atom(0, 0, [M4A_Tree_Atom(b'ilst', [])]))

        # removing album total sets value to None if album number is > 0
        metadata = M4A_META_Atom(
            0, 0,
            [M4A_Tree_Atom(b'ilst', [
                M4A_ILST_Leaf_Atom(
                    b'disk',
                    [M4A_ILST_DISK_Data_Atom(3, 4)])])])
        self.assertEqual(metadata.album_number, 3)
        self.assertEqual(metadata.album_total, 4)
        del(metadata.album_total)
        self.assertEqual(metadata.album_number, 3)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(
            metadata,
            M4A_META_Atom(
                0, 0,
                [M4A_Tree_Atom(b'ilst', [
                    M4A_ILST_Leaf_Atom(
                        b'disk',
                        [M4A_ILST_DISK_Data_Atom(3, 0)])])]))

    @METADATA_M4A
    def test_images(self):
        for audio_class in self.supported_formats:
            with tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX) as temp_file:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                metadata = self.empty_metadata()
                self.assertEqual(metadata.images(), [])

                image1 = audiotools.Image.new(TEST_COVER1, u"", 0)

                track.set_metadata(metadata)
                metadata = track.get_metadata()

                # ensure that adding one image works
                metadata.add_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1])

                # ensure that deleting the first image works
                metadata.delete_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [])

    @METADATA_M4A
    def test_converted(self):
        # build a generic MetaData with everything
        image1 = audiotools.Image.new(TEST_COVER1, u"", 0)

        metadata_orig = audiotools.MetaData(track_name=u"a",
                                            track_number=1,
                                            track_total=2,
                                            album_name=u"b",
                                            artist_name=u"c",
                                            performer_name=u"d",
                                            composer_name=u"e",
                                            conductor_name=u"f",
                                            media=u"g",
                                            ISRC=u"h",
                                            catalog=u"i",
                                            copyright=u"j",
                                            publisher=u"k",
                                            year=u"l",
                                            date=u"m",
                                            album_number=3,
                                            album_total=4,
                                            comment="n",
                                            images=[image1])

        # ensure converted() builds something with our class
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new.__class__, self.metadata_class)

        # ensure our fields match
        for field in audiotools.MetaData.FIELDS:
            if field in self.supported_fields:
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            else:
                self.assertIsNone(getattr(metadata_new, field))

        # ensure images match, if supported
        if self.metadata_class.supports_images():
            self.assertEqual(metadata_new.images(), [image1])

        # check non-MetaData fields
        metadata_orig = self.empty_metadata()
        metadata_orig[b'ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                b'test',
                [audiotools.m4a_atoms.M4A_Leaf_Atom(b"data", b"foobar")]))
        self.assertEqual(
            metadata_orig[b'ilst'][b'test'][b'data'].data, b"foobar")
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(
            metadata_orig[b'ilst'][b'test'][b'data'].data, b"foobar")

        # ensure that convert() builds a whole new object
        metadata_new.track_name = u"Foo"
        self.assertEqual(metadata_new.track_name, u"Foo")
        metadata_new2 = self.metadata_class.converted(metadata_new)
        self.assertEqual(metadata_new2.track_name, u"Foo")
        metadata_new2.track_name = u"Bar"
        self.assertEqual(metadata_new2.track_name, u"Bar")
        self.assertEqual(metadata_new.track_name, u"Foo")

    @METADATA_M4A
    def test_clean(self):
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_EMPTY_TAG)

        # check trailing whitespace
        metadata = audiotools.m4a_atoms.M4A_META_Atom(
            0, 0, [audiotools.m4a_atoms.M4A_Tree_Atom(b'ilst', [])])
        metadata[b'ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                b"\xa9nam",
                [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(0,
                                                                 1,
                                                                 b"Foo ")]))
        self.assertEqual(metadata[b'ilst'][b"\xa9nam"][b'data'].data, b"Foo ")
        self.assertEqual(metadata.track_name, u'Foo ')
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": "nam"}])
        self.assertEqual(cleaned[b'ilst'][b'\xa9nam'][b'data'].data, b"Foo")
        self.assertEqual(cleaned.track_name, u'Foo')

        # check leading whitespace
        metadata = audiotools.m4a_atoms.M4A_META_Atom(
            0, 0, [audiotools.m4a_atoms.M4A_Tree_Atom(b'ilst', [])])
        metadata[b'ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                b"\xa9nam",
                [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(0,
                                                                 1,
                                                                 b" Foo")]))
        self.assertEqual(metadata[b'ilst'][b"\xa9nam"][b'data'].data, b" Foo")
        self.assertEqual(metadata.track_name, u' Foo')
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": "nam"}])
        self.assertEqual(cleaned[b'ilst'][b'\xa9nam'][b'data'].data, b"Foo")
        self.assertEqual(cleaned.track_name, u'Foo')

        # check empty fields
        metadata = audiotools.m4a_atoms.M4A_META_Atom(
            0, 0, [audiotools.m4a_atoms.M4A_Tree_Atom(b'ilst', [])])
        metadata[b'ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                b"\xa9nam",
                [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(0, 1, b"")]))
        self.assertEqual(metadata[b'ilst'][b"\xa9nam"][b'data'].data, b"")
        self.assertEqual(metadata.track_name, u'')
        (cleaned, fixes) = metadata.clean()
        self.assertEqual(fixes,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": "nam"}])
        self.assertRaises(KeyError,
                          cleaned[b'ilst'].__getitem__,
                          b'\xa9nam')
        self.assertIsNone(cleaned.track_name)

        # numerical fields can't have whitespace
        # and images aren't stored with metadata
        # so there's no need to check those

    @METADATA_M4A
    def test_intersection2(self):
        from audiotools.m4a_atoms import M4A_META_Atom as META_Atom
        from audiotools.m4a_atoms import M4A_Tree_Atom as Tree_Atom
        from audiotools.m4a_atoms import M4A_ILST_Leaf_Atom as Leaf_Atom
        from audiotools.m4a_atoms import M4A_ILST_Unicode_Data_Atom as Data_Atom
        from audiotools.m4a_atoms import M4A_ILST_TRKN_Data_Atom as TRKN_Atom

        base = META_Atom(
            0,
            0,
            [Tree_Atom(b'ilst',
                       [Leaf_Atom(b"\xa9nam", [Data_Atom(0, 1, b"Name")]),
                        Leaf_Atom(b"trkn", [TRKN_Atom(2, 3)]),
                        Leaf_Atom(b"fooz", [Data_Atom(0, 1, b"Bar")])])])

        self.assertEqual(base.track_name, u"Name")
        self.assertEqual(base.track_number, 2)
        self.assertEqual(base.track_total, 3)

        # test no matches
        no_matches = META_Atom(
            0,
            0,
            [Tree_Atom(b'ilst',
                       [Leaf_Atom(b"\xa9nam", [Data_Atom(0, 1, b"Name 2")]),
                        Leaf_Atom(b"trkn", [TRKN_Atom(3, 4)]),
                        Leaf_Atom(b"barz", [Data_Atom(0, 1, b"Kelp")])])])
        test = base.intersection(no_matches)
        self.assertIs(type(test), META_Atom)
        self.assertEqual(test, META_Atom(0, 0, []))

        # test some matches
        some_matches = META_Atom(
            0,
            0,
            [Tree_Atom(b'ilst',
                       [Leaf_Atom(b"barz", [Data_Atom(0, 1, "Blah")]),
                        Leaf_Atom(b"trkn", [TRKN_Atom(2, 3)]),
                        Leaf_Atom(b"fooz", [Data_Atom(0, 1, b"Kelp")]),
                        Leaf_Atom(b"fooz", [Data_Atom(0, 1, b"Bar")])])])
        test = base.intersection(some_matches)
        self.assertIs(type(test), META_Atom)
        self.assertEqual(
            test,
            META_Atom(
                0,
                0,
                [Tree_Atom(b'ilst',
                           [Leaf_Atom(b"trkn", [TRKN_Atom(2, 3)]),
                            Leaf_Atom(b"fooz", [Data_Atom(0, 1, b"Bar")])])]))

        # test all matches
        all_matches = META_Atom(
            0,
            0,
            [Tree_Atom(b'ilst',
                       [Leaf_Atom(b"fooz", [Data_Atom(0, 1, b"Bar")]),
                        Leaf_Atom(b"trkn", [TRKN_Atom(2, 3)]),
                        Leaf_Atom(b"\xa9nam", [Data_Atom(0, 1, b"Name")])])])
        test = base.intersection(all_matches)
        self.assertIs(type(test), META_Atom)
        self.assertEqual(
            test,
            META_Atom(
                0,
                0,
               [Tree_Atom(b'ilst',
                          [Leaf_Atom(b"\xa9nam", [Data_Atom(0, 1, b"Name")]),
                           Leaf_Atom(b"trkn", [TRKN_Atom(2, 3)]),
                           Leaf_Atom(b"fooz", [Data_Atom(0, 1, b"Bar")])])]))


class VorbisCommentTest(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.VorbisComment
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "catalog",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.VorbisAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_VORBIS
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # vendor_string not updated with set_metadata()
                # but can be updated with update_metadata()
                old_metadata = track.get_metadata()
                new_metadata = audiotools.VorbisComment(
                    comment_strings=old_metadata.comment_strings[:],
                    vendor_string=u"Vendor String")
                track.set_metadata(new_metadata)
                self.assertEqual(track.get_metadata().vendor_string,
                                 old_metadata.vendor_string)
                track.update_metadata(new_metadata)
                self.assertEqual(track.get_metadata().vendor_string,
                                 new_metadata.vendor_string)

                # REPLAYGAIN_* tags not updated with set_metadata()
                # but can be updated with update_metadata()
                old_metadata = track.get_metadata()
                new_metadata = audiotools.VorbisComment(
                    comment_strings=old_metadata.comment_strings +
                    [u"REPLAYGAIN_REFERENCE_LOUDNESS=89.0 dB"],
                    vendor_string=old_metadata.vendor_string)
                track.set_metadata(new_metadata)
                self.assertRaises(
                    KeyError,
                    track.get_metadata().__getitem__,
                    u"REPLAYGAIN_REFERENCE_LOUDNESS")
                track.update_metadata(new_metadata)
                self.assertEqual(
                    track.get_metadata()[u"REPLAYGAIN_REFERENCE_LOUDNESS"],
                    [u"89.0 dB"])
            finally:
                temp_file.close()

    @METADATA_VORBIS
    def test_foreign_field(self):
        metadata = audiotools.VorbisComment([u"TITLE=Track Name",
                                             u"ALBUM=Album Name",
                                             u"TRACKNUMBER=1",
                                             u"TRACKTOTAL=3",
                                             u"DISCNUMBER=2",
                                             u"DISCTOTAL=4",
                                             u"FOO=Bar"], u"")
        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertEqual(metadata.comment_strings,
                                 metadata2.comment_strings)
                self.assertEqual(metadata.__class__, metadata2.__class__)
                self.assertEqual(metadata2[u"FOO"], [u"Bar"])
            finally:
                temp_file.close()

    @METADATA_VORBIS
    def test_field_mapping(self):
        mapping = [('track_name', u'TITLE', u'a'),
                   ('track_number', u'TRACKNUMBER', 1),
                   ('track_total', u'TRACKTOTAL', 2),
                   ('album_name', u'ALBUM', u'b'),
                   ('artist_name', u'ARTIST', u'c'),
                   ('performer_name', u'PERFORMER', u'd'),
                   ('composer_name', u'COMPOSER', u'e'),
                   ('conductor_name', u'CONDUCTOR', u'f'),
                   ('media', u'SOURCE MEDIUM', u'g'),
                   ('ISRC', u'ISRC', u'h'),
                   ('catalog', u'CATALOG', u'i'),
                   ('copyright', u'COPYRIGHT', u'j'),
                   ('year', u'DATE', u'k'),
                   ('album_number', u'DISCNUMBER', 3),
                   ('album_total', u'DISCTOTAL', 4),
                   ('comment', u'COMMENT', u'l')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                # ensure that setting a class field
                # updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[key][0],
                        u"{}".format(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[key][0],
                        u"{}".format(value))

                # ensure that updating the low-level implementation
                # is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[key] = [u"{}".format(value)]
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[key][0],
                        u"{}".format(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[key][0],
                        u"{}".format(value))
            finally:
                temp_file.close()

    @METADATA_VORBIS
    def test_getitem(self):
        # getitem with no matches raises KeyError
        self.assertRaises(KeyError,
                          audiotools.VorbisComment([u"FOO=kelp"],
                                                   u"vendor").__getitem__,
                          u"BAR")

        # getitem with 1 match returns list of length 1
        self.assertEqual(
            audiotools.VorbisComment([u"FOO=kelp",
                                      u"BAR=spam"], u"vendor")[u"FOO"],
            [u"kelp"])

        # getitem with multiple matches returns multiple items, in order
        self.assertEqual(
            audiotools.VorbisComment([u"FOO=1",
                                      u"BAR=spam",
                                      u"FOO=2",
                                      u"FOO=3"], u"vendor")[u"FOO"],
            [u"1", u"2", u"3"])

        # getitem with aliases returns all matching items, in order
        self.assertEqual(
            audiotools.VorbisComment([u"TRACKTOTAL=1",
                                      u"TOTALTRACKS=2",
                                      u"TRACKTOTAL=3"],
                                     u"vendor")[u"TRACKTOTAL"],
            [u"1", u"2", u"3"])

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKTOTAL=1",
                                      u"TOTALTRACKS=2",
                                      u"TRACKTOTAL=3"],
                                     u"vendor")[u"TOTALTRACKS"],
            [u"1", u"2", u"3"])

        # getitem is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"FOO=kelp"], u"vendor")[u"FOO"],
            [u"kelp"])

        self.assertEqual(
            audiotools.VorbisComment([u"FOO=kelp"], u"vendor")[u"foo"],
            [u"kelp"])

        self.assertEqual(
            audiotools.VorbisComment([u"foo=kelp"], u"vendor")[u"FOO"],
            [u"kelp"])

        self.assertEqual(
            audiotools.VorbisComment([u"foo=kelp"], u"vendor")[u"foo"],
            [u"kelp"])

    @METADATA_VORBIS
    def test_setitem(self):
        # setitem replaces all keys with new values
        metadata = audiotools.VorbisComment([], u"vendor")
        metadata[u"FOO"] = [u"bar"]
        self.assertEqual(metadata[u"FOO"], [u"bar"])

        metadata = audiotools.VorbisComment([u"FOO=1"], u"vendor")
        metadata[u"FOO"] = [u"bar"]
        self.assertEqual(metadata[u"FOO"], [u"bar"])

        metadata = audiotools.VorbisComment([u"FOO=1",
                                             u"FOO=2"], u"vendor")
        metadata[u"FOO"] = [u"bar"]
        self.assertEqual(metadata[u"FOO"], [u"bar"])

        metadata = audiotools.VorbisComment([], u"vendor")
        metadata[u"FOO"] = [u"bar", u"baz"]
        self.assertEqual(metadata[u"FOO"], [u"bar", u"baz"])

        metadata = audiotools.VorbisComment([u"FOO=1"], u"vendor")
        metadata[u"FOO"] = [u"bar", u"baz"]
        self.assertEqual(metadata[u"FOO"], [u"bar", u"baz"])

        metadata = audiotools.VorbisComment([u"FOO=1",
                                             u"FOO=2"], u"vendor")
        metadata[u"FOO"] = [u"bar", u"baz"]
        self.assertEqual(metadata[u"FOO"], [u"bar", u"baz"])

        # setitem leaves other items alone
        metadata = audiotools.VorbisComment([u"BAR=bar"],
                                            u"vendor")
        metadata[u"FOO"] = [u"foo"]
        self.assertEqual(metadata.comment_strings,
                         [u"BAR=bar", u"FOO=foo"])

        metadata = audiotools.VorbisComment([u"FOO=ack",
                                             u"BAR=bar"],
                                            u"vendor")
        metadata[u"FOO"] = [u"foo"]
        self.assertEqual(metadata.comment_strings,
                         [u"FOO=foo", u"BAR=bar"])

        metadata = audiotools.VorbisComment([u"FOO=ack",
                                             u"BAR=bar"],
                                            u"vendor")
        metadata[u"FOO"] = [u"foo", u"fud"]
        self.assertEqual(metadata.comment_strings,
                         [u"FOO=foo", u"BAR=bar", u"FOO=fud"])

        # setitem handles aliases automatically
        metadata = audiotools.VorbisComment([u"TRACKTOTAL=1",
                                             u"TOTALTRACKS=2",
                                             u"TRACKTOTAL=3"],
                                            u"vendor")
        metadata[u"TRACKTOTAL"] = [u"4", u"5", u"6"]
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=4",
                          u"TOTALTRACKS=5",
                          u"TRACKTOTAL=6"])

        metadata = audiotools.VorbisComment([u"TRACKTOTAL=1",
                                             u"TOTALTRACKS=2",
                                             u"TRACKTOTAL=3"],
                                            u"vendor")
        metadata[u"TOTALTRACKS"] = [u"4", u"5", u"6"]
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=4",
                          u"TOTALTRACKS=5",
                          u"TRACKTOTAL=6"])

        # setitem is case-preserving
        metadata = audiotools.VorbisComment([u"FOO=1"], u"vendor")
        metadata[u"FOO"] = [u"bar"]
        self.assertEqual(metadata.comment_strings,
                         [u"FOO=bar"])

        metadata = audiotools.VorbisComment([u"FOO=1"], u"vendor")
        metadata[u"foo"] = [u"bar"]
        self.assertEqual(metadata.comment_strings,
                         [u"FOO=bar"])

        metadata = audiotools.VorbisComment([u"foo=1"], u"vendor")
        metadata[u"FOO"] = [u"bar"]
        self.assertEqual(metadata.comment_strings,
                         [u"foo=bar"])

        metadata = audiotools.VorbisComment([u"foo=1"], u"vendor")
        metadata[u"foo"] = [u"bar"]
        self.assertEqual(metadata.comment_strings,
                         [u"foo=bar"])

    @METADATA_VORBIS
    def test_getattr(self):
        # track_number grabs the first available integer
        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=10"],
                                     u"vendor").track_number,
            10)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=10",
                                      u"TRACKNUMBER=5"],
                                     u"vendor").track_number,
            10)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=foo 10 bar"],
                                     u"vendor").track_number,
            10)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=foo",
                                      u"TRACKNUMBER=10"],
                                     u"vendor").track_number,
            10)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=foo",
                                      u"TRACKNUMBER=foo 10 bar"],
                                     u"vendor").track_number,
            10)

        # track_number is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"tRaCkNuMbEr=10"],
                                     u"vendor").track_number,
            10)

        # album_number grabs the first available integer
        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=20"],
                                     u"vendor").album_number,
            20)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=20",
                                      u"DISCNUMBER=5"],
                                     u"vendor").album_number,
            20)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=foo 20 bar"],
                                     u"vendor").album_number,
            20)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=foo",
                                      u"DISCNUMBER=20"],
                                     u"vendor").album_number,
            20)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=foo",
                                      u"DISCNUMBER=foo 20 bar"],
                                     u"vendor").album_number,
            20)

        # album_number is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"dIsCnUmBeR=20"],
                                     u"vendor").album_number,
            20)

        # track_total grabs the first available TRACKTOTAL integer
        # before falling back on slashed fields
        self.assertEqual(
            audiotools.VorbisComment([u"TRACKTOTAL=15"],
                                     u"vendor").track_total,
            15)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=5/10"],
                                     u"vendor").track_total,
            10)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKTOTAL=foo/10"],
                                     u"vendor").track_total,
            10)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=5/10",
                                      u"TRACKTOTAL=15"],
                                     u"vendor").track_total,
            15)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKTOTAL=15",
                                      u"TRACKNUMBER=5/10"],
                                     u"vendor").track_total,
            15)

        # track_total is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"tracktotal=15"],
                                     u"vendor").track_total,
            15)

        # track_total supports aliases
        self.assertEqual(
            audiotools.VorbisComment([u"TOTALTRACKS=15"],
                                     u"vendor").track_total,
            15)

        # album_total grabs the first available DISCTOTAL integer
        # before falling back on slashed fields
        self.assertEqual(
            audiotools.VorbisComment([u"DISCTOTAL=25"],
                                     u"vendor").album_total,
            25)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=10/30"],
                                     u"vendor").album_total,
            30)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=foo/30"],
                                     u"vendor").album_total,
            30)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=10/30",
                                      u"DISCTOTAL=25"],
                                     u"vendor").album_total,
            25)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCTOTAL=25",
                                      u"DISCNUMBER=10/30"],
                                     u"vendor").album_total,
            25)

        # album_total is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"disctotal=25"],
                                     u"vendor").album_total,
            25)

        # album_total supports aliases
        self.assertEqual(
            audiotools.VorbisComment([u"TOTALDISCS=25"],
                                     u"vendor").album_total,
            25)

        # other fields grab the first available item
        self.assertEqual(
            audiotools.VorbisComment([u"TITLE=first",
                                      u"TITLE=last"],
                                     u"vendor").track_name,
            u"first")

    @METADATA_VORBIS
    def test_setattr(self):
        # track_number adds new field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertIsNone(metadata.track_number)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=11"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=blah"],
                                            u"vendor")
        self.assertIsNone(metadata.track_number)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=blah",
                          u"TRACKNUMBER=11"])
        self.assertEqual(metadata.track_number, 11)

        # track_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=10/12"], u"vendor")
        self.assertEqual(metadata.track_number, 10)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=11/12"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=foo 10 bar"],
                                            u"vendor")
        self.assertEqual(metadata.track_number, 10)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=foo 11 bar"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=foo 10 bar",
                                             u"TRACKNUMBER=blah"],
                                            u"vendor")
        self.assertEqual(metadata.track_number, 10)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=foo 11 bar",
                          u"TRACKNUMBER=blah"])
        self.assertEqual(metadata.track_number, 11)

        # album_number adds new field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertIsNone(metadata.album_number)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=3"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.VorbisComment([u"DISCNUMBER=blah"],
                                            u"vendor")
        self.assertIsNone(metadata.album_number)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=blah",
                          u"DISCNUMBER=3"])
        self.assertEqual(metadata.album_number, 3)

        # album_number updates the first integer field
        # and leaves other junk in that field alone
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/4"], u"vendor")
        self.assertEqual(metadata.album_number, 2)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=3/4"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.VorbisComment([u"DISCNUMBER=foo 2 bar"],
                                            u"vendor")
        self.assertEqual(metadata.album_number, 2)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=foo 3 bar"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.VorbisComment([u"DISCNUMBER=foo 2 bar",
                                             u"DISCNUMBER=blah"],
                                            u"vendor")
        self.assertEqual(metadata.album_number, 2)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=foo 3 bar",
                          u"DISCNUMBER=blah"])
        self.assertEqual(metadata.album_number, 3)

        # track_total adds new TRACKTOTAL field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertIsNone(metadata.track_total)
        metadata.track_total = 12
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=12"])
        self.assertEqual(metadata.track_total, 12)

        metadata = audiotools.VorbisComment([u"TRACKTOTAL=blah"],
                                            u"vendor")
        self.assertIsNone(metadata.track_total)
        metadata.track_total = 12
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=blah",
                          u"TRACKTOTAL=12"])
        self.assertEqual(metadata.track_total, 12)

        # track_total updates first integer TRACKTOTAL field first if possible
        # including aliases
        metadata = audiotools.VorbisComment([u"TRACKTOTAL=blah",
                                             u"TRACKTOTAL=2"], u"vendor")
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=blah",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.VorbisComment([u"TOTALTRACKS=blah",
                                             u"TOTALTRACKS=2"], u"vendor")
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.comment_strings,
                         [u"TOTALTRACKS=blah",
                          u"TOTALTRACKS=3"])
        self.assertEqual(metadata.track_total, 3)

        # track_total updates slashed TRACKNUMBER field if necessary
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/4",
                                             u"TRACKTOTAL=2"], u"vendor")
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=1/4",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/4"], u"vendor")
        self.assertEqual(metadata.track_total, 4)
        metadata.track_total = 3
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=1/3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER= foo / 4 bar"],
                                            u"vendor")
        self.assertEqual(metadata.track_total, 4)
        metadata.track_total = 3
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER= foo / 3 bar"])
        self.assertEqual(metadata.track_total, 3)

        # album_total adds new DISCTOTAL field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertIsNone(metadata.album_total)
        metadata.album_total = 4
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        metadata = audiotools.VorbisComment([u"DISCTOTAL=blah"],
                                            u"vendor")
        self.assertIsNone(metadata.album_total)
        metadata.album_total = 4
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=blah",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        # album_total updates DISCTOTAL field first if possible
        # including aliases
        metadata = audiotools.VorbisComment([u"DISCTOTAL=blah",
                                             u"DISCTOTAL=3"], u"vendor")
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 4
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=blah",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        metadata = audiotools.VorbisComment([u"TOTALDISCS=blah",
                                             u"TOTALDISCS=3"], u"vendor")
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 4
        self.assertEqual(metadata.comment_strings,
                         [u"TOTALDISCS=blah",
                          u"TOTALDISCS=4"])
        self.assertEqual(metadata.album_total, 4)

        # album_total updates slashed DISCNUMBER field if necessary
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/3",
                                             u"DISCTOTAL=5"], u"vendor")
        self.assertEqual(metadata.album_total, 5)
        metadata.album_total = 6
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=2/3",
                          u"DISCTOTAL=6"])
        self.assertEqual(metadata.album_total, 6)

        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/3"], u"vendor")
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 6
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=2/6"])
        self.assertEqual(metadata.album_total, 6)

        metadata = audiotools.VorbisComment([u"DISCNUMBER= foo / 3 bar"],
                                            u"vendor")
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 6
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER= foo / 6 bar"])
        self.assertEqual(metadata.album_total, 6)

        # other fields update the first match
        # while leaving the rest alone
        metadata = audiotools.VorbisComment([u"TITLE=foo",
                                             u"TITLE=bar",
                                             u"FOO=baz"],
                                            u"vendor")
        metadata.track_name = u"blah"
        self.assertEqual(metadata.track_name, u"blah")
        self.assertEqual(metadata.comment_strings,
                         [u"TITLE=blah",
                          u"TITLE=bar",
                          u"FOO=baz"])

        # setting field to an empty string is okay
        metadata = audiotools.VorbisComment([], u"vendor")
        metadata.track_name = u""
        self.assertEqual(metadata.track_name, u"")
        self.assertEqual(metadata.comment_strings,
                         [u"TITLE="])

    @METADATA_VORBIS
    def test_delattr(self):
        # deleting nonexistent field is okay
        for field in audiotools.MetaData.FIELDS:
            metadata = audiotools.VorbisComment([],
                                                u"vendor")
            delattr(metadata, field)
            self.assertIsNone(getattr(metadata, field))

        # deleting field removes all instances of it
        metadata = audiotools.VorbisComment([],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.VorbisComment([u"TITLE=track name"],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.VorbisComment([u"TITLE=track name",
                                             u"ALBUM=album name"],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [u"ALBUM=album name"])
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.VorbisComment([u"TITLE=track name",
                                             u"TITLE=track name 2",
                                             u"ALBUM=album name",
                                             u"TITLE=track name 3"],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [u"ALBUM=album name"])
        self.assertIsNone(metadata.track_name)

        # setting field to None is the same as deleting field
        metadata = audiotools.VorbisComment([u"TITLE=track name"],
                                            u"vendor")
        metadata.track_name = None
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        metadata = audiotools.VorbisComment([u"TITLE=track name"],
                                            u"vendor")
        metadata.track_name = None
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.track_name)

        # deleting track_number removes TRACKNUMBER field
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1"],
                                            u"vendor")
        del(metadata.track_number)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.track_number)

        # deleting slashed TRACKNUMBER converts it to fresh TRACKTOTAL field
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/3"],
                                            u"vendor")
        del(metadata.track_number)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=3"])
        self.assertIsNone(metadata.track_number)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/3",
                                             u"TRACKTOTAL=4"],
                                            u"vendor")
        self.assertEqual(metadata.track_total, 4)
        del(metadata.track_number)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=4"])
        self.assertEqual(metadata.track_total, 4)
        self.assertIsNone(metadata.track_number)

        # deleting track_total removes TRACKTOTAL/TOTALTRACKS fields
        metadata = audiotools.VorbisComment([u"TRACKTOTAL=3",
                                             u"TOTALTRACKS=4"],
                                            u"vendor")
        del(metadata.track_total)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.track_total)

        # deleting track_total also removes slashed side of TRACKNUMBER fields
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/3"],
                                            u"vendor")
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1 / foo 3 baz"],
                                            u"vendor")
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.VorbisComment(
            [u"TRACKNUMBER= foo 1 bar / blah 4 baz"], u"vendor")
        del(metadata.track_total)
        self.assertIsNone(metadata.track_total)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER= foo 1 bar"])

        # deleting album_number removes DISCNUMBER field
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2"],
                                            u"vendor")
        del(metadata.album_number)
        self.assertEqual(metadata.comment_strings,
                         [])

        # deleting slashed DISCNUMBER converts it to fresh DISCTOTAL field
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/4"],
                                            u"vendor")
        del(metadata.album_number)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=4"])

        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/4",
                                             u"DISCTOTAL=5"],
                                            u"vendor")
        self.assertEqual(metadata.album_total, 5)
        del(metadata.album_number)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=5"])
        self.assertEqual(metadata.album_total, 5)

        # deleting album_total removes DISCTOTAL/TOTALDISCS fields
        metadata = audiotools.VorbisComment([u"DISCTOTAL=4",
                                             u"TOTALDISCS=5"],
                                            u"vendor")
        del(metadata.album_total)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertIsNone(metadata.album_total)

        # deleting album_total also removes slashed side of DISCNUMBER fields
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/4"],
                                            u"vendor")
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.VorbisComment([u"DISCNUMBER=2 / foo 4 baz"],
                                            u"vendor")
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.VorbisComment(
            [u"DISCNUMBER= foo 2 bar / blah 4 baz"], u"vendor")
        del(metadata.album_total)
        self.assertIsNone(metadata.album_total)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER= foo 2 bar"])

    @METADATA_VORBIS
    def test_supports_images(self):
        self.assertEqual(self.metadata_class.supports_images(), False)

    @METADATA_VORBIS
    def test_lowercase(self):
        for audio_format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_format.SUFFIX)
            try:
                track = audio_format.from_pcm(temp_file.name,
                                              BLANK_PCM_Reader(1))

                lc_metadata = audiotools.VorbisComment(
                    [u"title=track name",
                     u"tracknumber=1",
                     u"tracktotal=3",
                     u"album=album name",
                     u"artist=artist name",
                     u"performer=performer name",
                     u"composer=composer name",
                     u"conductor=conductor name",
                     u"source medium=media",
                     u"isrc=isrc",
                     u"catalog=catalog",
                     u"copyright=copyright",
                     u"publisher=publisher",
                     u"date=2009",
                     u"discnumber=2",
                     u"disctotal=4",
                     u"comment=some comment"],
                    u"vendor string")

                metadata = audiotools.MetaData(
                    track_name=u"track name",
                    track_number=1,
                    track_total=3,
                    album_name=u"album name",
                    artist_name=u"artist name",
                    performer_name=u"performer name",
                    composer_name=u"composer name",
                    conductor_name=u"conductor name",
                    media=u"media",
                    ISRC=u"isrc",
                    catalog=u"catalog",
                    copyright=u"copyright",
                    publisher=u"publisher",
                    year=u"2009",
                    album_number=2,
                    album_total=4,
                    comment=u"some comment")

                track.set_metadata(lc_metadata)
                track = audiotools.open(track.filename)
                self.assertEqual(metadata, lc_metadata)

                track = audio_format.from_pcm(temp_file.name,
                                              BLANK_PCM_Reader(1))
                track.set_metadata(audiotools.MetaData(
                    track_name=u"Track Name",
                    track_number=1))
                metadata = track.get_metadata()
                self.assertEqual(metadata[u"TITLE"], [u"Track Name"])
                self.assertEqual(metadata[u"TRACKNUMBER"], [u"1"])
                self.assertEqual(metadata.track_name, u"Track Name")
                self.assertEqual(metadata.track_number, 1)

                metadata[u"title"] = [u"New Track Name"]
                metadata[u"tracknumber"] = [u"2"]
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[u"TITLE"], [u"New Track Name"])
                self.assertEqual(metadata[u"TRACKNUMBER"], [u"2"])
                self.assertEqual(metadata.track_name, u"New Track Name")
                self.assertEqual(metadata.track_number, 2)

                metadata.track_name = u"New Track Name 2"
                metadata.track_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata[u"TITLE"], [u"New Track Name 2"])
                self.assertEqual(metadata[u"TRACKNUMBER"], [u"3"])
                self.assertEqual(metadata.track_name, u"New Track Name 2")
                self.assertEqual(metadata.track_number, 3)
            finally:
                temp_file.close()

    @METADATA_VORBIS
    def test_totals(self):
        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"2/4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"02/4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"2/04"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"02/04"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"foo 2 bar /4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"2/ foo 4 bar"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"TRACKNUMBER"] = [u"foo 2 bar / kelp 4 spam"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"1/3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"01/3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"1/03"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"01/03"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"foo 1 bar /3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"1/ foo 3 bar"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

        metadata = self.empty_metadata()
        metadata[u"DISCNUMBER"] = [u"foo 1 bar / kelp 3 spam"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

    @METADATA_VORBIS
    def test_clean(self):
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_ZEROES,
                                     CLEAN_REMOVE_LEADING_WHITESPACE_ZEROES,
                                     CLEAN_REMOVE_EMPTY_TAG)

        # check trailing whitespace
        metadata = audiotools.VorbisComment([u"TITLE=Foo "], u"vendor")
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([u"TITLE=Foo"], u"vendor"))
        self.assertEqual(results,
                         [CLEAN_REMOVE_TRAILING_WHITESPACE %
                          {"field": u"TITLE"}])

        # check leading whitespace
        metadata = audiotools.VorbisComment([u"TITLE= Foo"], u"vendor")
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([u"TITLE=Foo"], u"vendor"))
        self.assertEqual(results,
                         [CLEAN_REMOVE_LEADING_WHITESPACE %
                          {"field": u"TITLE"}])

        # check leading zeroes
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=001"], u"vendor")
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([u"TRACKNUMBER=1"],
                                                  u"vendor"))
        self.assertEqual(results,
                         [CLEAN_REMOVE_LEADING_ZEROES %
                          {"field": u"TRACKNUMBER"}])

        # check leading space/zeroes in slashed field
        for field in [u"TRACKNUMBER=01/2",
                      u"TRACKNUMBER=1/02",
                      u"TRACKNUMBER=01/02",
                      u"TRACKNUMBER=1/ 2",
                      u"TRACKNUMBER=1/ 02"]:
            metadata = audiotools.VorbisComment([field], u"vendor")
            (cleaned, results) = metadata.clean()
            self.assertEqual(cleaned,
                             audiotools.VorbisComment([u"TRACKNUMBER=1/2"],
                                                      u"vendor"))
            self.assertEqual(results,
                             [CLEAN_REMOVE_LEADING_WHITESPACE_ZEROES %
                              {"field": u"TRACKNUMBER"}])

        # check empty fields
        metadata = audiotools.VorbisComment([u"TITLE="], u"vendor")
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([], u"vendor"))
        self.assertEqual(results,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": u"TITLE"}])

        metadata = audiotools.VorbisComment([u"TITLE=    "], u"vendor")
        (cleaned, results) = metadata.clean()
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([], u"vendor"))
        self.assertEqual(results,
                         [CLEAN_REMOVE_EMPTY_TAG %
                          {"field": u"TITLE"}])

    @METADATA_VORBIS
    def test_aliases(self):
        for (key, map_to) in audiotools.VorbisComment.ALIASES.items():
            attr = [attr for (attr, item) in
                    audiotools.VorbisComment.ATTRIBUTE_MAP.items()
                    if item in map_to][0]

            if audiotools.VorbisComment.FIELD_TYPES[attr] is int:
                old_raw_value = u"1"
                old_attr_value = 1
                new_raw_value = u"2"
                new_attr_value = 2
            else:
                old_raw_value = old_attr_value = u"Foo"
                new_raw_value = new_attr_value = u"Bar"

            metadata = audiotools.VorbisComment([], u"")

            # ensure setting aliased field shows up in attribute
            metadata[key] = [old_raw_value]
            self.assertEqual(getattr(metadata, attr), old_attr_value)

            # ensure updating attribute reflects in aliased field
            setattr(metadata, attr, new_attr_value)
            self.assertEqual(getattr(metadata, attr), new_attr_value)
            self.assertEqual(metadata[key], [new_raw_value])

            self.assertEqual(metadata.keys(), [key])

            # ensure updating the metadata with an aliased key
            # doesn't change the aliased key field
            for new_key in map_to:
                if new_key != key:
                    metadata[new_key] = [old_raw_value]
                    self.assertEqual(metadata.keys(), [key])

    @METADATA_VORBIS
    def test_replay_gain(self):
        import test_streams

        for input_class in [audiotools.FlacAudio,
                            audiotools.VorbisAudio]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + input_class.SUFFIX)
            try:
                track1 = input_class.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assertIsNone(
                    track1.get_replay_gain(),
                    "ReplayGain present for class {}".format(
                        input_class.NAME))
                track1.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                audiotools.add_replay_gain([track1])
                self.assertEqual(track1.get_metadata().track_name, u"Foo")
                self.assertIsNotNone(
                    track1.get_replay_gain(),
                    "ReplayGain not present for class {}".format(
                        input_class.NAME))

                for output_class in [audiotools.VorbisAudio]:
                    temp2 = tempfile.NamedTemporaryFile(
                        suffix="." + input_class.SUFFIX)
                    try:
                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))

                        # ensure that ReplayGain doesn't get ported
                        # via set_metadata()
                        self.assertIsNone(
                            track2.get_replay_gain(),
                            "ReplayGain present for class {}".format(
                                output_class.NAME))
                        track2.set_metadata(track1.get_metadata())
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Foo")
                        self.assertIsNone(
                            track2.get_replay_gain(),
                            "ReplayGain present for class {} from {}".format(
                                output_class.NAME, input_class.NAME))

                        # and if ReplayGain is already set,
                        # ensure set_metadata() doesn't remove it
                        audiotools.add_replay_gain([track2])
                        old_replay_gain = track2.get_replay_gain()
                        self.assertIsNotNone(old_replay_gain)
                        track2.set_metadata(audiotools.MetaData(
                            track_name=u"Bar"))
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Bar")
                        self.assertEqual(track2.get_replay_gain(),
                                         old_replay_gain)
                    finally:
                        temp2.close()
            finally:
                temp1.close()

    @METADATA_VORBIS
    def test_intersection2(self):
        from audiotools.vorbiscomment import VorbisComment

        base = VorbisComment([u"TITLE=Title",
                              u"PERFORMER=Performer",
                              u"FOO=Bar"],
                             u"vendor 1")
        self.assertEqual(base.track_name, u"Title")
        self.assertEqual(base.performer_name, u"Performer")

        # test no matches
        no_matches = VorbisComment([u"TITLE=Bar",
                                    u"FOO=Baz",
                                    u"KELP=Spam"],
                                   u"vendor 2")
        test = base.intersection(no_matches)
        self.assertIs(type(test), VorbisComment)
        self.assertEqual(test.comment_strings, [])
        self.assertEqual(test.vendor_string, u"vendor 1")

        # test some matches
        some_matches = VorbisComment([u"TITLE=Bar",
                                      u"ALBUM ARTIST=Performer",
                                      u"FOO=Baz",
                                      u"KELP=Spam"],
                                     u"vendor 2")
        test = base.intersection(some_matches)
        self.assertIs(type(test), VorbisComment)
        self.assertEqual(test.performer_name, u"Performer")
        self.assertEqual(test.comment_strings, [u"PERFORMER=Performer"])
        self.assertEqual(test.vendor_string, u"vendor 1")

        some_matches = VorbisComment([u"TITLE=Bar",
                                      u"FOO=Baz",
                                      u"FOO=Bar",
                                      u"KELP=Spam"],
                                     u"vendor 2")
        test = base.intersection(some_matches)
        self.assertIs(type(test), VorbisComment)
        self.assertEqual(test.comment_strings, [u"FOO=Bar"])
        self.assertEqual(test.vendor_string, u"vendor 1")

        # test all matches
        all_matches = VorbisComment([u"FOO=Bar",
                                     u"ALBUM ARTIST=Performer",
                                     u"TITLE=Title"],
                                    u"vendor 2")
        test = base.intersection(all_matches)
        self.assertIs(type(test), VorbisComment)
        self.assertEqual(test.track_name, u"Title")
        self.assertEqual(test.performer_name, u"Performer")
        self.assertEqual(test.comment_strings, [u"TITLE=Title",
                                                u"PERFORMER=Performer",
                                                u"FOO=Bar"])
        self.assertEqual(test.vendor_string, u"vendor 1")


class OpusTagsTest(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.VorbisComment
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "performer_name",
                                 "composer_name",
                                 "conductor_name",
                                 "media",
                                 "ISRC",
                                 "catalog",
                                 "copyright",
                                 "publisher",
                                 "year",
                                 "album_number",
                                 "album_total",
                                 "comment",
                                 "compilation"]
        self.supported_formats = [audiotools.OpusAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_OPUS
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                # vendor_string not updated with set_metadata()
                # but can be updated with update_metadata()
                old_metadata = track.get_metadata()
                new_metadata = audiotools.VorbisComment(
                    comment_strings=old_metadata.comment_strings[:],
                    vendor_string=u"Vendor String")
                track.set_metadata(new_metadata)
                self.assertEqual(track.get_metadata().vendor_string,
                                 old_metadata.vendor_string)
                track.update_metadata(new_metadata)
                self.assertEqual(track.get_metadata().vendor_string,
                                 new_metadata.vendor_string)

                # REPLAYGAIN_* tags not updated with set_metadata()
                # but can be updated with update_metadata()
                old_metadata = track.get_metadata()
                new_metadata = audiotools.VorbisComment(
                    comment_strings=old_metadata.comment_strings +
                    [u"REPLAYGAIN_REFERENCE_LOUDNESS=89.0 dB"],
                    vendor_string=old_metadata.vendor_string)
                track.set_metadata(new_metadata)
                self.assertRaises(
                    KeyError,
                    track.get_metadata().__getitem__,
                    u"REPLAYGAIN_REFERENCE_LOUDNESS")
                track.update_metadata(new_metadata)
                self.assertEqual(
                    track.get_metadata()[u"REPLAYGAIN_REFERENCE_LOUDNESS"],
                    [u"89.0 dB"])
            finally:
                temp_file.close()

    @METADATA_OPUS
    def test_foreign_field(self):
        metadata = audiotools.VorbisComment([u"TITLE=Track Name",
                                             u"ALBUM=Album Name",
                                             u"TRACKNUMBER=1",
                                             u"TRACKTOTAL=3",
                                             u"DISCNUMBER=2",
                                             u"DISCTOTAL=4",
                                             u"FOO=Bar"], u"")
        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name,
                                        BLANK_PCM_Reader(1))
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assertTrue(
                    set(metadata.comment_strings).issubset(
                        set(metadata2.comment_strings)))
                self.assertEqual(metadata.__class__, metadata2.__class__)
                self.assertEqual(metadata2[u"FOO"], [u"Bar"])
            finally:
                temp_file.close()

    @METADATA_OPUS
    def test_field_mapping(self):
        mapping = [('track_name', u'TITLE', u'a'),
                   ('track_number', u'TRACKNUMBER', 1),
                   ('track_total', u'TRACKTOTAL', 2),
                   ('album_name', u'ALBUM', u'b'),
                   ('artist_name', u'ARTIST', u'c'),
                   ('performer_name', u'PERFORMER', u'd'),
                   ('composer_name', u'COMPOSER', u'e'),
                   ('conductor_name', u'CONDUCTOR', u'f'),
                   ('media', u'SOURCE MEDIUM', u'g'),
                   ('ISRC', u'ISRC', u'h'),
                   ('catalog', u'CATALOG', u'i'),
                   ('copyright', u'COPYRIGHT', u'j'),
                   ('year', u'DATE', u'k'),
                   ('album_number', u'DISCNUMBER', 3),
                   ('album_total', u'DISCTOTAL', 4),
                   ('comment', u'COMMENT', u'l')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                # ensure that setting a class field
                # updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[key][0],
                        u"{}".format(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[key][0],
                        u"{}".format(value))

                # ensure that updating the low-level implementation
                # is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[key] = [u"{}".format(value)]
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[key][0],
                        u"{}".format(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[key][0],
                        u"{}".format(value))
            finally:
                temp_file.close()

    @METADATA_OPUS
    def test_supports_images(self):
        self.assertEqual(self.metadata_class.supports_images(), False)


class TrueAudioTest(unittest.TestCase):
    # True Audio supports APEv2, ID3v2 and ID3v1
    # which makes the format much more complicated
    # than if it supported only a single format.

    def __base_metadatas__(self):
        base_metadata = audiotools.MetaData(
            track_name=u"Track Name",
            album_name=u"Album Name",
            artist_name=u"Artist Name",
            track_number=1)

        yield audiotools.ApeTag.converted(base_metadata)

    @METADATA_TTA
    def test_update(self):
        import os

        for base_metadata in self.__base_metadatas__():
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audiotools.TrueAudio.SUFFIX)
            track = audiotools.TrueAudio.from_pcm(temp_file.name,
                                                  BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                # update_metadata on file's internal metadata round-trips okay
                track.update_metadata(base_metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Track Name")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertIs(metadata.__class__, base_metadata.__class__)
                self.assertEqual(metadata.track_name, u"Bar")

                # update_metadata on unwritable file generates IOError
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  base_metadata)
                os.chmod(temp_file.name, temp_file_stat)

                # update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                # # update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                if isinstance(base_metadata, audiotools.ApeTag):
                    # replaygain strings not updated with set_metadata()
                    # but can be updated with update_metadata()
                    self.assertRaises(KeyError,
                                      track.get_metadata().__getitem__,
                                      b"replaygain_track_gain")
                    metadata[b"replaygain_track_gain"] = \
                        audiotools.ape.ApeTagItem.string(
                            b"replaygain_track_gain", u"???")
                    track.set_metadata(metadata)
                    self.assertRaises(KeyError,
                                      track.get_metadata().__getitem__,
                                      b"replaygain_track_gain")
                    track.update_metadata(metadata)
                    self.assertEqual(
                        track.get_metadata()[b"replaygain_track_gain"],
                        audiotools.ape.ApeTagItem.string(
                            b"replaygain_track_gain", u"???"))

                    # cuesheet not updated with set_metadata()
                    # but can be updated with update_metadata()
                    metadata[b"Cuesheet"] = \
                        audiotools.ape.ApeTagItem.string(
                            b"Cuesheet", u"???")
                    track.set_metadata(metadata)
                    self.assertRaises(KeyError,
                                      track.get_metadata().__getitem__,
                                      b"Cuesheet")
                    track.update_metadata(metadata)
                    self.assertEqual(
                        track.get_metadata()[b"Cuesheet"],
                        audiotools.ape.ApeTagItem.string(b"Cuesheet", u"???"))
            finally:
                temp_file.close()

    @METADATA_TTA
    def test_delete(self):
        # delete metadata clears out ID3v?, ID3v1, ApeTag and ID3CommentPairs

        for metadata in self.__base_metadatas__():
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audiotools.TrueAudio.SUFFIX)
            try:
                track = audiotools.TrueAudio.from_pcm(temp_file.name,
                                                      BLANK_PCM_Reader(1))

                self.assertIsNone(track.get_metadata())
                track.update_metadata(metadata)
                self.assertIsNotNone(track.get_metadata())
                track.delete_metadata()
                self.assertIsNone(track.get_metadata())
            finally:
                temp_file.close()

    @METADATA_TTA
    def test_images(self):
        # images work like either WavPack or MP3
        # depending on which metadata is in place

        for metadata in self.__base_metadatas__():
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audiotools.TrueAudio.SUFFIX)
            try:
                track = audiotools.TrueAudio.from_pcm(temp_file.name,
                                                      BLANK_PCM_Reader(1))

                self.assertEqual(metadata.images(), [])

                image1 = audiotools.Image.new(TEST_COVER1,
                                              u"Text 1", 0)
                image2 = audiotools.Image.new(TEST_COVER2,
                                              u"Text 2", 1)

                track.set_metadata(metadata)
                metadata = track.get_metadata()

                # ensure that adding one image works
                metadata.add_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1])

                # ensure that adding a second image works
                metadata.add_image(image2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1,
                                                     image2])

                # ensure that deleting the first image works
                metadata.delete_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image2])

                metadata.delete_image(image2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [])

            finally:
                temp_file.close()

    @METADATA_TTA
    def test_replay_gain(self):
        # adding ReplayGain converts internal MetaData to APEv2
        # but otherwise works like WavPack

        import test_streams
        for metadata in self.__base_metadatas__():
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + audiotools.TrueAudio.SUFFIX)
            try:
                track1 = audiotools.TrueAudio.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assertIsNone(
                    track1.get_replay_gain(),
                    "ReplayGain present for class {}".format(
                        audiotools.TrueAudio.NAME))
                track1.update_metadata(metadata)
                audiotools.add_replay_gain([track1])
                self.assertIsInstance(track1.get_metadata(), audiotools.ApeTag)
                self.assertEqual(track1.get_metadata().track_name,
                                 u"Track Name")
                self.assertIsNotNone(
                    track1.get_replay_gain(),
                    "ReplayGain not present for class {}".format(
                        audiotools.TrueAudio.NAME))

                temp2 = tempfile.NamedTemporaryFile(
                    suffix="." + audiotools.TrueAudio.SUFFIX)
                try:
                    track2 = audiotools.TrueAudio.from_pcm(
                        temp2.name,
                        test_streams.Sine16_Stereo(66150, 44100,
                                                   8820.0, 0.70,
                                                   4410.0, 0.29, 1.0))

                    # ensure that ReplayGain doesn't get ported
                    # via set_metadata()
                    self.assertIsNone(
                        track2.get_replay_gain(),
                        "ReplayGain present for class {}".format(
                            audiotools.TrueAudio.NAME))
                    track2.set_metadata(track1.get_metadata())
                    self.assertEqual(track2.get_metadata().track_name,
                                     u"Track Name")
                    self.assertIsNone(
                        track2.get_replay_gain(),
                        "ReplayGain present for class {} from {}".format(
                            audiotools.TrueAudio.NAME,
                            audiotools.TrueAudio.NAME))

                    # and if ReplayGain is already set,
                    # ensure set_metadata() doesn't remove it
                    audiotools.add_replay_gain([track2])
                    old_replay_gain = track2.get_replay_gain()
                    self.assertIsNotNone(old_replay_gain)
                    track2.set_metadata(
                        audiotools.MetaData(track_name=u"Bar"))
                    self.assertEqual(track2.get_metadata().track_name,
                                     u"Bar")
                    self.assertEqual(track2.get_replay_gain(),
                                     old_replay_gain)

                finally:
                    temp2.close()
            finally:
                temp1.close()
