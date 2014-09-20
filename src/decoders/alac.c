#include "alac.h"
#include "../pcmconv.h"
#include <string.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

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

#ifndef STANDALONE
int
ALACDecoder_init(decoders_ALACDecoder *self,
                 PyObject *args, PyObject *kwds)
{
    enum {FILE_START};
    char *filename;
    static char *kwlist[] = {"filename", NULL};
    status status;
    unsigned i;

    self->filename = NULL;
    self->file = NULL;
    self->bitstream = NULL;
    self->audiotools_pcm = NULL;

    self->seektable = a_obj_new((ARRAY_COPY_FUNC)alac_seektable_copy,
                                free,
                                (ARRAY_PRINT_FUNC)alac_seektable_print);

    self->frameset_channels = aa_int_new();
    self->frame_channels = aa_int_new();
    self->uncompressed_LSBs = a_int_new();
    self->residuals = a_int_new();

    for (i = 0; i < MAX_CHANNELS; i++) {
        self->subframe_headers[i].qlp_coeff = a_int_new();
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &filename))
        return -1;

    /*open the alac file as a BitstreamReader*/
    if ((self->file = fopen(filename, "rb")) == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_IOError, filename);
        return -1;
    } else {
        self->bitstream = br_open(self->file, BS_BIG_ENDIAN);
    }
    self->filename = strdup(filename);

    self->bitstream->mark(self->bitstream, FILE_START);

    if ((status = parse_decoding_parameters(self)) != OK) {
        PyErr_SetString(alac_exception(status), alac_strerror(status));
        self->bitstream->unmark(self->bitstream, FILE_START);
        return -1;
    } else {
        self->bitstream->rewind(self->bitstream, FILE_START);
    }

    /*seek to the 'mdat' atom, which contains the ALAC stream*/
    if (seek_mdat(self->bitstream) == IO_ERROR) {
        self->bitstream->unmark(self->bitstream, FILE_START);
        PyErr_SetString(PyExc_IOError,
                        "Unable to locate 'mdat' atom in stream");
        return -1;
    } else {
        self->bitstream->unmark(self->bitstream, FILE_START);
        /*if seektable is empty, populate it with a single
          entry containing the offset to the start of mdat*/
        if (self->seektable->len == 0) {
            struct alac_seektable entry = {0, (unsigned)ftell(self->file)};
            self->seektable->append(self->seektable, &entry);
        }
    }

    /*setup a framelist generator function*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    /*mark stream as not closed and ready for reading*/
    self->closed = 0;

    return 0;
}

