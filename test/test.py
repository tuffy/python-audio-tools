#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2016  Brian Langenberger

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

import io
import unittest
import audiotools
import tempfile
import os
import os.path
from hashlib import md5
import random
import decimal
import test_streams
import sys
import subprocess
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

parser = SafeConfigParser()
parser.read("test.cfg")

TEST_DIR = os.path.dirname(os.path.realpath(__file__))


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


def BLANK_PCM_Reader(length, sample_rate=44100, channels=2,
                     bits_per_sample=16, channel_mask=None):
    from audiotools.decoders import SameSample

    if channel_mask is None:
        channel_mask = int(audiotools.ChannelMask.from_channels(channels))

    return SameSample(sample=1,
                      total_pcm_frames=length * sample_rate,
                      sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)


class EXACT_RANDOM_PCM_Reader(audiotools.PCMReader):
    def __init__(self, pcm_frames,
                 sample_rate=44100, channels=2, bits_per_sample=16,
                 channel_mask=None):
        audiotools.PCMReader.__init__(
            self,
            sample_rate=sample_rate,
            channels=channels,
            channel_mask=(channel_mask if channel_mask is not None else
                          int(audiotools.ChannelMask.from_channels(channels))),
            bits_per_sample=bits_per_sample)

        self.closed = False
        self.total_frames = pcm_frames
        self.original_frames = self.total_frames

    def read(self, pcm_frames):
        if self.closed:
            raise ValueError("cannot read from closed stream")
        elif self.total_frames > 0:
            frames_to_read = min(pcm_frames, self.total_frames)
            frame = audiotools.pcm.FrameList(
                os.urandom(frames_to_read *
                           (self.bits_per_sample // 8) *
                           self.channels),
                self.channels,
                self.bits_per_sample,
                True,
                True)
            self.total_frames -= frame.frames
            return frame
        else:
            return audiotools.pcm.empty_framelist(
                self.channels, self.bits_per_sample)

    def close(self):
        self.closed = True

    def reset(self):
        self.closed = False
        self.total_frames = self.original_frames


class RANDOM_PCM_Reader(EXACT_RANDOM_PCM_Reader):
    def __init__(self, length,
                 sample_rate=44100, channels=2, bits_per_sample=16,
                 channel_mask=None):
        EXACT_RANDOM_PCM_Reader.__init__(
            self,
            pcm_frames=length * sample_rate,
            sample_rate=sample_rate,
            channels=channels,
            bits_per_sample=bits_per_sample,
            channel_mask=channel_mask)


def EXACT_BLANK_PCM_Reader(pcm_frames, sample_rate=44100, channels=2,
                           bits_per_sample=16, channel_mask=None):
    from audiotools.decoders import SameSample

    if channel_mask is None:
        channel_mask = int(audiotools.ChannelMask.from_channels(channels))

    return SameSample(sample=1,
                      total_pcm_frames=pcm_frames,
                      sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)


def EXACT_SILENCE_PCM_Reader(pcm_frames, sample_rate=44100, channels=2,
                             bits_per_sample=16, channel_mask=None):
    from audiotools.decoders import SameSample

    if channel_mask is None:
        channel_mask = int(audiotools.ChannelMask.from_channels(channels))

    return SameSample(sample=0,
                      total_pcm_frames=pcm_frames,
                      sample_rate=sample_rate,
                      channels=channels,
                      channel_mask=channel_mask,
                      bits_per_sample=bits_per_sample)


class MD5_Reader(audiotools.PCMReader):
    def __init__(self, pcmreader):
        audiotools.PCMReader.__init__(
            self,
            sample_rate=pcmreader.sample_rate,
            channels=pcmreader.channels,
            channel_mask=pcmreader.channel_mask,
            bits_per_sample=pcmreader.bits_per_sample)
        self.pcmreader = pcmreader
        self.md5 = md5()

    def __repr__(self):
        return "MD5Reader({!r},{!r},{!r})".format(
            self.sample_rate, self.channels, self.bits_per_sample)

    def reset(self):
        if hasattr(self.pcmreader, "reset"):
            self.pcmreader.reset()
        self.md5 = md5()

    def read(self, pcm_frames):
        framelist = self.pcmreader.read(pcm_frames)
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def close(self):
        self.pcmreader.close()

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()


class Variable_Reader(audiotools.PCMReader):
    def __init__(self, pcmreader):
        audiotools.PCMReader.__init__(
            self,
            sample_rate=pcmreader.sample_rate,
            channels=pcmreader.channels,
            channel_mask=pcmreader.channel_mask,
            bits_per_sample=pcmreader.bits_per_sample)
        self.pcmreader = audiotools.BufferedPCMReader(pcmreader)
        self.md5 = md5()
        self.range = range(self.channels * (self.bits_per_sample // 8),
                           4096)

    def read(self, pcm_frames):
        return self.pcmreader.read(random.choice(self.range))

    def close(self):
        self.pcmreader.close()


class Join_Reader(audiotools.PCMReader):
    # given a list of 1 channel PCM readers,
    # combines them into a single reader
    # a bit like PCMCat but across channels instead of PCM frames
    def __init__(self, pcm_readers, channel_mask):
        if len({r.sample_rate for r in pcm_readers}) != 1:
            raise ValueError("all readers must have the same sample rate")
        if len({r.bits_per_sample for r in pcm_readers}) != 1:
            raise ValueError("all readers must have the same bits per sample")
        if {r.channels for r in pcm_readers} != {1}:
            raise ValueError("all readers must be 1 channel")
        assert(isinstance(channel_mask, int))

        audiotools.PCMReader.__init__(
            self,
            sample_rate=pcm_readers[0].sample_rate,
            channels=len(pcm_readers),
            channel_mask=channel_mask,
            bits_per_sample=pcm_readers[0].bits_per_sample)

        self.pcm_readers = pcm_readers
        self.readers = map(audiotools.BufferedPCMReader, pcm_readers)

    def read(self, pcm_frames):
        return audiotools.pcm.from_channels(
            [r.read(pcm_frames) for r in self.pcm_readers])

    def reset(self):
        for r in self.pcm_readers:
            r.reset()
        self.readers = map(audiotools.BufferedPCMReader, self.pcm_readers)

    def close(self):
        for r in self.pcm_readers:
            r.close()


class FrameCounter:
    def __init__(self, channels, bits_per_sample, sample_rate, value=0):
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.sample_rate = sample_rate
        self.value = value

    def __repr__(self):
        return "FrameCounter({!r}, {!r}, {!r}, {!r})".format(
            self.channels, self.bits_per_sample, self.sample_rate, self.value)

    def update(self, f):
        self.value += len(f)

    def __int__(self):
        return int(round(decimal.Decimal(self.value) /
                         (self.channels *
                          (self.bits_per_sample // 8) *
                          self.sample_rate)))


# probstat does this better, but I don't want to require that
# for something used only rarely
def Combinations(items, n):
    if n == 0:
        yield []
    else:
        for i in range(len(items)):
            for combos in Combinations(items[i + 1:], n - 1):
                yield [items[i]] + combos


def Possibilities(*lists):
    if len(lists) == 0:
        yield ()
    else:
        remainder = list(Possibilities(*lists[1:]))
        for item in lists[0]:
            for rem in remainder:
                yield (item,) + rem


from_channels = audiotools.ChannelMask.from_channels

# these are combinations that tend to occur in nature
SHORT_PCM_COMBINATIONS = \
    ((11025,  1, int(from_channels(1)), 8),
     (22050,  1, int(from_channels(1)), 8),
     (22050,  1, int(from_channels(1)), 16),
     (32000,  2, int(from_channels(2)), 16),
     (44100,  1, int(from_channels(1)), 16),
     (44100,  2, int(from_channels(2)), 16),
     (48000,  1, int(from_channels(1)), 16),
     (48000,  2, int(from_channels(2)), 16),
     (48000,  6, int(audiotools.ChannelMask.from_fields(
                         front_left=True,
                         front_right=True,
                         front_center=True,
                         low_frequency=True,
                         back_left=True,
                         back_right=True)), 16),
     (192000, 2, int(from_channels(2)), 24),
     (96000,  6, int(audiotools.ChannelMask.from_fields(
                         front_left=True,
                         front_right=True,
                         front_center=True,
                         low_frequency=True,
                         back_left=True,
                         back_right=True)), 24))

with io.open(os.path.join(TEST_DIR, "test_cover1.jpg"), "rb") as c:
    TEST_COVER1 = c.read()

with io.open(os.path.join(TEST_DIR, "test_cover2.png"), "rb") as c:
    TEST_COVER2 = c.read()

with io.open(os.path.join(TEST_DIR, "test_cover3.jpg"), "rb") as c:
    TEST_COVER3 = c.read()

with io.open(os.path.join(TEST_DIR, "test_cover4.png"), "rb") as c:
    TEST_COVER4 = c.read()

# this is a very large, plain BMP encoded as bz2
with io.open(os.path.join(TEST_DIR, "huge.bmp.bz2"), "rb") as c:
    HUGE_BMP = c.read()


from test_formats import *
from test_core import *
from test_metadata import *
from test_utils import *

if (__name__ == '__main__'):
    unittest.main()
