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
#include <mpc/minimax.h>
#include <mpc/mpcmath.h>

/*
 *  Klemm 1994 and 1997. Experimental data. Sorry, data looks a little bit
 *  dodderly. Data below 30 Hz is extrapolated from other material, above 18
 *  kHz the ATH is limited due to the original purpose (too much noise at
 *  ATH is not good even if it's theoretically inaudible).
 */

// FIXME : move this in a struct, to eliminate multiple declarations
// w_low for long               0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23   24   25   26   27   28   29   30   31   32   33   34   35   36   37   38   39   40   41   42   43   44   45   46   47   48   49   50   51   52   53   54   55   56
const int   wl [PART_LONG] = {  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  13,  15,  17,  19,  21,  23,  25,  27,  29,  31,  33,  35,  38,  41,  44,  47,  50,  54,  58,  62,  67,  72,  78,  84,  91,  98, 106, 115, 124, 134, 145, 157, 170, 184, 199, 216, 234, 254, 276, 301, 329, 360, 396, 437, 485 };
const int   wh [PART_LONG] = {  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  12,  14,  16,  18,  20,  22,  24,  26,  28,  30,  32,  34,  37,  40,  43,  46,  49,  53,  57,  61,  66,  71,  77,  83,  90,  97, 105, 114, 123, 133, 144, 156, 169, 183, 198, 215, 233, 253, 275, 300, 328, 359, 395, 436, 484, 511 };
// Width:                       1    1    1    1    1    1    1    1    1    1    1    2    2    2    2    2    2    2    2    2    2    2    2    3    3    3    3    3    4    4    4    5    5    6    6    7    7    8    9    9   10   11   12   13   14   15   17   18   20   22   25   28   31   36   41   48   27

// inverse partition-width for long
const float iw [PART_LONG] = { 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/3, 1.f/3, 1.f/3, 1.f/3, 1.f/3, 1.f/4, 1.f/4, 1.f/4, 1.f/5, 1.f/5, 1.f/6, 1.f/6, 1.f/7, 1.f/7, 1.f/8, 1.f/9, 1.f/9, 1.f/10, 1.f/11, 1.f/12, 1.f/13, 1.f/14, 1.f/15, 1.f/17, 1.f/18, 1.f/20, 1.f/22, 1.f/25, 1.f/28, 1.f/31, 1.f/36, 1.f/41, 1.f/48, 1.f/27 };

// w_low for short                    0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17   18
const int   wl_short [PART_SHORT] = { 0,  1,  2,  3,  4,  5,  6,  8, 10, 12, 15, 18, 23, 29, 36, 46, 59, 75,  99 };
const int   wh_short [PART_SHORT] = { 0,  1,  2,  3,  5,  6,  7,  9, 12, 14, 18, 23, 29, 36, 46, 58, 75, 99, 127 };

// inverse partition-width for short
const float iw_short [PART_SHORT] = { 1.f, 1.f, 1.f, 1.f, 1.f/2, 1.f/2, 1.f/2, 1.f/2, 1.f/3, 1.f/3, 1.f/4, 1.f/6, 1.f/7, 1.f/8, 1.f/11, 1.f/13, 1.f/17, 1.f/25, 1.f/29 };

float  MinVal   [PART_LONG];               // contains minimum tonality soffsets
float  Loudness [PART_LONG];               // weighting factors for loudness calculation
float  SPRD     [PART_LONG] [PART_LONG];   // tabulated spreading function
float  O_MAX;
float  O_MIN;
float  FAC1;
float  FAC2;                               // constants for offset calculation
float  partLtq  [PART_LONG];               // threshold in quiet (partitions)
float  invLtq   [PART_LONG];               // inverse threshold in quiet (partitions, long)
float  fftLtq   [512];                     // threshold in quiet (FFT)

