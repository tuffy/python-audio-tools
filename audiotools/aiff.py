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

from audiotools import (InvalidFile, PCMReader, AiffContainer)
from audiotools.pcm import FrameList
import struct


def parse_ieee_extended(bitstream):
    """returns a parsed 80-bit IEEE extended value from BitstreamReader
    this is used to handle AIFF's sample rate field"""

    (signed, exponent, mantissa) = bitstream.parse("1u 15u 64U")
    if ((exponent == 0) and (mantissa == 0)):
        return 0
    elif (exponent == 0x7FFF):
        return 1.79769313486231e+308
    else:
        f = mantissa * (2.0 ** (exponent - 16383 - 63))
        return f if not signed else -f


def build_ieee_extended(bitstream, value):
    """writes an 80-bit IEEE extended value to BitstreamWriter
    this is used to handle AIFF's sample rate field"""

    from math import frexp

    if (value < 0):
        signed = 1
        value = abs(value)
    else:
        signed = 0

    (fmant, exponent) = frexp(value)
    if ((exponent > 16384) or (fmant >= 1)):
        exponent = 0x7FFF
        mantissa = 0
    else:
        exponent += 16382
        mantissa = fmant * (2 ** 64)

    bitstream.build("1u 15u 64U", (signed, exponent, int(mantissa)))


