#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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


import audiotools
import audiotools.pcmstream
import tempfile
import sys
import os
import random
import cStringIO
import unittest
import decimal as D
import subprocess
import filecmp
import gettext
import time

gettext.install("audiotools",unicode=True)

(METADATA,PCM,FRAMELIST,EXECUTABLE,CUESHEET,IMAGE,FLAC,CUSTOM) = range(8)
CASES = set([METADATA,PCM,FRAMELIST,EXECUTABLE,CUESHEET,IMAGE,FLAC])

def nothing(self):
    pass

def TEST_METADATA(function):
    if (METADATA not in CASES):
        return nothing
    else:
        return function

def TEST_PCM(function):
    if (PCM not in CASES):
        return nothing
    else:
        return function

def TEST_FRAMELIST(function):
    if (FRAMELIST not in CASES):
        return nothing
    else:
        return function

def TEST_EXECUTABLE(function):
    if (EXECUTABLE not in CASES):
        return nothing
    else:
        return function

def TEST_CUESHEET(function):
    if (CUESHEET not in CASES):
        return nothing
    else:
        return function

def TEST_IMAGE(function):
    if (IMAGE not in CASES):
        return nothing
    else:
        return function

def TEST_FLAC(function):
    if (FLAC not in CASES):
        return nothing
    else:
        return function

def TEST_CUSTOM(function):
    if (CUSTOM not in CASES):
        return nothing
    else:
        return function


try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

Con = audiotools.Con

#probstat does this better, but I don't want to require that
#for something used only rarely
def Combinations(items, n):
    if (n == 0):
        yield []
    else:
        for i in xrange(len(items)):
            for combos in Combinations(items[i + 1:], n - 1):
                yield [items[i]] + combos