static float
ATHformula_Frank ( float freq )
{
    /*
     * one value per 100 cent = 1
     * semitone = 1/4
     * third = 1/12
     * octave = 1/40 decade
     * rest is linear interpolated, values are currently in millibel rel. 20 Pa
     */
    static short tab [] = {
        /*    10.0 */  9669, 9669, 9626, 9512,
        /*    12.6 */  9353, 9113, 8882, 8676,
        /*    15.8 */  8469, 8243, 7997, 7748,
        /*    20.0 */  7492, 7239, 7000, 6762,
        /*    25.1 */  6529, 6302, 6084, 5900,
        /*    31.6 */  5717, 5534, 5351, 5167,
        /*    39.8 */  5004, 4812, 4638, 4466,
        /*    50.1 */  4310, 4173, 4050, 3922,
        /*    63.1 */  3723, 3577, 3451, 3281,
        /*    79.4 */  3132, 3036, 2902, 2760,
        /*   100.0 */  2658, 2591, 2441, 2301,
        /*   125.9 */  2212, 2125, 2018, 1900,
        /*   158.5 */  1770, 1682, 1594, 1512,
        /*   199.5 */  1430, 1341, 1260, 1198,
        /*   251.2 */  1136, 1057,  998,  943,
        /*   316.2 */   887,  846,  744,  712,
        /*   398.1 */   693,  668,  637,  606,
        /*   501.2 */   580,  555,  529,  502,
        /*   631.0 */   475,  448,  422,  398,
        /*   794.3 */   375,  351,  327,  322,
        /*  1000.0 */   312,  301,  291,  268,
        /*  1258.9 */   246,  215,  182,  146,
        /*  1584.9 */   107,   61,   13,  -35,
        /*  1995.3 */   -96, -156, -179, -235,
        /*  2511.9 */  -295, -350, -401, -421,
        /*  3162.3 */  -446, -499, -532, -535,
        /*  3981.1 */  -513, -476, -431, -313,
        /*  5011.9 */  -179,    8,  203,  403,
        /*  6309.6 */   580,  736,  881, 1022,
        /*  7943.3 */  1154, 1251, 1348, 1421,
        /* 10000.0 */  1479, 1399, 1285, 1193,
        /* 12589.3 */  1287, 1519, 1914, 2369,
#if 0
        /* 15848.9 */  3352, 4865, 5942, 6177,
        /* 19952.6 */  6385, 6604, 6833, 7009,
        /* 25118.9 */  7066, 7127, 7191, 7260,
#else
        /* 15848.9 */  3352, 4352, 5352, 6352,
        /* 19952.6 */  7352, 8352, 9352, 9999,
        /* 25118.9 */  9999, 9999, 9999, 9999,
#endif
    };
    double    freq_log;
    unsigned  index;

    if ( freq <    10. ) freq =    10.;
    if ( freq > 29853. ) freq = 29853.;

    freq_log = 40. * log10 (0.1 * freq);   /* 4 steps per third, starting at 10 Hz */
    index    = (unsigned) freq_log;
    return 0.01 * (tab [index] * (1 + index - freq_log) + tab [index+1] * (freq_log - index));
}


