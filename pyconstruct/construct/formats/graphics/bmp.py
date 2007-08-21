"""
Windows/OS2 Bitmap (BMP)
this could have been a perfect show-case file format, but they had to make
it ugly (all sorts of alignment or 
"""
from construct import *


#===============================================================================
# pixels: uncompressed
#===============================================================================
def UncompressedRows(subcon, align_to_byte = False):
    """argh! lines must be aligned to a 4-byte boundary, and bit-pixel
    lines must be aligned to full bytes..."""
    if align_to_byte:
        line_pixels = Bitwise(
            Aligned(Array(lambda ctx: ctx.width, subcon), modulus = 8)
        )
    else:
        line_pixels = Array(lambda ctx: ctx.width, subcon)
    return Array(lambda ctx: ctx.height, 
        Aligned(line_pixels, modulus = 4)
    )

uncompressed_pixels = Switch("uncompressed", lambda ctx: ctx.bpp,
    {
        1 : UncompressedRows(Bit("index"), align_to_byte = True),
        4 : UncompressedRows(Nibble("index"), align_to_byte = True),
        8 : UncompressedRows(Byte("index")),
        24 : UncompressedRows(
            Sequence("rgb", Byte("red"), Byte("green"), Byte("blue"))
        ),
    }
)

#===============================================================================
# pixels: Run Length Encoding (RLE) 8 bit
#===============================================================================
class RunLengthAdapter(Adapter):
    def _encode(self, obj):
        return len(obj), obj[0]
    def _decode(self, (length, value)):
        return [value] * length

rle8pixel = RunLengthAdapter(
    Sequence("rle8pixel", 
        Byte("length"), 
        Byte("value")
    )
)

#===============================================================================
# file structure
#===============================================================================
def iff(cond, thenval, elseval):
    if cond:
        return thenval
    else:
        return elseval

bitmap_file = Struct("bitmap_file",
    # header
    Const(String("signature", 2), "BM"),
    ULInt32("file_size"),
    Padding(4),
    ULInt32("data_offset"),
    ULInt32("header_size"),
    Enum(Alias("version", "header_size"),
        v2 = 12,
        v3 = 40,
        v4 = 108,
    ),
    ULInt32("width"),
    ULInt32("height"),
    Value("number_of_pixels", lambda ctx: ctx.width * ctx.height),
    ULInt16("planes"),
    ULInt16("bpp"), # bits per pixel
    Enum(ULInt32("compression"),
        Uncompressed = 0,
        RLE8 = 1,
        RLE4 = 2,
        Bitfields = 3,
        JPEG = 4,
        PNG = 5,
    ),
    ULInt32("image_data_size"), # in bytes
    ULInt32("horizontal_dpi"),
    ULInt32("vertical_dpi"),
    ULInt32("colors_used"),
    ULInt32("important_colors"),
    
    # palette (24 bit has no palette)
    OnDemand(
        Array(lambda ctx: iff(ctx.bpp <= 8, 2 ** ctx.bpp, 0), 
            Struct("palette",
                Byte("blue"),
                Byte("green"),
                Byte("red"),
                Padding(1),
            )
        )
    ),
    
    # pixels
    OnDemandPointer(lambda ctx: ctx.data_offset, 
        Switch("pixels", lambda ctx: ctx.compression,
            {
                "Uncompressed" : uncompressed_pixels,
            }
        ),
    ),
)


if __name__ == "__main__":
    obj = bitmap_file.parse_stream(open("../../test/bitmap8.bmp", "rb"))
    print obj 
    print repr(obj.pixels.value)























