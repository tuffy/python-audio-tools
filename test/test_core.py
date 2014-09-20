#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

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

import sys
import unittest
import audiotools
import struct
import random
import tempfile
import decimal
import os
import os.path
import test_streams
from io import BytesIO
from hashlib import md5

from test import (parser, Variable_Reader, BLANK_PCM_Reader,
                  RANDOM_PCM_Reader, EXACT_SILENCE_PCM_Reader,
                  EXACT_BLANK_PCM_Reader, SHORT_PCM_COMBINATIONS,
                  MD5_Reader, FrameCounter, Join_Reader,
                  Combinations, Possibilities,
                  TEST_COVER1, TEST_COVER2, TEST_COVER3, HUGE_BMP)


def do_nothing(self):
    pass


# add a bunch of decorator metafunctions like LIB_CORE
# which can be wrapped around individual tests as needed
for section in parser.sections():
    for option in parser.options(section):
        if (parser.getboolean(section, option)):
            vars()["%s_%s" % (section.upper(),
                              option.upper())] = lambda function: function
        else:
            vars()["%s_%s" % (section.upper(),
                              option.upper())] = lambda function: do_nothing


if (sys.version_info[0] >= 3):
    def ints_to_bytes(l):
        return bytes(l)
else:
    def ints_to_bytes(l):
        return b"".join(map(chr, l))


class PCMReader(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        # try reading lots of bps/signed/endianness combinations
        for bps in [8, 16, 24]:
            for big_endian in [True, False]:
                for signed in [True, False]:
                    reader = audiotools.PCMFileReader(
                        BytesIO(
                            from_list(list(range(-5, 5)),
                                      1,
                                      bps,
                                      True).to_bytes(big_endian, signed)),
                        sample_rate=44100,
                        channels=1,
                        channel_mask=0x4,
                        bits_per_sample=bps,
                        signed=signed,
                        big_endian=big_endian)

                    self.assertEqual(reader.sample_rate, 44100)
                    self.assertEqual(reader.channels, 1)
                    self.assertEqual(reader.channel_mask, 0x4)
                    self.assertEqual(reader.bits_per_sample, bps)

                    # ensure the FrameList is read correctly
                    f = reader.read((bps // 8) * 10)
                    self.assertEqual(len(f), 10)
                    self.assertEqual(list(f), list(range(-5, 5)))

                    # ensure subsequent reads return empty FrameLists
                    for i in range(10):
                        f = reader.read((bps // 8) * 10)
                        self.assertEqual(len(f), 0)

                    # ensure closing the stream raises ValueErrors
                    # on subsequent reads
                    reader.close()

                    self.assertRaises(ValueError, reader.read, (bps // 8) * 10)


class PCMCat(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        # ensure mismatched streams raise ValueError at init time
        audiotools.PCMCat([audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=44100,
                                                    channels=1,
                                                    channel_mask=0x4,
                                                    bits_per_sample=16)])

        self.assertRaises(ValueError,
                          audiotools.PCMCat,
                          [audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=96000,
                                                    channels=1,
                                                    channel_mask=0x4,
                                                    bits_per_sample=16),
                           audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=44100,
                                                    channels=1,
                                                    channel_mask=0x4,
                                                    bits_per_sample=16)])

        self.assertRaises(ValueError,
                          audiotools.PCMCat,
                          [audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=44100,
                                                    channels=2,
                                                    channel_mask=0x3,
                                                    bits_per_sample=16),
                           audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=44100,
                                                    channels=1,
                                                    channel_mask=0x4,
                                                    bits_per_sample=16)])

        self.assertRaises(ValueError,
                          audiotools.PCMCat,
                          [audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=44100,
                                                    channels=1,
                                                    channel_mask=0x4,
                                                    bits_per_sample=24),
                           audiotools.PCMFileReader(BytesIO(b""),
                                                    sample_rate=44100,
                                                    channels=1,
                                                    channel_mask=0x4,
                                                    bits_per_sample=16)])

        main_readers = [
            audiotools.PCMFileReader(
                BytesIO(
                    from_list(samples, 1, 16, True).to_bytes(True,
                                                             True)),
                sample_rate=44100,
                channels=1,
                channel_mask=0x4,
                bits_per_sample=16,
                signed=True,
                big_endian=True)
            for samples in [range(-15, -5), range(-5, 5), range(5, 15)]]

        reader = audiotools.PCMCat(main_readers)

        # ensure PCMCat's stream attributes match first reader's
        self.assertEqual(reader.sample_rate, 44100)
        self.assertEqual(reader.channels, 1)
        self.assertEqual(reader.channel_mask, 0x4)
        self.assertEqual(reader.bits_per_sample, 16)

        # ensure all the substreams are read correctly
        samples = []
        f = reader.read(2)
        while (len(f) > 0):
            samples.extend(list(f))
            f = reader.read(2)

        self.assertEqual(samples, list(range(-15, 15)))

        # ensure subsequent reads return empty FrameLists
        for i in range(10):
            self.assertEqual(len(reader.read(2)), 0)

        # main readers should not yet be closed
        for r in main_readers:
            for i in range(10):
                self.assertEqual(len(r.read(2)), 0)

        # ensure closing the stream raises ValueErrors
        # on subsequent reads
        reader.close()

        self.assertRaises(ValueError, reader.read, 2)

        # sub readers should also be closed by PCMCat's close()
        for r in main_readers:
            self.assertRaises(ValueError, r.read, 2)


class BufferedPCMReader(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        def frame_lengths(reader, pcm_frames):
            frame = reader.read(pcm_frames)
            while (len(frame) > 0):
                yield frame.frames
                frame = reader.read(pcm_frames)
            else:
                reader.close()

        # ensure our reader is generating randomly-sized frames
        reader = Variable_Reader(EXACT_BLANK_PCM_Reader(4096 * 100))
        self.assertGreater(len(set(frame_lengths(reader, 4096))), 1)

        # then, ensure that wrapped our reader in a BufferedPCMReader
        # results in equal-sized frames
        reader = audiotools.BufferedPCMReader(
            Variable_Reader(EXACT_BLANK_PCM_Reader(4096 * 100)))
        # (make sure to account for bps/channels in frame_lengths())
        self.assertEqual(set(frame_lengths(reader, 4096)), set([4096]))

        # check that sample_rate, bits_per_sample, channel_mask and channels
        # pass-through properly
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

        # ensure that random-sized reads also work okay
        total_frames = 4096 * 1000
        reader = audiotools.BufferedPCMReader(
            Variable_Reader(EXACT_BLANK_PCM_Reader(total_frames)))
        while (total_frames > 0):
            frames = min(total_frames, random.choice(range(1, 1000)))
            frame = reader.read(frames)
            self.assertEqual(frame.frames, frames)
            total_frames -= frame.frames

        # ensure reading after the stream has been exhausted
        # results in empty FrameLists
        reader = audiotools.BufferedPCMReader(
            EXACT_BLANK_PCM_Reader(44100))
        f = reader.read(4096)
        while (len(f) > 0):
            f = reader.read(4096)

        self.assertEqual(len(f), 0)

        for i in range(10):
            f = reader.read(4096)
            self.assertEqual(len(f), 0)

        # and ensure reading after the stream is closed
        # raises a ValueError
        reader.close()

        self.assertRaises(ValueError,
                          reader.read,
                          4096)


class LimitedPCMReader(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        main_reader = audiotools.PCMFileReader(
            BytesIO(
                from_list(list(range(-50, 50)),
                          1,
                          16,
                          True).to_bytes(True, True)),
            sample_rate=44100,
            channels=1,
            channel_mask=0x4,
            bits_per_sample=16,
            signed=True,
            big_endian=True)

        total_samples = []
        for pcm_frames in [10, 20, 30, 40]:
            reader_samples = []
            reader = audiotools.LimitedPCMReader(main_reader, pcm_frames)
            self.assertEqual(reader.sample_rate, 44100)
            self.assertEqual(reader.channels, 1)
            self.assertEqual(reader.channel_mask, 0x4)
            self.assertEqual(reader.bits_per_sample, 16)

            f = reader.read(2)
            while (len(f) > 0):
                reader_samples.extend(list(f))
                f = reader.read(2)

            self.assertEqual(len(reader_samples), pcm_frames)

            total_samples.extend(reader_samples)

            # ensure subsequent reads return empty FrameLists
            for i in range(10):
                self.assertEqual(len(reader.read(2)), 0)

            # ensure closing the substream raises ValueErrors
            # on subsequent reads
            # (note that this doesn't close the main reader)
            reader.close()

            self.assertRaises(ValueError, reader.read, 2)

        self.assertEqual(total_samples, list(range(-50, 50)))

        # ensure subsequent reads of main reader return empty FrameLists
        for i in range(10):
            self.assertEqual(len(main_reader.read(2)), 0)

        # ensure closing the substream raises ValueErrors
        # on subsequent reads
        main_reader.close()

        self.assertRaises(ValueError, main_reader.read, 2)


class PCMReaderWindow(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        for initial_offset in range(-5, 5):
            for pcm_frames in range(5, 15):
                main_reader = audiotools.PCMFileReader(
                    BytesIO(
                        from_list(list(range(1, 11)),
                                  1,
                                  16,
                                  True).to_bytes(True, True)),
                    sample_rate=44100,
                    channels=1,
                    channel_mask=0x4,
                    bits_per_sample=16,
                    signed=True,
                    big_endian=True)

                reader = audiotools.PCMReaderWindow(main_reader,
                                                    initial_offset,
                                                    pcm_frames)

                self.assertEqual(reader.sample_rate,
                                 main_reader.sample_rate)
                self.assertEqual(reader.channels,
                                 main_reader.channels)
                self.assertEqual(reader.channel_mask,
                                 main_reader.channel_mask)
                self.assertEqual(reader.bits_per_sample,
                                 main_reader.bits_per_sample)

                # ensure reads generate the proper window of samples
                samples = []
                f = reader.read(2)
                while (len(f) > 0):
                    samples.extend(list(f))
                    f = reader.read(2)

                self.assertEqual(len(samples), pcm_frames)

                target_samples = list(range(1, 11))
                if (initial_offset < 0):
                    # negative offsets pad window with 0s
                    target_samples = (([0] * abs(initial_offset)) +
                                      target_samples)
                elif (initial_offset > 0):
                    # positive offsets remove samples from window
                    target_samples = target_samples[initial_offset:]

                if (len(target_samples) < pcm_frames):
                    # window longer than samples gets padded with 0s
                    target_samples += [0] * (pcm_frames - len(target_samples))
                elif (len(target_samples) > pcm_frames):
                    # window shorder than samples truncates samples
                    target_samples = target_samples[0:pcm_frames]

                self.assertEqual(samples, target_samples)

                # ensure subsequent reads return empty FrameLists
                for i in range(10):
                    self.assertEqual(len(reader.read(2)), 0)

                # ensure closing the PCMReaderWindow
                # generates ValueErrors on subsequent reads
                reader.close()

                self.assertRaises(ValueError, reader.read, 2)

                # ensure closing the PCMReaderWindow
                # closes the main PCMReader also
                self.assertRaises(ValueError, main_reader.read, 2)


class Sines(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        for stream in [
            test_streams.Generate01(44100),
            test_streams.Generate02(44100),
            test_streams.Generate03(44100),
            test_streams.Generate04(44100),

            test_streams.Sine8_Mono(200000, 48000,
                                    441.0, 0.50, 441.0, 0.49),
            test_streams.Sine8_Stereo(200000, 48000,
                                      441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine16_Mono(200000, 48000,
                                     441.0, 0.50, 441.0, 0.49),
            test_streams.Sine16_Stereo(200000, 48000,
                                       441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Sine24_Mono(200000, 48000,
                                     441.0, 0.50, 441.0, 0.49),
            test_streams.Sine24_Stereo(200000, 48000,
                                       441.0, 0.50, 441.0, 0.49, 1.0),
            test_streams.Simple_Sine(200000, 44100, 0x3F, 16,
                                     (6400, 10000),
                                     (11520, 15000),
                                     (16640, 20000),
                                     (21760, 25000),
                                     (26880, 30000),
                                     (30720, 35000)),

            test_streams.fsd16([1, -1], 100),

            test_streams.WastedBPS16(1000)]:

            # read the base data from the stream
            f = stream.read(4096)
            while (len(f) > 0):
                f = stream.read(4096)

            # ensure subsequent reads return empty FrameLists
            for i in range(10):
                self.assertEqual(len(stream.read(4096)), 0)

            # ensure subsequent reads on a closed stream
            # raises ValueError
            stream.close()

            self.assertRaises(ValueError, stream.read, 4096)


class CDDA(unittest.TestCase):
    @LIB_CDIO
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bin = os.path.join(self.temp_dir, "Test.BIN")
        self.cue = os.path.join(self.temp_dir, "Test.CUE")

        bin_file = open(self.bin, "wb")
        self.reader = test_streams.Sine16_Stereo(43646652, 44100,
                                                 441.0, 0.50,
                                                 4410.0, 0.49, 1.0)
        audiotools.transfer_framelist_data(self.reader, bin_file.write)
        bin_file.close()

        with open(self.cue, "wb") as f1:
            with open("cdda_test.cue", "rb") as f2:
                f1.write(f2.read())

    @LIB_CDIO
    def tearDown(self):
        os.unlink(self.bin)
        os.unlink(self.cue)
        os.rmdir(self.temp_dir)

    @LIB_CDIO
    def test_cdda(self):
        from audiotools.cdio import CDDAReader

        cdda = CDDAReader(self.cue)

        self.assertEqual(cdda.is_cd_image, True)
        self.assertEqual(cdda.sample_rate, 44100)
        self.assertEqual(cdda.channels, 2)
        self.assertEqual(cdda.channel_mask, 0x3)
        self.assertEqual(cdda.bits_per_sample, 16)
        self.assertEqual(cdda.first_sector, 0)
        self.assertEqual(cdda.last_sector, (43646652 // 588) - 1)
        self.assertEqual(cdda.track_lengths,
                         {1: 8038548,
                          2: 7932120,
                          3: 6318648,
                          4: 10765104,
                          5: 5491920,
                          6: 5100312})
        self.assertEqual(cdda.track_offsets,
                         {1: 0,
                          2: 8038548,
                          3: 15970668,
                          4: 22289316,
                          5: 33054420,
                          6: 38546340})

        # verify whole disc
        checksum = md5()
        audiotools.transfer_framelist_data(cdda, checksum.update)
        self.assertEqual(self.reader.hexdigest(),
                         checksum.hexdigest())

        # ensure subsequent reads keep generating empty framelists
        for i in range(10):
            self.assertEqual(cdda.read(44100).frames, 0)

        # verify individual track sections
        for track_num in sorted(cdda.track_offsets.keys()):
            offset = cdda.track_offsets[track_num]
            length = cdda.track_lengths[track_num]
            remaining_offset = offset - cdda.seek(offset)
            self.reader.reset()
            self.assertTrue(audiotools.pcm_cmp(
                audiotools.PCMReaderWindow(cdda,
                                           remaining_offset,
                                           length,
                                           False),
                audiotools.PCMReaderWindow(self.reader, offset, length)))

        # verify close raises exceptions when reading/seeking
        cdda.close()
        self.assertRaises(ValueError, cdda.read, 10)

        self.assertRaises(ValueError, cdda.seek, 10)


class ChannelMask(unittest.TestCase):
    @LIB_CORE
    def test_mask(self):
        mask = audiotools.ChannelMask.from_fields()
        self.assertFalse(mask.defined())
        self.assertTrue(mask.undefined())
        self.assertEqual(len(mask), 0)
        self.assertEqual(set([]), set(mask.channels()))
        mask2 = audiotools.ChannelMask(int(mask))
        self.assertEqual(mask, mask2)

        mask_fields = list(audiotools.ChannelMask.SPEAKER_TO_MASK.keys())
        for count in range(1, len(mask_fields) + 1):
            for fields in Combinations(mask_fields, count):
                # build a mask from fields
                mask = audiotools.ChannelMask.from_fields(
                    **dict([(field, True) for field in fields]))
                self.assertTrue(mask.defined())
                self.assertFalse(mask.undefined())
                self.assertEqual(len(mask), len(fields))
                self.assertEqual(set(fields), set(mask.channels()))
                mask2 = audiotools.ChannelMask(int(mask))
                self.assertEqual(mask, mask2)


class Filename(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file1 = os.path.join(self.temp_dir, "file1")
        self.temp_file2 = os.path.join(self.temp_dir, "file2")
        f = open(self.temp_file1, "w")
        f.write("hello world")
        f.close()
        os.link(self.temp_file1, self.temp_file2)

    def tearDown(self):
        os.unlink(self.temp_file1)
        os.unlink(self.temp_file2)
        os.rmdir(self.temp_dir)

    @LIB_CORE
    def test_filename(self):
        file1 = audiotools.Filename(self.temp_file1)
        file2 = audiotools.Filename(self.temp_file2)
        file3 = audiotools.Filename(os.path.join(self.temp_dir, "file3"))
        file4 = audiotools.Filename(os.path.join(self.temp_dir, "./file3"))
        file5 = audiotools.Filename(os.path.join(self.temp_dir, "file4"))

        self.assertTrue(file1.disk_file())
        self.assertTrue(file2.disk_file())
        self.assertNotEqual(str(file1), str(file2))
        self.assertNotEqual(u"%s" % (file1,), u"%s" % (file2,))
        self.assertEqual(file1, file2)
        self.assertEqual(hash(file1), hash(file2))

        self.assertFalse(file3.disk_file())
        self.assertNotEqual(str(file1), str(file3))
        self.assertNotEqual(u"%s" % (file1,), u"%s" % (file3,))
        self.assertNotEqual(file1, file3)
        self.assertNotEqual(hash(file1), hash(file3))

        self.assertFalse(file4.disk_file())
        self.assertEqual(str(file3), str(file4))
        self.assertEqual(u"%s" % (file3,), u"%s" % (file4,))
        self.assertEqual(file3, file4)
        self.assertEqual(hash(file3), hash(file4))

        self.assertFalse(file5.disk_file())
        self.assertNotEqual(str(file3), str(file5))
        self.assertNotEqual(u"%s" % (file3,), u"%s" % (file5,))
        self.assertNotEqual(file3, file5)
        self.assertNotEqual(hash(file3), hash(file5))


class ImageJPEG(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        with open("imagejpeg_setup.jpg", "rb") as f:
            self.image = f.read()
        self.md5sum = "f8c43ff52c53aff1625979de47a04cec"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/jpeg"

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
        with open("imagepng_setup.png", "rb") as f:
            self.image = f.read()
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
        with open("imagegif_setup.gif", "rb") as f:
            self.image = f.read()
        self.md5sum = "1d4d36801b53c41d01086cbf9d0cb471"
        self.width = 12
        self.height = 21
        self.bpp = 8
        self.colors = 32
        self.mime_type = "image/gif"


class ImageBMP(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        with open("imagebmp_setup.bmp", "rb") as f:
            self.image = f.read()
        self.md5sum = "cb6ef2f7a458ab1d315c329f72ec9898"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/x-ms-bmp"


class ImageTIFF(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        with open("imagetiff_setup.tiff", "rb") as f:
            self.image = f.read()
        self.md5sum = "192ceb086d217421a5f151cc0afa3f05"
        self.width = 12
        self.height = 21
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/tiff"


class ImageHugeBMP(ImageJPEG):
    @LIB_CORE
    def setUp(self):
        from bz2 import decompress
        self.image = decompress(HUGE_BMP)
        self.md5sum = "558d875195829de829059fd4952fed46"
        self.width = 2366
        self.height = 2366
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/x-ms-bmp"


class PCMConverter(unittest.TestCase):
    @LIB_PCM
    def setUp(self):
        self.tempwav = tempfile.NamedTemporaryFile(suffix=".wav")

    @LIB_PCM
    def tearDown(self):
        self.tempwav.close()

    @LIB_PCM
    def test_conversions(self):
        for ((i_sample_rate,
              i_channels,
              i_channel_mask,
              i_bits_per_sample),
             (o_sample_rate,
              o_channels,
              o_channel_mask,
              o_bits_per_sample)) in Combinations(SHORT_PCM_COMBINATIONS, 2):

            reader = BLANK_PCM_Reader(5,
                                      sample_rate=i_sample_rate,
                                      channels=i_channels,
                                      bits_per_sample=i_bits_per_sample,
                                      channel_mask=i_channel_mask)

            converter = audiotools.PCMConverter(
                reader,
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

    @LIB_PCM
    def test_pcm(self):
        for (in_sample_rate,
             (in_channels,
              in_channel_mask),
             in_bits_per_sample) in Possibilities([44100, 96000],
                                                  [(1, 0x4),
                                                   (2, 0x3),
                                                   (4, 0x33)],
                                                  [16, 24]):
            for (out_sample_rate,
                 (out_channels,
                  out_channel_mask),
                 out_bits_per_sample) in Possibilities([44100, 96000],
                                                       [(1, 0x4),
                                                        (2, 0x3),
                                                        (4, 0x33)],
                                                       [16, 24]):

                main_reader = BLANK_PCM_Reader(
                    length=1,
                    sample_rate=in_sample_rate,
                    channels=in_channels,
                    bits_per_sample=in_bits_per_sample,
                    channel_mask=in_channel_mask)

                reader = audiotools.PCMConverter(
                    pcmreader=main_reader,
                    sample_rate=out_sample_rate,
                    channels=out_channels,
                    channel_mask=out_channel_mask,
                    bits_per_sample=out_bits_per_sample)

                # read contents of converted stream
                f = reader.read(4096)
                while (len(f) > 0):
                    f = reader.read(4096)

                # ensure subsequent reads return empty FrameLists
                for i in range(10):
                    self.assertEqual(len(reader.read(4096)), 0)

                # ensure closing stream raises ValueErrors
                # on subsequent reads
                reader.close()

                self.assertRaises(ValueError, reader.read, 4096)

                # ensure main reader is also closed
                # when converter is closed
                self.assertRaises(ValueError, main_reader.read, 4096)


class Test_ReplayGain(unittest.TestCase):
    @LIB_CORE
    def test_replaygain(self):
        # a trivial test of the ReplayGain container

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


class Test_group_tracks(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.output_format = audiotools.FlacAudio
        self.track_files = [
            tempfile.NamedTemporaryFile(
                suffix="." + self.output_format.SUFFIX)
            for i in range(5)]
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
        groupings.sort(key=lambda x: x[0].get_metadata().album_name)
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
        self.dummy1.write(b"12345" * 1000)
        self.dummy1.flush()
        self.dummy2.write(b"54321" * 1000)
        self.dummy2.flush()

        with open("flac-allframes.flac", "rb") as f:
            data = f.read()
        self.dummy3.write(data[0:0x4] + b"\xFF" + data[0x5:])
        self.dummy3.flush()

    @LIB_CORE
    def tearDown(self):
        self.dummy1.close()
        self.dummy2.close()
        self.dummy3.close()

    @LIB_CORE
    def test_open(self):
        # ensure open on dummy file raises UnsupportedFile
        self.assertRaises(audiotools.UnsupportedFile,
                          audiotools.open,
                          self.dummy1.name)

        # ensure open on nonexistent file raises IOError
        self.assertRaises(IOError,
                          audiotools.open,
                          "/dev/null/foo")

        # ensure open on directory raises IOError
        self.assertRaises(IOError,
                          audiotools.open,
                          "/")

        # ensure open on unreadable file raises IOError
        os.chmod(self.dummy1.name, 0)
        try:
            self.assertRaises(IOError,
                              audiotools.open,
                              self.dummy1.name)
        finally:
            os.chmod(self.dummy1.name, 0o600)

        self.assertRaises(audiotools.InvalidFile,
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
        dummy1.write(b"Hello World")
        dummy1.close()

        tracks = list(audiotools.open_files([track1.filename, track2.filename,
                                             dummy1_name, track3.filename]))
        self.assertEqual([t.filename for t in tracks],
                         [t.filename for t in [track1, track2, track3]])


class Test_sorted_tracks(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    @LIB_CORE
    def tearDown(self):
        import shutil

        shutil.rmtree(self.dir)

    def __clean__(self):
        for f in os.listdir(self.dir):
            os.unlink(os.path.join(self.dir, f))

    def __no_metadata__(self, filename_number):
        return audiotools.WaveAudio.from_pcm(
            os.path.join(self.dir, "%2.2d.wav" % (filename_number)),
            BLANK_PCM_Reader(1))

    def __metadata__(self, filename_number,
                     track_number=None, album_number=None):
        track = audiotools.FlacAudio.from_pcm(
            os.path.join(self.dir, "%2.2d.flac" % (filename_number)),
            BLANK_PCM_Reader(1))
        track.set_metadata(audiotools.MetaData(track_number=track_number,
                                               album_number=album_number))
        return track

    def __test_order__(self, sorted_tracks):
        from random import shuffle

        self.assertGreater(len(sorted_tracks), 1)

        shuffled_tracks = sorted_tracks[:]
        while ([f.filename for f in shuffled_tracks] ==
               [f.filename for f in sorted_tracks]):
            shuffle(shuffled_tracks)

        self.assertNotEqual([f.filename for f in shuffled_tracks],
                            [f.filename for f in sorted_tracks])

        reordered_tracks = audiotools.sorted_tracks(shuffled_tracks)

        self.assertEqual([f.filename for f in reordered_tracks],
                         [f.filename for f in sorted_tracks])

    @LIB_CORE
    def test_sort(self):
        # tracks without metadata come before tracks with metadata
        self.__clean__()
        self.__test_order__([self.__no_metadata__(1),
                             self.__metadata__(2, 2),
                             self.__metadata__(3, 3)])

        self.__clean__()
        self.__test_order__([self.__no_metadata__(3),
                             self.__metadata__(1, 1),
                             self.__metadata__(2, 2)])

        self.__clean__()
        self.__test_order__([self.__no_metadata__(3),
                             self.__no_metadata__(10),
                             self.__metadata__(1, 1),
                             self.__metadata__(2, 2)])

        # tracks without metadata are sorted by filename
        self.__clean__()
        self.__test_order__([self.__no_metadata__(1),
                             self.__no_metadata__(2),
                             self.__no_metadata__(3)])

        self.__clean__()
        self.__test_order__([self.__no_metadata__(1),
                             self.__no_metadata__(2),
                             self.__no_metadata__(10),
                             self.__no_metadata__(11)])

        # tracks without album numbers come before tracks with album numbers
        self.__clean__()
        self.__test_order__([self.__metadata__(3, 3),
                             self.__metadata__(2, 1, 1),
                             self.__metadata__(1, 2, 1)])

        self.__clean__()
        self.__test_order__([self.__metadata__(4, 3),
                             self.__metadata__(3, 4),
                             self.__metadata__(2, 1, 1),
                             self.__metadata__(1, 2, 1)])

        # tracks without album numbers are sorted by track number (if any)
        self.__clean__()
        self.__test_order__([self.__metadata__(3),
                             self.__metadata__(2, 1),
                             self.__metadata__(1, 2)])

        self.__clean__()
        self.__test_order__([self.__metadata__(3, 1),
                             self.__metadata__(2, 2),
                             self.__metadata__(1, 3)])

        # tracks with album numbers are sorted by album number
        # and then by track number (if any)
        self.__clean__()
        self.__test_order__([self.__metadata__(5),
                             self.__metadata__(4, 1, 1),
                             self.__metadata__(3, 2, 1),
                             self.__metadata__(2, 1, 2),
                             self.__metadata__(1, 2, 2)])


class Test_pcm_frame_cmp(unittest.TestCase):
    @LIB_CORE
    def test_pcm_frame_cmp(self):
        from test_formats import CLOSE_PCM_Reader

        reader1 = CLOSE_PCM_Reader(
            test_streams.Sine16_Stereo(44100, 44100,
                                       441.0, 0.50,
                                       4410.0, 0.49, 1.0))
        reader2 = CLOSE_PCM_Reader(
            test_streams.Sine16_Stereo(44100, 44100,
                                       441.0, 0.50,
                                       4410.0, 0.49, 1.0))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertIsNone(audiotools.pcm_frame_cmp(reader1 , reader2))
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)

        reader1 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1))
        reader2 = CLOSE_PCM_Reader(RANDOM_PCM_Reader(1))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertEqual(audiotools.pcm_frame_cmp(reader1, reader2), 0)
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)

        reader1 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1))
        reader2 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1, sample_rate=48000))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertEqual(audiotools.pcm_frame_cmp(reader1, reader2), 0)
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)

        reader1 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1))
        reader2 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1, channels=1))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertEqual(audiotools.pcm_frame_cmp(reader1, reader2), 0)
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)

        reader1 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1))
        reader2 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1, bits_per_sample=24))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertEqual(audiotools.pcm_frame_cmp(reader1, reader2), 0)
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)

        reader1 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1))
        reader2 = CLOSE_PCM_Reader(BLANK_PCM_Reader(1, channel_mask=0x30))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertEqual(audiotools.pcm_frame_cmp(reader1, reader2), 0)
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)

        reader1 = CLOSE_PCM_Reader(BLANK_PCM_Reader(2))
        reader2 = CLOSE_PCM_Reader(
            audiotools.PCMCat([BLANK_PCM_Reader(1), RANDOM_PCM_Reader(1)]))

        self.assertEqual(reader1.closes_called, 0)
        self.assertEqual(reader2.closes_called, 0)
        self.assertEqual(audiotools.pcm_frame_cmp(reader1, reader2), 44100)
        self.assertEqual(reader1.closes_called, 1)
        self.assertEqual(reader2.closes_called, 1)


