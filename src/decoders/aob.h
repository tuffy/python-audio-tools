#ifndef STANDALONE
#include <Python.h>
#endif
#include "../array.h"
#include "../bitstream.h"
#include "aobpcm.h"
#include "mlp.h"
#ifdef HAS_UNPROT
#include "cppm.h"
#endif

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

struct DVDA_Sector_Reader_s;
struct DVDA_Packet_Reader_s;
struct DVDA_Packet_s;

typedef enum {PCM, MLP} DVDA_Codec;

/*a title in a given titleset
  this generates DVDA_Track objects which are actual decoders*/
typedef struct {
#ifndef STANDALONE
    PyObject_HEAD
#endif

    /*an AOB sector reader*/
    struct DVDA_Sector_Reader_s* sector_reader;

    /*a reader which extracts packets from sectors*/
    struct DVDA_Packet_Reader_s* packet_reader;

    struct DVDA_Packet_s* packet;
    struct bs_buffer* packet_data;

    /*PCM or MLP frame data, aligned on a frame start*/
    DVDA_Codec frame_codec;
    struct bs_buffer* frames;

    /*total PCM frames remaining in the current track*/
    unsigned pcm_frames_remaining;
    unsigned channel_assignment;

    /*PCMReader attributes for the current track*/
    unsigned bits_per_sample;
    unsigned sample_rate;
    unsigned channel_count;
    unsigned channel_mask;

    AOBPCMDecoder pcm_decoder;
    MLPDecoder* mlp_decoder;

    /*a FrameList to be appended to by the PCM or MLP decoder*/
    array_ia* codec_framelist;

    /*a FrameList to be returned by calls to read()*/
    array_ia* output_framelist;

#ifndef STANDALONE
    /*a FrameList generator*/
    PyObject* audiotools_pcm;
#endif
} decoders_DVDA_Title;

void
DVDA_Title_dealloc(decoders_DVDA_Title *self);

#ifndef STANDALONE
static PyObject*
DVDA_Title_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
DVDA_Title_init(decoders_DVDA_Title *self, PyObject *args, PyObject *kwds);

static PyObject*
DVDA_Title_sample_rate(decoders_DVDA_Title *self, void *closure);

static PyObject*
DVDA_Title_bits_per_sample(decoders_DVDA_Title *self, void *closure);

static PyObject*
DVDA_Title_channels(decoders_DVDA_Title *self, void *closure);

static PyObject*
DVDA_Title_channel_mask(decoders_DVDA_Title *self, void *closure);

static PyObject*
DVDA_Title_pcm_frames(decoders_DVDA_Title *self, void *closure);

PyGetSetDef DVDA_Title_getseters[] = {
    {"channels",
     (getter)DVDA_Title_channels, NULL, "channels", NULL},
    {"bits_per_sample",
     (getter)DVDA_Title_bits_per_sample, NULL, "bits_per_sample", NULL},
    {"sample_rate",
     (getter)DVDA_Title_sample_rate, NULL, "sample_rate", NULL},
    {"channel_mask",
     (getter)DVDA_Title_channel_mask, NULL, "channel_mask", NULL},
    {"pcm_frames",
     (getter)DVDA_Title_pcm_frames, NULL, "pcm_frames", NULL},
    {NULL}
};

static PyObject*
DVDA_Title_next_track(decoders_DVDA_Title *self, PyObject *args);

static PyObject*
DVDA_Title_read(decoders_DVDA_Title *self, PyObject *args);

static PyObject*
DVDA_Title_close(decoders_DVDA_Title *self, PyObject *args);

PyMethodDef DVDA_Title_methods[] = {
    {"next_track", (PyCFunction)DVDA_Title_next_track,
     METH_VARARGS, "Reinitializes the title for the next track in the stream"},
    {"read", (PyCFunction)DVDA_Title_read,
     METH_VARARGS, "Reads a frame of data from the AOB stream"},
    {"close", (PyCFunction)DVDA_Title_close,
     METH_NOARGS, "Closes the AOB stream"},
    {NULL}
};

PyTypeObject decoders_DVDA_Title_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "decoders.DVDA_Title",     /*tp_name*/
    sizeof(decoders_DVDA_Title), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)DVDA_Title_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "DVDA_Title objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    DVDA_Title_methods,        /* tp_methods */
    0,                         /* tp_members */
    DVDA_Title_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)DVDA_Title_init, /* tp_init */
    0,                         /* tp_alloc */
    DVDA_Title_new,            /* tp_new */
};
#endif

