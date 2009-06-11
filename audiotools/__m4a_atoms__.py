#!/usr/bin/python

#from audiotools import Con
import construct as Con

def VersionLength(name):
    return Con.IfThenElse(name,
                          lambda ctx: ctx["version"] == 0,
                          Con.UBInt32(None),
                          Con.UBInt64(None))

ATOM_FTYPE = Con.Struct("ftyp",
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
                       Con.String("playback_speed",4),
                       Con.String("user_volume",2),
                       Con.Padding(10),
                       Con.String("windows",36),
                       Con.UBInt64("quicktime_preview"),
                       Con.UBInt32("quicktime_still_poster"),
                       Con.UBInt64("quicktime_selection_time"),
                       Con.UBInt32("quicktime_current_time"),
                       Con.String("next_track_id",4))

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
                       Con.String("volume",2),
                       Con.Padding(2),
                       Con.String("video_geometry",36),
                       Con.String("video_width",4),
                       Con.String("video_height",4))

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
                       Con.UBInt32("references"),
                       Con.Struct("qt_atom",
                                  Con.UBInt32("size"),
                                  Con.String("type",4),
                                  Con.String("data",lambda ctx: ctx["size"] - 8)))


ATOM_STSD = Con.Struct('stsd',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.UBInt32("number_of_descriptions"),
                       Con.StringAdapter(
        Con.GreedyRepeater(Con.Field("sub_atoms",1))))

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
                       Con.UBInt32("number_of_times"),
                       Con.GreedyRepeater(
        Con.Struct("time_per_frame",
                   Con.UBInt32("frame_count"),
                   Con.UBInt32("duration"))))


ATOM_STSZ = Con.Struct('stsz',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.UBInt32("block_byte_size"),
                       Con.UBInt32("number_of_block_sizes"),
                       Con.GreedyRepeater(Con.UBInt32("block_byte_sizes")))

#not sure about this one
ATOM_STSC = Con.Struct('stsc',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(
        length_field=Con.UBInt32("total_blocks"),
        subcon=Con.Struct("block",
                          Con.UBInt32("next_block"),
                          Con.UBInt32("total_frames"),
                          Con.UBInt32("description_id"))))

ATOM_STCO = Con.Struct('stco',
                       Con.Byte("version"),
                       Con.String("flags",3),
                       Con.PrefixedArray(
        length_field=Con.UBInt32("total_offsets"),
        subcon=Con.UBInt32("offset")))

