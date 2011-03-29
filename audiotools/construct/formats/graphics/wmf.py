"""
Windows Meta File
"""
from construct import *


wmf_record = Struct("records",
    ULInt32("size"), # size in words, including the size, function and params
    Enum(ULInt16("function"),
        Arc = 0x0817,
        Chord = 0x0830,
        Ellipse = 0x0418,
        ExcludeClipRect = 0x0415,
        FloodFill = 0x0419,
        IntersectClipRect = 0x0416,
        LineTo = 0x0213,
        MoveTo = 0x0214,
        OffsetClipRgn = 0x0220,
        OffsetViewportOrg = 0x0211,
        OffsetWindowOrg = 0x020F,
        PatBlt = 0x061D,
        Pie = 0x081A,
        RealizePalette = 0x0035,
        Rectangle = 0x041B,
        ResizePalette = 0x0139,
        RestoreDC = 0x0127,
        RoundRect = 0x061C,
        SaveDC = 0x001E,
        ScaleViewportExt = 0x0412,
        ScaleWindowExt = 0x0400,
        SetBkColor = 0x0201,
        SetBkMode = 0x0102,
        SetMapMode = 0x0103,
        SetMapperFlags = 0x0231,
        SetPixel = 0x041F,
        SetPolyFillMode = 0x0106,
        SetROP2 = 0x0104,
        SetStretchBltMode = 0x0107,
        SetTextAlign = 0x012E,
        SetTextCharacterExtra = 0x0108,
        SetTextColor = 0x0209,
        SetTextJustification = 0x020A,
        SetViewportExt = 0x020E,
        SetViewportOrg = 0x020D,
        SetWindowExt = 0x020C,
        SetWindowOrg = 0x020B,
        _default_ = Pass,
    ),
    Array(lambda ctx: ctx.size - 3, ULInt16("params")),
)

wmf_placeable_header = Struct("placeable_header",
  Const(ULInt32("key"), 0x9AC6CDD7),
  ULInt16("handle"),
  SLInt16("left"),
  SLInt16("top"),
  SLInt16("right"),
  SLInt16("bottom"),
  ULInt16("units_per_inch"),
  Padding(4),
  ULInt16("checksum")
)

wmf_file = Struct("wmf_file",
    # --- optional placeable header ---
    Optional(wmf_placeable_header),
    
    # --- header ---
    Enum(ULInt16("type"),
        InMemory = 0,
        File = 1,
    ),
    Const(ULInt16("header_size"), 9),
    ULInt16("version"),
    ULInt32("size"), # file size is in words
    ULInt16("number_of_objects"),
    ULInt32("size_of_largest_record"),
    ULInt16("number_of_params"),
    
    # --- records ---
    GreedyRange(wmf_record)
)

if __name__ == "__main__":
    obj = wmf_file.parse_stream(open("../../test/wmf1.wmf", "rb"))
    print obj
























