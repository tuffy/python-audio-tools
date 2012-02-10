#include "dvda.h"
#include <dirent.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>

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

DVDA_Disc*
open_dvda_disc(const char* audio_ts_path, status* status)
{
    BitstreamReader* bs;
    DVDA_Disc* dvda = malloc(sizeof(DVDA_Disc));

    dvda->titlesets = array_o_new(NULL,
                                  (ARRAY_FREE_FUNC)close_titleset,
                                  NULL);

    /*open AUDIO_TS.IFO, verify it and get a titleset count*/
    bs = open_audio_ts_file(audio_ts_path, "AUDIO_TS.IFO");
    if (bs != NULL) {
        uint8_t identifier[12];

        if (!setjmp(*br_try(bs))) {
            unsigned titleset_count;
            unsigned i;

            bs->read_bytes(bs, identifier, 12);

            if (memcmp(identifier, "DVDAUDIO-AMG", 12)) {
                br_etry(bs);
                bs->close(bs);
                *status = INVALID_AUDIO_TS;
                close_dvda_disc(dvda);
                return NULL;
            }

            bs->parse(bs,
                      "32p 96p 32p 8p 8p 32p 16p 16p 8p 40p 32p 80p 8p 8u 32P",
                      &titleset_count);

            br_etry(bs);
            bs->close(bs);

            for (i = 0; i < titleset_count; i++) {
                DVDA_Titleset* titleset = open_titleset(audio_ts_path,
                                                        i,
                                                        status);
                if (titleset != NULL)
                    dvda->titlesets->append(dvda->titlesets, titleset);
                else {
                    close_dvda_disc(dvda);
                    return NULL;
                }
            }

            *status = OK;
            return dvda;
        } else {
            br_etry(bs);
            bs->close(bs);
            *status = IO_ERROR;
            close_dvda_disc(dvda);
            return NULL;
        }
    } else {
        *status = IO_ERROR;
        close_dvda_disc(dvda);
        return NULL;
    }
}

void
close_dvda_disc(DVDA_Disc* dvda)
{
    dvda->titlesets->del(dvda->titlesets);
    free(dvda);
}

void
close_titleset(DVDA_Titleset* titleset)
{
    titleset->titles->del(titleset->titles);
    free(titleset);
}

DVDA_Titleset*
open_titleset(const char* audio_ts_path, unsigned number, status* status)
{
    DVDA_Titleset* titleset = malloc(sizeof(DVDA_Titleset));
    char ATS_XX_0_name[13];
    BitstreamReader* bs;

    titleset->titles = array_o_new(NULL, (ARRAY_FREE_FUNC)close_title, NULL);

    sprintf(ATS_XX_0_name, "ATS_%2.2d_0.IFO", number + 1);

    /*open ATS_XX_0.IFO*/
    if ((bs = open_audio_ts_file(audio_ts_path, ATS_XX_0_name)) == NULL) {
        *status = IO_ERROR;
        close_titleset(titleset);
        return NULL;
    }

    if (!setjmp(*br_try(bs))) {
        char identifier[12];
        unsigned last_byte_address;
        unsigned title_count;
        unsigned i;

        /*verify ATS_XX_0.IFO file*/
        bs->parse(bs, "12b 2036P 16u 16p 32u",
                  identifier,
                  &title_count,
                  &last_byte_address);

        if (memcmp(identifier, "DVDAUDIO-ATS", 12)) {
            *status = INVALID_ATS_XX_0;
            close_titleset(titleset);
            return NULL;
        }

        /*read title table for each title in file*/
        for (i = 0; i < title_count; i++) {
            unsigned title_number;
            unsigned title_table_offset;
            DVDA_Title* title;

            bs->parse(bs, "8u 24p 32u", &title_number, &title_table_offset);
            bs->mark(bs);
            fseek(bs->input.file, title_table_offset + 0x800, SEEK_SET);
            if ((title = open_title(bs,
                                    title_table_offset + 0x800,
                                    status)) == NULL) {
                br_etry(bs);
                bs->unmark(bs);
                bs->close(bs);
                return NULL;
            } else {
                titleset->titles->append(titleset->titles, title);
                bs->rewind(bs);
                bs->unmark(bs);
            }
        }

        br_etry(bs);
        bs->close(bs);
        *status = OK;
        return titleset;
    } else {
        br_etry(bs);
        bs->close(bs);
        *status = IO_ERROR;
        close_titleset(titleset);
        return NULL;
    }
}