/* F U N C T I O N S */
// calculation of the threshold in quiet in FFT-resolution
static void
Ruhehoerschwelle ( PsyModel* m,
				   unsigned int  EarModelFlag,
                   int           Ltq_offset,
                   int           Ltq_max )
{
    int     n;
    int     k;
    float   f;
    float   erg;
    double  tmp;
    float   absLtq [512];

    for ( n = 0; n < 512; n++ ) {
		f = (float) ( (n+1) * (float)(m->SampleFreq / 2000.) / 512 );   // Frequency in kHz

        switch ( EarModelFlag / 100 ) {
        case 0:         // ISO-threshold in quiet
            tmp  = 3.64*pow (f,-0.8) -  6.5*exp (-0.6*(f-3.3)*(f-3.3)) + 0.001*pow (f, 4.0);
            break;
        default:
        case 1:         // measured threshold in quiet (Nick Berglmeir, Andree Buschmann, Kopfh�er)
            tmp  = 3.00*pow (f,-0.8) -  5.0*exp (-0.1*(f-3.0)*(f-3.0)) + 0.0000015022693846297*pow (f, 6.0) + 10.*exp (-(f-0.1)*(f-0.1));
            break;
        case 2:         // measured threshold in quiet (Filburt, Kopfh�er)
            tmp  = 9.00*pow (f,-0.5) - 15.0*exp (-0.1*(f-4.0)*(f-4.0)) + 0.0341796875*pow (f, 2.5)          + 15.*exp (-(f-0.1)*(f-0.1)) - 18;
            tmp  = mind ( tmp, Ltq_max - 18 );
            break;
        case 3:
            tmp  = ATHformula_Frank ( 1.e3 * f );
            break;
        case 4:
            tmp  = ATHformula_Frank ( 1.e3 * f );
            if ( f > 4.8 ) {
                tmp += 3.00*pow (f,-0.8) -  5.0*exp (-0.1*(f-3.0)*(f-3.0)) + 0.0000015022693846297*pow (f, 6.0) + 10.*exp (-(f-0.1)*(f-0.1));
                tmp *= 0.5 ;
            }
            break;
        case 5:
            tmp  = ATHformula_Frank ( 1.e3 * f );
            if ( f > 4.8 ) {
                tmp = 3.00*pow (f,-0.8) -  5.0*exp (-0.1*(f-3.0)*(f-3.0)) + 0.0000015022693846297*pow (f, 6.0) + 10.*exp (-(f-0.1)*(f-0.1));
            }
            break;
        }

        tmp -= f * f * (int)(EarModelFlag % 100 - 50) * 0.0015;  // 00: +30 dB, 100: -30 dB  @20 kHz

        tmp       = mind ( tmp, Ltq_max );              // Limit ATH
        tmp      += Ltq_offset - 23;                    // Add chosen Offset
        fftLtq[n] = absLtq[n] = POW10 ( 0.1 * tmp);     // conversion into power
    }

    // threshold in quiet in partitions (long)
    for ( n = 0; n < PART_LONG; n++ ) {
        erg = 1.e20f;
        for ( k = wl[n]; k <= wh[n]; k++ )
            erg = minf (erg, absLtq[k]);

		partLtq[n] = erg;               // threshold in quiet
		invLtq [n] = 1.f / partLtq[n];  // Inverse
    }
}

#ifdef _MSC_VER
static double
asinh ( double x )
{
    return x >= 0  ?  log (sqrt (x*x+1) + x)  :  -log (sqrt (x*x+1) - x);
}
#endif


static double
Freq2Bark ( double Hz )           // Klemm 2002
{
    return 9.97074*asinh (1.1268e-3 * Hz) - 6.25817*asinh (0.197193e-3 * Hz) ;
}

// static double
// Bark2Freq ( double Bark )           // Klemm 2002
// {
//     return 956.86 * sinh (0.101561*Bark) + 11.7296 * sinh (0.304992*Bark) + 6.33622e-3*sinh (0.538621*Bark);
// }

static double
LongPart2Bark ( PsyModel* m, int Part )
{
	return Freq2Bark ((wl [Part] + wh [Part]) * m->SampleFreq / 2048.);
}

// calculating the table for loudness calculation based on absLtq = ank
static void
Loudness_Tabelle (PsyModel* m)
{
    int    n;
    float  midfreq;
    float  tmp;

    // ca. dB(A)
    for ( n = 0; n < PART_LONG; n++ ){
		midfreq      = (wh[n] + wl[n] + 3) * (0.25 * m->SampleFreq / 512);     // center frequency in kHz, why +3 ???
        tmp          = LOG10 (midfreq) - 3.5f;                                  // dB(A)
        tmp          = -10 * tmp * tmp + 3 - midfreq/3000;
		Loudness [n] = POW10 ( 0.1 * tmp );                                     // conversion into power
    }
}


static double
Bass ( float f, float TMN, float NMT, float bass )
{
    static unsigned char  lfe [11] = { 120, 100, 80, 60, 50, 40, 30, 20, 15, 10, 5 };
    int                   tmp      = (int) ( 1024/44100. * f + 0.5 );

    switch ( tmp ) {
    case  0:
    case  1:
    case  2:
    case  3:
    case  4:
    case  5:
    case  6:
    case  7:
    case  8:
    case  9:
    case 10:
        return TMN + bass * lfe [tmp];
    case 11:
    case 12:
    case 13:
    case 14:
    case 15:
    case 16:
    case 17:
    case 18:
        return TMN;
    case 19:
    case 20:
    case 21:
    case 22:
        return TMN*0.75 + NMT*0.25;
    case 23:
    case 24:
        return TMN*0.50 + NMT*0.50;
    case 25:
    case 26:
        return TMN*0.25 + NMT*0.75;
    default:
        return NMT;
    }
}


