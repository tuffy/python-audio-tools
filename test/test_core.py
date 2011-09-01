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
import struct
import random
import tempfile
import decimal
import os
import os.path
import test_streams
import cStringIO
from hashlib import md5

from test import (parser, Variable_Reader, BLANK_PCM_Reader,
                  RANDOM_PCM_Reader,
                  EXACT_BLANK_PCM_Reader, SHORT_PCM_COMBINATIONS,
                  MD5_Reader, FrameCounter,
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


class CDDA(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bin = os.path.join(self.temp_dir, "Test.BIN")
        self.cue = os.path.join(self.temp_dir, "Test.CUE")

        bin_file = open(self.bin, "wb")
        # self.reader = MD5_Reader(EXACT_BLANK_PCM_Reader(69470436))
        self.reader = test_streams.Sine16_Stereo(69470436, 44100,
                                                 441.0, 0.50,
                                                 4410.0, 0.49, 1.0)
        audiotools.transfer_framelist_data(

            self.reader, bin_file.write)
        bin_file.close()

        f = open(self.cue, "w")
        f.write("""eJydkF1LwzAUQN8L/Q+X/oBxk6YfyVtoM4mu68iy6WudQ8qkHbNu+u9NneCc1IdCnk649xyuUQXk
epnpHGiOMU2Q+Z5xMCuLQs0tBOq92nTy7alus3b/AUeccL5/ZIHvZdLKWXkDjKcpIg2RszjxvYUy
09IUykCwanZNe2pAHrr6tXMjVtuZ+uG27l62Dk91T03VPG8np+oYwL1cK98DsEZmd4AE5CrXZU8c
O++wh2qzQxKc4X/S/l8vTQa3i7V2kWEap/iN57l66Pcjiq93IaWDUjpOyn9LETAVyASh1y0OR4Il
Fy3hYEs4qiXB6wOQULBQkOhCygalbISUUvrnACQVERfIr1scI4K5lk9od5+/""".decode('base64').decode('zlib'))
        f.close()

        self.sample_offset = audiotools.config.get_default("System",
                                                           "cdrom_read_offset",
                                                           "0")

    @LIB_CORE
    def tearDown(self):
        for f in os.listdir(self.temp_dir):
            os.unlink(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

        audiotools.config.set_default("System",
                                      "cdrom_read_offset",
                                      self.sample_offset)

    @LIB_CORE
    def test_init(self):
        from audiotools.cdio import CDDA
        from audiotools.cdio import CDImage

        self.assertRaises(TypeError, CDDA)
        self.assertRaises(TypeError, CDDA, None)
        self.assertRaises(TypeError, CDImage)
        self.assertRaises(ValueError, CDImage, "", -1)


    @LIB_CORE
    def test_cdda(self):
        cdda = audiotools.CDDA(self.cue)
        self.assertEqual(len(cdda), 4)
        checksum = md5()
        audiotools.transfer_framelist_data(
            audiotools.PCMCat(iter(cdda)),
            checksum.update)
        self.assertEqual(self.reader.hexdigest(),
                         checksum.hexdigest())

    @LIB_CORE
    def test_cdda_positive_offset(self):
        audiotools.config.set_default("System",
                                      "cdrom_read_offset",
                                      str(10))
        cdda = audiotools.CDDA(self.cue)
        reader_checksum = md5()
        cdrom_checksum = md5()
        audiotools.transfer_framelist_data(
            audiotools.PCMCat(iter(cdda)),
            cdrom_checksum.update)
        self.reader.reset()
        audiotools.transfer_framelist_data(
            audiotools.PCMReaderWindow(self.reader,
                                       10,
                                       69470436),
            reader_checksum.update)
        self.assertEqual(reader_checksum.hexdigest(),
                         cdrom_checksum.hexdigest())

    @LIB_CORE
    def test_cdda_negative_offset(self):
        audiotools.config.set_default("System",
                                      "cdrom_read_offset",
                                      str(-10))
        cdda = audiotools.CDDA(self.cue)
        reader_checksum = md5()
        cdrom_checksum = md5()
        audiotools.transfer_framelist_data(
            audiotools.PCMCat(iter(cdda)),
            cdrom_checksum.update)
        self.reader.reset()
        audiotools.transfer_framelist_data(
            audiotools.PCMReaderWindow(self.reader,
                                       -10,
                                       69470436),
            reader_checksum.update)
        self.assertEqual(reader_checksum.hexdigest(),
                         cdrom_checksum.hexdigest())


class ChannelMask(unittest.TestCase):
    @LIB_CORE
    def test_mask(self):
        mask = audiotools.ChannelMask.from_fields()
        self.assert_(not mask.defined())
        self.assert_(mask.undefined())
        self.assertEqual(len(mask), 0)
        self.assertEqual(set([]), set(mask.channels()))
        mask2 = audiotools.ChannelMask(int(mask))
        self.assertEqual(mask, mask2)

        mask_fields = audiotools.ChannelMask.SPEAKER_TO_MASK.keys()
        for count in xrange(1, len(mask_fields) + 1):
            for fields in Combinations(mask_fields, count):
                #build a mask from fields
                mask = audiotools.ChannelMask.from_fields(
                    **dict([(field, True) for field in fields]))
                self.assert_(mask.defined())
                self.assert_(not mask.undefined())
                self.assertEqual(len(mask), len(fields))
                self.assertEqual(set(fields), set(mask.channels()))
                mask2 = audiotools.ChannelMask(int(mask))
                self.assertEqual(mask, mask2)


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
    def test_resampler_init(self):
        from audiotools.resample import Resampler

        self.assertRaises(TypeError, Resampler)
        self.assertRaises(ValueError, Resampler, -1, 1.0, 0)
        self.assertRaises(ValueError, Resampler, 0, 1.0, 0)
        self.assertRaises(ValueError, Resampler, 2, 1.0, -1)
        self.assertRaises(ValueError, Resampler, 2, 1.0, 5)

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


class LimitedPCMReader(unittest.TestCase):
    @LIB_CORE
    def test_read(self):
        reader = audiotools.BufferedPCMReader(BLANK_PCM_Reader(1))
        counter1 = FrameCounter(2, 16, 44100)
        counter2 = FrameCounter(2, 16, 44100)
        audiotools.transfer_framelist_data(
            audiotools.LimitedPCMReader(reader, 4100), counter1.update)
        audiotools.transfer_framelist_data(
            audiotools.LimitedPCMReader(reader, 40000), counter2.update)
        self.assertEqual(counter1.value, 4100 * 4)
        self.assertEqual(counter2.value, 40000 * 4)


class PCMCat(unittest.TestCase):
    @LIB_CORE
    def test_read(self):
        reader1 = BLANK_PCM_Reader(1)
        reader2 = BLANK_PCM_Reader(2)
        reader3 = BLANK_PCM_Reader(3)
        counter = FrameCounter(2, 16, 44100)
        cat = audiotools.PCMCat(iter([reader1, reader2, reader3]))
        self.assertEqual(cat.sample_rate, 44100)
        self.assertEqual(cat.bits_per_sample, 16)
        self.assertEqual(cat.channels, 2)
        self.assertEqual(cat.channel_mask, 0x3)
        audiotools.transfer_framelist_data(cat, counter.update)
        self.assertEqual(int(counter), 6)


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

class Test_ReplayGain(unittest.TestCase):
    @LIB_CORE
    def test_replaygain(self):
        #a trivial test of the ReplayGain container

        self.assertEqual(audiotools.ReplayGain(0.5, 1.0, 0.5, 1.0),
                         audiotools.ReplayGain(0.5, 1.0, 0.5, 1.0))
        self.assertNotEqual(audiotools.ReplayGain(0.5, 1.0, 0.5, 1.0),
                            audiotools.ReplayGain(0.25, 1.0, 0.5, 1.0))
        self.assertNotEqual(audiotools.ReplayGain(0.5, 1.0, 0.5, 1.0),
                            audiotools.ReplayGain(0.5, 0.5, 0.5, 1.0))
        self.assertNotEqual(audiotools.ReplayGain(0.5, 1.0, 0.5, 1.0),
                            audiotools.ReplayGain(0.5, 1.0, 0.25, 1.0))
        self.assertNotEqual(audiotools.ReplayGain(0.5, 1.0, 0.5, 1.0),
                            audiotools.ReplayGain(0.5, 1.0, 0.5, 0.5))


class Test_filename_to_type(unittest.TestCase):
    @LIB_CORE
    def test_filename_to_type(self):
        type_group = {}
        for audio_type in audiotools.AVAILABLE_TYPES:
            type_group.setdefault(audio_type.SUFFIX, []).append(audio_type)

        for suffix in type_group.keys():
            temp = tempfile.NamedTemporaryFile(suffix="." + suffix)
            try:
                if (len(type_group[suffix]) == 1):
                    self.assertEqual(audiotools.filename_to_type(temp.name),
                                     type_group[suffix][0])
                else:
                    self.assertRaises(audiotools.AmbiguousAudioType,
                                      audiotools.filename_to_type,
                                      temp.name)
            finally:
                temp.close()

        temp = tempfile.NamedTemporaryFile(suffix=".foo")
        try:
            self.assertRaises(audiotools.UnknownAudioType,
                              audiotools.filename_to_type,
                              temp.name)
        finally:
            temp.close()

        temp = tempfile.NamedTemporaryFile()
        try:
            self.assertRaises(audiotools.UnknownAudioType,
                              audiotools.filename_to_type,
                              temp.name)
        finally:
            temp.close()


class Test_timestamp(unittest.TestCase):
    @LIB_CORE
    def test_timestamp(self):
        for timestamp in xrange(100000):
            self.assertEqual(
                audiotools.parse_timestamp(
                    audiotools.build_timestamp(timestamp)),
                timestamp)


class Test_group_tracks(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.output_format = audiotools.FlacAudio
        self.track_files = [
            tempfile.NamedTemporaryFile(
                suffix="." + self.output_format.SUFFIX)
            for i in xrange(5)]
        self.tracks = [
            self.output_format.from_pcm(
                track.name,
                BLANK_PCM_Reader(1)) for track in self.track_files]
        self.tracks[0].set_metadata(audiotools.MetaData(
                album_name=u"Album 1",
                album_number=1,
                track_number=1))
        self.tracks[1].set_metadata(audiotools.MetaData(
                album_name=u"Album 2",
                album_number=1,
                track_number=1))
        self.tracks[2].set_metadata(audiotools.MetaData(
                album_name=u"Album 1",
                album_number=1,
                track_number=2))
        self.tracks[3].set_metadata(audiotools.MetaData(
                album_name=u"Album 2",
                album_number=2,
                track_number=1))
        self.tracks[4].set_metadata(audiotools.MetaData(
                album_name=u"Album 3",
                album_number=1,
                track_number=1))


    @LIB_CORE
    def tearDown(self):
        for track in self.track_files:
            track.close()

    @LIB_CORE
    def test_grouping(self):
        groupings = list(audiotools.group_tracks(self.tracks))
        groupings.sort(lambda x,y: cmp(x[0].get_metadata().album_name,
                                       y[0].get_metadata().album_name))
        self.assertEqual(groupings[0], [self.tracks[0], self.tracks[2]])
        self.assertEqual(groupings[1], [self.tracks[1]])
        self.assertEqual(groupings[2], [self.tracks[3]])
        self.assertEqual(groupings[3], [self.tracks[4]])


class Test_open(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.dummy1 = tempfile.NamedTemporaryFile()
        self.dummy2 = tempfile.NamedTemporaryFile()
        self.dummy3 = tempfile.NamedTemporaryFile()
        self.dummy1.write("12345" * 1000)
        self.dummy1.flush()
        self.dummy2.write("54321" * 1000)
        self.dummy2.flush()

        data = open("flac-allframes.flac", "rb").read()
        self.dummy3.write(data[0:0x4] + chr(0xFF) + data[0x5:])
        self.dummy3.flush()

    @LIB_CORE
    def tearDown(self):
        self.dummy1.close()
        self.dummy2.close()

    @LIB_CORE
    def test_open(self):
        #ensure open on dummy file raises UnsupportedFile
        self.assertRaises(audiotools.UnsupportedFile,
                          audiotools.open,
                          self.dummy1.name)

        #ensure open on nonexistent file raises IOError
        self.assertRaises(IOError,
                          audiotools.open,
                          "/dev/null/foo")

        #ensure open on directory raises IOError
        self.assertRaises(IOError,
                          audiotools.open,
                          "/")

        #ensure open on unreadable file raises IOError
        os.chmod(self.dummy1.name, 0)
        try:
            self.assertRaises(IOError,
                              audiotools.open,
                              self.dummy1.name)
        finally:
            os.chmod(self.dummy1.name, 0600)

        #ensure a file whose __init__ method triggers InvalidFile
        #raises UnsupportedFile
        self.assertRaises(audiotools.UnsupportedFile,
                          audiotools.open,
                          self.dummy3.name)


class Test_open_directory(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.output_type = audiotools.FlacAudio
        self.suffix = "." + self.output_type.SUFFIX
        self.dir = tempfile.mkdtemp()

    def make_track(self, directory, track_number):
        track = self.output_type.from_pcm(
            os.path.join(directory, str(track_number) + self.suffix),
            BLANK_PCM_Reader(1))
        track.set_metadata(audiotools.MetaData(track_name=u"Track Name",
                                               track_number=track_number))
        return track

    @LIB_CORE
    def tearDown(self):
        import shutil

        shutil.rmtree(self.dir)

    @LIB_CORE
    def test_open_directory(self):
        subdir1 = os.path.join(self.dir, "dir1")
        subdir2 = os.path.join(self.dir, "dir2")
        subdir3 = os.path.join(subdir1, "dir3")

        os.mkdir(subdir1)
        os.mkdir(subdir2)
        os.mkdir(subdir3)

        track0_1 = self.make_track(self.dir, 1)
        track0_2 = self.make_track(self.dir, 2)
        track0_3 = self.make_track(self.dir, 3)
        track1_1 = self.make_track(subdir1, 1)
        track1_2 = self.make_track(subdir1, 2)
        track1_3 = self.make_track(subdir1, 3)
        track2_1 = self.make_track(subdir2, 1)
        track2_2 = self.make_track(subdir2, 2)
        track2_3 = self.make_track(subdir2, 3)
        track3_1 = self.make_track(subdir3, 1)
        track3_2 = self.make_track(subdir3, 2)
        track3_3 = self.make_track(subdir3, 3)

        tracks = list(audiotools.open_directory(self.dir))
        self.assertEqual([t.filename for t in tracks],
                         [t.filename for t in
                          [track0_1, track0_2, track0_3,
                           track1_1, track1_2, track1_3,
                           track3_1, track3_2, track3_3,
                           track2_1, track2_2, track2_3]])


class Test_open_files(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.output_type = audiotools.FlacAudio
        self.suffix = "." + self.output_type.SUFFIX
        self.dir = tempfile.mkdtemp()

    def make_track(self, directory, track_number):
        track = self.output_type.from_pcm(
            os.path.join(directory, str(track_number) + self.suffix),
            BLANK_PCM_Reader(1))
        track.set_metadata(audiotools.MetaData(track_name=u"Track Name",
                                               track_number=track_number))
        return track

    @LIB_CORE
    def tearDown(self):
        import shutil

        shutil.rmtree(self.dir)

    @LIB_CORE
    def test_open_files(self):
        track1 = self.make_track(self.dir, 1)
        track2 = self.make_track(self.dir, 2)
        track3 = self.make_track(self.dir, 3)
        dummy1_name = os.path.join(self.dir, "4" + self.suffix)
        dummy1 = open(dummy1_name, "wb")
        dummy1.write("Hello World")
        dummy1.close()

        tracks = list(audiotools.open_files([track1.filename, track2.filename,
                                             dummy1_name, track3.filename]))
        self.assertEqual([t.filename for t in tracks],
                         [t.filename for t in [track1, track2, track3]])


class Test_pcm_frame_cmp(unittest.TestCase):
    @LIB_CORE
    def test_pcm_frame_cmp(self):
        self.assert_(audiotools.pcm_frame_cmp(
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50,
                                           4410.0, 0.49, 1.0),
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50,
                                           4410.0, 0.49, 1.0)) is None)
        self.assertEqual(audiotools.pcm_frame_cmp(BLANK_PCM_Reader(1),
                                                  RANDOM_PCM_Reader(1)), 0)

        self.assertEqual(audiotools.pcm_frame_cmp(
                BLANK_PCM_Reader(1),
                BLANK_PCM_Reader(1, sample_rate=48000)), 0)
        self.assertEqual(audiotools.pcm_frame_cmp(
                BLANK_PCM_Reader(1),
                BLANK_PCM_Reader(1, channels=1)), 0)
        self.assertEqual(audiotools.pcm_frame_cmp(
                BLANK_PCM_Reader(1),
                BLANK_PCM_Reader(1, bits_per_sample=24)), 0)
        self.assertEqual(audiotools.pcm_frame_cmp(
                BLANK_PCM_Reader(1),
                BLANK_PCM_Reader(1, channel_mask=0x30)), 0)

        self.assertEqual(audiotools.pcm_frame_cmp(
                BLANK_PCM_Reader(2),
                audiotools.PCMCat(iter([BLANK_PCM_Reader(1),
                                        RANDOM_PCM_Reader(1)]))), 44100)

class Test_pcm_split(unittest.TestCase):
    @LIB_CORE
    def test_pcm_split(self):
        from itertools import izip

        pcm_frames = [44100 * l for l in (5, 10, 15, 4, 16, 10)]

        for (sub_pcm, sub_frames) in izip(
            audiotools.pcm_split(BLANK_PCM_Reader(60), pcm_frames),
            pcm_frames):
            counter = FrameCounter(2, 16, 44100)
            audiotools.transfer_framelist_data(sub_pcm, counter.update)
            self.assertEqual(sub_frames, int(counter) * 44100)

class Test_str_width(unittest.TestCase):
    @LIB_CORE
    def test_str_width(self):
        #check a plain ASCII string
        self.assertEqual(audiotools.str_width(u"Foo"), 3)

        #check a Unicode string without combining characters
        self.assertEqual(audiotools.str_width(u"F\u00f3o"), 3)

        #check a Unicode string with combining characters
        self.assertEqual(audiotools.str_width(u"Fo\u0301o"), 3)

        #check an ANSI-escaped ASCII string
        self.assertEqual(audiotools.str_width(u"\x1b[1mFoo\x1b[0m"), 3)

        #check an ANSI-escaped Unicode string without combining characeters
        self.assertEqual(audiotools.str_width(u"\x1b[1mF\u00f3o\x1b[0m"), 3)

        #check an ANSI-escaped Unicode string with combining characters
        self.assertEqual(audiotools.str_width(u"\x1b[1mFo\u0301o\x1b[0m"), 3)


class TestFrameList(unittest.TestCase):
    @classmethod
    def Bits8(cls):
        for i in xrange(0, 0xFF + 1):
            yield chr(i)

    @classmethod
    def Bits16(cls):
        for i in xrange(0, 0xFF + 1):
            for j in xrange(0, 0xFF + 1):
                yield chr(i) + chr(j)

    @classmethod
    def Bits24(cls):
        for i in xrange(0, 0xFF + 1):
            for j in xrange(0, 0xFF + 1):
                for k in xrange(0, 0xFF + 1):
                    yield chr(i) + chr(j) + chr(k)

    @LIB_CORE
    def test_basics(self):
        import audiotools.pcm

        self.assertRaises(TypeError,
                          audiotools.pcm.FrameList,
                          0, 2, 16, 0, 1)

        self.assertRaises(TypeError,
                          audiotools.pcm.FrameList,
                          [1, 2, 3], 2, 16, 0, 1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          "abc", 2, 16, 0, 1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          "abc", 4, 8, 0, 1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          "abcd", 1, 15, 0, 1)

        f = audiotools.pcm.FrameList("".join(map(chr, range(16))),
                                     2, 16, True, True)
        self.assertEqual(len(f), 8)
        self.assertEqual(f.channels, 2)
        self.assertEqual(f.frames, 4)
        self.assertEqual(f.bits_per_sample, 16)
        self.assertRaises(IndexError, f.__getitem__, 9)

        self.assertEqual(list(f.frame(0)),
                         [0x0001, 0x0203])
        self.assertEqual(list(f.frame(1)),
                         [0x0405, 0x0607])
        self.assertEqual(list(f.frame(2)),
                         [0x0809, 0x0A0B])
        self.assertEqual(list(f.frame(3)),
                         [0x0C0D, 0x0E0F])
        self.assertRaises(IndexError, f.frame, 4)
        self.assertRaises(IndexError, f.frame, -1)

        self.assertEqual(list(f.channel(0)),
                         [0x0001, 0x0405, 0x0809, 0x0C0D])
        self.assertEqual(list(f.channel(1)),
                         [0x0203, 0x0607, 0x0A0B, 0x0E0F])
        self.assertRaises(IndexError, f.channel, 2)
        self.assertRaises(IndexError, f.channel, -1)

        for bps in [8, 16, 24]:
            self.assertEqual(list(audiotools.pcm.from_list(
                        range(-40, 40), 1, bps, True)),
                             range(-40, 40))

        for bps in [8, 16, 24]:
            self.assertEqual(list(audiotools.pcm.from_list(
                        range((1 << (bps - 1)) - 40,
                              (1 << (bps - 1)) + 40), 1, bps, False)),
                             range(-40, 40))

        for channels in range(1, 9):
            for bps in [8, 16, 24]:
                for signed in [True, False]:
                    if (signed):
                        l = [random.choice(range(-40, 40)) for i in
                             xrange(16 * channels)]
                    else:
                        l = [random.choice(range(0, 80)) for i in
                             xrange(16 * channels)]
                    f2 = audiotools.pcm.from_list(l, channels, bps, signed)
                    if (signed):
                        self.assertEqual(list(f2), l)
                        for channel in range(channels):
                            self.assertEqual(list(f2.channel(channel)),
                                             l[channel::channels])
                    else:
                        self.assertEqual(list(f2),
                                         [i - (1 << (bps - 1))
                                          for i in l])
                        for channel in range(channels):
                            self.assertEqual(list(f2.channel(channel)),
                                             [i - (1 << (bps - 1))
                                              for i in l[channel::channels]])

        self.assertEqual(f.to_bytes(True, True),
                         '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f')
        self.assertEqual(f.to_bytes(False, True),
                         '\x01\x00\x03\x02\x05\x04\x07\x06\t\x08\x0b\n\r\x0c\x0f\x0e')
        #FIXME - check signed

        self.assertEqual(list(f),
                         list(audiotools.pcm.from_frames([f.frame(0),
                                                          f.frame(1),
                                                          f.frame(2),
                                                          f.frame(3)])))
        self.assertEqual(list(f),
                         list(audiotools.pcm.from_channels([f.channel(0),
                                                            f.channel(1)])))

        self.assertEqual(list(audiotools.pcm.from_list(
                    [0x0001, 0x0203, 0x0405, 0x0607,
                     0x0809, 0x0A0B, 0x0C0D, 0x0E0F], 2, 16, True)),
                         list(f))

        self.assertRaises(ValueError,
                          audiotools.pcm.from_list,
                          [0x0001, 0x0203, 0x0405, 0x0607,
                           0x0809, 0x0A0B, 0x0C0D], 2, 16, True)

        self.assertRaises(ValueError,
                          audiotools.pcm.from_list,
                          [0x0001, 0x0203, 0x0405, 0x0607,
                           0x0809, 0x0A0B, 0x0C0D, 0x0E0F], 2, 15, True)

        self.assertRaises(TypeError,
                          audiotools.pcm.from_frames,
                          [audiotools.pcm.from_list(range(2), 2, 16, False),
                           range(2)])

        self.assertRaises(ValueError,
                          audiotools.pcm.from_frames,
                          [audiotools.pcm.from_list(range(2), 2, 16, False),
                           audiotools.pcm.from_list(range(4), 2, 16, False)])

        self.assertRaises(ValueError,
                          audiotools.pcm.from_frames,
                          [audiotools.pcm.from_list(range(2), 2, 16, False),
                           audiotools.pcm.from_list(range(2), 1, 16, False)])

        self.assertRaises(ValueError,
                          audiotools.pcm.from_frames,
                          [audiotools.pcm.from_list(range(2), 2, 16, False),
                           audiotools.pcm.from_list(range(2), 2, 8, False)])

        self.assertEqual(list(audiotools.pcm.from_frames(
                    [audiotools.pcm.from_list(range(2), 2, 16, True),
                     audiotools.pcm.from_list(range(2, 4), 2, 16, True)])),
                         range(4))

        self.assertRaises(TypeError,
                          audiotools.pcm.from_channels,
                          [audiotools.pcm.from_list(range(2), 1, 16, False),
                           range(2)])

        self.assertRaises(ValueError,
                          audiotools.pcm.from_channels,
                          [audiotools.pcm.from_list(range(1), 1, 16, False),
                           audiotools.pcm.from_list(range(2), 2, 16, False)])

        self.assertRaises(ValueError,
                          audiotools.pcm.from_channels,
                          [audiotools.pcm.from_list(range(2), 1, 16, False),
                           audiotools.pcm.from_list(range(3), 1, 16, False)])

        self.assertRaises(ValueError,
                          audiotools.pcm.from_channels,
                          [audiotools.pcm.from_list(range(2), 1, 16, False),
                           audiotools.pcm.from_list(range(2), 1, 8, False)])

        self.assertEqual(list(audiotools.pcm.from_channels(
                    [audiotools.pcm.from_list(range(2), 1, 16, True),
                     audiotools.pcm.from_list(range(2, 4), 1, 16, True)])),
                         [0, 2, 1, 3])

        self.assertRaises(IndexError, f.split, -1)

        (f1, f2) = f.split(2)
        self.assertEqual(list(f1),
                         [0x0001, 0x0203,
                          0x0405, 0x0607])
        self.assertEqual(list(f2),
                         [0x0809, 0x0A0B,
                          0x0C0D, 0x0E0F])

        (f1, f2) = f.split(0)
        self.assertEqual(list(f1),
                         [])
        self.assertEqual(list(f2),
                         [0x0001, 0x0203,
                          0x0405, 0x0607,
                          0x0809, 0x0A0B,
                          0x0C0D, 0x0E0F])

        (f1, f2) = f.split(20)
        self.assertEqual(list(f1),
                         [0x0001, 0x0203,
                          0x0405, 0x0607,
                          0x0809, 0x0A0B,
                          0x0C0D, 0x0E0F])
        self.assertEqual(list(f2),
                         [])

        for i in xrange(f.frames):
            (f1, f2) = f.split(i)
            self.assertEqual(len(f1), i * f.channels)
            self.assertEqual(len(f2), (len(f) - (i * f.channels)))
            self.assertEqual(list(f1 + f2), list(f))

        import operator

        f1 = audiotools.pcm.from_list(range(10), 2, 16, False)
        self.assertRaises(TypeError, operator.concat, f1, [1, 2, 3])
        f2 = audiotools.pcm.from_list(range(10, 20), 1, 16, False)
        self.assertRaises(ValueError, operator.concat, f1, f2)
        f2 = audiotools.pcm.from_list(range(10, 20), 2, 8, False)
        self.assertRaises(ValueError, operator.concat, f1, f2)

        f1 = audiotools.pcm.from_list(range(10), 2, 16, False)
        self.assertEqual(f1, audiotools.pcm.from_list(range(10), 2, 16, False))
        self.assertNotEqual(f1, 10)
        self.assertNotEqual(f1, range(10))
        self.assertNotEqual(f1,
                            audiotools.pcm.from_list(range(10), 1, 16, False))
        self.assertNotEqual(f1,
                            audiotools.pcm.from_list(range(10), 2, 8, False))
        self.assertNotEqual(f1,
                            audiotools.pcm.from_list(range(10), 1, 8, False))
        self.assertNotEqual(f1,
                            audiotools.pcm.from_list(range(8), 2, 16, False))
        self.assertNotEqual(f1,
                            audiotools.pcm.from_list(range(12), 2, 8, False))

    @LIB_CORE
    def test_8bit_roundtrip(self):
        import audiotools.pcm

        unsigned_ints = range(0, 0xFF + 1)
        signed_ints = range(-0x80, 0x7F + 1)

        #unsigned, big-endian
        self.assertEqual([i - (1 << 7) for i in unsigned_ints],
                         list(audiotools.pcm.FrameList(
                    struct.pack(">%dB" % (len(unsigned_ints)), *unsigned_ints),
                    1, 8, True, False)))

        #unsigned, little-endian
        self.assertEqual([i - (1 << 7) for i in unsigned_ints],
                         list(audiotools.pcm.FrameList(
                    struct.pack("<%dB" % (len(unsigned_ints)), *unsigned_ints),
                    1, 8, False, False)))

        #signed, big-endian
        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    struct.pack(">%db" % (len(signed_ints)), *signed_ints),
                    1, 8, True, True)))

        #signed, little-endian
        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    struct.pack("<%db" % (len(signed_ints)), *signed_ints),
                    1,8,0,1)))

    @LIB_CORE
    def test_8bit_roundtrip_str(self):
        import audiotools.pcm

        s = "".join(TestFrameList.Bits8())

        #big endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     True, False).to_bytes(True, False), s)

        #big-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     True, True).to_bytes(True, True), s)

        #little-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     False, False).to_bytes(False, False), s)

        #little-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     False, True).to_bytes(False, True), s)

    @LIB_CORE
    def test_16bit_roundtrip(self):
        import audiotools.pcm

        unsigned_ints = range(0, 0xFFFF + 1)
        signed_ints = range(-0x8000, 0x7FFF + 1)

        #unsigned, big-endian
        self.assertEqual([i - (1 << 15) for i in unsigned_ints],
                         list(audiotools.pcm.FrameList(
                    struct.pack(">%dH" % (len(unsigned_ints)), *unsigned_ints),
                    1, 16, True, False)))

        #unsigned, little-endian
        self.assertEqual([i - (1 << 15) for i in unsigned_ints],
                         list(audiotools.pcm.FrameList(
                    struct.pack("<%dH" % (len(unsigned_ints)), *unsigned_ints),
                    1, 16, False, False)))

        #signed, big-endian
        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    struct.pack(">%dh" % (len(signed_ints)), *signed_ints),
                    1, 16, True, True)))

        #signed, little-endian
        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    struct.pack("<%dh" % (len(signed_ints)), *signed_ints),
                    1, 16, False, True)))

    @LIB_CORE
    def test_16bit_roundtrip_str(self):
        import audiotools.pcm

        s = "".join(TestFrameList.Bits16())

        #big-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     True, False).to_bytes(True, False),
            s,
            "data mismatch converting UBInt16 through string")

        #big-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     True, True).to_bytes(True, True),
            s,
            "data mismatch converting SBInt16 through string")

        #little-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     False, False).to_bytes(False, False),
            s,
            "data mismatch converting ULInt16 through string")

        #little-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     False, True).to_bytes(False, True),
            s,
            "data mismatch converting USInt16 through string")

    @LIB_CORE
    def test_24bit_roundtrip(self):
        import audiotools.pcm
        from audiotools.bitstream import BitstreamRecorder

        #setting this higher than 1 means we only test a sample
        #of the full 24-bit value range
        #since testing the whole range takes a very, very long time
        RANGE = 8

        unsigned_ints_high = [r << 8 for r in xrange(0, 0xFFFF + 1)]
        signed_ints_high = [r << 8 for r in xrange(-0x8000, 0x7FFF + 1)]

        for low_bits in xrange(0, 0xFF + 1, RANGE):
            unsigned_values = [high_bits | low_bits for high_bits in
                               unsigned_ints_high]

            rec = BitstreamRecorder(0)
            rec.build("24u" * len(unsigned_values), unsigned_values)
            self.assertEqual([i - (1 << 23) for i in unsigned_values],
                             list(audiotools.pcm.FrameList(
                        rec.data(), 1, 24, True, False)))


            rec = BitstreamRecorder(1)
            rec.build("24u" * len(unsigned_values), unsigned_values)
            self.assertEqual([i - (1 << 23) for i in unsigned_values],
                             list(audiotools.pcm.FrameList(
                        rec.data(), 1, 24, False, False)))

        for low_bits in xrange(0, 0xFF + 1, RANGE):
            if (high_bits < 0):
                signed_values = [high_bits - low_bits for high_bits in
                                 signed_ints_high]
            else:
                signed_values = [high_bits + low_bits for high_bits in
                                 signed_ints_high]

            rec = BitstreamRecorder(0)
            rec.build("24s" * len(signed_values), signed_values)
            self.assertEqual(signed_values,
                             list(audiotools.pcm.FrameList(
                        rec.data(), 1, 24, True, True)))

            rec = BitstreamRecorder(1)
            rec.build("24s" * len(signed_values), signed_values)
            self.assertEqual(signed_values,
                             list(audiotools.pcm.FrameList(
                        rec.data(), 1, 24, False, True)))

    @LIB_CORE
    def test_24bit_roundtrip_str(self):
        import audiotools.pcm

        s = "".join(TestFrameList.Bits24())
        #big-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     True, False).to_bytes(True, False), s)

        #big-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     True, True).to_bytes(True, True), s)

        #little-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     False, False).to_bytes(False, False), s)

        #little-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     False, True).to_bytes(False, True), s)

    @LIB_CORE
    def test_conversion(self):
        for format in audiotools.AVAILABLE_TYPES:
            temp_track = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
            try:
                for sine_class in [test_streams.Sine8_Stereo,
                                   test_streams.Sine16_Stereo,
                                   test_streams.Sine24_Stereo]:
                    sine = sine_class(88200, 44100, 441.0, 0.50, 441.0, 0.49, 1.0)
                    try:
                        track = format.from_pcm(temp_track.name, sine)
                    except audiotools.UnsupportedBitsPerSample:
                        continue
                    if (track.lossless()):
                        md5sum = md5()
                        audiotools.transfer_framelist_data(track.to_pcm(),
                                                           md5sum.update)
                        self.assertEqual(md5sum.hexdigest(), sine.hexdigest(),
                                         "MD5 mismatch for %s using %s" % \
                                             (track.NAME, repr(sine)))
                        for new_format in audiotools.AVAILABLE_TYPES:
                            temp_track2 = tempfile.NamedTemporaryFile(suffix="." + format.SUFFIX)
                            try:
                                try:
                                    track2 = new_format.from_pcm(temp_track2.name,
                                                                 track.to_pcm())
                                    if (track2.lossless()):
                                        md5sum2 = md5()
                                        audiotools.transfer_framelist_data(track2.to_pcm(),
                                                                           md5sum2.update)
                                        self.assertEqual(md5sum.hexdigest(), sine.hexdigest(),
                                                         "MD5 mismatch for converting %s from %s to %s" % \
                                                             (repr(sine), track.NAME, track2.NAME))
                                except audiotools.UnsupportedBitsPerSample:
                                    continue
                            finally:
                                temp_track2.close()
            finally:
                temp_track.close()

    @LIB_CORE
    def test_errors(self):
        #check list that's too large
        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [0.0] * 5, 2)

        #check list that's too small
        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [0.0] * 3, 2)

        #check channels <= 0
        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [0.0] * 4, 0)

        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [0.0] * 4, -1)


