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


from audiotools import (AudioFile, InvalidFile, ChannelMask, PCMReader,
                        Con, BUFFER_SIZE, transfer_data,
                        transfer_framelist_data,
                        __capped_stream_reader__, FILENAME_FORMAT,
                        BIN, open_files, os, subprocess, cStringIO,
                        EncodingError, DecodingError, UnsupportedChannelMask,
                        WaveContainer, to_pcm_progress)
import os.path
import gettext
from . import pcm

gettext.install("audiotools", unicode=True)

#######################
#RIFF WAVE
#######################


class WaveReader(PCMReader):
    """A subclass of PCMReader for reading wave file contents."""

    def __init__(self, wave_file,
                 sample_rate, channels, channel_mask, bits_per_sample,
                 process=None):
        """wave_file should be a file-like stream of wave data.

        sample_rate, channels, channel_mask and bits_per_sample are ints.
        If present, process is waited for when close() is called.
        """

        self.file = wave_file
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.channel_mask = channel_mask

        self.process = process

        from .bitstream import BitstreamReader

        #build a capped reader for the data chunk
        wave_reader = BitstreamReader(wave_file, 1)
        try:
            (riff, wave) = wave_reader.parse("4b 32p 4b")
            if (riff != 'RIFF'):
                raise InvalidWave(_(u"Not a RIFF WAVE file"))
            elif (wave != 'WAVE'):
                raise InvalidWave(_(u"Invalid RIFF WAVE file"))

            while (True):
                (chunk_id, chunk_size) = wave_reader.parse("4b 32u")
                if (chunk_id == 'data'):
                    self.wave = __capped_stream_reader__(self.file,
                                                         chunk_size)
                    self.data_chunk_length = chunk_size
                    break
                else:
                    wave_reader.skip_bytes(chunk_size)
                    if (chunk_size % 2):
                        wave_reader.skip(1)

        except IOError:
            raise InvalidWave(_(u"data chunk not found"))

    def read(self, bytes):
        """Try to read a pcm.FrameList of size "bytes"."""

        #align bytes downward if an odd number is read in
        bytes -= (bytes % (self.channels * self.bits_per_sample / 8))
        bytes = max(bytes, self.channels * self.bits_per_sample / 8)
        pcm_data = self.wave.read(bytes)
        if ((len(pcm_data) == 0) and (self.data_chunk_length > 0)):
            raise IOError("data chunk ends prematurely")
        else:
            self.data_chunk_length -= len(pcm_data)

        try:
            return pcm.FrameList(pcm_data,
                                 self.channels,
                                 self.bits_per_sample,
                                 False,
                                 self.bits_per_sample != 8)
        except ValueError:
            raise IOError("data chunk ends prematurely")

    def close(self):
        """Closes the stream for reading.

        Any subprocess is waited for also so for proper cleanup."""

        self.wave.close()
        if (self.process is not None):
            if (self.process.wait() != 0):
                raise DecodingError()


class TempWaveReader(WaveReader):
    """A subclass of WaveReader for reading wave data from temporary files."""

    def __init__(self, tempfile):
        """tempfile should be a NamedTemporaryFile.

        Its contents are used to populate the rest of the fields."""

        wave = WaveAudio(tempfile.name)
        WaveReader.__init__(self,
                            tempfile,
                            sample_rate=wave.sample_rate(),
                            channels=wave.channels(),
                            channel_mask=int(wave.channel_mask()),
                            bits_per_sample=wave.bits_per_sample())
        self.tempfile = tempfile

    def close(self):
        """Closes the input stream and temporary file."""

        WaveReader.close(self)
        self.tempfile.close()


class InvalidWave(InvalidFile):
    """Raises during initialization time if a wave file is invalid."""

    pass


