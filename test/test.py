#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2009  Brian Langenberger

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
import audiotools.bitstream
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

gettext.install("audiotools",unicode=True)

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
        if (self.current_size > 0):
            buffer = os.urandom(min(bytes,self.current_size))
            self.md5.update(buffer)
            self.current_size -= len(buffer)
            return buffer
        else:
            return ""

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
                                     album_name=u"Album Name",
                                     artist_name=u"Artist Name",
                                     performer_name=u"Performer",
                                     composer_name=u"Composer",
                                     conductor_name=u"Conductor",
                                     media=u"CD",
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
                                     album_name=u"New Album Name",
                                     artist_name=u"New Artist Name",
                                     performer_name=u"New Performer",
                                     composer_name=u"New Composer",
                                     conductor_name=u"New Conductor",
                                     media=u"CD-R",
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

#this is an insane amount of different PCM combinations
PCM_COMBINATIONS = (
    (11025, 1, 8), (22050, 1, 8), (32000, 1, 8),  (44100, 1, 8),
    (48000, 1, 8), (96000, 1, 8), (192000, 1, 8), (11025, 2, 8),
    (22050, 2, 8), (32000, 2, 8), (44100, 2, 8),  (48000, 2, 8),
    (96000, 2, 8), (192000, 2, 8),(11025, 6, 8),  (22050, 6, 8),
    (32000, 6, 8), (44100, 6, 8), (48000, 6, 8),  (96000, 6, 8),
    (192000, 6, 8),(11025, 1, 16),(22050, 1, 16), (32000, 1, 16),
    (44100, 1, 16),(48000, 1, 16),(96000, 1, 16), (192000, 1, 16),
    (11025, 2, 16),(22050, 2, 16),(32000, 2, 16), (44100, 2, 16),
    (48000, 2, 16),(96000, 2, 16),(192000, 2, 16),(11025, 6, 16),
    (22050, 6, 16),(32000, 6, 16),(44100, 6, 16), (48000, 6, 16),
    (96000, 6, 16),(192000, 6, 16),(11025, 1, 24),(22050, 1, 24),
    (32000, 1, 24),(44100, 1, 24),(48000, 1, 24), (96000, 1, 24),
    (192000, 1, 24),(11025, 2, 24),(22050, 2, 24),(32000, 2, 24),
    (44100, 2, 24),(48000, 2, 24),(96000, 2, 24), (192000, 2, 24),
    (11025, 6, 24),(22050, 6, 24),(32000, 6, 24), (44100, 6, 24),
    (48000, 6, 24),(96000, 6, 24),(192000, 6, 24))

