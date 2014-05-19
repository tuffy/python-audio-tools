#include "dvd_css.h"
#include "ioctl.h"
#include <string.h>
#include "csstables.h"

/****************************************************************************
* css.c: Functions for DVD authentication and descrambling
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

int
GetBusKey(int i_fd, css_t* css) {
    uint8_t   p_buffer[10];
    uint8_t   p_challenge[2*KEY_SIZE];
    dvd_key_t p_key1;
    dvd_key_t p_key2;
    dvd_key_t p_key_check;
    uint8_t   i_variant = 0;
    int       i_ret = -1;
    int       i;

    i_ret = ioctl_ReportAgid(i_fd, &(css->agid));

    /* We might have to reset hung authentication processes in the drive
     * by invalidating the corresponding AGID'.  As long as we haven't got
     * an AGID, invalidate one (in sequence) and try again. */

    for (i = 0; i_ret == -1 && i < 4 ; ++i) {
        /* This is really _not good_, should be handled by the OS.
         * Invalidating an AGID could make another process fail somewhere
         * in its authentication process. */
        css->agid = i;
        ioctl_InvalidateAgid(i_fd, &(css->agid));
        i_ret = ioctl_ReportAgid(i_fd, &(css->agid));
    }

    /* Unable to authenticate without AGID */
    if (i_ret == -1) return -1;

    /* Setup a challenge, any values should work */
    for (i = 0; i < 10; ++i)
        p_challenge[i] = i;

    /* Get challenge from host */
    for (i = 0; i < 10; ++i)
        p_buffer[9-i] = p_challenge[i];

    /* Send challenge to LU */
    if (ioctl_SendChallenge(i_fd, &(css->agid), p_buffer)) {
        ioctl_InvalidateAgid(i_fd, &(css->agid));
        return -1;
    }

    /* Get key1 from LU */
    if (ioctl_ReportKey1(i_fd, &(css->agid), p_buffer)) {
        ioctl_InvalidateAgid(i_fd, &(css->agid));
        return -1;
    }

    /* Send key1 to host */
    for (i = 0; i < KEY_SIZE; i++)
        p_key1[i] = p_buffer[4-i];
    for (i = 0; i < 32; ++i) {
        CryptKey(0, i, p_challenge, p_key_check);
        if (memcmp(p_key_check, p_key1, KEY_SIZE) == 0)
        {
            i_variant = i;
            break;
        }
    }

    if (i == 32) {
        ioctl_InvalidateAgid(i_fd, &(css->agid));
        return -1;
    }

    /* Get challenge from LU */
    if (ioctl_ReportChallenge(i_fd, &(css->agid), p_buffer)) {
        ioctl_InvalidateAgid(i_fd, &(css->agid));
        return -1;
    }

    /* Send challenge to host */
    for (i = 0; i < 10; ++i)
        p_challenge[i] = p_buffer[9-i];
    CryptKey(1, i_variant, p_challenge, p_key2);

    /* Get key2 from host */
    for (i = 0; i < KEY_SIZE; ++i)
        p_buffer[4-i] = p_key2[i];

    /* Send key2 to LU */
    if (ioctl_SendKey2(i_fd, &(css->agid), p_buffer))
    {
        ioctl_InvalidateAgid(i_fd, &(css->agid));
        return -1;
    }

    /* The drive has accepted us as authentic. */
    memcpy(p_challenge, p_key1, KEY_SIZE);
    memcpy(p_challenge + KEY_SIZE, p_key2, KEY_SIZE);
    CryptKey(2, i_variant, p_challenge, css->p_bus_key);

    return 0;
}

/*****************************************************************************
 * CryptKey : shuffles bits and unencrypt keys.
 *****************************************************************************
 * Used during authentication and disc key negociation in GetBusKey.
 * i_key_type : 0->key1, 1->key2, 2->buskey.
 * i_variant : between 0 and 31.
 *****************************************************************************/
