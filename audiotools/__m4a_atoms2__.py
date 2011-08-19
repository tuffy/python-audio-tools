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

from audiotools import MetaData,Image,image_metrics

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
            raise TypeError(_(u"leaf atoms must be a list"))
        self.leaf_atoms = leaf_atoms

    def __repr__(self):
        return "M4A_Tree_Atom(%s, %s)" % \
            (repr(self.name), repr(self.leaf_atoms))

    def __iter__(self):
        for leaf in self.leaf_atoms:
            yield leaf

    def __getitem__(self, atom_name):
        return self.get_child(atom_name)

    def get_child(self, atom_name):
        for leaf in self:
            if (leaf.name == atom_name):
                return leaf
        else:
            raise KeyError(atom_name)

    def has_child(self, atom_name):
        for leaf in self:
            if (leaf.name == atom_name):
                return True
        else:
            return False

    def add_child(self, atom_obj):
        self.leaf_atoms.append(atom_obj)

    def remove_child(self, atom_name):
        new_leaf_atoms = []
        data_deleted = False
        for leaf_atom in self:
            if ((leaf_atom.name == atom_obj.name) and (not data_deleted)):
                data_deleted = True
            else:
                new_leaf_atoms.append(leaf_atom)

        self.leaf_atoms = new_leaf_atoms

    def replace_child(self, atom_obj):
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
        return cls(name, parse_sub_atoms(data_size, reader, parsers))

    def build(self, writer):
        from .bitstream import BitstreamAccumulator

        leaf_size = BitstreamAccumulator(0)
        for sub_atom in self:
            leaf_size.reset()
            sub_atom.build(leaf_size)
            writer.build("32u 4b", (leaf_size.bytes() + 8, sub_atom.name))
            sub_atom.build(writer)

    def size(self):
        total_size = 0
        for sub_atom in self:
            total_size += (8 + sub_atom.size())
        return total_size

