#include "flac.h"
#include "../framelist.h"
#include "../common/flac_crc.h"

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
              INVALID_SYNC_CODE,
              INVALID_SAMPLE_RATE,
              INVALID_BPS,
              INVALID_CHANNEL_ASSIGNMENT,
              INVALID_UTF8,
              INVALID_CRC8,
              IOERROR_HEADER,
              IOERROR_SUBFRAME,
              INVALID_SUBFRAME_HEADER,
              INVALID_FIXED_ORDER,
              INVALID_LPC_ORDER,
              INVALID_CODING_METHOD,
              INVALID_WASTED_BPS,
              INVALID_PARTITION_ORDER,
              BLOCK_SIZE_MISMATCH,
              SAMPLE_RATE_MISMATCH,
              BPS_MISMATCH,
              CHANNEL_COUNT_MISMATCH} status_t;

typedef enum {INDEPENDENT,
              LEFT_DIFFERENCE,
              DIFFERENCE_RIGHT,
              AVERAGE_DIFFERENCE} channel_assignment_t;

typedef enum {CONSTANT,
              VERBATIM,
              FIXED,
              LPC} subframe_type_t;

struct frame_header {
    unsigned blocking_strategy;
    unsigned block_size;
    unsigned sample_rate;
    channel_assignment_t channel_assignment;
    unsigned channel_count;
    unsigned bits_per_sample;
    unsigned frame_number;
};

/*******************************
 * private function signatures *
 *******************************/

static int
valid_stream_id(BitstreamReader *r);

static void
read_block_header(BitstreamReader *r,
                  unsigned *last,
                  unsigned *type,
                  unsigned *size);

static void
read_STREAMINFO(BitstreamReader *r, struct STREAMINFO *streaminfo);

static void
read_SEEKTABLE(BitstreamReader *r,
               unsigned block_size,
               struct SEEKTABLE *seektable);

static void
read_VORBIS_COMMENT(BitstreamReader *r, unsigned *channel_mask);

static status_t
read_frame_header(BitstreamReader *r,
                  const struct STREAMINFO *streaminfo,
                  struct frame_header *frame_header);

static status_t
read_utf8(BitstreamReader *r, unsigned *utf8);

static status_t
decode_independent(BitstreamReader *r,
                   const struct frame_header *frame_header,
                   int samples[]);

static status_t
decode_left_difference(BitstreamReader *r,
                       const struct frame_header *frame_header,
                       int samples[]);
static status_t
decode_difference_right(BitstreamReader *r,
                        const struct frame_header *frame_header,
                        int samples[]);

static status_t
decode_average_difference(BitstreamReader *r,
                          const struct frame_header *frame_header,
                          int samples[]);

static status_t
read_subframe(BitstreamReader *r,
              unsigned block_size,
              unsigned bits_per_sample,
              int channel_data[]);

static status_t
read_subframe_header(BitstreamReader *r,
                     subframe_type_t *type,
                     unsigned *order,
                     unsigned *wasted_bps);

static void
read_CONSTANT_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[]);

static void
read_VERBATIM_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[]);

static status_t
read_FIXED_subframe(BitstreamReader *r,
                    unsigned block_size,
                    unsigned bits_per_sample,
                    unsigned predictor_order,
                    int samples[]);

static status_t
read_LPC_subframe(BitstreamReader *r,
                  unsigned block_size,
                  unsigned bits_per_sample,
                  unsigned predictor_order,
                  int samples[]);

static status_t
read_residual_block(BitstreamReader *r,
                    unsigned block_size,
                    unsigned predictor_order,
                    int residuals[]);

static void
decorrelate_left_difference(unsigned block_size,
                            const int left[],
                            const int difference[],
                            int right[]);
static void
decorrelate_difference_right(unsigned block_size,
                             const int difference[],
                             const int right[],
                             int left[]);

static void
decorrelate_average_difference(unsigned block_size,
                               const int average[],
                               const int difference[],
                               int left[],
                               int right[]);

static status_t
skip_subframe(BitstreamReader *r,
              unsigned block_size,
              unsigned bits_per_sample);

static void
skip_CONSTANT_subframe(BitstreamReader *r,
                       unsigned bits_per_sample);

static void
skip_VERBATIM_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample);

static status_t
skip_FIXED_subframe(BitstreamReader *r,
                    unsigned block_size,
                    unsigned bits_per_sample,
                    unsigned predictor_order);

static status_t
skip_LPC_subframe(BitstreamReader *r,
                  unsigned block_size,
                  unsigned bits_per_sample,
                  unsigned predictor_order);

static status_t
skip_residual_block(BitstreamReader *r,
                    unsigned block_size,
                    unsigned predictor_order);

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int pcm_data[],
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames);

static int
verify_md5sum(audiotools__MD5Context *stream_md5,
              const uint8_t streaminfo_md5[]);

PyObject*
flac_exception(status_t status);

const char*
flac_strerror(status_t status);

/***********************************
 * public function implementations *
 ***********************************/

PyObject*
FlacDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_FlacDecoder *self;

    self = (decoders_FlacDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}


