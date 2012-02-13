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

typedef enum {OK, IO_ERROR, INVALID_AUDIO_TS, INVALID_ATS_XX_0,
              NO_AOBS_FOUND} status;

/*given a path to the AUDIO_TS directory
  and a filename to search for, in upper case,
  returns the full path to the file
  or NULL if the file is not found
  the path must be freed later once no longer needed*/
char*
find_audio_ts_file(const char* audio_ts_path,
                   const char* uppercase_file);

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

#define SECTOR_SIZE 2048

typedef struct {
    char* path;             /*the full path to the AOB file*/
    FILE* file;             /*opened FILE object to AOB file*/
    unsigned total_sectors; /*the total number of 2048 byte sectors*/
    unsigned start_sector;  /*the first sector in the AOB file*/
    unsigned end_sector;    /*the last sector in the AOB file, inclusive
                              for example:
                              AOB1->first_sector=0, last_sector=99
                              AOB2->first_sector=100, last_sector=199
                              etc.*/
} DVDA_AOB;

typedef struct {
    array_o* aobs;          /*all the AOB files on the disc, in order*/
    struct {
        unsigned sector;
        DVDA_AOB* aob;
    } current;
    unsigned end_sector;    /*the final sector on the entire disc*/
} DVDA_Sector_Reader;

typedef struct {
    array_o* titlesets;
    DVDA_Sector_Reader* reader;
} DVDA_Disc;

/*open the DVD-A disc at the given "AUDIO_TS" path
  returns a DVDA_Disc object and sets status to OK on success*/
DVDA_Disc*
open_dvda_disc(const char* audio_ts_path, status* status);

/*deallocates any sub-data allocated by open_dvda_disc*/
void
close_dvda_disc(DVDA_Disc* dvda);

DVDA_Titleset*
open_titleset(const char* audio_ts_path,
              unsigned titleset_number,
              status* status);

void
close_titleset(DVDA_Titleset* titleset);

DVDA_Title*
open_title(BitstreamReader* bs, unsigned table_offset, status* status);

void
close_title(DVDA_Title* title);

DVDA_Sector_Reader*
open_sector_reader(const char* audio_ts_path,
                   unsigned titleset_number,
                   status* status);

void
close_sector_reader(DVDA_Sector_Reader* reader);

int
read_sector(DVDA_Sector_Reader* reader,
            struct bs_buffer* sector);

void
seek_sector(DVDA_Sector_Reader* reader,
            unsigned sector);

void
free_aob(DVDA_AOB* aob);
