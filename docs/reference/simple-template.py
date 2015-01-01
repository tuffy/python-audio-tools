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


class Template:
    def __init__(self, replacements):
        import re

        self.__replacements__ = replacements
        self.__template__ = re.compile(r'<<([a-z]+?):(.+?)>>')

    def process_string(self, s):
        return self.__template__.sub(self.process_command, s)

    def process_command(self, match):
        command = match.group(1)
        argument = match.group(2)
        if command == "const":
            return (self.__replacements__[argument]
                    if argument in self.__replacements__ else "")
        elif command == "file":
            with open(argument, "r") as f:
                return self.process_string(f.read().strip())
        else:
            print("*** Unknown command \"%s\"" % (command),
                  file=sys.stderr)
            sys.exit(1)


if (__name__ == "__main__"):
    import argparse

    parser = argparse.ArgumentParser("trivial Python templating system")

    parser.add_argument("-D",
                        action="append",
                        dest="const",
                        help="constant definition")

    parser.add_argument("filename",
                        metavar="FILENAME")

    options = parser.parse_args()

    template = Template(dict([arg.split("=", 1) for arg in options.const])
                        if options.const is not None else {})
    with open(options.filename, "rb") as f:
        sys.stdout.write(template.process_string(f.read()))
