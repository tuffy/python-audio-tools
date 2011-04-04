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
                self.assertEqual(self.metadata_class, metadata2.__class__)

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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
        for field in audiotools.MetaData.__FIELDS__:
            if (field in self.supported_fields):
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            elif (field in audiotools.MetaData.__INTEGER_FIELDS__):
                self.assertEqual(getattr(metadata_new, field), 0)
            else:
                self.assertEqual(getattr(metadata_new, field), u"")

        #ensure images match, if supported
        if (self.metadata_class.supports_images()):
            self.assertEqual(metadata_new.images(),
                             [image1, image2, image3])

        #subclasses should ensure non-MetaData fields are converted

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
                    self.assertEqual(metadata.images(), [image1])

                    #ensure that adding a second image works
                    metadata.add_image(image2)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(metadata.images(), [image1,
                                                         image2])

                    #ensure that adding a third image works
                    metadata.add_image(image3)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(metadata.images(), [image1,
                                                         image2,
                                                         image3])

                    #ensure that deleting the first image works
                    metadata.delete_image(image1)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(metadata.images(), [image2,
                                                         image3])

                    #ensure that deleting the second image works
                    metadata.delete_image(image2)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(metadata.images(), [image3])

                    #ensure that deleting the third image works
                    metadata.delete_image(image3)
                    track.set_metadata(metadata)
                    metadata = track.get_metadata()
                    self.assertEqual(metadata.images(), [])

                finally:
                    temp_file.close()

    @METADATA_METADATA
    def test_merge(self):
        import random

        def field_val(field, value, int_value):
            if (field in audiotools.MetaData.__INTEGER_FIELDS__):
                return int_value
            else:
                return value

        for audio_class in self.supported_formats:
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + audio_class.SUFFIX)
            try:
                track = audio_class.from_pcm(temp_file.name,
                                             BLANK_PCM_Reader(1))

                for i in xrange(10):
                    shuffled_fields = self.supported_fields[:]
                    random.shuffle(shuffled_fields)

                    for (range_a, range_b) in [
                        ((0, len(shuffled_fields) / 3), #no overlap
                         (-(len(shuffled_fields) / 3),
                           len(shuffled_fields) + 1)),

                        ((0, len(shuffled_fields) / 2), #partial overlap
                         (len(shuffled_fields) / 4,
                          len(shuffled_fields) / 4 + len(shuffled_fields) / 2)),

                        ((0, len(shuffled_fields) / 3), #complete overlap
                         (0, len(shuffled_fields) / 3))]:
                        fields_a = shuffled_fields[range_a[0]:range_a[1]]
                        fields_b = shuffled_fields[range_b[0]:range_b[1]]

                        metadata_a = audiotools.MetaData(**dict([
                                    (field, field_val(field, u"a", 1))
                                    for field in fields_a]))
                        metadata_b = audiotools.MetaData(**dict([
                                    (field, field_val(field, u"b", 2))
                                    for field in fields_b]))

                        #ensure that metadata round-trips properly
                        track.delete_metadata()
                        track.set_metadata(metadata_a)
                        metadata_c = track.get_metadata()
                        self.assertEqual(metadata_c, metadata_a)
                        metadata_c.merge(metadata_b)
                        track.set_metadata(metadata_c)
                        metadata_c = track.get_metadata()

                        #ensure that the individual fields merge properly
                        for field in self.supported_fields:
                            if (field in fields_a):
                                if (field in
                                    audiotools.MetaData.__INTEGER_FIELDS__):
                                    self.assertEqual(
                                        getattr(metadata_c, field), 1)
                                else:
                                    self.assertEqual(
                                        getattr(metadata_c, field), u"a")
                            elif (field in fields_b):
                                if (field in
                                    audiotools.MetaData.__INTEGER_FIELDS__):
                                    self.assertEqual(
                                        getattr(metadata_c, field), 2)
                                else:
                                    self.assertEqual(
                                        getattr(metadata_c, field), u"b")
                            else:
                                if (field in
                                    audiotools.MetaData.__INTEGER_FIELDS__):
                                    self.assertEqual(
                                        getattr(metadata_c, field), 0)
                                else:
                                    self.assertEqual(
                                        getattr(metadata_c, field), u"")

                #ensure that embedded images merge properly
                if (self.metadata_class.supports_images()):
                    image1 = audiotools.Image.new(TEST_COVER1, u"", 0)
                    image2 = audiotools.Image.new(TEST_COVER2, u"", 0)

                    #if metadata_a has images and metadata_b has images
                    #metadata_a.merge(metadata_b) results in
                    #only metadata_a's images remaining
                    metadata_a = self.empty_metadata()
                    metadata_b = self.empty_metadata()
                    metadata_a.add_image(image1)
                    track.set_metadata(metadata_a)
                    metadata_a = track.get_metadata()
                    metadata_b.add_image(image2)
                    metadata_a.merge(metadata_b)
                    self.assertEqual(len(metadata_a.images()), 1)
                    self.assertEqual(metadata_a.images(), [image1])
                    track.set_metadata(metadata_a)
                    metadata_a = track.get_metadata()
                    self.assertEqual(metadata_a.images(), [image1])

                    #if metadata_a has no images and metadata_b has images
                    #metadata_a.merge(metadata_b) results in
                    #only metadata_b's images remaining
                    metadata_a = self.empty_metadata()
                    metadata_b = self.empty_metadata()
                    track.set_metadata(metadata_a)
                    metadata_a = track.get_metadata()
                    metadata_b.add_image(image2)
                    metadata_a.merge(metadata_b)
                    self.assertEqual(len(metadata_a.images()), 1)
                    self.assertEqual(metadata_a.images(), [image2])
                    track.set_metadata(metadata_a)
                    metadata_a = track.get_metadata()
                    self.assertEqual(metadata_a.images(), [image2])

                    #if metadata_a has images and metadata_b has no images
                    #metadata_a.merge(metadata_b) results in
                    #only metadata_a's images remaining
                    metadata_a = self.empty_metadata()
                    metadata_b = self.empty_metadata()
                    metadata_a.add_image(image1)
                    track.set_metadata(metadata_a)
                    metadata_a = track.get_metadata()
                    metadata_a.merge(metadata_b)
                    self.assertEqual(len(metadata_a.images()), 1)
                    self.assertEqual(metadata_a.images(), [image1])
                    track.set_metadata(metadata_a)
                    metadata_a = track.get_metadata()
                    self.assertEqual(metadata_a.images(), [image1])

            finally:
                temp_file.close()


