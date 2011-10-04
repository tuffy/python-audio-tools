#!/usr/bin/python

import sys
import re

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import registerFont
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print "*** ReportLab is required"
    print "Please fetch the open-source version from http://www.reportlab.org"
    sys.exit(1)

#this size of an individual bit cell, in points
BIT_WIDTH = 20
BIT_HEIGHT = 30


class Chunk:
    def __init__(self, bits, superscripts,
                 name=None,
                 background_color=None,
                 w_border=False, e_border=False):
        assert(len(bits) == len(superscripts))
        self.bits = bits
        self.superscripts = superscripts
        self.name = name
        self.background_color = background_color
        self.w_border = w_border
        self.e_border = e_border

        #the chunk's location in the PDF, in x,y point pairs
        self.ne = self.nw = self.se = self.sw = (0, 0)

    def set_w_offset(self, x):
        self.nw = (x, self.nw[1])
        self.sw = (x, self.sw[1])
        self.ne = (x + (self.size() * BIT_WIDTH), self.ne[1])
        self.se = (x + (self.size() * BIT_WIDTH), self.se[1])

    def set_s_offset(self, y):
        self.nw = (self.nw[0], y + BIT_HEIGHT)
        self.sw = (self.sw[0], y)
        self.ne = (self.ne[0], y + BIT_HEIGHT)
        self.se = (self.se[0], y)

    def size(self):
        return len(self.bits)

    def split(self, bits):
        return (Chunk(bits=self.bits[0:bits],
                      superscripts=self.superscripts[0:bits],
                      name=self.name,
                      background_color=self.background_color,
                      w_border=self.w_border,
                      e_border=False),
                Chunk(bits=self.bits[bits:],
                      superscripts=self.superscripts[bits:],
                      name=self.name,
                      background_color=self.background_color,
                      w_border=False,
                      e_border=self.e_border))

    def __repr__(self):
        return "Chunk(%s)" % \
            ",".join([repr(getattr(self, attr))
                      for attr in ["bits", "superscripts", "name",
                                   "background_color",
                                   "w_border", "e_border",
                                   "nw", "ne", "sw", "se"]])

    def pt_width(self):
        return abs(self.nw[0] - self.ne[0])

    def pt_height(self):
        return abs(self.nw[1] - self.sw[1])

    def to_pdf(self, pdf):
        pts_per_bit = self.pt_width() / float(len(self.bits))
        pt_offset = self.nw[0] + (pts_per_bit / 2)

        #draw background color, if any
        if (self.background_color is not None):
            pdf.setFillColorRGB(*self.background_color)
            pdf.rect(self.sw[0], self.sw[1], self.pt_width(), self.pt_height(),
                     stroke=0, fill=1)

        pdf.setFillColorRGB(0.0, 0.0, 0.0)
        for (i, (bit, superscript)) in enumerate(zip(self.bits,
                                                     self.superscripts)):
            #draw bit
            pdf.setFont("Courier", 18)
            pdf.drawCentredString((i * pts_per_bit) + pt_offset,
                                  self.se[1] + 12, unicode(bit))

            #draw superscript, if any
            if (superscript is not None):
                pdf.setFont("Courier", 5)
                pdf.drawRightString(self.nw[0] + ((i + 1) * pts_per_bit) - 2,
                                    self.se[1] + 25,
                                    unicode(superscript))

        #draw centered name, if any
        if (self.name is not None):
            pdf.setFont("DejaVu", 6)
            pdf.drawCentredString(self.nw[0] + (self.pt_width() / 2),
                                   self.se[1] + 2,
                                  unicode(self.name))

        pdf.setStrokeColorRGB(0.0,0.0,0.0)
        #drop top and bottom borders
        pdf.line(self.nw[0], self.nw[1],
                 self.ne[0], self.ne[1])
        pdf.line(self.sw[0], self.sw[1],
                 self.se[0], self.se[1])

        #draw left and right borders, if any
        if (self.w_border):
            pdf.line(self.nw[0], self.nw[1],
                     self.sw[0], self.sw[1])
        if (self.e_border):
            pdf.line(self.ne[0], self.ne[1],
                     self.se[0], self.se[1])


