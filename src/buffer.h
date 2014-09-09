#ifndef BUFFER_H
#define BUFFER_H

#include <stdint.h>
#include <stdio.h>

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

 /*bs_buffer can be thought of as a FIFO queue of byte data

  buf_putc and other data writers append to "data"
  starting from "window_end",
  increasing the size of "data" and "data_size" as necessary to fit

  buf_getc and other data readers pull from the beginning of "data"
  starting from "window_start" to "window_end"

  "rewindable" indicates whether "window_start" can go backwards
  to point at previously read data
  if false, data writers may slide the window down and reuse the buffer
  if true, data writers may only append new data to the buffer*/
struct bs_buffer {
    uint8_t* data;
    unsigned data_size;
    unsigned window_start;
    unsigned window_end;
    int rewindable;
};

typedef unsigned buf_size_t;
typedef unsigned buf_pos_t;

/*returns a new bs_buffer struct which can be appended to and read from

  it must be closed with buf_close() when no longer needed*/
struct bs_buffer*
buf_new(void);

/*deallocates buffer struct*/
void
buf_close(struct bs_buffer *stream);

/*returns the amount of data in the buffer in bytes*/
static inline unsigned
buf_window_size(const struct bs_buffer *stream)
{
    return stream->window_end - stream->window_start;
}

/*returns the amount of data that can be added to the buffer
  without resizing, in bytes*/
static inline unsigned
buf_unused_size(const struct bs_buffer *stream)
{
    return stream->data_size - stream->window_end;
}

/*returns the starting position of the buffer window
  pointing to the first byte that may be read*/
static inline uint8_t*
buf_window_start(const struct bs_buffer *stream)
{
    return stream->data + stream->window_start;
}

/*returns the ending position of the buffer window
  pointing to the first byte that may be written*/
static inline uint8_t*
buf_window_end(const struct bs_buffer *stream)
{
    return stream->data + stream->window_end;
}

/*resize buffer to fit at least "additional_bytes", if necessary

  this may alter where window_start and window_end point to
  unless the stream has been set to be rewindable*/
void
buf_resize(struct bs_buffer *stream, unsigned additional_bytes);


/*clears out the buffer for possible reuse

  resets window_start, window_end and sets stream to be non-rewindable*/
static inline void
buf_reset(struct bs_buffer *stream)
{
    stream->window_start = stream->window_end = 0;
    stream->rewindable = 0;
}


/*** stdio-like functions for bs_buffer ***/

/*analagous to fgetc
  returns byte at beginning of buffer
  returns EOF if no bytes remain in buffer*/
static inline int
buf_getc(struct bs_buffer *stream)
{
    if (stream->window_start < stream->window_end)
        return stream->data[stream->window_start++];
    else
        return EOF;
}

/*analagous to fputc
  places byte "i" at end of buffer*/
static inline int
buf_putc(int i, struct bs_buffer *stream)
{
    if (stream->window_end == stream->data_size) {
        buf_resize(stream, 1);
    }

    stream->data[stream->window_end++] = (uint8_t)i;

    return i;
}

/*analagous to fread

  reads "data_size" bytes from "stream" to "data"
  starting at the beginning of stream
  returns the amount of bytes actually read
  (which may be less than the amount requested)*/
unsigned
buf_read(struct bs_buffer *stream, uint8_t *data, unsigned data_size);

/*analagous to buf_read except that data is ignored rather than returned

  returns the amount of bytes actually skipped*/
unsigned
buf_skip(struct bs_buffer *stream, unsigned data_size);

/*analgous to fwrite

  appends "data_size" bytes from "data" to stream starting at "window_end"*/
void
buf_write(struct bs_buffer *stream, const uint8_t *data, unsigned data_size);

/*places the current position of the buffer in "pos"

  Subsequent calls to buf_write may render that position invalid
  unless the stream has been set to be rewindable.*/
static inline void
buf_getpos(struct bs_buffer *stream, buf_pos_t *pos)
{
    *pos = stream->window_start;
}

/*sets the current position of the buffer to that of "pos"*/
static inline void
buf_setpos(struct bs_buffer *stream, buf_pos_t pos)
{
    stream->window_start = pos;
}

/*analagous to fseek
  note that writing more data to the buffer may render
  seek points invalid unless rewindable is true
  returns 0 on success, nonzero on failure*/
int
buf_fseek(struct bs_buffer *stream, long position, int whence);

/*if rewindable is true, the buffer's window can't be moved down
  to fit more data and can only be appended to
  if false, old data can be discarded as space is needed*/
static inline void
buf_set_rewindable(struct bs_buffer *stream, int rewindable)
{
    stream->rewindable = rewindable;
}

/*appends unconsumed data in "source" to "target"*/
static inline void
buf_extend(const struct bs_buffer *source, struct bs_buffer* target)
{
    buf_write(target, buf_window_start(source), buf_window_size(source));
}

#endif