def __blank_channel_mask__():
    c = Con.Container(undefined=0, undefined2=0)

    for attr in ('front_right_of_center',
                 'front_left_of_center',
                 'rear_right',
                 'rear_left',
                 'LFE',
                 'front_center',
                 'front_right',
                 'front_left',
                 'top_back_left',
                 'top_front_right',
                 'top_front_center',
                 'top_front_left',
                 'top_center',
                 'side_right',
                 'side_left',
                 'rear_center',
                 'top_back_right',
                 'top_back_center'):
        setattr(c, attr, False)

    return c


def __channel_mask__(filename, mask, channel_count):
    mask = ChannelMask(mask)
    c = __blank_channel_mask__()

    if (mask.defined()):
        attr_map = {"front_left": 'front_left',
                    "front_right": 'front_right',
                    "front_center": 'front_center',
                    "low_frequency": 'LFE',
                    "back_left": 'rear_left',
                    "back_right": 'rear_right',
                    "front_left_of_center": 'front_left_of_center',
                    "front_right_of_center": 'front_right_of_center',
                    "back_center": 'rear_center',
                    "side_left": 'side_left',
                    "side_right": 'side_right',
                    "top_center": 'top_center',
                    "top_front_left": 'top_front_left',
                    "top_front_center": 'top_front_center',
                    "top_front_right": 'top_front_right',
                    "top_back_left": 'top_back_left',
                    "top_back_center": 'top_back_center',
                    "top_back_right": 'top_back_right'}

        for channel in mask.channels():
            setattr(c, attr_map[channel], True)
    else:
        attr_map = ['front_left',
                    'front_right',
                    'front_center',
                    'LFE',
                    'rear_left',
                    'rear_right',
                    'front_left_of_center',
                    'front_right_of_center',
                    'rear_center',
                    'side_left',
                    'side_right',
                    'top_center',
                    'top_front_left',
                    'top_front_center',
                    'top_front_right',
                    'top_back_left',
                    'top_back_center',
                    'top_back_right']
        if (channel_count <= len(attr_map)):
            for channel in attr_map[0:channel_count]:
                setattr(c, channel, True)
        else:
            raise UnsupportedChannelMask(filename, mask)

    return c


class __ASCII_String__(Con.Validator):
    """Validates that its data string is printable ASCII."""

    PRINTABLE_ASCII = set([chr(i) for i in xrange(0x20, 0x7E + 1)])

    def _validate(self, obj, context):
        return set(obj).issubset(self.PRINTABLE_ASCII)


