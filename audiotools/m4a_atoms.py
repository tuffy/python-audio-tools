#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2013  Brian Langenberger

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

from . import MetaData, Image
from .image import image_metrics

#M4A atoms are typically laid on in the file as follows:
# ftyp
# mdat
# moov/
# +mvhd
# +iods
# +trak/
# +-tkhd
# +-mdia/
# +--mdhd
# +--hdlr
# +--minf/
# +---smhd
# +---dinf/
# +----dref
# +---stbl/
# +----stsd
# +----stts
# +----stsz
# +----stsc
# +----stco
# +----ctts
# +udta/
# +-meta
#
#Where atoms ending in / are container atoms and the rest are leaf atoms.
#'mdat' is where the file's audio stream is stored
#the rest are various bits of metadata


def parse_sub_atoms(data_size, reader, parsers):
    """data size is the length of the parent atom's data
    reader is a BitstreamReader
    parsers is a dict of leaf_name->parser()
    where parser is defined as:
    parser(leaf_name, leaf_data_size, BitstreamReader, parsers)
    as a sort of recursive parsing handler
    """

    leaf_atoms = []

    while (data_size > 0):
        (leaf_size, leaf_name) = reader.parse("32u 4b")
        leaf_atoms.append(
            parsers.get(leaf_name, M4A_Leaf_Atom).parse(
                leaf_name,
                leaf_size - 8,
                reader.substream(leaf_size - 8),
                parsers))
        data_size -= leaf_size

    return leaf_atoms

#build(), parse() and size() work on atom data
#but not the atom's size and name values


class M4A_Tree_Atom:
    def __init__(self, name, leaf_atoms):
        """name should be a 4 byte string

        children should be a list of M4A_Tree_Atoms or M4A_Leaf_Atoms"""

        self.name = name
        try:
            iter(leaf_atoms)
        except TypeError:
            from .text import ERR_M4A_INVALID_LEAF_ATOMS
            raise TypeError(ERR_M4A_INVALID_LEAF_ATOMS)
        self.leaf_atoms = leaf_atoms

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_Tree_Atom(self.name, [leaf.copy() for leaf in self])

    def __repr__(self):
        return "M4A_Tree_Atom(%s, %s)" % \
            (repr(self.name), repr(self.leaf_atoms))

    def __eq__(self, atom):
        for attr in ["name", "leaf_atoms"]:
            if ((not hasattr(atom, attr)) or (getattr(self, attr) !=
                                              getattr(atom, attr))):
                return False
        else:
            return True

    def __iter__(self):
        for leaf in self.leaf_atoms:
            yield leaf

    def __getitem__(self, atom_name):
        return self.get_child(atom_name)

    def get_child(self, atom_name):
        """returns the first instance of the given child atom
        raises KeyError if the child is not found"""

        for leaf in self:
            if (leaf.name == atom_name):
                return leaf
        else:
            raise KeyError(atom_name)

    def has_child(self, atom_name):
        """returns True if the given atom name
        is an immediate child of this atom"""

        for leaf in self:
            if (leaf.name == atom_name):
                return True
        else:
            return False

    def add_child(self, atom_obj):
        """adds the given child atom to this container"""

        self.leaf_atoms.append(atom_obj)

    def remove_child(self, atom_name):
        """removes the first instance of the given atom from this container"""

        new_leaf_atoms = []
        data_deleted = False
        for leaf_atom in self:
            if ((leaf_atom.name == atom_name) and (not data_deleted)):
                data_deleted = True
            else:
                new_leaf_atoms.append(leaf_atom)

        self.leaf_atoms = new_leaf_atoms

    def replace_child(self, atom_obj):
        """replaces the first instance of the given atom's name
        with the given atom"""

        new_leaf_atoms = []
        data_replaced = False
        for leaf_atom in self:
            if ((leaf_atom.name == atom_obj.name) and (not data_replaced)):
                new_leaf_atoms.append(atom_obj)
                data_replaced = True
            else:
                new_leaf_atoms.append(leaf_atom)

        self.leaf_atoms = new_leaf_atoms

    def child_offset(self, *child_path):
        """given a path to the given child atom
        returns its offset within this parent

        raises KeyError if the child cannot be found"""

        offset = 0
        next_child = child_path[0]
        for leaf_atom in self:
            if (leaf_atom.name == next_child):
                if (len(child_path) > 1):
                    return (offset + 8 +
                            leaf_atom.child_offset(*(child_path[1:])))
                else:
                    return offset
            else:
                offset += (8 + leaf_atom.size())
        else:
            raise KeyError(next_child)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        return cls(name, parse_sub_atoms(data_size, reader, parsers))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        for sub_atom in self:
            writer.build("32u 4b", (sub_atom.size() + 8, sub_atom.name))
            sub_atom.build(writer)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return sum([8 + sub_atom.size() for sub_atom in self])


class M4A_Leaf_Atom:
    def __init__(self, name, data):
        """name should be a 4 byte string

        data should be a binary string of atom data"""

        self.name = name
        self.data = data

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_Leaf_Atom(self.name, self.data)

    def __repr__(self):
        return "M4A_Leaf_Atom(%s, %s)" % \
            (repr(self.name), repr(self.data))

    def __eq__(self, atom):
        for attr in ["name", "data"]:
            if ((not hasattr(atom, attr)) or (getattr(self, attr) !=
                                              getattr(atom, attr))):
                return False
        else:
            return True

    def __unicode__(self):
        #FIXME - should make this more informative, if possible
        return self.data.encode('hex')[0:40].decode('ascii')

    def raw_info(self):
        """returns a line of human-readable information about the atom"""

        if (len(self.data) > 20):
            return u"%s : %s\u2026" % \
                (self.name.decode('ascii', 'replace'),
                 u"".join([u"%2.2X" % (ord(b)) for b in self.data[0:20]]))
        else:
            return u"%s : %s" % \
                (self.name.decode('ascii', 'replace'),
                 u"".join([u"%2.2X" % (ord(b)) for b in self.data]))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        return cls(name, reader.read_bytes(data_size))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.write_bytes(self.data)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return len(self.data)


