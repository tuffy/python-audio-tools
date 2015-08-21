/********************************************************
 Bitstream Library, a module for reading bits of data

 Copyright (C) 2007-2015  Brian Langenberger

 The Bitstream Library is free software; you can redistribute it and/or modify
 it under the terms of either:

   * the GNU Lesser General Public License as published by the Free
     Software Foundation; either version 3 of the License, or (at your
     option) any later version.

 or

   * the GNU General Public License as published by the Free Software
     Foundation; either version 2 of the License, or (at your option) any
     later version.

 or both in parallel, as here.

 The Bitstream Library is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 for more details.

 You should have received copies of the GNU General Public License and the
 GNU Lesser General Public License along with the GNU MP Library.  If not,
 see https://www.gnu.org/licenses/.
 *******************************************************/

#include "func_io.h"
#include <string.h>

struct br_external_input*
ext_open_r(void* user_data,
           unsigned buffer_size,
           ext_read_f read,
           ext_setpos_f setpos,
           ext_getpos_f getpos,
           ext_free_pos_f free_pos,
           ext_seek_f seek,
           ext_close_f close,
           ext_free_f free)
{
    struct br_external_input* input = malloc(sizeof(struct br_external_input));

    input->user_data = user_data;
    input->read = read;
    input->setpos = setpos;
    input->getpos = getpos;
    input->free_pos = free_pos;
    input->seek = seek;
    input->close = close;
    input->free = free;

    input->buffer.data = malloc(buffer_size * sizeof(uint8_t));
    input->buffer.pos = 0;
    input->buffer.size = 0;
    input->buffer.maximum_size = buffer_size;

    return input;
}

/*returns true if the buffer has no data*/
static inline int
reader_buffer_empty(const struct br_external_input* stream)
{
    return stream->buffer.pos == stream->buffer.size;
}

/*returns the amount of bytes currently in the buffer*/
static inline int
reader_buffer_size(const struct br_external_input* stream)
{
    return stream->buffer.size - stream->buffer.pos;
}

/*attempts to refill the buffer to its maximum size
  by calling our external function
  and returns the amount of bytes actually filled
  (which may be 0 if no data is received or no more data can fit)*/
static unsigned
refill_reader_buffer(struct br_external_input* stream)
{
    const unsigned buffer_size = reader_buffer_size(stream);
    unsigned filled;

    /*reclaim used buffer space, if any*/
    if (buffer_size) {
        memmove(stream->buffer.data,
                stream->buffer.data + stream->buffer.pos,
                buffer_size);
        stream->buffer.pos = 0;
        stream->buffer.size -= buffer_size;
    } else {
        stream->buffer.pos = stream->buffer.size = 0;
    }

    /*then fill buffer from external function*/
    filled = stream->read(stream->user_data,
                          stream->buffer.data + stream->buffer.size,
                          stream->buffer.maximum_size - stream->buffer.size);
    stream->buffer.size += filled;
    return filled;
}

/*mark buffer as empty and needing to be refilled*/
static inline void
reset_reader_buffer(struct br_external_input* stream)
{
    stream->buffer.pos = stream->buffer.size = 0;
}

int
ext_getc(struct br_external_input* stream)
{
    if (reader_buffer_empty(stream)) {
        /*buffer is empty, so try to refill from external function*/
        if (refill_reader_buffer(stream) == 0) {
            /*read unsuccessful, so return EOF*/
            return EOF;
        }
    }

    return stream->buffer.data[stream->buffer.pos++];
}

unsigned
ext_fread(struct br_external_input* stream,
          uint8_t* data,
          unsigned data_size)
{
    const unsigned initial_data_size = data_size;

    /*if data_size == 0 this loop will be a no-op
      but I think that's an uncommon case*/
    do {
        /*copy either the total bytes in the buffer
          or the remaining "data_size" to "data", whichever is less*/
        const unsigned buffer_size = reader_buffer_size(stream);
        const unsigned to_copy =
            data_size > buffer_size ? buffer_size : data_size;

        memcpy(data, stream->buffer.data + stream->buffer.pos, to_copy);
        stream->buffer.pos += to_copy;
        data += to_copy;
        data_size -= to_copy;

        if (data_size) {
            /*if another pass is required, refill the buffer*/
            if (refill_reader_buffer(stream) == 0) {
                /*read unsuccessful, so return as many bytes as we could get*/
                return initial_data_size - data_size;
            }
        }
    } while (data_size);

    /*all bytes processed successfully*/
    return initial_data_size;
}

int
ext_fseek_r(struct br_external_input *stream, long position, int whence)
{
    if (stream->seek == NULL) {
        /*unseekable stream*/
        return -1;
    }

    switch (whence) {
    case 0:  /*SEEK_SET*/
    case 2:  /*SEEK_END*/
        reset_reader_buffer(stream);
        return stream->seek(stream->user_data, position, whence);
    case 1:  /*SEEK_CUR*/
        /*if the relative position being seeked is still in the
          bounds of the buffer, simply seek within the buffer itself
          otherwise, perform a relative seek
          that accounts for the current size of the buffer contents*/
        if (position > 0) {
            const unsigned buffer_size = reader_buffer_size(stream);
            if (position <= buffer_size) {
                stream->buffer.pos += position;
                return 0;
            } else {
                reset_reader_buffer(stream);
                return stream->seek(stream->user_data,
                                    position - buffer_size,
                                    whence);
            }
        } else if (position < 0) {
            if (-position <= stream->buffer.pos) {
                stream->buffer.pos += position;
                return 0;
            } else {
                const unsigned buffer_size = reader_buffer_size(stream);
                reset_reader_buffer(stream);
                return stream->seek(stream->user_data,
                                    position - buffer_size,
                                    whence);
            }
        } else {
            /*no need to move anywhere*/
            return 0;
        }
    default:
        /*unknown "whence"*/
        return -1;
    }
}

