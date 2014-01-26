#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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
                  RANDOM_PCM_Reader, EXACT_SILENCE_PCM_Reader,
                  EXACT_BLANK_PCM_Reader, SHORT_PCM_COMBINATIONS,
                  MD5_Reader, FrameCounter,
                  MiniFrameReader, Combinations, Possibilities,
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


class PCMReader(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        #try reading lots of bps/signed/endianness combinations
        for bps in [8, 16, 24]:
            for big_endian in [True, False]:
                for signed in [True, False]:
                    reader = audiotools.PCMReader(
                        cStringIO.StringIO(
                            from_list(range(-5, 5),
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

                    #ensure the FrameList is read correctly
                    f = reader.read((bps / 8) * 10)
                    self.assertEqual(len(f), 10)
                    self.assertEqual(list(f), range(-5, 5))

                    #ensure subsequent reads return empty FrameLists
                    for i in xrange(10):
                        f = reader.read((bps / 8) * 10)
                        self.assertEqual(len(f), 0)

                    #ensure closing the stream raises ValueErrors
                    #on subsequent reads
                    reader.close()

                    self.assertRaises(ValueError, reader.read, (bps / 8) * 10)


class PCMCat(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        #ensure mismatched streams raise ValueError at init time
        audiotools.PCMCat([audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=44100,
                                                channels=1,
                                                channel_mask=0x4,
                                                bits_per_sample=16)])

        self.assertRaises(ValueError,
                          audiotools.PCMCat,
                          [audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=96000,
                                                channels=1,
                                                channel_mask=0x4,
                                                bits_per_sample=16),
                           audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=44100,
                                                channels=1,
                                                channel_mask=0x4,
                                                bits_per_sample=16)])

        self.assertRaises(ValueError,
                          audiotools.PCMCat,
                          [audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=44100,
                                                channels=2,
                                                channel_mask=0x3,
                                                bits_per_sample=16),
                           audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=44100,
                                                channels=1,
                                                channel_mask=0x4,
                                                bits_per_sample=16)])

        self.assertRaises(ValueError,
                          audiotools.PCMCat,
                          [audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=44100,
                                                channels=1,
                                                channel_mask=0x4,
                                                bits_per_sample=24),
                           audiotools.PCMReader(cStringIO.StringIO(""),
                                                sample_rate=44100,
                                                channels=1,
                                                channel_mask=0x4,
                                                bits_per_sample=16)])

        main_readers = [audiotools.PCMReader(
                cStringIO.StringIO(
                    from_list(samples, 1, 16, True).to_bytes(True,
                                                             True)),
                sample_rate=44100,
                channels=1,
                channel_mask=0x4,
                bits_per_sample=16,
                signed=True,
                big_endian=True)
                        for samples in [range(-15, -5),
                                        range(-5, 5),
                                        range(5, 15)]]

        reader = audiotools.PCMCat(main_readers)

        #ensure PCMCat's stream attributes match first reader's
        self.assertEqual(reader.sample_rate, 44100)
        self.assertEqual(reader.channels, 1)
        self.assertEqual(reader.channel_mask, 0x4)
        self.assertEqual(reader.bits_per_sample, 16)

        #ensure all the substreams are read correctly
        samples = []
        f = reader.read(2)
        while (len(f) > 0):
            samples.extend(list(f))
            f = reader.read(2)

        self.assertEqual(samples, range(-15, 15))

        #ensure subsequent reads return empty FrameLists
        for i in xrange(10):
            self.assertEqual(len(reader.read(2)), 0)

        #main readers should not yet be closed
        for r in main_readers:
            for i in xrange(10):
                self.assertEqual(len(r.read(2)), 0)

        #ensure closing the stream raises ValueErrors
        #on subsequent reads
        reader.close()

        self.assertRaises(ValueError, reader.read, 2)

        #sub readers should also be closed by PCMCat's close()
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

        #ensure our reader is generating randomly-sized frames
        reader = Variable_Reader(EXACT_BLANK_PCM_Reader(4096 * 100))
        self.assert_(len(set(frame_lengths(reader, 4096))) > 1)

        #then, ensure that wrapped our reader in a BufferedPCMReader
        #results in equal-sized frames
        reader = audiotools.BufferedPCMReader(
            Variable_Reader(EXACT_BLANK_PCM_Reader(4096 * 100)))
        #(make sure to account for bps/channels in frame_lengths())
        self.assertEqual(set(frame_lengths(reader, 4096)), set([4096]))

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

        #ensure that random-sized reads also work okay
        total_frames = 4096 * 1000
        reader = audiotools.BufferedPCMReader(
            Variable_Reader(EXACT_BLANK_PCM_Reader(total_frames)))
        while (total_frames > 0):
            frames = min(total_frames, random.choice(range(1, 1000)))
            frame = reader.read(frames)
            self.assertEqual(frame.frames, frames)
            total_frames -= frame.frames

        #ensure reading after the stream has been exhausted
        #results in empty FrameLists
        reader = audiotools.BufferedPCMReader(
            EXACT_BLANK_PCM_Reader(44100))
        f = reader.read(4096)
        while (len(f) > 0):
            f = reader.read(4096)

        self.assertEqual(len(f), 0)

        for i in xrange(10):
            f = reader.read(4096)
            self.assertEqual(len(f), 0)

        #and ensure reading after the stream is closed
        #raises a ValueError
        reader.close()

        self.assertRaises(ValueError,
                          reader.read,
                          4096)


