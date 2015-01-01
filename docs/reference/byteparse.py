#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from __future__ import print_function
import sys
import re

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import registerFont
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("*** ReportLab is required")
    print("Please fetch the open-source version from http://www.reportlab.org")
    sys.exit(1)

HEX_WIDTH = 16
HEX_HEIGHT = 20
ASCII_WIDTH = 8
ASCII_HEIGHT = 20
FONT_SIZE = 10
LABEL_FONT_SIZE = 6
S_OFFSET = 10
LABEL_S_OFFSET = 2

(BORDER_NONE, BORDER_LINE, BORDER_DOTTED) = range(3)


class RGB_Color:
    RGB = re.compile(r'^#([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})$')
    RGBA = re.compile(r'^#([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})' +
                      r'([0-9A-Fa-f]{2})$')

    COLOR_TABLE = {u"red": (1.0, 0.0, 0.0),
                   u"orange": (1.0, 0.4, 0.0),
                   u"yellow": (1.0, 1.0, 0.0),
                   u"green": (0.0, 1.0, 0.0),
                   u"blue": (0.0, 0.0, 1.0),
                   u"aqua": (0.0, 1.0, 1.0),
                   u"black": (0.0, 0.0, 0.0),
                   u"fuchsia": (1.0, 0.0, 1.0),
                   u"gray": (0.5, 0.5, 0.5),
                   u"lime": (0.0, 1.0, 0.0),
                   u"maroon": (0.5, 0.0, 0.0),
                   u"navy": (0.0, 0.0, 0.5),
                   u"olive": (0.5, 0.5, 0.0),
                   u"purple": (0.5, 0.0, 0.5),
                   u"silver": (0.75, 0.75, 0.75),
                   u"teal": (0.0, 0.5, 0.5),
                   u"white": (1.0, 1.0, 1.0)}

    def __init__(self, red, green, blue, alpha=None):
        """all should be floats between 0.0 and 1.0"""

        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    @classmethod
    def from_string(cls, s):
        if s in cls.COLOR_TABLE:
            (r, g, b) = cls.COLOR_TABLE[s]
            return cls(red=r, green=g, blue=b, alpha=1.0)
        else:
            rgb = cls.RGB.match(s)
            if rgb is not None:
                return cls(red=int(rgb.group(1), 16) / 255.0,
                           green=int(rgb.group(2), 16) / 255.0,
                           blue=int(rgb.group(3), 16) / 255.0)
            else:
                rgba = cls.RGBA.match(s)
                if rgba is not None:
                    return cls(red=int(rgba.group(1), 16) / 255.0,
                               green=int(rgba.group(2), 16) / 255.0,
                               blue=int(rgba.group(3), 16) / 255.0,
                               alpha=int(rgba.group(4), 16) / 255.0)
                else:
                    raise ValueError("invalid color string %s" % (repr(s)))