class BLANK_PCM_Reader:
    #length is the total length of this PCM stream, in seconds
    def __init__(self, length,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = length
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.total_size = length * sample_rate * channels * bits_per_sample / 8
        self.current_size = self.total_size

    def read(self, bytes):
        if (self.current_size > 0):
            if (self.bits_per_sample > 8):
                buffer = ('\x01\x00' * (min(bytes,self.current_size) / 2)) + \
                          '\x00' * (min(bytes,self.current_size) % 2)
            else:
                buffer = chr(0) * (min(bytes,self.current_size))

            self.current_size -= len(buffer)
            return buffer
        else:
            return ""

    def close(self):
        pass

class EXACT_BLANK_PCM_Reader(BLANK_PCM_Reader):
    def __init__(self, pcm_frames,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = pcm_frames * sample_rate
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.total_size = pcm_frames * channels * bits_per_sample / 8
        self.current_size = self.total_size

#this sends out random samples instead of a bunch of identical ones
class RANDOM_PCM_Reader(BLANK_PCM_Reader):
    def __init__(self, length,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        BLANK_PCM_Reader.__init__(self,length,
                                  sample_rate,channels,bits_per_sample)
        self.md5 = md5()

    def read(self, bytes):
        import audiotools.pcm

        if (self.current_size > 0):
            framelist = audiotools.pcm.FrameList(
                os.urandom(min(bytes,self.current_size)),
                self.channels,
                self.bits_per_sample,
                True,True)
            s = framelist.to_bytes(False)
            self.md5.update(s)
            self.current_size -= len(s)
            return framelist
        else:
            return audiotools.pcm.FrameList("",
                                            self.channels,
                                            self.bits_per_sample,
                                            True,True)

    def digest(self):
        return self.md5.digest()

    def hexdigest(self):
        return self.md5.hexdigest()

class EXACT_RANDOM_PCM_Reader(RANDOM_PCM_Reader):
    def __init__(self, pcm_frames,
                 sample_rate=44100,channels=2,bits_per_sample=16):
        self.length = pcm_frames * sample_rate
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample

        self.total_size = pcm_frames * channels * bits_per_sample / 8
        self.current_size = self.total_size

        self.md5 = md5()

    def __repr__(self):
        return "EXACT_RANDOM_PCM_Reader(%s,%s,%s)" % \
            (self.sample_rate,
             self.channels,
             self.bits_per_sample)

#this not only sends out random samples,
#but the amount sent on each read() is also random
#between 1 and audiotools.BUFFER_SIZE * 2
class VARIABLE_PCM_Reader(RANDOM_PCM_Reader):
    def read(self, bytes):
        if (self.current_size > 0):
            buffer = os.urandom(min(
                random.randint(1,audiotools.BUFFER_SIZE * 2),
                self.current_size))
            self.md5.update(buffer)
            self.current_size -= len(buffer)
            return buffer
        else:
            return ""

class PCM_Count:
    def __init__(self):
        self.count = 0

    def write(self, bytes):
        self.count += len(bytes)

    def __len__(self):
        return self.count

class DummyMetaData(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"Track Name",
                                     #track_name=u"T\u2604rack Name",
                                     track_number=5,
                                     album_number=2,
                                     album_name=u"Album Name",
                                     artist_name=u"Artist Name",
                                     performer_name=u"Performer",
                                     composer_name=u"Composer",
                                     conductor_name=u"Conductor",
                                     ISRC=u"US-PR3-08-12345",
                                     copyright=u"Copyright Attribution",
                                     year=u"2008",
                                     publisher=u"Test Records Inc.",
                                     #comment=u"Comment")
                                     comment=u"C\u2604mment")

    @classmethod
    def supports_images(cls):
        return True

class SmallDummyMetaData(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"Track Name",
                                     artist_name=u"Artist Name",
                                     year=u'2008',
                                     performer_name=u"Performer",
                                     track_number=5,
                                     album_name=u"Album Name",
                                     composer_name=u"Composer",
                                     album_number=6,
                                     comment=u"Comment")

    @classmethod
    def supports_images(cls):
        return True

class DummyMetaData2(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(self,
                                     track_name=u"New Track Name",
                                     track_number=6,
                                     track_total=10,
                                     album_number=3,
                                     album_total=4,
                                     album_name=u"New Album Name",
                                     artist_name=u"New Artist Name",
                                     performer_name=u"New Performer",
                                     composer_name=u"New Composer",
                                     conductor_name=u"New Conductor",
                                     ISRC=u"US-PR3-08-54321",
                                     copyright=u"Copyright Attribution 2",
                                     year=u"2007",
                                     publisher=u"Testing Records Inc.")

    @classmethod
    def supports_images(cls):
        return True

TEST_LENGTH = 30
SHORT_LENGTH = 5

TEST_COVER1 = \
"""eJzt1H1M0mkcAPAH0bSXZT/R6BLpxNJOz4rMXs7UP86Xq+AcQ5BCdNMLgwQ6EU0qu9tdm4plLb0p
mG62Uf7yZWpZgEpnvmTmHBmQChiSaGZUpEmKcdTt1nb3z/XPbbf1ebbnj+/3eb7Py549jkeOx2DN
/rh9cQCBQIDvnA04jGBt7HEWEwAiEQQDADzAB45R8C1wQ7q6uiLdnJ2bm9sy91Ue7k6eK1cuXwV5
enlBnhCEWotBo7zX+0DQOv916/38NmzYgELjNuKwGzHYDdj3RRDOqe7L3Fd7eKzGekPe2E/muA0g
D8QsYhaJwAEXCIGEEI4ugAEIgAQuSPCRc4euHggXpDO7aQ0CIFxdXFyQ7w/6gTPh6rYM8vJ3R3nj
8CSf7c5h3n8lP3ofhf4ZHQGrkAjn6kgIRAML7e/5zz77z/nfxDSKWK20hYHeTUNHW5qFC/jmlvoR
Ra5sei8Lvipud4Dzy89/Ws105Vr2Dvr96NLgCRotL3e7LO4O+jCVgQ+ztY6LM1UUsmWzKAqFNTWY
05cy95dstGnPWEOlcYOcK7A5juKtqpg1pzbxtovTYZaSq89WCXGRgqzguWe2FYcX6rJKSrN1Wxl3
d9La4tEFoyNGB+gb1jdRs9UnpmsycHpSFry5RpyhTjE/IZKD9Xrt1z22oQucVzdPMM4MluSdnZLK
lEnDzZpHLyUaHkGAZkpyufGCmHcaVvWL1u6+W9HoJ6k/U/vplF2CWeK63JdWrtHQFNMVo4rt9yEl
k/CQHh+ZQHo2JLlsEoYG+Z2LvKZJN7HHi6Yqj5972hBSITbXVplrYeaffvgiJyl0NHNe6c8/u1pg
vxTkbZrHh5drLOrdwzIVM4urE+OEMKuwhRtRwtA+cP/JMEk+/Yvlhth57VncDEYTdTGIf71b0djf
o2AzFa11PcTUxKHEIQbELTpNKy//bajTVuJnbGNrMSbxyLYbOVJ5bdOuEIVOm6hOVFP4FEpuWPRw
dYrygkc9umdvwL7r3Y+eXVePKs5QKMZDMkm+JWoTJaZrQBKu3fk8gYxfICeQwsDlV0tbesvsvVZq
C+fe29D1RCoX/fixkdM4viQwdLYw+hZDKcR8fNTTmuCiNHYDMzBD86BYPRW+fkAzxv+lcC7Dwj2k
qM6dgRvl13Ke3oiZC8MnJJIJ+U1+c7rFNxf//UtCVL7u4N/f7QB7H/xYz/N8MMPhNTJaGu4pO2Ql
ieqjWF7y4pHiQ/YAmF0wDSumA4UvNMW9UTQDOcMchbwQJyqdME2F8bfMZG2zveESJdmG27JYmVSR
A0snBUmEhF8HyWOnBJFuN/Osp1EmXwwxaMsITc3bYqT1K0VsvV1EZSmyOLGp2fSChfEZIlYQG5nf
kkie8GzY2mdHB5VM8ji8WjtmlfxYc2Dd0Yc60dxxG136UOWjDc8b2mEbimL0MpocoDpb0rCv2awg
RvvpJoYf2QWF6avT6cIQWQ6/QSeJQiWUMoqYYqmut1Ro8b87IbcwGiYwkwGU+ic0eaXl4NXK0YW6
AxcvpsgrfbMNjb49FXCtqFRFGOiYLrA+0yFZ4/bBs1b6nvlw+gqFluJtHrnXoyg84Ss/WcOltxPD
VaiEWxUFhQVVygIGr38MO8MXlB9XTJvfjOLwN1R8JE6/p4xAmGfD9V3Jl+eqLOSwmFwobDE+Lxdt
ijh5aaxfXp9fXZZGm8CkdbcHMi1tEjUDlhzcCb9uF7IlgreGmjS1IJZEmDf5EeKlJj61s7dTLL/V
MUm5WDdmTJ/4/o5L25GmrOKIhwPX+MnxowTb/bd06xU4QDYPtDeVQcdOYU0BlBbDqYPrykhxjOxx
gyzdC154JZq/WsMZrigsXJq+8rDTiEJB+MguB9ikaXsX0aFOmdTxjlZYPcd5rW+Hqfgdwr2Zbcn2
k1cdYPBJUpoSvlUo4b9JrgnoCYyMWNm77Sv1q+fcZrE15Iqnl7rgGg5mPifFQgmCgShpY8rC3NhL
zMtP+eKwIVLxFFz0tKgW/qa83BIY3R1xzp76+6xvJlHaeIDRVrw1ulNq4SxqjtlNcIcoKQTWV40z
o/ez5iJPo7/8tO/0s8/+jxCO4T8AO2LoJg==""".decode('base64').decode('zlib')

TEST_COVER2 = \
"""eJztV4lT00kWDrqzoEiC16JgiGcxoyCDiNFByCggIEdcWQXEcAoZbgmQRE6RS0YIogYEiYwgAcwg
gqIhCYciRs6IHEIiiVwiRwgQQoQcs41bUzvM1O4fsDuvqqv719/3+vXxvVf1SzvlaK2xVnstBALR
sLWxPA2BqMwvN7VVYMbyic0A6NZctHENh0DUNy43FUhe/hYwqRph62Cl+m6N+vpt0K96uOcgkHUY
W8tj/yByhQPBP5B9VzfMTgZhDbF3vqvOsd3wJNer1b7vzXnSoi3mpOGpdWv2VvpWwwoTrE4M5vhf
2ZJ2yuf5130lVRfI19NrvnFIL6ttKz+UX9S3NqLmUFnQ2FEElDJ28Fv5dbQbRyQdr+uInE58/2yM
0x7Z0QG33b1B5XJ8zrpUyPfvVTQJkJdwSJgqGP7af5laCYHhvyEwXAn9nr0C+gN7BfRn2P/FsJ+Z
+aj4uMYUDSSf6IPHL2AIAz19fZ9uX6Yb12LoF+8VFnp7en54c8+itrbWxMQEbSbprouVKaW/3CAe
nY7YPj0j7WMSRK9fv05FxBFFtVI+nhdsip/qY10Kt7Oz25llY36vurq6quoACoUyNAxdnBs1MDBo
ZvN4vF1Zr++3ylNSUmx2v+3vz92mewR3H/AA6WNb7uS7CpFQ6GAmToSZX7XcWYIu4D8LFcgXxcYH
DhwwNqZAqfl/sUdL34dz8kwC3yIWFVKBEw8Oh+fm5qLNFy8QCFKkIEbcZsyx3JmFRikOHmFeHHwh
m2Yaxgp8W7MHYqUDzUIfNsmqqFPvLrGwpKSERqM9ePCgtPTTi2T15n6lUqn54sEZ2kk7Ozc3t3rg
aIztOAy3NxnqiDDxeZXOYDBo7WednXNu3bqPQxkZVYLVe2jOeqngLqA75iWSPake8YpINa9flIrm
QW51ILiL4Vki7vDRo/kUioIbWLEntV65FKi2A4mUglN1rHLK9t1KpbXmGLK9K2nteDz+4bnqvdWe
N7Ky/u7qemlupHlkZpaN4LS0BAQEnIQK4mRCFovF1o3WjxXY7L6xjR8jbrfL2W+Gn3LB3aZQ4Mdd
aqMk5c/4E/qe7XCln7Ff2xYEop47VWyXs1ZdvQvxjb7+NjjcQRI1wIgUscSOOKOxAYKgvKws1yTw
LA4fETHfjhTo24gXxwpgGhrF9dwrX6nnr6JWlVo0HIwcoxAW5uftGdkikciDRQxT81qY6t+1a9f4
Yy1D93yzaHwA3b+LKhPV15eXB4OlgDRKy8sdHNpzjUsYjCg2CT7OHBsZkY9TNkr4z8mm51VhZvOn
rK3ZHz54TmQpZNIcMlkDBkvVPPuzSyeX+52RUVb+j+zh4ODgzZs3l+lVuD72U8oXVWG6QSEh7lUX
mqt8W087AQjLuYu57uft7c1nXSId6UrLhN+mvmKztQzOPYkYf7uwsJCQkPDOI95s3z5aXZ35EVk/
tgAIIEMHCaC7YNtdVAdXV1c9x3yb+OQcj7gaOp3+6NFMQ8Lq8cyCw2E7tTPMgeDMzMxiY2OZeGFL
W1sMELxSZpak+TRUML3pA+/ARYz883AmELyVlRVYivA+zNrCwmJpKmuXNTjL+mtNc3NzZx+e7+/t
PeQvDR/rsNqZJZfLwcM55AUEBrrV4Hzd3d0dHR2Bb3i4uIB/aKjjlpatfFYLAXEJ/w+5TP9bXD/J
X19yc3Jc3mlCx2GjdLSX7QGNZheMXuqJ1CTcjvvxi82JxU48sLWya0tcLrfpmhaHYvqsqMiH9zS4
pqaGTCbXy+fs1HboZtYvTdCamprANpKTk2Eo+YxUEF+gbDElTLNGs928K13OnDmDxWIPag/UxUYH
LBiGFGgMQd85g7P6+AyzLondo8aLiUfrwIOQSCSQkLuTZnrdQoXvax7X1cWBejIz2FjiSOE+8rJY
IlWw5k5iMBg0mvM0mKdL/JCQlpbWveHN7DD73UOM2+nTuInusiLrTFJGBgiKYRE7VbABs4237QnN
gRPNKD/4C0bk5Ia0lx/b71ioecRKehoavlfzEvFr0yyHSgrilhZ4oU5oPiMy0M/PL4AeswheYK77
UWWl0X3FK5GHwFyHquY8LQ8k37qVpOnXkb/1+Nf79zuGyIHbjiQX/d7u7ic/dBYCxW3etIk1+0qn
LPpQsiaDyWxtaTndODExMZ+jmORhE3230utw4eGNCEFpWpN3c8aIlaK33I0g5Ermu9AIVJx8frxL
BxliLwgLCvr5p5+2m7AGU3TeYitGF/pnMsVnbJQIEyQStfSpyO1pkK2BI5XzyrsSFIOSlJu9Xcsk
UGhhW3R07pgSQnDRMTGs4uI9SZqZbFANj6s9A9UAyDU3am6wMbVL6jBgbiqxCQ2t4GGNe1yyvbR1
dL8YAoEOhsFgHq2k0dFRkDxTE8sWNZJlvXfv3uNqZZHivLw8kAmrVaHroNC4+U7rVCj8pEDapOUB
qEBNk0KhUCQS1EYT/P3H7481oDjYFvthGdNDUR/xeVhmUCZ6m56enqQ5MTm5Me1lrjE2W991Q8YJ
LX2XGaVMFD/bpIUciHA6duwYTrDP+WF3Tw+oB3pIJEGxJElMTNyRpOVOHNQOLdAIua7h1E3e5wzq
/E3awbEOyr79+/mPsRwxByV67en6Vyrtph7648ePIf1VxRUVFUzmciK3NzdfmnmuCt/6Ek6tBE9M
pVKBaLKBkckKuZiDiJeHLemVfitxzVa5OAq9TF+9fRpy1RQyBP21/9fU0LTmbz+vmv6GCYYroD86
Q/8LeyX0e/ZK6M+w/z9h5ahFWOF6xsYTVuUy8O8BsbVytHx43PPKPwEw98Hh""".decode('base64').decode('zlib')

TEST_COVER3 = \
"""eJz7f+P/AwYBLzdPNwZGRkYGDyBk+H+bwZmBl5OLm4uDl5uLm4+Pl19YQVRYSEhYXUZOXEFP09BA\nT1NXx9jKy87YzM1cR9ch3NHNxy8oOMjILioxKiDBKzDIH2QIIx8fn7CgsJqoqJq/qa6pP8ng/wEG\nQQ6GFIYUZkZBBiZBRmZBxv9HGMTATkUGLBzsQHEJAUZGNBlmJiNHoIwImnogAIkKYoreYuBhZgRa\nxSzIYM9wpviCpICZQknDjcaLzEnsLrwdsiCuwwSfmS+4O6QFrBRyHF40bmRexHaED8R18FDz+cJ6\nBKYMSZeKsFoV0yOgsgnIuk7wdQg/ULP5wuaCTwvEoga4RUKc/baME5HdA9KVwu7CyXJ8XsMJJPdA\nLVrC0pRy3iEGyXAFMwewp5gcDZ8vMELzBZirMOPzBUkFNCdB/F75gmcCpt8VPCAemQBW1nCTEewk\nsEfk/98EALdspDk=\n""".decode('base64').decode('zlib')

#this is a very large, plain BMP encoded as bz2
HUGE_BMP = \
"""QlpoOTFBWSZTWSpJrRQACVR+SuEoCEAAQAEBEAIIAABAAAEgAAAIoABwU0yMTExApURDRoeppjv2
2uMceMt8M40qoj5nGLjFQkcuWdsL3rW+ugRSA6SFFV4lUR1/F3JFOFCQKkmtFA==""".decode('base64')

#this is an insane amount of different PCM combinations
PCM_COMBINATIONS = (
    (11025,  1, 8), (22050,  1, 8), (32000,  1, 8), (44100,  1, 8),
    (48000,  1, 8), (96000,  1, 8), (192000, 1, 8), (11025,  2, 8),
    (22050,  2, 8), (32000,  2, 8), (44100,  2, 8), (48000,  2, 8),
    (96000,  2, 8), (192000, 2, 8), (11025,  6, 8), (22050,  6, 8),
    (32000,  6, 8), (44100,  6, 8), (48000,  6, 8), (96000,  6, 8),
    (192000, 6, 8), (11025,  1, 16),(22050,  1, 16),(32000,  1, 16),
    (44100,  1, 16),(48000,  1, 16),(96000,  1, 16),(192000, 1, 16),
    (11025,  2, 16),(22050,  2, 16),(32000,  2, 16),(44100,  2, 16),
    (48000,  2, 16),(96000,  2, 16),(192000, 2, 16),(11025,  6, 16),
    (22050,  6, 16),(32000,  6, 16),(44100,  6, 16),(48000,  6, 16),
    (96000,  6, 16),(192000, 6, 16),(11025,  1, 24),(22050,  1, 24),
    (32000,  1, 24),(44100,  1, 24),(48000,  1, 24),(96000,  1, 24),
    (192000, 1, 24),(11025,  2, 24),(22050,  2, 24),(32000,  2, 24),
    (44100,  2, 24),(48000,  2, 24),(96000,  2, 24),(192000, 2, 24),
    (11025,  6, 24),(22050,  6, 24),(32000,  6, 24),(44100,  6, 24),
    (48000,  6, 24),(96000,  6, 24),(192000, 6, 24))

#these are combinations that tend to occur in nature
SHORT_PCM_COMBINATIONS = ((11025,  1, 8), (22050, 1, 8),
                          (22050,  1, 16),(32000, 2, 16),
                          (44100,  1, 16),(44100, 2, 16),
                          (48000,  1, 16),(48000, 2, 16),
                          (48000,  6, 16),
                          (192000, 2, 24),(96000, 6, 24))

class DummyMetaData3(audiotools.MetaData):
    def __init__(self):
        audiotools.MetaData.__init__(
            self,
            track_name=u"Track Name Three",
            track_number=5,
            album_name=u"Album Name",
            artist_name=u"Artist Name",
            performer_name=u"Performer",
            images=[audiotools.Image.new(TEST_COVER1,u'',0)])

    @classmethod
    def supports_images(cls):
        return True

############
#BEGIN TESTS
############

class TestPCMCombinations(unittest.TestCase):
    @TEST_PCM
    def testpcmcombinations(self):
        for (sample_rate,channels,bits_per_sample) in SHORT_PCM_COMBINATIONS:
            reader = BLANK_PCM_Reader(SHORT_LENGTH,
                                      sample_rate, channels,
                                      bits_per_sample)
            counter = PCM_Count()
            audiotools.transfer_data(reader.read,counter.write)
            self.assertEqual(len(counter),reader.total_size)

class TestTextOutput(unittest.TestCase):
    #takes a list of argument strings
    #returns a returnval integer
    #self.stdout and self.stderr are set to file-like cStringIO objects
    def __run_app__(self,arguments):
        sub = subprocess.Popen(arguments,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

        self.stdout = cStringIO.StringIO(sub.stdout.read())
        self.stderr = cStringIO.StringIO(sub.stderr.read())
        sub.stdout.close()
        sub.stderr.close()
        returnval = sub.wait()
        return returnval

    def filename(self,s):
        return s.decode(audiotools.FS_ENCODING,'replace')

    def __check_output__(self,s):
        self.assertEqual(
            self.stdout.readline().decode(audiotools.IO_ENCODING),
            s + unicode(os.linesep))

    def __check_info__(self,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            s + unicode(os.linesep))

    def __check_error__(self,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            u"*** Error: " + s + unicode(os.linesep))

    def __check_warning__(self,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            u"*** Warning: " + s + unicode(os.linesep))

    def __check_usage__(self,executable,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            u"*** Usage: " + executable.decode('ascii') + u" " + s +
            unicode(os.linesep))

class TestAiffAudio(TestTextOutput):
    def DummyMetaData(self):
        return DummyMetaData()

    def DummyMetaData2(self):
        return DummyMetaData2()

    def DummyMetaData3(self):
        return DummyMetaData3()

    def flag_field_values(self):
        return zip(["--name",
                    "--artist",
                    "--performer",
                    "--composer",
                    "--conductor",
                    "--album",
                    "--number",
                    "--track-total",
                    "--album-number",
                    "--album-total",
                    "--ISRC",
                    "--publisher",
                    "--year",
                    "--copyright",
                    "--comment"],
                   ["track_name",
                    "artist_name",
                    "performer_name",
                    "composer_name",
                    "conductor_name",
                    "album_name",
                    "track_number",
                    "track_total",
                    "album_number",
                    "album_total",
                    "ISRC",
                    "publisher",
                    "year",
                    "copyright",
                    "comment"],
                   ["Track Name",
                    "Artist Name",
                    "Performer Name",
                    "Composer Name",
                    "Conductor Name",
                    "Album Name",
                    2,
                    5,
                    3,
                    4,
                    "ISRC-NUM",
                    "Publisher Name",
                    "2008",
                    "Copyright Text",
                    "Some Lengthy Text Comment"])

    def setUp(self):
        self.audio_class = audiotools.AiffAudio

    def __is_lossless__(self):
        short_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            short = self.audio_class.from_pcm(
                short_file.name,
                BLANK_PCM_Reader(5))
            return short.lossless()
        finally:
            short_file.close()

    #this is a basic test of CD-quality audio
    @TEST_PCM
    def testblankencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            self.assertEqual(new_file.channels(),2)
            self.assertEqual(new_file.bits_per_sample(),16)
            self.assertEqual(new_file.sample_rate(),44100)

            if (new_file.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    BLANK_PCM_Reader(TEST_LENGTH)),True)
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assertEqual(
                    (D.Decimal(len(counter) / 4) / 44100).to_integral(),
                    TEST_LENGTH)
                pcm.close()
        finally:
            temp.close()

    @TEST_PCM
    def testrandomencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            reader = VARIABLE_PCM_Reader(TEST_LENGTH)

            new_file = self.audio_class.from_pcm(
                temp.name,reader)

            self.assertEqual(new_file.channels(),2)
            self.assertEqual(new_file.bits_per_sample(),16)
            self.assertEqual(new_file.sample_rate(),44100)

            if (new_file.lossless()):
                md5sum = md5()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,md5sum.update)
                pcm.close()
                self.assertEqual(md5sum.hexdigest(),reader.hexdigest())
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assertEqual(
                    (D.Decimal(len(counter) / 4) / 44100).to_integral(),
                    TEST_LENGTH)
                pcm.close()
        finally:
            temp.close()


    @TEST_PCM
    def testunusualaudio(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            #not all of these combinations will be supported by all formats
            for (sample_rate,channels,bits_per_sample) in SHORT_PCM_COMBINATIONS:
                try:
                    new_file = self.audio_class.from_pcm(
                        temp.name,
                        BLANK_PCM_Reader(SHORT_LENGTH,
                                         sample_rate, channels,
                                         bits_per_sample))
                except audiotools.InvalidFormat:
                    continue


                if (new_file.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        BLANK_PCM_Reader(SHORT_LENGTH,
                                         sample_rate, channels,
                                         bits_per_sample)),
                                     True)

                    #lots of lossy formats convert BPS to 16 bits or float bits
                    #(MP3, Vorbis, etc.)
                    #only check an exact match on lossless
                    self.assertEqual(new_file.bits_per_sample(),
                                     bits_per_sample)
                    self.assertEqual(new_file.channels(),
                                     channels)
                    self.assertEqual(new_file.sample_rate(),sample_rate)
                else:
                    #If files are lossy,
                    #only be sure the lengths are the same.
                    #Everything else is too variable.

                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    pcm.close()
                    self.assertEqual(
                        (D.Decimal(new_file.total_frames()) / \
                         new_file.sample_rate()).to_integral(),
                        SHORT_LENGTH,
                        "conversion mismatch on %sHz, %s channels, %s bps" % \
                            (sample_rate,channels,bits_per_sample))

        finally:
            temp.close()

    @TEST_PCM
    def testwaveconversion(self):
        tempwav = tempfile.NamedTemporaryFile(suffix=".wav")
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp2 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))
            new_file.to_wave(tempwav.name)
            if (new_file.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    audiotools.WaveAudio(tempwav.name).to_pcm()),True)
            else:
                counter = PCM_Count()
                pcm = new_file.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assertEqual(
                    (D.Decimal(len(counter) / 4) / 44100).to_integral(),
                    TEST_LENGTH)
                pcm.close()

            new_file2 = self.audio_class.from_wave(temp2.name,
                                                   tempwav.name)
            if (new_file2.lossless()):
                self.assertEqual(audiotools.pcm_cmp(
                    new_file2.to_pcm(),
                    new_file.to_pcm()),True)
            else:
                counter = PCM_Count()
                pcm = new_file2.to_pcm()
                audiotools.transfer_data(pcm.read,counter.write)
                self.assert_(len(counter) > 0)
                pcm.close()
        finally:
            tempwav.close()
            temp.close()
            temp2.close()


    @TEST_PCM
    def testmassencode(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

        tempfiles = [(tempfile.NamedTemporaryFile(
            suffix="." + audio_class.SUFFIX),
            audio_class) for audio_class in audiotools.TYPE_MAP.values()]

        other_files = [audio_class.from_pcm(temp_file.name,
                                            BLANK_PCM_Reader(SHORT_LENGTH))
                       for (temp_file,audio_class) in tempfiles]
        for audio_file in other_files:
            audio_file.set_metadata(DummyMetaData3())

        try:
            for f in other_files:
                new_file = self.audio_class.from_pcm(
                    temp.name,
                    f.to_pcm())

                new_file.set_metadata(f.get_metadata())

                if (new_file.lossless() and f.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        f.to_pcm()),True,
                                     "PCM mismatch converting %s to %s" % \
                                     (repr(f),repr(new_file)))
                else:
                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    pcm.close()
                    self.assert_(len(counter) > 0)

                new_file_metadata = new_file.get_metadata()
                f_metadata = f.get_metadata()

                if ((new_file_metadata is not None) and
                    (f_metadata is not None)):
                    self.assertEqual(
                        new_file_metadata,
                        f_metadata,
                        "metadata mismatch converting %s to %s (%s != %s)" % \
                        (repr(f),repr(new_file),
                         repr(f_metadata),
                         repr(new_file_metadata)))

                    if (new_file_metadata.supports_images() and
                        f_metadata.supports_images()):
                        self.assertEqual(new_file_metadata.images(),
                                         f_metadata.images())
        finally:
            temp.close()
            for (temp_file,audio_class) in tempfiles:
                temp_file.close()


    #just like testmassencode, but without file suffixes
    @TEST_PCM
    def testmassencode_nonsuffix(self):
        temp = tempfile.NamedTemporaryFile()

        tempfiles = [(tempfile.NamedTemporaryFile(),
                      audio_class) for audio_class in
                     audiotools.TYPE_MAP.values()]

        other_files = [audio_class.from_pcm(temp_file.name,
                                            BLANK_PCM_Reader(SHORT_LENGTH))
                       for (temp_file,audio_class) in tempfiles]
        for audio_file in other_files:
            audio_file.set_metadata(DummyMetaData3())

        try:
            for f in other_files:
                new_file = self.audio_class.from_pcm(
                    temp.name,
                    f.to_pcm())

                new_file.set_metadata(f.get_metadata())

                if (new_file.lossless() and f.lossless()):
                    self.assertEqual(audiotools.pcm_cmp(
                        new_file.to_pcm(),
                        f.to_pcm()),True,
                                     "PCM mismatch converting %s to %s" % \
                                     (repr(f),repr(new_file)))
                else:
                    counter = PCM_Count()
                    pcm = new_file.to_pcm()
                    audiotools.transfer_data(pcm.read,counter.write)
                    pcm.close()
                    self.assert_(len(counter) > 0,
                                 "error converting %s to %s without suffix" % \
                                     (repr(f),repr(new_file)))

                new_file_metadata = new_file.get_metadata()
                f_metadata = f.get_metadata()

                if ((new_file_metadata is not None) and
                    (f_metadata is not None)):
                    self.assertEqual(
                        new_file_metadata,
                        f_metadata,
                        "metadata mismatch converting %s to %s (%s != %s)" % \
                        (repr(f),repr(new_file),
                         repr(f_metadata),
                         repr(new_file_metadata)))

                    if (new_file_metadata.supports_images() and
                        f_metadata.supports_images()):
                        self.assertEqual(new_file_metadata.images(),
                                         f_metadata.images())
        finally:
            temp.close()
            for (temp_file,audio_class) in tempfiles:
                temp_file.close()

    @TEST_PCM
    def testinvalidoutput(self):
        temp_track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp_wave_file = tempfile.NamedTemporaryFile(suffix=".wav")

        temp_track = self.audio_class.from_pcm(
            temp_track_file.name,
            BLANK_PCM_Reader(5))

        temp_wave = audiotools.WaveAudio.from_pcm(
            temp_wave_file.name,
            BLANK_PCM_Reader(5))

        try:
            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_pcm,
                              "/dev/null/foo.%s" % (self.audio_class.SUFFIX),
                              BLANK_PCM_Reader(5))

            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_wave,
                              "/dev/null/foo.%s" % (self.audio_class.SUFFIX),
                              temp_wave_file.name)

            self.assertRaises(audiotools.EncodingError,
                              temp_track.to_wave,
                              "/dev/null/foo.wav")

        finally:
            temp_track_file.close()
            temp_wave_file.close()


    @TEST_METADATA
    def testmetadata(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            metadata = self.DummyMetaData()
            new_file.set_metadata(metadata)
            if (new_file.get_metadata() is not None):
                self.assertEqual(metadata,new_file.get_metadata())
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata,new_file.get_metadata())

                #ensure that setting data from external sources works
                #(this tests the convert() method, mostly)
                metadata2 = self.DummyMetaData2()
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())

                for field in metadata2.__FIELDS__:
                    if (isinstance(getattr(metadata2,field),int)):
                        new_field = getattr(metadata2,field) + 1
                        setattr(metadata2,field,new_field)
                        self.assertEqual(getattr(metadata2,field),new_field)
                    elif (len(getattr(metadata2,field)) > 0):
                        new_field = getattr(metadata2,field) + u"+1"
                        setattr(metadata2,field,new_field)
                        self.assertEqual(getattr(metadata2,field),new_field)
                    else:
                        continue

                    new_file.set_metadata(metadata2)
                    new_file = audiotools.open(temp.name)
                    self.assertEqual(metadata2,new_file.get_metadata())

                #ensure that setting data from the actual format works
                #(this tests that __setattr__/__getattr__ works, mostly)
                new_file.set_metadata(self.DummyMetaData2())
                new_file = audiotools.open(temp.name)
                metadata2 = new_file.get_metadata()
                for field in metadata2.__FIELDS__:
                    if (isinstance(getattr(metadata2,field),int)):
                        new_field = getattr(metadata2,field) + 1
                        setattr(metadata2,field,new_field)
                        self.assertEqual(getattr(metadata2,field),new_field)
                    elif (len(getattr(metadata2,field)) > 0):
                        new_field = getattr(metadata2,field) + u"+1"
                        setattr(metadata2,field,new_field)
                        self.assertEqual(getattr(metadata2,field),new_field)
                    else:
                        continue

                    new_file.set_metadata(metadata2)
                    new_file = audiotools.open(temp.name)
                    self.assertEqual(metadata2,new_file.get_metadata())
        finally:
            temp.close()

    @TEST_METADATA
    def test_metadata_deletion_full(self):
        temp_track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            temp_track = self.audio_class.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            temp_track.set_metadata(DummyMetaData())
            if (temp_track.get_metadata() is not None):
                temp_track = audiotools.open(temp_track_file.name)
                temp_track.delete_metadata()
                metadata = temp_track.get_metadata()
                if (metadata is None):
                    self.assertEqual(metadata,None) #a formality
                else:
                    self.assertEqual(metadata,audiotools.MetaData())
                temp_track = audiotools.open(temp_track_file.name)
                metadata = temp_track.get_metadata()
                if (metadata is None):
                    self.assertEqual(metadata,None) #another formality
                else:
                    self.assertEqual(metadata,audiotools.MetaData())
        finally:
            temp_track_file.close()

    @TEST_METADATA
    def test_metadata_deletion_fields(self):
        temp_track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            temp_track = self.audio_class.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            temp_track.set_metadata(DummyMetaData())
            if (temp_track.get_metadata() is not None):
                for field in audiotools.MetaData.__FIELDS__:
                    temp_track = audiotools.open(temp_track_file.name)
                    metadata = temp_track.get_metadata()
                    if (field in audiotools.MetaData.__INTEGER_FIELDS__):
                        if (getattr(metadata,field) != 0):
                            delattr(metadata,field)
                            temp_track.set_metadata(metadata)
                            metadata = temp_track.get_metadata()
                            self.assertEqual(getattr(metadata,field),0)
                    else:
                        if (getattr(metadata,field) != u''):
                            delattr(metadata,field)
                            temp_track.set_metadata(metadata)
                            metadata = temp_track.get_metadata()
                            self.assertEqual(getattr(metadata,field),u'')

                    delattr(metadata,field) #multiple deletion should be okay
        finally:
            temp_track_file.close()

    @TEST_METADATA
    def testinvalidmetadata(self):
        temp_track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

        orig_stat = os.stat(temp_track_file.name)[0]

        temp_track = self.audio_class.from_pcm(
            temp_track_file.name,
            BLANK_PCM_Reader(5))

        try:
            temp_track.set_metadata(DummyMetaData2())
            if (temp_track.get_metadata() is not None):
                os.chmod(temp_track_file.name,0)
                self.assertRaises(IOError,
                                  temp_track.set_metadata,
                                  DummyMetaData())
                os.chmod(temp_track_file.name,orig_stat)
                temp_track.set_metadata(DummyMetaData())
                os.chmod(temp_track_file.name,0)
                self.assertRaises(IOError,
                                  temp_track.get_metadata)
                os.chmod(temp_track_file.name,orig_stat)
        finally:
            os.chmod(temp_track_file.name,orig_stat)
            temp_track_file.close()

    @TEST_METADATA
    def testimages(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if ((new_file.get_metadata() is not None)
                and (new_file.get_metadata().supports_images())):
                metadata = self.DummyMetaData()
                new_file.set_metadata(metadata)
                self.assertEqual(metadata,new_file.get_metadata())

                image1 = audiotools.Image.new(TEST_COVER1,u'',0)
                image2 = audiotools.Image.new(TEST_COVER2,u'',0)

                metadata.add_image(image1)
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)
                metadata.delete_image(metadata.images()[0])

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(len(metadata.images()),0)
                metadata.add_image(image2)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image2)
                self.assertEqual(metadata.front_covers()[0],image2)
        finally:
            temp.close()

    @TEST_PCM
    def testsplit(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(60))

            if (new_file.lossless()):
                PCM_LENGTHS = [s * 44100 for s in (5,10,15,4,16,10)]

                self.assertEqual(sum(PCM_LENGTHS),
                                 new_file.total_frames())

                for (sub_pcm,pcm_length) in zip(audiotools.pcm_split(
                    new_file.to_pcm(),
                    PCM_LENGTHS),
                                                PCM_LENGTHS):
                    sub_temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
                    try:
                        sub_file = self.audio_class.from_pcm(sub_temp.name,
                                                             sub_pcm)
                        self.assertEqual(sub_file.total_frames(),
                                         pcm_length)

                    finally:
                        sub_temp.close()

                self.assertEqual(audiotools.pcm_cmp(
                    new_file.to_pcm(),
                    audiotools.PCMCat(
                    audiotools.pcm_split(new_file.to_pcm(),PCM_LENGTHS))),
                                 True)

        finally:
            temp.close()


    #much like testmassencode, but using track2track
    @TEST_EXECUTABLE
    def test_track2track_massencode(self):
        base_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            base = self.audio_class.from_pcm(base_file.name,
                                             BLANK_PCM_Reader(SHORT_LENGTH))
            metadata = self.DummyMetaData3()

            base.set_metadata(metadata)
            metadata = base.get_metadata()

            for new_audio_class in audiotools.TYPE_MAP.values():
                temp_file = tempfile.NamedTemporaryFile(
                    suffix="." + new_audio_class.SUFFIX)
                try:
                    subprocess.call(["track2track",
                                     '--no-replay-gain',
                                     "-t",new_audio_class.NAME,
                                     "-o",temp_file.name,
                                     base_file.name])

                    new_file = audiotools.open(temp_file.name)
                    self.assertEqual(new_file.NAME,new_audio_class.NAME)

                    if (base.lossless() and new_file.lossless()):
                        self.assertEqual(audiotools.pcm_cmp(
                                base.to_pcm(),
                                new_file.to_pcm()),True,
                                         "PCM mismatch converting %s to %s" % \
                                             (repr(base.NAME),
                                              repr(new_audio_class.NAME)))
                    else:
                        counter = PCM_Count()
                        pcm = new_file.to_pcm()
                        audiotools.transfer_data(pcm.read,counter.write)
                        self.assert_(len(counter) > 0)

                    new_metadata = new_file.get_metadata()

                    if ((metadata is not None) and
                        (new_metadata is not None)):
                        self.assertEqual(
                        new_metadata,
                        metadata,
                        "metadata mismatch converting %s to %s (%s != %s)" % \
                        (repr(base.NAME),
                         repr(new_audio_class.NAME),
                         repr(metadata),
                         repr(new_metadata)))

                        if (new_metadata.supports_images() and
                            metadata.supports_images()):
                            self.assertEqual(new_metadata.images(),
                                             metadata.images())

                finally:
                    temp_file.close()
        finally:
            base_file.close()

    def __test_track2xmcd__(self, arguments, album_metadata,
                            lossless, has_metadata):

        #these are both collections of live data,
        #which may change as the data on the servers changes
        MUSICBRAINZ_METADATA = \
            {1: audiotools.MetaData(
                    track_name=u'\u65b0\u305f\u306a\u308b\u5192\u967a\u306e\u821e\u53f0\u3078\u3002',
                    track_number=1,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008'),
             2: audiotools.MetaData(
                    track_name=u'\u751f\u6b7b\u3092\u5206\u304b\u3064\u6fc0\u95d8\u306e\u97ff\u304d\u3002',
                    track_number=2,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008'),
             3: audiotools.MetaData(
                    track_name=u'\u5176\u306f\u7d05\u304d\u8ff7\u8def\u306e\u679c\u3066\u3002',
                    track_number=3,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008'),
             4: audiotools.MetaData(
                    track_name=u'\u7a7a\u3067\u307e\u307f\u3048\u308b\u795e\u306e\u4ed4\u3089\u3002',
                    track_number=4,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008'),
             5: audiotools.MetaData(
                    track_name=u'\u96ea\u3068\u6c37\u306e\u54c0\u3057\u307f\u306e\u5148\u3078\u3002',
                    track_number=5,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008'),
             6: audiotools.MetaData(
                    track_name=u'***Secret Sound***',
                    track_number=6,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008'),
             7: audiotools.MetaData(
                    track_name=u'\u5192\u967a\u8005\u305f\u3061\u306e\u5b89\u3089\u304e\u306e\u5834\u3002',
                    track_number=7,
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ 2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    catalog=u'SJMK-0001',
                    year=u'2008')}

        FREEDB_METADATA = \
            {1: audiotools.MetaData(
                    track_name=u'\u65b0\u305f\u306a\u308b\u5192\u967a\u306e\u821e\u53f0\u3078\u3002',
                    track_number=1,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007'),
             2: audiotools.MetaData(
                    track_name=u'\u751f\u6b7b\u3092\u5206\u304b\u3064\u6fc0\u95d8\u306e\u97ff\u304d\u3002',
                    track_number=2,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007'),
             3: audiotools.MetaData(
                    track_name=u'\u5176\u306f\u7d05\u304d\u8ff7\u8def\u306e\u679c\u3066\u3002',
                    track_number=3,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007'),
             4: audiotools.MetaData(
                    track_name=u'\u7a7a\u3067\u307e\u307f\u3048\u308b\u795e\u306e\u4ed4\u3089\u3002',
                    track_number=4,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007'),
             5: audiotools.MetaData(
                    track_name=u'\u96ea\u3068\u6c37\u306e\u54c0\u3057\u307f\u306e\u5148\u3078\u3002',
                    track_number=5,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007'),
             6: audiotools.MetaData(
                    track_name=u'***Secret Sount***',
                    track_number=6,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007'),
             7: audiotools.MetaData(
                    track_name=u'\u5192\u967a\u8005\u305f\u3061\u306e\u5b89\u3089\u304e\u306e\u5834\u3002',
                    track_number=7,
                    track_total=7,
                    album_name=u'\u4e16\u754c\u6a39\u306e\u8ff7\u5baeII \u30d4\u30a2\u30ce\u30b9\u30b1\u30c3\u30c1Ver.',
                    artist_name=u'\u53e4\u4ee3\u7950\u4e09',
                    year=u'2007')}

        if (lossless):
            #test musicbrainz, no --metadata
            time.sleep(2)
            sub = subprocess.Popen(["track2xmcd","-V","quiet","-D",
                                    "--musicbrainz-server=musicbrainz.org",
                                    "--no-freedb"] + arguments,
                                   stdout=subprocess.PIPE)
            xml = sub.stdout.read()
            self.assertEqual(sub.wait(),0)
            self.assert_(len(xml) > 0)
            mbxml = audiotools.MusicBrainzReleaseXML.read_data(xml).metadata()

            #NOTE: this fails intermittently simply because
            #the MusicBrainz service is not 100% reliable
            #an album that returns 1 match may return 0 later on
            #even with a lengthy delay between checks
            #this may only be a temporary problem
            self.assertEqual(mbxml,MUSICBRAINZ_METADATA)

            #test freedb, no --metadata
            sub = subprocess.Popen(["track2xmcd","-V","quiet","-D",
                                    "--freedb-server=us.freedb.org",
                                    "--no-musicbrainz"] + arguments,
                                   stdout=subprocess.PIPE,
                                   stderr=open(os.devnull,"ab"))
            xmcd = sub.stdout.read().decode('utf-8','replace')
            self.assertEqual(sub.wait(),0)
            self.assert_(len(xmcd) > 0)
            xmcd = audiotools.XMCD.read_data(xmcd).metadata()
            self.assertEqual(xmcd,FREEDB_METADATA)

        if (has_metadata):
            #test musicbrainz, with --metadata
            sub = subprocess.Popen(["track2xmcd","-V","quiet",
                                    "--metadata",
                                    "--no-freedb"] + arguments,
                                   stdout=subprocess.PIPE,
                                   stderr=open(os.devnull,"ab"))
            xml = sub.stdout.read()
            self.assertEqual(sub.wait(),0)
            self.assert_(len(xml) > 0)
            mbxml = audiotools.MusicBrainzReleaseXML.read_data(xml).metadata()
            self.assertEqual(mbxml,album_metadata)

            #test freedb, with --metadata
            sub = subprocess.Popen(["track2xmcd","-V","quiet",
                                    "--metadata",
                                    "--no-musicbrainz"] + arguments,
                                   stdout=subprocess.PIPE,
                                   stderr=open(os.devnull,"ab"))
            xmcd = sub.stdout.read().decode('utf-8','replace')
            self.assertEqual(sub.wait(),0)
            self.assert_(len(xmcd) > 0)
            xmcd = audiotools.XMCD.read_data(xmcd).metadata()
            self.assertEqual(xmcd,album_metadata)

    #test individual tracks run through track2xmcd
    @TEST_EXECUTABLE
    def test_track2xmcd1(self):
        album_metadata = audiotools.AlbumMetaData(
            [audiotools.MetaData(
                    track_name=u'To the Stage of a New Adventure',
                    track_number=1,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'),
             audiotools.MetaData(
                    track_name=u'Echoes of a Fierce Battle that Separates Life and Death',
                    track_number=2,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'),
             audiotools.MetaData(
                    track_name=u'That is the Depths of a Crimson Labyrinth',
                    track_number=3,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'),
             audiotools.MetaData(
                    track_name=u'The Sons of God Meeting in the Sky',
                    track_number=4,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'),
             audiotools.MetaData(
                    track_name=u'To a Sorrowful Future of Snow and Ice',
                    track_number=5,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'),
             audiotools.MetaData(
                    track_name=u'***Secret Sound***',
                    track_number=6,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008',date=u''),
              audiotools.MetaData(
                    track_name=u'A Restful Place for the Adventurers',
                    track_number=7,track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008')])

        trackdir = tempfile.mkdtemp()

        track_files = [tempfile.NamedTemporaryFile(
                suffix=self.audio_class.SUFFIX) for i in
                       xrange(5)]
        try:
            tracks = [self.audio_class.from_pcm(
                    os.path.join(trackdir,"track %2.2d.%s" % \
                                     (i,self.audio_class.SUFFIX)),
                    EXACT_BLANK_PCM_Reader(frames))
                      for (i,frames) in
                      enumerate([7939176, 4799256, 6297480, 5383140,
                                 5246136, 5052684, 5013876])]

            for (i,track) in enumerate(tracks):
                track.set_metadata(album_metadata[i + 1])
            self.__test_track2xmcd__(
                [track.filename for track in tracks],
                album_metadata,
                set([track.lossless() for track in tracks]) == set([True]),
                None not in [track.get_metadata() for track in tracks])
        finally:
            for f in os.listdir(trackdir):
                os.unlink(os.path.join(trackdir,f))
            os.rmdir(trackdir)

    #test CD image and cuesheet run through track2xmcd
    @TEST_EXECUTABLE
    def test_track2xmcd2(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        cue_file = tempfile.NamedTemporaryFile(
            suffix=".toc")

        try:
            track = self.audio_class.from_pcm(
                track_file.name,
                EXACT_BLANK_PCM_Reader(sum([7939176, 4799256, 6297480, 5383140,
                                            5246136, 5052684, 5013876])))

            #FIXME - AIFF has a stupid race condition
            #in which calling close() does not guarantee writing to disk
            #this should be fixed by replacing Python's built-in aifc module
            time.sleep(1)

            track.set_metadata(audiotools.MetaData(
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'))
            cue_file.write(
"""QlpoOTFBWSZTWbyn4AMAALXfgAAQUAH/8C9v3qCsCBWAMAEtkBGpGg9Q0ZAAAAAaaBFAAMhpoAAE
fqlBTYpmJBoGQxpqHlFvwqjDgECCIriA1AeSphpbRItLIsgKQGZkDM34D22RH5MTDiYwcDQ4GZSe
ZhfWe0omZRIIIIOMJlzMzqQS4YDXOeWlICCr0cvBeYADTSHABVTJajiYELoVgw2FKlIXBWIwzKWg
zbRFFkTFETNfdPx1Pk9ISZmJvoOJSUdoProZFRcWFZ2Opug5lRkdILi8tgqgpgrMzMxOZ4l5dC0k
uhhDdCiCwqg2Gw3lphgaGhoamR+mptKYNT/F3JFOFCQvKfgAwA==""".decode('base64').decode('bz2'))
            cue_file.flush()
            self.__test_track2xmcd__(
                ["--cue",cue_file.name,track.filename],
                audiotools.AlbumMetaData([
                        audiotools.MetaData(
                            track_number=1,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=2,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=3,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=4,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=5,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=6,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),audiotools.MetaData(
                            track_number=7,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008')]),
                track.lossless(),
                track.get_metadata() is not None)
        finally:
            track_file.close()
            cue_file.close()

    #test CD image with embedded cuesheet run through track2xmcd
    @TEST_EXECUTABLE
    def test_track2xmcd3(self):
        import audiotools.toc

        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)

        try:
            track = self.audio_class.from_pcm(
                track_file.name,
                EXACT_BLANK_PCM_Reader(sum([7939176, 4799256, 6297480, 5383140,
                                            5246136, 5052684, 5013876])))

            #FIXME - AIFF has a stupid race condition
            #in which calling close() does not guarantee writing to disk
            #this should be fixed by replacing Python's built-in aifc module
            time.sleep(1)

            track.set_metadata(audiotools.MetaData(
                    track_total=7,
                    album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                    artist_name=u'Yuzo Koshiro & Yuji Himukai',
                    year=u'2008'))
            track.set_cuesheet(audiotools.toc.parse(
                    cStringIO.StringIO("""QlpoOTFBWSZTWbyn4AMAALXfgAAQUAH/8C9v3qCsCBWAMAEtkBGpGg9Q0ZAAAAAaaBFAAMhpoAAE
fqlBTYpmJBoGQxpqHlFvwqjDgECCIriA1AeSphpbRItLIsgKQGZkDM34D22RH5MTDiYwcDQ4GZSe
ZhfWe0omZRIIIIOMJlzMzqQS4YDXOeWlICCr0cvBeYADTSHABVTJajiYELoVgw2FKlIXBWIwzKWg
zbRFFkTFETNfdPx1Pk9ISZmJvoOJSUdoProZFRcWFZ2Opug5lRkdILi8tgqgpgrMzMxOZ4l5dC0k
uhhDdCiCwqg2Gw3lphgaGhoamR+mptKYNT/F3JFOFCQvKfgAwA==""".decode('base64').decode('bz2')).readlines()))
            if (track.get_cuesheet() is None):
                return

            self.__test_track2xmcd__(
                [track.filename],
                audiotools.AlbumMetaData([
                        audiotools.MetaData(
                            track_number=1,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=2,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=3,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=4,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=5,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),
                        audiotools.MetaData(
                            track_number=6,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008'),audiotools.MetaData(
                            track_number=7,
                            track_total=7,
                            album_name=u'Sekaiju no MeiQ\xb2 *syoou no seihai* sound track : Piano sketch version',
                            artist_name=u'Yuzo Koshiro & Yuji Himukai',
                            year=u'2008')]),
                track.lossless(),
                track.get_metadata() is not None)
        finally:
            track_file.close()


    @TEST_EXECUTABLE
    def test_track2track_invalid(self):
        basedir_src = tempfile.mkdtemp()

        basedir_tar = tempfile.mkdtemp()
        basedir_tar_stat = os.stat(basedir_tar)[0]

        try:
            track = self.audio_class.from_pcm(
                os.path.join(basedir_src,"track01.%s" % \
                                 (self.audio_class.SUFFIX)),
                BLANK_PCM_Reader(5))

            #try to use track2track with an invalid XMCD file
            self.assertEqual(self.__run_app__(
                    ["track2track",
                     "-t","wav",
                     "-x","/dev/null/foo.xmcd",
                     track.filename]),1)

            self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

            #try to use track2track -d on an un-writable directory
            os.chmod(basedir_tar,basedir_tar_stat & 07555)

            self.assertEqual(self.__run_app__(
                    ["track2track",
                     "-t","wav",
                     "-j",str(1),
                     track.filename,
                     "-d",
                     os.path.join(basedir_tar,"foo")]),1)

            self.__check_error__(_(u"Unable to write \"%s\"") % \
                                     (self.filename(
                        os.path.join(basedir_tar,"foo","track01.wav"))))

            #try to use track2track -o on an un-writable directory
            self.assertEqual(self.__run_app__(
                    ["track2track",
                     "-t","wav",
                     track.filename,
                     "-o",
                     os.path.join(basedir_tar,"foo","track01.wav")]),1)

            self.__check_error__(_(u"Unable to write \"%s\"") % \
                                     (self.filename(
                        os.path.join(basedir_tar,"foo","track01.wav"))))

            os.chmod(basedir_tar,basedir_tar_stat)

            #try to use track2track -d on an un-writable file
            f = open(os.path.join(basedir_tar,"track01.wav"),"wb")
            f.write("")
            f.close()
            f_stat = os.stat(os.path.join(basedir_tar,"track01.wav"))[0]
            os.chmod(os.path.join(basedir_tar,"track01.wav"),
                     f_stat & 07555)
            try:
                self.assertEqual(self.__run_app__(
                    ["track2track",
                     "-t","wav",
                     "-j",str(1),
                     track.filename,
                     "-d",
                     basedir_tar]),1)

                self.__check_info__(_(u"%s -> %s") % \
                                        (self.filename(track.filename),
                                         self.filename(os.path.join(basedir_tar,"track01.wav"))))

                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(
                            os.path.join(basedir_tar,"track01.wav"))))

                #try to use track2track -o on an un-writable file
                self.assertEqual(self.__run_app__(
                    ["track2track",
                     "-t","wav",
                     track.filename,
                     "-o",
                     os.path.join(basedir_tar,"track01.wav")]),1)

                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(
                            os.path.join(basedir_tar,"track01.wav"))))
            finally:
                os.chmod(os.path.join(basedir_tar,"track01.wav"),f_stat)
            os.unlink(os.path.join(basedir_tar,"track01.wav"))

        finally:
            for f in os.listdir(basedir_src):
                os.unlink(os.path.join(basedir_src,f))
            os.rmdir(basedir_src)

            os.chmod(basedir_tar,basedir_tar_stat)
            for f in os.listdir(basedir_tar):
                os.unlink(os.path.join(basedir_tar,f))
            os.rmdir(basedir_tar)

    @TEST_EXECUTABLE
    def test_trackcat_invalid(self):
        temp_track_file1 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp_track_file2 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp_track_file3 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            temp_track1 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(5))

            temp_track2 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(6))

            temp_track3 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(7))

            self.assertEqual(self.__run_app__(
                    ["trackcat",
                     temp_track1.filename,
                     temp_track2.filename,
                     temp_track3.filename,
                     "-o","/dev/null/foo.wav"]),1)

            self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         ("/dev/null/foo.wav"))

            self.assertEqual(self.__run_app__(
                    ["trackcat",
                     "--cue","/dev/null/foo.cue",
                     temp_track1.filename,
                     temp_track2.filename,
                     temp_track3.filename,
                     "-o","foo.wav"]),1)

            self.__check_error__(_(u"Unable to read cuesheet"))
        finally:
            temp_track_file1.close()
            temp_track_file2.close()
            temp_track_file3.close()

    @TEST_EXECUTABLE
    def test_track2xmcd_invalid(self):
        temp_track_file1 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp_track_file2 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            temp_track1 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(5))

            temp_track2 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(6))

            self.assertEqual(self.__run_app__(
                    ["track2xmcd",
                     "--no-musicbrainz",
                     "--freedb-server=foo.bar",
                     "--freedb-port=9001",
                     temp_track1.filename,
                     temp_track2.filename]),1)

            self.__check_info__(_(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
                                   {"disc_id":u"0a000c02",
                                    "server":u"foo.bar"})

            #an invalid freedb-server will generate one of the following
            #depending on whether DNS is spoofing bogus hostnames or not
            #self.__check_error__(u"[Errno 111] Connection refused")
            #self.__check_error__(u"[Errno -2] Name or service not known")

            self.assertEqual(self.__run_app__(
                    ["track2xmcd",
                     temp_track1.filename,
                     temp_track2.filename,
                     "-x","/dev/null/foo.xmcd"]),1)
            self.__check_error__(_(u"Unable to write \"%s\"") % \
                                     (self.filename("/dev/null/foo.xmcd")))
        finally:
            temp_track_file1.close()
            temp_track_file2.close()

    @TEST_EXECUTABLE
    def test_tracktag_invalid(self):
        temp_track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp_track_stat = os.stat(temp_track_file.name)[0]
        try:
            temp_track = self.audio_class.from_pcm(
                temp_track_file.name,
                BLANK_PCM_Reader(5))

            temp_track.set_metadata(DummyMetaData())
            if (temp_track.get_metadata() is not None):
                self.assertEqual(self.__run_app__(
                        ["tracktag","--xmcd=/dev/null/foo.xmcd",
                         self.filename(temp_track.filename)]),1)
                self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

                self.assertEqual(self.__run_app__(
                        ["tracktag","--comment-file=/dev/null/foo.txt",
                         self.filename(temp_track.filename)]),1)
                self.__check_error__(_(u"Unable to open comment file \"%s\"") % \
                                         (self.filename("/dev/null/foo.txt")))

                os.chmod(temp_track_file.name,temp_track_stat & 07555)
                self.assertEqual(self.__run_app__(
                        ["tracktag","--name=Foo",
                         self.filename(temp_track.filename)]),1)
                self.__check_error__(_(u"Unable to modify \"%s\"") % \
                                         (self.filename(temp_track.filename)))
        finally:
            os.chmod(temp_track_file.name,temp_track_stat)
            temp_track_file.close()

    @TEST_EXECUTABLE
    def test_tracksplit_invalid(self):
        if (not self.__is_lossless__()):
            return

        TOTAL_FRAMES = 24725400
        CUE_SHEET = 'FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 03:16:55\n    INDEX 01 03:18:18\n  TRACK 03 AUDIO\n    INDEX 00 05:55:12\n    INDEX 01 06:01:45\n'

        base_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        cue_file = tempfile.NamedTemporaryFile(suffix=".cue")

        tempdir = tempfile.mkdtemp()
        tempdir_stat = os.stat(tempdir)[0]
        try:
            track = self.audio_class.from_pcm(
                    base_file.name,
                    EXACT_BLANK_PCM_Reader(TOTAL_FRAMES))
            track.set_metadata(audiotools.MetaData(album_number=0))
            cue_file.write(CUE_SHEET)
            cue_file.flush()

            self.assertEqual(self.__run_app__(
                    ["tracksplit","--xmcd=/dev/null/foo.xmcd",
                     "--cue",cue_file.name,
                     "-d",tempdir,self.filename(track.filename)]),1)

            self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

            self.assertEqual(self.__run_app__(
                    ["tracksplit",
                     "--cue","/dev/null/foo.cue",
                     "-d",tempdir,track.filename]),1)
            self.__check_error__(_(u"Unable to read cuesheet"))

            os.chmod(tempdir,tempdir_stat & 0x7555)
            self.assertEqual(self.__run_app__(
                    ["tracksplit",
                     "--cue",cue_file.name,
                     "-d",tempdir,
                     "-j",str(1),
                     "-t","wav",
                     track.filename]),1)

            self.__check_info__(_(u"%s -> %s") % \
                                        (self.filename(track.filename),
                                         self.filename(os.path.join(tempdir,"track01.wav"))))

            self.__check_error__(_(u"Unable to write \"%s\"") % \
                                     (self.filename(
                        os.path.join(tempdir,"track01.wav"))))

        finally:
            os.chmod(tempdir,tempdir_stat)
            os.rmdir(tempdir)
            cue_file.close()
            base_file.close()

    @TEST_EXECUTABLE
    def test_trackrename_invalid(self):
        tempdir = tempfile.mkdtemp()
        tempdir_stat = os.stat(tempdir)[0]
        track = self.audio_class.from_pcm(
            os.path.join(tempdir,"01 - track.%s" % (self.audio_class.SUFFIX)),
            BLANK_PCM_Reader(5))
        track.set_metadata(audiotools.MetaData(track_name=u"Name",
                                               track_number=1,
                                               album_name=u"Album"))
        try:
            if (track.get_metadata() is not None):
                os.chmod(tempdir,tempdir_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["trackrename",
                         '--format=%(album_name)s/%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]),1)

                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         self.filename(
                        os.path.join(
                            "Album",
                            "%(track_number)2.2d - %(track_name)s.%(suffix)s" % \
                                {"track_number":1,
                                 "track_name":"Name",
                                 "suffix":self.audio_class.SUFFIX})))

                self.assertEqual(self.__run_app__(
                        ["trackrename",
                         '--format=%(track_number)2.2d - %(track_name)s.%(suffix)s',
                         track.filename]),1)

                 #mv(1)'s output is system-specific and not something
                 #that should be tested against directly
        finally:
            os.chmod(tempdir,tempdir_stat)
            os.unlink(track.filename)
            os.rmdir(tempdir)

    @TEST_EXECUTABLE
    def test_tracklint_invalid1(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        track_file_stat = os.stat(track_file.name)[0]

        undo_db_dir = tempfile.mkdtemp()
        undo_db = os.path.join(undo_db_dir,"undo.db")

        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))
            track.set_metadata(audiotools.MetaData(
                    track_name=u"Track Name ",
                    track_number=1))
            if (track.get_metadata() is not None):
                #unwritable undo DB, writable file
                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix","--db","/dev/null/undo.db",
                         track.filename]),1)
                self.__check_error__(_(u"Unable to open \"%s\"") % \
                                         (self.filename("/dev/null/undo.db")))

                self.assertEqual(self.__run_app__(
                        ["tracklint","--undo","--db","/dev/null/undo.db",
                         track.filename]),1)
                self.__check_error__(_(u"Unable to open \"%s\"") % \
                                         (self.filename("/dev/null/undo.db")))

                #unwritable undo DB, unwritable file
                os.chmod(track.filename, track_file_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix","--db","/dev/null/undo.db",
                         track.filename]),1)
                self.__check_error__(_(u"Unable to open \"%s\"") % \
                                         (self.filename("/dev/null/undo.db")))

                self.assertEqual(self.__run_app__(
                        ["tracklint","--undo","--db","/dev/null/undo.db",
                         track.filename]),1)
                self.__check_error__(_(u"Unable to open \"%s\"") % \
                                         (self.filename("/dev/null/undo.db")))

                #restore from DB to unwritable file
                os.chmod(track.filename,track_file_stat)
                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix","--db",undo_db,
                         track.filename]),0)
                os.chmod(track.filename,track_file_stat & 0x7555)
                self.assertEqual(self.__run_app__(
                        ["tracklint","--undo","--db",undo_db,
                         track.filename]),1)
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))

        finally:
            os.chmod(track_file.name,track_file_stat)
            track_file.close()
            for p in [os.path.join(undo_db_dir,f) for f in
                      os.listdir(undo_db_dir)]:
                os.unlink(p)
            os.rmdir(undo_db_dir)

    @TEST_EXECUTABLE
    def test_tracklint_invalid2(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        track_file_stat = os.stat(track_file.name)[0]

        undo_db_dir = tempfile.mkdtemp()
        undo_db = os.path.join(undo_db_dir,"undo.db")

        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))
            track.set_metadata(audiotools.MetaData(
                    track_name=u"Track Name ",
                    track_number=1))
            if (track.get_metadata() is not None):
                #writable undo DB, unwritable file
                os.chmod(track.filename,
                         track_file_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix","--db",undo_db,
                         track.filename]),1)
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename":self.filename(track.filename),
                            "message":_(u"Stripped whitespace from track_name field")})
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))

                #no undo DB, unwritable file
                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix",track.filename]),1)
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename":self.filename(track.filename),
                            "message":_(u"Stripped whitespace from track_name field")})
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))
        finally:
            os.chmod(track_file.name,track_file_stat)
            track_file.close()
            for p in [os.path.join(undo_db_dir,f) for f in
                      os.listdir(undo_db_dir)]:
                os.unlink(p)
            os.rmdir(undo_db_dir)

    @TEST_EXECUTABLE
    def test_coverdump_invalid(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        temp_dir = tempfile.mkdtemp()
        temp_dir_stat = os.stat(temp_dir)[0]
        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))
            track.set_metadata(DummyMetaData3())
            if ((track.get_metadata() is not None) and
                (len(track.get_metadata().images()) == 1)):
                os.chmod(temp_dir,temp_dir_stat & 0x7555)
                self.assertEqual(self.__run_app__(
                        ["coverdump","-d",temp_dir,track.filename]),1)
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(
                            os.path.join(temp_dir,"front_cover.jpg"))))
        finally:
            track_file.close()
            os.chmod(temp_dir,temp_dir_stat)
            for p in [os.path.join(temp_dir,f) for f in
                      os.listdir(temp_dir)]:
                os.unlink(p)
            os.rmdir(temp_dir)

    #tests the splitting and concatenating programs
    @TEST_EXECUTABLE
    @TEST_CUESHEET
    def test_tracksplit_trackcat(self):
        if (not self.__is_lossless__()):
            return

        TOTAL_FRAMES = 24725400
        FILE_FRAMES = [8742384,7204176,8778840]
        CUE_SHEET = 'FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 03:16:55\n    INDEX 01 03:18:18\n  TRACK 03 AUDIO\n    INDEX 00 05:55:12\n    INDEX 01 06:01:45\n'

        TOC_SHEET = 'CD_DA\n\nTRACK AUDIO\n    AUDIOFILE "data.wav" 00:00:00 03:16:55\n\nTRACK AUDIO\n    AUDIOFILE "data.wav" 03:16:55 02:38:32\n    START 00:01:38\n\nTRACK AUDIO\n    AUDIOFILE "data.wav" 05:55:12\n    START 00:06:33\n'

        TOC_SHEET2 = 'CD_DA\n\nCATALOG "0000000000000"\n\n// Track 1\nTRACK AUDIO\nNO COPY\nNO PRE_EMPHASIS\nTWO_CHANNEL_AUDIO\nISRC "JPVI00213050"\nFILE "data.wav" 0 03:16:55\n\n\n// Track 2\nTRACK AUDIO\nNO COPY\nNO PRE_EMPHASIS\nTWO_CHANNEL_AUDIO\nISRC "JPVI00213170"\nFILE "data.wav" 03:16:55 02:38:32\nSTART 00:01:38\n\n\n// Track 3\nTRACK AUDIO\nNO COPY\nNO PRE_EMPHASIS\nTWO_CHANNEL_AUDIO\nISRC "JPVI00213200"\nFILE "data.wav" 05:55:12 03:25:38\nSTART 00:06:33\n\n'

        for (sheet,suffix) in zip([CUE_SHEET,TOC_SHEET,TOC_SHEET2],
                                  ['.cue','.toc','.toc']):
            base_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

            cue_file = tempfile.NamedTemporaryFile(suffix=suffix)
            cue_file.write(sheet)
            cue_file.flush()

            joined_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)

            try:
                base = self.audio_class.from_pcm(
                    base_file.name,
                    EXACT_RANDOM_PCM_Reader(TOTAL_FRAMES))

                if (not base.lossless()):
                    return

                self.assertEqual(base.total_frames(),TOTAL_FRAMES)

                tempdir = tempfile.mkdtemp()

                subprocess.call(["tracksplit",
                                 "-V","quiet","-j",str(1),
                                 "-t",self.audio_class.NAME,
                                 "--cue=%s" % (cue_file.name),
                                 "--no-replay-gain",
                                 "-d",tempdir,
                                 base.filename])

                split_files = list(audiotools.open_directory(tempdir))

                for (f,length) in zip(split_files,FILE_FRAMES):
                    self.assertEqual(f.total_frames(),length)

                subprocess.call(["trackcat",
                                 "-t",self.audio_class.NAME,
                                 "-o",joined_file.name] + \
                                [f.filename for f in split_files])

                self.assertEqual(audiotools.pcm_cmp(
                        base.to_pcm(),
                        audiotools.open(joined_file.name).to_pcm()),
                                 True)


                self.assertEqual(subprocess.call(["trackcmp",
                                                  "-V","quiet",
                                                  base.filename,
                                                  joined_file.name]),0)

                self.assertEqual(subprocess.call(["trackcmp",
                                                  "-V","quiet",
                                                  base.filename,
                                                  split_files[0].filename]),1)

                for f in split_files:
                    os.unlink(f.filename)
                os.rmdir(tempdir)
            finally:
                base_file.close()
                cue_file.close()
                joined_file.close()

    @TEST_EXECUTABLE
    def test_trackcmp(self):
        basedir = tempfile.mkdtemp()
        try:
            subdir1 = os.path.join(basedir,"subdir1")
            subdir2 = os.path.join(basedir,"subdir2")
            os.mkdir(subdir1)
            os.mkdir(subdir2)
            try:
                tempfile1 = self.audio_class.from_pcm(
                    os.path.join(subdir1,"track01.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(10))
                tempfile1.set_metadata(audiotools.MetaData(
                        track_number=1))

                tempfile2 = self.audio_class.from_pcm(
                    os.path.join(subdir1,"track02.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(5))
                tempfile2.set_metadata(audiotools.MetaData(
                        track_number=2))

                tempfile3 = self.audio_class.from_pcm(
                    os.path.join(subdir1,"track03.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(15))
                tempfile3.set_metadata(audiotools.MetaData(
                        track_number=3))
                try:
                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)
                    os.link(tempfile1.filename,
                            os.path.join(subdir2,
                                         "track01.%s" % \
                                             (self.audio_class.SUFFIX)))
                    tempfile4 = audiotools.open(
                            os.path.join(subdir2,
                                         "track01.%s" % \
                                             (self.audio_class.SUFFIX)))

                    self.assertEqual(filecmp.cmp(tempfile1.filename,
                                                 tempfile4.filename),
                                     True)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.link(tempfile2.filename,
                            os.path.join(subdir2,
                                         "track02.%s" % \
                                             (self.audio_class.SUFFIX)))
                    tempfile5 = audiotools.open(
                            os.path.join(subdir2,
                                         "track02.%s" % \
                                             (self.audio_class.SUFFIX)))

                    self.assertEqual(filecmp.cmp(tempfile2.filename,
                                                 tempfile5.filename),
                                     True)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.link(tempfile3.filename,
                            os.path.join(subdir2,
                                         "track03.%s" % \
                                             (self.audio_class.SUFFIX)))
                    tempfile6 = audiotools.open(
                            os.path.join(subdir2,
                                         "track03.%s" % \
                                             (self.audio_class.SUFFIX)))

                    self.assertEqual(filecmp.cmp(tempfile3.filename,
                                                 tempfile6.filename),
                                     True)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),0)

                    os.unlink(tempfile2.filename)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.unlink(tempfile3.filename)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)

                    os.unlink(tempfile1.filename)

                    self.assertEqual(subprocess.call(["trackcmp",
                                                      "-V","quiet",
                                                      subdir1,
                                                      subdir2]),1)
                finally:
                    for temp in (tempfile1,tempfile2,tempfile3,
                                 tempfile4,tempfile5,tempfile6):
                        if (os.path.isfile(temp.filename)):
                            os.unlink(temp.filename)
            finally:
                os.rmdir(subdir1)
                os.rmdir(subdir2)
        finally:
            os.rmdir(basedir)

    @TEST_EXECUTABLE
    def test_tracklength(self):
        basedir = tempfile.mkdtemp()
        try:
            tempfile1 = self.audio_class.from_pcm(
                    os.path.join(basedir,"track01.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(10))

            tempfile2 = self.audio_class.from_pcm(
                    os.path.join(basedir,"track02.%s" % \
                                     (self.audio_class.SUFFIX)),
                    RANDOM_PCM_Reader(5))

            try:
                len1 = subprocess.Popen(["tracklength",
                                         tempfile1.filename],
                                        stdout=subprocess.PIPE)
                len1_result = len1.stdout.read()
                len1.wait()

                len2 = subprocess.Popen(["tracklength",
                                         tempfile2.filename],
                                        stdout=subprocess.PIPE)
                len2_result = len2.stdout.read()
                len2.wait()

                len3 = subprocess.Popen(["tracklength",
                                         basedir],
                                        stdout=subprocess.PIPE)
                len3_result = len3.stdout.read()
                len3.wait()

                self.assertEqual(len1_result,'0:00:10\n')
                self.assertEqual(len2_result,'0:00:05\n')
                self.assertEqual(len3_result,'0:00:15\n')
            finally:
                os.unlink(tempfile1.filename)
                os.unlink(tempfile2.filename)
        finally:
            os.rmdir(basedir)

    @TEST_EXECUTABLE
    @TEST_METADATA
    def test_tracktag_trackrename(self):
        template = "%(track_number)2.2d - %(album_number)d - %(album_track_number)s-%(track_total)d-%(album_total)d-%(track_name)s%(album_name)s%(artist_name)s%(performer_name)s%(composer_name)s%(conductor_name)s%(media)s%(ISRC)s%(copyright)s%(publisher)s%(year)s%(suffix)s"

        basedir = tempfile.mkdtemp()
        try:
            track = self.audio_class.from_pcm(
                os.path.join(basedir,"track.%s" % (self.audio_class.SUFFIX)),
                BLANK_PCM_Reader(5))
            metadata = audiotools.MetaData(track_name="Name")
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if (metadata is None):
                return

            jpeg = os.path.join(basedir,"image1.jpg")
            png = os.path.join(basedir,"image2.png")

            f = open(jpeg,"wb")
            f.write(TEST_COVER1)
            f.close()
            f = open(png,"wb")
            f.write(TEST_COVER2)
            f.close()

            self.assertEqual(metadata.track_name,"Name")

            for (flag,field,value) in self.flag_field_values():
                self.assertEqual(subprocess.call(["tracktag",
                                                  flag,str(value),
                                                  track.filename]),0)
                setattr(metadata,field,value)
                self.assertEqual(getattr(metadata,field),value,
                                 "metadata.%s = %s, should be %s" % \
                                     (field,getattr(metadata,field),value))
                self.assertEqual(metadata,track.get_metadata())

                new_path = os.path.join(basedir,
                                        self.audio_class.track_name(
                        metadata.track_number,
                        metadata,
                        metadata.album_number,
                        template))

                self.assertEqual(subprocess.call(["trackrename",
                                                  "-V","quiet",
                                                  "--format",template,
                                                  track.filename]),0)

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)

            os.rename(track.filename,
                      os.path.join(basedir,"track.%s" % \
                                       (self.audio_class.SUFFIX)))
            track = audiotools.open(os.path.join(basedir,"track.%s" % \
                                                     (self.audio_class.SUFFIX)))

            for (flag,field,value) in self.flag_field_values():
                self.assertEqual(subprocess.call(["tracktag",
                                                  "--replace",
                                                  flag,str(value),
                                                  track.filename]),0)
                metadata = audiotools.MetaData(**{field:value})
                self.assertEqual(metadata,track.get_metadata())

                os.rename(track.filename,
                          os.path.join(basedir,"track.%s" % \
                                           (self.audio_class.SUFFIX)))
                track = audiotools.open(os.path.join(basedir,"track.%s" % \
                                                         (self.audio_class.SUFFIX)))

                new_path = os.path.join(basedir,
                                        self.audio_class.track_name(
                        metadata.track_number,
                        metadata,
                        metadata.album_number,
                        template))

                self.assertEqual(subprocess.call(["trackrename",
                                                  "-V","quiet",
                                                  "--format",template,
                                                  track.filename]),0)

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)
                metadata = track.get_metadata()

            if (metadata.supports_images()):
                metadata = audiotools.MetaData(track_name='Images')
                track.set_metadata(metadata)
                self.assertEqual(metadata,track.get_metadata())

                flag_type_images_data = self.__flag_type_images_data__(
                    jpeg,png,TEST_COVER1,TEST_COVER2)

                for (flag,img_type,value,data) in flag_type_images_data:
                    self.assertEqual(subprocess.call(["tracktag",
                                                      flag,str(value),
                                                      track.filename]),0)
                    metadata.add_image(audiotools.Image.new(
                            data,u"",img_type))
                    self.assertEqual(metadata.images(),
                                     track.get_metadata().images())

                for (flag,img_type,value,data) in flag_type_images_data:
                    self.assertEqual(subprocess.call(["tracktag",
                                                      "--remove-images",
                                                      flag,str(value),
                                                      track.filename]),0)
                    metadata = audiotools.MetaData(track_name='Images')
                    metadata.add_image(audiotools.Image.new(
                            data,u"",img_type))
                    self.assertEqual(metadata.images(),
                                     track.get_metadata().images())
        finally:
            for f in os.listdir(basedir):
                os.unlink(os.path.join(basedir,f))
            os.rmdir(basedir)

    def __flag_type_images_data__(self,jpeg,png,test_cover1,test_cover2):
        return zip(["--front-cover",
                    "--back-cover",
                    "--leaflet",
                    "--leaflet",
                    "--media",
                    "--other-image",],
                   [0,1,2,2,3,4],
                   [jpeg,jpeg,png,jpeg,png,jpeg],
                   [test_cover1,
                    test_cover1,
                    test_cover2,
                    test_cover1,
                    test_cover2,
                    test_cover1])

    @TEST_EXECUTABLE
    @TEST_METADATA
    def test_coverdump(self):
        basefile = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        imgdir = tempfile.mkdtemp()
        try:
            track = self.audio_class.from_pcm(basefile.name,
                                              BLANK_PCM_Reader(10))
            metadata = audiotools.MetaData(track_name=u"Name")
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if ((metadata is None) or (not metadata.supports_images())):
                return

            metadata.add_image(audiotools.Image.new(
                    TEST_COVER1,u"",0))
            metadata.add_image(audiotools.Image.new(
                    TEST_COVER2,u"",2))
            metadata.add_image(audiotools.Image.new(
                    TEST_COVER3,u"",1))

            track.set_metadata(metadata)

            subprocess.call(["coverdump",
                             "-V","quiet",
                             "-d",imgdir,
                             track.filename])

            f = open(os.path.join(imgdir,"front_cover.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER1)
            f.close()
            f = open(os.path.join(imgdir,"leaflet.png"),"rb")
            self.assertEqual(f.read(),TEST_COVER2)
            f.close()
            f = open(os.path.join(imgdir,"back_cover.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER3)
            f.close()

            for f in os.listdir(imgdir):
                os.unlink(os.path.join(imgdir,f))

            metadata = audiotools.MetaData(track_name=u"Name")
            track.set_metadata(metadata)
            metadata = track.get_metadata()

            metadata.add_image(audiotools.Image.new(
                    TEST_COVER3,u"",2))
            metadata.add_image(audiotools.Image.new(
                    TEST_COVER2,u"",2))
            metadata.add_image(audiotools.Image.new(
                    TEST_COVER1,u"",2))

            track.set_metadata(metadata)

            subprocess.call(["coverdump",
                             "-V","quiet",
                             "-d",imgdir,
                             track.filename])

            f = open(os.path.join(imgdir,"leaflet01.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER3)
            f.close()
            f = open(os.path.join(imgdir,"leaflet02.png"),"rb")
            self.assertEqual(f.read(),TEST_COVER2)
            f.close()
            f = open(os.path.join(imgdir,"leaflet03.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER1)
            f.close()
        finally:
            basefile.close()
            for f in os.listdir(imgdir):
                os.unlink(os.path.join(imgdir,f))
            os.rmdir(imgdir)

    @TEST_EXECUTABLE
    def testinvalidbinaries(self):
        if (len(self.audio_class.BINARIES) == 0):
            return

        temp_track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)

        temp_track = self.audio_class.from_pcm(
            temp_track_file.name,
            BLANK_PCM_Reader(5))

        wave_temp_file = tempfile.NamedTemporaryFile(suffix=".wav")

        wave_file = audiotools.WaveAudio.from_pcm(
            wave_temp_file.name,
            BLANK_PCM_Reader(5))

        #grab our original binaries so we can point them back later
        if (not audiotools.config.has_section("Binaries")):
            audiotools.config.add_section("Binaries")

        old_settings = [(bin,audiotools.config.get_default("Binaries",bin,bin))
                        for bin in self.audio_class.BINARIES]
        try:
            for bin in self.audio_class.BINARIES:
                audiotools.config.set("Binaries",bin,"./error.py")

            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_wave,
                              "test.%s" % (self.audio_class.SUFFIX),
                              wave_file.filename)

            self.assertRaises(audiotools.EncodingError,
                              temp_track.to_wave,
                              "test.wav")

            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_pcm,
                              "test.%s" % (self.audio_class.SUFFIX),
                              BLANK_PCM_Reader(5))

            for audio_class in audiotools.TYPE_MAP.values():
                if (len(audio_class.BINARIES) > 0):
                    self.assertRaises(audiotools.EncodingError,
                                      audio_class.from_pcm,
                                      "test.%s" % (audio_class.SUFFIX),
                                      temp_track.to_pcm())

        finally:
            for (bin,setting) in old_settings:
                audiotools.config.set("Binaries",bin,setting)
            wave_temp_file.close()
            temp_track_file.close()

class TestForeignWaveChunks:
    @TEST_METADATA
    def testforeignwavechunks(self):
        import filecmp

        self.assertEqual(self.audio_class.supports_foreign_riff_chunks(),True)

        tempwav1 = tempfile.NamedTemporaryFile(suffix=".wav")
        tempwav2 = tempfile.NamedTemporaryFile(suffix=".wav")
        audio = tempfile.NamedTemporaryFile(suffix='.'+self.audio_class.SUFFIX)
        try:
            #build a WAVE with some oddball chunks
            audiotools.WaveAudio.wave_from_chunks(
                tempwav1.name,
                [('fmt ','\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00'),
                 ('fooz','testtext'),
                 ('barz','somemoretesttext'),
                 ('bazz',chr(0) * 1024),
                 ('data','BZh91AY&SY\xdc\xd5\xc2\x8d\x06\xba\xa7\xc0\x00`\x00 \x000\x80MF\xa9$\x84\x9a\xa4\x92\x12qw$S\x85\t\r\xcd\\(\xd0'.decode('bz2'))])

            #convert it to our audio type
            wav = self.audio_class.from_wave(audio.name,
                                             tempwav1.name)

            self.assertEqual(wav.has_foreign_riff_chunks(),True)

            #then convert it back to a WAVE
            wav.to_wave(tempwav2.name)

            #check that the two WAVEs are byte-for-byte identical
            self.assertEqual(filecmp.cmp(tempwav1.name,
                                         tempwav2.name,
                                         False),True)

            #finally, ensure that setting metadata doesn't erase the chunks
            wav.set_metadata(self.DummyMetaData())
            wav = audiotools.open(wav.filename)
            self.assertEqual(wav.has_foreign_riff_chunks(),True)
        finally:
            tempwav1.close()
            tempwav2.close()
            audio.close()


class TestWaveAudio(TestForeignWaveChunks,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.WaveAudio

class TestAuAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.AuAudio

class VorbisLint:
    #tracklint is tricky to test since set_metadata()
    #usually won't write anything that needs fixing.
    #For instance, it won't generate empty fields or leading zeroes in numbers.
    #So, bogus tags must be generated at a lower level.
    @TEST_EXECUTABLE
    def test_tracklint(self):
        bad_vorbiscomment = audiotools.VorbisComment(
            {"TITLE":[u"Track Name  "],
             "TRACKNUMBER":[u"02"],
             "DISCNUMBER":[u"003"],
             "ARTIST":[u"  Some Artist"],
             "PERFORMER":[u"Some Artist"],
             "CATALOG":[u""],
             "YEAR":[u"  "],
             "COMMENT":[u"  Some Comment  "]})

        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            album_number=3,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed,bad_vorbiscomment)

        tempdir = tempfile.mkdtemp()
        tempmp = os.path.join(tempdir,"track.%s" % (self.audio_class.SUFFIX))
        undo = os.path.join(tempdir,"undo.db")
        try:
            track = self.audio_class.from_pcm(
                tempmp,
                BLANK_PCM_Reader(10))

            track.set_metadata(bad_vorbiscomment)
            metadata = track.get_metadata()
            if (isinstance(metadata,audiotools.FlacMetaData)):
                metadata = metadata.vorbis_comment
            self.assertEqual(metadata,bad_vorbiscomment)
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_vorbiscomment[key])

            original_checksum = md5()
            f = open(track.filename,'rb')
            audiotools.transfer_data(f.read,original_checksum.update)
            f.close()

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--fix","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertNotEqual(metadata,bad_vorbiscomment)
            self.assertEqual(metadata,fixed)

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--undo","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            if (isinstance(metadata,audiotools.FlacMetaData)):
                metadata = metadata.vorbis_comment
            self.assertEqual(metadata,bad_vorbiscomment)
            self.assertNotEqual(metadata,fixed)
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_vorbiscomment[key])
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir,f))
            os.rmdir(tempdir)

class EmbeddedCuesheet:
    @TEST_CUESHEET
    def testembeddedcuesheet(self):
        for (suffix,data) in zip([".cue",".toc"],
                                 [
"""eJydkF1LwzAUQN8L/Q+X/oBxk6YfyVtoM4mu68iy6WudQ8qkHbNu+u9NneCc1IdCnk649xyuUQXk
epnpHGiOMU2Q+Z5xMCuLQs0tBOq92nTy7alus3b/AUeccL5/ZIHvZdLKWXkDjKcpIg2RszjxvYUy
09IUykCwanZNe2pAHrr6tXMjVtuZ+uG27l62Dk91T03VPG8np+oYwL1cK98DsEZmd4AE5CrXZU8c
O++wh2qzQxKc4X/S/l8vTQa3i7V2kWEap/iN57l66Pcjiq93IaWDUjpOyn9LETAVyASh1y0OR4Il
Fy3hYEs4qiXB6wOQULBQkOhCygalbISUUvrnACQVERfIr1scI4K5lk9od5+/""".decode('base64').decode('zlib'),
"""eJytkLtOxDAQRfv5ipE/gB0/Y09nOYE1hDhKDIgqiqCjQwh+n11BkSJlqtuM7jlzU7u0ESDFGvty
h8IE74mUpmBcIwBOJ6yf69sHSqhTTA8Yn9pcYCiYyvh6zXHqlu5xPMc5z1BfypLOcRi6fvm7zPOU
UNyPz/lSqb3zJOA29x2K9/VrvflZvwUSkmcyLBVsiOogYtgj/vOQLOvApGGucapIxCRZ262HPsaj
oR0PqdlolvbqIS27sAWbI8BKqb0BpGd7+TsgNSwdy+0AirUD+AUsDYSu""".decode('base64').decode('zlib')]):
            sheet_file = tempfile.NamedTemporaryFile(suffix=suffix)
            try:
                sheet_file.write(data)
                sheet_file.flush()
                sheet = audiotools.read_sheet(sheet_file.name)

                basefile = tempfile.NamedTemporaryFile(
                    suffix="." + self.audio_class.SUFFIX)
                try:
                    album = self.audio_class.from_pcm(
                        basefile.name,
                        EXACT_BLANK_PCM_Reader(69470436))
                    album.set_cuesheet(sheet)
                    album_sheet = album.get_cuesheet()

                    #ensure the cuesheet embeds correctly
                    #in our current album
                    self.assertNotEqual(album_sheet,None)
                    self.assertEqual(sheet.catalog(),
                                     album_sheet.catalog())
                    self.assertEqual(sorted(sheet.ISRCs().items()),
                                     sorted(album_sheet.ISRCs().items()))
                    self.assertEqual(list(sheet.indexes()),
                                     list(album_sheet.indexes()))
                    self.assertEqual(list(sheet.pcm_lengths(69470436)),
                                     list(album_sheet.pcm_lengths(69470436)))

                    #then ensure our embedded cuesheet
                    #exports correctly to other audio formats
                    for new_class in [audiotools.FlacAudio,
                                      audiotools.OggFlacAudio,
                                      audiotools.WavPackAudio]:
                        newfile = tempfile.NamedTemporaryFile(
                            suffix="." + self.audio_class.SUFFIX)
                        try:
                            new_album = new_class.from_pcm(
                                newfile.name,
                                album.to_pcm())
                            new_album.set_cuesheet(album.get_cuesheet())
                            new_cuesheet = new_album.get_cuesheet()

                            self.assertNotEqual(new_cuesheet,None)
                            self.assertEqual(
                                new_cuesheet.catalog(),
                                album_sheet.catalog())
                            self.assertEqual(
                                sorted(new_cuesheet.ISRCs().items()),
                                sorted(album_sheet.ISRCs().items()))
                            self.assertEqual(
                                list(new_cuesheet.indexes()),
                                list(album_sheet.indexes()))
                            self.assertEqual(
                                list(new_cuesheet.pcm_lengths(69470436)),
                                list(album_sheet.pcm_lengths(69470436)))
                        finally:
                            newfile.close()
                finally:
                    basefile.close()
            finally:
                sheet_file.close()

    @TEST_CUESHEET
    def testioerrorcuesheet(self):
        data = """eJydkF1LwzAUQN8L/Q+X/oBxk6YfyVtoM4mu68iy6WudQ8qkHbNu+u9NneCc1IdCnk649xyuUQXk
epnpHGiOMU2Q+Z5xMCuLQs0tBOq92nTy7alus3b/AUeccL5/ZIHvZdLKWXkDjKcpIg2RszjxvYUy
09IUykCwanZNe2pAHrr6tXMjVtuZ+uG27l62Dk91T03VPG8np+oYwL1cK98DsEZmd4AE5CrXZU8c
O++wh2qzQxKc4X/S/l8vTQa3i7V2kWEap/iN57l66Pcjiq93IaWDUjpOyn9LETAVyASh1y0OR4Il
Fy3hYEs4qiXB6wOQULBQkOhCygalbISUUvrnACQVERfIr1scI4K5lk9od5+/""".decode('base64').decode('zlib')
        sheet_file = tempfile.NamedTemporaryFile(suffix=".cue")
        try:
            sheet_file.write(data)
            sheet_file.flush()
            sheet = audiotools.read_sheet(sheet_file.name)

            basefile = tempfile.NamedTemporaryFile(
                suffix=self.audio_class.SUFFIX)

            basefile_stat = os.stat(basefile.name)[0]
            try:
                album = self.audio_class.from_pcm(
                    basefile.name,
                    EXACT_BLANK_PCM_Reader(69470436))

                os.chmod(basefile.name,0)
                self.assertRaises(IOError,
                                  album.set_cuesheet,
                                  sheet)
                os.chmod(basefile.name,basefile_stat)
                album.set_cuesheet(sheet)
                os.chmod(basefile.name,0)
                self.assertRaises(IOError,
                                  album.get_cuesheet)
                os.chmod(basefile.name,basefile_stat)
            finally:
                os.chmod(basefile.name,basefile_stat)
                basefile.close()
        finally:
            sheet_file.close()

class LCVorbisComment:
    @TEST_METADATA
    def test_lowercase_vorbiscomment(self):
        track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))

            lc_metadata = audiotools.VorbisComment(
                    {"title":[u"track name"],
                     "tracknumber":[u"1"],
                     "tracktotal":[u"3"],
                     "album":[u"album name"],
                     "artist":[u"artist name"],
                     "performer":[u"performer name"],
                     "composer":[u"composer name"],
                     "conductor":[u"conductor name"],
                     "source medium":[u"media"],
                     "isrc":[u"isrc"],
                     "catalog":[u"catalog"],
                     "copyright":[u"copyright"],
                     "publisher":[u"publisher"],
                     "date":[u"2009"],
                     "discnumber":[u"2"],
                     "disctotal":[u"4"],
                     "comment":[u"some comment"]},
                    u"vendor string")

            metadata = audiotools.MetaData(
                track_name=u"track name",
                track_number=1,
                track_total=3,
                album_name=u"album name",
                artist_name=u"artist name",
                performer_name=u"performer name",
                composer_name=u"composer name",
                conductor_name=u"conductor name",
                media=u"media",
                ISRC=u"isrc",
                catalog=u"catalog",
                copyright=u"copyright",
                publisher=u"publisher",
                year=u"2009",
                album_number=2,
                album_total=4,
                comment=u"some comment")

            track.set_metadata(lc_metadata)
            track = audiotools.open(track_file.name)
            self.assertEqual(metadata,lc_metadata)
        finally:
            track_file.close()

    @TEST_METADATA
    def test_lowercase_vorbiscomment_field(self):
        track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))
            track.set_metadata(audiotools.MetaData(
                    track_name=u"Track Name",
                    track_number=1))
            metadata = track.get_metadata()
            if (hasattr(metadata,"vorbis_comment")):
                metadata = metadata.vorbis_comment
            self.assertEqual(metadata["TITLE"],[u"Track Name"])
            self.assertEqual(metadata["TRACKNUMBER"],[u"1"])
            self.assertEqual(metadata.track_name,u"Track Name")
            self.assertEqual(metadata.track_number,1)

            metadata["title"] = [u"New Track Name"]
            metadata["tracknumber"] = [u"2"]
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if (hasattr(metadata,"vorbis_comment")):
                metadata = metadata.vorbis_comment
            self.assertEqual(metadata["TITLE"],[u"New Track Name"])
            self.assertEqual(metadata["TRACKNUMBER"],[u"2"])
            self.assertEqual(metadata.track_name,u"New Track Name")
            self.assertEqual(metadata.track_number,2)

            metadata.track_name = "New Track Name 2"
            metadata.track_number = 3
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if (hasattr(metadata,"vorbis_comment")):
                metadata = metadata.vorbis_comment
            self.assertEqual(metadata["TITLE"],[u"New Track Name 2"])
            self.assertEqual(metadata["TRACKNUMBER"],[u"3"])
            self.assertEqual(metadata.track_name,u"New Track Name 2")
            self.assertEqual(metadata.track_number,3)
        finally:
            track_file.close()

