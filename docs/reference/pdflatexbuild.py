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

# this is a wrapper around pdflatex(1)
# which monitors its stdout output
# and keeps re-running its arguments
# every time pdflatex writes "Rerun to get cross-references"
# or until pdflatex returns non-zero

from __future__ import print_function
import sys
import subprocess

if (__name__ == '__main__'):
    times_ran = 0
    rerun = True
    while (rerun):
        rerun = False
        print("Running pdflatex")
        sub = subprocess.Popen(["pdflatex"] + sys.argv[1:],
                               stdout=subprocess.PIPE)
        times_ran += 1
        line = sub.stdout.readline()
        while (len(line) > 0):
            if ("Rerun to get cross-references" in line):
                rerun = True
            sys.stdout.write(line)
            line = sub.stdout.readline()
        if (sub.wait() != 0):
            rerun = False

    print("pdflatex ran %s time(s)" % (times_ran))
