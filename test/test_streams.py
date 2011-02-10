#!/usr/bin/python

import audiotools
import cStringIO
import math
import os
from hashlib import md5

#these are test stream generators using stream formulas
#taken from the FLAC reference encoder
#but converted to PCMReaders for more general use


class FrameListReader:
    def __init__(self, samples, sample_rate, channels, bits_per_sample,
                 channel_mask = None):
        import audiotools.pcm

        self.framelist = audiotools.pcm.from_list(samples,
                                                  channels,
                                                  bits_per_sample,
                                                  True)
        self.sample_rate = sample_rate
        self.channels = channels
        if (channel_mask is None):
            self.channel_mask = audiotools.ChannelMask.from_channels(channels)
        else:
            self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample

    def read(self, bytes):
        (framelist, self.framelist) = self.framelist.split(
            self.framelist.frame_count(bytes))
        return framelist

    def close(self):
        pass


class MD5Reader:
    def __init__(self, pcmreader):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.channel_mask = pcmreader.channel_mask
        self.bits_per_sample = pcmreader.bits_per_sample
        self.md5 = md5()

    def __repr__(self):
        return "MD5Reader(%s,%s,%s)" % (self.sample_rate,
                                        self.channels,
                                        self.bits_per_sample)

    def read(self, bytes):
        framelist = self.pcmreader.read(bytes)
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


class Sine8_Mono:
    def __init__(self,
                 pcm_frames,
                 sample_rate,
                 f1, a1, f2, a2):
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.full_scale = 0x7F
        self.delta1 = 2 * math.pi / (sample_rate / f1)
        self.delta2 = 2 * math.pi / (sample_rate / f2)
        self.theta1 = self.theta2 = 0.0

        self.original_frames = pcm_frames
        self.pcm_frames = pcm_frames
        self.sample_rate = sample_rate
        self.channels = 1
        self.channel_mask = 0x4
        self.bits_per_sample = 8
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 1, 8, False, False)
        self.md5 = md5()

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            wave.append(int(((self.a1 * math.sin(self.theta1) + self.a2 *
                              math.sin(self.theta2)) * self.full_scale) + 0.5))
            self.theta1 += self.delta1
            self.theta2 += self.delta2
        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def reset(self):
        self.theta1 = self.theta2 = 0.0
        self.md5 = md5()
        self.pcm_frames = self.original_frames

    def close(self):
        self.pcm_frames = 0

    def __repr__(self):
        return "Sine8_Mono(%s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2))


class Sine8_Stereo(Sine8_Mono):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.fmult = fmult
        self.full_scale = 0x7F
        self.delta1 = 2 * math.pi / (sample_rate / f1)
        self.delta2 = 2 * math.pi / (sample_rate / f2)
        self.theta1 = self.theta2 = 0.0

        self.original_frames = pcm_frames
        self.pcm_frames = pcm_frames
        self.sample_rate = sample_rate
        self.channels = 2
        self.channel_mask = 0x3
        self.bits_per_sample = 8
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 2, 8, False, False)
        self.md5 = md5()

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            wave.append(int(((self.a1 * math.sin(self.theta1) + self.a2 *
                              math.sin(self.theta2)) * self.full_scale) + 0.5))
            wave.append(int((-(self.a1 * math.sin(self.theta1 * self.fmult) +
                               self.a2 *
                               math.sin(self.theta2 * self.fmult)) *
                              self.full_scale) +
                            0.5))
            self.theta1 += self.delta1
            self.theta2 += self.delta2

        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

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
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.full_scale = 0x7FFF
        self.delta1 = 2 * math.pi / (sample_rate / f1)
        self.delta2 = 2 * math.pi / (sample_rate / f2)
        self.theta1 = self.theta2 = 0.0

        self.original_frames = pcm_frames
        self.pcm_frames = pcm_frames
        self.sample_rate = sample_rate
        self.channels = 1
        self.channel_mask = 0x4
        self.bits_per_sample = 16
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 1, 16, False, False)
        self.md5 = md5()

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            wave.append(int(((self.a1 * math.sin(self.theta1) + self.a2 *
                              math.sin(self.theta2)) * self.full_scale) + 0.5))
            self.theta1 += self.delta1
            self.theta2 += self.delta2
        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def __repr__(self):
        return "Sine16_Mono(%s, %s, %s, %s, %s, %s)" % \
            (repr(self.pcm_frames),
             repr(self.sample_rate),
             repr(self.f1),
             repr(self.a1),
             repr(self.f2),
             repr(self.a2))