class TestOggFlacAudio(EmbeddedCuesheet,VorbisLint,TestAiffAudio,LCVorbisComment):
    def setUp(self):
        self.audio_class = audiotools.OggFlacAudio

    @TEST_METADATA
    def testpreservevendortags(self):
        tempflac1 = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        tempflac2 = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)

        try:
            f1 = self.audio_class.from_pcm(tempflac1.name,
                                           BLANK_PCM_Reader(3))
            f1.set_metadata(DummyMetaData())

            f2 = self.audio_class.from_pcm(tempflac2.name,
                                           f1.to_pcm())

            f2.set_metadata(f1.get_metadata())

            self.assertEqual(f1.get_metadata().vorbis_comment.vendor_string,
                             f2.get_metadata().vorbis_comment.vendor_string)
        finally:
            tempflac1.close()
            tempflac2.close()

    @TEST_METADATA
    def test_oversized_images(self):
        tempflac = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            flac = self.audio_class.from_pcm(
                tempflac.name,
                BLANK_PCM_Reader(5))

            flac.set_metadata(DummyMetaData())

            orig_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,orig_md5.update)
            pcm.close()

            #add an image too large to fit into a FLAC metadata chunk
            metadata = flac.get_metadata()
            metadata.add_image(
                audiotools.Image.new(HUGE_BMP.decode('bz2'),u'',0))

            flac.set_metadata(metadata)

            #ensure that setting the metadata doesn't break the file
            new_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #ensure that setting fresh oversized metadata doesn't break the file
            metadata = audiotools.MetaData()
            metadata.add_image(
                audiotools.Image.new(HUGE_BMP.decode('bz2'),u'',0))

            flac.set_metadata(metadata)

            new_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

        finally:
            tempflac.close()

    @TEST_METADATA
    def test_oversized_text(self):
        tempflac = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        try:
            flac = self.audio_class.from_pcm(
                tempflac.name,
                BLANK_PCM_Reader(5))

            flac.set_metadata(DummyMetaData())

            orig_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,orig_md5.update)
            pcm.close()

            #add a COMMENT block too large to fit into a FLAC metadata chunk
            metadata = flac.get_metadata()
            metadata.comment = "QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2').decode('ascii')

            flac.set_metadata(metadata)

            #ensure that setting the metadata doesn't break the file
            new_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #ensure that setting fresh oversized metadata doesn't break the file
            metadata = audiotools.MetaData(
                comment = "QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2').decode('ascii'))

            flac.set_metadata(metadata)

            new_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,new_md5.update)
            pcm.close()

            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())
        finally:
            tempflac.close()

    @TEST_METADATA
    def test_oversized_metadata_via_apps(self):
        tempflac = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        tempwv = tempfile.NamedTemporaryFile(
            suffix="." + audiotools.WavPackAudio.SUFFIX)
        big_bmp = tempfile.NamedTemporaryFile(suffix=".bmp")
        big_text = tempfile.NamedTemporaryFile(suffix=".txt")
        try:
            flac = self.audio_class.from_pcm(
                tempflac.name,
                BLANK_PCM_Reader(5))

            flac.set_metadata(DummyMetaData())

            big_bmp.write(HUGE_BMP.decode('bz2'))
            big_bmp.flush()

            big_text.write("QlpoOTFBWSZTWYmtEk8AgICBAKAAAAggADCAKRoBANIBAOLuSKcKEhE1okng".decode('base64').decode('bz2'))
            big_text.flush()

            orig_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,orig_md5.update)
            pcm.close()

            #ensure that setting a big image via tracktag doesn't break the file
            subprocess.call(["tracktag","-V","quiet",
                             "--front-cover=%s" % (big_bmp.name),
                             flac.filename])
            new_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,new_md5.update)
            pcm.close()
            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            #ensure that setting big text via tracktag doesn't break the file
            subprocess.call(["tracktag","-V","quiet",
                             "--comment-file=%s" % (big_text.name),
                             flac.filename])
            new_md5 = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,new_md5.update)
            pcm.close()
            self.assertEqual(orig_md5.hexdigest(),
                             new_md5.hexdigest())

            subprocess.call(["track2track","-V","quiet","-t","wv",
                             "-o",tempwv.name,
                             flac.filename])

            wv = audiotools.open(tempwv.name)

            self.assertEqual(flac,wv)

            self.assertEqual(subprocess.call(
                    ["tracktag","-V","quiet",
                     "--front-cover=%s" % (big_bmp.name),
                     "--comment-file=%s" % (big_text.name),
                     wv.filename]),0)

            self.assertEqual(len(wv.get_metadata().images()),1)
            self.assert_(len(wv.get_metadata().comment) > 0)

            subprocess.call(["track2track","-t",self.audio_class.NAME,"-o",
                             flac.filename,wv.filename])

            flac = audiotools.open(tempflac.name)
            self.assertEqual(flac,wv)
        finally:
            tempflac.close()
            tempwv.close()
            big_bmp.close()
            big_text.close()



class TestFlacAudio(TestOggFlacAudio,TestForeignWaveChunks):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio

    @TEST_METADATA
    def test_tracklint2(self):
        #copy the test track to a temporary location
        tempflac = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            f = open("flac-id3.flac","rb")
            audiotools.transfer_data(f.read,tempflac.write)
            f.close()
            tempflac.flush()

            tempflac.seek(0,0)
            self.assertEqual(tempflac.read(3),"ID3")
            tempflac.seek(-0x80,2)
            self.assertEqual(tempflac.read(3),"TAG")

            self.assertEqual(self.__run_app__(["trackinfo",tempflac.name]),0)
            self.__check_error__(_(u"ID3v2 tag found at start of FLAC file.  Please remove with tracklint(1)"))

            #ensure that FLACs tagged with ID3v2/ID3v1 comments are scrubbed
            self.assertEqual(self.__run_app__(
                    ["tracklint","-V","quiet","--fix",tempflac.name]),0)
            flac = audiotools.open(tempflac.name)
            md5sum = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,md5sum.update)
            pcm.close()
            self.assertEqual(md5sum.hexdigest(),
                             "9a0ab096c517a627b0ab5a0b959e5f36")
        finally:
            tempflac.close()

    @TEST_METADATA
    def test_tracklint3(self):
        #copy the test track to a temporary location
        tempflac = tempfile.NamedTemporaryFile(suffix=".flac")
        try:
            f = open("flac-disordered.flac","rb")
            audiotools.transfer_data(f.read,tempflac.write)
            f.close()
            tempflac.flush()

            tempflac.seek(0,0)
            self.assertEqual(tempflac.read(4),'fLaC')
            self.assertNotEqual(ord(tempflac.read(1)) & 0x07,0)

            self.assertEqual(self.__run_app__(["trackinfo",tempflac.name]),0)
            self.__check_error__(_(u"STREAMINFO not first metadata block.  Please fix with tracklint(1)"))

            #ensure that FLACs with improper metadata ordering are reordered
            self.assertEqual(self.__run_app__(
                    ["tracklint","-V","quiet","--fix",tempflac.name]),0)
            flac = audiotools.open(tempflac.name)
            md5sum = md5()
            pcm = flac.to_pcm()
            audiotools.transfer_data(pcm.read,md5sum.update)
            pcm.close()
            self.assertEqual(md5sum.hexdigest(),
                             "9a0ab096c517a627b0ab5a0b959e5f36")
        finally:
            tempflac.close()

class APEv2Lint:
    #tracklint is tricky to test since set_metadata()
    #usually won't write anything that needs fixing.
    #For instance, it won't generate empty fields or leading zeroes in numbers.
    #So, bogus ID3 tags must be generated at a lower level.
    @TEST_METADATA
    def test_tracklint(self):
        bad_apev2 = audiotools.ApeTag(
            [audiotools.ApeTagItem(0,False,"Title","Track Name  "),
             audiotools.ApeTagItem(0,False,"Track","02"),
             audiotools.ApeTagItem(0,False,"Artist","  Some Artist"),
             audiotools.ApeTagItem(0,False,"Performer","Some Artist"),
             audiotools.ApeTagItem(0,False,"Catalog",""),
             audiotools.ApeTagItem(0,False,"Year","  "),
             audiotools.ApeTagItem(0,False,"Comment","  Some Comment  ")])

        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed,bad_apev2)

        tempdir = tempfile.mkdtemp()
        tempmp = os.path.join(tempdir,"track.%s" % (self.audio_class.SUFFIX))
        undo = os.path.join(tempdir,"undo.db")
        try:
            track = self.audio_class.from_pcm(
                tempmp,
                BLANK_PCM_Reader(10))

            track.set_metadata(bad_apev2)
            metadata = track.get_metadata()
            self.assertEqual(metadata,bad_apev2)
            for key in metadata.keys():
                self.assertEqual(metadata[key].data,bad_apev2[key].data)

            original_checksum = md5()
            f = open(track.filename,'rb')
            audiotools.transfer_data(f.read,original_checksum.update)
            f.close()

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--fix","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertNotEqual(metadata,bad_apev2)
            self.assertEqual(metadata,fixed)

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--undo","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertEqual(metadata,bad_apev2)
            self.assertNotEqual(metadata,fixed)
            for tag in metadata.tags:
                self.assertEqual(tag.data,bad_apev2[tag.key].data)
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir,f))
            os.rmdir(tempdir)

class ApeTaggedAudio:
    @TEST_METADATA
    def test_coverdump(self):
        basefile = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        imgdir = tempfile.mkdtemp()
        try:
            track = self.audio_class.from_pcm(basefile.name,
                                              BLANK_PCM_Reader(10))
            metadata = audiotools.MetaData(track_name=u"Name")
            track.set_metadata(metadata)
            metadata = track.get_metadata()
            if ((metadata is None) or (not metadata.supports_images())):
                return

            metadata.add_image(audiotools.Image.new(
                    TEST_COVER1,u"",0))
            metadata.add_image(audiotools.Image.new(
                    TEST_COVER3,u"",1))

            track.set_metadata(metadata)

            subprocess.call(["coverdump",
                             "-V","quiet",
                             "-d",imgdir,
                             track.filename])

            f = open(os.path.join(imgdir,"front_cover.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER1)
            f.close()
            f = open(os.path.join(imgdir,"back_cover.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER3)
            f.close()

            for f in os.listdir(imgdir):
                os.unlink(os.path.join(imgdir,f))

            metadata = audiotools.MetaData(track_name=u"Name")
            track.set_metadata(metadata)
            metadata = track.get_metadata()

            metadata.add_image(audiotools.Image.new(
                    TEST_COVER3,u"",0))
            metadata.add_image(audiotools.Image.new(
                    TEST_COVER1,u"",1))

            track.set_metadata(metadata)

            subprocess.call(["coverdump",
                             "-V","quiet",
                             "-d",imgdir,
                             track.filename])

            f = open(os.path.join(imgdir,"front_cover.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER3)
            f.close()
            f = open(os.path.join(imgdir,"back_cover.jpg"),"rb")
            self.assertEqual(f.read(),TEST_COVER1)
            f.close()
        finally:
            basefile.close()
            for f in os.listdir(imgdir):
                os.unlink(os.path.join(imgdir,f))
            os.rmdir(imgdir)

    def __flag_type_images_data__(self,jpeg,png,test_cover1,test_cover2):
        return zip(["--front-cover",
                    "--back-cover"],
                   [0,1],
                   [jpeg,png],
                   [test_cover1,
                    test_cover2])

class TestWavPackAudio(EmbeddedCuesheet,ApeTaggedAudio,TestForeignWaveChunks,APEv2Lint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio

class M4AMetadata:
    def DummyMetaData(self):
        return audiotools.MetaData(track_name=u"Track Name",
                                   track_number=5,
                                   album_number=2,
                                   album_name=u"Album Name",
                                   artist_name=u"Artist Name",
                                   performer_name=u"Performer",
                                   composer_name=u"Composer",
                                   copyright=u"Copyright Attribution",
                                   year=u"2008",
                                   comment=u"C\u2604mment")

    def DummyMetaData2(self):
        return audiotools.MetaData(track_name=u"New Track Name",
                                   track_number=6,
                                   track_total=10,
                                   album_number=3,
                                   album_total=4,
                                   album_name=u"New Album Name",
                                   artist_name=u"New Artist Name",
                                   performer_name=u"New Performer",
                                   composer_name=u"New Composer",
                                   copyright=u"Copyright Attribution 2",
                                   year=u"2007",
                                   comment=u"Additional C\u2604mment")

    def flag_field_values(self):
        return zip(["--name",
                    "--artist",
                    "--performer",
                    "--composer",
                    "--album",
                    "--number",
                    "--track-total",
                    "--album-number",
                    "--album-total",
                    "--year",
                    "--copyright",
                    "--comment"],
                   ["track_name",
                    "artist_name",
                    "performer_name",
                    "composer_name",
                    "album_name",
                    "track_number",
                    "track_total",
                    "album_number",
                    "album_total",
                    "year",
                    "copyright",
                    "comment"],
                   ["Track Name",
                    "Artist Name",
                    "Performer Name",
                    "Composer Name",
                    "Album Name",
                    2,
                    3,
                    4,
                    5,
                    "2008",
                    "Copyright Text",
                    "Some Lengthy Text Comment"])

    def __flag_type_images_data__(self,jpeg,png,test_cover1,test_cover2):
        return zip(["--front-cover"],
                   [0],
                   [jpeg],
                   [test_cover1])

    @TEST_METADATA
    def testimages(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if ((new_file.get_metadata() is not None)
                and (new_file.get_metadata().supports_images())):
                metadata = SmallDummyMetaData()
                new_file.set_metadata(metadata)
                self.assertEqual(metadata,new_file.get_metadata())

                image1 = audiotools.Image.new(TEST_COVER1,u'',0)
                image2 = audiotools.Image.new(TEST_COVER2,u'',0)

                metadata.add_image(image1)
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image1)
                self.assertEqual(metadata.front_covers()[0],image1)
                metadata.delete_image(metadata.images()[0])

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(len(metadata.images()),0)
                metadata.add_image(image2)

                new_file.set_metadata(metadata)
                metadata = new_file.get_metadata()
                self.assertEqual(metadata.images()[0],image2)
                self.assertEqual(metadata.front_covers()[0],image2)
        finally:
            temp.close()

    def test_coverdump(self):
        pass


# class TestAlacAudio(M4AMetadata,TestAiffAudio):
#    def setUp(self):
#        self.audio_class = audiotools.ALACAudio




class ID3Lint:
    #tracklint is tricky to test since set_metadata()
    #usually won't write anything that needs fixing.
    #For instance, it won't generate empty fields or leading zeroes in numbers.
    #So, bogus ID3 tags must be generated at a lower level.
    @TEST_EXECUTABLE
    def __test_tracklint__(self, bad_id3v2):
        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            album_number=3,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed,bad_id3v2)

        tempdir = tempfile.mkdtemp()
        tempmp = os.path.join(tempdir,"track.%s" % (self.audio_class.SUFFIX))
        undo = os.path.join(tempdir,"undo.db")
        try:
            track = self.audio_class.from_pcm(
                tempmp,
                BLANK_PCM_Reader(10))

            track.set_metadata(bad_id3v2)
            metadata = track.get_metadata()
            self.assertEqual(metadata,bad_id3v2)
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_id3v2[key])

            original_checksum = md5()
            f = open(track.filename,'rb')
            audiotools.transfer_data(f.read,original_checksum.update)
            f.close()

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--fix","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertNotEqual(metadata,bad_id3v2)
            self.assertEqual(metadata,fixed)

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--undo","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertEqual(metadata,bad_id3v2)
            self.assertNotEqual(metadata,fixed)
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_id3v2[key])
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir,f))
            os.rmdir(tempdir)

    @TEST_EXECUTABLE
    def test_tracklint_id3v22(self):
        return self.__test_tracklint__(
            audiotools.ID3v22Comment(
                [audiotools.ID3v22TextFrame.from_unicode("TT2",u"Track Name  "),
                 audiotools.ID3v22TextFrame.from_unicode("TRK",u"02"),
                 audiotools.ID3v22TextFrame.from_unicode("TPA",u"003"),
                 audiotools.ID3v22TextFrame.from_unicode("TP1",u"  Some Artist\u0000"),
                 audiotools.ID3v22TextFrame.from_unicode("TP2",u"Some Artist"),
                 audiotools.ID3v22TextFrame.from_unicode("TRC",u""),
                 audiotools.ID3v22TextFrame.from_unicode("TYE",u""),
                 audiotools.ID3v22TextFrame.from_unicode("COM",u"  Some Comment  ")]))

    @TEST_EXECUTABLE
    def test_tracklint_id3v23(self):
        return self.__test_tracklint__(
            audiotools.ID3v23Comment(
                [audiotools.ID3v23TextFrame.from_unicode("TIT2",u"Track Name  "),
                 audiotools.ID3v23TextFrame.from_unicode("TRCK",u"02"),
                 audiotools.ID3v23TextFrame.from_unicode("TPOS",u"003"),
                 audiotools.ID3v23TextFrame.from_unicode("TPE1",u"  Some Artist\u0000"),
                 audiotools.ID3v23TextFrame.from_unicode("TPE2",u"Some Artist"),
                 audiotools.ID3v23TextFrame.from_unicode("TYER",u""),
                 audiotools.ID3v23TextFrame.from_unicode("TCOP",u""),
                 audiotools.ID3v23TextFrame.from_unicode("COMM",u"  Some Comment  ")]))

    @TEST_EXECUTABLE
    def test_tracklint_id3v24(self):
        return self.__test_tracklint__(
            audiotools.ID3v24Comment(
                [audiotools.ID3v24TextFrame.from_unicode("TIT2",u"Track Name  "),
                 audiotools.ID3v24TextFrame.from_unicode("TRCK",u"02"),
                 audiotools.ID3v24TextFrame.from_unicode("TPOS",u"003"),
                 audiotools.ID3v24TextFrame.from_unicode("TPE1",u"  Some Artist\u0000"),
                 audiotools.ID3v24TextFrame.from_unicode("TPE2",u"Some Artist"),
                 audiotools.ID3v24TextFrame.from_unicode("TYER",u""),
                 audiotools.ID3v24TextFrame.from_unicode("TCOP",u""),
                 audiotools.ID3v24TextFrame.from_unicode("COMM",u"  Some Comment  ")]))

class TestMP3Audio(ID3Lint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.MP3Audio

    @TEST_EXECUTABLE
    def test_tracklint_invalid2(self):
        track_file = tempfile.NamedTemporaryFile(
            suffix="." + self.audio_class.SUFFIX)
        track_file_stat = os.stat(track_file.name)[0]

        undo_db_dir = tempfile.mkdtemp()
        undo_db = os.path.join(undo_db_dir,"undo.db")

        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))
            track.set_metadata(audiotools.MetaData(
                    track_name=u"Track Name ",
                    track_number=1))
            if (track.get_metadata() is not None):
                #writable undo DB, unwritable file
                os.chmod(track.filename,
                         track_file_stat & 0x7555)

                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix","--db",undo_db,
                         track.filename]),1)
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename":self.filename(track.filename),
                            "message":_(u"Stripped whitespace from track_name field")})
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename":self.filename(track.filename),
                            "message":_(u"Stripped whitespace from track_name field")})
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))

                #no undo DB, unwritable file
                self.assertEqual(self.__run_app__(
                        ["tracklint","--fix",track.filename]),1)
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename":self.filename(track.filename),
                            "message":_(u"Stripped whitespace from track_name field")})
                self.__check_info__(_(u"* %(filename)s: %(message)s") % \
                           {"filename":self.filename(track.filename),
                            "message":_(u"Stripped whitespace from track_name field")})
                self.__check_error__(_(u"Unable to write \"%s\"") % \
                                         (self.filename(track.filename)))
        finally:
            os.chmod(track_file.name,track_file_stat)
            track_file.close()
            for p in [os.path.join(undo_db_dir,f) for f in
                      os.listdir(undo_db_dir)]:
                os.unlink(p)
            os.rmdir(undo_db_dir)


