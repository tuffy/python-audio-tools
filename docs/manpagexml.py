#!/usr/bin/python

# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2014  Brian Langenberger

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

import re
import time

WHITESPACE = re.compile(r'\s+')


def subtag(node, name):
    return [child for child in node.childNodes
            if (hasattr(child, "nodeName") and
                (child.nodeName == name))][0]


def subtags(node, name):
    return [child for child in node.childNodes
            if (hasattr(child, "nodeName") and
                (child.nodeName == name))]


def text(node):
    try:
        return WHITESPACE.sub(u" ", node.childNodes[0].wholeText.strip())
    except IndexError:
        return u""


def man_escape(s):
    return s.replace('-', '\\-').encode('ascii')


class Manpage:
    FIELDS = [
        ("%(track_number)2.2d", "the track's number on the CD"),
        ("%(track_total)d", "the total number of tracks on the CD"),
        ("%(album_number)d", "the CD's album number"),
        ("%(album_total)d", "the total number of CDs in the set"),
        ("%(album_track_number)s", "combination of album and track number"),
        ("%(track_name)s", "the track's name"),
        ("%(album_name)s", "the album's name"),
        ("%(artist_name)s", "the track's artist name"),
        ("%(performer_name)s", "the track's performer name"),
        ("%(composer_name)s", "the track's composer name"),
        ("%(conductor_name)s", "the track's conductor name"),
        ("%(media)s", "the track's source media"),
        ("%(ISRC)s", "the track's ISRC"),
        ("%(catalog)s", "the track's catalog number"),
        ("%(copyright)s", "the track's copyright information"),
        ("%(publisher)s", "the track's publisher"),
        ("%(year)s", "the track's publication year"),
        ("%(date)s", "the track's original recording date"),
        ("%(suffix)s", "the track's suffix"),
        ("%(basename)s", "the track's original name, without suffix")]

    def __init__(self,
                 utility=u"",
                 section=1,
                 name=u"",
                 title=u"",
                 synopsis=None,
                 description=u"",
                 author=u"",
                 options=None,
                 elements=None,
                 examples=None,
                 see_also=None):
        self.utility = utility
        self.section = int(section)
        self.name = name
        self.title = title
        self.synopsis = synopsis
        self.description = description
        self.author = author

        if (options is not None):
            self.options = options
        else:
            self.options = []

        if (examples is not None):
            self.examples = examples
        else:
            self.examples = []

        if (elements is not None):
            self.elements = elements
        else:
            self.elements = []

        if (see_also is not None):
            self.see_also = see_also
        else:
            self.see_also = []

    def __repr__(self):
        return "Manpage(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % \
            (repr(self.utility),
             repr(self.section),
             repr(self.name),
             repr(self.title),
             repr(self.synopsis),
             repr(self.description),
             repr(self.author),
             repr(self.options),
             repr(self.elements),
             repr(self.examples),
             repr(self.see_also))

    def flatten_options(self):
        for option_category in self.options:
            for option in option_category.options:
                yield option

    @classmethod
    def parse_file(cls, filename):
        return cls.parse(xml.dom.minidom.parse(filename))

    @classmethod
    def parse(cls, xml_dom):
        manpage = xml_dom.getElementsByTagName(u"manpage")[0]

        try:
            synopsis = text(subtag(manpage, u"synopsis"))
        except IndexError:
            synopsis = None

        options = [Options.parse(options)
                   for options in subtags(manpage, u"options")]

        elements = [Element.parse(element)
                    for element in subtags(manpage, u"element")]

        try:
            examples = [Example.parse(example)
                        for example in subtags(subtag(manpage,
                                                      u"examples"),
                                               u"example")]
        except IndexError:
            examples = None

        return cls(utility=text(subtag(manpage, u"utility")),
                   section=text(subtag(manpage, u"section")),
                   name=text(subtag(manpage, u"name")),
                   title=text(subtag(manpage, u"title")),
                   synopsis=synopsis,
                   description=text(subtag(manpage, u"description")),
                   author=text(subtag(manpage, u"author")),
                   options=options,
                   elements=elements,
                   examples=examples)

    def to_man(self, stream):
        stream.write((".TH \"%(utility)s\" %(section)d " +
                      "\"%(date)s\" \"\" \"%(title)s\"\n") %
                     {"utility": self.utility.upper().encode('ascii'),
                      "section": self.section,
                      "date": time.strftime("%B %Y", time.localtime()),
                      "title": self.title.encode('ascii')})
        stream.write(".SH NAME\n")
        stream.write("%(utility)s \\- %(name)s\n" %
                     {"utility": self.utility.encode('ascii'),
                      "name": self.name.encode('ascii')})
        if (self.synopsis is not None):
            stream.write(".SH SYNOPSIS\n")
            stream.write("%(utility)s %(synopsis)s\n" %
                         {"utility": self.utility.encode('ascii'),
                          "synopsis": self.synopsis.encode('ascii')})
        stream.write(".SH DESCRIPTION\n")
        stream.write(".PP\n")
        stream.write(self.description.encode('ascii'))
        stream.write("\n")
        for option in self.options:
            option.to_man(stream)
        for element in self.elements:
            element.to_man(stream)
        if (len(self.examples) > 0):
            if (len(self.examples) > 1):
                stream.write(".SH EXAMPLES\n")
            else:
                stream.write(".SH EXAMPLE\n")
            for example in self.examples:
                example.to_man(stream)

        for option in self.flatten_options():
            if (option.long_arg == 'format'):
                self.format_fields_man(stream)
                break

        self.see_also.sort(key=lambda x: x.utility)

        if (len(self.see_also) > 0):
            stream.write(".SH SEE ALSO\n")
            # handle the trailing comma correctly
            for page in self.see_also[0:-1]:
                stream.write(".BR %(utility)s (%(section)d),\n" %
                             {"utility": page.utility.encode('ascii'),
                              "section": page.section})

            stream.write(".BR %(utility)s (%(section)d)\n" %
                         {"utility": self.see_also[-1].utility.encode('ascii'),
                          "section": self.see_also[-1].section})

        stream.write(".SH AUTHOR\n")
        stream.write("%(author)s\n" % {"author": self.author.encode('ascii')})

    def format_fields_man(self, stream):
        stream.write(".SH FORMAT STRING FIELDS\n")
        stream.write(".TS\n")
        stream.write("tab(:);\n")
        stream.write("| c   s |\n")
        stream.write("| c | c |\n")
        stream.write("| r | l |.\n")
        stream.write("_\n")
        stream.write("Template Fields\n")
        stream.write("Key:Value\n")
        stream.write("=\n")
        for (field, description) in self.FIELDS:
            stream.write("\\fC%(field)s\\fR:%(description)s\n" %
                         {"field": field,
                          "description": description})
        stream.write("_\n")
        stream.write(".TE\n")

    def to_html(self, stream):
        stream.write('<div class="utility" id="%s">\n' %
                     (self.utility.encode('utf-8')))

        # display utility name
        stream.write("<h2>%s</h2>\n" % (self.utility.encode('utf-8')))

        # display utility description
        stream.write("<p>%s</p>\n" % (self.description.encode('utf-8')))

        # display options
        for option_section in self.options:
            option_section.to_html(stream)

        # display additional sections
        for element in self.elements:
            element.to_html(stream)

        # display examples
        if (len(self.examples) > 0):
            stream.write('<dl class="examples">\n')
            if (len(self.examples) > 1):
                stream.write("<dt>Examples</dt>\n")
            else:
                stream.write("<dt>Example</dt>\n")
            stream.write("<dd>\n")
            for example in self.examples:
                example.to_html(stream)
            stream.write("</dd>\n")
            stream.write("</dl>\n")

        stream.write('</div>\n')


