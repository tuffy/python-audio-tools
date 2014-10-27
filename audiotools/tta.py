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
from audiotools.ape import ApeGainedAudio


def div_ceil(n, d):
    """returns the ceiling of n divided by d as an int"""

    return n // d + (1 if ((n % d) != 0) else 0)


class InvalidTTA(InvalidFile):
    pass


class TrueAudio(AudioFile, ApeGainedAudio):
    """a True Audio file"""

    SUFFIX = "tta"
    NAME = SUFFIX
    DESCRIPTION = u"True Audio"

    def __init__(self, filename):
        from audiotools.id3 import skip_id3v2_comment

        AudioFile.__init__(self, filename)

        try:
            with open(filename, "rb") as f:
                skip_id3v2_comment(f)

                from audiotools.bitstream import BitstreamReader
                from audiotools.text import (ERR_TTA_INVALID_SIGNATURE,
                                             ERR_TTA_INVALID_FORMAT)

                reader = BitstreamReader(f, True)

                (signature,
                 format_,
                 self.__channels__,
                 self.__bits_per_sample__,
                 self.__sample_rate__,
                 self.__total_pcm_frames__) = reader.parse(
                    "4b 16u 16u 16u 32u 32u 32p")

                if (signature != b"TTA1"):
                    raise InvalidTTA(ERR_TTA_INVALID_SIGNATURE)
                elif (format_ != 1):
                    raise InvalidTTA(ERR_TTA_INVALID_FORMAT)

                self.__total_tta_frames__ = div_ceil(
                    self.__total_pcm_frames__ * 245,
                    self.__sample_rate__ * 256)
                self.__frame_lengths__ = list(reader.parse(
                    "%d* 32u" % (self.__total_tta_frames__) + "32p"))
        except IOError as msg:
            raise InvalidTTA(str(msg))

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        from audiotools import ChannelMask

        if (self.__channels__ == 1):
            return ChannelMask(0x4)
        elif (self.__channels__ == 2):
            return ChannelMask(0x3)
        else:
            return ChannelMask(0)

    def lossless(self):
        """returns True if this track's data is stored losslessly"""

        return True

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__total_pcm_frames__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def seekable(self):
        """returns True if the file is seekable"""

        return True

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        from audiotools import decoders
        from audiotools import PCMReaderError
        from audiotools.id3 import skip_id3v2_comment

        try:
            tta = open(self.filename, "rb")
        except IOError as msg:
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())
        try:
            skip_id3v2_comment(tta)
            return decoders.TTADecoder(tta)
        except (IOError, ValueError) as msg:
            # This isn't likely unless the TTA file is modified
            # between when TrueAudio is instantiated
            # and to_pcm() is called.
            tta.close()
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None,
                 total_pcm_frames=None,
                 encoding_function=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AudioFile-compatible object

        may raise EncodingError if some problem occurs when
        encoding the input file.  This includes an error
        in the input stream, a problem writing the output file,
        or even an EncodingError subclass such as
        "UnsupportedBitsPerSample" if the input stream
        is formatted in a way this class is unable to support
        """

        from audiotools import (BufferedPCMReader,
                                CounterPCMReader,
                                transfer_data,
                                EncodingError)
        # from audiotools.py_encoders import encode_tta
        from audiotools.encoders import encode_tta
        from audiotools.bitstream import BitstreamWriter

        # open output file right away
        # so we can fail as soon as possible
        try:
            file = open(filename, "wb")
        except IOError as err:
            pcmreader.close()
            raise EncodingError(str(err))

        writer = BitstreamWriter(file, True)
        counter = CounterPCMReader(pcmreader)
        try:
            if (total_pcm_frames is not None):
                # write header to disk
                write_header(writer,
                             pcmreader.channels,
                             pcmreader.bits_per_sample,
                             pcmreader.sample_rate,
                             total_pcm_frames)

                block_size = (pcmreader.sample_rate * 256) // 245
                total_tta_frames = div_ceil(total_pcm_frames, block_size)

                # write temporary seektable to disk
                seektable_start = writer.getpos()
                write_seektable(writer, [0] * total_tta_frames)
                writer.flush()

                # write frames to disk
                try:
                    frame_sizes = \
                        (encode_tta if encoding_function is None
                         else encoding_function)(file,
                                                 BufferedPCMReader(counter))
                except (IOError, ValueError) as err:
                    cls.__unlink__(filename)
                    raise EncodingError(str(err))

                # ensure written number of PCM frames
                # matches total_pcm_frames
                if (counter.frames_written != total_pcm_frames):
                    from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                    cls.__unlink__(filename)
                    raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

                assert(len(frame_sizes) == total_tta_frames)

                # go back and rewrite seektable with completed one
                writer.setpos(seektable_start)
                write_seektable(writer, frame_sizes)
            else:
                import tempfile

                frames = tempfile.TemporaryFile()

                # encode TTA frames to temporary file
                try:
                    frame_sizes = \
                        (encode_tta if encoding_function is None
                         else encoding_function)(frames,
                                                 BufferedPCMReader(counter))
                except (IOError, ValueError) as err:
                    frames.close()
                    cls.__unlink__(filename)
                    raise EncodingError(str(err))

                # write header to disk
                write_header(writer,
                             pcmreader.channels,
                             pcmreader.bits_per_sample,
                             pcmreader.sample_rate,
                             counter.frames_written)

                # write seektable to disk
                write_seektable(writer, frame_sizes)

                # transfer TTA frames from temporary space to disk
                frames.seek(0, 0)
                transfer_data(frames.read, writer.write_bytes)
                frames.close()
        finally:
            counter.close()
            writer.close()

        return cls(filename)

    def data_size(self):
        """returns the size of the file's data, in bytes,
        calculated from its header and seektable"""

        return (22 +                                     # header size
                (len(self.__frame_lengths__) * 4) + 4 +  # seektable size
                sum(self.__frame_lengths__))             # frames size

    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        with open(self.filename, "rb") as f:
            # first, attempt to find APEv2 comment at end of file
            f.seek(-32, 2)
            if (f.read(10) == b"APETAGEX\xd0\x07"):
                from audiotools import ApeTag

                return ApeTag.read(f)
            else:
                # then, look for ID3v2 comment at beginning of file
                f.seek(0, 0)
                if (f.read(3) == b"ID3"):
                    from audiotools.id3 import read_id3v2_comment
                    try:
                        id3v2 = read_id3v2_comment(self.filename)
                    except ValueError:
                        id3v2 = None
                else:
                    id3v2 = None

                # and look for ID3v1 comment at end of file
                try:
                    f.seek(-128, 2)
                    if (f.read(3) == b"TAG"):
                        from audiotools.id3v1 import ID3v1Comment
                        try:
                            id3v1 = ID3v1Comment.parse(f)
                        except ValueError:
                            id3v1 = None
                    else:
                        id3v1 = None
                except IOError:
                    id3v1 = None

                # if both ID3v2 and ID3v1 are present, return a pair
                if ((id3v2 is not None) and (id3v1 is not None)):
                    from audiotools.id3 import ID3CommentPair
                    return ID3CommentPair(id3v2, id3v1)
                elif (id3v2 is not None):
                    return id3v2
                else:
                    return id3v1

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        import os
        from audiotools.ape import ApeTag
        from audiotools.bitstream import BitstreamWriter

        if (metadata is None):
            return
        else:
            new_metadata = ApeTag.converted(metadata)

        if (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        # if current metadata is present and in a particular format
        # set_metadata() should continue using that format
        old_metadata = ApeTag.converted(self.get_metadata())
        if (old_metadata is not None):
            # transfer ReplayGain tags from old metadata to new metadata
            for tag in [b"replaygain_track_gain",
                        b"replaygain_track_peak",
                        b"replaygain_album_gain",
                        b"replaygain_album_peak"]:
                try:
                    # if old_metadata has tag, shift it over
                    new_metadata[tag] = old_metadata[tag]
                except KeyError:
                    try:
                        # otherwise, if new_metadata has tag, delete it
                        del(new_metadata[tag])
                    except KeyError:
                        # if neither has tag, ignore it
                        continue

            # transfer Cuesheet from old metadata to new metadata
            if (b"Cuesheet" in old_metadata):
                new_metadata[b"Cuesheet"] = old_metadata[b"Cuesheet"]
            elif (b"Cuesheet" in new_metadata):
                del(new_metadata[b"Cuesheet"])

            self.update_metadata(new_metadata)
        else:
            # delete ReplayGain tags from new metadata
            for tag in [b"replaygain_track_gain",
                        b"replaygain_track_peak",
                        b"replaygain_album_gain",
                        b"replaygain_album_peak"]:
                try:
                    del(new_metadata[tag])
                except KeyError:
                    continue

            # delete Cuesheet from new metadata
            if (b"Cuesheet" in new_metadata):
                del(new_metadata[b"Cuesheet"])

            # no current metadata, so append a fresh APEv2 tag
            with BitstreamWriter(open(self.filename, "ab"), True) as writer:
                new_metadata.build(writer)

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        import os
        from audiotools.ape import ApeTag
        from audiotools.id3 import ID3v2Comment
        from audiotools.id3 import ID3CommentPair
        from audiotools.id3v1 import ID3v1Comment

        if (metadata is None):
            return
        elif (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        # ensure metadata is APEv2, ID3v2, ID3v1, or ID3CommentPair
        if (((not isinstance(metadata, ApeTag)) and
             (not isinstance(metadata, ID3v2Comment)) and
             (not isinstance(metadata, ID3CommentPair)) and
             (not isinstance(metadata, ID3v1Comment)))):
            from audiotools.text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        current_metadata = self.get_metadata()

        if (isinstance(metadata, ApeTag) and (current_metadata is None)):
            # if new metadata is APEv2 and no current metadata,
            # simply append APEv2 tag
            from audiotools.bitstream import BitstreamWriter
            with BitstreamWriter(open(self.filename, "ab"), True) as writer:
                metadata.build(writer)
        elif (isinstance(metadata, ApeTag) and
              isinstance(current_metadata, ApeTag) and
              (metadata.total_size() > current_metadata.total_size())):
            # if new metadata is APEv2, current metadata is APEv2
            # and new metadata is larger,
            # overwrite old tag with new tag
            from audiotools.bitstream import BitstreamWriter
            with open(self.filename, "r+b") as f:
                f.seek(-current_metadata.total_size(), 2)
                metadata.build(BitstreamWriter(f, True))
        else:
            from audiotools.bitstream import BitstreamWriter
            from audiotools import (transfer_data,
                                    LimitedFileReader,
                                    TemporaryFile)
            from audiotools.id3 import skip_id3v2_comment

            # otherwise, rebuild TTA with APEv2/ID3 tags in place
            old_tta = open(self.filename, "rb")
            skip_id3v2_comment(old_tta)
            old_tta = LimitedFileReader(old_tta, self.data_size())

            new_tta = TemporaryFile(self.filename)

            if (isinstance(metadata, ApeTag)):
                transfer_data(old_tta.read, new_tta.write)
                metadata.build(BitstreamWriter(new_tta, True))
            elif (isinstance(metadata, ID3CommentPair)):
                metadata.id3v2.build(BitstreamWriter(new_tta, False))
                transfer_data(old_tta.read, new_tta.write)
                metadata.id3v1.build(new_tta)
            elif (isinstance(metadata, ID3v2Comment)):
                metadata.build(BitstreamWriter(new_tta, False))
                transfer_data(old_tta.read, new_tta.write)
            else:
                # ID3v1Comment
                transfer_data(old_tta.read, new_tta.write)
                metadata.build(new_tta)

            old_tta.close()
            new_tta.close()

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        import os
        from audiotools import (transfer_data,
                                LimitedFileReader,
                                TemporaryFile)
        from audiotools.id3 import skip_id3v2_comment

        if (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        # overwrite original with no tags attached
        old_tta = open(self.filename, "rb")
        skip_id3v2_comment(old_tta)
        old_tta = LimitedFileReader(old_tta, self.data_size())

        new_tta = TemporaryFile(self.filename)
        transfer_data(old_tta.read, new_tta.write)

        old_tta.close()
        new_tta.close()

    @classmethod
    def supports_cuesheet(cls):
        return True

    def get_cuesheet(self):
        """returns the embedded Cuesheet-compatible object, or None

        raises IOError if a problem occurs when reading the file"""

        import audiotools.cue as cue
        from audiotools import SheetException

        metadata = self.get_metadata()

        if ((metadata is not None) and (b'Cuesheet' in metadata.keys())):
            try:
                return cue.read_cuesheet_string(
                    metadata[b'Cuesheet'].__unicode__())
            except SheetException:
                # unlike FLAC, just because a cuesheet is embedded
                # does not mean it is compliant
                return None
        else:
            return None

    def set_cuesheet(self, cuesheet):
        """imports cuesheet data from a Sheet object

        Raises IOError if an error occurs setting the cuesheet"""

        import os.path
        from io import BytesIO
        from audiotools import (MetaData, Filename, FS_ENCODING)
        from audiotools.ape import ApeTag
        from audiotools.cue import write_cuesheet

        if (cuesheet is None):
            return self.delete_cuesheet()

        metadata = self.get_metadata()
        if (metadata is None):
            metadata = ApeTag([])
        else:
            metadata = ApeTag.converted(metadata)

        cuesheet_data = BytesIO()
        write_cuesheet(cuesheet,
                       u"%s" % (Filename(self.filename).basename(),),
                       cuesheet_data)

        metadata[b'Cuesheet'] = ApeTag.ITEM.string(
            b'Cuesheet',
            cuesheet_data.getvalue().decode(FS_ENCODING, 'replace'))

        self.update_metadata(metadata)

    def delete_cuesheet(self):
        """deletes embedded Sheet object, if any

        Raises IOError if a problem occurs when updating the file"""

        from audiotools import ApeTag

        metadata = self.get_metadata()
        if ((metadata is not None) and
            (isinstance(metadata, ApeTag) and
             (b"Cuesheet" in metadata))):
            del(metadata[b"Cuesheet"])
            self.update_metadata(metadata)

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return True

    def get_replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values"""

        from audiotools.ape import ApeTag

        # if current metadata is present and is in APEv2 format,
        # return contents of "replaygain_" tags
        metadata = self.get_metadata()
        if ((metadata is not None) and isinstance(metadata, ApeTag)):
            return ApeGainedAudio.get_replay_gain(self)
        else:
            # otherwise, return None
            return None

    def set_replay_gain(self, replaygain):
        """given a ReplayGain object, sets the track's gain to those values

        may raise IOError if unable to read or write the file"""

        if (replaygain is None):
            return self.delete_replay_gain()

        from audiotools.ape import ApeTag

        metadata = self.get_metadata()
        if ((metadata is None) or (isinstance(metadata, ApeTag))):
            ApeGainedAudio.set_replay_gain(self, replaygain)
        else:
            metadata = ApeTag.converted(metadata)
            self.update_metadata(metadata)
            ApeGainedAudio.set_replay_gain(self, replaygain)

    def delete_replay_gain(self):
        """removes ReplayGain values from file, if any

        may raise IOError if unable to modify the file"""

        from audiotools.ape import ApeTag

        metadata = self.get_metadata()
        if ((metadata is not None) and (isinstance(metadata, ApeTag))):
            ApeGainedAudio.delete_replay_gain(self)

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
        from audiotools import open as open_audiofile
        from audiotools import transfer_data
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
                return file_fixes
        else:
            # perform full fix
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
                return file_fixes