void
ext_close_r(struct br_external_input* stream)
{
    stream->close(stream->user_data);
}

void
ext_free_r(struct br_external_input* stream)
{
    stream->free(stream->user_data);
    free(stream->buffer.data);
    free(stream);
}

struct bw_external_output*
ext_open_w(void* user_data,
           unsigned buffer_size,
           ext_write_f write,
           ext_setpos_f setpos,
           ext_getpos_f getpos,
           ext_free_pos_f free_pos,
           ext_seek_f seek,
           ext_flush_f flush,
           ext_close_f close,
           ext_free_f free)
{
    struct bw_external_output* output =
        malloc(sizeof(struct bw_external_output));
    output->user_data = user_data;
    output->write = write;
    output->setpos = setpos;
    output->getpos = getpos;
    output->free_pos = free_pos;
    output->seek = seek;
    output->flush = flush;
    output->close = close;
    output->free = free;

    output->buffer.data = malloc(buffer_size * sizeof(uint8_t));
    output->buffer.pos = 0;
    output->buffer.maximum_size = buffer_size;

    return output;
}

/*returns true if the buffer can hold no more data*/
static inline int
writer_buffer_full(const struct bw_external_output* stream)
{
    return stream->buffer.pos == stream->buffer.maximum_size;
}

/*attempts to empty the buffer by calling our external function
  and returns 0 on success, 1 if some write error occurs*/
static int
empty_writer_buffer(struct bw_external_output* stream)
{
    /*send buffer contents to external function*/
    if (stream->write(stream->user_data,
                      stream->buffer.data,
                      stream->buffer.pos)) {
        /*some write error occurred*/
        return 1;
    }

    /*reclaim buffer space so it can get more data*/
    stream->buffer.pos = 0;

    /*return success*/
    return 0;
}

/*returns the total bytes that can fit in the buffer
  before it becomes full*/
static inline unsigned
writer_buffer_remaining_size(const struct bw_external_output* stream)
{
    return stream->buffer.maximum_size - stream->buffer.pos;
}

int
ext_putc(int i, struct bw_external_output* stream)
{
    /*flush buffer if it can hold no more data*/
    if (writer_buffer_full(stream)) {
        if (empty_writer_buffer(stream)) {
            return EOF;
        }
    }

    /*add byte to internal buffer*/
    stream->buffer.data[stream->buffer.pos++] = (uint8_t)i;

    /*return success*/
    return i;
}

int
ext_fwrite(struct bw_external_output* stream,
           const uint8_t *data,
           unsigned data_size)
{
    do {
        /*copy either the total size that can fit in the buffer
          or "data_size" from "data" to the buffer, whichever is less*/
        const unsigned buffer_size = writer_buffer_remaining_size(stream);
        const unsigned to_copy =
            data_size > buffer_size ? buffer_size : data_size;

        memcpy(stream->buffer.data + stream->buffer.pos, data, to_copy);
        stream->buffer.pos += to_copy;
        data += to_copy;
        data_size -= to_copy;

        if (data_size) {
            /*if another pass is required, empty the buffer*/
            if (empty_writer_buffer(stream)) {
                /*write unsuccessful, so return EOF*/
                return EOF;
            }
        }
    } while (data_size);

    return 0;
}

int
ext_setpos_w(struct bw_external_output *stream, void *pos)
{
    /*flush internal buffer before moving to new position*/
    if (!ext_flush_w(stream)) {
        return stream->setpos(stream->user_data, pos);
    } else {
        /*error occurred flushing stream*/
        return EOF;
    }
}

void*
ext_getpos_w(struct bw_external_output *stream)
{
    /*flush internal buffer before retrieving new position*/
    if (!ext_flush_w(stream)) {
        return stream->getpos(stream->user_data);
    } else {
        /*some error occurred when flushing stream*/
        return NULL;
    }
}

int
ext_fseek_w(struct bw_external_output *stream, long position, int whence)
{
    /*flush internal buffer before moving to new position*/
    if (!ext_flush_w(stream)) {
        return stream->seek(stream->user_data, position, whence);
    } else {
        /*error occurred flushing stream*/
        return EOF;
    }
}

int
ext_flush_w(struct bw_external_output* stream)
{
    if (empty_writer_buffer(stream)) {
        return EOF;
    } else {
        return stream->flush(stream->user_data);
    }
}

int
ext_close_w(struct bw_external_output* stream)
{
    if (!ext_flush_w(stream)) {
        return stream->close(stream->user_data);
    } else {
        /*some error occurred when flushing stream*/
        return EOF;
    }
}

void
ext_free_w(struct bw_external_output* stream)
{
    stream->free(stream->user_data);
    free(stream->buffer.data);
    free(stream);
}
