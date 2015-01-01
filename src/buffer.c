#include "buffer.h"
#include <string.h>
#include <stdlib.h>
#include <assert.h>

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

struct bs_buffer*
buf_new(void)
{
    struct bs_buffer* stream = malloc(sizeof(struct bs_buffer));
    stream->data = malloc(1);
    stream->data_size = 1;
    stream->window_start = 0;
    stream->window_end = 0;
    return stream;
}

void
buf_close(struct bs_buffer *stream)
{
    free(stream->data);
    free(stream);
}

void
buf_resize(struct bs_buffer *stream, unsigned additional_bytes)
{
    /*only perform resize if space actually needed*/
    if (additional_bytes > buf_unused_size(stream)) {
        if (stream->window_start > 0) {
            /*shift window down before extending buffer to add more space*/
            if (buf_window_size(stream)) {
                memmove(stream->data,
                        buf_window_start(stream),
                        buf_window_size(stream));
            }
            stream->window_end -= stream->window_start;
            stream->window_start = 0;
        }

        while (additional_bytes > buf_unused_size(stream)) {
            stream->data_size *= 2;
        }

        stream->data = realloc(stream->data, stream->data_size);
    }
}

unsigned
buf_read(struct bs_buffer *stream, uint8_t *data, unsigned data_size)
{
    const buf_size_t to_read = MIN(data_size, buf_window_size(stream));
    memcpy(data, buf_window_start(stream), to_read);
    stream->window_start += to_read;
    return to_read;
}

unsigned
buf_skip(struct bs_buffer *stream, unsigned data_size)
{
    const buf_size_t to_read = MIN(data_size, buf_window_size(stream));
    stream->window_start += to_read;
    return to_read;
}

void
buf_write(struct bs_buffer *stream, const uint8_t* data, unsigned data_size)
{
    buf_resize(stream, data_size);
    memcpy(buf_window_end(stream), data, (size_t)data_size);
    stream->window_end += data_size;
}
