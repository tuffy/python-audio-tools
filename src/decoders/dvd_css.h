#include <stdint.h>

/****************************************************************************
 * css.h: Functions for DVD authentication and descrambling
 *****************************************************************************
 * Copyright (C) 1999-2008 VideoLAN
 *
 * Authors: Stéphane Borel <stef@via.ecp.fr>
 * Håkan Hjort <d95hjort@dtek.chalmers.se>
 *
 * based on:
 * - css-auth by Derek Fawcus <derek@spider.com>
 * - DVD CSS ioctls example program by Andrew T. Veliath <andrewtv@usa.net>
 * - The Divide and conquer attack by Frank A. Stevenson <frank@funcom.com>
 * (see http://www-2.cs.cmu.edu/~dst/DeCSS/FrankStevenson/index.html)
 * - DeCSSPlus by Ethan Hawke
 * - DecVOB
 * see http://www.lemuria.org/DeCSS/ by Tom Vogt for more information.
 *
 * Modified 2011 by Brian Langenberger for use in Python Audio Tools
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this library; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 *****************************************************************************/

#define KEY_SIZE 5

typedef uint8_t dvd_key_t[KEY_SIZE];

typedef struct {
    int       protection;
    int       agid;
    dvd_key_t p_bus_key;
    dvd_key_t p_disc_key;
    dvd_key_t p_title_key;
} css_t;

int
GetBusKey(int i_fd, css_t* css);

int
GetASF(int i_fd);

void
CryptKey(int i_key_type, int i_variant,
         uint8_t const *p_challenge, uint8_t *p_key);