class M4A_Leaf_Atom:
    def __init__(self, name, data):
        """name should be a 4 byte string

        data should be a binary string of atom data"""

        self.name = name
        self.data = data

    def __repr__(self):
        return "M4A_Leaf_Atom(%s, %s)" % \
            (repr(self.name), repr(self.data))

    def __unicode__(self):
        #FIXME
        return self.data.encode('hex')[0:40].decode('ascii')

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        return cls(name, reader.read_bytes(data_size))

    def build(self, writer):
        writer.write_bytes(self.data)

    def size(self):
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
        assert(name == 'ftyp')
        return cls(reader.read_bytes(4),
                   reader.read(32),
                   [reader.read_bytes(4)
                    for i in xrange((data_size - 8) / 4)])

    def build(self, writer):
        writer.build("4b 32u %s" % ("4b" * len(self.compatible_brands)),
                     [self.major_brand,
                      self.major_brand_version] +
                     self.compatible_brands)

    def size(self):
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
        writer.build("8u 24u", (self.version, self.flags))

        if (self.version == 0):
            atom_format = "32u 32u 32u 32u 32u 16u 10P"
        else:
            atom_format = "64U 64U 32u 64U 32u 16u 10P"

        writer.build(atom_format,
                     (self.created_utc_date, self.modified_utc_date,
                      self.time_scale, self.duration,
                      self.playback_speed, self.user_volume))

        writer.build("32u" * 9, self.geometry_matrices)

        writer.build("64U 32u 64U 32u 32u",
                     (self.qt_preview, self.qt_still_poster,
                      self.qt_selection_time, self.qt_current_time,
                      self.next_track_id))

    def size(self):
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

        geometry_matrices = reader.parse("32u" * 9)
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
        writer.build("32u" * 9, self.geometry_matrices)
        writer.build("32u 32u", (self.video_width, self.video_height))

    def size(self):
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
        language = reader.parse("1u 5u 5u 5u")
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
        writer.build("8u 24u", (self.version, self.flags))
        if (self.version == 0):
            atom_format = "32u 32u 32u 32u"
        else:
            atom_format = "64U 64U 32u 64U"
        writer.build(atom_format,
                     (self.created_utc_date, self.modified_utc_date,
                      self.sample_rate, self.track_length))
        writer.build("1u 5u 5u 5u", self.language)
        writer.write(16, self.quality)

    def size(self):
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
        return cls(*reader.parse("8u 24u 16u 16p"))

    def build(self, writer):
        writer.build("8u 24u 16u 16p",
                     (self.version, self.flags, self.audio_balance))

    def size(self):
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
        (version, flags, reference_count) = reader.parse("8u 24u 32u")
        references = []
        for i in xrange(reference_count):
            (leaf_size, leaf_name) = reader.parse("32u 4b")
            references.append(M4A_Leaf_Atom.parse(
                    leaf_name, leaf_size - 8,
                    reader.substream(leaf_size - 8), {}))
        return cls(version, flags, references)

    def build(self, writer):
        from .bitstream import BitstreamAccumulator

        writer.build("8u 24u 32u", (self.version,
                                    self.flags,
                                    len(self.references)))

        leaf_size = BitstreamAccumulator(0)
        for reference_atom in self.references:
            leaf_size.reset()
            reference_atom.build(leaf_size)
            writer.build("32u 4b", (leaf_size.bytes() + 8, reference_atom.name))
            reference_atom.build(writer)

    def size(self):
        total_size = 8
        for reference_atom in self.references:
            total_size += (8 + reference_atom.size())
        return total_size


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
        from .bitstream import BitstreamAccumulator

        writer.build("8u 24u 32u", (self.version,
                                    self.flags,
                                    len(self.descriptions)))

        leaf_size = BitstreamAccumulator(0)
        for description_atom in self.descriptions:
            leaf_size.reset()
            description_atom.build(leaf_size)
            writer.build("32u 4b", (leaf_size.bytes() + 8,
                                    description_atom.name))
            description_atom.build(writer)

    def size(self):
        total_size = 8
        for description_atom in self.descriptions:
            total_size += (8 + description_atom.size())
        return total_size


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
        (version, flags) = reader.parse("8u 24u")
        return cls(version=version,
                   flags=flags,
                   times=[tuple(reader.parse("32u 32u"))
                          for i in xrange(reader.read(32))])

    def build(self, writer):
        writer.build("8u 24u 32u", (self.version, self.flags, len(self.times)))
        for time in self.times:
            writer.build("32u 32u", time)

    def size(self):
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
        (version, flags) = reader.parse("8u 24u")
        return cls(version=version,
                   flags=flags,
                   blocks=[tuple(reader.parse("32u 32u 32u"))
                           for i in xrange(reader.read(32))])

    def build(self, writer):
        writer.build("8u 24u 32u", (self.version, self.flags, len(self.blocks)))
        for block in self.blocks:
            writer.build("32u 32u 32u", block)

    def size(self):
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
        (version, flags, byte_size) = reader.parse("8u 24u 32u")
        return cls(version=version,
                   flags=flags,
                   byte_size=byte_size,
                   block_sizes=[reader.read(32) for i in
                                xrange(reader.read(32))])

    def build(self, writer):
        writer.build("8u 24u 32u 32u", (self.version,
                                        self.flags,
                                        self.byte_size,
                                        len(self.block_sizes)))
        for size in self.block_sizes:
            writer.write(32, size)

    def size(self):
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
        assert(name == "stco")
        (version, flags, offset_count) = reader.parse("8u 24u 32u")
        return cls(version, flags,
                   [reader.read(32) for i in xrange(offset_count)])

    def build(self, writer):
        writer.build("8u 24u 32u", (self.version, self.flags,
                                    len(self.offsets)))
        for offset in self.offsets:
            writer.write(32, offset)

    def size(self):
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
        return 28 + 8 + self.sub_alac.size()


class M4A_SUB_ALAC_Atom(M4A_Leaf_Atom):
    def __init__(self, max_samples_per_frame, bits_per_sample,
                 history_multiplier, initial_history, maximum_k,
                 channels, unknown, max_coded_frame_size, bitrate, sample_rate):
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
        return cls(*reader.parse(
                "4P 32u 8p 8u 8u 8u 8u 8u 16u 32u 32u 32u"))

    def build(self, writer):
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
        return 28