void
ALACDecoder_dealloc(decoders_ALACDecoder *self)
{
    int i;

    if (self->filename != NULL)
        free(self->filename);

    if (self->bitstream != NULL)
        /*this closes self->file also*/
        self->bitstream->close(self->bitstream);

    for (i = 0; i < MAX_CHANNELS; i++)
        self->subframe_headers[i].qlp_coeff->del(
            self->subframe_headers[i].qlp_coeff);

    self->seektable->del(self->seektable);

    self->frameset_channels->del(self->frameset_channels);
    self->frame_channels->del(self->frame_channels);
    self->uncompressed_LSBs->del(self->uncompressed_LSBs);
    self->residuals->del(self->residuals);

    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject*
ALACDecoder_new(PyTypeObject *type,
                PyObject *args, PyObject *kwds)
{
    decoders_ALACDecoder *self;

    self = (decoders_ALACDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
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
    switch (self->channels) {
    case 1:
        return Py_BuildValue("I", 0x0004);
    case 2:
        return Py_BuildValue("I", 0x0003);
    case 3:
        return Py_BuildValue("I", 0x0007);
    case 4:
        return Py_BuildValue("I", 0x0107);
    case 5:
        return Py_BuildValue("I", 0x0037);
    case 6:
        return Py_BuildValue("I", 0x003F);
    case 7:
        return Py_BuildValue("I", 0x013F);
    case 8:
        return Py_BuildValue("I", 0x00FF);
    default:
        return Py_BuildValue("I", 0x0000);
    }
}

static PyObject*
ALACDecoder_read(decoders_ALACDecoder* self, PyObject *args)
{
    unsigned channel_count;
    BitstreamReader* mdat = self->bitstream;
    aa_int* frameset_channels = self->frameset_channels;
    PyThreadState *thread_state;

    if (self->closed) {
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    /*return an empty framelist if total samples are exhausted*/
    if (self->remaining_frames == 0) {
        return empty_FrameList(self->audiotools_pcm,
                               self->channels,
                               self->bits_per_sample);
    }

    thread_state = PyEval_SaveThread();

    if (!setjmp(*br_try(mdat))) {
        frameset_channels->reset(frameset_channels);

        /*get initial frame's channel count*/
        channel_count = mdat->read(mdat, 3) + 1;
        while (channel_count != 8) {
            status status;

            /*read a frame from the frameset into "channels"*/
            if ((status = read_frame(self,
                                     mdat,
                                     frameset_channels,
                                     channel_count)) != OK) {
                br_etry(mdat);
                PyEval_RestoreThread(thread_state);
                PyErr_SetString(alac_exception(status), alac_strerror(status));
                return NULL;
            } else {
                /*ensure all frames have the same sample count*/
                /*FIXME*/

                /*read the channel count of the next frame
                  in the frameset, if any*/
                channel_count = mdat->read(mdat, 3) + 1;
            }
        }

        /*once all the frames in the frameset are read,
          byte-align the output stream*/
        mdat->byte_align(mdat);
        br_etry(mdat);
        PyEval_RestoreThread(thread_state);

        /*decrement the remaining sample count*/
        self->remaining_frames -= MIN(self->remaining_frames,
                                      frameset_channels->_[0]->len);

        /*convert ALAC channel assignment to standard audiotools assignment*/
        alac_order_to_wave_order(frameset_channels);

        /*finally, build and return framelist object from the sample data*/
        return aa_int_to_FrameList(self->audiotools_pcm,
                                   frameset_channels,
                                   self->bits_per_sample);
    } else {
        br_etry(mdat);
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_IOError, "EOF during frame reading");
        return NULL;
    }
}

static PyObject*
ALACDecoder_seek(decoders_ALACDecoder* self, PyObject *args)
{
    long long seeked_offset;
    struct alac_seektable *best_offset = NULL;
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

    /*walk through seektable and find the latest offset
      whose PCM index is <= the seeked offset*/
    for (i = 0; i < self->seektable->len; i++) {
        struct alac_seektable *offset = self->seektable->_[i];
        if (offset->pcm_frames_offset <= seeked_offset) {
            best_offset = offset;
        } else {
            break;
        }
    }

    if (best_offset == NULL) {
        PyErr_SetString(PyExc_ValueError, "no offset found in seektable");
        return NULL;
    }

    /*update the remaining frames value based on the latest offset*/
    self->remaining_frames = (self->total_frames -
                              best_offset->pcm_frames_offset);

    /*seek to the absolute position in file*/
    fseek(self->file, (long)(best_offset->absolute_file_offset), SEEK_SET);

    /*return the latest offset seeked to*/
    return Py_BuildValue("I", best_offset->pcm_frames_offset);
}

static PyObject*
ALACDecoder_close(decoders_ALACDecoder* self, PyObject *args)
{
    /*mark stream as closed so more calls to read()
      generate ValueErrors*/
    self->closed = 1;

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

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject*
alac_exception(status status)
{
    switch (status) {
    case IO_ERROR:
        return PyExc_IOError;
    case INVALID_UNUSED_BITS:
    case INVALID_ALAC_ATOM:
    case INVALID_MDHD_ATOM:
    case MDIA_NOT_FOUND:
    case STSD_NOT_FOUND:
    case MDHD_NOT_FOUND:
    case INVALID_SEEKTABLE:
        return PyExc_ValueError;
    default:
        /*this shouldn't happen*/
        return PyExc_ValueError;
    }
}

#else

#include <errno.h>

int
ALACDecoder_init(decoders_ALACDecoder *self, char *filename)
{
    enum {FILE_START};
    unsigned i;
    status status;

    self->seektable = a_obj_new((ARRAY_COPY_FUNC)alac_seektable_copy,
                                free,
                                (ARRAY_PRINT_FUNC)alac_seektable_print);

    self->frameset_channels = aa_int_new();
    self->frame_channels = aa_int_new();
    self->uncompressed_LSBs = a_int_new();
    self->residuals = a_int_new();

    for (i = 0; i < MAX_CHANNELS; i++) {
        self->subframe_headers[i].qlp_coeff = a_int_new();
    }

    if ((self->file = fopen(filename, "rb")) == NULL) {
        fprintf(stderr, "*** %s: %s\n", filename, strerror(errno));
        return -1;
    } else {
        self->bitstream = br_open(self->file, BS_BIG_ENDIAN);
    }
    self->filename = strdup(filename);

    self->bitstream->mark(self->bitstream, FILE_START);

    if ((status = parse_decoding_parameters(self)) != OK) {
        fprintf(stderr, "*** Error: %s\n", alac_strerror(status));
        self->bitstream->unmark(self->bitstream, FILE_START);
        return -1;
    } else {
        self->bitstream->rewind(self->bitstream, FILE_START);
    }

    /*seek to the 'mdat' atom, which contains the ALAC stream*/
    if (seek_mdat(self->bitstream) == IO_ERROR) {
        self->bitstream->unmark(self->bitstream, FILE_START);
        fprintf(stderr, "Unable to locate 'mdat' atom in stream\n");
        return -1;
    } else {
        self->bitstream->unmark(self->bitstream, FILE_START);
    }

    return 0;
}

void
ALACDecoder_dealloc(decoders_ALACDecoder *self)
{
    int i;

    if (self->filename != NULL)
        free(self->filename);

    if (self->bitstream != NULL)
        /*this closes self->file also*/
        self->bitstream->close(self->bitstream);

    for (i = 0; i < MAX_CHANNELS; i++)
        self->subframe_headers[i].qlp_coeff->del(
            self->subframe_headers[i].qlp_coeff);

    self->seektable->del(self->seektable);

    self->frameset_channels->del(self->frameset_channels);
    self->frame_channels->del(self->frame_channels);
    self->uncompressed_LSBs->del(self->uncompressed_LSBs);
    self->residuals->del(self->residuals);
}
#endif

const char*
alac_strerror(status status)
{
    switch (status) {
    case IO_ERROR:
        return "I/O Errror";
    case INVALID_UNUSED_BITS:
        return "invalid unused bits";
    case INVALID_ALAC_ATOM:
        return "invalid alac atom";
    case INVALID_MDHD_ATOM:
        return "invalid mdhd atom";
    case MDIA_NOT_FOUND:
        return "mdia atom not found";
    case STSD_NOT_FOUND:
        return "stsd atom not found";
    case MDHD_NOT_FOUND:
        return "mdhd atom not found";
    case INVALID_SEEKTABLE:
        return "invalid seektable entries";
    default:
        /*this shouldn't happen*/
        return "no error";
    }
}

static status
parse_decoding_parameters(decoders_ALACDecoder *self)
{
    enum {MDIA_START};
    BitstreamReader* mdia_atom = br_substream_new(BS_BIG_ENDIAN);
    BitstreamReader* atom = br_substream_new(BS_BIG_ENDIAN);
    a_obj* block_sizes = a_obj_new((ARRAY_COPY_FUNC)alac_stts_copy,
                                   free,
                                   (ARRAY_PRINT_FUNC)alac_stts_print);
    a_obj* chunk_sizes = a_obj_new((ARRAY_COPY_FUNC)alac_stsc_copy,
                                   free,
                                   (ARRAY_PRINT_FUNC)alac_stsc_print);
    a_unsigned* chunk_offsets = a_unsigned_new();
    unsigned mdia_atom_size;
    unsigned atom_size;
    int stts_found;
    int stsc_found;
    int stco_found;
    status status = OK;

    /*find the mdia atom, which is the parent to stsd and mdhd*/
    if (find_sub_atom(self->bitstream, mdia_atom, &mdia_atom_size,
                      "moov", "trak", "mdia", NULL)) {
        status = MDIA_NOT_FOUND;
        goto error;
    } else {
        /*mark the mdia atom so we can parse
          several different trees from it*/
        mdia_atom->mark(mdia_atom, MDIA_START);
    }

    /*find and parse the alac atom,
      which contains lots of crucial decoder details*/
    br_substream_reset(atom);
    if (find_sub_atom(mdia_atom, atom, &atom_size,
                      "minf", "stbl", "stsd", NULL)) {
        status = STSD_NOT_FOUND;
        goto error;
    } else if ((status = read_alac_atom(atom,
                                        &(self->max_samples_per_frame),
                                        &(self->bits_per_sample),
                                        &(self->history_multiplier),
                                        &(self->initial_history),
                                        &(self->maximum_k),
                                        &(self->channels),
                                        &(self->sample_rate))) != OK) {
        goto error;
    }

    /*find and parse the mdhd atom, which contains our total frame count*/
    mdia_atom->rewind(mdia_atom, MDIA_START);
    br_substream_reset(atom);
    if (find_sub_atom(mdia_atom, atom, &atom_size,
                      "mdhd", NULL)) {
        status = MDHD_NOT_FOUND;
        goto error;
    } else if ((status = read_mdhd_atom(atom,
                                        &(self->total_frames))) != OK) {
        goto error;
    } else {
        self->remaining_frames = self->total_frames;
    }

    /*if any seektable atoms aren't found or are invalid,
      skip building the seektable entirely
      and populate it with a single entry
      that rewinds to the start of the mdat atom*/

    /*find and parse the stts atom, which contains our block sizes*/
    mdia_atom->rewind(mdia_atom, MDIA_START);
    br_substream_reset(atom);
    stts_found = (!find_sub_atom(mdia_atom, atom, &atom_size,
                                 "minf", "stbl", "stts", NULL) &&
                  (read_stts_atom(atom, block_sizes) == OK));

    /*find and parse the stsc atom, which contains our chunk sizes*/
    mdia_atom->rewind(mdia_atom, MDIA_START);
    br_substream_reset(atom);
    stsc_found = (!find_sub_atom(mdia_atom, atom, &atom_size,
                                 "minf", "stbl", "stsc", NULL) &&
                  (read_stsc_atom(atom, chunk_sizes) == OK));

    /*parse the stco atom, which contains our chunk offsets*/
    mdia_atom->rewind(mdia_atom, MDIA_START);
    br_substream_reset(atom);
    stco_found = (!find_sub_atom(mdia_atom, atom, &atom_size,
                                 "minf", "stbl", "stco", NULL) &&
                  (read_stco_atom(atom, chunk_offsets) == OK));

    if (stts_found && stsc_found && stco_found) {
        /*ensure total number of PCM frames in stts
          (based on block size and frame count)
          matches the total number of PCM frames in the alac atom*/
        unsigned frame_sizes_sum = 0;
        unsigned i;
        for (i = 0; i < block_sizes->len; i++) {
            const struct alac_stts *stts = block_sizes->_[i];
            frame_sizes_sum += (stts->frame_count * stts->frame_duration);
        }
        if (frame_sizes_sum != self->total_frames) {
            status = INVALID_SEEKTABLE;
            goto error;
        }

        /*once all the component seektable atoms are parsed,
          assemble them into a complete seektable*/
        if ((status = populate_seektable(block_sizes,
                                         chunk_sizes,
                                         chunk_offsets,
                                         self->seektable)) != OK) {
            goto error;
        }
    }

    status = OK;

error:
    /*perform cleanup of temporary buffers and arrays*/
    if (mdia_atom->has_mark(mdia_atom, MDIA_START))
        mdia_atom->unmark(mdia_atom, MDIA_START);
    mdia_atom->close(mdia_atom);
    atom->close(atom);
    block_sizes->del(block_sizes);
    chunk_sizes->del(chunk_sizes);
    chunk_offsets->del(chunk_offsets);

    return status;
}

static status
populate_seektable(a_obj* block_sizes,
                   a_obj* chunk_sizes,
                   a_unsigned* chunk_offsets,
                   a_obj* seektable)
{
    unsigned i;
    a_unsigned* frame_sizes = a_unsigned_new();
    l_unsigned* frame_sizes_l = l_unsigned_new();
    l_unsigned* chunk_frames = l_unsigned_new();
    a_unsigned* chunk_lengths = a_unsigned_new();
    unsigned pcm_frames_offset = 0;
    status status = OK;

    /*expand the frame count/frame duration atom
      into a single list of ALAC frame sizes, in PCM frames
      then link to it for easier tearing apart*/
    for (i = 0; i < block_sizes->len; i++) {
        struct alac_stts *stts = block_sizes->_[i];
        frame_sizes->mappend(frame_sizes,
                             stts->frame_count,
                             stts->frame_duration);
    }
    frame_sizes->link(frame_sizes, frame_sizes_l);
    /*ensure there's at least one frame_sizes entry*/
    if (frame_sizes->len == 0) {
        status = INVALID_SEEKTABLE;
        goto error;
    }

    /*ensure there's at least one chunk_sizes entry*/
    if (chunk_sizes->len == 0) {
        status = INVALID_SEEKTABLE;
        goto error;
    }

    for (i = 0; i < chunk_sizes->len; i++) {
        struct alac_stsc *stsc = chunk_sizes->_[i];

        if (stsc->ALAC_frames_per_chunk == 0) {
            status = INVALID_SEEKTABLE;
            goto error;
        }

        if ((i + 1) < chunk_sizes->len) {
            /*if there's a next chunk size,
              pull "ALAC_frames_per_chunk" ALAC frames from frame_sizes
              for all chunks between this size and the next size*/
            struct alac_stsc *next_stsc = chunk_sizes->_[i + 1];
            unsigned j;
            for (j = stsc->first_chunk; j < next_stsc->first_chunk; j++) {
                frame_sizes_l->split(frame_sizes_l,
                                     stsc->ALAC_frames_per_chunk,
                                     chunk_frames,
                                     frame_sizes_l);
                /*ensure chunk_frames has the requested number of ALAC frames*/
                if (chunk_frames->len == stsc->ALAC_frames_per_chunk) {
                    chunk_lengths->append(chunk_lengths,
                                          chunk_frames->sum(chunk_frames));
                } else {
                    status = INVALID_SEEKTABLE;
                    goto error;
                }
            }
        } else {
            /*if there's no next size,
              all remaining chunks are the size of this one*/

            while (frame_sizes_l->len > 0) {
                frame_sizes_l->split(frame_sizes_l,
                                     stsc->ALAC_frames_per_chunk,
                                     chunk_frames,
                                     frame_sizes_l);
                /*ensure chunk_frames has the requested number of ALAC frames*/
                if (chunk_frames->len == stsc->ALAC_frames_per_chunk) {
                    chunk_lengths->append(chunk_lengths,
                                          chunk_frames->sum(chunk_frames));
                } else {
                    status = INVALID_SEEKTABLE;
                    goto error;
                }
            }
        }
    }

    /*ensure number of chunk_lengths equals number of chunk_offsets*/
    if (chunk_lengths->len != chunk_offsets->len) {
        status = INVALID_SEEKTABLE;
        goto error;
    }

    seektable->reset_for(seektable, chunk_lengths->len);
    for (i = 0; i < chunk_lengths->len; i++) {
        struct alac_seektable entry = {pcm_frames_offset,
                                       chunk_offsets->_[i]};
        seektable->append(seektable, &entry);
        pcm_frames_offset += chunk_lengths->_[i];
    }

error:
    frame_sizes->del(frame_sizes);
    frame_sizes_l->del(frame_sizes_l);
    chunk_frames->del(chunk_frames);
    chunk_lengths->del(chunk_lengths);

    return status;
}

static struct alac_stts*
alac_stts_copy(struct alac_stts* stts)
{
    struct alac_stts* new_stts = malloc(sizeof(struct alac_stts));
    new_stts->frame_count = stts->frame_count;
    new_stts->frame_duration = stts->frame_duration;
    return new_stts;
}

static void
alac_stts_print(struct alac_stts* stts, FILE* output)
{
    fprintf(output, "STTS(%u, %u)", stts->frame_count, stts->frame_duration);
}

static struct alac_stsc*
alac_stsc_copy(struct alac_stsc* stsc)
{
    struct alac_stsc* new_stsc = malloc(sizeof(struct alac_stsc));
    new_stsc->first_chunk = stsc->first_chunk;
    new_stsc->ALAC_frames_per_chunk = stsc->ALAC_frames_per_chunk;
    new_stsc->description_index = stsc->description_index;
    return new_stsc;
}

static void
alac_stsc_print(struct alac_stsc* stsc, FILE* output)
{
    fprintf(output, "STSC(%u, %u, %u)",
            stsc->first_chunk,
            stsc->ALAC_frames_per_chunk,
            stsc->description_index);
}


static void
alac_order_to_wave_order(aa_int* alac_ordered)
{
    aa_int* wave_ordered = aa_int_new();
    a_int* wave_ch;
    unsigned i;
    wave_ordered->resize(wave_ordered, alac_ordered->len);

    switch (alac_ordered->len) {
    case 2:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*right*/
        break;
    case 1:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        break;
    case 3:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[2]); /*right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        break;
    case 4:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[2]); /*right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[3]); /*back center*/
        break;
    case 5:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[2]); /*right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[3]); /*back left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[4]); /*back right*/
        break;
    case 6:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[2]); /*right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[5]); /*LFE*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[3]); /*back left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[4]); /*back right*/
        break;
    case 7:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[2]); /*right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[6]); /*LFE*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[3]); /*back left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[4]); /*back right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[5]); /*back center*/
        break;
    case 8:
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[3]); /*left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[4]); /*right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[0]); /*center*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[7]); /*LFE*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[5]); /*back left*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[6]); /*back right*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[1]); /*left of center*/
        wave_ch = wave_ordered->append(wave_ordered);
        wave_ch->swap(wave_ch, alac_ordered->_[2]); /*right of center*/
        break;
    default:
        for (i = 0; i < alac_ordered->len; i++) {
            wave_ch = wave_ordered->append(wave_ordered);
            wave_ch->swap(wave_ch, alac_ordered->_[i]);
        }
        break;
    }

    wave_ordered->swap(wave_ordered, alac_ordered);
    wave_ordered->del(wave_ordered);
}

