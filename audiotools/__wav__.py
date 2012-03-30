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


from audiotools import (AudioFile, InvalidFile, ChannelMask, PCMReader,
                        BUFFER_SIZE, transfer_data,
                        transfer_framelist_data,
                        __capped_stream_reader__, FILENAME_FORMAT,
                        BIN, open_files, os, subprocess, cStringIO,
                        EncodingError, DecodingError,
                        UnsupportedChannelMask,
                        UnsupportedChannelCount,
                        WaveContainer, to_pcm_progress,
                        LimitedFileReader)
import os.path
import struct
import gettext
from . import pcm

gettext.install("audiotools", unicode=True)

#######################
#RIFF WAVE
#######################


class RIFF_Chunk:
    """a raw chunk of RIFF WAVE data"""

    def __init__(self, chunk_id, chunk_size, chunk_data):
        """chunk_id should be a binary string of ASCII
        chunk_data should be a binary string of chunk data"""

        #FIXME - check chunk_id's validity

        self.id = chunk_id
        self.__size__ = chunk_size
        self.__data__ = chunk_data

    def __repr__(self):
        return "RIFF_Chunk(%s)" % (repr(self.id))

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

        return cStringIO.StringIO(self.__data__)

    def verify(self):
        return self.__size__ == len(self.__data__)

    def write(self, f):
        """writes the entire chunk to the given output file object
        returns size of entire chunk (including header and spacer)
        in bytes"""

        f.write(self.id)
        f.write(struct.pack("<I", self.__size__))
        f.write(self.__data__)
        if (self.__size__ % 2):
            f.write(chr(0))
        return self.total_size()


class RIFF_File_Chunk(RIFF_Chunk):
    """a raw chunk of RIFF WAVE data taken from an existing file"""

    def __init__(self, chunk_id, chunk_size, wav_file, chunk_data_offset):
        """chunk_id should be a binary string of ASCII
        chunk_size is the size of the chunk in bytes
        (not counting any spacer byte)
        wav_file is the file this chunk belongs to
        chunk_data_offset is the offset to the chunk's data bytes
        (not including the 8 byte header)"""

        self.id = chunk_id
        self.__size__ = chunk_size
        self.__wav_file__ = wav_file
        self.__offset__ = chunk_data_offset

    def __repr__(self):
        return "RIFF_File_Chunk(%s)" % (repr(self.id))

    def data(self):
        """returns chunk data as file-like object"""

        self.__wav_file__.seek(self.__offset__)
        return LimitedFileReader(self.__wav_file__, self.size())

    def verify(self):
        self.__wav_file__.seek(self.__offset__)
        to_read = self.__size__
        while (to_read > 0):
            s = self.__wav_file__.read(min(0x100000, to_read))
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
        f.write(struct.pack("<I", self.__size__))
        self.__wav_file__.seek(self.__offset__)
        to_write = self.__size__
        while (to_write > 0):
            s = self.__wav_file__.read(min(0x100000, to_write))
            f.write(s)
            to_write -= len(s)

        if (self.__size__ % 2):
            f.write(chr(0))
        return self.total_size()


def parse_fmt(fmt):
    """given a fmt block BitstreamReader (without the 8 byte header)
    returns (channels, sample_rate, bits_per_sample, channel_mask)
    where channel_mask is a ChannelMask object and the rest are ints
    may raise ValueError if the fmt chunk is invalid
    or IOError if an error occurs parsing the chunk"""

    (compression,
     channels,
     sample_rate,
     bytes_per_second,
     block_align,
     bits_per_sample) = fmt.parse("16u 16u 32u 32u 16u 16u")

    if (compression == 1):
        #if we have a multi-channel WAVE file
        #that's not WAVEFORMATEXTENSIBLE,
        #assume the channels follow
        #SMPTE/ITU-R recommendations
        #and hope for the best
        if (channels == 1):
            channel_mask = ChannelMask.from_fields(
                front_center=True)
        elif (channels == 2):
            channel_mask = ChannelMask.from_fields(
                front_left=True, front_right=True)
        elif (channels == 3):
            channel_mask = ChannelMask.from_fields(
                front_left=True, front_right=True,
                front_center=True)
        elif (channels == 4):
            channel_mask = ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True)
        elif (channels == 5):
            channel_mask = ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True,
                front_center=True)
        elif (channels == 6):
            channel_mask = ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True,
                front_center=True, low_frequency=True)
        else:
            channel_mask = ChannelMask(0)

        return (channels, sample_rate, bits_per_sample, channel_mask)
    elif (compression == 0xFFFE):
        (cb_size,
         valid_bits_per_sample,
         channel_mask,
         sub_format) = fmt.parse("16u 16u 32u 16b")
        if (sub_format !=
            ('\x01\x00\x00\x00\x00\x00\x10\x00' +
             '\x80\x00\x00\xaa\x00\x38\x9b\x71')):
            raise ValueError("invalid WAVE sub-format")
        else:
            channel_mask = ChannelMask(channel_mask)

            return (channels, sample_rate, bits_per_sample, channel_mask)
    else:
        raise ValueError("unsupported WAVE compression")