class HexChunk:
    def __init__(self, digits, label=None, background_color=None,
                 w_border=BORDER_NONE, e_border=BORDER_NONE):
        """digits is a list of 2 byte unicode strings for each hex pair
        background_color is an RGB_Color object
        w_border and e_border are one of the BORDER_* enum values"""

        import string

        hexdigits = string.hexdigits.decode('ascii')
        for pair in digits:
            assert(len(pair) == 2)
            if pair != u"  ":
                assert(pair[0] in hexdigits)
                assert(pair[1] in hexdigits)

        self.digits = digits
        self.label = label
        self.background_color = background_color
        self.w_border = w_border
        self.e_border = e_border

        # the chunk's location in the PDF, in x,y point pairs
        self.ne = self.nw = self.se = self.sw = (0, 0)

    def __repr__(self):
        return "HexChunk(%s)" % \
            ",".join(["%s=%s" % (attr, repr(getattr(self, attr)))
                      for attr in ["digits",
                                   "label",
                                   "background_color",
                                   "w_border",
                                   "e_border"]])

    def size(self):
        """returns the number of hex digits in the chunk"""

        return len(self.digits)

    def set_w_offset(self, w):
        """given an west position in points,
        calculates the x positions of all 4 corners"""

        self.nw = (w, self.nw[1])
        self.sw = (w, self.sw[1])
        self.ne = (w + (self.size() * HEX_WIDTH), self.ne[1])
        self.se = (w + (self.size() * HEX_WIDTH), self.se[1])

    def set_s_offset(self, s):
        """given an south position in points,
        calculates the y positions of all 4 corners"""

        self.nw = (self.nw[0], s + HEX_HEIGHT)
        self.sw = (self.sw[0], s)
        self.ne = (self.ne[0], s + HEX_HEIGHT)
        self.se = (self.se[0], s)

    def split(self, digits):
        """returns 2 objects, the first containing up to "digits"
        and the second containing the remainder"""

        return (HexChunk(digits=self.digits[0:digits],
                         label=self.label,
                         background_color=self.background_color,
                         w_border=self.w_border,
                         e_border=BORDER_NONE),
                HexChunk(digits=self.digits[digits:],
                         label=self.label,
                         background_color=self.background_color,
                         w_border=BORDER_NONE,
                         e_border=self.e_border))

    def pt_width(self):
        return abs(self.nw[0] - self.ne[0])

    def pt_height(self):
        return abs(self.nw[1] - self.sw[1])

    def pts_per_cell(self):
        return self.pt_width() / float(len(self.digits))

    def cells(self):
        return iter(self.digits)

    def to_pdf(self, pdf):
        pts_per_string = self.pts_per_cell()
        pt_offset = self.nw[0] + (pts_per_string / 2)

        # draw background color, if any
        if self.background_color is not None:
            pdf.setFillColorRGB(r=self.background_color.red,
                                g=self.background_color.green,
                                b=self.background_color.blue,
                                alpha=self.background_color.alpha)
            pdf.rect(self.sw[0], self.sw[1], self.pt_width(), self.pt_height(),
                     stroke=0, fill=1)

        pdf.setFillColorRGB(0.0, 0.0, 0.0, 1.0)
        pdf.setFont("Courier", FONT_SIZE)
        for (i, s) in enumerate(self.cells()):
            # draw individual cells
            pdf.drawCentredString((i * pts_per_string) + pt_offset,
                                  self.se[1] + S_OFFSET,
                                  unicode(s))

        # draw label, if any
        if ((self.label is not None) and
            (pdf.stringWidth(unicode(self.label),
                             "DejaVu",
                             LABEL_FONT_SIZE) <= (self.pt_width() * 2))):
            pdf.setFont("DejaVu", LABEL_FONT_SIZE)
            pdf.drawCentredString(self.nw[0] + (self.pt_width() // 2),
                                  self.se[1] + LABEL_S_OFFSET,
                                  unicode(self.label))

        # draw top and bottom borders
        pdf.setStrokeColorRGB(0.0, 0.0, 0.0, 1.0)
        pdf.setDash()
        pdf.line(self.nw[0], self.nw[1],
                 self.ne[0], self.ne[1])
        pdf.line(self.sw[0], self.sw[1],
                 self.se[0], self.se[1])

        # draw left and right borders, if any
        if self.w_border == BORDER_LINE:
            pdf.setDash()
            pdf.line(self.nw[0], self.nw[1],
                     self.sw[0], self.sw[1])
        elif self.w_border == BORDER_DOTTED:
            pdf.setDash(1, 6)
            pdf.line(self.nw[0], self.nw[1],
                     self.sw[0], self.sw[1])

        if self.e_border == BORDER_LINE:
            pdf.setDash()
            pdf.line(self.ne[0], self.ne[1],
                     self.se[0], self.se[1])
        elif self.e_border == BORDER_DOTTED:
            pdf.setDash(1, 6)
            pdf.line(self.ne[0], self.ne[1],
                     self.se[0], self.se[1])


class HexChunkTable:
    def __init__(self, width, rows=None):
        """width is the number of hex digits per row"""

        self.width = width
        if rows is None:
            self.rows = []  # a list of HexChunk object lists per row
        else:
            self.rows = rows

    def size(self):
        """returns the size of the largest row, in digits/chars"""

        return max([sum([col.size() for col in row])
                    for row in self.rows if (len(row) > 0)])

    def __repr__(self):
        return "HexChunkTable(%s, %s)" % (repr(self.width),
                                          repr(self.rows))

    def add_value(self, digits, label=None, background_color=None):
        """digits is a list of hex unicode strings
        label is an optional unicode string
        background_color is an optional RGB_Color object"""

        self.add_chunk(HexChunk(digits=digits,
                                label=label,
                                background_color=background_color,
                                w_border=BORDER_LINE,
                                e_border=BORDER_LINE))

    def add_chunk(self, chunk):
        """chunk is a Chunk object to be added"""

        if len(self.rows) == 0:
            # no current rows, so start a new one
            self.rows.append([])
            self.add_chunk(chunk)
        else:
            remaining_space = (self.width -
                               sum([c.size() for c in self.rows[-1]]))
            if remaining_space == 0:
                # last row is filled, so start a new one
                self.rows.append([])
                self.add_chunk(chunk)
            elif chunk.size() > remaining_space:
                # chunk is too big to fit into row,
                # so split chunk and add as much as possible
                (head, tail) = chunk.split(remaining_space)
                self.rows[-1].append(head)
                self.rows.append([])
                self.add_chunk(tail)
            else:
                # room remains in row, so add as-is
                self.rows[-1].append(chunk)

    def pt_width(self):
        return max([row[-1].ne[0] - row[0].nw[0] for row in self.rows])

    def pt_height(self):
        return sum([row[0].pt_height() for row in self.rows if len(row) > 0])

    def set_w_offset(self, w):
        for row in self.rows:
            if len(row) > 0:
                offset = 0
                for col in row:
                    col.set_w_offset(offset + w)
                    offset += col.pt_width()

    def set_s_offset(self, s):
        offset = 0
        for row in reversed(self.rows):
            if len(row) > 0:
                for col in row:
                    col.set_s_offset(offset + s)
                offset += row[0].pt_height()

    def to_pdf(self, pdf):
        for row in self.rows:
            for col in row:
                col.to_pdf(pdf)


class ASCIIChunk(HexChunk):
    def __init__(self, chars, background_color=None,
                 w_border=BORDER_NONE, e_border=BORDER_NONE):

        # asciidigits = frozenset([unichr(i) for i in range(0x20, 0x7F)])
        # for char in chars:
        #     assert(len(char) == 1)
        #     assert(char[0] in asciidigits)

        self.chars = chars
        self.label = None
        self.background_color = background_color
        self.w_border = w_border
        self.e_border = e_border

        # the chunk's location in the PDF, in x,y point pairs
        self.ne = self.nw = self.se = self.sw = (0, 0)

    def __repr__(self):
        return "ASCIIChunk(%s)" % \
            ",".join(["%s=%s" % (attr, repr(getattr(self, attr)))
                      for attr in ["chars",
                                   "background_color",
                                   "w_border",
                                   "e_border"]])

    def size(self):
        """returns the number of ASCII characters in the chunk"""

        return len(self.chars)

    def set_w_offset(self, w):
        """given an west position in points,
        calculates the x positions of all 4 corners"""

        self.nw = (w, self.nw[1])
        self.sw = (w, self.sw[1])
        self.ne = (w + (self.size() * ASCII_WIDTH), self.ne[1])
        self.se = (w + (self.size() * ASCII_WIDTH), self.se[1])

    def set_s_offset(self, s):
        """given an south position in points,
        calculates the y positions of all 4 corners"""

        self.nw = (self.nw[0], s + ASCII_HEIGHT)
        self.sw = (self.sw[0], s)
        self.ne = (self.ne[0], s + ASCII_HEIGHT)
        self.se = (self.se[0], s)

    def pts_per_cell(self):
        return self.pt_width() / float(len(self.chars))

    def cells(self):
        return iter(self.chars)

    def split(self, digits):
        """returns 2 objects, the first containing up to "digits"
        and the second containing the remainder"""

        return (ASCIIChunk(chars=self.chars[0:digits],
                           background_color=self.background_color,
                           w_border=self.w_border,
                           e_border=BORDER_NONE),
                ASCIIChunk(chars=self.chars[digits:],
                           background_color=self.background_color,
                           w_border=BORDER_NONE,
                           e_border=self.e_border))


class ASCIIChunkTable(HexChunkTable):
    def __repr__(self):
        return "ASCIIChunkTable(%s, %s)" % (repr(self.width),
                                            repr(self.rows))

    def add_value(self, chars, background_color=None):
        self.add_chunk(ASCIIChunk(chars=chars,
                                  background_color=background_color,
                                  w_border=BORDER_LINE,
                                  e_border=BORDER_LINE))


def populate_tables(xml_filename, hex_table, ascii_table):
    import xml.dom.minidom

    dom = xml.dom.minidom.parse(xml_filename)
    struct = dom.getElementsByTagName(u"bytestruct")[0]

    for part in struct.childNodes:
        if part.nodeName == u"field":
            if part.hasAttribute(u"background-color"):
                background_color = RGB_Color.from_string(
                    part.getAttribute(u"background-color"))
            else:
                background_color = None

            if part.hasAttribute(u"label"):
                label = part.getAttribute(u"label")
            else:
                label = None

            hexvalue = part.childNodes[0].data.strip()
            if len(hexvalue) % 2:
                raise ValueError("hex value must be divisible by 2")
            else:
                hex_digits = []
                ascii_digits = []
                while (len(hexvalue) > 0):
                    value = int(hexvalue[0:2], 16)
                    hexvalue = hexvalue[2:]
                    hex_digits.append(u"%2.2X" % (value))
                    if value in range(0x20, 0x7F):
                        ascii_digits.append(unichr(value))
                    else:
                        ascii_digits.append(u"\u00B7")

                hex_table.add_value(digits=hex_digits,
                                    label=label,
                                    background_color=background_color)
                ascii_table.add_value(chars=ascii_digits,
                                      background_color=background_color)


if (__name__ == "__main__"):
    import argparse

    parser = argparse.ArgumentParser("byte parsing generator")
    parser.add_argument('-i', '--input',
                        dest='input',
                        help='input XML file')
    parser.add_argument('-o', '--output',
                        dest='output',
                        help='output file')
    parser.add_argument('-d', '--digits-per-row',
                        dest='digits_per_row',
                        type=int,
                        default=16)
    parser.add_argument('-w', '--width',
                        dest='width',
                        type=int,
                        default=6 * 72,
                        help='digram width, in PostScript points')
    parser.add_argument('-s', '--space',
                        dest='space',
                        type=int,
                        default=30,
                        help='space between hex and ASCII sections, ' +
                        'in PostScript points')
    parser.add_argument('--no-ascii',
                        dest='ascii',
                        action='store_false',
                        default=True)
    parser.add_argument('-t', '--type',
                        dest='type',
                        choices=("pdf",),
                        help="type of output file",
                        default="pdf")

    options = parser.parse_args()

    hex_table = HexChunkTable(options.digits_per_row)
    ascii_table = ASCIIChunkTable(options.digits_per_row)

    populate_tables(options.input, hex_table, ascii_table)

    if options.ascii:
        diagram_width = ((hex_table.size() * HEX_WIDTH) +
                         options.space +
                         (ascii_table.size() * ASCII_WIDTH))
    else:
        diagram_width = (hex_table.size() * HEX_WIDTH)

    x_offset = (options.width - diagram_width) // 2

    hex_table.set_w_offset(x_offset)
    hex_table.set_s_offset(0)

    if options.ascii:
        ascii_table.set_w_offset(x_offset +
                                 hex_table.pt_width() +
                                 options.space)
        ascii_table.set_s_offset(0)

    if options.type == 'pdf':
        registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
        pdf = canvas.Canvas(options.output)
        pdf.setPageSize((options.width,
                         hex_table.pt_height()))
        hex_table.to_pdf(pdf)
        if options.ascii:
            ascii_table.to_pdf(pdf)
        pdf.showPage()
        pdf.save()
    else:
        print("unknown output type", file=sys.stderr)
        sys.exit(1)