class TextChunk(Chunk):
    def __init__(self, bit_width,
                 name=None,
                 background_color=None,
                 w_border=False, e_border=False):
        self.bit_width = bit_width
        self.name = name
        self.background_color = background_color
        self.w_border = w_border
        self.e_border = e_border

        #the chunk's location in the PDF, in x,y point pairs
        self.ne = self.nw = self.se = self.sw = (0, 0)

    def size(self):
        return self.bit_width

    def split(self, bits):
        return (TextChunk(bit_width=bits,
                          name=self.name,
                          background_color=self.background_color,
                          w_border=self.w_border,
                          e_border=False),
                TextChunk(bit_width=self.bit_width - bits,
                          name=self.name,
                          background_color=self.background_color,
                          w_border=self.w_border,
                          e_border=False))

    def __repr__(self):
        return "TextChunk(%s)" % \
            ",".join([repr(getattr(self, attr))
                      for attr in ["bit_width", "name",
                                   "background_color",
                                   "w_border", "e_border",
                                   "nw", "ne", "sw", "se"]])

    def to_pdf(self, pdf):
        pts_per_bit = self.pt_width() / float(self.bit_width)
        pt_offset = self.nw[0] + (pts_per_bit / 2)

        #draw background color, if any
        if (self.background_color is not None):
            pdf.setFillColorRGB(*self.background_color)
            pdf.rect(self.sw[0], self.sw[1], self.pt_width(), self.pt_height(),
                     stroke=0, fill=1)

        #draw centered name, if any
        pdf.setFont("DejaVu", 18)
        pdf.drawCentredString(self.nw[0] + (self.pt_width() / 2),
                              self.se[1] + 12,
                              unicode(self.name))

        pdf.setStrokeColorRGB(0.0,0.0,0.0)
        #drop top and bottom borders
        pdf.line(self.nw[0], self.nw[1],
                 self.ne[0], self.ne[1])
        pdf.line(self.sw[0], self.sw[1],
                 self.se[0], self.se[1])

        #draw left and right borders, if any
        if (self.w_border):
            pdf.line(self.nw[0], self.nw[1],
                     self.sw[0], self.sw[1])
        if (self.e_border):
            pdf.line(self.ne[0], self.ne[1],
                     self.se[0], self.se[1])


class ChunkTable:
    def __init__(self, chunks):
        self.chunks = chunks

    def to_pdf(self, total_width, filename):
        total_height = max([chunk.nw[1] for chunk in self.chunks])

        registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))

        pdf = canvas.Canvas(filename)
        pdf.setPageSize((total_width,total_height))

        for chunk in self.chunks:
            chunk.to_pdf(pdf)

        pdf.showPage()
        pdf.save()


class Bits:
    def __init__(self, name, bits):
        """name is a unicode string
        bits is a list of individual bit values
        this generates chunks to be displayed"""

        self.name = name
        self.bits = bits

    def __repr__(self):
        return "Bits(%s, %s)" % (repr(self.name), repr(self.bits))

    def chunk(self, superscript_bits, bits_lookup, background_color):
        chunk_superscripts = []
        for bit in self.bits:
            superscript_bits.append(bit)
            if (tuple(superscript_bits) in bits_lookup):
                chunk_superscripts.append(bits_lookup[tuple(superscript_bits)])
                for i in xrange(len(superscript_bits)):
                    superscript_bits.pop(-1)
            else:
                chunk_superscripts.append(None)

        return Chunk(bits=self.bits,
                     superscripts=chunk_superscripts,
                     name=self.name,
                     background_color=background_color)


class Text:
    def __init__(self, name, bit_count):
        self.name = name
        self.bit_count = bit_count

    def __repr__(self):
        return "Text(%s, %s)" % (repr(self.name), repr(self.bit_count))

    def chunk(self, superscript_bits, bits_lookup, background_color):
        for i in xrange(len(superscript_bits)):
            superscript_bits.pop(-1)

        return TextChunk(bit_width=self.bit_count,
                         name=self.name,
                         background_color=background_color)


BE_LOOKUP = {(0, 0, 0, 0):u"0",
             (0, 0, 0, 1):u"1",
             (0, 0, 1, 0):u"2",
             (0, 0, 1, 1):u"3",
             (0, 1, 0, 0):u"4",
             (0, 1, 0, 1):u"5",
             (0, 1, 1, 0):u"6",
             (0, 1, 1, 1):u"7",
             (1, 0, 0, 0):u"8",
             (1, 0, 0, 1):u"9",
             (1, 0, 1, 0):u"A",
             (1, 0, 1, 1):u"B",
             (1, 1, 0, 0):u"C",
             (1, 1, 0, 1):u"D",
             (1, 1, 1, 0):u"E",
             (1, 1, 1, 1):u"F"}

LE_LOOKUP = {(0, 0, 0, 0):u"0",
             (1, 0, 0, 0):u"1",
             (0, 1, 0, 0):u"2",
             (1, 1, 0, 0):u"3",
             (0, 0, 1, 0):u"4",
             (1, 0, 1, 0):u"5",
             (0, 1, 1, 0):u"6",
             (1, 1, 1, 0):u"7",
             (0, 0, 0, 1):u"8",
             (1, 0, 0, 1):u"9",
             (0, 1, 0, 1):u"A",
             (1, 1, 0, 1):u"B",
             (0, 0, 1, 1):u"C",
             (1, 0, 1, 1):u"D",
             (0, 1, 1, 1):u"E",
             (1, 1, 1, 1):u"F"}


