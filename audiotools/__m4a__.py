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
                        subprocess, BIN, cStringIO, MetaData, os,
                        Image, InvalidImage, ignore_sigint, InvalidFormat,
                        open, open_files, EncodingError, DecodingError,
                        WaveAudio, TempWaveReader,
                        ChannelMask, UnsupportedBitsPerSample,
                        BufferedPCMReader, to_pcm_progress,
                        at_a_time, VERSION, PCMReaderError,
                        __default_quality__)
from __m4a_atoms__ import *
import gettext

gettext.install("audiotools", unicode=True)


#######################
#M4A File
#######################


class InvalidM4A(InvalidFile):
    pass


#M4A files are made up of QuickTime Atoms
#some of those Atoms are containers for sub-Atoms
class __Qt_Atom__:
    CONTAINERS = frozenset(
        ['dinf', 'edts', 'imag', 'imap', 'mdia', 'mdra', 'minf',
         'moov', 'rmra', 'stbl', 'trak', 'tref', 'udta', 'vnrp'])

    STRUCT = Con.Struct("qt_atom",
                     Con.UBInt32("size"),
                     Con.String("type", 4))

    def __init__(self, type, data, offset):
        self.type = type
        self.data = data
        self.offset = offset

    def __repr__(self):
        return "__Qt_Atom__(%s,%s,%s)" % \
            (repr(self.type),
             repr(self.data),
             repr(self.offset))

    def __eq__(self, o):
        if (hasattr(o, "type") and
            hasattr(o, "data")):
            return ((self.type == o.type) and
                    (self.data == o.data))
        else:
            return False

    #takes an 8 byte string
    #returns an Atom's (type,size) as a tuple
    @classmethod
    def parse(cls, header_data):
        header = cls.STRUCT.parse(header_data)
        return (header.type, header.size)

    def build(self):
        return __build_qt_atom__(self.type, self.data)

    #performs a search of all sub-atoms to find the one
    #with the given type, or None if one cannot be found
    def get_atom(self, type):
        if (self.type == type):
            return self
        elif (self.is_container()):
            for atom in self:
                returned_atom = atom.get_atom(type)
                if (returned_atom is not None):
                    return returned_atom

        return None

    #returns True if the Atom is a container, False if not
    def is_container(self):
        return self.type in self.CONTAINERS

    def __iter__(self):
        for atom in __parse_qt_atoms__(cStringIO.StringIO(self.data),
                                       __Qt_Atom__):
            yield atom

    def __len__(self):
        count = 0
        for atom in self:
            count += 1
        return count

    def __getitem__(self, type):
        for atom in self:
            if (atom.type == type):
                return atom
        raise KeyError(type)

    def keys(self):
        return [atom.type for atom in self]


#a stream of __Qt_Atom__ objects
#though it is an Atom-like container, it has no type of its own
class __Qt_Atom_Stream__(__Qt_Atom__):
    def __init__(self, stream):
        self.stream = stream
        self.atom_class = __Qt_Atom__

        __Qt_Atom__.__init__(self, None, None, 0)

    def is_container(self):
        return True

    def __iter__(self):
        self.stream.seek(0, 0)

        for atom in __parse_qt_atoms__(self.stream,
                                       self.atom_class,
                                       self.offset):
            yield atom


Qt_Atom_Stream = __Qt_Atom_Stream__


#takes a stream object with a read() method
#iterates over all of the atoms it contains and yields
#a series of qt_class objects, which defaults to __Qt_Atom__
def __parse_qt_atoms__(stream, qt_class=__Qt_Atom__, base_offset=0):
    h = stream.read(8)
    while (len(h) == 8):
        (header_type, header_size) = qt_class.parse(h)
        if (header_size == 0):
            yield qt_class(header_type,
                           stream.read(),
                           base_offset)
        else:
            yield qt_class(header_type,
                           stream.read(header_size - 8),
                           base_offset)
        base_offset += header_size

        h = stream.read(8)


def __build_qt_atom__(atom_type, atom_data):
    con = Con.Container()
    con.type = atom_type
    con.size = len(atom_data) + __Qt_Atom__.STRUCT.sizeof()
    return __Qt_Atom__.STRUCT.build(con) + atom_data


#takes an existing __Qt_Atom__ object (possibly a container)
#and a __Qt_Atom__ to replace
#finds all sub-atoms with the same type as new_atom and replaces them
#returns a string
def __replace_qt_atom__(qt_atom, new_atom):
    if (qt_atom.type is None):
        return "".join(
            [__replace_qt_atom__(a, new_atom) for a in qt_atom])
    elif (qt_atom.type == new_atom.type):
        #if we've found the atom to replace,
        #build a new atom string from new_atom's data
        return __build_qt_atom__(new_atom.type, new_atom.data)
    else:
        #if we're still looking for the atom to replace
        if (not qt_atom.is_container()):
            #build the old atom string from qt_atom's data
            #if it is not a container
            return __build_qt_atom__(qt_atom.type, qt_atom.data)
        else:
            #recursively build the old atom's data
            #with values from __replace_qt_atom__
            return __build_qt_atom__(qt_atom.type,
                                     "".join(
                    [__replace_qt_atom__(a, new_atom) for a in qt_atom]))


def __remove_qt_atom__(qt_atom, atom_name):
    if (qt_atom.type is None):
        return "".join(
            [__remove_qt_atom__(a, atom_name) for a in qt_atom])
    elif (qt_atom.type == atom_name):
        return ""
    else:
        if (not qt_atom.is_container()):
            return __build_qt_atom__(qt_atom.type, qt_atom.data)
        else:
            return __build_qt_atom__(qt_atom.type,
                                     "".join(
                    [__remove_qt_atom__(a, atom_name) for a in qt_atom]))


