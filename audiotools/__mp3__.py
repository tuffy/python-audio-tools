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


from audiotools import (AudioFile, InvalidFile, PCMReader, PCMConverter,
                        Con, transfer_data, transfer_framelist_data,
                        subprocess, BIN, BIG_ENDIAN, ApeTag, ReplayGain,
                        ignore_sigint, open_files, EncodingError,
                        DecodingError, PCMReaderError, ChannelMask)
from __id3__ import *
import gettext

gettext.install("audiotools", unicode=True)


#######################
#MP3
#######################


class MP3Exception(InvalidFile):
    pass


class MP3Audio(AudioFile):
    SUFFIX = "mp3"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "2"
    #0 is better quality/lower compression
    #9 is worse quality/higher compression
    COMPRESSION_MODES = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
    BINARIES = ("lame",)

    #MPEG1, Layer 1
    #MPEG1, Layer 2,
    #MPEG1, Layer 3,
    #MPEG2, Layer 1,
    #MPEG2, Layer 2,
    #MPEG2, Layer 3
    MP3_BITRATE = ((None, None, None, None, None, None),
                   (32, 32, 32, 32, 8, 8),
                   (64, 48, 40, 48, 16, 16),
                   (96, 56, 48, 56, 24, 24),
                   (128, 64, 56, 64, 32, 32),
                   (160, 80, 64, 80, 40, 40),
                   (192, 96, 80, 96, 48, 48),
                   (224, 112, 96, 112, 56, 56),
                   (256, 128, 112, 128, 64, 64),
                   (288, 160, 128, 144, 80, 80),
                   (320, 192, 160, 160, 96, 96),
                   (352, 224, 192, 176, 112, 112),
                   (384, 256, 224, 192, 128, 128),
                   (416, 320, 256, 224, 144, 144),
                   (448, 384, 320, 256, 160, 160))

    #MPEG1, MPEG2, MPEG2.5
    MP3_SAMPLERATE = ((44100, 22050, 11025),
                      (48000, 24000, 12000),
                      (32000, 16000, 8000))

    MP3_FRAME_HEADER = Con.BitStruct("mp3_header",
                                  Con.Bits("sync", 11),
                                  Con.Bits("mpeg_version", 2),
                                  Con.Bits("layer", 2),
                                  Con.Bits("protection", 1),
                                  Con.Bits("bitrate", 4),
                                  Con.Bits("sampling_rate", 2),
                                  Con.Bits("padding", 1),
                                  Con.Bits("private", 1),
                                  Con.Bits("channel", 2),
                                  Con.Bits("mode_extension", 2),
                                  Con.Bits("copyright", 1),
                                  Con.Bits("original", 1),
                                  Con.Bits("emphasis", 2))

    XING_HEADER = Con.Struct("xing_header",
                             Con.Bytes("header_id", 4),
                             Con.Bytes("flags", 4),
                             Con.UBInt32("num_frames"),
                             Con.UBInt32("bytes"),
                             Con.StrictRepeater(100, Con.Byte("toc_entries")),
                             Con.UBInt32("quality"))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        mp3file = file(filename, "rb")
        try:
            MP3Audio.__find_next_mp3_frame__(mp3file)
            fr = MP3Audio.MP3_FRAME_HEADER.parse(mp3file.read(4))
            self.__samplerate__ = MP3Audio.__get_mp3_frame_sample_rate__(fr)
            self.__channels__ = MP3Audio.__get_mp3_frame_channels__(fr)
            self.__framelength__ = self.__length__()
        finally:
            mp3file.close()

    @classmethod
    def is_type(cls, file):
        ID3v2Comment.skip(file)

        try:
            frame = cls.MP3_FRAME_HEADER.parse_stream(file)
            if ((frame.sync == 0x07FF) and
                (frame.mpeg_version in (0x03, 0x02, 0x00)) and
                (frame.layer in (0x01, 0x03))):
                return True
            else:
                #oddly, MP3s sometimes turn up in RIFF containers
                #this isn't a good idea, but can be supported nonetheless
                file.seek(-cls.MP3_FRAME_HEADER.sizeof(), 1)
                header = file.read(12)
                if ((header[0:4] == 'RIFF') and
                    (header[8:12] == 'RMP3')):
                    return True
                else:
                    return False
        except:
            return False

    def lossless(self):
        return False

    def to_pcm(self):
        #if mpg123 is available, use that for decoding
        if (BIN.can_execute(BIN["mpg123"])):
            sub = subprocess.Popen([BIN["mpg123"], "-qs", self.filename],
                                   stdout=subprocess.PIPE,
                                   stderr=file(os.devnull, "a"))
            return PCMReader(sub.stdout,
                             sample_rate=self.sample_rate(),
                             channels=self.channels(),
                             bits_per_sample=16,
                             channel_mask=int(ChannelMask.from_channels(
                        self.channels())),
                             process=sub,
                             big_endian=BIG_ENDIAN)
        else:
            #if not, use LAME for decoding
            if (self.filename.endswith("." + self.SUFFIX)):
                if (BIG_ENDIAN):
                    endian = ['-x']
                else:
                    endian = []

                sub = subprocess.Popen([BIN['lame']] + endian + \
                                           ["--decode", "-t", "--quiet",
                                            self.filename, "-"],
                                       stdout=subprocess.PIPE)
                return PCMReader(sub.stdout,
                                 sample_rate=self.sample_rate(),
                                 channels=self.channels(),
                                 bits_per_sample=16,
                                 channel_mask=int(ChannelMask.from_channels(
                            self.channels())),
                                 process=sub)
            else:
                import tempfile
                from audiotools import TempWaveReader
                #copy our file to one that ends with .mp3
                tempmp3 = tempfile.NamedTemporaryFile(suffix='.' + self.SUFFIX)
                f = open(self.filename, 'rb')
                transfer_data(f.read, tempmp3.write)
                f.close()
                tempmp3.flush()

                #decode the mp3 file to a WAVE file
                wave = tempfile.NamedTemporaryFile(suffix='.wav')
                returnval = subprocess.call([BIN['lame'], "--decode",
                                             "--quiet",
                                             tempmp3.name, wave.name])
                tempmp3.close()

                if (returnval == 0):
                    #return WAVE file as a stream
                    wave.seek(0, 0)
                    return TempWaveReader(wave)
                else:
                    return PCMReaderError(None,
                                          sample_rate=self.sample_rate(),
                                          channels=self.channels(),
                                          bits_per_sample=16)

    @classmethod
    def __help_output__(cls):
        import cStringIO
        help_data = cStringIO.StringIO()
        sub = subprocess.Popen([BIN['lame'], '--help'],
                               stdout=subprocess.PIPE)
        transfer_data(sub.stdout.read, help_data.write)
        sub.wait()
        return help_data.getvalue()

    @classmethod
    def __lame_version__(cls):
        try:
            version = re.findall(r'version \d+\.\d+',
                                 cls.__help_output__())[0]
            return tuple(map(int, version[len('version '):].split(".")))
        except IndexError:
            return (0, 0)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="2"):
        import decimal
        import bisect

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if ((pcmreader.channels > 2) or
            (pcmreader.sample_rate not in (32000, 48000, 44100))):
            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=[32000, 32000, 44100, 48000][bisect.bisect(
                        [32000, 44100, 48000], pcmreader.sample_rate)],
                channels=min(pcmreader.channels, 2),
                channel_mask=ChannelMask.from_channels(
                    min(pcmreader.channels, 2)),
                bits_per_sample=16)

        if (pcmreader.channels > 1):
            mode = "j"
        else:
            mode = "m"

        #FIXME - not sure if all LAME versions support "--little-endian"
        # #LAME 3.98 (and up, presumably) handle the byteswap correctly
        # #LAME 3.97 always uses -x
        # if (BIG_ENDIAN or (cls.__lame_version__() < (3,98))):
        #     endian = ['-x']
        # else:
        #     endian = []

        devnull = file(os.devnull, 'ab')

        sub = subprocess.Popen([
                BIN['lame'], "--quiet",
                "-r",
                "-s", str(decimal.Decimal(pcmreader.sample_rate) / 1000),
                "--bitwidth", str(pcmreader.bits_per_sample),
                "--signed", "--little-endian",
                "-m", mode,
                "-V" + str(compression),
                "-",
                filename],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)

        transfer_framelist_data(pcmreader, sub.stdin.write)
        try:
            pcmreader.close()
        except DecodingError:
            raise EncodingError()
        sub.stdin.close()

        devnull.close()

        if (sub.wait() == 0):
            return MP3Audio(filename)
        else:
            raise EncodingError(BIN['lame'])

    def bits_per_sample(self):
        return 16

    def channels(self):
        return self.__channels__

    def sample_rate(self):
        return self.__samplerate__

    def get_metadata(self):
        f = file(self.filename, "rb")
        try:
            if (f.read(3) != "ID3"):      # no ID3v2 tag, try ID3v1
                id3v1 = ID3v1Comment.read_id3v1_comment(self.filename)
                if (id3v1[-1] == -1):     # no ID3v1 either
                    return None
                else:
                    return ID3v1Comment(id3v1)
            else:
                id3v2 = ID3v2Comment.read_id3v2_comment(self.filename)

                id3v1 = ID3v1Comment.read_id3v1_comment(self.filename)
                if (id3v1[-1] == -1):      # only ID3v2, no ID3v1
                    return id3v2
                else:                      # both ID3v2 and ID3v1
                    return ID3CommentPair(
                        id3v2,
                        ID3v1Comment(id3v1))
        finally:
            f.close()

    def set_metadata(self, metadata):
        if (metadata is None):
            return

        if ((not isinstance(metadata, ID3v2Comment)) and
            (not isinstance(metadata, ID3v1Comment))):
            metadata = ID3CommentPair.converted(metadata)

        #metadata = ID3v24Comment.converted(metadata)

        #get the original MP3 data
        f = file(self.filename, "rb")
        MP3Audio.__find_mp3_start__(f)
        data_start = f.tell()
        MP3Audio.__find_last_mp3_frame__(f)
        data_end = f.tell()
        f.seek(data_start, 0)
        mp3_data = f.read(data_end - data_start)
        f.close()

        if (isinstance(metadata, ID3CommentPair)):
            id3v2 = metadata.id3v2.build()
            id3v1 = metadata.id3v1.build_tag()
        elif (isinstance(metadata, ID3v2Comment)):
            id3v2 = metadata.build()
            id3v1 = ""
        elif (isinstance(metadata, ID3v1Comment)):
            id3v2 = ""
            id3v1 = metadata.build_tag()

        #write id3v2 + data + id3v1 to file
        f = file(self.filename, "wb")
        f.write(id3v2)
        f.write(mp3_data)
        f.write(id3v1)
        f.close()

    def delete_metadata(self):
        #get the original MP3 data
        f = file(self.filename, "rb")
        MP3Audio.__find_mp3_start__(f)
        data_start = f.tell()
        MP3Audio.__find_last_mp3_frame__(f)
        data_end = f.tell()
        f.seek(data_start, 0)
        mp3_data = f.read(data_end - data_start)
        f.close()

        #write data to file
        f = file(self.filename, "wb")
        f.write(mp3_data)
        f.close()

    #places mp3file at the position of the next MP3 frame's start
    @classmethod
    def __find_next_mp3_frame__(cls, mp3file):
        #if we're starting at an ID3v2 header, skip it to save a bunch of time
        ID3v2Comment.skip(mp3file)

        #then find the next mp3 frame
        (b1, b2) = mp3file.read(2)
        while ((b1 != chr(0xFF)) or ((ord(b2) & 0xE0) != 0xE0)):
            mp3file.seek(-1, 1)
            (b1, b2) = mp3file.read(2)
        mp3file.seek(-2, 1)

    #places mp3file at the position of the MP3 file's start
    #either at the next frame (most commonly)
    #or at the "RIFF????RMP3" header
    @classmethod
    def __find_mp3_start__(cls, mp3file):
        #if we're starting at an ID3v2 header, skip it to save a bunch of time
        ID3v2Comment.skip(mp3file)

        while (True):
            byte = mp3file.read(1)
            while ((byte != chr(0xFF)) and (byte != 'R') and (len(byte) > 0)):
                byte = mp3file.read(1)

            if (byte == chr(0xFF)):  # possibly a frame sync
                mp3file.seek(-1, 1)
                try:
                    header = cls.MP3_FRAME_HEADER.parse_stream(mp3file)
                    if ((header.sync == 0x07FF) and
                        (header.mpeg_version in (0x03, 0x02, 0x00)) and
                        (header.layer in (0x01, 0x02, 0x03))):
                        mp3file.seek(-4, 1)
                        return
                    else:
                        mp3file.seek(-3, 1)
                except:
                    continue
            elif (byte == 'R'):     # possibly a 'RIFF????RMP3' header
                header = mp3file.read(11)
                if ((header[0:3] == 'IFF') and
                    (header[7:11] == 'RMP3')):
                    mp3file.seek(-12, 1)
                    return
                else:
                    mp3file.seek(-11, 1)
            elif (len(byte) == 0):  # we've run out of MP3 file
                return

    #places mp3file at the position of the last MP3 frame's end
    #(either the last byte in the file or just before the ID3v1 tag)
    #this may not be strictly accurate if ReplayGain data is present,
    #since APEv2 tags came before the ID3v1 tag,
    #but we're not planning to change that tag anyway
    @classmethod
    def __find_last_mp3_frame__(cls, mp3file):
        mp3file.seek(-128, 2)
        if (mp3file.read(3) == 'TAG'):
            mp3file.seek(-128, 2)
            return
        else:
            mp3file.seek(0, 2)
        return

    #header is a Construct parsed from 4 bytes sent to MP3_FRAME_HEADER
    #returns the total length of the frame, including the header
    #(subtract 4 when doing a seek or read to the next one)
    @classmethod
    def __mp3_frame_length__(cls, header):
        layer = 4 - header.layer  # layer 1, 2 or 3

        bit_rate = MP3Audio.__get_mp3_frame_bitrate__(header)
        if (bit_rate is None):
            raise MP3Exception(_(u"Invalid bit rate"))

        sample_rate = MP3Audio.__get_mp3_frame_sample_rate__(header)

        if (layer == 1):
            return (12 * (bit_rate * 1000) / sample_rate + header.padding) * 4
        else:
            return 144 * (bit_rate * 1000) / sample_rate + header.padding

    #takes a parsed MP3_FRAME_HEADER
    #returns the mp3's sample rate based on that information
    #(typically 44100)
    @classmethod
    def __get_mp3_frame_sample_rate__(cls, frame):
        try:
            if (frame.mpeg_version == 0x00):    # MPEG 2.5
                return MP3Audio.MP3_SAMPLERATE[frame.sampling_rate][2]
            elif (frame.mpeg_version == 0x02):  # MPEG 2
                return MP3Audio.MP3_SAMPLERATE[frame.sampling_rate][1]
            else:                               # MPEG 1
                return MP3Audio.MP3_SAMPLERATE[frame.sampling_rate][0]
        except IndexError:
            raise MP3Exception(_(u"Invalid sampling rate"))

    @classmethod
    def __get_mp3_frame_channels__(cls, frame):
        if (frame.channel == 0x03):
            return 1
        else:
            return 2

    @classmethod
    def __get_mp3_frame_bitrate__(cls, frame):
        layer = 4 - frame.layer  # layer 1, 2 or 3

        try:
            if (frame.mpeg_version == 0x00):    # MPEG 2.5
                return MP3Audio.MP3_BITRATE[frame.bitrate][layer + 2]
            elif (frame.mpeg_version == 0x02):  # MPEG 2
                return MP3Audio.MP3_BITRATE[frame.bitrate][layer + 2]
            elif (frame.mpeg_version == 0x03):  # MPEG 1
                return MP3Audio.MP3_BITRATE[frame.bitrate][layer - 1]
            else:
                return 0
        except IndexError:
            raise MP3Exception(_(u"Invalid bit rate"))

    def cd_frames(self):
        #calculate length at create-time so that we can
        #throw MP3Exception as soon as possible
        return self.__framelength__

    #returns the length of this file in CD frame
    #raises MP3Exception if any portion of the frame is invalid
    def __length__(self):
        mp3file = file(self.filename, "rb")

        try:
            MP3Audio.__find_next_mp3_frame__(mp3file)

            start_position = mp3file.tell()

            fr = MP3Audio.MP3_FRAME_HEADER.parse(mp3file.read(4))

            first_frame = mp3file.read(MP3Audio.__mp3_frame_length__(fr) - 4)

            sample_rate = MP3Audio.__get_mp3_frame_sample_rate__(fr)

            if (fr.mpeg_version == 0x00):    # MPEG 2.5
                version = 3
            elif (fr.mpeg_version == 0x02):  # MPEG 2
                version = 3
            else:                            # MPEG 1
                version = 0

            try:
                if (fr.layer == 0x03):    # layer 1
                    frames_per_sample = 384
                    bit_rate = MP3Audio.MP3_BITRATE[fr.bitrate][version]
                elif (fr.layer == 0x02):  # layer 2
                    frames_per_sample = 1152
                    bit_rate = MP3Audio.MP3_BITRATE[fr.bitrate][version + 1]
                elif (fr.layer == 0x01):  # layer 3
                    frames_per_sample = 1152
                    bit_rate = MP3Audio.MP3_BITRATE[fr.bitrate][version + 2]
                else:
                    raise MP3Exception(_(u"Unsupported MPEG layer"))
            except IndexError:
                raise MP3Exception(_(u"Invalid bit rate"))

            if ('Xing' in first_frame):
                #the first frame has a Xing header,
                #use that to calculate the mp3's length
                xing_header = MP3Audio.XING_HEADER.parse(
                    first_frame[first_frame.index('Xing'):])

                return (xing_header.num_frames * frames_per_sample * 75 /
                        sample_rate)
            else:
                #no Xing header,
                #assume a constant bitrate file
                mp3file.seek(-128, 2)
                if (mp3file.read(3) == "TAG"):
                    end_position = mp3file.tell() - 3
                else:
                    mp3file.seek(0, 2)
                    end_position = mp3file.tell()

                return ((end_position - start_position) * 75 * 8 /
                        (bit_rate * 1000))
        finally:
            mp3file.close()

    def total_frames(self):
        return self.cd_frames() * self.sample_rate() / 75

    @classmethod
    def can_add_replay_gain(cls):
        return BIN.can_execute(BIN['mp3gain'])

    @classmethod
    def lossless_replay_gain(cls):
        return False

    @classmethod
    def add_replay_gain(cls, filenames):
        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track, cls)]

        if ((len(track_names) > 0) and (BIN.can_execute(BIN['mp3gain']))):
            devnull = file(os.devnull, 'ab')
            sub = subprocess.Popen([BIN['mp3gain'], '-f', '-k', '-q', '-r'] + \
                                       track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()

            devnull.close()


#######################
#MP2 AUDIO
#######################

class MP2Audio(MP3Audio):
    SUFFIX = "mp2"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = str(192)
    COMPRESSION_MODES = map(str, (32,  48,  56,  64,  80,  96,  112,
                                  128, 160, 192, 224, 256, 320, 384))
    BINARIES = ("lame", "twolame")

    @classmethod
    def is_type(cls, file):
        ID3v2Comment.skip(file)

        try:
            frame = cls.MP3_FRAME_HEADER.parse_stream(file)

            return ((frame.sync == 0x07FF) and
                    (frame.mpeg_version in (0x03, 0x02, 0x00)) and
                    (frame.layer == 0x02))
        except:
            return False

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression="192"):
        import decimal
        import bisect

        if (compression not in cls.COMPRESSION_MODES):
            compression = cls.DEFAULT_COMPRESSION

        if ((pcmreader.channels > 2) or
            (pcmreader.sample_rate not in (32000, 48000, 44100)) or
            (pcmreader.bits_per_sample != 16)):
            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=[32000, 32000, 44100, 48000][bisect.bisect(
                        [32000, 44100, 48000], pcmreader.sample_rate)],
                channels=min(pcmreader.channels, 2),
                channel_mask=pcmreader.channel_mask,
                bits_per_sample=16)

        devnull = file(os.devnull, 'ab')

        sub = subprocess.Popen([BIN['twolame'], "--quiet",
                                "-r",
                                "-s", str(pcmreader.sample_rate),
                                "--samplesize", str(pcmreader.bits_per_sample),
                                "-N", str(pcmreader.channels),
                                "-m", "a",
                                "-b", compression,
                                "-",
                                filename],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)

        transfer_framelist_data(pcmreader, sub.stdin.write)
        try:
            pcmreader.close()
        except DecodingError:
            raise EncodingError()
        sub.stdin.close()

        devnull.close()

        if (sub.wait() == 0):
            return MP2Audio(filename)
        else:
            raise EncodingError(BIN['twolame'])