class TestFrameList(unittest.TestCase):
    if (sys.version_info[0] >= 3):
        @classmethod
        def Bits8(cls):
            for i in range(0, 0xFF + 1):
                yield bytes([i])

        @classmethod
        def Bits16(cls):
            for i in range(0, 0xFF + 1):
                for j in range(0, 0xFF + 1):
                    yield bytes([i, j])

        @classmethod
        def Bits24(cls):
            for i in range(0, 0xFF + 1):
                for j in range(0, 0xFF + 1):
                    for k in range(0, 0xFF + 1):
                        yield bytes([i, j, k])
    else:
        @classmethod
        def Bits8(cls):
            for i in range(0, 0xFF + 1):
                yield chr(i)

        @classmethod
        def Bits16(cls):
            for i in range(0, 0xFF + 1):
                for j in range(0, 0xFF + 1):
                    yield chr(i) + chr(j)

        @classmethod
        def Bits24(cls):
            for i in range(0, 0xFF + 1):
                for j in range(0, 0xFF + 1):
                    for k in range(0, 0xFF + 1):
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
                list(range(-40, 40)))

        for bps in [8, 16, 24]:
            self.assertEqual(list(audiotools.pcm.from_list(
                range((1 << (bps - 1)) - 40,
                      (1 << (bps - 1)) + 40), 1, bps, False)),
                list(range(-40, 40)))

        for channels in range(1, 9):
            for bps in [8, 16, 24]:
                for signed in [True, False]:
                    if (signed):
                        l = [random.choice(range(-40, 40)) for i in
                             range(16 * channels)]
                    else:
                        l = [random.choice(range(0, 80)) for i in
                             range(16 * channels)]
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

        self.assertEqual(
            f.to_bytes(True, True),
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f')
        self.assertEqual(
            f.to_bytes(False, True),
            b'\x01\x00\x03\x02\x05\x04\x07\x06\t\x08\x0b\n\r\x0c\x0f\x0e')
        # FIXME - check signed

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

        self.assertRaises(
            TypeError,
            audiotools.pcm.from_frames,
            [audiotools.pcm.from_list(list(range(2)), 2, 16, False),
             list(range(2))])

        self.assertRaises(
            ValueError,
            audiotools.pcm.from_frames,
            [audiotools.pcm.from_list(list(range(2)), 2, 16, False),
             audiotools.pcm.from_list(list(range(4)), 2, 16, False)])

        self.assertRaises(
            ValueError,
            audiotools.pcm.from_frames,
            [audiotools.pcm.from_list(list(range(2)), 2, 16, False),
             audiotools.pcm.from_list(list(range(2)), 1, 16, False)])

        self.assertRaises(
            ValueError,
            audiotools.pcm.from_frames,
            [audiotools.pcm.from_list(list(range(2)), 2, 16, False),
             audiotools.pcm.from_list(list(range(2)), 2, 8, False)])

        self.assertEqual(list(audiotools.pcm.from_frames(
            [audiotools.pcm.from_list(list(range(2)), 2, 16, True),
             audiotools.pcm.from_list(list(range(2, 4)), 2, 16, True)])),
            list(range(4)))

        self.assertRaises(
            TypeError,
            audiotools.pcm.from_channels,
            [audiotools.pcm.from_list(list(range(2)), 1, 16, False),
             list(range(2))])

        self.assertRaises(
            ValueError,
            audiotools.pcm.from_channels,
            [audiotools.pcm.from_list(list(range(1)), 1, 16, False),
             audiotools.pcm.from_list(list(range(2)), 2, 16, False)])

        self.assertRaises(
            ValueError,
            audiotools.pcm.from_channels,
            [audiotools.pcm.from_list(list(range(2)), 1, 16, False),
             audiotools.pcm.from_list(list(range(3)), 1, 16, False)])

        self.assertRaises(
            ValueError,
            audiotools.pcm.from_channels,
            [audiotools.pcm.from_list(list(range(2)), 1, 16, False),
             audiotools.pcm.from_list(list(range(2)), 1, 8, False)])

        self.assertEqual(list(audiotools.pcm.from_channels(
            [audiotools.pcm.from_list(list(range(2)), 1, 16, True),
             audiotools.pcm.from_list(list(range(2, 4)), 1, 16, True)])),
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

        for i in range(f.frames):
            (f1, f2) = f.split(i)
            self.assertEqual(len(f1), i * f.channels)
            self.assertEqual(len(f2), (len(f) - (i * f.channels)))
            self.assertEqual(list(f1 + f2), list(f))

        import operator

        f1 = audiotools.pcm.from_list(list(range(10)), 2, 16, False)
        self.assertRaises(TypeError, operator.concat, f1, [1, 2, 3])
        f2 = audiotools.pcm.from_list(list(range(10, 20)), 1, 16, False)
        self.assertRaises(ValueError, operator.concat, f1, f2)
        f2 = audiotools.pcm.from_list(list(range(10, 20)), 2, 8, False)
        self.assertRaises(ValueError, operator.concat, f1, f2)

        f1 = audiotools.pcm.from_list(list(range(10)), 2, 16, False)
        self.assertEqual(f1, audiotools.pcm.from_list(range(10), 2, 16, False))
        self.assertNotEqual(f1, 10)
        self.assertNotEqual(f1, list(range(10)))
        self.assertNotEqual(
            f1,
            audiotools.pcm.from_list(list(range(10)), 1, 16, False))
        self.assertNotEqual(
            f1,
            audiotools.pcm.from_list(list(range(10)), 2, 8, False))
        self.assertNotEqual(
            f1,
            audiotools.pcm.from_list(list(range(10)), 1, 8, False))
        self.assertNotEqual(
            f1,
            audiotools.pcm.from_list(list(range(8)), 2, 16, False))
        self.assertNotEqual(
            f1,
            audiotools.pcm.from_list(list(range(12)), 2, 8, False))

    @LIB_CORE
    def test_8bit_roundtrip(self):
        import audiotools.pcm

        unsigned_ints = list(range(0, 0xFF + 1))
        signed_ints = list(range(-0x80, 0x7F + 1))

        # unsigned, big-endian
        self.assertEqual(
            [i - (1 << 7) for i in unsigned_ints],
            list(audiotools.pcm.FrameList(
                struct.pack(">%dB" % (len(unsigned_ints)), *unsigned_ints),
                1, 8, True, False)))

        # unsigned, little-endian
        self.assertEqual(
            [i - (1 << 7) for i in unsigned_ints],
            list(audiotools.pcm.FrameList(
                struct.pack("<%dB" % (len(unsigned_ints)), *unsigned_ints),
                1, 8, False, False)))

        # signed, big-endian
        self.assertEqual(
            signed_ints,
            list(audiotools.pcm.FrameList(
                struct.pack(">%db" % (len(signed_ints)), *signed_ints),
                1, 8, True, True)))

        # signed, little-endian
        self.assertEqual(
            signed_ints,
            list(audiotools.pcm.FrameList(
                struct.pack("<%db" % (len(signed_ints)), *signed_ints),
                1, 8, 0, 1)))

    @LIB_CORE
    def test_8bit_roundtrip_str(self):
        import audiotools.pcm

        s = b"".join(TestFrameList.Bits8())

        # big endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     True, False).to_bytes(True, False), s)

        # big-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     True, True).to_bytes(True, True), s)

        # little-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     False, False).to_bytes(False, False), s)

        # little-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 8,
                                     False, True).to_bytes(False, True), s)

    @LIB_CORE
    def test_16bit_roundtrip(self):
        import audiotools.pcm

        unsigned_ints = list(range(0, 0xFFFF + 1))
        signed_ints = list(range(-0x8000, 0x7FFF + 1))

        # unsigned, big-endian
        self.assertEqual(
            [i - (1 << 15) for i in unsigned_ints],
            list(audiotools.pcm.FrameList(
                struct.pack(">%dH" % (len(unsigned_ints)), *unsigned_ints),
                1, 16, True, False)))

        # unsigned, little-endian
        self.assertEqual(
            [i - (1 << 15) for i in unsigned_ints],
            list(audiotools.pcm.FrameList(
                struct.pack("<%dH" % (len(unsigned_ints)), *unsigned_ints),
                1, 16, False, False)))

        # signed, big-endian
        self.assertEqual(
            signed_ints,
            list(audiotools.pcm.FrameList(
                struct.pack(">%dh" % (len(signed_ints)), *signed_ints),
                1, 16, True, True)))

        # signed, little-endian
        self.assertEqual(
            signed_ints,
            list(audiotools.pcm.FrameList(
                struct.pack("<%dh" % (len(signed_ints)), *signed_ints),
                1, 16, False, True)))

    @LIB_CORE
    def test_16bit_roundtrip_str(self):
        import audiotools.pcm

        s = b"".join(TestFrameList.Bits16())

        # big-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     True, False).to_bytes(True, False),
            s,
            "data mismatch converting UBInt16 through string")

        # big-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     True, True).to_bytes(True, True),
            s,
            "data mismatch converting SBInt16 through string")

        # little-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     False, False).to_bytes(False, False),
            s,
            "data mismatch converting ULInt16 through string")

        # little-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 16,
                                     False, True).to_bytes(False, True),
            s,
            "data mismatch converting USInt16 through string")

    @LIB_CORE
    def test_24bit_roundtrip(self):
        import audiotools.pcm
        from audiotools.bitstream import BitstreamRecorder

        unsigned_values = list(range(0, 2 ** 24, 1024))
        unsigned_values.append(2 ** 24 - 1)

        #unsigned, big-endian
        rec = BitstreamRecorder(0)
        rec.build("%d*24u" % (len(unsigned_values)), unsigned_values)
        framelist = audiotools.pcm.FrameList(rec.data(), 1, 24, True, False)
        self.assertEqual(len(unsigned_values), framelist.frames)
        self.assertEqual(
            [i - (1 << 23) for i in unsigned_values],
            list(framelist))

        #unsigned, little-endian
        rec = BitstreamRecorder(1)
        rec.build("%d*24u" % (len(unsigned_values)), unsigned_values)
        framelist = audiotools.pcm.FrameList(rec.data(), 1, 24, False, False)
        self.assertEqual(len(unsigned_values), framelist.frames)
        self.assertEqual(
            [i - (1 << 23) for i in unsigned_values],
            list(framelist))

        signed_values = list(range(-(2 ** 23), 2 ** 23, 1024))
        signed_values.append(2 ** 23 - 1)

        rec = BitstreamRecorder(0)
        rec.build("%d*24s" % (len(signed_values)), signed_values)
        framelist = audiotools.pcm.FrameList(rec.data(), 1, 24, True, True)
        self.assertEqual(len(signed_values), framelist.frames)
        self.assertEqual(signed_values, list(framelist))

        rec = BitstreamRecorder(1)
        rec.build("%d*24s" % (len(signed_values)), signed_values)
        framelist = audiotools.pcm.FrameList(rec.data(), 1, 24, False, True)
        self.assertEqual(len(signed_values), framelist.frames)
        self.assertEqual(signed_values, list(framelist))

    @LIB_CORE
    def test_24bit_roundtrip_str(self):
        import audiotools.pcm

        s = b"".join(TestFrameList.Bits24())
        # big-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     True, False).to_bytes(True, False), s)

        # big-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     True, True).to_bytes(True, True), s)

        # little-endian, unsigned
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     False, False).to_bytes(False, False), s)

        # little-endian, signed
        self.assertEqual(
            audiotools.pcm.FrameList(s, 1, 24,
                                     False, True).to_bytes(False, True), s)

    @LIB_CORE
    def test_conversion(self):
        for format in audiotools.AVAILABLE_TYPES:
            temp_track = tempfile.NamedTemporaryFile(
                suffix="." + format.SUFFIX)
            try:
                for sine_class in [test_streams.Sine8_Stereo,
                                   test_streams.Sine16_Stereo,
                                   test_streams.Sine24_Stereo]:
                    sine = sine_class(88200,
                                      44100,
                                      441.0,
                                      0.50,
                                      441.0,
                                      0.49,
                                      1.0)
                    try:
                        track = format.from_pcm(temp_track.name, sine)
                    except audiotools.UnsupportedBitsPerSample:
                        continue
                    if (track.lossless()):
                        md5sum = md5()
                        with track.to_pcm() as pcmreader:
                            audiotools.transfer_framelist_data(
                                pcmreader, md5sum.update)
                        self.assertEqual(
                            md5sum.hexdigest(), sine.hexdigest(),
                            "MD5 mismatch for %s using %s" % (
                                track.NAME, repr(sine)))
                        for new_format in audiotools.AVAILABLE_TYPES:
                            temp_track2 = tempfile.NamedTemporaryFile(
                                suffix="." + format.SUFFIX)
                            try:
                                try:
                                    track2 = new_format.from_pcm(
                                        temp_track2.name,
                                        track.to_pcm())
                                except audiotools.UnsupportedBitsPerSample:
                                    continue
                                if (track2.lossless()):
                                    md5sum2 = md5()
                                    with track2.to_pcm() as pcmreader:
                                        audiotools.transfer_framelist_data(
                                            pcmreader, md5sum2.update)
                                    self.assertEqual(
                                        md5sum.hexdigest(),
                                        sine.hexdigest(),
                                        "MD5 mismatch for converting %s from %s to %s" % (repr(sine), track.NAME, track2.NAME))
                            finally:
                                temp_track2.close()
            finally:
                temp_track.close()

    @LIB_CORE
    def test_errors(self):
        # check list that's too large
        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [0.0] * 5, 2)

        # check list that's too small
        self.assertRaises(ValueError,
                          audiotools.pcm.FloatFrameList,
                          [0.0] * 3, 2)

        # check channels <= 0
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

        f = audiotools.pcm.FloatFrameList(list(map(float, range(8))), 2)
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
                         list(audiotools.pcm.from_float_channels([
                             f.channel(0),
                             f.channel(1)])))

        # FIXME - check from_frames
        # FIXME - check from_channels

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

        for i in range(f.frames):
            (f1, f2) = f.split(i)
            self.assertEqual(len(f1), i * f.channels)
            self.assertEqual(len(f2), (len(f) - (i * f.channels)))
            self.assertEqual(list(f1 + f2), list(f))

        import operator

        f1 = audiotools.pcm.FloatFrameList(list(map(float, range(10))), 2)
        self.assertRaises(TypeError, operator.concat, f1, [1, 2, 3])

        # check round-trip from float->int->float
        l = [float(i - 128) / (1 << 7) for i in range(0, 1 << 8)]
        for bps in [8, 16, 24]:
            for signed in [True, False]:
                self.assertEqual(
                    l,
                    list(audiotools.pcm.FloatFrameList(l, 1).to_int(bps).to_float()))

        # check round-trip from int->float->int
        for bps in [8, 16, 24]:
            l = list(range(0, 1 << bps, 4))
            self.assertEqual(
                [i - (1 << (bps - 1)) for i in l],
                list(audiotools.pcm.from_list(l, 1, bps, False).to_float().to_int(bps)))

            l = list(range(-(1 << (bps - 1)), (1 << (bps - 1)) - 1, 4))
            self.assertEqual(
                l,
                list(audiotools.pcm.from_list(l, 1, bps, True).to_float().to_int(bps)))

    @LIB_CORE
    def test_errors(self):
        # check string that's too large
        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          b"\x00" * 5, 2, 16, 1, 1)

        # check string that's too small
        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          b"\x00" * 3, 2, 16, 1, 1)

        # check channels <= 0
        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          b"\x00" * 4, 0, 16, 1, 1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          b"\x00" * 4, -1, 16, 1, 1)

        # check bps != 8,16,24
        for bps in [0, 7, 9, 15, 17, 23, 25, 64]:
            self.assertRaises(ValueError,
                              audiotools.pcm.FrameList,
                              b"\x00" * 4, 2, bps, 1, 1)


