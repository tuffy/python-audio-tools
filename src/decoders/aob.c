#include "aob.h"
#include <string.h>
#include <math.h>
#include <dirent.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <sys/stat.h>
#include "../pcmconv.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

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
#define PTS_PER_SECOND 90000
#define PCM_CODEC_ID 0xA0
#define MLP_CODEC_ID 0xA1

#ifndef STANDALONE
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
#else
int
    DVDA_Title_init(decoders_DVDA_Title *self,
                    char* audio_ts,
                    unsigned titleset,
                    unsigned start_sector,
                    unsigned end_sector)
{
#endif
    char* cdrom = NULL;

    self->sector_reader = NULL;
    self->packet_reader = NULL;

    self->packet_data = buf_new();

    self->frames = buf_new();

    self->pcm_frames_remaining = 0;

    self->bits_per_sample = 0;
    self->sample_rate = 0;
    self->channel_count = 0;
    self->channel_mask = 0;

    self->mlp_decoder = open_mlp_decoder(self->frames);

    self->codec_framelist = array_ia_new();
    self->output_framelist = array_ia_new();

#ifndef STANDALONE
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "sIII|s",
                                     kwlist,
                                     &audio_ts,
                                     &titleset,
                                     &start_sector,
                                     &end_sector,
                                     &cdrom))
        return -1;
#endif

    /*setup a sector reader according to AUDIO_TS and cdrom device*/
    if ((self->sector_reader = open_sector_reader(audio_ts,
                                                  titleset,
                                                  cdrom)) == NULL) {
#ifndef STANDALONE
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, audio_ts);
#endif
        return -1;
    }

    /*setup a packet reader according to start and end sector
      this packet reader will be shared by all returned DVDA_Tracks*/
    self->packet_reader = open_packet_reader(self->sector_reader,
                                             start_sector,
                                             end_sector);

    return 0;
}

void
DVDA_Title_dealloc(decoders_DVDA_Title *self) {
    /*additional memory deallocation here*/

    close_mlp_decoder(self->mlp_decoder);

    if (self->packet_reader != NULL)
        close_packet_reader(self->packet_reader);

    if (self->sector_reader != NULL)
        close_sector_reader(self->sector_reader);

    buf_close(self->packet_data);

    buf_close(self->frames);

    self->codec_framelist->del(self->codec_framelist);
    self->output_framelist->del(self->output_framelist);

#ifndef STANDALONE
    Py_XDECREF(self->audiotools_pcm);

    self->ob_type->tp_free((PyObject*)self);
#endif
}

#ifndef STANDALONE
static PyObject*
DVDA_Title_sample_rate(decoders_DVDA_Title *self, void *closure)
{
    return Py_BuildValue("I", self->sample_rate);
}

static PyObject*
DVDA_Title_bits_per_sample(decoders_DVDA_Title *self, void *closure)
{
    return Py_BuildValue("I", self->bits_per_sample);
}

static PyObject*
DVDA_Title_channels(decoders_DVDA_Title *self, void *closure)
{
    return Py_BuildValue("I", self->channel_count);
}

static PyObject*
DVDA_Title_channel_mask(decoders_DVDA_Title *self, void *closure)
{
    return Py_BuildValue("I", self->channel_mask);
}

