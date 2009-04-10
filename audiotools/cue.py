#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2008-2009  Brian Langenberger

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import re
from audiotools import SheetException,parse_timestamp,build_timestamp
import gettext

gettext.install("audiotools",unicode=True)

###################
#Cue Sheet Parsing
###################

#This method of cuesheet reading involves a tokenizer and parser,
#analagous to lexx/yacc.
#It might be easier to use a line-by-line ad-hoc method for parsing,
#but this brute-force approach should be a bit more thorough.

SPACE = 0x0
TAG = 0x1
NUMBER = 0x2
EOL = 0x4
STRING = 0x8
ISRC = 0x10
TIMESTAMP = 0x20

class CueException(SheetException): pass

def tokens(cuedata):
    full_length = len(cuedata)
    cuedata = cuedata.lstrip("\xEF\xBB\xBF")
    line_number = 1

    #This isn't completely accurate since the whitespace requirements
    #between tokens aren't enforced.
    TOKENS = [(re.compile("^(%s)" % (s)),element) for (s,element) in
              [(r'[A-Z]{2}[A-Za-z0-9]{3}[0-9]{7}',ISRC),
               (r'[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}',TIMESTAMP),
               (r'[0-9]+',NUMBER),
               (r'[\r\n]+',EOL),
               (r'".+?"',STRING),
               (r'\S+',STRING),
               (r'[ ]+',SPACE)]]

    TAGMATCH = re.compile(r'^[A-Z]+$')

    while (True):
        for (token,element) in TOKENS:
            t = token.search(cuedata)
            if (t is not None):
                cuedata = cuedata[len(t.group()):]
                if (element == SPACE):
                    break
                elif (element == NUMBER):
                    yield (int(t.group()),element,line_number)
                elif (element == EOL):
                    line_number += 1
                    yield (t.group(),element,line_number)
                elif (element == STRING):
                    if (TAGMATCH.match(t.group())):
                        yield (t.group(),TAG,line_number)
                    else:
                        yield (t.group().strip('"'),element,line_number)
                elif (element == TIMESTAMP):
                    (m,s,f) = map(int,t.group().split(":"))
                    yield (((m * 60 * 75) + (s * 75) + f),
                           element,line_number)
                else:
                    yield (t.group(),element,line_number)
                break
        else:
            break

    if (len(cuedata) > 0):
        raise CueException(_(u"Invalid token at char %d") % \
                                 (full_length - len(cuedata)))

#tokens is the token iterator
#accept is an "or"ed list of all the tokens we'll accept
#error is the string to prepend to the error message
#returns the gotten value which matches
#or throws ValueError if it does not
def get_value(tokens, accept, error):
    (token,element,line_number) = tokens.next()
    if ((element & accept) != 0):
        return token
    else:
        raise CueException(_(u"%(error)s at line %(line)d") % \
                                 {"error":error,
                                  "line":line_number})

#takes an iterator of tokens
#parses the cuesheet lines (usually <TAG> <DATA> ... <EOL> formatted)
#returns a Cuesheet object
#or raises CueException if we hit a parsing error
def parse(tokens):
    def skip_to_eol(tokens):
        (token,element,line_number) = tokens.next()
        while (element != EOL):
            (token,element,line_number) = tokens.next()

    cuesheet = Cuesheet()
    track = None

    try:
        while (True):
            (token,element,line_number) = tokens.next()
            if (element == TAG):

                #ignore comment lines
                if (token == "REM"):
                    skip_to_eol(tokens)

                #we're moving to a new track
                elif (token == 'TRACK'):
                    if (track is not None):
                        cuesheet.tracks[track.number] = track

                    track = Track(get_value(tokens,NUMBER,
                                            _(u"Invalid track number")),
                                  get_value(tokens,TAG | STRING,
                                            _(u"Invalid track type")))

                    get_value(tokens,EOL,"Excess data")

                #if we haven't started on track data yet,
                #add attributes to the main cue sheet
                elif (track is None):
                    if (token in ('CATALOG','CDTEXTFILE',
                                  'PERFORMER','SONGWRITER',
                                  'TITLE')):
                        cuesheet.attribs[token] = get_value(
                            tokens,
                            STRING | TAG | NUMBER | ISRC,
                            _(u"Missing value"))

                        get_value(tokens,EOL,_(u"Excess data"))

                    elif (token == 'FILE'):
                        filename = get_value(tokens,STRING,
                                             _(u"Missing filename"))
                        filetype = get_value(tokens,STRING | TAG,
                                             _(u"Missing file type"))

                        cuesheet.attribs[token] = (filename,filetype)

                        get_value(tokens,EOL,_(u"Excess data"))

                    else:
                        raise CueException(
                            _(u"Invalid tag %(tag)s at line %(line)d") % \
                                  {"tag":token,
                                   "line":line_number})
                #otherwise, we're adding data to the current track
                else:
                    if (token in ('ISRC','PERFORMER',
                                  'SONGWRITER','TITLE')):
                        track.attribs[token] = get_value(
                            tokens,
                            STRING | TAG | NUMBER | ISRC,
                            "Missing value")

                        get_value(tokens,EOL,_(u"Invalid data"))

                    elif (token == 'FLAGS'):
                        flags = []
                        s = get_value(tokens,STRING | TAG | EOL,
                                      _(u"Invalid flag"))
                        while (('\n' not in s) and ('\r' not in s)):
                            flags.append(s)
                            s = get_value(tokens,STRING | TAG | EOL,
                                          _(u"Invalid flag"))
                        track.attribs[token] = ",".join(flags)

                    elif (token in ('POSTGAP','PREGAP')):
                        track.attribs[token] = get_value(
                            tokens,TIMESTAMP,
                            _(u"Invalid timestamp"))
                        get_value(tokens,EOL,_(u"Excess data"))

                    elif (token == 'INDEX'):
                        index_number = get_value(tokens,NUMBER,
                                                 _(u"Invalid index number"))
                        index_timestamp = get_value(tokens,TIMESTAMP,
                                                    _(u"Invalid timestamp"))
                        track.indexes[index_number] = index_timestamp

                        get_value(tokens,EOL,_(u"Excess data"))

                    elif (token in ('FILE',)):
                        skip_to_eol(tokens)

                    else:
                        raise CueException(
                            _(u"Invalid tag %(tag)s at line %(line)d") % \
                                  {"tag":token,
                                   "line":line_number})

            else:
                raise CueException(_(u"Missing tag at line %d") % (line_number))
    except StopIteration:
        if (track is not None):
            cuesheet.tracks[track.number] = track
        return cuesheet