def bits_to_chunks(bits_iter, colors, lookup=BE_LOOKUP):
    """for each Bits object in bits_iter, yields a Chunk object
    whose bits, superscripts, name and background_color have been populated

    positions and borders must be populated afterward
    """

    from itertools import izip,cycle

    superscript_bits = []
    for (bits, background_color) in izip(bits_iter,cycle(colors)):
        yield bits.chunk(superscript_bits, lookup, background_color)


def chunks_to_rows(chunks_iter, bits_per_row, x_offset=0):
    """for each Chunk object in chunks_iter
    yields a list of Chunk objects
    whose borders and east/west positions have been populated"""

    chunk_list = []
    x_position = x_offset

    for chunk in chunks_iter:
        #populate the chunk's borders
        chunk.w_border = chunk.e_border = True

        remaining_bits = bits_per_row - sum([c.size() for c in chunk_list])

        #split a single chunk across multiple rows, if necessary
        while (chunk.size() > remaining_bits):
            if (remaining_bits > 0):
                (row_end, row_start) = chunk.split(remaining_bits)

                #populate row_end's east/west positions
                row_end.set_w_offset(x_position)

                #before appending it to the row's chunks for returning
                chunk_list.append(row_end)
                yield chunk_list
                chunk = row_start
            elif (len(chunk_list) > 0):
                yield chunk_list

            #and resetting the row for the remainder of the chunk
            chunk_list = []
            x_position = x_offset
            remaining_bits = bits_per_row
        else:
            #populate the chunk's east/west positions
            chunk.set_w_offset(x_position)

            #and update the east/west position
            x_position += chunk.size() * BIT_WIDTH

            #before appending it to the row's chunks for returning
            chunk_list.append(chunk)
    else:
        #return any leftover chunks on the row
        yield chunk_list


def align_rows(chunk_rows_iter):
    chunk_rows = list(chunk_rows_iter)

    for (i, chunk_row) in enumerate(reversed(chunk_rows)):
        for chunk in chunk_row:
            chunk.set_s_offset(i * BIT_HEIGHT)

    for chunk_row in chunk_rows:
        for chunk in chunk_row:
            yield chunk


def int_converter(u):
    if (u.startswith(u"0x")):
        return long(u[2:], 16)
    elif (u.endswith(u"b")):
        return long(u[0:-1], 2)
    else:
        return long(u)


def bits_converter_be(size, value):
    size = int_converter(size)
    value = int_converter(value)

    bits = []
    for i in xrange(size):
        bits.append(value & 1)
        value >>= 1

    bits.reverse()

    return bits


def bits_converter_le(size, value):
    size = int_converter(size)
    value = int_converter(value)

    bits = []
    for i in xrange(size):
        bits.append(value & 1)
        value >>= 1

    return bits


def xml_to_chunks(xml_filename):
    import xml.dom.minidom

    dom = xml.dom.minidom.parse(xml_filename)
    struct = dom.getElementsByTagName(u"struct")[0]

    if (not struct.hasAttribute(u'endianness')):
        print >>sys.stderr,"struct tag's endianness must be big or little"
        sys.exit(1)

    if (struct.getAttribute(u'endianness') == u'big'):
        lookup = BE_LOOKUP
        bits_converter = bits_converter_be
    elif (struct.getAttribute(u'endianness') == u'little'):
        lookup = LE_LOOKUP
        bits_converter = bits_converter_le
    else:
        print >>sys.stderr,"struct tag's endianness must be big or little"
        sys.exit(1)

    bits = []
    for part in struct.childNodes:
        if (part.nodeName == u'field'):
            bits.append(Bits(part.childNodes[0].data.strip(),
                             bits_converter(part.getAttribute(u"size"),
                                            part.getAttribute(u"value"))))
        elif (part.nodeName == u'text'):
            bits.append(Text(part.childNodes[0].data.strip(),
                             int_converter(part.getAttribute(u"size"))))

    return bits_to_chunks(bits, [None], lookup)


if (__name__ == '__main__'):
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('-i','--input',dest='input',help='input XML file')
    parser.add_option('-o','--output',dest='output',help='output PDF file')
    parser.add_option('-b', '--bits-per-row', dest='bits_per_row',
                      type='int', default=16)
    parser.add_option('-w','--width',dest='width',
                      type='int', default=6 * 72,
                      help='digram width, in PostScript points')

    (options,args) = parser.parse_args()

    x_offset = (options.width - (options.bits_per_row * BIT_WIDTH)) / 2

    ChunkTable(list(align_rows(chunks_to_rows(
                    chunks_iter=xml_to_chunks(options.input),
                    bits_per_row=options.bits_per_row,
                    x_offset=x_offset)))).to_pdf(options.width, options.output)