int
FlacDecoder_init(decoders_FlacDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    PyObject *file;
    int streaminfo_read = 0;
    int vorbis_comment_read = 0;
    unsigned last;
    unsigned type;
    unsigned size;

    self->bitstream = NULL;
    self->seektable.total_points = 0;
    self->seektable.seek_points = NULL;
    self->channel_mask = 0;
    self->remaining_samples = 0;
    self->closed = 0;
    audiotools__MD5Init(&(self->md5));
    self->perform_validation = 1;
    self->stream_finalized = 0;
    self->audiotools_pcm = NULL;
    self->beginning_of_frames = NULL;

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

    if (!setjmp(*br_try(self->bitstream))) {
        /*validate stream ID*/
        if (!valid_stream_id(self->bitstream)) {
            PyErr_SetString(PyExc_ValueError, "invalid stream ID");
            br_etry(self->bitstream);
            return -1;
        }

        /*parse metadata blocks*/
        do {
            read_block_header(self->bitstream, &last, &type, &size);

            switch (type) {
            case 0: /*STREAMINFO*/
                if (!streaminfo_read) {
                    enum {fL  = 0x1,
                          fR  = 0x2,
                          fC  = 0x4,
                          LFE = 0x8,
                          bL  = 0x10,
                          bR  = 0x20,
                          bC  = 0x100,
                          sL  = 0x200,
                          sR  = 0x400};
                    const uint8_t empty_md5[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                                   0, 0, 0, 0, 0, 0, 0, 0};

                    read_STREAMINFO(self->bitstream, &(self->streaminfo));
                    /*use a dummy channel mask for now*/
                    switch (self->streaminfo.channel_count) {
                    case 1:
                        self->channel_mask = fC;
                        break;
                    case 2:
                        self->channel_mask = fL | fR;
                        break;
                    case 3:
                        self->channel_mask = fL | fR | fC;
                        break;
                    case 4:
                        self->channel_mask = fL | fR | bL | bR;
                        break;
                    case 5:
                        self->channel_mask = fL | fR | fC | bL | bR;
                        break;
                    case 6:
                        self->channel_mask = fL | fR | fC | bL | bR | LFE;
                        break;
                    case 7:
                        self->channel_mask =
                        fL | fR | fC | LFE | bC | bL | bR;
                        break;
                    case 8:
                        self->channel_mask =
                        fL | fR | fC | LFE | bL | bR | sL | sR;
                        break;
                    }

                    /*turn off MD5 checking if MD5 sum is empty*/
                    if (memcmp(self->streaminfo.MD5, empty_md5, 16) == 0) {
                        self->perform_validation = 0;
                    }

                    streaminfo_read = 1;
                } else {
                    PyErr_SetString(PyExc_ValueError,
                                    "multiple STREAMINFO blocks in stream");
                    br_etry(self->bitstream);
                    return -1;
                }
                break;
            case 1: /*PADDING*/
            case 2: /*APPLICATION*/
            case 5: /*CUESHEET*/
            case 6: /*PICTURE*/
                self->bitstream->skip_bytes(self->bitstream, size);
                break;
            case 3: /*SEEKTABLE*/
                if (!(self->seektable.seek_points)) {
                    read_SEEKTABLE(self->bitstream, size, &(self->seektable));
                } else {
                    PyErr_SetString(PyExc_ValueError,
                                    "multiple SEEKTABLE blocks in stream");
                    br_etry(self->bitstream);
                    return -1;
                }
                break;
            case 4: /*VORBIS_COMMENT*/
                if (!vorbis_comment_read) {
                    BitstreamReader *comment =
                        self->bitstream->substream(self->bitstream, size);
                    read_VORBIS_COMMENT(comment, &(self->channel_mask));
                    comment->close(comment);
                    vorbis_comment_read = 1;
                } else {
                    PyErr_SetString(PyExc_ValueError,
                                    "multiple VORBIS_COMMENT blocks in stream");
                    br_etry(self->bitstream);
                    return -1;
                }
                break;
            default:
                PyErr_SetString(PyExc_ValueError, "unknown block ID in stream");
                br_etry(self->bitstream);
                return -1;
            }
        } while (last == 0);

        if (streaminfo_read) {
            self->remaining_samples = self->streaminfo.total_samples;
        } else {
            PyErr_SetString(PyExc_ValueError, "no STREAMINFO block in stream");
            br_etry(self->bitstream);
            return -1;
        }

        /*mark beginning of frames for start of decoding*/
        self->beginning_of_frames = self->bitstream->getpos(self->bitstream);

        br_etry(self->bitstream);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading FLAC metadata");
        return -1;
    }

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL) {
        return -1;
    }

    return 0;
}

void
FlacDecoder_dealloc(decoders_FlacDecoder *self)
{
    if (self->bitstream) {
        self->bitstream->free(self->bitstream);
    }
    free(self->seektable.seek_points);
    Py_XDECREF(self->audiotools_pcm);
    if (self->beginning_of_frames) {
        self->beginning_of_frames->del(self->beginning_of_frames);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}


PyObject*
FlacDecoder_close(decoders_FlacDecoder* self,
                  PyObject *args)
{
    /*mark stream as closed so more calls to read()
      generate ValueErrors*/
    self->closed = 1;

    /*close internal stream itself*/
    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
FlacDecoder_enter(decoders_FlacDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
FlacDecoder_exit(decoders_FlacDecoder* self, PyObject *args)
{
    self->closed = 1;
    self->bitstream->close_internal_stream(self->bitstream);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
FlacDecoder_sample_rate(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->streaminfo.sample_rate);
}

static PyObject*
FlacDecoder_bits_per_sample(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->streaminfo.bits_per_sample);
}

static PyObject*
FlacDecoder_channels(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->streaminfo.channel_count);
}

static PyObject*
FlacDecoder_channel_mask(decoders_FlacDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->channel_mask);
}