class TestMP2Audio(TestMP3Audio):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio

    @TEST_EXECUTABLE
    def test_track2xmcd_invalid(self):
        temp_track_file1 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        temp_track_file2 = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            temp_track1 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(5))

            temp_track2 = self.audio_class.from_pcm(
                temp_track_file1.name,
                BLANK_PCM_Reader(6))

            self.assertEqual(self.__run_app__(
                    ["track2xmcd",
                     "--no-musicbrainz",
                     "--freedb-server=foo.bar",
                     "--freedb-port=9001",
                     temp_track1.filename,
                     temp_track2.filename]),1)

            #Disc ID is different in MP2 because of its lossy length
            self.__check_info__(_(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
                                   {"disc_id":u"09000b02",
                                    "server":u"foo.bar"})

            #an invalid freedb-server will generate one of the following
            #depending on whether DNS is spoofing bogus hostnames or not
            #self.__check_error__(u"[Errno 111] Connection refused")
            #self.__check_error__(u"[Errno -2] Name or service not known")

            self.assertEqual(self.__run_app__(
                    ["track2xmcd",
                     temp_track1.filename,
                     temp_track2.filename,
                     "-x","/dev/null/foo.xmcd"]),1)
            self.__check_error__(_(u"Unable to write \"%s\"") % \
                                     (self.filename("/dev/null/foo.xmcd")))
        finally:
            temp_track_file1.close()
            temp_track_file2.close()

class TestVorbisAudio(VorbisLint,TestAiffAudio,LCVorbisComment):
    def setUp(self):
        self.audio_class = audiotools.VorbisAudio

    @TEST_METADATA
    def test_bigvorbiscomment(self):
        track_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            track = self.audio_class.from_pcm(track_file.name,
                                              BLANK_PCM_Reader(5))
            pcm = track.to_pcm()
            original_pcm_sum = md5()
            audiotools.transfer_data(pcm.read,original_pcm_sum.update)
            pcm.close()

            comment = audiotools.MetaData(
                track_name=u"Name",
                track_number=1,
                comment=u"abcdefghij" * 13005)
            track.set_metadata(comment)
            track = audiotools.open(track_file.name)
            self.assertEqual(comment,track.get_metadata())

            pcm = track.to_pcm()
            new_pcm_sum = md5()
            audiotools.transfer_data(pcm.read,new_pcm_sum.update)
            pcm.close()

            self.assertEqual(original_pcm_sum.hexdigest(),
                             new_pcm_sum.hexdigest())
        finally:
            track_file.close()




class TestM4AAudio(M4AMetadata,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.M4AAudio

    @TEST_METADATA
    def test_tracklint(self):
        bad_m4a = audiotools.M4AMetaData([])
        bad_m4a['\xa9nam'] = audiotools.M4AMetaData.text_atom(
            '\xa9nam',u"Track Name  ")
        bad_m4a['\xa9ART'] = audiotools.M4AMetaData.text_atom(
            '\xa9ART',u"  Some Artist")
        bad_m4a['aART'] = audiotools.M4AMetaData.text_atom(
            'aART',u"Some Artist")
        bad_m4a['cprt'] = audiotools.M4AMetaData.text_atom(
            'cprt',u"")
        bad_m4a['\xa9day'] = audiotools.M4AMetaData.text_atom(
            '\xa9day',u"  ")
        bad_m4a['\xa9cmt'] = audiotools.M4AMetaData.text_atom(
            '\xa9cmt',u"  Some Comment  ")
        bad_m4a['trkn'] = audiotools.M4AMetaData.trkn_atom(2,0)
        bad_m4a['disk'] = audiotools.M4AMetaData.disk_atom(3,0)

        fixed = audiotools.MetaData(
            track_name=u"Track Name",
            track_number=2,
            album_number=3,
            artist_name=u"Some Artist",
            comment=u"Some Comment")

        self.assertNotEqual(fixed,bad_m4a)

        tempdir = tempfile.mkdtemp()
        tempmp = os.path.join(tempdir,"track.%s" % (self.audio_class.SUFFIX))
        undo = os.path.join(tempdir,"undo.db")
        try:
            track = self.audio_class.from_pcm(
                tempmp,
                BLANK_PCM_Reader(10))

            track.set_metadata(bad_m4a)
            metadata = track.get_metadata()
            self.assertEqual(metadata,bad_m4a)
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_m4a[key])

            original_checksum = md5()
            f = open(track.filename,'rb')
            audiotools.transfer_data(f.read,original_checksum.update)
            f.close()

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--fix","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertNotEqual(metadata,bad_m4a)
            self.assertEqual(metadata,fixed)

            subprocess.call(["tracklint",
                             "-V","quiet",
                             "--undo","--db=%s" % (undo),
                             track.filename])

            metadata = track.get_metadata()
            self.assertEqual(metadata,bad_m4a)
            self.assertNotEqual(metadata,fixed)
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_m4a[key])
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir,f))
            os.rmdir(tempdir)

class TestAACAudio(TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.AACAudio

# class TestMusepackAudio(ApeTaggedAudio,APEv2Lint,TestAiffAudio):
#     def setUp(self):
#         self.audio_class = audiotools.MusepackAudio

class TestSpeexAudio(VorbisLint,TestAiffAudio,LCVorbisComment):
    def setUp(self):
        self.audio_class = audiotools.SpeexAudio

# class TestApeAudio(TestForeignWaveChunks,APEv2Lint,TestAiffAudio):
#    def setUp(self):
#        self.audio_class = audiotools.ApeAudio

class TestID3v2(unittest.TestCase):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".mp3")

        self.mp3_file = audiotools.MP3Audio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    def __comment_test__(self,id3_class):
        self.mp3_file.set_metadata(
            id3_class.converted(DummyMetaData()))
        metadata = self.mp3_file.get_metadata()
        self.assertEqual(isinstance(metadata,id3_class),True)

        metadata.track_name = u"New Track Name"
        self.assertEqual(metadata.track_name,u"New Track Name")
        self.mp3_file.set_metadata(metadata)
        metadata2 = self.mp3_file.get_metadata()
        self.assertEqual(isinstance(metadata2,id3_class),True)
        self.assertEqual(metadata,metadata2)

        metadata = id3_class.converted(DummyMetaData3())
        for new_class in (audiotools.ID3v22Comment,
                          audiotools.ID3v23Comment,
                          audiotools.ID3v24Comment):
            self.assertEqual(metadata,new_class.converted(metadata))
            self.assertEqual(metadata.images(),
                             new_class.converted(metadata).images())

    def __dict_test__(self,id3_class):
        INTEGER_ATTRIBS = ('track_number',
                           'track_total',
                           'album_number',
                           'album_total')

        attribs1 = {}  #a dict of attribute -> value pairs ("track_name":u"foo")
        attribs2 = {}  #a dict of ID3v2 -> value pairs     ("TT2":u"foo")
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                attribs1[attribute] = attribs2[key] = u"value %d" % (i)
        attribs1["track_number"] = 2
        attribs1["track_total"] = 10
        attribs1["album_number"] = 1
        attribs1["album_total"] = 3

        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        self.mp3_file.set_metadata(id3)
        self.assertEqual(self.mp3_file.get_metadata(),id3)
        id3 = self.mp3_file.get_metadata()

        #ensure that all the attributes match up
        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(id3,attribute),value)

        #ensure that all the keys for non-integer items match up
        for (key,value) in attribs2.items():
            self.assertEqual(unicode(id3[key][0]),value)

        #ensure the keys for integer items match up
        self.assertEqual(int(id3[id3_class.INTEGER_ITEMS[0]][0]),
                         attribs1["track_number"])
        self.assertEqual(id3[id3_class.INTEGER_ITEMS[0]][0].total(),
                         attribs1["track_total"])
        self.assertEqual(int(id3[id3_class.INTEGER_ITEMS[1]][0]),
                         attribs1["album_number"])
        self.assertEqual(id3[id3_class.INTEGER_ITEMS[1]][0].total(),
                         attribs1["album_total"])

        #ensure that changing attributes changes the underlying frame
        #>>> id3.track_name = u"bar"
        #>>> id3['TT2'][0] == u"bar"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                setattr(id3,attribute,u"new value %d" % (i))
                self.assertEqual(unicode(id3[key][0]),u"new value %d" % (i))

        #ensure that changing integer attributes changes the underlying frame
        #>>> id3.track_number = 2
        #>>> id3['TRK'][0] == u"2"
        id3.track_number = 3
        id3.track_total = 0
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[0]][0]),u"3")

        id3.track_total = 8
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[0]][0]),u"3/8")

        id3.album_number = 2
        id3.album_total = 0
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[1]][0]),u"2")

        id3.album_total = 4
        self.assertEqual(unicode(id3[id3_class.INTEGER_ITEMS[1]][0]),u"2/4")


        #reset and re-check everything for the next round
        id3 = id3_class.converted(audiotools.MetaData(**attribs1))
        self.mp3_file.set_metadata(id3)
        self.assertEqual(self.mp3_file.get_metadata(),id3)
        id3 = self.mp3_file.get_metadata()

        #ensure that all the attributes match up
        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(id3,attribute),value)

        for (key,value) in attribs2.items():
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(unicode(id3[key][0]),value)
            else:
                self.assertEqual(int(id3[key][0]),value)

        #ensure that changing the underlying frames changes attributes
        #>>> id3['TT2'] = [u"bar"]
        #>>> id3.track_name == u"bar"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                id3[key] = [u"new value %d" % (i)]
                self.mp3_file.set_metadata(id3)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(getattr(id3,attribute),u"new value %d" % (i))

        #ensure that changing the underlying integer frames changes attributes
        id3[id3_class.INTEGER_ITEMS[0]] = [7]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.track_number,7)

        id3[id3_class.INTEGER_ITEMS[0]] = [u"8/9"]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.track_number,8)
        self.assertEqual(id3.track_total,9)

        id3[id3_class.INTEGER_ITEMS[1]] = [4]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.album_number,4)

        id3[id3_class.INTEGER_ITEMS[1]] = [u"5/6"]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.album_number,5)
        self.assertEqual(id3.album_total,6)

        #finally, just for kicks, ensure that explicitly setting
        #frames also changes attributes
        #>>> id3['TT2'] = [id3_class.TextFrame.from_unicode('TT2',u"foo")]
        #>>> id3.track_name = u"foo"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                id3[key] = [id3_class.TextFrame.from_unicode(key,unicode(i))]
                self.mp3_file.set_metadata(id3)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(getattr(id3,attribute),unicode(i))

        #and ensure explicitly setting integer frames also changes attribs
        id3[id3_class.INTEGER_ITEMS[0]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[0],
                                             u"4")]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.track_number,4)
        self.assertEqual(id3.track_total,0)

        id3[id3_class.INTEGER_ITEMS[0]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[0],
                                             u"2/10")]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.track_number,2)
        self.assertEqual(id3.track_total,10)

        id3[id3_class.INTEGER_ITEMS[1]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[1],
                                             u"3")]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.album_number,3)
        self.assertEqual(id3.album_total,0)

        id3[id3_class.INTEGER_ITEMS[1]] = [
            id3_class.TextFrame.from_unicode(id3_class.INTEGER_ITEMS[1],
                                             u"5/7")]
        self.mp3_file.set_metadata(id3)
        id3 = self.mp3_file.get_metadata()
        self.assertEqual(id3.album_number,5)
        self.assertEqual(id3.album_total,7)

    @TEST_METADATA
    def testid3v2_2(self):
        self.__comment_test__(audiotools.ID3v22Comment)
        self.__dict_test__(audiotools.ID3v22Comment)

    @TEST_METADATA
    def testid3v2_3(self):
        self.__comment_test__(audiotools.ID3v23Comment)
        self.__dict_test__(audiotools.ID3v23Comment)

    @TEST_METADATA
    def testid3v2_4(self):
        self.__comment_test__(audiotools.ID3v24Comment)
        self.__dict_test__(audiotools.ID3v24Comment)

    @TEST_METADATA
    def testladder(self):
        self.mp3_file.set_metadata(DummyMetaData3())
        for new_class in (audiotools.ID3v22Comment,
                          audiotools.ID3v23Comment,
                          audiotools.ID3v24Comment,
                          audiotools.ID3v23Comment,
                          audiotools.ID3v22Comment):
            metadata = new_class.converted(self.mp3_file.get_metadata())
            self.mp3_file.set_metadata(metadata)
            metadata = self.mp3_file.get_metadata()
            self.assertEqual(isinstance(metadata,new_class),True)
            self.assertEqual(metadata.__comment_name__(),
                             new_class([]).__comment_name__())
            self.assertEqual(metadata,DummyMetaData3())
            self.assertEqual(metadata.images(),DummyMetaData3().images())

    @TEST_METADATA
    def testsetpicture(self):
        m = DummyMetaData()
        m.add_image(audiotools.Image.new(TEST_COVER1,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         1))
        self.mp3_file.set_metadata(m)

        new_mp3_file = audiotools.open(self.file.name)
        m2 = new_mp3_file.get_metadata()

        self.assertEqual(m.images()[0].data,m2.images()[0].data)
        self.assertEqual(m.images()[0],m2.images()[0])

    @TEST_METADATA
    def testconvertedpicture(self):
        flac_tempfile = tempfile.NamedTemporaryFile(suffix=".flac")

        try:
            flac_file = audiotools.FlacAudio.from_pcm(
                flac_tempfile.name,BLANK_PCM_Reader(TEST_LENGTH))

            m = DummyMetaData()
            m.add_image(audiotools.Image.new(
                TEST_COVER1,
                u'Unicode \u3057\u3066\u307f\u308b',
                1))
            flac_file.set_metadata(m)

            new_mp3 = audiotools.MP3Audio.from_pcm(
                self.file.name,
                flac_file.to_pcm())
            new_mp3.set_metadata(flac_file.get_metadata())

            self.assertEqual(flac_file.get_metadata().images(),
                             new_mp3.get_metadata().images())
        finally:
            flac_tempfile.close()

    @TEST_METADATA
    def testucs2codec(self):
        #this should be 4 characters long in UCS-4 environments
        #if not, we're in a UCS-2 environment
        #which is limited to 16 bits anyway
        test_string = u'f\U0001d55foo'

        #u'\ufffd' is the "not found" character
        #this string should result from escaping through UCS-2
        test_string_out = u'f\ufffdoo'

        if (len(test_string) == 4):
            self.assertEqual(test_string,
                             test_string.encode('utf-16').decode('utf-16'))
            self.assertEqual(test_string.encode('ucs2').decode('ucs2'),
                             test_string_out)

            #ID3v2.4 supports UTF-8/UTF-16
            metadata = audiotools.ID3v24Comment.converted(DummyMetaData())
            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3,metadata)

            metadata.track_name = test_string

            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3,metadata)

            metadata.comment = test_string
            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3,metadata)

            metadata.add_image(audiotools.ID3v24Comment.PictureFrame.converted(
                    audiotools.Image.new(TEST_COVER1,
                                         test_string,
                                         0)))
            self.mp3_file.set_metadata(metadata)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(id3.images()[0].description,test_string)


            #ID3v2.3 and ID3v2.2 only support UCS-2
            for id3_class in (audiotools.ID3v23Comment,
                              audiotools.ID3v22Comment):
                metadata = audiotools.ID3v23Comment.converted(DummyMetaData())
                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3,metadata)

                #ensure that text fields round-trip correctly
                #(i.e. the extra-wide char gets replaced)
                metadata.track_name = test_string

                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3.track_name,test_string_out)

                #ensure that comment blocks round-trip correctly
                metadata.comment = test_string
                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3.track_name,test_string_out)

                #ensure that image comment fields round-trip correctly
                metadata.add_image(id3_class.PictureFrame.converted(
                        audiotools.Image.new(TEST_COVER1,
                                             test_string,
                                             0)))
                self.mp3_file.set_metadata(metadata)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(id3.images()[0].description,test_string_out)

    @TEST_METADATA
    def tearDown(self):
        self.file.close()

class TestID3v1(unittest.TestCase):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".mp3")

        self.mp3_file = audiotools.MP3Audio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    @TEST_METADATA
    def test_comment(self):
        id3v1_1 = audiotools.ID3v1Comment.converted(
            audiotools.MetaData(track_name=u"Name 1",
                                track_number=1,
                                album_name=u"Album 1",
                                artist_name=u"Artist 1",
                                year=u"2009",
                                comment=u"Comment 1"))

        self.assertEqual(self.mp3_file.get_metadata(),None)
        self.mp3_file.set_metadata(id3v1_1)
        self.assertEqual(self.mp3_file.get_metadata(),id3v1_1)
        self.assert_(isinstance(self.mp3_file.get_metadata(),
                                audiotools.ID3v1Comment))

        m = self.mp3_file.get_metadata()
        for field in ("track_name","track_number","album_name",
                      "artist_name","year","comment"):
            self.assertEqual(getattr(id3v1_1,field),
                             getattr(m,field))

        for (field,new_value) in zip(("track_name","track_number","album_name",
                                      "artist_name","year","comment"),
                                     (u"Name 2",2,u"Album 2",
                                      u"Artist 2",u"2008",u"Comment 2")):
            m = self.mp3_file.get_metadata()
            setattr(m,field,new_value)
            self.mp3_file.set_metadata(m)
            m = self.mp3_file.get_metadata()
            self.assertEqual(getattr(m,field),new_value)

        for field in ("track_name","album_name","artist_name","year","comment"):
            m = self.mp3_file.get_metadata()
            delattr(m,field)
            self.assertEqual(getattr(m,field),u"")
            self.mp3_file.set_metadata(m)
            m = self.mp3_file.get_metadata()
            self.assertEqual(getattr(m,field),u"")

        m = self.mp3_file.get_metadata()
        delattr(m,"track_number")
        self.assertEqual(getattr(m,"track_number"),0)
        self.mp3_file.set_metadata(m)
        m = self.mp3_file.get_metadata()
        self.assertEqual(getattr(m,"track_number"),0)

    @TEST_METADATA
    def tearDown(self):
        self.file.close()

class TestFlacComment(unittest.TestCase):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.flac_file = audiotools.FlacAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    @TEST_METADATA
    def testsetpicture(self):
        m = DummyMetaData()
        m.add_image(audiotools.Image.new(TEST_COVER1,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         1))
        self.flac_file.set_metadata(m)

        new_flac_file = audiotools.open(self.file.name)
        m2 = new_flac_file.get_metadata()

        self.assertEqual(m.images()[0],m2.images()[0])

    @TEST_METADATA
    def testconvertedpicture(self):
        mp3_tempfile = tempfile.NamedTemporaryFile(suffix=".mp3")

        try:
            mp3_file = audiotools.MP3Audio.from_pcm(
                mp3_tempfile.name,BLANK_PCM_Reader(TEST_LENGTH))

            m = DummyMetaData()
            m.add_image(audiotools.Image.new(
                TEST_COVER1,
                u'Unicode \u3057\u3066\u307f\u308b',
                1))
            mp3_file.set_metadata(m)

            new_flac = audiotools.FlacAudio.from_pcm(
                self.file.name,
                mp3_file.to_pcm())
            new_flac.set_metadata(mp3_file.get_metadata())

            self.assertEqual(mp3_file.get_metadata().images(),
                             new_flac.get_metadata().images())
        finally:
            mp3_tempfile.close()

    @TEST_METADATA
    def tearDown(self):
        self.file.close()


class TestWavPackAPEv2MetaData(unittest.TestCase):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".wv")

        self.ape_file = audiotools.WavPackAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

        self.tag_class = audiotools.WavePackAPEv2

    @TEST_METADATA
    def tearDown(self):
        self.file.close()

    @TEST_METADATA
    def test_comment(self):
        self.ape_file.set_metadata(DummyMetaData())
        metadata = self.ape_file.get_metadata()
        self.assert_(isinstance(metadata,self.tag_class))
        self.assertEqual(metadata,DummyMetaData())

        metadata.track_name = u"New Track Name"
        self.assertEqual(metadata.track_name,u"New Track Name")
        self.ape_file.set_metadata(metadata)
        metadata2 = self.ape_file.get_metadata()
        self.assert_(isinstance(metadata,self.tag_class))
        self.assertEqual(metadata,metadata2)

        #handle unknown fields correctly
        metadata['Foo'] = audiotools.ApeTagItem.string('Foo',u'Bar')
        self.assertEqual(metadata['Foo'].data,'Bar')
        self.ape_file.set_metadata(metadata)
        metadata2 = self.ape_file.get_metadata()
        self.assertEqual(metadata2['Foo'].data,'Bar')
        self.assertEqual(metadata,metadata2)

        metadata2['Foo'] = audiotools.ApeTagItem.string('Foo',u'Baz')
        self.assertNotEqual(metadata,metadata2)
        metadata2['Foo'] = metadata['Foo']
        self.assertEqual(metadata,metadata2)
        metadata2['Bar'] = audiotools.ApeTagItem.string('Bar',u'Blah')
        self.assertNotEqual(metadata,metadata2)
        metadata['Bar'] = metadata2['Bar']
        self.assertEqual(metadata,metadata2)
        del(metadata2['Bar'])
        self.assertRaises(KeyError,
                          metadata2.__getitem__,
                          'Bar')
        self.assertNotEqual(metadata,metadata2)

    @TEST_METADATA
    def test_dict(self):
        INTEGER_ATTRIBS = ('track_number',
                           'track_total',
                           'album_number',
                           'album_total')

        attribs1 = {}  #a dict of attribute -> value pairs ("track_name":u"foo")
        attribs2 = {}  #a dict of APEv2 -> value pairs     ("Title":u"foo")
        for (i,(attribute,key)) in enumerate(self.tag_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                attribs1[attribute] = attribs2[key] = u"value %d" % (i)
        attribs1["track_number"] = 2
        attribs1["track_total"] = 10
        attribs1["album_number"] = 1
        attribs1["album_total"] = 3

        apev2 = self.tag_class.converted(audiotools.MetaData(**attribs1))
        self.ape_file.set_metadata(apev2)
        self.assertEqual(self.ape_file.get_metadata(),apev2)
        apev2 = self.ape_file.get_metadata()

        #ensure that all the attributes match up
        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(apev2,attribute),value)

        #ensure that all the keys for non-integer items match up
        for (key,value) in attribs2.items():
            self.assertEqual(unicode(apev2[key]),value)

        #ensure the keys for integer items match up
        self.assertEqual(unicode(apev2['Track']),u'2/10')
        self.assertEqual(unicode(apev2['Media']),u'1/3')

        #ensure that changing attributes changes the underlying frame
        #>>> apev2.track_name = u"bar"
        #>>> unicode(apev2['Title']) == u"bar"
        for (i,(attribute,key)) in enumerate(self.tag_class.ATTRIBUTE_MAP.items()):
            if (key not in self.tag_class.INTEGER_ITEMS):
                setattr(apev2,attribute,u"new value %d" % (i))
                self.assertEqual(unicode(apev2[key]),u"new value %d" % (i))

        #ensure that changing integer attributes changes the underlying frame
        #>>> apev2.track_number = 2
        #>>> unicode(apev2['Track']) == u"2"
        apev2.track_number = 3
        apev2.track_total = 0
        self.assertEqual(unicode(apev2['Track']),u"3")

        apev2.track_total = 8
        self.assertEqual(unicode(apev2['Track']),u"3/8")

        apev2.album_number = 2
        apev2.album_total = 0
        self.assertEqual(unicode(apev2['Media']),u"2")

        apev2.album_total = 4
        self.assertEqual(unicode(apev2['Media']),u"2/4")

        #reset and re-check everything for the next round
        apev2 = self.tag_class.converted(audiotools.MetaData(**attribs1))
        self.ape_file.set_metadata(apev2)
        self.assertEqual(self.ape_file.get_metadata(),apev2)
        apev2 = self.ape_file.get_metadata()

        #ensure that all the attributes match up
        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(apev2,attribute),value)

        for (key,value) in attribs2.items():
            if (key not in self.tag_class.INTEGER_ITEMS):
                self.assertEqual(unicode(apev2[key]),value)
        self.assertEqual(unicode(apev2['Track']),u"2/10")
        self.assertEqual(unicode(apev2['Media']),u"1/3")

        #ensure that changing the underlying frames changes attributes
        #>>> apev2['Title'] = ApeTag.string('Title',u"bar")
        #>>> apev2.track_name == u"bar"
        for (i,(attribute,key)) in enumerate(self.tag_class.ATTRIBUTE_MAP.items()):
            if (attribute not in INTEGER_ATTRIBS):
                apev2[key] = self.tag_class.ITEM.string(key,
                                                        u"new value %d" % (i))
                self.ape_file.set_metadata(apev2)
                apev2 = self.ape_file.get_metadata()
                self.assertEqual(getattr(apev2,attribute),u"new value %d" % (i))

        #ensure that changing the underlying integer frames changes attributes
        apev2['Track'] = self.tag_class.ITEM.string('Track',u'7')
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(apev2.track_number,7)

        apev2['Track'] = self.tag_class.ITEM.string('Track',u'8/9')
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(apev2.track_number,8)
        self.assertEqual(apev2.track_total,9)

        apev2['Media'] = self.tag_class.ITEM.string('Media',u'4')
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(apev2.album_number,4)

        apev2['Media'] = self.tag_class.ITEM.string('Media',u'5/6')
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(apev2.album_number,5)
        self.assertEqual(apev2.album_total,6)

    @TEST_METADATA
    def testimages(self):
        self.ape_file.set_metadata(audiotools.MetaData(
                track_name=u'Images Track'))
        apev2 = self.ape_file.get_metadata()
        apev2.add_image(audiotools.Image.new(
                TEST_COVER1,u'',0))
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        img = apev2.front_covers()[0]
        self.assertEqual(img.data,TEST_COVER1)
        self.assertEqual(img.mime_type,u"image/jpeg")
        self.assertEqual(img.width,500)
        self.assertEqual(img.height,500)
        self.assertEqual(img.color_depth,24)
        self.assertEqual(img.color_count,0)
        self.assertEqual(img.description,u'')
        self.assertEqual(img.type,0)

        apev2.add_image(audiotools.Image.new(
                TEST_COVER2,u'',1))
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        img = apev2.back_covers()[0]
        self.assertEqual(img.data,TEST_COVER2)
        self.assertEqual(img.mime_type,u"image/png")
        self.assertEqual(img.width,500)
        self.assertEqual(img.height,500)
        self.assertEqual(img.color_depth,24)
        self.assertEqual(img.color_count,0)
        self.assertEqual(img.description,u'')
        self.assertEqual(img.type,1)

        apev2.add_image(audiotools.Image.new(
                TEST_COVER1,u'',2))
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(apev2.leaflet_pages(),[])

        self.assertEqual(len(apev2.images()),2)
        apev2.delete_image(audiotools.Image.new(
                TEST_COVER1,u'',0))
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(len(apev2.images()),1)
        apev2.delete_image(audiotools.Image.new(
                TEST_COVER2,u'',1))
        self.ape_file.set_metadata(apev2)
        apev2 = self.ape_file.get_metadata()
        self.assertEqual(len(apev2.images()),0)

    @TEST_METADATA
    def test_wvunpack(self):
        import re

        self.ape_file.set_metadata(SmallDummyMetaData())
        metadata = self.ape_file.get_metadata()
        sub = subprocess.Popen([audiotools.BIN["wvunpack"],
                                "-ss",self.ape_file.filename],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        sub.stderr.read()
        data = sub.stdout.read()
        sub.wait()
        self.assert_(len(data) > 0)
        #this assumes wvunpack -ss always outputs UTF-8
        fields = dict([(key,value.decode('utf-8')) for (key,value) in
                       re.findall(r'(.+) = (.+)',data)] + \
                      [(key,value.decode('utf-8')) for (key,value) in
                       re.findall(r'(.+):\s+(.+)',data)])
        self.assert_(len(fields) > 0)
        self.assertEqual(metadata.track_name,fields['Title'])
        self.assertEqual(metadata.artist_name,fields['Artist'])
        self.assertEqual(metadata.year,fields['Year'])
        self.assertEqual(metadata.performer_name,fields['Performer'])
        self.assertEqual(unicode(metadata.track_number),fields['Track'])
        self.assertEqual(metadata.album_name,fields['Album'])
        self.assertEqual(metadata.composer_name,fields['Composer'])
        self.assertEqual(unicode(metadata.album_number),fields['Media'])
        self.assertEqual(metadata.comment,fields['Comment'])


class TestM4AMetaData(unittest.TestCase):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".m4a")

        self.m4a_file = audiotools.M4AAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    @TEST_METADATA
    def tearDown(self):
        self.file.close()

    @TEST_METADATA
    def testsetmetadata(self):
        #does setting metadata result in a still-playable file?
        tempfile1 = tempfile.NamedTemporaryFile(suffix=".wav")
        tempfile2 = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            self.m4a_file.to_wave(tempfile1.name)
            wave1 = audiotools.open(tempfile1.name)
            self.assertEqual(wave1.sample_rate(),44100)
            self.assertEqual(wave1.bits_per_sample(),16)
            self.assertEqual(wave1.channels(),2)
            self.assertEqual(wave1.total_frames(),TEST_LENGTH * 44100)

            self.m4a_file.set_metadata(
                audiotools.MetaData(track_name=u"Track Name",
                                    track_number=1,
                                    album_name=u"Some Album Name"))

            self.m4a_file.to_wave(tempfile2.name)
            wave2 = audiotools.open(tempfile2.name)
            self.assertEqual(wave2.sample_rate(),44100)
            self.assertEqual(wave2.bits_per_sample(),16)
            self.assertEqual(wave2.channels(),2)
            self.assertEqual(wave2.total_frames(),TEST_LENGTH * 44100)
        finally:
            tempfile1.close()
            tempfile2.close()

    @TEST_METADATA
    def testcomment1(self):
        for (attribute,value,key,result) in zip(
            ["track_name",
             "artist_name",
             "year",
             "performer_name",
             "album_name",
             "composer_name",
             "comment",
             "copyright"],
            [u"Track Name\u03e8",
             u"Artist \u03e8Name",
             u"2009",
             u"Performer\u03e8 Name",
             u"Albu\u03e8m Name",
             u"Composer N\u03e8ame",
             u"Some Comm\u03e8ent",
             u"Copyright T\u03e8ext"],
            ["\xa9nam",
             "\xa9ART",
             "\xa9day",
             "aART",
             "\xa9alb",
             "\xa9wrt",
             "\xa9cmt",
             "cprt"],
            [u"Track Name\u03e8",
             u"Artist \u03e8Name",
             u"2009",
             u"Performer\u03e8 Name",
             u"Albu\u03e8m Name",
             u"Composer N\u03e8ame",
             u"Some Comm\u03e8ent",
             u"Copyright T\u03e8ext"]):
            metadata = self.m4a_file.get_metadata()
            setattr(metadata,attribute,value)
            self.m4a_file.set_metadata(metadata)
            metadata = self.m4a_file.get_metadata()
            self.assertEqual(unicode(metadata[key][0]),result)
        for (attribute,value,key,result) in zip(
            ["track_number",
             "track_total",
             "album_number",
             "album_total"],
            [1,
             3,
             2,
             4],
            ["trkn",
             "trkn",
             "disk",
             "disk"],
            ["\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00",
             "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x00",
             "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00",
             "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x04"]):
            metadata = self.m4a_file.get_metadata()
            setattr(metadata,attribute,value)
            self.m4a_file.set_metadata(metadata)
            metadata = self.m4a_file.get_metadata()
            self.assertEqual(str(metadata[key][0]),result)

    @TEST_METADATA
    def testcomment2(self):
        for (attribute,value,key) in zip(
            ["track_name",
             "artist_name",
             "year",
             "performer_name",
             "album_name",
             "composer_name",
             "comment",
             "copyright"],
            [u"Track Name\u03e8",
             u"Artist \u03e8Name",
             u"2009",
             u"Performer\u03e8 Name",
             u"Albu\u03e8m Name",
             u"Composer N\u03e8ame",
             u"Some Comm\u03e8ent",
             u"Copyright T\u03e8ext"],
            ["\xa9nam",
             "\xa9ART",
             "\xa9day",
             "aART",
             "\xa9alb",
             "\xa9wrt",
             "\xa9cmt",
             "cprt"]):
            metadata = self.m4a_file.get_metadata()
            metadata[key] = audiotools.M4AMetaData.text_atom(key,value)
            self.m4a_file.set_metadata(metadata)
            metadata = self.m4a_file.get_metadata()
            self.assertEqual(unicode(metadata[key][0]),value)
        for (attribute,value,key,result) in zip(
            ["track_number",
             "track_total",
             "album_number",
             "album_total"],
            [1,
             3,
             2,
             4],
            ["trkn",
             "trkn",
             "disk",
             "disk"],
            ["\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00",
             "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x00",
             "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00",
             "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x04"]):
            metadata = self.m4a_file.get_metadata()
            metadata[key] = audiotools.M4AMetaData.binary_atom(key,result)
            self.m4a_file.set_metadata(metadata)
            metadata = self.m4a_file.get_metadata()
            self.assertEqual(str(metadata[key][0]),result)

    @TEST_METADATA
    def testsetpicture(self):
        #setting 1 front cover is okay
        self.assertEqual(len(self.m4a_file.get_metadata().images()),0)
        m = DummyMetaData()
        m.add_image(audiotools.Image.new(TEST_COVER1,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         0))
        self.m4a_file.set_metadata(m)

        new_m4a_file = audiotools.open(self.file.name)
        m2 = new_m4a_file.get_metadata()

        self.assertEqual(len(m2.images()),1)
        image2 = m2.images()[0]
        self.assertEqual(image2.data,TEST_COVER1)
        self.assertEqual(image2.mime_type,"image/jpeg")
        self.assertEqual(image2.width,500)
        self.assertEqual(image2.height,500)
        self.assertEqual(image2.color_depth,24)
        self.assertEqual(image2.color_count,0)
        self.assertEqual(image2.description,u"")
        self.assertEqual(image2.type,0)

        #setting 2 front covers is also okay
        m = m2
        m.add_image(audiotools.Image.new(TEST_COVER2,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         0))
        self.m4a_file.set_metadata(m)

        new_m4a_file = audiotools.open(self.file.name)
        m2 = new_m4a_file.get_metadata()

        self.assertEqual(len(m2.images()),2)
        image1 = m2.images()[0]
        image2 = m2.images()[1]

        if (image2.mime_type == "image/jpeg"):
            (image1,image2) = (image2,image1)

        self.assertEqual(image1.data,TEST_COVER1)
        self.assertEqual(image1.mime_type,"image/jpeg")
        self.assertEqual(image1.width,500)
        self.assertEqual(image1.height,500)
        self.assertEqual(image1.color_depth,24)
        self.assertEqual(image1.color_count,0)
        self.assertEqual(image1.description,u"")
        self.assertEqual(image1.type,0)

        self.assertEqual(image2.data,TEST_COVER2)
        self.assertEqual(image2.mime_type,"image/png")
        self.assertEqual(image2.width,500)
        self.assertEqual(image2.height,500)
        self.assertEqual(image2.color_depth,24)
        self.assertEqual(image2.color_count,0)
        self.assertEqual(image2.description,u"")
        self.assertEqual(image2.type,0)

        #however, setting back covers are dropped
        #M4AMetaData currently supports only 1 type of cover
        m.add_image(audiotools.Image.new(TEST_COVER3,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         1))
        self.m4a_file.set_metadata(m)

        new_m4a_file = audiotools.open(self.file.name)
        m2 = new_m4a_file.get_metadata()

        self.assertEqual(len(m2.images()),2)
        image1 = m2.images()[0]
        image2 = m2.images()[1]

        if (image2.mime_type == "image/jpeg"):
            (image1,image2) = (image2,image1)

        self.assertEqual(image1.data,TEST_COVER1)
        self.assertEqual(image1.mime_type,"image/jpeg")
        self.assertEqual(image1.width,500)
        self.assertEqual(image1.height,500)
        self.assertEqual(image1.color_depth,24)
        self.assertEqual(image1.color_count,0)
        self.assertEqual(image1.description,u"")
        self.assertEqual(image1.type,0)

        self.assertEqual(image2.data,TEST_COVER2)
        self.assertEqual(image2.mime_type,"image/png")
        self.assertEqual(image2.width,500)
        self.assertEqual(image2.height,500)
        self.assertEqual(image2.color_depth,24)
        self.assertEqual(image2.color_count,0)
        self.assertEqual(image2.description,u"")
        self.assertEqual(image2.type,0)

    @TEST_METADATA
    def testconvertedpicture(self):
        m4a_tempfile = tempfile.NamedTemporaryFile(suffix=".m4a")

        try:
            m4a_file = audiotools.M4AAudio.from_pcm(
                m4a_tempfile.name,BLANK_PCM_Reader(TEST_LENGTH))

            m = DummyMetaData()
            m.add_image(audiotools.Image.new(
                TEST_COVER1,
                u'',
                1))
            m4a_file.set_metadata(m)

            new_flac = audiotools.FlacAudio.from_pcm(
                self.file.name,
                m4a_file.to_pcm())
            new_flac.set_metadata(m4a_file.get_metadata())

            self.assertEqual(m4a_file.get_metadata().images(),
                             new_flac.get_metadata().images())
        finally:
            m4a_tempfile.close()

    def __test_encoder__(self, encoder,
                         sample_rate=44100,
                         bits_per_sample=16,
                         channels=2):
        f = open("m4a-%s.m4a" % (encoder),'rb')
        temp_file = tempfile.NamedTemporaryFile(suffix=".m4a")
        try:
            audiotools.transfer_data(f.read,temp_file.write)
            temp_file.flush()
            track = audiotools.open(temp_file.name)
            self.assertEqual(track.sample_rate(),sample_rate)
            self.assertEqual(track.bits_per_sample(),bits_per_sample)
            self.assertEqual(track.channels(),channels)

            original_mdat_data = md5(track.qt_stream['mdat'].data).hexdigest()

            pcm = track.to_pcm()
            pcm_count = PCM_Count()
            audiotools.transfer_data(pcm.read,pcm_count.write)
            pcm.close()

            original_pcm_count = len(pcm_count)

            track.set_metadata(audiotools.MetaData(
                    track_name=u"Foo",
                    album_name=u"Bar",
                    images=[audiotools.Image(
                            TEST_COVER1,"image/jpeg",
                            500,500,24,0,u"",0)]))

            track = audiotools.open(temp_file.name)
            self.assertEqual(track.get_metadata().track_name,u"Foo")
            self.assertEqual(track.get_metadata().album_name,u"Bar")
            self.assertEqual(track.sample_rate(),sample_rate)
            self.assertEqual(track.bits_per_sample(),bits_per_sample)
            self.assertEqual(track.channels(),channels)

            self.assertEqual(md5(track.qt_stream['mdat'].data).hexdigest(),
                             original_mdat_data)

            pcm = track.to_pcm()
            pcm_count = PCM_Count()
            audiotools.transfer_data(pcm.read,pcm_count.write)
            pcm.close()

            self.assertEqual(len(pcm_count),original_pcm_count)

        finally:
            f.close()
            temp_file.close()

    def __test_roundtrip__(self, encoder):
        f = open("m4a-%s.m4a" % (encoder),'rb')
        temp_file = tempfile.NamedTemporaryFile(suffix=".m4a")
        try:
            audiotools.transfer_data(f.read,temp_file.write)
            temp_file.flush()
            track = audiotools.open(temp_file.name)

            original_size = os.path.getsize(temp_file.name)

            original_metadata = track.get_metadata()
            track.set_metadata(original_metadata)
            track = audiotools.open(temp_file.name)

            new_metadata = track.get_metadata()

            self.assertEqual(sorted(original_metadata.keys()),
                             sorted(new_metadata.keys()))

            for key in new_metadata.keys():
                self.assertEqual(sorted(original_metadata[key],
                                        lambda x,y: cmp(len(x),len(y))),
                                 sorted(new_metadata[key],
                                        lambda x,y: cmp(len(x),len(y))))

            self.assertEqual(original_size,os.path.getsize(temp_file.name))

        finally:
            f.close()
            temp_file.close()

    @TEST_METADATA
    def test_faac_encoder(self):
        self.__test_encoder__("faac")

    @TEST_METADATA
    def test_faac_roundtrip(self):
        self.__test_roundtrip__("faac")

    @TEST_METADATA
    def test_faac_encoder2(self):
        self.__test_encoder__("faac2",48000,16,2)

    @TEST_METADATA
    def test_faac_roundtrip2(self):
        self.__test_roundtrip__("faac2")

    @TEST_METADATA
    def test_faac_encoder3(self):
        self.__test_encoder__("faac3",96000,16,2)

    @TEST_METADATA
    def test_faac_roundtrip3(self):
        self.__test_roundtrip__("faac3")

    @TEST_METADATA
    def test_nero_encoder(self):
        self.__test_encoder__("nero")

    @TEST_METADATA
    def test_nero_roundtrip(self):
        self.__test_roundtrip__("nero")

    @TEST_METADATA
    def test_nero_encoder2(self):
        self.__test_encoder__("nero2",48000,16,1)

    @TEST_METADATA
    def test_nero_roundtrip2(self):
        self.__test_roundtrip__("nero2")

    @TEST_METADATA
    def test_nero_encoder3(self):
        self.__test_encoder__("nero3",96000,16,6)

    @TEST_METADATA
    def test_nero_roundtrip3(self):
        self.__test_roundtrip__("nero3")

    @TEST_METADATA
    def test_itunes_encoder(self):
        self.__test_encoder__("itunes")

    @TEST_METADATA
    def test_itunes_roundtrip(self):
        self.__test_roundtrip__("itunes")