class __SimpleChunkReader__:
    def __init__(self, chunks):
        self.chunks = chunks
        self.i = 0

    def read(self, bytes):
        try:
            chunk = self.chunks[self.i]
            self.i += 1
            return chunk
        except IndexError:
            return ""

    def tell(self):
        return self.i

    def seek(self, position):
        self.i = position

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
        # check the bitstream reader
        # against some known big-endian values

        reader.mark()
        self.assertEqual(reader.read(2), 0x2)
        self.assertEqual(reader.read(3), 0x6)
        self.assertEqual(reader.read(5), 0x07)
        self.assertEqual(reader.read(3), 0x5)
        self.assertEqual(reader.read(19), 0x53BC1)

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
        self.assertEqual(reader.read_bytes(2), b"\xB1\xED")
        reader.rewind()
        self.assertEqual(reader.read(4), 11)
        self.assertEqual(reader.read_bytes(2), b"\x1E\xD3")

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

        reader.seek(3, 0)
        self.assertEqual(reader.read(8), 0xC1)
        reader.seek(2, 0)
        self.assertEqual(reader.read(8), 0x3B)
        reader.seek(1, 0)
        self.assertEqual(reader.read(8), 0xED)
        reader.seek(0, 0)
        self.assertEqual(reader.read(8), 0xB1)
        try:
            reader.seek(4, 0)
            reader.read(8)
            self.assertTrue(False)
        except IOError:
            self.assertTrue(True)
        try:
            reader.seek(-1, 0)
            reader.read(8)
            self.assertTrue(False)
        except IOError:
            self.assertTrue(True)

        reader.seek(-1, 2)
        self.assertEqual(reader.read(8), 0xC1)
        reader.seek(-2, 2)
        self.assertEqual(reader.read(8), 0x3B)
        reader.seek(-3, 2)
        self.assertEqual(reader.read(8), 0xED)
        reader.seek(-4, 2)
        self.assertEqual(reader.read(8), 0xB1)
        # BytesIO objects allow seeking to before the beginning
        # of the stream, placing the cursor at the beginning
        # try:
        #     reader.seek(-5, 2)
        #     reader.read(8)
        #     self.assertTrue(False)
        # except IOError:
        #     self.assertTrue(True)
        try:
            reader.seek(1, 2)
            reader.read(8)
            self.assertTrue(False)
        except IOError:
            self.assertTrue(True)

        reader.seek(0, 0)
        reader.seek(3, 1)
        self.assertEqual(reader.read(8), 0xC1)
        reader.seek(0, 0)
        reader.seek(2, 1)
        self.assertEqual(reader.read(8), 0x3B)
        reader.seek(0, 0)
        reader.seek(1, 1)
        self.assertEqual(reader.read(8), 0xED)
        reader.seek(0, 0)
        reader.seek(0, 1)
        self.assertEqual(reader.read(8), 0xB1)
        try:
            reader.seek(0, 0)
            reader.seek(4, 1)
            reader.read(8)
            self.assertTrue(False)
        except IOError:
            self.assertTrue(True)
        # BytesIO objects allow seeking to before the beginning
        # of the stream, placing the cursor at the beginning
        # try:
        #     reader.seek(0, 0)
        #     reader.seek(-1, 1)
        #     reader.read(8)
        #     self.assertTrue(False)
        # except IOError:
        #     self.assertTrue(True)

        reader.seek(0, 2)
        reader.seek(-1, 1)
        self.assertEqual(reader.read(8), 0xC1)
        reader.seek(0, 2)
        reader.seek(-2, 1)
        self.assertEqual(reader.read(8), 0x3B)
        reader.seek(0, 2)
        reader.seek(-3, 1)
        self.assertEqual(reader.read(8), 0xED)
        reader.seek(0, 2)
        reader.seek(-4, 1)
        self.assertEqual(reader.read(8), 0xB1)
        # BytesIO objects allow seeking to before the beginning
        # of the stream, placing the cursor at the beginning
        # try:
        #     reader.seek(0, 2)
        #     reader.seek(-5, 1)
        #     reader.read(8)
        #     self.assertTrue(False)
        # except IOError:
        #     self.assertTrue(True)
        try:
            reader.seek(0, 2)
            reader.seek(1, 1)
            reader.read(8)
            self.assertTrue(False)
        except IOError:
            self.assertTrue(True)

        reader.rewind()
        reader.unmark()

    def __test_little_endian_reader__(self, reader, table):
        # check the bitstream reader
        # against some known little-endian values

        reader.mark()
        self.assertEqual(reader.read(2), 0x1)
        self.assertEqual(reader.read(3), 0x4)
        self.assertEqual(reader.read(5), 0x0D)
        self.assertEqual(reader.read(3), 0x3)
        self.assertEqual(reader.read(19), 0x609DF)

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
        self.assertEqual(reader.read_bytes(2), b"\xB1\xED")
        reader.rewind()
        self.assertEqual(reader.read(4), 1)

        self.assertEqual(reader.read_bytes(2), b"\xDB\xBE")

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

        # bounce to the very end of the stream
        reader.skip(31)
        reader.mark()
        self.assertEqual(reader.read(1), 1)
        reader.rewind()

        # then test all the read methods to ensure they trigger br_abort
        # in the case of unary/Huffman, the stream ends on a "1" bit
        # whether reading it big-endian or little-endian

        self.assertRaises(IOError, reader.read, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.read_signed, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.skip, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.unary, 0)
        reader.rewind()
        self.assertEqual(reader.unary(1), 0)
        self.assertRaises(IOError, reader.unary, 1)
        reader.rewind()
        self.assertRaises(IOError, reader.read_huffman_code, table)
        reader.rewind()
        self.assertRaises(IOError, reader.read_bytes, 2)
        reader.rewind()
        self.assertRaises(IOError, reader.substream, 1)
        reader.rewind()
        self.assertRaises(ValueError, reader.read, -1)
        reader.rewind()
        self.assertRaises(ValueError, reader.read_signed, -1)
        reader.rewind()
        self.assertRaises(ValueError, reader.read_signed, 0)
        reader.rewind()
        self.assertRaises(ValueError, reader.skip, -1)
        reader.rewind()
        self.assertRaises(ValueError, reader.read_bytes, -2)
        reader.rewind()
        self.assertRaises(IOError, reader.skip_bytes, 2 ** 30)
        reader.rewind()
        self.assertRaises(IOError, reader.skip_bytes, 2 ** 65)
        reader.rewind()
        self.assertRaises(IOError, reader.read_bytes, 2 ** 30)
        reader.rewind()
        self.assertRaises(IOError, reader.read_bytes, 2 ** 65)
        reader.rewind()
        self.assertRaises(IOError, reader.substream, 2 ** 30)
        reader.rewind()

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

        # a single callback
        counter.reset()
        for i in range(8):
            reader.read(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        # calling callbacks directly
        counter.reset()
        for i in range(20):
            reader.call_callbacks(0)
        self.assertEqual(int(counter), 20)

        # two callbacks
        counter.reset()
        reader.add_callback(counter.callback)
        for i in range(8):
            reader.read(4)
        self.assertEqual(int(counter), 8)
        reader.pop_callback()
        reader.rewind()

        # temporarily suspending the callback
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

        # temporarily adding two callbacks
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

        # read_signed
        counter.reset()
        for i in range(8):
            reader.read_signed(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        # skip
        counter.reset()
        for i in range(8):
            reader.skip(4)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        # read_unary
        counter.reset()
        for i in range(unary_0_reads):
            reader.unary(0)
        self.assertEqual(int(counter), 4)
        counter.reset()
        reader.rewind()
        for i in range(unary_1_reads):
            reader.unary(1)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        # read_huffman_code
        counter.reset()
        for i in range(huffman_code_count):
            reader.read_huffman_code(table)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        # read_bytes
        counter.reset()
        reader.read_bytes(2)
        reader.read_bytes(2)
        self.assertEqual(int(counter), 4)
        reader.rewind()

        reader.pop_callback()
        reader.unmark()

    @LIB_BITSTREAM
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

    @LIB_BITSTREAM
    def test_parse(self):
        from audiotools.bitstream import parse

        # test basic big-endian string
        self.assertEqual(parse("2u3u5u3s19s",
                               False,
                               ints_to_bytes([0xB1, 0xED, 0x3B, 0xC1])),
                         [2, 6, 7, -3, -181311])

        # test all the defined format fields
        for (fields, values) in [("2u 3u 5u 3u 19u",
                                  [0x2, 0x6, 0x07, 0x5, 0x53BC1]),
                                 ("2s 3s 5s 3s 19s",
                                  [-2, -2, 7, -3, -181311]),
                                 ("2U 3U 5U 3U 19U",
                                  [0x2, 0x6, 0x07, 0x5, 0x53BC1]),
                                 ("2S 3S 5S 3S 19S",
                                  [-2, -2, 7, -3, -181311]),
                                 ("2u 3p 5u 3p 19u",
                                  [0x2, 0x07, 0x53BC1]),
                                 ("2p 1P 3u 19u",
                                  [0x5, 0x53BC1]),
                                 ("2b 2b",
                                  [b"\xB1\xED", b"\x3B\xC1"]),
                                 ("2u a 3u a 4u a 5u",
                                  [2, 7, 3, 24]),
                                 ("3* 2u",
                                  [2, 3, 0]),
                                 ("3* 2* 2u",
                                  [2, 3, 0, 1, 3, 2]),
                                 ("2u ? 3u", [2]),
                                 ("2u 10? 3u", [2]),
                                 ("2u 10* ? 3u", [2]),
                                 ("2u 10* 3? 3u", [2])]:
            self.assertEqual(parse(fields,
                                   False,
                                   ints_to_bytes([0xB1, 0xED, 0x3B, 0xC1])),
                             values)

        # test several big-endian unsigned edge cases
        self.assertEqual(
            parse("32u 32u 32u 32u 64U 64U 64U 64U",
                  False,
                  ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                                 128, 0, 0, 0, 127, 255, 255, 255,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 255, 255, 255, 255, 255, 255, 255, 255,
                                 128, 0, 0, 0, 0, 0, 0, 0,
                                 127, 255, 255, 255, 255, 255, 255, 255])),
            [0,
             4294967295,
             2147483648,
             2147483647,
             0,
             0xFFFFFFFFFFFFFFFF,
             9223372036854775808,
             9223372036854775807])

        # test several big-endian signed edge cases
        self.assertEqual(
            parse("32s 32s 32s 32s 64S 64S 64S 64S",
                  False,
                  ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                                 128, 0, 0, 0, 127, 255, 255, 255,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 255, 255, 255, 255, 255, 255, 255, 255,
                                 128, 0, 0, 0, 0, 0, 0, 0,
                                 127, 255, 255, 255, 255, 255, 255, 255])),
            [0,
             -1,
             -2147483648,
             2147483647,
             0,
             -1,
             -9223372036854775808,
             9223372036854775807])

        # test big-endian read errors
        for s in ["3u", "3s", "3U", "3S", "3p", "3P", "3b"]:
            self.assertRaises(IOError,
                              parse,
                              "8u" + s,
                              False,
                              "a")

        # test basic little-endian string
        self.assertEqual(parse("2u3u5u3s19s",
                               True,
                               ints_to_bytes([0xB1, 0xED, 0x3B, 0xC1])),
                         [1, 4, 13, 3, -128545])

        # test all the defined format fields
        for (fields, values) in [("2u 3u 5u 3u 19u",
                                  [0x1, 0x4, 0x0D, 0x3, 0x609DF]),
                                 ("2s 3s 5s 3s 19s",
                                  [1, -4, 13, 3, -128545]),
                                 ("2U 3U 5U 3U 19U",
                                  [0x1, 0x4, 0x0D, 0x3, 0x609DF]),
                                 ("2S 3S 5S 3S 19S",
                                  [1, -4, 13, 3, -128545]),
                                 ("2u 3p 5u 3p 19u",
                                  [0x1, 0x0D, 0x609DF]),
                                 ("2p 1P 3u 19u",
                                  [0x3, 0x609DF]),
                                 ("2b 2b",
                                  [b"\xB1\xED", b"\x3B\xC1"]),
                                 ("2u a 3u a 4u a 5u",
                                  [1, 5, 11, 1]),
                                 ("3* 2u",
                                  [1, 0, 3]),
                                 ("3* 2* 2u",
                                  [1, 0, 3, 2, 1, 3]),
                                 ("2u ? 3u", [1]),
                                 ("2u 10? 3u", [1]),
                                 ("2u 10* ? 3u", [1]),
                                 ("2u 10* 3? 3u", [1])]:
            self.assertEqual(parse(fields,
                                   True,
                                   ints_to_bytes([0xB1, 0xED, 0x3B, 0xC1])),
                             values)

        # test several little-endian unsigned edge cases
        self.assertEqual(
            parse("32u 32u 32u 32u 64U 64U 64U 64U",
                  True,
                  ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                                 0, 0, 0, 128, 255, 255, 255, 127,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 255, 255, 255, 255, 255, 255, 255, 255,
                                 0, 0, 0, 0, 0, 0, 0, 128,
                                 255, 255, 255, 255, 255, 255, 255, 127])),
            [0,
             4294967295,
             2147483648,
             2147483647,
             0,
             0xFFFFFFFFFFFFFFFF,
             9223372036854775808,
             9223372036854775807])

        # test several little-endian signed edge cases
        self.assertEqual(
            parse("32s 32s 32s 32s 64S 64S 64S 64S",
                  True,
                  ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                                 0, 0, 0, 128, 255, 255, 255, 127,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 255, 255, 255, 255, 255, 255, 255, 255,
                                 0, 0, 0, 0, 0, 0, 0, 128,
                                 255, 255, 255, 255, 255, 255, 255, 127])),
            [0,
             -1,
             -2147483648,
             2147483647,
             0,
             -1,
             -9223372036854775808,
             9223372036854775807])

        # test little-endian read errors
        for s in ["3u", "3s", "3U", "3S", "3p", "3P", "3b"]:
            self.assertRaises(IOError,
                              parse,
                              "8u" + s,
                              True,
                              "a")

    @LIB_BITSTREAM
    def test_build(self):
        from audiotools.bitstream import build

        # test basic big-endian string
        self.assertEqual(build("2u3u5u3s19s",
                               False,
                               [2, 6, 7, -3, -181311]),
                         ints_to_bytes([0xB1, 0xED, 0x3B, 0xC1]))

        # test several big-endian unsigned edge cases
        self.assertEqual(
            build("32u 32u 32u 32u 64U 64U 64U 64U",
                  False,
                  [0,
                   4294967295,
                   2147483648,
                   2147483647,
                   0,
                   0xFFFFFFFFFFFFFFFF,
                   9223372036854775808,
                   9223372036854775807]),
            ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                           128, 0, 0, 0, 127, 255, 255, 255,
                           0, 0, 0, 0, 0, 0, 0, 0,
                           255, 255, 255, 255, 255, 255, 255, 255,
                           128, 0, 0, 0, 0, 0, 0, 0,
                           127, 255, 255, 255, 255, 255, 255, 255]))

        # test several big-endian signed edge cases
        self.assertEqual(
            build("32s 32s 32s 32s 64S 64S 64S 64S",
                  False,
                  [0,
                   -1,
                   -2147483648,
                   2147483647,
                   0,
                   -1,
                   -9223372036854775808,
                   9223372036854775807]),
            ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                           128, 0, 0, 0, 127, 255, 255, 255,
                           0, 0, 0, 0, 0, 0, 0, 0,
                           255, 255, 255, 255, 255, 255, 255, 255,
                           128, 0, 0, 0, 0, 0, 0, 0,
                           127, 255, 255, 255, 255, 255, 255, 255]))

        # test big-endian write errors
        for l in [[2, 6, 7, -3], [2, 6, 7], [2, 6], [2], []]:
            self.assertRaises(IndexError,
                              build,
                              "2u3u5u3s19s",
                              False,
                              l)

        # test basic little-endian string
        self.assertEqual(build("2u3u5u3s19s",
                               True,
                               [1, 4, 13, 3, -128545]),
                         ints_to_bytes([0xB1, 0xED, 0x3B, 0xC1]))

        # test several little-endian unsigned edge cases
        self.assertEqual(
            build("32u 32u 32u 32u 64U 64U 64U 64U",
                  True,
                  [0,
                   4294967295,
                   2147483648,
                   2147483647,
                   0,
                   0xFFFFFFFFFFFFFFFF,
                   9223372036854775808,
                   9223372036854775807]),
            ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                           0, 0, 0, 128, 255, 255, 255, 127,
                           0, 0, 0, 0, 0, 0, 0, 0,
                           255, 255, 255, 255, 255, 255, 255, 255,
                           0, 0, 0, 0, 0, 0, 0, 128,
                           255, 255, 255, 255, 255, 255, 255, 127]))

        # test several little-endian signed edge cases
        self.assertEqual(
            build("32s 32s 32s 32s 64S 64S 64S 64S",
                  True,
                  [0,
                   -1,
                   -2147483648,
                   2147483647,
                   0,
                   -1,
                   -9223372036854775808,
                   9223372036854775807]),
            ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                           0, 0, 0, 128, 255, 255, 255, 127,
                           0, 0, 0, 0, 0, 0, 0, 0,
                           255, 255, 255, 255, 255, 255, 255, 255,
                           0, 0, 0, 0, 0, 0, 0, 128,
                           255, 255, 255, 255, 255, 255, 255, 127]))

        # test little-endian write errors
        for l in [[1, 4, 13, 3], [1, 4, 13], [1, 4], [1], []]:
            self.assertRaises(IndexError,
                              build,
                              "2u3u5u3s19s",
                              True,
                              l)

    @LIB_BITSTREAM
    def test_build_parse_roundtrip(self):
        from audiotools.bitstream import build, parse

        for (format_string, values) in [("1u a",   [1]),
                                        ("2u a",   [1]),
                                        ("3u a",   [1]),
                                        ("4u a",   [1]),
                                        ("5u a",   [1]),
                                        ("6u a",   [1]),
                                        ("7u a",   [1]),
                                        ("8u",     [1]),
                                        ("2s a",   [-1]),
                                        ("3s a",   [-1]),
                                        ("4s a",   [-1]),
                                        ("5s a",   [-1]),
                                        ("6s a",   [-1]),
                                        ("7s a",   [-1]),
                                        ("8s a",   [-1]),
                                        ("64U",    [0xFFFFFFFFFFFFFFFF]),
                                        ("64S",    [-9223372036854775808]),
                                        ("10b",    [b"\x00" * 10]),
                                        ("10p10b a", [b"\x01" * 10]),
                                        ("10P10b", [b"\x02" * 10])]:
            self.assertEqual(parse(format_string, False,
                                   build(format_string, False, values)),
                             values)
            self.assertEqual(parse(format_string, True,
                                   build(format_string, True, values)),
                             values)

    @LIB_BITSTREAM
    def test_simple_reader(self):
        from audiotools.bitstream import BitstreamReader, HuffmanTree

        data = b"\xB1\xED\x3B\xC1"

        temp = tempfile.TemporaryFile()

        temp.write(data)
        temp.flush()
        temp.seek(0, 0)

        temp_s = BytesIO()
        temp_s.write(data)
        temp_s.seek(0, 0)

        # test a big-endian stream
        for reader in [BitstreamReader(temp, False),
                       BitstreamReader(temp_s, False),
                       BitstreamReader(data, False)]:
            table_be = HuffmanTree([[1, 1], 0,
                                    [1, 0], 1,
                                    [0, 1], 2,
                                    [0, 0, 1], 3,
                                    [0, 0, 0], 4], 0)
            self.__test_big_endian_reader__(reader, table_be)
            self.__test_try__(reader, table_be)
            self.__test_callbacks_reader__(reader, 14, 18, table_be, 14)

        temp.seek(0, 0)
        temp_s.seek(0, 0)

        # test a little-endian stream
        for reader in [BitstreamReader(temp, True),
                       BitstreamReader(temp_s, True),
                       BitstreamReader(data, True)]:
            table_le = HuffmanTree([[1, 1], 0,
                                    [1, 0], 1,
                                    [0, 1], 2,
                                    [0, 0, 1], 3,
                                    [0, 0, 0], 4], 1)
            self.__test_little_endian_reader__(reader, table_le)
            self.__test_try__(reader, table_le)
            self.__test_callbacks_reader__(reader, 14, 18, table_le, 13)

        # pad the stream with some additional data at both ends
        data = b"\xFF" + b"\xFF" + data + b"\xFF" + b"\xFF"

        temp.seek(0, 0)
        temp.write(data)
        temp.flush()
        temp.seek(0, 0)

        temp_s = BytesIO()
        temp_s.write(data)
        temp_s.seek(0, 0)

        # check a big-endian substream
        for reader in [BitstreamReader(temp, False),
                       BitstreamReader(temp_s, False),
                       BitstreamReader(data, False)]:
            reader.mark()

            reader.skip(16)
            subreader = reader.substream(4)
            self.__test_big_endian_reader__(subreader, table_be)
            self.__test_try__(subreader, table_be)
            self.__test_callbacks_reader__(subreader, 14, 18, table_be, 13)

            # check a big-endian substream built from another substream
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
        temp_s.seek(0, 0)

        # check a little-endian substream built from a file
        for reader in [BitstreamReader(temp, True),
                       BitstreamReader(temp_s, True),
                       BitstreamReader(data, True)]:
            reader.mark()

            reader.skip(16)
            subreader = reader.substream(4)
            self.__test_little_endian_reader__(subreader, table_le)
            self.__test_try__(subreader, table_le)
            self.__test_callbacks_reader__(subreader, 14, 18, table_le, 13)

            # check a little-endian substream built from another substream
            reader.rewind()
            reader.skip(8)
            subreader1 = reader.substream(6)
            subreader1.skip(8)
            subreader2 = subreader.substream(4)
            self.__test_little_endian_reader__(subreader2, table_le)
            self.__test_try__(subreader2, table_le)
            self.__test_callbacks_reader__(subreader2, 14, 18, table_le, 13)
            reader.unmark()

        temp.close()

        # test the writer functions with each endianness
        self.__test_writer__(0)
        self.__test_writer__(1)

    def __test_edge_reader_be__(self, reader):
        reader.mark()

        # try the unsigned 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read(32), 0)
        self.assertEqual(reader.read(32), 4294967295)
        self.assertEqual(reader.read(32), 2147483648)
        self.assertEqual(reader.read(32), 2147483647)
        self.assertEqual(reader.read(64), 0)
        self.assertEqual(reader.read(64), 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(reader.read(64), 9223372036854775808)
        self.assertEqual(reader.read(64), 9223372036854775807)

        # try the signed 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read_signed(32), 0)
        self.assertEqual(reader.read_signed(32), -1)
        self.assertEqual(reader.read_signed(32), -2147483648)
        self.assertEqual(reader.read_signed(32), 2147483647)
        self.assertEqual(reader.read_signed(64), 0)
        self.assertEqual(reader.read_signed(64), -1)
        self.assertEqual(reader.read_signed(64), -9223372036854775808)
        self.assertEqual(reader.read_signed(64), 9223372036854775807)

        # try the unsigned values via parse()
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
        self.assertEqual(u_val64_2, 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(u_val64_3, 9223372036854775808)
        self.assertEqual(u_val64_4, 9223372036854775807)

        # try the signed values via parse()
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
        self.assertEqual(s_val64_3, -9223372036854775808)
        self.assertEqual(s_val64_4, 9223372036854775807)

        reader.unmark()

    def __test_edge_reader_le__(self, reader):
        reader.mark()

        # try the unsigned 32 and 64 bit values
        self.assertEqual(reader.read(32), 0)
        self.assertEqual(reader.read(32), 4294967295)
        self.assertEqual(reader.read(32), 2147483648)
        self.assertEqual(reader.read(32), 2147483647)
        self.assertEqual(reader.read(64), 0)
        self.assertEqual(reader.read(64), 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(reader.read(64), 9223372036854775808)
        self.assertEqual(reader.read(64), 9223372036854775807)

        # try the signed 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read_signed(32), 0)
        self.assertEqual(reader.read_signed(32), -1)
        self.assertEqual(reader.read_signed(32), -2147483648)
        self.assertEqual(reader.read_signed(32), 2147483647)
        self.assertEqual(reader.read_signed(64), 0)
        self.assertEqual(reader.read_signed(64), -1)
        self.assertEqual(reader.read_signed(64), -9223372036854775808)
        self.assertEqual(reader.read_signed(64), 9223372036854775807)

        # try the unsigned values via parse()
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
        self.assertEqual(u_val64_2, 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(u_val64_3, 9223372036854775808)
        self.assertEqual(u_val64_4, 9223372036854775807)

        # try the signed values via parse()
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
        self.assertEqual(s_val64_3, -9223372036854775808)
        self.assertEqual(s_val64_4, 9223372036854775807)

        reader.unmark()

    def __test_edge_writer__(self, get_writer, validate_writer):
        # try the unsigned 32 and 64 bit values
        (writer, temp) = get_writer()
        writer.write(32, 0)
        writer.write(32, 4294967295)
        writer.write(32, 2147483648)
        writer.write(32, 2147483647)
        writer.write(64, 0)
        writer.write(64, 0xFFFFFFFFFFFFFFFF)
        writer.write(64, 9223372036854775808)
        writer.write(64, 9223372036854775807)
        validate_writer(writer, temp)

        # try the signed 32 and 64 bit values
        (writer, temp) = get_writer()
        writer.write_signed(32, 0)
        writer.write_signed(32, -1)
        writer.write_signed(32, -2147483648)
        writer.write_signed(32, 2147483647)
        writer.write_signed(64, 0)
        writer.write_signed(64, -1)
        writer.write_signed(64, -9223372036854775808)
        writer.write_signed(64, 9223372036854775807)
        validate_writer(writer, temp)

        # try the unsigned values via build()
        (writer, temp) = get_writer()
        u_val_1 = 0
        u_val_2 = 4294967295
        u_val_3 = 2147483648
        u_val_4 = 2147483647
        u_val64_1 = 0
        u_val64_2 = 0xFFFFFFFFFFFFFFFF
        u_val64_3 = 9223372036854775808
        u_val64_4 = 9223372036854775807
        writer.build("32u 32u 32u 32u 64u 64u 64u 64u",
                     [u_val_1, u_val_2, u_val_3, u_val_4,
                      u_val64_1, u_val64_2, u_val64_3, u_val64_4])
        validate_writer(writer, temp)

        # try the signed values via build()
        (writer, temp) = get_writer()
        s_val_1 = 0
        s_val_2 = -1
        s_val_3 = -2147483648
        s_val_4 = 2147483647
        s_val64_1 = 0
        s_val64_2 = -1
        s_val64_3 = -9223372036854775808
        s_val64_4 = 9223372036854775807
        writer.build("32s 32s 32s 32s 64s 64s 64s 64s",
                     [s_val_1, s_val_2, s_val_3, s_val_4,
                      s_val64_1, s_val64_2, s_val64_3, s_val64_4])
        validate_writer(writer, temp)

    def __get_edge_writer_be__(self):
        from audiotools.bitstream import BitstreamWriter

        temp_file = tempfile.NamedTemporaryFile()
        return (BitstreamWriter(open(temp_file.name, "wb"), False), temp_file)

    def __validate_edge_writer_be__(self, writer, temp_file):
        writer.close()

        with open(temp_file.name, "rb") as f:
            self.assertEqual(
                f.read(),
                ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                               128, 0, 0, 0, 127, 255, 255, 255,
                               0, 0, 0, 0, 0, 0, 0, 0,
                               255, 255, 255, 255, 255, 255, 255, 255,
                               128, 0, 0, 0, 0, 0, 0, 0,
                               127, 255, 255, 255, 255, 255, 255, 255]))

        temp_file.close()

    def __get_edge_recorder_be__(self):
        from audiotools.bitstream import BitstreamRecorder

        return (BitstreamRecorder(0), tempfile.NamedTemporaryFile())

    def __validate_edge_recorder_be__(self, writer, temp_file):
        from audiotools.bitstream import BitstreamWriter

        writer2 = BitstreamWriter(open(temp_file.name, "wb"), False)
        writer.copy(writer2)
        writer2.close()

        with open(temp_file.name, "rb") as f:
            self.assertEqual(
                f.read(),
                ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                               128, 0, 0, 0, 127, 255, 255, 255,
                               0, 0, 0, 0, 0, 0, 0, 0,
                               255, 255, 255, 255, 255, 255, 255, 255,
                               128, 0, 0, 0, 0, 0, 0, 0,
                               127, 255, 255, 255, 255, 255, 255, 255]))

        temp_file.close()

    def __get_edge_accumulator_be__(self):
        from audiotools.bitstream import BitstreamAccumulator

        return (BitstreamAccumulator(0), None)

    def __validate_edge_accumulator_be__(self, writer, temp_file):
        self.assertEqual(writer.bits(), 48 * 8)

    def __get_edge_writer_le__(self):
        from audiotools.bitstream import BitstreamWriter

        temp_file = tempfile.NamedTemporaryFile()
        return (BitstreamWriter(open(temp_file.name, "wb"), True), temp_file)

    def __validate_edge_writer_le__(self, writer, temp_file):
        writer.close()

        with open(temp_file.name, "rb") as f:
            self.assertEqual(
                f.read(),
                ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                               0, 0, 0, 128, 255, 255, 255, 127,
                               0, 0, 0, 0, 0, 0, 0, 0,
                               255, 255, 255, 255, 255, 255, 255, 255,
                               0, 0, 0, 0, 0, 0, 0, 128,
                               255, 255, 255, 255, 255, 255, 255, 127]))

        temp_file.close()

    def __get_edge_recorder_le__(self):
        from audiotools.bitstream import BitstreamRecorder

        return (BitstreamRecorder(1), tempfile.NamedTemporaryFile())

    def __validate_edge_recorder_le__(self, writer, temp_file):
        from audiotools.bitstream import BitstreamWriter

        writer2 = BitstreamWriter(open(temp_file.name, "wb"), True)
        writer.copy(writer2)
        writer2.close()

        with open(temp_file.name, "rb") as f:
            self.assertEqual(
                f.read(),
                ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                               0, 0, 0, 128, 255, 255, 255, 127,
                               0, 0, 0, 0, 0, 0, 0, 0,
                               255, 255, 255, 255, 255, 255, 255, 255,
                               0, 0, 0, 0, 0, 0, 0, 128,
                               255, 255, 255, 255, 255, 255, 255, 127]))

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
                  self.__writer_perform_write_unary_0__,
                  self.__writer_perform_write_unary_1__,
                  self.__writer_perform_write_huffman__]

        # perform file-based checks
        for check in checks:
            temp = tempfile.NamedTemporaryFile()
            try:
                writer = BitstreamWriter(open(temp.name, "wb"), endianness)
                check(writer, endianness)
                writer.close()
                self.__check_output_file__(temp)
            finally:
                temp.close()

            data = BytesIO()
            writer = BitstreamWriter(data, endianness)
            check(writer, endianness)
            del(writer)
            self.assertEqual(data.getvalue(), b"\xB1\xED\x3B\xC1")

        # perform recorder-based checks
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

        # perform accumulator-based checks
        for check in checks:
            writer = BitstreamAccumulator(endianness)
            check(writer, endianness)
            self.assertEqual(writer.bits(), 32)

        # check swap records
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

        # check recorder reset
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

        # check endianness setting
        # FIXME

        # check a file-based byte-align
        # FIXME

        # check a recorder-based byte-align
        # FIXME

        # check an accumulator-based byte-align
        # FIXME

        # check a partial dump
        # FIXME

        # check that recorder->recorder->file works
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

        # check that recorder->accumulator works
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

        self.assertRaises(ValueError, writer.write, -1, 0)

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

        self.assertRaises(ValueError, writer.write_signed, -1, 0)

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

    def __writer_perform_write_huffman__(self, writer, endianness):
        from audiotools.bitstream import HuffmanTree

        table = HuffmanTree([[1, 1], 0,
                             [1, 0], 1,
                             [0, 1], 2,
                             [0, 0, 1], 3,
                             [0, 0, 0], 4], endianness)

        if (endianness == 0):
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 4)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 2)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 2)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 2)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 4)
            writer.write_huffman_code(table, 2)
        else:
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 3)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 2)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 0)
            writer.write_huffman_code(table, 1)
            writer.write_huffman_code(table, 2)
            writer.write_huffman_code(table, 4)
            writer.write_huffman_code(table, 3)
            writer.write(1, 1)

    def __check_output_file__(self, temp_file):
        with open(temp_file.name, "rb") as f:
            self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

    @LIB_BITSTREAM
    def test_read_errors(self):
        from audiotools.bitstream import BitstreamReader

        for little_endian in [False, True]:
            for reader in [BitstreamReader(BytesIO(b"a" * 10),
                                           little_endian),
                           BitstreamReader(BytesIO(b"a" * 10),
                                           little_endian).substream(5)]:
                # reading negative number of bits shouldn't work
                self.assertRaises(ValueError,
                                  reader.read,
                                  -1)

                self.assertRaises(ValueError,
                                  reader.read_signed,
                                  -1)

                # reading signed value in 0 bits shouldn't work
                self.assertRaises(ValueError,
                                  reader.read_signed,
                                  0)

                self.assertRaises(ValueError,
                                  reader.parse,
                                  "0s")

                # reading unary with non 0/1 bit shouldn't work
                self.assertRaises(ValueError,
                                  reader.unary,
                                  3)

                self.assertRaises(ValueError,
                                  reader.unary,
                                  -1)

    @LIB_BITSTREAM
    def test_write_errors(self):
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        for little_endian in [False, True]:
            for writer in [BitstreamWriter(BytesIO(),
                                           little_endian),
                           BitstreamRecorder(little_endian),
                           BitstreamAccumulator(little_endian)]:
                # writing negative number of bits shouldn't work
                self.assertRaises(ValueError,
                                  writer.write,
                                  -1, 0)

                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  -1, 0)

                # writing signed value in 0 bits shouldn't work
                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  0, 0)

                self.assertRaises(ValueError,
                                  writer.build,
                                  "0s", [0])

                # writing negative value as unsigned shouldn't work
                self.assertRaises(ValueError,
                                  writer.write,
                                  8, -1)

                # write unsigned value that's too large shouldn't work
                self.assertRaises(ValueError,
                                  writer.write,
                                  8, 2 ** 8)

                # nor should it work from the .build method
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8u", [-1])
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8u", [2 ** 8])

                # writing negative value that's too small shouldn't work
                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  8, -(2 ** 8))

                # writing signed value that's too large shouldn't work
                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  8, 2 ** 8)

                # nor should it work from the .build method
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8s", [-(2 ** 8)])
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8s", [2 ** 8])

                # writing some value that's not a number shouldn't work
                self.assertRaises(TypeError,
                                  writer.write,
                                  8, "foo")

                self.assertRaises(TypeError,
                                  writer.write_signed,
                                  8, "foo")

                self.assertRaises(TypeError,
                                  writer.build,
                                  "8u", ["foo"])

                self.assertRaises(TypeError,
                                  writer.build,
                                  "8s", ["foo"])

                # writing unary with non 0/1 bit shouldn't work
                self.assertRaises(ValueError,
                                  writer.unary,
                                  3, 1)

                self.assertRaises(ValueError,
                                  writer.unary,
                                  -1, 1)

    @LIB_BITSTREAM
    def test_edge_cases(self):
        from audiotools.bitstream import BitstreamReader

        temp = tempfile.NamedTemporaryFile()
        try:
            # write the temp file with a set of known big-endian data
            temp.write(ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                                      128, 0, 0, 0, 127, 255, 255, 255,
                                      0, 0, 0, 0, 0, 0, 0, 0,
                                      255, 255, 255, 255, 255, 255, 255, 255,
                                      128, 0, 0, 0, 0, 0, 0, 0,
                                      127, 255, 255, 255, 255, 255, 255, 255]))
            temp.flush()

            # ensure a big-endian reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), False)
            self.__test_edge_reader_be__(reader)
            reader.close()

            # ensure a big-endian sub-reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), False)
            subreader = reader.substream(48)
            self.__test_edge_reader_be__(subreader)
            subreader.close()
            reader.close()
        finally:
            temp.close()

        temp = tempfile.NamedTemporaryFile()
        try:
            # write the temp file with a collection of known little-endian data
            temp.write(ints_to_bytes([0, 0, 0, 0, 255, 255, 255, 255,
                                      0, 0, 0, 128, 255, 255, 255, 127,
                                      0, 0, 0, 0, 0, 0, 0, 0,
                                      255, 255, 255, 255, 255, 255, 255, 255,
                                      0, 0, 0, 0, 0, 0, 0, 128,
                                      255, 255, 255, 255, 255, 255, 255, 127]))
            temp.flush()

            # ensure a little-endian reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), True)
            self.__test_edge_reader_le__(reader)
            reader.close()

            # ensure a little-endian sub-reader reads the values correctly
            reader = BitstreamReader(open(temp.name, "rb"), True)
            subreader = reader.substream(48)
            self.__test_edge_reader_be__(subreader)
            subreader.close()
            reader.close()
        finally:
            temp.close()

        # test a bunch of big-endian values via the bitstream writer
        self.__test_edge_writer__(self.__get_edge_writer_be__,
                                  self.__validate_edge_writer_be__)

        # test a bunch of big-endian values via the bitstream recorder
        self.__test_edge_writer__(self.__get_edge_recorder_be__,
                                  self.__validate_edge_recorder_be__)

        # test a bunch of big-endian values via the bitstream accumulator
        self.__test_edge_writer__(self.__get_edge_accumulator_be__,
                                  self.__validate_edge_accumulator_be__)

        # test a bunch of little-endian values via the bitstream writer
        self.__test_edge_writer__(self.__get_edge_writer_le__,
                                  self.__validate_edge_writer_le__)

        # test a bunch of little-endian values via the bitstream recorder
        self.__test_edge_writer__(self.__get_edge_recorder_le__,
                                  self.__validate_edge_recorder_le__)

        # test a bunch of little-endian values via the bitstream accumulator
        self.__test_edge_writer__(self.__get_edge_accumulator_le__,
                                  self.__validate_edge_accumulator_le__)

    @LIB_BITSTREAM
    def test_huge_values(self):
        from audiotools.bitstream import BitstreamReader
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        for b in [2, 4, 8, 16, 32, 64, 128, 256, 512]:
            data = os.urandom(b)
            bits = b * 8
            for little_endian in [False, True]:
                unsigned1 = BitstreamReader(
                    BytesIO(data),
                    little_endian).read(bits)

                unsigned2 = BitstreamReader(
                    BytesIO(data),
                    little_endian).parse("%du" % (bits))[0]

                signed1 = BitstreamReader(
                    BytesIO(data),
                    little_endian).read_signed(bits)

                signed2 = BitstreamReader(
                    BytesIO(data),
                    little_endian).parse("%ds" % (bits))[0]

                # check that reading from .read and .parse
                # yield the same values
                self.assertEqual(unsigned1, unsigned2)
                self.assertEqual(signed1, signed2)

                # check that writing round-trips properly
                unsigned_data1 = BytesIO()
                unsigned_data2 = BytesIO()
                signed_data1 = BytesIO()
                signed_data2 = BytesIO()

                BitstreamWriter(unsigned_data1,
                                little_endian).write(bits, unsigned1)
                BitstreamWriter(unsigned_data2,
                                little_endian).build("%du" % (bits),
                                                     [unsigned1])
                BitstreamWriter(signed_data1,
                                little_endian).write_signed(bits, signed1)
                BitstreamWriter(signed_data2,
                                little_endian).build("%ds" % (bits),
                                                     [signed1])

                self.assertEqual(data, unsigned_data1.getvalue())
                self.assertEqual(data, unsigned_data2.getvalue())
                self.assertEqual(data, signed_data1.getvalue())
                self.assertEqual(data, signed_data2.getvalue())

                unsigned_data1 = BitstreamRecorder(little_endian)
                unsigned_data2 = BitstreamRecorder(little_endian)
                signed_data1 = BitstreamRecorder(little_endian)
                signed_data2 = BitstreamRecorder(little_endian)

                unsigned_data1.write(bits, unsigned1)
                unsigned_data2.build("%du" % (bits), [unsigned1])
                signed_data1.write_signed(bits, signed1)
                signed_data2.build("%ds" % (bits), [signed1])

                self.assertEqual(data, unsigned_data1.data())
                self.assertEqual(data, unsigned_data2.data())
                self.assertEqual(data, signed_data1.data())
                self.assertEqual(data, signed_data2.data())

                unsigned_data1 = BitstreamAccumulator(little_endian)
                unsigned_data2 = BitstreamAccumulator(little_endian)
                signed_data1 = BitstreamAccumulator(little_endian)
                signed_data2 = BitstreamAccumulator(little_endian)

                unsigned_data1.write(bits, unsigned1)
                unsigned_data2.build("%du" % (bits), [unsigned1])
                signed_data1.write_signed(bits, signed1)
                signed_data2.build("%ds" % (bits), [signed1])

                self.assertEqual(unsigned_data1.bits(), bits)
                self.assertEqual(unsigned_data2.bits(), bits)
                self.assertEqual(signed_data1.bits(), bits)
                self.assertEqual(signed_data2.bits(), bits)

                # check that endianness swapping works
                r = BitstreamReader(
                    BytesIO(data),
                    little_endian)

                unsigned1 = r.read(bits // 2)
                r.set_endianness(not little_endian)
                unsigned2 = r.read(bits // 2)

                new_data = BytesIO()
                w = BitstreamWriter(
                    new_data, little_endian)
                w.write(bits // 2, unsigned1)
                w.set_endianness(not little_endian)
                w.write(bits // 2, unsigned2)
                w.flush()

                self.assertEqual(data, new_data.getvalue())

                w = BitstreamRecorder(little_endian)
                w.write(bits // 2, unsigned1)
                w.set_endianness(not little_endian)
                w.write(bits // 2, unsigned2)

                self.assertEqual(data, w.data())

                w = BitstreamAccumulator(little_endian)
                w.write(bits // 2, unsigned1)
                w.set_endianness(not little_endian)
                w.write(bits // 2, unsigned2)

                self.assertEqual(bits, w.bits())

    @LIB_BITSTREAM
    def test_python_reader(self):
        from audiotools.bitstream import BitstreamReader

        # Vanilla, file-based BitstreamReader uses a 1 character buffer
        # and relies on stdio to perform buffering which is fast enough.
        # Therefore, a byte-aligned file can be seek()ed at will.
        # However, making lots of read(1) calls on a Python object
        # is unacceptably slow.
        # Therefore, we read a 4KB string and pull individual bytes from
        # it as needed, which should keep performance reasonable.
        def new_temp1():
            temp = BytesIO()
            temp.write(b"\xB1")
            temp.write(b"\xED")
            temp.write(b"\x3B")
            temp.write(b"\xC1")
            temp.seek(0, 0)
            return temp

        def new_temp2():
            return __SimpleChunkReader__([b"\xB1" +
                                          b"\xED" +
                                          b"\x3B" +
                                          b"\xC1"])

        def new_temp3():
            return __SimpleChunkReader__([b"\xB1" +
                                          b"\xED",
                                          b"\x3B" +
                                          b"\xC1"])

        def new_temp4():
            return __SimpleChunkReader__([b"\xB1",
                                          b"\xED",
                                          b"\x3B" +
                                          b"\xC1"])

        def new_temp5():
            return __SimpleChunkReader__([b"\xB1",
                                          b"\xED",
                                          b"\x3B",
                                          b"\xC1"])

        for new_temp in [new_temp1, new_temp2, new_temp3, new_temp4,
                         new_temp5]:
            # first, check the bitstream reader
            # against some simple known big-endian values
            bitstream = BitstreamReader(new_temp(), False)

            self.assertEqual(bitstream.read(2), 2)
            self.assertEqual(bitstream.read(3), 6)
            self.assertEqual(bitstream.read(5), 7)
            self.assertEqual(bitstream.read(3), 5)
            self.assertEqual(bitstream.read(19), 342977)

            bitstream = BitstreamReader(new_temp(), False)
            self.assertEqual(bitstream.read_signed(2), -2)
            self.assertEqual(bitstream.read_signed(3), -2)
            self.assertEqual(bitstream.read_signed(5), 7)
            self.assertEqual(bitstream.read_signed(3), -3)
            self.assertEqual(bitstream.read_signed(19), -181311)

            bitstream = BitstreamReader(new_temp(), False)
            self.assertEqual(bitstream.unary(0), 1)
            self.assertEqual(bitstream.unary(0), 2)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 4)
            bitstream.byte_align()
            bitstream = BitstreamReader(new_temp(), False)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 1)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 3)
            self.assertEqual(bitstream.unary(1), 0)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), False)
            self.assertEqual(bitstream.read(1), 1)
            bit = bitstream.read(1)
            self.assertEqual(bit, 0)
            bitstream.unread(bit)
            self.assertEqual(bitstream.read(2), 1)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), False)
            self.assertEqual(bitstream.read(8), 0xB1)
            bitstream.unread(0)
            self.assertEqual(bitstream.read(1), 0)
            bitstream.unread(1)
            self.assertEqual(bitstream.read(1), 1)

            bitstream = BitstreamReader(new_temp(), False)
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
            bitstream = BitstreamReader(new_temp(), False)

            # then, check the bitstream reader
            # against some simple known little-endian values
            bitstream = BitstreamReader(new_temp(), True)

            self.assertEqual(bitstream.read(2), 1)
            self.assertEqual(bitstream.read(3), 4)
            self.assertEqual(bitstream.read(5), 13)
            self.assertEqual(bitstream.read(3), 3)
            self.assertEqual(bitstream.read(19), 395743)

            bitstream = BitstreamReader(new_temp(), True)
            self.assertEqual(bitstream.read_signed(2), 1)
            self.assertEqual(bitstream.read_signed(3), -4)
            self.assertEqual(bitstream.read_signed(5), 13)
            self.assertEqual(bitstream.read_signed(3), 3)
            self.assertEqual(bitstream.read_signed(19), -128545)

            bitstream = BitstreamReader(new_temp(), True)
            self.assertEqual(bitstream.unary(0), 1)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 0)
            self.assertEqual(bitstream.unary(0), 2)
            self.assertEqual(bitstream.unary(0), 2)
            bitstream.byte_align()
            bitstream = BitstreamReader(new_temp(), True)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 3)
            self.assertEqual(bitstream.unary(1), 0)
            self.assertEqual(bitstream.unary(1), 1)
            self.assertEqual(bitstream.unary(1), 0)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), True)
            self.assertEqual(bitstream.read(1), 1)
            bit = bitstream.read(1)
            self.assertEqual(bit, 0)
            bitstream.unread(bit)
            self.assertEqual(bitstream.read(4), 8)
            bitstream.byte_align()

            bitstream = BitstreamReader(new_temp(), True)
            self.assertEqual(bitstream.read(8), 0xB1)
            bitstream.unread(0)
            self.assertEqual(bitstream.read(1), 0)
            bitstream.unread(1)
            self.assertEqual(bitstream.read(1), 1)

            bitstream = BitstreamReader(new_temp(), True)
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

    @LIB_BITSTREAM
    def test_simple_writer(self):
        from audiotools.bitstream import BitstreamWriter

        with tempfile.NamedTemporaryFile() as temp:
            # first, have the bitstream writer generate
            # a set of known big-endian values

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, False)
            bitstream.write(2, 2)
            bitstream.write(3, 6)
            bitstream.write(5, 7)
            bitstream.write(3, 5)
            bitstream.write(19, 342977)
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, False)
            bitstream.write_signed(2, -2)
            bitstream.write_signed(3, -2)
            bitstream.write_signed(5, 7)
            bitstream.write_signed(3, -3)
            bitstream.write_signed(19, -181311)
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, False)
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
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, False)
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
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            # then, have the bitstream writer generate
            # a set of known little-endian values
            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, True)
            bitstream.write(2, 1)
            bitstream.write(3, 4)
            bitstream.write(5, 13)
            bitstream.write(3, 3)
            bitstream.write(19, 395743)
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, True)
            bitstream.write_signed(2, 1)
            bitstream.write_signed(3, -4)
            bitstream.write_signed(5, 13)
            bitstream.write_signed(3, 3)
            bitstream.write_signed(19, -128545)
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, True)
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
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, True)
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
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")

            f = open(temp.name, "wb")
            bitstream = BitstreamWriter(f, True)
            bitstream.write(4, 0x1)
            bitstream.byte_align()
            bitstream.write(4, 0xD)
            bitstream.byte_align()
            bitstream.flush()
            bitstream.close()
            with open(temp.name, "rb") as f:
                self.assertEqual(f.read(), b"\x01\x0D")

    # and have the bitstream reader check those values are accurate

    @LIB_BITSTREAM
    def test_reader_close(self):
        from audiotools.bitstream import BitstreamReader, HuffmanTree

        def test_reader(reader):
            self.assertRaises(IOError, reader.read, 1)
            self.assertRaises(IOError, reader.skip, 3)
            self.assertRaises(IOError, reader.skip_bytes, 1)
            self.assertRaises(IOError, reader.read_signed, 2)
            self.assertRaises(IOError, reader.unary, 1)
            self.assertRaises(IOError, reader.read_bytes, 1)
            self.assertRaises(IOError, reader.parse, "1b2b3b")
            self.assertRaises(IOError, reader.substream, 2)
            self.assertRaises(IOError, reader.read_huffman_code,
                              HuffmanTree([(1, ),     1,
                                           (0, 1),    2,
                                           (0, 0, 1), 3,
                                           (0, 0, 0), 4], False))

        def new_temp():
            temp = BytesIO()
            temp.write(b"\xB1")
            temp.write(b"\xED")
            temp.write(b"\x3B")
            temp.write(b"\xC1")
            temp.seek(0, 0)
            return temp

        # test a BitstreamReader from a Python file object
        f = open("test_core.py", "rb")

        reader = BitstreamReader(f, False)
        reader.close()
        test_reader(reader)
        reader.set_endianness(1)
        test_reader(reader)

        reader = BitstreamReader(f, True)
        reader.close()
        test_reader(reader)
        reader.set_endianness(0)
        test_reader(reader)

        f.close()
        del(f)

        # test a BitstreamReader from a Python BytesIO object
        reader = BitstreamReader(new_temp(), False)
        reader.close()
        test_reader(reader)
        reader.set_endianness(1)
        test_reader(reader)

        reader = BitstreamReader(new_temp(), True)
        reader.close()
        test_reader(reader)
        reader.set_endianness(0)
        test_reader(reader)

    @LIB_BITSTREAM
    def test_reader_context(self):
        from io import BytesIO
        from audiotools.bitstream import BitstreamReader

        b = BytesIO(b"\xB1\xED\x3B\xC1")
        self.assertFalse(b.closed)
        r = BitstreamReader(b, False)
        self.assertEqual(r.read(2), 0x2)
        self.assertEqual(r.read(3), 0x6)
        self.assertEqual(r.read(5), 0x07)
        self.assertEqual(r.read(3), 0x5)
        self.assertEqual(r.read(19), 0x53BC1)
        self.assertRaises(IOError, r.read, 8)
        self.assertFalse(b.closed)
        del(r)
        self.assertFalse(b.closed)

        b = BytesIO(b"\xB1\xED\x3B\xC1")
        self.assertFalse(b.closed)
        r = BitstreamReader(b, True)
        self.assertEqual(r.read(2), 0x1)
        self.assertEqual(r.read(3), 0x4)
        self.assertEqual(r.read(5), 0x0D)
        self.assertEqual(r.read(3), 0x3)
        self.assertEqual(r.read(19), 0x609DF)
        self.assertRaises(IOError, r.read, 8)
        self.assertFalse(b.closed)
        del(r)
        self.assertFalse(b.closed)

        b = BytesIO(b"\xB1\xED\x3B\xC1")
        self.assertFalse(b.closed)
        with BitstreamReader(b, False) as r:
            self.assertEqual(r.read(2), 0x2)
            self.assertEqual(r.read(3), 0x6)
            self.assertEqual(r.read(5), 0x07)
            self.assertEqual(r.read(3), 0x5)
            self.assertEqual(r.read(19), 0x53BC1)
            self.assertRaises(IOError, r.read, 8)
            self.assertFalse(b.closed)
        self.assertTrue(b.closed)

        b = BytesIO(b"\xB1\xED\x3B\xC1")
        self.assertFalse(b.closed)
        with BitstreamReader(b, True) as r:
            self.assertEqual(r.read(2), 0x1)
            self.assertEqual(r.read(3), 0x4)
            self.assertEqual(r.read(5), 0x0D)
            self.assertEqual(r.read(3), 0x3)
            self.assertEqual(r.read(19), 0x609DF)
            self.assertRaises(IOError, r.read, 8)
            self.assertFalse(b.closed)
        self.assertTrue(b.closed)

    @LIB_BITSTREAM
    def test_writer_close(self):
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        def test_writer(writer):
            self.assertRaises(IOError, writer.write, 1, 1)
            self.assertRaises(IOError, writer.write_signed, 2, 1)
            self.assertRaises(IOError, writer.unary, 1, 1)
            self.assertRaises(IOError, writer.write_bytes, b"foo")
            self.assertRaises(IOError, writer.build, "1u2u3u", [0, 1, 2])

        # test a BitstreamWriter to a Python file object
        f = open("test.bin", "wb")
        try:
            writer = BitstreamWriter(f, False)
            writer.close()
            test_writer(writer)
            writer.set_endianness(1)
            test_writer(writer)
            f.close()
            del(f)
        finally:
            os.unlink("test.bin")

        f = open("test.bin", "wb")
        try:
            writer = BitstreamWriter(f, True)
            writer.close()
            test_writer(writer)
            writer.set_endianness(0)
            test_writer(writer)
            f.close()
            del(f)
        finally:
            os.unlink("test.bin")

        # test a BitstreamWriter to a Python BytesIO object
        s = BytesIO()
        writer = BitstreamWriter(s, False)
        writer.close()
        test_writer(writer)
        writer.set_endianness(1)
        test_writer(writer)
        del(writer)
        del(s)

        s = BytesIO()
        writer = BitstreamWriter(s, True)
        writer.close()
        test_writer(writer)
        writer.set_endianness(0)
        test_writer(writer)
        del(writer)
        del(s)

        # test a BitstreamRecorder
        writer = BitstreamRecorder(0)
        writer.close()
        test_writer(writer)
        writer.set_endianness(1)
        test_writer(writer)
        del(writer)

        writer = BitstreamRecorder(1)
        writer.close()
        test_writer(writer)
        writer.set_endianness(0)
        test_writer(writer)
        del(writer)

        # test a BitstreamAccumulator
        writer = BitstreamAccumulator(0)
        writer.close()
        test_writer(writer)
        writer.set_endianness(1)
        test_writer(writer)
        del(writer)

        writer = BitstreamAccumulator(1)
        writer.close()
        test_writer(writer)
        writer.set_endianness(0)
        test_writer(writer)
        del(writer)

    @LIB_BITSTREAM
    def test_writer_context(self):
        from io import BytesIO
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        # if simply deallocated, writers should flush contents
        # but not close internal stream
        b = BytesIO()
        self.assertFalse(b.closed)
        w = BitstreamWriter(b, False)
        w.write(2, 0x2)
        w.write(3, 0x6)
        w.write(5, 0x07)
        w.write(3, 0x5)
        w.write(19, 0x53BC1)
        del(w)
        self.assertFalse(b.closed)
        self.assertEqual(b.getvalue(), b"\xB1\xED\x3B\xC1")

        b = BytesIO()
        self.assertFalse(b.closed)
        w = BitstreamWriter(b, True)
        w.write(2, 0x1)
        w.write(3, 0x4)
        w.write(5, 0x0D)
        w.write(3, 0x3)
        w.write(19, 0x609DF)
        del(w)
        self.assertFalse(b.closed)
        self.assertEqual(b.getvalue(), b"\xB1\xED\x3B\xC1")

        # if put into a context manager, writers should flush contents
        # but also close internal stream
        b = open("test.bin", "wb")
        try:
            self.assertFalse(b.closed)
            with BitstreamWriter(b, False) as w:
                w.write(2, 0x2)
                w.write(3, 0x6)
                w.write(5, 0x07)
                w.write(3, 0x5)
                w.write(19, 0x53BC1)
                self.assertFalse(b.closed)
            self.assertTrue(b.closed)
            with open("test.bin", "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")
        finally:
            os.unlink("test.bin")

        b = open("test.bin", "wb")
        try:
            self.assertFalse(b.closed)
            with BitstreamWriter(b, True) as w:
                w.write(2, 0x1)
                w.write(3, 0x4)
                w.write(5, 0x0D)
                w.write(3, 0x3)
                w.write(19, 0x609DF)
                self.assertFalse(b.closed)
            self.assertTrue(b.closed)
            with open("test.bin", "rb") as f:
                self.assertEqual(f.read(), b"\xB1\xED\x3B\xC1")
        finally:
            os.unlink("test.bin")

        # recorders should work in a context manager
        # even if it's not particularly useful
        with BitstreamRecorder(False) as w:
            w.write(2, 0x2)
            w.write(3, 0x6)
            w.write(5, 0x07)
            w.write(3, 0x5)
            w.write(19, 0x53BC1)
            self.assertEqual(w.data(), b"\xB1\xED\x3B\xC1")

        with BitstreamRecorder(True) as w:
            w.write(2, 0x1)
            w.write(3, 0x4)
            w.write(5, 0x0D)
            w.write(3, 0x3)
            w.write(19, 0x609DF)
            self.assertEqual(w.data(), b"\xB1\xED\x3B\xC1")

        # accumulators should work in a context manager
        # even if it's not particularly useful
        with BitstreamAccumulator(False) as w:
            w.write(2, 0x2)
            w.write(3, 0x6)
            w.write(5, 0x07)
            w.write(3, 0x5)
            w.write(19, 0x53BC1)
            self.assertEqual(w.bits(), 32)

        with BitstreamAccumulator(True) as w:
            w.write(2, 0x1)
            w.write(3, 0x4)
            w.write(5, 0x0D)
            w.write(3, 0x3)
            w.write(19, 0x609DF)
            self.assertEqual(w.bits(), 32)

    def __test_writer_marks__(self, writer):
        writer.write(1, 1)
        self.assertRaises(IOError, writer.mark)
        writer.write(2, 3)
        self.assertRaises(IOError, writer.mark)
        writer.write(3, 7)
        self.assertRaises(IOError, writer.mark)
        writer.write(2, 3)
        writer.mark()
        writer.write(4, 15)
        self.assertRaises(IOError, writer.rewind)
        writer.write(4, 15)
        writer.write(8, 0xFF)
        writer.rewind()
        writer.write(8, 0)
        writer.unmark()

    @LIB_BITSTREAM
    def test_writer_marks(self):
        from audiotools.bitstream import BitstreamWriter

        f = open("test.bin", "wb")
        try:
            writer = BitstreamWriter(f, False)
            self.__test_writer_marks__(writer)
            del(writer)
            f.close()
            with open("test.bin", "rb") as f:
                self.assertEqual(f.read(), b"\xFF\x00\xFF")
        finally:
            os.unlink("test.bin")

        f = open("test.bin", "wb")
        try:
            writer = BitstreamWriter(f, True)
            self.__test_writer_marks__(writer)
            del(writer)
            f.close()
            with open("test.bin", "rb") as f:
                self.assertEqual(f.read(), b"\xFF\x00\xFF")
        finally:
            os.unlink("test.bin")

        s = BytesIO()
        writer = BitstreamWriter(s, False)
        self.__test_writer_marks__(writer)
        del(writer)
        self.assertEqual(s.getvalue(), b"\xFF\x00\xFF")

        s = BytesIO()
        writer = BitstreamWriter(s, True)
        self.__test_writer_marks__(writer)
        del(writer)
        self.assertEqual(s.getvalue(), b"\xFF\x00\xFF")


