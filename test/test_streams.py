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

import audiotools
import cStringIO
import math
import os
from hashlib import md5
from audiotools.decoders import Sine_Mono, Sine_Stereo, Sine_Simple

# these are test stream generators using stream formulas
# taken from the FLAC reference encoder
# but converted to PCMReaders for more general use


class FrameListReader:
    def __init__(self, samples, sample_rate, channels, bits_per_sample,
                 channel_mask=None):
        import audiotools.pcm

        self.framelist = audiotools.pcm.from_list(samples,
                                                  channels,
                                                  bits_per_sample,
                                                  True)
        self.samples = samples[:]
        self.sample_rate = sample_rate
        self.channels = channels
        if (channel_mask is None):
            self.channel_mask = audiotools.ChannelMask.from_channels(channels)
        else:
            self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

    def read(self, pcm_frames):
        (framelist, self.framelist) = self.framelist.split(pcm_frames)
        return framelist

    def reset(self):
        self.framelist = audiotools.pcm.from_list(self.samples,
                                                  self.channels,
                                                  self.bits_per_sample,
                                                  True)

    def read_closed(self, pcm_frames):
        raise ValueError()

    def close(self):
        self.read = self.read_closed


class MD5Reader:
    def __init__(self, pcmreader):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.md5 = md5()

    def reset(self):
        if (hasattr(self.pcmreader, "reset")):
            self.pcmreader.reset()
        self.md5 = md5()

    def __repr__(self):
        return "MD5Reader(%s,%s,%s)" % (self.sample_rate,
                                        self.channels,
                                        self.bits_per_sample)

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


class ShortStream(MD5Reader):
    def __init__(self, samples, sample_rate, channels, bits_per_sample):
        MD5Reader.__init__(
            self,
            FrameListReader(samples,
                            sample_rate,
                            channels,
                            bits_per_sample))


class Generate01(ShortStream):
    def __init__(self, sample_rate):
        ShortStream.__init__(self, [-32768],
                             sample_rate, 1, 16)


class Generate02(ShortStream):
    def __init__(self, sample_rate):
        ShortStream.__init__(self, [-32768, 32767],
                             sample_rate, 2, 16)


class Generate03(ShortStream):
    def __init__(self, sample_rate):
        ShortStream.__init__(self, [-25, 0, 25, 50, 100],
                             sample_rate, 1, 16)


class Generate04(ShortStream):
    def __init__(self, sample_rate):
        ShortStream.__init__(self, [-25, 500, 0, 400, 25, 300, 50, 200,
                                    100, 100],
                             sample_rate, 2, 16)


class Sine8_Mono(Sine_Mono):
    def __init__(self,
                 pcm_frames,
                 sample_rate,
                 f1, a1, f2, a2):
        Sine_Mono.__init__(self, 8, pcm_frames, sample_rate,
                           f1, a1, f2, a2)
        self.pcm_frames = pcm_frames
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.md5 = md5()

    def read(self, pcm_frames):
        framelist = Sine_Mono.read(self, pcm_frames)
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def reset(self):
        Sine_Mono.reset(self)
        self.md5 = md5()

    def __repr__(self):
        return "Sine8_Mono(%s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2))


class Sine8_Stereo(Sine_Stereo):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        Sine_Stereo.__init__(self, 8, pcm_frames,
                             sample_rate, f1, a1, f2, a2, fmult)
        self.pcm_frames = pcm_frames
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.fmult = fmult
        self.md5 = md5()

    def read(self, pcm_frames):
        framelist = Sine_Stereo.read(self, pcm_frames)
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def reset(self):
        Sine_Stereo.reset(self)
        self.md5 = md5()

    def __repr__(self):
        return "Sine8_Stereo(%s, %s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2),
             repr(self.fmult))


class Sine16_Mono(Sine8_Mono):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        Sine_Mono.__init__(self, 16, pcm_frames, sample_rate,
                           f1, a1, f2, a2)
        self.pcm_frames = pcm_frames
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.md5 = md5()

    def __repr__(self):
        return "Sine16_Mono(%s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2))


class Sine16_Stereo(Sine8_Stereo):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        Sine_Stereo.__init__(self, 16, pcm_frames, sample_rate,
                             f1, a1, f2, a2, fmult)
        self.pcm_frames = pcm_frames
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.fmult = fmult
        self.md5 = md5()

    def __repr__(self):
        return "Sine16_Stereo(%s, %s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2),
             repr(self.fmult))


class Sine24_Mono(Sine8_Mono):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        Sine_Mono.__init__(self, 24, pcm_frames, sample_rate,
                           f1, a1, f2, a2)
        self.pcm_frames = pcm_frames
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.md5 = md5()

    def __repr__(self):
        return "Sine24_Mono(%s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2))


