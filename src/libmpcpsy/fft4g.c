/*
 * Musepack audio compression
 * Copyright (c) 2005-2009, The Musepack Development Team
 * Copyright (C) 1999-2004 Buschmann/Klemm/Piecha/Wolf
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#include "libmpcpsy.h"
#include <mpc/mpcmath.h>

/* F U N C T I O N S */
static          void  makewt       ( const int nw, int* ip, float* w );
static          void  makect       ( const int nc, int* ip, float* c );

# define cftmdl(n,l,a,w)   cftmdl_i386  ( n, l, a, w )


/* -------- child routines -------- */
static mpc_inline void
bitrv2 ( const int n, int* ip, float* a )
{
	int    j, j1, k, k1, l, m, m2;
	float  xr, xi, yr, yi;

	ip[0] = 0;
	l     = n;
	m     = 1;
	while ( (m << 3) < l ) {
		l >>= 1;
		for ( j = 0; j < m; j++ ) {
			ip[m + j] = ip[j] + l;
		}
		m <<= 1;
	}
	m2 = 2 * m;
	if ( (m << 3) == l ) {
		for ( k = 0; k < m; k++ ) {
			for ( j = 0; j < k; j++ ) {
				j1        = 2 * j + ip[k];
				k1        = 2 * k + ip[j];
				xr        = a[j1];
				xi        = a[j1 + 1];
				yr        = a[k1];
				yi        = a[k1 + 1];
				a[j1]     = yr;
				a[j1 + 1] = yi;
				a[k1]     = xr;
				a[k1 + 1] = xi;
				j1       += m2;
				k1       += 2 * m2;
				xr        = a[j1];
				xi        = a[j1 + 1];
				yr        = a[k1];
				yi        = a[k1 + 1];
				a[j1]     = yr;
				a[j1 + 1] = yi;
				a[k1]     = xr;
				a[k1 + 1] = xi;
				j1       += m2;
				k1       -= m2;
				xr        = a[j1];
				xi        = a[j1 + 1];
				yr        = a[k1];
				yi        = a[k1 + 1];
				a[j1]     = yr;
				a[j1 + 1] = yi;
				a[k1]     = xr;
				a[k1 + 1] = xi;
				j1       += m2;
				k1       += 2 * m2;
				xr        = a[j1];
				xi        = a[j1 + 1];
				yr        = a[k1];
				yi        = a[k1 + 1];
				a[j1]     = yr;
				a[j1 + 1] = yi;
				a[k1]     = xr;
				a[k1 + 1] = xi;
			}
			j1        = 2 * k + m2 + ip[k];
			k1        = j1 + m2;
			xr        = a[j1];
			xi        = a[j1 + 1];
			yr        = a[k1];
			yi        = a[k1 + 1];
			a[j1]     = yr;
			a[j1 + 1] = yi;
			a[k1]     = xr;
			a[k1 + 1] = xi;
		}
	} else {
		for ( k = 1; k < m; k++ ) {
			for ( j = 0; j < k; j++ ) {
				j1        = 2 * j + ip[k];
				k1        = 2 * k + ip[j];
				xr        = a[j1];
				xi        = a[j1 + 1];
				yr        = a[k1];
				yi        = a[k1 + 1];
				a[j1]     = yr;
				a[j1 + 1] = yi;
				a[k1]     = xr;
				a[k1 + 1] = xi;
				j1       += m2;
				k1       += m2;
				xr        = a[j1];
				xi        = a[j1 + 1];
				yr        = a[k1];
				yi        = a[k1 + 1];
				a[j1]     = yr;
				a[j1 + 1] = yi;
				a[k1]     = xr;
				a[k1 + 1] = xi;
			}
		}
	}
	return;
}


