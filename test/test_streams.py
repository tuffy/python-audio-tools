#!/usr/bin/python

import audiotools
import cStringIO
import math
import os
from hashlib import md5

#these are test stream generators using stream formulas
#taken from the FLAC reference encoder
#but converted to PCMReaders for more general use

class MD5Reader(audiotools.PCMReader):
    def __init__(self, file, sample_rate, channels, bits_per_sample,
                 process=None):
        audiotools.PCMReader.__init__(self,
                                      file=file,
                                      sample_rate=sample_rate,
                                      channels=channels,
                                      bits_per_sample=bits_per_sample,
                                      process=None)
        self.md5 = md5()

    def __repr__(self):
        return "MD5Reader(%s,%s,%s)" % (self.sample_rate,
                                        self.channels,
                                        self.bits_per_sample)

    def read(self, bytes):
        data = audiotools.PCMReader.read(self,bytes)
        self.md5.update(data)
        return data

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

class ShortStream(MD5Reader):
    def __init__(self,samples,sample_rate,channels,bits_per_sample):
        file = cStringIO.StringIO()
        file.write(audiotools.FrameList(samples,channels).string(bits_per_sample))
        file.seek(0,0)
        MD5Reader.__init__(self,file,sample_rate,channels,bits_per_sample)

class Generate01(ShortStream):
    def __init__(self,sample_rate):
        ShortStream.__init__(self,[-32768],sample_rate,1,16)

class Generate02(ShortStream):
    def __init__(self,sample_rate):
        ShortStream.__init__(self,[-32768,32767],sample_rate,2,16)

class Generate03(ShortStream):
    def __init__(self,sample_rate):
        ShortStream.__init__(self,[-25,0,25,50,100],sample_rate,1,16)

class Generate04(ShortStream):
    def __init__(self,sample_rate):
        ShortStream.__init__(self,[-25,500,0,400,25,300,50,200,100,100],
                             sample_rate,2,16)

class Sine8_Mono(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        self.options = [f1,a2,f2,a2]
        full_scale = 0x7F
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.wave = audiotools.FrameList(wave,1).string(8)
        MD5Reader.__init__(self,
                           cStringIO.StringIO(self.wave),
                           sample_rate,
                           1,
                           8)

    def reset(self):
        self.file = cStringIO.StringIO(self.wave)
        self.md5 = md5()

    def __repr__(self):
        return "Sine(%s,%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample,
             ",".join(map(repr,self.options)))

class Sine8_Stereo(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        full_scale = 0x7F
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            wave.append(int((-(a1 * math.sin(theta1 * fmult) + a2 * math.sin(theta2 * fmult)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2
        self.wave = audiotools.FrameList(wave,2).string(8)
        MD5Reader.__init__(self,
                           cStringIO.StringIO(self.wave),
                           sample_rate,
                           2,
                           8)

    def reset(self):
        self.file = cStringIO.StringIO(self.wave)
        self.md5 = md5()

class Sine16_Mono(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        full_scale = 0x7FFF
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.wave = audiotools.FrameList(wave,1).string(16)
        MD5Reader.__init__(self,
                           cStringIO.StringIO(self.wave),
                           sample_rate,
                           1,
                           16)

    def reset(self):
        self.file = cStringIO.StringIO(self.wave)
        self.md5 = md5()

class Sine16_Stereo(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        full_scale = 0x7FFF
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            wave.append(int((-(a1 * math.sin(theta1 * fmult) + a2 * math.sin(theta2 * fmult)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.wave = audiotools.FrameList(wave,2).string(16)
        MD5Reader.__init__(self,
                           cStringIO.StringIO(self.wave),
                           sample_rate,
                           2,
                           16)

    def reset(self):
        self.file = cStringIO.StringIO(self.wave)
        self.md5 = md5()

class Sine24_Mono(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        full_scale = 0x7FFFFF
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.wave = audiotools.FrameList(wave,1).string(24)
        MD5Reader.__init__(self,
                           cStringIO.StringIO(self.wave),
                           sample_rate,
                           1,
                           24)
    def reset(self):
        self.file = cStringIO.StringIO(self.wave)
        self.md5 = md5()

class Sine24_Stereo(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        full_scale = 0x7FFFFF
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            wave.append(int((-(a1 * math.sin(theta1 * fmult) + a2 * math.sin(theta2 * fmult)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.wave = audiotools.FrameList(wave,2).string(24)
        MD5Reader.__init__(self,
                           cStringIO.StringIO(self.wave),
                           sample_rate,
                           2,
                           24)

    def reset(self):
        self.file = cStringIO.StringIO(self.wave)
        self.md5 = md5()

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
            channel.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5) + ((ord(os.urandom(1)) >> 4) - 8))
            theta1 += delta1
            theta2 += delta2

        self.file.write(audiotools.FrameList.from_channels([channel] * channels).string(bits_per_sample))

        self.file.seek(0,0)

PATTERN01 = [1,-1]
PATTERN02 = [1,1,-1]
PATTERN03 = [1,-1,-1]
PATTERN04 = [1,-1,1,-1]
PATTERN05 = [1,-1,-1,1]
PATTERN06 = [1,-1,1,1,-1]
PATTERN07 = [1,-1,-1,1,-1]

def fsd8(pattern, reps):
    #FIXME - not quite accurate
    values = {1:127,-1:-128}
    return audiotools.FrameList([values[p] for p in pattern],1).string(8) * reps

def fsd16(pattern, reps):
    values = {1:32767,-1:-32768}
    return audiotools.FrameList([values[p] for p in pattern],1).string(16) * reps

def fsd24(pattern, reps):
    values = {1:8388607,-1:-8388608}
    return audiotools.FrameList([values[p] for p in pattern],1).string(24) * reps

