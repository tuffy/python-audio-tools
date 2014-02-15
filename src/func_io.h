#ifndef FUNCIO_H
#define FUNCIO_H

#include "buffer.h"
#include <stdio.h>
#include <stdlib.h>

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

/*casts for inserting functions with non-void pointers into ext_open_r*/

/*returns 0 on successful read, 1 if a read error occurs*/
typedef int (*ext_read_f)(void* user_data,
                          struct bs_buffer* buffer,
                          unsigned buffer_size);
typedef void (*ext_close_f)(void* user_data);
typedef void (*ext_free_f)(void* user_data);

/*casts for inserting functions with non-void pointers into ext_open_w*/

/*returns 0 on successful write, 1 if a write error occurs*/
typedef int (*ext_write_f)(void* user_data,
                           struct bs_buffer* buffer,
                           unsigned buffer_size);
typedef void (*ext_flush_f)(void* user_data);

struct br_external_input {
    void* user_data;
    ext_read_f read;
    ext_close_f close;
    ext_free_f free;

    struct bs_buffer* buffer;
    unsigned buffer_size;
};

struct bw_external_output {
    void* user_data;
    ext_write_f write;
    ext_flush_f flush;
    ext_close_f close;
    ext_free_f free;

    struct bs_buffer* buffer;
    unsigned buffer_size;
};

/*** stdio-like functions for br_external_input ***/

/*analagous to fopen for reading*/
struct br_external_input*
ext_open_r(void* user_data,
           unsigned buffer_size,
           ext_read_f read,
           ext_close_f close,
           ext_free_f free);

/*analagous to fgetc

  returns EOF and end of stream or if a read error occurs*/
int
ext_getc(struct br_external_input* stream);

/*analagous to fread

  reads "data_size" bytes from "stream" to "data"
  and returns the amount of bytes actually read
  (which may be less than the amount requested)*/
unsigned
ext_fread(struct br_external_input* stream,
          uint8_t* data,
          unsigned data_size);

/*analagous to fclose

  this calls the passed-in close() function
  but doesn't deallocate "stream" itself*/
void
ext_close_r(struct br_external_input* stream);

/*this calls the passed-in free() function
  before deallocating "stream" itself*/
void
ext_free_r(struct br_external_input* stream);

/*** stdio-like functions for bw_external_input ***/

/*analagous to fopen for writing*/
struct bw_external_output*
ext_open_w(void* user_data,
           unsigned buffer_size,
           ext_write_f write,
           ext_flush_f flush,
           ext_close_f close,
           ext_free_f free);

/*analagous to fputc*/
int
ext_putc(int i, struct bw_external_output* stream);

/*analagous to fwrite*/
void
ext_fwrite(struct bw_external_output* stream,
           const uint8_t *data,
           unsigned data_size);

/*analagous to fflush,
  this sends all buffered bytes to write function
  and calls passed-in flush() function*/
void
ext_flush_w(struct bw_external_output* stream);

/*analagous to fclose

  this flushes output and calls passed-in close() function
  but doesn't deallocate "stream" itself*/
void
ext_close_w(struct bw_external_output* stream);

/*this calls the passed-in free() function
  before deallocating "stream"*/
void
ext_free_w(struct bw_external_output* stream);


#endif