static PyObject*
DVDA_Title_pcm_frames(decoders_DVDA_Title *self, void *closure)
{
    return Py_BuildValue("I", self->pcm_frames_remaining);
}
static PyObject*
DVDA_Title_next_track(decoders_DVDA_Title *self, PyObject *args)
{
    unsigned PTS_ticks;
    DVDA_Packet next_packet;
    struct bs_buffer* packet_data = self->packet_data;
    unsigned i;

    if (!PyArg_ParseTuple(args, "I", &PTS_ticks))
        return NULL;

    /*ensure previous track has been exhausted, if any*/
    if (self->pcm_frames_remaining) {
        PyErr_SetString(PyExc_ValueError,
                        "current track has not been exhausted");
        return NULL;
    }

    /*read the next packet*/
    if (read_audio_packet(self->packet_reader,
                          &next_packet, packet_data)) {
        PyErr_SetString(PyExc_IOError,
                        "I/O error reading initialization packet");
        return NULL;
    }
#else
int
DVDA_Title_next_track(decoders_DVDA_Title *self, unsigned PTS_ticks)
{
    DVDA_Packet next_packet;
    struct bs_buffer* packet_data = self->packet_data;
    unsigned i;

    if (self->pcm_frames_remaining) {
        fprintf(stderr, "current track has not been exhausted\n");
        return 0;
    }

    if (read_audio_packet(self->packet_reader,
                          &next_packet, packet_data)) {
        fprintf(stderr, "I/O error reading initialization packet\n");
        return 0;
    }
#endif

    if (next_packet.codec_ID == PCM_CODEC_ID) {
        /*if the packet is PCM, initialize Title's stream attributes
          (bits-per-sample, sample rate, channel assignment/mask)
          with values taken from the first packet*/

        /*PCM stores stream attributes in the second padding block*/
        self->bits_per_sample =
            dvda_bits_per_sample(next_packet.PCM.group_1_bps);
        self->sample_rate =
            dvda_sample_rate(next_packet.PCM.group_1_rate);
        self->channel_assignment =
            next_packet.PCM.channel_assignment;
        self->channel_count =
            dvda_channel_count(next_packet.PCM.channel_assignment);
        self->channel_mask =
            dvda_channel_mask(next_packet.PCM.channel_assignment);

        self->frame_codec = PCM;

        init_aobpcm_decoder(&(self->pcm_decoder),
                            self->bits_per_sample,
                            self->channel_count);

        buf_extend(packet_data, self->frames);

    } else if (next_packet.codec_ID == MLP_CODEC_ID) {
        /*if the packet is MLP,
          check if the first frame starts with a major sync*/
        BitstreamReader* r = br_open_buffer(packet_data, BS_BIG_ENDIAN);
        r->mark(r);
        if (!setjmp(*br_try(r))) {
            unsigned sync_words;
            unsigned stream_type;

            r->parse(r, "32p 24u 8u", &sync_words, &stream_type);
            if ((sync_words == 0xF8726F) && (stream_type == 0xBB)) {
                /*if so, discard any unconsumed packet data
                  and initialize Title's stream attributes
                  with values taken from the major sync*/

                unsigned group_1_bps;
                unsigned group_2_bps;
                unsigned group_1_rate;
                unsigned group_2_rate;

                r->parse(r, "4u 4u 4u 4u 11p 5u 48p",
                         &group_1_bps, &group_2_bps,
                         &group_1_rate, &group_2_rate,
                         &(self->channel_assignment));

                self->bits_per_sample =
                    dvda_bits_per_sample(group_1_bps);
                self->sample_rate =
                    dvda_sample_rate(group_1_rate);
                self->channel_count =
                    dvda_channel_count(self->channel_assignment);
                self->channel_mask =
                    dvda_channel_mask(self->channel_assignment);
                self->frame_codec = MLP;
                self->mlp_decoder->major_sync_read = 0;

                r->rewind(r);
                r->unmark(r);
                br_etry(r);
                r->close(r);

                buf_reset(self->frames);
                buf_extend(packet_data, self->frames);
            } else {
                /*if not, append packet data to any unconsumed data
                  and leave Title's stream attributes as they were*/

                r->rewind(r);
                r->unmark(r);
                br_etry(r);
                r->close(r);

                buf_extend(packet_data, self->frames);
            }
        } else {
            /*if I/O error reading major sync,
              append packet data to any unconsumed data
              and leave Title's stream attributes as they were*/

            r->rewind(r);
            r->unmark(r);
            br_etry(r);
            r->close(r);

            buf_extend(packet_data, self->frames);
        }

    } else {
#ifndef STANDALONE
        PyErr_SetString(PyExc_ValueError, "unknown codec ID");
        return NULL;
#else
        return 0;
#endif
    }

    /*convert PTS ticks to PCM frames based on sample rate*/
    self->pcm_frames_remaining = (unsigned)round((double)PTS_ticks *
                                                 (double)self->sample_rate /
                                                 (double)PTS_PER_SECOND);

    /*initalize codec's framelist with the proper number of channels*/
    if (self->codec_framelist->len != self->channel_count) {
        self->codec_framelist->reset(self->codec_framelist);
        for (i = 0; i < self->channel_count; i++)
            self->codec_framelist->append(self->codec_framelist);
    }

#ifndef STANDALONE
    Py_INCREF(Py_None);
    return Py_None;
#else
    return 1;
#endif
}

#ifndef STANDALONE
static PyObject*
DVDA_Title_read(decoders_DVDA_Title *self, PyObject *args)
{
    DVDA_Packet next_packet;
    struct bs_buffer* packet_data = self->packet_data;
    mlp_status mlp_status;

    /*if track has been exhausted, return empty FrameList*/
    if (!self->pcm_frames_remaining) {
        return empty_FrameList(self->audiotools_pcm,
                               self->channel_count,
                               self->bits_per_sample);
    }

    /*otherwise, build FrameList from PCM or MLP packet data*/
    switch (self->frame_codec) {
    case PCM:
        /*if not enough bytes in buffer, read another packet*/
        while (aobpcm_packet_empty(&(self->pcm_decoder), self->frames)) {
            if (read_audio_packet(self->packet_reader,
                                  &next_packet, packet_data)) {
                PyErr_SetString(PyExc_IOError, "I/O reading PCM packet");
                return NULL;
            }

            /*FIXME - ensure packet has same format as PCM*/

            buf_extend(packet_data, self->frames);
        }

        /*FIXME - make this thread friendly*/
        read_aobpcm(&(self->pcm_decoder), self->frames, self->codec_framelist);
        break;
    case MLP:
        /*if not enough bytes in buffer, read another packet*/
        while (mlp_packet_empty(self->mlp_decoder)) {
            if (read_audio_packet(self->packet_reader,
                                  &next_packet, packet_data)) {
                PyErr_SetString(PyExc_IOError, "I/O reading MLP packet");
                return NULL;
            }

            /*FIXME - ensure packet has same format as MLP*/

            buf_extend(packet_data, self->frames);
        }

        /*FIXME - make this thread friendly*/
        if ((mlp_status = read_mlp_frames(self->mlp_decoder,
                                          self->codec_framelist)) != OK) {
            PyErr_SetString(mlp_python_exception(mlp_status),
                            mlp_python_exception_msg(mlp_status));
            return NULL;
        }
    }

    /*account for framelists larger than frames remaining*/
    self->codec_framelist->cross_split(self->codec_framelist,
                                       MIN(self->pcm_frames_remaining,
                                           self->codec_framelist->_[0]->len),
                                       self->output_framelist,
                                       self->codec_framelist);

    /*deduct output FrameList's PCM frames from remaining count*/
    self->pcm_frames_remaining -= self->output_framelist->_[0]->len;

    /*and return output FrameList*/
    return array_ia_to_FrameList(self->audiotools_pcm,
                                 self->output_framelist,
                                 self->bits_per_sample);
}

static PyObject*
DVDA_Title_close(decoders_DVDA_Title *self, PyObject *args)
{
    Py_INCREF(Py_None);
    return Py_None;
}
#endif


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
                   unsigned titleset_number,
                   const char* cdrom_device)
{
    DVDA_Sector_Reader* reader = malloc(sizeof(DVDA_Sector_Reader));
    unsigned i;

    reader->aobs = array_o_new(NULL, (ARRAY_FREE_FUNC)free_aob, NULL);
#ifdef HAS_UNPROT
    reader->cppm_decoder = NULL;
#endif

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
          set initial position to start of 0th sector*/

        reader->current.sector = 0;
        reader->current.aob = reader->aobs->_[0];

#ifdef HAS_UNPROT
        /*if cdrom device given, initialize CPPM decoder if possible*/
        if (cdrom_device != NULL) {
            char* dvdaudio_mkb = find_audio_ts_file(audio_ts_path,
                                                    "DVDAUDIO.MKB");
            if (dvdaudio_mkb != NULL) {
                reader->cppm_decoder =
                    malloc(sizeof(struct cppm_decoder));
                reader->cppm_decoder->media_type = 0;
                reader->cppm_decoder->media_key = 0;
                reader->cppm_decoder->id_album_media = 0;

                switch (cppm_init(reader->cppm_decoder,
                                  cdrom_device,
                                  dvdaudio_mkb)) {
                case -1: /* I/O error */
                    free(dvdaudio_mkb);
                    close_sector_reader(reader);
                    return NULL;
                case -2: /* unsupported protection type */
                    free(dvdaudio_mkb);
                    close_sector_reader(reader);
                    fprintf(stderr, "unsupported protection type\n");
                    errno = ENOENT;
                    return NULL;
                default: /* all okay */
                    free(dvdaudio_mkb);
                    break;
                }
            }
        }
#endif

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
#ifdef HAS_UNPROT
    if (reader->cppm_decoder != NULL) {
        free(reader->cppm_decoder);
    }
#endif
    reader->aobs->del(reader->aobs);
    free(reader);
}