class TestReplayGain(unittest.TestCase):
    @LIB_REPLAYGAIN
    def test_basics(self):
        import audiotools.replaygain
        import audiotools.pcm

        # check for invalid sample rate
        self.assertRaises(ValueError,
                          audiotools.replaygain.ReplayGain,
                          200000)

        # check for a very small sample count
        rg = audiotools.replaygain.ReplayGain(44100)

        self.assertEqual(
            rg.title_gain(audiotools.PCMFileReader(BytesIO(b""),
                                                   44100, 2, 0x3, 16)),
            (0.0, 0.0))
        self.assertRaises(ValueError, rg.album_gain)

        # check for no tracks
        assert(len(list(audiotools.calculate_replay_gain([]))) == 0)

        # check for lots of invalid combinations for calculate_replay_gain
        track_file1 = tempfile.NamedTemporaryFile(suffix=".wav")
        track_file2 = tempfile.NamedTemporaryFile(suffix=".wav")
        track_file3 = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            track1 = audiotools.WaveAudio.from_pcm(track_file1.name,
                                                   BLANK_PCM_Reader(2))
            track2 = audiotools.WaveAudio.from_pcm(track_file2.name,
                                                   BLANK_PCM_Reader(3))
            track3 = audiotools.WaveAudio.from_pcm(track_file3.name,
                                                   BLANK_PCM_Reader(2))

            gain = list(audiotools.calculate_replay_gain([track1,
                                                          track2,
                                                          track3]))
            self.assertEqual(len(gain), 3)
            self.assertIs(gain[0][0], track1)
            self.assertIs(gain[1][0], track2)
            self.assertIs(gain[2][0], track3)
        finally:
            track_file1.close()
            track_file2.close()
            track_file3.close()

    @LIB_REPLAYGAIN
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
                                              (30000, sample_rate // 100))
            (gain, peak) = gain.title_gain(reader)
            self.assertLess(gain, -4.0)
            self.assertGreater(peak, .90)

    @LIB_REPLAYGAIN
    def test_pcm(self):
        import audiotools.replaygain

        gain = audiotools.replaygain.ReplayGain(44100)
        (gain, peak) = gain.title_gain(
            test_streams.Sine16_Stereo(44100, 44100,
                                       441.0, 0.50,
                                       4410.0, 0.49, 1.0))

        main_reader = test_streams.Sine16_Stereo(44100, 44100,
                                                 441.0, 0.50,
                                                 4410.0, 0.49, 1.0)

        reader = audiotools.replaygain.ReplayGainReader(main_reader,
                                                        gain,
                                                        peak)

        # read FrameLists from ReplayGainReader
        f = reader.read(4096)
        while (len(f) > 0):
            f = reader.read(4096)

        # ensure subsequent reads return empty FrameLists
        for i in range(10):
            self.assertEqual(len(reader.read(4096)), 0)

        # ensure closing the ReplayGainReader raises ValueError
        # on subsequent reads
        reader.close()

        self.assertRaises(ValueError, reader.read, 4096)

        # ensure wrapped reader is also closed
        self.assertRaises(ValueError, main_reader.read, 4096)

    @LIB_REPLAYGAIN
    def test_reader(self):
        import audiotools.replaygain

        test_format = audiotools.WaveAudio

        dummy1 = tempfile.NamedTemporaryFile(suffix="." + test_format.SUFFIX)
        dummy2 = tempfile.NamedTemporaryFile(suffix="." + test_format.SUFFIX)
        try:
            # build dummy file
            track1 = test_format.from_pcm(
                dummy1.name,
                test_streams.Sine16_Stereo(44100, 44100,
                                           441.0, 0.50,
                                           4410.0, 0.49, 1.0))

            # calculate its ReplayGain
            gain = audiotools.replaygain.ReplayGain(track1.sample_rate())
            with track1.to_pcm() as pcm:
                (gain, peak) = gain.title_gain(pcm)

            # apply gain to dummy file
            track2 = test_format.from_pcm(
                dummy2.name,
                audiotools.replaygain.ReplayGainReader(track1.to_pcm(),
                                                       gain,
                                                       peak))

            # ensure gain applied is quieter than without gain applied
            gain2 = audiotools.replaygain.ReplayGain(track1.sample_rate())
            with track2.to_pcm() as pcm:
                (gain2, peak2) = gain2.title_gain(pcm)

            self.assertGreater(gain2, gain)
        finally:
            dummy1.close()
            dummy2.close()


class testcuesheet(unittest.TestCase):
    def setUp(self):
        from audiotools.cue import Cuesheet, read_cuesheet, write_cuesheet
        self.suffix = ".cue"
        self.sheet_class = Cuesheet
        self.read_sheet = read_cuesheet

    def __sheets__(self):
        from audiotools import Sheet, SheetTrack, SheetIndex

        def timestamp_to_frac(m, s, f):
            from fractions import Fraction
            return Fraction((m * 60 * 75) + (s * 75) + f, 75)

        # an ordinary cuesheet with no pre-gaps
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))]),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(5, 50, 65))]),
                     SheetTrack(
                     number=3,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(9, 47, 50))]),
                     SheetTrack(
                     number=4,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(15, 12, 53))]),
                     SheetTrack(
                     number=5,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(25, 2, 40))]),
                     SheetTrack(
                     number=6,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(27, 34, 5))]),
                     SheetTrack(
                     number=7,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(31, 58, 53))]),
                     SheetTrack(
                     number=8,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(35, 8, 65))])])

        # a cuesheet spread across a couple of different files
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))],
                     filename="TRACK1.WAV"),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(5, 50, 65))],
                     filename="TRACK1.WAV"),
                     SheetTrack(
                     number=3,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(9, 47, 50))],
                     filename="TRACK1.WAV"),
                     SheetTrack(
                     number=4,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(15, 12, 53))],
                     filename="TRACK1.WAV"),
                     SheetTrack(
                     number=5,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))],
                     filename="TRACK2.WAV"),
                     SheetTrack(
                     number=6,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(2, 31, 40))],
                     filename="TRACK2.WAV"),
                     SheetTrack(
                     number=7,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(6, 56, 13))],
                     filename="TRACK2.WAV"),
                     SheetTrack(
                     number=8,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(10, 6, 25))],
                     filename="TRACK2.WAV")])

        # mix in some pre-gaps
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))]),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(5, 49, 65)),
                         SheetIndex(1, timestamp_to_frac(5, 50, 65))]),
                     SheetTrack(
                     number=3,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(9, 45, 50)),
                         SheetIndex(1, timestamp_to_frac(9, 47, 50))]),
                     SheetTrack(
                     number=4,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(15, 9, 53)),
                         SheetIndex(1, timestamp_to_frac(15, 12, 53))])])

        # add catalog numbers, ISRCs and multiple index points
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0)),
                         SheetIndex(2, timestamp_to_frac(2, 0, 0)),
                         SheetIndex(3, timestamp_to_frac(4, 0, 0))],
                     metadata=audiotools.MetaData(
                         ISRC=u"ABCDE1234567"),
                     filename="MYAUDIO1.WAV"),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))],
                     metadata=audiotools.MetaData(
                         ISRC=u"XYZZY0000000"),
                     filename="MYAUDIO2.WAV"),
                     SheetTrack(
                     number=3,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(3, 0, 0)),
                         SheetIndex(1, timestamp_to_frac(3, 2, 0)),
                         SheetIndex(2, timestamp_to_frac(5, 34, 32)),
                         SheetIndex(3, timestamp_to_frac(8, 12, 49)),
                         SheetIndex(4, timestamp_to_frac(10, 1, 74))],
                    metadata=audiotools.MetaData(
                         ISRC=u"123456789012"),
                    filename="MYAUDIO2.WAV")],
                    metadata=audiotools.MetaData(catalog=u"3898347789120"))

    def __metadata_sheets__(self):
        from audiotools import Sheet, SheetTrack, SheetIndex

        def timestamp_to_frac(m, s, f):
            from fractions import Fraction
            return Fraction((m * 60 * 75) + (s * 75) + f, 75)

        # a sheet with a portable set of plain metadata
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))],
                     metadata=audiotools.MetaData(
                         track_name=u"Track 1",
                         performer_name=u"Performer 1",
                         artist_name=u"Artist 1"),
                     filename="CDImage.wav"),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(4, 36, 50)),
                         SheetIndex(1, timestamp_to_frac(4, 41, 10))],
                     metadata=audiotools.MetaData(
                         track_name=u"Track 2",
                         performer_name=u"Performer 2",
                         artist_name=u"Artist 2"),
                     filename="CDImage.wav")],
                     metadata=audiotools.MetaData(
                         album_name=u"Album Name",
                         performer_name=u"Album Performer",
                         artist_name=u"Album Artist"))

        # a sheet with a lot of strings that need escaping
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))],
                     metadata=audiotools.MetaData(
                         track_name=u"Track \"1\"",
                         performer_name=u"Performer \"1\"",
                         artist_name=u"Artist \"1\""),
                     filename="CD\"Image\".wav"),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(4, 36, 50)),
                         SheetIndex(1, timestamp_to_frac(4, 41, 10))],
                     metadata=audiotools.MetaData(
                         track_name=u"Track \"2\"",
                         performer_name=u"Performer \"2\"",
                         artist_name=u"Artist \"2\""),
                     filename="CD\"Image\".wav")],
                     metadata=audiotools.MetaData(
                         album_name=u"Album \"Name\"",
                         performer_name=u"Album \"Performer\"",
                         artist_name=u"Album \"Artist\""))

        # a sheet with lots of backslashes that need escaping
        yield Sheet([SheetTrack(
                     number=1,
                     track_indexes=[
                         SheetIndex(1, timestamp_to_frac(0, 0, 0))],
                     metadata=audiotools.MetaData(
                         track_name=u"Track \\ 1",
                         performer_name=u"Performer \\ 1",
                         artist_name=u"Artist \\ 1"),
                     filename="CD\\Image.wav"),
                     SheetTrack(
                     number=2,
                     track_indexes=[
                         SheetIndex(0, timestamp_to_frac(4, 36, 50)),
                         SheetIndex(1, timestamp_to_frac(4, 41, 10))],
                     metadata=audiotools.MetaData(
                         track_name=u"Track \\ 2",
                         performer_name=u"Performer \\ 2",
                         artist_name=u"Artist \\ 2"),
                     filename="CD\\Image.wav")],
                     metadata=audiotools.MetaData(
                         album_name=u"Album \\ Name",
                         performer_name=u"Album \\ Performer",
                         artist_name=u"Album \\ Artist"))

    @LIB_CUESHEET
    def test_attributes(self):
        from audiotools import Sheet, SheetTrack, SheetIndex

        def timestamp_to_frac(m, s, f):
            from fractions import Fraction
            return Fraction((m * 60 * 75) + (s * 75) + f, 75)

        raw_sheet = Sheet([SheetTrack(
                           number=1,
                           track_indexes=[
                               SheetIndex(0, timestamp_to_frac(0, 0, 0)),
                               SheetIndex(1, timestamp_to_frac(0, 1, 0))],
                           metadata=audiotools.MetaData(
                               track_name=u"Track 1"),
                           filename="CDImage.wav"),
                           SheetTrack(
                           number=2,
                           track_indexes=[
                               SheetIndex(1, timestamp_to_frac(0, 5, 0))],
                           metadata=audiotools.MetaData(
                               track_name=u"Track 2"),
                           filename="CDImage.wav"),
                           SheetTrack(
                           number=3,
                           track_indexes=[
                               SheetIndex(0, timestamp_to_frac(0, 9, 0)),
                               SheetIndex(1, timestamp_to_frac(0, 11, 0)),
                               SheetIndex(2, timestamp_to_frac(0, 12, 0))],
                           metadata=audiotools.MetaData(
                               track_name=u"Track 3"),
                           filename="CDImage.wav")])

        sheet = self.sheet_class.converted(raw_sheet)

        self.assertEqual(sheet, raw_sheet)
        for other_sheet in self.__sheets__():
            self.assertNotEqual(sheet, other_sheet)

        self.assertEqual(sheet.track_numbers(), [1, 2, 3])
        self.assertRaises(KeyError, sheet.track, 0)
        self.assertRaises(KeyError, sheet.track, 4)
        self.assertEqual(sheet.pre_gap(), 1)
        self.assertEqual(sheet.track_offset(1), 1)
        self.assertEqual(sheet.track_length(1), 4)
        self.assertEqual(sheet.track_offset(2), 5)
        self.assertEqual(sheet.track_length(2), 6)
        self.assertEqual(sheet.track_offset(3), 11)
        self.assertEqual(sheet.track_length(3), None)

        self.assertEqual(sheet.track(1).indexes(), [0, 1])
        self.assertRaises(KeyError, sheet.track(1).index, 2)
        self.assertEqual(sheet.track(2).indexes(), [1])
        self.assertRaises(KeyError, sheet.track(2).index, 0)
        self.assertRaises(KeyError, sheet.track(2).index, 2)
        self.assertEqual(sheet.track(3).indexes(), [0, 1, 2])
        self.assertRaises(KeyError, sheet.track(3).index, 3)

        round_trip_sheet = Sheet.converted(sheet)
        self.assertEqual(round_trip_sheet, sheet)

    @LIB_CUESHEET
    def test_round_trip(self):
        for sheet in self.__sheets__():
            converted = self.sheet_class.converted(sheet)
            self.assertEqual(converted, sheet)
            temp_sheet = tempfile.NamedTemporaryFile(suffix=self.suffix)
            temp_sheet.write(converted.build())
            temp_sheet.flush()
            re_read = self.read_sheet(temp_sheet.name)
            temp_sheet.close()
            self.assertEqual(re_read, sheet)

    @LIB_CUESHEET
    def test_metadata(self):
        for sheet in self.__metadata_sheets__():
            converted = self.sheet_class.converted(sheet)
            self.assertEqual(converted, sheet)
            temp_sheet = tempfile.NamedTemporaryFile(suffix=self.suffix)
            temp_sheet.write(converted.build())
            temp_sheet.flush()
            re_read = self.read_sheet(temp_sheet.name)
            temp_sheet.close()
            self.assertEqual(re_read, sheet)

    @LIB_CUESHEET
    def test_flags(self):
        from audiotools import Sheet, SheetTrack, SheetIndex
        from fractions import Fraction

        raw_sheet = Sheet([SheetTrack(
                           number=1,
                           track_indexes=[SheetIndex(1, Fraction(0, 1))],
                           filename="track1.wav",
                           pre_emphasis=False,
                           copy_permitted=False),
                           SheetTrack(
                           number=2,
                           track_indexes=[SheetIndex(1, Fraction(0, 1))],
                           filename="track2.wav",
                           pre_emphasis=True,
                           copy_permitted=False),
                           SheetTrack(
                           number=3,
                           track_indexes=[SheetIndex(1, Fraction(0, 1))],
                           filename="track3.wav",
                           pre_emphasis=False,
                           copy_permitted=True),
                           SheetTrack(
                           number=4,
                           track_indexes=[SheetIndex(1, Fraction(0, 1))],
                           filename="track4.wav",
                           pre_emphasis=True,
                           copy_permitted=True)])

        self.assertEqual(raw_sheet.track(1).filename(), "track1.wav")
        self.assertEqual(raw_sheet.track(1).pre_emphasis(), False)
        self.assertEqual(raw_sheet.track(1).copy_permitted(), False)
        self.assertEqual(raw_sheet.track(2).filename(), "track2.wav")
        self.assertEqual(raw_sheet.track(2).pre_emphasis(), True)
        self.assertEqual(raw_sheet.track(2).copy_permitted(), False)
        self.assertEqual(raw_sheet.track(3).filename(), "track3.wav")
        self.assertEqual(raw_sheet.track(3).pre_emphasis(), False)
        self.assertEqual(raw_sheet.track(3).copy_permitted(), True)
        self.assertEqual(raw_sheet.track(4).filename(), "track4.wav")
        self.assertEqual(raw_sheet.track(4).pre_emphasis(), True)
        self.assertEqual(raw_sheet.track(4).copy_permitted(), True)

        sheet = self.sheet_class.converted(raw_sheet)

        self.assertEqual(sheet.track(1).filename(), "track1.wav")
        self.assertEqual(sheet.track(1).pre_emphasis(), False)
        self.assertEqual(sheet.track(1).copy_permitted(), False)
        self.assertEqual(sheet.track(2).filename(), "track2.wav")
        self.assertEqual(sheet.track(2).pre_emphasis(), True)
        self.assertEqual(sheet.track(2).copy_permitted(), False)
        self.assertEqual(sheet.track(3).filename(), "track3.wav")
        self.assertEqual(sheet.track(3).pre_emphasis(), False)
        self.assertEqual(sheet.track(3).copy_permitted(), True)
        self.assertEqual(sheet.track(4).filename(), "track4.wav")
        self.assertEqual(sheet.track(4).pre_emphasis(), True)
        self.assertEqual(sheet.track(4).copy_permitted(), True)

        self.assertEqual(sheet, raw_sheet)

        for other_sheet in self.__sheets__():
           self.assertNotEqual(sheet, other_sheet)

        # round-trip sheet to disk to ensure it still works
        temp_sheet = tempfile.NamedTemporaryFile(suffix=self.suffix)
        temp_sheet.write(sheet.build())
        temp_sheet.flush()
        re_read = self.read_sheet(temp_sheet.name)
        temp_sheet.close()
        self.assertEqual(re_read, sheet)