def pad_data(pcm_frames, channels, bits_per_sample):
    """returns True if the given stream combination
    requires an extra padding byte at the end of the 'data' chunk"""

    return (pcm_frames * channels * (bits_per_sample // 8)) % 2


def validate_header(header):
    """given header string as returned by aiff_header_footer()
    returns (total size, ssnd size)
    where total size is the size of the file in bytes
    and ssnd size is the size of the SSND chunk in bytes
    (including the 8 prefix bytes in the chunk
    but *not* including any padding byte at the end)

    the size of the SSND chunk and of the total file should be validated
    after the file has been completely written
    such that len(header) + len(SSND chunk) + len(footer) = total size

    raises ValueError if the header is invalid"""

    import cStringIO
    from audiotools.bitstream import BitstreamReader

    header_size = len(header)
    aiff_file = BitstreamReader(cStringIO.StringIO(header), 0)
    try:
        # ensure header starts with FORM<size>AIFF chunk
        (form, remaining_size, aiff) = aiff_file.parse("4b 32u 4b")
        if (form != "FORM"):
            from audiotools.text import ERR_AIFF_NOT_AIFF
            raise ValueError(ERR_AIFF_NOT_AIFF)
        elif (aiff != "AIFF"):
            from audiotools.text import ERR_AIFF_INVALID_AIFF
            raise ValueError(ERR_AIFF_INVALID_AIFF)
        else:
            total_size = remaining_size + 8
            header_size -= 12

        comm_found = False

        while (header_size > 0):
            # ensure each chunk header is valid
            (chunk_id, chunk_size) = aiff_file.parse("4b 32u")
            if (frozenset(chunk_id).issubset(AiffAudio.PRINTABLE_ASCII)):
                header_size -= 8
            else:
                from audiotools.text import ERR_AIFF_INVALID_CHUNK
                raise ValueError(ERR_AIFF_INVALID_CHUNK)

            if (chunk_id == "COMM"):
                if (not comm_found):
                    # skip COMM chunk when found
                    comm_found = True
                    if (chunk_size % 2):
                        aiff_file.skip_bytes(chunk_size + 1)
                        header_size -= (chunk_size + 1)
                    else:
                        aiff_file.skip_bytes(chunk_size)
                        header_size -= chunk_size
                else:
                    # ensure only one COMM chunk is found
                    from audiotools.text import ERR_AIFF_MULTIPLE_COMM_CHUNKS
                    raise ValueError(ERR_AIFF_MULTIPLE_COMM_CHUNKS)
            elif (chunk_id == "SSND"):
                if (not comm_found):
                    # ensure at least one COMM chunk is found
                    from audiotools.text import ERR_AIFF_PREMATURE_SSND_CHUNK
                    raise ValueError(ERR_AIFF_PREMATURE_SSND_CHUNK)
                elif (header_size > 8):
                    # ensure exactly 8 bytes remain after SSND chunk header
                    from audiotools.text import ERR_AIFF_HEADER_EXTRA_SSND
                    raise ValueError(ERR_AIFF_HEADER_EXTRA_SSND)
                elif (header_size < 8):
                    from audiotools.text import ERR_AIFF_HEADER_MISSING_SSND
                    raise ValueError(ERR_AIFF_HEADER_MISSING_SSND)
                else:
                    return (total_size, chunk_size - 8)
            else:
                # skip the full contents of non-audio chunks
                if (chunk_size % 2):
                    aiff_file.skip_bytes(chunk_size + 1)
                    header_size -= (chunk_size + 1)
                else:
                    aiff_file.skip_bytes(chunk_size)
                    header_size -= chunk_size
        else:
            # header parsed with no SSND chunks found
            from audiotools.text import ERR_AIFF_NO_SSND_CHUNK
            raise ValueError(ERR_AIFF_NO_SSND_CHUNK)
    except IOError:
        from audiotools.text import ERR_AIFF_HEADER_IOERROR
        raise ValueError(ERR_AIFF_HEADER_IOERROR)


def validate_footer(footer, ssnd_bytes_written):
    """given a footer string as returned by aiff_header_footer()
    and PCM stream parameters, returns True if the footer is valid

    raises ValueError is the footer is invalid"""

    import cStringIO
    from audiotools.bitstream import BitstreamReader

    total_size = len(footer)
    aiff_file = BitstreamReader(cStringIO.StringIO(footer), 0)
    try:
        # ensure footer is padded properly if necessary
        # based on size of data bytes written
        if (ssnd_bytes_written % 2):
            aiff_file.skip_bytes(1)
            total_size -= 1

        while (total_size > 0):
            (chunk_id, chunk_size) = aiff_file.parse("4b 32u")
            if (frozenset(chunk_id).issubset(AiffAudio.PRINTABLE_ASCII)):
                total_size -= 8
            else:
                from audiotools.text import ERR_AIFF_INVALID_CHUNK
                raise ValueError(ERR_AIFF_INVALID_CHUNK)

            if (chunk_id == "COMM"):
                # ensure no COMM chunks are found
                from audiotools.text import ERR_AIFF_MULTIPLE_COMM_CHUNKS
                raise ValueError(ERR_AIFF_MULTIPLE_COMM_CHUNKS)
            elif (chunk_id == "SSND"):
                # ensure no SSND chunks are found
                from audiotools.text import ERR_AIFF_MULTIPLE_SSND_CHUNKS
                raise ValueError(ERR_AIFF_MULTIPLE_SSND_CHUNKS)
            else:
                # skip the full contents of non-audio chunks
                if (chunk_size % 2):
                    aiff_file.skip_bytes(chunk_size + 1)
                    total_size -= (chunk_size + 1)
                else:
                    aiff_file.skip_bytes(chunk_size)
                    total_size -= chunk_size
        else:
            return True
    except IOError:
        from audiotools.text import ERR_AIFF_FOOTER_IOERROR
        raise ValueError(ERR_AIFF_FOOTER_IOERROR)


class AIFF_Chunk:
    """a raw chunk of AIFF data"""

    def __init__(self, chunk_id, chunk_size, chunk_data):
        """chunk_id should be a binary string of ASCII
        chunk_size is the length of chunk_data
        chunk_data should be a binary string of chunk data"""

        # FIXME - check chunk_id's validity

        self.id = chunk_id
        self.__size__ = chunk_size
        self.__data__ = chunk_data

    def __repr__(self):
        return "AIFF_Chunk(%s)" % (repr(self.id))

    def size(self):
        """returns size of chunk in bytes
        not including any spacer byte for odd-sized chunks"""

        return self.__size__

    def total_size(self):
        """returns the total size of the chunk
        including the 8 byte ID/size and any padding byte"""

        if (self.__size__ % 2):
            return 8 + self.__size__ + 1
        else:
            return 8 + self.__size__

    def data(self):
        """returns chunk data as file-like object"""

        import cStringIO

        return cStringIO.StringIO(self.__data__)

    def verify(self):
        """returns True if chunk size matches chunk's data"""

        return self.__size__ == len(self.__data__)

    def write(self, f):
        """writes the entire chunk to the given output file object
        returns size of entire chunk (including header and spacer)
        in bytes"""

        f.write(self.id)
        f.write(struct.pack(">I", self.__size__))
        f.write(self.__data__)
        if (self.__size__ % 2):
            f.write(chr(0))
        return self.total_size()


class AIFF_File_Chunk(AIFF_Chunk):
    """a raw chunk of AIFF data taken from an existing file"""

    def __init__(self, chunk_id, chunk_size, aiff_file, chunk_data_offset):
        """chunk_id should be a binary string of ASCII
        chunk_size is the size of the chunk in bytes
        (not counting any spacer byte)
        aiff_file is the file this chunk belongs to
        chunk_data_offset is the offset to the chunk's data bytes
        (not including the 8 byte header)"""

        self.id = chunk_id
        self.__size__ = chunk_size
        self.__aiff_file__ = aiff_file
        self.__offset__ = chunk_data_offset

    def __repr__(self):
        return "AIFF_File_Chunk(%s)" % (repr(self.id))

    def data(self):
        """returns chunk data as file-like object"""

        from audiotools import LimitedFileReader

        self.__wav_file__.seek(self.__offset__)
        return LimitedFileReader(self.__wav_file__, self.size())

    def verify(self):
        """returns True if chunk size matches chunk's data"""

        self.__aiff_file__.seek(self.__offset__)
        to_read = self.__size__
        while (to_read > 0):
            s = self.__aiff_file__.read(min(0x100000, to_read))
            if (len(s) == 0):
                return False
            else:
                to_read -= len(s)
        return True

    def write(self, f):
        """writes the entire chunk to the given output file object
        returns size of entire chunk (including header and spacer)
        in bytes"""

        f.write(self.id)
        f.write(struct.pack(">I", self.__size__))
        self.__aiff_file__.seek(self.__offset__)
        to_write = self.__size__
        while (to_write > 0):
            s = self.__aiff_file__.read(min(0x100000, to_write))
            f.write(s)
            to_write -= len(s)

        if (self.__size__ % 2):
            f.write(chr(0))
        return self.total_size()


def parse_comm(comm):
    """given a COMM chunk (without the 8 byte name/size header)
    returns (channels, total_sample_frames, bits_per_sample,
             sample_rate, channel_mask)
    where channel_mask is a ChannelMask object and the rest are ints
    may raise IOError if an error occurs reading the chunk"""

    from audiotools import ChannelMask

    (channels,
     total_sample_frames,
     bits_per_sample) = comm.parse("16u 32u 16u")
    sample_rate = int(parse_ieee_extended(comm))

    if (channels <= 2):
        channel_mask = ChannelMask.from_channels(channels)
    else:
        channel_mask = ChannelMask(0)

    return (channels, total_sample_frames, bits_per_sample,
            sample_rate, channel_mask)


class AiffReader:
    """a PCMReader object for reading AIFF file contents"""

    def __init__(self, aiff_filename):
        """aiff_filename is a string"""

        from audiotools.bitstream import BitstreamReader

        self.file = open(aiff_filename, "rb")

        # ensure FORM<size>AIFF header is ok
        try:
            (form,
             total_size,
             aiff) = struct.unpack(">4sI4s", self.file.read(12))
        except struct.error:
            from audiotools.text import ERR_AIFF_INVALID_AIFF
            raise InvalidAIFF(ERR_AIFF_INVALID_AIFF)

        if (form != 'FORM'):
            from audiotools.text import ERR_AIFF_NOT_AIFF
            raise ValueError(ERR_AIFF_NOT_AIFF)
        elif (aiff != 'AIFF'):
            from audiotools.text import ERR_AIFF_INVALID_AIFF
            raise ValueError(ERR_AIFF_INVALID_AIFF)
        else:
            total_size -= 4
            comm_chunk_read = False

        # walk through chunks until "SSND" chunk encountered
        while (total_size > 0):
            try:
                (chunk_id,
                 chunk_size) = struct.unpack(">4sI", self.file.read(8))
            except struct.error:
                from audiotools.text import ERR_AIFF_INVALID_AIFF
                raise ValueError(ERR_AIFF_INVALID_AIFF)

            if (not frozenset(chunk_id).issubset(AiffAudio.PRINTABLE_ASCII)):
                from audiotools.text import ERR_AIFF_INVALID_CHUNK_ID
                raise ValueError(ERR_AIFF_INVALID_CHUNK_ID)
            else:
                total_size -= 8

            if (chunk_id == "COMM"):
                # when "COMM" chunk encountered,
                # use it to populate PCMReader attributes
                (self.channels,
                 self.total_pcm_frames,
                 self.bits_per_sample,
                 self.sample_rate,
                 channel_mask) = parse_comm(BitstreamReader(self.file, False))
                self.channel_mask = int(channel_mask)
                self.bytes_per_pcm_frame = ((self.bits_per_sample // 8) *
                                            self.channels)
                self.remaining_pcm_frames = self.total_pcm_frames
                comm_chunk_read = True
            elif (chunk_id == "SSND"):
                # when "SSND" chunk encountered,
                # strip off the "offset" and "block_size" attributes
                # and ready PCMReader for reading
                if (not comm_chunk_read):
                    from audiotools.text import ERR_AIFF_PREMATURE_SSND_CHUNK
                    raise ValueError(ERR_AIFF_PREMATURE_SSND_CHUNK)
                else:
                    self.file.read(8)
                    self.ssnd_chunk_offset = self.file.tell()
                    return
            else:
                # all other chunks are ignored
                self.file.read(chunk_size)

            if (chunk_size % 2):
                if (len(self.file.read(1)) < 1):
                    from audiotools.text import ERR_AIFF_INVALID_CHUNK
                    raise ValueError(ERR_AIFF_INVALID_CHUNK)
                total_size -= (chunk_size + 1)
            else:
                total_size -= chunk_size
        else:
            # raise an error if no "SSND" chunk is encountered
            from audiotools.text import ERR_AIFF_NO_SSND_CHUNK
            raise ValueError(ERR_AIFF_NO_SSND_CHUNK)

    def read(self, pcm_frames):
        """try to read a pcm.FrameList with the given number of PCM frames"""

        # try to read requested PCM frames or remaining frames
        requested_pcm_frames = min(max(pcm_frames, 1),
                                   self.remaining_pcm_frames)
        requested_bytes = (self.bytes_per_pcm_frame *
                           requested_pcm_frames)
        pcm_data = self.file.read(requested_bytes)

        # raise exception if "SSND" chunk exhausted early
        if (len(pcm_data) < requested_bytes):
            from audiotools.text import ERR_AIFF_TRUNCATED_SSND_CHUNK
            raise IOError(ERR_AIFF_TRUNCATED_SSND_CHUNK)
        else:
            self.remaining_pcm_frames -= requested_pcm_frames

            # return parsed chunk
            return FrameList(pcm_data,
                             self.channels,
                             self.bits_per_sample,
                             True,
                             True)

    def seek(self, pcm_frame_offset):
        """tries to seek to the given PCM frame offset
        returns the total amount of frames actually seeked over"""

        if (pcm_frame_offset < 0):
            from audiotools.text import ERR_NEGATIVE_SEEK
            raise ValueError(ERR_NEGATIVE_SEEK)

        # ensure one doesn't walk off the end of the file
        pcm_frame_offset = min(pcm_frame_offset,
                               self.total_pcm_frames)

        # position file in "SSND" chunk
        self.file.seek(self.ssnd_chunk_offset +
                       (pcm_frame_offset *
                        self.bytes_per_pcm_frame), 0)
        self.remaining_pcm_frames = (self.total_pcm_frames -
                                     pcm_frame_offset)

        return pcm_frame_offset

    def close(self):
        """closes the stream for reading"""

        self.file.close()


def aiff_header(sample_rate,
                channels,
                bits_per_sample,
                total_pcm_frames):
    """given a set of integer stream attributes,
    returns header string of everything before an AIFF's PCM data

    may raise ValueError if the total size of the file is too large"""

    from audiotools.bitstream import (BitstreamRecorder, format_size)

    header = BitstreamRecorder(False)

    data_size = (bits_per_sample // 8) * channels * total_pcm_frames
    total_size = ((format_size("4b" + "4b 32u" +
                               "16u 32u 16u 1u 15u 64U" +
                               "4b 32u 32u 32u") // 8) +
                  data_size + (data_size % 2))

    if (total_size < (2 ** 32)):
        header.build("4b 32u 4b", ("FORM", total_size, "AIFF"))
        header.build("4b 32u", ("COMM", 0x12))
        header.build("16u 32u 16u", (channels,
                                     total_pcm_frames,
                                     bits_per_sample))
        build_ieee_extended(header, sample_rate)
        header.build("4b 32u 32u 32u", ("SSND", data_size + 8, 0, 0))

        return header.data()
    else:
        raise ValueError("total size too large for aiff file")


class InvalidAIFF(InvalidFile):
    """raised if some problem occurs parsing AIFF chunks"""

    pass


class AiffAudio(AiffContainer):
    """an AIFF audio file"""

    SUFFIX = "aiff"
    NAME = SUFFIX
    DESCRIPTION = u"Audio Interchange File Format"

    PRINTABLE_ASCII = frozenset([chr(i) for i in range(0x20, 0x7E + 1)])

    def __init__(self, filename):
        """filename is a plain string"""

        from audiotools import ChannelMask

        AiffContainer.__init__(self, filename)

        self.__channels__ = 0
        self.__bits_per_sample__ = 0
        self.__sample_rate__ = 0
        self.__channel_mask__ = ChannelMask(0)
        self.__total_sample_frames__ = 0

        from audiotools.bitstream import BitstreamReader

        try:
            for chunk in self.chunks():
                if (chunk.id == "COMM"):
                    try:
                        (self.__channels__,
                         self.__total_sample_frames__,
                         self.__bits_per_sample__,
                         self.__sample_rate__,
                         self.__channel_mask__) = parse_comm(
                            BitstreamReader(chunk.data(), 0))
                        break
                    except IOError:
                        continue
        except IOError:
            raise InvalidAIFF("I/O error reading wave")

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        return self.__channel_mask__

    def lossless(self):
        """returns True"""

        return True

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__total_sample_frames__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def seekable(self):
        """returns True if the file is seekable"""

        return True

    def chunks(self):
        """yields a AIFF_Chunk compatible objects for each chunk in file"""

        from audiotools.text import (ERR_AIFF_NOT_AIFF,
                                     ERR_AIFF_INVALID_AIFF,
                                     ERR_AIFF_INVALID_CHUNK_ID,
                                     ERR_AIFF_INVALID_CHUNK)

        aiff_file = __open__(self.filename, 'rb')
        try:
            (form,
             total_size,
             aiff) = struct.unpack(">4sI4s", aiff_file.read(12))
        except struct.error:
            raise InvalidAIFF(ERR_AIFF_INVALID_AIFF)

        if (form != 'FORM'):
            raise InvalidAIFF(ERR_AIFF_NOT_AIFF)
        elif (aiff != 'AIFF'):
            raise InvalidAIFF(ERR_AIFF_INVALID_AIFF)
        else:
            total_size -= 4

        while (total_size > 0):
            # read the chunk header and ensure its validity
            try:
                data = aiff_file.read(8)
                (chunk_id,
                 chunk_size) = struct.unpack(">4sI", data)
            except struct.error:
                raise InvalidAIFF(ERR_AIFF_INVALID_AIFF)

            if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                raise InvalidAIFF(ERR_AIFF_INVALID_CHUNK_ID)
            else:
                total_size -= 8

            # yield AIFF_Chunk or AIFF_File_Chunk depending on chunk size
            if (chunk_size >= 0x100000):
                # if chunk is too large, yield a File_Chunk
                yield AIFF_File_Chunk(chunk_id,
                                      chunk_size,
                                      open(self.filename, "rb"),
                                      aiff_file.tell())
                aiff_file.seek(chunk_size, 1)
            else:
                # otherwise, yield a raw data Chunk
                yield AIFF_Chunk(chunk_id, chunk_size,
                                 aiff_file.read(chunk_size))

            if (chunk_size % 2):
                if (len(aiff_file.read(1)) < 1):
                    raise InvalidAIFF(ERR_AIFF_INVALID_CHUNK)
                total_size -= (chunk_size + 1)
            else:
                total_size -= chunk_size

    @classmethod
    def aiff_from_chunks(cls, aiff_file, chunk_iter):
        """builds a new AIFF file from a chunk data iterator

        aiff_file is a seekable file object
        chunk_iter should yield AIFF_Chunk-compatible objects
        """

        start = aiff_file.tell()

        # write an unfinished header with a placeholder size
        aiff_file.write(struct.pack(">4sI4s", "FORM", 4, "AIFF"))

        # write the individual chunks
        total_size = 4

        for chunk in chunk_iter:
            total_size += chunk.write(aiff_file)

        # once the chunks are done, go back and re-write the header
        aiff_file.seek(start)
        aiff_file.write(struct.pack(">4sI4s", "FORM", total_size, "AIFF"))

    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from audiotools.bitstream import BitstreamReader
        from audiotools.id3 import ID3v22Comment

        for chunk in self.chunks():
            if (chunk.id == 'ID3 '):
                return ID3v22Comment.parse(BitstreamReader(chunk.data(), 0))
        else:
            return None

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        from audiotools import transfer_data, TemporaryFile
        from audiotools.id3 import ID3v22Comment
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.text import ERR_FOREIGN_METADATA
        import os

        if (metadata is None):
            return
        elif (not isinstance(metadata, ID3v22Comment)):
            raise ValueError(ERR_FOREIGN_METADATA)
        elif (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        # turn our ID3v2.2 tag into a raw binary chunk
        id3_chunk = BitstreamRecorder(0)
        metadata.build(id3_chunk)

        # generate a temporary AIFF file in which our new ID3v2.2 chunk
        # replaces the existing ID3v2.2 chunk
        new_aiff = TemporaryFile(self.filename)

        self.__class__.aiff_from_chunks(
            new_aiff,
            [(chunk if chunk.id != "ID3 " else
              AIFF_Chunk("ID3 ",
                         id3_chunk.bytes(),
                         id3_chunk.data())) for chunk in self.chunks()])

        new_aiff.close()

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        from audiotools.id3 import ID3v22Comment

        if (metadata is None):
            return self.delete_metadata()
        elif (self.get_metadata() is not None):
            # current file has metadata, so replace it with new metadata
            self.update_metadata(ID3v22Comment.converted(metadata))
        else:
            # current file has no metadata, so append new ID3 block
            import os
            from audiotools.bitstream import BitstreamRecorder
            from audiotools import transfer_data, TemporaryFile

            if (not os.access(self.filename, os.W_OK)):
                raise IOError(self.filename)

            # turn our ID3v2.2 tag into a raw binary chunk
            id3_chunk = BitstreamRecorder(0)
            ID3v22Comment.converted(metadata).build(id3_chunk)

            # generate a temporary AIFF file in which our new ID3v2.2 chunk
            # is appended to the file's set of chunks
            new_aiff = TemporaryFile(self.filename)
            self.__class__.aiff_from_chunks(
                new_aiff,
                [c for c in self.chunks()] + [AIFF_Chunk("ID3 ",
                                                         id3_chunk.bytes(),
                                                         id3_chunk.data())])

            new_aiff.close()

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        import os
        from audiotools import transfer_data, TemporaryFile

        if (not os.access(self.filename, os.W_OK)):
            raise IOError(self.filename)

        new_aiff = TemporaryFile(self.filename)
        self.__class__.aiff_from_chunks(
            new_aiff,
            [c for c in self.chunks() if c.id != "ID3 "])

        new_aiff.close()

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        return AiffReader(self.filename)

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AiffAudio object"""

        from audiotools import EncodingError
        from audiotools import DecodingError
        from audiotools import CounterPCMReader
        from audiotools import transfer_framelist_data

        try:
            header = aiff_header(pcmreader.sample_rate,
                                 pcmreader.channels,
                                 pcmreader.bits_per_sample,
                                 total_pcm_frames if total_pcm_frames
                                 is not None else 0)
        except ValueError as err:
            raise EncodingError(str(err))

        try:
            f = open(filename, "wb")
        except IOError as msg:
            raise EncodingError(str(msg))

        counter = CounterPCMReader(pcmreader)
        f.write(header)
        try:
            transfer_framelist_data(counter, f.write, True, True)
        except (IOError, ValueError) as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))

        # handle odd-sized SSND chunks
        if (counter.frames_written % 2):
            f.write(chr(0))

        if (total_pcm_frames is not None):
            if (total_pcm_frames != counter.frames_written):
                # ensure written number of PCM frames
                # matches total_pcm_frames argument
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                cls.__unlink__(filename)
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)
            else:
                f.close()
        else:
            # go back and rewrite populated header
            # with counted number of PCM frames
            f.seek(0, 0)
            f.write(aiff_header(pcmreader.sample_rate,
                                pcmreader.channels,
                                pcmreader.bits_per_sample,
                                counter.frames_written))
            f.close()

        return AiffAudio(filename)

    def has_foreign_aiff_chunks(self):
        """returns True if the audio file contains non-audio AIFF chunks"""

        return ({'COMM', 'SSND'} != {c.id for c in self.chunks()})

    def aiff_header_footer(self):
        """returns (header, footer) tuple of strings
        containing all data before and after the PCM stream

        if self.has_foreign_aiff_chunks() is False,
        may raise ValueError if the file has no header and footer
        for any reason"""

        from audiotools.bitstream import BitstreamReader
        from audiotools.bitstream import BitstreamRecorder
        from audiotools.text import (ERR_AIFF_NOT_AIFF,
                                     ERR_AIFF_INVALID_AIFF,
                                     ERR_AIFF_INVALID_CHUNK_ID)

        head = BitstreamRecorder(0)
        tail = BitstreamRecorder(0)
        current_block = head

        aiff_file = BitstreamReader(open(self.filename, 'rb'), 0)
        try:
            # transfer the 12-byte "RIFFsizeWAVE" header to head
            (form, size, aiff) = aiff_file.parse("4b 32u 4b")
            if (form != 'FORM'):
                raise InvalidAIFF(ERR_AIFF_NOT_AIFF)
            elif (aiff != 'AIFF'):
                raise InvalidAIFF(ERR_AIFF_INVALID_AIFF)
            else:
                current_block.build("4b 32u 4b", (form, size, aiff))
                total_size = size - 4

            while (total_size > 0):
                # transfer each chunk header
                (chunk_id, chunk_size) = aiff_file.parse("4b 32u")
                if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                    raise InvalidAIFF(ERR_AIFF_INVALID_CHUNK_ID)
                else:
                    current_block.build("4b 32u", (chunk_id, chunk_size))
                    total_size -= 8

                # and transfer the full content of non-audio chunks
                if (chunk_id != "SSND"):
                    if (chunk_size % 2):
                        current_block.write_bytes(
                            aiff_file.read_bytes(chunk_size + 1))
                        total_size -= (chunk_size + 1)
                    else:
                        current_block.write_bytes(
                            aiff_file.read_bytes(chunk_size))
                        total_size -= chunk_size
                else:
                    # transfer alignment as part of SSND's chunk header
                    align = aiff_file.parse("32u 32u")
                    current_block.build("32u 32u", align)
                    aiff_file.skip_bytes(chunk_size - 8)
                    current_block = tail

                    if (chunk_size % 2):
                        current_block.write_bytes(aiff_file.read_bytes(1))
                        total_size -= (chunk_size + 1)
                    else:
                        total_size -= chunk_size

            return (head.data(), tail.data())
        finally:
            aiff_file.close()

    @classmethod
    def from_aiff(cls, filename, header, pcmreader, footer, compression=None):
        """encodes a new file from AIFF data

        takes a filename string, header string,
        PCMReader object, footer string
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AiffAudio object

        header + pcm data + footer should always result
        in the original AIFF file being restored
        without need for any padding bytes

        may raise EncodingError if some problem occurs when
        encoding the input file"""

        from audiotools import (DecodingError, EncodingError, FRAMELIST_SIZE)
        from struct import unpack

        # ensure header validates correctly
        try:
            (total_size, ssnd_size) = validate_header(header)
        except ValueError as err:
            raise EncodingError(str(err))

        try:
            # write header to output file
            f = open(filename, "wb")
            f.write(header)

            # write PCM data to output file
            SSND_bytes_written = 0
            s = pcmreader.read(FRAMELIST_SIZE).to_bytes(True, True)
            while (len(s) > 0):
                SSND_bytes_written += len(s)
                f.write(s)
                s = pcmreader.read(FRAMELIST_SIZE).to_bytes(True, True)

            # ensure output data size matches the "SSND" chunk's size
            if (ssnd_size != SSND_bytes_written):
                cls.__unlink__(filename)
                from audiotools.text import ERR_AIFF_TRUNCATED_SSND_CHUNK
                raise EncodingError(ERR_AIFF_TRUNCATED_SSND_CHUNK)

            # ensure footer validates correctly
            try:
                validate_footer(footer, SSND_bytes_written)
                # before writing it to disk
                f.write(footer)
            except ValueError as err:
                cls.__unlink__(filename)
                raise EncodingError(str(err))

            f.close()

            # ensure total size is correct
            if ((len(header) + ssnd_size + len(footer)) != total_size):
                cls.__unlink__(filename)
                from audiotools.text import ERR_AIFF_INVALID_SIZE
                raise EncodingError(ERR_AIFF_INVALID_SIZE)

            return cls(filename)
        except IOError as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except DecodingError as err:
            cls.__unlink__(filename)
            raise EncodingError(err.error_message)

    def verify(self, progress=None):
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        from audiotools import CounterPCMReader
        from audiotools import transfer_framelist_data
        from audiotools import to_pcm_progress

        try:
            (header, footer) = self.aiff_header_footer()
        except IOError as err:
            raise InvalidAIFF(unicode(err))
        except ValueError as err:
            raise InvalidAIFF(unicode(err))

        # ensure header is valid
        try:
            (total_size, data_size) = validate_header(header)
        except ValueError as err:
            raise InvalidAIFF(unicode(err))

        # ensure "ssnd" chunk has all its data
        counter = CounterPCMReader(to_pcm_progress(self, progress))
        try:
            transfer_framelist_data(counter, lambda f: f)
        except IOError:
            from audiotools.text import ERR_AIFF_TRUNCATED_SSND_CHUNK
            raise InvalidAIFF(ERR_AIFF_TRUNCATED_SSND_CHUNK)

        data_bytes_written = counter.bytes_written()

        # ensure output data size matches the "ssnd" chunk's size
        if (data_size != data_bytes_written):
            from audiotools.text import ERR_AIFF_TRUNCATED_SSND_CHUNK
            raise InvalidAIFF(ERR_AIFF_TRUNCATED_SSND_CHUNK)

        # ensure footer validates correctly
        try:
            validate_footer(footer, data_bytes_written)
        except ValueError as err:
            from audiotools.text import ERR_AIFF_INVALID_SIZE
            raise InvalidAIFF(ERR_AIFF_INVALID_SIZE)

        # ensure total size is correct
        if ((len(header) + data_size + len(footer)) != total_size):
            from audiotools.text import ERR_AIFF_INVALID_SIZE
            raise InvalidAIFF(ERR_AIFF_INVALID_SIZE)

        return True

    def clean(self, output_filename=None):
        """cleans the file of known data and metadata problems

        output_filename is an optional filename of the fixed file
        if present, a new AudioFile is written to that path
        otherwise, only a dry-run is performed and no new file is written

        return list of fixes performed as Unicode strings

        raises IOError if unable to write the file or its metadata
        raises ValueError if the file has errors of some sort
        """

        from audiotools.text import (CLEAN_AIFF_MULTIPLE_COMM_CHUNKS,
                                     CLEAN_AIFF_REORDERED_SSND_CHUNK,
                                     CLEAN_AIFF_MULTIPLE_SSND_CHUNKS)

        fixes_performed = []
        chunk_queue = []
        pending_data = None

        for chunk in self.chunks():
            if (chunk.id == "COMM"):
                if ("COMM" in [c.id for c in chunk_queue]):
                    fixes_performed.append(
                        CLEAN_AIFF_MULTIPLE_COMM_CHUNKS)
                else:
                    chunk_queue.append(chunk)
                    if (pending_data is not None):
                        chunk_queue.append(pending_data)
                        pending_data = None
            elif (chunk.id == "SSND"):
                if ("COMM" not in [c.id for c in chunk_queue]):
                    fixes_performed.append(CLEAN_AIFF_REORDERED_SSND_CHUNK)
                    pending_data = chunk
                elif ("SSND" in [c.id for c in chunk_queue]):
                    fixes_performed.append(CLEAN_AIFF_MULTIPLE_SSND_CHUNKS)
                else:
                    chunk_queue.append(chunk)
            else:
                chunk_queue.append(chunk)

        old_metadata = self.get_metadata()
        if (old_metadata is not None):
            (fixed_metadata,
             metadata_fixes) = old_metadata.clean()
        else:
            fixed_metadata = old_metadata
            metadata_fixes = []

        if (output_filename is not None):
            output_file = open(output_filename, "wb")
            AiffAudio.aiff_from_chunks(output_file, chunk_queue)
            output_file.close()
            fixed_aiff = AiffAudio(output_filename)
            if (fixed_metadata is not None):
                fixed_aiff.update_metadata(fixed_metadata)

        return fixes_performed + metadata_fixes
