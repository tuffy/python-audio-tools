#include <Python.h>
#include "mod_defs.h"
#include "framelist.h"
#include "pcmreader.h"
#include "bitstream.h"
#include "dither.c"
#include "replaygain.h"

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

#ifndef MIN
#define MIN(x, y) ((x) < (y) ? (x) : (y))
#endif
#ifndef MAX
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#endif

PyMethodDef module_methods[] = {
    {NULL}
};

PyGetSetDef ReplayGain_getseters[] = {
    {"sample_rate",
     (getter)ReplayGain_sample_rate, NULL, "sample rate", NULL},
    {NULL}
};

PyMethodDef ReplayGain_methods[] = {
    {"update", (PyCFunction)ReplayGain_update,
     METH_VARARGS, "update(FrameList) -> None"},
    {"title_gain", (PyCFunction)ReplayGain_title_gain,
     METH_NOARGS, "title_gain() -> title gain float"},
    {"title_peak", (PyCFunction)ReplayGain_title_peak,
     METH_NOARGS, "title_peak() -> title peak float"},
    {"album_gain", (PyCFunction)ReplayGain_album_gain,
     METH_NOARGS, "album_gain() -> album gain float"},
    {"album_peak", (PyCFunction)ReplayGain_album_peak,
     METH_NOARGS, "album_peak() -> album peak float"},
    {"next_title", (PyCFunction)ReplayGain_next_title,
     METH_NOARGS, "call after each title is completed"},
    {NULL}
};

PyTypeObject replaygain_ReplayGainType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "replaygain.ReplayGain",   /*tp_name*/
    sizeof(replaygain_ReplayGain), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ReplayGain_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "ReplayGain objects",      /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ReplayGain_methods,        /* tp_methods */
    0,                         /* tp_members */
    ReplayGain_getseters,      /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ReplayGain_init, /* tp_init */
    0,                         /* tp_alloc */
    ReplayGain_new,            /* tp_new */
};