class M4A_FTYP_Atom(M4A_Leaf_Atom):
    def __init__(self, major_brand, major_brand_version, compatible_brands):
        self.name = 'ftyp'
        self.major_brand = major_brand
        self.major_brand_version = major_brand_version
        self.compatible_brands = compatible_brands

    def __repr__(self):
        return "M4A_FTYP_Atom(%s, %s, %s)" % \
            (repr(self.major_brand),
             repr(self.major_brand_version),
             repr(self.compatible_brands))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == 'ftyp')
        return cls(reader.read_bytes(4),
                   reader.read(32),
                   [reader.read_bytes(4)
                    for i in xrange((data_size - 8) / 4)])

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("4b 32u %d* 4b" % (len(self.compatible_brands)),
                     [self.major_brand,
                      self.major_brand_version] +
                     self.compatible_brands)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 4 + 4 + (4 * len(self.compatible_brands))


class M4A_MVHD_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, created_utc_date, modified_utc_date,
                 time_scale, duration, playback_speed, user_volume,
                 geometry_matrices, qt_preview, qt_still_poster,
                 qt_selection_time, qt_current_time, next_track_id):
        self.name = 'mvhd'
        self.version = version
        self.flags = flags
        self.created_utc_date = created_utc_date
        self.modified_utc_date = modified_utc_date
        self.time_scale = time_scale
        self.duration = duration
        self.playback_speed = playback_speed
        self.user_volume = user_volume
        self.geometry_matrices = geometry_matrices
        self.qt_preview = qt_preview
        self.qt_still_poster = qt_still_poster
        self.qt_selection_time = qt_selection_time
        self.qt_current_time = qt_current_time
        self.next_track_id = next_track_id

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == 'mvhd')
        (version, flags) = reader.parse("8u 24u")

        if (version == 0):
            atom_format = "32u 32u 32u 32u 32u 16u 10P"
        else:
            atom_format = "64U 64U 32u 64U 32u 16u 10P"
        (created_utc_date,
         modified_utc_date,
         time_scale,
         duration,
         playback_speed,
         user_volume) = reader.parse(atom_format)

        geometry_matrices = reader.parse("32u" * 9)

        (qt_preview,
         qt_still_poster,
         qt_selection_time,
         qt_current_time,
         next_track_id) = reader.parse("64U 32u 64U 32u 32u")

        return cls(version=version,
                   flags=flags,
                   created_utc_date=created_utc_date,
                   modified_utc_date=modified_utc_date,
                   time_scale=time_scale,
                   duration=duration,
                   playback_speed=playback_speed,
                   user_volume=user_volume,
                   geometry_matrices=geometry_matrices,
                   qt_preview=qt_preview,
                   qt_still_poster=qt_still_poster,
                   qt_selection_time=qt_selection_time,
                   qt_current_time=qt_current_time,
                   next_track_id=next_track_id)

    def __repr__(self):
        return "MVHD_Atom(%s)" % (
            ",".join(map(repr,
                         [self.version, self.flags,
                          self.created_utc_date, self.modified_utc_date,
                          self.time_scale, self.duration, self.playback_speed,
                          self.user_volume, self.geometry_matrices,
                          self.qt_preview, self.qt_still_poster,
                          self.qt_selection_time, self.qt_current_time,
                          self.next_track_id])))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u", (self.version, self.flags))

        if (self.version == 0):
            atom_format = "32u 32u 32u 32u 32u 16u 10P"
        else:
            atom_format = "64U 64U 32u 64U 32u 16u 10P"

        writer.build(atom_format,
                     (self.created_utc_date, self.modified_utc_date,
                      self.time_scale, self.duration,
                      self.playback_speed, self.user_volume))

        writer.build("9* 32u", self.geometry_matrices)

        writer.build("64U 32u 64U 32u 32u",
                     (self.qt_preview, self.qt_still_poster,
                      self.qt_selection_time, self.qt_current_time,
                      self.next_track_id))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        if (self.version == 0):
            return 100
        else:
            return 112


class M4A_TKHD_Atom(M4A_Leaf_Atom):
    def __init__(self, version, track_in_poster, track_in_preview,
                 track_in_movie, track_enabled, created_utc_date,
                 modified_utc_date, track_id, duration, video_layer,
                 qt_alternate, volume, geometry_matrices,
                 video_width, video_height):
        self.name = 'tkhd'
        self.version = version
        self.track_in_poster = track_in_poster
        self.track_in_preview = track_in_preview
        self.track_in_movie = track_in_movie
        self.track_enabled = track_enabled
        self.created_utc_date = created_utc_date
        self.modified_utc_date = modified_utc_date
        self.track_id = track_id
        self.duration = duration
        self.video_layer = video_layer
        self.qt_alternate = qt_alternate
        self.volume = volume
        self.geometry_matrices = geometry_matrices
        self.video_width = video_width
        self.video_height = video_height

    def __repr__(self):
        return "M4A_TKHD_Atom(%s)" % (
            ",".join(map(repr,
                         [self.version, self.track_in_poster,
                          self.track_in_preview, self.track_in_movie,
                          self.track_enabled, self.created_utc_date,
                          self.modified_utc_date, self.track_id,
                          self.duration, self.video_layer, self.qt_alternate,
                          self.volume, self.geometry_matrices,
                          self.video_width, self.video_height])))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (version,
         track_in_poster,
         track_in_preview,
         track_in_movie,
         track_enabled) = reader.parse("8u 20p 1u 1u 1u 1u")

        if (version == 0):
            atom_format = "32u 32u 32u 4P 32u 8P 16u 16u 16u 2P"
        else:
            atom_format = "64U 64U 32u 4P 64U 8P 16u 16u 16u 2P"
        (created_utc_date,
         modified_utc_date,
         track_id,
         duration,
         video_layer,
         qt_alternate,
         volume) = reader.parse(atom_format)

        geometry_matrices = reader.parse("9* 32u")
        (video_width, video_height) = reader.parse("32u 32u")

        return cls(version=version,
                   track_in_poster=track_in_poster,
                   track_in_preview=track_in_preview,
                   track_in_movie=track_in_movie,
                   track_enabled=track_enabled,
                   created_utc_date=created_utc_date,
                   modified_utc_date=modified_utc_date,
                   track_id=track_id,
                   duration=duration,
                   video_layer=video_layer,
                   qt_alternate=qt_alternate,
                   volume=volume,
                   geometry_matrices=geometry_matrices,
                   video_width=video_width,
                   video_height=video_height)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 20p 1u 1u 1u 1u",
                     (self.version, self.track_in_poster,
                      self.track_in_preview, self.track_in_movie,
                      self.track_enabled))
        if (self.version == 0):
            atom_format = "32u 32u 32u 4P 32u 8P 16u 16u 16u 2P"
        else:
            atom_format = "64U 64U 32u 4P 64U 8P 16u 16u 16u 2P"
        writer.build(atom_format,
                     (self.created_utc_date, self.modified_utc_date,
                      self.track_id, self.duration, self.video_layer,
                      self.qt_alternate, self.volume))
        writer.build("9* 32u", self.geometry_matrices)
        writer.build("32u 32u", (self.video_width, self.video_height))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        if (self.version == 0):
            return 84
        else:
            return 96


