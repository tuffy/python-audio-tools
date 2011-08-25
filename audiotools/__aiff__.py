#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2011  Brian Langenberger

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
                        __capped_stream_reader__, PCMReaderError,
                        transfer_data, DecodingError, EncodingError,
                        ID3v22Comment, BUFFER_SIZE, ChannelMask,
                        ReorderedPCMReader, pcm,
                        cStringIO, os, AiffContainer, to_pcm_progress)

import gettext

gettext.install("audiotools", unicode=True)

def parse_ieee_extended(bitstream):
    (signed, exponent, mantissa) = bitstream.parse("1u 15u 64U")
    if ((exponent == 0) and (mantissa == 0)):
        return 0
    elif (exponent == 0x7FFF):
        return 1.79769313486231e+308
    else:
        f = mantissa * (2.0 ** (exponent - 16383 - 63))
        return f if not signed else -f

def build_ieee_extended(bitstream, value):
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

    bitstream.build("1u 15u 64U", (signed, exponent, mantissa))

#######################
#AIFF
#######################


class AiffReader(PCMReader):
    """A subclass of PCMReader for reading AIFF file contents."""

    def __init__(self, aiff_file,
                 sample_rate, channels, channel_mask, bits_per_sample,
                 total_frames, process=None):
        """aiff_file should be a file-like object of aiff data

        sample_rate, channels, channel_mask and bits_per_sample are ints."""

        self.file = aiff_file
        self.sample_rate = sample_rate
        self.channels = channels
        self.channel_mask = channel_mask
        self.bits_per_sample = bits_per_sample
        self.remaining_frames = total_frames
        self.bytes_per_frame = self.channels * self.bits_per_sample / 8

        self.process = process

        from .bitstream import BitstreamReader

        #build a capped reader for the ssnd chunk
        aiff_reader = BitstreamReader(aiff_file, 0)
        try:
            (form, aiff) = aiff_reader.parse("4b 32p 4b")
            if (form != 'FORM'):
                raise InvalidAIFF(_(u"Not an AIFF file"))
            elif (aiff != 'AIFF'):
                raise InvalidAIFF(_(u"Invalid AIFF file"))

            while (True):
                (chunk_id, chunk_size) = aiff_reader.parse("4b 32u")
                if (chunk_id == 'SSND'):
                    #adjust for the SSND alignment
                    aiff_reader.skip(64)
                    break
                else:
                    aiff_reader.skip_bytes(chunk_size)
                    if (chunk_size % 2):
                        aiff_reader.skip(8)
        except IOError:
            raise InvalidAIFF(_(u"ssnd chunk not found"))

        #handle AIFF unusual channel order
        standard_channel_mask = ChannelMask(self.channel_mask)
        aiff_channel_mask = AIFFChannelMask(standard_channel_mask)
        if (channels in (3, 4, 6)):
            self.channel_order = [aiff_channel_mask.channels().index(channel)
                                  for channel in
                                  standard_channel_mask.channels()]
        else:
            self.channel_order = None

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes"."""

        #convert bytes to a number of PCM frames
        frames_read = min(max(bytes / self.bytes_per_frame, 1),
                          self.remaining_frames)

        if (frames_read > 0):
            pcm_data = self.file.read(frames_read * self.bytes_per_frame)
            if (len(pcm_data) < frames_read * self.bytes_per_frame):
                raise IOError("ssnd chunk ends prematurely")
            else:
                framelist = pcm.FrameList(pcm_data,
                                          self.channels,
                                          self.bits_per_sample,
                                          True, True)
                self.remaining_frames -= framelist.frames
                if (self.channel_order is not None):
                    return pcm.from_channels(
                        [framelist.channel(channel) for channel
                         in self.channel_order])
                else:
                    return framelist

        else:
            return pcm.FrameList("",
                                 self.channels,
                                 self.bits_per_sample,
                                 True, True)

class InvalidAIFF(InvalidFile):
    """Raised if some problem occurs parsing AIFF chunks."""

    pass


