#ifndef A_SHN_ENCODE
#define A_SHN_ENCODE

#include <Python.h>

#include <stdint.h>
#include "../bitstream_w.h"
#include "../array.h"

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2010  Brian Langenberger

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

typedef enum {SHN_FN_DIFF1,
	      SHN_FN_DIFF2,
	      SHN_FN_DIFF3,
	      SHN_FN_ZERO,
	      SHN_FN_BLOCKSIZE,
	      SHN_FN_QUIT} flac_command_type;

typedef enum {OK,ERROR} status;

#endif