void
ReplayGain_dealloc(replaygain_ReplayGain* self)
{
    Py_XDECREF(self->framelist_type);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject*
ReplayGain_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    replaygain_ReplayGain *self;

    self = (replaygain_ReplayGain *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
ReplayGain_init(replaygain_ReplayGain *self, PyObject *args, PyObject *kwds)
{
    long sample_rate;
    PyObject *audiotools_pcm;
    int  i;

    self->framelist_type = NULL;
    self->sample_rate = 0;
    self->title_peak = 0.0;
    self->album_peak = 0.0;

    if (!PyArg_ParseTuple(args, "l", &sample_rate))
        return -1;

    /*store FrameList type for later comparison*/
    if ((audiotools_pcm = PyImport_ImportModule("audiotools.pcm")) != NULL) {
        self->framelist_type = PyObject_GetAttrString(audiotools_pcm,
                                                      "FrameList");
        Py_DECREF(audiotools_pcm);
    } else {
        return -1;
    }

    self->sample_rate = (unsigned)sample_rate;

    /* zero out initial values*/
    for (i = 0; i < MAX_ORDER; i++ )
        self->linprebuf[i] =
            self->lstepbuf[i] =
            self->loutbuf[i] =
            self->rinprebuf[i] =
            self->rstepbuf[i] =
            self->routbuf[i] = 0.;

    switch (sample_rate) {
    case 48000: self->freqindex = 0; break;
    case 44100: self->freqindex = 1; break;
    case 32000: self->freqindex = 2; break;
    case 24000: self->freqindex = 3; break;
    case 22050: self->freqindex = 4; break;
    case 16000: self->freqindex = 5; break;
    case 12000: self->freqindex = 6; break;
    case 11025: self->freqindex = 7; break;
    case  8000: self->freqindex = 8; break;
    case 18900: self->freqindex = 9; break;
    case 37800: self->freqindex = 10; break;
    case 56000: self->freqindex = 11; break;
    case 64000: self->freqindex = 12; break;
    case 88200: self->freqindex = 13; break;
    case 96000: self->freqindex = 14; break;
    case 112000: self->freqindex = 15; break;
    case 128000: self->freqindex = 16; break;
    case 144000: self->freqindex = 17; break;
    case 176400: self->freqindex = 18; break;
    case 192000: self->freqindex = 19; break;
    default:
        PyErr_SetString(PyExc_ValueError,"unsupported sample rate");
        return -1;
    }

    self->sampleWindow = (int)ceil(sample_rate * RMS_WINDOW_TIME);

    self->lsum         = 0.;
    self->rsum         = 0.;
    self->totsamp      = 0;

    memset (self->A, 0, sizeof(self->A));

    self->linpre       = self->linprebuf + MAX_ORDER;
    self->rinpre       = self->rinprebuf + MAX_ORDER;
    self->lstep        = self->lstepbuf  + MAX_ORDER;
    self->rstep        = self->rstepbuf  + MAX_ORDER;
    self->lout         = self->loutbuf   + MAX_ORDER;
    self->rout         = self->routbuf   + MAX_ORDER;

    memset (self->B, 0, sizeof(self->B));


    return 0;
}

PyObject*
ReplayGain_sample_rate(replaygain_ReplayGain *self, void *closure)
{
    return Py_BuildValue("I", self->sample_rate);
}

PyObject*
ReplayGain_next_title(replaygain_ReplayGain *self)
{
    /*reset initial values for next title*/
    int    i;

    for ( i = 0; i < (int)(sizeof(self->A)/sizeof(*(self->A))); i++ ) {
        self->B[i] += self->A[i];
        self->A[i]  = 0;
    }

    for ( i = 0; i < MAX_ORDER; i++ )
        self->linprebuf[i] =
            self->lstepbuf[i] =
            self->loutbuf[i] =
            self->rinprebuf[i] =
            self->rstepbuf[i] =
            self->routbuf[i] = 0.f;

    self->totsamp = 0;
    self->lsum    = self->rsum = 0.;

    self->title_peak = 0.0;

    Py_INCREF(Py_None);
    return Py_None;
}

#define CHUNK_SIZE 4096

PyObject*
ReplayGain_update(replaygain_ReplayGain *self, PyObject *args)
{
    pcm_FrameList* framelist;
    unsigned total_frames;
    const int *samples;
    int32_t peak_shift;
    static int left_i[CHUNK_SIZE];
    static int right_i[CHUNK_SIZE];
    static double left_f[CHUNK_SIZE];
    static double right_f[CHUNK_SIZE];

    if (!PyArg_ParseTuple(args, "O!", self->framelist_type, &framelist))
        return NULL;

    peak_shift = 1 << (framelist->bits_per_sample - 1);
    total_frames = framelist->frames;
    samples = framelist->samples;

    /*FrameList could be very large, so process it in chunks
      rather than all at once*/
    while (total_frames) {
        const unsigned to_process = MIN(total_frames, CHUNK_SIZE);
        unsigned i;

        /*split FrameList's packed ints into a set of channels
          to a maximum of 2 channels*/
        get_channel_data(samples,
                         0,
                         framelist->channels,
                         to_process,
                         left_i);

        /*if 1 channel, duplicate to right channel*/
        get_channel_data(samples,
                         framelist->channels > 1 ? 1 : 0,
                         framelist->channels,
                         to_process,
                         right_i);


        /*calculate peak values*/
        for (i = 0; i < to_process; i++) {
            const double peak_l = ((double)(abs(left_i[i]))) / peak_shift;
            const double peak_r = ((double)(abs(right_i[i]))) / peak_shift;
            const double peak = MAX(peak_l, peak_r);
            self->title_peak = MAX(self->title_peak, peak);
            self->album_peak = MAX(self->album_peak, peak);
        }

        /*convert channels to 16-bit doubles*/
        switch (framelist->bits_per_sample) {
        case 8:
            for (i = 0; i < to_process; i++) {
                left_f[i] = (double)(left_i[i] << 8);
                right_f[i] = (double)(right_i[i] << 8);
            }
            break;
        case 16:
            for (i = 0; i < to_process; i++) {
                left_f[i] = (double)(left_i[i]);
                right_f[i] = (double)(right_i[i]);
            }
            break;
        case 24:
            for (i = 0; i < to_process; i++) {
                left_f[i] = (double)(left_i[i] >> 8);
                right_f[i] = (double)(right_i[i] >> 8);
            }
            break;
        default:
            PyErr_SetString(PyExc_ValueError, "unsupported bits per sample");
            return NULL;
        }

        /*perform gain analysis on channels*/
        if (ReplayGain_analyze_samples(self,
                                       left_f,
                                       right_f,
                                       to_process,
                                       2) == GAIN_ANALYSIS_ERROR) {
            PyErr_SetString(PyExc_ValueError, "ReplayGain calculation error");
            return NULL;
        }

        total_frames -= to_process;
        samples += (to_process * framelist->channels);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject*
ReplayGain_title_gain(replaygain_ReplayGain *self)
{
    const double gain_value = ReplayGain_get_title_gain(self);
    if (gain_value != GAIN_NOT_ENOUGH_SAMPLES) {
        return Py_BuildValue("d", gain_value);
    } else {
        PyErr_SetString(PyExc_ValueError,
                        "Not enough samples to perform calculation");
        return NULL;
    }
}

PyObject*
ReplayGain_title_peak(replaygain_ReplayGain *self)
{
    return Py_BuildValue("d", self->title_peak);
}

PyObject*
ReplayGain_album_gain(replaygain_ReplayGain *self)
{
    const double gain_value = ReplayGain_get_album_gain(self);
    if (gain_value != GAIN_NOT_ENOUGH_SAMPLES) {
        return Py_BuildValue("d", gain_value);
    } else {
        PyErr_SetString(PyExc_ValueError,
                        "Not enough samples to perform calculation");
        return NULL;
    }
}

PyObject*
ReplayGain_album_peak(replaygain_ReplayGain *self)
{
    return Py_BuildValue("d", self->album_peak);
}

PyGetSetDef ReplayGainReader_getseters[] = {
    {"sample_rate",
     (getter)ReplayGainReader_sample_rate, NULL, "sample rate", NULL},
    {"bits_per_sample",
     (getter)ReplayGainReader_bits_per_sample, NULL, "bits per sample", NULL},
    {"channels",
     (getter)ReplayGainReader_channels, NULL, "channels", NULL},
    {"channel_mask",
     (getter)ReplayGainReader_channel_mask, NULL, "channel_mask", NULL},
    {NULL}
};

PyMethodDef ReplayGainReader_methods[] = {
    {"read", (PyCFunction)ReplayGainReader_read,
     METH_VARARGS,
     "Reads a pcm.FrameList with ReplayGain applied"},
    {"close", (PyCFunction)ReplayGainReader_close,
     METH_NOARGS, "Closes the substream"},
    {NULL}
};

PyTypeObject replaygain_ReplayGainReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "replaygain.ReplayGainReader", /*tp_name*/
    sizeof(replaygain_ReplayGainReader), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)ReplayGainReader_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "ReplayGainReader objects",/* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    ReplayGainReader_methods,  /* tp_methods */
    0,                         /* tp_members */
    ReplayGainReader_getseters,/* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)ReplayGainReader_init, /* tp_init */
    0,                         /* tp_alloc */
    ReplayGainReader_new,      /* tp_new */
};



MOD_INIT(replaygain)
{
    PyObject* m;

    MOD_DEF(m, "replaygain",
            "a ReplayGain calculation and synthesis module",
            module_methods)

    replaygain_ReplayGainType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&replaygain_ReplayGainType) < 0)
        return MOD_ERROR_VAL;

    replaygain_ReplayGainReaderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&replaygain_ReplayGainReaderType) < 0)
        return MOD_ERROR_VAL;

    Py_INCREF(&replaygain_ReplayGainType);
    PyModule_AddObject(m, "ReplayGain",
                       (PyObject *)&replaygain_ReplayGainType);

    Py_INCREF(&replaygain_ReplayGainReaderType);
    PyModule_AddObject(m, "ReplayGainReader",
                       (PyObject *)&replaygain_ReplayGainReaderType);

    return MOD_SUCCESS_VAL(m);
}




