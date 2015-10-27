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
 *  Prediction
 *  Short-Block-detection with smooth inset
 *  revise CalcMSThreshold
 *  /dev/audio for Windows too
 *  revise PNS/IS
 *  CVS with smoother inset
 *  several files per call
 *  revise ANS with changing SCFs

  * No IS
  * PNS estimation very rough, also IS should be used to reduce data rate in the side channel
  * ANS problems at Frame boundaries when resolution changes
  * ANS problems at Subframe boundaries when SCF changes
  * CVS+ with smoother transition

----------------------------------------

Optimize Tabelle[18] (use second table)
CVS+

- ANS is disregarded during the search for the best Res
- ANS messes up if res changes (each 36 samples) and/or SCF changes (each 12 samples)
- PNS not in difference signal

- implement IS in decoder
- Experimental Quantizer with complete energy preservation
  - 1D, calculated
  - 2D, calculated
  - 2D, manually modified, coeffs set to 1.f

 */

#include <string.h>
#include <stdio.h>

#include "libmpcpsy.h"
#include "../mpc/datatypes.h"
#include "../mpc/minimax.h"
#include "../mpc/mpcmath.h"

// psy_tab.c
extern const float  iw        [PART_LONG];      // inverse partition-width for long
extern const float  iw_short  [PART_SHORT];     // inverse partition-width for short
extern const int    wl        [PART_LONG];      // w_low  for long
extern const int    wl_short  [PART_SHORT];     // w_low  for short
extern const int    wh        [PART_LONG];      // w_high for long
extern const int    wh_short  [PART_SHORT];     // w_high for short
extern float        MinVal   [PART_LONG];       // minimum quality that's adapted to the model, minval for long
extern float  Loudness [PART_LONG];               // weighting factors for loudness calculation
extern float  SPRD     [PART_LONG] [PART_LONG];   // tabulated spreading function
extern float  O_MAX;
extern float  O_MIN;
extern float  FAC1;
extern float  FAC2;                               // constants for offset calculation
extern float  partLtq  [PART_LONG];               // threshold in quiet (partitions)
extern float  invLtq   [PART_LONG];               // inverse threshold in quiet (partitions, long)
extern float  fftLtq   [512];                     // threshold in quiet (FFT)

// ans.c
extern float         ANSspec_L [MAX_ANS_LINES];
extern float         ANSspec_R [MAX_ANS_LINES];         // L/R-masking threshold for ANS
extern float         ANSspec_M [MAX_ANS_LINES];
extern float         ANSspec_S [MAX_ANS_LINES];         // M/S-masking threshold for ANS

void   Init_Psychoakustiktabellen ( PsyModel* );
int    CVD2048 ( PsyModel*, const float*, int* );

// Antialiasing for calculation of the subband power
const float  Butfly    [7] = { 0.5f, 0.2776f, 0.1176f, 0.0361f, 0.0075f, 0.000948f, 0.0000598f };

// Antialiasing for calculation of the masking thresholds
const float  InvButfly [7] = { 2.f, 3.6023f, 8.5034f, 27.701f, 133.33f, 1054.852f, 16722.408f };

/* V A R I A B L E S */

static float         a          [PART_LONG];
static float         b          [PART_LONG];
static float         c          [PART_LONG];
static float         d          [PART_LONG];           // Integrations for tmpMask
static float  Xsave_L    [3 * 512];
static float  Xsave_R    [3 * 512];             // FFT-Amplitudes L/R
static float  Ysave_L    [3 * 512];
static float  Ysave_R    [3 * 512];             // FFT-Phases L/R
static float         T_L        [PART_LONG];
static float         T_R        [PART_LONG];           // time-constants for tmpMask
static float         pre_erg_L[2][PART_SHORT];
static float         pre_erg_R[2][PART_SHORT];          // Preecho-control short
static float         PreThr_L   [PART_LONG];
static float         PreThr_R   [PART_LONG];           // for Pre-Echo-control L/R
static float         tmp_Mask_L [PART_LONG];
static float         tmp_Mask_R [PART_LONG];           // for Post-Masking L/R
static int           Vocal_L    [MAX_CVD_LINE + 4];
static int           Vocal_R    [MAX_CVD_LINE + 4];    // FFT-Line belongs to harmonic?

/* F U N C T I O N S */

// fft_routines.c
void   Init_FFT      ( PsyModel* );
void   PowSpec256    ( const float*, float* );
void   PowSpec1024   ( const float*, float* );
void   PowSpec2048   ( const float*, float* );
void   PolarSpec1024 ( const float*, float*, float* );
void   Cepstrum2048  ( float* cep, const int );

void   Init_ANS   ( void );

// Resets Arrays
void Init_Psychoakustik ( PsyModel* m)
{
    int  i;

    // initializing arrays with zero
	memset ( Xsave_L,   0, sizeof Xsave_L );
	memset ( Xsave_R,   0, sizeof Xsave_R );
	memset ( Ysave_L,   0, sizeof Ysave_L );
	memset ( Ysave_R,   0, sizeof Ysave_R );
	memset ( a,         0, sizeof a       );
	memset ( b,         0, sizeof b       );
	memset ( c,         0, sizeof c       );
	memset ( d,         0, sizeof d       );
	memset ( T_L,       0, sizeof T_L     );
	memset ( T_R,       0, sizeof T_R     );
	memset ( Vocal_L,   0, sizeof Vocal_L );
	memset ( Vocal_R,   0, sizeof Vocal_R );

	m->SampleFreq = 0.;
	m->BandWidth = 0.;
	m->KBD1 = 2.;
	m->KBD2 = -1.;
	m->Ltq_offset = 0;
	m->Ltq_max = 0;
	m->EarModelFlag = 0;
	m->PNS = 0.;
	m->CombPenalities = -1;

    // generate FFT lookup-tables with largest FFT-size of 1024
	Init_FFT (m);

	Init_ANS ();

	Init_Psychoakustiktabellen (m);

    // setting pre-echo variables to Ltq
	for ( i = 0; i < PART_LONG; i++ ) {
		pre_erg_L  [0][i/3] = pre_erg_R  [0][i/3] =
				pre_erg_L  [1][i/3] = pre_erg_R  [1][i/3] =
				tmp_Mask_L [i]   = tmp_Mask_R [i]   =
				PreThr_L   [i]   = PreThr_R   [i]   = partLtq [i];
	}

    return;
}


// VBRmode 1: Adjustment of all SMRs via a factor (offset of SMRoffset dB)
// VBRmode 2: SMRs have a minimum of minSMR dB
static void
RaiseSMR_Signal ( const int MaxBand, float* signal, float tmp )
{
    int    Band;
    float  z = 0.;

    for ( Band = MaxBand; Band >= 0; Band-- ) {
        if ( z < signal [Band]  ) z = signal [Band];
        if ( z > tmp            ) z = tmp;
        if ( signal [Band]  < z ) signal [Band] = z;
    }
}


