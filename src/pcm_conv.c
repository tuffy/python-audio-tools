#include "pcm_conv.h"
#include <stdlib.h>
#include <math.h>

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

/*******************************
 * private function signatures *
 *******************************/

#define PCM_CONV(name)                                     \
    static void                                            \
    pcm_##name##_to_int(unsigned total_samples,            \
                        const unsigned char pcm_samples[], \
                        int int_samples[]);                \
                                                           \
    static void                                            \
    int_to_##name##_pcm(unsigned total_samples,            \
                        const int int_samples[],           \
                        unsigned char pcm_samples[]);

PCM_CONV(S8)
PCM_CONV(U8)
PCM_CONV(SB16)
PCM_CONV(SL16)
PCM_CONV(UB16)
PCM_CONV(UL16)
PCM_CONV(SB24)
PCM_CONV(SL24)
PCM_CONV(UB24)
PCM_CONV(UL24)

#define PCM_INT_CONV_DEFS(bits)                           \
    static void                                           \
    int_##bits##_to_double(unsigned total_samples,        \
                           const int int_samples[],       \
                           double double_samples[]);      \
                                                          \
    static void                                           \
    int_##bits##_to_float(unsigned total_samples,         \
                          const int int_samples[],        \
                          float float_samples[]);         \
                                                          \
    static void                                           \
    double_to_##bits##_int(unsigned total_samples,        \
                           const double double_samples[], \
                           int int_samples[]);            \
                                                          \
    static void                                           \
    float_to_##bits##_int(unsigned total_samples,         \
                          const float float_samples[],    \
                          int int_samples[]);

PCM_INT_CONV_DEFS(8)
PCM_INT_CONV_DEFS(16)
PCM_INT_CONV_DEFS(24)

/***********************************
 * public function implementations *
 ***********************************/

pcm_to_int_f
pcm_to_int_converter(unsigned bits_per_sample,
                     int is_big_endian,
                     int is_signed)
{
    switch (bits_per_sample) {
    case 8:
        if (is_signed) {
            return pcm_S8_to_int;
        } else {
            return pcm_U8_to_int;
        }
    case 16:
        if (is_signed) {
            return is_big_endian ? pcm_SB16_to_int : pcm_SL16_to_int;
        } else {
            return is_big_endian ? pcm_UB16_to_int : pcm_UL16_to_int;
        }
    case 24:
        if (is_signed) {
            return is_big_endian ? pcm_SB24_to_int : pcm_SL24_to_int;
        } else {
            return is_big_endian ? pcm_UB24_to_int : pcm_UL24_to_int;
        }
    default:
        return NULL;
    }
}

int_to_pcm_f
int_to_pcm_converter(unsigned bits_per_sample,
                     int is_big_endian,
                     int is_signed)
{
    switch (bits_per_sample) {
    case 8:
        if (is_signed) {
            return int_to_S8_pcm;
        } else {
            return int_to_U8_pcm;
        }
    case 16:
        if (is_signed) {
            return is_big_endian ? int_to_SB16_pcm : int_to_SL16_pcm;
        } else {
            return is_big_endian ? int_to_UB16_pcm : int_to_UL16_pcm;
        }
    case 24:
        if (is_signed) {
            return is_big_endian ? int_to_SB24_pcm : int_to_SL24_pcm;
        } else {
            return is_big_endian ? int_to_UB24_pcm : int_to_UL24_pcm;
        }
    default:
        return NULL;
    }
}

int_to_double_f
int_to_double_converter(unsigned bits_per_sample)
{
    switch (bits_per_sample) {
    case 8:
        return int_8_to_double;
    case 16:
        return int_16_to_double;
    case 24:
        return int_24_to_double;
    default:
        return NULL;
    }
}

int_to_float_f
int_to_float_converter(unsigned bits_per_sample)
{
    switch (bits_per_sample) {
    case 8:
        return int_8_to_float;
    case 16:
        return int_16_to_float;
    case 24:
        return int_24_to_float;
    default:
        return NULL;
    }
}

double_to_int_f
double_to_int_converter(unsigned bits_per_sample)
{
    switch (bits_per_sample) {
    case 8:
        return double_to_8_int;
    case 16:
        return double_to_16_int;
    case 24:
        return double_to_24_int;
    default:
        return NULL;
    }
}

float_to_int_f
float_to_int_converter(unsigned bits_per_sample)
{
    switch (bits_per_sample) {
    case 8:
        return float_to_8_int;
    case 16:
        return float_to_16_int;
    case 24:
        return float_to_24_int;
    default:
        return NULL;
    }
}

/************************************
 * private function implementations *
 ************************************/