class TestFloatFrameList(unittest.TestCase):
    @LIB_CORE
    def test_basics(self):
        import audiotools.pcm

        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [1.0, 2.0, 3.0], 2)

        self.assertRaises(TypeError,
                          audiotools.pcm.FloatFrameList,
                          0, 1)

        self.assertRaises(TypeError,
                          audiotools.pcm.FloatFrameList,
                          [1.0, 2.0, "a"], 1)

        f = audiotools.pcm.FloatFrameList(map(float, range(8)), 2)
        self.assertEqual(len(f), 8)
        self.assertEqual(f.channels, 2)
        self.assertEqual(f.frames, 4)
        self.assertRaises(IndexError, f.__getitem__, 9)

        self.assertEqual(list(f.frame(0)),
                         [0.0, 1.0])
        self.assertEqual(list(f.frame(1)),
                         [2.0, 3.0])
        self.assertEqual(list(f.frame(2)),
                         [4.0, 5.0])
        self.assertEqual(list(f.frame(3)),
                         [6.0, 7.0])
        self.assertRaises(IndexError, f.frame, 4)
        self.assertRaises(IndexError, f.frame, -1)

        self.assertEqual(list(f.channel(0)),
                         [0.0, 2.0, 4.0, 6.0])
        self.assertEqual(list(f.channel(1)),
                         [1.0, 3.0, 5.0, 7.0])
        self.assertRaises(IndexError, f.channel, 2)
        self.assertRaises(IndexError, f.channel, -1)

        self.assertEqual(list(f),
                         list(audiotools.pcm.from_float_frames([f.frame(0),
                                                                f.frame(1),
                                                                f.frame(2),
                                                                f.frame(3)])))
        self.assertEqual(list(f),
                         list(audiotools.pcm.from_float_channels([f.channel(0),
                                                                  f.channel(1)])))

        #FIXME - check from_frames
        #FIXME - check from_channels

        self.assertRaises(IndexError, f.split, -1)

        (f1, f2) = f.split(2)
        self.assertEqual(list(f1),
                         [0.0, 1.0,
                          2.0, 3.0])
        self.assertEqual(list(f2),
                         [4.0, 5.0,
                          6.0, 7.0])

        (f1, f2) = f.split(0)
        self.assertEqual(list(f1),
                         [])
        self.assertEqual(list(f2),
                         [0.0, 1.0,
                          2.0, 3.0,
                          4.0, 5.0,
                          6.0, 7.0])

        (f1, f2) = f.split(20)
        self.assertEqual(list(f1),
                         [0.0, 1.0,
                          2.0, 3.0,
                          4.0, 5.0,
                          6.0, 7.0])
        self.assertEqual(list(f2),
                         [])

        for i in xrange(f.frames):
            (f1, f2) = f.split(i)
            self.assertEqual(len(f1), i * f.channels)
            self.assertEqual(len(f2), (len(f) - (i * f.channels)))
            self.assertEqual(list(f1 + f2), list(f))

        import operator

        f1 = audiotools.pcm.FloatFrameList(map(float, range(10)), 2)
        self.assertRaises(TypeError, operator.concat, f1, [1, 2, 3])

        #check round-trip from float->int->float
        l = [float(i - 128) / (1 << 7) for i in range(0, 1 << 8)]
        for bps in [8, 16, 24]:
            for signed in [True, False]:
                self.assertEqual(
                    l,
                    list(audiotools.pcm.FloatFrameList(l, 1).to_int(bps).to_float()))

        #check round-trip from int->float->int
        for bps in [8, 16, 24]:
            l = range(0, 1 << bps, 4)
            self.assertEqual(
                [i - (1 << (bps - 1)) for i in l],
                list(audiotools.pcm.from_list(l, 1, bps, False).to_float().to_int(bps)))

            l = range(-(1 << (bps - 1)), (1 << (bps - 1)) - 1, 4)
            self.assertEqual(
                l,
                list(audiotools.pcm.from_list(l, 1, bps, True).to_float().to_int(bps)))

    @LIB_CORE
    def test_errors(self):
        #check string that's too large
        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          chr(0) * 5, 2, 16, 1, 1)

        #check string that's too small
        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          chr(0) * 3, 2, 16, 1, 1)


        #check channels <= 0
        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          chr(0) * 4, 0, 16, 1, 1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          chr(0) * 4, -1, 16, 1, 1)


        #check bps != 8,16,24
        for bps in [0,7,9,15,17,23,25,64]:
            self.assertRaises(ValueError,
                              audiotools.pcm.FrameList,
                              chr(0) * 4, 2, bps, 1, 1)



class __SimpleChunkReader__:
    def __init__(self, chunks):
        self.chunks = chunks
        self.position = 0

    def read(self, bytes):
        try:
            self.position += len(self.chunks[0])
            return self.chunks.pop(0)
        except IndexError:
            return ""

    def tell(self):
        return self.position

    def close(self):
        pass

class ByteCounter:
    def __init__(self):
        self.bytes = 0

    def __int__(self):
        return self.bytes

    def reset(self):
        self.bytes = 0

    def callback(self, i):
        self.bytes += 1