class WaveReader(PCMReader):
    """a subclass of PCMReader for reading wave file contents"""

    def __init__(self, wave_file,
                 sample_rate, channels, channel_mask, bits_per_sample,
                 process=None):
        """wave_file should be a file-like stream of wave data

        sample_rate, channels, channel_mask and bits_per_sample are ints
        if present, process is waited for when close() is called
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
                        wave_reader.skip(8)

        except IOError:
            raise InvalidWave(_(u"data chunk not found"))

    def read(self, bytes):
        """try to read a pcm.FrameList of size 'bytes'"""

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
        """closes the stream for reading

        any subprocess is waited for also so for proper cleanup"""

        self.wave.close()
        if (self.process is not None):
            if (self.process.wait() != 0):
                raise DecodingError()


class TempWaveReader(WaveReader):
    """a subclass of WaveReader for reading wave data from temporary files"""

    def __init__(self, tempfile):
        """tempfile should be a NamedTemporaryFile

        its contents are used to populate the rest of the fields"""

        wave = WaveAudio(tempfile.name)
        WaveReader.__init__(self,
                            tempfile,
                            sample_rate=wave.sample_rate(),
                            channels=wave.channels(),
                            channel_mask=int(wave.channel_mask()),
                            bits_per_sample=wave.bits_per_sample())
        self.tempfile = tempfile

    def close(self):
        """closes the input stream and temporary file"""

        WaveReader.close(self)
        self.tempfile.close()


class InvalidWave(InvalidFile):
    """raises during initialization time if a wave file is invalid"""

    pass


class WaveAudio(WaveContainer):
    """a waveform audio file"""

    SUFFIX = "wav"
    NAME = SUFFIX

    PRINTABLE_ASCII = frozenset([chr(i) for i in xrange(0x20, 0x7E + 1)])

    def __init__(self, filename):
        """filename is a plain string"""

        AudioFile.__init__(self, filename)

        self.__channels__ = 0
        self.__sample_rate__ = 0
        self.__bits_per_sample__ = 0
        self.__data_size__ = 0
        self.__channel_mask__ = ChannelMask(0)

        from .bitstream import BitstreamReader

        fmt_read = data_read = False

        try:
            for chunk in self.chunks():
                if (chunk.id == "fmt "):
                    try:
                        (self.__channels__,
                         self.__sample_rate__,
                         self.__bits_per_sample__,
                         self.__channel_mask__) = parse_fmt(
                            BitstreamReader(chunk.data(), 1))
                        fmt_read = True
                        if (fmt_read and data_read):
                            break
                    except IOError:
                        continue
                elif (chunk.id == "data"):
                    self.__data_size__ = chunk.size()
                    data_read = True
                    if (fmt_read and data_read):
                        break
        except IOError:
            raise InvalidWave("I/O error reading wave")

    @classmethod
    def is_type(cls, file):
        """returns True if the given file object describes this format

        takes a seekable file pointer rewound to the start of the file"""

        header = file.read(12)
        return ((header[0:4] == 'RIFF') and
                (header[8:12] == 'WAVE'))

    def lossless(self):
        """returns True"""

        return True

    def has_foreign_riff_chunks(self):
        """returns True if the audio file contains non-audio RIFF chunks

        during transcoding, if the source audio file has foreign RIFF chunks
        and the target audio format supports foreign RIFF chunks,
        conversion should be routed through .wav conversion
        to avoid losing those chunks"""

        return set(['fmt ', 'data']) != set([c.id for c in self.chunks()])

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        return self.__channel_mask__

    #Returns the PCMReader object for this WAV's data
    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        return WaveReader(file(self.filename, 'rb'),
                          sample_rate=self.sample_rate(),
                          channels=self.channels(),
                          bits_per_sample=self.bits_per_sample(),
                          channel_mask=int(self.channel_mask()))

    #Takes a filename and PCMReader containing WAV data
    #builds a WAV from that data and returns a new WaveAudio object
    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object
        and optional compression level string
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object"""

        if (pcmreader.channels > 18):
            raise UnsupportedChannelCount(filename, pcmreader.channels)

        from .bitstream import BitstreamWriter, format_size

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

            #build a regular or extended fmt chunk
            #based on the reader's attributes
            if ((pcmreader.channels <= 2) and
                (pcmreader.bits_per_sample <= 16)):
                fmt = "16u 16u 32u 32u 16u 16u"
                fmt_fields = (1,   # compression code
                              pcmreader.channels,
                              pcmreader.sample_rate,
                              avg_bytes_per_second,
                              block_align,
                              pcmreader.bits_per_sample)
            else:
                if (pcmreader.channel_mask != 0):
                    channel_mask = pcmreader.channel_mask
                else:
                    channel_mask = {1:0x4,
                                    2:0x3,
                                    3:0x7,
                                    4:0x33,
                                    5:0x37,
                                    6:0x3F}.get(pcmreader.channels, 0)

                fmt = "16u 16u 32u 32u 16u 16u" + "16u 16u 32u 16b"
                fmt_fields = (0xFFFE,   # compression code
                              pcmreader.channels,
                              pcmreader.sample_rate,
                              avg_bytes_per_second,
                              block_align,
                              pcmreader.bits_per_sample,
                              22,       # CB size
                              pcmreader.bits_per_sample,
                              channel_mask,
                              '\x01\x00\x00\x00\x00\x00\x10\x00' +
                              '\x80\x00\x00\xaa\x00\x38\x9b\x71'  # sub format
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

            if (total_size < (2 ** 32)):
                #go back to the beginning the rewrite the header
                f.seek(0, 0)
                wave.build("4b 32u 4b", ("RIFF", total_size, "WAVE"))
                wave.build("4b 32u", ('fmt ', format_size(fmt) / 8))
                wave.build(fmt, fmt_fields)
                wave.build("4b 32u", ('data', data_size))
            else:
                os.unlink(filename)
                raise EncodingError("PCM data too large for wave file")

        finally:
            f.close()

        return WaveAudio(filename)

    def to_wave(self, wave_filename, progress=None):
        """writes the contents of this file to the given .wav filename string

        raises EncodingError if some error occurs during decoding"""

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
        """encodes a new AudioFile from an existing .wav file

        takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string
        encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new WaveAudio object"""

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
        """encodes a new AudioFile from existing AudioFile

        take a filename string, target class and optional compression string
        encodes a new AudioFile in the target class and returns
        the resulting object
        may raise EncodingError if some problem occurs during encoding"""

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
        """returns the total PCM frames of the track as an integer"""

        return self.__data_size__ / (self.__bits_per_sample__ / 8) / \
               self.__channels__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    @classmethod
    def can_add_replay_gain(cls):
        """returns True if we have the necessary binaries to add ReplayGain"""

        return True

    @classmethod
    def lossless_replay_gain(cls):
        """returns False"""

        return False

    @classmethod
    def add_replay_gain(cls, filenames, progress=None):
        """adds ReplayGain values to a list of filename strings

        all the filenames must be of this AudioFile type
        raises ValueError if some problem occurs during ReplayGain application
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
        """constructs a new filename string

        given a plain string to an existing path,
        a MetaData-compatible object (or None),
        a UTF-8-encoded Python format string
        and an ASCII-encoded suffix string (such as "mp3")
        returns a plain string of a new filename with format's
        fields filled-in and encoded as FS_ENCODING
        raises UnsupportedTracknameField if the format string
        contains invalid template fields"""

        if (format is None):
            format = "track%(track_number)2.2d.wav"
        return AudioFile.track_name(file_path, track_metadata, format,
                                    suffix=cls.SUFFIX)

    def chunks(self):
        """yields a set of RIFF_Chunk or RIFF_File_Chunk objects"""

        wave_file = file(self.filename, "rb")
        try:
            (riff,
             total_size,
             wave) = struct.unpack("<4sI4s", wave_file.read(12))
        except struct.error:
            raise InvalidWave(_(u"Invalid RIFF WAVE file"))

        if (riff != 'RIFF'):
            raise InvalidWave(_(u"Not a RIFF WAVE file"))
        elif (wave != 'WAVE'):
            raise InvalidWave(_(u"Invalid RIFF WAVE file"))
        else:
            total_size -= 4

        while (total_size > 0):
            #read the chunk header and ensure its validity
            try:
                (chunk_id,
                 chunk_size) = struct.unpack("<4sI", wave_file.read(8))
            except struct.error:
                raise InvalidWave(_(u"Invalid RIFF WAVE file"))
            if (not frozenset(chunk_id).issubset(self.PRINTABLE_ASCII)):
                raise InvalidWave(_(u"Invalid RIFF WAVE chunk ID"))
            else:
                total_size -= 8

            #yield RIFF_Chunk or RIFF_File_Chunk depending on chunk size
            if (chunk_size >= 0x100000):
                #if chunk is too large, yield a File_Chunk
                yield RIFF_File_Chunk(chunk_id,
                                      chunk_size,
                                      file(self.filename, "rb"),
                                      wave_file.tell())
                wave_file.seek(chunk_size, 1)
            else:
                #otherwise, yield a raw data Chunk
                yield RIFF_Chunk(chunk_id, chunk_size,
                                 wave_file.read(chunk_size))

            if (chunk_size % 2):
                if (len(wave_file.read(1)) < 1):
                    raise InvalidWave(_(u"Invalid RIFF WAVE chunk"))
                total_size -= (chunk_size + 1)
            else:
                total_size -= chunk_size

    @classmethod
    def wave_from_chunks(cls, filename, chunk_iter):
        """builds a new RIFF WAVE file from a chunk data iterator

        filename is the path to the wave file to build
        chunk_iter should yield RIFF_Chunk-compatible objects
        """

        wave_file = file(filename, 'wb')
        try:
            total_size = 4

            #write an unfinished header with a placeholder size
            wave_file.write(struct.pack("<4sI4s", "RIFF", total_size, "WAVE"))

            #write the individual chunks
            for chunk in chunk_iter:
                total_size += chunk.write(wave_file)

            #once the chunks are done, go back and re-write the header
            wave_file.seek(0, 0)
            wave_file.write(struct.pack("<4sI4s", "RIFF", total_size, "WAVE"))
        finally:
            wave_file.close()

    def pcm_split(self):
        """returns a pair of data strings before and after PCM data

        the first contains all data before the PCM content of the data chunk
        the second containing all data after the data chunk
        for example:

        >>> w = audiotools.open("input.wav")
        >>> (head, tail) = w.pcm_split()
        >>> f = open("output.wav", "wb")
        >>> f.write(head)
        >>> audiotools.transfer_framelist_data(w.to_pcm(), f.write)
        >>> f.write(tail)
        >>> f.close()

        should result in "output.wav" being identical to "input.wav"
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
        """verifies the current file for correctness

        returns True if the file is okay
        raises an InvalidFile with an error message if there is
        some problem with the file"""

        #RIFF WAVE chunk verification is likely to be so fast
        #that individual calls to progress() are
        #a waste of time.
        if (progress is not None):
            progress(0, 1)

        fmt_found = False
        data_found = False

        for chunk in self.chunks():
            if (chunk.id == "fmt "):
                if (not fmt_found):
                    fmt_found = True
                else:
                    raise InvalidWave(_(u"multiple fmt chunks found"))

            elif (chunk.id == "data"):
                if (not fmt_found):
                    raise InvalidWave(_(u"data chunk found before fmt"))
                elif (data_found):
                    raise InvalidWave(_(u"multiple data chunks found"))
                else:
                    data_found = True

            if (not chunk.verify()):
                raise InvalidWave(_(u"truncated %s chunk found") %
                                  (chunk.id.decode('ascii')))

        if (not fmt_found):
            raise InvalidWave(_(u"fmt chunk not found"))
        if (not data_found):
            raise InvalidWave(_(u"data chunk not found"))

        if (progress is not None):
            progress(1, 1)

        return True

    def clean(self, fixes_performed, output_filename=None):
        """cleans the file of known data and metadata problems

        fixes_performed is a list-like object which is appended
        with Unicode strings of fixed problems

        output_filename is an optional filename of the fixed file
        if present, a new AudioFile is returned
        otherwise, only a dry-run is performed and no new file is written

        raises IOError if unable to write the file or its metadata
        raises ValueError if the file has errors of some sort
        """

        chunk_queue = []
        pending_data = None

        for chunk in self.chunks():
            if (chunk.id == "fmt "):
                if ("fmt " in [c.id for c in chunk_queue]):
                    fixes_performed.append(
                        _(u"multiple fmt chunks found"))
                else:
                    chunk_queue.append(chunk)
                    if (pending_data is not None):
                        chunk_queue.append(pending_data)
                        pending_data = None
            elif (chunk.id == "data"):
                if ("fmt " not in [c.id for c in chunk_queue]):
                    fixes_performed.append(_(u"data chunk found before fmt"))
                    pending_data = chunk
                elif ("data" in [c.id for c in chunk_queue]):
                    fixes_performed.append(_(u"multiple data chunks found"))
                else:
                    chunk_queue.append(chunk)
            else:
                chunk_queue.append(chunk)

        if (output_filename is not None):
            WaveAudio.wave_from_chunks(output_filename, chunk_queue)
            return WaveAudio(output_filename)