PyObject*
FlacDecoder_read(decoders_FlacDecoder* self, PyObject *args)
{
    status_t status;
    struct frame_header frame_header;
    uint16_t crc16 = 0;

    if (self->closed) {
        /*ensure file isn't closed*/
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    } else if (self->remaining_samples == 0) {
        /*validate MD5 sum if still validating
          (if we haven't seeked to the middle of the file, for instance)*/
        if (self->perform_validation) {
            if (verify_md5sum(&(self->md5), self->streaminfo.MD5)) {
                self->perform_validation = 0;
                /*return empty FrameList if nothing left to send*/
                return empty_FrameList(self->audiotools_pcm,
                                       self->streaminfo.channel_count,
                                       self->streaminfo.bits_per_sample);
            } else {
                PyErr_SetString(PyExc_ValueError,
                                "MD5 mismatch at end of stream");
                return NULL;
            }
        } else {
            return empty_FrameList(self->audiotools_pcm,
                                   self->streaminfo.channel_count,
                                   self->streaminfo.bits_per_sample);
        }
    }

    self->bitstream->add_callback(self->bitstream,
                                  (bs_callback_f)flac_crc16,
                                  &crc16);

    /*ensure frame header is read successfully*/
    if ((status = read_frame_header(self->bitstream,
                                    &(self->streaminfo),
                                    &frame_header)) != OK) {
        self->bitstream->pop_callback(self->bitstream, NULL);
        PyErr_SetString(flac_exception(status), flac_strerror(status));
        return NULL;
    } else {
        /*setup framelist to be output once populated*/
        pcm_FrameList *framelist = new_FrameList(self->audiotools_pcm,
                                                 frame_header.channel_count,
                                                 frame_header.bits_per_sample,
                                                 frame_header.block_size);

        /*decode subframes based on channel assignment*/
        status_t (*decode)(BitstreamReader *r,
                           const struct frame_header *frame_header,
                           int samples[]) = NULL;

        switch (frame_header.channel_assignment) {
        case INDEPENDENT:
            decode = decode_independent;
            break;
        case LEFT_DIFFERENCE:
            decode = decode_left_difference;
            break;
        case DIFFERENCE_RIGHT:
            decode = decode_difference_right;
            break;
        case AVERAGE_DIFFERENCE:
            decode = decode_average_difference;
            break;
        }
        assert(decode);

        if ((status = decode(self->bitstream,
                             &frame_header,
                             framelist->samples)) != OK) {
            Py_DECREF((PyObject*)framelist);
            self->bitstream->pop_callback(self->bitstream, NULL);
            PyErr_SetString(flac_exception(status), flac_strerror(status));
            return NULL;
        }

        /*validate CRC-16 in frame footer*/
        if (!setjmp(*br_try(self->bitstream))) {
            self->bitstream->byte_align(self->bitstream);
            self->bitstream->skip(self->bitstream, 16); /*CRC-16 itself*/
            br_etry(self->bitstream);
        } else {
            br_etry(self->bitstream);
            self->bitstream->pop_callback(self->bitstream, NULL);
            PyErr_SetString(PyExc_IOError, "I/O error reading CRC-16");
            Py_DECREF((PyObject*)framelist);
            return NULL;
        }
        self->bitstream->pop_callback(self->bitstream, NULL);
        if (crc16) {
            PyErr_SetString(PyExc_ValueError, "frame CRC-16 mismatch");
            Py_DECREF((PyObject*)framelist);
            return NULL;
        }

        /*if validating, update running MD5 sum*/
        if (self->perform_validation) {
            update_md5sum(&(self->md5),
                          framelist->samples,
                          frame_header.channel_count,
                          frame_header.bits_per_sample,
                          frame_header.block_size);
        }

        self->remaining_samples -= MIN(self->remaining_samples,
                                       frame_header.block_size);

        return (PyObject*)framelist;
    }
}

static PyObject*
FlacDecoder_frame_size(decoders_FlacDecoder* self, PyObject *args)
{
    status_t status;
    struct frame_header frame_header;
    unsigned c;
    uint16_t crc16 = 0;
    unsigned frame_size = 0;

    if (self->closed) {
        /*ensure file isn't closed*/
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    } else if (self->remaining_samples == 0) {
        /*return None if samples are exhausted*/
        Py_INCREF(Py_None);
        return Py_None;
    }

    self->perform_validation = 0;

    self->bitstream->add_callback(self->bitstream,
                                  (bs_callback_f)flac_crc16,
                                  &crc16);

    self->bitstream->add_callback(self->bitstream,
                                  (bs_callback_f)byte_counter,
                                  &frame_size);

    /*ensure frame header is read successfully*/
    if ((status = read_frame_header(self->bitstream,
                                    &(self->streaminfo),
                                    &frame_header)) != OK) {
        self->bitstream->pop_callback(self->bitstream, NULL);
        self->bitstream->pop_callback(self->bitstream, NULL);
        PyErr_SetString(flac_exception(status), flac_strerror(status));
        return NULL;
    }

    /*skip subframes*/
    switch (frame_header.channel_assignment) {
    case INDEPENDENT:
        for (c = 0; c < frame_header.channel_count; c++) {
            if ((status = skip_subframe(self->bitstream,
                                        frame_header.block_size,
                                        frame_header.bits_per_sample)) != OK) {
                self->bitstream->pop_callback(self->bitstream, NULL);
                self->bitstream->pop_callback(self->bitstream, NULL);
                PyErr_SetString(flac_exception(status), flac_strerror(status));
                return NULL;
            }
        }
        break;
    case LEFT_DIFFERENCE:
    case AVERAGE_DIFFERENCE:
        if ((status = skip_subframe(self->bitstream,
                                    frame_header.block_size,
                                    frame_header.bits_per_sample)) != OK) {
            self->bitstream->pop_callback(self->bitstream, NULL);
            self->bitstream->pop_callback(self->bitstream, NULL);
            PyErr_SetString(flac_exception(status), flac_strerror(status));
            return NULL;
        }
        if ((status = skip_subframe(self->bitstream,
                                    frame_header.block_size,
                                    frame_header.bits_per_sample + 1)) != OK) {
            self->bitstream->pop_callback(self->bitstream, NULL);
            self->bitstream->pop_callback(self->bitstream, NULL);
            PyErr_SetString(flac_exception(status), flac_strerror(status));
            return NULL;
        }
        break;
    case DIFFERENCE_RIGHT:
        if ((status = skip_subframe(self->bitstream,
                                    frame_header.block_size,
                                    frame_header.bits_per_sample + 1)) != OK) {
            self->bitstream->pop_callback(self->bitstream, NULL);
            self->bitstream->pop_callback(self->bitstream, NULL);
            PyErr_SetString(flac_exception(status), flac_strerror(status));
            return NULL;
        }
        if ((status = skip_subframe(self->bitstream,
                                    frame_header.block_size,
                                    frame_header.bits_per_sample)) != OK) {
            self->bitstream->pop_callback(self->bitstream, NULL);
            self->bitstream->pop_callback(self->bitstream, NULL);
            PyErr_SetString(flac_exception(status), flac_strerror(status));
            return NULL;
        }
        break;
    }

    /*validate CRC-16 in frame footer*/
    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->byte_align(self->bitstream);
        self->bitstream->skip(self->bitstream, 16); /*CRC-16 itself*/
        br_etry(self->bitstream);
    } else {
        br_etry(self->bitstream);
        self->bitstream->pop_callback(self->bitstream, NULL);
        self->bitstream->pop_callback(self->bitstream, NULL);
        PyErr_SetString(PyExc_IOError, "I/O error reading CRC-16");
        return NULL;
    }
    self->bitstream->pop_callback(self->bitstream, NULL);
    self->bitstream->pop_callback(self->bitstream, NULL);
    if (crc16) {
        PyErr_SetString(PyExc_ValueError, "frame CRC-16 mismatch");
        return NULL;
    }

    self->remaining_samples -= MIN(self->remaining_samples,
                                   frame_header.block_size);

    /*return tuple of frame size (in bytes) and block size (in samples)*/
    return Py_BuildValue("(I, I)", frame_size, frame_header.block_size);
}