class Bitstream(unittest.TestCase):
    def __test_big_endian_reader__(self, reader, table):
        #check the bitstream reader
        #against some known big-endian values

        reader.mark()
        self.assertEqual(reader.read(2), 0x2)
        self.assertEqual(reader.read(3), 0x6)
        self.assertEqual(reader.read(5), 0x07)
        self.assertEqual(reader.read(3), 0x5)
        self.assertEqual(reader.read(19), 0x53BC1)

        reader.rewind()
        self.assertEqual(reader.read64(2), 0x2)
        self.assertEqual(reader.read64(3), 0x6)
        self.assertEqual(reader.read64(5), 0x07)
        self.assertEqual(reader.read64(3), 0x5)
        self.assertEqual(reader.read64(19), 0x53BC1)

        reader.rewind()
        self.assertEqual(reader.read(2), 0x2)
        reader.skip(3)
        self.assertEqual(reader.read(5), 0x07)
        reader.skip(3)
        self.assertEqual(reader.read(19), 0x53BC1)

        reader.rewind()
        self.assertEqual(reader.read(1), 1)
        bit = reader.read(1)
        self.assertEqual(bit, 0)
        reader.unread(bit)
        self.assertEqual(reader.read(2), 1)
        reader.byte_align()

        reader.rewind()
        self.assertEqual(reader.read(8), 0xB1)
        reader.unread(0)
        self.assertEqual(reader.read(1), 0)
        reader.unread(1)
        self.assertEqual(reader.read(1), 1)

        reader.rewind()
        self.assertEqual(reader.read_signed(2), -2)
        self.assertEqual(reader.read_signed(3), -2)
        self.assertEqual(reader.read_signed(5), 7)
        self.assertEqual(reader.read_signed(3), -3)
        self.assertEqual(reader.read_signed(19), -181311)

        reader.rewind()
        self.assertEqual(reader.read_signed64(2), -2)
        self.assertEqual(reader.read_signed64(3), -2)
        self.assertEqual(reader.read_signed64(5), 7)
        self.assertEqual(reader.read_signed64(3), -3)
        self.assertEqual(reader.read_signed64(19), -181311)

        reader.rewind()
        self.assertEqual(reader.unary(0), 1)
        self.assertEqual(reader.unary(0), 2)
        self.assertEqual(reader.unary(0), 0)
        self.assertEqual(reader.unary(0), 0)
        self.assertEqual(reader.unary(0), 4)

        reader.rewind()
        self.assertEqual(reader.unary(1), 0)
        self.assertEqual(reader.unary(1), 1)
        self.assertEqual(reader.unary(1), 0)
        self.assertEqual(reader.unary(1), 3)
        self.assertEqual(reader.unary(1), 0)

        reader.rewind()
        self.assertEqual(reader.limited_unary(0, 2), 1)
        self.assertEqual(reader.limited_unary(0, 2), None)
        reader.rewind()
        self.assertEqual(reader.limited_unary(1, 2), 0)
        self.assertEqual(reader.limited_unary(1, 2), 1)
        self.assertEqual(reader.limited_unary(1, 2), 0)
        self.assertEqual(reader.limited_unary(1, 2), None)

        reader.rewind()
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 4)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 2)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 2)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 2)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 4)
        self.assertEqual(reader.read_huffman_code(table), 2)

        reader.rewind()
        self.assertEqual(reader.read(3), 5)
        reader.byte_align()
        self.assertEqual(reader.read(3), 7)
        reader.byte_align()
        reader.byte_align()
        self.assertEqual(reader.read(8), 59)
        reader.byte_align()
        self.assertEqual(reader.read(4), 12)

        reader.rewind()
        self.assertEqual(reader.read_bytes(2), "\xB1\xED")
        reader.rewind()
        self.assertEqual(reader.read(4), 11)
        self.assertEqual(reader.read_bytes(2), "\x1E\xD3")

        reader.rewind()
        self.assertEqual(reader.read(3), 5)
        reader.set_endianness(1)
        self.assertEqual(reader.read(3), 5)
        reader.set_endianness(0)
        self.assertEqual(reader.read(4), 3)
        reader.set_endianness(0)
        self.assertEqual(reader.read(4), 12)

        reader.rewind()
        reader.mark()
        self.assertEqual(reader.read(4), 0xB)
        reader.rewind()
        self.assertEqual(reader.read(8), 0xB1)
        reader.rewind()
        self.assertEqual(reader.read(12), 0xB1E)
        reader.unmark()
        reader.mark()
        self.assertEqual(reader.read(4), 0xD)
        reader.rewind()
        self.assertEqual(reader.read(8), 0xD3)
        reader.rewind()
        self.assertEqual(reader.read(12), 0xD3B)
        reader.unmark()

        reader.rewind()
        reader.unmark()

    def __test_little_endian_reader__(self, reader, table):
        #check the bitstream reader
        #against some known little-endian values

        reader.mark()
        self.assertEqual(reader.read(2), 0x1)
        self.assertEqual(reader.read(3), 0x4)
        self.assertEqual(reader.read(5), 0x0D)
        self.assertEqual(reader.read(3), 0x3)
        self.assertEqual(reader.read(19), 0x609DF)

        reader.rewind()
        self.assertEqual(reader.read64(2), 1)
        self.assertEqual(reader.read64(3), 4)
        self.assertEqual(reader.read64(5), 13)
        self.assertEqual(reader.read64(3), 3)
        self.assertEqual(reader.read64(19), 395743)

        reader.rewind()
        self.assertEqual(reader.read(2), 0x1)
        reader.skip(3)
        self.assertEqual(reader.read(5), 0x0D)
        reader.skip(3)
        self.assertEqual(reader.read(19), 0x609DF)

        reader.rewind()
        self.assertEqual(reader.read(1), 1)
        bit = reader.read(1)
        self.assertEqual(bit, 0)
        reader.unread(bit)
        self.assertEqual(reader.read(4), 8)
        reader.byte_align()

        reader.rewind()
        self.assertEqual(reader.read(8), 0xB1)
        reader.unread(0)
        self.assertEqual(reader.read(1), 0)
        reader.unread(1)
        self.assertEqual(reader.read(1), 1)

        reader.rewind()
        self.assertEqual(reader.read_signed(2), 1)
        self.assertEqual(reader.read_signed(3), -4)
        self.assertEqual(reader.read_signed(5), 13)
        self.assertEqual(reader.read_signed(3), 3)
        self.assertEqual(reader.read_signed(19), -128545)

        reader.rewind()
        self.assertEqual(reader.read_signed64(2), 1)
        self.assertEqual(reader.read_signed64(3), -4)
        self.assertEqual(reader.read_signed64(5), 13)
        self.assertEqual(reader.read_signed64(3), 3)
        self.assertEqual(reader.read_signed64(19), -128545)

        reader.rewind()
        self.assertEqual(reader.unary(0), 1)
        self.assertEqual(reader.unary(0), 0)
        self.assertEqual(reader.unary(0), 0)
        self.assertEqual(reader.unary(0), 2)
        self.assertEqual(reader.unary(0), 2)

        reader.rewind()
        self.assertEqual(reader.unary(1), 0)
        self.assertEqual(reader.unary(1), 3)
        self.assertEqual(reader.unary(1), 0)
        self.assertEqual(reader.unary(1), 1)
        self.assertEqual(reader.unary(1), 0)

        reader.rewind()
        self.assertEqual(reader.limited_unary(0, 2), 1)
        self.assertEqual(reader.limited_unary(0, 2), 0)
        self.assertEqual(reader.limited_unary(0, 2), 0)
        self.assertEqual(reader.limited_unary(0, 2), None)

        reader.rewind()
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 3)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 2)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 0)
        self.assertEqual(reader.read_huffman_code(table), 1)
        self.assertEqual(reader.read_huffman_code(table), 2)
        self.assertEqual(reader.read_huffman_code(table), 4)
        self.assertEqual(reader.read_huffman_code(table), 3)

        reader.rewind()
        self.assertEqual(reader.read_bytes(2), "\xB1\xED")
        reader.rewind()
        self.assertEqual(reader.read(4), 1)

        self.assertEqual(reader.read_bytes(2), "\xDB\xBE")

        reader.rewind()
        self.assertEqual(reader.read(3), 1)
        reader.byte_align()
        self.assertEqual(reader.read(3), 5)
        reader.byte_align()
        reader.byte_align()
        self.assertEqual(reader.read(8), 59)
        reader.byte_align()
        self.assertEqual(reader.read(4), 1)

        reader.rewind()
        self.assertEqual(reader.read(3), 1)
        reader.set_endianness(0)
        self.assertEqual(reader.read(3), 7)
        reader.set_endianness(1)
        self.assertEqual(reader.read(4), 11)
        reader.set_endianness(1)
        self.assertEqual(reader.read(4), 1)

        reader.rewind()
        self.assertEqual(reader.limited_unary(1, 2), 0)
        self.assertEqual(reader.limited_unary(1, 2), None)

        reader.rewind()
        reader.mark()
        self.assertEqual(reader.read(4), 0x1)
        reader.rewind()
        self.assertEqual(reader.read(8), 0xB1)
        reader.rewind()
        self.assertEqual(reader.read(12), 0xDB1)
        reader.unmark()
        reader.mark()
        self.assertEqual(reader.read(4), 0xE)
        reader.rewind()
        self.assertEqual(reader.read(8), 0xBE)
        reader.rewind()
        self.assertEqual(reader.read(12), 0x3BE)
        reader.unmark()

        reader.rewind()
        reader.unmark()

    def __test_try__(self, reader, table):
        reader.mark()

        #bounce to the very end of the stream
        reader.skip(31)
        reader.mark()
        self.assertEqual(reader.read(1), 1)
        reader.rewind()

        #then test all the read methods to ensure they trigger br_abort
        #in the case of unary/Huffman, the stream ends on a "1" bit
        #whether reading it big-endian or little-endian

        self.assertRaises(IOError, reader.read, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.read64, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.read_signed, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.read_signed64, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.skip, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.unary, 0)
        reader.rewind()
        self.assertEqual(reader.unary(1), 0)
        self.assertRaises(IOError, reader.unary, 1)
        reader.rewind()
        self.assertRaises(IOError, reader.limited_unary, 0, 3)
        reader.rewind()
        self.assertEqual(reader.limited_unary(1, 3), 0)
        self.assertRaises(IOError, reader.limited_unary, 1, 3)
        reader.rewind()
        self.assertRaises(IOError, reader.read_huffman_code, table)
        reader.rewind()
        self.assertRaises(IOError, reader.read_bytes, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.substream, 1)

        reader.unmark()

        reader.rewind()
        reader.unmark()

    def __test_callbacks_reader__(self,
                                  reader,
                                  unary_0_reads,
                                  unary_1_reads,
                                  table,
                                  huffman_code_count):
        counter = ByteCounter()
        reader.mark()
        reader.add_callback(counter.callback)

        #a single callback
        counter.reset()
        for i in xrange(8):
            reader.read(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #calling callbacks directly
        counter.reset()
        for i in xrange(20):
            reader.call_callbacks(0)
        self.assertEqual(int(counter), 20)

        #two callbacks
        counter.reset()
        reader.add_callback(counter.callback)
        for i in xrange(8):
            reader.read(4)
        self.assertEqual(int(counter), 8)
        reader.pop_callback()
        reader.rewind()

        #temporarily suspending the callback
        counter.reset()
        reader.read(8)
        self.assertEqual(int(counter), 1)
        callback = reader.pop_callback()
        reader.read(8)
        reader.read(8)
        reader.add_callback(counter.callback)
        reader.read(8)
        self.assertEqual(int(counter), 2)
        reader.rewind()

        #temporarily adding two callbacks
        counter.reset()
        reader.read(8)
        self.assertEqual(int(counter), 1)
        reader.add_callback(counter.callback)
        reader.read(8)
        reader.read(8)
        reader.pop_callback()
        reader.read(8)
        self.assertEqual(int(counter), 6)
        reader.rewind()

        #read_signed
        counter.reset()
        for i in xrange(8):
            reader.read_signed(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #read_64
        counter.reset()
        for i in xrange(8):
            reader.read64(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #skip
        counter.reset()
        for i in xrange(8):
            reader.skip(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #read_unary
        counter.reset()
        for i in xrange(unary_0_reads):
            reader.unary(0)
        self.assertEqual(int(counter), 4)
        counter.reset()
        reader.rewind()
        for i in xrange(unary_1_reads):
            reader.unary(1)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #read_limited_unary
        counter.reset()
        for i in xrange(unary_0_reads):
            reader.limited_unary(0, 6)
        self.assertEqual(int(counter), 4)
        counter.reset()
        reader.rewind()
        for i in xrange(unary_1_reads):
            reader.limited_unary(1, 6)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #read_huffman_code
        counter.reset()
        for i in xrange(huffman_code_count):
            reader.read_huffman_code(table)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        #read_bytes
        counter.reset()
        reader.read_bytes(2)
        reader.read_bytes(2)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        reader.pop_callback()
        reader.unmark()


    @LIB_CORE
    def test_init_error(self):
        from audiotools.bitstream import BitstreamAccumulator
        from audiotools.bitstream import BitstreamReader
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamWriter

        self.assertRaises(TypeError, BitstreamAccumulator)
        self.assertRaises(TypeError, BitstreamAccumulator, None)
        self.assertRaises(TypeError, BitstreamRecorder)
        self.assertRaises(TypeError, BitstreamRecorder, None)
        self.assertRaises(TypeError, BitstreamWriter)
        self.assertRaises(TypeError, BitstreamReader)

    @LIB_CORE
    def test_simple_reader(self):
        from audiotools.bitstream import BitstreamReader,HuffmanTree

        temp = tempfile.TemporaryFile()
        try:
            temp.write(chr(0xB1))
            temp.write(chr(0xED))
            temp.write(chr(0x3B))
            temp.write(chr(0xC1))
            temp.seek(0, 0)

            #test a big-endian stream built from a file
            reader = BitstreamReader(temp, 0)
            table_be = HuffmanTree([[1, 1], 0,
                                    [1, 0], 1,
                                    [0, 1], 2,
                                    [0, 0, 1], 3,
                                    [0, 0, 0], 4], 0)
            self.__test_big_endian_reader__(reader, table_be)
            self.__test_try__(reader, table_be)
            self.__test_callbacks_reader__(reader, 14, 18, table_be, 14)

            temp.seek(0, 0)

            #test a little-endian stream built from a file
            reader = BitstreamReader(temp, 1)
            table_le = HuffmanTree([[1, 1], 0,
                                    [1, 0], 1,
                                    [0, 1], 2,
                                    [0, 0, 1], 3,
                                    [0, 0, 0], 4], 1)
            self.__test_little_endian_reader__(reader, table_le)
            self.__test_try__(reader, table_le)
            self.__test_callbacks_reader__(reader, 14, 18, table_le, 13)

            #pad the stream with some additional data at both ends
            temp.seek(0, 0)
            temp.write(chr(0xFF))
            temp.write(chr(0xFF))
            temp.write(chr(0xB1))
            temp.write(chr(0xED))
            temp.write(chr(0x3B))
            temp.write(chr(0xC1))
            temp.write(chr(0xFF))
            temp.write(chr(0xFF))
            temp.flush()
            temp.seek(0, 0)

            reader = BitstreamReader(temp, 0)
            reader.mark()

            #check a big-endian substream built from a file
            reader.skip(16)
            subreader = reader.substream(4)
            self.__test_big_endian_reader__(subreader, table_be)
            self.__test_try__(subreader, table_be)
            self.__test_callbacks_reader__(subreader, 14, 18, table_be, 13)

            #check a big-endian substream built from another substream
            reader.rewind()
            reader.skip(8)
            subreader1 = reader.substream(6)
            subreader1.skip(8)
            subreader2 = subreader.substream(4)
            self.__test_big_endian_reader__(subreader2, table_be)
            self.__test_try__(subreader2, table_be)
            self.__test_callbacks_reader__(subreader2, 14, 18, table_be, 13)
            reader.unmark()

            temp.seek(0, 0)

            reader = BitstreamReader(temp, 1)
            reader.mark()

            #check a little-endian substream built from a file
            reader.skip(16)
            subreader = reader.substream(4)
            self.__test_little_endian_reader__(subreader, table_le)
            self.__test_try__(subreader, table_le)
            self.__test_callbacks_reader__(subreader, 14, 18, table_le, 13)

            #check a little-endian substream built from another substream
            reader.rewind()
            reader.skip(8)
            subreader1 = reader.substream(6)
            subreader1.skip(8)
            subreader2 = subreader.substream(4)
            self.__test_little_endian_reader__(subreader2, table_le)
            self.__test_try__(subreader2, table_le)
            self.__test_callbacks_reader__(subreader2, 14, 18, table_le, 13)
            reader.unmark()

            #test the writer functions with each endianness
            self.__test_writer__(0)
            self.__test_writer__(1)

        finally:
            temp.close()

    def __test_edge_reader_be__(self, reader):
        reader.mark()

        #try the unsigned 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read(32), 0)
        self.assertEqual(reader.read(32), 4294967295)
        self.assertEqual(reader.read(32), 2147483648)
        self.assertEqual(reader.read(32), 2147483647)
        self.assertEqual(reader.read64(64), 0)
        self.assertEqual(reader.read64(64), 0xFFFFFFFFFFFFFFFFL)
        self.assertEqual(reader.read64(64), 9223372036854775808L)
        self.assertEqual(reader.read64(64), 9223372036854775807L)

        #try the signed 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read_signed(32), 0)
        self.assertEqual(reader.read_signed(32), -1)
        self.assertEqual(reader.read_signed(32), -2147483648)
        self.assertEqual(reader.read_signed(32), 2147483647)
        self.assertEqual(reader.read_signed64(64), 0)
        self.assertEqual(reader.read_signed64(64), -1)
        self.assertEqual(reader.read_signed64(64), -9223372036854775808L)
        self.assertEqual(reader.read_signed64(64), 9223372036854775807L)

        #try the unsigned values via parse()
        reader.rewind()
        (u_val_1,
         u_val_2,
         u_val_3,
         u_val_4,
         u_val64_1,
         u_val64_2,
         u_val64_3,
         u_val64_4) = reader.parse("32u 32u 32u 32u 64U 64U 64U 64U")
        self.assertEqual(u_val_1, 0)
        self.assertEqual(u_val_2, 4294967295)
        self.assertEqual(u_val_3, 2147483648)
        self.assertEqual(u_val_4, 2147483647)
        self.assertEqual(u_val64_1, 0)
        self.assertEqual(u_val64_2, 0xFFFFFFFFFFFFFFFFL)
        self.assertEqual(u_val64_3, 9223372036854775808L)
        self.assertEqual(u_val64_4, 9223372036854775807L)

        #try the signed values via parse()
        reader.rewind()
        (s_val_1,
         s_val_2,
         s_val_3,
         s_val_4,
         s_val64_1,
         s_val64_2,
         s_val64_3,
         s_val64_4) = reader.parse("32s 32s 32s 32s 64S 64S 64S 64S")
        self.assertEqual(s_val_1, 0)
        self.assertEqual(s_val_2, -1)
        self.assertEqual(s_val_3, -2147483648)
        self.assertEqual(s_val_4, 2147483647)
        self.assertEqual(s_val64_1, 0)
        self.assertEqual(s_val64_2, -1)
        self.assertEqual(s_val64_3, -9223372036854775808L)
        self.assertEqual(s_val64_4, 9223372036854775807L)

        reader.unmark()

    def __test_edge_reader_le__(self, reader):
        reader.mark()

        #try the unsigned 32 and 64 bit values
        self.assertEqual(reader.read(32), 0)
        self.assertEqual(reader.read(32), 4294967295)
        self.assertEqual(reader.read(32), 2147483648)
        self.assertEqual(reader.read(32), 2147483647)
        self.assertEqual(reader.read64(64), 0)
        self.assertEqual(reader.read64(64), 0xFFFFFFFFFFFFFFFFL)
        self.assertEqual(reader.read64(64), 9223372036854775808L)
        self.assertEqual(reader.read64(64), 9223372036854775807L)

        #try the signed 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read_signed(32), 0)
        self.assertEqual(reader.read_signed(32), -1)
        self.assertEqual(reader.read_signed(32), -2147483648)
        self.assertEqual(reader.read_signed(32), 2147483647)
        self.assertEqual(reader.read_signed64(64), 0)
        self.assertEqual(reader.read_signed64(64), -1)
        self.assertEqual(reader.read_signed64(64), -9223372036854775808L)
        self.assertEqual(reader.read_signed64(64), 9223372036854775807L)

        #try the unsigned values via parse()
        reader.rewind()
        (u_val_1,
         u_val_2,
         u_val_3,
         u_val_4,
         u_val64_1,
         u_val64_2,
         u_val64_3,
         u_val64_4) = reader.parse("32u 32u 32u 32u 64U 64U 64U 64U")
        self.assertEqual(u_val_1, 0)
        self.assertEqual(u_val_2, 4294967295)
        self.assertEqual(u_val_3, 2147483648)
        self.assertEqual(u_val_4, 2147483647)
        self.assertEqual(u_val64_1, 0)
        self.assertEqual(u_val64_2, 0xFFFFFFFFFFFFFFFFL)
        self.assertEqual(u_val64_3, 9223372036854775808L)
        self.assertEqual(u_val64_4, 9223372036854775807L)

        #try the signed values via parse()
        reader.rewind()
        (s_val_1,
         s_val_2,
         s_val_3,
         s_val_4,
         s_val64_1,
         s_val64_2,
         s_val64_3,
         s_val64_4) = reader.parse("32s 32s 32s 32s 64S 64S 64S 64S")
        self.assertEqual(s_val_1, 0)
        self.assertEqual(s_val_2, -1)
        self.assertEqual(s_val_3, -2147483648)
        self.assertEqual(s_val_4, 2147483647)
        self.assertEqual(s_val64_1, 0)
        self.assertEqual(s_val64_2, -1)
        self.assertEqual(s_val64_3, -9223372036854775808L)
        self.assertEqual(s_val64_4, 9223372036854775807L)

        reader.unmark()

    def __test_edge_writer__(self, get_writer, validate_writer):
        #try the unsigned 32 and 64 bit values
        (writer, temp) = get_writer()
        writer.write(32, 0)
        writer.write(32, 4294967295)
        writer.write(32, 2147483648)
        writer.write(32, 2147483647)
        writer.write64(64, 0)
        writer.write64(64, 0xFFFFFFFFFFFFFFFFL)
        writer.write64(64, 9223372036854775808L)
        writer.write64(64, 9223372036854775807L)
        validate_writer(writer, temp)

        #try the signed 32 and 64 bit values
        (writer, temp) = get_writer()
        writer.write_signed(32, 0)
        writer.write_signed(32, -1)
        writer.write_signed(32, -2147483648)
        writer.write_signed(32, 2147483647)
        writer.write_signed64(64, 0)
        writer.write_signed64(64, -1)
        writer.write_signed64(64, -9223372036854775808L)
        writer.write_signed64(64, 9223372036854775807L)
        validate_writer(writer, temp)

        #try the unsigned values via build()
        (writer, temp) = get_writer()
        u_val_1 = 0
        u_val_2 = 4294967295
        u_val_3 = 2147483648
        u_val_4 = 2147483647
        u_val64_1 = 0
        u_val64_2 = 0xFFFFFFFFFFFFFFFFL
        u_val64_3 = 9223372036854775808L
        u_val64_4 = 9223372036854775807L
        writer.build("32u 32u 32u 32u 64U 64U 64U 64U",
                     [u_val_1, u_val_2, u_val_3, u_val_4,
                      u_val64_1, u_val64_2, u_val64_3, u_val64_4])
        validate_writer(writer, temp)

        #try the signed values via build()
        (writer, temp) = get_writer()
        s_val_1 = 0
        s_val_2 = -1
        s_val_3 = -2147483648
        s_val_4 = 2147483647
        s_val64_1 = 0
        s_val64_2 = -1
        s_val64_3 = -9223372036854775808L
        s_val64_4 = 9223372036854775807L
        writer.build("32s 32s 32s 32s 64S 64S 64S 64S",
                     [s_val_1, s_val_2, s_val_3, s_val_4,
                      s_val64_1, s_val64_2, s_val64_3, s_val64_4])
        validate_writer(writer, temp)

    def __get_edge_writer_be__(self):
        from audiotools.bitstream import BitstreamWriter

        temp_file = tempfile.NamedTemporaryFile()
        return (BitstreamWriter(open(temp_file.name, "wb"), 0), temp_file)

    def __validate_edge_writer_be__(self, writer, temp_file):
        writer.close()

        self.assertEqual(open(temp_file.name, "rb").read(),
                         "".join(map(chr,
                                     [0, 0, 0, 0, 255, 255, 255, 255,
                                      128, 0, 0, 0, 127, 255, 255, 255,
                                      0, 0, 0, 0, 0, 0, 0, 0,
                                      255, 255, 255, 255, 255, 255, 255, 255,
                                      128, 0, 0, 0, 0, 0, 0, 0,
                                      127, 255, 255, 255, 255, 255, 255, 255])))

        temp_file.close()

    def __get_edge_recorder_be__(self):
        from audiotools.bitstream import BitstreamRecorder

        return (BitstreamRecorder(0), tempfile.NamedTemporaryFile())

    def __validate_edge_recorder_be__(self, writer, temp_file):
        from audiotools.bitstream import BitstreamWriter

        writer2 = BitstreamWriter(open(temp_file.name, "wb"), 0)
        writer.copy(writer2)
        writer2.close()

        self.assertEqual(open(temp_file.name, "rb").read(),
                         "".join(map(chr,
                                     [0, 0, 0, 0, 255, 255, 255, 255,
                                      128, 0, 0, 0, 127, 255, 255, 255,
                                      0, 0, 0, 0, 0, 0, 0, 0,
                                      255, 255, 255, 255, 255, 255, 255, 255,
                                      128, 0, 0, 0, 0, 0, 0, 0,
                                      127, 255, 255, 255, 255, 255, 255, 255])))

        temp_file.close()

    def __get_edge_accumulator_be__(self):
        from audiotools.bitstream import BitstreamAccumulator

        return (BitstreamAccumulator(0), None)

    def __validate_edge_accumulator_be__(self, writer, temp_file):
        self.assertEqual(writer.bits(), 48 * 8)


    def __get_edge_writer_le__(self):
        from audiotools.bitstream import BitstreamWriter

        temp_file = tempfile.NamedTemporaryFile()
        return (BitstreamWriter(open(temp_file.name, "wb"), 1), temp_file)

    def __validate_edge_writer_le__(self, writer, temp_file):
        writer.close()

        self.assertEqual(open(temp_file.name, "rb").read(),
                         "".join(map(chr,
                                     [0, 0, 0, 0, 255, 255, 255, 255,
                                      0, 0, 0, 128, 255, 255, 255, 127,
                                      0, 0, 0, 0, 0, 0, 0, 0,
                                      255, 255, 255, 255, 255, 255, 255, 255,
                                      0, 0, 0, 0, 0, 0, 0, 128,
                                      255, 255, 255, 255, 255, 255, 255, 127])))

        temp_file.close()

    def __get_edge_recorder_le__(self):
        from audiotools.bitstream import BitstreamRecorder

        return (BitstreamRecorder(1), tempfile.NamedTemporaryFile())

    def __validate_edge_recorder_le__(self, writer, temp_file):
        from audiotools.bitstream import BitstreamWriter

        writer2 = BitstreamWriter(open(temp_file.name, "wb"), 1)
        writer.copy(writer2)
        writer2.close()

        self.assertEqual(open(temp_file.name, "rb").read(),
                         "".join(map(chr,
                                     [0, 0, 0, 0, 255, 255, 255, 255,
                                      0, 0, 0, 128, 255, 255, 255, 127,
                                      0, 0, 0, 0, 0, 0, 0, 0,
                                      255, 255, 255, 255, 255, 255, 255, 255,
                                      0, 0, 0, 0, 0, 0, 0, 128,
                                      255, 255, 255, 255, 255, 255, 255, 127])))

        temp_file.close()

    def __get_edge_accumulator_le__(self):
        from audiotools.bitstream import BitstreamAccumulator

        return (BitstreamAccumulator(1), None)

    def __validate_edge_accumulator_le__(self, writer, temp_file):
        self.assertEqual(writer.bits(), 48 * 8)

    def __test_writer__(self, endianness):
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        checks = [self.__writer_perform_write__,
                  self.__writer_perform_write_signed__,
                  self.__writer_perform_write_64__,
                  self.__writer_perform_write_signed_64__,
                  self.__writer_perform_write_unary_0__,
                  self.__writer_perform_write_unary_1__]

        #perform file-based checks
        for check in checks:
            temp = tempfile.NamedTemporaryFile()
            try:
                writer = BitstreamWriter(open(temp.name, "wb"), endianness)
                check(writer, endianness)
                writer.close()
                self.__check_output_file__(temp)
            finally:
                temp.close()

            data = cStringIO.StringIO()
            writer = BitstreamWriter(data, endianness)
            check(writer, endianness)
            del(writer)
            self.assertEqual(data.getvalue(), "\xB1\xED\x3B\xC1")

        #perform recorder-based checks
        for check in checks:
            temp = tempfile.NamedTemporaryFile()
            try:
                writer = BitstreamWriter(open(temp.name, "wb"), endianness)
                recorder = BitstreamRecorder(endianness)
                check(recorder, endianness)
                recorder.copy(writer)
                writer.close()
                self.__check_output_file__(temp)
                self.assertEqual(recorder.bits(), 32)
            finally:
                temp.close()

        #perform accumulator-based checks
        for check in checks:
            writer = BitstreamAccumulator(endianness)
            check(writer, endianness)
            self.assertEqual(writer.bits(), 32)

        #check swap records
        temp = tempfile.NamedTemporaryFile()
        try:
            writer = BitstreamWriter(open(temp.name, "wb"), endianness)
            recorder1 = BitstreamRecorder(endianness)
            recorder2 = BitstreamRecorder(endianness)
            recorder2.write(8, 0xB1)
            recorder2.write(8, 0xED)
            recorder1.write(8, 0x3B)
            recorder1.write(8, 0xC1)
            recorder1.swap(recorder2)
            recorder1.copy(writer)
            recorder2.copy(writer)
            writer.close()
            self.__check_output_file__(temp)
        finally:
            temp.close()

        #check recorder reset
        temp = tempfile.NamedTemporaryFile()
        try:
            writer = BitstreamWriter(open(temp.name, "wb"), endianness)
            recorder = BitstreamRecorder(endianness)
            recorder.write(8, 0xAA)
            recorder.write(8, 0xBB)
            recorder.write(8, 0xCC)
            recorder.write(8, 0xDD)
            recorder.write(8, 0xEE)
            recorder.reset()
            recorder.write(8, 0xB1)
            recorder.write(8, 0xED)
            recorder.write(8, 0x3B)
            recorder.write(8, 0xC1)
            recorder.copy(writer)
            writer.close()
            self.__check_output_file__(temp)
        finally:
            temp.close()

        #check endianness setting
        #FIXME

        #check a file-based byte-align
        #FIXME

        #check a recorder-based byte-align
        #FIXME

        #check an accumulator-based byte-align
        #FIXME

        #check a partial dump
        #FIXME

        #check that recorder->recorder->file works
        for check in checks:
            temp = tempfile.NamedTemporaryFile()
            try:
                writer = BitstreamWriter(open(temp.name, "wb"), endianness)
                recorder1 = BitstreamRecorder(endianness)
                recorder2 = BitstreamRecorder(endianness)
                self.assertEqual(recorder1.bits(), 0)
                self.assertEqual(recorder2.bits(), 0)
                check(recorder2, endianness)
                self.assertEqual(recorder1.bits(), 0)
                self.assertEqual(recorder2.bits(), 32)
                recorder2.copy(recorder1)
                self.assertEqual(recorder1.bits(), 32)
                self.assertEqual(recorder2.bits(), 32)
                recorder1.copy(writer)
                writer.close()
                self.__check_output_file__(temp)
            finally:
                temp.close()

        #check that recorder->accumulator works
        for check in checks:
            recorder = BitstreamRecorder(endianness)
            accumulator = BitstreamAccumulator(endianness)
            self.assertEqual(recorder.bits(), 0)
            self.assertEqual(accumulator.bits(), 0)
            check(recorder, endianness)
            self.assertEqual(recorder.bits(), 32)
            self.assertEqual(accumulator.bits(), 0)
            recorder.copy(accumulator)
            self.assertEqual(recorder.bits(), 32)
            self.assertEqual(accumulator.bits(), 32)

    def __writer_perform_write__(self, writer, endianness):
        if (endianness == 0):
            writer.write(2, 2)
            writer.write(3, 6)
            writer.write(5, 7)
            writer.write(3, 5)
            writer.write(19, 342977)
        else:
            writer.write(2, 1)
            writer.write(3, 4)
            writer.write(5, 13)
            writer.write(3, 3)
            writer.write(19, 395743)

    def __writer_perform_write_signed__(self, writer, endianness):
        if (endianness == 0):
            writer.write_signed(2, -2)
            writer.write_signed(3, -2)
            writer.write_signed(5, 7)
            writer.write_signed(3, -3)
            writer.write_signed(19, -181311)
        else:
            writer.write_signed(2, 1)
            writer.write_signed(3, -4)
            writer.write_signed(5, 13)
            writer.write_signed(3, 3)
            writer.write_signed(19, -128545)

    def __writer_perform_write_64__(self, writer, endianness):
        if (endianness == 0):
            writer.write64(2, 2)
            writer.write64(3, 6)
            writer.write64(5, 7)
            writer.write64(3, 5)
            writer.write64(19, 342977)
        else:
            writer.write64(2, 1)
            writer.write64(3, 4)
            writer.write64(5, 13)
            writer.write64(3, 3)
            writer.write64(19, 395743)

    def __writer_perform_write_signed_64__(self, writer, endianness):
        if (endianness == 0):
            writer.write_signed64(2, -2)
            writer.write_signed64(3, -2)
            writer.write_signed64(5, 7)
            writer.write_signed64(3, -3)
            writer.write_signed64(19, -181311)
        else:
            writer.write_signed64(2, 1)
            writer.write_signed64(3, -4)
            writer.write_signed64(5, 13)
            writer.write_signed64(3, 3)
            writer.write_signed64(19, -128545)

    def __writer_perform_write_unary_0__(self, writer, endianness):
        if (endianness == 0):
            writer.unary(0, 1)
            writer.unary(0, 2)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.unary(0, 4)
            writer.unary(0, 2)
            writer.unary(0, 1)
            writer.unary(0, 0)
            writer.unary(0, 3)
            writer.unary(0, 4)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.write(1, 1)
        else:
            writer.unary(0, 1)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.unary(0, 2)
            writer.unary(0, 2)
            writer.unary(0, 2)
            writer.unary(0, 5)
            writer.unary(0, 3)
            writer.unary(0, 0)
            writer.unary(0, 1)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.unary(0, 0)
            writer.write(2, 3)

    def __writer_perform_write_unary_1__(self, writer, endianness):
        if (endianness == 0):
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 3)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 2)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 5)
        else:
            writer.unary(1, 0)
            writer.unary(1, 3)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 1)
            writer.unary(1, 0)
            writer.unary(1, 0)
            writer.unary(1, 2)
            writer.unary(1, 5)
            writer.unary(1, 0)

    def __check_output_file__(self, temp_file):
        self.assertEqual(open(temp_file.name, "rb").read(), "\xB1\xED\x3B\xC1")

    @LIB_CORE
    def test_edge_cases(self):
        from audiotools.bitstream import BitstreamReader

        temp = tempfile.NamedTemporaryFile()
        try:
            #write the temp file with a set of known big-endian data
            temp.write("".join(map(chr,
                                   [0, 0, 0, 0, 255, 255, 255, 255,
                                    128, 0, 0, 0, 127, 255, 255, 255,
                                    0, 0, 0, 0, 0, 0, 0, 0,
                                    255, 255, 255, 255, 255, 255, 255, 255,
                                    128, 0, 0, 0, 0, 0, 0, 0,
                                    127, 255, 255, 255, 255, 255, 255, 255])))
            temp.flush()

            #ensure a big-endian reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), 0)
            self.__test_edge_reader_be__(reader)
            del(reader)

            #ensure a big-endian sub-reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), 0)
            subreader = reader.substream(48)
            self.__test_edge_reader_be__(subreader)
        finally:
            temp.close()

        temp = tempfile.NamedTemporaryFile()
        try:
            #write the temp file with a collection of known little-endian data
            temp.write("".join(map(chr,
                                   [0, 0, 0, 0, 255, 255, 255, 255,
                                    0, 0, 0, 128, 255, 255, 255, 127,
                                    0, 0, 0, 0, 0, 0, 0, 0,
                                    255, 255, 255, 255, 255, 255, 255, 255,
                                    0, 0, 0, 0, 0, 0, 0, 128,
                                    255, 255, 255, 255, 255, 255, 255, 127])))
            temp.flush()

            #ensure a little-endian reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), 1)
            self.__test_edge_reader_le__(reader)
            del(reader)

            #ensure a little-endian sub-reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), 1)
            subreader = reader.substream(48)
            self.__test_edge_reader_be__(subreader)
        finally:
            temp.close()

        #test a bunch of big-endian values via the bitstream writer
        self.__test_edge_writer__(self.__get_edge_writer_be__,
                                  self.__validate_edge_writer_be__)

        #test a bunch of big-endian values via the bitstream recorder
        self.__test_edge_writer__(self.__get_edge_recorder_be__,
                                  self.__validate_edge_recorder_be__)

        #test a bunch of big-endian values via the bitstream accumulator
        self.__test_edge_writer__(self.__get_edge_accumulator_be__,
                                  self.__validate_edge_accumulator_be__)

        #test a bunch of little-endian values via the bitstream writer
        self.__test_edge_writer__(self.__get_edge_writer_le__,
                                  self.__validate_edge_writer_le__)

        #test a bunch of little-endian values via the bitstream recorder
        self.__test_edge_writer__(self.__get_edge_recorder_le__,
                                  self.__validate_edge_recorder_le__)

        #test a bunch of little-endian values via the bitstream accumulator
        self.__test_edge_writer__(self.__get_edge_accumulator_le__,
                                  self.__validate_edge_accumulator_le__)

    @LIB_CORE
    def test_python_reader(self):
        from audiotools.bitstream import BitstreamReader

        #Vanilla, file-based BitstreamReader uses a 1 character buffer
        #and relies on stdio to perform buffering which is fast enough.
        #Therefore, a byte-aligned file can be seek()ed at will.
        #However, making lots of read(1) calls on a Python object
        #is unacceptably slow.
        #Therefore, we read a 4KB string and pull individual bytes from
        #it as needed, which should keep performance reasonable.
        def new_temp1():
            temp = cStringIO.StringIO()
            temp.write(chr(0xB1))
            temp.write(chr(0xED))
            temp.write(chr(0x3B))
            temp.write(chr(0xC1))
            temp.seek(0, 0)
            return temp

        def new_temp2():
            return __SimpleChunkReader__([chr(0xB1) +
                                          chr(0xED) +
                                          chr(0x3B) +
                                          chr(0xC1)])

        def new_temp3():
            return __SimpleChunkReader__([chr(0xB1) +
                                          chr(0xED),
                                          chr(0x3B) +
                                          chr(0xC1)])

        def new_temp4():
            return __SimpleChunkReader__([chr(0xB1),
                                          chr(0xED),
                                          chr(0x3B) +
                                          chr(0xC1)])
        def new_temp5():
            return __SimpleChunkReader__([chr(0xB1),
                                          chr(0xED),
                                          chr(0x3B),
                                          chr(0xC1)])

        for new_temp in [new_temp1, new_temp2, new_temp3, new_temp4,
                         new_temp5]:
            #first, check the bitstream reader
            #against some simple known big-endian values
            bitstream = BitstreamReader(new_temp(), 0)

            self.assertEqual(bitstream.read(2), 2)
            self.assertEqual(bitstream.read(3), 6)
            self.assertEqual(bitstream.read(5), 7)
            self.assertEqual(bitstream.read(3), 5)
            self.assertEqual(bitstream.read(19), 342977)

            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.read64(2), 2)
            self.assertEqual(bitstream.read64(3), 6)
            self.assertEqual(bitstream.read64(5), 7)
            self.assertEqual(bitstream.read64(3), 5)
            self.assertEqual(bitstream.read64(19), 342977)

            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.read_signed(2), -2)
            self.assertEqual(bitstream.read_signed(3), -2)
            self.assertEqual(bitstream.read_signed(5), 7)
            self.assertEqual(bitstream.read_signed(3), -3)
            self.assertEqual(bitstream.read_signed(19), -181311)

            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.unary(0), 1)
            self.assertEqual(bitstream.unary(0), 2)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 4)
            bitstream.byte_align()
            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 1)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 3)
            self.assertEqual(bitstream.unary(1), 0)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.read(1), 1)
            bit = bitstream.read(1)
            self.assertEqual(bit, 0)
            bitstream.unread(bit)
            self.assertEqual(bitstream.read(2), 1)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.read(8), 0xB1)
            bitstream.unread(0)
            self.assertEqual(bitstream.read(1), 0)
            bitstream.unread(1)
            self.assertEqual(bitstream.read(1), 1)

            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.limited_unary(0, 2), 1)
            self.assertEqual(bitstream.limited_unary(0, 2), None)
            bitstream.byte_align()
            bitstream = BitstreamReader(new_temp(), 0)
            self.assertEqual(bitstream.limited_unary(1, 2), 0)
            self.assertEqual(bitstream.limited_unary(1, 2), 1)
            self.assertEqual(bitstream.limited_unary(1, 2), 0)
            self.assertEqual(bitstream.limited_unary(1, 2), None)

            bitstream = BitstreamReader(new_temp(), 0)
            bitstream.mark()
            self.assertEqual(bitstream.read(4), 0xB)
            bitstream.rewind()
            self.assertEqual(bitstream.read(8), 0xB1)
            bitstream.rewind()
            self.assertEqual(bitstream.read(12), 0xB1E)
            bitstream.unmark()
            bitstream.mark()
            self.assertEqual(bitstream.read(4), 0xD)
            bitstream.rewind()
            self.assertEqual(bitstream.read(8), 0xD3)
            bitstream.rewind()
            self.assertEqual(bitstream.read(12), 0xD3B)
            bitstream.unmark()

            del(bitstream)
            bitstream = BitstreamReader(new_temp(), 0)

            #then, check the bitstream reader
            #against some simple known little-endian values
            bitstream = BitstreamReader(new_temp(), 1)

            self.assertEqual(bitstream.read(2), 1)
            self.assertEqual(bitstream.read(3), 4)
            self.assertEqual(bitstream.read(5), 13)
            self.assertEqual(bitstream.read(3), 3)
            self.assertEqual(bitstream.read(19), 395743)

            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.read64(2), 1)
            self.assertEqual(bitstream.read64(3), 4)
            self.assertEqual(bitstream.read64(5), 13)
            self.assertEqual(bitstream.read64(3), 3)
            self.assertEqual(bitstream.read64(19), 395743)

            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.read_signed(2), 1)
            self.assertEqual(bitstream.read_signed(3), -4)
            self.assertEqual(bitstream.read_signed(5), 13)
            self.assertEqual(bitstream.read_signed(3), 3)
            self.assertEqual(bitstream.read_signed(19), -128545)

            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.unary(0), 1)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 2)
            self.assertEqual(bitstream.unary(0), 2)
            bitstream.byte_align()
            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 3)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 1)
            self.assertEqual(bitstream.unary(1), 0)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.read(1), 1)
            bit = bitstream.read(1)
            self.assertEqual(bit, 0)
            bitstream.unread(bit)
            self.assertEqual(bitstream.read(4), 8)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.read(8), 0xB1)
            bitstream.unread(0)
            self.assertEqual(bitstream.read(1), 0)
            bitstream.unread(1)
            self.assertEqual(bitstream.read(1), 1)

            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.limited_unary(0, 2), 1)
            self.assertEqual(bitstream.limited_unary(0, 2), 0)
            self.assertEqual(bitstream.limited_unary(0, 2), 0)
            self.assertEqual(bitstream.limited_unary(0, 2), None)
            bitstream.byte_align()
            bitstream = BitstreamReader(new_temp(), 1)
            self.assertEqual(bitstream.limited_unary(1, 2), 0)
            self.assertEqual(bitstream.limited_unary(1, 2), None)

            bitstream = BitstreamReader(new_temp(), 1)
            bitstream.mark()
            self.assertEqual(bitstream.read(4), 0x1)
            bitstream.rewind()
            self.assertEqual(bitstream.read(8), 0xB1)
            bitstream.rewind()
            self.assertEqual(bitstream.read(12), 0xDB1)
            bitstream.unmark()
            bitstream.mark()
            self.assertEqual(bitstream.read(4), 0xE)
            bitstream.rewind()
            self.assertEqual(bitstream.read(8), 0xBE)
            bitstream.rewind()
            self.assertEqual(bitstream.read(12), 0x3BE)
            bitstream.unmark()


    @LIB_CORE
    def test_simple_writer(self):
        from audiotools.bitstream import BitstreamWriter

        temp = tempfile.NamedTemporaryFile()
        try:
            #first, have the bitstream writer generate
            #a set of known big-endian values

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 0)
            bitstream.write(2, 2)
            bitstream.write(3, 6)
            bitstream.write(5, 7)
            bitstream.write(3, 5)
            bitstream.write(19, 342977)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 0)
            bitstream.write64(2, 2)
            bitstream.write64(3, 6)
            bitstream.write64(5, 7)
            bitstream.write64(3, 5)
            bitstream.write64(19, 342977)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 0)
            bitstream.write_signed(2, -2)
            bitstream.write_signed(3, -2)
            bitstream.write_signed(5, 7)
            bitstream.write_signed(3, -3)
            bitstream.write_signed(19, -181311)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 0)
            bitstream.unary(0, 1)
            bitstream.unary(0, 2)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.unary(0, 4)
            bitstream.unary(0, 2)
            bitstream.unary(0, 1)
            bitstream.unary(0, 0)
            bitstream.unary(0, 3)
            bitstream.unary(0, 4)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.write(1, 1)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 3)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 2)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 5)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            #then, have the bitstream writer generate
            #a set of known little-endian values
            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 1)
            bitstream.write(2, 1)
            bitstream.write(3, 4)
            bitstream.write(5, 13)
            bitstream.write(3, 3)
            bitstream.write(19, 395743)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 1)
            bitstream.write64(2, 1)
            bitstream.write64(3, 4)
            bitstream.write64(5, 13)
            bitstream.write64(3, 3)
            bitstream.write64(19, 395743)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 1)
            bitstream.write_signed(2, 1)
            bitstream.write_signed(3, -4)
            bitstream.write_signed(5, 13)
            bitstream.write_signed(3, 3)
            bitstream.write_signed(19, -128545)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 1)
            bitstream.unary(0, 1)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.unary(0, 2)
            bitstream.unary(0, 2)
            bitstream.unary(0, 2)
            bitstream.unary(0, 5)
            bitstream.unary(0, 3)
            bitstream.unary(0, 0)
            bitstream.unary(0, 1)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.unary(0, 0)
            bitstream.write(2, 3)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 3)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 1)
            bitstream.unary(1, 0)
            bitstream.unary(1, 0)
            bitstream.unary(1, 2)
            bitstream.unary(1, 5)
            bitstream.unary(1, 0)
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0xB1, 0xED, 0x3B, 0xC1])

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, 1)
            bitstream.write(4, 0x1)
            bitstream.byte_align()
            bitstream.write(4, 0xD)
            bitstream.byte_align()
            f.close()
            del(bitstream)
            self.assertEqual(map(ord, open(temp.name, "rb").read()),
                             [0x01, 0x0D])

        finally:
            temp.close()

    #and have the bitstream reader check those values are accurate

    @LIB_CORE
    def close_test(self):
        from audiotools.bitstream import BitstreamReader

        r1 = BitstreamReader(open("test.py", "rb"), False)
        r1.read(8)
        r1.close()
        self.assertRaises(IOError,
                          r1.read,
                          8)
        del(r1)

        r1 = BitstreamReader(cStringIO.StringIO("abcd"), False)
        r1.read(8)
        r1.close()
        self.assertRaises(IOError,
                          r1.read,
                          8)
        del(r1)