static void
pcm_S8_to_int(unsigned total_samples,
              const unsigned char pcm_samples[],
              int int_samples[])
{
    for (; total_samples; total_samples--) {
        if (pcm_samples[0] & 0x80) {
            /*negative*/
            int_samples[0] = -(int)(0x100 - pcm_samples[0]);
        } else {
            /*positive*/
            int_samples[0] = (int)pcm_samples[0];
        }
        pcm_samples += 1;
        int_samples += 1;
    }
}

static void
int_to_S8_pcm(unsigned total_samples,
              const int int_samples[],
              unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        if (i > 0x7F)
            i = 0x7F;  /*avoid overflow*/
        else if (i < -0x80)
            i = -0x80; /*avoid underflow*/

        if (int_samples[0] >= 0) {
            /*positive*/
            pcm_samples[0] = i;
        } else {
            /*negative*/
            pcm_samples[0] = (1 << 8) - (-i);
        }

        int_samples += 1;
        pcm_samples += 1;
    }
}

static void
pcm_U8_to_int(unsigned total_samples,
              const unsigned char pcm_samples[],
              int int_samples[])
{
    for (; total_samples; total_samples--) {
        int_samples[0] = ((int)pcm_samples[0]) - (1 << 7);
        pcm_samples += 1;
        int_samples += 1;
    }
}

static void
int_to_U8_pcm(unsigned total_samples,
              const int int_samples[],
              unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        i += (1 << 7);

        pcm_samples[0] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 1;
    }
}

static void
pcm_SB16_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        if (pcm_samples[0] & 0x80) {
            /*negative*/
            int_samples[0] =
                -(int)(0x10000 - ((pcm_samples[0] << 8) | pcm_samples[1]));
        } else {
            /*positive*/
            int_samples[0] =
                (int)(pcm_samples[0] << 8) | pcm_samples[1];
        }
        pcm_samples += 2;
        int_samples += 1;
    }
}

static void
int_to_SB16_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        if (i > 0x7FFF)
            i = 0x7FFF;
        else if (i < -0x8000)
            i = -0x8000;

        if (i < 0) {
            i = (1 << 16) - (-i);
        }

        pcm_samples[0] = i >> 8;
        pcm_samples[1] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 2;
    }
}

static void
pcm_SL16_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        if (pcm_samples[1] & 0x80) {
            /*negative*/
            int_samples[0] =
               -(int)(0x10000 - ((pcm_samples[1] << 8) | pcm_samples[0]));
        } else {
            /*positive*/
            int_samples[0] =
               (int)(pcm_samples[1] << 8) | pcm_samples[0];
        }
        pcm_samples += 2;
        int_samples += 1;
    }
}

static void
int_to_SL16_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        if (i > 0x7FFF)
            i = 0x7FFF;
        else if (i < -0x8000)
            i = -0x8000;

        if (i < 0) {
            i = (1 << 16) - (-i);
        }

        pcm_samples[1] = i >> 8;
        pcm_samples[0] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 2;
    }
}

static void
pcm_UB16_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        int_samples[0] =
            ((int)(pcm_samples[0] << 8) | pcm_samples[1]) - (1 << 15);
        pcm_samples += 2;
        int_samples += 1;
    }
}

static void
int_to_UB16_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        i += (1 << 15);

        pcm_samples[0] = (i >> 8) & 0xFF;
        pcm_samples[1] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 2;
    }
}

static void
pcm_UL16_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        int_samples[0] =
            ((int)(pcm_samples[1] << 8) | pcm_samples[0]) - (1 << 15);
        pcm_samples += 2;
        int_samples += 1;
    }
}

static void
int_to_UL16_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        i += (1 << 15);

        pcm_samples[1] = (i >> 8) & 0xFF;
        pcm_samples[0] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 2;
    }
}

static void
pcm_SB24_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        if (pcm_samples[0] & 0x80) {
            /*negative*/
            int_samples[0] =
                -(int)(0x1000000 - ((pcm_samples[0] << 16) |
                                    (pcm_samples[1] << 8) |
                                    pcm_samples[2]));
        } else {
            /*positive*/
            int_samples[0] =
                (int)((pcm_samples[0] << 16) |
                      (pcm_samples[1] << 8) |
                      pcm_samples[2]);
        }

        pcm_samples += 3;
        int_samples += 1;
    }
}

static void
int_to_SB24_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        if (i > 0x7FFFFF)
            i = 0x7FFFFF;
        else if (i < -0x800000)
            i = -0x800000;

        if (i < 0) {
            i = (1 << 24) - (-i);
        }

        pcm_samples[0] = i >> 16;
        pcm_samples[1] = (i >> 8) & 0xFF;
        pcm_samples[2] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 3;
    }
}

static void
pcm_SL24_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        if (pcm_samples[2] & 0x80) {
            /*negative*/
            int_samples[0] =
                -(int)(0x1000000 - ((pcm_samples[2] << 16) |
                                    (pcm_samples[1] << 8) |
                                    pcm_samples[0]));
        } else {
            /*positive*/
            int_samples[0] =
                (int)((pcm_samples[2] << 16) |
                      (pcm_samples[1] << 8) |
                      pcm_samples[0]);
        }

        pcm_samples += 3;
        int_samples += 1;
    }
}

