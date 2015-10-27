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

/*
 *  Depending on how transient it is, it can be further reduced (up to 0=No ANS).
 *  Estimate coefficient for feedback at Order=1 over Mask_fu - Mask_fo.
 *  3 quantization routines: Order=0, Order=1, Order=2...6
 *  Order doesn't specify the power of the noise shaping, but only the flexibility of the form.
 *  Don't reset utilization of the "remains" at the frame borders;
 *  "remains"-utilization as scalefactor-independent values,
 *  so that a utilization beyond Subframe/Frame Borders is even possible.
 */

#include <string.h>

#include "libmpcpsy.h"
#include "../mpc/mpcmath.h"


static float  InvFourier [MAX_NS_ORDER + 1] [16];
static float  Cos_Tab    [16] [MAX_NS_ORDER + 1];
static float  Sin_Tab    [16] [MAX_NS_ORDER + 1];

float         ANSspec_L  [MAX_ANS_LINES];
float         ANSspec_R  [MAX_ANS_LINES];       // L/R-masking thresholds for ANS
float         ANSspec_M  [MAX_ANS_LINES];
float         ANSspec_S  [MAX_ANS_LINES];       // M/S-masking thresholds for ANS

void
Init_ANS ( void )
{
    int  n;
    int  k;

    // calculate Fourier tables
    for ( k = 0; k <= MAX_NS_ORDER; k++ ) {
        for ( n = 0; n < 16; n++ ) {
            InvFourier [k] [n] = (float) cos ( +2*M_PI/64 * (2*n)   *  k    ) / 16.;
            Cos_Tab    [n] [k] = (float) cos ( -2*M_PI/64 * (2*n+1) * (k+1) );
            Sin_Tab    [n] [k] = (float) sin ( -2*M_PI/64 * (2*n+1) * (k+1) );
        }
    }
}


// calculates optimal reflection coefficients and time response of a prediction filter in LPC analysis
static mpc_inline void
durbin_akf_to_kh1( float*        k,     // out: reflection coefficients
                   float*        h,     // out: time response
                   const float*  akf )  // in : autocorrelation function (0..1 used)
{
    h[0] = k[0] = akf [1] / akf [0];
}

static mpc_inline void
durbin_akf_to_kh2( float*        k,     // out: reflection coefficients
                   float*        h,     // out: time response
                   const float*  akf )  // in : autocorrelation function (0..2 used)
{
    float tk,e;

    tk    = akf [1] / akf[0];
    e     = akf[0] * (1. - tk*tk);
    h[0]  = k[0] = tk;
    h[0] *= 1. - (h[1]  = k[1] = tk = (akf[2] - h[0] * akf[1]) / e);
}

static mpc_inline void
durbin_akf_to_kh3( float*        k,     // out: reflection coefficients
                   float*        h,     // out: time response
                   const float*  akf )  // in : autocorrelation function (0..3 used)
{
    float a,b,tk,e;

    tk    = akf[1] / akf[0];
    e     = akf[0] * (1. - tk*tk);
    h[0]  = k[0] = tk;

    tk    = (akf[2] - h[0] * akf[1]) / e;
    e    *= 1. - tk*tk;
    h[0] *= 1. - (h[1] = k[1] = tk);
    h[2]  = k[2] = tk = (akf[3] - h[0] * akf[2] - h[1] * akf[1]) / e;

    h[0]  = (a=h[0]) - (b=h[1])*tk;
    h[1]  = b - a*tk;
}


static mpc_inline void
durbin_akf_to_kh ( float*        k,     // out: reflection coefficients
                   float*        h,     // out: time response
                   float*  akf,   // in : autocorrelation function (0..n used)
                   const int     n )    // in : number of parameters to calculate
{
    int    i,j;
    float  s,a,b,tk,e;
    float* p;
    float* q;

    e = akf [0];
    for ( i = 0; i < n; i++ ) {
        s = 0.f;
        p = h;
        q = akf+i;
        j = i;
        while ( j-- )
            s += *p++ * *q--;

        tk   = (akf[i+1] - s) / e;
        e   *= 1. - tk*tk;
        h[i] = k[i] = tk;
        p = h;
        q = h + i - 1;

        for ( ; p < q; p++, q-- ) {
            a  = *p;
            b  = *q;
            *p = a - b*tk;
            *q = b - a*tk;
        }
        if ( p == q )
            *p *= 1. - tk;
    }
}

static const unsigned char  maxANSOrder [32] = {
    6, 5, 4, 3, 2, 2, 2, 2,
    2, 2, 2, 2, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
};

