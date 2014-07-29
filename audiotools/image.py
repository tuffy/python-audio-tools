#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2014  Brian Langenberger

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

import imghdr
from audiotools.bitstream import BitstreamReader, format_size
from audiotools import InvalidImage


def __jpeg__(h, f):
    if (h[0:3] == "FFD8FF".decode('hex')):
        return 'jpeg'
    else:
        return None


imghdr.tests.append(__jpeg__)


def image_metrics(file_data):
    """returns an ImageMetrics subclass from a string of file data

    raises InvalidImage if there is an error parsing the file
    or its type is unknown"""

    header = imghdr.what(None, file_data)

    if (header == 'jpeg'):
        return __JPEG__.parse(file_data)
    elif (header == 'png'):
        return __PNG__.parse(file_data)
    elif (header == 'gif'):
        return __GIF__.parse(file_data)
    elif (header == 'bmp'):
        return __BMP__.parse(file_data)
    elif (header == 'tiff'):
        return __TIFF__.parse(file_data)
    else:
        from audiotools.text import ERR_IMAGE_UNKNOWN_TYPE
        raise InvalidImage(ERR_IMAGE_UNKNOWN_TYPE)


#######################
#JPEG
#######################


class ImageMetrics:
    """a container for image data"""

    def __init__(self, width, height, bits_per_pixel, color_count, mime_type):
        """fields are as follows:

        width          - image width as an integer number of pixels
        height         - image height as an integer number of pixels
        bits_per_pixel - the number of bits per pixel as an integer
        color_count    - for palette-based images, the total number of colors
        mime_type      - the image's MIME type, as a string

        all of the ImageMetrics subclasses implement these fields
        in addition, they all implement a parse() classmethod
        used to parse binary string data and return something
        imageMetrics compatible
        """

        self.width = width
        self.height = height
        self.bits_per_pixel = bits_per_pixel
        self.color_count = color_count
        self.mime_type = mime_type

    def __repr__(self):
        return "ImageMetrics(%s,%s,%s,%s,%s)" % \
               (repr(self.width),
                repr(self.height),
                repr(self.bits_per_pixel),
                repr(self.color_count),
                repr(self.mime_type))

    @classmethod
    def parse(cls, file_data):
        raise NotImplementedError()


class InvalidJPEG(InvalidImage):
    """raised if a JPEG cannot be parsed correctly"""

    pass


class __JPEG__(ImageMetrics):
    def __init__(self, width, height, bits_per_pixel):
        ImageMetrics.__init__(self, width, height, bits_per_pixel,
                              0, u'image/jpeg')

    @classmethod
    def parse(cls, file_data):
        def segments(reader):
            if (reader.read(8) != 0xFF):
                from audiotools.text import ERR_IMAGE_INVALID_JPEG_MARKER
                raise InvalidJPEG(ERR_IMAGE_INVALID_JPEG_MARKER)
            segment_type = reader.read(8)

            while (segment_type != 0xDA):
                if (segment_type not in (0xD8, 0xD9)):
                    yield (segment_type, reader.substream(reader.read(16) - 2))
                else:
                    yield (segment_type, None)

                if (reader.read(8) != 0xFF):
                    from audiotools.text import ERR_IMAGE_INVALID_JPEG_MARKER
                    raise InvalidJPEG(ERR_IMAGE_INVALID_JPEG_MARKER)
                segment_type = reader.read(8)

        try:
            for (segment_type,
                 segment_data) in segments(BitstreamReader(file_data, 0)):
                if (segment_type in (0xC0, 0xC1, 0xC2, 0xC3,
                                     0xC5, 0XC5, 0xC6, 0xC7,
                                     0xC9, 0xCA, 0xCB, 0xCD,
                                     0xCE, 0xCF)):  # start of frame
                    (data_precision,
                     image_height,
                     image_width,
                     components) = segment_data.parse("8u 16u 16u 8u")
                    return __JPEG__(width=image_width,
                                    height=image_height,
                                    bits_per_pixel=data_precision * components)
        except IOError:
            from audiotools.text import ERR_IMAGE_IOERROR_JPEG
            raise InvalidJPEG(ERR_IMAGE_IOERROR_JPEG)