static void
int_to_SL24_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        if (i > 0x7FFFFF)
            i = 0x7FFFFF;
        else if (i < -0x800000)
            i = -0x800000;

        if (i < 0) {
            i = (1 << 24) - (-i);
        }

        pcm_samples[2] = i >> 16;
        pcm_samples[1] = (i >> 8) & 0xFF;
        pcm_samples[0] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 3;
    }

}

static void
pcm_UB24_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        int_samples[0] =
            ((int)((pcm_samples[0] << 16) |
                   (pcm_samples[1] << 8) |
                   pcm_samples[2])) - (1 << 23);
        pcm_samples += 3;
        int_samples += 1;
    }
}

static void
int_to_UB24_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        i += (1 << 23);

        pcm_samples[0] = (i >> 16) & 0xFF;
        pcm_samples[1] = (i >> 8) & 0xFF;
        pcm_samples[2] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 3;
    }
}

static void
pcm_UL24_to_int(unsigned total_samples,
                const unsigned char pcm_samples[],
                int int_samples[])
{
    for (; total_samples; total_samples--) {
        int_samples[0] = ((int)((pcm_samples[2] << 16) |
                                (pcm_samples[1] << 8) |
                                pcm_samples[0])) - (1 << 23);
        pcm_samples += 3;
        int_samples += 1;
    }
}

static void
int_to_UL24_pcm(unsigned total_samples,
                const int int_samples[],
                unsigned char pcm_samples[])
{
    for (; total_samples; total_samples--) {
        register int i = int_samples[0];

        i += (1 << 23);

        pcm_samples[2] = (i >> 16) & 0xFF;
        pcm_samples[1] = (i >> 8) & 0xFF;
        pcm_samples[0] = i & 0xFF;

        int_samples += 1;
        pcm_samples += 3;
    }
}

#include <stdio.h>

#define PCM_INT_CONV(BITS, NEGATIVE_MIN, POSITIVE_MAX)                     \
  static void                                                              \
  int_##BITS##_to_double(unsigned total_samples,                           \
                         const int int_samples[],                          \
                         double double_samples[])                          \
  {                                                                        \
      for (; total_samples; total_samples--) {                             \
          const register int i = int_samples[0];                           \
          if (i >= 0) {                                                    \
              double_samples[0] = (double)i / POSITIVE_MAX;                \
          } else {                                                         \
              double_samples[0] = (double)i / -(NEGATIVE_MIN);             \
          }                                                                \
          int_samples += 1;                                                \
          double_samples += 1;                                             \
      }                                                                    \
  }                                                                        \
                                                                           \
  static void                                                              \
  int_##BITS##_to_float(unsigned total_samples,                            \
                        const int int_samples[],                           \
                        float float_samples[])                             \
  {                                                                        \
      for (; total_samples; total_samples--) {                             \
          const register int i = int_samples[0];                           \
          if (i >= 0) {                                                    \
              float_samples[0] = (float)i / POSITIVE_MAX;                  \
          } else {                                                         \
              float_samples[0] = (float)i / -(NEGATIVE_MIN);               \
          }                                                                \
          int_samples += 1;                                                \
          float_samples += 1;                                              \
      }                                                                    \
  }                                                                        \
                                                                           \
  static void                                                              \
  double_to_##BITS##_int(unsigned total_samples,                           \
                         const double double_samples[],                    \
                         int int_samples[])                                \
  {                                                                        \
      for (; total_samples; total_samples--) {                             \
          const register double d = double_samples[0];                     \
          const int value =                                                \
              d * (signbit(d) ? -(NEGATIVE_MIN) : POSITIVE_MAX);           \
          int_samples[0] = MIN(MAX(value, NEGATIVE_MIN), POSITIVE_MAX);    \
          double_samples += 1;                                             \
          int_samples += 1;                                                \
      }                                                                    \
  }                                                                        \
                                                                           \
  static void                                                              \
  float_to_##BITS##_int(unsigned total_samples,                            \
                        const float float_samples[],                       \
                        int int_samples[])                                 \
  {                                                                        \
      for (; total_samples; total_samples--) {                             \
          const register double d = float_samples[0];                      \
          const int value =                                                \
              d * (signbit(d) ? -(NEGATIVE_MIN) : POSITIVE_MAX);           \
          int_samples[0] = MIN(MAX(value, NEGATIVE_MIN), POSITIVE_MAX);    \
          float_samples += 1;                                              \
          int_samples += 1;                                                \
      }                                                                    \
  }

PCM_INT_CONV(8, -128, 127)
PCM_INT_CONV(16, -32768, 32767)
PCM_INT_CONV(24, -8388608, 8388607)