class M4A_MDHD_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, created_utc_date, modified_utc_date,
                 sample_rate, track_length, language, quality):
        self.name = 'mdhd'
        self.version = version
        self.flags = flags
        self.created_utc_date = created_utc_date
        self.modified_utc_date = modified_utc_date
        self.sample_rate = sample_rate
        self.track_length = track_length
        self.language = language
        self.quality = quality

    def __repr__(self):
        return "M4A_MDHD_Atom(%s)" % \
            (",".join(map(repr,
                          [self.version, self.flags, self.created_utc_date,
                           self.modified_utc_date, self.sample_rate,
                           self.track_length, self.language, self.quality])))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == 'mdhd')
        (version, flags) = reader.parse("8u 24u")
        if (version == 0):
            atom_format = "32u 32u 32u 32u"
        else:
            atom_format = "64U 64U 32u 64U"
        (created_utc_date,
         modified_utc_date,
         sample_rate,
         track_length) = reader.parse(atom_format)
        language = reader.parse("1p 5u 5u 5u")
        quality = reader.read(16)

        return cls(version=version,
                   flags=flags,
                   created_utc_date=created_utc_date,
                   modified_utc_date=modified_utc_date,
                   sample_rate=sample_rate,
                   track_length=track_length,
                   language=language,
                   quality=quality)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u", (self.version, self.flags))
        if (self.version == 0):
            atom_format = "32u 32u 32u 32u"
        else:
            atom_format = "64U 64U 32u 64U"
        writer.build(atom_format,
                     (self.created_utc_date, self.modified_utc_date,
                      self.sample_rate, self.track_length))
        writer.build("1p 5u 5u 5u", self.language)
        writer.write(16, self.quality)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        if (self.version == 0):
            return 24
        else:
            return 36


class M4A_SMHD_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, audio_balance):
        self.name = 'smhd'
        self.version = version
        self.flags = flags
        self.audio_balance = audio_balance

    def __repr__(self):
        return "M4A_SMHD_Atom(%s)" % \
            (",".join(map(repr, (self.version,
                                 self.flags,
                                 self.audio_balance))))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        return cls(*reader.parse("8u 24u 16u 16p"))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 16u 16p",
                     (self.version, self.flags, self.audio_balance))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8


class M4A_DREF_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, references):
        self.name = 'dref'
        self.version = version
        self.flags = flags
        self.references = references

    def __repr__(self):
        return "M4A_DREF_Atom(%s)" % \
            (",".join(map(repr, (self.version,
                                 self.flags,
                                 self.references))))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (version, flags, reference_count) = reader.parse("8u 24u 32u")
        references = []
        for i in xrange(reference_count):
            (leaf_size, leaf_name) = reader.parse("32u 4b")
            references.append(
                M4A_Leaf_Atom.parse(
                    leaf_name, leaf_size - 8,
                    reader.substream(leaf_size - 8), {}))
        return cls(version, flags, references)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32u", (self.version,
                                    self.flags,
                                    len(self.references)))

        for reference_atom in self.references:
            writer.build("32u 4b", (reference_atom.size() + 8,
                                    reference_atom.name))
            reference_atom.build(writer)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + sum([reference_atom.size() + 8
                        for reference_atom in self.references])


class M4A_STSD_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, descriptions):
        self.name = 'stsd'
        self.version = version
        self.flags = flags
        self.descriptions = descriptions

    def __repr__(self):
        return "M4A_STSD_Atom(%s, %s, %s)" % \
            (repr(self.version), repr(self.flags), repr(self.descriptions))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (version, flags, description_count) = reader.parse("8u 24u 32u")
        descriptions = []
        for i in xrange(description_count):
            (leaf_size, leaf_name) = reader.parse("32u 4b")
            descriptions.append(
                parsers.get(leaf_name, M4A_Leaf_Atom).parse(
                    leaf_name,
                    leaf_size - 8,
                    reader.substream(leaf_size - 8),
                    parsers))
        return cls(version=version,
                   flags=flags,
                   descriptions=descriptions)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32u", (self.version,
                                    self.flags,
                                    len(self.descriptions)))

        for description_atom in self.descriptions:
            writer.build("32u 4b", (description_atom.size() + 8,
                                    description_atom.name))
            description_atom.build(writer)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + sum([8 + description_atom.size()
                        for description_atom in self.descriptions])


class M4A_STTS_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, times):
        self.name = 'stts'
        self.version = version
        self.flags = flags
        self.times = times

    def __repr__(self):
        return "M4A_STTS_Atom(%s, %s, %s)" % \
            (repr(self.version), repr(self.flags), repr(self.times))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (version, flags) = reader.parse("8u 24u")
        return cls(version=version,
                   flags=flags,
                   times=[tuple(reader.parse("32u 32u"))
                          for i in xrange(reader.read(32))])

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32u", (self.version, self.flags, len(self.times)))
        for time in self.times:
            writer.build("32u 32u", time)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + (8 * len(self.times))