class M4A_META_Atom(MetaData, M4A_Tree_Atom):
    UNICODE_ATTRIB_TO_ILST = {"track_name":"\xa9nam",
                              "album_name":"\xa9alb",
                              "artist_name":"\xa9ART",
                              "composer_name":"\xa9wrt",
                              "copyright":"cprt",
                              "year":"\xa9day",
                              "comment":"\xa9cmt"}

    INT_ATTRIB_TO_ILST = {"track_number":"trkn",
                          "album_number":"disk"}

    TOTAL_ATTRIB_TO_ILST = {"track_total":"trkn",
                            "album_total":"disk"}

    def __init__(self, version, flags, leaf_atoms):
        M4A_Tree_Atom.__init__(self, "meta", leaf_atoms)
        self.__dict__["version"] = version
        self.__dict__["flags"] = flags
        try:
            self.__dict__["ilst_atom"] = filter(lambda l: l.name == 'ilst',
                                                self.leaf_atoms)[0]
        except IndexError:
            self.__dict__["ilst_atom"] = None

    def __repr__(self):
        return "M4A_META_Atom(%s, %s, %s)" % \
            (repr(self.version), repr(self.flags), repr(self.leaf_atoms))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        """given a 4 byte name, data_size int, BitstreamReader
        and dict of {"atom":handler} sub-parsers,
        returns an M4A_META_Atom
        """

        assert(name == "meta")
        (version, flags) = reader.parse("8u 24u")
        return cls(version, flags,
                   parse_sub_atoms(data_size - 4, reader, parsers))

    def build(self, writer):
        from .bitstream import BitstreamAccumulator

        leaf_size = BitstreamAccumulator(0)
        writer.build("8u 24u", (self.version, self.flags))
        for sub_atom in self:
            leaf_size.reset()
            sub_atom.build(leaf_size)
            writer.build("32u 4b", (leaf_size.bytes() + 8, sub_atom.name))
            sub_atom.build(writer)

    def size(self):
        total_size = 4
        for sub_atom in self:
            total_size += (8 + sub_atom.size())
        return total_size


    def __getattr__(self, key):
        if (key in self.UNICODE_ATTRIB_TO_ILST):
            if (self.ilst_atom is not None):
                try:
                    return unicode([a for a in self.ilst_atom
                                    if (a.name ==
                                        self.UNICODE_ATTRIB_TO_ILST[key])][0])
                except IndexError:
                    return u""
            else:
                return u""
        elif (key in self.INT_ATTRIB_TO_ILST):
            if (self.ilst_atom is not None):
                try:
                    return int([a for a in self.ilst_atom
                                if (a.name ==
                                    self.INT_ATTRIB_TO_ILST[key])][0])
                except IndexError:
                    return 0
            else:
                return 0
        elif (key in self.TOTAL_ATTRIB_TO_ILST):
            if (self.ilst_atom is not None):
                try:
                    return [a for a in self.ilst_atom
                            if (a.name ==
                                self.TOTAL_ATTRIB_TO_ILST[key])][0].total()
                except IndexError:
                    return 0
            else:
                return 0
        elif (key in self.__FIELDS__):
            return u""
        else:
            raise AttributeError(key)

    def __setattr__(self, key, value):
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

        ilst_leaf = self.UNICODE_ATTRIB_TO_ILST.get(
            key,
            self.INT_ATTRIB_TO_ILST.get(
                key,
                self.TOTAL_ATTRIB_TO_ILST.get(
                    key,
                    None)))

        if (ilst_leaf is None):
            self.__dict__[key] = value
            return

        if (self.ilst_atom is not None):
            #an ilst atom is present, so check its sub-atoms
            for ilst_atom in self.ilst_atom:
                if (ilst_atom.name == ilst_leaf):
                    #atom already present, so adjust its data sub-atom
                    replace_data_atom(key, ilst_atom, value)
                    break
            else:
                #atom not present, so append new parent and data sub-atom
                self.ilst_atom.add_child(
                    M4A_ILST_Leaf_Atom(ilst_leaf, [new_data_atom(key, value)]))
        else:
            #no ilst atom, so build one and add the appropriate sub-atoms
            #FIXME
            raise NotImplementedError()


    def __delattr__(self, key):
        if (self.ilst_atom is not None):
            if (key in self.UNICODE_ATTRIB_TO_ILST):
                self.ilst_atom.leaf_atoms = filter(
                    lambda atom: atom.name != self.UNICODE_ATTRIB_TO_ILST[key],
                    self.ilst_atom)
            elif (key == "track_number"):
                if (self.track_total == 0):
                    self.ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "trkn", self.ilst_atom)
                else:
                    self.track_number = 0
            elif (key == "track_total"):
                if (self.track_number == 0):
                    self.ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "trkn", self.ilst_atom)
                else:
                    self.track_total = 0
            elif (key == "album_number"):
                if (self.album_total == 0):
                    self.ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "disk", self.ilst_atom)
                else:
                    self.album_number = 0
            elif (key == "album_total"):
                if (self.album_number == 0):
                    self.ilst_atom.leaf_atoms = filter(
                        lambda atom: atom.name != "disk", self.ilst_atom)
                else:
                    self.album_total = 0
            else:
                try:
                    del(self.__dict__[key])
                except KeyError:
                    raise AttributeError(key)

    def images(self):
        if (self.ilst_atom is not None):
            return [atom['data'] for atom in self.ilst_atom
                    if ((atom.name == 'covr') and (atom.has_child('data')))]
        else:
            return []

    def add_image(self, image):
        if (self.ilst_atom is not None):
            #filter out old cover image before adding new one
            self.ilst_atom.leaf_atoms = filter(
                lambda atom: not ((atom.name == 'covr') and
                                  (atom.has_child('data')) and
                                  (atom['data'].data == image.data)),
                self.ilst_atom) + [M4A_ILST_Leaf_Atom(
                    'covr',
                    [M4A_ILST_COVR_Data_Atom.converted(image)])]
        else:
            #no ilst atom, so build one and add the appropriate sub-atoms
            #FIXME
            raise NotImplementedError()

    def delete_image(self, image):
        if (self.ilst_atom is not None):
            self.ilst_atom.leaf_atoms = filter(
                lambda atom: not ((atom.name == 'covr') and
                                  (atom.has_child('data')) and
                                  (atom['data'].data == image.data)),
                self.ilst_atom)

    @classmethod
    def converted(cls, metadata):
        if ((metadata is None) or isinstance(metadata, cls)):
            return metadata

        ilst_atoms = [M4A_ILST_Leaf_Atom(
                cls.UNICODE_ATTRIB_TO_ILST[attrib],
                [M4A_ILST_Unicode_Data_Atom(
                        0, 1, getattr(metadata,
                                      attrib).encode('utf-8'))])
                      for attrib in cls.__FIELDS__
                      if (attrib in cls.UNICODE_ATTRIB_TO_ILST)]

        if ((metadata.track_number != 0) or
            (metadata.track_total != 0)):
            ilst_atoms.append(M4A_ILST_Leaf_Atom(
                    'trkn',
                    [M4A_ILST_TRKN_Data_Atom(
                            metadata.track_number,
                            metadata.track_total)]))

        if ((metadata.album_number != 0) or
            (metadata.album_total != 0)):
            ilst_atoms.append(M4A_ILST_Leaf_Atom(
                    'disk',
                    [M4A_ILST_DISK_Data_Atom(
                            metadata.album_number,
                            metadata.album_total)]))

        if (len(metadata.front_covers()) > 0):
            ilst_atoms.append(M4A_ILST_Leaf_Atom(
                    'covr',
                    [M4A_ILST_COVR_Data_Atom.converted(
                            metadata.front_covers()[0])]))

        ilst_atoms.append(M4A_ILST_Leaf_Atom(
                'cpil',
                [M4A_Leaf_Atom('data',
                               '\x00\x00\x00\x15\x00\x00\x00\x00\x01')]))

        return cls(0, 0, [M4A_HDLR_Atom(0, 0, '\x00\x00\x00\x00',
                                        'mdir', 'appl', 0, 0, '', 0),
                          M4A_Tree_Atom('ilst', ilst_atoms),
                          M4A_FREE_Atom(1024)])


    # def merge(self, metadata):
    #     raise NotImplementedError() #FIXME

    def __comment_name__(self):
        return u'M4A'

    @classmethod
    def supports_images(self):
        """Returns True."""

        return True

    @classmethod
    def __by_pair__(cls, atom1, atom2):
        KEY_MAP = {"\xa9nam": 1,
                   "\xa9ART": 6,
                   "\xa9com": 5,
                   "\xa9alb": 2,
                   "trkn": 3,
                   "disk": 4,
                   "----": 8}

        return cmp(KEY_MAP.get(atom1.name, 7), KEY_MAP.get(atom2.name, 7))

    def __comment_pairs__(self):
        if (self.ilst_atom is not None):
            return [(atom.name.replace(chr(0xA9), " "), unicode(atom))
                    for atom in sorted(self.ilst_atom, self.__by_pair__)
                    if (atom.name not in ('covr', ))]
        else:
            return []

    def clean(self, fixes_applied):
        def cleaned_atom(atom):
            #numerical fields are stored in bytes,
            #so no leading zeroes are possible

            #image fields don't store metadata,
            #so no field problems are possible there either

            if (atom.name in self.UNICODE_ATTRIB_TO_ILST.values()):
                text = atom['data'].data.decode('utf-8')
                fix1 = text.rstrip()
                if (fix1 != text):
                    fixes_applied.append(
                        _(u"removed trailing whitespace from %(field)s") %
                        {"field":atom.name.lstrip('\xa9').decode('ascii')})
                fix2 = fix1.lstrip()
                if (fix2 != fix1):
                    fixes_applied.append(
                        _(u"removed leading whitespace from %(field)s") %
                        {"field":atom.name.lstrip('\xa9').decode('ascii')})
                if (len(fix2) > 0):
                    return M4A_ILST_Leaf_Atom(
                        atom.name,
                        [M4A_ILST_Unicode_Data_Atom(0, 1,
                                                    fix2.encode('utf-8'))])
                else:
                    fixes_applied.append(
                        _(u"removed empty field %(field)s") %
                        {"field":atom.name.lstrip('\xa9').decode('ascii')})
                    return None
            else:
                return atom

        if (self.ilst_atom is not None):
            cleaned_leaf_atoms = filter(lambda atom: atom is not None,
                                        map(cleaned_atom, self.ilst_atom))
        else:
            print "no ilst atom"

        return M4A_META_Atom(self.version, self.flags,
                             [M4A_Tree_Atom('ilst', cleaned_leaf_atoms)])


