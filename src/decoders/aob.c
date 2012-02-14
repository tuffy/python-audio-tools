#include "aob.h"
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

#define SECTOR_SIZE 2048

PyObject*
DVDA_Title_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_DVDA_Title *self;

    self = (decoders_DVDA_Title *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
DVDA_Title_init(decoders_DVDA_Title *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"audio_ts",
                             "titleset",
                             "start_sector",
                             "end_sector",

                             "cdrom",
                             NULL};
    char* audio_ts;
    unsigned titleset;
    unsigned start_sector;
    unsigned end_sector;
    char* cdrom;

    self->sector_reader = NULL;
    self->packet_reader = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "sIII|s",
                                     kwlist,
                                     &audio_ts,
                                     &titleset,
                                     &start_sector,
                                     &end_sector,
                                     &cdrom))
        return -1;

    /*setup a sector reader according to AUDIO_TS and cdrom device*/
    if ((self->sector_reader = open_sector_reader(audio_ts,
                                                  titleset)) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, audio_ts);
        return -1;
    }

    /*setup a packet reader according to start and end sector
      this packet reader will be shared by all returned DVDA_Tracks*/
    self->packet_reader = open_packet_reader(self->sector_reader,
                                             start_sector, end_sector);

    return 0;
}

void
DVDA_Title_dealloc(decoders_DVDA_Title *self) {
    /*additional memory deallocation here*/

    if (self->packet_reader != NULL)
        close_packet_reader(self->packet_reader);

    if (self->sector_reader != NULL)
        close_sector_reader(self->sector_reader);

    self->ob_type->tp_free((PyObject*)self);
}

static PyObject*
DVDA_Title_track(decoders_DVDA_Title *self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Title_next(decoders_DVDA_Title *self, PyObject *args)
{
    /*FIXME - delete this method once no longer needed*/
    struct bs_buffer* packet = buf_new();

    if (!next_audio_packet(self->packet_reader, packet)) {
        PyObject* to_return = PyString_FromStringAndSize((char *)packet->buffer,
                                                         packet->buffer_size);
        buf_close(packet);
        return to_return;
    } else {
        buf_close(packet);
        PyErr_SetString(PyExc_IOError, "I/O error reading packet");
        return NULL;
    }
}

PyObject*
DVDA_Track_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    decoders_DVDA_Track *self;

    self = (decoders_DVDA_Track *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

void
DVDA_Track_dealloc(decoders_DVDA_Track *self) {
    /*additional memory deallocation here*/

    self->ob_type->tp_free((PyObject*)self);
}

int
DVDA_Track_init(decoders_DVDA_Track *self, PyObject *args, PyObject *kwds) {
    return 0;
}

static PyObject*
DVDA_Track_sample_rate(decoders_DVDA_Track *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Track_bits_per_sample(decoders_DVDA_Track *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Track_channels(decoders_DVDA_Track *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Track_channel_mask(decoders_DVDA_Track *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Track_read(decoders_DVDA_Track *self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Track_close(decoders_DVDA_Track *self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}


static char*
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


void
free_aob(DVDA_AOB* aob)
{
    fclose(aob->file);
    free(aob->path);
    free(aob);
}


static DVDA_Sector_Reader*
open_sector_reader(const char* audio_ts_path,
                   unsigned titleset_number)
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
                    return NULL;
                }
                aob->total_sectors = (unsigned)(aob_stat.st_size / SECTOR_SIZE);

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
        return reader;
    } else {
        /*couldn't find any matching AOB files for titleset*/
        close_sector_reader(reader);
        errno = ENOENT;
        return NULL;
    }
}

static void
close_sector_reader(DVDA_Sector_Reader* reader)
{
    reader->aobs->del(reader->aobs);
    free(reader);
}

static int
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

static void
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


static DVDA_Packet_Reader*
open_packet_reader(DVDA_Sector_Reader* sectors,
                   unsigned start_sector,
                   unsigned last_sector)
{
    DVDA_Packet_Reader* packets = malloc(sizeof(DVDA_Packet_Reader));
    assert(last_sector >= start_sector);

    packets->sectors = sectors;
    packets->reader = br_substream_new(BS_BIG_ENDIAN);

    packets->total_sectors = last_sector - start_sector;
    seek_sector(sectors, start_sector);
    return packets;
}

static int
next_audio_packet(DVDA_Packet_Reader* packets, struct bs_buffer* packet)
{
    if (packets->total_sectors) {
        BitstreamReader* reader = packets->reader;
        struct bs_buffer* buffer = reader->input.substream;
        buf_reset(buffer);
        if (!read_sector(packets->sectors, buffer)) {
            if (buffer->buffer_size == 0) {
                return 0;
            }

            if (!setjmp(*br_try(reader))) {
                unsigned sync_bytes;
                unsigned pad[6];
                unsigned PTS_high;
                unsigned PTS_mid;
                unsigned PTS_low;
                unsigned SCR_extension;
                unsigned bitrate;
                unsigned stuffing_count;
                int audio_packet_found = 0;

                /*read pack header*/
                reader->parse(reader,
                              "32u 2u 3u 1u 15u 1u 15u 1u 9u 1u 22u 2u 5p 3u",
                              &sync_bytes, &(pad[0]), &PTS_high,
                              &(pad[1]), &PTS_mid, &(pad[2]),
                              &PTS_low, &(pad[3]), &SCR_extension,
                              &(pad[4]), &bitrate, &(pad[5]),
                              &stuffing_count);
                if (sync_bytes != 0x000001BA) {
                    fprintf(stderr, "invalid packet sync bytes\n");
                    return 1;
                }

                if ((pad[0] != 1) || (pad[1] != 1) || (pad[2] != 1) ||
                    (pad[3] != 1) || (pad[4] != 1) || (pad[5] != 3)) {
                    fprintf(stderr, "invalid packet padding bits\n");
                    return 1;
                }

                for (; stuffing_count; stuffing_count--) {
                    reader->skip(reader, 8);
                }

                /*read packets from sector until sector is empty*/
                while (buffer->buffer_position < buffer->buffer_size) {
                    unsigned start_code;
                    unsigned stream_id;
                    unsigned packet_length;

                    reader->parse(reader, "24u 8u 16u",
                                  &start_code, &stream_id, &packet_length);

                    if (start_code != 0x000001) {
                        fprintf(stderr, "invalid packet start code\n");
                        return 1;
                    }

                    if (stream_id == 0xBD) {
                        /*audio packets are forwarded to packet*/
                        reader->read_bytes(reader,
                                           buf_extend(packet, packet_length),
                                           packet_length);
                        packet->buffer_size += packet_length;
                        audio_packet_found = 1;
                    } else {
                        /*other packets are ignored*/
                        reader->skip_bytes(reader, packet_length);
                    }
                }

                /*return success if an audio packet was read*/
                br_etry(reader);
                if (audio_packet_found) {
                    return 0;
                } else {
                    fprintf(stderr, "no audio packet found in sector\n");
                    return 1;
                }
            } else {
                /*error reading sector*/
                br_etry(reader);
                fprintf(stderr, "I/O error reading sector\n");
                return 1;
            }
        } else {
            /*error reading sector*/
            fprintf(stderr, "error reading sector\n");
            return 1;
        }
    } else {
        /*no more sectors, so return EOF*/
        return 0;
    }
}

static void
close_packet_reader(DVDA_Packet_Reader* packets)
{
    packets->reader->close(packets->reader);
    free(packets);
}