static PyObject*
FlacDecoder_seek(decoders_FlacDecoder* self, PyObject *args)
{
    long long seeked_offset;

    const struct SEEKTABLE *seektable = &(self->seektable);
    uint64_t pcm_frames_offset = 0;
    uint64_t byte_offset = 0;
    unsigned i;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot seek closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "L", &seeked_offset))
        return NULL;

    if (seeked_offset < 0) {
        PyErr_SetString(PyExc_ValueError, "cannot seek to negative value");
        return NULL;
    }

    self->stream_finalized = 0;

    /*find latest seekpoint whose first sample is <= seeked_offset
      or 0 if there are no seekpoints in the seektable*/
    for (i = 0; i < seektable->total_points; i++) {
        if (seektable->seek_points[i].sample_number <= seeked_offset) {
            pcm_frames_offset = seektable->seek_points[i].sample_number;
            byte_offset = seektable->seek_points[i].frame_offset;
        } else {
            break;
        }
    }

    /*position bitstream to indicated value in file*/
    if (!setjmp(*br_try(self->bitstream))) {
        self->bitstream->setpos(self->bitstream, self->beginning_of_frames);
        while (byte_offset) {
            /*perform this in chunks in case seeked distance
              is longer than a "long" taken by fseek*/
            const uint64_t seek = MIN(byte_offset, LONG_MAX);
            self->bitstream->seek(self->bitstream,
                                  (long)seek,
                                  BS_SEEK_CUR);
            byte_offset -= seek;
        }
        br_etry(self->bitstream);
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error seeking in stream");
        return NULL;
    }

    /*reset stream's total remaining frames*/
    self->remaining_samples = (self->streaminfo.total_samples -
                               pcm_frames_offset);

    if (pcm_frames_offset == 0) {
        /*if pcm_frames_offset is 0, reset MD5 validation*/
        audiotools__MD5Init(&(self->md5));
        self->perform_validation = 1;
    } else {
        /*otherwise, disable MD5 validation altogether at end of stream*/
        self->perform_validation = 0;
    }

    /*return actual PCM frames position in file*/
    return Py_BuildValue("K", pcm_frames_offset);
}

/************************************
 * private function implementations *
 ************************************/

static int
valid_stream_id(BitstreamReader *r)
{
    unsigned char stream_id[4];
    const unsigned char valid_stream_id[4] = "fLaC";
    r->read_bytes(r, stream_id, 4);
    return (memcmp(stream_id, valid_stream_id, 4) == 0);
}

static void
read_block_header(BitstreamReader *r,
                  unsigned *last,
                  unsigned *type,
                  unsigned *size)
{
    r->parse(r, "1u 7u 24u", last, type, size);
}

static void
read_STREAMINFO(BitstreamReader *r, struct STREAMINFO *streaminfo)
{
    streaminfo->minimum_block_size = r->read(r, 16);
    streaminfo->maximum_block_size = r->read(r, 16);
    streaminfo->minimum_frame_size = r->read(r, 24);
    streaminfo->maximum_frame_size = r->read(r, 24);
    streaminfo->sample_rate = r->read(r, 20);
    streaminfo->channel_count = r->read(r, 3) + 1;
    streaminfo->bits_per_sample = r->read(r, 5) + 1;
    streaminfo->total_samples = r->read_64(r, 36);
    r->read_bytes(r, streaminfo->MD5, 16);
}

static void
read_SEEKTABLE(BitstreamReader *r,
               unsigned block_size,
               struct SEEKTABLE *seektable)
{
    const unsigned seekpoint_size = (64 + 64 + 16) / 8;
    unsigned i;

    seektable->total_points = block_size / seekpoint_size;
    seektable->seek_points =
        malloc(sizeof(struct SEEKPOINT) * seektable->total_points);
    for (i = 0; i < seektable->total_points; i++) {
        r->parse(r, "64U 64U 16u",
                 &(seektable->seek_points[i].sample_number),
                 &(seektable->seek_points[i].frame_offset),
                 &(seektable->seek_points[i].frame_samples));
    }
}

static void
read_VORBIS_COMMENT(BitstreamReader *r, unsigned *channel_mask)
{
    unsigned total_entries;
    const char channel_mask_key[] = "WAVEFORMATEXTENSIBLE_CHANNEL_MASK=";
    const size_t mask_key_len = strlen(channel_mask_key);
    char channel_mask_entry[] = "WAVEFORMATEXTENSIBLE_CHANNEL_MASK=0x0000";
    const size_t mask_entry_len = strlen(channel_mask_entry);

    r->set_endianness(r, BS_LITTLE_ENDIAN);

    /*ignore vendor string*/
    r->skip_bytes(r, r->read(r, 32));

    for (total_entries = r->read(r, 32);
         total_entries;
         total_entries--) {
        const unsigned entry_len = r->read(r, 32);
        if ((entry_len > mask_key_len) && (entry_len <= mask_entry_len)) {
            r->read_bytes(r, (uint8_t*)channel_mask_entry, entry_len);
            if (strncmp(channel_mask_key,
                        channel_mask_entry,
                        mask_key_len) == 0) {
                errno = 0;
                const unsigned long mask =
                    strtoul(channel_mask_entry + mask_key_len, NULL, 16);
                if ((mask != 0) || (errno == 0)) {
                    *channel_mask = (unsigned)mask;
                }
            }
        } else {
            r->skip_bytes(r, entry_len);
        }
    }

    r->set_endianness(r, BS_BIG_ENDIAN);
}

static status_t
read_frame_header(BitstreamReader *r,
                  const struct STREAMINFO *streaminfo,
                  struct frame_header *frame_header)
{
    uint8_t crc8 = 0;
    unsigned encoded_block_size;
    unsigned encoded_sample_rate;
    unsigned encoded_channels;
    unsigned encoded_bps;

