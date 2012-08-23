#ifndef REPLAYGAIN_H
#define REPLAYGAIN_H

/*
 *  ReplayGainAnalysis - analyzes input samples and give the recommended dB change
 *  Copyright (C) 2001 David Robinson and Glen Sawyer
 *  Modified 2010 by Brian Langenberger for use in Python Audio Tools
 *
 *  This library is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU Lesser General Public
 *  License as published by the Free Software Foundation; either
 *  version 2.1 of the License, or (at your option) any later version.
 *
 *  This library is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *  Lesser General Public License for more details.
 *
 *  You should have received a copy of the GNU Lesser General Public
 *  License along with this library; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 *  concept and filter values by David Robinson (David@Robinson.org)
 *    -- blame him if you think the idea is flawed
 *  coding by Glen Sawyer (mp3gain@hotmail.com) 735 W 255 N, Orem, UT 84057-4505 USA
 *    -- blame him if you think this runs too slowly, or the coding is otherwise flawed
 *
 *  For an explanation of the concepts and the basic algorithms involved, go to:
 *    http://www.replaygain.org/
 */

#define GAIN_NOT_ENOUGH_SAMPLES  -24601

#define YULE_ORDER         10
#define BUTTER_ORDER        2
#define YULE_FILTER     filterYule
#define BUTTER_FILTER   filterButter
#define RMS_PERCENTILE      0.95        /* percentile which is louder than the proposed level */
#define MAX_SAMP_FREQ   192000.          /* maximum allowed sample frequency [Hz] */
#define RMS_WINDOW_TIME     0.050       /* Time slice size [s] */
#define STEPS_per_dB      100.          /* Table entries per dB */
#define MAX_dB            120.          /* Table entries for 0...MAX_dB (normal max. values are 70...80 dB) */
#define STEPS_per_dB_times_MAX_dB 12000

#define MAX_ORDER 10 /* MAX(BUTTER_ORDER , YULE_ORDER) */
#define MAX_SAMPLES_PER_WINDOW 9600  /* MAX_SAMP_FREQ * RMS_WINDOW_TIME */
#define PINK_REF                64.82 /* calibration value */

typedef enum {GAIN_ANALYSIS_ERROR, GAIN_ANALYSIS_OK} gain_calc_status;

typedef struct {
    PyObject_HEAD;

    double          linprebuf [MAX_ORDER * 2];
    double*         linpre;  /* left input samples, with pre-buffer */
    double          lstepbuf  [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
    double*         lstep;   /* left "first step" (i.e. post first filter) samples */
    double          loutbuf   [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
    double*         lout;    /* left "out" (i.e. post second filter) samples */
    double          rinprebuf [MAX_ORDER * 2];
    double*         rinpre;  /* right input samples ... */
    double          rstepbuf  [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
    double*         rstep;
    double          routbuf   [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
    double*         rout;
    long            sampleWindow; /* number of samples required to reach number of milliseconds required for RMS window */
    long            totsamp;
    double          lsum;
    double          rsum;
    int             freqindex;
    int             first;
    uint32_t  A [STEPS_per_dB_times_MAX_dB];
    uint32_t  B [STEPS_per_dB_times_MAX_dB];

    unsigned sample_rate;
    double album_peak;
} replaygain_ReplayGain;

void
ReplayGain_dealloc(replaygain_ReplayGain* self);

PyObject*
ReplayGain_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
ReplayGain_init(replaygain_ReplayGain *self, PyObject *args, PyObject *kwds);

PyObject*
ReplayGain_title_gain(replaygain_ReplayGain *self, PyObject* args);

PyObject*
ReplayGain_album_gain(replaygain_ReplayGain *self);

gain_calc_status
ReplayGain_analyze_samples(replaygain_ReplayGain* self,
                           const double* left_samples,
                           const double* right_samples,
                           size_t num_samples,
                           int num_channels);

double
ReplayGain_get_title_gain(replaygain_ReplayGain *self);

double
ReplayGain_get_album_gain(replaygain_ReplayGain *self);


typedef struct {
    PyObject_HEAD;

    pcmreader* pcmreader;
    array_ia* channels;
    BitstreamReader* white_noise;
    PyObject* audiotools_pcm;
    double multiplier;
} replaygain_ReplayGainReader;

void
ReplayGainReader_dealloc(replaygain_ReplayGainReader* self);

PyObject*
ReplayGainReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int
ReplayGainReader_init(replaygain_ReplayGainReader *self,
                      PyObject *args, PyObject *kwds);

static PyObject*
ReplayGainReader_sample_rate(replaygain_ReplayGainReader *self,
                             void *closure);

static PyObject*
ReplayGainReader_bits_per_sample(replaygain_ReplayGainReader *self,
                                 void *closure);

static PyObject*
ReplayGainReader_channels(replaygain_ReplayGainReader *self,
                          void *closure);

static PyObject*
ReplayGainReader_channel_mask(replaygain_ReplayGainReader *self,
                              void *closure);

static PyObject*
ReplayGainReader_read(replaygain_ReplayGainReader* self, PyObject *args);

static PyObject*
ReplayGainReader_close(replaygain_ReplayGainReader* self, PyObject *args);

#endif