def __attrib_str__(attrib):
    if (isinstance(attrib,tuple)):
        return " ".join([__attrib_str__(a) for a in attrib])
    elif (re.match(r'^[A-Z]+$',attrib) is not None):
        return attrib
    else:
        return "\"%s\"" % (attrib)

class Cuesheet:
    def __init__(self):
        self.attribs = {}
        self.tracks = {}

    def __repr__(self):
        return "Cuesheet(attribs=%s,tracks=%s)" % \
            (repr(self.attribs),repr(self.tracks))

    def __str__(self):
        return "\r\n".join(["%s %s" % (key,__attrib_str__(value))
                            for key,value in self.attribs.items()] + \
                           [str(track) for track in sorted(self.tracks.values())])

    def catalog(self):
        if ('CATALOG' in self.attribs):
            return str(self.attribs['CATALOG'])
        else:
            return None

    #returns True if this cuesheet is for a single file
    def single_file_type(self):
        previous = -1
        for t in self.indexes():
            for index in t:
                if (index <= previous):
                    return False
                else:
                    previous = index
        else:
            return True


    #returns an iterator of index lists
    def indexes(self):
        for key in sorted(self.tracks.keys()):
            yield tuple(
                [self.tracks[key].indexes[k]
                 for k in sorted(self.tracks[key].indexes.keys())])


    #takes total_length of the entire file in PCM frames
    #returns a list of PCM lengths for all audio tracks within the cuesheet
    def pcm_lengths(self, total_length):
        previous = None

        for key in sorted(self.tracks.keys()):
            current = self.tracks[key].indexes
            if (previous is None):
                previous = current
            else:
                track_length = (current[max(current.keys())] - \
                                    previous[max(previous.keys())]) * (44100 / 75)
                total_length -= track_length
                yield track_length
                previous = current

        yield total_length

    #returns a track_number->ISRC dict
    #of all tracks whose ISRC is not empty
    def ISRCs(self):
        return dict([(track.number,track.ISRC()) for track in
                     self.tracks.values() if track.ISRC() is not None])

    #takes a sheet-compatible object with
    #catalog(), indexes() and ISRCs() methods
    #along with a filename string
    #returns a string of a newly-generated CUE sheet
    @classmethod
    def file(cls,sheet,filename):
        import cStringIO

        catalog = sheet.catalog()       #a catalog string, or None
        indexes = list(sheet.indexes()) #a list of index tuples
        ISRCs = sheet.ISRCs()           #a track_number->ISRC dict

        data = cStringIO.StringIO()

        if (catalog is not None):
            data.write("CATALOG %s\r\n" % (catalog))
        data.write("FILE \"%s\" WAVE\r\n" % (filename))

        for (i,current) in enumerate(indexes):
            tracknum = i + 1

            data.write("  TRACK %2.2d AUDIO\r\n" % (tracknum))

            if (tracknum in ISRCs.keys()):
                data.write("    ISRC %s\r\n" % (ISRCs[tracknum]))

            for (j,index) in enumerate(current):
                data.write("    INDEX %2.2d %s\r\n" % (j,
                                                       build_timestamp(index)))

        return data.getvalue()

class Track:
    def __init__(self, number, type):
        self.number = number
        self.type = type
        self.attribs = {}
        self.indexes = {}

    def __cmp__(self,t):
        return cmp(self.number,t.number)

    def __repr__(self):
        return "Track(%s,%s,attribs=%s,indexes=%s)" % \
            (repr(self.number),repr(self.type),
             repr(self.attribs),repr(self.indexes))

    def __str__(self):
        return ("  TRACK %2.2d %s\r\n" % (self.number,self.type)) + \
            "\r\n".join(["    %s %s" % (key,__attrib_str__(value))
                         for key,value in self.attribs.items()] + \
                        ["    INDEX %2.2d %2.2d:%2.2d:%2.2d" % \
                             (k,v / 75 / 60,v / 75 % 60,v % 75)
                         for (k,v) in sorted(self.indexes.items())])

    def ISRC(self):
        if ('ISRC' in self.attribs.keys()):
            return str(self.attribs['ISRC'])
        else:
            return None


def read_cuesheet(filename):
    try:
        f = open(filename,'r')
    except IOError,msg:
        raise CueException(unicode(msg))
    try:
        sheet = parse(tokens(f.read()))
        if (not sheet.single_file_type()):
            raise CueException(_(u"Cuesheet not formatted for disc images"))
        else:
            return sheet
    finally:
        f.close()