static mpc_inline void
cft1st ( const int n, float* a, float* w )
{
	int    j, k1;
	float  wk1r, wk1i, wk2r, wk2i, wk3r, wk3i;
	float  x0r, x0i, x1r, x1i, x2r, x2i, x3r, x3i;

	x0r   = a[ 0] + a[ 2];
	x0i   = a[ 1] + a[ 3];
	x1r   = a[ 0] - a[ 2];
	x1i   = a[ 1] - a[ 3];
	x2r   = a[ 4] + a[ 6];
	x2i   = a[ 5] + a[ 7];
	x3r   = a[ 4] - a[ 6];
	x3i   = a[ 5] - a[ 7];
	a[ 0] = x0r + x2r;
	a[ 1] = x0i + x2i;
	a[ 4] = x0r - x2r;
	a[ 5] = x0i - x2i;
	a[ 2] = x1r - x3i;
	a[ 3] = x1i + x3r;
	a[ 6] = x1r + x3i;
	a[ 7] = x1i - x3r;
	wk1r  = w[ 2];
	x0r   = a[ 8] + a[10];
	x0i   = a[ 9] + a[11];
	x1r   = a[ 8] - a[10];
	x1i   = a[ 9] - a[11];
	x2r   = a[12] + a[14];
	x2i   = a[13] + a[15];
	x3r   = a[12] - a[14];
	x3i   = a[13] - a[15];
	a[ 8] = x0r + x2r;
	a[ 9] = x0i + x2i;
	a[12] = x2i - x0i;
	a[13] = x0r - x2r;
	x0r   = x1r - x3i;
	x0i   = x1i + x3r;
	a[10] = wk1r * (x0r - x0i);
	a[11] = wk1r * (x0r + x0i);
	x0r   = x3i + x1r;
	x0i   = x3r - x1i;
	a[14] = wk1r * (x0i - x0r);
	a[15] = wk1r * (x0i + x0r);

	k1 = 0;
	j  = 16;
	do {
		k1       += 2;
		wk2r      = w[k1];
		wk2i      = w[k1 + 1];
		wk1r      = w[2*k1];
		wk1i      = w[2*k1 + 1];
		wk3r      = wk1r - 2 * wk2i * wk1i;
		wk3i      = 2 * wk2i * wk1r - wk1i;
		x0r       = a[j]     + a[j + 2];
		x0i       = a[j + 1] + a[j + 3];
		x1r       = a[j]     - a[j + 2];
		x1i       = a[j + 1] - a[j + 3];
		x2r       = a[j + 4] + a[j + 6];
		x2i       = a[j + 5] + a[j + 7];
		x3r       = a[j + 4] - a[j + 6];
		x3i       = a[j + 5] - a[j + 7];
		a[j]      = x0r + x2r;
		a[j + 1]  = x0i + x2i;
		x0r      -= x2r;
		x0i      -= x2i;
		a[j + 4]  = wk2r * x0r - wk2i * x0i;
		a[j + 5]  = wk2r * x0i + wk2i * x0r;
		x0r       = x1r - x3i;
		x0i       = x1i + x3r;
		a[j + 2]  = wk1r * x0r - wk1i * x0i;
		a[j + 3]  = wk1r * x0i + wk1i * x0r;
		x0r       = x1r + x3i;
		x0i       = x1i - x3r;
		a[j + 6]  = wk3r * x0r - wk3i * x0i;
		a[j + 7]  = wk3r * x0i + wk3i * x0r;
		wk1r      = w[2*k1 + 2];
		wk1i      = w[2*k1 + 3];
		wk3r      = wk1r - 2 * wk2r * wk1i;
		wk3i      = 2 * wk2r * wk1r - wk1i;
		x0r       = a[j +  8] + a[j + 10];
		x0i       = a[j +  9] + a[j + 11];
		x1r       = a[j +  8] - a[j + 10];
		x1i       = a[j +  9] - a[j + 11];
		x2r       = a[j + 12] + a[j + 14];
		x2i       = a[j + 13] + a[j + 15];
		x3r       = a[j + 12] - a[j + 14];
		x3i       = a[j + 13] - a[j + 15];
		a[j + 8]  = x0r + x2r;
		a[j + 9]  = x0i + x2i;
		x0r      -= x2r;
		x0i      -= x2i;
		a[j + 12] = -wk2i * x0r - wk2r * x0i;
		a[j + 13] = -wk2i * x0i + wk2r * x0r;
		x0r       = x1r - x3i;
		x0i       = x1i + x3r;
		a[j + 10] = wk1r * x0r - wk1i * x0i;
		a[j + 11] = wk1r * x0i + wk1i * x0r;
		x0r       = x1r + x3i;
		x0i       = x1i - x3r;
		a[j + 14] = wk3r * x0r - wk3i * x0i;
		a[j + 15] = wk3r * x0i + wk3i * x0r;
	} while ( j += 16, j < n );
	return;
}

