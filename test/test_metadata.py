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

from test import (parser, BLANK_PCM_Reader, Combinations,
                  TEST_COVER1, TEST_COVER2, TEST_COVER3, TEST_COVER4,
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
                                 "comment"]
        self.supported_formats = []

    def empty_metadata(self):
        return self.metadata_class()

    @METADATA_METADATA
    def test_roundtrip(self):
        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))
                metadata = self.empty_metadata()
                setattr(metadata, self.supported_fields[0], u"Foo")
                track.set_metadata(metadata)
                metadata2 = track.get_metadata()
                self.assert_(isinstance(metadata2, self.metadata_class))

                #also ensure that the new track is playable
                audiotools.transfer_framelist_data(track.to_pcm(), lambda f: f)
            finally:
                temp_file.close()

    @METADATA_METADATA
    def test_attribs(self):
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

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                #check that setting the fields to random values works
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in xrange(random.choice(range(1, 21)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    else:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)

                #check that blanking out the fields works
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
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
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in xrange(random.choice(range(1, 21)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    else:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)

                    #check that deleting the fields works
                    delattr(metadata, field)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
                        self.assertEqual(getattr(metadata, field), u"")
                    else:
                        self.assertEqual(getattr(metadata, field), 0)

            finally:
                temp_file.close()

    @METADATA_METADATA
    def test_field_mapping(self):
        #ensure that setting a class field
        #updates its corresponding low-level implementation

        #ensure that updating the low-level implementation
        #is reflected in the class field

        pass

    @METADATA_METADATA
    def test_foreign_field(self):
        pass

    @METADATA_METADATA
    def test_converted(self):
        #build a generic MetaData with everything
        image1 = audiotools.Image.new(TEST_COVER1, "Text 1", 0)
        image2 = audiotools.Image.new(TEST_COVER2, "Text 2", 1)
        image3 = audiotools.Image.new(TEST_COVER3, "Text 3", 2)

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
                                            images=[image1, image2, image3])

        #ensure converted() builds something with our class
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new.__class__, self.metadata_class)

        #ensure our fields match
        for field in audiotools.MetaData.FIELDS:
            if (field in self.supported_fields):
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            elif (field in audiotools.MetaData.INTEGER_FIELDS):
                self.assertEqual(getattr(metadata_new, field), 0)
            else:
                self.assertEqual(getattr(metadata_new, field), u"")

        #ensure images match, if supported
        if (self.metadata_class.supports_images()):
            self.assertEqual(metadata_new.images(),
                             [image1, image2, image3])

        #subclasses should ensure non-MetaData fields are converted

        #ensure that convert() builds a whole new object
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
        #perform tests only if images are actually supported
        if (self.metadata_class.supports_images()):
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

                    #ensure that adding one image works
                    metadata.add_image(image1)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assert_(image1 in metadata.images())
                    self.assert_(image2 not in metadata.images())
                    self.assert_(image3 not in metadata.images())

                    #ensure that adding a second image works
                    metadata.add_image(image2)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assert_(image1 in metadata.images())
                    self.assert_(image2 in metadata.images())
                    self.assert_(image3 not in metadata.images())

                    #ensure that adding a third image works
                    metadata.add_image(image3)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assert_(image1 in metadata.images())
                    self.assert_(image2 in metadata.images())
                    self.assert_(image3 in metadata.images())

                    #ensure that deleting the first image works
                    metadata.delete_image(image1)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assert_(image1 not in metadata.images())
                    self.assert_(image2 in metadata.images())
                    self.assert_(image3 in metadata.images())

                    #ensure that deleting the second image works
                    metadata.delete_image(image2)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assert_(image1 not in metadata.images())
                    self.assert_(image2 not in metadata.images())
                    self.assert_(image3 in metadata.images())

                    #ensure that deleting the third image works
                    metadata.delete_image(image3)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assert_(image1 not in metadata.images())
                    self.assert_(image2 not in metadata.images())
                    self.assert_(image3 not in metadata.images())

                finally:
                    temp_file.close()


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
                                 "comment"]
        self.supported_formats = [audiotools.WavPackAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_WAVPACK
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                #update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                #update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #replaygain strings not updated with set_metadata()
                #but can be updated with update_metadata()
                self.assertRaises(KeyError,
                                  track.get_metadata().__getitem__,
                                  "replaygain_track_gain")
                metadata["replaygain_track_gain"] = \
                    audiotools.ape.ApeTagItem.string(
                    "replaygain_track_gain", u"???")
                track.set_metadata(metadata)
                self.assertRaises(KeyError,
                                  track.get_metadata().__getitem__,
                                  "replaygain_track_gain")
                track.update_metadata(metadata)
                self.assertEqual(track.get_metadata()["replaygain_track_gain"],
                                 audiotools.ape.ApeTagItem.string(
                        "replaygain_track_gain", u"???"))

                #cuesheet not updated with set_metadata()
                #but can be updated with update_metadata()
                metadata["Cuesheet"] = \
                    audiotools.ape.ApeTagItem.string(
                    "Cuesheet", u"???")
                track.set_metadata(metadata)
                self.assertRaises(KeyError,
                                  track.get_metadata().__getitem__,
                                  "Cuesheet")
                track.update_metadata(metadata)
                self.assertEqual(track.get_metadata()["Cuesheet"],
                                 audiotools.ape.ApeTagItem.string(
                        "Cuesheet", u"???"))

            finally:
                temp_file.close()


    @METADATA_WAVPACK
    def test_foreign_field(self):
        metadata = audiotools.ApeTag(
        [audiotools.ape.ApeTagItem(0, False, "Title", 'Track Name'),
         audiotools.ape.ApeTagItem(0, False, "Album", 'Album Name'),
         audiotools.ape.ApeTagItem(0, False, "Track", "1/3"),
         audiotools.ape.ApeTagItem(0, False, "Media", "2/4"),
         audiotools.ape.ApeTagItem(0, False, "Foo", "Bar")])
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
                self.assertEqual(unicode(metadata2["Foo"]), u"Bar")
            finally:
                temp_file.close()

    @METADATA_WAVPACK
    def test_field_mapping(self):
        mapping = [('track_name', 'Title', u'a'),
                   ('album_name', 'Album', u'b'),
                   ('artist_name', 'Artist', u'c'),
                   ('performer_name', 'Performer', u'd'),
                   ('composer_name', 'Composer', u'e'),
                   ('conductor_name', 'Conductor', u'f'),
                   ('ISRC', 'ISRC', u'g'),
                   ('catalog', 'Catalog', u'h'),
                   ('publisher', 'Publisher', u'i'),
                   ('year', 'Year', u'j'),
                   ('date', 'Record Date', u'k'),
                   ('comment', 'Comment', u'l')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                #ensure that setting a class field
                #updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key]), unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(unicode(metadata2[key]), unicode(value))

                #ensure that updating the low-level implementation
                #is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[key] = audiotools.ape.ApeTagItem.string(
                        key, unicode(value))
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key]), unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key]), unicode(value))

                #ensure that setting numerical fields also
                #updates the low-level implementation
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.track_number = 1
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Track']), u'1')
                metadata.track_total = 2
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Track']), u'1/2')
                del(metadata.track_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Track']), u'0/2')
                del(metadata.track_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Track']), u'0')
                del(metadata.track_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata.__getitem__,
                                  'Track')

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.album_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Media']), u'3')
                metadata.album_total = 4
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Media']), u'3/4')
                del(metadata.album_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Media']), u'0/4')
                del(metadata.album_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['Media']), u'0')
                del(metadata.album_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata.__getitem__,
                                  'Media')

                #and ensure updating the low-level implementation
                #updates the numerical fields
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata['Track'] = audiotools.ape.ApeTagItem.string(
                        'Track', u"1")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 1)
                self.assertEqual(metadata.track_total, None)
                metadata['Track'] = audiotools.ape.ApeTagItem.string(
                        'Track', u"1/2")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 1)
                self.assertEqual(metadata.track_total, 2)
                metadata['Track'] = audiotools.ape.ApeTagItem.string(
                        'Track', u"0/2")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 0)
                self.assertEqual(metadata.track_total, 2)
                del(metadata['Track'])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, None)
                self.assertEqual(metadata.track_total, None)

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata['Media'] = audiotools.ape.ApeTagItem.string(
                        'Media', u"3")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 3)
                self.assertEqual(metadata.album_total, None)
                metadata['Media'] = audiotools.ape.ApeTagItem.string(
                        'Media', u"3/4")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 3)
                self.assertEqual(metadata.album_total, 4)
                metadata['Media'] = audiotools.ape.ApeTagItem.string(
                        'Media', u"0/4")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 0)
                self.assertEqual(metadata.album_total, 4)
                del(metadata['Media'])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, None)
                self.assertEqual(metadata.album_total, None)
            finally:
                temp_file.close()

    @METADATA_WAVPACK
    def test_converted(self):
        #build a generic MetaData with everything
        image1 = audiotools.Image.new(TEST_COVER1, "Text 1", 0)
        image2 = audiotools.Image.new(TEST_COVER2, "Text 2", 1)

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
                                            images=[image1, image2])

        #ensure converted() builds something with our class
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new.__class__, self.metadata_class)

        #ensure our fields match
        for field in audiotools.MetaData.FIELDS:
            if (field in self.supported_fields):
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            else:
                self.assertEqual(getattr(metadata_new, field), None)

        #ensure images match, if supported
        self.assertEqual(metadata_new.images(), [image1, image2])

        #ensure non-MetaData fields are converted
        metadata_orig = self.empty_metadata()
        metadata_orig['Foo'] = audiotools.ape.ApeTagItem.string(
            'Foo', u'Bar'.encode('utf-8'))
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_orig['Foo'].data,
                         metadata_new['Foo'].data)

        #ensure that convert() builds a whole new object
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

                track.set_metadata(metadata)
                metadata = track.get_metadata()

                #ensure that adding one image works
                metadata.add_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1])

                #ensure that adding a second image works
                metadata.add_image(image2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1,
                                                     image2])

                #ensure that deleting the first image works
                metadata.delete_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image2])

                #ensure that deleting the second image works
                metadata.delete_image(image2)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [])

            finally:
                temp_file.close()

    @METADATA_WAVPACK
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Title', u'Foo ')])
        self.assertEqual(metadata.track_name, u'Foo ')
        self.assertEqual(metadata['Title'].data, u'Foo '.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":'Title'.decode('ascii')}])
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(cleaned['Title'].data, u'Foo'.encode('ascii'))

        #check leading whitespace
        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Title', u' Foo')])
        self.assertEqual(metadata.track_name, u' Foo')
        self.assertEqual(metadata['Title'].data, u' Foo'.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":'Title'.decode('ascii')}])
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(cleaned['Title'].data, u'Foo'.encode('ascii'))

        #check empty fields
        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Title', u'')])
        self.assertEqual(metadata.track_name, u'')
        self.assertEqual(metadata['Title'].data, u''.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed empty field %(field)s") %
                          {"field":'Title'.decode('ascii')}])
        self.assertEqual(cleaned.track_name, None)
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          'Title')

        #check leading zeroes
        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Track', u'01')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata['Track'].data, u'01'.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, None)
        self.assertEqual(cleaned['Track'].data, u'1'.encode('ascii'))

        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Track', u'01/2')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata['Track'].data, u'01/2'.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, 2)
        self.assertEqual(cleaned['Track'].data, u'1/2'.encode('ascii'))

        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Track', u'1/02')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata['Track'].data, u'1/02'.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, 2)
        self.assertEqual(cleaned['Track'].data, u'1/2'.encode('ascii'))

        metadata = audiotools.ApeTag(
            [audiotools.ape.ApeTagItem.string('Track', u'01/02')])
        self.assertEqual(metadata.track_number, 1)
        self.assertEqual(metadata.track_total, 2)
        self.assertEqual(metadata['Track'].data, u'01/02'.encode('ascii'))
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":'Track'.decode('ascii')}])
        self.assertEqual(cleaned.track_number, 1)
        self.assertEqual(cleaned.track_total, 2)
        self.assertEqual(cleaned['Track'].data, u'1/2'.encode('ascii'))

        #images don't store metadata,
        #so no need to check their fields

    @METADATA_WAVPACK
    def test_replay_gain(self):
        import test_streams

        for input_class in [audiotools.WavPackAudio]:
            temp1 = tempfile.NamedTemporaryFile(
                suffix="." + input_class.SUFFIX)
            try:
                track1 = input_class.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assert_(track1.replay_gain() is None,
                             "ReplayGain present for class %s" % \
                                 (input_class.NAME))
                track1.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                input_class.add_replay_gain([track1.filename])
                self.assertEqual(track1.get_metadata().track_name, u"Foo")
                self.assert_(track1.replay_gain() is not None,
                             "ReplayGain not present for class %s" % \
                                 (input_class.NAME))

                for output_class in [audiotools.WavPackAudio]:
                    temp2 = tempfile.NamedTemporaryFile(
                        suffix="." + input_class.SUFFIX)
                    try:
                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))

                        #ensure that ReplayGain doesn't get ported
                        #via set_metadata()
                        self.assert_(track2.replay_gain() is None,
                                     "ReplayGain present for class %s" % \
                                         (output_class.NAME))
                        track2.set_metadata(track1.get_metadata())
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Foo")
                        self.assert_(track2.replay_gain() is None,
                                "ReplayGain present for class %s from %s" % \
                                         (output_class.NAME,
                                          input_class.NAME))

                        #and if ReplayGain is already set,
                        #ensure set_metadata() doesn't remove it
                        output_class.add_replay_gain([track2.filename])
                        old_replay_gain = track2.replay_gain()
                        self.assert_(old_replay_gain is not None)
                        track2.set_metadata(audiotools.MetaData(
                                track_name=u"Bar"))
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Bar")
                        self.assertEqual(track2.replay_gain(),
                                         old_replay_gain)

                    finally:
                        temp2.close()
            finally:
                temp1.close()


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
                #update_metadata on file's internal metadata round-trips okay
                metadata = self.empty_metadata()
                metadata.track_name = u"Foo"
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                #update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #update_metadata with None makes no changes
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
        import string
        import random

        #ID3v1 only supports ASCII characters
        #and not very many of them
        chars = u"".join(map(unichr,
                             range(0x30, 0x39 + 1) +
                             range(0x41, 0x5A + 1) +
                             range(0x61, 0x7A + 1)))

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                #check that setting the fields to random values works
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in xrange(random.choice(range(1, 5)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    else:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)

                #check that blanking out the fields works
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
                        setattr(metadata, field, u"")
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), None)
                    else:
                        setattr(metadata, field, 0)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), None)

                #re-set the fields with random values
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    if (field not in audiotools.MetaData.INTEGER_FIELDS):
                        unicode_string = u"".join(
                            [random.choice(chars)
                             for i in xrange(random.choice(range(1, 5)))])
                        setattr(metadata, field, unicode_string)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field),
                                         unicode_string)
                    else:
                        number = random.choice(range(1, 100))
                        setattr(metadata, field, number)
                        track.set_metadata(metadata)
                        metadata = track.get_metadata()
                        self.assertEqual(getattr(metadata, field), number)

                #check that deleting the fields works
                for field in self.supported_fields:
                    metadata = self.empty_metadata()
                    delattr(metadata, field)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), None)

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

                #ensure that setting a class field
                #updates its corresponding low-level implementation
                for (field, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)

                #ID3v1 no longer has a low-level implementation
                #since it builds and parses directly on strings
            finally:
                temp_file.close()

    @METADATA_ID3V1
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.ID3v1Comment(
            track_name="Title " + chr(0) * 24)
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from title")])
        self.assertEqual(
            cleaned,
            audiotools.ID3v1Comment(
                track_name="Title" + chr(0) * 25))

        #check leading whitespace
        metadata = audiotools.ID3v1Comment(
                track_name=" Title" + chr(0) * 24)
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"removed leading whitespace from title")])
        self.assertEqual(
            cleaned,
            audiotools.ID3v1Comment(
                    track_name="Title" + chr(0) * 25))

        #ID3v1 has no empty fields, image data or leading zeroes
        #so those can be safely ignored


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
                                 "comment"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio,
                                  audiotools.AiffAudio]

    def empty_metadata(self):
        return self.metadata_class([])

    @METADATA_ID3V2
    def test_update(self):
        import os

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            track = audio_class.from_pcm(temp_file.name, BLANK_PCM_Reader(10))
            temp_file_stat = os.stat(temp_file.name)[0]
            try:
                #update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                #update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")
            finally:
                temp_file.close()

    @METADATA_ID3V2
    def test_foreign_field(self):
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame("TT2", 0, "Track Name"),
             audiotools.id3.ID3v22_T__Frame("TAL", 0, "Album Name"),
             audiotools.id3.ID3v22_T__Frame("TRK", 0, "1/3"),
             audiotools.id3.ID3v22_T__Frame("TPA", 0, "2/4"),
             audiotools.id3.ID3v22_T__Frame("TFO", 0, "Bar")])
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
                self.assertEqual(metadata["TFO"][0].data, "Bar")
            finally:
                temp_file.close()

    @METADATA_ID3V2
    def test_field_mapping(self):
        id3_class = self.metadata_class

        INTEGER_ATTRIBS = ('track_number',
                           'track_total',
                           'album_number',
                           'album_total')

        attribs1 = {}  # a dict of attribute -> value pairs
                       # ("track_name":u"foo")
        attribs2 = {}  # a dict of ID3v2 -> value pairs
                       # ("TT2":u"foo")
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                attribs1[attribute] = attribs2[key] = u"value %d" % (i)
        attribs1["track_number"] = 2
        attribs1["track_total"] = 10
        attribs1["album_number"] = 1
        attribs1["album_total"] = 3

        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        #ensure that all the attributes match up
        for (attribute, value) in attribs1.items():
            self.assertEqual(getattr(id3, attribute), value)

        #ensure that all the keys for non-integer items match up
        for (key, value) in attribs2.items():
            self.assertEqual(unicode(id3[key][0]), value)

        #ensure the keys for integer items match up
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

        #ensure that changing attributes changes the underlying frame
        #>>> id3.track_name = u"bar"
        #>>> id3['TT2'][0] == u"bar"
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.TEXT_FRAME.NUMERICAL_IDS):
                setattr(id3, attribute, u"new value %d" % (i))
                self.assertEqual(unicode(id3[key][0]), u"new value %d" % (i))

        #ensure that changing integer attributes changes the underlying frame
        #>>> id3.track_number = 2
        #>>> id3['TRK'][0] == u"2"
        id3.track_number = 3
        id3.track_total = 0
        self.assertEqual(
            unicode(id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]][0]),
            u"3")

        id3.track_total = 8
        self.assertEqual(
            unicode(id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]][0]),
            u"3/8")

        id3.album_number = 2
        id3.album_total = 0
        self.assertEqual(
            unicode(id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]][0]),
            u"2")

        id3.album_total = 4
        self.assertEqual(
            unicode(id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]][0]),
            u"2/4")

        #reset and re-check everything for the next round
        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        #ensure that all the attributes match up
        for (attribute, value) in attribs1.items():
            self.assertEqual(getattr(id3, attribute), value)

        for (key, value) in attribs2.items():
            if (key not in id3_class.TEXT_FRAME.NUMERICAL_IDS):
                self.assertEqual(unicode(id3[key][0]), value)
            else:
                self.assertEqual(int(id3[key][0]), value)

        #ensure that changing the underlying frames changes attributes
        #>>> id3['TT2'] = [ID3v22_T__Frame('TT2, u"bar")]
        #>>> id3.track_name == u"bar"
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                id3[key] = [id3_class.TEXT_FRAME(key, 0, "new value %d" % (i))]
                self.assertEqual(getattr(id3, attribute),
                                 u"new value %d" % (i))

        #ensure that changing the underlying integer frames changes attributes
        key = id3_class.TEXT_FRAME.NUMERICAL_IDS[0]
        id3[key] = [id3_class.TEXT_FRAME(key, 0, "7")]
        self.assertEqual(id3.track_number, 7)

        id3[key] = [id3_class.TEXT_FRAME(key, 0, "8/9")]
        self.assertEqual(id3.track_number, 8)
        self.assertEqual(id3.track_total, 9)

        key = id3_class.TEXT_FRAME.NUMERICAL_IDS[1]
        id3[key] = [id3_class.TEXT_FRAME(key, 0, "4")]
        self.assertEqual(id3.album_number, 4)

        id3[key] = [id3_class.TEXT_FRAME(key, 0, "5/6")]
        self.assertEqual(id3.album_number, 5)
        self.assertEqual(id3.album_total, 6)

        #finally, just for kicks, ensure that explicitly setting
        #frames also changes attributes
        #>>> id3['TT2'] = [id3_class.TEXT_FRAME.from_unicode('TT2',u"foo")]
        #>>> id3.track_name = u"foo"
        for (i,
             (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                id3[key] = [id3_class.TEXT_FRAME.converted(key, unicode(i))]
                self.assertEqual(getattr(id3, attribute), unicode(i))

        #and ensure explicitly setting integer frames also changes attribs
        id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[0]] = [
            id3_class.TEXT_FRAME.converted(
                id3_class.TEXT_FRAME.NUMERICAL_IDS[0],
                u"4")]
        self.assertEqual(id3.track_number, 4)
        self.assertEqual(id3.track_total, None)

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
        self.assertEqual(id3.album_total, None)

        id3[id3_class.TEXT_FRAME.NUMERICAL_IDS[1]] = [
            id3_class.TEXT_FRAME.converted(
                id3_class.TEXT_FRAME.NUMERICAL_IDS[1],
                u"5/7")]
        self.assertEqual(id3.album_number, 5)
        self.assertEqual(id3.album_total, 7)

    @METADATA_ID3V2
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame.converted("TT2", u"Title ")])
        self.assertEqual(metadata.track_name, u"Title ")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         ["removed trailing whitespace from %(field)s" %
                          {"field":u"TT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        #check leading whitespace
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame.converted("TT2", u" Title")])
        self.assertEqual(metadata.track_name, u" Title")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         ["removed leading whitespace from %(field)s" %
                          {"field":u"TT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        #check empty fields
        metadata = audiotools.ID3v22Comment(
            [audiotools.id3.ID3v22_T__Frame.converted("TT2", u"")])
        self.assertEqual(metadata["TT2"][0].data, "")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         ["removed empty field %(field)s" %
                          {"field":u"TT2"}])
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          "TT2")

        #check leading zeroes,
        #depending on whether we're preserving them or not

        id3_pad = audiotools.config.get_default("ID3", "pad", "off")
        try:
            #pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "on")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             True)

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted("TRK", u"1")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, None)
            self.assertEqual(metadata["TRK"][0].data, "1")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             ["added leading zeroes to %(field)s" %
                              {"field":u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, None)
            self.assertEqual(cleaned["TRK"][0].data, "01")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted("TRK", u"1/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRK"][0].data, "1/2")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             ["added leading zeroes to %(field)s" %
                              {"field":u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRK"][0].data, "01/02")

            #don't pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "off")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             False)

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted("TRK", u"01")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, None)
            self.assertEqual(metadata["TRK"][0].data, "01")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             ["removed leading zeroes from %(field)s" %
                              {"field":u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, None)
            self.assertEqual(cleaned["TRK"][0].data, "1")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted("TRK", u"01/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRK"][0].data, "01/2")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             ["removed leading zeroes from %(field)s" %
                              {"field":u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRK"][0].data, "1/2")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted("TRK", u"1/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRK"][0].data, "1/02")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             ["removed leading zeroes from %(field)s" %
                              {"field":u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRK"][0].data, "1/2")

            metadata = audiotools.ID3v22Comment(
                [audiotools.id3.ID3v22_T__Frame.converted("TRK", u"01/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRK"][0].data, "01/02")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             ["removed leading zeroes from %(field)s" %
                              {"field":u"TRK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRK"][0].data, "1/2")
        finally:
            audiotools.config.set_default("ID3", "pad", id3_pad)


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
                                 "comment"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio]

    @METADATA_ID3V2
    def test_foreign_field(self):
        metadata = self.metadata_class(
            [audiotools.id3.ID3v23_T___Frame("TIT2", 0, "Track Name"),
             audiotools.id3.ID3v23_T___Frame("TALB", 0, "Album Name"),
             audiotools.id3.ID3v23_T___Frame("TRCK", 0, "1/3"),
             audiotools.id3.ID3v23_T___Frame("TPOS", 0, "2/4"),
             audiotools.id3.ID3v23_T___Frame("TFOO", 0, "Bar")])
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
                self.assertEqual(metadata["TFOO"][0].data, "Bar")
            finally:
                temp_file.close()

    def empty_metadata(self):
        return self.metadata_class([])

    @METADATA_ID3V2
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.ID3v23Comment(
            [audiotools.id3.ID3v23_T___Frame.converted("TIT2", u"Title ")])
        self.assertEqual(metadata.track_name, u"Title ")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        #check leading whitespace
        metadata = audiotools.ID3v23Comment(
            [audiotools.id3.ID3v23_T___Frame.converted("TIT2", u" Title")])
        self.assertEqual(metadata.track_name, u" Title")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        #check empty fields
        metadata = audiotools.ID3v23Comment(
            [audiotools.id3.ID3v23_T___Frame.converted("TIT2", u"")])
        self.assertEqual(metadata["TIT2"][0].data, "")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed empty field %(field)s") %
                          {"field":u"TIT2"}])
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          "TIT2")

        #check leading zeroes,
        #depending on whether we're preserving them or not

        id3_pad = audiotools.config.get_default("ID3", "pad", "off")
        try:
            #pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "on")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             True)

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted("TRCK", u"1")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, None)
            self.assertEqual(metadata["TRCK"][0].data, "1")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"added leading zeroes to %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, None)
            self.assertEqual(cleaned["TRCK"][0].data, "01")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted("TRCK", u"1/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "1/2")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"added leading zeroes to %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "01/02")

            #don't pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "off")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             False)

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted("TRCK", u"01")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, None)
            self.assertEqual(metadata["TRCK"][0].data, "01")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, None)
            self.assertEqual(cleaned["TRCK"][0].data, "1")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted("TRCK", u"01/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "01/2")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "1/2")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted("TRCK", u"1/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "1/02")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "1/2")

            metadata = audiotools.ID3v23Comment(
                [audiotools.id3.ID3v23_T___Frame.converted("TRCK", u"01/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "01/02")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "1/2")
        finally:
            audiotools.config.set_default("ID3", "pad", id3_pad)


class ID3v24MetaData(ID3v22MetaData):
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
                                 "comment"]
        self.supported_formats = [audiotools.MP3Audio,
                                  audiotools.MP2Audio]

    def empty_metadata(self):
        return self.metadata_class([])

    @METADATA_ID3V2
    def test_clean(self):
       #check trailing whitespace
        metadata = audiotools.ID3v24Comment(
            [audiotools.id3.ID3v24_T___Frame.converted("TIT2", u"Title ")])
        self.assertEqual(metadata.track_name, u"Title ")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        #check leading whitespace
        metadata = audiotools.ID3v24Comment(
            [audiotools.id3.ID3v24_T___Frame.converted("TIT2", u" Title")])
        self.assertEqual(metadata.track_name, u" Title")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":u"TIT2"}])
        self.assertEqual(cleaned.track_name, u"Title")

        #check empty fields
        metadata = audiotools.ID3v24Comment(
            [audiotools.id3.ID3v24_T___Frame.converted("TIT2", u"")])
        self.assertEqual(metadata["TIT2"][0].data, "")
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_(u"removed empty field %(field)s") %
                          {"field":u"TIT2"}])
        self.assertRaises(KeyError,
                          cleaned.__getitem__,
                          "TIT2")

        #check leading zeroes,
        #depending on whether we're preserving them or not

        id3_pad = audiotools.config.get_default("ID3", "pad", "off")
        try:
            #pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "on")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             True)

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted("TRCK", u"1")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, None)
            self.assertEqual(metadata["TRCK"][0].data, "1")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"added leading zeroes to %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, None)
            self.assertEqual(cleaned["TRCK"][0].data, "01")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted("TRCK", u"1/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "1/2")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"added leading zeroes to %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "01/02")

            #don't pad ID3v2 tags with 0
            audiotools.config.set_default("ID3", "pad", "off")
            self.assertEqual(audiotools.config.getboolean("ID3", "pad"),
                             False)

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted("TRCK", u"01")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, None)
            self.assertEqual(metadata["TRCK"][0].data, "01")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, None)
            self.assertEqual(cleaned["TRCK"][0].data, "1")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted("TRCK", u"01/2")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "01/2")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "1/2")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted("TRCK", u"1/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "1/02")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "1/2")

            metadata = audiotools.ID3v24Comment(
                [audiotools.id3.ID3v24_T___Frame.converted("TRCK", u"01/02")])
            self.assertEqual(metadata.track_number, 1)
            self.assertEqual(metadata.track_total, 2)
            self.assertEqual(metadata["TRCK"][0].data, "01/02")
            fixes = []
            cleaned = metadata.clean(fixes)
            self.assertEqual(fixes,
                             [_(u"removed leading zeroes from %(field)s") %
                              {"field":u"TRCK"}])
            self.assertEqual(cleaned.track_number, 1)
            self.assertEqual(cleaned.track_total, 2)
            self.assertEqual(cleaned["TRCK"][0].data, "1/2")
        finally:
            audiotools.config.set_default("ID3", "pad", id3_pad)


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
                                 "comment"]
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
                                 "comment"]
        self.supported_formats = [audiotools.FlacAudio,
                                  audiotools.OggFlacAudio]

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
                #update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                #update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #streaminfo not updated with set_metadata()
                #but can be updated with update_metadata()
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

                #vendor_string not updated with set_metadata()
                #but can be updated with update_metadata()
                old_vorbiscomment = metadata.get_block(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)
                new_vorbiscomment = audiotools.flac.Flac_VORBISCOMMENT(
                    comment_strings=old_vorbiscomment.comment_strings[:],
                    vendor_string=u"Vendor String")
                metadata.replace_blocks(
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID, [new_vorbiscomment])
                track.set_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                        ).vendor_string,
                                 old_vorbiscomment.vendor_string)
                track.update_metadata(metadata)
                self.assertEqual(track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID
                        ).vendor_string,
                                 new_vorbiscomment.vendor_string)

                #REPLAYGAIN_* tags not updated with set_metadata()
                #but can be updated with update_metadata()
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
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID, [new_vorbiscomment])
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

                #WAVEFORMATEXTENSIBLE_CHANNEL_MASK
                #not updated with set_metadata()
                #but can be updated with update_metadata()
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
                    audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID, [new_vorbiscomment])
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

                #cuesheet not updated with set_metadata()
                #but can be updated with update_metadata()
                new_cuesheet = audiotools.flac.Flac_CUESHEET(
                    catalog_number=chr(0) * 128,
                    lead_in_samples=0,
                    is_cdda=1,
                    tracks=[audiotools.flac.Flac_CUESHEET_track(
                            offset=0,
                            number=0,
                            ISRC=" " * 12,
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[audiotools.flac.Flac_CUESHEET_index(0,
                                                                         0)])])
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

                if (audio_class is not audiotools.OggFlacAudio):
                    #seektable not updated with set_metadata()
                    #but can be updated with update_metadata()

                    #Ogg FLAC doesn't really support seektables as such

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

                #application blocks not updated with set_metadata()
                #but can be updated with update_metadata()
                application = audiotools.flac.Flac_APPLICATION(
                    application_id="fooz",
                    data="kelp")
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
                self.assert_(isinstance(metadata, audiotools.FlacMetaData))
                self.assertEqual(track.get_metadata().get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)["FOO"],
                                 [u"Bar"])
            finally:
                temp_file.close()

    @METADATA_FLAC
    def test_field_mapping(self):
        mapping = [('track_name', 'TITLE', u'a'),
                   ('track_number', 'TRACKNUMBER', 1),
                   ('track_total', 'TRACKTOTAL', 2),
                   ('album_name', 'ALBUM', u'b'),
                   ('artist_name', 'ARTIST', u'c'),
                   ('performer_name', 'PERFORMER', u'd'),
                   ('composer_name', 'COMPOSER', u'e'),
                   ('conductor_name', 'CONDUCTOR', u'f'),
                   ('media', 'SOURCE MEDIUM', u'g'),
                   ('ISRC', 'ISRC', u'h'),
                   ('catalog', 'CATALOG', u'i'),
                   ('copyright', 'COPYRIGHT', u'j'),
                   ('year', 'DATE', u'k'),
                   ('album_number', 'DISCNUMBER', 3),
                   ('album_total', 'DISCTOTAL', 4),
                   ('comment', 'COMMENT', u'l')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                #ensure that setting a class field
                #updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[key][0],
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[key][0],
                        unicode(value))

                #ensure that updating the low-level implementation
                #is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata.get_block(
                        audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[key] = \
                        [unicode(value)]
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[key][0],
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2.get_block(
                            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)[key][0],
                        unicode(value))
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

        #ensure that convert() builds a whole new object
        metadata_new.track_name = u"Foo"
        self.assertEqual(metadata_new.track_name, u"Foo")
        metadata_new2 = self.metadata_class.converted(metadata_new)
        self.assertEqual(metadata_new2, metadata_new)
        metadata_new2.track_name = u"Bar"
        self.assertEqual(metadata_new2.track_name, u"Bar")
        self.assertEqual(metadata_new.track_name, u"Foo")

    @METADATA_FLAC
    def test_oversized(self):
        oversized_image = audiotools.Image.new(HUGE_BMP.decode('bz2'), u'', 0)
        oversized_text = "QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2').decode('ascii')

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                #check that setting an oversized field fails properly
                metadata = self.empty_metadata()
                metadata.track_name = oversized_text
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertNotEqual(metadata.track_name, oversized_text)

                #check that setting an oversized image fails properly
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
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)["TRACKNUMBER"] = [u"2/4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata.get_block(
            audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)["DISCNUMBER"] = [u"1/3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

    @METADATA_FLAC
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE=Foo "], u"")])
        self.assertEqual(metadata.track_name, u'Foo ')
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        #check leading whitespace
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE= Foo"], u"")])
        self.assertEqual(metadata.track_name, u' Foo')
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(results,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        #check leading zeroes
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=01"], u"")])
        self.assertEqual(
            metadata.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)["TRACKNUMBER"],
            [u"01"])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(
            cleaned.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)["TRACKNUMBER"],
            [u"1"])
        self.assertEqual(results,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field": u"TRACKNUMBER"}])

        #check empty fields
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                        ["TITLE=  "], u"")])
        self.assertEqual(
            metadata.get_block(
                audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID)["TITLE"], [u'  '])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT([], u"")]))

        self.assertEqual(results,
                         [_(u"removed empty field %(field)s") %
                          {"field": u"TITLE"}])

        #check mis-tagged images
        metadata = audiotools.FlacMetaData(
                    [audiotools.flac.Flac_PICTURE(
                        0, "image/jpeg", u"", 20, 20, 24, 10,
"""iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKAQMAAAC3/F3+AAAAAXNSR0IArs4c6QAAAANQTFRF////
p8QbyAAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9sEBBMWM3PnvjMAAAALSURBVAjXY2DA
BwAAHgABboVHMgAAAABJRU5ErkJggg==""".decode('base64'))])
        self.assertEqual(
            len(metadata.get_blocks(audiotools.flac.Flac_PICTURE.BLOCK_ID)), 1)
        image = metadata.images()[0]
        self.assertEqual(image.mime_type, "image/jpeg")
        self.assertEqual(image.width, 20)
        self.assertEqual(image.height, 20)
        self.assertEqual(image.color_depth, 24)
        self.assertEqual(image.color_count, 10)

        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"fixed embedded image metadata fields")])
        self.assertEqual(
            len(cleaned.get_blocks(audiotools.flac.Flac_PICTURE.BLOCK_ID)), 1)
        image = cleaned.images()[0]
        self.assertEqual(image.mime_type, "image/png")
        self.assertEqual(image.width, 10)
        self.assertEqual(image.height, 10)
        self.assertEqual(image.color_depth, 8)
        self.assertEqual(image.color_count, 1)

        #check seektable with empty seekpoints
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_SEEKTABLE([(0, 10, 10),
                                        (10, 20, 0),
                                        (10, 20, 0),
                                        (10, 20, 0),
                                        (10, 20, 20)])])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"removed empty seekpoints from seektable")])
        self.assertEqual(
            cleaned.get_block(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            audiotools.flac.Flac_SEEKTABLE([(0, 10, 10),
                                       (10, 20, 20)]))

        #check seektable with duplicate seekpoints
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                        (2, 20, 10),
                                        (2, 20, 10),
                                        (2, 20, 10),
                                        (4, 40, 10)])])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"reordered seektable to be in ascending order")])
        self.assertEqual(
            cleaned.get_block(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                       (2, 20, 10),
                                       (4, 40, 10)]))

        #check seektable with mis-ordered seekpoints
        metadata = audiotools.FlacMetaData(
            [audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                        (6, 60, 10),
                                        (4, 40, 10),
                                        (2, 20, 10),
                                        (8, 80, 10)])])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"reordered seektable to be in ascending order")])
        self.assertEqual(
            cleaned.get_block(audiotools.flac.Flac_SEEKTABLE.BLOCK_ID),
            audiotools.flac.Flac_SEEKTABLE([(0, 0, 10),
                                       (2, 20, 10),
                                       (4, 40, 10),
                                       (6, 60, 10),
                                       (8, 80, 10)]))

        #check that cleanup doesn't disturb other metadata blocks
        #FIXME
        metadata = audiotools.FlacMetaData([
            audiotools.flac.Flac_STREAMINFO(
                minimum_block_size=4096,
                maximum_block_size=4096,
                minimum_frame_size=14,
                maximum_frame_size=18,
                sample_rate=44100,
                channels=2,
                bits_per_sample=16,
                total_samples=149606016L,
                md5sum='\xae\x87\x1c\x8e\xe1\xfc\x16\xde' +
                '\x86\x81&\x8e\xc8\xd52\xff'),
            audiotools.flac.Flac_APPLICATION(
                    application_id="FOOZ",
                    data="KELP"),
            audiotools.flac.Flac_SEEKTABLE([
                        (0L, 0L, 4096),
                        (8335360L, 30397L, 4096),
                        (8445952L, 30816L, 4096),
                        (17379328L, 65712L, 4096),
                        (17489920L, 66144L, 4096),
                        (28041216L, 107360L, 4096),
                        (28151808L, 107792L, 4096),
                        (41672704L, 160608L, 4096),
                        (41783296L, 161040L, 4096),
                        (54444032L, 210496L, 4096),
                        (54558720L, 210944L, 4096),
                        (65687552L, 254416L, 4096),
                        (65802240L, 254864L, 4096),
                        (76267520L, 295744L, 4096),
                        (76378112L, 296176L, 4096),
                        (89624576L, 347920L, 4096),
                        (89739264L, 348368L, 4096),
                        (99688448L, 387232L, 4096),
                        (99803136L, 387680L, 4096),
                        (114176000L, 443824L, 4096),
                        (114286592L, 444256L, 4096),
                        (125415424L, 487728L, 4096),
                        (125526016L, 488160L, 4096),
                        (138788864L, 539968L, 4096),
                        (138903552L, 540416L, 4096)]),
            audiotools.flac.Flac_VORBISCOMMENT(["TITLE=Foo "], u""),
            audiotools.flac.Flac_CUESHEET(
                catalog_number='4560248013904\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                lead_in_samples=88200L,
                is_cdda=1,
                tracks=[
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=0L,
                        number=1,
                        ISRC='JPK631002201',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=8336076L,
                        number=2,
                        ISRC='JPK631002202',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=17379516L,
                        number=3,
                        ISRC='JPK631002203',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=28042308L,
                        number=4,
                        ISRC='JPK631002204',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=41672736L,
                        number=5,
                        ISRC='JPK631002205',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=54447624L,
                        number=6,
                        ISRC='JPK631002206',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=65689596L,
                        number=7,
                        ISRC='JPK631002207',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=76267716L,
                        number=8,
                        ISRC='JPK631002208',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=89627076L,
                        number=9,
                        ISRC='JPK631002209',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=99691872L,
                        number=10,
                        ISRC='JPK631002210',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=114176076L,
                        number=11,
                        ISRC='JPK631002211',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(113484L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=125415696L,
                        number=12,
                        ISRC='JPK631002212',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(114072L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=138791520L,
                        number=13,
                        ISRC='JPK631002213',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            audiotools.flac.Flac_CUESHEET_index(0L, 0),
                            audiotools.flac.Flac_CUESHEET_index(114072L, 1)]),
                    audiotools.flac.Flac_CUESHEET_track(
                        offset=149606016L,
                        number=170,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[])]),
            audiotools.flac.Flac_PICTURE(0, "image/jpeg", u"",
                                    500, 500, 24, 0, TEST_COVER1)])

        self.assertEqual([b.BLOCK_ID for b in metadata.block_list],
                         [audiotools.flac.Flac_STREAMINFO.BLOCK_ID,
                          audiotools.flac.Flac_APPLICATION.BLOCK_ID,
                          audiotools.flac.Flac_SEEKTABLE.BLOCK_ID,
                          audiotools.flac.Flac_VORBISCOMMENT.BLOCK_ID,
                          audiotools.flac.Flac_CUESHEET.BLOCK_ID,
                          audiotools.flac.Flac_PICTURE.BLOCK_ID])

        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TITLE"}])

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

    @METADATA_FLAC
    def test_replay_gain(self):
        import test_streams

        for input_class in [audiotools.FlacAudio,
                            audiotools.OggFlacAudio,
                            audiotools.VorbisAudio]:
            temp1 = tempfile.NamedTemporaryFile(suffix="." + input_class.SUFFIX)
            try:
                track1 = input_class.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assert_(track1.replay_gain() is None,
                             "ReplayGain present for class %s" % \
                                 (input_class.NAME))
                track1.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                input_class.add_replay_gain([track1.filename])
                self.assertEqual(track1.get_metadata().track_name, u"Foo")
                self.assert_(track1.replay_gain() is not None,
                             "ReplayGain not present for class %s" % \
                                 (input_class.NAME))

                for output_class in [audiotools.FlacAudio,
                                     audiotools.OggFlacAudio]:
                    temp2 = tempfile.NamedTemporaryFile(
                        suffix="." + input_class.SUFFIX)
                    try:
                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))

                        #ensure that ReplayGain doesn't get ported
                        #via set_metadata()
                        self.assert_(track2.replay_gain() is None,
                                     "ReplayGain present for class %s" % \
                                         (output_class.NAME))
                        track2.set_metadata(track1.get_metadata())
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Foo")
                        self.assert_(track2.replay_gain() is None,
                                "ReplayGain present for class %s from %s" % \
                                         (output_class.NAME,
                                          input_class.NAME))

                        #and if ReplayGain is already set,
                        #ensure set_metadata() doesn't remove it
                        output_class.add_replay_gain([track2.filename])
                        old_replay_gain = track2.replay_gain()
                        self.assert_(old_replay_gain is not None)
                        track2.set_metadata(audiotools.MetaData(
                                track_name=u"Bar"))
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Bar")
                        self.assertEqual(track2.replay_gain(),
                                         old_replay_gain)
                    finally:
                        temp2.close()
            finally:
                temp1.close()

    @METADATA_FLAC
    def test_getattr(self):
        #track_number grabs the first available integer
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=10"],
                        u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=10",
                         u"TRACKNUMBER=5"],
                        u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=foo 10 bar"],
                        u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=foo",
                         u"TRACKNUMBER=10"],
                        u"vendor")]).track_number,
            10)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=foo",
                         u"TRACKNUMBER=foo 10 bar"],
                        u"vendor")]).track_number,
            10)

        #track_number is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"tRaCkNuMbEr=10"],
                        u"vendor")]).track_number,
            10)

        #album_number grabs the first available integer
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=20"],
                        u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=20",
                         u"DISCNUMBER=5"],
                        u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=foo 20 bar"],
                        u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=foo",
                         u"DISCNUMBER=20"],
                        u"vendor")]).album_number,
            20)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=foo",
                         u"DISCNUMBER=foo 20 bar"],
                        u"vendor")]).album_number,
            20)

        #album_number is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"dIsCnUmBeR=20"],
                        u"vendor")]).album_number,
            20)

        #track_total grabs the first available TRACKTOTAL integer
        #before falling back on slashed fields
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKTOTAL=15"],
                        u"vendor")]).track_total,
            15)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=5/10"],
                        u"vendor")]).track_total,
            10)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKNUMBER=5/10",
                         u"TRACKTOTAL=15"],
                        u"vendor")]).track_total,
            15)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TRACKTOTAL=15",
                         u"TRACKNUMBER=5/10"],
                        u"vendor")]).track_total,
            15)

        #track_total is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"tracktotal=15"],
                        u"vendor")]).track_total,
            15)

        #track_total supports aliases
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TOTALTRACKS=15"],
                        u"vendor")]).track_total,
            15)

        #album_total grabs the first available DISCTOTAL integer
        #before falling back on slashed fields
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCTOTAL=25"],
                        u"vendor")]).album_total,
            25)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=10/30"],
                        u"vendor")]).album_total,
            30)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCNUMBER=10/30",
                         u"DISCTOTAL=25"],
                        u"vendor")]).album_total,
            25)

        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"DISCTOTAL=25",
                         u"DISCNUMBER=10/30"],
                        u"vendor")]).album_total,
            25)

        #album_total is case-insensitive
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"disctotal=25"],
                        u"vendor")]).album_total,
            25)

        #album_total supports aliases
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TOTALDISCS=25"],
                        u"vendor")]).album_total,
            25)

        #other fields grab the first available item
        self.assertEqual(
            audiotools.FlacMetaData([
                    audiotools.flac.Flac_VORBISCOMMENT(
                        [u"TITLE=first",
                         u"TITLE=last"],
                        u"vendor")]).track_name,
            u"first")

    @METADATA_FLAC
    def test_setattr(self):
        #track_number adds new field if necessary
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [], u"vendor")])
        self.assertEqual(metadata.track_number, None)
        metadata.track_number = 11
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=11"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=blah"],
                    u"vendor")])
        self.assertEqual(metadata.track_number, None)
        metadata.track_number = 11
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=blah",
                          u"TRACKNUMBER=11"])
        self.assertEqual(metadata.track_number, 11)

        #track_number updates the first integer field
        #and leaves other junk in that field alone
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
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

        #album_number adds new field if necessary
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [], u"vendor")])
        self.assertEqual(metadata.album_number, None)
        metadata.album_number = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=3"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=blah"],
                    u"vendor")])
        self.assertEqual(metadata.album_number, None)
        metadata.album_number = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=blah",
                          u"DISCNUMBER=3"])
        self.assertEqual(metadata.album_number, 3)

        #album_number updates the first integer field
        #and leaves other junk in that field alone
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

        #track_total adds new TRACKTOTAL field if necessary
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [], u"vendor")])
        self.assertEqual(metadata.track_total, None)
        metadata.track_total = 12
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=12"])
        self.assertEqual(metadata.track_total, 12)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKTOTAL=blah"],
                    u"vendor")])
        self.assertEqual(metadata.track_total, None)
        metadata.track_total = 12
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=blah",
                          u"TRACKTOTAL=12"])
        self.assertEqual(metadata.track_total, 12)

        #track_total updates first integer TRACKTOTAL field first if possible
        #including aliases
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKTOTAL=blah",
                     u"TRACKTOTAL=2"], u"vendor")])
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=blah",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TOTALTRACKS=blah",
                     u"TOTALTRACKS=2"], u"vendor")])
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TOTALTRACKS=blah",
                          u"TOTALTRACKS=3"])
        self.assertEqual(metadata.track_total, 3)

        #track_total updates slashed TRACKNUMBER field if necessary
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1/4",
                     u"TRACKTOTAL=2"], u"vendor")])
        self.assertEqual(metadata.track_total, 2)
        metadata.track_total = 3
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1/4",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 3)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1/4"], u"vendor")])
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

        #album_total adds new DISCTOTAL field if necessary
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [], u"vendor")])
        self.assertEqual(metadata.album_total, None)
        metadata.album_total = 4
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCTOTAL=blah"],
                    u"vendor")])
        self.assertEqual(metadata.album_total, None)
        metadata.album_total = 4
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCTOTAL=blah",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        #album_total updates DISCTOTAL field first if possible
        #including aliases
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCTOTAL=blah",
                     u"DISCTOTAL=3"], u"vendor")])
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 4
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCTOTAL=blah",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TOTALDISCS=blah",
                     u"TOTALDISCS=3"], u"vendor")])
        self.assertEqual(metadata.album_total, 3)
        metadata.album_total = 4
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TOTALDISCS=blah",
                          u"TOTALDISCS=4"])
        self.assertEqual(metadata.album_total, 4)

        #album_total updates slashed DISCNUMBER field if necessary
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=2/3",
                     u"DISCTOTAL=5"], u"vendor")])
        self.assertEqual(metadata.album_total, 5)
        metadata.album_total = 6
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2/3",
                          u"DISCTOTAL=6"])
        self.assertEqual(metadata.album_total, 6)

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=2/3"], u"vendor")])
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

        #other fields update the first match
        #while leaving the rest alone
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

        #setting field to an empty string is okay
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [], u"vendor")])
        metadata.track_name = u""
        self.assertEqual(metadata.track_name, u"")
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TITLE="])

    @METADATA_FLAC
    def test_delattr(self):
        #deleting field removes all instances of it
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE=track name"],
                    u"vendor")])
        del(metadata.track_name)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE=track name",
                     u"ALBUM=album name"],
                    u"vendor")])
        del(metadata.track_name)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"ALBUM=album name"])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE=track name",
                     u"TITLE=track name 2",
                     u"ALBUM=album name",
                     u"TITLE=track name 3"],
                    u"vendor")])
        del(metadata.track_name)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"ALBUM=album name"])

        #setting field to None is the same as deleting field
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TITLE=track name"],
                    u"vendor")])
        metadata.track_name = None
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])

        #deleting track_number removes TRACKNUMBER field
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1"],
                    u"vendor")])
        del(metadata.track_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])

        #deleting slashed TRACKNUMBER converts it to fresh TRACKTOTAL field
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1/3"],
                    u"vendor")])
        del(metadata.track_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=3"])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1/3",
                     u"TRACKTOTAL=4"],
                    u"vendor")])
        self.assertEqual(metadata.track_total, 4)
        del(metadata.track_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKTOTAL=4",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 4)

        #deleting track_total removes TRACKTOTAL/TOTALTRACKS fields
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKTOTAL=3",
                     u"TOTALTRACKS=4"],
                    u"vendor")])
        del(metadata.track_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertEqual(metadata.track_total, None)

        #deleting track_total also removes slashed side of TRACKNUMBER fields
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1/3"],
                    u"vendor")])
        del(metadata.track_total)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER=1 / foo 3 baz"],
                    u"vendor")])
        del(metadata.track_total)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"TRACKNUMBER= foo 1 bar / blah 4 baz"], u"vendor")])
        del(metadata.track_total)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"TRACKNUMBER= foo 1 bar"])

        #deleting album_number removes DISCNUMBER field
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=2"],
                    u"vendor")])
        del(metadata.album_number)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])

        #deleting slashed DISCNUMBER converts it to fresh DISCTOTAL field
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
                         [u"DISCTOTAL=5",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 5)

        #deleting album_total removes DISCTOTAL/TOTALDISCS fields
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCTOTAL=4",
                     u"TOTALDISCS=5"],
                    u"vendor")])
        del(metadata.album_total)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [])
        self.assertEqual(metadata.album_total, None)

        #deleting album_total also removes slashed side of DISCNUMBER fields
        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=2/4"],
                    u"vendor")])
        del(metadata.album_total)
        self.assertEqual(metadata.album_total, None)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER=2 / foo 4 baz"],
                    u"vendor")])
        del(metadata.album_total)
        self.assertEqual(metadata.album_total, None)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.FlacMetaData([
                audiotools.flac.Flac_VORBISCOMMENT(
                    [u"DISCNUMBER= foo 2 bar / blah 4 baz"], u"vendor")])
        del(metadata.album_total)
        self.assertEqual(metadata.album_total, None)
        self.assertEqual(metadata.get_block(4).comment_strings,
                         [u"DISCNUMBER= foo 2 bar"])


