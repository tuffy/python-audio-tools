#ifndef BUFFER_H
#define BUFFER_H

#include <stdint.h>

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

/*the number of bytes remaining to be read
  b is evaluated twice*/
#define BUF_WINDOW_SIZE(b) ((b)->window_end - (b)->window_start)

/*the start of the buffer's data window as a uint8_t pointer
  b is evaluated twice*/
#define BUF_WINDOW_START(b) ((b)->data + (b)->window_start)

/*the end of the buffers's data window as a uint8_t pointer
  b is evaluated twice*/
#define BUF_WINDOW_END(b) ((b)->data + (b)->window_end)

/*returns a new bs_buffer struct which can be appended to and read from

  it must be closed with buf_close() when no longer needed*/
struct bs_buffer*
buf_new(void);

/*deallocates buffer struct*/
void
buf_close(struct bs_buffer *stream);

/*resize buffer to fit at least "additional_bytes", if necessary

  this may alter where stream's "data" points to*/
void
buf_resize(struct bs_buffer *stream, unsigned additional_bytes);

/*makes target's data a duplicate of source's data

  target must not be rewindable since old data will
  no longer be reachable*/
void
buf_copy(const struct bs_buffer *source, struct bs_buffer *target);

/*appends unconsumed data in "source" to "target"*/
void
buf_extend(const struct bs_buffer *source, struct bs_buffer* target);

/*clears out the buffer for possible reuse

  resets window_start, window_end and any marks in progress*/
void
buf_reset(struct bs_buffer *stream);


/*** stdio-like functions for bs_buffer ***/

/*analagous to fgetc, returns EOF at the end of buffer*/
int
buf_getc(struct bs_buffer *stream);

/*analagous to fputc*/
int
buf_putc(int i, struct bs_buffer *stream);

/*analagous to fread

  reads "data_size" bytes from "stream" to "data"
  starting at stream's "window_start"
  and returns the amount of bytes actually read
  (which may be less than the amount requested)*/
unsigned
buf_read(struct bs_buffer *stream, uint8_t *data, unsigned data_size);

/*analgous to fwrite

  appends "data_size" bytes from "data" to "stream" starting at "window_end"*/
void
buf_write(struct bs_buffer *stream, const uint8_t *data, unsigned data_size);

/*gets the current position of the buffer to "pos"

  Note that subsequent calls to buf_putc/buf_write/buf_resize
  may render the position invalid if the window's current position
  is shifted down!

  Call buf_rewindable() to disable shifting out old data
  to disable rewinding in those cases.*/
void
buf_getpos(struct bs_buffer *stream, unsigned *pos);

/*sets the current position of the buffer in "pos"*/
void
buf_setpos(struct bs_buffer *stream, unsigned pos);

/*if rewindable is true, the buffer's window can't be moved down
  to fit more data and can only be appended to
  if false, old data can be discarded as space is needed*/
void
buf_set_rewindable(struct bs_buffer *stream, int rewindable);

#endif
