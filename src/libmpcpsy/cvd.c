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

#include <string.h>

#include "mpc/mpc_types.h"
#include "mpc/mpcmath.h"
#include "libmpcpsy.h"

void   Cepstrum2048  ( float* cep, const int );

/* C O N S T A N T S */
// from MatLab-Simulation (Fourier-transforms of the Cos-Rolloff)
#if 0
static const float  Puls [11] = {
    -0.02724753942504f, -0.10670808991329f, -0.06198987803623f,  0.18006206051664f,
     0.49549552704050f,  0.64201253447071f,  0.49549552704050f,  0.18006206051664f,
    -0.06198987803623f, -0.10670808991329f, -0.02724753942504f
};
#endif

static const float  Puls [ 9] = {
    -0.10670808991329f, -0.06198987803623f,  0.18006206051664f,  0.49549552704050f,
     0.64201253447071f,  0.49549552704050f,  0.18006206051664f, -0.06198987803623f,
    -0.10670808991329f
};

/*
// Generating the Cos-Rolloff of the Cepstral-analysis, Cos-Rolloff from 5512,5 Hz to 11025 Hz
// for ( k = 0; k <= 1024; k++ ) {
//     if      (k < 256) CosWin [k-256] = 1;
//     else if (k < 512) CosWin [k-256] = 0.5 + 0.5*cos (M_PI*(k-256)/256);
//     else              CosWin [k-256] = 0;
// }
*/
static const float  CosWin [256] = {
    1.0000000000000000f, 0.9999623298645020f, 0.9998494386672974f, 0.9996612071990967f, 0.9993977546691895f, 0.9990590810775757f, 0.9986452460289002f, 0.9981563091278076f, 0.9975923895835877f, 0.9969534873962402f, 0.9962397813796997f, 0.9954513311386108f, 0.9945882558822632f, 0.9936507344245911f, 0.9926388263702393f, 0.9915527701377869f, 0.9903926253318787f, 0.9891586899757385f, 0.9878510832786560f, 0.9864699840545654f, 0.9850156307220459f, 0.9834882616996765f, 0.9818880558013916f, 0.9802152514457703f, 0.9784701466560364f, 0.9766530394554138f, 0.9747641086578369f, 0.9728036522865295f, 0.9707720279693604f, 0.9686695337295532f, 0.9664964079856873f, 0.9642530679702759f, 0.9619397521018982f, 0.9595569372177124f, 0.9571048617362976f, 0.9545840024948120f, 0.9519946575164795f, 0.9493372440338135f, 0.9466121792793274f, 0.9438198208808899f, 0.9409606456756592f, 0.9380350708961487f, 0.9350435137748718f, 0.9319864511489868f, 0.9288643002510071f, 0.9256775975227356f, 0.9224267601966858f, 0.9191123247146606f, 0.9157348275184631f, 0.9122946262359619f, 0.9087924361228943f, 0.9052286148071289f, 0.9016037583351135f, 0.8979184627532959f, 0.8941732048988342f, 0.8903686404228210f, 0.8865052461624146f, 0.8825836181640625f, 0.8786044120788574f, 0.8745682239532471f, 0.8704755902290344f, 0.8663271069526672f, 0.8621235489845276f, 0.8578653931617737f,
    0.8535534143447876f, 0.8491881489753723f, 0.8447702527046204f, 0.8403005003929138f, 0.8357794880867004f, 0.8312078714370728f, 0.8265864253044128f, 0.8219157457351685f, 0.8171966671943665f, 0.8124297261238098f, 0.8076158165931702f, 0.8027555346488953f, 0.7978496551513672f, 0.7928989529609680f, 0.7879040837287903f, 0.7828658819198608f, 0.7777851223945618f, 0.7726625204086304f, 0.7674987912178040f, 0.7622948288917542f, 0.7570513486862183f, 0.7517691850662231f, 0.7464491128921509f, 0.7410919070243835f, 0.7356983423233032f, 0.7302693724632263f, 0.7248056530952454f, 0.7193081378936768f, 0.7137775421142578f, 0.7082147598266602f, 0.7026206851005554f, 0.6969960331916809f, 0.6913416981697083f, 0.6856585741043091f, 0.6799474954605103f, 0.6742093563079834f, 0.6684449315071106f, 0.6626551747322083f, 0.6568408608436585f, 0.6510030031204224f, 0.6451423168182373f, 0.6392598152160645f, 0.6333563923835754f, 0.6274328231811523f, 0.6214900612831116f, 0.6155290603637695f, 0.6095505952835083f, 0.6035556793212891f, 0.5975451469421387f, 0.5915199518203735f, 0.5854809284210205f, 0.5794290900230408f, 0.5733652114868164f, 0.5672903656959534f, 0.5612053275108337f, 0.5551111102104187f, 0.5490085482597351f, 0.5428986549377441f, 0.5367822647094727f, 0.5306603908538818f, 0.5245338082313538f, 0.5184035897254944f, 0.5122706294059753f, 0.5061357617378235f,
    0.5000000000000000f, 0.4938642382621765f, 0.4877294003963471f, 0.4815963804721832f, 0.4754661619663239f, 0.4693396389484406f, 0.4632177054882050f, 0.4571013450622559f, 0.4509914219379425f, 0.4448888897895813f, 0.4387946724891663f, 0.4327096343040466f, 0.4266347587108612f, 0.4205709397792816f, 0.4145190417766571f, 0.4084800481796265f, 0.4024548530578613f, 0.3964443206787109f, 0.3904493749141693f, 0.3844709396362305f, 0.3785099089145660f, 0.3725671768188477f, 0.3666436076164246f, 0.3607401549816132f, 0.3548576533794403f, 0.3489970266819000f, 0.3431591391563416f, 0.3373448550701141f, 0.3315550684928894f, 0.3257906734943390f, 0.3200524747371674f, 0.3143413960933685f, 0.3086582720279694f, 0.3030039668083191f, 0.2973793447017670f, 0.2917852103710175f, 0.2862224578857422f, 0.2806918919086456f, 0.2751943469047546f, 0.2697306573390961f, 0.2643016278743744f, 0.2589081227779388f, 0.2535509169101715f, 0.2482308149337769f, 0.2429486215114594f, 0.2377051562070847f, 0.2325011938810349f, 0.2273375093936920f, 0.2222148776054382f, 0.2171340882778168f, 0.2120959013700485f, 0.2071010768413544f, 0.2021503448486328f, 0.1972444802522659f, 0.1923841983079910f, 0.1875702589750290f, 0.1828033626079559f, 0.1780842244625092f, 0.1734135746955872f, 0.1687921136617661f, 0.1642205268144608f, 0.1596994996070862f, 0.1552297323942184f, 0.1508118808269501f,
    0.1464466154575348f, 0.1421345919370651f, 0.1378764659166336f, 0.1336728632450104f, 0.1295244395732880f, 0.1254318058490753f, 0.1213955804705620f, 0.1174163669347763f, 0.1134947761893272f, 0.1096313893795013f, 0.1058267876505852f, 0.1020815446972847f, 0.0983962342143059f, 0.0947714000940323f, 0.0912075936794281f, 0.0877053514122963f, 0.0842651948332787f, 0.0808876454830170f, 0.0775732174515724f, 0.0743224024772644f, 0.0711356922984123f, 0.0680135712027550f, 0.0649565011262894f, 0.0619649514555931f, 0.0590393692255020f, 0.0561801902949810f, 0.0533878505229950f, 0.0506627671420574f, 0.0480053536593914f, 0.0454160086810589f, 0.0428951233625412f, 0.0404430739581585f, 0.0380602329969406f, 0.0357469581067562f, 0.0335035994648933f, 0.0313304923474789f, 0.0292279683053494f, 0.0271963365375996f, 0.0252359099686146f, 0.0233469791710377f, 0.0215298328548670f, 0.0197847411036491f, 0.0181119665503502f, 0.0165117643773556f, 0.0149843730032444f, 0.0135300243273377f, 0.0121489353477955f, 0.0108413146808743f, 0.0096073597669601f, 0.0084472559392452f, 0.0073611787520349f, 0.0063492907211185f, 0.0054117450490594f, 0.0045486823655665f, 0.0037602325901389f, 0.0030465149320662f, 0.0024076367262751f, 0.0018436938989908f, 0.0013547716662288f, 0.0009409435442649f, 0.0006022718735039f, 0.0003388077020645f, 0.0001505906548118f, 0.0000376490788767f,
};


