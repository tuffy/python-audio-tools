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


from audiotools import (AudioFile, InvalidFile, PCMReader,
                        transfer_data, InvalidFormat,
                        __capped_stream_reader__, BUFFER_SIZE,
                        FILENAME_FORMAT, EncodingError, DecodingError,
                        ChannelMask, os)
import audiotools.pcm
import gettext

gettext.install("audiotools", unicode=True)


class InvalidAU(InvalidFile):
    pass


#######################
#Sun AU
#######################


class AuReader(PCMReader):
    """A subclass of PCMReader for reading Sun AU file contents."""

    def __init__(self, au_file, data_size,
                 sample_rate, channels, channel_mask, bits_per_sample):
        """au_file is a file, data_size is an integer byte count.

        sample_rate, channels, channel_mask and bits_per_sample are ints.
        """

        PCMReader.__init__(self,
                           file=au_file,
                           sample_rate=sample_rate,
                           channels=channels,
                           channel_mask=channel_mask,
                           bits_per_sample=bits_per_sample)
        self.data_size = data_size

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes"."""

        #align bytes downward if an odd number is read in
        bytes -= (bytes % (self.channels * self.bits_per_sample / 8))
        bytes = max(bytes, self.channels * self.bits_per_sample / 8)
        pcm_data = self.file.read(bytes)
        if ((len(pcm_data) == 0) and (self.data_size > 0)):
            raise IOError("data ends prematurely")
        else:
            self.data_size -= len(pcm_data)

        try:
            return audiotools.pcm.FrameList(pcm_data,
                                            self.channels,
                                            self.bits_per_sample,
                                            True,
                                            True)
        except ValueError:
            raise IOError("data ends prematurely")


class AuAudio(AudioFile):
    """A Sun AU audio file."""

    SUFFIX = "au"
    NAME = SUFFIX

    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        from .bitstream import BitstreamReader

        try:
            f = file(filename, 'rb')

            (magic_number,
             self.__data_offset__,
             self.__data_size__,
             encoding_format,
             self.__sample_rate__,
             self.__channels__) = BitstreamReader(f, 0).parse(
                "4b 32u 32u 32u 32u 32u")
        except IOError, msg:
            raise InvalidAU(str(msg))

        if (magic_number != '.snd'):
            raise InvalidAU(_(u"Invalid Sun AU header"))
        try:
            self.__bits_per_sample__ = {2: 8, 3: 16, 4: 24}[encoding_format]
        except KeyError:
            raise InvalidAU(_(u"Unsupported encoding format"))

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        return file.read(4) == ".snd"

    def lossless(self):
        """Returns True."""

        return True

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bits_per_sample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        if (self.channels() <= 2):
            return ChannelMask.from_channels(self.channels())
        else:
            return ChannelMask(0)

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__sample_rate__

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return (self.__data_size__ /
                (self.__bits_per_sample__ / 8) /
                self.__channels__)

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        f = file(self.filename, 'rb')
        f.seek(self.__data_offset__, 0)

        return AuReader(au_file=f,
                        data_size=self.__data_size__,
                        sample_rate=self.sample_rate(),
                        channels=self.channels(),
                        channel_mask=int(self.channel_mask()),
                        bits_per_sample=self.bits_per_sample())

    def pcm_split(self):
        """Returns a pair of data strings before and after PCM data.

        The first contains all data before the PCM content of the data chunk.
        The second containing all data after the data chunk."""

        import struct

        f = file(self.filename, 'rb')
        (magic_number, data_offset) = struct.unpack(">4sI", f.read(8))
        header = f.read(data_offset - struct.calcsize(">4sI"))
        return (struct.pack(">4sI%ds" % (len(header)),
                            magic_number, data_offset, header), "")

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AuAudio object."""

        from .bitstream import BitstreamWriter

        if (pcmreader.bits_per_sample not in (8, 16, 24)):
            raise InvalidFormat(
                _(u"Unsupported bits per sample %s") % (
                    pcmreader.bits_per_sample))

        data_size = 0
        encoding_format = {8: 2, 16: 3, 24: 4}[pcmreader.bits_per_sample]

        try:
            f = file(filename, 'wb')
            au = BitstreamWriter(f, 0)
        except IOError, err:
            raise EncodingError(str(err))
        try:
            #write a dummy header
            au.build("4b 32u 32u 32u 32u 32u",
                     (".snd", 24, data_size, encoding_format,
                      pcmreader.sample_rate, pcmreader.channels))

            #write our big-endian PCM data
            try:
                framelist = pcmreader.read(BUFFER_SIZE)
                while (len(framelist) > 0):
                    bytes = framelist.to_bytes(True, True)
                    f.write(bytes)
                    data_size += len(bytes)
                    framelist = pcmreader.read(BUFFER_SIZE)
            except (IOError, ValueError), err:
                cls.__unlink__(filename)
                raise EncodingError(str(err))
            except Exception, err:
                cls.__unlink__(filename)
                raise err

            if (data_size < 2 ** 32):
                #rewind and write a complete header
                f.seek(0, 0)
                au.build("4b 32u 32u 32u 32u 32u",
                         (".snd", 24, data_size, encoding_format,
                          pcmreader.sample_rate, pcmreader.channels))
            else:
                os.unlink(filename)
                raise EncodingError("PCM data too large for Sun AU file")
        finally:
            f.close()

        try:
            pcmreader.close()
        except DecodingError, err:
            raise EncodingError(err.error_message)

        return AuAudio(filename)

    @classmethod
    def track_name(cls, file_path, track_metadata=None, format=None,
                   suffix=None):
        """Constructs a new filename string.

        Given a plain string to an existing path,
        a MetaData-compatible object (or None),
        a UTF-8-encoded Python format string
        and an ASCII-encoded suffix string (such as "mp3")
        returns a plain string of a new filename with format's
        fields filled-in and encoded as FS_ENCODING.
        Raises UnsupportedTracknameField if the format string
        contains invalid template fields."""

        if (format is None):
            format = "track%(track_number)2.2d.au"
        return AudioFile.track_name(file_path, track_metadata, format,
                                    suffix=cls.SUFFIX)