class testtocfile(testcuesheet):
    def setUp(self):
        from audiotools.toc import TOCFile, read_tocfile, write_tocfile
        self.suffix = ".toc"
        self.sheet_class = TOCFile
        self.read_sheet = read_tocfile


class test_flac_cuesheet(testcuesheet):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio

    def __sheets__(self):
        # unlike the regular testcuesheet files
        # these only contain CD images

        for sheet in testcuesheet.__sheets__(self):
            if (sheet.image_formatted()):
                yield sheet

    @LIB_CUESHEET
    def test_attributes(self):
        from audiotools import Sheet, SheetTrack, SheetIndex
        from audiotools.flac import Flac_CUESHEET

        def timestamp_to_frac(m, s, f):
            from fractions import Fraction
            return Fraction((m * 60 * 75) + (s * 75) + f, 75)

        raw_sheet = Sheet([SheetTrack(
                           number=1,
                           track_indexes=[
                               SheetIndex(0, timestamp_to_frac(0, 0, 0)),
                               SheetIndex(1, timestamp_to_frac(0, 1, 0))],
                           metadata=audiotools.MetaData(
                               track_name=u"Track 1"),
                           filename="CDImage.wav"),
                           SheetTrack(
                           number=2,
                           track_indexes=[
                               SheetIndex(1, timestamp_to_frac(0, 5, 0))],
                           metadata=audiotools.MetaData(
                               track_name=u"Track 2"),
                           filename="CDImage.wav"),
                           SheetTrack(
                           number=3,
                           track_indexes=[
                               SheetIndex(0, timestamp_to_frac(0, 9, 0)),
                               SheetIndex(1, timestamp_to_frac(0, 11, 0)),
                               SheetIndex(2, timestamp_to_frac(0, 12, 0))],
                           metadata=audiotools.MetaData(
                               track_name=u"Track 3"),
                           filename="CDImage.wav")])

        sheet = Flac_CUESHEET.converted(raw_sheet, 882000, 44100)

        self.assertEqual(sheet, raw_sheet)
        for other_sheet in self.__sheets__():
            self.assertNotEqual(sheet, other_sheet)

        self.assertEqual(sheet.track_numbers(), [1, 2, 3])
        self.assertRaises(KeyError, sheet.track, 0)
        self.assertRaises(KeyError, sheet.track, 4)
        self.assertEqual(sheet.pre_gap(), 1)
        self.assertEqual(sheet.track_offset(1), 1)
        self.assertEqual(sheet.track_length(1), 4)
        self.assertEqual(sheet.track_offset(2), 5)
        self.assertEqual(sheet.track_length(2), 6)
        self.assertEqual(sheet.track_offset(3), 11)
        self.assertEqual(sheet.track_length(3), 9)

        self.assertEqual(sheet.track(1).indexes(), [0, 1])
        self.assertRaises(KeyError, sheet.track(1).index, 2)
        self.assertEqual(sheet.track(2).indexes(), [1])
        self.assertRaises(KeyError, sheet.track(2).index, 0)
        self.assertRaises(KeyError, sheet.track(2).index, 2)
        self.assertEqual(sheet.track(3).indexes(), [0, 1, 2])
        self.assertRaises(KeyError, sheet.track(3).index, 3)

        round_trip_sheet = Sheet.converted(sheet)
        self.assertEqual(round_trip_sheet, sheet)

    @LIB_CUESHEET
    def test_round_trip(self):
        sample_rate = 44100

        for sheet in self.__sheets__():
            # tack on 1 minute to cuesheet's last index for total size
            total_length = int((sheet[-1][-1].offset() + 60) * sample_rate)

            # create dummy file
            temp_file = tempfile.NamedTemporaryFile(
                suffix="." + self.audio_class.SUFFIX)
            temp_track = self.audio_class.from_pcm(
                temp_file.name,
                EXACT_SILENCE_PCM_Reader(pcm_frames=total_length,
                                         sample_rate=sample_rate,
                                         channels=2,
                                         bits_per_sample=16,
                                         channel_mask=0x3),
                total_pcm_frames=total_length)

            # set cuesheet
            temp_track.set_cuesheet(sheet)

            # get cuesheet
            track_sheet = audiotools.open(temp_file.name).get_cuesheet()
            self.assertIsNot(track_sheet, None)

            # ensure they match
            self.assertEqual(track_sheet, sheet)

            # clean out dummy file
            temp_file.close()

    @LIB_CUESHEET
    def test_metadata(self):
        # FLAC cuesheets don't support meaningful metadata
        # outside of catalog and ISRC
        self.assertTrue(True)

    @LIB_CUESHEET
    def test_flags(self):
        # FLAC cuesheets only support pre-emphasis flag
        #FIXME

        self.assertTrue(True)