class M4A_STSC_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, blocks):
        self.name = 'stsc'
        self.version = version
        self.flags = flags
        self.blocks = blocks

    def __repr__(self):
        return "M4A_STSC_Atom(%s, %s, %s)" % \
            (repr(self.version), repr(self.flags), repr(self.blocks))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (version, flags) = reader.parse("8u 24u")
        return cls(version=version,
                   flags=flags,
                   blocks=[tuple(reader.parse("32u 32u 32u"))
                           for i in xrange(reader.read(32))])

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32u",
                     (self.version, self.flags, len(self.blocks)))
        for block in self.blocks:
            writer.build("32u 32u 32u", block)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + (12 * len(self.blocks))


class M4A_STSZ_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, byte_size, block_sizes):
        self.name = 'stsz'
        self.version = version
        self.flags = flags
        self.byte_size = byte_size
        self.block_sizes = block_sizes

    def __repr__(self):
        return "M4A_STSZ_Atom(%s, %s, %s, %s)" % \
            (repr(self.version), repr(self.flags), repr(self.byte_size),
             repr(self.block_sizes))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (version, flags, byte_size) = reader.parse("8u 24u 32u")
        return cls(version=version,
                   flags=flags,
                   byte_size=byte_size,
                   block_sizes=[reader.read(32) for i in
                                xrange(reader.read(32))])

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32u 32u", (self.version,
                                        self.flags,
                                        self.byte_size,
                                        len(self.block_sizes)))
        for size in self.block_sizes:
            writer.write(32, size)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 12 + (4 * len(self.block_sizes))


class M4A_STCO_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, offsets):
        self.name = 'stco'
        self.version = version
        self.flags = flags
        self.offsets = offsets

    def __repr__(self):
        return "M4A_STCO_Atom(%s, %s, %s)" % \
            (self.version, self.flags, self.offsets)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "stco")
        (version, flags, offset_count) = reader.parse("8u 24u 32u")
        return cls(version, flags,
                   [reader.read(32) for i in xrange(offset_count)])

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32u", (self.version, self.flags,
                                    len(self.offsets)))
        for offset in self.offsets:
            writer.write(32, offset)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + (4 * len(self.offsets))


class M4A_ALAC_Atom(M4A_Leaf_Atom):
    def __init__(self, reference_index, qt_version, qt_revision_level,
                 qt_vendor, channels, bits_per_sample, qt_compression_id,
                 audio_packet_size, sample_rate, sub_alac):
        self.name = 'alac'
        self.reference_index = reference_index
        self.qt_version = qt_version
        self.qt_revision_level = qt_revision_level
        self.qt_vendor = qt_vendor
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.qt_compression_id = qt_compression_id
        self.audio_packet_size = audio_packet_size
        self.sample_rate = sample_rate
        self.sub_alac = sub_alac

    def __repr__(self):
        return "M4A_ALAC_Atom(%s)" % \
            ",".join(map(repr, [self.reference_index,
                                self.qt_version,
                                self.qt_revision_level,
                                self.qt_vendor,
                                self.channels,
                                self.bits_per_sample,
                                self.qt_compression_id,
                                self.audio_packet_size,
                                self.sample_rate,
                                self.sub_alac]))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        (reference_index,
         qt_version,
         qt_revision_level,
         qt_vendor,
         channels,
         bits_per_sample,
         qt_compression_id,
         audio_packet_size,
         sample_rate) = reader.parse(
             "6P 16u 16u 16u 4b 16u 16u 16u 16u 32u")
        (sub_alac_size, sub_alac_name) = reader.parse("32u 4b")
        sub_alac = M4A_SUB_ALAC_Atom.parse(sub_alac_name,
                                           sub_alac_size - 8,
                                           reader.substream(sub_alac_size - 8),
                                           {})
        return cls(reference_index=reference_index,
                   qt_version=qt_version,
                   qt_revision_level=qt_revision_level,
                   qt_vendor=qt_vendor,
                   channels=channels,
                   bits_per_sample=bits_per_sample,
                   qt_compression_id=qt_compression_id,
                   audio_packet_size=audio_packet_size,
                   sample_rate=sample_rate,
                   sub_alac=sub_alac)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("6P 16u 16u 16u 4b 16u 16u 16u 16u 32u",
                     (self.reference_index,
                      self.qt_version,
                      self.qt_revision_level,
                      self.qt_vendor,
                      self.channels,
                      self.bits_per_sample,
                      self.qt_compression_id,
                      self.audio_packet_size,
                      self.sample_rate))
        writer.build("32u 4b", (self.sub_alac.size() + 8,
                                self.sub_alac.name))
        self.sub_alac.build(writer)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 28 + 8 + self.sub_alac.size()


class M4A_SUB_ALAC_Atom(M4A_Leaf_Atom):
    def __init__(self, max_samples_per_frame, bits_per_sample,
                 history_multiplier, initial_history, maximum_k,
                 channels, unknown, max_coded_frame_size, bitrate,
                 sample_rate):
        self.name = 'alac'
        self.max_samples_per_frame = max_samples_per_frame
        self.bits_per_sample = bits_per_sample
        self.history_multiplier = history_multiplier
        self.initial_history = initial_history
        self.maximum_k = maximum_k
        self.channels = channels
        self.unknown = unknown
        self.max_coded_frame_size = max_coded_frame_size
        self.bitrate = bitrate
        self.sample_rate = sample_rate

    def __repr__(self):
        return "M4A_SUB_ALAC_Atom(%s)" % \
            (",".join(map(repr, [self.max_samples_per_frame,
                                 self.bits_per_sample,
                                 self.history_multiplier,
                                 self.initial_history,
                                 self.maximum_k,
                                 self.channels,
                                 self.unknown,
                                 self.max_coded_frame_size,
                                 self.bitrate,
                                 self.sample_rate])))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        return cls(
            *reader.parse(
                "4P 32u 8p 8u 8u 8u 8u 8u 16u 32u 32u 32u"))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("4P 32u 8p 8u 8u 8u 8u 8u 16u 32u 32u 32u",
                     (self.max_samples_per_frame,
                      self.bits_per_sample,
                      self.history_multiplier,
                      self.initial_history,
                      self.maximum_k,
                      self.channels,
                      self.unknown,
                      self.max_coded_frame_size,
                      self.bitrate,
                      self.sample_rate))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 28


