#include "alac.h"
#include "../common/m4a_atoms.h"
#include "../framelist.h"
#include <string.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2015  Brian Langenberger

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

typedef enum {OK,
              INVALID_FRAME_CHANNEL_COUNT,
              EXCESSIVE_FRAME_CHANNEL_COUNT,
              FRAME_BLOCK_SIZE_MISMATCH,
              INVALID_BLOCK_SIZE,
              INVALID_PREDICTION_TYPE,
              NOT_IMPLEMENTED_ERROR} status_t;

/*the maximum coefficients that can fit in an unsigned 5-bit field*/
#define MAX_COEFFICIENTS 31

struct subframe_header {
    unsigned prediction_type;
    unsigned shift_needed;
    unsigned rice_modifier;
    unsigned coeff_count;
    int coeff[MAX_COEFFICIENTS];
};

/**********************************/
/*  private function definitions  */
/**********************************/

/*reads an atom header to the given size and name
  returns 1 on success, 0 if a read error occurs*/
static int
read_atom_header(BitstreamReader *stream,
                 unsigned *atom_size,
                 char atom_name[4]);

/*given a "moov" atom, parses the stream's decoding parameters
  returns 1 on success, 0 on failure*/
static int
get_decoding_parameters(decoders_ALACDecoder *self,
                        struct qt_atom *moov_atom);

/*given a "moov" atom, parses the stream's seektable
  returns 1 on success, 0 on failure*/
static int
get_seektable(decoders_ALACDecoder *self,
              struct qt_atom *moov_atom);

#ifndef STANDALONE
static PyObject*
alac_exception(status_t status);
#endif

static const char*
alac_strerror(status_t status);

static status_t
decode_frameset(decoders_ALACDecoder *self,
                unsigned *pcm_frames_read,
                int *samples);

static status_t
decode_frame(BitstreamReader *br,
             const struct alac_parameters *params,
             unsigned bits_per_sample,
             unsigned *block_size,
             unsigned channels,
             int channel_0[],
             int channel_1[]);

static status_t
decode_uncompressed_frame(BitstreamReader *br,
                          unsigned bits_per_sample,
                          unsigned block_size,
                          unsigned channels,
                          int channel_0[],
                          int channel_1[]);

static status_t
decode_compressed_frame(BitstreamReader *br,
                        const struct alac_parameters *params,
                        unsigned uncompressed_LSBs,
                        unsigned bits_per_sample,
                        unsigned block_size,
                        unsigned channels,
                        int channel_0[],
                        int channel_1[]);

static status_t
read_subframe_header(BitstreamReader *br,
                     struct subframe_header *subframe_header);

static void
read_residual_block(BitstreamReader *br,
                    const struct alac_parameters *params,
                    unsigned sample_size,
                    unsigned block_size,
                    int residual[]);

static unsigned
read_residual(BitstreamReader *br,
              unsigned int k,
              unsigned int sample_size);

static void
decode_subframe(unsigned block_size,
                unsigned sample_size,
                struct subframe_header *subframe_header,
                const int residuals[],
                int subframe[]);

static void
decorrelate_channels(unsigned block_size,
                     unsigned interlacing_shift,
                     unsigned interlacing_leftweight,
                     const int subframe_0[],
                     const int subframe_1[],
                     int left[],
                     int right[]);

static void
reorder_channels(unsigned pcm_frames,
                 unsigned channel_count,
                 int *samples);

/*************************************/
/*  public function implementations  */
/*************************************/