/* F U N C T I O N S */
// sets all the harmonics
static void
SetVoiceLines ( int* VoiceLine, const float base, int val )
{
    int    n;
    int    max = (int) (MAX_CVD_LINE * base / 1024.f);  // harmonics up to Index MAX_CVD_LINE (spectral lines outside of that don't make sense)
    int    line;
    float  frq = 1024.f / base;                         // frq = 1024./i is the Index of the basic harmonic

    // go through all harmonics
    for ( n = 1; n <= max; n++ ) {
        line = (int) (n * frq);
        VoiceLine [line] = VoiceLine [line+1] = val;
    }
}


// Analyze the Cepstrum, search for the basic harmonic
static void
CEP_Analyse2048 ( PsyModel* m,
				  float* res1,
                  float* res2,
                  float* qual1,
                  float* qual2,
                  float* cep )
{
    int           n;
    int           line;
    float         cc [MAX_ANALYZED_IDX + 3];    // cross correlation
    float         ref;
    float         line_sum;
    float         sum;
    float         kkf;
    float         norm;
    const float*  x;

    // cross-correlation with pulse shape
    // Calculate idx = MIN_ANALYZED_IDX-2  to  MAX_ANALYZED_IDX+2,
    // because they are read during search for maximum
    // 50 -> 882 Hz, 700 -> 63 Hz base frequency

    *res1 = *res2 = 0. ;
    memset ( cc, 0, sizeof cc );

    for ( n = MIN_ANALYZED_IDX - 2; n <= MAX_ANALYZED_IDX + 2; n++ ) {
        x    = cep + n;
        if ( x[0] > 0 ) {
            norm = x[-4] * x[-4] +
                   x[-3] * x[-3] +
                   x[-2] * x[-2] +
                   x[-1] * x[-1] +
                   x[ 0] * x[ 0] +
                   x[ 1] * x[ 1] +
                   x[ 2] * x[ 2] +
                   x[ 3] * x[ 3] +
                   x[ 4] * x[ 4];
            kkf  = x[-4] * Puls [0] +
                   x[-3] * Puls [1] +
                   x[-2] * Puls [2] +
                   x[-1] * Puls [3] +
                   x[ 0] * Puls [4] +
                   x[ 1] * Puls [5] +
                   x[ 2] * Puls [6] +
                   x[ 3] * Puls [7] +
                   x[ 4] * Puls [8];
            cc [n] = kkf * kkf / norm;         // calculate the square of ncc to avoid sqrt()
        }
    }

    // search for the (relative) maximum
    ref  = 0.f;
    line = MED_ANALYZED_IDX;
    for ( n = MAX_ANALYZED_IDX; n >= MED_ANALYZED_IDX; n-- ) {
        if (
             cc[n] * cep[n] * cep[n] > ref      &&
             cc[n]                   > 0.40f    &&      // e33 (02)     0.85
             cep[n]                  > 0.00f    &&      // e33 (02)
             cc[n  ]                >= cc[n+1]  &&
             cc[n  ]                >= cc[n-1]  &&
             cc[n+1]                >= cc[n+2]  &&
             cc[n-1]                >= cc[n-2]
           )
        {
            ref  = cc[n] * cep[n] * cep[n];
            line = n;
        }
    }

    // Calculating the center of the maximum (Interpolation)
    x        = cep + line;
    sum      = x[-3] + x[-2] + x[-1] + x[0] + x[1] + x[2] + x[3] + 1.e-30f;
    line_sum = (x[1]-x[-1]) + 2 * (x[2]-x[-2]) + 3 * (x[3]-x[-3]) + sum * line + 1.e-30f;

    /* e33 (04) */
    ref = cc[line  ] * cep[line  ] * cep[line  ]
        + cc[line-1] * cep[line-1] * cep[line-1]
        + cc[line+1] * cep[line+1] * cep[line+1];

    //{
    //    static unsigned int x = 0;
    //
    //    printf ("%7.3f s   ", (x/2)*1152./44100       );
    //  x++;
    //}

    //printf ("ref=%5.3f *res1=%7.3f f=%8.3f    ", ref, line_sum / sum, 44100. / (line_sum / sum) );

    *qual1 = ref;
    if ( ref > 0.015f )
        *res1 = line_sum / sum;

    if ( m->CVD_used < 2 )
        return;

    // search for the (relative) maximum
    ref  = 0.f;
    line = MIN_ANALYZED_IDX;

    for ( n = MED_ANALYZED_IDX + 1; n >= MIN_ANALYZED_IDX - 1; n-- ) {
        cc  [2*n  ] += 0.5 * cc [n];
        cc  [2*n+1] += 0.5 * (cc [n] + cc[n+1]);
        cep [2*n  ] += 0.5 * cep [n];
        cep [2*n+1] += 0.5 * (cep [n] + cep[n+1]);
    }

    for ( n = 2*MED_ANALYZED_IDX; n >= 2*MIN_ANALYZED_IDX; n-- ) {
        if (
             cc[n] * cep[n] * cep[n] > ref      &&
             cc[n]                   > 0.85f    &&      /* e33 (02) */
             cep[n]                  > 0.00f    &&      /* e33 (02) */
             cc[n  ]                >= cc[n+1]  &&
             cc[n  ]                >= cc[n-1]  &&
             cc[n+1]                >= cc[n+2]  &&
             cc[n-1]                >= cc[n-2]
           )
        {
            ref  = cc[n] * cep[n] * cep[n];
            line = n;
        }
    }

    // Calculating the center of the maximum (Interpolation)
    x        = cep + line;
    sum      = x[-3] + x[-2] + x[-1] + x[0] + x[1] + x[2] + x[3] + 1.e-30f;
    line_sum = (x[1]-x[-1]) + 2 * (x[2]-x[-2]) + 3 * (x[3]-x[-3]) + sum * line + 1.e-30f;

    /* e33 (04) */
    ref = cc[line  ] * cep[line  ] * cep[line  ]
        + cc[line-1] * cep[line-1] * cep[line-1]
        + cc[line+1] * cep[line+1] * cep[line+1];

    //printf ("ref=%5.3f *res2=%8.3f f=%8.3f\n", ref, 0.5 * line_sum / sum, 44100. / (0.5 * line_sum / sum) );

    *qual2 = ref;
    if ( ref >= 0.1f )
        *res2 = 0.5 * line_sum / sum;

    return;
}