class Sine16_Stereo(Sine8_Mono):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.fmult = fmult
        self.full_scale = 0x7FFF
        self.delta1 = 2 * math.pi / (sample_rate / f1)
        self.delta2 = 2 * math.pi / (sample_rate / f2)
        self.theta1 = self.theta2 = 0.0

        self.original_frames = pcm_frames
        self.pcm_frames = pcm_frames
        self.sample_rate = sample_rate
        self.channels = 2
        self.channel_mask = 0x3
        self.bits_per_sample = 16
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 2, 16, False, False)
        self.md5 = md5()

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            wave.append(int(((self.a1 * math.sin(self.theta1) + self.a2 *
                              math.sin(self.theta2)) * self.full_scale) + 0.5))
            wave.append(int((-(self.a1 * math.sin(self.theta1 * self.fmult) +
                               self.a2 *
                               math.sin(self.theta2 * self.fmult)) *
                              self.full_scale) +
                            0.5))
            self.theta1 += self.delta1
            self.theta2 += self.delta2

        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

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
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.full_scale = 0x7FFFFF
        self.delta1 = 2 * math.pi / (sample_rate / f1)
        self.delta2 = 2 * math.pi / (sample_rate / f2)
        self.theta1 = self.theta2 = 0.0

        self.original_frames = pcm_frames
        self.pcm_frames = pcm_frames
        self.sample_rate = sample_rate
        self.channels = 1
        self.channel_mask = 0x4
        self.bits_per_sample = 24
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 1, 24, False, False)
        self.md5 = md5()

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            wave.append(int(((self.a1 * math.sin(self.theta1) + self.a2 *
                              math.sin(self.theta2)) * self.full_scale) + 0.5))
            self.theta1 += self.delta1
            self.theta2 += self.delta2

        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

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
        self.f1 = f1
        self.a1 = a1
        self.f2 = f2
        self.a2 = a2
        self.fmult = fmult
        self.full_scale = 0x7FFFFF
        self.delta1 = 2 * math.pi / (sample_rate / f1)
        self.delta2 = 2 * math.pi / (sample_rate / f2)
        self.theta1 = self.theta2 = 0.0

        self.original_frames = pcm_frames
        self.pcm_frames = pcm_frames
        self.sample_rate = sample_rate
        self.channels = 2
        self.channel_mask = 0x3
        self.bits_per_sample = 24
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("", 2, 24, False, False)
        self.md5 = md5()

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            wave.append(int(((self.a1 * math.sin(self.theta1) + self.a2 *
                              math.sin(self.theta2)) * self.full_scale) + 0.5))
            wave.append(int((-(self.a1 * math.sin(self.theta1 * self.fmult) +
                               self.a2 *
                               math.sin(self.theta2 * self.fmult)) *
                              self.full_scale) +
                            0.5))
            self.theta1 += self.delta1
            self.theta2 += self.delta2

        framelist = audiotools.pcm.from_list(wave,
                                             self.channels,
                                             self.bits_per_sample,
                                             self.signed)
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

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
        self.signed = True
        self.sample_frame = audiotools.pcm.FrameList("",
                                                     self.channels,
                                                     self.bits_per_sample,
                                                     False,
                                                     False)
        self.md5 = md5()

    def read(self, bytes):
        frames = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
            frames.append(
                audiotools.pcm.from_list(
                    [int(round(max_value *
                               math.sin((((math.pi * 2) *
                                          (self.i % count))) / count)))
                     for (max_value, count) in zip(self.channel_max_values,
                                                   self.channel_counts)],
                    self.channels,
                    self.bits_per_sample,
                    True))
            self.i += 1
        if (len(frames) > 0):
            framelist = audiotools.pcm.from_frames(frames)
        else:
            framelist = self.sample_frame
        self.pcm_frames -= framelist.frames
        self.md5.update(framelist.to_bytes(False, True))
        return framelist

    def reset(self):
        self.i = 0
        self.pcm_frames = self.total_frames
        self.md5 = md5()

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def close(self):
        self.pcm_frames = 0

    def __repr__(self):
        return "Simple_Sine(%s, %s, %s, %s, %s, %s)" % \
            (self.pcm_frames,
             self.sample_rate,
             self.channel_mask,
             self.bits_per_sample,
             repr(self.channel_max_values),
             repr(self.channel_counts))


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

    def read(self, bytes):
        wave = []
        for i in xrange(min(self.sample_frame.frame_count(bytes),
                            self.pcm_frames)):
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

    def reset(self):
        self.i = 0
        self.pcm_frames = self.total_frames
        self.md5 = md5()

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

    def close(self):
        self.pcm_frames = 0

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
        for i in xrange(pcm_frames):
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
    #FIXME - not quite accurate
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
