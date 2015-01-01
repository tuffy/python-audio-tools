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

# this program uses pdftk to add Title and Author tags to PDF files

from __future__ import print_function
import sys
import subprocess
import tempfile
import argparse

if (__name__ == "__main__"):
    parser = argparse.ArgumentParser(description="pdftk wrapper")
    parser.add_argument("-t", "--title",
                        dest="title",
                        help="the PDF's Title field")
    parser.add_argument("-a", "--author",
                        dest="author",
                        help="the PDF's Author field")
    parser.add_argument("filenames",
                        metavar="FILENAME",
                        nargs="+",
                        help="input PDF filename")

    options = parser.parse_args()
    if (len(options.filenames) < 1):
        print("*** at least 1 PDF is required", file=sys.stderr)
        sys.exit(1)

    fields = {}
    if (options.title is not None):
        fields["Title"] = options.title
    if (options.author is not None):
        fields["Author"] = options.author

    for pdf in options.filenames:
        # grab the PDF's current Info data
        dump = subprocess.Popen(["pdftk", pdf, "dump_data"],
                                stdout=subprocess.PIPE)
        info_data = []

        # filter out any duplicate keys already in "fields"
        line = dump.stdout.readline()
        while (len(line) > 0):
            if (line.startswith("InfoKey:") and
                (line[len("InfoKey:"):].strip() in fields.keys())):
                dump.stdout.readline()  # skip InfoValue also
            else:
                info_data.append(line)
            line = dump.stdout.readline()
        if (dump.wait() != 0):
            print("*** Error dumping data with pdftk", file=sys.stderr)
            sys.exit(1)

        temp_info = tempfile.NamedTemporaryFile(suffix=".info")
        temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf")
        try:
            # dump our new fields and existing data to a temporary info file
            for field in ["Title", "Author"]:
                if (field in fields.keys()):
                    temp_info.write("InfoKey: %s\n" % (field))
                    temp_info.write("InfoValue: %s\n" % (fields[field]))

            for line in info_data:
                temp_info.write(line)
            temp_info.flush()

            # use pdftk to add the info file's contents to a temporary PDF
            if (subprocess.call(["pdftk", pdf, "update_info",
                                 temp_info.name,
                                 "output", temp_pdf.name]) != 0):
                print("*** Error transferring data with pdftk",
                      file=sys.stderr)
                sys.exit(1)

            # copy the temporary PDF over the original PDF
            if (subprocess.call(["cp", "-f", temp_pdf.name, pdf]) != 0):
                print("*** Error copying updated PDF over original",
                      file=sys.stderr)
                sys.exit(1)
        finally:
            # close temporary files
            temp_info.close()
            temp_pdf.close()