/*given a path to the AUDIO_TS directory
  and a filename to search for, in upper case,
  returns the full path to the file
  or NULL if the file is not found
  the path must be freed later once no longer needed*/
static char*
find_audio_ts_file(const char* audio_ts_path,
                   const char* uppercase_file);

/*DVDA_AOB is an AOB file on disk
  which is opened and ready for reading*/
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

static void
free_aob(DVDA_AOB* aob);


/*DVDA_Sector_Reader is a file-like object
  which abstracts away the split nature of AOB files
  that is, one can seek to a specific sector
  and this reader will automatically determine which AOB file
  to place the file cursor*/
typedef struct DVDA_Sector_Reader_s {
    array_o* aobs;          /*all the AOB files on the disc, in order*/
    struct {
        unsigned sector;
        DVDA_AOB* aob;
    } current;
    unsigned end_sector;    /*the final sector on the entire disc*/

#ifdef HAS_UNPROT
    /*if not NULL, indicates a CPPM decoder to call
      prior to returning sectors*/
    struct cppm_decoder* cppm_decoder;
#endif
} DVDA_Sector_Reader;

/*returns a DVDA_Sector_Reader which must be closed later
  or NULL with errno set if there's a problem opening
  any of the AOB files in that directory
  or there are no AOBs at all*/
static DVDA_Sector_Reader*
open_sector_reader(const char* audio_ts_path,
                   unsigned titleset_number,
                   const char* cdrom_device);

static void
close_sector_reader(DVDA_Sector_Reader* reader);

/*appends the next sector in the list to "sector"
  returns 0 on success, or 1 if a read error occurs
  an EOF condition appends no data to "sector" but returns 0*/
static int
read_sector(DVDA_Sector_Reader* reader,
            struct bs_buffer* sector);

static void
seek_sector(DVDA_Sector_Reader* reader,
            unsigned sector);


typedef struct DVDA_Packet_s {
    unsigned codec_ID;
    unsigned CRC;
    struct {
        unsigned first_audio_frame;
        unsigned group_1_bps;
        unsigned group_2_bps;
        unsigned group_1_rate;
        unsigned group_2_rate;
        unsigned channel_assignment;
        unsigned CRC;
    } PCM;
} DVDA_Packet;

/*DVDA_Packet_Reader is a file-like object
  which abstracts away the packet layout in AOB sectors
  that is, one can perform reads on the audio packets
  as a single, continuous stream of data
  (which may be a subset of the sector reader's total stream)*/
typedef struct DVDA_Packet_Reader_s {
    unsigned start_sector;
    unsigned end_sector;

    DVDA_Sector_Reader* sectors;
    BitstreamReader* reader;
    unsigned total_sectors;
} DVDA_Packet_Reader;

/*returns a DVDA_Packet_Reader which must be closed later
  this reader is confined to the given range of sectors
  which are inclusive at both ends*/
static DVDA_Packet_Reader*
open_packet_reader(DVDA_Sector_Reader* sectors,
                   unsigned start_sector,
                   unsigned end_sector);

/*writes the next audio packet in the list to "packet"
  returns 0 on success, or 1 if a read error occurs
  an EOF condition writes no data to "packet" but returns 0*/
static int
read_audio_packet(DVDA_Packet_Reader* packets,
                  DVDA_Packet* packet, struct bs_buffer* packet_data);

/*closes the DVDA_Packet_Reader
  but does *not* close the enclosed DVDA_Sector_Reader object*/
static void
close_packet_reader(DVDA_Packet_Reader* packets);


/*given a 4-bit encoded bits-per-sample value
  returns the stream's bits-per-sample as 16/20/24 or 0 if not found*/
unsigned
dvda_bits_per_sample(unsigned encoded);

/*given a 4-bit encoded sample rate value
  returns the stream's sample rate in Hz or 0 if not found*/
unsigned
dvda_sample_rate(unsigned encoded);

/*given a 5-bit encoded channel assignment value
  returns the stream's channel count*/
unsigned
dvda_channel_count(unsigned encoded);

/*given a 5-bit encoded channel assignment value
  returns the stream's channel mask*/
unsigned
dvda_channel_mask(unsigned encoded);