    if (!setjmp(*br_try(r))) {
        status_t status;

        r->add_callback(r, (bs_callback_f)flac_crc8, &crc8);
        if (r->read(r, 14) != 0x3FFE) {
            br_etry(r);
            return INVALID_SYNC_CODE;
        }
        r->skip(r, 1);
        frame_header->blocking_strategy = r->read(r, 1);
        encoded_block_size = r->read(r, 4);
        encoded_sample_rate = r->read(r, 4);
        encoded_channels = r->read(r, 4);
        encoded_bps = r->read(r, 3);
        r->skip(r, 1);
        if ((status = read_utf8(r, &(frame_header->frame_number))) != OK) {
            br_etry(r);
            return status;
        }

        switch (encoded_block_size) {
        case 0:
        default:
            frame_header->block_size = streaminfo->maximum_block_size;
            break;
        case 1: frame_header->block_size = 192; break;
        case 2: frame_header->block_size = 576; break;
        case 3: frame_header->block_size = 1152; break;
        case 4: frame_header->block_size = 2304; break;
        case 5: frame_header->block_size = 4608; break;
        case 6: frame_header->block_size = r->read(r, 8) + 1; break;
        case 7: frame_header->block_size = r->read(r, 16) + 1; break;
        case 8: frame_header->block_size = 256; break;
        case 9: frame_header->block_size = 512; break;
        case 10: frame_header->block_size = 1024; break;
        case 11: frame_header->block_size = 2048; break;
        case 12: frame_header->block_size = 4096; break;
        case 13: frame_header->block_size = 8192; break;
        case 14: frame_header->block_size = 16384; break;
        case 15: frame_header->block_size = 32768; break;
        }
        if (frame_header->block_size > streaminfo->maximum_block_size) {
            br_etry(r);
            return BLOCK_SIZE_MISMATCH;
        }

        switch (encoded_sample_rate) {
        case 0:
        default:
            frame_header->sample_rate = streaminfo->sample_rate;
            break;
        case 1: frame_header->sample_rate = 88200; break;
        case 2: frame_header->sample_rate = 176400; break;
        case 3: frame_header->sample_rate = 192000; break;
        case 4: frame_header->sample_rate = 8000; break;
        case 5: frame_header->sample_rate = 16000; break;
        case 6: frame_header->sample_rate = 22050; break;
        case 7: frame_header->sample_rate = 24000; break;
        case 8: frame_header->sample_rate = 32000; break;
        case 9: frame_header->sample_rate = 44100; break;
        case 10: frame_header->sample_rate = 48000; break;
        case 11: frame_header->sample_rate = 96000; break;
        case 12: frame_header->sample_rate = r->read(r, 8) * 1000; break;
        case 13: frame_header->sample_rate = r->read(r, 16); break;
        case 14: frame_header->sample_rate = r->read(r, 16) * 10; break;
        case 15:
            br_etry(r);
            return INVALID_SAMPLE_RATE;
        }
        if (frame_header->sample_rate != streaminfo->sample_rate) {
            br_etry(r);
            return SAMPLE_RATE_MISMATCH;
        }

        switch (encoded_bps) {
        case 0:
        default:
            frame_header->bits_per_sample = streaminfo->bits_per_sample;
            break;
        case 1: frame_header->bits_per_sample = 8; break;
        case 2: frame_header->bits_per_sample = 12; break;
        case 4: frame_header->bits_per_sample = 16; break;
        case 5: frame_header->bits_per_sample = 20; break;
        case 6: frame_header->bits_per_sample = 24; break;
        case 3:
        case 7:
            br_etry(r);
            return INVALID_BPS;
        }
        if (frame_header->bits_per_sample != streaminfo->bits_per_sample) {
            br_etry(r);
            return BPS_MISMATCH;
        }

        switch (encoded_channels) {
        case 0:
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
        case 6:
        case 7:
            frame_header->channel_assignment = INDEPENDENT;
            frame_header->channel_count = encoded_channels + 1;
            break;
        case 8:
            frame_header->channel_assignment = LEFT_DIFFERENCE;
            frame_header->channel_count = 2;
            break;
        case 9:
            frame_header->channel_assignment = DIFFERENCE_RIGHT;
            frame_header->channel_count = 2;
            break;
        case 10:
            frame_header->channel_assignment = AVERAGE_DIFFERENCE;
            frame_header->channel_count = 2;
            break;
        default:
            br_etry(r);
            return INVALID_CHANNEL_ASSIGNMENT;
        }
        if (frame_header->channel_count != streaminfo->channel_count) {
            br_etry(r);
            return CHANNEL_COUNT_MISMATCH;
        }

        r->skip(r, 8); /*CRC-8*/
        br_etry(r);
        r->pop_callback(r, NULL);
        if (crc8) {
            return INVALID_CRC8;
        } else {
            return OK;
        }
    } else {
        br_etry(r);
        return IOERROR_HEADER;
    }
}

static status_t
read_utf8(BitstreamReader *r, unsigned *utf8)
{
    const unsigned count = r->read_unary(r, 0);
    unsigned i;
    *utf8 = r->read(r, 7 - count);
    if (count > 0) {
        for (i = 0; i < (count - 1); i++) {
            if (r->read(r, 2) == 2) {
                *utf8 = (*utf8 << 8) | (r->read(r, 6));
            } else {
                return INVALID_UTF8;
            }
        }
    }
    return OK;
}

static status_t
decode_independent(BitstreamReader *r,
                   const struct frame_header *frame_header,
                   int samples[])
{
    unsigned c;
    status_t status;
    for (c = 0; c < frame_header->channel_count; c++) {
        int channel_data[frame_header->block_size];
        if ((status = read_subframe(r,
                                    frame_header->block_size,
                                    frame_header->bits_per_sample,
                                    channel_data)) != OK) {
            return status;
        } else {
            put_channel_data(samples,
                             c,
                             frame_header->channel_count,
                             frame_header->block_size,
                             channel_data);
        }
    }

    return OK;
}

static status_t
decode_left_difference(BitstreamReader *r,
                       const struct frame_header *frame_header,
                       int samples[])
{
    status_t status;
    int left_data[frame_header->block_size];
    int difference_data[frame_header->block_size];
    int right_data[frame_header->block_size];

    if ((status = read_subframe(r,
                                frame_header->block_size,
                                frame_header->bits_per_sample,
                                left_data)) != OK) {
        return status;
    }

    if ((status = read_subframe(r,
                                frame_header->block_size,
                                frame_header->bits_per_sample + 1,
                                difference_data)) != OK) {
        return status;
    }

    decorrelate_left_difference(frame_header->block_size,
                                left_data,
                                difference_data,
                                right_data);

    put_channel_data(samples,
                     0,
                     2,
                     frame_header->block_size,
                     left_data);

    put_channel_data(samples,
                     1,
                     2,
                     frame_header->block_size,
                     right_data);

    return OK;
}

