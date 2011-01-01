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


from audiotools import (AudioFile, InvalidFile, Con, subprocess, BIN,
                        open_files, os, ReplayGain, ignore_sigint,
                        transfer_data, transfer_framelist_data,
                        BufferedPCMReader, Image, MetaData, sheet_to_unicode,
                        calculate_replay_gain, ApeTagItem,
                        EncodingError, DecodingError, PCMReaderError,
                        PCMReader, ChannelMask, UnsupportedChannelMask,
                        InvalidWave, __default_quality__,
                        WaveContainer)
from __wav__ import WaveAudio, WaveReader
from __ape__ import ApeTaggedAudio, ApeTag, __number_pair__
import gettext

gettext.install("audiotools", unicode=True)


class InvalidWavPack(InvalidFile):
    pass


class __24BitsLE__(Con.Adapter):
    def _encode(self, value, context):
        return  chr(value & 0x0000FF) + \
                chr((value & 0x00FF00) >> 8) + \
                chr((value & 0xFF0000) >> 16)

    def _decode(self, obj, context):
        return (ord(obj[2]) << 16) | (ord(obj[1]) << 8) | ord(obj[0])


def ULInt24(name):
    return __24BitsLE__(Con.Bytes(name, 3))


def __riff_chunk_ids__(data):
    import cStringIO

    total_size = len(data)
    data = cStringIO.StringIO(data)
    header = WaveAudio.WAVE_HEADER.parse_stream(data)

    while (data.tell() < total_size):
        chunk_header = WaveAudio.CHUNK_HEADER.parse_stream(data)
        chunk_size = chunk_header.chunk_length
        if ((chunk_size & 1) == 1):
            chunk_size += 1
        data.seek(chunk_size, 1)
        yield chunk_header.chunk_id


#######################
#WavPack APEv2
#######################