class TestVorbisMetaData(unittest.TestCase):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".ogg")

        self.track = audiotools.VorbisAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    @TEST_METADATA
    def tearDown(self):
        self.file.close()

    def __track_metadata__(self):
        return self.track.get_metadata()

    def __attribute_value_key_result__(self):
        return zip(
            ["track_name",
             "album_name",
             "artist_name",
             "performer_name",
             "composer_name",
             "conductor_name",
             "media",
             "ISRC",
             "catalog",
             "copyright",
             "publisher",
             "year",
             "comment",
             "track_number",
             "track_total",
             "album_number",
             "album_total"],
            [u"Track Name\u03e8",
             u"Albu\u03e8m Name",
             u"Artist \u03e8Name",
             u"Performer\u03e8 Name",
             u"Composer N\u03e8ame",
             u"Condu\u03e8ctor Name",
             u"Med\u03e8ia",
             u"US-PR3-08-54321",
             u"Ca\u03e8talog",
             u"Copyright T\u03e8ext",
             u"Publishe\u03e8r",
             u"2009",
             u"Some Comm\u03e8ent",
             1,
             3,
             2,
             4],
            ["TITLE",
             "ALBUM",
             "ARTIST",
             "PERFORMER",
             "COMPOSER",
             "CONDUCTOR",
             "SOURCE MEDIUM",
             "ISRC",
             "CATALOG",
             "COPYRIGHT",
             "PUBLISHER",
             "DATE",
             "COMMENT",
             "TRACKNUMBER",
             "TRACKTOTAL",
             "DISCNUMBER",
             "DISCTOTAL"],
            [u"Track Name\u03e8",
             u"Albu\u03e8m Name",
             u"Artist \u03e8Name",
             u"Performer\u03e8 Name",
             u"Composer N\u03e8ame",
             u"Condu\u03e8ctor Name",
             u"Med\u03e8ia",
             u"US-PR3-08-54321",
             u"Ca\u03e8talog",
             u"Copyright T\u03e8ext",
             u"Publishe\u03e8r",
             u"2009",
             u"Some Comm\u03e8ent",
             u"1",
             u"3",
             u"2",
             u"4"])

    @TEST_METADATA
    def testcomment1(self):
        for (attribute,value,key,result) in self.__attribute_value_key_result__():
            metadata = self.__track_metadata__()
            setattr(metadata,attribute,value)
            self.track.set_metadata(metadata)
            metadata = self.__track_metadata__()
            self.assertEqual(metadata[key][0],result)

    @TEST_METADATA
    def testcomment2(self):
        for (attribute,value,key,result) in self.__attribute_value_key_result__():
            metadata = self.__track_metadata__()
            metadata[key] = [result]
            self.track.set_metadata(metadata)
            metadata = self.__track_metadata__()
            self.assertEqual(getattr(metadata,attribute),value)

    @TEST_METADATA
    def testtracktotal(self):
        metadata = self.__track_metadata__()
        metadata["TRACKNUMBER"] = [u"2/4"]
        self.assertEqual(metadata.track_number,2)
        self.assertEqual(metadata.track_total,4)
        self.track.set_metadata(metadata)
        metadata = self.__track_metadata__()
        self.assertEqual(metadata.track_number,2)
        self.assertEqual(metadata.track_total,4)

    @TEST_METADATA
    def testalbumtotal(self):
        metadata = self.__track_metadata__()
        metadata["DISCNUMBER"] = [u"1/3"]
        self.assertEqual(metadata.album_number,1)
        self.assertEqual(metadata.album_total,3)
        self.track.set_metadata(metadata)
        metadata = self.__track_metadata__()
        self.assertEqual(metadata.album_number,1)
        self.assertEqual(metadata.album_total,3)

class TestFLACMetaData(TestVorbisMetaData):
    @TEST_METADATA
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.track = audiotools.FlacAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    def __track_metadata__(self):
        return self.track.get_metadata().vorbis_comment

class TestPCMConversion(unittest.TestCase):
    @TEST_PCM
    def setUp(self):
        self.tempwav = tempfile.NamedTemporaryFile(suffix=".wav")

    @TEST_PCM
    def tearDown(self):
        self.tempwav.close()

    @TEST_PCM
    def testconversions(self):
        for (input,output) in Combinations(SHORT_PCM_COMBINATIONS,2):
            #print >>sys.stderr,repr(input),repr(output)
            reader = BLANK_PCM_Reader(5,
                                      sample_rate=input[0],
                                      channels=input[1],
                                      bits_per_sample=input[2])
            converter = audiotools.PCMConverter(reader,
                                                sample_rate=output[0],
                                                channels=output[1],
                                                bits_per_sample=output[2])
            wave = audiotools.WaveAudio.from_pcm(self.tempwav.name,converter)
            converter.close()

            self.assertEqual(wave.sample_rate(),output[0])
            self.assertEqual(wave.channels(),output[1])
            self.assertEqual(wave.bits_per_sample(),output[2])
            self.assertEqual((D.Decimal(wave.cd_frames()) / 75).to_integral(),
                             5)

class TestPCMStreamReader(unittest.TestCase):
    @TEST_PCM
    def testinvalidstreams(self):
        self.assertRaises(ValueError,
                          audiotools.pcmstream.PCMStreamReader,
                          cStringIO.StringIO(chr(0) * 10),0,False,False)

        self.assertRaises(ValueError,
                          audiotools.pcmstream.PCMStreamReader,
                          cStringIO.StringIO(chr(0) * 10),5,False,False)

        r = audiotools.pcmstream.PCMStreamReader(None,2,False,False)
        self.assertRaises(AttributeError,r.read,10)

    @TEST_PCM
    def testroundtrip(self):
        for (bytes_per_sample,big_endian) in ((1,False),(2,False),(3,False),
                                              (1,True), (2,True), (3, True)):
            #channels and sample_rate don't really matter here
            data = VARIABLE_PCM_Reader(TEST_LENGTH,
                                       bits_per_sample=bytes_per_sample * 8)
            converter = audiotools.pcmstream.PCMStreamReader(data,
                                                             bytes_per_sample,
                                                             big_endian,
                                                             False)
            md5sum = md5()
            d = converter.read(audiotools.BUFFER_SIZE)
            while (len(d) > 0):
                md5sum.update(audiotools.pcmstream.pcm_to_string(
                    d,bytes_per_sample,big_endian))
                d = converter.read(audiotools.BUFFER_SIZE)

            self.assertEqual(data.hexdigest(),md5sum.hexdigest())

    @TEST_PCM
    def testfloatroundtrip(self):
        for (bytes_per_sample,big_endian) in ((1,False),(2,False),(3,False),
                                              (1,True), (2,True), (3, True)):
            data = VARIABLE_PCM_Reader(TEST_LENGTH,
                                       bits_per_sample=bytes_per_sample * 8)
            multiplier = 1 << ((bytes_per_sample * 8) - 1)
            converter = audiotools.pcmstream.PCMStreamReader(data,
                                                             bytes_per_sample,
                                                             big_endian,
                                                             True)

            md5sum = md5()
            d = converter.read(audiotools.BUFFER_SIZE) #a list of floats
            while (len(d) > 0):
                md5sum.update(audiotools.pcmstream.pcm_to_string(
                    [int(round(f * multiplier)) for f in d],
                    bytes_per_sample,big_endian))
                d = converter.read(audiotools.BUFFER_SIZE)

            self.assertEqual(data.hexdigest(),md5sum.hexdigest())

    @TEST_PCM
    def testbyteswap(self):
        for (bytes_per_sample,big_endian) in ((1,False),(2,False),(3,False),
                                              (1,True), (2,True), (3, True)):
            data = VARIABLE_PCM_Reader(SHORT_LENGTH,
                                       bits_per_sample=bytes_per_sample * 8)
            converter = audiotools.pcmstream.PCMStreamReader(data,
                                                             bytes_per_sample,
                                                             big_endian,
                                                             False)
            #our byteswapped data
            dump = cStringIO.StringIO()
            d = converter.read(audiotools.BUFFER_SIZE)
            while (len(d) > 0):
               dump.write(audiotools.pcmstream.pcm_to_string(
                   d,bytes_per_sample,not big_endian))
               d = converter.read(audiotools.BUFFER_SIZE)

            dump.seek(0,0)

            new_data = audiotools.PCMReader(
                dump,
                sample_rate=data.sample_rate,
                bits_per_sample=data.bits_per_sample,
                channels=data.channels)

            converter = audiotools.pcmstream.PCMStreamReader(new_data,
                                                             bytes_per_sample,
                                                             not big_endian,
                                                             False)

            md5sum = md5()
            d = converter.read(audiotools.BUFFER_SIZE)
            while (len(d) > 0):
                md5sum.update(audiotools.pcmstream.pcm_to_string(
                    d,bytes_per_sample,big_endian))
                d = converter.read(audiotools.BUFFER_SIZE)

            self.assertEqual(data.hexdigest(),md5sum.hexdigest())

    @TEST_PCM
    def test8bitpcmtostring(self):
        def _8bits():
            for i in xrange(0x100):
                yield chr(i)

        le_parser = Con.ULInt8('s')
        be_parser = Con.UBInt8('s')

        for c in _8bits():
            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        le_parser.parse(c) - 0x7F],1,False))

            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        be_parser.parse(c) - 0x7F],1,True))

    @TEST_PCM
    def test16bitpcmtostring(self):
        def _16bits():
            for i in xrange(0x100):
                for j in xrange(0x100):
                    yield chr(i) + chr(j)

        le_parser = Con.SLInt16('s')
        be_parser = Con.SBInt16('s')

        for c in _16bits():
            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        le_parser.parse(c)],2,False))

            self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
                        be_parser.parse(c)],2,True))

    #this is extremely time-consuming
    #and not a test you'll want to run all the time
    #def test24bitpcmtostring(self):
    #    def _24bits():
    #        for i in xrange(0x100):
    #            for j in xrange(0x100):
    #                for k in xrange(0x100):
    #                    yield chr(i) + chr(j) + chr(k)
    #
    #    le_parser = Con.BitStruct('bits',Con.Bits('value',24,
    #                                              swapped=True,
    #                                              signed=True))
    #
    #    be_parser = Con.BitStruct('bits',Con.Bits('value',24,
    #                                              swapped=False,
    #                                              signed=True))
    #
    #    for c in _24bits():
    #        self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
    #                    le_parser.parse(c).value],3,False))
    #
    #        self.assertEqual(c,audiotools.pcmstream.pcm_to_string([
    #                    be_parser.parse(c).value],3,True))

class testbufferedstream(unittest.TestCase):
    @TEST_PCM
    def testbuffer(self):
        reader = VARIABLE_PCM_Reader(TEST_LENGTH)
        bufferedreader = audiotools.BufferedPCMReader(reader)

        output = md5()

        s = bufferedreader.read(4096)
        while (len(s) > 0):
            output.update(s)
            s = bufferedreader.read(4096)

        self.assertEqual(output.hexdigest(),reader.hexdigest())

    @TEST_PCM
    def testrandombuffer(self):
        reader = VARIABLE_PCM_Reader(TEST_LENGTH)
        bufferedreader = audiotools.BufferedPCMReader(reader)
        size = reader.total_size

        output = md5()

        while (size > 0):
            buffer_length = min(size,random.randint(1,10000))
            s = bufferedreader.read(buffer_length)
            self.assertEqual(len(s),buffer_length)
            output.update(s)
            size -= buffer_length

        self.assertEqual(output.hexdigest(),reader.hexdigest())

class testtracknumber(unittest.TestCase):
    @TEST_METADATA
    def testnumber(self):
        dir01 = tempfile.mkdtemp(suffix="01")
        dir02 = tempfile.mkdtemp(suffix="02")
        dir03 = tempfile.mkdtemp(suffix="03")
        try:
            file01 = audiotools.WaveAudio.from_pcm(
                os.path.join(dir03,"track01.wav"),
                BLANK_PCM_Reader(10))
            file02 = audiotools.WaveAudio.from_pcm(
                os.path.join(dir01,"track02.wav"),
                BLANK_PCM_Reader(10))
            file03 = audiotools.WaveAudio.from_pcm(
                os.path.join(dir02,"track03.wav"),
                BLANK_PCM_Reader(10))

            try:
                self.assertEqual(file01.track_number(),1)
                self.assertEqual(file02.track_number(),2)
                self.assertEqual(file03.track_number(),3)
            finally:
                os.unlink(file01.filename)
                os.unlink(file02.filename)
                os.unlink(file03.filename)
        finally:
            os.rmdir(dir01)
            os.rmdir(dir02)
            os.rmdir(dir03)

class testcuesheet(unittest.TestCase):
    @TEST_CUESHEET
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

    @TEST_CUESHEET
    def testreadsheet(self):
        for sheet in self.sheets():
            self.assertEqual(isinstance(sheet,self.sheet_class),True)
            self.assertEqual(sheet.catalog(),'4580226563955')
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
                             [(0,),(20885,),(42189, 42411),(49242, 49473),
                              (52754,),(69656,),(95428,),(118271, 118430),
                              (136968,),(138433, 138567),(156412,),
                              (168864,),(187716,),(192245, 192373),
                              (200347,),(204985,),(227336,),
                              (243382, 243549),(265893, 266032),
                              (292606, 292942),(302893, 303123),(321611,)])
            self.assertEqual(list(sheet.pcm_lengths(191795016)),
                             [12280380, 12657288, 4152456, 1929228,
                              9938376, 15153936, 13525176, 10900344,
                              940212, 10492860, 7321776, 11084976,
                              2738316, 4688712, 2727144, 13142388,
                              9533244, 13220004, 15823080, 5986428,
                              10870944, 2687748])

    @TEST_CUESHEET
    def testconvertsheet(self):
        import audiotools.cue
        import audiotools.toc

        for sheet in self.sheets():
            #convert to CUE and test for equality
            temp_cue_file = tempfile.NamedTemporaryFile(suffix='.cue')
            try:
                temp_cue_file.write(audiotools.cue.Cuesheet.file(
                        sheet,os.path.basename(temp_cue_file.name)))
                temp_cue_file.flush()

                cue_sheet = audiotools.read_sheet(temp_cue_file.name)

                self.assertEqual(sheet.catalog(),cue_sheet.catalog())
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
                        sheet,os.path.basename(temp_toc_file.name)))
                temp_toc_file.flush()

                toc_sheet = audiotools.read_sheet(temp_toc_file.name)

                self.assertEqual(sheet.catalog(),toc_sheet.catalog())
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
                    self.assertNotEqual(f_sheet,None)

                    self.assertEqual(sheet.catalog(),f_sheet.catalog())
                    self.assertEqual(list(sheet.indexes()),
                                     list(f_sheet.indexes()))
                    self.assertEqual(list(sheet.pcm_lengths(191795016)),
                                     list(f_sheet.pcm_lengths(191795016)))
                    self.assertEqual(sorted(sheet.ISRCs().items()),
                                     sorted(f_sheet.ISRCs().items()))
                finally:
                    temp_file.close()