class WavPackApeTagMetaData(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.WavPackAPEv2
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
    def test_foreign_field(self):
        metadata = audiotools.WavePackAPEv2(
        [audiotools.ApeTagItem(0, False, "Title", 'Track Name'),
         audiotools.ApeTagItem(0, False, "Album", 'Album Name'),
         audiotools.ApeTagItem(0, False, "Track", "1/3"),
         audiotools.ApeTagItem(0, False, "Media", "2/4"),
         audiotools.ApeTagItem(0, False, "Foo", "Bar")])
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
                    metadata[key] = audiotools.ApeTagItem.string(
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
                self.assertRaises(KeyError,
                                  metadata.__getitem__,
                                  'Media')

                #and ensure updating the low-level implementation
                #updates the numerical fields
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata['Track'] = audiotools.ApeTagItem.string(
                        'Track', u"1")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 1)
                self.assertEqual(metadata.track_total, 0)
                metadata['Track'] = audiotools.ApeTagItem.string(
                        'Track', u"1/2")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 1)
                self.assertEqual(metadata.track_total, 2)
                metadata['Track'] = audiotools.ApeTagItem.string(
                        'Track', u"0/2")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 0)
                self.assertEqual(metadata.track_total, 2)
                del(metadata['Track'])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_number, 0)
                self.assertEqual(metadata.track_total, 0)

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata['Media'] = audiotools.ApeTagItem.string(
                        'Media', u"3")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 3)
                self.assertEqual(metadata.album_total, 0)
                metadata['Media'] = audiotools.ApeTagItem.string(
                        'Media', u"3/4")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 3)
                self.assertEqual(metadata.album_total, 4)
                metadata['Media'] = audiotools.ApeTagItem.string(
                        'Media', u"0/4")
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 0)
                self.assertEqual(metadata.album_total, 4)
                del(metadata['Media'])
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(metadata.album_number, 0)
                self.assertEqual(metadata.album_total, 0)

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
        for field in audiotools.MetaData.__FIELDS__:
            if (field in self.supported_fields):
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            elif (field in audiotools.MetaData.__INTEGER_FIELDS__):
                self.assertEqual(getattr(metadata_new, field), 0)
            else:
                self.assertEqual(getattr(metadata_new, field), u"")

        #ensure images match, if supported
        self.assertEqual(metadata_new.images(), [image1, image2])

        #ensure non-MetaData fields are converted
        metadata_orig = self.empty_metadata()
        metadata_orig['Foo'] = audiotools.ApeTagItem.string(
            'Foo', u'Bar'.encode('utf-8'))
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_orig['Foo'].data,
                         metadata_new['Foo'].data)

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
        return self.metadata_class((u"", u"", u"", u"", u"", 0))

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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
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
                    if (field not in audiotools.MetaData.__INTEGER_FIELDS__):
                        self.assertEqual(getattr(metadata, field), u"")
                    else:
                        self.assertEqual(getattr(metadata, field), 0)

            finally:
                temp_file.close()

    @METADATA_ID3V1
    def test_field_mapping(self):
        mapping = [('track_name', 0, u'a'),
                   ('artist_name', 1, u'b'),
                   ('album_name', 2, u'c'),
                   ('year', 3, u'1234'),
                   ('comment', 4, u'd'),
                   ('track_number', 5, 1)]

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
                    metadata[key] = value
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key]), unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key]), unicode(value))
            finally:
                temp_file.close()

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
    def test_foreign_field(self):
        metadata = audiotools.ID3v22Comment(
            [audiotools.ID3v22TextFrame("TT2", 0, "Track Name"),
             audiotools.ID3v22TextFrame("TAL", 0, "Album Name"),
             audiotools.ID3v22TextFrame("TRK", 0, "1/3"),
             audiotools.ID3v22TextFrame("TPA", 0, "2/4"),
             audiotools.ID3v22TextFrame("TFO", 0, "Bar")])
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
                self.assertEqual(metadata["TFO"][0].string, "Bar")
            finally:
                temp_file.close()

    @METADATA_ID3V2
    def test_field_mapping(self):
        id3_class = self.metadata_class

        INTEGER_ATTRIBS = ('track_number',
                           'track_total',
                           'album_number',
                           'album_total')

        attribs1 = {}  # a dict of attribute -> value pairs ("track_name":u"foo")
        attribs2 = {}  # a dict of ID3v2 -> value pairs     ("TT2":u"foo")
        for (i, (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
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
        self.assertEqual(int(id3[id3_class.INTEGER_ITEMS[0]][0]),
                         attribs1["track_number"])
        self.assertEqual(id3[id3_class.INTEGER_ITEMS[0]][0].total(),
                         attribs1["track_total"])
        self.assertEqual(int(id3[id3_class.INTEGER_ITEMS[1]][0]),
                         attribs1["album_number"])
        self.assertEqual(id3[id3_class.INTEGER_ITEMS[1]][0].total(),
                         attribs1["album_total"])

        #ensure that changing attributes changes the underlying frame
        #>>> id3.track_name = u"bar"
        #>>> id3['TT2'][0] == u"bar"
        for (i, (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                setattr(id3, attribute, u"new value %d" % (i))
                self.assertEqual(unicode(id3[key][0]), u"new value %d" % (i))

        #ensure that changing integer attributes changes the underlying frame
        #>>> id3.track_number = 2
        #>>> id3['TRK'][0] == u"2"
        id3.track_number = 3
        id3.track_total = 0
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[0]][0]), u"3")

        id3.track_total = 8
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[0]][0]), u"3/8")

        id3.album_number = 2
        id3.album_total = 0
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[1]][0]), u"2")

        id3.album_total = 4
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[1]][0]), u"2/4")

        #reset and re-check everything for the next round
        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        #ensure that all the attributes match up
        for (attribute, value) in attribs1.items():
            self.assertEqual(getattr(id3, attribute), value)

        for (key, value) in attribs2.items():
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(unicode(id3[key][0]), value)
            else:
                self.assertEqual(int(id3[key][0]), value)

        #ensure that changing the underlying frames changes attributes
        #>>> id3['TT2'] = [u"bar"]
        #>>> id3.track_name == u"bar"
        for (i, (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                id3[key] = [u"new value %d" % (i)]
                self.assertEqual(getattr(id3, attribute),
                                 u"new value %d" % (i))

        #ensure that changing the underlying integer frames changes attributes
        id3[id3_class.INTEGER_ITEMS[0]] = [7]
        self.assertEqual(id3.track_number, 7)

        id3[id3_class.INTEGER_ITEMS[0]] = [u"8/9"]
        self.assertEqual(id3.track_number, 8)
        self.assertEqual(id3.track_total, 9)

        id3[id3_class.INTEGER_ITEMS[1]] = [4]
        self.assertEqual(id3.album_number, 4)

        id3[id3_class.INTEGER_ITEMS[1]] = [u"5/6"]
        self.assertEqual(id3.album_number, 5)
        self.assertEqual(id3.album_total, 6)

        #finally, just for kicks, ensure that explicitly setting
        #frames also changes attributes
        #>>> id3['TT2'] = [id3_class.TextFrame.from_unicode('TT2',u"foo")]
        #>>> id3.track_name = u"foo"
        for (i, (attribute, key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                id3[key] = [id3_class.TextFrame.from_unicode(key, unicode(i))]
                self.assertEqual(getattr(id3, attribute), unicode(i))

        #and ensure explicitly setting integer frames also changes attribs
        id3[id3_class.INTEGER_ITEMS[0]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[0],
                                             u"4")]
        self.assertEqual(id3.track_number, 4)
        self.assertEqual(id3.track_total, 0)

        id3[id3_class.INTEGER_ITEMS[0]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[0],
                                             u"2/10")]
        self.assertEqual(id3.track_number, 2)
        self.assertEqual(id3.track_total, 10)

        id3[id3_class.INTEGER_ITEMS[1]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[1],
                                             u"3")]
        self.assertEqual(id3.album_number, 3)
        self.assertEqual(id3.album_total, 0)

        id3[id3_class.INTEGER_ITEMS[1]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[1],
                                             u"5/7")]
        self.assertEqual(id3.album_number, 5)
        self.assertEqual(id3.album_total, 7)



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
            [audiotools.ID3v23TextFrame("TIT2", 0, "Track Name"),
             audiotools.ID3v23TextFrame("TALB", 0, "Album Name"),
             audiotools.ID3v23TextFrame("TRCK", 0, "1/3"),
             audiotools.ID3v23TextFrame("TPOS", 0, "2/4"),
             audiotools.ID3v23TextFrame("TFOO", 0, "Bar")])
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
                self.assertEqual(metadata["TFOO"][0].string, "Bar")
            finally:
                temp_file.close()

    def empty_metadata(self):
        return self.metadata_class([])

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
    def test_foreign_field(self):
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=4,
                    data=audiotools.FlacVorbisComment(
                        {"TITLE": [u'Track Name'],
                         "ALBUM": [u'Album Name'],
                         "TRACKNUMBER": [u"1"],
                         "TRACKTOTAL": [u"3"],
                         "DISCNUMBER": [u"2"],
                         "DISCTOTAL": [u"4"],
                         "FOO": [u"Bar"]}).build())])
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
                self.assertEqual(track.get_metadata().vorbis_comment["FOO"],
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
                        metadata.vorbis_comment[key][0],
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2.vorbis_comment[key][0],
                        unicode(value))

                #ensure that updating the low-level implementation
                #is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata.vorbis_comment[key] = [unicode(value)]
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(
                        metadata.vorbis_comment[key][0],
                        unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(
                        metadata2.vorbis_comment[key][0],
                        unicode(value))
            finally:
                temp_file.close()

    @METADATA_FLAC
    def test_converted(self):
        MetaDataTest.test_converted(self)

        metadata_orig = self.empty_metadata()
        metadata_orig.vorbis_comment['FOO'] = [u'bar']

        self.assertEqual(metadata_orig.vorbis_comment['FOO'], [u'bar'])

        metadata_new = self.metadata_class.converted(metadata_orig)

        self.assertEqual(metadata_orig.vorbis_comment['FOO'],
                         metadata_new.vorbis_comment['FOO'])

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

                #check that merging metadata with an oversized field
                #fails properly
                metadata = self.empty_metadata()
                metadata.merge(audiotools.MetaData(track_name=oversized_text))
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertNotEqual(metadata.track_name, oversized_text)

                #check that merging metadata with an oversized image
                #fails properly
            finally:
                temp_file.close()

    @METADATA_FLAC
    def test_totals(self):
        metadata = self.empty_metadata()
        metadata.vorbis_comment["TRACKNUMBER"] = [u"2/4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata.vorbis_comment["DISCNUMBER"] = [u"1/3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

    @METADATA_FLAC
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=4,
                    data=audiotools.FlacVorbisComment(
                        {"TITLE": [u'Foo ']}).build())])
        self.assertEqual(metadata.track_name, u'Foo ')
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        #check leading whitespace
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=4,
                    data=audiotools.FlacVorbisComment(
                        {"TITLE": [u' Foo']}).build())])
        self.assertEqual(metadata.track_name, u' Foo')
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned.track_name, u'Foo')
        self.assertEqual(results,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        #check leading zeroes
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=4,
                    data=audiotools.FlacVorbisComment(
                        {"TRACKNUMBER": [u'01']}).build())])
        self.assertEqual(metadata.vorbis_comment["TRACKNUMBER"],[u"01"])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned.vorbis_comment["TRACKNUMBER"],[u"1"])
        self.assertEqual(results,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":u"TRACKNUMBER"}])

        #check empty fields
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=4,
                    data=audiotools.FlacVorbisComment(
                        {"TITLE": [u'  ']}).build())])
        self.assertEqual(metadata.vorbis_comment["TITLE"], [u'  '])
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.FlacMetaData([
                    audiotools.FlacMetaDataBlock(
                        type=4,
                        data=audiotools.FlacVorbisComment(
                            {}).build())]))
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TITLE"},
                          _(u"removed empty field %(field)s") %
                          {"field":u"TITLE"}])

        #check mis-tagged images
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=6,
                    data=audiotools.FlacPictureComment(
                        0, "image/jpeg", u"", 20, 20, 24, 10,
"""iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKAQMAAAC3/F3+AAAAAXNSR0IArs4c6QAAAANQTFRF////
p8QbyAAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9sEBBMWM3PnvjMAAAALSURBVAjXY2DA
BwAAHgABboVHMgAAAABJRU5ErkJggg==""".decode('base64')).build())])
        self.assertEqual(len(metadata.image_blocks), 1)
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
        self.assertEqual(len(cleaned.image_blocks), 1)
        image = cleaned.images()[0]
        self.assertEqual(image.mime_type, "image/png")
        self.assertEqual(image.width, 10)
        self.assertEqual(image.height, 10)
        self.assertEqual(image.color_depth, 8)
        self.assertEqual(image.color_count, 1)


        #check that cleanup doesn't disturb other metadata blocks
        metadata = audiotools.FlacMetaData([
                audiotools.FlacMetaDataBlock(
                    type=0,
                    data='\x10\x00\x10\x00\x00\x00\x0e\x009?\n\xc4B\xf0\x07\xf4u4\xc0Z\xaf\xf6\xaa\xfd\x00M\xa2h2\xd8\x83w\xab\xec'),
                audiotools.FlacMetaDataBlock(
                    type=4,
                    data=audiotools.FlacVorbisComment(
                        {"TITLE": [u'Foo ']}).build()),
                audiotools.FlacMetaDataBlock(
                    type=3,
                    data=\
"""eJxd2HtYVHUex/GZObe5zzCwCmjL4IWLBmrCegENMUXKBbyBa9CSYosiu2qGZMslFU3BMnQL1F1H
SzFFzFUwERWwEnQFerxgCisGliIqmi6at56nz+f8s/7z83k9XOY93zm/8zsImt/FaP7vnx2L/CVW
t8ZuimUh1gHtr1A8nFhHauwU7zaskxf0UHxdWN/sdZ8SEIc1w6uYMoRrgUcd/xfahHW7/yBKeC7W
r6IbKeMjsDakv0B5lQkda8opcaz4ZXsQJQEVWvuZAZQ3hkL8vU5RUlChHdM3nJKGCu20uAuUxcmQ
1CtvUd7Fqs0uaqPkoEK7sXARZdV6yO6exZR1qNBWX1tF2YhF2+xop2yqhtyK8aBsQ4VOCNZRdqFC
5zVuNaWsGxIcOplSjgpd5IoSShUqdAmpmZQTTkh6dhilHhW6FVPUd7UJFbribeosmjFT3b5Ctf2/
WHQ1u0opHajQnTowkXIzF9JacZZyjxX3/N6mPESFoBxWf/tzzFToc+effMdlVAhDaj6gWFAhTJhx
lOLeBpnZaKR4o0JIn/sOxRcVwvJTtykBWIWiUfMowagQSqeIlFBUCLXL71HCIyAXz/Lzo41kRZc3
P3XaaFY8bVEocZipaP/XNEoCKsSB6vWlTUKFODpvDCXFBYnV1VPSUCHOzuEVp+VnTcy0DqVkYqZi
/jcSJQcVoiv8Z8oqVIjlWR9T1mkgpwdEUjagQrzSZxdlEyse+P+Hsg0zlUxZKZQSVEg+gQsoZaiQ
Avb0p5QnQ8L7vESpwipN9Yim1KJCSh27llKPmUrZ17SUJlRIGx/zKtA2o0LaM2QDpbUaUjOb89Z2
oEJqXsrPofYmK24dvEq5i5nKQseLlIeokL2jtlCeo0Ie+tMPEJ3shETF96OYUSEnbThPcUeFvGTw
FYo3ZiqvncZZ6nxRIbui+W7o/FEhV9weTQnOhZwZdYsSigq5PSSDEsaKR389RonETBXboQ8p0ahQ
BlZGUeJQoYR1jaLEt0GmLlNLk1ChpHb9SElBhZKTwFno0rAq/2iIpyxChVI61J+SiQrl+O4mSk4E
5FRAHCUPFUprUyelgBXd7dyXdRswU72ofjJ1m1Ch9wz5H8WFCn3Qd3+mlLggkXvyKGWo0Cfk6ync
mfTpE7mH645gpvrld5MotajQFyWr06lHhb4saz0F36TRf/3ZPsoFVOgvrf+c0sqKOy0HKB2YqUHI
tlA6UWHw9FTfw7uoMASNfUR5mAyJXD2C8hyrIeGTHdz1JLwgw/z3CihmzNSQ1fERxR0VhsJgVgje
qDCUHFC/xlkNqVqeQ/FHheG73MOUYFb8NDKCEoKZGp508h0TwlBhdMyspUSiwhiwUpVoJ2RsaTAl
FhXG6VvUr4lHhTH1R953hCTM1LhozVJKCiqMef250wrzUWEsvs5rR1iUC9ln4fUuZKLCeKKLu7qQ
jQrjxZC/UfIwU+PNE9zVhQJWPE/8lLIBFSb3DN5hheI2iH9lF8WFClNYNfdwoQQVpri+ZyhlWE1z
1/CKEw6iwrTsNM8twhFUmNaH8DoVaiMgO9ZdpNShwlS5cy6lERWmxgcVlAuYqanj6F8orax4pF47
QjsqzNaGIkqnC9Jv7hLKXVSYQ8/zniI8xGqObh9OeYaZmpN6/gARJVSYFztqKGZUmFdN511PdNdA
NptnU7xQYf4yYQrFiQrzN7WbKP6Yqfmyj4kSxIruWJ6axBBUWKQM7gViWDLE8w7vFyLvmZbfD9tM
mYQKS/99PLeIsZipJbCJnwQxHhWW4HM8LYtJqLCEDu9FmVMNCcvleyjOR4UlUu+gLEKFJdqTdytx
KWZqib3xlJLNivh5qZQ8ViSF80QkFjghKR6xlEJWpL39gFLMisXf8roQXZipZZmFe4tYwor3S96j
7GXFWo/dlIO5kMJ7n1GOsGLT5juUGlZs+8KPUoeZWkpOj6c0sqKsH09W4gVWHNyvvj8tbZDKWdwT
xHZWHOvF5x2xkxWnO7jTinc508uP+Zwi9rCi64WvKc9Y8fDcWIgkRfy2WqVhb1BMqLA6JvEEIjlQ
YXU+4DUoeWGm1iGD/khxosI6ZifvjJIfKqyT3xlJCXJBXt/MUikEFda0EVYKT/rWZac4d2kcZmr9
4N+vUyahwlrkyScgKZYVu16+TInXQA6rZzYpkRX1Fp75pTms+P4472jSfMzU2hnFvU5ayIr7Wn6i
pKWs6HksULKTIU+LeCaRuMfYhN48s0n5qLAZyvlUIhVipjbbpV8oxaiw9VoynYJfpbH1LThJ2VkN
6f/+t5S9qLAFPj1COYgK21B/taISM7WNCPoTpQY/2jb2lYGUOlTYxjdeozQ6IdFVXpTzrIh5xGcQ
qYUV8cNtlHbM1JY0iru61MmKOT2+lG5WpPmoP7knF7K4nleT9IwVmVF9IbLIiqxDLRQTZmpbcYWn
U9nBirVHuavLXqwoHMaTg+zTBin25V1P9mOFazCvbjmIFTu6QikhnOmeUvW3j2bFvgWDKeNYUTGQ
90F5UgTkeMZNSgwr6lbx7xvyDFacDeB5VU7kTFt387Qsz2HF9XRe5/I8Vtxrfo2y0AV5sptPE/JS
VNhlT/XdyMZqtyTOp6zETO29MvjUJuejwu5M4BlSLkSF3e/v/PTKxRpI4EQ+78hbUWF/KZ5zl3ei
wh5Wxd1P3ouZ2ifEqN91ABX2mNtbKZWosM/8Sn3NNcmQ2XsaKPzbjH1BIu+VcgMr3h3Ov67I5zFT
+5pc9btaWPFJ/veUdlZ83sKnY/lGNaTCwKtJ7mbFyTd5ypV7WHGxmacB+Slmau+s4n1ZEVnx+BKf
YRUTKtxMs3gOVxxOiPc53nMVT1S4vbh/I8UHFW4vh/am+GGmblM9uY8pQahwm+vDK0UZjgq3zAnn
KKNzIWvu8z6ojEOFW1HmXkoUKtxKkjkdJQYzdTvUob6eGayo28z3R0lkxbkP+VlVZrdBribypKfM
Y8Xtji8oC1nxJOVVCk+7DuMh7lFKFiocXm/xHKWsRIUj8BjPWkp+BGTUFt4ZlY9R4Yiu4N/9lCJU
OGZ18a6nbMVMHemaQMpOVDiy98+glKLCsT6JV65ywAXZfp3PMkolKhzlvn0ofKWOkx/x6UY5iZk6
LoxQX3MDK67O5NOfcp4VPy/kfVBp+W3RuMsWb8oPqHDvfZL7mHIDFe6DJN6plW7M1D185Gq75lfx
eQSm""".decode('base64').decode('zlib')),
                audiotools.FlacMetaDataBlock(
                    type=5,
                    data=\
"""eJxjZWCxYBgMgDGio2Gg3TDwgAfGYMSthhGD8UCkhAm3ekwpxrkFML2MaztmMJOpl6lqFQ8LmXqZ
o2tVWMnUy2JXeYKNFL1MC/7A9T4+uYWdFL0MLi9geln76304SNGL5GY22dsXOMnV+/y7BReZetkd
QyS4SdHL9PUHXO+XUpNVuPUyAABOeh/F""".decode('base64').decode('zlib')),
                audiotools.FlacMetaDataBlock(
                    type=6,
                    data=\
"""AAAAAwAAAAlpbWFnZS9wbmcAAAAAAAAACgAAAAoAAAAIAAAAAQAAAIiJUE5HDQoaCgAAAA1JSERS
AAAACgAAAAoBAwAAALf8Xf4AAAABc1JHQgCuzhzpAAAAA1BMVEX///+nxBvIAAAACXBIWXMAAAsT
AAALEwEAmpwYAAAAB3RJTUUH2wQEExYzc+e+MwAAAAtJREFUCNdjYMAHAAAeAAFuhUcyAAAAAElF
TkSuQmCC""".decode('base64')),
                audiotools.FlacMetaDataBlock(
                    type=2,
                    data="FOOZKELP")])

        self.assert_(metadata.streaminfo is not None)
        self.assert_(metadata.vorbis_comment is not None)
        self.assert_(metadata.seektable is not None)
        self.assert_(metadata.cuesheet is not None)
        self.assertEqual(len(metadata.image_blocks), 1)
        self.assertEqual(len(metadata.extra_blocks), 1)

        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TITLE"}])

        self.assertEqual(cleaned.streaminfo, metadata.streaminfo)
        self.assertEqual(cleaned.seektable, metadata.seektable)
        self.assertEqual(cleaned.cuesheet, metadata.cuesheet)
        self.assertEqual(cleaned.image_blocks, metadata.image_blocks)
        self.assertEqual(cleaned.extra_blocks, metadata.extra_blocks)


