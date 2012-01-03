#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2012  Brian Langenberger

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
                        transfer_data, transfer_framelist_data,
                        subprocess, BIN, BIG_ENDIAN, ApeTag, ReplayGain,
                        ignore_sigint, open_files, EncodingError,
                        DecodingError, PCMReaderError, ChannelMask,
                        __default_quality__, config)
from __id3__ import *
import gettext

gettext.install("audiotools", unicode=True)


#######################
#MP3
#######################


class InvalidMP3(InvalidFile):
    """Raised by invalid files during MP3 initialization."""

    pass


class MP3Audio(AudioFile):
    """An MP3 audio file."""

    SUFFIX = "mp3"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "2"
    #0 is better quality/lower compression
    #9 is worse quality/higher compression
    COMPRESSION_MODES = ("0", "1", "2", "3", "4", "5", "6",
                         "medium", "standard", "extreme", "insane")
    COMPRESSION_DESCRIPTIONS = {"0": _(u"high quality, larger files, " +
                                       u"corresponds to lame's -V0"),
                                "6": _(u"lower quality, smaller files, " +
                                       u"corresponds to lame's -V6"),
                                "medium": _(u"corresponds to lame's " +
                                            u"--preset medium"),
                                "standard": _(u"corresponds to lame's " +
                                              u"--preset standard"),
                                "extreme": _(u"corresponds to lame's " +
                                             u"--preset extreme"),
                                "insane": _(u"corresponds to lame's " +
                                            u"--preset insane")}
    BINARIES = ("lame",)
    REPLAYGAIN_BINARIES = ("mp3gain", )

    SAMPLE_RATE = ((11025, 12000, 8000, None),  #MPEG-2.5
                   (None, None, None, None),    #reserved
                   (22050, 24000, 16000, None), #MPEG-2
                   (44100, 48000, 32000, None)) #MPEG-1

    BIT_RATE = (
        #MPEG-2.5
        (
            #reserved
            (None,) * 16,
            #layer III
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            #layer II
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            #layer I
            (None, 32000, 48000, 56000, 64000, 80000, 96000, 112000,
             128000, 144000, 160000, 176000, 192000, 224000, 256000, None),
        ),
        #reserved
        ((None,) * 16, ) * 4,
        #MPEG-2
        (
            #reserved
            (None,) * 16,
            #layer III
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            #layer II
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            #layer I
            (None, 32000, 48000, 56000, 64000, 80000, 96000, 112000,
             128000, 144000, 160000, 176000, 192000, 224000, 256000, None),
            ),
        #MPEG-1
        (
            #reserved
            (None,) * 16,
            #layer III
            (None, 32000, 40000, 48000, 56000, 64000, 80000, 96000,
             112000, 128000, 160000, 192000, 224000, 256000, 320000, None),
            #layer II
            (None, 32000, 48000, 56000, 64000, 80000, 96000, 112000,
             128000, 160000, 192000, 224000, 256000, 320000, 384000, None),
            #layer I
            (None, 32000, 64000, 96000, 128000, 160000, 192000, 224000,
             256000, 288000, 320000, 352000, 384000, 416000, 448000, None)
            )
        )

    PCM_FRAMES_PER_MPEG_FRAME = (None, 1152, 1152, 384)

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)

        from .bitstream import BitstreamReader

        try:
            mp3file = open(filename, "rb")
        except IOError, msg:
            raise InvalidMP3(str(msg))

        try:
            try:
                header_bytes = MP3Audio.__find_next_mp3_frame__(mp3file)
            except IOError:
                raise InvalidMP3(_(u"MP3 frame not found"))

            (frame_sync,
             mpeg_id,
             layer,
             bit_rate,
             sample_rate,
             pad,
             channels) = BitstreamReader(mp3file, 0).parse(
                "11u 2u 2u 1p 4u 2u 1u 1p 2u 6p")

            self.__samplerate__ = self.SAMPLE_RATE[mpeg_id][sample_rate]
            if (self.__samplerate__ is None):
                raise InvalidMP3(_(u"Invalid sample rate"))
            if (channels in (0, 1, 2)):
                self.__channels__ = 2
            else:
                self.__channels__ = 1

            first_frame = mp3file.read(self.frame_length(mpeg_id,
                                                         layer,
                                                         bit_rate,
                                                         sample_rate,
                                                         pad) - 4)

            if ("Xing" in first_frame):
                #pull length from Xing header, if present
                self.__pcm_frames__ = (
                    BitstreamReader(
                        cStringIO.StringIO(
                            first_frame[first_frame.index("Xing"):
                                            first_frame.index("Xing") + 160]),
                        0).parse("32p 32p 32u 32p 832p")[0] *
                    self.PCM_FRAMES_PER_MPEG_FRAME[layer])
            else:
                #otherwise, bounce through file frames
                reader = BitstreamReader(mp3file, 0)
                self.__pcm_frames__ = 0

                try:
                    (frame_sync,
                     mpeg_id,
                     layer,
                     bit_rate,
                     sample_rate,
                     pad) = reader.parse("11u 2u 2u 1p 4u 2u 1u 9p")

                    while (frame_sync == 0x7FF):
                        self.__pcm_frames__ += \
                            self.PCM_FRAMES_PER_MPEG_FRAME[layer]

                        reader.skip_bytes(self.frame_length(mpeg_id,
                                                            layer,
                                                            bit_rate,
                                                            sample_rate,
                                                            pad) - 4)

                        (frame_sync,
                         mpeg_id,
                         layer,
                         bit_rate,
                         sample_rate,
                         pad) = reader.parse("11u 2u 2u 1p 4u 2u 1u 9p")
                except IOError:
                    pass
                except ValueError,err:
                    raise InvalidMP3(unicode(err))
        finally:
            mp3file.close()

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        from .bitstream import BitstreamReader

        try:
            skip_id3v2_comment(file)

            (frame_sync,
             mpeg_id,
             layer) = BitstreamReader(file, 0).parse("11u 2u 2u 1p")

            return ((frame_sync == 0x7FF) and
                    (mpeg_id in (0, 2, 3)) and
                    (layer in (1, 3)))
        except IOError:
            return False

    def lossless(self):
        """Returns False."""

        return False

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

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
                return PCMReader(
                    sub.stdout,
                    sample_rate=self.sample_rate(),
                    channels=self.channels(),
                    bits_per_sample=16,
                    channel_mask=int(self.channel_mask()),
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
                    return PCMReaderError(
                        error_message=u"lame exited with error",
                        sample_rate=self.sample_rate(),
                        channels=self.channels(),
                        channel_mask=int(self.channel_mask()),
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
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new MP3Audio object."""

        import decimal
        import bisect

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

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

        if (str(compression) in map(str, range(0, 10))):
            compression = ["-V" + str(compression)]
        else:
            compression = ["--preset", str(compression)]

        sub = subprocess.Popen([
                BIN['lame'], "--quiet",
                "-r",
                "-s", str(decimal.Decimal(pcmreader.sample_rate) / 1000),
                "--bitwidth", str(pcmreader.bits_per_sample),
                "--signed", "--little-endian",
                "-m", mode] + compression + ["-", filename],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)

        try:
            transfer_framelist_data(pcmreader, sub.stdin.write)
        except (IOError, ValueError), err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise err

        try:
            pcmreader.close()
        except DecodingError, err:
            cls.__unlink__(filename)
            raise EncodingError(err.error_message)
        sub.stdin.close()

        devnull.close()

        if (sub.wait() == 0):
            return MP3Audio(filename)
        else:
            cls.__unlink__(filename)
            raise EncodingError(u"error encoding file with lame")

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return 16

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__samplerate__

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        f = file(self.filename, "rb")
        try:
            if (f.read(3) != "ID3"):      # no ID3v2 tag, try ID3v1
                try:
                    # no ID3v2, yes ID3v1
                    return ID3v1Comment.parse(f)
                except ValueError:
                    # no ID3v2, no ID3v1
                    return None
            else:
                id3v2 = read_id3v2_comment(self.filename)

                try:
                    # yes IDv2, yes ID3v1
                    return ID3CommentPair(id3v2,
                                          ID3v1Comment.parse(f))
                except ValueError:
                    # yes ID3v2, no ID3v1
                    return id3v2
        finally:
            f.close()

    def update_metadata(self, metadata):
        """Takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object.

        Raises IOError if unable to write the file.
        """

        if (metadata is None):
            return
        elif (not (isinstance(metadata, ID3v2Comment) or
                   isinstance(metadata, ID3CommentPair) or
                   isinstance(metadata, ID3v1Comment))):
            raise _(u"metadata not from audio file")

        #get the original MP3 data
        f = file(self.filename, "rb")
        MP3Audio.__find_mp3_start__(f)
        data_start = f.tell()
        MP3Audio.__find_last_mp3_frame__(f)
        data_end = f.tell()
        f.seek(data_start, 0)
        mp3_data = f.read(data_end - data_start)
        f.close()

        from .bitstream import BitstreamWriter

        #write id3v2 + data + id3v1 to file
        f = file(self.filename, "wb")
        if (isinstance(metadata, ID3CommentPair)):
            metadata.id3v2.build(BitstreamWriter(f, 0))
            f.write(mp3_data)
            metadata.id3v1.build(f)
        elif (isinstance(metadata, ID3v2Comment)):
            metadata.build(BitstreamWriter(f, 0))
            f.write(mp3_data)
        elif (isinstance(metadata, ID3v1Comment)):
            f.write(mp3_data)
            metadata.build(f)
        f.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        if (metadata is None):
            return

        if (not (isinstance(metadata, ID3v2Comment) or
                 isinstance(metadata, ID3CommentPair) or
                 isinstance(metadata, ID3v1Comment))):
            DEFAULT_ID3V2 = "id3v2.3"
            DEFAULT_ID3V1 = "id3v1.1"

            id3v2_class = {"id3v2.2": ID3v22Comment,
                           "id3v2.3": ID3v23Comment,
                           "id3v2.4": ID3v24Comment,
                           "none": None}.get(config.get_default("ID3",
                                                                "id3v2",
                                                                DEFAULT_ID3V2),
                                             DEFAULT_ID3V2)
            id3v1_class = {"id3v1.1": ID3v1Comment,
                           "none": None}.get(config.get_default("ID3",
                                                                "id3v1",
                                                                DEFAULT_ID3V1))
            if ((id3v2_class is not None) and (id3v1_class is not None)):
                self.update_metadata(
                    ID3CommentPair.converted(metadata,
                                             id3v2_class=id3v2_class,
                                             id3v1_class=id3v1_class))
            elif (id3v2_class is not None):
                self.update_metadata(id3v2_class.converted(metadata))
            elif (id3v1_class is not None):
                self.update_metadata(id3v1_class.converted(metadata))
            else:
                return
        else:
            self.update_metadata(metadata)

    def delete_metadata(self):
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

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
        bytes_skipped = skip_id3v2_comment(mp3file)

        #then find the next mp3 frame
        from .bitstream import BitstreamReader

        reader = BitstreamReader(mp3file, 0)
        reader.mark()
        try:
            (sync,
             mpeg_id,
             layer_description) = reader.parse("11u 2u 2u 1p")
        except IOError, err:
            reader.unmark()
            raise err

        while (not ((sync == 0x7FF) and
                    (mpeg_id in (0, 2, 3)) and
                    (layer_description in (1, 2, 3)))):
            reader.rewind()
            reader.unmark()
            reader.skip(8)
            bytes_skipped += 1
            reader.mark()
            try:
                (sync,
                 mpeg_id,
                 layer_description) = reader.parse("11u 2u 2u 1p")
            except IOError, err:
                reader.unmark()
                raise err
        else:
            reader.rewind()
            reader.unmark()
            return bytes_skipped

    @classmethod
    def __find_mp3_start__(cls, mp3file):
        """places mp3file at the position of the MP3 file's start"""

        #if we're starting at an ID3v2 header, skip it to save a bunch of time
        skip_id3v2_comment(mp3file)

        from .bitstream import BitstreamReader

        reader = BitstreamReader(mp3file, 0)

        #skip over any bytes that aren't a valid MPEG header
        reader.mark()
        (frame_sync, mpeg_id, layer) = reader.parse("11u 2u 2u 1p")
        while (not ((frame_sync == 0x7FF) and
                    (mpeg_id in (0, 2, 3)) and
                    (layer in (1, 2, 3)))):
            reader.rewind()
            reader.unmark()
            reader.skip(8)
            reader.mark()
        reader.rewind()
        reader.unmark()

    @classmethod
    def __find_last_mp3_frame__(cls, mp3file):
        """places mp3file at the position of the last MP3 frame's end

        (either the last byte in the file or just before the ID3v1 tag)
        this may not be strictly accurate if ReplayGain data is present,
        since APEv2 tags came before the ID3v1 tag,
        but we're not planning to change that tag anyway
        """

        mp3file.seek(-128, 2)
        if (mp3file.read(3) == 'TAG'):
            mp3file.seek(-128, 2)
            return
        else:
            mp3file.seek(0, 2)
        return

    def frame_length(self, mpeg_id, layer, bit_rate, sample_rate, pad):
        """returns the total MP3 frame length in bytes

        the given arguments are the header's bit values
        mpeg_id     = 2 bits
        layer       = 2 bits
        bit_rate    = 4 bits
        sample_rate = 2 bits
        pad         = 1 bit
        """

        sample_rate = self.SAMPLE_RATE[mpeg_id][sample_rate]
        if (sample_rate is None):
            raise ValueError(_(u"Invalid sample rate"))
        bit_rate = self.BIT_RATE[mpeg_id][layer][bit_rate]
        if (bit_rate is None):
            raise ValueError(_(u"Invalid bit rate"))
        if (layer == 3): #layer I
            return (((12 * bit_rate) / sample_rate) + pad) * 4
        else:            #layer II/III
            return ((144 * bit_rate) / sample_rate) + pad


    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__pcm_frames__

    @classmethod
    def can_add_replay_gain(cls):
        """Returns True if we have the necessary binaries to add ReplayGain."""

        return BIN.can_execute(BIN['mp3gain'])

    @classmethod
    def lossless_replay_gain(cls):
        """Returns False."""

        return False

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """Adds ReplayGain values to a list of filename strings.

        All the filenames must be of this AudioFile type.
        Raises ValueError if some problem occurs during ReplayGain application.
        """

        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track, cls)]

        if (progress is not None):
            progress(0, 1)

        if ((len(track_names) > 0) and (BIN.can_execute(BIN['mp3gain']))):
            devnull = file(os.devnull, 'ab')
            sub = subprocess.Popen([BIN['mp3gain'], '-f', '-k', '-q', '-r'] + \
                                       track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()

            devnull.close()

        if (progress is not None):
            progress(1, 1)

    def verify(self, progress=None):
        from . import verify
        try:
            f = open(self.filename, 'rb')
        except IOError, err:
            raise InvalidMP3(str(err))

        #MP3 verification is likely to be so fast
        #that individual calls to progress() are
        #a waste of time.
        if (progress is not None):
            progress(0, 1)

        try:
            try:
                #skip ID3v2/ID3v1 tags during verification
                self.__find_mp3_start__(f)
                start = f.tell()
                self.__find_last_mp3_frame__(f)
                end = f.tell()
                f.seek(start, 0)

                verify.mpeg(f, start, end)
                if (progress is not None):
                    progress(1, 1)

                return True
            except (IOError, ValueError), err:
                raise InvalidMP3(str(err))
        finally:
            f.close()


#######################
#MP2 AUDIO
#######################

class MP2Audio(MP3Audio):
    """An MP2 audio file."""

    SUFFIX = "mp2"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = str(192)
    COMPRESSION_MODES = tuple(map(str, (64,  96,  112, 128, 160, 192,
                                        224, 256, 320, 384)))
    COMPRESSION_DESCRIPTIONS = {"64": _(u"total bitrate of 64kbps"),
                                "384": _(u"total bitrate of 384kbps")}
    BINARIES = ("lame", "twolame")

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        from .bitstream import BitstreamReader

        try:
            skip_id3v2_comment(file)

            (frame_sync,
             mpeg_id,
             layer) = BitstreamReader(file, 0).parse("11u 2u 2u 1p")

            return ((frame_sync == 0x7FF) and
                    (mpeg_id in (0, 2, 3)) and
                    (layer == 2))
        except IOError:
            return False

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new MP2Audio object."""

        import decimal
        import bisect

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

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

        try:
            transfer_framelist_data(pcmreader, sub.stdin.write)
        except (ValueError, IOError), err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception, err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise err

        try:
            pcmreader.close()
        except DecodingError, err:
            cls.__unlink__(filename)
            raise EncodingError(err.error_message)

        sub.stdin.close()
        devnull.close()

        if (sub.wait() == 0):
            return MP2Audio(filename)
        else:
            cls.__unlink__(filename)
            raise EncodingError(u"twolame exited with error")