class testtocsheet(testcuesheet):
    @TEST_CUESHEET
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
    @TEST_CUESHEET
    def setUp(self):
        self.sheet_class = audiotools.FlacCueSheet
        self.suffix = '.flac'
        self.test_sheets = [
            Con.Container(catalog_number = '4580226563955\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                      cuesheet_tracks = [
                    Con.Container(ISRC = 'JPG750800183',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 1,
                              track_offset = 0),
                    Con.Container(ISRC = 'JPG750800212',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 2,
                              track_offset = 12280380),
                    Con.Container(ISRC = 'JPG750800214',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0), Con.Container(offset = 130536, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 3,
                              track_offset = 24807132),
                    Con.Container(ISRC = 'JPG750800704',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0), Con.Container(offset = 135828, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 4,
                              track_offset = 28954296),
                    Con.Container(ISRC = 'JPG750800705',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 5,
                              track_offset = 31019352),
                    Con.Container(ISRC = 'JPG750800706',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 6,
                              track_offset = 40957728),
                    Con.Container(ISRC = 'JPG750800707',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 7,
                              track_offset = 56111664),
                    Con.Container(ISRC = 'JPG750800708',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 93492, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 8,
                              track_offset = 69543348),
                    Con.Container(ISRC = 'JPG750800219',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 9,
                              track_offset = 80537184),
                    Con.Container(ISRC = 'JPG750800722',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 78792, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 10,
                              track_offset = 81398604),
                    Con.Container(ISRC = 'JPG750800709',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 11,
                              track_offset = 91970256),
                    Con.Container(ISRC = 'JPG750800290',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 12,
                              track_offset = 99292032),
                    Con.Container(ISRC = 'JPG750800218',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 13,
                              track_offset = 110377008),
                    Con.Container(ISRC = 'JPG750800710',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 75264, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 14,
                              track_offset = 113040060),
                    Con.Container(ISRC = 'JPG750800217',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 15,
                              track_offset = 117804036),
                    Con.Container(ISRC = 'JPG750800531',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 16,
                              track_offset = 120531180),
                    Con.Container(ISRC = 'JPG750800225',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 17,
                              track_offset = 133673568),
                    Con.Container(ISRC = 'JPG750800711',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 98196, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 18,
                              track_offset = 143108616),
                    Con.Container(ISRC = 'JPG750800180',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 81732, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 19,
                              track_offset = 156345084),
                    Con.Container(ISRC = 'JPG750800712',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 197568, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 20,
                              track_offset = 172052328),
                    Con.Container(ISRC = 'JPG750800713',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 0),
                                                      Con.Container(offset = 135240, point_number = 1)
],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 21,
                              track_offset = 178101084),
                    Con.Container(ISRC = 'JPG750800714',
                              cuesheet_track_index = [Con.Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 22,
                              track_offset = 189107268),
                    Con.Container(ISRC = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                              cuesheet_track_index = [],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 170,
                              track_offset = 191795016)],
                      is_cd = True, lead_in_samples = 88200)]

    def sheets(self):
        for test_sheet in self.test_sheets:
            tempflacfile = tempfile.NamedTemporaryFile(suffix=self.suffix)
            try:
                tempflac = audiotools.FlacAudio.from_pcm(
                    tempflacfile.name,
                    EXACT_BLANK_PCM_Reader(191795016),
                    "1")
                metadata = tempflac.get_metadata()
                metadata.cuesheet = audiotools.FlacCueSheet(test_sheet)
                tempflac.set_metadata(metadata)

                sheet = audiotools.open(tempflacfile.name).get_metadata().cuesheet
            finally:
                tempflacfile.close()
            yield sheet

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
                   4351,[150, 21035, 42561, 49623, 52904, 69806, 95578,
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
                   4455,[150, 14731, 31177, 48245, 60099, 78289, 94077,
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
                   2888,[150, 19307, 41897, 60903, 78413, 93069, 109879,
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
                    9754332, 10701012, 11718840, 7439964, 11717664, 11446596])
                  ]

    @TEST_METADATA
    def testroundtrip(self):
        for (data,length,offsets,items,track_lengths) in self.XMCD_FILES:
            f = tempfile.NamedTemporaryFile(suffix=".xmcd")
            try:
                f.write(data)
                f.flush()

                #check that reading in an XMCD file matches
                #its expected values
                xmcd = audiotools.XMCD.read(f.name)
                self.assertEqual(length,xmcd.length)
                self.assertEqual(offsets,xmcd.offsets)
                for (pair1,pair2) in zip(sorted(items),
                                         sorted(xmcd.items())):
                    self.assertEqual(pair1,pair2)
                #self.assertEqual(dict(items),dict(xmcd.items()))

                #check that building an XMCD file from values
                #and reading it back in results in the same values
                f2 = tempfile.NamedTemporaryFile(suffix=".xmcd")
                try:
                    f2.write(xmcd.build())
                    f2.flush()

                    xmcd2 = audiotools.XMCD.read(f2.name)
                    self.assertEqual(length,xmcd2.length)
                    self.assertEqual(offsets,xmcd2.offsets)
                    for (pair1,pair2) in zip(sorted(items),
                                             sorted(xmcd2.items())):
                        self.assertEqual(pair1,pair2)
                    self.assertEqual(xmcd.length,xmcd2.length)
                    self.assertEqual(xmcd.offsets,xmcd2.offsets)
                    self.assertEqual(dict(xmcd.items()),dict(xmcd2.items()))
                finally:
                    f2.close()
            finally:
                f.close()

    @TEST_METADATA
    def testtracktagging(self):
        for (data,length,offsets,items,track_lengths) in self.XMCD_FILES:
            f = tempfile.NamedTemporaryFile(suffix=".xmcd")
            try:
                f.write(data)
                f.flush()

                xmcd = audiotools.XMCD.read(f.name)

                #build a bunch of temporary FLAC files from the track_lengths
                temp_files = [tempfile.NamedTemporaryFile(suffix=".flac")
                              for track_length in track_lengths]
                try:
                    temp_tracks = [audiotools.FlacAudio.from_pcm(
                            temp_file.name,
                            EXACT_BLANK_PCM_Reader(track_length),
                            "1")
                                   for (track_length,temp_file) in
                                   zip(track_lengths,temp_files)]

                    for i in xrange(len(track_lengths)):
                        temp_tracks[i].set_metadata(
                            audiotools.MetaData(track_number=i + 1))

                    #tag them with metadata from XMCD
                    metadata = xmcd.metadata()

                    for track in temp_tracks:
                        track.set_metadata(metadata[track.track_number()])

                    #build a new XMCD file from track metadata
                    xmcd2 = audiotools.XMCD.from_files(temp_tracks)

                    #check that the original XMCD values match the track ones
                    self.assertEqual(xmcd.length,xmcd2.length)
                    self.assertEqual(xmcd.offsets,xmcd2.offsets)
                    self.assertEqual(xmcd['DISCID'],xmcd2['DISCID'])
                    if (len([pair for pair in xmcd.items()
                             if (pair[0].startswith('TTITLE') and
                                 (u" / " in pair[1]))]) > 0):
                        self.assertEqual(xmcd['DTITLE'].split(' / ',1)[1],
                                         xmcd2['DTITLE'].split(' / ',1)[1])
                    else:
                        self.assertEqual(xmcd['DTITLE'],xmcd2['DTITLE'])
                    self.assertEqual(xmcd['DYEAR'],xmcd2['DYEAR'])
                    for (pair1,pair2) in zip(
                        sorted([pair for pair in xmcd.items()
                                if (pair[0].startswith('TTITLE'))]),
                        sorted([pair for pair in xmcd2.items()
                                if (pair[0].startswith('TTITLE'))])):
                        self.assertEqual(pair1,pair2)
                finally:
                    for t in temp_files:
                        t.close()
            finally:
                f.close()

    @TEST_METADATA
    def test_formatting(self):
        LENGTH = 1134
        OFFSETS = [150, 18740, 40778, 44676, 63267]

        #ensure that latin-1 and UTF-8 encodings are handled properly
        for (encoding,data) in zip(["ISO-8859-1","UTF-8","UTF-8"],
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
            xmcd = audiotools.XMCD(data,OFFSETS,LENGTH)
            xmcd2 = audiotools.XMCD.read_data(xmcd.build().decode(encoding))
            self.assertEqual(dict(xmcd.items()),dict(xmcd2.items()))

            xmcdfile = tempfile.NamedTemporaryFile(suffix='.xmcd')
            try:
                xmcdfile.write(xmcd.build())
                xmcdfile.flush()
                xmcd2 = audiotools.XMCD.read(xmcdfile.name)
                self.assertEqual(dict(xmcd.items()),dict(xmcd2.items()))
            finally:
                xmcdfile.close()

        #ensure that excessively long XMCD lines are wrapped properly
        xmcd = audiotools.XMCD({"TTITLE0":u"l" + (u"o" * 512) + u"ng title",
                                "TTITLE1":u"track two",
                                "TTITLE2":u"track three",
                                "TTITLE4":u"track four",
                                "TTITLE5":u"track five"},
                               OFFSETS,LENGTH)
        xmcd2 = audiotools.XMCD.read_data(xmcd.build().decode('ISO-8859-1'))
        self.assertEqual(dict(xmcd.items()),dict(xmcd2.items()))
        self.assert_(max(map(len,cStringIO.StringIO(xmcd.build()).readlines())) < 80)

        #ensure that UTF-8 multi-byte characters aren't split
        xmcd = audiotools.XMCD({"TTITLE0":u'\u30de\u30af\u30ed\u30b9' * 100,
                                "TTITLE1":u"a" + (u'\u30de\u30af\u30ed\u30b9' * 100),
                                "TTITLE2":u"ab" + (u'\u30de\u30af\u30ed\u30b9' * 100),
                                "TTITLE4":u"abc" + (u'\u30de\u30af\u30ed\u30b9' * 100),
                                "TTITLE5":u"track tw\xf3"},
                               OFFSETS,LENGTH)

        xmcd2 = audiotools.XMCD.read_data(xmcd.build().decode('UTF-8'))
        self.assertEqual(dict(xmcd.items()),dict(xmcd2.items()))
        self.assert_(max(map(len,cStringIO.StringIO(xmcd.build()))) < 80)

    @TEST_EXECUTABLE
    def testtracktag(self):
        LENGTH = 1134
        OFFSETS = [150, 18740, 40778, 44676, 63267]
        TRACK_LENGTHS = [y - x for x,y in zip(OFFSETS + [LENGTH * 75],
                                              (OFFSETS + [LENGTH * 75])[1:])]
        data = {"DTITLE":"Artist / Album",
                "TTITLE0":u"track one",
                "TTITLE1":u"track two",
                "TTITLE2":u"track three",
                "TTITLE3":u"track four",
                "TTITLE4":u"track five"}

        #construct our XMCD file
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        xmcd_file.write(audiotools.XMCD(data,OFFSETS,LENGTH).build())
        xmcd_file.flush()

        #construct a batch of temporary tracks
        temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                       for i in xrange(len(OFFSETS))]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    EXACT_BLANK_PCM_Reader(length * 44100 / 75))
                      for (track,length) in zip(temp_tracks,TRACK_LENGTHS)]
            for (i,track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            #tag them with tracktag
            subprocess.call(["tracktag","-x",xmcd_file.name] + \
                            [track.filename for track in tracks])

            #ensure the metadata values are correct
            for (track,name,i) in zip(tracks,[u"track one",
                                              u"track two",
                                              u"track three",
                                              u"track four",
                                              u"track five"],
                                      range(len(tracks))):
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name,name)
                self.assertEqual(metadata.track_number,i + 1)
                self.assertEqual(metadata.album_name,u"Album")
                self.assertEqual(metadata.artist_name,u"Artist")
        finally:
            xmcd_file.close()
            for track in temp_tracks:
                track.close()

        #construct a fresh XMCD file
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        xmcd_file.write(audiotools.XMCD(data,OFFSETS,LENGTH).build())
        xmcd_file.flush()

        #construct a batch of temporary tracks with a file missing
        temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                       for i in xrange(len(OFFSETS))]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    EXACT_BLANK_PCM_Reader(length * 44100 / 75))
                      for (track,length) in zip(temp_tracks,TRACK_LENGTHS)]
            for (i,track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            del(tracks[2])

            #tag them with tracktag
            subprocess.call(["tracktag","-x",xmcd_file.name] + \
                            [track.filename for track in tracks])

            #ensure the metadata values are correct
            for (track,name,i) in zip(tracks,[u"track one",
                                              u"track two",
                                              u"track four",
                                              u"track five"],
                                      [0,1,3,4]):
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name,name)
                self.assertEqual(metadata.track_number,i + 1)
                self.assertEqual(metadata.album_name,u"Album")
                self.assertEqual(metadata.artist_name,u"Artist")
        finally:
            xmcd_file.close()
            for track in temp_tracks:
                track.close()

        #construct a fresh XMCD file with a track missing
        del(data["TTITLE2"])
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        xmcd_file.write(audiotools.XMCD(data,OFFSETS,LENGTH).build())
        xmcd_file.flush()

        #construct a batch of temporary tracks
        temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                       for i in xrange(len(OFFSETS))]
        try:
            tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    EXACT_BLANK_PCM_Reader(length * 44100 / 75))
                      for (track,length) in zip(temp_tracks,TRACK_LENGTHS)]
            for (i,track) in enumerate(tracks):
                track.set_metadata(audiotools.MetaData(track_number=i + 1))

            #tag them with tracktag
            subprocess.call(["tracktag","-x",xmcd_file.name] + \
                            [track.filename for track in tracks])

            #ensure the metadata values are correct
            for (track,name,i) in zip(tracks,[u"track one",
                                              u"track two",
                                              u"",
                                              u"track four",
                                              u"track five"],
                                      range(len(tracks))):
                metadata = track.get_metadata()
                self.assertEqual(metadata.track_name,name)
                self.assertEqual(metadata.track_number,i + 1)
                self.assertEqual(metadata.album_name,u"Album")
                self.assertEqual(metadata.artist_name,u"Artist")
        finally:
            xmcd_file.close()
            for track in temp_tracks:
                track.close()

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
                  {1:audiotools.MetaData(track_name=u'Frontier 2059',track_number=1,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   2:audiotools.MetaData(track_name=u"Welcome To My FanClub's Night! (Sheryl On Stage)",track_number=2,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   3:audiotools.MetaData(track_name=u"What 'bout my star? (Sheryl On Stage)",track_number=3,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   4:audiotools.MetaData(track_name=u"\u5c04\u624b\u5ea7\u2606\u5348\u5f8c\u4e5d\u6642Don't be late (Sheryl On Stage)",track_number=4,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   5:audiotools.MetaData(track_name=u'Vital Force',track_number=5,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   6:audiotools.MetaData(track_name=u'\u30c8\u30e9\u30a4\u30a2\u30f3\u30b0\u30e9\u30fc',track_number=6,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   7:audiotools.MetaData(track_name=u'Zero Hour',track_number=7,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   8:audiotools.MetaData(track_name=u"What 'bout my star? @Formo",track_number=8,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   9:audiotools.MetaData(track_name=u'Innocent green',track_number=9,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   10:audiotools.MetaData(track_name=u'\u30a2\u30a4\u30e2',track_number=10,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   11:audiotools.MetaData(track_name=u'\u30d3\u30c3\u30b0\u30fb\u30dc\u30fc\u30a4\u30ba',track_number=11,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   12:audiotools.MetaData(track_name=u'Private Army',track_number=12,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   13:audiotools.MetaData(track_name=u'SMS\u5c0f\u968a\u306e\u6b4c\u301c\u3042\u306e\u5a18\u306f\u30a8\u30a4\u30ea\u30a2\u30f3',track_number=13,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   14:audiotools.MetaData(track_name=u'\u30cb\u30f3\u30b8\u30fc\u30f3 Loves you yeah!',track_number=14,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   15:audiotools.MetaData(track_name=u'\u8d85\u6642\u7a7a\u98ef\u5e97 \u5a18\u3005: CM\u30bd\u30f3\u30b0(Ranka Version)',track_number=15,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   16:audiotools.MetaData(track_name=u"Alto's Theme",track_number=16,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   17:audiotools.MetaData(track_name=u'Tally Ho!',track_number=17,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   18:audiotools.MetaData(track_name=u'The Target',track_number=18,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   19:audiotools.MetaData(track_name=u'Bajura',track_number=19,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   20:audiotools.MetaData(track_name=u'\u30ad\u30e9\u30ad\u30e9',track_number=20,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   21:audiotools.MetaData(track_name=u'\u30a2\u30a4\u30e2\u301c\u9ce5\u306e\u3072\u3068',track_number=21,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   22:audiotools.MetaData(track_name=u'Take Off',track_number=22,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   23:audiotools.MetaData(track_name=u'\u30a4\u30f3\u30d5\u30a3\u30cb\u30c6\u30a3',track_number=23,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u''),
                   24:audiotools.MetaData(track_name=u'\u30c0\u30a4\u30a2\u30e2\u30f3\u30c9 \u30af\u30ec\u30d0\u30b9',track_number=24,track_total=24,album_name=u'\u30de\u30af\u30ed\u30b9\u30d5\u30ed\u30f3\u30c6\u30a3\u30a2: \u5a18\u30d5\u30ed',artist_name=u'\u83c5\u91ce\u3088\u3046\u5b50',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'VTCL-60060',copyright=u'',publisher=u'',year=u'2008',date=u'',album_number=0,album_total=0,comment=u'')}),
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
                  {1:audiotools.MetaData(track_name=u'Scars Left by Time (feat. Dale North)',track_number=1,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Ailsean',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   2:audiotools.MetaData(track_name=u'Star Stealing Girl (feat. Miss Sara Broome)',track_number=2,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'The OneUps',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   3:audiotools.MetaData(track_name=u"A Hero's Judgement (feat. Ailsean, Dale North & Roy McClanahan)",track_number=3,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Matt Pollard',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   4:audiotools.MetaData(track_name=u'Parallelism (The Frozen Flame)',track_number=4,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Matt Pollard',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   5:audiotools.MetaData(track_name=u'Guardian of Time (feat. Greg Kennedy)',track_number=5,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Mustin',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   6:audiotools.MetaData(track_name=u'The Boy Feared by Time',track_number=6,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Ailsean',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   7:audiotools.MetaData(track_name=u'The Girl Forgotten by Time',track_number=7,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Mark Porter',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   8:audiotools.MetaData(track_name=u'Wings of Time',track_number=8,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Dale North',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   9:audiotools.MetaData(track_name=u'Good to be Home',track_number=9,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Dale North',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   10:audiotools.MetaData(track_name=u'Dream of Another Time',track_number=10,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Mustin',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   11:audiotools.MetaData(track_name=u'Fields of Time',track_number=11,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Mellogear vs. Mark Porter',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   12:audiotools.MetaData(track_name=u'To Good Friends (feat. Tim Sheehy)',track_number=12,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Dale North',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   13:audiotools.MetaData(track_name=u'The Fighting Priest',track_number=13,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Ailsean',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   14:audiotools.MetaData(track_name=u'June Mermaid',track_number=14,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Dale North',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   15:audiotools.MetaData(track_name=u'Navigation is Key! (feat. Dale North)',track_number=15,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Matt Pollard',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   16:audiotools.MetaData(track_name=u'Gentle Wind',track_number=16,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Dale North',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   17:audiotools.MetaData(track_name=u'Star of Hope (feat. Mark Porter)',track_number=17,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Dale North',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u''),
                   18:audiotools.MetaData(track_name=u'Shake the Heavens (feat. Matt Pollard & Dale North)',track_number=18,track_total=18,album_name=u'OneUp Studios presents Time & Space ~ A Tribute to Yasunori Mitsuda',artist_name=u'Mark Porter',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'',copyright=u'',publisher=u'',year=u'',date=u'',album_number=0,album_total=0,comment=u'')}),
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
                  {1:audiotools.MetaData(track_name=u'\u30e1\u30ea\u30c3\u30b5',track_number=1,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'\u30dd\u30eb\u30ce\u30b0\u30e9\u30d5\u30a3\u30c6\u30a3',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   2:audiotools.MetaData(track_name=u'\u6d88\u305b\u306a\u3044\u7f6a',track_number=2,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'\u5317\u51fa\u83dc\u5948',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   3:audiotools.MetaData(track_name=u'READY STEADY GO',track_number=3,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u"L'Arc~en~Ciel",performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   4:audiotools.MetaData(track_name=u'\u6249\u306e\u5411\u3053\u3046\u3078',track_number=4,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'YeLLOW Generation',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   5:audiotools.MetaData(track_name=u'UNDO',track_number=5,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'COOL JOKE',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   6:audiotools.MetaData(track_name=u'Motherland',track_number=6,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'Crystal Kay',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   7:audiotools.MetaData(track_name=u'\u30ea\u30e9\u30a4\u30c8',track_number=7,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'ASIAN KUNG-FU GENERATION',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u''),
                   8:audiotools.MetaData(track_name=u'I Will',track_number=8,track_total=8,album_name=u'FULLMETAL ALCHEMIST COMPLETE BEST',artist_name=u'Sowelu',performer_name=u'',composer_name=u'',conductor_name=u'',media=u'',ISRC=u'',catalog=u'SVWC-7218',copyright=u'',publisher=u'',year=u'2005',date=u'',album_number=0,album_total=0,comment=u'')})]

    @TEST_METADATA
    def testreading(self):
        #check that reading in XML file data matches
        #its expected values
        for (xml,metadata) in self.XML_FILES:
            self.assertEqual(audiotools.MusicBrainzReleaseXML.read_data(
                    xml).metadata(),metadata)

        #check that reading in an XML file matches
        #its expected values
        for (xml,metadata) in self.XML_FILES:
            f = tempfile.NamedTemporaryFile(suffix=".xml")
            try:
                f.write(xml)
                f.flush()
                self.assertEqual(audiotools.MusicBrainzReleaseXML.read(
                        f.name).metadata(),metadata)
            finally:
                f.close()

    @TEST_METADATA
    def testtracktagging(self):
        for (xml,metadata) in self.XML_FILES:
            #build a bunch of temporary FLAC files
            temp_files = [tempfile.NamedTemporaryFile(suffix=".flac")
                          for i in metadata.keys()]
            try:
                temp_tracks = [audiotools.FlacAudio.from_pcm(
                        temp_file.name,
                        BLANK_PCM_Reader(5),
                        "1") for temp_file in temp_files]
                for (i,track) in enumerate(temp_tracks):
                    track.set_metadata(audiotools.MetaData(track_number=i + 1))

                #tag them with metadata from XML
                xml_metadata = audiotools.MusicBrainzReleaseXML.read_data(xml).metadata()
                for track in temp_tracks:
                    track.set_metadata(xml_metadata[track.track_number()])

                #build a new XML file from track metadata
                new_xml = audiotools.MusicBrainzReleaseXML.from_files(
                    temp_tracks)

                #check that the original XML values match the track ones
                self.assertEqual(metadata,new_xml.metadata())
            finally:
                for t in temp_files:
                    t.close()

    @TEST_METADATA
    def testtracktag(self):
        for (xml,metadata) in self.XML_FILES:
            #construct our XML file
            xml_file = tempfile.NamedTemporaryFile(suffix=".xml")
            xml_file.write(xml)
            xml_file.flush()

            #construct a batch of temporary tracks
            temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                           for i in metadata.keys()]

            try:
                tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    BLANK_PCM_Reader(5),
                    "1")
                          for track in temp_tracks]

                for (i,track) in enumerate(tracks):
                    track.set_metadata(audiotools.MetaData(track_number=i + 1))

                #tag them with tracktag
                subprocess.call(["tracktag","-x",xml_file.name] + \
                                    [track.filename for track in tracks])

                #ensure the metadata values are correct
                for track in tracks:
                    self.assertEqual(track.get_metadata(),
                                     metadata[track.track_number()])
            finally:
                xml_file.close()
                for track in temp_tracks:
                    track.close()

    @TEST_EXECUTABLE
    def testtracktag(self):
        for (xml,metadata) in self.XML_FILES:
            #construct our XML file
            xml_file = tempfile.NamedTemporaryFile(suffix=".xml")
            xml_file.write(xml)
            xml_file.flush()

            #construct a batch of temporary tracks
            temp_tracks = [tempfile.NamedTemporaryFile(suffix=".flac")
                           for i in metadata.keys()]

            try:
                tracks = [audiotools.FlacAudio.from_pcm(
                    track.name,
                    BLANK_PCM_Reader(5),
                    "1")
                          for track in temp_tracks]

                for (i,track) in enumerate(tracks):
                    track.set_metadata(audiotools.MetaData(track_number=i + 1))

                #remove one of the tracks from consideration
                tracks = [track for track in tracks if
                          track.track_number() != 2]

                #tag them with tracktag
                subprocess.call(["tracktag","-x",xml_file.name] + \
                                    [track.filename for track in tracks])

                #ensure the metadata values are correct
                for track in tracks:
                    self.assertEqual(track.get_metadata(),
                                     metadata[track.track_number()])
            finally:
                xml_file.close()
                for track in temp_tracks:
                    track.close()

    @TEST_METADATA
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

        self.assertEqual(audiotools.MusicBrainzReleaseXML.read_data(
                VALID_ORDER).metadata(),
                         audiotools.MusicBrainzReleaseXML.read_data(
                INVALID_ORDER).metadata())

        self.assertEqual(audiotools.MusicBrainzReleaseXML.read_data(
                VALID_ORDER).build().replace('\n',''),
                         VALID_ORDER.replace('\n',''))

        self.assertEqual(audiotools.MusicBrainzReleaseXML.read_data(
                INVALID_ORDER).build().replace('\n',''),
                         VALID_ORDER.replace('\n',''))

class TestProgramOutput(TestTextOutput):
    @TEST_EXECUTABLE
    def setUp(self):
        self.dir1 = tempfile.mkdtemp()
        self.dir2 = tempfile.mkdtemp()
        self.format_string = "%(track_number)2.2d - %(track_name)s.%(suffix)s"

        metadata1 = audiotools.MetaData(
            track_name=u"ASCII-only name",
            track_number=1)

        metadata2 = audiotools.MetaData(
            track_name=u"L\u00e0t\u00edn-1 N\u00e4m\u00ea",
            track_number=2)

        metadata3 = audiotools.MetaData(
            track_name=u"Unicode %s" % \
                (u"".join(map(unichr,range(0x30a1,0x30b2 + 1)))),
            track_number=3)

        self.flac1 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir1,
                audiotools.FlacAudio.track_name(1,
                                                metadata1,
                                                format=self.format_string)),
            BLANK_PCM_Reader(4),
            compression="1")
        self.flac1.set_metadata(metadata1)

        self.flac2 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir1,
                audiotools.FlacAudio.track_name(2,
                                                metadata2,
                                                format=self.format_string)),
            BLANK_PCM_Reader(5),
            compression="1")
        self.flac2.set_metadata(metadata2)

        self.flac3 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir1,
                audiotools.FlacAudio.track_name(3,
                                                metadata3,
                                                format=self.format_string)),
            BLANK_PCM_Reader(6),
            compression="1")
        self.flac3.set_metadata(metadata3)

        self.stdout = cStringIO.StringIO("")
        self.stderr = cStringIO.StringIO("")

    @TEST_EXECUTABLE
    def tearDown(self):
        for f in os.listdir(self.dir1):
            os.unlink(os.path.join(self.dir1,f))
        os.rmdir(self.dir1)

        for f in os.listdir(self.dir2):
            os.unlink(os.path.join(self.dir2,f))
        os.rmdir(self.dir2)


    @TEST_EXECUTABLE
    def test_track2track1(self):
        returnval = self.__run_app__(
            ["track2track","-j",str(1),"-t","flac","-d",self.dir2,
             self.flac1.filename,self.flac2.filename,self.flac3.filename])

        self.assertEqual(returnval,0)
        self.__check_info__(_(u"%s -> %s" % \
                                  (self.filename(self.flac1.filename),
                                   self.filename(os.path.join(
                            self.dir2,os.path.basename(self.flac1.filename))))))
        self.__check_info__(_(u"%s -> %s" % \
                                  (self.filename(self.flac2.filename),
                                   self.filename(os.path.join(
                            self.dir2,os.path.basename(self.flac2.filename))))))
        self.__check_info__(_(u"%s -> %s" % \
                                  (self.filename(self.flac3.filename),
                                   self.filename(os.path.join(
                            self.dir2,os.path.basename(self.flac3.filename))))))
        self.__check_info__(_(u"Adding ReplayGain metadata.  This may take some time."))

    @TEST_EXECUTABLE
    def test_track2track2(self):
        self.assertEqual(self.__run_app__(
                ["track2track","-d",self.dir2,"-o","fail.flac",
                 self.flac1.filename]),1)
        self.__check_error__(_(u"-o and -d options are not compatible"))
        self.__check_info__(_(u"Please specify either -o or -d but not both"))

        self.assertEqual(self.__run_app__(
                ["track2track","--format=%(track_name)s",
                 "-o",os.path.join(self.dir2,"warn.flac"),
                 self.flac1.filename]),0)
        self.__check_warning__(_(u"--format has no effect when used with -o"))

        self.assertEqual(self.__run_app__(
                ["track2track","-t","flac","-q","help"]),0)
        self.__check_info__(_(u"Available compression types for %s:") % \
                                (audiotools.FlacAudio.NAME))
        for m in audiotools.FlacAudio.COMPRESSION_MODES:
            self.__check_info__(m.decode('ascii'))

        self.assertEqual(self.__run_app__(
                ["track2track","-t","wav","-q","help"]),0)

        self.__check_error__(_(u"Audio type %s has no compression modes") % \
                                 (audiotools.WaveAudio.NAME))

        self.assertEqual(self.__run_app__(
                ["track2track","-t","flac","-q","foobar"]),1)

        self.__check_error__(_(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") % \
                                 {"quality":"foobar",
                                  "type":audiotools.FlacAudio.NAME})

        self.assertEqual(self.__run_app__(
                ["track2track","-t","flac","-d",self.dir2]),1)

        self.__check_error__(_(u"You must specify at least 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["track2track","-j",str(0),"-t","flac","-d",self.dir2,
                 self.flac1.filename]),1)

        self.__check_error__(_(u'You must run at least 1 process at a time'))

        self.assertEqual(self.__run_app__(
                ["track2track","-o","fail.flac",
                 self.flac1.filename,self.flac2.filename,self.flac3.filename]),1)

        self.__check_error__(_(u'You may specify only 1 input file for use with -o'))

        self.assertEqual(self.__run_app__(
                ["track2track","-t","flac","-d",self.dir2,
                 "-x","/dev/null",
                 self.flac1.filename,self.flac2.filename,self.flac3.filename]),
                         1)

        self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

        self.assertEqual(self.__run_app__(
                ["track2track","--format=%(foo)s","-t","flac","-d",self.dir2,
                 self.flac1.filename]),1)

        self.__check_error__(_(u"Unknown field \"%s\" in file format") % \
                            ("foo"))
        self.__check_info__(_(u"Supported fields are:"))
        for field in sorted(audiotools.MetaData.__FIELDS__ + \
                                ("album_track_number","suffix")):
            if (field == 'track_number'):
                self.__check_info__(u"%(track_number)2.2d")
            else:
                self.__check_info__(u"%%(%s)s" % (field))

        #FIXME - check invalid thumbnails

    @TEST_EXECUTABLE
    def test_track2track3(self):
        self.assertEqual(self.__run_app__(
                ["track2track","-j",str(1),"-t","mp3","--replay-gain",
                 "-d",self.dir2,self.flac1.filename]),0)

        self.__check_info__(_(u"%s -> %s" % \
                                  (self.filename(self.flac1.filename),
                                   self.filename(os.path.join(
                            self.dir2,self.format_string % \
                                {"track_number":1,
                                 "track_name":"ASCII-only name",
                                 "suffix":"mp3"})))))

        self.__check_info__(_(u"Applying ReplayGain.  This may take some time."))

    @TEST_EXECUTABLE
    def test_coverdump1(self):
        m1 = self.flac1.get_metadata()
        m1.add_image(audiotools.Image.new(TEST_COVER1,u'',0))
        self.flac1.set_metadata(m1)

        self.assertEqual(self.__run_app__(
                ["coverdump","-d",self.dir2]),1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["coverdump","-d",self.dir2,"/dev/null"]),1)

        self.__check_error__(_(u"%s file format not supported") % ("/dev/null"))

        self.assertEqual(self.__run_app__(
                ["coverdump","-d",self.dir2,self.flac1.filename]),0)

        self.__check_info__(
            self.filename(os.path.join(self.dir2,"front_cover.jpg")))

    @TEST_EXECUTABLE
    def test_coverdump2(self):
        m1 = self.flac1.get_metadata()
        m1.add_image(audiotools.Image.new(TEST_COVER1,u'',0))
        m1.add_image(audiotools.Image.new(TEST_COVER2,u'',2))
        m1.add_image(audiotools.Image.new(TEST_COVER3,u'',2))
        self.flac1.set_metadata(m1)

        self.assertEqual(self.__run_app__(
                ["coverdump","-d",self.dir2,self.flac1.filename]),0)

        self.__check_info__(
            self.filename(os.path.join(self.dir2,"front_cover.jpg")))
        self.__check_info__(
            self.filename(os.path.join(self.dir2,"leaflet01.png")))
        self.__check_info__(
            self.filename(os.path.join(self.dir2,"leaflet02.jpg")))

    @TEST_EXECUTABLE
    def test_trackcat1(self):
        self.assertEqual(self.__run_app__(
                ["trackcat",self.flac1.filename,self.flac2.filename,
                 self.flac3.filename]),1)
        self.__check_error__(_(u'You must specify an output file'))

        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","flac","-q","help"]),0)
        self.__check_info__(_(u"Available compression types for %s:") % \
                         (audiotools.FlacAudio.NAME))
        for m in audiotools.FlacAudio.COMPRESSION_MODES:
            self.__check_info__(m.decode('ascii'))

        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","wav","-q","help"]),0)

        self.__check_error__(_(u"Audio type %s has no compression modes") % \
                                 (audiotools.WaveAudio.NAME))

        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","flac","-q","foobar",
                 self.flac1.filename,self.flac2.filename,self.flac3.filename]),
                         1)

        self.__check_error__(_(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") % \
                                 {"quality":"foobar",
                                  "type":audiotools.FlacAudio.NAME})

    @TEST_EXECUTABLE
    def test_trackcat2(self):
        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","flac"]),1)

        self.__check_error__(_(u"You must specify at least 1 supported audio file"))

        flac4 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.dir1,"test4.flac"),
            BLANK_PCM_Reader(4,sample_rate=48000))

        flac5 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.dir1,"test5.flac"),
            BLANK_PCM_Reader(4,channels=6))

        flac6 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.dir1,"test6.flac"),
            BLANK_PCM_Reader(4,bits_per_sample=24))

        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","flac",
                 self.flac1.filename,self.flac2.filename,
                 self.flac3.filename,flac4.filename]),1)

        self.__check_error__(_(u"All audio files must have the same sample rate"))

        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","flac",
                 self.flac1.filename,self.flac2.filename,
                 self.flac3.filename,flac5.filename]),1)

        self.__check_error__(_(u"All audio files must have the same channel count"))

        self.assertEqual(self.__run_app__(
                ["trackcat","-o","fail.flac","-t","flac",
                 self.flac1.filename,self.flac2.filename,
                 self.flac3.filename,flac6.filename]),1)

        self.__check_error__(_(u"All audio files must have the same bits per sample"))

    @TEST_EXECUTABLE
    def test_trackcmp1(self):
        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac1.filename]),1)

        self.__check_usage__("trackcmp",_(u"<path 1> <path 2>"))

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac1.filename,self.dir2]),1)

        self.__check_output__(_(u"%(file1)s %(file2)s differ") % \
                                  {"file1":self.filename(self.flac1.filename),
                                   "file2":self.filename(self.dir2)})

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac1.filename,self.flac2.filename,
                 self.flac3.filename]),1)

        self.__check_usage__("trackcmp",_(u"<path 1> <path 2>"))

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac1.filename,self.flac2.filename]),1)

        self.__check_output__(_(u"%(file1)s != %(file2)s") % \
                                {"file1":self.filename(self.flac1.filename),
                                 "file2":self.filename(self.flac2.filename)})

    @TEST_EXECUTABLE
    def test_trackcmp2(self):
        subprocess.call(["cp","-f",self.flac1.filename,self.dir2])
        subprocess.call(["cp","-f",self.flac2.filename,self.dir2])
        subprocess.call(["cp","-f",self.flac3.filename,self.dir2])

        flac4 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac1.filename)))

        flac5 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac2.filename)))

        flac6 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac3.filename)))

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),0)
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac3.filename),
                                    "file2":self.filename(flac6.filename)})+\
                                  _(u"OK"))

        subprocess.call(["rm","-f",flac6.filename])

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        #FIXME - the "track %2.2d" and "album %d track %2.2d" templates
        #should be internationalized
        self.__check_output__(_(u"%s: missing") % \
                                  (self.filename(
                    os.path.join(self.dir2,
                                 "track %2.2d" % (3)))))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))

        subprocess.call(["mv","-f",self.flac3.filename,flac6.filename])

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        self.__check_output__(_(u"%s: missing") % \
                                  (self.filename(
                    os.path.join(self.dir1,
                                 "track %2.2d" % (3)))))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))

    @TEST_EXECUTABLE
    def test_trackcmp3(self):
        m = self.flac1.get_metadata()
        m.album_number = 1
        self.flac1.set_metadata(m)

        m = self.flac2.get_metadata()
        m.album_number = 1
        self.flac2.set_metadata(m)

        m = self.flac3.get_metadata()
        m.album_number = 1
        self.flac3.set_metadata(m)

        subprocess.call(["cp","-f",self.flac1.filename,self.dir2])
        subprocess.call(["cp","-f",self.flac2.filename,self.dir2])
        subprocess.call(["cp","-f",self.flac3.filename,self.dir2])

        flac4 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac1.filename)))

        flac5 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac2.filename)))

        flac6 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac3.filename)))

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),0)
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac3.filename),
                                    "file2":self.filename(flac6.filename)})+\
                                  _(u"OK"))

        subprocess.call(["rm","-f",flac6.filename])

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        self.__check_output__(_(u"%s: missing") % \
                                  (self.filename(
                    os.path.join(self.dir2,
                                 "album %d track %2.2d" % (1,3)))))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))

        subprocess.call(["mv","-f",self.flac3.filename,flac6.filename])

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        self.__check_output__(_(u"%s: missing") % \
                                  (self.filename(
                    os.path.join(self.dir1,
                                 "album %d track %2.2d" % (1,3)))))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))

    @TEST_EXECUTABLE
    def test_trackcmp4(self):
        subprocess.call(["cp","-f",self.flac2.filename,self.dir2])
        subprocess.call(["cp","-f",self.flac3.filename,self.dir2])

        flac4 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir2,
                audiotools.FlacAudio.track_name(1,
                                                audiotools.MetaData(
                        track_name=u"ASCII-only name",
                        track_number=1),
                                                format=self.format_string)),
            RANDOM_PCM_Reader(4),
            compression="1")

        flac5 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac2.filename)))

        flac6 = audiotools.open(os.path.join(
                self.dir2,
                os.path.basename(self.flac3.filename)))

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac1.filename,flac4.filename]),1)

        self.__check_output__(_(u"%(file1)s != %(file2)s") % \
                       {"file1":self.filename(self.flac1.filename),
                        "file2":self.filename(flac4.filename)})

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"differ"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"OK"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac3.filename),
                                    "file2":self.filename(flac6.filename)})+\
                                  _(u"OK"))

        m = flac5.get_metadata()
        flac5 = audiotools.FlacAudio.from_pcm(
            flac5.filename,
            RANDOM_PCM_Reader(5),
            compression="1")
        flac5.set_metadata(m)

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac2.filename,flac5.filename]),1)

        self.__check_output__(_(u"%(file1)s != %(file2)s") % \
                       {"file1":self.filename(self.flac2.filename),
                        "file2":self.filename(flac5.filename)})

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"differ"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"differ"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac3.filename),
                                    "file2":self.filename(flac6.filename)})+\
                                  _(u"OK"))

        m = flac6.get_metadata()
        flac6 = audiotools.FlacAudio.from_pcm(
            flac6.filename,
            RANDOM_PCM_Reader(6),
            compression="1")
        flac6.set_metadata(m)

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.flac3.filename,flac6.filename]),1)

        self.__check_output__(_(u"%(file1)s != %(file2)s") % \
                       {"file1":self.filename(self.flac3.filename),
                        "file2":self.filename(flac6.filename)})

        self.assertEqual(self.__run_app__(
                ["trackcmp",self.dir1,self.dir2]),1)

        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac1.filename),
                                    "file2":self.filename(flac4.filename)})+\
                                  _(u"differ"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac2.filename),
                                    "file2":self.filename(flac5.filename)})+\
                                  _(u"differ"))
        self.__check_output__((_(u"%(file1)s <> %(file2)s :") % \
                                   {"file1":self.filename(self.flac3.filename),
                                    "file2":self.filename(flac6.filename)})+\
                                  _(u"differ"))

    @TEST_EXECUTABLE
    def test_trackinfo(self):
        for flac in [self.flac1,self.flac2,self.flac3]:
            self.assertEqual(self.__run_app__(
                    ["trackinfo",flac.filename]),0)
            self.__check_output__(_(u"%(minutes)2.2d:%(seconds)2.2d %(channels)dch %(rate)dHz %(bits)d-bit: %(filename)s") % \
                                      {"minutes":flac.cd_frames() / 75 / 60,
                                       "seconds":flac.cd_frames() / 75 % 60,
                                       "channels":flac.channels(),
                                       "rate":flac.sample_rate(),
                                       "bits":flac.bits_per_sample(),
                                       "filename":self.filename(flac.filename)})

            self.__check_output__(_(u"%s Comment:") % ("FLAC"))
            self.__check_output__(u"      TITLE : %s" % \
                                      (flac.get_metadata().track_name))
            self.__check_output__(u"TRACKNUMBER : %s" % \
                                      (flac.get_metadata().track_number))

            self.assertEqual(self.__run_app__(
                    ["trackinfo","-n",flac.filename]),0)

            self.__check_output__(_(u"%(minutes)2.2d:%(seconds)2.2d %(channels)dch %(rate)dHz %(bits)d-bit: %(filename)s") % \
                                      {"minutes":flac.cd_frames() / 75 / 60,
                                       "seconds":flac.cd_frames() / 75 % 60,
                                       "channels":flac.channels(),
                                       "rate":flac.sample_rate(),
                                       "bits":flac.bits_per_sample(),
                                       "filename":self.filename(flac.filename)})

            self.assertEqual(self.stdout.read(),"")

            self.assertEqual(self.__run_app__(
                    ["trackinfo","-b",flac.filename]),0)

            self.__check_output__(_(u"%(bitrate)4.4s kbps: %(filename)s") % \
                               {'bitrate': ((os.path.getsize(flac.filename) * 8) / 2 ** 10) / (flac.cd_frames() / 75),
                                'filename':self.filename(flac.filename)})
            self.__check_output__(_(u"%s Comment:") % ("FLAC"))
            self.__check_output__(u"      TITLE : %s" % \
                                      (flac.get_metadata().track_name))
            self.__check_output__(u"TRACKNUMBER : %s" % \
                                      (flac.get_metadata().track_number))

            self.assertEqual(self.__run_app__(
                    ["trackinfo","-nb",flac.filename]),0)

            self.__check_output__(_(u"%(bitrate)4.4s kbps: %(filename)s") % \
                               {'bitrate': ((os.path.getsize(flac.filename) * 8) / 2 ** 10) / (flac.cd_frames() / 75),
                                'filename':self.filename(flac.filename)})

            self.assertEqual(self.stdout.read(),"")

            self.assertEqual(self.__run_app__(
                    ["trackinfo","-%",flac.filename]),0)

            self.__check_output__(_(u"%(percentage)3.3s%%: %(filename)s") % \
                           {'percentage':
                                int(round(float(os.path.getsize(flac.filename) * 100) / (flac.total_frames() * flac.channels() * \
                                                                                             (flac.bits_per_sample() / 8)))),
                            'filename':self.filename(flac.filename)})

            self.__check_output__(_(u"%s Comment:") % ("FLAC"))
            self.__check_output__(u"      TITLE : %s" % \
                                      (flac.get_metadata().track_name))
            self.__check_output__(u"TRACKNUMBER : %s" % \
                                      (flac.get_metadata().track_number))

            self.assertEqual(self.__run_app__(
                    ["trackinfo","-%n",flac.filename]),0)

            self.__check_output__(_(u"%(percentage)3.3s%%: %(filename)s") % \
                           {'percentage':
                                int(round(float(os.path.getsize(flac.filename) * 100) / (flac.total_frames() * flac.channels() * \
                                                                                             (flac.bits_per_sample() / 8)))),
                            'filename':self.filename(flac.filename)})

            self.assertEqual(self.stdout.read(),"")

    @TEST_EXECUTABLE
    def test_tracktag1(self):
        self.assertEqual(self.__run_app__(
                ["tracktag","-x","/dev/null",self.flac1.filename]),1)
        self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

        self.assertEqual(self.__run_app__(
                ["tracktag","--front-cover=/dev/null/foo.jpg",
                 self.flac1.filename]),1)
        self.__check_error__(_(u"%(filename)s: %(message)s") % \
                              {"filename":self.filename(self.flac1.filename),
                               "message":_(u"Unable to open file")})

        self.assertEqual(self.__run_app__(
                ["tracktag","--comment-file=/dev/null/file.txt",
                 self.flac1.filename]),1)
        self.__check_error__(_(u"Unable to open comment file \"%s\"") % \
                                 (self.filename("/dev/null/file.txt")))

        f = open(os.path.join(self.dir1,"comment.txt"),"w")
        f.write(os.urandom(1024) + ((u"\uFFFD".encode('utf-8')) * 103))
        f.close()

        self.assertEqual(self.__run_app__(
                ["tracktag","--comment-file=%s" % \
                     (os.path.join(self.dir1,"comment.txt")),
                 self.flac1.filename]),1)
        self.__check_error__(_(u"Comment file \"%s\" does not appear to be UTF-8 text") % \
                                 (os.path.join(self.dir1,"comment.txt")))

        self.assertEqual(self.__run_app__(
                ["tracktag","--replay-gain",
                 self.flac1.filename,self.flac2.filename,self.flac3.filename]),0)
        self.__check_info__(_(u"Adding ReplayGain metadata.  This may take some time."))

        self.assertEqual(self.__run_app__(
                ["track2track","-t","mp3","-d",self.dir2,
                 self.flac1.filename,self.flac2.filename,self.flac3.filename]),0)

        mp3_files = [os.path.join(self.dir2,f) for f in os.listdir(self.dir2)]

        self.assertEqual(self.__run_app__(
                ["tracktag","--replay-gain"] + mp3_files),0)

        self.__check_info__(_(u"Applying ReplayGain.  This may take some time."))

    @TEST_EXECUTABLE
    def test_tracklint1(self):
        self.assertEqual(self.__run_app__(
                ["tracklint","--undo",self.flac1.filename]),1)
        self.__check_error__(_(u"Cannot perform undo without undo db"))

        self.assertEqual(self.__run_app__(
                ["tracklint","--fix","--db","/dev/null/foo.db",
                 self.flac1.filename]),1)
        self.__check_error__(_(u"Unable to open \"%s\"") % \
                                 (self.filename("/dev/null/foo.db")))

        self.assertEqual(self.__run_app__(
                ["tracklint","--undo","--db","/dev/null/foo.db",
                 self.flac1.filename]),1)
        self.__check_error__(_(u"Unable to open \"%s\"") % \
                                 (self.filename("/dev/null/foo.db")))

        #FIXME - tracklint can generate swaths of info text
        #these should probably be tested somewhere

    @TEST_EXECUTABLE
    def test_trackrename(self):
        self.assertEqual(self.__run_app__(["trackrename"]),1)
        self.__check_error__(_(u"You must specify at least 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["trackrename","-x","/dev/null",self.flac1.filename]),1)
        self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

        self.assertEqual(self.__run_app__(
                ["trackrename","--format=%(foo)s",self.flac1.filename]),1)

        self.__check_error__(_(u"Unknown field \"%s\" in file format") % \
                            ("foo"))
        self.__check_info__(_(u"Supported fields are:"))
        for field in sorted(audiotools.MetaData.__FIELDS__ + \
                                ("album_track_number","suffix")):
            if (field == 'track_number'):
                self.__check_info__(u"%(track_number)2.2d")
            else:
                self.__check_info__(u"%%(%s)s" % (field))

class TestTracklengthOutput(TestTextOutput):
    @TEST_EXECUTABLE
    def setUp(self):
        self.dir1 = tempfile.mkdtemp()
        self.dir2 = tempfile.mkdtemp()
        self.format_string = "%(track_number)2.2d - %(track_name)s.%(suffix)s"

        metadata1 = audiotools.MetaData(
            track_name=u"ASCII-only name",
            track_number=1)

        metadata2 = audiotools.MetaData(
            track_name=u"L\u00e0t\u00edn-1 N\u00e4m\u00ea",
            track_number=2)

        metadata3 = audiotools.MetaData(
            track_name=u"Unicode %s" % \
                (u"".join(map(unichr,range(0x30a1,0x30b2 + 1)))),
            track_number=3)

        self.flac1 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir1,
                audiotools.FlacAudio.track_name(1,
                                                metadata1,
                                                format=self.format_string)),
            BLANK_PCM_Reader(5),
            compression="1")
        self.flac1.set_metadata(metadata1)

        self.flac2 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir1,
                audiotools.FlacAudio.track_name(2,
                                                metadata2,
                                                format=self.format_string)),
            BLANK_PCM_Reader(122,sample_rate=48000,bits_per_sample=24),
            compression="1")
        self.flac2.set_metadata(metadata2)

        self.flac3 = audiotools.FlacAudio.from_pcm(
            os.path.join(
                self.dir1,
                audiotools.FlacAudio.track_name(3,
                                                metadata3,
                                                format=self.format_string)),
            BLANK_PCM_Reader(3661,channels=1,sample_rate=22050),
            compression="1")
        self.flac3.set_metadata(metadata3)

    @TEST_EXECUTABLE
    def tearDown(self):
        for f in os.listdir(self.dir1):
            os.unlink(os.path.join(self.dir1,f))
        os.rmdir(self.dir1)

        for f in os.listdir(self.dir2):
            os.unlink(os.path.join(self.dir2,f))
        os.rmdir(self.dir2)

    @TEST_EXECUTABLE
    def test_tracklength(self):
        self.assertEqual(self.__run_app__(
                ["tracklength",self.flac1.filename]),0)
        total_length = self.flac1.cd_frames()

        self.__check_output__(_(u"%(hours)d:%(minutes)2.2d:%(seconds)2.2d") % \
                                  {"hours":total_length / (75 * 60 * 60),
                                   "minutes":total_length / (75 * 60) % 60,
                                   "seconds":int(round(total_length) / 75.0) % 60})

        self.assertEqual(self.__run_app__(
                ["tracklength",self.flac1.filename,
                 self.flac2.filename]),0)
        total_length = sum([self.flac1.cd_frames(),
                            self.flac2.cd_frames()])

        self.__check_output__(_(u"%(hours)d:%(minutes)2.2d:%(seconds)2.2d") % \
                                  {"hours":total_length / (75 * 60 * 60),
                                   "minutes":total_length / (75 * 60) % 60,
                                   "seconds":int(round(total_length) / 75.0) % 60})

        self.assertEqual(self.__run_app__(
                ["tracklength",self.flac1.filename,
                 self.flac2.filename,self.flac3.filename]),0)
        total_length = sum([self.flac1.cd_frames(),
                            self.flac2.cd_frames(),
                            self.flac3.cd_frames()])

        self.__check_output__(_(u"%(hours)d:%(minutes)2.2d:%(seconds)2.2d") % \
                                  {"hours":total_length / (75 * 60 * 60),
                                   "minutes":total_length / (75 * 60) % 60,
                                   "seconds":int(round(total_length) / 75.0) % 60})

class TestTracksplitOutput(TestTextOutput):
    @TEST_EXECUTABLE
    def setUp(self):
        self.dir1 = tempfile.mkdtemp()
        self.dir2 = tempfile.mkdtemp()

        self.cue_path = os.path.join(self.dir1,"album.cue")
        f = open(self.cue_path,"w")
        f.write('FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 03:16:55\n    INDEX 01 03:18:18\n  TRACK 03 AUDIO\n    INDEX 00 05:55:12\n    INDEX 01 06:01:45\n')
        f.close()

        self.bad_cue_path = os.path.join(self.dir1,"album2.cue")
        f = open(self.bad_cue_path,"w")
        f.write('FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 03:16:55\n    INDEX 01 03:18:18\n  TRACK 03 AUDIO\n    INDEX 00 05:55:12\n    INDEX 01 06:01:45\n  TRACK 04 AUDIO\n    INDEX 00 06:03:45\n    INDEX 01 20:00:00\n')
        f.close()

        self.xmcd_path = os.path.join(self.dir1,"album.xmcd")
        f = open(self.xmcd_path,"w")
        f.write("""eJyFk0tv20YQgO8B8h+m8MHJReXyTQFEm0pyYcAvSELTHCmKigRLYiHSanUTSdt1agd9BGnsOo3R
# uGmcNn60AYrakfNjsqVinfwXOpS0KwRtEQKL2Zmd/WZ2ZjgFXzTs8tUrU5CsYsuyl6HSshoOuJWK
# 5/heOrEnH1EEthWJIClMkUVFJVwxVFFiiiIagswU1dAFlSmGomg6BxNd0TmbSBoaJpquEW2Sgqqo
# ItdUQyCcT3RNV3kAYojKJBFREGRDm2gKmaQvipqs83uiLKmGwTVVJTqPJxqSYHBNEiRR4xEkkWij
# KiQrW/NsqDvN2341DbKk8IO80655NbeJ1kRdarm243lOGUqdNNjlcqkMbZJSUuLSnAAZ97NOq3a7
# 6sM1+zoUfKftQMGuOq0KOD5Y9VSCKKyUGjXfR0S7ZqXhI7e5nGvaCUVIqaOw2dlCZjZrygoRKmWC
# xmxxtjiXM2n0iIbHNDqk4elMfnGhOJvLw/vwlhkWafSygKuIS4L4YJsGezR49Xqne9l7ie9cJpe9
# c0Teyt3Im1hn7Fz249xCPmcW3JVm2U8G6uqV4jCigCE3aPSMhj/T8DGNXtDwJFGjHvMg5s2q5cN0
# yV3xodEBz7daH8CHM26r4TIf0UwuIyJ6zEwSgruMOgRHd2D4iOc0+gbfcXn+KP79fv/hbrz2PH74
# HQ1+o8Ev7LZs3nTqtosjX3RhvgMzVjNTXylNe7CQVP895qeY8clq/85mfPb09fZ6fHcjfrX19+mP
# /Z0w6zanfSg5ULd8h7mr//UWdqiZwxdgovdpuE+jTRqt4wamNOahm7S7dfHnGuLfPDsb7B/HZw+G
# 9e+u0e5dyMzT8HxUQriWt5rLFnzitJLZus4Ihtnf3ht8f2+wv3vx0xYvsWC+eRrQ4Cg+79EAS/Tt
# MJNDGkXYHe5FTBoc0uBe/8GTi4NtbsbiJ7li2L+wbbiBObfteNBxV6DjWFVeLCKZ8dGX8dFOvLYa
# 9/YuNk75iWwW5gvxydeDH77CNPqHW9gdGoRJSsl4HdPwYJjSr6Mh4feUSeNhMZVJ8QN1coCowYsn
# iKLBHzQ44C6a2V/dxRGmAcbEd29g/2mwipNMgx0abHJH/V2jxD2Nt6JiqYY8DLyOvwha+LwK/9tr
# +LzmV5PxaLu2Vff4DfKuKv/rYu7TYtaE5CdMw+gvREtRMEeSjKU4ltJYymOpjKU6ltpY6mNpMA4H
# MiJhSMKYhEEJoxKGJYxLGJgwssjIYkJemrtxazGfzeVx/w8vFHIR""".decode('base64').decode('zlib'))
        f.close()

        self.flac = audiotools.FlacAudio.from_pcm(
            os.path.join(self.dir1,"album.flac"),
            EXACT_BLANK_PCM_Reader(24725400),
            compression="1")

        self.flac2 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.dir1,"extra.flac"),
            BLANK_PCM_Reader(5),
            compression="1")

        self.format_string = "%(track_number)2.2d - %(track_name)s.%(suffix)s"


    @TEST_EXECUTABLE
    def tearDown(self):
        for f in os.listdir(self.dir1):
            os.unlink(os.path.join(self.dir1,f))
        os.rmdir(self.dir1)

        for f in os.listdir(self.dir2):
            os.unlink(os.path.join(self.dir2,f))
        os.rmdir(self.dir2)

    @TEST_EXECUTABLE
    @TEST_CUESHEET
    def test_tracksplit1(self):
        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-q","help"]),0)
        self.__check_info__(_(u"Available compression types for %s:") % \
                                (audiotools.FlacAudio.NAME))
        for m in audiotools.FlacAudio.COMPRESSION_MODES:
            self.__check_info__(m.decode('ascii'))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","wav","-q","help"]),0)

        self.__check_error__(_(u"Audio type %s has no compression modes") % \
                                 (audiotools.WaveAudio.NAME))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-q","foobar"]),1)

        self.__check_error__(_(u"\"%(quality)s\" is not a supported compression mode for type \"%(type)s\"") % \
                                 {"quality":"foobar",
                                  "type":audiotools.FlacAudio.NAME})

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-d",self.dir2]),1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-d",self.dir2,
                 self.flac.filename,self.flac2.filename]),1)

        self.__check_error__(_(u"You must specify exactly 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-j",str(0),"-t","flac","-d",self.dir2,
                 "--cue",self.cue_path,self.flac.filename]),1)

        self.__check_error__(_(u'You must run at least 1 process at a time'))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-d",self.dir2,
                 "--cue",self.cue_path,"-x","/dev/null",self.flac.filename]),1)

        self.__check_error__(_(u"Invalid XMCD or MusicBrainz XML file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-d",self.dir2,
                 self.flac.filename]),1)

        self.__check_error__(_(u"You must specify a cuesheet to split audio file"))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-d",self.dir2,
                 "--cue",self.bad_cue_path,self.flac.filename]),1)

        self.__check_error__(_(u"Cuesheet too long for track being split"))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-j",str(1),"-t","flac","--format=%(foo)s","-d",
                 self.dir2,"--cue",self.cue_path,"-x",self.xmcd_path,
                 self.flac.filename]),1)

        self.__check_error__(_(u"Unknown field \"%s\" in file format") % \
                            ("foo"))
        self.__check_info__(_(u"Supported fields are:"))
        for field in sorted(audiotools.MetaData.__FIELDS__ + \
                                ("album_track_number","suffix")):
            if (field == 'track_number'):
                self.__check_info__(u"%(track_number)2.2d")
            else:
                self.__check_info__(u"%%(%s)s" % (field))

        self.assertEqual(self.__run_app__(
                ["tracksplit","-j",str(1),"-t","wav","-d",self.dir2,
                 "--format=%s" % (self.format_string),
                 "--cue",self.cue_path,self.flac.filename]),0)

        for i in range(3):
            self.__check_info__(_(u"%(source)s -> %(destination)s") % \
                                    {"source":self.filename(self.flac.filename),
                                     "destination":self.filename(
                        os.path.join(self.dir2,
                                     audiotools.WaveAudio.track_name(i + 1,
                                                                     None,
                                                                     format=self.format_string)))})

        #FIXME? - check for broken cue sheet output?

    @TEST_EXECUTABLE
    @TEST_CUESHEET
    def test_tracksplit2(self):
        format_string = "%(track_name)s - %(album_track_number)s.%(suffix)s"

        xmcd = audiotools.XMCD.read_data(open(self.xmcd_path).read().decode('utf-8'))
        xmcd_metadata = xmcd.metadata()

        self.assertEqual(self.__run_app__(
                ["tracksplit","-j",str(1),"-t","mp3","-d",self.dir2,
                 "-x",self.xmcd_path,
                 "--format=%s" % (format_string),
                 "--cue",self.cue_path,self.flac.filename]),0)

        for i in xrange(3):
            self.__check_info__(_(u"%(source)s -> %(destination)s") % \
                                    {"source":self.filename(self.flac.filename),
                                     "destination":self.filename(os.path.join(
                            self.dir2,audiotools.MP3Audio.track_name(
                                i+1,xmcd_metadata[i+1],format=format_string)))})

        metadata = self.flac.get_metadata()
        metadata.album_number = 1
        self.flac.set_metadata(metadata)

        self.assertEqual(self.__run_app__(
                ["tracksplit","-t","flac","-d",self.dir2,
                 "-j",str(1),
                 "-x",self.xmcd_path,
                 "--format=%s" % (format_string),
                 "--cue",self.cue_path,self.flac.filename]),0)

        for i in xrange(3):
            self.__check_info__(_(u"%(source)s -> %(destination)s") % \
                                    {"source":self.filename(self.flac.filename),
                                     "destination":self.filename(os.path.join(
                            self.dir2,audiotools.FlacAudio.track_name(
                                i+1,
                                xmcd_metadata[i+1],
                                album_number=1,
                                format=format_string)))})
        self.__check_info__(_(u"Adding ReplayGain metadata.  This may take some time."))