/* for each filter: */
/* [0] 48 kHz, [1] 44.1 kHz, [2] 32 kHz, [3] 24 kHz, [4] 22050 Hz, [5] 16 kHz, [6] 12 kHz, [7] is 11025 Hz, [8] 8 kHz */

static const double ABYule[20][2*YULE_ORDER + 1] = {
    /*48000Hz*/
    {0.03857599435200, -3.84664617118067, -0.02160367184185,  7.81501653005538, -0.00123395316851,-11.34170355132042, -0.00009291677959, 13.05504219327545, -0.01655260341619,-12.28759895145294,  0.02161526843274,  9.48293806319790, -0.02074045215285, -5.87257861775999,  0.00594298065125,  2.75465861874613,  0.00306428023191, -0.86984376593551,  0.00012025322027,  0.13919314567432,  0.00288463683916 },

    /*44100Hz*/
    {0.05418656406430, -3.47845948550071, -0.02911007808948,  6.36317777566148, -0.00848709379851, -8.54751527471874, -0.00851165645469,  9.47693607801280, -0.00834990904936, -8.81498681370155,  0.02245293253339,  6.85401540936998, -0.02596338512915, -4.39470996079559,  0.01624864962975,  2.19611684890774, -0.00240879051584, -0.75104302451432,  0.00674613682247,  0.13149317958808, -0.00187763777362 },

    /*32000Hz*/
    {0.15457299681924, -2.37898834973084, -0.09331049056315,  2.84868151156327, -0.06247880153653, -2.64577170229825,  0.02163541888798,  2.23697657451713, -0.05588393329856, -1.67148153367602,  0.04781476674921,  1.00595954808547,  0.00222312597743, -0.45953458054983,  0.03174092540049,  0.16378164858596, -0.01390589421898, -0.05032077717131,  0.00651420667831,  0.02347897407020, -0.00881362733839 },

    /*24000Hz*/
    {0.30296907319327, -1.61273165137247, -0.22613988682123,  1.07977492259970, -0.08587323730772, -0.25656257754070,  0.03282930172664, -0.16276719120440, -0.00915702933434, -0.22638893773906, -0.02364141202522,  0.39120800788284, -0.00584456039913, -0.22138138954925,  0.06276101321749,  0.04500235387352, -0.00000828086748,  0.02005851806501,  0.00205861885564,  0.00302439095741, -0.02950134983287 },

    /*22050Hz*/
    {0.33642304856132, -1.49858979367799, -0.25572241425570,  0.87350271418188, -0.11828570177555,  0.12205022308084,  0.11921148675203, -0.80774944671438, -0.07834489609479,  0.47854794562326, -0.00469977914380, -0.12453458140019, -0.00589500224440, -0.04067510197014,  0.05724228140351,  0.08333755284107,  0.00832043980773, -0.04237348025746, -0.01635381384540,  0.02977207319925, -0.01760176568150 },

    /*16000Hz*/
    {0.44915256608450, -0.62820619233671, -0.14351757464547,  0.29661783706366, -0.22784394429749, -0.37256372942400, -0.01419140100551,  0.00213767857124,  0.04078262797139, -0.42029820170918, -0.12398163381748,  0.22199650564824,  0.04097565135648,  0.00613424350682,  0.10478503600251,  0.06747620744683, -0.01863887810927,  0.05784820375801, -0.03193428438915,  0.03222754072173,  0.00541907748707 },

    /*12000Hz*/
    {0.56619470757641, -1.04800335126349, -0.75464456939302,  0.29156311971249,  0.16242137742230, -0.26806001042947,  0.16744243493672,  0.00819999645858, -0.18901604199609,  0.45054734505008,  0.30931782841830, -0.33032403314006, -0.27562961986224,  0.06739368333110,  0.00647310677246, -0.04784254229033,  0.08647503780351,  0.01639907836189, -0.03788984554840,  0.01807364323573, -0.00588215443421 },

    /*11025Hz*/
    {0.58100494960553, -0.51035327095184, -0.53174909058578, -0.31863563325245, -0.14289799034253, -0.20256413484477,  0.17520704835522,  0.14728154134330,  0.02377945217615,  0.38952639978999,  0.15558449135573, -0.23313271880868, -0.25344790059353, -0.05246019024463,  0.01628462406333, -0.02505961724053,  0.06920467763959,  0.02442357316099, -0.03721611395801,  0.01818801111503, -0.00749618797172 },

    /*8000Hz*/
    {0.53648789255105, -0.25049871956020, -0.42163034350696, -0.43193942311114, -0.00275953611929, -0.03424681017675,  0.04267842219415, -0.04678328784242, -0.10214864179676,  0.26408300200955,  0.14590772289388,  0.15113130533216, -0.02459864859345, -0.17556493366449, -0.11202315195388, -0.18823009262115, -0.04060034127000,  0.05477720428674,  0.04788665548180,  0.04704409688120, -0.02217936801134 },


    /*18900Hz*/
    {0.38524531015142, -1.29708918404534, -0.27682212062067, 0.90399339674203, -0.09980181488805, -0.29613799017877, 0.09951486755646, -0.42326645916207, -0.08934020156622, 0.37934887402200, -0.00322369330199, -0.37919795944938, -0.00110329090689, 0.23410283284785, 0.03784509844682, -0.03892971758879, 0.01683906213303, 0.00403009552351, -0.01147039862572, 0.03640166626278, -0.01941767987192 },

    /*37800Hz*/
    {0.08717879977844, -2.62816311472146, -0.01000374016172, 3.53734535817992, -0.06265852122368, -3.81003448678921, -0.01119328800950, 3.91291636730132, -0.00114279372960, -3.53518605896288, 0.02081333954769, 2.71356866157873, -0.01603261863207, -1.86723311846592, 0.01936763028546, 1.12075382367659, 0.00760044736442, -0.48574086886890, -0.00303979112271, 0.11330544663849, -0.00075088605788 },

    /*56000Hz*/
    {0.03144914734085, -4.87377313090032, -0.06151729206963, 12.03922160140209, 0.08066788708145, -20.10151118381395, -0.09737939921516, 25.10388534415171, 0.08943210803999, -24.29065560815903, -0.06989984672010, 18.27158469090663, 0.04926972841044, -10.45249552560593, -0.03161257848451, 4.30319491872003, 0.01456837493506, -1.13716992070185, -0.00316015108496, 0.14510733527035, 0.00132807215875 },

    /*64000Hz*/
    {0.02613056568174, -5.73625477092119, -0.08128786488109, 16.15249794355035, 0.14937282347325, -29.68654912464508, -0.21695711675126, 39.55706155674083, 0.25010286673402, -39.82524556246253, -0.23162283619278, 30.50605345013009, 0.17424041833052, -17.43051772821245, -0.10299599216680, 7.05154573908017, 0.04258696481981, -1.80783839720514, -0.00977952936493, 0.22127840210813, 0.00105325558889 },

    /*88200Hz*/
    {0.02667482047416, -6.31836451657302, -0.11377479336097, 18.31351310801799, 0.23063167910965, -31.88210014815921, -0.30726477945593, 36.53792146976740, 0.33188520686529, -28.23393036467559, -0.33862680249063, 14.24725258227189, 0.31807161531340, -4.04670980012854, -0.23730796929880, 0.18865757280515, 0.12273894790371, 0.25420333563908, -0.03840017967282, -0.06012333531065, 0.00549673387936 },

    /*96000Hz*/
    {0.00588138296683, -5.97808823642008, -0.01613559730421, 16.21362507964068, 0.02184798954216, -25.72923730652599, -0.01742490405317, 25.40470663139513, 0.00464635643780, -14.66166287771134, 0.01117772513205, 2.81597484359752, -0.02123865824368, 2.51447125969733, 0.01959354413350, -2.23575306985286, -0.01079720643523, 0.75788151036791, 0.00352183686289, -0.10078025199029, -0.00063124341421 },

    /*112000Hz*/
    {0.00528778718259, -6.24932108456288, -0.01893240907245, 17.42344320538476, 0.03185982561867, -27.86819709054896, -0.02926260297838, 26.79087344681326, 0.00715743034072, -13.43711081485123, 0.01985743355827, -0.66023612948173, -0.03222614850941, 6.03658091814935, 0.02565681978192, -4.24926577030310, -0.01210662313473, 1.40829268709186, 0.00325436284541, -0.19480852628112, -0.00044173593001 },

    /*128000Hz*/
    {0.00553120584305, -6.14581710839925, -0.02112620545016, 16.04785903675838, 0.03549076243117, -22.19089131407749, -0.03362498312306, 15.24756471580286, 0.01425867248183, -0.52001440400238, 0.01344686928787, -8.00488641699940, -0.03392770787836, 6.60916094768855, 0.03464136459530, -2.37856022810923, -0.02039116051549, 0.33106947986101, 0.00667420794705, 0.00459820832036, -0.00093763762995 },

    /*144000Hz*/
    {0.00639682359450, -6.14814623523425, -0.02556437970955, 15.80002457141566, 0.04230854400938, -20.78487587686937, -0.03722462201267, 11.98848552310315, 0.01718514827295, 3.36462015062606, 0.00610592243009, -10.22419868359470, -0.03065965747365, 6.65599702146473, 0.04345745003539, -1.67141861110485, -0.03298592681309, -0.05417956536718, 0.01320937236809, 0.07374767867406, -0.00220304127757 },

    /*176400Hz*/
    {0.00268568524529, -5.57512782763045, -0.00852379426080, 12.44291056065794, 0.00852704191347, -12.87462799681221, 0.00146116310295, 3.08554846961576, -0.00950855828762, 6.62493459880692, 0.00625449515499, -7.07662766313248, 0.00116183868722, 2.51175542736441, -0.00362461417136, 0.06731510802735, 0.00203961000134, -0.24567753819213, -0.00050664587933, 0.03961404162376, 0.00004327455427 },

    /*192000Hz*/
    {0.01184742123123, -5.24727318348167, -0.04631092400086, 10.60821585192244, 0.06584226961238, -8.74127665810413, -0.02165588522478, -1.33906071371683, -0.05656260778952, 8.07972882096606, 0.08607493592760, -5.46179918950847, -0.03375544339786, 0.54318070652536, -0.04216579932754, 0.87450969224280, 0.06416711490648, -0.34656083539754, -0.03444708260844, 0.03034796843589, 0.00697275872241 },
};

