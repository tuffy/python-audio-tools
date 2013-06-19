#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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


from . import (AudioFile, InvalidFile)


#######################
#True Audio
#######################


def div_ceil(n, d):
    """returns the ceiling of n divided by d as an int"""

    return n // d + (1 if ((n % d) != 0) else 0)


class InvalidTTA(InvalidFile):
    pass


class TrueAudio(AudioFile):
    """a True Audio file"""

    SUFFIX = "tta"
    NAME = SUFFIX
    DESCRIPTION = u"True Audio"

    def __init__(self, filename):
        from .id3 import skip_id3v2_comment

        self.filename = filename

        try:
            f = open(filename, "rb")
            self.__stream_offset__ = skip_id3v2_comment(f)

            from .bitstream import BitstreamReader
            from .text import (ERR_TTA_INVALID_SIGNATURE,
                               ERR_TTA_INVALID_FORMAT)

            reader = BitstreamReader(f, True)

            (signature,
             format_,
             self.__channels__,
             self.__bits_per_sample__,
             self.__sample_rate__,
             self.__total_pcm_frames__) = reader.parse(
                 "4b 16u 16u 16u 32u 32u 32p")

            if (signature != "TTA1"):
                raise InvalidTTA(ERR_TTA_INVALID_SIGNATURE)
            elif (format_ != 1):
                raise InvalidTTA(ERR_TTA_INVALID_FORMAT)

            self.__total_tta_frames__ = div_ceil(
                self.__total_pcm_frames__ * 245,
                self.__sample_rate__ * 256)
            self.__frame_lengths__ = list(reader.parse(
                "%d* 32u" % (self.__total_tta_frames__) + "32p"))
        except IOError, msg:
            raise InvalidTTA(str(msg))

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        from . import ChannelMask

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

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data

        if an error occurs initializing a decoder, this should
        return a PCMReaderError with an appropriate error message"""

        from . import decoders
        from . import PCMReaderError

        try:
            return decoders.TTADecoder(self.filename,
                                       self.__stream_offset__)
        except (IOError, ValueError), msg:
            #This isn't likely unless the TTA file is modified
            #between when TrueAudio is instantiated
            #and to_pcm() is called.
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

        from . import (BufferedPCMReader,
                       CounterPCMReader,
                       transfer_data,
                       EncodingError)
        # from audiotools.py_encoders import encode_tta
        from .encoders import encode_tta
        from .bitstream import BitstreamWriter
        import tempfile

        #open output file right away
        #so we can fail as soon as possible
        try:
            file = open(filename, "wb")
            writer = BitstreamWriter(file, True)
        except IOError, err:
            raise EncodingError(str(err))

        counter = CounterPCMReader(pcmreader)
        if (total_pcm_frames is not None):
            #write header to disk
            write_header(writer,
                         pcmreader.channels,
                         pcmreader.bits_per_sample,
                         pcmreader.sample_rate,
                         total_pcm_frames)

            total_tta_frames = div_ceil(total_pcm_frames * 245,
                                        pcmreader.sample_rate * 256)

            #write temporary seektable to disk
            write_seektable(writer, [0] * total_tta_frames)

            #write frames to disk
            try:
                frame_sizes = \
                    (encode_tta if encoding_function is None
                     else encoding_function)(file, BufferedPCMReader(counter))
            except (IOError, ValueError), err:
                file.close()
                cls.__unlink__(filename)
                raise EncodingError(str(err))

            #ensure written number of PCM frames
            #matches total_pcm_frames
            if (counter.frames_written != total_pcm_frames):
                from .text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                cls.__unlink__(filename)
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

            assert(len(frame_sizes) == total_tta_frames)

            #go back and rewrite seektable with completed one
            file.seek(0x16, 0)
            write_seektable(writer, frame_sizes)
        else:
            frames = tempfile.TemporaryFile()

            #encode TTA frames to temporary file
            try:
                frame_sizes = \
                    (encode_tta if encoding_function is None
                     else encoding_function)(frames,
                                             BufferedPCMReader(counter))
            except (IOError, ValueError), err:
                frames.close()
                file.close()
                cls.__unlink__(filename)
                raise EncodingError(str(err))

            assert(len(frame_sizes) == div_ceil(counter.frames_written * 245,
                                                pcmreader.sample_rate * 256))

            #write header to disk
            write_header(writer,
                         pcmreader.channels,
                         pcmreader.bits_per_sample,
                         pcmreader.sample_rate,
                         counter.frames_written)

            #write seektable to disk
            write_seektable(writer, frame_sizes)

            #transfer TTA frames from temporary space to disk
            frames.seek(0, 0)
            transfer_data(frames.read, file.write)
            frames.close()

        file.close()

        return cls(filename)

    def data_size(self):
        """returns the size of the file's data, in bytes,
        calculated from its header and seektable"""

        return (22 +                                     # header size
                (len(self.__frame_lengths__) * 4) + 4 +  # seektable size
                sum(self.__frame_lengths__))             # frames size

    @classmethod
    def can_add_replay_gain(cls, audiofiles):
        """given a list of audiofiles,
        returns True if this class can add ReplayGain to those files
        returns False if not"""

        for audiofile in audiofiles:
            if (not isinstance(audiofile, TrueAudio)):
                return False
        else:
            return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        f = open(self.filename, "rb")

        #first, attempt to find APEv2 comment at end of file
        f.seek(-32, 2)
        if (f.read(10) == "APETAGEX\xd0\x07"):
            from . import ApeTag

            return ApeTag.read(f)
        else:
            #then, look for ID3v2 comment at beginning of file
            f.seek(0, 0)
            if (f.read(3) == "ID3"):
                from .id3 import read_id3v2_comment
                try:
                    id3v2 = read_id3v2_comment(self.filename)
                except ValueError:
                    id3v2 = None
            else:
                id3v2 = None

            #and look for ID3v1 comment at end of file
            try:
                f.seek(-128, 2)
                if (f.read(3) == "TAG"):
                    from .id3v1 import ID3v1Comment
                    try:
                        id3v1 = ID3v1Comment.parse(f)
                    except ValueError:
                        id3v1 = None
                else:
                    id3v1 = None
            except IOError:
                id3v1 = None

            #if both ID3v2 and ID3v1 are present, return a pair
            if ((id3v2 is not None) and (id3v1 is not None)):
                from .id3 import ID3CommentPair
                return ID3CommentPair(id3v2, id3v1)
            elif (id3v2 is not None):
                return id3v2
            else:
                return id3v1

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        from .ape import ApeTag
        from .bitstream import BitstreamWriter

        if (metadata is None):
            return
        else:
            new_metadata = ApeTag.converted(metadata)

        #if current metadata is present and in a particular format
        #set_metadata() should continue using that format
        old_metadata = ApeTag.converted(self.get_metadata())
        if (old_metadata is not None):
            #transfer ReplayGain tags from old metadata to new metadata
            for tag in ["replaygain_track_gain",
                        "replaygain_track_peak",
                        "replaygain_album_gain",
                        "replaygain_album_peak"]:
                try:
                    #if old_metadata has tag, shift it over
                    new_metadata[tag] = old_metadata[tag]
                except KeyError:
                    try:
                        #otherwise, if new_metadata has tag, delete it
                        del(new_metadata[tag])
                    except KeyError:
                        #if neither has tag, ignore it
                        continue

            #transfer Cuesheet from old metadata to new metadata
            if ("Cuesheet" in old_metadata):
                new_metadata["Cuesheet"] = old_metadata["Cuesheet"]
            elif ("Cuesheet" in new_metadata):
                del(new_metadata["Cuesheet"])

            self.update_metadata(new_metadata)
        else:
            #delete ReplayGain tags from new metadata
            for tag in ["replaygain_track_gain",
                        "replaygain_track_peak",
                        "replaygain_album_gain",
                        "replaygain_album_peak"]:
                try:
                    del(new_metadata[tag])
                except KeyError:
                    continue

            #delete Cuesheet from new metadata
            if ("Cuesheet" in new_metadata):
                del(new_metadata["Cuesheet"])

            #no current metadata, so append a fresh APEv2 tag
            f = file(self.filename, "ab")
            new_metadata.build(BitstreamWriter(f, 1))
            f.close()

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        if (metadata is None):
            return

        from .ape import ApeTag
        from .id3 import ID3v2Comment
        from .id3 import ID3CommentPair
        from .id3v1 import ID3v1Comment

        #ensure metadata is APEv2, ID3v2, ID3v1, or ID3CommentPair
        if (((not isinstance(metadata, ApeTag)) and
             (not isinstance(metadata, ID3v2Comment)) and
             (not isinstance(metadata, ID3CommentPair)) and
             (not isinstance(metadata, ID3v1Comment)))):
            from .text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        current_metadata = self.get_metadata()

        if (isinstance(metadata, ApeTag) and (current_metadata is None)):
            #if new metadata is APEv2 and no current metadata,
            #simply append APEv2 tag
            from .bitstream import BitstreamWriter
            f = open(self.filename, "ab")
            metadata.build(BitstreamWriter(f, True))
        elif (isinstance(metadata, ApeTag) and
              isinstance(current_metadata, ApeTag) and
              (metadata.total_size() > current_metadata.total_size())):
            #if new metadata is APEv2, current metadata is APEv2
            #and new metadata is larger,
            #overwrite old tag with new tag
            from .bitstream import BitstreamWriter
            f = open(self.filename, "r+b")
            f.seek(-current_metadata.total_size(), 2)
            metadata.build(BitstreamWriter(f, True))
        else:
            from tempfile import TemporaryFile
            from . import (transfer_data, LimitedFileReader)
            from .id3 import skip_id3v2_comment

            #otherwise, shift TTA file data to temporary space
            temp_tta_data = TemporaryFile()
            f = open(self.filename, "rb")
            skip_id3v2_comment(f)
            current_tta_data = LimitedFileReader(f, self.data_size())
            transfer_data(current_tta_data.read, temp_tta_data.write)
            f.close()

            #and rebuild TTA with APEv2/ID3 tags in place
            f = open(self.filename, "wb")
            temp_tta_data.seek(0, 0)

            if (isinstance(metadata, ApeTag)):
                from .bitstream import BitstreamWriter
                transfer_data(temp_tta_data.read, f.write)
                metadata.build(BitstreamWriter(f, True))
            elif (isinstance(metadata, ID3CommentPair)):
                from .bitstream import BitstreamWriter
                metadata.id3v2.build(BitstreamWriter(f, False))
                transfer_data(temp_tta_data.read, f.write)
                metadata.id3v1.build(f)
            elif (isinstance(metadata, ID3v2Comment)):
                from .bitstream import BitstreamWriter
                metadata.build(BitstreamWriter(f, False))
                transfer_data(temp_tta_data.read, f.write)
            else:
                transfer_data(temp_tta_data.read, f.write)
                metadata.build(f)

            f.close()
            temp_tta_data.close()

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from tempfile import TemporaryFile
        from . import (transfer_data, LimitedFileReader)
        from .id3 import skip_id3v2_comment

        #move only TTA data to temporary space
        temp_tta_data = TemporaryFile()
        f = open(self.filename, "rb")
        skip_id3v2_comment(f)
        current_tta_data = LimitedFileReader(f, self.data_size())
        transfer_data(current_tta_data.read, temp_tta_data.write)
        f.close()

        #and overwrite original with no tags attached
        f = open(self.filename, "wb")
        temp_tta_data.seek(0, 0)
        transfer_data(temp_tta_data.read, f.write)
        f.close()
        temp_tta_data.close()

    def get_cuesheet(self):
        """returns the embedded Cuesheet-compatible object, or None

        raises IOError if a problem occurs when reading the file"""

        import cue

        metadata = self.get_metadata()

        if ((metadata is not None) and ('Cuesheet' in metadata.keys())):
            try:
                return cue.read_cuesheet_string(
                    unicode(metadata['Cuesheet']).encode('utf-8', 'replace'))
            except cue.CueException:
                #unlike FLAC, just because a cuesheet is embedded
                #does not mean it is compliant
                return None
        else:
            return None

    def set_cuesheet(self, cuesheet):
        """imports cuesheet data from a Sheet object

        Raises IOError if an error occurs setting the cuesheet"""

        import os.path
        import cStringIO
        from . import (MetaData, Filename, FS_ENCODING)
        from .ape import ApeTag
        from .cue import write_cuesheet

        if (cuesheet is None):
            return

        metadata = self.get_metadata()
        if (metadata is None):
            metadata = ApeTag([])

        cuesheet_data = cStringIO.StringIO()
        write_cuesheet(cuesheet,
                       str(Filename(self.filename).basename()),
                       cuesheet_data)

        metadata['Cuesheet'] = ApeTag.ITEM.string(
            'Cuesheet',
            cuesheet_data.getvalue().decode(FS_ENCODING, 'replace'))

        self.update_metadata(metadata)

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """adds ReplayGain values to a list of filename strings

        all the filenames must be of this AudioFile type
        raises ValueError if some problem occurs during ReplayGain application
        """

        from . import open_files
        from . import calculate_replay_gain
        from .ape import ApeTag, ApeTagItem

        tracks = [track for track in open_files(filenames) if
                  isinstance(track, cls)]

        #calculate ReplayGain for all TrueAudio tracks
        if (len(tracks) > 0):
            for (track,
                 track_gain,
                 track_peak,
                 album_gain,
                 album_peak) in calculate_replay_gain(tracks, progress):
                metadata = track.get_metadata()

                #convert current in each track metadata to APEv2
                #or create new APEv2 tag if necessary
                if (metadata is None):
                    metadata = ApeTag([])
                else:
                    metadata = ApeTag.converted(metadata)

                #then update track with tagged metadata
                metadata["replaygain_track_gain"] = ApeTagItem.string(
                    "replaygain_track_gain",
                    u"%+1.2f dB" % (track_gain))
                metadata["replaygain_track_peak"] = ApeTagItem.string(
                    "replaygain_track_peak",
                    u"%1.6f" % (track_peak))
                metadata["replaygain_album_gain"] = ApeTagItem.string(
                    "replaygain_album_gain",
                    u"%+1.2f dB" % (album_gain))
                metadata["replaygain_album_peak"] = ApeTagItem.string(
                    "replaygain_album_peak",
                    u"%1.6f" % (album_peak))

                track.update_metadata(metadata)

    @classmethod
    def supports_replay_gain(cls):
        """returns True if this class supports ReplayGain"""

        return True

    @classmethod
    def lossless_replay_gain(cls):
        """returns True"""

        return True

    def replay_gain(self):
        """returns a ReplayGain object of our ReplayGain values

        returns None if we have no values"""

        from .ape import ApeTag

        #if current metadata is present and is in APEv2 format,
        #return contents of "replaygain_" tags
        metadata = self.get_metadata()
        if ((metadata is not None) and
            isinstance(metadata, ApeTag) and
            set(['replaygain_track_gain', 'replaygain_track_peak',
                 'replaygain_album_gain', 'replaygain_album_peak']).issubset(
                metadata.keys())):
            try:
                from . import ReplayGain
                return ReplayGain(
                    unicode(metadata['replaygain_track_gain'])[0:-len(" dB")],
                    unicode(metadata['replaygain_track_peak']),
                    unicode(metadata['replaygain_album_gain'])[0:-len(" dB")],
                    unicode(metadata['replaygain_album_peak']))
            except ValueError:
                return None
        else:
            #otherwise, return None
            return None


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
                 ["TTA1",
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
    writer.build("32U" * len(frame_sizes), frame_sizes)
    writer.pop_callback()
    writer.write(32, int(crc))


def div_ceil(n, d):
    """returns the ceiling of n divided by d as an int"""

    return n // d + (1 if ((n % d) != 0) else 0)


class CRC32:
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