#ifndef CVD_FASTLOG
# define logfast(x)     ((float) log (x))
#else

static mpc_inline float   /* This is a rough estimation with an accuracy of |x|<0.0037 */
logfast ( float x )
{
	mpc_doubleint y;
	y.d = x * x;
    y.d *= y.d;
    y.d *= y.d;
	return (y.n[1] + (45127.5 - 1072693248.)) * ( M_LN2 / (1L<<23) );
}

#endif

// ClearVoiceDetection for spectrum *spec
// input : Spectrum *spec
// output: Array *vocal contains information if the FFT-Line is a harmonic component
int
CVD2048 ( PsyModel* m, const float* spec, int* vocal )
{
    static float  cep [4096];     // cep[4096] -- array, which is also used for the 2048 FFT
    const float*  win = CosWin;   // pointer to cos-roll-off
    float         res1;
    float         res2;
    float         qual1;
    float         qual2;
    int           n;

    // Calculating logarithmated, windowed spectrum cep[]
    // cep[512...1024] = 0 -- cep[1025...2047] doesn't matter, because the first have to be filled by fft
    for ( n =   0; n < 256; n++ )
        cep[n] = logfast (*spec++);
    for ( n = 256; n < 512; n++ )
        cep[n] = logfast (*spec++) * *win++;

    memset ( cep+512, 0, 513*sizeof(*cep) );

    // Calculating cepstrum of cep[] (the function Cepstrum() outputs the cepstrum in-place)
    Cepstrum2048 ( cep, MAX_ANALYZED_IDX );

    // search the harmonic
	CEP_Analyse2048 ( m, &res1, &res2, &qual1, &qual2, cep );
//#include "cvd.h"
    if ( res1 > 0.f  ||  res2 > 0.f ) {
        if ( res1 > 0. ) SetVoiceLines ( vocal, res1, 100 );
        if ( res2 > 0. ) SetVoiceLines ( vocal, res2,  20 );
        return 1;
    }
    return 0;
}
