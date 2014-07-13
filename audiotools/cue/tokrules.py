#!/usr/bin/python

#Audio Tools, a module and set of tools for manipulating audio data
#Copyright (C) 2007-2014  Brian Langenberger

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

RESERVED = {"CATALOG":"CATALOG",
            "CDTEXTFILE":"CDTEXTFILE",
            "FILE":"FILE",
            "BINARY":"BINARY",
            "MOTOROLA":"MOTOROLA",
            "AIFF":"AIFF",
            "WAVE":"WAVE",
            "FLAGS":"FLAGS",
            "DCP":"DCP",
            "PRE":"PRE",
            "SCMS":"SCMS",
            "INDEX":"INDEX",
            "ISRC":"ISRC_ID",
            "PERFORMER":"PERFORMER",
            "POSTGAP":"POSTGAP",
            "PREGAP":"PREGAP",
            "SONGWRITER":"SONGWRITER",
            "TITLE":"TITLE",
            "TRACK":"TRACK",
            "AUDIO":"AUDIO",
            "CDG":"CDG"}

tokens = ["REM",
          "ISRC",
          "TIMESTAMP",
          "MP3",
          "MODE",
          "CDI",
          "NUMBER",
          "ID",
          "STRING"] + RESERVED.values()

def t_REM(t):
    r"REM .+"
    pass

def t_ISRC(t):
    r'[A-Z]{2}[A-Za-z0-9]{3}[0-9]{7}'
    return t

def t_TIMESTAMP(t):
    r'[0-9]{1,3}:[0-9]{1,2}:[0-9]{1,2}'
    (m, s, f) = t.value.split(":")
    t.value = ((int(m) * 75 * 60) + (int(s) * 75) + (int(f)))
    return t

def t_MP3(t):
    r'MP3'
    return t

def t_MODE(t):
    r'MODE1/2048|MODE1/2352|MODE2/2336|MODE2/2352'
    return t

def t_CDI(t):
    r'CDI/2336|CDI/2352'
    return t

def t_NUMBER(t):
    r'[0-9]+'
    t.value = int(t.value)
    return t

def t_ID(t):
    r"[A-Z]+"
    if (t.value in RESERVED.keys()):
        t.type = RESERVED[t.value]
    else:
        t.type = "STRING"
    return t

def t_STRING(t):
    r'\".+?\"'
    t.value = t.value[1:-1]
    return t

t_ignore = " \r\t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    raise ValueError("illegal character %s" % (repr(t.value[0])))