static void
FindOptimalANS ( const int             MaxBand,
                 const unsigned char*  ms,
                 const float*          spec0,
                 const float*          spec1,
                 unsigned int*         NS,
                 float*                snr_comp,
                 float                 fir [] [MAX_NS_ORDER],
                 const float*          smr0,
                 const float*          smr1,
                 const int             scf [] [3],
                 const int             Transient [32] )
{
    int           Band;
    int           n;
    int           k;
    int           order;
    float         akf     [MAX_NS_ORDER + 1];
    float         h       [MAX_NS_ORDER];
    float         reflex  [MAX_NS_ORDER];
    float         spec    [16];
    float         invspec [16];
    float         norm;
    float         ns_loss;
    float         min_spec;
    float         min_diff;
    float         re;
    float         im;
    float         ns_energy;
    float         gain;
    float         NS_Gain;
    float         actSMR;
    int           max;
    const float*  tmp;

    for ( Band = 0; Band <= MaxBand  &&  maxANSOrder[Band]; Band++ ) {

        if ( scf[Band][0] != scf[Band][1]  ||  scf[Band][1] != scf[Band][2] )
            continue;

        if ( Transient[Band] )
            continue;

        max = maxANSOrder [Band];

        if ( ms[Band] ) {                       // setting pointer and SMR in relation to the M/S-flag
            tmp    = &spec1 [Band<<4];          // pointer to MS-data
            actSMR = smr1   [Band];             // selecting SMR
        }
        else {
            tmp    = &spec0 [Band<<4];          // pointer to LR-data
            actSMR = smr0   [Band];             // selecting SMR
        }

        if ( actSMR >= 1. ) {
            NS_Gain =     1.f;                  // reset gain
            norm    = 1.e-30f;

            // Selection of the masking threshold of the current subband, also considering frequency inversion in every 2nd subband
            if ( Band & 1 )
                for ( n = 0, tmp += 15; n < 16; n++ )
                    norm += spec[n] = *tmp--;
            else
                for ( n = 0; n < 16; n++ )
                    norm += spec[n] = *tmp++;

            // Preprocessing: normalization of the the power of spec[] to 1, and search for minimum of masking threshold
            norm     = 16.f / norm;
            min_spec = 1.e+12f;
            for ( n = 0; n < 16; n++ ) {
                invspec[n] = 1.f / (spec[n] *= norm);
                if ( spec[n] < min_spec )               // normalize spec[]
                    min_spec = spec[n];
            }

            // Calculation of the auto-correlation function
            tmp = InvFourier [0];
            for ( k = 0; k <= max; k++, tmp += 16 ) {
                akf[k] = tmp[ 0]*invspec[ 0] + tmp[ 1]*invspec[ 1] + tmp[ 2]*invspec[ 2] + tmp[ 3]*invspec[ 3] +
                         tmp[ 4]*invspec[ 4] + tmp[ 5]*invspec[ 5] + tmp[ 6]*invspec[ 6] + tmp[ 7]*invspec[ 7] +
                         tmp[ 8]*invspec[ 8] + tmp[ 9]*invspec[ 9] + tmp[10]*invspec[10] + tmp[11]*invspec[11] +
                         tmp[12]*invspec[12] + tmp[13]*invspec[13] + tmp[14]*invspec[14] + tmp[15]*invspec[15];
            }

            // Searching for the noise-shaper with maximum gain
            for ( order = 1; order <= max; order++ ) {
                switch ( order ) {                                              // calculating best FIR-Filter for the return
                case  1: durbin_akf_to_kh1 (reflex, h, akf);        break;
                case  2: durbin_akf_to_kh2 (reflex, h, akf);        break;
                case  3: durbin_akf_to_kh3 (reflex, h, akf);        break;
                default: durbin_akf_to_kh  (reflex, h, akf, order); break;
                }

                ns_loss  = 1.e-30f;                             // estimating the gain
                min_diff = 1.e+12f;
                for ( n = 0; n < 16; n++ ) {
                    re = 1.f;                                   // calculating the obtained noise shaping
                    im = 0.f;
                    for ( k = 0; k < order; k++ ) {
                        re -= h[k] * Cos_Tab[n][k];
                        im += h[k] * Sin_Tab[n][k];
                    }

                    ns_energy = re*re + im*im;                  // calculated spectral shaped noise
                    ns_loss  += ns_energy;                      // noise energy increases with shaping

                    if ( spec[n] < min_diff * ns_energy )       // Searching for minimum distance between the shaped noise and the masking threshold
                        min_diff = spec[n] / ns_energy;
                }

                // Updating the Filter if new gain is bigger than old gain and if the extra noise power through shaping is smaller than the SMR of this band
                gain = 16. * min_diff / (min_spec * ns_loss);
                if ( gain > NS_Gain  &&  ns_loss < actSMR ) {
                    NS [Band] = order;
                    NS_Gain   = gain;
                    memcpy ( fir [Band], h, order * sizeof(*h) );
                }
            }

            if ( NS_Gain > 1.f ) {                      // Activation of ANS if there is gain
                snr_comp[Band] *= NS_Gain;
            }
        }
    }

    return;
}


// perform ANS-analysis (calculation of FIR-filter and gain)
void
NS_Analyse ( PsyModel* m,
			 const int             MaxBand,
             const unsigned char*  MSflag,
             const SMRTyp          smr,
             const int*            Transient )
{

    // for L or M, respectively
    memset ( m->FIR_L,      0, sizeof m->FIR_L      );         // reset FIR
    memset ( m->NS_Order_L, 0, sizeof m->NS_Order_L );         // reset Flags
	FindOptimalANS ( MaxBand, MSflag, ANSspec_L, ANSspec_M, m->NS_Order_L, m->SNR_comp_L, m->FIR_L, smr.L, smr.M, (const int (*) [3]) m->SCF_Index_L, Transient );

    // for R or S, respectively
	memset ( m->FIR_R,      0, sizeof m->FIR_R      );         // reset FIR
	memset ( m->NS_Order_R, 0, sizeof m->NS_Order_R );         // reset Flags
	FindOptimalANS ( MaxBand, MSflag, ANSspec_R, ANSspec_S, m->NS_Order_R, m->SNR_comp_R, m->FIR_R, smr.R, smr.S, (const int (*) [3]) m->SCF_Index_R, Transient );

    return;
}

/* end of ans.c */
