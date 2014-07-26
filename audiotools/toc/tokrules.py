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
            "CD_DA":"CD_DA",
            "CD_ROM":"CD_ROM",
            "CD_ROM_XA":"CD_ROM_XA",
            "CD_TEXT":"CD_TEXT",
            "TRACK":"TRACK",
            "AUDIO":"AUDIO",
            "MODE1":"MODE1",
            "MODE1_RAW":"MODE1_RAW",
            "MODE2":"MODE2",
            "MODE2_FORM1":"MODE2_FORM1",
            "MODE2_FORM2":"MODE2_FORM2",
            "MODE2_FORM_MIX":"MODE2_FORM_MIX",
            "MODE2_RAW":"MODE2_RAW",
            "RW":"RW",
            "RW_RAW":"RW_RAW",
            "NO":"NO",
            "COPY":"COPY",
            "PRE_EMPHASIS":"PRE_EMPHASIS",
            "TWO_CHANNEL_AUDIO":"TWO_CHANNEL_AUDIO",
            "FOUR_CHANNEL_AUDIO":"FOUR_CHANNEL_AUDIO",
            "ISRC":"ISRC",
            "SILENCE":"SILENCE",
            "ZERO":"ZERO",
            "FILE":"FILE",
            "AUDIOFILE":"AUDIOFILE",
            "DATAFILE":"DATAFILE",
            "FIFO":"FIFO",
            "START":"START",
            "PREGAP":"PREGAP",
            "INDEX":"INDEX",
            "LANGUAGE_MAP":"LANGUAGE_MAP",
            "LANGUAGE":"LANGUAGE",
            "TITLE":"TITLE",
            "PERFORMER":"PERFORMER",
            "SONGWRITER":"SONGWRITER",
            "COMPOSER":"COMPOSER",
            "ARRANGER":"ARRANGER",
            "MESSAGE":"MESSAGE",
            "DISC_ID":"DISC_ID",
            "GENRE":"GENRE",
            "TOC_INFO1":"TOC_INFO1",
            "TOC_INFO2":"TOC_INFO2",
            "UPC_EAN":"UPC_EAN",
            "SIZE_INFO":"SIZE_INFO",

            "EN":"EN"}

tokens = ["COMMENT",
          "START_BLOCK",
          "END_BLOCK",
          "COLON",
          "COMMA",
          "TIMESTAMP",
          "NUMBER",
          "ID",
          "STRING"] + RESERVED.values()

def t_COMMENT(t):
    r'//.*'
    pass

t_START_BLOCK = r'{'
t_END_BLOCK = r'}'
t_COLON = r':'
t_COMMA = r','

def t_ID(t):
    r'[A-Z][A-Z0-9_]*'
    if (t.value in RESERVED.keys()):
        t.type = RESERVED[t.value]
    return t

def t_STRING(t):
    r'\"(\\.|[^"])*\"'
    from re import sub
    t.value = sub(r'\\.', lambda s: s.group(0)[1:], t.value[1:-1])
    return t

def t_TIMESTAMP(t):
    r'[0-9]{1,3}:[0-9]{1,2}:[0-9]{1,2}'
    (m, s, f) = t.value.split(":")
    t.value = ((int(m) * 75 * 60) + (int(s) * 75) + (int(f)))
    return t

def t_NUMBER(t):
    r'[0-9]+'
    t.value = int(t.value)
    return t

t_ignore = " \r\t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    raise ValueError("illegal character %s" % (repr(t.value[0])))
