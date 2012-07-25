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

from audiotools import (AudioFile, InvalidFile, ChannelMask)


class InvalidVorbis(InvalidFile):
    pass


def verify_ogg_stream(stream):
    """verifies an Ogg stream file object

    this file must be rewound to the start of a page
    returns True if the file is valid
    raises IOError or ValueError if there is some problem with the file
    """

    from . import verify
    verify.ogg(stream)
    return True


#######################
#Vorbis File
#######################

class VorbisAudio(AudioFile):
    """an Ogg Vorbis file"""

    from .text import (COMP_VORBIS_0,
                       COMP_VORBIS_10)

    SUFFIX = "ogg"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "3"
    COMPRESSION_MODES = tuple([str(i) for i in range(0, 11)])
    COMPRESSION_DESCRIPTIONS = {"0": COMP_VORBIS_0,
                                "10": COMP_VORBIS_10}
    BINARIES = ("oggenc", "oggdec")
    REPLAYGAIN_BINARIES = ("vorbisgain", )

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)
        self.__sample_rate__ = 0
        self.__channels__ = 0
        try:
            self.__read_identification__()
        except IOError, msg:
            raise InvalidVorbis(str(msg))

    @classmethod
    def is_type(cls, file):
        """returns True if the given file object describes this format

        takes a seekable file pointer rewound to the start of the file"""

        header = file.read(0x23)

        return (header.startswith('OggS') and
                header[0x1C:0x23] == '\x01vorbis')

    def __read_identification__(self):
        from .bitstream import BitstreamReader

        f = open(self.filename, "rb")
        try:
            ogg_reader = BitstreamReader(f, 1)
            (magic_number,
             version,
             header_type,
             granule_position,
             self.__serial_number__,
             page_sequence_number,
             checksum,
             segment_count) = ogg_reader.parse("4b 8u 8u 64S 32u 32u 32u 8u")

            if (magic_number != 'OggS'):
                from .text import ERR_OGG_INVALID_MAGIC_NUMBER
                raise InvalidFLAC(ERR_OGG_INVALID_MAGIC_NUMBER)
            if (version != 0):
                from .text import ERR_OGG_INVALID_VERSION
                raise InvalidFLAC(ERR_OGG_INVALID_VERSION)

            segment_length = ogg_reader.read(8)

            (vorbis_type,
             header,
             version,
             self.__channels__,
             self.__sample_rate__,
             maximum_bitrate,
             nominal_bitrate,
             minimum_bitrate,
             blocksize0,
             blocksize1,
             framing) = ogg_reader.parse(
                "8u 6b 32u 8u 32u 32u 32u 32u 4u 4u 1u")

            if (vorbis_type != 1):
                from .text import ERR_VORBIS_INVALID_TYPE
                raise InvalidVorbis(ERR_VORBIS_INVALID_TYPE)
            if (header != 'vorbis'):
                from .text import ERR_VORBIS_INVALID_HEADER
                raise InvalidVorbis(ERR_VORBIS_INVALID_HEADER)
            if (version != 0):
                from .text import ERR_VORBIS_INVALID_VERSION
                raise InvalidVorbis(ERR_VORBIS_INVALID_VERSION)
            if (framing != 1):
                from .text import ERR_VORBIS_INVALID_FRAMING_BIT
                raise InvalidVorbis(ERR_VORBIS_INVALID_FRAMING_BIT)
        finally:
            f.close()

    def lossless(self):
        """returns False"""

        return False

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return 16

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        if (self.channels() == 1):
            return ChannelMask.from_fields(
                front_center=True)
        elif (self.channels() == 2):
            return ChannelMask.from_fields(
                front_left=True, front_right=True)
        elif (self.channels() == 3):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True)
        elif (self.channels() == 4):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True)
        elif (self.channels() == 5):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True,
                back_left=True, back_right=True)
        elif (self.channels() == 6):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True,
                back_left=True, back_right=True,
                low_frequency=True)
        elif (self.channels() == 7):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True,
                side_left=True, side_right=True,
                back_center=True, low_frequency=True)
        elif (self.channels() == 8):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                side_left=True, side_right=True,
                back_left=True, back_right=True,
                front_center=True, low_frequency=True)
        else:
            return ChannelMask(0)

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        from .bitstream import BitstreamReader
        from .ogg import OggStreamReader

        pcm_samples = 0
        for (granule_position,
             segments,
             continuation,
             first_page,
             last_page) in OggStreamReader(
            BitstreamReader(file(self.filename, "rb"), 1)).pages():
            if (granule_position >= 0):
                pcm_samples = granule_position
        return pcm_samples

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from . import PCMReader
        from . import BIN
        import subprocess
        import os

        sub = subprocess.Popen([BIN['oggdec'], '-Q',
                                '-b', str(16),
                                '-e', str(0),
                                '-s', str(1),
                                '-R',
                                '-o', '-',
                                self.filename],
                               stdout=subprocess.PIPE,
                               stderr=file(os.devnull, "a"))

        pcmreader = PCMReader(sub.stdout,
                              sample_rate=self.sample_rate(),
                              channels=self.channels(),
                              channel_mask=int(self.channel_mask()),
                              bits_per_sample=self.bits_per_sample(),
                              process=sub)

        if (self.channels() <= 2):
            return pcmreader
        elif (self.channels() <= 8):
            #these mappings transform Vorbis order into ChannelMask order
            from . import ReorderedPCMReader

            standard_channel_mask = self.channel_mask()
            vorbis_channel_mask = VorbisChannelMask(self.channel_mask())
            return ReorderedPCMReader(
                pcmreader,
                [vorbis_channel_mask.channels().index(channel) for channel in
                 standard_channel_mask.channels()])
        else:
            return pcmreader

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """returns a PCMReader object containing the track's PCM data"""

        from . import transfer_framelist_data
        from . import BIN
        from . import ignore_sigint
        from . import EncodingError
        from . import DecodingError
        from . import UnsupportedChannelMask
        from . import __default_quality__
        import subprocess
        import os

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        devnull = file(os.devnull, 'ab')

        sub = subprocess.Popen([BIN['oggenc'], '-Q',
                                '-r',
                                '-B', str(pcmreader.bits_per_sample),
                                '-C', str(pcmreader.channels),
                                '-R', str(pcmreader.sample_rate),
                                '--raw-endianness', str(0),
                                '-q', compression,
                                '-o', filename, '-'],
                               stdin=subprocess.PIPE,
                               stdout=devnull,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)

        if ((pcmreader.channels <= 2) or (int(pcmreader.channel_mask) == 0)):
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

        elif (pcmreader.channels <= 8):
            if (int(pcmreader.channel_mask) in
                (0x7,      # FR, FC, FL
                 0x33,     # FR, FL, BR, BL
                 0x37,     # FR, FC, FL, BL, BR
                 0x3f,     # FR, FC, FL, BL, BR, LFE
                 0x70f,    # FL, FC, FR, SL, SR, BC, LFE
                 0x63f)):  # FL, FC, FR, SL, SR, BL, BR, LFE

                standard_channel_mask = ChannelMask(pcmreader.channel_mask)
                vorbis_channel_mask = VorbisChannelMask(standard_channel_mask)
            else:
                raise UnsupportedChannelMask(filename,
                                             int(pcmreader.channel_mask))

            try:
                from . import ReorderedPCMReader

                transfer_framelist_data(ReorderedPCMReader(
                        pcmreader,
                        [standard_channel_mask.channels().index(channel)
                         for channel in vorbis_channel_mask.channels()]),
                                        sub.stdin.write)
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

        else:
            raise UnsupportedChannelMask(filename,
                                         int(pcmreader.channel_mask))

        try:
            pcmreader.close()
        except DecodingError, err:
            raise EncodingError(err.error_message)

        sub.stdin.close()
        devnull.close()

        if (sub.wait() == 0):
            return VorbisAudio(filename)
        else:
            raise EncodingError(u"unable to encode file with oggenc")

    def update_metadata(self, metadata):
        """takes this track's current MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        raises IOError if unable to write the file
        """

        from .bitstream import BitstreamReader
        from .bitstream import BitstreamRecorder
        from .bitstream import BitstreamWriter
        from .ogg import OggStreamWriter
        from .ogg import OggStreamReader
        from .ogg import read_ogg_packets_data
        from . import iter_first
        from .vorbiscomment import VorbisComment

        if (metadata is None):
            return

        if (not isinstance(metadata, VorbisComment)):
            from .text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        original_reader = BitstreamReader(open(self.filename, "rb"), 1)
        original_ogg = OggStreamReader(original_reader)
        original_serial_number = original_ogg.serial_number
        original_packets = read_ogg_packets_data(original_reader)

        #save the current file's identification page/packet
        #(the ID packet is always fixed size, and fits in one page)
        identification_page = original_ogg.read_page()

        #discard the current file's comment packet
        original_packets.next()

        #save the current file's setup packet
        setup_packet = original_packets.next()

        #save all the subsequent Ogg pages
        data_pages = list(original_ogg.pages())

        del(original_ogg)
        del(original_packets)
        original_reader.close()

        updated_writer = BitstreamWriter(open(self.filename, "wb"), 1)
        updated_ogg = OggStreamWriter(updated_writer, original_serial_number)

        #write the identification packet in its own page
        updated_ogg.write_page(*identification_page)

        #write the new comment packet in its own page(s)
        comment_writer = BitstreamRecorder(1)
        comment_writer.build("8u 6b", (3, "vorbis"))
        vendor_string = metadata.vendor_string.encode('utf-8')
        comment_writer.build("32u %db" % (len(vendor_string)),
                             (len(vendor_string), vendor_string))
        comment_writer.write(32, len(metadata.comment_strings))
        for comment_string in metadata.comment_strings:
            comment_string = comment_string.encode('utf-8')
            comment_writer.build("32u %db" % (len(comment_string)),
                                 (len(comment_string), comment_string))

        comment_writer.build("1u a", (1,))

        for (first_page, segments) in iter_first(
            updated_ogg.segments_to_pages(
                updated_ogg.packet_to_segments(comment_writer.data()))):
            updated_ogg.write_page(0, segments, 0 if first_page else 1, 0, 0)

        #write the setup packet in its own page(s)
        for (first_page, segments) in iter_first(
            updated_ogg.segments_to_pages(
                updated_ogg.packet_to_segments(setup_packet))):
            updated_ogg.write_page(0, segments, 0 if first_page else 1, 0, 0)

        #write the subsequent Ogg pages
        for page in data_pages:
            updated_ogg.write_page(*page)

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        from .vorbiscomment import VorbisComment

        if (metadata is not None):
            metadata = VorbisComment.converted(metadata)

            old_metadata = self.get_metadata()

            metadata.vendor_string = old_metadata.vendor_string

            #remove REPLAYGAIN_* tags from new metadata (if any)
            for key in [u"REPLAYGAIN_TRACK_GAIN",
                        u"REPLAYGAIN_TRACK_PEAK",
                        u"REPLAYGAIN_ALBUM_GAIN",
                        u"REPLAYGAIN_ALBUM_PEAK",
                        u"REPLAYGAIN_REFERENCE_LOUDNESS"]:
                try:
                    metadata[key] = old_metadata[key]
                except KeyError:
                    metadata[key] = []

            self.update_metadata(metadata)

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from .bitstream import BitstreamReader
        from .ogg import read_ogg_packets
        from .vorbiscomment import VorbisComment

        packets = read_ogg_packets(
            BitstreamReader(open(self.filename, "rb"), 1))

        identification = packets.next()
        comment = packets.next()

        (packet_type, packet_header) = comment.parse("8u 6b")
        if ((packet_type != 3) or (packet_header != 'vorbis')):
            return None
        else:
            vendor_string = \
                comment.read_bytes(comment.read(32)).decode('utf-8')
            comment_strings = [
                comment.read_bytes(comment.read(32)).decode('utf-8')
                for i in xrange(comment.read(32))]
            if (comment.read(1) == 1):   # framing bit
                return VorbisComment(comment_strings, vendor_string)
            else:
                return None

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from . import MetaData

        #the vorbis comment packet is required,
        #so simply zero out its contents
        self.set_metadata(MetaData())

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """adds ReplayGain values to a list of filename strings

        all the filenames must be of this AudioFile type
        raises ValueError if some problem occurs during ReplayGain application
        """

        from . import BIN
        from . import open_files
        import subprocess
        import os

        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track, cls)]

        if (progress is not None):
            progress(0, 1)

        if ((len(track_names) > 0) and
            BIN.can_execute(BIN['vorbisgain'])):
            devnull = file(os.devnull, 'ab')

            sub = subprocess.Popen([BIN['vorbisgain'],
                                    '-q', '-a'] + track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()
            devnull.close()

        if (progress is not None):
            progress(1, 1)

    @classmethod
    def can_add_replay_gain(cls, audiofiles):
        """given a list of audiofiles,
        returns True if this class can add ReplayGain to those files
        returns False if not"""

        for audiofile in audiofiles:
            if (not isinstance(audiofile, VorbisAudio)):
                return False
        else:
            from . import BIN

            return BIN.can_execute(BIN['vorbisgain'])

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

        from . import ReplayGain

        vorbis_metadata = self.get_metadata()

        if ((vorbis_metadata is not None) and
            (set(['REPLAYGAIN_TRACK_PEAK', 'REPLAYGAIN_TRACK_GAIN',
                  'REPLAYGAIN_ALBUM_PEAK', 'REPLAYGAIN_ALBUM_GAIN']).issubset(
                    vorbis_metadata.keys()))):  # we have ReplayGain data
            try:
                return ReplayGain(
                    vorbis_metadata['REPLAYGAIN_TRACK_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_TRACK_PEAK'][0],
                    vorbis_metadata['REPLAYGAIN_ALBUM_GAIN'][0][0:-len(" dB")],
                    vorbis_metadata['REPLAYGAIN_ALBUM_PEAK'][0])
            except (IndexError, ValueError):
                return None
        else:
            return None

    def verify(self, progress=None):
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        #Ogg stream verification is likely to be so fast
        #that individual calls to progress() are
        #a waste of time.
        if (progress is not None):
            progress(0, 1)

        try:
            f = open(self.filename, 'rb')
        except IOError, err:
            raise InvalidVorbis(str(err))
        try:
            try:
                result = verify_ogg_stream(f)
                if (progress is not None):
                    progress(1, 1)
                return result
            except (IOError, ValueError), err:
                raise InvalidVorbis(str(err))
        finally:
            f.close()


class VorbisChannelMask(ChannelMask):
    """the Vorbis-specific channel mapping"""

    def __repr__(self):
        return "VorbisChannelMask(%s)" % \
            ",".join(["%s=%s" % (field, getattr(self, field))
                      for field in self.SPEAKER_TO_MASK.keys()
                      if (getattr(self, field))])

    def channels(self):
        """returns a list of speaker strings this mask contains

        returned in the order in which they should appear
        in the PCM stream
        """

        count = len(self)
        if (count == 1):
            return ["front_center"]
        elif (count == 2):
            return ["front_left", "front_right"]
        elif (count == 3):
            return ["front_left", "front_center", "front_right"]
        elif (count == 4):
            return ["front_left", "front_right",
                    "back_left", "back_right"]
        elif (count == 5):
            return ["front_left", "front_center", "front_right",
                    "back_left", "back_right"]
        elif (count == 6):
            return ["front_left", "front_center", "front_right",
                    "back_left", "back_right", "low_frequency"]
        elif (count == 7):
            return ["front_left", "front_center", "front_right",
                    "side_left", "side_right", "back_center",
                    "low_frequency"]
        elif (count == 8):
            return ["front_left", "front_center", "front_right",
                    "side_left", "side_right",
                    "back_left", "back_right", "low_frequency"]
        else:
            return []