#######################
#PNG
#######################


class InvalidPNG(InvalidImage):
    """raised if a PNG cannot be parsed correctly"""

    pass


class __PNG__(ImageMetrics):
    def __init__(self, width, height, bits_per_pixel, color_count):
        ImageMetrics.__init__(self, width, height, bits_per_pixel, color_count,
                              u'image/png')

    @classmethod
    def parse(cls, file_data):
        def chunks(reader):
            if (reader.read_bytes(8) != '\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
                from audiotools.text import ERR_IMAGE_INVALID_PNG
                raise InvalidPNG(ERR_IMAGE_INVALID_PNG)
            (chunk_length, chunk_type) = reader.parse("32u 4b")
            while (chunk_type != 'IEND'):
                yield (chunk_type,
                       chunk_length,
                       reader.substream(chunk_length))
                chunk_crc = reader.read(32)
                (chunk_length, chunk_type) = reader.parse("32u 4b")

        ihdr = None
        plte_length = 0

        try:
            for (chunk_type,
                 chunk_length,
                 chunk_data) in chunks(BitstreamReader(file_data, 0)):
                if (chunk_type == 'IHDR'):
                    ihdr = chunk_data
                elif (chunk_type == 'PLTE'):
                    plte_length = chunk_length

            if (ihdr is None):
                from audiotools.text import ERR_IMAGE_INVALID_PNG
                raise InvalidPNG(ERR_IMAGE_INVALID_PNG)

            (width,
             height,
             bit_depth,
             color_type,
             compression_method,
             filter_method,
             interlace_method) = ihdr.parse("32u 32u 8u 8u 8u 8u 8u")
        except IOError:
            from audiotools.text import ERR_IMAGE_IOERROR_PNG
            raise InvalidPNG(ERR_IMAGE_IOERROR_PNG)

        if (color_type == 0):    # grayscale
            return cls(width=width,
                       height=height,
                       bits_per_pixel=bit_depth,
                       color_count=0)
        elif (color_type == 2):  # RGB
            return cls(width=width,
                       height=height,
                       bits_per_pixel=bit_depth * 3,
                       color_count=0)
        elif (color_type == 3):  # palette
            if ((plte_length % 3) != 0):
                from audiotools.text import ERR_IMAGE_INVALID_PLTE
                raise InvalidPNG(ERR_IMAGE_INVALID_PLTE)
            else:
                return cls(width=width,
                           height=height,
                           bits_per_pixel=8,
                           color_count=plte_length // 3)
        elif (color_type == 4):  # grayscale + alpha
            return cls(width=width,
                       height=height,
                       bits_per_pixel=bit_depth * 2,
                       color_count=0)
        elif (color_type == 6):  # RGB + alpha
            return cls(width=width,
                       height=height,
                       bits_per_pixel=bit_depth * 4,
                       color_count=0)

#######################
#BMP
#######################


class InvalidBMP(InvalidImage):
    """raised if a BMP cannot be parsed correctly"""

    pass


class __BMP__(ImageMetrics):
    def __init__(self, width, height, bits_per_pixel, color_count):
        ImageMetrics.__init__(self, width, height, bits_per_pixel, color_count,
                              u'image/x-ms-bmp')

    @classmethod
    def parse(cls, file_data):
        try:
            (magic_number,
             file_size,
             data_offset,
             header_size,
             width,
             height,
             color_planes,
             bits_per_pixel,
             compression_method,
             image_size,
             horizontal_resolution,
             vertical_resolution,
             colors_used,
             important_colors_used) = BitstreamReader(file_data, 1).parse(
                "2b 32u 16p 16p 32u " +
                "32u 32u 32u 16u 16u 32u 32u 32u 32u 32u 32u")
        except IOError:
            from audiotools.text import ERR_IMAGE_IOERROR_BMP
            raise InvalidBMP(ERR_IMAGE_IOERROR_BMP)

        if (magic_number != 'BM'):
            from audiotools.text import ERR_IMAGE_INVALID_BMP
            raise InvalidBMP(ERR_IMAGE_INVALID_BMP)
        else:
            return cls(width=width,
                       height=height,
                       bits_per_pixel=bits_per_pixel,
                       color_count=colors_used)


#######################
#GIF
#######################


class InvalidGIF(InvalidImage):
    """raised if a GIF cannot be parsed correctly"""

    pass


class __GIF__(ImageMetrics):
    def __init__(self, width, height, color_count):
        ImageMetrics.__init__(self, width, height, 8, color_count,
                              u'image/gif')

    @classmethod
    def parse(cls, file_data):
        try:
            (gif,
             version,
             width,
             height,
             color_table_size) = BitstreamReader(file_data, 1).parse(
                "3b 3b 16u 16u 3u 5p")
        except IOError:
            from audiotools.text import ERR_IMAGE_IOERROR_GIF
            raise InvalidGIF(ERR_IMAGE_IOERROR_GIF)

        if (gif != 'GIF'):
            from audiotools.text import ERR_IMAGE_INVALID_GIF
            raise InvalidGIF(ERR_IMAGE_INVALID_GIF)
        else:
            return cls(width=width,
                       height=height,
                       color_count=2 ** (color_table_size + 1))


#######################
#TIFF
#######################


class InvalidTIFF(InvalidImage):
    """raised if a TIFF cannot be parsed correctly"""

    pass


class __TIFF__(ImageMetrics):
    def __init__(self, width, height, bits_per_pixel, color_count):
        ImageMetrics.__init__(self, width, height,
                              bits_per_pixel, color_count,
                              u'image/tiff')

    @classmethod
    def parse(cls, file_data):
        import cStringIO

        def tags(file, order):
            while (True):
                reader = BitstreamReader(file, order)
                #read all the tags in an IFD
                tag_count = reader.read(16)
                sub_reader = reader.substream(tag_count * 12)
                next_ifd = reader.read(32)

                for i in xrange(tag_count):
                    (tag_code,
                     tag_datatype,
                     tag_value_count) = sub_reader.parse("16u 16u 32u")
                    if (tag_datatype == 1):    # BYTE type
                        tag_struct = "8u" * tag_value_count
                    elif (tag_datatype == 3):  # SHORT type
                        tag_struct = "16u" * tag_value_count
                    elif (tag_datatype == 4):  # LONG type
                        tag_struct = "32u" * tag_value_count
                    else:                      # all other types
                        tag_struct = "4b"
                    if (format_size(tag_struct) <= 32):
                        yield (tag_code, sub_reader.parse(tag_struct))
                        sub_reader.skip(32 - format_size(tag_struct))
                    else:
                        offset = sub_reader.read(32)
                        file.seek(offset, 0)
                        yield (tag_code,
                               BitstreamReader(file, order).parse(tag_struct))

                if (next_ifd != 0):
                    file.seek(next_ifd, 0)
                else:
                    break

        file = cStringIO.StringIO(file_data)
        try:
            byte_order = file.read(2)
            if (byte_order == 'II'):
                order = 1
            elif (byte_order == 'MM'):
                order = 0
            else:
                from audiotools.text import ERR_IMAGE_INVALID_TIFF
                raise InvalidTIFF(ERR_IMAGE_INVALID_TIFF)
            reader = BitstreamReader(file, order)
            if (reader.read(16) != 42):
                from audiotools.text import ERR_IMAGE_INVALID_TIFF
                raise InvalidTIFF(ERR_IMAGE_INVALID_TIFF)

            initial_ifd = reader.read(32)
            file.seek(initial_ifd, 0)

            width = 0
            height = 0
            bits_per_pixel = 0
            color_count = 0
            for (tag_id, tag_values) in tags(file, order):
                if (tag_id == 0x0100):
                    width = tag_values[0]
                elif (tag_id == 0x0101):
                    height = tag_values[0]
                elif (tag_id == 0x0102):
                    bits_per_pixel = sum(tag_values)
                elif (tag_id == 0x0140):
                    color_count = len(tag_values) // 3
        except IOError:
            from audiotools.text import ERR_IMAGE_IOERROR_TIFF
            raise InvalidTIFF(ERR_IMAGE_IOERROR_TIFF)

        return cls(width=width,
                   height=height,
                   bits_per_pixel=bits_per_pixel,
                   color_count=color_count)