static const double ABButter[20][2*BUTTER_ORDER + 1] = {
    /*48000Hz*/
    {0.98621192462708, -1.97223372919527, -1.97242384925416,  0.97261396931306,  0.98621192462708 },

    /*44100Hz*/
    {0.98500175787242, -1.96977855582618, -1.97000351574484,  0.97022847566350,  0.98500175787242 },

    /*32000Hz*/
    {0.97938932735214, -1.95835380975398, -1.95877865470428,  0.95920349965459,  0.97938932735214 },

    /*24000Hz*/
    {0.97531843204928, -1.95002759149878, -1.95063686409857,  0.95124613669835,  0.97531843204928 },

    /*22050Hz*/
    {0.97316523498161, -1.94561023566527, -1.94633046996323,  0.94705070426118,  0.97316523498161 },

    /*16000Hz*/
    {0.96454515552826, -1.92783286977036, -1.92909031105652,  0.93034775234268,  0.96454515552826 },

    /*12000Hz*/
    {0.96009142950541, -1.91858953033784, -1.92018285901082,  0.92177618768381,  0.96009142950541 },

    /*11025Hz*/
    {0.95856916599601, -1.91542108074780, -1.91713833199203,  0.91885558323625,  0.95856916599601 },

    /*8000Hz*/
    {0.94597685600279, -1.88903307939452, -1.89195371200558,  0.89487434461664,  0.94597685600279 },

    /*18900Hz*/
    {0.96535326815829, -1.92950577983524, -1.93070653631658, 0.93190729279793, 0.96535326815829 },

    /*37800Hz*/
    {0.98252400815195, -1.96474258269041, -1.96504801630391, 0.96535344991740, 0.98252400815195 },

    /*56000Hz*/
    {0.98816995007392, -1.97619994516973, -1.97633990014784, 0.97647985512594, 0.98816995007392 },

    /*64000Hz*/
    {0.98964101933472, -1.97917472731009, -1.97928203866944, 0.97938935002880, 0.98964101933472 },

    /*88200Hz*/
    {0.99247255046129, -1.98488843762335, -1.98494510092259, 0.98500176422183, 0.99247255046129 },

    /*96000Hz*/
    {0.99308203517541, -1.98611621154089, -1.98616407035082, 0.98621192916075, 0.99308203517541 },

    /*112000Hz*/
    {0.99406737810867, -1.98809955990514, -1.98813475621734, 0.98816995252954, 0.99406737810867 },

    /*128000Hz*/
    {0.99480702681278, -1.98958708647324, -1.98961405362557, 0.98964102077790, 0.99480702681278 },

    /*144000Hz*/
    {0.99538268958706, -1.99074405950505, -1.99076537917413, 0.99078669884321, 0.99538268958706 },

    /*176400Hz*/
    {0.99622916581118, -1.99244411238133, -1.99245833162236, 0.99247255086339, 0.99622916581118 },

    /*192000Hz*/
    {0.99653501465135, -1.99305802314321, -1.99307002930271, 0.99308203546221, 0.99653501465135 }
};


