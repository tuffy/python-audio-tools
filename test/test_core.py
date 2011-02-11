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
import random
import tempfile
import decimal
from hashlib import md5

from test_reorg import (parser, Variable_Reader, BLANK_PCM_Reader,
                        EXACT_BLANK_PCM_Reader, SHORT_PCM_COMBINATIONS,
                        MiniFrameReader, Combinations,
                        TEST_COVER1, TEST_COVER2, TEST_COVER3, HUGE_BMP)

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


class BufferedPCMReader(unittest.TestCase):
    @LIB_CORE
    def test_pcm(self):
        def frame_lengths(reader, bytes):
            frame = reader.read(bytes)
            while (len(frame) > 0):
                yield frame.frames
                frame = reader.read(bytes)
            else:
                reader.close()

        #ensure our reader is generating randomly-sized frames
        reader = Variable_Reader(EXACT_BLANK_PCM_Reader(4096 * 100))
        self.assert_(len(set(frame_lengths(reader, 4096))) > 1)

        #then, ensure that wrapped our reader in a BufferedPCMReader
        #results in equal-sized frames
        reader = audiotools.BufferedPCMReader(
            Variable_Reader(EXACT_BLANK_PCM_Reader(4096 * 100)))
        #(make sure to account for bps/channels in frame_lengths())
        self.assertEqual(set(frame_lengths(reader, 4096 * 4)), set([4096]))

        #check that sample_rate, bits_per_sample, channel_mask and channels
        #pass-through properly
        for sample_rate in [32000, 44100, 48000, 192000]:
            for bits_per_sample in [8, 16, 24]:
                for (channels, channel_mask) in [(1, 0x4),
                                                 (2, 0x3),
                                                 (4, 0x33),
                                                 (6, 0x3F)]:
                    reader = BLANK_PCM_Reader(1,
                                              sample_rate=sample_rate,
                                              channels=channels,
                                              bits_per_sample=bits_per_sample,
                                              channel_mask=channel_mask)
                    reader2 = audiotools.BufferedPCMReader(reader)
                    self.assertEqual(reader.sample_rate, sample_rate)
                    self.assertEqual(reader.channels, channels)
                    self.assertEqual(reader.bits_per_sample, bits_per_sample)
                    self.assertEqual(reader.channel_mask, channel_mask)

                    self.assertEqual(reader2.sample_rate, sample_rate)
                    self.assertEqual(reader2.channels, channels)
                    self.assertEqual(reader2.bits_per_sample, bits_per_sample)
                    self.assertEqual(reader2.channel_mask, channel_mask)


        #finally, ensure that random-sized reads also work okay
        total_frames = 4096 * 1000
        reader = audiotools.BufferedPCMReader(
            Variable_Reader(EXACT_BLANK_PCM_Reader(total_frames)))
        while (total_frames > 0):
            frames = min(total_frames, random.choice(range(1, 1000)))
            frame = reader.read(frames * 4)
            self.assertEqual(frame.frames, frames)
            total_frames -= frame.frames


