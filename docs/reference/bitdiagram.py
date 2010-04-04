#!/usr/bin/python

import sys

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import registerFont
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print "*** ReportLab is required"
    print "Please fetch the open-source version from http://www.reportlab.org"
    sys.exit(1)

(SOLID,DASHED,DOTTED,BLANK) = range(4)
(NE,NW,SE,SW) = range(4)
ROW_HEIGHT = 22

class Chunk:
    #text should be the chunk's text Unicode string, or None
    #width is size of the chunk as a floating point percentage
    #chunk_id is a unique text string, or None
    #style is one of the style enumerations such as SOLID, DASHED, etc.
    def __init__(self, text = None, start_size = None, end_size = None,
                 width = 1.0, chunk_id = None, style = SOLID):
        self.text = text
        self.width = width
        self.id = chunk_id
        self.style = style
        if (start_size is not None):
            self.start_size = unicode(start_size)
        else:
            self.start_size = None
        if (end_size is not None):
            self.end_size = unicode(end_size)
        else:
            self.end_size = None

        #the chunk's location in the PDF, in x,y point pairs
        self.ne = self.nw = self.se = self.sw = (0,0)

    def get_corner(self, corner):
        if (corner == NE):
            return self.ne
        elif (corner == NW):
            return self.nw
        elif (corner == SE):
            return self.se
        elif (corner == SW):
            return self.sw
        else:
            raise ValueError("invalid corner")

    def previous_column(self, row):
        i = row.index(self) - 1
        if (i >= 0):
            return row[i]
        else:
            return None

    def next_column(self, row):
        try:
            return row[row.index(self) + 1]
        except IndexError:
            return None

    def previous_chunk(self, chunks):
        i = chunks.index(self) - 1
        if (i >= 0):
            return chunks[i]
        else:
            return None

    def pt_width(self):
        return abs(self.nw[0] - self.ne[0])

    def pt_height(self):
        return abs(self.nw[1] - self.sw[1])

    def __repr__(self):
        return "Chunk(%s,%s,%s,%s,%s,%s)" % \
            (repr(self.text),self.start_size,self_end_size,
             self.width,self.id,self.style)

    def to_pdf(self, pdf):
        pdf.setStrokeColorRGB(0,0,0)
        pdf.setFillColorRGB(0,0,0)

        if (self.style is not BLANK):
            if (self.style == SOLID):
                pdf.setDash(1,0)
            elif (self.style == DASHED):
                pdf.setDash(6,6)
            elif (self.style == DOTTED):
                pdf.setDash(1,6)
            pdf.rect(self.sw[0],self.sw[1],self.pt_width(),self.pt_height())

        if (self.text is not None):
            pdf.setFont("DejaVu",10)
            pdf.drawCentredString((self.ne[0] + self.nw[0]) / 2,
                                  self.se[1] + 10,
                                  self.text)

            pdf.setFont("DejaVu",6)
            if ((self.start_size == self.end_size) and
                (self.start_size is not None)):
                pdf.drawCentredString((self.ne[0] + self.nw[0]) / 2,
                                  self.se[1] + 3,
                                  self.start_size)
            else:
                if (self.start_size is not None):
                    pdf.drawString(self.sw[0] + 4,
                                   self.se[1] + 3,
                                   self.start_size)
                if (self.end_size is not None):
                    pdf.drawRightString(self.se[0] - 4,
                                        self.se[1] + 3,
                                        self.end_size)

class BlankChunk(Chunk):
    def __init__(self, width = 1.0):
        Chunk.__init__(self,text=None,start_size=None,end_size=None,
                       width=width,chunk_id=None,
                       style=BLANK)

class Row:
    def __init__(self):
        self.chunks = []
        self.height = ROW_HEIGHT

    def add_chunk(self, chunk):
        self.chunks.append(chunk)

    def index(self, chunk):
        return self.chunks.index(chunk)

    def __iter__(self):
        return iter(self.chunks)

    def __len__(self):
        return len(self.chunks)

    def __getitem__(self, i):
        return self.chunks[i]

    def to_pdf(self, pdf, total_width, top, bottom):
        for (col_pos,chunk) in enumerate(self):
            previous_column = chunk.previous_column(self)
            if (previous_column is None):
                left = 0
            else:
                left = previous_column.ne[0]
            right = left + (chunk.width * total_width)

            chunk.nw = (left,top)
            chunk.ne = (right,top)
            chunk.sw = (left,bottom)
            chunk.se = (right,bottom)

            #render the calculated chunk
            chunk.to_pdf(pdf)

class Spacer(Row):
    def __init__(self, height):
        self.chunks = []
        self.height = height

    def add_chunk(self, chunk):
        pass

    def to_pdf(self, pdf, total_width, top, bottom):
        pass


class Line:
    def __init__(self,
                 start_chunk, start_corner,
                 end_chunk, end_corner,
                 style=SOLID):
        self.start_chunk = start_chunk
        self.start_corner = start_corner
        self.end_chunk = end_chunk
        self.end_corner = end_corner
        self.style = style

    def render(self, pdf):
        if (self.style is not BLANK):
            if (self.style == SOLID):
                pdf.setDash(1,0)
            elif (self.style == DASHED):
                pdf.setDash(6,6)
            elif (self.style == DOTTED):
                pdf.setDash(1,6)
            pdf.setStrokeColorRGB(0,0,0)
            (start_x,start_y) = self.start_chunk.get_corner(self.start_corner)
            (end_x,end_y) = self.end_chunk.get_corner(self.end_corner)
            pdf.line(start_x,start_y,end_x,end_y)