/* When calling these filter procedures, make sure that ip[-order] and op[-order] point to real data! */

/* If your compiler complains that "'operation on 'output' may be undefined", you can */
/* either ignore the warnings or uncomment the three "y" lines (and comment out the indicated line) */

static void
filterYule (const double* input, double* output, size_t nSamples,
            const double* kernel)
{
    while (nSamples--) {
        *output =  1e-10  /* 1e-10 is a hack to avoid slowdown because of denormals */
            + input [0]  * kernel[0]
            - output[-1] * kernel[1]
            + input [-1] * kernel[2]
            - output[-2] * kernel[3]
            + input [-2] * kernel[4]
            - output[-3] * kernel[5]
            + input [-3] * kernel[6]
            - output[-4] * kernel[7]
            + input [-4] * kernel[8]
            - output[-5] * kernel[9]
            + input [-5] * kernel[10]
            - output[-6] * kernel[11]
            + input [-6] * kernel[12]
            - output[-7] * kernel[13]
            + input [-7] * kernel[14]
            - output[-8] * kernel[15]
            + input [-8] * kernel[16]
            - output[-9] * kernel[17]
            + input [-9] * kernel[18]
            - output[-10]* kernel[19]
            + input [-10]* kernel[20];
        ++output;
        ++input;
    }
}

