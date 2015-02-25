#include "pcm_conv.h"
#include <stdlib.h>

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

/*******************************
 * private function signatures *
 *******************************/

#define PCM_CONV(name)                              \
    static int                                      \
    pcm_##name##_to_int(const unsigned char *pcm);  \
                                                    \
    static void                                     \
    int_to_##name##_pcm(int i, unsigned char *pcm);

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

/************************************
 * private function implementations *
 ************************************/

static int
pcm_S8_to_int(const unsigned char *pcm)
{

    if (pcm[0] & 0x80) {
        /*negative*/
        return -(int)(0x100 - pcm[0]);
    } else {
        /*positive*/
        return (int)pcm[0];
    }
}

static void
int_to_S8_pcm(int i, unsigned char *pcm)
{
    if (i > 0x7F)
        i = 0x7F;  /*avoid overflow*/
    else if (i < -0x80)
        i = -0x80; /*avoid underflow*/

    if (i >= 0) {
        /*positive*/
        pcm[0] = i;
    } else {
        /*negative*/
        pcm[0] = (1 << 8) - (-i);
    }
}

static int
pcm_U8_to_int(const unsigned char *pcm)
{
    return ((int)pcm[0]) - (1 << 7);
}

static void
int_to_U8_pcm(int i, unsigned char *pcm)
{
    i += (1 << 7);
    pcm[0] = i & 0xFF;
}

static int
pcm_SB16_to_int(const unsigned char *pcm)
{
    if (pcm[0] & 0x80) {
        /*negative*/
        return -(int)(0x10000 - ((pcm[0] << 8) | pcm[1]));
    } else {
        /*positive*/
        return (int)(pcm[0] << 8) | pcm[1];
    }
}

static void
int_to_SB16_pcm(int i, unsigned char *pcm)
{
    if (i > 0x7FFF)
        i = 0x7FFF;
    else if (i < -0x8000)
        i = -0x8000;

    if (i < 0) {
        i = (1 << 16) - (-i);
    }

    pcm[0] = i >> 8;
    pcm[1] = i & 0xFF;
}

static int
pcm_SL16_to_int(const unsigned char *pcm)
{
    if (pcm[1] & 0x80) {
        /*negative*/
        return -(int)(0x10000 - ((pcm[1] << 8) | pcm[0]));
    } else {
        /*positive*/
        return (int)(pcm[1] << 8) | pcm[0];
    }
}

static void
int_to_SL16_pcm(int i, unsigned char *pcm)
{
    if (i > 0x7FFF)
        i = 0x7FFF;
    else if (i < -0x8000)
        i = -0x8000;

    if (i < 0) {
        i = (1 << 16) - (-i);
    }

    pcm[1] = i >> 8;
    pcm[0] = i & 0xFF;
}

static int
pcm_UB16_to_int(const unsigned char *pcm)
{
    return ((int)(pcm[0] << 8) | pcm[1]) - (1 << 15);
}

static void
int_to_UB16_pcm(int i, unsigned char *pcm)
{
    i += (1 << 15);
    pcm[0] = (i >> 8) & 0xFF;
    pcm[1] = i & 0xFF;
}

static int
pcm_UL16_to_int(const unsigned char *pcm)
{
    return ((int)(pcm[1] << 8) | pcm[0]) - (1 << 15);
}

static void
int_to_UL16_pcm(int i, unsigned char *pcm)
{
    i += (1 << 15);
    pcm[1] = (i >> 8) & 0xFF;
    pcm[0] = i & 0xFF;
}

static int
pcm_SB24_to_int(const unsigned char *pcm)
{
    if (pcm[0] & 0x80) {
        /*negative*/
        return -(int)(0x1000000 - ((pcm[0] << 16) | (pcm[1] << 8) | pcm[2]));
    } else {
        /*positive*/
        return (int)((pcm[0] << 16) | (pcm[1] << 8) | pcm[2]);
    }
}

static void
int_to_SB24_pcm(int i, unsigned char *pcm)
{
    if (i > 0x7FFFFF)
        i = 0x7FFFFF;
    else if (i < -0x800000)
        i = -0x800000;

    if (i < 0) {
        i = (1 << 24) - (-i);
    }

    pcm[0] = i >> 16;
    pcm[1] = (i >> 8) & 0xFF;
    pcm[2] = i & 0xFF;
}

static int
pcm_SL24_to_int(const unsigned char *pcm)
{
    if (pcm[2] & 0x80) {
        /*negative*/
        return -(int)(0x1000000 - ((pcm[2] << 16) | (pcm[1] << 8) | pcm[0]));
    } else {
        /*positive*/
        return (int)((pcm[2] << 16) | (pcm[1] << 8) | pcm[0]);
    }
}

static void
int_to_SL24_pcm(int i, unsigned char *pcm)
{
    if (i > 0x7FFFFF)
        i = 0x7FFFFF;
    else if (i < -0x800000)
        i = -0x800000;

    if (i < 0) {
        i = (1 << 24) - (-i);
    }

    pcm[2] = i >> 16;
    pcm[1] = (i >> 8) & 0xFF;
    pcm[0] = i & 0xFF;
}

static int
pcm_UB24_to_int(const unsigned char *pcm)
{
    return ((int)((pcm[0] << 16) | (pcm[1] << 8) | pcm[2])) - (1 << 23);
}

static void
int_to_UB24_pcm(int i, unsigned char *pcm)
{
    i += (1 << 23);
    pcm[0] = (i >> 16) & 0xFF;
    pcm[1] = (i >> 8) & 0xFF;
    pcm[2] = i & 0xFF;
}

static int
pcm_UL24_to_int(const unsigned char *pcm)
{
    return ((int)((pcm[2] << 16) | (pcm[1] << 8) | pcm[0])) - (1 << 23);
}

static void
int_to_UL24_pcm(int i, unsigned char *pcm)
{
    i += (1 << 23);
    pcm[2] = (i >> 16) & 0xFF;
    pcm[1] = (i >> 8) & 0xFF;
    pcm[0] = i & 0xFF;
}