static mpc_inline void
cftmdl_i386 ( const int n, const int l, float* a, float* w )
{
	int    j, j1, j2, j3, k, k1, m, m2;
	float  wk1r, wk1i, wk2r, wk2i, wk3r, wk3i;
	float  x0r, x0i, x1r, x1i, x2r, x2i, x3r, x3i;

	m = l << 2;

	for ( j = 0; j < l; j += 2 ) {
		j1        = j  + l;
		j2        = j1 + l;
		j3        = j2 + l;
		x0r       = a[j]      + a[j1];
		x0i       = a[j + 1]  + a[j1 + 1];
		x1r       = a[j]      - a[j1];
		x1i       = a[j + 1]  - a[j1 + 1];
		x2r       = a[j2]     + a[j3];
		x2i       = a[j2 + 1] + a[j3 + 1];
		x3r       = a[j2]     - a[j3];
		x3i       = a[j2 + 1] - a[j3 + 1];
		a[j]      = x0r + x2r;
		a[j + 1]  = x0i + x2i;
		a[j2]     = x0r - x2r;
		a[j2 + 1] = x0i - x2i;
		a[j1]     = x1r - x3i;
		a[j1 + 1] = x1i + x3r;
		a[j3]     = x1r + x3i;
		a[j3 + 1] = x1i - x3r;
	}

	wk1r = w[2];
	for ( j = m; j < l + m; j += 2 ) {
		j1        = j  + l;
		j2        = j1 + l;
		j3        = j2 + l;
		x0r       = a[j]      + a[j1];
		x0i       = a[j + 1]  + a[j1 + 1];
		x1r       = a[j]      - a[j1];
		x1i       = a[j + 1]  - a[j1 + 1];
		x2r       = a[j2]     + a[j3];
		x2i       = a[j2 + 1] + a[j3 + 1];
		x3r       = a[j2]     - a[j3];
		x3i       = a[j2 + 1] - a[j3 + 1];
		a[j]      = x0r + x2r;
		a[j + 1]  = x0i + x2i;
		a[j2]     = x2i - x0i;
		a[j2 + 1] = x0r - x2r;
		x0r       = x1r - x3i;
		x0i       = x1i + x3r;
		a[j1]     = wk1r * (x0r - x0i);
		a[j1 + 1] = wk1r * (x0r + x0i);
		x0r       = x3i + x1r;
		x0i       = x3r - x1i;
		a[j3]     = wk1r * (x0i - x0r);
		a[j3 + 1] = wk1r * (x0i + x0r);
	}

	k1 = 0;
	m2 = 2 * m;
	for ( k = m2; k < n; k += m2 ) {
		k1  += 2;
		wk2r = w[k1];
		wk2i = w[k1 + 1];
		wk1r = w[2*k1];
		wk1i = w[2*k1 + 1];
		wk3r = wk1r - 2 * wk2i * wk1i;
		wk3i = 2 * wk2i * wk1r - wk1i;
		j    = k;
		do {
			j1        = j  + l;
			j2        = j1 + l;
			j3        = j2 + l;
			x0r       = a[j]      + a[j1];
			x0i       = a[j + 1]  + a[j1 + 1];
			x1r       = a[j]      - a[j1];
			x1i       = a[j + 1]  - a[j1 + 1];
			x2r       = a[j2]     + a[j3];
			x2i       = a[j2 + 1] + a[j3 + 1];
			x3r       = a[j2]     - a[j3];
			x3i       = a[j2 + 1] - a[j3 + 1];
			a[j]      = x0r + x2r;
			a[j + 1]  = x0i + x2i;
			x0r      -= x2r;
			x0i      -= x2i;
			a[j2]     = wk2r * x0r - wk2i * x0i;
			a[j2 + 1] = wk2r * x0i + wk2i * x0r;
			x0r       = x1r - x3i;
			x0i       = x1i + x3r;
			a[j1]     = wk1r * x0r - wk1i * x0i;
			a[j1 + 1] = wk1r * x0i + wk1i * x0r;
			x0r       = x1r + x3i;
			x0i       = x1i - x3r;
			a[j3]     = wk3r * x0r - wk3i * x0i;
			a[j3 + 1] = wk3r * x0i + wk3i * x0r;
		} while ( j += 2, j < l + k );

		wk1r = w[2*k1 + 2];
		wk1i = w[2*k1 + 3];
		wk3r = wk1r - 2 * wk2r * wk1i;
		wk3i = 2 * wk2r * wk1r - wk1i;
		j    = k + m;
		do {
			j1        = j  + l;
			j2        = j1 + l;
			j3        = j2 + l;
			x0r       = a[j]      + a[j1];
			x0i       = a[j + 1]  + a[j1 + 1];
			x1r       = a[j]      - a[j1];
			x1i       = a[j + 1]  - a[j1 + 1];
			x2r       = a[j2]     + a[j3];
			x2i       = a[j2 + 1] + a[j3 + 1];
			x3r       = a[j2]     - a[j3];
			x3i       = a[j2 + 1] - a[j3 + 1];
			a[j]      = x0r + x2r;
			a[j + 1]  = x0i + x2i;
			x0r      -= x2r;
			x0i      -= x2i;
			a[j2]     = -wk2i * x0r - wk2r * x0i;
			a[j2 + 1] = -wk2i * x0i + wk2r * x0r;
			x0r       = x1r - x3i;
			x0i       = x1i + x3r;
			a[j1]     = wk1r * x0r - wk1i * x0i;
			a[j1 + 1] = wk1r * x0i + wk1i * x0r;
			x0r       = x1r + x3i;
			x0i       = x1i - x3r;
			a[j3]     = wk3r * x0r - wk3i * x0i;
			a[j3 + 1] = wk3r * x0i + wk3i * x0r;
		} while ( j += 2, j < l+k+m );
	}
	return;
}

