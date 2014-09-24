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

from audiotools.cue.tokrules import tokens


def p_cuesheet(t):
    '''cuesheet : files
                | cuesheet_items files'''

    from audiotools.cue import Cuesheet

    if (len(t) == 2):
        t[0] = Cuesheet(files=t[1])
    else:
        # FIXME - check against multiple "once only" attributes
        args = {}
        for (key, value) in t[1]:
            args[key] = value
        t[0] = Cuesheet(files=t[2], **args)


def p_cuesheet_items(t):
    '''cuesheet_items : cuesheet_item
                      | cuesheet_items cuesheet_item'''
    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]


def p_cuesheet_item(t):
    '''cuesheet_item : catalog
                     | title
                     | performer
                     | songwriter
                     | cdtextfile'''
    t[0] = t[1]


def p_catalog_string(t):
    'catalog : CATALOG STRING'

    t[0] = ("catalog", t[2])


def p_catalog_number(t):
    'catalog : CATALOG NUMBER'

    t[0] = ("catalog", "%13.13d" % (t[2]))


def p_title(t):
    'title : TITLE STRING'
    t[0] = ("title", t[2])


def p_performer(t):
    'performer : PERFORMER STRING'
    t[0] = ("performer", t[2])


def p_songwriter(t):
    'songwriter : SONGWRITER STRING'
    t[0] = ("songwriter", t[2])


def p_cdtextfile(t):
    'cdtextfile : CDTEXTFILE STRING'
    t[0] = ("cdtextfile", t[2])


def p_files(t):
    '''files : file
             | files file'''
    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]


def p_file(t):
    'file : FILE STRING filetype tracks'

    from audiotools.cue import File

    # FIXME - ensure tracks are ascending

    t[0] = File(filename=t[2],
                file_type=t[3],
                tracks=t[4])


def p_filetype(t):
    '''filetype : BINARY
                | MOTOROLA
                | AIFF
                | WAVE
                | MP3
                | FLAC'''
    t[0] = t[1]


def p_tracks(t):
    '''tracks : track
              | tracks track'''
    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]


def p_track(t):
    'track : TRACK NUMBER tracktype trackitems'

    from audiotools.cue import Track

    indexes = []
    args = {}

    for (key, value) in t[4]:
        if (key == "index"):
            indexes.append(value)
        else:
            args[key] = value

    # FIXME - ensure that index points are ascending

    t[0] = Track(number=t[2],
                 track_type=t[3],
                 indexes=indexes,
                 **args)


def p_tracktype(t):
    '''tracktype : AUDIO
                 | CDG
                 | MODE
                 | CDI'''
    # FIXME - return whether type is audio or not
    t[0] = t[1]


def p_indexes(t):
    '''trackitems : trackitem
                  | trackitems trackitem'''
    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]


def p_trackitem(t):
    '''trackitem : index
                 | isrc
                 | pregap
                 | postgap
                 | flags
                 | title
                 | performer
                 | songwriter'''
    t[0] = t[1]


def p_index(t):
    'index : INDEX NUMBER TIMESTAMP'

    from audiotools.cue import Index

    t[0] = ("index", Index(number=t[2], timestamp=t[3]))


def p_isrc(t):
    '''isrc : ISRC_ID ISRC
            | ISRC_ID NUMBER'''
    t[0] = ("isrc", u"%s" % (t[2],))


def p_pregap(t):
    'pregap : PREGAP TIMESTAMP'
    t[0] = ("pregap", t[2])


def p_postgap(t):
    'postgap : POSTGAP TIMESTAMP'
    t[0] = ("postgap", t[2])


def p_flags(t):
    'flags : FLAGS flaglist'
    t[0] = ("flags", t[2])


def p_flaglist(t):
    '''flaglist : flag
                | flaglist flag'''
    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]


def p_flag(t):
    '''flag : DCP
            | PRE
            | SCMS'''
    t[0] = t[1]


def p_error(t):
    from audiotools.text import ERR_CUE_SYNTAX_ERROR

    raise ValueError(ERR_CUE_SYNTAX_ERROR % (t.lexer.lineno))
