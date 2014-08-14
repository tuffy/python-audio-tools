#include "func_io.h"

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

struct br_external_input*
ext_open_r(void* user_data,
           unsigned buffer_size,
           ext_read_f read,
           ext_close_f close,
           ext_free_f free)
{
    struct br_external_input* input = malloc(sizeof(struct br_external_input));

    input->user_data = user_data;
    input->read = read;
    input->close = close;
    input->free = free;

    input->buffer = buf_new();
    input->buffer_size = buffer_size;

    return input;
}

int
ext_getc(struct br_external_input* stream)
{
    struct bs_buffer* buffer = stream->buffer;
    if (!buf_window_size(buffer)) {
        /*buffer is empty, so try to refill from external function*/
        if (stream->read(stream->user_data,
                         buffer,
                         stream->buffer_size)) {
            /*read unsuccessful, so return EOF*/
            return EOF;
        }
    }
    /*this may return EOF if the read was unable to add more data*/
    return buf_getc(buffer);
}

unsigned
ext_fread(struct br_external_input* stream,
          uint8_t* data,
          unsigned data_size)
{
    struct bs_buffer* buffer = stream->buffer;

    /*if there's enough bytes in the buffer*/
    if (data_size <= buf_window_size(buffer)) {
        /*simply copy them directly to "data"
          and return the amount read*/

        return buf_read(buffer, data, data_size);
    } else {
        /*otherwise, populate the buffer with read() calls*/
        while (data_size > buf_window_size(buffer)) {
            const buf_size_t old_size = buf_window_size(buffer);
            if (!stream->read(stream->user_data,
                              buffer,
                              stream->buffer_size) &&
                (buf_window_size(buffer) > old_size)) {
                /*as long as the reads are successful
                  and the buffer continues to grow*/
                continue;
            } else {
                /*otherwise, stop reading and return what we have*/
                break;
            }
        }

        /*read as much of the buffer as necessary/possible to "bytes"
          and return the amount actually read*/
        return buf_read(buffer, data, data_size);
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
    buf_close(stream->buffer);
    free(stream);
}

struct bw_external_output*
ext_open_w(void* user_data,
           unsigned buffer_size,
           ext_write_f write,
           ext_seek_f seek,
           ext_tell_f tell,
           ext_free_pos_f free_pos,
           ext_flush_f flush,
           ext_close_f close,
           ext_free_f free)
{
    struct bw_external_output* output =
        malloc(sizeof(struct bw_external_output));
    output->user_data = user_data;
    output->write = write;
    output->seek = seek;
    output->tell = tell;
    output->free_pos = free_pos;
    output->flush = flush;
    output->close = close;
    output->free = free;

    output->buffer = buf_new();
    output->buffer_size = buffer_size;

    return output;
}

int
ext_putc(int i, struct bw_external_output* stream)
{
    struct bs_buffer* buffer = stream->buffer;

    /*add byte to internal buffer*/
    buf_putc(i, buffer);

    /*then flush internal buffer while it is too large*/
    while (buf_window_size(buffer) >= stream->buffer_size) {
        stream->write(stream->user_data, buffer, stream->buffer_size);
    }

    return 0;
}

void
ext_fwrite(struct bw_external_output* stream,
           const uint8_t *data,
           unsigned data_size)
{
    struct bs_buffer* buffer = stream->buffer;

    /*add data to internal buffer*/
    buf_write(buffer, data, data_size);

    /*then flush internal buffer while it is too large*/
    while (buf_window_size(buffer) >= stream->buffer_size) {
        stream->write(stream->user_data, buffer, stream->buffer_size);
    }
}

void
ext_seek_w(struct bw_external_output *stream, void *pos)
{
    /*flush internal buffer before moving to new position*/
    ext_flush_w(stream);
    stream->seek(stream->user_data, pos);
}

void*
ext_tell_w(struct bw_external_output *stream)
{
    /*flush internal buffer before retrieving new position*/
    ext_flush_w(stream);
    return stream->tell(stream->user_data);
}

void
ext_free_pos_w(struct bw_external_output *stream, void *pos)
{
    stream->free_pos(pos);
}

void
ext_flush_w(struct bw_external_output* stream)
{
    struct bs_buffer* buffer = stream->buffer;
    while (buf_window_size(buffer) > 0) {
        stream->write(stream->user_data, buffer, buf_window_size(buffer));
    }
    stream->flush(stream->user_data);
}

void
ext_close_w(struct bw_external_output* stream)
{
    ext_flush_w(stream);
    stream->close(stream->user_data);
}

void
ext_free_w(struct bw_external_output* stream)
{
    stream->free(stream->user_data);
    buf_close(stream->buffer);
    free(stream);
}
