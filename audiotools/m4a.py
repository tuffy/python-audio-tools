# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

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


from audiotools import (AudioFile, InvalidFile, BIN, Image)
from audiotools.m4a_atoms import *


class InvalidM4A(InvalidFile):
    pass


def get_m4a_atom(reader, *atoms):
    """given a BitstreamReader and atom name strings
    returns a (size, substream) of the final atom data
    (not including its 64-bit size/name header)
    after traversing the parent atoms
    """

    for (last, next_atom) in [(i == len(atoms), v)
                              for (i, v) in enumerate(atoms, 1)]:
        # assert(isinstance(next_atom, bytes))

        try:
            (length, stream_atom) = reader.parse("32u 4b")
            while stream_atom != next_atom:
                if (length - 8) >= 0:
                    reader.skip_bytes(length - 8)
                    (length, stream_atom) = reader.parse("32u 4b")
                else:
                    raise KeyError(next_atom)
            if last:
                return (length - 8, reader.substream(length - 8))
            else:
                reader = reader.substream(length - 8)
        except IOError:
            raise KeyError(next_atom)


def get_m4a_atom_offset(reader, *atoms):
    """given a BitstreamReader and atom name strings
    returns a (size, offset) of the final atom data
    (including its 64-bit size/name header)
    after traversing the parent atoms"""

    offset = 0

    for (last, next_atom) in [(i == len(atoms), v)
                              for (i, v) in enumerate(atoms, 1)]:
        # assert(isinstance(next_atom, bytes))

        try:
            (length, stream_atom) = reader.parse("32u 4b")
            offset += 8
            while stream_atom != next_atom:
                if (length - 8) > 0:
                    reader.skip_bytes(length - 8)
                    offset += (length - 8)
                    (length, stream_atom) = reader.parse("32u 4b")
                    offset += 8
                else:
                    raise KeyError(next_atom)
            if last:
                return (length, offset - 8)
            else:
                reader = reader.substream(length - 8)
        except IOError:
            raise KeyError(next_atom)


def has_m4a_atom(reader, *atoms):
    """given a BitstreamReader and atom name strings
    returns True if the final atom is present
    after traversing the parent atoms"""

    for (last, next_atom) in [(i == len(atoms), v)
                              for (i, v) in enumerate(atoms, 1)]:
        # assert(isinstance(next_atom, bytes))

        try:
            (length, stream_atom) = reader.parse("32u 4b")
            while stream_atom != next_atom:
                if (length - 8) > 0:
                    reader.skip_bytes(length - 8)
                    (length, stream_atom) = reader.parse("32u 4b")
                else:
                    return False
            if last:
                return True
            else:
                reader = reader.substream(length - 8)
        except IOError:
            return False