static status_t
decode_difference_right(BitstreamReader *r,
                        const struct frame_header *frame_header,
                        int samples[])
{
    status_t status;
    int difference_data[frame_header->block_size];
    int right_data[frame_header->block_size];
    int left_data[frame_header->block_size];

    if ((status = read_subframe(r,
                                frame_header->block_size,
                                frame_header->bits_per_sample + 1,
                                difference_data)) != OK) {
        return status;
    }

    if ((status = read_subframe(r,
                                frame_header->block_size,
                                frame_header->bits_per_sample,
                                right_data)) != OK) {
        return status;
    }

    decorrelate_difference_right(frame_header->block_size,
                                 difference_data,
                                 right_data,
                                 left_data);

    put_channel_data(samples,
                     0,
                     2,
                     frame_header->block_size,
                     left_data);

    put_channel_data(samples,
                     1,
                     2,
                     frame_header->block_size,
                     right_data);

    return OK;
}

static status_t
decode_average_difference(BitstreamReader *r,
                          const struct frame_header *frame_header,
                          int samples[])
{
    status_t status;
    int average_data[frame_header->block_size];
    int difference_data[frame_header->block_size];
    int right_data[frame_header->block_size];
    int left_data[frame_header->block_size];

    if ((status = read_subframe(r,
                                frame_header->block_size,
                                frame_header->bits_per_sample,
                                average_data)) != OK) {
        return status;
    }

    if ((status = read_subframe(r,
                                frame_header->block_size,
                                frame_header->bits_per_sample + 1,
                                difference_data)) != OK) {
        return status;
    }

    decorrelate_average_difference(frame_header->block_size,
                                   average_data,
                                   difference_data,
                                   left_data,
                                   right_data);

    put_channel_data(samples,
                     0,
                     2,
                     frame_header->block_size,
                     left_data);

    put_channel_data(samples,
                     1,
                     2,
                     frame_header->block_size,
                     right_data);

    return OK;
}

static status_t
read_subframe(BitstreamReader *r,
              unsigned block_size,
              unsigned bits_per_sample,
              int channel_data[])
{
    if (!setjmp(*br_try(r))) {
        subframe_type_t type;
        unsigned order;
        unsigned wasted_bps;
        status_t status;

        if ((status =
             read_subframe_header(r, &type, &order, &wasted_bps)) != OK) {
            br_etry(r);
            return status;
        } else {
            const unsigned effective_bps = bits_per_sample - wasted_bps;

            if (wasted_bps >= bits_per_sample) {
                br_etry(r);
                return INVALID_WASTED_BPS;
            }

            switch (type) {
            case CONSTANT:
                read_CONSTANT_subframe(r,
                                       block_size,
                                       effective_bps,
                                       channel_data);
                break;
            case VERBATIM:
                read_VERBATIM_subframe(r,
                                       block_size,
                                       effective_bps,
                                       channel_data);
                break;
            case FIXED:
                if ((status =
                     read_FIXED_subframe(r,
                                         block_size,
                                         effective_bps,
                                         order,
                                         channel_data)) != OK) {
                    br_etry(r);
                    return status;
                }
                break;
            case LPC:
                if ((status =
                     read_LPC_subframe(r,
                                       block_size,
                                       effective_bps,
                                       order,
                                       channel_data)) != OK) {
                    br_etry(r);
                    return status;
                }
                break;
            }
            br_etry(r);
            if (wasted_bps) {
                unsigned i;
                for (i = 0; i < block_size; i++) {
                    channel_data[i] <<= wasted_bps;
                }
            }
            return OK;
        }
    } else {
        br_etry(r);
        return IOERROR_SUBFRAME;
    }
}

static status_t
read_subframe_header(BitstreamReader *r,
                     subframe_type_t *type,
                     unsigned *order,
                     unsigned *wasted_bps)
{
    unsigned type_and_order;
    unsigned has_wasted_bps;

    r->skip(r, 1);
    type_and_order = r->read(r, 6);
    has_wasted_bps = r->read(r, 1);
    if (has_wasted_bps) {
        *wasted_bps = r->read_unary(r, 1) + 1;
    } else {
        *wasted_bps = 0;
    }
    if (type_and_order == 0) {
        *type = CONSTANT;
        return OK;
    } else if (type_and_order == 1) {
        *type = VERBATIM;
        return OK;
    } else if ((8 <= type_and_order) && (type_and_order <= 12)) {
        *type = FIXED;
        *order = type_and_order - 8;
        return OK;
    } else if ((32 <= type_and_order) && (type_and_order <= 63)) {
        *type = LPC;
        *order = type_and_order - 31;
        return OK;
    } else {
        return INVALID_SUBFRAME_HEADER;
    }
}

static void
read_CONSTANT_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[])
{
    const int constant = r->read_signed(r, bits_per_sample);
    for (; block_size; block_size--) {
        samples[0] = constant;
        samples += 1;
    }
}

static void
read_VERBATIM_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample,
                       int samples[])
{
    for (; block_size; block_size--) {
        samples[0] = r->read_signed(r, bits_per_sample);
        samples += 1;
    }
}

static status_t
read_FIXED_subframe(BitstreamReader *r,
                    unsigned block_size,
                    unsigned bits_per_sample,
                    unsigned predictor_order,
                    int samples[])
{
    if ((predictor_order > 4) || (predictor_order > block_size)) {
        return INVALID_FIXED_ORDER;
    } else {
        unsigned i;
        int residuals[block_size - predictor_order];
        status_t status;

        /*warm-up samples*/
        for (i = 0; i < predictor_order; i++) {
            samples[i] = r->read_signed(r, bits_per_sample);
        }

        /*residuals*/
        if ((status = read_residual_block(r,
                                          block_size,
                                          predictor_order,
                                          residuals)) != OK) {
            return status;
        }

        switch (predictor_order) {
        case 0:
            for (i = 0; i < block_size; i++) {
                samples[i] = residuals[i];
            }
            return OK;
        case 1:
            for (i = 1; i < block_size; i++) {
                samples[i] = samples[i - 1] + residuals[i - 1];
            }
            return OK;
        case 2:
            for (i = 2; i < block_size; i++) {
                samples[i] = (2 * samples[i - 1]) -
                             samples[i - 2] +
                             residuals[i - 2];
            }
            return OK;
        case 3:
            for (i = 3; i < block_size; i++) {
                samples[i] = (3 * samples[i - 1]) -
                             (3 * samples[i - 2]) +
                             samples[i - 3] +
                             residuals[i - 3];
            }
            return OK;
        case 4:
            for (i = 4; i < block_size; i++) {
                samples[i] = (4 * samples[i - 1]) -
                             (6 * samples[i - 2]) +
                             (4 * samples[i - 3]) -
                             samples[i - 4] +
                             residuals[i - 4];
            }
            return OK;
        default:
            return INVALID_FIXED_ORDER;
        }
    }
}