static void
filterButter (const double* input, double* output, size_t nSamples, const double* kernel)
{
    while (nSamples--) {
        *output =
            input [0]  * kernel[0]
            - output[-1] * kernel[1]
            + input [-1] * kernel[2]
            - output[-2] * kernel[3]
            + input [-2] * kernel[4];
        ++output;
        ++input;
    }
}

static inline double
fsqr(const double d)
{
    return d * d;
}

/* returns GAIN_ANALYSIS_OK if successful, GAIN_ANALYSIS_ERROR if not */
gain_calc_status
ReplayGain_analyze_samples(replaygain_ReplayGain* self,
                           const double* left_samples,
                           const double* right_samples,
                           size_t num_samples,
                           int num_channels)
{
    const double*  curleft;
    const double*  curright;
    long            batchsamples;
    long            cursamples;
    long            cursamplepos;
    long            i;

    if ( num_samples == 0 )
        return GAIN_ANALYSIS_OK;

    cursamplepos = 0;
    batchsamples = num_samples;

    switch ( num_channels) {
    case  1: right_samples = left_samples;
    case  2: break;
    default: return GAIN_ANALYSIS_ERROR;
    }

    if ( num_samples < MAX_ORDER ) {
        memcpy (self->linprebuf + MAX_ORDER, left_samples , num_samples * sizeof(double) );
        memcpy ( self->rinprebuf + MAX_ORDER, right_samples, num_samples * sizeof(double) );
    }
    else {
        memcpy ( self->linprebuf + MAX_ORDER, left_samples,  MAX_ORDER   * sizeof(double) );
        memcpy ( self->rinprebuf + MAX_ORDER, right_samples, MAX_ORDER   * sizeof(double) );
    }

    while ( batchsamples > 0 ) {
        cursamples = batchsamples > self->sampleWindow - self->totsamp  ?  self->sampleWindow - self->totsamp  :  batchsamples;
        if ( cursamplepos < MAX_ORDER ) {
            curleft  = self->linpre + cursamplepos;
            curright = self->rinpre + cursamplepos;
            if (cursamples > MAX_ORDER - cursamplepos )
                cursamples = MAX_ORDER - cursamplepos;
        }
        else {
            curleft  = left_samples  + cursamplepos;
            curright = right_samples + cursamplepos;
        }

        YULE_FILTER ( curleft , self->lstep + self->totsamp, cursamples, ABYule[self->freqindex]);
        YULE_FILTER ( curright, self->rstep + self->totsamp, cursamples, ABYule[self->freqindex]);

        BUTTER_FILTER ( self->lstep + self->totsamp, self->lout + self->totsamp, cursamples, ABButter[self->freqindex]);
        BUTTER_FILTER ( self->rstep + self->totsamp, self->rout + self->totsamp, cursamples, ABButter[self->freqindex]);

        curleft = self->lout + self->totsamp; /* Get the squared values */
        curright = self->rout + self->totsamp;

        i = cursamples % 16;
        while (i--)
            {   self->lsum += fsqr(*curleft++);
                self->rsum += fsqr(*curright++);
            }
        i = cursamples / 16;
        while (i--)
            {   self->lsum += fsqr(curleft[0])
                    + fsqr(curleft[1])
                    + fsqr(curleft[2])
                    + fsqr(curleft[3])
                    + fsqr(curleft[4])
                    + fsqr(curleft[5])
                    + fsqr(curleft[6])
                    + fsqr(curleft[7])
                    + fsqr(curleft[8])
                    + fsqr(curleft[9])
                    + fsqr(curleft[10])
                    + fsqr(curleft[11])
                    + fsqr(curleft[12])
                    + fsqr(curleft[13])
                    + fsqr(curleft[14])
                    + fsqr(curleft[15]);
                curleft += 16;
                self->rsum += fsqr(curright[0])
                    + fsqr(curright[1])
                    + fsqr(curright[2])
                    + fsqr(curright[3])
                    + fsqr(curright[4])
                    + fsqr(curright[5])
                    + fsqr(curright[6])
                    + fsqr(curright[7])
                    + fsqr(curright[8])
                    + fsqr(curright[9])
                    + fsqr(curright[10])
                    + fsqr(curright[11])
                    + fsqr(curright[12])
                    + fsqr(curright[13])
                    + fsqr(curright[14])
                    + fsqr(curright[15]);
                curright += 16;
            }

        batchsamples -= cursamples;
        cursamplepos += cursamples;
        self->totsamp      += cursamples;
        if ( self->totsamp == self->sampleWindow ) {  /* Get the Root Mean Square (RMS) for this set of samples */
            double  val  = STEPS_per_dB * 10. * log10 ( (self->lsum + self->rsum) / self->totsamp * 0.5 + 1.e-37 );
            int     ival = (int) val;
            if ( ival <                     0 ) ival = 0;
            if ( ival >= (int)(sizeof(self->A)/sizeof(*(self->A))) ) ival = sizeof(self->A)/sizeof(*(self->A)) - 1;
            self->A [ival]++;
            self->lsum = self->rsum = 0.;
            memmove ( self->loutbuf , self->loutbuf  + self->totsamp, MAX_ORDER * sizeof(double) );
            memmove ( self->routbuf , self->routbuf  + self->totsamp, MAX_ORDER * sizeof(double) );
            memmove ( self->lstepbuf, self->lstepbuf + self->totsamp, MAX_ORDER * sizeof(double) );
            memmove ( self->rstepbuf, self->rstepbuf + self->totsamp, MAX_ORDER * sizeof(double) );
            self->totsamp = 0;
        }
        if ( self->totsamp > self->sampleWindow )   /* somehow I really screwed up: Error in programming! Contact author about self->totsamp > self->sampleWindow */
            return GAIN_ANALYSIS_ERROR;
    }
    if ( num_samples < MAX_ORDER ) {
        memmove ( self->linprebuf,                           self->linprebuf + num_samples, (MAX_ORDER-num_samples) * sizeof(double) );
        memmove ( self->rinprebuf,                           self->rinprebuf + num_samples, (MAX_ORDER-num_samples) * sizeof(double) );
        memcpy  ( self->linprebuf + MAX_ORDER - num_samples, left_samples,          num_samples             * sizeof(double) );
        memcpy  ( self->rinprebuf + MAX_ORDER - num_samples, right_samples,         num_samples             * sizeof(double) );
    }
    else {
        memcpy  ( self->linprebuf, left_samples  + num_samples - MAX_ORDER, MAX_ORDER * sizeof(double) );
        memcpy  ( self->rinprebuf, right_samples + num_samples - MAX_ORDER, MAX_ORDER * sizeof(double) );
    }

    return GAIN_ANALYSIS_OK;
}


