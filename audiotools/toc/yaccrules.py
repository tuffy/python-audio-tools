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

from audiotools.toc.tokrules import tokens

def p_tocfile(t):
    '''tocfile : headers tracks'''

    from audiotools.toc import TOCFile

    args = dict(t[1])
    args["tracks"] = t[2]

    t[0] = TOCFile(**args)

def p_headers(t):
    '''headers : header
               | headers header'''

    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]

def p_header(t):
    '''header : CD_DA
              | CD_ROM
              | CD_ROM_XA
              | CATALOG STRING
              | header_cd_text'''

    if (t[1] in ["CD_DA", "CD_ROM", "CD_ROM_XA"]):
        t[0] = ("type", t[1])
    elif (t[1] == "CATALOG"):
        t[0] = ("catalog", t[2])
    else:
        t[0] = ("cd_text", t[1])

def p_header_cd_text(t):
    '''header_cd_text : CD_TEXT START_BLOCK language_map language_blocks END_BLOCK'''
    from audiotools.toc import CDText
    t[0] = CDText(languages=t[4], language_map=t[3])

def p_language_map(t):
    '''language_map : LANGUAGE_MAP START_BLOCK language_mappings END_BLOCK'''

    from audiotools.toc import CDTextLanguageMap
    t[0] = CDTextLanguageMap(t[3])

def p_language_mappings(t):
    '''language_mappings : language_mapping
                         | language_mappings language_mapping'''

    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] = [t[2]]

def p_language_mapping(t):
    '''language_mapping : NUMBER COLON language'''

    t[0] = (t[1], t[3])

def p_language(t):
    '''language : EN
                | NUMBER'''

    #FIXME - find list of supported languages
    t[0] = t[1]

def p_language_blocks(t):
    '''language_blocks : language_block
                       | language_blocks language_block'''

    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]

def p_language_block(t):
    '''language_block : LANGUAGE NUMBER START_BLOCK cd_text_items END_BLOCK'''

    from audiotools.toc import CDTextLanguage
    t[0] = CDTextLanguage(language_id=t[2], text_pairs=t[4])

def p_cd_text_items(t):
    '''cd_text_items : cd_text_item
                     | cd_text_items cd_text_item'''

    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]

def p_cd_text_item(t):
    '''cd_text_item : TITLE STRING
                    | PERFORMER STRING
                    | SONGWRITER STRING
                    | COMPOSER STRING
                    | ARRANGER STRING
                    | MESSAGE STRING
                    | DISC_ID STRING
                    | GENRE STRING
                    | TOC_INFO1 binary
                    | TOC_INFO2 binary
                    | UPC_EAN STRING
                    | ISRC STRING
                    | SIZE_INFO binary'''
    t[0] = (t[1], t[2])

def p_binary(t):
    '''binary : START_BLOCK bytes END_BLOCK'''
    t[0] = "".join(map(chr, t[2]))

def p_bytes(t):
    '''bytes : NUMBER
             | NUMBER COMMA bytes'''
    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = [t[1]] + t[3]

def p_tracks(t):
    '''tracks : track
              | tracks track'''

    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]

def p_track(t):
    '''track : TRACK track_mode track_flags
             | TRACK track_mode sub_channel_mode track_flags'''

    from audiotools.toc import TOCTrack

    if (len(t) == 4):
        t[0] = TOCTrack(mode=t[2], flags=t[3])
    else:
        t[0] = TOCTrack(mode=t[2], flags=t[4], sub_channel_mode=t[3])

def p_track_mode(t):
    '''track_mode : AUDIO
                  | MODE1
                  | MODE1_RAW
                  | MODE2
                  | MODE2_FORM1
                  | MODE2_FORM2
                  | MODE2_FORM_MIX
                  | MODE2_RAW'''
    t[0] = t[1]

def p_sub_channel_mode(t):
    '''sub_channel_mode : RW
                        | RW_RAW'''
    t[0] = t[1]