class M4A_ILST_Leaf_Atom(M4A_Tree_Atom):
    def __repr__(self):
        return "M4A_ILST_Leaf_Atom(%s, %s)" % \
            (repr(self.name), repr(self.leaf_atoms))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        return cls(name,
                   parse_sub_atoms(
                data_size, reader,
                {"data":{"\xa9alb":M4A_ILST_Unicode_Data_Atom,
                         "\xa9ART":M4A_ILST_Unicode_Data_Atom,
                         "\xa9cmt":M4A_ILST_Unicode_Data_Atom,
                         "cprt":M4A_ILST_Unicode_Data_Atom,
                         "\xa9day":M4A_ILST_Unicode_Data_Atom,
                         "\xa9grp":M4A_ILST_Unicode_Data_Atom,
                         "\xa9nam":M4A_ILST_Unicode_Data_Atom,
                         "\xa9too":M4A_ILST_Unicode_Data_Atom,
                         "\xa9wrt":M4A_ILST_Unicode_Data_Atom,
                         "covr":M4A_ILST_COVR_Data_Atom,
                         "trkn":M4A_ILST_TRKN_Data_Atom,
                         "disk":M4A_ILST_DISK_Data_Atom}.get(
                        name, M4A_Leaf_Atom)}))

    def __unicode__(self):
        try:
            return unicode(filter(lambda f: f.name == 'data',
                                  self.leaf_atoms)[0])
        except IndexError:
            return u""

    def __int__(self):
        try:
            return int(filter(lambda f: f.name == 'data',
                              self.leaf_atoms)[0])
        except IndexError:
            return 0

    def total(self):
        try:
            return filter(lambda f: f.name == 'data',
                          self.leaf_atoms)[0].total()
        except IndexError:
            return 0