void RaiseSMR (PsyModel* m, const int MaxBand, SMRTyp* smr )
{
    float  tmp = POW10 ( 0.1 * m->minSMR );

    RaiseSMR_Signal ( MaxBand, smr->L, tmp );
    RaiseSMR_Signal ( MaxBand, smr->R, tmp );
    RaiseSMR_Signal ( MaxBand, smr->M, tmp );
    RaiseSMR_Signal ( MaxBand, smr->S, 0.5 * tmp );

    return;
}

// input : *smr
// output: *smr, *ms, *x        (only the entries for L/R contain relevant data)
// Check if either M/S- or L/R-coding has a lower perceptual entropy
// Choose the better mode, copy the appropriate data into the
// arrays that belong to L and R and set the ms-Flag accordingly.
void
MS_LR_Entscheidung ( const int MaxBand, unsigned char* ms, SMRTyp* smr, SubbandFloatTyp* x )
{
    int     Band;
    int     n;
    float   PE_MS;
    float   PE_LR;
    float   tmpM;
    float   tmpS;
    float*  l;
    float*  r;


    for ( Band = 0; Band <= MaxBand; Band++ ) {        // calculate perceptual entropy
        PE_LR = PE_MS = 1.f;
        if (smr->L[Band] > 1.) PE_LR *= smr->L[Band];
        if (smr->R[Band] > 1.) PE_LR *= smr->R[Band];
        if (smr->M[Band] > 1.) PE_MS *= smr->M[Band];
        if (smr->S[Band] > 1.) PE_MS *= smr->S[Band];

        if ( PE_MS < PE_LR ) {
            ms[Band] = 1;

            // calculate M/S-signal and copies it to L/R-array
            l = x[Band].L;
            r = x[Band].R;
            for ( n = 0; n < 36; n++, l++, r++ ) {
                tmpM = (*l + *r) * 0.5f;
                tmpS = (*l - *r) * 0.5f;
                *l   = tmpM;
                *r   = tmpS;
            }

            // copy M/S - SMR to L/R-fields
            smr->L[Band] = smr->M[Band];
            smr->R[Band] = smr->S[Band];
        }
        else {
            ms[Band] = 0;
        }
    }

    return;
}

// input : FFT-spectrums *spec0 und *spec1
// output: energy in the individual subbands *erg0 and *erg1
// With Butfly[], you can calculate the results of aliasing during calculation
// of subband energy from the FFT-spectrums.
static void
SubbandEnergy ( const int     MaxBand,
                float*        erg0,
                float*        erg1,
                const float*  spec0,
                const float*  spec1 )
{
    int    n;
    int    k;
    int    alias;
    float  tmp0;
    float  tmp1;


    // Is this here correct for FFT-based data or is this calculation rule only for MDCTs???

    for ( k = 0; k <= MaxBand; k++ ) {                  // subband index
        tmp0 = tmp1 = 0.f;
        for ( n = 0; n < 16; n++, spec0++, spec1++ ) {  // spectral index
            tmp0 += *spec0;
            tmp1 += *spec1;

            // Consideration of Aliasing between the subbands
            if      ( n <   +sizeof(Butfly)/sizeof(*Butfly)  &&  k !=  0 ) {
                alias = -1 - (n<<1);
                tmp0 += Butfly [n]    * (spec0[alias] - *spec0);
                tmp1 += Butfly [n]    * (spec1[alias] - *spec1);
            }
            else if ( n > 15-sizeof(Butfly)/sizeof(*Butfly)  &&  k != 31 ) {
                alias = 31 - (n<<1);
                tmp0 += Butfly [15-n] * (spec0[alias] - *spec0);
                tmp1 += Butfly [15-n] * (spec1[alias] - *spec1);
            }
        }
        *erg0++ = tmp0;
        *erg1++ = tmp1;
    }

    return;
}

// input : FFT-Spectrums *spec0 and *spec1
// output: energy in the individual partitions *erg0 and *erg1
static void
PartitionEnergy ( float*        erg0,
                  float*        erg1,
                  const float*  spec0,
                  const float*  spec1 )
{
    unsigned int  n;
    unsigned int  k;
    float         e0;
    float         e1;

    n = 0;

    for ( ; n < 23; n++ ) {             // 11 or 23
        k  = wh[n] - wl[n];
        e0 = *spec0++;
        e1 = *spec1++;
        while ( k-- ) {
            e0 += *spec0++;
            e1 += *spec1++;
        }
        *erg0++ = e0;
        *erg1++ = e1;
    }

    for ( ; n < 48; n++ ) {             // 37 ... 46, 48, 57
        k  = wh[n] - wl[n];
        e0 = sqrt (*spec0++);
        e1 = sqrt (*spec1++);
        while ( k-- ) {
            e0 += sqrt (*spec0++);
            e1 += sqrt (*spec1++);
        }
        *erg0++ = e0*e0 * iw[n];
        *erg1++ = e1*e1 * iw[n];
    }

    for ( ; n < PART_LONG; n++ ) {
        k  = wh[n] - wl[n];
        e0 = *spec0++;
        e1 = *spec1++;
        while ( k-- ) {
            e0 += *spec0++;
            e1 += *spec1++;
        }
        *erg0++ = e0;
        *erg1++ = e1;
    }
}


// input : FFT-Spectrums *spec0, *spec1 and unpredictability *cw0 and *cw1
// output: weighted energy in the individual partitions *erg0, *erg1
static void
WeightedPartitionEnergy ( float*        erg0,
                          float*        erg1,
                          const float*  spec0,
                          const float*  spec1,
                          const float*  cw0,
                          const float*  cw1 )
{
    unsigned int  n;
    unsigned int  k;
    float         e0;
    float         e1;

    n = 0;

    for ( ; n < 23; n++ ) {
        e0 = *spec0++ * *cw0++;
        e1 = *spec1++ * *cw1++;
        k  = wh[n] - wl[n];
        while ( k-- ) {
            e0 += *spec0++ * *cw0++;
            e1 += *spec1++ * *cw1++;
        }
        *erg0++ = e0;
        *erg1++ = e1;
    }

    for ( ; n < 48; n++ ) {
        e0 = sqrt (*spec0++ * *cw0++);
        e1 = sqrt (*spec1++ * *cw1++);
        k  = wh[n] - wl[n];
        while ( k-- ) {
            e0 += sqrt (*spec0++ * *cw0++);
            e1 += sqrt (*spec1++ * *cw1++);
        }
        *erg0++ = e0*e0 * iw[n];
        *erg1++ = e1*e1 * iw[n];
    }

    for ( ; n < PART_LONG; n++ ) {
        e0 = *spec0++ * *cw0++;
        e1 = *spec1++ * *cw1++;
        k  = wh[n] - wl[n];
        while ( k-- ) {
            e0 += *spec0++ * *cw0++;
            e1 += *spec1++ * *cw1++;
        }
        *erg0++ = e0;
        *erg1++ = e1;
    }
}

