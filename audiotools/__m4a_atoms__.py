#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2010  Brian Langenberger

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

from audiotools import Con
#import construct as Con

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

def VersionLength(name):
    return Con.IfThenElse(name,
                          lambda ctx: ctx["version"] == 0,
                          Con.UBInt32(None),
                          Con.UBInt64(None))

class AtomAdapter(Con.Adapter):
    def _encode(self, obj, context):
        obj.size = len(obj.data) + 8
        return obj

    def _decode(self, obj, context):
        del(obj.size)
        return obj

def Atom(name):
    return AtomAdapter(Con.Struct(
            name,
            Con.UBInt32("size"),
            Con.String("type",4),
            Con.String("data",lambda ctx: ctx["size"] - 8)))

class AtomListAdapter(Con.Adapter):
    ATOM_LIST = Con.GreedyRepeater(Atom("atoms"))

    def _encode(self, obj, context):
        obj.data = self.ATOM_LIST.build(obj.data)
        return obj

    def _decode(self, obj, context):
        obj.data = self.ATOM_LIST.parse(obj.data)
        return obj

def AtomContainer(name):
    return AtomListAdapter(Atom(name))

#wraps around an existing sub_atom and automatically appends/removes header
#during build/parse operations
#this should probably be an adapter, but it does seem to work okay
class AtomWrapper(Con.Struct):
    def __init__(self, atom_name, sub_atom):
        Con.Struct.__init__(self,atom_name)
        self.atom_name = atom_name
        self.sub_atom = sub_atom
        self.header = Con.Struct(atom_name,
                                 Con.UBInt32("size"),
                                 Con.Const(Con.String("type",4),atom_name))

    def _parse(self, stream, context):
        header = self.header.parse_stream(stream)
        return self.sub_atom.parse_stream(stream)

    def _build(self, obj, stream, context):
        data = self.sub_atom.build(obj)
        stream.write(self.header.build(Con.Container(type=self.atom_name,
                                                     size=len(data) + 8)))
        stream.write(data)

    def _sizeof(self, context):
        return self.sub_atom.sizeof(context) + 8



ATOM_FTYP = Con.Struct("ftyp",
                        Con.String("major_brand",4),
                        Con.UBInt32("major_brand_version"),
                        Con.GreedyRepeater(Con.String("compatible_brands",4)))

ATOM_MVHD = Con.Struct("mvhd",
                       Con.Byte("version"),
                       Con.String("flags",3),
                       VersionLength("created_mac_UTC_date"),
                       VersionLength("modified_mac_UTC_date"),
                       Con.UBInt32("time_scale"),
                       VersionLength("duration"),
                       Con.UBInt32("playback_speed"),
                       Con.UBInt16("user_volume"),
                       Con.Padding(10),
                       Con.Struct("windows",
                                  Con.UBInt32("geometry_matrix_a"),
                                  Con.UBInt32("geometry_matrix_b"),
                                  Con.UBInt32("geometry_matrix_u"),
                                  Con.UBInt32("geometry_matrix_c"),
                                  Con.UBInt32("geometry_matrix_d"),
                                  Con.UBInt32("geometry_matrix_v"),
                                  Con.UBInt32("geometry_matrix_x"),
                                  Con.UBInt32("geometry_matrix_y"),
                                  Con.UBInt32("geometry_matrix_w")),
                       Con.UBInt64("quicktime_preview"),
                       Con.UBInt32("quicktime_still_poster"),
                       Con.UBInt64("quicktime_selection_time"),
                       Con.UBInt32("quicktime_current_time"),
                       Con.UBInt32("next_track_id"))

ATOM_IODS = Con.Struct("iods",
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.Byte("type_tag"),
                       Con.Switch("descriptor",
                                  lambda ctx: ctx.type_tag,
                                  {0x10: Con.Struct(
                None,
                Con.StrictRepeater(3,Con.Byte("extended_descriptor_type")),
                Con.Byte("descriptor_type_length"),
                Con.UBInt16("OD_ID"),
                Con.Byte("OD_profile"),
                Con.Byte("scene_profile"),
                Con.Byte("audio_profile"),
                Con.Byte("video_profile"),
                Con.Byte("graphics_profile")),
                                   0x0E: Con.Struct(
                None,
                Con.StrictRepeater(3,Con.Byte("extended_descriptor_type")),
                Con.Byte("descriptor_type_length"),
                Con.String("track_id",4))}))

ATOM_TKHD = Con.Struct("tkhd",
                       Con.Byte("version"),
                       Con.BitStruct("flags",
                                     Con.Padding(20),
                                     Con.Flag("TrackInPoster"),
                                     Con.Flag("TrackInPreview"),
                                     Con.Flag("TrackInMovie"),
                                     Con.Flag("TrackEnabled")),
                       VersionLength("created_mac_UTC_date"),
                       VersionLength("modified_mac_UTC_date"),
                       Con.UBInt32("track_id"),
                       Con.Padding(4),
                       VersionLength("duration"),
                       Con.Padding(8),
                       Con.UBInt16("video_layer"),
                       Con.UBInt16("quicktime_alternate"),
                       Con.UBInt16("volume"),
                       Con.Padding(2),
                       Con.Struct("video",
                                  Con.UBInt32("geometry_matrix_a"),
                                  Con.UBInt32("geometry_matrix_b"),
                                  Con.UBInt32("geometry_matrix_u"),
                                  Con.UBInt32("geometry_matrix_c"),
                                  Con.UBInt32("geometry_matrix_d"),
                                  Con.UBInt32("geometry_matrix_v"),
                                  Con.UBInt32("geometry_matrix_x"),
                                  Con.UBInt32("geometry_matrix_y"),
                                  Con.UBInt32("geometry_matrix_w")),
                       Con.UBInt32("video_width"),
                       Con.UBInt32("video_height"))

