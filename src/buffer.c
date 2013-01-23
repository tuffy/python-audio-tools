#include "buffer.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

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
    stream->rewindable = 0;
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
    if (additional_bytes > (stream->data_size - stream->window_end)) {
        if ((stream->window_start > 0) && !stream->rewindable) {
            /*we don't need to rewind the buffer
              so shift window down before extending buffer to add more space*/
            if (BUF_WINDOW_SIZE(stream)) {
                memmove(stream->data,
                        BUF_WINDOW_START(stream),
                        BUF_WINDOW_SIZE(stream));
            }
            stream->window_end -= stream->window_start;
            stream->window_start = 0;

            if (additional_bytes > (stream->data_size - stream->window_end)) {
                /*only perform resizing if space still needed
                  after shifting the window down*/
                while (additional_bytes > (stream->data_size -
                                           stream->window_end)) {
                    stream->data_size *= 2;
                }
            }
        } else {
            while (additional_bytes > (stream->data_size -
                                       stream->window_end)) {
                stream->data_size *= 2;
            }
        }

        stream->data = realloc(stream->data, stream->data_size);
    }
}

void
buf_copy(const struct bs_buffer *source, struct bs_buffer *target)
{
    assert(target->rewindable == 0);

    if (target->data_size < source->data_size) {
        target->data_size = source->data_size;
        target->data = realloc(target->data, target->data_size);
    }

    memcpy(target->data, source->data, source->data_size);
    target->window_start = source->window_start;
    target->window_end = source->window_end;
}

void
buf_extend(const struct bs_buffer *source, struct bs_buffer* target)
{
    buf_write(target, BUF_WINDOW_START(source), BUF_WINDOW_SIZE(source));
}

void
buf_reset(struct bs_buffer *stream)
{
    stream->window_start = stream->window_end = 0;
    stream->rewindable = 0;
}

int
buf_getc(struct bs_buffer *stream)
{
    if (stream->window_start < stream->window_end)
        return stream->data[stream->window_start++];
    else
        return EOF;
}

int
buf_putc(int i, struct bs_buffer *stream) {
    if (stream->window_end == stream->data_size) {
        buf_resize(stream, 1);
    }

    stream->data[stream->window_end++] = (uint8_t)i;

    return i;
}

unsigned
buf_read(struct bs_buffer *stream, uint8_t *data, unsigned data_size)
{
    const unsigned to_read = MIN(data_size, BUF_WINDOW_SIZE(stream));
    memcpy(data, BUF_WINDOW_START(stream), to_read);
    stream->window_start += to_read;
    return to_read;
}

void
buf_write(struct bs_buffer *stream, const uint8_t* data, unsigned data_size)
{
    buf_resize(stream, data_size);
    memcpy(BUF_WINDOW_END(stream), data, (size_t)data_size);
    stream->window_end += data_size;
}

void
buf_getpos(struct bs_buffer *stream, unsigned *pos)
{
    *pos = stream->window_start;
}

void
buf_setpos(struct bs_buffer *stream, unsigned pos)
{
    stream->window_start = pos;
}

void
buf_set_rewindable(struct bs_buffer *stream, int rewindable)
{
    stream->rewindable = rewindable;
}
