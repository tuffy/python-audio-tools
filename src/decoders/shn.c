#include "shn.h"
#include "../buffer.h"
#include "../pcm_conv.h"
#include "../framelist.h"
#include <string.h>
#include <math.h>

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

/*all valid shorten commands*/
enum {FN_DIFF0     = 0,
      FN_DIFF1     = 1,
      FN_DIFF2     = 2,
      FN_DIFF3     = 3,
      FN_QUIT      = 4,
      FN_BLOCKSIZE = 5,
      FN_BITSHIFT  = 6,
      FN_QLPC      = 7,
      FN_ZERO      = 8,
      FN_VERBATIM  = 9};

/*reject overly large block sizes outright
  to keep a broken or malicious file from trying to
  allocate all the memory in the world*/
#define MAX_BLOCK_SIZE 65535

struct verbatim_list {
    uint8_t *bytes;
    unsigned size;
    struct verbatim_list *next;
};

/**********************************/
/*  private function definitions  */
/**********************************/

static inline unsigned
read_unsigned(BitstreamReader *bs, unsigned count)
{
    const register unsigned MSB = (bs->read_unary(bs, 1) << count);
    const register unsigned LSB = bs->read(bs, count);
    return MSB | LSB;
}

static inline void
skip_unsigned(BitstreamReader *bs, unsigned count)
{
    bs->skip_unary(bs, 1);
    bs->skip(bs, count);
}

static inline int
read_signed(BitstreamReader *bs, unsigned count)
{
    /*1 additional sign bit*/
    const unsigned u = read_unsigned(bs, count + 1);
    if (u % 2)
        return -(u >> 1) - 1;
    else
        return u >> 1;
}

static inline void
skip_signed(BitstreamReader *bs, unsigned count)
{
    skip_unsigned(bs, count + 1);
}

static inline unsigned
read_long(BitstreamReader *bs)
{
    return read_unsigned(bs, read_unsigned(bs, 2));
}

static void
parse_header(BitstreamReader *bs, struct shn_header *header);

/*skips a VERBATIM block*/
static void
skip_verbatim(BitstreamReader *bs);

/*reads "count" individual bytes from the stream to the buffer*/
static void
read_verbatim_chunk(BitstreamReader *bs,
                    unsigned count,
                    uint8_t buffer[]);

/*parses a VERBATIM block and returns a block of bytes and their size
  the bytes should be freed when no longer needed*/
static uint8_t*
read_verbatim(BitstreamReader *bs, unsigned *size);

/*adds a new node to the top of the verbatim list
  steals a reference to "bytes" so it should not be freed elsewhere*/
static struct verbatim_list*
push_verbatim(struct verbatim_list *head,
              uint8_t *bytes,
              unsigned size);

/*appends the given data to the verbatim entry at the top of the list
  steals a reference to "bytes" so it should not be freed elsewhere*/
static struct verbatim_list*
append_verbatim(struct verbatim_list *head,
                uint8_t *bytes,
                unsigned size);

/*given a verbatim list sorted with the last entry at the top,
  returns a Python list*/
static PyObject*
verbatim_list_to_py_list(const struct verbatim_list *head);

/*frees the entire verbatim list*/
static void
free_verbatim_list(struct verbatim_list *head);

static inline int
valid_block_size(unsigned block_size) {
    return (block_size > 0) && (block_size < MAX_BLOCK_SIZE);
}

/*returns nonzero and sets Python exception
  if an error occurs processing the command*/
typedef int (*command_f)(BitstreamReader *bs,
                         const struct shn_header *header,
                         const int means[],
                         int channel[]);

#define COMMAND_DEF(NAME)                         \
  static int                                      \
  command_##NAME(BitstreamReader *bs,             \
                 const struct shn_header *header, \
                 const int means[],               \
                 int channel[]);
COMMAND_DEF(diff0)
COMMAND_DEF(diff1)
COMMAND_DEF(diff2)
COMMAND_DEF(diff3)
COMMAND_DEF(qlpc)
COMMAND_DEF(zero)

static void
apply_left_shift(unsigned left_shift,
                 unsigned block_size,
                 int channel[]);