void
CryptKey(int i_key_type, int i_variant,
         uint8_t const *p_challenge, uint8_t *p_key) {
    /* Permutation table for challenge */
    uint8_t pp_perm_challenge[3][10] =
            { { 1, 3, 0, 7, 5, 2, 9, 6, 4, 8 },
              { 6, 1, 9, 3, 8, 5, 7, 4, 0, 2 },
              { 4, 0, 3, 5, 7, 2, 8, 6, 1, 9 } };

    /* Permutation table for variant table for key2 and buskey */
    uint8_t pp_perm_variant[2][32] =
            { { 0x0a, 0x08, 0x0e, 0x0c, 0x0b, 0x09, 0x0f, 0x0d,
                0x1a, 0x18, 0x1e, 0x1c, 0x1b, 0x19, 0x1f, 0x1d,
                0x02, 0x00, 0x06, 0x04, 0x03, 0x01, 0x07, 0x05,
                0x12, 0x10, 0x16, 0x14, 0x13, 0x11, 0x17, 0x15 },
              { 0x12, 0x1a, 0x16, 0x1e, 0x02, 0x0a, 0x06, 0x0e,
                0x10, 0x18, 0x14, 0x1c, 0x00, 0x08, 0x04, 0x0c,
                0x13, 0x1b, 0x17, 0x1f, 0x03, 0x0b, 0x07, 0x0f,
                0x11, 0x19, 0x15, 0x1d, 0x01, 0x09, 0x05, 0x0d } };

    uint8_t p_variants[32] =
            {   0xB7, 0x74, 0x85, 0xD0, 0xCC, 0xDB, 0xCA, 0x73,
                0x03, 0xFE, 0x31, 0x03, 0x52, 0xE0, 0xB7, 0x42,
                0x63, 0x16, 0xF2, 0x2A, 0x79, 0x52, 0xFF, 0x1B,
                0x7A, 0x11, 0xCA, 0x1A, 0x9B, 0x40, 0xAD, 0x01 };

    /* The "secret" key */
    uint8_t p_secret[5] = { 0x55, 0xD6, 0xC4, 0xC5, 0x28 };

    uint8_t p_bits[30], p_scratch[10], p_tmp1[5], p_tmp2[5];
    uint8_t i_lfsr0_o;  /* 1 bit used */
    uint8_t i_lfsr1_o;  /* 1 bit used */
    uint8_t i_css_variant, i_cse, i_index, i_combined, i_carry;
    uint8_t i_val = 0;
    uint32_t i_lfsr0, i_lfsr1;
    int i_term = 0;
    int i_bit;
    int i;

    for (i = 9; i >= 0; --i)
        p_scratch[i] = p_challenge[pp_perm_challenge[i_key_type][i]];

    i_css_variant = ( i_key_type == 0 ) ? i_variant :
                    pp_perm_variant[i_key_type-1][i_variant];

    /*
     * This encryption engine implements one of 32 variations
     * one the same theme depending upon the choice in the
     * variant parameter (0 - 31).
     *
     * The algorithm itself manipulates a 40 bit input into
     * a 40 bit output.
     * The parameter 'input' is 80 bits.  It consists of
     * the 40 bit input value that is to be encrypted followed
     * by a 40 bit seed value for the pseudo random number
     * generators.
     */

    /* Feed the secret into the input values such that
     * we alter the seed to the LFSR's used above,  then
     * generate the bits to play with.
     */
    for( i = 5 ; --i >= 0 ; )
    {
        p_tmp1[i] = p_scratch[5 + i] ^ p_secret[i] ^ p_crypt_tab2[i];
    }

    /*
     * We use two LFSR's (seeded from some of the input data bytes) to
     * generate two streams of pseudo-random bits.  These two bit streams
     * are then combined by simply adding with carry to generate a final
     * sequence of pseudo-random bits which is stored in the buffer that
     * 'output' points to the end of - len is the size of this buffer.
     *
     * The first LFSR is of degree 25,  and has a polynomial of:
     * x^13 + x^5 + x^4 + x^1 + 1
     *
     * The second LSFR is of degree 17,  and has a (primitive) polynomial of:
     * x^15 + x^1 + 1
     *
     * I don't know if these polynomials are primitive modulo 2,  and thus
     * represent maximal-period LFSR's.
     *
     *
     * Note that we take the output of each LFSR from the new shifted in
     * bit,  not the old shifted out bit.  Thus for ease of use the LFSR's
     * are implemented in bit reversed order.
     *
     */

    /* In order to ensure that the LFSR works we need to ensure that the
     * initial values are non-zero.  Thus when we initialise them from
     * the seed,  we ensure that a bit is set.
     */
    i_lfsr0 = ( p_tmp1[0] << 17 ) | ( p_tmp1[1] << 9 ) |
              (( p_tmp1[2] & ~7 ) << 1 ) | 8 | ( p_tmp1[2] & 7 );
    i_lfsr1 = ( p_tmp1[3] << 9 ) | 0x100 | p_tmp1[4];

    i_index = sizeof(p_bits);
    i_carry = 0;

    do
    {
        for( i_bit = 0, i_val = 0 ; i_bit < 8 ; ++i_bit )
        {

            i_lfsr0_o = ( ( i_lfsr0 >> 24 ) ^ ( i_lfsr0 >> 21 ) ^
                        ( i_lfsr0 >> 20 ) ^ ( i_lfsr0 >> 12 ) ) & 1;
            i_lfsr0 = ( i_lfsr0 << 1 ) | i_lfsr0_o;

            i_lfsr1_o = ( ( i_lfsr1 >> 16 ) ^ ( i_lfsr1 >> 2 ) ) & 1;
            i_lfsr1 = ( i_lfsr1 << 1 ) | i_lfsr1_o;

            i_combined = !i_lfsr1_o + i_carry + !i_lfsr0_o;
            /* taking bit 1 */
            i_carry = ( i_combined >> 1 ) & 1;
            i_val |= ( i_combined & 1 ) << i_bit;
        }

        p_bits[--i_index] = i_val;
    } while( i_index > 0 );

    /* This term is used throughout the following to
     * select one of 32 different variations on the
     * algorithm.
     */
    i_cse = p_variants[i_css_variant] ^ p_crypt_tab2[i_css_variant];

    /* Now the actual blocks doing the encryption.  Each
     * of these works on 40 bits at a time and are quite
     * similar.
     */
    i_index = 0;
    for( i = 5, i_term = 0 ; --i >= 0 ; i_term = p_scratch[i] )
    {
        i_index = p_bits[25 + i] ^ p_scratch[i];
        i_index = p_crypt_tab1[i_index] ^ ~p_crypt_tab2[i_index] ^ i_cse;

        p_tmp1[i] = p_crypt_tab2[i_index] ^ p_crypt_tab3[i_index] ^ i_term;
    }
    p_tmp1[4] ^= p_tmp1[0];

    for( i = 5, i_term = 0 ; --i >= 0 ; i_term = p_tmp1[i] )
    {
        i_index = p_bits[20 + i] ^ p_tmp1[i];
        i_index = p_crypt_tab1[i_index] ^ ~p_crypt_tab2[i_index] ^ i_cse;

        p_tmp2[i] = p_crypt_tab2[i_index] ^ p_crypt_tab3[i_index] ^ i_term;
    }
    p_tmp2[4] ^= p_tmp2[0];

    for( i = 5, i_term = 0 ; --i >= 0 ; i_term = p_tmp2[i] )
    {
        i_index = p_bits[15 + i] ^ p_tmp2[i];
        i_index = p_crypt_tab1[i_index] ^ ~p_crypt_tab2[i_index] ^ i_cse;
        i_index = p_crypt_tab2[i_index] ^ p_crypt_tab3[i_index] ^ i_term;

        p_tmp1[i] = p_crypt_tab0[i_index] ^ p_crypt_tab2[i_index];
    }
    p_tmp1[4] ^= p_tmp1[0];

    for( i = 5, i_term = 0 ; --i >= 0 ; i_term = p_tmp1[i] )
    {
        i_index = p_bits[10 + i] ^ p_tmp1[i];
        i_index = p_crypt_tab1[i_index] ^ ~p_crypt_tab2[i_index] ^ i_cse;

        i_index = p_crypt_tab2[i_index] ^ p_crypt_tab3[i_index] ^ i_term;

        p_tmp2[i] = p_crypt_tab0[i_index] ^ p_crypt_tab2[i_index];
    }
    p_tmp2[4] ^= p_tmp2[0];

    for( i = 5, i_term = 0 ; --i >= 0 ; i_term = p_tmp2[i] )
    {
        i_index = p_bits[5 + i] ^ p_tmp2[i];
        i_index = p_crypt_tab1[i_index] ^ ~p_crypt_tab2[i_index] ^ i_cse;

        p_tmp1[i] = p_crypt_tab2[i_index] ^ p_crypt_tab3[i_index] ^ i_term;
    }
    p_tmp1[4] ^= p_tmp1[0];

    for(i = 5, i_term = 0 ; --i >= 0 ; i_term = p_tmp1[i] )
    {
        i_index = p_bits[i] ^ p_tmp1[i];
        i_index = p_crypt_tab1[i_index] ^ ~p_crypt_tab2[i_index] ^ i_cse;

        p_key[i] = p_crypt_tab2[i_index] ^ p_crypt_tab3[i_index] ^ i_term;
    }

    return;
}

/*****************************************************************************
 * GetASF : Get Authentication success flag
 *****************************************************************************
 * Returns :
 *  -1 on ioctl error,
 *  0 if the device needs to be authenticated,
 *  1 either.
 *****************************************************************************/
int
GetASF(int i_fd) {
    int i_asf = 0;

    if( ioctl_ReportASF(i_fd, NULL, &i_asf) != 0 )
    {
        /* The ioctl process has failed */
        return -1;
    }

    return i_asf;
}
