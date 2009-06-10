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