class LimitedPCMReader(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        main_reader = audiotools.PCMReader(
            cStringIO.StringIO(
                from_list(range(-50, 50), 1, 16, True).to_bytes(True, True)),
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

            #ensure subsequent reads return empty FrameLists
            for i in xrange(10):
                self.assertEqual(len(reader.read(2)), 0)

            #ensure closing the substream raises ValueErrors
            #on subsequent reads
            #(note that this doesn't close the main reader)
            reader.close()

            self.assertRaises(ValueError, reader.read, 2)

        self.assertEqual(total_samples, range(-50, 50))

        #ensure subsequent reads of main reader return empty FrameLists
        for i in xrange(10):
            self.assertEqual(len(main_reader.read(2)), 0)

        #ensure closing the substream raises ValueErrors
        #on subsequent reads
        main_reader.close()

        self.assertRaises(ValueError, main_reader.read, 2)


class PCMReaderWindow(unittest.TestCase):
    @LIB_PCM
    def test_pcm(self):
        from audiotools.pcm import from_list

        for initial_offset in range(-5, 5):
            for pcm_frames in range(5, 15):
                main_reader = audiotools.PCMReader(
                    cStringIO.StringIO(
                        from_list(range(1, 11),
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

                #ensure reads generate the proper window of samples
                samples = []
                f = reader.read(2)
                while (len(f) > 0):
                    samples.extend(list(f))
                    f = reader.read(2)

                self.assertEqual(len(samples), pcm_frames)

                target_samples = range(1, 11)
                if (initial_offset < 0):
                    #negative offsets pad window with 0s
                    target_samples = (([0] * abs(initial_offset)) +
                                      target_samples)
                elif (initial_offset > 0):
                    #positive offsets remove samples from window
                    target_samples = target_samples[initial_offset:]

                if (len(target_samples) < pcm_frames):
                    #window longer than samples gets padded with 0s
                    target_samples += [0] * (pcm_frames - len(target_samples))
                elif (len(target_samples) > pcm_frames):
                    #window shorder than samples truncates samples
                    target_samples = target_samples[0:pcm_frames]

                self.assertEqual(samples, target_samples)

                #ensure subsequent reads return empty FrameLists
                for i in xrange(10):
                    self.assertEqual(len(reader.read(2)), 0)

                #ensure closing the PCMReaderWindow
                #generates ValueErrors on subsequent reads
                reader.close()

                self.assertRaises(ValueError, reader.read, 2)

                #ensure closing the PCMReaderWindow
                #closes the main PCMReader also
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

            #read the base data from the stream
            f = stream.read(4096)
            while (len(f) > 0):
                f = stream.read(4096)

            #ensure subsequent reads return empty FrameLists
            for i in xrange(10):
                self.assertEqual(len(stream.read(4096)), 0)

            #ensure subsequent reads on a closed stream
            #raises ValueError
            stream.close()

            self.assertRaises(ValueError, stream.read, 4096)


class CDDA(unittest.TestCase):
    @LIB_CORE
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bin = os.path.join(self.temp_dir, "Test.BIN")
        self.cue = os.path.join(self.temp_dir, "Test.CUE")

        bin_file = open(self.bin, "wb")
        self.reader = test_streams.Sine16_Stereo(69470436, 44100,
                                                 441.0, 0.50,
                                                 4410.0, 0.49, 1.0)
        audiotools.transfer_framelist_data(self.reader, bin_file.write)
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
        audiotools.transfer_framelist_data(audiotools.PCMCat(iter(cdda)),
                                           checksum.update)
        self.assertEqual(self.reader.hexdigest(),
                         checksum.hexdigest())

    @LIB_CORE
    def test_cdda_pcm(self):
        cdda = audiotools.CDDA(self.cue)

        for track in cdda:
            #ensure all track data reads correctly
            track_frames = track.length() * 588
            total_frames = 0
            f = track.read(4096)
            while (len(f) > 0):
                total_frames += f.frames
                f = track.read(4096)
            self.assertEqual(total_frames, track_frames)

            #ensure further reads return empty FrameLists
            for i in xrange(10):
                self.assertEqual(len(track.read(4096)), 0)

            #ensure closing the reader raises ValueErrors
            #on subsequent reads
            track.close()

            self.assertRaises(ValueError, track.read, 4096)

    @LIB_CORE
    def test_cdda_positive_offset(self):
        #offset values don't apply to CD images
        #so this test doesn't do much

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
                                       0,
                                       69470436),
            reader_checksum.update)
        self.assertEqual(reader_checksum.hexdigest(),
                         cdrom_checksum.hexdigest())

    @LIB_CORE
    def test_cdda_negative_offset(self):
        #offset values don't apply to CD images
        #so this test doesn't do much

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
                                       0,
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

        self.assert_(file1.disk_file())
        self.assert_(file2.disk_file())
        self.assertNotEqual(str(file1), str(file2))
        self.assertNotEqual(unicode(file1), unicode(file2))
        self.assertEqual(file1, file2)
        self.assertEqual(hash(file1), hash(file2))

        self.assert_(not file3.disk_file())
        self.assertNotEqual(str(file1), str(file3))
        self.assertNotEqual(unicode(file1), unicode(file3))
        self.assertNotEqual(file1, file3)
        self.assertNotEqual(hash(file1), hash(file3))

        self.assert_(not file4.disk_file())
        self.assertEqual(str(file3), str(file4))
        self.assertEqual(unicode(file3), unicode(file4))
        self.assertEqual(file3, file4)
        self.assertEqual(hash(file3), hash(file4))

        self.assert_(not file5.disk_file())
        self.assertNotEqual(str(file3), str(file5))
        self.assertNotEqual(unicode(file3), unicode(file5))
        self.assertNotEqual(file3, file5)
        self.assertNotEqual(hash(file3), hash(file5))

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

                #read contents of converted stream
                f = reader.read(4096)
                while (len(f) > 0):
                    f = reader.read(4096)

                #ensure subsequent reads return empty FrameLists
                for i in xrange(10):
                    self.assertEqual(len(reader.read(4096)), 0)

                #ensure closing stream raises ValueErrors
                #on subsequent reads
                reader.close()

                self.assertRaises(ValueError, reader.read, 4096)

                #ensure main reader is also closed
                #when converter is closed
                self.assertRaises(ValueError, main_reader.read, 4096)


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
        groupings.sort(lambda x, y: cmp(x[0].get_metadata().album_name,
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
        dummy1.write("Hello World")
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

        self.assert_(len(sorted_tracks) > 1)

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
        #tracks without metadata come before tracks with metadata
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

        #tracks without metadata are sorted by filename
        self.__clean__()
        self.__test_order__([self.__no_metadata__(1),
                             self.__no_metadata__(2),
                             self.__no_metadata__(3)])

        self.__clean__()
        self.__test_order__([self.__no_metadata__(1),
                             self.__no_metadata__(2),
                             self.__no_metadata__(10),
                             self.__no_metadata__(11)])

        #tracks without album numbers come before tracks with album numbers
        self.__clean__()
        self.__test_order__([self.__metadata__(3, 3),
                             self.__metadata__(2, 1, 1),
                             self.__metadata__(1, 2, 1)])

        self.__clean__()
        self.__test_order__([self.__metadata__(4, 3),
                             self.__metadata__(3, 4),
                             self.__metadata__(2, 1, 1),
                             self.__metadata__(1, 2, 1)])

        #tracks without album numbers are sorted by track number (if any)
        self.__clean__()
        self.__test_order__([self.__metadata__(3),
                             self.__metadata__(2, 1),
                             self.__metadata__(1, 2)])

        self.__clean__()
        self.__test_order__([self.__metadata__(3, 1),
                             self.__metadata__(2, 2),
                             self.__metadata__(1, 3)])

        #tracks with album numbers are sorted by album number
        #and then by track number (if any)
        self.__clean__()
        self.__test_order__([self.__metadata__(5),
                             self.__metadata__(4, 1, 1),
                             self.__metadata__(3, 2, 1),
                             self.__metadata__(2, 1, 2),
                             self.__metadata__(1, 2, 2)])


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
                    1, 8, 0, 1)))

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
        for bps in [0, 7, 9, 15, 17, 23, 25, 64]:
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
        self.assertRaises(IOError, reader.read_signed, 2)
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
        reader.rewind()
        self.assertRaises(ValueError, reader.read, -1)
        reader.rewind()
        self.assertRaises(ValueError, reader.read_signed, -1)
        reader.rewind()
        self.assertRaises(ValueError, reader.skip, -1)
        reader.rewind()
        self.assertRaises(ValueError, reader.read_bytes, -2)
        reader.rewind()
        self.assertRaises(IOError, reader.read_bytes, 2 ** 30)
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

        #test basic big-endian string
        self.assertEqual(parse("2u3u5u3s19s",
                               False,
                               "".join(map(chr, [0xB1, 0xED, 0x3B, 0xC1]))),
                         [2, 6, 7, -3, -181311])

        #test all the defined format fields
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
                                  ["\xB1\xED", "\x3B\xC1"]),
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
                                   "".join(map(chr, [0xB1, 0xED, 0x3B, 0xC1]))),
                             values)

        #test several big-endian unsigned edge cases
        self.assertEqual(
            parse("32u 32u 32u 32u 64U 64U 64U 64U",
                  False,
                  "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                                    128, 0, 0, 0, 127, 255, 255, 255,
                                    0, 0, 0, 0, 0, 0, 0, 0,
                                    255, 255, 255, 255, 255, 255, 255, 255,
                                    128, 0, 0, 0, 0, 0, 0, 0,
                                    127, 255, 255, 255, 255, 255, 255, 255]))),
            [0,
             4294967295,
             2147483648,
             2147483647,
             0,
             0xFFFFFFFFFFFFFFFFL,
             9223372036854775808L,
             9223372036854775807L])

        #test several big-endian signed edge cases
        self.assertEqual(
            parse("32s 32s 32s 32s 64S 64S 64S 64S",
                  False,
                  "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                                    128, 0, 0, 0, 127, 255, 255, 255,
                                    0, 0, 0, 0, 0, 0, 0, 0,
                                    255, 255, 255, 255, 255, 255, 255, 255,
                                    128, 0, 0, 0, 0, 0, 0, 0,
                                    127, 255, 255, 255, 255, 255, 255, 255]))),
            [0,
             -1,
             -2147483648,
             2147483647,
             0,
             -1,
             -9223372036854775808L,
             9223372036854775807L])

        #test big-endian read errors
        for s in ["3u", "3s", "3U", "3S", "3p", "3P", "3b"]:
            self.assertRaises(IOError,
                              parse,
                              "8u" + s,
                              False,
                              "a")

        #test basic little-endian string
        self.assertEqual(parse("2u3u5u3s19s",
                               True,
                               "".join(map(chr, [0xB1, 0xED, 0x3B, 0xC1]))),
                         [1, 4, 13, 3, -128545])

        #test all the defined format fields
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
                                  ["\xB1\xED", "\x3B\xC1"]),
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
                                   "".join(map(chr, [0xB1, 0xED, 0x3B, 0xC1]))),
                             values)


        #test several little-endian unsigned edge cases
        self.assertEqual(
            parse("32u 32u 32u 32u 64U 64U 64U 64U",
                  True,
                  "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                                    0, 0, 0, 128, 255, 255, 255, 127,
                                    0, 0, 0, 0, 0, 0, 0, 0,
                                    255, 255, 255, 255, 255, 255, 255, 255,
                                    0, 0, 0, 0, 0, 0, 0, 128,
                                    255, 255, 255, 255, 255, 255, 255, 127]))),
            [0,
             4294967295,
             2147483648,
             2147483647,
             0,
             0xFFFFFFFFFFFFFFFFL,
             9223372036854775808L,
             9223372036854775807L])

        #test several little-endian signed edge cases
        self.assertEqual(
            parse("32s 32s 32s 32s 64S 64S 64S 64S",
                  True,
                  "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                                    0, 0, 0, 128, 255, 255, 255, 127,
                                    0, 0, 0, 0, 0, 0, 0, 0,
                                    255, 255, 255, 255, 255, 255, 255, 255,
                                    0, 0, 0, 0, 0, 0, 0, 128,
                                    255, 255, 255, 255, 255, 255, 255, 127]))),
            [0,
             -1,
             -2147483648,
             2147483647,
             0,
             -1,
             -9223372036854775808L,
             9223372036854775807L])

        #test little-endian read errors
        for s in ["3u", "3s", "3U", "3S", "3p", "3P", "3b"]:
            self.assertRaises(IOError,
                              parse,
                              "8u" + s,
                              True,
                              "a")

    @LIB_BITSTREAM
    def test_build(self):
        from audiotools.bitstream import build

        #test basic big-endian string
        self.assertEqual(build("2u3u5u3s19s",
                               False,
                               [2, 6, 7, -3, -181311]),
                         "".join(map(chr, [0xB1, 0xED, 0x3B, 0xC1])))

        #test several big-endian unsigned edge cases
        self.assertEqual(
            build("32u 32u 32u 32u 64U 64U 64U 64U",
                  False,
                  [0,
                   4294967295,
                   2147483648,
                   2147483647,
                   0,
                   0xFFFFFFFFFFFFFFFFL,
                   9223372036854775808L,
                   9223372036854775807L]),
            "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                              128, 0, 0, 0, 127, 255, 255, 255,
                              0, 0, 0, 0, 0, 0, 0, 0,
                              255, 255, 255, 255, 255, 255, 255, 255,
                              128, 0, 0, 0, 0, 0, 0, 0,
                              127, 255, 255, 255, 255, 255, 255, 255])))

        #test several big-endian signed edge cases
        self.assertEqual(
            build("32s 32s 32s 32s 64S 64S 64S 64S",
                  False,
                  [0,
                   -1,
                   -2147483648,
                   2147483647,
                   0,
                   -1,
                   -9223372036854775808L,
                   9223372036854775807L]),
            "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                              128, 0, 0, 0, 127, 255, 255, 255,
                              0, 0, 0, 0, 0, 0, 0, 0,
                              255, 255, 255, 255, 255, 255, 255, 255,
                              128, 0, 0, 0, 0, 0, 0, 0,
                              127, 255, 255, 255, 255, 255, 255, 255])))

        #test big-endian write errors
        for l in [[2, 6, 7, -3], [2, 6, 7], [2, 6], [2], []]:
            self.assertRaises(IndexError,
                              build,
                              "2u3u5u3s19s",
                              False,
                              l)

        #test basic little-endian string
        self.assertEqual(build("2u3u5u3s19s",
                               True,
                               [1, 4, 13, 3, -128545]),
                         "".join(map(chr, [0xB1, 0xED, 0x3B, 0xC1])))

        #test several little-endian unsigned edge cases
        self.assertEqual(
            build("32u 32u 32u 32u 64U 64U 64U 64U",
                  True,
                  [0,
                   4294967295,
                   2147483648,
                   2147483647,
                   0,
                   0xFFFFFFFFFFFFFFFFL,
                   9223372036854775808L,
                   9223372036854775807L]),
            "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                              0, 0, 0, 128, 255, 255, 255, 127,
                              0, 0, 0, 0, 0, 0, 0, 0,
                              255, 255, 255, 255, 255, 255, 255, 255,
                              0, 0, 0, 0, 0, 0, 0, 128,
                              255, 255, 255, 255, 255, 255, 255, 127])))

        #test several little-endian signed edge cases
        self.assertEqual(
            build("32s 32s 32s 32s 64S 64S 64S 64S",
                  True,
                  [0,
                   -1,
                   -2147483648,
                   2147483647,
                   0,
                   -1,
                   -9223372036854775808L,
                   9223372036854775807L]),
            "".join(map(chr, [0, 0, 0, 0, 255, 255, 255, 255,
                              0, 0, 0, 128, 255, 255, 255, 127,
                              0, 0, 0, 0, 0, 0, 0, 0,
                              255, 255, 255, 255, 255, 255, 255, 255,
                              0, 0, 0, 0, 0, 0, 0, 128,
                              255, 255, 255, 255, 255, 255, 255, 127])))

        #test little-endian write errors
        for l in [[1, 4, 13, 3], [1, 4, 13], [1, 4], [1], []]:
            self.assertRaises(IndexError,
                              build,
                              "2u3u5u3s19s",
                              True,
                              l)

    @LIB_BITSTREAM
    def test_build_parse_roundtrip(self):
        from audiotools.bitstream import build,parse

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
                                        ("64U",    [0xFFFFFFFFFFFFFFFFL]),
                                        ("64S",    [-9223372036854775808L]),
                                        ("10b",    [chr(0) * 10]),
                                        ("10p10b a", [chr(1) * 10]),
                                        ("10P10b", [chr(2) * 10])]:
            self.assertEqual(parse(format_string, False,
                                   build(format_string, False, values)),
                             values)
            self.assertEqual(parse(format_string, True,
                                   build(format_string, True, values)),
                             values)

    @LIB_BITSTREAM
    def test_simple_reader(self):
        from audiotools.bitstream import BitstreamReader, HuffmanTree

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
        self.assertEqual(reader.read(64), 0)
        self.assertEqual(reader.read(64), 0xFFFFFFFFFFFFFFFFL)
        self.assertEqual(reader.read(64), 9223372036854775808L)
        self.assertEqual(reader.read(64), 9223372036854775807L)

        #try the signed 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read_signed(32), 0)
        self.assertEqual(reader.read_signed(32), -1)
        self.assertEqual(reader.read_signed(32), -2147483648)
        self.assertEqual(reader.read_signed(32), 2147483647)
        self.assertEqual(reader.read_signed(64), 0)
        self.assertEqual(reader.read_signed(64), -1)
        self.assertEqual(reader.read_signed(64), -9223372036854775808L)
        self.assertEqual(reader.read_signed(64), 9223372036854775807L)

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
        self.assertEqual(reader.read(64), 0)
        self.assertEqual(reader.read(64), 0xFFFFFFFFFFFFFFFFL)
        self.assertEqual(reader.read(64), 9223372036854775808L)
        self.assertEqual(reader.read(64), 9223372036854775807L)

        #try the signed 32 and 64 bit values
        reader.rewind()
        self.assertEqual(reader.read_signed(32), 0)
        self.assertEqual(reader.read_signed(32), -1)
        self.assertEqual(reader.read_signed(32), -2147483648)
        self.assertEqual(reader.read_signed(32), 2147483647)
        self.assertEqual(reader.read_signed(64), 0)
        self.assertEqual(reader.read_signed(64), -1)
        self.assertEqual(reader.read_signed(64), -9223372036854775808L)
        self.assertEqual(reader.read_signed(64), 9223372036854775807L)

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
        writer.write(64, 0)
        writer.write(64, 0xFFFFFFFFFFFFFFFFL)
        writer.write(64, 9223372036854775808L)
        writer.write(64, 9223372036854775807L)
        validate_writer(writer, temp)

        #try the signed 32 and 64 bit values
        (writer, temp) = get_writer()
        writer.write_signed(32, 0)
        writer.write_signed(32, -1)
        writer.write_signed(32, -2147483648)
        writer.write_signed(32, 2147483647)
        writer.write_signed(64, 0)
        writer.write_signed(64, -1)
        writer.write_signed(64, -9223372036854775808L)
        writer.write_signed(64, 9223372036854775807L)
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
        writer.build("32u 32u 32u 32u 64u 64u 64u 64u",
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
        writer.build("32s 32s 32s 32s 64s 64s 64s 64s",
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
                  self.__writer_perform_write_unary_0__,
                  self.__writer_perform_write_unary_1__,
                  self.__writer_perform_write_huffman__]

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
        self.assertEqual(open(temp_file.name, "rb").read(), "\xB1\xED\x3B\xC1")

    @LIB_BITSTREAM
    def test_write_errors(self):
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        for little_endian in [False, True]:
            for writer in [BitstreamWriter(cStringIO.StringIO(),
                                           little_endian),
                           BitstreamRecorder(little_endian),
                           BitstreamAccumulator(little_endian)]:
                #writing negative number of bits shouldn't work
                self.assertRaises(ValueError,
                                  writer.write,
                                  -1, 0)

                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  -1, 0)

                #writing negative value as unsigned shouldn't work
                self.assertRaises(ValueError,
                                  writer.write,
                                  8, -1)

                #write unsigneed value that's too large shouldn't work
                self.assertRaises(ValueError,
                                  writer.write,
                                  8, 2 ** 8)

                #nor should it work from the .build method
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8u", [-1])
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8u", [2 ** 8])

                #writing negative value that's too small shouldn't work
                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  8, -(2 ** 8))

                #writing signed value that's too large shouldn't work
                self.assertRaises(ValueError,
                                  writer.write_signed,
                                  8, 2 ** 8)

                #nor should it work from the .build method
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8s", [-(2 ** 8)])
                self.assertRaises(ValueError,
                                  writer.build,
                                  "8s", [2 ** 8])

                #writing some value that's not a number shouldn't work
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

                #writing unary with non 0/1 bit shouldn't work
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

    @LIB_BITSTREAM
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

    @LIB_BITSTREAM
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

    @LIB_BITSTREAM
    def test_reader_close(self):
        from audiotools.bitstream import BitstreamReader, HuffmanTree

        def test_reader(reader):
            self.assertRaises(IOError, reader.read, 1)
            self.assertRaises(IOError, reader.skip, 3)
            self.assertRaises(IOError, reader.skip_bytes, 1)
            self.assertRaises(IOError, reader.read_signed, 2)
            self.assertRaises(IOError, reader.unary, 1)
            self.assertRaises(IOError, reader.limited_unary, 1, 2)
            self.assertRaises(IOError, reader.read_bytes, 1)
            self.assertRaises(IOError, reader.parse, "1b2b3b")
            self.assertRaises(IOError, reader.substream, 2)
            self.assertRaises(IOError, reader.read_huffman_code,
                              HuffmanTree([(1, ),     1,
                                           (0, 1),    2,
                                           (0, 0, 1), 3,
                                           (0, 0, 0), 4], False))

        def new_temp():
            temp = cStringIO.StringIO()
            temp.write(chr(0xB1))
            temp.write(chr(0xED))
            temp.write(chr(0x3B))
            temp.write(chr(0xC1))
            temp.seek(0, 0)
            return temp

        #test a BitstreamReader from a Python file object
        f = open("test_core.py", "rb")

        reader = BitstreamReader(f, 0)
        reader.close()
        test_reader(reader)
        reader.set_endianness(1)
        test_reader(reader)

        reader = BitstreamReader(f, 1)
        reader.close()
        test_reader(reader)
        reader.set_endianness(0)
        test_reader(reader)

        f.close()
        del(f)

        #test a BitstreamReader from a Python cStringIO object
        reader = BitstreamReader(new_temp(), 0)
        reader.close()
        test_reader(reader)
        reader.set_endianness(1)
        test_reader(reader)

        reader = BitstreamReader(new_temp(), 1)
        reader.close()
        test_reader(reader)
        reader.set_endianness(0)
        test_reader(reader)

    @LIB_BITSTREAM
    def test_writer_close(self):
        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.bitstream import BitstreamAccumulator

        def test_writer(writer):
            self.assertRaises(IOError, writer.write, 1, 1)
            self.assertRaises(IOError, writer.write_signed, 2, 1)
            self.assertRaises(IOError, writer.unary, 1, 1)
            self.assertRaises(IOError, writer.write_bytes, "foo")
            self.assertRaises(IOError, writer.build, "1u2u3u", [0, 1, 2])

        #test a BitstreamWriter to a Python file object
        f = open("test.bin", "wb")
        try:
            writer = BitstreamWriter(f, 0)
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
            writer = BitstreamWriter(f, 1)
            writer.close()
            test_writer(writer)
            writer.set_endianness(0)
            test_writer(writer)
            f.close()
            del(f)
        finally:
            os.unlink("test.bin")

        #test a BitstreamWriter to a Python cStringIO object
        s = cStringIO.StringIO()
        writer = BitstreamWriter(s, 0)
        writer.close()
        test_writer(writer)
        writer.set_endianness(1)
        test_writer(writer)
        del(writer)
        del(s)

        s = cStringIO.StringIO()
        writer = BitstreamWriter(s, 1)
        writer.close()
        test_writer(writer)
        writer.set_endianness(0)
        test_writer(writer)
        del(writer)
        del(s)

        #test a BitstreamRecorder
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

        #test a BitstreamAccumulator
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


