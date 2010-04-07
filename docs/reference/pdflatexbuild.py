#!/usr/bin/python

#this is a wrapper around pdflatex(1)
#which monitors its stdout output
#and keeps re-running its arguments
#every time pdflatex writes "Rerun to get cross-references"
#or until pdflatex returns non-zero

import sys
import subprocess

if (__name__ == '__main__'):
    times_ran = 0
    rerun = True
    while (rerun):
        rerun = False
        print "Running pdflatex"
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

    print "pdflatex ran %s time(s)" % (times_ran)