class M4AAudio_faac(AudioFile):
    """An M4A audio file using faac/faad binaries for I/O."""

    SUFFIX = "m4a"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "100"
    COMPRESSION_MODES = tuple(["10"] + map(str, range(50, 500, 25)) + ["500"])
    BINARIES = ("faac", "faad")

    MP4A_ATOM = Con.Struct("mp4a",
                           Con.UBInt32("length"),
                           Con.String("type", 4),
                           Con.String("reserved", 6),
                           Con.UBInt16("reference_index"),
                           Con.UBInt16("version"),
                           Con.UBInt16("revision_level"),
                           Con.String("vendor", 4),
                           Con.UBInt16("channels"),
                           Con.UBInt16("bits_per_sample"))

    MDHD_ATOM = Con.Struct("mdhd",
                           Con.Byte("version"),
                           Con.Bytes("flags", 3),
                           Con.UBInt32("creation_date"),
                           Con.UBInt32("modification_date"),
                           Con.UBInt32("sample_rate"),
                           Con.UBInt32("track_length"))

    def __init__(self, filename):
        """filename is a plain string."""

        self.filename = filename
        try:
            self.qt_stream = __Qt_Atom_Stream__(file(self.filename, "rb"))
        except IOError, msg:
            raise InvalidM4A(str(msg))

        try:
            mp4a = M4AAudio.MP4A_ATOM.parse(
                self.qt_stream['moov']['trak']['mdia']['minf']['stbl'][
                    'stsd'].data[8:])

            self.__channels__ = mp4a.channels
            self.__bits_per_sample__ = mp4a.bits_per_sample

            mdhd = M4AAudio.MDHD_ATOM.parse(
                self.qt_stream['moov']['trak']['mdia']['mdhd'].data)

            self.__sample_rate__ = mdhd.sample_rate
            self.__length__ = mdhd.track_length
        except KeyError:
            raise InvalidM4A(_(u'Required moov atom not found'))

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        #M4A seems to use the same channel assignment
        #as old-style RIFF WAVE/FLAC
        if (self.channels() == 1):
            return ChannelMask.from_fields(
                front_center=True)
        elif (self.channels() == 2):
            return ChannelMask.from_fields(
                front_left=True, front_right=True)
        elif (self.channels() == 3):
            return ChannelMask.from_fields(
                front_left=True, front_right=True, front_center=True)
        elif (self.channels() == 4):
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True)
        elif (self.channels() == 5):
            return ChannelMask.from_fields(
                front_left=True, front_right=True, front_center=True,
                back_left=True, back_right=True)
        elif (self.channels() == 6):
            return ChannelMask.from_fields(
                front_left=True, front_right=True, front_center=True,
                back_left=True, back_right=True,
                low_frequency=True)
        else:
            return ChannelMask(0)

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(12)

        if ((header[4:8] == 'ftyp') and
            (header[8:12] in ('mp41', 'mp42', 'M4A ', 'M4B '))):
            file.seek(0, 0)
            atoms = __Qt_Atom_Stream__(file)
            try:
                return (ATOM_STSD.parse(atoms['moov']['trak']['mdia']['minf']['stbl']['stsd'].data).descriptions[0].type == 'mp4a')
            except (Con.ConstError, Con.FieldError, Con.ArrayError, KeyError,
                    IndexError):
                return False
        else:
            return False

    def lossless(self):
        """Returns False."""

        return False

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bits_per_sample__

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__sample_rate__

    def cd_frames(self):
        """Returns the total length of the track in CD frames.

        Each CD frame is 1/75th of a second."""

        return (self.__length__ - 1024) / self.__sample_rate__ * 75

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__length__ - 1024

    def get_metadata(self):
        """Returns a MetaData object, or None.

        Raises IOError if unable to read the file."""

        f = file(self.filename, 'rb')
        try:
            qt_stream = __Qt_Atom_Stream__(f)
            try:
                meta_atom = ATOM_META.parse(
                    qt_stream['moov']['udta']['meta'].data)
            except KeyError:
                return None

            for atom in meta_atom.atoms:
                if (atom.type == 'ilst'):
                    return M4AMetaData([
                            ILST_Atom(
                                type=ilst_atom.type,
                                sub_atoms=[__Qt_Atom__(type=sub_atom.type,
                                                       data=sub_atom.data,
                                                       offset=0)
                                           for sub_atom in ilst_atom.data])
                            for ilst_atom in ATOM_ILST.parse(atom.data)])
            else:
                return None
        finally:
            f.close()

    def set_metadata(self, metadata):
        """Takes a MetaData object and sets this track's metadata.

        This metadata includes track name, album name, and so on.
        Raises IOError if unable to write the file."""

        metadata = M4AMetaData.converted(metadata)
        if (metadata is None):
            return

        old_metadata = self.get_metadata()
        if (old_metadata is not None):
            if ('----' in old_metadata.keys()):
                metadata['----'] = old_metadata['----']
            if ('=A9too'.decode('quopri') in old_metadata.keys()):
                metadata['=A9too'.decode('quopri')] = \
                    old_metadata['=A9too'.decode('quopri')]

        new_meta = metadata.to_atom(self.qt_stream['moov']['udta']['meta'])

        #first, attempt to replace the meta atom by resizing free

        #check to ensure our file is laid out correctly for that purpose
        if (self.qt_stream.keys() == ['ftyp', 'moov', 'free', 'mdat']):
            old_pre_mdat_size = sum([len(self.qt_stream[atom].data) + 8
                                     for atom in 'ftyp', 'moov', 'free'])

            #if so, replace moov's old meta atom with our new one
            new_moov = __replace_qt_atom__(self.qt_stream['moov'],
                                           new_meta)

            #and see if we can shrink the free atom enough to fit
            new_pre_mdat_size = (len(self.qt_stream['ftyp'].data) + 8 +
                                   len(new_moov) + 8)

            if (new_pre_mdat_size <= old_pre_mdat_size):
                #if we can, replace the start of the file with a new set of
                #ftyp, moov, free  atoms while leaving mdat alone
                f = file(self.filename, 'r+b')
                f.write(self.qt_stream['ftyp'].build())
                f.write(new_moov)
                f.write(__build_qt_atom__('free',
                                          chr(0) * (old_pre_mdat_size -
                                                    new_pre_mdat_size)))
                f.close()

                f = file(self.filename, "rb")
                self.qt_stream = __Qt_Atom_Stream__(f)
            else:
                self.__set_meta_atom__(new_meta)
        else:
            #otherwise, run a traditional full file replacement
            self.__set_meta_atom__(new_meta)

    #this updates our old 'meta' atom with a new 'meta' atom
    #where meta_atom is a __Qt_Atom__ object
    def __set_meta_atom__(self, meta_atom):
        #this is a two-pass operation
        #first we replace the contents of the moov->udta->meta atom
        #with our new 'meta' atom
        #this may move the 'mdat' atom, so we must go back
        #and update the contents of
        #moov->trak->mdia->minf->stbl->stco
        #with new offset information

        stco = ATOM_STCO.parse(
           self.qt_stream['moov']['trak']['mdia']['minf']['stbl']['stco'].data)

        mdat_offset = stco.offset[0] - self.qt_stream['mdat'].offset

        new_file = __Qt_Atom_Stream__(cStringIO.StringIO(
                __replace_qt_atom__(self.qt_stream, meta_atom)))

        mdat_offset = new_file['mdat'].offset + mdat_offset

        stco.offset = [x - stco.offset[0] + mdat_offset
                       for x in stco.offset]

        new_file = __replace_qt_atom__(new_file,
                                       __Qt_Atom__('stco',
                                                   ATOM_STCO.build(stco),
                                                   0))

        f = file(self.filename, "wb")
        f.write(new_file)
        f.close()

        f = file(self.filename, "rb")
        self.qt_stream = __Qt_Atom_Stream__(f)

    def delete_metadata(self):
        """Deletes the track's MetaData.

        This removes or unsets tags as necessary in order to remove all data.
        Raises IOError if unable to write the file."""

        self.set_metadata(MetaData())

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        devnull = file(os.devnull, "ab")

        sub = subprocess.Popen([BIN['faad'], "-f", str(2), "-w",
                                self.filename],
                               stdout=subprocess.PIPE,
                               stderr=devnull)
        return PCMReader(
            sub.stdout,
            sample_rate=self.sample_rate(),
            channels=self.channels(),
            channel_mask=int(self.channel_mask()),
            bits_per_sample=self.bits_per_sample(),
            process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new M4AAudio object."""

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if (pcmreader.channels > 2):
            pcmreader = PCMConverter(pcmreader,
                                     sample_rate=pcmreader.sample_rate,
                                     channels=2,
                                     channel_mask=ChannelMask.from_channels(2),
                                     bits_per_sample=pcmreader.bits_per_sample)

        #faac requires files to end with .m4a for some reason
        if (not filename.endswith(".m4a")):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".m4a")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

        devnull = file(os.devnull, "ab")

        sub = subprocess.Popen([BIN['faac'],
                                "-q", compression,
                                "-P",
                                "-R", str(pcmreader.sample_rate),
                                "-B", str(pcmreader.bits_per_sample),
                                "-C", str(pcmreader.channels),
                                "-X",
                                "-o", filename,
                                "-"],
                               stdin=subprocess.PIPE,
                               stderr=devnull,
                               stdout=devnull,
                               preexec_fn=ignore_sigint)
        #Note: faac handles SIGINT on its own,
        #so trying to ignore it doesn't work like on most other encoders.

        try:
            transfer_framelist_data(pcmreader, sub.stdin.write)
        except (ValueError, IOError), err:
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

        if (sub.wait() == 0):
            if (tempfile is not None):
                filename = actual_filename
                f = file(filename, 'wb')
                tempfile.seek(0, 0)
                transfer_data(tempfile.read, f.write)
                f.close()
                tempfile.close()

            return M4AAudio(filename)
        else:
            if (tempfile is not None):
                tempfile.close()
            raise EncodingError(u"unable to write file with faac")

    @classmethod
    def can_add_replay_gain(cls):
        """Returns False."""

        return False

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

        track_names = [track.filename for track in
                       open_files(filenames) if
                       isinstance(track, cls)]

        if (progress is not None):
            progress(0, 1)

        #helpfully, aacgain is flag-for-flag compatible with mp3gain
        if ((len(track_names) > 0) and (BIN.can_execute(BIN['aacgain']))):
            devnull = file(os.devnull, 'ab')
            sub = subprocess.Popen([BIN['aacgain'], '-k', '-q', '-r'] + \
                                       track_names,
                                   stdout=devnull,
                                   stderr=devnull)
            sub.wait()

            devnull.close()

        if (progress is not None):
            progress(1, 1)


class M4AAudio_nero(M4AAudio_faac):
    """An M4A audio file using neroAacEnc/neroAacDec binaries for I/O."""

    DEFAULT_COMPRESSION = "0.5"
    COMPRESSION_MODES = ("0.0", "0.1", "0.2", "0.3", "0.4", "0.5",
                         "0.6", "0.7", "0.8", "0.9", "1.0")
    COMPRESSION_DESCRIPTIONS = {"0.0": _(u"lowest quality, " +
                                         u"corresponds to neroAacEnc -q 0"),
                                "1.0": _(u"highest quality, " +
                                         u"corresponds to neroAacEnc -q 1")}
    BINARIES = ("neroAacDec", "neroAacEnc")

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new M4AAudio object."""

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        import tempfile
        tempwavefile = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            if (pcmreader.sample_rate > 96000):
                tempwave = WaveAudio.from_pcm(
                    tempwavefile.name,
                    PCMConverter(pcmreader,
                                 sample_rate=96000,
                                 channels=pcmreader.channels,
                                 channel_mask=pcmreader.channel_mask,
                                 bits_per_sample=pcmreader.bits_per_sample))
            else:
                tempwave = WaveAudio.from_pcm(
                    tempwavefile.name,
                    pcmreader)

            cls.__from_wave__(filename, tempwave.filename, compression)
            return cls(filename)
        finally:
            if (os.path.isfile(tempwavefile.name)):
                tempwavefile.close()
            else:
                tempwavefile.close_called = True

    def to_pcm(self):
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".wav")
        try:
            self.to_wave(f.name)
            f.seek(0, 0)
            return TempWaveReader(f)
        except EncodingError, err:
            return PCMReaderError(error_message=err.error_message,
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    def to_wave(self, wave_file, progress=None):
        """Writes the contents of this file to the given .wav filename string.

        Raises EncodingError if some error occurs during decoding."""

        devnull = file(os.devnull, "w")
        try:
            sub = subprocess.Popen([BIN["neroAacDec"],
                                    "-if", self.filename,
                                    "-of", wave_file],
                                   stdout=devnull,
                                   stderr=devnull)
            if (sub.wait() != 0):
                raise EncodingError(u"unable to write file with neroAacDec")
        finally:
            devnull.close()

    @classmethod
    def from_wave(cls, filename, wave_filename, compression=None,
                  progress=None):
        """Encodes a new AudioFile from an existing .wav file.

        Takes a filename string, wave_filename string
        of an existing WaveAudio file
        and an optional compression level string.
        Encodes a new audio file from the wave's data
        at the given filename with the specified compression level
        and returns a new M4AAudio object."""

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        try:
            wave = WaveAudio(wave_filename)
            wave.verify()
        except InvalidFile:
            raise EncodingError(u"invalid wave file")

        if (wave.sample_rate > 96000):
            #convert through PCMConverter if sample rate is too high
            import tempfile
            tempwavefile = tempfile.NamedTemporaryFile(suffix=".wav")
            try:
                tempwave = WaveAudio.from_pcm(
                    tempwavefile.name,
                    PCMConverter(to_pcm_progress(wave, progress),
                                 sample_rate=96000,
                                 channels=wave.channels(),
                                 channel_mask=wave.channel_mask(),
                                 bits_per_sample=wave.bits_per_sample()))
                return cls.__from_wave__(filename, tempwave.filename,
                                         compression)
            finally:
                if (os.path.isfile(tempwavefile.name)):
                    tempwavefile.close()
                else:
                    tempwavefile.close_called = True
        else:
            return cls.__from_wave__(filename, wave_filename, compression)

    @classmethod
    def __from_wave__(cls, filename, wave_filename, compression):
        devnull = file(os.devnull, "w")
        try:
            sub = subprocess.Popen([BIN["neroAacEnc"],
                                    "-q", compression,
                                    "-if", wave_filename,
                                    "-of", filename],
                                   stdout=devnull,
                                   stderr=devnull)

            if (sub.wait() != 0):
                raise EncodingError(u"neroAacEnc unable to write file")
            else:
                return cls(filename)
        finally:
            devnull.close()

if (BIN.can_execute(BIN["neroAacEnc"]) and
    BIN.can_execute(BIN["neroAacDec"])):
    M4AAudio = M4AAudio_nero
else:
    M4AAudio = M4AAudio_faac


class ILST_Atom:
    """An ILST sub-atom, which itself is a container for other atoms.

    For human-readable fields, those will contain a single DATA sub-atom
    containing the data itself.
    For instance:

    'ilst' atom
      |
      +-'\xa9nam' atom
            |
            +-'data' atom
               |
               +-'\x00\x00\x00\x01\x00\x00\x00\x00Track Name' data
    """

    #type is a string
    #sub_atoms is a list of __Qt_Atom__-compatible sub-atom objects
    def __init__(self, type, sub_atoms):
        self.type = type
        self.data = sub_atoms

    def __eq__(self, o):
        if (hasattr(o, "type") and
            hasattr(o, "data")):
            return ((self.type == o.type) and
                    (self.data == o.data))
        else:
            return False

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return "ILST_Atom(%s,%s)" % (repr(self.type),
                                     repr(self.data))

    def __unicode__(self):
        for atom in self.data:
            if (atom.type == 'data'):
                if (atom.data.startswith('0000000100000000'.decode('hex'))):
                    return atom.data[8:].decode('utf-8')
                elif (self.type == 'trkn'):
                    trkn = ATOM_TRKN.parse(atom.data[8:])
                    if (trkn.total_tracks > 0):
                        return u"%d/%d" % (trkn.track_number,
                                           trkn.total_tracks)
                    else:
                        return unicode(trkn.track_number)
                elif (self.type == 'disk'):
                    disk = ATOM_DISK.parse(atom.data[8:])
                    if (disk.total_disks > 0):
                        return u"%d/%d" % (disk.disk_number,
                                           disk.total_disks)
                    else:
                        return unicode(disk.disk_number)
                else:
                    if (len(atom.data) > 28):
                        return unicode(
                            atom.data[8:20].encode('hex').upper()) + u"\u2026"
                    else:
                        return unicode(atom.data[8:].encode('hex'))
        else:
            return u""

    def __str__(self):
        for atom in self.data:
            if (atom.type == 'data'):
                return atom.data
        else:
            return ""


class M4AMetaData(MetaData, dict):
    """meta atoms are typically laid out like:

    meta
      |-hdlr
      |-ilst
      |   |- nam
      |   |   \-data
      |   \-trkn
      |       \-data
      \-free

    where the stuff we're interested in is in ilst
    and its data grandchild atoms.
    """
                                                    # iTunes ID:
    ATTRIBUTE_MAP = {
        'track_name': '=A9nam'.decode('quopri'),     # Name
        'artist_name': '=A9ART'.decode('quopri'),    # Artist
        'year': '=A9day'.decode('quopri'),           # Year
        'track_number': 'trkn',                      # Track Number
        'track_total': 'trkn',
        'album_name': '=A9alb'.decode('quopri'),     # Album
        'album_number': 'disk',                      # Disc Number
        'album_total': 'disk',
        'composer_name': '=A9wrt'.decode('quopri'),  # Composer
        'comment': '=A9cmt'.decode('quopri'),        # Comments
        'copyright': 'cprt'}                         # (not listed)

    def __init__(self, ilst_atoms):
        dict.__init__(self)
        for ilst_atom in ilst_atoms:
            self.setdefault(ilst_atom.type, []).append(ilst_atom)

    @classmethod
    def binary_atom(cls, key, value):
        """Generates a binary ILST_Atom list from key and value strings.

        The returned list is suitable for adding to our internal dict."""

        return [ILST_Atom(key,
                              [__Qt_Atom__(
                        "data",
                        value,
                        0)])]

    @classmethod
    def text_atom(cls, key, text):
        """Generates a text ILST_Atom list from key and text values.

        key is a binary string, text is a unicode string.
        The returned list is suitable for adding to our internal dict."""

        return cls.binary_atom(key, '0000000100000000'.decode('hex') + \
                                   text.encode('utf-8'))

    @classmethod
    def trkn_atom(cls, track_number, track_total):
        """Generates a trkn ILST_Atom list from integer values."""

        return cls.binary_atom('trkn',
                               '0000000000000000'.decode('hex') + \
                                   ATOM_TRKN.build(
                                       Con.Container(
                    track_number=track_number,
                    total_tracks=track_total)))

    @classmethod
    def disk_atom(cls, disk_number, disk_total):
        """Generates a disk ILST_Atom list from integer values."""

        return cls.binary_atom('disk',
                               '0000000000000000'.decode('hex') + \
                                   ATOM_DISK.build(
                                       Con.Container(
                    disk_number=disk_number,
                    total_disks=disk_total)))

    @classmethod
    def covr_atom(cls, image_data):
        """Generates a covr ILST_Atom list from raw image binary data."""

        return cls.binary_atom('covr',
                               '0000000000000000'.decode('hex') + \
                                   image_data)

    #if an attribute is updated (e.g. self.track_name)
    #make sure to update the corresponding dict pair
    def __setattr__(self, key, value):
        if (key in self.ATTRIBUTE_MAP.keys()):
            if (key not in MetaData.__INTEGER_FIELDS__):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.text_atom(
                    self.ATTRIBUTE_MAP[key],
                    value)

            elif (key == 'track_number'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.trkn_atom(
                    int(value), self.track_total)

            elif (key == 'track_total'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.trkn_atom(
                    self.track_number, int(value))

            elif (key == 'album_number'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.disk_atom(
                    int(value), self.album_total)

            elif (key == 'album_total'):
                self[self.ATTRIBUTE_MAP[key]] = self.__class__.disk_atom(
                    self.album_number, int(value))

    def __getattr__(self, key):
        if (key == 'track_number'):
            return ATOM_TRKN.parse(
                str(self.get('trkn', [chr(0) * 16])[0])[8:]).track_number
        elif (key == 'track_total'):
            return ATOM_TRKN.parse(
                str(self.get('trkn', [chr(0) * 16])[0])[8:]).total_tracks
        elif (key == 'album_number'):
            return ATOM_DISK.parse(
                str(self.get('disk', [chr(0) * 14])[0])[8:]).disk_number
        elif (key == 'album_total'):
            return ATOM_DISK.parse(
                str(self.get('disk', [chr(0) * 14])[0])[8:]).total_disks
        elif (key in self.ATTRIBUTE_MAP):
            return unicode(self.get(self.ATTRIBUTE_MAP[key], [u''])[0])
        elif (key in MetaData.__FIELDS__):
            return u''
        else:
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError(key)

    def __delattr__(self, key):
        if (key == 'track_number'):
            setattr(self, 'track_number', 0)
            if ((self.track_number == 0) and (self.track_total == 0)):
                del(self['trkn'])
        elif (key == 'track_total'):
            setattr(self, 'track_total', 0)
            if ((self.track_number == 0) and (self.track_total == 0)):
                del(self['trkn'])
        elif (key == 'album_number'):
            setattr(self, 'album_number', 0)
            if ((self.album_number == 0) and (self.album_total == 0)):
                del(self['disk'])
        elif (key == 'album_total'):
            setattr(self, 'album_total', 0)
            if ((self.album_number == 0) and (self.album_total == 0)):
                del(self['disk'])
        elif (key in self.ATTRIBUTE_MAP):
            if (self.ATTRIBUTE_MAP[key] in self):
                del(self[self.ATTRIBUTE_MAP[key]])
        elif (key in MetaData.__FIELDS__):
            pass
        else:
            try:
                del(self.__dict__[key])
            except KeyError:
                raise AttributeError(key)

    def images(self):
        """Returns a list of embedded Image objects."""

        try:
            return [M4ACovr(str(i)[8:]) for i in self['covr']
                    if (len(str(i)) > 8)]
        except KeyError:
            return list()

    def add_image(self, image):
        """Embeds an Image object in this metadata."""

        if (image.type == 0):
            self.setdefault('covr', []).append(self.__class__.covr_atom(
                    image.data)[0])

    def delete_image(self, image):
        """Deletes an Image object from this metadata."""

        i = 0
        for image_atom in self.get('covr', []):
            if (str(image_atom)[8:] == image.data):
                del(self['covr'][i])
                break

    @classmethod
    def converted(cls, metadata):
        """Converts a MetaData object to a M4AMetaData object."""

        if ((metadata is None) or (isinstance(metadata, M4AMetaData))):
            return metadata

        m4a = M4AMetaData([])

        for (field, key) in cls.ATTRIBUTE_MAP.items():
            value = getattr(metadata, field)
            if (field not in cls.__INTEGER_FIELDS__):
                if (value != u''):
                    m4a[key] = cls.text_atom(key, value)

        if ((metadata.track_number != 0) or
            (metadata.track_total != 0)):
            m4a['trkn'] = cls.trkn_atom(metadata.track_number,
                                         metadata.track_total)

        if ((metadata.album_number != 0) or
            (metadata.album_total != 0)):
            m4a['disk'] = cls.disk_atom(metadata.album_number,
                                         metadata.album_total)

        if (len(metadata.front_covers()) > 0):
            m4a['covr'] = [cls.covr_atom(i.data)[0]
                            for i in metadata.front_covers()]

        m4a['cpil'] = cls.binary_atom(
            'cpil',
            '0000001500000000'.decode('hex') + chr(1))

        return m4a

    def merge(self, metadata):
        """Updates any currently empty entries from metadata's values."""

        metadata = self.__class__.converted(metadata)
        if (metadata is None):
            return

        for (key, values) in metadata.items():
            if ((key not in 'trkn', 'disk') and
                (len(values) > 0) and
                (len(self.get(key, [])) == 0)):
                self[key] = values
        for attr in ("track_number", "track_total",
                     "album_number", "album_total"):
            if ((getattr(self, attr) == 0) and
                (getattr(metadata, attr) != 0)):
                setattr(self, attr, getattr(metadata, attr))

    def to_atom(self, previous_meta):
        """Returns a 'meta' __Qt_Atom__ object from this M4AMetaData."""

        previous_meta = ATOM_META.parse(previous_meta.data)

        new_meta = Con.Container(version=previous_meta.version,
                                 flags=previous_meta.flags,
                                 atoms=[])

        ilst = []
        for values in self.values():
            for ilst_atom in values:
                ilst.append(Con.Container(type=ilst_atom.type,
                                          data=[
                            Con.Container(type=sub_atom.type,
                                          data=sub_atom.data)
                            for sub_atom in ilst_atom.data]))

        #port the non-ilst atoms from old atom to new atom directly
        #
        for sub_atom in previous_meta.atoms:
            if (sub_atom.type == 'ilst'):
                new_meta.atoms.append(Con.Container(
                        type='ilst',
                        data=ATOM_ILST.build(ilst)))
            else:
                new_meta.atoms.append(sub_atom)

        return __Qt_Atom__(
            'meta',
            ATOM_META.build(new_meta),
            0)

    def __comment_name__(self):
        return u'M4A'

    @classmethod
    def supports_images(self):
        """Returns True."""

        return True

    @classmethod
    def __by_pair__(cls, pair1, pair2):
        KEY_MAP = {" nam": 1,
                   " ART": 6,
                   " com": 5,
                   " alb": 2,
                   "trkn": 3,
                   "disk": 4,
                   "----": 8}

        return cmp((KEY_MAP.get(pair1[0], 7), pair1[0], pair1[1]),
                   (KEY_MAP.get(pair2[0], 7), pair2[0], pair2[1]))

    def __comment_pairs__(self):
        pairs = []
        for (key, values) in self.items():
            for value in values:
                pairs.append((key.replace(chr(0xA9), ' '), unicode(value)))
        pairs.sort(M4AMetaData.__by_pair__)
        return pairs


class M4ACovr(Image):
    """A subclass of Image to store M4A 'covr' atoms."""

    def __init__(self, image_data):
        self.image_data = image_data

        img = Image.new(image_data, u'', 0)

        Image.__init__(self,
                       data=image_data,
                       mime_type=img.mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.color_depth,
                       color_count=img.color_count,
                       description=img.description,
                       type=img.type)

    @classmethod
    def converted(cls, image):
        """Given an Image object, returns an M4ACovr object."""

        return M4ACovr(image.data)


class __counter__:
    def __init__(self):
        self.val = 0

    def incr(self):
        self.val += 1

    def __int__(self):
        return self.val


class InvalidALAC(InvalidFile):
    pass


class ALACAudio(M4AAudio_faac):
    """An Apple Lossless audio file."""

    SUFFIX = "m4a"
    NAME = "alac"
    DEFAULT_COMPRESSION = ""
    COMPRESSION_MODES = ("",)
    BINARIES = tuple()

    ALAC_ATOM = Con.Struct("stsd_alac",
                           Con.String("reserved", 6),
                           Con.UBInt16("reference_index"),
                           Con.UBInt16("version"),
                           Con.UBInt16("revision_level"),
                           Con.String("vendor", 4),
                           Con.UBInt16("channels"),
                           Con.UBInt16("bits_per_sample"),
                           Con.UBInt16("compression_id"),
                           Con.UBInt16("audio_packet_size"),
                           #this sample rate always seems to be 0xAC440000
                           #no matter what the other sample rate fields are
                           Con.Bytes("sample_rate", 4),
                           Con.Struct("alac",
                                      Con.UBInt32("length"),
                                      Con.Const(Con.String("type", 4),
                                                'alac'),
                                      Con.Padding(4),
                                      Con.UBInt32("max_samples_per_frame"),
                                      Con.Padding(1),
                                      Con.UBInt8("sample_size"),
                                      Con.UBInt8("history_multiplier"),
                                      Con.UBInt8("initial_history"),
                                      Con.UBInt8("maximum_k"),
                                      Con.UBInt8("channels"),
                                      Con.UBInt16("unknown"),
                                      Con.UBInt32("max_coded_frame_size"),
                                      Con.UBInt32("bitrate"),
                                      Con.UBInt32("sample_rate")))

    ALAC_FTYP = AtomWrapper("ftyp", ATOM_FTYP)

    ALAC_MOOV = AtomWrapper(
        "moov", Con.Struct(
            "moov",
            AtomWrapper("mvhd", ATOM_MVHD),
            AtomWrapper("trak", Con.Struct(
                    "trak",
                    AtomWrapper("tkhd", ATOM_TKHD),
                    AtomWrapper("mdia", Con.Struct(
                            "mdia",
                            AtomWrapper("mdhd", ATOM_MDHD),
                            AtomWrapper("hdlr", ATOM_HDLR),
                            AtomWrapper("minf", Con.Struct(
                                    "minf",
                                    AtomWrapper("smhd", ATOM_SMHD),
                                    AtomWrapper("dinf", Con.Struct(
                                            "dinf",
                                            AtomWrapper("dref", ATOM_DREF))),
                                    AtomWrapper("stbl", Con.Struct(
                                            "stbl",
                                            AtomWrapper("stsd", ATOM_STSD),
                                            AtomWrapper("stts", ATOM_STTS),
                                            AtomWrapper("stsc", ATOM_STSC),
                                            AtomWrapper("stsz", ATOM_STSZ),
                                            AtomWrapper("stco", ATOM_STCO))))))))),
            AtomWrapper("udta", Con.Struct(
                    "udta",
                    AtomWrapper("meta", ATOM_META)))))

    BLOCK_SIZE = 4096
    INITIAL_HISTORY = 10
    HISTORY_MULTIPLIER = 40
    MAXIMUM_K = 14

    def __init__(self, filename):
        """filename is a plain string."""

        self.filename = filename
        try:
            self.qt_stream = __Qt_Atom_Stream__(file(self.filename, "rb"))
        except IOError, msg:
            raise InvalidALAC(str(msg))

        try:
            alac = ALACAudio.ALAC_ATOM.parse(
                ATOM_STSD.parse(self.qt_stream['moov']['trak']['mdia'][
                        'minf']['stbl']['stsd'].data).descriptions[0].data)

            self.__channels__ = alac.alac.channels
            self.__bits_per_sample__ = alac.bits_per_sample
            self.__sample_rate__ = alac.alac.sample_rate

            mdhd = M4AAudio.MDHD_ATOM.parse(
                self.qt_stream['moov']['trak']['mdia']['mdhd'].data)

            self.__length__ = mdhd.track_length
        except KeyError:
            raise InvalidALAC(_(u'Required moov atom not found'))

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        header = file.read(12)

        if ((header[4:8] == 'ftyp') and
            (header[8:12] in ('mp41', 'mp42', 'M4A ', 'M4B '))):
            file.seek(0, 0)
            atoms = __Qt_Atom_Stream__(file)
            try:
                return (ATOM_STSD.parse(atoms['moov']['trak']['mdia']['minf']['stbl']['stsd'].data).descriptions[0].type == 'alac')
            except (Con.ConstError, Con.FieldError, Con.ArrayError, KeyError,
                    IndexError):
                return False
        else:
            return False

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__length__

    def channel_mask(self):
        """Returns a ChannelMask object of this track's channel layout."""

        try:
            #FIXME - see if it's possible to find an actual channel mask
            #for multichannel ALAC audio
            return ChannelMask.from_channels(self.channels())
        except ValueError:
            return ChannelMask(0)

    def cd_frames(self):
        """Returns the total length of the track in CD frames.

        Each CD frame is 1/75th of a second."""

        try:
            return (self.total_frames() * 75) / self.sample_rate()
        except ZeroDivisionError:
            return 0

    def lossless(self):
        """Returns True."""

        return True

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        import audiotools.decoders

        try:
            f = file(self.filename, 'rb')
            qt = __Qt_Atom_Stream__(f)
            alac = ALACAudio.ALAC_ATOM.parse(
                ATOM_STSD.parse(
                    qt['moov']['trak']['mdia']['minf']['stbl'][
                        'stsd'].data).descriptions[0].data).alac
            f.close()

            return audiotools.decoders.ALACDecoder(
                filename=self.filename,
                sample_rate=alac.sample_rate,
                channels=alac.channels,
                channel_mask=self.channel_mask(),
                bits_per_sample=alac.sample_size,
                total_frames=self.total_frames(),
                max_samples_per_frame=alac.max_samples_per_frame,
                history_multiplier=alac.history_multiplier,
                initial_history=alac.initial_history,
                maximum_k=alac.maximum_k)
        except (Con.FieldError, Con.ArrayError, IOError, ValueError), msg:
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None,
                 block_size=4096):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new ALACAudio object."""

        if (pcmreader.bits_per_sample not in (16, 24)):
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        from . import encoders
        import time
        import tempfile

        mdat_file = tempfile.TemporaryFile()

        #perform encode_alac() on pcmreader to our output file
        #which returns a tuple of output values:
        #(framelist, - a list of (frame_samples,frame_size,frame_offset) tuples
        # various fields for the "alac" atom)
        try:
            (frame_sample_sizes,
             frame_byte_sizes,
             frame_file_offsets,
             mdat_size) = encoders.encode_alac(
                file=mdat_file,
                pcmreader=BufferedPCMReader(pcmreader),
                block_size=block_size,
                initial_history=cls.INITIAL_HISTORY,
                history_multiplier=cls.HISTORY_MULTIPLIER,
                maximum_k=cls.MAXIMUM_K)
        except (IOError, ValueError), err:
            raise EncodingError(str(err))

        #use the fields from encode_alac() to populate our ALAC atoms
        create_date = long(time.time()) + 2082844800
        total_pcm_frames = sum(frame_sample_sizes)

        stts_frame_counts = {}
        for sample_size in frame_sample_sizes:
            stts_frame_counts.setdefault(sample_size, __counter__()).incr()

        offsets = frame_file_offsets[:]
        chunks = []
        for frames in at_a_time(len(frame_file_offsets), 5):
            if (frames > 0):
                chunks.append(offsets[0:frames])
                offsets = offsets[frames:]
        del(offsets)

        #add the size of ftyp + moov + free to our absolute file offsets
        pre_mdat_size = (len(cls.__build_ftyp_atom__()) +
                         len(cls.__build_moov_atom__(pcmreader,
                                                     create_date,
                                                     mdat_size,
                                                     total_pcm_frames,
                                                     frame_sample_sizes,
                                                     stts_frame_counts,
                                                     chunks,
                                                     frame_byte_sizes)) +
                         len(cls.__build_free_atom__(0x1000)))
        chunks = [[chunk + pre_mdat_size for chunk in chunk_list]
                  for chunk_list in chunks]

        #then regenerate our live ftyp, moov and free atoms
        #with actual data
        ftyp = cls.__build_ftyp_atom__()

        moov = cls.__build_moov_atom__(pcmreader,
                                       create_date,
                                       mdat_size,
                                       total_pcm_frames,
                                       frame_sample_sizes,
                                       stts_frame_counts,
                                       chunks,
                                       frame_byte_sizes)

        free = cls.__build_free_atom__(0x1000)

        #build our complete output file
        try:
            f = file(filename, 'wb')

            mdat_file.seek(0, 0)
            f.write(ftyp)
            f.write(moov)
            f.write(free)
            transfer_data(mdat_file.read, f.write)
            f.close()
            mdat_file.close()
        except (IOError), err:
            mdat_file.close()
            raise EncodingError(str(err))

        return cls(filename)

    @classmethod
    def __build_ftyp_atom__(cls):
        return cls.ALAC_FTYP.build(
            Con.Container(major_brand='M4A ',
                          major_brand_version=0,
                          compatible_brands=['M4A ',
                                             'mp42',
                                             'isom',
                                             chr(0) * 4]))

    @classmethod
    def __build_moov_atom__(cls, pcmreader,
                            create_date,
                            mdat_size,
                            total_pcm_frames,
                            frame_sample_sizes,
                            stts_frame_counts,
                            chunks,
                            frame_byte_sizes):
        version = (chr(0) * 3) + chr(1) + (chr(0) * 4) + (
            "Python Audio Tools %s" % (VERSION))

        tool = Con.Struct('tool',
                          Con.UBInt32('size'),
                          Con.String('type', 4),
                          Con.Struct('data',
                                     Con.UBInt32('size'),
                                     Con.String('type', 4),
                                     Con.String(
                    'data',
                    lambda ctx: ctx["size"] - 8))).build(
            Con.Container(size=len(version) + 16,
                          type=chr(0xa9) + 'too',
                          data=Con.Container(size=len(version) + 8,
                                             type='data',
                                             data=version)))

        return cls.ALAC_MOOV.build(
            Con.Container(
                mvhd=Con.Container(version=0,
                                   flags=chr(0) * 3,
                                   created_mac_UTC_date=create_date,
                                   modified_mac_UTC_date=create_date,
                                   time_scale=pcmreader.sample_rate,
                                   duration=total_pcm_frames,
                                   playback_speed=0x10000,
                                   user_volume=0x100,
                                   windows=Con.Container(
                        geometry_matrix_a=0x10000,
                        geometry_matrix_b=0,
                        geometry_matrix_u=0,
                        geometry_matrix_c=0,
                        geometry_matrix_d=0x10000,
                        geometry_matrix_v=0,
                        geometry_matrix_x=0,
                        geometry_matrix_y=0,
                        geometry_matrix_w=0x40000000),
                                   quicktime_preview=0,
                                   quicktime_still_poster=0,
                                   quicktime_selection_time=0,
                                   quicktime_current_time=0,
                                   next_track_id=2),
                trak=Con.Container(
                    tkhd=Con.Container(version=0,
                                       flags=Con.Container(
                            TrackInPoster=0,
                            TrackInPreview=1,
                            TrackInMovie=1,
                            TrackEnabled=1),
                                       created_mac_UTC_date=create_date,
                                       modified_mac_UTC_date=create_date,
                                       track_id=1,
                                       duration=total_pcm_frames,
                                       video_layer=0,
                                       quicktime_alternate=0,
                                       volume=0x100,
                                       video=Con.Container(
                            geometry_matrix_a=0x10000,
                            geometry_matrix_b=0,
                            geometry_matrix_u=0,
                            geometry_matrix_c=0,
                            geometry_matrix_d=0x10000,
                            geometry_matrix_v=0,
                            geometry_matrix_x=0,
                            geometry_matrix_y=0,
                            geometry_matrix_w=0x40000000),
                                       video_width=0,
                                       video_height=0),
                    mdia=Con.Container(
                        mdhd=Con.Container(version=0,
                                           flags=chr(0) * 3,
                                           created_mac_UTC_date=create_date,
                                           modified_mac_UTC_date=create_date,
                                           time_scale=pcmreader.sample_rate,
                                           duration=total_pcm_frames,
                                           languages=Con.Container(
                                language=[0x15, 0x0E, 0x04]),
                                           quicktime_quality=0),
                        hdlr=Con.Container(
                            version=0,
                            flags=chr(0) * 3,
                            quicktime_type=chr(0) * 4,
                            subtype='soun',
                            quicktime_manufacturer=chr(0) * 4,
                            quicktime_component_reserved_flags=0,
                            quicktime_component_reserved_flags_mask=0,
                            component_name=""),
                        minf=Con.Container(
                            smhd=Con.Container(version=0,
                                               flags=chr(0) * 3,
                                               audio_balance=chr(0) * 2),
                            dinf=Con.Container(dref=Con.Container(
                                    version=0,
                                    flags=chr(0) * 3,
                                    references=[Con.Container(
                                            size=12,
                                            type='url ',
                                            data="\x00\x00\x00\x01")])),
                            stbl=Con.Container(stsd=Con.Container(
                                    version=0,
                                    flags=chr(0) * 3,
                                    descriptions=[Con.Container(
                                            type="alac",
                                            data=cls.ALAC_ATOM.build(
                                                Con.Container(
                                                    reserved=chr(0) * 6,
                                                    reference_index=1,
                                                    version=0,
                                                revision_level=0,
                                                vendor=chr(0) * 4,
                                                channels=pcmreader.channels,
                                                bits_per_sample=pcmreader.bits_per_sample,
                                                compression_id=0,
                                                audio_packet_size=0,
                                                sample_rate=chr(0xAC) + chr(0x44) + chr(0x00) + chr(0x00),
                                                alac=Con.Container(
                                                    length=36,
                                                    type='alac',
                                                    max_samples_per_frame=max(frame_sample_sizes),
                                                    sample_size=pcmreader.bits_per_sample,
                                                    history_multiplier=cls.HISTORY_MULTIPLIER,
                                                    initial_history=cls.INITIAL_HISTORY,
                                                    maximum_k=cls.MAXIMUM_K,
                                                    channels=pcmreader.channels,
                                                    unknown=0x00FF,
                                                    max_coded_frame_size=max(frame_byte_sizes),
                                                    bitrate=((mdat_size * 8 * pcmreader.sample_rate) / sum(frame_sample_sizes)),
                                                    sample_rate=pcmreader.sample_rate))))]),

                                stts=Con.Container(
                                    version=0,
                                    flags=chr(0) * 3,
                                    frame_size_counts=[
                                        Con.Container(
                                            frame_count=int(stts_frame_counts[samples]),
                                            duration=samples)
                                        for samples in
                                        reversed(sorted(stts_frame_counts.keys()))]),

                                stsc=Con.Container(
                                    version=0,
                                    flags=chr(0) * 3,
                                    block=[Con.Container(
                                            first_chunk=i + 1,
                                            samples_per_chunk=current,
                                            sample_description_index=1)
                                           for (i, (current, previous))
                                           in enumerate(zip(map(len, chunks),
                                                            [0] + map(len, chunks)))
                                           if (current != previous)]),

                                stsz=Con.Container(
                                    version=0,
                                    flags=chr(0) * 3,
                                    block_byte_size=0,
                                    block_byte_sizes=frame_byte_sizes),

                                stco=Con.Container(
                                    version=0,
                                    flags=chr(0) * 3,
                                    offset=[chunk[0] for chunk in chunks]))))),
                udta=Con.Container(
                    meta=Con.Container(
                        version=0,
                        flags=chr(0) * 3,
                        atoms=[Con.Container(
                                type='hdlr',
                                data=ATOM_HDLR.build(
                                    Con.Container(
                                        version=0,
                                        flags=chr(0) * 3,
                                        quicktime_type=chr(0) * 4,
                                        subtype='mdir',
                                        quicktime_manufacturer='appl',
                                        quicktime_component_reserved_flags=0,
                                        quicktime_component_reserved_flags_mask=0,
                                        component_name=""))),
                               Con.Container(
                                type='ilst',
                                data=tool),
                               Con.Container(
                                type='free',
                                data=chr(0) * 1024)]))))

    @classmethod
    def __build_free_atom__(cls, size):
        return Atom('free').build(Con.Container(
                type='free',
                data=chr(0) * size))

#######################
#AAC File
#######################


class InvalidAAC(InvalidFile):
    """Raised if some error occurs parsing AAC audio files."""

    pass


class AACAudio(AudioFile):
    """An AAC audio file.

    This is AAC data inside an ADTS container."""

    SUFFIX = "aac"
    NAME = SUFFIX
    DEFAULT_COMPRESSION = "100"
    COMPRESSION_MODES = tuple(["10"] + map(str, range(50, 500, 25)) + ["500"])
    BINARIES = ("faac", "faad")

    AAC_FRAME_HEADER = Con.BitStruct("aac_header",
                                 Con.Const(Con.Bits("sync", 12),
                                           0xFFF),
                                 Con.Bits("mpeg_id", 1),
                                 Con.Bits("mpeg_layer", 2),
                                 Con.Flag("protection_absent"),
                                 Con.Bits("profile", 2),
                                 Con.Bits("sampling_frequency_index", 4),
                                 Con.Flag("private"),
                                 Con.Bits("channel_configuration", 3),
                                 Con.Bits("original", 1),
                                 Con.Bits("home", 1),
                                 Con.Bits("copyright_identification_bit", 1),
                                 Con.Bits("copyright_identification_start", 1),
                                 Con.Bits("aac_frame_length", 13),
                                 Con.Bits("adts_buffer_fullness", 11),
                                 Con.Bits("no_raw_data_blocks_in_frame", 2),
                                 Con.If(
        lambda ctx: ctx["protection_absent"] == False,
        Con.Bits("crc_check", 16)))

    SAMPLE_RATES = [96000, 88200, 64000, 48000,
                    44100, 32000, 24000, 22050,
                    16000, 12000, 11025,  8000]

    def __init__(self, filename):
        """filename is a plain string."""

        self.filename = filename

        try:
            f = file(self.filename, "rb")
        except IOError, msg:
            raise InvalidAAC(str(msg))
        try:
            try:
                header = AACAudio.AAC_FRAME_HEADER.parse_stream(f)
            except Con.FieldError:
                raise InvalidAAC(_(u"Invalid ADTS frame header"))
            except Con.ConstError:
                raise InvalidAAC(_(u"Invalid ADTS frame header"))
            f.seek(0, 0)
            self.__channels__ = header.channel_configuration
            self.__bits_per_sample__ = 16  # floating point samples
            self.__sample_rate__ = AACAudio.SAMPLE_RATES[
                header.sampling_frequency_index]
            self.__frame_count__ = AACAudio.aac_frame_count(f)
        finally:
            f.close()

    @classmethod
    def is_type(cls, file):
        """Returns True if the given file object describes this format.

        Takes a seekable file pointer rewound to the start of the file."""

        try:
            header = AACAudio.AAC_FRAME_HEADER.parse_stream(file)
            return ((header.sync == 0xFFF) and
                    (header.mpeg_id == 1) and
                    (header.mpeg_layer == 0))
        except:
            return False

    def bits_per_sample(self):
        """Returns an integer number of bits-per-sample this track contains."""

        return self.__bits_per_sample__

    def channels(self):
        """Returns an integer number of channels this track contains."""

        return self.__channels__

    def lossless(self):
        """Returns False."""

        return False

    def total_frames(self):
        """Returns the total PCM frames of the track as an integer."""

        return self.__frame_count__ * 1024

    def sample_rate(self):
        """Returns the rate of the track's audio as an integer number of Hz."""

        return self.__sample_rate__

    def to_pcm(self):
        """Returns a PCMReader object containing the track's PCM data."""

        devnull = file(os.devnull, "ab")

        sub = subprocess.Popen([BIN['faad'], "-t", "-f", str(2), "-w",
                                self.filename],
                               stdout=subprocess.PIPE,
                               stderr=devnull)
        return PCMReader(sub.stdout,
                         sample_rate=self.sample_rate(),
                         channels=self.channels(),
                         channel_mask=int(self.channel_mask()),
                         bits_per_sample=self.bits_per_sample(),
                         process=sub)

    @classmethod
    def from_pcm(cls, filename, pcmreader, compression=None):
        """Encodes a new file from PCM data.

        Takes a filename string, PCMReader object
        and optional compression level string.
        Encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new AACAudio object."""

        import bisect

        if ((compression is None) or
            (compression not in cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if (pcmreader.sample_rate not in AACAudio.SAMPLE_RATES):
            sample_rates = list(sorted(AACAudio.SAMPLE_RATES))

            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=([sample_rates[0]] + sample_rates)[
                    bisect.bisect(sample_rates, pcmreader.sample_rate)],
                channels=max(pcmreader.channels, 2),
                channel_mask=ChannelMask.from_channels(
                    max(pcmreader.channels, 2)),
                bits_per_sample=pcmreader.bits_per_sample)
        elif (pcmreader.channels > 2):
            pcmreader = PCMConverter(
                pcmreader,
                sample_rate=pcmreader.sample_rate,
                channels=2,
                channel_mask=ChannelMask.from_channels(2),
                bits_per_sample=pcmreader.bits_per_sample)

        #faac requires files to end with .aac for some reason
        if (not filename.endswith(".aac")):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".aac")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

        devnull = file(os.devnull, "ab")

        sub = subprocess.Popen([BIN['faac'],
                                "-q", compression,
                                "-P",
                                "-R", str(pcmreader.sample_rate),
                                "-B", str(pcmreader.bits_per_sample),
                                "-C", str(pcmreader.channels),
                                "-X",
                                "-o", filename,
                                "-"],
                               stdin=subprocess.PIPE,
                               stderr=devnull,
                               preexec_fn=ignore_sigint)
        #Note: faac handles SIGINT on its own,
        #so trying to ignore it doesn't work like on most other encoders.

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

        if (sub.wait() == 0):
            if (tempfile is not None):
                filename = actual_filename
                f = file(filename, 'wb')
                tempfile.seek(0, 0)
                transfer_data(tempfile.read, f.write)
                f.close()
                tempfile.close()

            return AACAudio(filename)
        else:
            if (tempfile is not None):
                tempfile.close()
            raise EncodingError(u"error writing file with faac")

    @classmethod
    def aac_frames(cls, stream):
        """Takes an open file stream and yields (header, data) tuples.

        header is a Container parsed from AACAudio.AAC_FRAME_HEADER.
        data is a binary string of frame data."""

        while (True):
            try:
                header = AACAudio.AAC_FRAME_HEADER.parse_stream(stream)
            except Con.FieldError:
                break

            if (header.sync != 0xFFF):
                raise InvalidAAC(_(u"Invalid frame sync"))

            if (header.protection_absent):
                yield (header, stream.read(header.aac_frame_length - 7))
            else:
                yield (header, stream.read(header.aac_frame_length - 9))

    @classmethod
    def aac_frame_count(cls, stream):
        """Takes an open file stream and returns the total ADTS frames."""

        import sys
        total = 0
        while (True):
            try:
                header = AACAudio.AAC_FRAME_HEADER.parse_stream(stream)
            except Con.FieldError:
                break

            if (header.sync != 0xFFF):
                break

            total += 1

            if (header.protection_absent):
                stream.seek(header.aac_frame_length - 7, 1)
            else:
                stream.seek(header.aac_frame_length - 9, 1)

        return total