class ImageJPEG(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.image = """/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYF
BgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoK
CgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAAVAAwDAREA
AhEBAxEB/8QAGAAAAgMAAAAAAAAAAAAAAAAAAAgGBwn/xAAfEAACAgMAAwEBAAAAAAAAAAACAwQG
AQUHCBITABn/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwD
AQACEQMRAD8A1/qnmzp6JO6PSvLudoqjZKDsZE6HB1TZEllhrLpABrNnCiYApEhrTcuAUZAuPM8M
pXgsuQJhaPDbB1q18n0tn7pQIdUtOxjFJ2lZhbIZmNV7sIlRWPDOVtetWVg0lESvqLPmZh6mQLNd
eO/02mVjy4qMeLpYXONsnb+Pe131ehvCws+2vm53hPE2SB1c1aMw1RvVJemSn5Brh1jIQNJyq32q
90ODZrvzPZU/bOJy9hXdrLjyGxWKcas5FsZhrao/T6LPGcESmBkwWeSWISH8B+D/2Q==""".decode('base64')
        self.md5sum = "f8c43ff52c53aff1625979de47a04cec"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/jpeg"

    @LIB_CORE
    def tearDown(self):
        pass

    @LIB_CORE
    def test_checksum(self):
        self.assertEqual(md5(self.image).hexdigest(), self.md5sum)

    @LIB_CORE
    def test_image(self):
        img = audiotools.Image.new(self.image, u"Description", 1)
        self.assertEqual(img.data, self.image)
        self.assertEqual(img.mime_type, self.mime_type)
        self.assertEqual(img.width, self.width)
        self.assertEqual(img.height, self.height)
        self.assertEqual(img.color_depth, self.bpp)
        self.assertEqual(img.color_count, self.colors)
        self.assertEqual(img.description, u"Description")
        self.assertEqual(img.type, 1)


class ImagePNG(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = """iVBORw0KGgoAAAANSUhEUgAAAAwAAAAVCAIAAAD9zpjjAAAAAXNSR0IArs4c6QAAAAlwSFlzAAAL
EwAACxMBAJqcGAAAAAd0SU1FB9kGBQA7LTgWUZgAAAAIdEVYdENvbW1lbnQA9syWvwAAANFJREFU
KM+9UrERgzAMfCUddy4pvIZZQPTsQOkBGAAxBgMwBBUTqGMHZqBSCuc4cO6SFLmokuT3698ymRk+
xQ1fxHegdV3btn092LZtHMdnse97WZYxRrtG13VN06QcZqaqIYQMBODIKdXDMADo+z7RE9HF9QFn
ZmY2sxCCqp5ZLzeIiJkBLMtycZFJKYpimqasmTOZWS7o/JhVVakqABFJPvJxInLmF5FzB2YWY3TO
ZTpExHuf8jsROefmec7Wwsx1XXvvAVCa+H7B9Of/9DPQAzSV43jVGYrtAAAAAElFTkSuQmCC""".decode('base64')
        self.md5sum = "31c4c5224327d5869aa6059bcda84d2e"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/png"


class ImageCover1(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = TEST_COVER1
        self.md5sum = "dbb6a01eca6336381754346de71e052e"
        self.width = 500
        self.height = 500
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/jpeg"


class ImageCover2(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = TEST_COVER2
        self.md5sum = "2d348cf729c840893d672dd69476955c"
        self.width = 500
        self.height = 500
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/png"


class ImageCover3(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = TEST_COVER3
        self.md5sum = "534b107e88d3830eac7ce814fc5d0279"
        self.width = 100
        self.height = 100
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/jpeg"


class ImageGIF(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = """R0lGODdhDAAVAIQSAAAAAAoKCg0NDRUVFRkZGTIyMkBAQExMTF5eXmdnZ3Nzc4CAgJiYmKWlpc3N
zdPT0+bm5vn5+f///////////////////////////////////////////////////////ywAAAAA
DAAVAAAFPKAkjmRpnuiDmBAjRkNSKsfoFCVQLsuomwaDpOBAAYIoUaCR1P1MRAnP1BtNRwnBjiC6
loqSZ3JMLpvNIQA7""".decode('base64')
        self.md5sum = "1d4d36801b53c41d01086cbf9d0cb471"
        self.width = 12
        self.height = 21
        self.bpp = 8
        self.colors = 32
        self.mime_type = "image/gif"


class ImageBMP(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = """Qk0qAwAAAAAAADYAAAAoAAAADAAAABUAAAABABgAAAAAAPQCAAATCwAAEwsAAAAAAAAAAAAA////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////AAAA////////////////////////////////////////////gICAgICA////////////
////////////////zc3N////////////Z2dnDQ0N////////////////////gICAGRkZ////////
////////gICA////////////////gICAgICA////////////////////////MjIyzc3N////gICA
gICA////////////////////////////////AAAA////AAAA////////////////////////////
////////////CgoKpaWl////////////////////////////////////AAAAQEBAQEBA////////
////////////////////////QEBAQEBA////MjIyzc3N////////////////////////gICAgICA
////////////AAAA////////////////////zc3NMjIy////////////////////AAAA////////
////+fn5FRUVZ2dn////////////////////c3NzTExM////////09PTXl5e////////////////
////////5ubmmJiY////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////""".decode('base64')
        self.md5sum = "cb6ef2f7a458ab1d315c329f72ec9898"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/x-ms-bmp"


class ImageTIFF(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = """SUkqAPwCAAD/////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
///T09NeXl7////////////////////////m5uaYmJj////////5+fkVFRVnZ2f/////////////
//////9zc3NMTEz////////////Nzc0yMjL///////////////////8AAAD/////////////////
//+AgICAgID///////////8AAAD///////////////////////////9AQEBAQED///8yMjLNzc3/
//////////////////////////////8AAABAQEBAQED/////////////////////////////////
//////8KCgqlpaX///////////////////////////////////8AAAD///8AAAD/////////////
//////////////////8yMjLNzc3///+AgICAgID///////////////////////+AgID/////////
//////+AgICAgID///////////////9nZ2cNDQ3///////////////////+AgIAZGRn///////+A
gICAgID////////////////////////////Nzc3///////8AAAD/////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
//////////////////////////////8QAP4ABAABAAAAAAAAAAABAwABAAAADAAAAAEBAwABAAAA
FQAAAAIBAwADAAAAwgMAAAMBAwABAAAAAQAAAAYBAwABAAAAAgAAAA0BAgAzAAAAyAMAABEBBAAB
AAAACAAAABIBAwABAAAAAQAAABUBAwABAAAAAwAAABYBAwABAAAAQAAAABcBBAABAAAA9AIAABoB
BQABAAAA/AMAABsBBQABAAAABAQAABwBAwABAAAAAQAAACgBAwABAAAAAgAAAAAAAAAIAAgACAAv
aG9tZS9icmlhbi9EZXZlbG9wbWVudC9hdWRpb3Rvb2xzL3Rlc3QvaW1hZ2UudGlmZgAAAAAASAAA
AAEAAABIAAAAAQ==""".decode('base64')
        self.md5sum = "192ceb086d217421a5f151cc0afa3f05"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/tiff"


class ImageHugeBMP(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        self.image = HUGE_BMP.decode('bz2')
        self.md5sum = "558d875195829de829059fd4952fed46"
        self.width = 2366
        self.height = 2366
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/x-ms-bmp"


class PCMConverter(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.tempwav = tempfile.NamedTemporaryFile(suffix=".wav")

    @LIB_CORE
    def tearDown(self):
        self.tempwav.close()

    @LIB_CORE
    def test_conversions(self):
        for ((i_sample_rate,
              i_channels,
              i_channel_mask,
              i_bits_per_sample),
             (o_sample_rate,
              o_channels,
              o_channel_mask,
              o_bits_per_sample)) in Combinations(SHORT_PCM_COMBINATIONS, 2):

            # print "(%s,%s,%s,%s) -> (%s,%s,%s,%s)" % \
            #     (i_sample_rate,
            #      i_channels,
            #      i_channel_mask,
            #      i_bits_per_sample,
            #      o_sample_rate,
            #      o_channels,
            #      o_channel_mask,
            #      o_bits_per_sample)
            reader = BLANK_PCM_Reader(5,
                                      sample_rate=i_sample_rate,
                                      channels=i_channels,
                                      bits_per_sample=i_bits_per_sample,
                                      channel_mask=i_channel_mask)

            converter = audiotools.PCMConverter(reader,
                                                sample_rate=o_sample_rate,
                                                channels=o_channels,
                                                bits_per_sample=o_bits_per_sample,
                                                channel_mask=o_channel_mask)
            wave = audiotools.WaveAudio.from_pcm(self.tempwav.name, converter)
            converter.close()

            self.assertEqual(wave.sample_rate(), o_sample_rate)
            self.assertEqual(wave.channels(), o_channels)
            self.assertEqual(wave.bits_per_sample(), o_bits_per_sample)
            self.assertEqual(wave.channel_mask(), o_channel_mask)
            self.assertEqual(
                (decimal.Decimal(wave.cd_frames()) / 75).to_integral(),
                5)


class PCMReaderWindow(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.channels = [range(0, 20),
                         range(20, 0, -1)]

    def __test_reader__(self, pcmreader, channels):
        framelist = pcmreader.read(1024)
        output_channels = [[] for i in xrange(len(channels))]
        while (len(framelist) > 0):
            for c in xrange(framelist.channels):
                output_channels[c].extend(framelist.channel(c))
            framelist = pcmreader.read(1024)
        self.assertEqual(channels, output_channels)

    @LIB_CORE
    def test_basic(self):
        self.__test_reader__(MiniFrameReader(self.channels,
                                             44100, 3, 16),
                             [range(0, 20), range(20, 0, -1)])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), 0, 20),
                             [range(0, 20), range(20, 0, -1)])

    @LIB_CORE
    def test_crop(self):
        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), 0, 15),
                             [range(0, 15), range(20, 5, -1)])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), 5, 15),
                             [range(5, 20), range(15, 0, -1)])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), 5, 10),
                             [range(5, 15), range(15, 5, -1)])

    @LIB_CORE
    def test_extend(self):
        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), -5, 25),
                             [[0] * 5 + range(0, 20),
                              [0] * 5 + range(20, 0, -1)])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), 0, 25),
                             [range(0, 20) + [0] * 5,
                              range(20, 0, -1) + [0] * 5])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), -5, 20),
                             [[0] * 5 + range(0, 15),
                              [0] * 5 + range(20, 5, -1)])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), -5, 15),
                             [[0] * 5 + range(0, 10),
                              [0] * 5 + range(20, 10, -1)])

        self.__test_reader__(audiotools.PCMReaderWindow(
                MiniFrameReader(self.channels, 44100, 3, 16), -5, 30),
                             [[0] * 5 + range(0, 20) + [0] * 5,
                              [0] * 5 + range(20, 0, -1) + [0] * 5])
