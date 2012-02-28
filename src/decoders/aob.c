#include "aob.h"
#include <dirent.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <sys/stat.h>
#include "../pcmconv.h"

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
#define PTS_PER_SECOND 90000

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
    char* cdrom = NULL;

    self->sector_reader = NULL;
    self->packet_reader = NULL;

    self->packet = malloc(sizeof(DVDA_Packet));
    self->packet->data = buf_new();

    self->mlp_frame_sync_read = 0;

    self->frames = buf_new();

    self->pcm_frames_remaining = 0;

    self->bits_per_sample = 0;
    self->sample_rate = 0;
    self->channel_count = 0;
    self->channel_mask = 0;

    self->mlp_decoder = open_mlp_decoder(self->frames);

    self->codec_framelist = array_ia_new();
    self->output_framelist = array_ia_new();
    self->wave_framelist = array_ia_new();

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

    /*setup a sector reader according to AUDIO_TS and cdrom device*/
    if ((self->sector_reader = open_sector_reader(audio_ts,
                                                  titleset,
                                                  cdrom)) == NULL) {
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

    close_mlp_decoder(self->mlp_decoder);

    if (self->packet_reader != NULL)
        close_packet_reader(self->packet_reader);

    if (self->sector_reader != NULL)
        close_sector_reader(self->sector_reader);

    buf_close(self->packet->data);
    free(self->packet);

    buf_close(self->frames);

    self->codec_framelist->del(self->codec_framelist);
    self->output_framelist->del(self->output_framelist);
    self->wave_framelist->del(self->wave_framelist);

    Py_XDECREF(self->audiotools_pcm);

    self->ob_type->tp_free((PyObject*)self);
}

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
DVDA_Title_next_track(decoders_DVDA_Title *self, PyObject *args)
{
    unsigned PTS_ticks;
    DVDA_Packet* packet = self->packet;
    unsigned i;

    if (!PyArg_ParseTuple(args, "I", &PTS_ticks))
        return NULL;

    /*ensure previous track has been exhausted, if any*/
    if (self->pcm_frames_remaining) {
        PyErr_SetString(PyExc_ValueError,
                        "current track has not been exhausted");
        return NULL;
    }

    if ((packet->data->buffer_size - packet->data->buffer_position) == 0) {
        /*initialize Title's stream attributes
          (bits-per-sample, sample rate, channel assignment/mask)
          with values taken from the first packet*/
        if (read_audio_packet(self->packet_reader, packet)) {
            PyErr_SetString(PyExc_IOError,
                            "I/O error reading initialization packet");
            return NULL;
        }

        self->channel_assignment = packet->PCM.channel_assignment;

        if (packet->codec_ID == 0xA0) {         /*PCM*/
            /*PCM stores stream attributes in the second padding block*/
            self->bits_per_sample =
                dvda_bits_per_sample(packet->PCM.group_1_bps);
            self->sample_rate =
                dvda_sample_rate(packet->PCM.group_1_rate);
            self->channel_count =
                dvda_channel_count(packet->PCM.channel_assignment);
            self->channel_mask =
                dvda_channel_mask(packet->PCM.channel_assignment);
            self->frame_codec = PCM;
            self->mlp_frame_sync_read = 0;

            init_aobpcm_decoder(&(self->pcm_decoder),
                                self->bits_per_sample,
                                self->channel_count);

        } else if (packet->codec_ID == 0xA1) {  /*MLP*/
            /*MLP stores stream attributes in its first frame*/
            BitstreamReader* r = br_open_buffer(packet->data, BS_BIG_ENDIAN);
            r->mark(r);
            if (!setjmp(*br_try(r))) {
                unsigned sync_words;
                unsigned stream_type;
                unsigned group_1_bps;
                unsigned group_2_bps;
                unsigned group_1_rate;
                unsigned group_2_rate;

                r->parse(r, "32p 24u 8u 4u 4u 4u 4u 11p 5u 48p",
                         &sync_words, &stream_type,
                         &group_1_bps, &group_2_bps,
                         &group_1_rate, &group_2_rate,
                         &(self->channel_assignment));

                if ((sync_words == 0xF8726F) && (stream_type == 0xBB)) {
                    self->bits_per_sample =
                        dvda_bits_per_sample(group_1_bps);
                    self->sample_rate =
                        dvda_sample_rate(group_1_rate);
                    self->channel_count =
                        dvda_channel_count(self->channel_assignment);
                    self->channel_mask =
                        dvda_channel_mask(self->channel_assignment);
                    self->frame_codec = MLP;
                    self->mlp_frame_sync_read = 1;

                    r->rewind(r);
                    r->unmark(r);
                    br_etry(r);
                    r->close(r);
                } else {
                    r->rewind(r);
                    br_etry(r);
                    r->unmark(r);
                    r->close(r);

                    if (!self->mlp_frame_sync_read) {
                        PyErr_SetString(PyExc_IOError,
                                        "Invalid MLP sync frame");
                        return NULL;
                    }
                }
            } else {
                /*I/O error reading MLP frame*/
                r->rewind(r);
                r->unmark(r);
                br_etry(r);
                r->close(r);
                PyErr_SetString(PyExc_IOError, "I/O error reading MLP frame");
                return NULL;
            }
        } else {
            PyErr_SetString(PyExc_ValueError, "unknown codec ID");
            return NULL;
        }

        /*once first packet is read for stream attributes,
          copy its payload to our frame store for later parsing*/
        buf_reset(self->frames);
        buf_append(packet->data, self->frames);
    }

    /*convert PTS ticks to PCM frames based on sample rate*/
    self->pcm_frames_remaining = (unsigned)ceil((double)PTS_ticks *
                                                (double)self->sample_rate /
                                                (double)PTS_PER_SECOND);

    /*initalize codec's framelist with the proper number of channels*/
    if (self->codec_framelist->len != self->channel_count) {
        self->codec_framelist->reset(self->codec_framelist);
        for (i = 0; i < self->channel_count; i++)
            self->codec_framelist->append(self->codec_framelist);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
DVDA_Title_read(decoders_DVDA_Title *self, PyObject *args)
{
    const static int CHANNEL_MAP[][6] = {
        /* 0x00 */ {  0, -1, -1, -1, -1, -1},
        /* 0x01 */ {  0,  1, -1, -1, -1, -1},
        /* 0x02 */ {  0,  1,  2, -1, -1, -1},
        /* 0x03 */ {  0,  1,  2,  3, -1, -1},
        /* 0x04 */ {  0,  1,  2, -1, -1, -1},
        /* 0x05 */ {  0,  1,  2,  3, -1, -1},
        /* 0x06 */ {  0,  1,  2,  3,  4, -1},
        /* 0x07 */ {  0,  1,  2, -1, -1, -1},
        /* 0x08 */ {  0,  1,  2,  3, -1, -1},
        /* 0x09 */ {  0,  1,  2,  3,  4, -1},
        /* 0x0A */ {  0,  1,  2,  3, -1, -1},
        /* 0x0B */ {  0,  1,  2,  3,  4, -1},
        /* 0x0C */ {  0,  1,  2,  3,  4,  5},
        /* 0x0D */ {  0,  1,  2,  3, -1, -1},
        /* 0x0E */ {  0,  1,  2,  3,  4, -1},
        /* 0x0F */ {  0,  1,  2,  3, -1, -1},
        /* 0x10 */ {  0,  1,  2,  3,  4, -1},
        /* 0x11 */ {  0,  1,  2,  3,  4,  5},
        /* 0x12 */ {  0,  1,  3,  4,  2, -1},
        /* 0x13 */ {  0,  1,  3,  4,  2, -1},
        /* 0x14 */ {  0,  1,  4,  5,  2,  3}
    };

    mlp_status mlp_status;
    unsigned c;

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
            if (read_audio_packet(self->packet_reader, self->packet)) {
                PyErr_SetString(PyExc_IOError, "I/O reading PCM packet");
                return NULL;
            }

            /*FIXME - ensure packet has same format as PCM*/

            buf_append(self->packet->data, self->frames);
        }

        /*FIXME - make this thread friendly*/
        read_aobpcm(&(self->pcm_decoder), self->frames, self->codec_framelist);
        break;
    case MLP:
        /*if not enough bytes in buffer, read another packet*/
        while (mlp_packet_empty(self->mlp_decoder)) {
            if (read_audio_packet(self->packet_reader, self->packet)) {
                PyErr_SetString(PyExc_IOError, "I/O reading MLP packet");
                return NULL;
            }

            /*FIXME - ensure packet has same format as MLP*/

            buf_append(self->packet->data, self->frames);
        }

        /*FIXME - make this thread friendly*/
        if ((mlp_status = read_mlp_frames(self->mlp_decoder,
                                          self->codec_framelist)) != OK) {
            PyErr_SetString(mlp_python_exception(mlp_status),
                            mlp_python_exception_msg(mlp_status));
            return NULL;
        }
    }

    if (self->codec_framelist->_[0]->len == 0) {
        fprintf(stderr, "warning: got empty framelist from codec %d\n",
                self->frame_codec);
    }

    /*account for framelists larger than frames remaining*/
    self->codec_framelist->cross_split(self->codec_framelist,
                                       MIN(self->pcm_frames_remaining,
                                           self->codec_framelist->_[0]->len),
                                       self->output_framelist,
                                       self->codec_framelist);

    /*deduct output FrameList's PCM frames from remaining count*/
    self->pcm_frames_remaining -= self->output_framelist->_[0]->len;

    /*reorder channels from PCM/MLP order to WAVE order*/
    self->wave_framelist->reset(self->wave_framelist);
    for (c = 0; c < self->output_framelist->len; c++) {
        self->wave_framelist->append(self->wave_framelist);
    }
    for (c = 0; c < self->output_framelist->len; c++) {
        array_i* mlp_channel =
            self->output_framelist->_[c];
        array_i* wav_channel =
            self->wave_framelist->_[CHANNEL_MAP[self->channel_assignment][c]];
        mlp_channel->swap(mlp_channel, wav_channel);
    }

    /*and return output FrameList*/
    return array_ia_to_FrameList(self->audiotools_pcm,
                                 self->wave_framelist,
                                 self->bits_per_sample);
}