static mpc_inline void
cftfsub ( const int n, float* a, float* w )
{
	int    j, j1, j2, j3, l;
	float  x0r, x0i, x1r, x1i, x2r, x2i, x3r, x3i;

	l = 2;
	if ( n > 8 ) {
		cft1st ( n, a, w );
		l = 8;
		while ( (l << 2) < n ) {
			cftmdl ( n, l, a, w );
			l <<= 2;
		}
	}
	if ( (l << 2) == n ) {
		j = 0;
		do {
			j1        = j  + l;
			j2        = j1 + l;
			j3        = j2 + l;
			x0r       = a[j]      + a[j1];
			x0i       = a[j + 1]  + a[j1 + 1];
			x1r       = a[j]      - a[j1];
			x1i       = a[j + 1]  - a[j1 + 1];
			x2r       = a[j2]     + a[j3];
			x2i       = a[j2 + 1] + a[j3 + 1];
			x3r       = a[j2]     - a[j3];
			x3i       = a[j2 + 1] - a[j3 + 1];
			a[j]      = x0r + x2r;
			a[j + 1]  = x0i + x2i;
			a[j2]     = x0r - x2r;
			a[j2 + 1] = x0i - x2i;
			a[j1]     = x1r - x3i;
			a[j1 + 1] = x1i + x3r;
			a[j3]     = x1r + x3i;
			a[j3 + 1] = x1i - x3r;
		} while ( j += 2, j < l );
	} else {
		j = 0;
		do {
			j1        = j + l;
			x0r       = a[j]     - a[j1];
			x0i       = a[j + 1] - a[j1 + 1];
			a[j]     += a[j1];
			a[j + 1] += a[j1 + 1];
			a[j1]     = x0r;
			a[j1 + 1] = x0i;
		} while ( j += 2, j < l );
	}
	return;
}


