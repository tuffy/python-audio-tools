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
#include "../mpc/minimax.h"


typedef struct {
	float            ShortThr;
	unsigned char    MinValChoice;
	unsigned int     EarModelFlag;
	signed char      Ltq_offset;
	float            TMN;
	float            NMT;
	signed char      minSMR;
	signed char      Ltq_max;
	unsigned short   BandWidth;
	unsigned char    tmpMask_used;
	unsigned char    CVD_used;
	float            varLtq;
	unsigned char    MS_Channelmode;
	unsigned char    CombPenalities;
	unsigned char    NS_Order;
	float            PNS;
	float            TransDetect;
} Profile_Setting_t;

#define PROFILE_PRE2_TELEPHONE   5      // --quality  0
// #define PROFILE_PRE_TELEPHONE    6      // --quality  1
// #define PROFILE_TELEPHONE        7      // --quality  2
// #define PROFILE_THUMB            8      // --quality  3
// #define PROFILE_RADIO            9      // --quality  4
// #define PROFILE_STANDARD        10      // --quality  5
// #define PROFILE_XTREME          11      // --quality  6
// #define PROFILE_INSANE          12      // --quality  7
// #define PROFILE_BRAINDEAD       13      // --quality  8
// #define PROFILE_POST_BRAINDEAD  14      // --quality  9
#define PROFILE_POST2_BRAINDEAD 15      // --quality 10


static const Profile_Setting_t  Profiles [16] = {
	{ 0 },
	{ 0 },
	{ 0 },
	{ 0 },
	{ 0 },
	/*    Short   MinVal  EarModel  Ltq_                min   Ltq_  Band-  tmpMask  CVD_  varLtq    MS   Comb   NS_        Trans */
	/*    Thr     Choice  Flag      offset  TMN   NMT   SMR   max   Width  _used    used         channel Penal used  PNS    Det  */
	{ 1.e9f,  1,      300,       30,    3.0, -1.0,    0,  106,   4820,   1,      1,    1.,      3,     24,  6,   1.09f, 200 },  // 0: pre-Telephone
	{ 1.e9f,  1,      300,       24,    6.0,  0.5,    0,  100,   7570,   1,      1,    1.,      3,     20,  6,   0.77f, 180 },  // 1: pre-Telephone
	{ 1.e9f,  1,      400,       18,    9.0,  2.0,    0,   94,  10300,   1,      1,    1.,      4,     18,  6,   0.55f, 160 },  // 2: Telephone
	{ 50.0f,  2,      430,       12,   12.0,  3.5,    0,   88,  13090,   1,      1,    1.,      5,     15,  6,   0.39f, 140 },  // 3: Thumb
	{ 15.0f,  2,      440,        6,   15.0,  5.0,    0,   82,  15800,   1,      1,    1.,      6,     10,  6,   0.27f, 120 },  // 4: Radio
	{  5.0f,  2,      550,        0,   18.0,  6.5,    1,   76,  19980,   1,      2,    1.,     11,      9,  6,   0.00f, 100 },  // 5: Standard
	{  4.0f,  2,      560,       -6,   21.0,  8.0,    2,   70,  22000,   1,      2,    1.,     12,      7,  6,   0.00f,  80 },  // 6: Xtreme
	{  3.0f,  2,      570,      -12,   24.0,  9.5,    3,   64,  24000,   1,      2,    2.,     13,      5,  6,   0.00f,  60 },  // 7: Insane
	{  2.8f,  2,      580,      -18,   27.0, 11.0,    4,   58,  26000,   1,      2,    4.,     13,      4,  6,   0.00f,  40 },  // 8: BrainDead
	{  2.6f,  2,      590,      -24,   30.0, 12.5,    5,   52,  28000,   1,      2,    8.,     13,      4,  6,   0.00f,  20 },  // 9: post-BrainDead
	{  2.4f,  2,      599,      -30,   33.0, 14.0,    6,   46,  30000,   1,      2,   16.,     15,      2,  6,   0.00f,  10 },  //10: post-BrainDead
};