static PyObject*
DVDA_Title_close(decoders_DVDA_Title *self, PyObject *args)
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
                   unsigned titleset_number,
                   const char* cdrom_device)
{
    DVDA_Sector_Reader* reader = malloc(sizeof(DVDA_Sector_Reader));
    unsigned i;

    reader->aobs = array_o_new(NULL, (ARRAY_FREE_FUNC)free_aob, NULL);
    reader->cppm_decoder = NULL;

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
    if (reader->cppm_decoder != NULL) {
        free(reader->cppm_decoder);
    }
    reader->aobs->del(reader->aobs);
    free(reader);
}

static int
read_sector(DVDA_Sector_Reader* reader,
            struct bs_buffer* sector)
{
    if (reader->current.sector <= reader->end_sector) {
        DVDA_AOB* aob = reader->current.aob;
        uint8_t* sector_data = buf_extend(sector, SECTOR_SIZE);
        size_t bytes_read = fread(sector_data, sizeof(uint8_t), SECTOR_SIZE,
                                  aob->file);

        if (bytes_read == SECTOR_SIZE) {
            /*sector read successfully*/

            /*unprotect if necessary*/
            if (reader->cppm_decoder != NULL) {
                cppm_decrypt(reader->cppm_decoder,
                             sector_data, 1, 1);
            }

            /*then move on to next sector*/

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
read_audio_packet(DVDA_Packet_Reader* packets, DVDA_Packet* packet)
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
                    /*FIXME - remove warnings*/
                    fprintf(stderr, "invalid packet sync bytes\n");
                    br_etry(reader);
                    return 1;
                }

                if ((pad[0] != 1) || (pad[1] != 1) || (pad[2] != 1) ||
                    (pad[3] != 1) || (pad[4] != 1) || (pad[5] != 3)) {
                    /*FIXME - remove warnings*/
                    fprintf(stderr, "invalid packet padding bits\n");
                    br_etry(reader);
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
                    uint8_t* packet_data;

                    reader->parse(reader, "24u 8u 16u",
                                  &start_code, &stream_id, &packet_length);

                    if (start_code != 0x000001) {
                        /*FIXME - remove warnings*/
                        fprintf(stderr, "invalid packet start code\n");
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

                        buf_reset(packet->data);
                        packet_data = buf_extend(packet->data, packet_length);
                        reader->read_bytes(reader, packet_data, packet_length);
                        packet->data->buffer_size += packet_length;

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
                    /*FIXME - remove warnings*/
                    fprintf(stderr, "no audio packet found in sector\n");
                    return 1;
                }
            } else {
                /*error reading sector*/
                br_etry(reader);
                /*FIXME - remove warnings*/
                fprintf(stderr, "I/O error reading sector\n");
                return 1;
            }
        } else {
            /*error reading sector*/
            /*FIXME - remove warnings*/
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
