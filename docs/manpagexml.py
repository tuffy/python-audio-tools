#!/usr/bin/python

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
    return WHITESPACE.sub(u" ", node.childNodes[0].wholeText.strip())

def man_escape(s):
    return s.replace('-','\\-').encode('ascii')


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
                 synopsis=u"",
                 description=u"",
                 author=u"",
                 options=None,
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
        if (see_also is not None):
            self.see_also = see_also
        else:
            self.see_also = []

    def __repr__(self):
        return "Manpage(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % \
            (repr(self.utility),
             repr(self.section),
             repr(self.name),
             repr(self.title),
             repr(self.synopsis),
             repr(self.description),
             repr(self.author),
             repr(self.options),
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

        options = [Options.parse(options)
                   for options in subtags(manpage, u"options")]

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
                   synopsis=text(subtag(manpage, u"synopsis")),
                   description=text(subtag(manpage, u"description")),
                   author=text(subtag(manpage, u"author")),
                   options=options,
                   examples=examples)

    def to_man(self, stream):
        stream.write(".TH \"%(utility)s\" %(section)d \"%(date)s\" \"\" \"%(title)s\"\n" %
                     {"utility": self.utility.upper().encode('ascii'),
                      "section": self.section,
                      "date": time.strftime("%B %Y", time.localtime()),
                      "title": self.title.encode('ascii')})
        stream.write(".SH NAME\n")
        stream.write("%(utility)s \\- %(name)s\n" %
                     {"utility": self.utility.encode('ascii'),
                      "name": self.name.encode('ascii')})
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

        self.see_also.sort(lambda x,y: cmp(x.utility, y.utility))

        if (len(self.see_also) > 0):
            stream.write(".SH SEE ALSO\n")
            #handle the trailing comma correctly
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
            stream.write(".SH %(category)s OPTIONS\n" % \
                             {"category":
                                  self.category.upper().encode('ascii')})
        for option in self.options:
            option.to_man(stream)


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
        if ((self.short_arg is not None) and
            (self.long_arg is not None)):
            if (self.arg_name is not None):
                stream.write(("\\fB\\-%(short_arg)s\\fR, " +
                              "\\fB\\-\\-%(long_arg)s\\fR=" +
                              "\\fI%(arg_name)s\\fR\n") %
                             {"short_arg": man_escape(self.short_arg),
                              "long_arg": man_escape(self.long_arg),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write(("\\fB\\-%(short_arg)s\\fR, " +
                              "\\fB\\-\\-%(long_arg)s\n") %
                             {"short_arg": man_escape(self.short_arg),
                              "long_arg": man_escape(self.long_arg)})
        elif (self.short_arg is not None):
            if (self.arg_name is not None):
                stream.write(("\\fB\\-%(short_arg)s\\fR " +
                              "\\fI%(arg_name)s\\fR\n") %
                             {"short_arg": man_escape(self.short_arg),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write("\\fB\\-%(short_arg)s\n" %
                             {"short_arg": man_escape(self.short_arg)})
        elif (self.long_arg is not None):
            if (self.arg_name is not None):
                stream.write(("\\fB\\-\\-%(long_arg)s\\fR" +
                              "=\\fI%(arg_name)s\\fR\n") %
                             {"long_arg": man_escape(self.long_arg),
                              "arg_name": man_escape(self.arg_name.upper())})
            else:
                stream.write("\\fB\\-\\-%(long_arg)s\n" %
                             {"long_arg": man_escape(self.long_arg)})
        else:
            raise ValueError("short arg or long arg must be present in option")

        if (self.description is not None):
            stream.write(self.description.encode('ascii'))
            stream.write("\n")


class Example:
    def __init__(self,
                 description=u"",
                 command=u""):
        self.description = description
        self.command = command

    def __repr__(self):
        return "Example(%s, %s)" % \
            (repr(self.description),
             repr(self.command))

    @classmethod
    def parse(cls, xml_dom):
        return cls(description=text(subtag(xml_dom, u"description")),
                   command=text(subtag(xml_dom, u"command")))

    def to_man(self, stream):
        stream.write(".LP\n")
        stream.write(self.description.encode('ascii')) #FIXME
        stream.write("\n")
        stream.write(".IP\n")
        stream.write(self.command.encode('ascii')) #FIXME
        stream.write("\n")

if (__name__ == '__main__'):
    import sys
    import xml.dom.minidom
    import optparse

    parser = optparse.OptionParser()

    parser.add_option("-i", "--input",
                      dest="input",
                      help="the primary input XML file")

    parser.add_option("-t", "--type",
                      dest="type",
                      choices=("man", ),
                      default="man",
                      help="the output type")

    (options, args) = parser.parse_args()

    main_page = Manpage.parse_file(options.input)
    all_pages = [Manpage.parse_file(filename) for filename in args]
    main_page.see_also = [page for page in all_pages
                          if (page.utility != main_page.utility)]

    if (options.type == "man"):
        main_page.to_man(sys.stdout)
