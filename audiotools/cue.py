#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2008-2013  Brian Langenberger

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

"""the cuesheet handling module"""

from audiotools import SheetException


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


class CueException(SheetException):
    """raised by cuesheet parsing errors"""

    pass


def __tokens__(cuedata):
    """yields (text, token, line) tuples from cuedata string

    text is a plain string
    token is an integer such as TAG or NUMBER
    line is a line number integer"""

    import re

    full_length = len(cuedata)
    cuedata = cuedata.lstrip('efbbbf'.decode('hex'))
    line_number = 1

    #This isn't completely accurate since the whitespace requirements
    #between tokens aren't enforced.
    TOKENS = [(re.compile("^(%s)" % (s)), element) for (s, element) in
              [(r'[A-Z]{2}[A-Za-z0-9]{3}[0-9]{7}', ISRC),
               (r'[0-9]{1,3}:[0-9]{1,2}:[0-9]{1,2}', TIMESTAMP),
               (r'[0-9]+', NUMBER),
               (r'[\r\n]+', EOL),
               (r'".+?"', STRING),
               (r'\S+', STRING),
               (r'[ ]+', SPACE)]]

    TAGMATCH = re.compile(r'^[A-Z]+$')

    while (True):
        for (token, element) in TOKENS:
            t = token.search(cuedata)
            if (t is not None):
                cuedata = cuedata[len(t.group()):]
                if (element == SPACE):
                    break
                elif (element == NUMBER):
                    yield (int(t.group()), element, line_number)
                elif (element == EOL):
                    line_number += 1
                    yield (t.group(), element, line_number)
                elif (element == STRING):
                    if (TAGMATCH.match(t.group())):
                        yield (t.group(), TAG, line_number)
                    else:
                        yield (t.group().strip('"'), element, line_number)
                elif (element == TIMESTAMP):
                    (m, s, f) = map(int, t.group().split(":"))
                    yield (((m * 60 * 75) + (s * 75) + f),
                           element, line_number)
                else:
                    yield (t.group(), element, line_number)
                break
        else:
            break

    if (len(cuedata) > 0):
        from .text import ERR_CUE_INVALID_TOKEN
        raise CueException(ERR_CUE_INVALID_TOKEN %
                           (full_length - len(cuedata)))


def get_value(tokens, accept, error):
    """retrieves a specific token from the stream of tokens

    tokens - the token iterator
    accept - an "or"ed list of all the tokens we'll accept
    error - the string to prepend to the error message

    returns the gotten value which matches one of the accepted tokens
    or raises ValueError if the token matches none of them
    """

    (token, element, line_number) = tokens.next()
    if ((element & accept) != 0):
        return token
    else:
        from .text import ERR_CUE_ERROR
        raise CueException(ERR_CUE_ERROR %
                           {"error": error,
                            "line": line_number})