#these are combinations that tend to occur in nature
SHORT_PCM_COMBINATIONS = ((11025, 1, 8),  (22050, 1, 8),
                          (22050, 1, 16), (32000, 2, 16),
                          (44100, 1, 16), (44100, 2, 16),
                          (48000, 1, 16), (48000, 2, 16),
                          (48000, 6, 16),
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
    def testpcmcombinations(self):
        for (sample_rate,channels,bits_per_sample) in SHORT_PCM_COMBINATIONS:
            reader = BLANK_PCM_Reader(SHORT_LENGTH,
                                      sample_rate, channels,
                                      bits_per_sample)
            counter = PCM_Count()
            audiotools.transfer_data(reader.read,counter.write)
            self.assertEqual(len(counter),reader.total_size)

class TestAiffAudio(unittest.TestCase):
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

    def testmetadata(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            metadata = DummyMetaData()
            new_file.set_metadata(metadata)
            if (new_file.get_metadata() is not None):
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata,new_file.get_metadata())

                metadata2 = DummyMetaData2()
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())

                metadata2.track_name = u'Track Name 3'
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())
        finally:
            temp.close()

    def testimages(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if ((new_file.get_metadata() is not None)
                and (new_file.get_metadata().supports_images())):
                metadata = DummyMetaData()
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
    def test_track2track_massencode(self):
        base_file = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            base = self.audio_class.from_pcm(base_file.name,
                                             BLANK_PCM_Reader(SHORT_LENGTH))
            metadata = DummyMetaData3()

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

    #tests the splitting and concatenating programs
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
                                 "-V","quiet",
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

    def test_tracktag_trackrename(self):
        template = "%(track_number)2.2d - %(album_number)d - %(album_track_number)s%(track_name)s%(album_name)s%(artist_name)s%(performer_name)s%(composer_name)s%(conductor_name)s%(media)s%(ISRC)s%(copyright)s%(publisher)s%(year)s%(suffix)s"

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

            flag_field_values = zip(["--name",
                                     "--artist",
                                     "--performer",
                                     "--composer",
                                     "--conductor",
                                     "--album",
                                     "--number",
                                     "--ISRC",
                                     "--publisher",
                                     "--media-type",
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
                                     "ISRC",
                                     "publisher",
                                     "media",
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
                                     "ISRC-NUM",
                                     "Publisher Name",
                                     "Media",
                                     "2008",
                                     "Copyright Text",
                                     "Some Lengthy Text Comment"])

            for (flag,field,value) in flag_field_values:
                subprocess.call(["tracktag",
                                 flag,str(value),
                                 track.filename])
                setattr(metadata,field,value)
                self.assertEqual(metadata,track.get_metadata())

                new_path = os.path.join(basedir,
                                        self.audio_class.track_name(
                        metadata.track_number,
                        metadata,
                        metadata.album_number,
                        template))

                subprocess.call(["trackrename",
                                 "-V","quiet",
                                 "--format",template,
                                 track.filename])

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)

            os.rename(track.filename,
                      os.path.join(basedir,"track.%s" % \
                                       (self.audio_class.SUFFIX)))
            track = audiotools.open(os.path.join(basedir,"track.%s" % \
                                                     (self.audio_class.SUFFIX)))

            for (flag,field,value) in flag_field_values:
                subprocess.call(["tracktag",
                                 "--replace",
                                 flag,str(value),
                                 track.filename])
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

                subprocess.call(["trackrename",
                                 "-V","quiet",
                                 "--format",template,
                                 track.filename])

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
                    subprocess.call(["tracktag",
                                     flag,str(value),
                                     track.filename])
                    metadata.add_image(audiotools.Image.new(
                            data,u"",img_type))
                    self.assertEqual(metadata.images(),
                                     track.get_metadata().images())

                for (flag,img_type,value,data) in flag_type_images_data:
                    subprocess.call(["tracktag",
                                     "--remove-images",
                                     flag,str(value),
                                     track.filename])
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

    def testinvalidbinaries(self):
        if (len(self.audio_class.BINARIES) == 0):
            return

        temp_track_file = tempfile.NamedTemporaryFile(
            suffix=self.audio_class.SUFFIX)

        temp_track = self.audio_class.from_pcm(
            temp_track_file.name,
            BLANK_PCM_Reader(5))

        wave_temp_file = tempfile.NamedTemporaryFile(suffix=".wav")

        wave_file = audiotools.WaveAudio.from_pcm(
            wave_temp_file.name,
            BLANK_PCM_Reader(5))

        #grab our original binaries so we can point them back later
        old_settings = [(bin,audiotools.config.get_default("Binaries",bin,bin))
                        for bin in self.audio_class.BINARIES]
        try:
            for bin in self.audio_class.BINARIES:
                audiotools.config.set("Binaries",bin,"./error.py")

            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_pcm,
                              "test.%s" % (self.audio_class.SUFFIX),
                              BLANK_PCM_Reader(5))

            self.assertRaises(audiotools.DecodingError,
                              audiotools.WaveAudio.from_pcm,
                              "test.wav",
                              temp_track.to_pcm())

            self.assertRaises(audiotools.EncodingError,
                              self.audio_class.from_wave,
                              "test.%s" % (self.audio_class.SUFFIX),
                              wave_file.filename)

            self.assertRaises(audiotools.DecodingError,
                              temp_track.to_wave,
                              "test.wav")
        finally:
            for (bin,setting) in old_settings:
                audiotools.config.set("Binaries",bin,setting)
            wave_temp_file.close()
            temp_track_file.close()

