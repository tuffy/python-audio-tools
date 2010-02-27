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
    def __init__(self, samples, sample_rate, channels, bits_per_sample):
        import audiotools.pcm

        self.framelist = audiotools.pcm.from_list(samples,
                                                  channels,
                                                  bits_per_sample,
                                                  True)
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

    def read(self, bytes):
        (framelist,self.framelist) = self.framelist.split(
            self.framelist.frame_count(bytes))
        return framelist

    def close(self):
        pass

class MD5Reader:
    def __init__(self, pcmreader):
        self.pcmreader = pcmreader
        self.sample_rate = pcmreader.sample_rate
        self.channels = pcmreader.channels
        self.bits_per_sample = pcmreader.bits_per_sample
        self.md5 = md5()

    def __repr__(self):
        return "MD5Reader(%s,%s,%s)" % (self.sample_rate,
                                        self.channels,
                                        self.bits_per_sample)

    def read(self, bytes):
        framelist = self.pcmreader.read(bytes)
        self.md5.update(framelist.to_bytes(False,True))
        return framelist

    def close(self):
        self.pcmreader.close()

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

class ShortStream(MD5Reader):
    def __init__(self,samples,sample_rate,channels,bits_per_sample):
        MD5Reader.__init__(self,
                           FrameListReader(samples,
                                           sample_rate,
                                           channels,
                                           bits_per_sample))

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
        self.wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            self.wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        MD5Reader.__init__(self,
                           FrameListReader(self.wave,
                                           sample_rate,
                                           1,
                                           8))

    def reset(self):
        self.pcmreader = FrameListReader(self.wave,
                                         self.sample_rate,
                                         1,
                                         8)
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
        self.options = [f1,a2,f2,a2,fmult]
        full_scale = 0x7F
        self.wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            self.wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            self.wave.append(int((-(a1 * math.sin(theta1 * fmult) + a2 * math.sin(theta2 * fmult)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        MD5Reader.__init__(self,
                           FrameListReader(self.wave,
                                           sample_rate,
                                           2,
                                           8))

    def reset(self):
        self.pcmreader = FrameListReader(self.wave,
                                         self.sample_rate,
                                         2,
                                         8)
        self.md5 = md5()

    def __repr__(self):
        return "Sine(%s,%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample,
             ",".join(map(repr,self.options)))

class Sine16_Mono(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        self.options = [f1,a2,f2,a2]
        full_scale = 0x7FFF
        self.wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            self.wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        MD5Reader.__init__(self,
                           FrameListReader(self.wave,
                                           sample_rate,
                                           1,
                                           16))

    def reset(self):
        self.pcmreader = FrameListReader(self.wave,
                                         self.sample_rate,
                                         1,
                                         16)
        self.md5 = md5()

    def __repr__(self):
        return "Sine(%s,%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample,
             ",".join(map(repr,self.options)))

class Sine16_Stereo(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.options = [f1,a2,f2,a2,fmult]
        full_scale = 0x7FFF
        self.wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            self.wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            self.wave.append(int((-(a1 * math.sin(theta1 * fmult) + a2 * math.sin(theta2 * fmult)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        MD5Reader.__init__(self,
                           FrameListReader(self.wave,
                                           sample_rate,
                                           2,
                                           16))

    def reset(self):
        self.pcmreader = FrameListReader(self.wave,
                                         self.sample_rate,
                                         2,
                                         16)
        self.md5 = md5()

    def __repr__(self):
        return "Sine(%s,%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample,
             ",".join(map(repr,self.options)))

class Sine24_Mono(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        self.options = [f1,a2,f2,a2]
        full_scale = 0x7FFFFF
        self.wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            self.wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        MD5Reader.__init__(self,
                           FrameListReader(self.wave,
                                           sample_rate,
                                           1,
                                           24))

    def reset(self):
        self.pcmreader = FrameListReader(self.wave,
                                         self.sample_rate,
                                         1,
                                         24)
        self.md5 = md5()

    def __repr__(self):
        return "Sine(%s,%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample,
             ",".join(map(repr,self.options)))

class Sine24_Stereo(MD5Reader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.options = [f1,a2,f2,a2,fmult]
        full_scale = 0x7FFFFF
        self.wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            self.wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            self.wave.append(int((-(a1 * math.sin(theta1 * fmult) + a2 * math.sin(theta2 * fmult)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        MD5Reader.__init__(self,
                           FrameListReader(self.wave,
                                           sample_rate,
                                           2,
                                           24))

    def reset(self):
        self.pcmreader = FrameListReader(self.wave,
                                         self.sample_rate,
                                         2,
                                         24)
        self.md5 = md5()

    def __repr__(self):
        return "Sine(%s,%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample,
             ",".join(map(repr,self.options)))

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
    return FrameListReader([values[p] for p in pattern] * reps,
                           44100,1,8)

def fsd16(pattern, reps):
    values = {1:32767,-1:-32768}
    return FrameListReader([values[p] for p in pattern] * reps,
                           44100,1,16)

def fsd24(pattern, reps):
    values = {1:8388607,-1:-8388608}
    return FrameListReader([values[p] for p in pattern] * reps,
                           44100,1,24)