class TestTrack2XMCDFreeDB(TestTextOutput):
    @TEST_EXECUTABLE
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.xmcd_filename = os.path.join(
            self.dir,
            (u"Unicode %s.xmcd" % \
                 (u"".join(map(unichr,range(0x30a1,0x30b2 + 1))))).encode(
                        audiotools.FS_ENCODING,"replace"))
        self.existing_filename = os.path.join(
            self.dir,
            (u"Unicode2 %s.xmcd" % \
                 (u"".join(map(unichr,range(0x30a1,0x30b2 + 1))))).encode(
                        audiotools.FS_ENCODING,"replace"))

        f = open(self.existing_filename,"w")
        f.write("Hello World")
        f.close()

        self.flac_files = [audiotools.FlacAudio.from_pcm(
                os.path.join(self.dir,"file%2.2d.flac" % (i + 1)),
                EXACT_BLANK_PCM_Reader(sample_length),
                compression="1")
                           for (i,sample_length) in
                           enumerate([12280380, 12657288, 4152456, 1929228,
                                      9938376,15153936, 13525176, 10900344,
                                      940212, 10492860,7321776, 11084976,
                                      2738316, 4688712, 2727144,13142388,
                                      9533244, 13220004, 15823080, 5986428,
                                      10870944, 2687748])]

    @TEST_EXECUTABLE
    def tearDown(self):
        for f in os.listdir(self.dir):
            os.unlink(os.path.join(self.dir,f))
        os.rmdir(self.dir)

    @TEST_EXECUTABLE
    def test_track2xmcd(self):
        self.assertEqual(self.__run_app__(["track2xmcd"]),1)
        self.__check_error__(_(u"You must specify at least 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["track2xmcd","-x",self.existing_filename] + \
                [flac.filename for flac in self.flac_files]),
                         1)
        self.__check_error__(_(u"Refusing to overwrite \"%s\"") % \
                                 (self.filename(self.existing_filename)))

        self.assertEqual(self.__run_app__(
                ["track2xmcd","--no-musicbrainz",
                 "--freedb-server=us.freedb.org",
                 "-D","-x",self.xmcd_filename] + \
                [flac.filename for flac in self.flac_files]),
                         0)

        self.__check_info__(_(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
                                {"disc_id":u"4510fd16",
                                 "server":u"us.freedb.org"})

        #NOTE - This particular batch of tracks has 3 matches
        #on FreeDB's servers right now.
        #Since we're working with live data,
        #that number may change further down the line
        #so one mustn't panic if this test fails someday in the future.
        self.__check_info__(_(u"%s matches found") % (3,))

        self.__check_info__(_(u"%s written") % \
                                (self.filename(self.xmcd_filename)))


class TestTrack2XMLMusicBrainz(TestTextOutput):
    @TEST_EXECUTABLE
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.xml_filename = os.path.join(
            self.dir,
            (u"Unicode %s.xml" % \
                 (u"".join(map(unichr,range(0x30a1,0x30b2 + 1))))).encode(
                        audiotools.FS_ENCODING,"replace"))
        self.existing_filename = os.path.join(
            self.dir,
            (u"Unicode2 %s.xml" % \
                 (u"".join(map(unichr,range(0x30a1,0x30b2 + 1))))).encode(
                        audiotools.FS_ENCODING,"replace"))

        f = open(self.existing_filename,"w")
        f.write("Hello World")
        f.close()

        self.flac_files = [audiotools.FlacAudio.from_pcm(
                os.path.join(self.dir,"file%2.2d.flac" % (i + 1)),
                EXACT_BLANK_PCM_Reader(sample_length),
                compression="1")
                           for (i,sample_length) in
                           enumerate([12280380, 12657288, 4152456, 1929228,
                                      9938376,15153936, 13525176, 10900344,
                                      940212, 10492860,7321776, 11084976,
                                      2738316, 4688712, 2727144,13142388,
                                      9533244, 13220004, 15823080, 5986428,
                                      10870944, 2687748])]

    @TEST_EXECUTABLE
    def tearDown(self):
        for f in os.listdir(self.dir):
            os.unlink(os.path.join(self.dir,f))
        os.rmdir(self.dir)

    @TEST_EXECUTABLE
    def test_track2xmcd(self):
        self.assertEqual(self.__run_app__(["track2xmcd"]),1)
        self.__check_error__(_(u"You must specify at least 1 supported audio file"))

        self.assertEqual(self.__run_app__(
                ["track2xmcd","-x",self.existing_filename] + \
                [flac.filename for flac in self.flac_files]),
                         1)
        self.__check_error__(_(u"Refusing to overwrite \"%s\"") % \
                                 (self.filename(self.existing_filename)))

        #MusicBrainz will ban IPs who submit more than 1 search per second
        time.sleep(1)

        self.assertEqual(self.__run_app__(
                ["track2xmcd","--no-freedb",
                 "--musicbrainz-server=musicbrainz.org",
                 "-D","-x",self.xml_filename] + \
                [flac.filename for flac in self.flac_files]),
                         0)

        self.__check_info__(_(u"Sending Disc ID \"%(disc_id)s\" to server \"%(server)s\"") % \
                                {"disc_id":u"I6V9tQ_QttDWJ0YffInP9pu57RY-",
                                 "server":u"musicbrainz.org"})

        #NOTE - This particular batch of tracks has 1 match
        #on MusicBrainz's servers right now.
        #Since we're working with live data,
        #that number may change further down the line
        #so one mustn't panic if this test fails someday in the future.
        self.__check_info__(_(u"%s match found") % (1,))

        self.__check_info__(_(u"%s written") % \
                                (self.filename(self.xml_filename)))

class TestTrackTag(unittest.TestCase):
    def __run_tag__(self,arguments):
        return subprocess.call(["tracktag",
                                self.track.filename] + \
                               list(arguments) + \
                               ["-V","quiet"])

    @TEST_METADATA
    @TEST_EXECUTABLE
    def setUp(self):
        self.xmcd1_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd2_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.track_file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.xmcd1_file.write('# xmcd\n#\nDTITLE=XMCD Artist / XMCD Album\nDYEAR=2009\nTTITLE0=XMCD Track 1\nTTITLE1=XMCD Track 2\nTTITLE2=XMCD Track 3\nEXTDD=\nEXTT0=\nEXTT1=\nEXTT2=\nPLAYORDER=\n')
        self.xmcd1_file.flush()

        self.xmcd2_file.write('# xmcd\n#\nDTITLE=XMCD Artist 2 / XMCD Album 2\nDYEAR=2009\nTTITLE0=XMCD Track 4\nTTITLE1=XMCD Track 5\nTTITLE2=XMCD Track 6\nEXTDD=\nEXTT0=\nEXTT1=\nEXTT2=\nPLAYORDER=\n')
        self.xmcd2_file.flush()

        self.track = audiotools.FlacAudio.from_pcm(
            self.track_file.name,
            BLANK_PCM_Reader(5))
        self.track.set_metadata(audiotools.MetaData(track_number=1))

        self.xmcd1 = audiotools.XMCD.read(self.xmcd1_file.name)
        self.xmcd2 = audiotools.XMCD.read(self.xmcd2_file.name)

        self.metadata = audiotools.MetaData(track_name=u"Metadata Track 1",
                                            album_name=u"Metadata Album",
                                            year=u"2008",
                                            track_number=2,
                                            track_total=4)

    def __metadata_fields__(self,metadata):
        return ["--name",
                metadata.track_name.encode('ascii'),
                "--album",
                metadata.album_name.encode('ascii'),
                "--year",
                metadata.year.encode('ascii'),
                "--number",
                str(metadata.track_number),
                "--track-total",
                str(metadata.track_total)]

    @TEST_METADATA
    @TEST_EXECUTABLE
    def tearDown(self):
        self.xmcd1_file.close()
        self.xmcd2_file.close()
        self.track_file.close()

    #these tests handle all the combinations of
    #command-line tagging ("tag"/"notag")
    #XMCD file ("xmcd"/"noxmcd")
    #and the --replace flag ("replace"/"noreplace")

    def test_notag_noxmcd_noreplace(self):
        #does nothing
        pass

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_noxmcd_noreplace(self):
        #test a standard command-line tag
        self.assertEqual(self.__run_tag__(
                self.__metadata_fields__(self.metadata)),0)
        self.assertEqual(self.metadata,self.track.get_metadata())

        #then test a command-line re-tag
        self.metadata.track_name = u"Metadata Track 2"
        self.assertEqual(self.__run_tag__(
                ["--name","Metadata Track 2"]),0)
        self.assertEqual(self.metadata,self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_notag_xmcd_noreplace(self):
        #test an XMCD file
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name]),0)

        self.assertEqual(self.xmcd1.metadata()[1],self.track.get_metadata())

        #then test overwriting it with another XMCD file
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd2_file.name]),0)

        self.assertEqual(self.xmcd2.metadata()[1],self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_xmcd_noreplace1(self):
        #test a command-line tag followed by an XMCD tag
        self.assertEqual(self.__run_tag__(
                ["--name","Tagged Name",
                 "--composer","Composer Name"]),0)

        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name]),0)

        self.assertEqual(audiotools.MetaData(
                track_name=u"XMCD Track 1",
                track_number=1,
                track_total=3,
                album_name=u"XMCD Album",
                artist_name=u"XMCD Artist",
                year=u"2009",
                composer_name=u"Composer Name"),
                         self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_xmcd_noreplace2(self):
        #test an XMCD tag followed by a command-line tag
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name]),0)

        self.assertEqual(self.__run_tag__(
                ["--name","Tagged Name",
                 "--composer","Composer Name"]),0)

        self.assertEqual(audiotools.MetaData(
                track_name=u"Tagged Name",
                track_number=1,
                track_total=3,
                album_name=u"XMCD Album",
                artist_name=u"XMCD Artist",
                year=u"2009",
                composer_name=u"Composer Name"),
                         self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_xmcd_noreplace3(self):
        #test simultaneous command-line and XMCD tag
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name,
                 "--name","Tagged Name",
                 "--composer","Composer Name"]),0)

        self.assertEqual(audiotools.MetaData(
                track_name=u"Tagged Name",
                track_number=1,
                track_total=3,
                album_name=u"XMCD Album",
                artist_name=u"XMCD Artist",
                year=u"2009",
                composer_name=u"Composer Name"),
                         self.track.get_metadata())


    def test_notag_noxmcd_replace(self):
        #does nothing
        pass

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_noxmcd_replace(self):
        #test a standard command-line tag
        self.assertEqual(self.__run_tag__(
                self.__metadata_fields__(self.metadata) + ["--replace"]),0)
        self.assertEqual(self.metadata,self.track.get_metadata())

        #then test a command-line re-tag
        self.assertEqual(self.__run_tag__(
                ["--name","New Track Name","--number",str(2),"--replace"]),0)
        self.assertEqual(audiotools.MetaData(track_name=u"New Track Name",
                                             track_number=2),
                         self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_notag_xmcd_replace(self):
        #test an XMCD file
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name,"--replace"]),0)

        self.assertEqual(self.xmcd1.metadata()[1],self.track.get_metadata())

        #then test overwriting it with another XMCD file
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd2_file.name,"--replace"]),0)

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_xmcd_replace1(self):
        #test a command-line tag followed by an XMCD tag
        self.assertEqual(self.__run_tag__(
                ["--name","Tagged Name",
                 "--composer","Composer Name",
                 "--number",str(1),"--replace"]),0)

        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name,"--replace"]),0)

        self.assertEqual(audiotools.MetaData(
                track_name=u"XMCD Track 1",
                track_number=1,
                track_total=3,
                album_name=u"XMCD Album",
                artist_name=u"XMCD Artist",
                year=u"2009"),
                         self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_xmcd_replace2(self):
        #test an XMCD tag followed by a command-line tag
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name,"--replace"]),0)

        self.assertEqual(self.__run_tag__(
                ["--name","Tagged Name",
                 "--composer","Composer Name",
                 "--number",str(1),"--replace"]),0)

        self.assertEqual(audiotools.MetaData(
                track_name=u"Tagged Name",
                track_number=1,
                composer_name=u"Composer Name"),
                         self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tag_xmcd_replace3(self):
        #test simultaneous command-line and XMCD tag
        self.assertEqual(self.__run_tag__(
                ["-x",self.xmcd1_file.name,
                 "--name","Tagged Name",
                 "--composer","Composer Name"]),0)

        self.assertEqual(audiotools.MetaData(
                track_name=u"Tagged Name",
                track_number=1,
                track_total=3,
                album_name=u"XMCD Album",
                artist_name=u"XMCD Artist",
                year=u"2009",
                composer_name=u"Composer Name"),
                         self.track.get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_images(self):
        jpeg_file = tempfile.NamedTemporaryFile(suffix=".jpg")
        png_file = tempfile.NamedTemporaryFile(suffix=".png")
        jpeg2_file = tempfile.NamedTemporaryFile(suffix=".jpg")
        try:
            jpeg_file.write(TEST_COVER1);
            jpeg_file.flush()
            png_file.write(TEST_COVER2)
            png_file.flush()
            jpeg2_file.write(TEST_COVER3)
            jpeg2_file.flush()

            self.assertEqual(self.__run_tag__(["--name","Track Name"]),0)

            self.assertEqual(audiotools.MetaData(track_name=u"Track Name",
                                                 track_number=1),
                             self.track.get_metadata())

            self.assertEqual([],self.track.get_metadata().images())

            self.assertEqual(self.__run_tag__(
                    ["--front-cover",jpeg_file.name]),0)

            self.assertEqual(audiotools.MetaData(track_name=u"Track Name",
                                                 track_number=1),
                             self.track.get_metadata())

            self.assertEqual([audiotools.Image.new(TEST_COVER1,u"",0)],
                             self.track.get_metadata().images())

            self.assertEqual(self.__run_tag__(
                    ["--back-cover",png_file.name]),0)

            self.assertEqual([audiotools.Image.new(TEST_COVER1,u"",0),
                              audiotools.Image.new(TEST_COVER2,u"",1)],
                             self.track.get_metadata().images())

            self.assertEqual(self.__run_tag__(
                    ["--replace","--name","New Name","--number",str(1)]),0)

            self.assertEqual(audiotools.MetaData(track_name=u"New Name",
                                                 track_number=1),
                             self.track.get_metadata())

            self.assertEqual([],self.track.get_metadata().images())

            self.assertEqual(self.__run_tag__(
                    ["--front-cover",jpeg_file.name,
                     "--back-cover",png_file.name]),0)

            self.assertEqual([audiotools.Image.new(TEST_COVER1,u"",0),
                              audiotools.Image.new(TEST_COVER2,u"",1)],
                             self.track.get_metadata().images())

            self.assertEqual(self.__run_tag__(
                    ["--front-cover",jpeg2_file.name,
                     "--remove-images"]),0)

            self.assertEqual(audiotools.MetaData(track_name=u"New Name",
                                                 track_number=1),
                             self.track.get_metadata())

            self.assertEqual([audiotools.Image.new(TEST_COVER3,u"",0)],
                             self.track.get_metadata().images())

            self.assertEqual(self.__run_tag__(
                    ["--remove-images"]),0)

            self.assertEqual(audiotools.MetaData(track_name=u"New Name",
                                                 track_number=1),
                             self.track.get_metadata())

            self.assertEqual([],self.track.get_metadata().images())
        finally:
            jpeg2_file.close()
            jpeg_file.close()
            png_file.close()

class TestTrackTagXML(TestTrackTag):
    @TEST_METADATA
    @TEST_EXECUTABLE
    def setUp(self):
        self.xmcd1_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd2_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.track_file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.xmcd1_file.write('<?xml version="1.0" encoding="utf-8"?>\n<metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>XMCD Album</title><text-representation language="ENG" script="Latn"/><artist><name>XMCD Artist</name></artist><release-event-list><event date="2009-01-02" format="CD"/></release-event-list><track-list><track><title>XMCD Track 1</title><duration>218000</duration></track><track><title>XMCD Track 2</title><duration>204000</duration></track><track><title>XMCD Track 3</title><duration>218000</duration></track></track-list></release></release-list></metadata>\n')

        self.xmcd1_file.flush()

        self.xmcd2_file.write('<?xml version="1.0" encoding="utf-8"?>\n<metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>XMCD Album 2</title><text-representation language="ENG" script="Latn"/><artist><name>XMCD Artist 2</name></artist><release-event-list><event date="2009-01-02" format="CD"/></release-event-list><track-list><track><title>XMCD Track 4</title><duration>218000</duration></track><track><title>XMCD Track 5</title><duration>204000</duration></track><track><title>XMCD Track 6</title><duration>218000</duration></track></track-list></release></release-list></metadata>\n')

        self.xmcd2_file.flush()

        self.track = audiotools.FlacAudio.from_pcm(
            self.track_file.name,
            BLANK_PCM_Reader(5))
        self.track.set_metadata(audiotools.MetaData(track_number=1))

        self.xmcd1 = audiotools.MusicBrainzReleaseXML.read(self.xmcd1_file.name)
        self.xmcd2 = audiotools.MusicBrainzReleaseXML.read(self.xmcd2_file.name)

        self.metadata = audiotools.MetaData(track_name=u"Metadata Track 1",
                                            album_name=u"Metadata Album",
                                            year=u"2008",
                                            track_number=2,
                                            track_total=4)


class TestTrack2Track(unittest.TestCase):
    def __run_convert__(self,arguments):
        return subprocess.call(["track2track",
                                self.track.filename] + \
                               list(arguments) + \
                               ["-o",self.output_file.name,"-V","quiet"])

    def __run_convert2__(self,arguments):
        return subprocess.call(["track2track",
                                self.track.filename] + \
                               list(arguments) + \
                               ["-d",self.output_dir,"-t","flac","-V","quiet"])

    def output_dir_track(self):
        return audiotools.open(os.path.join(self.output_dir,
                                            os.listdir(self.output_dir)[0]))

    @TEST_METADATA
    @TEST_EXECUTABLE
    def setUp(self):
        self.track_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.output_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.output_dir = tempfile.mkdtemp()

        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('# xmcd\n#\nDTITLE=XMCD Artist / XMCD Album\nDYEAR=2009\nTTITLE0=XMCD Track 1\nTTITLE1=XMCD Track 2\nTTITLE2=XMCD Track 3\nEXTDD=\nEXTT0=\nEXTT1=\nEXTT2=\nPLAYORDER=\n')
        self.xmcd_file.flush()
        self.xmcd = audiotools.XMCD.read(self.xmcd_file.name)

        self.xml_file = tempfile.NamedTemporaryFile(suffix=".xml")
        self.xml_file.write('<?xml version="1.0" encoding="utf-8"?>\n<metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>XML Album</title><text-representation language="ENG" script="Latn"/><artist><name>XML Artist</name></artist><release-event-list><event date="2009-01-02" format="CD"/></release-event-list><track-list><track><title>XML Track 1</title><duration>218000</duration></track><track><title>XML Track 2</title><duration>204000</duration></track><track><title>XML Track 3</title><duration>218000</duration></track></track-list></release></release-list></metadata>\n')
        self.xml_file.flush()
        self.xml = audiotools.MusicBrainzReleaseXML.read(self.xml_file.name)

        self.track = audiotools.FlacAudio.from_pcm(
            self.track_file.name,
            BLANK_PCM_Reader(5))
        self.track.set_metadata(audiotools.MetaData(track_number=1))

        self.metadata = audiotools.MetaData(track_name=u"Test Name",
                                            artist_name=u"Some Artist",
                                            composer_name=u"Composer",
                                            track_number=1)

    @TEST_METADATA
    @TEST_EXECUTABLE
    def tearDown(self):
        self.track_file.close()
        self.output_file.close()
        self.xmcd_file.close()
        self.xml_file.close()
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir,f))
        os.rmdir(self.output_dir)

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_nonxmcd1(self):
        self.track.set_metadata(self.metadata)
        self.assertEqual(self.__run_convert__([]),0)
        self.assertEqual(self.metadata,
                         audiotools.open(self.output_file.name).get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_nonxmcd2(self):
        self.track.set_metadata(self.metadata)
        self.assertEqual(self.__run_convert2__([]),0)
        self.assertEqual(self.metadata,
                         self.output_dir_track().get_metadata())

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xmcd1(self):
        self.track.set_metadata(self.metadata)
        self.assertEqual(self.__run_convert__(["-x",self.xmcd_file.name]),0)

        self.assertEqual(audiotools.open(self.output_file.name).get_metadata(),
                         audiotools.MetaData(track_name=u"XMCD Track 1",
                                             album_name=u"XMCD Album",
                                             artist_name=u"XMCD Artist",
                                             track_number=1,
                                             track_total=3,
                                             year=u"2009",
                                             composer_name=u"Composer"))

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xmcd2(self):
        self.track.set_metadata(self.metadata)
        self.assertEqual(self.__run_convert2__(["-x",self.xmcd_file.name]),0)

        self.assertEqual(self.output_dir_track().get_metadata(),
                         audiotools.MetaData(track_name=u"XMCD Track 1",
                                             album_name=u"XMCD Album",
                                             artist_name=u"XMCD Artist",
                                             track_number=1,
                                             track_total=3,
                                             year=u"2009",
                                             composer_name=u"Composer"))

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xml1(self):
        self.track.set_metadata(self.metadata)
        self.assertEqual(self.__run_convert__(["-x",self.xml_file.name]),0)

        self.assertEqual(audiotools.open(self.output_file.name).get_metadata(),
                         audiotools.MetaData(track_name=u"XML Track 1",
                                             album_name=u"XML Album",
                                             artist_name=u"XML Artist",
                                             track_number=1,
                                             track_total=3,
                                             year=u"2009",
                                             composer_name=u"Composer"))

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xml2(self):
        self.track.set_metadata(self.metadata)
        self.assertEqual(self.__run_convert2__(["-x",self.xml_file.name]),0)

        self.assertEqual(self.output_dir_track().get_metadata(),
                         audiotools.MetaData(track_name=u"XML Track 1",
                                             album_name=u"XML Album",
                                             artist_name=u"XML Artist",
                                             track_number=1,
                                             track_total=3,
                                             year=u"2009",
                                             composer_name=u"Composer"))

class TestTrackSplit(unittest.TestCase):
    def dir_files(self):
        return audiotools.open_files([os.path.join(self.output_dir,f)
                                      for f in os.listdir(self.output_dir)])

    def dir_metadata(self):
        return [f.get_metadata() for f in self.dir_files()]

    @TEST_METADATA
    @TEST_EXECUTABLE
    def setUp(self):
        self.flac_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.track = audiotools.FlacAudio.from_pcm(
            self.flac_file.name,
            EXACT_BLANK_PCM_Reader(24725400))

        self.cue_file = tempfile.NamedTemporaryFile(suffix=".cue")
        self.cue_file.write('FILE "data.wav" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n  TRACK 02 AUDIO\n    INDEX 00 03:16:55\n    INDEX 01 03:18:18\n  TRACK 03 AUDIO\n    INDEX 00 05:55:12\n    INDEX 01 06:01:45\n')
        self.cue_file.flush()

        self.output_dir = tempfile.mkdtemp()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def tearDown(self):
        self.flac_file.close()
        self.cue_file.close()
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir,f))
        os.rmdir(self.output_dir)

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_nonxmcd(self):
        self.track.set_metadata(audiotools.MetaData(
                album_name=u"Some Album",
                performer_name=u"Performer"))

        self.assertEqual(subprocess.call(["tracksplit",
                                          self.track.filename,
                                          "-d",
                                          self.output_dir,
                                          "-t","flac",
                                          "-q","0",
                                          "--cue",self.cue_file.name,
                                          "-V","quiet"]),0)
        metadata = self.dir_metadata()

        self.assertEqual(metadata[0],
                         audiotools.MetaData(
                track_number=1,
                track_total=3,
                album_name=u"Some Album",
                performer_name=u"Performer"))

        self.assertEqual(metadata[1],
                         audiotools.MetaData(
                track_number=2,
                track_total=3,
                album_name=u"Some Album",
                performer_name=u"Performer"))

        self.assertEqual(metadata[2],
                         audiotools.MetaData(
                track_number=3,
                track_total=3,
                album_name=u"Some Album",
                performer_name=u"Performer"))

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xmcd(self):
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        try:
            xmcd_file.write('# xmcd\n#\nDTITLE=XMCD Artist / XMCD Album\nDYEAR=2009\nTTITLE0=XMCD Track 1\nTTITLE1=XMCD Track 2\nTTITLE2=XMCD Track 3\nEXTDD=\nEXTT0=\nEXTT1=\nEXTT2=\nPLAYORDER=\n')
            xmcd_file.flush()

            self.track.set_metadata(audiotools.MetaData(
                album_name=u"Some Album",
                performer_name=u"Performer"))

            self.assertEqual(subprocess.call(["tracksplit",
                                              self.track.filename,
                                              "-d",
                                              self.output_dir,
                                              "-x",xmcd_file.name,
                                              "-t","flac",
                                              "-q","0",
                                              "--cue",self.cue_file.name,
                                              "-V","quiet"]),0)

            metadata = self.dir_metadata()

            self.assertEqual(metadata[0],
                             audiotools.MetaData(
                    track_number=1,
                    track_total=3,
                    track_name=u"XMCD Track 1",
                    album_name=u"XMCD Album",
                    artist_name=u"XMCD Artist",
                    year=u"2009",
                    performer_name=u"Performer"))

            self.assertEqual(metadata[1],
                             audiotools.MetaData(
                    track_number=2,
                    track_total=3,
                    track_name=u"XMCD Track 2",
                    album_name=u"XMCD Album",
                    artist_name=u"XMCD Artist",
                    year=u"2009",
                    performer_name=u"Performer"))

            self.assertEqual(metadata[2],
                             audiotools.MetaData(
                    track_number=3,
                    track_total=3,
                    track_name=u"XMCD Track 3",
                    album_name=u"XMCD Album",
                    artist_name=u"XMCD Artist",
                    year=u"2009",
                    performer_name=u"Performer"))

        finally:
            xmcd_file.close()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xml(self):
        xml_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        try:
            xml_file.write('<?xml version="1.0" encoding="utf-8"?>\n<metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>XML Album</title><text-representation language="ENG" script="Latn"/><artist><name>XML Artist</name></artist><release-event-list><event date="2009-01-02" format="CD"/></release-event-list><track-list><track><title>XML Track 1</title><duration>218000</duration></track><track><title>XML Track 2</title><duration>204000</duration></track><track><title>XML Track 3</title><duration>218000</duration></track></track-list></release></release-list></metadata>\n')
            xml_file.flush()

            self.track.set_metadata(audiotools.MetaData(
                album_name=u"Some Album",
                performer_name=u"Performer"))

            self.assertEqual(subprocess.call(["tracksplit",
                                              self.track.filename,
                                              "-d",
                                              self.output_dir,
                                              "-x",xml_file.name,
                                              "-t","flac",
                                              "-q","0",
                                              "--cue",self.cue_file.name,
                                              "-V","quiet"]),0)

            metadata = self.dir_metadata()

            self.assertEqual(metadata[0],
                             audiotools.MetaData(
                    track_number=1,
                    track_total=3,
                    track_name=u"XML Track 1",
                    album_name=u"XML Album",
                    artist_name=u"XML Artist",
                    year=u"2009",
                    performer_name=u"Performer"))

            self.assertEqual(metadata[1],
                             audiotools.MetaData(
                    track_number=2,
                    track_total=3,
                    track_name=u"XML Track 2",
                    album_name=u"XML Album",
                    artist_name=u"XML Artist",
                    year=u"2009",
                    performer_name=u"Performer"))

            self.assertEqual(metadata[2],
                             audiotools.MetaData(
                    track_number=3,
                    track_total=3,
                    track_name=u"XML Track 3",
                    album_name=u"XML Album",
                    artist_name=u"XML Artist",
                    year=u"2009",
                    performer_name=u"Performer"))
        finally:
            xml_file.close()

class TestTrackrename(unittest.TestCase):
    @TEST_METADATA
    @TEST_EXECUTABLE
    def setUp(self):
        self.output_dir = tempfile.mkdtemp()
        self.track = audiotools.FlacAudio.from_pcm(
            os.path.join(self.output_dir,"test.flac"),
            BLANK_PCM_Reader(5))

        self.format = "%(track_number)2.2d - %(track_name)s - %(album_name)s - %(composer_name)s.%(suffix)s"

    @TEST_METADATA
    @TEST_EXECUTABLE
    def tearDown(self):
        for f in os.listdir(self.output_dir):
            os.unlink(os.path.join(self.output_dir,f))
        os.rmdir(self.output_dir)

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_noxmcd(self):
        self.track.set_metadata(audiotools.MetaData(
                track_number=1,
                track_name=u"Track Name",
                album_name=u"Album Name",
                composer_name=u"Composer Name"))
        self.assertEqual(subprocess.call(["trackrename",
                                          "--format",self.format,
                                          self.track.filename,
                                          "-V","quiet"]),0)
        self.assertEqual(os.listdir(self.output_dir)[0],
                         "01 - Track Name - Album Name - Composer Name.flac")

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_noxmcd2(self):
        self.track.set_metadata(audiotools.MetaData(
                track_number=1,
                track_name=u"Track Name",
                album_name=u"Album Name",
                composer_name=u"Composer Name"))
        track2 = audiotools.FlacAudio.from_pcm(
            os.path.join(self.output_dir,"test2.flac"),
            BLANK_PCM_Reader(5))
        track2.set_metadata(audiotools.MetaData(
                track_number=1,
                track_name=u"Track Name 2",
                album_name=u"Album Name 2",
                composer_name=u"Composer Name 2"))
        self.assertEqual(subprocess.call(["trackrename",
                                          "--format",self.format,
                                          self.track.filename,
                                          track2.filename,
                                          "-V","quiet"]),0)
        self.assertEqual(set(os.listdir(self.output_dir)),
                         set([
                    "01 - Track Name - Album Name - Composer Name.flac",
                    "01 - Track Name 2 - Album Name 2 - Composer Name 2.flac"]))

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xmcd(self):
        xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        try:
            xmcd_file.write('# xmcd\n#\nDTITLE=XMCD Artist / XMCD Album\nDYEAR=2009\nTTITLE0=XMCD Track 1\nTTITLE1=XMCD Track 2\nTTITLE2=XMCD Track 3\nEXTDD=\nEXTT0=\nEXTT1=\nEXTT2=\nPLAYORDER=\n')
            xmcd_file.flush()

            self.track.set_metadata(audiotools.MetaData(
                    track_number=1,
                    track_name=u"Track Name",
                    album_name=u"Album Name",
                    composer_name=u"Composer Name"))

            self.assertEqual(subprocess.call(["trackrename",
                                              "--format",self.format,
                                              self.track.filename,
                                              "-x",xmcd_file.name,
                                              "-V","quiet"]),0)
            self.assertEqual(os.listdir(self.output_dir)[0],
                             "01 - XMCD Track 1 - XMCD Album - Composer Name.flac")
        finally:
            xmcd_file.close()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_xml(self):
        xml_file = tempfile.NamedTemporaryFile(suffix=".xml")
        try:
            xml_file.write('<?xml version="1.0" encoding="utf-8"?>\n<metadata xmlns="http://musicbrainz.org/ns/mmd-1.0#" xmlns:ext="http://musicbrainz.org/ns/ext-1.0#"><release-list><release><title>XML Album</title><text-representation language="ENG" script="Latn"/><artist><name>XML Artist</name></artist><release-event-list><event date="2009-01-02" format="CD"/></release-event-list><track-list><track><title>XML Track 1</title><duration>218000</duration></track><track><title>XML Track 2</title><duration>204000</duration></track><track><title>XML Track 3</title><duration>218000</duration></track></track-list></release></release-list></metadata>\n')
            xml_file.flush()

            self.track.set_metadata(audiotools.MetaData(
                    track_number=1,
                    track_name=u"Track Name",
                    album_name=u"Album Name",
                    composer_name=u"Composer Name"))

            self.assertEqual(subprocess.call(["trackrename",
                                              "--format",self.format,
                                              self.track.filename,
                                              "-x",xml_file.name,
                                              "-V","quiet"]),0)

            self.assertEqual(os.listdir(self.output_dir)[0],
                             "01 - XML Track 1 - XML Album - Composer Name.flac")
        finally:
            xml_file.close()

class TestImageJPEG(unittest.TestCase):
    @TEST_IMAGE
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

    @TEST_IMAGE
    def tearDown(self):
        pass

    @TEST_IMAGE
    def test_checksum(self):
        self.assertEqual(md5(self.image).hexdigest(),self.md5sum)

    @TEST_IMAGE
    def test_image(self):
        img = audiotools.Image.new(self.image,u"Description",1)
        self.assertEqual(img.data,self.image)
        self.assertEqual(img.mime_type,self.mime_type)
        self.assertEqual(img.width,self.width)
        self.assertEqual(img.height,self.height)
        self.assertEqual(img.color_depth,self.bpp)
        self.assertEqual(img.color_count,self.colors)
        self.assertEqual(img.description,u"Description")
        self.assertEqual(img.type,1)

class TestImagePNG(TestImageJPEG):
    @TEST_IMAGE
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

class TestImageCover1(TestImageJPEG):
    @TEST_IMAGE
    def setUp(self):
        self.image = TEST_COVER1
        self.md5sum = "dbb6a01eca6336381754346de71e052e"
        self.width = 500
        self.height = 500
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/jpeg"

class TestImageCover2(TestImageJPEG):
    @TEST_IMAGE
    def setUp(self):
        self.image = TEST_COVER2
        self.md5sum = "2d348cf729c840893d672dd69476955c"
        self.width = 500
        self.height = 500
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/png"

class TestImageCover3(TestImageJPEG):
    @TEST_IMAGE
    def setUp(self):
        self.image = TEST_COVER3
        self.md5sum = "534b107e88d3830eac7ce814fc5d0279"
        self.width = 100
        self.height = 100
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/jpeg"


class TestImageGIF(TestImageJPEG):
    @TEST_IMAGE
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

class TestImageBMP(TestImageJPEG):
    @TEST_IMAGE
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

class TestImageTIFF(TestImageJPEG):
    @TEST_IMAGE
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

class TestHugeBMP(TestImageJPEG):
    @TEST_IMAGE
    def setUp(self):
        self.image = HUGE_BMP.decode('bz2')
        self.md5sum = "558d875195829de829059fd4952fed46"
        self.width = 2366
        self.height = 2366
        self.bpp = 24
        self.colors = 0
        self.mime_type = "image/x-ms-bmp"