class TestForeignWaveChunks:
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
            wav.set_metadata(DummyMetaData())
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
                    suffix=self.audio_class.SUFFIX)
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
                            suffix=new_class.SUFFIX)
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


class TestFlacAudio(EmbeddedCuesheet,TestForeignWaveChunks,VorbisLint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.FlacAudio

    def testpreservevendortags(self):
        tempflac1 = tempfile.NamedTemporaryFile(suffix=".flac")
        tempflac2 = tempfile.NamedTemporaryFile(suffix=".flac")

        f1 = audiotools.FlacAudio.from_pcm(tempflac1.name,
                                           BLANK_PCM_Reader(3))
        f1.set_metadata(DummyMetaData())

        f2 = audiotools.FlacAudio.from_pcm(tempflac2.name,
                                           f1.to_pcm())

        f2.set_metadata(f1.get_metadata())

        self.assertEqual(f1.get_metadata().vorbis_comment.vendor_string,
                         f2.get_metadata().vorbis_comment.vendor_string)


class APEv2Lint:
    #tracklint is tricky to test since set_metadata()
    #usually won't write anything that needs fixing.
    #For instance, it won't generate empty fields or leading zeroes in numbers.
    #So, bogus ID3 tags must be generated at a lower level.
    def test_tracklint(self):
        bad_apev2 = audiotools.ApeTag(
            {"Title":u"Track Name  ",
             "Track":u"02",
             "Artist":u"  Some Artist",
             "Performer":u"Some Artist",
             "Catalog":u"",
             "Year":u"  ",
             "Comment":u"  Some Comment  "})

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
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_apev2[key])

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
            for (key,value) in metadata.items():
                self.assertEqual(value,bad_apev2[key])
        finally:
            for f in os.listdir(tempdir):
                os.unlink(os.path.join(tempdir,f))
            os.rmdir(tempdir)