class TestReplayGain(unittest.TestCase):
    @LIB_CORE
    def test_basics(self):
        import audiotools.replaygain
        import audiotools.pcm

        #check for invalid sample rate
        self.assertRaises(ValueError,
                          audiotools.replaygain.ReplayGain,
                          200000)

        #check for invalid channel count
        rg = audiotools.replaygain.ReplayGain(44100)
        self.assertRaises(ValueError,
                          rg.update,
                          audiotools.pcm.from_list(range(20), 4, 16, True))

        #check for not enough samples
        rg.update(audiotools.pcm.from_list([1, 2], 2, 16, True))
        self.assertRaises(ValueError, rg.title_gain)
        self.assertRaises(ValueError, rg.album_gain)

        #check for no tracks
        gain = audiotools.calculate_replay_gain([])
        self.assertRaises(ValueError, list, gain)

        #check for lots of invalid combinations for calculate_replay_gain
        track_file1 = tempfile.NamedTemporaryFile(suffix=".wav")
        track_file2 = tempfile.NamedTemporaryFile(suffix=".wav")
        track_file3 = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            track1 = audiotools.WaveAudio.from_pcm(track_file1.name,
                                                   BLANK_PCM_Reader(2))
            track2 = audiotools.WaveAudio.from_pcm(track_file2.name,
                                                   BLANK_PCM_Reader(3))
            track3 = audiotools.WaveAudio.from_pcm(
                track_file3.name,
                BLANK_PCM_Reader(2, sample_rate=48000))

            gain = audiotools.calculate_replay_gain([track1, track2, track3])
            self.assertRaises(ValueError, list, gain)

            track3 = audiotools.WaveAudio.from_pcm(
                track_file3.name,
                BLANK_PCM_Reader(
                    2,
                    channels=4,
                    channel_mask=audiotools.ChannelMask.from_fields(
                        front_left=True,
                        front_right=True,
                        back_left=True,
                        back_right=True)))

            gain = audiotools.calculate_replay_gain([track1, track2, track3])
            self.assertRaises(ValueError, list, gain)

            track3 = audiotools.WaveAudio.from_pcm(
                track_file3.name,
                BLANK_PCM_Reader(
                    2,
                    sample_rate=48000,
                    channels=3,
                    channel_mask=audiotools.ChannelMask.from_fields(
                        front_left=True,
                        front_right=True,
                        front_center=True)))

            gain = audiotools.calculate_replay_gain([track1, track2, track3])
            self.assertRaises(ValueError, list, gain)

            track3 = audiotools.WaveAudio.from_pcm(
                track_file3.name,
                BLANK_PCM_Reader(2))

            gain = list(audiotools.calculate_replay_gain([track1, track2, track3]))
            self.assertEqual(len(gain), 3)
            self.assert_(gain[0][0] is track1)
            self.assert_(gain[1][0] is track2)
            self.assert_(gain[2][0] is track3)
        finally:
            track_file1.close()
            track_file2.close()
            track_file3.close()

    @LIB_CORE
    def test_valid_rates(self):
        import audiotools.replaygain

        for sample_rate in [8000, 11025, 12000, 16000, 18900, 22050, 24000,
                            32000, 37800, 44100, 48000, 56000, 64000, 88200,
                            96000, 112000, 128000, 144000, 176400, 192000]:
            gain = audiotools.replaygain.ReplayGain(sample_rate)
            reader = test_streams.Simple_Sine(sample_rate * 2,
                                              sample_rate,
                                              0x4,
                                              16,
                                              (30000, sample_rate / 100))
            audiotools.transfer_data(reader.read, gain.update)
            (gain, peak) = gain.title_gain()
            self.assert_(gain < -4.0)
            self.assert_(peak > .90)

    @LIB_CORE
    def test_reader(self):
        import audiotools.replaygain

        test_format = audiotools.WaveAudio

        dummy1 = tempfile.NamedTemporaryFile(suffix="." + test_format.SUFFIX)
        dummy2 = tempfile.NamedTemporaryFile(suffix="." + test_format.SUFFIX)
        try:
            #build dummy file
            track1 = test_format.from_pcm(
                dummy1.name,
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50,
                                           4410.0, 0.49, 1.0))

            #calculate its ReplayGain
            gain = audiotools.replaygain.ReplayGain(track1.sample_rate())
            pcm = track1.to_pcm()
            audiotools.transfer_data(pcm.read, gain.update)
            (gain, peak) = gain.title_gain()

            #apply gain to dummy file
            track2 = test_format.from_pcm(
                dummy2.name,
                audiotools.ReplayGainReader(track1.to_pcm(),
                                            gain,
                                            peak))

            #ensure gain applied is quieter than without gain applied
            gain2 = audiotools.replaygain.ReplayGain(track1.sample_rate())
            pcm = track2.to_pcm()
            audiotools.transfer_data(pcm.read, gain2.update)
            (gain2, peak2) = gain2.title_gain()

            self.assert_(gain2 > gain)
        finally:
            dummy1.close()
            dummy2.close()

    @LIB_CORE
    def test_applicable(self):
        #build a bunch of test tracks
        test_format = audiotools.WaveAudio

        temp_files = [tempfile.NamedTemporaryFile(
                suffix="." + test_format.SUFFIX)
                      for i in xrange(6)]

        try:
            track1 = test_format.from_pcm(temp_files[0].name,
                                          BLANK_PCM_Reader(1, 44100, 2, 16))

            track2 = test_format.from_pcm(temp_files[1].name,
                                          BLANK_PCM_Reader(2, 44100, 2, 16))

            track3 = test_format.from_pcm(temp_files[2].name,
                                          BLANK_PCM_Reader(3, 48000, 2, 16))

            track4 = test_format.from_pcm(temp_files[3].name,
                                          BLANK_PCM_Reader(4, 44100, 1, 16))

            track5 = test_format.from_pcm(temp_files[4].name,
                                          BLANK_PCM_Reader(5, 44100, 2, 24))

            track6 = test_format.from_pcm(temp_files[5].name,
                                          BLANK_PCM_Reader(6, 44100, 2, 16))


            #inconsistent sample rates aren't applicable
            self.assertEqual(audiotools.applicable_replay_gain([track1,
                                                                track2,
                                                                track3]),
                             False)

            #inconsistent channel counts aren't applicable
            self.assertEqual(audiotools.applicable_replay_gain([track1,
                                                                track2,
                                                                track4]),
                             False)

            #inconsistent bit-per-sample *are* applicable
            self.assertEqual(audiotools.applicable_replay_gain([track1,
                                                                track2,
                                                                track5]),
                             True)

            #consistent everything is applicable
            self.assertEqual(audiotools.applicable_replay_gain([track1,
                                                                track2,
                                                                track6]),
                             True)

        finally:
            for f in temp_files:
                f.close()