class M4AMetaDataTest(MetaDataTest):
    def setUp(self):
        self.metadata_class = audiotools.M4AMetaData
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
    def test_foreign_field(self):
        metadata = audiotools.M4AMetaData([])
        metadata["\xa9nam"] = audiotools.M4AMetaData.text_atom(
            "\xa9nam", u'Track Name')
        metadata["\xa9alb"] = audiotools.M4AMetaData.text_atom(
            "\xa9alb", u'Album Name')
        metadata["trkn"] = audiotools.M4AMetaData.trkn_atom(
            1, 3)
        metadata["disk"] = audiotools.M4AMetaData.disk_atom(
            2, 4)
        metadata["\xa9foo"] = audiotools.M4AMetaData.text_atom(
            "\xa9foo", u'Bar')
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
                self.assertEqual(unicode(track.get_metadata()["\xa9foo"][0]),
                                 u"Bar")
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
                    self.assertEqual(unicode(metadata[key][0]),
                                     unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata2, field), value)
                    self.assertEqual(unicode(metadata2[key][0]),
                                     unicode(value))

                #ensure that updating the low-level implementation
                #is reflected in the class field
                for (field, key, value) in mapping:
                    track.delete_metadata()
                    metadata = self.empty_metadata()
                    metadata[key] = audiotools.M4AMetaData.text_atom(
                        key, unicode(value))
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key][0]),
                                     unicode(value))
                    track.set_metadata(metadata)
                    metadata2 = track.get_metadata()
                    self.assertEqual(getattr(metadata, field), value)
                    self.assertEqual(unicode(metadata[key][0]),
                                     unicode(value))

                #ensure that setting numerical fields also
                #updates the low-level implementation
                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.track_number = 1
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['trkn'][0]),
                                 u'1')
                metadata.track_total = 2
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['trkn'][0]),
                                 u'1/2')
                del(metadata.track_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['trkn'][0]),
                                 u'0/2')
                del(metadata.track_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata.__getitem__,
                                  'trkn')

                track.delete_metadata()
                metadata = self.empty_metadata()
                metadata.album_number = 3
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['disk'][0]),
                                 u'3')
                metadata.album_total = 4
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['disk'][0]),
                                 u'3/4')
                del(metadata.album_number)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertEqual(unicode(metadata['disk'][0]),
                                 u'0/4')
                del(metadata.album_total)
                track.set_metadata(metadata)
                metadata = track.get_metadata()
                self.assertRaises(KeyError,
                                  metadata.__getitem__,
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
        for field in audiotools.MetaData.__FIELDS__:
            if (field in self.supported_fields):
                self.assertEqual(getattr(metadata_orig, field),
                                 getattr(metadata_new, field))
            elif (field in audiotools.MetaData.__INTEGER_FIELDS__):
                self.assertEqual(getattr(metadata_new, field), 0)
            else:
                self.assertEqual(getattr(metadata_new, field), u"")

        #ensure images match, if supported
        if (self.metadata_class.supports_images()):
            self.assertEqual(metadata_new.images(), [image1])

        #check non-MetaData fields
        metadata_orig = self.empty_metadata()
        metadata_orig['test'] = audiotools.M4AMetaData.binary_atom(
            'test', "foobar")
        self.assertEqual(metadata_orig['test'][0].data[0].data, "foobar")
        metadata_new = self.metadata_class.converted(metadata_orig)
        self.assertEqual(metadata_new['test'][0].data[0].data, "foobar")


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
        self.supported_formats = [audiotools.VorbisAudio,
                                  audiotools.SpeexAudio]

    def empty_metadata(self):
        return self.metadata_class.converted(audiotools.MetaData())

    @METADATA_VORBIS
    def test_foreign_field(self):
        metadata = audiotools.VorbisComment(
            {"TITLE": [u'Track Name'],
             "ALBUM": [u'Album Name'],
             "TRACKNUMBER": [u"1"],
             "TRACKTOTAL": [u"3"],
             "DISCNUMBER": [u"2"],
             "DISCTOTAL": [u"4"],
             "FOO": [u"Bar"]})
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
                self.assertEqual(metadata2["FOO"], [u"Bar"])
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
                        {"title": [u"track name"],
                         "tracknumber": [u"1"],
                         "tracktotal": [u"3"],
                         "album": [u"album name"],
                         "artist": [u"artist name"],
                         "performer": [u"performer name"],
                         "composer": [u"composer name"],
                         "conductor": [u"conductor name"],
                         "source medium": [u"media"],
                         "isrc": [u"isrc"],
                         "catalog": [u"catalog"],
                         "copyright": [u"copyright"],
                         "publisher": [u"publisher"],
                         "date": [u"2009"],
                         "discnumber": [u"2"],
                         "disctotal": [u"4"],
                         "comment": [u"some comment"]},
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
        metadata["TRACKNUMBER"] = [u"2/4"]
        self.assertEqual(metadata.track_number, 2)
        self.assertEqual(metadata.track_total, 4)

        metadata = self.empty_metadata()
        metadata["DISCNUMBER"] = [u"1/3"]
        self.assertEqual(metadata.album_number, 1)
        self.assertEqual(metadata.album_total, 3)

    @METADATA_VORBIS
    def test_clean(self):
        #check trailing whitespace
        metadata = audiotools.VorbisComment({"TAG":[u"Foo "]},
                                            u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment({"TAG":[u"Foo"]},
                                                  u"vendor"))
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TAG"}])

        #check leading whitespace
        metadata = audiotools.VorbisComment({"TAG":[u" Foo"]},
                                            u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment({"TAG":[u"Foo"]},
                                                  u"vendor"))
        self.assertEqual(results,
                         [_(u"removed leading whitespace from %(field)s") %
                          {"field":u"TAG"}])

        #check leading zeroes
        metadata = audiotools.VorbisComment({"TRACKNUMBER":[u"001"]},
                                            u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment({"TRACKNUMBER":[u"1"]},
                                                  u"vendor"))
        self.assertEqual(results,
                         [_(u"removed leading zeroes from %(field)s") %
                          {"field":u"TRACKNUMBER"}])

        #check empty fields
        metadata = audiotools.VorbisComment({"TAG":[u""]},
                                            u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment({}, u"vendor"))
        self.assertEqual(results,
                         [_(u"removed empty field %(field)s") %
                          {"field":u"TAG"}])

        metadata = audiotools.VorbisComment({"TAG":[u"    "]},
                                            u"vendor")
        results = []
        cleaned = metadata.clean(results)
        self.assertEqual(cleaned,
                         audiotools.VorbisComment({}, u"vendor"))
        self.assertEqual(results,
                         [_(u"removed trailing whitespace from %(field)s") %
                          {"field":u"TAG"},
                          _(u"removed empty field %(field)s") %
                          {"field":u"TAG"}])