class TestWavPackAudio(EmbeddedCuesheet,TestForeignWaveChunks,APEv2Lint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.WavPackAudio

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

class M4AMetadata:
    #M4A supports only a subset of the MetaData of every other format
    #so it must be handled separately
    def testmetadata(self):
        temp = tempfile.NamedTemporaryFile(suffix="." + self.audio_class.SUFFIX)
        try:
            new_file = self.audio_class.from_pcm(temp.name,
                                                 BLANK_PCM_Reader(TEST_LENGTH))

            if (new_file.get_metadata() is not None):
                metadata = audiotools.MetaData(track_name=u"Track Name",
                                               track_number=5,
                                               album_name=u"Album Name",
                                               artist_name=u"Artist Name",
                                               performer_name=u"Performer")
                new_file.set_metadata(metadata)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata,new_file.get_metadata())

                metadata2 = audiotools.MetaData(track_name=u"New Track Name",
                                                track_number=6,
                                                album_name=u"New Album Name",
                                                artist_name=u"New Artist Name",
                                                performer_name=u"New Performer")
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())

                metadata2.track_name = u'Track Name 3'
                new_file.set_metadata(metadata2)
                new_file = audiotools.open(temp.name)
                self.assertEqual(metadata2,new_file.get_metadata())
        finally:
            temp.close()

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

    def test_tracktag_trackrename(self):
        template = "%(track_number)2.2d - %(album_number)d - %(album_track_number)s%(track_name)s%(album_name)s%(artist_name)s%(performer_name)s%(composer_name)s%(conductor_name)s%(media)s%(ISRC)s%(copyright)s%(publisher)s%(year)s%(suffix)s"

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

            self.assertEqual(metadata.track_name,"Name")

            flag_field_values = zip(["--name",
                                     "--artist",
                                     "--performer",
                                     "--composer",
                                     "--album",
                                     "--number",
                                     "--year",
                                     "--copyright",
                                     "--comment"],
                                    ["track_name",
                                     "artist_name",
                                     "performer_name",
                                     "composer_name",
                                     "album_name",
                                     "track_number",
                                     "year",
                                     "copyright",
                                     "comment"],
                                    ["Track Name",
                                     "Artist Name",
                                     "Performer Name",
                                     "Composer Name",
                                     "Album Name",
                                     2,
                                     "2008",
                                     "Copyright Text",
                                     "Some Lengthy Text Comment"])

            for (flag,field,value) in flag_field_values:
                subprocess.call(["tracktag",
                                 flag,str(value),
                                 track.filename])
                setattr(metadata,field,value)
                self.assertEqual(metadata,track.get_metadata())

                new_path = os.path.join(basedir,
                                        self.audio_class.track_name(
                        metadata.track_number,
                        metadata,
                        metadata.album_number,
                        template))

                subprocess.call(["trackrename",
                                 "-V","quiet",
                                 "--format",template,
                                 track.filename])

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)

            os.rename(track.filename,
                      os.path.join(basedir,"track.%s" % \
                                       (self.audio_class.SUFFIX)))
            track = audiotools.open(os.path.join(basedir,"track.%s" % \
                                                     (self.audio_class.SUFFIX)))

            for (flag,field,value) in flag_field_values:
                subprocess.call(["tracktag",
                                 "--replace",
                                 flag,str(value),
                                 track.filename])
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

                subprocess.call(["trackrename",
                                 "-V","quiet",
                                 "--format",template,
                                 track.filename])

                self.assertEqual(os.path.isfile(new_path),True)
                track = audiotools.open(new_path)
                metadata = track.get_metadata()
        finally:
            for f in os.listdir(basedir):
                os.unlink(os.path.join(basedir,f))
            os.rmdir(basedir)

    def test_coverdump(self):
        pass

    def test_invalid_name(self):
        metadata = audiotools.MetaData(track_name=u"Name",
                                       track_number=1)
        format = "%(track_number)2.2d - %(track_name)s"

        self.assertEqual(self.audio_class.track_name(track_number=1,
                                                     track_metadata=metadata,
                                                     format=format),
                         "01 - Name")

        self.assertEqual(self.audio_class.track_name(track_number=2,
                                                     track_metadata=metadata,
                                                     format=format),
                         "02 - Name")

        metadata.track_name = u"Name / Test"

        self.assertEqual(self.audio_class.track_name(track_number=1,
                                                     track_metadata=metadata,
                                                     format=format),
                         "01 - Name - Test")

        metadata.track_name = u"Name\u0000Test"

        self.assertEqual(self.audio_class.track_name(track_number=1,
                                                     track_metadata=metadata,
                                                     format=format),
                         "01 - Name Test")

        metadata.track_name = u"Name\u0000/\u0000Test"

        self.assertEqual(self.audio_class.track_name(track_number=1,
                                                     track_metadata=metadata,
                                                     format=format),
                         "01 - Name - Test")

# class TestAlacAudio(M4AMetadata,TestAiffAudio):
#    def setUp(self):
#        self.audio_class = audiotools.ALACAudio