DVDA_Title*
open_title(BitstreamReader* bs, unsigned table_offset, status* status)
{
    DVDA_Title* title = malloc(sizeof(DVDA_Title));
    unsigned track_count;
    unsigned index_count;
    unsigned sector_pointers_offset;
    unsigned i;

    title->tracks = array_o_new(NULL, free, NULL);
    title->indexes = array_o_new(NULL, free, NULL);

    if (!setjmp(*br_try(bs))) {
        bs->parse(bs, "16p 8u 8u 32u 32p 16u 16p",
                  &track_count,
                  &index_count,
                  &(title->PTS_length),
                  &sector_pointers_offset);

        for (i = 0; i < track_count; i++) {
            DVDA_Track* track = malloc(sizeof(DVDA_Track));

            if (!setjmp(*br_try(bs))) {
                bs->parse(bs, "32p 8u 8p 32u 32u 48p",
                          &(track->index_number),
                          &(track->initial_PTS_index),
                          &(track->PTS_length));
                title->tracks->append(title->tracks, track);
                br_etry(bs);
            } else {
                free(track);
                br_etry(bs);
                br_abort(bs);
            }
        }

        fseek(bs->input.file,
              table_offset + sector_pointers_offset,
              SEEK_SET);
        for (i = 0; i < index_count; i++) {
            DVDA_Index* index = malloc(sizeof(DVDA_Index));
            uint32_t index_id;

            if (!setjmp(*br_try(bs))) {
                bs->parse(bs, "32u 32u 32u",
                          &index_id,
                          &(index->first_sector),
                          &(index->last_sector));

                if (index_id == 0x01000000) {
                    title->indexes->append(title->indexes, index);
                    br_etry(bs);
                } else {
                    free(index);
                    br_etry(bs);
                    br_etry(bs);
                    close_title(title);
                    *status = INVALID_ATS_XX_0;
                    return NULL;
                }
            } else {
                free(index);
                br_etry(bs);
                br_abort(bs);
            }
        }

        br_etry(bs);

        return title;
    } else {
        close_title(title);
        *status = IO_ERROR;
        return NULL;
    }

}

void
close_title(DVDA_Title* title)
{
    title->tracks->del(title->tracks);
    title->indexes->del(title->indexes);
    free(title);
}

BitstreamReader*
open_audio_ts_file(const char* audio_ts_path,
                   const char* uppercase_file)
{
    DIR* dir = opendir(audio_ts_path);

    if (dir != NULL) {
        struct dirent* dirent;
        for (dirent = readdir(dir); dirent != NULL; dirent = readdir(dir)) {
            /*convert directory entry to upper-case
              in order to make implementing match() easier*/
            const size_t dirent_namelen = strlen(dirent->d_name);
            char* uppercase_filename = malloc(dirent_namelen + 1);
            size_t i;

            for (i = 0; i < dirent_namelen; i++) {
                uppercase_filename[i] = (char)toupper(dirent->d_name[i]);
            }
            uppercase_filename[i] = '\0';

            if (!strcmp(uppercase_filename, uppercase_file)) {
                /*if the filename matches,
                  join audio_ts path and name into a single path
                  and try to open it*/

                const size_t full_path_len = (strlen(audio_ts_path) +
                                              1 + /*path separator*/
                                              dirent_namelen);
                char* full_path = malloc(full_path_len + 1);
                FILE* opened_file;

                snprintf(full_path, full_path_len + 1,
                         "%s/%s", audio_ts_path, dirent->d_name);

                free(uppercase_filename);
                closedir(dir);

                opened_file = fopen(full_path, "rb");

                free(full_path);

                return br_open(opened_file, BS_BIG_ENDIAN);
            } else {
                /*filename doesn't match, so try next one*/
                free(uppercase_filename);
            }
        }

        /*gone through entire directory without a match*/
        errno = ENOENT;
        closedir(dir);
        return NULL;
    } else {
        errno = ENOENT;
        return NULL;
    }
}

#ifdef STANDALONE
int main(int argc, char* argv[])
{
    status status;
    DVDA_Disc* dvda;

    if ((dvda = open_dvda_disc(argv[1], &status)) != NULL) {
        unsigned i;
        unsigned j;
        unsigned k;

        printf("Disc opened successfully\n");

        for (i = 0; i < dvda->titlesets->len; i++) {
            DVDA_Titleset* titleset = dvda->titlesets->_[i];
            for (j = 0; j < titleset->titles->len; j++) {
                DVDA_Title* title = titleset->titles->_[j];
                printf("Title : %u  Length : %u\n", j + 1, title->PTS_length);
                for (k = 0; k < title->tracks->len; k++) {
                    DVDA_Track* track = title->tracks->_[k];
                    printf("  Track : %u  index : %u  PTS index : %u  "
                           "PTS length : %u\n",
                           k + 1,
                           track->index_number,
                           track->initial_PTS_index,
                           track->PTS_length);
                }
            }
        }

        close_dvda_disc(dvda);
    } else {
        printf("Error status : %d\n", status);
        /* printf("Error : %s\n", strerror(errno)); */
    }

    return 0;
}
#endif