#ifndef STANDALONE
PyObject*
ALACDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_ALACDecoder *self;

    self = (decoders_ALACDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
ALACDecoder_init(decoders_ALACDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    PyObject *file;
    unsigned atom_size;
    char atom_name[4];
    int got_decoding_parameters = 0;
    int got_seektable = 0;

    self->bitstream = NULL;
    self->mdat_start = NULL;
    self->total_pcm_frames = 0;
    self->read_pcm_frames = 0;
    self->seektable = NULL;
    self->closed = 0;
    self->audiotools_pcm = NULL;

    /*setup some dummy parameters*/
    self->params.block_size = 4096;
    self->params.history_multiplier = 40;
    self->params.initial_history = 10;
    self->params.maximum_K = 14;

    if (!PyArg_ParseTuple(args, "O", &file)) {
        return -1;
    } else {
        Py_INCREF(file);
    }

    self->bitstream = br_open_external(
        file,
        BS_BIG_ENDIAN,
        4096,
        (ext_read_f)br_read_python,
        (ext_setpos_f)bs_setpos_python,
        (ext_getpos_f)bs_getpos_python,
        (ext_free_pos_f)bs_free_pos_python,
        (ext_seek_f)bs_fseek_python,
        (ext_close_f)bs_close_python,
        (ext_free_f)bs_free_python_decref);

    /*walk through atoms*/
    while (read_atom_header(self->bitstream, &atom_size, atom_name)) {
        if (!memcmp(atom_name, "mdat", 4)) {
            /*get mdat atom's starting position*/
            if (self->mdat_start) {
                PyErr_SetString(PyExc_ValueError,
                                "multiple mdat atoms found in stream");
                return -1;
            } else {
                self->mdat_start = self->bitstream->getpos(self->bitstream);
                self->bitstream->seek(self->bitstream,
                                      atom_size - 8,
                                      BS_SEEK_CUR);
            }
        } else if (!memcmp(atom_name, "moov", 4)) {
            /*find and parse metadata from moov atom*/

            struct qt_atom *moov_atom;

            if (!setjmp(*br_try(self->bitstream))) {
                moov_atom = qt_atom_parse_by_name(self->bitstream,
                                                  atom_size,
                                                  atom_name);

                br_etry(self->bitstream);
            } else {
                br_etry(self->bitstream);
                PyErr_SetString(PyExc_IOError, "I/O error parsing moov atom");
                return -1;
            }

            if (!got_decoding_parameters &&
                get_decoding_parameters(self, moov_atom)) {

                /*this is an arbitrary block size limit
                  to keep from blowing up the stack

                  Apple's reference encoder uses 4096 exclusively
                  but the file format allows sizes up to 32 bits(!)
                  which would break the whole world if anybody used
                  them all for a single ALAC frame.

                  so I'll just assume such files are malicious
                  and reject them outright*/
                if (self->params.block_size > 65535) {
                    PyErr_SetString(PyExc_ValueError, "block size too large");
                    return -1;
                }

                got_decoding_parameters = 1;
            }

            if (!got_seektable && get_seektable(self, moov_atom)) {
                got_seektable = 1;
            }

            moov_atom->free(moov_atom);
        } else {
            /*skip remaining atoms*/

            if (atom_size >= 8) {
                self->bitstream->seek(self->bitstream,
                                      atom_size - 8,
                                      BS_SEEK_CUR);
            }
        }
    }

    if (!got_decoding_parameters) {
        PyErr_SetString(PyExc_ValueError, "no decoding parameters");
        return -1;
    }

    /*seek to start of mdat atom*/
    if (self->mdat_start) {
        self->bitstream->setpos(self->bitstream, self->mdat_start);
    } else {
        PyErr_SetString(PyExc_ValueError, "no mdat atom found in stream");
        return -1;
    }

    /*open FrameList generator*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL) {
        return -1;
    }

    return 0;
}

void
ALACDecoder_dealloc(decoders_ALACDecoder *self)
{
    if (self->bitstream) {
        self->bitstream->free(self->bitstream);
    }
    if (self->mdat_start) {
        self->mdat_start->del(self->mdat_start);
    }
    free(self->seektable);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
ALACDecoder_sample_rate(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->sample_rate);
}

static PyObject*
ALACDecoder_bits_per_sample(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->bits_per_sample);
}

static PyObject*
ALACDecoder_channels(decoders_ALACDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->channels);
}

static PyObject*
ALACDecoder_channel_mask(decoders_ALACDecoder *self, void *closure)
{
    enum {fL=0x1,   /*front left*/
          fR=0x2,   /*front right*/
          fC=0x4,   /*front center*/
          LFE=0x8,
          bL=0x10,  /*back left*/
          bR=0x20,  /*back right*/
          bC=0x100, /*back center*/
          lC=0x200, /*left center*/
          rC=0x400  /*right center*/
          };
    int mask;

    switch (self->channels) {
    case 1:
        mask = fC;
        break;
    case 2:
        mask = fL | fR;
        break;
    case 3:
        mask = fC | fL | fR;
        break;
    case 4:
        mask = fC | fL | fR | bC;
        break;
    case 5:
        mask = fC | fL | fR | bL | bR;
        break;
    case 6:
        mask = fC | fL | fR | bL | bR | LFE;
        break;
    case 7:
        mask = fC | fL | fR | bL | bR | bC | LFE;
        break;
    case 8:
        mask = fC | lC | rC | fL | fR | bL | bR | LFE;
        break;
    default:
        mask = 0;
        break;
    }

    return Py_BuildValue("i", mask);
}

static PyObject*
ALACDecoder_read(decoders_ALACDecoder* self, PyObject *args)
{
    pcm_FrameList *framelist;
    status_t status;
    unsigned pcm_frames_read;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    if (self->read_pcm_frames >= self->total_pcm_frames) {
        return empty_FrameList(self->audiotools_pcm,
                               self->channels,
                               self->bits_per_sample);
    }

    /*build FrameList based on alac decoding parameters*/
    framelist = new_FrameList(self->audiotools_pcm,
                              self->channels,
                              self->bits_per_sample,
                              self->params.block_size);

    /*decode ALAC frameset to FrameList*/
    if (!setjmp(*br_try(self->bitstream))) {
        status = decode_frameset(self,
                                 &pcm_frames_read,
                                 framelist->samples);
        br_etry(self->bitstream);
    } else {
        br_etry(self->bitstream);
        Py_DECREF((PyObject*)framelist);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }

    if (status != OK) {
        Py_DECREF((PyObject*)framelist);
        PyErr_SetString(alac_exception(status), alac_strerror(status));
        return NULL;
    }

    /*constrain FrameList to actual amount of PCM frames read
      which may be less than block size at the end of stream*/
    framelist->frames = pcm_frames_read;
    framelist->samples_length = pcm_frames_read * self->channels;

    /*reorder FrameList to .wav order*/
    reorder_channels(pcm_frames_read,
                     self->channels,
                     framelist->samples);

    self->read_pcm_frames += pcm_frames_read;

    /*return populated FrameList*/
    return (PyObject*)framelist;
}