class TestOggFlacAudio(EmbeddedCuesheet,VorbisLint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.OggFlacAudio

    def testpreservevendortags(self):
        tempflac1 = tempfile.NamedTemporaryFile(suffix=".flac")
        tempflac2 = tempfile.NamedTemporaryFile(suffix=".flac")

        f1 = audiotools.FlacAudio.from_pcm(tempflac1.name,
                                           BLANK_PCM_Reader(3))
        f1.set_metadata(DummyMetaData())

        f2 = audiotools.FlacAudio.from_pcm(tempflac2.name,
                                           f1.to_pcm())

        f2.set_metadata(f1.get_metadata())

        self.assertEqual(f1.get_metadata().vorbis_comment.vendor_string,
                         f2.get_metadata().vorbis_comment.vendor_string)

class ID3Lint:
    #tracklint is tricky to test since set_metadata()
    #usually won't write anything that needs fixing.
    #For instance, it won't generate empty fields or leading zeroes in numbers.
    #So, bogus ID3 tags must be generated at a lower level.
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

class TestMP2Audio(ID3Lint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.MP2Audio

class TestVorbisAudio(VorbisLint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.VorbisAudio

class TestM4AAudio(M4AMetadata,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.M4AAudio

    def test_tracklint(self):
        bad_m4a = audiotools.M4AMetaData(
            {'\xa9nam':[u"Track Name  "],
             'trkn':['\x00\x00\x00\x02\x00\x00\x00\x00'],
             'disk':['\x00\x00\x00\x03\x00\x00'],
             '\xa9ART':[u"  Some Artist"],
             'aART':[u"Some Artist"],
             'cprt':[u""],
             '\xa9day':[u"  "],
             '\xa9cmt':[u"  Some Comment  "]})

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

class TestMusepackAudio(APEv2Lint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.MusepackAudio

class TestSpeexAudio(VorbisLint,TestAiffAudio):
    def setUp(self):
        self.audio_class = audiotools.SpeexAudio

# class TestApeAudio(TestForeignWaveChunks,APEv2Lint,TestAiffAudio):
#    def setUp(self):
#        self.audio_class = audiotools.ApeAudio

class TestID3v2(unittest.TestCase):
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
        attribs1 = {}  #a dict of attribute -> value pairs ("track_name":u"foo")
        attribs2 = {}  #a dict of ID3v2 -> value pairs     ("TT2":u"foo")
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                attribs1[attribute] = attribs2[key] = u"value %d" % (i)
            else:
                attribs1[attribute] = attribs2[key] = i

        id3 = id3_class.converted(audiotools.MetaData(**attribs1))

        self.mp3_file.set_metadata(id3)
        self.assertEqual(self.mp3_file.get_metadata(),id3)
        id3 = self.mp3_file.get_metadata()

        #ensure that all the attributes match up
        for (attribute,value) in attribs1.items():
            self.assertEqual(getattr(id3,attribute),value)

        #ensure that all the keys match up
        for (key,value) in attribs2.items():
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(unicode(id3[key][0]),value)
            else:
                self.assertEqual(int(id3[key][0]),value)

        #ensure that changing attributes changes the underlying frame
        #>>> id3.track_name = u"bar"
        #>>> id3['TT2'][0] == u"bar"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            if (key not in id3_class.INTEGER_ITEMS):
                setattr(id3,attribute,u"new value %d" % (i))
                self.assertEqual(unicode(id3[key][0]),u"new value %d" % (i))
            else:
                setattr(id3,attribute,i + 10)
                self.assertEqual(int(id3[key][0]),i + 10)

        #reset and re-check everything for the next round
        id3 = id3_class.converted(audiotools.MetaData(**attribs1))
        self.mp3_file.set_metadata(id3)
        self.assertEqual(self.mp3_file.get_metadata(),id3)
        id3 = self.mp3_file.get_metadata()

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
            if (key not in id3_class.INTEGER_ITEMS):
                id3[key] = [u"new value %d" % (i)]
                self.mp3_file.set_metadata(id3)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(getattr(id3,attribute),u"new value %d" % (i))
            else:
                id3[key] = [i + 10]
                self.mp3_file.set_metadata(id3)
                id3 = self.mp3_file.get_metadata()
                self.assertEqual(getattr(id3,attribute),i + 10)

        #ensure that nutty track and album numbers are handled correctly
        #in both directions
        for attribute in ('track_number','album_number'):
            id3 = self.mp3_file.get_metadata()
            setattr(id3,attribute,u"5/10")
            self.mp3_file.set_metadata(id3)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(getattr(id3,attribute),5)
            self.assertEqual(
                unicode(id3[id3_class.ATTRIBUTE_MAP[attribute]][0]),u"5/10")

        id3.track_number = 1
        id3.album_number = 2
        self.mp3_file.set_metadata(id3)

        for attribute in ('track_number','album_number'):
            field = id3_class.ATTRIBUTE_MAP[attribute]
            id3 = self.mp3_file.get_metadata()
            id3[field] = [id3_class.TextFrame.from_unicode(field,u"5/10")]
            self.mp3_file.set_metadata(id3)
            id3 = self.mp3_file.get_metadata()
            self.assertEqual(getattr(id3,attribute),5)
            self.assertEqual(unicode(id3[field][0]),u"5/10")

        #finally, just for kicks, ensure that explicitly setting
        #frames also changes attributes
        #>>> id3['TT2'] = [id3_class.TextFrame.from_unicode('TT2',u"foo")]
        #>>> id3.track_name = u"foo"
        for (i,(attribute,key)) in enumerate(id3_class.ATTRIBUTE_MAP.items()):
            id3[key] = [id3_class.TextFrame.from_unicode(key,unicode(i))]
            self.mp3_file.set_metadata(id3)
            id3 = self.mp3_file.get_metadata()
            if (key not in id3_class.INTEGER_ITEMS):
                self.assertEqual(getattr(id3,attribute),unicode(i))
            else:
                self.assertEqual(getattr(id3,attribute),i)

    def testid3v2_2(self):
        self.__comment_test__(audiotools.ID3v22Comment)
        self.__dict_test__(audiotools.ID3v22Comment)

    def testid3v2_3(self):
        self.__comment_test__(audiotools.ID3v23Comment)
        self.__dict_test__(audiotools.ID3v23Comment)

    def testid3v2_4(self):
        self.__comment_test__(audiotools.ID3v24Comment)
        self.__dict_test__(audiotools.ID3v24Comment)

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

    def tearDown(self):
        self.file.close()

class TestFlacComment(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".flac")

        self.flac_file = audiotools.FlacAudio.from_pcm(
            self.file.name,BLANK_PCM_Reader(TEST_LENGTH))

    def testsetpicture(self):
        m = DummyMetaData()
        m.add_image(audiotools.Image.new(TEST_COVER1,
                                         u'Unicode \u3057\u3066\u307f\u308b',
                                         1))
        self.flac_file.set_metadata(m)

        new_flac_file = audiotools.open(self.file.name)
        m2 = new_flac_file.get_metadata()

        self.assertEqual(m.images()[0],m2.images()[0])

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

    def tearDown(self):
        self.file.close()

class TestPCMConversion(unittest.TestCase):
    def setUp(self):
        self.tempwav = tempfile.NamedTemporaryFile(suffix=".wav")

    def tearDown(self):
        self.tempwav.close()

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
    def testinvalidstreams(self):
        self.assertRaises(ValueError,
                          audiotools.pcmstream.PCMStreamReader,
                          cStringIO.StringIO(chr(0) * 10),0,False,False)

        self.assertRaises(ValueError,
                          audiotools.pcmstream.PCMStreamReader,
                          cStringIO.StringIO(chr(0) * 10),5,False,False)

        r = audiotools.pcmstream.PCMStreamReader(None,2,False,False)
        self.assertRaises(AttributeError,r.read,10)

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

class testbitstream(unittest.TestCase):
    def testinvalidstream(self):
        b = audiotools.bitstream.BitStreamReader(None)
        self.assertRaises(AttributeError,
                          b.read,10)

    def testcompliance(self):
        allbits = "".join(map(chr,range(0,0x100)) + \
                          map(chr,reversed(range(0,0x100)))) * 20
        for i in xrange(1,65):
            reader1 = Con.BitStreamReader(cStringIO.StringIO(allbits))
            reader2 = audiotools.bitstream.BitStreamReader(cStringIO.StringIO(allbits))
            sum1 = md5()
            sum2 = md5()

            for (reader,sum) in ((reader1,sum1),(reader2,sum2)):
                bits = reader.read(i)
                while (len(bits) > 0):
                    sum.update(bits)
                    bits = reader.read(i)
                reader.close()

            self.assertEqual(sum1.hexdigest(),sum2.hexdigest())

class testbufferedstream(unittest.TestCase):
    def testbuffer(self):
        reader = VARIABLE_PCM_Reader(TEST_LENGTH)
        bufferedreader = audiotools.BufferedPCMReader(reader)

        output = md5()

        s = bufferedreader.read(4096)
        while (len(s) > 0):
            output.update(s)
            s = bufferedreader.read(4096)

        self.assertEqual(output.hexdigest(),reader.hexdigest())

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
                    suffix=audio_class.SUFFIX)
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
    def setUp(self):
        from construct import Container

        self.sheet_class = audiotools.FlacCueSheet
        self.suffix = '.flac'
        self.test_sheets = [
            Container(catalog_number = '4580226563955\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                      cuesheet_tracks = [
                    Container(ISRC = 'JPG750800183',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 1,
                              track_offset = 0),
                    Container(ISRC = 'JPG750800212',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 2,
                              track_offset = 12280380),
                    Container(ISRC = 'JPG750800214',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0), Container(offset = 130536, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 3,
                              track_offset = 24807132),
                    Container(ISRC = 'JPG750800704',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0), Container(offset = 135828, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 4,
                              track_offset = 28954296),
                    Container(ISRC = 'JPG750800705',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 5,
                              track_offset = 31019352),
                    Container(ISRC = 'JPG750800706',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 6,
                              track_offset = 40957728),
                    Container(ISRC = 'JPG750800707',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 7,
                              track_offset = 56111664),
                    Container(ISRC = 'JPG750800708',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 93492, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 8,
                              track_offset = 69543348),
                    Container(ISRC = 'JPG750800219',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 9,
                              track_offset = 80537184),
                    Container(ISRC = 'JPG750800722',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 78792, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 10,
                              track_offset = 81398604),
                    Container(ISRC = 'JPG750800709',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 11,
                              track_offset = 91970256),
                    Container(ISRC = 'JPG750800290',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 12,
                              track_offset = 99292032),
                    Container(ISRC = 'JPG750800218',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 13,
                              track_offset = 110377008),
                    Container(ISRC = 'JPG750800710',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 75264, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 14,
                              track_offset = 113040060),
                    Container(ISRC = 'JPG750800217',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 15,
                              track_offset = 117804036),
                    Container(ISRC = 'JPG750800531',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 16,
                              track_offset = 120531180),
                    Container(ISRC = 'JPG750800225',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 17,
                              track_offset = 133673568),
                    Container(ISRC = 'JPG750800711',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 98196, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 18,
                              track_offset = 143108616),
                    Container(ISRC = 'JPG750800180',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 81732, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 19,
                              track_offset = 156345084),
                    Container(ISRC = 'JPG750800712',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 197568, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 20,
                              track_offset = 172052328),
                    Container(ISRC = 'JPG750800713',
                              cuesheet_track_index = [Container(offset = 0, point_number = 0),
                                                      Container(offset = 135240, point_number = 1)
],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 21,
                              track_offset = 178101084),
                    Container(ISRC = 'JPG750800714',
                              cuesheet_track_index = [Container(offset = 0, point_number = 1)],
                              non_audio = False,
                              pre_emphasis = False,
                              track_number = 22,
                              track_offset = 189107268),
                    Container(ISRC = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
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

    def test_formatting(self):
        LENGTH = 1134
        OFFSETS = [150, 18740, 40778, 44676, 63267]

        #ensure that latin-1 and UTF-8 encodings are handled properly
        for (encoding,data) in zip(["ISO-8859-1","ISO-8859-1","UTF-8"],
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

        #construct a fresh our XMCD file
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


class TestProgramOutput(unittest.TestCase):
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
        #FIXME
        pass

    def __check_info__(self,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            s + u"\n")

    def __check_error__(self,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            u"*** Error: " + s + u"\n")

    def __check_warning__(self,s):
        self.assertEqual(
            self.stderr.readline().decode(audiotools.IO_ENCODING),
            u"*** Warning: " + s + u"\n")

    def __check_usage__(self,s):
        #FIXME
        pass

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

        self.__check_error__(_(u"Invalid XMCD file"))

        #FIXME - check invalid thumbnails

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

    def tearDown(self):
        for f in os.listdir(self.dir1):
            os.unlink(os.path.join(self.dir1,f))
        os.rmdir(self.dir1)

        for f in os.listdir(self.dir2):
            os.unlink(os.path.join(self.dir2,f))
        os.rmdir(self.dir2)


############
#END TESTS
############

if (__name__ == '__main__'):
    unittest.main()