class test_oggflac_cuesheet(test_flac_cuesheet):
    def setUp(self):
        self.audio_class = audiotools.OggFlacAudio

    @LIB_CUESHEET
    def test_attributes(self):
        pass


class test_tta_cuesheet(test_flac_cuesheet):
    def setUp(self):
        self.audio_class = audiotools.TrueAudio

    @LIB_CUESHEET
    def test_attributes(self):
        pass


class test_wavpack_cuesheet(test_flac_cuesheet):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio

    @LIB_CUESHEET
    def test_attributes(self):
        pass


class TestMultiChannel(unittest.TestCase):
    def setUp(self):
        # these support the full range of ChannelMasks
        self.wav_channel_masks = [audiotools.WaveAudio,
                                  audiotools.WavPackAudio]

        # these support a subset of ChannelMasks up to 6 channels
        self.flac_channel_masks = [audiotools.FlacAudio,
                                   audiotools.OggFlacAudio]

        # these support a reordered subset of ChannelMasks up to 8 channels
        self.vorbis_channel_masks = [audiotools.VorbisAudio,
                                     audiotools.OpusAudio]

    def __test_mask_blank__(self, audio_class, channel_mask):
        with tempfile.NamedTemporaryFile(
                 suffix="." + audio_class.SUFFIX) as temp_file:
            temp_track = audio_class.from_pcm(
                temp_file.name,
                Join_Reader(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in range(len(channel_mask))],
                    channel_mask))
            self.assertEqual(temp_track.channel_mask(), channel_mask,
                             "%s != %s for format %s" %
                             (temp_track.channel_mask(),
                              channel_mask,
                              audio_class.NAME))

            with temp_track.to_pcm() as pcm:
                self.assertEqual(int(pcm.channel_mask), int(channel_mask))
                audiotools.transfer_framelist_data(pcm, lambda x: x)

    def __test_undefined_mask_blank__(self, audio_class, channels,
                                      should_be_blank):
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX)
        try:
            temp_track = audio_class.from_pcm(
                temp_file.name,
                Join_Reader(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in range(channels)],
                    audiotools.ChannelMask(0)))
            self.assertEqual(temp_track.channels(), channels)
            if (should_be_blank):
                self.assertEqual(int(temp_track.channel_mask()), 0)
                with temp_track.to_pcm() as pcm:
                    self.assertEqual(int(pcm.channel_mask), 0)
                    audiotools.transfer_framelist_data(pcm, lambda x: x)
            else:
                self.assertNotEqual(int(temp_track.channel_mask()), 0,
                                    "mask = %s for format %s at %d channels" %
                                    (temp_track.channel_mask(),
                                     audio_class,
                                     channels))
                with temp_track.to_pcm() as pcm:
                    self.assertEqual(int(pcm.channel_mask),
                                     int(temp_track.channel_mask()))
                    audiotools.transfer_framelist_data(pcm, lambda x: x)
        finally:
            temp_file.close()

    def __test_error_mask_blank__(self, audio_class, channels,
                                  channel_mask):
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX)
        try:
            self.assertRaises(
                audiotools.UnsupportedChannelMask,
                audio_class.from_pcm,
                temp_file.name,
                Join_Reader([BLANK_PCM_Reader(2, channels=1)
                             for i in range(channels)],
                            channel_mask))
        finally:
            temp_file.close()

    def __test_error_channel_count__(self, audio_class, channels,
                                     channel_mask):
        temp_file = tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX)
        try:
            self.assertRaises(
                audiotools.UnsupportedChannelCount,
                audio_class.from_pcm,
                temp_file.name,
                Join_Reader([BLANK_PCM_Reader(2, channels=1)
                             for i in range(channels)],
                            channel_mask))
        finally:
            temp_file.close()

    def __test_pcm_conversion__(self,
                                source_audio_class,
                                target_audio_class,
                                channel_mask):
        source_file = tempfile.NamedTemporaryFile(
            suffix="." + source_audio_class.SUFFIX)
        target_file = tempfile.NamedTemporaryFile(
            suffix="." + target_audio_class.SUFFIX)
        wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            source_track = source_audio_class.from_pcm(
                source_file.name,
                Join_Reader(
                    [BLANK_PCM_Reader(2, channels=1)
                     for i in range(len(channel_mask))],
                    channel_mask))
            self.assertEqual(source_track.channel_mask(), channel_mask)

            source_pcm = source_track.to_pcm()

            self.assertEqual(isinstance(source_pcm.channel_mask, int),
                             True,
                             "%s's to_pcm() PCMReader is not an int" %
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
                for mask in [from_fields(front_left=True,
                                         front_right=True,
                                         front_center=True,
                                         side_left=True,
                                         side_right=True,
                                         back_center=True,
                                         low_frequency=True),
                             from_fields(front_left=True,
                                         front_right=True,
                                         side_left=True,
                                         side_right=True,
                                         back_left=True,
                                         back_right=True,
                                         front_center=True,
                                         low_frequency=True)]:
                    self.__test_pcm_conversion__(source_audio_class,
                                                 target_audio_class,
                                                 mask)

        for source_audio_class in self.wav_channel_masks:
            for target_audio_class in self.wav_channel_masks:
                for mask in [from_fields(front_left=True,
                                         front_right=True,
                                         side_left=True,
                                         side_right=True,
                                         back_left=True,
                                         back_right=True,
                                         front_center=True,
                                         back_center=True,
                                         low_frequency=True),
                             from_fields(front_left=True,
                                         front_right=True,
                                         side_left=True,
                                         side_right=True,
                                         back_left=True,
                                         back_right=True,
                                         front_center=True,
                                         back_center=True)]:
                    self.__test_pcm_conversion__(source_audio_class,
                                                 target_audio_class,
                                                 mask)

    @LIB_CORE
    def test_unsupported_channel_mask_from_pcm(self):
        for channels in range(1, 6 + 1):
            self.__test_undefined_mask_blank__(audiotools.WaveAudio,
                                               channels,
                                               False)
        for channels in range(1, 3):
            self.__test_undefined_mask_blank__(audiotools.WavPackAudio,
                                               channels,
                                               False)
        for channels in range(3, 21):
            self.__test_undefined_mask_blank__(audiotools.WavPackAudio,
                                               channels,
                                               True)

        for channels in range(1, 9):
            self.__test_undefined_mask_blank__(audiotools.ALACAudio,
                                               channels,
                                               False)
        for channels in range(9, 21):
            self.__test_undefined_mask_blank__(audiotools.ALACAudio,
                                               channels,
                                               True)

        for audio_class in [audiotools.FlacAudio, audiotools.OggFlacAudio]:
            for channels in range(1, 9):
                self.__test_undefined_mask_blank__(audio_class,
                                                   channels,
                                                   False)

            self.__test_error_channel_count__(audio_class,
                                              9, audiotools.ChannelMask(0))
            self.__test_error_channel_count__(audio_class,
                                              10, audiotools.ChannelMask(0))

        for stereo_audio_class in [audiotools.MP3Audio,
                                   audiotools.MP2Audio]:

            self.__test_undefined_mask_blank__(stereo_audio_class,
                                               2, False)
            for channels in range(3, 20):
                temp_file = tempfile.NamedTemporaryFile(
                    suffix="." + stereo_audio_class.SUFFIX)
                try:
                    temp_track = stereo_audio_class.from_pcm(
                        temp_file.name,
                        Join_Reader(
                            [BLANK_PCM_Reader(2, channels=1)
                             for i in range(channels)],
                            audiotools.ChannelMask(0)))
                    self.assertEqual(temp_track.channels(), 2)
                    self.assertEqual(
                        int(temp_track.channel_mask()),
                        int(audiotools.ChannelMask.from_fields(
                            front_left=True, front_right=True)))
                    with temp_track.to_pcm() as pcm:
                        self.assertEqual(int(pcm.channel_mask),
                                         int(temp_track.channel_mask()))
                        audiotools.transfer_framelist_data(pcm, lambda x: x)
                finally:
                    temp_file.close()

        for channels in range(1, 9):
            self.__test_undefined_mask_blank__(audiotools.VorbisAudio,
                                               channels,
                                               False)

        for channels in range(9, 20):
            self.__test_undefined_mask_blank__(audiotools.VorbisAudio,
                                               channels,
                                               True)

        for channels in [1, 2]:
            self.__test_undefined_mask_blank__(audiotools.AiffAudio,
                                               channels,
                                               False)

        for channels in [3, 4, 5, 6, 7, 8, 9, 10]:
            self.__test_undefined_mask_blank__(audiotools.AiffAudio,
                                               channels,
                                               True)

        for channels in [1, 2]:
            self.__test_undefined_mask_blank__(audiotools.AuAudio,
                                               channels,
                                               False)
        for channels in range(3, 11):
            self.__test_undefined_mask_blank__(audiotools.AuAudio,
                                               channels,
                                               True)


class Test_FreeDB(unittest.TestCase):
    def __test_disc_id_tracks__(self, disc_id_obj,
                                track_lengths,
                                cuesheet,
                                disc_id):
        from audiotools.cdio import CDDAReader
        from shutil import rmtree

        dir = tempfile.mkdtemp()
        try:
            # dump cuesheet to temporary directory
            f = open(os.path.join(dir, "CDImage.cue"), "wb")
            f.write(cuesheet)
            f.close()

            # build CD image from track lengths
            f = open(os.path.join(dir, "CDImage.bin"), "wb")
            f.write(chr(0) * 2 * 2 * sum(track_lengths))
            f.close()

            # open disc image with CDDAReader
            cddareader = CDDAReader(os.path.join(dir, "CDImage.cue"))

            # ensure DiscID from CDDAReader matches
            self.assertEqual(str(disc_id_obj.from_cddareader(cddareader)),
                             disc_id)

            # dump contents of CDDAReader to individual tracks
            tracks = []
            for i in sorted(cddareader.track_offsets.keys()):
                offset = cddareader.track_offsets[i]
                length = cddareader.track_lengths[i]
                self.assertEqual(length, track_lengths[i - 1])
                self.assertEqual(cddareader.seek(offset), offset)
                tracks.append(audiotools.WaveAudio.from_pcm(
                    os.path.join(dir, "track%d.wav"),
                    audiotools.PCMReaderHead(cddareader, length, False),
                    total_pcm_frames=length))

            # ensure DiscID from tracks matches
            self.assertEqual(str(disc_id_obj.from_tracks(tracks)),
                             str(disc_id_obj.from_cddareader(cddareader)))

            # open cuesheet as a Sheet object
            sheet = audiotools.read_sheet(os.path.join(dir, "CDImage.cue"))

            # ensure DiscID from sheet matches
            self.assertEqual(str(disc_id_obj.from_sheet(sheet,
                                                        sum(track_lengths),
                                                        44100)),
                             str(disc_id_obj.from_cddareader(cddareader)))
        finally:
            rmtree(dir)

    def __test_disc_id__(self, disc_id_obj,
                         total_length,
                         cuesheet,
                         disc_id):
        from audiotools.cdio import CDDAReader
        from shutil import rmtree

        dir = tempfile.mkdtemp()
        try:
            # dump cuesheet to temporary directory
            f = open(os.path.join(dir, "CDImage.cue"), "wb")
            f.write(cuesheet)
            f.close()

            # build CD image from total length
            f = open(os.path.join(dir, "CDImage.bin"), "wb")
            f.write(chr(0) * 2 * 2 * total_length)
            f.close()

            # open disc image with CDDAReader
            cddareader = CDDAReader(os.path.join(dir, "CDImage.cue"))

            # ensure DiscID from CDDAReader matches
            self.assertEqual(str(disc_id_obj.from_cddareader(cddareader)),
                             disc_id)

            # open cuesheet as a Sheet object
            sheet = audiotools.read_sheet(os.path.join(dir, "CDImage.cue"))

            # ensure DiscID from sheet matches
            self.assertEqual(str(disc_id_obj.from_sheet(sheet,
                                                        total_length,
                                                        44100)),
                             str(disc_id_obj.from_cddareader(cddareader)))
        finally:
            rmtree(dir)

    @LIB_FREEDB
    def test_discid(self):
        from audiotools.freedb import DiscID

        self.__test_disc_id_tracks__(
            disc_id_obj=DiscID,
            track_lengths=[7939176, 4799256, 6297480, 5383140,
                           5246136, 5052684, 5013876],
            cuesheet=open("freedb_test_discid-1.cue", "rb").read(),
            disc_id="5A038407")

        self.__test_disc_id_tracks__(
            disc_id_obj=DiscID,
            track_lengths=[1339464, 4048380, 692076, 10600464, 10602816,
                           1178940, 7454664, 2664816, 989604, 7008960,
                           9632616, 1070160, 6094620, 1622880, 13361124,
                           403956, 5208504, 7373520, 483336, 12012840,
                           8534820, 439824, 7626360, 1262436, 4874520,
                           398664, 11229036, 483924, 9003456, 883764,
                           5018580],
            cuesheet=open("freedb_test_discid-2.cue", "rb").read(),
            disc_id="BE0D9A1F")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=190928304,
            cuesheet=open("freedb_test_discid-3.cue", "rb").read(),
            disc_id="A610E90A")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=127937040,
            cuesheet=open("freedb_test_discid-4.cue", "rb").read(),
            disc_id="CE0AD30E")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=119882616,
            cuesheet=open("freedb_test_discid-5.cue", "rb").read(),
            disc_id="FC0A9E14")