class M4ATaggedAudio(object):
    @classmethod
    def supports_metadata(cls):
        """returns True if this audio type supports MetaData"""

        return True

    def get_metadata(self):
        """returns a MetaData object, or None

        raises IOError if unable to read the file"""

        from audiotools.bitstream import BitstreamReader

        with BitstreamReader(open(self.filename, 'rb'), False) as reader:
            try:
                (meta_size,
                 meta_reader) = get_m4a_atom(reader, b"moov", b"udta", b"meta")
            except KeyError:
                return None

            return M4A_META_Atom.parse(b"meta", meta_size, meta_reader,
                                       {b"hdlr": M4A_HDLR_Atom,
                                        b"ilst": M4A_Tree_Atom,
                                        b"free": M4A_FREE_Atom,
                                        b"\xa9alb": M4A_ILST_Leaf_Atom,
                                        b"\xa9ART": M4A_ILST_Leaf_Atom,
                                        b'aART': M4A_ILST_Leaf_Atom,
                                        b"\xa9cmt": M4A_ILST_Leaf_Atom,
                                        b"covr": M4A_ILST_Leaf_Atom,
                                        b"cpil": M4A_ILST_Leaf_Atom,
                                        b"cprt": M4A_ILST_Leaf_Atom,
                                        b"\xa9day": M4A_ILST_Leaf_Atom,
                                        b"disk": M4A_ILST_Leaf_Atom,
                                        b"gnre": M4A_ILST_Leaf_Atom,
                                        b"----": M4A_ILST_Leaf_Atom,
                                        b"pgap": M4A_ILST_Leaf_Atom,
                                        b"rtng": M4A_ILST_Leaf_Atom,
                                        b"tmpo": M4A_ILST_Leaf_Atom,
                                        b"\xa9grp": M4A_ILST_Leaf_Atom,
                                        b"\xa9nam": M4A_ILST_Leaf_Atom,
                                        b"\xa9too": M4A_ILST_Leaf_Atom,
                                        b"trkn": M4A_ILST_Leaf_Atom,
                                        b"\xa9wrt": M4A_ILST_Leaf_Atom})

    def update_metadata(self, metadata, old_metadata=None):
        """takes this track's updated MetaData object
        as returned by get_metadata() and sets this track's metadata
        with any fields updated in that object

        old_metadata is the unmodifed metadata returned by get_metadata()

        raises IOError if unable to write the file
        """

        from audiotools.bitstream import BitstreamWriter
        from audiotools.bitstream import BitstreamReader
        import os.path

        if metadata is None:
            return

        if not isinstance(metadata, M4A_META_Atom):
            from audiotools.text import ERR_FOREIGN_METADATA
            raise ValueError(ERR_FOREIGN_METADATA)

        if old_metadata is None:
            # get_metadata() result may still be None, and that's okay
            old_metadata = self.get_metadata()

        # M4A streams often have *two* "free" atoms we can attempt to resize

        # first, attempt to resize the one inside the "meta" atom
        if ((old_metadata is not None) and
            metadata.has_child(b"free") and
            ((metadata.size() - metadata[b"free"].size()) <=
             old_metadata.size())):

            metadata.replace_child(
                M4A_FREE_Atom(old_metadata.size() -
                              (metadata.size() -
                               metadata[b"free"].size())))

            f = open(self.filename, 'r+b')
            (meta_size, meta_offset) = get_m4a_atom_offset(
                BitstreamReader(f, False), b"moov", b"udta", b"meta")
            f.seek(meta_offset + 8, 0)
            with BitstreamWriter(f, False) as writer:
                metadata.build(writer)
            # writer will close "f" when finished
        else:
            from audiotools import TemporaryFile

            # if there's insufficient room,
            # attempt to resize the outermost "free" also

            # this is only possible if the file is laid out correctly,
            # with "free" coming after "moov" but before "mdat"
            # FIXME

            # if neither fix is possible, the whole file must be rewritten
            # which also requires adjusting the "stco" atom offsets
            with open(self.filename, "rb") as f:
                m4a_tree = M4A_Tree_Atom.parse(
                    None,
                    os.path.getsize(self.filename),
                    BitstreamReader(f, False),
                    {b"moov": M4A_Tree_Atom,
                     b"trak": M4A_Tree_Atom,
                     b"mdia": M4A_Tree_Atom,
                     b"minf": M4A_Tree_Atom,
                     b"stbl": M4A_Tree_Atom,
                     b"stco": M4A_STCO_Atom,
                     b"udta": M4A_Tree_Atom})

            # find initial mdat offset
            initial_mdat_offset = m4a_tree.child_offset(b"mdat")

            # adjust moov -> udta -> meta atom
            # (generating sub-atoms as necessary)
            if not m4a_tree.has_child(b"moov"):
                return
            else:
                moov = m4a_tree[b"moov"]
            if not moov.has_child(b"udta"):
                moov.append_child(M4A_Tree_Atom(b"udta", []))
            udta = moov[b"udta"]
            if not udta.has_child(b"meta"):
                udta.append_child(metadata)
            else:
                udta.replace_child(metadata)

            # find new mdat offset
            new_mdat_offset = m4a_tree.child_offset(b"mdat")

            # adjust moov -> trak -> mdia -> minf -> stbl -> stco offsets
            # based on the difference between the new mdat position and the old
            try:
                delta_offset = new_mdat_offset - initial_mdat_offset
                stco = m4a_tree[b"moov"][b"trak"][b"mdia"][b"minf"][b"stbl"][b"stco"]
                stco.offsets = [offset + delta_offset for offset in
                                stco.offsets]
            except KeyError:
                # if there is no stco atom, don't worry about it
                pass

            # then write entire tree back to disk
            with BitstreamWriter(TemporaryFile(self.filename),
                                 False) as writer:
                m4a_tree.build(writer)

    def set_metadata(self, metadata):
        """takes a MetaData object and sets this track's metadata

        this metadata includes track name, album name, and so on
        raises IOError if unable to write the file"""

        if metadata is None:
            return self.delete_metadata()

        old_metadata = self.get_metadata()
        metadata = M4A_META_Atom.converted(metadata)

        # replace file-specific atoms in new metadata
        # with ones from old metadata (if any)
        # which can happen if we're shifting metadata
        # from one M4A file to another
        file_specific_atoms = {b'\xa9too', b'----', b'pgap', b'tmpo'}

        if metadata.has_ilst_atom():
            metadata.ilst_atom().leaf_atoms = [
                atom for atom in metadata.ilst_atom()
                if atom.name not in file_specific_atoms]

            if old_metadata.has_ilst_atom():
                metadata.ilst_atom().leaf_atoms.extend(
                    [atom for atom in old_metadata.ilst_atom()
                     if atom.name in file_specific_atoms])

        self.update_metadata(metadata, old_metadata)

    def delete_metadata(self):
        """deletes the track's MetaData

        this removes or unsets tags as necessary in order to remove all data
        raises IOError if unable to write the file"""

        from audiotools import MetaData

        self.set_metadata(MetaData())