ATOM_MDHD = Con.Struct("mdhd",
                       Con.Byte("version"),
                       Con.String("flags",3),
                       VersionLength("created_mac_UTC_date"),
                       VersionLength("modified_mac_UTC_date"),
                       Con.UBInt32("time_scale"),
                       VersionLength("duration"),
                       Con.BitStruct("languages",
                                     Con.Padding(1),
                                     Con.StrictRepeater(3,
                                                        Con.Bits("language",5))),
                       Con.UBInt16("quicktime_quality"))


ATOM_HDLR = Con.Struct("hdlr",
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.String("quicktime_type",4),
                       Con.String("subtype",4),
                       Con.String("quicktime_manufacturer",4),
                       Con.UBInt32("quicktime_component_reserved_flags"),
                       Con.UBInt32("quicktime_component_reserved_flags_mask"),
                       Con.PascalString("component_name"))

ATOM_SMHD = Con.Struct('smhd',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.String("audio_balance",2),
                       Con.Padding(2))

ATOM_DREF = Con.Struct('dref',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(
        length_field=Con.UBInt32("num_references"),
        subcon=Atom("references")))


ATOM_STSD = Con.Struct('stsd',
                       Con.Byte("version"),
                       Con.String("flags",3),
                        Con.PrefixedArray(
        length_field=Con.UBInt32("num_descriptions"),
        subcon=Atom("descriptions")))

ATOM_MP4A = Con.Struct("mp4a",
                       Con.Padding(6),
                       Con.UBInt16("reference_index"),
                       Con.UBInt16("quicktime_audio_encoding_version"),
                       Con.UBInt16("quicktime_audio_encoding_revision"),
                       Con.String("quicktime_audio_encoding_vendor",4),
                       Con.UBInt16("channels"),
                       Con.UBInt16("sample_size"),
                       Con.UBInt16("audio_compression_id"),
                       Con.UBInt16("quicktime_audio_packet_size"),
                       Con.String("sample_rate",4))

#out of all this mess, the only interesting bits are the _bit_rate fields
#and (maybe) the buffer_size
#everything else is a constant of some kind as far as I can tell
ATOM_ESDS = Con.Struct("esds",
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.Byte("ES_descriptor_type"),
                       Con.StrictRepeater(
        3,Con.Byte("extended_descriptor_type_tag")),
                       Con.Byte("descriptor_type_length"),
                       Con.UBInt16("ES_ID"),
                       Con.Byte("stream_priority"),
                       Con.Byte("decoder_config_descriptor_type"),
                       Con.StrictRepeater(
        3,Con.Byte("extended_descriptor_type_tag2")),
                       Con.Byte("descriptor_type_length2"),
                       Con.Byte("object_ID"),
                       Con.Embed(
        Con.BitStruct(None,Con.Bits("stream_type",6),
                      Con.Flag("upstream_flag"),
                      Con.Flag("reserved_flag"),
                      Con.Bits("buffer_size",24))),
                       Con.UBInt32("maximum_bit_rate"),
                       Con.UBInt32("average_bit_rate"),
                       Con.Byte('decoder_specific_descriptor_type3'),
                       Con.StrictRepeater(
        3,Con.Byte("extended_descriptor_type_tag2")),
                       Con.PrefixedArray(
        length_field=Con.Byte("ES_header_length"),
        subcon=Con.Byte("ES_header_start_codes")),
                       Con.Byte("SL_config_descriptor_type"),
                       Con.StrictRepeater(
        3,Con.Byte("extended_descriptor_type_tag3")),
                       Con.Byte("descriptor_type_length3"),
                       Con.Byte("SL_value"))


ATOM_STTS = Con.Struct('stts',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(length_field=Con.UBInt32("total_counts"),
                                     subcon=Con.Struct("frame_size_counts",
                                                       Con.UBInt32("frame_count"),
                                                       Con.UBInt32("duration"))))


ATOM_STSZ = Con.Struct('stsz',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.UBInt32("block_byte_size"),
                       Con.PrefixedArray(length_field=Con.UBInt32("total_sizes"),
                                         subcon=Con.UBInt32("block_byte_sizes")))


ATOM_STSC = Con.Struct('stsc',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(
        length_field=Con.UBInt32("entry_count"),
        subcon=Con.Struct("block",
                          Con.UBInt32("first_chunk"),
                          Con.UBInt32("samples_per_chunk"),
                          Con.UBInt32("sample_description_index"))))

ATOM_STCO = Con.Struct('stco',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(
        length_field=Con.UBInt32("total_offsets"),
        subcon=Con.UBInt32("offset")))

ATOM_CTTS = Con.Struct('ctts',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(
        length_field=Con.UBInt32("entry_count"),
        subcon=Con.Struct("sample",
                          Con.UBInt32("sample_count"),
                          Con.UBInt32("sample_offset"))))

ATOM_META = Con.Struct('meta',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.GreedyRepeater(Atom("atoms")))

ATOM_ILST = Con.GreedyRepeater(AtomContainer('ilst'))

ATOM_TRKN = Con.Struct('trkn',
                       Con.Padding(2),
                       Con.UBInt16('track_number'),
                       Con.UBInt16('total_tracks'),
                       Con.Padding(2))

ATOM_DISK = Con.Struct('disk',
                       Con.Padding(2),
                       Con.UBInt16('disk_number'),
                       Con.UBInt16('total_disks'))