def p_track_flags(t):
    '''track_flags : track_flag
                   | track_flags track_flag'''

    if (len(t) == 2):
        t[0] = [t[1]]
    else:
        t[0] = t[1] + [t[2]]

def p_track_flag(t):
    '''track_flag : SILENCE length
                  | ZERO length
                  | DATAFILE STRING
                  | DATAFILE STRING length
                  | FIFO STRING length
                  | PREGAP TIMESTAMP'''
    #FIXME - handle remaining flags
    raise NotImplementedError()

def p_track_cd_text(t):
    "track_flag : CD_TEXT START_BLOCK language_blocks END_BLOCK"
    from audiotools.toc import CDText
    t[0] = CDText(languages=t[3])

def p_track_flag_copy(t):
    "track_flag : COPY"
    from audiotools.toc import TOCFlag_COPY
    t[0] = TOCFlag_COPY(True)

def p_track_flag_no_copy(t):
    "track_flag : NO COPY"
    from audiotools.toc import TOCFlag_COPY
    t[0] = TOCFlag_COPY(False)

def p_track_flag_pre_emphasis(t):
    "track_flag : PRE_EMPHASIS"
    from audiotools.toc import TOCFlag_PRE_EMPHASIS
    t[0] = TOCFlag_PRE_EMPHASIS(True)

def p_track_flag_no_pre_emphasis(t):
    "track_flag : NO PRE_EMPHASIS"
    from audiotools.toc import TOCFlag_PRE_EMPHASIS
    t[0] = TOCFlag_PRE_EMPHASIS(False)

def p_track_flag_two_channels(t):
    "track_flag : TWO_CHANNEL_AUDIO"
    from audiotools.toc import TOCFlag_CHANNELS
    t[0] = TOCFlag_CHANNELS(2)

def p_track_flag_four_channels(t):
    "track_flag : FOUR_CHANNEL_AUDIO"
    from audiotools.toc import TOCFlag_CHANNELS
    t[0] = TOCFlag_CHANNELS(4)

def p_track_flag_isrc(t):
    "track_flag : ISRC STRING"
    from audiotools.toc import TOCFlag_ISRC
    t[0] = TOCFlag_ISRC(t[2])

def p_track_file(t):
    '''track_flag : FILE STRING start
                  | AUDIOFILE STRING start
                  | FILE STRING start length
                  | AUDIOFILE STRING start length'''
    from audiotools.toc import TOCFlag_FILE
    if (len(t) == 4):
        t[0] = TOCFlag_FILE(type=t[1],
                            filename=t[2],
                            start=t[3])
    else:
        t[0] = TOCFlag_FILE(type=t[1],
                            filename=t[2],
                            start=t[3],
                            length=t[4])

def p_track_start(t):
    '''track_flag : START
                  | START TIMESTAMP'''
    from audiotools.toc import TOCFlag_START
    if (len(t) == 2):
        t[0] = TOCFlag_START()
    else:
        from fractions import Fraction
        t[0] = TOCFlag_START(Fraction(t[2], 75))

def p_track_index(t):
    "track_flag : INDEX TIMESTAMP"
    from audiotools.toc import TOCFlag_INDEX
    from fractions import Fraction
    t[0] = TOCFlag_INDEX(Fraction(t[2], 75))

def p_start_number(t):
    "start : NUMBER"

    from fractions import Fraction
    t[0] = Fraction(t[1], 44100)

def p_start_timestamp(t):
    "start : TIMESTAMP"

    from fractions import Fraction
    t[0] = Fraction(t[1], 75)

def p_length_number(t):
    "length : NUMBER"

    from fractions import Fraction
    t[0] = Fraction(t[1], 44100)

def p_length_timestamp(t):
    "length : TIMESTAMP"

    from fractions import Fraction
    t[0] = Fraction(t[1], 75)

def p_error(t):
    raise ValueError("Syntax error at line %d" % (t.lexer.lineno))