class M4A_ILST_Unicode_Data_Atom(M4A_Leaf_Atom):
    def __init__(self, type, flags, data):
        self.name = "data"
        self.type = type
        self.flags = flags
        self.data = data

    def __repr__(self):
        return "M4A_ILST_Unicode_Data_Atom(%s, %s, %s)" % \
            (repr(self.type), repr(self.flags), repr(self.data))

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        assert(name == "data")
        (type, flags) = reader.parse("8u 24u 32p")
        return cls(type, flags, reader.read_bytes(data_size - 8))

    def build(self, writer):
        writer.build("8u 24u 32p %db" % (len(self.data)),
                     (self.type, self.flags, self.data))

    def size(self):
        return 8 + len(self.data)

    def __unicode__(self):
        return self.data.decode('utf-8')

class M4A_ILST_TRKN_Data_Atom(M4A_Leaf_Atom):
    def __init__(self, track_number, track_total):
        self.name = "data"
        self.track_number = track_number
        self.track_total = track_total

    def __repr__(self):
        return "M4A_ILST_TRKN_Data_Atom(%d, %d)" % \
            (self.track_number, self.track_total)

    def __unicode__(self):
        if (self.track_total > 0):
            return u"%d/%d" % (self.track_number, self.track_total)
        else:
            return unicode(self.track_number)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        assert(name == "data")
        return cls(*reader.parse("64p 16p 16u 16u 16p"))

    def build(self, writer):
        writer.build("64p 16p 16u 16u 16p",
                     (self.track_number, self.track_total))

    def size(self):
        return 16

    def __int__(self):
        return self.track_number

    def total(self):
        return self.track_total