static int
shn_mean(unsigned count, const int values[]);

static unsigned
count_bits(int value);

/*************************************/
/*  public function implementations  */
/*************************************/

PyObject*
SHNDecoder_new(PyTypeObject *type,
               PyObject *args, PyObject *kwds)
{
    decoders_SHNDecoder *self;

    self = (decoders_SHNDecoder *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
SHNDecoder_init(decoders_SHNDecoder *self,
                PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"file",
                             "sample_rate",
                             "channel_mask",
                             NULL};
    const uint8_t shn_magic[4] = {0x61, 0x6A, 0x6B, 0x67};
    uint8_t file_magic[4];
    unsigned version;

    PyObject *file;
    self->channel_mask = 0;
    self->bitstream = NULL;
    self->bits_per_sample =0;
    self->left_shift = 0;
    self->audiotools_pcm = NULL;
    self->closed = 0;
    self->quitted = 0;

    if (!PyArg_ParseTupleAndKeywords(args,
                                     kwds,
                                     "Oi|i",
                                     kwlist,
                                     &file,
                                     &(self->sample_rate),
                                     &(self->channel_mask))) {
        return -1;
    } else {
        /*sanity-check sample rate and channel mask*/
        if (self->sample_rate < 1) {
            PyErr_SetString(PyExc_ValueError, "sample_rate must be > 0");
            return -1;
        }

        if (self->channel_mask < 0) {
            PyErr_SetString(PyExc_ValueError, "channel_mask must be >= 0");
            return -1;
        }

        Py_INCREF(file);
    }

    /*open the shn file*/
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
        unsigned c;

        /*validate file header*/
        self->bitstream->read_bytes(self->bitstream, file_magic, 4);
        version = self->bitstream->read(self->bitstream, 8);

        if (memcmp(file_magic, shn_magic, 4)) {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_ValueError, "invalid magic number");
            return -1;
        }

        if (version != 2) {
            br_etry(self->bitstream);
            PyErr_SetString(PyExc_ValueError, "invalid version");
            return -1;
        }

        /*parse header*/
        parse_header(self->bitstream, &(self->header));

        br_etry(self->bitstream);

        /*sanity check header parameters*/
        if (!valid_block_size(self->header.block_size)) {
            PyErr_SetString(PyExc_ValueError, "invalid block size");
            return -1;
        }

        if (self->channel_mask &&
            (count_bits(self->channel_mask) != self->header.channels)) {
            PyErr_SetString(PyExc_ValueError,
                            "channel mask doesn't match channel count");
            return -1;
        }

        if (self->header.max_LPC > 16) {
            PyErr_SetString(PyExc_ValueError, "excessive LPC coefficients");
            return -1;
        } else if (self->header.max_LPC > 3) {
            self->to_wrap = self->header.max_LPC;
        } else {
            self->to_wrap = 3;
        }

        /*determine bits-per-sample*/
        switch (self->header.file_type) {
        case 1: /*signed 8-bit PCM*/
        case 2: /*unsigned 8-bit PCM*/
            self->bits_per_sample = 8;
            break;
        case 3: /*signed 16-bit big-endian PCM*/
        case 4: /*unsigned 16-bit big-endian PCM*/
        case 5: /*signed 16-bit little-endian PCM*/
        case 6: /*unsigned 16-bit little-endian PCM*/
            self->bits_per_sample = 16;
            break;
        default:
            PyErr_SetString(PyExc_ValueError, "unsupported file type");
            return -1;
        }

        /*allocate wrapped samples per channel*/
        self->wrapped_samples = malloc(self->header.channels * sizeof(int*));

        /*allocate means per channel*/
        self->means = malloc(self->header.channels * sizeof(int*));

        for (c = 0; c < self->header.channels; c++) {
            self->wrapped_samples[c] = calloc(self->to_wrap, sizeof(int));
            self->means[c] = calloc(self->header.mean_count, sizeof(int));
        }
    } else {
        br_etry(self->bitstream);
        PyErr_SetString(PyExc_IOError, "I/O error reading Shorten metadata");
        return -1;
    }

    /*setup PCM generator*/
    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    return 0;
}