// input : masking thresholds, first half of the arrays *shaped0 and *shaped1
// output: masking thresholds, second half of the arrays *shaped0 and *shaped1
// Considering the result of aliasing via InvButfly[]
// The input *thr0, *thr1 is gathered via address calculation from *shaped0, *shaped1

static void
AdaptThresholds ( const int MaxLine, float* shaped0, float* shaped1 )
{
    int           n;
    int           mod;
    int           alias;
    float         tmp;
    const float*  invb = InvButfly;
    const float*  thr0 = shaped0 - 512;
    const float*  thr1 = shaped1 - 512;
    float         tmp0;
    float         tmp1;


    // should be able to optimize it with coasting.  [ 9 ] + n * [ 7 + 7 + 2 ] + [ 7 ]
    //                                                    Schleife    Schl Schl Ausr  Schleife
    for ( n = 0; n < MaxLine; n++, thr0++, thr1++ ) {
        mod  = n & 15;  // n%16
        tmp0 = *thr0;
        tmp1 = *thr1;

        if      ( mod <   +sizeof(InvButfly)/sizeof(*InvButfly)  &&  n >  12 ) {
            alias = -1 - (mod<<1);
            tmp   = thr0[alias] * invb[mod];
            if ( tmp < tmp0 ) tmp0 = tmp;
            tmp   = thr1[alias] * invb[mod];
            if ( tmp < tmp1 ) tmp1 = tmp;
        }
        else if ( mod > 15-sizeof(InvButfly)/sizeof(*InvButfly)  &&  n < 499 ) {
            alias = 31 - (mod<<1);
            tmp   = thr0[alias] * invb[15-mod];
            if ( tmp < tmp0 ) tmp0 = tmp;
            tmp   = thr1[alias] * invb[15-mod];
            if ( tmp < tmp1 ) tmp1 = tmp;
        }
        *shaped0++ = tmp0;
        *shaped1++ = tmp1;
    }

    return;
}


// input : current spectrum in the form of power *spec and phase *phase,
//         the last two earlier spectrums are at position
//         512 and 1024 of the corresponding Input-Arrays.
//         Array *vocal, which can mark an FFT_Linie as harmonic
// output: current amplitude *amp and unpredictability *cw
static void
CalcUnpred (PsyModel* m,
			const int     MaxLine,
			const float*  spec,
			const float*  phase,
			const int*    vocal,
			float*        amp0,
			float*        phs0,
			float*        cw )
{
    int     n;
    float   amp;
    float   tmp;
#define amp1  ((amp0) +  512)           // amp[ 512...1023] contains data of frame-1
#define amp2  ((amp0) + 1024)           // amp[1024...1535] contains data of frame-2
#define phs1  ((phs0) +  512)           // phs[ 512...1023] contains data of frame-1
#define phs2  ((phs0) + 1024)           // phs[1024...1535] contains data of frame-2


    for ( n = 0; n < MaxLine; n++ ) {
        tmp     = COSF  ((phs0[n] = phase[n]) - 2*phs1[n] + phs2[n]);   // copy phase to output-array, predict phase and calculate predictive error
        amp0[n] = SQRTF (spec[n]);                                      // calculate and set amplitude
        amp     = 2*amp1[n] - amp2[n];                                  // predict amplitude

        // calculate unpredictability
        cw[n] = SQRTF (spec[n] + amp * (amp - 2*amp0[n] * tmp)) / (amp0[n] + FABS(amp));
    }

    // postprocessing of harmonic FFT-lines (*cw is set to CVD_UNPRED)
	if ( m->CVD_used  &&  vocal != NULL ) {
        for ( n = 0; n < MAX_CVD_LINE; n++, cw++, vocal++ )
            if ( *vocal != 0  &&  *cw > CVD_UNPRED * 0.01 * *vocal )
                *cw = CVD_UNPRED * 0.01 * *vocal;
    }

    return;
}
#undef amp1
#undef amp2
#undef phs1
#undef phs2


// input : Energy *erg, calibrated energy *werg
// output: spread energy *res, spread weighted energy *wres
// SPRD describes the spreading function as calculated in psy_tab.c
static void
SpreadingSignal ( const float* erg, const float* werg, float* res,
				  float* wres )
{
    int           n;
    int           k;
    int           start;
    int           stop;
    const float*  sprd;
    float         e;
    float         ew;


    for (k=0; k<PART_LONG; ++k, ++erg, ++werg) { // Source (masking partition)
        start = maxi(k-5, 0);           // minimum affected partition
        stop  = mini(k+7, PART_LONG-1); // maximum affected partition
        sprd  = SPRD[k] + start;         // load vector
        e     = *erg;
        ew    = *werg;

        for (n=start; n<=stop; ++n, ++sprd) {
            res [n] += *sprd * e;       // spreading signal
            wres[n] += *sprd * ew;      // spreading weighted signal
        }
    }

    return;
}

// input : spread weighted energy *werg, spread energy *erg
// output: masking threshold *erg after applying the tonality-offset
static void
ApplyTonalityOffset ( float* erg0, float* erg1, const float* werg0, const float* werg1 )
{
    int    n;
    float  Offset;
    float  quot;


    // calculation of the masked threshold in the partition range
    for ( n = 0; n < PART_LONG; n++ ) {
        quot = *werg0++ / *erg0;
        if      (quot <= 0.05737540597f) Offset = O_MAX;
        else if (quot <  0.5871011603f ) Offset = FAC1 * POW (quot, FAC2);
        else                             Offset = O_MIN;
        *erg0++ *= iw[n] * minf(MinVal[n], Offset);

        quot = *werg1++ / *erg1;
        if      (quot <= 0.05737540597f) Offset = O_MAX;
        else if (quot <  0.5871011603f ) Offset = FAC1 * POW (quot, FAC2);
        else                             Offset = O_MIN;
		*erg1++ *= iw[n] * minf(MinVal[n], Offset);
    }

    return;
}

// input: previous loudness *loud, energies *erg, threshold in quiet *adapted_ltq
// output: tracked loudness *loud, adapted threshold in quiet <Return value>
static float
AdaptLtq ( PsyModel* m, const float* erg0, const float* erg1 )
{
    static float  loud   = 0.f;
	float*        weight = Loudness;
    float         sum    = 0.f;
    int           n;

    // calculate loudness
    for ( n = 0; n < PART_LONG; n++ )
        sum += (*erg0++ + *erg1++) * *weight++;

    // Utilization of the time constants (fast drop of Ltq T=5, slow rise of Ltq T=20)
    //loud = (sum < loud) ? (4 * sum + loud)*0.2f : (19 * loud + sum)*0.05f;
    loud = 0.98 * loud + 0.02 * (0.5 * sum);

    // calculate dynamic offset for threshold in quiet, 0...+20 dB, at 96 dB loudness, an offset of 20 dB is assumed
    return 1.f + m->varLtq * loud * 5.023772e-08f;
}