int TestProfileParams ( PsyModel* m )
{   //                                       0    1    2    3    4   5   6  7 8 9  10  11  12  13 14  15
	static signed char  TMNStereoAdj [] = { -6, -18, -15, -18, -12, -9, -6, 0,0,0, +1, +1, +1, +1, 0, +1 };  // Penalties for TMN
	static signed char  NMTStereoAdj [] = { -3, -18, -15, -15,  -9, -6, -3, 0,0,0,  0, +1, +1, +1, 0, +1 };  // Penalties for NMT
	int                 i;

	m->MainQual = PROFILE_PRE2_TELEPHONE;

	for ( i = PROFILE_PRE2_TELEPHONE; i <= PROFILE_POST2_BRAINDEAD; i++ ) {
		if ( m->ShortThr     > Profiles [i].ShortThr     ) continue;
		if ( m->MinValChoice < Profiles [i].MinValChoice ) continue;
		if ( m->EarModelFlag < Profiles [i].EarModelFlag ) continue;
		if ( m->Ltq_offset   > Profiles [i].Ltq_offset   ) continue;
		if ( m->Ltq_max      > Profiles [i].Ltq_max      ) continue;                     // offset should normally be considered here
		if ( m->TMN + TMNStereoAdj [m->MS_Channelmode] <
				   Profiles [i].TMN + TMNStereoAdj [Profiles [i].MS_Channelmode] )
			continue;
		if ( m->NMT + NMTStereoAdj [m->MS_Channelmode] <
				   Profiles [i].NMT + NMTStereoAdj [Profiles [i].MS_Channelmode] )
			continue;
		if ( m->minSMR       < Profiles [i].minSMR       ) continue;
		if ( m->BandWidth    < Profiles [i].BandWidth    ) continue;
		if ( m->tmpMask_used < Profiles [i].tmpMask_used ) continue;
		if ( m->CVD_used     < Profiles [i].CVD_used     ) continue;
     // if ( varLtq       > Profiles [i].varLtq       ) continue;
     // if ( NS_Order     < Profiles [i].NS_Order     ) continue;
		if ( m->PNS          > Profiles [i].PNS          ) continue;
		m->MainQual = i;
	}
	return m->MainQual;
}

void SetQualityParams (PsyModel * m, float qual )
{
	int    i;
	float  mix;

	qual = clip(qual, 0., 10.);

	i   = (int) qual + PROFILE_PRE2_TELEPHONE;
	mix = qual - (int) qual;

	m->MainQual       = i;
	m->FullQual       = qual + PROFILE_PRE2_TELEPHONE;
	m->ShortThr       = Profiles [i].ShortThr   * (1-mix) + Profiles [i+1].ShortThr   * mix;
	m->MinValChoice   = Profiles [i].MinValChoice  ;
	m->EarModelFlag   = Profiles [i].EarModelFlag  ;
	m->Ltq_offset     = Profiles [i].Ltq_offset * (1-mix) + Profiles [i+1].Ltq_offset * mix;
	m->varLtq         = Profiles [i].varLtq     * (1-mix) + Profiles [i+1].varLtq     * mix;
	m->Ltq_max        = Profiles [i].Ltq_max    * (1-mix) + Profiles [i+1].Ltq_max    * mix;
	m->TMN            = Profiles [i].TMN        * (1-mix) + Profiles [i+1].TMN        * mix;
	m->NMT            = Profiles [i].NMT        * (1-mix) + Profiles [i+1].NMT        * mix;
	m->minSMR         = Profiles [i].minSMR        ;
	m->BandWidth      = Profiles [i].BandWidth  * (1-mix) + Profiles [i+1].BandWidth  * mix;
	m->tmpMask_used   = Profiles [i].tmpMask_used  ;
	m->CVD_used       = Profiles [i].CVD_used      ;
	m->MS_Channelmode = Profiles [i].MS_Channelmode;
	m->CombPenalities = Profiles [i].CombPenalities;
	m->NS_Order       = Profiles [i].NS_Order      ;
	m->PNS            = Profiles [i].PNS        * (1-mix) + Profiles [i+1].PNS        * mix;
	m->TransDetect    = Profiles [i].TransDetect* (1-mix) + Profiles [i+1].TransDetect* mix;
}