class WavPackAPEv2(ApeTag):
    """A WavPack-specific APEv2 implementation with minor differences."""

    def __init__(self, tags, tag_length=None, frame_count=0):
        """Constructs an ApeTag from a list of ApeTagItem objects.

        tag_length is an optional total length integer.
        frame_count is an optional number of PCM frames
        to be used by cuesheets."""

        ApeTag.__init__(self, tags=tags, tag_length=tag_length)
        self.frame_count = frame_count

    def __comment_pairs__(self):
        return filter(lambda pair: pair[0] != 'Cuesheet',
                      ApeTag.__comment_pairs__(self))

    def __unicode__(self):
        if ('Cuesheet' not in self.keys()):
            return ApeTag.__unicode__(self)
        else:
            import cue

            try:
                return u"%s%sCuesheet:\n%s" % \
                    (MetaData.__unicode__(self),
                     os.linesep * 2,
                     sheet_to_unicode(
                            cue.parse(
                                cue.tokens(unicode(self['Cuesheet']).encode(
                                        'ascii', 'replace'))),
                            self.frame_count))
            except cue.CueException:
                return ApeTag.__unicode__(self)

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to a WavPackAPEv2 object."""

        if ((metadata is None) or (isinstance(metadata, WavPackAPEv2))):
            return metadata
        elif (isinstance(metadata, ApeTag)):
            return WavPackAPEv2(metadata.tags)
        else:
            return WavPackAPEv2(ApeTag.converted(metadata).tags)

WavePackAPEv2 = WavPackAPEv2

#######################
#WavPack
#######################


class WavPackAudio(ApeTaggedAudio, WaveContainer):
    """A WavPack audio file."""

    SUFFIX = "wv"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "standard"
    COMPRESSION_MODES = ("veryfast", "fast", "standard", "high", "veryhigh")

    APE_TAG_CLASS = WavPackAPEv2

    HEADER = Con.Struct("wavpackheader",
                        Con.Const(Con.String("id", 4), 'wvpk'),
                        Con.ULInt32("block_size"),
                        Con.ULInt16("version"),
                        Con.ULInt8("track_number"),
                        Con.ULInt8("index_number"),
                        Con.ULInt32("total_samples"),
                        Con.ULInt32("block_index"),
                        Con.ULInt32("block_samples"),
                        Con.Embed(
            Con.BitStruct("flags",
                          Con.Flag("floating_point_data"),
                          Con.Flag("hybrid_noise_shaping"),
                          Con.Flag("cross_channel_decorrelation"),
                          Con.Flag("joint_stereo"),
                          Con.Flag("hybrid_mode"),
                          Con.Flag("mono_output"),
                          Con.Bits("bits_per_sample", 2),

                          Con.Bits("left_shift_data_low", 3),
                          Con.Flag("final_block_in_sequence"),
                          Con.Flag("initial_block_in_sequence"),
                          Con.Flag("hybrid_noise_balanced"),
                          Con.Flag("hybrid_mode_control_bitrate"),
                          Con.Flag("extended_size_integers"),

                          Con.Bit("sampling_rate_low"),
                          Con.Bits("maximum_magnitude", 5),
                          Con.Bits("left_shift_data_high", 2),

                          Con.Flag("reserved2"),
                          Con.Flag("false_stereo"),
                          Con.Flag("use_IIR"),
                          Con.Bits("reserved1", 2),
                          Con.Bits("sampling_rate_high", 3))),
                        Con.ULInt32("crc"))

    SUB_HEADER = Con.Struct("wavpacksubheader",
                            Con.Embed(
            Con.BitStruct("flags",
                          Con.Flag("large_block"),
                          Con.Flag("actual_size_1_less"),
                          Con.Flag("nondecoder_data"),
                          Con.Bits("metadata_function", 5))),
                            Con.IfThenElse('size',
                                           lambda ctx: ctx['large_block'],
                                           ULInt24('s'),
                                           Con.Byte('s')))

    BITS_PER_SAMPLE = (8, 16, 24, 32)
    SAMPLING_RATE = (6000,  8000,  9600,   11025,
                     12000, 16000, 22050,  24000,
                     32000, 44100, 48000,  64000,
                     88200, 96000, 192000, 0)

    __options__ = {"veryfast": {"block_size": 44100,
                                "joint_stereo": True,
                                "false_stereo": True,
                                "wasted_bits": True,
                                "decorrelation_passes": 1},
                   "fast": {"block_size": 44100,
                            "joint_stereo": True,
                            "false_stereo": True,
                            "wasted_bit": True,
                            "decorrelation_passes": 2},
                   "standard": {"block_size": 44100,
                                "joint_stereo": True,
                                "false_stereo": True,
                                "wasted_bits": True,
                                "decorrelation_passes": 5},
                   "high": {"block_size": 44100,
                            "joint_stereo": True,
                            "false_stereo": True,
                            "wasted_bits": True,
                            "decorrelation_passes": 10},
                   "veryhigh": {"block_size": 44100,
                                "joint_stereo": True,
                                "false_stereo": True,
                                "wasted_bits": True,
                                "decorrelation_passes": 16}}

    def __init__(self, filename):
        """filename is a plain string."""

        self.filename = filename
        self.__samplerate__ = 0
        self.__channels__ = 0
        self.__bitspersample__ = 0
        self.__total_frames__ = 0

        try:
            self.__read_info__()
        except IOError, msg:
            raise InvalidWavPack(str(msg))

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        return file.read(4) == 'wvpk'

    def lossless(self):
        """Returns True."""

        return True

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        if ((self.__channels__ == 1) or (self.__channels__ == 2)):
            return ChannelMask.from_channels(self.__channels__)
        else:
            for (block_id, nondecoder, data) in self.sub_frames():
                if ((block_id == 0xD) and not nondecoder):
                    mask = 0
                    for byte in reversed(map(ord, data[1:])):
                        mask = (mask << 8) | byte
                    return ChannelMask(mask)
            else:
                return ChannelMask(0)

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        metadata = ApeTaggedAudio.get_metadata(self)
        if (metadata is not None):
            metadata.frame_count = self.total_frames()
        return metadata

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        for (sub_header, nondecoder, data) in self.sub_frames():
            if ((sub_header == 1) and nondecoder):
                if (set(__riff_chunk_ids__(data)) != set(['fmt ', 'data'])):
                    return True
            elif ((sub_header == 2) and nondecoder):
                return True
        else:
            return False

    def frames(self):
        """Yields (header, data) tuples of WavPack frames.

        header is a Container parsed from WavPackAudio.HEADER.
        data is a binary string.
        """

        f = file(self.filename)
        total_size = os.path.getsize(self.filename)
        try:
            while (f.tell() < total_size):
                try:
                    header = WavPackAudio.HEADER.parse(f.read(
                            WavPackAudio.HEADER.sizeof()))
                except Con.ConstError:
                    break

                data = f.read(header.block_size - 24)

                yield (header, data)
        finally:
            f.close()

    def sub_frames(self):
        """Yields (function,nondecoder,data) tuples.

        function is an integer.
        nondecoder is a boolean indicating non-decoder data.
        data is a binary string.
        """

        import cStringIO

        for (header, data) in self.frames():
            total_size = len(data)
            data = cStringIO.StringIO(data)
            while (data.tell() < total_size):
                sub_header = WavPackAudio.SUB_HEADER.parse_stream(data)
                if (sub_header.actual_size_1_less):
                    yield (sub_header.metadata_function,
                           sub_header.nondecoder_data,
                           data.read((sub_header.size * 2) - 1))
                    data.read(1)
                else:
                    yield (sub_header.metadata_function,
                           sub_header.nondecoder_data,
                           data.read(sub_header.size * 2))

    def __read_info__(self):
        f = file(self.filename)
        try:
            try:
                header = WavPackAudio.HEADER.parse(f.read(
                    WavPackAudio.HEADER.sizeof()))
            except Con.ConstError:
                raise InvalidWavPack(_(u'WavPack header ID invalid'))
            except Con.FieldError:
                raise InvalidWavPack(_(u'WavPack header ID invalid'))

            self.__samplerate__ = WavPackAudio.SAMPLING_RATE[
                (header.sampling_rate_high << 1) |
                header.sampling_rate_low]
            self.__bitspersample__ = WavPackAudio.BITS_PER_SAMPLE[
                header.bits_per_sample]
            self.__total_frames__ = header.total_samples

            self.__channels__ = 0

            #go through as many headers as necessary
            #to count the number of channels
            if (header.mono_output):
                self.__channels__ += 1
            else:
                self.__channels__ += 2

            while (not header.final_block_in_sequence):
                f.seek(header.block_size - 24, 1)
                header = WavPackAudio.HEADER.parse(f.read(
                        WavPackAudio.HEADER.sizeof()))
                if (header.mono_output):
                    self.__channels__ += 1
                else:
                    self.__channels__ += 2
        finally:
            f.close()

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bitspersample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__total_frames__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__samplerate__

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new WavPackAudio object."""

        from . import encoders

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        try:
            encoders.encode_wavpack(filename,
                                    BufferedPCMReader(pcmreader),
                                    **cls.__options__[compression])

            return cls(filename)
        except (ValueError, IOError), msg:
            cls.__unlink__(filename)
            raise EncodingError(str(msg))
        except Exception, err:
            cls.__unlink__(filename)
            raise err

    def to_wave(self, wave_filename):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        from . import decoders

        try:
            f = open(wave_filename, 'wb')
        except IOError, msg:
            raise EncodingError(str(msg))

        (head, tail) = self.pcm_split()

        try:
            f.write(head)
            transfer_framelist_data(
                decoders.WavPackDecoder(self.filename),
                f.write)
            f.write(tail)
            f.close()
        except IOError, msg:
            self.__unlink__(wave_filename)
            raise EncodingError(str(msg))

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        from . import decoders

        try:
            return decoders.WavPackDecoder(self.filename)
        except (IOError, ValueError), msg:
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.__samplerate__,
                                  channels=self.__channels__,
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.__bitspersample__)

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new WavPackAudio object."""

        from . import encoders

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        wave = WaveAudio(wave_filename)

        (head, tail) = wave.pcm_split()

        try:
            encoders.encode_wavpack(filename,
                                    wave.to_pcm(),
                                    wave_header=head,
                                    wave_footer=tail,
                                    **cls.__options__[compression])

            return cls(filename)
        except (ValueError, IOError), msg:
            cls.__unlink__(filename)
            raise EncodingError(str(msg))
        except Exception, err:
            cls.__unlink__(filename)
            raise err


    def pcm_split(self):
        """Returns a pair of data strings before and after PCM data."""

        head = ""
        tail = ""

        for (sub_block_id, nondecoder, data) in self.sub_frames():
            if ((sub_block_id == 1) and nondecoder):
                head = data
            elif ((sub_block_id == 2) and nondecoder):
                tail = data

        return (head, tail)

    @classmethod
    def add_replay_gain(cls, filenames):
        """Adds ReplayGain values to a list of filename strings.

        All the filenames must be of this AudioFile type.
        Raises ValueError if some problem occurs during ReplayGain application.
        """

        tracks = [track for track in open_files(filenames) if
                  isinstance(track, cls)]

        if (len(tracks) > 0):
            for (track,
                 track_gain,
                 track_peak,
                 album_gain,
                 album_peak) in calculate_replay_gain(tracks):
                metadata = track.get_metadata()
                if (metadata is None):
                    metadata = WavPackAPEv2([])
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
                track.set_metadata(metadata)

    @classmethod
    def can_add_replay_gain(cls):
        """Returns True."""

        return True

    @classmethod
    def lossless_replay_gain(cls):
        """Returns True."""

        return True

    def replay_gain(self):
        """Returns a ReplayGain object of our ReplayGain values.

        Returns None if we have no values."""

        metadata = self.get_metadata()
        if (metadata is None):
            return None

        if (set(['replaygain_track_gain', 'replaygain_track_peak',
                 'replaygain_album_gain', 'replaygain_album_peak']).issubset(
                metadata.keys())):  # we have ReplayGain data
            try:
                return ReplayGain(
                    unicode(metadata['replaygain_track_gain'])[0:-len(" dB")],
                    unicode(metadata['replaygain_track_peak']),
                    unicode(metadata['replaygain_album_gain'])[0:-len(" dB")],
                    unicode(metadata['replaygain_album_peak']))
            except ValueError:
                return None
        else:
            return None

    def get_cuesheet(self):
        """Returns the embedded Cuesheet-compatible object, or None.

        Raises IOError if a problem occurs when reading the file."""

        import cue

        metadata = self.get_metadata()

        if ((metadata is not None) and ('Cuesheet' in metadata.keys())):
            try:
                return cue.parse(cue.tokens(
                        unicode(metadata['Cuesheet']).encode('utf-8',
                                                             'replace')))
            except cue.CueException:
                #unlike FLAC, just because a cuesheet is embedded
                #does not mean it is compliant
                return None
        else:
            return None

    def set_cuesheet(self, cuesheet):
        """Imports cuesheet data from a Cuesheet-compatible object.

        This are objects with catalog(), ISRCs(), indexes(), and pcm_lengths()
        methods.  Raises IOError if an error occurs setting the cuesheet."""

        import os.path
        import cue

        if (cuesheet is None):
            return

        metadata = self.get_metadata()
        if (metadata is None):
            metadata = WavPackAPEv2.converted(MetaData())

        metadata['Cuesheet'] = WavPackAPEv2.ITEM.string('Cuesheet',
                                                        cue.Cuesheet.file(
                cuesheet,
                os.path.basename(self.filename)).decode('ascii', 'replace'))
        self.set_metadata(metadata)