class TestXMCD(unittest.TestCase):
    XMCD_FILES = [(
"""eJyFk0tv20YQgO8B8h+m8MHJReXyTQFEm0pyYcAvSELTHCmKigRLYiHSanUTSdt1agd9BGnsOo3R
uGmcNn60AYrakfNjsqVinfwXOpS0KwRtEQKL2Zmd/WZ2ZjgFXzTs8tUrU5CsYsuyl6HSshoOuJWK
5/heOrEnH1EEthWJIClMkUVFJVwxVFFiiiIagswU1dAFlSmGomg6BxNd0TmbSBoaJpquEW2Sgqqo
ItdUQyCcT3RNV3kAYojKJBFREGRDm2gKmaQvipqs83uiLKmGwTVVJTqPJxqSYHBNEiRR4xEkkWij
KiQrW/NsqDvN2341DbKk8IO80655NbeJ1kRdarm243lOGUqdNNjlcqkMbZJSUuLSnAAZ97NOq3a7
6sM1+zoUfKftQMGuOq0KOD5Y9VSCKKyUGjXfR0S7ZqXhI7e5nGvaCUVIqaOw2dlCZjZrygoRKmWC
xmxxtjiXM2n0iIbHNDqk4elMfnGhOJvLw/vwlhkWafSygKuIS4L4YJsGezR49Xqne9l7ie9cJpe9
c0Teyt3Im1hn7Fz249xCPmcW3JVm2U8G6uqV4jCigCE3aPSMhj/T8DGNXtDwJFGjHvMg5s2q5cN0
yV3xodEBz7daH8CHM26r4TIf0UwuIyJ6zEwSgruMOgRHd2D4iOc0+gbfcXn+KP79fv/hbrz2PH74
HQ1+o8Ev7LZs3nTqtosjX3RhvgMzVjNTXylNe7CQVP895qeY8clq/85mfPb09fZ6fHcjfrX19+mP
/Z0w6zanfSg5ULd8h7mr//UWdqiZwxdgovdpuE+jTRqt4wamNOahm7S7dfHnGuLfPDsb7B/HZw+G
9e+u0e5dyMzT8HxUQriWt5rLFnzitJLZus4Ihtnf3ht8f2+wv3vx0xYvsWC+eRrQ4Cg+79EAS/Tt
MJNDGkXYHe5FTBoc0uBe/8GTi4NtbsbiJ7li2L+wbbiBObfteNBxV6DjWFVeLCKZ8dGX8dFOvLYa
9/YuNk75iWwW5gvxydeDH77CNPqHW9gdGoRJSsl4HdPwYJjSr6Mh4feUSeNhMZVJ8QN1coCowYsn
iKLBHzQ44C6a2V/dxRGmAcbEd29g/2mwipNMgx0abHJH/V2jxD2Nt6JiqYY8DLyOvwha+LwK/9tr
+LzmV5PxaLu2Vff4DfKuKv/rYu7TYtaE5CdMw+gvREtRMEeSjKU4ltJYymOpjKU6ltpY6mNpMA4H
MiJhSMKYhEEJoxKGJYxLGJgwssjIYkJemrtxazGfzeVx/w8vFHIR""".decode('base64').decode('zlib'),
                   4351, [150, 21035, 42561, 49623, 52904, 69806, 95578,
                         118580, 137118, 138717, 156562, 169014, 187866,
                         192523, 200497, 205135, 227486, 243699, 266182,
                         293092, 303273, 321761],
                   [('EXTT0', u''),
                    ('EXTT1', u''),
                    ('EXTT2', u''),
                    ('EXTT3', u''),
                    ('EXTT4', u''),
                    ('EXTT5', u''),
                    ('EXTT6', u''),
                    ('EXTT7', u''),
                    ('EXTT8', u''),
                    ('EXTT9', u''),
                    ('DTITLE', u'\u30de\u30af\u30ed\u30b9FRONTIER / \u30de\u30af\u30ed\u30b9F O\u30fbS\u30fbT\u30fb3 \u5a18\u305f\u307e\u2640\uff3bDisk1\uff3d'),
                    ('EXTT19', u''),
                    ('DYEAR', u'2008'),
                    ('DISCID', u'4510fd16'),
                    ('TTITLE20', u'\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3 #7 without vocals'),
                    ('TTITLE21', u'\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah! without vocals'),
                    ('EXTT18', u''),
                    ('EXTD', u' YEAR: 2008'),
                    ('EXTT12', u''),
                    ('EXTT13', u''),
                    ('EXTT10', u''),
                    ('DGENRE', u'Soundtrack'),
                    ('EXTT16', u''),
                    ('EXTT17', u''),
                    ('EXTT14', u''),
                    ('EXTT15', u''),
                    ('EXTT20', u''),
                    ('TTITLE9', u'\u661f\u9593\u98db\u884c'),
                    ('TTITLE8', u'\u300c\u8d85\u6642\u7a7a\u98ef\u5e97 \u5a18\u3005\u300d CM\u30bd\u30f3\u30b0 (Ranka Version)'),
                    ('TTITLE5', u"\u5c04\u624b\u5ea7\u2606\u5348\u5f8c\u4e5d\u6642Don't be late"),
                    ('TTITLE4', u"Welcome To My FanClub's Night!"),
                    ('TTITLE7', u'\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3 #7'),
                    ('TTITLE6', u"What 'bout my star?"),
                    ('TTITLE1', u"What 'bout my star? @Formo"),
                    ('TTITLE0', u'\u30c8\u30e9\u30a4\u30a2\u30f3\u30b0\u30e9\u30fc'),
                    ('TTITLE3', u'\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9\uff5e\u5c55\u671b\u516c\u5712\u306b\u3066'),
                    ('TTITLE2', u'\u30a2\u30a4\u30e2'),
                    ('TTITLE19', u'\u30a2\u30a4\u30e2\uff5e\u3053\u3044\u306e\u3046\u305f\uff5e'),
                    ('TTITLE18', u'\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9'),
                    ('EXTT21', u''),
                    ('EXTT11', u''),
                    ('TTITLE11', u'\u306d\u3053\u65e5\u8a18'),
                    ('TTITLE10', u'\u79c1\u306e\u5f7c\u306f\u30d1\u30a4\u30ed\u30c3\u30c8'),
                    ('TTITLE13', u'\u5b87\u5b99\u5144\u5f1f\u8239'),
                    ('TTITLE12', u'\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah!'),
                    ('TTITLE15', u'\u30a2\u30a4\u30e2 O.C.'),
                    ('TTITLE14', u'SMS\u5c0f\u968a\u306e\u6b4c\uff5e\u3042\u306e\u5a18\u306f\u30a8\u30a4\u30ea\u30a2\u30f3'),
                    ('TTITLE17', u'\u611b\u30fb\u304a\u307c\u3048\u3066\u3044\u307e\u3059\u304b'),
                    ('TTITLE16', u'\u30a2\u30a4\u30e2\uff5e\u9ce5\u306e\u3072\u3068'),
                    ('PLAYORDER', u'')],
                    [12280380, 12657288, 4152456, 1929228, 9938376, 15153936,
                     13525176, 10900344, 940212, 10492860, 7321776, 11084976,
                     2738316, 4688712, 2727144, 13142388, 9533244, 13220004,
                     15823080, 5986428, 10870944, 2687748]),
                  (
"""eJxNU9uOo0gMfZ6W+h8szcuM1OqhuBOpHpImnYnUlyhh5/JYASeUGqhMQbKTv19XcclKSDb28bF9
MJ/hb50X8JRCITqxFy3CQVZ4f/eZHsi0yD/goEWNoA6HFrt2RvFPLHCs8SOPGcdjLIqM48euHxgn
dJwkMU4Uu7F1Et/pMYw5SdjXu4Hj9DEv9qKwpw69yLde5Dpxn018P7RZl7HYtbWuG/mxbeX6bhTb
CjcMWRhbL46ixOI8h7k9s+fSTGzYLJVtDhU2x66cge8HAbSYq6Zoh/wWL7KVqpmBYYGNVjm2LRaw
v84gL4p9ARf2GDy6mxcHntTpquWx7OBL/hV2HV4QdnmJ+gDYgageDcXuvK9l1xHFRYoZKY5/gRj6
gdL17mmdcpf2CwNGy6TZOntZ8vcG/zkR47mQqoVv8AsbdUShW3gx/Qj3eznfctqMpEhXy7ftkq/o
a93fZZbA4RuNtWpkR7uMQcZXWpSHB5q7+XNGrTR9XEiF/mhoxxHl8sw2olRX0j4dvTzAd4p1U3CD
6lRNzTz+LDTM/xVXo1ct2ynj89cr/JBVJY4I6xbezvUeNdB2IyLguxIvonuwvD9lU4Bs4UlUlWyO
IyjkO3qjZ+y/wqareviIiYhIkMzawAxmebTwVKOop+Vioyz8LBUshMYWnkVzbGHewUpNTAlfmIMw
xTsUIGikZ6mniZlDneTJpivEkwVsSWx925sxvtDqAxt4lZp0nuIu7+e5qavVbU/m8YyCi+qM5he8
YIW3Up+/550y8r2iroWc5mWBrcqIuD1rs53MS5KwaVQHC9ND0cFP6JD/IHXxSjgk9P9lXyh9w0V0
UJS0etojANlY9Ju9+N3HdYLGdoB5dSp7ud5rPIopm/B10ylY0rdpRNWLdn+3/JWlHMwVz6A/Y4pk
Du8tG6w7WG+w/mCDwYaDjQYbDzYZeSbCkZGNlGzkZCMpG1nZSMtGXjYSM8O8eZn/ft+myy35/wHM
D3PD""".decode('base64').decode('zlib'),
                   4455, [150, 14731, 31177, 48245, 60099, 78289, 94077,
                          110960, 125007, 138376, 156374, 172087, 194466,
                          211820, 227485, 242784, 266168, 287790, 301276,
                          320091],
                   [('EXTT0', u''), ('EXTT1', u''), ('EXTT2', u''),
                    ('EXTT3', u''), ('EXTT4', u''), ('EXTT5', u''),
                    ('EXTT6', u''), ('EXTT7', u''), ('EXTT8', u''),
                    ('EXTT9', u''),
                    ('DTITLE', u'OneUp Studios / Xenogears Light'),
                    ('EXTT19', u''), ('DYEAR', u'2005'),
                    ('DISCID', u'22116514'), ('EXTT18', u''),
                    ('EXTD', u' YEAR: 2005'), ('EXTT12', u''),
                    ('EXTT13', u''), ('EXTT10', u''), ('DGENRE', u'Game'),
                    ('EXTT16', u''), ('EXTT17', u''), ('EXTT14', u''),
                    ('EXTT15', u''),
                    ('TTITLE9', u'Bonds of Sea and Fire'),
                    ('TTITLE8', u'One Who Bares Fangs At God'),
                    ('TTITLE5', u'Shevat, the Wind is Calling'),
                    ('TTITLE4', u'My Village Is Number One'),
                    ('TTITLE7', u'Shattering the Egg of Dreams'),
                    ('TTITLE6', u'Singing of the Gentle Wind'),
                    ('TTITLE1', u'Grahf, Conqueror of Darkness'),
                    ('TTITLE0', u'Premonition'),
                    ('TTITLE3', u'Far Away Promise'),
                    ('TTITLE2', u'Tears of the Stars, Hearts of the People'),
                    ('TTITLE19', u'Into Eternal Sleep'),
                    ('TTITLE18', u'The Alpha and Omega'),
                    ('EXTT11', u''),
                    ('TTITLE11', u'Broken Mirror'),
                    ('TTITLE10', u'Ship of Sleep and Remorse'),
                    ('TTITLE13', u'The Blue Traveler'),
                    ('TTITLE12', u'Dreams of the Strong'),
                    ('TTITLE15', u'The Treasure Which Cannot Be Stolen'),
                    ('TTITLE14', u'October Mermaid'),
                    ('TTITLE17', u'Gathering Stars in the Night Sky'),
                    ('TTITLE16', u'Valley Where the Wind is Born'),
                    ('PLAYORDER', u'')],
                   [8573628, 9670248, 10035984, 6970152, 10695720, 9283344,
                    9927204, 8259636, 7860972, 10582824, 9239244, 13158852,
                    10204152, 9211020, 8995812, 13749792, 12713736, 7929768,
                    11063220, 8289036]),
                  (
"""eJxdUU1v00AQvVfqf5iqF5BoajuO7UTag5OY1lI+KtsN5OjYm8ZKYke2k5JLhW3EoYA4gjiAxNeh
iCKEQCAi8WMWqt76F1i3touwbL95s2/fzsxuwr2pZa+vbUL6Gb5pjWHom1MM3nAY4DCopfn0YStM
EVbLjJgTnpWqBRGYKlPOiSjxbEHoFqFaGDBVSbxmnMALUsF4XhAKQ1bgK9f2rChy/5YhsqKU1950
Agsm2D0IRzXgJKlY0PDCCRzPpdmU7vmehYMA2zBY1sCy7YENC7ZUKXF7LQYa3mzpOwejEG5YN0EP
8QKDbo2wPwQcgjkppRb6fDB1wpBaLByzBnXPHSuulbowpezYpqo31CYyJWbAC4xFE4ZqtBTUM33H
mwcg+6EThAFsQ32CTWsExghDHQchNJpU3FdkDXEMI9B4R+loCpJdZ4rX14xLGwZ1Nbmzo8DVfxsu
VsdHJH5N4h8k/kWSk8vg01GuZ5HmYBjOqbLlDDE4AcUxBpPWboa5ikO73bYCbbmpwJ/Tb2fPnlI9
ib+S5AuJP5LkHUlWF6uIvvmOMtrvKdqh509sKm1uhdhyvfSEXMAjkrxP9yfHqVf0k0QPSfTk7Pmr
XFFB+tjzZuC5oHtTPPDsJVWOzNlsOcPebFJYCWhX3dkF07WhTQOjD41uq6tR8e/v989XJyQ6PT/+
nKtF1N9X03bV20qek5A+d3V6jfqhE4zSepKXJH5Lkhe0MTqxXFdFdUU2oKHt63QUmk6VRreTnnnr
PyzmyyASPaCNkTimdZDoMYkekTjteVfuyHW1ELIovaD4A0kikryh6+1uT+1sbKyvKXeNJtJ7dxpb
Is+xl9xg0BWyGXIZljPkM6xkKGQoZihlWM19CsPUca8l97sa7ZDGfwEBGThn""".decode('base64').decode('zlib'),
                   2888, [150, 19307, 41897, 60903, 78413, 93069, 109879,
                          126468, 144667, 164597, 177250, 197178],
                   [('EXTT0', u''), ('EXTT1', u''), ('EXTT2', u''),
                    ('EXTT3', u''), ('EXTT4', u''), ('EXTT5', u''),
                    ('EXTT6', u''), ('EXTT7', u''), ('EXTT8', u''),
                    ('EXTT9', u''),
                    ('DTITLE', u'Various Artists / Bleach The Best CD'),
                    ('DYEAR', u'2006'), ('DISCID', u'a80b460c'),
                    ('EXTD', u'SVWC-7421'), ('EXTT10', u''),
                    ('DGENRE', u'Anime'),
                    ('TTITLE9', u'BEAT CRUSADERS / TONIGHT,TONIGHT,TONIGHT'),
                    ('TTITLE8', u'SunSet Swish / \u30de\u30a4\u30da\u30fc\u30b9'),
                    ('TTITLE5', u'Skoop on Somebody / happypeople'),
                    ('TTITLE4', u'\u30e6\u30f3\u30ca / \u307b\u3046\u304d\u661f'),
                    ('TTITLE7', u'YUI / LIFE'),
                    ('TTITLE6', u'HIGH and MIGHTY COLOR / \u4e00\u8f2a\u306e\u82b1'),
                    ('TTITLE1', u'Rie fu / Life is Like a Boat'),
                    ('TTITLE0', u'ORANGE RANGE / \uff0a~\u30a2\u30b9\u30bf\u30ea\u30b9\u30af~'),
                    ('TTITLE3', u'UVERworld / D-tecnoLife'),
                    ('TTITLE2', u'HOME MADE \u5bb6\u65cf / \u30b5\u30f3\u30ad\u30e5\u30fc\uff01\uff01'),
                    ('EXTT11', u''),
                    ('TTITLE11', u'\u30bf\u30ab\u30c1\u30e3 / MOVIN!!'),
                    ('TTITLE10', u'\u3044\u304d\u3082\u306e\u304c\u304b\u308a / HANABI'),
                    ('PLAYORDER', u'')],
                   [11264316, 13282920, 11175528, 10295880, 8617728, 9884280,
                    9754332, 10701012, 11718840, 7439964, 11717664, 11446596])]

    @LIB_CORE
    def testroundtrip(self):
        for (data, length, offsets, items, track_lengths) in self.XMCD_FILES:
            f = tempfile.NamedTemporaryFile(suffix=".xmcd")
            try:
                f.write(data)
                f.flush()
                f.seek(0, 0)

                #check that reading in an XMCD file matches
                #its expected values
                xmcd = audiotools.XMCD.from_string(f.read())
                # self.assertEqual(length, xmcd.length)
                # self.assertEqual(offsets, xmcd.offsets)
                for (pair1, pair2) in zip(sorted(items),
                                          sorted(xmcd.fields.items())):
                    self.assertEqual(pair1, pair2)
                #self.assertEqual(dict(items),dict(xmcd.items()))

                #check that building an XMCD file from values
                #and reading it back in results in the same values
                f2 = tempfile.NamedTemporaryFile(suffix=".xmcd")
                try:
                    f2.write(xmcd.to_string())
                    f2.flush()
                    f2.seek(0, 0)

                    xmcd2 = audiotools.XMCD.from_string(f2.read())
                    # self.assertEqual(length, xmcd2.length)
                    # self.assertEqual(offsets, xmcd2.offsets)
                    for (pair1, pair2) in zip(sorted(items),
                                              sorted(xmcd2.fields.items())):
                        self.assertEqual(pair1, pair2)
                    # self.assertEqual(xmcd.length, xmcd2.length)
                    # self.assertEqual(xmcd.offsets, xmcd2.offsets)
                    self.assertEqual(dict(xmcd.fields.items()),
                                     dict(xmcd2.fields.items()))
                finally:
                    f2.close()
            finally:
                f.close()

    @LIB_CORE
    def testtracktagging(self):
        for (data, length, offsets, items, track_lengths) in self.XMCD_FILES:
            f = tempfile.NamedTemporaryFile(suffix=".xmcd")
            try:
                f.write(data)
                f.flush()
                f.seek(0, 0)

                xmcd = audiotools.XMCD.from_string(f.read())

                #build a bunch of temporary FLAC files from the track_lengths
                temp_files = [tempfile.NamedTemporaryFile(suffix=".flac")
                              for track_length in track_lengths]
                try:
                    temp_tracks = [audiotools.FlacAudio.from_pcm(
                            temp_file.name,
                            EXACT_BLANK_PCM_Reader(track_length),
                            "1")
                                   for (track_length, temp_file) in
                                   zip(track_lengths, temp_files)]

                    for i in xrange(len(track_lengths)):
                        temp_tracks[i].set_metadata(
                            audiotools.MetaData(track_number=i + 1))

                    #tag them with metadata from XMCD
                    for track in temp_tracks:
                        track.set_metadata(xmcd.track_metadata(
                                track.track_number()))

                    #build a new XMCD file from track metadata
                    xmcd2 = audiotools.XMCD.from_tracks(temp_tracks)

                    #check that the original XMCD values match the track ones
                    # self.assertEqual(xmcd.length, xmcd2.length)
                    # self.assertEqual(xmcd.offsets, xmcd2.offsets)
                    self.assertEqual(xmcd.fields['DISCID'],
                                     xmcd2.fields['DISCID'])
                    if (len([pair for pair in xmcd.fields.items()
                             if (pair[0].startswith('TTITLE') and
                                 (u" / " in pair[1]))]) > 0):
                        self.assertEqual(
                            xmcd.fields['DTITLE'].split(' / ', 1)[1],
                            xmcd2.fields['DTITLE'].split(' / ', 1)[1])
                    else:
                        self.assertEqual(xmcd.fields['DTITLE'],
                                         xmcd2.fields['DTITLE'])
                    self.assertEqual(xmcd.fields['DYEAR'],
                                     xmcd2.fields['DYEAR'])
                    for (pair1, pair2) in zip(
                        sorted([pair for pair in xmcd.fields.items()
                                if (pair[0].startswith('TTITLE'))]),
                        sorted([pair for pair in xmcd2.fields.items()
                                if (pair[0].startswith('TTITLE'))])):
                        self.assertEqual(pair1, pair2)
                finally:
                    for t in temp_files:
                        t.close()
            finally:
                f.close()

    @LIB_CORE
    def test_formatting(self):
        LENGTH = 1134
        OFFSETS = [150, 18740, 40778, 44676, 63267]

        #ensure that latin-1 and UTF-8 encodings are handled properly
        for (encoding, data) in zip(["ISO-8859-1", "UTF-8", "UTF-8"],
                                   [{"TTITLE0":u"track one",
                                     "TTITLE1":u"track two",
                                     "TTITLE2":u"track three",
                                     "TTITLE4":u"track four",
                                     "TTITLE5":u"track five"},
                                    {"TTITLE0":u"track \xf3ne",
                                     "TTITLE1":u"track two",
                                     "TTITLE2":u"track three",
                                     "TTITLE4":u"track four",
                                     "TTITLE5":u"track five"},
                                    {"TTITLE0":u'\u30de\u30af\u30ed\u30b9',
                                     "TTITLE1":u"track tw\xf3",
                                     "TTITLE2":u"track three",
                                     "TTITLE4":u"track four",
                                     "TTITLE5":u"track five"}]):
            # xmcd = audiotools.XMCD(data, OFFSETS, LENGTH)
            xmcd = audiotools.XMCD(data, [u"# xmcd"])
            xmcd2 = audiotools.XMCD.from_string(xmcd.to_string())
            self.assertEqual(dict(xmcd.fields.items()),
                             dict(xmcd2.fields.items()))

            xmcdfile = tempfile.NamedTemporaryFile(suffix='.xmcd')
            try:
                xmcdfile.write(xmcd.to_string())
                xmcdfile.flush()
                xmcdfile.seek(0, 0)
                xmcd2 = audiotools.XMCD.from_string(xmcdfile.read())
                self.assertEqual(dict(xmcd.fields.items()),
                                 dict(xmcd2.fields.items()))
            finally:
                xmcdfile.close()

        #ensure that excessively long XMCD lines are wrapped properly
        xmcd = audiotools.XMCD({"TTITLE0": u"l" + (u"o" * 512) + u"ng title",
                                "TTITLE1": u"track two",
                                "TTITLE2": u"track three",
                                "TTITLE4": u"track four",
                                "TTITLE5": u"track five"},
                               [u"# xmcd"])
        xmcd2 = audiotools.XMCD.from_string(xmcd.to_string())
        self.assertEqual(dict(xmcd.fields.items()),
                         dict(xmcd2.fields.items()))
        self.assert_(max(map(len,
                             cStringIO.StringIO(xmcd.to_string()).readlines())) < 80)

        #ensure that UTF-8 multi-byte characters aren't split
        xmcd = audiotools.XMCD({"TTITLE0": u'\u30de\u30af\u30ed\u30b9' * 100,
                                "TTITLE1": u"a" + (u'\u30de\u30af\u30ed\u30b9' * 100),
                                "TTITLE2": u"ab" + (u'\u30de\u30af\u30ed\u30b9' * 100),
                                "TTITLE4": u"abc" + (u'\u30de\u30af\u30ed\u30b9' * 100),
                                "TTITLE5": u"track tw\xf3"},
                               [u"# xmcd"])

        xmcd2 = audiotools.XMCD.from_string(xmcd.to_string())
        self.assertEqual(dict(xmcd.fields.items()),
                         dict(xmcd2.fields.items()))
        self.assert_(max(map(len, cStringIO.StringIO(xmcd.to_string()))) < 80)

    @LIB_CORE
    def test_attrs(self):
        for (xmcd_data, attrs) in zip(
            self.XMCD_FILES,
            [{"album_name": u"\u30de\u30af\u30ed\u30b9F O\u30fbS\u30fbT\u30fb3 \u5a18\u305f\u307e\u2640\uff3bDisk1\uff3d",
              "artist_name": u"\u30de\u30af\u30ed\u30b9FRONTIER",
              "year": u"2008",
              "extra": u" YEAR: 2008"},
             {"album_name": u"Xenogears Light",
              "artist_name": u"OneUp Studios",
              "year": u"2005",
              "extra": u" YEAR: 2005"},
             {"album_name": u"Bleach The Best CD",
              "artist_name": u"Various Artists",
              "year": u"2006",
              "extra": u"SVWC-7421"}]):
            xmcd_file = audiotools.XMCD.from_string(xmcd_data[0])

            #first, check that attributes are retrieved properly
            for key in attrs.keys():
                self.assertEqual(getattr(xmcd_file, key),
                                 attrs[key])

        #then, check that setting attributes round-trip properly
        for xmcd_data in self.XMCD_FILES:
            for (attr, new_value) in [
                ("album_name", u"New Album"),
                ("artist_name", u"T\u00e9st N\u00e0me"),
                ("year", u"2010"),
                ("extra", u"Extra!" * 200)]:
                xmcd_file = audiotools.XMCD.from_string(xmcd_data[0])
                setattr(xmcd_file, attr, new_value)
                self.assertEqual(getattr(xmcd_file, attr), new_value)

        #finally, check that the file with set attributes
        #round-trips properly
        for xmcd_data in self.XMCD_FILES:
            for (attr, new_value) in [
                ("album_name", u"New Album" * 8),
                ("artist_name", u"T\u00e9st N\u00e0me" * 8),
                ("year", u"2010"),
                ("extra", u"Extra!" * 200)]:
                xmcd_file = audiotools.XMCD.from_string(xmcd_data[0])
                setattr(xmcd_file, attr, new_value)
                xmcd_file2 = audiotools.XMCD.from_string(
                    xmcd_file.to_string())
                self.assertEqual(getattr(xmcd_file2, attr), new_value)
                self.assertEqual(getattr(xmcd_file, attr),
                                 getattr(xmcd_file2, attr))

    @LIB_CORE
    def test_tracks(self):
        for (xmcd_data, tracks) in zip(
            self.XMCD_FILES,
            [[(u'\u30c8\u30e9\u30a4\u30a2\u30f3\u30b0\u30e9\u30fc',
               u'', u''),
              (u"What 'bout my star? @Formo",
               u'', u''),
              (u'\u30a2\u30a4\u30e2',
               u'', u''),
              (u'\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9\uff5e\u5c55\u671b\u516c\u5712\u306b\u3066',
               u'', u''),
              (u"Welcome To My FanClub's Night!",
               u'', u''),
              (u"\u5c04\u624b\u5ea7\u2606\u5348\u5f8c\u4e5d\u6642Don't be late",
               u'', u''),
              (u"What 'bout my star?",
               u'', u''),
              (u'\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3 #7',
               u'', u''),
              (u'\u300c\u8d85\u6642\u7a7a\u98ef\u5e97 \u5a18\u3005\u300d CM\u30bd\u30f3\u30b0 (Ranka Version)',
               u'', u''),
              (u'\u661f\u9593\u98db\u884c',
               u'', u''),
              (u'\u79c1\u306e\u5f7c\u306f\u30d1\u30a4\u30ed\u30c3\u30c8',
               u'', u''),
              (u'\u306d\u3053\u65e5\u8a18',
               u'', u''),
              (u'\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah!',
               u'', u''),
              (u'\u5b87\u5b99\u5144\u5f1f\u8239',
               u'', u''),
              (u'SMS\u5c0f\u968a\u306e\u6b4c\uff5e\u3042\u306e\u5a18\u306f\u30a8\u30a4\u30ea\u30a2\u30f3',
               u'', u''),
              (u'\u30a2\u30a4\u30e2 O.C.',
               u'', u''),
              (u'\u30a2\u30a4\u30e2\uff5e\u9ce5\u306e\u3072\u3068',
               u'', u''),
              (u'\u611b\u30fb\u304a\u307c\u3048\u3066\u3044\u307e\u3059\u304b',
               u'', u''),
              (u'\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9',
               u'', u''),
              (u'\u30a2\u30a4\u30e2\uff5e\u3053\u3044\u306e\u3046\u305f\uff5e',
               u'', u''),
              (u'\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3 #7 without vocals',
               u'', u''),
              (u'\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah! without vocals',
               u'', u'')],
             [(u'Premonition', u'', u''),
              (u'Grahf, Conqueror of Darkness', u'', u''),
              (u'Tears of the Stars, Hearts of the People',
               u'', u''),
              (u'Far Away Promise', u'', u''),
              (u'My Village Is Number One', u'', u''),
              (u'Shevat, the Wind is Calling', u'', u''),
              (u'Singing of the Gentle Wind', u'', u''),
              (u'Shattering the Egg of Dreams', u'', u''),
              (u'One Who Bares Fangs At God', u'', u''),
              (u'Bonds of Sea and Fire', u'', u''),
              (u'Ship of Sleep and Remorse', u'', u''),
              (u'Broken Mirror', u'', u''),
              (u'Dreams of the Strong', u'', u''),
              (u'The Blue Traveler', u'', u''),
              (u'October Mermaid', u'', u''),
              (u'The Treasure Which Cannot Be Stolen', u'', u''),
              (u'Valley Where the Wind is Born', u'', u''),
              (u'Gathering Stars in the Night Sky', u'', u''),
              (u'The Alpha and Omega', u'', u''),
              (u'Into Eternal Sleep', u'', u'')],
             [(u'\uff0a~\u30a2\u30b9\u30bf\u30ea\u30b9\u30af~',
               u'ORANGE RANGE', u''),
              (u'Life is Like a Boat', u'Rie fu', u''),
              (u'\u30b5\u30f3\u30ad\u30e5\u30fc\uff01\uff01',
               u'HOME MADE \u5bb6\u65cf', u''),
              (u'D-tecnoLife', u'UVERworld', u''),
              (u'\u307b\u3046\u304d\u661f', u'\u30e6\u30f3\u30ca', u''),
              (u'happypeople', u'Skoop on Somebody', u''),
              (u'\u4e00\u8f2a\u306e\u82b1', u'HIGH and MIGHTY COLOR', u''),
              (u'LIFE', u'YUI', u''),
              (u'\u30de\u30a4\u30da\u30fc\u30b9', u'SunSet Swish', u''),
              (u'TONIGHT,TONIGHT,TONIGHT', u'BEAT CRUSADERS', u''),
              (u'HANABI', u'\u3044\u304d\u3082\u306e\u304c\u304b\u308a', u''),
              (u'MOVIN!!', u'\u30bf\u30ab\u30c1\u30e3', u'')]]):
            xmcd_file = audiotools.XMCD.from_string(xmcd_data[0])

            #first, check that tracks are read properly
            for (i, data) in enumerate(tracks):
                self.assertEqual(data, xmcd_file.get_track(i))

            #then, check that setting tracks round-trip properly
            for i in xrange(len(tracks)):
                xmcd_file = audiotools.XMCD.from_string(xmcd_data[0])
                xmcd_file.set_track(i,
                                    u"Track %d" % (i),
                                    u"Art\u00ecst N\u00e4me" * 40,
                                    u"Extr\u00e5" * 40)
                self.assertEqual(xmcd_file.get_track(i),
                                 (u"Track %d" % (i),
                                  u"Art\u00ecst N\u00e4me" * 40,
                                  u"Extr\u00e5" * 40))

            #finally, check that a file with set tracks round-trips
            for i in xrange(len(tracks)):
                xmcd_file = audiotools.XMCD.from_string(xmcd_data[0])
                xmcd_file.set_track(i,
                                    u"Track %d" % (i),
                                    u"Art\u00ecst N\u00e4me" * 40,
                                    u"Extr\u00e5" * 40)
                xmcd_file2 = audiotools.XMCD.from_string(
                    xmcd_file.to_string())
                self.assertEqual(xmcd_file2.get_track(i),
                                 (u"Track %d" % (i),
                                  u"Art\u00ecst N\u00e4me" * 40,
                                  u"Extr\u00e5" * 40))
                self.assertEqual(xmcd_file.get_track(i),
                                 xmcd_file2.get_track(i))

    @LIB_CORE
    def test_from_tracks(self):
        track_files = [tempfile.NamedTemporaryFile() for i in xrange(5)]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    BLANK_PCM_Reader(1)) for track in track_files]
            metadatas = [
                audiotools.MetaData(track_name=u"Track Name",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=1,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 2",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=2,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 4",
                                    artist_name=u"Special Artist",
                                    album_name=u"Test Album 2",
                                    track_number=4,
                                    track_total=5,
                                    year=u"2009"),
                audiotools.MetaData(track_name=u"Track N\u00e1me 3",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=3,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 5" * 40,
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=5,
                                    track_total=5,
                                    year=u"2010")]
            for (track, metadata) in zip(tracks, metadatas):
                track.set_metadata(metadata)
                self.assertEqual(track.get_metadata(), metadata)
            xmcd = audiotools.XMCD.from_tracks(tracks)
            self.assertEqual(len(xmcd), 5)
            self.assertEqual(xmcd.album_name, u"Test Album")
            self.assertEqual(xmcd.artist_name, u"Album Artist")
            self.assertEqual(xmcd.year, u"2010")
            self.assertEqual(xmcd.catalog, u"")
            self.assertEqual(xmcd.extra, u"")

            #note that track 4 loses its intentionally malformed
            #album name and year during the round-trip
            for metadata in [
                audiotools.MetaData(track_name=u"Track Name",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=1,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 2",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=2,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 4",
                                    artist_name=u"Special Artist",
                                    album_name=u"Test Album",
                                    track_number=4,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track N\u00e1me 3",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=3,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 5" * 40,
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=5,
                                    track_total=5,
                                    year=u"2010")]:
                self.assertEqual(metadata,
                                 xmcd.track_metadata(metadata.track_number))
        finally:
            for track in track_files:
                track.close()

    @LIB_CORE
    def test_from_cuesheet(self):
        CUESHEET = """REM DISCID 4A03DD06
PERFORMER "Unknown Artist"
TITLE "Unknown Title"
FILE "cue.wav" WAVE
  TRACK 01 AUDIO
    TITLE "Track01"
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    TITLE "Track02"
    INDEX 00 03:00:21
    INDEX 01 03:02:21
  TRACK 03 AUDIO
    TITLE "Track03"
    INDEX 00 06:00:13
    INDEX 01 06:02:11
  TRACK 04 AUDIO
    TITLE "Track04"
    INDEX 00 08:23:32
    INDEX 01 08:25:32
  TRACK 05 AUDIO
    TITLE "Track05"
    INDEX 00 12:27:40
    INDEX 01 12:29:40
  TRACK 06 AUDIO
    TITLE "Track06"
    INDEX 00 14:32:05
    INDEX 01 14:34:05
"""
        cue_file = tempfile.NamedTemporaryFile(suffix=".cue")
        try:
            cue_file.write(CUESHEET)
            cue_file.flush()

            #from_cuesheet wraps around from_tracks,
            #so I don't need to hit this one so hard
            xmcd = audiotools.XMCD.from_cuesheet(
                cuesheet=audiotools.read_sheet(cue_file.name),
                total_frames=43646652,
                sample_rate=44100,
                metadata=audiotools.MetaData(album_name=u"Test Album",
                                             artist_name=u"Test Artist"))

            self.assertEqual(xmcd.album_name, u"Test Album")
            self.assertEqual(xmcd.artist_name, u"Test Artist")
            self.assertEqual(xmcd.year, u"")
            self.assertEqual(xmcd.catalog, u"")
            self.assertEqual(xmcd.extra, u"")
            self.assertEqual(len(xmcd), 6)
            for i in xrange(len(xmcd)):
                self.assertEqual(xmcd.get_track(i),
                                 (u"", u"", u""))
        finally:
            cue_file.close()

    @LIB_CORE
    def test_missing_fields(self):
        xmcd_file_lines = ["# xmcd\r\n",
                           "DTITLE=Album Artist / Album Name\r\n",
                           "DYEAR=2010\r\n",
                           "TTITLE0=Track 1\r\n",
                           "TTITLE1=Track Artist / Track 2\r\n",
                           "TTITLE2=Track 3\r\n",
                           "EXTT0=Extra 1\r\n",
                           "EXTT1=Extra 2\r\n",
                           "EXTT2=Extra 3\r\n",
                           "EXTD=Disc Extra\r\n"]

        xmcd = audiotools.XMCD.from_string("".join(xmcd_file_lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))


        lines = xmcd_file_lines[:]
        del(lines[0])
        self.assertRaises(audiotools.XMCDException,
                          audiotools.XMCD.from_string,
                          "".join(lines))

        lines = xmcd_file_lines[:]
        del(lines[1])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"")
        self.assertEqual(xmcd.artist_name, u"")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

        lines = xmcd_file_lines[:]
        del(lines[2])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

        lines = xmcd_file_lines[:]
        del(lines[3])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"", u"", u""))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

        lines = xmcd_file_lines[:]
        del(lines[4])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"", u"", u""))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

        lines = xmcd_file_lines[:]
        del(lines[5])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"", u"", u""))

        lines = xmcd_file_lines[:]
        del(lines[6])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"", u"", u""))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

        lines = xmcd_file_lines[:]
        del(lines[7])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"", u"", u""))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

        lines = xmcd_file_lines[:]
        del(lines[8])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"Disc Extra")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"", u"", u""))

        lines = xmcd_file_lines[:]
        del(lines[9])
        xmcd = audiotools.XMCD.from_string("".join(lines))
        self.assertEqual(xmcd.album_name, u"Album Name")
        self.assertEqual(xmcd.artist_name, u"Album Artist")
        self.assertEqual(xmcd.year, u"2010")
        self.assertEqual(xmcd.catalog, u"")
        self.assertEqual(xmcd.extra, u"")
        self.assertEqual(xmcd.get_track(0),
                         (u"Track 1", u"", u"Extra 1"))
        self.assertEqual(xmcd.get_track(1),
                         (u"Track 2", u"Track Artist", u"Extra 2"))
        self.assertEqual(xmcd.get_track(2),
                         (u"Track 3", u"", u"Extra 3"))

    @LIB_CORE
    def test_metadata(self):
        xmcd = audiotools.XMCD({"DTITLE": u"Album Artist / Album Name",
                                "DYEAR": u"2010",
                                "TTITLE0": u"Track 1",
                                "TTITLE1": u"Track 2",
                                "TTITLE2": u"Track 3"},
                               [u"# xmcd"])
        self.assertEqual(xmcd.metadata(),
                         audiotools.MetaData(artist_name=u"Album Artist",
                                             album_name=u"Album Name",
                                             track_total=3,
                                             year=u"2010"))



