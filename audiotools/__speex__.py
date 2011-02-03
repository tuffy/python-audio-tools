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


from audiotools import (AudioFile, InvalidFile, PCMReader, PCMConverter,
                        Con, transfer_data, transfer_framelist_data,
                        subprocess, BIN, cStringIO, os, ignore_sigint,
                        EncodingError, DecodingError, ChannelMask,
                        __default_quality__)
from __vorbis__ import *

#######################
#Speex File
#######################


class InvalidSpeex(InvalidFile):
    pass


class UnframedVorbisComment(VorbisComment):
    """An implementation of VorbisComment without the framing bit."""

    VORBIS_COMMENT = Con.Struct("vorbis_comment",
                                Con.PascalString(
            "vendor_string",
            length_field=Con.ULInt32("length")),
                                Con.PrefixedArray(
        length_field=Con.ULInt32("length"),
        subcon=Con.PascalString("value",
                                length_field=Con.ULInt32("length"))))


class SpeexAudio(VorbisAudio):
    """An Ogg Speex audio file."""

    SUFFIX = "spx"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "8"
    COMPRESSION_MODES = tuple([str(i) for i in range(0, 11)])
    COMPRESSION_DESCRIPTIONS = {"0":
                                    _(u"corresponds to speexenc --quality 0"),
                                "10":
                                    _(u"corresponds to speexenc --quality 10")}
    BINARIES = ("speexenc", "speexdec")
    REPLAYGAIN_BINARIES = tuple()

    SPEEX_HEADER = Con.Struct('speex_header',
                              Con.String('speex_string', 8),
                              Con.String('speex_version', 20),
                              Con.ULInt32('speex_version_id'),
                              Con.ULInt32('header_size'),
                              Con.ULInt32('sampling_rate'),
                              Con.ULInt32('mode'),
                              Con.ULInt32('mode_bitstream_version'),
                              Con.ULInt32('channels'),
                              Con.ULInt32('bitrate'),
                              Con.ULInt32('frame_size'),
                              Con.ULInt32('vbr'),
                              Con.ULInt32('frame_per_packet'),
                              Con.ULInt32('extra_headers'),
                              Con.ULInt32('reserved1'),
                              Con.ULInt32('reserved2'))

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)
        try:
            self.__read_metadata__()
        except IOError, msg:
            raise InvalidSpeex(str(msg))

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x23] == 'Speex  ')

    def __read_metadata__(self):
        f = OggStreamReader(file(self.filename, "rb"))
        packets = f.packets()
        try:
            #first read the Header packet
            try:
                header = SpeexAudio.SPEEX_HEADER.parse(packets.next())
            except StopIteration:
                raise InvalidSpeex(_(u"Header packet not found"))

            self.__sample_rate__ = header.sampling_rate
            self.__channels__ = header.channels

            #the read the Comment packet
            comment_packet = packets.next()

            self.comment = UnframedVorbisComment.VORBIS_COMMENT.parse(
                comment_packet)
        finally:
            del(packets)
            f.close()
            del(f)

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        devnull = file(os.devnull, 'ab')
        sub = subprocess.Popen([BIN['speexdec'], self.filename, '-'],
                               stdout=subprocess.PIPE,
                               stderr=devnull)
        return PCMReader(
            sub.stdout,
            sample_rate=self.sample_rate(),
            channels=self.channels(),
            channel_mask=int(ChannelMask.from_channels(self.channels())),
            bits_per_sample=self.bits_per_sample(),
            process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new SpeexAudio object."""

        import bisect

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if ((pcmreader.bits_per_sample not in (8, 16)) or
            (pcmreader.channels > 2) or
            (pcmreader.sample_rate not in (8000, 16000, 32000, 44100))):
            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=[8000, 8000, 16000, 32000, 44100][bisect.bisect(
                    [8000, 16000, 32000, 44100], pcmreader.sample_rate)],
                channels=min(pcmreader.channels, 2),
                channel_mask=ChannelMask.from_channels(
                    min(pcmreader.channels, 2)),
                bits_per_sample=min(pcmreader.bits_per_sample, 16))

        BITS_PER_SAMPLE = {8: ['--8bit'],
                           16: ['--16bit']}[pcmreader.bits_per_sample]

        CHANNELS = {1: [], 2: ['--stereo']}[pcmreader.channels]

        devnull = file(os.devnull, "ab")

        sub = subprocess.Popen([BIN['speexenc'],
                                '--quality', str(compression),
                                '--rate', str(pcmreader.sample_rate),
                                '--le'] + \
                               BITS_PER_SAMPLE + \
                               CHANNELS + \
                               ['-', filename],
                               stdin=subprocess.PIPE,
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
            raise EncodingError(err.error_message)
        sub.stdin.close()
        result = sub.wait()
        devnull.close()

        if (result == 0):
            return SpeexAudio(filename)
        else:
            raise EncodingError(u"unable to encode file with speexenc")

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        comment = VorbisComment.converted(metadata)

        if (comment is None):
            return

        reader = OggStreamReader(file(self.filename, 'rb'))
        new_file = cStringIO.StringIO()
        writer = OggStreamWriter(new_file)

        pages = reader.pages()

        #transfer our old header
        (header_page, header_data) = pages.next()
        writer.write_page(header_page, header_data)

        #skip the existing comment packet
        (page, data) = pages.next()
        while (page.segment_lengths[-1] == 255):
            (page, data) = pages.next()

        #write the pages for our new comment packet
        comment_pages = OggStreamWriter.build_pages(
            0,
            header_page.bitstream_serial_number,
            header_page.page_sequence_number + 1,
            comment.build())

        for (page, data) in comment_pages:
            writer.write_page(page, data)

        #write the rest of the pages, re-sequenced and re-checksummed
        sequence_number = comment_pages[-1][0].page_sequence_number + 1
        for (i, (page, data)) in enumerate(pages):
            page.page_sequence_number = i + sequence_number
            page.checksum = OggStreamReader.calculate_ogg_checksum(page, data)
            writer.write_page(page, data)

        reader.close()

        #re-write the file with our new data in "new_file"
        f = file(self.filename, "wb")
        f.write(new_file.getvalue())
        f.close()
        writer.close()

        self.__read_metadata__()

    @classmethod
    def can_add_replay_gain(cls):
        """Returns False."""

        return False
