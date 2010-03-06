#ifndef REPLAYGAIN_H
#define REPLAYGAIN_H

#define GAIN_NOT_ENOUGH_SAMPLES  -24601
#define GAIN_ANALYSIS_ERROR           0
#define GAIN_ANALYSIS_OK              1

#define INIT_GAIN_ANALYSIS_ERROR      0
#define INIT_GAIN_ANALYSIS_OK         1

typedef double  Float_t;         // Type used for filtering
typedef unsigned short  Uint16_t;
typedef signed short    Int16_t;
typedef unsigned int    Uint32_t;
typedef signed int      Int32_t;

#define YULE_ORDER         10
#define BUTTER_ORDER        2
#define YULE_FILTER     filterYule
#define BUTTER_FILTER   filterButter
#define RMS_PERCENTILE      0.95        // percentile which is louder than the proposed level
#define MAX_SAMP_FREQ   48000.          // maximum allowed sample frequency [Hz]
#define RMS_WINDOW_TIME     0.050       // Time slice size [s]
#define STEPS_per_dB      100.          // Table entries per dB
#define MAX_dB            120.          // Table entries for 0...MAX_dB (normal max. values are 70...80 dB)

#define MAX_ORDER               (BUTTER_ORDER > YULE_ORDER ? BUTTER_ORDER : YULE_ORDER)
#define MAX_SAMPLES_PER_WINDOW  (size_t) (MAX_SAMP_FREQ * RMS_WINDOW_TIME)      // max. Samples per Time slice
#define PINK_REF                64.82 //298640883795                              // calibration value



typedef struct {
  PyObject_HEAD;

  Float_t          linprebuf [MAX_ORDER * 2];
  Float_t*         linpre;                                          // left input samples, with pre-buffer
  Float_t          lstepbuf  [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
  Float_t*         lstep;                                           // left "first step" (i.e. post first filter) samples
  Float_t          loutbuf   [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
  Float_t*         lout;                                            // left "out" (i.e. post second filter) samples
  Float_t          rinprebuf [MAX_ORDER * 2];
  Float_t*         rinpre;                                          // right input samples ...
  Float_t          rstepbuf  [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
  Float_t*         rstep;
  Float_t          routbuf   [MAX_SAMPLES_PER_WINDOW + MAX_ORDER];
  Float_t*         rout;
  long             sampleWindow;                                    // number of samples required to reach number of milliseconds required for RMS window
  long             totsamp;
  double           lsum;
  double           rsum;
  int              freqindex;
  int              first;
  Uint32_t  A [(size_t)(STEPS_per_dB * MAX_dB)];
  Uint32_t  B [(size_t)(STEPS_per_dB * MAX_dB)];
} replaygain_ReplayGain;

void ReplayGain_dealloc(replaygain_ReplayGain* self);

PyObject *ReplayGain_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int ReplayGain_init(replaygain_ReplayGain *self, PyObject *args, PyObject *kwds);

PyObject* ReplayGain_update(replaygain_ReplayGain *self, PyObject *args);

PyObject* ReplayGain_title_gain(replaygain_ReplayGain *self);

PyObject* ReplayGain_album_gain(replaygain_ReplayGain *self);

int     AnalyzeSamples   (replaygain_ReplayGain* self, const Float_t* left_samples, const Float_t* right_samples, size_t num_samples, int num_channels );
Float_t   GetTitleGain     (replaygain_ReplayGain *self);
Float_t   GetAlbumGain     (replaygain_ReplayGain *self);


#endif