static double
analyzeResult(uint32_t* Array, size_t len)
{
    uint32_t  elems;
    int32_t   upper;
    size_t    i;

    elems = 0;
    for ( i = 0; i < len; i++ )
        elems += Array[i];
    if ( elems == 0 )
        return GAIN_NOT_ENOUGH_SAMPLES;

    upper = (int32_t)ceil (elems * (1. - RMS_PERCENTILE));
    for ( i = len; i-- > 0; ) {
        if ( (upper -= Array[i]) <= 0 )
            break;
    }

    return (double) ((double)PINK_REF - (double)i / (double)STEPS_per_dB);
}


double
ReplayGain_get_title_gain(replaygain_ReplayGain *self)
{
    return analyzeResult(self->A, sizeof(self->A)/sizeof(*(self->A)) );
}


double
ReplayGain_get_album_gain(replaygain_ReplayGain *self)
{
    return analyzeResult(self->B, sizeof(self->B)/sizeof(*(self->B)) );
}


PyObject*
ReplayGainReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    replaygain_ReplayGainReader *self;

    self = (replaygain_ReplayGainReader *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}

int
ReplayGainReader_init(replaygain_ReplayGainReader *self,
                      PyObject *args, PyObject *kwds) {
    double replaygain;
    double peak;

    self->stream_closed = 0;
    self->pcmreader = NULL;
    self->white_noise = NULL;
    self->audiotools_pcm = NULL;


    if (!PyArg_ParseTuple(args, "O&dd",
                          py_obj_to_pcmreader, &(self->pcmreader),
                          &(replaygain),
                          &(peak)))
        return -1;

    if ((self->white_noise = open_dither()) == NULL)
        return -1;

    if ((self->audiotools_pcm = open_audiotools_pcm()) == NULL)
        return -1;

    self->multiplier = powl(10.0l, replaygain / 20.0l);
    if (self->multiplier > 1.0l)
        self->multiplier = 1.0l / peak;

    return 0;
}