class AiffAudio(AiffContainer):
    """An AIFF audio file."""

    SUFFIX = "aiff"
    NAME = SUFFIX

    # SSND_ALIGN = Con.Struct("ssnd",
    #                         Con.UBInt32("offset"),
    #                         Con.UBInt32("blocksize"))

    PRINTABLE_ASCII = frozenset([chr(i) for i in xrange(0x20, 0x7E + 1)])

    def __init__(self, filename):
        """filename is a plain string."""

        self.filename = filename

        self.__channels__ = 0
        self.__bits_per_sample__ = 0
        self.__sample_rate__ = 0
        self.__channel_mask__ = ChannelMask(0)
        self.__total_sample_frames__ = 0

        from .bitstream import BitstreamReader

        try:
            aiff_file = BitstreamReader(open(filename, 'rb'), 0)
        except IOError, msg:
            raise InvalidAIFF(str(msg))

        try:
            try:
                (form, total_size, aiff) = aiff_file.parse("4b 32u 4b")
                if (form != 'FORM'):
                    raise InvalidAIFF(_(u"Not an AIFF file"))
                elif (aiff != 'AIFF'):
                    raise InvalidAIFF(_(u"Invalid AIFF file"))
                else:
                    total_size -= 4

                while (total_size > 0):
                    (chunk_id, chunk_size) = aiff_file.parse("4b 32u")
                    total_size -= 8
                    if (chunk_id == 'COMM'):
                        (self.__channels__,
                         self.__total_sample_frames__,
                         self.__bits_per_sample__) = aiff_file.parse(
                            "16u 32u 16u")
                        self.__sample_rate__ = int(
                            parse_ieee_extended(aiff_file))

                        #this unusual arrangement is taken from
                        #the AIFF-C specification
                        if (self.__channels__ <= 2):
                            self.__channel_mask__ = ChannelMask.from_channels(
                                self.__channels__)
                        elif (self.__channels__ == 3):
                            self.__channel_mask__ = ChannelMask.from_fields(
                                front_left=True, front_right=True,
                                front_center=True)
                        elif (self.__channels__ == 4):
                            self.__channel_mask__ = ChannelMask.from_fields(
                                front_left=True, front_right=True,
                                back_left=True, back_right=True)
                        elif (self.__channels__ == 6):
                            self.__channel_mask__ = ChannelMask.from_fields(
                                front_left=True, side_left=True,
                                front_center=True, front_right=True,
                                side_right=True, back_center=True)
                        else:
                            self.__channel_mask__ = ChannelMask(0)
                        break
                    elif (not frozenset(chunk_id).issubset(
                            self.PRINTABLE_ASCII)):
                        raise InvalidWave(_(u"Invalid AIFF chunk ID"))
                    else:
                        aiff_file.skip_bytes(chunk_size)
                        total_size -= chunk_size
                        if (chunk_size % 2):
                            aiff_file.skip(8)
                            total_size -= 1
                else:
                    raise InvalidAIFF(_(u"COMM chunk not found"))
            except IOError:
                raise InvalidAIFF(_(u"I/O error in AIFF headers "))
        finally:
            aiff_file.close()

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bits_per_sample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        return self.__channel_mask__

    def lossless(self):
        """Returns True."""

        return True

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__total_sample_frames__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__sample_rate__

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(12)

        return ((header[0:4] == 'FORM') and
                (header[8:12] == 'AIFF'))

    def chunks(self):
        """yields a (chunk_id, chunk_data) tuples

        chunk_id is a binary strings
        chunk_data is a binary string"""

        from .bitstream import BitstreamReader

        aiff_file = BitstreamReader(file(self.filename, 'rb'), 0)
        try:
            (form, total_size, aiff) = aiff_file.parse("4b 32u 4b")
            if (form != 'FORM'):
                raise InvalidAIFF(_(u"Not an AIFF file"))
            elif (aiff != 'AIFF'):
                raise InvalidAIFF(_(u"Invalid AIFF file"))
            else:
                total_size -= 4

            while (total_size > 0):
                #read the chunk header and ensure its validity
                (chunk_id, chunk_size) = aiff_file.parse("4b 32u")
                if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                    raise InvalidAIFF(_(u"Invalid AIFF chunk ID"))
                else:
                    total_size -= 8

                #yield the (chunk_id, chunk_data) strings
                yield (chunk_id, aiff_file.read_bytes(chunk_size))

                total_size -= chunk_size

                #round up chunk size to 16 bits
                if (chunk_size % 2):
                    aiff_file.skip(8)
                    total_size -= 1
        finally:
            aiff_file.close()

    @classmethod
    def aiff_from_chunks(cls, filename, chunk_iter):
        """Builds a new AIFF file from a chunk data iterator.

        filename is the path to the AIFF file to build.
        chunk_iter should yield (chunk_id, chunk_data) tuples.
        """

        from .bitstream import BitstreamWriter

        aiff = file(filename, 'wb')
        aiff_file = BitstreamWriter(aiff, 0)
        try:
            total_size = 4

            #write an unfinished header with a placeholder size
            aiff_file.build("4b 32u 4b", ("FORM", total_size, "AIFF"))

            #write the individual chunks
            for (chunk_id, chunk_data) in chunk_iter:
                aiff_file.build("4b 32u %db" % (len(chunk_data)),
                                (chunk_id, len(chunk_data), chunk_data))
                total_size += (8 + len(chunk_data))

                #round up chunks to 16 bit boundries
                if (len(chunk_data) % 2):
                    aiff_file.write(8, 0)
                    total_size += 1

            #once the chunks are done, go back and re-write the header
            aiff.seek(4, 0)
            aiff_file.write(32, total_size)
        finally:
            aiff_file.close()

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        from .bitstream import BitstreamReader

        for (chunk_id, chunk_data) in self.chunks():
            if (chunk_id == 'ID3 '):
                return ID3v22Comment.parse(
                    BitstreamReader(cStringIO.StringIO(chunk_data), 0))
        else:
            return None

    def update_metadata(self, metadata):
        """Takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object.

        Raises IOError if unable to write the file.
        """

        if (metadata is None):
            return
        elif (not isinstance(metadata, ID3v22Comment)):
            raise _(u"metadata not from audio file")

        def chunk_filter(chunks, id3_chunk):
            id3_found = False

            for (chunk_id, chunk_data) in chunks:
                if (chunk_id == 'ID3 '):
                    yield (chunk_id, id3_chunk)
                    id3_found = True
                else:
                    yield (chunk_id, chunk_data)
            else:
                if (not id3_found):
                    yield ('ID3 ', id3_chunk)

        import tempfile
        from .bitstream import BitstreamRecorder

        #turn our ID3v2.2 tag into a raw binary chunk
        id3_chunk = BitstreamRecorder(0)
        metadata.build(id3_chunk)
        id3_chunk = id3_chunk.data()

        #generate a temporary AIFF file in which our new ID3v2.2 chunk
        #replaces the existing ID3v2.2 chunk
        new_aiff = tempfile.NamedTemporaryFile(suffix=self.SUFFIX)
        self.__class__.aiff_from_chunks(new_aiff.name,
                                        chunk_filter(self.chunks(),
                                                     id3_chunk))

        #replace the existing file with data from the temporary file
        new_file = open(new_aiff.name, 'rb')
        old_file = open(self.filename, 'wb')
        transfer_data(new_file.read, old_file.write)
        old_file.close()
        new_file.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        if (metadata is None):
            return
        else:
            self.update_metadata(ID3v22Comment.converted(metadata))

    def delete_metadata(self):
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

        def chunk_filter(chunks):
            for (chunk_id, chunk_data) in chunks:
                if (chunk_id == 'ID3 '):
                    continue
                else:
                    yield (chunk_id, chunk_data)

        import tempfile

        import tempfile

        new_aiff = tempfile.NamedTemporaryFile(suffix=self.SUFFIX)
        self.__class__.aiff_from_chunks(new_aiff.name,
                                        chunk_filter(self.chunks()))

        new_file = open(new_aiff.name, 'rb')
        old_file = open(self.filename, 'wb')
        transfer_data(new_file.read, old_file.write)
        old_file.close()
        new_file.close()

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        return AiffReader(file(self.filename, 'rb'),
                          sample_rate=self.sample_rate(),
                          channels=self.channels(),
                          bits_per_sample=self.bits_per_sample(),
                          channel_mask=int(self.channel_mask()),
                          total_frames=self.__total_sample_frames__)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AiffAudio object."""

        from .bitstream import BitstreamWriter

        try:
            f = open(filename, 'wb')
            aiff = BitstreamWriter(f, 0)
        except IOError, msg:
            raise EncodingError(str(msg))

        try:
            total_size = 0
            data_size = 0
            total_pcm_frames = 0

            #switch pcmreader channel masks to AIFF's unusual configuration
            if (int(pcmreader.channel_mask) in
                (0x4,      # FC
                 0x3,      # FL, FR
                 0x7,      # FL, FR, FC
                 0x33,     # FL, FR, BL, BR
                 0x707)):  # FL, SL, FC, FR, SR, BC
                standard_channel_mask = ChannelMask(pcmreader.channel_mask)
                aiff_channel_mask = AIFFChannelMask(standard_channel_mask)
                pcmreader = ReorderedPCMReader(
                    pcmreader,
                    [standard_channel_mask.channels().index(channel)
                     for channel in aiff_channel_mask.channels()])

            #write out the basic headers first
            #we'll be back later to clean up the sizes
            aiff.build("4b 32u 4b", ("FORM", total_size, "AIFF"))
            total_size += 4

            aiff.build("4b 32u", ("COMM", 0x12))
            total_size += 8

            aiff.build("16u 32u 16u", (pcmreader.channels,
                                       total_pcm_frames,
                                       pcmreader.bits_per_sample))
            build_ieee_extended(aiff, pcmreader.sample_rate)
            total_size += 0x12

            aiff.build("4b 32u", ("SSND", data_size))
            total_size += 8

            aiff.build("32u 32u", (0, 0))
            data_size += 8
            total_size += 8

            #dump pcmreader's FrameLists into the file as big-endian
            try:
                framelist = pcmreader.read(BUFFER_SIZE)
                while (len(framelist) > 0):
                    bytes = framelist.to_bytes(True, True)
                    f.write(bytes)

                    total_size += len(bytes)
                    data_size += len(bytes)
                    total_pcm_frames += framelist.frames

                    framelist = pcmreader.read(BUFFER_SIZE)
            except (IOError, ValueError), err:
                cls.__unlink__(filename)
                raise EncodingError(str(err))
            except Exception, err:
                cls.__unlink__(filename)
                raise err

            #handle odd-sized data chunks
            if (data_size % 2):
                aiff.write(8, 0)
                total_size += 1

            #close the PCM reader and flush our output
            try:
                pcmreader.close()
            except DecodingError, err:
                cls.__unlink__(filename)
                raise EncodingError(err.error_message)
            f.flush()

            #go back to the beginning and rewrite the header
            f.seek(0, 0)
            aiff.build("4b 32u 4b", ("FORM", total_size, "AIFF"))
            aiff.build("4b 32u", ("COMM", 0x12))
            aiff.build("16u 32u 16u", (pcmreader.channels,
                                       total_pcm_frames,
                                       pcmreader.bits_per_sample))
            build_ieee_extended(aiff, pcmreader.sample_rate)
            aiff.build("4b 32u", ("SSND", data_size))
        finally:
            f.close()

        return AiffAudio(filename)

    def to_aiff(self, aiff_filename, progress=None):
        """Writes the contents of this file to the given .aiff filename string.

        Raises EncodingError if some error occurs during decoding."""

        try:
            self.verify()
        except InvalidAIFF, err:
            raise EncodingError(str(err))

        try:
            output = file(aiff_filename, 'wb')
            input = file(self.filename, 'rb')
        except IOError, msg:
            raise EncodingError(str(msg))
        try:
            transfer_data(input.read, output.write)
        finally:
            input.close()
            output.close()

    @classmethod
    def from_aiff(cls, filename, aiff_filename, compression=None,
                  progress=None):
        try:
            cls(aiff_filename).verify()
        except InvalidAIFF, err:
            raise EncodingError(unicode(err))

        try:
            input = file(aiff_filename, 'rb')
            output = file(filename, 'wb')
        except IOError, err:
            raise EncodingError(str(err))
        try:
            total_bytes = os.path.getsize(aiff_filename)
            current_bytes = 0
            s = input.read(4096)
            while (len(s) > 0):
                current_bytes += len(s)
                output.write(s)
                if (progress is not None):
                    progress(current_bytes, total_bytes)
                s = input.read(4096)
            output.flush()
            try:
                return AiffAudio(filename)
            except InvalidFile:
                cls.__unlink__(filename)
                raise EncodingError(u"invalid AIFF source file")
        finally:
            input.close()
            output.close()

    def convert(self, target_path, target_class, compression=None,
                progress=None):
        """Encodes a new AudioFile from existing AudioFile.

        Take a filename string, target class and optional compression string.
        Encodes a new AudioFile in the target class and returns
        the resulting object.
        May raise EncodingError if some problem occurs during encoding."""

        if (hasattr(target_class, "from_aiff")):
            return target_class.from_aiff(target_path,
                                          self.filename,
                                          compression=compression,
                                          progress=progress)
        else:
            return target_class.from_pcm(target_path,
                                         to_pcm_progress(self, progress),
                                         compression)

    def pcm_split(self):
        """Returns a pair of data strings before and after PCM data.

        The first contains all data before the PCM content of the data chunk.
        The second containing all data after the data chunk.
        For example:

        >>> a = audiotools.open("input.aiff")
        >>> (head, tail) = a.pcm_split()
        >>> f = open("output.aiff", "wb")
        >>> f.write(head)
        >>> audiotools.transfer_framelist_data(a.to_pcm(), f.write, True, True)
        >>> f.write(tail)
        >>> f.close()

        should result in "output.aiff" being identical to "input.aiff".
        """

        from .bitstream import BitstreamReader
        from .bitstream import BitstreamRecorder

        head = BitstreamRecorder(0)
        tail = BitstreamRecorder(0)
        current_block = head

        aiff_file = BitstreamReader(open(self.filename, 'rb'), 0)
        try:
            #transfer the 12-byte "RIFFsizeWAVE" header to head
            (form, size, aiff) = aiff_file.parse("4b 32u 4b")
            if (form != 'FORM'):
                raise InvalidAIFF(_(u"Not an AIFF file"))
            elif (aiff != 'AIFF'):
                raise InvalidAIFF(_(u"Invalid AIFF file"))
            else:
                current_block.build("4b 32u 4b", (form, size, aiff))
                total_size = size - 4

            while (total_size > 0):
                #transfer each chunk header
                (chunk_id, chunk_size) = aiff_file.parse("4b 32u")
                if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                    raise InvalidWave(_(u"Invalid AIFF chunk ID"))
                else:
                    current_block.build("4b 32u", (chunk_id, chunk_size))
                    total_size -= 8

                #round up chunk size to 16 bits
                if (chunk_size % 2):
                    chunk_size += 1

                #and transfer the full content of non-data chunks
                if (chunk_id != "SSND"):
                    current_block.write_bytes(aiff_file.read_bytes(chunk_size))
                else:
                    #transfer alignment as part of SSND's chunk header
                    align = aiff_file.parse("32u 32u")
                    current_block.build("32u 32u", align)
                    aiff_file.skip_bytes(chunk_size - 8)
                    current_block = tail

                total_size -= chunk_size

            return (head.data(), tail.data())
        finally:
            aiff_file.close()

    def has_foreign_aiff_chunks(self):
        return (set(['COMM', 'SSND']) !=
                set([chunk[0] for chunk in self.chunks()]))


class AIFFChannelMask(ChannelMask):
    """The AIFF-specific channel mapping."""

    def __repr__(self):
        return "AIFFChannelMask(%s)" % \
            ",".join(["%s=%s" % (field, getattr(self, field))
                      for field in self.SPEAKER_TO_MASK.keys()
                      if (getattr(self, field))])

    def channels(self):
        """Returns a list of speaker strings this mask contains.

        Returned in the order in which they should appear
        in the PCM stream.
        """

        count = len(self)
        if (count == 1):
            return ["front_center"]
        elif (count == 2):
            return ["front_left", "front_right"]
        elif (count == 3):
            return ["front_left", "front_right", "front_center"]
        elif (count == 4):
            return ["front_left", "front_right",
                    "back_left", "back_right"]
        elif (count == 6):
            return ["front_left", "side_left", "front_center",
                    "front_right", "side_right", "back_center"]
        else:
            return []
