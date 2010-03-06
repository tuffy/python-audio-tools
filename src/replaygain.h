#ifndef REPLAYGAIN_H
#define REPLAYGAIN_H

typedef struct {
  PyObject_HEAD;

} replaygain_ReplayGain;

void ReplayGain_dealloc(replaygain_ReplayGain* self);

PyObject *ReplayGain_new(PyTypeObject *type, PyObject *args, PyObject *kwds);

int ReplayGain_init(replaygain_ReplayGain *self, PyObject *args, PyObject *kwds);

PyObject* ReplayGain_update(replaygain_ReplayGain *self, PyObject *args);

PyObject* ReplayGain_title_gain(replaygain_ReplayGain *self);

PyObject* ReplayGain_album_gain(replaygain_ReplayGain *self);


#define GAIN_NOT_ENOUGH_SAMPLES  -24601
#define GAIN_ANALYSIS_ERROR           0
#define GAIN_ANALYSIS_OK              1

#define INIT_GAIN_ANALYSIS_ERROR      0
#define INIT_GAIN_ANALYSIS_OK         1

typedef double  Float_t;         // Type used for filtering

int     InitGainAnalysis ( long samplefreq );
int     AnalyzeSamples   ( const Float_t* left_samples, const Float_t* right_samples, size_t num_samples, int num_channels );
int	ResetSampleFrequency ( long samplefreq );
Float_t   GetTitleGain     ( void );
Float_t   GetAlbumGain     ( void );


#endif