class Test_MusicBrainz(Test_FreeDB):
    @LIB_MUSICBRAINZ
    def test_discid(self):
        from audiotools.musicbrainz import DiscID

        self.__test_disc_id_tracks__(
            disc_id_obj=DiscID,
            track_lengths=[7939176, 4799256, 6297480, 5383140,
                           5246136, 5052684, 5013876],
            cuesheet=open("freedb_test_discid-1.cue", "rb").read(),
            disc_id="SJco4q4a9rzKdBw7HcFvBQugKc8-")

        self.__test_disc_id_tracks__(
            disc_id_obj=DiscID,
            track_lengths=[1339464, 4048380, 692076, 10600464, 10602816,
                           1178940, 7454664, 2664816, 989604, 7008960,
                           9632616, 1070160, 6094620, 1622880, 13361124,
                           403956, 5208504, 7373520, 483336, 12012840,
                           8534820, 439824, 7626360, 1262436, 4874520,
                           398664, 11229036, 483924, 9003456, 883764,
                           5018580],
            cuesheet=open("freedb_test_discid-2.cue", "rb").read(),
            disc_id="yrelpXuXXP2WKDpTUqrS62keIFE-")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=190928304,
            cuesheet=open("freedb_test_discid-3.cue", "rb").read(),
            disc_id="naJ8mpfbMHx_qQnJbyRx4lE_h4E-")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=127937040,
            cuesheet=open("freedb_test_discid-4.cue", "rb").read(),
            disc_id="1o5aDeltYCEwCecU1cMMi1cvees-")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=119882616,
            cuesheet=open("freedb_test_discid-5.cue", "rb").read(),
            disc_id="aS0RfXDrxs718yypC2AlgpNEIE0-")


class Test_Accuraterip(Test_FreeDB):
    @LIB_ACCURATERIP
    def test_discid(self):
        from audiotools.accuraterip import DiscID

        self.__test_disc_id_tracks__(
            disc_id_obj=DiscID,
            track_lengths=[7939176, 4799256, 6297480, 5383140,
                           5246136, 5052684, 5013876],
            cuesheet=open("freedb_test_discid-1.cue", "rb").read(),
            disc_id="dBAR-007-00045db7-0019b8d8-5a038407.bin")

        self.__test_disc_id_tracks__(
            disc_id_obj=DiscID,
            track_lengths=[1339464, 4048380, 692076, 10600464, 10602816,
                           1178940, 7454664, 2664816, 989604, 7008960,
                           9632616, 1070160, 6094620, 1622880, 13361124,
                           403956, 5208504, 7373520, 483336, 12012840,
                           8534820, 439824, 7626360, 1262436, 4874520,
                           398664, 11229036, 483924, 9003456, 883764,
                           5018580],
            cuesheet=open("freedb_test_discid-2.cue", "rb").read(),
            disc_id="dBAR-031-003fee31-058c64b9-be0d9a1f.bin")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=190928304,
            cuesheet=open("freedb_test_discid-3.cue", "rb").read(),
            disc_id="dBAR-010-00193b54-00c9f723-a610e90a.bin")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=127937040,
            cuesheet=open("freedb_test_discid-4.cue", "rb").read(),
            disc_id="dBAR-014-001977f9-01097144-ce0ad30e.bin")

        self.__test_disc_id__(
            disc_id_obj=DiscID,
            total_length=119882616,
            cuesheet=open("freedb_test_discid-5.cue", "rb").read(),
            disc_id="dBAR-020-001d4d13-01bab5f6-fc0a9e14.bin")

    @LIB_ACCURATERIP
    def test_checksum(self):
        from audiotools.accuraterip import Checksum
        from test_streams import Simple_Sine, Generate02

        # sanity checking for initial options
        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=10,
                          sample_rate=0,
                          is_first=False,
                          is_last=False,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=10,
                          sample_rate=-1,
                          is_first=False,
                          is_last=False,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=0,
                          sample_rate=44100,
                          is_first=False,
                          is_last=False,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=-1,
                          sample_rate=44100,
                          is_first=False,
                          is_last=False,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=-1,
                          sample_rate=-1,
                          is_first=False,
                          is_last=False,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=10,
                          sample_rate=44100,
                          is_first=False,
                          is_last=False,
                          pcm_frame_range=0,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=10,
                          sample_rate=44100,
                          is_first=False,
                          is_last=False,
                          pcm_frame_range=-1,
                          accurateripv2_offset=0)

        self.assertRaises(ValueError,
                          Checksum,
                          total_pcm_frames=10,
                          sample_rate=44100,
                          is_first=False,
                          is_last=False,
                          accurateripv2_offset=-1)

        checksum = Checksum(total_pcm_frames=200000,
                            sample_rate=44100,
                            is_first=False,
                            is_last=False,
                            pcm_frame_range=1)

        for v in [None, 0, 1, "foo", "bar"]:
            self.assertRaises(TypeError,
                              checksum.update,
                              v)

        # sanity checking for stream parameters
        for params in [[200000, 44100, 0x04, 8, (25, 10000)],      # 8bps 1ch
                       [200000, 44100, 0x03, 8, (25, 10000),
                                                (50, 20000)],      # 8bps 2ch
                       [200000, 44100, 0x07, 8, (25, 10000),
                                                (50, 20000),
                                                (120, 30000)],     # 8bps 3ch
                       [200000, 44100, 0x04, 16, (6400, 10000)],   # 16bps 1ch
                       [200000, 44100, 0x07, 16, (6400, 10000),
                                                 (12800, 20000),
                                                 (30720, 30000)],  # 16bps 3ch
                       [200000, 44100, 0x04, 24,
                        (1638400, 10000)],                         # 24bps 1ch
                       [200000, 44100, 0x03, 24,
                        (1638400, 10000),
                        (3276800, 20000)],                         # 24bps 2ch
                       [200000, 44100, 0x07, 24,
                        (1638400, 10000),
                        (3276800, 20000),
                        (7864320, 30000)]]:                        # 24bps 3ch
            sine = Simple_Sine(*params)
            checksum = Checksum(total_pcm_frames=200000,
                                sample_rate=44100,
                                is_first=False,
                                is_last=False,
                                pcm_frame_range=1)
            self.assertRaises(ValueError,
                              audiotools.transfer_data,
                              sine.read, checksum.update)

        # ensure very short streams work correctly
        # whether middle, first, last or only track
        short_track = Checksum(total_pcm_frames=1,
                               sample_rate=44100,
                               is_first=False,
                               is_last=False,
                               pcm_frame_range=1)
        audiotools.transfer_data(
            Generate02(44100).read, short_track.update)
        self.assertEqual(short_track.checksums_v1(), [0x7FFF8000])
        self.assertEqual(short_track.checksum_v2(), 0x7FFF8000)

        short_track = Checksum(total_pcm_frames=1,
                               sample_rate=44100,
                               is_first=True,
                               is_last=False,
                               pcm_frame_range=1)
        audiotools.transfer_data(
            Generate02(44100).read, short_track.update)
        self.assertEqual(short_track.checksums_v1(), [0])
        self.assertEqual(short_track.checksum_v2(), 0)

        short_track = Checksum(total_pcm_frames=1,
                               sample_rate=44100,
                               is_first=False,
                               is_last=True,
                               pcm_frame_range=1)
        audiotools.transfer_data(
            Generate02(44100).read, short_track.update)
        self.assertEqual(short_track.checksums_v1(), [0])
        self.assertEqual(short_track.checksum_v2(), 0)

        short_track = Checksum(total_pcm_frames=1,
                               sample_rate=44100,
                               is_first=True,
                               is_last=True,
                               pcm_frame_range=1)
        audiotools.transfer_data(
            Generate02(44100).read, short_track.update)
        self.assertEqual(short_track.checksums_v1(), [0])
        self.assertEqual(short_track.checksum_v2(), 0)

        track = audiotools.open("tone.flac")

        # ensure various checksum range options work correctly
        # values taken from reference implementation

        middle_track = Checksum(total_pcm_frames=track.total_frames(),
                                sample_rate=track.sample_rate(),
                                is_first=False,
                                is_last=False)
        with track.to_pcm() as pcmreader:
            audiotools.transfer_data(pcmreader.read, middle_track.update)
        self.assertEqual(middle_track.checksums_v1(), [0xF6E4AD26])
        self.assertEqual(middle_track.checksum_v2(), 0x4781FC37)

        middle_track = Checksum(total_pcm_frames=track.total_frames(),
                                sample_rate=track.sample_rate(),
                                is_first=False,
                                is_last=False,
                                pcm_frame_range=3,
                                accurateripv2_offset=1)
        with audiotools.PCMReaderWindow(track.to_pcm(),
                                        -1,
                                        track.total_frames() + 2) as pcmreader:
            audiotools.transfer_data(pcmreader.read, middle_track.update)
        self.assertEqual(middle_track.checksums_v1(), [0xCA705E69,
                                                       0xF6E4AD26,
                                                       0x951FB12F])
        self.assertEqual(middle_track.checksum_v2(), 0x4781FC37)
        # self.assertEqual(middle_track.checksums_v2(), [0x1B0BE28C,
        #                                                0x4781FC37,
        #                                                0xE5B9A28E])

        first_track = Checksum(total_pcm_frames=track.total_frames(),
                               sample_rate=track.sample_rate(),
                               is_first=True,
                               is_last=False)
        with track.to_pcm() as pcmreader:
            audiotools.transfer_data(pcmreader.read, first_track.update)
        self.assertEqual(first_track.checksums_v1(), [0xEE4DBEB4])
        self.assertEqual(first_track.checksum_v2(), 0x3ECA2C04)

        first_track = Checksum(total_pcm_frames=track.total_frames(),
                               sample_rate=track.sample_rate(),
                               is_first=True,
                               is_last=False,
                               pcm_frame_range=3,
                               accurateripv2_offset=1)
        with audiotools.PCMReaderWindow(track.to_pcm(),
                                        -1,
                                        track.total_frames() + 2) as pcmreader:
            audiotools.transfer_data(pcmreader.read, first_track.update)
        self.assertEqual(first_track.checksums_v1(), [0x7CC66A55,
                                                      0xEE4DBEB4,
                                                      0x9A58C7EC])
        self.assertEqual(first_track.checksum_v2(), 0x3ECA2C04)
        # self.assertEqual(first_track.checksums_v2(), [0xCD410A97,
        #                                               0x3ECA2C04,
        #                                               0xEAD1D8AA])

        last_track = Checksum(total_pcm_frames=track.total_frames(),
                              sample_rate=track.sample_rate(),
                              is_first=False,
                              is_last=True)
        with track.to_pcm() as pcmreader:
            audiotools.transfer_data(pcmreader.read, last_track.update)
        self.assertEqual(last_track.checksums_v1(), [0xF819E862])
        self.assertEqual(last_track.checksum_v2(), 0x222E32FA)

        last_track = Checksum(total_pcm_frames=track.total_frames(),
                              sample_rate=track.sample_rate(),
                              is_first=False,
                              is_last=True,
                              pcm_frame_range=3,
                              accurateripv2_offset=1)
        with audiotools.PCMReaderWindow(track.to_pcm(),
                                        -1,
                                        track.total_frames() + 2) as pcmreader:
            audiotools.transfer_data(pcmreader.read, last_track.update)
        self.assertEqual(last_track.checksums_v1(), [0x682F9316,
                                                     0xF819E862,
                                                     0x00DBAF4E])
        self.assertEqual(last_track.checksum_v2(), 0x222E32FA)
        # self.assertEqual(last_track.checksums_v2(), [0x92419BB8,
        #                                              0x222E32FA,
        #                                              0x2AF10061])

        only_track = Checksum(total_pcm_frames=track.total_frames(),
                              sample_rate=track.sample_rate(),
                              is_first=True,
                              is_last=True)
        with track.to_pcm() as pcmreader:
            audiotools.transfer_data(pcmreader.read, only_track.update)
        self.assertEqual(only_track.checksums_v1(), [0xEF82F9F0])
        self.assertEqual(only_track.checksum_v2(), 0x197662C7)

        only_track = Checksum(total_pcm_frames=track.total_frames(),
                              sample_rate=track.sample_rate(),
                              is_first=True,
                              is_last=True,
                              pcm_frame_range=3,
                              accurateripv2_offset=1)
        with audiotools.PCMReaderWindow(track.to_pcm(),
                                        -1,
                                        track.total_frames() + 2) as pcmreader:
            audiotools.transfer_data(pcmreader.read, only_track.update)
        self.assertEqual(only_track.checksums_v1(), [0x1A859F02,
                                                     0xEF82F9F0,
                                                     0x0614C60B])
        self.assertEqual(only_track.checksum_v2(), 0x197662C7)
        # self.assertEqual(only_track.checksums_v2(), [0x4476C3C3,
        #                                              0x197662C7,
        #                                              0x3009367D])

        # ensure feeding checksum with not enough samples
        # raises ValueError at checksums()-time
        insufficient_samples = Checksum(
            total_pcm_frames=track.total_frames() + 1,
            sample_rate=track.sample_rate(),
            is_first=False,
            is_last=False,
            pcm_frame_range=1)
        with track.to_pcm() as pcmreader:
            audiotools.transfer_data(pcmreader.read,
                                     insufficient_samples.update)
        self.assertRaises(ValueError, insufficient_samples.checksums_v1)
        self.assertRaises(ValueError, insufficient_samples.checksum_v2)

        # ensure insufficient samples also works with a range
        insufficient_samples = Checksum(
            total_pcm_frames=track.total_frames(),
            sample_rate=track.sample_rate(),
            is_first=False,
            is_last=False,
            pcm_frame_range=2,
            accurateripv2_offset=1)
        with track.to_pcm() as pcmreader:
            audiotools.transfer_data(pcmreader.read,
                                     insufficient_samples.update)
        self.assertRaises(ValueError, insufficient_samples.checksums_v1)
        self.assertRaises(ValueError, insufficient_samples.checksum_v2)

        # ensure feeding checksum with too many samples
        # raises ValueError at update()-time
        too_many_samples = Checksum(
            total_pcm_frames=track.total_frames() - 1,
            sample_rate=track.sample_rate(),
            is_first=False,
            is_last=False,
            pcm_frame_range=1)
        with track.to_pcm() as pcmreader:
            self.assertRaises(ValueError,
                              audiotools.transfer_data,
                              pcmreader.read,
                              too_many_samples.update)

        # ensure too many samples also works with a range
        too_many_samples = Checksum(
            total_pcm_frames=track.total_frames() - 2,
            sample_rate=track.sample_rate(),
            is_first=False,
            is_last=False,
            pcm_frame_range=2)
        with track.to_pcm() as pcmreader:
            self.assertRaises(ValueError,
                              audiotools.transfer_data,
                              pcmreader.read,
                              too_many_samples.update)

    @LIB_ACCURATERIP
    def test_perform_lookup(self):
        from audiotools.freedb import DiscID as FDiscID
        from audiotools.accuraterip import DiscID, perform_lookup
        import time

        offsets = [0, 2278, 9163, 10340, 28368, 46400, 48405,
                   61083, 65615, 67298, 79218, 95600, 97420,
                   107785, 110545, 133268, 133955, 142813,
                   155353, 156175, 176605, 191120, 191868,
                   204838, 206985, 215275, 215953, 235050,
                   235873, 251185, 252688]

        freedb_disc_id = FDiscID(
            offsets=offsets,
            total_length=3482,
            track_count=31)

        disc_id = DiscID(
            track_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                           13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
                           23, 24, 25, 26, 27, 28, 29, 30, 31],
            track_offsets=offsets,
            lead_out_offset=261223,
            freedb_disc_id=freedb_disc_id)

        matches = perform_lookup(disc_id)
        time.sleep(1)

        self.assertEqual(set(matches.keys()), set(range(1, 32)))

    @LIB_ACCURATERIP
    def test_accuraterip_lookup(self):
        import time

        lengths = [1339464, 4048380, 692076, 10600464, 10602816,
                   1178940, 7454664, 2664816, 989604, 7008960,
                   9632616, 1070160, 6094620, 1622880, 13361124,
                   403956, 5208504, 7373520, 483336, 12012840,
                   8534820, 439824, 7626360, 1262436, 4874520,
                   398664, 11229036, 483924, 9003456, 883764, 5018580]
        tempfiles = [tempfile.NamedTemporaryFile(suffix=".flac")
                     for l in lengths]

        tracks = [audiotools.FlacAudio.from_pcm(
                  t.name,
                  EXACT_SILENCE_PCM_Reader(pcm_frames=l,
                                           sample_rate=44100,
                                           channels=2,
                                           channel_mask=0x3,
                                           bits_per_sample=16),
                  total_pcm_frames=l)
                  for (t, l) in zip(tempfiles, lengths)]

        matches = audiotools.accuraterip_lookup(tracks)
        time.sleep(1)

        for t in tempfiles:
            t.close()

        self.assertEqual(set(matches.keys()), set(range(1, 32)))

    @LIB_ACCURATERIP
    def test_accuraterip_sheet_lookup(self):
        import time

        cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        cuesheet.write(open("freedb_test_discid-2.cue", "rb").read())
        cuesheet.flush()
        sheet = audiotools.read_sheet(cuesheet.name)
        cuesheet.close()

        matches = audiotools.accuraterip_sheet_lookup(sheet, 153599124, 44100)
        time.sleep(1)

        self.assertEqual(set(matches.keys()), set(range(1, 32)))

    @LIB_ACCURATERIP
    def test_match_offset(self):
        from audiotools.accuraterip import match_offset

        # no checksums, raise Exception
        self.assertRaises(ValueError,
                          match_offset,
                          [(1, 1, 0)],
                          [],
                          0)

        # no AR matches, one checksum, no checksum found
        (checksum,
         confidence,
         offset) = match_offset([], [1], 0)
        self.assertEqual(checksum, 1)
        self.assertEqual(confidence, None)
        self.assertEqual(offset, 0)

        # one AR match, one checksum, no checksum found in matches
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0)], [10], 0)
        self.assertEqual(checksum, 10)
        self.assertEqual(confidence, None)
        self.assertEqual(offset, 0)

        # one AR match, one checksum, one checksum found in matches
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0)], [1], 0)
        self.assertEqual(checksum, 1)
        self.assertEqual(confidence, 1)
        self.assertEqual(offset, 0)

        # one AR match, multiple checksums, no checksum found in matches
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0)], [2, 3, 4], -1)
        self.assertEqual(checksum, 3)
        self.assertEqual(confidence, None)
        self.assertEqual(offset, 0)

        # one AR match, multiple checksums, one checksum found in matches
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0)], [99, 0, 1], -1)
        self.assertEqual(checksum, 1)
        self.assertEqual(confidence, 1)
        self.assertEqual(offset, 1)

        # multiple AR matches, one checksum, no checksum found in matches
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0), (2, 2, 0)], [3], 0)
        self.assertEqual(checksum, 3)
        self.assertEqual(confidence, None)
        self.assertEqual(offset, 0)

        # multiple AR matches, one checksum, one checksum found in matches
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0), (2, 2, 0)], [2], 0)
        self.assertEqual(checksum, 2)
        self.assertEqual(confidence, 2)
        self.assertEqual(offset, 0)

        # multiple AR matches, multiple checksums, no checksums found
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0), (2, 2, 0)], [3, 4, 5], -1)
        self.assertEqual(checksum, 4)
        self.assertEqual(confidence, None)
        self.assertEqual(offset, 0)

        # multiple AR matches, multiple checksums, one match found
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0), (2, 2, 0)], [98, 99, 2], -1)
        self.assertEqual(checksum, 2)
        self.assertEqual(confidence, 2)
        self.assertEqual(offset, 1)

        # multiple AR matches, multiple checksums, multiple matches found
        (checksum,
         confidence,
         offset) = match_offset([(1, 1, 0), (2, 2, 0)], [0, 1, 2], -1)
        self.assertEqual(checksum, 2)
        self.assertEqual(confidence, 2)
        self.assertEqual(offset, 1)