class TestReplayGain(unittest.TestCase):
    @LIB_REPLAYGAIN
    def test_basics(self):
        import audiotools.replaygain
        import audiotools.pcm
        from cStringIO import StringIO

        #check for invalid sample rate
        self.assertRaises(ValueError,
                          audiotools.replaygain.ReplayGain,
                          200000)

        #check for a very small sample count
        rg = audiotools.replaygain.ReplayGain(44100)

        self.assertEqual(
            rg.title_gain(audiotools.PCMReader(StringIO(""),
                                               44100, 2, 0x3, 16)),
            (0.0, 0.0))
        self.assertRaises(ValueError, rg.album_gain)

        #check for no tracks
        assert(len(list(audiotools.calculate_replay_gain([]))) == 0)

        #check for lots of invalid combinations for calculate_replay_gain
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

            gain = list(audiotools.calculate_replay_gain(
                    [track1, track2, track3]))
            self.assertEqual(len(gain), 3)
            self.assert_(gain[0][0] is track1)
            self.assert_(gain[1][0] is track2)
            self.assert_(gain[2][0] is track3)
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
                                              (30000, sample_rate / 100))
            (gain, peak) = gain.title_gain(reader)
            self.assert_(gain < -4.0)
            self.assert_(peak > .90)

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

        #read FrameLists from ReplayGainReader
        f = reader.read(4096)
        while (len(f) > 0):
            f = reader.read(4096)

        #ensure subsequent reads return empty FrameLists
        for i in xrange(10):
            self.assertEqual(len(reader.read(4096)), 0)

        #ensure closing the ReplayGainReader raises ValueError
        #on subsequent reads
        reader.close()

        self.assertRaises(ValueError, reader.read, 4096)

        #ensure wrapped reader is also closed
        self.assertRaises(ValueError, main_reader.read, 4096)


    @LIB_REPLAYGAIN
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
            (gain, peak) = gain.title_gain(track1.to_pcm())

            #apply gain to dummy file
            track2 = test_format.from_pcm(
                dummy2.name,
                audiotools.replaygain.ReplayGainReader(track1.to_pcm(),
                                                       gain,
                                                       peak))

            #ensure gain applied is quieter than without gain applied
            gain2 = audiotools.replaygain.ReplayGain(track1.sample_rate())
            (gain2, peak2) = gain2.title_gain(track2.to_pcm())

            self.assert_(gain2 > gain)
        finally:
            dummy1.close()
            dummy2.close()