static status_t
read_LPC_subframe(BitstreamReader *r,
                  unsigned block_size,
                  unsigned bits_per_sample,
                  unsigned predictor_order,
                  int samples[])
{
    if (predictor_order > block_size) {
        return INVALID_LPC_ORDER;
    } else {
        unsigned i;
        unsigned precision;
        int shift;
        int coefficient[predictor_order];
        int residuals[block_size - predictor_order];
        status_t status;

        /*warm-up samples*/
        for (i = 0; i < predictor_order; i++) {
            samples[i] = r->read_signed(r, bits_per_sample);
        }

        precision = r->read(r, 4) + 1;
        shift = r->read_signed(r, 5);
        if (shift < 0) {
            shift = 0;
        }

        /*coefficients*/
        for (i = 0; i < predictor_order; i++) {
            coefficient[i] = r->read_signed(r, precision);
        }

        if ((status = read_residual_block(r,
                                          block_size,
                                          predictor_order,
                                          residuals)) != OK) {
            return status;
        }

        for (i = predictor_order; i < block_size; i++) {
            int64_t sum = 0;
            unsigned j;
            for (j = 0; j < predictor_order; j++) {
                sum += (int64_t)coefficient[j] * (int64_t)samples[i - j - 1];
            }
            sum >>= shift;
            samples[i] = (int)sum + residuals[i - predictor_order];
        }

        return OK;
    }
}

static status_t
read_residual_block(BitstreamReader *r,
                    unsigned block_size,
                    unsigned predictor_order,
                    int residuals[])
{
    br_read_f read = r->read;
    br_read_unary_f read_unary = r->read_unary;
    const unsigned coding_method = r->read(r, 2);
    const unsigned partition_order = r->read(r, 4);
    const unsigned partition_count = 1 << partition_order;
    unsigned rice_bits;
    unsigned i = 0;
    unsigned p;

    if (coding_method == 0) {
        rice_bits = 4;
    } else if (coding_method == 1) {
        rice_bits = 5;
    } else {
        return INVALID_CODING_METHOD;
    }

    if ((block_size % partition_count) ||
        (predictor_order > (block_size / partition_count))) {
        return INVALID_PARTITION_ORDER;
    }

    for (p = 0; p < partition_count; p++) {
        const unsigned rice = r->read(r, rice_bits);
        const unsigned partition_size = block_size / partition_count -
                                        (p == 0 ? predictor_order : 0);
        register unsigned j;
        if (((coding_method == 0) && (rice == 15)) ||
            ((coding_method == 1) && (rice == 31))) {
            const unsigned escape_code = read(r, 5);
            br_read_signed_f read_signed = r->read_signed;
            for (j = 0; j < partition_size; j++) {
                residuals[i++] = read_signed(r, escape_code);
            }
        } else {
            for (j = 0; j < partition_size; j++) {
                const unsigned MSB = read_unary(r, 1);
                const unsigned LSB = read(r, rice);
                const unsigned unsigned_ = (MSB << rice) | LSB;
                residuals[i++] = (unsigned_ % 2) ?
                                 (-(unsigned_ >> 1) - 1) :
                                 (unsigned_ >> 1);
            }
        }
    }

    return OK;
}

static void
decorrelate_left_difference(unsigned block_size,
                            const int left[],
                            const int difference[],
                            int right[])
{
    for (; block_size; block_size--) {
        right[0] = left[0] - difference[0];
        left += 1;
        right += 1;
        difference += 1;
    }
}

static void
decorrelate_difference_right(unsigned block_size,
                             const int difference[],
                             const int right[],
                             int left[])
{
    for (; block_size; block_size--) {
        left[0] = difference[0] + right[0];
        difference += 1;
        right += 1;
        left += 1;
    }
}

static void
decorrelate_average_difference(unsigned block_size,
                               const int average[],
                               const int difference[],
                               int left[],
                               int right[])
{
    for (; block_size; block_size--) {
        const int sum = (average[0] * 2) + (abs(difference[0]) % 2);
        left[0] = (sum + difference[0]) >> 1;
        right[0] = (sum - difference[0]) >> 1;
        average += 1;
        difference += 1;
        left += 1;
        right += 1;
    }
}

static status_t
skip_subframe(BitstreamReader *r,
              unsigned block_size,
              unsigned bits_per_sample)
{
    if (!setjmp(*br_try(r))) {
        subframe_type_t type;
        unsigned order;
        unsigned wasted_bps;
        status_t status;

        if ((status =
             read_subframe_header(r, &type, &order, &wasted_bps)) != OK) {
            br_etry(r);
            return status;
        } else {
            const unsigned effective_bps = bits_per_sample - wasted_bps;
            switch (type) {
            case CONSTANT:
                skip_CONSTANT_subframe(r, effective_bps);
                break;
            case VERBATIM:
                skip_VERBATIM_subframe(r, block_size, effective_bps);
                break;
            case FIXED:
                if ((status =
                     skip_FIXED_subframe(r,
                                         block_size,
                                         effective_bps,
                                         order)) != OK) {
                    return status;
                }
                break;
            case LPC:
                if ((status =
                     skip_LPC_subframe(r,
                                       block_size,
                                       effective_bps,
                                       order)) != OK) {
                    return status;
                }
                break;
            }
            br_etry(r);
            return OK;
        }
    } else {
        br_etry(r);
        return IOERROR_SUBFRAME;
    }
}

