"""
Enhanced Meta File
"""
from construct import *


record_type = Enum(ULInt32("record_type"),
    ABORTPATH = 68,
    ANGLEARC = 41,
    ARC = 45,
    ARCTO = 55,
    BEGINPATH = 59,
    BITBLT = 76,
    CHORD = 46,
    CLOSEFIGURE = 61,
    CREATEBRUSHINDIRECT = 39,
    CREATEDIBPATTERNBRUSHPT = 94,
    CREATEMONOBRUSH = 93,
    CREATEPALETTE = 49,
    CREATEPEN = 38,
    DELETEOBJECT = 40,
    ELLIPSE = 42,
    ENDPATH = 60,
    EOF = 14,
    EXCLUDECLIPRECT = 29,
    EXTCREATEFONTINDIRECTW = 82,
    EXTCREATEPEN = 95,
    EXTFLOODFILL = 53,
    EXTSELECTCLIPRGN = 75,
    EXTTEXTOUTA = 83,
    EXTTEXTOUTW = 84,
    FILLPATH = 62,
    FILLRGN = 71,
    FLATTENPATH = 65,
    FRAMERGN = 72,
    GDICOMMENT = 70,
    HEADER = 1,
    INTERSECTCLIPRECT = 30,
    INVERTRGN = 73,
    LINETO = 54,
    MASKBLT = 78,
    MODIFYWORLDTRANSFORM = 36,
    MOVETOEX = 27,
    OFFSETCLIPRGN = 26,
    PAINTRGN = 74,
    PIE = 47,
    PLGBLT = 79,
    POLYBEZIER = 2,
    POLYBEZIER16 = 85,
    POLYBEZIERTO = 5,
    POLYBEZIERTO16 = 88,
    POLYDRAW = 56,
    POLYDRAW16 = 92,
    POLYGON = 3,
    POLYGON16 = 86,
    POLYLINE = 4,
    POLYLINE16 = 87,
    POLYLINETO = 6,
    POLYLINETO16 = 89,
    POLYPOLYGON = 8,
    POLYPOLYGON16 = 91,
    POLYPOLYLINE = 7,
    POLYPOLYLINE16 = 90,
    POLYTEXTOUTA = 96,
    POLYTEXTOUTW = 97,
    REALIZEPALETTE = 52,
    RECTANGLE = 43,
    RESIZEPALETTE = 51,
    RESTOREDC = 34,
    ROUNDRECT = 44,
    SAVEDC = 33,
    SCALEVIEWPORTEXTEX = 31,
    SCALEWINDOWEXTEX = 32,
    SELECTCLIPPATH = 67,
    SELECTOBJECT = 37,
    SELECTPALETTE = 48,
    SETARCDIRECTION = 57,
    SETBKCOLOR = 25,
    SETBKMODE = 18,
    SETBRUSHORGEX = 13,
    SETCOLORADJUSTMENT = 23,
    SETDIBITSTODEVICE = 80,
    SETMAPMODE = 17,
    SETMAPPERFLAGS = 16,
    SETMETARGN = 28,
    SETMITERLIMIT = 58,
    SETPALETTEENTRIES = 50,
    SETPIXELV = 15,
    SETPOLYFILLMODE = 19,
    SETROP2 = 20,
    SETSTRETCHBLTMODE = 21,
    SETTEXTALIGN = 22,
    SETTEXTCOLOR = 24,
    SETVIEWPORTEXTEX = 11,
    SETVIEWPORTORGEX = 12,
    SETWINDOWEXTEX = 9,
    SETWINDOWORGEX = 10,
    SETWORLDTRANSFORM = 35,
    STRETCHBLT = 77,
    STRETCHDIBITS = 81,
    STROKEANDFILLPATH = 63,
    STROKEPATH = 64,
    WIDENPATH = 66,
    _default_ = Pass,
)

generic_record = Struct("records",
    record_type,
    ULInt32("record_size"),      # Size of the record in bytes 
    Union("params",              # Parameters
        Field("raw", lambda ctx: ctx._.record_size - 8),
        Array(lambda ctx: (ctx._.record_size - 8) // 4, ULInt32("params"))
    ),
)

header_record = Struct("header_record",
    Const(record_type, "HEADER"),
    ULInt32("record_size"),              # Size of the record in bytes 
    SLInt32("bounds_left"),              # Left inclusive bounds 
    SLInt32("bounds_right"),             # Right inclusive bounds 
    SLInt32("bounds_top"),               # Top inclusive bounds 
    SLInt32("bounds_bottom"),            # Bottom inclusive bounds 
    SLInt32("frame_left"),               # Left side of inclusive picture frame 
    SLInt32("frame_right"),              # Right side of inclusive picture frame 
    SLInt32("frame_top"),                # Top side of inclusive picture frame 
    SLInt32("frame_bottom"),             # Bottom side of inclusive picture frame 
    Const(ULInt32("signature"), 0x464D4520),
    ULInt32("version"),                  # Version of the metafile 
    ULInt32("size"),                     # Size of the metafile in bytes 
    ULInt32("num_of_records"),           # Number of records in the metafile 
    ULInt16("num_of_handles"),           # Number of handles in the handle table 
    Padding(2),
    ULInt32("description_size"),         # Size of description string in WORDs 
    ULInt32("description_offset"),       # Offset of description string in metafile 
    ULInt32("num_of_palette_entries"),   # Number of color palette entries 
    SLInt32("device_width_pixels"),      # Width of reference device in pixels 
    SLInt32("device_height_pixels"),     # Height of reference device in pixels 
    SLInt32("device_width_mm"),          # Width of reference device in millimeters
    SLInt32("device_height_mm"),         # Height of reference device in millimeters
    
    # description string
    Pointer(lambda ctx: ctx.description_offset,
        StringAdapter(
            Array(lambda ctx: ctx.description_size,
                Field("description", 2)
            )
        )
    ),
    
    # padding up to end of record
    Padding(lambda ctx: ctx.record_size - 88),
)

emf_file = Struct("emf_file",
    header_record,
    Array(lambda ctx: ctx.header_record.num_of_records - 1, 
        generic_record
    ),
)


if __name__ == "__main__":
    obj = emf_file.parse_stream(open("../../test/emf1.emf", "rb"))
    print obj


