class M4A_META_Atom(MetaData, M4A_Tree_Atom):
    UNICODE_ATTRIB_TO_ILST = {"track_name": "\xa9nam",
                              "album_name": "\xa9alb",
                              "artist_name": "\xa9ART",
                              "composer_name": "\xa9wrt",
                              "copyright": "cprt",
                              "year": "\xa9day",
                              "comment": "\xa9cmt"}

    INT_ATTRIB_TO_ILST = {"track_number": "trkn",
                          "album_number": "disk"}

    TOTAL_ATTRIB_TO_ILST = {"track_total": "trkn",
                            "album_total": "disk"}

    def __init__(self, version, flags, leaf_atoms):
        M4A_Tree_Atom.__init__(self, "meta", leaf_atoms)
        self.__dict__["version"] = version
        self.__dict__["flags"] = flags

    def __repr__(self):
        return "M4A_META_Atom(%s, %s, %s)" % \
            (repr(self.version), repr(self.flags), repr(self.leaf_atoms))

    def has_ilst_atom(self):
        """returns True if this atom contains an ILST sub-atom"""

        for a in self.leaf_atoms:
            if (a.name == 'ilst'):
                return True
        else:
            return False

    def ilst_atom(self):
        """returns the first ILST sub-atom, or None"""

        for a in self.leaf_atoms:
            if (a.name == 'ilst'):
                return a
        else:
            return None

    def add_ilst_atom(self):
        """place new ILST atom after the first HDLR atom, if any"""

        for (index, atom) in enumerate(self.leaf_atoms):
            if (atom.name == 'hdlr'):
                self.leaf_atoms.insert(index, M4A_Tree_Atom('ilst', []))
                break
        else:
            self.leaf_atoms.append(M4A_Tree_Atom('ilst', []))

    def raw_info(self):
        """returns a Unicode string of low-level MetaData information

        whereas __unicode__ is meant to contain complete information
        at a very high level
        raw_info() should be more developer-specific and with
        very little adjustment or reordering to the data itself
        """

        from os import linesep

        if (self.has_ilst_atom()):
            comment_lines = [u"M4A:"]

            for atom in self.ilst_atom():
                if (hasattr(atom, "raw_info_lines")):
                    comment_lines.extend(atom.raw_info_lines())
                else:
                    comment_lines.append(u"%s : (%d bytes)" %
                                         (atom.name.decode('ascii', 'replace'),
                                          atom.size()))

            return linesep.decode('ascii').join(comment_lines)
        else:
            return u""

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "meta")
        (version, flags) = reader.parse("8u 24u")
        return cls(version, flags,
                   parse_sub_atoms(data_size - 4, reader, parsers))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u", (self.version, self.flags))
        for sub_atom in self:
            writer.build("32u 4b", (sub_atom.size() + 8, sub_atom.name))
            sub_atom.build(writer)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 4 + sum([8 + sub_atom.size() for sub_atom in self])

    def __getattr__(self, attr):
        if (attr in self.UNICODE_ATTRIB_TO_ILST):
            if (self.has_ilst_atom()):
                try:
                    return unicode(
                        self.ilst_atom()[
                            self.UNICODE_ATTRIB_TO_ILST[attr]]['data'])
                except KeyError:
                    return None
            else:
                return None
        elif (attr in self.INT_ATTRIB_TO_ILST):
            if (self.has_ilst_atom()):
                try:
                    return self.ilst_atom()[
                        self.INT_ATTRIB_TO_ILST[attr]]['data'].number()
                except KeyError:
                    return None
            else:
                return None
        elif (attr in self.TOTAL_ATTRIB_TO_ILST):
            if (self.has_ilst_atom()):
                try:
                    return self.ilst_atom()[
                        self.TOTAL_ATTRIB_TO_ILST[attr]]['data'].total()
                except KeyError:
                    return None
            else:
                return None
        elif (attr in self.FIELDS):
            return None
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        def new_data_atom(attribute, value):
            if (attribute in self.UNICODE_ATTRIB_TO_ILST):
                return M4A_ILST_Unicode_Data_Atom(0, 1, value.encode('utf-8'))
            elif (attribute == "track_number"):
                return M4A_ILST_TRKN_Data_Atom(int(value), 0)
            elif (attribute == "track_total"):
                return M4A_ILST_TRKN_Data_Atom(0, int(value))
            elif (attribute == "album_number"):
                return M4A_ILST_DISK_Data_Atom(int(value), 0)
            elif (attribute == "album_total"):
                return M4A_ILST_DISK_Data_Atom(0, int(value))
            else:
                raise ValueError(value)

        def replace_data_atom(attribute, parent_atom, value):
            new_leaf_atoms = []
            data_replaced = False
            for leaf_atom in parent_atom.leaf_atoms:
                if ((leaf_atom.name == 'data') and (not data_replaced)):
                    if (attribute == "track_number"):
                        new_leaf_atoms.append(
                            M4A_ILST_TRKN_Data_Atom(int(value),
                                                    leaf_atom.track_total))
                    elif (attribute == "track_total"):
                        new_leaf_atoms.append(
                            M4A_ILST_TRKN_Data_Atom(leaf_atom.track_number,
                                                    int(value)))
                    elif (attribute == "album_number"):
                        new_leaf_atoms.append(
                            M4A_ILST_DISK_Data_Atom(int(value),
                                                    leaf_atom.disk_total))
                    elif (attribute == "album_total"):
                        new_leaf_atoms.append(
                            M4A_ILST_DISK_Data_Atom(leaf_atom.disk_number,
                                                    int(value)))
                    else:
                        new_leaf_atoms.append(new_data_atom(attribute, value))

                    data_replaced = True
                else:
                    new_leaf_atoms.append(leaf_atom)

            parent_atom.leaf_atoms = new_leaf_atoms

        if (value is None):
            delattr(self, attr)
            return

        ilst_leaf = self.UNICODE_ATTRIB_TO_ILST.get(
            attr,
            self.INT_ATTRIB_TO_ILST.get(
                attr,
                self.TOTAL_ATTRIB_TO_ILST.get(
                    attr,
                    None)))

        if (ilst_leaf is not None):
            if (not self.has_ilst_atom()):
                self.add_ilst_atom()

            #an ilst atom is present, so check its sub-atoms
            for ilst_atom in self.ilst_atom():
                if (ilst_atom.name == ilst_leaf):
                    #atom already present, so adjust its data sub-atom
                    replace_data_atom(attr, ilst_atom, value)
                    break
            else:
                #atom not present, so append new parent and data sub-atom
                self.ilst_atom().add_child(
                    M4A_ILST_Leaf_Atom(ilst_leaf,
                                       [new_data_atom(attr, value)]))
        else:
            #attribute is not an atom, so pass it through
            self.__dict__[attr] = value
            return

    def __delattr__(self, attr):
        if (self.has_ilst_atom()):
            ilst_atom = self.ilst_atom()

            if (attr in self.UNICODE_ATTRIB_TO_ILST):
                ilst_atom.leaf_atoms = filter(
                    lambda atom: atom.name !=
                    self.UNICODE_ATTRIB_TO_ILST[attr],
                    ilst_atom)
            elif (attr == "track_number"):
                if (self.track_total is None):
                    #if track_number and track_total are both 0
                    #remove trkn atom
                    ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "trkn", ilst_atom)
                else:
                    self.track_number = 0
            elif (attr == "track_total"):
                if (self.track_number is None):
                    #if track_number and track_total are both 0
                    #remove trkn atom
                    ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "trkn", ilst_atom)
                else:
                    self.track_total = 0
            elif (attr == "album_number"):
                if (self.album_total is None):
                    #if album_number and album_total are both 0
                    #remove disk atom
                    ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "disk", ilst_atom)
                else:
                    self.album_number = 0
            elif (attr == "album_total"):
                if (self.album_number is None):
                    #if album_number and album_total are both 0
                    #remove disk atom
                    ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "disk", ilst_atom)
                else:
                    self.album_total = 0
            else:
                try:
                    del(self.__dict__[attr])
                except KeyError:
                    raise AttributeError(attr)

    def images(self):
        """returns a list of embedded Image objects"""

        if (self.has_ilst_atom()):
            return [atom['data'] for atom in self.ilst_atom()
                    if ((atom.name == 'covr') and (atom.has_child('data')))]
        else:
            return []

    def add_image(self, image):
        """embeds an Image object in this metadata"""

        if (not self.has_ilst_atom()):
            self.add_ilst_atom()

        ilst_atom = self.ilst_atom()

        #filter out old cover image before adding new one
        ilst_atom.leaf_atoms = filter(
            lambda atom: not ((atom.name == 'covr') and
                              (atom.has_child('data'))),
            ilst_atom) + [M4A_ILST_Leaf_Atom(
                'covr',
                [M4A_ILST_COVR_Data_Atom.converted(image)])]

    def delete_image(self, image):
        """deletes an Image object from this metadata"""

        if (self.has_ilst_atom()):
            ilst_atom = self.ilst_atom()

            ilst_atom.leaf_atoms = filter(
                lambda atom: not ((atom.name == 'covr') and
                                  (atom.has_child('data')) and
                                  (atom['data'].data == image.data)),
                ilst_atom)

    @classmethod
    def converted(cls, metadata):
        """converts metadata from another class to this one, if necessary

        takes a MetaData-compatible object (or None)
        and returns a new MetaData subclass with the data fields converted"""

        if (metadata is None):
            return None
        elif (isinstance(metadata, cls)):
            return cls(metadata.version,
                       metadata.flags,
                       [leaf.copy() for leaf in metadata])

        ilst_atoms = [
            M4A_ILST_Leaf_Atom(
                cls.UNICODE_ATTRIB_TO_ILST[attrib],
                [M4A_ILST_Unicode_Data_Atom(0, 1, value.encode('utf-8'))])
            for (attrib, value) in metadata.filled_fields()
            if (attrib in cls.UNICODE_ATTRIB_TO_ILST)]

        if (((metadata.track_number is not None) or
             (metadata.track_total is not None))):
            ilst_atoms.append(
                M4A_ILST_Leaf_Atom(
                    'trkn',
                    [M4A_ILST_TRKN_Data_Atom(metadata.track_number if
                                             (metadata.track_number
                                              is not None) else 0,
                                             metadata.track_total if
                                             (metadata.track_total
                                              is not None) else 0)]))

        if (((metadata.album_number is not None) or
             (metadata.album_total is not None))):
            ilst_atoms.append(
                M4A_ILST_Leaf_Atom(
                    'disk',
                    [M4A_ILST_DISK_Data_Atom(metadata.album_number if
                                             (metadata.album_number
                                              is not None) else 0,
                                             metadata.album_total if
                                             (metadata.album_total
                                              is not None) else 0)]))

        if (len(metadata.front_covers()) > 0):
            ilst_atoms.append(
                M4A_ILST_Leaf_Atom(
                    'covr',
                    [M4A_ILST_COVR_Data_Atom.converted(
                        metadata.front_covers()[0])]))

        ilst_atoms.append(
            M4A_ILST_Leaf_Atom(
                'cpil',
                [M4A_Leaf_Atom('data',
                               '\x00\x00\x00\x15\x00\x00\x00\x00\x01')]))

        return cls(0, 0, [M4A_HDLR_Atom(0, 0, '\x00\x00\x00\x00',
                                        'mdir', 'appl', 0, 0, '', 0),
                          M4A_Tree_Atom('ilst', ilst_atoms),
                          M4A_FREE_Atom(1024)])

    @classmethod
    def supports_images(self):
        """returns True"""

        return True

    def clean(self):
        """returns a new MetaData object that's been cleaned of problems

        any fixes performed are appended to fixes_performed as Unicode"""

        fixes_performed = []

        def cleaned_atom(atom):
            #numerical fields are stored in bytes,
            #so no leading zeroes are possible

            #image fields don't store metadata,
            #so no field problems are possible there either

            if (atom.name in self.UNICODE_ATTRIB_TO_ILST.values()):
                text = atom['data'].data.decode('utf-8')
                fix1 = text.rstrip()
                if (fix1 != text):
                    from .text import CLEAN_REMOVE_TRAILING_WHITESPACE
                    fixes_performed.append(
                        CLEAN_REMOVE_TRAILING_WHITESPACE %
                        {"field": atom.name.lstrip('\xa9').decode('ascii')})
                fix2 = fix1.lstrip()
                if (fix2 != fix1):
                    from .text import CLEAN_REMOVE_LEADING_WHITESPACE
                    fixes_performed.append(
                        CLEAN_REMOVE_LEADING_WHITESPACE %
                        {"field": atom.name.lstrip('\xa9').decode('ascii')})
                if (len(fix2) > 0):
                    return M4A_ILST_Leaf_Atom(
                        atom.name,
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    fix2.encode('utf-8'))])
                else:
                    from .text import CLEAN_REMOVE_EMPTY_TAG
                    fixes_performed.append(
                        CLEAN_REMOVE_EMPTY_TAG %
                        {"field": atom.name.lstrip('\xa9').decode('ascii')})
                    return None
            else:
                return atom

        if (self.has_ilst_atom()):
            return (M4A_META_Atom(
                self.version,
                self.flags,
                [M4A_Tree_Atom('ilst',
                               filter(lambda atom: atom is not None,
                                      map(cleaned_atom, self.ilst_atom())))]),
                fixes_performed)
        else:
            #if no ilst atom, return a copy of the meta atom as-is
            return (M4A_META_Atom(
                self.version,
                self.flags,
                [M4A_Tree_Atom('ilst',
                               [atom.copy() for atom in self.ilst_atom()])]),
                [])