class testcuesheet(unittest.TestCase):
    @LIB_CUESHEET
    def setUp(self):
        import audiotools.cue

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
2L8vEA7SCz8do7+XaqGL""".decode('base64').decode('zlib'),

"""eJydlcFu2zAMhu8B8g5CHqAQSUuyeTMcB/C6NIXrbrumXbEF3eIh89r17Se1ASoT0A4CfPpt+KNE
6lPfbtW6u2m6tdo0uq5aKJaL3ofNbrttrwa1av/u76f6z9fD2Iy/XtQTXOg7Wi0X122/2fXbtler
2+PjcXw+qvo0HX5P/t3QDR/b93w4TD8efLzpQvrz5fhw+Pb9bjxN4zSexovn/dNKfa4/tcuFUkNf
N5dKg6pv190uJD57+91w2t8/ali9hf/jh/fdTd+oD9fDpS7LUhsN5/hq3X4J/9eaX58IikkoZkJR
QpELYocRlJJQyoSShBaMyMZF0CIJLTKhhYQaLiyjmcWotM8sWz2LKcRGn78+l2iSJZrMEo0s0TFq
LuJ9sUmozYRaCS0ZgU28UpeEukyok9CKQz9iaJmElpnQUkDBN7ScH7AqCa0yoZWEAlPBNlop6BQU
dB4UtIQaxopJzjq4MOsUzRcktQaZWgOpNSjZPzbadUhqDTK1BlJr/hgRsY1XmtQaZGoNpNbwVWux
MyCpNcjUGkitoWPyh8mJVvtB93vg5vtCyk8F0uzcQVJrkKk1kFojzYBsUZRIwGEgq6iWpO0g03Yg
bUcYptFoWQuxNz5F1yAkJQiZEgQpQe8Ff8fM1JCUIGRKEKQEybG/8zFeaVKCkClBkBKkMrQ6vvAx
KUHMlCDOe6pVgb6hbOUEhNjr0dfyD7jgakg=""".decode('base64').decode('zlib'),

"""eJyVlU9rGzEQxe8Gfwfhe4Nm9Hfntl1vYGkdl+2m7dVNCzUxdkldp/32HW0MWY9RQaDTE+j99GY0
6tuVWnYfm26p3mrQvtHNfNaz2KxXq/ZuUIv2z+bhWP/+tj00h59/1Qlu9FezmM8+tP3tul+1vVrc
7x/3h+e9qp+O219H3hu64X37qg/b4+47y7ddUn9sdgd8czrs8OZ5c1qoz/Wndj5Taujr5p3SoOr7
ZbdOCmsvBw1Pm4dHDYsX8X/Oab+7W7Zf0kFa07guZEwyVOTjhWySbCOZasKCWRYsY9F8FhlH2khE
lj35K0RLRlMwEjESL2svZKuAL8TwbkJusuSmlByQIFLQgpxl1OQkORiyHK4kB0/GkpuGa7OIthix
Ig3kg0Rk2ZwRz6Yua+pKTRFJB7IgTJNcERqRC3quG0EQuWAcczGioliRs+cLncl9ltyXkpvxAQQU
5CwjkJu2UciahmJT7nRgA2nKsiHtRFzprTjyTsRlQuou1CIuO14Ip4WOWfJYSm65h/h02V1cTm66
K3IbyESuniDn0cIXCnaCWGURq1JEx8n664ommVnw1RR0zhR0sSkPKZQ3hVHmFUUuzqcAHIhcXOS3
cv0APM8zLuokLsh+DFD4MWjlzTgvvCBPchpfgtzbcdLFCUv2Y4Dij8F7SjNTjtckO0KULCENYy9T
9FX6L5L8D7C+vb8=""".decode('base64').decode('zlib'),

"""eJyVlU9r20AQxe8Gf4dF94aZ/afV3IQlg2gdF1Vpe3WSQk2CXVI3ab99Z2OVrAe2sKDTWzPz2zez
z2O/Ud3waTV0qjPQ1y2sl4uRxdV2s+mvJ1X1v3d3p/bX/f64Ov74o57xCm5NtVx87Mf1dtz0o6pu
Dg+H48tBtU+n/c8Tn03D9KF/06f96fEby+shqt93j0fzDq9eds+V+tJ+7pcLpaaxXb1XgKq96YZt
VFg7V5medncPgNVZ/F/beD5cd/3XWAiAXr+kus5W12XVQYEhbai2sinLjvBS1goc2XhyIRsFnmwg
lyKaLKIpNiCQjX0FCwIZJjdJU5ttakt9QU1GE3rBEuV/LHNTl23qSm+KjjSSa+RNa+J5WC1cZ9nY
eRgzi8+y+GKWhvjzXrI05GqyXrAwdtyAS3KreLWY8sKuOotYl85I8+09GRDkUWZrtCCPWkMmJCwh
yxJK7dINgSUfRFMDhEi+FnYZJOSJOmEXbxwP+vzqZsQmi9iUInJ1y9OT7yjuEM86SERPwHfCNxaE
HAtCMYvnuCBIhoHZyMTCyARlQlzSGmVTloPMOq0sRF9AGmDZLssrkyBmcxcLcxcVl+Y9dT6pno1M
LI5MW0d7UT7e1/HPOZ3clH/KHmB602ySYmGSouKO/DJsLVgcexvIyJfhPHEKijdtFY+TR5e+DMzm
LhbnLpfmvzXgxPgLE4nhKA==""".decode('base64').decode('zlib')]

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

    def catalogs(self):
        yield '4580226563955'
        yield None
        yield None
        yield None

    def ISRCs(self):
        yield ['JPG750800183',
               'JPG750800212',
               'JPG750800214',
               'JPG750800704',
               'JPG750800705',
               'JPG750800706',
               'JPG750800707',
               'JPG750800708',
               'JPG750800219',
               'JPG750800722',
               'JPG750800709',
               'JPG750800290',
               'JPG750800218',
               'JPG750800710',
               'JPG750800217',
               'JPG750800531',
               'JPG750800225',
               'JPG750800711',
               'JPG750800180',
               'JPG750800712',
               'JPG750800713',
               'JPG750800714']
        yield ['JPTK08880501',
               'JPTK08880502',
               'JPTK08880503',
               'JPTK08880504',
               'JPTK08880505',
               'JPTK08880506',
               'JPTK08880507',
               'JPTK08880508',
               'JPTK08880509',
               'JPTK08880510',
               'JPTK08880511',
               'JPTK08880512',
               'JPTK08880513',
               'JPTK08880514',
               'JPTK08880515',
               'JPTK08880516',
               'JPTK08880517',
               'JPTK08880518',
               'JPTK08880519',
               'JPTK08880520']
        yield [None] * 12
        yield [None] * 15

    def indexes(self):
        yield [[0, ],
               [20885, ],
               [42189,  42411],
               [49242,  49473],
               [52754, ],
               [69656, ],
               [95428, ],
               [118271,  118430],
               [136968, ],
               [138433,  138567],
               [156412, ],
               [168864, ],
               [187716, ],
               [192245, 192373],
               [200347, ],
               [204985, ],
               [227336, ],
               [243382, 243549],
               [265893, 266032],
               [292606, 292942],
               [302893, 303123],
               [321611, ]]
        yield [[0],
               [12297],
               [19707],
               [25975, 29010, 30775],
               [33047],
               [37630],
               [40920],
               [47100],
               [52115],
               [69710, 78487],
               [82410],
               [92542],
               [109675],
               [124432, 127572, 132270],
               [135962, 140804],
               [145400, 148982],
               [156815],
               [166672],
               [172332],
               [191466, 191652]]
        yield [[0, 1493, 3639],
               [11628, 11760, 20323, 36644, 45795],
               [55420, 55550, 62238, 74609],
               [85642, 85775],
               [99566, 99698, 120317, 128603, 134617],
               [136497, 136630],
               [146346, 146480, 157940, 170195, 181445],
               [197952, 198080, 214404, 216449],
               [231522, 231652],
               [245454, 245588, 252426, 262778, 273014],
               [283641, 283774, 289558],
               [298015, 298147, 302911, 312811]]
        yield [[0],
               [15299, 15389, 25750, 30650],
               [39418, 47548],
               [56416, 56668],
               [69134, 76767, 79075],
               [86991, 89821, 98159, 104818],
               [109980, 110057, 124463],
               [130868, 135892, 140520, 144239],
               [147728, 155193, 162676],
               [165758],
               [175346, 175424, 183683, 192339],
               [199856],
               [215266, 224525, 228019],
               [238847, 245887, 253155, 260864],
               [264227]]

    def pcm_lengths(self):
        yield [12280380,
               12657288,
               4152456,
               1929228,
               9938376,
               15153936,
               13525176,
               10900344,
               940212,
               10492860,
               7321776,
               11084976,
               2738316,
               4688712,
               2727144,
               13142388,
               9533244,
               13220004,
               15823080,
               5986428,
               10870944,
               2687748]
        yield [7230636,
               4357080,
               3685584,
               4158336,
               2694804,
               1934520,
               3633840,
               2948820,
               10345860,
               7467600,
               5957616,
               10074204,
               8677116,
               6779640,
               5549544,
               6712020,
               5795916,
               3328080,
               11360160,
               7191240]
        yield [6914880,
               25748520,
               17772300,
               8186724,
               21716016,
               5791800,
               30340800,
               19740336,
               8194368,
               22453368,
               8451324,
               10101840]
        yield [9048732,
               14129052,
               10143000,
               7330008,
               10499916,
               13562808,
               12236868,
               9913680,
               10601640,
               5683608,
               14366016,
               9061080,
               13865628,
               14923440,
               8108520]

    @LIB_CUESHEET
    def testreadsheet(self):
        from itertools import izip

        for (sheet,
             catalog,
             ISRCs,
             indexes,
             pcm_lengths) in izip(self.sheets(),
                                  self.catalogs(),
                                  self.ISRCs(),
                                  self.indexes(),
                                  self.pcm_lengths()):
            self.assertEqual(sheet.catalog(), catalog)
            self.assertEqual([t.ISRC() for t in sheet.tracks()], ISRCs)

            self.assertEqual([[int(i.offset() * 75) for i in t.indexes()]
                              for t in sheet.tracks()], indexes)

            self.assertEqual(list(sheet.pcm_lengths(sum(pcm_lengths), 44100)),
                             pcm_lengths)

    @LIB_CUESHEET
    def testconvertsheet(self):
        import audiotools.cue
        import audiotools.toc
        from itertools import izip

        for (sheet,
             pcm_lengths) in izip(self.sheets(),
                                  self.pcm_lengths()):
            #convert to CUE and test for equality
            temp_cue_file = tempfile.NamedTemporaryFile(suffix='.cue')
            try:
                audiotools.cue.write_cuesheet(
                    sheet,
                    os.path.basename(temp_cue_file.name),
                    temp_cue_file)
                temp_cue_file.flush()

                cue_sheet = audiotools.read_sheet(temp_cue_file.name)

                self.assertEqual(sheet, cue_sheet)
            finally:
                temp_cue_file.close()

            #convert to TOC and test for equality
            temp_toc_file = tempfile.NamedTemporaryFile(suffix='.toc')
            try:
                audiotools.toc.write_tocfile(
                    sheet,
                    os.path.basename(temp_toc_file.name),
                    temp_toc_file)
                temp_toc_file.flush()

                toc_sheet = audiotools.read_sheet(temp_toc_file.name)

                for (track1, track2) in izip(sheet.tracks(),
                                             toc_sheet.tracks()):
                    self.assertEqual(track1, track2)
                self.assertEqual(sheet, toc_sheet)
            finally:
                temp_toc_file.close()

            #convert to embedded cuesheets and test for equality
            for audio_class in [audiotools.FlacAudio,
                                audiotools.OggFlacAudio,
                                audiotools.WavPackAudio,
                                audiotools.TrueAudio]:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix="." + audio_class.SUFFIX)
                try:
                    f = audio_class.from_pcm(
                        temp_file.name,
                        EXACT_BLANK_PCM_Reader(sum(pcm_lengths)))
                    f.set_cuesheet(sheet)
                    f_sheet = audiotools.open(temp_file.name).get_cuesheet()

                    self.assertEqual(sheet, f_sheet)
                finally:
                    temp_file.close()


class testtocsheet(testcuesheet):
    @LIB_CUESHEET
    def setUp(self):
        import audiotools.toc

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

"""eJytl21v2jAQx1+TT2HxAcAPsRNO07QIUsTaUpQGqe8qHiKKOsgU0nXVxHffnYsEvNlsyShCke3E
vzvf3f/S77Nxta+aRVut2fKDrd4q2dYrxntx1O+zovpZNy1bvm0OrK3Zl3XV7BbtYfXybbP73VtX
X6Ph6HmU0X+ZP5XsT8Twd5dNx/NsnD/fZzMc6nAGLJ/aqePVAsZpupyUdznrzvev+/p9z8pt+6Pq
Rp1ZXtw8FPd5cZ7KmnZ7aLunNx2jqCyy4S3L5qPJgx2cPBZD1v0+K295mqZcc/G5+MzXud6bJk/7
l81i9UoP2MF/7N45Xphi976Z0At2H/tqu3lZosfqtm7q3vviV5dxDvZiXEKsIJEO1NKXWganPsEy
LkClYLgDtfKlVsGpY5ASdELUUqEFDtSxL3UcnFpDbEBq62uy4BN0OsqfGMcJQ+6/GtIclzvYpn1t
08FtS0ByiO2J0JU6UBtfahOcOgUpQGtKXkwD4+LrxJc6CU49AAolG0eYBsolZ1Nf6jQ0tcBYTm19
xPAwbr4e+FIPglPbVDXoawU6Rqf/n1pwT2p6IDC1BjkApW15H1ANOZcVkVClUYmDIb6iKoKLqkhB
kCqRIWgUd6H2FVURXFSxEiqsJgkFTZzivQO1r6iK4KIqrahKG+oCtcfF176iKoKLqkxAYT1MKELQ
6foy1LHe4FEklzqLaUENg0sa+4qqCC6qioOQYCTZhhXfqAtDlADK5IGDIb46K4LrrJKUxtqmMd1f
HhIeGsqBcmiXha/0iuDSi1qAPZmxhZWkwYXaV3pFcOlVCSCvtE0+VlHlEv2+0iuCSy9+jmCEU5Mf
29rvEOrSV3plcOmNbYQbY1c/lllR2i9DHDXRX1rQ4zA=""".decode('base64').decode('zlib'),

"""eJytVV1r2zAUfY5/hfD7En3Lvowx07ghrE2L50DfipuYtjSNh+O2GyP/fVdaoDIJebGC8cNRZJ2j
c8+9kwmZ1du6rbp6TR7+kNVbzbtmRehYRpMJKepfTduRh7fHHeka8nVdt69Vt1s9fX98/T1e19+i
i+n9NLPvMr8ryd+I4O8qW8yW2Sy/v85uERpRAiRfuKV97w+E2uVyXl7lJF5uX7bNx5aUz92mjqPR
bV5c3hTXefG5lLXd866LD1/aR1FZZBc/SLaczm8c+Mlj1D/DLh7OKdtq9UJZ/B88c8po71F2Z1zO
7Qeeqk3Dv7w3Gz7+qN5jQim4h1AOQgEVbsN8Mc3v7BpLQSd9SCYg0iHseUD2B9KEpiAFaOM2/Cyz
onTKGCjjs5cgKJiexgTwkdKDGMpGmWqIRhFOI+PAEjDokAbJwfBjjcpnL0Ciab5GpkFIUINMkwEF
pZa0NoQKoArZHgtKhlBV4ahyDtSAZLZM0AfBztcXR4cksB6UuLv37eApKGlrdYBGHU6jcCk33IaJ
MeAysB0mIFVrAXBGLE8Mrj6mmnoXbVuDAu2nQxibDk49SDr9CA3QmITTiG1MIR1Mh8G3bUNHGv1i
kgZEgvXkQ4mVbeQQQWk4QQq90q6+XNzViR49pNUyGpAqzgeOl2njjillJ1qtX19KO0HMh3Cj6Duk
cZZgiQ2xgwUc+Fq47qutHRij093XYy8xGsM6AAs48LUGO+Do+T6sjR2Z2jdGp3b0I/QPz+duJQ==""".decode('base64').decode('zlib'),

"""eJytlt9r20AMx5/jv+LI+5L7fbYYY6ZxQ1ibFs+BvpU0MW1pm4zUXTdG/vdK14ycO9jLXTDB6GTf
R7qvJI/HbNpu2t2ya9fs5jdbvbSy264YH+lsPGZ1+2O769jNy+0z67bs87rdPS2759Xd19unX6N1
+yU7mVxPSvpvqquG/ckY/s7K+XRRTqvr8/ISTQPOgFVzv7TvOTBOy82sOavYcLF52GxfN6y57x7b
YTa4rOrTi/q8qo9L5a67f+6Ghzfts6ypy5NvrFxMZhfeeOQY9PegxcM+zW65euBi+G78zy6DfYDs
9zid0Qvulo9b9UmMXpc/h4xz8BfjCqQCp2OgZCqoAwvjBqQArb3396asGw8sQBhvms0n1RV5aXyi
Z7KgczA8JhqVKpocNBFSWJq4Ak7BQWGkKoZTJ+IUEpQEYRmXoAsE/pB1TLGL4TSpOL0oTEH5NDlw
F+bTEaeWfZPSpI4IdJsKvQC8rCXJokRVEXIWYBwKJDCR9lHFoRfWBQakowTjEkUjMa0YBPYODSrH
658y5eFBSDyIgrwi0PNU6AUgtM19TeINDzgVByHAhrJS2HHQMewwWCr4rIjql0WiaJQvWKPoIDDx
qhcNHhKqLmw6ygLH+EUEuuCp0C12aeA5NR3uwMYIW6QaiihmLEUn/Pyxf9XRE7YK8qk5pZ+HKdaS
ZIX1HRFNqmmKIFipxvqxakDFdEKRaihqR+cufCcUmCkRJo+0TMP7aEJfzLKIymeqOYlsWGfaETq1
vR7neycMe4ex+LXywcvR4IrqHSLVNEUQ/HjCRv0G5L+vfQ==""".decode('base64').decode('zlib')]

        self.suffix = '.toc'


class testflaccuesheet(testcuesheet):
    @LIB_CUESHEET
    def setUp(self):
        from audiotools.flac import (Flac_CUESHEET,
                                     Flac_CUESHEET_track,
                                     Flac_CUESHEET_index)

        self.suffix = '.flac'
        self.test_sheets = [
            Flac_CUESHEET(
                catalog_number='4580226563955\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                lead_in_samples=88200,
                is_cdda=1,
                tracks=[Flac_CUESHEET_track(
                    offset=0,
                    number=1,
                    ISRC='JPG750800183',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=12280380,
                            number=2,
                            ISRC='JPG750800212',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=24807132,
                            number=3,
                            ISRC='JPG750800214',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(130536, 1)]),
                        Flac_CUESHEET_track(
                            offset=28954296,
                            number=4,
                            ISRC='JPG750800704',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(135828, 1)]),
                        Flac_CUESHEET_track(
                            offset=31019352,
                            number=5,
                            ISRC='JPG750800705',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=40957728,
                            number=6,
                            ISRC='JPG750800706',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=56111664,
                            number=7,
                            ISRC='JPG750800707',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=69543348,
                            number=8,
                            ISRC='JPG750800708',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(93492, 1)]),
                        Flac_CUESHEET_track(
                            offset=80537184,
                            number=9,
                            ISRC='JPG750800219',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=81398604,
                            number=10,
                            ISRC='JPG750800722',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(78792, 1)]),
                        Flac_CUESHEET_track(
                            offset=91970256,
                            number=11,
                            ISRC='JPG750800709',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=99292032,
                            number=12,
                            ISRC='JPG750800290',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=110377008,
                            number=13,
                            ISRC='JPG750800218',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=113040060,
                            number=14,
                            ISRC='JPG750800710',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(75264, 1)]),
                        Flac_CUESHEET_track(
                            offset=117804036,
                            number=15,
                            ISRC='JPG750800217',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=120531180,
                            number=16,
                            ISRC='JPG750800531',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=133673568,
                            number=17,
                            ISRC='JPG750800225',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=143108616,
                            number=18,
                            ISRC='JPG750800711',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(98196, 1)]),
                        Flac_CUESHEET_track(
                            offset=156345084,
                            number=19,
                            ISRC='JPG750800180',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(81732, 1)]),
                        Flac_CUESHEET_track(
                            offset=172052328,
                            number=20,
                            ISRC='JPG750800712',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(197568, 1)]),
                        Flac_CUESHEET_track(
                            offset=178101084,
                            number=21,
                            ISRC='JPG750800713',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 0),
                                Flac_CUESHEET_index(135240, 1)]),
                        Flac_CUESHEET_track(
                            offset=189107268,
                            number=22,
                            ISRC='JPG750800714',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[
                                Flac_CUESHEET_index(0, 1)]),
                        Flac_CUESHEET_track(
                            offset=191795016,
                            number=170,
                            ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                            track_type=0,
                            pre_emphasis=0,
                            index_points=[])]),

        Flac_CUESHEET(
            catalog_number='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            lead_in_samples=88200L,
            is_cdda=1,
            tracks=[
                Flac_CUESHEET_track(
                    offset=0L,
                    number=1,
                    ISRC='JPTK08880501',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=7230636L,
                    number=2,
                    ISRC='JPTK08880502',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=11587716L,
                    number=3,
                    ISRC='JPTK08880503',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=15273300L,
                    number=4,
                    ISRC='JPTK08880504',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1),
                        Flac_CUESHEET_index(1784580L, 2),
                        Flac_CUESHEET_index(2822400L, 3)]),
                Flac_CUESHEET_track(
                    offset=19431636L,
                    number=5,
                    ISRC='JPTK08880505',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=22126440L,
                    number=6,
                    ISRC='JPTK08880506',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=24060960L,
                    number=7,
                    ISRC='JPTK08880507',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=27694800L,
                    number=8,
                    ISRC='JPTK08880508',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=30643620L,
                    number=9,
                    ISRC='JPTK08880509',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=40989480L,
                    number=10,
                    ISRC='JPTK08880510',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1),
                        Flac_CUESHEET_index(5160876L, 2)]),
                Flac_CUESHEET_track(
                    offset=48457080L,
                    number=11,
                    ISRC='JPTK08880511',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=54414696L,
                    number=12,
                    ISRC='JPTK08880512',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=64488900L,
                    number=13,
                    ISRC='JPTK08880513',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=73166016L,
                    number=14,
                    ISRC='JPTK08880514',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1),
                        Flac_CUESHEET_index(1846320L, 2),
                        Flac_CUESHEET_index(4608744L, 3)]),
                Flac_CUESHEET_track(
                    offset=79945656L,
                    number=15,
                    ISRC='JPTK08880515',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1),
                        Flac_CUESHEET_index(2847096L, 2)]),
                Flac_CUESHEET_track(
                    offset=85495200L,
                    number=16,
                    ISRC='JPTK08880516',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1),
                        Flac_CUESHEET_index(2106216L, 2)]),
                Flac_CUESHEET_track(
                    offset=92207220L,
                    number=17,
                    ISRC='JPTK08880517',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=98003136L,
                    number=18,
                    ISRC='JPTK08880518',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=101331216L,
                    number=19,
                    ISRC='JPTK08880519',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1)]),
                Flac_CUESHEET_track(
                    offset=112582008L,
                    number=20,
                    ISRC='JPTK08880520',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(109368L, 1)]),
                Flac_CUESHEET_track(
                    offset=119882616L,
                    number=170,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[])]),

        Flac_CUESHEET(
            catalog_number='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            lead_in_samples=88200L,
            is_cdda=1,
            tracks=[
                Flac_CUESHEET_track(
                    offset=0L,
                    number=1,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 1),
                        Flac_CUESHEET_index(877884L, 2),
                        Flac_CUESHEET_index(2139732L, 3)]),
                Flac_CUESHEET_track(
                    offset=6837264L,
                    number=2,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(77616L, 1),
                        Flac_CUESHEET_index(5112660L, 2),
                        Flac_CUESHEET_index(14709408L, 3),
                        Flac_CUESHEET_index(20090196L, 4)]),
                Flac_CUESHEET_track(
                    offset=32586960L,
                    number=3,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(76440L, 1),
                        Flac_CUESHEET_index(4008984L, 2),
                        Flac_CUESHEET_index(11283132L, 3)]),
                Flac_CUESHEET_track(
                    offset=50357496L,
                    number=4,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(78204L, 1)]),
                Flac_CUESHEET_track(
                    offset=58544808L,
                    number=5,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(77616L, 1),
                        Flac_CUESHEET_index(12201588L, 2),
                        Flac_CUESHEET_index(17073756L, 3),
                        Flac_CUESHEET_index(20609988L, 4)]),
                Flac_CUESHEET_track(
                    offset=80260236L,
                    number=6,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(78204L, 1)]),
                Flac_CUESHEET_track(
                    offset=86051448L,
                    number=7,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(78792L, 1),
                        Flac_CUESHEET_index(6817272L, 2),
                        Flac_CUESHEET_index(14023212L, 3),
                        Flac_CUESHEET_index(20638212L, 4)]),
                Flac_CUESHEET_track(
                    offset=116395776L,
                    number=8,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(75264L, 1),
                        Flac_CUESHEET_index(9673776L, 2),
                        Flac_CUESHEET_index(10876236L, 3)]),
                Flac_CUESHEET_track(
                    offset=136134936L,
                    number=9,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(76440L, 1)]),
                Flac_CUESHEET_track(
                    offset=144326952L,
                    number=10,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(78792L, 1),
                        Flac_CUESHEET_index(4099536L, 2),
                        Flac_CUESHEET_index(10186512L, 3),
                        Flac_CUESHEET_index(16205280L, 4)]),
                Flac_CUESHEET_track(
                    offset=166780908L,
                    number=11,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(78204L, 1),
                        Flac_CUESHEET_index(3479196L, 2)]),
                Flac_CUESHEET_track(
                    offset=175232820L,
                    number=12,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[
                        Flac_CUESHEET_index(0L, 0),
                        Flac_CUESHEET_index(77616L, 1),
                        Flac_CUESHEET_index(2878848L, 2),
                        Flac_CUESHEET_index(8700048L, 3)]),
                Flac_CUESHEET_track(
                    offset=185412276L,
                    number=170,
                    ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    track_type=0,
                    pre_emphasis=0,
                    index_points=[])]),

            Flac_CUESHEET(
                catalog_number='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                lead_in_samples=88200L,
                is_cdda=1,
                tracks=[
                    Flac_CUESHEET_track(
                        offset=0L,
                        number=1,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1)]),
                    Flac_CUESHEET_track(
                        offset=8995812L,
                        number=2,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 0),
                            Flac_CUESHEET_index(52920L, 1),
                            Flac_CUESHEET_index(6145188L, 2),
                            Flac_CUESHEET_index(9026388L, 3)]),
                    Flac_CUESHEET_track(
                        offset=23177784L,
                        number=3,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(4780440L, 2)]),
                    Flac_CUESHEET_track(
                        offset=33172608L,
                        number=4,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 0),
                            Flac_CUESHEET_index(148176L, 1)]),
                    Flac_CUESHEET_track(
                        offset=40650792L,
                        number=5,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(4488204L, 2),
                            Flac_CUESHEET_index(5845308L, 3)]),
                    Flac_CUESHEET_track(
                        offset=51150708L,
                        number=6,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(1664040L, 2),
                            Flac_CUESHEET_index(6566784L, 3),
                            Flac_CUESHEET_index(10482276L, 4)]),
                    Flac_CUESHEET_track(
                        offset=64668240L,
                        number=7,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 0),
                            Flac_CUESHEET_index(45276L, 1),
                            Flac_CUESHEET_index(8516004L, 2)]),
                    Flac_CUESHEET_track(
                        offset=76950384L,
                        number=8,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(2954112L, 2),
                            Flac_CUESHEET_index(5675376L, 3),
                            Flac_CUESHEET_index(7862148L, 4)]),
                    Flac_CUESHEET_track(
                        offset=86864064L,
                        number=9,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(4389420L, 2),
                            Flac_CUESHEET_index(8789424L, 3)]),
                    Flac_CUESHEET_track(
                        offset=97465704L,
                        number=10,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1)]),
                    Flac_CUESHEET_track(
                        offset=103103448L,
                        number=11,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 0),
                            Flac_CUESHEET_index(45864L, 1),
                            Flac_CUESHEET_index(4902156L, 2),
                            Flac_CUESHEET_index(9991884L, 3)]),
                    Flac_CUESHEET_track(
                        offset=117515328L,
                        number=12,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1)]),
                    Flac_CUESHEET_track(
                        offset=126576408L,
                        number=13,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(5444292L, 2),
                            Flac_CUESHEET_index(7498764L, 3)]),
                    Flac_CUESHEET_track(
                        offset=140442036L,
                        number=14,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1),
                            Flac_CUESHEET_index(4139520L, 2),
                            Flac_CUESHEET_index(8413104L, 3),
                            Flac_CUESHEET_index(12945996L, 4)]),
                    Flac_CUESHEET_track(
                        offset=155365476L,
                        number=15,
                        ISRC='\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                        track_type=0,
                        pre_emphasis=0,
                        index_points=[
                            Flac_CUESHEET_index(0L, 1)]),
                    Flac_CUESHEET_track(
                        offset=163473996L,
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
                metadata.replace_blocks(
                    audiotools.flac.Flac_CUESHEET.BLOCK_ID,
                    [test_sheet])
                tempflac.update_metadata(metadata)

                sheet = audiotools.open(tempflacfile.name).get_cuesheet()
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

    def read(self, pcm_frames):
        return audiotools.pcm.from_channels(
            [reader.read(pcm_frames) for reader in self.buffers])

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

        if (audiotools.m4a.M4AAudio_nero.available(audiotools.BIN)):
            self.flac_channel_masks.append(audiotools.m4a.M4AAudio_nero)

        #these support a reordered subset of ChannelMasks up to 8 channels
        self.vorbis_channel_masks = [audiotools.VorbisAudio,
                                     audiotools.OpusAudio]

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
                                    "mask = %s for format %s at %d channels" %
                                    (temp_track.channel_mask(),
                                     audio_class,
                                     channels))
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
        try:
            temp_track = audio_class.from_pcm(
                temp_file.name,
                PCM_Reader_Multiplexer([t.to_pcm() for t in tone_tracks],
                                       channel_mask))

            gain_values = [
                replaygain.ReplayGain(temp_track.sample_rate()).title_gain(
                    audiotools.RemaskedPCMReader(temp_track.to_pcm(),
                                                 1,
                                                 mask))[0]
                           for mask in
                           [int(audiotools.ChannelMask.from_fields(
                            **{channel_name:True}))
                            for channel_name in
                            channel_mask.channels()]]

            self.assertEqual(set([True]),
                             set([prev.replay_gain().track_gain >
                                  curr.replay_gain().track_gain
                                  for (prev, curr) in
                                  zip(tone_tracks, tone_tracks[1:])]))

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
                    ((audio_class is audiotools.m4a.M4AAudio_nero) or
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

        # for mask in [from_fields(front_left=True, front_right=True),
        #              from_fields(front_left=True, front_right=True,
        #                          back_left=True, back_right=True),
        #              from_fields(front_left=True, side_left=True,
        #                          front_center=True, front_right=True,
        #                          side_right=True, back_center=True)]:
        #     self.__test_assignment__(audiotools.AiffAudio,
        #                              TONE_TRACKS[0:len(mask)],
        #                              mask)

    @LIB_CORE
    def test_unsupported_channel_mask_from_pcm(self):
        for channels in xrange(1, 6 + 1):
            self.__test_undefined_mask_blank__(audiotools.WaveAudio,
                                               channels,
                                               False)
        for channels in xrange(1, 3):
            self.__test_undefined_mask_blank__(audiotools.WavPackAudio,
                                               channels,
                                               False)
        for channels in xrange(3, 21):
            self.__test_undefined_mask_blank__(audiotools.WavPackAudio,
                                               channels,
                                               True)

        for channels in xrange(1, 9):
            self.__test_undefined_mask_blank__(audiotools.ALACAudio,
                                               channels,
                                               False)
        for channels in xrange(9, 21):
            self.__test_undefined_mask_blank__(audiotools.ALACAudio,
                                               channels,
                                               True)

        for audio_class in [audiotools.FlacAudio, audiotools.OggFlacAudio]:
            for channels in xrange(1, 9):
                self.__test_undefined_mask_blank__(audio_class,
                                                   channels,
                                                   False)

            self.__test_error_channel_count__(audio_class,
                                              9, audiotools.ChannelMask(0))
            self.__test_error_channel_count__(audio_class,
                                              10, audiotools.ChannelMask(0))

        for stereo_audio_class in [audiotools.MP3Audio,
                                   audiotools.MP2Audio,
                                   audiotools.m4a.M4AAudio_faac]:

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
        for channels in xrange(3, 11):
            self.__test_undefined_mask_blank__(audiotools.AuAudio,
                                               channels,
                                               True)

        if (audiotools.m4a.M4AAudio_nero.available(audiotools.BIN)):
            for channels in xrange(1, 7):
                self.__test_undefined_mask_blank__(audiotools.m4a.M4AAudio_nero,
                                                   channels,
                                                   False)


class __callback__:
    def __init__(self):
        self.called = False

    def call(self):
        self.called = True

    def reset(self):
        self.called = False


class Test_NULL_Player(unittest.TestCase):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            EXACT_SILENCE_PCM_Reader(pcm_frames=44100 * 6))
        self.output_name = "NULL"

    @LIB_PLAYER
    def tearDown(self):
        self.temp_track_file.close()

    @LIB_PLAYER
    def test_stopped_notrack(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING,
                                       RG_NO_REPLAYGAIN,
                                       RG_TRACK_GAIN,
                                       RG_ALBUM_GAIN)
        import time

        #try all the player methods while the player is stopped
        #and no track is opened
        try:
            player = audiotools.player.Player(
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #output not supported on this system
            return

        try:
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure setting ReplayGain causes no errors
            for gain in [RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN]:
                player.set_replay_gain(gain)

            #pause does nothing
            player.pause()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #play does nothing
            player.play()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #toggle playing/pausing does nothing
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #stopping does nothing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure progress remains constant
            player.play()
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assertEqual(s_current, e_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
        finally:
            player.close()

    @LIB_PLAYER
    def test_stopped_track(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING,
                                       RG_NO_REPLAYGAIN,
                                       RG_TRACK_GAIN,
                                       RG_ALBUM_GAIN)
        import time

        #try all the player methods while a track is opened
        #and the player is stopped
        try:
            player = audiotools.player.Player(
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #player not supported on this system
            return

        try:
            self.assertEqual(player.state(), PLAYER_STOPPED)

            player.open(self.temp_track)
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #opening new track while stopped should keep us in stopped state
            player.open(self.temp_track)
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure setting ReplayGain causes no errors
            for gain in [RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN]:
                player.set_replay_gain(gain)

            #pause does nothing while stopped
            player.pause()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #play starts track playing
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #toggle playing/pausing starts playing if stopped
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #stopping while stopped does nothing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure progress remains constant while stopped
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assertEqual(s_current, e_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
        finally:
            player.close()

    @LIB_PLAYER
    def test_paused(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING,
                                       RG_NO_REPLAYGAIN,
                                       RG_TRACK_GAIN,
                                       RG_ALBUM_GAIN)
        import time

        #try all the player methods while a track is opened
        #and the player is paused
        try:
            player = audiotools.player.Player(
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #player not supported on this system
            return

        try:
            player.open(self.temp_track)
            player.play()
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #open new track while paused should put us in stopped state
            player.open(self.temp_track)
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #ensure setting ReplayGain causes no errors
            for gain in [RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN]:
                player.set_replay_gain(gain)

            self.assertEqual(player.state(), PLAYER_PAUSED)

            #pause does nothing while paused
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #play starts track playing
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #toggle playing/pausing starts playing if paused
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #stopping while paused stops playing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #ensure progress remains constant while paused
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assertEqual(s_current, e_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(
                audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.play()
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)
        finally:
            player.close()

    @LIB_PLAYER
    def test_playing(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING,
                                       RG_NO_REPLAYGAIN,
                                       RG_TRACK_GAIN,
                                       RG_ALBUM_GAIN)
        import time

        try:
            player = audiotools.player.Player(
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #player not supported on this system
            return

        #try all the player methods while a track is opened
        #and the player is playing
        try:
            player.open(self.temp_track)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #open new track while playing should put us in stopped state
            player.open(self.temp_track)
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #ensure setting ReplayGain causes no errors
            for gain in [RG_NO_REPLAYGAIN, RG_TRACK_GAIN, RG_ALBUM_GAIN]:
                player.set_replay_gain(gain)

            self.assertEqual(player.state(), PLAYER_PLAYING)

            #pause pauses while playing
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #play while playing does nothing
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #toggle playing/pausing pauses playing
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #stopping while playing stops playing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #ensure progress increments while playing
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assert_(e_current > s_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(
                audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

        finally:
            player.close()


    @LIB_PLAYER
    def test_callback(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING,
                                       RG_NO_REPLAYGAIN,
                                       RG_TRACK_GAIN,
                                       RG_ALBUM_GAIN)
        import time

        callback = __callback__()

        try:
            player = audiotools.player.Player(
                audiotools.player.open_output(self.output_name),
                next_track_callback=callback.call)
        except ValueError:
            #player not supported on this system
            return

        try:
            player.open(self.temp_track)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #let player run to the end of the track
            while (player.state() == PLAYER_PLAYING):
                time.sleep(1)

            #ensure it stops when finished
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure callback has been called
            self.assertEqual(callback.called, True)
        finally:
            player.close()

class Test_Dummy_Player(Test_NULL_Player):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            EXACT_SILENCE_PCM_Reader(pcm_frames=44100 * 6))
        #this should raise ValueError when opened by player
        self.output_name = "DUMMY"


class Test_ALSA_Player(Test_NULL_Player):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            EXACT_SILENCE_PCM_Reader(pcm_frames=44100 * 6))
        self.output_name = "ALSA"


class Test_PulseAudio_Player(Test_NULL_Player):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            EXACT_SILENCE_PCM_Reader(pcm_frames=44100 * 6))
        self.output_name = "PulseAudio"


class Test_OSS_Player(Test_NULL_Player):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            EXACT_SILENCE_PCM_Reader(pcm_frames=44100 * 6))
        self.output_name = "OSS"


class Test_CoreAudio_Player(Test_NULL_Player):
    @LIB_PLAYER
    def setUp(self):
        self.temp_track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.temp_track = audiotools.FlacAudio.from_pcm(
            self.temp_track_file.name,
            EXACT_SILENCE_PCM_Reader(pcm_frames=44100 * 6))
        self.output_name = "CoreAudio"


class Test_NULL_CDPlayer(unittest.TestCase):
    def __setup_bin_cue__(self):
        input_dir = tempfile.mkdtemp()
        cue_file = os.path.join(input_dir, "CDImage.cue")
        bin_file = os.path.join(input_dir, "CDImage.bin")

        f = open(cue_file, "w")
        f.write('FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 05:04:53\n    INDEX 01 05:06:30\n  TRACK 03 AUDIO\n    INDEX 00 09:50:31\n    INDEX 01 09:54:19\n  TRACK 04 AUDIO\n    INDEX 00 14:58:69\n    INDEX 01 15:00:47\n')
        f.close()

        f = open(bin_file, "w")
        audiotools.transfer_framelist_data(
            EXACT_SILENCE_PCM_Reader(52251444), f.write)
        f.close()

        return (input_dir, cue_file, bin_file)

    @LIB_PLAYER
    def setUp(self):
        (self.input_dir,
         self.cue_file,
         self.bin_file) = self.__setup_bin_cue__()
        self.output_name = "NULL"

    @LIB_PLAYER
    def tearDown(self):
        for f in os.listdir(self.input_dir):
            os.unlink(os.path.join(self.input_dir, f))
        os.rmdir(self.input_dir)

    @LIB_PLAYER
    def test_stopped_notrack(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING)
        import time

        #try all the player methods while the player is stopped
        #and no track is opened
        try:
            player = audiotools.player.CDPlayer(
                audiotools.CDDA(self.cue_file),
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #output not supported on this system
            return

        try:
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #pause does nothing
            player.pause()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #play does nothing
            player.play()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #toggle playing/pausing does nothing
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #stopping does nothing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure progress remains constant
            player.play()
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assertEqual(s_current, e_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
        finally:
            player.close()

    @LIB_PLAYER
    def test_stopped_track(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING)
        import time

        #try all the player methods while a track is opened
        #and the player is stopped
        try:
            player = audiotools.player.CDPlayer(
                audiotools.CDDA(self.cue_file),
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #output not supported on this system
            return

        try:
            self.assertEqual(player.state(), PLAYER_STOPPED)

            player.open(1)
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #opening new track while stopped should keep us in stopped state
            player.open(2)
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #pause does nothing while stopped
            player.pause()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #play starts track playing
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #toggle playing/pausing starts playing if stopped
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #stopping while stopped does nothing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)

            #ensure progress remains constant while stopped
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assertEqual(s_current, e_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
        finally:
            player.close()

    @LIB_PLAYER
    def test_paused(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING)
        import time

        def next_track():
            print "track finished"

        #try all the player methods while a track is opened
        #and the player is paused
        try:
            player = audiotools.player.CDPlayer(
                audiotools.CDDA(self.cue_file),
                audiotools.player.open_output(self.output_name),
                next_track_callback=next_track)
        except ValueError:
            #player not supported on this system
            return

        try:
            player.open(1)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #open new track while paused should put us in stopped state
            player.open(2)
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #pause does nothing while paused
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #play starts track playing
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #toggle playing/pausing starts playing if paused
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_PLAYING)
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #stopping while paused stops playing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)

            #ensure progress remains constant while paused
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assertEqual(s_current, e_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(
                audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)
            self.assertEqual(player.state(), PLAYER_STOPPED)

            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)
        finally:
            player.close()

    @LIB_PLAYER
    def test_playing(self):
        import audiotools.player
        from audiotools.player import (PLAYER_STOPPED,
                                       PLAYER_PAUSED,
                                       PLAYER_PLAYING)
        import time

        try:
            player = audiotools.player.CDPlayer(
                audiotools.CDDA(self.cue_file),
                audiotools.player.open_output(self.output_name))
        except ValueError:
            #player not supported on this system
            return

        #try all the player methods while a track is opened
        #and the player is playing
        try:
            player.open(1)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #open new track while playing should put us in stopped state
            player.open(2)
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #pause pauses while playing
            player.pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #play while playing does nothing
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #toggle playing/pausing pauses playing
            player.toggle_play_pause()
            self.assertEqual(player.state(), PLAYER_PAUSED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #stopping while playing stops playing
            player.stop()
            self.assertEqual(player.state(), PLAYER_STOPPED)
            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)

            #ensure progress increments while playing
            (s_current, s_total) = player.progress()
            time.sleep(1)
            (e_current, e_total) = player.progress()
            self.assertEqual(s_total, e_total)
            self.assert_(s_current <= s_total)
            self.assert_(e_current <= s_total)
            self.assert_(e_current > s_current)

            self.assertEqual(player.current_output_name(), self.output_name)

            #changing volume should be okay
            current_volume = player.get_volume()
            try:
                player.set_volume(0.0)
                self.assertEqual(player.get_volume(), 0.0)
            finally:
                player.set_volume(current_volume)

            #setting output should cause no errors
            for output in audiotools.player.available_outputs():
                player.set_output(output)
                self.assertEqual(player.current_output_name(), output.NAME)

            #setting invalid output should raise TypeError
            self.assertRaises(TypeError, player.set_output, "DUMMY")

            player.set_output(
                audiotools.player.open_output(self.output_name))
            self.assertEqual(player.current_output_name(), self.output_name)

            player.play()
            self.assertEqual(player.state(), PLAYER_PLAYING)
        finally:
            player.close()


    @LIB_PLAYER
    def test_callback(self):
        #FIXME
        self.assert_(True)


class Test_Dummy_CDPlayer(Test_NULL_CDPlayer):
    @LIB_PLAYER
    def setUp(self):
        (self.input_dir,
         self.cue_file,
         self.bin_file) = self.__setup_bin_cue__()
        #this should raise ValueError when opened by player
        self.output_name = "DUMMY"


class Test_ALSA_CDPlayer(Test_NULL_CDPlayer):
    @LIB_PLAYER
    def setUp(self):
        (self.input_dir,
         self.cue_file,
         self.bin_file) = self.__setup_bin_cue__()
        self.output_name = "ALSA"


class Test_PulseAudio_CDPlayer(Test_NULL_CDPlayer):
    @LIB_PLAYER
    def setUp(self):
        (self.input_dir,
         self.cue_file,
         self.bin_file) = self.__setup_bin_cue__()
        self.output_name = "PulseAudio"


class Test_OSS_CDPlayer(Test_NULL_CDPlayer):
    @LIB_PLAYER
    def setUp(self):
        (self.input_dir,
         self.cue_file,
         self.bin_file) = self.__setup_bin_cue__()
        self.output_name = "OSS"


class Test_CoreAudio_CDPlayer(Test_NULL_CDPlayer):
    @LIB_PLAYER
    def setUp(self):
        (self.input_dir,
         self.cue_file,
         self.bin_file) = self.__setup_bin_cue__()
        self.output_name = "CoreAudio"


class Test_Accuraterip(unittest.TestCase):
    @LIB_ACCURATERIP
    def test_checksum_v1(self):
        from audiotools._accuraterip import ChecksumV1

        #sanity checking
        self.assertRaises(ValueError,
                          ChecksumV1,
                          False, False,
                          0, 10)

        self.assertRaises(ValueError,
                          ChecksumV1,
                          False, False,
                          -1, 10)

        self.assertRaises(ValueError,
                          ChecksumV1,
                          False, False,
                          44100, 0)

        self.assertRaises(ValueError,
                          ChecksumV1,
                          False, False,
                          44100, -1)

        self.assertRaises(ValueError,
                          ChecksumV1,
                          False, False,
                          -1, -1)

        track = audiotools.open("tone.flac")

        first_track = ChecksumV1(True, False,
                                 track.sample_rate(),
                                 track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, first_track.update)

        #values taken from reference implementation
        self.assertEqual(first_track.checksum(), 0xEE4DBEB4)

        middle_track = ChecksumV1(False, False,
                                  track.sample_rate(),
                                  track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, middle_track.update)

        self.assertEqual(middle_track.checksum(), 0xF6E4AD26)

        last_track = ChecksumV1(False, True,
                                track.sample_rate(),
                                track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, last_track.update)

        self.assertEqual(last_track.checksum(), 0xF819E862)

        only_track = ChecksumV1(True, True,
                                track.sample_rate(),
                                track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, only_track.update)

        self.assertEqual(only_track.checksum(), 0xEF82F9F0)

    @LIB_ACCURATERIP
    def test_checksum_v2(self):
        from audiotools._accuraterip import ChecksumV2

        #sanity checking
        self.assertRaises(ValueError,
                          ChecksumV2,
                          False, False,
                          0, 10)

        self.assertRaises(ValueError,
                          ChecksumV2,
                          False, False,
                          -1, 10)

        self.assertRaises(ValueError,
                          ChecksumV2,
                          False, False,
                          44100, 0)

        self.assertRaises(ValueError,
                          ChecksumV2,
                          False, False,
                          44100, -1)

        self.assertRaises(ValueError,
                          ChecksumV2,
                          False, False,
                          -1, -1)

        track = audiotools.open("tone.flac")

        first_track = ChecksumV2(True, False,
                                 track.sample_rate(),
                                 track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, first_track.update)

        #values taken from reference implementation
        self.assertEqual(first_track.checksum(), 0x3ECA2C04)

        middle_track = ChecksumV2(False, False,
                                  track.sample_rate(),
                                  track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, middle_track.update)

        self.assertEqual(middle_track.checksum(), 0x4781FC37)

        last_track = ChecksumV2(False, True,
                                track.sample_rate(),
                                track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, last_track.update)

        self.assertEqual(last_track.checksum(), 0x222E32FA)

        only_track = ChecksumV2(True, True,
                                track.sample_rate(),
                                track.total_frames())

        audiotools.transfer_data(track.to_pcm().read, only_track.update)

        self.assertEqual(only_track.checksum(), 0x197662C7)


class Test_Ogg(unittest.TestCase):
    @LIB_OGG
    def test_roundtrip(self):
        import audiotools.ogg
        import cStringIO

        for packet_len in xrange(0, 1000):
            packet = os.urandom(packet_len)
            ogg_stream = cStringIO.StringIO()
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