static PyObject*
ALACDecoder_seek(decoders_ALACDecoder* self, PyObject *args)
{
    long long seeked_offset;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot seek closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "L", &seeked_offset)) {
        return NULL;
    }

    if (seeked_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "cannot seek to negative value");
        return NULL;
    }

    if (!self->seektable) {
        /*no seektable, so seek to beginning of file*/
        if (!setjmp(*br_try(self->bitstream))) {
            self->bitstream->setpos(self->bitstream, self->mdat_start);
            br_etry(self->bitstream);
            self->read_pcm_frames = 0;
            return Py_BuildValue("i", 0);
        } else {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error seeking in stream");
            return NULL;
        }
    } else {
        unsigned i;
        unsigned pcm_frames_offset = 0;
        long byte_offset = 0;

        /*find latest seekpoint whose first sample is <= seeked_offset
          or 0 if there are no seekpoints in the seektable*/
        for (i = 0; i < self->total_alac_frames; i++) {
            if (seeked_offset >= self->seektable[i].pcm_frames) {
                seeked_offset -= self->seektable[i].pcm_frames;
                pcm_frames_offset += self->seektable[i].pcm_frames;
                byte_offset += self->seektable[i].byte_size;
            } else {
                break;
            }
        }

        /*position bitstream to indicated position in file*/
        if (!setjmp(*br_try(self->bitstream))) {
            self->bitstream->setpos(self->bitstream, self->mdat_start);
            self->bitstream->seek(self->bitstream, byte_offset, BS_SEEK_CUR);
            br_etry(self->bitstream);
        } else {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_IOError, "I/O error seeking in stream");
            return NULL;
        }

        /*reset stream's total remaining frames*/
        self->read_pcm_frames = pcm_frames_offset;

        /*return actual PCM frame position in file*/
        return Py_BuildValue("I", pcm_frames_offset);
    }

}