class WaveAudio(WaveContainer):
    """A waveform audio file."""

    SUFFIX = "wav"
    NAME = SUFFIX

    WAVE_HEADER = Con.Struct("wave_header",
                             Con.Const(Con.Bytes("wave_id", 4), 'RIFF'),
                             Con.ULInt32("wave_size"),
                             Con.Const(Con.Bytes("riff_type", 4), 'WAVE'))

    CHUNK_HEADER = Con.Struct("chunk_header",
                              __ASCII_String__(Con.Bytes("chunk_id", 4)),
                              Con.ULInt32("chunk_length"))

    FMT_CHUNK = Con.Struct("fmt_chunk",
                           Con.ULInt16("compression"),
                           Con.ULInt16("channels"),
                           Con.ULInt32("sample_rate"),
                           Con.ULInt32("bytes_per_second"),
                           Con.ULInt16("block_align"),
                           Con.ULInt16("bits_per_sample"),
                           Con.If(lambda ctx: ctx['compression'] == 0xFFFE,
                                  Con.Embed(
                Con.Struct('extensible',
                           Con.ULInt16('cb_size'),
                           Con.ULInt16('valid_bits_per_sample'),
                           Con.BitStruct('channel_mask',
                                         #0x80
                                         Con.Flag('front_right_of_center'),

                                         #0x40
                                         Con.Flag('front_left_of_center'),

                                         #0x20
                                         Con.Flag('rear_right'),

                                         #0x10
                                         Con.Flag('rear_left'),

                                         #0x8
                                         Con.Flag('LFE'),

                                         #0x4
                                         Con.Flag('front_center'),

                                         #0x2
                                         Con.Flag('front_right'),

                                         #0x1
                                         Con.Flag('front_left'),

                                         #0x8000
                                         Con.Flag('top_back_left'),

                                         #0x4000
                                         Con.Flag('top_front_right'),

                                         #0x2000
                                         Con.Flag('top_front_center'),

                                         #0x1000
                                         Con.Flag('top_front_left'),

                                         #0x800
                                         Con.Flag('top_center'),

                                         #0x400
                                         Con.Flag('side_right'),

                                         #0x200
                                         Con.Flag('side_left'),

                                         #0x100
                                         Con.Flag('rear_center'),

                                         #0x800000
                                         #0x400000
                                         #0x200000
                                         #0x100000
                                         #0x80000
                                         #0x40000
                                         Con.Bits('undefined', 6),

                                         #0x20000
                                         Con.Flag('top_back_right'),

                                         #0x10000
                                         Con.Flag('top_back_center'),

                                         Con.Bits('undefined2', 8)),
                           Con.String('sub_format', 16)))))

    PRINTABLE_ASCII = frozenset([chr(i) for i in xrange(0x20, 0x7E + 1)])

    def __init__(self, filename):
        """filename is a plain string."""

        AudioFile.__init__(self, filename)

        self.__wavtype__ = 0
        self.__channels__ = 0
        self.__samplespersec__ = 0
        self.__bytespersec__ = 0
        self.__blockalign__ = 0
        self.__bitspersample__ = 0
        self.__data_size__ = 0
        self.__channel_mask__ = ChannelMask(0)

        self.__chunk_ids__ = []

        from .bitstream import BitstreamReader

        try:
            wave_file = BitstreamReader(open(filename, 'rb'), 1)
            try:
                (riff, total_size, wave) = wave_file.parse("4b 32u 4b")
                if (riff != 'RIFF'):
                    raise InvalidWave(_(u"Not a RIFF WAVE file"))
                elif (wave != 'WAVE'):
                    raise InvalidWave(_(u"Invalid RIFF WAVE file"))
                else:
                    total_size -= 4

                while (total_size > 0):
                    (chunk_id, chunk_size) = wave_file.parse("4b 32u")
                    self.__chunk_ids__.append(chunk_id)

                    if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                        raise InvalidWave(_(u"Invalid RIFF WAVE chunk ID"))
                    else:
                        total_size -= 8

                    if (chunk_id == 'fmt '):
                        (compression,
                         self.__channels__,
                         self.__samplespersec__,
                         self.__bytespersec__,
                         self.__blockalign__,
                         self.__bitspersample__) = wave_file.parse(
                            "16u 16u 32u 32u 16u 16u")
                        if (compression == 1):
                            #if we have a multi-channel WAVE file
                            #that's not WAVEFORMATEXTENSIBLE,
                            #assume the channels follow
                            #SMPTE/ITU-R recommendations
                            #and hope for the best
                            if (self.__channels__ == 1):
                                self.__channel_mask__ = ChannelMask.from_fields(
                                    front_center=True)
                            elif (self.__channels__ == 2):
                                self.__channel_mask__ = ChannelMask.from_fields(
                                    front_left=True, front_right=True)
                            elif (self.__channels__ == 3):
                                self.__channel_mask__ = ChannelMask.from_fields(
                                    front_left=True, front_right=True,
                                    front_center=True)
                            elif (self.__channels__ == 4):
                                self.__channel_mask__ = ChannelMask.from_fields(
                                    front_left=True, front_right=True,
                                    back_left=True, back_right=True)
                            elif (self.__channels__ == 5):
                                self.__channel_mask__ = ChannelMask.from_fields(
                                    front_left=True, front_right=True,
                                    back_left=True, back_right=True,
                                    front_center=True)
                            elif (self.__channels__ == 6):
                                self.__channel_mask__ = ChannelMask.from_fields(
                                    front_left=True, front_right=True,
                                    back_left=True, back_right=True,
                                    front_center=True, low_frequency=True)
                            else:
                                self.__channel_mask__ = ChannelMask(0)

                        elif (compression == 0xFFFE):
                            (cb_size,
                             valid_bits_per_sample,
                             channel_mask,
                             sub_format) = wave_file.parse("16u 16u 32u 16b")
                            if (sub_format !=
                                ('\x01\x00\x00\x00\x00\x00\x10\x00' +
                                 '\x80\x00\x00\xaa\x00\x38\x9b\x71')):
                                raise InvalidWave(_(u"Invalid WAVE sub-format"))
                            else:
                                self.__channel_mask__ = \
                                    ChannelMask(channel_mask)
                        else:
                            raise InvalidWave(
                                _(u"Unsupported WAVE compression"))
                    elif (chunk_id == 'data'):
                        self.__data_size__ = chunk_size
                        wave_file.skip_bytes(chunk_size)
                    else:
                        wave_file.skip_bytes(chunk_size)

                    total_size -= chunk_size

                    #round up chunk sizes to 16 bits
                    if (chunk_size % 2):
                        wave_file.skip(8)
                        total_size -= 1
            except IOError, msg:
                raise InvalidWave(str(msg))
        finally:
            wave_file.close()

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(12)
        return ((header[0:4] == 'RIFF') and
                (header[8:12] == 'WAVE'))

    def lossless(self):
        """Returns True."""

        return True

    def has_foreign_riff_chunks(self):
        """Returns True if the audio file contains non-audio RIFF chunks.

        During transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks."""

        return set(['fmt ', 'data']) != set(self.__chunk_ids__)

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        return self.__channel_mask__

    #Returns the PCMReader object for this WAV's data
    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        return WaveReader(file(self.filename, 'rb'),
                          sample_rate=self.sample_rate(),
                          channels=self.channels(),
                          bits_per_sample=self.bits_per_sample(),
                          channel_mask=int(self.channel_mask()))

    #Takes a filename and PCMReader containing WAV data
    #builds a WAV from that data and returns a new WaveAudio object
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object."""

        from .bitstream import BitstreamWriter,format_size

        try:
            f = file(filename, "wb")
            wave = BitstreamWriter(f, 1)
        except IOError, err:
            raise EncodingError(str(err))

        try:
            total_size = 0
            data_size = 0

            avg_bytes_per_second = (pcmreader.sample_rate *
                                    pcmreader.channels *
                                    (pcmreader.bits_per_sample / 8))
            block_align = (pcmreader.channels *
                           (pcmreader.bits_per_sample / 8))

            if ((pcmreader.channels <= 2) and
                (pcmreader.bits_per_sample <= 16)):
                fmt = "16u 16u 32u 32u 16u 16u"
                fmt_fields = (1,   #compression code
                              pcmreader.channels,
                              pcmreader.sample_rate,
                              avg_bytes_per_second,
                              block_align,
                              pcmreader.bits_per_sample)
            else:
                fmt = "16u 16u 32u 32u 16u 16u" + "16u 16u 32u 16b"
                fmt_fields = (0xFFFE,   #compression code
                              pcmreader.channels,
                              pcmreader.sample_rate,
                              avg_bytes_per_second,
                              block_align,
                              pcmreader.bits_per_sample,
                              22,       #CB size
                              pcmreader.bits_per_sample,
                              pcmreader.channel_mask,
                              '\x01\x00\x00\x00\x00\x00\x10\x00' +
                              '\x80\x00\x00\xaa\x00\x38\x9b\x71' #sub format
                              )

            #write out the basic headers first
            #we'll be back later to clean up the sizes
            wave.build("4b 32u 4b", ("RIFF", total_size, "WAVE"))
            total_size += 4

            wave.build("4b 32u", ('fmt ', format_size(fmt) / 8))
            total_size += format_size("4b 32u") / 8

            wave.build(fmt, fmt_fields)
            total_size += format_size(fmt) / 8

            wave.build("4b 32u", ('data', data_size))
            total_size += format_size("4b 32u") / 8

            #dump pcmreader's FrameLists into the file as little-endian
            try:
                framelist = pcmreader.read(BUFFER_SIZE)
                while (len(framelist) > 0):
                    if (framelist.bits_per_sample > 8):
                        bytes = framelist.to_bytes(False, True)
                    else:
                        bytes = framelist.to_bytes(False, False)

                    f.write(bytes)
                    total_size += len(bytes)
                    data_size += len(bytes)

                    framelist = pcmreader.read(BUFFER_SIZE)
            except (IOError, ValueError), err:
                cls.__unlink__(filename)
                raise EncodingError(str(err))
            except Exception, err:
                cls.__unlink__(filename)
                raise err

            #handle odd-sized data chunks
            if (data_size % 2):
                wave.write(8, 0)
                total_size += 1

            #close the PCM reader and flush our output
            try:
                pcmreader.close()
            except DecodingError, err:
                cls.__unlink__(filename)
                raise EncodingError(err.error_message)
            f.flush()

            #go back to the beginning the re-write the header
            f.seek(0, 0)
            wave.build("4b 32u 4b", ("RIFF", total_size, "WAVE"))
            wave.build("4b 32u", ('fmt ', format_size(fmt) / 8))
            wave.build(fmt, fmt_fields)
            wave.build("4b 32u", ('data', data_size))

        finally:
            f.close()

        return WaveAudio(filename)

    def to_wave(self, wave_filename, progress=None):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        try:
            self.verify()
        except InvalidWave, err:
            raise EncodingError(str(err))

        try:
            output = file(wave_filename, 'wb')
            input = file(self.filename, 'rb')
        except IOError, msg:
            raise EncodingError(str(msg))
        try:
            transfer_data(input.read, output.write)
        finally:
            input.close()
            output.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None,
                  progress=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object."""

        try:
            cls(wave_filename).verify()
        except InvalidWave, err:
            raise EncodingError(unicode(err))

        try:
            input = file(wave_filename, 'rb')
            output = file(filename, 'wb')
        except IOError, err:
            raise EncodingError(str(err))
        try:
            total_bytes = os.path.getsize(wave_filename)
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
                return WaveAudio(filename)
            except InvalidFile:
                cls.__unlink__(filename)
                raise EncodingError(u"invalid RIFF WAVE source file")
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

        if (hasattr(target_class, "from_wave")):
            return target_class.from_wave(target_path,
                                          self.filename,
                                          compression=compression,
                                          progress=progress)
        else:
            return target_class.from_pcm(target_path,
                                         to_pcm_progress(self, progress),
                                         compression)

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__data_size__ / (self.__bitspersample__ / 8) / \
               self.__channels__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__samplespersec__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bitspersample__

    @classmethod
    def can_add_replay_gain(cls):
        """Returns True if we have the necessary binaries to add ReplayGain."""

        return True

    @classmethod
    def lossless_replay_gain(cls):
        """Returns False."""

        return False

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """Adds ReplayGain values to a list of filename strings.

        All the filenames must be of this AudioFile type.
        Raises ValueError if some problem occurs during ReplayGain application.
        """

        from audiotools.replaygain import ReplayGain, ReplayGainReader
        import tempfile

        wave_files = [track for track in open_files(filenames) if
                      isinstance(track, cls)]

        track_gains = []
        total_frames = sum([track.total_frames() for track in wave_files]) * 2
        processed_frames = 0

        #first, calculate the Gain and Peak values from our files
        for original_wave in wave_files:
            try:
                rg = ReplayGain(original_wave.sample_rate())
            except ValueError:
                track_gains.append((None, None))
            pcm = original_wave.to_pcm()
            try:
                try:
                    frame = pcm.read(BUFFER_SIZE)
                    while (len(frame) > 0):
                        processed_frames += frame.frames
                        if (progress is not None):
                            progress(processed_frames, total_frames)
                        rg.update(frame)
                        frame = pcm.read(BUFFER_SIZE)
                    track_gains.append(rg.title_gain())
                except ValueError:
                    track_gains.append((None, None))
            finally:
                pcm.close()

        #then, apply those Gain and Peak values to our files
        #rewriting the originals in the process
        for (original_wave, (gain, peak)) in zip(wave_files, track_gains):
            if (gain is None):
                continue

            temp_wav_file = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                (header, footer) = original_wave.pcm_split()
                temp_wav_file.write(header)
                replaygain_pcm = ReplayGainReader(original_wave.to_pcm(),
                                                  gain, peak)
                frame = replaygain_pcm.read(BUFFER_SIZE)
                while (len(frame) > 0):
                    processed_frames += frame.frames
                    if (progress is not None):
                        progress(processed_frames, total_frames)
                    temp_wav_file.write(frame.to_bytes(
                            False,
                            original_wave.bits_per_sample() > 8))
                    frame = replaygain_pcm.read(BUFFER_SIZE)

                temp_wav_file.write(footer)
                temp_wav_file.seek(0, 0)
                new_wave = open(original_wave.filename, 'wb')
                transfer_data(temp_wav_file.read, new_wave.write)
                new_wave.close()
            finally:
                temp_wav_file.close()

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
            format = "track%(track_number)2.2d.wav"
        return AudioFile.track_name(file_path, track_metadata, format,
                                    suffix=cls.SUFFIX)

    def chunk_ids(self):
        """Returns a list of RIFF WAVE chunk ID strings."""

        return self.__chunk_ids__[:]

    def chunks(self):
        """Yields (chunk_id, chunk_data) tuples.

        chunk_id and chunk_data are both binary strings."""

        from .bitstream import BitstreamReader

        wave_file = BitstreamReader(file(self.filename, 'rb'), 1)
        try:
            (riff, total_size, wave) = wave_file.parse("4b 32u 4b")
            if (riff != 'RIFF'):
                raise InvalidWave(_(u"Not a RIFF WAVE file"))
            elif (wave != 'WAVE'):
                raise InvalidWave(_(u"Invalid RIFF WAVE file"))
            else:
                total_size -= 4

            while (total_size > 0):
                #read the chunk header and ensure its validity
                (chunk_id, chunk_size) = wave_file.parse("4b 32u")
                if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                    raise InvalidWave(_(u"Invalid RIFF WAVE chunk ID"))
                else:
                    total_size -= 8

                #yield the (chunk_id, chunk_data) strings
                yield (chunk_id, wave_file.read_bytes(chunk_size))

                total_size -= chunk_size

                #round up chunk size to 16 bits
                if (chunk_size % 2):
                    wave_file.skip(8)
                    total_size -= 1

        finally:
            wave_file.close()

    @classmethod
    def wave_from_chunks(cls, filename, chunk_iter):
        """Builds a new RIFF WAVE file from a chunk data iterator.

        filename is the path to the wave file to build.
        chunk_iter should yield (chunk_id, chunk_data) tuples.
        """

        from .bitstream import BitstreamWriter

        wave = file(filename, 'wb')
        wave_file = BitstreamWriter(wave, 1)
        try:
            total_size = 4

            #write an unfinished header with a placeholder size
            wave_file.build("4b 32u 4b", ("RIFF", total_size, "WAVE"))

            #write the individual chunks
            for (chunk_id, chunk_data) in chunk_iter:
                wave_file.build("4b 32u %db" % (len(chunk_data)),
                                (chunk_id, len(chunk_data), chunk_data))
                total_size += (8 + len(chunk_data))

                #round up chunks to 16 bit boundries
                if (len(chunk_data) % 2):
                    wave_file.write(8, 0)
                    total_size += 1

            #once the chunks are done, go back and re-write the header
            wave.seek(4, 0)
            wave_file.write(32, total_size)
        finally:
            wave_file.close()

    def pcm_split(self):
        """Returns a pair of data strings before and after PCM data.

        The first contains all data before the PCM content of the data chunk.
        The second containing all data after the data chunk.
        For example:

        >>> w = audiotools.open("input.wav")
        >>> (head, tail) = w.pcm_split()
        >>> f = open("output.wav", "wb")
        >>> f.write(head)
        >>> audiotools.transfer_framelist_data(w.to_pcm(), f.write)
        >>> f.write(tail)
        >>> f.close()

        should result in "output.wav" being identical to "input.wav".
        """

        from .bitstream import BitstreamReader
        from .bitstream import BitstreamRecorder

        head = BitstreamRecorder(1)
        tail = BitstreamRecorder(1)
        current_block = head

        wave_file = BitstreamReader(open(self.filename, 'rb'), 1)
        try:
            #transfer the 12-byte "RIFFsizeWAVE" header to head
            (riff, size, wave) = wave_file.parse("4b 32u 4b")
            if (riff != 'RIFF'):
                raise InvalidWave(_(u"Not a RIFF WAVE file"))
            elif (wave != 'WAVE'):
                raise InvalidWave(_(u"Invalid RIFF WAVE file"))
            else:
                current_block.build("4b 32u 4b", (riff, size, wave))
                total_size = size - 4

            while (total_size > 0):
                #transfer each chunk header
                (chunk_id, chunk_size) = wave_file.parse("4b 32u")
                if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                    raise InvalidWave(_(u"Invalid RIFF WAVE chunk ID"))
                else:
                    current_block.build("4b 32u", (chunk_id, chunk_size))
                    total_size -= 8

                #round up chunk size to 16 bits
                if (chunk_size % 2):
                    chunk_size += 1

                #and transfer the full content of non-data chunks
                if (chunk_id != "data"):
                    current_block.write_bytes(wave_file.read_bytes(chunk_size))
                else:
                    wave_file.skip_bytes(chunk_size)
                    current_block = tail

                total_size -= chunk_size

            return (head.data(), tail.data())
        finally:
            wave_file.close()

    def verify(self, progress=None):
        """Verifies the current file for correctness.

        Returns True if the file is okay.
        Raises an InvalidFile with an error message if there is
        some problem with the file."""

        #RIFF WAVE chunk verification is likely to be so fast
        #that individual calls to progress() are
        #a waste of time.
        if (progress is not None):
            progress(0, 1)

        try:
            f = open(self.filename, 'rb')
        except IOError, msg:
            raise InvalidWave(str(msg))

        try:
            #check the RIFF WAVE header is correct
            try:
                wave_header = self.WAVE_HEADER.parse_stream(f)
            except (Con.ConstError, Con.FieldError):
                raise InvalidWave(u"error parsing RIFF WAVE header")

            if (os.path.getsize(self.filename) != (wave_header.wave_size + 8)):
                raise InvalidWave(u"wave file appears truncated")

            bytes_remaining = wave_header.wave_size - 4

            fmt_chunk_found = data_chunk_found = False

            #bounce through all the chunks
            while (bytes_remaining > 0):
                try:
                    chunk_header = self.CHUNK_HEADER.parse_stream(f)
                except (Con.FieldError, Con.ValidationError):
                    raise InvalidWave(u"error parsing chunk header")
                bytes_remaining -= 8

                if (chunk_header.chunk_id == 'fmt '):
                    #verify the fmt chunk is sane
                    try:
                        fmt_chunk = self.FMT_CHUNK.parse_stream(f)
                        fmt_chunk_found = True
                        fmt_chunk_size = len(self.FMT_CHUNK.build(fmt_chunk))
                        bytes_remaining -= fmt_chunk_size
                    except Con.FieldError:
                        raise InvalidWave(u"invalid fmt chunk")
                else:
                    if (chunk_header.chunk_id == 'data'):
                        data_chunk_found = True
                    #verify all other chunks are the correct size
                    f.seek(chunk_header.chunk_length, 1)
                    bytes_remaining -= chunk_header.chunk_length

            if (fmt_chunk_found and data_chunk_found):
                if (progress is not None):
                    progress(1, 1)

                return True
            elif (not fmt_chunk_found):
                raise InvalidWave(u"fmt chunk not found")
            else:
                raise InvalidWave(u"data chunk not found")
        finally:
            f.close()
