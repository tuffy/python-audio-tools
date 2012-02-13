#include "dvda.h"
#include <dirent.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <sys/stat.h>

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
    dvda->reader = NULL;

    /*open AUDIO_TS.IFO, verify it and get a titleset count*/
    bs = open_audio_ts_file(audio_ts_path, "AUDIO_TS.IFO");
    if (bs != NULL) {
        uint8_t identifier[12];

        if (!setjmp(*br_try(bs))) {
            unsigned titleset_count;
            DVDA_Titleset* titleset;

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

            /*read information for the first titleset*/
            if ((titleset = open_titleset(audio_ts_path, 1, status)) != NULL)
                dvda->titlesets->append(dvda->titlesets, titleset);
            else {
                close_dvda_disc(dvda);
                return NULL;
            }

            /*open AOB reader*/
            if ((dvda->reader = open_sector_reader(audio_ts_path,
                                                   1,
                                                   status)) != NULL) {
                return dvda;
            } else {
                close_dvda_disc(dvda);
                return NULL;
            }
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
    if (dvda->reader != NULL) {
        close_sector_reader(dvda->reader);
    }
    free(dvda);
}

void
close_titleset(DVDA_Titleset* titleset)
{
    titleset->titles->del(titleset->titles);
    free(titleset);
}

DVDA_Titleset*
open_titleset(const char* audio_ts_path,
              unsigned titleset_number,
              status* status)
{
    DVDA_Titleset* titleset = malloc(sizeof(DVDA_Titleset));
    char ATS_XX_0_name[13];
    BitstreamReader* bs;

    titleset->titles = array_o_new(NULL, (ARRAY_FREE_FUNC)close_title, NULL);

    sprintf(ATS_XX_0_name, "ATS_%2.2d_0.IFO", titleset_number);

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

DVDA_Sector_Reader*
open_sector_reader(const char* audio_ts_path,
                   unsigned titleset_number,
                   status* status)
{
    DVDA_Sector_Reader* reader = malloc(sizeof(DVDA_Sector_Reader));
    unsigned i;

    reader->aobs = array_o_new(NULL, (ARRAY_FREE_FUNC)free_aob, NULL);

    for (i = 1; i <= 9; i++) {
        char aob[13];
        char* path;

        snprintf(aob, 13, "ATS_%2.2d_%d.AOB", titleset_number, i);

        if ((path = find_audio_ts_file(audio_ts_path, aob)) != NULL) {
            struct stat aob_stat;
            if (!stat(path, &aob_stat)) {
                DVDA_AOB* aob = malloc(sizeof(DVDA_AOB));
                aob->path = path;
                if ((aob->file = fopen(aob->path, "rb")) == NULL) {
                    /*error opening AOB for reading*/
                    free(aob);
                    close_sector_reader(reader);
                    *status = IO_ERROR;
                    return NULL;
                }
                aob->total_sectors = aob_stat.st_size / SECTOR_SIZE;

                /*set AOBs first_sector and last_sector
                  relative to the previous AOB, if any*/
                if (reader->aobs->len) {
                    DVDA_AOB* last_aob = reader->aobs->_[reader->aobs->len - 1];
                    aob->start_sector = last_aob->end_sector + 1;
                } else {
                    aob->start_sector = 0;
                }
                aob->end_sector = aob->start_sector + (aob->total_sectors - 1);
                reader->end_sector = aob->end_sector;

                reader->aobs->append(reader->aobs, aob);
            } else {
                /*error getting stat of AOB,
                  free memory and return error*/
                close_sector_reader(reader);
                *status = IO_ERROR;
                return NULL;
            }
        } else {
            /*AOB not found, so exit loop*/
            break;
        }
    }

    if (reader->aobs->len) {
        /*ran out of AOBs,
          set initial position to start of 0th sector
          and return success if any AOBs are found*/

        reader->current.sector = 0;
        reader->current.aob = reader->aobs->_[0];
        *status = OK;
        return reader;
    } else {
        close_sector_reader(reader);
        *status = NO_AOBS_FOUND;
        return NULL;
    }

}

void
close_sector_reader(DVDA_Sector_Reader* reader)
{
    reader->aobs->del(reader->aobs);
    free(reader);
}

int
read_sector(DVDA_Sector_Reader* reader,
            struct bs_buffer* sector)
{
    if (reader->current.sector <= reader->end_sector) {
        DVDA_AOB* aob = reader->current.aob;
        size_t bytes_read = fread(buf_extend(sector, SECTOR_SIZE),
                                  sizeof(uint8_t), SECTOR_SIZE,
                                  aob->file);
        if (bytes_read == SECTOR_SIZE) {
            /*sector read successfully, so move on to next sector*/

            sector->buffer_size += SECTOR_SIZE;
            reader->current.sector++;
            if (reader->current.sector > aob->end_sector) {
                /*move on to next AOB in set, if any*/
                if (reader->current.sector <= reader->end_sector) {
                    seek_sector(reader, reader->current.sector);
                }
            }
            return 0;
        } else {
            /*I/O error reading sector*/
            return 1;
        }
    } else {
        /*no more sectors to read, so return EOF*/
        return 0;
    }
}

void
seek_sector(DVDA_Sector_Reader* reader,
            unsigned sector)
{
    if (sector <= reader->end_sector) {
        unsigned i;
        for (i = 0; i < reader->aobs->len; i++) {
            reader->current.aob = reader->aobs->_[i];
            if ((reader->current.aob->start_sector <= sector) &&
                (sector <= reader->current.aob->end_sector)) {
                fseek(reader->current.aob->file,
                      (sector - reader->current.aob->start_sector) /
                      SECTOR_SIZE, SEEK_SET);
                break;
            }
        }
        reader->current.sector = sector;
    } else {
        /*sector outside AOBs*/
        reader->current.sector = sector;
    }
}

void
free_aob(DVDA_AOB* aob)
{
    fclose(aob->file);
    free(aob->path);
    free(aob);
}

char*
find_audio_ts_file(const char* audio_ts_path,
                   const char* uppercase_file)
{
    DIR* dir = opendir(audio_ts_path);

    if (dir != NULL) {
        struct dirent* dirent;
        for (dirent = readdir(dir); dirent != NULL; dirent = readdir(dir)) {
            /*convert directory entry to upper-case*/
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
                  and return it*/

                const size_t full_path_len = (strlen(audio_ts_path) +
                                              1 + /*path separator*/
                                              dirent_namelen);
                char* full_path = malloc(full_path_len + 1);

                snprintf(full_path, full_path_len + 1,
                         "%s/%s", audio_ts_path, dirent->d_name);

                free(uppercase_filename);
                closedir(dir);
                return full_path;
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
        return NULL;
    }
}

BitstreamReader*
open_audio_ts_file(const char* audio_ts_path,
                   const char* uppercase_file)
{
    char* full_path;

    if ((full_path = find_audio_ts_file(audio_ts_path,
                                        uppercase_file)) != NULL) {
        FILE* file = fopen(full_path, "rb");
        if (file != NULL) {
            free(full_path);
            return br_open(file, BS_BIG_ENDIAN);
        } else {
            free(full_path);
            return NULL;
        }
    } else {
        errno = ENOENT;
        return NULL;
    }
}

#ifdef STANDALONE
int main(int argc, char* argv[])
{
    DVDA_Disc* dvda;
    FILE* output = fopen(argv[2], "wb");
    struct bs_buffer* buffer = buf_new();
    status status;

    if ((dvda = open_dvda_disc(argv[1], &status)) != NULL) {
        buf_reset(buffer);
        while (!read_sector(dvda->reader, buffer)) {

            assert((buffer->buffer_size == SECTOR_SIZE) ||
                   (buffer->buffer_size == 0));

            if (buffer->buffer_size) {
                fwrite(buffer->buffer,
                       sizeof(uint8_t),
                       buffer->buffer_size,
                       output);
            } else {
                /*EOF*/
                break;
            }
            buf_reset(buffer);
        }
        fclose(output);
        buf_close(buffer);
        close_dvda_disc(dvda);
        return 0;
    } else {
        fclose(output);
        buf_close(buffer);
        fprintf(stderr, "error opening DVD-A\n");
        return 1;
    }
}

/* int main(int argc, char* argv[]) */
/* { */
/*     status status; */
/*     DVDA_Disc* dvda; */

/*     if ((dvda = open_dvda_disc(argv[1], &status)) != NULL) { */
/*         unsigned i; */
/*         unsigned j; */
/*         unsigned k; */

/*         printf("Disc opened successfully\n"); */

/*         for (i = 0; i < dvda->titlesets->len; i++) { */
/*             DVDA_Titleset* titleset = dvda->titlesets->_[i]; */
/*             for (j = 0; j < titleset->titles->len; j++) { */
/*                 DVDA_Title* title = titleset->titles->_[j]; */
/*                 printf("Title : %u  Length : %u\n", j + 1, title->PTS_length); */
/*                 for (k = 0; k < title->tracks->len; k++) { */
/*                     DVDA_Track* track = title->tracks->_[k]; */
/*                     printf("  Track : %u  index : %u  PTS index : %u  " */
/*                            "PTS length : %u\n", */
/*                            k + 1, */
/*                            track->index_number, */
/*                            track->initial_PTS_index, */
/*                            track->PTS_length); */
/*                 } */
/*                 for (k = 0; k < title->indexes->len; k++) { */
/*                     DVDA_Index* index = title->indexes->_[k]; */
/*                     printf("  Index : %u  first : %d  last : %d\n", */
/*                            k + 1, */
/*                            index->first_sector, */
/*                            index->last_sector); */
/*                 } */
/*             } */
/*         } */

/*         for (i = 0; i < dvda->reader->aobs->len; i++) { */
/*             DVDA_AOB* aob = dvda->reader->aobs->_[i]; */
/*             printf("  AOB : %s %u  %u - %u\n", */
/*                    aob->path, aob->total_sectors, */
/*                    aob->start_sector, aob->end_sector); */
/*         } */

/*         close_dvda_disc(dvda); */
/*     } else { */
/*         printf("Error status : %d\n", status); */
/*         /\* printf("Error : %s\n", strerror(errno)); *\/ */
/*     } */

/*     return 0; */
/* } */
#endif