class M4AMetaDataTest(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.M4A_META_Atom
        self.supported_fields = ["track_name",
                                 "track_number",
                                 "track_total",
                                 "album_name",
                                 "artist_name",
                                 "composer_name",
                                 "copyright",
                                 "year",
                                 "album_number",
                                 "album_total",
                                 "comment"]
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
                #update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                #update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #set_metadata can't alter the '\xa9too' field
                metadata = track.get_metadata()
                old_ilst = metadata.ilst_atom()["\xa9too"]
                new_ilst = audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                    '\xa9too',
                    [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(
                            0, 1, "Fooz")])
                metadata.ilst_atom().replace_child(new_ilst)
                self.assertEqual(metadata.ilst_atom()["\xa9too"],
                                 new_ilst)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.ilst_atom()["\xa9too"], old_ilst)

                #update_metadata can alter the '\xa9too' field
                metadata = track.get_metadata()
                old_ilst = metadata.ilst_atom()["\xa9too"]
                new_ilst = audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                    '\xa9too',
                    [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(
                            0, 1, "Fooz")])
                metadata.ilst_atom().replace_child(new_ilst)
                self.assertEqual(metadata.ilst_atom()["\xa9too"],
                                 new_ilst)
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.ilst_atom()["\xa9too"], new_ilst)
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
            [M4A_HDLR_Atom(0, 0, '\x00\x00\x00\x00',
                           'mdir', 'appl', 0, 0, '', 0),
             M4A_Tree_Atom(
                    'ilst',
                    [M4A_ILST_Leaf_Atom(
                            '\xa9nam',
                            [M4A_ILST_Unicode_Data_Atom(0, 1, "Track Name")]),
                     M4A_ILST_Leaf_Atom(
                            '\xa9alb',
                            [M4A_ILST_Unicode_Data_Atom(0, 1, "Album Name")]),
                     M4A_ILST_Leaf_Atom(
                            'trkn', [M4A_ILST_TRKN_Data_Atom(1, 3)]),
                     M4A_ILST_Leaf_Atom(
                            'disk', [M4A_ILST_DISK_Data_Atom(2, 4)]),
                     M4A_ILST_Leaf_Atom(
                            '\xa9foo',
                            [M4A_ILST_Unicode_Data_Atom(0, 1, "Bar")])]),
             M4A_FREE_Atom(1024)])

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
                self.assertEqual(
                    track.get_metadata().ilst_atom()["\xa9foo"].data,
                    "\x00\x00\x00\x13data\x00\x00\x00\x01\x00\x00\x00\x00Bar")
            finally:
                temp_file.close()

    @METADATA_M4A
    def test_field_mapping(self):
        mapping = [('track_name', '\xA9nam', u'a'),
                   ('artist_name', '\xA9ART', u'b'),
                   ('year', '\xA9day', u'c'),
                   ('album_name', '\xA9alb', u'd'),
                   ('composer_name', '\xA9wrt', u'e'),
                   ('comment', '\xA9cmt', u'f'),
                   ('copyright', 'cprt', u'g')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                #ensure that setting a class field
                #updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata['ilst'][key]['data'].data.decode('utf-8'),
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2['ilst'][key]['data'].data.decode('utf-8'),
                        unicode(value))

                #ensure that updating the low-level implementation
                #is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata['ilst'].add_child(
                        audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                            key,
                            [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(
                                    0, 1, unicode(value).encode('utf-8'))]))
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata['ilst'][key]['data'].data.decode('utf-8'),
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata['ilst'][key]['data'].data.decode('utf-8'),
                        unicode(value))

                #ensure that setting numerical fields also
                #updates the low-level implementation
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.track_number = 1
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata['ilst']['trkn']['data'].track_number,
                                 1)
                self.assertEqual(metadata['ilst']['trkn']['data'].track_total,
                                 0)
                metadata.track_total = 2
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata['ilst']['trkn']['data'].track_number,
                                 1)
                self.assertEqual(metadata['ilst']['trkn']['data'].track_total,
                                 2)
                del(metadata.track_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata['ilst']['trkn']['data'].track_number,
                                 0)
                self.assertEqual(metadata['ilst']['trkn']['data'].track_total,
                                 2)
                del(metadata.track_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata['ilst'].__getitem__,
                                  'trkn')

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.album_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata['ilst']['disk']['data'].disk_number,
                                 3)
                self.assertEqual(metadata['ilst']['disk']['data'].disk_total,
                                 0)

                metadata.album_total = 4
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata['ilst']['disk']['data'].disk_number,
                                 3)
                self.assertEqual(metadata['ilst']['disk']['data'].disk_total,
                                 4)
                del(metadata.album_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata['ilst']['disk']['data'].disk_number,
                                 0)
                self.assertEqual(metadata['ilst']['disk']['data'].disk_total,
                                 4)
                del(metadata.album_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata['ilst'].__getitem__,
                                  'disk')
            finally:
                temp_file.close()

    @METADATA_M4A
    def test_images(self):
        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                metadata = self.empty_metadata()
                self.assertEqual(metadata.images(), [])

                image1 = audiotools.Image.new(TEST_COVER1, u"", 0)

                track.set_metadata(metadata)
                metadata = track.get_metadata()

                #ensure that adding one image works
                metadata.add_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [image1])

                #ensure that deleting the first image works
                metadata.delete_image(image1)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.images(), [])

            finally:
                temp_file.close()

    @METADATA_M4A
    def test_converted(self):
        #build a generic MetaData with everything
        image1 = audiotools.Image.new(TEST_COVER1, "", 0)

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

        #ensure converted() builds something with our class
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new.__class__, self.metadata_class)

        #ensure our fields match
        for field in audiotools.MetaData.FIELDS:
            if (field in self.supported_fields):
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            elif (field in audiotools.MetaData.INTEGER_FIELDS):
                self.assertEqual(getattr(metadata_new, field), 0)
            else:
                self.assertEqual(getattr(metadata_new, field), u"")

        #ensure images match, if supported
        if (self.metadata_class.supports_images()):
            self.assertEqual(metadata_new.images(), [image1])

        #check non-MetaData fields
        metadata_orig = self.empty_metadata()
        metadata_orig['ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                'test',
                [audiotools.m4a_atoms.M4A_Leaf_Atom("data", "foobar")]))
        self.assertEqual(metadata_orig['ilst']['test']['data'].data, "foobar")
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_orig['ilst']['test']['data'].data, "foobar")

        #ensure that convert() builds a whole new object
        metadata_new.track_name = u"Foo"
        self.assertEqual(metadata_new.track_name, u"Foo")
        metadata_new2 = self.metadata_class.converted(metadata_new)
        self.assertEqual(metadata_new2.track_name, u"Foo")
        metadata_new2.track_name = u"Bar"
        self.assertEqual(metadata_new2.track_name, u"Bar")
        self.assertEqual(metadata_new.track_name, u"Foo")

    @METADATA_M4A
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.m4a_atoms.M4A_META_Atom(
            0, 0, [audiotools.m4a_atoms.M4A_Tree_Atom('ilst', [])])
        metadata['ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                "\xa9nam",
                [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(0, 1, "Foo ")]))
        self.assertEqual(metadata['ilst']["\xa9nam"]['data'].data, "Foo ")
        self.assertEqual(metadata.track_name, u'Foo ')
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_("removed trailing whitespace from %(field)s") %
                          {"field":"nam"}])
        self.assertEqual(cleaned['ilst']['\xa9nam']['data'].data, "Foo")
        self.assertEqual(cleaned.track_name, u'Foo')

        #check leading whitespace
        metadata = audiotools.m4a_atoms.M4A_META_Atom(
            0, 0, [audiotools.m4a_atoms.M4A_Tree_Atom('ilst', [])])
        metadata['ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                "\xa9nam",
                [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(0, 1, " Foo")]))
        self.assertEqual(metadata['ilst']["\xa9nam"]['data'].data, " Foo")
        self.assertEqual(metadata.track_name, u' Foo')
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_("removed leading whitespace from %(field)s") %
                          {"field":"nam"}])
        self.assertEqual(cleaned['ilst']['\xa9nam']['data'].data, "Foo")
        self.assertEqual(cleaned.track_name, u'Foo')

        #check empty fields
        metadata = audiotools.m4a_atoms.M4A_META_Atom(
            0, 0, [audiotools.m4a_atoms.M4A_Tree_Atom('ilst', [])])
        metadata['ilst'].add_child(
            audiotools.m4a_atoms.M4A_ILST_Leaf_Atom(
                "\xa9nam",
                [audiotools.m4a_atoms.M4A_ILST_Unicode_Data_Atom(0, 1, "")]))
        self.assertEqual(metadata['ilst']["\xa9nam"]['data'].data, "")
        self.assertEqual(metadata.track_name, u'')
        fixes = []
        cleaned = metadata.clean(fixes)
        self.assertEqual(fixes,
                         [_("removed empty field %(field)s") %
                          {"field":"nam"}])
        self.assertRaises(KeyError,
                          cleaned['ilst'].__getitem__,
                          '\xa9nam')
        self.assertEqual(cleaned.track_name, u'')

        #numerical fields can't have whitespace
        #and images aren't stored with metadata
        #so there's no need to check those


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
                                 "comment"]
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
                #update_metadata on file's internal metadata round-trips okay
                track.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Foo")
                metadata.track_name = u"Bar"
                track.update_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #update_metadata on unwritable file generates IOError
                metadata = track.get_metadata()
                os.chmod(temp_file.name, 0)
                self.assertRaises(IOError,
                                  track.update_metadata,
                                  metadata)
                os.chmod(temp_file.name, temp_file_stat)

                #update_metadata with foreign MetaData generates ValueError
                self.assertRaises(ValueError,
                                  track.update_metadata,
                                  audiotools.MetaData(track_name=u"Foo"))

                #update_metadata with None makes no changes
                track.update_metadata(None)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name, u"Bar")

                #vendor_string not updated with set_metadata()
                #but can be updated with update_metadata()
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

                #REPLAYGAIN_* tags not updated with set_metadata()
                #but can be updated with update_metadata()
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
        mapping = [('track_name', 'TITLE', u'a'),
                   ('track_number', 'TRACKNUMBER', 1),
                   ('track_total', 'TRACKTOTAL', 2),
                   ('album_name', 'ALBUM', u'b'),
                   ('artist_name', 'ARTIST', u'c'),
                   ('performer_name', 'PERFORMER', u'd'),
                   ('composer_name', 'COMPOSER', u'e'),
                   ('conductor_name', 'CONDUCTOR', u'f'),
                   ('media', 'SOURCE MEDIUM', u'g'),
                   ('ISRC', 'ISRC', u'h'),
                   ('catalog', 'CATALOG', u'i'),
                   ('copyright', 'COPYRIGHT', u'j'),
                   ('year', 'DATE', u'k'),
                   ('album_number', 'DISCNUMBER', 3),
                   ('album_total', 'DISCTOTAL', 4),
                   ('comment', 'COMMENT', u'l')]

        for format in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                track = format.from_pcm(temp_file.name, BLANK_PCM_Reader(1))

                #ensure that setting a class field
                #updates its corresponding low-level implementation
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    setattr(metadata, field, value)
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[key][0],
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[key][0],
                        unicode(value))

                #ensure that updating the low-level implementation
                #is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[key] = [unicode(value)]
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata[key][0],
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2[key][0],
                        unicode(value))
            finally:
                temp_file.close()

    @METADATA_VORBIS
    def test_getitem(self):
        #getitem with no matches raises KeyError
        self.assertRaises(KeyError,
                          audiotools.VorbisComment([u"FOO=kelp"],
                                                   u"vendor").__getitem__,
                          u"BAR")

        #getitem with 1 match returns list of length 1
        self.assertEqual(
            audiotools.VorbisComment([u"FOO=kelp",
                                      u"BAR=spam"], u"vendor")[u"FOO"],
            [u"kelp"])

        #getitem with multiple matches returns multiple items, in order
        self.assertEqual(
            audiotools.VorbisComment([u"FOO=1",
                                      u"BAR=spam",
                                      u"FOO=2",
                                      u"FOO=3"], u"vendor")[u"FOO"],
            [u"1", u"2", u"3"])

        #getitem with aliases returns all matching items, in order
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

        #getitem is case-insensitive
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
        #setitem replaces all keys with new values
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

        #setitem leaves other items alone
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

        #setitem handles aliases automatically
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

        #setitem is case-preserving
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
        #track_number grabs the first available integer
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

        #track_number is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"tRaCkNuMbEr=10"],
                                     u"vendor").track_number,
            10)

        #album_number grabs the first available integer
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

        #album_number is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"dIsCnUmBeR=20"],
                                     u"vendor").album_number,
            20)

        #track_total grabs the first available TRACKTOTAL integer
        #before falling back on slashed fields
        self.assertEqual(
            audiotools.VorbisComment([u"TRACKTOTAL=15"],
                                     u"vendor").track_total,
            15)

        self.assertEqual(
            audiotools.VorbisComment([u"TRACKNUMBER=5/10"],
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

        #track_total is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"tracktotal=15"],
                                     u"vendor").track_total,
            15)

        #track_total supports aliases
        self.assertEqual(
            audiotools.VorbisComment([u"TOTALTRACKS=15"],
                                     u"vendor").track_total,
            15)

        #album_total grabs the first available DISCTOTAL integer
        #before falling back on slashed fields
        self.assertEqual(
            audiotools.VorbisComment([u"DISCTOTAL=25"],
                                     u"vendor").album_total,
            25)

        self.assertEqual(
            audiotools.VorbisComment([u"DISCNUMBER=10/30"],
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

        #album_total is case-insensitive
        self.assertEqual(
            audiotools.VorbisComment([u"disctotal=25"],
                                     u"vendor").album_total,
            25)

        #album_total supports aliases
        self.assertEqual(
            audiotools.VorbisComment([u"TOTALDISCS=25"],
                                     u"vendor").album_total,
            25)

        #other fields grab the first available item
        self.assertEqual(
            audiotools.VorbisComment([u"TITLE=first",
                                      u"TITLE=last"],
                                     u"vendor").track_name,
            u"first")

    @METADATA_VORBIS
    def test_setattr(self):
        #track_number adds new field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertEqual(metadata.track_number, None)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=11"])
        self.assertEqual(metadata.track_number, 11)

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=blah"],
                                            u"vendor")
        self.assertEqual(metadata.track_number, None)
        metadata.track_number = 11
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=blah",
                          u"TRACKNUMBER=11"])
        self.assertEqual(metadata.track_number, 11)

        #track_number updates the first integer field
        #and leaves other junk in that field alone
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

        #album_number adds new field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertEqual(metadata.album_number, None)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=3"])
        self.assertEqual(metadata.album_number, 3)

        metadata = audiotools.VorbisComment([u"DISCNUMBER=blah"],
                                            u"vendor")
        self.assertEqual(metadata.album_number, None)
        metadata.album_number = 3
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=blah",
                          u"DISCNUMBER=3"])
        self.assertEqual(metadata.album_number, 3)

        #album_number updates the first integer field
        #and leaves other junk in that field alone
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

        #track_total adds new TRACKTOTAL field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertEqual(metadata.track_total, None)
        metadata.track_total = 12
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=12"])
        self.assertEqual(metadata.track_total, 12)

        metadata = audiotools.VorbisComment([u"TRACKTOTAL=blah"],
                                            u"vendor")
        self.assertEqual(metadata.track_total, None)
        metadata.track_total = 12
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=blah",
                          u"TRACKTOTAL=12"])
        self.assertEqual(metadata.track_total, 12)

        #track_total updates first integer TRACKTOTAL field first if possible
        #including aliases
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

        #track_total updates slashed TRACKNUMBER field if necessary
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

        #album_total adds new DISCTOTAL field if necessary
        metadata = audiotools.VorbisComment([], u"vendor")
        self.assertEqual(metadata.album_total, None)
        metadata.album_total = 4
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        metadata = audiotools.VorbisComment([u"DISCTOTAL=blah"],
                                            u"vendor")
        self.assertEqual(metadata.album_total, None)
        metadata.album_total = 4
        self.assertEqual(metadata.comment_strings,
                         [u"DISCTOTAL=blah",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 4)

        #album_total updates DISCTOTAL field first if possible
        #including aliases
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

        #album_total updates slashed DISCNUMBER field if necessary
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

        #other fields update the first match
        #while leaving the rest alone
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

        #setting field to an empty string is okay
        metadata = audiotools.VorbisComment([], u"vendor")
        metadata.track_name = u""
        self.assertEqual(metadata.track_name, u"")
        self.assertEqual(metadata.comment_strings,
                         [u"TITLE="])

    @METADATA_VORBIS
    def test_delattr(self):
        #deleting field removes all instances of it
        metadata = audiotools.VorbisComment([u"TITLE=track name"],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [])

        metadata = audiotools.VorbisComment([u"TITLE=track name",
                                             u"ALBUM=album name"],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [u"ALBUM=album name"])

        metadata = audiotools.VorbisComment([u"TITLE=track name",
                                             u"TITLE=track name 2",
                                             u"ALBUM=album name",
                                             u"TITLE=track name 3"],
                                            u"vendor")
        del(metadata.track_name)
        self.assertEqual(metadata.comment_strings,
                         [u"ALBUM=album name"])

        #setting field to None is the same as deleting field
        metadata = audiotools.VorbisComment([u"TITLE=track name"],
                                            u"vendor")
        metadata.track_name = None
        self.assertEqual(metadata.comment_strings,
                         [])

        #deleting track_number removes TRACKNUMBER field
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1"],
                                            u"vendor")
        del(metadata.track_number)
        self.assertEqual(metadata.comment_strings,
                         [])

        #deleting slashed TRACKNUMBER converts it to fresh TRACKTOTAL field
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/3"],
                                            u"vendor")
        del(metadata.track_number)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=3"])

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/3",
                                             u"TRACKTOTAL=4"],
                                            u"vendor")
        self.assertEqual(metadata.track_total, 4)
        del(metadata.track_number)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKTOTAL=4",
                          u"TRACKTOTAL=3"])
        self.assertEqual(metadata.track_total, 4)

        #deleting track_total removes TRACKTOTAL/TOTALTRACKS fields
        metadata = audiotools.VorbisComment([u"TRACKTOTAL=3",
                                             u"TOTALTRACKS=4"],
                                            u"vendor")
        del(metadata.track_total)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertEqual(metadata.track_total, None)

        #deleting track_total also removes slashed side of TRACKNUMBER fields
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1/3"],
                                            u"vendor")
        del(metadata.track_total)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.VorbisComment([u"TRACKNUMBER=1 / foo 3 baz"],
                                            u"vendor")
        del(metadata.track_total)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER=1"])

        metadata = audiotools.VorbisComment(
            [u"TRACKNUMBER= foo 1 bar / blah 4 baz"], u"vendor")
        del(metadata.track_total)
        self.assertEqual(metadata.track_total, None)
        self.assertEqual(metadata.comment_strings,
                         [u"TRACKNUMBER= foo 1 bar"])

        #deleting album_number removes DISCNUMBER field
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2"],
                                            u"vendor")
        del(metadata.album_number)
        self.assertEqual(metadata.comment_strings,
                         [])

        #deleting slashed DISCNUMBER converts it to fresh DISCTOTAL field
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
                         [u"DISCTOTAL=5",
                          u"DISCTOTAL=4"])
        self.assertEqual(metadata.album_total, 5)

        #deleting album_total removes DISCTOTAL/TOTALDISCS fields
        metadata = audiotools.VorbisComment([u"DISCTOTAL=4",
                                             u"TOTALDISCS=5"],
                                            u"vendor")
        del(metadata.album_total)
        self.assertEqual(metadata.comment_strings,
                         [])
        self.assertEqual(metadata.album_total, None)

        #deleting album_total also removes slashed side of DISCNUMBER fields
        metadata = audiotools.VorbisComment([u"DISCNUMBER=2/4"],
                                            u"vendor")
        del(metadata.album_total)
        self.assertEqual(metadata.album_total, None)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.VorbisComment([u"DISCNUMBER=2 / foo 4 baz"],
                                            u"vendor")
        del(metadata.album_total)
        self.assertEqual(metadata.album_total, None)
        self.assertEqual(metadata.comment_strings,
                         [u"DISCNUMBER=2"])

        metadata = audiotools.VorbisComment(
            [u"DISCNUMBER= foo 2 bar / blah 4 baz"], u"vendor")
        del(metadata.album_total)
        self.assertEqual(metadata.album_total, None)
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
                self.assertEqual(metadata["TITLE"], [u"Track Name"])
                self.assertEqual(metadata["TRACKNUMBER"], [u"1"])
                self.assertEqual(metadata.track_name, u"Track Name")
                self.assertEqual(metadata.track_number, 1)

                metadata["title"] = [u"New Track Name"]
                metadata["tracknumber"] = [u"2"]
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata["TITLE"], [u"New Track Name"])
                self.assertEqual(metadata["TRACKNUMBER"], [u"2"])
                self.assertEqual(metadata.track_name, u"New Track Name")
                self.assertEqual(metadata.track_number, 2)

                metadata.track_name = "New Track Name 2"
                metadata.track_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata["TITLE"], [u"New Track Name 2"])
                self.assertEqual(metadata["TRACKNUMBER"], [u"3"])
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
        #check trailing whitespace
        metadata = audiotools.VorbisComment([u"TITLE=Foo "], u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment(["TITLE=Foo"], u"vendor"))
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        #check leading whitespace
        metadata = audiotools.VorbisComment([u"TITLE= Foo"], u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([u"TITLE=Foo"], u"vendor"))
        self.assertEqual(results,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        #check leading zeroes
        metadata = audiotools.VorbisComment([u"TRACKNUMBER=001"], u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([u"TRACKNUMBER=1"],
                                                  u"vendor"))
        self.assertEqual(results,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":u"TRACKNUMBER"}])

        #check leading space/zeroes in slashed field
        for field in [u"TRACKNUMBER=01/2",
                      u"TRACKNUMBER=1/02",
                      u"TRACKNUMBER=01/02",
                      u"TRACKNUMBER=1/ 2",
                      u"TRACKNUMBER=1/ 02"]:
            metadata = audiotools.VorbisComment([field], u"vendor")
            results = []
            cleaned = metadata.clean(results)
            self.assertEqual(cleaned,
                             audiotools.VorbisComment([u"TRACKNUMBER=1/2"],
                                                      u"vendor"))
            self.assertEqual(results,
                             [_(u"removed whitespace/zeroes from %(field)s") %
                              {"field":u"TRACKNUMBER"}])

        #check empty fields
        metadata = audiotools.VorbisComment([u"TITLE="], u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([], u"vendor"))
        self.assertEqual(results,
                         [_(u"removed empty field %(field)s") %
                          {"field":u"TITLE"}])

        metadata = audiotools.VorbisComment([u"TITLE=    "], u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment([], u"vendor"))
        self.assertEqual(results,
                         [_(u"removed empty field %(field)s") %
                          {"field":u"TITLE"}])

    @METADATA_VORBIS
    def test_aliases(self):
        for (key, map_to) in audiotools.VorbisComment.ALIASES.items():
            attr = [attr for (attr, item) in
                    audiotools.VorbisComment.ATTRIBUTE_MAP.items()
                    if item in map_to][0]

            if (attr in audiotools.VorbisComment.INTEGER_FIELDS):
                old_raw_value = u"1"
                old_attr_value = 1
                new_raw_value = u"2"
                new_attr_value = 2
            else:
                old_raw_value = old_attr_value = u"Foo"
                new_raw_value = new_attr_value = u"Bar"

            metadata = audiotools.VorbisComment([], u"")

            #ensure setting aliased field shows up in attribute
            metadata[key] = [old_raw_value]
            self.assertEqual(getattr(metadata, attr), old_attr_value)

            #ensure updating attribute reflects in aliased field
            setattr(metadata, attr, new_attr_value)
            self.assertEqual(getattr(metadata, attr), new_attr_value)
            self.assertEqual(metadata[key], [new_raw_value])

            self.assertEqual(metadata.keys(), [key])

            #ensure updating the metadata with an aliased key
            #doesn't change the aliased key field
            for new_key in map_to:
                if (new_key != key):
                    metadata[new_key] = [old_raw_value]
                    self.assertEqual(metadata.keys(), [key])

    @METADATA_VORBIS
    def test_replay_gain(self):
        import test_streams

        for input_class in [audiotools.FlacAudio,
                            audiotools.OggFlacAudio,
                            audiotools.VorbisAudio]:
            temp1 = tempfile.NamedTemporaryFile(suffix="." + input_class.SUFFIX)
            try:
                track1 = input_class.from_pcm(
                    temp1.name,
                    test_streams.Sine16_Stereo(44100, 44100,
                                               441.0, 0.50,
                                               4410.0, 0.49, 1.0))
                self.assert_(track1.replay_gain() is None,
                             "ReplayGain present for class %s" % \
                                 (input_class.NAME))
                track1.set_metadata(audiotools.MetaData(track_name=u"Foo"))
                input_class.add_replay_gain([track1.filename])
                self.assertEqual(track1.get_metadata().track_name, u"Foo")
                self.assert_(track1.replay_gain() is not None,
                             "ReplayGain not present for class %s" % \
                                 (input_class.NAME))

                for output_class in [audiotools.VorbisAudio]:
                    temp2 = tempfile.NamedTemporaryFile(
                        suffix="." + input_class.SUFFIX)
                    try:
                        track2 = output_class.from_pcm(
                            temp2.name,
                            test_streams.Sine16_Stereo(66150, 44100,
                                                       8820.0, 0.70,
                                                       4410.0, 0.29, 1.0))

                        #ensure that ReplayGain doesn't get ported
                        #via set_metadata()
                        self.assert_(track2.replay_gain() is None,
                                     "ReplayGain present for class %s" % \
                                         (output_class.NAME))
                        track2.set_metadata(track1.get_metadata())
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Foo")
                        self.assert_(track2.replay_gain() is None,
                                "ReplayGain present for class %s from %s" % \
                                         (output_class.NAME,
                                          input_class.NAME))

                        #and if ReplayGain is already set,
                        #ensure set_metadata() doesn't remove it
                        output_class.add_replay_gain([track2.filename])
                        old_replay_gain = track2.replay_gain()
                        self.assert_(old_replay_gain is not None)
                        track2.set_metadata(audiotools.MetaData(
                                track_name=u"Bar"))
                        self.assertEqual(track2.get_metadata().track_name,
                                         u"Bar")
                        self.assertEqual(track2.replay_gain(),
                                         old_replay_gain)
                    finally:
                        temp2.close()
            finally:
                temp1.close()