def write_header(writer,
                 channels,
                 bits_per_sample,
                 sample_rate,
                 total_pcm_frames):
    """writes a TTA header to the given BitstreamWriter
    with the given int attributes"""

    crc = CRC32()
    writer.add_callback(crc.update)
    writer.build("4b 16u 16u 16u 32u 32u",
                 [b"TTA1",
                  1,
                  channels,
                  bits_per_sample,
                  sample_rate,
                  total_pcm_frames])
    writer.pop_callback()
    writer.write(32, int(crc))


def write_seektable(writer, frame_sizes):
    """writes a TTA header to the given BitstreamWriter
    where frame_sizes is a list of frame sizes, in bytes"""

    crc = CRC32()
    writer.add_callback(crc.update)
    writer.build("%d* 32U" % (len(frame_sizes)), frame_sizes)
    writer.pop_callback()
    writer.write(32, int(crc))


class CRC32(object):
    TABLE = [0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA,
             0x076DC419, 0x706AF48F, 0xE963A535, 0x9E6495A3,
             0x0EDB8832, 0x79DCB8A4, 0xE0D5E91E, 0x97D2D988,
             0x09B64C2B, 0x7EB17CBD, 0xE7B82D07, 0x90BF1D91,
             0x1DB71064, 0x6AB020F2, 0xF3B97148, 0x84BE41DE,
             0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
             0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC,
             0x14015C4F, 0x63066CD9, 0xFA0F3D63, 0x8D080DF5,
             0x3B6E20C8, 0x4C69105E, 0xD56041E4, 0xA2677172,
             0x3C03E4D1, 0x4B04D447, 0xD20D85FD, 0xA50AB56B,
             0x35B5A8FA, 0x42B2986C, 0xDBBBC9D6, 0xACBCF940,
             0x32D86CE3, 0x45DF5C75, 0xDCD60DCF, 0xABD13D59,
             0x26D930AC, 0x51DE003A, 0xC8D75180, 0xBFD06116,
             0x21B4F4B5, 0x56B3C423, 0xCFBA9599, 0xB8BDA50F,
             0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924,
             0x2F6F7C87, 0x58684C11, 0xC1611DAB, 0xB6662D3D,
             0x76DC4190, 0x01DB7106, 0x98D220BC, 0xEFD5102A,
             0x71B18589, 0x06B6B51F, 0x9FBFE4A5, 0xE8B8D433,
             0x7807C9A2, 0x0F00F934, 0x9609A88E, 0xE10E9818,
             0x7F6A0DBB, 0x086D3D2D, 0x91646C97, 0xE6635C01,
             0x6B6B51F4, 0x1C6C6162, 0x856530D8, 0xF262004E,
             0x6C0695ED, 0x1B01A57B, 0x8208F4C1, 0xF50FC457,
             0x65B0D9C6, 0x12B7E950, 0x8BBEB8EA, 0xFCB9887C,
             0x62DD1DDF, 0x15DA2D49, 0x8CD37CF3, 0xFBD44C65,
             0x4DB26158, 0x3AB551CE, 0xA3BC0074, 0xD4BB30E2,
             0x4ADFA541, 0x3DD895D7, 0xA4D1C46D, 0xD3D6F4FB,
             0x4369E96A, 0x346ED9FC, 0xAD678846, 0xDA60B8D0,
             0x44042D73, 0x33031DE5, 0xAA0A4C5F, 0xDD0D7CC9,
             0x5005713C, 0x270241AA, 0xBE0B1010, 0xC90C2086,
             0x5768B525, 0x206F85B3, 0xB966D409, 0xCE61E49F,
             0x5EDEF90E, 0x29D9C998, 0xB0D09822, 0xC7D7A8B4,
             0x59B33D17, 0x2EB40D81, 0xB7BD5C3B, 0xC0BA6CAD,
             0xEDB88320, 0x9ABFB3B6, 0x03B6E20C, 0x74B1D29A,
             0xEAD54739, 0x9DD277AF, 0x04DB2615, 0x73DC1683,
             0xE3630B12, 0x94643B84, 0x0D6D6A3E, 0x7A6A5AA8,
             0xE40ECF0B, 0x9309FF9D, 0x0A00AE27, 0x7D079EB1,
             0xF00F9344, 0x8708A3D2, 0x1E01F268, 0x6906C2FE,
             0xF762575D, 0x806567CB, 0x196C3671, 0x6E6B06E7,
             0xFED41B76, 0x89D32BE0, 0x10DA7A5A, 0x67DD4ACC,
             0xF9B9DF6F, 0x8EBEEFF9, 0x17B7BE43, 0x60B08ED5,
             0xD6D6A3E8, 0xA1D1937E, 0x38D8C2C4, 0x4FDFF252,
             0xD1BB67F1, 0xA6BC5767, 0x3FB506DD, 0x48B2364B,
             0xD80D2BDA, 0xAF0A1B4C, 0x36034AF6, 0x41047A60,
             0xDF60EFC3, 0xA867DF55, 0x316E8EEF, 0x4669BE79,
             0xCB61B38C, 0xBC66831A, 0x256FD2A0, 0x5268E236,
             0xCC0C7795, 0xBB0B4703, 0x220216B9, 0x5505262F,
             0xC5BA3BBE, 0xB2BD0B28, 0x2BB45A92, 0x5CB36A04,
             0xC2D7FFA7, 0xB5D0CF31, 0x2CD99E8B, 0x5BDEAE1D,
             0x9B64C2B0, 0xEC63F226, 0x756AA39C, 0x026D930A,
             0x9C0906A9, 0xEB0E363F, 0x72076785, 0x05005713,
             0x95BF4A82, 0xE2B87A14, 0x7BB12BAE, 0x0CB61B38,
             0x92D28E9B, 0xE5D5BE0D, 0x7CDCEFB7, 0x0BDBDF21,
             0x86D3D2D4, 0xF1D4E242, 0x68DDB3F8, 0x1FDA836E,
             0x81BE16CD, 0xF6B9265B, 0x6FB077E1, 0x18B74777,
             0x88085AE6, 0xFF0F6A70, 0x66063BCA, 0x11010B5C,
             0x8F659EFF, 0xF862AE69, 0x616BFFD3, 0x166CCF45,
             0xA00AE278, 0xD70DD2EE, 0x4E048354, 0x3903B3C2,
             0xA7672661, 0xD06016F7, 0x4969474D, 0x3E6E77DB,
             0xAED16A4A, 0xD9D65ADC, 0x40DF0B66, 0x37D83BF0,
             0xA9BCAE53, 0xDEBB9EC5, 0x47B2CF7F, 0x30B5FFE9,
             0xBDBDF21C, 0xCABAC28A, 0x53B39330, 0x24B4A3A6,
             0xBAD03605, 0xCDD70693, 0x54DE5729, 0x23D967BF,
             0xB3667A2E, 0xC4614AB8, 0x5D681B02, 0x2A6F2B94,
             0xB40BBE37, 0xC30C8EA1, 0x5A05DF1B, 0x2D02EF8D]

    def __init__(self):
        self.crc = 0xffffffff

    def update(self, byte):
        self.crc = self.TABLE[(self.crc ^ byte) & 0xFF] ^ (self.crc >> 8)

    def __int__(self):
        return self.crc ^ 0xFFFFFFFF