static status
read_frame(decoders_ALACDecoder *self,
           BitstreamReader* mdat,
           aa_int* frameset_channels,
           unsigned channel_count)
{
    unsigned has_sample_count;
    unsigned uncompressed_LSBs;
    unsigned not_compressed;
    unsigned sample_count;

    /*read frame header*/
    if (mdat->read(mdat, 16) != 0) {
        return INVALID_UNUSED_BITS;
    }
    has_sample_count = mdat->read(mdat, 1);
    uncompressed_LSBs = mdat->read(mdat, 2);
    not_compressed = mdat->read(mdat, 1);
    if (has_sample_count == 0)
        sample_count = self->max_samples_per_frame;
    else
        sample_count = mdat->read(mdat, 32);

    if (not_compressed == 1) {
        unsigned channel;
        unsigned i;
        aa_int* frame_channels = self->frame_channels;

        /*if uncompressed, read and return a bunch of verbatim samples*/

        frame_channels->reset(frame_channels);
        for (channel = 0; channel < channel_count; channel++)
            frame_channels->append(frame_channels);

        for (i = 0; i < sample_count; i++) {
            for (channel = 0; channel < channel_count; channel++) {
                frame_channels->_[channel]->append(
                    frame_channels->_[channel],
                    mdat->read_signed(mdat, self->bits_per_sample));
            }
        }

        for (channel = 0; channel < channel_count; channel++)
            frame_channels->_[channel]->swap(
                 frame_channels->_[channel],
                 frameset_channels->append(frameset_channels));

        return OK;
    } else {
        unsigned interlacing_shift;
        unsigned interlacing_leftweight;
        unsigned channel;
        unsigned i;
        unsigned sample_size;
        a_int* LSBs = NULL;

        aa_int* frame_channels = self->frame_channels;

        frame_channels->reset(frame_channels);

        /*if compressed, read interlacing shift and leftweight*/
        interlacing_shift = mdat->read(mdat, 8);
        interlacing_leftweight = mdat->read(mdat, 8);

        /*read a subframe header per channel*/
        for (channel = 0; channel < channel_count; channel++) {
            read_subframe_header(mdat,
                                 &(self->subframe_headers[channel]));
        }

        /*if uncompressed LSBs, read a block of partial samples to prepend*/
        if (uncompressed_LSBs > 0) {
            LSBs = self->uncompressed_LSBs;
            LSBs->reset_for(LSBs, channel_count * sample_count);
            for (i = 0; i < (channel_count * sample_count); i++)
                a_append(LSBs, mdat->read(mdat, uncompressed_LSBs * 8));
        }

        sample_size = (self->bits_per_sample -
                       (uncompressed_LSBs * 8) +
                       (channel_count - 1));

        /*read a residual block per channel
          and calculate the subframe's samples*/
        for (channel = 0; channel < channel_count; channel++) {
            a_int* residuals = self->residuals;
            residuals->reset(residuals);
            read_residuals(mdat,
                           residuals,
                           sample_count,
                           sample_size,
                           self->initial_history,
                           self->history_multiplier,
                           self->maximum_k);

            decode_subframe(
                frame_channels->append(frame_channels),
                sample_size,
                residuals,
                self->subframe_headers[channel].qlp_coeff,
                self->subframe_headers[channel].qlp_shift_needed);
        }

        /*if stereo, decorrelate channels
          according to interlacing shift and interlacing leftweight*/
        if ((channel_count == 2) && (interlacing_leftweight > 0)) {
            decorrelate_channels(frame_channels->_[0],
                                 frame_channels->_[1],
                                 interlacing_shift,
                                 interlacing_leftweight);
        }

        /*if uncompressed LSBs, prepend partial samples to output*/
        if (uncompressed_LSBs > 0) {
            for (channel = 0; channel < channel_count; channel++) {
                a_int* channel_data = frame_channels->_[channel];
                for (i = 0; i < sample_count; i++) {
                    channel_data->_[i] = ((channel_data->_[i] <<
                                           uncompressed_LSBs * 8) |
                                          LSBs->_[(i * channel_count) +
                                                  channel]);
                }
            }
        }

        /*finally, return frame's channel data*/
        for (channel = 0; channel < channel_count; channel++)
            frame_channels->_[channel]->swap(
                 frame_channels->_[channel],
                 frameset_channels->append(frameset_channels));

        return OK;
    }
}