// input : simultaneous masking threshold *frqthr,
//         previous masking threshold *tmpthr,
//         Integrations *a (short-time) and *b (long-time)
// output: tracked Integrations *a and *b, time constant *tau
static void
CalcTemporalThreshold ( float* a, float* b, float* tau, float* frqthr, float* tmpthr )
{
    int    n;
    float  tmp;


    for ( n = 0; n < PART_LONG; n++ ) {
        // following calculations relative to threshold in quiet
        frqthr[n] *= invLtq[n];
		tmpthr[n] *= invLtq[n];

        // new post-masking 'tmp' via time constant tau, if old post-masking  > Ltq (=1)
        tmp = tmpthr[n] > 1.f  ?  POW ( tmpthr[n], tau[n] )  :  1.f;

        // calculate time constant for post-masking in next frame,
        // if new time constant has to be calculated (new tmpMask < frqMask)
        a[n] += 0.5f  * (frqthr[n] - a[n]); // short time integrator
        b[n] += 0.15f * (frqthr[n] - b[n]); // long  time integrator
        if (tmp < frqthr[n])
            tau[n] = a[n] <= b[n]  ?  0.8f  :  0.2f + b[n] / a[n] * 0.6f;

        // use post-masking of (Re-Normalization)
		tmpthr[n] = maxf (frqthr[n], tmp) * partLtq[n];
    }

    return;
}

// input : L/R-Masking thresholds in Partitions *thrL, *thrR
//         L/R-Subband energies *ergL, *ergR
//         M/S-Subband energies *ergM, *ergS
// output: M/S-Masking thresholds in Partitions *thrM, *thrS
static void
CalcMSThreshold ( PsyModel* m,
				  const float*  const ergL,
                  const float*  const ergR,
                  const float*  const ergM,
                  const float*  const ergS,
                  float*        const thrL,
                  float*        const thrR,
                  float*        const thrM,
                  float*        const thrS )
{
    int    n;
    float  norm;
    float  tmp;

    // All hardcoded numbers here should be pulled from somewhere,
    // the "4.", the -2 dB, the 0.0625 and the 0.9375, as well as all bands where this is done

    for ( n = 0; n < PART_LONG; n++ ) {
        // estimate M/S thresholds out of L/R thresholds and M/S and L/R energies
        thrS[n] = thrM[n] = maxf (ergM[n], ergS[n]) / maxf (ergL[n], ergR[n]) * minf (thrL[n], thrR[n]);

        switch ( m->MS_Channelmode ) { // preserve 'near-mid' signal components
        case 3:
            if ( n > 0 ) {
                double ratioMS = ergM[n] > ergS[n] ? ergS[n] / ergM[n]  :  ergM[n] / ergS[n];
                double ratioLR = ergL[n] > ergR[n] ? ergR[n] / ergL[n]  :  ergL[n] / ergR[n];
                if ( ratioMS < ratioLR ) {              // MS
                    if ( ergM[n] > ergS[n] )
                        thrS[n] = thrL[n] = thrR[n] = 1.e18f;
                    else
                        thrM[n] = thrL[n] = thrR[n] = 1.e18f;
                }
                else {                                  // LR
                    if ( ergL[n] > ergR[n] )
                        thrR[n] = thrM[n] = thrS[n] = 1.e18f;
                    else
                        thrL[n] = thrM[n] = thrS[n] = 1.e18f;
                }
            }
            break;
        case 4:
            if ( n > 0 ) {
                double ratioMS = ergM[n] > ergS[n] ? ergS[n] / ergM[n]  :  ergM[n] / ergS[n];
                double ratioLR = ergL[n] > ergR[n] ? ergR[n] / ergL[n]  :  ergL[n] / ergR[n];
                if ( ratioMS < ratioLR ) {              // MS
                    if ( ergM[n] > ergS[n] )
                        thrS[n] = 1.e18f;
                    else
                        thrM[n] = 1.e18f;
                }
                else {                                  // LR
                    if ( ergL[n] > ergR[n] )
                        thrR[n] = 1.e18f;
                    else
                        thrL[n] = 1.e18f;
                }
            }
            break;
        case 5:
            thrS[n] *= 2.;      // +3 dB
            break;
        case 6:
            break;
        default:
            fprintf ( stderr, "Unknown stereo mode\n");
        case 10:
            if ( 4. * ergL[n] > ergR[n]   &&  ergL[n] < 4. * ergR[n] ) {// Energy between both channels differs by less than 6 dB
                norm = 0.70794578f * iw[n];  // -1.5 dB * iwidth
                if        ( ergM[n] > ergS[n] ) {
                    tmp = ergS[n] * norm;
                    if ( thrS[n] > tmp )
                        thrS[n] = MS2SPAT1 * thrS[n] + (1.f-MS2SPAT1) * tmp;    // raises masking threshold by up to 3 dB
                } else if ( ergS[n] > ergM[n] ) {
                    tmp = ergM[n] * norm;
                    if ( thrM[n] > tmp )
                        thrM[n] = MS2SPAT1 * thrM[n] + (1.f-MS2SPAT1) * tmp;
                }
            }
            break;
        case 11:
            if ( 4. * ergL[n] > ergR[n]   &&  ergL[n] < 4. * ergR[n] ) {// Energy between both channels differs by less than 6 dB
                norm = 0.63095734f * iw[n];  // -2.0 dB * iwidth
                if        ( ergM[n] > ergS[n] ) {
                    tmp = ergS[n] * norm;
                    if ( thrS[n] > tmp )
                        thrS[n] = MS2SPAT2 * thrS[n] + (1.f-MS2SPAT2) * tmp;    // raises masking threshold by up to 6 dB
                } else if ( ergS[n] > ergM[n] ) {
                    tmp = ergM[n] * norm;
                    if ( thrM[n] > tmp )
                        thrM[n] = MS2SPAT2 * thrM[n] + (1.f-MS2SPAT2) * tmp;
                }
            }
            break;
        case 12:
            if ( 4. * ergL[n] > ergR[n]   &&  ergL[n] < 4. * ergR[n] ) {// Energy between both channels differs by less than 6 dB
                norm = 0.56234133f * iw[n];  // -2.5 dB * iwidth
                if        ( ergM[n] > ergS[n] ) {
                    tmp = ergS[n] * norm;
                    if ( thrS[n] > tmp )
                        thrS[n] = MS2SPAT3 * thrS[n] + (1.f-MS2SPAT3) * tmp;    // raises masking threshold by up to 9 dB
                } else if ( ergS[n] > ergM[n] ) {
                    tmp = ergM[n] * norm;
                    if ( thrM[n] > tmp )
                        thrM[n] = MS2SPAT3 * thrM[n] + (1.f-MS2SPAT3) * tmp;
                }
            }
            break;
        case 13:
            if ( 4. * ergL[n] > ergR[n]   &&  ergL[n] < 4. * ergR[n] ) {// Energy between both channels differs by less than 6 dB
                norm = 0.50118723f * iw[n];  // -3.0 dB * iwidth
                if        ( ergM[n] > ergS[n] ) {
                    tmp = ergS[n] * norm;
                    if ( thrS[n] > tmp )
                        thrS[n] = MS2SPAT4 * thrS[n] + (1.f-MS2SPAT4) * tmp;    // raises masking threshold by up to 12 dB
                } else if ( ergS[n] > ergM[n] ) {
                    tmp = ergM[n] * norm;
                    if ( thrM[n] > tmp )
                        thrM[n] = MS2SPAT4 * thrM[n] + (1.f-MS2SPAT4) * tmp;
                }
            }
            break;
        case 15:
            if ( 4. * ergL[n] > ergR[n]   &&  ergL[n] < 4. * ergR[n] ) {// Energy between both channels differs by less than 6 dB
                norm = 0.50118723f * iw[n];  // -3.0 dB * iwidth
                if        ( ergM[n] > ergS[n] ) {
                    tmp = ergS[n] * norm;
                    if ( thrS[n] > tmp )
                        thrS[n] = tmp;                                  // raises masking threshold by up to +oo dB an
                } else if ( ergS[n] > ergM[n] ) {
                    tmp = ergM[n] * norm;
                    if ( thrM[n] > tmp )
                        thrM[n] = tmp;
                }
            }
            break;
        case 22:
            if ( 4. * ergL[n] > ergR[n]   &&  ergL[n] < 4. * ergR[n] ) {// Energy between both channels differs by less than 6 dB
                norm = 0.56234133f * iw[n];  // -2.5 dB * iwidth
                if        ( ergM[n] > ergS[n] ) {
                    tmp = ergS[n] * norm;
                    if ( thrS[n] > tmp )
                        thrS[n] = maxf (tmp, ergM[n]*iw[n]*0.025);              // +/- 1.414
                } else if ( ergS[n] > ergM[n] ) {
                    tmp = ergM[n] * norm;
                    if ( thrM[n] > tmp )
                        thrM[n] = maxf (tmp, ergS[n]*iw[n]*0.025);              // +/- 1.414
                }
            }
            break;
        }
    }

    return;
}