class M4AAudio_faac(M4ATaggedAudio, AudioFile):
    """an M4A audio file using faac/faad binaries for I/O"""

    SUFFIX = "m4a"
    NAME = SUFFIX
    DESCRIPTION = u"Advanced Audio Coding"
    DEFAULT_COMPRESSION = "100"
    COMPRESSION_MODES = tuple(["10"] +
                              list(map(str, range(50, 500, 25))) +
                              ["500"])
    BINARIES = ("faac", "faad")
    BINARY_URLS = {"faac": "http://www.audiocoding.com/",
                   "faad": "http://www.audiocoding.com/"}

    def __init__(self, filename):
        """filename is a plain string"""

        from audiotools.bitstream import BitstreamReader

        AudioFile.__init__(self, filename)

        # first, fetch the mdia atom
        # which is the parent of both the mp4a and mdhd atoms
        try:
            with BitstreamReader(open(filename, "rb"), False) as reader:
                mdia = get_m4a_atom(reader,
                                    b"moov", b"trak", b"mdia")[1]
                mdia_start = mdia.getpos()
        except IOError:
            from audiotools.text import ERR_M4A_IOERROR
            raise InvalidM4A(ERR_M4A_IOERROR)
        except KeyError:
            from audiotools.text import ERR_M4A_MISSING_MDIA
            raise InvalidM4A(ERR_M4A_MISSING_MDIA)

        try:
            stsd = get_m4a_atom(mdia, b"minf", b"stbl", b"stsd")[1]
        except KeyError:
            from audiotools.text import ERR_M4A_MISSING_STSD
            raise InvalidM4A(ERR_M4A_MISSING_STSD)

        # then, fetch the mp4a atom for bps, channels and sample rate
        try:
            (stsd_version, descriptions) = stsd.parse("8u 24p 32u")
            (mp4a,
             self.__channels__,
             self.__bits_per_sample__) = stsd.parse(
                "32p 4b 48p 16p 16p 16p 4P 16u 16u 16p 16p 32p")
        except IOError:
            from audiotools.text import ERR_M4A_INVALID_MP4A
            raise InvalidM4A(ERR_M4A_INVALID_MP4A)

        # finally, fetch the mdhd atom for total track length
        mdia.setpos(mdia_start)
        try:
            mdhd = get_m4a_atom(mdia, b"mdhd")[1]
        except KeyError:
            from audiotools.text import ERR_M4A_MISSING_MDHD
            raise InvalidM4A(ERR_M4A_MISSING_MDHD)
        try:
            (version, ) = mdhd.parse("8u 24p")
            if version == 0:
                (self.__sample_rate__,
                 self.__length__,) = mdhd.parse("32p 32p 32u 32u 2P 16p")
            elif version == 1:
                (self.__sample_rate__,
                 self.__length__,) = mdhd.parse("64p 64p 32u 64U 2P 16p")
            else:
                from audiotools.text import ERR_M4A_UNSUPPORTED_MDHD
                raise InvalidM4A(ERR_M4A_UNSUPPORTED_MDHD)
        except IOError:
            from audiotools.text import ERR_M4A_INVALID_MDHD
            raise InvalidM4A(ERR_M4A_INVALID_MDHD)

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        from audiotools import ChannelMask

        # M4A seems to use the same channel assignment
        # as old-style RIFF WAVE/FLAC
        if self.channels() == 1:
            return ChannelMask.from_fields(
                front_center=True)
        elif self.channels() == 2:
            return ChannelMask.from_fields(
                front_left=True, front_right=True)
        elif self.channels() == 3:
            return ChannelMask.from_fields(
                front_left=True, front_right=True, front_center=True)
        elif self.channels() == 4:
            return ChannelMask.from_fields(
                front_left=True, front_right=True,
                back_left=True, back_right=True)
        elif self.channels() == 5:
            return ChannelMask.from_fields(
                front_left=True, front_right=True, front_center=True,
                back_left=True, back_right=True)
        elif self.channels() == 6:
            return ChannelMask.from_fields(
                front_left=True, front_right=True, front_center=True,
                back_left=True, back_right=True,
                low_frequency=True)
        else:
            return ChannelMask(0)

    def lossless(self):
        """returns False"""

        return False

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def cd_frames(self):
        """returns the total length of the track in CD frames

        each CD frame is 1/75th of a second"""

        return ((self.__length__ - 1024) * 75) // self.__sample_rate__

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__length__ - 1024

    @classmethod
    def supports_to_pcm(cls):
        """returns True if all necessary components are available
        to support the .to_pcm() method"""

        return BIN.can_execute(BIN["faad"])

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from audiotools import PCMFileReader
        import subprocess
        import os

        sub = subprocess.Popen(
            [BIN['faad'], "-f", str(2), "-w", self.filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"))
        return PCMFileReader(sub.stdout,
                             sample_rate=self.sample_rate(),
                             channels=self.channels(),
                             channel_mask=int(self.channel_mask()),
                             bits_per_sample=self.bits_per_sample(),
                             process=sub)

    @classmethod
    def supports_from_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        return BIN.can_execute(BIN["faac"])

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and optional
        total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new M4AAudio object"""

        import subprocess
        import os
        from audiotools import PCMConverter
        from audiotools import transfer_data
        from audiotools import transfer_framelist_data
        from audiotools import ignore_sigint
        from audiotools import EncodingError
        from audiotools import DecodingError
        from audiotools import ChannelMask
        from audiotools import __default_quality__

        if ((compression is None) or (compression not in
                                      cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        if pcmreader.channels > 2:
            pcmreader = PCMConverter(pcmreader,
                                     sample_rate=pcmreader.sample_rate,
                                     channels=2,
                                     channel_mask=ChannelMask.from_channels(2),
                                     bits_per_sample=pcmreader.bits_per_sample)

        # faac requires files to end with .m4a for some reason
        if not filename.endswith(".m4a"):
            import tempfile
            actual_filename = filename
            tempfile = tempfile.NamedTemporaryFile(suffix=".m4a")
            filename = tempfile.name
        else:
            actual_filename = tempfile = None

        sub = subprocess.Popen(
            [BIN['faac'],
             "-q", compression,
             "-P",
             "-R", str(pcmreader.sample_rate),
             "-B", str(pcmreader.bits_per_sample),
             "-C", str(pcmreader.channels),
             "-X",
             "-o", filename,
             "-"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"),
            stdout=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"),
            preexec_fn=ignore_sigint)
        # Note: faac handles SIGINT on its own,
        # so trying to ignore it doesn't work like on most other encoders.

        try:
            if total_pcm_frames is not None:
                from audiotools import CounterPCMReader
                pcmreader = CounterPCMReader(pcmreader)

            transfer_framelist_data(pcmreader, sub.stdin.write)

            if ((total_pcm_frames is not None) and
                (total_pcm_frames != pcmreader.frames_written)):
                from audiotools.text import ERR_TOTAL_PCM_FRAMES_MISMATCH
                raise EncodingError(ERR_TOTAL_PCM_FRAMES_MISMATCH)

        except (ValueError, IOError) as err:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception:
            sub.stdin.close()
            sub.wait()
            cls.__unlink__(filename)
            raise

        sub.stdin.close()

        if sub.wait() == 0:
            if tempfile is not None:
                filename = actual_filename
                f = open(filename, 'wb')
                tempfile.seek(0, 0)
                transfer_data(tempfile.read, f.write)
                f.close()
                tempfile.close()

            return M4AAudio(filename)
        else:
            if tempfile is not None:
                tempfile.close()
            raise EncodingError(u"unable to write file with faac")


class M4AAudio_nero(M4AAudio_faac):
    """an M4A audio file using neroAacEnc/neroAacDec binaries for I/O"""

    from audiotools.text import (COMP_NERO_LOW, COMP_NERO_HIGH)

    DEFAULT_COMPRESSION = "0.5"
    COMPRESSION_MODES = ("0.4", "0.5",
                         "0.6", "0.7", "0.8", "0.9", "1.0")
    COMPRESSION_DESCRIPTIONS = {"0.4": COMP_NERO_LOW,
                                "1.0": COMP_NERO_HIGH}
    BINARIES = ("neroAacDec", "neroAacEnc")
    BINARY_URLS = {"neroAacDec": "http://www.nero.com/enu/" +
                   "downloads-nerodigital-nero-aac-codec.php",
                   "neroAacEnc": "http://www.nero.com/enu/" +
                   "downloads-nerodigital-nero-aac-codec.php"}

    @classmethod
    def supports_from_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        return BIN.can_execute(BIN["neroAacEnc"])

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new M4AAudio object"""

        import tempfile
        import os
        import os.path
        from audiotools import PCMConverter
        from audiotools import WaveAudio
        from audiotools import __default_quality__

        if ((compression is None) or (compression not in
                                      cls.COMPRESSION_MODES)):
            compression = __default_quality__(cls.NAME)

        tempwavefile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tempwave_name = tempwavefile.name
        try:
            if pcmreader.sample_rate > 96000:
                tempwave = WaveAudio.from_pcm(
                    tempwave_name,
                    PCMConverter(pcmreader,
                                 sample_rate=96000,
                                 channels=pcmreader.channels,
                                 channel_mask=pcmreader.channel_mask,
                                 bits_per_sample=pcmreader.bits_per_sample),
                    total_pcm_frames=total_pcm_frames)
            else:
                tempwave = WaveAudio.from_pcm(
                    tempwave_name,
                    pcmreader,
                    total_pcm_frames=total_pcm_frames)

            cls.__from_wave__(filename, tempwave.filename, compression)
            return cls(filename)
        finally:
            tempwavefile.close()
            if os.path.isfile(tempwave_name):
                os.unlink(tempwave_name)

    @classmethod
    def supports_to_pcm(cls):
        """returns True if all necessary components are available
        to support the .to_pcm() method"""

        return BIN.can_execute(BIN["neroAacDec"])

    def to_pcm(self):
        from audiotools import PCMFileReader
        import subprocess
        import os

        sub = subprocess.Popen(
            [BIN["neroAacDec"],
             "-if", self.filename,
             "-of", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"))

        return PCMFileReader(file=sub.stdout,
                             sample_rate=self.sample_rate(),
                             channels=self.channels(),
                             channel_mask=int(self.channel_mask()),
                             bits_per_sample=self.bits_per_sample(),
                             process=sub)

    @classmethod
    def __from_wave__(cls, filename, wave_filename, compression):
        import subprocess
        import os
        from audiotools import EncodingError

        sub = subprocess.Popen(
            [BIN["neroAacEnc"],
             "-q", compression,
             "-if", wave_filename,
             "-of", filename],
            stdout=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"),
            stderr=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else
            open(os.devnull, "wb"))

        if sub.wait() != 0:
            raise EncodingError(u"neroAacEnc unable to write file")
        else:
            return cls(filename)

if BIN.can_execute(BIN["neroAacEnc"]) and BIN.can_execute(BIN["neroAacDec"]):
    M4AAudio = M4AAudio_nero
else:
    M4AAudio = M4AAudio_faac


class InvalidALAC(InvalidFile):
    pass


class ALACAudio(M4ATaggedAudio, AudioFile):
    """an Apple Lossless audio file"""

    SUFFIX = "m4a"
    NAME = "alac"
    DESCRIPTION = u"Apple Lossless"
    DEFAULT_COMPRESSION = ""
    COMPRESSION_MODES = ("",)
    BINARIES = tuple()

    BLOCK_SIZE = 4096
    INITIAL_HISTORY = 10
    HISTORY_MULTIPLIER = 40
    MAXIMUM_K = 14

    def __init__(self, filename):
        """filename is a plain string"""

        from audiotools.bitstream import BitstreamReader

        AudioFile.__init__(self, filename)

        # first, fetch the mdia atom
        # which is the parent of both the alac and mdhd atoms
        try:
            with BitstreamReader(open(filename, "rb"), False) as reader:
                mdia = get_m4a_atom(reader,
                                    b"moov", b"trak", b"mdia")[1]
                mdia_start = mdia.getpos()
        except IOError:
            from audiotools.text import ERR_ALAC_IOERROR
            raise InvalidALAC(ERR_ALAC_IOERROR)
        except KeyError:
            from audiotools.text import ERR_M4A_MISSING_MDIA
            raise InvalidALAC(ERR_M4A_MISSING_MDIA)

        try:
            stsd = get_m4a_atom(mdia, b"minf", b"stbl", b"stsd")[1]
        except KeyError:
            from audiotools.text import ERR_M4A_MISSING_STSD
            raise InvalidALAC(ERR_M4A_MISSING_STSD)

        # then, fetch the alac atom for bps, channels and sample rate
        try:
            # though some of these fields are parsed redundantly
            # in .to_pcm(), we still need to parse them here
            # to fetch values for .bits_per_sample(), etc.
            (stsd_version, descriptions) = stsd.parse("8u 24p 32u")
            (alac1,
             alac2,
             self.__max_samples_per_frame__,
             self.__bits_per_sample__,
             self.__history_multiplier__,
             self.__initial_history__,
             self.__maximum_k__,
             self.__channels__,
             self.__sample_rate__) = stsd.parse(
                # ignore much of the stuff in the "high" ALAC atom
                "32p 4b 6P 16p 16p 16p 4P 16p 16p 16p 16p 4P" +
                # and use the attributes in the "low" ALAC atom instead
                "32p 4b 4P 32u 8p 8u 8u 8u 8u 8u 16p 32p 32p 32u")
        except IOError:
            from audiotools.text import ERR_ALAC_INVALID_ALAC
            raise InvalidALAC(ERR_ALAC_INVALID_ALAC)

        if (alac1 != b'alac') or (alac2 != b'alac'):
            from audiotools.text import ERR_ALAC_INVALID_ALAC
            raise InvalidALAC(ERR_ALAC_INVALID_ALAC)

        # finally, fetch the mdhd atom for total track length
        mdia.setpos(mdia_start)
        try:
            mdhd = get_m4a_atom(mdia, b"mdhd")[1]
        except KeyError:
            from audiotools.text import ERR_M4A_MISSING_MDHD
            raise InvalidALAC(ERR_M4A_MISSING_MDHD)
        try:
            (version, ) = mdhd.parse("8u 24p")
            if version == 0:
                (self.__length__,) = mdhd.parse("32p 32p 32p 32u 2P 16p")
            elif version == 1:
                (self.__length__,) = mdhd.parse("64p 64p 32p 64U 2P 16p")
            else:
                from audiotools.text import ERR_M4A_UNSUPPORTED_MDHD
                raise InvalidALAC(ERR_M4A_UNSUPPORTED_MDHD)
        except IOError:
            from audiotools.text import ERR_M4A_INVALID_MDHD
            raise InvalidALAC(ERR_M4A_INVALID_MDHD)

    def channels(self):
        """returns an integer number of channels this track contains"""

        return self.__channels__

    def bits_per_sample(self):
        """returns an integer number of bits-per-sample this track contains"""

        return self.__bits_per_sample__

    def sample_rate(self):
        """returns the rate of the track's audio as an integer number of Hz"""

        return self.__sample_rate__

    def total_frames(self):
        """returns the total PCM frames of the track as an integer"""

        return self.__length__

    def channel_mask(self):
        """returns a ChannelMask object of this track's channel layout"""

        from audiotools import ChannelMask

        with self.to_pcm() as r:
            return ChannelMask(r.channel_mask)

    def cd_frames(self):
        """returns the total length of the track in CD frames

        each CD frame is 1/75th of a second"""

        try:
            return (self.total_frames() * 75) // self.sample_rate()
        except ZeroDivisionError:
            return 0

    def lossless(self):
        """returns True"""

        return True

    def seekable(self):
        """returns True if the file is seekable"""

        from audiotools.bitstream import BitstreamReader

        with BitstreamReader(open(self.filename, "rb"), False) as reader:
            stream_start = reader.getpos()
            has_stts = has_m4a_atom(reader,
                                    b"moov",
                                    b"trak",
                                    b"mdia",
                                    b"minf",
                                    b"stbl",
                                    b"stts")
            reader.setpos(stream_start)
            has_stsc = has_m4a_atom(reader,
                                    b"moov",
                                    b"trak",
                                    b"mdia",
                                    b"minf",
                                    b"stbl",
                                    b"stsc")
            reader.setpos(stream_start)
            has_stco = has_m4a_atom(reader,
                                    b"moov",
                                    b"trak",
                                    b"mdia",
                                    b"minf",
                                    b"stbl",
                                    b"stco")
            return has_stts and has_stsc and has_stco

    @classmethod
    def supports_to_pcm(cls):
        """returns True if all necessary components are available
        to support the .to_pcm() method"""

        try:
            from audiotools.decoders import ALACDecoder
            return True
        except ImportError:
            return False

    def to_pcm(self):
        """returns a PCMReader object containing the track's PCM data"""

        from audiotools.decoders import ALACDecoder
        from audiotools import PCMReaderError

        try:
            return ALACDecoder(open(self.filename, "rb"))
        except (IOError, ValueError) as msg:
            return PCMReaderError(error_message=str(msg),
                                  sample_rate=self.sample_rate(),
                                  channels=self.channels(),
                                  channel_mask=int(self.channel_mask()),
                                  bits_per_sample=self.bits_per_sample())

    @classmethod
    def supports_from_pcm(cls):
        """returns True if all necessary components are available
        to support the .from_pcm() classmethod"""

        try:
            from audiotools.encoders import encode_alac
            return True
        except ImportError:
            return False

    @classmethod
    def from_pcm(cls, filename, pcmreader,
                 compression=None, total_pcm_frames=None,
                 block_size=4096, encoding_function=None):
        """encodes a new file from PCM data

        takes a filename string, PCMReader object,
        optional compression level string and
        optional total_pcm_frames integer
        encodes a new audio file from pcmreader's data
        at the given filename with the specified compression level
        and returns a new ALACAudio object"""

        from audiotools.encoders import encode_alac
        from audiotools import VERSION,EncodingError

        if pcmreader.bits_per_sample not in {16, 24}:
            from audiotools import UnsupportedBitsPerSample

            pcmreader.close()
            raise UnsupportedBitsPerSample(filename, pcmreader.bits_per_sample)

        if (pcmreader.channel_mask not in
            {0x0001,    # 1ch - mono
             0x0004,    # 1ch - mono
             0x0003,    # 2ch - left, right
             0x0007,    # 3ch - center, left, right
             0x0107,    # 4ch - center, left, right, back center
             0x0037,    # 5ch - center, left, right, back left, back right
             0x003F,    # 6ch - C, L, R, back left, back right, LFE
             0x013F,    # 7ch - C, L, R, bL, bR, back center, LFE
             0x00FF,    # 8ch - C, cL, cR, L, R, bL, bR, LFE
             0x0000}):  # undefined
            from audiotools import UnsupportedChannelMask

            pcmreader.close()
            raise UnsupportedChannelMask(filename, pcmreader.channel_mask)

        try:
            file = open(filename, "wb")
        except IOError as err:
            pcmreader.close()
            raise EncodingError(str(err))

        try:
            encode_alac(
                file=file,
                pcmreader=pcmreader,
                total_pcm_frames=(total_pcm_frames if
                                  (total_pcm_frames is not None) else 0),
                block_size=block_size,
                initial_history=cls.INITIAL_HISTORY,
                history_multiplier=cls.HISTORY_MULTIPLIER,
                maximum_k=cls.MAXIMUM_K,
                version="Python Audio Tools " + VERSION)
        except (ValueError,IOError) as err:
            cls.__unlink__(filename)
            raise EncodingError(str(err))
        except Exception:
            cls.__unlink__(filename)
            raise
        finally:
            pcmreader.close()
            file.close()

        return cls(filename)
