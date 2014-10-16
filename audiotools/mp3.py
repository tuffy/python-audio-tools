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


from audiotools import (AudioFile, InvalidFile)


class InvalidMP3(InvalidFile):
    """raised by invalid files during MP3 initialization"""

    pass


class MP3Audio(AudioFile):
    """an MP3 audio file"""

    from audiotools.text import (COMP_LAME_0,
                                 COMP_LAME_6,
                                 COMP_LAME_MEDIUM,
                                 COMP_LAME_STANDARD,
                                 COMP_LAME_EXTREME,
                                 COMP_LAME_INSANE)

    SUFFIX = "mp3"
    NAME = SUFFIX
    DESCRIPTION = u"MPEG-1 Audio Layer III"
    DEFAULT_COMPRESSION = "2"
    # 0 is better quality/lower compression
    # 9 is worse quality/higher compression
    COMPRESSION_MODES = ("0", "1", "2", "3", "4", "5", "6",
                         "medium", "standard", "extreme", "insane")
    COMPRESSION_DESCRIPTIONS = {"0": COMP_LAME_0,
                                "6": COMP_LAME_6,
                                "medium": COMP_LAME_MEDIUM,
                                "standard": COMP_LAME_STANDARD,
                                "extreme": COMP_LAME_EXTREME,
                                "insane": COMP_LAME_INSANE}

    SAMPLE_RATE = ((11025, 12000, 8000, None),   # MPEG-2.5
                   (None, None, None, None),     # reserved
                   (22050, 24000, 16000, None),  # MPEG-2
                   (44100, 48000, 32000, None))  # MPEG-1

    BIT_RATE = (
        # MPEG-2.5
        (
            # reserved
            (None,) * 16,
            # layer III
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            # layer II
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            # layer I
            (None, 32000, 48000, 56000, 64000, 80000, 96000, 112000,
             128000, 144000, 160000, 176000, 192000, 224000, 256000, None),
        ),
        # reserved
        ((None,) * 16, ) * 4,
        # MPEG-2
        (
            # reserved
            (None,) * 16,
            # layer III
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            # layer II
            (None, 8000, 16000, 24000, 32000, 40000, 48000, 56000,
             64000, 80000, 96000, 112000, 128000, 144000, 160000, None),
            # layer I
            (None, 32000, 48000, 56000, 64000, 80000, 96000, 112000,
             128000, 144000, 160000, 176000, 192000, 224000, 256000, None)),
        # MPEG-1
        (
            # reserved
            (None,) * 16,
            # layer III
            (None, 32000, 40000, 48000, 56000, 64000, 80000, 96000,
             112000, 128000, 160000, 192000, 224000, 256000, 320000, None),
            # layer II
            (None, 32000, 48000, 56000, 64000, 80000, 96000, 112000,
             128000, 160000, 192000, 224000, 256000, 320000, 384000, None),
            # layer I
            (None, 32000, 64000, 96000, 128000, 160000, 192000, 224000,
             256000, 288000, 320000, 352000, 384000, 416000, 448000, None)))

    PCM_FRAMES_PER_MPEG_FRAME = (None, 1152, 1152, 384)

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)

        from audiotools.bitstream import parse

        try:
            mp3file = open(filename, "rb")
        except IOError as msg:
            raise InvalidMP3(str(msg))

        try:
            try:
                header_bytes = MP3Audio.__find_next_mp3_frame__(mp3file)
            except IOError:
                from audiotools.text import ERR_MP3_FRAME_NOT_FOUND
                raise InvalidMP3(ERR_MP3_FRAME_NOT_FOUND)

            (frame_sync,
             mpeg_id,
             layer,
             bit_rate,
             sample_rate,
             pad,
             channels) = parse("11u 2u 2u 1p 4u 2u 1u 1p 2u 6p",
                               False,
                               mp3file.read(4))

            self.__samplerate__ = self.SAMPLE_RATE[mpeg_id][sample_rate]
            if (self.__samplerate__ is None):
                from audiotools.text import ERR_MP3_INVALID_SAMPLE_RATE
                raise InvalidMP3(ERR_MP3_INVALID_SAMPLE_RATE)
            if (channels in (0, 1, 2)):
                self.__channels__ = 2
            else:
                self.__channels__ = 1

            first_frame = mp3file.read(self.frame_length(mpeg_id,
                                                         layer,
                                                         bit_rate,
                                                         sample_rate,
                                                         pad) - 4)

            if ((b"Xing" in first_frame) and
                (len(first_frame[first_frame.index(b"Xing"):
                                 first_frame.index(b"Xing") + 160]) == 160)):
                # pull length from Xing header, if present
                self.__pcm_frames__ = (
                    parse("32p 32p 32u 32p 832p",
                          0,
                          first_frame[first_frame.index(b"Xing"):
                                      first_frame.index(b"Xing") + 160])[0] *
                    self.PCM_FRAMES_PER_MPEG_FRAME[layer])
            else:
                # otherwise, bounce through file frames
                from audiotools.bitstream import BitstreamReader

                reader = BitstreamReader(mp3file, False)
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
                except ValueError as err:
                    raise InvalidMP3(err)
        finally:
            mp3file.close()

    def lossless(self):
        """returns False"""

        return False

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from audiotools.decoders import MP3Decoder

        return MP3Decoder(self.filename)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new MP3Audio object"""

        from audiotools import (PCMConverter,
                                BufferedPCMReader,
                                ChannelMask,
                                __default_quality__,
                                EncodingError)
        from audiotools.encoders import encode_mp3

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        try:
            if (total_pcm_frames is not None):
                from audiotools import CounterPCMReader
                pcmreader = CounterPCMReader(pcmreader)

            encode_mp3(filename,
                       BufferedPCMReader(
                           PCMConverter(pcmreader,
                                        sample_rate=pcmreader.sample_rate,
                                        channels=min(pcmreader.channels, 2),
                                        channel_mask=ChannelMask.from_channels(
                                            min(pcmreader.channels, 2)),
                                        bits_per_sample=16)),
                       compression)

            if ((total_pcm_frames is not None) and
                (total_pcm_frames != pcmreader.frames_written)):
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                cls.__unlink__(filename)
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

            return MP3Audio(filename)
        except (ValueError, IOError) as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        finally:
            pcmreader.close()

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return 16

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__samplerate__

    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from audiotools.id3 import ID3CommentPair
        from audiotools.id3 import read_id3v2_comment
        from audiotools.id3v1 import ID3v1Comment

        with open(self.filename, "rb") as f:
            if (f.read(3) == b"ID3"):
                id3v2 = read_id3v2_comment(self.filename)

                try:
                    # yes IDv2, yes ID3v1
                    return ID3CommentPair(id3v2, ID3v1Comment.parse(f))
                except ValueError:
                    # yes ID3v2, no ID3v1
                    return id3v2
            else:
                try:
                    # no ID3v2, yes ID3v1
                    return ID3v1Comment.parse(f)
                except ValueError:
                    # no ID3v2, no ID3v1
                    return None

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        import os
        from audiotools import (TemporaryFile,
                                LimitedFileReader,
                                transfer_data)
        from audiotools.id3 import (ID3v2Comment, ID3CommentPair)
        from audiotools.id3v1 import ID3v1Comment
        from audiotools.bitstream import BitstreamWriter

        if (metadata is None):
            return
        elif (not (isinstance(metadata, ID3v2Comment) or
                   isinstance(metadata, ID3CommentPair) or
                   isinstance(metadata, ID3v1Comment))):
            from audiotools.text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)
        elif (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        new_mp3 = TemporaryFile(self.filename)

        # get the original MP3 data
        old_mp3 = open(self.filename, "rb")
        MP3Audio.__find_last_mp3_frame__(old_mp3)
        data_end = old_mp3.tell()
        old_mp3.seek(0, 0)
        MP3Audio.__find_mp3_start__(old_mp3)
        data_start = old_mp3.tell()
        old_mp3 = LimitedFileReader(old_mp3, data_end - data_start)

        # write id3v2 + data + id3v1 to file
        if (isinstance(metadata, ID3CommentPair)):
            metadata.id3v2.build(BitstreamWriter(new_mp3, False))
            transfer_data(old_mp3.read, new_mp3.write)
            metadata.id3v1.build(new_mp3)
        elif (isinstance(metadata, ID3v2Comment)):
            metadata.build(BitstreamWriter(new_mp3, False))
            transfer_data(old_mp3.read, new_mp3.write)
        elif (isinstance(metadata, ID3v1Comment)):
            transfer_data(old_mp3.read, new_mp3.write)
            metadata.build(new_mp3)

        # commit change to disk
        old_mp3.close()
        new_mp3.close()

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        from audiotools.id3 import ID3v2Comment
        from audiotools.id3 import ID3v22Comment
        from audiotools.id3 import ID3v23Comment
        from audiotools.id3 import ID3v24Comment
        from audiotools.id3 import ID3CommentPair
        from audiotools.id3v1 import ID3v1Comment

        if (metadata is None):
            return self.delete_metadata()

        if (not (isinstance(metadata, ID3v2Comment) or
                 isinstance(metadata, ID3CommentPair) or
                 isinstance(metadata, ID3v1Comment))):
            from audiotools import config

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
                                                                DEFAULT_ID3V1),
                                             DEFAULT_ID3V1)
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
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        import os
        from audiotools import (TemporaryFile,
                                LimitedFileReader,
                                transfer_data)

        # this works a lot like update_metadata
        # but without any new metadata to set

        if (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        new_mp3 = TemporaryFile(self.filename)

        # get the original MP3 data
        old_mp3 = open(self.filename, "rb")
        MP3Audio.__find_last_mp3_frame__(old_mp3)
        data_end = old_mp3.tell()
        old_mp3.seek(0, 0)
        MP3Audio.__find_mp3_start__(old_mp3)
        data_start = old_mp3.tell()
        old_mp3 = LimitedFileReader(old_mp3, data_end - data_start)

        # write data to file
        transfer_data(old_mp3.read, new_mp3.write)

        # commit change to disk
        old_mp3.close()
        new_mp3.close()

    def clean(self, output_filename=None):
        """cleans the file of known data and metadata problems

        output_filename is an optional filename of the fixed file
        if present, a new AudioFile is written to that path
        otherwise, only a dry-run is performed and no new file is written

        return list of fixes performed as Unicode strings

        raises IOError if unable to write the file or its metadata
        raises ValueError if the file has errors of some sort
        """

        from audiotools.id3 import total_id3v2_comments
        from audiotools import transfer_data
        from audiotools import open as open_audiofile
        from audiotools.text import CLEAN_REMOVE_DUPLICATE_ID3V2

        with open(self.filename, "rb") as f:
            if (total_id3v2_comments(f) > 1):
                file_fixes = [CLEAN_REMOVE_DUPLICATE_ID3V2]
            else:
                file_fixes = []

        if (output_filename is None):
            # dry run only
            metadata = self.get_metadata()
            if (metadata is not None):
                (metadata, fixes) = metadata.clean()
                return file_fixes + fixes
            else:
                return []
        else:
            # perform complete fix
            input_f = open(self.filename, "rb")
            output_f = open(output_filename, "wb")
            try:
                transfer_data(input_f.read, output_f.write)
            finally:
                input_f.close()
                output_f.close()

            new_track = open_audiofile(output_filename)
            metadata = self.get_metadata()
            if (metadata is not None):
                (metadata, fixes) = metadata.clean()
                if (len(file_fixes + fixes) > 0):
                    # only update metadata if fixes are actually performed
                    new_track.update_metadata(metadata)
                return file_fixes + fixes
            else:
                return []

    # places mp3file at the position of the next MP3 frame's start
    @classmethod
    def __find_next_mp3_frame__(cls, mp3file):
        from audiotools.id3 import skip_id3v2_comment

        # if we're starting at an ID3v2 header, skip it to save a bunch of time
        bytes_skipped = skip_id3v2_comment(mp3file)

        # then find the next mp3 frame
        from audiotools.bitstream import BitstreamReader

        reader = BitstreamReader(mp3file, False)
        pos = reader.getpos()
        try:
            (sync,
             mpeg_id,
             layer_description) = reader.parse("11u 2u 2u 1p")
        except IOError as err:
            raise err

        while (not ((sync == 0x7FF) and
                    (mpeg_id in (0, 2, 3)) and
                    (layer_description in (1, 2, 3)))):
            reader.setpos(pos)
            reader.skip(8)
            bytes_skipped += 1
            pos = reader.getpos()
            try:
                (sync,
                 mpeg_id,
                 layer_description) = reader.parse("11u 2u 2u 1p")
            except IOError as err:
                raise err
        else:
            reader.setpos(pos)
            return bytes_skipped

    @classmethod
    def __find_mp3_start__(cls, mp3file):
        """places mp3file at the position of the MP3 file's start"""

        from audiotools.id3 import skip_id3v2_comment

        # if we're starting at an ID3v2 header, skip it to save a bunch of time
        skip_id3v2_comment(mp3file)

        from audiotools.bitstream import BitstreamReader

        reader = BitstreamReader(mp3file, False)

        # skip over any bytes that aren't a valid MPEG header
        pos = reader.getpos()
        (frame_sync, mpeg_id, layer) = reader.parse("11u 2u 2u 1p")
        while (not ((frame_sync == 0x7FF) and
                    (mpeg_id in (0, 2, 3)) and
                    (layer in (1, 2, 3)))):
            reader.setpos(pos)
            reader.skip(8)
            pos = reader.getpos()
        reader.setpos(pos)

    @classmethod
    def __find_last_mp3_frame__(cls, mp3file):
        """places mp3file at the position of the last MP3 frame's end

        (either the last byte in the file or just before the ID3v1 tag)
        this may not be strictly accurate if ReplayGain data is present,
        since APEv2 tags came before the ID3v1 tag,
        but we're not planning to change that tag anyway
        """

        mp3file.seek(-128, 2)
        if (mp3file.read(3) == b'TAG'):
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
            from audiotools.text import ERR_MP3_INVALID_SAMPLE_RATE
            raise ValueError(ERR_MP3_INVALID_SAMPLE_RATE)
        bit_rate = self.BIT_RATE[mpeg_id][layer][bit_rate]
        if (bit_rate is None):
            from audiotools.text import ERR_MP3_INVALID_BIT_RATE
            raise ValueError(ERR_MP3_INVALID_BIT_RATE)
        if (layer == 3):  # layer I
            return (((12 * bit_rate) // sample_rate) + pad) * 4
        else:             # layer II/III
            return ((144 * bit_rate) // sample_rate) + pad

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__pcm_frames__

    @classmethod
    def available(cls, system_binaries):
        """returns True if all necessary compenents are available
        to support format"""

        try:
            from audiotools.decoders import MP3Decoder
            from audiotools.encoders import encode_mp3

            return True
        except ImportError:
            return False

    @classmethod
    def missing_components(cls, messenger):
        """given a Messenger object, displays missing binaries or libraries
        needed to support this format and where to get them"""

        from audiotools.text import (ERR_LIBRARY_NEEDED,
                                     ERR_LIBRARY_DOWNLOAD_URL,
                                     ERR_PROGRAM_PACKAGE_MANAGER)

        format_ = cls.NAME.decode('ascii')

        # display where to get libmp3lame
        messenger.info(
            ERR_LIBRARY_NEEDED %
            {"library": u"\"libmp3lame\"",
             "format": format_})
        messenger.info(
            ERR_LIBRARY_DOWNLOAD_URL %
            {"library": u"mp3lame",
             "url": "http://lame.sourceforge.net/"})

        # then display where to get libmpg123
        messenger.info(
            ERR_LIBRARY_NEEDED %
            {"library": u"\"libmpg123\"",
             "format": format_})
        messenger.info(
            ERR_LIBRARY_DOWNLOAD_URL %
            {"library": u"mpg123",
             "url": u"http://www.mpg123.org/"})

        messenger.info(ERR_PROGRAM_PACKAGE_MANAGER)


class MP2Audio(MP3Audio):
    """an MP2 audio file"""

    from audiotools.text import (COMP_TWOLAME_64,
                                 COMP_TWOLAME_384)

    SUFFIX = "mp2"
    NAME = SUFFIX
    DESCRIPTION = u"MPEG-1 Audio Layer II"
    DEFAULT_COMPRESSION = str(192)
    COMPRESSION_MODES = tuple(map(str, (64,  96,  112, 128, 160, 192,
                                        224, 256, 320, 384)))
    COMPRESSION_DESCRIPTIONS = {"64": COMP_TWOLAME_64,
                                "384": COMP_TWOLAME_384}

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new MP2Audio object"""

        from audiotools import (PCMConverter,
                                BufferedPCMReader,
                                ChannelMask,
                                __default_quality__,
                                EncodingError)
        from audiotools.encoders import encode_mp2
        import bisect

        if (((compression is None) or
             (compression not in cls.COMPRESSION_MODES))):
            compression = __default_quality__(cls.NAME)

        if (pcmreader.sample_rate in (32000, 48000, 44100)):
            sample_rate = pcmreader.sample_rate
        else:
            sample_rate = [32000,
                           32000,
                           44100,
                           48000][bisect.bisect([32000,
                                                 44100,
                                                 48000],
                                                pcmreader.sample_rate)]

        if (total_pcm_frames is not None):
            from audiotools import CounterPCMReader
            pcmreader = CounterPCMReader(pcmreader)

        try:
            encode_mp2(filename,
                       BufferedPCMReader(
                           PCMConverter(pcmreader,
                                        sample_rate=sample_rate,
                                        channels=min(pcmreader.channels, 2),
                                        channel_mask=ChannelMask.from_channels(
                                            min(pcmreader.channels, 2)),
                                        bits_per_sample=16)),
                       int(compression))

            if ((total_pcm_frames is not None) and
                (total_pcm_frames != pcmreader.frames_written)):
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                cls.__unlink__(filename)
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

            return MP2Audio(filename)
        except (ValueError, IOError) as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        finally:
            pcmreader.close()

    @classmethod
    def available(cls, system_binaries):
        """returns True if all necessary compenents are available
        to support format"""

        try:
            from audiotools.decoders import MP3Decoder
            from audiotools.encoders import encode_mp2

            return True
        except ImportError:
            return False

    @classmethod
    def missing_components(cls, messenger):
        """given a Messenger object, displays missing binaries or libraries
        needed to support this format and where to get them"""

        from audiotools.text import (ERR_LIBRARY_NEEDED,
                                     ERR_LIBRARY_DOWNLOAD_URL,
                                     ERR_PROGRAM_PACKAGE_MANAGER)

        format_ = cls.NAME.decode('ascii')

        # display where to get libtwo,ame
        messenger.info(
            ERR_LIBRARY_NEEDED %
            {"library": u"\"libtwolame\"",
             "format": format_})
        messenger.info(
            ERR_LIBRARY_DOWNLOAD_URL %
            {"library": u"twolame",
             "url": "http://twolame.sourceforge.net/"})

        # then display where to get libmpg123
        messenger.info(
            ERR_LIBRARY_NEEDED %
            {"library": u"\"libmpg123\"",
             "format": format_})
        messenger.info(
            ERR_LIBRARY_DOWNLOAD_URL %
            {"library": u"mpg123",
             "url": u"http://www.mpg123.org/"})

        messenger.info(ERR_PROGRAM_PACKAGE_MANAGER)