// input : Masking thresholds in Partitions *partThr0, *partThr1
//         level of threshold in quiet *ltq in FFT-resolution
// output: Masking thresholds in FFT-resolution *thr0, *thr1
// inline, because it's called 4x
static void
ApplyLtq ( float*        thr0,
           float*        thr1,
           const float*  partThr0,
           const float*  partThr1,
           const float   AdaptedLTQ,
           int           MSflag )
{
    int     n, k;
    float   ms, ltq, tmp, tmpThr0, tmpThr1;

    ms = AdaptedLTQ * (MSflag ? 0.125f : 0.25f);
    for( n = 0; n < PART_LONG; n++ )
    {
        tmpThr0 = sqrt(partThr0[n]);
        tmpThr1 = sqrt(partThr1[n]);
        for ( k = wl[n]; k <= wh[n]; k++, thr0++, thr1++ )
        {
            // threshold in quiet (Partition)
            // Applies a much more gentle ATH rolloff + 6 dB more dynamic
            ltq   = sqrt (ms * fftLtq [k]);
            tmp   = tmpThr0 + ltq;
            *thr0 = tmp * tmp;
            tmp   = tmpThr1 + ltq;
            *thr1 = tmp * tmp;
        }
    }
}

// input : Subband energies *erg0, *erg1
//         Masking thresholds in FFT-resolution *thr0, *thr1
// output: SMR per Subband *smr0, *smr1
static void
CalculateSMR ( const int     MaxBand,
               const float*  erg0,
               const float*  erg1,
               const float*  thr0,
               const float*  thr1,
               float*        smr0,
               float*        smr1 )
{
    int    n;
    int    k;
    float  tmp0;
    float  tmp1;

    // calculation of the masked thresholds in the subbands
    for (n = 0; n <= MaxBand; n++ ) {
        tmp0 = *thr0++;
        tmp1 = *thr1++;
        for (k=1; k<16; ++k, ++thr0, ++thr1) {
            if (*thr0 < tmp0) tmp0 = *thr0;
            if (*thr1 < tmp1) tmp1 = *thr1;
        }
        *smr0++ = 0.0625f * *erg0++ / tmp0;
        *smr1++ = 0.0625f * *erg1++ / tmp1;
    }

    return;
}

// input : energy spectrums erg[4][128] (4 delayed FFTs)
//         Energy of the last short block *preerg in short partitions
//         PreechoFac declares allowed traved of the masking threshold
// output: masking threshold *thr in short partitions
//         Energy of the last short block *preerg in short partitions
static void
CalcShortThreshold ( PsyModel* m,
					 const float  erg [4] [128],
                     const float  ShortThr,
                     float*       thr,
                     float        old_erg [2][PART_SHORT],
                     int*         transient )
{
    const int*    index_lo = wl_short; // lower FFT-index
    const int*    index_hi = wh_short; // upper FFT-index
    const float*  iwidth   = iw_short; // inverse partition-width
    int           k;
    int           n;
    int           l;
    float         new_erg;
	float         th, TransDetect = m->TransDetect;
    const float*  ep;

    for ( k = 0; k < PART_SHORT; k++ ) {
        transient [k] = 0;
        th            = old_erg [0][k];
        for ( n = 0; n < 4; n++ ) {
            ep   = erg[n] + index_lo [k];
            l    = index_hi [k] - index_lo [k];

            new_erg = *ep++;
            while (l--)
                new_erg += *ep++;               // e = Short_Partition-energy in piece n

            if ( new_erg > old_erg [0][k] ) {           // bigger than the old?

                if ( new_erg > old_erg [0][k] * TransDetect  ||
					 new_erg > old_erg [1][k] * TransDetect*2 )  // is signal transient?
                    transient [k] = 1;
            }
            else {
                th = minf ( th, new_erg );          // assume short threshold = engr*PreechoFac
            }

            old_erg [1][k] = old_erg [0][k];
            old_erg [0][k] = new_erg;           // save the current one
        }
        thr [k] = th * ShortThr * *iwidth++;  // pull out and multiply only when transient[k]=1
    }

    return;
}

