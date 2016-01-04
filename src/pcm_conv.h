#ifndef PCM_CONV_H
#define PCM_CONV_H

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2016  Brian Langenberger

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

/*for turning raw PCM bytes into integer values

  given "total_samples * (bits_per_sample / 8)" PCM samples
  converts to "total_samples" integer samples*/
typedef void (*pcm_to_int_f)(unsigned total_samples,
                             const unsigned char pcm_samples[],
                             int int_samples[]);

pcm_to_int_f
pcm_to_int_converter(unsigned bits_per_sample,
                     int is_big_endian,
                     int is_signed);

/*for turning integer values into raw PCM bytes

  given "total_samples" integer samples
  converts to "total_samples * (bits_per_sample / 8)" PCM samples*/
typedef void (*int_to_pcm_f)(unsigned total_samples,
                             const int int_samples[],
                             unsigned char pcm_samples[]);

int_to_pcm_f
int_to_pcm_converter(unsigned bits_per_sample,
                     int is_big_endian,
                     int is_signed);

/*for turning integer values with the given bits-per-sample
  into double values between -1.0 and 1.0

  given "total_samples" integer samples
  outputs "total_samples" double samples*/
typedef void (*int_to_double_f)(unsigned total_samples,
                                const int int_samples[],
                                double double_samples[]);

int_to_double_f
int_to_double_converter(unsigned bits_per_sample);


/*for turning integer values with the given bits-per-sample
  into float values between -1.0 and 1.0

  given "total_samples" integer samples
  outputs "total_samples" float samples*/
typedef void (*int_to_float_f)(unsigned total_samples,
                               const int int_samples[],
                               float float_samples[]);

int_to_float_f
int_to_float_converter(unsigned bits_per_sample);


/*for turning double values between [-1.0 .. 1.0] (inclusive)
  into integer values with the given bits-per-sample

  given "total_samples" double samples
  outputs "total_samples" integer samples*/
typedef void (*double_to_int_f)(unsigned total_samples,
                                const double double_samples[],
                                int int_samples[]);

double_to_int_f
double_to_int_converter(unsigned bits_per_sample);



/*for turning float values between [-1.0 .. 1.0] (inclusive)
  into integer values with the given bits-per-sample

  given "total_samples" float samples
  outputs "total_samples" integer samples*/
typedef void (*float_to_int_f)(unsigned total_samples,
                               const float float_samples[],
                               int int_samples[]);

float_to_int_f
float_to_int_converter(unsigned bits_per_sample);

#endif