class Options:
    def __init__(self, options, category=None):
        self.options = options
        self.category = category

    def __repr__(self):
        return "Options(%s, %s)" % \
            (self.options,
             self.category)

    @classmethod
    def parse(cls, xml_dom):
        if (xml_dom.hasAttribute(u"category")):
            category = xml_dom.getAttribute(u"category")
        else:
            category = None

        return cls(options=[Option.parse(child) for child in
                            subtags(xml_dom, u"option")],
                   category=category)

    def to_man(self, stream):
        if (self.category is None):
            stream.write(".SH OPTIONS\n")
        else:
            stream.write(".SH %(category)s OPTIONS\n" %
                         {"category":
                          self.category.upper().encode('ascii')})
        for option in self.options:
            option.to_man(stream)

    def to_html(self, stream):
        stream.write("<dl>\n")
        if (self.category is None):
            stream.write("<dt>Options</dt>\n")
        else:
            stream.write("<dt>%s Options</dt>\n" %
                         self.category.capitalize().encode('utf-8'))
        stream.write("<dd>\n")
        stream.write("<dl>\n")
        for option in self.options:
            option.to_html(stream)
        stream.write("</dl>\n")
        stream.write("</dd>\n")
        stream.write("</dl>\n")


class Option:
    def __init__(self,
                 short_arg=None,
                 long_arg=None,
                 arg_name=None,
                 description=None):
        self.short_arg = short_arg
        self.long_arg = long_arg
        self.arg_name = arg_name
        self.description = description

    def __repr__(self):
        return "Option(%s, %s, %s, %s)" % \
            (repr(self.short_arg),
             repr(self.long_arg),
             repr(self.arg_name),
             repr(self.description))

    @classmethod
    def parse(cls, xml_dom):
        if (xml_dom.hasAttribute("short")):
            short_arg = xml_dom.getAttribute("short")
            if (len(short_arg) > 1):
                raise ValueError("short arguments should be 1 character")
        else:
            short_arg = None

        if (xml_dom.hasAttribute("long")):
            long_arg = xml_dom.getAttribute("long")
        else:
            long_arg = None

        if (xml_dom.hasAttribute("arg")):
            arg_name = xml_dom.getAttribute("arg")
        else:
            arg_name = None

        if (len(xml_dom.childNodes) > 0):
            description = WHITESPACE.sub(
                u" ", xml_dom.childNodes[0].wholeText.strip())
        else:
            description = None

        return cls(short_arg=short_arg,
                   long_arg=long_arg,
                   arg_name=arg_name,
                   description=description)

    def to_man(self, stream):
        stream.write(".TP\n")
        if ((self.short_arg is not None) and (self.long_arg is not None)):
            if (self.arg_name is not None):
                stream.write(("\\fB\\-%(short_arg)s\\fR, " +
                              "\\fB\\-\\-%(long_arg)s\\fR=" +
                              "\\fI%(arg_name)s\\fR\n") %
                             {"short_arg": man_escape(self.short_arg),
                              "long_arg": man_escape(self.long_arg),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write(("\\fB\\-%(short_arg)s\\fR, " +
                              "\\fB\\-\\-%(long_arg)s\\fR\n") %
                             {"short_arg": man_escape(self.short_arg),
                              "long_arg": man_escape(self.long_arg)})
        elif (self.short_arg is not None):
            if (self.arg_name is not None):
                stream.write(("\\fB\\-%(short_arg)s\\fR " +
                              "\\fI%(arg_name)s\\fR\n") %
                             {"short_arg": man_escape(self.short_arg),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write("\\fB\\-%(short_arg)s\\fR\n" %
                             {"short_arg": man_escape(self.short_arg)})
        elif (self.long_arg is not None):
            if (self.arg_name is not None):
                stream.write(("\\fB\\-\\-%(long_arg)s\\fR" +
                              "=\\fI%(arg_name)s\\fR\n") %
                             {"long_arg": man_escape(self.long_arg),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write("\\fB\\-\\-%(long_arg)s\\fR\n" %
                             {"long_arg": man_escape(self.long_arg)})
        else:
            raise ValueError("short arg or long arg must be present in option")

        if (self.description is not None):
            stream.write(self.description.encode('ascii'))
            stream.write("\n")

    def to_html(self, stream):
        stream.write("<dt>\n")
        if ((self.short_arg is not None) and (self.long_arg is not None)):
            if (self.arg_name is not None):
                stream.write(("<b>-%(short_arg)s</b>, " +
                              "<b>--%(long_arg)s</b>=" +
                              "<i>%(arg_name)s</i>\n") %
                             {"short_arg": self.short_arg.encode('utf-8'),
                              "long_arg": self.long_arg.encode('utf-8'),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write(("<b>-%(short_arg)s</b>, " +
                              "<b>--%(long_arg)s</b>\n") %
                             {"short_arg": self.short_arg.encode('utf-8'),
                              "long_arg": self.long_arg.encode('utf-8')})
        elif (self.short_arg is not None):
            if (self.arg_name is not None):
                stream.write(("<b>-%(short_arg)s</b> " +
                              "<i>%(arg_name)s</i>\n") %
                             {"short_arg": self.short_arg.encode('utf-8'),
                              "arg_name":
                              self.arg_name.upper().encode('utf-8')})
            else:
                stream.write("<b>-%(short_arg)s\n" %
                             {"short_arg": self.short_arg.encode('utf-8')})
        elif (self.long_arg is not None):
            if (self.arg_name is not None):
                stream.write(("<b>--%(long_arg)s</b>" +
                              "=<i>%(arg_name)s</i>\n") %
                             {"long_arg": self.long_arg.encode('utf-8'),
                              "arg_name":
                              self.arg_name.upper().encode('utf-8')})
            else:
                stream.write("<b>--%(long_arg)s</b>\n" %
                             {"long_arg": self.long_arg.encode('utf-8')})
        else:
            raise ValueError("short arg or long arg must be present in option")

        stream.write("</dt>\n")

        if (self.description is not None):
            stream.write("<dd>%s</dd>\n" % (self.description.encode('ascii')))
        else:
            stream.write("<dd></dd>\n")


class Example:
    def __init__(self,
                 description=u"",
                 commands=[]):
        self.description = description
        self.commands = commands

    def __repr__(self):
        return "Example(%s, %s)" % \
            (repr(self.description),
             repr(self.commands))

    @classmethod
    def parse(cls, xml_dom):
        return cls(description=text(subtag(xml_dom, u"description")),
                   commands=map(Command.parse, subtags(xml_dom, u"command")))

    def to_man(self, stream):
        stream.write(".LP\n")
        stream.write(self.description.encode('ascii'))  # FIXME
        stream.write("\n")
        for command in self.commands:
            command.to_man(stream)

    def to_html(self, stream):
        stream.write('<dl>\n')
        stream.write("<dt>%s</dt>\n" % (self.description.encode('utf-8')))
        stream.write("<dd>\n")
        for command in self.commands:
            command.to_html(stream)
        stream.write("</dd>\n")
        stream.write("</dl>\n")


class Command:
    def __init__(self, commandline, note=None):
        self.commandline = commandline
        self.note = note

    def __repr__(self):
        return "Command(%s, %s)" % (repr(self.commandline),
                                    repr(self.note))

    @classmethod
    def parse(cls, xml_dom):
        if (xml_dom.hasAttribute(u"note")):
            note = xml_dom.getAttribute(u"note")
        else:
            note = None

        return cls(commandline=text(xml_dom),
                   note=note)

    def to_man(self, stream):
        if (self.note is not None):
            stream.write(".LP\n")
            stream.write(self.note.encode('ascii') + " :\n\n")

        stream.write(".IP\n")
        stream.write(self.commandline.encode('ascii'))
        stream.write("\n\n")

    def to_html(self, stream):
        if (self.note is not None):
            stream.write('<span class="note">%s :</span><br>\n' %
                         self.note.encode('utf-8'))

        stream.write(self.commandline.encode('utf-8'))
        stream.write("<br>\n")


class Element_P:
    def __init__(self, contents):
        self.contents = contents

    def __repr__(self):
        return "Element_P(%s)" % (repr(self.contents))

    @classmethod
    def parse(cls, xml_dom):
        return cls(contents=text(xml_dom))

    def to_man(self, stream):
        stream.write(self.contents.encode('ascii'))
        stream.write("\n.PP\n")

    def to_html(self, stream):
        stream.write("<p>%s</p>" % (self.contents.encode('utf-8')))


class Element_UL:
    def __init__(self, list_items):
        self.list_items = list_items

    def __repr__(self):
        return "Element_UL(%s)" % (repr(self.list_items))

    @classmethod
    def parse(cls, xml_dom):
        return cls(list_items=map(text, subtags(xml_dom, u"li")))

    def to_man(self, stream):
        for item in self.list_items:
            stream.write("\\[bu] ")
            stream.write(item.encode('ascii'))
            stream.write("\n")
            stream.write(".PP\n")

    def to_html(self, stream):
        stream.write("<ul>\n")
        for item in self.list_items:
            stream.write("<li>%s</li>\n" % (item.encode('utf-8')))
        stream.write("</ul>\n")


class Element_TABLE:
    def __init__(self, rows):
        self.rows = rows

    def __repr__(self):
        return "Element_TABLE(%s)" % (repr(self.rows))

    @classmethod
    def parse(cls, xml_dom):
        return cls(rows=[Element_TR.parse(tr) for tr in subtags(xml_dom,
                                                                u"tr")])

    def to_man(self, stream):
        if (len(self.rows) == 0):
            return

        if (len(set([len(row.columns) for row in self.rows
                     if row.tr_class in (TR_NORMAL, TR_HEADER)])) != 1):
            raise ValueError("all rows must have the same number of columns")
        else:
            columns = len(self.rows[0].columns)

        stream.write(".TS\n")
        stream.write("tab(:);\n")
        stream.write(" ".join(["l" for l in self.rows[0].columns]) + ".\n")
        for row in self.rows:
            row.to_man(stream)
        stream.write(".TE\n")

    def to_html(self, stream):
        if (len(self.rows) == 0):
            return

        if (len(set([len(row.columns) for row in self.rows
                     if row.tr_class in (TR_NORMAL, TR_HEADER)])) != 1):
            raise ValueError("all rows must have the same number of columns")

        stream.write("<table>\n")
        for (row, spans) in zip(self.rows, self.calculate_row_spans()):
            row.to_html(stream, spans)
        stream.write("</table>\n")

    def calculate_row_spans(self):
        # turn rows into arrays of "span" boolean values
        row_spans = []
        for row in self.rows:
            if (row.tr_class in (TR_NORMAL, TR_HEADER)):
                row_spans.append([col.empty() for col in row.columns])
            elif (row.tr_class == TR_DIVIDER):
                row_spans.append([False] * len(row_spans[-1]))

        # turn columns into arrays of integers containing the row span
        columns = [list(self.calculate_span_column([row[i] for
                                                    row in row_spans]))
                   for i in xrange(len(row_spans[0]))]

        # turn columns back into rows and return them
        return zip(*columns)

    def calculate_span_column(self, row_spans):
        rows = None
        for span in row_spans:
            if (span):
                rows += 1
            else:
                if (rows is not None):
                    yield rows
                    for i in xrange(rows - 1):
                        yield 0
                rows = 1

        if (rows is not None):
            yield rows
            for i in xrange(rows - 1):
                yield 0


(TR_NORMAL, TR_HEADER, TR_DIVIDER) = range(3)


class Element_TR:
    def __init__(self, columns, tr_class):
        self.columns = columns
        self.tr_class = tr_class

    def __repr__(self):
        if (self.tr_class in (TR_NORMAL, TR_HEADER)):
            return "Element_TR(%s, %s)" % (repr(self.columns), self.tr_class)
        else:
            return "Element_TR_DIVIDER()"

    @classmethod
    def parse(cls, xml_dom):
        if (xml_dom.hasAttribute("class")):
            if (xml_dom.getAttribute("class") == "header"):
                return cls(columns=[Element_TD.parse(tag)
                                    for tag in subtags(xml_dom, u"td")],
                           tr_class=TR_HEADER)
            elif (xml_dom.getAttribute("class") == "divider"):
                return cls(columns=None, tr_class=TR_DIVIDER)
            else:
                raise ValueError("unsupported class \"%s\"" %
                                 (xmldom_getAttribute("class")))
        else:
            return cls(columns=[Element_TD.parse(tag)
                                for tag in subtags(xml_dom, u"td")],
                       tr_class=TR_NORMAL)

    def to_man(self, stream):
        if (self.tr_class == TR_NORMAL):
            stream.write(":".join([column.string()
                                   for column in self.columns]) + "\n")
        elif (self.tr_class == TR_HEADER):
            stream.write(":".join(["\\fB%s\\fR" % (column.string())
                                   for column in self.columns]) + "\n")
            stream.write("_\n")
        elif (self.tr_class == TR_DIVIDER):
            stream.write("_\n")

    def column_widths(self):
        if (self.tr_class in (TR_NORMAL, TR_HEADER)):
            return [column.width() for column in self.columns]
        else:
            return None

    def to_html(self, stream, rowspans):
        if (self.tr_class in (TR_NORMAL, TR_HEADER)):
            stream.write("<tr>\n")
            for (column, span) in zip(self.columns, rowspans):
                column.to_html(stream, self.tr_class == TR_HEADER, span)
            stream.write("</tr>\n")


class Element_TD:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Element_TD(%s)" % (repr(self.value))

    @classmethod
    def parse(cls, xml_dom):
        try:
            return cls(value=WHITESPACE.sub(
                       u" ",
                       xml_dom.childNodes[0].wholeText.strip()))
        except IndexError:
            return cls(value=None)

    def empty(self):
        return self.value is None

    def string(self):
        if (self.value is not None):
            return self.value.encode('ascii')
        else:
            return "\\^"

    def to_man(self, stream):
        stream.write(self.value.encode('ascii'))

    def width(self):
        if (self.value is not None):
            return len(self.value)
        else:
            return 0

    def to_html(self, stream, header, rowspan):
        if (self.value is not None):
            if (rowspan > 1):
                rowspan = " rowspan=\"%d\"" % (rowspan)
            else:
                rowspan = ""

            if (header):
                stream.write("<th%s>%s</th>" %
                             (rowspan, self.value.encode('utf-8')))
            else:
                stream.write("<td%s>%s</td>" %
                             (rowspan, self.value.encode('utf-8')))


class Element:
    SUB_ELEMENTS = {u"p": Element_P,
                    u"ul": Element_UL,
                    u"table": Element_TABLE}

    def __init__(self, name, elements):
        self.name = name
        self.elements = elements

    def __repr__(self):
        return "Element(%s, %s)" % (repr(self.name), repr(self.elements))

    @classmethod
    def parse(cls, xml_dom):
        if (xml_dom.hasAttribute(u"name")):
            name = xml_dom.getAttribute(u"name")
        else:
            raise ValueError("elements must have names")

        elements = []
        for child in xml_dom.childNodes:
            if (hasattr(child, "tagName")):
                if (child.tagName in cls.SUB_ELEMENTS.keys()):
                    elements.append(
                        cls.SUB_ELEMENTS[child.tagName].parse(child))
                else:
                    raise ValueError("unsupported tag %s" %
                                     (child.tagName.encode('ascii')))

        return cls(name=name,
                   elements=elements)

    def to_man(self, stream):
        stream.write(".SH %s\n" % (self.name.upper().encode('ascii')))
        for element in self.elements:
            element.to_man(stream)

    def to_html(self, stream):
        stream.write("<dl>\n")
        stream.write("<dt>%s</dt>\n" %
                     ((u" ".join([part.capitalize()
                                  for part in
                                  self.name.split()])).encode('utf-8')))
        stream.write("<dd>\n")
        for element in self.elements:
            element.to_html(stream)
        stream.write("</dd>\n")
        stream.write("</dl>\n")


if (__name__ == '__main__'):
    import sys
    import xml.dom.minidom
    import argparse

    parser = argparse.ArgumentParser(description="manual page generator")

    parser.add_argument("-i", "--input",
                        dest="input",
                        help="the primary input XML file")

    parser.add_argument("-t", "--type",
                        dest="type",
                        choices=("man", "html"),
                        default="man",
                        help="the output type")

    parser.add_argument("see_also",
                        metavar="FILENAME",
                        nargs="*",
                        help="\"see also\" man pages")

    options = parser.parse_args()

    if (options.input is not None):
        main_page = Manpage.parse_file(options.input)
        all_pages = [Manpage.parse_file(filename)
                     for filename in options.see_also]
        main_page.see_also = [page for page in all_pages
                              if (page.utility != main_page.utility)]

        if (options.type == "man"):
            main_page.to_man(sys.stdout)
        elif (options.type == "html"):
            main_page.to_html(sys.stdout)