class M4A_ILST_DISK_Data_Atom(M4A_Leaf_Atom):
    def __init__(self, disk_number, disk_total):
        self.name = "data"
        self.disk_number = disk_number
        self.disk_total = disk_total

    def __repr__(self):
        return "M4A_ILST_DISK_Data_Atom(%d, %d)" % \
            (self.disk_number, self.disk_total)

    def __unicode__(self):
        if (self.disk_total > 0):
            return u"%d/%d" % (self.disk_number, self.disk_total)
        else:
            return unicode(self.disk_number)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        assert(name == "data")
        return cls(*reader.parse("64p 16p 16u 16u"))

    def build(self, writer):
        writer.build("64p 16p 16u 16u",
                     (self.disk_number, self.disk_total))

    def size(self):
        return 14

    def __int__(self):
        return self.disk_number

    def total(self):
        return self.disk_total

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

    def __repr__(self):
        return "M4A_ILST_COVR_Data_Atom(%s, %s, ...)" % \
            (self.version, self.flags)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        assert(name == "data")
        (version, flags) = reader.parse("8u 24u 32p")
        return cls(version, flags, reader.read_bytes(data_size - 8))

    def build(self, writer):
        writer.build("8u 24u 32p %db" % (len(self.data)),
                     (self.version, self.flags, self.data))

    def size(self):
        return 8 + len(self.data)

    @classmethod
    def converted(cls, image):
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

    def __repr__(self):
        return "M4A_HDLR_Atom(%s, %s, %s, %s, %s, %s, %s, %s, %d)" % \
            (self.version, self.flags, repr(self.qt_type),
             repr(self.qt_subtype), repr(self.qt_manufacturer),
             self.qt_reserved_flags, self.qt_reserved_flags_mask,
             repr(self.component_name), self.padding_size)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
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
        writer.build("8u 24u 4b 4b 4b 32u 32u 8u %db %dP" % \
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
        return 25 + len(self.component_name) + self.padding_size

class M4A_FREE_Atom(M4A_Leaf_Atom):
    def __init__(self, bytes):
        self.name = "free"
        self.bytes = bytes

    def __repr__(self):
        return "M4A_FREE_Atom(%d)" % (self.bytes)

    @classmethod
    def parse(cls, name, data_size, reader, parsers):
        assert(name == "free")
        reader.skip_bytes(data_size)
        return cls(data_size)

    def build(self, writer):
        writer.write_bytes(chr(0) * self.bytes)

    def size(self):
        return self.bytes