class M4A_ILST_Leaf_Atom(M4A_Tree_Atom):
    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_ILST_Leaf_Atom(self.name, [leaf.copy() for leaf in self])

    def __repr__(self):
        return "M4A_ILST_Leaf_Atom(%s, %s)" % \
            (repr(self.name), repr(self.leaf_atoms))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        return cls(
            name,
            parse_sub_atoms(data_size, reader,
                            {"data": {"\xa9alb": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9ART": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9cmt": M4A_ILST_Unicode_Data_Atom,
                                      "cprt": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9day": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9grp": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9nam": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9too": M4A_ILST_Unicode_Data_Atom,
                                      "\xa9wrt": M4A_ILST_Unicode_Data_Atom,
                                      'aART': M4A_ILST_Unicode_Data_Atom,
                                      "covr": M4A_ILST_COVR_Data_Atom,
                                      "trkn": M4A_ILST_TRKN_Data_Atom,
                                      "disk": M4A_ILST_DISK_Data_Atom
                                      }.get(name, M4A_Leaf_Atom)}))

    def __unicode__(self):
        try:
            return unicode(filter(lambda f: f.name == 'data',
                                  self.leaf_atoms)[0])
        except IndexError:
            return u""

    def raw_info_lines(self):
        """yields lines of human-readable information about the atom"""

        for leaf_atom in self.leaf_atoms:
            name = self.name.replace("\xa9", " ").decode('ascii')
            if (hasattr(leaf_atom, "raw_info")):
                yield u"%s : %s" % (name, leaf_atom.raw_info())
            else:
                yield u"%s : %s" % (name, repr(leaf_atom))  # FIXME


