#!/usr/bin/python

import audiotools
import cStringIO
import math

#these are test stream generators using stream formulas
#taken from the FLAC reference encoder
#but converted to PCMReaders for more general use

class Sine8_Mono(audiotools.PCMReader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        self.sample_rate = sample_rate
        self.channels = 1
        self.bits_per_sample = 8
        self.process = None
        self.file = cStringIO.StringIO()

        full_scale = 0x7F
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.file.write(audiotools.FrameList(wave,1).string(8))

        self.file.seek(0,0)

class Sine8_Stereo(audiotools.PCMReader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.sample_rate = sample_rate
        self.channels = 2
        self.bits_per_sample = 8
        self.process = None
        self.file = cStringIO.StringIO()

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

        self.file.write(audiotools.FrameList(wave,2).string(8))

        self.file.seek(0,0)

class Sine16_Mono(audiotools.PCMReader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        self.sample_rate = sample_rate
        self.channels = 1
        self.bits_per_sample = 16
        self.process = None
        self.file = cStringIO.StringIO()

        full_scale = 0x7FFF
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.file.write(audiotools.FrameList(wave,1).string(16))

        self.file.seek(0,0)

class Sine16_Stereo(audiotools.PCMReader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.sample_rate = sample_rate
        self.channels = 2
        self.bits_per_sample = 16
        self.process = None
        self.file = cStringIO.StringIO()

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

        self.file.write(audiotools.FrameList(wave,2).string(16))

        self.file.seek(0,0)

class Sine24_Mono(audiotools.PCMReader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2):
        self.sample_rate = sample_rate
        self.channels = 1
        self.bits_per_sample = 24
        self.process = None
        self.file = cStringIO.StringIO()

        full_scale = 0x7FFFFF
        wave = []
        delta1 = 2 * math.pi / (sample_rate / f1)
        delta2 = 2 * math.pi / (sample_rate / f2)
        theta1 = theta2 = 0.0
        for i in xrange(pcm_frames):
            wave.append(int(((a1 * math.sin(theta1) + a2 * math.sin(theta2)) * full_scale) + 0.5))
            theta1 += delta1
            theta2 += delta2

        self.file.write(audiotools.FrameList(wave,1).string(24))

        self.file.seek(0,0)

class Sine24_Stereo(audiotools.PCMReader):
    def __init__(self, pcm_frames, sample_rate,
                 f1, a1, f2, a2, fmult):
        self.sample_rate = sample_rate
        self.channels = 2
        self.bits_per_sample = 24
        self.process = None
        self.file = cStringIO.StringIO()

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

        self.file.write(audiotools.FrameList(wave,2).string(24))

        self.file.seek(0,0)
