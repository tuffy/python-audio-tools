#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "../bitstream.h"
#include "../array2.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2012  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

typedef enum {OK, IO_ERROR, INVALID_AUDIO_TS, INVALID_ATS_XX_0} status;

/*given a path to the AUDIO_TS directory
  and a filename to search for, in upper case,
  returns an open BitstreamReader to that file
  or NULL if not found or an error occurs opening the file*/
BitstreamReader*
open_audio_ts_file(const char* audio_ts_path,
                   const char* uppercase_file);

/*a DVD-Audio disc contains 1 or more titlesets
  (though we only care about the first audio titleset)

  the audio titleset contains 1 or more titles

  each title typically has 1 or more tracks in a consistent stream format
  (title1 = 2ch/128kHz, title2 = 5.1ch/96kHz, etc.)

  finally, each track contains 1 or more frames of MLP or AOBPCM audio
*/

typedef struct {
    uint32_t index_number;
    uint32_t initial_PTS_index;
    uint32_t PTS_length;
} DVDA_Track;

typedef struct {
    uint32_t first_sector;
    uint32_t last_sector;
} DVDA_Index;

typedef struct {
    uint32_t PTS_length;
    array_o* tracks;
    array_o* indexes;
} DVDA_Title;

typedef struct {
    array_o* titles;
} DVDA_Titleset;

typedef struct {
    array_o* titlesets;
} DVDA_Disc;

/*open the DVD-A disc at the given "AUDIO_TS" path
  returns OK on success*/
DVDA_Disc*
open_dvda_disc(const char* audio_ts_path, status* status);

/*deallocates any sub-data allocated by open_dvda_disc*/
void
close_dvda_disc(DVDA_Disc* dvda);

DVDA_Titleset*
open_titleset(const char* audio_ts_path, unsigned number, status* status);

void
close_titleset(DVDA_Titleset* titleset);

DVDA_Title*
open_title(BitstreamReader* bs, unsigned table_offset, status* status);

void
close_title(DVDA_Title* title);
