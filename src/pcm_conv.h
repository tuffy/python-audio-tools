#ifndef PCM_CONV_H
#define PCM_CONV_H

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

/*for turning raw PCM bytes into integer values*/
typedef int (*pcm_to_int_f)(const unsigned char *pcm);

pcm_to_int_f
pcm_to_int_converter(unsigned bits_per_sample,
                     int is_big_endian,
                     int is_signed);

/*for turning integer values into raw PCM bytes*/
typedef void (*int_to_pcm_f)(int i, unsigned char *pcm);

int_to_pcm_f
int_to_pcm_converter(unsigned bits_per_sample,
                     int is_big_endian,
                     int is_signed);

#endif