static mpc_inline void
rftfsub ( const int n, float* a, int nc, float* c )
{
	int    j, k, kk, ks, m;
	float  wkr, wki, xr, xi, yr, yi;

	m  = n >> 1;
	ks = 2 * nc / m;
	kk = ks;
	j  = 2;
	k  = n;
	do {
		k        -= 2;
		nc       -= ks;
		wkr       = 0.5f - c[nc];
		wki       = c[kk];
		xr        = a[j]     - a[k];
		xi        = a[j + 1] + a[k + 1];
		yr        = wkr * xr - wki * xi;
		yi        = wkr * xi + wki * xr;
		a[j]     -= yr;
		a[j + 1] -= yi;
		a[k]     += yr;
		a[k + 1] -= yi;
		kk       += ks;
	} while ( j += 2, j < m );
	return;
}

// generates lookup-tables
void
Generate_FFT_Tables ( const int n, int* ip, float* w )
{
    int  nw;
    int  nc;

    nw = n >> 2;
    makewt ( nw, ip, w );

    nc = n >> 2;
    makect ( nc, ip, w + nw );
}


// patched to only-forward
void
rdft ( const int n, float* a, int* ip, float* w )
{
    float  xi;

    if ( n > 4) {
        bitrv2  ( n, ip + 2, a );
        cftfsub ( n, a, w );
        rftfsub ( n, a, ip[1], w + ip[0] );
    }
    else if ( n == 4 ) {
        cftfsub ( n, a, w );
    }
    xi    = a[0] - a[1];
    a[0] += a[1];
    a[1]  = xi;
    return;
}


/* -------- initializing routines -------- */
static void
makewt ( const int nw, int* ip, float* w )
{
    int     j;
    int     nwh;
    float   x;
    float   y;
    double  delta;

    ip[0] = nw;
    ip[1] = 1;
    if ( nw > 2 ) {
        nwh        = nw >> 1;
        delta      = (M_PI/4) / nwh;
        w[0]       = 1.;
        w[1]       = 0.;
        w[nwh]     = COS (delta * nwh);
        w[nwh + 1] = w[nwh];
        if ( nwh > 2 ) {
            for ( j = 2; j < nwh; j += 2 ) {
                x             = COS (delta * j);
                y             = SIN (delta * j);
                w[j]          = x;
                w[j + 1]      = y;
                w[nw - j]     = y;
                w[nw - j + 1] = x;
            }
            bitrv2 ( nw, ip + 2, w );
        }
    }
    return;
}


static void
makect ( const int nc, int* ip, float* c )
{
    int     j;
    int     nch;
    double  delta;

    ip[1] = nc;
    if ( nc > 1 ) {
        nch    = nc >> 1;
        delta  = (M_PI/4) / nch;
        c[0]   = COS (delta * nch);
        c[nch] = 0.5f * c[0];
        for ( j = 1; j < nch; j++ ) {
            c[j]      = 0.5f * COS (delta * j);
            c[nc - j] = 0.5f * SIN (delta * j);
        }
    }
    return;
}

/* end of fft4g.c */