def __parse__(tokens):
    """returns a Cuesheet object from the token iterator stream

    raises CueException if a parsing error occurs
    """

    from fractions import Fraction
    from audiotools import Sheet, SheetTrack, SheetIndex
    from .text import (ERR_CUE_INVALID_TRACK_NUMBER,
                       ERR_CUE_INVALID_TRACK_TYPE,
                       ERR_CUE_EXCESS_DATA,
                       ERR_CUE_MISSING_FILENAME,
                       ERR_CUE_MISSING_FILETYPE,
                       ERR_CUE_INVALID_TAG,
                       ERR_CUE_INVALID_DATA,
                       ERR_CUE_INVALID_FLAG,
                       ERR_CUE_INVALID_TIMESTAMP,
                       ERR_CUE_INVALID_INDEX_NUMBER,
                       ERR_CUE_MISSING_TAG,
                       ERR_CUE_MISSING_VALUE)

    def skip_to_eol(tokens):
        (token, element, line_number) = tokens.next()
        while (element != EOL):
            (token, element, line_number) = tokens.next()

    cuesheet_tracks = []
    cuesheet_catalog_number = None

    track_number = None
    track_indexes = []
    track_audio = False
    track_ISRC = None

    index_number = 0
    index_offset = 0

    try:
        while (True):
            (token, element, line_number) = tokens.next()
            if (element == TAG):

                #ignore comment lines
                if (token == "REM"):
                    skip_to_eol(tokens)

                #we're moving to a new track
                elif (token == 'TRACK'):
                    if (track_number is not None):
                        cuesheet_tracks.append(
                            SheetTrack(track_number,
                                       track_indexes,
                                       track_audio,
                                       track_ISRC))

                    track_number = get_value(tokens,
                                             NUMBER,
                                             ERR_CUE_INVALID_TRACK_NUMBER)
                    track_indexes = []
                    track_audio = (get_value(tokens,
                                             TAG | STRING,
                                             ERR_CUE_INVALID_TRACK_TYPE) ==
                                   "AUDIO")
                    track_ISRC = None

                    get_value(tokens, EOL, ERR_CUE_EXCESS_DATA)

                #if we haven't started on track data yet,
                #add catalog number to main track
                #or ignore other values
                elif (track_number is None):
                    if (token in ('CATALOG',
                                  'CDTEXTFILE',
                                  'PERFORMER',
                                  'SONGWRITER',
                                  'TITLE')):
                        if (token == 'CATALOG'):
                            cuesheet_catalog_number = str(get_value(
                                tokens, STRING | NUMBER ,
                                ERR_CUE_MISSING_VALUE))
                        else:
                            get_value(tokens,
                                      STRING | TAG | NUMBER | ISRC,
                                      ERR_CUE_MISSING_VALUE)

                        get_value(tokens, EOL, ERR_CUE_EXCESS_DATA)

                    elif (token == 'FILE'):
                        filename = get_value(tokens, STRING,
                                             ERR_CUE_MISSING_FILENAME)
                        filetype = get_value(tokens, STRING | TAG,
                                             ERR_CUE_MISSING_FILETYPE)

                        get_value(tokens, EOL, ERR_CUE_EXCESS_DATA)

                    else:
                        raise CueException(ERR_CUE_INVALID_TAG %
                                           {"tag": token,
                                            "line": line_number})
                #otherwise, we're adding data to the current track
                else:
                    if (token in ('ISRC',
                                  'PERFORMER',
                                  'SONGWRITER',
                                  'TITLE')):
                        if (token == 'ISRC'):
                            track_ISRC = get_value(tokens,
                                                   ISRC | NUMBER,
                                                   ERR_CUE_MISSING_VALUE)
                            if (isinstance(track_ISRC, int)):
                                #these are usually all 0s
                                #which isn't a valid ISRC
                                #and doesn't need to be stored
                                track_ISRC = None
                        else:
                            get_value(tokens,
                                      STRING | TAG | NUMBER | ISRC,
                                      ERR_CUE_MISSING_VALUE)

                        get_value(tokens, EOL, ERR_CUE_INVALID_DATA)

                    elif (token == 'FLAGS'):
                        flags = []
                        s = get_value(tokens,
                                      STRING | TAG | EOL,
                                      ERR_CUE_INVALID_FLAG)
                        while (('\n' not in s) and ('\r' not in s)):
                            flags.append(s)
                            s = get_value(tokens, STRING | TAG | EOL,
                                          ERR_CUE_INVALID_FLAG)

                    elif (token in ('POSTGAP', 'PREGAP')):
                        get_value(tokens,
                                  TIMESTAMP,
                                  ERR_CUE_INVALID_TIMESTAMP)
                        get_value(tokens, EOL, ERR_CUE_EXCESS_DATA)

                    elif (token == 'INDEX'):
                        index_number = get_value(tokens,
                                                 NUMBER,
                                                 ERR_CUE_INVALID_INDEX_NUMBER)
                        index_offset = get_value(tokens,
                                                 TIMESTAMP,
                                                 ERR_CUE_INVALID_TIMESTAMP)

                        track_indexes.append(
                            SheetIndex(index_number,
                                       Fraction(index_offset, 75)))

                        get_value(tokens, EOL, ERR_CUE_EXCESS_DATA)

                    elif (token in ('FILE',)):
                        skip_to_eol(tokens)

                    else:
                        raise CueException(ERR_CUE_INVALID_TAG %
                                           {"tag": token,
                                            "line": line_number})

            else:
                raise CueException(ERR_CUE_MISSING_TAG %
                                   (line_number,))
    except StopIteration:
        if (track_number is not None):
            cuesheet_tracks.append(SheetTrack(track_number,
                                              track_indexes,
                                              track_audio,
                                              track_ISRC))

        return Sheet(cuesheet_tracks, cuesheet_catalog_number)


def __attrib_str__(attrib):
    import re

    if (isinstance(attrib, tuple)):
        return " ".join([__attrib_str__(a) for a in attrib])
    elif (re.match(r'^[A-Z]+$', attrib) is not None):
        return attrib
    else:
        return "\"%s\"" % (attrib)


def read_cuesheet(filename):
    """returns a Sheet from a cuesheet filename on disk

    raises CueException if some error occurs reading or parsing the file
    """

    try:
        f = open(filename, 'r')
    except IOError, msg:
        from .text import ERR_CUE_IOERROR
        raise CueException(ERR_CUE_IOERROR)
    try:
        return __parse__(__tokens__(f.read()))
    finally:
        f.close()


def read_cuesheet_string(cuesheet):
    """given a plain string of cuesheet data returns a Sheet object

    raises CueException if some error occurs parsing the file"""

    return __parse__(__tokens__(cuesheet))


def write_cuesheet(sheet, filename, file):
    """given a Sheet object and filename string,
    writes a .cue file to the given file object"""

    from . import build_timestamp

    if (sheet.catalog() is not None):
        file.write("CATALOG %s\r\n" % (sheet.catalog()))

    file.write("FILE \"%s\" WAVE\r\n" % (filename))

    for track in sheet.tracks():
        file.write("  TRACK %2.2d %s\r\n" %
                   (track.number(),
                    ("AUDIO" if track.audio() else "BINARY")))

        if (track.ISRC() is not None):
            file.write("    ISRC %s\r\n" % (track.ISRC()))

        for index in track.indexes():
            file.write("    INDEX %2.2d %s\r\n" %
                       (index.number(),
                        build_timestamp(int(index.offset() * 75))))