#tests to ensure that unsupported chunks of MetaData
#aren't blown away improperly by MetaData modifying tools
class TestForeignMetaData_WavPackAPE(unittest.TestCase):
    AUDIO_CLASS = audiotools.WavPackAudio
    METADATA_CLASS = audiotools.WavePackAPEv2
    BASE_CLASS_METADATA = audiotools.WavePackAPEv2(
        [audiotools.ApeTagItem(0,False,"Title",'Track Name'),
         audiotools.ApeTagItem(0,False,"Album",'Album Name'),
         audiotools.ApeTagItem(0,False,"Track","1/3"),
         audiotools.ApeTagItem(0,False,"Media","2/4"),
         audiotools.ApeTagItem(0,False,"Foo","Bar")])

    def __verify_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("Foo" in track.get_metadata().keys())
        self.assertEqual(unicode(track.get_metadata()["Foo"]),u"Bar")

    def __verify_no_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("Foo" not in track.get_metadata().keys())

    BASE_METADATA = audiotools.MetaData(
        track_name=u"Track Name",
        album_name=u"Album Name",
        track_number=1,
        track_total=3,
        album_number=2,
        album_total=4)

    @TEST_METADATA
    @TEST_EXECUTABLE
    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(
            suffix="." + self.AUDIO_CLASS.SUFFIX)
        self.track = self.AUDIO_CLASS.from_pcm(
            self.tempfile.name,
            BLANK_PCM_Reader(5))
        self.track.set_metadata(self.BASE_CLASS_METADATA)

        self.xmcd_file = tempfile.NamedTemporaryFile(suffix=".xmcd")
        self.xmcd_file.write('# xmcd\n#\nDTITLE=XMCD Artist / XMCD Album\nDYEAR=2009\nTTITLE0=XMCD Track 1\nTTITLE1=XMCD Track 2\nTTITLE2=XMCD Track 3\nEXTDD=\nEXTT0=\nEXTT1=\nEXTT2=\nPLAYORDER=\n')
        self.xmcd_file.flush()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def tearDown(self):
        self.tempfile.close()
        self.xmcd_file.close()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_track2track_noxmcd(self):
        tempfile2 = tempfile.NamedTemporaryFile(
            suffix="." + self.AUDIO_CLASS.SUFFIX)
        try:
            subprocess.call(["track2track","-t",self.AUDIO_CLASS.NAME,
                             "-o",tempfile2.name,self.track.filename])
            track2 = audiotools.open(tempfile2.name)
            self.assertEqual(self.track.get_metadata(),
                             track2.get_metadata())
            self.__verify_foreign_field__(track2)
        finally:
            tempfile2.close()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_track2track_xmcd(self):
        tempfile2 = tempfile.NamedTemporaryFile(
            suffix="." + self.AUDIO_CLASS.SUFFIX)
        try:
            subprocess.call(["track2track","-t",self.AUDIO_CLASS.NAME,
                             "-x",self.xmcd_file.name,
                             "-o",tempfile2.name,self.track.filename])
            track2 = audiotools.open(tempfile2.name)
            self.assertEqual(track2.get_metadata().track_name,
                             u"XMCD Track 1")
            self.__verify_foreign_field__(track2)
        finally:
            tempfile2.close()

    #FIXME
    #should tracksplit port foreign metadata to sub-tracks?
    #such metadata may not be album-specific

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tracktag_noxmcd_noreplace(self):
        self.assertEqual(self.BASE_METADATA,
                         self.track.get_metadata())
        self.__verify_foreign_field__()
        subprocess.call(["tracktag","--name=New Name",self.track.filename])
        self.assertEqual(self.track.get_metadata().track_name,u"New Name")
        self.assertEqual(self.track.get_metadata().track_number,1)
        self.assertEqual(self.track.get_metadata().track_total,3)
        self.assertEqual(self.track.get_metadata().album_number,2)
        self.assertEqual(self.track.get_metadata().album_total,4)
        self.__verify_foreign_field__()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tracktag_xmcd_noreplace(self):
        self.assertEqual(self.BASE_METADATA,
                         self.track.get_metadata())
        self.__verify_foreign_field__()
        subprocess.call(["tracktag","-x",self.xmcd_file.name,
                         self.track.filename])
        self.assertEqual(self.track.get_metadata().track_name,u"XMCD Track 1")
        self.assertEqual(self.track.get_metadata().track_number,1)
        self.assertEqual(self.track.get_metadata().track_total,3)
        self.assertEqual(self.track.get_metadata().album_number,2)
        self.assertEqual(self.track.get_metadata().album_total,4)
        self.__verify_foreign_field__()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tracktag_noxmcd_replace(self):
        self.assertEqual(self.BASE_METADATA,
                         self.track.get_metadata())
        self.__verify_foreign_field__()
        subprocess.call(["tracktag","--replace",
                         "--name=New Name",self.track.filename])
        self.assertEqual(self.track.get_metadata().track_name,u"New Name")
        self.__verify_no_foreign_field__()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tracktag_xmcd_replace(self):
        self.assertEqual(self.BASE_METADATA,
                         self.track.get_metadata())
        self.__verify_foreign_field__()
        subprocess.call(["tracktag","--replace","-x",self.xmcd_file.name,
                         self.track.filename])
        self.assertEqual(self.track.get_metadata().track_name,u"XMCD Track 1")
        self.__verify_no_foreign_field__()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tracktag_images_noreplace(self):
        temp_img = tempfile.NamedTemporaryFile(suffix=".jpg")
        try:
            temp_img.write(TEST_COVER1)
            temp_img.flush()

            self.__verify_foreign_field__()
            subprocess.call(["tracktag","--front-cover",temp_img.name,
                             self.track.filename])
            self.assertEqual(self.track.get_metadata().track_number,1)
            self.assertEqual(self.track.get_metadata().track_total,3)
            self.assertEqual(self.track.get_metadata().album_number,2)
            self.assertEqual(self.track.get_metadata().album_total,4)
            self.__verify_foreign_field__()
        finally:
            temp_img.close()

    @TEST_METADATA
    @TEST_EXECUTABLE
    def test_tracktag_images_replace(self):
        temp_img = tempfile.NamedTemporaryFile(suffix=".jpg")
        try:
            temp_img.write(TEST_COVER1)
            temp_img.flush()

            self.__verify_foreign_field__()
            subprocess.call(["tracktag","--remove-images",
                             "--front-cover",temp_img.name,
                             self.track.filename])
            self.__verify_foreign_field__()
        finally:
            temp_img.close()

# class TestForeignMetaData_MusepackAPE(TestForeignMetaData_WavPackAPE):
#     AUDIO_CLASS = audiotools.MusepackAudio
#     METADATA_CLASS = audiotools.ApeTag
#     BASE_CLASS_METADATA = audiotools.ApeTag(
#         [audiotools.ApeTagItem(0,False,"Title",'Track Name'),
#          audiotools.ApeTagItem(0,False,"Album",'Album Name'),
#          audiotools.ApeTagItem(0,False,"Track","1/3"),
#          audiotools.ApeTagItem(0,False,"Media","2/4"),
#          audiotools.ApeTagItem(0,False,"Foo","Bar")])

#     def __verify_foreign_field__(self, track=None):
#         if (track is None):
#             track = self.track
#         self.assert_("Foo" in track.get_metadata().keys())
#         self.assertEqual(unicode(track.get_metadata()["Foo"]),u"Bar")

#     def __verify_no_foreign_field__(self, track=None):
#         if (track is None):
#             track = self.track
#         self.assert_("Foo" not in track.get_metadata().keys())

class TestForeignMetaData_VorbisComment(TestForeignMetaData_WavPackAPE):
    AUDIO_CLASS = audiotools.VorbisAudio
    METADATA_CLASS = audiotools.VorbisComment
    BASE_CLASS_METADATA = audiotools.VorbisComment(
        {"TITLE":[u'Track Name'],
         "ALBUM":[u'Album Name'],
         "TRACKNUMBER":[u"1"],
         "TRACKTOTAL":[u"3"],
         "DISCNUMBER":[u"2"],
         "DISCTOTAL":[u"4"],
         "FOO":[u"Bar"]})

    def __verify_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("FOO" in track.get_metadata().keys())
        self.assertEqual(track.get_metadata()["FOO"],[u"Bar"])

    def __verify_no_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("FOO" not in track.get_metadata().keys())

class TestForeignMetaData_FLACComment(TestForeignMetaData_WavPackAPE):
    AUDIO_CLASS = audiotools.FlacAudio
    METADATA_CLASS = audiotools.FlacMetaData
    BASE_CLASS_METADATA = audiotools.FlacMetaData([
            audiotools.FlacMetaDataBlock(
                type=4,
                data=audiotools.FlacVorbisComment(
                    {"TITLE":[u'Track Name'],
                     "ALBUM":[u'Album Name'],
                     "TRACKNUMBER":[u"1"],
                     "TRACKTOTAL":[u"3"],
                     "DISCNUMBER":[u"2"],
                     "DISCTOTAL":[u"4"],
                     "FOO":[u"Bar"]}).build())])

    def __verify_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("FOO" in track.get_metadata().vorbis_comment.keys())
        self.assertEqual(track.get_metadata().vorbis_comment["FOO"],[u"Bar"])

    def __verify_no_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("FOO" not in track.get_metadata().vorbis_comment.keys())

class TestForeignMetaData_ID3v22(TestForeignMetaData_WavPackAPE):
    AUDIO_CLASS = audiotools.MP3Audio
    METADATA_CLASS = audiotools.ID3v22Comment
    BASE_CLASS_METADATA = audiotools.ID3v22Comment(
        [audiotools.ID3v22TextFrame("TT2",0,"Track Name"),
         audiotools.ID3v22TextFrame("TAL",0,"Album Name"),
         audiotools.ID3v22TextFrame("TRK",0,"1/3"),
         audiotools.ID3v22TextFrame("TPA",0,"2/4"),
         audiotools.ID3v22TextFrame("TFO",0,"Bar")])

    def __verify_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        metadata = track.get_metadata()
        if (hasattr(metadata,"id3v2")):
            metadata = metadata.id3v2

        self.assert_("TFO" in metadata.keys())
        self.assertEqual(metadata["TFO"][0].string,"Bar")

    def __verify_no_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        metadata = track.get_metadata()
        if (hasattr(metadata,"id3v2")):
            metadata = metadata.id3v2
        self.assert_("TFO" not in metadata.keys())

class TestForeignMetaData_ID3v23(TestForeignMetaData_WavPackAPE):
    AUDIO_CLASS = audiotools.MP3Audio
    METADATA_CLASS = audiotools.ID3v23Comment
    BASE_CLASS_METADATA = audiotools.ID3v23Comment(
        [audiotools.ID3v23TextFrame("TIT2",0,"Track Name"),
         audiotools.ID3v23TextFrame("TALB",0,"Album Name"),
         audiotools.ID3v23TextFrame("TRCK",0,"1/3"),
         audiotools.ID3v23TextFrame("TPOS",0,"2/4"),
         audiotools.ID3v23TextFrame("TFOO",0,"Bar")])

    def __verify_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        metadata = track.get_metadata()
        if (hasattr(metadata,"id3v2")):
            metadata = metadata.id3v2

        self.assert_("TFOO" in metadata.keys())
        self.assertEqual(metadata["TFOO"][0].string,"Bar")

    def __verify_no_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        metadata = track.get_metadata()
        if (hasattr(metadata,"id3v2")):
            metadata = metadata.id3v2
        self.assert_("TFOO" not in metadata.keys())

class TestForeignMetaData_ID3v24(TestForeignMetaData_ID3v23):
    AUDIO_CLASS = audiotools.MP3Audio
    METADATA_CLASS = audiotools.ID3v24Comment
    BASE_CLASS_METADATA = audiotools.ID3v24Comment(
        [audiotools.ID3v24TextFrame("TIT2",0,"Track Name"),
         audiotools.ID3v24TextFrame("TALB",0,"Album Name"),
         audiotools.ID3v24TextFrame("TRCK",0,"1/3"),
         audiotools.ID3v24TextFrame("TPOS",0,"2/4"),
         audiotools.ID3v24TextFrame("TFOO",0,"Bar")])

class TestForeignMetaData_M4A(TestForeignMetaData_WavPackAPE):
    AUDIO_CLASS = audiotools.M4AAudio
    METADATA_CLASS = audiotools.M4AMetaData
    BASE_CLASS_METADATA = audiotools.M4AMetaData([])
    BASE_CLASS_METADATA["\xa9nam"] = audiotools.M4AMetaData.text_atom(
        "\xa9nam",u'Track Name')
    BASE_CLASS_METADATA["\xa9alb"] = audiotools.M4AMetaData.text_atom(
        "\xa9alb",u'Album Name')
    BASE_CLASS_METADATA["trkn"] = audiotools.M4AMetaData.trkn_atom(
        1,3)
    BASE_CLASS_METADATA["disk"] = audiotools.M4AMetaData.disk_atom(
        2,4)
    BASE_CLASS_METADATA["\xa9foo"] = audiotools.M4AMetaData.text_atom(
        "\xa9foo",u'Bar')

    def __verify_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("\xa9foo" in track.get_metadata().keys())
        self.assertEqual(unicode(track.get_metadata()["\xa9foo"][0]),u"Bar")

    def __verify_no_foreign_field__(self, track=None):
        if (track is None):
            track = self.track
        self.assert_("\xa9foo" not in track.get_metadata().keys())

class Test_IEEEExtended(unittest.TestCase):
    @TEST_PCM
    def testroundtrip(self):
        ieee = audiotools.IEEE_Extended("i")
        for i in xrange(0,192000 + 1):
            assert(i == int(ieee.parse(ieee.build(float(i)))))

import test_streams

#these are tests on our built-in FLAC encoder
class TestFlacCodec(unittest.TestCase):
    def __stream_variations__(self):
        if (not hasattr(self,"__stream_variations_cache__")):
            self.__class__.__stream_variations_cache__ = [
                test_streams.Sine8_Mono(200000,48000,441.0,0.50,441.0,0.49),
                test_streams.Sine8_Mono(200000,96000,441.0,0.61,661.5,0.37),
                test_streams.Sine8_Mono(200000,44100,441.0,0.50,882.0,0.49),
                test_streams.Sine8_Mono(200000,44100,441.0,0.50,4410.0,0.49),
                test_streams.Sine8_Mono(200000,44100,8820.0,0.70,4410.0,0.29),

                test_streams.Sine8_Stereo(200000,48000,441.0,0.50,441.0,0.49,1.0),
                test_streams.Sine8_Stereo(200000,48000,441.0,0.61,661.5,0.37,1.0),
                test_streams.Sine8_Stereo(200000,96000,441.0,0.50,882.0,0.49,1.0),
                test_streams.Sine8_Stereo(200000,44100,441.0,0.50,4410.0,0.49,1.0),
                test_streams.Sine8_Stereo(200000,44100,8820.0,0.70,4410.0,0.29,1.0),
                test_streams.Sine8_Stereo(200000,44100,441.0,0.50,441.0,0.49,0.5),
                test_streams.Sine8_Stereo(200000,44100,441.0,0.61,661.5,0.37,2.0),
                test_streams.Sine8_Stereo(200000,44100,441.0,0.50,882.0,0.49,0.7),
                test_streams.Sine8_Stereo(200000,44100,441.0,0.50,4410.0,0.49,1.3),
                test_streams.Sine8_Stereo(200000,44100,8820.0,0.70,4410.0,0.29,0.1),

                test_streams.Sine16_Mono(200000,48000,441.0,0.50,441.0,0.49),
                test_streams.Sine16_Mono(200000,96000,441.0,0.61,661.5,0.37),
                test_streams.Sine16_Mono(200000,44100,441.0,0.50,882.0,0.49),
                test_streams.Sine16_Mono(200000,44100,441.0,0.50,4410.0,0.49),
                test_streams.Sine16_Mono(200000,44100,8820.0,0.70,4410.0,0.29),

                test_streams.Sine16_Stereo(200000,48000,441.0,0.50,441.0,0.49,1.0),
                test_streams.Sine16_Stereo(200000,48000,441.0,0.61,661.5,0.37,1.0),
                test_streams.Sine16_Stereo(200000,96000,441.0,0.50,882.0,0.49,1.0),
                test_streams.Sine16_Stereo(200000,44100,441.0,0.50,4410.0,0.49,1.0),
                test_streams.Sine16_Stereo(200000,44100,8820.0,0.70,4410.0,0.29,1.0),
                test_streams.Sine16_Stereo(200000,44100,441.0,0.50,441.0,0.49,0.5),
                test_streams.Sine16_Stereo(200000,44100,441.0,0.61,661.5,0.37,2.0),
                test_streams.Sine16_Stereo(200000,44100,441.0,0.50,882.0,0.49,0.7),
                test_streams.Sine16_Stereo(200000,44100,441.0,0.50,4410.0,0.49,1.3),
                test_streams.Sine16_Stereo(200000,44100,8820.0,0.70,4410.0,0.29,0.1),

                test_streams.Sine24_Mono(200000,48000,441.0,0.50,441.0,0.49),
                test_streams.Sine24_Mono(200000,96000,441.0,0.61,661.5,0.37),
                test_streams.Sine24_Mono(200000,44100,441.0,0.50,882.0,0.49),
                test_streams.Sine24_Mono(200000,44100,441.0,0.50,4410.0,0.49),
                test_streams.Sine24_Mono(200000,44100,8820.0,0.70,4410.0,0.29),

                test_streams.Sine24_Stereo(200000,48000,441.0,0.50,441.0,0.49,1.0),
                test_streams.Sine24_Stereo(200000,48000,441.0,0.61,661.5,0.37,1.0),
                test_streams.Sine24_Stereo(200000,96000,441.0,0.50,882.0,0.49,1.0),
                test_streams.Sine24_Stereo(200000,44100,441.0,0.50,4410.0,0.49,1.0),
                test_streams.Sine24_Stereo(200000,44100,8820.0,0.70,4410.0,0.29,1.0),
                test_streams.Sine24_Stereo(200000,44100,441.0,0.50,441.0,0.49,0.5),
                test_streams.Sine24_Stereo(200000,44100,441.0,0.61,661.5,0.37,2.0),
                test_streams.Sine24_Stereo(200000,44100,441.0,0.50,882.0,0.49,0.7),
                test_streams.Sine24_Stereo(200000,44100,441.0,0.50,4410.0,0.49,1.3),
                test_streams.Sine24_Stereo(200000,44100,8820.0,0.70,4410.0,0.29,0.1)]
        for stream in self.__class__.__stream_variations_cache__:
            stream.reset()
            yield stream

    def setUp(self):
        import audiotools.decoders
        import audiotools.encoders
        self.audio_class = audiotools.FlacAudio
        self.decoder = audiotools.decoders.FlacDecoder
        self.encode = audiotools.encoders.encode_flac
        self.encode_opts = [{"block_size":1152,
                             "max_lpc_order":0,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":3},
                            {"block_size":1152,
                             "max_lpc_order":0,
                             "adaptive_mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":3},
                            {"block_size":1152,
                             "max_lpc_order":0,
                             "exhaustive_model_search":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":3},
                            {"block_size":4096,
                             "max_lpc_order":6,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":4},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "adaptive_mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":4},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":5},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "mid_side":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":6},
                            {"block_size":4096,
                             "max_lpc_order":8,
                             "mid_side":True,
                             "exhaustive_model_search":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":6},
                            {"block_size":4096,
                             "max_lpc_order":12,
                             "mid_side":True,
                             "exhaustive_model_search":True,
                             "min_residual_partition_order":0,
                             "max_residual_partition_order":6}]

    ### these are close analogues to FLAC's test_stream.sh ###

    @TEST_FLAC
    def test_streams(self):
        for g in self.__stream_variations__():
            md5sum = md5()
            f = g.read(audiotools.BUFFER_SIZE)
            while (len(f) > 0):
                md5sum.update(f.to_bytes(False))
                f = g.read(audiotools.BUFFER_SIZE)
            self.assertEqual(md5sum.digest(),g.digest())
            g.close()

    def __test_reader__(self, pcmreader, **encode_options):
        temp_file = tempfile.NamedTemporaryFile(suffix=".flac")
        self.encode(temp_file.name,
                    pcmreader,
                    **encode_options)

        self.assertEqual(subprocess.call([audiotools.BIN["flac"],"-ts",
                                          temp_file.name]),
                         0,
                         "flac decode error on %s with options %s" % \
                             (repr(pcmreader),
                              repr(encode_options)))

        flac = audiotools.open(temp_file.name)
        self.assert_(flac.total_frames() > 0)
        if (hasattr(pcmreader,"digest")):
            self.assertEqual(flac.__md5__,pcmreader.digest())

        md5sum = md5()
        d = self.decoder(temp_file.name)
        f = d.read(audiotools.BUFFER_SIZE)
        while (len(f) > 0):
            md5sum.update(f.to_bytes(False))
            f = d.read(audiotools.BUFFER_SIZE)
        d.close()
        self.assertEqual(md5sum.digest(),pcmreader.digest())

    @TEST_FLAC
    def test_small_files(self):
        for g in [test_streams.Generate01,
                  test_streams.Generate02,
                  test_streams.Generate03,
                  test_streams.Generate04]:
            self.__test_reader__(g(44100),
                                 block_size=1152,
                                 max_lpc_order=16,
                                 min_residual_partition_order=0,
                                 max_residual_partition_order=3,
                                 mid_side=True,
                                 adaptive_mid_side=True,
                                 exhaustive_model_search=True)

    @TEST_FLAC
    def test_full_scale_deflection(self):
        for (bps,fsd) in [(8,test_streams.fsd8),
                          (16,test_streams.fsd16),
                          (24,test_streams.fsd24)]:
            for pattern in [test_streams.PATTERN01,
                            test_streams.PATTERN02,
                            test_streams.PATTERN03,
                            test_streams.PATTERN04,
                            test_streams.PATTERN05,
                            test_streams.PATTERN06,
                            test_streams.PATTERN07]:
                self.__test_reader__(
                    test_streams.MD5Reader(fsd(pattern,100)),
                    block_size=1152,
                    max_lpc_order=16,
                    min_residual_partition_order=0,
                    max_residual_partition_order=3,
                    mid_side=True,
                    adaptive_mid_side=True,
                    exhaustive_model_search=True)

    @TEST_FLAC
    def test_sines(self):
        for g in self.__stream_variations__():
            self.__test_reader__(g,
                                 block_size=1152,
                                 max_lpc_order=16,
                                 min_residual_partition_order=0,
                                 max_residual_partition_order=3,
                                 mid_side=True,
                                 adaptive_mid_side=True,
                                 exhaustive_model_search=True)

    #FIXME - add support for wasted-bps at some point

    @TEST_FLAC
    def test_blocksizes(self):
        #FIXME - handle 8bps/24bps also
        noise = audiotools.Con.GreedyRepeater(audiotools.Con.SBInt16(None)).parse(os.urandom(64))
        encoding_args = {"min_residual_partition_order":0,
                         "max_residual_partition_order":6,
                         "mid_side":True,
                         "adaptive_mid_side":True,
                         "exhaustive_model_search":True}
        for to_disable in [[],
                           ["disable_verbatim_subframes",
                            "disable_constant_subframes"],
                           ["disable_verbatim_subframes",
                            "disable_constant_subframes",
                            "disable_fixed_subframes"]]:
            for block_size in [16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33]:
                for lpc_order in [0,1,2,3,4,5,7,8,9,15,16,17,31,32]:
                    args = encoding_args.copy()
                    for disable in to_disable:
                        args[disable] = True
                    args["block_size"] = block_size
                    args["max_lpc_order"] = lpc_order
                    self.__test_reader__(test_streams.MD5Reader(
                            test_streams.FrameListReader(noise,
                                                         44100,1,16)),
                                         **args)

    @TEST_FLAC
    def test_frame_header_variations(self):
        max_lpc_order = 16

        self.__test_reader__(test_streams.Sine16_Mono(200000,96000,
                                                      441.0,0.61,661.5,0.37),
                             block_size=max_lpc_order,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000,96000,
                                                      441.0,0.61,661.5,0.37),
                             block_size=65535,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000,9,
                                                      441.0,0.61,661.5,0.37),
                             block_size=1152,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000,90,
                                                      441.0,0.61,661.5,0.37),
                             block_size=1152,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        self.__test_reader__(test_streams.Sine16_Mono(200000,90000,
                                                      441.0,0.61,661.5,0.37),
                             block_size=1152,
                             max_lpc_order=max_lpc_order,
                             min_residual_partition_order=0,
                             max_residual_partition_order=3,
                             mid_side=True,
                             adaptive_mid_side=True,
                             exhaustive_model_search=True)

        #the reference encoder's test_streams.sh unit test
        #re-does the 9Hz/90Hz/90000Hz tests for some reason
        #which I won't repeat here

    @TEST_FLAC
    def test_option_variations(self):
        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for disable in [[],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes"],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes",
                             "disable_fixed_subframes"]]:
                for extra in [[],
                              #FIXME - no analogue for -p option
                              ["exhaustive_model_search"]]:
                    for d in disable:
                        encode_opts[d] = True
                    for e in extra:
                        encode_opts[e] = True
                    for g in self.__stream_variations__():
                        self.__test_reader__(g,**encode_opts)

    @TEST_FLAC
    def test_noise(self):
        for opts in self.encode_opts:
            encode_opts = opts.copy()
            for disable in [[],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes"],
                            ["disable_verbatim_subframes",
                             "disable_constant_subframes",
                             "disable_fixed_subframes"]]:
                for channels in [1,2,4,8]:
                    for bps in [8,16,24]:
                        for extra in  [[],
                                       #FIXME - no analogue for -p option
                                       ["exhaustive_model_search"]]:
                            for blocksize in [None,32,32768,65535]:
                                for d in disable:
                                    encode_opts[d] = True
                                for e in extra:
                                    encode_opts[e] = True
                                if (blocksize is not None):
                                    encode_opts["block_size"] = blocksize
                                self.__test_reader__(
                                    EXACT_RANDOM_PCM_Reader(
                                        pcm_frames=65536,
                                        sample_rate=44100,
                                        channels=channels,
                                        bits_per_sample=bps),
                                    **encode_opts)

    ### these are close analogues to FLAC's test_flac.sh ####

    @TEST_FLAC
    def test_fractional(self):
        def __perform_test__(block_size,pcm_frames):
            self.__test_reader__(
                EXACT_RANDOM_PCM_Reader(
                    pcm_frames=pcm_frames,
                    sample_rate=44100,
                    channels=2,
                    bits_per_sample=16),
                block_size=block_size,
                max_lpc_order=8,
                min_residual_partition_order=0,
                max_residual_partition_order=6)

        for pcm_frames in [31,32,33,34,35,2046,2047,2048,2049,2050]:
            __perform_test__(33,pcm_frames)

        for pcm_frames in [254,255,256,257,258,510,511,512,513,514,1022,1023,1024,1025,1026,2046,2047,2048,2049,2050,4094,4095,4096,4097,4098]:
            __perform_test__(256,pcm_frames)

        for pcm_frames in [1022,1023,1024,1025,1026,2046,2047,2048,2049,2050,4094,4095,4096,4097,4098]:
            __perform_test__(2048,pcm_frames)

        for pcm_frames in [1022,1023,1024,1025,1026,2046,2047,2048,2049,2050,4094,4095,4096,4097,4098,4606,4607,4608,4609,4610,8190,8191,8192,8193,8194,16382,16383,16384,16385,16386]:
            __perform_test__(4608,pcm_frames)

    #PCMReaders don't yet support seeking,
    #so the seek tests can be skipped

    #cuesheets are supported at the metadata level,
    #which is tested above

    #WAVE and AIFF length fixups are handled by the
    #WaveAudio and AIFFAudio classes

    #multiple file handling is performed at the tool level

    #as is metadata handling

class TestFrameList(unittest.TestCase):
    @classmethod
    def Bits8(cls):
        for i in xrange(0,0xFF + 1):
            yield chr(i)

    @classmethod
    def Bits16(cls):
        for i in xrange(0,0xFF + 1):
            for j in xrange(0,0xFF + 1):
                yield chr(i) + chr(j)

    @classmethod
    def Bits24(cls):
        for i in xrange(0,0xFF + 1):
            for j in xrange(0,0xFF + 1):
                for k in xrange(0,0xFF + 1):
                    yield chr(i) + chr(j) + chr(k)

    @TEST_FRAMELIST
    def test_basics(self):
        import audiotools.pcm

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          "abc",2,16,0,1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          "abc",4,8,0,1)

        self.assertRaises(ValueError,
                          audiotools.pcm.FrameList,
                          "abcd",1,15,0,1)

        f = audiotools.pcm.FrameList("".join(map(chr,range(16))),
                                     2,16,1,0)
        self.assertEqual(len(f),8)
        self.assertEqual(f.channels,2)
        self.assertEqual(f.frames,4)
        self.assertEqual(f.bits_per_sample,16)
        self.assertEqual(f.signed,False)
        self.assertRaises(IndexError,f.__getitem__,17)

        self.assertEqual(list(f.frame(0)),
                         [0x0001,0x0203])
        self.assertEqual(list(f.frame(1)),
                         [0x0405,0x0607])
        self.assertEqual(list(f.frame(2)),
                         [0x0809,0x0A0B])
        self.assertEqual(list(f.frame(3)),
                         [0x0C0D,0x0E0F])
        self.assertRaises(IndexError,f.frame,4)
        self.assertRaises(IndexError,f.frame,-1)

        self.assertEqual(list(f.channel(0)),
                         [0x0001,0x0405,0x0809,0x0C0D])
        self.assertEqual(list(f.channel(1)),
                         [0x0203,0x0607,0x0A0B,0x0E0F])
        self.assertRaises(IndexError,f.channel,2)
        self.assertRaises(IndexError,f.channel,-1)

        self.assertEqual(f.to_bytes(True),
                         '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f')
        self.assertEqual(f.to_bytes(False),
                         '\x01\x00\x03\x02\x05\x04\x07\x06\t\x08\x0b\n\r\x0c\x0f\x0e')

        self.assertEqual(list(f),
                         list(audiotools.pcm.from_frames([f.frame(0),
                                                          f.frame(1),
                                                          f.frame(2),
                                                          f.frame(3)])))
        self.assertEqual(list(f),
                         list(audiotools.pcm.from_channels([f.channel(0),
                                                            f.channel(1)])))

        self.assertEqual(list(audiotools.pcm.from_list(
                    [0x0001,0x0203,0x0405,0x0607,
                     0x0809,0x0A0B,0x0C0D,0x0E0F],2,16,0)),
                         list(f))

        self.assertRaises(ValueError,
                          audiotools.pcm.from_list,
                          [0x0001,0x0203,0x0405,0x0607,
                           0x0809,0x0A0B,0x0C0D],2,16,0)

        self.assertRaises(ValueError,
                          audiotools.pcm.from_list,
                          [0x0001,0x0203,0x0405,0x0607,
                           0x0809,0x0A0B,0x0C0D,0x0E0F],2,15,0)

        #FIXME - check from_frames
        #FIXME - check from_channels

        self.assertRaises(IndexError,f.split,-1)

        (f1,f2) = f.split(2)
        self.assertEqual(list(f1),
                         [0x0001,0x0203,
                          0x0405,0x0607])
        self.assertEqual(list(f2),
                         [0x0809,0x0A0B,
                          0x0C0D,0x0E0F])

        (f1,f2) = f.split(0)
        self.assertEqual(list(f1),
                         [])
        self.assertEqual(list(f2),
                         [0x0001,0x0203,
                          0x0405,0x0607,
                          0x0809,0x0A0B,
                          0x0C0D,0x0E0F])

        (f1,f2) = f.split(20)
        self.assertEqual(list(f1),
                         [0x0001,0x0203,
                          0x0405,0x0607,
                          0x0809,0x0A0B,
                          0x0C0D,0x0E0F])
        self.assertEqual(list(f2),
                         [])

        for i in xrange(f.frames):
            (f1,f2) = f.split(i)
            self.assertEqual(len(f1),i * f.channels)
            self.assertEqual(len(f2),(len(f) - (i * f.channels)))
            self.assertEqual(list(f1 + f2),list(f))

        import operator

        f1 = audiotools.pcm.from_list(range(10),2,16,False)
        self.assertRaises(TypeError,operator.concat,f1,[1,2,3])
        f2 = audiotools.pcm.from_list(range(10,20),1,16,False)
        self.assertRaises(ValueError,operator.concat,f1,f2)
        f2 = audiotools.pcm.from_list(range(10,20),2,8,False)
        self.assertRaises(ValueError,operator.concat,f1,f2)
        f2 = audiotools.pcm.from_list(range(10,20),2,16,True)
        self.assertRaises(ValueError,operator.concat,f1,f2)

    @TEST_FRAMELIST
    def test_8bit_roundtrip(self):
        import audiotools.pcm

        unsigned_ints = range(0,0xFF + 1)
        signed_ints = range(-0x80,0x7F + 1)

        UB8Int = audiotools.Con.GreedyRepeater(audiotools.Con.UBInt8(None))
        UL8Int = audiotools.Con.GreedyRepeater(audiotools.Con.ULInt8(None))
        SB8Int = audiotools.Con.GreedyRepeater(audiotools.Con.SBInt8(None))
        SL8Int = audiotools.Con.GreedyRepeater(audiotools.Con.UBInt8(None))

        self.assertEqual(unsigned_ints,
                         list(audiotools.pcm.FrameList(
                    UB8Int.build(unsigned_ints),
                    1,8,1,0)))

        self.assertEqual(unsigned_ints,
                         list(audiotools.pcm.FrameList(
                    UL8Int.build(unsigned_ints),
                    1,8,0,0)))

        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    SB8Int.build(signed_ints),
                    1,8,1,1)))

        #this test triggers a DeprecationWarning
        #which is odd since signed little-endian 8 bit
        #should be the same as signed big-endian 8 bit
        # self.assertEqual(signed_ints,
        #                  list(audiotools.pcm.FrameList(
        #             SL8Int.build(signed_ints),
        #             1,8,0,1)))

    @TEST_FRAMELIST
    def test_8bit_roundtrip_str(self):
        import audiotools.pcm

        s = "".join(TestFrameList.Bits8())
        self.assertEqual(audiotools.pcm.FrameList(s,1,8,1,0).to_bytes(1),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,8,1,1).to_bytes(1),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,8,0,0).to_bytes(0),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,8,0,1).to_bytes(0),s)

    @TEST_FRAMELIST
    def test_16bit_roundtrip(self):
        import audiotools.pcm

        unsigned_ints = range(0,0xFFFF + 1)
        signed_ints = range(-0x8000,0x7FFF + 1)

        UB16Int = audiotools.Con.GreedyRepeater(audiotools.Con.UBInt16(None))
        UL16Int = audiotools.Con.GreedyRepeater(audiotools.Con.ULInt16(None))
        SB16Int = audiotools.Con.GreedyRepeater(audiotools.Con.SBInt16(None))
        SL16Int = audiotools.Con.GreedyRepeater(audiotools.Con.SLInt16(None))

        self.assertEqual(unsigned_ints,
                         list(audiotools.pcm.FrameList(
                    UB16Int.build(unsigned_ints),
                    1,16,1,0)))

        self.assertEqual(unsigned_ints,
                         list(audiotools.pcm.FrameList(
                    UL16Int.build(unsigned_ints),
                    1,16,0,0)))

        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    SB16Int.build(signed_ints),
                    1,16,1,1)))

        self.assertEqual(signed_ints,
                         list(audiotools.pcm.FrameList(
                    SL16Int.build(signed_ints),
                    1,16,0,1)))

    @TEST_FRAMELIST
    def test_16bit_roundtrip_str(self):
        import audiotools.pcm

        s = "".join(TestFrameList.Bits16())
        self.assertEqual(audiotools.pcm.FrameList(s,1,16,1,0).to_bytes(1),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,16,1,1).to_bytes(1),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,16,0,0).to_bytes(0),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,16,0,1).to_bytes(0),s)

    @TEST_FRAMELIST
    def test_24bit_roundtrip(self):
        import audiotools.pcm

        #setting this higher than 1 means we only test a sample
        #of the fill 24-bit value range
        #since testing the whole range takes a very, very long time
        RANGE = 8

        unsigned_ints_high = [r << 8 for r in xrange(0,0xFFFF + 1)]
        signed_ints_high = [r << 8 for r in xrange(-0x8000,0x7FFF + 1)]

        UB24Int = audiotools.Con.BitStruct(
            None,
            audiotools.Con.GreedyRepeater(audiotools.Con.Bits("i",
                                                              length=24,
                                                              swapped=False,
                                                              signed=False)))

        UL24Int = audiotools.Con.BitStruct(
            None,
            audiotools.Con.GreedyRepeater(audiotools.Con.Bits("i",
                                                              length=24,
                                                              swapped=True,
                                                              signed=False)))

        SB24Int = audiotools.Con.BitStruct(
            None,
            audiotools.Con.GreedyRepeater(audiotools.Con.Bits("i",
                                                              length=24,
                                                              swapped=False,
                                                              signed=True)))

        SL24Int = audiotools.Con.BitStruct(
            None,
            audiotools.Con.GreedyRepeater(audiotools.Con.Bits("i",
                                                              length=24,
                                                              swapped=True,
                                                              signed=True)))

        for low_bits in xrange(0,0xFF + 1,RANGE):
            unsigned_values = [high_bits | low_bits for high_bits in
                               unsigned_ints_high]

            self.assertEqual(unsigned_values,
                             list(audiotools.pcm.FrameList(
                        UB24Int.build(Con.Container(i=unsigned_values)),
                        1,24,1,0)))

            self.assertEqual(unsigned_values,
                             list(audiotools.pcm.FrameList(
                        UL24Int.build(Con.Container(i=unsigned_values)),
                        1,24,0,0)))

        for low_bits in xrange(0,0xFF + 1,RANGE):
            if (high_bits < 0):
                signed_values = [high_bits - low_bits for high_bits in
                                 signed_ints_high]
            else:
                signed_values = [high_bits + low_bits for high_bits in
                                 signed_ints_high]

            self.assertEqual(signed_values,
                             list(audiotools.pcm.FrameList(
                        SB24Int.build(Con.Container(i=signed_values)),
                        1,24,1,1)))

            self.assertEqual(signed_values,
                             list(audiotools.pcm.FrameList(
                        SL24Int.build(Con.Container(i=signed_values)),
                        1,24,0,1)))

    @TEST_FRAMELIST
    def test_24bit_roundtrip_str(self):
        import audiotools.pcm

        s = "".join(TestFrameList.Bits24())
        self.assertEqual(audiotools.pcm.FrameList(s,1,24,1,0).to_bytes(1),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,24,1,1).to_bytes(1),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,24,0,0).to_bytes(0),s)
        self.assertEqual(audiotools.pcm.FrameList(s,1,24,0,1).to_bytes(0),s)


############
#END TESTS
############

if (__name__ == '__main__'):
    unittest.main()