// input : previous simultaneous masking threshold *preThr,
//         current simultaneous masking threshold *simThr
// output: update of *preThr for next call,
//         current masking threshold *partThr
static void
PreechoControl ( float*        partThr0,
                 float*        preThr0,
                 const float*  simThr0,
                 float*        partThr1,
                 float*        preThr1,
                 const float*  simThr1 )
{
    int  n;

    for ( n = 0; n < PART_LONG; n++ ) {
        *partThr0++ = minf ( *simThr0, *preThr0 * PREFAC_LONG);
        *partThr1++ = minf ( *simThr1, *preThr1 * PREFAC_LONG);
        *preThr0++  = *simThr0++;
        *preThr1++  = *simThr1++;
    }
    return;
}


void
TransientenCalc ( int*       T,
                  const int* TL,
                  const int* TR )
{
    int  i;
    int  x1;
    int  x2;

    memset ( T, 0, 32*sizeof(*T) );

    for ( i = 0; i < PART_SHORT; i++ )
        if ( TL[i]  ||  TR[i] ) {
            x1 = wl_short[i] >> 2;
            x2 = wh_short[i] >> 2;
            while ( x1 <= x2 )
                T [x1++] = 1;
        }
}


// input : PCM-Data *data
// output: SMRs for the input data
SMRTyp
Psychoakustisches_Modell ( PsyModel* m,
						   const int MaxBand,
						   const PCMDataTyp* data,
						   int* TransientL,
						   int* TransientR )
{
    float      Xi_L[32],     Xi_R[32];                          // acoustic pressure per Subband L/R
    float      Xi_M[32],     Xi_S[32];                          // acoustic pressure per Subband M/S
    float     cw_L[512],    cw_R[512];                          // unpredictability (only L/R)
    float     erg0[512],    erg1[512];                          // holds energy spectrum of long FFT
    float     phs0[512],    phs1[512];                          // holds phase spectrum of long FFT
    float  Thr_L[2*512], Thr_R[2*512];                          // masking thresholds L/R, second half for triangle swap
    float  Thr_M[2*512], Thr_S[2*512];                          // masking thresholds M/S, second half for triangle swap
    float F_256[4][128];                                        // holds energies of short FFTs (L/R only)
    float    Xerg[1024];                                        // holds energy spectrum of very long FFT
    float        Ls_L[PART_LONG],       Ls_R[PART_LONG];        // acoustic pressure in Partition L/R
    float        Ls_M[PART_LONG],       Ls_S[PART_LONG];        // acoustic pressure per each partition M/S
    float   PartThr_L[PART_LONG],  PartThr_R[PART_LONG];        // masking thresholds L/R (Partition)
    float   PartThr_M[PART_LONG],  PartThr_S[PART_LONG];        // masking thresholds M/S (Partition)
    float  sim_Mask_L[PART_LONG], sim_Mask_R[PART_LONG];        // simultaneous masking (only L/R)
    float      clow_L[PART_LONG],     clow_R[PART_LONG];        // spread, weighted energy (only L/R)
    float       cLs_L[PART_LONG],      cLs_R[PART_LONG];        // weighted partition energy (only L/R)
    float shortThr_L[PART_SHORT],shortThr_R[PART_SHORT];        // threshold for short FFT (only L/R)
    int      n;
    int      MaxLine    = (MaxBand+1)*16;                       // set FFT-resolution according to MaxBand
    SMRTyp   SMR0;
    SMRTyp   SMR1;                                              // holds SMR's for first and second Analysis
    int      isvoc_L = 0;
    int      isvoc_R = 0;
    float    factorLTQ  = 1.f;                                  // Offset after variable LTQ

    // 'ClearVocalDetection'-Process
    if ( m->CVD_used ) {
        memset ( Vocal_L, 0, sizeof Vocal_L );
        memset ( Vocal_R, 0, sizeof Vocal_R );

        // left channel
        PowSpec2048 ( &data->L[0], Xerg );
        isvoc_L = CVD2048 ( m, Xerg, Vocal_L );
        // right channel
        PowSpec2048 ( &data->R[0], Xerg );
        isvoc_R = CVD2048 ( m, Xerg, Vocal_R );
    }

    // calculation of the spectral energy via FFT
    PolarSpec1024 ( &data->L[0], erg0, phs0 );  // left
    PolarSpec1024 ( &data->R[0], erg1, phs1 );  // right

    // calculation of the acoustic pressures per each subband for L/R-signals
    SubbandEnergy ( MaxBand, Xi_L, Xi_R, erg0, erg1 );

    // calculation of the acoustic pressures per each partition
    PartitionEnergy ( Ls_L, Ls_R, erg0, erg1 );

    // calculate the predictability of the signal
    // left
    memmove ( Xsave_L+512, Xsave_L, 1024*sizeof(float) );
    memmove ( Ysave_L+512, Ysave_L, 1024*sizeof(float) );
    CalcUnpred ( m, MaxLine, erg0, phs0, isvoc_L ? Vocal_L : NULL, Xsave_L, Ysave_L, cw_L );
    // right
    memmove ( Xsave_R+512, Xsave_R, 1024*sizeof(float) );
    memmove ( Ysave_R+512, Ysave_R, 1024*sizeof(float) );
    CalcUnpred ( m, MaxLine, erg1, phs1, isvoc_R ? Vocal_R : NULL, Xsave_R, Ysave_R, cw_R );

    // calculation of the weighted acoustic pressures per each partition
    WeightedPartitionEnergy ( cLs_L, cLs_R, erg0, erg1, cw_L, cw_R );

    // Spreading Signal & weighted unpredictability-signal
    // left
    memset ( clow_L    , 0, sizeof clow_L );
    memset ( sim_Mask_L, 0, sizeof sim_Mask_L );
    SpreadingSignal ( Ls_L, cLs_L, sim_Mask_L, clow_L );
    // right
    memset ( clow_R    , 0, sizeof clow_R );
    memset ( sim_Mask_R, 0, sizeof sim_Mask_R );
    SpreadingSignal ( Ls_R, cLs_R, sim_Mask_R, clow_R );

    // Offset depending on tonality
    ApplyTonalityOffset ( sim_Mask_L, sim_Mask_R, clow_L, clow_R );

    // handling of transient signals
    // calculate four short FFTs (left)
    PowSpec256 ( &data->L[  0+SHORTFFT_OFFSET], F_256[0] );
    PowSpec256 ( &data->L[144+SHORTFFT_OFFSET], F_256[1] );
    PowSpec256 ( &data->L[288+SHORTFFT_OFFSET], F_256[2] );
    PowSpec256 ( &data->L[432+SHORTFFT_OFFSET], F_256[3] );
    // calculate short Threshold
	CalcShortThreshold ( m, (const float (*) [128]) F_256, m->ShortThr, shortThr_L, pre_erg_L, TransientL );

    // calculate four short FFTs (right)
    PowSpec256 ( &data->R[  0+SHORTFFT_OFFSET], F_256[0] );
    PowSpec256 ( &data->R[144+SHORTFFT_OFFSET], F_256[1] );
    PowSpec256 ( &data->R[288+SHORTFFT_OFFSET], F_256[2] );
    PowSpec256 ( &data->R[432+SHORTFFT_OFFSET], F_256[3] );
    // calculate short Threshold
    CalcShortThreshold ( m, (const float (*) [128]) F_256, m->ShortThr, shortThr_R, pre_erg_R, TransientR );

    // dynamic adjustment of the threshold in quiet to the loudness of the current sequence
    if ( m->varLtq > 0. )
        factorLTQ = AdaptLtq (m, Ls_L, Ls_R );

    // utilization of the temporal post-masking
    if ( m->tmpMask_used ) {
		CalcTemporalThreshold ( a, b, T_L, sim_Mask_L, tmp_Mask_L );
		CalcTemporalThreshold ( c, d, T_R, sim_Mask_R, tmp_Mask_R );
		memcpy ( sim_Mask_L, tmp_Mask_L, sizeof sim_Mask_L );
		memcpy ( sim_Mask_R, tmp_Mask_R, sizeof sim_Mask_R );
    }

    // transient signal?
    for ( n = 0; n < PART_SHORT; n++ ) {
        if ( TransientL [n] ) {
            sim_Mask_L [3*n  ] = minf ( sim_Mask_L [3*n  ], shortThr_L [n] );
            sim_Mask_L [3*n+1] = minf ( sim_Mask_L [3*n+1], shortThr_L [n] );
            sim_Mask_L [3*n+2] = minf ( sim_Mask_L [3*n+2], shortThr_L [n] );
        }
        if ( TransientR[n] ) {
            sim_Mask_R [3*n  ] = minf ( sim_Mask_R [3*n  ], shortThr_R [n] );
            sim_Mask_R [3*n+1] = minf ( sim_Mask_R [3*n+1], shortThr_R [n] );
            sim_Mask_R [3*n+2] = minf ( sim_Mask_R [3*n+2], shortThr_R [n] );
        }
    }

    // Pre-Echo control
	PreechoControl ( PartThr_L,PreThr_L, sim_Mask_L, PartThr_R, PreThr_R, sim_Mask_R );

    // utilization of the threshold in quiet
    ApplyLtq ( Thr_L, Thr_R, PartThr_L, PartThr_R, factorLTQ, 0 );

    // Consideration of aliasing between the subbands (noise is smeared)
    // In: Thr[0..511], Out: Thr[512...1023]
    AdaptThresholds ( MaxLine, Thr_L+512, Thr_R+512 );
    memmove ( Thr_L, Thr_L+512, 512*sizeof(float) );
    memmove ( Thr_R, Thr_R+512, 512*sizeof(float) );

    // calculation of the Signal-to-Mask-Ratio
    CalculateSMR ( MaxBand, Xi_L, Xi_R, Thr_L, Thr_R, SMR0.L, SMR0.R );

    /***************************************************************************************/
    /***************************************************************************************/
	if ( m->MS_Channelmode > 0 ) {
        // calculation of the spectral energy via FFT
        PowSpec1024 ( &data->M[0], erg0 );      // mid
        PowSpec1024 ( &data->S[0], erg1 );      // side

        // calculation of the acoustic pressures per each subband for M/S-signals
        SubbandEnergy ( MaxBand, Xi_M, Xi_S, erg0, erg1 );

        // calculation of the acoustic pressures per each partition
        PartitionEnergy ( Ls_M, Ls_S, erg0, erg1 );

        // calculate masking thresholds for M/S
        CalcMSThreshold ( m, Ls_L, Ls_R, Ls_M, Ls_S, PartThr_L, PartThr_R, PartThr_M, PartThr_S );
        ApplyLtq ( Thr_M, Thr_S, PartThr_M, PartThr_S, factorLTQ, 1 );

        // Consideration of aliasing between the subbands (noise is smeared)
        // In: Thr[0..511], Out: Thr[512...1023]
        AdaptThresholds ( MaxLine, Thr_M+512, Thr_S+512 );
        memmove ( Thr_M, Thr_M+512, 512*sizeof(float) );
        memmove ( Thr_S, Thr_S+512, 512*sizeof(float) );

        // calculation of the Signal-to-Mask-Ratio
        CalculateSMR ( MaxBand, Xi_M, Xi_S, Thr_M, Thr_S, SMR0.M, SMR0.S );
    }

	if ( m->NS_Order > 0 ) {       // providing the Noise Shaping thresholds
		memcpy ( ANSspec_L, Thr_L, sizeof ANSspec_L );
		memcpy ( ANSspec_R, Thr_R, sizeof ANSspec_R );
		memcpy ( ANSspec_M, Thr_M, sizeof ANSspec_M );
		memcpy ( ANSspec_S, Thr_S, sizeof ANSspec_S );
    }
    /***************************************************************************************/
    /***************************************************************************************/

    //
    //-------- second model calculation via shifted FFT ------------------------
    //
    // calculation of the spectral power via FFT
    PolarSpec1024 ( &data->L[576], erg0, phs0 ); // left
    PolarSpec1024 ( &data->R[576], erg1, phs1 ); // right

    // calculation of the acoustic pressures per each subband for L/R-signals
    SubbandEnergy ( MaxBand, Xi_L, Xi_R, erg0, erg1 );

    // calculation of the acoustic pressures per each partition
    PartitionEnergy ( Ls_L, Ls_R, erg0, erg1 );

    // calculate the predictability of the signal
    // left
    memmove ( Xsave_L+512, Xsave_L, 1024*sizeof(float) );
    memmove ( Ysave_L+512, Ysave_L, 1024*sizeof(float) );
	CalcUnpred ( m, MaxLine, erg0, phs0, isvoc_L ? Vocal_L : NULL, Xsave_L, Ysave_L, cw_L );
    // right
    memmove ( Xsave_R+512, Xsave_R, 1024*sizeof(float) );
    memmove ( Ysave_R+512, Ysave_R, 1024*sizeof(float) );
	CalcUnpred ( m, MaxLine, erg1, phs1, isvoc_R ? Vocal_R : NULL, Xsave_R, Ysave_R, cw_R );

    // calculation of the weighted acoustic pressure per each partition
    WeightedPartitionEnergy ( cLs_L, cLs_R, erg0, erg1, cw_L, cw_R );

    // Spreading Signal & weighted unpredictability-signal
    // left
    memset ( clow_L    , 0, sizeof clow_L );
    memset ( sim_Mask_L, 0, sizeof sim_Mask_L );
    SpreadingSignal ( Ls_L, cLs_L, sim_Mask_L, clow_L );
    // right
    memset ( clow_R    , 0, sizeof clow_R );
    memset ( sim_Mask_R, 0, sizeof sim_Mask_R );
    SpreadingSignal ( Ls_R, cLs_R, sim_Mask_R, clow_R );

    // Offset depending on tonality
    ApplyTonalityOffset ( sim_Mask_L, sim_Mask_R, clow_L, clow_R );

    // Handling of transient signals
    // calculate four short FFTs (left)
    PowSpec256 ( &data->L[ 576+SHORTFFT_OFFSET], F_256[0] );
    PowSpec256 ( &data->L[ 720+SHORTFFT_OFFSET], F_256[1] );
    PowSpec256 ( &data->L[ 864+SHORTFFT_OFFSET], F_256[2] );
    PowSpec256 ( &data->L[1008+SHORTFFT_OFFSET], F_256[3] );
    // calculate short Threshold
	CalcShortThreshold ( m, (const float (*) [128]) F_256, m->ShortThr, shortThr_L, pre_erg_L, TransientL );

    // calculate four short FFTs (right)
    PowSpec256 ( &data->R[ 576+SHORTFFT_OFFSET], F_256[0] );
    PowSpec256 ( &data->R[ 720+SHORTFFT_OFFSET], F_256[1] );
    PowSpec256 ( &data->R[ 864+SHORTFFT_OFFSET], F_256[2] );
    PowSpec256 ( &data->R[1008+SHORTFFT_OFFSET], F_256[3] );
    // calculate short Threshold
	CalcShortThreshold ( m, (const float (*) [128]) F_256, m->ShortThr, shortThr_R, pre_erg_R, TransientR );

    // dynamic adjustment of threshold in quiet to loudness of the current sequence
	if ( m->varLtq > 0. )
        factorLTQ = AdaptLtq ( m, Ls_L, Ls_R );

    // utilization of temporal post-masking
	if (m->tmpMask_used) {
		CalcTemporalThreshold ( a, b, T_L, sim_Mask_L, tmp_Mask_L );
		CalcTemporalThreshold ( c, d, T_R, sim_Mask_R, tmp_Mask_R );
		memcpy ( sim_Mask_L, tmp_Mask_L, sizeof sim_Mask_L );
		memcpy ( sim_Mask_R, tmp_Mask_R, sizeof sim_Mask_R );
    }

    // transient signal?
    for ( n = 0; n < PART_SHORT; n++ ) {
        if ( TransientL[n] ) {
            sim_Mask_L [3*n  ] = minf ( sim_Mask_L [3*n  ], shortThr_L [n] );
            sim_Mask_L [3*n+1] = minf ( sim_Mask_L [3*n+1], shortThr_L [n] );
            sim_Mask_L [3*n+2] = minf ( sim_Mask_L [3*n+2], shortThr_L [n] );
        }
        if ( TransientR[n] ) {
            sim_Mask_R [3*n  ] = minf ( sim_Mask_R [3*n  ], shortThr_R [n] );
            sim_Mask_R [3*n+1] = minf ( sim_Mask_R [3*n+1], shortThr_R [n] );
            sim_Mask_R [3*n+2] = minf ( sim_Mask_R [3*n+2], shortThr_R [n] );
        }
    }

    // Pre-Echo control
	PreechoControl ( PartThr_L, PreThr_L, sim_Mask_L, PartThr_R, PreThr_R, sim_Mask_R );

    // utilization of threshold in quiet
    ApplyLtq ( Thr_L, Thr_R, PartThr_L, PartThr_R, factorLTQ, 0 );

    // Consideration of aliasing between the subbands (noise is smeared)
    // In: Thr[0..511], Out: Thr[512...1023]
    AdaptThresholds ( MaxLine, Thr_L+512, Thr_R+512 );
    memmove ( Thr_L, Thr_L+512, 512*sizeof(float) );
    memmove ( Thr_R, Thr_R+512, 512*sizeof(float) );

    // calculation of the Signal-to-Mask-Ratio
    CalculateSMR ( MaxBand, Xi_L, Xi_R, Thr_L, Thr_R, SMR1.L, SMR1.R );

    /***************************************************************************************/
    /***************************************************************************************/
	if ( m->MS_Channelmode > 0 ) {
        // calculation of the spectral energy via FFT
        PowSpec1024 ( &data->M[576], erg0 );    // mid
        PowSpec1024 ( &data->S[576], erg1 );    // side

        // calculation of the acoustic pressure per each subband for M/S-signals
        SubbandEnergy ( MaxBand, Xi_M, Xi_S, erg0, erg1 );

        // calculation of the acoustic pressure per each partition
        PartitionEnergy ( Ls_M, Ls_S, erg0, erg1 );

        // calculate masking thresholds for M/S
        CalcMSThreshold ( m, Ls_L, Ls_R, Ls_M, Ls_S, PartThr_L, PartThr_R, PartThr_M, PartThr_S );
        ApplyLtq ( Thr_M, Thr_S, PartThr_M, PartThr_S, factorLTQ, 1 );

        // Consideration of aliasing between the subbands (noise is smeared)
        // In: Thr[0..511], Out: Thr[512...1023]
        AdaptThresholds ( MaxLine, Thr_M+512, Thr_S+512 );
        memmove ( Thr_M, Thr_M+512, 512*sizeof(float) );
        memmove ( Thr_S, Thr_S+512, 512*sizeof(float) );

        // calculation of the Signal-to-Mask-Ratio
        CalculateSMR ( MaxBand, Xi_M, Xi_S, Thr_M, Thr_S, SMR1.M, SMR1.S );
    }
    /***************************************************************************************/
    /***************************************************************************************/

	if ( m->NS_Order > 0 ) {
        for ( n = 0; n < MAX_ANS_LINES; n++ ) {                 // providing Noise Shaping thresholds
			ANSspec_L [n] = minf ( ANSspec_L [n], Thr_L [n] );
			ANSspec_R [n] = minf ( ANSspec_R [n], Thr_R [n] );
			ANSspec_M [n] = minf ( ANSspec_M [n], Thr_M [n] );
			ANSspec_S [n] = minf ( ANSspec_S [n], Thr_S [n] );
        }
    }

    for ( n = 0; n <= MaxBand; n++ ) {                          // choose 'worst case'-SMR from shifted analysis windows
        SMR0.L[n] = maxf ( SMR0.L[n], SMR1.L[n] );
        SMR0.R[n] = maxf ( SMR0.R[n], SMR1.R[n] );
        SMR0.M[n] = maxf ( SMR0.M[n], SMR1.M[n] );
        SMR0.S[n] = maxf ( SMR0.S[n], SMR1.S[n] );
    }
    return SMR0;
}