static status
seek_mdat(BitstreamReader* alac_stream)
{
    unsigned int atom_size;
    uint8_t atom_type[4];

    if (!setjmp(*br_try(alac_stream))) {
        alac_stream->parse(alac_stream, "32u 4b", &atom_size, atom_type);
        while (memcmp(atom_type, "mdat", 4)) {
            alac_stream->skip_bytes(alac_stream, atom_size - 8);
            alac_stream->parse(alac_stream, "32u 4b", &atom_size, atom_type);
        }
        br_etry(alac_stream);
        return OK;
    } else {
        br_etry(alac_stream);
        return IO_ERROR;
    }
}

static void
read_subframe_header(BitstreamReader *bs,
                     struct alac_subframe_header *subframe_header)
{
    unsigned predictor_coef_num;
    unsigned i;

    subframe_header->prediction_type = bs->read(bs, 4);
    subframe_header->qlp_shift_needed = bs->read(bs, 4);
    subframe_header->rice_modifier = bs->read(bs, 3);
    predictor_coef_num = bs->read(bs, 5);

    subframe_header->qlp_coeff->reset(subframe_header->qlp_coeff);
    for (i = 0; i < predictor_coef_num; i++)
        subframe_header->qlp_coeff->append(subframe_header->qlp_coeff,
                                           bs->read_signed(bs, 16));
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
read_residuals(BitstreamReader *bs,
               a_int* residuals,
               unsigned int residual_count,
               unsigned int sample_size,
               unsigned int initial_history,
               unsigned int history_multiplier,
               unsigned int maximum_k)
{
    int history = initial_history;
    unsigned int sign_modifier = 0;
    int i, j;

    residuals->reset_for(residuals, residual_count);

    for (i = 0; i < residual_count; i++) {
        /*get an unsigned residual based on "history"
          and on "sample_size" as a last resort*/
        const unsigned unsigned_residual = read_residual(
            bs,
            MIN(LOG2((history >> 9) + 3), maximum_k),
            sample_size) + sign_modifier;

        /*clear out old sign modifier, if any */
        sign_modifier = 0;

        /*change unsigned residual into a signed residual
          and append it to "residuals"*/
        if (unsigned_residual & 1) {
            a_append(residuals, -((unsigned_residual + 1) >> 1));
        } else {
            a_append(residuals, unsigned_residual >> 1);
        }

        /*then use our old unsigned residual to update "history"*/
        if (unsigned_residual > 0xFFFF)
            history = 0xFFFF;
        else
            history += ((unsigned_residual * history_multiplier) -
                        ((history * history_multiplier) >> 9));

        /*if history gets too small, we may have a block of 0 samples
          which can be compressed more efficiently*/
        if ((history < 128) && ((i + 1) < residual_count)) {
            unsigned zero_block_size = read_residual(
                bs,
                MIN(7 - LOG2(history) + ((history + 16) / 64), maximum_k),
                16);
            if (zero_block_size > 0) {
                /*block of 0s found, so write them out*/

                /*ensure block of zeroes doesn't exceed
                  remaining residual count*/
                zero_block_size = MIN(zero_block_size, residual_count - i);

                for (j = 0; j < zero_block_size; j++) {
                    a_append(residuals, 0);
                    i++;
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
read_residual(BitstreamReader *bs,
              unsigned int k,
              unsigned int sample_size)
{
    static br_huffman_table_t MSB[] =
#include "alac_residual.h"
    ;
    const int msb = bs->read_huffman_code(bs, MSB);

    /*read a unary 0 value to a maximum of 9 bits*/
    if (msb == -1) {
        /*we've exceeded the maximum number of 1 bits,
          so return an unencoded value*/
        return bs->read(bs, sample_size);
    } else if (k == 0) {
        /*no least-significant bits to read, so return most-significant bits*/
        return (unsigned int)msb;
    } else {
        /*read a set of least-significant bits*/
        const unsigned lsb = bs->read(bs, k);
        if (lsb > 1) {
            /*if > 1, combine with MSB and return*/
            return (msb * ((1 << k) - 1)) + (lsb - 1);
        } else if (lsb == 1) {
            /*if = 1, unread single 1 bit and return shifted MSB*/
            bs->unread(bs, 1);
            return msb * ((1 << k) - 1);
        } else {
            /*if = 0, unread single 0 bit and return shifted MSB*/
            bs->unread(bs, 0);
            return msb * ((1 << k) - 1);
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
decode_subframe(a_int* samples,
                unsigned sample_size,
                a_int* residuals,
                a_int* qlp_coeff,
                uint8_t qlp_shift_needed)
{
    int* residuals_data = residuals->_;
    int i = 0;

    samples->reset_for(samples, MAX(qlp_coeff->len, residuals->len));

    /*first sample always copied verbatim*/
    a_append(samples, residuals_data[i++]);

    if (qlp_coeff->len < 31) { /*typical decoding case*/
        int j;

        /*grab a number of warm-up samples equal to coefficients' length*/
        for (j = 0; j < qlp_coeff->len; j++) {
            /*these are adjustments to the previous sample
              rather than copied verbatim*/
            a_append(samples,
                     TRUNCATE_BITS(residuals_data[i] + samples->_[i - 1],
                                   sample_size));
            i++;
        }

        /*then calculate a new sample per remaining residual*/
        for (; i < residuals->len; i++) {
            const int base_sample = samples->_[i - (qlp_coeff->len + 1)];
            int residual = residuals_data[i];
            int64_t lpc_sum = 1 << (qlp_shift_needed - 1);

            /*base_sample gets stripped from previously encoded samples
              then re-added prior to adding the next sample*/

            for (j = 0; j < qlp_coeff->len; j++) {
                lpc_sum += ((int64_t)qlp_coeff->_[j] *
                            (int64_t)(samples->_[i - j - 1] - base_sample));
            }

            /*sample = ((sum + 2 ^ (quant - 1)) / (2 ^ quant)) +
              residual + base_sample*/
            lpc_sum >>= qlp_shift_needed;
            lpc_sum += base_sample;
            a_append(samples,
                     TRUNCATE_BITS((int)(residual + lpc_sum), sample_size));

            /*At this point, except for base_sample,
              everything looks a lot like a FLAC LPC subframe.
              We're not done yet, though.
              ALAC's adaptive algorithm then adjusts the QLP coefficients
              up or down 1 step based on previously decoded samples
              and the residual*/

            if (residual > 0) {
                for (j = 0; j < qlp_coeff->len; j++) {
                    const int diff = (base_sample -
                                      samples->_[i - qlp_coeff->len + j]);
                    const int sign = SIGN_ONLY(diff);
                    qlp_coeff->_[qlp_coeff->len - j - 1] -= sign;
                    residual -= (((diff * sign) >> qlp_shift_needed) *
                                 (j + 1));
                    if (residual <= 0)
                        break;
                }
            } else if (residual < 0) {
                for (j = 0; j < qlp_coeff->len; j++) {
                    const int diff = (base_sample -
                                      samples->_[i - qlp_coeff->len + j]);
                    const int sign = SIGN_ONLY(diff);
                    qlp_coeff->_[qlp_coeff->len - j - 1] += sign;
                    residual -= (((diff * -sign) >> qlp_shift_needed) *
                                 (j + 1));
                    if (residual >= 0)
                        break;
                }
            }
        }
    } else {
        for (; i < residuals->len; i++) {
            a_append(samples,
                     TRUNCATE_BITS(residuals_data[i] + samples->_[i - 1],
                                   sample_size));
            i++;
        }
    }
}

void
decorrelate_channels(a_int* left,
                     a_int* right,
                     unsigned interlacing_shift,
                     unsigned interlacing_leftweight)
{
    const unsigned size = left->len;
    unsigned i;

    for (i = 0; i < size; i++) {
        const int ch0_s = left->_[i];
        const int ch1_s = right->_[i];
        int64_t leftweight = ch1_s * (int)interlacing_leftweight;
        int left_s;
        int right_s;
        leftweight >>= interlacing_shift;
        right_s = ch0_s - (int)leftweight;
        left_s = ch1_s + right_s;

        left->_[i]  = left_s;
        right->_[i] = right_s;
    }
}

int
find_atom(BitstreamReader* parent,
          BitstreamReader* sub_atom, unsigned* sub_atom_size,
          const char* sub_atom_name)
{
    if (!setjmp(*br_try(parent))) {
        unsigned atom_size = parent->read(parent, 32);
        uint8_t atom_name[4];
        parent->read_bytes(parent, atom_name, 4);
        while (memcmp(atom_name, sub_atom_name, 4)) {
            parent->skip_bytes(parent, atom_size - 8);
            atom_size = parent->read(parent, 32);
            parent->read_bytes(parent, atom_name, 4);
        }

        parent->substream_append(parent, sub_atom, atom_size - 8);
        *sub_atom_size = atom_size - 8;

        br_etry(parent);
        return 0;
    } else {
        br_etry(parent);
        return 1;
    }
}

int
find_sub_atom(BitstreamReader* parent,
              BitstreamReader* sub_atom, unsigned* sub_atom_size,
              ...)
{
    va_list ap;
    char* sub_atom_name;

    va_start(ap, sub_atom_size);

    sub_atom_name = va_arg(ap, char*);
    if (sub_atom_name == NULL) {
        /*no sub-atoms at all, so return 1 rather than 0*/
        va_end(ap);
        return 1;
    } else {
        /*at least 1 sub-atom*/
        BitstreamReader* parent_atom = br_substream_new(BS_BIG_ENDIAN);
        BitstreamReader* child_atom = br_substream_new(BS_BIG_ENDIAN);
        unsigned child_atom_size;

        /*first, try to find the sub-atom from our original parent*/
        if (find_atom(parent, child_atom, &child_atom_size, sub_atom_name)) {
            child_atom->close(child_atom);
            parent_atom->close(parent_atom);

            va_end(ap);
            return 1;
        }

        /*then, so long as there's still sub-atom names*/
        for (sub_atom_name = va_arg(ap, char*);
             sub_atom_name != NULL;
             sub_atom_name = va_arg(ap, char*)) {
            swap_readers(&parent_atom, &child_atom);
            br_substream_reset(child_atom);

            /*recursively find sub-atoms*/
            if (find_atom(parent_atom, child_atom, &child_atom_size,
                           sub_atom_name)) {
                /*unless one of the sub-atoms is not found*/
                child_atom->close(child_atom);
                parent_atom->close(parent_atom);

                va_end(ap);
                return 1;
            }
        }

        /*otherwise, return the found atom*/
        child_atom->substream_append(child_atom, sub_atom, child_atom_size);
        *sub_atom_size = child_atom_size;
        child_atom->close(child_atom);
        parent_atom->close(parent_atom);
        va_end(ap);
        return 0;
    }
}

void
swap_readers(BitstreamReader** a, BitstreamReader** b)
{
    BitstreamReader* c = *a;
    *a = *b;
    *b = c;
}

status
read_alac_atom(BitstreamReader* stsd_atom,
               unsigned int* max_samples_per_frame,
               unsigned int* bits_per_sample,
               unsigned int* history_multiplier,
               unsigned int* initial_history,
               unsigned int* maximum_k,
               unsigned int* channels,
               unsigned int* sample_rate)
{
    if (!setjmp(*br_try(stsd_atom))) {
        unsigned int stsd_version;
        unsigned int stsd_descriptions;
        uint8_t alac1[4];
        uint8_t alac2[4];

        stsd_atom->parse(stsd_atom,
                         "8u 24p 32u"
                         "32p 4b 6P 16p 16p 16p 4P 16p 16p 16p 16p 4P"
                         "32p 4b 4P 32u 8p 8u 8u 8u 8u 8u 16p 32p 32p 32u",
                         &stsd_version,
                         &stsd_descriptions,
                         alac1,
                         alac2,
                         max_samples_per_frame,
                         bits_per_sample,
                         history_multiplier,
                         initial_history,
                         maximum_k,
                         channels,
                         sample_rate);
        br_etry(stsd_atom);

        if (memcmp(alac1, "alac", 4) || memcmp(alac2, "alac", 4))
            return INVALID_ALAC_ATOM;
        else
            return OK;
    } else {
        br_etry(stsd_atom);
        return IO_ERROR;
    }
}

status
read_mdhd_atom(BitstreamReader* mdhd_atom,
               unsigned int* total_frames)
{
    if (!setjmp(*br_try(mdhd_atom))) {
        unsigned int version;

        mdhd_atom->parse(mdhd_atom, "8u 24p", &version);

        if (version == 0) {
            mdhd_atom->parse(mdhd_atom, "32p 32p 32p 32u 2P 16p", total_frames);
            br_etry(mdhd_atom);
            return OK;
        } else {
            br_etry(mdhd_atom);
            return INVALID_MDHD_ATOM;
        }
    } else {
        br_etry(mdhd_atom);
        return IO_ERROR;
    }
}

static status
read_stts_atom(BitstreamReader* stts_atom, a_obj* block_sizes)
{
    if (!setjmp(*br_try(stts_atom))) {
        unsigned times;
        stts_atom->parse(stts_atom, "8p 24p 32u", &times);
        block_sizes->reset_for(block_sizes, times);
        for (;times > 0; times--) {
            struct alac_stts alac_stts;
            stts_atom->parse(stts_atom, "32u 32u",
                             &(alac_stts.frame_count),
                             &(alac_stts.frame_duration));
            block_sizes->append(block_sizes, &alac_stts);
        }
        br_etry(stts_atom);
        return OK;
    } else {
        br_etry(stts_atom);
        return IO_ERROR;
    }
}

static status
read_stsc_atom(BitstreamReader* stsc_atom, a_obj* chunk_sizes)
{
    if (!setjmp(*br_try(stsc_atom))) {
        unsigned entries;
        stsc_atom->parse(stsc_atom, "8p 24p 32u", &entries);
        chunk_sizes->reset_for(chunk_sizes, entries);
        for (;entries > 0; entries--) {
            struct alac_stsc alac_stsc;
            stsc_atom->parse(stsc_atom, "32u 32u 32u",
                             &(alac_stsc.first_chunk),
                             &(alac_stsc.ALAC_frames_per_chunk),
                             &(alac_stsc.description_index));
            chunk_sizes->append(chunk_sizes, &alac_stsc);
        }
        br_etry(stsc_atom);
        return OK;
    } else {
        br_etry(stsc_atom);
        return IO_ERROR;
    }
}

static status
read_stco_atom(BitstreamReader* stco_atom, a_unsigned* chunk_offsets)
{
    if (!setjmp(*br_try(stco_atom))) {
        unsigned offsets;
        stco_atom->parse(stco_atom, "8p 24p 32u", &offsets);
        chunk_offsets->reset_for(chunk_offsets, offsets);
        for (;offsets > 0; offsets--) {
            a_append(chunk_offsets, stco_atom->read(stco_atom, 32));
        }
        br_etry(stco_atom);
        return OK;
    } else {
        br_etry(stco_atom);
        return IO_ERROR;
    }
}

static struct alac_seektable*
alac_seektable_copy(struct alac_seektable *entry)
{
    struct alac_seektable *new_entry = malloc(sizeof(struct alac_seektable));
    new_entry->pcm_frames_offset = entry->pcm_frames_offset;
    new_entry->absolute_file_offset = entry->absolute_file_offset;
    return new_entry;
}

static void
alac_seektable_print(struct alac_seektable *entry, FILE *output)
{
    fprintf(output, "seektable(%u, 0x%X)",
            entry->pcm_frames_offset,
            entry->absolute_file_offset);
}


#ifdef STANDALONE
int main(int argc, char* argv[]) {
    decoders_ALACDecoder decoder;
    unsigned channel_count;
    BitstreamReader* mdat;
    aa_int* frameset_channels;
    unsigned frame;
    unsigned channel;
    unsigned bytes_per_sample;
    FrameList_int_to_char_converter converter;
    unsigned char* output_data;
    unsigned output_data_size;
    unsigned pcm_size;

    if (argc < 2) {
        fprintf(stderr, "*** Usage: %s <file.m4a>\n", argv[0]);
        return 1;
    }

    if (ALACDecoder_init(&decoder, argv[1])) {
        fprintf(stderr, "*** Error: unable to initialize ALAC file\n");
        ALACDecoder_dealloc(&decoder);
        return 1;
    } else {
        mdat = decoder.bitstream;
        frameset_channels = decoder.frameset_channels;
        output_data = malloc(1);
        output_data_size = 1;
        bytes_per_sample = decoder.bits_per_sample / 8;
        converter = FrameList_get_int_to_char_converter(
            decoder.bits_per_sample, 0, 1);
    }

    while (decoder.remaining_frames) {
        if (!setjmp(*br_try(mdat))) {
            frameset_channels->reset(frameset_channels);

            /*get initial frame's channel count*/
            channel_count = mdat->read(mdat, 3) + 1;
            while (channel_count != 8) {
                status status;

                /*read a frame from the frameset into "channels"*/
                if ((status = read_frame(&decoder,
                                         mdat,
                                         frameset_channels,
                                         channel_count)) != OK) {
                    br_etry(mdat);
                    fprintf(stderr, "*** Error: %s", alac_strerror(status));
                    goto error;
                } else {
                    /*ensure all frames have the same sample count*/
                    /*FIXME*/

                    /*read the channel count of the next frame
                      in the frameset, if any*/
                    channel_count = mdat->read(mdat, 3) + 1;
                }
            }

            /*once all the frames in the frameset are read,
              byte-align the output stream*/
            mdat->byte_align(mdat);
            br_etry(mdat);

            /*decrement the remaining sample count*/
            decoder.remaining_frames -= MIN(decoder.remaining_frames,
                                            frameset_channels->_[0]->len);

            /*convert ALAC channel assignment to
              standard audiotools assignment*/
            alac_order_to_wave_order(frameset_channels);

            /*finally, build and return framelist string from the sample data*/
            pcm_size = (bytes_per_sample *
                        frameset_channels->len *
                        frameset_channels->_[0]->len);
            if (pcm_size > output_data_size) {
                output_data_size = pcm_size;
                output_data = realloc(output_data, output_data_size);
            }
            for (channel = 0; channel < frameset_channels->len; channel++) {
                const a_int* channel_data = frameset_channels->_[channel];
                for (frame = 0; frame < channel_data->len; frame++) {
                    converter(channel_data->_[frame],
                              output_data +
                              ((frame * frameset_channels->len) + channel) *
                              bytes_per_sample);
                }
            }

            fwrite(output_data, sizeof(unsigned char), pcm_size, stdout);
        } else {
            br_etry(mdat);
            fprintf(stderr, "*** Error: EOF during frame reading\n");
            goto error;
        }
    }

    ALACDecoder_dealloc(&decoder);
    free(output_data);

    return 0;

error:
    ALACDecoder_dealloc(&decoder);
    free(output_data);

    return 1;
}
#endif