class TestMusicBrainzXML(unittest.TestCase):
    XML_FILES = [(
"""QlpoOTFBWSZTWZHZsOEAAmLf+QAQeOf/9/1/3bA//99wf//K9x732X8f4FAGHp3dsABh2rtyIBUD
U0JiCaaZNJ5TBpqGjU2oeo09JoAZAMjQ0yBoGgaAaNGhp6E9Qip+EaZBoVKABpkaAAABoAAAAAAA
AAAAGU/AGiKNhR6npNAaAAANAAAAAAAAAAAAEGmJgAAAAAAAAAAAAAAjCMAAAACRQmggGhDTTVPJ
H6NU0DIejUNNlHqbUBmoDTQNAANA0AADN5RLP0eOEM/mcT4+2+SfHNdRRk+lrXyi2DVDhUA3BpKS
UhLoINkzquanlotv9PGs5xY5clNuvcvVLd0AwO1lx9K7n1nbrWefQoIZEg7p08WygJgBjCMXAuWL
aSakgglqhUchgiqtqpNQKCAakvsJANKGjEWUwzlgYZJCsEthxOMeGKG4K2pgHQCwJqXaV5Sxi4rm
SVxVEK+YOEm07ULFRFGF1B8CNoR02kIQORxurqm4bob4hbre+QrGJCwb+szLbl1rZe1NZhMojx4i
ocOccTgMKMyVrQQwiHQgQCiBKoCpbbbhSFUsM6ERGvOvhGLQbxapnFuBw81zDZAbgtevZuBXYlwe
62pJMU2K23PUgEwroQTY1Z613s2RZmuE1GARCzByvdOhW+szQjtriTiKXERJeKSM91nTZbkWGQrS
zp7YpVRXM3UcbnZMCoyJFwWiUCsRQdZXRqZnaARKTscCcS4iJBVcY2pBN0luuyIBu5C+gqIGUHMR
hTvi2pYmEqDiGhKDe8C4UIoyUKWplMbyLgHBRzGsZlBWbD1ihyHSC2tA9EtJ6CbVrpmcs4IVietG
zUfETxBIEXGZwGMA+s0RRvXcTzC51VQOhPgBZbyljbW5O4zVshxFNtZjMoeTqlCMTmwI4lixpDPt
ZrGGmBjeunrezi6XnWOHEDuq3q8g4q7CJA+sRdNyYQ0DDqRqU2nA0ksZtatMBm1BwYDgHlrCZVqw
kOe6WHTuRhErm7EUs2HUCaRRJSkpm4gwJF1285rvaDJZscjHe8XBFGumVMs50ENjJqn5/ydU0bmT
Wwg2x643BtuDg4OPZa04LcHP7UdWz0O10j5/F/S9LH+UPGn+ebt5EkLhYCW4WYrW4ptBHJGDLZAo
5+/4agFzqHVDwpALZdEqAE3qgOA0CmIi0KUqGIVwnz/AwNketGnqeb7MjkqgPerUKZcrhxQFWTn5
bZjpNpabQQRBJHAIoqeZlZl+/es379a9RxHl31vLzXmrSHDqcYzuwG4n2TGjDTj7TeK23WnDgAcL
sFR4eHqQdxyJegRdEAZw0dDuaahUZc4T4MR+uNWqOi9rIdiAAMetaqFYbflOeeFNeaepNx5MdyJh
41y41X490KaUN5kE+SQBYCzyC5m4PTywUHZL7sw8A3UtWCGn1JE1AqWKNI3mEGc7kY4IktPEYZ9c
YTIbmjBHQYYwBlZFenCCXJFFAcUZSISAkRhT8bKeLLLIc7hIRlEKiqhznWW60y87uYzRvQ29hgLc
AXcGrmZs+fL4ahjvZJhs4as9FWfHTOOxGmycq47d+G3bcw6jDuAKoaGwQRPcg4M9WKCseZJ46Kjw
xR6igaSabIkIU1Tt6vDVxnTHXiyieoJ7EHWfhkDVuwClrYrLUrVpVHJDFuHStNdxGM2+6xsk2Vk2
uhAkNOIDddEy1d95+BDseVVGVkgHfgU01jjLF800ohth9wGFo1ctUzReJxGALFKmLQ3qgIFKdxIF
hhjfNW7C+ZKxAmLd2UqJj9TgwX+dO9ZUFnd9hOpl8hoU6m1U9DAEyOCp2TuzmuvjKjAUhS7IWVl3
R18lzwccNcvevCzP1oCBXeCjlOZGk0d1Mw7x6VpTw1Gxfeu85ClIFWQAFmk9Ojabb2uCgni6MTTe
ytRJl+K8QegMXQ00iotIG0sVttaComWXNeDsODekXSBejVllUlEoNpXYyKYK/cjFAKwwIFQgVIgX
MtObIBUNgKrAYjJmroiHYrAFpInfXsaslxwIhxXKlioaeIvH8L22A95Axja5zmMYBGtr7nuSPgzD
pJ2S4PmcbHewcGzhpNLMPDwegzwwZJv3YYmNDcmg7NePApT/5islCQ6AgfA5DIyGyBoEjCQUPU0A
hH8l+2x+drf3W9tm9uRe0f3AX6G7Yj2oRM3vtHvb04qlt26OazBgWgqZ98kSXP8lwRPWSuppyEWI
vCUDDrZiT4cevVmI9LRpPw/7DgctthGdx4P+LuSKcKEhI7Nhwg==""".decode('base64').decode('bz2'),
                  {1:audiotools.MetaData(track_name=u'Frontier 2059', track_number=1, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   2:audiotools.MetaData(track_name=u"Welcome To My FanClub's Night! (Sheryl On Stage)", track_number=2, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   3:audiotools.MetaData(track_name=u"What 'bout my star? (Sheryl On Stage)", track_number=3, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   4:audiotools.MetaData(track_name=u"\u5c04\u624b\u5ea7\u2606\u5348\u5f8c\u4e5d\u6642Don't be late (Sheryl On Stage)", track_number=4, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   5:audiotools.MetaData(track_name=u'Vital Force', track_number=5, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   6:audiotools.MetaData(track_name=u'\u30c8\u30e9\u30a4\u30a2\u30f3\u30b0\u30e9\u30fc', track_number=6, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   7:audiotools.MetaData(track_name=u'Zero Hour', track_number=7, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   8:audiotools.MetaData(track_name=u"What 'bout my star? @Formo", track_number=8, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   9:audiotools.MetaData(track_name=u'Innocent green', track_number=9, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   10:audiotools.MetaData(track_name=u'\u30a2\u30a4\u30e2', track_number=10, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   11:audiotools.MetaData(track_name=u'\u30d3\u30c3\u30b0\u30fb\u30dc\u30fc\u30a4\u30ba', track_number=11, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   12:audiotools.MetaData(track_name=u'Private Army', track_number=12, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   13:audiotools.MetaData(track_name=u'SMS\u5c0f\u968a\u306e\u6b4c\u301c\u3042\u306e\u5a18\u306f\u30a8\u30a4\u30ea\u30a2\u30f3', track_number=13, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   14:audiotools.MetaData(track_name=u'\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah!', track_number=14, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   15:audiotools.MetaData(track_name=u'\u8d85\u6642\u7a7a\u98ef\u5e97 \u5a18\u3005: CM\u30bd\u30f3\u30b0(Ranka Version)', track_number=15, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   16:audiotools.MetaData(track_name=u"Alto's Theme", track_number=16, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   17:audiotools.MetaData(track_name=u'Tally Ho!', track_number=17, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   18:audiotools.MetaData(track_name=u'The Target', track_number=18, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   19:audiotools.MetaData(track_name=u'Bajura', track_number=19, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   20:audiotools.MetaData(track_name=u'\u30ad\u30e9\u30ad\u30e9', track_number=20, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   21:audiotools.MetaData(track_name=u'\u30a2\u30a4\u30e2\u301c\u9ce5\u306e\u3072\u3068', track_number=21, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   22:audiotools.MetaData(track_name=u'Take Off', track_number=22, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   23:audiotools.MetaData(track_name=u'\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3', track_number=23, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u''),
                   24:audiotools.MetaData(track_name=u'\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9', track_number=24, track_total=24, album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed', artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'VTCL-60060', copyright=u'', publisher=u'', year=u'2008', date=u'', album_number=0, album_total=0, comment=u'')}),
                 (
"""QlpoOTFBWSZTWeDENZEAAz5fgAAQeef//7/f36A/799xYAcrsz7YABzkbI43Y2qaoDJCGTU2iZMm
NU0TMNJMjQepoGmgepggyEDQBJTUADyjTQABkAANNBzAEYJiAYBME0ZDQwCYIxMJCkamTJNqjaT0
EbUPUGmgGRkGQAAcwBGCYgGATBNGQ0MAmCMTCKSYgIamlPRtRmhT2iDTITyhkG0jyhp6R7ft9O/i
1Z4/pPTR3rEndbINagfOT+z0r/acXK6koolQSF4RDaTfyoI9CdAf2Q+6+JfP58XljKSVU1jYzzsv
rxUEcNIiDTBtBYZYTFVzF0A1VJvW7m06MuQVuzR4vUQAFGcHeFFnWMEm8FVq6qJqbEzQY7rbK6Ht
qIIYMjFCBtu0Kgu9S2ICsWHCtVacniFimTBY7DoXQua5d7FuDdoQaI7j9Atk1vS7WB9OeZUNoZdb
Jh8ZzRmMZxD1rgPYXSVqTQ49QFKG8dGZ1mwhej0yDo6Bxd6YpMyuqauSI3gU1kOb5H5HKdqIViO0
koeshQndohdYwJeDYy4GlnxbIpiIGW6ZW34jGcnGl7JHgzujXFHDKkYTtn1RTCY7hM3ZEghnCsZV
tN0FT6zXwo1rVuBEzmCxnRlcv8257p0KUrRqrHp+p1Tk6TrecakrEMGAbjiW+kEGOCynYNnhjLjU
jevIGSC2dXuxHShR0EbpUEoavBRa0bmbWx1npEYVQ3DzTJKGB0ctHoUzvdkzkoUqlr1siTbG1VK5
EUfabNTHVcu/VJ8lvZnFVn01kCImuUqIkWNqLPlpPNUEtHTQmUIaCi1cNBDgXZsoN2XCIgMAi2IL
Q1XW7KKUETE3o9YbxRqxoCuw97jW8vIodbPNuHRsgUth5UDmVJadRqmJxZUSFMziL7k9ZCqz5vaW
FgcLRZ2ZoKwxeubSi44+ag8rykdMMX5mXIQbNdzTQG7C8Bmsq3MYQQQTNrIGgS4vIULY06UFebnd
6rBd8XDbpZpT4ajY5mC3MMX4WbArheSqtzyOIXaQOZhUKQeouZtZ2L3zkcGMRGBO7gWiDsyhFFRt
q6SllhMPhjYVWiJNLvuUMg6vuoEtGnSY21YtJbovyyy8Jv8UW8kF9u6SSSORscpsXGzYK/BWEtNm
GsujIUrKN2Ss56MbB3SRk4bxF+EKoUK3W2AsFkLICV23uqIVUKRGUCGExDlsoIcahKJAkKFQshGc
0ErO7j4BiaO0wgmJ2SNHzkTdJENkagwaYMaYe9wGJpMboKRMGNEZBjGM6GQQ3coRvVjxi3a5azbw
V2gVpxUXcpNNinvCQE4T8LeBx3Zmja767xrTY8PDsCQIxqNdWXop6PZ7MDd2/sAXTjstBQ/VrbRa
GgkePhNcp/8eC8fQodKhQP/gDae3RrBDxwWvs3cXPx/iZjzdEx1bXdbPxqYGMIsgT3qSaJY0YOkA
7y+c199/G44GbVbgQ3qdCYiJou5xOPJtgaqO+Bdpv1s4VPlrqYjss52VQc8gkJG62B5CWQ3pJ4ID
2nUsMdhqxaMSniimd0YCQNtlqY8II1ZfvgcTTKDmumwNSr9Jnc21qxPPKszuwbA6NCAkCuGukaY0
ZzmgIVhczGuharoq2KBA1ggZ7z05EVtaCFpH2bMY3vGqjmChGcJqvF61SS9GPNCAki6WGNuBtHf/
CE3h4ujYBYob9BCShBAMDChsTbaGk2x767N+WS14XpYH1zheB9tRfhwd5F91K66spY61AU7hX4dt
2Tf96Y49yUZ3E0YN7AZQ+cZNo+sOojVlHli5Ne5TOdW1EK3dfLr3NByIC3y737D62wz5VUFzVvzU
N4ACFBPjCrpRNQTVC8Z1ySDSAB2TeQC0C1dNofd58ZdJpx5BQ91DdLvXUhpDy65ZWYFhlAITweox
pdyuqQMaQMYCJyZkZAhjEGeFJufzPeuugmEDAoSCyyXMmxbLC8obFzimVLGy2SbICQZubln4UsTK
FSmMFEZk2yIQPFIKqFzJgGIIFgi2sd212zC6lNkrzMlOGps0Gek4N9LzrWfZecAwiHoL5395s37h
QwX9ABOznbOweXBfpbYNR22fwAX6WjNFiFCUcCQMgp4BBAF/8y2cvHEcvzLQ5OL03nDC5mZw6LaT
W9FZCg9QjtrHm+PNp5Zn2bw8qlCnfPkpA2E5xUKZkBwJAxJCxEpCpQIMbsZB7dYJ6sRQioEUZ11T
sVKGBzFcZXXrlOQBq14B8sRQoAmahcoY5ihS8xKCFYgQreW2rhgZYAcGy7y0RK484IQbjqDn69OU
Qav7keYLy1lhvaQNZW37i7kinChIcGIayIA=""".decode('base64').decode('bz2'),
                  {1:audiotools.MetaData(track_name=u'Scars Left by Time (feat. Dale North)', track_number=1, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Ailsean', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   2:audiotools.MetaData(track_name=u'Star Stealing Girl (feat. Miss Sara Broome)', track_number=2, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'The OneUps', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   3:audiotools.MetaData(track_name=u"A Hero's Judgement (feat. Ailsean, Dale North & Roy McClanahan)", track_number=3, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Matt Pollard', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   4:audiotools.MetaData(track_name=u'Parallelism (The Frozen Flame)', track_number=4, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Matt Pollard', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   5:audiotools.MetaData(track_name=u'Guardian of Time (feat. Greg Kennedy)', track_number=5, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Mustin', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   6:audiotools.MetaData(track_name=u'The Boy Feared by Time', track_number=6, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Ailsean', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   7:audiotools.MetaData(track_name=u'The Girl Forgotten by Time', track_number=7, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Mark Porter', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   8:audiotools.MetaData(track_name=u'Wings of Time', track_number=8, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Dale North', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   9:audiotools.MetaData(track_name=u'Good to be Home', track_number=9, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Dale North', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   10:audiotools.MetaData(track_name=u'Dream of Another Time', track_number=10, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Mustin', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   11:audiotools.MetaData(track_name=u'Fields of Time', track_number=11, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Mellogear vs. Mark Porter', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   12:audiotools.MetaData(track_name=u'To Good Friends (feat. Tim Sheehy)', track_number=12, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Dale North', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   13:audiotools.MetaData(track_name=u'The Fighting Priest', track_number=13, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Ailsean', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   14:audiotools.MetaData(track_name=u'June Mermaid', track_number=14, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Dale North', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   15:audiotools.MetaData(track_name=u'Navigation is Key! (feat. Dale North)', track_number=15, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Matt Pollard', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   16:audiotools.MetaData(track_name=u'Gentle Wind', track_number=16, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Dale North', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   17:audiotools.MetaData(track_name=u'Star of Hope (feat. Mark Porter)', track_number=17, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Dale North', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u''),
                   18:audiotools.MetaData(track_name=u'Shake the Heavens (feat. Matt Pollard & Dale North)', track_number=18, track_total=18, album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda', artist_name=u'Mark Porter', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'', copyright=u'', publisher=u'', year=u'', date=u'', album_number=0, album_total=0, comment=u'')}),
                 (
"""QlpoOTFBWSZTWborpk4AAb9f+QAQWIf/97//36A/79/xPeXqji45Q1ILwFAFBPIAg1bPdjQMGpkT
RGgmg9CbSZNGhpoaAMJ6EBoAAAaGgGj0hFPTRoyaBSjEaGmg0AaAAAAAAAAAAA4aAaAA0BoDQAAA
NNGmgDIAABo0yDDT1Up6mh6h6jJ6QABkDEABk0ABpoNMQAyAABJIEBMmjQ1PVTelPJk0T0n6o8oP
TKP1Jo9NT1PUNAAAAAA5jWBiUcwUqQeZFEVhfPM5ZoFkRkUyeSggCQZmRESkhAaLVnaTswolMTqp
VUriy58+eZUr/IogIFgJIqBg4DjeW5ErKKmgwAGWeGkB2zgzYEs+IZ+iyCFTtNww0FV4NO0wpGEW
ugQ4THUaiJTOpSo8eIBawqjIUtOtpyIbvia0AmlUWR15hznCDaz0WLrOQ3gOVAcbNyjkFAwkuXMx
ZVfdpfK/Tlhq0FLtPKEpqn0tOPcYtAm4CqUKmdXik1zmpOTxKUQSaxUBrQnVkSXgbroU1vFZT0Ty
CQSq1ye98wjZwQQMKj6RpjVDMJIOTgK8JA9xuqkMG4oYlPAZgxmzYmRSnLEHVrTC0GNInW4zogGs
hYDhh11gLMDqvR9bFBTuLxHI1Y3uECq4ARzgvBr2BRAwnJkgtYyQ3XC0b0tJoAyjZanQzhOQ1cJ1
SLJZQsTILWnGkZuoYZrHI2KtBQZxioxjGZUoLMUluE3TqVDWKHeohCMQQXrUgiUFQovXAOwM3lOb
2QXvAxci0os2AUMHOor2uYOBHJHErAV2Y7SZoYjWjK5VyB63qRkIYoW2DXbDOyAJQG4uBxamr1+/
qe3rNu0yGSPhRhR46vEP/Hd/X9/BlEBzsAiOnNwPchzkD3CtZzLsgk/N3ts4HGTsww0nOdsYDREI
sD4gMyOJA4ZwhkDpJRgkKHfxLvV5jMdR4SC20em+R5CDjm7fiK+oavx9BI6fZs5CuJaKxFkOsyFE
iS7o4JZXjh3r9W4WBhNNMTPJojE93sdZIy4jFZNG1rVZWNYUPmjEjBQJY3UKkBRiGLUCKFCbTsah
ChKCpMbUVUINMGyTz1CFXhHbyCCqMlG2PQxA6GpBBtFxdBgecg89BnF7d5ZJluGEATArSjyXG5Tb
iEyjQxJgMqrk0uxZU0UFbuKgYMKEwB0gjHlYtRlzYeMpgJVvp40gKwmJTDIA0roA6AJrV0xG7SRp
ua3UX3X54T3ZhBqnpM9NemyOq3s1oNYGE+N5jPkrtnByINkmdNlzyn0PG1V1xplVHHtbwvUZawu8
sBwmBMIYAQMhAuBPwViZ+G/ckSCCG8DK8URNxh3QHCjAqBbU0cK9VDEcTccYsuJajyJGQs44kz0s
ty0ngwGHXTYo4OGaNEqSxqpQqm1ore2zhrM/FgdqNaHaLxtG6U0iDmOBHc291HesKgpYAtUJ3oGG
AZMzHGwgryCCc32uJqLdNAgiLfRuJQoKIk+yEAQTdvyJsGB1kAmsGQkk48yTrJQnABAgABPOihOU
yMhFVM08w8wtlqiXpkgh2GfuREHPEsRMeiWI0EyOfpQarp2kINnCPKADwG5uYMzNhvQMTPQ8qQ4H
CCAgoK8CsxTxre/rnFTMagyoLkFyKECvGKtIjW4nEDh1V74pJ5WTPHyamvNlgCKgRYgkgoEERwD2
YCegjsMqDdN+VaW+AMYnBcp4HS4eFxdcgYpDyj+gF8PwDf3+jv5/z6YwvHbaV4nbSO9CzD7BoJQg
nbvdly53/Ea4Pe78RYPpd/V9AYf/k/36b75h+9/i7kinChIXRXTJwA==""".decode('base64').decode('bz2'),
                  {1:audiotools.MetaData(track_name=u'\u30e1\u30ea\u30c3\u30b5', track_number=1, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'\u30dd\u30eb\u30ce\u30b0\u30e9\u30d5\u30a3\u30c6\u30a3', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   2:audiotools.MetaData(track_name=u'\u6d88\u305b\u306a\u3044\u7f6a', track_number=2, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'\u5317\u51fa\u83dc\u5948', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   3:audiotools.MetaData(track_name=u'READY STEADY GO', track_number=3, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u"L'Arc~en~Ciel", performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   4:audiotools.MetaData(track_name=u'\u6249\u306e\u5411\u3053\u3046\u3078', track_number=4, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'YeLLOW Generation', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   5:audiotools.MetaData(track_name=u'UNDO', track_number=5, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'COOL JOKE', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   6:audiotools.MetaData(track_name=u'Motherland', track_number=6, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'Crystal Kay', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   7:audiotools.MetaData(track_name=u'\u30ea\u30e9\u30a4\u30c8', track_number=7, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'ASIAN KUNG-FU GENERATION', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u''),
                   8:audiotools.MetaData(track_name=u'I Will', track_number=8, track_total=8, album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST', artist_name=u'Sowelu', performer_name=u'', composer_name=u'', conductor_name=u'', media=u'', ISRC=u'', catalog=u'SVWC-7218', copyright=u'', publisher=u'', year=u'2005', date=u'', album_number=0, album_total=0, comment=u'')})]

    @LIB_CORE
    def testreading(self):
        #check that reading in XML file data matches
        #its expected values
        for (xml, metadata) in self.XML_FILES:
            mb_xml = audiotools.MusicBrainzReleaseXML.from_string(xml)
            for i in xrange(len(mb_xml)):
                self.assertEqual(mb_xml.track_metadata(i + 1), metadata[i + 1])

        #check that reading in an XML file matches
        #its expected values
        for (xml, metadata) in self.XML_FILES:
            f = tempfile.NamedTemporaryFile(suffix=".xml")
            try:
                f.write(xml)
                f.flush()
                f.seek(0, 0)
                mb_xml = audiotools.MusicBrainzReleaseXML.from_string(f.read())
                for i in xrange(len(mb_xml)):
                    self.assertEqual(mb_xml.track_metadata(i + 1),
                                     metadata[i + 1])
            finally:
                f.close()

    @LIB_CORE
    def testtracktagging(self):
        for (xml, metadata) in self.XML_FILES:
            #build a bunch of temporary FLAC files
            temp_files = [tempfile.NamedTemporaryFile(suffix=".flac")
                          for i in metadata.keys()]
            try:
                temp_tracks = [audiotools.FlacAudio.from_pcm(
                        temp_file.name,
                        BLANK_PCM_Reader(5),
                        "1") for temp_file in temp_files]
                for (i, track) in enumerate(temp_tracks):
                    track.set_metadata(audiotools.MetaData(track_number=i + 1))

                #tag them with metadata from XML
                xml_metadata = audiotools.MusicBrainzReleaseXML.from_string(xml)
                for track in temp_tracks:
                    track.set_metadata(
                        xml_metadata.track_metadata(track.track_number()))

                #build a new XML file from track metadata
                new_xml = audiotools.MusicBrainzReleaseXML.from_tracks(
                    temp_tracks)

                #check that the original XML values match the track ones
                for i in xrange(len(new_xml)):
                    self.assertEqual(metadata[i + 1],
                                     new_xml.track_metadata(i + 1))
            finally:
                for t in temp_files:
                    t.close()

    @LIB_CORE
    def testorder(self):
        VALID_ORDER = \
"""QlpoOTFBWSZTWQRNLWEAAMFfyQAQWGf/979fWCA/799wAIEJIQKgQAKLoc44CEqaSJ6bRMUzSejF
P1I9Q0GjyNTE0D1AD1CJiGgKeRRp6ZEAAGmgAAAAaEaiA0AAAAAABoAABIoQJ6ieo9JslGeVG9U0
NPUBoaBkeUAJduZ5atyq+8Qc8hinE2gjl5at2wXrmqloSptHFn6YW86gJh7GnEnIAKMMoaQXMozq
1K7UmkegbTX00RcL0uyTdGC8Tme983GQhA7HG9bzzGQbhdre4hYMS3XjLNbnhrtDPc9Qcb8MMjmX
ym8V8hgpuGNwtUIIRolAixMpPW0GcINraYOOFjJLxWWC5sJUFqUIyF7q1JguFowcQRi8yXCyAkBu
eYnmBlYPxIJtedBnSs6IEbTkMosBGvk+dBhRIzc40cU11rKR+AX5sfbAAL7FSaN/OQrUpXKIAAQV
mzERCZ2ZzYgaEesQoAFlTdS40B41aoBnSQGgMgjhNVSK8Tlt/DI4GS69igp+lxwGDCsf3G13fFQY
2oJWjJpmpNDi0Guu4mihwtWdY5OHRZfoa1SkXbwjEY6Bn9CSuQTEIPassuTLFp8TAdTIK0oaMieM
MYonf4BIdUeufDDAKigH4ccczUCgOPYYyWxYZrEkXeRueqkwPhOIDY2ltvr9DR6VhvVkqY+ePzFM
pvxMOSfwvI7Oh23+Pb1dDyNL1nTn4oHKLMvOYiWCx8ETT2TNkmBq+tNcmhtiMxHStVhp00iONLHF
Koq1WRiFGPKcFBQsVENDV7AZOl11SKigtJKbdVJwWDV2Zr3mjgZWbYQQU9pnQdakbCPWXVuQiwjc
Bffsbb2bpGl6BmBPAJ+TGhKrqYuIiYnFbboQTuOeBUQIV8kaEokx0OycEFZNEkaBErSISbCrnLTK
dyoZiBkU31Oq3oLCLfCMIi75/brrrf67/F3JFOFCQBE0tYQ=""".decode('base64').decode('bz2')

        INVALID_ORDER = \
"""QlpoOTFBWSZTWRPfcE8AAMHfyQAQWGf/979fWCA/799wAIEJIQKgQAKLoXcaghKmiRpkwk2TIZPU
j1MTRowTE0DQA9QiYhoCnkKaegQAA0aAA0AAIKJ+kmgyDIDCAaMgAaaNMQBhIkQnqelNqm0nspDe
pG1APUBoAZHlACc34Hlq4K1d4gzyH1MTeCMcWrhuF7MOmelNLaZuqHnbkUAxdy9mIogAowyhcF7K
M69Wu3NpHoG019VEXDGl+KbowXqdT3PB9yGz3uWK3nlOcNwupvcRQYluxGU5HXK60OW96g5H5MmJ
zMcpvFecwU3JhcLVCCEaJQIsTKT1tBnEDa2mDjhYyS8FlgubCVBalCMhe6tSYLhaMHEEYvMlwsgJ
AbnmJ5gZWD8CCbXnQZ0rOiBG05DKLARr5PnQYUSM3ONHFNdaykfiGPNh7oABfYqTPo4CJag5hUAC
wClmOyIhS4S+soJkaui++gXW7YPDMJTiYQ5QXwAiEjFMzEXhRkifr9SE+PIwG5vQgCAgNOKEqCnS
qkHa4skzTaMNRmYtBrrt1ooYclnWMoDLtsUtapSL5cw+j7oGP0JdUol0Qe13571+PR4lozvwakpa
PxvENwUUW7IkWu5sohigFRwFuKS5hagUhi3EhPtWGDakq3Ebj01FD16IabG0uXHR52j0LLeqTtl5
pfMVS3HMy46/DEls6HHNlv5+hGkCSGSrpWSiqiYoGDwrFjYQb7ZecQCH1s2pttDEbRHgXFQvvtEd
hLPNK4u4qSkFmfZOChRRWRpaxYDLKmi6ZcWGBNVbutOCya17Tk3mngc9OWIQW9RtsOlTNhLpNehz
EUJawMcTYN7N0y96RmRXIK+LOxK7yMWokZmrDDSgrrOaC4gjRxysSkVHY6VhBoKomjSIngSCbYXc
xgc9dasZmA0qsKdVxQWEfGIfIyv5/a66+X9X/i7kinChICe+4J4=""".decode('base64').decode('bz2')

        self.assert_(VALID_ORDER != INVALID_ORDER)

        self.assertEqual(audiotools.MusicBrainzReleaseXML.from_string(
                VALID_ORDER).metadata(),
                         audiotools.MusicBrainzReleaseXML.from_string(
                INVALID_ORDER).metadata())

        self.assertEqual(audiotools.MusicBrainzReleaseXML.from_string(
                VALID_ORDER).to_string().replace('\n', ''),
                         VALID_ORDER.replace('\n', ''))

        self.assertEqual(audiotools.MusicBrainzReleaseXML.from_string(
                INVALID_ORDER).to_string().replace('\n', ''),
                         VALID_ORDER.replace('\n', ''))

    @LIB_CORE
    def test_attrs(self):
        for (xml_data, attrs) in zip(
            self.XML_FILES,
            [{"album_name": u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',
              "artist_name": u'\u83c5\u91ce\u3088\u3046\u5b50',
              "year": u'2008',
              "catalog": u'VTCL-60060',
              "extra": u""},
             {"album_name": u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',
              "artist_name": u'Various Artists',
              "year": u'',
              "catalog": u'',
              "extra": u""},
             {"album_name": u'FULLMETAL ALCHEMIST COMPLETE BEST',
              "artist_name": u'Various Artists',
              "year": u'2005',
              "catalog": u'SVWC-7218',
              "extra": u""}]):
            mb_xml = audiotools.MusicBrainzReleaseXML.from_string(xml_data[0])

            #first, check that attributes are retrieved properly
            for key in attrs.keys():
                self.assertEqual(getattr(mb_xml, key),
                                 attrs[key])

        #then, check that setting attributes round-trip properly
        for (xml_data, xml_metadata) in self.XML_FILES:
            for (attr, new_value) in [
                ("album_name", u"New Album"),
                ("artist_name", u"T\u00e9st N\u00e0me"),
                ("year", u"2010"),
                ("catalog", u"Catalog #")]:
                mb_xml = audiotools.MusicBrainzReleaseXML.from_string(
                    xml_data)
                setattr(mb_xml, attr, new_value)
                self.assertEqual(getattr(mb_xml, attr), new_value)

        #finally, check that the file with set attributes
        #round-trips properly
        for (xml_data, xml_metadata) in self.XML_FILES:
            for (attr, new_value) in [
                ("album_name", u"New Album"),
                ("artist_name", u"T\u00e9st N\u00e0me"),
                ("year", u"2010"),
                ("catalog", u"Catalog #")]:
                mb_xml = audiotools.MusicBrainzReleaseXML.from_string(
                    xml_data)
                setattr(mb_xml, attr, new_value)
                mb_xml2 = audiotools.MusicBrainzReleaseXML.from_string(
                    mb_xml.to_string())
                self.assertEqual(getattr(mb_xml2, attr), new_value)
                self.assertEqual(getattr(mb_xml, attr),
                                 getattr(mb_xml2, attr))

    @LIB_CORE
    def test_tracks(self):
        for ((xml_data, metadata),
             track_metadata) in zip(self.XML_FILES,
                                    [[(u"Frontier 2059",
                                       u"", u""),
                                      (u"Welcome To My FanClub's Night! (Sheryl On Stage)",
                                       u"", u""),
                                      (u"What 'bout my star? (Sheryl On Stage)",
                                       u"", u""),
                                      (u"\u5c04\u624b\u5ea7\u2606\u5348\u5f8c\u4e5d\u6642Don't be late (Sheryl On Stage)",
                                       u"", u""),
                                      (u"Vital Force",
                                       u"", u""),
                                      (u"\u30c8\u30e9\u30a4\u30a2\u30f3\u30b0\u30e9\u30fc",
                                       u"", u""),
                                      (u"Zero Hour",
                                       u"", u""),
                                      (u"What 'bout my star? @Formo",
                                       u"", u""),
                                      (u"Innocent green",
                                       u"", u""),
                                      (u"\u30a2\u30a4\u30e2",
                                       u"", u""),
                                      (u"\u30d3\u30c3\u30b0\u30fb\u30dc\u30fc\u30a4\u30ba",
                                       u"", u""),
                                      (u"Private Army",
                                       u"", u""),
                                      (u"SMS\u5c0f\u968a\u306e\u6b4c\u301c\u3042\u306e\u5a18\u306f\u30a8\u30a4\u30ea\u30a2\u30f3",
                                       u"", u""),
                                      (u"\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah!",
                                       u"", u""),
                                      (u"\u8d85\u6642\u7a7a\u98ef\u5e97 \u5a18\u3005: CM\u30bd\u30f3\u30b0(Ranka Version)",
                                       u"", u""),
                                      (u"Alto's Theme",
                                       u"", u""),
                                      (u"Tally Ho!",
                                       u"", u""),
                                      (u"The Target",
                                       u"", u""),
                                      (u"Bajura",
                                       u"", u""),
                                      (u"\u30ad\u30e9\u30ad\u30e9",
                                       u"", u""),
                                      (u"\u30a2\u30a4\u30e2\u301c\u9ce5\u306e\u3072\u3068",
                                       u"", u""),
                                      (u"Take Off",
                                       u"", u""),
                                      (u"\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3",
                                       u"", u""),
                                      (u"\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9",
                                       u"", u"")],
                                     [(u"Scars Left by Time (feat. Dale North)",
                                       u"Ailsean", u""),
                                      (u"Star Stealing Girl (feat. Miss Sara Broome)",
                                       u"The OneUps", u""),
                                      (u"A Hero's Judgement (feat. Ailsean, Dale North & Roy McClanahan)",
                                       u"Matt Pollard", u""),
                                      (u"Parallelism (The Frozen Flame)",
                                       u"Matt Pollard", u""),
                                      (u"Guardian of Time (feat. Greg Kennedy)",
                                       u"Mustin", u""),
                                      (u"The Boy Feared by Time",
                                       u"Ailsean", u""),
                                      (u"The Girl Forgotten by Time",
                                       u"Mark Porter", u""),
                                      (u"Wings of Time",
                                       u"Dale North", u""),
                                      (u"Good to be Home",
                                       u"Dale North", u""),
                                      (u"Dream of Another Time",
                                       u"Mustin", u""),
                                      (u"Fields of Time",
                                       u"Mellogear vs. Mark Porter", u""),
                                      (u"To Good Friends (feat. Tim Sheehy)",
                                       u"Dale North", u""),
                                      (u"The Fighting Priest",
                                       u"Ailsean", u""),
                                      (u"June Mermaid",
                                       u"Dale North", u""),
                                      (u"Navigation is Key! (feat. Dale North)",
                                       u"Matt Pollard", u""),
                                      (u"Gentle Wind",
                                       u"Dale North", u""),
                                      (u"Star of Hope (feat. Mark Porter)",
                                       u"Dale North", u""),
                                      (u"Shake the Heavens (feat. Matt Pollard & Dale North)",
                                       u"Mark Porter", u"")],
                                     [(u"\u30e1\u30ea\u30c3\u30b5",
                                       u"\u30dd\u30eb\u30ce\u30b0\u30e9\u30d5\u30a3\u30c6\u30a3", u""),
                                      (u"\u6d88\u305b\u306a\u3044\u7f6a",
                                       u"\u5317\u51fa\u83dc\u5948", u""),
                                      (u"READY STEADY GO",
                                       u"L'Arc~en~Ciel", u""),
                                      (u"\u6249\u306e\u5411\u3053\u3046\u3078",
                                       u"YeLLOW Generation", u""),
                                      (u"UNDO",
                                       u"COOL JOKE", u""),
                                      (u"Motherland",
                                       u"Crystal Kay", u""),
                                      (u"\u30ea\u30e9\u30a4\u30c8",
                                       u"ASIAN KUNG-FU GENERATION", u""),
                                      (u"I Will",
                                       u"Sowelu", u"")]]):
            mb_xml = audiotools.MusicBrainzReleaseXML.from_string(xml_data)

            #first, check that tracks are read properly
            for (i, data) in enumerate(metadata):
                self.assertEqual(track_metadata[i],
                                 mb_xml.get_track(i))

            #then, check that setting tracks round-trip properly
            for i in xrange(len(metadata)):
                mb_xml = audiotools.MusicBrainzReleaseXML.from_string(
                    xml_data)
                mb_xml.set_track(i,
                                 u"Track %d" % (i),
                                 u"Art\u00ecst N\u00e4me" * 40,
                                 u"")
                self.assertEqual(mb_xml.get_track(i),
                                 (u"Track %d" % (i),
                                  u"Art\u00ecst N\u00e4me" * 40,
                                  u""))

            #finally, check that a file with set tracks round-trips
            for i in xrange(len(metadata)):
                mb_xml = audiotools.MusicBrainzReleaseXML.from_string(
                    xml_data)
                mb_xml.set_track(i,
                                 u"Track %d" % (i),
                                 u"Art\u00ecst N\u00e4me" * 40,
                                 u"")
                mb_xml2 = audiotools.MusicBrainzReleaseXML.from_string(
                    mb_xml.to_string())
                self.assertEqual(mb_xml2.get_track(i),
                                 (u"Track %d" % (i),
                                  u"Art\u00ecst N\u00e4me" * 40,
                                  u""))
                self.assertEqual(mb_xml.get_track(i),
                                 mb_xml2.get_track(i))

    @LIB_CORE
    def test_from_tracks(self):
        track_files = [tempfile.NamedTemporaryFile() for i in xrange(5)]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    BLANK_PCM_Reader(1)) for track in track_files]
            metadatas = [
                audiotools.MetaData(track_name=u"Track Name",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=1,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 2",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=2,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 4",
                                    artist_name=u"Special Artist",
                                    album_name=u"Test Album 2",
                                    track_number=4,
                                    track_total=5,
                                    year=u"2009"),
                audiotools.MetaData(track_name=u"Track N\u00e1me 3",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=3,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 5" * 40,
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=5,
                                    track_total=5,
                                    year=u"2010")]
            for (track, metadata) in zip(tracks, metadatas):
                track.set_metadata(metadata)
                self.assertEqual(track.get_metadata(), metadata)
            mb_xml = audiotools.MusicBrainzReleaseXML.from_tracks(tracks)
            self.assertEqual(len(mb_xml), 5)
            self.assertEqual(mb_xml.album_name, u"Test Album")
            self.assertEqual(mb_xml.artist_name, u"Album Artist")
            self.assertEqual(mb_xml.year, u"2010")
            self.assertEqual(mb_xml.catalog, u"")
            self.assertEqual(mb_xml.extra, u"")

            #note that track 4 loses its intentionally malformed
            #album name and year during the round-trip
            for metadata in [
                audiotools.MetaData(track_name=u"Track Name",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=1,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 2",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=2,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 4",
                                    artist_name=u"Special Artist",
                                    album_name=u"Test Album",
                                    track_number=4,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track N\u00e1me 3",
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=3,
                                    track_total=5,
                                    year=u"2010"),
                audiotools.MetaData(track_name=u"Track Name 5" * 40,
                                    artist_name=u"Album Artist",
                                    album_name=u"Test Album",
                                    track_number=5,
                                    track_total=5,
                                    year=u"2010")]:
                self.assertEqual(metadata,
                                 mb_xml.track_metadata(metadata.track_number))
        finally:
            for track in track_files:
                track.close()

    @LIB_CORE
    def test_from_cuesheet(self):
        CUESHEET = """REM DISCID 4A03DD06
PERFORMER "Unknown Artist"
TITLE "Unknown Title"
FILE "cue.wav" WAVE
  TRACK 01 AUDIO
    TITLE "Track01"
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    TITLE "Track02"
    INDEX 00 03:00:21
    INDEX 01 03:02:21
  TRACK 03 AUDIO
    TITLE "Track03"
    INDEX 00 06:00:13
    INDEX 01 06:02:11
  TRACK 04 AUDIO
    TITLE "Track04"
    INDEX 00 08:23:32
    INDEX 01 08:25:32
  TRACK 05 AUDIO
    TITLE "Track05"
    INDEX 00 12:27:40
    INDEX 01 12:29:40
  TRACK 06 AUDIO
    TITLE "Track06"
    INDEX 00 14:32:05
    INDEX 01 14:34:05
"""
        cue_file = tempfile.NamedTemporaryFile(suffix=".cue")
        try:
            cue_file.write(CUESHEET)
            cue_file.flush()

            #from_cuesheet wraps around from_tracks,
            #so I don't need to hit this one so hard
            mb_xml = audiotools.MusicBrainzReleaseXML.from_cuesheet(
                cuesheet=audiotools.read_sheet(cue_file.name),
                total_frames=43646652,
                sample_rate=44100,
                metadata=audiotools.MetaData(album_name=u"Test Album",
                                             artist_name=u"Test Artist"))

            self.assertEqual(mb_xml.album_name, u"Test Album")
            self.assertEqual(mb_xml.artist_name, u"Test Artist")
            self.assertEqual(mb_xml.year, u"")
            self.assertEqual(mb_xml.catalog, u"")
            self.assertEqual(mb_xml.extra, u"")
            self.assertEqual(len(mb_xml), 6)
            for i in xrange(len(mb_xml)):
                self.assertEqual(mb_xml.get_track(i),
                                 (u"", u"", u""))
        finally:
            cue_file.close()


    @LIB_CORE
    def test_missing_fields(self):
        def remove_node(parent, *to_remove):
            toremove_parent = audiotools.walk_xml_tree(parent,
                                                       *to_remove[0:-1])
            if (len(to_remove) > 2):
                self.assertEqual(toremove_parent.tagName, to_remove[-2])
            toremove = audiotools.walk_xml_tree(toremove_parent,
                                                to_remove[-1])
            self.assertEqual(toremove.tagName, to_remove[-1])
            toremove_parent.removeChild(toremove)

        from xml.dom.minidom import parseString

        xml_data = """<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Album Name</title><artist><name>Album Artist</name></artist><release-event-list><event date="2010" catalog-number="cat#"/></release-event-list><track-list><track><title>Track 1</title><duration>272000</duration></track><track><title>Track 2</title><artist><name>Track Artist</name></artist><duration>426333</duration></track><track><title>Track 3</title><duration>249560</duration></track></track-list></release></release-list></metadata>"""

        xml_dom = parseString(xml_data)
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        xml_dom = parseString(xml_data)
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <metadata>
        xml_dom = parseString(xml_data)
        xml_dom.removeChild(xml_dom.firstChild)
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"")
        self.assertEqual(xml.artist_name, u"")
        self.assertEqual(xml.year, u"")
        self.assertEqual(xml.catalog, u"")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 0)

        #removing <release-list>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"")
        self.assertEqual(xml.artist_name, u"")
        self.assertEqual(xml.year, u"")
        self.assertEqual(xml.catalog, u"")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 0)

        #removing <release>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"")
        self.assertEqual(xml.artist_name, u"")
        self.assertEqual(xml.year, u"")
        self.assertEqual(xml.catalog, u"")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 0)

        #removing <title>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release',
                    u'title')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <artist>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release',
                    u'artist')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <artist> -> <name>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release',
                    u'artist', u'name')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <release-event-list>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release',
                    u'release-event-list')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"")
        self.assertEqual(xml.catalog, u"")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <release-event-list> -> <event>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release',
                    u'release-event-list', u'event')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"")
        self.assertEqual(xml.catalog, u"")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <track-list>
        xml_dom = parseString(xml_data)
        remove_node(xml_dom, u'metadata', u'release-list', u'release',
                    u'track-list')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 0)

        #removing <track> (1)
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        track_list.removeChild(track_list.childNodes[0])
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 2)
        self.assertEqual(xml.get_track(0),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 3", u"", u""))

        #removing <track> (1) -> <title>
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        remove_node(track_list.childNodes[0], u'title')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 3)
        self.assertEqual(xml.get_track(0),
                         (u"", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <track> (2)
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        track_list.removeChild(track_list.childNodes[1])
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 2)
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 3", u"", u""))

        #removing <track> (2) -> <title>
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        remove_node(track_list.childNodes[1], u'title')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 3)
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <track> (2) -> <artist>
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        remove_node(track_list.childNodes[1], u'artist')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 3)
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <track> (2) -> <artist> -> <name>
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        remove_node(track_list.childNodes[1], u'artist', u'name')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 3)
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"", u""))
        self.assertEqual(xml.get_track(2),
                         (u"Track 3", u"", u""))

        #removing <track> (3)
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        track_list.removeChild(track_list.childNodes[2])
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 2)
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))

        #removing <track> (3) -> <title>
        xml_dom = parseString(xml_data)
        track_list = audiotools.walk_xml_tree(xml_dom, u'metadata',
                                              u'release-list', u'release',
                                              u'track-list')
        self.assertEqual(track_list.tagName, u'track-list')
        remove_node(track_list.childNodes[2], u'title')
        xml = audiotools.MusicBrainzReleaseXML(xml_dom)
        self.assertEqual(xml.album_name, u"Album Name")
        self.assertEqual(xml.artist_name, u"Album Artist")
        self.assertEqual(xml.year, u"2010")
        self.assertEqual(xml.catalog, u"cat#")
        self.assertEqual(xml.extra, u"")
        self.assertEqual(len(xml), 3)
        self.assertEqual(xml.get_track(0),
                         (u"Track 1", u"", u""))
        self.assertEqual(xml.get_track(1),
                         (u"Track 2", u"Track Artist", u""))
        self.assertEqual(xml.get_track(2),
                         (u"", u"", u""))


    @LIB_CORE
    def test_metadata(self):
        xml = audiotools.MusicBrainzReleaseXML.from_string(
            """<?xml version="1.0" encoding="utf-8"?><metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>Album Name</title><artist><name>Album Artist</name></artist><release-event-list><event date="2010"/></release-event-list><track-list><track><title>Track 1</title><duration>272000</duration></track><track><title>Track 2</title><duration>426333</duration></track><track><title>Track 3</title><duration>249560</duration></track></track-list></release></release-list></metadata>""")

        self.assertEqual(xml.metadata(),
                         audiotools.MetaData(artist_name=u"Album Artist",
                                             album_name=u"Album Name",
                                             track_total=3,
                                             year=u"2010"))

class testcuesheet(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        import audiotools.cue

        self.sheet_class = audiotools.cue.Cuesheet
        self.test_sheets = [
"""eJydlt1q20AQRu8NfofFDxB2Zv/nTshyUBvHQVHa3rppKCbFDqmbtG/f3VqQzZjtxYKvPiOdz6Od
Iw/dWiz727ZfCm1ArpZg57Mhhu1mve6uR7Hofm/vj82vb7tDe3j6I17kRQhPX/ViPmubsbnaXMYL
vUS0xqpgzHx20w2rzbDuBrG42z/uD6970Twfdz+P8ZKxH6+6t3zcHX88xHjVp3TY7r8/XLxuXxbi
c/Opm8+EGIem/SgkiOZu2W9SErPTPcbn7f2jhMUp/B80fd/fDq34cHPpjPRSgldTfL3svqT7S0n/
PhkUi1CsgiIgh2pSnpTJoKoIVZVQ/Q4qhQyESCrwLjE2pGzWRRe76KouTvIuIMlY0nwuKQ6kfdbF
FLuYyi6GQ4G0IgwZ1BahthJqOdQQ+jiDDOqKUFcJdQyKQICRm0F9EeoroZ49arQElhzwLjEOJPMV
CMUuoXIF+FlXkhI3GwDIEhRk3QAQ2QAiVBsy/ryLdtMKTF2KtoM62zl5NgCduiiXQYu2g0rbBcmh
jhRM4pmgRdtBre34eHXcaiSbLRgUtQaVWgPJHnUkJpXwAaRYk1NZl6LWoE5rCHzZIzFOHfPzVdQa
1GnNKL7V6XApguxtCkWtQZ3WELnAjUy/FCCDFrUGlVoDYI/a6CgvOlNsih2hzroUtQZ1WgPPj51J
IqWzFUixmyqeumDRdlhpO+C2s3Eocdn5wUixIZt3KdoOK20HindxcShxI3mX+IDg3b8MLEoQ6yTo
2L8vEA7SCz8do7+XaqGL""".decode('base64').decode('zlib')]

        self.suffix = '.cue'

    def sheets(self):
        for test_sheet in self.test_sheets:
            tempsheetfile = tempfile.NamedTemporaryFile(suffix=self.suffix)
            try:
                tempsheetfile.write(test_sheet)
                tempsheetfile.flush()
                sheet = audiotools.read_sheet(tempsheetfile.name)
            finally:
                tempsheetfile.close()
            yield sheet

    @LIB_CORE
    def testreadsheet(self):
        for sheet in self.sheets():
            self.assertEqual(isinstance(sheet, self.sheet_class), True)
            self.assertEqual(sheet.catalog(), '4580226563955')
            self.assertEqual(sorted(sheet.ISRCs().items()),
                             [(1, 'JPG750800183'),
                              (2, 'JPG750800212'),
                              (3, 'JPG750800214'),
                              (4, 'JPG750800704'),
                              (5, 'JPG750800705'),
                              (6, 'JPG750800706'),
                              (7, 'JPG750800707'),
                              (8, 'JPG750800708'),
                              (9, 'JPG750800219'),
                              (10, 'JPG750800722'),
                              (11, 'JPG750800709'),
                              (12, 'JPG750800290'),
                              (13, 'JPG750800218'),
                              (14, 'JPG750800710'),
                              (15, 'JPG750800217'),
                              (16, 'JPG750800531'),
                              (17, 'JPG750800225'),
                              (18, 'JPG750800711'),
                              (19, 'JPG750800180'),
                              (20, 'JPG750800712'),
                              (21, 'JPG750800713'),
                              (22, 'JPG750800714')])
            self.assertEqual(list(sheet.indexes()),
                             [(0, ), (20885, ), (42189,  42411), (49242,  49473),
                              (52754, ), (69656, ), (95428, ), (118271,  118430),
                              (136968, ), (138433,  138567), (156412, ),
                              (168864, ), (187716, ), (192245, 192373),
                              (200347, ), (204985, ), (227336, ),
                              (243382, 243549), (265893,  266032),
                              (292606, 292942), (302893, 303123), (321611, )])
            self.assertEqual(list(sheet.pcm_lengths(191795016)),
                             [12280380, 12657288, 4152456, 1929228,
                              9938376, 15153936, 13525176, 10900344,
                              940212, 10492860, 7321776, 11084976,
                              2738316, 4688712, 2727144, 13142388,
                              9533244, 13220004, 15823080, 5986428,
                              10870944, 2687748])

    @LIB_CORE
    def testconvertsheet(self):
        import audiotools.cue
        import audiotools.toc

        for sheet in self.sheets():
            #convert to CUE and test for equality
            temp_cue_file = tempfile.NamedTemporaryFile(suffix='.cue')
            try:
                temp_cue_file.write(audiotools.cue.Cuesheet.file(
                        sheet, os.path.basename(temp_cue_file.name)))
                temp_cue_file.flush()

                cue_sheet = audiotools.read_sheet(temp_cue_file.name)

                self.assertEqual(sheet.catalog(), cue_sheet.catalog())
                self.assertEqual(list(sheet.indexes()),
                                 list(cue_sheet.indexes()))
                self.assertEqual(list(sheet.pcm_lengths(191795016)),
                                 list(cue_sheet.pcm_lengths(191795016)))
                self.assertEqual(sorted(sheet.ISRCs().items()),
                                 sorted(cue_sheet.ISRCs().items()))
            finally:
                temp_cue_file.close()

            #convert to TOC and test for equality
            temp_toc_file = tempfile.NamedTemporaryFile(suffix='.toc')
            try:
                temp_toc_file.write(audiotools.toc.TOCFile.file(
                        sheet, os.path.basename(temp_toc_file.name)))
                temp_toc_file.flush()

                toc_sheet = audiotools.read_sheet(temp_toc_file.name)

                self.assertEqual(sheet.catalog(), toc_sheet.catalog())
                self.assertEqual(list(sheet.indexes()),
                                 list(toc_sheet.indexes()))
                self.assertEqual(list(sheet.pcm_lengths(191795016)),
                                 list(toc_sheet.pcm_lengths(191795016)))
                self.assertEqual(sorted(sheet.ISRCs().items()),
                                 sorted(toc_sheet.ISRCs().items()))
            finally:
                temp_toc_file.close()

            #convert to embedded cuesheets and test for equality
            for audio_class in [audiotools.FlacAudio,
                                audiotools.OggFlacAudio,
                                audiotools.WavPackAudio]:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)
                try:
                    f = audio_class.from_pcm(
                        temp_file.name,
                        EXACT_BLANK_PCM_Reader(191795016))
                    f.set_cuesheet(sheet)
                    f_sheet = audiotools.open(temp_file.name).get_cuesheet()
                    self.assertNotEqual(f_sheet, None)

                    self.assertEqual(sheet.catalog(), f_sheet.catalog())
                    self.assertEqual(list(sheet.indexes()),
                                     list(f_sheet.indexes()))
                    self.assertEqual(list(sheet.pcm_lengths(191795016)),
                                     list(f_sheet.pcm_lengths(191795016)))
                    self.assertEqual(sorted(sheet.ISRCs().items()),
                                     sorted(f_sheet.ISRCs().items()))
                finally:
                    temp_file.close()


class testtocsheet(testcuesheet):
    @LIB_CORE
    def setUp(self):
        import audiotools.toc

        self.sheet_class = audiotools.toc.TOCFile
        self.test_sheets = [
"""eJytlr1uG0EMhPt7isU9QExyf4/d4aTYShRJkM4IUglC0qULguT1Q15c7MJbspIhGPhmR8Mhl919
Nw/DMq/z8fzsxhALEKWY/BTjOAxPT2799fj+0+GwXufls5tfd4fzcDq75Xz5pp+X6/6+/3J5mW+H
27B+Pd+Xl/l02h/v///zcLsubvx0ec4RCgAWPw4fD8e9G388fj8+/H38GR04COwL+zhURLIhElKH
+MbTP0JgCDXYW4FDBzwxEfvJAbIXsB9u63xdHQADcaZaR7DRkaGjA4Fj4kAKDokTVTo8Q6p1RCsd
saMDOXgm8cNziEy5BicrcOqABVbEAwdRFYQGnK3A+T2YkJGErWBNn6/BxQpcOuDEmDijZn6LYRM9
mGodk9UITO91eGCVUhSMEweowQhGDlBn6oUsGYtFwxYnjqFyAOWbRohR4WXoWRBUiM9OjJfpg2bs
0ar4JuiQM3vc+iewzF47b2jWfJ34BZl04pS0+cRwat226jrsvFmw2jGg5FDU7eZnbwYQjcqOsDP6
smnEfKLNAuTUko3aLnrskCVtnnFbtFEswIZsVHdEnYKPoG9G1JkTCbklW/Uddt4cpeakYvNWtFI1
2PQdtsk3KjwsnfxJ1YgE3Bpfli76Jn+puT3Iqv96V0+KCvTotvfLGqqESDSbpU9W/Yedgy8JvMhQ
vq2i4Nvroz0Djeow986xjHoFaDq3UtJ0/gOiA7rW""".decode('base64').decode('zlib'),
"""eJytl+tq20AQhX9bT7HoAeKd2Zs0lFLhOMZtbigK9F9wHJGGNHZxlKal+N07uzGkcaDSwhpjzK7Q
fjrMnDMaj8WsXbWbRdfeiOvfYvnUYrdeCnmA2Xgs6vbHetOJ66fbR9GtxYebdvOw6B6X3z7dPvw6
uGk/ZpOqqY7PZiLXppCI1lhVGpNnk8Orw8r/NtOvjfiTCf4cV6ezy2o2vTqpznlpJAWJ6WnY2r65
QEi/3cyb46nIL1f3q/XzSjR33fc2z0bn0/rorD6Z1q9b1aa7e+zy3Z22WdbU1eSLqC4P52dhcX5R
T0T++XzmjCykhEK9XPzKN3p7tt/cnd9sFst7CfnL4n9OH23/eZRw9tHc36BerG7bg+fFz1xISeEr
pCZVkDK9qAgYi4ppUHeE/o/WJPUAVB2LqtKgloRIqhQSSDGqCtdeNFXdBMWRHPbSOxlNr5PQgyRj
SaNH1ZYs7tErknYAvYmlN2nogbQiZO0VaUPoBqDaWFSbBpXxCtZaSOOZ9RBUF4vqkqAiECDTelTf
f2oAahGLWqRBtQSWHHifCI34rvlkOcA6ylj6Mgm9kuQfoPCoUJKW/UJjrCGDTIXKDWYK32mmJKP3
hAZeHVAmsUJDmuRjX2Z65QQXBLuc7DdkLGUsaprkU44UhDjRxPY2wNIQYpsP0iSfZvdFstYnH9cA
DigAiFY1Tcwxpw8K6VF14QvgXfn2uxxCrCFDmpjjCYhrAjEIDWT7UY2CWNQ0MefbTBGEGdOw0NCv
KsYOD5Am5oz0qgJ4S2Nm14/qIFrVNDFnON04i11IZM4KeBdz0O8TUEQ3X5qY47xgbgjzBA+bsD8h
c0X3z/cu+lUE0ySfNZ5QgQgq82S0R8+9OWBChth3PkyTfJaJC/a+3YCk97Xn+b7/NdBFv1thmjB0
4IdmLve//kjXkg==""".decode('base64').decode('zlib')]

        self.suffix = '.toc'


class testflaccuesheet(testcuesheet):
    @LIB_CORE
    def setUp(self):
        self.sheet_class = audiotools.Flac_CUESHEET
        self.suffix = '.flac'
        self.test_sheets = [
            audiotools.Flac_CUESHEET(
                catalog_number='4580226563955\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                lead_in_samples=88200,
                is_cdda=1,
                tracks=[audiotools.Flac_CUESHEET_track(
                        offset=0,
                        number=1,
                        ISRC='JPG750800183',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=12280380,
                        number=2,
                        ISRC='JPG750800212',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=24807132,
                        number=3,
                        ISRC='JPG750800214',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(130536, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=28954296,
                        number=4,
                        ISRC='JPG750800704',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(135828, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=31019352,
                        number=5,
                        ISRC='JPG750800705',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=40957728,
                        number=6,
                        ISRC='JPG750800706',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=56111664,
                        number=7,
                        ISRC='JPG750800707',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=69543348,
                        number=8,
                        ISRC='JPG750800708',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(93492, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=80537184,
                        number=9,
                        ISRC='JPG750800219',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=81398604,
                        number=10,
                        ISRC='JPG750800722',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(78792, 1)]),
                                                audiotools.Flac_CUESHEET_track(
                        offset=91970256,
                        number=11,
                        ISRC='JPG750800709',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=99292032,
                        number=12,
                        ISRC='JPG750800290',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=110377008,
                        number=13,
                        ISRC='JPG750800218',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=113040060,
                        number=14,
                        ISRC='JPG750800710',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(75264, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=117804036,
                        number=15,
                        ISRC='JPG750800217',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=120531180,
                        number=16,
                        ISRC='JPG750800531',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=133673568,
                        number=17,
                        ISRC='JPG750800225',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=143108616,
                        number=18,
                        ISRC='JPG750800711',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(98196, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=156345084,
                        number=19,
                        ISRC='JPG750800180',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(81732, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=172052328,
                        number=20,
                        ISRC='JPG750800712',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(197568, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=178101084,
                        number=21,
                        ISRC='JPG750800713',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 0),
                                      audiotools.Flac_CUESHEET_index(135240, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=189107268,
                        number=22,
                        ISRC='JPG750800714',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[audiotools.Flac_CUESHEET_index(0, 1)]),
                        audiotools.Flac_CUESHEET_track(
                        offset=191795016,
                        number=170,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[])])]

    def sheets(self):
        for test_sheet in self.test_sheets:
            tempflacfile = tempfile.NamedTemporaryFile(suffix=self.suffix)
            try:
                tempflac = audiotools.FlacAudio.from_pcm(
                    tempflacfile.name,
                    EXACT_BLANK_PCM_Reader(191795016),
                    "1")
                metadata = tempflac.get_metadata()
                metadata.cuesheet = test_sheet
                tempflac.set_metadata(metadata)

                sheet = audiotools.open(tempflacfile.name).get_metadata().cuesheet
            finally:
                tempflacfile.close()
            yield sheet


#takes several 1-channel PCMReaders and combines them into a single PCMReader
class PCM_Reader_Multiplexer:
    def __init__(self, pcm_readers, channel_mask):
        self.buffers = map(audiotools.BufferedPCMReader, pcm_readers)
        self.sample_rate = pcm_readers[0].sample_rate
        self.channels = len(pcm_readers)
        self.channel_mask = channel_mask
        self.bits_per_sample = pcm_readers[0].bits_per_sample

    def read(self, bytes):
        return audiotools.pcm.from_channels(
            [reader.read(bytes) for reader in self.buffers])

    def close(self):
        for reader in self.buffers:
            reader.close()



class TestMultiChannel(unittest.TestCase):
    def setUp(self):
        #these support the full range of ChannelMasks
        self.wav_channel_masks = [audiotools.WaveAudio,
                                  audiotools.WavPackAudio]

        #these support a subset of ChannelMasks up to 6 channels
        self.flac_channel_masks = [audiotools.FlacAudio,
                                   audiotools.OggFlacAudio]

        if (audiotools.M4AAudio_nero.has_binaries(audiotools.BIN)):
            self.flac_channel_masks.append(audiotools.M4AAudio_nero)

        #these support a reordered subset of ChannelMasks up to 8 channels
        self.vorbis_channel_masks = [audiotools.VorbisAudio]

    def __test_mask_blank__(self, audio_class, channel_mask):
        temp_file = tempfile.NamedTemporaryFile(suffix="." + audio_class.SUFFIX)
        try:
            temp_track = audio_class.from_pcm(
                temp_file.name,
                PCM_Reader_Multiplexer(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in xrange(len(channel_mask))],
                    channel_mask))
            self.assertEqual(temp_track.channel_mask(), channel_mask,
                             "%s != %s for format %s" %
                             (temp_track.channel_mask(),
                              channel_mask,
                              audio_class.NAME))

            pcm = temp_track.to_pcm()
            self.assertEqual(int(pcm.channel_mask), int(channel_mask))
            audiotools.transfer_framelist_data(pcm, lambda x: x)
            pcm.close()
        finally:
            temp_file.close()

    def __test_undefined_mask_blank__(self, audio_class, channels,
                                      should_be_blank):
        temp_file = tempfile.NamedTemporaryFile(suffix="." + audio_class.SUFFIX)
        try:
            temp_track = audio_class.from_pcm(
                temp_file.name,
                PCM_Reader_Multiplexer(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in xrange(channels)],
                    audiotools.ChannelMask(0)))
            self.assertEqual(temp_track.channels(), channels)
            if (should_be_blank):
                self.assertEqual(int(temp_track.channel_mask()), 0)
                pcm = temp_track.to_pcm()
                self.assertEqual(int(pcm.channel_mask), 0)
                audiotools.transfer_framelist_data(pcm, lambda x: x)
                pcm.close()
            else:
                self.assertNotEqual(int(temp_track.channel_mask()), 0,
                                    "mask = %s for format %s" %
                                    (temp_track.channel_mask(),
                                     audio_class))
                pcm = temp_track.to_pcm()
                self.assertEqual(int(pcm.channel_mask),
                                 int(temp_track.channel_mask()))
                audiotools.transfer_framelist_data(pcm, lambda x: x)
                pcm.close()
        finally:
            temp_file.close()

    def __test_error_mask_blank__(self, audio_class, channels,
                                  channel_mask):
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX)
        try:
            self.assertRaises(audiotools.UnsupportedChannelMask,
                              audio_class.from_pcm,
                              temp_file.name,
                              PCM_Reader_Multiplexer(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in xrange(channels)],
                    channel_mask))
        finally:
            temp_file.close()

    def __test_error_channel_count__(self, audio_class, channels,
                                     channel_mask):
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX)
        try:
            self.assertRaises(audiotools.UnsupportedChannelCount,
                              audio_class.from_pcm,
                              temp_file.name,
                              PCM_Reader_Multiplexer(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in xrange(channels)],
                    channel_mask))
        finally:
            temp_file.close()

    def __test_pcm_conversion__(self,
                                source_audio_class,
                                target_audio_class,
                                channel_mask):
        source_file = tempfile.NamedTemporaryFile(suffix="." + source_audio_class.SUFFIX)
        target_file = tempfile.NamedTemporaryFile(suffix="." + target_audio_class.SUFFIX)
        wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            source_track = source_audio_class.from_pcm(
                source_file.name,
                PCM_Reader_Multiplexer(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in xrange(len(channel_mask))],
                    channel_mask))
            self.assertEqual(source_track.channel_mask(), channel_mask)

            source_pcm = source_track.to_pcm()

            self.assertEqual(isinstance(source_pcm.channel_mask, int),
                             True,
                             "%s's to_pcm() PCMReader is not an int" % \
                                 (source_audio_class.NAME))

            target_track = target_audio_class.from_pcm(
                target_file.name,
                source_pcm)

            self.assertEqual(target_track.channel_mask(), channel_mask)
            self.assertEqual(source_track.channel_mask(),
                             target_track.channel_mask())

            source_track.convert(wav_file.name, audiotools.WaveAudio)
            wav = audiotools.open(wav_file.name)
            wav.verify()
            self.assertEqual(source_track.channel_mask(),
                             wav.channel_mask())
            target_track = wav.convert(target_file.name,
                                       audiotools.WaveAudio)
            self.assertEqual(target_track.channel_mask(), channel_mask)
            self.assertEqual(source_track.channel_mask(),
                             target_track.channel_mask())
        finally:
            source_file.close()
            target_file.close()
            wav_file.close()

    def __test_assignment__(self, audio_class, tone_tracks, channel_mask):
        from audiotools import replaygain as replaygain

        self.assertEqual(len(tone_tracks), len(channel_mask))
        temp_file = tempfile.NamedTemporaryFile(suffix="." + audio_class.SUFFIX)
        gain_calcs = [replaygain.ReplayGain(44100) for t in tone_tracks]
        try:
            temp_track = audio_class.from_pcm(
                temp_file.name,
                PCM_Reader_Multiplexer([t.to_pcm() for t in tone_tracks],
                                       channel_mask))

            pcm = temp_track.to_pcm()
            frame = pcm.read(audiotools.BUFFER_SIZE)
            while (len(frame) > 0):
                for c in xrange(frame.channels):
                    gain_calcs[c].update(frame.channel(c))
                frame = pcm.read(audiotools.BUFFER_SIZE)
            pcm.close()

            self.assertEqual(set([True]),
                             set([prev.replay_gain().track_gain >
                                  curr.replay_gain().track_gain
                                  for (prev, curr) in
                                  zip(tone_tracks, tone_tracks[1:])]))

            gain_values = [gain_calc.title_gain()[0]
                           for gain_calc in gain_calcs]

            self.assertEqual(set([True]),
                             set([prev > curr for (prev, curr) in
                                  zip(gain_values, gain_values[1:])]),
                             "channel mismatch for mask %s with format %s (gain values %s)" % (channel_mask, audio_class.NAME, gain_values))

        finally:
            temp_file.close()

    @LIB_CORE
    def test_channel_mask(self):
        from_fields = audiotools.ChannelMask.from_fields

        for audio_class in (self.wav_channel_masks +
                            self.flac_channel_masks +
                            self.vorbis_channel_masks):
            for mask in [from_fields(front_center=True),
                         from_fields(front_left=True,
                                     front_right=True),
                         from_fields(front_left=True,
                                     front_right=True,
                                     front_center=True),
                         from_fields(front_right=True,
                                     front_left=True,
                                     back_right=True,
                                     back_left=True),
                         from_fields(front_right=True,
                                     front_center=True,
                                     front_left=True,
                                     back_right=True,
                                     back_left=True),
                         from_fields(front_right=True,
                                     front_center=True,
                                     low_frequency=True,
                                     front_left=True,
                                     back_right=True,
                                     back_left=True)]:
                self.__test_mask_blank__(audio_class, mask)

        for audio_class in (self.wav_channel_masks +
                            self.vorbis_channel_masks):
            for mask in [from_fields(front_left=True, front_right=True,
                                     front_center=True,
                                     side_left=True, side_right=True,
                                     back_center=True, low_frequency=True),
                         from_fields(front_left=True, front_right=True,
                                     side_left=True, side_right=True,
                                     back_left=True, back_right=True,
                                     front_center=True, low_frequency=True)]:
                self.__test_mask_blank__(audio_class, mask)

        for audio_class in self.wav_channel_masks:
            for mask in [from_fields(front_left=True, front_right=True,
                                     side_left=True, side_right=True,
                                     back_left=True, back_right=True,
                                     front_center=True, back_center=True,
                                     low_frequency=True),
                         from_fields(front_left=True, front_right=True,
                                     side_left=True, side_right=True,
                                     back_left=True, back_right=True,
                                     front_center=True, back_center=True)]:
                self.__test_mask_blank__(audio_class, mask)

        for mask in [from_fields(front_center=True),
                     from_fields(front_left=True, front_right=True),
                     from_fields(front_left=True, front_right=True,
                                 back_left=True, back_right=True),
                     from_fields(front_left=True, side_left=True,
                                 front_center=True, front_right=True,
                                 side_right=True, back_center=True)]:
            self.__test_mask_blank__(audiotools.AiffAudio, mask)

    @LIB_CORE
    def test_channel_mask_conversion(self):
        from_fields = audiotools.ChannelMask.from_fields

        for source_audio_class in audiotools.AVAILABLE_TYPES:
            for target_audio_class in audiotools.AVAILABLE_TYPES:
                self.__test_pcm_conversion__(source_audio_class,
                                             target_audio_class,
                                             from_fields(front_left=True,
                                                         front_right=True))

        for source_audio_class in (self.wav_channel_masks +
                                   self.flac_channel_masks +
                                   self.vorbis_channel_masks):
            for target_audio_class in (self.wav_channel_masks +
                                       self.flac_channel_masks +
                                       self.vorbis_channel_masks):
                for mask in [from_fields(front_center=True),
                             from_fields(front_left=True,
                                         front_right=True),
                             from_fields(front_left=True,
                                         front_right=True,
                                         front_center=True),
                             from_fields(front_right=True,
                                         front_left=True,
                                         back_right=True,
                                         back_left=True),
                             from_fields(front_right=True,
                                         front_center=True,
                                         front_left=True,
                                         back_right=True,
                                         back_left=True),
                             from_fields(front_right=True,
                                         front_center=True,
                                         low_frequency=True,
                                         front_left=True,
                                         back_right=True,
                                         back_left=True)]:
                    self.__test_pcm_conversion__(source_audio_class,
                                                 target_audio_class,
                                                 mask)

        for source_audio_class in (self.wav_channel_masks +
                                   self.vorbis_channel_masks):
            for target_audio_class in (self.wav_channel_masks +
                                       self.vorbis_channel_masks):
                for mask in [from_fields(front_left=True, front_right=True,
                                         front_center=True,
                                         side_left=True, side_right=True,
                                         back_center=True, low_frequency=True),
                             from_fields(front_left=True, front_right=True,
                                         side_left=True, side_right=True,
                                         back_left=True, back_right=True,
                                         front_center=True, low_frequency=True)]:
                    self.__test_pcm_conversion__(source_audio_class,
                                                 target_audio_class,
                                                 mask)

        for source_audio_class in self.wav_channel_masks:
            for target_audio_class in self.wav_channel_masks:
                for mask in [from_fields(front_left=True, front_right=True,
                                         side_left=True, side_right=True,
                                         back_left=True, back_right=True,
                                         front_center=True, back_center=True,
                                         low_frequency=True),
                             from_fields(front_left=True, front_right=True,
                                         side_left=True, side_right=True,
                                         back_left=True, back_right=True,
                                         front_center=True, back_center=True)]:
                    self.__test_pcm_conversion__(source_audio_class,
                                                 target_audio_class,
                                                 mask)

        for target_audio_class in self.wav_channel_masks:
            for mask in [from_fields(front_center=True),
                         from_fields(front_left=True, front_right=True),
                         from_fields(front_left=True, front_right=True,
                                     back_left=True, back_right=True),
                         from_fields(front_left=True, side_left=True,
                                     front_center=True, front_right=True,
                                     side_right=True, back_center=True)]:
                self.__test_pcm_conversion__(audiotools.AiffAudio,
                                             target_audio_class,
                                             mask)

    @LIB_CORE
    def test_channel_assignment(self):
        from_fields = audiotools.ChannelMask.from_fields

        TONE_TRACKS = map(audiotools.open,
                          ["tone%d.flac" % (i + 1) for i in xrange(8)])

        for audio_class in audiotools.AVAILABLE_TYPES:
            self.__test_assignment__(audio_class,
                                     TONE_TRACKS[0:2],
                                     from_fields(front_left=True,
                                                 front_right=True))

        for audio_class in (self.wav_channel_masks +
                            self.flac_channel_masks +
                            self.vorbis_channel_masks):
            for mask in [from_fields(front_left=True,
                                     front_right=True,
                                     front_center=True),
                         from_fields(front_right=True,
                                     front_left=True,
                                     back_right=True,
                                     back_left=True),
                         from_fields(front_right=True,
                                     front_center=True,
                                     front_left=True,
                                     back_right=True,
                                     back_left=True),
                         from_fields(front_right=True,
                                     front_center=True,
                                     low_frequency=True,
                                     front_left=True,
                                     back_right=True,
                                     back_left=True)]:

                #Encoding 6 channel audio with neroAacEnc
                #with this batch of tones causes Nero to essentially
                #zero out the LFE channel,
                #as does newer versions of oggenc.
                #This is likely due to the characteristics of
                #my input samples.
                if ((len(mask) == 6) and
                    ((audio_class is audiotools.M4AAudio_nero) or
                     (audio_class is audiotools.VorbisAudio))):
                    continue

                self.__test_assignment__(audio_class,
                                         TONE_TRACKS[0:len(mask)],
                                         mask)

        for audio_class in (self.wav_channel_masks +
                            self.vorbis_channel_masks):
            for mask in [from_fields(front_left=True, front_right=True,
                                     front_center=True,
                                     side_left=True, side_right=True,
                                     back_center=True, low_frequency=True),
                         from_fields(front_left=True, front_right=True,
                                     side_left=True, side_right=True,
                                     back_left=True, back_right=True,
                                     front_center=True, low_frequency=True)]:
                self.__test_assignment__(audio_class,
                                         TONE_TRACKS[0:len(mask)],
                                         mask)

        for audio_class in self.wav_channel_masks:
            for mask in [from_fields(front_left=True, front_right=True,
                                     side_left=True, side_right=True,
                                     back_left=True, back_right=True,
                                     front_center=True, back_center=True)]:
                self.__test_assignment__(audio_class,
                                         TONE_TRACKS[0:len(mask)],
                                         mask)

        for mask in [from_fields(front_left=True, front_right=True),
                     from_fields(front_left=True, front_right=True,
                                 back_left=True, back_right=True),
                     from_fields(front_left=True, side_left=True,
                                 front_center=True, front_right=True,
                                 side_right=True, back_center=True)]:
            self.__test_assignment__(audiotools.AiffAudio,
                                     TONE_TRACKS[0:len(mask)],
                                     mask)

    @LIB_CORE
    def test_unsupported_channel_mask_from_pcm(self):
        for channels in xrange(1, 19):
            self.__test_undefined_mask_blank__(audiotools.WaveAudio,
                                               channels,
                                               False)
            self.__test_error_mask_blank__(audiotools.WaveAudio,
                                           19, audiotools.ChannelMask(0))
            self.__test_error_mask_blank__(audiotools.WaveAudio,
                                           20, audiotools.ChannelMask(0))

        for channels in xrange(1, 3):
            self.__test_undefined_mask_blank__(audiotools.WavPackAudio,
                                               channels,
                                               False)
        for channels in xrange(3, 21):
            self.__test_undefined_mask_blank__(audiotools.WavPackAudio,
                                               channels,
                                               True)

        for channels in xrange(1, 3):
            self.__test_undefined_mask_blank__(audiotools.ALACAudio,
                                               channels,
                                               False)
        for channels in xrange(3, 21):
            self.__test_undefined_mask_blank__(audiotools.ALACAudio,
                                               channels,
                                               True)

        for audio_class in [audiotools.FlacAudio, audiotools.OggFlacAudio]:
            for channels in xrange(1, 7):
                self.__test_undefined_mask_blank__(audio_class,
                                                   channels,
                                                   False)
            for channels in xrange(7, 9):
                self.__test_undefined_mask_blank__(audio_class,
                                                   channels,
                                                   True)
            self.__test_error_channel_count__(audio_class,
                                              9, audiotools.ChannelMask(0))
            self.__test_error_channel_count__(audio_class,
                                              10, audiotools.ChannelMask(0))

        for stereo_audio_class in [audiotools.MP3Audio,
                                   audiotools.MP2Audio,
                                   audiotools.M4AAudio_faac]:

            self.__test_undefined_mask_blank__(stereo_audio_class,
                                               2, False)
            for channels in xrange(3, 20):
                temp_file = tempfile.NamedTemporaryFile(suffix="." + stereo_audio_class.SUFFIX)
                try:
                    temp_track = stereo_audio_class.from_pcm(
                        temp_file.name,
                        PCM_Reader_Multiplexer(
                            [BLANK_PCM_Reader(2, channels=1)
                             for i in xrange(channels)],
                            audiotools.ChannelMask(0)))
                    self.assertEqual(temp_track.channels(), 2)
                    self.assertEqual(int(temp_track.channel_mask()),
                                     int(audiotools.ChannelMask.from_fields(
                                front_left=True, front_right=True)))
                    pcm = temp_track.to_pcm()
                    self.assertEqual(int(pcm.channel_mask),
                                     int(temp_track.channel_mask()))
                    audiotools.transfer_framelist_data(pcm, lambda x: x)
                    pcm.close()
                finally:
                    temp_file.close()

        for channels in xrange(1, 9):
            self.__test_undefined_mask_blank__(audiotools.VorbisAudio,
                                               channels,
                                               False)

        for channels in xrange(9, 20):
            self.__test_undefined_mask_blank__(audiotools.VorbisAudio,
                                               channels,
                                               True)

        for channels in [1, 2, 3, 4, 6]:
            self.__test_undefined_mask_blank__(audiotools.AiffAudio,
                                               channels,
                                               False)

        for channels in [5, 7, 8, 9, 10]:
            self.__test_undefined_mask_blank__(audiotools.AiffAudio,
                                               channels,
                                               True)

        for channels in [1, 2]:
            self.__test_undefined_mask_blank__(audiotools.AuAudio,
                                               channels,
                                               False)
        for channels in xrange(3, 11):
            self.__test_undefined_mask_blank__(audiotools.AuAudio,
                                               channels,
                                               True)

        if (audiotools.M4AAudio_nero.has_binaries(audiotools.BIN)):
            for channels in xrange(1, 7):
                self.__test_undefined_mask_blank__(audiotools.M4AAudio_nero,
                                                   channels,
                                                   False)

class __callback__:
    def __init__(self):
        self.called = False

    def call(self):
        self.called = True

class Test_Player(unittest.TestCase):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            BLANK_PCM_Reader(6))

    @LIB_PLAYER
    def tearDown(self):
        self.temp_track_file.close()

    @LIB_PLAYER
    def test_player(self):
        import audiotools.player
        import time

        callback = __callback__()
        player = audiotools.player.Player(audiotools.player.NULLAudioOutput(),
                                          next_track_callback=callback.call)
        self.assertEqual(callback.called, False)
        self.assertEqual(player.progress(), (0, 0))
        player.open(self.temp_track)
        player.play()
        time.sleep(1)
        (current1, total1) = player.progress()
        self.assertEqual(callback.called, False)
        self.assert_(current1 > 0)
        self.assert_(total1 > 0)
        time.sleep(1)
        (current2, total2) = player.progress()
        self.assertEqual(callback.called, False)
        self.assert_(current2 > current1)
        self.assertEqual(total2, total1)
        time.sleep(1)
        player.pause()
        time.sleep(.5)
        (current3, total3) = player.progress()
        self.assertEqual(callback.called, False)
        self.assert_(current3 > current2)
        self.assertEqual(total3, total1)
        time.sleep(1)
        (current4, total4) = player.progress()
        self.assertEqual(callback.called, False)
        self.assertEqual(current4, current3)
        self.assertEqual(total4, total1)
        player.play()
        time.sleep(6)
        self.assertEqual(callback.called, True)

class Test_CDPlayer(unittest.TestCase):
    @LIB_PLAYER
    def setUp(self):
        self.input_dir = tempfile.mkdtemp()

        self.stream = test_streams.Sine16_Stereo(793800, 44100,
                                                 8820.0, 0.70,
                                                 4410.0, 0.29, 1.0)

        self.cue_file = os.path.join(self.input_dir, "CDImage.cue")
        self.bin_file = os.path.join(self.input_dir, "CDImage.bin")

        f = open(self.cue_file, "w")
        f.write('FILE "CDImage.wav" WAVE\r\n  TRACK 01 AUDIO\r\n    ISRC JPPI00652340\r\n    INDEX 01 00:00:00\r\n  TRACK 02 AUDIO\r\n    ISRC JPPI00652349\r\n    INDEX 00 00:06:00\r\n    INDEX 01 00:08:00\r\n  TRACK 03 AUDIO\r\n    ISRC JPPI00652341\r\n    INDEX 00 00:9:00\r\n    INDEX 01 00:11:00\r\n')
        f.close()

        f = open(self.bin_file, "w")
        audiotools.transfer_framelist_data(self.stream, f.write)
        f.close()

        self.cdda = audiotools.CDDA(self.cue_file)

    @LIB_PLAYER
    def tearDown(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

    @LIB_PLAYER
    def test_player(self):
        import audiotools.player
        import time

        callback = __callback__()
        player = audiotools.player.CDPlayer(
            self.cdda,
            audiotools.player.NULLAudioOutput(),
            next_track_callback=callback.call)
        self.assertEqual(callback.called, False)
        self.assertEqual(player.progress(), (0, 0))
        player.open(1)
        player.play()
        time.sleep(1)
        (current1, total1) = player.progress()
        self.assertEqual(callback.called, False)
        self.assert_(current1 > 0)
        self.assert_(total1 > 0)
        time.sleep(1)
        (current2, total2) = player.progress()
        self.assertEqual(callback.called, False)
        self.assert_(current2 > current1)
        self.assertEqual(total2, total1)
        time.sleep(1)
        player.pause()
        time.sleep(.5)
        (current3, total3) = player.progress()
        self.assertEqual(callback.called, False)
        self.assert_(current3 > current2)
        self.assertEqual(total3, total1)
        time.sleep(1)
        (current4, total4) = player.progress()
        self.assertEqual(callback.called, False)
        self.assertEqual(current4, current3)
        self.assertEqual(total4, total1)
        player.play()
        time.sleep(6)
        self.assertEqual(callback.called, True)