// calculating the coefficient for utilization of the tonality offset, depending on TMN und NMT
static void
Tonalitaetskoeffizienten ( PsyModel* m )
{
    double                tmp;
    int                   n;
    float                 bass;

	bass = 0.1/8 * m->NMT;
	if ( m->MinValChoice <= 2  &&  bass > 0.1 )
        bass = 0.1f;
	if ( m->MinValChoice <= 1 )
        bass = 0.0f;

    // alternative: calculation of the minval-values dependent on TMN and TMN
    for ( n = 0; n < PART_LONG; n++ ) {
		tmp        = Bass ( (wl [n] + wh [n]) / 2048. * m->SampleFreq, m->TMN, m->NMT, bass );
		MinVal [n] = POW10 ( -0.1 * tmp );                      // conversion into power
    }

    // calculation of the constants for "tonality offset"
	O_MAX = POW10 ( -0.1 * m->TMN );
	O_MIN = POW10 ( -0.1 * m->NMT );
	FAC1  = POW10 ( -0.1 * (m->NMT - (m->TMN - m->NMT) * 0.229) ) ;
	FAC2  = (m->TMN - m->NMT) * (0.99011159 * 0.1);
}


// calculation of the spreading function
static void
Spread ( PsyModel* m )
{
    int    i;
    int    j;
    float  tmpx;
    float  tmpy;
    float  tmpz;
    float  x;

    // calculation of the spreading-function for all occuring values
    for ( i = 0; i < PART_LONG; i++ ) {                 // i is masking Partition, Source
        for ( j = 0; j < PART_LONG; j++ ) {             // j is masking Partition, Target
            tmpx = LongPart2Bark (m, j) - LongPart2Bark (m, i);// Difference of the partitions in Bark
            tmpy = tmpz = 0.;                           // tmpz = 0: no dip

            if      ( tmpx < 0 ) {                      // downwards (S1)
                tmpy  = -32.f * tmpx;                   // 32 dB per Bark, e33 (10)
            }
            else if ( tmpx > 0 ) {                      // upwards (S2)
#if 0
                x = (wl[i]+wh[i])/2 * (float)(SampleFreq / 2000)/512;   // center frequency in kHz ???????
                if (i==0) x = 0.5f  * (float)(SampleFreq / 2000)/512;   // if first spectral line
#else
                x  = i  ?  wl[i]+wh[i]  :  1;
                x *= m->SampleFreq / 1000. / 2048;         // center frequency in kHz
#endif
                // dB/Bark
                tmpy = (22.f + 0.23f / x) * tmpx;       // e33 (10)

                // dip (up to 6 dB)
                tmpz = 8 * minf ( (tmpx-0.5f) * (tmpx-0.5f) - 2 * (tmpx-0.5f), 0.f );
            }

            // calculate coefficient
			SPRD[i][j] = POW10 ( -0.1 * (tmpy+tmpz) );  // [Source] [Target]
        }
    }

    // Normierung e33 (10)
    for ( i = 0; i < PART_LONG; i++ ) {                 // i is masked Partition
        float  norm = 0.f;
        for ( j = 0; j < PART_LONG; j++ )               // j is masking Partition
			norm += SPRD [j] [i];
        for ( j = 0; j < PART_LONG; j++ )               // j is masking Partition
			SPRD [j] [i] /= norm;
    }
}

// call all initialisation procedures
void
Init_Psychoakustiktabellen ( PsyModel* m )
{
	m->Max_Band = (int) ( m->BandWidth * 64. / m->SampleFreq );
	if ( m->Max_Band <  1 ) m->Max_Band =  1;
	if ( m->Max_Band > 31 ) m->Max_Band = 31;

    Tonalitaetskoeffizienten (m);
	Ruhehoerschwelle ( m, m->EarModelFlag, m->Ltq_offset, m->Ltq_max );
    Loudness_Tabelle (m);
    Spread (m);
}

/* end of psy_tab.c */