static void
skip_CONSTANT_subframe(BitstreamReader *r,
                       unsigned bits_per_sample)
{
    r->skip(r, bits_per_sample);
}

static void
skip_VERBATIM_subframe(BitstreamReader *r,
                       unsigned block_size,
                       unsigned bits_per_sample)
{
    r->skip(r, block_size * bits_per_sample);
}

static status_t
skip_FIXED_subframe(BitstreamReader *r,
                    unsigned block_size,
                    unsigned bits_per_sample,
                    unsigned predictor_order)
{
    if ((predictor_order > 4) || (predictor_order > block_size)) {
        return INVALID_FIXED_ORDER;
    } else {
        /*warm-up samples*/
        r->skip(r, predictor_order * bits_per_sample);
        return skip_residual_block(r, block_size, predictor_order);
    }
}

static status_t
skip_LPC_subframe(BitstreamReader *r,
                  unsigned block_size,
                  unsigned bits_per_sample,
                  unsigned predictor_order)
{
    if (predictor_order >= block_size) {
        return INVALID_LPC_ORDER;
    } else {
        unsigned precision;

        /*warm-up samples*/
        r->skip(r, predictor_order * bits_per_sample);
        precision = r->read(r, 4) + 1;
        r->skip(r, 5);
        /*coefficients*/
        r->skip(r, predictor_order * precision);
        return skip_residual_block(r, block_size, predictor_order);
    }
}

static status_t
skip_residual_block(BitstreamReader *r,
                    unsigned block_size,
                    unsigned predictor_order)
{
    br_skip_f skip = r->skip;
    br_skip_unary_f skip_unary = r->skip_unary;
    const unsigned coding_method = r->read(r, 2);
    const unsigned partition_order = r->read(r, 4);
    const unsigned partition_count = 1 << partition_order;
    unsigned rice_bits;
    unsigned p;

    if (coding_method == 0) {
        rice_bits = 4;
    } else if (coding_method == 1) {
        rice_bits = 5;
    } else {
        return INVALID_CODING_METHOD;
    }

    for (p = 0; p < partition_count; p++) {
        const unsigned rice = r->read(r, rice_bits);
        const unsigned partition_size = block_size / partition_count -
                                        (p == 0 ? predictor_order : 0);
        register unsigned j;
        if (((coding_method == 0) && (rice == 15)) ||
            ((coding_method == 1) && (rice == 31))) {
            const unsigned escape_code = r->read(r, 5);
            r->skip(r, partition_size * escape_code);
        } else {
            for (j = 0; j < partition_size; j++) {
                skip_unary(r, 1);
                skip(r, rice);
            }
        }
    }

    return OK;

}

static void
update_md5sum(audiotools__MD5Context *md5sum,
              const int pcm_data[],
              unsigned channels,
              unsigned bits_per_sample,
              unsigned pcm_frames)
{
    const unsigned bytes_per_sample = bits_per_sample / 8;
    unsigned total_samples = pcm_frames * channels;
    const unsigned buffer_size = total_samples * bytes_per_sample;
    unsigned char buffer[buffer_size];
    unsigned char *output_buffer = buffer;
    void (*converter)(int, unsigned char *) =
        int_to_pcm_converter(bits_per_sample, 0, 1);

    for (; total_samples; total_samples--) {
        converter(*pcm_data, output_buffer);
        pcm_data += 1;
        output_buffer += bytes_per_sample;
    }

    audiotools__MD5Update(md5sum, buffer, buffer_size);
}

static int
verify_md5sum(audiotools__MD5Context *stream_md5,
              const uint8_t streaminfo_md5[])
{
    unsigned char digest[16];
    audiotools__MD5Final(digest, stream_md5);
    return (memcmp(digest, streaminfo_md5, 16) == 0);
}

PyObject*
flac_exception(status_t status)
{
    switch (status) {
    case OK:
    default:
    case INVALID_SYNC_CODE:
    case INVALID_SAMPLE_RATE:
    case INVALID_BPS:
    case INVALID_CHANNEL_ASSIGNMENT:
    case INVALID_UTF8:
    case INVALID_CRC8:
    case INVALID_SUBFRAME_HEADER:
    case INVALID_FIXED_ORDER:
    case INVALID_LPC_ORDER:
    case INVALID_CODING_METHOD:
    case INVALID_WASTED_BPS:
    case INVALID_PARTITION_ORDER:
    case BLOCK_SIZE_MISMATCH:
    case SAMPLE_RATE_MISMATCH:
    case BPS_MISMATCH:
    case CHANNEL_COUNT_MISMATCH:
        return PyExc_ValueError;
    case IOERROR_HEADER:
    case IOERROR_SUBFRAME:
        return PyExc_IOError;
    }
}

const char*
flac_strerror(status_t status)
{
    switch (status) {
    default:
        return "undefined error";
    case OK:
        return "OK";
    case INVALID_SYNC_CODE:
        return "invalid sync code in frame header";
    case INVALID_SAMPLE_RATE:
        return "invalid sample rate in frame header";
    case INVALID_BPS:
        return "invalid bits-per-sample in frame header";
    case INVALID_CHANNEL_ASSIGNMENT:
        return "invalid channel assignment in frame header";
    case INVALID_UTF8:
        return "invalid UTF-8 value in frame header";
    case INVALID_CRC8:
        return "invalid CRC-8 in frame header";
    case IOERROR_HEADER:
        return "I/O error reading frame header";
    case IOERROR_SUBFRAME:
        return "I/O error reading subframe data";
    case INVALID_SUBFRAME_HEADER:
        return "invalid subframe header";
    case INVALID_FIXED_ORDER:
        return "invalid FIXED subframe order";
    case INVALID_LPC_ORDER:
        return "invalid LPC subframe order";
    case INVALID_CODING_METHOD:
        return "invalid coding method";
    case INVALID_WASTED_BPS:
        return "invalid wasted BPS in subframe header";
    case INVALID_PARTITION_ORDER:
        return "invalid residual partition order";
    case BLOCK_SIZE_MISMATCH:
        return "frame header block size larger than maximum";
    case SAMPLE_RATE_MISMATCH:
        return "frame header sample rate mismatch";
    case BPS_MISMATCH:
        return "frame header bits-per-sample mismatch";
    case CHANNEL_COUNT_MISMATCH:
        return "frame header channel count mismatch";
    }
}