class M4A_ILST_Unicode_Data_Atom(M4A_Leaf_Atom):
    def __init__(self, type, flags, data):
        self.name = "data"
        self.type = type
        self.flags = flags
        self.data = data

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_ILST_Unicode_Data_Atom(self.type, self.flags, self.data)

    def __repr__(self):
        return "M4A_ILST_Unicode_Data_Atom(%s, %s, %s)" % \
            (repr(self.type), repr(self.flags), repr(self.data))

    def __eq__(self, atom):
        for attr in ["type", "flags", "data"]:
            if ((not hasattr(atom, attr)) or (getattr(self, attr) !=
                                              getattr(atom, attr))):
                return False
        else:
            return True

    def raw_info(self):
        """returns a line of human-readable information about the atom"""

        return self.data.decode('utf-8')

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "data")
        (type, flags) = reader.parse("8u 24u 32p")
        return cls(type, flags, reader.read_bytes(data_size - 8))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32p %db" % (len(self.data)),
                     (self.type, self.flags, self.data))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + len(self.data)

    def __unicode__(self):
        return self.data.decode('utf-8')


class M4A_ILST_TRKN_Data_Atom(M4A_Leaf_Atom):
    def __init__(self, track_number, track_total):
        self.name = "data"
        self.track_number = track_number
        self.track_total = track_total

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_ILST_TRKN_Data_Atom(self.track_number, self.track_total)

    def __repr__(self):
        return "M4A_ILST_TRKN_Data_Atom(%d, %d)" % \
            (self.track_number, self.track_total)

    def __eq__(self, atom):
        for attr in ["track_number", "track_total"]:
            if ((not hasattr(atom, attr)) or (getattr(self, attr) !=
                                              getattr(atom, attr))):
                return False
        else:
            return True

    def __unicode__(self):
        if (self.track_total > 0):
            return u"%d/%d" % (self.track_number, self.track_total)
        else:
            return unicode(self.track_number)

    def raw_info(self):
        """returns a line of human-readable information about the atom"""

        return u"%d/%d" % (self.track_number, self.track_total)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "data")
        #FIXME - handle mis-sized TRKN data atoms
        return cls(*reader.parse("64p 16p 16u 16u 16p"))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("64p 16p 16u 16u 16p",
                     (self.track_number, self.track_total))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 16

    def number(self):
        """returns this atom's track_number field
        or None if the field is 0"""

        if (self.track_number != 0):
            return self.track_number
        else:
            return None

    def total(self):
        """returns this atom's track_total field
        or None if the field is 0"""

        if (self.track_total != 0):
            return self.track_total
        else:
            return None


