#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007  Brian Langenberger

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

#######################
#JPEG
#######################

class ImageMetrics:
    def __init__(self, width, height, bits_per_pixel, color_count, mime_type):
        self.width = width
        self.height = height
        self.bits_per_pixel = bits_per_pixel
        self.color_count = color_count
        self.mime_type = mime_type


class InvalidJPEG(Exception): pass

class JPEG(ImageMetrics):
    SEGMENT_HEADER = Con.Struct('segment_header',
                                Con.Const(Con.Byte('header'),0xFF),
                                Con.Byte('type'),
                                Con.If(
        lambda ctx: ctx['type'] not in (0xD8,0xD9),
        Con.UBInt16('length')))

    APP0 = Con.Struct('JFIF_segment_marker',
                      Con.Const(Con.String('identifier',5),'JFIF\x00'),
                      Con.Const(Con.Byte('major_version'),1),
                      Con.Byte('minor_version'),
                      Con.Byte('density_units'),
                      Con.UBInt16('x_density'),
                      Con.UBInt16('y_density'),
                      Con.Byte('thumbnail_width'),
                      Con.Byte('thumbnail_height'))

    SOF0 = Con.Struct('start_of_frame_0',
                      Con.Byte('data_precision'),
                      Con.UBInt16('image_width'),
                      Con.UBInt16('image_height'),
                      Con.PrefixedArray(
        length_field=Con.Byte('total_components'),
        subcon=Con.Struct('components',
                          Con.Byte('id'),
                          Con.Byte('sampling_factors'),
                          Con.Byte('quantization_table_number'))))

    def __init__(self, width, height, bits_per_pixel):
        ImageMetrics.__init__(self, width, height, bits_per_pixel,
                              0, 'image/jpeg')

    @classmethod
    def parse(cls, file):
        frame0 = None
        
        header = cls.SEGMENT_HEADER.parse_stream(file)
        if (header.type != 0xD8):
            raise InvalidJPEG('invalid JPEG header')
        
        segment = cls.SEGMENT_HEADER.parse_stream(file)
        while (segment.type != 0xD9):
            if (segment.type == 0xDA):
                break

            if (segment.type == 0xE0):
                jfif_segment_marker = cls.APP0.parse_stream(file)
                file.seek(segment.length - cls.APP0.sizeof() - 2,1)
            elif (segment.type == 0xC0):
                frame0 = cls.SOF0.parse_stream(file)
            else:
                file.seek(segment.length - 2,1)
            segment = cls.SEGMENT_HEADER.parse_stream(file)

        if (frame0 is not None):
            return JPEG(width = frame0.image_width,
                        height = frame0.image_height,
                        bits_per_pixel = (frame0.data_precision * \
                                          len(frame0.components)))