static int
read_sector(DVDA_Sector_Reader* reader,
            struct bs_buffer* sector)
{
    if (reader->current.sector <= reader->end_sector) {
        DVDA_AOB* aob = reader->current.aob;
        static uint8_t sector_data[SECTOR_SIZE];
        const size_t bytes_read = fread(sector_data,
                                        sizeof(uint8_t),
                                        SECTOR_SIZE,
                                        aob->file);
        buf_write(sector, sector_data, (uint32_t)bytes_read);

        if (bytes_read == SECTOR_SIZE) {
            /*sector read successfully*/

#ifdef HAS_UNPROT
            /*unprotect if necessary*/
            if (reader->cppm_decoder != NULL) {
                cppm_decrypt(reader->cppm_decoder,
                             sector_data, 1, 1);
            }
#endif

            /*then move on to next sector*/
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
                      (sector - reader->current.aob->start_sector) *
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
                   unsigned end_sector)
{
    DVDA_Packet_Reader* packets = malloc(sizeof(DVDA_Packet_Reader));
    assert(end_sector >= start_sector);

    packets->start_sector = start_sector;
    packets->end_sector = end_sector;

    packets->sectors = sectors;
    packets->reader = br_substream_new(BS_BIG_ENDIAN);

    packets->total_sectors = end_sector - start_sector;
    seek_sector(sectors, start_sector);
    return packets;
}

static int
read_audio_packet(DVDA_Packet_Reader* packets,
                  DVDA_Packet* packet, struct bs_buffer* packet_data)
{
    if (packets->total_sectors) {
        BitstreamReader* reader = packets->reader;
        struct bs_buffer* buffer = reader->input.substream;
        buf_reset(buffer);
        if (!read_sector(packets->sectors, buffer)) {
            if (BUF_WINDOW_SIZE(buffer) == 0) {
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
                    br_etry(reader);
                    return 1;
                }

                if ((pad[0] != 1) || (pad[1] != 1) || (pad[2] != 1) ||
                    (pad[3] != 1) || (pad[4] != 1) || (pad[5] != 3)) {
                    br_etry(reader);
                    return 1;
                }

                for (; stuffing_count; stuffing_count--) {
                    reader->skip(reader, 8);
                }

                /*read packets from sector until sector is empty*/
                while (BUF_WINDOW_SIZE(buffer) > 0) {
                    unsigned start_code;
                    unsigned stream_id;
                    unsigned packet_length;

                    reader->parse(reader, "24u 8u 16u",
                                  &start_code, &stream_id, &packet_length);

                    if (start_code != 0x000001) {
                        br_etry(reader);
                        return 1;
                    }

                    if (stream_id == 0xBD) {
                        /*audio packets are forwarded to packet*/
                        unsigned pad1_size;
                        unsigned pad2_size;

                        reader->parse(reader, "16p 8u", &pad1_size);
                        reader->skip_bytes(reader, pad1_size);
                        reader->parse(reader, "8u 8u 8p 8u",
                                      &(packet->codec_ID),
                                      &(packet->CRC),
                                      &pad2_size);

                        if (packet->codec_ID == 0xA0) { /*PCM*/
                            reader->parse(reader,
                                          "16u 8p 4u 4u 4u 4u 8p 8u 8p 8u",
                                          &(packet->PCM.first_audio_frame),
                                          &(packet->PCM.group_1_bps),
                                          &(packet->PCM.group_2_bps),
                                          &(packet->PCM.group_1_rate),
                                          &(packet->PCM.group_2_rate),
                                          &(packet->PCM.channel_assignment),
                                          &(packet->PCM.CRC));
                            reader->skip_bytes(reader, pad2_size - 9);
                        } else {                        /*probably MLP*/
                            reader->skip_bytes(reader, pad2_size);
                        }

                        packet_length -= 3 + pad1_size + 4 + pad2_size;

                        buf_reset(packet_data);
                        while (packet_length) {
                            static uint8_t buffer[4096];
                            const unsigned to_read = MIN(packet_length, 4096);
                            reader->read_bytes(reader, buffer, to_read);
                            buf_write(packet_data, buffer, to_read);
                            packet_length -= to_read;
                        }

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
                    return 1;
                }
            } else {
                /*error reading sector*/
                br_etry(reader);
                return 1;
            }
        } else {
            /*error reading sector*/
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

unsigned
dvda_bits_per_sample(unsigned encoded)
{
    switch (encoded) {
    case 0:  return 16;
    case 1:  return 20;
    case 2:  return 24;
    default: return 0;
    }
}

unsigned
dvda_sample_rate(unsigned encoded)
{
    switch (encoded) {
    case 0:  return 48000;
    case 1:  return 96000;
    case 2:  return 192000;
    case 8:  return 44100;
    case 9:  return 88200;
    case 10: return 176400;
    default: return 0;
    }
}

unsigned
dvda_channel_count(unsigned encoded)
{
    switch (encoded) {
    case 0:  return 1;
    case 1:  return 2;
    case 2:  return 3;
    case 3:  return 4;
    case 4:  return 3;
    case 5:  return 4;
    case 6:  return 5;
    case 7:  return 3;
    case 8:  return 4;
    case 9:  return 5;
    case 10: return 4;
    case 11: return 5;
    case 12: return 6;
    case 13: return 4;
    case 14: return 5;
    case 15: return 4;
    case 16: return 5;
    case 17: return 6;
    case 18: return 5;
    case 19: return 5;
    case 20: return 6;
    default: return 0;
    }
}

unsigned
dvda_channel_mask(unsigned encoded)
{
    switch (encoded) {
    case 0:  return 0x4;
    case 1:  return 0x3;
    case 2:  return 0x103;
    case 3:  return 0x33;
    case 4:  return 0xB;
    case 5:  return 0x10B;
    case 6:  return 0x3B;
    case 7:  return 0x7;
    case 8:  return 0x107;
    case 9:  return 0x37;
    case 10: return 0xF;
    case 11: return 0x10F;
    case 12: return 0x3F;
    case 13: return 0x107;
    case 14: return 0x37;
    case 15: return 0xF;
    case 16: return 0x10F;
    case 17: return 0x3F;
    case 18: return 0x3B;
    case 19: return 0x37;
    case 20: return 0x3F;
    default: return 0;
    }
}

#ifdef STANDALONE
int main(int argc, char* argv[]) {
    decoders_DVDA_Title title;
    char* audio_ts;
    unsigned titleset;
    unsigned start_sector;
    unsigned end_sector;
    unsigned pts_ticks;

    DVDA_Packet next_packet;
    struct bs_buffer* packet_data;
    mlp_status mlp_status;

    unsigned output_data_size = 1;
    uint8_t* output_data;

    unsigned bytes_per_sample;
    FrameList_int_to_char_converter converter;

    if (argc < 6) {
        fprintf(stderr, "*** Usage: %s <AUDIO_TS> <titleset> "
                "<start sector> <end sector> <PTS ticks>\n", argv[0]);
        return 1;
    } else {
        audio_ts = argv[1];
        titleset = strtoul(argv[2], NULL, 10);
        start_sector = strtoul(argv[3], NULL, 10);
        end_sector = strtoul(argv[4], NULL, 10);
        pts_ticks = strtoul(argv[5], NULL, 10);
    }

    if (DVDA_Title_init(&title, audio_ts, titleset,
                        start_sector, end_sector)) {
        fprintf(stderr, "*** Error: unable to initialize DVDA title\n");
        return 1;
    } else {
        packet_data = title.packet_data;
        output_data = malloc(output_data_size);
    }

    if (!DVDA_Title_next_track(&title, pts_ticks)) {
        fprintf(stderr, "*** Error getting next track\n");
        goto error;
    } else {
        bytes_per_sample = title.bits_per_sample / 8;
        converter = FrameList_get_int_to_char_converter(
            title.bits_per_sample, 0, 1);
    }

    fprintf(stderr, "frames remaining: %u\n", title.pcm_frames_remaining);

    while (title.pcm_frames_remaining) {
        unsigned pcm_size;
        unsigned channel;
        unsigned frame;

        /*build FrameList from PCM or MLP packet data*/
        switch (title.frame_codec) {
        case PCM:
            /*if not enough bytes in buffer, read another packet*/
            while (aobpcm_packet_empty(&(title.pcm_decoder), title.frames)) {
                if (read_audio_packet(title.packet_reader,
                                      &next_packet, packet_data)) {
                    fprintf(stderr, "I/O Error reading PCM packet\n");
                    goto error;
                }

                /*FIXME - ensure packet has same format as PCM*/

                buf_extend(packet_data, title.frames);
            }

            /*FIXME - make this thread friendly*/
            read_aobpcm(&(title.pcm_decoder),
                        title.frames,
                        title.codec_framelist);
            break;
        case MLP:
            /*if not enough bytes in buffer, read another packet*/
            while (mlp_packet_empty(title.mlp_decoder)) {
                if (read_audio_packet(title.packet_reader,
                                      &next_packet, packet_data)) {
                    fprintf(stderr, "I/O Error reading MLP packet\n");
                    goto error;
                }

                /*FIXME - ensure packet has same format as MLP*/

                buf_extend(packet_data, title.frames);
            }

            /*FIXME - make this thread friendly*/
            if ((mlp_status = read_mlp_frames(title.mlp_decoder,
                                              title.codec_framelist)) != OK) {
                fprintf(stderr, "*** MLP Error: %s\n",
                        mlp_python_exception_msg(mlp_status));
                goto error;
            }
        }

        /*account for framelists larger than frames remaining*/
        title.codec_framelist->cross_split(
            title.codec_framelist,
            MIN(title.pcm_frames_remaining, title.codec_framelist->_[0]->len),
            title.output_framelist,
            title.codec_framelist);

        /*deduct output FrameList's PCM frames from remaining count*/
        title.pcm_frames_remaining -= title.output_framelist->_[0]->len;

        /*convert framelist data to string*/
        pcm_size = (bytes_per_sample *
                    title.output_framelist->len *
                    title.output_framelist->_[0]->len);

        if (pcm_size > output_data_size) {
            output_data_size = pcm_size;
            output_data = realloc(output_data, output_data_size);
        }
        for (channel = 0; channel < title.output_framelist->len; channel++) {
            const array_i* channel_data = title.output_framelist->_[channel];
            for (frame = 0; frame < channel_data->len; frame++) {
                converter(channel_data->_[frame],
                          output_data +
                          ((frame * title.output_framelist->len) + channel) *
                          bytes_per_sample);
            }
        }

        /*output framelist data to stdout*/
        fwrite(output_data, sizeof(unsigned char), pcm_size, stdout);
    }


    DVDA_Title_dealloc(&title);
    free(output_data);

    return 0;

error:
    DVDA_Title_dealloc(&title);
    free(output_data);

    return 0;
}
#endif