void
SHNDecoder_dealloc(decoders_SHNDecoder *self)
{
    unsigned c;

    if (self->bitstream != NULL) {
        self->bitstream->free(self->bitstream);
    }

    /*deallocate per-buffer channels*/
    for (c = 0; c < self->header.channels; c++) {
        free(self->wrapped_samples[c]);
        free(self->means[c]);
    }
    free(self->wrapped_samples);
    free(self->means);

    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject*
SHNDecoder_close(decoders_SHNDecoder* self, PyObject *args)
{
    /*mark stream as closed so more calls to read() generate ValueErrors*/
    self->closed = 1;

    /*close bitstream for further reading*/
    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
SHNDecoder_enter(decoders_SHNDecoder* self, PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject*
SHNDecoder_exit(decoders_SHNDecoder* self, PyObject *args)
{
    self->closed = 1;

    self->bitstream->close_internal_stream(self->bitstream);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
SHNDecoder_sample_rate(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->sample_rate);
}

static PyObject*
SHNDecoder_bits_per_sample(decoders_SHNDecoder *self,
                           void *closure)
{
    return Py_BuildValue("I", self->bits_per_sample);
}

static PyObject*
SHNDecoder_channels(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("I", self->header.channels);
}

static PyObject*
SHNDecoder_channel_mask(decoders_SHNDecoder *self, void *closure)
{
    return Py_BuildValue("i", self->channel_mask);
}

PyObject*
SHNDecoder_read(decoders_SHNDecoder* self, PyObject *args)
{
    unsigned c = 0;
    unsigned command;
    pcm_FrameList *framelist;
    const static command_f audio_command[] = {command_diff0,
                                              command_diff1,
                                              command_diff2,
                                              command_diff3,
                                              NULL, /*QUIT*/
                                              NULL, /*BLOCKSIZE*/
                                              NULL, /*BITSHIFT*/
                                              command_qlpc,
                                              command_zero,
                                              NULL  /*VERBATIM*/};

    if (self->closed) {
        /*ensure .close() hasn't been called on reader*/
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    if (self->quitted) {
        /*if QUIT command encountered, generate empty FrameLists*/
        return empty_FrameList(self->audiotools_pcm,
                               self->header.channels,
                               self->bits_per_sample);
    }

    /*process commands until a FrameList is filled or QUIT is called*/
    framelist = new_FrameList(self->audiotools_pcm,
                              self->header.channels,
                              self->bits_per_sample,
                              self->header.block_size);

    if (!setjmp(*br_try(self->bitstream))) {
        while (c < self->header.channels) {
            switch (command = read_unsigned(self->bitstream, 2)) {
            case FN_DIFF0:
            case FN_DIFF1:
            case FN_DIFF2:
            case FN_DIFF3:
            case FN_QLPC:
            case FN_ZERO:
                {
                    const unsigned to_wrap = self->to_wrap;
                    const unsigned mean_count = self->header.mean_count;
                    const unsigned block_size = self->header.block_size;
                    int channel[to_wrap + block_size];

                    /*transfer wrapped samples to start of buffer*/
                    memcpy(channel,
                           self->wrapped_samples[c],
                           to_wrap * sizeof(int));

                    /*process audio command*/
                    if (audio_command[command](self->bitstream,
                                               &(self->header),
                                               self->means[c],
                                               channel + to_wrap)) {
                        br_etry(self->bitstream);
                        Py_DECREF((PyObject*)framelist);
                        return NULL;
                    }

                    /*calculate next mean for given channel*/
                    if (mean_count) {
                        memmove(self->means[c],
                                self->means[c] + 1,
                                (mean_count - 1) * sizeof(int));
                        self->means[c][mean_count - 1] =
                            shn_mean(block_size, channel + to_wrap);
                    }

                    /*apply shift, if any*/
                    if (self->left_shift) {
                        apply_left_shift(self->left_shift,
                                         block_size,
                                         channel + to_wrap);
                    }

                    /*transfer new samples in buffer to framelist*/
                    put_channel_data(framelist->samples,
                                     c,
                                     self->header.channels,
                                     block_size,
                                     channel + to_wrap);

                    /*wrap trailing samples for next frame*/
                    memcpy(self->wrapped_samples[c],
                           channel + block_size,
                           to_wrap * sizeof(int));

                    c += 1;
                }
                break;
            case FN_QUIT:
                self->quitted = 1;
                br_etry(self->bitstream);
                Py_DECREF((PyObject*)framelist);
                return empty_FrameList(self->audiotools_pcm,
                                       self->header.channels,
                                       self->bits_per_sample);
            case FN_BLOCKSIZE:
                Py_DECREF((PyObject*)framelist);

                if (c != 0) {
                    br_etry(self->bitstream);
                    PyErr_SetString(PyExc_ValueError,
                                    "block size changed mid-FrameList");
                    return NULL;
                }

                self->header.block_size = read_long(self->bitstream);

                if (!valid_block_size(self->header.block_size)) {
                    br_etry(self->bitstream);
                    PyErr_SetString(PyExc_ValueError, "invalid block size");
                    return NULL;
                }

                framelist = new_FrameList(self->audiotools_pcm,
                                          self->header.channels,
                                          self->bits_per_sample,
                                          self->header.block_size);
                break;
            case FN_BITSHIFT:
                self->left_shift = read_unsigned(self->bitstream, 2);
                break;
            case FN_VERBATIM:
                skip_verbatim(self->bitstream);
                break;
            default:
                /*unknown or unsupported command encountered*/
                br_etry(self->bitstream);
                Py_DECREF((PyObject*)framelist);
                PyErr_SetString(PyExc_ValueError, "unsupported command");
                return NULL;
            }
        }

        br_etry(self->bitstream);
        return (PyObject*)framelist;
    } else {
        br_etry(self->bitstream);
        Py_DECREF((PyObject*)framelist);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }
}

static PyObject*
SHNDecoder_verbatims(decoders_SHNDecoder* self, PyObject *args)
{
    struct verbatim_list *verbatims = NULL;
    PyObject *verbatims_obj;
    unsigned previous_command = 0;
    unsigned command;

    if (self->closed) {
        /*ensure .close() hasn't been called on reader*/
        PyErr_SetString(PyExc_ValueError, "cannot read closed stream");
        return NULL;
    }

    if (self->quitted) {
        return PyList_New(0);
    }

    /*process all commands until QUIT is called*/
    if (!setjmp(*br_try(self->bitstream))) {
        while ((command = read_unsigned(self->bitstream, 2)) != FN_QUIT) {
            switch (command) {
            case FN_DIFF0:
            case FN_DIFF1:
            case FN_DIFF2:
            case FN_DIFF3:
                {
                    const unsigned energy = read_unsigned(self->bitstream, 3);
                    unsigned block_size;
                    for (block_size = self->header.block_size;
                         block_size;
                         block_size--) {
                        skip_signed(self->bitstream, energy);
                    }
                }
                break;
            case FN_BLOCKSIZE:
                /*not going to bother validating mid-FrameList size changes*/

                self->header.block_size = read_long(self->bitstream);

                if (!valid_block_size(self->header.block_size)) {
                    br_etry(self->bitstream);
                    free_verbatim_list(verbatims);
                    PyErr_SetString(PyExc_ValueError, "invalid block size");
                    return NULL;
                }
                break;
            case FN_BITSHIFT:
                skip_unsigned(self->bitstream, 2);
                break;
            case FN_QLPC:
                {
                    const unsigned energy = read_unsigned(self->bitstream, 3);
                    unsigned coeff_count;
                    unsigned block_size;
                    for (coeff_count = read_unsigned(self->bitstream, 2);
                         coeff_count;
                         coeff_count--) {
                         skip_signed(self->bitstream, 5);
                    }
                    for (block_size = self->header.block_size;
                         block_size;
                         block_size--) {
                         skip_signed(self->bitstream, energy);
                    }
                }
                break;
            case FN_QUIT:
            case FN_ZERO:
                /*do nothing*/
                break;
            case FN_VERBATIM:
                {
                    unsigned size;
                    uint8_t *bytes = read_verbatim(self->bitstream, &size);
                    if (previous_command == FN_VERBATIM) {
                        verbatims = append_verbatim(verbatims, bytes, size);
                    } else {
                        verbatims = push_verbatim(verbatims, bytes, size);
                    }
                }
                break;
            default:
                br_etry(self->bitstream);
                free_verbatim_list(verbatims);
                PyErr_SetString(PyExc_ValueError, "unsupported command");
                return NULL;
            }

            previous_command = command;
        }

        self->quitted = 1;
        br_etry(self->bitstream);
        verbatims_obj = verbatim_list_to_py_list(verbatims);
        free_verbatim_list(verbatims);
        return verbatims_obj;
    } else {
        br_etry(self->bitstream);
        free_verbatim_list(verbatims);
        PyErr_SetString(PyExc_IOError, "I/O error reading stream");
        return NULL;
    }

}

/**************************************/
/*  private function implementations  */
/**************************************/

static void
parse_header(BitstreamReader *bs, struct shn_header *header)
{
    unsigned bytes_to_skip;

    header->file_type = read_long(bs);
    header->channels = read_long(bs);
    header->block_size = read_long(bs);
    header->max_LPC = read_long(bs);
    header->mean_count = read_long(bs);
    bytes_to_skip = read_long(bs);
    bs->skip_bytes(bs, bytes_to_skip);
}

static void
skip_verbatim(BitstreamReader *bs)
{
    unsigned verbatim_bytes;
    for (verbatim_bytes = read_unsigned(bs, 5);
         verbatim_bytes;
         verbatim_bytes--) {
        skip_unsigned(bs, 8);
    }
}

static void
read_verbatim_chunk(BitstreamReader *bs,
                    unsigned count,
                    uint8_t buffer[])
{
    for (; count; count--) {
        buffer[0] = read_unsigned(bs, 8) & 0xFF;
        buffer += 1;
    }
}

#define BUFFER_SIZE 512

static uint8_t*
read_verbatim(BitstreamReader *bs, unsigned *size)
{
    unsigned verbatim_bytes = read_unsigned(bs, 5);
    uint8_t *bytes = NULL;
    *size = 0;

    if (!setjmp(*br_try(bs))) {
        /*read verbatim block in smallish chunks
          to avoid blowing up if the size turns out to be huge*/
        uint8_t buffer[BUFFER_SIZE];

        while (verbatim_bytes) {
            if (verbatim_bytes <= BUFFER_SIZE) {
                read_verbatim_chunk(bs, verbatim_bytes, buffer);
                bytes = realloc(bytes, *size + verbatim_bytes);
                memcpy(bytes + *size, buffer, verbatim_bytes);
                *size += verbatim_bytes;
                verbatim_bytes = 0;
            } else {
                read_verbatim_chunk(bs, BUFFER_SIZE, buffer);
                bytes = realloc(bytes, *size + BUFFER_SIZE);
                memcpy(bytes + *size, buffer, BUFFER_SIZE);
                *size += verbatim_bytes;
                verbatim_bytes -= BUFFER_SIZE;
            }
        }

        br_etry(bs);
        return bytes;
    } else {
        br_etry(bs);
        free(bytes);
        br_abort(bs);
        return NULL; /*won't get here*/
    }
}

static struct verbatim_list*
push_verbatim(struct verbatim_list *head,
              uint8_t *bytes,
              unsigned size)
{
    struct verbatim_list *node = malloc(sizeof(struct verbatim_list));
    node->bytes = bytes;
    node->size = size;
    node->next = head;
    return node;
}

static struct verbatim_list*
append_verbatim(struct verbatim_list *head,
                uint8_t *bytes,
                unsigned size)
{
    if (head) {
        head->bytes = realloc(head->bytes, head->size + size);
        memcpy(head->bytes + head->size, bytes, size);
        head->size += size;
        free(bytes);
        return head;
    } else {
        return push_verbatim(head, bytes, size);
    }
}

static PyObject*
verbatim_list_to_py_list(const struct verbatim_list *head)
{
    PyObject *list = PyList_New(0);

    for (; head; head = head->next) {
        PyObject *bytes = PyBytes_FromStringAndSize((char*)head->bytes,
                                                    head->size);
        PyList_Append(list, bytes);
        Py_DECREF(bytes);
    }

    PyList_Reverse(list);
    return list;
}

static void
free_verbatim_list(struct verbatim_list *head)
{
    while (head) {
        struct verbatim_list *next = head->next;
        free(head->bytes);
        free(head);
        head = next;
    }
}

static int
command_diff0(BitstreamReader *bs,
              const struct shn_header *header,
              const int means[],
              int channel[])
{
    unsigned block_size;
    const int offset = shn_mean(header->mean_count, means);
    const unsigned energy = read_unsigned(bs, 3);
    for (block_size = header->block_size; block_size; block_size--) {
        channel[0] = offset + read_signed(bs, energy);
        channel += 1;
    }
    return 0;
}

static int
command_diff1(BitstreamReader *bs,
              const struct shn_header *header,
              const int means[],
              int channel[])
{
    unsigned block_size;
    const unsigned energy = read_unsigned(bs, 3);
    for (block_size = header->block_size; block_size; block_size--) {
        channel[0] = channel[-1] + read_signed(bs, energy);
        channel += 1;
    }
    return 0;
}

static int
command_diff2(BitstreamReader *bs,
              const struct shn_header *header,
              const int means[],
              int channel[])
{
    unsigned block_size;
    const unsigned energy = read_unsigned(bs, 3);
    for (block_size = header->block_size; block_size; block_size--) {
        channel[0] = (2 * channel[-1]) - channel[-2] + read_signed(bs, energy);
        channel += 1;
    }
    return 0;
}

static int
command_diff3(BitstreamReader *bs,
              const struct shn_header *header,
              const int means[],
              int channel[])
{
    unsigned block_size;
    const unsigned energy = read_unsigned(bs, 3);
    for (block_size = header->block_size; block_size; block_size--) {
        channel[0] = (3 * (channel[-1] - channel[-2])) +
                     channel[-3] +
                     read_signed(bs, energy);
        channel += 1;
    }
    return 0;
}

static int
command_qlpc(BitstreamReader *bs,
             const struct shn_header *header,
             const int means[],
             int channel[])
{
    const int offset = shn_mean(header->mean_count, means);
    const unsigned block_size = header->block_size;
    const unsigned energy = read_unsigned(bs, 3);
    const unsigned LPC_count = read_unsigned(bs, 2);
    int coeff[header->max_LPC];
    int unoffset[header->block_size];
    int i;

    if (LPC_count > header->max_LPC) {
        PyErr_SetString(PyExc_ValueError, "excessive LPC coefficients");
        return 1;
    }

    for (i = 0; i < LPC_count; i++) {
        coeff[i] = read_signed(bs, 5);
    }

    for (i = 0; i < block_size; i++) {
        register int32_t sum = 1 << 5;
        const int residual = read_signed(bs, energy);
        int j;
        for (j = 0; j < LPC_count; j++) {
            if ((i - j - 1) < 0) {
                sum += coeff[j] * (channel[i - j - 1] - offset);
            } else {
                sum += coeff[j] * unoffset[i - j - 1];
            }
        }
        sum >>= 5;
        unoffset[i] = sum + residual;
    }

    /*re-apply offset to samples*/
    for (i = 0; i < block_size; i++) {
        channel[i] = unoffset[i] + offset;
    }

    return 0;
}

static int
command_zero(BitstreamReader *bs,
             const struct shn_header *header,
             const int means[],
             int channel[])
{
    unsigned block_size;
    for (block_size = header->block_size; block_size; block_size--) {
        channel[0] = 0;
        channel += 1;
    }
    return 0;
}

static void
apply_left_shift(unsigned left_shift,
                 unsigned block_size,
                 int channel[])
{
    if (left_shift) {
        for (; block_size; block_size--) {
            channel[0] <<= left_shift;
            channel += 1;
        }
    }
}

static int
shn_mean(unsigned count, const int values[])
{
    unsigned i;
    int sum = count / 2;
    for (i = 0; i < count; i++) {
        sum += values[i];
    }
    sum /= count;
    return sum;
}

static unsigned
count_bits(int value)
{
    unsigned bits = 0;

    for (; value; value >>= 1) {
        if (value & 1) {
            bits += 1;
        }
    }

    return bits;
}
