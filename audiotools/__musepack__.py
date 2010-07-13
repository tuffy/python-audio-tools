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


from audiotools import (AudioFile, InvalidFile, InvalidFormat, PCMReader,
                        PCMConverter, Con, subprocess, BIN, ApeTaggedAudio,
                        os, TempWaveReader, ignore_sigint, transfer_data,
                        EncodingError, DecodingError)
from __wav__ import WaveAudio
import gettext

gettext.install("audiotools", unicode=True)

#######################
#Musepack Audio
#######################


class NutValue(Con.Adapter):
    """A construct for Musepack Nut-encoded integer fields."""

    def __init__(self, name):
        Con.Adapter.__init__(
            self,
            Con.RepeatUntil(lambda obj, ctx: (obj & 0x80) == 0x00,
                            Con.UBInt8(name)))

    def _encode(self, value, context):
        data = [value & 0x7F]
        value = value >> 7

        while (value != 0):
            data.append(0x80 | (value & 0x7F))
            value = value >> 7

        data.reverse()
        return data

    def _decode(self, obj, context):
        i = 0
        for x in obj:
            i = (i << 7) | (x & 0x7F)
        return i


class Musepack8StreamReader:
    """An object for parsing Musepack SV8 streams."""

    NUT_HEADER = Con.Struct('nut_header',
                            Con.String('key', 2),
                            NutValue('length'))

    def __init__(self, stream):
        """Initialized with a file object."""

        self.stream = stream

    def packets(self):
        """Yields a set of (key, data) tuples."""

        import string

        UPPERCASE = frozenset(string.ascii_uppercase)

        while (True):
            try:
                frame_header = self.NUT_HEADER.parse_stream(self.stream)
            except Con.core.FieldError:
                break

            if (not frozenset(frame_header.key).issubset(UPPERCASE)):
                break

            yield (frame_header.key,
                   self.stream.read(frame_header.length -
                                    len(self.NUT_HEADER.build(frame_header))))