static PyObject*
ALACDecoder_close(decoders_ALACDecoder* self, PyObject *args)
{
    /*mark stream as closed so more calls to read()
      generate ValueErrors*/
    self->closed = 1;

    /*close internal stream*/
    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
ALACDecoder_enter(decoders_ALACDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
ALACDecoder_exit(decoders_ALACDecoder* self, PyObject *args)
{
    self->closed = 1;

    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}
#endif

/**************************************/
/*  private function implementations  */
/**************************************/

static int
read_atom_header(BitstreamReader *stream,
                 unsigned *atom_size,
                 char atom_name[4])
{
    if (!setjmp(*br_try(stream))) {
        *atom_size = stream->read(stream, 32);
        stream->read_bytes(stream, (uint8_t*)atom_name, 4);
        br_etry(stream);
        return 1;
    } else {
        br_etry(stream);
        return 0;
    }
}

static int
get_decoding_parameters(decoders_ALACDecoder *self,
                        struct qt_atom *moov_atom)
{
    const static char *mvhd_path[] =
        {"mvhd", NULL};
    const static char *alac_path[] =
        {"trak", "mdia", "minf", "stbl", "stsd", "alac", "alac", NULL};
    struct qt_atom *mvhd_atom;
    struct qt_atom *alac_atom;

    /*use mvhd atom to populate total PCM frames*/
    if (((mvhd_atom = moov_atom->find(moov_atom, mvhd_path)) != NULL) &&
        (mvhd_atom->type == QT_MVHD)) {
        self->total_pcm_frames = (unsigned)mvhd_atom->_.mvhd.duration;
    } else {
        return 0;
    }

    /*use alac atom to populate stream parameters*/
    if (((alac_atom = moov_atom->find(moov_atom, alac_path)) != NULL) &&
        (alac_atom->type == QT_SUB_ALAC)) {
        self->params.block_size =
            alac_atom->_.sub_alac.max_samples_per_frame;
        self->bits_per_sample =
            alac_atom->_.sub_alac.bits_per_sample;
        self->params.history_multiplier =
            alac_atom->_.sub_alac.history_multiplier;
        self->params.initial_history =
            alac_atom->_.sub_alac.initial_history;
        self->params.maximum_K =
            alac_atom->_.sub_alac.maximum_K;
        self->channels =
            alac_atom->_.sub_alac.channels;
        self->sample_rate =
            alac_atom->_.sub_alac.sample_rate;
    } else {
        return 0;
    }

    return 1;
}

static int
get_seektable(decoders_ALACDecoder *self,
              struct qt_atom *moov_atom)
{
    const char *stts_path[] =
        {"trak", "mdia", "minf", "stbl", "stts", NULL};
    const char *stsz_path[] =
        {"trak", "mdia", "minf", "stbl", "stsz", NULL};
    struct qt_atom *stts_atom;
    struct qt_atom *stsz_atom;
    unsigned stts_total_frames = 0;
    unsigned i;
    unsigned j;
    struct stts_time time;

    /*ensure both stts and stsz are present and the correct type*/
    if (((stts_atom = moov_atom->find(moov_atom, stts_path)) == NULL) ||
        (stts_atom->type != QT_STTS)) {
        return 0;
    }
    if (((stsz_atom = moov_atom->find(moov_atom, stsz_path)) == NULL) ||
        (stsz_atom->type != QT_STSZ)) {
        return 0;
    }

    /*ensure frame count of stts matches frame count of stsz*/
    for (i = 0; i < stts_atom->_.stts.times_count; i++) {
        stts_total_frames += stts_atom->_.stts.times[i].occurences;
    }
    if (stts_total_frames != stsz_atom->_.stsz.frames_count) {
        return 0;
    }

    /*allocate and populate seektable*/
    time = stts_atom->_.stts.times[0];
    self->total_alac_frames = stts_total_frames;
    self->seektable = malloc(stts_total_frames * sizeof(struct alac_seekpoint));
    for (i = j = 0; i < stts_total_frames; i++) {
        while (time.occurences == 0) {
            time = stts_atom->_.stts.times[++j];
        }
        self->seektable[i].pcm_frames = time.pcm_frame_count;
        self->seektable[i].byte_size = stsz_atom->_.stsz.frame_size[i];
        time.occurences -= 1;
    }

    return 1;
}

#ifndef STANDALONE
static PyObject*
alac_exception(status_t status)
{
    switch (status) {
    default: /*shouldn't happen*/
        return PyExc_ValueError;
    case INVALID_FRAME_CHANNEL_COUNT:
    case EXCESSIVE_FRAME_CHANNEL_COUNT:
    case FRAME_BLOCK_SIZE_MISMATCH:
    case INVALID_BLOCK_SIZE:
    case INVALID_PREDICTION_TYPE:
    case NOT_IMPLEMENTED_ERROR:
        return PyExc_ValueError;
    }
}
#endif

static const char*
alac_strerror(status_t status)
{
    switch (status) {
    default:
        return "unknown error";
    case INVALID_FRAME_CHANNEL_COUNT:
        return "frame channel count not 1 or 2";
    case EXCESSIVE_FRAME_CHANNEL_COUNT:
        return "frameset channels too large";
    case FRAME_BLOCK_SIZE_MISMATCH:
        return "all frames not the same block size";
    case INVALID_BLOCK_SIZE:
        return "frame block size greater than maximum block size";
    case INVALID_PREDICTION_TYPE:
        return "invalid prediction type";
    case NOT_IMPLEMENTED_ERROR:
        return "not yet implemented";
    }
}

static status_t
decode_frameset(decoders_ALACDecoder *self,
                unsigned *pcm_frames_read,
                int *samples)
{
    BitstreamReader *br = self->bitstream;
    int channel_0[self->params.block_size];
    int channel_1[self->params.block_size];
    unsigned c = 0;
    unsigned block_size = self->params.block_size;
    unsigned channels = br->read(br, 3) + 1;

    while (channels != 8) {
        status_t status;
        unsigned frame_block_size;

        if ((channels != 1) && (channels != 2)) {
            /*only handle 1 or 2 channel frames*/
            return INVALID_FRAME_CHANNEL_COUNT;
        } else if ((c + channels) > self->channels) {
            /*ensure one doesn't decode too many channels*/
            return EXCESSIVE_FRAME_CHANNEL_COUNT;
        }

        if ((status = decode_frame(br,
                                   &(self->params),
                                   self->bits_per_sample,
                                   c == 0 ? &block_size : &frame_block_size,
                                   channels,
                                   channel_0,
                                   channel_1)) != OK) {
            return status;
        } else if ((c != 0) && (block_size != frame_block_size)) {
            return FRAME_BLOCK_SIZE_MISMATCH;
        }

        put_channel_data(samples,
                         c++,
                         self->channels,
                         block_size,
                         channel_0);

        if (channels == 2) {
            put_channel_data(samples,
                             c++,
                             self->channels,
                             block_size,
                             channel_1);
        }

        channels = br->read(br, 3) + 1;
    }
    br->byte_align(br);
    *pcm_frames_read = block_size;
    return OK;
}

static status_t
decode_frame(BitstreamReader *br,
             const struct alac_parameters *params,
             unsigned bits_per_sample,
             unsigned *block_size,
             unsigned channels,
             int channel_0[],
             int channel_1[])
{
    unsigned has_sample_count;
    unsigned uncompressed_LSBs;
    unsigned not_uncompressed;

    /*20 or 52-bit frame header*/
    br->skip(br, 16);
    has_sample_count = br->read(br, 1);
    uncompressed_LSBs = br->read(br, 2);
    not_uncompressed = br->read(br, 1);
    if (has_sample_count == 0) {
        *block_size = params->block_size;
    } else {
        *block_size = br->read(br, 32);
        if (*block_size > params->block_size) {
            return INVALID_BLOCK_SIZE;
        }
    }

    /*either compressed or uncompressed frame based on header*/
    if (not_uncompressed == 0) {
        return decode_compressed_frame(br,
                                       params,
                                       uncompressed_LSBs,
                                       bits_per_sample,
                                       *block_size,
                                       channels,
                                       channel_0,
                                       channel_1);
    } else {
        return decode_uncompressed_frame(br,
                                         bits_per_sample,
                                         *block_size,
                                         channels,
                                         channel_0,
                                         channel_1);
    }
}

static status_t
decode_uncompressed_frame(BitstreamReader *br,
                          unsigned bits_per_sample,
                          unsigned block_size,
                          unsigned channels,
                          int channel_0[],
                          int channel_1[])
{
    unsigned i;

    if (channels == 2) {
        for (i = 0; i < block_size; i++) {
            channel_0[i] = br->read_signed(br, bits_per_sample);
            channel_1[i] = br->read_signed(br, bits_per_sample);
        }
    } else {
        for (i = 0; i < block_size; i++) {
            channel_0[i] = br->read_signed(br, bits_per_sample);
        }
    }

    return OK;
}

static status_t
decode_compressed_frame(BitstreamReader *br,
                        const struct alac_parameters *params,
                        unsigned uncompressed_LSBs,
                        unsigned bits_per_sample,
                        unsigned block_size,
                        unsigned channels,
                        int channel_0[],
                        int channel_1[])
{

    const unsigned uncompressed_bits = uncompressed_LSBs * 8;
    const unsigned sample_size =
        bits_per_sample - uncompressed_bits + (channels - 1);
    const unsigned interlacing_shift = br->read(br, 8);
    const unsigned interlacing_leftweight = br->read(br, 8);
    struct subframe_header subframe_header[channels];
    int subframe[channels][block_size];
    unsigned i;
    unsigned c;
    status_t status;

    for (c = 0; c < channels; c++) {
        if ((status = read_subframe_header(br, &subframe_header[c])) != OK) {
            return status;
        }
    }

    if (!uncompressed_bits) {
        /*the common case where there's no uncompressed
          least-significant bits to handle, such as 16bps audio*/

        for (c = 0; c < channels; c++) {
            int residual[block_size];

            read_residual_block(br, params, sample_size, block_size, residual);

            decode_subframe(block_size,
                            sample_size,
                            &subframe_header[c],
                            residual,
                            subframe[c]);
        }

        /*perform channel decorrelation, if necessary*/
        if (channels == 2) {
            if (interlacing_leftweight > 0) {
                decorrelate_channels(block_size,
                                     interlacing_shift,
                                     interlacing_leftweight,
                                     subframe[0],
                                     subframe[1],
                                     channel_0,
                                     channel_1);
            } else {
                memcpy(channel_0, subframe[0], block_size * sizeof(int));
                memcpy(channel_1, subframe[1], block_size * sizeof(int));
            }
        } else {
            memcpy(channel_0, subframe[0], block_size * sizeof(int));
        }
    } else {
        /*the case where there are least significant bits to handle
          such as for 24bps audio*/

        int LSBs[channels][block_size];

        for (i = 0; i < block_size; i++) {
            for (c = 0; c < channels; c++) {
                LSBs[c][i] = br->read(br, uncompressed_bits);
            }
        }

        for (c = 0; c < channels; c++) {
            int residual[block_size];

            read_residual_block(br, params, sample_size, block_size, residual);

            decode_subframe(block_size,
                            sample_size,
                            &subframe_header[c],
                            residual,
                            subframe[c]);
        }

        /*perform channel decorrelation, if necessary*/
        if (channels == 2) {
            if (interlacing_leftweight > 0) {
                decorrelate_channels(block_size,
                                     interlacing_shift,
                                     interlacing_leftweight,
                                     subframe[0],
                                     subframe[1],
                                     channel_0,
                                     channel_1);
            } else {
                memcpy(channel_0, subframe[0], block_size * sizeof(int));
                memcpy(channel_1, subframe[1], block_size * sizeof(int));
            }

            /*apply uncompressed LSBs to channel data*/
            for (i = 0; i < block_size; i++) {
                channel_0[i] <<= uncompressed_bits;
                channel_0[i] |= LSBs[0][i];
                channel_1[i] <<= uncompressed_bits;
                channel_1[i] |= LSBs[1][i];
            }
        } else {
            memcpy(channel_0, subframe[0], block_size * sizeof(int));

            /*apply uncompressed LSBs to channel data*/
            for (i = 0; i < block_size; i++) {
                channel_0[i] <<= uncompressed_bits;
                channel_0[i] |= LSBs[0][i];
            }
        }
    }

    return OK;
}

static status_t
read_subframe_header(BitstreamReader *br,
                     struct subframe_header *subframe_header)
{
    unsigned i;

    subframe_header->prediction_type = br->read(br, 4);
    if (subframe_header->prediction_type != 0) {
        return INVALID_PREDICTION_TYPE;
    }
    subframe_header->shift_needed = br->read(br, 4);
    subframe_header->rice_modifier = br->read(br, 3);
    subframe_header->coeff_count = br->read(br, 5);
    for (i = 0; i < subframe_header->coeff_count; i++) {
        subframe_header->coeff[i] = br->read_signed(br, 16);
    }
    return OK;
}

/*this is the slow version*/
/*
  static inline int LOG2(int value) {
  double newvalue = trunc(log((double)value) / log((double)2));

  return (int)(newvalue);
  }
*/

/*the fast version used by ffmpeg and the "alac" decoder
  subtracts MSB zero bits from total bit size - 1,
  essentially counting the number of LSB non-zero bits, -1*/

/*my version just counts the number of non-zero bits and subtracts 1
  which is good enough for now*/
static inline int
LOG2(int value)
{
    int bits = -1;
    while (value) {
        bits++;
        value >>= 1;
    }
    return bits;
}

static void
read_residual_block(BitstreamReader *br,
                    const struct alac_parameters *params,
                    unsigned sample_size,
                    unsigned block_size,
                    int residual[])
{
    const unsigned maximum_k = params->maximum_K;
    const unsigned history_multiplier = params->history_multiplier;
    int history = params->initial_history;
    unsigned sign_modifier = 0;
    int i = 0;

    while (i < block_size) {
        /*get an unsigned residual based on "history"
          and on "sample_size" as a last resort*/
        const unsigned k = LOG2((history >> 9) + 3);
        const unsigned unsigned_residual =
            read_residual(br,
                          MIN(k, maximum_k),
                          sample_size) + sign_modifier;

        /*clear out old sign modifier, if any */
        sign_modifier = 0;

        /*change unsigned residual into a signed residual
          and append it to "residuals"*/
        if (unsigned_residual & 1) {
            residual[i++] = -((unsigned_residual + 1) >> 1);
        } else {
            residual[i++] = unsigned_residual >> 1;
        }

        /*then use our old unsigned residual to update "history"*/
        if (unsigned_residual > 0xFFFF)
            history = 0xFFFF;
        else
            history += ((unsigned_residual * history_multiplier) -
                        ((history * history_multiplier) >> 9));

        /*if history gets too small, we may have a block of 0 samples
          which can be compressed more efficiently*/
        if ((history < 128) && (i < block_size)) {
            unsigned zero_block_size = read_residual(
                br,
                MIN(7 - LOG2(history) + ((history + 16) / 64), maximum_k),
                16);

            if (zero_block_size > 0) {
                /*block of 0s found, so write them out*/

                /*ensure block of zeroes doesn't exceed
                  remaining residual count*/

                unsigned j;

                for (j = 0; (j < zero_block_size) && (i < block_size); j++) {
                    residual[i++] = 0;
                }
            }

            history = 0;

            if (zero_block_size <= 0xFFFF) {
                sign_modifier = 1;
            }
        }
    }
}

static unsigned
read_residual(BitstreamReader *br,
              unsigned int k,
              unsigned int sample_size)
{
    static br_huffman_table_t MSB[] =
#include "alac_residual.h"
    ;
    const int msb = br->read_huffman_code(br, MSB);

    /*read a unary 0 value to a maximum of 9 bits*/
    if (msb == -1) {
        /*we've exceeded the maximum number of 1 bits,
          so return an unencoded value*/
        return br->read(br, sample_size);
    } else if ((k == 0) || (k == 1)) {
        /*no least-significant bits to read, so return most-significant bits*/
        return (unsigned)msb;
    } else {
        /*read a set of least-significant bits*/
        unsigned lsb = br->read(br, k - 1);
        if (lsb == 0) {
            return (unsigned)msb * ((1 << k) - 1);
        } else {
            lsb <<= 1;
            lsb |= br->read(br, 1);
            return (msb * ((1 << k) - 1)) + (lsb - 1);
        }
    }
}

static inline int
SIGN_ONLY(int value)
{
    if (value > 0)
        return 1;
    else if (value < 0)
        return -1;
    else
        return 0;
}

static inline int
TRUNCATE_BITS(int value, unsigned bits)
{
    /*truncate value to bits*/
    const int truncated = value & ((1 << bits) - 1);

    /*apply sign bit*/
    if (truncated & (1 << (bits - 1))) {
        return truncated - (1 << bits);
    } else {
        return truncated;
    }
}

static void
decode_subframe(unsigned block_size,
                unsigned sample_size,
                struct subframe_header *subframe_header,
                const int residuals[],
                int subframe[])
{
    const unsigned qlp_shift_needed = subframe_header->shift_needed;
    const unsigned coeff_count = subframe_header->coeff_count;
    int *coeff = subframe_header->coeff;
    unsigned i;

    subframe[0] = residuals[0];

    for (i = 1; i < coeff_count + 1; i++) {
        subframe[i] = TRUNCATE_BITS(residuals[i] + subframe[i - 1],
                                    sample_size);
    }

    for (i = coeff_count + 1; i < block_size; i++) {
        int residual = residuals[i];
        const int base_sample = subframe[i - coeff_count - 1];
        register int64_t qlp_sum = 0;
        unsigned j;

        for (j = 0; j < coeff_count; j++) {
            qlp_sum += coeff[j] * (subframe[i - j - 1] - base_sample);
        }

        qlp_sum += (1 << (qlp_shift_needed - 1));
        qlp_sum >>= qlp_shift_needed;

        subframe[i] = TRUNCATE_BITS((int)(qlp_sum) + residual + base_sample,
                                    sample_size);

        if (residual > 0) {
            for (j = 0; j < coeff_count; j++) {
                int diff = base_sample - subframe[i - coeff_count + j];
                int sign = SIGN_ONLY(diff);
                coeff[coeff_count - j - 1] -= sign;
                residual -= ((diff * sign) >> qlp_shift_needed) * (j + 1);
                if (residual <= 0) {
                    break;
                }
            }
        } else if (residual < 0) {
            for (j = 0; j < coeff_count; j++) {
                int diff = base_sample - subframe[i - coeff_count + j];
                int sign = SIGN_ONLY(diff);
                coeff[coeff_count - j - 1] += sign;
                residual -= ((diff * -sign) >> qlp_shift_needed) * (j + 1);
                if (residual >= 0) {
                    break;
                }
            }
        }
    }
}

static void
decorrelate_channels(unsigned block_size,
                     unsigned interlacing_shift,
                     unsigned interlacing_leftweight,
                     const int subframe_0[],
                     const int subframe_1[],
                     int left[],
                     int right[])
{
    unsigned i;
    for (i = 0; i < block_size; i++) {
        register int64_t leftweight = subframe_1[i];
        leftweight *= interlacing_leftweight;
        leftweight >>= interlacing_shift;
        right[i] = subframe_0[i] - (int)leftweight;
        left[i] = subframe_1[i] + right[i];
    }
}

static void
reorder_channels(unsigned pcm_frames,
                 unsigned channel_count,
                 int *samples)
{
    switch (channel_count) {
    default:
        /*do nothing, leave samples as-is*/
        break;
    case 3:
        /*fC fL fR -> fL fC fR*/
        swap_channel_data(samples, 0, 1, 3, pcm_frames);

        /*fL fC fR -> fL fR fC*/
        swap_channel_data(samples, 1, 2, 3, pcm_frames);
        break;
    case 4:
        /*fC fL fR bC -> fL fC fR bC*/
        swap_channel_data(samples, 0, 1, 4, pcm_frames);

        /*fL fC fR bC -> fL fR fC bC*/
        swap_channel_data(samples, 1, 2, 4, pcm_frames);
        break;
    case 5:
        /*fC fL fR bL bR -> fL fC fR bL bR*/
        swap_channel_data(samples, 0, 1, 5, pcm_frames);

        /*fL fC fR bL bR -> fL fR fC bL bR*/
        swap_channel_data(samples, 1, 2, 5, pcm_frames);
        break;
    case 6:
        /*fC fL fR bL bR LFE -> fL fC fR bL bR LFE*/
        swap_channel_data(samples, 0, 1, 6, pcm_frames);

        /*fL fC fR bL bR LFE -> fL fR fC bL bR LFE*/
        swap_channel_data(samples, 1, 2, 6, pcm_frames);

        /*fL fR fC bL bR LFE -> fL fR fC LFE bR bL*/
        swap_channel_data(samples, 3, 5, 6, pcm_frames);

        /*fL fR fC LFE bR bL -> fL fR fC LFE bL bR*/
        swap_channel_data(samples, 4, 5, 6, pcm_frames);
        break;
    case 7:
        /*fC fL fR bL bR bC LFE -> fL fC fR bL bR bC LFE*/
        swap_channel_data(samples, 0, 1, 7, pcm_frames);

        /*fL fC fR bL bR bC LFE -> fL fR fC bL bR bC LFE*/
        swap_channel_data(samples, 1, 2, 7, pcm_frames);

        /*fL fR fC bL bR bC LFE -> fL fR fC LFE bR bC bL*/
        swap_channel_data(samples, 3, 6, 7, pcm_frames);

        /*fL fR fC LFE bR bC bL -> fL fR fC LFE bL bC bR*/
        swap_channel_data(samples, 4, 6, 7, pcm_frames);

        /*fL fR fC LFE bL bC bR -> fL fR fC LFE bL bR bC*/
        swap_channel_data(samples, 5, 6, 7, pcm_frames);
        break;
    case 8:
        /*fC sL sR fL fR bL bR LFE -> fL sL sR fC fR bL bR LFE*/
        swap_channel_data(samples, 0, 3, 8, pcm_frames);

        /*fL sL sR fC fR bL bR LFE -> fL fR sR fC sL bL bR LFE*/
        swap_channel_data(samples, 1, 4, 8, pcm_frames);

        /*fL fR sR fC sL bL bR LFE -> fL fR fC sR sL bL bR LFE*/
        swap_channel_data(samples, 2, 3, 8, pcm_frames);

        /*fL fR fC sR sL bL bR LFE -> fL fR fC LFE sL bL bR sR*/
        swap_channel_data(samples, 3, 7, 8, pcm_frames);

        /*fL fR fC LFE sL bL bR sR -> fL fR fC LFE bL sL bR sR*/
        swap_channel_data(samples, 4, 5, 8, pcm_frames);

        /*fL fR fC LFE bL sL bR sR -> fL fR fC LFE bL bR sL sR*/
        swap_channel_data(samples, 5, 6, 8, pcm_frames);
        break;
    }
}

#ifdef STANDALONE

#include <errno.h>

int
main(int argc, char *argv[])
{
    FILE *file;
    BitstreamReader *bitstream;
    unsigned atom_size;
    char atom_name[4];
    int got_decoding_parameters = 0;
    br_pos_t *mdat_start = NULL;
    decoders_ALACDecoder decoder;
    int *samples = NULL;
    int_to_pcm_f converter;
    unsigned char *buffer = NULL;
    unsigned bytes_per_sample;
    int return_status = 0;

    /*setup some dummy parameters*/
    decoder.params.block_size = 4096;
    decoder.params.history_multiplier = 40;
    decoder.params.initial_history = 10;
    decoder.params.maximum_K = 14;

    /*open input file*/
    if (argc < 2) {
        fprintf(stderr, "*** Usage: alacdec <file.m4a>\n");
        return 1;
    }

    errno = 0;
    if ((file = fopen(argv[1], "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", argv[1], strerror(errno));
        return 1;
    } else {
        bitstream = br_open(file, BS_BIG_ENDIAN);
    }

    /*walk through atoms and get decoding parameters*/
    while (read_atom_header(bitstream, &atom_size, atom_name)) {
        if (!memcmp(atom_name, "mdat", 4)) {
            /*get mdat atom's starting position*/
            if (mdat_start) {
                fputs("multiple mdat atoms found in stream\n", stderr);
                return_status = 1;
                goto done;
            } else {
                mdat_start = bitstream->getpos(bitstream);
                bitstream->seek(bitstream, atom_size - 8, BS_SEEK_CUR);
            }
        } else if (!memcmp(atom_name, "moov", 4)) {
            /*find and parse metadata from moov atom*/

            struct qt_atom *moov_atom;

            if (!setjmp(*br_try(bitstream))) {
                moov_atom = qt_atom_parse_by_name(bitstream,
                                                  atom_size,
                                                  atom_name);

                br_etry(bitstream);
            } else {
                br_etry(bitstream);
                fputs("I/O error reading moov atom\n", stderr);
                return_status = 1;
                goto done;
            }

            if (!got_decoding_parameters &&
                get_decoding_parameters(&decoder, moov_atom)) {

                if (decoder.params.block_size > 65535) {
                    fprintf(stderr, "block size %u too large\n",
                            decoder.params.block_size);
                    return_status = 1;
                    goto done;
                }

                got_decoding_parameters = 1;
            }

            moov_atom->free(moov_atom);
        } else {
            /*skip remaining atoms*/

            if (atom_size >= 8) {
                bitstream->seek(bitstream, atom_size - 8, BS_SEEK_CUR);
            }
        }
    }

    if (!got_decoding_parameters) {
        fputs("no decoding parameters found in stream\n", stderr);
        return_status = 1;
        goto done;
    } else {
        converter = int_to_pcm_converter(decoder.bits_per_sample, 0, 1);
        bytes_per_sample = decoder.bits_per_sample / 8;
        samples = malloc(decoder.channels *
                         decoder.params.block_size *
                         sizeof(int));
        buffer = malloc(decoder.channels *
                        decoder.params.block_size *
                        bytes_per_sample);
        decoder.bitstream = bitstream;
        decoder.read_pcm_frames = 0;
    }

    /*rewind to start of mdat*/
    bitstream->setpos(bitstream, mdat_start);
    mdat_start->del(mdat_start);
    mdat_start = NULL;

    /*decode all PCM frames from input file to stdout*/
    while (decoder.read_pcm_frames < decoder.total_pcm_frames) {
        unsigned pcm_frames_read;
        status_t status;

        if (!setjmp(*br_try(bitstream))) {
            status = decode_frameset(&decoder, &pcm_frames_read, samples);
            br_etry(bitstream);
        } else {
            br_etry(bitstream);
            fputs("I/O error reading stream\n", stderr);
            return_status = 1;
            goto done;
        }

        if (status == OK) {
            /*increment samples read*/
            decoder.read_pcm_frames += pcm_frames_read;

            /*reorder channels to .wav order*/
            reorder_channels(pcm_frames_read,
                             decoder.channels,
                             samples);

            /*output samples to stdout*/
            converter(pcm_frames_read * decoder.channels, samples, buffer);

            fwrite(buffer,
                   1,
                   pcm_frames_read * decoder.channels * bytes_per_sample,
                   stdout);
        } else {
            fprintf(stderr, "*** Error: %s\n", alac_strerror(status));
            return_status = 1;
            goto done;
        }
    }

done:
    /*deallocate reader and any buffers*/
    free(samples);
    free(buffer);
    if (mdat_start) {
        mdat_start->del(mdat_start);
    }
    bitstream->close(bitstream);

    return return_status;
}

#endif