class Test_Lookup(unittest.TestCase):
    @LIB_FREEDB
    @LIB_MUSICBRAINZ
    def test_metadata_lookup(self):
        from audiotools.freedb import DiscID as FDiscID
        from audiotools.musicbrainz import DiscID as MDiscID
        import time

        freedb_disc_id = FDiscID(
            offsets=[150, 2428, 9313, 10490, 28518, 46550, 48555, 61233,
                     65765, 67448, 79368, 95750, 97570, 107935, 110695,
                     133418, 134105, 142963, 155503, 156325, 176755,
                     191270, 192018, 204988, 207135, 215425, 216103,
                     235200, 236023, 251335, 252838],
            total_length=3482,
            track_count=31)
        musicbrainz_disc_id = MDiscID(
            first_track_number=1,
            last_track_number=31,
            lead_out_offset=261373,
            offsets=[150, 2428, 9313, 10490, 28518, 46550, 48555, 61233,
                     65765, 67448, 79368, 95750, 97570, 107935, 110695,
                     133418, 134105, 142963, 155503, 156325, 176755,
                     191270, 192018, 204988, 207135, 215425, 216103,
                     235200, 236023, 251335, 252838])
        total_tracks = 31

        self.assertEqual(str(freedb_disc_id),
                         "BE0D9A1F")
        self.assertEqual(str(musicbrainz_disc_id),
                         "yrelpXuXXP2WKDpTUqrS62keIFE-")

        # since the contents of lookup services
        # can change over time, all we can really verify
        # is the track count
        for choice in audiotools.metadata_lookup(
            musicbrainz_disc_id=musicbrainz_disc_id,
            freedb_disc_id=freedb_disc_id):
            self.assertEqual(len(choice), total_tracks)
        time.sleep(1)

    @LIB_FREEDB
    @LIB_MUSICBRAINZ
    def test_cddareader_lookup(self):
        from shutil import rmtree
        from audiotools.cdio import CDDAReader
        from audiotools.freedb import DiscID as FDiscID
        from audiotools.musicbrainz import DiscID as MDiscID
        import time

        dir = tempfile.mkdtemp()
        try:
            # dump cuesheet to file
            f = open(os.path.join(dir, "CDImage.cue"), "wb")
            f.write(open("freedb_test_discid-2.cue", "rb").read())
            f.close()

            # dump CD image to file
            f = open(os.path.join(dir, "CDImage.bin"), "wb")
            f.write(chr(0) * 2 * 2 * 153599124)
            f.close()

            r = CDDAReader(os.path.join(dir, "CDImage.cue"))

            freedb_disc_id = FDiscID.from_cddareader(r)
            musicbrainz_disc_id = MDiscID.from_cddareader(r)
            total_tracks = 31

            self.assertEqual(str(freedb_disc_id),
                             "BE0D9A1F")
            self.assertEqual(str(musicbrainz_disc_id),
                             "yrelpXuXXP2WKDpTUqrS62keIFE-")

            # since the contents of lookup services
            # can change over time, all we can really verify
            # is the track count
            for choice in audiotools.metadata_lookup(
                musicbrainz_disc_id=musicbrainz_disc_id,
                freedb_disc_id=freedb_disc_id):
                self.assertEqual(len(choice), total_tracks)
            time.sleep(1)
        finally:
            rmtree(dir)

    @LIB_FREEDB
    @LIB_MUSICBRAINZ
    def test_track_lookup(self):
        from audiotools.freedb import DiscID as FDiscID
        from audiotools.musicbrainz import DiscID as MDiscID
        import time

        lengths = [1339464, 4048380, 692076, 10600464, 10602816,
                   1178940, 7454664, 2664816, 989604, 7008960,
                   9632616, 1070160, 6094620, 1622880, 13361124,
                   403956, 5208504, 7373520, 483336, 12012840,
                   8534820, 439824, 7626360, 1262436, 4874520,
                   398664, 11229036, 483924, 9003456, 883764, 5018580]
        tempfiles = [tempfile.NamedTemporaryFile(suffix=".flac")
                     for l in lengths]

        tracks = [audiotools.FlacAudio.from_pcm(
                  t.name,
                  EXACT_SILENCE_PCM_Reader(pcm_frames=l,
                                           sample_rate=44100,
                                           channels=2,
                                           channel_mask=0x3,
                                           bits_per_sample=16),
                  total_pcm_frames=l)
                  for (t, l) in zip(tempfiles, lengths)]

        freedb_disc_id = FDiscID.from_tracks(tracks)
        musicbrainz_disc_id = MDiscID.from_tracks(tracks)
        total_tracks = 31

        self.assertEqual(str(freedb_disc_id),
                         "BE0D9A1F")
        self.assertEqual(str(musicbrainz_disc_id),
                         "yrelpXuXXP2WKDpTUqrS62keIFE-")

        # since the contents of lookup services
        # can change over time, all we can really verify
        # is the track count
        for choice in audiotools.metadata_lookup(
            musicbrainz_disc_id=musicbrainz_disc_id,
            freedb_disc_id=freedb_disc_id):
            self.assertEqual(len(choice), total_tracks)
        time.sleep(1)

        for t in tempfiles:
            t.close()

    @LIB_FREEDB
    @LIB_MUSICBRAINZ
    def test_sheet_lookup(self):
        from audiotools.freedb import DiscID as FDiscID
        from audiotools.musicbrainz import DiscID as MDiscID
        import time

        cuesheet = tempfile.NamedTemporaryFile(suffix=".cue")
        cuesheet.write(open("freedb_test_discid-2.cue", "rb").read())
        cuesheet.flush()
        sheet = audiotools.read_sheet(cuesheet.name)
        cuesheet.close()

        freedb_disc_id = FDiscID.from_sheet(sheet, 153599124, 44100)
        musicbrainz_disc_id = MDiscID.from_sheet(sheet, 153599124, 44100)
        total_tracks = 31

        self.assertEqual(str(freedb_disc_id),
                         "BE0D9A1F")
        self.assertEqual(str(musicbrainz_disc_id),
                         "yrelpXuXXP2WKDpTUqrS62keIFE-")

        # since the contents of lookup services
        # can change over time, all we can really verify
        # is the track count
        for choice in audiotools.metadata_lookup(
            musicbrainz_disc_id=musicbrainz_disc_id,
            freedb_disc_id=freedb_disc_id):
            self.assertEqual(len(choice), total_tracks)
        time.sleep(1)


class Test_Ogg(unittest.TestCase):
    @LIB_OGG
    def test_roundtrip(self):
        import audiotools.ogg

        for packet_len in range(0, 1000):
            packet = os.urandom(packet_len)
            ogg_stream = BytesIO()
            self.assertEqual(packet_len, len(packet))

            ogg_writer = audiotools.ogg.PageWriter(ogg_stream)
            for page in audiotools.ogg.packet_to_pages(packet, 1234):
                ogg_writer.write(page)
            ogg_writer.flush()

            ogg_stream.seek(0)

            ogg_reader = audiotools.ogg.PacketReader(
                audiotools.ogg.PageReader(ogg_stream))

            self.assertEqual(packet, ogg_reader.read_packet())

            ogg_writer.close()
            ogg_reader.close()


class Test_Image(unittest.TestCase):
    @LIB_IMAGE
    def test_metrics(self):
        from audiotools.image import image_metrics

        with open("image_test_metrics-1.jpg", "rb") as f:
            jpeg = image_metrics(f.read())
            self.assertEqual(jpeg.width, 3)
            self.assertEqual(jpeg.height, 2)
            self.assertEqual(jpeg.bits_per_pixel, 24)
            self.assertEqual(jpeg.color_count, 0)
            self.assertEqual(jpeg.mime_type, "image/jpeg")

        with open("image_test_metrics-2.png", "rb") as f:
            png1 = image_metrics(f.read())
            self.assertEqual(png1.width, 3)
            self.assertEqual(png1.height, 2)
            self.assertEqual(png1.bits_per_pixel, 24)
            self.assertEqual(png1.color_count, 0)
            self.assertEqual(png1.mime_type, "image/png")

        with open("image_test_metrics-3.png", "rb") as f:
            png2 = image_metrics(f.read())
            self.assertEqual(png2.width, 3)
            self.assertEqual(png2.height, 2)
            self.assertEqual(png2.bits_per_pixel, 8)
            self.assertEqual(png2.color_count, 1)
            self.assertEqual(png2.mime_type, "image/png")

        with open("image_test_metrics-4.gif", "rb") as f:
            gif = image_metrics(f.read())
            self.assertEqual(gif.width, 3)
            self.assertEqual(gif.height, 2)
            self.assertEqual(gif.bits_per_pixel, 8)
            self.assertEqual(gif.color_count, 2)
            self.assertEqual(gif.mime_type, "image/gif")

        with open("image_test_metrics-5.bmp", "rb") as f:
            bmp = image_metrics(f.read())
            self.assertEqual(bmp.width, 3)
            self.assertEqual(bmp.height, 2)
            self.assertEqual(bmp.bits_per_pixel, 24)
            self.assertEqual(bmp.color_count, 0)
            self.assertEqual(bmp.mime_type, "image/x-ms-bmp")

        with open("image_test_metrics-6.tiff", "rb") as f:
            tiff = image_metrics(f.read())
            self.assertEqual(tiff.width, 3)
            self.assertEqual(tiff.height, 2)
            self.assertEqual(tiff.bits_per_pixel, 24)
            self.assertEqual(tiff.color_count, 0)
            self.assertEqual(tiff.mime_type, "image/tiff")


class Test_ExecProgressQueue(unittest.TestCase):
    @LIB_CORE
    def test_queue(self):
        def range_sum(start, end, progress):
            import time

            sum_ = 0
            for i in range(start, end):
                progress(start, end)
                sum_ += i
                time.sleep(0.1)
            return sum_

        def range_sum_output(total):
            return u"%d" % (total)

        for max_processes in range(1, 21):
            queue = audiotools.ExecProgressQueue(audiotools.SilentMessenger())

            for i in range(100):
                queue.execute(
                    function=range_sum,
                    progress_text=u"Sum %d" % (i + 1),
                    completion_output=((u"Sum %d Finished" % (i + 1))
                                       if (i % 2) else range_sum_output),
                    start=i,
                    end=i + 10)

            results = queue.run(100)

            for i in range(max_processes):
                self.assertEqual(results[i], sum(range(i, i + 10)))


class Test_Output_Text(unittest.TestCase):
    @LIB_CORE
    def test_output_text(self):
        from audiotools import output_text

        # ensure invalid colors and styles raise an exception
        self.assertRaises(ValueError,
                          output_text,
                          unicode_string=u"Foo",
                          fg_color="unknown")

        self.assertRaises(ValueError,
                          output_text,
                          unicode_string=u"Foo",
                          bg_color="unknown")

        self.assertRaises(ValueError,
                          output_text,
                          unicode_string=u"Foo",
                          style="unknown")

        # ensure setting format returns new output_text with that format
        t1 = output_text(unicode_string=u"Foo")
        self.assertEqual(u"%s" % (t1,), u"Foo")
        self.assertEqual(t1.format(False), u"Foo")
        self.assertIn(u"Foo", t1.format(True))
        self.assertEqual(t1.fg_color(), None)
        self.assertEqual(t1.fg_color(), None)
        self.assertEqual(t1.style(), None)

        t2 = t1.set_format(fg_color="black",
                           bg_color="blue",
                           style="underline")
        self.assertEqual(u"%s" % (t2,), u"Foo")
        self.assertEqual(t2.format(False), u"Foo")
        self.assertIn(u"Foo", t2.format(True))
        self.assertEqual(t2.fg_color(), "black")
        self.assertEqual(t2.bg_color(), "blue")
        self.assertEqual(t2.style(), "underline")

        t3 = t2.set_format(fg_color=None,
                           bg_color=None,
                           style=None)
        self.assertEqual(u"%s" % (t3,), u"Foo")
        self.assertEqual(t3.format(False), u"Foo")
        self.assertIn(u"Foo", t3.format(True))
        self.assertEqual(t3.fg_color(), None)
        self.assertEqual(t3.fg_color(), None)
        self.assertEqual(t3.style(), None)

        # ensure negative head, tail and split values raise ValueError
        self.assertRaises(ValueError,
                          t1.head,
                          -1)

        self.assertRaises(ValueError,
                          t1.tail,
                          -1)

        self.assertRaises(ValueError,
                          t1.split,
                          -1)

        for string in [u"a",
                       u"Foo",
                       u"a" * 100,
                       u'\u1107' * 50,
                       u"a" + (u'\u1107' * 50),
                       u"a" + (u'\u1107' * 50) + u"b"]:
            for (fg_color,
                 bg_color,
                 style) in Possibilities([None, "black"],
                                         [None, "blue"],
                                         [None, "underline"]):

                t = output_text(unicode_string=string,
                                fg_color=fg_color,
                                bg_color=bg_color,
                                style=style)

                # ensure calling head returns a new output_text
                # with no more than "display_characters" and
                # with the same formatting as the original
                for i in range(len(t) + 5):
                    t2 = t.head(i)
                    self.assertLessEqual(len(t2), i)
                    self.assertEqual(t2.fg_color(), fg_color)
                    self.assertEqual(t2.bg_color(), bg_color)
                    self.assertEqual(t2.style(), style)

                # ensure calling tail returns a new output_text
                # with no more than "display_characters" and
                # with the same formatting as the original
                for i in range(len(t) + 5):
                    t2 = t.tail(i)
                    self.assertLessEqual(len(t2), i)
                    self.assertEqual(t2.fg_color(), fg_color)
                    self.assertEqual(t2.bg_color(), bg_color)
                    self.assertEqual(t2.style(), style)

                # ensure calling split returns a tuple of new output_text
                # with no more than "display_characters" in the head
                # and with the same formatting as the original
                for i in range(len(t) + 5):
                    (t2, t3) = t.split(i)
                    self.assertLessEqual(len(t2), i)
                    self.assertEqual(len(t2) + len(t3), len(t))
                    self.assertEqual(t2.fg_color(), fg_color)
                    self.assertEqual(t2.bg_color(), bg_color)
                    self.assertEqual(t2.style(), style)
                    self.assertEqual(t3.fg_color(), fg_color)
                    self.assertEqual(t3.bg_color(), bg_color)
                    self.assertEqual(t3.style(), style)

    @LIB_CORE
    def test_output_list(self):
        from audiotools import output_text, output_list

        # ensure invalid colors and styles raise an exception
        self.assertRaises(ValueError,
                          output_list,
                          output_texts=[u"Foo", u"Bar"],
                          fg_color="unknown")

        self.assertRaises(ValueError,
                          output_list,
                          output_texts=[u"Foo", u"Bar"],
                          bg_color="unknown")

        self.assertRaises(ValueError,
                          output_list,
                          output_texts=[u"Foo", u"Bar"],
                          style="unknown")

        # ensure setting format returns new output_list with that format
        t1 = output_list(output_texts=[u"Foo", output_text(u"Bar")])
        self.assertEqual(u"%s" % (t1,), u"FooBar")
        self.assertEqual(t1.format(False), u"FooBar")
        self.assertIn(u"FooBar", t1.format(True))
        self.assertEqual(t1.fg_color(), None)
        self.assertEqual(t1.fg_color(), None)
        self.assertEqual(t1.style(), None)

        t2 = t1.set_format(fg_color="black",
                           bg_color="blue",
                           style="underline")
        self.assertEqual(u"%s" % (t2,), u"FooBar")
        self.assertEqual(t2.format(False), u"FooBar")
        self.assertIn(u"FooBar", t2.format(True))
        self.assertEqual(t2.fg_color(), "black")
        self.assertEqual(t2.bg_color(), "blue")
        self.assertEqual(t2.style(), "underline")

        t3 = t2.set_format(fg_color=None,
                           bg_color=None,
                           style=None)
        self.assertEqual(u"%s" % (t3,), u"FooBar")
        self.assertEqual(t3.format(False), u"FooBar")
        self.assertIn(u"FooBar", t3.format(True))
        self.assertEqual(t3.fg_color(), None)
        self.assertEqual(t3.fg_color(), None)
        self.assertEqual(t3.style(), None)

        # ensure negative head, tail and split values raise ValueError
        self.assertRaises(ValueError,
                          t1.head,
                          -1)

        self.assertRaises(ValueError,
                          t1.tail,
                          -1)

        self.assertRaises(ValueError,
                          t1.split,
                          -1)

        for strings in [[u"a"],
                        [output_text(u"a",
                                     fg_color="white",
                                     bg_color="blue",
                                     style="underline")],
                        [u"Foo"],
                        [u"a" * 100],
                        [output_text(u"Foo")],
                        [u"Foo", output_text(u"Bar")],
                        [output_text(u'\u1107' * 10)],
                        [u"a", output_text(u'\u1107' * 20,
                                           fg_color="white",
                                           bg_color="blue",
                                           style="underline"), u"b"]]:
            for (fg_color,
                 bg_color,
                 style) in Possibilities([None, "black"],
                                         [None, "blue"],
                                         [None, "underline"]):

                t = output_list(output_texts=strings,
                                fg_color=fg_color,
                                bg_color=bg_color,
                                style=style)

                # ensure calling head returns a new output_list
                # with no more than "display_characters" and
                # with the same formatting as the original
                for i in range(len(t) + 5):
                    t2 = t.head(i)
                    self.assertLessEqual(len(t2), i)
                    self.assertEqual(t2.fg_color(), fg_color)
                    self.assertEqual(t2.bg_color(), bg_color)
                    self.assertEqual(t2.style(), style)

                # ensure calling tail returns a new output_list
                # with no more than "display_characters" and
                # with the same formatting as the original
                for i in range(len(t) + 5):
                    t2 = t.tail(i)
                    self.assertLessEqual(len(t2), i)
                    self.assertEqual(t2.fg_color(), fg_color)
                    self.assertEqual(t2.bg_color(), bg_color)
                    self.assertEqual(t2.style(), style)

                # ensure calling split returns a tuple of new output_list
                # with no more than "display_characters" in the head
                # and with the same formatting as the original
                for i in range(len(t) + 5):
                    (t2, t3) = t.split(i)
                    self.assertLessEqual(len(t2), i)
                    self.assertEqual(len(t2) + len(t3), len(t))
                    self.assertEqual(t2.fg_color(), fg_color)
                    self.assertEqual(t2.bg_color(), bg_color)
                    self.assertEqual(t2.style(), style)
                    self.assertEqual(t3.fg_color(), fg_color)
                    self.assertEqual(t3.bg_color(), bg_color)
                    self.assertEqual(t3.style(), style)

    @LIB_CORE
    def test_output_table(self):
        from audiotools import output_table, output_text, output_list

        # check a table with mismatched columns
        err = output_table()
        row1 = err.row()
        row1.add_column(u"Foo")
        self.assertEqual(len(list(err.format(False))), 1)
        self.assertEqual(len(list(err.format(True))), 1)
        row2 = err.row()
        row2.add_column(u"Foo")
        row2.add_column(u"Bar")
        self.assertRaises(ValueError,
                          list,
                          err.format(False))
        self.assertRaises(ValueError,
                          list,
                          err.format(True))

        # check a table with nothing but dividers
        dividers = output_table()
        dividers.divider_row([u"-", u"-"])
        dividers.divider_row([u"*", u"*"])
        dividers.divider_row([u"x", u"x"])
        self.assertEqual(len(list(dividers.format(False))), 3)
        self.assertEqual(len(list(dividers.format(True))), 3)
        dividers.divider_row([u"_"])
        self.assertRaises(ValueError,
                          list,
                          dividers.format(False))
        self.assertRaises(ValueError,
                          list,
                          dividers.format(True))

        # check a table with nothing but blank rows
        blanks = output_table()
        blanks.blank_row()
        blanks.blank_row()
        blanks.blank_row()
        blanks.blank_row()
        self.assertEqual(len(list(blanks.format(False))), 4)
        self.assertEqual(len(list(blanks.format(True))), 4)

        # check a typical table with black rows and dividers
        table = output_table()

        row1 = table.blank_row()
        row2 = table.divider_row([u"-",u"-", u"-"])
        row3 = table.row()
        row3.add_column(u"a", "left")
        row3.add_column(u"b", "center")
        row3.add_column(u"c", "right")
        self.assertRaises(ValueError,
                          row3.add_column,
                          u"d", "unknown")

        row4 = table.row()
        row4.add_column(output_text(u"Foo",
                                    fg_color="black",
                                    bg_color="white"))
        row4.add_column(output_list([u"Bar", u'\u1107' * 5],
                                    fg_color="blue",
                                    bg_color="red"), "center")
        row4.add_column(output_text(u"Blah"), "right")

        row5 = table.divider_row([u"-",u"-", u"-"])
        row6 = table.blank_row()

        self.assertEqual(len(list(table.format(False))), 6)
        self.assertEqual(len(list(table.format(True))), 6)


class Test_Most_Numerous(unittest.TestCase):
    @LIB_CORE
    def test_most_numerous(self):
        from audiotools import most_numerous

        self.assertEqual(most_numerous([1, 1, 2, 3]), 1)
        self.assertEqual(most_numerous([1, 2, 2, 3]), 2)
        self.assertEqual(most_numerous([1, 2, 3, 3]), 3)
        self.assertEqual(most_numerous([], empty_list=-1), -1)
        self.assertEqual(most_numerous([1, 2, 3],
                                       empty_list=-1,
                                       all_differ=-2), -2)


class Test_Test_Iter(unittest.TestCase):
    @LIB_CORE
    def test_iter(self):
        from audiotools import iter_first, iter_last

        self.assertEqual(list(iter_first([])),
                         [])
        self.assertEqual(list(iter_first([1])),
                         [(True, 1)])
        self.assertEqual(list(iter_first([1, 2])),
                         [(True, 1), (False, 2)])
        self.assertEqual(list(iter_first([1, 2, 3])),
                         [(True, 1), (False, 2), (False, 3)])

        self.assertEqual(list(iter_last([])),
                         [])
        self.assertEqual(list(iter_last([1])),
                         [(True, 1)])
        self.assertEqual(list(iter_last([1, 2])),
                         [(False, 1), (True, 2)])
        self.assertEqual(list(iter_last([1, 2, 3])),
                         [(False, 1), (False, 2), (True, 3)])