class MusepackAudio(ApeTaggedAudio, AudioFile):
    """A Musepack audio file."""

    SUFFIX = "mpc"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "standard"
    COMPRESSION_MODES = ("thumb", "radio", "standard", "extreme", "insane")

    ###Musepack SV7###
    #BINARIES = ('mppdec','mppenc')

    ###Musepack SV8###
    BINARIES = ('mpcdec', 'mpcenc')

    MUSEPACK8_HEADER = Con.Struct('musepack8_header',
                                  Con.UBInt32('crc32'),
                                  Con.Byte('bitstream_version'),
                                  NutValue('sample_count'),
                                  NutValue('beginning_silence'),
                                  Con.Embed(Con.BitStruct(
        'flags',
        Con.Bits('sample_frequency', 3),
        Con.Bits('max_used_bands', 5),
        Con.Bits('channel_count', 4),
        Con.Flag('mid_side_used'),
        Con.Bits('audio_block_frames', 3))))

    #not sure about some of the flag locations
    #Musepack 7's header is very unusual
    MUSEPACK7_HEADER = Con.Struct('musepack7_header',
                                 Con.Const(Con.String('signature', 3), 'MP+'),
                                 Con.Byte('version'),
                                 Con.ULInt32('frame_count'),
                                 Con.ULInt16('max_level'),
                                 Con.Embed(
        Con.BitStruct('flags',
                      Con.Bits('profile', 4),
                      Con.Bits('link', 2),
                      Con.Bits('sample_frequency', 2),
                      Con.Flag('intensity_stereo'),
                      Con.Flag('midside_stereo'),
                      Con.Bits('maxband', 6))),
                                 Con.ULInt16('title_gain'),
                                 Con.ULInt16('title_peak'),
                                 Con.ULInt16('album_gain'),
                                 Con.ULInt16('album_peak'),
                                 Con.Embed(
        Con.BitStruct('more_flags',
                      Con.Bits('unused1', 16),
                      Con.Bits('last_frame_length_low', 4),
                      Con.Flag('true_gapless'),
                      Con.Bits('unused2', 3),
                      Con.Flag('fast_seeking'),
                      Con.Bits('last_frame_length_high', 7))),
                                 Con.Bytes('unknown', 3),
                                 Con.Byte('encoder_version'))

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)
        f = file(filename, 'rb')
        try:
            if (f.read(4) == 'MPCK'):  # a Musepack 8 stream
                for (key, packet) in Musepack8StreamReader(f).packets():
                    if (key == 'SH'):
                        header = MusepackAudio.MUSEPACK8_HEADER.parse(packet)

                        self.__sample_rate__ = (44100, 48000,
                                                37800, 32000)[
                            header.sample_frequency]

                        self.__total_frames__ = header.sample_count
                        self.__channels__ = header.channel_count + 1

                        break
                    elif (key == 'SE'):
                        raise InvalidFile(_(u'No Musepack header found'))

            else:                      # a Musepack 7 stream
                f.seek(0, 0)

                try:
                    header = MusepackAudio.MUSEPACK7_HEADER.parse_stream(f)
                except Con.ConstError:
                    raise InvalidFile(_(u'Musepack signature incorrect'))

                header.last_frame_length = \
                                   (header.last_frame_length_high << 4) | \
                                   header.last_frame_length_low

                self.__sample_rate__ = (44100, 48000,
                                        37800, 32000)[header.sample_frequency]
                self.__total_frames__ = (((header.frame_count - 1) * 1152) +
                                         header.last_frame_length)

                self.__channels__ = 2
        finally:
            f.close()

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new MusepackAudio object."""

        import tempfile
        import bisect

        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if ((pcmreader.channels > 2) or
            (pcmreader.sample_rate not in (44100, 48000, 37800, 32000)) or
            (pcmreader.bits_per_sample != 16)):
            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=[32000, 32000, 37800, 44100, 48000][bisect.bisect(
                        [32000, 37800, 44100, 48000], pcmreader.sample_rate)],
                channels=min(pcmreader.channels, 2),
                bits_per_sample=16)

        f = tempfile.NamedTemporaryFile(suffix=".wav")
        w = WaveAudio.from_pcm(f.name, pcmreader)
        try:
            return cls.__from_wave__(filename, f.name, compression)
        finally:
            del(w)
            f.close()

    #While Musepack needs to pipe things through WAVE,
    #not all WAVEs are acceptable.
    #Use the *_pcm() methods first.
    def __to_wave__(self, wave_filename):
        devnull = file(os.devnull, "wb")
        try:
            sub = subprocess.Popen([BIN['mpcdec'],
                                    self.filename,
                                    wave_filename],
                                   stdout=devnull,
                                   stderr=devnull)

            #FIXME - small files (~5 seconds) result in an error by mpcdec,
            #even if they decode correctly.
            #Not much we can do except try to workaround its bugs.
            if (sub.wait() not in [0, 250]):
                raise DecodingError()
        finally:
            devnull.close()

    @classmethod
    def __from_wave__(cls, filename, wave_filename, compression=None):
        if (str(compression) not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        #mppenc requires files to end with .mpc for some reason
        if (not filename.endswith(".mpc")):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".mpc")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

        ###Musepack SV7###
        #sub = subprocess.Popen([BIN['mppenc'],
        #                        "--silent",
        #                        "--overwrite",
        #                        "--%s" % (compression),
        #                        wave_filename,
        #                        filename],
        #                       preexec_fn=ignore_sigint)

        ###Musepack SV8###
        sub = subprocess.Popen([BIN['mpcenc'],
                                "--silent",
                                "--overwrite",
                                "--%s" % (compression),
                                wave_filename,
                                filename])

        if (sub.wait() == 0):
            if (tempfile is not None):
                filename = actual_filename
                f = file(filename, 'wb')
                tempfile.seek(0, 0)
                transfer_data(tempfile.read, f.write)
                f.close()
                tempfile.close()

            return MusepackAudio(filename)
        else:
            if (tempfile is not None):
                tempfile.close()
            raise EncodingError(u"error encoding file with mpcenc")

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(4)

        ###Musepack SV7###
        #return header == 'MP+\x07'

        ###Musepack SV8###
        return (header == 'MP+\x07') or (header == 'MPCK')

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__sample_rate__

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__total_frames__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return 16

    def lossless(self):
        """Returns False."""

        return False