class ChunkTable:
    def __init__(self):
        self.rows = []
        self.chunks = []
        self.lines = []
        self.chunk_map = {}

    def add_row(self, *chunks):
        row = Row()
        for chunk in chunks:
            if (chunk.id is not None):
                if (chunk.id in self.chunk_map):
                    raise ValueError("chunk ID %s already taken" % (chunk.id))
                else:
                    self.chunk_map[chunk.id] = chunk

            row.add_chunk(chunk)
            self.chunks.append(chunk)
        self.rows.append(row)

    def add_spacer(self, height):
        self.rows.append(Spacer(height))

    def add_line(self, start_id, start_corner,
                 end_id, end_corner,
                 style=SOLID):
        self.lines.append(Line(self.chunk_map[start_id],start_corner,
                               self.chunk_map[end_id],end_corner,
                               style))

    #given a width value (in points) and filename string,
    #render all the lines and chunks as a PDF file
    def to_pdf(self, total_width, filename):
        total_rows = len(self.rows)
        total_height = sum([row.height for row in self.rows])

        registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))

        pdf = canvas.Canvas(filename)
        pdf.setPageSize((total_width,total_height))

        #calculate the positions of each row
        top = total_height
        for (row_pos,row) in enumerate(self.rows):
            bottom = top - row.height
            row.to_pdf(pdf, total_width, top, bottom)
            top = bottom

        #calculate the positions for each line
        for line in self.lines:
            line.render(pdf)

        pdf.showPage()
        pdf.save()


# def build_pdf():
#     wave = ChunkTable()
#     wave.add_row(Chunk(u"ID (\u2018RIFF\u2019 0x52494646)",0,31,.333333),
#                  Chunk(u"Chunk Size (file size - 8)",32,63,.333333),
#                  Chunk(u"Chunk Data",64,None,.333333,
#                        chunk_id="data"))
#     wave.add_row(BlankChunk(1.0))
#     wave.add_row(Chunk(u"Type (\u2018WAVE\u2019 0x57415645)",0,31,.333333,
#                        chunk_id="type"),
#                  Chunk(u"Chunk\u2081",32,None,.222222,
#                        chunk_id="chunk"),
#                  Chunk(u"Chunk\u2082",None,None,.222222),
#                  Chunk(u"...",None,None,.222222,style=DASHED,
#                        chunk_id="..."))

#     wave.add_line("data",SW,"type",NW,DOTTED)
#     wave.add_line("data",SE,"...",NE,DOTTED)

#     wave.add_row(BlankChunk(1.0))
#     wave.add_row(Chunk(u"Chunk ID (ASCII text)",0,31,.333333,
#                        chunk_id="chunk_id"),
#                  Chunk(u"Chunk Size",32,63,.333333),
#                  Chunk(u"Chunk Data",64,None,.333333,style=DASHED,
#                        chunk_id="chunk_data"))

#     wave.add_line("chunk",SW,"chunk_id",NW,DOTTED)
#     wave.add_line("chunk",SE,"chunk_data",NE,DOTTED)

#     wave.to_pdf(6 * 72,"bits.pdf")

def parse_xml(xml_filename):
    import xml.dom.minidom

    STYLE_MAP = {u"solid":SOLID,
                 u"dashed":DASHED,
                 u"dotted":DOTTED,
                 u"blank":BLANK}

    CORNER_MAP = {u"ne":NE,
                  u"se":SE,
                  u"nw":NW,
                  u"sw":SW}

    dom = xml.dom.minidom.parse(xml_filename)
    diagram = dom.getElementsByTagName(u"diagram")[0]
    table = ChunkTable()

    for part in diagram.childNodes:
        if (part.nodeName == u'row'):
            columns = []
            for col in part.childNodes:
                if (col.nodeName == u'col'):
                    chunk_args = {}
                    if (len(col.childNodes) > 0):
                        chunk_args["text"] = col.childNodes[0].data
                    if (col.hasAttribute("start")):
                        chunk_args["start_size"] = col.getAttribute("start")
                    if (col.hasAttribute("end")):
                        chunk_args["end_size"] = col.getAttribute("end")
                    if (col.hasAttribute("width")):
                        chunk_args["width"] = float(col.getAttribute("width"))
                    if (col.hasAttribute("id")):
                        chunk_args["chunk_id"] = col.getAttribute("id")
                    if (col.hasAttribute("style")):
                        chunk_args["style"] = STYLE_MAP[col.getAttribute("style")]
                    columns.append(Chunk(**chunk_args))
                elif (col.nodeName == u'blank'):
                    chunk_args = {}
                    if (col.hasAttribute("width")):
                        chunk_args["width"] = float(col.getAttribute("width"))
                    columns.append(BlankChunk(**chunk_args))

            table.add_row(*columns)
        elif (part.nodeName == u"spacer"):
            if (part.hasAttribute("height")):
                table.add_spacer(int(
                        round(ROW_HEIGHT *
                              float(part.getAttribute("height")))))
            else:
                table.add_spacer(ROW_HEIGHT)
        elif (part.nodeName == u"line"):
            table.add_line(part.getAttribute("s_id"),
                           CORNER_MAP[part.getAttribute("s_corner")],
                           part.getAttribute("e_id"),
                           CORNER_MAP[part.getAttribute("e_corner")],
                           STYLE_MAP[part.getAttribute("style")])

    return table

if (__name__ == '__main__'):
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('-i','--input',dest='input',help='input XML file')
    parser.add_option('-o','--output',dest='output',help='output PDF file')
    parser.add_option('-w','--width',dest='width',
                      type='int',default=6 * 72,
                      help='digram width, in PostScript points')

    (options,args) = parser.parse_args()

    if (options.input is None):
        print "*** An input file is required"
        sys.exit(1)
    if (options.output is None):
        print "*** An output file is required"
        sys.exit(1)

    parse_xml(options.input).to_pdf(options.width,options.output)