class Sine24_Stereo(Sine8_Stereo):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        Sine_Stereo.__init__(self, 24, pcm_frames, sample_rate,
                             f1, a1, f2, a2, fmult)
        self.pcm_frames = pcm_frames
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.fmult = fmult
        self.md5 = md5()

    def __repr__(self):
        return "Sine24_Stereo(%s, %s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2),
             repr(self.fmult))


class Simple_Sine:
    def __init__(self, pcm_frames, sample_rate, channel_mask,
                 bits_per_sample, *values):
        self.pcm_frames = pcm_frames
        self.total_frames = pcm_frames
        self.i = 0
        self.channel_max_values = [v[0] for v in values]
        self.channel_counts = [v[1] for v in values]

        self.sample_rate = sample_rate
        self.channels = len(values)
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

        self.streams = [Sine_Simple(pcm_frames,
                                    bits_per_sample,
                                    sample_rate,
                                    max_value,
                                    count)
                        for (max_value, count) in zip(self.channel_max_values,
                                                      self.channel_counts)]
        self.md5 = md5()

    def read(self, pcm_frames):
        framelist = audiotools.pcm.from_channels(
            [stream.read(pcm_frames) for stream in self.streams])
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def reset(self):
        for stream in self.streams:
            stream.reset()
        self.md5 = md5()

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def close(self):
        for stream in self.streams:
            stream.close()

    def __repr__(self):
        return "Simple_Sine(%s, %s, %s, %s, *%s)" % \
            (self.pcm_frames,
             self.sample_rate,
             self.channel_mask,
             self.bits_per_sample,
             repr([(m, c) for m, c in zip(self.channel_max_values,
                                          self.channel_counts)]))


class WastedBPS16:
    def __init__(self, pcm_frames):
        self.total_frames = pcm_frames
        self.pcm_frames = pcm_frames

        self.i = 0
        self.sample_rate = 44100
        self.channels = 2
        self.channel_mask = 0x3
        self.bits_per_sample = 16
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 2, 16, False, False)
        self.md5 = md5()

    def read(self, pcm_frames):
        wave = []
        for i in range(min(pcm_frames, self.pcm_frames)):
            wave.append((self.i % 2000) << 2)
            wave.append((self.i % 1000) << 3)
            self.i += 1

        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def read_closed(self, pcm_frames):
        raise ValueError()

    def reset(self):
        self.i = 0
        self.pcm_frames = self.total_frames
        self.md5 = md5()

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def close(self):
        self.read = self.read_closed

    def __repr__(self):
        return "WastedBPS(%s)" % (repr(self.pcm_frames))


class Raw(audiotools.PCMReader):
    def __init__(self, pcm_frames, channels, bits_per_sample):
        self.sample_rate = 44100
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.process = None
        self.file = cStringIO.StringIO()

        full_scale = (1 << (bits_per_sample - 1)) - 1
        f1 = 441.0
        a1 = 0.61
        f2 = 661.5
        a2 = 0.37
        delta1 = 2.0 * math.pi / (self.sample_rate / f1)
        delta2 = 2.0 * math.pi / (self.sample_rate / f2)
        theta1 = theta2 = 0.0
        channel = []
        for i in range(pcm_frames):
            channel.append(int(((a1 * math.sin(theta1) + a2 *
                                 math.sin(theta2)) * full_scale) + 0.5) +
                           ((ord(os.urandom(1)) >> 4) - 8))
            theta1 += delta1
            theta2 += delta2

        self.file.write(
            audiotools.FrameList.from_channels(
                [channel] * channels).string(bits_per_sample))

        self.file.seek(0, 0)

PATTERN01 = [1, -1]
PATTERN02 = [1, 1, -1]
PATTERN03 = [1, -1, -1]
PATTERN04 = [1, -1, 1, -1]
PATTERN05 = [1, -1, -1, 1]
PATTERN06 = [1, -1, 1, 1, -1]
PATTERN07 = [1, -1, -1, 1, -1]


def fsd8(pattern, reps):
    # FIXME - not quite accurate
    values = {1: 127, -1: -128}
    return FrameListReader([values[p] for p in pattern] * reps,
                           44100, 1, 8)


def fsd16(pattern, reps):
    values = {1: 32767, -1: -32768}
    return FrameListReader([values[p] for p in pattern] * reps,
                           44100, 1, 16)


def fsd24(pattern, reps):
    values = {1: 8388607, -1: -8388608}
    return FrameListReader([values[p] for p in pattern] * reps,
                           44100, 1, 24)
