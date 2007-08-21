#!/usr/bin/python

import sys,re

if (__name__ == '__main__'):
    TITLE = re.compile(r'.TH ".*?" \d')

    for line in sys.stdin.readlines():
        if (line.startswith('.SH SEE ALSO')):
            break
        elif (line.startswith('.TH')):
            print >>sys.stdout,"%s \"\" \"\" \"\"" % (TITLE.findall(line)[0])
            #print >>sys.stdout,'.TH \"foo\"'
        else:
            sys.stdout.write(line)

