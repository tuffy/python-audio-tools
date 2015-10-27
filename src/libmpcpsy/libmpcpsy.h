/*
 * Musepack audio compression
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

// psy_tab.h
#define PART_LONG          57                   // number of partitions for long
#define PART_SHORT     (PART_LONG / 3)          // number of partitions for short
#define MAX_SPL            20                   // maximum assumed Sound Pressure Level

// psy.c
#define SHORTFFT_OFFSET   168                   // fft-offset for short FFT's
#define PREFAC_LONG        10                   // preecho-factor for long partitions


#define MAX_CVD_LINE      300                   // maximum FFT-Index for CVD
#define CVD_UNPRED          0.040f              // unpredictability (cw) for CVD-detected bins, e33 (04)
#define MIN_ANALYZED_IDX   12                   // maximum base-frequency = 44100/MIN_ANALYZED_IDX ^^^^^^
#define MED_ANALYZED_IDX   50                   // maximum base-frequency = 44100/MED_ANALYZED_IDX ^^^^^^
#define MAX_ANALYZED_IDX  900                   // minimum base-frequency = 44100/MAX_ANALYZED_IDX  (816 for Amnesia)


#define MAX_NS_ORDER        6                   // maximum order of the Adaptive Noise Shaping Filter (IIR)
#define MAX_ANS_BANDS      16
#define MAX_ANS_LINES    (32 * MAX_ANS_BANDS)   // maximum number of noiseshaped FFT-lines
///////// 16 * MAX_ANS_BANDS not sufficient? //////////////////
#define MS2SPAT1             0.5f
#define MS2SPAT2             0.25f
#define MS2SPAT3             0.125f
#define MS2SPAT4             0.0625f

typedef struct {
    float  L [32];
	float  R [32];
	float  M [32];
	float  S [32];
} SMRTyp;

typedef struct {
	int           Max_Band;                    // maximum bandwidth
	float         SampleFreq;
	int MainQual;	// main profile quality
	float FullQual;	// full profile quality

	// profile params
	float            ShortThr;         // Factor to calculate the masking threshold with transients
	int              MinValChoice;
	unsigned int     EarModelFlag;
	float            Ltq_offset;       // Offset for threshold in quiet
	float            TMN;              // Offset for purely sinusoid components
	float            NMT;              // Offset for purely noisy components
	float            minSMR;           // minimum SMR for all subbands
	float            Ltq_max;          // maximum level for threshold in quiet
	float            BandWidth;
	unsigned char    tmpMask_used;     // global flag for temporal masking
	unsigned char    CVD_used;         // global flag for ClearVoiceDetection
	float            varLtq;           // variable threshold in quiet
	unsigned char    MS_Channelmode;
	int              CombPenalities;
	unsigned int    NS_Order;         // Maximum order for ANS
	float            PNS;
	float            TransDetect;      // minimum slewrate for transient detection

	// ans.h
	unsigned int  NS_Order_L [32];
	unsigned int  NS_Order_R [32];                  // frame-wise order of the Noiseshaping (0: off, 1...5: on)
	float         FIR_L      [32] [MAX_NS_ORDER];
	float         FIR_R      [32] [MAX_NS_ORDER];   // contains FIR-Filter for NoiseShaping
	float         SNR_comp_L [32];
	float         SNR_comp_R [32];             // SNR-compensation after SCF-combination and ANS-gain

	float KBD1; // = 2.
	float KBD2; // = -1.

	// FIXME : remove this :
	int (*SCF_Index_L) [3];
	int (*SCF_Index_R) [3];              // Scalefactor-index for Bitstream

} PsyModel;

void Init_Psychoakustik ( PsyModel* m);