void
ReplayGainReader_dealloc(replaygain_ReplayGainReader* self) {
    if (self->pcmreader != NULL)
        self->pcmreader->del(self->pcmreader);
    if (self->white_noise != NULL)
        self->white_noise->close(self->white_noise);
    Py_XDECREF(self->audiotools_pcm);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject*
ReplayGainReader_sample_rate(replaygain_ReplayGainReader *self,
                             void *closure) {
    return Py_BuildValue("i", self->pcmreader->sample_rate);
}

static PyObject*
ReplayGainReader_bits_per_sample(replaygain_ReplayGainReader *self,
                                 void *closure) {
    return Py_BuildValue("i", self->pcmreader->bits_per_sample);
}

static PyObject*
ReplayGainReader_channels(replaygain_ReplayGainReader *self,
                          void *closure) {
    return Py_BuildValue("i", self->pcmreader->channels);
}

static PyObject*
ReplayGainReader_channel_mask(replaygain_ReplayGainReader *self,
                              void *closure) {
    return Py_BuildValue("i", self->pcmreader->channel_mask);
}

static PyObject*
ReplayGainReader_read(replaygain_ReplayGainReader* self, PyObject *args) {
    int pcm_frames;

    if (self->stream_closed) {
        PyErr_SetString(PyExc_ValueError, "unable to read from closed stream");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "i", &pcm_frames))
        return NULL;

    if (pcm_frames <= 0) {
        PyErr_SetString(PyExc_ValueError, "pcm_frames must be positive");
        return NULL;
    } else {
        const int max_value = (1 << (self->pcmreader->bits_per_sample - 1)) - 1;
        const int min_value = -(1 << (self->pcmreader->bits_per_sample - 1));
        const double multiplier = self->multiplier;

        pcm_FrameList *framelist = new_FrameList(
            self->audiotools_pcm,
            self->pcmreader->channels,
            self->pcmreader->bits_per_sample,
            pcm_frames);

        const unsigned frames_read =
            self->pcmreader->read(self->pcmreader,
                                  pcm_frames,
                                  framelist->samples);
        const unsigned total_samples =
            frames_read * self->pcmreader->channels;
        unsigned i;

        if (!frames_read && (self->pcmreader->status != PCM_OK)) {
            Py_DECREF((PyObject*)framelist);
            return NULL;
        } else {
            framelist->frames = frames_read;
            framelist->samples_length = total_samples;
        }

        /*apply our multiplier to framelist's integer samples
          and apply dithering*/
        for (i = 0; i < total_samples; i++) {
            framelist->samples[i] =
                (int)lround(framelist->samples[i] * multiplier);
            framelist->samples[i] =
                (MIN(MAX(framelist->samples[i], min_value), max_value) ^
                 self->white_noise->read(self->white_noise, 1));
        }

        /*return integer samples as a new FrameList object*/
        return (PyObject*)framelist;
    }
}

static PyObject*
ReplayGainReader_close(replaygain_ReplayGainReader* self, PyObject *args) {
    self->pcmreader->close(self->pcmreader);
    self->stream_closed = 1;
    Py_INCREF(Py_None);
    return Py_None;
}