class M4A_ILST_DISK_Data_Atom(M4A_Leaf_Atom):
    def __init__(self, disk_number, disk_total):
        self.name = "data"
        self.disk_number = disk_number
        self.disk_total = disk_total

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_ILST_DISK_Data_Atom(self.disk_number, self.disk_total)

    def __repr__(self):
        return "M4A_ILST_DISK_Data_Atom(%d, %d)" % \
            (self.disk_number, self.disk_total)

    def __eq__(self, atom):
        for attr in ["disk_number", "disk_total"]:
            if ((not hasattr(atom, attr)) or (getattr(self, attr) !=
                                              getattr(atom, attr))):
                return False
        else:
            return True

    def __unicode__(self):
        if (self.disk_total > 0):
            return u"%d/%d" % (self.disk_number, self.disk_total)
        else:
            return unicode(self.disk_number)

    def raw_info(self):
        """returns a line of human-readable information about the atom"""

        return u"%d/%d" % (self.disk_number, self.disk_total)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "data")
        #FIXME - handle mis-sized DISK data atoms
        return cls(*reader.parse("64p 16p 16u 16u"))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("64p 16p 16u 16u",
                     (self.disk_number, self.disk_total))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 14

    def number(self):
        """returns this atom's disc_number field"""

        if (self.disk_number != 0):
            return self.disk_number
        else:
            return None

    def total(self):
        """returns this atom's disk_total field"""

        if (self.disk_total != 0):
            return self.disk_total
        else:
            return None


class M4A_ILST_COVR_Data_Atom(Image, M4A_Leaf_Atom):
    def __init__(self, version, flags, image_data):
        self.version = version
        self.flags = flags
        self.name = "data"

        img = image_metrics(image_data)
        Image.__init__(self,
                       data=image_data,
                       mime_type=img.mime_type,
                       width=img.width,
                       height=img.height,
                       color_depth=img.bits_per_pixel,
                       color_count=img.color_count,
                       description=u"",
                       type=0)

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_ILST_COVR_Data_Atom(self.version, self.flags, self.data)

    def __repr__(self):
        return "M4A_ILST_COVR_Data_Atom(%s, %s, ...)" % \
            (self.version, self.flags)

    def raw_info(self):
        """returns a line of human-readable information about the atom"""

        if (len(self.data) > 20):
            return (u"(%d bytes) " % (len(self.data)) +
                    u"".join([u"%2.2X" % (ord(b)) for b in self.data[0:20]]) +
                    u"\u2026")
        else:
            return (u"(%d bytes) " % (len(self.data)) +
                    u"".join([u"%2.2X" % (ord(b)) for b in self.data[0:20]]))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "data")
        (version, flags) = reader.parse("8u 24u 32p")
        return cls(version, flags, reader.read_bytes(data_size - 8))

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 32p %db" % (len(self.data)),
                     (self.version, self.flags, self.data))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 8 + len(self.data)

    @classmethod
    def converted(cls, image):
        """given an Image-compatible object,
        returns a new M4A_ILST_COVR_Data_Atom object"""

        return cls(0, 0, image.data)


class M4A_HDLR_Atom(M4A_Leaf_Atom):
    def __init__(self, version, flags, qt_type, qt_subtype,
                 qt_manufacturer, qt_reserved_flags, qt_reserved_flags_mask,
                 component_name, padding_size):
        self.name = 'hdlr'
        self.version = version
        self.flags = flags
        self.qt_type = qt_type
        self.qt_subtype = qt_subtype
        self.qt_manufacturer = qt_manufacturer
        self.qt_reserved_flags = qt_reserved_flags
        self.qt_reserved_flags_mask = qt_reserved_flags_mask
        self.component_name = component_name
        self.padding_size = padding_size

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_HDLR_Atom(self.version,
                             self.flags,
                             self.qt_type,
                             self.qt_subtype,
                             self.qt_manufacturer,
                             self.qt_reserved_flags,
                             self.qt_reserved_flags_mask,
                             self.component_name,
                             self.padding_size)

    def __repr__(self):
        return "M4A_HDLR_Atom(%s, %s, %s, %s, %s, %s, %s, %s, %d)" % \
            (self.version, self.flags, repr(self.qt_type),
             repr(self.qt_subtype), repr(self.qt_manufacturer),
             self.qt_reserved_flags, self.qt_reserved_flags_mask,
             repr(self.component_name), self.padding_size)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == 'hdlr')
        (version,
         flags,
         qt_type,
         qt_subtype,
         qt_manufacturer,
         qt_reserved_flags,
         qt_reserved_flags_mask) = reader.parse(
             "8u 24u 4b 4b 4b 32u 32u")
        component_name = reader.read_bytes(reader.read(8))
        return cls(version, flags, qt_type, qt_subtype,
                   qt_manufacturer, qt_reserved_flags,
                   qt_reserved_flags_mask, component_name,
                   data_size - len(component_name) - 25)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.build("8u 24u 4b 4b 4b 32u 32u 8u %db %dP" %
                     (len(self.component_name),
                      self.padding_size),
                     (self.version,
                      self.flags,
                      self.qt_type,
                      self.qt_subtype,
                      self.qt_manufacturer,
                      self.qt_reserved_flags,
                      self.qt_reserved_flags_mask,
                      len(self.component_name),
                      self.component_name))

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return 25 + len(self.component_name) + self.padding_size


class M4A_FREE_Atom(M4A_Leaf_Atom):
    def __init__(self, bytes):
        self.name = "free"
        self.bytes = bytes

    def copy(self):
        """returns a newly copied instance of this atom
        and new instances of any sub-atoms it contains"""

        return M4A_FREE_Atom(self.bytes)

    def __repr__(self):
        return "M4A_FREE_Atom(%d)" % (self.bytes)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an atom of this class"""

        assert(name == "free")
        reader.skip_bytes(data_size)
        return cls(data_size)

    def build(self, writer):
        """writes the atom to the given BitstreamWriter
        not including its 64-bit size / name header"""

        writer.write_bytes(chr(0) * self.bytes)

    def size(self):
        """returns the atom's size
        not including its 64-bit size / name header"""

        return self.bytes
