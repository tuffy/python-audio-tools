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


from audiotools import (AudioFile, InvalidFile, PCMReader, Con,
                        transfer_data, InvalidFormat,
                        __capped_stream_reader__, BUFFER_SIZE,
                        FILENAME_FORMAT, EncodingError, DecodingError,
                        ChannelMask)
import gettext

gettext.install("audiotools", unicode=True)


class InvalidAU(InvalidFile):
    pass


#######################
#Sun AU
#######################


class AuAudio(AudioFile):
    """A Sun AU audio file."""

    SUFFIX = "au"
    NAME = SUFFIX

    AU_HEADER = Con.Struct('header',
                           Con.Const(Con.String('magic_number', 4), '.snd'),
                           Con.UBInt32('data_offset'),
                           Con.UBInt32('data_size'),
                           Con.UBInt32('encoding_format'),
                           Con.UBInt32('sample_rate'),
                           Con.UBInt32('channels'))

    def __init__(self, filename):
        AudioFile.__init__(self, filename)

        try:
            f = file(filename, 'rb')
        except IOError, msg:
            raise InvalidAU(str(msg))
        try:
            header = AuAudio.AU_HEADER.parse_stream(f)

            if (header.encoding_format not in (2, 3, 4)):
                raise InvalidFile(_(u"Unsupported Sun AU encoding format"))

            self.__bits_per_sample__ = {2: 8, 3: 16, 4: 24}[
                header.encoding_format]
            self.__channels__ = header.channels
            self.__sample_rate__ = header.sample_rate
            self.__total_frames__ = header.data_size / \
                (self.__bits_per_sample__ / 8) / \
                self.__channels__
            self.__data_offset__ = header.data_offset
            self.__data_size__ = header.data_size
        except Con.ConstError:
            raise InvalidFile(_(u"Invalid Sun AU header"))
        except Con.FieldError:
                raise InvalidAU(_(u"Invalid Sun AU header"))

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

        return self.__total_frames__

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        f = file(self.filename, 'rb')
        f.seek(self.__data_offset__, 0)

        return PCMReader(f,
                         sample_rate=self.sample_rate(),
                         channels=self.channels(),
                         channel_mask=int(self.channel_mask()),
                         bits_per_sample=self.bits_per_sample(),
                         signed=True,
                         big_endian=True)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AuAudio object."""

        if (pcmreader.bits_per_sample not in (8, 16, 24)):
            raise InvalidFormat(
                _(u"Unsupported bits per sample %s") % (
                    pcmreader.bits_per_sample))

        bytes_per_sample = pcmreader.bits_per_sample / 8

        header = Con.Container(magic_number='.snd',
                               data_offset=0,
                               data_size=0,
                               encoding_format={8: 2, 16: 3, 24: 4}[
                pcmreader.bits_per_sample],
                               sample_rate=pcmreader.sample_rate,
                               channels=pcmreader.channels)

        try:
            f = file(filename, 'wb')
        except IOError, err:
            raise EncodingError(str(err))
        try:
            #send out a dummy header
            f.write(AuAudio.AU_HEADER.build(header))
            header.data_offset = f.tell()

            #send our big-endian PCM data
            #d will be a list of ints, so we can't use transfer_data
            framelist = pcmreader.read(BUFFER_SIZE)
            while (len(framelist) > 0):
                bytes = framelist.to_bytes(True, True)
                f.write(bytes)
                header.data_size += len(bytes)
                framelist = pcmreader.read(BUFFER_SIZE)

            #send out a complete header
            f.seek(0, 0)
            f.write(AuAudio.AU_HEADER.build(header))
        finally:
            f.close()

        try:
            pcmreader.close()
        except DecodingError, err:
            raise EncodingError(err.error_message)

        return AuAudio(filename)

    @classmethod
    def track_name(cls, file_path, track_metadata=None, format=None):
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
